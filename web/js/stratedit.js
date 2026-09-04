/* stratedit.js - Campaign Map: the settlement a province starts with

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE SETTLEMENT PANEL - Phase 16h.

   Every name here starts `cs`, and the only two `cs` names anywhere else in
   the tree are `cssq` and `csv`, neither of which is a `csXxx` - checked, the
   way 16e checked `cp`, 16f checked `cchk` and 16g checked `cq`.

   PYTHON OWNS THE RULES, INCLUDING THE ONES THAT LOOK EASY. Whether a
   `merchant_vault` may stand in a castle, whether `level town` is high enough
   for a `hall_2`, which faction's capital moves when this province changes
   hands: every one of those is decided in stratedit.py and arrives here as a
   sentence. There is no second copy of the ladder on this side deciding
   anything, and the numbers shown beside a building row - its pin, its
   settlement_min - are the server's own data being displayed rather than a
   rule being applied.

   SO THE FORM ASKS. The panel posts /api/map/settlement_plan while somebody is
   still typing, on a 450 ms debounce, and shows what comes back. That is a
   whole plan - the file spliced, re-read and checked - for the price of a
   fifth of a second on the largest campaign installed, and it means the
   findings under the form are the findings the save would produce rather than
   a browser's guess at them.

   THE BUILDING LIST IS THE FILE'S ORDER. What the rows read top to bottom is
   what the block writes top to bottom, so dragging a row and saving reorders
   the block. Rows that keep their level are not rewritten at all, which is
   what lets the five buildings you did not touch keep their comments.
   ===================================================================== */

//: How long after the last keystroke the panel asks the server what it thinks.
//: A plan is a file read, a splice and two parses; 450 ms is long enough that
//: typing a four-digit population asks once rather than four times.
const CS_DEBOUNCE = 450;

/* ---------- state ----------

   Beside `state.cmap` rather than inside it, like the paint tool, the
   validator and the query panel: `loadCampmap` rebuilds that object whenever
   the mod changes, and which settlement somebody has open is not a fact about
   the map. */
function csNew(mod, region){
  return {mod, region, open: true, loading: false, err: '', d: null,
          w: null, blds: [], owner: '', place: '', busy: false,
          preview: null, timer: 0};
}

//: Called from the map's own pick, so opening a province opens its settlement.
//: A province nobody starts holding has no block to edit and says so.
async function csOpen(region){
  const c = state.cmap;
  if(!c) return;
  const was = state.cset;
  if(!region){ state.cset = null; csPaint(); return; }
  if(was && was.mod === c.mod && was.region === region && was.d) return;
  const k = state.cset = csNew(c.mod, region);
  k.open = was ? was.open : true;
  k.loading = true;
  csPaint();
  let d;
  try{ d = await api.get(`/api/map/settlement?mod=${enc(c.mod)}`
    + `&region=${enc(region)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cset !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; csPaint(); return; }
  csAdopt(k, d);
  csPaint();
}

//: The working copy every box edits and every save is built from, and the
//: values beside it are what came off disk - so "has anything changed" is a
//: comparison rather than a flag somebody has to remember to set.
function csAdopt(k, d){
  k.d = d;
  k.w = {settlement_type: d.settlement_type, level: d.level,
         population: d.population == null ? '' : String(d.population),
         year_founded: d.year_founded == null ? '' : String(d.year_founded),
         plan_set: d.plan_set, faction_creator: d.faction_creator};
  k.blds = (d.buildings || []).map(b => ({line: b.line, level: b.level}));
  k.owner = d.owner;
  k.place = '';
  k.preview = null;
}

function csToggle(){
  const k = state.cset;
  if(!k) return;
  k.open = !k.open;
  csPaint();
}

/* ---------- editing ---------- */

function csSet(slot, value){
  const k = state.cset;
  if(!k || !k.w) return;
  k.w[slot] = value;
  // the castle tier beside the level changes with both boxes, and the level
  // list itself does not, so this is a repaint rather than a rebuild
  csPlanSoon();
  csPaint();
}

function csBld(i, slot, value){
  const k = state.cset;
  if(!k || !k.blds[i]) return;
  k.blds[i][slot] = value;
  if(slot === 'line'){
    // a line without one of its own levels is not a building the engine can
    // find, so picking a line picks its first level with it
    const line = (k.d.vocab.lines || []).find(L => L.name === value);
    k.blds[i].level = line && line.levels.length ? line.levels[0].level : '';
  }
  csPlanSoon();
  csPaint();
}

function csBldDrop(i){
  const k = state.cset;
  if(!k) return;
  k.blds.splice(i, 1);
  csPlanSoon();
  csPaint();
}

function csBldMove(i, by){
  const k = state.cset;
  const j = i + by;
  if(!k || j < 0 || j >= k.blds.length) return;
  const row = k.blds[i];
  k.blds[i] = k.blds[j];
  k.blds[j] = row;
  csPlanSoon();
  csPaint();
}

function csBldAdd(name){
  const k = state.cset;
  if(!k || !name) return;
  const line = (k.d.vocab.lines || []).find(L => L.name === name);
  k.blds.push({line: name,
               level: line && line.levels.length ? line.levels[0].level : ''});
  csPlanSoon();
  csPaint();
}

function csOwner(value){
  const k = state.cset;
  if(!k) return;
  k.owner = value;
  // a province given to somebody else has to land somewhere in their block,
  // and the file's own habit is at the end
  if(value !== k.d.owner && !k.place) k.place = 'last';
  if(value === k.d.owner && k.place === 'last') k.place = '';
  csPlanSoon();
  csPaint();
}

function csPlace(value){
  const k = state.cset;
  if(!k) return;
  k.place = value;
  csPlanSoon();
  csPaint();
}

/* ---------- what the server makes of it ---------- */

//: Everything the save would post, so the preview and the save cannot disagree
//: about what is being asked for.
function csBody(){
  const k = state.cset;
  const body = {mod: k.mod, region: k.region, campaign: k.d.campaign,
                edits: {settlement_type: k.w.settlement_type,
                        level: (k.w.level || '').trim(),
                        population: String(k.w.population).trim(),
                        year_founded: String(k.w.year_founded).trim(),
                        plan_set: (k.w.plan_set || '').trim(),
                        faction_creator: (k.w.faction_creator || '').trim()},
                buildings: k.blds.map(b => ({line: b.line, level: b.level}))};
  if(k.owner && k.owner !== k.d.owner) body.owner = k.owner;
  if(k.place) body.place = k.place;
  return body;
}

function csPlanSoon(){
  const k = state.cset;
  if(!k || !k.d) return;
  clearTimeout(k.timer);
  k.timer = setTimeout(() => csPlanNow(k), CS_DEBOUNCE);
}

async function csPlanNow(k){
  if(state.cset !== k || !k.d) return;
  let res;
  try{ res = await api.post('/api/map/settlement_plan', csBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.cset !== k) return;
  k.preview = res.plan || null;
  csPaint();
}

async function csSave(){
  const k = state.cset;
  if(!k || !k.d || k.busy) return;
  clearTimeout(k.timer);
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/settlement_plan', csBody()); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); k.preview = plan.plan || null;
    csPaint(); return; }
  const p = plan.plan || {};
  k.preview = p;
  csPaint();
  const lines = (p.changes || []).slice(0, 14);
  const notes = (p.capitals || []).concat((p.warnings || []).slice(0, 4))
    .map(x => '⚠ ' + x);
  if(!confirm(`Write: save the settlement in ${k.region}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14
       ? `\n…and ${p.changes.length - 14} more` : '')
    + (notes.length ? '\n\n' + notes.join('\n') : '')
    + '\n\nOnly this block moves. Backed up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/settlement_apply', csBody()); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('settlement', `${k.mod} ${k.region} saved`);
  const at = state.cmap && state.cmap.pick;
  await loadCampmap();
  if(at && state.cmap) cmapPick(at);
}

function csRevert(){
  const k = state.cset;
  if(!k || !k.d) return;
  csAdopt(k, k.d);
  csPaint();
}

/* ---------- drawing ---------- */

function csPaint(){
  const el = document.getElementById('cmSettle');
  if(!el) return;
  el.innerHTML = csHtml();
}

function csHtml(){
  const k = state.cset;
  if(!k) return '';
  const d = k.d;
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="csToggle()"
      title="The settlement this province starts with: its level, its buildings and who holds it."
      >\u{1F3DB} Settlement${k.open ? ' ✓' : ''}</button>
    ${d ? `<span class="count">${esc(d.owner_label || d.owner || 'nobody')}${
      d.is_capital ? ' · capital' : ''}</span>` : ''}
    ${k.busy ? '<span class="count">working…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + `<div class="cspanel count">reading
    ${esc(k.region)}…</div>`;
  if(k.err) return head + `<div class="cspanel w-warn">${esc(k.err)}</div>`;
  if(!d) return head;
  return head + `<div class="cspanel">
    <div class="cshead">
      <b>${esc(d.shown_settlement || d.settlement || d.region)}</b>
      <span class="count">${esc(d.file)}, lines ${d.lines[0]}-${d.lines[1]}</span>
    </div>
    ${csFormHtml()}
    ${csBuildingsHtml()}
    ${csOwnerHtml()}
    ${csFindingsHtml()}
    <div class="csbtns">
      <button class="primary" onclick="csSave()">Save settlement</button>
      <button onclick="csRevert()">Revert</button>
    </div>
  </div>`;
}

function csFormHtml(){
  const k = state.cset, d = k.d, w = k.w, v = d.vocab;
  const tier = w.settlement_type === 'castle'
    ? (v.castle_tier || {})[w.level] || '' : '';
  const list = (slot, values) => `<datalist id="csl-${slot}">${
    (values || []).map(x => `<option value="${esc(x)}">`).join('')}</datalist>`;
  return `<div class="cmform">
    <div class="csrow2">
      <div class="cmfield"><label>Kind</label>
        <select onchange="csSet('settlement_type', this.value)">
          ${(v.types || []).map(t => `<option value="${esc(t)}"${
            t === w.settlement_type ? ' selected' : ''}>${esc(t)}</option>`).join('')}
        </select></div>
      <div class="cmfield"><label>Level</label>
        <select onchange="csSet('level', this.value)">
          ${(v.ladder || []).map(l => `<option value="${esc(l)}"${
            l === w.level ? ' selected' : ''}>${esc(l)}</option>`).join('')}
          ${(v.ladder || []).includes(w.level) ? ''
            : `<option value="${esc(w.level)}" selected>${esc(w.level)}</option>`}
        </select>
        ${tier ? `<div class="count">a castle at this level is a
          <b>${esc(tier)}</b></div>` : ''}</div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Population</label>
        <input type="number" value="${esc(w.population)}" min="0"
          oninput="csSet('population', this.value)"></div>
      <div class="cmfield"><label>Year founded</label>
        <input type="number" value="${esc(w.year_founded)}"
          oninput="csSet('year_founded', this.value)"></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Plan set</label>
        <input list="csl-plan" value="${esc(w.plan_set)}"
          oninput="csSet('plan_set', this.value)">
        ${list('plan', v.plan_sets)}
        <div class="count">The street plan the battle map is drawn from.
        ${(v.plan_sets || []).length > 1
          ? `This campaign uses ${(v.plan_sets || []).length}.`
          : 'This campaign uses one.'}</div></div>
      <div class="cmfield"><label>Faction creator</label>
        <input list="csl-creator" value="${esc(w.faction_creator)}"
          oninput="csSet('faction_creator', this.value)">
        ${list('creator', v.factions)}
        <div class="count">Whose architecture it is built in, which is not the
        same as who holds it.</div></div>
    </div>
  </div>`;
}

/* One row per building, in the order the block writes them.

   The line and the level are two boxes rather than one, because that is what
   the file writes - `type <line> <level>` - and because picking a line is what
   narrows the levels worth offering. What each level's own EDB block says is
   printed beside it as text; whether that is a problem is the server's to say,
   and it says so in the findings below. */
function csBuildingsHtml(){
  const k = state.cset, v = k.d.vocab;
  const lines = v.lines || [];
  const rows = k.blds.map((b, i) => {
    const L = lines.find(x => x.name === b.line);
    const levels = (L && L.levels) || [{level: b.level, declared: false}];
    const info = levels.find(x => x.level === b.level);
    const note = !info ? ''
      : !info.declared ? 'not in an EDB on disk'
      : [info.pin ? info.pin + ' only' : '',
         info.min ? 'from ' + info.min : '',
         info.max ? 'to ' + info.max : ''].filter(Boolean).join(' · ');
    return `<div class="csbld">
      <select onchange="csBld(${i}, 'line', this.value)">
        ${lines.map(x => `<option value="${esc(x.name)}"${
          x.name === b.line ? ' selected' : ''}>${esc(x.name)}</option>`).join('')}
        ${L ? '' : `<option value="${esc(b.line)}" selected>${esc(b.line)}</option>`}
      </select>
      <select onchange="csBld(${i}, 'level', this.value)">
        ${levels.map(x => `<option value="${esc(x.level)}"${
          x.level === b.level ? ' selected' : ''}>${esc(x.level)}</option>`).join('')}
        ${info ? '' : `<option value="${esc(b.level)}" selected>${esc(b.level)}</option>`}
      </select>
      <button onclick="csBldMove(${i}, -1)" title="Move up">↑</button>
      <button onclick="csBldMove(${i}, 1)" title="Move down">↓</button>
      <button onclick="csBldDrop(${i})" title="Take this building out">✕</button>
      ${note ? `<span class="count csnote">${esc(note)}</span>` : ''}
    </div>`;
  }).join('');
  return `<div class="k">Buildings
      <span class="count">${k.blds.length}${v.have_edb ? ''
        : ' · no export_descr_buildings.txt on disk, so these are the lines this'
          + ' campaign itself names'}</span></div>
    <div class="csblds">${rows || '<div class="count">None.</div>'}</div>
    <div class="csadd">
      <select onchange="csBldAdd(this.value); this.value=''">
        <option value="">add a building…</option>
        ${lines.map(x => `<option value="${esc(x.name)}">${esc(x.name)}</option>`)
          .join('')}
      </select>
    </div>`;
}

/* Who holds it, and where in their block it sits.

   The two are one control because in the file they are one thing: the block's
   position IS the owner, and its position within the block is whether it is
   the capital. */
function csOwnerHtml(){
  const k = state.cset, d = k.d;
  const rows = d.factions || [];
  const dest = rows.find(f => f.name === k.owner);
  const moving = k.owner !== d.owner;
  return `<div class="k">Owner
      <span class="count">the block's place in the file</span></div>
    <div class="csown">
      <select onchange="csOwner(this.value)">
        ${rows.map(f => `<option value="${esc(f.name)}"${
          f.name === k.owner ? ' selected' : ''}>${esc(f.label || f.name)}${
          f.roster ? ' · ' + esc(f.roster) : ' · in no roster'} · ${
          f.settlements} held</option>`).join('')}
      </select>
      <select onchange="csPlace(this.value)">
        <option value=""${k.place ? '' : ' selected'}>leave it where it is</option>
        <option value="first"${k.place === 'first' ? ' selected' : ''}
          >first in the block - the capital</option>
        <option value="last"${k.place === 'last' ? ' selected' : ''}
          >last in the block</option>
      </select>
      ${dest && dest.capital ? `<div class="count">${esc(dest.name)}'s capital is
        ${esc(dest.capital)}${moving && k.place === 'first'
          ? ', and this would take its place' : ''}.</div>` : ''}
      ${moving && !k.place ? `<div class="count">A province cannot change hands
        without moving: pick where in ${esc(k.owner)}'s block it lands.</div>` : ''}
    </div>`;
}

/* What the server says about the form as it stands.

   `preview` is a whole plan, so what is under the form is what the save would
   do: the same findings, the same changes and the same refusals. Before the
   first plan comes back it is the detail's own findings, which are the same
   check run over the block as it is on disk. */
function csFindingsHtml(){
  const k = state.cset, p = k.preview;
  const findings = p ? (p.findings || []) : (k.d.findings || []);
  const changes = p ? (p.changes || []) : [];
  const errors = p ? (p.errors || []) : [];
  const caps = p ? (p.capitals || []) : [];
  const said = findings.map(f => f.message);
  const real = errors.filter(e => e !== 'nothing to change');
  const rows = findings.map(f =>
    `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`).join('');
  // the plan's warnings are the findings plus the two a move makes on its own -
  // a faction left holding nothing, and the architecture that does not follow
  // the flag - and those two have no finding to carry them
  const extra = (p ? (p.warnings || []) : []).filter(w => !said.includes(w));
  const problems = (k.d.problems || []).map(x =>
    `<div class="w-warn">${esc(x)}</div>`).join('');
  return `<div class="csfind">
    ${caps.map(c => `<div class="w-good">${esc(c)}</div>`).join('')}
    ${real.filter(e => !said.includes(e))
        .map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${rows}
    ${extra.map(w => `<div class="w-warn">${esc(w)}</div>`).join('')}
    ${problems}
    ${changes.length ? `<div class="count">Would change:
      ${changes.map(esc).join(' · ')}</div>`
      : p ? '<div class="count">Nothing to save yet.</div>' : ''}
  </div>`;
}
