// node main/tests/test_map_creation.js — no game files are written.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ctx = {state:{},window:{},document:{getElementById:()=>null},toast(){},
  cpinCancel(){},cpaintToggle(){ctx.state.cpaint.on=!ctx.state.cpaint.on;},
  cmapSub:(tab,sub)=>{ctx.panel=[tab,sub];},cmapPaint(){},cpaintPaint(){},
  cpaintApply:changed=>{ctx.applied=changed;},
  cpinArm:(what,fn,args)=>{ctx.pin={what,fn,args};},
  cpaintPost:async(action,body)=>{ctx.post={action,body};return {changed:{regions:{}}};},
};
vm.createContext(ctx);
for(const file of ['campmark.js','campcreate.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js',file),'utf8'),ctx);
(async()=>{
  ctx.state.cmap={sel:{name:'Alpha'},man:{campaign_map:{},regions:[]},campaign:'campaign'};
  ctx.state.cpaint={on:true,st:{}};
  ctx.cmapCreateMarker('port');
  assert.equal(ctx.state.cpaint.on,false,'placement suspends painting');
  assert.equal(ctx.pin.fn,'cmapCreateMarkerAt');
  assert.equal(ctx.pin.args[1],'Alpha');
  await ctx.cmapCreateMarkerAt('port','Alpha',[3,4],[3,5]);
  assert.equal(ctx.post.action,'paint');
  assert.deepEqual(Array.from(ctx.post.body.points[0]),[3,5],'marker uses image coordinates');
  assert.equal(ctx.post.body.region,'Alpha');
  assert(ctx.applied,'successful marker updates the canvas');
  ctx.pin=null;
  ctx.state.cmap.man.campaign_map.paints=false;
  ctx.cmapCreateMarker('port');
  assert.equal(ctx.pin,null,'private campaign map cannot arm a base-map edit');

  ctx.cxOpen=async faction=>{ctx.state.cx={faction,d:{characters:[]}};};
  ctx.cxAdd=()=>{ctx.state.cx.w={};};ctx.cxPaint=ctx.cxPlanSoon=()=>{};
  await ctx.cmapCreateCharacterAt('england','princess',[5,7]);
  assert.equal(ctx.state.cx.w.x,5);assert.equal(ctx.state.cx.w.y,7);
  assert.equal(ctx.state.cx.w.gender,'female');
  assert.equal(ctx.state.cx.w.type,'princess');
  assert.deepEqual(ctx.panel,['place','chars']);
  // A late response cannot open an editor for a campaign the user has left.
  ctx.panel=null;
  ctx.cxOpen=async()=>{ctx.state.cmap.campaign='other';};
  await ctx.cmapCreateCharacterAt('england','general',[5,7]);
  assert.equal(ctx.panel,null);

  const r={name:'Alpha',key:0xff0000,declared:true,port:[0,0]};
  const data=new Uint8ClampedArray(3*3*4);
  for(let i=0;i<9;i++)data.set([255,0,0,255],i*4);
  data.set([255,255,255,255],4*4);
  ctx.state.cmap={man:{width:3,height:3,regions:[r],markers:{settlement:[0,0,0],port:[255,255,255]}},layers:{regions:{}}};
  ctx.cmapRawOf=()=>({w:3,h:3,data});
  ctx.state.cmk=ctx.cmkNew('test');ctx.state.cmk.d={items:[]};
  ctx.cmkPaint=()=>{};
  ctx.cmkSyncMapMarkers({Alpha:{settlement:null,port:[1,1]}});
  assert.deepEqual(Array.from(r.port),[1,1],'port icon follows edited pixels');
  assert.equal(ctx.state.cmk.groups[0].items[0].kind,'port');
  data.set([255,0,0,255],4*4);data.set([255,255,255,255],5*4);
  ctx.cmkSyncMapMarkers({Alpha:{settlement:null,port:[2,1]}});
  assert.deepEqual(Array.from(r.port),[2,1],'port icon follows undo/redo pixel changes');
  assert.equal(ctx.state.cmk.groups.length,1,'old port icon is removed');
  console.log('PASS: placement coordinates, map restrictions, character creation, stale responses and port icons');
})().catch(e=>{console.error(e);process.exitCode=1;});
