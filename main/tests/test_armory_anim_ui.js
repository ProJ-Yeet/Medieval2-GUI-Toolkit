const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const calls=[];
let project={assets:[],anim:{mod:'fixture',skel:'human'}};
const c={ARM:{},state:{},armProj:()=>project,armFrame(){},armSave(){},
  document:{getElementById:()=>null},performance:{now:()=>0},
  v3aBind:d=>d,v3aTravel:()=>[0,0],v3aCarried:()=>false,
  tt:x=>x,esc:String,errText:String,confirm:()=>true,
  api:{post:async(url,body)=>{calls.push({url,body});return url.endsWith('save_plan') ? {plan:{ok:true,target:'animations/scaled.cas',notes:[]}} : {times:[0,1],bones:[]};}}};
vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js/armanim.js'),'utf8'),c);
c.armAnimPaint=()=>{};
const a=c.armAnim();
a.data={times:[0,1],bones:[]};a.orig=a.data;
a.source={mod:'fixture',rel:'animations/walk.cas',skeleton:'human',slot:2};
a.scale=[1,1,1];a.saveAs='animations/scaled.cas';a.saveTarget='loose';
assert.equal(JSON.stringify(c.armAnimScaleEdits()),'{}');
(async()=>{
  await c.armAnimScaleSet(-1,2);
  assert.equal(calls.at(-1).url,'/api/model/anim/preview');
  assert.deepEqual(JSON.parse(JSON.stringify(calls.at(-1).body.edits)),{scale:[2,2,2]});
  await c.armAnimScaleSet(1,3);
  assert.equal(JSON.stringify(c.armAnimScaleEdits()),'{"scale":[2,3,2]}');
  assert.match(c.armAnimScaleHtml(),/armAnimScaleSet\(-1/);
  assert.match(c.armAnimScaleHtml(),/armAnimScaleSet\(2/);
  await c.armAnimScaleSave();
  assert.deepEqual(calls.slice(-2).map(c=>c.url),['/api/model/anim/save_plan','/api/model/anim/save_apply']);
  assert.equal(calls.at(-1).body.save_as,'animations/scaled.cas');
  a.saveTarget='pack';a.packName='walk_scaled';
  await c.armAnimScaleSave();
  assert.equal(calls.at(-1).body.target,'pack');
  assert.equal(calls.at(-1).body.name,'walk_scaled');
  await c.armAnimScaleSet(-1,1);
  const count=calls.length;
  await c.armAnimScaleSave();assert.equal(calls.length,count,'scale 1 writes nothing');
  await c.armAnimScaleSet(0,0); assert.equal(calls.length,count,'invalid scale never previews or writes');
  let resolvePreview;
  c.api.post=()=>new Promise(resolve=>{resolvePreview=resolve;});
  const preview=c.armAnimScaleSet(-1,2);
  c.armAnimRest();
  resolvePreview({times:[0,1],bones:[]});await preview;
  assert.equal(a.data,null,'a late preview cannot restore an action after Rest');
  assert.equal(a.source,null,'Rest removes the editable source');
  console.log('Armory animation scale preview and save passed');
})().catch(err=>{console.error(err);process.exitCode=1;});
