/* stratmap.js - Strat map tab: descr_model_strat.txt and data/models_strat

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE STRAT MAP'S MODELS - the other half of a mod's 3D art.

   BMDB mode's list is every battle model; this is every *campaign map* model:
   the generals, agents, heroes and faction symbols `descr_model_strat.txt`
   declares and the `.CAS` meshes and textures under `data/models_strat` they
   point at. The two screens do the same job on different trees, so this one is
   deliberately the same shape - a list you can search, a row per entry saying
   who uses it, and one 🧹 dialog that moves the dead weight out of the mod
   (backed up, exported, undoable) rather than deleting anything.

   Why it is worth a screen: the strat map is where unused art hides. A battle
   model nobody recruits is at least visible in the unit list; a general model
   that was replaced two versions ago is visible nowhere at all, and its 5 MB
   texture goes on shipping. Divide and Conquer carries 54 MB of files under
   models_strat that nothing in the mod names.

   `models_strat/residences` is left out of all of it - see stratmap.py: the
   game reads a faction's settlement variant out of that tree by folder, with
   nothing naming the file, so "nothing names it" would be wrong about all of it.
   ===================================================================== */
async function loadStratmap(){
  const mod=state.src;
  const job=newJob();
  main.innerHTML=`<div class="empty" style="max-width:420px;margin:60px auto">
      <div class="progress-track"><div class="progress-fill" id="jobFill" style="width:0%"></div></div>
      <div class="count" style="margin-top:8px"><b id="jobPct">0%</b>
        <span id="jobStep">${tt('stratmap.reading_s_descr_model_strat_txt',{mod:esc(mod)})}</span></div>
    </div>`;
  state.stmJob=job;
  (async()=>{ while(state.stmJob===job){
    await new Promise(r=>setTimeout(r,300));
    if(state.stmJob!==job)break;
    let p=null; try{p=await api.get('/api/progress?job='+enc(job),1);}catch(e){}
    if(state.stmJob===job&&p&&typeof p.pct==='number')jobPaint(p.pct,p.label||'');
  }})();
  try{ state.stm=await api.get(`/api/stratmap/entries?mod=${enc(mod)}&job=${enc(job)}`); }
  catch(e){ state.stmJob=null; if(stale('stratmap',mod))return;
    main.innerHTML=`<div class="empty">${tt('stratmap.couldnt_read_the_strat_map_models')}<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadStratmap()">${tt('common.retry')}</button></div>`; return; }
  finally{ state.stmJob=null; }
  if(stale('stratmap',mod))return;
  renderStratmap();
}
function renderStratmap(){
  if(!state.stm||state.stm.mod!==state.src)return loadStratmap();
  const s=state.stm;
  // 49: the panel comes off before anything rewrites `#main` under it, in both
  // branches - it is a live canvas and its parent is about to be replaced
  stmPrevDetach();
  if(!s.has_file){
    // nothing to draw and nothing to list: let the viewer go rather than leave
    // it running against an element this branch never puts back
    if(typeof v3!=='undefined'&&v3&&v3.host===STM_PREV_HOST)v3Unmount();
    count.textContent='';
    main.innerHTML=bmdbTabsHtml('data/descr_model_strat.txt')+`<div class="empty">
      <b>${esc(state.src)}</b> ${tt('stratmap.has_no_data_descr_model_strat')}</div>`;
    return;
  }
  const qq=search.value.trim().toLowerCase();
  const rows=s.entries.filter(e=>
    (!qq||e.name.toLowerCase().includes(qq)||(e.skeleton||'').toLowerCase().includes(qq)
      ||e.used_by.some(u=>u.toLowerCase().includes(qq))
      ||e.files.some(f=>f.toLowerCase().includes(qq)))
    &&(!unusedOnly.checked||e.unused));
  const nUnused=s.entries.filter(e=>e.unused).length;
  const dupes=s.count-s.names;
  count.textContent=`${rows.length}/${s.names}`;
  // 49: the 3D panel is a live canvas - detached above, not rewritten, the same
  // trick and the same reason as the BMDB browser's
  if(!stmPrevNode&&stmPrevOn())stmPrevMake('','');
  main.innerHTML=bmdbTabsHtml('data/descr_model_strat.txt')+`<div class="bmsplit" id="stmSplit">
    <div class="bmmain">
    <div class="dbhead">
      <h2>${ttN('stratmap.strat_map_model_count',s.names,{src:esc(state.src)})}</h2>
      ${tt('stratmap.referenced_by_nothing',{nUnused,nUnused2:nUnused?tt('stratmap.clean_up_strat_map_moves_them'):'',dupes:dupes?ttN('stratmap.duplicate_blocks_share_a_name',dupes):''})}
      <button class="${stmPrevNode?'on':''}" onclick="stmPrevToggle()"
        title="${ttA('stratmap.draw_a_campaign_map_model_beside')}">${tt('stratmap.view_in_3d')}</button>
    </div>
    ${rows.length?`<div class="dblist">${rows.map(stmRow).join('')}</div>`
                 :`<div class="empty">${tt('stratmap.no_strat_models_match')}</div>`}
    </div>
  </div>`;
  main.querySelectorAll('.dbrow').forEach(r=>r.onclick=()=>openStratEntry(r.dataset.name));
  stmPrevAttach();
}
function stmRow(e){
  const use=e.unused?`<span class="w-warn">${tt('common.nothing_references_it')}</span>`
    :e.mentioned_in?`<span class="count">${tt('stratmap.no_character_uses_it',{mentioned_in_lua:e.mentioned_in_lua
        ?tt('stratmap.named_by_a_lua_script'):tt('stratmap.only_named_in')})} <code>${esc(e.mentioned_in)}</code></span>`
    :`${esc(e.used_by.slice(0,4).join(', '))}${e.use_count>4?tt('stratmap.more',{use_count:e.use_count-4}):''}`;
  // 49: the entry's first mesh that the mod actually ships. An entry whose
  // .CAS files are all in a .pack, or missing, gets no button rather than a
  // button that opens a 404 - the same rule the BMDB row follows.
  const cas=(e.meshes||[])[0]||'';
  return `<div class="dbrow ${e.unused?'unused':''}${
      stmPrevRel&&cas===stmPrevRel?' showing':''}" data-name="${esc(e.name)}">
    <span class="en">${esc(e.name)}</span>
    <span class="use">${use}</span>
    ${tt('stratmap.model_texture_line',{models:ttN('stratmap.model_count',e.models),skins:ttN('stratmap.texture_count',e.skins),missing:e.missing.length?` ${tt('stratmap.not_shipped',{missing_n:e.missing.length})}`:'',x:cas?`<button class="db3d" title="${ttA('stratmap.draw_in_the_panel_beside_the',{x:esc(cas.split('/').pop())})}"
      onclick="event.stopPropagation();stmPrevOpen('${q1(esc(cas))}','${q1(esc(e.name))}')">🧊</button>`
      :'<span class="db3d" style="visibility:hidden">🧊</span>'})}
  </div>`;
}

/* ======================= THE 3D PANEL BESIDE THE LIST - 49 =================
   The BMDB browser's panel, on the other tree, and deliberately the same one:
   the same split, the same saved width, the same detach-and-reattach so that a
   keystroke in the search box does not rebuild the canvas and refetch the mesh.

   What is different is what it can be pointed at, and it is two things rather
   than one. A row's 🧊 draws the `.CAS` that entry names. The browser inside the
   panel draws any file under `data/models_strat` - which is where the
   settlements are, and a settlement is in no entry at all: the game picks it by
   level and culture out of the folder tree with nothing naming the file. That
   browser is `stratview.js`, and it was in the campaign map's side column until
   this phase, where it edited nothing and sat beside nothing else about models.

   Still ONE viewer on the page - `v3MountCas` drops whatever was showing - so
   this panel and the BMDB one cannot both be drawing. */
let stmPrevNode = null;         // the panel, or null when it is closed
let stmPrevRel = '';            // the .cas it is drawing, relative to data/
let stmPrevWhat = '';           // what to call it in the bar
const STM_PREV_HOST = 'stmV3Host';
//: On unless it has been turned off, like the BMDB panel: this tab's errand is
//: looking at a mod's campaign-map art, and a panel you have to ask for every
//: time you open a tab is one that mostly does not get opened.
const stmPrevOn = () => state.settings.stratmap_preview !== false;

function stmPrevDetach(){
  if(stmPrevNode && stmPrevNode.parentNode)
    stmPrevNode.parentNode.removeChild(stmPrevNode);
}
function stmPrevAttach(){
  const split = document.getElementById('stmSplit');
  if(!split || !stmPrevNode) return;
  split.appendChild(stmPrevNode);
  splitInstall(split, stmPrevNode, 'stratmap_prev_px', avail => Math.round(avail / 2));
  stmPrevBar();
  cmodLoad();              // the file browser, walked once per mod
  stmPrevMount();
}
//: Build the panel without painting - `renderStratmap` opens it too, and
//: calling something that re-renders from inside the render is how you get a
//: loop. Same split as `bmPrevMake`, for the same reason.
function stmPrevMake(rel, what){
  if(!stmPrevNode){
    stmPrevNode = document.createElement('aside');
    stmPrevNode.className = 'bmprev';
    stmPrevNode.id = 'stmPrevCol';
    stmPrevNode.innerHTML = `<div class="edprevbar" id="stmPrevBar"></div>
      <div class="stmbrowse" id="cmodBrowse"></div>
      <div class="edprevbody" id="${STM_PREV_HOST}"></div>`;
  }
  if(rel){ stmPrevRel = rel; stmPrevWhat = what || rel.split('/').pop(); }
}
function stmPrevOpen(rel, what){
  stmPrevMake(rel, what);
  renderStratmap();          // re-marks the row that is showing, then re-attaches
}
//: The browser's own click. The page is not re-rendered around it: the list
//: this came from is inside the panel, and rebuilding the page under a click
//: would throw that list's scroll position away on every model.
function stmPrevShowFile(rel){
  stmPrevMake(rel, rel.split('/').pop());
  cmodPaint();
  stmPrevBar();
  stmPrevMount();
  // the row that matched the old file is no longer the one showing
  main.querySelectorAll('.dbrow.showing').forEach(r => r.classList.remove('showing'));
}
function stmPrevClose(){
  if(typeof v3 !== 'undefined' && v3 && v3.host === STM_PREV_HOST) v3Unmount();
  stmPrevDetach();
  stmPrevNode = null; stmPrevRel = ''; stmPrevWhat = '';
  state.settings.stratmap_preview = false;
  api.post('/api/settings', {stratmap_preview: false});
  renderStratmap();
}
function stmPrevToggle(){
  if(stmPrevNode) return stmPrevClose();
  state.settings.stratmap_preview = true;
  api.post('/api/settings', {stratmap_preview: true});
  stmPrevMake('', '');
  renderStratmap();
}
function stmPrevBar(){
  const el = document.getElementById('stmPrevBar');
  if(!el) return;
  el.innerHTML = `<b>3D</b>
    <span class="count" title="${esc(stmPrevRel)}">${
      esc(stmPrevWhat || tt('stratmap.pick_a_model'))}</span>
    <span class="sp"></span>
    ${stmPrevRel?`<button onclick="stmPrevFull()"
      title="${ttA('stratmap.full_screen_esc_comes_back')}">⤢</button>`:''}
    <button onclick="stmPrevClose()" title="${ttA('stratmap.close_the_panel')}">✕</button>`;
}
async function stmPrevMount(){
  const host = document.getElementById(STM_PREV_HOST);
  if(!host) return;
  if(!stmPrevRel){
    host.innerHTML = `<div class="empty">${tt('stratmap.press_on_any_entry_or_pick')}</div>`;
    return;
  }
  await v3MountCas(STM_PREV_HOST, state.src, stmPrevRel);
}
function stmPrevFull(){
  const el = stmPrevNode;
  if(!el) return;
  if(document.fullscreenElement) return document.exitFullscreen();
  const go = el.requestFullscreen || el.webkitRequestFullscreen;
  if(!go){ toast(tt('common.this_browser_will_not_go_full'), 3000); return; }
  Promise.resolve(go.call(el)).catch(e =>
    toast(tt('stratmap.full_screen_was_refused',{reason:(e && e.message) || e}), 4000));
}

/* One entry, read-only: the block exactly as the file stores it, and what each
   of its lines points at. Read-only on purpose - this tab exists to find what is
   dead, and a strat model is edited by editing eight tab-aligned lines, which a
   form would make worse rather than better. The block is here so you can check
   what you are about to remove without leaving the tool. */
async function openStratEntry(name){
  const modal=document.getElementById('modal');
  modal.className='modal wide'; modal.innerHTML=`<h2>${tt('stratmap.loading')}</h2>`;
  overlay.classList.add('open');
  let r;
  try{ r=await api.get(`/api/stratmap/entry?mod=${enc(state.src)}&name=${enc(name)}`); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.innerHTML=`<h2>${tt('stratmap.strat_model')}</h2><div class="mbody w-bad">${esc(r.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  modal.innerHTML=`<h2>${tt('stratmap.strat_model')} <span class="pill">${esc(state.src)}</span></h2>
    <div class="ehead">
      <div><div class="nm" style="font-family:ui-monospace,Consolas,monospace">${esc(r.name)}</div>
        <div class="count">${tt('stratmap.line_of_data_descr_model_strat',{skeleton:r.skeleton?`${tt('stratmap.skeleton',{skeleton:esc(r.skeleton)})} `:'',line:r.line,x:r.used_by.length?tt('stratmap.used_by',{used_by:esc(r.used_by.slice(0,6).join(', ')),used_by2:r.used_by.length>6?` +${r.used_by.length-6}`:''})
                            :`<span class="w-warn">${tt('stratmap.referenced_by_nothing_2')}</span>`})}</div></div>
    </div>
    <div class="mbody">
      ${(r.characters||[]).length?`<fieldset><legend>${tt('stratmap.the_characters_it_stands_in_for')}</legend>
        <div class="count">${r.characters.map(c=>navLinkHtml({mode:'characters', name:c.key},
          `${esc(c.type)} · ${esc(c.faction)}${c.label?` <span class="count">(${esc(c.label)})</span>`:''}`,
          'ulink',tt('stratmap.open_this_block_in_agents_and'))).join(' · ')}</div></fieldset>`:''}
      <fieldset class="assetconf"><legend>${tt('stratmap.the_files_it_names')}</legend>
        <div class="flist">${r.files.map(f=>`<div class="frow">
          <span class="fp">${esc(f.rel)}</span>
          <span class="fs">${esc(f.kind)}${f.exists?'':` ${tt('stratmap.not_in_this_mod')}`}${
            // 49: a mesh the mod ships opens in the viewer from here too. The
            // card is read to decide whether a block can go, and what it draws
            // is the part of that decision nothing else could show.
            f.exists&&f.kind.indexOf('texture')<0
              ?` <button class="db3d" title="${ttA('stratmap.draw_this_model')}"
                 onclick="v3OpenCas('${q1(esc(state.src))}','${q1(esc(f.rel))}')">🧊</button>`:''}</span>
        </div>`).join('')||`<div class="count">${tt('common.none')}</div>`}</div>
        ${r.factions.length?`<div class="count" style="margin-top:6px">${tt('stratmap.texture_factions',{x:r.factions.map(f=>`<code>${esc(f)}</code>`).join(' ')})}</div>`:''}
      </fieldset>
      <fieldset><legend>${tt('stratmap.the_block_as_the_file_stores')}</legend>
        <pre class="rawblock">${esc(r.raw)}</pre></fieldset>
    </div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`;
}

/* ======================= 🧹 CLEAN UP THE STRAT MAP =======================
   Same two questions the BMDB cleanup asks, on the other tree: which declared
   models nothing references, and which files under models_strat nothing names.
   Same contract too - everything ticked is MOVED to a folder outside the mod,
   in the mod's own layout, and every rewritten file is backed up first. */
async function openStratCleanup(){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  const job=newJob();
  let a;
  try{ a=await runJob(job,tt('stratmap.clean_up_s_strat_map',{src:esc(state.src)}),
        tt('stratmap.reading_descr_model_strat_txt_every'),
        ()=>api.get(`/api/stratmap/audit?mod=${enc(state.src)}&job=${enc(job)}`)); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>${tt('common.clean_up')}</h2><div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  const was=(state.strclean&&state.strclean.a&&state.strclean.a.mod===a.mod)?state.strclean:null;
  state.strclean={a,target:(was&&was.target)||state.settings.last_stratmap_target
                                            ||state.settings.last_cleanup_target||'',
    // unused: pre-ticked, they are dead by definition. Files: NOT pre-ticked -
    // a texture with no entry naming it is a likelier false positive than a
    // block with no character naming it, and this is the tick that frees the
    // megabytes, so it is the one worth reading first.
    entries:new Set(a.unused.map(u=>u.entry)),
    orphans:new Set(),
    open:(was&&was.open)||{unused:true,orphans:true},
    plan:null};
  resetPlace();
  renderStratCleanup();
}
function renderStratCleanup(){
  const c=state.strclean,a=c.a;
  const sec=(k,title,body)=>`<div class="clsec">
      <div class="h" onclick="stmToggle('${k}')"><span>${c.open[k]?'▾':'▸'}</span>
        <b>${title}</b><span class="count" id="stc_${k}">${stmCountText(k)}</span></div>
      ${c.open[k]?`<div class="b">${body()}</div>`:''}</div>`;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('stratmap.clean_up_s_strat_map_2',{mod:esc(a.mod)})}</h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:10px">${tt('stratmap.models_in_scanned_against_game_files',{models:ttN('stratmap.model_count',a.entry_count),file:esc(a.file),game_files:ttN('stratmap.game_file_count',a.scanned.length),scripts:ttN('stratmap.lua_script_count',a.lua_files)})}</div>

      <fieldset><legend>${tt('stratmap.where_the_removed_assets_go')}</legend>
        <div class="cltarget">
          <input id="stmTarget" value="${esc(c.target)}"
            placeholder="${ttA('stratmap.e_g_d_m2tw_backups_stratmap',{mod:esc(a.mod)})}"
            oninput="state.strclean.target=this.value;stmStale()">
          <button onclick="stmPickTarget()">${tt('common.browse')}</button>
        </div>
        <div class="treebox">${tt('stratmap.stratmap_unused_removed_model_strat_txt',{mod:esc(a.mod)})}</div>
        <div class="count" style="margin-top:6px">${tt('stratmap.must_be_outside_the_mod_or')}</div>
      </fieldset>

      ${sec('unused',tt('stratmap.strat_models_nothing_references'),()=>stmUnusedBody())}
      ${sec('orphans',tt('stratmap.files_under_no_model_names',{x:esc(a.skipped_dir.split('/')[0])}),()=>stmOrphanBody())}

      ${stmLuaBox(a)}
      ${a.mentioned.length?`<div class="count">${tt('stratmap.more_model_used_by_no_character',{mentioned_n:a.mentioned.length,mentioned:a.mentioned.length===1?' is':tt('common.s_are'),x:[...new Set(a.mentioned.map(m=>m.file))].slice(0,4).map(esc).join('</code>, <code>')})}</div>`:''}
      ${a.held_file_count?`<div class="count">${tt('stratmap.file_named_by_no_model_but',{held_file_count:a.held_file_count,held_file_count2:a.held_file_count===1?' is':tt('common.s_are')})}</div>`:''}
      <div class="count"><code>${esc(a.skipped_dir)}</code> ${tt('stratmap.is_skipped_entirely_the_game_picks')}</div>
      <div id="stmPreview"></div>
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="stmPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="stmApply()">${tt('common.move_them_out')}</button>
    </div>`;
}
function stmUnusedBody(){
  const c=state.strclean,rows=c.a.unused;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('stratmap.nothing_every_model_is_referenced')}</div>`;
  return `<div class="count" style="margin-top:7px">${tt('stratmap.no_strat_model_line_in_descr')}</div>
    <div class="clbar">
      <button onclick="stmAll('entries',true)">${tt('common.select_all')}</button>
      <button onclick="stmAll('entries',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(u=>`<div class="clrow">
      <input type="checkbox" ${c.entries.has(u.entry)?'checked':''}
        onchange="stmPick('entries','${q1(esc(u.entry))}',this.checked)">
      <div class="grow"><span class="nm">${esc(u.entry)}</span>
        ${u.skeleton?`<span class="badge">${esc(u.skeleton)}</span>`:''}
        <div class="sub">${tt('stratmap.model_texture_files_named_on_disk',{models:ttN('stratmap.model_count',u.models),skins:ttN('stratmap.texture_count',u.skins),files:ttN('stratmap.file_count',u.files.length),on_disk:u.on_disk})}</div></div>
      <span class="count">${MB(u.bytes)}</span>
    </div>`).join('')}</div>`;
}
function stmOrphanBody(){
  const c=state.strclean,rows=c.a.orphans;
  if(!rows.length)return `<div class="count" style="margin-top:8px">${tt('stratmap.none_every_file_under_models_strat')}</div>`;
  return `<div class="count" style="margin-top:7px">${tt('stratmap.files_sitting_in_data_models_strat')}</div>
    <div class="clbar">
      <button onclick="stmAll('orphans',true)">${tt('common.select_all')}</button>
      <button onclick="stmAll('orphans',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(o=>`<div class="clrow">
      <input type="checkbox" ${c.orphans.has(o.rel)?'checked':''}
        onchange="stmPick('orphans','${q1(esc(o.rel))}',this.checked)">
      <div class="grow"><span class="sub" style="margin:0">${esc(o.rel)}</span></div>
      <span class="count">${MB(o.size)}</span></div>`).join('')}</div>`;
}
/* The Lua safety net, said out loud for the same reason the BMDB dialog says it:
   an M2TWEOP script names a strat model by string and nothing in the mod's .txt
   files records that, so without this pass the cleanup would remove a model the
   campaign spawns and the break would only show up in game. */
function stmLuaBox(a){
  const kept=a.lua_kept||[], scanned=a.lua_files||0;
  if(!scanned) return '';
  if(!kept.length) return `<div class="count">${tt('stratmap.read_lua_scripts_in_the_mod',{scripts:ttN('stratmap.lua_script_count_bold',scanned)})}</div>`;
  const rows=kept.slice(0,60).map(m=>`<div class="frow"><span class="fp">${esc(m.entry)}</span><span class="fs">${
    esc(m.file)}${m.in_comment?tt('stratmap.in_a_comment_and_still_protected'):''}</span></div>`).join('');
  return `<fieldset class="assetconf" style="margin-top:10px;border-color:var(--good)">
    <legend class="w-good">${tt('stratmap.protected_by_the_mods_lua_scripts')}</legend>
    <div class="count">${ttN('stratmap.models_named_by_lua_scripts',kept.length,{scripts:ttN('stratmap.lua_script_count_bold',scanned)})}</div>
    <div class="flist" style="margin-top:6px">${rows}${
      kept.length>60?`<div class="count">${tt('stratmap.and_more',{kept:kept.length-60})}</div>`:''}</div>
  </fieldset>`;
}
function stmCountText(k){
  const c=state.strclean,a=c.a;
  if(k==='unused'){
    const bytes=a.unused.reduce((n,u)=>n+(c.entries.has(u.entry)?u.bytes:0),0);
    return tt('stratmap.ticked',{entries_n:c.entries.size,unused_n:a.unused.length,x:MB(bytes)});
  }
  const bytes=a.orphans.reduce((n,o)=>n+(c.orphans.has(o.rel)?o.size:0),0);
  return tt('stratmap.ticked_2',{orphans_n:c.orphans.size,orphans_n2:a.orphans.length,x:MB(bytes)});
}
function stmCounts(){['unused','orphans'].forEach(k=>{
  const el=document.getElementById('stc_'+k); if(el)el.textContent=stmCountText(k);});}
// The checkbox already shows its own new state, so only the header count needs
// touching - that keeps ticking one of 600 rows instant.
function stmPick(key,id,on){const s=state.strclean[key]; on?s.add(id):s.delete(id);
  stmStale(); stmCounts();}
function stmAll(key,on){
  const c=state.strclean;
  const all=key==='entries'?c.a.unused.map(u=>u.entry):c.a.orphans.map(o=>o.rel);
  c[key]=new Set(on?all:[]);
  const head=document.getElementById('stc_'+(key==='entries'?'unused':key));
  if(head)head.closest('.clsec').querySelectorAll('.cllist input[type=checkbox]')
    .forEach(cb=>{cb.checked=on;});
  stmStale(); stmCounts();
}
function stmToggle(k){state.strclean.open[k]=!state.strclean.open[k];renderStratCleanup();}
function stmStale(){const b=document.getElementById('stmPreview');
  if(b&&state.strclean.plan){state.strclean.plan=null;b.innerHTML='';}}
async function stmPickTarget(){
  const r=await api.post('/api/browse_folder',{title:tt('stratmap.folder_to_move_the_unused_strat')});
  if(!r.path)return;
  state.strclean.target=r.path; stmStale(); renderStratCleanup();
  state.settings.last_stratmap_target=r.path;
  api.post('/api/settings',{last_stratmap_target:r.path});
}
function stmPayload(){
  const c=state.strclean;
  return {mod:c.a.mod,target:c.target,
    entries:[...c.entries],orphans:[...c.orphans]};
}
async function stmPreview(){
  const box=document.getElementById('stmPreview'); if(!box)return null;
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/stratmap/cleanup_plan',stmPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.strclean.plan=r;
  box.innerHTML=clPlanHtml(r); return r;
}
async function stmApply(){
  const c=state.strclean;
  if(!c.target){toast(tt('stratmap.choose_where_the_removed_assets_should'));return;}
  const r=state.strclean.plan||await stmPreview();
  if(!r)return;
  if(r.errors&&r.errors.length){toast(r.errors[0]);return;}
  if(!r.entry_deletes.length&&!r.export_count){toast(tt('common.nothing_is_ticked'));return;}
  if(!confirm(ttN('stratmap.move_strat_models_confirm',r.entry_deletes.length,{export_count:r.export_count,mod:c.a.mod,target:r.target})))return;
  const job=newJob();
  const res=await runJob(job,tt('stratmap.cleaning_up_the_strat_map'),
    tt('stratmap.copying_file_s_out_then_rewriting',{export_count:r.export_count,mod:esc(c.a.mod)}),
    ()=>api.post('/api/stratmap/cleanup_apply',{...stmPayload(),job}));
  if(res.error){toast(tt('stratmap.cleanup_failed_error',{error:res.error}));renderStratCleanup();return;}
  toast(tt('stratmap.removed_strat_models_and_files',{entry_deletes_n:res.plan.entry_deletes.length,export_count:res.plan.export_count}),5200);
  // The lists in this dialog were built from an audit taken BEFORE the cleanup,
  // so the mod on disk has changed and the answer on screen has to change with
  // it - re-run rather than leave stale rows up inviting a second tick.
  state.stm=null;
  loadStratmap();
  await openStratCleanup();
}
