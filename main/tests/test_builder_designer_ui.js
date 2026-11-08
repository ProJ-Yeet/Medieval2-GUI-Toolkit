const fs=require('fs'),vm=require('vm'),assert=require('assert');
const tables=JSON.parse(fs.readFileSync('unittransfer/builder_rules.json','utf8')).tables;
const strings=JSON.parse(fs.readFileSync('web/i18n/en.json','utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tick=()=>new Promise(r=>setTimeout(r,5));
async function main(){
 const els={},calls=[],pending=[];let saved=null,rev='r0',hostWrites=0;
 const modal={className:'',get innerHTML(){return this.html||'';},set innerHTML(v){hostWrites++;this.html=v;}};
 for(const id of ['bd_edit_id','bdResults','bdStatus','bdPresetFields','bdWeaponOptions','bdEligibility'])els[id]={innerHTML:'',textContent:''};
 els.modal=modal;els.overlay={classList:{contains:()=>true}};
 const c={console,Set,Map,Promise,JSON,Math,setTimeout,clearTimeout,structuredClone,
  state:{src:'Fixture',mods:[],ed:null,settings:{}},modal,esc,ttA:k=>strings[k]||k,ttN:k=>strings[k]||k,
  tt:(k,p={})=>(strings[k]||k).replace(/\{(\w+)\}/g,(_,n)=>p[n]??n),
  overlay:{classList:{add(){},contains(){return true;},remove(){}}},
  document:{getElementById:id=>els[id]||null,addEventListener(){},querySelectorAll:()=>[],activeElement:null},
  window:{scrollY:0,scrollX:0,scrollTo(){}},requestAnimationFrame:fn=>fn(),toast(){},paintDirty(){},errText:e=>e.message,
  enc:encodeURIComponent,closeModal(){},renderEditor(){},openNewUnitPicker(){},
  api:{post:async(url,body)=>{
   calls.push({url,body:clone(body)});
   if(url.endsWith('/load'))return {design:clone(saved),revision:rev,source_token:'source',tables:clone(tables),defaults:{unit_category:'Martial Nobility',quality:'Average',category:'infantry',class:'heavy',equipment_grade:'common',pri_preset:'arming_sword',sec_preset:'none',armour_preset:'unarmored',armour_weight:'medium',offhand:'empty',origin:'Western European',bible_formation_auto:true},native:{attack:5}};
   if(url.endsWith('/save')){assert.equal(body.revision,rev);saved=clone(body.design);rev+='x';return {design:clone(saved),revision:rev,source_token:'source'};}
   if(url.endsWith('/preview')){
    if(c.delay)return new Promise(resolve=>pending.push({resolve,body:clone(body)}));
    return reply(body);
   }
   throw Error(url);
  }}
 };
 function reply(body){return {design:clone(body.design),native:{attack:7,recruit_cost:500},explanations:{attack:{terms:{weapon:5,equipment_grade:0},result:7}},edu:'type preview\nstat_pri 7',metadata:{omitted:{pri_attributes:['sp']},upgrade_preview:{attack:10,armor:4},engine_rules:{profile:'vanilla',weapon_upgrade_attack:{value:3,source:'engine_default',status:'default'},armour_upgrade_armour:{value:2,source:'engine_default',status:'default'},notes:[{id:'builder.upgrade_card_note',params:{weapon:3,armour:2}}]}}};}
 vm.createContext(c);
 vm.runInContext(fs.readFileSync('web/js/builder.js','utf8'),c);
 vm.runInContext(fs.readFileSync('web/js/undo.js','utf8'),c);
 c.undoFocus=()=>null;c.scrollSnapshot=()=>[];c.scrollRestore=()=>{};c.undoRefocus=()=>{};c.paintDirty=()=>{};
 const get=s=>vm.runInContext(s,c);
 await c.bdOpen('');
 assert.equal(c.state.builder.design,null,'opening must not select a balance profile');
 assert(modal.innerHTML.includes('Combat Reforged'));
 c.bdStart('combat-reforged');await tick();
 assert(c.state.builder.design);
 // Drive the rendered handlers, including text inputs; no app-specific testing copies.
 function change(key,value,event='change'){
  const html=modal.innerHTML;
  const tag=[...html.matchAll(/<(?:input|select|textarea)\b([^>]*)>/g)].find(m=>m[1].includes('id="bd_'+key+'"'));
  assert(tag,'rendered control '+key);
  const handler=tag[1].match(new RegExp('on'+event+'="([^"]+)"'));assert(handler,'handler '+key);
  const el={value,checked:!!value};c.el=el;
  get('(function(){'+handler[1].replace(/&quot;/g,'"').replace(/&#39;/g,"'")+'}).call(el)');
 }
 for(const [category,cls,preset] of [['infantry','heavy','arming_sword'],['infantry','missile','self_bow'],['cavalry','heavy','horseman_sword'],['infantry','heavy','great_sword']]){
  change('category',category);change('class',cls);change('pri_preset',preset);await tick();
  assert.equal(calls.at(-1).body.design.inputs.pri_preset,preset);
  assert(els.bdResults.innerHTML.includes('stat_pri'));
 }
 assert(c.bdEligible('pri','self_bow')===false);
 assert(c.bdPresetOptions('pri').includes('disabled'));
 // Inherited grips and automatic formation must display the effective defaults.
 assert(modal.innerHTML.match(/id="bd_pri_twohand"[^>]*\schecked(?:\s|>)/),'two-handed preset defaults must be visible');
 assert(modal.innerHTML.match(/id="bd_bible_formation_auto"[^>]*\schecked(?:\s|>)/),'automatic formation defaults to on');
 change('hide_forest_override','false');
 assert(modal.innerHTML.match(/value="false" selected/),'false hiding state survives redraw');
 change('hide_forest_override','inherit');
 assert(!('hide_forest_override' in c.state.builder.design.overrides.inputs));
 change('pri_category','axe');change('pri_category','');
 assert(!('pri_category' in c.state.builder.design.inputs),'blank category resumes preset inheritance');
 c.state.builder.design.overrides.inputs.equipment_grade='poor';
 change('equipment_grade','high');assert.equal(c.bdValue('equipment_grade'),'high','editing an overridden selection takes effect');
 // Selecting an ineligible preset stays visible with a localized reason.
 change('pri_preset','self_bow');await tick();assert(els.bdEligibility.innerHTML.includes('role'));
 change('class','missile');change('sec_preset','arming_sword');await tick();
 let writes=hostWrites,fields=els.bdPresetFields;
 change('pri_base_atk','12','input');change('pri_base_atk','123','input');await tick();
 assert.equal(hostWrites,writes,'live typing must not replace the form');assert.strictEqual(els.bdPresetFields,fields);
 assert.equal(c.state.builder.design.overrides.inputs.pri_base_atk,'123');
 c.bdPresetEdit('pri','atk','19');await tick();assert.equal(hostWrites,writes,'preset typing must not replace the form');
 change('equipment_grade','high');change('pri_preset','crossbow');await tick();
 assert.equal(c.state.builder.design.overrides.inputs.pri_base_atk,'123');
 c.bdPin('attack','0');c.bdInput('hide_forest_override',false,true);await tick();
 assert.equal(c.state.builder.design.overrides.native.attack,0);
 assert(els.bdResults.innerHTML.includes('unit card shows +1'));
 c.bdSelect('pri_preset','self_bow');c.bdPresetReset('pri');await tick();
 assert(!c.state.builder.design.presets.pri?.self_bow);
 assert.equal(c.state.builder.design.overrides.inputs.pri_base_atk,'123');
 c.bdInherit('pri_base_atk');await tick();assert(!('pri_base_atk' in c.state.builder.design.overrides.inputs));
 // Preset filtering replaces only its option list, never the search control or form.
 writes=hostWrites;change('filter','sword','input');assert.equal(hostWrites,writes);assert(els.bd_edit_id.innerHTML.includes('sword'));assert(c.bdEditKey().includes('sword'),'visible preset and edited row must agree');c.bdFilter('');
 // Armor ensemble defaults are visible; explicit layer/base choices survive changes.
 change('armour_preset','mail_med');assert.equal(c.bdValue('armour_layer1'),tables.loadouts.mail_med[1]);
 c.bdInput('armour_layer1','reinforcing');change('armour_preset','full_plate');assert.equal(c.bdValue('armour_layer1'),'reinforcing');
 // Unknown snapshot keys cannot become executable inline handlers.
 c.state.builder.design.presets.pri={self_bow:{["');alert(1);//"]:2}};c.state.builder.family='pri';c.state.builder.editId='self_bow';
 assert(!c.bdPresetFields().includes('alert(1)'));
 // Undo/redo through the real shared snapshot stack.
 c.undoReset();c.bdInput('cost_construct','100');c.undoCapture('cost');
 c.bdInput('cost_construct','200');c.undoCapture('other');
 assert(c.undoStep(false));await tick();assert.equal(c.state.builder.design.overrides.inputs.cost_construct,'100');
 assert(c.undoStep(true));await tick();assert.equal(c.state.builder.design.overrides.inputs.cost_construct,'200');
 await c.bdSave();const packet=clone(c.state.builder.design);
 c.state.builder=null;await c.bdOpen('');await tick();assert.deepEqual(clone(c.state.builder.design),packet);
 // Late previews cannot replace a newer result, and a save cannot overwrite edits typed while it waits.
 c.delay=true;c.bdInput('cost_construct','300');await tick();c.bdInput('cost_construct','400');await tick();
 const older=pending.shift(),newer=pending.shift();assert(older&&newer);
 newer.resolve({...reply(newer.body),edu:'latest'});await tick();older.resolve({...reply(older.body),edu:'stale'});await tick();
 assert(els.bdResults.innerHTML.includes('latest')&&!els.bdResults.innerHTML.includes('stale'));
 c.delay=false;
 // Failed previews clear old results, retain typed values and leave the input form intact.
 const post=c.api.post;c.api.post=async(url,body)=>{if(url.endsWith('/preview'))return {error:'refused'};return post(url,body);};
 writes=hostWrites;c.bdInput('cost_construct','500');await tick();assert.equal(hostWrites,writes);
 assert.equal(c.state.builder.design.overrides.inputs.cost_construct,'500');assert(els.bdResults.innerHTML.includes(strings['builder.invalid']));
 c.api.post=async(url,body)=>url.endsWith('/save')?{error:'conflict'}:post(url,body);
 const savedBefore=c.state.builder.saved;await c.bdSave();assert.equal(c.state.builder.saved,savedBefore);assert(els.bdStatus.textContent.includes(strings['builder.save_failed']));
 c.api.post=post;
 // Escape all user-controlled preview, preset and metadata values.
 c.state.builder.result={...reply({design:packet}),edu:'<script>bad</script>'};c.bdResultsPaint();
 assert(!els.bdResults.innerHTML.includes('<script>'));
 const editor=fs.readFileSync('web/js/editor.js','utf8'),settings=fs.readFileSync('web/js/settings.js','utf8');
 assert(editor.includes('bdOpen('));assert(settings.includes('bdOpen('));
 assert(!calls.some(x=>/apply|stage|edit\//.test(x.url)));
 // The same workflow sends the exact editor unit ID without touching editor edits.
 c.state.builder=null;c.state.ed={mod:'Fixture',unit:'Guard',ov:{stat_pri:'keep'}};
 await c.bdOpen('Guard');await tick();c.bdInput('cost_construct','700');await c.bdSave();
 assert.equal(calls.at(-1).body.unit,'Guard');assert.equal(c.state.ed.ov.stat_pri,'keep');
 console.log('Builder designer UI: all assertions passed');
}
main().catch(e=>{console.error(e);process.exit(1);});
