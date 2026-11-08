/* builder.js - Guided, draft-only designer using the Phase 103 calculator.
   Rules: lupinemaverick, MUG Unit Builder v1.5 / MUG Unit Creation Guide,
   Combat Reforged work for King Siegfried. No upstream scripts are executed. */
const BD_FAMILIES={archetypes:'unit_category',foot_quality:'quality',mounted_quality:'quality',grades:'equipment_grade',pri:'pri_preset',sec:'sec_preset',
  weapon_categories:'pri_category',armour:'armour_base',loadouts:'armour_preset',layers:'armour_layer1',offhands:'offhand',horse:'horse_type',breed:'horse_origin',barding:'horse_barding',shield_type:'shield_type',shield_mat:'shield_material',terrain:'origin'};
const BD_SUBTYPES=['guards','hybrid','aggressive','reckless','fanatic','bloc','raider','mounted','engineer','mercenary','garrison','command'];
const BD_EXPORTS={project:['builder.download_project','builder.copy_project'],presets:['builder.download_presets','builder.copy_presets'],
  upstream:['builder.download_upstream','builder.copy_upstream'],edu:['builder.download_edu','builder.copy_edu'],csv:['builder.download_csv','builder.copy_csv']};
function bdCurrent(){return state.builder;}
function bdValue(key,fallback){
  const d=bdCurrent().design;
  if(Object.hasOwn(d.overrides.inputs,key))return d.overrides.inputs[key];
  if(Object.hasOwn(d.inputs,key))return d.inputs[key];
  if(/^armour_layer[1-3]$/.test(key))return (bdCurrent().tables.loadouts[bdValue('armour_preset','unarmored')]||[])[Number(key.slice(-1))]||'none';
  return fallback??bdCurrent().defaults[key]??'';
}
function bdLabel(key){const b=bdCurrent();return (b.labels||(b.labels=bdLabels()))[key]||key;}
async function bdOpen(unit){
  const mod=state.ed&&unit?state.ed.mod:state.src;
  let b=bdCurrent();
  if(!b||b.mod!==mod||b.unit!==unit){
    let r;
    try{r=await api.post('/api/builder/load',{mod,unit});if(r.error)throw r;}
    catch(e){toast(tt('builder.load_failed'));return;}
    b={mod,unit,...r,saved:JSON.stringify(r.design),result:null,seq:0,filter:'',family:'pri',editId:'',error:'',active:true};
    state.builder=b;
  }
  b.active=true;
  document.getElementById('modal').className='modal wide';
  overlay.classList.add('open');bdRender();undoReset();
  if(b.design)bdCalculate();
}
function bdClose(){
  const b=bdCurrent();b.active=false;++b.seq;
  if(b.unit&&state.ed){renderEditor();undoReset();}
  else{openNewUnitPicker();undoReset();}
}
function bdStart(profile){
  const b=bdCurrent();
  b.design={schema:'m2-unit-design',version:1,profile:{id:profile,revision:profile==='native'?'1':'d4ed9368d0db3da2000bc895e96f52a83b93cb67'},
    inputs:profile==='native'?{}:{...b.defaults},
    presets:{},overrides:{inputs:{},native:profile==='native'?{...b.native}:{}},metadata:{}};
  bdRender();bdCalculate();
}
function bdRender(){
  const b=bdCurrent(),d=b.design;
  document.getElementById('modal').innerHTML=`<h2>${tt('builder.title')}</h2><div class="mbody">
    <p class="count">${tt('builder.preview_only')}</p>
    <details><summary>${tt('builder.portable')}</summary><p class="count">${tt('builder.portable_help')}</p>
      <label>${tt('builder.import_project')}<input type="file" accept=".json,application/json" onchange="bdImportFile(this)"></label>
      ${d?`<div>${['project','presets','upstream','edu','csv'].filter(f=>f!=='upstream'||d.profile.id==='combat-reforged').map(f=>
        `<button onclick="bdExport('${f}',false)">${tt(BD_EXPORTS[f][0])}</button><button onclick="bdExport('${f}',true)">${tt(BD_EXPORTS[f][1])}</button>`).join('')}</div>`:''}</details>
    ${!d?`<p>${tt('builder.choose_profile')}</p><pre>${esc(JSON.stringify(b.native,null,2))}</pre>
      <button onclick="bdStart('native')">${tt('builder.native_profile')}</button>
      <button onclick="bdStart('combat-reforged')">${tt('builder.reforged_profile')}</button>`:
    `<p>${esc(d.profile.id==='native'?tt('builder.native_profile'):tt('builder.reforged_profile'))}</p>
     <div id="bdForm">${bdForm()}</div><div id="bdEligibility" class="w-warn"></div>
     <div id="bdResults" aria-live="polite"></div>`}
    <div id="bdStatus" role="status"></div></div><div class="foot">
      <button onclick="bdClose()">${tt('builder.back')}</button>
      ${d?`<button onclick="undoStep(false)">${tt('builder.undo')}</button><button onclick="undoStep(true)">${tt('builder.redo')}</button>
      <button class="primary" onclick="bdSave()">${tt('builder.save_draft')}</button>`:''}</div>`;
  bdEligibilityPaint();bdResultsPaint();bdStatus();
}
function bdSelectControl(key,values,fallback){
  return `<label class="gfrow">${esc(bdLabel(key))}<select id="bd_${key}" onchange="bdSelect('${key}',this.value)">${values.map(v=>`<option value="${esc(v)}"${String(bdValue(key,fallback))===v?' selected':''}>${esc(v===''?tt('builder.inherited'):bdLabel(v))}</option>`).join('')}</select></label>`;
}
function bdNumber(key){
  const d=bdCurrent().design,own=Object.hasOwn(d.overrides.inputs,key),value=own?d.overrides.inputs[key]:'';
  return `<label class="gfrow">${esc(bdLabel(key))}<input id="bd_${key}" type="text" inputmode="decimal" value="${esc(value)}" placeholder="${ttA('builder.inherited')}" oninput="bdInput('${key}',this.value)">
    <button type="button" onclick="bdInherit('${key}')">${tt('builder.inherit')}</button></label>`;
}
function bdText(key){
  return `<label class="gfrow">${esc(bdLabel(key))}<input id="bd_${key}" value="${esc(bdValue(key))}" oninput="bdInput('${key}',this.value)">
    <button type="button" onclick="bdInherit('${key}')">${tt('builder.inherit')}</button></label>`;
}
function bdCheck(key){
  const b=bdCurrent(),slot=key.startsWith('sec_')?'sec':'pri';
  const preset={...b.tables[slot][bdValue(slot+'_preset')],...b.design.presets[slot]?.[bdValue(slot+'_preset')]};
  const fallback=key.endsWith('_twohand')?!!preset.twohand:key==='bible_formation_auto';
  return `<label class="chk"><input id="bd_${key}" type="checkbox"${bdValue(key,fallback)?' checked':''} onchange="bdInput('${key}',this.checked,true)"> ${esc(bdLabel(key))}</label>
    <button type="button" onclick="bdInherit('${key}')">${tt('builder.inherit')}</button>`;
}
function bdTableIds(family){const b=bdCurrent();return [...new Set([...Object.keys(b.tables[family]),...Object.keys(b.design.presets[family]||{})])];}
function bdTableSelect(family,key,fallback){return bdSelectControl(key,bdTableIds(family),fallback);}
function bdWeaponSelect(slot){return `<label class="gfrow">${esc(bdLabel(slot+'_preset'))}<select id="bd_${slot}_preset" onchange="bdSelect('${slot}_preset',this.value)">${bdPresetOptions(slot)}</select></label>`;}
function bdForm(){
  const b=bdCurrent(),d=b.design;
  const pins=`<details><summary>${tt('builder.final_pins')}</summary><p class="count">${tt('builder.pin_help')}</p>
    ${['attack','armor','defense','shield','morale','recruit_cost','upkeep'].map(k=>`<label class="gfrow">${esc(bdLabel(k))}<input id="bd_pin_${k}" value="${esc(d.overrides.native[k]??'')}" oninput="bdPin('${k}',this.value)"></label>`).join('')}</details>`;
  if(d.profile.id==='native')return pins;
  return `<fieldset><legend>${tt('builder.identity')}</legend>
    ${bdTableSelect('archetypes','unit_category',b.defaults.unit_category)}${bdTableSelect('foot_quality','quality',b.defaults.quality)}
    ${bdSelectControl('category',['infantry','cavalry','siege'],'infantry')}${bdSelectControl('class',['heavy','light','spearmen','missile','skirmish'],'heavy')}
    ${bdTableSelect('grades','equipment_grade','common')}
    <p class="count">${tt('builder.grade_help')}</p>${BD_SUBTYPES.map(k=>bdCheck('trait_'+k)).join('')}
    <p class="count">${tt('builder.subtype_help')}</p></fieldset>
    <fieldset><legend>${tt('builder.weapons')}</legend>
    ${['pri','sec'].map(s=>`${bdWeaponSelect(s)}${bdSelectControl(s+'_category',['',...bdTableIds('weapon_categories'),'bow','crossbow','firearm','thrown','none'],'')}
      ${bdCheck(s+'_twohand')}<details><summary>${esc(bdLabel(s))}</summary>
      ${['base_atk','base_charge','handling','range','ammo','delay','heat'].map(k=>bdNumber(s+'_'+k)).join('')}
      ${bdText(s+'_attr')}${bdText(s+'_missile')}</details>`).join('')}
    <p class="count">${tt('builder.weapon_help')}</p></fieldset>
    <fieldset><legend>${tt('builder.equipment')}</legend>
      ${bdTableSelect('loadouts','armour_preset','unarmored')}${bdSelectControl('armour_base',['',...bdTableIds('armour')],'')}${bdSelectControl('armour_weight',['light','medium','heavy'],'medium')}
      ${[1,2,3].map(i=>bdTableSelect('layers','armour_layer'+i,'none')).join('')}
      ${bdSelectControl('offhand',[...Object.keys(b.tables.offhands),'legacy'],'empty')}
      ${bdTableSelect('shield_type','shield_type','none')}${bdTableSelect('shield_mat','shield_material','wooden')}
      <p class="count">${tt('builder.layer_help')}</p></fieldset>
    <fieldset><legend>${tt('builder.mounted')}</legend>
      ${bdTableSelect('horse','horse_type','stallion')}${bdTableSelect('breed','horse_origin','western_europe')}${bdTableSelect('barding','horse_barding','none')}
      ${bdSelectControl('cav_style',['lancer','charger','brawler'],'lancer')}<p class="count">${tt('builder.mount_help')}</p></fieldset>
    <fieldset><legend>${tt('builder.attributes')}</legend>
      ${bdText('extra_attrs')}${bdText('unit_custom_attrs')}${bdCheck('can_sap')}
      ${bdSelectControl('hide_forest_override',['inherit','true','false'],'inherit')}
      ${bdTableSelect('terrain','origin',b.defaults.origin)}${bdSelectControl('terrain_specialty',['','scrub','sand','forest','snow'],'')}
      ${bdCheck('unit_tag_desert_raider')}${bdCheck('unit_tag_forest_ambusher')}
      ${bdCheck('bible_formation_auto')}${['f_cs','f_cf','f_ls','f_lf','f_ranks'].map(bdNumber).join('')}${bdText('f_types')}
      <p class="count">${tt('builder.attribute_help')}</p></fieldset>
    <details><summary>${tt('builder.overrides')}</summary>
      ${['cost_construct','cost_upkeep','cost_custom','soldier_count','armour','arm_agi','arm_heat','core_defense_skill','morale_baseline','weapon_upgrade_level','armour_upgrade_level'].map(bdNumber).join('')}
    </details>
    <details><summary>${tt('builder.edit_presets')}</summary>
      <label>${tt('builder.preset_family')}<select id="bd_family" onchange="bdFamily(this.value)">${Object.keys(BD_FAMILIES).map(f=>`<option value="${f}"${f===b.family?' selected':''}>${esc(bdLabel(f))}</option>`).join('')}</select></label>
      <label>${tt('builder.filter_presets')}<input id="bd_filter" value="${esc(b.filter)}" oninput="bdFilter(this.value)"></label>
      <select id="bd_edit_id" onchange="bdEditId(this.value)">${bdEditOptions()}</select>
      <div id="bdPresetFields">${bdPresetFields()}</div>
    </details>${pins}`;
}
function bdEligible(slot,id){
  const b=bdCurrent(),p={...(b.tables[slot][id]||{}),...(b.design.presets[slot]?.[id]||{})};
  const role=bdValue('category','infantry')==='cavalry'?'cav':['missile','skirmish'].includes(bdValue('class','heavy'))?bdValue('class'):'inf';
  return (p.roles||[]).some(r=>r==='any'||r===role||slot==='pri'&&role==='skirmish'&&r==='missile'||slot==='sec'&&['missile','skirmish'].includes(role)&&r==='inf');
}
function bdPresetOptions(slot){
  const b=bdCurrent(),keys=[...new Set([...Object.keys(b.tables[slot]),...Object.keys(b.design.presets[slot]||{})])];
  return keys.map(id=>`<option value="${esc(id)}"${bdValue(slot+'_preset',slot==='pri'?'arming_sword':'none')===id?' selected':''}${!bdEligible(slot,id)?' disabled':''}>${esc(bdLabel(id))}</option>`).join('');
}
function bdEligibilityPaint(){
  const b=bdCurrent(),el=document.getElementById('bdEligibility');if(!el||!b.design)return;
  const issues=[];
  if(b.design.profile.id!=='native'){
    for(const slot of ['pri','sec'])if(!bdEligible(slot,bdValue(slot+'_preset',slot==='pri'?'arming_sword':'none')))issues.push(tt('builder.role_ineligible',{slot:bdLabel(slot)}));
    if(bdValue('trait_mounted',false)&&bdValue('category')==='cavalry')issues.push(tt('builder.mounted_ineligible'));
    if(bdValue('trait_engineer',false)&&bdValue('category')!=='siege')issues.push(tt('builder.engineer_ineligible'));
    if(bdValue('trait_hybrid',false))issues.push(tt('builder.hybrid_help'));
    if(bdValue('unit_category')==='Royal Retinue')issues.push(tt('builder.royal_help'));
  }
  el.innerHTML=issues.map(s=>`<p>${esc(s)}</p>`).join('');
}
function bdSelect(key,value){
  if(key==='hide_forest_override'){
    if(value==='inherit'){delete bdCurrent().design.inputs[key];delete bdCurrent().design.overrides.inputs[key];}
    else bdCurrent().design.overrides.inputs[key]=value==='true';
  }else if(key.endsWith('_category')&&value===''){
    delete bdCurrent().design.inputs[key];delete bdCurrent().design.overrides.inputs[key];
  }else if(Object.hasOwn(bdCurrent().design.overrides.inputs,key))bdCurrent().design.overrides.inputs[key]=value;
  else bdCurrent().design.inputs[key]=value;
  bdRender();bdCalculate();
}
function bdInput(key,value,boolean=false){
  bdCurrent().design.overrides.inputs[key]=boolean?!!value:value;
  bdEligibilityPaint();bdCalculate();
}
function bdInherit(key){delete bdCurrent().design.overrides.inputs[key];bdRender();bdCalculate();}
function bdPin(key,value){
  const pins=bdCurrent().design.overrides.native;
  if(value==='')delete pins[key];else pins[key]=Number(value);
  bdCalculate();
}
function bdFamily(family){bdCurrent().family=family;bdCurrent().editId='';bdRender();}
function bdEditKey(){
  const b=bdCurrent(),ids=bdEditIds();
  return [b.editId,bdValue(BD_FAMILIES[b.family]),ids[0]].find(id=>ids.includes(id))||'';
}
function bdEditIds(){const b=bdCurrent();return bdTableIds(b.family).filter(id=>bdLabel(id).toLowerCase().includes(b.filter.toLowerCase()));}
function bdEditOptions(){
  return bdEditIds()
    .map(id=>`<option value="${esc(id)}"${id===bdEditKey()?' selected':''}>${esc(bdLabel(id))}</option>`).join('');
}
function bdFilter(value){
  const b=bdCurrent();b.filter=value;
  const el=document.getElementById('bd_edit_id');if(el)el.innerHTML=bdEditOptions();
  const fields=document.getElementById('bdPresetFields');if(fields)fields.innerHTML=bdPresetFields();
}
function bdEditId(id){bdCurrent().editId=id;const el=document.getElementById('bdPresetFields');if(el)el.innerHTML=bdPresetFields();}
function bdPresetFields(){
  const b=bdCurrent(),f=b.family,id=bdEditKey(),custom=b.design.presets[f]?.[id]||{};
  const baseline=b.tables[f][id]||Object.fromEntries(Object.keys(Object.values(b.tables[f])[0]||{}).filter(k=>Object.hasOwn(custom,k)).map(k=>[k,custom[k]]));
  // Edit only the profile's known properties. Dormant snapshot keys stay data.
  if(!id)return `<p>${tt('builder.no_presets')}</p>`;
  if(Array.isArray(baseline))return `<p>${esc(bdLabel(id))}</p><p>${tt('builder.loadout_help')}</p>`;
  const row=Object.fromEntries(Object.keys(baseline).map(k=>[k,b.design.presets[f]?.[id]?.[k]??baseline[k]]));
  return `<p>${esc(bdLabel(id))}</p>${Object.entries(row).map(([k,v])=>{
    const control=typeof v==='boolean'
      ?`<input id="bd_preset_${k}" type="checkbox"${v?' checked':''} onchange="bdPresetEdit('${f}','${k}',this.checked)">`
      :`<input id="bd_preset_${k}" value="${esc(Array.isArray(v)?v.join(', '):v??'')}" oninput="bdPresetEdit('${f}','${k}',this.value)">`;
    return `<label class="gfrow">${esc(bdLabel(k))}${control}</label>`;
  }).join('')}
    <button onclick="bdPresetReset('${f}')">${tt('builder.reset_preset')}</button><p class="count">${tt('builder.reset_help')}</p>`;
}
function bdPresetEdit(family,key,value){
  const b=bdCurrent(),id=bdEditKey(),original=b.tables[family][id][key];
  if(Array.isArray(original))value=String(value).split(',').map(x=>typeof original[0]==='number'?Number(x.trim()):x.trim()).filter(x=>x!=='');
  const f=b.design.presets[family]||(b.design.presets[family]={});
  (f[id]||(f[id]={}))[key]=value;
  bdEligibilityPaint();bdCalculate();
}
function bdPresetReset(family){const b=bdCurrent();if(b.design.presets[family])delete b.design.presets[family][bdEditKey()];bdRender();bdCalculate();}
async function bdCalculate(){
  const b=bdCurrent(),seq=++b.seq;
  b.result=null;b.error='';bdResultsPaint();bdStatus();
  try{
    const r=await api.post('/api/builder/preview',{mod:b.mod,unit:b.unit,design:b.design});
    if(b!==bdCurrent()||seq!==b.seq||!b.active)return;
    if(r.error)throw r;
    b.result=r;
  }catch(e){if(b!==bdCurrent()||seq!==b.seq||!b.active)return;b.error=tt('builder.invalid');}
  bdResultsPaint();bdStatus();
}
function bdResultsPaint(){
  const b=bdCurrent(),el=document.getElementById('bdResults');if(!el)return;
  const r=b.result;if(!r){el.innerHTML=b.error?`<p class="w-bad">${esc(b.error)}</p>`:`<p>${tt('common.reading')}</p>`;return;}
  const rules=r.metadata.engine_rules;
  el.innerHTML=`<h3>${tt('builder.calculated')}</h3><table>${Object.entries(r.native).map(([k,v])=>`<tr><th>${esc(bdLabel(k))}</th><td>${esc(Array.isArray(v)?v.join(', '):v)}</td></tr>`).join('')}</table>
    <details><summary>${tt('builder.contributions')}</summary>${Object.entries(r.explanations).map(([k,e])=>`<p><b>${esc(bdLabel(k))}</b></p><ul>${Object.entries(e.terms).map(([term,v])=>`<li>${esc(bdLabel(term))}: ${esc(typeof v==='object'?JSON.stringify(v):v)}</li>`).join('')}</ul>
    ${Object.hasOwn(e,'native_pin')?`<p>${tt('builder.pinned_result',{value:esc(e.result),before:esc(e.before_pin)})}</p>`:''}`).join('')}</details>
    <details open><summary>${tt('builder.upgrades')}</summary>
      ${rules.notes.map(n=>`<p>${esc(tt(n.id,n.params))}</p>`).join('')}
      <p>${esc(JSON.stringify(r.metadata.upgrade_preview))}</p>
      ${['weapon_upgrade_attack','armour_upgrade_armour'].map(k=>`<p>${esc(bdLabel(k))}: ${esc(rules[k].value)} (${esc(rules[k].source)})</p>`).join('')}</details>
    <details><summary>${tt('builder.design_metadata')}</summary><p>${tt('builder.attribute_help')}</p><pre>${esc(JSON.stringify(r.metadata,null,2))}</pre></details>
    <details open><summary>${tt('builder.edu_view')}</summary><p class="count">${tt('builder.edu_help')}</p><pre>${esc(r.edu)}</pre></details>`;
}
function bdStatus(){
  const b=bdCurrent(),el=document.getElementById('bdStatus');if(!el)return;
  el.textContent=b.error|| (b.saved===JSON.stringify(b.design)?tt('builder.saved'):tt('builder.unsaved'));
}
async function bdSave(){
  const b=bdCurrent();if(b.saving)return;b.saving=true;
  const design=JSON.parse(JSON.stringify(b.design));
  try{
    const r=await api.post('/api/builder/save',{mod:b.mod,unit:b.unit,design,revision:b.revision,source_token:b.source_token});
    if(b!==bdCurrent())return;
    if(r.error)throw r;
    b.revision=r.revision;b.source_token=r.source_token;b.saved=JSON.stringify(design);b.error='';
  }catch(e){if(b===bdCurrent())b.error=tt('builder.save_failed');}
  finally{b.saving=false;if(b===bdCurrent())bdStatus();}
}

function bdPortableError(error,fallback){
  return tt(['builder.project_version','builder.project_schema'].includes(error?.message_id)?error.message_id:fallback);
}
function bdImportSnapshot(b){return JSON.stringify([b.design,b.filter,b.family,b.editId]);}
async function bdImportFile(input){
  const file=input.files?.[0];if(!file)return;
  const b=bdCurrent(),before=bdImportSnapshot(b),seq=b.fileSeq=(b.fileSeq||0)+1;
  try{
    if(file.size>1000000)throw Error('size');
    const text=await file.text();
    if(b!==bdCurrent()||!b.active||seq!==b.fileSeq)return;
    if(bdImportSnapshot(b)!==before){b.error=tt('builder.import_changed');bdStatus();return;}
    await bdImportText(text);
  }catch(e){if(b===bdCurrent()){b.error=tt('builder.import_failed');bdStatus();}}
  finally{input.value='';}
}
async function bdImportText(text){
  const b=bdCurrent(),before=bdImportSnapshot(b),seq=b.importSeq=(b.importSeq||0)+1;
  try{
    const r=await api.post('/api/builder/import',{mod:b.mod,unit:b.unit,text,design:b.design});
    if(b!==bdCurrent()||!b.active||seq!==b.importSeq)return;
    if(bdImportSnapshot(b)!==before){b.error=tt('builder.import_changed');bdStatus();return;}
    if(r.error)throw r;
    b.design=r.design;b.result=null;b.error='';++b.seq;
    bdRender();undoCapture('');bdCalculate();
  }catch(e){if(b===bdCurrent()&&b.active&&seq===b.importSeq){b.error=bdPortableError(e,'builder.import_failed');bdStatus();}}
}
async function bdExport(format,copy){
  const b=bdCurrent(),before=JSON.stringify(b.design);
  try{
    const r=await api.post('/api/builder/export',{mod:b.mod,unit:b.unit,design:JSON.parse(before),format});
    if(b!==bdCurrent()||!b.active)return;
    if(JSON.stringify(b.design)!==before){b.error=tt('builder.import_changed');bdStatus();return;}
    if(r.error)throw r;
    if(copy)await navigator.clipboard.writeText(r.text);
    else{
      const url=URL.createObjectURL(new Blob([r.text],{type:r.mime})),a=document.createElement('a');
      a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
    b.error='';bdStatus();
  }catch(e){if(b===bdCurrent()&&b.active){b.error=bdPortableError(e,'builder.export_failed');bdStatus();}}
}

function bdLabels(){
  return {
    "Africa":tt('builder.label_africa'),
    "Anatolia":tt('builder.label_anatolia'),
    "Average":tt('builder.label_average'),
    "Byzantine":tt('builder.label_byzantine'),
    "Career Soldiers":tt('builder.label_career_soldiers'),
    "Cuman/Mongol":tt('builder.label_cuman_mongol'),
    "Eastern European":tt('builder.label_eastern_european'),
    "Emergency Levies":tt('builder.label_emergency_levies'),
    "Exceptional":tt('builder.label_exceptional'),
    "Household Soldiers":tt('builder.label_household_soldiers'),
    "Iberia":tt('builder.label_iberia'),
    "Inferior":tt('builder.label_inferior'),
    "Ireland/Highlands":tt('builder.label_ireland_highlands'),
    "Italian":tt('builder.label_italian'),
    "Martial Nobility":tt('builder.label_martial_nobility'),
    "Middle East/Persia":tt('builder.label_middle_east_persia'),
    "Outstanding":tt('builder.label_outstanding'),
    "Royal Retinue":tt('builder.label_royal_retinue'),
    "Rural Militia":tt('builder.label_rural_militia'),
    "Scandinavian":tt('builder.label_scandinavian'),
    "Superior":tt('builder.label_superior'),
    "Urban Militia":tt('builder.label_urban_militia'),
    "Wales":tt('builder.label_wales'),
    "Warrior Levies":tt('builder.label_warrior_levies'),
    "Western European":tt('builder.label_western_european'),
    "aggressive":tt('builder.label_aggressive'),
    "agi":tt('builder.label_agi'),
    "ammo":tt('builder.label_ammo'),
    "anatolia":tt('builder.label_anatolia'),
    "applicable":tt('builder.label_applicable'),
    "arbalest":tt('builder.label_arbalest'),
    "archetype":tt('builder.label_archetype'),
    "archetype_training":tt('builder.label_archetype_training'),
    "archetypes":tt('builder.label_archetypes'),
    "arm":tt('builder.label_arm'),
    "arm_agi":tt('builder.label_arm_agi'),
    "arm_heat":tt('builder.label_arm_heat'),
    "arming_doublet":tt('builder.label_arming_doublet'),
    "arming_sword":tt('builder.label_arming_sword'),
    "armor":tt('builder.label_armor'),
    "armor_upgrade_cost":tt('builder.label_armor_upgrade_cost'),
    "armour_preset":tt('builder.label_armour_preset'),
    "armour":tt('builder.label_armour'),
    "armourBonus":tt('builder.label_armourbonus'),
    "armour_base":tt('builder.label_armour_base'),
    "armour_layer1":tt('builder.label_armour_layer1'),
    "armour_layer2":tt('builder.label_armour_layer2'),
    "armour_layer3":tt('builder.label_armour_layer3'),
    "armour_sound":tt('builder.label_armour_sound'),
    "armour_upgrade_armour":tt('builder.label_armour_upgrade_armour'),
    "armour_upgrade_level":tt('builder.label_armour_upgrade_level'),
    "armour_upgrade_points":tt('builder.label_armour_upgrade_points'),
    "armour_weight":tt('builder.label_armour_weight'),
    "artisan":tt('builder.label_artisan'),
    "atk":tt('builder.label_atk'),
    "atk_tr":tt('builder.label_atk_tr'),
    "attack":tt('builder.label_attack'),
    "attack_delay":tt('builder.label_attack_delay'),
    "attr":tt('builder.label_attr'),
    "attributes":tt('builder.label_attributes'),
    "attrs":tt('builder.label_attrs'),
    "automatic":tt('builder.label_automatic'),
    "axe":tt('builder.label_axe'),
    "back_strapped":tt('builder.label_back_strapped'),
    "barding":tt('builder.label_barding'),
    "base":tt('builder.label_base'),
    "baseline":tt('builder.label_baseline'),
    "bible_formation_auto":tt('builder.label_bible_formation_auto'),
    "bill":tt('builder.label_bill'),
    "bonus":tt('builder.label_bonus'),
    "bow":tt('builder.label_bow'),
    "brawler":tt('builder.label_brawler'),
    "breast_plate":tt('builder.label_breast_plate'),
    "breed":tt('builder.label_breed'),
    "brigandine":tt('builder.label_brigandine'),
    "brigandine_late":tt('builder.label_brigandine_late'),
    "buckler":tt('builder.label_buckler'),
    "camel":tt('builder.label_camel'),
    "can_sap":tt('builder.label_can_sap'),
    "cataphract":tt('builder.label_cataphract'),
    "category":tt('builder.label_category'),
    "cav_style":tt('builder.label_cav_style'),
    "cavalry":tt('builder.label_cavalry'),
    "cavalry_style":tt('builder.label_cavalry_style'),
    "cdist":tt('builder.label_cdist'),
    "chain":tt('builder.label_chain'),
    "charge":tt('builder.label_charge'),
    "charge_mounted":tt('builder.label_charge_mounted'),
    "charger":tt('builder.label_charger'),
    "class":tt('builder.label_class'),
    "climate":tt('builder.label_climate'),
    "close_front":tt('builder.label_close_front'),
    "close_side":tt('builder.label_close_side'),
    "coat_cloth":tt('builder.label_coat_cloth'),
    "coat_of_plates":tt('builder.label_coat_of_plates'),
    "common":tt('builder.label_common'),
    "composite_bow":tt('builder.label_composite_bow'),
    "core":tt('builder.label_core'),
    "core_defense_skill":tt('builder.label_core_defense_skill'),
    "cost_construct":tt('builder.label_cost_construct'),
    "cost_custom":tt('builder.label_cost_custom'),
    "cost_upkeep":tt('builder.label_cost_upkeep'),
    "couched_lance":tt('builder.label_couched_lance'),
    "courser":tt('builder.label_courser'),
    "crossbow":tt('builder.label_crossbow'),
    "culture":tt('builder.label_culture'),
    "custom_cost":tt('builder.label_custom_cost'),
    "custom_limit":tt('builder.label_custom_limit'),
    "custom_stacking":tt('builder.label_custom_stacking'),
    "dagger":tt('builder.label_dagger'),
    "def":tt('builder.label_def'),
    "def_tr":tt('builder.label_def_tr'),
    "default":tt('builder.label_default'),
    "defense":tt('builder.label_defense'),
    "delay":tt('builder.label_delay'),
    "delay_mounted":tt('builder.label_delay_mounted'),
    "destrier":tt('builder.label_destrier'),
    "discipline":tt('builder.label_discipline'),
    "dmg":tt('builder.label_dmg'),
    "double_mail":tt('builder.label_double_mail'),
    "eastern_europe":tt('builder.label_eastern_europe'),
    "elephant":tt('builder.label_elephant'),
    "empty":tt('builder.label_empty'),
    "engine_rules":tt('builder.label_engine_rules'),
    "equipment_grade":tt('builder.label_equipment_grade'),
    "estoc":tt('builder.label_estoc'),
    "extra_attrs":tt('builder.label_extra_attrs'),
    "f_cf":tt('builder.label_f_cf'),
    "f_cs":tt('builder.label_f_cs'),
    "f_lf":tt('builder.label_f_lf'),
    "f_ls":tt('builder.label_f_ls'),
    "f_ranks":tt('builder.label_f_ranks'),
    "f_types":tt('builder.label_f_types'),
    "falchion":tt('builder.label_falchion'),
    "false":tt('builder.label_false'),
    "fanatic":tt('builder.label_fanatic'),
    "fighting_spear":tt('builder.label_fighting_spear'),
    "firearm":tt('builder.label_firearm'),
    "floor":tt('builder.label_floor'),
    "foot_quality":tt('builder.label_foot_quality'),
    "foot_spear":tt('builder.label_foot_spear'),
    "forest":tt('builder.label_forest'),
    "formation":tt('builder.label_formation'),
    "formation_types":tt('builder.label_formation_types'),
    "full_plate":tt('builder.label_full_plate'),
    "gaelic":tt('builder.label_gaelic'),
    "gambeson":tt('builder.label_gambeson'),
    "glaive":tt('builder.label_glaive'),
    "gothic_plate":tt('builder.label_gothic_plate'),
    "grade":tt('builder.label_grade'),
    "grade_multiplier":tt('builder.label_grade_multiplier'),
    "grades":tt('builder.label_grades'),
    "great_sword":tt('builder.label_great_sword'),
    "greatsword":tt('builder.label_greatsword'),
    "guards":tt('builder.label_guards'),
    "halberd":tt('builder.label_halberd'),
    "half_mail":tt('builder.label_half_mail'),
    "half_plate":tt('builder.label_half_plate'),
    "handling":tt('builder.label_handling'),
    "heat":tt('builder.label_heat'),
    "heat_mounted":tt('builder.label_heat_mounted'),
    "heater":tt('builder.label_heater'),
    "heavy":tt('builder.label_heavy'),
    "heavy_couched_lance":tt('builder.label_heavy_couched_lance'),
    "heavy_lamellar":tt('builder.label_heavy_lamellar'),
    "heavy_scale":tt('builder.label_heavy_scale'),
    "height":tt('builder.label_height'),
    "held":tt('builder.label_held'),
    "hide_forest_override":tt('builder.label_hide_forest_override'),
    "high":tt('builder.label_high'),
    "hobby":tt('builder.label_hobby'),
    "horse":tt('builder.label_horse'),
    "horse_barding":tt('builder.label_horse_barding'),
    "horse_origin":tt('builder.label_horse_origin'),
    "horse_type":tt('builder.label_horse_type'),
    "horseman_axe":tt('builder.label_horseman_axe'),
    "horseman_mace":tt('builder.label_horseman_mace'),
    "horseman_sword":tt('builder.label_horseman_sword'),
    "hybrid":tt('builder.label_hybrid'),
    "hybrid_divisor":tt('builder.label_hybrid_divisor'),
    "hybrid_rounded":tt('builder.label_hybrid_rounded'),
    "iberian":tt('builder.label_iberian'),
    "id":tt('builder.label_id'),
    "infantry":tt('builder.label_infantry'),
    "inherit":tt('builder.label_inherit'),
    "input":tt('builder.label_input'),
    "italian_plate":tt('builder.label_italian_plate'),
    "javelin":tt('builder.label_javelin'),
    "kataphract":tt('builder.label_kataphract'),
    "kite":tt('builder.label_kite'),
    "knife":tt('builder.label_knife'),
    "lamellar":tt('builder.label_lamellar'),
    "lamellar_light":tt('builder.label_lamellar_light'),
    "lamellar_med":tt('builder.label_lamellar_med'),
    "lance":tt('builder.label_lance'),
    "lancer":tt('builder.label_lancer'),
    "large":tt('builder.label_large'),
    "late_full_plate":tt('builder.label_late_full_plate'),
    "layers":tt('builder.label_layers'),
    "leather":tt('builder.label_leather'),
    "leather_jerkin":tt('builder.label_leather_jerkin'),
    "legacy":tt('builder.label_legacy'),
    "leine_croine":tt('builder.label_leine_croine'),
    "light":tt('builder.label_light'),
    "light_couched_lance":tt('builder.label_light_couched_lance'),
    "light_crossbow":tt('builder.label_light_crossbow'),
    "loadouts":tt('builder.label_loadouts'),
    "lock_morale":tt('builder.label_lock_morale'),
    "long_axe":tt('builder.label_long_axe'),
    "long_bow":tt('builder.label_long_bow'),
    "long_sword":tt('builder.label_long_sword'),
    "longaxe":tt('builder.label_longaxe'),
    "longsword":tt('builder.label_longsword'),
    "loose_front":tt('builder.label_loose_front'),
    "loose_side":tt('builder.label_loose_side'),
    "mace":tt('builder.label_mace'),
    "mail_haubergon":tt('builder.label_mail_haubergon'),
    "mail_lamellar":tt('builder.label_mail_lamellar'),
    "mail_light":tt('builder.label_mail_light'),
    "mail_med":tt('builder.label_mail_med'),
    "mail_surcoat":tt('builder.label_mail_surcoat'),
    "mail_voiders":tt('builder.label_mail_voiders'),
    "mass":tt('builder.label_mass'),
    "medium":tt('builder.label_medium'),
    "metal":tt('builder.label_metal'),
    "middle_east":tt('builder.label_middle_east'),
    "missile":tt('builder.label_missile'),
    "mongol":tt('builder.label_mongol'),
    "moor":tt('builder.label_moor'),
    "morale":tt('builder.label_morale'),
    "morale_baseline":tt('builder.label_morale_baseline'),
    "mount":tt('builder.label_mount'),
    "mountClass":tt('builder.label_mountclass'),
    "mount_effect":tt('builder.label_mount_effect'),
    "mountedAtkPenalty":tt('builder.label_mountedatkpenalty'),
    "mounted_crossbow":tt('builder.label_mounted_crossbow'),
    "mounted_heavy_recurve_bow":tt('builder.label_mounted_heavy_recurve_bow'),
    "mounted_javelin":tt('builder.label_mounted_javelin'),
    "mounted_quality":tt('builder.label_mounted_quality'),
    "mounted_recurve_bow":tt('builder.label_mounted_recurve_bow'),
    "mounted_short_bow":tt('builder.label_mounted_short_bow'),
    "mounted_spear":tt('builder.label_mounted_spear'),
    "movement":tt('builder.label_movement'),
    "munition":tt('builder.label_munition'),
    "name":tt('builder.label_name'),
    "noMount":tt('builder.label_nomount'),
    "none":tt('builder.label_none'),
    "offhand":tt('builder.label_offhand'),
    "offhands":tt('builder.label_offhands'),
    "origin":tt('builder.label_origin'),
    "origin_weight":tt('builder.label_origin_weight'),
    "override":tt('builder.label_override'),
    "padded":tt('builder.label_padded'),
    "params":tt('builder.label_params'),
    "pavise":tt('builder.label_pavise'),
    "pick":tt('builder.label_pick'),
    "pike":tt('builder.label_pike'),
    "plate":tt('builder.label_plate'),
    "plate_lamellar":tt('builder.label_plate_lamellar'),
    "pole_axe":tt('builder.label_pole_axe'),
    "poleaxe":tt('builder.label_poleaxe'),
    "pony":tt('builder.label_pony'),
    "poor":tt('builder.label_poor'),
    "pre_grade":tt('builder.label_pre_grade'),
    "pri":tt('builder.label_pri'),
    "pri_ammo":tt('builder.label_pri_ammo'),
    "pri_attr":tt('builder.label_pri_attr'),
    "pri_attributes":tt('builder.label_pri_attributes'),
    "pri_base_atk":tt('builder.label_pri_base_atk'),
    "pri_base_charge":tt('builder.label_pri_base_charge'),
    "pri_category":tt('builder.label_pri_category'),
    "pri_delay":tt('builder.label_pri_delay'),
    "pri_handling":tt('builder.label_pri_handling'),
    "pri_heat":tt('builder.label_pri_heat'),
    "pri_missile":tt('builder.label_pri_missile'),
    "pri_preset":tt('builder.label_pri_preset'),
    "pri_range":tt('builder.label_pri_range'),
    "pri_twohand":tt('builder.label_pri_twohand'),
    "primary":tt('builder.label_primary'),
    "profile":tt('builder.label_profile'),
    "projectile_accuracy":tt('builder.label_projectile_accuracy'),
    "puffed_cloth":tt('builder.label_puffed_cloth'),
    "quality":tt('builder.label_quality'),
    "radius":tt('builder.label_radius'),
    "range":tt('builder.label_range'),
    "ranks":tt('builder.label_ranks'),
    "reckless":tt('builder.label_reckless'),
    "recruit":tt('builder.label_recruit'),
    "recruit_cost":tt('builder.label_recruit_cost'),
    "recruit_priority":tt('builder.label_recruit_priority'),
    "recruit_turns":tt('builder.label_recruit_turns'),
    "reinforced":tt('builder.label_reinforced'),
    "reinforcing":tt('builder.label_reinforcing'),
    "ren_3q_plate":tt('builder.label_ren_3q_plate'),
    "ren_half_plate":tt('builder.label_ren_half_plate'),
    "result":tt('builder.label_result'),
    "roles":tt('builder.label_roles'),
    "rouncy":tt('builder.label_rouncy'),
    "round":tt('builder.label_round'),
    "sand":tt('builder.label_sand'),
    "scale_light":tt('builder.label_scale_light'),
    "scale_med":tt('builder.label_scale_med'),
    "scandinavia":tt('builder.label_scandinavia'),
    "scrub":tt('builder.label_scrub'),
    "sec":tt('builder.label_sec'),
    "sec_ammo":tt('builder.label_sec_ammo'),
    "sec_attack":tt('builder.label_sec_attack'),
    "sec_attr":tt('builder.label_sec_attr'),
    "sec_attributes":tt('builder.label_sec_attributes'),
    "sec_base_atk":tt('builder.label_sec_base_atk'),
    "sec_base_charge":tt('builder.label_sec_base_charge'),
    "sec_category":tt('builder.label_sec_category'),
    "sec_charge":tt('builder.label_sec_charge'),
    "sec_delay":tt('builder.label_sec_delay'),
    "sec_handling":tt('builder.label_sec_handling'),
    "sec_heat":tt('builder.label_sec_heat'),
    "sec_missile":tt('builder.label_sec_missile'),
    "sec_preset":tt('builder.label_sec_preset'),
    "sec_range":tt('builder.label_sec_range'),
    "sec_twohand":tt('builder.label_sec_twohand'),
    "secondary":tt('builder.label_secondary'),
    "selection":tt('builder.label_selection'),
    "self_bow":tt('builder.label_self_bow'),
    "shield":tt('builder.label_shield'),
    "shield_mat":tt('builder.label_shield_mat'),
    "shield_material":tt('builder.label_shield_material'),
    "shield_type":tt('builder.label_shield_type'),
    "short_sword":tt('builder.label_short_sword'),
    "siege":tt('builder.label_siege'),
    "size_cav":tt('builder.label_size_cav'),
    "size_inf":tt('builder.label_size_inf'),
    "skirmish":tt('builder.label_skirmish'),
    "small":tt('builder.label_small'),
    "snow":tt('builder.label_snow'),
    "soldier_count":tt('builder.label_soldier_count'),
    "soldier_quality":tt('builder.label_soldier_quality'),
    "sound":tt('builder.label_sound'),
    "source":tt('builder.label_source'),
    "spear":tt('builder.label_spear'),
    "spearmen":tt('builder.label_spearmen'),
    "specialty":tt('builder.label_specialty'),
    "speed":tt('builder.label_speed'),
    "staff":tt('builder.label_staff'),
    "stallion":tt('builder.label_stallion'),
    "stamina":tt('builder.label_stamina'),
    "stat":tt('builder.label_stat'),
    "status":tt('builder.label_status'),
    "subtype":tt('builder.label_subtype'),
    "subtypes":tt('builder.label_subtypes'),
    "surcoat":tt('builder.label_surcoat'),
    "sword_cut":tt('builder.label_sword_cut'),
    "sword_thrust":tt('builder.label_sword_thrust'),
    "tech":tt('builder.label_tech'),
    "terms":tt('builder.label_terms'),
    "terrain":tt('builder.label_terrain'),
    "terrain_choice":tt('builder.label_terrain_choice'),
    "terrain_heavy":tt('builder.label_terrain_heavy'),
    "terrain_light":tt('builder.label_terrain_light'),
    "terrain_med":tt('builder.label_terrain_med'),
    "terrain_specialty":tt('builder.label_terrain_specialty'),
    "third_layer":tt('builder.label_third_layer'),
    "thrown":tt('builder.label_thrown'),
    "training":tt('builder.label_training'),
    "trait_aggressive":tt('builder.label_trait_aggressive'),
    "trait_bloc":tt('builder.label_trait_bloc'),
    "trait_command":tt('builder.label_trait_command'),
    "trait_engineer":tt('builder.label_trait_engineer'),
    "trait_fanatic":tt('builder.label_trait_fanatic'),
    "trait_garrison":tt('builder.label_trait_garrison'),
    "trait_guards":tt('builder.label_trait_guards'),
    "trait_hybrid":tt('builder.label_trait_hybrid'),
    "trait_mercenary":tt('builder.label_trait_mercenary'),
    "trait_mounted":tt('builder.label_trait_mounted'),
    "trait_raider":tt('builder.label_trait_raider'),
    "trait_reckless":tt('builder.label_trait_reckless'),
    "transitional":tt('builder.label_transitional'),
    "true":tt('builder.label_true'),
    "twohand":tt('builder.label_twohand'),
    "unarmored":tt('builder.label_unarmored'),
    "unit_category":tt('builder.label_unit_category'),
    "unit_custom_attrs":tt('builder.label_unit_custom_attrs'),
    "unit_size":tt('builder.label_unit_size'),
    "unit_tag_desert_raider":tt('builder.label_unit_tag_desert_raider'),
    "unit_tag_forest_ambusher":tt('builder.label_unit_tag_forest_ambusher'),
    "upkeep":tt('builder.label_upkeep'),
    "value":tt('builder.label_value'),
    "verified":tt('builder.label_verified'),
    "war_bow":tt('builder.label_war_bow'),
    "war_knife":tt('builder.label_war_knife'),
    "weapon":tt('builder.label_weapon'),
    "weapon_categories":tt('builder.label_weapon_categories'),
    "weapon_category":tt('builder.label_weapon_category'),
    "weapon_handling":tt('builder.label_weapon_handling'),
    "weapon_upgrade_attack":tt('builder.label_weapon_upgrade_attack'),
    "weapon_upgrade_cost":tt('builder.label_weapon_upgrade_cost'),
    "weapon_upgrade_level":tt('builder.label_weapon_upgrade_level'),
    "weapon_upgrade_points":tt('builder.label_weapon_upgrade_points'),
    "weight":tt('builder.label_weight'),
    "western_europe":tt('builder.label_western_europe'),
    "wooden":tt('builder.label_wooden'),
    "wtype":tt('builder.label_wtype')
  };
}
