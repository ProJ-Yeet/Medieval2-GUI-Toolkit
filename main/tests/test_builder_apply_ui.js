// Phase 106: the designer's Apply panel stages ticked fields and hands them to
// the Unit Editor's own edits or to New unit's composer. It writes nothing itself.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const strings=JSON.parse(fs.readFileSync('web/i18n/en.json','utf8'));
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function main(){
 const els={bdApply:{innerHTML:''},bdStatus:{textContent:''}},calls=[],toasts=[];let reply=null,started=null,closed=0;
 const cfgs={};
 const c={console,Set,Map,Promise,JSON,Object,Array,
  state:{src:'Fixture',data:{units:[{type:'Rider',name:'Riders'},{type:'Guard',name:'Guards'}]},ed:null},
  esc,q1:v=>v.replace(/\\/g,'\\\\').replace(/'/g,"\\'"),
  tt:(k,p={})=>{assert(k in strings,'missing string '+k);return strings[k].replace(/\{(\w+)\}/g,(_,n)=>p[n]??n);},
  document:{getElementById:id=>els[id]||null},toast:t=>toasts.push(t),
  cfgFor:t=>cfgs[t]||(cfgs[t]={field_overrides:{old:'x'}}),startNewUnit:t=>{started=t;},
  renderEditor(){},undoReset(){},openNewUnitPicker(){},
  api:{post:async(url,body)=>{calls.push({url,body});return reply;}}};
 vm.createContext(c);
 vm.runInContext(fs.readFileSync('web/js/builder.js','utf8'),c);
 c.bdClose=()=>{closed++;};
 const result={native:{attack:9,armor:4},explanations:{},metadata:{}};

 // An existing unit: tick, stage, then into the editor's pending edits.
 c.state.ed={ov:{stat_mental:'7, normal, trained'},rm:new Set(['stat_pri','era 2'])};
 c.state.builder={mod:'Fixture',unit:'Guard',design:{profile:{id:'native'}},result,seq:1,active:true,labels:{}};
 c.bdApplyPaint();
 assert(/<button onclick="bdStage\(\)" disabled/.test(els.bdApply.innerHTML),'nothing ticked, nothing to stage');
 c.bdPick('attack',true);
 assert(!/bdStage\(\)" disabled/.test(els.bdApply.innerHTML));
 reply={mode:'edit',target:'Guard',profile:'native',field_overrides:{stat_pri:'9, 2'},remove_fields:[],
  changes:[{column:'attack',before:5,after:9}],missing:[]};
 await c.bdStage();
 assert.deepEqual(calls.at(-1),{url:'/api/builder/stage',body:{mod:'Fixture',design:{profile:{id:'native'}},fields:['attack'],unit:'Guard'}});
 assert(els.bdApply.innerHTML.includes('bdHandOver()'));
 c.bdHandOver();
 assert.equal(c.state.ed.ov.stat_pri,'9, 2');
 assert.equal(c.state.ed.ov.stat_mental,'7, normal, trained','other pending edits stay');
 assert(!c.state.ed.rm.has('stat_pri'),'a staged field is no longer marked for removal');
 assert(c.state.ed.rm.has('era 2'));
 assert.equal(closed,1);assert.equal(toasts.length,1);

 // A missing prerequisite blocks the hand-over.
 reply={...reply,missing:[{kind:'projectile',name:'fire_arrow'},{kind:'mount',name:''}]};
 await c.bdStage();
 assert(!els.bdApply.innerHTML.includes('bdHandOver()'));
 assert(els.bdApply.innerHTML.includes('fire_arrow'));
 const ov={...c.state.ed.ov};c.bdHandOver();assert.deepEqual(c.state.ed.ov,ov);

 // Recalculating drops a staged result: it no longer matches the design.
 c.bdPick('armor',true);assert.equal(c.state.builder.staged,null);

 // A new unit: a donor is required, then New unit opens on it with the fields.
 c.state.ed=null;
 c.state.builder={mod:'Fixture',unit:'',design:{profile:{id:'native'}},result,seq:1,active:true,labels:{},pick:new Set(['armor'])};
 c.bdApplyPaint();
 assert(/bdStage\(\)" disabled/.test(els.bdApply.innerHTML),'no donor yet');
 assert(els.bdApply.innerHTML.indexOf('Guards (Guard)')<els.bdApply.innerHTML.indexOf('Riders (Rider)'));
 c.bdDonor('Rider');
 reply={mode:'new',target:'Rider',profile:'native',field_overrides:{stat_pri_armour:'4, 2, 3, metal'},remove_fields:[],
  changes:[{column:'armor',before:3,after:4}],missing:[]};
 await c.bdStage();
 assert.equal(calls.at(-1).body.donor,'Rider');assert(!('unit' in calls.at(-1).body));
 c.bdHandOver();
 assert.equal(started,'Rider');
 assert.deepEqual(cfgs.Rider.field_overrides,{stat_pri_armour:'4, 2, 3, metal'});
 assert.equal(c.state.builder.active,false);
 console.log('test_builder_apply_ui: PASS');
}
main().catch(e=>{console.error(e);process.exit(1);});
