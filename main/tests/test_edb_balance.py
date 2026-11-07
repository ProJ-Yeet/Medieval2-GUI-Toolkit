import copy,unittest
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

if __name__=='__main__':unittest.main()
