import copy,unittest
from unittransfer import edu,sheet_ops as ops,unit_sheets as sheets
from tests import test_unit_sheets as fixture
TEXT=fixture.TEXT

FULL=TEXT.replace('; keep','stat_pri_armour 6, 4, 2, metal ; armor note\nstat_sec 3, 1, no, 0, 0, melee, simple, piercing, sword, 20, 1\nstat_cost 1, 100, 40, 0, 0, 100, 4, 1\n; keep')
class SheetOperationTests(unittest.TestCase):
 def test_gunpowder_optional_effect_keeps_delay_and_other_members(self):
  for field,column in [('stat_pri','attack_delay'),('stat_sec','sec_delay')]:
   original='20, 3, bullet, 45, 20, missile, missile_gunpowder, piercing, none, musket_shot_set, 25, 1'
   self.mod.edu=edu.parse_text('type Gunner\ncategory infantry\n'+field+' '+original+' ; retain\n')
   self.assertEqual(ops.records(self.mod,self.project)[0][0][column],25)
   p,_=ops.stage_operation(self.mod,self.project,['Gunner'],column,'set',0)
   fields,_=ops.field_changes(self.mod.edu.units[0],p['draft']['Gunner'])
   self.assertEqual(fields[field],original.replace('25, 1','0, 1'))
   self.assertIn('; retain',self.mod.edu.units[0].raw)
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

class MassSafetyTests(unittest.TestCase):
 setUp = SheetOperationTests.setUp
 def request(self, **edit):
  current = sheets.service(self.mod, 'load')
  return sheets.service(self.mod, 'operate', {
   'revision':current['revision'], 'source_token':current['source_token'], **edit})

 def test_matching_recomputes_ids_from_filter_without_pagination(self):
  result = self.request(mode='matching', ids=['Horse'], column='Tier', value='T2',
   where={'column':'category', 'value':'infantry'}, limit=1)
  self.assertEqual([c['id'] for c in result['changes']], ['Guard'])
  self.assertEqual(result['target_count'], 1)
  result = self.request(mode='matching', column='Tier', value='T3', limit=1)
  self.assertEqual(result['target_count'], 2)

 def test_selected_filtered_out_id_refuses_all_and_preserves_file(self):
  sheets.service(self.mod, 'load')
  path = sheets.project_path(self.mod)
  before = path.read_bytes()
  with self.assertRaisesRegex(sheets.SheetError, 'match'):
   self.request(mode='selected', ids=['Guard','Horse'], column='Tier', value='T2',
    where={'column':'category', 'value':'infantry'})
  self.assertEqual(path.read_bytes(), before)

 def test_rule_targets_obey_filter_in_both_modes(self):
  p = sheets.empty_project()
  p['rules']['pool'] = [{'id':'a','T0':1}, {'id':'b','T0':2}]
  sheets.save_project(self.mod, p)
  edit = dict(view='rules:pool', column='T0', value=0,
   where={'column':'T0','op':'gt','value':1})
  with self.assertRaises(sheets.SheetError):
   self.request(mode='selected', ids=['a','b'], **edit)
  result = self.request(mode='matching', ids=['a'], **edit)
  self.assertEqual([c['id'] for c in result['changes']], ['b'])

 def test_native_numeric_booleans_are_rejected(self):
  for column in ('attack','movement'):
   for value in (True, False):
    with self.subTest(column=column, value=value):
     with self.assertRaises(sheets.SheetError):
      ops.stage_operation(self.mod, self.project, ['Guard'], column, 'set', value)
     with self.assertRaises(sheets.SheetError):
      ops.stage_cells(self.mod, self.project, [{'id':'Guard','column':column,'value':value}])
  with self.assertRaises(sheets.SheetError):
   ops.stage_operation(self.mod, self.project, ['Guard'], 'attack', 'add', True)

 def test_blank_sets_require_clear_for_all_field_kinds(self):
  for column in ('Tier','formation','movement','attributes'):
   for value in ('', None, '   ', *([[]] if column == 'attributes' else [])):
    with self.subTest(column=column, value=value):
     with self.assertRaisesRegex(sheets.SheetError, '[Cc]lear'):
      ops.stage_operation(self.mod, self.project, ['Guard'], column, 'set', value)
  for value in ('', None, []):
   with self.assertRaisesRegex(sheets.SheetError, '[Cc]lear'):
    ops.stage_cells(self.mod, self.project, [{'id':'Guard','column':'attributes','value':value}])
  for column in ('Tier','class','movement','attributes'):
   p, changes = ops.stage_operation(self.mod, self.project, ['Guard'], column, 'clear')
   self.assertIn(changes[0]['after'], ('', None, []))
  with self.assertRaises(sheets.SheetError):
   ops.stage_operation(self.mod, self.project, ['Guard'], 'attack', 'clear')
  p, changes = ops.stage_operation(self.mod, self.project, ['Guard'], 'attack', 'set', 0)
  self.assertEqual(changes[0]['after'], 0)

 def test_paste_cannot_bypass_submitted_filter(self):
  first = sheets.service(self.mod, 'load')
  before = sheets.project_path(self.mod).read_bytes()
  with self.assertRaisesRegex(sheets.SheetError, 'match'):
   sheets.service(self.mod, 'paste', {**first,
    'where':{'column':'category','value':'infantry'},
    'cells':[{'id':'Horse','column':'Tier','value':'T2'}]})
  self.assertEqual(sheets.project_path(self.mod).read_bytes(), before)

 def test_rule_blank_set_requires_clear_and_zero_is_value(self):
  p = sheets.validate_project(sheets.empty_project())
  p['rules']['pool'] = [{'id':'a','T0':1}]
  for value in ('', None):
   with self.assertRaisesRegex(sheets.SheetError, '[Cc]lear'):
    ops.stage_rule_operation(p, 'pool', ['a'], 'T0', 'set', value)
  cleared, _ = ops.stage_rule_operation(p, 'pool', ['a'], 'T0', 'clear')
  self.assertEqual(cleared['rules']['pool'][0]['T0'], '')
  zero, _ = ops.stage_rule_operation(p, 'pool', ['a'], 'T0', 'set', 0)
  self.assertEqual(zero['rules']['pool'][0]['T0'], 0)

 def test_rule_blank_paste_requires_clear(self):
  p = sheets.validate_project(sheets.empty_project())
  p['rules']['pool'] = [{'id':'a','T0':1}]
  for value in ('', None):
   with self.assertRaisesRegex(sheets.SheetError, '[Cc]lear'):
    ops.stage_rule_cells(p, 'pool', [{'id':'a','column':'T0','value':value}])

 def test_rule_dry_run_is_byte_identical(self):
  p = sheets.empty_project()
  p['rules']['pool'] = [{'id':'a','T0':1}]
  sheets.save_project(self.mod, p)
  current = sheets.service(self.mod, 'load')
  path = sheets.project_path(self.mod)
  before = path.read_bytes()
  result = self.request(view='rules:pool', ids=['a'], column='T0', value=0, dry_run=True)
  self.assertEqual(result['changes'], [{'id':'a','column':'T0','before':1,'after':0}])
  self.assertEqual(result['target_count'], 1)
  self.assertEqual(result['revision'], current['revision'])
  self.assertEqual(path.read_bytes(), before)

 def test_dry_run_has_same_changes_without_writes_or_revision(self):
  first = sheets.service(self.mod, 'load')
  path = sheets.project_path(self.mod)
  before = path.read_bytes()
  stamp = path.stat().st_mtime_ns
  edit = dict(ids=['Guard'], column='attack', operation='add', value=2)
  preview = self.request(dry_run=True, **edit)
  self.assertEqual(path.read_bytes(), before)
  self.assertEqual(path.stat().st_mtime_ns, stamp)
  self.assertEqual(preview['revision'], first['revision'])
  self.assertEqual(preview['project'], first['project'])
  actual = self.request(**edit)
  self.assertEqual(preview['changes'], actual['changes'])
  self.assertEqual(preview['target_count'], actual['target_count'])

 def test_dry_run_does_not_create_or_migrate_project_file(self):
  body = {'revision':sheets.revision(sheets.empty_project()),
   'source_token':sheets.source_token(self.mod), 'ids':['Guard'],
   'column':'attack', 'value':9, 'dry_run':True}
  sheets.service(self.mod, 'operate', body)
  self.assertFalse(sheets.project_path(self.mod).exists())
  import json
  legacy = sheets.empty_project()
  del legacy['rule_schema']
  path = sheets.project_path(self.mod)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(legacy), encoding='utf-8')
  before = path.read_bytes()
  body['revision'] = sheets.revision(sheets.validate_project(copy.deepcopy(legacy)))
  sheets.service(self.mod, 'operate', body)
  self.assertEqual(path.read_bytes(), before)

 def check_arithmetic(self, operation, value, expected):
  _, changes = ops.stage_operation(self.mod, self.project, ['Guard'],
   'attack', operation, value)
  self.assertEqual(changes, [{'id':'Guard','column':'attack','before':5,'after':expected}])

 def test_add_branch(self):
  self.check_arithmetic('add', 2, 7)
 def test_subtract_branch(self):
  self.check_arithmetic('subtract', 2, 3)
 def test_multiply_branch(self):
  self.check_arithmetic('multiply', 2, 10)
 def test_divide_branch(self):
  self.check_arithmetic('divide', 5, 1)
 def test_percentage_branch(self):
  self.check_arithmetic('percent', 100, 10)
 def test_minimum_clamp_branch(self):
  self.check_arithmetic('min', 8, 8)
 def test_maximum_clamp_branch(self):
  self.check_arithmetic('max', 3, 3)
 def test_round_branch(self):
  self.check_arithmetic('round', -1, 0)

 def test_copy_branch(self):
  _, changes = ops.stage_operation(self.mod, self.project, ['Guard'], 'attack', 'copy', 'charge')
  self.assertEqual(changes[0]['after'], 2)

 def test_text_replace_branch(self):
  _, changes = ops.stage_operation(self.mod, self.project, ['Guard'], 'class', 'replace', 'heavy', 'light')
  self.assertEqual(changes[0]['after'], 'light')

 def test_attribute_deduplicate_preserves_unknown(self):
  self.mod.edu = edu.parse_text(FULL.replace('hardy, unknown_custom', 'hardy, unknown_custom, hardy'))
  _, changes = ops.stage_operation(self.mod, self.project, ['Guard'], 'attributes', 'deduplicate')
  self.assertEqual(changes[0]['after'], ['hardy','unknown_custom'])

 def test_recipe_validation_is_transactional_and_zero_roundtrips(self):
  first = sheets.service(self.mod, 'load')
  path = sheets.project_path(self.mod)
  before = path.read_bytes()
  bad_recipes = [
   {'column':'attack','operation':'surprise','value':1},
   {'column':'unknown','operation':'set','value':1},
   {'column':'attack','operation':'set','value':True},
   {'column':'attack','operation':'set','value':{}},
   {'column':'attributes','operation':'set','value':{}},
   {'column':'attributes','operation':'set','value':[True]},
   {'column':'class','operation':'set','value':True},
   {'column':'attack','operation':'set','value':''},
   {'column':'attack','operation':'copy','value':'unknown'},
   {'column':'class','operation':'multiply','value':2},
   {'column':'attack','operation':'set','value':2,'target':{'view':'soft'}},
   {'column':'T0','operation':'set','value':2,'target':{'view':'rules','rule_table':'missing'}},
   {'column':'city_multiplier','operation':'set','value':1,'target':{'profile':'missing'}},
   {'column':'T0','operation':'set','value':True,'target':{'view':'rules:pool'}},
   {'column':'T0','operation':'surprise','value':1,'target':{'view':'rules:pool'}},
   {'column':'attack','operation':'expression','value':'__import__("os")'},
   {'column':'attack','operation':'divide','value':0},
   {'column':'attack','operation':'round','value':7},
   {'column':'attack','operation':'expression','value':'1e999'},
  ]
  for recipe in bad_recipes:
   with self.subTest(recipe=recipe):
    p = copy.deepcopy(first['project'])
    p['recipes']['bad'] = recipe
    with self.assertRaises(sheets.SheetError):
     sheets.service(self.mod, 'save', {**first, 'project':p})
    self.assertEqual(path.read_bytes(), before)
  p = copy.deepcopy(first['project'])
  p['balance_profile'] = {'name':'Custom'}
  p['recipes'] = {
   'zero':{'column':'attack','operation':'set','value':0},
   'null_target':{'column':'attack','operation':'set','value':0,'target':None},
   'pool':{'column':'T0','operation':'set','value':0,'target':{'view':'rules','rule_table':'pool'}},
   'profile':{'column':'city_multiplier','operation':'set','value':0.5,'target':{'profile':'Custom'}},
  }
  sheets.service(self.mod, 'save', {**first, 'project':p})
  self.assertEqual(sheets.load_project(self.mod)['recipes'], p['recipes'])

if __name__=='__main__':unittest.main()
