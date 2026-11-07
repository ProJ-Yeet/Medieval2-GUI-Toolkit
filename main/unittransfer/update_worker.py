"""Transactional portable-update worker. Runs outside the installed runtime."""
from __future__ import annotations

import ctypes
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

# The copied worker has no toolkit imports; keep its diagnostics available
# when imported by the server while remaining stdlib-only as a standalone file.
if __package__:
    from . import i18n as _i18n
else:
    class _Messages:
        @staticmethod
        def msg(_key, default, **params):
            return default.format(**params)
    _i18n = _Messages()

MANIFEST = 'release-manifest.json'
COMPONENTS = {'app.py', 'transfer_cli.py', 'Full Cleaner.bat',
              'Launch-Medieval2-GUI-Toolkit.bat', 'Install-Dependencies.bat',
              'Troubleshoot.bat', 'README.txt', 'LICENSE', 'NOTICE', 'unittransfer', 'web', 'vendor', 'runtime'}


class UpdateInProgress(RuntimeError):
    pass


def pid_alive(pid):
    if pid <= 0:
        return True  # Invalid owners must not permit stealing a lock.
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass
        return True
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        return ctypes.get_last_error() != 87  # Only a missing PID proves it is dead.
    try:
        return kernel.WaitForSingleObject(handle, 0) != 0
    finally:
        kernel.CloseHandle(handle)


def update_locked(root):
    lock = Path(root) / 'config/updates/install.lock'
    try:
        return pid_alive(int(lock.read_text(encoding='utf-8')))
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        return True  # Includes a worker still writing its PID.


@contextmanager
def update_lock(root):
    lock = Path(root) / 'config/updates/install.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            # Recheck identity so a recovered lock is not mistaken for the stale one.
            try:
                before = lock.stat()
                if update_locked(root):
                    raise UpdateInProgress(_i18n.msg('eng.updater.update_already_in_progress', 'Update already in progress'))
                if lock.stat() == before:
                    lock.unlink()
            except FileNotFoundError:
                pass
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def relative_file(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError(_i18n.msg('eng.updater.invalid_update_path', 'Invalid update path'))
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts):
        raise ValueError(_i18n.msg('eng.updater.invalid_update_path', 'Invalid update path'))
    if parts[0] not in COMPONENTS:
        raise ValueError(_i18n.msg('eng.updater.unmanaged_path', 'Package contains an unmanaged path: {path}', path=name))
    return Path(*parts)


def verify(root, expected=None, strict=False, allow_cache=True):
    root = Path(root).resolve()
    data = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not re.fullmatch(r'v?\d+\.\d+\.\d+', str(data.get('version', ''))):
        raise ValueError(_i18n.msg('eng.updater.invalid_release_manifest', 'Invalid release manifest'))
    if expected and data['version'].lstrip('v') != expected.lstrip('v'):
        raise ValueError(_i18n.msg('eng.updater.package_version_does_not_match_the_release', 'Package version does not match the release'))
    files = data.get('files')
    if not isinstance(files, dict) or not {'app.py', 'unittransfer/__init__.py', 'web/index.html', 'runtime/python.exe'} <= files.keys():
        raise ValueError(_i18n.msg('eng.updater.incomplete_portable_release', 'Incomplete portable release'))
    seen = set()
    for name, want in files.items():
        rel = relative_file(name)
        if name.lower() in seen or not re.fullmatch('[0-9a-f]{64}', str(want)):
            raise ValueError(_i18n.msg('eng.updater.invalid_release_file_hash', 'Invalid release file hash'))
        seen.add(name.lower())
        path = root / rel
        if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
            raise ValueError(_i18n.msg('eng.updater.updates_cannot_follow_linked_paths', 'Updates cannot follow linked paths'))
        if not path.resolve().is_relative_to(root) or not path.is_file() or digest(path) != want:
            raise ValueError(_i18n.msg('eng.updater.modified_path', 'Release files are missing or locally modified: {path}', path=name))
    if strict:
        for component in COMPONENTS:
            path = root / component
            if path.is_dir():
                actual = (p for p in path.rglob('*') if p.is_file())
            else:
                actual = [path] if path.is_file() else []
            for p in actual:
                rel = p.relative_to(root)
                cached = allow_cache and ('__pycache__' in rel.parts or p.suffix == '.pyc')
                if not cached and rel.as_posix() not in files:
                    raise ValueError(_i18n.msg('eng.updater.untracked_path', 'Untracked files in an application folder: {path}', path=rel.as_posix()))
    return data


def install(root, staged, version, backup, validate=None):
    """Replace only managed components; restore the previous set on failure."""
    with update_lock(Path(root).resolve()):
        return _install(root, staged, version, backup, validate)


def _install(root, staged, version, backup, validate=None):
    root, staged, backup = map(lambda p: Path(p).resolve(), (root, staged, backup))
    updates = root / 'config' / 'updates'
    if not staged.is_relative_to(updates) or not backup.is_relative_to(updates) or staged == backup:
        raise ValueError(_i18n.msg('eng.updater.update_paths_must_stay_inside_this_installation', 'Update paths must stay inside this installation'))
    if (root / '.git').exists() or (root.parent / '.git').exists():
        raise ValueError(_i18n.msg('eng.updater.a_source_checkout_is_never_updated_automatically', 'A source checkout is never updated automatically'))
    before = verify(root, strict=True)
    after = verify(staged, version, strict=True, allow_cache=False)
    if tuple(map(int, after['version'].lstrip('v').split('.'))) <= tuple(map(int, before['version'].lstrip('v').split('.'))):
        raise ValueError(_i18n.msg('eng.updater.update_must_be_newer_than_the_installed_version', 'Update must be newer than the installed version'))
    names = sorted({p.split('/')[0] for p in before['files']} | {p.split('/')[0] for p in after['files']}) + [MANIFEST]
    backup.mkdir(parents=True, exist_ok=False)
    moved, placed = [], []
    try:
        for name in names:
            target, source = root / name, staged / name
            # These paths have a fixed allowlist, resolved root and no links.
            if target.exists():
                os.replace(target, backup / name)
                moved.append(name)
            if source.exists():
                os.replace(source, target)
                placed.append(name)
        verify(root, version, strict=True)
        if validate:
            validate(root)
    except Exception:
        for name in reversed(placed):
            os.replace(root / name, staged / name)
        for name in reversed(moved):
            os.replace(backup / name, root / name)
        raise
    return backup


def wait_for_pid(pid, timeout=90):
    if os.name != 'nt':
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(.2)
        raise TimeoutError(_i18n.msg('eng.updater.the_old_toolkit_process_did_not_stop', 'The old toolkit process did not stop'))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:  # process has already exited
            return
        raise OSError(_i18n.msg('eng.updater.cannot_wait_for_the_toolkit_process', 'Cannot wait for the toolkit process'))
    try:
        if kernel.WaitForSingleObject(handle, int(timeout * 1000)) != 0:
            raise TimeoutError(_i18n.msg('eng.updater.the_old_toolkit_process_did_not_stop', 'The old toolkit process did not stop'))
    finally:
        kernel.CloseHandle(handle)


def main(job_path):
    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    root = Path(job['root']).resolve()
    try:
        with update_lock(root):
            _run_job(job, root)
    except UpdateInProgress:
        return
    # Release before starting the app: its launch guard checks the same lock.
    exe = root / 'runtime' / 'python.exe'
    args = [str(exe), str(root / 'app.py'), '--serve', '--port', str(int(job['port']))]
    if job.get('no_browser'):
        args.append('--no-browser')
    subprocess.Popen(args, cwd=root, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def _run_job(job, root):
    updates = root / 'config' / 'updates'
    state = updates / 'state.json'
    def report(phase, error=''):
        tmp = state.with_suffix('.tmp')
        tmp.write_text(json.dumps({'phase': phase, 'latest': job['version'], 'error': error}), encoding='utf-8')
        os.replace(tmp, state)
    try:
        wait_for_pid(int(job['pid']))
        def healthcheck(folder):
            result = subprocess.run([str(folder / 'runtime/python.exe'), str(folder / 'app.py'),
                                     '--check', '--port', str(int(job['port']))],
                                    cwd=folder, capture_output=True, timeout=90,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                raise RuntimeError(_i18n.msg('eng.updater.the_updated_toolkit_failed_its_startup_check_restored', 'The updated toolkit failed its startup check; restored the previous version'))
        _install(root, job['stage'], job['version'], job['backup'], validate=healthcheck)
        (updates / 'pending.json').unlink(missing_ok=True)
        report('installed')
    except Exception as exc:
        report('error', str(exc))
        # Failed updates must not retry on every launch.
        (updates / 'pending.json').unlink(missing_ok=True)


if __name__ == '__main__':
    main(sys.argv[1])
