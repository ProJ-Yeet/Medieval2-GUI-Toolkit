/* sprites.js - Sprites mode: generating and wiring the far-LOD unit sprites

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ---------- sprites mode ----------
   Sprites are the flat billboards the game swaps in at the far LOD. The engine
   renders them, but only as a side effect of booting with a magic flag, and what
   lands on disk is raw TGA. This workspace does the prep, then owns everything
   after generation: convert, dedup, install and point the modeldb at the result.
   The two published methods differ only in step 1, so that is the only step that
   branches. */
async function loadSprites(){
  const mod=state.src;
  main.innerHTML=`<div class="empty">${tt('sprites.reading_mod_s_models',{mod:esc(mod)})}</div>`;
  let r;
  try{ r=await api.get('/api/sprites?mod='+enc(mod)); }
  catch(e){ if(stale('sprites',mod))return;
    main.innerHTML=`<div class="empty">${tt('sprites.couldnt_read_the_modeldb')}<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadSprites()">${tt('common.retry')}</button></div>`; return; }
  if(stale('sprites',mod))return;       // moved on while this was in flight
  state.spr=Object.assign({
    picked:new Set(),
    // EOP is strictly nicer where it exists (no CFG edit, no restart per batch),
    // so it leads unless the mod shows no sign of it
    method:r.has_eop?'eop':'classic',
    cfg:r.cfgs[0]||'', mipmaps:false, dedup:true, mounts:false, last:null,
    // a real mod lists 2000+ models of which a couple of hundred need anything,
    // so the list opens on the work rather than on the whole modeldb
    todo:true
  },r);
  renderSprites();
}
function sprSet(k,v){state.spr[k]=v;renderSprites();}
function sprPick(name,on){const s=state.spr;on?s.picked.add(name):s.picked.delete(name);renderSprites();}
function sprPickShown(on){const s=state.spr;sprShown().forEach(m=>on?s.picked.add(m.name):s.picked.delete(m.name));renderSprites();}
// The models a unit visibly *switches to* - its armour-upgrade levels. An entry
// that is only ever somebody's soldier, officer or general model is skipped:
// picking those alongside is what makes a batch balloon from thirty models to
// two thousand, and they are covered by their own unit's row anyway.
function sprPickUpgrades(){
  const s=state.spr, hits=sprShown().filter(m=>(m.roles||[]).includes('armour'));
  if(!hits.length)return toast(tt('sprites.no_armour_upgrade_models_among_the'));
  hits.forEach(m=>s.picked.add(m.name));
  renderSprites(); toast(tt('sprites.picked_armour_upgrade_model_s',{hits_n:hits.length}));
}
function sprQuery(){
  // the sidebar box and the picker's own box are the same filter, so either works
  return ((state.spr&&state.spr.q)||search.value||'').trim().toLowerCase();
}
function sprShown(){
  const s=state.spr,qq=sprQuery();
  // "needs sprites" hides anything whose every faction record already resolves,
  // plus anything marked done by hand. A search overrides it, so a model you
  // deliberately look up never silently fails to appear.
  return s.models.filter(m=>(!qq||m.name.includes(qq))&&(s.mounts||!m.is_mount||qq)
    &&(!s.todo||qq||(m.state!=='ok'&&!m.done)));
}
const SPR_STATE={ok:tt('sprites.has_sprites'),partial:tt('sprites.partly_done'),none:tt('sprites.no_sprites')};
// What a model is used AS. Worth showing per row: it is the difference between
// "this needs a sprite of its own" and "this is already covered elsewhere".
const SPR_ROLE={soldier:'soldier',armour:tt('sprites.armour_ug'),officer:'officer',mount:'mount'};
function sprFlags(m){
  const out=(m.roles||[]).map(r=>`<span class="sprtag">${esc(SPR_ROLE[r]||r)}</span>`);
  if(m.is_mount&&!(m.roles||[]).includes('mount'))out.unshift(`<span class="sprtag">${tt('sprites.mount')}</span>`);
  if(m.done)out.push(`<span class="sprtag on">${tt('sprites.done')}</span>`);
  // state 'none' used to render nothing at all, so the rows that most need
  // flagging were the only ones with no flag
  out.push(m.state==='none'
    ?`<span class="sprtag warn">${tt('sprites.not_in_unit_sprites')}</span>`
    :`<span class="sprtag ${m.state==='ok'?'on':''}">${SPR_STATE[m.state]}</span>`);
  return out.join(' ');
}
async function sprMark(on){
  const s=state.spr,names=[...s.picked];
  if(!names.length)return toast(tt('sprites.pick_some_models_first'));
  const r=await api.post('/api/sprites/mark',{mod:state.src,models:names,done:on});
  if(r.error)return toast(r.error);
  s.picked.clear();
  toast(tt('sprites.model_s',{names_n:names.length,on:on?tt('sprites.marked_done'):'unmarked'}));
  await loadSprites();
}
function renderSprites(){
  if(!state.spr||state.spr.mod!==state.src)return loadSprites();
  const s=state.spr, a=s.audit, picked=[...s.picked];
  const shown=sprShown();
  count.textContent=`${picked.length} picked`;
  const pending=s.pending.filter(p=>p.complete);
  const cfgState=s.cfg?(s.cfg_state[s.cfg]||'absent'):'absent';

  main.innerHTML=bmdbTabsHtml('data/unit_sprites')+`<div class="sprhead">
      <h2>${tt('sprites.unit_sprites',{src:esc(state.src)})}</h2>
      <span class="count">${tt('sprites.generate_the_far_lod_billboards_convert',{x:a.missing||a.misnamed_total
        ?tt('sprites.n_of_total_sprite_lines_resolve_to_no_file',{bad:a.missing+a.misnamed_total,total:a.ok+a.missing+a.misnamed_total})
        :tt('sprites.all_sprite_line_s_resolve',{ok:a.ok})})}</span>
    </div>

    <div class="sprstep"><h3><span class="n">1</span> ${tt('sprites.generate')}
      <span class="grow"></span>
      <span class="count">${s.method==='eop'?tt('sprites.via_the_m2tweop_console'):tt('sprites.via_sprite_script_cfg')}</span>
      </h3>
      <div class="sprbody">
        <div class="sprnote">${s.has_eop
          ?docPoints(tt('sprites.this_mod_ships_m2tweop_so_generation'),[
            tt('sprites.no_cfg_to_edit'),
            tt('sprites.no_restart_between_batches'),
            s.method==='classic'
              ?`<a href="#" onclick="sprSet('method','eop');return false">${tt('sprites.use_it_instead')}</a>`
              :`<a href="#" onclick="sprSet('method','classic');return false">${tt('sprites.use_the_classic_route_instead')}</a>`])
          :docPoints(tt('sprites.this_mod_has_no_m2tweop_install'),[
            tt('sprites.the_game_renders_the_sprites_on'),
            tt('sprites.everything_after_that_is_the_same')])}</div>
        <div class="sprrow">
          <input id="sprQ" type="search" placeholder="${ttA('sprites.search_models')}" value="${esc(s.q||'')}"
            oninput="sprSet('q',this.value)" style="min-width:200px">
          <span class="count">${tt('sprites.of_model_s',{shown_n:shown.length,models_n:s.models.length})}</span>
          <button onclick="sprPickShown(true)">${tt('sprites.pick_all_shown')}</button>
          <button onclick="sprPickUpgrades()" title="${ttA('sprites.armour_upgrade_models_only_skips_entries')}">${tt('sprites.pick_armour_upgrades')}</button>
          <button onclick="sprPickShown(false)">${tt('common.clear')}</button>
          <label class="chk"><input type="checkbox" ${s.todo?'checked':''}
            onchange="sprSet('todo',this.checked)"> ${tt('sprites.needs_sprites_only')}</label>
          <label class="chk"><input type="checkbox" ${s.mounts?'checked':''}
            onchange="sprSet('mounts',this.checked)"> ${tt('sprites.show_mounts')}</label>
          <span class="grow"></span>
        </div>
        <div class="sprrow">
          <button ${picked.length?'':'disabled'} onclick="sprMark(true)">
            ${tt('sprites.mark_done_by_hand',{picked_n:picked.length})}</button>
          <button ${picked.length?'':'disabled'} onclick="sprMark(false)">${tt('sprites.unmark')}</button>
          <span class="count">${tt('sprites.marked_done_2',{done_total:s.done_total,todo:s.todo
            ?tt('sprites.hidden_along_with_models_whose_lines'):''})}</span>
        </div>
        <div class="sprnote">${tt('sprites.mounts_need_their_own_sprites_so')}</div>
        <div class="sprpick">${shown.length?shown.map(m=>`
          <label><input type="checkbox" ${s.picked.has(m.name)?'checked':''}
            onchange="sprPick('${q1(m.name)}',this.checked)">
            <span>${esc(m.name)}</span> ${sprFlags(m)}
            <span class="fac">${tt('sprites.n_factions',{n:m.factions.length})}</span></label>`).join('')
          :`<div class="empty" style="padding:14px">${s.todo
            ?tt('sprites.nothing_left_to_generate_every_model')
            :tt('sprites.no_models_match')}</div>`}</div>
        ${s.method==='eop'?`
          <div class="sprnote">${tt('sprites.load_to_the_main_menu_and')}</div>
          <textarea class="sprlua" readonly onclick="this.select()">${
            picked.length?picked.map(m=>`M2TWEOP.generateSprite("${m}")`).join('\n')
            :tt('sprites.pick_one_or_more_models_above')}</textarea>
          <div class="sprrow"><button ${picked.length?'':'disabled'}
            onclick="sprCopyLua()">${tt('sprites.copy_to_clipboard')}</button>
            <span class="count">${tt('sprites.sprites_land_in',{sprExportDirs:sprExportDirs(s)})}</span></div>`
        :`
          <div class="sprrow">
            <span class="count">${tt('sprites.cfg_that_launches_the_mod')}</span>
            <select onchange="sprSet('cfg',this.value)" style="max-width:340px">
              ${s.cfgs.length?s.cfgs.map(c=>`<option value="${esc(c)}" ${c===s.cfg?'selected':''}>${esc(c)}</option>`).join('')
                :`<option value="">${tt('sprites.none_found')}</option>`}
            </select>
            <span class="sprtag ${cfgState==='on'?'on':'off'}">${tt('sprites.bypass',{cfgState:esc(cfgState)})}</span>
          </div>
          <div class="sprnote">${docPoints(tt('sprites.two_things_catch_people_out_on'),[
            tt('sprites.sprite_script_txt_goes_in_the_medieval'),
            tt('sprites.the_bypass_flag_makes_the_next_normal')])}</div>
          <div class="sprrow">
            <button class="primary" ${picked.length?'':'disabled'} onclick="sprPrep()">
              ${tt('sprites.write_sprite_script_set_flag',{picked_n:picked.length})}</button>
            <button ${cfgState==='on'?'':'disabled'} onclick="sprRevert()">${tt('sprites.turn_the_flag_back_off')}</button>
          </div>`}
      </div></div>

    <div class="sprstep"><h3><span class="n">2</span> ${tt('sprites.convert_waiting',{pending_n:pending.length})}</h3>
      <div class="sprbody">
        ${s.have_nvcompress?'':`<div class="sprnote w-warn">${tt('sprites.nvcompress_exe_is_missing_from_vendor')}</div>`}
        <div class="sprnote">${docPoints(tt('sprites.conversion_runs_here_start_to_finish'),[
          tt('sprites.tga_dxt5_dds_texture'),
          tt('sprites.installed_into',{install_dir:esc(s.install_dir)}),
          tt('sprites.the_published_route_needs_a_gui')])}</div>
        ${pending.length?`<div class="sprlist">
          <div class="r hrow">${tt('sprites.sprite_model_sheets')}</div>
          ${pending.map(p=>`<div class="r"><span>${esc(p.stem)}</span>
            <span class="count">${esc(p.model)}</span>
            <span class="count">${p.sheets||p.textures}</span></div>`).join('')}</div>`
        :`<div class="sprnote">${tt('sprites.nothing_waiting_in_run_step_1',{sprExportDirs:sprExportDirs(s)})}</div>`}
        ${s.pending.length>pending.length?`<div class="sprnote w-warn">
          ${tt('sprites.incomplete_set_s_ignored_because_they',{n:s.pending.length-pending.length})}</div>`:''}
        <div class="sprrow">
          <button class="primary" ${pending.length&&s.have_nvcompress?'':'disabled'}
            onclick="sprConvert()">${tt('sprites.convert_sprite_s',{pending_n:pending.length})}</button>
          <button onclick="loadSprites()">${tt('sprites.rescan')}</button>
          <label class="chk"><input type="checkbox" ${s.dedup?'checked':''}
            onchange="sprSet('dedup',this.checked)"> ${tt('sprites.collapse_identical_faction_copies')}</label>
          <label class="chk"><input type="checkbox" ${s.mipmaps?'checked':''}
            onchange="sprSet('mipmaps',this.checked)"> ${tt('sprites.mipmaps')}</label>
        </div>
        <div class="sprnote">${tt('sprites.the_engine_writes_one_sprite_per')}</div>
        ${s.last?sprResultHtml(s.last):''}
      </div></div>

    <div class="sprstep"><h3><span class="n">3</span> ${tt('sprites.wire_into_the_modeldb')}</h3>
      <div class="sprbody">
        <div class="sprnote">${tt('sprites.both_published_methods_stop_here_and')}</div>
        ${a.misnamed.length?`
          <div class="sprnote"><b class="w-warn">${a.misnamed_total}</b> ${tt('sprites.line_s_point_at_nothing_while')}</div>
          <div class="sprlist">
            <div class="r hrow">${tt('sprites.points_at_model_faction')}</div>
            ${a.misnamed.slice(0,50).map(r=>`<div class="r"><span>${esc(r.path)}</span>
              <span class="count">${esc(r.model)}</span>
              <span class="count">${esc(r.faction)}</span></div>`).join('')}</div>
          <div class="sprrow"><button class="primary" onclick="sprFixNames()">
            ${tt('sprites.repoint_line_s',{misnamed_n:a.misnamed.length})}</button>
            ${a.misnamed_total>a.misnamed.length?`<span class="count">${tt('sprites.of_run_it_again_for_the',{misnamed_total:a.misnamed_total})}</span>`:''}</div>`
        :`<div class="sprnote">${tt('sprites.no_misnamed_sprite_lines')}</div>`}
        ${a.missing?`<div class="sprnote w-warn">${tt('sprites.line_s_name_a_sprite_that',{missing:a.missing})}</div>`:''}
        ${a.orphans?`<div class="sprnote">${tt('sprites.sprite_file_s_in_unit_sprites',{orphans:a.orphans})}</div>`:''}
      </div></div>`;
}
// Two folders when the mod lives outside the install that launches it - both are
// scanned, and naming both is what makes "nothing found" diagnosable.
function sprExportDirs(s){
  const d=(s.export_dirs&&s.export_dirs.length)?s.export_dirs
         :[s.export_dir||'export/unit_sprites'];
  return d.map(p=>`<code>${esc(p)}</code>`).join(' or ');
}
function sprResultHtml(r){
  const dupes=Object.values(r.duplicates||{}).reduce((n,v)=>n+Object.keys(v).length,0);
  const models=Object.keys(r.models||{}).length;
  return `<div class="sprnote" style="border-top:1px solid var(--edge);padding-top:9px">
    ${dupes?tt('sprites.converted_sheets_across_models_installed_dupes',{converted_n:r.converted.length,models,installed_n:r.installed.length,dupes})
      :tt('sprites.converted_sheets_across_models_installed',{converted_n:r.converted.length,models,installed_n:r.installed.length})}
    </div>
    <div class="sprrow"><button class="primary" onclick="sprWire()">
      ${tt('sprites.point_the_modeldb_at_these_model',{models})}</button></div>`;
}
async function sprCopyLua(){
  const t=[...state.spr.picked].map(m=>`M2TWEOP.generateSprite("${m}")`).join('\n');
  try{ await navigator.clipboard.writeText(t); toast(tt('sprites.copied_paste_it_into_the_eop')); }
  catch(e){ toast(tt('sprites.could_not_reach_the_clipboard_select')); }
}
async function sprPrep(){
  const s=state.spr;
  const r=await api.post('/api/sprites/prep_apply',{mod:state.src,models:[...s.picked],
    method:'classic',cfg_path:s.cfg});
  if(r.error)return toast(r.error);
  if(r.unknown?.length)toast(tt('sprites.name_s_are_not_modeldb_entries',{unknown_n:r.unknown.length}));
  else toast(tt('sprites.ready_run_the_mod_then_come'));
  await loadSprites();
}
async function sprRevert(){
  const r=await api.post('/api/sprites/revert_cfg',{cfg:state.spr.cfg});
  toast(r.error?r.error:r.changed?tt('sprites.flag_turned_off'):tt('sprites.flag_was_already_off'));
  await loadSprites();
}
async function sprConvert(){
  const s=state.spr,job=newJob();
  overlay.classList.add('open');
  const r=await runJob(job,tt('sprites.converting_sprites'),
    tt('sprites.tga_dxt5_dds_texture_then_installing',{install_dir:esc(s.install_dir)}),
    ()=>api.post('/api/sprites/convert_apply',{mod:state.src,job,mipmaps:s.mipmaps,
      dedup:s.dedup,install:true,cleanup:true}));
  closeModal();
  if(r.error)return toast(tt('sprites.convert_failed_error',{error:r.error}));
  const last=r.record;
  await loadSprites();           // re-reads the mod: export/ and data/ both changed
  state.spr.last=last; renderSprites();
  toast(tt('sprites.converted_sheet_s',{converted_n:last.converted.length}));
}
async function sprWire(){
  const last=state.spr.last; if(!last)return;
  const r=await api.post('/api/sprites/wire',{mod:state.src,models:last.models,
    duplicates:last.duplicates});
  if(r.error)return toast(r.error);
  toast(tt('sprites.modeldb_updated_undo_is_in_the'));
  await loadSprites();
}
async function sprFixNames(){
  // rebuild the sprite line for every faction record the audit flagged; the
  // server derives the correct casing from the modeldb itself
  const models={};
  for(const r of state.spr.audit.misnamed)(models[r.model]||(models[r.model]=[])).push(r.faction);
  const res=await api.post('/api/sprites/wire',{mod:state.src,models});
  if(res.error)return toast(res.error);
  toast(tt('sprites.sprite_lines_repointed_undo_is_in'));
  await loadSprites();
}

function renderSounds(){
  if(!state.snd||state.snd.mod!==state.src)return loadSounds();
  const s=state.snd;
  if(!s.has_file){
    main.innerHTML=soundTabsHtml()+`<div class="empty">${tt('sprites.has_no_data_export_descr_sounds',{src:esc(state.src)})}</div>`;
    sndBtn.textContent=tt('sprites.apply_voice_edits_0'); sndBtn.disabled=true; return;
  }
  const qq=search.value.trim().toLowerCase();
  const list=s.tab==='missing'?s.missing:s.tab==='existing'?s.existing:s.orphans;
  const all=list.filter(u=>{
    if(qq&&!(u.type.toLowerCase().includes(qq)||(u.name||'').toLowerCase().includes(qq)))return false;
    const a=sndVal(u,'accent'),c=sndVal(u,'class');
    if(s.fAccent&&a!==s.fAccent)return false;
    if(s.fClass&&c!==s.fClass)return false;
    if(s.onlyBad&&s.tab==='existing'&&!(u.accent_conflict||u.class_conflict))return false;
    if(s.onlyBad&&s.tab==='missing'&&u.accent_valid)return false;
    return true;
  });
  s.view=all.slice(0,SND_CAP);
  const staged=sndOps().length;
  sndBtn.textContent=tt('sprites.apply_voice_edits',{staged}); sndBtn.disabled=!staged;
  count.textContent=`${all.length}/${list.length}`;
  const nConf=s.existing.filter(u=>u.accent_conflict||u.class_conflict).length;
  const tab=(k,label,n)=>`<button class="${s.tab===k?'on':''}" onclick="sndTab('${k}')">${label} <span class="badge">${n}</span></button>`;
  const opt=(v,cur)=>`<option value="${esc(v)}" ${v===cur?'selected':''}>${esc(v)}</option>`;
  main.innerHTML=soundTabsHtml('data/export_descr_sounds_units_voice.txt')+`<div class="sndhead">
      <h2>${tt('sprites.unit_voices',{src:esc(state.src)})}</h2>
      <div class="count">${docPoints(tt('sprites.units_have_their_own_selection_barks',{donors_n:s.donors.length,pairs_n:s.pairs.length}),[
        nConf?tt('sprites.n_unit_s_sit_in_a_block_their_edu_doesnt_point_at',{n:nConf}):'',
        s.ships_skipped?tt('sprites.ship_s_are_left_out_a',{ships_skipped:s.ships_skipped}):''])}</div>
      <div class="sndtabs">
        ${tab('missing',tt('sprites.no_voice_entry'),s.missing.length)}
        ${tab('existing',tt('sprites.has_a_voice_entry'),s.existing.length)}
        ${tab('orphans',tt('sprites.entries_with_no_unit'),s.orphans.length)}
      </div>
    </div>
    ${s.tab==='orphans'?`<div class="count" style="margin-top:10px">${docPoints(
       tt('sprites.these_entries_name_units_that_no'),[
       tt('sprites.they_do_nothing_on_their_own'),
       tt('sprites.the_name_stays_taken_a_new'),
       tt('sprites.tick_one_to_delete_it')])}</div>`:''}
    <div class="sndbar">
      <span class="count">${tt('sprites.filter')}</span>
      <select onchange="sndFilter('fAccent',this.value)">
        <option value="">${tt('sprites.all_accents')}</option>${s.accents.map(a=>opt(a,s.fAccent)).join('')}</select>
      <select onchange="sndFilter('fClass',this.value)">
        <option value="">${tt('sprites.all_classes')}</option>${s.classes.map(c=>opt(c,s.fClass)).join('')}</select>
      ${s.tab==='orphans'?'':`<label class="chk"><input type="checkbox" ${s.onlyBad?'checked':''}
        onchange="sndFilter('onlyBad',this.checked)"> ${s.tab==='existing'?tt('sprites.only_ones_the_edu_disagrees_with'):tt('sprites.only_ones_with_no_usable_accent')}</label>`}
      <span class="grow"></span>
      ${s.tab==='orphans'?'':`<span class="count">${tt('sprites.set_all_shown_to_copy',{view_n:s.view.length})}</span>
      <select onchange="sndFilter('bulkDonor',this.value)" style="max-width:230px">
        <option value="">${tt('sprites.pick_a_unit')}</option>
        ${s.donors.map(d=>`<option value="${esc(d.name)}" ${d.name===s.bulkDonor?'selected':''}>${esc(d.name)} (${esc(d.accent)}/${esc(d['class'])})</option>`).join('')}
      </select>
      <button onclick="sndBulk()">${tt('sprites.apply_to_shown')}</button>`}
      ${staged?`<button class="danger" onclick="sndReset()">${tt('sprites.clear_staged',{staged})}</button>`:''}
      <button class="${s.cv?'on':''}" title="${ttA('sprites.show_a_units_block_exactly_as')}"
        onclick="sndCvToggle()">${tt('common.code_view')}</button>
    </div>
    <div class="cvsplit${s.cv?'':' off'}">
    <div id="sndGui">
    ${all.length?`<div class="sndlist">
      <div class="sndrow hrow">${tt('sprites.unit_in_game_now_accent_class')}</div>
      ${tt('sprites.x',{x:s.view.map(sndRowHtml).join('')})}</div>`
     :`<div class="empty">${tt('common.no_units_match')}</div>`}
    </div>
    ${s.cv?`<div id="sndCodeCol">${cvHtml(s.cv)}</div>`:''}
    </div>
    ${all.length>SND_CAP?`<div class="count" style="margin:10px 0">${tt('sprites.showing_the_first_of_narrow_it',{SND_CAP,all_n:all.length})}</div>`:''}`;
  if(s.cv&&s.cv.loaded)cvWire(s.cv);
}
function sndRowHtml(u,i){
  const s=state.snd,op=s.ops[u.type]||{};
  const a=sndVal(u,'accent'),c=sndVal(u,'class');
  const isOrphan=s.tab==='orphans', has=u.accent!==undefined;
  const ready=sndReady(u), dropping=!!op.remove;
  // what the game does with this unit right now, before anything staged
  let now;
  if(isOrphan) now=`<span class="w-warn">${tt('sprites.no_such_unit')}</span>`;
  else if(!has) now=u.edu_accent
    ? (u.accent_valid?`<span class="count">${tt('sprites.generic',{edu_accent:esc(u.edu_accent)})}</span>`
                     :`<span class="w-bad" title="${ttA('sprites.the_edu_names_an_accent_this')}">${esc(u.edu_accent)} ✗</span>`)
    : `<span class="w-warn" title="${ttA('sprites.no_accent_line_in_the_edu')}">${tt('sprites.no_accent')}</span>`;
  else now=(u.accent_conflict||u.class_conflict)
    ? `<span class="w-bad" title="${ttA('sprites.edu_says_the_bank_has_it',{edu_accent:esc(u.edu_accent||'none'),edu_class:esc(u.edu_class||'none'),accent:esc(u.accent),x:esc(u['class'])})}">${esc(u.accent)}/${esc(u['class'])} ✗</span>`
    : `<span class="count">${esc(u.accent)}/${esc(u['class'])}</span>`;
  if(isOrphan) return `<div class="sndrow ${dropping?'dropping':''}">
    <div class="un"><span class="uc empty" title="${ttA('sprites.no_unit_by_this_name_exists')}"></span>
      <span class="un2"><span class="nm">${esc(u.name)}</span>
        <span class="ty">${tt('sprites.voice_entry_only')}</span></span></div>
    <span class="now">${now}</span>
    <span class="count">${esc(u.accent)}</span><span class="count">${esc(u['class'])}</span>
    ${tt('sprites.none')}<input type="checkbox" ${dropping?'checked':''} title="${ttA('sprites.delete_this_entry_from_the_voice')}"
      onchange="sndToggleRemove(${i},this.checked)"></span></div>`;
  const donors=sndDonors(a,c);
  const sel=(cur,vals,key,blank)=>`<select onchange="sndPick(${i},'${key}',this.value)" ${dropping?'disabled':''}>
    <option value="">${blank}</option>
    ${vals.map(v=>`<option value="${esc(v)}" ${v===cur?'selected':''}>${esc(v)}</option>`).join('')}</select>`;
  return `<div class="sndrow ${dropping?'dropping':ready?'staged':''}"
    data-label="unit" data-snd="${esc(u.type)}">
    <div class="un" onclick="sndCvShow('${q1(esc(u.type))}')"
      title="${ttA('sprites.show_this_units_block_in_the')}">
      <img class="uc" loading="lazy" onerror="iconRetry(this)"
        src="${iconUrl(state.src,u.type)}" alt="">
      <span class="un2"><span class="nm">${esc(u.name||u.type)}</span>
        <span class="ty">${esc(u.type)}</span></span></div>
    <span class="now">${now}</span>
    ${sel(a,s.accents,'accent',tt('sprites.pick_an_accent'))}
    ${sel(c,s.classes,'class',tt('sprites.pick_a_class'))}
    <select onchange="sndPick(${i},'donor',this.value)" ${dropping?'disabled':''}
      title="${a&&c?tt('sprites.units_with_their_own_barks_in',{x:esc(a),x2:esc(c)}):tt('sprites.pick_an_accent_and_a_class')}">
      <option value="">${a&&c?(has?tt('sprites.keep_its_own_sounds'):tt('sprites.pick_a_unit_2',{donors_n:donors.length})):tt('sprites.pick_an_accent_and_a_class_2')}</option>
      ${donors.map(d=>`<option value="${esc(d.name)}" ${d.name===(op.donor||'')?'selected':''}>${esc(d.name)}</option>`).join('')}
    </select>
    <span class="rm">${has?`<input type="checkbox" ${dropping?'checked':''}
      title="${ttA('sprites.remove_this_units_voice_entry_from')}" onchange="sndToggleRemove(${i},this.checked)">`:''}</span>
  </div>`;
}
/* ---- code view on the sounds screen ----
   READ-ONLY (see codeview.sounds_document): a voice entry only means anything
   under the accent/class headers above it, and moving it between those is the
   staged edits' whole job. The pane answers "what does the file actually say
   about this unit", which is what the screen had no way to show. */
async function sndCvToggle(){
  const s=state.snd;
  if(s.cv){cvDrop(s.cv); s.cv=null; renderSounds(); return;}
  s.cv=cvCreate({kind:'sounds', mod:state.src, id:s.cvUnit||'', readonly:true,
    where:'data/export_descr_sounds_units_voice.txt'});
  renderSounds();
  if(s.cvUnit)await sndCvShow(s.cvUnit); else {s.cv.loaded=true; renderSounds();}
}
async function sndCvShow(type){
  const s=state.snd; if(!s.cv)return;
  s.cvUnit=type;
  const cv=s.cv; cv.id=type;
  // A unit on the "no voice entry" tab has no block to show, and asking the
  // server for one comes back as a bare 404. Say what is actually true instead.
  const row=(s.existing||[]).concat(s.missing||[],s.orphans||[])
    .find(u=>u.type===type||u.name===type);
  if(row&&row.accent===undefined){
    cv.loaded=true; cv.text=''; cv.spans={}; cv.partSpans={}; cv.err=null;
    cv.base=''; cv.pristine=''; cv.hidden=[]; cv.comments=0; cv.auto=null;
    cv.note=tt('sprites.has_no_entry_in_the_voice_bank_stage_one',{type});
    renderSounds(); return;
  }
  cv.loaded=false;
  renderSounds();
  await cvLoad(cv);
  if(state.snd===s&&s.cv===cv)renderSounds();
}
async function sndApply(){
  const ops=sndOps(); if(!ops.length)return;
  const modal=document.getElementById('modal');
  modal.className='modal'; modal.innerHTML=`<h2>${tt('sprites.planning_voice_edits')}</h2>`;
  overlay.classList.add('open');
  let r;
  try{ r=await api.post('/api/sounds/plan',{mod:state.src,ops}); }
  catch(e){ r={error:''+e}; }
  if(r.error&&!r.errors){ modal.innerHTML=`<h2>${tt('sprites.voice_edits')}</h2><div class="mbody w-bad">${esc(r.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  const bad=(r.errors||[]).length;
  modal.innerHTML=`<h2>${tt('sprites.voice_edits')} <span class="pill">${esc(state.src)}</span></h2>
    <div class="mbody">
      ${bad?`<div class="warnbox">${tt('sprites.row_s_cant_be_written_nothing',{bad,errors:r.errors.map(e=>esc(e)).join('<br>')})}</div>`:''}
      <div class="count" style="margin-bottom:8px">${docPoints(
        r.edu_rewritten?tt('sprites.writes_the_voice_bank_and_the_edu'):tt('sprites.writes_the_voice_bank_only'),[
        tt('sprites.backed_up_first_log_undo_restores_them_exactly')])}</div>
      ${renderSummary(r.summary)}
    </div>
    <div class="foot">${cleanerBoxHtml()}<button onclick="closeModal()">${tt('common.cancel')}</button>
      <button class="primary" ${bad?'disabled':''} onclick="sndDoApply()">${tt('sprites.apply_change_s',{ops_n:ops.length})}</button></div>`;
}
async function sndDoApply(){
  const ops=sndOps();
  document.getElementById('modal').innerHTML=`<h2>${tt('sprites.writing_voice_edits')}</h2>
    <div class="mbody"><div class="progress-track"><div class="progress-fill" style="width:60%"></div></div>
      <div class="count" style="margin-top:8px">${tt('sprites.n_units',{n:ops.length})}</div></div>`;
  let r;
  try{ r=await api.post('/api/sounds/apply',{mod:state.src,ops,clear_strings_bin:clearBinOn()}); }
  catch(e){ r={error:''+e}; }
  if(r.error){ toast(tt('sprites.voice_edits_failed_error',{error:r.error}),4500); closeModal(); return; }
  closeModal();
  toast(tt('sprites.voice_change_s_written_undo_in',{ops_n:ops.length,binMsg:binMsg(r)}),4200);
  state.snd=null; state.destSnd=null; loadSounds();
}
