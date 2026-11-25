// Armory Studio's live look at the Cycles bake (web/js/armcycles.js) and when
// armlit.js draws an object with it.
//   node tests/test_armory_cycles_ui.js
// The bar's toggle and that it is remembered, each loose part numbered as the
// bake moves parts apart, a light map's basis, and which objects get the look.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const calls=[];
const project={objects:[{id:1,name:'helm',src:[]},{id:2,name:'cloak',src:[],lit:{src:null}},{id:3,name:'belt',src:[]}]};
const c={ARM:{sel:new Set(),sheetCache:new Map(),sheetAllowed:new Set(),sheetStamp:{}},state:{settings:{}},
  armProj:()=>project,armSelected:()=>[],armVisibleObjects:()=>project.objects,
  armFrame(){},armPaintObjects(){},tt:k=>k,ttN:k=>k,esc:String,errText:String,toast(){},
  api:{post:async(url,body)=>{calls.push({url,body});return {};}},setTimeout:()=>1,clearTimeout(){}};
vm.createContext(c);
for(const f of ['armlit.js','armcycles.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js/'+f),'utf8'),c);
// a top-level const of the page's scripts is read in their scope
for(const n of ['armCyOn','armCyBasis']) c[n]=vm.runInContext(n,c);

// on unless the user turned it off, and remembered
assert.equal(c.armCyOn(),true);
c.armCyToggle(false);
assert.equal(c.armCyOn(),false);
assert.equal(JSON.stringify(calls.at(-1)),JSON.stringify({url:'/api/settings',body:{armory_bake_look:false}}));
assert.match(c.armCyBarHtml(),/armCyToggle\(this\.checked\)/);
assert.doesNotMatch(c.armCyBarHtml(),/checked onchange/);
c.armCyToggle(true);

// two triangles sharing an edge are one part; a third apart is another
const parts=c.armCyPartsOf(new Uint16Array([0,1,2, 1,2,3, 4,5,6]),7);
assert.equal(parts[0],parts[3]);
assert.notEqual(parts[0],parts[4]);
assert.equal(parts[4],parts[6]);
assert.ok(parts.every(p=>p>0&&p<=1));

// a light map's basis: square to the light and to each other
for(const L of [[0,1,0],[0.3,0.2,0.93].map(v=>v/Math.hypot(0.3,0.2,0.93)),[1,0,0]]){
  const [X,Y]=c.armCyBasis(L);
  const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  assert.ok(Math.abs(dot(X,L))<1e-9&&Math.abs(dot(Y,L))<1e-9&&Math.abs(dot(X,Y))<1e-9);
  assert.ok(Math.abs(dot(X,X)-1)<1e-9);
}

// which objects get the look: PBR maps, not baked; the Pre-render light until it is ready
c.ARM.litMaps={sig:'x',byId:{1:{colour:'C:/h_d.png',spec:'C:/h_s.png'},2:{colour:'C:/c_d.png',normal:'C:/c_n.png'}},busy:false};
assert.equal(c.armLitMode(project.objects[0]),1);
c.ARM.gl={}; c.ARM.cy={ready:true,gl:c.ARM.gl,look:{}};
assert.equal(c.armLitMode(project.objects[0]),3);
assert.equal(c.armLitSheetOf(project.objects[0]),'C:/h_d.png');
// baked: its own texture; no maps: the viewport's light
assert.equal(c.armLitMode(project.objects[1]),0);
assert.equal(c.armLitMode(project.objects[2]),0);
// the bar's toggle off: the viewport's own light while modelling
c.armCyToggle(false);
assert.equal(c.armLitMode(project.objects[0]),0);
// the Pre-render panel open draws its own bake's light on what it covers, toggle or not
c.armLitToggle();
assert.equal(c.armLitMode(project.objects[0]),1);
console.log('armory cycles ui: ok');
