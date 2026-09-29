/* packs.js - unit packs - units in a zip you can send someone

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   Unit packs - units in a zip you can send someone

   Export builds a miniature mod: the units' EDU blocks, their modeldb entries,
   the meshes, textures and icons those name, and whatever descr_* blocks they
   reach for. Import mounts that zip as an ordinary source mod and then gets out
   of the way: the source dropdown switches to it and every existing screen -
   the composer, the base picker, conflicts, preview, Save, the undo log - works
   on it unchanged. There is no separate "import" screen to keep in step with
   the transfer one, because the import IS a transfer.
   ========================================================================= */
const MBs=n=>(n/1048576).toFixed(1)+' MB';
async function packExport(types){
  if(!types.length)return toast(tt('packs.tick_some_units_first'));
  const modal=document.getElementById('modal');
  modal.className='modal';
  overlay.classList.add('open');
  modal.innerHTML=`<h2>${ttN('packs.export_units_as_a_pack',types.length)}</h2>
    <div class="mbody"><div class="empty">${tt('packs.working_out_what_has_to_travel')}</div></div>
    <div class="foot"><button onclick="closeModal()">${tt('common.cancel')}</button></div>`;
  let r;
  try{ r=await api.post('/api/pack/plan',{mod:state.src,units:types}); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.querySelector('.mbody').innerHTML=`<div class="w-bad">${esc(r.error)}</div>`; return; }
  state.pack={mod:state.src,types,plan:r};
  packExportRender();
}
function packExportRender(){
  const p=state.pack.plan;
  document.getElementById('modal').innerHTML=`<h2>${ttN('packs.export_units_as_a_pack',p.units.length)} <span class="pill">${esc(state.pack.mod)}</span></h2>
    <div class="mbody">
      <div class="sum">
        <div class="srow"><span class="sicon">•</span><span class="stext">
          ${p.units.map(t=>`<code>${esc(t)}</code>`).join(', ')}</span></div>
        <div class="srow"><span class="sicon">•</span><span class="stext">
          ${tt('packs.model_entries_files_icons',{models:ttN('packs.battle_model_entries',p.models.length),assets:ttN('packs.mesh_texture_files',p.assets),icons:ttN('packs.icons',p.icons)})}</span></div>
        ${p.mounts.length?`<div class="srow"><span class="sicon">•</span><span class="stext">
          ${ttN('packs.mounts_list',p.mounts.length,{list:p.mounts.map(m=>`<code>${esc(m)}</code>`).join(', ')})}</span></div>`:''}
        ${p.projectiles.length?`<div class="srow"><span class="sicon">•</span><span class="stext">
          ${ttN('packs.projectiles_list',p.projectiles.length,{list:p.projectiles.map(m=>`<code>${esc(m)}</code>`).join(', ')})}</span></div>`:''}
        ${p.engines.length?`<div class="srow"><span class="sicon">•</span><span class="stext">
          ${ttN('packs.engines_list',p.engines.length,{list:p.engines.map(m=>`<code>${esc(m)}</code>`).join(', ')})}</span></div>`:''}
        <div class="srow"><span class="sicon">→</span><span class="stext">
          ${tt('packs.about_of_art_before_compression',{x:MBs(p.bytes)})}</span></div>
        ${(p.missing||[]).map(t=>`<div class="srow bad"><span class="sicon">✕</span>
          <span class="stext">${tt('packs.is_not_in_this_mod',{x:esc(t)})}</span></div>`).join('')}
        ${(p.warnings||[]).map(w=>`<div class="srow warn"><span class="sicon">!</span>
          <span class="stext">${esc(w)}</span></div>`).join('')}
      </div>
      <div class="bnote">${tt('packs.the_zip_is_a_miniature_mod')}</div>
      <div id="packResult"></div>
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.cancel')}</button>
      <button class="primary" ${p.units.length?'':'disabled'} onclick="packWrite()">
        ${tt('packs.choose_where_to_save')}</button></div>`;
}
async function packWrite(){
  const p=state.pack;
  const name=(p.plan.units.length===1?p.plan.units[0]:`${p.mod}-${p.plan.units.length}-units`)
    .replace(/[^A-Za-z0-9_.-]+/g,'_')+'.zip';
  const pick=await api.post('/api/browse_save',
    {title:tt('packs.save_the_unit_pack'),filter:tt('packs.unit_pack_zip_zip_all_files'),
     name,ext:'zip'});
  if(!pick.path)return;                       // cancelled
  const box=document.getElementById('packResult');
  box.innerHTML=`<div class="count" style="padding:8px">${tt('packs.writing_the_pack')}</div>`;
  let r;
  try{ r=await api.post('/api/pack/write',{mod:p.mod,units:p.types,path:pick.path}); }
  catch(e){ r={error:''+e}; }
  if(r.error){ box.innerHTML=`<div class="mbody w-bad">${esc(r.error)}</div>`; return; }
  const rec=r.record;
  box.innerHTML=`<div class="sum" style="margin-top:10px">
    <div class="srow good"><span class="sicon">✓</span><span class="stext">
      ${tt('packs.wrote_file_s',{path:esc(rec.path),files:rec.files,x:MBs(rec.bytes)})}</span></div></div>`;
  toast(tt('packs.pack_written',{path:rec.path}),5000);
}

async function packImport(){
  const pick=await api.post('/api/browse_file',
    {title:tt('packs.open_a_unit_pack'),filter:tt('packs.unit_pack_zip_zip_all_files')});
  if(!pick.path)return;
  const modal=document.getElementById('modal');
  modal.className='modal';
  overlay.classList.add('open');
  modal.innerHTML=`<h2>${tt('packs.import_a_unit_pack')}</h2>
    <div class="mbody"><div class="empty">${tt('packs.opening_the_pack')}</div></div>
    <div class="foot"><button onclick="closeModal()">${tt('common.cancel')}</button></div>`;
  let r;
  try{ r=await api.post('/api/pack/open',{path:pick.path}); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.querySelector('.mbody').innerHTML=`<div class="w-bad">${esc(r.error)}</div>`; return; }
  state.packIn=r;
  packImportRender();
}
function packImportRender(){
  const r=state.packIn,m=r.manifest||{};
  document.getElementById('modal').innerHTML=`<h2>${tt('packs.import_a_unit_pack')}</h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:8px">
        <code>${esc(r.path)}</code> · ${MBs(r.bytes)}${
        m.source_mod?` ${tt('packs.made_from')} <b>${esc(m.source_mod)}</b>`:''}${
        m.created?` on ${esc(m.created)}`:''}</div>
      ${r.has_manifest?'':`<div class="warnbox">${tt('packs.this_zip_carries_no_unitpack_json')}</div>`}
      <div class="baselist" style="max-height:280px">${r.units.map(u=>`
        <div class="baserow">
          <div><div class="bn">${esc(u.name)}${u.has_card?'':` <span class="badge">${tt('packs.no_card')}</span>`}</div>
            <div class="bs">${esc(u.type)} · ${esc([u.kind,u.class].filter(Boolean).join(' · '))}${
              u.mount?` ${tt('packs.rides')} <code>${esc(u.mount)}</code>`:''}</div></div>
        </div>`).join('')||`<div class="caprow"><span class="count">${tt('packs.this_pack_names_no_units')}</span></div>`}</div>
      <div class="bnote">${tt('packs.battle_model_entr_travel_with_them',{entries_n:r.entries.length,x:r.entries.length===1?'y':'ies'})}</div>
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.cancel')}</button>
      <button class="primary" ${r.units.length?'':'disabled'} onclick="packMount()">
        ${ttN('packs.open_units_for_transfer',r.units.length)}</button></div>`;
}
async function packMount(){
  const r=state.packIn;
  let info;
  try{ info=await api.post('/api/pack/mount',{path:r.path}); }
  catch(e){ info={error:''+e}; }
  if(info.error)return toast(info.error,5000);
  closeModal();
  // From here it is an ordinary transfer: the pack is just another source mod.
  state.mode='transfer';
  await refreshMods(info.name,state.dst===info.name?null:state.dst);
  state.src=info.name; srcSel.value=info.name;
  applyMode(true);
  await loadSource();
  toast(tt('packs.pack_opened_pick_the_units',{name:info.name,dst:state.dst}),6000);
}

/* ---- clean-up: what nothing uses, and where to put it ---- */
async function openCleanup(){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  const job=newJob();
  let a;
  try{ a=await runJob(job,tt('packs.clean_up_s_bmdb',{src:esc(state.src)}),
        tt('packs.scanning_every_entry_every_unit_that'),
        ()=>api.get(`/api/bmdb/audit?mod=${enc(state.src)}&job=${enc(job)}`)); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>${tt('common.clean_up')}</h2><div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  // Re-opened straight after a cleanup (see clApply), the folder that was typed
  // in and the sections that were unfolded are still the ones being worked in -
  // only the LISTS are out of date, and it is those the fresh audit replaces.
  const was=(state.clean&&state.clean.a&&state.clean.a.mod===a.mod)?state.clean:null;
  state.clean={a,target:(was&&was.target)||state.settings.last_cleanup_target||'',
    entries:new Set(a.unused.map(u=>u.entry)),     // unused: pre-ticked, they are dead by definition
    merges:new Set(),                              // suggestions: never pre-ticked, they change a model
    into:Object.fromEntries(a.merges.map(m=>[m.entry,m.into])),
    orphans:new Set(a.orphans.map(o=>o.rel)),
    mounts:new Set(),                              // rewrites descr_mount.txt: opt in by hand
    open:(was&&was.open)||{unused:true,merges:true,mounts:false,orphans:false},
    plan:null};
  resetPlace();
  renderCleanup();
}
const MB=n=>(n/1048576).toFixed(1)+' MB';
function renderCleanup(){
  const c=state.clean,a=c.a;
  // The counts get their own node: ticking a row must not re-render the lists
  // (a big mod has 3000+ file rows and rebuilding them per click is unusable).
  const sec=(k,title,body)=>`<div class="clsec">
      <div class="h" onclick="clToggle('${k}')"><span>${c.open[k]?'▾':'▸'}</span>
        <b>${title}</b><span class="count" id="clc_${k}">${clCountText(k)}</span></div>
      ${c.open[k]?`<div class="b">${body()}</div>`:''}</div>`;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('packs.clean_up_s_battle_models_modeldb',{mod:esc(a.mod)})}</h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:10px">${tt('packs.entries_scanned_nothing_is_deleted_everything',{entry_count:a.entry_count})}</div>

      <fieldset><legend>${tt('packs.where_the_removed_assets_go')}</legend>
        <div class="cltarget">
          <input id="clTarget" value="${esc(c.target)}" placeholder="${ttA('packs.e_g_d_m2tw_backups_unused',{mod:esc(a.mod)})}"
            oninput="state.clean.target=this.value;clStale()">
          <button onclick="clPickTarget()">${tt('common.browse')}</button>
        </div>
        <div class="treebox">${tt('packs.unused_removed_battle_models_modeldb_only',{mod:esc(a.mod)})}</div>
        <div class="count" style="margin-top:6px">${tt('packs.must_be_outside_the_mod_or')}</div>
      </fieldset>

      ${sec('unused',tt('packs.entries_nothing_references'),()=>clUnusedBody())}
      ${sec('merges',tt('packs.soldier_only_entries_with_an_identical'),()=>clMergeBody())}
      ${sec('mounts',tt('packs.mounts_no_unit_rides'),()=>clMountBody())}
      ${sec('orphans',tt('packs.files_under_unit_models_no_entry'),()=>clOrphanBody())}

      ${clLuaBox(a)}
      ${a.mentioned.length?`<div class="count">${tt('packs.more_entr_used_by_no_unit',{mentioned_n:a.mentioned.length,mentioned:a.mentioned.length===1?tt('packs.y_is'):tt('packs.ies_are'),x:[...new Set(a.mentioned.map(m=>m.file))].slice(0,4).map(esc).join('</code>, <code>')})}</div>`:''}
      ${a.mentioned_mounts.length?`<div class="count">${tt('packs.mount_ridden_by_no_unit_but',{mentioned_mounts_n:a.mentioned_mounts.length,mentioned_mounts:a.mentioned_mounts.length===1?' is':tt('common.s_are')})}</div>`:''}
      ${a.campaign_files.length?`<div class="count">${tt('packs.campaign_and_battle_scripts_also_read',{campaign_files_n:a.campaign_files.length,campaign_files:a.campaign_files.slice(0,8).map(esc).join('</code>, <code>'),campaign_files2:a.campaign_files.length>8?tt('packs.and_more',{campaign_files:a.campaign_files.length-8}):''})}</div>`:''}
      <div id="clPreview"></div>
    </div>
    <div class="foot">
      ${cleanerBoxHtml()}
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="openRecheck()" title="${ttA('packs.re_test_what_earlier_cleanups_removed')}">${tt('packs.recheck_past_cleanups')}</button>
      <button onclick="clPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="clApply()">${tt('common.move_them_out')}</button>
    </div>`;
}
function clToggle(k){state.clean.open[k]=!state.clean.open[k];renderCleanup();}
function clStale(){const b=document.getElementById('clPreview');
  if(b&&state.clean.plan){state.clean.plan=null;b.innerHTML='';}}
async function clPickTarget(){
  const r=await api.post('/api/browse_folder',{title:tt('packs.folder_to_move_the_unused_assets')});
  if(!r.path)return;
  state.clean.target=r.path; clStale(); renderCleanup();
  state.settings.last_cleanup_target=r.path;      // so reopening the dialog offers it again
  api.post('/api/settings',{last_cleanup_target:r.path});
}
/* What the Lua pass protected. Its own box rather than a line in the "named in
   another file" note, because this is the safety net people do not know exists:
   an M2TWEOP script names battle models by string and nothing in the mod's .txt
   files records that, so without it the cleanup would delete a model the campaign
   uses and the break would only show up in game. */
function clLuaBox(a){
  const kept=a.lua_kept||[];
  const scanned=a.lua_files||0;
  if(!scanned) return '';
  if(!kept.length) return `<div class="count">${ttN('packs.read_lua_scripts_in_the_mod',scanned)}</div>`;
  const rows=kept.slice(0,60).map(m=>`<div class="frow"><span class="fp">${esc(m.entry)}</span><span class="fs">${
    esc(m.file)}${m.in_comment?tt('packs.in_a_comment_and_still_protected'):''}</span></div>`).join('');
  return `<fieldset class="assetconf" style="margin-top:10px;border-color:var(--good)">
    <legend class="w-good">${tt('packs.protected_by_the_mods_lua_scripts')}</legend>
    <div class="count">${ttN('packs.entries_named_by_lua_scripts',kept.length,{scripts:ttN('packs.lua_scripts_bold',scanned)})}</div>
    <div class="flist" style="margin-top:6px">${rows}${
      kept.length>60?`<div class="count">${tt('packs.and_more_2',{kept:kept.length-60})}</div>`:''}</div>
  </fieldset>`;
}
function clUnusedBody(){
  const c=state.clean,rows=c.a.unused;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('packs.nothing_every_entry_is_referenced')}</div>`;
  return `<div class="count" style="margin-top:7px">${tt('packs.no_unit_mount_or_character_in')}</div>
    <div class="clbar">
      <button onclick="clAll('entries',true)">${tt('common.select_all')}</button>
      <button onclick="clAll('entries',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(u=>`<div class="clrow">
      <input type="checkbox" ${c.entries.has(u.entry)?'checked':''}
        onchange="clPick('entries','${q1(esc(u.entry))}',this.checked)">
      <div class="grow"><span class="nm">${esc(u.entry)}</span>${u.copies>1?`
        <span class="badge w-warn">${tt('packs.copies_of_this_name_and_all',{copies:u.copies})}</span>`:''}
        <div class="sub">${tt('packs.lods_skins_files_named',{lods:ttN('packs.lods',u.lods),skins:ttN('packs.skins',u.skins),files:ttN('packs.files',u.files.length),on_disk:u.on_disk})}</div></div>
    </div>`).join('')}</div>`;
}
/* Suggestions, never decisions: the twin has the same animations, skeletons and
   torch block, but its meshes and textures are its own - so every row is ticked
   by hand (or with "Agree to all" once you have read them). */
function clMergeBody(){
  const c=state.clean,rows=c.a.merges;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('packs.none_found')}</div>`;
  return `<div class="count" style="margin-top:7px">
      ${tt('packs.each_of_these_is_used_only')}</div>
    <div class="clbar">
      <button onclick="clAll('merges',true)">${tt('packs.agree_to_all')}</button>
      <button onclick="clAll('merges',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(m=>{
      const risky=m.units_without_upgrades.length;
      return `<div class="clrow ${risky?'risky':''}">
      <input type="checkbox" ${c.merges.has(m.entry)?'checked':''}
        onchange="clPick('merges','${q1(esc(m.entry))}',this.checked)">
      <div class="grow">
        <span class="nm">${esc(m.entry)}</span> →
        <select onchange="clInto('${q1(esc(m.entry))}',this.value)">
          ${m.options.map(o=>`<option value="${esc(o)}" ${c.into[m.entry]===o?'selected':''}>${esc(o)}</option>`).join('')}
        </select>
        <span class="badge" id="clOwn_${esc(m.entry)}" style="color:var(--good);border-color:var(--good)${
          clIsOwn(m,c.into[m.entry])?'':';display:none'}">${tt('packs.already_an_armour_tier_of_the')}</span>
        <div class="sub">${tt('packs.soldier_of_lods_files',{units:m.units.map(u=>userLink(u)).join(', '),lods:ttN('packs.lods',m.lods),files:ttN('packs.files',m.files.length)})}</div>
        ${risky?`<div class="sub w-warn">${tt('packs.list_no_armour_ug_models_so',{units_without_upgrades:esc(m.units_without_upgrades.join(', '))})}</div>`:''}
      </div></div>`;}).join('')}</div>`;
}
/* "already an armour tier of the same unit" is a fact about the PICKED twin, not
   about the row - the picker offers up to 12, and only some of them are models the
   unit already draws. So the badge is re-evaluated on every change instead of being
   frozen at whatever the server suggested. */
const clIsOwn=(m,into)=>(m.own_options||[]).includes(into);
function clInto(entry,into){
  const c=state.clean;
  c.into[entry]=into;
  const row=c.a.merges.find(m=>m.entry===entry),b=document.getElementById('clOwn_'+entry);
  if(row&&b)b.style.display=clIsOwn(row,into)?'':'none';
  clStale();
}
/* A mount nothing rides is dead weight in descr_mount.txt, and its model entry is
   usually alive for that reason alone - so ticking one here is what lets the entry
   go too (that is what "frees ..." means on the row). Not pre-ticked: this is the
   one part of the cleanup that rewrites descr_mount.txt. */
function clMountBody(){
  const c=state.clean,rows=c.a.unused_mounts;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('packs.none_every_mount_is_ridden_by')}</div>`;
  return `<div class="count" style="margin-top:7px">${tt('packs.no_unit_rides_these_so_their')}</div>
    <div class="clbar">
      <button onclick="clAll('mounts',true)">${tt('common.select_all')}</button>
      <button onclick="clAll('mounts',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(m=>`<div class="clrow">
      <input type="checkbox" ${c.mounts.has(m.mount)?'checked':''}
        onchange="clPick('mounts','${q1(esc(m.mount))}',this.checked)">
      <div class="grow"><span class="nm">${esc(m.mount)}</span>
        ${m.class?`<span class="badge">${esc(m.class)}</span>`:''}
        ${m.frees_model?`<span class="badge" style="color:var(--good);border-color:var(--good)">${tt('packs.frees',{model:esc(m.model)})}</span>`:''}
        <div class="sub">${tt('packs.model',{model:esc(m.model||'(none)'),in_db:m.in_db?'':` <span class="w-warn">${tt('packs.not_in_the_modeldb')}</span>`})}</div>
        ${!m.frees_model&&m.kept_by.length?`<div class="sub">${tt('packs.its_model_stays_still_used_by',{kept_by:esc(m.kept_by.join(', '))})}</div>`:''}
        ${!m.frees_model&&!m.kept_by.length&&m.mentioned_in?`<div class="sub">${tt('packs.its_model_stays_named_in')} <code>${esc(m.mentioned_in)}</code></div>`:''}
      </div></div>`).join('')}</div>`;
}
function clOrphanBody(){
  const c=state.clean,rows=c.a.orphans;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('packs.none_every_file_under_unit_models')}</div>`;
  return `<div class="count" style="margin-top:7px">${tt('packs.files_sitting_in_data_unit_models')}</div>
    <div class="clbar">
      <button onclick="clAll('orphans',true)">${tt('common.select_all')}</button>
      <button onclick="clAll('orphans',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(o=>`<div class="clrow">
      <input type="checkbox" ${c.orphans.has(o.rel)?'checked':''}
        onchange="clPick('orphans','${q1(esc(o.rel))}',this.checked)">
      <div class="grow"><span class="sub" style="margin:0">${esc(o.rel)}</span></div>
      <span class="count">${MB(o.size)}</span></div>`).join('')}</div>`;
}
function clCountText(k){
  const c=state.clean,a=c.a;
  if(k==='unused')return tt('packs.ticked',{entries_n:c.entries.size,unused_n:a.unused.length});
  if(k==='merges')return tt('packs.ticked_needs_your_eye',{merges_n:c.merges.size,merges_n2:a.merges.length});
  if(k==='mounts'){
    const frees=a.unused_mounts.filter(m=>c.mounts.has(m.mount)&&m.frees_model).length;
    return tt('packs.ticked_2',{mounts_n:c.mounts.size,unused_mounts_n:a.unused_mounts.length,frees:frees?tt('packs.frees_entr',{frees,frees2:frees===1?'y':'ies'}):''});
  }
  const bytes=a.orphans.reduce((n,o)=>n+(c.orphans.has(o.rel)?o.size:0),0);
  return tt('packs.ticked_3',{orphans_n:c.orphans.size,orphans_n2:a.orphans.length,x:MB(bytes)});
}
function clCounts(){['unused','merges','mounts','orphans'].forEach(k=>{
  const el=document.getElementById('clc_'+k); if(el)el.textContent=clCountText(k);});}
// The checkbox already shows its own new state, so only the header count needs
// touching - that keeps ticking one of 3000 rows instant.
function clPick(key,id,on){const s=state.clean[key]; on?s.add(id):s.delete(id);
  clStale(); clCounts();}
function clAll(key,on){
  const c=state.clean;
  const all=key==='entries'?c.a.unused.map(u=>u.entry)
           :key==='merges'?c.a.merges.map(m=>m.entry)
           :key==='mounts'?c.a.unused_mounts.map(m=>m.mount)
           :c.a.orphans.map(o=>o.rel);
  c[key]=new Set(on?all:[]);
  const head=document.getElementById('clc_'+(key==='entries'?'unused':key));
  if(head)head.closest('.clsec').querySelectorAll('.cllist input[type=checkbox]')
    .forEach(cb=>{cb.checked=on;});
  clStale(); clCounts();
}
function clPayload(){
  const c=state.clean;
  // A ticked mount carries its model with it, so the freed entries ride along in
  // `entries` - they are never in the unused list (the mount was referencing them).
  const freed=c.a.unused_mounts.filter(m=>c.mounts.has(m.mount)&&m.frees_model).map(m=>m.model);
  return {mod:c.a.mod,target:c.target,
    entries:[...new Set([...c.entries,...freed])],
    merges:[...c.merges].map(e=>({entry:e,into:c.into[e]})),
    mounts:[...c.mounts],
    orphans:[...c.orphans]};
}
async function clPreview(){
  const box=document.getElementById('clPreview'); if(!box)return null;
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/bmdb/cleanup_plan',clPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.clean.plan=r;
  box.innerHTML=clPlanHtml(r); return r;
}
function clPlanHtml(r){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  const sample=r.exports.slice(0,12);
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">🧹</span><span class="stext">${tt('packs.what_this_moves')}</span></div>
    ${li('',r.changes)}
    ${r.target?`<div class="srow"><span class="sicon">📁</span><span class="stext">${tt('packs.into')} <span class="path">${esc(r.target)}</span></span></div>`:''}
    ${sample.length?`<div class="srow"><span class="sicon">·</span><span class="stext">
      ${sample.map(x=>`<span class="path">${esc(x)}</span>`).join('<br>')}
      ${r.export_count>sample.length?`<br><i>${tt('packs.and_more_3',{n:r.export_count-sample.length})}</i>`:''}</span></div>`:''}
    ${li('warn',r.warnings)}${li('bad',r.errors)}</div>`;
}
async function clApply(){
  const c=state.clean;
  if(!c.target){toast(tt('packs.choose_where_the_removed_assets_should'));return;}
  const r=state.clean.plan||await clPreview();
  if(!r)return;
  if(r.errors&&r.errors.length){toast(r.errors[0]);return;}
  if(!r.entry_deletes.length&&!r.export_count&&!r.mount_deletes.length){toast(tt('common.nothing_is_ticked'));return;}
  if(!confirm(tt('packs.move_entries_and_files_out',{entries:ttN('packs.modeldb_entries',r.entry_deletes.length),export_count:r.export_count,mod:c.a.mod,target:r.target,
      merges:r.merges.length?tt('packs.unit_soldier_line_s_are_repointed',{merges_n:r.merges.length}):'',
      mounts:r.mount_deletes.length?tt('packs.mount_s_are_removed_from_descr',{mount_deletes_n:r.mount_deletes.length}):''})))return;
  const job=newJob();
  const res=await runJob(job,tt('packs.cleaning_up'),
    tt('packs.copying_file_s_out_then_rewriting',{export_count:r.export_count,mod:esc(c.a.mod)}),
    ()=>api.post('/api/bmdb/cleanup_apply',{...clPayload(),job,clear_strings_bin:clearBinOn()}));
  if(res.error){toast(tt('packs.cleanup_failed_error',{error:res.error}));renderCleanup();return;}
  toast(ttN('packs.removed_entries_and_files',res.plan.entry_deletes.length,{export_count:res.plan.export_count,x:binMsg(res)}),5200);
  state.bmdb=null; state.destData=null;
  // The lists in this dialog were built from an audit taken BEFORE the cleanup,
  // so leaving them up shows entries that are no longer in the mod and invites
  // ticking them again. The audit is re-run here rather than left to whoever
  // reopens the dialog: the mod on disk changed, and the answer on screen has
  // to change with it. `loadSource` is not awaited - it repaints the page
  // behind the dialog and has nothing to do with what the dialog shows.
  loadSource();
  await openCleanup();
}

/* ---- recheck: what a PAST cleanup took out that today's nets would have kept ----

   The cleanup dialog above answers "may this go?" before anything moves. This one
   is for the morning after: a cleanup ran under an older, narrower idea of what
   counts as a reference, the mod now crashes, and the thing that broke it is by
   definition NOT in the mod any more - so no scan of the mod can find it. The
   server re-reads the cleanup log instead, re-tests everything each run removed
   against the current nets, and reports what can be put back and from where.

   Two states worth designing for, because both are common: a row that is wrong
   AND recoverable (tick it, it goes back), and a row that is wrong and whose
   backup and export folder have both since been deleted. The second cannot be
   fixed from here and says so plainly rather than offering a button that fails. */
async function openRecheck(){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  const job=newJob();
  let r;
  try{ r=await runJob(job,tt('packs.recheck_s_past_cleanups',{src:esc(state.src)}),
        tt('packs.re_reading_every_campaign_and_battle'),
        ()=>api.get(`/api/bmdb/recheck?mod=${enc(state.src)}&job=${enc(job)}`)); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.innerHTML=`<h2>${tt('packs.recheck')}</h2><div class="mbody w-bad">${esc(r.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  state.recheck={r,picks:new Set(r.rows.filter(x=>x.revertable).map(rcKey))};
  renderRecheck();
}
const rcKey=x=>`${x.kind}:${x.run}:${x.name}`;
function renderRecheck(){
  const s=state.recheck,r=s.r;
  const n=r.rows.length,ok=r.revertable,lost=n-ok;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('packs.recheck_s_past_cleanups_2',{mod:esc(r.mod)})}</h2>
    <div class="mbody">
      ${rcNetsHtml(r)}
      ${rcRunsHtml(r)}
      ${n?`<fieldset class="assetconf" style="margin-top:10px;border-color:var(--bad)">
        <legend class="w-bad">${tt('packs.removed_but_needed')}</legend>
        <div class="count">${ttN('packs.things_a_past_cleanup_took_out',n,{ok:ok?`<b>${ok}</b> ${tt('packs.can_be_put_back_from_a')}`:'',lost:lost?`<span class="w-bad">${ttN(ok?'packs.backup_gone_the_other_cannot':'packs.backup_gone_none_can_go_back',lost)}</span>`:''})}</div>
        <div class="clbar">
          <button onclick="rcAll(true)">${tt('packs.select_all_that_can_go_back')}</button>
          <button onclick="rcAll(false)">${tt('common.none_2')}</button></div>
        <div class="cllist">${r.rows.map(rcRowHtml).join('')}</div>
      </fieldset>`
      :`<div class="sum" style="margin-top:10px"><div class="srow">
          <span class="sicon">✓</span><span class="stext">${tt('packs.nothing_a_past_cleanup_removed_is',{x:r.checked_files+r.checked_entries
            ?ttN('packs.all_files_and_entries_removed',r.checked_entries,{checked_files:r.checked_files})
            :tt('packs.no_cleanup_of_this_mod_has')})}</span></div></div>`}
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="openCleanup()">${tt('packs.back_to_clean_up')}</button>
      ${ok?`<button class="primary" onclick="rcApply()">${tt('packs.put_the_ticked_ones_back')}</button>`:''}
    </div>`;
}
/* Said up front, not buried at the bottom: a clean result is only worth as much
   as the net that produced it, and the user has to be able to see that the file
   they are worried about was actually read. */
function rcNetsHtml(r){
  const n=r.nets||{};
  const cf=n.campaign_files||[];
  return `<div class="count" style="margin-bottom:10px">${tt('packs.read_for_this_check_scripts_and_text',{campaign:ttN('packs.campaign_scripts_bold',cf.length),x:cf.length?`(<code>${cf.slice(0,6).map(esc).join('</code>, <code>')}</code>${
      cf.length>6?tt('packs.and_more_4',{cf:cf.length-6}):''})`:'',lua:ttN('packs.lua_scripts_bold',n.lua_files||0),text_refs:n.text_refs||0})}</div>`;
}
/* The runs themselves, because "can this be undone at all" is decided here and
   not in the row list: a run whose backup AND export folder are both gone can
   still be reported on - the log remembers what it removed - but nothing it took
   out can be put back by this tool, and that is worth knowing before reading a
   list of things to tick. */
function rcRunsHtml(r){
  if(!r.runs.length)return '';
  return `<fieldset><legend>${tt('packs.cleanups_of_this_mod_that_are')}</legend>
    <div class="cllist">${r.runs.map(x=>`<div class="clrow ${
      x.hits&&!x.backup_here&&!x.export_here?'risky':''}">
      <div class="grow"><span class="nm">${esc(x.when)}</span>
        ${x.hits?`<span class="badge w-bad" style="border-color:var(--bad)">${tt('packs.flagged',{hits:x.hits})}</span>`
          :`<span class="badge" style="color:var(--good);border-color:var(--good)">${tt('packs.nothing_flagged')}</span>`}
        <div class="sub">${tt('packs.file_s_and_entr_removed_still',{files:x.files,x:x.entries,x2:x.entries===1?'y':'ies',missing:x.missing})}</div>
        <div class="sub">${tt('packs.backup_export_folder',{backup_here:x.backup_here?`<b class="w-good">${tt('packs.present')}</b>`
          :tt('packs.gone',{backup:esc(x.backup||tt('packs.not_recorded'))}),export_here:x.export_here?`<b class="w-good">${tt('packs.present')}</b>`
          :tt('packs.gone_2',{export:esc(x.export||tt('packs.not_recorded'))})})}</div>
      </div></div>`).join('')}</div></fieldset>`;
}
function rcRowHtml(x){
  const k=rcKey(x),on=state.recheck.picks.has(k);
  return `<div class="clrow ${x.revertable?'':'risky'}">
    <input type="checkbox" ${on?'checked':''} ${x.revertable?'':'disabled'}
      onchange="rcPick('${q1(esc(k))}',this.checked)">
    <div class="grow">
      <span class="nm">${esc(x.name)}</span>
      <span class="badge">${x.kind==='entry'?tt('packs.modeldb_entry'):'file'}</span>
      ${x.revertable?`<span class="badge" style="color:var(--good);border-color:var(--good)">
        ${tt('packs.from_the',{source:esc(x.source)})}</span>`
        :`<span class="badge w-bad" style="border-color:var(--bad)">${tt('packs.no_copy_left')}</span>`}
      <div class="sub">${x.why.map(esc).join(' · ')}</div>
      <div class="sub" style="color:var(--dim)">${tt('packs.removed',{when:esc(x.when),x:x.from?` · ${esc(x.from)}`:''})}</div>
    </div></div>`;
}
function rcPick(k,on){const p=state.recheck.picks; on?p.add(k):p.delete(k);}
function rcAll(on){
  const s=state.recheck;
  s.picks=new Set(on?s.r.rows.filter(x=>x.revertable).map(rcKey):[]);
  renderRecheck();
}
async function rcApply(){
  const s=state.recheck;
  const picks=s.r.rows.filter(x=>s.picks.has(rcKey(x)));
  if(!picks.length){toast(tt('common.nothing_is_ticked'));return;}
  const files=picks.filter(x=>x.kind==='file').length;
  const entries=picks.length-files;
  if(!confirm(entries?ttN('packs.put_files_and_entries_back',entries,{files,mod:s.r.mod}):tt('packs.put_files_back',{files,mod:s.r.mod})))return;
  const job=newJob();
  const res=await runJob(job,tt('packs.putting_them_back'),
    entries?ttN('packs.copying_files_and_entries_back',entries,{files,mod:esc(s.r.mod)}):tt('packs.copying_files_back',{files,mod:esc(s.r.mod)}),
    ()=>api.post('/api/bmdb/recheck_revert',
      {mod:s.r.mod,job,picks:picks.map(x=>({kind:x.kind,run:x.run,name:x.name}))}));
  if(res.error){toast(tt('packs.revert_failed_error',{error:res.error}));return;}
  toast(tt('packs.put_thing_s_back_undo_in',{restored_n:res.restored.length,x:res.failed.length?tt('packs.could_not_be',{failed_n:res.failed.length}):''}),5200);
  state.bmdb=null; state.destData=null;
  loadSource();
  // Re-run rather than leaving the list up: the rows that just went back are no
  // longer findings, and a list that still shows them invites a second revert.
  await openRecheck();
}

function edDeleteDialog(){
  const e=state.ed;
  document.getElementById('modal').innerHTML=`<h2 class="w-bad">${tt('packs.delete',{type:esc(e.d.type)})}</h2>
    <div class="mbody">
      <div class="warnbox">${tt('packs.this_removes_the_units_block_from')}</div>
      <fieldset><legend>${tt('packs.also_remove')}</legend>
        <label class="chk"><input type="checkbox" id="dOptLoc" checked> ${tt('packs.its_text_entry_from_export_units',{dictionary:esc(e.d.dictionary)})}</label><br>
        <label class="chk"><input type="checkbox" id="dOptModels"> ${tt('packs.its_battle_model_entries_only_ones')}</label><br>
        <label class="chk"><input type="checkbox" id="dOptAssets"> ${tt('packs.the_mesh_texture_files_of_those')}</label><br>
        <label class="chk"><input type="checkbox" id="dOptIcons"> ${tt('packs.its_unit_card_and_info_card')}</label>
      </fieldset>
      <div class="count">${tt('packs.everything_removed_is_backed_up_first')}</div>
      <div id="edPreview"></div>
    </div>
    <div class="foot"><button onclick="renderEditor()">${tt('common.cancel')}</button>
      <button onclick="edDeletePreview()">${tt('common.probe')}</button>
      <button class="danger" onclick="edDoDelete()">${tt('packs.delete_unit')}</button></div>`;
  edDeletePreview();
}
function edDeleteOpts(){
  const g=id=>{const el=document.getElementById(id);return !!(el&&el.checked);};
  return {delete:true,delete_options:{remove_loc:g('dOptLoc'),remove_models:g('dOptModels'),
    remove_assets:g('dOptAssets'),remove_icons:g('dOptIcons')}};
}
async function edDeletePreview(){
  const box=document.getElementById('edPreview'); if(!box)return;
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/edit/plan',edPayload(edDeleteOpts()));
  box.innerHTML=r.error?`<div class="preview w-bad">${esc(r.error)}</div>`:edPlanHtml(r);
}
async function edDoDelete(){
  const e=state.ed;
  if(!confirm(tt('packs.delete_from_it_is_backed_up',{type:e.d.type,mod:e.mod})))return;
  const res=await api.post('/api/edit/apply',edPayload(edDeleteOpts()));
  if(res.error){toast(tt('packs.delete_failed_error',{error:res.error}));return;}
  closeModal(); toast(tt('packs.deleted_undo_in_log',{type:e.d.type}),4200);
  state.destData=null; loadSource();
}
