"""Official-release checks and verified, deferred portable updates.

Network work runs on a background thread. A staged release is installed at the
next launch/restart, before the server starts, by an external worker runtime.
Source checkouts can check for releases but are never overwritten.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

from . import __version__, config
from . import i18n as _i18n
from .update_worker import MANIFEST, COMPONENTS, digest, relative_file, verify, update_locked

REPO = 'ProJ-Yeet/Medieval2-GUI-Toolkit'
RELEASES = 'https://api.github.com/repos/' + REPO + '/releases/latest'
MAX_DOWNLOAD = 256 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
CHECK_INTERVAL = 6 * 60 * 60
log = logging.getLogger(__name__)


def version(text):
    if not isinstance(text, str) or not re.fullmatch(r'v?\d+\.\d+\.\d+', text):
        raise ValueError(_i18n.msg('eng.updater.expected_a_stable_release_version', 'Expected a stable release version'))
    return tuple(map(int, text.lstrip('v').split('.')))


def managed(root):
    root = Path(root)
    return ((root / MANIFEST).is_file() and (root / 'runtime/python.exe').is_file()
            and not (root / '.git').exists() and not (root.parent / '.git').exists())


class _Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        if u.scheme != 'https' or u.hostname not in {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com', 'releases.githubusercontent.com'}:
            raise ValueError(_i18n.msg('eng.updater.update_redirected_outside_github', 'Update redirected outside GitHub'))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Medieval2-GUI-Toolkit/' + __version__,
                                              'Accept': 'application/vnd.github+json'})
    return urllib.request.build_opener(_Redirects()).open(req, timeout=30)


def select_release(data, current):
    tag = data.get('tag_name', '')
    if data.get('draft') or data.get('prerelease') or version(tag) <= version(current):
        return None
    wanted = 'Medieval2-GUI-Toolkit-' + tag + '.zip'
    for asset in data.get('assets', []):
        if asset.get('name') != wanted or asset.get('state', 'uploaded') != 'uploaded':
            continue
        url = 'https://github.com/' + REPO + '/releases/download/' + tag + '/' + wanted
        sha = asset.get('digest', '')
        size = asset.get('size', 0)
        if asset.get('browser_download_url') != url or not re.fullmatch('sha256:[0-9a-f]{64}', sha or ''):
            raise ValueError(_i18n.msg('eng.updater.the_release_has_no_verified_portable_download', 'The release has no verified portable download'))
        if not isinstance(size, int) or not 0 < size <= MAX_DOWNLOAD:
            raise ValueError(_i18n.msg('eng.updater.invalid_update_download_size', 'Invalid update download size'))
        return {'version': tag, 'url': url, 'size': size, 'sha256': sha[7:],
                'release_url': 'https://github.com/' + REPO + '/releases/tag/' + tag}
    raise ValueError(_i18n.msg('eng.updater.the_latest_release_has_no_portable_zip_asset', 'The latest release has no portable ZIP asset'))


def unpack(archive, stage, expected):
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        seen, total = set(), 0
        for item in z.infolist():
            name = item.filename
            if not name.startswith('Medieval2-GUI-Toolkit/') or '\\' in name or ':' in name:
                raise ValueError(_i18n.msg('eng.updater.unexpected_update_archive_path', 'Unexpected update archive path'))
            rel = name[len('Medieval2-GUI-Toolkit/'):].rstrip('/')
            if not rel:
                continue
            if rel != MANIFEST:
                relative_file(rel)
            if rel.lower() in seen or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(_i18n.msg('eng.updater.duplicate_or_linked_update_entry', 'Duplicate or linked update entry'))
            seen.add(rel.lower())
            total += item.file_size
            if total > MAX_EXPANDED:
                raise ValueError(_i18n.msg('eng.updater.update_archive_is_too_large', 'Update archive is too large'))
            target = stage / rel
            if not target.resolve().is_relative_to(stage.resolve()):
                raise ValueError(_i18n.msg('eng.updater.update_archive_escapes_its_staging_folder', 'Update archive escapes its staging folder'))
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as src, target.open('xb') as dest:
                shutil.copyfileobj(src, dest)
    return verify(stage, expected, strict=True, allow_cache=False)


class UpdateManager:
    def __init__(self, root=None, current=__version__):
        self.root = Path(root or config.PROJECT_ROOT).resolve()
        self.current = current
        self.folder = self.root / 'config/updates'
        self.lock = threading.RLock()
        self.busy = False
        self.loop_started = False
        self.status = self._read('state.json') or {'phase': 'idle'}
        pending = self._read('pending.json')
        try:
            if pending and version(pending['version']) > version(current):
                self.status.update(phase='ready', latest=pending['version'])
        except (KeyError, ValueError, TypeError):
            self.status.update(phase='error', error='The pending update record is invalid')

    def _read(self, name):
        try:
            return json.loads((self.folder / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def snapshot(self):
        with self.lock:
            return dict(self.status, current=self.current, managed=managed(self.root), busy=self.busy,
                        enabled=config.load_settings().get('auto_updates', True) is not False)

    def report(self, **changes):
        with self.lock:
            self.status.update(changes)
            config._write_json(self.folder / 'state.json', self.status)

    def check(self, force=False):
        with self.lock:
            if self.busy:
                return self.snapshot()
            if not force and time.time() - self.status.get('checked_at', 0) < CHECK_INTERVAL:
                return self.snapshot()
            self.busy = True
            threading.Thread(target=self._check, daemon=True, name='release-check').start()
        return self.snapshot()

    def _check(self):
        try:
            self.report(phase='checking', error='', progress=0)
            with open_url(RELEASES) as response:
                data = json.loads(response.read(2 * 1024 * 1024))
            release = select_release(data, self.current)
            self.report(checked_at=time.time())
            if not release:
                self.report(phase='up_to_date', latest=self.current)
                return
            self.report(latest=release['version'], release_url=release['release_url'])
            if not managed(self.root):
                self.report(phase='source')
                return
            if config.load_settings().get('auto_updates', True) is False:
                self.report(phase='available')
                return
            pending = self._read('pending.json')
            if pending.get('version') == release['version']:
                verify(Path(pending['stage']), release['version'], strict=True, allow_cache=False)
                self.report(phase='ready', progress=100)
                return
            verify(self.root, self.current, strict=True)
            self.folder.mkdir(parents=True, exist_ok=True)
            token = uuid.uuid4().hex
            archive = self.folder / (token + '.download')
            self.report(phase='downloading')
            sha, count, stage, complete = hashlib.sha256(), 0, None, False
            try:
                with open_url(release['url']) as response, archive.open('xb') as out:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > release['size'] or count > MAX_DOWNLOAD:
                            raise ValueError(_i18n.msg('eng.updater.update_download_exceeded_its_declared_size', 'Update download exceeded its declared size'))
                        if config.load_settings().get('auto_updates', True) is False:
                            self.report(phase='available')
                            return
                        sha.update(chunk); out.write(chunk)
                        self.report(progress=int(count * 100 / release['size']))
                if count != release['size'] or sha.hexdigest() != release['sha256']:
                    raise ValueError(_i18n.msg('eng.updater.update_download_is_incomplete_or_its_checksum_does', 'Update download is incomplete or its checksum does not match'))
                stage = self.folder / ('stage-' + token)
                unpack(archive, stage, release['version'])
                config._write_json(self.folder / 'pending.json', {'version': release['version'], 'stage': str(stage)})
                complete = True
                self.report(phase='ready', progress=100)
            finally:
                archive.unlink(missing_ok=True)
                if stage and not complete and stage.resolve().is_relative_to(self.folder.resolve()) and stage.resolve() != self.folder.resolve():
                    shutil.rmtree(stage, ignore_errors=True)
        except Exception as exc:
            log.warning('Update check/download failed: %s', exc)
            self.report(phase='error', error=str(exc))
        finally:
            with self.lock:
                self.busy = False

    def start(self):
        if self.loop_started or os.environ.get('UT_NO_UPDATES') or os.environ.get('UT_NO_BROWSER'):
            return
        self.loop_started = True
        def loop():
            while True:
                if config.load_settings().get('auto_updates', True) is not False:
                    self.check()
                time.sleep(CHECK_INTERVAL)
        threading.Thread(target=loop, daemon=True, name='automatic-updates').start()


_manager = None
_manager_lock = threading.Lock()


def manager():
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = UpdateManager()
        return _manager


def apply_on_launch(root, port, no_browser=False):
    """Hand a pending install to a helper; caller must exit before it can start."""
    root = Path(root).resolve()
    if update_locked(root):
        return True  # The caller exits while the existing worker finishes/restarts.
    if not managed(root) or config.load_settings().get('auto_updates', True) is False:
        return False
    pending_file = root / 'config/updates/pending.json'
    if not pending_file.is_file():
        return False
    try:
        pending = json.loads(pending_file.read_text(encoding='utf-8'))
        if version(pending['version']) <= version(__version__):
            pending_file.unlink()
            return False
        stage = Path(pending['stage']).resolve()
        if not stage.is_relative_to(root / 'config/updates'):
            raise ValueError(_i18n.msg('eng.updater.update_staging_path_is_outside_this_installation', 'Update staging path is outside this installation'))
        verify(root, __version__, strict=True)
        verify(stage, pending['version'], strict=True, allow_cache=False)
        worker = root / 'config/updates' / ('worker-' + uuid.uuid4().hex)
        runtime = worker / 'runtime'
        runtime.mkdir(parents=True)
        # A private stdlib-only interpreter can replace even the installed runtime.
        # Its ._pth's parent entry resolves to worker/, alongside update_worker.py.
        for path in (root / 'runtime').iterdir():
            if path.is_file():
                shutil.copy2(path, runtime / path.name)
        shutil.copy2(Path(__file__).with_name('update_worker.py'), worker / 'update_worker.py')
        job = worker / 'job.json'
        config._write_json(job, {'root': str(root), 'stage': str(stage), 'version': pending['version'],
                                'backup': str(root / 'config/updates' / ('rollback-' + uuid.uuid4().hex)),
                                'pid': os.getpid(), 'port': int(port), 'no_browser': no_browser})
        subprocess.Popen([str(runtime / 'python.exe'), str(worker / 'update_worker.py'), str(job)],
                         cwd=worker, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return True
    except Exception as exc:
        log.warning('Update installation postponed: %s', exc)
        config._write_json(root / 'config/updates/state.json', {'phase': 'error', 'error': str(exc)})
        return False
