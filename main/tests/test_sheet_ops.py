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

if __name__=='__main__':unittest.main()
