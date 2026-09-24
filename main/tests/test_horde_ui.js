// node main/tests/test_horde_ui.js
// Phase 72: the Horde start tab's form - what it starts from, what the pin
// writes, and the body it posts. The rules are the server's (test_hordestart.py).
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const ctx={state:{},document:{getElementById:()=>null},window:{},
  esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
  enc:encodeURIComponent,setTimeout:()=>0,clearTimeout:()=>{},toast:()=>{},activity:()=>{},
  cjPaint:()=>{},cmapPaint:()=>{},cmapCampQ:()=>'',CJ_DEBOUNCE:450};
vm.createContext(ctx);
for(const file of ['mappin.js','hordestart.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/js',file),'utf8'),ctx);

const keys=['horde_min_units','horde_max_units','horde_max_units_reduction_every_horde',
  'horde_unit_per_settlement_population','horde_min_named_characters',
  'horde_max_percent_army_stack','horde_disband_percent_on_settlement_capture'];
const donor={faction:'mongols',units:['Mongol Horse Archers'],
  keys:Object.fromEntries(keys.map((k,i)=>[k,String(10+i)]))};
const view={campaign:'imperial_campaign',modes:['map','emerge'],keys,
  defaults:Object.fromEntries(keys.map(k=>[k,1])),stack_limit:20,default_age:30,size:[40,20],
  factions:[{name:'england',settlements:1,characters:1,dormant:false},
            {name:'khazars',settlements:0,characters:0,dormant:false}],
  faction:{name:'khazars',settlements:[],characters:[],leader:'',flags:[],in_sm:true,
    horde:null,donors:[donor],owned:['Khazar Bodyguard','Khazar Horse Archers','Peasants'],
    bodyguards:['Khazar Bodyguard'],units:['Khazar Bodyguard','Khazar Horse Archers','Peasants'],
    names:['Bulan','Obadiah'],have_pool:true,event:null,events_file:true,
    text:{title:'',body:'',have_file:true},eventspic:['ui/a/eventspic','ui/b/eventspic'],
    pictures:['first_windmill','mongols'],has_picture:false}};

ctx.state.cmap={mod:'Toy',campaign:'',man:{width:40,height:20}};
ctx.state.hs=Object.assign(ctx.hsNew('Toy',''),{d:view,faction:'khazars'});
ctx.hsReset();
const w=ctx.state.hs.w;
assert.equal(w.mode,'map','a faction with no event and no flag starts on the map');
assert.equal(w.donor,'mongols','the mod\'s own horde is where the numbers come from');
assert.equal(w.keys.horde_max_units,'11');
assert.deepEqual(Array.from(w.units),['Khazar Horse Archers','Peasants'],'its own troops, not the donor\'s, and no bodyguard');
assert.deepEqual(JSON.parse(JSON.stringify(w.generals)),
  [{name:'Bulan',age:30,x:'',y:'',army:['Khazar Bodyguard','Khazar Horse Archers','Peasants']}],
  'one general, a pool name, the bodyguard first');

let html=ctx.hsHtml();
assert(html.includes("mongols's numbers"),'the donor is a button');
assert(html.includes("hsPinned") && html.includes('Bulan'),'a pin beside the general');
assert(html.includes('the first one leads the faction'));

ctx.hsPinned('gen',0,[5,7]);
ctx.hsAddGeneral();
assert.equal(ctx.state.hs.w.generals[1].name,'Obadiah','a second general takes the next free name');
let body=ctx.hsBody();
assert.equal(body.mode,'map');
assert.deepEqual([body.generals[0].x,body.generals[0].y,body.generals[0].age],[5,7,30],'numbers go as numbers');
assert.equal(body.generals[1].x,'','an empty box goes as empty, for the server to refuse');
assert(!('dates' in body),'a map start posts no event');

ctx.hsKey('horde_min_units','3');
assert.equal(ctx.state.hs.w.donor,'','editing a number is no longer the donor\'s');
ctx.hsDonor('mongols');
assert.equal(ctx.state.hs.w.keys.horde_min_units,'10','and the donor button puts its numbers back');

ctx.hsSet('mode','emerge');
html=ctx.hsHtml();
assert(html.includes('a copy of mongols.tga') && html.includes('selected'),'the picture to copy is offered, mongols by default');
assert(html.includes('{KHAZARS_TITLE}'),'the text keys are named');
ctx.hsPinned('pos',-1,[4,6]);
ctx.hsPinned('pos',-1,[9,3]);
ctx.hsPinned('pos',0,[2,2]);
ctx.hsItem(['dates',0],'100 110');
body=ctx.hsBody();
assert.deepEqual(JSON.parse(JSON.stringify(body.positions)),[[2,2],[9,3]],'the pin adds a position, or moves one');
assert.deepEqual(Array.from(body.dates),['100 110']);
assert.equal(body.picture_from,'mongols');
assert(!('generals' in body),'an emergence posts no generals');

ctx.state.hs.w.positions.push([50,1]);
assert(ctx.hsHtml().includes('off a 40×20 map'),'a position off the map is marked before the server is asked');

// a faction that holds a settlement is told why, and offered nothing to write
ctx.state.hs.d=Object.assign({},view,{faction:Object.assign({},view.faction,{name:'england',settlements:['London']})});
html=ctx.hsHtml();
assert(html.includes('holds London') && !html.includes('Write the horde start'));

console.log('PASS: horde start tab - its starting values, the donor, the pin, both bodies, the refusals it draws');
