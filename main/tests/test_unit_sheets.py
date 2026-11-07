import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittransfer import edu,unit_sheets as sheets

TEXT='''type Guard
category infantry
class heavy
soldier guard, 60, 0, 1
ownership england
stat_pri 5, 2, no, 0, 0, melee, simple, piercing, sword, 25, 1
attributes hardy, unknown_custom
; keep

type Horse
category cavalry
class heavy
soldier horse, 30, 0, 1
ownership france
'''
class SheetProjectTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.mod=SimpleNamespace(data=self.root/'mod/data',edu=edu.parse_text(TEXT),name='Example')
  self.patch=patch.object(sheets.config,'CONFIG_DIR',self.root/'config');self.patch.start();self.addCleanup(self.patch.stop)
 def test_refresh_is_read_only_and_retains_missing_annotations(self):
  p=sheets.empty_project();p['units']['Removed']={'annotations':{'Unit Race':'Elf','Tier':'T2'},'extra':{'Future':'keep'}};p['known']=['Removed']
  new,r=sheets.refresh(self.mod,p)
  self.assertEqual(r['added'],['Guard','Horse']);self.assertEqual(r['removed'],['Removed']);self.assertIn('Removed',new['units']);self.assertEqual(len(r['missing_classifications']),2)
  self.assertFalse(sheets.project_path(self.mod).exists());self.assertEqual(p['known'],['Removed'])
 def test_reference_import_joins_exact_ids_preserves_extra_columns_and_live_category(self):
  p,r=sheets.import_reference(sheets.empty_project(),'Name,Unit Race,Tier,Category,Main Faction,AOR,Future\nGuard,Human,T2,cavalry,England,North,preserve\n')
  _,live=sheets.refresh(self.mod,p);row=live['rows'][0]
  self.assertEqual(row['Category'],'infantry');self.assertEqual(row['Unit Race'],'Human');self.assertEqual(row['extra']['Future'],'preserve')
  p['units']['Guard']['category_override']='siege';self.assertEqual(sheets.refresh(self.mod,p)[1]['rows'][0]['Category'],'siege')
 def test_duplicate_ids_or_headers_rejected_transactionally(self):
  p=sheets.empty_project()
  for text in ['Name,Tier\nGuard,T1\nGuard,T2\n','Name,Name\nGuard,Guard\n']:
   with self.assertRaises(sheets.SheetError):sheets.import_reference(p,text)
  self.assertEqual(p,sheets.empty_project())
 def test_json_adapter_validates_type_and_retains_arrays(self):
  p,r=sheets.import_reference(sheets.empty_project(),json.dumps({'Guard':{'Type':'Guard','Category':'infantry','Attributes':['hardy']}}),'edu_json')
  self.assertEqual(p['units']['Guard']['extra']['Attributes'],['hardy'])
  with self.assertRaises(sheets.SheetError):sheets.import_reference(p,'{"Guard":{"Type":"Wrong"}}','edu_json')
 def test_custom_header_mapping(self):
  p,r=sheets.import_reference(sheets.empty_project(),'A,Race,Grade\nGuard,Human,T3\n',mapping={'Name':'A','Unit Race':'Race','Tier':'Grade'})
  self.assertEqual(p['units']['Guard']['annotations']['Tier'],'T3')
 def test_save_roundtrip_and_revision_conflict(self):
  p=sheets.empty_project();rev=sheets.revision(p);sheets.save_project(self.mod,p,rev)
  p['units']['Guard']={'annotations':{'Tier':'T2'},'extra':{}}
  sheets.save_project(self.mod,p,rev)
  with self.assertRaises(sheets.SheetError):sheets.save_project(self.mod,sheets.empty_project(),rev)
  self.assertEqual(sheets.load_project(self.mod),p)
 def test_new_live_unit_is_in_queue_without_second_pipeline_run(self):
  p,_=sheets.refresh(self.mod,sheets.empty_project());self.mod.edu=edu.parse_text(TEXT+'\ntype New Guard\ncategory infantry\n')
  new,r=sheets.refresh(self.mod,p);self.assertEqual(r['added'],['New Guard']);self.assertIn('New Guard',[x['id'] for x in r['missing_classifications']])
 def test_removed_rename_suggestion_requires_unique_matching_signature_and_explicit_action(self):
  p,_=sheets.refresh(self.mod,sheets.empty_project());p['units']['Guard']={'annotations':{'Tier':'T2'},'extra':{'Note':'keep'}}
  self.mod.edu=edu.parse_text(TEXT.replace('type Guard\n','type Renamed Guard\n'))
  new,r=sheets.refresh(self.mod,p);self.assertEqual(r['rename_candidates'],[{'from':'Guard','to':'Renamed Guard'}])
  renamed=sheets.rename_annotations(new,sheets.live_units(self.mod),'Guard','Renamed Guard')
  self.assertEqual(renamed['units']['Renamed Guard']['extra']['Note'],'keep')
 def test_rule_keys_are_validated(self):
  text='Unit Race,Category,BarracksTier,T0\nHuman,infantry,T1,2\n'
  p=sheets.import_rules(sheets.empty_project(),text,'pool');self.assertEqual(p['rules']['pool'][0]['T0'],'2')
  with self.assertRaises(sheets.SheetError):sheets.import_rules(p,text+'Human,infantry,T1,3\n','pool')
 def test_export_retains_annotations_extra_and_current_category(self):
  p,_=sheets.import_reference(sheets.empty_project(),'Name,Unit Race,Tier,Note\nGuard,Human,T2,Keep\n')
  out=sheets.export_reference(self.mod,p);self.assertIn('Keep',out);self.assertIn('Human,T2',out);self.assertIn('infantry',out)
 def test_edb_json_snapshot_adapter(self):
  text=json.dumps({'barracks':{'Levels':[{'Name':'small','Capabilities':[{'Type':'recruit_pool','Unit':'Guard','MaximumPoolString':'2','Condition':'factions { england, }'}]}]}})
  rows=sheets.import_edb_json(text);self.assertEqual(rows[0]['maximum'],'2');self.assertEqual(rows[0]['unit'],'Guard')
 def test_unknown_project_schema_is_not_silently_reset(self):
  with self.assertRaises(sheets.SheetError):sheets.validate_project({'version':999})

if __name__=='__main__':unittest.main()
