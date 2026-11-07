"""Automatic updater regression tests. Never download or replace a real install."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from unittransfer import updater, update_worker as worker


def package(folder, version):
    folder.mkdir(parents=True, exist_ok=True)
    files = {'app.py': 'print("fixture")', 'unittransfer/__init__.py': '__version__ = "'+version+'"',
             'web/index.html': '<html>'+version+'</html>', 'runtime/python.exe': 'test runtime '+version,
             'runtime/python312.zip': 'test stdlib', 'Launch-Medieval2-GUI-Toolkit.bat': '@echo fixture'}
    for name, body in files.items():
        p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
    manifest={'schema':1,'version':version,'files':{n:worker.digest(folder/n) for n in files}}
    (folder/worker.MANIFEST).write_text(json.dumps(manifest),encoding='utf-8')
    return folder


def archive(folder):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob('*'):
            if p.is_file():z.write(p,'Medieval2-GUI-Toolkit/'+p.relative_to(folder).as_posix())
    return buf.getvalue()


def release(body, tag='v2.0.0'):
    name='Medieval2-GUI-Toolkit-'+tag+'.zip'
    return {'tag_name':tag,'draft':False,'prerelease':False,'assets':[{'name':name,'size':len(body),
       'browser_download_url':'https://github.com/'+updater.REPO+'/releases/download/'+tag+'/'+name,
       'digest':'sha256:'+hashlib.sha256(body).hexdigest()}]}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=package(self.base/'install','v1.0.0')
        self.new=package(self.base/'new','v2.0.0');self.body=archive(self.new)
        self.stage=self.root/'config/updates/stage-test';self.backup=self.root/'config/updates/rollback-test'
        self.settings=patch.object(updater.config,'load_settings',return_value={});self.settings.start();self.addCleanup(self.settings.stop)

    def test_numeric_version_order_and_unstable_rejection(self):
        self.assertGreater(updater.version('v2.10.0'),updater.version('v2.9.9'))
        self.assertIsNone(updater.select_release(release(self.body),'v2.0.0'))
        d=release(self.body);d['prerelease']=True
        self.assertIsNone(updater.select_release(d,'v1.0.0'))
        with self.assertRaises(ValueError):updater.version('beta-2026-11-06')

    def test_only_official_asset_with_checksum_is_selected(self):
        d=release(self.body);a=updater.select_release(d,'v1.0.0');self.assertEqual(a['version'],'v2.0.0')
        d['assets'][0]['browser_download_url']='https://example.com/other.zip'
        with self.assertRaises(ValueError):updater.select_release(d,'v1.0.0')
        d=release(self.body);d['assets'][0]['digest']=None
        with self.assertRaises(ValueError):updater.select_release(d,'v1.0.0')

    def test_valid_package_and_changed_files(self):
        self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')
        (self.root/'app.py').write_text('local edit')
        with self.assertRaises(ValueError):worker.verify(self.root)

    def test_extra_user_file_in_managed_folder_prevents_overwrite(self):
        (self.root/'web/user-notes.txt').write_text('keep this')
        with self.assertRaises(ValueError):worker.verify(self.root,strict=True)

    def test_archive_traversal_case_duplicates_and_symlinks_are_rejected(self):
        for names in [('Medieval2-GUI-Toolkit/../config/settings.json',),
                      ('Medieval2-GUI-Toolkit/web/X.txt','Medieval2-GUI-Toolkit/web/x.txt'),
                      ('Medieval2-GUI-Toolkit/C:/bad.txt',)]:
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:
                for n in names:z.writestr(n,'bad')
            with self.assertRaises(ValueError):updater.unpack(io.BytesIO(b.getvalue()),self.base/str(len(list(self.base.iterdir()))),'v2.0.0')
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            i=zipfile.ZipInfo('Medieval2-GUI-Toolkit/web/link');i.create_system=3;i.external_attr=0o120777<<16;z.writestr(i,'target')
        with self.assertRaises(ValueError):updater.unpack(io.BytesIO(b.getvalue()),self.base/'linked','v2.0.0')

    def test_staging_verifies_manifest_version(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        self.assertEqual(worker.verify(self.stage)['version'],'v2.0.0')
        with self.assertRaises(ValueError):updater.unpack(io.BytesIO(self.body),self.base/'wrong','v3.0.0')

    def test_install_preserves_settings_sessions_and_unmanaged_files(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        personal=self.root/'config/armory/sessions/guard.json';personal.parent.mkdir(parents=True,exist_ok=True);personal.write_text('personal session')
        (self.root/'my-notes.txt').write_text('personal notes')
        worker.install(self.root,self.stage,'v2.0.0',self.backup)
        self.assertEqual(worker.verify(self.root)['version'],'v2.0.0')
        self.assertEqual(personal.read_text(),'personal session');self.assertEqual((self.root/'my-notes.txt').read_text(),'personal notes')
        self.assertEqual(worker.verify(self.backup)['version'],'v1.0.0')

    def test_failed_startup_check_restores_old_release(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        def fail(_):raise RuntimeError('startup failed')
        with self.assertRaises(RuntimeError):worker.install(self.root,self.stage,'v2.0.0',self.backup,validate=fail)
        self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')

    def test_install_lock_blocks_another_process_and_launch(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        updates=self.root/'config/updates'
        (updates/'pending.json').write_text(json.dumps({'stage':str(self.stage),'version':'v2.0.0'}))
        code=('from unittransfer import update_worker as w; import sys; '
              'w.install(*sys.argv[1:])')
        def competing_install(_):
            result=subprocess.run([sys.executable,'-c',code,str(self.root),str(self.stage),'v2.0.0',str(updates/'rollback-second')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Update already in progress',result.stderr)
            self.assertFalse((updates/'rollback-second').exists())
            self.assertEqual(worker.verify(self.root)['version'],'v2.0.0')
            with patch.object(updater,'__version__','v1.0.0'),patch.object(updater.subprocess,'Popen') as spawn:
                self.assertTrue(updater.apply_on_launch(self.root,8756))
                spawn.assert_not_called()
        worker.install(self.root,self.stage,'v2.0.0',self.backup,validate=competing_install)
        self.assertFalse((updates/'install.lock').exists())

    def test_lock_is_released_after_rollback_and_dead_owner_is_recovered(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        lock=self.root/'config/updates/install.lock'
        # Use a real PID that has exited, rather than assuming an arbitrary PID is dead.
        child=subprocess.Popen([sys.executable,'-c','pass']);child.wait()
        lock.write_text(str(child.pid),encoding='utf-8')
        def fail(_):
            self.assertEqual(lock.read_text(encoding='utf-8'),str(os.getpid()))
            raise RuntimeError('startup failed')
        with self.assertRaisesRegex(RuntimeError,'startup failed'):
            worker.install(self.root,self.stage,'v2.0.0',self.backup,validate=fail)
        self.assertFalse(lock.exists())
        self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')

    def test_duplicate_worker_leaves_pending_and_state_untouched(self):
        updates=self.root/'config/updates';updates.mkdir(parents=True)
        lock=updates/'install.lock';lock.write_text(str(os.getpid()),encoding='utf-8')
        pending=updates/'pending.json';pending.write_text('keep pending')
        state=updates/'state.json';state.write_text('keep state')
        job=updates/'job.json';job.write_text(json.dumps({'root':str(self.root),'pid':os.getpid(),'version':'v2.0.0','port':8756,'stage':str(self.stage),'backup':str(self.backup)}))
        with patch.object(worker,'wait_for_pid'),patch.object(worker.subprocess,'Popen') as spawn:
            worker.main(job)
            spawn.assert_not_called()
        self.assertEqual(pending.read_text(),'keep pending');self.assertEqual(state.read_text(),'keep state')
        self.assertEqual(lock.read_text(),str(os.getpid()))

    def test_worker_releases_lock_before_restarting_app(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        updates=self.root/'config/updates'
        job=updates/'job.json';job.write_text(json.dumps({'root':str(self.root),'pid':os.getpid(),'version':'v2.0.0','port':8756,'stage':str(self.stage),'backup':str(self.backup)}))
        def restart(*args,**kwargs):
            self.assertFalse(worker.update_locked(self.root),'restarted app must not exit because of the worker lock')
            self.assertEqual(json.loads((updates/'state.json').read_text())['phase'],'installed')
        with patch.object(worker,'wait_for_pid'),patch.object(worker.subprocess,'run') as check,patch.object(worker.subprocess,'Popen',side_effect=restart):
            check.return_value.returncode=0
            worker.main(job)

    def test_interrupted_replacement_restores_old_release(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        original=worker.os.replace
        def replace(src,dst):
            if Path(src)==self.stage/'web':raise PermissionError('simulated Windows lock')
            return original(src,dst)
        with patch.object(worker.os,'replace',side_effect=replace):
            with self.assertRaises(PermissionError):worker.install(self.root,self.stage,'v2.0.0',self.backup)
        self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')

    def test_background_check_downloads_and_stages_without_installing(self):
        m=updater.UpdateManager(self.root,current='v1.0.0')
        with patch.object(updater,'open_url',side_effect=[io.BytesIO(json.dumps(release(self.body)).encode()),io.BytesIO(self.body)]):m._check()
        self.assertEqual(m.snapshot()['phase'],'ready');self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')
        self.assertEqual(m._read('pending.json')['version'],'v2.0.0')

    def test_hash_failure_does_not_stage_an_update(self):
        m=updater.UpdateManager(self.root,current='v1.0.0');d=release(self.body);d['assets'][0]['digest']='sha256:'+'0'*64
        with patch.object(updater,'open_url',side_effect=[io.BytesIO(json.dumps(d).encode()),io.BytesIO(self.body)]):m._check()
        self.assertEqual(m.snapshot()['phase'],'error');self.assertFalse((m.folder/'pending.json').exists())

    def test_offline_check_is_nonfatal_and_releases_busy_flag(self):
        m=updater.UpdateManager(self.root,current='v1.0.0');m.busy=True
        with patch.object(updater,'open_url',side_effect=OSError('offline')):m._check()
        self.assertEqual(m.snapshot()['phase'],'error');self.assertFalse(m.busy)

    def test_source_checkout_never_downloads_or_applies(self):
        (self.root/'.git').mkdir()
        m=updater.UpdateManager(self.root,current='v1.0.0')
        with patch.object(updater,'open_url',return_value=io.BytesIO(json.dumps(release(self.body)).encode())) as fetch:m._check()
        self.assertEqual(fetch.call_count,1);self.assertEqual(m.snapshot()['phase'],'source')
        self.assertFalse(updater.apply_on_launch(self.root,8756))

    def test_disabled_auto_update_checks_but_does_not_download(self):
        m=updater.UpdateManager(self.root,current='v1.0.0')
        with patch.object(updater.config,'load_settings',return_value={'auto_updates':False}),patch.object(updater,'open_url',return_value=io.BytesIO(json.dumps(release(self.body)).encode())) as fetch:m._check()
        self.assertEqual(fetch.call_count,1);self.assertEqual(m.snapshot()['phase'],'available')

    def test_pending_install_uses_private_runtime_and_does_not_touch_current_files(self):
        updater.unpack(io.BytesIO(self.body),self.stage,'v2.0.0')
        (self.root/'config/updates/pending.json').write_text(json.dumps({'stage':str(self.stage),'version':'v2.0.0'}))
        with patch.object(updater,'__version__','v1.0.0'),patch.object(updater.subprocess,'Popen') as spawn:
            self.assertTrue(updater.apply_on_launch(self.root,8757,True))
        exe,script,job=map(Path,spawn.call_args.args[0]);self.assertTrue(exe.is_file());self.assertTrue(script.is_file())
        data=json.loads(job.read_text());self.assertEqual(data['port'],8757);self.assertTrue(data['no_browser'])
        self.assertNotEqual(exe,self.root/'runtime/python.exe');self.assertEqual(worker.verify(self.root)['version'],'v1.0.0')

    def test_path_allowlist(self):
        for n in ('../x','config/settings.json','web/../x','web/a:stream','runtime\\bad','web/file.'):
            with self.assertRaises(ValueError):worker.relative_file(n)

    def test_release_builder_emits_verifiable_manifest(self):
        script=Path(__file__).resolve().parents[1]/'dev/release/build_release.py'
        spec=importlib.util.spec_from_file_location('build_release_test',script);br=importlib.util.module_from_spec(spec);spec.loader.exec_module(br)
        (self.new/worker.MANIFEST).unlink();br.write_update_manifest(self.new)
        self.assertEqual(worker.verify(self.new)['version'],'v2.0.0')

    def test_release_stage_top_level_names_are_managed(self):
        script=Path(__file__).resolve().parents[1]/'dev/release/build_release.py'
        spec=importlib.util.spec_from_file_location('build_release_test',script);br=importlib.util.module_from_spec(spec);spec.loader.exec_module(br)
        docs=self.base/'docs';docs.mkdir();br.write_docs(docs,portable=True)
        names=set(br.INCLUDE_FILES)|set(br.INCLUDE_DIRS)|{p.name for p in docs.iterdir()}|{'runtime'}
        self.assertLessEqual(names,worker.COMPONENTS)

    def test_staged_unlisted_bytecode_is_rejected(self):
        (self.new/'unittransfer/unknown.pyc').write_bytes(b'not in manifest')
        with self.assertRaises(ValueError):updater.unpack(io.BytesIO(archive(self.new)),self.stage,'v2.0.0')

    def test_unattended_test_mode_does_not_start_network_loop(self):
        m=updater.UpdateManager(self.base/'source',current='v1.0.0')
        with patch.dict(updater.os.environ,{'UT_NO_UPDATES':'1'}),patch.object(updater.threading,'Thread') as thread:m.start()
        thread.assert_not_called()

    def test_malformed_pending_record_is_reported(self):
        (self.root/'config/updates').mkdir(parents=True)
        (self.root/'config/updates/pending.json').write_text('{"version":"broken"}')
        self.assertEqual(updater.UpdateManager(self.root,current='v1.0.0').snapshot()['phase'],'error')

    def test_update_settings_route_rejects_non_boolean(self):
        from types import SimpleNamespace
        from unittransfer.server import Handler
        h=SimpleNamespace(path='/api/updates/settings',_read_body=lambda:{'enabled':'yes'},_err=lambda code,msg:code)
        self.assertEqual(Handler.do_POST(h),400)

    def test_check_endpoint_uses_fixed_updater_not_client_url(self):
        from types import SimpleNamespace
        from unittransfer.server import Handler
        h=SimpleNamespace(path='/api/updates/check',_read_body=lambda:{'url':'https://example.com/unsafe'},_json=lambda result:result)
        fake=SimpleNamespace(check=lambda force=False:{'forced':force})
        with patch.object(updater,'manager',return_value=fake):result=Handler.do_POST(h)
        self.assertTrue(result['forced'])


if __name__=='__main__':unittest.main()
