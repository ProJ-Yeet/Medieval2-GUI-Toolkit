// node main/tests/test_map_view_refresh.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ctx = {state:{src:'Test'},document:{addEventListener(){}},window:{},
  main:{innerHTML:''},esc:String,enc:encodeURIComponent,stale:()=>false,
  clearTimeout(){},confirm:()=>true,toast(){},activity(){}};
vm.createContext(ctx);
for(const f of ['campmap.js','stratchar.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js',f),'utf8'),ctx);
(async()=>{
  const camera = {zoom:12,ox:-412,oy:-731,fitted:true};
  let manifest = {width:510,height:487};
  ctx.state.cmap={mod:'Test',campaign:'custom/campaign',man:manifest,view:{...camera}};
  let url, renders=0;
  ctx.api={get:async value=>{url=value;return manifest;}};
  ctx.cmapNew=(mod,man)=>({mod,man,view:{zoom:1,ox:0,oy:0,fitted:false},terrain:{on:false}});
  ctx.renderCampmap=()=>{renders++;};ctx.cmapLoadLayers=()=>{};
  await ctx.loadCampmap();
  assert.deepEqual({...ctx.state.cmap.view},camera,'reload preserves zoom and pan');
  assert.equal(ctx.state.cmap.campaign,'custom/campaign');
  assert.match(url,/campaign=custom%2Fcampaign/,'reload fetches the active campaign');
  manifest={width:100,height:100};
  await ctx.loadCampmap();
  assert.equal(ctx.state.cmap.view.fitted,false,'a resized map receives a fresh fit');
  ctx.state.src='Other';
  await ctx.loadCampmap();
  assert.equal(ctx.state.cmap.campaign,'','switching mods does not carry a campaign');

  const map=ctx.state.cmap;
  map.view={...camera};
  ctx.state.cx={mod:'Other',faction:'england',open:true,tab:'people',d:{},w:{name:'Arthur'}};
  ctx.state.cmk={d:{}};
  ctx.cxBody=()=>({character:'Arthur',edits:{name:'Arthur'}});
  ctx.cxPaint=()=>{};
  ctx.api.post=async url=>url.endsWith('_plan')?{plan:{changes:['Move Arthur']}}:{name:'Arthur'};
  ctx.cxOpen=async()=>{ctx.state.cx={d:{characters:[{name:'Arthur'}]}};};
  let picked=-1,icons=0;
  ctx.cxPick=i=>{picked=i;};ctx.cmkLoad=async()=>{icons++;};
  const before=renders;
  await ctx.cxSave('edit');
  assert.equal(ctx.state.cmap,map,'character save retains the map and canvas state');
  assert.deepEqual({...map.view},camera);
  assert.equal(renders,before,'character save does not rebuild the map UI');
  assert.equal(picked,0,'saved character stays selected');
  assert.equal(icons,1,'character icons are refreshed');
  console.log('PASS: save/reload camera preservation, campaign identity and local character refresh');
})().catch(e=>{console.error(e);process.exitCode=1;});
