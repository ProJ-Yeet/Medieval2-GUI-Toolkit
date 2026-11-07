import base64,copy,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from unittransfer import buildings,config,edb_balance as balance,unit_sheets as sheets
from unittransfer.mod import Mod
from unittransfer.transfer import undo
from tests import test_edb_balance as fixture
EDB,EDU=fixture.EDB,fixture.EDU

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.data=self.root/'fixture/data';self.data.mkdir(parents=True)
  (self.data/'export_descr_unit.txt').write_bytes(EDU.encode('latin-1'))
  self.original=EDB.replace('keep this','café').replace('\n','\r\n').encode('latin-1')
  (self.data/'export_descr_buildings.txt').write_bytes(self.original)
  self.mod=Mod(self.data.parent)
  for key,value in [('CONFIG_DIR',self.root/'config'),('BACKUP_DIR',self.root/'config/backups'),('LOG_PATH',self.root/'config/transfers.json'),('SETTINGS_PATH',self.root/'config/settings.json')]:
   p=patch.object(config,key,value);p.start();self.addCleanup(p.stop)
  helper=fixture.BalanceTests();helper.setUp();self.project=helper.p
  sheets.save_project(self.mod,self.project)
 def body(self):
  d=sheets.service(self.mod,'load');return {'revision':d['revision'],'source_token':d['source_token']}
 def test_export_complete_bundle_and_intermediates_is_read_only(self):
  body=self.body();result=sheets.service(self.mod,'balance_export',{**body,'intermediate':True})
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['text']))) as z:
   self.assertIn('export_descr_buildings_new.txt',z.namelist());self.assertIn('export_descr_buildings_r.txt',z.namelist())
   for stage in balance.STAGES:
    all_=json.loads(z.read('logs/'+stage+'_all.json'));issues=json.loads(z.read('logs/'+stage+'_skip_error.json'))
    self.assertEqual(len(all_),4);self.assertEqual(issues,[e for e in all_ if e['status'] in ('invalid','skipped')])
   self.assertIn(b'caf\xe9\r\n',z.read('export_descr_buildings_new.txt'))
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_apply_then_log_undo_restores_exact_bytes(self):
  body=self.body();preview=sheets.service(self.mod,'balance_preview',body)
  result=sheets.service(self.mod,'balance_apply',{**body,'stages':preview['stages'],'plan_token':preview['plan_token']})
  self.assertNotEqual(self.mod.edb_path.read_bytes(),self.original)
  record=result['record'];self.assertEqual(record['manifest']['backed_up'],['export_descr_buildings.txt'])
  self.assertEqual(config.load_log()[0]['id'],record['id'])
  undo(record['id']);self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_external_edb_edit_refuses_stale_apply(self):
  preview=balance.preview(self.mod,self.project)
  self.mod.edb_path.write_bytes(self.original+b'; external\r\n')
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original+b'; external\r\n')
 def test_external_edu_edit_refuses_stale_apply_even_if_cached(self):
  preview=balance.preview(self.mod,self.project)
  self.mod.edu_path.write_bytes(EDU.replace('infantry','cavalry').encode())
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_changed_rules_or_stages_refuse_stale_apply(self):
  preview=balance.preview(self.mod,self.project)
  p=copy.deepcopy(self.project);p['rules']['replenish'][0]['Human_Earliest']='12'
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,p,None,preview['plan_token'])
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,['pool'],preview['plan_token'])
 def test_failed_replace_leaves_original_and_no_temporary_file(self):
  preview=balance.preview(self.mod,self.project)
  with patch.object(buildings.os,'replace',side_effect=OSError('blocked')):
   with self.assertRaises(OSError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original);self.assertEqual(list(self.data.glob('*.tmp')),[])
 def test_failed_log_write_rolls_back_the_document(self):
  preview=balance.preview(self.mod,self.project)
  with patch.object(config,'append_log',side_effect=OSError('full disk')):
   with self.assertRaises(OSError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_invalid_profile_import_is_transactional(self):
  body=self.body();before=sheets.load_project(self.mod);bad=copy.deepcopy(before);bad['balance_profile']={'city_multiplier':'nan'}
  with self.assertRaises(sheets.SheetError):sheets.service(self.mod,'save',{**body,'project':bad})
  self.assertEqual(sheets.load_project(self.mod),before)
 def test_recruitment_queries_retain_condition_and_classification(self):
  d=sheets.service(self.mod,'query',{'view':'recruitment','where':{'all':[{'column':'building','op':'eq','value':'barracks'},{'column':'Unit Race','op':'eq','value':'Human'},{'column':'maximum','op':'lt','value':1}]}})
  self.assertEqual(d['table']['total'],1);self.assertEqual(d['table']['rows'][0]['unit'],'Horse')

if __name__=='__main__':unittest.main()
