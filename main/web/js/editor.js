/* editor.js - Unit Editor mode: EDU fields, identity, model entries, textures

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= UNIT EDITOR (edit mode) =======================
   Edits one mod in place: EDU fields, the localised name/description, the
   battle_models.modeldb entries the unit uses (including creating a new entry
   from an existing one), and deleting the unit. Every apply goes through the
   same backup + log as a transfer, so 🕑 Log → Undo reverts it. */
const enc=encodeURIComponent;
const modRoot=n=>(state.mods.find(m=>m.name===n)||{}).root||'';
// A native dialog hands back an absolute path; show it as the mod-relative one
// the game actually uses (the server accepts either).
function relInMod(p){
  const root=modRoot(state.src); if(!p||!root)return p||'';
  const norm=s=>s.replace(/\\/g,'/').replace(/\/+$/,'');
  const r=norm(root)+'/data/', s=norm(p);
  return s.toLowerCase().startsWith(r.toLowerCase())?s.slice(r.length):s;
}

async function openEditor(type){
  activity(tt('editor.opened_unit'),`${type} in ${state.src}`);
  const modal=document.getElementById('modal');
  modal.className='modal wide'; modal.innerHTML=`<h2>${tt('editor.loading_unit')}</h2>`;
  overlay.classList.add('open');
  let d;
  try{ d=await api.get(`/api/edit/unit?mod=${enc(state.src)}&type=${enc(type)}`); }
  catch(e){ modal.innerHTML=`<h2>${tt('editor.unit_editor')}</h2><div class="mbody w-bad">${esc(errText(e))}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  if(d.error){ modal.innerHTML=`<h2>${tt('editor.unit_editor')}</h2><div class="mbody w-bad">${esc(d.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  state.ed={mod:state.src,unit:type,d,tab:'identity',ov:{},rm:new Set(),
            loc:Object.assign({},d.loc),newType:'',newDict:'',
            mEdits:{},newModels:[],open:{},form:null,removeOldIcons:false,added:new Set(),
            // replacement card / info card picked off disk, applied on save
            cardSrc:'',infoSrc:'',
            // per-entry UI state: which faction has its "unique textures" panel
            // open, and the last /api/edit/model_folder answer for its folder box
            facOpen:{},folder:{},
            // the Code View pane on the EDU fields tab (null until it's opened),
            // and the modeldb one on the Models tab - one card at a time
            cv:null,mcv:null,mcvName:'',
            // the Compare tab: a SECOND unit loaded beside this one, with edits
            // of its own that Save writes as a second, independent unit save
            cmp:null,cmpQ:'',cmpSame:false,
            // the Recruitment tab: every building line that trains this unit,
            // fetched the first time the tab is opened - see edrecruit.js
            rec:null,
            ug:null};      // the armour-tier ＋ menu, closed
  undoReset();
  resetPlace();            // a different unit starts at the top, not where the last one sat
  renderEditor();
  // the code pane is remembered: whoever works with it wants it on every unit,
  // and it is fetched after the first paint so it never delays the dialog
  if(state.settings.code_view){
    const e=state.ed;
    e.cv=cvCreate(edCvHost());
    cvLoad(e.cv).then(()=>{if(state.ed===e&&e.tab==='fields')edRenderTab();});
  }
}
// Every unit opens in its own browser tab, so you can follow "this model is also
// used by X" without losing the edits in the tab you came from.
function openUnitTab(type){
  window.open(`/?mod=${enc(state.ed?state.ed.mod:state.src)}&edit=${enc(type)}`,'_blank');
}
// A model's users are unit types, plus "mount:<name>" / "file:<name>" referrers
// which are not units and so have no editor to open.
function userLink(name){
  return /^(mount|file):/.test(name) ? `<span class="count">${esc(name)}</span>`
    : `<a class="ulink" onclick="openUnitTab('${q1(esc(name))}')">${esc(name)}</a>`;
}
function edDirty(){
  const e=state.ed; if(!e)return false;
  return !!(Object.keys(e.ov).length||e.rm.size||e.newModels.length||
            edModelEdits().length||e.newType||e.newDict||edCvUserEdited()||
            // a staged card / info card is a save of its own: it writes no EDU
            // line, so nothing else here notices it, and leaving it out is what
            // made "Replace for every faction" end in "Nothing to save"
            e.cardSrc||e.infoSrc||
            (e.tierEdit&&Object.keys(e.tierEdit).length)||
            JSON.stringify(e.loc)!==JSON.stringify(e.d.loc));
}
// Has the unit's block been hand-edited in Code View? `base` is what the text
// pane last parsed cleanly, `pristine` what the file said when it opened. Note
// this stays true while the pane shows an error: the last GOOD text is still
// the one a save would write, and dropping it silently back to the file's
// version would throw away work the user can still see on screen. What an error
// does stop is the save itself - see edCvBlocked().
// Keyed on the kind because bmdb mode shares `state.ed`: its pane holds a
// modeldb entry, which goes to the save as `raw_entry` on the model edit, never
// as the unit block's `raw_block`.
function edCvEdited(){
  const cv=state.ed&&state.ed.cv;
  return !!(cv&&cv.kind==='edu'&&cv.loaded&&cv.base!==cv.pristine);
}
/* …and the narrower question the DIALOG asks: is there anything to save.

   The pane lines the block up the moment it opens (cvAutoTidy), so opening it
   already makes `edCvEdited` true - and a view toggle that says "unsaved
   changes" and offers to throw work away on close is a lie about what the user
   did. The tool's own layout pass is remembered as `cv.auto`, so this can tell
   the two apart: it is not a reason to save on its own, and the moment there IS
   one the tidied text is what gets written. */
function edCvUserEdited(){
  const cv=state.ed&&state.ed.cv;
  if(!cv||cv.kind!=='edu'||!cv.loaded)return false;
  return cv.base!==cv.pristine&&cv.base!==cv.auto;
}
// The text pane can't be read, so neither Probe nor Save may run: they would
// act on the last good text while the screen shows something else.
function edCvBlocked(){
  const cv=state.ed&&state.ed.cv;
  if(!cv||!cv.err)return '';
  return tt('editor.code_view_unreadable_fix',{err:cv.err});
}
/* ---- what each touched bmdb entry sends ----
   Texture paths go by faction + kind, never by span index: ticking a faction on
   or off renumbers every texture slot in the entry, so an index captured by the
   page would land on the wrong one. Meshes keep using indices - those are stable. */
function edModelEdits(){
  const e=state.ed;
  // an entry hand-edited in Code View is a change even if no box was touched
  const cvName=(e.cv&&e.cv.kind==='bmdb'&&e.cv.owns)?e.cv.id:'';
  const names=Object.keys(e.mEdits);
  if(cvName&&!names.includes(cvName))names.push(cvName);
  return names.map(name=>{
    const me=e.mEdits[name]||{};
    if(!me._touched&&name!==cvName)return null;
    const m=e.d.models.find(x=>x.name===name); if(!m)return null;
    /* Which faction slots are sent as OVERRIDES, and which are left to follow
       the default. Getting this wrong is invisible in the form and total in the
       file: the server writes a faction's override in preference to the default,
       so a faction sent as an override is a faction the default cannot reach.

       "Anything that differs from the default is an override" was the rule, and
       it compared against the default AS JUST TYPED. So editing the default box
       - the one that says "used by every faction unless it has its own" - made
       every faction differ from it by definition, and all of them were sent
       pinned to the value they already had. The new default was written and then
       overridden 29 times by the old one: the boxes reverted on save, while the
       LOD meshes (which have no override layer, just indexed paths) stayed. That
       is the shape the bug was reported in.

       A faction is an override when one of two things is true, and neither of
       them is about the value being typed right now:
         * its own box was edited this session - a value typed against ONE
           faction is that faction's, whatever it equals; or
         * it already had a value of its own on disk, meaning it differed from
           the default IT WAS FOLLOWING - the original one, not the new one.
       Everything else follows the default, which is what makes editing the
       default box reach exactly the factions that were sharing it. */
    const v=edTexView(m), kinds=edKinds(m), faction_paths={};
    edFacs(m).forEach(f=>{
      const o={},cur=v.facs[f]||{},own=(me.faction_paths||{})[f]||{},was=m.textures[f]||{};
      kinds.forEach(k=>{
        if(!cur[k])return;
        if(k in own){o[k]=cur[k];return;}
        if(was[k]&&was[k]!==m.texture_defaults[k])o[k]=cur[k];
      });
      if(Object.keys(o).length)faction_paths[f]=o;
    });
    return {entry:name,new_name:me.new_name||'',paths:me.paths||{},copies:me.copies||[],
      // the entry as hand-edited in Code View; everything above applies on top
      raw_entry:name===cvName?e.cv.base:'',
      imports:(me.imports||[]).map(x=>({src:x.src,dest_dir:x.dest_dir})),
      defaults:v.defs,faction_paths,factions:me.factions||null,
      move_dir:me.move_dir||'',move_shared:!!me.move_shared};
  }).filter(Boolean);
}
function edPayload(extra){
  const e=state.ed;
  const locChanged=JSON.stringify(e.loc)!==JSON.stringify(e.d.loc);
  return Object.assign({mod:e.mod,unit:e.unit,new_type:e.newType,new_dictionary:e.newDict,
    // a block edited as text replaces the file's; the boxes still apply on top
    raw_block:edCvEdited()?e.cv.base:'',
    field_overrides:e.ov,remove_fields:[...e.rm],loc:locChanged?e.loc:null,
    model_edits:edModelEdits(),new_models:e.newModels,
    card_src:e.cardSrc||'',info_src:e.infoSrc||'',
    // which faction folders that card reaches; empty = every one of them
    card_folders:edIcoPayloadFolders('cardSrc'),
    info_folders:edIcoPayloadFolders('infoSrc'),
    // absent (not "") unless the user touched it - clearing a tier and never
    // setting one are different requests, and the server tells them apart
    tier:(e.tierEdit&&'tier' in e.tierEdit)?e.tierEdit.tier:null,
    tier_variant:(e.tierEdit&&'tier_variant' in e.tierEdit)?e.tierEdit.tier_variant:null,
    remove_old_icons:!!e.removeOldIcons},extra||{});
}
function renderEditor(){
  const e=state.ed,d=e.d;
  // the id is for the Recruitment tab's count badge, which changes without the
  // tab bar being redrawn - see edRecPaintTab
  const tab=(k,label)=>`<button id="edTab_${k}" class="${e.tab===k?'on':''}"
    onclick="edTab('${k}')">${label}</button>`;
  // The preview column is a live WebGL canvas holding a mesh that took a moment
  // to fetch, so it is DETACHED here rather than destroyed, and appended again
  // below - see edPrevAttach. Rewriting the modal around it would take the
  // context with it and reload the model on every tab switch.
  edPrevDetach();
  document.getElementById('modal').innerHTML=`
    <h2>${tt('editor.edit_unit',{mod:esc(e.mod),x:edPrevOn()?'':`<button class="edprevon" onclick="edPrevShow()"
        title="${ttA('editor.draw_this_units_battle_model_beside')}">${tt('editor.3d_preview')}</button>`})}</h2>
    <div class="edsplit" id="edSplit">
     <div class="edmain">
      <div class="ehead">
        <img onerror="iconRetry(this)" src="${iconUrl(e.mod,e.unit)}">
        <div><div class="nm">${esc(e.loc.name||d.type)}${
          d.eop?`<span class="badge eop" style="margin-left:6px;vertical-align:middle">${tt('editor.eop')}</span>`:''}</div>
          <div class="count">${ttN('editor.dictionary_model_entries',d.models.length,{type:esc(d.type),dictionary:esc(d.dictionary)})}</div>
          <div class="count">${d.eop
            ? tt('editor.m2tweop_unit_saves_are_written_to',{eop_file:esc(d.eop_file)})
            : tt('editor.defined_in_data_export_descr_unit')}</div></div>
      </div>
      <div class="tabs">${tab('identity',tt('editor.identity_text'))}${tab('fields',tt('editor.edu_fields'))}
        ${tab('models',tt('editor.battle_models_bmdb'))}${tab('recruit',edRecTabLabel())}${
        tab('compare',tt('editor.compare'))}</div>
      <div class="mbody" id="edBody"></div>
     </div>
    </div>
    <div class="foot">
      <button class="danger" onclick="edDeleteDialog()">${tt('editor.delete_unit')}</button>
      <span id="edDirtyNote"></span>
      ${tt('editor.ctrl_z_undo_ctrl_y_redo',{x:state.bldReturn?`<button onclick="backToBuilding()"
        title="${ttA('editor.return_to_the_building_editor_exactly')}">← ${esc(state.bldReturn.label)}</button>`:'',cleanerBoxHtml:cleanerBoxHtml()})}
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="edPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="edSave()">${tt('common.save_changes')}</button>
    </div>`;
  edRenderTab();
  edPrevAttach();
}
function edTab(t){state.ed.tab=t;renderEditor();}

/* ======================= THE 3D PREVIEW COLUMN =======================
   The model viewer, docked to the right of the unit editor and ON by default.

   Reaching a unit's model used to mean leaving the unit: BMDB mode, find the
   entry among two thousand, open it, look, come back. The entry names are
   already here on the Models tab, and the viewer already knows how to paint
   into any element it is handed (`v3Mount`), so the model belongs beside the
   fields that decide which model it is.

   Three things this column is careful about:

     * **the canvas outlives a re-render.** `renderEditor` replaces the whole
       modal on every tab switch. The column is detached first and appended
       again after, so the WebGL context, the uploaded buffers and the mesh
       survive - otherwise every tab switch refetched a 30 MB model.
     * **one viewer at a time.** `v3Mount` drops whatever was mounted, so
       opening the full-screen viewer or the BMDB side panel takes this one
       down rather than leaving two GL contexts and two animation loops running.
     * **minimised is paused, not unloaded.** Folding the column away stops the
       draw loop and leaves everything on the GPU, so unfolding is instant. */

// the column itself, kept across re-renders (see above). Null when hidden.
let edPrevNode = null;
const ED_PREV_HOST = 'edV3Host';

// On unless it has been turned off, because a preview you have to go and ask
// for is the trip to BMDB mode again with fewer steps.
const edPrevOn = () => state.settings.model_preview !== false;
/* Which of the unit's battle-model entries are worth offering.

   A unit that carries `armour_ug_models` is DRAWN from that list, one model per
   armour level, and the model on its `soldier` line is never seen - Uruk-hai
   Bodyguards names `heavy_uruk_sword` there and puts `isengard_bodyguard` in
   both upgrade slots, so offering the first is offering a model this unit never
   appears in. It is dropped, and the officers, the upgrade models and the mount
   are left. A unit with no upgrade list is the other way round: the soldier
   line IS what gets drawn, so it stays.

   The test is per model, not per unit, because the same entry is often in both
   places (Uruk Bodyguard's `mordor_uruk_bodyguards` is the soldier AND upgrade
   1) - an entry earns its place by any slot that is not the soldier line. */
const edPrevEntries = () => {
  const all = ((state.ed && state.ed.d && state.ed.d.models) || []).filter(m => m && !m.missing);
  const upgraded = all.some(m => (m.slots || []).some(x => x.indexOf('armour_ug_models') === 0));
  const keep = upgraded
    ? all.filter(m => !((m.slots || []).length && m.slots.every(x => x === 'soldier')))
    : all;
  return (keep.length ? keep : all).map(m => m.name);
};
function edPrevEntry(){
  const list = edPrevEntries(), want = state.ed && state.ed.prevEntry;
  return (want && list.includes(want)) ? want : (list[0] || '');
}

function edPrevDetach(){
  if(edPrevNode && edPrevNode.parentNode) edPrevNode.parentNode.removeChild(edPrevNode);
}
function edPrevAttach(){
  const split = document.getElementById('edSplit');
  if(!split) return;
  if(!edPrevOn() || !state.ed) return edPrevDrop();
  if(!edPrevNode){
    edPrevNode = document.createElement('aside');
    edPrevNode.className = 'edprev' + (state.ed.prevMin ? ' min' : '');
    edPrevNode.id = 'edPrevCol';
    edPrevNode.innerHTML = `<div class="edprevbar" id="edPrevBar"></div>
      <div class="edprevbody" id="${ED_PREV_HOST}"></div>`;
  }
  split.appendChild(edPrevNode);
  // Folded to its bar, the column is as wide as that bar and a divider would be
  // dragging nothing - `.edprev.min` sizes itself, so the width is not ours.
  if(state.ed.prevMin) edPrevNode.style.flex = '';
  else splitInstall(split, edPrevNode, 'v3_dock_px', 340);
  edPrevBar();
  edPrevMount();
}
function edPrevDrop(){
  if(typeof v3 !== 'undefined' && v3 && v3.host === ED_PREV_HOST) v3Unmount();
  edPrevDetach();
  edPrevNode = null;
}

// The bar only - never the body, which is the canvas.
function edPrevBar(){
  const el = document.getElementById('edPrevBar');
  if(!el) return;
  const list = edPrevEntries(), cur = edPrevEntry(), min = !!(state.ed && state.ed.prevMin);
  el.innerHTML = `<b>3D</b>
    ${list.length > 1
      ? `<select title="${ttA('editor.which_of_this_units_battle_model')}"
           onchange="edPrevPick(this.value)">${list.map(n =>
           `<option value="${esc(n)}"${n===cur?' selected':''}>${esc(n)}</option>`).join('')}</select>`
      : `<span class="count" title="${esc(cur)}">${esc(cur || tt('editor.no_entry'))}</span>`}
    <span class="sp"></span>
    <button onclick="edPrevFull()" title="${ttA('editor.full_screen_esc_comes_back')}">&#10530;</button>
    <button onclick="edPrevMin()" title="${min?tt('editor.unfold_the_preview'):tt('editor.fold_the_preview_away')}"
      >${min?'&#9656;':'&#9662;'}</button>
    <button onclick="edPrevHide()" title="${ttA('editor.hide_the_preview_the_button_at')}">&#10005;</button>`;
}

async function edPrevMount(){
  const host = document.getElementById(ED_PREV_HOST);
  if(!host) return;
  if(state.ed && state.ed.prevMin){ v3Pause(true); return; }
  const entry = edPrevEntry();
  if(!entry){
    if(v3 && v3.host === ED_PREV_HOST) v3Unmount();
    host.innerHTML = `<div class="empty">${tt('editor.this_unit_names_no_battle_model')}</div>`;
    return;
  }
  v3Pause(false);
  await v3Mount(ED_PREV_HOST, state.ed.mod || state.src, entry);
}

function edPrevPick(name){
  if(!state.ed) return;
  state.ed.prevEntry = name;
  edPrevMount();
}
function edPrevMin(){
  if(!state.ed) return;
  state.ed.prevMin = !state.ed.prevMin;
  if(edPrevNode) edPrevNode.classList.toggle('min', !!state.ed.prevMin);
  // Fold and unfold in place rather than re-rendering (the canvas is live), so
  // the width and its grab bar are put right here: `.edprev.min` sizes itself
  // and the inline width splitInstall wrote would otherwise beat it.
  const bar = document.querySelector('#edSplit > .splitbar');
  if(state.ed.prevMin){
    if(edPrevNode) edPrevNode.style.flex = '';
    if(bar) bar.style.display = 'none';
  }else{
    if(bar) bar.style.display = '';
    edPrevAttach();
  }
  edPrevBar();
  edPrevMount();
}
async function edPrevHide(){
  edPrevDrop();
  state.settings.model_preview = false;
  api.post('/api/settings', {model_preview:false});
  renderEditor();
}
async function edPrevShow(){
  state.settings.model_preview = true;
  api.post('/api/settings', {model_preview:true});
  renderEditor();
}
/* Full screen is the browser's own, not a bigger box inside the dialog: the
   model is the whole point of going full screen, and the modal is most of the
   window already. Esc leaves it, which is what everyone expects. The canvas
   needs nothing done to it - v3Draw sizes itself from the element every frame. */
function edPrevFull(){
  const el = edPrevNode || document.getElementById('edPrevCol');
  if(!el) return;
  if(document.fullscreenElement){ document.exitFullscreen(); return; }
  if(state.ed && state.ed.prevMin) edPrevMin();          // nothing to look at folded
  const go = el.requestFullscreen || el.webkitRequestFullscreen;
  if(!go){ toast(tt('common.this_browser_will_not_go_full'), 3000); return; }
  Promise.resolve(go.call(el)).catch(e =>
    toast(tt('editor.full_screen_refused_because',{why:(e && e.message) || e}), 4000));
}
function edRenderTab(){
  const e=state.ed,b=document.getElementById('edBody');
  // Editing anything re-renders the whole tab, and replacing innerHTML throws
  // every scroll position back to the top - both the dialog's and the EDU field
  // list's own box. Ticking a faction 40 rows down must leave you looking at it,
  // not at the top of the unit, so both are put back afterwards.
  const modal=document.getElementById('modal');
  const wasModal=modal?modal.scrollTop:0;
  const fields=document.getElementById('allFields');
  const wasFields=fields?fields.scrollTop:0;
  const gbody=document.getElementById('gfBody');
  const wasG=gbody?gbody.scrollTop:0;
  b.innerHTML=(e.tab==='identity'?edIdentity():e.tab==='fields'?edFields()
              :e.tab==='recruit'?edRecTab()
              :e.tab==='compare'?edCompare():edModels())
    // bmdb mode edits an entry with no unit around it, so "who uses this?" has
    // nowhere else to live - it goes at the bottom of the entry itself
    +(e.bmdb?edEntryUsers(e.d.models[0]):'')
    +'<div id="edPreview"></div>';
  // keep the last preview visible across cosmetic re-renders (tab switch, expanding
  // an entry) - flagged as stale once anything has been edited since it was made
  if(e.plan)document.getElementById('edPreview').innerHTML=edPlanHtml(e.plan,e.planStale);
  if(e.tab==='fields')edWireFields();
  if(e.tab==='identity')edWireIdentity();
  if(e.tab==='models')edWireModels();
  if(e.tab==='compare')edWireCompare();
  if(e.tab==='recruit')edWireRecruit();
  const nowFields=document.getElementById('allFields');
  if(nowFields&&wasFields)nowFields.scrollTop=wasFields;
  const nowG=document.getElementById('gfBody');
  if(nowG&&wasG)nowG.scrollTop=wasG;
  if(modal&&wasModal)modal.scrollTop=wasModal;
  paintDirty();
}
function edWireModels(){
  document.querySelectorAll('#edBody input[data-entry]').forEach(inp=>{
    inp.oninput=()=>{const name=inp.dataset.entry,i=+inp.dataset.i;
      const m=state.ed.d.models.find(x=>x.name===name);
      const orig=(m.paths.find(p=>p.i===i)||{}).value;
      const me=edTouch(name);
      if(inp.value!==orig)me.paths[i]=inp.value; else delete me.paths[i];
      inp.classList.toggle('changed',inp.value!==orig);};
  });
  document.querySelectorAll('#edBody input[data-def]').forEach(inp=>{
    inp.oninput=()=>{const name=inp.dataset.def,k=inp.dataset.kind;
      const m=state.ed.d.models.find(x=>x.name===name),me=edTouch(name),v=inp.value.trim();
      if(v&&v!==m.texture_defaults[k])me.defaults[k]=v; else delete me.defaults[k];
      inp.classList.toggle('changed',k in me.defaults);};
  });
  document.querySelectorAll('#edBody input[data-fac]').forEach(inp=>{
    inp.oninput=()=>{const name=inp.dataset.fac,f=inp.dataset.f,k=inp.dataset.kind;
      const me=edTouch(name),v=inp.value.trim();
      const fp=me.faction_paths[f]||(me.faction_paths[f]={});
      if(v)fp[k]=v; else delete fp[k];
      if(!Object.keys(fp).length)delete me.faction_paths[f];
      inp.classList.toggle('changed',!!v);};
  });
  // …and the modeldb pane, when a model card has one open
  const e=state.ed;
  if(e.mcv&&e.mcv.loaded){
    cvWire(e.mcv);
    const idx=(e.d.models||[]).findIndex(m=>m.name===e.mcvName);
    cvBindHover(e.mcv,document.getElementById('edmGui'+idx));
  }
  // any box on this tab moves the pane's text with it
  document.querySelectorAll('#edBody input[data-entry],#edBody input[data-def],#edBody input[data-fac]').forEach(inp=>{
      const prev=inp.oninput;
      inp.oninput=ev=>{if(prev)prev.call(inp,ev); cvFromGui(state.ed.mcv);};
    });
}
// Where an imported texture should land: alongside the one it replaces, else in
// the model folder's textures/ (sprites live in their own shared folder).
function edImportDir(m,kind){
  const cur=edTexView(m).defs[kind]||'';
  if(cur.includes('/'))return cur.slice(0,cur.lastIndexOf('/'));
  const me=state.ed.mEdits[m.name]||{};
  const base=me.move_dir||m.folder.base||m.folder.suggestion;
  return kind==='sprite'?'unit_sprites':base+'/textures';
}
const TEX_FILTER=tt('editor.textures_texture_texture_all_files');
const SPR_FILTER=tt('editor.sprites_spr_spr_all_files');
async function edImportInto(name,kind,set){
  const m=state.ed.d.models.find(x=>x.name===name);
  const r=await api.post('/api/browse_file',
    {title:tt('editor.select_a_file_to_import'),filter:kind==='sprite'?SPR_FILTER:TEX_FILTER});
  if(!r.path)return;
  const dir=edImportDir(m,kind),rel=dir+'/'+r.path.split(/[\\\/]/).pop();
  const me=edTouch(name);
  me.imports=(me.imports||[]).filter(x=>x.rel!==rel).concat([{src:r.path,dest_dir:dir,rel}]);
  set(me,rel); edRenderTab(); edPreview();
}
const edImportDefault=(name,kind)=>edImportInto(name,kind,(me,rel)=>{me.defaults[kind]=rel;});
const edImportFac=(name,fac,kind)=>edImportInto(name,kind,(me,rel)=>{
  (me.faction_paths[fac]||(me.faction_paths[fac]={}))[kind]=rel;});

/* ---- EDU field access shared by every tab ----
   `e.ov` holds overrides keyed by the label block_fields() produced; `e.added`
   remembers fields this session created, so an override that happens to equal
   the (empty) starting value still gets written. */
const csv=s=>(s||'').split(',').map(x=>x.trim()).filter(Boolean);
function edFieldVal(label){const e=state.ed;
  if(label in e.ov)return e.ov[label];
  const f=e.d.fields.find(x=>x[0]===label); return f?f[1]:'';}
function edSetField(label,val){
  const e=state.ed,f=e.d.fields.find(x=>x[0]===label);
  if(!f){e.d.fields=e.d.fields.concat([[label,'']]); e.added.add(label);}
  if(val===((f||['',''])[1])&&!e.added.has(label)) delete e.ov[label]; else e.ov[label]=val;
  e.rm.delete(label); edStale();
}
// Put a field back exactly as it was - including "it wasn't there at all", which
// setting it to "" would not do (an empty EDU line is still a line).
function edRestoreField(label,val){
  const e=state.ed;
  if(val===''&&e.added.has(label)){
    e.added.delete(label); delete e.ov[label];
    e.d.fields=e.d.fields.filter(f=>f[0]!==label); edStale(); return;
  }
  edSetField(label,val);
}

/* ---- identity + localisation ---- */
// export_units.txt keeps a description on ONE line, so a real newline or tab
// typed into the box would split the record. They are written as the literal
// two-character escapes the game reads instead, the moment the box loses focus.
const escLines=s=>(s==null?'':''+s).replace(/\r\n?|\n/g,'\\n').replace(/\t/g,'\\t');
function edIsMerc(){return csv(edFieldVal('attributes')).includes('mercenary_unit');}
function edIdentity(){
  const e=state.ed,d=e.d,merc=edIsMerc();
  return `<div class="frm">
    <div class="two">
      <div><label>${tt('editor.unit_type_edu_type_the_internal')}
        <input id="edType" value="${esc(e.newType||d.type)}"></label>
        <div class="count" style="margin-top:4px">${docPoints(
          tt('editor.renaming_it_follows_the_unit_through'),[
          tt('editor.rename_rewrote_list'),
          tt('editor.probe_lists_every_file_and_how'),
          tt('editor.spellings_differ_other_things')])}</div></div>
      <div><label>${tt('editor.dictionary_localisation_unit_card_key')}
        <input id="edDict" value="${esc(e.newDict||d.dictionary)}"></label>
        <div class="count" style="margin-top:4px">${ttN('editor.renaming_moves_text_entry',d.icons.length)}
          <label class="chk" style="margin-top:4px"><input type="checkbox" id="edRmIcons"
            ${e.removeOldIcons?'checked':''}> ${tt('editor.delete_the_old_icon_files')}</label></div></div>
    </div>
    <label>${tt('editor.displayed_name')}<input id="edName" value="${esc(e.loc.name)}"></label>
    <label>${tt('editor.short_description_unit_card_tooltip')}<textarea id="edShort">${esc(e.loc.descr_short)}</textarea></label>
    <label>${tt('editor.description_info_card')}<textarea id="edDescr" style="min-height:150px">${esc(e.loc.descr)}</textarea></label>
    <div class="count" style="margin-top:4px">${tt('editor.the_description_is_stored_on_a')}</div>
    ${edTierBox()}
    <fieldset style="margin-top:12px"><legend>${tt('editor.mercenary')}</legend>
      <button class="${merc?'on':''}" onclick="edToggleMerc(${merc?'false':'true'})">${
        merc?tt('editor.mercenary_unit'):tt('editor.make_this_a_mercenary_unit')}</button>
      <div class="count" style="margin-top:6px">${tt('editor.to_recruit_it_add_a_pool',{merc:merc
        ?tt('editor.this_unit_has_the_mercenary_unit')
        :tt('editor.adds_the_mercenary_unit_attribute')})}</div>
    </fieldset>
    <fieldset style="margin-top:12px"><legend>${tt('editor.unit_card_info_card')}</legend>
      <div class="count">${docPoints(tt('editor.import_a_replacement_from_anywhere_on'),[
        tt('editor.on_save_it_takes_the_units'),
        edOwnFolders().length
          ?tt('editor.right_now_that_is_folder_s',{n:edOwnFolders().length,edOwnFolders:edOwnFolders().map(esc).join('</code> <code>')})
          :tt('editor.this_unit_has_no_ownership_so'),
        tt('editor.card_png_converted_engine_reads_nothing_else')])}</div>
      <div class="icoprev">${edIconSlot('card')}${edIconSlot('info')}</div>
      ${edCardVariants('card',tt('editor.unit_cards_on_disk'))}
      ${edCardVariants('info',tt('editor.info_cards_on_disk'))}
      ${(e.cardSrc||e.infoSrc)?`<div class="count w-good" style="margin-top:8px">
        ${tt('editor.staged_nothing_is_written_until_you')}</div>`:''}
    </fieldset>
  </div>`;
}
/* One of the two slots over the lists.

   Its picture is the one thing the lists below can also show: the slot resolves
   whichever faction folder came first, and where a mod ships more than one
   distinct picture that is a copy of the first row underneath, now at the same
   size. So the picture is dropped as soon as there IS a list - repeating it said
   nothing - and the slot keeps what only it has: the import that renames one
   file and copies it into EVERY faction folder that owns the unit, which is a
   different job from replacing one file where it lies.

   A staged import brings the picture back, whatever is on disk. That one is not
   a repeat of anything: it is the art that is about to be written. */
/* A staged picture is one of two things: a file picked from anywhere on disk
   (an absolute path) or one of the mod's own cards, which the page knows only
   by its path under `data/`. They are previewed through different routes, and
   `edit._resolve_icon_src` reads both out of the same field on the way back. */
const edSrcAbs=s=>/^([a-zA-Z]:[\\/]|[\\/])/.test(s||'');
const edSrcUrl=s=>edSrcAbs(s)?'/preview_image?path='+enc(s)
  :`/icon?mod=${enc(state.ed.mod)}&kind=modfile&rel=${enc(s)}${iconBust()}`;
function edIconSlot(kind){
  const e=state.ed, card=kind==='card';
  const key=card?'cardSrc':'infoSrc', src=e[key]||'';
  const what=card?tt('editor.unit_card'):'info card';
  const many=((e.d.icon_variants||{})[kind]||[]).length;
  const pic=!!src||many<2;
  return `<div class="icoslot">
    ${pic?`<div class="icowrap">
      <img class="${card?'card':'info'}" onerror="this.style.display='none'"
        title="${ttA('editor.replace_the',{what})}" onclick="edPickIcon('${key}')"
        src="${src?edSrcUrl(src):iconUrl(e.mod,e.unit,card?'':'info')}">
      <button class="icoedit" title="${ttA('editor.replace_the',{what})}"
        onclick="edPickIcon('${key}')">✎</button>
    </div>`:''}
    <div class="k">${card?tt('editor.unit_card_2'):tt('editor.info_card')}</div>
    <div class="fn">${src?esc(src.split(/[\\/]/).pop())
      :(pic?'current':`${many} different pictures - below`)}</div>
    <div class="sprrow">
      ${pic?'':`<button onclick="edPickIcon('${key}')"
        title="${ttA('editor.import_one_picture_and_copy_it')}">${tt('editor.replace_for_every_faction')}</button>`}
      ${edRevealBtn(kind)}
      ${src?`<button class="danger" onclick="edClearIcon('${key}')">✕</button>`:''}
    </div>
  </div>`;
}
/* Every DISTINCT card on disk, and which factions share it. The game looks a
   card up under the PLAYER's faction folder, so a mod may ship one picture for
   ten factions or ten different ones - and the preview above can only ever show
   whichever folder was found first. Grouped by file content on the server
   (edit.icon_variants), so ten identical copies are one row.

   Each row shows its picture at the size the one above the buttons is - a unit
   card as a portrait, an info card as the wide banner it is. The whole reason
   this list exists is that these pictures DIFFER, and a 56px thumbnail of a
   400px banner is too small to tell you how. */
function edCardVariants(kind,title){
  const e=state.ed;
  const rows=((e.d.icon_variants||{})[kind])||[];
  if(rows.length<2)return '';           // one picture for everyone: nothing to say
  const nFac=rows.reduce((n,r)=>n+r.factions.length,0);
  return `<div class="cardvars" data-kind="${kind}">
    <div class="k">${tt('editor.different_picture_across_faction_folders',{title:esc(title),pictures:ttN('editor.different_picture_count',rows.length),folders:ttN('editor.faction_folder_count',nFac)})}</div>
    <div class="cardvarlist">${rows.map(r=>{
      // one variant is ONE file, so it can be swapped on its own - which is the
      // point of the list: the whole reason it exists is that these differ.
      // Not `loading="lazy"` like the grid's cards: an info card is sized by the
      // picture itself, so an unloaded one is a zero-high box, and a zero-high
      // box never scrolls into view to be loaded. There are two or three of
      // these, not three hundred.
      // The stamp goes on the `src` only: imgPick sends the URL back to the
      // server as the question "which file is this", and a cache-buster is no
      // part of that question.
      const url=`/icon?mod=${enc(e.mod)}&kind=modfile&rel=${enc(r.rel)}`;
      return `<figure>
      <div class="icowrap"><img onerror="iconRetry(this)"
        title="${ttA('common.replace_this_picture')}" onclick="imgPick('${q1(esc(url))}','edRenderTab')"
        src="${url}${iconBust()}" alt="">${imgEditBtn(url,'edRenderTab')}</div>
      <figcaption>
        <span class="count">${esc(r.rel)}</span>
        <span class="tags">${r.factions.map(f=>`<span class="badge">${esc(f)}</span>`).join('')}</span>
        ${imgRow(url,'edRenderTab')}
      </figcaption></figure>`;}).join('')}</div></div>`;
}

// The faction folders an imported card would land in: this save's ownership if it
// is being changed, otherwise the unit's current one. Mirrors _plan_icon_import.
function edOwnFolders(){
  const own=(edFieldVal('ownership')||'')
    .split(/[,\s]+/).map(s=>s.trim().toLowerCase()).filter(Boolean);
  const real=own.filter(f=>f!=='slave');   // slave alone still needs a folder
  return real.length?real:own;
}
/* ---- where the picture actually lives ----
   The preview comes through /icon, which resolves the faction folders for us,
   so the page never knew the path it was showing. `d.icons` lists them in the
   order that resolution walks, so its first entry of a kind IS the picture
   above the button. The path goes back to the server as `rel` and is resolved
   under the mod's own data folder there. */
const edIconRel=kind=>{
  const f=(state.ed.d.icons||[]).find(x=>x.kind===kind);
  return f?f.rel:'';
};
function edRevealBtn(kind){
  const rel=edIconRel(kind),what=kind==='card'?'unit':'info';
  if(!rel)return `<button disabled title="${ttA('editor.this_unit_has_no_card_on',{what})}">${tt('editor.open_file_location')}</button>`;
  const many=((state.ed.d.icon_variants||{})[kind]||[]).length>1;
  return `<button title="${ttA('editor.show_in_the_file_manager',{rel:esc(rel),many:many?tt('editor.this_unit_has_more_than_one')
      :tt('editor.every_faction_folder_that_has_one')})}"
    onclick="edReveal('${q1(esc(rel))}')">${tt('editor.open_file_location')}</button>`;
}
async function edReveal(rel){
  const r=await api.post('/api/reveal',{mod:state.ed.mod,rel});
  if(!r||!r.ok)toast((r&&r.error)||tt('common.that_folder_could_not_be_opened'));
}
/* ---- Replacing a card: which folders, and which picture ------------------
   The game looks a card up under the PLAYER's faction folder, so one unit's
   card is a file per owning faction. Two questions follow from that, and the
   old button asked neither: WHERE the new picture goes, and WHICH picture.

   Where: every owning faction plus the mercs/merc fallback, all ticked. A mod
   that ships different art per faction is not always wrong to, so untick the
   ones that should keep what they have and those are left alone.

   Which: a file off disk, always - and, when the unit's folders really do hold
   more than one DIFFERENT picture, those pictures too, so "make them all use
   this one" is a click rather than a hunt through Explorer for the file. With
   one picture everywhere there is nothing to standardise and that half is not
   drawn.

   A picked picture is staged as its path under the mod's own `data/`, which is
   the only name the page has for it; `edit._resolve_icon_src` reads both that
   and an absolute one out of the same field. */
let edIconBack=null;
const edIcoKind=key=>key==='cardSrc'?'card':'info';
const edIcoMerc=kind=>kind==='card'?'mercs':'merc';
// Every folder this unit's card is looked up under, ownership first and the
// fallback last, which is the order _plan_icon_import writes them in.
function edIcoFolders(kind){
  return edOwnFolders().concat([edIcoMerc(kind)])
    .filter((f,i,a)=>f&&a.indexOf(f)===i);
}
// What each folder holds today, out of the server's content-hashed grouping:
// `folder -> the index of its variant`, so a row can show the picture it is
// about to lose.
function edIcoHas(kind){
  const rows=((state.ed.d.icon_variants||{})[kind])||[],out={};
  rows.forEach((r,i)=>(r.factions||[]).forEach(f=>{out[f]=i;}));
  return out;
}
// The ticked folders, as a Set. The dialog opens with all of them ticked, which
// is what an empty `card_folders` means to the server.
function edIcoSel(key){
  const e=state.ed;
  e.icoSel=e.icoSel||{};
  if(!e.icoSel[key])e.icoSel[key]=new Set(edIcoFolders(edIcoKind(key)));
  return e.icoSel[key];
}
function edPickIcon(key){
  // the 3D preview is a live canvas, so it is taken out of the dialog rather
  // than thrown away with it - the same move renderEditor makes
  edPrevDetach();
  edIconBack={scroll:stashPlace()};
  edIcoSel(key);
  edIcoRender(key);
}
function edIcoRender(key){
  const e=state.ed,kind=edIcoKind(key);
  const rows=((e.d.icon_variants||{})[kind])||[];
  const what=kind==='card'?tt('editor.unit_card'):'info card';
  const fname=kind==='card'?tt('editor.tga',{dictionary:e.d.dictionary}):`${e.d.dictionary}_info.tga`;
  const folders=edIcoFolders(kind),merc=edIcoMerc(kind),sel=edIcoSel(key),has=edIcoHas(kind);
  const n=folders.filter(f=>sel.has(f)).length;
  const thumb=i=>rows[i]
    ? `<img class="edicothumb" onerror="iconRetry(this)" alt=""
        src="/icon?mod=${enc(e.mod)}&kind=modfile&rel=${enc(rows[i].rel)}${iconBust()}">`
    : `<span class="edicothumb none">${tt('common.none')}</span>`;
  document.getElementById('modal').innerHTML=`<h2>${tt('editor.replace_the',{what})}
      <span class="pill">${esc(e.d.dictionary)}</span></h2>
    <div class="mbody">
      <div class="count">${docPoints(
        tt('editor.the_game_looks_a_up_under',{what,fname:esc(fname)}),[
        tt('editor.untick_a_folder_to_leave_the'),
        tt('editor.nothing_is_written_until_you_press')])}
      </div>

      <fieldset style="margin-top:12px"><legend>${tt('editor.where_it_goes')}</legend>
        ${folders.length?`
        <div class="barrow">
          <button onclick="edIcoAll('${key}',true)">${tt('editor.replace_for_all')}</button>
          <button onclick="edIcoAll('${key}',false)">${tt('common.none_2')}</button>
          <span class="count">${tt('editor.folders_ticked_of',{n,folders:ttN('editor.folder_count',folders.length)})}</span>
        </div>
        <div class="edicofolders">${folders.map(f=>`
          <label class="edicofold${sel.has(f)?' on':''}">
            <input type="checkbox" ${sel.has(f)?'checked':''}
              onchange="edIcoToggle('${key}','${q1(esc(f))}',this.checked)">
            ${thumb(has[f])}
            <span class="grow">
              <span class="nm">${esc(f===merc?tt('editor.mercenary_fallback'):edFacLabel(f))}</span>
              <span class="count">${esc(f)}${f===merc
                ? tt('editor.what_the_game_reads_when_a'):''}</span></span>
          </label>`).join('')}</div>`
        :`<div class="count w-warn">${tt('editor.this_unit_has_no_ownership_so_2')}</div>`}
      </fieldset>

      ${rows.length>1?`<fieldset style="margin-top:12px">
        <legend>${tt('editor.use_one_of_the_pictures_this')}</legend>
        <div class="count">${tt('editor.its_folders_hold_different_s_pick',{rows_n:rows.length,what:esc(what)})}</div>
        <div class="cardvars" data-kind="${kind}"><div class="cardvarlist">${rows.map((r,i)=>`
          <figure class="edicopick" onclick="edTakeIcon('${key}',${i})"
              title="${ttA('editor.give_every_ticked_folder_this_picture')}">
            <div class="icowrap"><img onerror="iconRetry(this)" alt=""
              src="/icon?mod=${enc(e.mod)}&kind=modfile&rel=${enc(r.rel)}${iconBust()}"></div>
            <figcaption>
              <span class="count">${esc(r.rel)}</span>
              <span class="tags">${r.factions.map(f=>
                `<span class="badge">${esc(f)}</span>`).join('')}</span>
              <button onclick="event.stopPropagation();edTakeIcon('${key}',${i})">${tt('editor.use_this_one')}</button>
            </figcaption></figure>`).join('')}</div></div>
      </fieldset>`:''}
    </div>
    <div class="foot">
      <button onclick="edIconCancel()">${tt('common.cancel')}</button>
      <button class="primary" ${n?'':'disabled'}
        onclick="edBrowseIcon('${key}')">${tt('editor.choose_a_file_from_disk')}</button>
    </div>`;
}
function edIcoToggle(key,folder,on){
  const sel=edIcoSel(key);
  on?sel.add(folder):sel.delete(folder);
  edIcoRender(key);
}
function edIcoAll(key,on){
  edIcoSel(key);                        // makes sure the map exists
  state.ed.icoSel[key]=on?new Set(edIcoFolders(edIcoKind(key))):new Set();
  edIcoRender(key);
}
// Back to the editor, rebuilt from state rather than from stashed markup: the
// dialog is one screen deep and the whole editor is a render away, so the only
// thing worth carrying across is where the page was scrolled to.
function edIconCancel(){
  const back=edIconBack; edIconBack=null;
  renderEditor();
  if(back)usePlace(back.scroll);
}
/* What the save sends. All of them is the server's own default, and saying it
   again would pin the list to the ownership as it stands rather than as this
   same save leaves it - so a full tick sends nothing and only a real subset is
   spelled out. */
function edIcoPayloadFolders(key){
  const sel=state.ed.icoSel&&state.ed.icoSel[key];
  if(!sel)return [];
  const all=edIcoFolders(edIcoKind(key)),picked=all.filter(f=>sel.has(f));
  return picked.length===all.length?[]:picked;
}
function edIcoStaged(key,label){
  const folders=edIcoPayloadFolders(key);
  edStale(); edIconCancel();
  toast(tt('editor.staged_for_save_to_write_it',{label,x:folders.length?folders.join(', ')
        :tt('editor.every_folder_this_unit_is_looked')}),4600);
}
function edTakeIcon(key,i){
  const e=state.ed,row=(((e.d.icon_variants||{})[edIcoKind(key)])||[])[i];
  if(!row)return;
  if(!edIcoSel(key).size)return toast(tt('editor.tick_at_least_one_folder_to'));
  e[key]=row.rel;                       // mod-relative; the server resolves both
  edIcoStaged(key,row.rel.split('/').pop());
}
async function edBrowseIcon(key){
  const what=edIcoKind(key)==='card'?tt('editor.unit_card'):'info card';
  const r=await api.post('/api/browse_file',
    {title:tt('editor.select_the_image_to_use_as',{what}),
     filter:tt('editor.images_tga_dds_png_jpg_jpeg')});
  if(!r.path)return edIconBack?edIconCancel():undefined;
  state.ed[key]=r.path;
  if(edIconBack)edIcoStaged(key,r.path.split(/[\\/]/).pop());
  else {edStale(); edRenderTab();}
}
/* ---- the tier: the toolkit's own note about a unit, not a game field ----
   Every other box on this screen writes a line the engine reads. This one does
   not, and the badge says so where it cannot be missed: a tier lives in a
   comment above the unit's `type` line, and it exists so the EDU cleanup has
   something to group by. `edTierVal` reads the pending edit before the saved
   value, the same way `edFieldVal` does for a real field. */
const edTierVal=k=>{const e=state.ed;
  return (e.tierEdit&&k in e.tierEdit)?e.tierEdit[k]:(e.d[k]||'');};
function edSetTier(k,v){const e=state.ed;
  e.tierEdit=e.tierEdit||{};
  if(v===(e.d[k]||''))delete e.tierEdit[k]; else e.tierEdit[k]=v;
  edStale(); edRenderTab();
}
function edTierBox(){
  const e=state.ed;
  const tier=edTierVal('tier'),variant=edTierVal('tier_variant');
  // A value typed through ＋ is not in the mod's list until the mod is read
  // again, so it is added to the list here. Without this the drop-down came back
  // with nothing selected and the new variant looked like it had been thrown
  // away - it was still staged, which is worse than losing it outright.
  const opts=(list,cur)=>{
    const all=(list||[]).slice();
    if(cur&&all.indexOf(cur)<0)all.push(cur);
    return ['<option value=""></option>'].concat(
      all.map(v=>`<option value="${esc(v)}"${v===cur?' selected':''}>${esc(v)}${
        (list||[]).indexOf(v)<0?' (new)':''}</option>`)).join('');
  };
  const v=gfVocabFor(e.mod)||{};
  /* The variant list is the mod's OWN vocabulary - every value any of its units
     already uses, read back out of the markers the tool wrote (vocab.py's
     `_marker_values`). So a mod that has never had a variant offers an empty
     drop-down, and the note underneath used to answer that with "type one in the
     unit file", which means leaving the toolkit to hand-edit the file it exists
     to replace. ＋ is that first value, typed here: it goes onto this unit, and
     from the next read of the mod it is in the list for every other one. */
  const adding=!!e.tierNewVar;
  return `<fieldset style="margin-top:12px"><legend>${tt('editor.tier_toolkit_only')}</legend>
    <div class="two">
      <div><label>${tt('editor.tier')}<select id="edTier">${opts(v.tier,tier)}</select></label></div>
      <div><label>${tt('editor.variant')}<span class="tiervar">${adding
        ? `<input id="edTierVarNew" placeholder="${ttA('editor.a_name_for_the_new_variant')}"
             value="${esc(variant)}" autofocus>
           <button title="${ttA('editor.keep_this_variant')}" onclick="edTierVarAdd(false)">✓</button>`
        : `<select id="edTierVar">${opts(v.tier_variant,variant)}</select>
           <button title="${ttA('editor.add_a_variant_this_mod_has')}"
             onclick="edTierVarAdd(true)">＋</button>`}</span></label></div>
    </div>
    <div class="count" style="margin-top:6px">${docPoints(
      tt('editor.the_game_never_reads_this_it'),[
      tt('editor.tier_comment_stored_variant'),
      tt('editor.tier_comment_exists_roster'),
      tt('editor.the_list_holds_every_variant_this')])}</div>
  </fieldset>`;
}
// ＋ opens the box; ✓ closes it again. The value is written on every keystroke,
// so a variant typed and never confirmed is still the unit's.
function edTierVarAdd(on){
  state.ed.tierNewVar=!!on;
  edRenderTab();
  const el=document.getElementById('edTierVarNew');
  if(el){el.focus(); el.select();}
}
function edClearIcon(key){state.ed[key]=''; edRenderTab();}
function edToggleMerc(on){
  const attrs=csv(edFieldVal('attributes'));
  const i=attrs.indexOf('mercenary_unit');
  if(on&&i<0)attrs.push('mercenary_unit');
  if(!on&&i>=0)attrs.splice(i,1);
  edSetField('attributes',attrs.join(', ')); edRenderTab();
}
function edWireIdentity(){
  const e=state.ed,d=e.d;
  const bind=(id,fn)=>{const el=document.getElementById(id);
    if(el)el.oninput=()=>{fn(el.value);edStale();};};
  bind('edType',v=>{e.newType=(v.trim()===d.type)?'':v.trim();});
  bind('edDict',v=>{e.newDict=(v.trim()===d.dictionary)?'':v.trim();});
  bind('edName',v=>{e.loc.name=v;});
  bind('edShort',v=>{e.loc.descr_short=v;});
  bind('edDescr',v=>{e.loc.descr=v;});
  ['edShort','edDescr'].forEach(id=>{const el=document.getElementById(id); if(!el)return;
    el.onblur=()=>{const v=escLines(el.value);
      if(v!==el.value){el.value=v; if(id==='edShort')e.loc.descr_short=v; else e.loc.descr=v; edStale();}};});
  const rm=document.getElementById('edRmIcons'); if(rm)rm.onchange=()=>e.removeOldIcons=rm.checked;
  const t=document.getElementById('edTier');
  if(t)t.onchange=()=>edSetTier('tier',t.value);
  const tv=document.getElementById('edTierVar');
  if(tv)tv.onchange=()=>edSetTier('tier_variant',tv.value);
  // the typed-in variant writes as it is typed, and must not redraw the box it
  // is being typed into - so it sets the value directly rather than via edSetTier
  const tn=document.getElementById('edTierVarNew');
  if(tn)tn.oninput=()=>{
    const w=state.ed; w.tierEdit=w.tierEdit||{};
    const v=tn.value.trim().replace(/\s+/g,'_');
    if(v===(w.d.tier_variant||''))delete w.tierEdit.tier_variant;
    else w.tierEdit.tier_variant=v;
    edStale();
  };
}

/* ---- every EDU field, editable, with a real delete ----
   Four of them are comma-separated lists whose ORDER is meaningful, so they get
   drag-to-reorder chips instead of a text box: `ownership` / `era 0..2` (the
   factions that may field the unit) and `armour_ug_models` (position N = armour
   upgrade level N). */
const LIST_FIELDS=new Set(['ownership',tt('editor.era_0'),tt('editor.era_1'),tt('editor.era_2')]);
function edFields(){
  const cv=state.ed.cv;
  return `<fieldset><legend>${tt('editor.edu_fields_edited_in_place')}</legend>
    ${edCeilHtml()}
    <div class="fieldbar">
      <input id="fieldFilter" placeholder="${ttA('editor.filter_fields')}" oninput="filterFields()">
      ${gfToggleHtml()}${edCvToggleHtml()}
      <span class="count" id="fieldChanged"></span>
    </div>
    <div class="cvsplit${cv?'':' off'}${(cv&&gfMode()==='raw')?' rawpair':''}">
      <div class="cvgui" id="edFieldsCol">${edFieldsCol()}</div>
      ${cv?`<div id="edCodeCol">${cvHtml(cv)}</div>`:''}
    </div></fieldset>`;
}
/* 39: the engine's ceilings this unit is past, as the file on disk has it. A
   line, never a refusal - an HP of 30 is read as 15 and the game still loads -
   and each one names the Medieval II document it comes from, because the list
   the phase was scoped from turned out to be Rome's. An edit that goes past one
   says so again in the save preview. */
function edCeilHtml(){
  const d=state.ed.d||{}, rows=(d.ceilings||[]).concat(d.roster_ceilings||[]);
  if(!rows.length)return '';
  return `<div class="trnote w-warn edceil">${tt('editor.past_the_engines_ceiling',{x:rows.map(f=>`<div>${esc(f.message)} <span class="count">(${esc(f.source)})</span></div>`).join('')})}
  </div>`;
}
// Just the boxes - redrawn on its own when the text pane re-reads the block,
// because redrawing the whole tab would take the caret out of the text.
function edFieldsCol(){
  return gfMode()==='guided'
    ? `<div class="allfields guided" id="allFields">${gfRender(gfHostEditor())}</div>`
    : edRawFields();
}
function edFieldsRefresh(){
  const col=document.getElementById('edFieldsCol'); if(!col){edRenderTab(); return;}
  const box=document.getElementById('allFields'),was=box?box.scrollTop:0;
  const g=document.getElementById('gfBody'),wasG=g?g.scrollTop:0;
  col.innerHTML=edFieldsCol();
  if(gfMode()==='guided')gfWire(gfHostEditor()); else edWireRawRows();
  const now=document.getElementById('allFields'); if(now&&was)now.scrollTop=was;
  const nowG=document.getElementById('gfBody'); if(nowG&&wasG)nowG.scrollTop=wasG;
  edCount(); cvBindHover(state.ed.cv); edRawAlign(); paintDirty();
}

/* ---- Code View on this tab ----
   Off by default and remembered per user: most edits never need the file, and
   the pane costs half the dialog's width. */
function edCvToggleHtml(){
  const on=!!state.ed.cv;
  return `<button class="${on?'on':''}" title="${ttA('editor.show_this_units_block_exactly_as')}"
    onclick="edCvToggle()">${tt('common.code_view')}</button>`;
}
async function edCvToggle(){
  const e=state.ed;
  if(e.cv){e.cv=null; api.post('/api/settings',{code_view:false});
    state.settings.code_view=false; edRenderTab(); return;}
  state.settings.code_view=true; api.post('/api/settings',{code_view:true});
  e.cv=cvCreate(edCvHost());
  edRenderTab();                       // shows "Loading the text…" beside the boxes
  await cvLoad(e.cv);
  if(state.ed===e&&e.cv)edRenderTab();
}
function edCvHost(){
  const e=state.ed;
  return {kind:'edu', mod:e.mod, id:e.unit,
    where:e.d.eop?e.d.eop_file:'data/export_descr_unit.txt',
    edits:()=>({overrides:state.ed.ov, removals:[...state.ed.rm]}),
    // the text pane re-read the block: it is the new starting point, so the
    // box-level overrides that produced it are folded in and cleared
    adopt:cv=>{const s=state.ed;
      s.d.fields=(cv.fields||[]).map(f=>[f[0],f[1]]);
      s.ov={}; s.rm=new Set(); s.added=new Set(); edStale();},
    refreshGui:()=>edFieldsRefresh(),
    // the block's line count changed, so the raw rows have to be re-placed
    relayout:()=>edRawAlign()};
}
function edRawFields(){
  const e=state.ed,d=e.d;
  const present=new Set(d.fields.map(([l])=>l.replace(/#\d+$/,'')));
  const missing=(d.known_fields||[]).filter(k=>!present.has(k));
  // type/dictionary/soldier define the block - the engine refuses to drop them
  const PROTECTED=new Set(['type','dictionary','soldier']);
  const rmBtn=(label,gone)=>PROTECTED.has(label.replace(/#\d+$/,''))
    ? `<span class="rm" title="${ttA('editor.this_field_defines_the_unit_and')}"> </span>`
    : `<button class="rm" data-rm="${esc(label)}" title="${
        gone?tt('editor.keep_this_field'):tt('editor.remove_this_line_from_the_unit')}">${gone?'↺':'✕'}</button>`;
  const rows=d.fields.map(([label,val])=>{
    const cur=(label in e.ov)?e.ov[label]:val;
    const gone=e.rm.has(label);
    const key=label.replace(/#\d+$/,'');
    // what this line is, moved onto the ? beside its name
    const why=GF_FIELDS[key]&&GF_FIELDS[key].t
      ? GF_FIELDS[key].t+'. '+gfPlainDoc(key) : '';
    const head=`<div class="afrow wide${gone?' gone':''}" data-label="${esc(label)}">
      <label>${qm(why,label)}${esc(label)}</label>`;
    if(LIST_FIELDS.has(label)&&!gone)
      return head+edFactionField(label,cur)+rmBtn(label,gone)+'</div>';
    if(label==='armour_ug_models'&&!gone)
      return head+edArmourField(label,cur)+rmBtn(label,gone)+'</div>';
    return `<div class="afrow${gone?' gone':''}" data-label="${esc(label)}">
      <label>${qm(why,label)}${esc(label)}</label>
      <input data-k="${esc(label)}" value="${esc(cur)}" ${gone?'disabled':''}
        class="${(label in e.ov)&&e.ov[label]!==val?'changed':''}">
      ${rmBtn(label,gone)}</div>`;
  }).join('');
  return `<div class="allfields" id="allFields">${rows}</div>
    <div class="count" style="margin-top:6px">${tt('editor.removes_the_whole_line_clearing_a')}</div>
    <div class="prow" style="margin-top:8px;grid-template-columns:var(--plw) 1fr auto">
      <span class="pl">${tt('editor.add_a_missing_field',{qm:qm(tt('editor.fields_the_edu_understands_that_this'),tt('editor.add_a_missing_field_2'))})}</span>
      <select id="edAddKey">${missing.map(k=>`<option>${esc(k)}</option>`).join('')||`<option value="">${tt('editor.nothing_missing')}</option>`}</select>
      <button onclick="edAddField()">${tt('common.add_2')}</button>
    </div>`;
}
function edWireFields(){
  if(gfMode()==='guided')gfWire(gfHostEditor()); else edWireRawRows();
  edCount();
  if(state.ed.cv){cvWire(state.ed.cv); cvBindHover(state.ed.cv);}
  edRawAlign();
}
/* ---- raw lines, line for line ----
   With Code View open, the raw view is one box per EDU line beside the file's
   own lines, and it is only worth having if row n really is line n. Counting
   will not give that: the block also has its `type` line, whatever comment
   lines the pane is hiding, and a repeated field is two rows for one key. The
   server already says where every field's line is - that is what the hover
   highlight runs on - so the rows are PLACED from those spans and the two sides
   agree whatever the block looks like. A row the spans do not cover (a field
   just added, which is not in the file yet) is stacked below the block. */
function edRawAlign(){
  const cv=state.ed&&state.ed.cv;
  const box=document.getElementById('allFields');
  if(!box)return;
  const on=!!(cv&&cv.loaded&&!cv.err&&gfMode()==='raw');
  const rows=[...box.querySelectorAll('.afrow')];
  box.classList.toggle('aligned',on);
  if(!on){rows.forEach(r=>{r.style.top='';}); box.style.height='';
    if(cv)cvExpand(cv,false); return;}
  const lh=cvLh(cv);
  cvExpand(cv,true);                   // grow the pane before measuring against it
  const top0=cvTextOrigin(cv,box);     // where the pane's line 1 is, from here
  let last=cvLines(cv.text).length;
  rows.forEach(r=>{
    const sp=(cv.spans[r.dataset.label]||[])[0];
    const line=sp?sp[0]:(last+=1);
    r.classList.toggle('unplaced',!sp);
    r.style.top=Math.round((line-1)*lh+top0)+'px';
  });
  box.style.height=Math.round(last*lh+top0+lh)+'px';
}
function edWireRawRows(){
  const e=state.ed;
  document.querySelectorAll('#allFields input[data-k]').forEach(inp=>{
    inp.oninput=()=>{const k=inp.dataset.k,orig=(e.d.fields.find(f=>f[0]===k)||['',''])[1];
      if(inp.value!==orig)e.ov[k]=inp.value; else delete e.ov[k];
      inp.classList.toggle('changed',inp.value!==orig); edCount(); edStale();};
  });
  document.querySelectorAll('#allFields .rm').forEach(b=>{
    b.onclick=()=>{const k=b.dataset.rm;
      if(e.rm.has(k)){e.rm.delete(k);} else {e.rm.add(k); delete e.ov[k];}
      edRenderTab();};
  });
}
function edCount(){
  const e=state.ed,el=document.getElementById('fieldChanged'); if(!el)return;
  const n=Object.keys(e.ov).length,r=e.rm.size;
  el.textContent=[n?`${n} changed`:'',r?`${r} removed`:''].filter(Boolean).join(' · ');
}
function edAddField(){
  const e=state.ed,sel=document.getElementById('edAddKey'); const k=sel&&sel.value; if(!k)return;
  e.d.fields=e.d.fields.concat([[k,'']]);      // shows up as a new (empty) row
  e.added.add(k); e.ov[k]=''; edRenderTab();
  const inp=document.querySelector(`#allFields input[data-k="${cssq(k)}"]`);
  if(inp){inp.focus();}
}

/* =========================================================================
   COMPARE - the same unit table twice, side by side

   "Is my new spearman better than the one it replaces, and by how much" is a
   question the EDU answers only if you hold two blocks of eleven-value lines in
   your head at once. So the second unit is loaded beside the first and the lines
   are split into their named slots - attack against attack, morale against
   morale - with the better side green and the worse red.

   Which side is "better" is only claimed where it is genuinely a merit: attack
   and armour go up, cost and heat fatigue go down, and everything else (a hit
   sound, a formation width, the skeleton factor) is simply marked as different.
   Guessing a winner for a setting that has none would be worse than saying
   nothing, because it reads as advice.

   Both columns are live boxes and both are written by Save - the whole point is
   to close a gap you can see, in whichever of the two units is wrong. */

/* One slot's verdict. `absent` names a side that has no such LINE at all, which
   makes its zeroes meaningless - a unit with no `stat_armour_ex` does not have
   0 armour, it has the ordinary line instead - so nothing wins those. */
/* The whole table as data, from two field lookups. Pure - it never touches the
   page - so the same call builds the view and answers "how many differences are
   there" for the header, and the test suite can drive it under node. */
/* ---- the two sides ----
   'a' is the unit the editor opened on and writes through the ordinary edit
   path; 'b' is the compared unit, which carries its own override map and is
   saved by a second request. Neither knows about the other. */
/* ---- the tab ---- */
function edCompare(){
  const e=state.ed;
  if(!e.cmp)return edCmpPicker();
  if(e.cmp.loading)return `<div class="frm"><div class="count">${tt('editor.loading',{unit:esc(e.cmp.unit)})}</div></div>`;
  if(e.cmp.error)return `<div class="frm"><div class="w-bad">${tt('editor.couldnt_open',{unit:esc(e.cmp.unit),error:esc(e.cmp.error)})}</div>
    <button style="margin-top:8px" onclick="state.ed.cmp=null;edRenderTab()">${tt('editor.pick_another_unit')}</button></div>`;
  const m=edCmpModel();
  const q=(e.cmpQ||'').trim().toLowerCase();
  const fields=[];
  m.sections.forEach(sec=>{
    const keep=sec.fields.map(f=>{
      const hit=!q||f.key.toLowerCase().includes(q)||f.title.toLowerCase().includes(q)
        ||f.rows.some(r=>(r.name||'').toLowerCase().includes(q));
      if(!hit)return null;
      const rows=e.cmpSame?f.rows:f.rows.filter(r=>!r.v.same);
      return rows.length?Object.assign({},f,{rows}):null;
    }).filter(Boolean);
    if(keep.length)fields.push(Object.assign({},sec,{fields:keep}));
  });
  return `<div class="frm">
    ${edCmpHead(m)}
    <div class="cmpbar">
      <input class="q" id="cmpQ" placeholder="${ttA('editor.filter_by_stat_attack_morale_cost')}"
        value="${esc(e.cmpQ||'')}">
      <label class="chk"><input type="checkbox" id="cmpSame" ${e.cmpSame?'checked':''}>
        ${tt('editor.show_the_stats_they_share')}</label>
      <span class="count">${tt('editor.both_columns_are_editable_save_changes')}</span>
    </div>
    ${fields.length?fields.map(edCmpSection).join('')
      :`<div class="count">${q?tt('editor.nothing_matches_that_filter')
        :tt('editor.these_two_units_are_identical_on')}</div>`}
    ${cmpDatalists()}</div>`;
}
/* Which vocabularies the table needs a datalist for, emitted once at the bottom
   rather than once per box - a `soldier` model list is two thousand entries and
   the table has forty of them. */
function edWireCompare(){
  const e=state.ed;
  const q=document.getElementById('cmpQ');
  if(q)q.oninput=()=>{ e.cmpQ=q.value;
    // in the picker the list itself is the thing being filtered; in the table
    // only the rows are, and both want the caret left where it is
    edRenderTab();
    const n=document.getElementById('cmpQ');
    if(n){n.focus();n.setSelectionRange(n.value.length,n.value.length);}
  };
  const same=document.getElementById('cmpSame');
  if(same)same.onchange=()=>edCmpToggleSame(same.checked);
  document.querySelectorAll('#edBody [data-cmp]').forEach(el=>{
    const w=el.dataset.cmp,label=el.dataset.cl,pi=+el.dataset.ci;
    const write=()=>{ cmpWrite(w,label,pi,el.value); cmpRepaint(el); };
    el.oninput=write; el.onchange=write;
  });
}
/* Recolour one row in place. A full re-render on every keystroke would throw the
   caret out of the box being typed into, which is exactly the box whose colour
   has to keep up. */
/* ---- drag-to-reorder chip lists ---------------------------------------
   The order of these lists is data, not decoration: armour_ug_models[N] is the
   model shown at armour upgrade level N, and era lines are conventionally led by
   the faction the unit belongs to. Dropping a chip rewrites the whole line. */
let edDrag=null;
function edDragStart(ev,label,i){
  edDrag={label,i}; ev.dataTransfer.effectAllowed='move';
  try{ev.dataTransfer.setData('text/plain',String(i));}catch(_){}
  ev.currentTarget.classList.add('drag');
}
function edDragOver(ev,label){
  if(!edDrag||edDrag.label!==label)return;
  ev.preventDefault(); ev.currentTarget.classList.add('over');
}
function edDragLeave(ev){ev.currentTarget.classList.remove('over');}
function edDragEnd(ev){ev.currentTarget.classList.remove('drag'); edDrag=null;}
function edDrop(ev,label,i){
  if(!edDrag||edDrag.label!==label)return;
  ev.preventDefault();
  const list=csv(edFieldVal(label)),from=edDrag.i;
  if(from===i){edDrag=null; edRenderTab(); return;}
  const [moved]=list.splice(from,1); list.splice(i,0,moved);
  edDrag=null; edSetField(label,list.join(', ')); edRenderTab();
}
// `opt.cls` styles the list (armour tiers use it to lift their ✕ above the chip)
// and `opt.rm` swaps in a different remove call - an armour tier has to drop its
// armour_ug_levels entry with it, which the plain list remove knows nothing about.
function edChips(label,items,extra,opt){
  const o=opt||{},cls=o.cls?' '+o.cls:'';
  // entries you added stand out from the ones the file already had, and the
  // ones you took out stay as ghosts you can click to put back
  // …except for armour tiers, where a slot is positional: putting one back is
  // not just re-adding a name, so no ghost is offered there
  const was=new Set(csv((state.ed.d.fields.find(x=>x[0]===label)||['',''])[1]));
  const gone=o.cls==='ug'?[]:[...was].filter(v=>items.indexOf(v)<0);
  return `<div class="chips${cls}">${items.map((v,i)=>`<span class="chipd${cls}${
      was.has(v)?'':' added'}" draggable="true"
      ondragstart="edDragStart(event,'${q1(esc(label))}',${i})"
      ondragover="edDragOver(event,'${q1(esc(label))}')" ondragleave="edDragLeave(event)"
      ondragend="edDragEnd(event)" ondrop="edDrop(event,'${q1(esc(label))}',${i})"
      title="${was.has(v)?tt('editor.drag_to_reorder'):tt('editor.added_by_you_drag_to_reorder')}">
      <span class="g">⠿</span><span class="${i===0?'first':''}">${esc(v)}</span>
      ${(extra||(()=>''))(v,i)}
      <button class="${o.cls==='ug'?'xup':'x'}" title="${ttA('editor.remove',{x:esc(v)})}"
        onclick="${o.rm?o.rm(i,v):`edListRemove('${q1(esc(label))}',${i})`}">✕</button>
    </span>`).join('')||`<span class="count">${tt('editor.empty')}</span>`}
    ${gone.map(v=>`<span class="chipd gone" title="${ttA('editor.removed_by_you_click_to_put')}"
      onclick="edListRestore('${q1(esc(label))}','${q1(esc(v))}')">${esc(v)}</span>`).join('')}</div>`;
}
function edListRestore(label,v){
  const list=csv(edFieldVal(label));
  if(list.indexOf(v)<0)list.push(v);
  edSetField(label,list.join(', ')); edRenderTab();
}
function edListRemove(label,i){
  const list=csv(edFieldVal(label)); list.splice(i,1);
  edSetField(label,list.join(', ')); edRenderTab();
}
function edListSet(label,items){edSetField(label,items.join(', ')); edRenderTab();}
function edListToggle(label,fac,on){
  const list=csv(edFieldVal(label)),i=list.indexOf(fac);
  if(on&&i<0)list.push(fac); else if(!on&&i>=0)list.splice(i,1);
  edListSet(label,list);
}

/* ---- ownership / era 0..2: a faction checklist over a chip list ---- */
function edFactionList(){
  const d=state.ed.d,seen=new Set();
  const all=(d.all_factions||[]).slice();
  ['ownership',tt('editor.era_0'),tt('editor.era_1'),tt('editor.era_2')].forEach(l=>csv(edFieldVal(l)).forEach(f=>all.push(f)));
  return all.filter(f=>!seen.has(f)&&seen.add(f))
            .sort((a,b)=>edFacLabel(a).localeCompare(edFacLabel(b)));
}
const edFacLabel=f=>facTwoNames(f,(state.ed.d.faction_names||{})[f]);
function edFactionField(label,cur){
  const list=csv(cur),chosen=new Set(list);
  const isEra=label!=='ownership';
  const own=csv(edFieldVal('ownership'));
  // which factions this line named before you touched it, so the ones you
  // added or removed stand out from the ones that were already there
  const was=new Set(csv((state.ed.d.fields.find(x=>x[0]===label)||['',''])[1]));
  const boxes=edFactionList().map(f=>facCheckRow(
      f,(state.ed.d.faction_names||{})[f],
      `edListToggle('${q1(esc(label))}','${q1(esc(f))}',this.checked)`,
      chosen.has(f),'',chosen.has(f)!==was.has(f))).join('');
  return `<div style="flex:1;min-width:0">
    ${edChips(label,list)}
    <div class="barrow">
      <details class="drop"><summary>${tt('editor.choose_factions_selected',{list_n:list.length})}</summary>
        <div class="dropbody"><div class="barrow" style="margin:0 0 6px">
          <button onclick="edListSet('${q1(esc(label))}',${JSON.stringify(edFactionList()).replace(/"/g,'&quot;')})">${tt('editor.all')}</button>
          <button onclick="edListSet('${q1(esc(label))}',[])">${tt('common.none_2')}</button>
        </div><div class="faclist" style="border:none;padding:0;max-height:none">${boxes}</div></div>
      </details>
      ${isEra?`<button ${own.length?'':'disabled'}
          onclick="edListSet('${q1(esc(label))}',${JSON.stringify(own).replace(/"/g,'&quot;')})"
          title="${ttA('editor.replace_this_era_with_the_ownership')}">${tt('editor.copy_ownership',{own_n:own.length})}</button>
        <button ${own.length?'':'disabled'}
          onclick="edListSet('${q1(esc(label))}',['${q1(esc(own[0]||''))}'])"
          title="${ttA('editor.replace_this_era_with_just_the')}">${tt('editor.copy_1st_ownership',{own:own.length?` (${esc(own[0])})`:''})}</button>`:''}
    </div></div>`;
}

/* ---- armour_ug_models: reorder tiers, jump to an entry, add the next one ----
   Each tier carries a ✕ above its chip, because dropping one is not just a list
   remove: armour_ug_levels is positional too and has to lose the same slot.
   The ＋ opens a four-mode panel - see edUgPanel. */
function edArmourField(label,cur){
  const models=csv(cur),levels=csv(edFieldVal('armour_ug_levels'));
  const jump=(v)=>`<button title="${ttA('editor.edit_in_the_battle_models_tab',{x:esc(v)})}"
      onclick="edJumpModel('${q1(esc(v))}')">✎</button>`;
  const open=!!state.ed.ug;
  return `<div style="flex:1;min-width:0">
    ${edChips(label,models,jump,{cls:'ug',rm:i=>`edUgRemove(${i})`})}
    <div class="barrow">
      <button class="ugadd${open?' on':''}" onclick="edUgOpen()"
        title="${ttA('editor.add_an_armour_upgrade_tier')}">${open?'−':'＋'}</button>
      <span class="count">${tt('editor.position_upgrade_level',{levels:levels.length?tt('editor.armour_ug_levels',{levels:esc(levels.join(', '))}):'',x:levels.length&&levels.length!==models.length
          ? ` <span class="w-warn">${tt('editor.level_s_for_model_s',{levels_n:levels.length,models_n:models.length})}</span>`:''})}</span>
    </div>
    ${edUgPanel()}</div>`;
}

/* ---- the ＋ menu: four ways to add an armour tier -------------------------
   1 repeat the last tier - the SAME entry again, so the armour upgrade is a
                            stat change with no model change
   2 take a unit's ugs    - read another unit's armour_ug_models, tick what to import
   3 pick an existing entry - search the whole modeldb and point a tier at one
   4 new entry from a tier - clone a chosen entry and give it its own mesh/texture
   Only mode 4 creates a modeldb entry. 1-3 just name entries that already exist:
   armour_ug_models is a list of bmdb entry names, and a new entry is only worth
   making when the tier is actually going to look different. */
function edUgOpen(){const e=state.ed; e.ug=e.ug?null:{mode:''}; edRenderTab();}
function edUgMode(m){
  const e=state.ed,u=e.ug||(e.ug={});
  if(m==='clone'){edUgCloneLast(); return;}          // nothing to configure
  u.mode=m; u.filter='';
  if(m==='unit'){u.unit='';u.donor=null;u.pick={};u.error='';u.loading=false;}
  if(m==='new'){
    const tiers=csv(edFieldVal('armour_ug_models'));
    const own=(e.d.models||[]).filter(x=>!x.missing).map(x=>x.name);
    u.from=own.slice().reverse().find(n=>tiers.includes(n))||own[own.length-1]||'';
  }
  edRenderTab();
}
function edUgPanel(){
  const u=state.ed.ug; if(!u)return '';
  const btn=(k,label,tip)=>`<button class="${u.mode===k?'on':''}" title="${esc(tip)}"
    onclick="edUgMode('${k}')">${label}</button>`;
  return `<div class="ugpanel">
    <div class="ugmodes">
      ${btn('clone',tt('editor.1_repeat_the_last_tier'),
        tt('editor.name_the_last_entry_again_as'))}
      ${btn('unit',tt('editor.2_take_a_units_upgrades'),
        tt('editor.read_another_units_armour_ug_models'))}
      ${btn('browse',tt('editor.3_pick_an_existing_entry'),
        tt('editor.search_every_entry_in_this_mods'))}
      ${btn('new',tt('editor.4_new_entry_from_a_tier'),
        tt('editor.create_a_new_modeldb_entry_based'))}
    </div>
    ${u.mode?`<div class="ugbody">${u.mode==='unit'?edUgUnitBody()
        :u.mode==='browse'?edUgBrowseBody():edUgNewBody()}</div>`
      :`<div class="count" style="margin-top:9px">${tt('editor.choose_how_the_new_tier_should')}</div>`}
  </div>`;
}

/* -- shared: append tiers, keeping armour_ug_levels in step -- */
const edUgSnapshot=()=>({models:edFieldVal('armour_ug_models'),
                         levels:edFieldVal('armour_ug_levels')});
// `opt.repeat` allows a name the list already has. Naming the same entry twice is
// a real M2TW pattern, not a mistake - it is how a unit gets the armour upgrade
// without a different model - so only the accidental case is guarded against.
function edUgAppend(names,donorLevels,opt){
  const models=csv(edFieldVal('armour_ug_models')),levels=csv(edFieldVal('armour_ug_levels'));
  const added=[];
  (names||[]).forEach((raw,i)=>{
    const name=(raw||'').trim().toLowerCase();
    if(!name||(models.includes(name)&&!(opt||{}).repeat))return;
    models.push(name); added.push(name);
    // armour_ug_levels has to stay ascending - the game reads it as "this model
    // from this armour level up". So a donor's own level is kept only when it is
    // still above everything here; otherwise the tier goes one past the highest.
    const nums=levels.map(x=>parseInt(x,10)).filter(x=>!isNaN(x));
    const max=nums.length?Math.max(...nums):0;
    const want=parseInt(((donorLevels||[])[i]||'').trim(),10);
    levels.push(String(!isNaN(want)&&want>max ? want
                       : nums.length?max+1:models.length));
  });
  if(!added.length)return added;
  edSetField('armour_ug_models',models.join(', '));
  edSetField('armour_ug_levels',levels.join(', '));
  return added;
}
// ✕ above a tier: drop the model AND its level, or every level above it slides
// down onto the wrong model.
function edUgRemove(i){
  const e=state.ed;
  const models=csv(edFieldVal('armour_ug_models')),levels=csv(edFieldVal('armour_ug_levels'));
  const hadLevels=!!edFieldVal('armour_ug_levels');
  const gone=models[i]; if(gone===undefined)return;
  models.splice(i,1);
  if(i<levels.length)levels.splice(i,1);
  edSetField('armour_ug_models',models.join(', '));
  if(hadLevels)edSetField('armour_ug_levels',levels.join(', '));
  // a pending entry that exists only to be this tier has nothing left to be -
  // unless the tier was repeated and another slot still names it
  const at=e.newModels.findIndex(n=>n._tier&&n.name===gone);
  if(at>=0&&!models.includes(gone))e.newModels.splice(at,1);
  edRenderTab(); edPreview();
}

/* -- mode 1: repeat the last tier -- */
// The SAME entry name again, not a copy of it. armour_ug_models is a list of
// bmdb entry names, so repeating one gives the unit the armour upgrade in its
// stats while the model on the field stays exactly as it was - vanilla and DaC
// both do it (isengard_bodyguard twice, at levels 3 and 6). Cloning the entry
// instead would put a second copy of the same meshes and textures in the modeldb
// for no visible difference.
function edUgCloneLast(){
  const e=state.ed,models=csv(edFieldVal('armour_ug_models'));
  // with no tiers yet, the first one repeats the body model
  const last=(models[models.length-1]||edFieldVal('soldier').split(',')[0]||'').trim().toLowerCase();
  if(!last){toast(tt('editor.this_unit_has_no_model_entry'));return;}
  if(!edUgAppend([last],null,{repeat:true}).length)return;
  e.ug=null; edRenderTab(); edPreview();
  const lv=csv(edFieldVal('armour_ug_levels')).slice(-1)[0];
  toast(lv?tt('editor.repeated_next_tier_armour',{last,lv}):tt('editor.repeated_next_tier',{last}),4200);
}
// Where a cloned tier comes from and what it gets called: `<stem>_ug<n>`, with n
// walked up until nothing in the mod (or pending) has that name.
function edUgNewSpec(srcName){
  const e=state.ed,d=e.d,models=csv(edFieldVal('armour_ug_models'));
  const src=(srcName||models[models.length-1]||edFieldVal('soldier').split(',')[0]||'')
            .trim().toLowerCase();
  if(!src||!d.models.some(m=>m.name===src)){
    toast(tt('editor.no_existing_model_entry_to_clone')); return null;}
  // strip an existing tier suffix so tiers stay <stem>_ug1.._ugN rather than
  // growing one per clone - mods write both `_ug3` and `_upg3`
  const stem=src.replace(/_u(p)?g\d+$/i,'');
  let n=models.length+1,name=`${stem}_ug${n}`;
  while(d.model_names.includes(name)||e.newModels.some(x=>x.name===name)||models.includes(name))
    name=`${stem}_ug${++n}`;
  const from=d.models.find(m=>m.name===src)||{};
  return {src,name,
          dest_dir:(from.folder&&(from.folder.base||from.folder.suggestion))||'unit_models'};
}

/* -- mode 2: import another unit's armour upgrades --
   The donor is picked with the same search + faction / category / class / mercs
   filters as "＋ New unit"'s base picker, off the same state.data.units the
   browser is showing, so finding a unit works the way it does everywhere else.
   The filters live in `u.f` rather than in the DOM, because every edit
   re-renders the whole tab and would otherwise reset them. */
function edUgUnitBody(){
  const e=state.ed,u=e.ug,d=e.d,dd=state.data||{};
  const f=u.f||(u.f={q:'',fac:'',cat:'',cls:'',merc:false});
  const have=new Set(csv(edFieldVal('armour_ug_models')));
  const donor=u.loading?`<div class="count" style="margin-top:9px">${tt('editor.reading_the_unit')}</div>`
    :u.error?`<div class="count w-bad" style="margin-top:9px">${esc(u.error)}</div>`
    :!u.donor?''
    :!u.donor.models.length
      ?`<div class="count w-warn" style="margin-top:9px"><b>${esc(u.unit)}</b> ${tt('editor.has_no_armour_ug_models',{x:u.donor.soldier?tt('editor.its_body_model_is_which_mode',{soldier:esc(u.donor.soldier)}):''})}</div>`
    :`<div class="count" style="margin-top:9px">${tt('editor.tiers_of_to_import',{unit:esc(u.unit)})}</div>
      <div class="uglist">${u.donor.models.map((m,i)=>{
        // an entry staged on the Battle models tab counts as known: it is not in
        // the modeldb yet, but the save that imports this tier writes it too
        const dup=have.has(m),
              known=(d.model_names||[]).includes(m)||e.newModels.some(n=>n.name===m);
        return `<label class="ugrow">
          <input type="checkbox" ${u.pick[i]?'checked':''}
            onchange="state.ed.ug.pick[${i}]=this.checked">
          <span class="nm">${esc(m)}</span>
          <span class="count">${tt('editor.level',{x:esc(u.donor.levels[i]||'none'),x2:dup?tt('editor.already_a_tier_so_it_imports')
              :known?'':` ${tt('editor.not_in_this_mods_modeldb')}`})}</span>
        </label>`;}).join('')}</div>
      <div class="barrow">
        <button class="primary" onclick="edUgTakeUnit()">${tt('editor.add_ticked_tier_s')}</button>
        <span class="count">${tt('editor.appended_after_the_tiers_this_unit')}</span>
      </div>`;
  const rows=edUgUnitRows();          // sets u._n, so the count renders first time
  return `<input id="ugSearch" style="width:100%" placeholder="${ttA('editor.filter_units')}"
      value="${esc(f.q)}" oninput="edUgFilterUnits('q',this.value)">
    <div class="barrow" style="margin:6px 0 0">
      <select onchange="edUgFilterUnits('fac',this.value)">${
        opts(tt('common.all_factions'),dd.factions||[],facLabel,f.fac)}</select>
      <select onchange="edUgFilterUnits('cat',this.value)">${
        opts(tt('editor.all_categories'),dd.categories||[],null,f.cat)}</select>
      <select onchange="edUgFilterUnits('cls',this.value)">${
        opts(tt('editor.all_classes'),dd.classes||[],null,f.cls)}</select>
      <label class="chk"><input type="checkbox" ${f.merc?'checked':''}
        onchange="edUgFilterUnits('merc',this.checked)"> ${tt('editor.mercs_only')}</label>
      <span class="count" id="ugCount">${u._n?`${u._n[0]}/${u._n[1]}`:''}</span>
    </div>
    <div class="baselist" id="ugUnitList">${rows}</div>
    ${donor}`;
}
// Rows only - the filter handler rewrites just this, so typing never loses the
// caret and the donor's tick list below is left as it is.
function edUgUnitRows(){
  const e=state.ed,u=e.ug,f=u.f,all=(state.data&&state.data.units)||[];
  const qq=(f.q||'').trim().toLowerCase();
  const units=all.filter(x=>x.type!==e.d.type
    &&(!qq||(x.name||'').toLowerCase().includes(qq)||x.type.toLowerCase().includes(qq)
        ||(x.dictionary||'').toLowerCase().includes(qq))
    &&(!f.fac||(x.ownership||[]).includes(f.fac))&&(!f.cat||x.kind===f.cat)
    &&(!f.cls||x.class===f.cls)&&(!f.merc||x.mercenary));
  u._n=[units.length,all.length];
  return units.slice(0,400).map(x=>`
    <div class="baserow${u.unit===x.type?' sel':''}" onclick="edUgPickUnit('${q1(esc(x.type))}')">
      <img onerror="iconRetry(this)" src="${iconUrl(e.mod,x.type)}">
      <div><div class="bn">${esc(x.name||x.type)}</div>
        <div class="bs">${esc(x.type)} · ${esc(x.kind||'?')}${x.class?' / '+esc(x.class):''}${
          x.mercenary?tt('editor.merc'):''}</div></div>
    </div>`).join('')||`<div class="count" style="padding:8px">${tt('common.no_units_match')}</div>`;
}
function edUgFilterUnits(k,v){
  const u=state.ed.ug; if(!u||!u.f)return;
  u.f[k]=v;
  const box=document.getElementById('ugUnitList');
  if(!box){edRenderTab();return;}
  box.innerHTML=edUgUnitRows();
  const c=document.getElementById('ugCount');
  if(c&&u._n)c.textContent=`${u._n[0]}/${u._n[1]}`;
}
async function edUgPickUnit(type){
  const e=state.ed,u=e.ug; if(!u)return;
  u.unit=(type||'').trim(); u.donor=null; u.pick={}; u.error='';
  if(!u.unit){edRenderTab();return;}
  u.loading=true; edRenderTab();
  let r;
  try{ r=await api.get(`/api/unit_fields?mod=${enc(e.mod)}&type=${enc(u.unit)}`); }
  catch(err){ r={error:''+err}; }
  if(state.ed!==e||e.ug!==u||u.unit!==(type||'').trim())return;   // moved on meanwhile
  u.loading=false;
  if(r.error){u.error=r.error; edRenderTab(); return;}
  const get=k=>(((r.fields||[]).find(([l])=>l===k))||['',''])[1];
  u.donor={models:csv(get('armour_ug_models')),levels:csv(get('armour_ug_levels')),
           soldier:(get('soldier').split(',')[0]||'').trim()};
  // a tier this unit already has is offered but not pre-ticked - importing it
  // would be a deliberate repeat, not something to do by default
  const have=new Set(csv(edFieldVal('armour_ug_models')));
  u.donor.models.forEach((m,i)=>{u.pick[i]=!have.has(m);});
  edRenderTab();
}
function edUgTakeUnit(){
  const e=state.ed,u=e.ug; if(!u||!u.donor)return;
  const names=[],levels=[];
  u.donor.models.forEach((m,i)=>{
    if(u.pick[i]){names.push(m); levels.push(u.donor.levels[i]||'');}});
  if(!names.length){toast(tt('editor.nothing_ticked_to_import'));return;}
  const added=edUgAppend(names,levels,{repeat:true}),from=u.unit;
  e.ug=null; edRenderTab(); edPreview();
  toast(ttN('editor.tiers_taken_from',added.length,{from}));
}

/* -- mode 3: search the whole modeldb -- */
function edUgBrowseBody(){
  const u=state.ed.ug;
  return `<div class="prow" style="grid-template-columns:var(--plw) 1fr">
      <span class="pl">${tt('editor.find_an_entry')}</span>
      <input id="ugFind" value="${esc(u.filter||'')}" placeholder="${ttA('editor.type_part_of_an_entry_name')}"
        oninput="edUgFilter(this.value)"></div>
    <div id="ugHits">${edUgBrowseHits()}</div>`;
}
const UG_HITS_MAX=200;
function edUgBrowseHits(){
  const e=state.ed,qq=(e.ug.filter||'').trim().toLowerCase();
  const have=new Set(csv(edFieldVal('armour_ug_models')));
  const all=(e.d.model_names||[]).concat(e.newModels.map(n=>n.name));
  const hits=all.filter(n=>!qq||n.includes(qq)),shown=hits.slice(0,UG_HITS_MAX);
  // an entry already on the unit is still offered: naming it again is how a tier
  // upgrades the stats without changing the model
  return `<div class="uglist">${shown.map(n=>{
      const dup=have.has(n);
      return `<div class="ugrow" onclick="edUgAddOne('${q1(esc(n))}')">
        <span class="nm">${esc(n)}</span>
        <span class="count">${dup?tt('editor.already_a_tier_click_to_repeat')
                                 :tt('editor.click_to_add_as_the_next')}</span>
      </div>`;}).join('')
      ||`<div class="ugrow have"><span class="count">${tt('editor.no_entry_matches')}</span></div>`}</div>
    <div class="count" style="margin-top:6px">${ttN('editor.hits_of_entries',all.length,{hits:hits.length,x:hits.length>shown.length
        ? tt('editor.showing_the_first_keep_typing',{shown_n:shown.length}):''})}</div>`;
}
// Only the results are redrawn - re-rendering the tab would take the focus out
// of the box on every keystroke.
function edUgFilter(v){
  const e=state.ed; if(!e.ug)return;
  e.ug.filter=v;
  const box=document.getElementById('ugHits');
  if(box)box.innerHTML=edUgBrowseHits(); else edRenderTab();
}
function edUgAddOne(name){
  const e=state.ed,again=csv(edFieldVal('armour_ug_models')).includes(name);
  if(!edUgAppend([name],null,{repeat:true}).length)return;
  e.ug=null; edRenderTab(); edPreview();
  toast(tt('editor.added_as_armour_tier',{name,again:again?tt('editor.a_repeated'):'an'}));
}

/* -- mode 4: a new entry based on one of this unit's -- */
function edUgNewBody(){
  const e=state.ed,u=e.ug;
  const own=(e.d.models||[]).filter(m=>!m.missing).map(m=>m.name);
  if(!own.length)return `<div class="count w-warn">${tt('editor.this_unit_has_no_readable_modeldb')}</div>`;
  return `<div class="prow" style="grid-template-columns:var(--plw) 1fr auto">
      <span class="pl">${tt('editor.base_it_on')}</span>
      <select onchange="state.ed.ug.from=this.value">${own.map(n=>
        `<option value="${esc(n)}" ${u.from===n?'selected':''}>${esc(n)}</option>`).join('')}</select>
      <button class="primary" onclick="edUgNewFromTier()">${tt('editor.set_it_up')}</button></div>
    <div class="count" style="margin-top:7px">${tt('editor.adds_the_tier_and_opens_the')}</div>`;
}
function edUgNewFromTier(){const u=state.ed.ug; edAddArmourTier(u&&u.from);}
// Jump straight to a model's entry in the bmdb tab (the ✎ beside an armour tier
// and the model links elsewhere both land here).
function edJumpModel(name){
  const e=state.ed,key=(name||'').toLowerCase();
  if(!e.d.models.some(m=>m.name===key)){
    if(e.newModels.some(n=>n.name===key)){e.tab='models'; renderEditor(); return;}
    toast(tt('editor.is_not_one_of_this_units',{name})); return;
  }
  e.tab='models'; e.open[key]=true; renderEditor();
  const el=document.querySelector(`#edBody .mentry[data-entry="${cssq(key)}"]`);
  if(el)el.scrollIntoView({block:'center'});
}
// Mode 4 of the ＋ menu: clone `src` (the last tier when unset) into a brand-new
// entry, add it as the next tier, bump armour_ug_levels, and open the form to
// give it its own mesh/texture - an upgrade tier pointing at the same files as
// the tier below it is not an upgrade.
function edAddArmourTier(src){
  const e=state.ed,spec=edUgNewSpec(src);
  if(!spec)return;
  // the tier list and levels are set now so the chips show it straight away;
  // dropping the pending entry puts both back
  const tier=edUgSnapshot();
  if(!edUgAppend([spec.name]).length)return;
  e.form={clone_from:spec.src,name:spec.name,dest_dir:spec.dest_dir,
          mesh_src:'',texture_src:'',normal_src:'',sprite_src:'',
          attach_texture_src:'',attach_normal_src:'',
          // the tier was written into armour_ug_models above, so the EDU slot is
          // already pointed at it - assigning again would append it twice, and
          // `_named` is what that line says, so a rename in this form follows
          mesh_all_lods:true,apply_to_attach:false,assign_to:'',
          _named:spec.name,_tier:tier};
  e.ug=null; e.tab='models'; renderEditor();
}

/* ---- battle model entries ----
   One entry per card: its name, who else uses it, its meshes, ONE set of default
   textures that every faction inherits, the faction checklist (with a per-faction
   override panel where a faction needs its own skin), and the folder its files
   live in. */
const TEX_KINDS=['texture','normal','sprite','attach_texture','attach_normal'];
// the sub-folder the standard layout keeps a model's textures in - mirrors
// edit.TEXTURE_SUBDIR, and the two have to agree or the preview lies
const TEX_SUBDIR='textures';
const KIND_LABEL={texture:tt('editor.texture'),normal:tt('editor.normal_map'),sprite:tt('editor.sprite_spr'),
  attach_texture:tt('editor.attachment_texture'),attach_normal:tt('editor.attachment_normal_map')};
// An attachment has no sprite - the format stores an empty string there - so
// that slot is never offered.
const edKinds=m=>['texture','normal','sprite'].concat(
  m.has_attach?['attach_texture','attach_normal']:[]);
const edFacs=m=>((state.ed.mEdits[m.name]||{}).factions)||m.factions;
// What each faction's slots read right now: the entry's own values, with the
// edits made in this session on top. Anything equal to the default is *not* sent
// as an override, so changing a default really does reach every faction that
// shares it - and only those.
// With a folder move pending, every path shown (and sent) is the one it will
// have AFTER the move - otherwise the boxes would still read the old folder and
// send it straight back.
function edRebase(name,val,kind){
  const me=state.ed.mEdits[name]||{};
  if(!me.move_dir||!val||kind==='sprite')return val;
  const base=me.move_dir.replace(/\/+$/,''),file=val.split('/').pop();
  return (kind==='mesh'?base:base+'/'+TEX_SUBDIR)+'/'+file;
}
function edTexView(m){
  const me=state.ed.mEdits[m.name]||{};
  const defs={},facs={};
  const merged=Object.assign({},m.texture_defaults,me.defaults||{});
  Object.keys(merged).forEach(k=>{defs[k]=edRebase(m.name,merged[k],k);});
  edFacs(m).forEach(f=>{
    const src=Object.assign({},m.textures[f]||{},(me.faction_paths||{})[f]||{}),out={};
    Object.keys(src).forEach(k=>{out[k]=edRebase(m.name,src[k],k);});
    facs[f]=out;});
  return {defs,facs};
}
function edModels(){
  const e=state.ed,d=e.d;
  const pending=e.newModels.map((n,i)=>`<div class="pending">
      <button class="x" onclick="edDropNew(${i})" title="${ttA('editor.discard')}">✕</button>
      <b>${esc(n.name)}</b>${tt('editor.new_entry_cloned_from',{clone_from:q1(esc(n.clone_from)),clone_from2:esc(n.clone_from),assign_to:n.assign_to?` → <code>${esc(n.assign_to)}</code>`:'',_tier:n._tier?` <span class="count">${tt('editor.next_armour_tier')}</span>`:''})}
      <div class="count">${esc(n.dest_dir||tt('editor.no_folder'))} · ${n.mesh_src?esc(n.mesh_src.split(/[\\\/]/).pop()):tt('editor.clone_mesh')}
        · ${n.texture_src?esc(n.texture_src.split(/[\\\/]/).pop()):tt('editor.clone_texture')}${
        n.attach_texture_src?tt('editor.attach_file',{file:esc(n.attach_texture_src.split(/[\\\/]/).pop())})
          :n.apply_to_attach?tt('editor.attachments_follow_the_main_texture'):''}
        <button style="padding:1px 7px;font-size:11px;margin-left:6px" onclick="edEditNew(${i})">${tt('editor.edit')}</button></div></div>`).join('');
  const entries=d.models.map((m,i)=>edModelCard(m,i)).join('');
  return `${pending}${e.form?edNewModelForm():''}
    <div class="count" style="margin-bottom:8px">${tt('editor.paths_are_relative_to_the_mods')}</div>
    ${entries}`;
}
function edModelCard(m,idx){
  const e=state.ed;
  if(m.missing) return `<div class="mentry"><div class="mhead">
      <span class="mn w-bad">${esc(m.name)}</span>
      <span class="count">${tt('editor.missing_from_this_mods_modeldb',{slots:m.slots.length?` · ${m.slots.map(esc).join(', ')}`:''})}</span>
    </div></div>`;
  const open=!!e.open[m.name];
  const me=e.mEdits[m.name]||{};
  const facs=edFacs(m);
  const meshes=m.paths.filter(p=>p.group==='lod').map(p=>{
    const cur=edRebase(m.name,(me.paths&&p.i in me.paths)?me.paths[p.i]:p.value,'mesh');
    return `<div class="prow">
      <span class="pl" title="${esc(p.label)}">${esc(p.label)}</span>
      <input data-entry="${esc(m.name)}" data-i="${p.i}" value="${esc(cur)}"
        title="${esc(cur)}" class="${cur!==p.value?'changed':''}">
      <button onclick="edImportPath('${q1(esc(m.name))}',${p.i},'mesh')">${tt('editor.import')}</button>
      <button onclick="edResetPath('${q1(esc(m.name))}',${p.i})" title="${ttA('editor.undo_this_change')}">↺</button></div>`;
  }).join('');
  const cvOn=!!(e.mcv&&e.mcvName===m.name);
  return `<div class="mentry" data-entry="${esc(m.name)}">
    <div class="mhead" onclick="edToggle('${q1(esc(m.name))}')">
      <span>${open?'▾':'▸'}</span><span class="mn">${esc(m.name)}</span>
      <span class="grow count">${tt('editor.slots_lods_skins',{slots:m.slots.map(esc).join(', ')
        ||(e.bmdb?`<span class="w-warn">${tt('common.nothing_references_it')}</span>`:tt('editor.referenced_by_this_unit')),lods:ttN('editor.lod_count',m.lods.length),skins:ttN('editor.skin_count',facs.length)})}</span>
      <button title="${ttA('editor.draw_this_model_its_parts_its')}"
        onclick="event.stopPropagation();v3Open('${q1(esc(e.mod||state.src))}','${q1(esc(m.name))}')"
        >${tt('editor.view_model')}</button>
      ${open&&!e.bmdb?`<button class="${cvOn?'on':''}" title="${ttA('editor.show_this_entry_exactly_as_battle')}"
        onclick="event.stopPropagation();edModelCv('${q1(esc(m.name))}')">&lt;/&gt;</button>`:''}
      ${edSharedDrop(m)}
    </div>
    ${open?`<div class="cvsplit${cvOn?'':' off'}">
      <div class="mbody2" id="edmGui${idx}">
      <div class="prow" style="grid-template-columns:var(--plw) 1fr auto">
        <span class="pl">${tt('editor.entry_name')}</span>
        <input id="edmn${idx}" value="${esc(me.new_name||m.name)}"
          oninput="edRename('${q1(esc(m.name))}',${idx},this.value)"
          class="${me.new_name?'changed':''}">
        <button onclick="edNewFrom('${q1(esc(m.name))}')">${tt('editor.new_entry_from_this')}</button>
      </div>
      <div class="prow" style="grid-template-columns:var(--plw) 1fr"><span class="pl"></span>
        <span id="edmns${idx}" class="count">${edNameHint(m,me.new_name||m.name)}</span></div>
      <div class="count" style="margin-top:5px">${tt('editor.skeletons',{skeletons:m.skeletons.map(esc).join(', ')||'none'})}</div>
      ${edFolderBox(m)}
      <div class="psec">${tt('editor.meshes_lods')}</div>${meshes||`<div class="count">${tt('common.none')}</div>`}
      ${edDefaultTextures(m)}
      ${edFactionSkins(m)}
      </div>
      ${cvOn?`<div id="edmCode${idx}">${cvHtml(e.mcv)}</div>`:''}
      </div>`:''}</div>`;
}
/* The modeldb pane on the unit editor's Models tab. The BMDB mode has had one
   since Phase 4b; this is the same widget on the same kind, pointed at whichever
   model card is open - one at a time, because two panes of the same file side by
   side is two answers to the same question. */
async function edModelCv(name){
  const e=state.ed;
  if(e.mcv&&e.mcvName===name){cvDrop(e.mcv); e.mcv=null; e.mcvName=''; edRenderTab(); return;}
  if(e.mcv)cvDrop(e.mcv);
  const idx=(e.d.models||[]).findIndex(m=>m.name===name);
  e.mcvName=name;
  e.mcv=cvCreate(bmCvHost(name,'edmGui'+idx,edRenderTab));
  edRenderTab();
  await cvLoad(e.mcv);
  if(state.ed===e&&e.mcv&&e.mcvName===name)edRenderTab();
}
/* "shared with" - every unit that references this entry, each a link that opens
   that unit in its own tab. */
function edSharedDrop(m){
  const users=m.used_by||[],bm=!!state.ed.bmdb;
  if(!users.length)return `<span class="count">${bm?tt('editor.used_by_nothing'):tt('editor.only_this_unit')}</span>`;
  return `<details class="drop" onclick="event.stopPropagation()">
    <summary class="${bm?'':'w-warn'}">${bm?tt('editor.used_by',{users_n:users.length})
      :ttN('editor.shared_with_others',users.length)} ▾</summary>
    <div class="dropbody" style="position:absolute;z-index:5;min-width:230px">
      <div class="count" style="margin-bottom:5px">${tt('editor.editing_this_entry_changes',{bm:bm?tt('editor.every_one_of_them')
        :tt('editor.them_too_use_new_entry_from')})}</div>
      ${users.map(u=>`<div class="urow">${userLink(u)}</div>`).join('')}
    </div></details>`;
}
function edNameHint(m,val){
  const e=state.ed,v=(val||'').trim().toLowerCase();
  if(!v)return `<span class="w-bad">${tt('editor.the_entry_needs_a_name')}</span>`;
  if(v===m.name)return 'unchanged';
  if(/\s/.test(v))return `<span class="w-bad">${tt('editor.entry_names_cannot_contain_spaces')}</span>`;
  if(e.d.model_names.includes(v)||e.newModels.some(n=>n.name===v))
    return `<span class="w-bad">${tt('editor.taken_another_entry_in_this_mod')}</span>`;
  const n=(m.used_by||[]).length+1;
  return ttN('editor.available_references_rewritten',n);
}

/* ---- the default texture set every faction inherits ---- */
function edDefaultTextures(m){
  const v=edTexView(m);
  const rows=edKinds(m).map(k=>`<div class="prow" style="grid-template-columns:var(--plw) 1fr auto">
      <span class="pl">${KIND_LABEL[k]}</span>
      <input data-def="${esc(m.name)}" data-kind="${k}" value="${esc(v.defs[k]||'')}"
        title="${esc(v.defs[k]||'')}"
        class="${(state.ed.mEdits[m.name]||{}).defaults&&k in state.ed.mEdits[m.name].defaults?'changed':''}">
      <button onclick="edImportDefault('${q1(esc(m.name))}','${k}')">${tt('editor.import')}</button></div>`).join('');
  return `<div class="psec">${tt('editor.default_textures_and_sprites')}</div>
    <div class="count">${tt('editor.used_by_every_faction_below_unless')}</div>
    ${rows}`;
}
/* ---- the faction checklist, with a per-faction override panel ---- */
function edFactionSkins(m){
  const e=state.ed,chosen=edFacs(m),set=new Set(chosen);
  const all=(e.d.all_factions||[]).slice();
  chosen.forEach(f=>{if(!all.includes(f))all.push(f);});
  all.sort((a,b)=>edFacLabel(a).localeCompare(edFacLabel(b)));
  const v=edTexView(m),kinds=edKinds(m);
  // Tokens descr_sm_factions.txt does not define. They stay in the list (they
  // are in the file, and unticking one would drop a skin) but they are marked,
  // because a checklist that quietly offers `ents` alongside `timurids` reads as
  // the tool having found a faction the mod does not have.
  const odd=new Set(e.d.unknown_factions||[]);
  const rows=all.map(f=>{
    const on=set.has(f),key=m.name+'|'+f,open=!!e.facOpen[key];
    const uniq=on&&kinds.some(k=>(v.facs[f]||{})[k]&&v.facs[f][k]!==v.defs[k]);
    const bad=odd.has(f.toLowerCase());
    return `<div class="facrow">
        <label class="chk"><input type="checkbox" ${on?'checked':''}
          onchange="edFacToggle('${q1(esc(m.name))}','${q1(esc(f))}',this.checked)">
          ${esc(edFacLabel(f))}</label>
        ${bad?`<span class="fc w-warn" title="${ttA('editor.no_faction_with_this_name_in')}">${tt('editor.not_a_faction_here')}</span>`:''}
        ${on?`<button class="uq ${uniq||open?'on':''}" title="${ttA('editor.give_its_own_textures',{f:esc(f)})}"
          onclick="edFacUnique('${q1(esc(m.name))}','${q1(esc(f))}')">${uniq?tt('editor.unique'):'✎'}</button>`:''}
      </div>${on&&open?edFacUniquePanel(m,f,v,kinds):''}`;
  }).join('');
  return `<div class="psec">${tt('editor.factions_which_factions_this_model_has')}</div>
    <div class="barrow" style="margin-top:4px">
      <button onclick="edFacAll('${q1(esc(m.name))}',true)">${tt('editor.all')}</button>
      <button onclick="edFacAll('${q1(esc(m.name))}',false)">${tt('common.none_2')}</button>
      <span class="count">${tt('editor.selected',{chosen_n:chosen.length,chosen:chosen.length?` ${tt('editor.first_the_record_new_skins_are',{chosen:esc(chosen[0])})}`:''})}</span>
    </div>
    <div class="faclist">${rows}</div>`;
}
function edFacUniquePanel(m,f,v,kinds){
  const cur=v.facs[f]||{};
  return `<div class="facuniq">
    <div class="count" style="margin-bottom:4px"><b>${esc(edFacLabel(f))}</b>${tt('editor.leave_a_box_empty_to_fall')}</div>
    ${kinds.map(k=>{const own=cur[k]&&cur[k]!==v.defs[k];
      return `<div class="prow" style="grid-template-columns:calc(var(--plw) - 10px) 1fr auto">
        <span class="pl">${KIND_LABEL[k]}</span>
        <input data-fac="${esc(m.name)}" data-f="${esc(f)}" data-kind="${k}"
          value="${esc(own?cur[k]:'')}" placeholder="${esc(v.defs[k]||'(default)')}"
          title="${esc(own?cur[k]:v.defs[k]||'')}" class="${own?'changed':''}">
        <button onclick="edImportFac('${q1(esc(m.name))}','${q1(esc(f))}','${k}')">${tt('editor.import')}</button>
      </div>`;}).join('')}</div>`;
}
function edFacToggle(name,fac,on){
  const m=state.ed.d.models.find(x=>x.name===name);
  const me=edTouch(name),list=(me.factions||m.factions).slice(),i=list.indexOf(fac);
  if(on&&i<0)list.push(fac); else if(!on&&i>=0)list.splice(i,1);
  me.factions=list; edRenderTab();
}
function edFacAll(name,on){
  const e=state.ed,m=e.d.models.find(x=>x.name===name),me=edTouch(name);
  if(!on&&m.factions.length){
    // one record has to survive: an entry with no faction skin can't be drawn
    me.factions=[ (me.factions||m.factions)[0] ];
    toast(tt('editor.kept_one_faction_a_battle_model'));
  } else if(on){
    const all=(e.d.all_factions||[]).slice();
    (me.factions||m.factions).forEach(f=>{if(!all.includes(f))all.push(f);});
    me.factions=all;
  }
  edRenderTab();
}
function edFacUnique(name,fac){
  const e=state.ed,k=name+'|'+fac; e.facOpen[k]=!e.facOpen[k]; edRenderTab();
}

/* ---- "all this model's files in one folder" ---- */
function edFolderBox(m){
  const e=state.ed,me=e.mEdits[m.name]||{},f=m.folder,chk=e.folder[m.name];
  const target=me.move_dir||(chk&&chk.target)||f.base||f.suggestion;
  if(me.move_dir) return `<div class="folderbox">
    <b class="w-good">${tt('editor.files_will_move_into_data',{move_dir:esc(me.move_dir)})}</b>
    <div class="count" style="margin-top:4px">${tt('editor.meshes_there_textures_in_textures_sprites',{x:me.move_shared?`<b class="w-warn">${tt('editor.other_entries_using_these_files_are')}</b>`
                      :tt('editor.other_entries_keep_their_paths')})}</div>
    <div class="barrow"><button onclick="edFolderCancel('${q1(esc(m.name))}')">${tt('editor.undo_this_move')}</button></div>
  </div>`;
  // `folders` is already collapsed server-side: a model folder and its
  // textures/ sub-folder are ONE folder (that is the layout), and two spellings
  // of the same folder are one folder too. Attachment sets live in `external`
  // and are never counted - they are shared packs, like sprites.
  const folders=f.folders||[...new Set((f.mesh_dirs||[]).concat(f.texture_dirs||[]))];
  const ext=f.external_dirs||[];
  const extNote=ext.length?`<div class="count" style="margin-top:4px">${tt('editor.attachment_textures_live_in_a_shared',{ext:ext.map(d=>`<span class="fpath">data/${esc(d)}</span>`).join(', ')})}</div>`:'';
  const head=f.standardized
    ? `${tt('editor.model_folder_data',{base:esc(f.base)})}
       <div class="count" style="margin-top:3px">${tt('editor.meshes_here_textures_in_its_one',{TEX_SUBDIR})}</div>${extNote}`
    : `<b class="w-warn">${tt('editor.no_single_model_folder')}</b>
       <div class="count" style="margin-top:3px">${tt('editor.this_entrys_files_are_spread_across',{folders_n:folders.length,folders:folders.map(d=>`<div class="fpath">data/${esc(d||tt('editor.data_root'))}</div>`).join('')})}</div>${extNote}`;
  return `<div class="folderbox${f.standardized?'':' bad'}">
    ${head}
    <div class="frow2">
      <input id="edfd_${esc(m.name)}" value="${esc(target)}" placeholder="unit_models/_Units/my_model">
      <button onclick="edFolderPick('${q1(esc(m.name))}')">${tt('common.browse')}</button>
      <button class="${f.standardized?'':'primary'}" onclick="edFolderCheck('${q1(esc(m.name))}')">${
        f.standardized?tt('editor.change_folder'):tt('editor.standardise')}</button>
    </div>
    ${chk?edFolderCheckHtml(m,chk):''}</div>`;
}
function edFolderCheckHtml(m,chk){
  if(chk.error)return `<div class="count w-bad" style="margin-top:6px">${esc(chk.error)}</div>`;
  if(!chk.moves.length)return `<div class="count w-good" style="margin-top:6px">${tt('editor.nothing_to_move_every_file_is',{target_rel:esc(chk.target_rel)})}</div>`;
  const missing=chk.moves.filter(x=>x.missing);
  const shared=chk.shared_entries||[];
  return `<div style="margin-top:8px;border-top:1px solid var(--edge);padding-top:7px">
    <div class="count">${tt('editor.file_s_would_move',{moves_n:chk.moves.length})}</div>
    <div class="movelist">${chk.moves.map(x=>`<div>${esc(x.old)} → <b>${esc(x.new)}</b>${
      x.missing?` <span class="w-warn">${tt('editor.not_on_disk')}</span>`:''}</div>`).join('')}</div>
    ${missing.length?`<div class="count w-warn" style="margin-top:5px">${tt('editor.of_them_arent_on_disk_those',{missing_n:missing.length})}</div>`:''}
    ${shared.length?`<div class="count w-warn" style="margin-top:6px">${ttN('editor.other_model_entries_share_files',shared.length,{names:shared.map(n=>`<code>${esc(n)}</code>`).join(', ')})}</div>
      <div class="barrow">
        <button class="primary" onclick="edFolderApply('${q1(esc(m.name))}',true)">${tt('editor.edit_and_move_anyway_updating_all',{shared_n:shared.length})}</button>
        <button onclick="edFolderApply('${q1(esc(m.name))}',false)">${tt('editor.move_only_this_entry')}</button>
      </div>`
    :`<div class="barrow"><button class="primary" onclick="edFolderApply('${q1(esc(m.name))}',false)">${tt('editor.move_the_files')}</button></div>`}
  </div>`;
}
function edFolderTarget(name){
  const el=document.getElementById('edfd_'+name); return el?el.value.trim():'';
}
async function edFolderCheck(name){
  const e=state.ed,target=edFolderTarget(name);
  if(!target){toast(tt('editor.give_the_folder_a_path_first'));return;}
  const r=await api.post('/api/edit/model_folder',{mod:e.mod,entry:name,target});
  e.folder[name]=r; edRenderTab();
}
async function edFolderPick(name){
  const r=await api.post('/api/browse_folder',{title:tt('editor.folder_inside_the_mods_data_for')});
  if(!r.path)return;
  const el=document.getElementById('edfd_'+name); if(el)el.value=relInMod(r.path);
  edFolderCheck(name);
}
function edFolderApply(name,shared){
  const chk=state.ed.folder[name]||{},me=edTouch(name);
  me.move_dir=chk.target_rel||edFolderTarget(name); me.move_shared=!!shared;
  delete state.ed.folder[name]; edRenderTab(); edPreview();
}
function edFolderCancel(name){
  const me=edTouch(name); me.move_dir=''; me.move_shared=false;
  edRenderTab(); edPreview();
}

function edToggle(name){const e=state.ed;e.open[name]=!e.open[name];edRenderTab();}
function edME(name){const e=state.ed;
  if(!e.mEdits[name])e.mEdits[name]={new_name:'',paths:{},copies:[],defaults:{},
    faction_paths:{},factions:null,move_dir:'',move_shared:false,_touched:false};
  return e.mEdits[name];}
// Only a *touched* entry is sent to the server - opening a card must never
// rewrite paths that merely happened to be displayed.
function edTouch(name){const me=edME(name); me._touched=true; edStale(); return me;}
function edRename(name,idx,v){
  const me=edTouch(name);
  me.new_name=(v.trim().toLowerCase()===name)?'':v.trim().toLowerCase();
  const m=state.ed.d.models.find(x=>x.name===name);
  const hint=document.getElementById('edmns'+idx);
  if(hint)hint.innerHTML=edNameHint(m,v);
}
function edSetPath(name,i,v){const me=edTouch(name);me.paths[i]=v;}
function edResetPath(name,i){const me=edTouch(name);delete me.paths[i];
  me.copies=(me.copies||[]).filter(c=>c.i!==i); edRenderTab();}
async function edImportPath(name,i,kind){
  const filt=kind==='mesh'?tt('editor.meshes_mesh_mesh_all_files')
            :kind==='sprite'?tt('editor.sprites_spr_spr_all_files')
            :tt('editor.textures_texture_texture_all_files');
  const r=await api.post('/api/browse_file',{title:tt('editor.select_a_file_to_import'),filter:filt});
  if(!r.path)return;
  const m=state.ed.d.models.find(x=>x.name===name);
  const slot=m.paths.find(p=>p.i===i);
  const me=edME(name);
  const cur=(i in me.paths)?me.paths[i]:slot.value;
  const dir=cur.includes('/')?cur.slice(0,cur.lastIndexOf('/')):'unit_models';
  const file=r.path.split(/[\\\/]/).pop();
  me.paths[i]=dir+'/'+file;
  me.copies=(me.copies||[]).filter(c=>c.i!==i).concat([{i,src:r.path,dest_dir:dir}]);
  edRenderTab(); edPreview();
}

/* ---- new bmdb entry cloned from an existing one ---- */
// A name nothing in this mod, and nothing staged this session, has yet.
function edFreeEntryName(base){
  const e=state.ed;
  const stem=(base||'').trim().toLowerCase().replace(/[^a-z0-9_]+/g,'_')||'new_entry';
  const taken=n=>(e.d.model_names||[]).includes(n)||e.newModels.some(x=>x.name===n);
  if(!taken(stem))return stem;
  let n=2; while(taken(`${stem}_${n}`))n++;
  return `${stem}_${n}`;
}
function edNewFrom(name){
  const e=state.ed,m=e.d.models.find(x=>x.name===name)||{};
  // Cloning an entry is nearly always making the next armour tier of it, so the
  // form opens named and pointed like one: <stem>_ug<n>, into the tier after the
  // unit's last. It used to open on `soldier` (or, worse, on whichever tier the
  // clone already filled), so every new entry replaced a model the unit had
  // rather than adding one. Both are still a box and a drop-down - change either.
  const spec=e.bmdb?null:edUgNewSpec(name);
  e.form={clone_from:name,
          name:(spec&&spec.name)||edFreeEntryName(e.newType||e.d.type||name+'_new'),
          dest_dir:(m.folder&&(m.folder.base||m.folder.suggestion))
                   ||('unit_models/'+(e.mod||'').replace(/[^A-Za-z0-9._-]+/g,'_')),
          mesh_src:'',texture_src:'',normal_src:'',sprite_src:'',
          attach_texture_src:'',attach_normal_src:'',
          mesh_all_lods:true,apply_to_attach:false,
          assign_to:e.bmdb?'':edNextTierSlot()};
  e.open[name]=true; edRenderTab();
}
function edEditNew(i){
  const e=state.ed; e.form=Object.assign({_editing:i},e.newModels[i]); edRenderTab();
}
/* ---- where a new entry can be pointed --------------------------------------
   The EDU slots this unit has, plus the one it does NOT have yet: the tier
   after its last armour_ug_models entry. Without that last option the only
   thing the drop-down could do with an armour upgrade was overwrite a tier the
   unit already had, which is not what "add an armour tier" means. Existing
   tiers say what they would replace, so picking one is a choice rather than an
   accident.

   armour_ug_models is read through edFieldVal, not off the file, so a tier
   added earlier in this same session counts. */
function edAssignSlots(){
  const e=state.ed;
  const out=[{v:'',t:tt('editor.dont_change_the_unit')},{v:'soldier',t:tt('editor.soldier_replace')}];
  e.d.fields.forEach(([l])=>{
    if(l.replace(/#\d+$/,'')!=='officer')return;
    const lb=(l==='officer')?'officer#1':l;
    out.push({v:lb,t:lb+' (replace)'});
  });
  const tiers=csv(edFieldVal('armour_ug_models'));
  tiers.forEach((n,i)=>out.push({v:`armour_ug_models#${i+1}`,
    t:tt('editor.armour_ug_models_replace',{x:i+1,x2:n})}));
  out.push({v:`armour_ug_models#${tiers.length+1}`,
    t:tt('editor.armour_ug_models_add_as_a',{tiers:tiers.length+1})});
  return out;
}
// The slot a new entry points at unless you say otherwise: the tier after the
// last one. A new entry is nearly always an upgrade of the model it was cloned
// from, and defaulting to `soldier` made every one of them replace the unit's
// body model instead.
const edNextTierSlot=()=>
  `armour_ug_models#${csv(edFieldVal('armour_ug_models')).length+1}`;
function edNewModelForm(){
  const e=state.ed,f=e.form;
  const from=(e.d.models||[]).find(m=>m.name===f.clone_from)||{};
  const slots=edAssignSlots();
  const file=(v)=>v?esc(v):`<span class="count">${tt('editor.not_set_so_the_clones_file')}</span>`;
  const pick=(key,label,filter)=>`<div class="fbrow"><span class="k">${label}</span>
    <div>${file(f[key])}</div>
    <span class="fbtn"><button onclick="edPickFile('${key}','${filter}')">${tt('editor.choose')}</button>${
      f[key]?`<button class="danger" title="${ttA('editor.leave_this_slot_on_the_clones')}"
        onclick="edClearFormFile('${key}')">✕</button>`:''}</span></div>`;
  const TEX=tt('editor.textures_texture_texture_all_files');
  return `<div class="newmodel">
    <b>${tt('editor.new_model_entry_cloned_from')} <code>${esc(f.clone_from)}</code></b>
    <div class="count" style="margin-top:3px">${tt('editor.sprites_the_faction_ownership_texture_records')}</div>
    <div class="fbrow"><span class="k">${tt('editor.entry_name')}</span>
      <input value="${esc(f.name)}" oninput="edForm('name',this.value)">
      <span></span></div>
    ${(()=>{const refs=edPendingRefs(f._named||'');
      return refs.length?`<div class="fbrow"><span class="k"></span>
        <div class="count">${tt('editor.renaming_it_here_rewrites_to_match',{refs:refs.map(esc).join('</code> <code>')})}</div>
        <span></span></div>`:'';})()}
    <div class="fbrow"><span class="k">${tt('editor.copy_files_into')}</span>
      <input value="${esc(f.dest_dir)}" oninput="edForm('dest_dir',this.value)"
        placeholder="unit_models/my_folder">
      <button onclick="edPickDir()">${tt('common.browse')}</button></div>
    ${pick('mesh_src',tt('editor.mesh_mesh'),tt('editor.meshes_mesh_mesh_all_files'))}
    ${pick('texture_src',tt('editor.texture'),TEX)}
    ${pick('normal_src',tt('editor.normal_map'),TEX)}
    ${pick('sprite_src',tt('editor.sprite_spr'),tt('editor.sprites_spr_spr_all_files'))}
    ${from.has_attach?`
      <div class="psec">${tt('editor.attachment_textures')}</div>
      <div class="count" style="margin-bottom:6px">${tt('editor.has_a_second_texture_group_the',{clone_from:esc(f.clone_from)})}</div>
      ${pick('attach_texture_src',tt('editor.attachment_texture'),TEX)}
      ${pick('attach_normal_src',tt('editor.attachment_normal_map'),TEX)}`
      :`<div class="count" style="margin-top:8px">${tt('editor.has_no_attachment_texture_group_so',{clone_from:esc(f.clone_from)})}</div>`}
    <div style="margin-top:8px">
      <label class="chk"><input type="checkbox" ${f.mesh_all_lods?'checked':''}
        onchange="edForm('mesh_all_lods',this.checked)"> ${tt('editor.use_the_mesh_for_every_lod')}</label>
      ${from.has_attach?`<label class="chk" style="margin-left:14px"
        title="${ttA('editor.point_any_attachment_slot_you_did')}"
        ><input type="checkbox" ${f.apply_to_attach?'checked':''}
        onchange="edForm('apply_to_attach',this.checked)"> ${tt('editor.attachments_fall_back_to_the_main')}</label>`:''}
    </div>
    ${e.bmdb?`<div class="fbrow"><span class="k"></span>
      <div class="count">${tt('editor.no_unit_is_open_so_nothing')}</div>
      <button class="primary" onclick="edAddNewModel()">${
        f._editing===undefined?tt('editor.add_entry'):tt('editor.save_entry')}</button></div>`
    :`<div class="fbrow"><span class="k">${tt('editor.point_edu_slot_at_it')}</span>
      <select onchange="edForm('assign_to',this.value)">
        ${slots.map(s=>`<option value="${esc(s.v)}" ${f.assign_to===s.v?'selected':''}>${
          esc(s.t)}</option>`).join('')}
      </select><button class="primary" onclick="edAddNewModel()">${
        f._editing===undefined?tt('editor.add_entry'):tt('editor.save_entry')}</button></div>`}
  </div>`;
}
function edClearFormFile(key){state.ed.form[key]=''; edRenderTab();}
function edForm(k,v){state.ed.form[k]=v; if(k==='mesh_all_lods'||k==='apply_to_attach')return; }
async function edPickFile(key,filter){
  const r=await api.post('/api/browse_file',{title:tt('editor.select_a_file_to_import'),filter});
  if(r.path){state.ed.form[key]=r.path; edRenderTab();}
}
async function edPickDir(){
  const r=await api.post('/api/browse_folder',{title:tt('editor.folder_inside_the_mods_data_to')});
  if(r.path){state.ed.form.dest_dir=relInMod(r.path); edRenderTab();}
}
/* ---- a pending entry that an EDU line already names -----------------------
   Mode 4 of the armour-tier menu writes the tier into `armour_ug_models` the
   moment it is added and only then opens the form, so renaming the entry in
   that form left the unit pointing at a name that was never going to exist.
   The lines the PAGE wrote are followed here; `assign_to` needs none of this,
   because the server writes whatever the entry is called at save time.

   `_named` is what the entry is called in those lines right now, which is not
   always what it was called last: the form can be reopened and renamed again. */
function edPendingRefs(name){
  const e=state.ed,out=[];
  if(!name)return out;
  if(csv(edFieldVal('armour_ug_models')).includes(name))out.push('armour_ug_models');
  if((edFieldVal('soldier').split(',')[0]||'').trim().toLowerCase()===name)out.push('soldier');
  e.d.fields.forEach(([l])=>{
    if(l.replace(/#\d+$/,'')==='officer'
       &&(edFieldVal(l)||'').trim().toLowerCase()===name)out.push(l);
  });
  return out;
}
function edRenamePending(from,to){
  const e=state.ed,hit=edPendingRefs(from);
  if(!from||!to||from===to||!hit.length)return [];
  hit.forEach(label=>{
    if(label==='armour_ug_models'){
      edSetField(label,csv(edFieldVal(label)).map(m=>m===from?to:m).join(', '));
    }else if(label==='soldier'){
      const parts=edFieldVal(label).split(',');
      const lead=parts[0].slice(0,parts[0].length-parts[0].replace(/^\s+/,'').length);
      parts[0]=lead+to; edSetField(label,parts.join(','));
    }else{
      edSetField(label,to);
    }
  });
  return hit;
}
function edAddNewModel(){
  const e=state.ed,f=e.form;
  if(!f.name.trim()){toast(tt('editor.the_new_entry_needs_a_name'));return;}
  const entry=Object.assign({},f,{name:f.name.trim().toLowerCase()});
  const at=entry._editing; delete entry._editing;
  // what the unit's own lines call it at this moment: the name this form opened
  // on for a tier, or the pending entry's previous name when it is being edited
  const prev=(at===undefined)?(f._named||''):((e.newModels[at]||{}).name||'');
  if(at===undefined)e.newModels.push(entry); else e.newModels[at]=entry;
  const moved=edRenamePending(prev,entry.name);
  entry._named=moved.length?entry.name:(prev?prev:entry._named||'');
  e.form=null; edRenderTab(); edPreview();
  if(moved.length)
    toast(ttN('editor.renamed_and_follows',moved.length,{name:entry.name,moved:moved.join(' and ')}),4200);
}
// Discarding a pending entry has to undo what adding it changed - an armour tier
// also wrote armour_ug_models / armour_ug_levels.
function edDropNew(i){
  const e=state.ed,[gone]=e.newModels.splice(i,1);
  if(gone&&gone._tier){
    edRestoreField('armour_ug_models',gone._tier.models);
    edRestoreField('armour_ug_levels',gone._tier.levels);
  }
  edRenderTab(); edPreview();
}

/* ---- preview / save / delete ---- */
// bmdb mode posts the very same body to the very same planner, minus the unit -
// see unittransfer.edit.plan_bmdb.
const edApi=p=>(state.ed&&state.ed.bmdb?'/api/bmdb/':'/api/edit/')+p;
async function edPreview(){
  const box=document.getElementById('edPreview'); if(!box)return null;
  await cvSettle(state.ed.cv);          // read the last keystroke before planning
  const blocked=edCvBlocked();
  if(blocked){box.innerHTML=`<div class="preview w-bad">${esc(blocked)}</div>`; return null;}
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post(edApi('plan'),edPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.ed.plan=r; state.ed.planStale=false;
  box.innerHTML=edPlanHtml(r);
  // the unit being compared against is a save of its own, so it gets its own
  // plan under the first one rather than being silently left out of it
  if(edCmpDirty()){
    const cr=await api.post('/api/edit/plan',edCmpPayload());
    box.insertAdjacentHTML('beforeend',cr.error
      ? `<div class="preview w-bad">${esc(state.ed.cmp.unit)}: ${esc(cr.error)}</div>`
      : `<div class="count" style="margin-top:8px">${tt('editor.and_for',{unit:esc(state.ed.cmp.unit)})}</div>`+edPlanHtml(cr));
  }
  // …and so is the Recruitment tab: a different file, planned by the buildings
  // planner, so it gets its own block rather than being folded into the unit's
  if(edRecDirty()){
    const rr=await api.post('/api/buildings/plan',edRecPayload());
    box.insertAdjacentHTML('beforeend',
      `<div class="count" style="margin-top:8px">${tt('editor.and_for_recruitment_export_descr_buildings')}</div>`
      +bldPlanHtml(rr,false));
  }
  return r;
}
function edStale(){const e=state.ed;
  // every path that changes a field ends here, so this is where the text pane
  // finds out it has to be re-serialised
  if(e&&e.cv)cvFromGui(e.cv);
  if(e&&e.plan&&!e.planStale){e.planStale=true;
  const b=document.getElementById('edPreview'); if(b)b.innerHTML=edPlanHtml(e.plan,true);}}
function edPlanHtml(r,stale){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">✎</span><span class="stext">${tt('editor.pending_changes',{stale:stale?` <span class="w-warn">${tt('editor.edited_since_this_probe_press_probe')}</span>`:''})}</span></div>
    ${li('',r.changes.length?r.changes:['no changes'])}
    ${r.files_written.length?`<div class="srow"><span class="sicon">💾</span><span class="stext">${tt('editor.writes',{x:r.files_written.map(f=>`<span class="path">${esc(f)}</span>`).join(', ')})}</span></div>`:''}
    ${(r.ref_counts||[]).length?`<div class="srow"><span class="sicon">🔗</span><span class="stext">${tt('editor.the_renamed_unit_is_followed_into',{ref_counts_n:r.ref_counts.length,ref_counts:r.ref_counts.map(x=>`<span class="path">${esc(x.file)}</span> <b>×${x.hits}</b>`).join(', ')})}</span></div>`:''}
    ${li('warn',r.warnings)}${li('bad',r.errors)}</div>`;
}
/* Everything this page remembers about a mod's battle_models.modeldb, dropped.

   Both are read once and kept for the session, which was right while the mod
   only ever changed under us: the field editor's vocabulary (the `model` list
   behind the soldier / armour_ug_models boxes) and the ⌕ picker's entry table.
   A save that creates an entry makes both of them wrong, and being wrong here
   reads as "the entry I just made is not in the modeldb" - so a save that could
   have touched the file throws them away and the next question re-asks. */
function edDropModCaches(mod){
  if(state.vocab){delete state.vocab[mod]; delete state.vocab['?'+mod];}
  if(state.mp&&state.mp.mod===mod)state.mp=null;
}
async function edSave(){
  const e=state.ed,bm=!!e.bmdb;
  await cvSettle(e.cv);                 // the last keystroke counts
  const blocked=edCvBlocked();
  if(blocked){toast(blocked); return;}
  const one=edDirty(),two=edCmpDirty(),rec=edRecDirty();
  if(!one&&!two&&!rec){toast(tt('editor.nothing_to_save'));return;}
  // Both units are planned BEFORE either is written, so a problem with the
  // second one is found while nothing has been touched - half a save is worse
  // than none when the two were being balanced against each other.
  let r=null,cr=null;
  if(one){
    r=await api.post(edApi('plan'),edPayload());
    if(r.error){toast(tt('editor.error_reason',{error:r.error}));return;}
    if(r.errors&&r.errors.length){
      document.getElementById('edPreview').innerHTML=edPlanHtml(r);
      toast(r.errors[0]);return;}
  }
  if(two){
    cr=await api.post('/api/edit/plan',edCmpPayload());
    if(cr.error){toast(tt('editor.error_in',{unit:e.cmp.unit,error:cr.error}));return;}
    if(cr.errors&&cr.errors.length){toast(`${e.cmp.unit}: ${cr.errors[0]}`);return;}
  }
  // The recruit pools are a third, independent write - a different file, planned
  // by the buildings planner - and it is checked here with the other two so a
  // problem in it is found while nothing has been touched.
  if(rec){
    const rp=await api.post('/api/buildings/plan',edRecPayload());
    if(rp.error){toast(tt('editor.recruitment_error',{error:rp.error}),5000);return;}
    if(rp.errors&&rp.errors.length){toast(tt('editor.recruitment_error',{error:rp.errors[0]}),5000);return;}
  }
  const what=bm?e.d.models[0].name:e.unit;
  const writing=[one?what:null,two?e.cmp.unit:null,
                 rec?tt('editor.recruit_pool_s',{edRecChangeCount:edRecChangeCount()}):null]
    .filter(Boolean).join(' and ');
  document.getElementById('modal').innerHTML=`<h2>${tt('editor.saving')}</h2>
    <div class="mbody"><div class="progress-track"><div class="progress-fill" style="width:60%"></div></div>
    <div class="count" style="margin-top:8px">${tt('editor.writing_into',{writing:esc(writing),mod:esc(e.mod)})}</div></div>`;
  let res=null;
  if(one){
    res=await api.post(edApi('apply'),edPayload({clear_strings_bin:clearBinOn()}));
    if(res.error){toast(tt('editor.save_failed_reason',{error:res.error}));bm?renderBmdbEditor():renderEditor();return;}
  }
  if(two){
    const res2=await api.post('/api/edit/apply',edCmpPayload({clear_strings_bin:clearBinOn()}));
    if(res2.error){
      toast(one?tt('editor.saved_but_saving_failed',{what,unit:e.cmp.unit,error:res2.error}):tt('editor.saving_failed_alone',{unit:e.cmp.unit,error:res2.error}),5000);
      renderEditor(); return;}
    if(!res)res=res2;
    e.cmp.ov={}; e.cmp.rm=new Set(); e.cmp.added=new Set();
  }
  let pools=0;
  if(rec){
    pools=edRecChangeCount();
    const res3=await api.post('/api/buildings/apply',edRecPayload());
    if(res3.error){
      toast(tt((one||two)?'editor.unit_saved_recruit_pools_failed':'editor.the_recruit_pools_failed',{error:res3.error}),6000);
      // the unit's own save landed; the tab has to stop showing what did not
      await edRecReload();
      renderEditor(); return;
    }
    /* The EDB has moved under everything that indexes it. A building line left
       open behind this editor numbers its capability rows against the old file,
       so its working copy goes - `backToBuilding` then re-reads the line from
       disk rather than splicing against numbers that have shifted. With nothing
       to go back to, the whole overview goes and the next visit re-reads it,
       recruit counts and all; the sidebar filters are rewired with it, since
       they hold a reference to the object being dropped. */
    if(state.bldReturn&&state.bld){
      state.bld.work=null; state.bld.plan=null; state.bld.checks=null; state.bld.cmp=null;
    }else{ state.bld=null; _bldFiltersFor=''; }
  }
  closeModal();
  const saved=[one?(bm?what:res.plan.resolved_type):null,two?e.cmp.unit:null].filter(Boolean);
  const note=saved.length
    ? tt(pools?'editor.saved_names_and_pools':'editor.saved_names',{pools,
        saved:saved.length>1?tt('editor.name_and_name',{a:saved[0],b:saved[1]}):tt('editor.name_quoted',{a:saved[0]})})
    : tt('editor.saved_recruit_pool_s',{pools});
  toast(tt('editor.undo_in_log',{note,x:binMsg(res)}),4200);
  state.destData=null; state.bmdb=null;
  edDropModCaches(e.mod);
  // a replaced card keeps its URL, so every <img> on the page has to be asked
  // for again or the grid goes on showing the picture that was just overwritten
  imgBust();
  loadSource();
}
