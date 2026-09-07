/* campevents.js - Campaign Map: the things that happen on their own

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   EVENTS AND DISASTERS - Phase 18b.

   Every name here starts `cev`, and there was no `cev` name anywhere in the
   tree before this phase - checked, the way 16e checked `cp`, 16f `cchk`, 16g
   `cq`, 16h `cs`, 16i `cx`, 16j `cj` and 17d `cmk`.

   IT IS ON THE MAP SCREEN AND NOT IN A MODE OF ITS OWN, and the reason is the
   `position x, y` line. A historical event fires at a coordinate and a disaster
   happens at one, so the question "where" is asked about half the fields on
   this panel - and the answer is the thing filling most of the window beside
   it. `＋ from the picked tile` is what that buys: click the map, then click
   the button, and the coordinate is written in the file's own convention (y up
   from the bottom) without anybody doing the arithmetic.

   TWO FILES, TWO TABS, TWO SAVES. `descr_events.txt` is per campaign and lives
   in the campaign folder; `descr_disasters.txt` is under world/maps/base with
   the layers, because one map has one set of disasters however many campaigns
   are painted on it. They are one panel because nobody thinks of them as two
   jobs, and two saves because they are two files - 18a's ruling, restated once
   more.

   PYTHON OWNS THE RULES. Whether a category is a category, whether a label has
   a title and a body in historic_events.txt, whether an event picture is on
   disk, whether a coordinate is on the grid: every one of those is decided in
   campevents.py and arrives here as a sentence. What is drawn beside a box -
   the mod's own climate list, the eight disaster types - is the server's data
   being shown, not a rule being applied twice.

   WHAT IS NOT HERE. There is no drag. 17d's drag moves a character because a
   character stands on exactly one tile; an event has a LIST of positions - the
   Black Death's third wave has seventeen - so dragging one of them is a gesture
   with no obvious subject. The list is edited as a list.
   ===================================================================== */

//: The two tabs, and which file each one is.
const CEV_TABS = [['events', 'Events'], ['disasters', 'Disasters']];

/* ---------- state ----------

   Beside `state.cmap` like every other campaign-map panel. Neither file is read
   until somebody opens the panel, which is the rule 16j and 16k already follow:
   most visits to this screen are about the pixels. */
function cevNew(mod, campaign){
  return {mod, campaign, open: false, tab: 'events', loading: false, err: '',
          ev: null, dis: null, sel: '', w: null, was: null, adding: false,
          busy: false, preview: null};
}

async function cevOpen(force){
  const c = state.cmap;
  if(!c) return;
  const was = state.cev;
  const camp = (state.cj && state.cj.d && state.cj.d.campaign) || '';
  if(was && was.mod === c.mod && was.ev && !force){ cevPaint(); return; }
  const k = state.cev = cevNew(c.mod, camp);
  k.open = was ? was.open : false;
  k.tab = was ? was.tab : 'events';
  if(!k.open){ cevPaint(); return; }
  await cevLoad();
}

async function cevLoad(){
  const k = state.cev, c = state.cmap;
  if(!k || !c) return;
  k.loading = true; k.err = '';
  cevPaint();
  const q = `mod=${enc(k.mod)}`;
  let ev, dis;
  try{
    ev = await api.get(`/api/campevents/events?${q}`
      + (k.campaign ? `&campaign=${enc(k.campaign)}` : ''));
    dis = await api.get(`/api/campevents/disasters?${q}`);
  }catch(e){
    if(state.cev !== k) return;
    k.loading = false; k.err = errText(e); cevPaint(); return;
  }
  if(state.cev !== k || !state.cmap || state.cmap.mod !== k.mod) return;
  k.loading = false;
  k.ev = ev; k.dis = dis;
  cevReset();
  cevPaint();
}

function cevToggle(){
  const k = state.cev;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.ev) cevLoad(); else cevPaint();
}

function cevTab(name){
  const k = state.cev;
  if(!k) return;
  k.tab = name; k.sel = ''; k.adding = false; k.preview = null;
  cevReset();
  cevPaint();
}

//: The rows of whichever tab is open, and the payload behind them.
function cevData(){
  const k = state.cev;
  return k && (k.tab === 'events' ? k.ev : k.dis);
}

function cevRows(){
  const d = cevData();
  return (d && d.rows) || [];
}

//: What a row is called. An event has a label; a disaster IS its type.
function cevKey(row){
  return (row && (row.name !== undefined ? row.name : row.type)) || '';
}

/* The working copy every box edits, and the copy it is compared against.

   Same shape as 16h, 16i and 16j: whether anything has changed is a comparison
   rather than a flag, so a box typed in and typed back out again leaves the
   Save button gone rather than offering to write nothing. */
function cevReset(){
  const k = state.cev;
  if(!k) return;
  if(k.adding){ k.w = cevBlank(); k.was = null; return; }
  const row = cevRows().find(r => cevKey(r) === k.sel);
  if(!row){ k.w = null; k.was = null; return; }
  k.w = k.tab === 'events'
    ? {category: row.category || 'historic', name: row.name || '',
       dates: (row.dates || []).slice(),
       positions: (row.positions || []).map(p => [p.x, p.y]),
       regions: (row.regions || []).slice(), movie: row.movie || ''}
    : {type: row.type || '', frequency: row.frequency || '',
       winter: row.winter || '', summer: row.summer || '',
       warning: row.warning || '', warning_set: !!row.warning_set,
       min_scale: row.min_scale || '', max_scale: row.max_scale || '',
       climates: (row.climates || []).slice(),
       regions: (row.regions || []).slice(),
       positions: (row.positions || []).map(p => [p.x, p.y])};
  k.was = JSON.stringify(k.w);
}

function cevBlank(){
  const k = state.cev;
  return k.tab === 'events'
    ? {category: 'historic', name: '', dates: ['2'], positions: [],
       regions: [], movie: ''}
    : {type: cevFreeType(), frequency: '20', winter: 'false', summer: 'false',
       warning: 'false', warning_set: true, min_scale: '2', max_scale: '5',
       climates: [], regions: [], positions: []};
}

//: The first of the eight disaster types this file has not declared yet. The
//: engine has one setting per disaster, so offering one it already has would
//: only produce a block that is never read.
function cevFreeType(){
  const k = state.cev, have = cevRows().map(r => (r.type || '').toLowerCase());
  const types = (k.dis && k.dis.types) || [];
  return types.find(t => have.indexOf(t) < 0) || types[0] || '';
}

const cevDirty = () => {
  const k = state.cev;
  return !!(k && k.w) && (k.adding || JSON.stringify(k.w) !== k.was);
};

function cevPick(name){
  const k = state.cev;
  if(!k) return;
  k.sel = k.sel === name && !k.adding ? '' : name;
  k.adding = false;
  k.preview = null;
  cevReset();
  cevPaint();
}

function cevAdd(){
  const k = state.cev;
  if(!k) return;
  k.adding = true; k.sel = ''; k.preview = null;
  cevReset();
  cevPaint();
}

function cevSet(key, value){
  const k = state.cev;
  if(!k || !k.w) return;
  k.w[key] = value;
  // no repaint: the caret is in the box. The Save button appears on the next
  // paint anything else causes, and the save checks dirtiness for itself.
}

//: A box whose change has to be seen at once - a select, or a list row going.
function cevSetPaint(key, value){
  cevSet(key, value);
  cevPaint();
}

/* ---------- the three lists a block carries ---------- */

function cevListAdd(key, value){
  const k = state.cev;
  if(!k || !k.w) return;
  k.w[key] = (k.w[key] || []).concat([value]);
  cevPaint();
}

function cevListSet(key, i, value){
  const k = state.cev;
  if(!k || !k.w) return;
  const list = (k.w[key] || []).slice();
  list[i] = value;
  k.w[key] = list;
}

function cevListDrop(key, i){
  const k = state.cev;
  if(!k || !k.w) return;
  const list = (k.w[key] || []).slice();
  list.splice(i, 1);
  k.w[key] = list;
  cevPaint();
}

function cevPosSet(i, which, value){
  const k = state.cev;
  if(!k || !k.w) return;
  const list = k.w.positions.map(p => p.slice());
  const n = parseInt(value, 10);
  list[i][which] = isNaN(n) ? value : n;
  k.w.positions = list;
}

/* The tile the map is picked on, in the coordinates the FILE writes.

   The one place in this panel that flip is made, and it is made here rather
   than on the server for the reason `mapquery.marker_view` gives about the
   other direction: whoever is holding the map's height owns the flip, and doing
   it twice in two places is how a coordinate ends up mirrored. */
function cevPicked(){
  const c = state.cmap;
  if(!c || !c.pick) return null;
  return [c.pick[0], c.man.height - 1 - c.pick[1]];
}

function cevPosFromPick(){
  const at = cevPicked();
  if(!at){ toast('Click a tile on the map first', 4000); return; }
  cevListAdd('positions', at);
}

//: Put the map on one of this block's positions, the way a finding's jump does.
function cevGo(i){
  const k = state.cev, c = state.cmap;
  if(!k || !k.w || !c) return;
  const p = k.w.positions[i];
  if(!p) return;
  const tile = [p[0], c.man.height - 1 - p[1]];
  if(!(tile[0] >= 0 && tile[1] >= 0 && tile[0] < c.man.width
       && tile[1] < c.man.height)){
    toast(`${p[0]},${p[1]} is off a ${c.man.width}×${c.man.height} map`, 5000);
    return;
  }
  const [w, h] = cmapCanvasSize();
  const v = c.view;
  v.zoom = Math.max(v.zoom, 8);
  v.ox = w / 2 - (tile[0] + 0.5) * v.zoom;
  v.oy = h / 2 - (tile[1] + 0.5) * v.zoom;
  v.fitted = true;
  cmapPick(tile);
  activity('map event', `went to ${p[0]},${p[1]}`);
}

/* ---------- the save ---------- */

function cevBody(action){
  const k = state.cev, w = k.w;
  const edits = k.tab === 'events'
    ? {category: w.category, name: w.name, dates: w.dates,
       positions: w.positions, regions: w.regions, movie: w.movie}
    : {type: w.type, frequency: w.frequency, winter: w.winter,
       summer: w.summer, warning: w.warning, min_scale: w.min_scale,
       max_scale: w.max_scale, climates: w.climates, regions: w.regions,
       positions: w.positions};
  return {mod: k.mod, what: k.tab, action: action || (k.adding ? 'add' : 'edit'),
          campaign: k.campaign,
          // a rename is a save against the name the block HAS, with the new one
          // in `edits`; the server splices the head line rather than making a
          // second block
          name: k.adding ? (k.tab === 'events' ? w.name : w.type) : k.sel,
          edits};
}

async function cevSave(action){
  const k = state.cev;
  if(!k || !k.w || k.busy) return;
  const body = cevBody(action);
  if(!body.name){
    toast(k.tab === 'events' ? 'An event needs a label' : 'A disaster needs a type',
          4000);
    return;
  }
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/campevents/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){
    toast('✗ ' + plan.error, 8000);
    k.preview = plan.plan || null;
    cevPaint();
    return;
  }
  const p = plan.plan || {};
  k.preview = p;
  cevPaint();
  const what = k.tab === 'events' ? 'event' : 'disaster';
  const verb = body.action === 'add' ? 'Add' : body.action === 'delete'
    ? 'Delete' : 'Write';
  if(!confirm(`${verb} the ${what} ${body.name}`
    + (k.tab === 'events' ? ` in ${k.campaign || 'this campaign'}` : '') + '?\n\n'
    + ((p.changes || []).slice(0, 14).join('\n') || 'no visible change')
    + ((p.changes || []).length > 14
       ? `\n…and ${p.changes.length - 14} more` : '')
    + ((p.warnings || []).length
       ? '\n\n' + (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x).join('\n') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/campevents/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('campaign events', `${k.mod}: ${body.action} ${what} ${body.name}`);
  k.sel = body.action === 'delete' ? '' : body.name;
  k.adding = false;
  await cevLoad();
  // the markers layer is drawn from these files too, so it is now a version
  // behind - the same reload 17d does after a character moves
  if(state.cmk && state.cmk.d){ state.cmk.d = null; cmkLoad(); }
}

function cevDelete(){
  const k = state.cev;
  if(!k || !k.sel) return;
  cevSave('delete');
}

/* ---------- drawing ---------- */

function cevPaint(){
  const el = document.getElementById('cmEvents');
  if(!el) return;
  el.innerHTML = cevHtml();
}

function cevHtml(){
  const k = state.cev;
  if(!k) return '';
  const n = (k.ev && k.ev.rows ? k.ev.rows.length : 0)
          + (k.dis && k.dis.rows ? k.dis.rows.length : 0);
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cevToggle()"
      title="descr_events.txt and descr_disasters.txt: the historical events a campaign fires, and the earthquakes, floods and plagues the map allows. Both place things by coordinate, so both are edited beside the map.">
      ⚡ Events${k.open ? ' ✓' : ''}</button>
    ${k.ev ? `<span class="count">${n} block${n === 1 ? '' : 's'}</span>` : ''}
    ${k.busy ? '<span class="count">working…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + '<div class="cxpanel count">reading the two files…</div>';
  if(k.err) return head + `<div class="cxpanel"><div class="w-bad">${esc(k.err)}</div></div>`;
  return head + `<div class="cxpanel">
    <div class="cqtabs">${CEV_TABS.map(([id, label]) =>
      `<button class="${k.tab === id ? 'on' : ''}" onclick="cevTab('${id}')"
        >${label}</button>`).join('')}</div>
    ${cevFileHtml()}
    ${cevWarnHtml()}
    ${cevListHtml()}
    ${k.w ? (k.tab === 'events' ? cevEventFormHtml() : cevDisasterFormHtml()) : ''}
    ${cevPlanHtml()}
  </div>`;
}

//: Which file this tab writes, and the sentence for a mod that has not got it.
function cevFileHtml(){
  const k = state.cev, d = cevData();
  if(!d) return '';
  if(!d.have) return `<div class="w-warn">${esc(d.problem || 'this file is not here')}
    <div class="count">${esc(d.file)}</div></div>`;
  const extra = k.tab === 'events'
    ? `labels are looked up in ${esc(d.text_file || '')} as
       <code>{NAME_TITLE}</code> and <code>{NAME_BODY}</code>`
    : `one set of disasters per map, whatever the campaign`;
  return `<div class="count">${esc(d.file)} · ${extra}</div>`;
}

function cevWarnHtml(){
  const d = cevData();
  const rows = ((d && d.warnings) || []).slice(0, 4);
  const bad = ((d && d.findings) || []).filter(f => f.fatal).length;
  const warn = ((d && d.findings) || []).length - bad;
  return rows.map(w => `<div class="w-warn">${esc(w)}</div>`).join('')
    + (bad || warn ? `<div class="count">${bad ? `${bad} fatal · ` : ''}${
        warn} thing${warn === 1 ? '' : 's'} to look at, listed against the
        block each belongs to</div>` : '');
}

/* One row per block, with what is wrong with it counted beside it.

   A disaster the file has not declared is still a row, greyed, for the reason
   18a's description screen shows a faction with no key: the eight are a fixed
   set, and "this map has no floods" is a fact somebody came here to learn or to
   change, not an absence to be hidden. */
function cevListHtml(){
  const k = state.cev, d = cevData();
  if(!d || !d.have) return '';
  const findings = d.findings || [];
  const rows = cevRows().map(r => {
    const name = cevKey(r);
    const mine = findings.filter(f => (f.name || '') === name);
    const bad = mine.filter(f => f.fatal).length;
    const where = k.tab === 'events'
      ? `${esc(r.category || '?')} · ${esc((r.dates || []).join(' / ') || 'no date')}`
      : `every ${esc(r.frequency || '?')} years`;
    const pos = (r.positions || []).length;
    return `<div class="cxrow${k.sel === name && !k.adding ? ' on' : ''}"
      onclick="cevPick('${esc(name).replace(/'/g, "\\'")}')">
      <b>${esc(name || '(unnamed)')}</b>
      <span class="count">${where}${pos ? ` · ${pos} position${pos === 1 ? '' : 's'}` : ''}</span>
      ${bad ? `<span class="w-bad">${bad}</span>`
        : mine.length ? `<span class="w-warn">${mine.length}</span>` : ''}
    </div>`;
  }).join('');
  const undeclared = k.tab === 'disasters'
    ? (d.types || []).filter(t => !cevRows().some(r => (r.type || '') === t))
    : [];
  return `<div class="cxlist">${rows}
    ${undeclared.map(t => `<div class="cxrow"><b class="count">${esc(t)}</b>
      <span class="count">not declared - never happens</span></div>`).join('')}
    </div>
    <div class="csbtns">
      <button onclick="cevAdd()">＋ ${k.tab === 'events' ? 'New event'
        : 'Declare a disaster'}</button>
    </div>`;
}

/* ---------- the two forms ---------- */

//: The rows of coordinates a block carries, in both forms.
function cevPositionsHtml(){
  const k = state.cev, w = k.w, d = cevData();
  const size = d && d.size;
  const rows = (w.positions || []).map((p, i) => {
    const off = size && !(p[0] >= 0 && p[1] >= 0 && p[0] < size[0] && p[1] < size[1]);
    return `<div class="cxrow">
      <input style="width:5.5em" value="${esc(String(p[0]))}"
        oninput="cevPosSet(${i}, 0, this.value)">
      <input style="width:5.5em" value="${esc(String(p[1]))}"
        oninput="cevPosSet(${i}, 1, this.value)">
      ${off ? `<span class="w-bad">off a ${size[0]}×${size[1]} map</span>`
            : '<span class="count">x, y</span>'}
      <button onclick="cevGo(${i})" title="Put the map on this tile">◎</button>
      <button onclick="cevListDrop('positions', ${i})" title="Remove">✕</button>
    </div>`;
  }).join('');
  const at = cevPicked();
  return `<div class="cmfield"><label>Positions</label>
    <div class="cxlist">${rows || '<div class="count">none</div>'}</div>
    <div class="csbtns">
      <button onclick="cevPosFromPick()">＋ from the picked tile${
        at ? ` (${at[0]}, ${at[1]})` : ''}</button>
      <button onclick="cevListAdd('positions', [0, 0])">＋ blank</button>
    </div>
    <div class="count">The file writes y up from the bottom of the map, and so
      does this - the number here is the one in descr_strat.txt, not the image
      row.</div>
  </div>`;
}

//: A plain repeatable list of words - an event's regions, a disaster's climates.
function cevWordsHtml(key, label, note, options){
  const w = state.cev.w;
  const list = w[key] || [];
  const rows = list.map((v, i) => `<div class="cxrow">
    ${options && options.length
      ? `<select onchange="cevListSet('${key}', ${i}, this.value); cevPaint()">
          ${options.indexOf(v) < 0 ? `<option selected>${esc(v)}</option>` : ''}
          ${options.map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`)
            .join('')}</select>`
      : `<input value="${esc(v)}" oninput="cevListSet('${key}', ${i}, this.value)">`}
    <button onclick="cevListDrop('${key}', ${i})" title="Remove">✕</button>
  </div>`).join('');
  return `<div class="cmfield"><label>${esc(label)}</label>
    <div class="cxlist">${rows || '<div class="count">none</div>'}</div>
    <div class="csbtns"><button
      onclick="cevListAdd('${key}', ${options && options.length
        ? `'${esc(options[0])}'` : "''"})">＋ add</button></div>
    ${note ? `<div class="count">${note}</div>` : ''}
  </div>`;
}

function cevEventFormHtml(){
  const k = state.cev, w = k.w, d = k.ev;
  const cats = d.categories || [];
  const dates = (w.dates || []).map((v, i) => `<div class="cxrow">
    <input value="${esc(v)}" oninput="cevListSet('dates', ${i}, this.value)">
    <span class="count">a year offset, or two for a range</span>
    <button onclick="cevListDrop('dates', ${i})" title="Remove">✕</button>
  </div>`).join('');
  const placed = (d.placed || []).indexOf(w.category) >= 0;
  return `<div class="cxform">
    <div class="csrow2">
      <div class="cmfield"><label>Category</label>
        <select onchange="cevSetPaint('category', this.value)">
          ${cats.indexOf(w.category) < 0 && w.category
            ? `<option selected>${esc(w.category)}</option>` : ''}
          ${cats.map(c => `<option${c === w.category ? ' selected' : ''}
            >${esc(c)}</option>`).join('')}
        </select>
        <div class="count">${placed
          ? 'happens at the positions below, so it needs at least one'
          : w.category === 'emergent_faction'
            ? 'the label is the faction that emerges, and it must be marked emergent in descr_strat.txt'
            : w.category === 'counter'
              ? 'increases a counter and shows no message'
              : 'shows the message the label names'}</div>
      </div>
      <div class="cmfield"><label>Label</label>
        <input value="${esc(w.name)}" oninput="cevSet('name', this.value)">
        <div class="count">${w.name
          ? `{${esc(w.name.toUpperCase())}_TITLE} and _BODY, and
             ${esc(w.name)}.tga in every eventspic folder`
          : 'the key the title, the body and the picture are all found by'}</div>
      </div>
    </div>
    <div class="cmfield"><label>Dates</label>
      <div class="cxlist">${dates || '<div class="count">none - it never fires</div>'}</div>
      <div class="csbtns"><button onclick="cevListAdd('dates', '')">＋ add</button></div>
    </div>
    ${cevPositionsHtml()}
    ${cevWordsHtml('regions', 'Regions', 'an alternative to positions - the '
      + 'file header allows either', [])}
    <div class="cmfield"><label>Movie</label>
      <input value="${esc(w.movie)}" placeholder="event/gunpowder_invented.bik"
        oninput="cevSet('movie', this.value)">
      <div class="count">cleared to nothing, the line goes rather than being
        written empty</div>
    </div>
    ${cevFindingsHtml()}
    ${cevButtonsHtml()}
  </div>`;
}

function cevDisasterFormHtml(){
  const k = state.cev, w = k.w, d = k.dis;
  const types = d.types || [];
  const flag = (key, label) => `<div class="cmfield"><label>${label}</label>
    <select onchange="cevSetPaint('${key}', this.value)">
      <option value=""${w[key] === '' ? ' selected' : ''}>(no line)</option>
      <option value="false"${w[key] === 'false' ? ' selected' : ''}>false</option>
      <option value="true"${w[key] === 'true' ? ' selected' : ''}>true</option>
    </select></div>`;
  const num = (key, label, note) => `<div class="cmfield"><label>${label}</label>
    <input value="${esc(String(w[key]))}" oninput="cevSet('${key}', this.value)">
    ${note ? `<div class="count">${note}</div>` : ''}</div>`;
  return `<div class="cxform">
    <div class="csrow2">
      <div class="cmfield"><label>Type</label>
        <select onchange="cevSetPaint('type', this.value)" ${k.adding ? '' : 'disabled'}>
          ${types.indexOf(w.type) < 0 && w.type
            ? `<option selected>${esc(w.type)}</option>` : ''}
          ${types.map(t => `<option${t === w.type ? ' selected' : ''}
            >${esc(t)}</option>`).join('')}
        </select>
        <div class="count">${k.adding ? 'the engine has one setting per disaster'
          : 'the type names the block; delete and declare to change it'}</div>
      </div>
      ${num('frequency', 'Frequency', 'in years - higher is rarer')}
    </div>
    <div class="csrow2">${flag('winter', 'Winter only')}${flag('summer', 'Summer only')}</div>
    <div class="csrow2">
      ${flag('warning', 'One year warning')}
      <div class="cmfield"><label>Scale</label>
        <div class="csrow2">
          <input value="${esc(String(w.min_scale))}"
            oninput="cevSet('min_scale', this.value)">
          <input value="${esc(String(w.max_scale))}"
            oninput="cevSet('max_scale', this.value)">
        </div>
        <div class="count">smallest and largest it can be</div>
      </div>
    </div>
    ${cevWordsHtml('climates', 'Climates',
      (d.climates || []).length
        ? 'from this mod\'s own descr_climates.txt'
        : 'descr_climates.txt is not on disk here, so nothing checks these',
      d.climates || [])}
    ${cevWordsHtml('regions', 'Regions',
      `<code>${esc(d.sea_region || 'the sea')}</code> is the one value that is
       not a region and is still right - vanilla's storm and horde both use it`,
      [])}
    ${cevPositionsHtml()}
    ${cevFindingsHtml()}
    ${cevButtonsHtml()}
  </div>`;
}

//: What the server says about the block on screen, out of the whole-file run.
function cevFindingsHtml(){
  const k = state.cev, d = cevData();
  const name = k.adding ? '' : k.sel;
  const mine = ((d && d.findings) || []).filter(f => (f.name || '') === name);
  if(!mine.length) return '';
  return `<div class="cjplan">${mine.map(f =>
    `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}${
      f.line ? ` <span class="count">line ${f.line}</span>` : ''}</div>`).join('')}
  </div>`;
}

function cevButtonsHtml(){
  const k = state.cev;
  const what = k.tab === 'events' ? 'event' : 'disaster';
  return `<div class="csbtns">
    ${cevDirty() ? `<button class="primary" onclick="cevSave()">${
      k.adding ? `Add the ${what}` : `Save the ${what}`}</button>` : ''}
    ${k.adding ? `<button onclick="cevPick('')">Cancel</button>`
      : `<button onclick="cevDelete()">Delete</button>`}
  </div>`;
}

//: The last plan, for when a save was refused and the reason has to stay put.
function cevPlanHtml(){
  const p = state.cev && state.cev.preview;
  if(!p) return '';
  const errs = (p.errors || []).filter(e => e !== 'nothing to change');
  if(!errs.length && !p.block) return '';
  return `<div class="cjplan">
    ${errs.map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${p.block ? `<pre class="cjblock">${esc(p.block)}</pre>` : ''}
  </div>`;
}
