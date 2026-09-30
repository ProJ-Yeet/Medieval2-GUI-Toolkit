/* minorfiles.js - Minor Files mode: the five small campaign files, one screen

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= MINOR FILES MODE =======================
   Five files nobody would open a module for on their own, and one module
   because they are all read the same afternoon: a mod's rebels, its religions,
   what its provinces trade, what its settlements look like and what its people
   are called.

   They are three shapes, not five (see unittransfer/minorfiles.py), and that is
   what lets one list, one pane and one save serve all five tabs. What differs
   per tab is the form - and two tabs are deliberately edit-only:

     * RESOURCES - the engine's list of 28 is closed. A `type` it does not know
       is read and then ignored, so "create a resource" would be a button that
       writes a line nothing reads.
     * CULTURES - a culture is eleven settlement models and cards, a fort, a
       port ladder, a watchtower and six agents. Nothing a text editor creates.

   And one tab writes four files at once: adding a religion writes its block,
   joins it to the `religions { … }` list, appends it to
   descr_religions_lookup.txt and creates its name in text/religions.txt. A
   religion that reaches three of the four half exists, so they are one job with
   one backup set and one undo.

   THE PAGE NEVER PARSES A GAME FILE: /api/minor, /api/minor/record and
   /api/minor/plan|apply do all of it, and a save posts back the shape the
   server's own render_any takes.

   CULTURES IS ITS OWN MODE (Phase 46) and still this screen: the `cultures`
   mode is the same list, pane and save locked to the cultures tab, which is
   why every "is this screen still up" check asks `mfMode()` rather than for
   the one mode id. */
const mfMode = () => state.mode === 'minor' || state.mode === 'cultures';

function renderCultures(){
  if(!state.mf || state.mf.tab !== 'cultures'){
    minorWantTab = 'cultures'; state.mf = null; loadMinor(); return;
  }
  renderMinor();
}

async function loadMinor(){
  const mod = state.src, mode = state.mode;
  let tab = minorWantTab || (state.mf && state.mf.tab) || 'rebels';
  // the cultures tab is the cultures mode now; the minor mode never shows it
  if(mode === 'cultures') tab = 'cultures';
  else if(tab === 'cultures') tab = 'rebels';
  minorWantTab = null;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('minorfiles.s_campaign_files')}</div>`;
  let r;
  try{ r = await api.get(`/api/minor?mod=${enc(mod)}&tab=${enc(tab)}`); }
  catch(e){ if(stale(mode, mod)) return;
    main.innerHTML = `<div class="empty">${tt('minorfiles.couldnt_read_the_campaign_files')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadMinor()">${tt('common.retry')}</button></div>`; return; }
  if(stale(mode, mod)) return;
  state.mf = Object.assign({tab, sel:'', d:null, busy:false, adding:false}, r);
  undoReset();
  renderMinor();
}

function mfTab(id){
  const f = state.mf;
  if(!f || f.tab === id) return;
  f.tab = id; f.sel = ''; f.d = null; f.adding = false;
  loadMinor();
}

function renderMinor(){
  const f = state.mf;
  if(!f){ loadMinor(); return; }
  const rows = mfRows();
  count.textContent = f.exists ? `${rows.length}/${f.count}` : '';
  main.innerHTML = mfTabsHtml() + (f.exists ? `<div class="trwrap">
    <div class="trlist">
      ${f.actions.includes('add')
        ? `<button class="trnew" onclick="mfNew()">${tt('minorfiles.new',{noun:esc(f.noun)})}</button>` : ''}
      ${findingsHtml('minor:' + f.tab, f.finding_list, 'mfOpen')}
      <div class="trrows">${rows.map(mfRowHtml).join('')
        || `<div class="count" style="padding:8px">${tt('minorfiles.no_matches',{noun:esc(f.noun)})}</div>`}</div>
    </div>
    <div class="trmain" id="mfMain">${mfDetailHtml()}</div>
  </div>` : `<div class="empty">${tt('minorfiles.it_would_live_in_data',{x:esc(f.error || tt('minorfiles.this_mod_has_not_got_that')),file:esc(f.file)})}</div>`);
}

const mfTabsHtml = () => minorTabsHtml(state.mf.tab, 'data/' + state.mf.file);

// Filtered in the page. The biggest list here is 28 factions of names or 68
// rebel factions - the file was parsed once to build it, and there is nothing
// left to page.
function mfRows(){
  const q = search.value.trim().toLowerCase();
  const rows = state.mf.records || [];
  if(!q) return rows;
  return rows.filter(r => r.name.toLowerCase().includes(q)
    || (r.label||'').toLowerCase().includes(q));
}

function mfRowHtml(r){
  const f = state.mf, on = f.sel === r.name;
  let sub = '';
  if(f.tab === 'rebels') sub = ttN('minorfiles.category_chance_units',r.units,{category:esc(r.category||tt('minorfiles.no_category')),chance:esc(r.chance||'0')});
  else if(f.tab === 'resources') sub = `trade ${esc(r.trade_value||'0')}${
    r.has_mine?tt('minorfiles.has_a_mine'):''}${r.known?'':` ${tt('minorfiles.not_an_engine_resource')}`}`;
  else if(f.tab === 'religions') sub = r.listed
    ? esc(r.pip_path||tt('minorfiles.no_pip')) : `<b>${tt('minorfiles.not_in_the_religions_list')}</b>`;
  else if(f.tab === 'cultures') sub = ttN('minorfiles.settlement_levels_agents',r.levels,{agents:r.agents});
  else sub = Object.entries(r.sections||{}).map(([k,n]) => `${n} ${k}`).join(' · ')
    || `<b>${tt('minorfiles.no_names_at_all')}</b>`;
  return `<button class="trrow${on?' on':''}" onclick="mfOpen('${q1(esc(r.name))}')">
    <span class="nm">${esc(r.label)}</span><br>
    <span class="sub">${sub}${r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</span>
  </button>`;
}

async function mfOpen(name){
  activity(tt('minorfiles.opened_record'), tt('minorfiles.in',{name,tab:state.mf.tab,src:state.src}));
  const f = state.mf;
  f.sel = name; f.adding = false; f.d = null;
  renderMinor();
  let d;
  try{ d = await api.get(
    `/api/minor/record?mod=${enc(f.mod)}&tab=${enc(f.tab)}&name=${enc(name)}`); }
  catch(e){ d = {error:''+e}; }
  if(!mfMode() || state.mf !== f || f.sel !== name) return;
  f.d = d.error ? d : mfWorking(d);
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
  mfPaint();
  if(!d.error && state.settings.code_view) mfCvToggle();
}

function mfWorking(d){
  d.w = JSON.parse(JSON.stringify(d.record));
  d.locEdits = {};
  return d;
}

// A blank record per tab, in the shape that tab's `edits` takes - the same shape
// the server's own new_any() writes from, so a create and a save agree.
function mfBlank(tab){
  if(tab === 'rebels') return {name:'', category:'brigands', chance:'50',
    description:'', units:[]};
  if(tab === 'religions') return {name:'', pip_path:''};
  if(tab === 'names') return {name:'', sections:[{name:'characters', entries:[]}]};
  return {name:''};
}

function mfNew(){
  const f = state.mf;
  f.sel = ''; f.adding = true;
  const blank = mfBlank(f.tab);
  f.d = {name:'', label:tt('minorfiles.new_2',{noun:f.noun}), tab:f.tab, file:f.file, noun:f.noun,
    record:blank, w:JSON.parse(JSON.stringify(blank)), findings:[], loc:{},
    locEdits:{}, missing_loc:[], loc_writable:true,
    // 89b: a new resource's name is a key M2EX derives from it, in strat.txt
    loc_tag:f.tab === 'resources' ? mfResourceTag('') : '',
    loc_file:f.tab === 'resources' ? 'text/strat.txt' : '',
    known:(f.records||[]).map(r=>r.name), actions:f.actions,
    vocab:(f.d && f.d.vocab) || {}};
  renderMinor();
  mfLoadVocab();
}

// SMT_RESOURCE_<NAME>, the key M2EX reads a resource's name under (89b)
const mfResourceTag = name => 'SMT_RESOURCE_' + ((name || '').trim().toUpperCase() || 'NAME');

/* ---- clone ----
   A rebel faction is a category, a chance and a LIST OF UNITS, and building the
   next one meant picking every unit out of a mod-wide dropdown again. This
   starts a new record holding everything the open one holds, under a free name,
   and leaves it unsaved so the name and the units can be adjusted before Create.

   The copy is staged in the page, not on the server: `add` already takes the
   whole record shape, so a clone is a create whose form arrives filled in. */
function mfClone(){
  const f = state.mf, d = f.d;
  if(!d || !d.w || !(f.actions||[]).includes('add')) return;
  const known = new Set((f.records||[]).map(r => r.name));
  const stem = d.name || 'new';
  let name = stem + '_copy';
  for(let n = 2; known.has(name); n++) name = stem + '_copy' + n;
  const w = JSON.parse(JSON.stringify(d.w));
  w.name = name;
  // a rebel faction's text key IS its `description` value, so a copy that kept
  // the original's would show the ORIGINAL's name on the campaign map
  if(f.tab === 'rebels') w.description = name;
  const was = d.loc_tag || '';
  // both tabs that have a writable text key are keyed by something that just
  // became the new name - a rebel by its `description`, a religion by itself
  const tag = (f.tab === 'rebels' || f.tab === 'religions') ? name
    : f.tab === 'resources' ? mfResourceTag(name) : '';
  // 89b: a copied resource keeps the donor's model, copies its icon to a file
  // of its own, and is not called by the donor's name
  if(f.tab === 'resources') w.icon_from = d.name;
  const shown = f.tab === 'resources' ? '' : was ? ((d.locEdits||{})['#name'] !== undefined ? d.locEdits['#name']
                       : ((d.loc||{})[was] || '')) : '';
  f.sel = ''; f.adding = true;
  f.d = {name:'', label:tt('minorfiles.copy_of',{label:d.label}), tab:f.tab, file:f.file, noun:f.noun,
    record:JSON.parse(JSON.stringify(w)), w,
    findings:[], loc:{}, locEdits:(tag && shown) ? {'#name':shown} : {},
    missing_loc:tag ? [tag] : [], loc_tag:tag, loc_file:d.loc_file || '',
    loc_writable:f.tab === 'resources' || d.loc_writable !== false,
    loc_note:f.tab === 'resources' ? '' : d.loc_note || '',
    known:[...known], actions:f.actions, vocab:d.vocab || {}};
  renderMinor();
  const carried = f.tab === 'rebels'
    ? tt('minorfiles.unit_s_and_every_field_came',{n:(w.units||[]).length})
    : tt('minorfiles.every_field_came_with_it');
  toast(tt('minorfiles.copied_as_nothing_written',{source:d.name,name,carried}), 6500);
}

// The pickers (this mod's unit list, its settlement levels) come with a record,
// and a brand-new one has no record to come with - so fetch them off any
// existing row rather than shipping a second endpoint for the same answer.
async function mfLoadVocab(){
  const f = state.mf;
  if(!f.adding || !f.records || !f.records.length) return;
  if(f.d.vocab && Object.keys(f.d.vocab).length) return;
  let d;
  try{ d = await api.get(`/api/minor/record?mod=${enc(f.mod)}&tab=${enc(f.tab)}`
    + `&name=${enc(f.records[0].name)}`); }
  catch(e){ return; }
  if(!mfMode() || state.mf !== f || !f.adding) return;
  f.d.vocab = d.vocab || {};
  mfPaintForm();
}

function mfPaint(){
  const el = document.getElementById('mfMain');
  if(el) el.innerHTML = mfDetailHtml();
  const d = state.mf.d;
  if(d && d.cv){ cvWire(d.cv); cvBindHover(d.cv, document.getElementById('mfGui')); }
}

// The form only - never the pane, which has the caret in it.
function mfPaintForm(){
  const d = state.mf.d, el = document.getElementById('mfGui');
  if(!d || !el) return;
  el.innerHTML = mfFindingsHtml(d) + mfFormHtml(d);
  if(d.cv) cvBindHover(d.cv, el);
}

/* ---- the detail pane ---- */
function mfDetailHtml(){
  const f = state.mf, d = f.d;
  if(!f.sel && !f.adding) return `<div class="empty">${ttN('minorfiles.pick_a_noun_on_the_left',f.count,{noun:esc(f.noun),file:esc(f.file),refused:f.refused ? `<div class="trnote"
      style="max-width:560px;margin:14px auto;text-align:left">${esc(f.refused)}</div>`
      : ''})}</div>`;
  if(!d) return `<div class="empty">${tt('minorfiles.reading_the',{noun:esc(f.noun)})}</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(f.adding ? tt('minorfiles.new_noun',{noun:f.noun}) : d.label)}</b>
        <span class="count">${esc(f.file)}</span></div>
      <span class="sp"></span>
      ${f.adding ? '' : `<button class="${d.cv?'on':''}" title="${ttA('minorfiles.show_this_exactly_as_stores_it',{noun:esc(f.noun),file:esc(f.file)})}"
        onclick="mfCvToggle()">${tt('common.code_view')}</button>
      ${(d.actions||[]).includes('add')
        ? `<button onclick="mfClone()" title="${ttA('minorfiles.start_a_new_holding_everything_this',{noun:esc(f.noun)})}">${tt('minorfiles.clone')}</button>` : ''}
      ${(d.actions||[]).includes('duplicate')
        ? `<button onclick="mfDuplicate()" title="${ttA('minorfiles.a_new_culture_this_ones_whole')}">${tt('minorfiles.duplicate')}</button>` : ''}
      ${(d.actions||[]).includes('merge')
        ? `<button onclick="mfMergeOpen()" title="${ttA('minorfiles.add_every_name_another_faction_keeps')}">${tt('minorfiles.merge_names')}</button>
      <button onclick="mfDedupe()" title="${ttA('minorfiles.clear_the_names_this_faction_lists')}">${tt('minorfiles.remove_duplicates')}</button>` : ''}
      ${(d.actions||[]).includes('delete')
        ? `<button class="danger" onclick="mfDelete()">${tt('common.delete')}</button>` : ''}`}
      <button class="primary" onclick="mfSave()">${f.adding?tt('common.create'):tt('common.save')}</button>
    </div>
    <div id="mfGui">
      ${mfFindingsHtml(d)}
      ${mfFormHtml(d)}
    </div>
    ${d.cv ? `<div id="mfCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}`;
}

function mfFindingsHtml(d){
  const out = (d.findings||[]).map(f =>
    `<div class="trfind w-warn">${tt('minorfiles.line',{line:f.line,message:esc(f.message)})}</div>`);
  if((d.missing_loc||[]).length && d.loc_writable) out.push(`<div class="trfind w-warn">
    ${tt('minorfiles.there_is_no_entry_in_so',{loc_tag:esc(d.loc_tag),loc_file:esc(d.loc_file),noun:esc(d.noun)})}</div>`);
  return out.join('');
}

/* ---- the forms, one per tab ---- */
function mfFormHtml(d){
  const f = state.mf;
  if(f.tab === 'rebels') return mfRebelForm(d);
  if(f.tab === 'resources') return mfResourceForm(d);
  if(f.tab === 'religions') return mfReligionForm(d);
  if(f.tab === 'cultures') return mfCultureForm(d);
  return mfNamesForm(d);
}

// The name box and, beside it, what the player actually reads. Same widget the
// traits and ancillaries editors use - except on the resources tab, where the
// text file behind it is read by position and only the Strings module can write
// it safely.
/* ---- the art these files point at ----
   A religion's pip, a resource's icon and a culture's settlement cards are all
   `.tga` paths under the mod's data/, and until now the editor showed them as
   text while the Buildings gallery showed its own art as pictures. Same server
   route as a faction symbol (`kind=modfile`), which is what keeps the path
   inside data/ - the page never gets to name an absolute file.

   A blank slot is NOT reported as a fault, and that is Phase 10a's ruling, not
   an oversight: every pip and settlement card in these files can legitimately
   live inside the game's own .pack archives, which the toolkit cannot read.
   Checking anyway produced 78 findings across three mods and 77 were noise. */
function mfArt(rel){
  // The two files disagree about the prefix and both are right: a resource icon
  // and a settlement card are written `data/ui/…` while a religion's pip is
  // written `ui/pips/…`. The server resolves everything under the mod's data/,
  // so the redundant half is dropped here rather than in one of the parsers -
  // neither file is wrong about its own format.
  const r=(rel||'').trim().replace(/\\/g,'/').replace(/^data\//i,'');
  if(!r)return `<span class="mfnoart" title="${ttA('minorfiles.no_path_set')}">${tt('common.none')}</span>`;
  // These sit in dense tables with no room for a pair of buttons, so the pip
  // itself is the ✎ - a click replaces it, and a right-click gets the same menu
  // (with "Open file location" on it) that every other picture in the tool has.
  const url=`/icon?mod=${enc(state.mf.mod)}&kind=modfile&rel=${enc(r)}${iconBust()}`;
  return `<img class="mfpip act" loading="lazy" src="${url}"
    alt="" title="${ttA('minorfiles.blank_here_means_the_file_is',{x:esc(r)})}"
    onclick="imgPick('${q1(esc(url))}','mfPaint')"
    onerror="this.classList.add('gone')">`;
}
function mfNameRow(d, placeholder){
  const w = d.w, tag = d.loc_tag || '';
  const shown = tag ? (d.locEdits['#name'] !== undefined ? d.locEdits['#name']
                       : ((d.loc||{})[tag] || '')) : '';
  return `<label class="lbl" data-label="name">${tt('common.name')}</label>
    <div class="${tag?'trkey':''}">
      <input data-label="name" value="${esc(w.name)}"
        ${state.mf.adding?'':'disabled'} placeholder="${esc(placeholder||'')}"
        oninput="mfSet('name',this.value.trim())">
      ${tag ? `<input class="trtext" value="${esc(shown)}"
        ${d.loc_writable?'':'disabled'}
        placeholder="${esc(d.loc_writable
          ? (((d.loc||{})[tag] === undefined) ? tt('minorfiles.not_in_file_yet',{file:d.loc_file})
             : tt('minorfiles.what_the_player_reads'))
          : (shown || tt('minorfiles.read_by_position_so_edit_it')))}"
        title="${esc(d.loc_writable ? tt('minorfiles.what_the_player_reads_saved_into_file',{file:d.loc_file}) : d.loc_note || '')}"
        oninput="mfSetLocName(this.value)">` : ''}
    </div>
    ${tag && !d.loc_writable ? `<span></span><div class="trhint count">${
      esc(d.loc_note||'')}</div>` : ''}`;
}

function mfRebelForm(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.the_rebel_faction_what_spawns_in')}</div>
    <div class="trgrid">
      ${mfNameRow(d, 'Evil_Rebels')}
      <label class="lbl" data-label="category">${tt('common.category')}</label>
      <div>
        <select data-label="category" onchange="mfSet('category',this.value)">
          ${(v.categories||[]).map(c =>
            `<option value="${esc(c)}"${c===w.category?' selected':''}>${esc(c)}</option>`).join('')}
          ${(v.categories||[]).includes(w.category) ? ''
            : `<option value="${esc(w.category)}" selected>${esc(w.category)} (unknown)</option>`}
        </select>
        <div class="trhint count">${tt('minorfiles.the_four_the_engine_knows_anything')}</div>
      </div>
      <label class="lbl" data-label="chance">${tt('minorfiles.chance')}</label>
      <input data-label="chance" value="${esc(w.chance)}"
        oninput="mfSet('chance',this.value.trim())">
      <label class="lbl" data-label="description">${tt('minorfiles.description_key')}</label>
      <input data-label="description" value="${esc(w.description)}"
        placeholder="${esc(w.name||'')}"
        oninput="mfSet('description',this.value.trim())">
    </div>
    <div class="treffects">
      <div class="trsechead" style="margin:8px 0 0">${tt('minorfiles.units_a_rebel_faction_with_none',{n:(w.units||[]).length})}</div>
      ${(w.units||[]).map((u,k)=>`<div class="treff" data-label="unit#${k+1}">
        <input class="trattr" value="${esc(u)}" list="mfUnits"
          placeholder="${ttA('minorfiles.unit_type')}" oninput="mfSetUnit(${k},this.value)">
        <span class="count" id="mfu${k}">${esc(mfUnitLabel(d, u))}</span>
        <button class="trgdel" onclick="mfDelUnit(${k})">✕</button>
      </div>`).join('')}
      <datalist id="mfUnits">${(v.units||[]).map(u =>
        `<option value="${esc(u.type)}">${esc(u.label)}</option>`).join('')}</datalist>
      <button class="trgadd" onclick="mfAddUnit()">${tt('minorfiles.add_unit')}</button>
    </div>
  </section>`;
}

// The picker offers this mod's units under their in-game names; the line itself
// holds the EDU type, so the name is shown beside the box rather than in it.
function mfUnitLabel(d, type){
  if(!type) return '';
  const hit = ((d.vocab||{}).units||[]).find(u => u.type === type);
  return hit ? hit.label : tt('minorfiles.not_a_unit_in_this_mod');
}

function mfResourceForm(d){
  const w = d.w;
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.the_resource_placed_on_the_campaign')}</div>
    <div class="trgrid">
      ${mfNameRow(d, 'timber')}
      <label class="lbl" data-label="trade_value">${tt('minorfiles.trade_value')}</label>
      <input data-label="trade_value" value="${esc(w.trade_value)}"
        oninput="mfSet('trade_value',this.value.trim())">
      <label class="lbl" data-label="item">${tt('minorfiles.model_item')}</label>
      <input data-label="item" value="${esc(w.item)}"
        placeholder="data/models_strat/resource_x.CAS"
        oninput="mfSet('item',this.value.trim())">
      <label class="lbl" data-label="icon">${tt('minorfiles.icon')}</label>
      <div class="mfart">
        ${mfArt(w.icon)}
        <input data-label="icon" value="${esc(w.icon)}"
          placeholder="data/ui/resources/resource_x.tga"
          oninput="mfSet('icon',this.value.trim())">
      </div>
      <label class="lbl" data-label="has_mine">${tt('minorfiles.has_a_mine_2')}</label>
      <div data-label="has_mine"><label class="chk"><input type="checkbox"
        ${w.has_mine?'checked':''} onchange="mfSet('has_mine',this.checked)">
        ${tt('minorfiles.shows_the_mine_model_named_at')}</label></div>
    </div>
  </section>${state.mf.adding ? mfResourceStartHtml(d) : ''}`;
}

/* ---- what a new resource brings (89b) ----
   Only offered on a mod marked as running on M2EX, whose resource list is
   open. Its name and tooltip are keys M2EX derives from it, each added after
   every other key in its file; its icon is copied from a resource that has one,
   until one is drawn - the way a new religion's pip is. */
function mfResourceStartHtml(d){
  const w = d.w, name = (w.name||'').trim() || 'name';
  const res = (state.mf.records || []).map(r => r.name);
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.what_the_new_resource_brings')}</div>
    <div class="trgrid">
      <label class="lbl mfstartlbl">${tt('minorfiles.icon_from')}</label>
      <div><select onchange="mfSet('icon_from', this.value)">
        <option value="">${tt('minorfiles.no_copy_use_the_icon_path',{name:esc(name)})}</option>
        ${res.map(r => `<option value="${esc(r)}" ${w.icon_from === r ? 'selected' : ''}>${tt('minorfiles.copy_s_icon',{x:esc(r)})}</option>`).join('')}
      </select></div>
      <label class="lbl mfstartlbl">${tt('minorfiles.tooltip')}</label>
      <div><input value="${esc(w.tooltip||'')}" placeholder="${ttA('minorfiles.left_empty_it_is_the_name')}"
        oninput="mfSet('tooltip', this.value)">
        <div class="trhint count">${tt('minorfiles.the_name_and_the_tooltip_are',{tag:esc(mfResourceTag(w.name)),tip:esc('TMT_' + name.toUpperCase() + '_TOOLTIP')})}</div>
      </div>
    </div>
  </section>`;
}

function mfReligionForm(d){
  const w = d.w;
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.the_religion_a_religion_is_written')}</div>
    <div class="trgrid">
      ${mfNameRow(d, 'catholic')}
      <label class="lbl" data-label="pip_path">${tt('minorfiles.pip')}</label>
      <div>
        <div class="mfart">
          ${mfArt(w.pip_path)}
          <input data-label="pip_path" value="${esc(w.pip_path)}"
            placeholder="ui/pips/pip_catholic.tga"
            oninput="mfSet('pip_path',this.value.trim())">
        </div>
        <div class="trhint count">${tt('minorfiles.what_the_campaign_map_draws_for')}</div>
      </div>
    </div>
    ${d.listed === false ? `<div class="trfind w-bad">${tt('minorfiles.this_religion_has_a_block_but')}</div>` : ''}
  </section>${state.mf.adding ? mfReligionStartHtml(d) : ''}`;
}

/* ---- where a new religion starts (60) ----
   geeko's *How to add a religion* has five steps; the list, the block, the
   lookup and the name were already one save. This is steps 2 and 4: the pip
   (copied from a religion that has one, until you draw your own) and every
   region's religions line. Every line gets `name 0`; a region given a share
   takes it from its other religions in proportion, so it still adds up to 100 -
   the server does the arithmetic and refuses a region that did not add up to
   100 to begin with. */
function mfReligionStartHtml(d){
  const w = d.w, v = d.vocab || {};
  const rels = (state.mf.records || []).map(r => r.name);
  const regions = v.regions || [];
  const seeds = w.seeds || (w.seeds = []);
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.where_it_starts_every_regions_religions',{name:esc((w.name||'').trim() || 'name')})}</div>
    <div class="trgrid">
      <label class="lbl mfstartlbl">${tt('minorfiles.pip_from')}</label>
      <div><select onchange="mfSet('pip_from', this.value)">
        <option value="">${tt('minorfiles.no_copy_draw_ui_pips_pip',{name:esc((w.name||'').trim() || 'name')})}</option>
        ${rels.map(r => `<option value="${esc(r)}" ${w.pip_from === r ? 'selected' : ''}>${tt('minorfiles.copy_s_pip',{x:esc(r)})}</option>`).join('')}
      </select></div>
      <label class="lbl mfstartlbl">${tt('minorfiles.starting_in')}</label>
      <div>
        ${seeds.map((row, i) => `<div class="mfseed">
          <input list="mfRegions" value="${esc(row.region || '')}" placeholder="${ttA('minorfiles.a_region_2')}"
            onchange="mfSeed(${i}, 'region', this.value)">
          <input type="number" min="1" max="100" value="${esc(row.share || '')}" style="width:64px"
            onchange="mfSeed(${i}, 'share', this.value)"> %
          <button onclick="mfSeed(${i}, 'drop')">✕</button></div>`).join('')}
        <button onclick="mfSeed(-1, 'add')">${tt('minorfiles.a_region')}</button>
        <datalist id="mfRegions">${regions.map(r => `<option value="${esc(r)}">`).join('')}</datalist>
        <div class="trhint count">${tt('minorfiles.left_empty_it_starts_nowhere_0')}</div>
      </div>
    </div>
  </section>`;
}

function mfSeed(i, what, value){
  const w = state.mf.d.w, seeds = w.seeds || (w.seeds = []);
  if(what === 'add') seeds.push({region: '', share: 10});
  else if(what === 'drop') seeds.splice(i, 1);
  else seeds[i][what] = what === 'share' ? (+value || '') : value.trim();
  renderMinor();
}

/* ---- the culture form, on four tabs (Phase 46) ----
   General, Settlements, Infrastructure, Agents: the strip every other record
   form here has. Infrastructure is the tab the phase was for - the fort, the
   fishing village, the watchtower and the PORT LADDER, which used to be pushed
   into the code view because a port level is a pair of lines. The ladder's
   shape (how many levels) is still the file's; what each line points at is a
   box. The chosen tab is remembered across records. */
const MF_CUL_TABS = [['general',tt('common.general')], ['settlements',tt('minorfiles.settlements')],
                     ['infra',tt('minorfiles.infrastructure')], ['agents',tt('minorfiles.agents')]];
function mfCulTab(id){ state.mfCulTab = id; mfPaintForm(); }
function mfCultureForm(d){
  const cur = state.mfCulTab || 'general';
  const strip = recTabsHtml(MF_CUL_TABS, cur, 'mfCulTab');
  const body = cur === 'settlements' ? mfCulSettlements(d)
    : cur === 'infra' ? mfCulInfra(d) : cur === 'agents' ? mfCulAgents(d)
    : mfCulGeneral(d);
  return strip + body;
}
function mfCulBox(w, k, label){
  return w[k] === undefined || w[k] === '' ? '' :
    `<label class="lbl" data-label="${k}">${esc(label||k)}</label>
     <input data-label="${k}" value="${esc(w[k])}" oninput="mfSet('${k}',this.value.trim())">`;
}
function mfCulGeneral(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.the_culture_the_record_does_not')}</div>
    <div class="trgrid">
      ${mfNameRow(d, 'southern_european')}
      ${(v.head||[]).map(k => mfCulBox(w, k)).join('')}
    </div>
  </section>`;
}
const MF_CUL_INFRA_LABEL = {fort:tt('minorfiles.fort_model'), fort_cost:tt('minorfiles.fort_cost'), fort_wall:tt('minorfiles.fort_wall'),
  fishing_village:tt('minorfiles.fishing_village'), watchtower:tt('minorfiles.watchtower_model'), watchtower_cost:tt('minorfiles.watchtower_cost')};
function mfCulInfra(d){
  const w = d.w, v = d.vocab || {};
  const ports = w.ports || [];
  const nth = {};
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.fort_fishing_village_and_watchtower')}</div>
    <div class="trgrid">
      ${(v.tail||[]).map(k => mfCulBox(w, k, MF_CUL_INFRA_LABEL[k])).join('')}
    </div>
    ${typeof smiButton === 'function' ? `<div class="count">${tt('minorfiles.import_a_model_for',{x:['fort', 'fort_wall', 'fishing_village', 'watchtower'].filter(k => w[k])
        .map(k => smiButton(w.name, k).replace('>Import…<', `>${esc(k)}<`)).join(' ')})}</div>
      ${smiHtml(w.name, true)}` : ''}
  </section>
  <section class="trsec">
    <div class="trsechead">${tt('minorfiles.port_ladder_line_s_in_the',{ports_n:ports.length})}</div>
    ${ports.length ? `<div class="trgrid">${ports.map((p, k) => {
      nth[p.key] = (nth[p.key] || 0) + 1;
      const lab = `${p.key}#${nth[p.key]}`;
      return `<label class="lbl" data-label="${esc(lab)}">${esc(p.key)} ${nth[p.key]}</label>
        <input data-label="${esc(lab)}" value="${esc(p.value)}"
          oninput="mfSetPort(${k},this.value.trim())">`;
    }).join('')}</div>`
      : `<div class="count">${tt('minorfiles.this_culture_has_no_port_lines')}</div>`}
  </section>`;
}
function mfCulSettlements(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.settlement_ladder_level_s_each_one',{n:(w.levels||[]).length})}</div>
    ${(w.levels||[]).map((l,k) => `<div class="mflvl" data-label="level.${esc(l.name)}">
      <div class="mflvlname">${esc(l.name)}</div>
      ${mfArt(l.card)}
      <div class="trgrid" style="flex:1">
        <label class="lbl" data-label="level.${esc(l.name)}.normal">${tt('minorfiles.model',{x:typeof smiButton === 'function' ? smiButton(w.name, l.name) : ''})}</label>
        <input value="${esc(l.model)}" oninput="mfSetLevel(${k},'model',this.value.trim())">
        <label class="lbl">${tt('minorfiles.settlement_plan')}</label>
        <input value="${esc(l.plan)}" oninput="mfSetLevel(${k},'plan',this.value.trim())">
        <label class="lbl" data-label="level.${esc(l.name)}.card">${tt('minorfiles.card')}</label>
        <input value="${esc(l.card)}" oninput="mfSetLevel(${k},'card',this.value.trim())">
      </div>
    </div>`).join('')}
    ${typeof smiHtml === 'function' ? smiHtml(w.name, false) : ''}
    ${mfMissingLevels(w, v)}
  </section>`;
}
function mfCulAgents(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.agents_card_info_card_pip_and')}</div>
    ${Object.entries(w.agents||{}).map(([a,g]) => `<div class="treff" data-label="agent.${esc(a)}">
      <span class="mfag">${esc(a)}</span>
      ${mfArt(g.tokens[0])}
      ${[['card',0],['info_card',1],['pip',2],['cost',3]].map(([nm,i]) =>
        `<input class="${nm==='cost'?'trnum':''}" value="${esc(g.tokens[i]||'')}"
          title="${esc(nm)}" placeholder="${esc(nm)}"
          oninput="mfSetAgent('${q1(esc(a))}',${i},this.value.trim())">`).join('')}
    </div>`).join('')}
    ${(v.agents||[]).filter(a => !(w.agents||{})[a]).length
      ? `<div class="trfind w-warn">${tt('minorfiles.no_line_so_this_culture_cannot',{x:(v.agents||[]).filter(a =>
          !(w.agents||{})[a]).map(esc).join(', ')})}</div>`
      : ''}
  </section>`;
}

function mfMissingLevels(w, v){
  const have = new Set((w.levels||[]).map(l => l.name));
  const gone = (v.levels||[]).filter(l => !have.has(l));
  if(!gone.length) return '';
  return `<div class="trhint count" style="margin-top:8px">${tt('minorfiles.not_defined_here_that_is_only',{gone:gone.map(esc).join(', ')})}</div>`;
}

// 800 names is a textarea, not 800 boxes. One name per line, which is exactly
// how the file itself holds them.
function mfNamesForm(d){
  const w = d.w, v = d.vocab || {};
  const has = new Set((w.sections||[]).map(s => s.name));
  return `<section class="trsec">
    <div class="trsechead">${tt('minorfiles.the_factions_names_one_name_per')}</div>
    <div class="trgrid">${mfNameRow(d, 'england')}</div>
    ${(w.sections||[]).map((s,k) => `<div style="margin-top:10px" data-label="${esc(s.name)}">
      <div class="trsechead" style="margin:0 0 4px">${esc(s.name)}
        <span class="count">${s.entries.length} name(s)</span></div>
      <textarea class="mfnames" rows="12"
        oninput="mfSetSection(${k},this.value)">${esc(s.entries.join('\n'))}</textarea>
    </div>`).join('')}
    ${(v.sections||[]).filter(s => !has.has(s)).length
      ? `<div class="trhint count" style="margin-top:8px">${tt('minorfiles.no_section_adding_one_is_a',{x:(v.sections||[]).filter(s => !has.has(s)).map(esc).join(', ')})}</div>` : ''}
  </section>`;
}

/* ---- 41: merging one faction's name pool into another ----

   `check_names` has always been able to say a name is repeated inside a section
   and name both lines, and nothing could act on it; and there was no way to pull
   one faction's surnames into another's short of retyping them. Two buttons and
   one dialog, both behind the same plan/apply preview every other save here uses.

   Three things Mylae's modal does that this deliberately does not:

   * his Merge button is live with no source selected, where the only thing it
     can do is dedupe in place. That is a real action, so it is its own button;
     merging nothing is refused and the refusal names the button that does it.
   * his preview labels a source name "skipped" when dedupe is off, and with
     dedupe off it is appended rather than skipped. The counts here come from the
     server's own merge, so they cannot disagree with the write.
   * his serialiser drops the `settlements` section. Ours carries all four. */
function mfMergeOpen(){
  const f = state.mf, d = f.d;
  if(!d || f.tab !== 'names') return;
  f.merge = {sources: [], dedupe: true, sort: false, sections: [],
             plan: null, busy: false, err: ''};
  mfMergeRender();
  overlay.classList.add('open');
  mfMergePreview();
}

function mfMergeClose(){ if(state.mf) state.mf.merge = null; closeModal(); }

function mfMergeSet(key, value){
  const m = state.mf && state.mf.merge;
  if(!m) return;
  m[key] = value;
  mfMergeRender();
  clearTimeout(state.mf._mgT);
  state.mf._mgT = setTimeout(mfMergePreview, 200);
}

function mfMergeSource(name, on){
  const m = state.mf && state.mf.merge;
  if(!m) return;
  m.sources = on ? [...new Set([...m.sources, name])]
                 : m.sources.filter(s => s !== name);
  mfMergeSet('sources', m.sources);
}

function mfMergeSection(name, on){
  const m = state.mf && state.mf.merge;
  if(!m) return;
  m.sections = on ? m.sections.filter(s => s !== name)
                  : [...new Set([...m.sections, name])];
  mfMergeSet('sections', m.sections);
}

function mfMergeBody(action){
  const f = state.mf, m = f.merge || {};
  const all = mfMergeAllSections();
  const want = all.filter(s => !(m.sections || []).includes(s));
  return {mod: f.mod, tab: 'names', action, name: f.d.name,
          sources: action === 'dedupe' ? [] : (m.sources || []),
          dedupe: action === 'dedupe' ? true : !!m.dedupe,
          sort: !!m.sort,
          // an empty list means every section, so only send one when it narrows
          sections: want.length === all.length ? [] : want};
}

// every section either the target or any offered source has, in file order
function mfMergeAllSections(){
  const f = state.mf;
  const seen = new Set(((f.d && f.d.w && f.d.w.sections) || []).map(s => s.name));
  (f.records || []).forEach(r => Object.keys(r.sections || {})
    .forEach(k => seen.add(k)));
  return (f.vocabSections || ['settlements', 'characters', 'surnames', 'women'])
    .filter(s => seen.has(s));
}

async function mfMergePreview(){
  const f = state.mf, m = f && f.merge;
  if(!m) return;
  if(!(m.sources || []).length){ m.plan = null; m.err = ''; mfMergePaint(); return; }
  m.busy = true; m.err = '';
  let r;
  try{ r = await api.post('/api/minor/plan', mfMergeBody('merge')); }
  catch(e){ r = {error: String((e && e.message) || e)}; }
  finally{ m.busy = false; }
  if(!state.mf || state.mf.merge !== m) return;      // the dialog moved on
  m.plan = r.plan || null;
  m.err = (r.error && !(r.plan && (r.plan.errors || []).length)) ? r.error : '';
  mfMergePaint();
}

function mfMergePaint(){
  const m = state.mf && state.mf.merge;
  if(!m) return;
  const host = document.getElementById('mgPlan');
  if(!host) return mfMergeRender();
  host.innerHTML = mfMergePlanHtml();
  const go = document.querySelector('.foot .primary');
  if(go) go.disabled = !(m.plan && m.plan.ok && !m.busy);
}

/* The three counts, per section, and they come from the server's own merge -
   so "added" is the number of lines the write will really add. A section that
   gained nothing is still drawn, because "did it work" is answered by seeing
   that every name offered was already there, not by seeing no row at all. */
function mfMergePlanHtml(){
  const m = state.mf.merge;
  if(m.err) return `<div class="w-warn fcmsg">${esc(m.err)}</div>`;
  if(!(m.sources || []).length) return `<div class="count fcintro">${tt('minorfiles.tick_a_faction_above_to_see')}</div>`;
  if(!m.plan) return `<div class="count fcintro">${tt('common.working_out_what_would_change')}</div>`;
  if((m.plan.errors || []).length)
    return `<div class="w-warn fcmsg">${m.plan.errors.map(esc).join('<br>')}</div>`;
  const rows = Object.entries(m.plan.merge || {});
  if(!rows.length) return `<div class="count fcintro">${tt('minorfiles.nothing_to_merge')}</div>`;
  return `<div class="fcplan">
    <div class="k">${tt('minorfiles.what_each_section_would_gain')}
      <span class="count">${esc((m.plan.merge_sources || []).join(', '))}</span></div>
    ${rows.map(([sec, c]) => `<div class="fcrow${c.added || c.removed ? '' : ' off'}">
      <span class="fcc">${c.added ? '+' + c.added : '0'}</span>
      ${tt('minorfiles.name_s',{sec:esc(sec),before:c.before,after:c.after,added:c.added ? `${c.added} new` : tt('minorfiles.nothing_new'),present:c.present ? tt('minorfiles.already_there',{present:c.present}) : '',x:c.removed ? tt('minorfiles.repeat_s_of_its_own_removed',{removed:c.removed})
                  : (c.duplicates ? tt('minorfiles.repeat_s_of_its_own_kept',{duplicates:c.duplicates})
                                  : '')})}
    </div>`).join('')}
    ${(m.plan.warnings || []).map(w =>
      `<div class="w-warn fcmsg">${esc(w)}</div>`).join('')}
  </div>`;
}

function mfMergeRender(){
  const f = state.mf, m = f.merge, d = f.d;
  if(!m) return;
  const others = (f.records || []).map(r => r.name).filter(n => n !== d.name);
  const secs = mfMergeAllSections();
  const modal = document.getElementById('modal');
  // Its own class, so it gets its own remembered size rather than opening at
  // whatever the last plain dialog was left at. Two dozen faction checkboxes and
  // a preview table do not fit the 640px a confirm box wants, and `closeModal`
  // puts the bare class back for whatever opens next.
  modal.className = 'modal mgwide';
  modal.innerHTML = `
    <h2>${tt('minorfiles.merge_names_into',{name:esc(d.name)})} <span class="pill">${esc(f.mod || state.src)}</span></h2>
    <div class="mbody" style="padding:14px 16px">
      <div class="count fcintro">
        ${tt('minorfiles.every_name_the_factions_you_tick',{name:esc(d.name)})}
      </div>
      <div class="trsechead" style="margin-top:12px">${tt('minorfiles.take_names_from_of_selected',{sources_n:m.sources.length,others_n:others.length})}</div>
      <div class="mgsrc">
        ${others.map(n => `<label class="fcart"><input type="checkbox"
          ${m.sources.includes(n) ? 'checked' : ''}
          onchange="mfMergeSource('${esc(n)}', this.checked)">${esc(n)}</label>`).join('')}
      </div>
      <div class="trsechead" style="margin-top:12px">${tt('minorfiles.which_sections')}</div>
      <div class="mgsrc">
        ${secs.map(s => `<label class="fcart"><input type="checkbox"
          ${m.sections.includes(s) ? '' : 'checked'}
          onchange="mfMergeSection('${esc(s)}', this.checked)">${esc(s)}</label>`).join('')}
      </div>
      <div style="margin-top:12px">
        <label class="fcart"><input type="checkbox" ${m.dedupe ? 'checked' : ''}
          onchange="mfMergeSet('dedupe', this.checked)">
          <span>${tt('minorfiles.remove_duplicates_a_name_already_has',{name:esc(d.name)})}</span></label>
        <label class="fcart"><input type="checkbox" ${m.sort ? 'checked' : ''}
          onchange="mfMergeSet('sort', this.checked)">
          <span>${tt('minorfiles.sort_alphabetically_reorders_the_whole_of')}</span></label>
      </div>
      <div id="mgPlan">${mfMergePlanHtml()}</div>
    </div>
    <div class="foot">
      <button onclick="mfMergeClose()">${tt('common.cancel')}</button>
      <span class="sp"></span>
      <button class="primary" ${m.plan && m.plan.ok && !m.busy ? '' : 'disabled'}
        onclick="mfMergeApply()">${tt('minorfiles.merge')}</button>
    </div>`;
}

async function mfMergeApply(){
  const f = state.mf, m = f && f.merge;
  if(!m || !m.plan || !m.plan.ok || m.busy) return;
  const rows = Object.entries(m.plan.merge || {})
    .filter(([, c]) => c.added || c.removed);
  if(!confirm(tt('minorfiles.merge_into_confirm',{sources:(m.plan.merge_sources || []).join(', '),name:f.d.name,
    changes:rows.map(([s, c]) => `  ${s}: ${c.before} → ${c.after}`).join('\n')
       || tt('common.no_visible_change')}))) return;
  m.busy = true;
  let res;
  try{ res = await api.post('/api/minor/apply', mfMergeBody('merge')); }
  finally{ m.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  const keep = f.d.name;
  f.merge = null;
  closeModal();
  toast(tt('minorfiles.merged_log_can_undo_it'));
  await loadMinor();
  mfOpen(keep);
}

/* Dedupe in place, with no dialog: it has no options to set, and the confirm
   `mfApply` already draws lists every section it would change. */
async function mfDedupe(){
  const d = state.mf && state.mf.d;
  if(!d) return;
  await mfApply({mod: state.mf.mod, tab: 'names', action: 'dedupe', name: d.name},
                tt('minorfiles.remove_s_repeated_names',{name:d.name}));
}


/* ---- edits ----
   Every one of these ends at `mfTouched`, which is the GUI→pane half of the
   Code View contract: change a box and the text pane is re-serialised by the
   server, through the same serialiser the save will use. */
function mfTouched(repaint){
  const d = state.mf.d; if(!d) return;
  if(repaint) mfPaintForm();
  if(d.cv) cvFromGui(d.cv);
}
function mfSet(key, value){
  const d = state.mf.d; if(!d) return;
  d.w[key] = value;
  // these change the shape of the form rather than one box's contents. `name`
  // is NOT one of them: it only feeds a placeholder, and repainting the form
  // under the caret on every keystroke is what the unit rows below were doing
  // wrong.
  mfTouched(key === 'has_mine');
}
/* The shown name is stored under one slot, `#name`, and the KEY it goes to is
   worked out at save time by `mfLocTag`. A rebel faction is keyed by its
   `description` value, which is a box on the same form - bake the key into the
   handler and retyping the description quietly sends the words to the old key. */
function mfSetLocName(value){
  const d = state.mf.d; if(!d) return;
  (d.locEdits = d.locEdits || {})['#name'] = value;
}
function mfLocTag(){
  const f = state.mf, d = f.d, w = (d && d.w) || {};
  if(f.tab === 'rebels') return (w.description || '').trim() || (w.name || '').trim();
  if(f.tab === 'religions') return (w.name || '').trim();
  if(f.tab === 'resources' && f.adding) return mfResourceTag(w.name);
  return d ? (d.loc_tag || '') : '';        // resources: read by position, not by tag
}
function mfLocBody(){
  const d = state.mf.d, e = (d && d.locEdits) || {};
  if(e['#name'] === undefined) return {};
  const tag = mfLocTag();
  return tag ? {[tag]: e['#name']} : {};
}
/* A rebel `unit` line is a unit TYPE and the whole rest of the line is the name,
   spaces and all - `Mordor Orcs Invasion`. So this box could not be trimmed as
   it was typed into and repainted from the trimmed value: every space the user
   pressed was cut back off and written over the box before the next keystroke,
   which is the space bar "not working" in the picker. Trimming belongs at save
   time (`mfEdits`), and the only thing that has to follow a keystroke here is
   the name shown beside the box. */
function mfSetUnit(k, value){
  const d = state.mf.d; if(!d) return;
  d.w.units[k] = value;
  const label = document.getElementById('mfu' + k);
  if(label) label.textContent = mfUnitLabel(d, value.trim());
  mfTouched(false);
}
function mfAddUnit(){
  const w = state.mf.d.w;
  (w.units = w.units || []).push('');
  mfTouched(true);
}
function mfDelUnit(k){
  state.mf.d.w.units.splice(k, 1);
  mfTouched(true);
}
function mfSetLevel(k, key, value){
  const l = state.mf.d.w.levels[k]; if(!l) return;
  l[key] = value;
  mfTouched(false);
}
function mfSetPort(k, value){
  const p = (state.mf.d.w.ports||[])[k]; if(!p) return;
  p.value = value;
  mfTouched(false);
}
function mfSetAgent(name, i, value){
  const g = (state.mf.d.w.agents||{})[name]; if(!g) return;
  g.tokens[i] = value;
  mfTouched(false);
}
function mfSetSection(k, text){
  const s = state.mf.d.w.sections[k]; if(!s) return;
  s.entries = text.split('\n').map(v => v.trim()).filter(Boolean);
  mfTouched(false);
}

/* ---- the code view ---- */
async function mfCvToggle(){
  const f = state.mf, d = f.d; if(!d) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); mfPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate({kind:f.tab, mod:f.mod, id:d.name, where:'data/' + f.file,
    edits:() => mfEdits(),
    adopt:cv => { const s = state.mf.d;
      if(!cv.detail) return;
      s.w = cv.detail;
      // `base`, never `text`: with comment hiding on, `text` is the view with the
      // comment-only lines cut out of it, and saving that would delete every one
      // of them. `base` is the record's real bytes.
      s.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => mfPaintForm()});
  mfPaint();
  await cvLoad(d.cv);
  if(state.mf.d !== d || !d.cv) return;
  mfPaint();
}

/* ---- writing ----
   `edits` is exactly what the server's render_any() for this tab takes, so the
   pane and the save cannot produce different bytes. */
function mfEdits(){
  const f = state.mf, w = f.d.w;
  if(f.tab === 'rebels') return {name:(w.name||'').trim(), category:w.category,
    chance:w.chance, description:w.description,
    units:(w.units||[]).map(u => (u||'').trim()).filter(Boolean)};
  if(f.tab === 'resources') return {name:(w.name||'').trim(), trade_value:w.trade_value,
    item:w.item, icon:w.icon, has_mine:!!w.has_mine};
  if(f.tab === 'religions') return {name:(w.name||'').trim(), pip_path:w.pip_path};
  if(f.tab === 'names') return {name:(w.name||'').trim(),
    sections:Object.fromEntries((w.sections||[]).map(s => [s.name, s.entries]))};
  // cultures: only the keys this culture actually HAS a line for - the server
  // refuses to invent one, because where it would go is the file's own order
  const out = {name:(w.name||'').trim(), levels:{}, agents:{}};
  const v = f.d.vocab || {};
  for(const k of (v.head||[]).concat(v.tail||[]))
    if(w[k]) out[k] = w[k];
  for(const l of (w.levels||[]))
    out.levels[l.name] = {model:l.model, plan:l.plan, card:l.card};
  for(const [a,g] of Object.entries(w.agents||{}))
    out.agents[a] = {card:g.tokens[0], info_card:g.tokens[1], pip:g.tokens[2],
      cost:g.tokens[3]};
  out.ports = (w.ports||[]).map(p => (p.value||'').trim());
  return out;
}

/* ---- duplicate a culture (Phase 46) ----
   A culture cannot be written from nothing, but it can be copied from one that
   works. The server writes the whole record under the new name and NAMES what a
   culture needs outside this file, from the mod's own files: its text keys in
   text/expanded.txt, the factions that could move onto it, and the art it still
   borrows. Named, not written - those are other screens' saves. */
async function mfDuplicate(){
  const f = state.mf, d = f.d;
  if(!d) return;
  const name = (prompt(tt('minorfiles.a_name_for_the_copy_of',{name:d.name}),
                       d.name + '_2') || '').trim();
  if(!name) return;
  const body = {mod: f.mod, tab: 'cultures', action: 'duplicate', name, source: d.name};
  let r;
  try{ r = await api.post('/api/minor/plan', body); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  const p = r.plan || {};
  const needs = (p.needs || []).map(n => `  • ${n.what}: ${n.detail}`).join('\n');
  if(!confirm(tt('minorfiles.write_needs_confirm',{changes:(p.changes||[]).join('; '),name,needs}))) return;
  let res;
  try{ res = await api.post('/api/minor/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('minorfiles.written_the_list_of_what_it',{name}), 5000);
  await loadMinor();
  mfOpen(name);
}

function mfBody(action){
  const f = state.mf, d = f.d;
  const body = {mod:f.mod, tab:f.tab, action,
    name:action === 'add' ? (d.w.name||'').trim() : d.name};
  if(action !== 'delete'){
    body.edits = mfEdits();
    body.loc = mfLocBody();
    if(d.raw) body.raw_block = d.raw;
  }
  if(f.tab === 'religions' && action === 'add'){
    body.pip_from = d.w.pip_from || '';
    body.seeds = (d.w.seeds || []).filter(r => r.region && r.share);
  }
  if(f.tab === 'resources' && action === 'add'){
    body.icon_from = d.w.icon_from || '';
    body.tooltip = (d.w.tooltip || '').trim();
  }
  return body;
}

async function mfSave(){
  const f = state.mf, d = f.d;
  if(f.adding && !(d.w.name||'').trim()){
    toast(tt('minorfiles.a_new_needs_a_name',{noun:f.noun}), 3500); return; }
  await mfApply(mfBody(f.adding ? 'add' : 'edit'),
                f.adding ? `create ${d.w.name}` : `save ${d.name}`);
}
async function mfDelete(){
  await mfApply(mfBody('delete'), `delete ${state.mf.d.name}`);
}

async function mfApply(body, what){
  const f = state.mf;
  if(f.busy) return;
  f.busy = true;
  let plan;
  try{ plan = await api.post('/api/minor/plan', body); }
  finally{ f.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 6000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const found = (p.findings || []).map(x => '⚠ ' + x.message);
  const also = (p.files || []).length
    ? tt('minorfiles.also_rewritten',{files:p.files.join(', ')}) : '';
  if(!confirm(tt('minorfiles.write_confirm',{what,details:(lines.join('\n') || tt('common.no_visible_change'))
    + ((p.changes || []).length > 14 ? tt('minorfiles.and_more',{changes:p.changes.length - 14}) : '')
    + also
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')}))) return;
  f.busy = true;
  let res;
  try{ res = await api.post('/api/minor/apply', body); }
  finally{ f.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  const keep = body.action === 'delete' ? '' : body.name;
  await loadMinor();
  if(keep) mfOpen(keep);
}
