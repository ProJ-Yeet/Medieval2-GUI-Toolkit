import copy,re,unittest
from types import SimpleNamespace
from unittransfer import buildings,edu,edb_balance as balance,unit_sheets as sheets

EDB='''; original document
building barracks
{
 levels hut hall
 {
  hut city requires factions { england, }
  {
   capability
   {
    recruit_pool "Guard"  1   0.1  2  0  requires factions { england, } ; keep this
    recruit_pool "Horse" 0.5 0.02 0.5 0 ; fractional
    armour 1
   }
   upgrades
   {
    hall
   }
  }
  hall castle
  {
   capability
   {
    recruit_pool "Guard" 1 0.1 2 0
    recruit_pool "Missing" 1 0.1 2 0 ; missing unit
   }
   upgrades
   {
   }
  }
 }
}
'''
EDU='''type Guard
category infantry
class heavy
soldier guard, 60, 0, 1

type Horse
category cavalry
class heavy
soldier horse, 30, 0, 1
'''

class BalanceTests(unittest.TestCase):
 def test_pipeline_order_refresh_and_shared_document(self):
  before=copy.deepcopy(self.p)
  r=balance.run(self.mod,self.p,['pool','replenish','experience'])
  self.assertEqual(r['pipeline_order'],['refresh','classification','replenish','experience','pool'])
  self.assertEqual(r['stages'],list(balance.STAGES))
  self.assertEqual(r['logs']['experience']['all'][0]['explanation']['inputs']['per_turn'],'0.09')
  self.assertEqual(r['logs']['pool']['all'][0]['explanation']['inputs']['experience'],'3')
  self.assertEqual(self.p,before)
  self.assertIn('missing_classifications',r['refresh'])
 def test_every_outcome_has_field_reason_rule_and_group(self):
  self.mod.edb=buildings.parse_text(EDB.replace('recruit_pool "Missing" 1 0.1 2 0','recruit_pool "Missing"'))
  r=balance.run(self.mod,self.p)
  for stage,logs in r['logs'].items():
   for e in logs['all']:
    self.assertTrue(e['reason']);self.assertIn('rule',e)
    self.assertEqual(e['field'],{'replenish':'per_turn','experience':'experience','pool':'maximum'}[stage])
    self.assertGreater(e['line'],0)
   grouped=[e for group in r['groups'] for e in group['entries'] if e['stage']==stage]
   self.assertCountEqual(grouped,logs['all'])
  self.assertEqual(set(g['status'] for g in r['groups']),{'changed','skipped','invalid'})
  again=balance.run(self.mod,self.p,edb=buildings.parse_text(r['text']))
  self.assertIn('unchanged',{g['status'] for g in again['groups']})
 def test_cancellation_after_partial_calculation_is_pure(self):
  before=copy.deepcopy(self.p);calls=[]
  def cancelled():
   calls.append(1);return len(calls)>5
  with self.assertRaisesRegex(sheets.SheetError,'cancel'):
   balance.run(self.mod,self.p,cancelled=cancelled)
  self.assertEqual(self.mod.edb.to_text(),EDB);self.assertEqual(self.p,before)
 def test_full_pipeline_preserves_siblings_sections_and_mixed_newlines(self):
  sibling='''building untouched
{
 levels shrine
 {
  shrine
  {
   capability
   {
    happiness_bonus bonus 2 ; handwritten
   }
  }
 }
}'''
  text=EDB.replace('keep this','caf\xe9').replace('\n','\r\n')+sibling
  text=text.replace('    armour 1\r\n','    armour 1\n')
  text=text.replace('   upgrades\r\n','   faction_capability\r\n   {\r\n    recruit_pool "Guard" 1 0.1 2 0 requires factions { england, } ; special\r\n   }\r\n   upgrades\r\n',1)
  r=balance.run(self.mod,self.p,edb=buildings.parse_text(text))
  def mask(value):
   return re.sub(r'(recruit_pool "[^"]+"\s+\S+)(\s+)\S+(\s+)\S+(\s+)\S+',r'\1\2RATE\3MAX\4EXP',value)
  self.assertEqual(mask(r['text']).encode('latin-1'),mask(text).encode('latin-1'))
  self.assertTrue(r['text'].endswith(sibling))
  self.assertTrue(any(e['section']=='faction_capability' for e in r['logs']['pool']['all']))
 def setUp(self):
  self.mod=SimpleNamespace(edu=edu.parse_text(EDU),edb=buildings.parse_text(EDB))
  self.p=sheets.empty_project()
  self.p['units']={u:{'annotations':{'Unit Race':'Human','Tier':'T1'},'extra':{}} for u in ('Guard','Horse')}
  self.p['rules']['replenish']=[{'Tier':'T1','Human_Earliest':'10','Human_Latest':'5'}]
  for stage,value in [('experience','3'),('pool','4')]:
   self.p['rules'][stage]=[{'Unit Race':'Human','Category':cat,'BarracksTier':tier,'T1':value} for cat in ('infantry','cavalry') for tier in ('T1','T2')]
 def test_full_pipeline_preserves_original_and_comments_and_reconciles_logs(self):
  result=balance.run(self.mod,self.p)
  self.assertIn('"Guard"  1   0.09  4  3  requires factions { england, } ; keep this',result['text'])
  self.assertIn('"Guard" 1 0.2 4 3',result['text']);self.assertIn('armour 1',result['text'])
  self.assertEqual(self.mod.edb.to_text(),EDB)
  for stage in balance.STAGES:
   self.assertEqual(sum(result['logs'][stage]['counts'].values()),4)
   self.assertEqual(len(result['logs'][stage]['all']),4)
  self.assertEqual(result['logs']['experience']['counts']['changed'],3)
  self.assertIn('"Horse" 0.5 0.02 0.5 3 ; fractional',result['text'])
 def test_stages_change_only_selected_token(self):
  for stage,fragment in [('replenish','1   0.09  2  0'),('experience','1   0.1  2  3'),('pool','1   0.1  4  0')]:
   r=balance.run(self.mod,self.p,[stage]);self.assertIn(fragment,r['text']);self.assertEqual(list(r['logs']),[stage])
 def test_repeated_run_is_idempotent(self):
  a=balance.run(self.mod,self.p);b=balance.run(self.mod,self.p,edb=buildings.parse_text(a['text']))
  self.assertEqual(a['text'],b['text']);self.assertEqual(b['changed_fields'],0)
 def test_missing_endpoint_fallback_and_single_level_city_cavalry(self):
  self.p['rules']['replenish'][0]['Human_Earliest']='N/A'
  chain=self.mod.edb.buildings[0];chain.blocks=chain.blocks[:1];chain.levels=['hut'];chain.blocks[0].upgrades=[]
  self.p['balance_profile']={'fractional_pool_exception':False}
  result=balance.run(self.mod,self.p,['replenish'])
  values=result['logs']['replenish']['all'];self.assertEqual(values[0]['after'],'0.18');self.assertEqual(values[1]['after'],'0.144')
 def test_beast_mapping_and_malformed_label(self):
  self.p['units']['Guard']['annotations']['Unit Race']='Beast Human'
  self.p['rules']['replenish'].append({'Tier':'Beast','Human_Earliest':20,'Human_Latest':10})
  self.assertEqual(balance.run(self.mod,self.p,['replenish'])['logs']['replenish']['all'][0]['after'],'0.045')
  self.p['units']['Guard']['annotations']['Unit Race']='Beast'
  self.assertEqual(balance.run(self.mod,self.p,['replenish'])['logs']['replenish']['all'][0]['reason'],'malformed_beast')
 def test_bg_invalid_values_and_duplicate_keys_never_become_zero(self):
  self.p['units']['Guard']['annotations']['Tier']='BG'
  r=balance.run(self.mod,self.p,['experience']);self.assertEqual(r['logs']['experience']['all'][0]['reason'],'unsupported_unit_tier:BG')
  self.p['units']['Guard']['annotations']['Tier']='T1';self.p['rules']['experience'][0]['T1']='NaN'
  r=balance.run(self.mod,self.p,['experience']);self.assertEqual(r['logs']['experience']['all'][0]['status'],'invalid')
  self.p['rules']['experience'].append(copy.deepcopy(self.p['rules']['experience'][0]))
  with self.assertRaises(sheets.SheetError):balance.run(self.mod,self.p)
 def test_beast_cavalry_keeps_original_category_multiplier_for_replenish(self):
  self.p['units']['Horse']['annotations']['Unit Race']='Beast Human';self.p['balance_profile']={'fractional_pool_exception':False}
  self.p['rules']['replenish'].append({'Tier':'Beast','Human_Earliest':20,'Human_Latest':10})
  entry=balance.run(self.mod,self.p,['replenish'])['logs']['replenish']['all'][1]
  self.assertEqual(entry['after'],'0.036');self.assertEqual(entry['explanation']['cavalry_multiplier'],.8)
 def test_graph_cycle_and_unknown_target_have_no_tier_zero_fallback(self):
  chain=self.mod.edb.buildings[0];chain.blocks[1].upgrades=['hut']
  g=balance.graph(chain);self.assertIn('cycle',g['errors']);self.assertEqual(g['depths'],{})
  r=balance.run(self.mod,self.p);self.assertEqual(r['text'],EDB)
  chain.blocks[1].upgrades=['absent'];self.assertIn('unknown_upgrade',balance.graph(chain)['errors'])
 def test_branch_merge_and_disconnected_policy(self):
  chain=buildings.BuildingLine(name='x',levels=['a','b','c','d'],blocks=[buildings.LevelBlock(name=n) for n in 'abcd'])
  a,b,c,d=chain.blocks;a.upgrades=['b','c'];b.upgrades=['c'];g=balance.graph(chain)
  self.assertEqual(g['depths'],{'a':0,'d':0,'b':1,'c':1});self.assertIn('unequal_merge:c',g['notes'])
  self.assertIn('ambiguous_depth',balance.graph(chain,'reject_ambiguous')['errors'])
 def test_explicit_override_and_conflict(self):
  self.p['balance_overrides']=[{'stage':'experience','unit':'Missing','value':7}]
  r=balance.run(self.mod,self.p,['experience']);self.assertEqual(r['logs']['experience']['all'][3]['after'],'7')
  self.p['balance_overrides'].append({'stage':'experience','unit':'Missing','value':8})
  r=balance.run(self.mod,self.p,['experience']);self.assertEqual(r['logs']['experience']['all'][3]['reason'],'conflicting_overrides')
 def test_invalid_original_numbers_and_missing_slots_are_logged(self):
  edb=buildings.parse_text(EDB.replace('"Guard"  1   0.1  2  0','"Guard" 1 requires factions'))
  r=balance.run(self.mod,self.p,['pool'],edb);self.assertEqual(r['logs']['pool']['all'][0]['status'],'invalid')
 def test_crlf_and_non_ascii_roundtrip_except_changed_digits(self):
  edb=buildings.parse_text(EDB.replace('keep this','café').replace('\n','\r\n'))
  r=balance.run(self.mod,self.p,['experience'],edb)
  self.assertEqual(r['text'].replace('  3  requires','  0  requires').replace('0.5 3 ;','0.5 0 ;').replace('2 3\r','2 0\r'),edb.to_text())

def golden_chain(name,levels,edges,headers=None,units=('Guard',)):
 """Small parser fixture, never sourced from a mod or reference document."""
 headers=headers or {}
 lines=['building '+name,'{',' levels '+' '.join(levels),' {']
 for level in levels:
  lines+=['  '+level+(' '+headers[level] if headers.get(level) else '')+' requires factions { england, }','  {','   capability','   {']
  lines += ['    recruit_pool "'+u+'"  1.25\t0.03125  '+('0.5' if u=='Fraction' else '2.50')+'  3 requires factions { england, } and hidden_resource test ; cafe' for u in units]
  lines+=['   }','   upgrades','   {']+['    '+x for x in edges.get(level,[])]+['   }','  }']
 return '\n'.join(lines+[' }','}',''])


class ReplenishmentGoldenTests(unittest.TestCase):
 def setUp(self):
  helper=BalanceTests();helper.setUp();self.p=helper.p
  self.units=('Guard','Horse','Beast','BadBeast','Fraction','Fallback','NoRule','NoEndpoints')
  text=EDU+''.join('\ntype '+u+'\ncategory infantry\nclass heavy\nsoldier guard, 60, 0, 1\n' for u in self.units[2:])
  self.edu=edu.parse_text(text)
  for u in self.units:self.p['units'][u]={'annotations':{'Unit Race':'Human','Tier':'T1'},'extra':{}}
  for u,race,tier in [('Beast','Beast Human','T1'),('BadBeast','Beast','T1'),('Fallback','Human','T2'),('NoRule','Human','T3'),('NoEndpoints','Human','T4')]:
   self.p['units'][u]['annotations']={'Unit Race':race,'Tier':tier}
  self.p['rules']['replenish'] += [{'Tier':'Beast','Human_Earliest':'20','Human_Latest':'10'},
   {'Tier':'T2','Human_Earliest':'N/A','Human_Latest':'8'}, {'Tier':'T4','Human_Earliest':'N/A','Human_Latest':'MISSING'}]
 def run_text(self,text):
  return balance.run(SimpleNamespace(edu=self.edu,edb=buildings.parse_text(text)),self.p,['replenish'])
 def entries(self,text):return self.run_text(text)['logs']['replenish']['all']
 def test_single_level_reference_goldens_and_named_exceptions(self):
  # E=10 alone gives .1; city .09; cavalry .072; Beast E=20 gives .045.
  entries=self.entries(golden_chain('single',['a'],{}, {'a':'city'},self.units))
  self.assertEqual([e['after'] for e in entries],['0.09','0.072','0.045','0.03125','0.03125','0.1125','0.03125','0.03125'])
  self.assertEqual([e['reason'] for e in entries],['changed','changed','changed','malformed_beast','fractional_pool_preserved','changed','missing_replenish_tier:T3','missing_replenish_endpoints:Human'])
  self.assertEqual([e['status'] for e in entries],['changed','changed','changed','invalid','skipped','changed','skipped','skipped'])
 def test_three_level_linear_reference_golden(self):
  # X=10, 7.5, 5; reciprocals .1, .133333, .2, then each own header.
  entries=self.entries(golden_chain('linear',['a','b','c'],{'a':['b'],'b':['c']},{'a':'city','b':'castle'}))
  self.assertEqual([e['after'] for e in entries],['0.09','0.133333','0.2'])
  self.assertEqual([e['explanation']['depth'] for e in entries],[0,1,2])
  self.assertEqual([e['settlement'] for e in entries],['city','castle','unspecified'])
 def test_per_level_header_compatibility_exception_hall_is_point_2_not_legacy_point_18(self):
  result=self.run_text(EDB);entry=result['logs']['replenish']['all'][2]
  self.assertEqual(entry['after'],'0.2')
  self.assertEqual(entry['explanation']['settlement_policy'],'per_level_header')
  self.assertEqual(entry['explanation']['settlement'],'castle')
 def test_branched_equal_merge_and_disconnected_goldens_under_both_policies(self):
  fixtures=[(['a','b','c','d'],{'a':['b','c'],'b':['d']},['0.1','0.133333','0.133333','0.2']),
   (['a','b','c','d'],{'a':['b','c'],'b':['d'],'c':['d']},['0.1','0.133333','0.133333','0.2']),
   (['a','b','c','island'],{'a':['b'],'b':['c']},['0.1','0.133333','0.2','0.1'])]
  for policy in ('shortest','reject_ambiguous'):
   self.p['balance_profile']={'branch_policy':policy}
   for levels,edges,expected in fixtures:
    with self.subTest(policy=policy,edges=edges):self.assertEqual([e['after'] for e in self.entries(golden_chain('graph',levels,edges))],expected)
 def test_unequal_merge_shortest_root_or_named_rejection(self):
  text=golden_chain('merge',['a','b','c'],{'a':['b','c'],'b':['c']})
  self.assertEqual([e['after'] for e in self.entries(text)],['0.1','0.2','0.2'])
  self.p['balance_profile']={'branch_policy':'reject_ambiguous'}
  entries=self.entries(text)
  self.assertEqual([e['reason'] for e in entries],['invalid_building_graph:ambiguous_depth']*3)
  self.assertTrue(all(e['before']==e['after'] for e in entries))
 def test_cycle_and_unknown_target_preserve_values_without_guessing_depth(self):
  for policy in ('shortest','reject_ambiguous'):
   self.p['balance_profile']={'branch_policy':policy}
   for edges,reason in [({'a':['b'],'b':['a']},'cycle'),({'a':['absent']},'unknown_upgrade')]:
    entries=self.entries(golden_chain('bad',['a','b'],edges))
    self.assertTrue(all(e['reason']=='invalid_building_graph:'+reason for e in entries))
    self.assertTrue(all(e['after']=='0.03125' for e in entries))
    if reason=='cycle':self.assertTrue(all(e['explanation']['depth'] is None for e in entries))
 def test_missing_latest_uses_earliest_and_invalid_endpoints_are_named(self):
  rule=self.p['rules']['replenish'][0];rule['Human_Latest']='N/A'
  self.assertEqual([e['after'] for e in self.entries(golden_chain('x',['a','b'],{'a':['b']}))],['0.1','0.1'])
  for value,reason in [('0','nonpositive_replenish_interval'),('NaN','invalid_number')]:
   rule['Human_Earliest']=value
   self.assertEqual(self.entries(golden_chain('x',['a'],{}))[0]['reason'],reason)
 def test_rounding_boundaries_reciprocal_then_sequential_multipliers(self):
  # Explicit decimals straddle a six-place boundary, with exact binary ties too.
  # 1/128=.0078125 ties to .007812; 1/640=.0015625 ties to .001563.
  for turns,reciprocal,expected in [('3',.333333,'0.24'),('7',.142857,'0.102857'),
    ('128',.007812,'0.005625'),('640',.001563,'0.001125'),
    ('9.99995',.100001,'0.072001'),('10.00005',.1,'0.072')]:
   self.p['rules']['replenish'][0].update(Human_Earliest=turns,Human_Latest=turns)
   e=self.entries(golden_chain('round',['a'],{}, {'a':'city'},('Horse',)))[0]
   with self.subTest(turns=turns):
    self.assertEqual(e['after'],expected);self.assertEqual(e['explanation']['reciprocal'],reciprocal)
    self.assertEqual(e['explanation']['rounding_steps'][0],{'operation':'reciprocal','input':1/float(turns),'digits':6,'output':reciprocal})
    self.assertEqual(e['explanation']['rounding_steps'][-1]['output'],float(expected))
 def test_every_outcome_retains_exact_inputs_and_only_performed_steps(self):
  entries=self.entries(golden_chain('single',['a'],{}, {'a':'city'},self.units))
  for entry in entries:
   ex=entry['explanation']
   self.assertEqual(ex['inputs']['per_turn'],'0.03125')
   self.assertEqual(ex['inputs']['maximum'],'0.5' if entry['unit']=='Fraction' else '2.50')
   self.assertEqual(ex['inputs']['annotations'],self.p['units'][entry['unit']]['annotations'])
   self.assertEqual(ex['depth'],0);self.assertEqual(ex['max_depth'],0)
   self.assertEqual(ex['branch_policy'],'shortest');self.assertEqual(ex['settlement_policy'],'per_level_header')
   self.assertEqual(ex['outcome'],entry['reason'] or entry['status'])
   if entry['status'] in ('skipped','invalid'):self.assertEqual(ex['rounding_steps'],[])
  ex=entries[5]['explanation']
  self.assertEqual(ex['endpoint_inputs'],{'earliest':'N/A','latest':'8'})
  self.assertEqual((ex['earliest'],ex['latest'],ex['interval']),(8,8,8))
  self.assertEqual(ex['endpoint_fallback'],'earliest_from_latest')
  self.assertEqual(ex['rounding_steps'][1],{'operation':'city_multiplier','input':.125,'multiplier':.9,'output':.1125})
 def test_replenish_only_is_byte_identical_outside_rate_and_idempotent(self):
  text=golden_chain('all',['a','b','c'],{'a':['b'],'b':['c']},{'a':'city','b':'castle'},self.units).replace('cafe','caf\xe9').replace('\n','\r\n')
  a=self.run_text(text);b=self.run_text(a['text'])
  # Mask only the rate token, compare every remaining byte including conditions.
  mask=lambda s:re.sub(r'(recruit_pool "[^"]+"\s+\S+\s+)\S+',r'\1<RATE>',s).encode('latin-1')
  self.assertEqual(mask(a['text']),mask(text));self.assertEqual(b['text'].encode('latin-1'),a['text'].encode('latin-1'))
  self.assertEqual(b['changed_fields'],0)


class LookupGoldenTests(unittest.TestCase):
 def setUp(self):
  self.p=sheets.empty_project()
  self.units=('Guard','Beast','BG','NoTier','NoRow','NoColumn','Invalid','Unsupported','Fraction','Override')
  self.edu=edu.parse_text(''.join('type '+u+'\ncategory infantry\nclass heavy\nsoldier guard, 60, 0, 1\n\n' for u in self.units))
  for u in self.units:self.p['units'][u]={'annotations':{'Unit Race':'Aurora','Tier':'T1'},'extra':{}}
  for u,race,tier in [('Beast','Beast Aurora','T2'),('BG','Aurora','BG'),('NoTier','Aurora',''),('NoRow','Absent','T1'),('NoColumn','Aurora','T4'),('Invalid','Aurora','T3')]:
   self.p['units'][u]['annotations']={'Unit Race':race,'Tier':tier}
  self.p['units']['Unsupported']['category_override']='ship'
  # Hand lookup: depth 0..5 selects T1,T2,T3,T4,T5,T5, then unit column.
  # The invented race proves keys belong to the project, not a global race list.
  for stage in ('experience','pool'):
   self.p['rules'][stage]=[{'Unit Race':'Aurora','Category':cat,'BarracksTier':'T'+str(i),
    'T0':1,'T1':i,'T2':i+1,'T3':'NaN'} for cat in ('infantry','beast') for i in range(1,6)]
  self.p['balance_overrides']=[{'stage':stage,'unit':'Override','value':6} for stage in ('experience','pool')]
  self.p['balance_overrides'] += [{'stage':stage,'unit':'Override','building':'lookup','level':'a','value':8} for stage in ('experience','pool')]
  self.text=golden_chain('lookup',list('abcdef'),{a:[b] for a,b in zip('abcde','bcdef')},units=self.units).replace('cafe','caf\xe9').replace('\n','\r\n')
 def run_text(self,stage,text=None):
  return balance.run(SimpleNamespace(edu=self.edu,edb=buildings.parse_text(self.text if text is None else text)),self.p,[stage])
 def test_reference_values_cap_beast_and_named_outcomes(self):
  for stage in ('experience','pool'):
   result=self.run_text(stage);entries=result['logs'][stage]['all']
   self.assertEqual([e['after'] for e in entries if e['unit']=='Guard'],['1','2','3','4','5','5'])
   self.assertEqual([e['after'] for e in entries if e['unit']=='Beast'],['2','3','4','5','6','6'])
   first={e['unit']:e for e in entries[:len(self.units)]}
   reasons={'BG':'unsupported_unit_tier:BG','NoTier':'missing_tier',
    'NoRow':"missing_lookup_row:('Absent', 'infantry', 'T1')",'NoColumn':'missing_lookup_value:T4',
    'Invalid':'invalid_number','Unsupported':'unsupported_unit_category:ship'}
   if stage=='pool':reasons['Fraction']='fractional_pool_preserved'
   for unit,reason in reasons.items():
    with self.subTest(stage=stage,unit=unit):
     self.assertEqual(first[unit]['reason'],reason)
     self.assertEqual(first[unit]['after'],first[unit]['before'])
   self.assertEqual(first['Fraction']['after'],'1' if stage=='experience' else '0.5')
   self.assertEqual(first['Override']['after'],'8')
   self.assertEqual([e['after'] for e in entries if e['unit']=='Override'],['8','6','6','6','6','6'])
 def test_every_outcome_explains_lookup_inputs_even_skips_and_overrides(self):
  for stage in ('experience','pool'):
   entries=self.run_text(stage)['logs'][stage]['all']
   for e in entries:
    with self.subTest(stage=stage,unit=e['unit'],level=e['level']):
     ex=e['explanation'];a=self.p['units'][e['unit']]['annotations'];depth='abcdef'.index(e['level'])
     race='Aurora' if e['unit']=='Beast' else a['Unit Race']
     category='beast' if e['unit']=='Beast' else ('ship' if e['unit']=='Unsupported' else 'infantry')
     self.assertEqual((ex['race'],ex['category'],ex['tier']),(race,category,a['Tier']))
     self.assertEqual((ex['depth'],ex['barracks_tier']),(depth,'T'+str(min(depth+1,5))))
     self.assertEqual(ex['rule_key'],(race,category,ex['barracks_tier']))
     self.assertEqual(ex['lookup_column'],a['Tier'])
     self.assertIn('lookup_value',ex);self.assertIn('lookup_row_found',ex)
     self.assertEqual(ex['override'],e['unit']=='Override')
     if e['unit']=='Invalid':self.assertEqual(ex['lookup_value'],'NaN')
     if e['unit']=='Override':
      self.assertEqual(ex['override_input'],8 if depth==0 else 6)
      self.assertEqual(ex['override_selector'],{'unit':'Override','building':'lookup','level':'a'} if depth==0 else {'unit':'Override'})
     self.assertEqual(ex['outcome'],e['reason'] or e['status'])
 def test_independent_stages_preserve_all_other_bytes_skips_and_repeat(self):
  for stage,slot in [('experience',3),('pool',2)]:
   a=self.run_text(stage);b=self.run_text(stage,a['text'])
   def mask(text):
    pattern=r'(recruit_pool "[^"\r\n]+"(?:[ \t]+[^\s;]+){'+str(slot)+r'}[ \t]+)[^\s;]+'
    return re.sub(pattern,r'\1<VALUE>',text).encode('latin-1')
   self.assertEqual(mask(a['text']),mask(self.text))
   before=self.text.splitlines(keepends=True);after=a['text'].splitlines(keepends=True)
   for e in a['logs'][stage]['issues']:self.assertEqual(after[e['line']-1],before[e['line']-1])
   self.assertEqual(a['text'],b['text']);self.assertEqual(b['changed_fields'],0)
 def test_each_unit_tier_selects_its_own_column(self):
  for stage in ('experience','pool'):
   for row in self.p['rules'][stage]:row.update(T0=1,T1=2,T2=4,T3=5,T4=6)
   for tier,value in [('T0','1'),('T1','2'),('T2','4'),('T3','5'),('T4','6')]:
    self.p['units']['Guard']['annotations']['Tier']=tier
    e=self.run_text(stage)['logs'][stage]['all'][0]
    self.assertEqual(e['after'],value)

 def test_legacy_table_samples_at_known_depths(self):
  # Literal cells read from Barracks_tiers_exp/pool.csv, never loaded at test time.
  self.p['units']['Guard']['annotations']={'Unit Race':'Elf','Tier':'T1'}
  self.p['units']['Beast']['annotations']={'Unit Race':'Beast Elf','Tier':'T2'}
  samples={'experience':{'infantry':[(2,2,1,0,0),(2,2,1,1,0),(3,2,2,1,1)],
                         'beast':[(2,2,1,0,0),(2,2,1,1,0),(3,2,2,1,1)]},
           'pool':{'infantry':[(4,4,3,2,2),(5,5,4,2,2),(6,5,4,3,2)],
                   'beast':[(4,3,3,2,2),(4,3,3,3,2),(4,4,3,3,2)]}}
  text=golden_chain('sample',list('abcdef'),{a:[b] for a,b in zip('abcde','bcdef')},units=('Guard','Beast'))
  # Keep the full graph but recruit only at depths 2..5: T3,T4,T5,T5.
  lines=text.splitlines(keepends=True);count=0
  for i,line in enumerate(lines):
   if 'recruit_pool' in line:
    count+=1
    if count<=4:lines[i]=''
  for stage,categories in samples.items():
   self.p['rules'][stage]=[{'Unit Race':'Elf','Category':cat,'BarracksTier':'T'+str(depth),
    **dict(zip(('T0','T1','T2','T3','T4'),values))} for cat,rows in categories.items() for depth,values in zip((3,4,5),rows)]
   entries=self.run_text(stage,''.join(lines))['logs'][stage]['all']
   self.assertEqual([e['after'] for e in entries],['2','1','2','1','2','2','2','2'] if stage=='experience' else ['4','3','5','3','5','3','5','3'])
 def test_overrides_bypass_fractional_and_classification_skips(self):
  for stage in ('experience','pool'):
   self.p['balance_overrides'] += [{'stage':stage,'unit':u,'building':'lookup','level':'a','value':7} for u in ('Fraction','BG','NoTier','Unsupported')]
   entries=self.run_text(stage)['logs'][stage]['all'][:len(self.units)]
   for e in entries:
    if e['unit'] in ('Fraction','BG','NoTier','Unsupported'):
     self.assertEqual(e['after'],'7');self.assertTrue(e['explanation']['override'])

 def test_category_becomes_supported_when_added_to_project_tables(self):
  for stage in ('experience','pool'):
   self.p['rules'][stage] += [{**r,'Category':'ship'} for r in self.p['rules'][stage] if r['Category']=='infantry']
   entry=next(e for e in self.run_text(stage)['logs'][stage]['all'] if e['unit']=='Unsupported')
   self.assertEqual(entry['after'],'1');self.assertEqual(entry['reason'],'changed')
 def test_conflicting_override_outcome_keeps_all_matching_selectors_and_values(self):
  for stage in ('experience','pool'):
   self.p['balance_overrides'].append({'stage':stage,'unit':'Override','building':'lookup','level':'a','value':9})
   e=next(e for e in self.run_text(stage)['logs'][stage]['all'] if e['unit']=='Override')
   self.assertEqual(e['reason'],'conflicting_overrides');self.assertEqual(e['after'],e['before'])
   self.assertEqual(e['explanation']['override_candidates'],[
    {'selector':{'unit':'Override'},'value':6},
    {'selector':{'unit':'Override','building':'lookup','level':'a'},'value':8},
    {'selector':{'unit':'Override','building':'lookup','level':'a'},'value':9}])

 def test_conflicting_duplicate_keys_refuse_run(self):
  for stage in ('experience','pool'):
   p=copy.deepcopy(self.p);r=copy.deepcopy(p['rules'][stage][0]);r['T1']=9;p['rules'][stage].append(r)
   with self.assertRaisesRegex(sheets.SheetError,'duplicate rule key'):
    balance.run(SimpleNamespace(edu=self.edu,edb=buildings.parse_text(self.text)),p,[stage])


if __name__=='__main__':unittest.main()
