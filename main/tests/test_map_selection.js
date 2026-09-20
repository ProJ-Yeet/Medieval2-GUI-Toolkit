// Run with node main/tests/test_map_selection.js; no game files required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = {
  state: {}, window: {}, esc: String,
  document: {addEventListener(){}, createElement(){
    const canvas = {width:0, height:0};
    canvas.getContext = () => ({
      createImageData:(w,h) => ({data:new Uint8ClampedArray(w*h*4)}),
      putImageData:im => {canvas.pixels = im.data;},
    });
    return canvas;
  }},
  cpaintTrail:()=>null,
};
vm.createContext(context);
for(const file of ['campmap.js','mapfind.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js',file),'utf8'),context);
const region = {name:'Alpha', key:0xff0000, anchor:[0,0], declared:true};
const raw = {w:2,h:1,data:new Uint8ClampedArray([255,0,0,255,0,0,255,255])};
const c = context.state.cmap = {
  man:{width:2,height:1,regions:[region]}, sel:region,
  layers:{regions:{raw}}, view:{zoom:1,ox:0,oy:0},
  outline:null, outlineKey:-1,
};
const draw = {save(){},restore(){},drawImage(){},strokeRect(){}};
context.cmapOverlay(draw,0,0,2,1);
assert.equal(c.outline.pixels[3],255,'selected boundary is visible');
const first = c.outline;
context.cmapOverlay(draw,0,0,2,1);
assert.equal(c.outline,first,'hover/pan reuse the cached outline');
raw.data.set([255,0,0,255],4);
c.outline = null; c.outlineKey = -1;
context.cmapOverlay(draw,0,0,2,1);
assert.notEqual(c.outline,first,'invalidated selection is rebuilt on redraw');
assert.equal(c.outline.pixels[7],255,'outline follows edited region pixels');
c.sel = null;
context.cmapOverlay(draw,0,0,2,1);
assert.equal(c.outline,null,'clearing selection removes its outline');
context.state.cfd = {q:'',hits:[],of:0};
assert.equal(context.cfdBrowseHits().length,1,'empty search browses regions');
assert.match(context.cfdResHtml(),/<button class="cfdrow"/,'region rows are keyboard buttons');
let selected = false, destination;
context.cpaintSelectRegion = () => {selected = true;};
context.cmapGoTile = (tile,zoom,name) => {destination = name;};
context.activity = () => {};
context.cfdGo(0);
assert(selected,'choosing a region enters selection mode');
assert.equal(destination,'Alpha','browse selection navigates to the region');
console.log('PASS: outline rebuild, cache, clear and region browsing/selection');

vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js/campaint.js'),'utf8'),context);
context.cpaintPaint = () => {};
const p = context.state.cpaint = context.cpaintNew('test');
p.on = true; p.tool = 'water'; p.sea = true; p.marker = 'port';
context.cpaintPickRegion(region);
assert.equal(p.region,'Alpha');
assert.equal(p.target,'regions');
assert.equal(p.tool,'brush');
assert.equal(p.sea,false);
assert.equal(p.marker,'');
assert.equal(p.on,true,'sampling keeps painting armed');
context.cpaintPickRegion(null);
assert.equal(p.region,'Alpha','sea or empty space does not erase the paint target');
p.on = false;
context.cpaintPickRegion(region);
assert.equal(p.on,false,'sampling does not unexpectedly arm painting');

const handlers = {};
const cv = {addEventListener:(name,fn)=>{handlers[name]=fn;},
  setPointerCapture(){},releasePointerCapture(){},getBoundingClientRect:()=>({left:0,top:0})};
context.document.getElementById = () => null;
context.cpaintArmed = () => true;
context.cmapPick = () => {c.sel = region;};
context.cmapEventTile = () => [0,0];
context.cmapTipPaint = context.cmapPaint = context.cmapHover = () => {};
context.cmapPointers(cv);
const event = {button:2,clientX:0,clientY:0,pointerId:1};
p.region = 'Before';
handlers.pointerdown(event);handlers.pointerup(event);
assert.equal(p.region,'Alpha','right click selects the painting region');
p.region = 'Before';
handlers.pointerdown(event);
handlers.pointermove({...event,clientX:20});
handlers.pointerup({...event,clientX:20});
assert.equal(p.region,'Before','right drag pans without sampling a region');
console.log('PASS: right-click paint sampling and right-drag pan');
