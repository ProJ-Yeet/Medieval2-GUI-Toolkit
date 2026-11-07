import copy,unittest
from unittransfer import edu,sheet_ops as ops,unit_sheets as sheets
from tests import test_unit_sheets as fixture
TEXT=fixture.TEXT

FULL=TEXT.replace('; keep','stat_pri_armour 6, 4, 2, metal ; armor note\nstat_sec 3, 1, no, 0, 0, melee, simple, piercing, sword, 20, 1\nstat_cost 1, 100, 40, 0, 0, 100, 4, 1\n; keep')
class SheetOperationTests(unittest.TestCase):
 def setUp(self):
  fixture.SheetProjectTests.setUp(self);self.mod.edu=edu.parse_text(FULL);self.project=sheets.empty_project()
 def test_staging_does_not_mutate_project_or_unit_and_preserves_tuple_members(self):
  original=self.mod.edu.units[0].raw
  p,changes=ops.stage_operation(self.mod,self.project,['Guard'],'attack','set',9)
  self.assertEqual(self.project['draft'],{});self.assertEqual(self.mod.edu.units[0].raw,original)
  fields,rm=ops.field_changes(self.mod.edu.units[0],p['draft']['Guard'])
  self.assertTrue(fields['stat_pri'].startswith('9, 2, no'));self.assertEqual(rm,[])
 def test_zero_secondary_and_clear_list_are_explicit(self):
  p,_=ops.stage_operation(self.mod,self.project,['Guard'],'sec_attack','set',0)
  self.assertEqual(ops.records(self.mod,p)[0][0]['sec_attack'],0)
  p,_=ops.stage_operation(self.mod,p,['Guard'],'attributes','clear')
  _,removed=ops.field_changes(self.mod.edu.units[0],p['draft']['Guard']);self.assertIn('attributes',removed)
 def test_bad_target_rolls_back_whole_operation(self):
  with self.assertRaises(sheets.SheetError):ops.stage_operation(self.mod,self.project,['Guard','missing'],'attack','set',8)
  self.assertEqual(self.project['draft'],{})
 def test_safe_expressions_and_division(self):
  p,_=ops.stage_operation(self.mod,self.project,['Guard'],'recruit_cost','expression','upkeep * 3 + attack')
  self.assertEqual(p['draft']['Guard']['recruit_cost'],125)
  for text in ['__import__("os").system("whoami")','attack ** 100','1 / 0','(lambda: 1)()']:
   with self.assertRaises(sheets.SheetError):ops.expression(text,{'attack':5})
 def test_attribute_append_remove_preserve_unknown_tags(self):
  p,_=ops.stage_operation(self.mod,self.project,['Guard'],'attributes','append','hardy, new_tag')
  self.assertEqual(p['draft']['Guard']['attributes'],['hardy','unknown_custom','new_tag'])
  p,_=ops.stage_operation(self.mod,p,['Guard'],'attributes','remove','hardy')
  self.assertEqual(p['draft']['Guard']['attributes'],['unknown_custom','new_tag'])
 def test_filters_nested_and_typed(self):
  rows,_=ops.records(self.mod,self.project)
  where={'all':[{'column':'category','op':'eq','value':'infantry'},{'any':[{'column':'attack','op':'gt','value':'4'},{'column':'attack','op':'missing'}]},{'not':{'column':'attributes','op':'contains','value':'never'}}]}
  self.assertEqual(ops.query(rows,where)['matched_ids'],['Guard'])
  self.assertTrue(ops.matches({'x':0},{'column':'x','op':'contains','value':'0'}))
  self.assertFalse(ops.matches({'x':0},{'column':'x','op':'blank'}))
 def test_stable_sort_and_paging(self):
  rows=[{'id':'b','n':2},{'id':'a','n':2},{'id':'c','n':None}]
  self.assertEqual(ops.query(rows,sort=[{'column':'n','desc':True}],limit=1)['matched_ids'],['a','b','c'])
 def test_derived_columns_are_read_only_and_do_not_replace_missing_with_zero(self):
  rows,_=ops.records(self.mod,self.project)
  self.assertEqual(rows[0]['defense_total'],12);self.assertIsNone(rows[1]['defense_total'])
  with self.assertRaises(sheets.SheetError):ops.stage_operation(self.mod,self.project,['Guard'],'defense_total','set',20)
 def test_service_conflict_and_invalid_import_leave_project_intact(self):
  first=sheets.service(self.mod,'load');before=sheets.load_project(self.mod)
  with self.assertRaises(sheets.SheetError):sheets.service(self.mod,'operate',{'ids':['Guard'],'column':'attack','value':9,'revision':'stale','source_token':first['source_token']})
  bad=copy.deepcopy(before);bad['draft']={'Guard':{'not_allowed':5}}
  with self.assertRaises(sheets.SheetError):sheets.service(self.mod,'save',{'project':bad,'revision':first['revision'],'source_token':first['source_token']})
  self.assertEqual(sheets.load_project(self.mod),before)
 def test_service_revision_and_native_draft_roundtrip(self):
  first=sheets.service(self.mod,'load')
  result=sheets.service(self.mod,'operate',{'ids':['Guard'],'column':'attack','operation':'add','value':2,'revision':first['revision'],'source_token':first['source_token']})
  self.assertEqual(result['table']['rows'][0]['attack'],7)
  self.assertNotEqual(first['revision'],result['revision'])

 def test_boolean_builder_values_match_booleans(self):
  for column in ('changed','needs_classification'):
   for value in (True,False):
    row={column:value}
    self.assertTrue(ops.matches(row,{'column':column,'op':'eq','value':str(value).lower()}))
    self.assertFalse(ops.matches(row,{'column':column,'op':'ne','value':str(value).lower()}))
  self.assertFalse(ops.matches({'changed':True},{'column':'changed','value':'1'}))
 def test_invalid_source_is_not_missing_and_uses_edit_validator(self):
  for value in ('bad','-2','1.5','nan'):
   self.mod.edu=edu.parse_text(FULL.replace('stat_pri 5,','stat_pri '+value+','))
   row=ops.records(self.mod,self.project)[0][0]
   self.assertTrue(ops.matches(row,{'column':'attack','op':'invalid'}),value)
   self.assertFalse(ops.matches(row,{'column':'attack','op':'missing'}),value)
  row=ops.records(self.mod,self.project)[0][1]
  self.assertTrue(ops.matches(row,{'column':'attack','op':'missing'}))
  self.assertFalse(ops.matches(row,{'column':'attack','op':'invalid'}))
 def test_classification_changes_and_staged_projectile_context(self):
  for column in ('Unit Race','Category override'):
   p,_=ops.stage_operation(self.mod,self.project,['Guard'],column,'set','Human' if column=='Unit Race' else 'siege')
   self.assertTrue(ops.records(self.mod,p)[0][0]['changed'])
  p,_=ops.stage_cells(self.mod,self.project,[{'id':'Guard','column':'Tier','value':'T2'}])
  self.assertTrue(ops.records(self.mod,p)[0][0]['changed'])
  p,_=ops.stage_operation(self.mod,self.project,['Guard'],'missile','set','arrow')
  row=ops.records(self.mod,p)[0][0]
  self.assertEqual(row['projectile'],'arrow')
  self.assertTrue(ops.matches(row,{'column':'projectile','value':'arrow'}))
 def test_weapon_members_are_derived_and_read_only(self):
  rows,_=ops.records(self.mod,self.project)
  for column,value in [('pri_weapon_type','melee'),('pri_tech_type','simple'),('sec_weapon_type','melee'),('sec_tech_type','simple')]:
   self.assertEqual(rows[0][column],value)
   self.assertTrue(ops.matches(rows[0],{'column':column,'value':value}))
   self.assertIsNone(rows[1][column])
   with self.assertRaises(sheets.SheetError):
    ops.stage_operation(self.mod,self.project,['Guard'],column,'set',value)

 def test_classification_reversion_clears_changed_and_noop_is_not_changed(self):
  p,_=ops.stage_operation(self.mod,self.project,['Guard'],'Tier','set','T2')
  p,_=ops.stage_operation(self.mod,p,['Guard'],'Tier','clear')
  self.assertFalse(ops.records(self.mod,p)[0][0]['changed'])
 def test_invalid_numeric_sources_do_not_break_derived_or_range_filters(self):
  self.mod.edu=edu.parse_text(FULL.replace('stat_pri_armour 6,','stat_pri_armour bad,'))
  row=ops.records(self.mod,self.project)[0][0]
  self.assertIsNone(row['defense_total'])
  self.assertIsNone(row['cost_efficiency'])
  self.assertFalse(ops.matches(row,{'column':'armor','op':'gt','value':'0'}))


 def test_comparison_group_statistics_use_valid_members_and_staged_values(self):
  self.project['groups'] = {'Archers':['Guard','Horse','Removed']}
  p,_ = ops.stage_operation(self.mod,self.project,['Horse'],'unit_size','set',90)
  result = ops.compare_group(self.mod,p,'Archers')
  self.assertEqual([r['id'] for r in result['members']],['Guard','Horse','Removed'])
  self.assertTrue(result['members'][2]['missing'])
  self.assertEqual(result['statistics']['unit_size'],{'min':60,'max':90,'average':75,'count':2})
  self.assertEqual(result['members'][0]['difference']['unit_size'],-15)
  self.assertEqual(result['members'][1]['difference']['ultra_size'],37.5)
  self.assertIsNone(result['members'][2]['difference']['attack'])
  self.assertEqual(result['statistics']['attack']['count'],1)
  self.assertIsNone(result['statistics']['movement']['average'])
  self.assertIn('category',result['columns'])
  self.assertNotIn('attributes',result['columns'])
  self.assertEqual(result['column_kinds']['attack'],'native')
  self.assertEqual(result['column_kinds']['defense_total'],'derived')

 def test_group_membership_filter_contract_and_readonly(self):
  self.project['groups'] = {'Gondor':['Guard'],'PikesHalberds':['Guard','Horse']}
  rows,_ = ops.records(self.mod,self.project)
  self.assertEqual(rows[0]['groups'],['Gondor','PikesHalberds'])
  self.assertEqual(ops.query(rows,{'column':'groups','op':'not_contains','value':'Gondor'})['matched_ids'],['Horse'])
  self.assertEqual(ops.query(rows,{'column':'groups','op':'contains','value':'Gondor'})['matched_ids'],['Guard'])
  self.assertEqual(ops.filter_info([])['groups']['type'],'list')
  for column,kind in [('attack','native'),('Tier','annotation'),('defense_total','derived'),('groups','annotation')]:
   self.assertEqual(ops.filter_info(rows)[column]['kind'],kind)
  with self.assertRaises(sheets.SheetError):
   ops.stage_operation(self.mod,self.project,['Guard'],'groups','set','Other')

if __name__=='__main__':unittest.main()
