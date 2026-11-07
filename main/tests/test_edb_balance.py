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
  self.assertEqual([e['reason'] for e in entries],['','','','malformed_beast','fractional_pool_preserved','','missing_replenish_tier:T3','missing_replenish_endpoints:Human'])
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
   if entry['reason']:self.assertEqual(ex['rounding_steps'],[])
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


if __name__=='__main__':unittest.main()
