import base64,copy,io,json,tempfile,unittest,zipfile
import subprocess,threading,urllib.request,urllib.error
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from unittransfer import buildings,config,edb_balance as balance,unit_sheets as sheets
from unittransfer.mod import Mod
from unittransfer.transfer import undo
from tests import test_edb_balance as fixture
EDB,EDU=fixture.EDB,fixture.EDU

class PipelineTests(unittest.TestCase):
 @contextmanager
 def http_fixture(self):
  from unittransfer import server
  class FixtureHandler(server.Handler):
   registry=SimpleNamespace(get=lambda name:Mod(self.data.parent),invalidate=lambda name:None)
  httpd=server._Server(('127.0.0.1',0),FixtureHandler)
  thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
  try:yield 'http://127.0.0.1:'+str(httpd.server_port)
  finally:httpd.shutdown();httpd.server_close();thread.join(5)
 def test_normal_ui_preview_export_apply_and_log_undo_over_http(self):
  # Run the actual UI handlers, including settings.js Log Undo, against the
  # actual HTTP routes. Only DOM painting primitives are represented by stubs.
  script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const base=process.argv[1],calls=[];
const c={console,Set,Map,Promise,setTimeout,clearTimeout,structuredClone,confirm:()=>true,
 state:{src:'fixture'},modal:{innerHTML:'',querySelector:()=>null,
 querySelectorAll:s=>s==='.us-stage:checked'?['pool','experience','replenish'].map(value=>({value})):[]},
 overlay:{classList:{add(){}}},document:{getElementById:()=>({checked:true}),createElement:()=>({click(){}})},
 tt:(key,p)=>key,ttA:key=>key,esc:s=>String(s),toast(){},errText:e=>e.message,
 URL:{createObjectURL:()=>'',revokeObjectURL(){}},Blob,Uint8Array,atob,
 api:{post:async(url,body)=>{calls.push({url,body});const r=await fetch(base+url,{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json();}}};
vm.createContext(c);
vm.runInContext(fs.readFileSync('web/js/unitsheets.js','utf8'),c);
vm.runInContext(fs.readFileSync('web/js/settings.js','utf8'),c);
(async()=>{
 await c.unitSheetsOpen();await c.unitSheetsBalancePreview();
 const p=vm.runInContext('USHEET.balance',c);assert(p.changed_fields>0);
 assert.deepEqual(Array.from(p.pipeline_order),['refresh','classification','replenish','experience','pool']);
 await c.unitSheetsBalanceExport();await c.unitSheetsBalanceApply();
 const id=vm.runInContext('USHEET.lastBalanceApply',c);assert(id);
 assert(c.unitSheetsBalanceHtml().includes('openLog()'));
 c.openLog=()=>{};await c.doUndo(id);
 assert(calls.some(x=>x.url==='/api/undo'&&x.body.id===id));
 const refused=calls.filter(x=>x.url.endsWith('balance_apply'));assert.equal(refused.length,1);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
  with self.http_fixture() as base:
   result=subprocess.run(['node','-e',script,base],capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
  records=config.load_log();self.assertEqual(len(records),1);self.assertTrue(records[0]['undone'])
 def test_http_cancellation_is_not_blocked_by_running_sheet_lock(self):
  from unittransfer import server
  entered=threading.Event();release=threading.Event();calculate=balance.calculate
  def gate(*args,**kwargs):
   entered.set();self.assertTrue(release.wait(5));return calculate(*args,**kwargs)
  def post(base,path,body):
   request=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   try:
    with opener.open(request,timeout=10) as response:return json.load(response)
   except urllib.error.HTTPError as error:return json.load(error)
  for action in ('balance_preview','balance_export'):
   body={**self.body(),'mod':'fixture','job':'fixture-'+action};before=sheets.project_path(self.mod).read_bytes();result=[]
   entered.clear();release.clear()
   with self.http_fixture() as base,patch.object(balance,'calculate',gate):
    thread=threading.Thread(target=lambda:result.append(post(base,'/api/unit_sheets/'+action,body)))
    thread.start()
    try:
     self.assertTrue(entered.wait(5))
     self.assertTrue(post(base,'/api/progress/cancel',{'job':body['job']})['ok'])
    finally:release.set();thread.join(10)
   self.assertFalse(thread.is_alive());self.assertIn('cancel',result[0]['error'].lower())
   self.assertFalse(server._progress_cancelled(body['job']))
   self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
 def test_apply_is_captured_by_my_changes_and_undo_clears_it(self):
  from unittransfer import changesets
  config.save_settings(med2_root=str(self.root))
  p=sheets.service(self.mod,'balance_preview',self.body())
  r=sheets.service(self.mod,'balance_apply',{**self.body(),'plan_token':p['plan_token']})
  summary=changesets.summary(self.mod)
  self.assertEqual([f['rel'] for f in summary['files']],['export_descr_buildings.txt'])
  self.assertEqual(summary['files'][0]['disk'],'same')
  undo(r['record']['id']);self.assertEqual(changesets.summary(self.mod)['files'],[])
 def test_failed_apply_rolls_back_my_changes_too(self):
  from unittransfer import changesets
  config.save_settings(med2_root=str(self.root))
  p=sheets.service(self.mod,'balance_preview',self.body())
  with patch.object(config,'append_log',side_effect=OSError('full disk')):
   with self.assertRaises(OSError):
    sheets.service(self.mod,'balance_apply',{**self.body(),'plan_token':p['plan_token']})
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
  self.assertEqual(changesets.summary(self.mod)['files'],[])
 def test_large_grouped_preview_covers_rows_beyond_compact_log_limit(self):
  text=self.original.replace(b'    armour 1',b'    recruit_pool "Guard" 1 0.1 2 0\r\n'*110+b'    armour 1')
  self.mod.edb_path.write_bytes(text)
  p=sheets.service(self.mod,'balance_preview',self.body())
  for stage in balance.STAGES:
   self.assertTrue(p['logs'][stage]['truncated']);self.assertEqual(len(p['logs'][stage]['all']),100)
   grouped=[e for g in p['groups'] for e in g['entries'] if e['stage']==stage]
   self.assertEqual(len(grouped),114)
   self.assertTrue(all('explanation' not in e for e in grouped))
   self.assertTrue(all(all(k in e for k in ('line','before','after','reason','rule')) for e in grouped))
   self.assertEqual(sum(p['logs'][stage]['counts'].values()),len(grouped))
  self.assertEqual(self.mod.edb_path.read_bytes(),text)
 def test_failed_or_invalid_runs_do_not_change_saved_state(self):
  body=self.body();before=sheets.project_path(self.mod).read_bytes()
  for action in ('balance_preview','balance_export'):
   with patch.object(balance,'calculate',side_effect=RuntimeError('calculation interrupted')):
    with self.assertRaisesRegex(RuntimeError,'interrupted'):sheets.service(self.mod,action,body)
   with self.assertRaises(sheets.SheetError):sheets.service(self.mod,action,{**body,'stages':['unknown']})
   self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
   self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
 def test_cancelled_preview_does_not_persist_legacy_project_migration(self):
  legacy=sheets.load_project(self.mod)
  for rows in legacy['rules'].values():
   for row in rows:row.pop('id',None)
  path=sheets.project_path(self.mod);path.write_text(json.dumps(legacy),encoding='utf-8')
  before=path.read_bytes();p=sheets.load_project(self.mod,persist_migration=False)
  body={'revision':sheets.revision(p),'source_token':sheets.source_token(self.mod)}
  with self.assertRaises(sheets.SheetError):sheets.service(self.mod,'balance_preview',body,cancelled=lambda:True)
  self.assertEqual(path.read_bytes(),before)
 def test_cancel_preview_and_export_preserve_edb_and_project(self):
  for action in ('balance_preview','balance_export'):
   with self.subTest(action=action):
    body=self.body();before=sheets.project_path(self.mod).read_bytes();calls=[]
    def cancelled():
     calls.append(1);return len(calls)>7
    with self.assertRaisesRegex(sheets.SheetError,'cancel'):
     sheets.service(self.mod,action,body,cancelled=cancelled)
    self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
    self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)
 def test_cancel_during_zip_generation_discards_bundle(self):
  cancelled=False;write=zipfile.ZipFile.writestr
  def interrupt(bundle,*args,**kwargs):
   nonlocal cancelled
   result=write(bundle,*args,**kwargs);cancelled=True;return result
  with patch.object(zipfile.ZipFile,'writestr',interrupt):
   with self.assertRaisesRegex(sheets.SheetError,'cancel'):
    sheets.service(self.mod,'balance_export',self.body(),cancelled=lambda:cancelled)
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_counts_preview_complete_logs_and_export_agree(self):
  body=self.body();p=sheets.service(self.mod,'balance_preview',body)
  exported=sheets.service(self.mod,'balance_export',{**body,'intermediate':True})
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported['text']))) as z:
   summary=json.loads(z.read('pipeline.json'))
   self.assertEqual(summary['pipeline_order'],p['pipeline_order'])
   self.assertEqual(summary['changed_fields'],p['changed_fields'])
   self.assertEqual(p['changed_fields'],sum(logs['counts'].get('changed',0) for logs in p['logs'].values()))
   self.assertIn('export_descr_buildings_exp.txt',z.namelist())
   for stage in balance.STAGES:
    entries=json.loads(z.read('logs/'+stage+'_all.json'))
    self.assertEqual(summary['counts'][stage],p['logs'][stage]['counts'])
    self.assertEqual(sum(p['logs'][stage]['counts'].values()),len(entries))
    self.assertEqual(json.loads(json.dumps(p['logs'][stage]['all'])),entries)
   applied=sheets.service(self.mod,'balance_apply',{**body,'plan_token':p['plan_token']})
   self.assertEqual(self.mod.edb_path.read_bytes(),z.read('export_descr_buildings_new.txt'))
  self.assertEqual(len(config.load_log()),1)
  self.assertEqual(sheets.service(self.mod,'balance_preview',self.body())['changed_fields'],0)
  undo(applied['record']['id']);self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_mid_write_failure_keeps_original_bytes(self):
  preview=balance.preview(self.mod,self.project);fdopen=buildings.os.fdopen
  class Interrupted:
   def __init__(self,fd,*args):self.out=fdopen(fd,*args)
   def __enter__(self):return self
   def __exit__(self,*args):self.out.close()
   def write(self,blob):self.out.write(blob[:17]);raise OSError('interrupted mid-write')
  with patch.object(buildings.os,'fdopen',Interrupted):
   with self.assertRaisesRegex(OSError,'mid-write'):
    balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
  self.assertEqual(list(self.data.glob('*.tmp')),[]);self.assertEqual(config.load_log(),[])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.data=self.root/'mods/fixture/data';self.data.mkdir(parents=True)
  (self.data/'export_descr_unit.txt').write_bytes(EDU.encode('latin-1'))
  self.original=EDB.replace('keep this','café').replace('\n','\r\n').encode('latin-1')
  (self.data/'export_descr_buildings.txt').write_bytes(self.original)
  self.mod=Mod(self.data.parent)
  for key,value in [('CONFIG_DIR',self.root/'config'),('BACKUP_DIR',self.root/'config/backups'),('LOG_PATH',self.root/'config/transfers.json'),('SETTINGS_PATH',self.root/'config/settings.json')]:
   p=patch.object(config,key,value);p.start();self.addCleanup(p.stop)
  helper=fixture.BalanceTests();helper.setUp();self.project=helper.p
  sheets.save_project(self.mod,self.project)
 def body(self):
  d=sheets.service(self.mod,'load');return {'revision':d['revision'],'source_token':d['source_token']}
 def test_export_complete_bundle_and_intermediates_is_read_only(self):
  body=self.body();result=sheets.service(self.mod,'balance_export',{**body,'intermediate':True})
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['text']))) as z:
   self.assertIn('export_descr_buildings_new.txt',z.namelist());self.assertIn('export_descr_buildings_r.txt',z.namelist())
   for stage in balance.STAGES:
    all_=json.loads(z.read('logs/'+stage+'_all.json'));issues=json.loads(z.read('logs/'+stage+'_skip_error.json'))
    self.assertEqual(len(all_),4);self.assertEqual(issues,[e for e in all_ if e['status'] in ('invalid','skipped')])
   self.assertIn(b'caf\xe9\r\n',z.read('export_descr_buildings_new.txt'))
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_apply_then_log_undo_restores_exact_bytes(self):
  body=self.body();preview=sheets.service(self.mod,'balance_preview',body)
  result=sheets.service(self.mod,'balance_apply',{**body,'stages':preview['stages'],'plan_token':preview['plan_token']})
  self.assertNotEqual(self.mod.edb_path.read_bytes(),self.original)
  record=result['record'];self.assertEqual(record['manifest']['backed_up'],['export_descr_buildings.txt'])
  self.assertEqual(config.load_log()[0]['id'],record['id'])
  undo(record['id']);self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_replenish_only_profile_response_export_and_apply_preserve_other_bytes(self):
  loaded=sheets.service(self.mod,'load');body={**self.body(),'stages':['replenish']}
  preview=sheets.service(self.mod,'balance_preview',body)
  self.assertEqual(preview['profile']['city_multiplier'],.9)
  self.assertEqual(preview['profile']['cavalry_multiplier'],.8)
  self.assertEqual(preview['profile']['branch_policy'],'shortest')
  policies=preview['profile_rules']
  self.assertEqual(loaded['balance_profile_rules'],policies)
  self.assertEqual(policies['settlement_policy'],'per_level_header')
  self.assertEqual(policies['unspecified_city_multiplier'],1)
  self.assertEqual(policies['beast_replenish_tier'],'Beast')
  self.assertEqual(policies['beast_cavalry_policy'],'native_category')
  self.assertEqual(policies['malformed_beast_policy'],'report')
  self.assertEqual(policies['missing_endpoint_policy'],'use_other_endpoint')
  expected=self.original.replace(b'1   0.1  2',b'1   0.09  2').replace(b'"Guard" 1 0.1 2',b'"Guard" 1 0.2 2')
  exported=sheets.service(self.mod,'balance_export',body)
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported['text']))) as z:
   self.assertEqual(z.read('export_descr_buildings_new.txt'),expected)
   self.assertEqual(json.loads(z.read('profile_rules.json')),policies)
  applied=sheets.service(self.mod,'balance_apply',{**body,'plan_token':preview['plan_token']})
  self.assertEqual(self.mod.edb_path.read_bytes(),expected)
  repeated=sheets.service(self.mod,'balance_preview',body)
  self.assertEqual(repeated['changed_fields'],0);self.assertEqual(self.mod.edb_path.read_bytes(),expected)
  undo(applied['record']['id']);self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_external_edb_edit_refuses_stale_apply(self):
  preview=balance.preview(self.mod,self.project)
  self.mod.edb_path.write_bytes(self.original+b'; external\r\n')
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original+b'; external\r\n')
 def test_external_edu_edit_refuses_stale_apply_even_if_cached(self):
  preview=balance.preview(self.mod,self.project)
  self.mod.edu_path.write_bytes(EDU.replace('infantry','cavalry').encode())
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_changed_rules_or_stages_refuse_stale_apply(self):
  preview=balance.preview(self.mod,self.project)
  p=copy.deepcopy(self.project);p['rules']['replenish'][0]['Human_Earliest']='12'
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,p,None,preview['plan_token'])
  with self.assertRaises(sheets.SheetError):balance.apply_preview(self.mod,self.project,['pool'],preview['plan_token'])
 def test_failed_replace_leaves_original_and_no_temporary_file(self):
  preview=balance.preview(self.mod,self.project)
  with patch.object(buildings.os,'replace',side_effect=OSError('blocked')):
   with self.assertRaises(OSError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original);self.assertEqual(list(self.data.glob('*.tmp')),[])
 def test_failed_log_write_rolls_back_the_document(self):
  preview=balance.preview(self.mod,self.project)
  with patch.object(config,'append_log',side_effect=OSError('full disk')):
   with self.assertRaises(OSError):balance.apply_preview(self.mod,self.project,None,preview['plan_token'])
  self.assertEqual(self.mod.edb_path.read_bytes(),self.original)
 def test_lookup_stages_export_apply_undo_independently(self):
  for stage in ('experience','pool'):
   with self.subTest(stage=stage):
    body={**self.body(),'stages':[stage]};preview=sheets.service(self.mod,'balance_preview',body)
    if stage=='experience':
     expected=self.original.replace(b'2  0  requires',b'2  3  requires').replace(b'0.5 0 ;',b'0.5 3 ;').replace(b'2 0\r',b'2 3\r')
    else:expected=self.original.replace(b'0.1  2  0',b'0.1  4  0').replace(b'"Guard" 1 0.1 2 0',b'"Guard" 1 0.1 4 0')
    exported=sheets.service(self.mod,'balance_export',body)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported['text']))) as z:
     self.assertEqual(z.read('export_descr_buildings_new.txt'),expected)
     entries=json.loads(z.read('logs/'+stage+'_all.json'))
     self.assertEqual(entries[0]['explanation']['lookup_column'],'T1')
     self.assertEqual(entries[0]['explanation']['lookup_value'],'3' if stage=='experience' else '4')
    applied=sheets.service(self.mod,'balance_apply',{**body,'plan_token':preview['plan_token']})
    self.assertEqual(self.mod.edb_path.read_bytes(),expected)
    self.assertEqual(sheets.service(self.mod,'balance_preview',body)['changed_fields'],0)
    undo(applied['record']['id']);self.assertEqual(self.mod.edb_path.read_bytes(),self.original)

 def test_custom_lookup_keys_import_edit_and_reload_per_project(self):
  for stage in ('experience','pool'):
   previous=copy.deepcopy(sheets.load_project(self.mod)['rules'][stage])
   headers=['Unit Race','Category','BarracksTier','T0','T1','T2','T3','T4']
   body={**self.body(),'format':'csv',
    'text':','.join(headers)+'\nAurora,levy,T1,1,2,3,4,5\n',
    'plans':[{'sheet':'CSV','view':'rules:'+stage,'header_row':1,
     'mapping':{name:i for i,name in enumerate(headers)}}]}
   preview=sheets.service(self.mod,'interchange_preview',body)
   sheets.service(self.mod,'interchange_import',{**body,'preview_token':preview['preview_token']})
   p=sheets.load_project(self.mod);row=next(r for r in p['rules'][stage] if r['Unit Race']=='Aurora')
   self.assertEqual((row['Unit Race'],row['Category']),('Aurora','levy'))
   result=sheets.service(self.mod,'operate',{**self.body(),'view':'rules:'+stage,
    'mode':'selected','ids':[row['id']],'column':'T1','operation':'set','value':7})
   current=sheets.load_project(self.mod)['rules'][stage]
   self.assertEqual(next(r for r in current if r['id']==row['id'])['T1'],7)
   self.assertEqual([r for r in current if r['id']!=row['id']],previous)
   self.assertEqual(sheets.empty_project()['rules'][stage],[])

 def test_invalid_profile_import_is_transactional(self):
  body=self.body();before=sheets.load_project(self.mod);bad=copy.deepcopy(before);bad['balance_profile']={'city_multiplier':'nan'}
  with self.assertRaises(sheets.SheetError):sheets.service(self.mod,'save',{**body,'project':bad})
  self.assertEqual(sheets.load_project(self.mod),before)
 def test_recruitment_queries_retain_condition_and_classification(self):
  d=sheets.service(self.mod,'query',{'view':'recruitment','where':{'all':[{'column':'building','op':'eq','value':'barracks'},{'column':'Unit Race','op':'eq','value':'Human'},{'column':'maximum','op':'lt','value':1}]}})
  self.assertEqual(d['table']['total'],1);self.assertEqual(d['table']['rows'][0]['unit'],'Horse')

if __name__=='__main__':unittest.main()
