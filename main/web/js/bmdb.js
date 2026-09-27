/* bmdb.js - BMDB + Sprites Editor mode: the whole battle_models.modeldb as a list

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   BMDB MODE - the whole battle_models.modeldb, not one unit's slice of it.

   The list is every entry in the mod; opening one loads it in the SAME model
   card the unit editor uses (server-side it is literally the same payload and
   the same plan engine), so an entry can be edited without going through a unit
   that happens to reference it. Entries nothing references are flagged, and
   "Clean up" moves them - and the files under unit_models nothing mentions -
   out of the mod entirely. */
async function loadBmdb(){
  const mod=state.src;
  // A real mod's modeldb is 30 MB and several seconds to read, parse and
  // cross-reference. The bar is the server's own progress, not a guess - see
  // bmdb.overview's `progress` sink.
  const job=newJob();
  main.innerHTML=`<div class="empty" style="max-width:420px;margin:60px auto">
      <div class="progress-track"><div class="progress-fill" id="jobFill" style="width:0%"></div></div>
      <div class="count" style="margin-top:8px"><b id="jobPct">0%</b>
        <span id="jobStep">${tt('bmdb.reading_s_battle_models_modeldb',{mod:esc(mod)})}</span></div>
    </div>`;
  state.bmdbJob=job;
  (async()=>{ while(state.bmdbJob===job){
    await new Promise(r=>setTimeout(r,300));
    if(state.bmdbJob!==job)break;
    // one try, no retries: a dropped poll just means the next one paints instead
    let p=null; try{p=await api.get('/api/progress?job='+enc(job),1);}catch(e){}
    if(state.bmdbJob===job&&p&&typeof p.pct==='number')jobPaint(p.pct,p.label||'');
  }})();
  try{ state.bmdb=await api.get(`/api/bmdb/entries?mod=${enc(mod)}&job=${enc(job)}`); }
  catch(e){ state.bmdbJob=null; if(stale('bmdb',mod))return;
    main.innerHTML=`<div class="empty">${tt('bmdb.couldnt_read_the_modeldb')}<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadBmdb()">${tt('common.retry')}</button></div>`; return; }
  finally{ state.bmdbJob=null; }
  if(stale('bmdb',mod))return;          // moved on while this was in flight
  renderBmdb();
}
function renderBmdb(){
  if(!state.bmdb||state.bmdb.mod!==state.src)return loadBmdb();
  const qq=search.value.trim().toLowerCase();
  const rows=state.bmdb.entries.filter(e=>
    (!qq||e.name.includes(qq)||(e.folder||'').toLowerCase().includes(qq)
      ||e.used_by.some(u=>u.toLowerCase().includes(qq)))
    &&(!unusedOnly.checked||e.unused));
  // Open by default, seeded with the first row that survived the search box -
  // done here rather than on entering the mode because this is the first point
  // at which there IS a row to show.
  if(!bmPrevNode && bmPrevOn() && rows.length) bmPrevMake(rows[0].name);
  const nUnused=state.bmdb.entries.filter(e=>e.unused).length;
  const dupBlocks=state.bmdb.count-state.bmdb.names;
  count.textContent=`${rows.length}/${state.bmdb.names}`;
  // the 3D panel is a live canvas: detached, not rewritten (see bmPrevAttach)
  bmPrevDetach();
  // 2000+ rows of HTML in one go is fine; it's the icons that are expensive and
  // there are none here.
  main.innerHTML=bmdbTabsHtml('data/unit_models/battle_models.modeldb')+`<div class="bmsplit" id="bmSplit">
    <div class="bmmain">
    <div class="dbhead">
      <h2>${tt('bmdb.battle_model_entries',{src:esc(state.src),names:state.bmdb.names})}</h2>
      ${tt('bmdb.referenced_by_nothing',{nUnused,nUnused2:nUnused?tt('bmdb.clean_up_bmdb_moves_them_out'):'',x:dupBlocks?tt('bmdb.entry_block_share_a_name_with',{dupBlocks,dupBlocks2:dupBlocks===1?'':'s',dupBlocks3:dupBlocks===1?'it':'them'}):'',x2:dupBlocks?`<button onclick="openDupes()"
        title="${ttA('bmdb.m2tw_reads_the_first_entry_with')}">${tt('bmdb.duplicates',{dupBlocks})}</button>`:''})}
      <button class="${bmPrevNode?'on':''}" onclick="bmPrevToggle()"
        title="${ttA('bmdb.draw_a_battle_model_beside_the')}">${tt('bmdb.view_in_3d')}</button>
    </div>
    ${rows.length?`<div class="dblist">${rows.map(bmdbRow).join('')}</div>`
                 :`<div class="empty">${tt('bmdb.no_entries_match')}</div>`}
    </div>
  </div>`;
  main.querySelectorAll('.dbrow').forEach(r=>r.onclick=()=>openBmdbEntry(r.dataset.name));
  bmPrevAttach();
}
function bmdbRow(e){
  const use=e.unused?`<span class="w-warn">${tt('common.nothing_references_it')}</span>`
    :e.mentioned_in?`<span class="count">${tt('bmdb.no_unit_uses_it',{mentioned_in_lua:e.mentioned_in_lua
        ?tt('bmdb.named_by_a_lua_script'):tt('bmdb.only_named_in')})} <code>${esc(e.mentioned_in)}</code></span>`
    :`${esc(e.used_by.slice(0,4).join(', '))}${e.use_count>4?tt('bmdb.more',{use_count:e.use_count-4}):''}`;
  return `<div class="dbrow ${e.unused?'unused':''}${
      bmPrevEntry===e.name?' showing':''}" data-name="${esc(e.name)}">
    <span class="en">${esc(e.name)}${e.copies>1?`<span class="badge w-warn" style="margin-left:5px"
      title="${ttA('bmdb.the_modeldb_holds_this_name_times',{copies:e.copies})}">×${e.copies}</span>`:''}</span>
    <span class="use">${use}</span>
    <span class="nums">${tt('bmdb.lod_skin',{lods:e.lods,lods2:e.lods===1?'':'s',skins:e.skins,skins2:e.skins===1?'':'s'})}</span>
    <button class="db3d" title="${ttA('bmdb.draw_this_model_in_the_panel')}"
      onclick="event.stopPropagation();bmPrevOpen('${q1(esc(e.name))}')">🧊</button>
  </div>`;
}

/* ======================= THE 3D PANEL BESIDE THE LIST =======================
   "View in 3D" opens the model viewer to the side of the browser instead of over
   it. The dialog viewer (`v3Open`) is still there and still the right thing when
   looking at ONE model is the errand; this is for the other errand - going down
   a list of two thousand entries deciding which of them is the horse.

   Same node-detach trick as the unit editor's preview column, for the same
   reason: `renderBmdb` rewrites the whole page on every keystroke in the search
   box, and the canvas must not be rebuilt (and the mesh refetched) each time. */
let bmPrevNode = null;          // the panel, or null when it is closed
let bmPrevEntry = '';           // which entry it is showing
const BM_PREV_HOST = 'bmV3Host';

function bmPrevDetach(){
  if(bmPrevNode && bmPrevNode.parentNode) bmPrevNode.parentNode.removeChild(bmPrevNode);
}
function bmPrevAttach(){
  const split = document.getElementById('bmSplit');
  if(!split || !bmPrevNode) return;
  split.appendChild(bmPrevNode);
  // Half the split by default - this mode's errand is looking AT models, not
  // reading a list with a thumbnail beside it - and draggable from there.
  splitInstall(split, bmPrevNode, 'bmdb_prev_px', avail => Math.round(avail / 2));
  bmPrevBar();
  bmPrevMount();
}
/* On unless it has been turned off, the way the unit editor's preview column
   already is. Going down a list of two thousand entries deciding which of them
   is the horse is what this mode is FOR, and a panel you have to go and ask for
   every time you open the mode is one that mostly does not get opened. */
const bmPrevOn = () => state.settings.bmdb_preview !== false;
function bmPrevClose(){
  if(v3 && v3.host === BM_PREV_HOST) v3Unmount();
  bmPrevDetach();
  bmPrevNode = null; bmPrevEntry = '';
  state.settings.bmdb_preview = false;
  api.post('/api/settings', {bmdb_preview: false});
  renderBmdb();
}
function bmPrevToggle(){
  if(bmPrevNode) return bmPrevClose();
  state.settings.bmdb_preview = true;
  api.post('/api/settings', {bmdb_preview: true});
  // seeded with the first row on screen, so the panel opens showing something
  const first = main.querySelector('.dbrow');
  bmPrevOpen(first ? first.dataset.name : '');
}
/* Build the panel without painting. Separate from `bmPrevOpen` because
   `renderBmdb` opens it too, and calling something that re-renders from inside
   the render is how you get a loop. */
function bmPrevMake(name){
  if(!bmPrevNode){
    bmPrevNode = document.createElement('aside');
    bmPrevNode.className = 'bmprev';
    bmPrevNode.id = 'bmPrevCol';
    bmPrevNode.innerHTML = `<div class="edprevbar" id="bmPrevBar"></div>
      <div class="edprevbody" id="${BM_PREV_HOST}"></div>`;
  }
  bmPrevEntry = name || bmPrevEntry;
}
function bmPrevOpen(name){
  bmPrevMake(name);
  renderBmdb();               // re-marks the row that is showing, then re-attaches
}
function bmPrevBar(){
  const el = document.getElementById('bmPrevBar');
  if(!el) return;
  el.innerHTML = `<b>3D</b>
    <span class="count" title="${esc(bmPrevEntry)}">${esc(bmPrevEntry || tt('bmdb.pick_an_entry'))}</span>
    <span class="sp"></span>
    ${bmPrevEntry?`<button onclick="openBmdbEntry('${q1(esc(bmPrevEntry))}')"
      title="${ttA('bmdb.open_this_entrys_editor')}">✎</button>
    <button onclick="bmPrevFull()" title="${ttA('bmdb.full_screen_esc_comes_back')}">⤢</button>`:''}
    <button onclick="bmPrevClose()" title="${ttA('bmdb.close_the_panel')}">✕</button>`;
}
async function bmPrevMount(){
  const host = document.getElementById(BM_PREV_HOST);
  if(!host) return;
  if(!bmPrevEntry){
    host.innerHTML = `<div class="empty">${tt('bmdb.press_on_any_row')}</div>`;
    return;
  }
  await v3Mount(BM_PREV_HOST, state.src, bmPrevEntry);
}
function bmPrevFull(){
  const el = bmPrevNode;
  if(!el) return;
  if(document.fullscreenElement) return document.exitFullscreen();
  const go = el.requestFullscreen || el.webkitRequestFullscreen;
  if(!go){ toast(tt('common.this_browser_will_not_go_full'), 3000); return; }
  Promise.resolve(go.call(el)).catch(e =>
    toast(tt('common.full_screen_was_refused') + ((e && e.message) || e), 4000));
}
// Opening an entry builds exactly the state the unit editor's model tab runs on,
// with a one-entry `models` list and no unit - so edModels(), the faction
// checklist, the folder box and "＋ New entry from this" all work unchanged.
async function openBmdbEntry(name){
  const modal=document.getElementById('modal');
  modal.className='modal wide'; modal.innerHTML=`<h2>${tt('bmdb.loading_entry')}</h2>`;
  overlay.classList.add('open');
  let r;
  try{ r=await api.get(`/api/bmdb/entry?mod=${enc(state.src)}&name=${enc(name)}`); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.innerHTML=`<h2>${tt('bmdb.battle_model')}</h2><div class="mbody w-bad">${esc(r.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  state.ed={bmdb:true,mod:state.src,unit:'',tab:'models',ov:{},rm:new Set(),added:new Set(),
    loc:{},newType:'',newDict:'',mEdits:{},newModels:[],open:{[r.model.name]:true},form:null,
    facOpen:{},folder:{},
    d:{type:'',dictionary:'',fields:[],loc:{},models:[r.model],model_names:r.model_names,
       all_factions:r.all_factions,faction_names:r.faction_names,
       unknown_factions:r.unknown_factions}};
  undoReset();
  resetPlace();
  renderBmdbEditor();
  if(state.settings.code_view){
    const e=state.ed;
    e.cv=cvCreate(bmCvHost());
    cvLoad(e.cv).then(()=>{if(state.ed===e&&e.cv)renderBmdbEditor();});
  }
}

/* ======================= CODE VIEW on the bmdb editor =====================
   The same widget again (web/js/codeview.js), pointed at the `bmdb` kind.

   This is the one record whose text carries bookkeeping nobody should be asked
   to type: a modeldb string is stored as `<length> <that many characters>`, so
   retyping a path leaves the number beside it wrong and desyncs the reader for
   everything after. The pane therefore refuses such text - naming the line and
   the number it should be - and offers ⟲ Fix lengths, which is the only kind
   with a repair. */
const bmCvEdited=()=>{const cv=state.ed&&state.ed.cv;
  return !!(cv&&cv.kind==='bmdb'&&cv.loaded&&cv.owns);};
function bmCvToggleHtml(){
  return `<button class="${state.ed.cv?'on':''}" title="${ttA('bmdb.show_this_entry_exactly_as_battle')}"
    onclick="bmCvToggle()">${tt('common.code_view')}</button>`;
}
async function bmCvToggle(){
  const e=state.ed;
  if(e.cv){cvDrop(e.cv); e.cv=null; state.settings.code_view=false;
    api.post('/api/settings',{code_view:false}); renderBmdbEditor(); return;}
  state.settings.code_view=true; api.post('/api/settings',{code_view:true});
  e.cv=cvCreate(bmCvHost());
  renderBmdbEditor();
  await cvLoad(e.cv);
  if(state.ed===e&&e.cv)renderBmdbEditor();
}
/* `name` picks which of the open editor's models the pane shows. The BMDB mode
   has exactly one and leaves it out; the unit editor has several, and its Models
   tab points a pane at whichever card is open. Everything else is the same, and
   there is only one implementation of it. */
const bmModel=name=>(state.ed.d.models||[]).find(m=>m.name===name)||state.ed.d.models[0];
function bmCvHost(name,gui,redraw){
  const e=state.ed,m=bmModel(name);
  const guiId=gui||'bmGui', paint=redraw||renderBmdbEditor;
  return {kind:'bmdb', mod:e.mod, id:m.name,
    where:'data/unit_models/battle_models.modeldb',
    // the same ModelEdit the save sends, minus the parts that are not text in
    // this entry (imported files, folder moves) - the pane can only show text
    edits:()=>{const me=(state.ed.mEdits[m.name])||{};
      return {paths:me.paths||{}, new_name:me.new_name||''};},
    adopt:cv=>{
      // The whole card is rebuilt from the re-read text - typing can add or drop
      // a faction record, which patching slot by slot would not survive. What
      // the card knows and the entry does not (who else uses it, which EDU slot
      // points here) is carried across.
      if(!cv.detail)return;
      const s=state.ed,i=(s.d.models||[]).findIndex(x=>x.name===m.name);
      if(i<0)return;
      const was=s.d.models[i];
      s.d.models[i]=Object.assign(cv.detail,
        {slots:was.slots, used_by:was.used_by, shared:was.shared});
      // box edits are now folded into the text and must not be applied twice
      const me=s.mEdits[was.name];
      if(me){me.paths={}; me.defaults={}; me.faction_paths={}; me.factions=null;}},
    refreshGui:()=>{paint(); cvBindHover(bmCvOf(m.name),document.getElementById(guiId));},
    label:el=>bmCvLabel(el,m.name), find:l=>bmCvFind(l,guiId)};
}
// whichever live view is pointed at this entry - the BMDB dialog's or the unit
// editor's Models tab
const bmCvOf=name=>{const e=state.ed;
  return (e.mcv&&e.mcvName===name)?e.mcv:e.cv;};
// The boxes already carry what they edit: a LOD mesh its span index, a texture
// its faction and kind. Both are exactly how entry_spans labels its lines.
function bmCvLabel(el,name){
  if(!el||!el.closest)return '';
  const idx=el.closest('[data-i]');
  if(idx&&idx.dataset.entry)return 'path#'+idx.dataset.i;
  const fac=el.closest('[data-fac]');
  if(fac)return tt('bmdb.fac')+fac.dataset.f+':'+fac.dataset.kind;
  // a default box stands for that kind in EVERY faction record
  const def=el.closest('[data-def]');
  if(def){
    const m=bmModel(name),k=def.dataset.kind;
    return (m.factions||[]).map(f=>tt('bmdb.fac')+f+':'+k);
  }
  const nm=el.closest('[data-rename]');
  return nm?'name':'';
}
function bmCvFind(label,guiId){
  const root='#'+(guiId||'bmGui');
  const m=/^path#(\d+)$/.exec(label);
  if(m)return [...document.querySelectorAll(`${root} [data-i="${m[1]}"]`)];
  const f=/^fac:([^:]*):(.+)$/.exec(label);
  if(f)return [...document.querySelectorAll(
    `${root} [data-f="${cssq(f[1])}"][data-kind="${cssq(f[2])}"]`)];
  if(label==='name')return [...document.querySelectorAll(`${root} [data-rename]`)];
  return [];
}

function renderBmdbEditor(){
  const e=state.ed,m=e.d.models[0];
  document.getElementById('modal').innerHTML=`
    <h2>${tt('bmdb.battle_model')} <span class="pill">${esc(e.mod)}</span></h2>
    <div class="ehead">
      <div><div class="nm" style="font-family:ui-monospace,Consolas,monospace">${esc(m.name)}</div>
        <div class="count">${tt('bmdb.lod_faction_skin',{lods_n:m.lods.length,lods:m.lods.length===1?'':'s',factions_n:m.factions.length,factions:m.factions.length===1?'':'s',used_by:m.used_by.length?tt('bmdb.used_by',{used_by_n:m.used_by.length}):`<span class="w-warn">${tt('bmdb.referenced_by_nothing_2')}</span>`})}</div></div>
    </div>
    <div class="cvsplit${e.cv?'':' off'}" style="padding:0 14px">
      <div id="bmGui"><div class="mbody" id="edBody" style="padding:0"></div></div>
      ${e.cv?`<div id="bmCodeCol" style="padding-top:12px">${cvHtml(e.cv)}</div>`:''}
    </div>
    <div class="foot">
      <span id="edDirtyNote"></span>
      ${tt('bmdb.ctrl_z_undo_ctrl_y_redo',{bmCvToggleHtml:bmCvToggleHtml(),cleanerBoxHtml:cleanerBoxHtml()})}
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="edPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="edSave()">${tt('common.save_changes')}</button>
    </div>`;
  edRenderTab();
  if(e.cv){cvWire(e.cv); cvBindHover(e.cv,document.getElementById('bmGui'));}
}

/* ---- who uses this entry ----
   Closed by default and only counted in the header: an entry a hundred units
   share would otherwise push the thing you came to edit off the screen. Opened,
   every user is a card with its own icon, and clicking one opens that unit in a
   new browser tab - so following "this model is also used by X" never costs you
   the edits in the tab you are in. */
function edUsersOpen(){ return !!(state.ed&&state.ed.usersOpen); }
function edToggleUsers(){ state.ed.usersOpen=!edUsersOpen(); edRenderTab(); }
function edUsersFilter(v){ state.ed.usersQ=v; edRenderTab(); }
function edEntryUsers(m){
  if(!m)return '';
  const all=m.used_by||[];
  const q=((state.ed.usersQ)||'').trim().toLowerCase();
  const index=Object.fromEntries(((state.data&&state.data.units)||[]).map(u=>[u.type.toLowerCase(),u]));
  const rows=all.filter(w=>!q||w.toLowerCase().includes(q));
  return `<div class="bsec edusers"><h4>
      <button class="usertog" onclick="edToggleUsers()">${tt('bmdb.used_by_2',{edUsersOpen:edUsersOpen()?'▾':'▸'})} <span class="n">${all.length}</span></button>
      ${all.length?`<span class="count">${tt('bmdb.every_unit_mount_and_file_that')}</span>`
                  :`<span class="count w-warn">${tt('bmdb.nothing_in_the_mod_references_it')}</span>`}
      ${edUsersOpen()&&all.length>8?`<input class="mini" style="margin-left:auto;max-width:200px"
        placeholder="${ttA('bmdb.filter')}" value="${esc(state.ed.usersQ||'')}"
        oninput="edUsersFilter(this.value)">`:''}</h4>
    ${edUsersOpen()&&all.length?`<div class="usergrid">${rows.map(w=>{
      const other=/^(mount|file):/.test(w);
      const u=index[w.toLowerCase()];
      return `<div class="ucell ${other?'plain':''}"
        ${other?'':tt('bmdb.onclick_openunittab_title_open_in_a',{x:q1(esc(w)),x2:esc(w)})}>
        ${other?`<div class="ic none">${tt('common.none')}</div>`
               :`<img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.ed.mod,w)}" alt="">`}
        <div class="un">${esc(u?u.name:short(w))}</div>
        <div class="ut">${esc(other?w.split(':')[0]:(u?(u.kind||u.category||w):w))}</div>
      </div>`;}).join('')||`<span class="count">${tt('common.nothing_matches')}</span>`}</div>`:''}
  </div>`;
}
const short=w=>w.replace(/^(mount|file):/,'');

/* ======================= 🛡 FACTION OWNERSHIP =======================
   A modeldb entry carries one texture record per faction, and the game reads
   the record for the faction whose army is on the field. An entry with no
   record for a faction that fields a unit drawn with it is a unit that does not
   show up right for that faction - and it is invisible in every file, because
   nothing in the EDU or the modeldb says the two lists have to agree.

   So this is that comparison, mod-wide, in two flavours a modder actually
   wants. Both are the same dialog and the same write; they differ in one
   question - which factions an entry SHOULD have a record for:

     * **Fix ownership** takes the answer from the units: every faction that
       owns a unit whose `soldier`, `officer` or `armour_ug_models` names this
       entry. Small, targeted and the honest reading of "this is missing".
     * **All factions** takes it from the roster: every faction the mod has.
       The blunt one, for a model meant to be usable by anybody. It is a much
       bigger write and the dialog says so in megabytes before you press it,
       because M2TW loads the whole modeldb into memory and that ceiling is the
       reason 🧹 Clean up BMDB exists.

   Nothing is ever REMOVED from a faction list here: the value handed to the
   planner is `current + missing`, so the write can only append. It goes through
   `edit.plan_bmdb` - the same engine as the model card's own faction checklist
   - so the backup, the undo record and the guards are the ones that already
   exist rather than new ones. */
const OWN_MODES={
  units:{icon:'🛡', title:tt('bmdb.fix_faction_ownership'),
         short:tt('bmdb.the_factions_their_units_are_owned')},
  all:  {icon:'🌐', title:tt('bmdb.give_every_model_every_faction'),
         short:tt('bmdb.every_faction_in_the_mod')}};

async function openOwnership(mode){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  const job=newJob();
  let a;
  try{ a=await runJob(job,`${OWN_MODES[mode].icon} ${OWN_MODES[mode].title}`,
        tt('bmdb.reading_battle_models_modeldb_the_faction'),
        ()=>api.get(`/api/bmdb/ownership?mod=${enc(state.src)}&mode=${enc(mode)}&job=${enc(job)}`)); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>${esc(OWN_MODES[mode].title)}</h2>
    <div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  state.own={a,mode,
    // Ticked by default: every row is a record the entry is missing, which is a
    // fact about the file rather than a judgement - the same reason the BMDB
    // cleanup pre-ticks the entries nothing references.
    picked:new Set(a.rows.map(r=>r.entry)),
    plan:null};
  resetPlace();
  renderOwnership();
}

/* Switching mode re-runs the scan rather than filtering the one already here:
   the two ask different questions of the mod, and half an answer to the other
   one is worse than making you wait three seconds. */
function ownMode(mode){ if(state.own&&state.own.mode!==mode) openOwnership(mode); }

function renderOwnership(){
  const o=state.own,a=o.a,def=OWN_MODES[o.mode];
  const grow=a.modeldb_bytes?a.bytes/a.modeldb_bytes:0;
  const heavy=grow>=0.25;                 // a quarter bigger is worth stopping for
  document.getElementById('modal').innerHTML=`
    <h2>${def.icon} ${esc(def.title)} <span class="pill">${esc(a.mod)}</span></h2>
    <div class="mbody">
      <div class="ownmodes">
        ${Object.entries(OWN_MODES).map(([k,d])=>`<button class="${k===o.mode?'on':''}"
          onclick="ownMode('${k}')">${d.icon} ${esc(d.title)}</button>`).join('')}
      </div>
      <div class="count" style="margin:8px 0 10px">${tt('bmdb.every_entry_gets_a_texture_record',{short:esc(def.short)})}</div>

      ${!a.has_roster?`<div class="warnbox">${tt('bmdb.this_mod_has_no_readable_descr')}</div>`:''}

      <div class="sum">
        <div class="srow shead"><span class="sicon">${def.icon}</span><span class="stext">
          ${tt('bmdb.of_entries_are_short_of_a',{row_count:a.row_count,entry_count:a.entry_count})}</span></div>
        <div class="srow"><span class="sicon">+</span><span class="stext">
          <b>${a.added_records}</b> ${tt('bmdb.record_to_add_across_faction_slot',{added_records:a.added_records===1?'':'s',slot_count:a.slot_count,slot_count2:a.slot_count===1?'':'s'})}</span></div>
        <div class="srow ${heavy?'warn':''}"><span class="sicon">${heavy?'!':'📦'}</span>
          <span class="stext">${tt('bmdb.battle_models_modeldb_grows_by_about',{x:MB(a.bytes),x2:a.modeldb_bytes?tt('bmdb.from_to_its_size',{x:MB(a.modeldb_bytes),x2:MB(a.modeldb_bytes+a.bytes),grow:(1+grow).toFixed(1)}):'',x3:heavy?tt('bmdb.m2tw_loads_the_whole_file_into'):'.'})}</span></div>
        ${a.covered?`<div class="srow"><span class="sicon">✓</span><span class="stext">
          ${tt('bmdb.entr_already_ha_every_record',{covered:a.covered,covered2:a.covered===1?'y':'ies',covered3:a.covered===1?'s':'ve',mode:o.mode==='all'?tt('bmdb.the_roster_asks_for'):tt('bmdb.their_units_need')})}</span></div>`:''}
        ${a.no_unit?`<div class="srow"><span class="sicon">·</span><span class="stext">
          ${tt('bmdb.entr_drawn_for_no_unit_at',{no_unit:a.no_unit,no_unit2:a.no_unit===1?tt('bmdb.y_is'):tt('bmdb.ies_are'),x:o.mode==='units'?tt('bmdb.so_this_mode_has_nothing_to')
          +(a.no_unit===1?'it':'them'):''})}</span></div>`:''}
        ${a.no_records?`<div class="srow warn"><span class="sicon">!</span><span class="stext">
          ${tt('bmdb.entr_no_texture_record_at_all',{no_records:a.no_records,no_records2:a.no_records===1?tt('bmdb.y_has'):tt('bmdb.ies_have')})}</span></div>`:''}
      </div>

      ${a.unknown_ownership.length?`<fieldset class="assetconf" style="margin-top:10px">
        <legend class="w-warn">${tt('bmdb.ownership_tokens_that_are_not_faction')}</legend>
        <div class="count">${tt('bmdb.these_appear_on_a_units_ownership')}</div>
        <div class="flist" style="margin-top:6px">${a.unknown_ownership.map(x=>`<div class="frow">
          <span class="fp">${esc(x.faction)}</span>
          <span class="fs">${tt('bmdb.unit',{count:x.count,count2:x.count===1?'':'s',units:esc(x.units.join(', ')),x:x.count>x.units.length?' …':''})}</span></div>`).join('')}</div>
      </fieldset>`:''}

      ${a.row_count?`<div class="clbar" style="margin-top:12px">
          <button onclick="ownAll(true)">${tt('common.select_all')}</button>
          <button onclick="ownAll(false)">${tt('common.none_2')}</button>
          <span class="count" id="ownCount">${ownCountText()}</span></div>
        <div class="cllist">${a.rows.map(ownRowHtml).join('')}</div>
        ${a.row_count>a.rows.length?`<div class="count">${tt('bmdb.and_more_not_listed_select_all',{n:a.row_count-a.rows.length})}</div>`:''}`
       :`<div class="count" style="margin-top:10px">${tt('bmdb.nothing_to_add_every_entry_already')} `
        +esc(def.short)+'. 🎉</div>'}
      <div id="ownPreview"></div>
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="ownPreview()" ${a.row_count?'':'disabled'}>${tt('common.probe')}</button>
      <button class="primary" onclick="ownApply()" ${a.row_count&&a.has_roster?'':'disabled'}>
        ${tt('bmdb.add_the_missing_records')}</button>
    </div>`;
}
function ownRowHtml(r){
  const o=state.own;
  return `<div class="clrow">
    <input type="checkbox" ${o.picked.has(r.entry)?'checked':''}
      onchange="ownPick('${q1(esc(r.entry))}',this.checked)">
    <div class="grow"><span class="nm">${esc(r.entry)}</span>
      <span class="badge">${tt('bmdb.has',{have:r.have})}</span>
      <div class="sub">+ ${r.missing.map(f=>`<code>${esc(f)}</code>`).join(' ')}</div>
      ${r.used_by.length?`<div class="sub">${tt('bmdb.drawn_for',{used_by:esc(r.used_by.slice(0,4).join(', ')),used_by2:r.used_by.length>4?tt('bmdb.more_2',{used_by:r.used_by.length-4}):''})}</div>`
       :`<div class="sub count">${tt('bmdb.no_unit_is_drawn_with_it')}</div>`}
    </div>
    <span class="count">+${MB(r.bytes)}</span></div>`;
}
function ownCountText(){
  const o=state.own;
  const bytes=o.a.rows.reduce((n,r)=>n+(o.picked.has(r.entry)?r.bytes:0),0);
  return tt('bmdb.ticked_about',{picked_n:o.picked.size,row_count:o.a.row_count,x:MB(bytes)});
}
// Only the header count is repainted on a tick - the checkbox already shows its
// own new state, and a mod can have 1500 rows here.
function ownPick(name,on){
  on?state.own.picked.add(name):state.own.picked.delete(name);
  ownStale();
  const el=document.getElementById('ownCount'); if(el)el.textContent=ownCountText();
}
function ownAll(on){
  const o=state.own;
  // `null` means "every entry the server finds", which is not the same as the
  // rows on screen when the list was capped - that is the whole reason the
  // payload can say "all" rather than naming them.
  o.picked=new Set(on?o.a.rows.map(r=>r.entry):[]);
  o.allRows=on;
  document.querySelectorAll('.cllist input[type=checkbox]').forEach(cb=>{cb.checked=on;});
  ownStale();
  const el=document.getElementById('ownCount'); if(el)el.textContent=ownCountText();
}
function ownStale(){const b=document.getElementById('ownPreview');
  if(b&&state.own.plan){state.own.plan=null;b.innerHTML='';}}
function ownPayload(){
  const o=state.own;
  const all=o.allRows!==false&&o.picked.size===o.a.rows.length;
  return {mod:o.a.mod, mode:o.mode,
    // Everything ticked and the list was not narrowed: send no `entries` at all,
    // so the server works on every entry it finds rather than on the capped page.
    ...(all?{}:{entries:[...o.picked]})};
}
async function ownPreview(){
  const box=document.getElementById('ownPreview'); if(!box)return null;
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/bmdb/ownership_plan',ownPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.own.plan=r;
  box.innerHTML=ownPlanHtml(r); return r;
}
/* The edit planner reports one line per entry, and this is a job that touches a
   thousand of them - so the plan box shows the shape and a sample rather than
   every line. The full list is in `config/server.log`, which is where a job this
   size belongs anyway. */
function ownPlanHtml(r){
  const p=r.plan||{},ch=p.changes||[];
  const li=(cls,items)=>(items||[]).slice(0,12).map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':'!'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">✎</span><span class="stext">${tt('common.what_this_writes')}</span></div>
    <div class="srow"><span class="sicon">·</span><span class="stext">
      <b>${r.entries||0}</b> ${tt('bmdb.entr_in_data_unit_models_battle',{x:r.entries===1?'y':'ies'})}</span></div>
    ${ch.slice(0,8).map(x=>`<div class="srow"><span class="sicon">·</span>
      <span class="stext">${esc(x)}</span></div>`).join('')}
    ${ch.length>8?`<div class="srow"><span class="sicon">·</span><span class="stext">
      <i>${tt('bmdb.and_more_listed_in_full_in',{ch:ch.length-8})}</i>
      </span></div>`:''}
    ${li('warn',p.warnings)}${li('bad',p.errors)}</div>`;
}
async function ownApply(){
  const o=state.own,a=o.a;
  const r=o.plan||await ownPreview();
  if(!r)return;
  const p=r.plan||{};
  if((p.errors||[]).length){toast(p.errors[0]);return;}
  if(!r.entries){toast(tt('bmdb.nothing_to_add'));return;}
  const bytes=a.rows.reduce((n,x)=>n+(o.picked.has(x.entry)?x.bytes:0),0);
  if(!confirm(tt('bmdb.add_the_missing_faction_texture_records',{x:r.entries})+
      tt('bmdb.entr_of',{x:r.entries===1?'y':'ies',mod:a.mod})+
      tt('bmdb.each_new_record_is_a_clone')+
      tt('bmdb.texture_nothing_is_removed')+
      tt('bmdb.battle_models_modeldb_grows_by_roughly',{x:MB(bytes)})+
      tt('bmdb.it_is_backed_up_first_log')))return;
  const job=newJob();
  const res=await runJob(job,`${OWN_MODES[o.mode].icon} ${esc(OWN_MODES[o.mode].title)}`,
    tt('bmdb.adding_the_missing_faction_records_to',{x:r.entries,x2:r.entries===1?'y':'ies',mod:esc(a.mod)}),
    ()=>api.post('/api/bmdb/ownership_apply',{...ownPayload(),job}));
  if(res.error){toast(tt('bmdb.could_not_add_the_records')+res.error);renderOwnership();return;}
  toast(tt('bmdb.entr_given_their_missing_faction',{res:res.entries,res2:res.entries===1?'y':'ies'})+
        tt('bmdb.record_s_undo_in_log'),5200);
  // The list was built from a scan taken BEFORE the write, so it now describes a
  // file that has changed - re-run rather than leave rows up inviting a second go.
  state.bmdb=null;
  loadBmdb();
  await openOwnership(o.mode);
}
