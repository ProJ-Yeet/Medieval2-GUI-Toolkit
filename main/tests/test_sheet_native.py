import copy,unittest
from unittest.mock import patch
from unittransfer import buildings,config,edu,sheet_native,sheet_ops,unit_sheets as sheets
from unittransfer.mod import Mod
from unittransfer.transfer import undo
from tests import test_sheet_pipeline as fixture

class NativeTests(unittest.TestCase):
 def setUp(self):
  fixture.PipelineTests.setUp(self)
  text=fixture.EDU.replace('class heavy','class heavy\nstat_pri 5, 2, no, 0, 0, melee, simple, piercing, sword, 20, 1\nattributes hardy, unknown_custom',1)
  self.original_edu=text.replace('\n','\r\n').encode('latin-1');self.mod.edu_path.write_bytes(self.original_edu)
  self.mod=Mod(self.data.parent)
 def stage(self,uid='Guard',column='attack',value=9):
  self.project,_=sheet_ops.stage_operation(self.mod,self.project,[uid],column,'set',value)
 def test_preview_and_apply_use_existing_patcher_then_log_undo(self):
  self.stage();before=sheets.revision(self.project);p=sheet_native.preview(self.mod,self.project)
  self.assertEqual(p['units'],1);self.assertEqual(self.mod.edu_path.read_bytes(),self.original_edu)
  rec=sheet_native.apply(self.mod,self.project,p['plan_token'])
  after=self.mod.edu_path.read_bytes();self.assertIn(b'stat_pri 9, 2, no, 0, 0, melee, simple, piercing, sword, 20, 1\r\n',after)
  self.assertIn(b'attributes hardy, unknown_custom\r\n',after);self.assertEqual(before,sheets.revision(self.project))
  self.assertEqual(rec['mode'],'edit');undo(rec['id']);self.assertEqual(self.mod.edu_path.read_bytes(),self.original_edu)
 def test_stale_unit_after_staging_refuses_even_a_new_preview(self):
  self.stage();self.mod.edu_path.write_bytes(self.original_edu.replace(b'stat_pri 5',b'stat_pri 6'))
  with self.assertRaises(sheets.SheetError):sheet_native.preview(self.mod,self.project)
 def test_changed_draft_refuses_old_apply_token(self):
  self.stage();p=sheet_native.preview(self.mod,self.project);self.project['draft']['Guard']['attack']=10
  with self.assertRaises(sheets.SheetError):sheet_native.apply(self.mod,self.project,p['plan_token'])
  self.assertEqual(self.mod.edu_path.read_bytes(),self.original_edu)
 def test_stale_draft_can_be_loaded_and_discarded(self):
  self.stage();sheets.save_project(self.mod,self.project)
  self.mod.edu_path.write_bytes(self.original_edu.replace(b'stat_pri 5',b'stat_pri 6'))
  fresh=Mod(self.mod.root);d=sheets.service(fresh,'load');self.assertEqual(d['stale_drafts'],['Guard'])
  self.assertEqual(next(r for r in d['table']['rows'] if r['id']=='Guard')['attack'],6)
  project=d['project'];project['draft']={};project['draft_sources']={}
  saved=sheets.service(fresh,'save',{'project':project,'revision':d['revision'],'source_token':d['source_token']})
  self.assertEqual(saved['stale_drafts'],[])
 def test_service_clears_draft_after_apply_and_keeps_annotations(self):
  self.stage();sheets.save_project(self.mod,self.project);d=sheets.service(self.mod,'load');body={'revision':d['revision'],'source_token':d['source_token']}
  p=sheets.service(self.mod,'native_preview',body);result=sheets.service(self.mod,'native_apply',{**body,'plan_token':p['plan_token']})
  saved=sheets.load_project(self.mod);self.assertEqual(saved['draft'],{});self.assertEqual(saved['units']['Guard']['annotations']['Tier'],'T1')
  self.assertTrue(result['record']['applied'])
 def eop_unit(self):
  path=self.data.parent/'eopData/units/extra.txt';path.parent.mkdir(parents=True)
  text=edu.parse_text(self.original_edu.decode()).units[0].raw.replace('type Guard','type Extra')
  path.write_bytes(text.encode('latin-1'));self.mod=Mod(self.data.parent);return path
 def test_mixed_operations_undo_redo_never_write_mod_files(self):
  # Native sheet undo/redo restores project snapshots, just like the UI.
  sheets.service(self.mod, 'load')
  def snapshot():
   return {str(path.relative_to(self.mod.root)):(path.read_bytes(), path.stat().st_mtime_ns)
    for path in self.mod.root.rglob('*') if path.is_file()}
  original = snapshot()
  past = []
  edits = [
   ('operate', {'ids':['Guard','Horse'], 'column':'unit_size','operation':'add','value':2}),
   ('paste', {'cells':[{'id':'Guard','column':'attack','value':9},
    {'id':'Horse','column':'Tier','value':'T3'},
    {'id':'Guard','column':'attributes','value':['hardy','unknown_custom','new_tag']}]}),
  ]
  def request(action, body):
   current = sheets.service(self.mod, 'load')
   return sheets.service(self.mod, action, {
    'revision':current['revision'], 'source_token':current['source_token'], **body})
  for action, edit in edits:
   past.append(copy.deepcopy(sheets.load_project(self.mod)))
   path = sheets.project_path(self.mod)
   before = path.read_bytes()
   log = config.load_log()
   preview = request(action, {**edit, 'dry_run':True})
   self.assertEqual(path.read_bytes(), before)
   self.assertEqual(config.load_log(), log)
   self.assertEqual(snapshot(), original)
   result = request(action, edit)
   self.assertEqual(preview['changes'], result['changes'])
   self.assertEqual(snapshot(), original)
  final = copy.deepcopy(result['project'])
  fields, _ = sheet_ops.field_changes(self.mod.edu.units[0], final['draft']['Guard'])
  self.assertEqual(fields['stat_pri'], '9, 2, no, 0, 0, melee, simple, piercing, sword, 20, 1')
  self.assertIn('unknown_custom', fields['attributes'])
  future = []
  for previous in reversed(past):
   future.append(copy.deepcopy(sheets.load_project(self.mod)))
   restored = request('save', {'project':previous})
   self.assertEqual(restored['project'], previous)
   self.assertEqual(snapshot(), original)
  for following in reversed(future):
   restored = request('save', {'project':following})
   self.assertEqual(restored['project'], following)
   self.assertEqual(snapshot(), original)
  self.assertEqual(restored['project'], final)
 def test_eop_keeps_own_file_and_uses_external_backup_undo(self):
  path=self.eop_unit();original=path.read_bytes();self.stage('Extra');p=sheet_native.preview(self.mod,self.project)
  rec=sheet_native.apply(self.mod,self.project,p['plan_token']);self.assertNotEqual(path.read_bytes(),original)
  self.assertEqual(self.mod.edu_path.read_bytes(),self.original_edu);self.assertTrue(rec['manifest']['ext_backed_up'])
  undo(rec['id']);self.assertEqual(path.read_bytes(),original)
 def test_multi_file_failure_rolls_back_written_files(self):
  path=self.eop_unit();original=path.read_bytes();self.stage();self.stage('Extra');p=sheet_native.preview(self.mod,self.project)
  writer=buildings._atomic_edb_write;calls=[]
  def fail_second(target,blob):
   calls.append(target)
   if len(calls)==2:raise OSError('simulated second file write failure')
   writer(target,blob)
  with patch.object(buildings,'_atomic_edb_write',side_effect=fail_second):
   with self.assertRaises(OSError):sheet_native.apply(self.mod,self.project,p['plan_token'])
  self.assertEqual(self.mod.edu_path.read_bytes(),self.original_edu);self.assertEqual(path.read_bytes(),original)

if __name__=='__main__':unittest.main()
