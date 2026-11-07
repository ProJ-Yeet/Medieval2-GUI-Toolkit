/* Phase 101j. Read-only joins; edits use characters and map character plans. */
async function openFactionModels(faction){
  const k = state.cm = {mod:state.src, faction:faction||'', values:{}, people:{}, preview:null, busy:true, results:[]};
  const modal = document.getElementById('modal');
  modal.className = 'modal wide';
  modal.innerHTML = `<h2>${tt('charmodels.title')}</h2><div class="mbody">${tt('common.reading')}</div>`;
  overlay.classList.add('open');
  await cmLoad(k);
}
async function cmLoad(k){
  try{
    const d = await api.get(`/api/charmodels?mod=${enc(k.mod)}&faction=${enc(k.faction)}`);
    if(state.cm !== k) return;
    if(d.error) throw new Error(d.error);
    k.d = d; k.faction = d.faction || k.faction;
    k.values = {}; k.people = {}; k.preview = null;
  }catch(e){ k.error = errText(e); }
  if(state.cm !== k) return;
  k.busy = false; cmRender();
}
function cmPick(faction){ if(!state.cm.busy) openFactionModels(faction); }
function cmSetValue(line, value, was){
  const k=state.cm;
  if(k.busy) return;
  if(value.trim() === was) delete k.values[line]; else k.values[line] = value.trim();
  k.preview=null; k.results=[]; cmRender();
}
function cmSetCharacter(i, value){
  const k=state.cm;
  if(k.busy) return;
  if(value.trim() === k.d.characters[i].battle_model) delete k.people[i]; else k.people[i]=value.trim();
  k.preview=null; k.results=[]; cmRender();
}
// A level's traits come from the whole EDCT: DaC gives level 3 to 22 heroes of
// every faction, and no trait names a culture, so the first few are shown and
// the rest are on hover.
const CM_TRAITS_SHOWN=4;
function cmLevelHtml(slot){
  const all=slot.traits||[], more=all.length-CM_TRAITS_SHOWN;
  const names=all.length?(more>0?tt('charmodels.more',{names:esc(all.slice(0,CM_TRAITS_SHOWN).join(', ')),n:more}):esc(all.join(', ')))
    :(slot.level === 0 ? tt('charmodels.default') : tt('charmodels.no_trait'));
  return `${tt('charmodels.level',{level:slot.level})} <span class="count"${more>0?` title="${esc(all.join(', '))}"`:''}>${
    names}</span>${slot.comment ? ` <span class="count">; ${esc(slot.comment)}</span>` : ''}`;
}
function cmModelLink(name, battle){
  return name ? navLinkHtml({mode:battle?'bmdb':'stratmap',name},esc(name),'ulink') : '';
}
function cmBox(line, was, battle){
  const k=state.cm, value=k.values[line] === undefined ? was : k.values[line];
  return `<input list="${battle?'cmBattleNames':'cmStratNames'}" style="width:16em" value="${esc(value)}" ${k.busy?'disabled':''}
    onchange="cmSetValue(${line},this.value,'${q1(esc(was))}')"> ${cmModelLink(was,battle)}`;
}
function cmBlockHtml(block){
  const b=block.battle_model;
  return `<fieldset><legend>${esc(block.type)} ${tt('charmodels.line',{line:block.line})}</legend>
    <div class="count">${esc(block.factions.join(', '))}</div>
    <table class="smxtab">${block.slots.map(s=>`<tr><td>${cmLevelHtml(s)}</td><td>${cmBox(s.line,s.model,false)}</td></tr>`).join('')}
    ${b?`<tr><td><code>battle_model</code></td><td>${cmBox(b.line,b.value,true)}</td></tr>`:''}</table></fieldset>`;
}
function cmCharacterRoute(c){ return {mode:'campmap',name:c.name,line:c.line,campaign:c.campaign,faction:c.faction||state.cm.faction}; }
function cmRole(role){
  return {generals:tt('charmodels.role_generals'),captain:tt('charmodels.role_captain'),
    general:tt('charmodels.role_general'),leader:tt('charmodels.role_leader'),heir:tt('charmodels.role_heir')}[role]||esc(role);
}
function cmUsersHtml(users, horse){
  if(!users || !users.length) return '';
  return `<fieldset><legend>${tt('charmodels.characters')}</legend>
    ${horse?'':`<div class="w-warn">${tt('charmodels.horse')}</div>`}
    ${users.map(c=>{
      const route=c.source==='descr_character'?{mode:'characters',name:c.key}:
        c.source==='descr_strat'?cmCharacterRoute(c):{mode:'rawtext',rel:c.rel,line:c.line};
      return `<div>${navLinkHtml(route,esc(c.name||c.faction),'ulink')} <span class="count">${
        esc(c.type||'')} ${cmRole(c.role)} ${esc(c.campaign||c.rel||'')}
        ${c.commented?tt('charmodels.commented'):''}</span></div>`;
    }).join('')}</fieldset>`;
}
function cmRender(){
  const k=state.cm, d=k.d||{}, modal=document.getElementById('modal');
  const jobs=cmJobs(), ready=k.preview && k.preview.key===JSON.stringify(jobs) && k.preview.ok;
  modal.innerHTML=`<h2>${tt('charmodels.title')} <span class="pill">${esc(k.mod)}</span></h2>
    <div class="mbody">
      <label>${tt('common.faction_2')} <select onchange="cmPick(this.value)" ${k.busy?'disabled':''}>
        <option value="">${tt('charmodels.pick')}</option>${(d.roster||[]).map(f=>`<option value="${esc(f)}" ${f===k.faction?'selected':''}>${esc(f)}</option>`).join('')}</select></label>
      ${k.error?`<div class="w-bad">${esc(k.error)}</div>`:''}
      ${d.faction?`<p class="count">${tt('charmodels.help')}</p>
        ${(d.findings||[]).map(f=>`<div class="${f.severity==='warn'?'w-warn':'count'}">${tt('charmodels.line',{line:f.line})}: ${esc(f.message)}</div>`).join('')}
        ${(d.named||[]).concat(d.captain||[],d.agents||[]).map(cmBlockHtml).join('')}
        <fieldset><legend>${tt('charmodels.campaign_characters')}</legend>
          ${(d.characters||[]).map((c,i)=>`<div>${navLinkHtml(cmCharacterRoute(c),esc(c.name),'ulink')} <span class="count">${esc(c.campaign)} ${esc(c.rank)}</span>
            <input list="cmBattleNames" style="width:16em" value="${esc(k.people[i]===undefined?c.battle_model:k.people[i])}" ${k.busy?'disabled':''}
              onchange="cmSetCharacter(${i},this.value)"> ${cmModelLink(c.battle_model,true)}</div>`).join('')||tt('common.none')}
        </fieldset>
        <fieldset><legend>${tt('charmodels.scripts')}</legend>${(d.scripts||[]).map(s=>`<div>${
          navLinkHtml({mode:'rawtext',rel:s.rel,line:s.line},`${esc(s.rel)}:${s.line}`,'ulink')}
          <code>${esc(s.who)}</code> ${cmModelLink(s.model,true)} ${s.commented?tt('charmodels.commented'):''}</div>`).join('')||tt('common.none')}</fieldset>
        <fieldset><legend>${tt('charmodels.symbols')}</legend>${Object.entries(d.symbols||{}).map(([key,value])=>`<div><code>${esc(key)}</code> ${esc(value)}</div>`).join('')||tt('common.none')}</fieldset>
        <fieldset><legend>${tt('charmodels.textures')}</legend>${(d.strat_textures||[]).map(n=>cmModelLink(n,false)).join(', ')||tt('common.none')}</fieldset>
        <datalist id="cmStratNames">${(d.strat_models||[]).map(n=>`<option value="${esc(n)}"></option>`).join('')}</datalist>
        <datalist id="cmBattleNames">${(d.battle_models||[]).map(n=>`<option value="${esc(n)}"></option>`).join('')}</datalist>`:''}
      ${(k.results||[]).map(r=>`<fieldset><legend>${esc(r.label)}</legend>${(r.plan.changes||[]).map(s=>`<div>${esc(s)}</div>`).join('')}
        ${(r.plan.warnings||[]).map(s=>`<div class="w-warn">${esc(s)}</div>`).join('')}
        ${(r.plan.errors||[]).map(s=>`<div class="w-bad">${esc(s)}</div>`).join('')}</fieldset>`).join('')}
      ${k.notice?`<div class="count">${esc(k.notice)}</div>`:''}
    </div><div class="foot"><button onclick="closeModal()" ${k.busy?'disabled':''}>${tt('common.close')}</button>
      <button onclick="cmPreview()" ${k.busy||!jobs.length?'disabled':''}>${tt('common.probe')}</button>
      <button class="primary" onclick="cmApply()" ${k.busy||!ready?'disabled':''}>${tt('common.apply')}</button></div>`;
}
function cmJobs(){
  const k=state.cm, jobs=[];
  if(Object.keys(k.values).length) jobs.push({url:'/api/characters/',body:{mod:k.mod,sig:k.d.sig,values:{...k.values}},label:'descr_character.txt'});
  Object.entries(k.people).forEach(([i,value])=>{
    const c=k.d.characters[i];
    jobs.push({url:'/api/map/character_',body:{mod:k.mod,campaign:c.campaign,faction:k.faction,character:c.name,line:c.line,action:'edit',edits:{battle_model:value}},label:c.campaign+': '+c.name});
  });
  return jobs;
}
async function cmPreview(){
  const k=state.cm;
  if(k.busy) return;
  const jobs=cmJobs();
  if(!jobs.length) return;
  k.busy=true; k.error=''; k.preview=null; k.results=[]; k.notice=''; cmRender();
  let ok=true;
  try{
    for(const job of jobs){
      const r=await api.post(job.url+'plan',job.body), plan=r.plan||{errors:[r.error||tt('charmodels.failed')]};
      if(state.cm!==k) return;
      if(r.error || (plan.errors||[]).length || plan.ok===false) ok=false;
      if(r.error && !(plan.errors||[]).includes(r.error)) plan.errors=(plan.errors||[]).concat(r.error);
      k.results.push({label:job.label,plan});
    }
    k.preview={key:JSON.stringify(jobs),ok};
  }catch(e){ k.error=errText(e); }
  k.busy=false;
  if(state.cm===k) cmRender();
}
async function cmApply(){
  const k=state.cm, jobs=cmJobs();
  if(k.busy || !k.preview || !k.preview.ok || k.preview.key!==JSON.stringify(jobs)) return;
  k.busy=true; k.error=''; k.preview=null; cmRender();
  let applied=0, error='';
  try{
    for(const job of jobs){
      const r=await api.post(job.url+'apply',job.body);
      if(r.error || (r.plan&&r.plan.errors||[]).length || !r.record) throw new Error(r.error||(r.plan.errors||[]).join('; ')||tt('charmodels.failed'));
      applied++;
      if(state.cm!==k) return;
    }
  }catch(e){ error=errText(e); }
  if(applied){
    k.notice=tt('charmodels.applied',{count:applied});
    await cmLoad(k);
  }else{ k.busy=false; k.preview=null; }
  if(error) k.error=error;
  if(state.cm===k) cmRender();
}
async function cmMapCharacter(route){
  if(route.campaign) cmapSetCampaign(route.campaign);
  if(route.campaign && state.cmap.campaign!==route.campaign) return;
  const map=state.cmap, campaign=map.campaign;
  await cxOpen(route.faction);
  const k=state.cx;
  if(state.cmap!==map || map.campaign!==campaign || !k || !k.d || k.faction!==route.faction) return;
  k.open=true; k.tab='people';
  const i=k.d.characters.findIndex(c=>c.name===route.name && (!route.line || c.line===+route.line));
  if(i>=0) cxPick(i);
  cmapSurface('cmChars');
}
