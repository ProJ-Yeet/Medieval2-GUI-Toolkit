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
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s campaign files…</div>';
  let r;
  try{ r = await api.get(`/api/minor?mod=${enc(mod)}&tab=${enc(tab)}`); }
  catch(e){ if(stale(mode, mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read the campaign files.<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadMinor()">Retry</button></div>`; return; }
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
        ? `<button class="trnew" onclick="mfNew()">＋ New ${esc(f.noun)}</button>` : ''}
      ${findingsHtml('minor:'+f.tab, f.finding_list, 'mfOpen')}
      <div class="trrows">${rows.map(mfRowHtml).join('')
        || `<div class="count" style="padding:8px">No ${esc(f.noun)} matches.</div>`}</div>
    </div>
    <div class="trmain" id="mfMain">${mfDetailHtml()}</div>
  </div>` : `<div class="empty">${esc(f.error || 'This mod has not got that file.')}<br>
      <span class="count">It would live in data/${esc(f.file)}</span></div>`);
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
  if(f.tab === 'rebels') sub = `${esc(r.category||'no category')} · chance ${
    esc(r.chance||'0')} · ${r.units} unit${r.units===1?'':'s'}`;
  else if(f.tab === 'resources') sub = `trade ${esc(r.trade_value||'0')}${
    r.has_mine?' · has a mine':''}${r.known?'':' · <b>not an engine resource</b>'}`;
  else if(f.tab === 'religions') sub = r.listed
    ? esc(r.pip_path||'no pip') : '<b>not in the religions list</b>';
  else if(f.tab === 'cultures') sub = `${r.levels} settlement level${
    r.levels===1?'':'s'} · ${r.agents}/6 agents`;
  else sub = Object.entries(r.sections||{}).map(([k,n]) => `${n} ${k}`).join(' · ')
    || '<b>no names at all</b>';
  return `<button class="trrow${on?' on':''}" onclick="mfOpen('${q1(esc(r.name))}')">
    <span class="nm">${esc(r.label)}</span><br>
    <span class="sub">${sub}${r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</span>
  </button>`;
}

async function mfOpen(name){
  activity('opened record', `${name} (${state.mf.tab}) in ${state.src}`);
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
  f.d = {name:'', label:`(new ${f.noun})`, tab:f.tab, file:f.file, noun:f.noun,
    record:blank, w:JSON.parse(JSON.stringify(blank)), findings:[], loc:{},
    locEdits:{}, missing_loc:[], loc_tag:'', loc_writable:true,
    known:(f.records||[]).map(r=>r.name), actions:f.actions,
    vocab:(f.d && f.d.vocab) || {}};
  renderMinor();
  mfLoadVocab();
}

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
  const tag = (f.tab === 'rebels' || f.tab === 'religions') ? name : '';
  const shown = was ? ((d.locEdits||{})['#name'] !== undefined ? d.locEdits['#name']
                       : ((d.loc||{})[was] || '')) : '';
  f.sel = ''; f.adding = true;
  f.d = {name:'', label:`copy of ${d.label}`, tab:f.tab, file:f.file, noun:f.noun,
    record:JSON.parse(JSON.stringify(w)), w,
    findings:[], loc:{}, locEdits:(tag && shown) ? {'#name':shown} : {},
    missing_loc:tag ? [tag] : [], loc_tag:tag, loc_file:d.loc_file || '',
    loc_writable:d.loc_writable !== false, loc_note:d.loc_note || '',
    known:[...known], actions:f.actions, vocab:d.vocab || {}};
  renderMinor();
  const carried = f.tab === 'rebels'
    ? `${(w.units||[]).length} unit(s) and every field came with it`
    : 'every field came with it';
  toast(`Copied ${d.name} as “${name}” - ${carried}. `
    + 'Nothing is written until you press Create.', 6500);
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
  if(!f.sel && !f.adding) return `<div class="empty">Pick a ${esc(f.noun)} on the left.<br>
    <span class="count">${f.count} ${esc(f.noun)}${f.count===1?'':'s'} in data/${
      esc(f.file)}</span>${f.refused ? `<div class="trnote"
      style="max-width:560px;margin:14px auto;text-align:left">${esc(f.refused)}</div>`
      : ''}</div>`;
  if(!d) return `<div class="empty">Reading the ${esc(f.noun)}…</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(f.adding ? 'New ' + f.noun : d.label)}</b>
        <span class="count">${esc(f.file)}</span></div>
      <span class="sp"></span>
      ${f.adding ? '' : `<button class="${d.cv?'on':''}" title="Show this ${esc(f.noun)}
exactly as ${esc(f.file)} stores it, beside the form."
        onclick="mfCvToggle()">&lt;/&gt; Code view</button>
      ${(d.actions||[]).includes('add')
        ? `<button onclick="mfClone()" title="Start a new ${esc(f.noun)} holding
everything this one holds, under a new name. Nothing is written until you press
Create.">⧉ Clone</button>` : ''}
      ${(d.actions||[]).includes('duplicate')
        ? `<button onclick="mfDuplicate()" title="A new culture: this one's whole record
under a new name. The preview names the text keys, factions and art it still needs.">⧉ Duplicate…</button>` : ''}
      ${(d.actions||[]).includes('merge')
        ? `<button onclick="mfMergeOpen()" title="Add every name another faction
keeps to this one's lists. The other faction is read, not changed.">⧉ Merge names…</button>
      <button onclick="mfDedupe()" title="Clear the names this faction lists twice.
Nothing is added.">Remove duplicates</button>` : ''}
      ${(d.actions||[]).includes('delete')
        ? '<button class="danger" onclick="mfDelete()">Delete</button>' : ''}`}
      <button class="primary" onclick="mfSave()">${f.adding?'Create':'Save'}</button>
    </div>
    <div id="mfGui">
      ${mfFindingsHtml(d)}
      ${mfFormHtml(d)}
    </div>
    ${d.cv ? `<div id="mfCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}`;
}

function mfFindingsHtml(d){
  const out = (d.findings||[]).map(f =>
    `<div class="trfind w-warn">line ${f.line}: ${esc(f.message)}</div>`);
  if((d.missing_loc||[]).length && d.loc_writable) out.push(`<div class="trfind w-warn">
    There is no <code>{${esc(d.loc_tag)}}</code> entry in ${esc(d.loc_file)}, so this
    ${esc(d.noun)} shows its code name in game. Type the words beside the name below,
    or save and the key is created with the code name as placeholder text.</div>`);
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
  if(!r)return '<span class="mfnoart" title="No path set">none</span>';
  // These sit in dense tables with no room for a pair of buttons, so the pip
  // itself is the ✎ - a click replaces it, and a right-click gets the same menu
  // (with "Open file location" on it) that every other picture in the tool has.
  const url=`/icon?mod=${enc(state.mf.mod)}&kind=modfile&rel=${enc(r)}${iconBust()}`;
  return `<img class="mfpip act" loading="lazy" src="${url}"
    alt="" title="${esc(r)}. Blank here means the file is not unpacked in this mod, which is normal: it may be inside a .pack archive.
Click to replace it; right-click for its file location."
    onclick="imgPick('${q1(esc(url))}','mfPaint')"
    onerror="this.classList.add('gone')">`;
}
function mfNameRow(d, placeholder){
  const w = d.w, tag = d.loc_tag || '';
  const shown = tag ? (d.locEdits['#name'] !== undefined ? d.locEdits['#name']
                       : ((d.loc||{})[tag] || '')) : '';
  return `<label class="lbl" data-label="name">Name</label>
    <div class="${tag?'trkey':''}">
      <input data-label="name" value="${esc(w.name)}"
        ${state.mf.adding?'':'disabled'} placeholder="${esc(placeholder||'')}"
        oninput="mfSet('name',this.value.trim())">
      ${tag ? `<input class="trtext" value="${esc(shown)}"
        ${d.loc_writable?'':'disabled'}
        placeholder="${esc(d.loc_writable
          ? (((d.loc||{})[tag] === undefined) ? 'not in ' + d.loc_file + ' yet'
             : 'what the player reads')
          : (shown || 'read by position, so edit it in the Strings module'))}"
        title="${esc(d.loc_writable ? 'What the player reads. Saved into data/'
          + d.loc_file + '.' : d.loc_note || '')}"
        oninput="mfSetLocName(this.value)">` : ''}
    </div>
    ${tag && !d.loc_writable ? `<span></span><div class="trhint count">${
      esc(d.loc_note||'')}</div>` : ''}`;
}

function mfRebelForm(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">The rebel faction
      <span class="count">What spawns in a region whose descr_regions line names it</span></div>
    <div class="trgrid">
      ${mfNameRow(d, 'Evil_Rebels')}
      <label class="lbl" data-label="category">Category</label>
      <div>
        <select data-label="category" onchange="mfSet('category',this.value)">
          ${(v.categories||[]).map(c =>
            `<option value="${esc(c)}"${c===w.category?' selected':''}>${esc(c)}</option>`).join('')}
          ${(v.categories||[]).includes(w.category) ? ''
            : `<option value="${esc(w.category)}" selected>${esc(w.category)} (unknown)</option>`}
        </select>
        <div class="trhint count">The four the engine knows. Anything else is
          read and ignored</div>
      </div>
      <label class="lbl" data-label="chance">Chance</label>
      <input data-label="chance" value="${esc(w.chance)}"
        oninput="mfSet('chance',this.value.trim())">
      <label class="lbl" data-label="description">Description key</label>
      <input data-label="description" value="${esc(w.description)}"
        placeholder="${esc(w.name||'')}"
        oninput="mfSet('description',this.value.trim())">
    </div>
    <div class="treffects">
      <div class="trsechead" style="margin:8px 0 0">Units
        <span class="count">${(w.units||[]).length}. A rebel faction with none
          cannot spawn. The whole rest of the line is the unit type, spaces and
          all.</span></div>
      ${(w.units||[]).map((u,k)=>`<div class="treff" data-label="unit#${k+1}">
        <input class="trattr" value="${esc(u)}" list="mfUnits"
          placeholder="unit type" oninput="mfSetUnit(${k},this.value)">
        <span class="count" id="mfu${k}">${esc(mfUnitLabel(d, u))}</span>
        <button class="trgdel" onclick="mfDelUnit(${k})">✕</button>
      </div>`).join('')}
      <datalist id="mfUnits">${(v.units||[]).map(u =>
        `<option value="${esc(u.type)}">${esc(u.label)}</option>`).join('')}</datalist>
      <button class="trgadd" onclick="mfAddUnit()">＋ Add unit</button>
    </div>
  </section>`;
}

// The picker offers this mod's units under their in-game names; the line itself
// holds the EDU type, so the name is shown beside the box rather than in it.
function mfUnitLabel(d, type){
  if(!type) return '';
  const hit = ((d.vocab||{}).units||[]).find(u => u.type === type);
  return hit ? hit.label : '✗ not a unit in this mod';
}

function mfResourceForm(d){
  const w = d.w;
  return `<section class="trsec">
    <div class="trsechead">The resource
      <span class="count">Placed on the campaign map by descr_regions.txt</span></div>
    <div class="trgrid">
      ${mfNameRow(d, 'timber')}
      <label class="lbl" data-label="trade_value">Trade value</label>
      <input data-label="trade_value" value="${esc(w.trade_value)}"
        oninput="mfSet('trade_value',this.value.trim())">
      <label class="lbl" data-label="item">Model (item)</label>
      <input data-label="item" value="${esc(w.item)}"
        placeholder="data/models_strat/resource_x.CAS"
        oninput="mfSet('item',this.value.trim())">
      <label class="lbl" data-label="icon">Icon</label>
      <div class="mfart">
        ${mfArt(w.icon)}
        <input data-label="icon" value="${esc(w.icon)}"
          placeholder="data/ui/resources/resource_x.tga"
          oninput="mfSet('icon',this.value.trim())">
      </div>
      <label class="lbl" data-label="has_mine">Has a mine</label>
      <div data-label="has_mine"><label class="chk"><input type="checkbox"
        ${w.has_mine?'checked':''} onchange="mfSet('has_mine',this.checked)">
        shows the mine model named at the top of this file</label></div>
    </div>
  </section>`;
}

function mfReligionForm(d){
  const w = d.w;
  return `<section class="trsec">
    <div class="trsechead">The religion
      <span class="count">A religion is written down three times: this file's
        list, this block, and descr_religions_lookup.txt. A save keeps all
        three in step.</span></div>
    <div class="trgrid">
      ${mfNameRow(d, 'catholic')}
      <label class="lbl" data-label="pip_path">Pip</label>
      <div>
        <div class="mfart">
          ${mfArt(w.pip_path)}
          <input data-label="pip_path" value="${esc(w.pip_path)}"
            placeholder="ui/pips/pip_catholic.tga"
            oninput="mfSet('pip_path',this.value.trim())">
        </div>
        <div class="trhint count">What the campaign map draws for it. The one
          line a religion block has</div>
      </div>
    </div>
    ${d.listed === false ? `<div class="trfind w-bad">This religion has a block but
      is not in the <code>religions { … }</code> list, and the engine reads the
      list, so as far as the game is concerned it does not exist.</div>` : ''}
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
    <div class="trsechead">Where it starts
      <span class="count">Every region's <code>religions { … }</code> line gets
        <code>${esc((w.name||'').trim() || 'name')} 0</code>, in every descr_regions.txt
        this mod ships. A share given here comes out of the region's other
        religions in proportion, so each line still adds up to 100.</span></div>
    <div class="trgrid">
      <label class="lbl mfstartlbl">Pip from</label>
      <div><select onchange="mfSet('pip_from', this.value)">
        <option value="">no copy - draw ui/pips/pip_${esc((w.name||'').trim() || 'name')}.tga yourself</option>
        ${rels.map(r => `<option value="${esc(r)}" ${w.pip_from === r ? 'selected' : ''}>copy ${esc(r)}'s pip</option>`).join('')}
      </select></div>
      <label class="lbl mfstartlbl">Starting in</label>
      <div>
        ${seeds.map((row, i) => `<div class="mfseed">
          <input list="mfRegions" value="${esc(row.region || '')}" placeholder="a region"
            onchange="mfSeed(${i}, 'region', this.value)">
          <input type="number" min="1" max="100" value="${esc(row.share || '')}" style="width:64px"
            onchange="mfSeed(${i}, 'share', this.value)"> %
          <button onclick="mfSeed(${i}, 'drop')">✕</button></div>`).join('')}
        <button onclick="mfSeed(-1, 'add')">＋ a region</button>
        <datalist id="mfRegions">${regions.map(r => `<option value="${esc(r)}">`).join('')}</datalist>
        <div class="trhint count">Left empty, it starts nowhere: 0 in every region.
          A faction takes it on the Factions screen, and its temples are
          buildings (geeko's steps 3 and 5).</div>
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
const MF_CUL_TABS = [['general','General'], ['settlements','Settlements'],
                     ['infra','Infrastructure'], ['agents','Agents']];
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
    <div class="trsechead">The culture
      <span class="count">The record does not end at its closing brace. The fort,
        the ports, the watchtower and the six agents on the other tabs belong to it too</span></div>
    <div class="trgrid">
      ${mfNameRow(d, 'southern_european')}
      ${(v.head||[]).map(k => mfCulBox(w, k)).join('')}
    </div>
  </section>`;
}
const MF_CUL_INFRA_LABEL = {fort:'Fort model', fort_cost:'Fort cost', fort_wall:'Fort wall',
  fishing_village:'Fishing village', watchtower:'Watchtower model', watchtower_cost:'Watchtower cost'};
function mfCulInfra(d){
  const w = d.w, v = d.vocab || {};
  const ports = w.ports || [];
  const nth = {};
  return `<section class="trsec">
    <div class="trsechead">Fort, fishing village and watchtower</div>
    <div class="trgrid">
      ${(v.tail||[]).map(k => mfCulBox(w, k, MF_CUL_INFRA_LABEL[k])).join('')}
    </div>
    ${typeof smiButton === 'function' ? `<div class="count">Import a model for:
      ${['fort', 'fort_wall', 'fishing_village', 'watchtower'].filter(k => w[k])
        .map(k => smiButton(w.name, k).replace('>Import…<', `>${esc(k)}<`)).join(' ')}</div>
      ${smiHtml(w.name, true)}` : ''}
  </section>
  <section class="trsec">
    <div class="trsechead">Port ladder
      <span class="count">${ports.length} line(s), in the file's own order: each port
        level is a <code>port_land</code> and a <code>port_sea</code> model. Adding or
        removing a level is a pair of lines placed in that order, so it is done in the
        code view; what each line points at is here.</span></div>
    ${ports.length ? `<div class="trgrid">${ports.map((p, k) => {
      nth[p.key] = (nth[p.key] || 0) + 1;
      const lab = `${p.key}#${nth[p.key]}`;
      return `<label class="lbl" data-label="${esc(lab)}">${esc(p.key)} ${nth[p.key]}</label>
        <input data-label="${esc(lab)}" value="${esc(p.value)}"
          oninput="mfSetPort(${k},this.value.trim())">`;
    }).join('')}</div>`
      : '<div class="count">This culture has no port lines.</div>'}
  </section>`;
}
function mfCulSettlements(d){
  const w = d.w, v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">Settlement ladder
      <span class="count">${(w.levels||[]).length} level(s), each one a strat
        model, the settlement plan that goes with it, and the card</span></div>
    ${(w.levels||[]).map((l,k) => `<div class="mflvl" data-label="level.${esc(l.name)}">
      <div class="mflvlname">${esc(l.name)}</div>
      ${mfArt(l.card)}
      <div class="trgrid" style="flex:1">
        <label class="lbl" data-label="level.${esc(l.name)}.normal">Model
          ${typeof smiButton === 'function' ? smiButton(w.name, l.name) : ''}</label>
        <input value="${esc(l.model)}" oninput="mfSetLevel(${k},'model',this.value.trim())">
        <label class="lbl">Settlement plan</label>
        <input value="${esc(l.plan)}" oninput="mfSetLevel(${k},'plan',this.value.trim())">
        <label class="lbl" data-label="level.${esc(l.name)}.card">Card</label>
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
    <div class="trsechead">Agents
      <span class="count">Card, info card, pip and cost. The two numbers after
        them are the same <code>1 1</code> in all 234 real agent lines, so they
        are carried by position and never rewritten.</span></div>
    ${Object.entries(w.agents||{}).map(([a,g]) => `<div class="treff" data-label="agent.${esc(a)}">
      <span class="mfag">${esc(a)}</span>
      ${mfArt(g.tokens[0])}
      ${[['card',0],['info_card',1],['pip',2],['cost',3]].map(([nm,i]) =>
        `<input class="${nm==='cost'?'trnum':''}" value="${esc(g.tokens[i]||'')}"
          title="${esc(nm)}" placeholder="${esc(nm)}"
          oninput="mfSetAgent('${q1(esc(a))}',${i},this.value.trim())">`).join('')}
    </div>`).join('')}
    ${(v.agents||[]).filter(a => !(w.agents||{})[a]).length
      ? `<div class="trfind w-warn">No ${(v.agents||[]).filter(a =>
          !(w.agents||{})[a]).map(esc).join(', ')} line, so this culture cannot
          recruit one. Adding an agent line means saying where it goes, which
          this file's own order decides, so it is written in the code view.</div>`
      : ''}
  </section>`;
}

function mfMissingLevels(w, v){
  const have = new Set((w.levels||[]).map(l => l.name));
  const gone = (v.levels||[]).filter(l => !have.has(l));
  if(!gone.length) return '';
  return `<div class="trhint count" style="margin-top:8px">Not defined here:
    ${gone.map(esc).join(', ')}. That is only a fault when the OTHER cultures in
    this file define it. A mod that drops a level everywhere has removed it.</div>`;
}

// 800 names is a textarea, not 800 boxes. One name per line, which is exactly
// how the file itself holds them.
function mfNamesForm(d){
  const w = d.w, v = d.vocab || {};
  const has = new Set((w.sections||[]).map(s => s.name));
  return `<section class="trsec">
    <div class="trsechead">The faction's names
      <span class="count">One name per line, and a name is one word: the engine
        picks from these when it generates a family</span></div>
    <div class="trgrid">${mfNameRow(d, 'england')}</div>
    ${(w.sections||[]).map((s,k) => `<div style="margin-top:10px" data-label="${esc(s.name)}">
      <div class="trsechead" style="margin:0 0 4px">${esc(s.name)}
        <span class="count">${s.entries.length} name(s)</span></div>
      <textarea class="mfnames" rows="12"
        oninput="mfSetSection(${k},this.value)">${esc(s.entries.join('\n'))}</textarea>
    </div>`).join('')}
    ${(v.sections||[]).filter(s => !has.has(s)).length
      ? `<div class="trhint count" style="margin-top:8px">No ${
          (v.sections||[]).filter(s => !has.has(s)).map(esc).join(', ')} section.
          Adding one is a heading and its names together, so it is written in the
          code view.</div>` : ''}
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
  if(!(m.sources || []).length) return `<div class="count fcintro">Tick a faction
    above to see exactly what each section would gain.</div>`;
  if(!m.plan) return `<div class="count fcintro">Working out what would change…</div>`;
  if((m.plan.errors || []).length)
    return `<div class="w-warn fcmsg">${m.plan.errors.map(esc).join('<br>')}</div>`;
  const rows = Object.entries(m.plan.merge || {});
  if(!rows.length) return `<div class="count fcintro">Nothing to merge.</div>`;
  return `<div class="fcplan">
    <div class="k">What each section would gain
      <span class="count">${esc((m.plan.merge_sources || []).join(', '))}</span></div>
    ${rows.map(([sec, c]) => `<div class="fcrow${c.added || c.removed ? '' : ' off'}">
      <span class="fcc">${c.added ? '+' + c.added : '0'}</span>
      <span class="fcn">${esc(sec)}
        <span class="fcf">${c.before} → ${c.after} name(s)</span></span>
      <span class="fcw count">${
        c.added ? `${c.added} new` : 'nothing new'}${
        c.present ? `, ${c.present} already there` : ''}${
        c.removed ? `, ${c.removed} repeat(s) of its own removed`
                  : (c.duplicates ? `, ${c.duplicates} repeat(s) of its own kept`
                                  : '')}</span>
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
    <h2>Merge names into ${esc(d.name)} <span class="pill">${esc(f.mod || state.src)}</span></h2>
    <div class="mbody" style="padding:14px 16px">
      <div class="count fcintro">
        Every name the factions you tick keep, added to <b>${esc(d.name)}</b>'s own
        lists. Nothing is taken from them - they are read, not changed.
      </div>
      <div class="trsechead" style="margin-top:12px">Take names from
        <span class="count">${m.sources.length} of ${others.length} selected</span></div>
      <div class="mgsrc">
        ${others.map(n => `<label class="fcart"><input type="checkbox"
          ${m.sources.includes(n) ? 'checked' : ''}
          onchange="mfMergeSource('${esc(n)}', this.checked)">${esc(n)}</label>`).join('')}
      </div>
      <div class="trsechead" style="margin-top:12px">Which sections</div>
      <div class="mgsrc">
        ${secs.map(s => `<label class="fcart"><input type="checkbox"
          ${m.sections.includes(s) ? '' : 'checked'}
          onchange="mfMergeSection('${esc(s)}', this.checked)">${esc(s)}</label>`).join('')}
      </div>
      <div style="margin-top:12px">
        <label class="fcart"><input type="checkbox" ${m.dedupe ? 'checked' : ''}
          onchange="mfMergeSet('dedupe', this.checked)">
          <span><b>Remove duplicates</b> - a name ${esc(d.name)} already has is not
          added again, and its own repeated lines are cleared out at the same time.
          With this off every name is appended as it comes, repeats and all.</span></label>
        <label class="fcart"><input type="checkbox" ${m.sort ? 'checked' : ''}
          onchange="mfMergeSet('sort', this.checked)">
          <span><b>Sort alphabetically</b> - reorders the whole of each section it
          touches, not just the names arriving.</span></label>
      </div>
      <div id="mgPlan">${mfMergePlanHtml()}</div>
    </div>
    <div class="foot">
      <button onclick="mfMergeClose()">Cancel</button>
      <span class="sp"></span>
      <button class="primary" ${m.plan && m.plan.ok && !m.busy ? '' : 'disabled'}
        onclick="mfMergeApply()">Merge</button>
    </div>`;
}

async function mfMergeApply(){
  const f = state.mf, m = f && f.merge;
  if(!m || !m.plan || !m.plan.ok || m.busy) return;
  const rows = Object.entries(m.plan.merge || {})
    .filter(([, c]) => c.added || c.removed);
  if(!confirm(`Merge ${(m.plan.merge_sources || []).join(', ')} into ${f.d.name}?\n\n`
    + (rows.map(([s, c]) => `  ${s}: ${c.before} → ${c.after}`).join('\n')
       || 'no visible change')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  m.busy = true;
  let res;
  try{ res = await api.post('/api/minor/apply', mfMergeBody('merge')); }
  finally{ m.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  const keep = f.d.name;
  f.merge = null;
  closeModal();
  toast('Merged. 🕑 Log can undo it.');
  await loadMinor();
  mfOpen(keep);
}

/* Dedupe in place, with no dialog: it has no options to set, and the confirm
   `mfApply` already draws lists every section it would change. */
async function mfDedupe(){
  const d = state.mf && state.mf.d;
  if(!d) return;
  await mfApply({mod: state.mf.mod, tab: 'names', action: 'dedupe', name: d.name},
                `remove ${d.name}'s repeated names`);
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
  const name = (prompt(`A name for the copy of ${d.name} (lower case, digits, underscores):`,
                       d.name + '_2') || '').trim();
  if(!name) return;
  const body = {mod: f.mod, tab: 'cultures', action: 'duplicate', name, source: d.name};
  let r;
  try{ r = await api.post('/api/minor/plan', body); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  const p = r.plan || {};
  const needs = (p.needs || []).map(n => `  • ${n.what}: ${n.detail}`).join('\n');
  if(!confirm(`Write: ${(p.changes||[]).join('; ')}?\n\nWhat else ${name} needs, and`
      + ` is NOT written here:\n${needs}\n\nBacked up first, and 🕑 Log can undo it.`)) return;
  let res;
  try{ res = await api.post('/api/minor/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(`${name} written. The list of what it still needs is in the preview you just read.`, 5000);
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
  return body;
}

async function mfSave(){
  const f = state.mf, d = f.d;
  if(f.adding && !(d.w.name||'').trim()){
    toast(`A new ${f.noun} needs a name`, 3500); return; }
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
    ? `\n\nAlso rewritten: ${p.files.join(', ')}` : '';
  if(!confirm(`Write: ${what}?\n\n` + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14 ? `\n…and ${p.changes.length - 14} more` : '')
    + also
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  f.busy = true;
  let res;
  try{ res = await api.post('/api/minor/apply', body); }
  finally{ f.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast('Saved. 🕑 Log can undo it.');
  const keep = body.action === 'delete' ? '' : body.name;
  await loadMinor();
  if(keep) mfOpen(keep);
}
