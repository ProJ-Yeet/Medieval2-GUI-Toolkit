/* stratchar.js - Campaign Map: the people a faction starts the campaign with

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE CHARACTER PANEL - Phase 16i.

   Every name here starts `cx`, and there was no `cx` name anywhere in the tree
   before this phase - checked, the way 16e checked `cp`, 16f `cchk`, 16g `cq`
   and 16h `cs`.

   PYTHON OWNS THE RULES, AGAIN AND FOR THE SAME REASON. Whether a bodyguard
   should lead this army, whether a trait may reach level 3, whether a father is
   old enough to have had this son, whether the tile a general is standing on is
   sea: every one of those is decided in stratchar.py and arrives here as a
   sentence with the number that made it a rule attached. What is drawn beside a
   box - which units the EDU marks as bodyguards, how many levels a trait has -
   is the server's own data being shown, not a rule being applied twice.

   SO THE FORM ASKS, on the same 450 ms debounce 16h uses. A plan is a file
   read, a splice and two parses, and it comes back with the findings the save
   would produce rather than a browser's guess at them.

   ONE PANEL, FOUR ACTIONS. Edit, add, delete and move are the same form and
   the same request with a different `action`, because in the file they are the
   same edit: a block rewritten, inserted, cut out, or lifted from one faction's
   list into another's.
   ===================================================================== */

//: How long after the last keystroke the panel asks the server what it thinks.
const CX_DEBOUNCE = 450;

/* ---------- state ----------

   Beside `state.cmap` like every other campaign-map panel: which faction's
   people somebody is looking at is a habit, not a fact about the map. */
function cxNew(mod, faction){
  return {mod, faction, open: true, loading: false, err: '', d: null,
          pick: -1, w: null, busy: false, preview: null, timer: 0,
          adding: false, tab: 'people'};
}

async function cxOpen(faction){
  const c = state.cmap;
  if(!c) return;
  const was = state.cx;
  if(!faction){ state.cx = null; cxPaint(); return; }
  if(was && was.mod === c.mod && was.faction === faction && was.d) return;
  const k = state.cx = cxNew(c.mod, faction);
  k.open = was ? was.open : true;
  k.loading = true;
  cxPaint();
  let d;
  try{ d = await api.get(`/api/map/faction?mod=${enc(c.mod)}`
    + `&faction=${enc(faction)}${cmapCampQ()}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cx !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cxPaint(); return; }
  k.d = d;
  cxPaint();
}

function cxToggle(){
  const k = state.cx;
  if(!k) return;
  k.open = !k.open;
  cxPaint();
}

function cxTab(name){
  const k = state.cx;
  if(!k) return;
  k.tab = name;
  cxPaint();
}

/* ---------- picking somebody ---------- */

//: The working copy every box edits and every save is built from - the same
//: shape the settlement panel and the region form use, and the values beside
//: it are what came off disk, so "has anything changed" is a comparison.
function cxPick(i){
  const k = state.cx;
  if(!k || !k.d) return;
  k.adding = false;
  k.preview = null;
  if(i < 0 || i >= k.d.characters.length){ k.pick = -1; k.w = null; cxPaint(); return; }
  k.pick = i;
  const s = k.d.characters[i].spec;
  k.w = JSON.parse(JSON.stringify(s));
  cxPaint();
}

//: A blank person, in the shape the server will check. The type and the sex
//: are filled in because a form that opens on nothing invites a line the engine
//: cannot read; the coordinates are the tile the map is looking at.
function cxAdd(){
  const k = state.cx, c = state.cmap;
  if(!k || !k.d) return;
  const at = (c && c.pick) || [0, 0];
  k.adding = true;
  k.pick = -1;
  k.preview = null;
  k.w = {name: '', type: 'general', gender: 'male', rank: '', age: 25,
         x: at[0], y: c ? c.man.height - 1 - at[1] : 0, sub_faction: '',
         tail: {}, traits: [], ancillaries: [], army: []};
  cxPaint();
  cxPlanSoon();
}

function cxCancel(){
  const k = state.cx;
  if(!k) return;
  k.adding = false;
  k.w = null;
  k.pick = -1;
  k.preview = null;
  cxPaint();
}

/* ---------- editing ---------- */

function cxSet(slot, value){
  const k = state.cx;
  if(!k || !k.w) return;
  k.w[slot] = value;
  cxPlanSoon();
  cxPaint();
}

function cxTail(slot, value){
  const k = state.cx;
  if(!k || !k.w) return;
  if(value) k.w.tail[slot] = value; else delete k.w.tail[slot];
  cxPlanSoon();
  cxPaint();
}

function cxTrait(i, slot, value){
  const k = state.cx;
  if(!k || !k.w || !k.w.traits[i]) return;
  k.w.traits[i][slot] = slot === 'level' ? +value : value;
  cxPlanSoon();
  cxPaint();
}

function cxTraitAdd(name){
  const k = state.cx;
  if(!k || !k.w || !name) return;
  k.w.traits.push({name, level: 1});
  cxPlanSoon();
  cxPaint();
}

function cxTraitDrop(i){
  const k = state.cx;
  if(!k || !k.w) return;
  k.w.traits.splice(i, 1);
  cxPlanSoon();
  cxPaint();
}

function cxAncAdd(name){
  const k = state.cx;
  if(!k || !k.w || !name || k.w.ancillaries.includes(name)) return;
  k.w.ancillaries.push(name);
  cxPlanSoon();
  cxPaint();
}

function cxAncDrop(i){
  const k = state.cx;
  if(!k || !k.w) return;
  k.w.ancillaries.splice(i, 1);
  cxPlanSoon();
  cxPaint();
}

function cxUnit(i, slot, value){
  const k = state.cx;
  if(!k || !k.w || !k.w.army[i]) return;
  k.w.army[i][slot] = slot === 'unit' ? value : +value;
  cxPlanSoon();
  cxPaint();
}

function cxUnitAdd(name){
  const k = state.cx;
  if(!k || !k.w || !name) return;
  k.w.army.push({unit: name, exp: 0, armour: 0, weapon_lvl: 0});
  cxPlanSoon();
  cxPaint();
}

function cxUnitDrop(i){
  const k = state.cx;
  if(!k || !k.w) return;
  k.w.army.splice(i, 1);
  cxPlanSoon();
  cxPaint();
}

function cxUnitMove(i, by){
  const k = state.cx;
  const j = i + by;
  if(!k || !k.w || j < 0 || j >= k.w.army.length) return;
  const row = k.w.army[i];
  k.w.army[i] = k.w.army[j];
  k.w.army[j] = row;
  cxPlanSoon();
  cxPaint();
}

//: Put the general where the map is looking. The panel holds game coordinates,
//: which count y from the bottom, and the map holds image ones - the same
//: transform the probe prints under every tile.
function cxHere(){
  const k = state.cx, c = state.cmap;
  if(!k || !k.w || !c || !c.pick) return;
  k.w.x = c.pick[0];
  k.w.y = c.man.height - 1 - c.pick[1];
  cxPlanSoon();
  cxPaint();
}

//: 20c, M8. The pin's answer, already in game coordinates - `cpinTake` made
//: the flip - so this is `cxHere` without a picked tile to need first.
function cxPinned(game){
  const k = state.cx;
  if(!k || !k.w){ toast('✗ the character form was closed before the tile was picked', 5000);
    return; }
  k.w.x = game[0];
  k.w.y = game[1];
  cxPlanSoon();
  cxPaint();
}

/* ---------- what the server makes of it ---------- */

function cxBody(action){
  const k = state.cx, w = k.w;
  const row = k.pick >= 0 ? k.d.characters[k.pick] : null;
  const body = {mod: k.mod, campaign: k.d.campaign, faction: k.faction,
                action: action || (k.adding ? 'add' : 'edit')};
  if(row){ body.character = row.name; body.line = row.line; }
  if(!w) return body;
  body.edits = {name: w.name, type: w.type, gender: w.gender, rank: w.rank,
                age: w.age, x: w.x, y: w.y, sub_faction: w.sub_faction};
  for(const key of k.d.vocab.tail) body.edits[key] = w.tail[key] || '';
  body.traits = w.traits;
  body.ancillaries = w.ancillaries;
  body.army = w.army;
  return body;
}

function cxPlanSoon(){
  const k = state.cx;
  if(!k || !k.d || !k.w) return;
  clearTimeout(k.timer);
  k.timer = setTimeout(() => cxPlanNow(k), CX_DEBOUNCE);
}

async function cxPlanNow(k){
  if(state.cx !== k || !k.d || !k.w) return;
  let res;
  try{ res = await api.post('/api/map/character_plan', cxBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.cx !== k) return;
  k.preview = res.plan || null;
  cxPaint();
}

async function cxSave(action){
  const k = state.cx;
  if(!k || !k.d || k.busy) return;
  clearTimeout(k.timer);
  const what = action || (k.adding ? 'add' : 'edit');
  const body = cxBody(what);
  if(what === 'move'){
    const to = prompt(`Move ${body.character} to which faction?\n\n`
      + k.d.vocab.factions.join(', '), '');
    if(!to) return;
    body.owner = to.trim();
  }
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/character_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); k.preview = plan.plan || null;
    cxPaint(); return; }
  const p = plan.plan || {};
  k.preview = p;
  cxPaint();
  const lines = (p.changes || []).slice(0, 14);
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  const verb = {edit: 'save', add: 'add', delete: 'delete', move: 'move'}[what];
  if(!confirm(`Write: ${verb} ${body.character || (k.w && k.w.name) || 'this character'}`
    + ` in ${k.faction}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14
       ? `\n…and ${p.changes.length - 14} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nOnly this block moves. Backed up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/character_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('character', `${k.mod} ${k.faction}: ${what} ${res.name || ''}`);
  const at = state.cmap && state.cmap.pick;
  await loadCampmap();
  if(at && state.cmap) cmapPick(at);
}

/* ---------- drawing ---------- */

function cxPaint(){
  const el = document.getElementById('cmChars');
  if(!el) return;
  el.innerHTML = cxHtml();
}

function cxHtml(){
  const k = state.cx;
  if(!k) return '';
  const d = k.d;
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cxToggle()"
      title="The characters, armies and family this faction starts the campaign with."
      >\u{2694} People${k.open ? ' ✓' : ''}</button>
    ${d ? `<span class="count">${esc(d.label || d.faction)} ·
      ${d.characters.length} character${d.characters.length === 1 ? '' : 's'}${
      d.leader ? ' · ' + esc(d.leader) : ''}</span>` : ''}
    ${k.busy ? '<span class="count">working…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + `<div class="cxpanel count">reading
    ${esc(k.faction)}…</div>`;
  if(k.err) return head + `<div class="cxpanel w-warn">${esc(k.err)}</div>`;
  if(!d) return head;
  return head + `<div class="cxpanel">
    <div class="cqtabs">
      <button class="${k.tab === 'people' ? 'on' : ''}" onclick="cxTab('people')"
        >Characters</button>
      <button class="${k.tab === 'family' ? 'on' : ''}" onclick="cxTab('family')"
        >Family tree</button>
    </div>
    ${k.tab === 'people' ? cxPeopleHtml() : cxFamilyHtml()}
    ${cxSkippedHtml()}
  </div>`;
}

function cxSkippedHtml(){
  const s = (state.cx.d.vocab.skipped || []).filter(x =>
    /descr_names|export_descr_(unit|character_traits|ancillaries)/.test(x.what));
  if(!s.length) return '';
  return `<div class="cqskip"><div class="k">Not read</div>
    ${s.map(x => `<div class="count"><b>${esc(x.what)}</b> ${esc(x.why)}</div>`)
      .join('')}</div>`;
}

function cxPeopleHtml(){
  const k = state.cx, d = k.d;
  const rows = d.characters.map((c, i) => {
    const bad = (c.findings || []).filter(f => f.fatal).length;
    const warn = (c.findings || []).length - bad;
    return `<div class="cxrow${i === k.pick ? ' on' : ''}" onclick="cxPick(${i})">
      <b>${esc(c.name)}</b>
      <span class="count">${esc(c.type)}${c.rank ? ' · ' + esc(c.rank) : ''}
        · age ${c.age} · ${c.x},${c.y}${c.army ? ' · ' + c.army + ' units' : ''}</span>
      ${bad ? `<span class="w-bad">${bad}</span>` : ''}
      ${warn ? `<span class="w-warn">${warn}</span>` : ''}
    </div>`;
  }).join('');
  return `<div class="cxlist">${rows || '<div class="count">Nobody.</div>'}</div>
    ${(d.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`).join('')}
    <div class="csbtns">
      <button onclick="cxAdd()">+ Add a character</button>
    </div>
    ${k.w ? cxFormHtml() : ''}`;
}

function cxFormHtml(){
  const k = state.cx, w = k.w, v = k.d.vocab;
  const list = (slot, values) => `<datalist id="cxl-${slot}">${
    (values || []).map(x => `<option value="${esc(x)}">`).join('')}</datalist>`;
  return `<div class="cxform">
    <div class="cshead"><b>${k.adding ? 'A new character'
      : esc(k.d.characters[k.pick].name)}</b>
      ${k.adding ? '' : `<span class="count">lines
        ${k.d.characters[k.pick].lines[0]}-${k.d.characters[k.pick].lines[1]}</span>`}
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Name</label>
        <input value="${esc(w.name)}" oninput="cxSet('name', this.value)"></div>
      <div class="cmfield"><label>Type</label>
        <select onchange="cxSet('type', this.value)">
          ${v.types.map(t => `<option value="${esc(t)}"${
            t === w.type ? ' selected' : ''}>${esc(t)}</option>`).join('')}
        </select></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Sex</label>
        <select onchange="cxSet('gender', this.value)">
          ${['male', 'female'].map(g => `<option value="${g}"${
            g === w.gender ? ' selected' : ''}>${g}</option>`).join('')}
        </select></div>
      <div class="cmfield"><label>Rank</label>
        <select onchange="cxSet('rank', this.value)">
          <option value=""${w.rank ? '' : ' selected'}>neither</option>
          ${v.ranks.map(r => `<option value="${r}"${
            r === w.rank ? ' selected' : ''}>${r}</option>`).join('')}
        </select>
        ${k.d.leader && w.rank === 'leader' && (k.adding
          || k.d.characters[k.pick].name !== k.d.leader)
          ? `<div class="count">${esc(k.d.leader)} is the leader today.</div>` : ''}
      </div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Age</label>
        <input type="number" value="${esc(w.age)}" min="0"
          oninput="cxSet('age', this.value)"></div>
      <div class="cmfield"><label>Where <span class="count">game x, y</span></label>
        <div class="cxxy">
          <input type="number" value="${esc(w.x)}" oninput="cxSet('x', this.value)">
          <input type="number" value="${esc(w.y)}" oninput="cxSet('y', this.value)">
          <button onclick="cxHere()" title="Put them on the tile the map is looking at"
            >Here</button>
          ${cpinButton(`${w.name || 'the new character'}'s tile`, 'cxPinned')}
        </div></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Portrait</label>
        <input list="cxl-portrait" value="${esc(w.tail.portrait || '')}"
          oninput="cxTail('portrait', this.value)">${list('portrait', v.portraits)}</div>
      <div class="cmfield"><label>Hero ability</label>
        <input list="cxl-ability" value="${esc(w.tail.hero_ability || '')}"
          oninput="cxTail('hero_ability', this.value)">${list('ability', v.abilities)}
        <div class="count">No file on disk declares these; the list is what this
        campaign already uses.</div></div>
    </div>
    ${cxTraitsHtml()}
    ${cxArmyHtml()}
    ${cxFindingsHtml()}
    <div class="csbtns">
      <button class="primary" onclick="cxSave()">${k.adding
        ? 'Add character' : 'Save character'}</button>
      ${k.adding ? `<button onclick="cxCancel()">Cancel</button>`
        : `<button onclick="cxSave('move')">Move…</button>
           <button onclick="cxSave('delete')">Delete</button>
           <button onclick="cxPick(-1)">Close</button>`}
    </div>
  </div>`;
}

/* Traits and ancillaries.

   The level box is a number and the picker knows how many levels the trait
   has, because the server sent that with the trait. Whether the number is too
   high is still the server's to say - it says so in the findings below. */
function cxTraitsHtml(){
  const k = state.cx, w = k.w, v = k.d.vocab;
  const known = {};
  for(const t of v.traits) known[t.name] = t.levels;
  const rows = w.traits.map((t, i) => `<div class="cxbit">
    <input list="cxl-trait" value="${esc(t.name)}"
      oninput="cxTrait(${i}, 'name', this.value)">
    <input type="number" min="1" value="${esc(t.level)}"
      oninput="cxTrait(${i}, 'level', this.value)">
    ${known[t.name] ? `<span class="count">of ${known[t.name]}</span>` : ''}
    <button onclick="cxTraitDrop(${i})" title="Take this trait off">✕</button>
  </div>`).join('');
  const ancs = w.ancillaries.map((a, i) => `<span class="cxtag">${esc(a)}
    <button onclick="cxAncDrop(${i})">✕</button></span>`).join('');
  return `<div class="k">Traits <span class="count">${w.traits.length}${
      v.have_edct ? '' : ' · no export_descr_character_traits.txt on disk'}</span></div>
    <div class="cxbits">${rows || '<div class="count">None.</div>'}</div>
    <datalist id="cxl-trait">${v.traits.map(t =>
      `<option value="${esc(t.name)}">${t.levels} levels</option>`).join('')}</datalist>
    <div class="csadd"><select onchange="cxTraitAdd(this.value); this.value=''">
      <option value="">add a trait…</option>
      ${v.traits.map(t => `<option value="${esc(t.name)}">${esc(t.name)}</option>`)
        .join('')}</select></div>
    <div class="k">Ancillaries <span class="count">${w.ancillaries.length}</span></div>
    <div class="cxtags">${ancs || '<span class="count">None.</span>'}</div>
    <div class="csadd"><select onchange="cxAncAdd(this.value); this.value=''">
      <option value="">add an ancillary…</option>
      ${v.ancillaries.map(a => `<option value="${esc(a)}">${esc(a)}</option>`)
        .join('')}</select></div>`;
}

/* The army, in the order the block writes it.

   A bodyguard is marked in the list rather than sorted to the top: which unit
   leads is the modder's decision, and whether it should be a bodyguard is a
   sentence the server writes underneath. */
function cxArmyHtml(){
  const k = state.cx, w = k.w, v = k.d.vocab;
  const guard = new Set(v.bodyguards || []);
  const rows = w.army.map((a, i) => `<div class="cxbld">
    <select onchange="cxUnit(${i}, 'unit', this.value)">
      ${v.units.map(u => `<option value="${esc(u.name)}"${
        u.name === a.unit ? ' selected' : ''}>${esc(u.name)}${
        u.general ? ' ★' : ''}</option>`).join('')}
      ${v.units.some(u => u.name === a.unit) ? ''
        : `<option value="${esc(a.unit)}" selected>${esc(a.unit)}</option>`}
    </select>
    <input type="number" min="0" max="9" value="${a.exp}" title="Experience"
      oninput="cxUnit(${i}, 'exp', this.value)">
    <input type="number" min="0" value="${a.armour}" title="Armour upgrade"
      oninput="cxUnit(${i}, 'armour', this.value)">
    <input type="number" min="0" value="${a.weapon_lvl}" title="Weapon upgrade"
      oninput="cxUnit(${i}, 'weapon_lvl', this.value)">
    <button onclick="cxUnitMove(${i}, -1)" title="Move up">↑</button>
    <button onclick="cxUnitMove(${i}, 1)" title="Move down">↓</button>
    <button onclick="cxUnitDrop(${i})" title="Take this regiment out">✕</button>
    ${i === 0 && guard.size ? `<span class="count csnote">${
      guard.has(a.unit) ? 'the bodyguard, in front' : 'leads this army'}</span>` : ''}
  </div>`).join('');
  return `<div class="k">Army <span class="count">${w.army.length} regiment${
      w.army.length === 1 ? '' : 's'}${v.have_edu ? ' · ★ is a bodyguard'
      : ' · no export_descr_unit.txt on disk, so these are the names this'
        + ' campaign itself writes'}</span></div>
    <div class="cxblds">${rows || '<div class="count">No army.</div>'}</div>
    <div class="csadd"><select onchange="cxUnitAdd(this.value); this.value=''">
      <option value="">add a regiment…</option>
      ${(v.units || []).map(u => `<option value="${esc(u.name)}">${esc(u.name)}${
        u.general ? ' ★' : ''}</option>`).join('')}</select></div>`;
}

function cxFindingsHtml(){
  const k = state.cx, p = k.preview;
  const findings = p ? (p.findings || [])
    : (k.pick >= 0 ? k.d.characters[k.pick].findings || [] : []);
  const errors = (p ? (p.errors || []) : []).filter(e => e !== 'nothing to change');
  const said = findings.map(f => f.message);
  const changes = p ? (p.changes || []) : [];
  return `<div class="csfind">
    ${errors.filter(e => !said.includes(e))
      .map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${findings.map(f => `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${
      esc(f.message)}${cxPoolFixHtml(f)}${cxNearHtml(f)}</div>`).join('')}
    ${changes.length ? `<div class="count">Would change:
      ${changes.map(esc).join(' · ')}</div>`
      : p ? '<div class="count">Nothing to save yet.</div>' : ''}
  </div>`;
}

/* 22b, D10: a character on the wrong side of the shore is told the nearest tile
   on the right one, and this is the button that puts it there - the numbers
   change and the plan is asked again, so nothing is written until Save. */
function cxNearHtml(f){
  if(!f.near || !state.cx || !state.cx.w) return '';
  return ` <button class="cxfix" onclick="cxNear(${+f.near[0]}, ${+f.near[1]})"
    title="Put the two numbers in the form and ask the plan again. Nothing is written until Save.">⌖ Move to ${+f.near[0]},${+f.near[1]}</button>`;
}

function cxNear(x, y){
  const k = state.cx;
  if(!k || !k.w) return;
  k.w.x = x; k.w.y = y;
  cxPlanSoon();
  cxPaint();
}

/* ---- 19a, D5: the two findings that now have a button ----

   `char.pool` says the name is in no pool and `char.name_key` says it is in one
   but has no line in text/names.txt. Both are "the record exists and the words
   the player reads for it do not", and one write closes either - so the button
   sits on the finding rather than in a screen of its own, which is where
   somebody actually meets the problem.

   It writes descr_names.txt and text/names.txt together and it is its own save:
   nothing about the character block is touched, and the 🕑 Log entry names the
   two files it put there. */
function cxPoolFixHtml(f){
  if(f.code !== 'char.pool' && f.code !== 'char.name_key') return '';
  if(!f.part) return '';
  return ` <button class="cxfix" onclick="cxPoolAdd('${esc(f.part)}')"
    title="Put this name in the faction's pool and give it a key in text/names.txt. Its own save, and its own undo.">Add to pool</button>`;
}

async function cxPoolAdd(part){
  const k = state.cx;
  if(!k || !k.d || k.busy) return;
  const name = (k.w && k.w.name) || (k.pick >= 0 ? k.d.characters[k.pick].name : '');
  const gender = (k.w && k.w.gender) || 'male';
  const shown = prompt(`What should the player read for "${part}"?\n\n`
    + 'This is the value of its key in text/names.txt. Leave it as it is to use '
    + 'the token with its underscores turned into spaces.',
    part.replace(/_/g, ' '));
  if(shown === null) return;
  const body = {mod: k.mod, what: 'name_pool', faction: k.faction,
                name, gender, edits: {[part]: shown}};
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/namekeys/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write: ${(p.changes || []).join('\n') || 'no visible change'}?\n\n`
    + ((p.warnings || []).length ? (p.warnings || []).slice(0, 3).join('\n') + '\n\n' : '')
    + `${(p.files || []).join(', ')} only - the character block is not touched.\n\n`
    + 'Backed up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/namekeys/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(`${part} is in ${k.faction}'s pool. 🕑 Log can undo it.`);
  activity('character', `${k.mod} ${k.faction}: pool + ${part}`);
  // re-read the faction so the finding this button just fixed goes away, then
  // put the same person back under the cursor: a save that closed the form
  // would make fixing two names take two trips through the list
  const faction = k.faction, was = k.adding ? null : name, form = k.w;
  k.d = null;
  await cxOpen(faction);
  const now = state.cx;
  if(!now || !now.d) return;
  if(was){
    const at = now.d.characters.findIndex(c => c.name === was);
    if(at >= 0) cxPick(at);
  }else if(form){
    now.adding = true; now.pick = -1; now.w = form;
    cxPaint();
    cxPlanSoon();
  }
}

/* The family tree, read only for now.

   The relative lines and the off-map records are shown with what is wrong with
   them, which is what 16i's exit criterion needs and what somebody fixing a
   family actually reads. Editing a relative line is 16j's neighbour and is not
   claimed here. */
function cxFamilyHtml(){
  const d = state.cx.d;
  const rel = (d.relatives || []).map(r => `<div class="cxfam">
    <span class="count">line ${r.line}</span>
    <b>${esc(r.names[0] || '')}</b> + ${esc(r.names[1] || '(nobody)')}
    ${r.names.length > 2 ? '&rarr; ' + r.names.slice(2).map(esc).join(', ') : ''}
  </div>`).join('');
  const rec = (d.records || []).map(r => `<div class="cxfam">
    <span class="count">line ${r.line}</span>
    <b>${esc(r.name)}</b>
    <span class="count">${esc(r.gender)} · age ${r.age} ·
      ${r.dead === null || r.dead === undefined ? 'alive' : 'dead ' + r.dead}${
      r.leadership ? ' · ' + esc(r.leadership) : ''}</span>
  </div>`).join('');
  return `<div class="k">Families <span class="count">${
      (d.relatives || []).length} relative line${
      (d.relatives || []).length === 1 ? '' : 's'}</span></div>
    <div class="cxfams">${rel || '<div class="count">None.</div>'}</div>
    <div class="k">Off the map <span class="count">${(d.records || []).length}
      character_record${(d.records || []).length === 1 ? '' : 's'} - the dead,
      the married-in and the never-seen the game needs to draw a family</span></div>
    <div class="cxfams">${rec || '<div class="count">None.</div>'}</div>
    ${(d.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`).join('')}`;
}
