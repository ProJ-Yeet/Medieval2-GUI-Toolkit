"""Phase 104 fixture-only service and HTTP regressions, written before implementation."""
import copy
import json
import shutil
import uuid
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittransfer import edu, unit_sheets as sheets, builder_contract as contract
from tests.test_builder_calculator import design

TEXT = """type Guard
dictionary guard
category infantry
class heavy
soldier guard, 60, 0, 1
stat_pri 5, 2, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_sec 0, 0, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_pri_armour 1, 2, 3, metal
stat_mental 5, normal, trained
stat_cost 1, 100, 50, 10, 10, 200, 1, 1
formation 1, 1, 2, 2, 4, square
stat_ground 0, 0, 0, 0
ownership england
; keep this comment
"""

class DesignerTests(unittest.TestCase):
 def setUp(self):
  from unittransfer import builder_designer
  self.service=builder_designer.service
  self.root=Path(__file__).resolve().parents[1]/'.tmp'/('designer_'+uuid.uuid4().hex)
  self.root.mkdir(mode=0o777,parents=True)
  self.addCleanup(shutil.rmtree,self.root)
  self.mod=SimpleNamespace(root=self.root/'mod',data=self.root/'mod/data',edu=edu.parse_text(TEXT),m2ex=False,eop_dirs=[])
  self.mod.data.mkdir(mode=0o777,parents=True)
  self.file=self.mod.data/'export_descr_unit.txt';self.file.write_text(TEXT)
  p=patch.object(sheets.config,'CONFIG_DIR',self.root/'config');p.start();self.addCleanup(p.stop)
 def call(self,action,**body):return self.service(self.mod,action,body)
 def test_load_does_not_infer_profile_or_write(self):
  r=self.call('load',unit='Guard')
  self.assertIsNone(r['design']);self.assertIn('pri',r['tables'])
  self.assertEqual(r['native']['attack'],5)
  self.assertFalse(sheets.project_path(self.mod).exists())
 def test_four_examples_preview_shared_projection_no_mod_writes(self):
  cases=[design(pri_preset='arming_sword'),design(pri_preset='self_bow',sec_preset='arming_sword',**{'class':'missile'}),design(pri_preset='horseman_sword',category='cavalry',horse_barding='plate'),design(pri_category='greatsword',pri_base_atk=8,pri_twohand=True,offhand='large')]
  for d in cases:
   before=copy.deepcopy(d)
   r=self.call('preview',design=d,unit='Guard')
   self.assertGreater(r['native']['attack'],0)
   self.assertIn('attack',r['explanations']);self.assertIn('; keep this comment',r['edu'])
   self.assertEqual(int(sheets.fields_of(edu.parse_text(r['edu']).units[0])['stat_pri'].split(',')[0]),r['native']['attack'])
   self.assertEqual(d,before)
  self.assertEqual(r['native']['shield'],0)
  self.assertEqual(self.file.read_text(),TEXT)
  self.assertFalse(sheets.project_path(self.mod).exists())
 def test_save_reopen_both_targets_preserve_packet_and_project(self):
  project=sheets.empty_project();project['units']['Guard']={'annotations':{'Tier':'T1'},'extra':{'note':'keep'}}
  project['draft']={'Guard':{'attack':9}};project['views']['keep']={};sheets.save_project(self.mod,project)
  d=design(pri_preset='arming_sword');d['presets']={'pri':{'arming_sword':{'atk':19}}}
  d['overrides']['inputs']={'pri_base_atk':7,'cost_construct':100,'hide_forest_override':False}
  d['overrides']['native']={'attack':0,'attributes':['sp']}
  for unit in ('Guard',''):
   r=self.call('load',unit=unit)
   saved=self.call('save',unit=unit,design=d,revision=r['revision'],source_token=r['source_token'])
   self.assertEqual(saved['design'],d)
   self.assertEqual(self.call('load',unit=unit)['design'],d)
  p=sheets.load_project(self.mod)
  self.assertEqual(p['draft'],project['draft']);self.assertEqual(p['units']['Guard']['annotations'],{'Tier':'T1'})
  self.assertEqual(p['units']['Guard']['extra'],{'note':'keep'})
  self.assertEqual(p['views'],project['views']);self.assertEqual(self.file.read_text(),TEXT)
 def test_live_preset_grade_and_override_precedence(self):
  d=design(pri_preset='arming_sword',cost_construct=100,cost_upkeep=200)
  d['presets']={'pri':{'arming_sword':{'atk':19}}}
  first=self.call('preview',design=d)
  self.assertEqual(first['native']['attack'],21)
  d['overrides']['inputs']={'pri_base_atk':7,'hide_forest_override':False}
  d['inputs']['equipment_grade']='high'
  second=self.call('preview',design=d)
  self.assertEqual(second['native']['attack'],10)
  self.assertEqual(second['native']['recruit_cost'],108)
  self.assertEqual(second['native']['upkeep'],210)
  self.assertNotIn('hide_forest',second['native']['attributes'])
  d['inputs']['pri_preset']='mace'
  self.assertEqual(self.call('preview',design=d)['native']['attack'],10)
  d['overrides']['native']['attack']=0
  d['inputs']['equipment_grade']='poor'
  self.assertEqual(self.call('preview',design=d)['native']['attack'],0)
  self.assertEqual(d['presets']['pri']['arming_sword']['atk'],19)
 def test_invalid_or_stale_save_is_transactional(self):
  r=self.call('load');d=design(pri_base_atk=6)
  self.call('save',design=d,revision=r['revision'],source_token=r['source_token'])
  before=sheets.project_path(self.mod).read_bytes()
  for body in [dict(design=d,revision='stale',source_token=r['source_token']),dict(design=d,revision=self.call('load')['revision'],source_token='stale'),dict(design={'version':2},**{k:self.call('load')[k] for k in ('revision','source_token')}),dict(design=d,unit='guard',**{k:self.call('load')[k] for k in ('revision','source_token')})]:
   with self.assertRaises((contract.ContractError,sheets.SheetError)):self.call('save',**body)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
 def test_sparse_donor_preview_uses_placeholders_without_writing(self):
  self.mod.edu=edu.parse_text('type Sparse\nownership england\n; sparse donor\n')
  r=self.call('preview',unit='Sparse',design=design(pri_base_atk=6))
  self.assertIn('; sparse donor',r['edu'])
  self.assertIn('stat_pri',r['edu'])
  self.assertEqual(self.file.read_text(),TEXT)
 def test_engine_notes_and_omitted_tags(self):
  self.mod.eop_dirs=[self.mod.root/'eopData']
  path=self.mod.root/'eopData/eopScripts/luaPluginScript.lua';path.parent.mkdir(mode=0o777,parents=True)
  path.write_text('M2TWEOP.setWeaponBonusModifier(1)\nM2TWEOP.setArmourUpgradeModifier(1)')
  d=design(pri_base_atk=6,pri_attr='sp, ap',weapon_upgrade_level=2)
  r=self.call('preview',design=d)
  self.assertEqual(r['metadata']['engine_rules']['weapon_upgrade_attack']['value'],1)
  self.assertEqual(r['metadata']['engine_rules']['notes'][0]['id'],'builder.upgrade_card_note')
  self.assertNotIn('sp',r['native']['pri_attributes']);self.assertNotIn('sp',r['edu'].split('stat_pri_attr')[1].splitlines()[0])
  self.mod.m2ex=True
  self.assertEqual(self.call('preview',design=d)['metadata']['engine_rules']['profile'],'M2EX')
 def test_http_routes_and_errors(self):
  from unittransfer.server import Handler,_Server
  class H(Handler):pass
  H.registry=SimpleNamespace(get=lambda name:self.mod if name=='Fixture' else (_ for _ in ()).throw(KeyError(name)))
  server=_Server(('127.0.0.1',0),H)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  def post(action,body):
   req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/builder/'+action,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req) as response:return json.load(response)
  r=post('load',{'mod':'Fixture'})
  self.assertIn('tables',r)
  for action,body in [('preview',{'design':design(pri_base_atk=6)}),('save',dict(design=design(pri_base_atk=6),revision=r['revision'],source_token=r['source_token']))]:
   self.assertIn('design',post(action,dict(mod='Fixture',**body)))
  for action,body in [('apply',{}),('preview',{'design':{}}),('load',{'unit':'missing'})]:
   with self.assertRaises(urllib.error.HTTPError) as error:post(action,dict(mod='Fixture',**body))
   self.assertEqual(error.exception.code,400)
   self.assertEqual(json.load(error.exception)['message_id'],'builder.invalid')

if __name__=='__main__':unittest.main()
