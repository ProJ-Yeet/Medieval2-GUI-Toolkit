const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const c = {state:{}, ARM:{}, armSave(){}, window:{addEventListener(){},removeEventListener(){}}, document:{getElementById:()=>null}, setTimeout:()=>0, clearTimeout(){}};
vm.createContext(c);
vm.runInContext(fs.readFileSync('main/web/js/armexport.js','utf8'), c);
c.armProj=()=>({collections:[]}); c.armExpDrawSheets=()=>{}; c.armExpPaintCv=()=>{}; c.armExportPaint=()=>{}; c.armExpFetchSel=()=>{};
const a={id:'a',objs:[1],x:0,y:0,w:100,h:200,own:1,placed:true};
const b={id:'b',objs:[2],x:200,y:0,w:100,h:100,own:1,placed:true};
const e=c.armExp(); e.live=false; e.plan={sheets:{main:{size:512,blocks:[a,b]},attach:{size:0,blocks:[]}}}; e.sel='a';
c.armExpBlockScale(50); e.sel='b'; c.armExpBlockScale(75);
assert.equal(c.armExpDisplayBlock(a).w,50,'first scale survives selecting/scaling another island');
assert.equal(c.armExpDisplayBlock(b).w,75);
const ev=key=>({key,stopPropagation(){},preventDefault(){}});
c.armExpKey(ev('s')); c.armExpKey(ev('0')); c.armExpKey(ev('.')); c.armExpKey(ev('5'));
assert.equal(e.settings.block_scale.b,0.375,'S 0.5 halves the current scale');
c.armExpKey(ev('Escape')); assert.equal(e.settings.block_scale.b,0.75,'Escape restores scale');
c.armExpKey(ev('s')); c.armExpKey(ev('2')); c.armExpKey(ev('Enter'));
assert.equal(e.settings.block_scale.b,1.5,'numeric scale also enlarges beyond original size');
c.armExpPick('main',{currentTarget:{getBoundingClientRect:()=>({left:0,top:0,width:512,height:512})},clientX:90,clientY:150});
assert.equal(e.sel,null,'clicking outside the scaled shape deselects');
c.armExpPick('main',{currentTarget:{getBoundingClientRect:()=>({left:0,top:0,width:512,height:512})},clientX:20,clientY:50});
assert.equal(e.sel,'a'); assert.equal(c.armExpDisplayBlock(a).w,50);
vm.runInContext(fs.readFileSync('main/web/js/armuv.js','utf8'), c);
c.armUvGeom=()=>({W:100,H:100,iw:100,ih:100,sh:{span:1}}); c.armUvPush=()=>{}; c.armUvPaint=()=>{};
c.ARM.uvEd={pts:[{u:0.1,w:0.1},{u:0.9,w:0.9}],snap:true,sel:new Set([0,1])};
c.ARM.uvEd.xf={op:'s',X:0,Y:0,X0:0,Y0:0,CX:50,CY:50,cu:0.5,cv:0.5,start:c.armUvSnapshot()};
c.armUvKey(ev('0')); c.armUvKey(ev('.')); c.armUvKey(ev('5'));
assert.ok(Math.abs(c.ARM.uvEd.pts[0].u-0.3)<1e-10,'UV editor accepts exact typed scaling');

// Packing history keeps a continuous slider movement as one edit.
e.sel='a'; e.history={past:[],future:[],start:null};
c.armExpBlockScale(60,true); c.armExpBlockScale(70,true); c.armExpBlockScale(70);
assert.equal(e.history.past.length,1);
c.armExpKey({...ev('z'),ctrlKey:true}); assert.equal(e.settings.block_scale.a,0.5);
c.armExpKey({...ev('y'),ctrlKey:true}); assert.equal(e.settings.block_scale.a,0.7);
// S follows the mouse without a button held, and Enter removes its listeners.
const listeners=new Map();
c.window.addEventListener=(name,fn)=>listeners.set(name,fn);
c.window.removeEventListener=(name,fn)=>{if(listeners.get(name)===fn)listeners.delete(name);};
const cv={width:512,height:512,getBoundingClientRect:()=>({left:0,top:0,width:512,height:512})};
c.document.getElementById=id=>id==='armExpCv_main'?cv:null;
e.pointer={sh:'main',x:85,y:70}; // selected box is 70 x 140: pointer radius 50
c.armExpKey(ev('s')); listeners.get('mousemove')({clientX:135,clientY:70});
assert.ok(Math.abs(e.settings.block_scale.a-1.4)<1e-10,'mouse distance doubles scale after S');
c.armExpKey(ev('Enter')); assert.equal(listeners.has('mousemove'),false);
let redone=null;c.armUndo=redo=>{redone=redo;};
c.armUvKey({...ev('z'),ctrlKey:true}); assert.equal(redone,false);
c.armUvKey({...ev('y'),ctrlKey:true}); assert.equal(redone,true);
// Session snapshots include output location and installation choices, never transient plans.
vm.runInContext(fs.readFileSync('main/web/js/armsess.js','utf8'),c);
let project={collections:[],objects:[],assets:[]};c.armProj=()=>project;
e.folder='D:/exports';e.stem='Black_Num_Inf';e.mod={target:'Example',folder:'unit_models/test',unit:'Guard',data:{huge:true},plan:{transient:true}};
c.armExtrasInto(project);
assert.equal(project.extra.exportOutput.folder,'D:/exports');
assert.equal(project.extra.exportOutput.mod.plan,undefined);
c.armExtrasFrom(project);
assert.equal(c.armExp().folder,'D:/exports');assert.equal(c.armExpMod().folder,'unit_models/test');
console.log('Armory UV gestures, live slider, undo/redo and session persistence passed');

(async()=>{
  c.enc=encodeURIComponent;c.errText=String;c.tt=x=>x;c.esc=String;
  let installLoads=0;
  c.armExpModLoad=()=>{installLoads++;};
  c.api={get:async url=>url.startsWith('/api/unit_models') ? {models:[{name:'guard',folders:['unit_models/guard','unit_models/shared']}]} : {found:true,stem:'older_name',folder:'D:/exports',files:['older_name.mesh'],vertices:3,triangles:1,groups:1}};
  const restored=c.armExp();restored.step='check';restored.check=null;
  await c.armExportStep('mod');
  assert.equal(restored.step,'mod','existing export unlocks step 4 independently of a fresh bake or current checks');
  assert.equal(installLoads,1);assert.equal(restored.stem,'older_name');
  const storage=new Map();c.localStorage={getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)};
  const m=c.armExpMod();m.choice='add';m.unit='Guard';m.target='Example';m.folder='unit_models/recent';
  c.armExpRememberFolder();await c.armExpUnitFolders();
  const choices=c.armExpFolderChoices();
  assert.ok(choices.includes('unit_models/guard') && choices.includes('unit_models/shared') && choices.includes('unit_models/recent'));
  m.target='Different';assert.equal(c.armExpRecentFolders().length,0,'recent paths stay scoped to their mod');
  console.log('Existing export reuse and unit/recent folder choices passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
