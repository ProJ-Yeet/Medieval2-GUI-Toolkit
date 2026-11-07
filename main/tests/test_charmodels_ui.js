/* Phase 101j: real dialog handlers with fixture responses. */
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const calls=[];
const fixture={roster:['sicily'],faction:'sicily',sig:'sig',strat_models:['default','heir'],battle_models:['mounted','foot'],
 named:[{type:'named character',line:3,factions:['sicily'],slots:[{line:4,level:1,model:'heir',traits:['FactionHeir'],comment:'Custom'}],battle_model:{line:5,value:'mounted',exists:true,horse:true}}],
 captain:[],agents:[],characters:[{campaign:'imperial_campaign',name:'King',line:20,rank:'leader',battle_model:'mounted'}],
 scripts:[{rel:'world/maps/campaign/imperial_campaign/campaign_script.txt',line:9,who:'leader',model:'foot',commented:true}],
 symbols:{symbol:'s.cas',rebel_symbol:'r.cas'},strat_textures:['default'],findings:[]};
const modal={innerHTML:'',querySelectorAll:()=>[]};
const c={console,Set,Map,Promise,structuredClone,state:{src:'Fixture'},modal,document:{getElementById:()=>modal},
 overlay:{classList:{add(){}}},tt:(k,p)=>k+(p?JSON.stringify(p):''),ttA:k=>k,enc:encodeURIComponent,
 esc:v=>String(v).replace(/</g,'&lt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'),q1:v=>String(v).replace(/'/g,"\\'"),
 navLinkHtml:(r,label)=>`<a data-mode="${r.mode}">${label}</a>`,toast(){},errText:e=>e.message,
 api:{get:async url=>{calls.push({url});return structuredClone(fixture);},post:async(url,body)=>{
 calls.push({url,body:structuredClone(body)});return {plan:{changes:['changed'],warnings:['warning'],errors:[],ok:true},record:{id:'fixture'}};}}};
vm.createContext(c);
vm.runInContext(fs.readFileSync('web/js/charmodels.js','utf8'),c);
(async()=>{
 await c.openFactionModels('sicily');
 assert(modal.innerHTML.includes('FactionHeir'));assert(modal.innerHTML.includes('Custom'));
 assert(modal.innerHTML.includes('cmStratNames'));assert(modal.innerHTML.includes('cmBattleNames'));
 assert(modal.innerHTML.includes('s.cas'));assert(modal.innerHTML.includes('campaign_script.txt'));
 c.cmSetValue(4,'default','heir');c.cmSetCharacter(0,'foot');
 await c.cmPreview();
 assert(calls.some(x=>x.url==='/api/characters/plan'&&x.body.sig==='sig'&&x.body.values['4']==='default'));
 const plan=calls.find(x=>x.url==='/api/map/character_plan');
 assert.equal(plan.body.action,'edit');assert.equal(plan.body.line,20);assert.equal(plan.body.edits.battle_model,'foot');
 assert(modal.innerHTML.includes('changed'));assert(modal.innerHTML.includes('warning'));
 await c.cmApply();
 assert(calls.some(x=>x.url==='/api/characters/apply'));assert(calls.some(x=>x.url==='/api/map/character_apply'));
 assert.equal(calls.filter(x=>x.url.startsWith('/api/charmodels')).length,2);
 c.cmSetValue(4,'default','heir');await c.cmPreview();c.cmSetValue(4,'heir','heir');
 const before=calls.filter(x=>x.url.endsWith('/apply')).length;await c.cmApply();
 assert.equal(calls.filter(x=>x.url.endsWith('/apply')).length,before,'changed edits invalidate preview');
 // Failed plans cannot be applied, and a partial save reloads the actual disk state.
 c.cmSetValue(4,'default','heir');
 const post=c.api.post;
 c.api.post=async()=>({error:'stale fixture',plan:{changes:[],warnings:[],errors:['stale fixture'],ok:false}});
 await c.cmPreview();assert(modal.innerHTML.includes('stale fixture'));
 await c.cmApply();assert.equal(calls.filter(x=>x.url.endsWith('/apply')).length,before);
 c.api.post=post;c.cmSetCharacter(0,'foot');await c.cmPreview();
 c.api.post=async(url,body)=>url==='/api/map/character_apply'?{error:'second save refused'}:post(url,body);
 await c.cmApply();assert(modal.innerHTML.includes('second save refused'));
 assert(modal.innerHTML.includes('charmodels.applied'));assert.equal(calls.filter(x=>x.url.startsWith('/api/charmodels')).length,3);
 c.api.post=post;
 // The entry cards consume the joined response and preserve level/comment labels.
 vm.runInContext(fs.readFileSync('web/js/bmdb.js','utf8'),c);
 vm.runInContext(fs.readFileSync('web/js/stratmap.js','utf8'),c);
 c.undoReset=()=>{};c.resetPlace=()=>{};c.edRenderTab=()=>{};c.bmCvToggleHtml=()=>'';c.cleanerBoxHtml=()=>'';
 c.ttN=c.tt;c.state.settings={};
 c.api.get=async url=>url.startsWith('/api/bmdb/entry')?{
   model:{name:'foot',lods:[],factions:[],used_by:[]},characters:[{source:'descr_character',type:'named character',key:'block/3',faction:'sicily',role:'generals'}],character_horse:false
 }: {name:'heir',line:1,used_by:[],files:[],factions:[],raw:'',characters:[{key:'block/3',type:'named character',faction:'sicily',level:1,traits:['FactionHeir'],label:'Custom'}]};
 await c.openBmdbEntry('foot');assert(modal.innerHTML.includes('charmodels.characters'));assert(modal.innerHTML.includes('charmodels.horse'));
 assert(modal.innerHTML.includes('data-mode="characters"'));
 await c.openStratEntry('heir');assert(modal.innerHTML.includes('FactionHeir'));assert(modal.innerHTML.includes('Custom'));
 assert(modal.innerHTML.includes('charmodels.level'));assert(modal.innerHTML.includes('openFactionModels'));
 // A campaign character link selects the intended campaign, faction and line.
 c.state.cmap={campaign:''};c.cmapSetCampaign=rel=>{c.state.cmap.campaign=rel;};
 c.cxOpen=async faction=>{c.state.cx={faction,d:{characters:[{name:'King',line:20},{name:'King',line:21}]}};};
 let picked=-1,surface='';c.cxPick=i=>{picked=i;};c.cmapSurface=id=>{surface=id;};
 await c.cmMapCharacter({campaign:'custom/nested',faction:'sicily',name:'King',line:21});
 assert.equal(c.state.cmap.campaign,'custom/nested');assert.equal(picked,1);assert.equal(surface,'cmChars');
 // A level's traits come from the whole EDCT (DaC gives level 3 to 22 heroes):
 // four are shown, the count of the rest, and all of them on hover.
 const many=c.cmLevelHtml({level:3,traits:['A','B','C','D','E','F'],comment:'3 (Custom)'});
 assert(many.includes('charmodels.more{"names":"A, B, C, D","n":2}'));assert(many.includes('title="A, B, C, D, E, F"'));
 assert(!c.cmLevelHtml({level:1,traits:['FactionHeir']}).includes('title='));
 console.log('PASS: faction fields, existing plans, warnings, apply, reload and preview invalidation');
})().catch(e=>{console.error(e);process.exitCode=1;});
