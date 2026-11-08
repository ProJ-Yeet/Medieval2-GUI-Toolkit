"""Phase 105 fixture-only regressions, written before implementation."""
import copy
import json
import threading
import urllib.request
import urllib.error
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_builder_designer as designer_tests
from tests.test_builder_calculator import design
from unittransfer import builder_contract as contract, unit_sheets as sheets, sheet_interchange


TEXT = designer_tests.TEXT

class ProjectTests(unittest.TestCase):
 setUp = designer_tests.DesignerTests.setUp
 call = designer_tests.DesignerTests.call
 def test_upstream_examples_and_roundtrip(self):
  from unittransfer import builder_projects as projects
  for fields in [dict(pri_preset='arming_sword'),dict(pri_preset='self_bow',**{'class':'missile'}),dict(category='cavalry',pri_preset='horseman_sword'),dict(pri_preset='great_sword')]:
   raw={'schema':'combat-reforged-builder','version':1,'fields':{'unit_category':'Martial Nobility','quality':'Average',**fields,'pri_base_atk':'7','hide_forest_override':False,'unit_custom_attrs':'hook_drag'},'presets':{'pri':{'custom':{'atk':19,'roles':['any'],'unknown':'keep'}}},'weapon_categories':{'sword_cut':{'atk':9}},'unit':{'attack':999},'future':{'text':'<script>kept as data</script>'}}
   original=copy.deepcopy(raw)
   r=self.call('import',text=json.dumps(raw))
   d=r['design'];self.assertEqual(d['overrides']['inputs']['pri_base_atk'],'7')
   self.assertIs(d['overrides']['inputs']['hide_forest_override'],False)
   self.assertEqual(d['metadata']['upstream'],original)
   self.assertEqual(d['presets']['pri']['custom']['atk'],19)
   self.assertEqual(self.call('preview',design=d)['native']['attack'],9)
   exported=self.call('export',design=d,format='upstream')
   again=self.call('import',text=exported['text'])['design']
   self.assertEqual(contract.effective_inputs(again),contract.effective_inputs(d))
   self.assertEqual(json.loads(exported['text'])['future'],raw['future'])
   native=self.call('export',design=d,format='project')
   self.assertEqual(json.loads(native['text'])['schema'],projects.SCHEMA)
   self.assertEqual(self.call('import',text=native['text'])['design'],d)
   self.assertEqual(raw,original)
  self.assertEqual(self.file.read_text(),TEXT)
  self.assertFalse(sheets.project_path(self.mod).exists())
 def test_native_presets_save_load_and_exports(self):
  d=design(pri_preset='arming_sword',pri_attr='sp, ap, hook_drag',unit_custom_attrs='unknown_ability')
  d['presets']={'pri':{'arming_sword':{'atk':11}}};d['metadata']={'unknown':{'keep':[False,0,'']}}
  d['overrides']['native']={'attack':0}
  for fmt in ('project','presets','edu','csv'):
   r=self.call('export',design=d,format=fmt)
   self.assertIsInstance(r['text'],str);self.assertIn('mime',r)
   if fmt=='project':self.assertEqual(self.call('import',text=r['text'])['design'],d)
   if fmt=='presets':self.assertEqual(self.call('import',design=d,text=r['text'])['design'],d)
   if fmt=='edu':
    self.assertIn('stat_pri 0,',r['text']);self.assertNotIn('hook_drag',r['text']);self.assertNotIn('sp,',r['text'])
   if fmt=='csv':
    self.assertIn('attack',r['text']);self.assertEqual(len(sheet_interchange.read_tables('csv',r['text'])),1)
  r=self.call('load');self.call('save',design=d,revision=r['revision'],source_token=r['source_token'])
  self.assertEqual(self.call('load')['design'],d)
  before=sheets.project_path(self.mod).read_bytes()
  for raw in ['{',json.dumps({'schema':'m2-builder-project','version':2}),json.dumps({'schema':'other','version':1}),json.dumps({'schema':'combat-reforged-builder','version':True,'fields':{}}),json.dumps({'schema':'combat-reforged-builder','version':1,'fields':{'unit_category':'missing'}}),'{"schema":"x","schema":"y"}']:
   with self.assertRaises(contract.ContractError):self.call('import',text=raw)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
  with self.assertRaises(contract.ContractError):self.call('export',design={'version':2},format='project')
  with self.assertRaises(contract.ContractError):self.call('export',design=d,format='unsupported')
  self.assertEqual(self.file.read_text(),TEXT)
 def test_csv_reuses_sheet_writer_and_escaping(self):
  d=design(pri_base_atk=7)
  with patch.object(sheet_interchange,'write_csv',wraps=sheet_interchange.write_csv) as writer:
   exported=self.call('export',unit='Guard',design=d,format='csv');writer.assert_called_once()
   self.assertEqual(sheet_interchange.read_tables('csv',exported['text'])[0]['cells']['A2']['value'],'Guard')
  table={'cells':{'A1':{'value':'=HYPERLINK("bad")'},'B1':{'value':'hello, "world"\nnext'}}}
  text=sheet_interchange.write_csv(table)
  cells=sheet_interchange.read_tables('csv',text)[0]['cells']
  self.assertTrue(cells['A1']['value'].startswith("'="));self.assertEqual(cells['B1']['value'],'hello, "world"\nnext')
 def test_upstream_blanks_and_custom_active_preset(self):
  raw={'schema':'combat-reforged-builder','version':1,'fields':{'unit_category':'Martial Nobility','pri_preset':'custom','sec_preset':'arming_sword','sec_base_atk':'','pri_category':'','quality':'Standard'},'presets':{'pri':{'custom':{'atk':10,'roles':['any'],'twohand':False,'attr':'sp, hook_drag'}}}}
  d=self.call('import',text=json.dumps(raw))['design']
  self.assertEqual(d['overrides']['inputs']['sec_base_atk'],'')
  r=self.call('preview',design=d)
  self.assertEqual(r['native']['attack'],12)
  self.assertNotIn('sec_attack',r['native'])  # Existing contract omits absent weapons.
  self.assertNotIn('hook_drag',r['edu'])
 def test_profile_mismatch_and_bad_presets_leave_saved_draft(self):
  d=design(pri_base_atk=7);r=self.call('load')
  self.call('save',design=d,revision=r['revision'],source_token=r['source_token'])
  before=sheets.project_path(self.mod).read_bytes()
  for packet in [dict(schema='m2-builder-presets',version=1,profile={'id':'native','revision':'1'},presets={}),dict(schema='combat-reforged-builder',version=1,fields={},presets={'pri':{'bad':[]}})]:
   with self.assertRaises(contract.ContractError):self.call('import',text=json.dumps(packet),design=d)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
 def test_portable_http_and_version_message(self):
  from unittransfer.server import Handler,_Server
  class H(Handler):pass
  H.registry=SimpleNamespace(get=lambda name:self.mod)
  server=_Server(('127.0.0.1',0),H);threading.Thread(target=server.serve_forever,daemon=True).start()
  self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  def post(action,body):
   req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/builder/'+action,data=json.dumps(dict(mod='Fixture',**body)).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req) as r:return json.load(r)
  out=post('export',dict(design=design(pri_base_atk=7),format='project'))
  self.assertIn('design',post('import',dict(text=out['text'])))
  with self.assertRaises(urllib.error.HTTPError) as error:post('import',dict(text='{"schema":"m2-builder-project","version":2}'))
  self.assertEqual(json.load(error.exception)['message_id'],'builder.project_version')


if __name__=='__main__':unittest.main()
