// Armory Studio's Pre-render lighting panel (web/js/armlit.js).
//   node tests/test_armory_lit_ui.js
// The light's direction as the viewport draws it, which objects show the live
// light and which their baked texture, the bake's request and what it leaves
// on each object, and taking it off again.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const calls=[], toasts=[];
let answer={baked:[],skipped:[]};
const project={objects:[{id:1,name:'helm',src:[]},{id:2,name:'cloak',src:[],sheet:'C:/own.png'},{id:3,name:'belt',src:[]}]};
const c={ARM:{sel:new Set([1,2]),sheetCache:new Map(),sheetAllowed:new Set(),sheetStamp:{}},state:{settings:{}},
  armProj:()=>project,armObj:id=>project.objects.find(o=>o.id===id),
  armSelected:()=>project.objects.filter(o=>c.ARM.sel.has(o.id)),armVisibleObjects:()=>project.objects,
  armFrame(){c.frames++;},armRepaint(){c.repaints++;},armPaintObjects(){c.paints++;},frames:0,repaints:0,paints:0,
  tt:(k,p)=>k+(p?JSON.stringify(p):''),ttN:(k,n)=>k+n,esc:String,errText:String,toast:t=>toasts.push(t),
  api:{post:async(url,body)=>{calls.push({url,body:JSON.parse(JSON.stringify(body))});return answer;}}};
vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js/armlit.js'),'utf8'),c);
const near=(a,b)=>a.every((x,i)=>Math.abs(x-b[i])<1e-6);

(async()=>{
  // the settings: the server's defaults, and what the user last chose
  assert.equal(c.armLitOpts().shadows,0.5);
  assert.equal(c.armLitOpts().key,true);

  // the light towards the page: y up, and x mirrored as the viewport mirrors the model
  c.armLitSet('direction',0,true);c.armLitSet('height',90,true);
  assert.ok(near(c.armLitDir(),[0,1,0]));
  c.armLitSet('direction',90,true);c.armLitSet('height',0,true);
  assert.ok(near(c.armLitDir(),[-1,0,0]));
  c.armLitSet('direction',0,true);
  assert.ok(near(c.armLitDir(),[0,0,1]));

  // closed: the viewport's own light on everything
  assert.equal(c.armLitMode(project.objects[0]),0);
  c.armLitToggle();
  assert.equal(c.paints,1);
  // open: the selected objects show the live light, the others stay as they were
  assert.equal(c.armLitMode(project.objects[0]),1);
  assert.equal(c.armLitMode(project.objects[2]),0);
  const html=c.armLitHtml();
  for(const k of ['ambient','direction','height','softness','strength','shadows','key','flip_green'])
    assert.match(html,new RegExp("armLitSet\\('"+k+"'"),k);
  assert.match(html,/armLitRun\(\)/);

  // a slider being dragged redraws the viewport and saves nothing yet
  const posts=calls.length,frames=c.frames;
  c.armLitSet('ambient',1.2,true);
  assert.equal(calls.length,posts);
  assert.ok(c.frames>frames);
  c.armLitSet('ambient',1.2);
  assert.equal(calls.at(-1).url,'/api/settings');
  assert.equal(calls.at(-1).body.armory_lit.ambient,1.2);

  // the bake: the selected objects and the settings go to the server
  answer={baked:[{source:'C:/helm_d.png',path:'C:/lit/helm_d_lit_1.png',objects:[1]},
                 {source:'C:/own.png',path:'C:/lit/own_lit_2.png',objects:[2]}],skipped:[]};
  await c.armLitRun();
  const sent=calls.at(-1);
  assert.equal(sent.url,'/api/armory/lit');
  assert.deepEqual(sent.body.ids,[1,2]);
  assert.equal(sent.body.settings.ambient,1.2);
  // each object wears its lit texture and remembers what it wore before
  assert.equal(project.objects[0].sheet,'C:/lit/helm_d_lit_1.png');
  assert.equal(project.objects[0].lit.src,null);
  assert.equal(project.objects[1].sheet,'C:/lit/own_lit_2.png');
  assert.equal(project.objects[1].lit.src,'C:/own.png');
  assert.ok(c.ARM.sheetAllowed.has('C:/lit/own_lit_2.png'));
  assert.ok(c.repaints>0);
  // baked: the texture is shown as it is, with no light over it
  assert.equal(c.armLitMode(project.objects[0]),2);
  assert.equal(c.armLitSheetOf(project.objects[1]),'C:/lit/own_lit_2.png');
  // a slider moved after that: the live light again, over the source texture
  c.armLitSet('strength',0.9,true);
  assert.equal(c.armLitMode(project.objects[1]),1);
  assert.equal(c.armLitSheetOf(project.objects[1]),'C:/own.png');
  assert.equal(c.armLitSheetOf(project.objects[0]),null);

  // a second bake keeps the first source, not the lit texture it now wears
  await c.armLitRun();
  assert.equal(project.objects[1].lit.src,'C:/own.png');

  // what could not be baked is said
  answer={baked:[],skipped:[{id:1,why:'two_sheets'}]};
  const said=toasts.length;
  await c.armLitRun();
  assert.ok(toasts.length>said);
  assert.match(toasts.at(-1),/helm/);

  // closed: a baked object is drawn with its lit texture, under the viewport's light
  c.armLitToggle();
  assert.equal(c.armLitMode(project.objects[1]),0);
  assert.equal(c.armLitSheetOf(project.objects[1]),'C:/lit/own_lit_2.png');

  // taking it off: each object wears what it wore before
  c.armLitRemove([1,2]);
  assert.equal(project.objects[0].sheet,null);
  assert.equal(project.objects[0].lit,undefined);
  assert.equal(project.objects[1].sheet,'C:/own.png');
  console.log('armory lit ui: ok');
})().catch(e=>{console.error(e);process.exit(1);});
