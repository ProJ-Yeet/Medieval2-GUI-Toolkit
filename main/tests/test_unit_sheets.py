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
 def test_effective_profile_response(self):
  from unittransfer import edb_balance
  result = sheets.service(self.mod, 'load')
  self.assertEqual(result['balance_effective'], edb_balance.profile_of(result['project']))

 def test_effective_profile_recipe_columns(self):
  from unittransfer import sheet_ops
  project = sheets.empty_project()
  project['balance_profile'] = {'name':'Custom', 'extra_text':'keep', 'extra_bool':True,
                                'extra_number':2}
  columns, rule = sheet_ops.recipe_columns(project, {'profile':'Custom'})
  self.assertFalse(rule)
  self.assertNotIn('name', columns)
  self.assertEqual(columns['extra_text'], 'text')
  self.assertEqual(columns['extra_bool'], 'bool')
  self.assertEqual(columns['extra_number'], 'number')
  self.assertIn('barracks_cap', columns)
  recipe = {'target':{'profile':'Custom'}, 'column':'extra_number', 'operation':'add', 'value':1}
  staged, changes = sheet_ops.stage_profile_recipe(project, recipe)
  self.assertEqual(staged['balance_profile']['extra_number'], 3)

 def test_default_profile_recipe_preview_run_and_undo(self):
  current = sheets.service(self.mod, 'load')
  project = copy.deepcopy(current['project'])
  self.assertEqual(project.get('balance_profile', {}), {})
  project['balance_profile'] = {}
  project['recipes']['cap'] = {'target':{'profile':'default'}, 'column':'barracks_cap',
                              'operation':'set', 'value':5}
  current = sheets.service(self.mod, 'save', dict(current, project=project))
  before = copy.deepcopy(current['project'])
  raw = sheets.project_path(self.mod).read_bytes()
  body = dict(recipe_name='cap', revision=current['revision'], source_token=current['source_token'])
  preview = sheets.service(self.mod, 'operate', dict(body, dry_run=True))
  self.assertEqual(preview['changes'], [{'id':'default', 'column':'barracks_cap', 'before':5, 'after':5}])
  self.assertEqual(preview['project'], before)
  self.assertEqual(sheets.project_path(self.mod).read_bytes(), raw)
  current = sheets.service(self.mod, 'operate', body)
  self.assertEqual(current['changes'], preview['changes'])
  self.assertEqual(current['project']['balance_profile']['barracks_cap'], 5)
  current = sheets.service(self.mod, 'save', dict(current, project=before))
  self.assertEqual(current['project'], before)
  self.assertEqual(current['project']['balance_profile'], {})
  refused = copy.deepcopy(before)
  refused['recipes']['cap']['target']['profile'] = 'another'
  with self.assertRaises(sheets.SheetError):
   sheets.service(self.mod, 'save', dict(current, project=refused))

 def test_invalid_legacy_recipes_load_query_and_unchanged_save(self):
  project=sheets.empty_project()
  project['recipes']={'old rule':{'column':'T0','operation':'set','value':2},
                      'blank':{'column':'attack','operation':'set','value':''}}
  path=sheets.project_path(self.mod)
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(project),encoding='utf-8')
  result=sheets.service(self.mod,'load')
  self.assertEqual(result['project']['recipes'],project['recipes'])
  self.assertEqual(set(result['invalid_recipes']),{'old rule','blank'})
  self.assertTrue(all(result['invalid_recipes'].values()))
  queried=sheets.service(self.mod,'query')
  self.assertEqual(queried['table']['total'],2)
  changed=copy.deepcopy(result['project']);changed['views']['test']={}
  saved=sheets.service(self.mod,'save',dict(project=changed,revision=result['revision'],source_token=result['source_token']))
  self.assertEqual(saved['project']['recipes'],project['recipes'])
  changed['recipes']['blank']['value']=' '
  with self.assertRaises(sheets.SheetError):
   sheets.service(self.mod,'save',dict(project=changed,revision=saved['revision'],source_token=saved['source_token']))

 def test_recipe_execution_revalidates_legacy_and_preserves_scope_and_zero(self):
  project=sheets.empty_project()
  project['recipes']={'zero':{'target':{'view':'base'},'column':'attack','operation':'set','value':0},
                      'rule':{'target':{'view':'rules:experience'},'column':'T0','operation':'set','value':0},
                      'bad':{'column':'attack','operation':'set','value':''}}
  project['rules']['experience']=[{'id':'row','Unit Race':'Human','Category':'infantry','BarracksTier':'T1','T0':2}]
  path=sheets.project_path(self.mod);path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(project),encoding='utf-8')
  current=sheets.service(self.mod,'load')
  for name,view in [('bad','base'),('zero','soft')]:
   with self.assertRaises(sheets.SheetError):
    sheets.service(self.mod,'operate',dict(recipe_name=name,view=view,ids=['Guard'],revision=current['revision'],source_token=current['source_token']))
  for name,view,uid in [('zero','base','Guard'),('rule','rules:experience','row')]:
   body=dict(recipe_name=name,view=view,ids=[uid],revision=current['revision'],source_token=current['source_token'])
   preview=sheets.service(self.mod,'operate',dict(body,dry_run=True))
   self.assertEqual(preview['changes'][0]['after'],0)
   current=sheets.service(self.mod,'operate',body)
   self.assertEqual(current['changes'],preview['changes'])

 def test_profile_recipe_arithmetic_and_refusals(self):
  for operation,value,expected in [('set',1.2,1.2),('add',.1,1),('subtract',.1,.8),
      ('multiply',2,1.8),('divide',2,.45),('percent',100,1.8),('min',1,1),('max',.5,.5),('round',0,1)]:
   with self.subTest(operation=operation):
    project=sheets.empty_project();project['balance_profile']={'name':'P'}
    project['recipes']['recipe']={'target':{'profile':'P'},'column':'city_multiplier','operation':operation,'value':value}
    sheets.save_project(self.mod,project)
    current=sheets.service(self.mod,'load')
    body=dict(recipe_name='recipe',revision=current['revision'],source_token=current['source_token'])
    preview=sheets.service(self.mod,'operate',dict(body,dry_run=True))
    self.assertAlmostEqual(preview['changes'][0]['after'],expected)
  before=sheets.project_path(self.mod).read_bytes()
  with self.assertRaises(sheets.SheetError):
   sheets.service(self.mod,'operate',dict(body,revision='stale'))
  for column,value in [('city_multiplier',True),('fractional_pool_exception','false'),('branch_policy',False)]:
   project=copy.deepcopy(current['project'])
   project['recipes']['recipe']={'target':{'profile':'P'},'column':column,'operation':'set','value':value}
   with self.assertRaises(sheets.SheetError):sheets.save_project(self.mod,project)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)

 def test_profile_recipe_preview_stage_and_snapshot_history(self):
  project=sheets.empty_project();project['balance_profile']={'name':'Example'}
  project['recipes']={'numeric':{'target':{'profile':'Example'},'column':'city_multiplier','operation':'add','value':.1},
                      'text':{'target':{'profile':'Example'},'column':'branch_policy','operation':'set','value':'reject_ambiguous'},
                      'bool':{'target':{'profile':'Example'},'column':'fractional_pool_exception','operation':'set','value':False}}
  sheets.save_project(self.mod,project)
  current=sheets.service(self.mod,'load')
  for name,key,expected in [('numeric','city_multiplier',1),('text','branch_policy','reject_ambiguous'),('bool','fractional_pool_exception',False)]:
   with self.subTest(name=name):
    before=copy.deepcopy(current['project']);raw=sheets.project_path(self.mod).read_bytes()
    body=dict(recipe_name=name,revision=current['revision'],source_token=current['source_token'])
    preview=sheets.service(self.mod,'operate',dict(body,dry_run=True))
    self.assertEqual(preview['target_count'],1)
    self.assertEqual(preview['changes'][0]['after'],expected)
    self.assertEqual(sheets.project_path(self.mod).read_bytes(),raw)
    current=sheets.service(self.mod,'operate',body)
    self.assertEqual(current['project']['balance_profile'][key],expected)
    staged=copy.deepcopy(current['project'])
    current=sheets.service(self.mod,'save',dict(project=before,revision=current['revision'],source_token=current['source_token']))
    self.assertEqual(current['project'],before)
    current=sheets.service(self.mod,'save',dict(project=staged,revision=current['revision'],source_token=current['source_token']))
    self.assertEqual(current['project'],staged)

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
  imported = sheets.import_rules(p,text+'Human,infantry,T1,3\n','pool')
  from unittransfer import sheet_ops
  self.assertEqual(sheet_ops.rule_records(imported, 'pool')[3][0]['code'],
                   'conflicting_duplicate_rule_key')
 def test_export_retains_annotations_extra_and_current_category(self):
  p,_=sheets.import_reference(sheets.empty_project(),'Name,Unit Race,Tier,Note\nGuard,Human,T2,Keep\n')
  out=sheets.export_reference(self.mod,p);self.assertIn('Keep',out);self.assertIn('Human,T2',out);self.assertIn('infantry',out)
 def test_edb_json_snapshot_adapter(self):
  text=json.dumps({'barracks':{'Levels':[{'Name':'small','Capabilities':[{'Type':'recruit_pool','Unit':'Guard','MaximumPoolString':'2','Condition':'factions { england, }'}]}]}})
  rows=sheets.import_edb_json(text);self.assertEqual(rows[0]['maximum'],'2');self.assertEqual(rows[0]['unit'],'Guard')
 def test_unknown_project_schema_is_not_silently_reset(self):
  with self.assertRaises(sheets.SheetError):sheets.validate_project({'version':999})

 def test_per_view_schema_matches_rows_even_when_empty(self):
  from unittransfer import buildings
  self.mod.edb=buildings.parse_text('')
  for view in ('base','attributes','soft','classification','recruitment'):
   result=sheets.service(self.mod,'query',{'view':view})
   info=result['filter_info']
   self.assertEqual(info['changed']['type'],'bool')
   self.assertTrue(all(item['type'] in ('text','number','bool','list') for item in info.values()))
   for row in result['table']['rows']:
    self.assertTrue(set(info).issubset(row))
   if view=='recruitment':
    self.assertNotIn('category',info)
    self.assertEqual(info['building_depth']['type'],'number')
   else:
    self.assertEqual(info['attack']['type'],'number')
    self.assertEqual(info['ownership']['type'],'list')
    self.assertTrue(info['pri_weapon_type']['readonly'])
 def test_recruitment_join_invalid_numbers_and_graph_depth(self):
  from unittransfer import buildings,edb_balance
  from tests.test_edb_balance import EDB
  edb=buildings.parse_text(EDB.replace('1   0.1  2  0','bad   0.1  -2  0'))
  p=sheets.empty_project()
  p['units']['Guard']={'annotations':{'Tier':'T2'},'category_override':'siege'}
  p['draft']={'Guard':{'missile':'arrow'}}
  sheets.save_project(self.mod,p)
  with patch.object(edb_balance,'fresh_edb',return_value=edb):
   result=sheets.service(self.mod,'query',{'view':'recruitment'})
   rows=result['table']['rows'];guard=rows[0]
   self.assertEqual(guard['projectile'],'arrow')
   self.assertEqual(guard['Category override'],'siege')
   self.assertTrue(guard['changed'])
   self.assertEqual(guard['initial'],'bad')
   self.assertIn('initial',guard['invalid_columns'])
   self.assertIn('maximum',guard['invalid_columns'])
   self.assertEqual([row['building_depth'] for row in rows],[0,0,1,1])
   self.assertEqual([row['building_tier'] for row in rows],[1,1,2,2])
   filtered=sheets.service(self.mod,'query',{'view':'recruitment','where':{'column':'initial','op':'invalid'}})
   self.assertEqual(filtered['table']['total'],1)
   filtered=sheets.service(self.mod,'query',{'view':'recruitment','where':{'column':'initial','op':'missing'}})
   self.assertEqual(filtered['table']['total'],0)
 def test_saved_classification_change_marks_changed(self):
  first=sheets.service(self.mod,'load')
  p=first['project'];p['units']['Guard']={'annotations':{'Tier':'T3'}}
  result=sheets.service(self.mod,'save',{'project':p,'revision':first['revision'],'source_token':first['source_token']})
  self.assertTrue(result['table']['rows'][0]['changed'])

 def test_recruitment_cycles_have_unknown_depth_instead_of_zero(self):
  from unittransfer import buildings,edb_balance
  from tests.test_edb_balance import EDB
  edb=buildings.parse_text(EDB)
  edb.buildings[0].blocks[1].upgrades=['hut']
  with patch.object(edb_balance,'fresh_edb',return_value=edb):
   rows=sheets.service(self.mod,'query',{'view':'recruitment'})['table']['rows']
  self.assertTrue(all(row['building_depth'] is None and row['building_tier'] is None for row in rows))
 def test_extra_column_filter_types_follow_values(self):
  p=sheets.empty_project()
  p['units']['Guard']={'extra':{'count':3,'flag':True,'tags':['a']}}
  sheets.save_project(self.mod,p)
  info=sheets.service(self.mod,'query')['filter_info']
  self.assertEqual(info['extra:count']['type'],'number')
  self.assertEqual(info['extra:flag']['type'],'bool')
  self.assertEqual(info['extra:tags']['type'],'list')

 def test_project_undo_restores_classification_baseline(self):
  first=sheets.service(self.mod,'load')
  old=copy.deepcopy(first['project'])
  edited=sheets.service(self.mod,'operate',{'ids':['Guard'],'column':'Tier','value':'T2','revision':first['revision'],'source_token':first['source_token']})
  undone=sheets.service(self.mod,'save',{'project':old,'revision':edited['revision'],'source_token':edited['source_token']})
  self.assertFalse(undone['table']['rows'][0]['changed'])

 def test_recruitment_building_type_uses_optional_edb_classification(self):
  from unittransfer import buildings,edb_balance
  from tests.test_edb_balance import EDB
  for classification in ('military',''):
   text=EDB.replace(' levels hut hall',(' classification '+classification+'\n' if classification else '')+' levels hut hall')
   with patch.object(edb_balance,'fresh_edb',return_value=buildings.parse_text(text)):
    result=sheets.service(self.mod,'query',{'view':'recruitment'})
   self.assertEqual(result['filter_info']['building_type']['type'],'text')
   self.assertTrue(all(row['building_type']==(classification or None) for row in result['table']['rows']))

 def rule_call(self, action, result=None, **body):
  result = result or sheets.service(self.mod, 'query', {'view': 'rules:pool'})
  return sheets.service(self.mod, action, dict(view='rules:pool',
   revision=result['revision'], source_token=result['source_token'], **body))

 def test_rule_identity_migration_is_persisted_and_edits_use_ids(self):
  p = sheets.empty_project()
  p['rules']['pool'] = [dict(zip(('Unit Race','Category','BarracksTier','T0'), values))
   for values in [('Custom','infantry','T1','2'), ('Other','cavalry','T2','3')]]
  sheets.config._write_json(sheets.project_path(self.mod), p)
  result = self.rule_call('query')
  rows = result['table']['rows']
  self.assertTrue(all(row['id'] for row in rows))
  persisted = json.loads(sheets.project_path(self.mod).read_text())
  self.assertEqual({r['id'] for r in persisted['rules']['pool']}, {r['id'] for r in rows})
  target = next(row['id'] for row in rows if row['Unit Race'] == 'Other')
  result = self.rule_call('operate', result, ids=[target], column='T0', value='0')
  self.assertEqual(next(r['T0'] for r in result['project']['rules']['pool'] if r['id'] == target), 0)
  with self.assertRaises(sheets.SheetError):
   self.rule_call('operate', result, ids=[0], column='T0', value=99)

 def test_rule_empty_schema_structure_and_project_undo(self):
  result = self.rule_call('query')
  self.assertEqual(result['filter_info']['Unit Race']['type'], 'text')
  self.assertEqual(result['filter_info']['T0']['type'], 'number')
  self.assertEqual(result['frozen_columns'], ['id','Unit Race','Category','BarracksTier'])
  original = result['project']
  result = self.rule_call('rule_structure', result, operation='add_row')
  row = result['table']['rows'][0]
  self.assertEqual(row['Unit Race'], '')
  result = self.rule_call('rule_structure', result, operation='add_column', column='Custom value')
  result = self.rule_call('operate', result, ids=[row['id']], column='Custom value', value=0)
  result = self.rule_call('rule_structure', result, operation='rename_column', column='Custom value', name='Renamed')
  self.assertEqual(result['table']['rows'][0]['Renamed'], 0)
  result = self.rule_call('rule_structure', result, operation='remove_column', column='Renamed')
  self.assertNotIn('Renamed', result['filter_info'])
  result = self.rule_call('rule_structure', result, operation='remove_rows', ids=[row['id']])
  self.assertEqual(result['table']['total'], 0)
  result = self.rule_call('save', result, project=original)
  self.assertEqual(result['project']['rules']['pool'], [])

 def test_rule_numeric_validation_paste_is_atomic_and_clear_is_explicit(self):
  result = self.rule_call('rule_structure', operation='add_row')
  uid = result['table']['rows'][0]['id']
  for value in ('bad','NaN',True):
   with self.assertRaises(sheets.SheetError):
    self.rule_call('paste', result, cells=[{'id':uid,'column':'T0','value':0},
     {'id':uid,'column':'T1','value':value}])
   self.assertEqual(sheets.load_project(self.mod)['rules']['pool'][0]['T0'], '')
  result = self.rule_call('operate', result, ids=[uid], column='T0', value='0')
  with self.assertRaisesRegex(sheets.SheetError, 'clear'):
   self.rule_call('operate', result, ids=[uid], column='T0', value='')
  result = self.rule_call('operate', result, ids=[uid], column='T0', operation='clear')
  self.assertEqual(result['table']['rows'][0]['T0'], '')

 def test_rule_query_uses_shared_filters_sort_and_pages_and_named_conflicts(self):
  p = sheets.empty_project()
  p['rules']['pool'] = [{'Unit Race':'Custom','Category':'infantry','BarracksTier':'T1','T0':n}
   for n in (3,1,2)]
  sheets.save_project(self.mod, p)
  result = self.rule_call('query', where={'column':'T0','op':'ge','value':2},
   sort=[{'column':'Unit Race'}, {'column':'T0','desc':True}], limit=1)
  self.assertEqual(result['table']['total'], 2)
  self.assertEqual(result['table']['rows'][0]['T0'], 3)
  self.assertEqual(result['rule_issues'][0]['code'], 'conflicting_duplicate_rule_key')
  self.assertEqual(len(result['rule_issues'][0]['ids']), 3)
  self.assertIn('Custom', result['rule_issues'][0]['message'])

 def test_rule_edited_path_matches_imported_balance(self):
  from unittransfer import buildings, edb_balance
  from tests.test_edb_balance import EDB
  self.mod.edb = buildings.parse_text(EDB)
  p = sheets.empty_project()
  p['units']['Guard'] = {'annotations':{'Unit Race':'Custom','Tier':'T1'}}
  imported = sheets.import_rules(p, 'Unit Race,Category,BarracksTier,T1\nCustom,infantry,T1,3\n', 'experience')
  sheets.save_project(self.mod, p)
  result = sheets.service(self.mod, 'query', {'view':'rules:experience'})
  def call(action, **body):
   return sheets.service(self.mod, action, dict(view='rules:experience',
    revision=result['revision'], source_token=result['source_token'], **body))
  result = call('rule_structure', operation='add_row')
  uid = result['table']['rows'][0]['id']
  result = call('paste', cells=[{'id':uid,'column':k,'value':v}
   for k,v in {'Unit Race':'Custom','Category':'infantry','BarracksTier':'T1','T1':'3'}.items()])
  self.assertEqual(edb_balance.run(self.mod, result['project'], ['experience'])['text'],
   edb_balance.run(self.mod, imported, ['experience'])['text'])

 def test_rule_legacy_dynamic_endpoints_keep_invalid_tokens_and_named_issues(self):
  p = sheets.empty_project()
  p['rules']['replenish'] = [{'Tier':'T1','Custom_Earliest':'bad','Custom_Latest':'0'}]
  sheets.config._write_json(sheets.project_path(self.mod), p)
  result = sheets.service(self.mod, 'query', {'view':'rules:replenish'})
  self.assertEqual(result['filter_info']['Custom_Earliest']['type'], 'number')
  self.assertEqual(result['table']['rows'][0]['Custom_Latest'], 0)
  self.assertEqual(result['rule_issues'][0]['code'], 'invalid_rule_value')
  self.assertIn('Custom_Earliest', result['table']['rows'][0]['invalid_columns'])

 def test_rule_custom_text_keys_and_structure_validation(self):
  result = self.rule_call('rule_structure', operation='add_column', column='Custom key', key=True)
  result = self.rule_call('rule_structure', result, operation='rename_column', column='Custom key', name='Renamed key')
  self.assertEqual(result['filter_info']['Renamed key']['type'], 'text')
  self.assertIn('Renamed key', result['frozen_columns'])
  result = self.rule_call('rule_structure', result, operation='add_row')
  uid = result['table']['rows'][0]['id']
  result = self.rule_call('operate', result, ids=[uid], column='Renamed key', value='Any race')
  for operation, body in [('add_column', {'column':'id'}),
    ('rename_column', {'column':'Renamed key','name':'T0'}),
    ('remove_rows', {'ids':['unknown']})]:
   with self.assertRaises(sheets.SheetError):
    self.rule_call('rule_structure', result, operation=operation, **body)
  bad = json.loads(json.dumps(result['project']))
  bad['rules']['pool'][0]['T0'] = 'bad'
  with self.assertRaises(sheets.SheetError):
   self.rule_call('save', result, project=bad)
  self.assertEqual(sheets.load_project(self.mod), result['project'])

 def test_rule_project_import_rejects_bad_numbers_transactionally(self):
  result = self.rule_call('rule_structure', operation='add_row')
  bad = json.loads(json.dumps(result['project']))
  bad['rules']['pool'][0]['T0'] = 'invalid'
  with self.assertRaises(sheets.SheetError):
   self.rule_call('import', result, kind='project', text=json.dumps(bad))
  self.assertEqual(sheets.load_project(self.mod), result['project'])


 def test_groups_roundtrip_rename_missing_members_and_selection_validation(self):
  result = sheets.service(self.mod,'load')
  def operate(operation, **extra):
   nonlocal result
   result = sheets.service(self.mod,'group',{'revision':result['revision'],
    'source_token':result['source_token'],'operation':operation,'name':'Archers',**extra})
   return result
  operate('create')
  operate('add',ids=['Guard','Horse'])
  self.assertEqual(sheets.load_project(self.mod)['groups']['Archers'],['Guard','Horse'])
  before = sheets.load_project(self.mod)
  for extra in ({'ids':['Guard','missing']},{'ids':['Guard'],'where':{'column':'id','value':'Horse'}},
                {'ids':['Guard'],'view':'rules:pool'}):
   with self.assertRaises(sheets.SheetError):
    operate('add',**extra)
   self.assertEqual(sheets.load_project(self.mod),before)
  self.mod.edu = edu.parse_text(TEXT.split('type Horse')[0])
  result = sheets.service(self.mod,'query',{'comparison_group':'Archers'})
  self.assertTrue(result['comparison_group']['members'][1]['missing'])
  operate('remove',ids=['Guard'])
  self.assertEqual(result['project']['groups']['Archers'],['Horse'])
  operate('rename',new_name='PikesHalberds')
  self.assertEqual(result['project']['groups'],{'PikesHalberds':['Horse']})
  operate('delete',name='PikesHalberds')
  self.assertEqual(result['project']['groups'],{})

 def test_group_schema_migrates_and_rejects_invalid_imports(self):
  p = sheets.empty_project()
  p.pop('groups',None)
  self.assertEqual(sheets.validate_project(p)['groups'],{})
  for groups in ([],{'':[]},{'A':['Guard','Guard']},{'A':[1]},{'A':'Guard'}):
   bad = sheets.empty_project()
   bad['groups'] = groups
   with self.assertRaises(sheets.SheetError):
    sheets.validate_project(bad)

if __name__=='__main__':unittest.main()
