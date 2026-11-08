// Browser contracts for the independently implemented campaign panels.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const en = JSON.parse(fs.readFileSync(path.join(root, 'web/i18n/en.json'), 'utf8'));
const read = file => fs.readFileSync(path.join(root, 'web/js', file), 'utf8');
const esc = value => String(value == null ? '' : value).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let assertions = 0;
function check(value, label){ assert(value, label); assertions++; }
function context(){
  const calls = [], elements = {};
  const ctx = vm.createContext({console, Uint8Array, Uint8ClampedArray, Map, Set,
    state:{src:'Test',mode:'scripts',mods:[]}, main:{innerHTML:''}, esc, docPoints:() => '',
    q1:v => v.replace(/\\/g,'\\\\').replace(/'/g,"\\'"), enc:encodeURIComponent,
    errText:e => e.message || String(e), toast:text => calls.push(['toast',text]), confirm:() => false,
    document:{getElementById:id => elements[id] || null, querySelector:() => null, addEventListener:() => {}},
    navigator:{clipboard:{writeText:async text => calls.push(['clipboard',text])}},
    window:{open:(...args) => calls.push(['open',...args]),addEventListener:() => {}},
    tt:(key,params={}) => {
      assert(Object.hasOwn(en,key), 'missing translation: ' + key);
      assert.strictEqual(typeof en[key], 'string', 'plural must use ttN: ' + key);
      return en[key].replace(/\{(\w+)\}/g,(m,k) => Object.hasOwn(params,k) ? String(params[k]) : m);
    },
    ttN:(key,n,params={}) => {
      assert(Object.hasOwn(en,key),'missing plural: ' + key);
      const entry = en[key], text = typeof entry === 'string' ? entry : n === 1 ? entry.one : entry.other;
      return text.replace(/\{(\w+)\}/g,(m,k) => k === 'count' ? String(n) : Object.hasOwn(params,k) ? String(params[k]) : m);
    },
    api:{get:async url => { calls.push(['get',url]); return {}; },post:async (url,body) => {calls.push(['post',url,body]); return {}; }},
    stale:(mode,mod) => ctx.state.mode !== mode || mod !== ctx.state.src,
    renderSounds:() => {}, loadSounds:async () => {}, cxPaint:() => {}, hlPaint:() => {},
    cxNamePickHtml:() => '', cxPoolOf:() => null, cxWithSurname:(n,s) => n+' '+s,
    setAppMode:mode => {ctx.state.mode=mode;}, loadSource:async () => {}, openEditor:type => calls.push(['unit',type]), rtOpen:(...args) => calls.push(['file',...args]),
    HL_SEV:{fatal:['x','w-bad','fatal'],warn:['!','w-warn','warning'],note:['.','','note']},
  });
  ctx.ttA = (key,params) => esc(ctx.tt(key,params));
  ctx.calls = calls; ctx.elements = elements;
  return ctx;
}
const run = (ctx,code) => vm.runInContext(code,ctx);
async function main(){
  const c = context();
  for(const file of ['cardgen.js','family.js','scripts.js','voices.js','healthx.js','guided.js']) vm.runInContext(read(file),c,{filename:file});
  check(true,'scripts load before later dependencies');
  run(c,"state.cg={cam:{yaw:12},post:{saturation:0}};cg()");
  check(c.state.cg.cam.yaw === 12 && c.state.cg.cam.pitch === 4 && c.state.cg.rig.type === 'auto','saved partial card settings merge');
  run(c,"state.cg.size='custom';state.cg.w=2;state.cg.h=9;state.cg.mult=2");
  check(JSON.stringify(run(c,'cgDimensions()')) === '[16,18]','custom dimensions and multiplier');
  check(run(c,"cgSelectHtml('','mult',[[1,'1'],[2,'2']])").includes('value="2" selected'),'numeric selections survive string input');
  c.armProj = () => ({objects:[{name:'Body'},{name:'BODY'},{name:'Hat',hidden:true},{name:'Shield',coll:'hidden'}]}); c.armCollHidden = o => o.coll === 'hidden';
  check(run(c,'cgObjects().length') === 1,'visible parts deduplicate case-insensitively');
  c.state.cg.oneEach = false; check(run(c,'cgObjects().length') === 2,'all visible variants');
  run(c,"var mask=new Uint8Array(81);mask[40]=1;var grown=cgDilate(mask,9,9,2)");
  check(run(c,'Array.from(grown).reduce((a,b)=>a+b,0)') === 25,'outline radius');
  run(c,"var pixel=new Uint8ClampedArray([100,150,200,255,20,30,40,0]);cgFinish(pixel,2,1,{})");
  check(run(c,"JSON.stringify(Array.from(pixel))") === '[100,150,200,255,20,30,40,0]','neutral finish preserves color and alpha');
  run(c,'cgFinish(pixel,2,1,{saturation:0})'); check(run(c,'pixel[0]===pixel[1]&&pixel[1]===pixel[2]&&pixel[7]===0'),'grayscale preserves transparency');
  c.armAnim=()=>({skel:'Man',key:'',list:{skeletons:{}},geos:new Map()}); c.armAnimEntries=()=>[]; c.armAnimFrac=()=>0;
  c.bmdbTabsHtml=()=>'';c.cardsSubTabsHtml=()=>''; c.cgWire=()=>{};c.cgDraw=()=>{};
  c.cardsSubNow=()=>c.state.cardsSub||'generate';
  c.state.mode='cards';c.state.cardsSub='generate';
  run(c,"CG_WORK.library={rigs:{},poses:[{n:'Pose',c:'Category',b:{}}]}");
  for(const pose of ['tpose','guard','brace','draw','riding','march','anim','rig']){
    c.state.cg.pose=pose;
    for(const size of ['card','large','info','custom','modcard','modinfo']){
      c.state.cg.size=size; run(c,'cgPaint()');
      assert(!/\{\w+\}/.test(c.main.innerHTML),'unfilled card translation for '+pose+'/'+size);
    }
  }
  check(c.main.innerHTML.includes('id="cgHd"')&&c.main.innerHTML.includes('name="cgSize"'),'all pose/size UI variants render with existing translations');
  c.state.mode='scripts';
  check(run(c,"GF_ATTR_HELP('HARDY_123')===GF_ATTR_HELP('hardy_1') && GF_ATTR_HELP('hp_damage_7')===GF_ATTR_HELP('hp_damage_2') && GF_ATTR_HELP(' hardy_1')===''"),'attribute help families and whitespace');
  check(run(c,"gfIsEx('HARDY_unusual123','attributes') && !gfIsEx('hardy_','attributes') && !gfIsEx('hp_damage_9','attributes') && gfIsEx('hp_damage_0','weapon')"),'extended classification contracts');
  const originalTt = c.tt; c.tt = key => 'new:' + key;
  check(run(c,"GF_ATTR_HELP('hardy')") === 'new:guided.attr_hardy','help translates at lookup'); c.tt = originalTt;
  c.state.mods = [{name:'Test',m2ex:1}]; check(run(c,"gfModEx({mod:'Test'}) && !gfModEx({mod:'test'}) && !gfModEx(null)"),'exact mod metadata');

  c.state.cx={mod:'Test',faction:'f',d:{campaign:'c'},fam:{ops:[],selected:'a',form:{name:'Child',age:0,dead:false,sex:'male'},data:{people:[{name:'A',source:'map',sex:'male',age:40},{name:'W',source:'record',sex:'female'}],tree:[{father:'A',wife:'W',children:[]}]},library:{error:'unavailable'}}};
  run(c,"fmRelative('son')"); check(c.state.cx.fam.ops.length === 2 && c.state.cx.fam.ops[0].age === 20,'relative stages two operations with default age');
  check(c.state.cx.fam.ops[1].wife === 'W' && c.state.cx.fam.ops[1].children[0] === 'Child','child preserves wife');
  check(run(c,'fmHtml()').includes('Child'),'staged person renders');
  c.state.cx.fam.data.tree=[{father:'A',wife:'nobody',children:['B']},{father:'B',wife:'nobody',children:['a']}];
  check(run(c,'fmHtml().length') < 20000,'ancestry cycles terminate');
  c.state.cx.fam.form.name=' '; const before=c.state.cx.fam.ops.length; run(c,"fmRelative('wife')"); check(c.state.cx.fam.ops.length===before,'blank names never stage');
  c.state.cx.fam.selected='w'; c.state.cx.fam.form.name='Sibling'; run(c,"fmRelative('sibling')"); check(c.calls.at(-1)[1]===en['family.no_parents'],'sibling needs parents');

  c.state.sx={mod:'Test',tab:'builder',view:'form',recipe:run(c,'sxNewRecipe()'),vocab:{events:[{key:'player_turn',label:'Turn'}],conditions:[{key:'test',label:'Test',help:'Help',fields:[{name:'names',kind:'names:units',label:'Names',default:[]}]}],actions:[],ops:[],match:[['all','All']],each:[['','None']],each_of:[['this','This']],examples:[]},mine:[]};
  run(c,"sxAdd('ifs')"); check(c.state.sx.recipe.ifs[0].k==='test','new row uses vocabulary defaults');
  run(c,"state.sx.pv={};sxFieldChange({dataset:{g:'ifs',i:'0',n:'names',list:'1'},value:' A, , B '})");
  check(JSON.stringify(c.state.sx.recipe.ifs[0].names)==='["A","B"]' && c.state.sx.pv===null,'recipe list field updates and invalidates');
  check(run(c,'sxFieldHtml("ifs",0,state.sx.vocab.conditions[0].fields[0],state.sx.recipe.ifs[0])').includes('data-list="1"'),'block-compatible field metadata');
  c.state.sx.cs={filter:'yes',picked:[99],pieces:[{n:2,frame:true,head:'yes'},{n:10,kind:'monitor',head:'yes',start:0,end:2,lines:3},{n:99,kind:'if',head:'other',start:4,end:5,lines:2}]};
  check(run(c,'sxCampaignMatches().length')===1 && run(c,'sxCampaignMatches()[0].n')===10,'campaign filters exclude frame and retain piece identities');
  c.state.sx.cs.pieces = Array.from({length:510},(_,i)=>({n:i,head:'yes',start:i,end:i,lines:1}));
  check(run(c,'sxCampaignMatches().length')===510 && (run(c,'sxCampaignRows()').match(/class="sxcsrow"/g)||[]).length===500,'display cap does not cap filtered removal');

  c.state.hl={mod:'Test',tab:'log',log:{found:true,path:'<unsafe>',age:90061,errors:2,warnings:1,verdict:{stopped:true,file:'x',line:2,col:4,now:'<bad>',headline:'Crash',lines:['<log>'],serious:['serious']},groups:[{level:'fatal',msg:'encountered an unspecified error',count:1},{level:'error',plain_first:'Problem',names:['a','b'],count:3,file:'data/x',seen:[{line:2,now:'<raw>',why:'why'}],msg:'original'},{level:'warning',msg:'Note',count:1,seen:[]}]}};
  const log=run(c,'hxPanelHtml()'); check(log.includes('&lt;bad&gt;') && !log.includes('encountered an unspecified error'),'log escapes input and omits redundant fatal');
  check(log.includes('<details class="hxnotes">'),'warning disclosure closed when problems exist');
  check(run(c,'hxAge(90061)')==='1 day ago' && run(c,'hxAge(59)')==='just now','log age units');
  await run(c,'hxFix("file","C:/game/data/folder/file.txt",7)'); check(c.calls.at(-1)[1]==='folder/file.txt','raw paths become data relative');
  c.state.hl.report={mod:'<mod>',campaign:'c',failed:{part:'failed'},factions:[{slot:'a',label:'A',special:'special'}],strat:{factions:[{slot:'a',playable:'playable',towns:[]}],counts:{}}};
  check(run(c,'hxReportHtml(state.hl.report)').includes('playable'),'contents joins faction slots');
  c.state.mode='health'; c.state.hl.sets={sets:[{name:'Set',mod:'Other'}]}; c.state.hl.tab='deep';
  c.state.hl.deep={set:'Set',records:2,files:['x'],ms:1234,failed:[],added:[{severity:'unknown',message:'<finding>',source:'s'}],cleared:[],same:4};
  check(run(c,'hxPanelHtml()').includes('&lt;finding&gt;') && run(c,'hxPanelHtml()').includes('1.2 s'),'deep severity fallback, escaping and timing');

  let resolve; c.state.mode='sounds'; c.state.snd={}; c.api.get=() => new Promise(r=>{resolve=r;});
  const first=run(c,"vxOpen('Old')"); const old=c.state.snd.hear; c.state.snd.hear={unit:'New'};
  resolve({heard:'a',heard_class:'c'}); await first; check(c.state.snd.hear.unit==='New' && !old.reply,'obsolete voice reply ignored');
  const second=run(c,"vxOpen('Unit')"); c.state.mode='edit'; let soundPaints=0;c.renderSounds=()=>{soundPaints++;};
  resolve({heard:'a',heard_class:'c'});await second;
  check(soundPaints===0,'voice reply cannot repaint a different application screen');c.state.mode='sounds';
  c.state.snd.hear={mod:'Test',unit:'<unit>',files:[],reply:{accent:'edu',class:'class',heard:'listen',heard_class:'class',accents:['a'],classes:['c'],packs:false,calls:[],orders:[]},listen:'listen',accent:'custom',class:'class'};
  const voice=run(c,'vxPanelHtml()'); check(voice.includes('&lt;unit&gt;') && voice.includes('preload="none"') && voice.includes(en['voices.no_name_call']),'voice panel safety, audio and empty messages');
  check(voice.includes('accent edu, voice_type class'),'EDU fields stay separate from listening accent');

  let reply; c.state.mode='health'; c.state.hl={mod:'Test',tab:'log'}; c.api.get=()=>new Promise(r=>{reply=r;});
  const pending=run(c,"hxLoad('log')"); c.state.hl={mod:'Other',tab:'log'}; reply({found:true}); await pending;
  check(!c.state.hl.log,'obsolete health context ignored');
  let familyReply,portraitReply; c.state.cx={mod:'Test',faction:'f',d:{campaign:'c'}};
  c.api.get=url=>new Promise(r=>{if(url.startsWith('/api/family?')) familyReply=r;else portraitReply=r;});
  run(c,'fmHtml()'); const oldFamily=c.state.cx.fam; c.state.cx={mod:'Other'}; familyReply({people:[],tree:[]});portraitReply({});await Promise.resolve();await Promise.resolve();
  check(!oldFamily.data,'obsolete family context ignored');
  c.state.mode='scripts'; c.state.src='Test'; c.calls.length=0;
  c.state.sx.addons=[{key:'addon',settings:[{var:'flag',kind:'bool'},{var:'names',kind:'list'},{var:'amount',kind:'int'}]}];
  c.elements.sx_addon_flag={checked:false};c.elements.sx_addon_names={value:' A, , B '};c.elements.sx_addon_amount={value:'12'};
  c.api.post=async (url,body)=>{c.calls.push(['post',url,body]);return {words:['Review'],plan:{changes:['Change'],warnings:[]}};};
  await run(c,"sxAddon(0,'install')");
  let body=c.calls.find(x=>x[0]==='post')[2];
  check(body.values.flag==='false'&&body.values.amount==='12'&&JSON.stringify(body.values.names)==='["A","B"]','add-on settings retain server types');
  check(c.calls.filter(x=>x[0]==='post').length===1,'cancelled add-on plan never applies');
  c.calls.length=0;c.state.sx.cs.sig='original';c.state.sx.cs.campaign='campaign';
  await run(c,'sxCampaignRemove(true)'); body=c.calls.find(x=>x[0]==='post')[2];
  check(body.drop.length===510&&body.sig==='original'&&body.campaign==='campaign','take shown plans all matches with original signature');
  check(c.calls.filter(x=>x[0]==='post').length===1,'cancelled campaign plan never applies');
  run(c,"state.sx.pv={problems:[]};state.sx.previewRecipe=JSON.stringify(state.sx.recipe);state.sx.recipe.each_faction='changed';sxRecipeEdited()");
  check(c.state.sx.pv===null,'direct block recipe edits invalidate preview');
  c.elements.sxPreview={innerHTML:'Old save action'};
  run(c,"state.sx.pv=null;state.sx.recipe.once=!state.sx.recipe.once;sxRecipeEdited()");
  check(c.elements.sxPreview.innerHTML==='','block edits that clear pv also remove stale Save controls');
  c.state.sx.mine=[{recipe:c.state.sx.recipe}];run(c,'sxOpenMine(0)');c.state.sx.recipe.title='Edited';
  check(c.state.sx.mine[0].recipe.title!=='Edited','saved modules open as independent copies');
  c.state.mode='sounds';c.state.snd.hear.files=[{name:'a.wav',b64:'abc'}];c.calls.length=0;
  await run(c,'vxApply()');
  check(c.state.snd.hear.files.length===1&&c.calls.filter(x=>x[0]==='post').length===1,'cancelled voice plan retains files');
  c.elements.vxAudio={play:async()=>{throw new Error('Playback failed');}};
  await run(c,"vxPlay('sounds/name.wav')");
  check(c.elements.vxAudio.src.includes('rel=sounds%2Fname.wav')&&c.calls.at(-1)[1]==='Playback failed','audio route and rejection notification');
  c.state.mode='cards';c.state.cardsSub='generate';c.state.cg.saved={path:'saved.png',kind:'info'};c.state.cg.unit='Unit';c.calls.length=0;
  await run(c,'cgGive(false)');body=c.calls.find(x=>x[0]==='post')[2];
  check(body.info_src==='saved.png'&&!Object.hasOwn(body,'card_src'),'information pictures use info_src');
  c.ARM={loading:null};let loaded;c.armEnsureLoaded=()=>new Promise(r=>{loaded=r;});c.api.get=async()=>({});
  const rendering=run(c,'renderCardGen()');c.state.mode='edit';c.main.innerHTML='Away';loaded();await rendering;
  check(c.main.innerHTML==='Away','late card resource replies cannot replace another screen');
  console.log(assertions+' clean-room browser contract checks passed');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
