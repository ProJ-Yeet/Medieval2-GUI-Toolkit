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
  if(name === 'horde') hzOpen();              // 72: read on first open
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
  if(!k || !k.w){ toast(tt('stratchar.the_character_form_was_closed_before'), 5000);
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
  const map = state.cmap, campaign = map && map.campaign;
  clearTimeout(k.timer);
  const what = action || (k.adding ? 'add' : 'edit');
  const body = cxBody(what);
  if(what === 'move'){
    const to = prompt(tt('stratchar.move_to_which_faction_list',{character:body.character,factions:k.d.vocab.factions.join(', ')}), '');
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
  const verb = {edit: tt('stratchar.verb_save'), add: tt('stratchar.verb_add'), delete: tt('stratchar.verb_delete'), move: tt('stratchar.verb_move')}[what];
  if(!confirm(tt('stratchar.write_in_faction_confirm',{verb,
    who:body.character || (k.w && k.w.name) || tt('stratchar.this_character'),faction:k.faction,
    changes:lines.join('\n') || tt('common.no_visible_change'),
    more:(p.changes || []).length > 14
       ? tt('stratchar.and_more',{changes:p.changes.length - 14}) : '',
    warnings:warn.length ? '\n\n' + warn.join('\n') : ''}))) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/character_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  activity('character', `${k.mod} ${k.faction}: ${what} ${res.name || ''}`);
  if(state.cmap !== map || !map || map.campaign !== campaign || state.cx !== k) return;
  // Only this faction and the object overlay changed. Keep the canvas,
  // camera, layers and active inspector intact.
  const open = k.open, tab = k.tab;
  k.d = null;
  await cxOpen(body.owner || k.faction);
  if(state.cmap !== map || map.campaign !== campaign) return;
  const fresh = state.cx;
  if(fresh && fresh.d){
    fresh.open = open; fresh.tab = tab;
    const name = res.name || (body.edits && body.edits.name) || body.character;
    const i = what === 'delete' ? -1 : fresh.d.characters.findIndex(ch => ch.name === name);
    cxPick(i);
  }
  if(state.cmk){
    state.cmk.d = null;
    await cmkLoad();
  }
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
      title="${ttA('stratchar.the_characters_armies_and_family_this')}"
      >${tt('stratchar.people',{open:k.open ? ' ✓' : ''})}</button>
    ${d ? `<span class="count">${ttN('stratchar.character_count',d.characters.length,{label:esc(d.label || d.faction),leader:d.leader ? ' · ' + esc(d.leader) : ''})}</span>` : ''}
    ${k.busy ? `<span class="count">${tt('common.working_2')}</span>` : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + `<div class="cxpanel count">${tt('stratchar.reading',{faction:esc(k.faction)})}</div>`;
  if(k.err) return head + `<div class="cxpanel w-warn">${esc(k.err)}</div>`;
  if(!d) return head;
  return head + `<div class="cxpanel">
    <div class="cqtabs">
      <button class="${k.tab === 'people' ? 'on' : ''}" onclick="cxTab('people')"
        >${tt('common.characters')}</button>
      <button class="${k.tab === 'family' ? 'on' : ''}" onclick="cxTab('family')"
        >${tt('stratchar.family_tree')}</button>
      <button class="${k.tab === 'horde' ? 'on' : ''}" onclick="cxTab('horde')"
        title="${ttA('stratchar.phase_72_fill_a_faction_that')}"
        >${tt('stratchar.horde_start')}</button>
    </div>
    ${k.tab === 'people' ? cxPeopleHtml() : k.tab === 'family' ? cxFamilyHtml()
      : hzHtml()}
    ${cxSkippedHtml()}
  </div>`;
}

function cxSkippedHtml(){
  const s = (state.cx.d.vocab.skipped || []).filter(x =>
    /descr_names|export_descr_(unit|character_traits|ancillaries)/.test(x.what));
  if(!s.length) return '';
  return `<div class="cqskip"><div class="k">${tt('stratchar.not_read')}</div>
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
      ${tt('stratchar.age',{type:esc(c.type),x:c.rank ? ' · ' + esc(c.rank) : '',age:c.age,x2:c.x,x3:c.y,x4:c.army ? ' · ' + c.army + ' units' : '',bad:bad ? `<span class="w-bad">${bad}</span>` : '',warn:warn ? `<span class="w-warn">${warn}</span>` : ''})}
    </div>`;
  }).join('');
  return `${k.w ? cxFormHtml() : ''}
    <details class="cxcharacters"${k.w ? '' : ' open'}><summary>${k.w ? tt('stratchar.switch_character') : tt('common.characters')} · ${d.characters.length}</summary>
    <div class="cxlist">${rows || `<div class="count">${tt('stratchar.nobody')}</div>`}</div></details>
    ${(d.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`).join('')}
    <div class="csbtns">
      <button onclick="cxAdd()">${tt('stratchar.add_a_character')}</button>
      ${d.characters.length ? '' : `<button onclick="cxTab('horde')"
        title="${ttA('stratchar.leaders_and_armies_on_free_land')}"
        >${tt('stratchar.give_it_a_horde_start')}</button>`}
    </div>`;
}

function cxFormHtml(){
  const k = state.cx, w = k.w, v = k.d.vocab;
  const list = (slot, values) => `<datalist id="cxl-${slot}">${
    (values || []).map(x => `<option value="${esc(x)}">`).join('')}</datalist>`;
  return `<div class="cxform">
    <div class="csbtns cxsectionnav">
      <button onclick="cxSection('cxCharacterFields')">${tt('stratchar.character_2')}</button>
      <button onclick="cxSection('cxTraitsEditor')">${tt('stratchar.traits_items')}</button>
      <button onclick="cxSection('cxArmyEditor')">${tt('stratchar.army',{army_n:w.army.length})}</button>
    </div>
    <div class="cshead" id="cxCharacterFields"><b>${k.adding ? tt('stratchar.a_new_character')
      : esc(k.d.characters[k.pick].name)}</b>
      ${k.adding ? '' : `<span class="count">${tt('stratchar.lines',{x:k.d.characters[k.pick].lines[0],x2:k.d.characters[k.pick].lines[1]})}</span>`}
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>${tt('common.name')}</label>
        <input value="${esc(w.name)}" oninput="cxSet('name', this.value)"></div>
      <div class="cmfield"><label>${tt('common.type')}</label>
        <select onchange="cxSet('type', this.value)">
          ${v.types.map(t => `<option value="${esc(t)}"${
            t === w.type ? ' selected' : ''}>${esc(t)}</option>`).join('')}
        </select></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>${tt('stratchar.sex')}</label>
        <select onchange="cxSet('gender', this.value)">
          ${['male', 'female'].map(g => `<option value="${g}"${
            g === w.gender ? ' selected' : ''}>${g}</option>`).join('')}
        </select></div>
      <div class="cmfield"><label>${tt('stratchar.rank')}</label>
        <select onchange="cxSet('rank', this.value)">
          <option value=""${w.rank ? '' : ' selected'}>${tt('stratchar.neither')}</option>
          ${v.ranks.map(r => `<option value="${r}"${
            r === w.rank ? ' selected' : ''}>${r}</option>`).join('')}
        </select>
        ${k.d.leader && w.rank === 'leader' && (k.adding
          || k.d.characters[k.pick].name !== k.d.leader)
          ? `<div class="count">${tt('stratchar.is_the_leader_today',{leader:esc(k.d.leader)})}</div>` : ''}
      </div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>${tt('stratchar.age_2')}</label>
        <input type="number" value="${esc(w.age)}" min="0"
          oninput="cxSet('age', this.value)"></div>
      <div class="cmfield"><label>${tt('stratchar.where_game_x_y')}</label>
        <div class="cxxy">
          <input type="number" value="${esc(w.x)}" oninput="cxSet('x', this.value)">
          <input type="number" value="${esc(w.y)}" oninput="cxSet('y', this.value)">
          <button onclick="cxHere()" title="${ttA('stratchar.put_them_on_the_tile_the')}"
            >${tt('stratchar.here')}</button>
          ${cpinButton(tt('stratchar.s_tile',{name:w.name || tt('stratchar.the_new_character')}), 'cxPinned')}
        </div></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>${tt('stratchar.portrait')}</label>
        <input list="cxl-portrait" value="${esc(w.tail.portrait || '')}"
          oninput="cxTail('portrait', this.value)">${list('portrait', v.portraits)}</div>
      <div class="cmfield"><label>${tt('stratchar.hero_ability')}</label>
        <input list="cxl-ability" value="${esc(w.tail.hero_ability || '')}"
          oninput="cxTail('hero_ability', this.value)">${list('ability', v.abilities)}
        <div class="count">${v.have_abilities
          ? (w.tail.hero_ability && (v.declared_abilities || []).includes(String(w.tail.hero_ability).toLowerCase())
            ? navLinkHtml({mode: 'heroabilities', name: 'name/' + w.tail.hero_ability}, tt('stratchar.what_it_does'), 'ulink',
                tt('stratchar.open_it_in_hero_abilities_middle'))
            : tt('stratchar.the_list_is_what_descr_hero'))
          : tt('stratchar.this_mod_has_no_descr_hero')}</div></div>
    </div>
    ${cxTraitsHtml()}
    ${cxArmyHtml()}
    ${cxFindingsHtml()}
    <div class="csbtns">
      <button class="primary" onclick="cxSave()">${k.adding
        ? tt('stratchar.add_character') : tt('stratchar.save_character')}</button>
      ${k.adding ? `<button onclick="cxCancel()">${tt('common.cancel')}</button>`
        : `<button onclick="cxSave('move')">${tt('stratchar.move')}</button>
           <button onclick="cxSave('delete')">${tt('common.delete')}</button>
           <button onclick="cxPick(-1)">${tt('common.close')}</button>`}
    </div>
  </div>`;
}

/* Traits and ancillaries.

   The level box is a number and the picker knows how many levels the trait
   has, because the server sent that with the trait. Whether the number is too
   high is still the server's to say - it says so in the findings below. */
function cxSection(id){
  const el = document.getElementById(id);
  if(el) el.scrollIntoView({block:'start',behavior:'smooth'});
}

function cxTraitsHtml(){
  const k = state.cx, w = k.w, v = k.d.vocab;
  const known = {};
  for(const t of v.traits) known[t.name] = t.levels;
  const rows = w.traits.map((t, i) => `<div class="cxbit">
    <input list="cxl-trait" value="${esc(t.name)}"
      oninput="cxTrait(${i}, 'name', this.value)">
    <input type="number" min="1" value="${esc(t.level)}"
      oninput="cxTrait(${i}, 'level', this.value)">
    ${known[t.name] ? `<span class="count">${tt('stratchar.of',{x:known[t.name]})}</span>` : ''}
    <button onclick="cxTraitDrop(${i})" title="${ttA('stratchar.take_this_trait_off')}">✕</button>
  </div>`).join('');
  const ancs = w.ancillaries.map((a, i) => `<span class="cxtag">${esc(a)}
    <button onclick="cxAncDrop(${i})">✕</button></span>`).join('');
  return `<div class="k" id="cxTraitsEditor">${tt('common.traits')} <span class="count">${w.traits.length}${
      v.have_edct ? '' : tt('stratchar.no_export_descr_character_traits_txt')}</span></div>
    <div class="cxbits">${rows || `<div class="count">${tt('common.none_3')}</div>`}</div>
    <datalist id="cxl-trait">${v.traits.map(t =>
      `<option value="${esc(t.name)}">${tt('stratchar.levels',{levels:t.levels})}</option>`).join('')}</datalist>
    <div class="csadd"><select onchange="cxTraitAdd(this.value); this.value=''">
      <option value="">${tt('stratchar.add_a_trait')}</option>
      ${v.traits.map(t => `<option value="${esc(t.name)}">${esc(t.name)}</option>`)
        .join('')}</select></div>
    <div class="k">${tt('common.ancillaries')} <span class="count">${w.ancillaries.length}</span></div>
    <div class="cxtags">${ancs || `<span class="count">${tt('common.none_3')}</span>`}</div>
    <div class="csadd"><select onchange="cxAncAdd(this.value); this.value=''">
      <option value="">${tt('stratchar.add_an_ancillary')}</option>
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
    <input type="number" min="0" max="9" value="${a.exp}" title="${ttA('common.experience')}"
      oninput="cxUnit(${i}, 'exp', this.value)">
    <input type="number" min="0" value="${a.armour}" title="${ttA('stratchar.armour_upgrade')}"
      oninput="cxUnit(${i}, 'armour', this.value)">
    <input type="number" min="0" value="${a.weapon_lvl}" title="${ttA('stratchar.weapon_upgrade')}"
      oninput="cxUnit(${i}, 'weapon_lvl', this.value)">
    <button onclick="cxUnitMove(${i}, -1)" title="${ttA('stratchar.move_up')}">↑</button>
    <button onclick="cxUnitMove(${i}, 1)" title="${ttA('stratchar.move_down')}">↓</button>
    <button onclick="cxUnitDrop(${i})" title="${ttA('stratchar.take_this_regiment_out')}">✕</button>
    ${i === 0 && guard.size ? `<span class="count csnote">${
      guard.has(a.unit) ? tt('stratchar.the_bodyguard_in_front') : tt('stratchar.leads_this_army')}</span>` : ''}
  </div>`).join('');
  return `<div class="k" id="cxArmyEditor">${ttN('stratchar.army_regiment_count',w.army.length,{have_edu:v.have_edu ? tt('stratchar.is_a_bodyguard')
      : tt('stratchar.no_export_descr_unit_names')})}</div>
    <div class="cxblds">${rows || `<div class="count">${tt('stratchar.no_army')}</div>`}</div>
    <div class="csadd"><select onchange="cxUnitAdd(this.value); this.value=''">
      <option value="">${tt('stratchar.add_a_regiment')}</option>
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
    ${changes.length ? `<div class="count">${tt('stratchar.would_change',{changes:changes.map(esc).join(' · ')})}</div>`
      : p ? `<div class="count">${tt('stratchar.nothing_to_save_yet')}</div>` : ''}
  </div>`;
}

/* 22b, D10: a character on the wrong side of the shore is told the nearest tile
   on the right one, and this is the button that puts it there - the numbers
   change and the plan is asked again, so nothing is written until Save. */
function cxNearHtml(f){
  if(!f.near || !state.cx || !state.cx.w) return '';
  return ` <button class="cxfix" onclick="cxNear(${+f.near[0]}, ${+f.near[1]})"
    title="${ttA('stratchar.put_the_two_numbers_in_the')}">${tt('stratchar.move_to',{x:+f.near[0],x2:+f.near[1]})}</button>`;
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
    title="${ttA('stratchar.put_this_name_in_the_factions')}">${tt('stratchar.add_to_pool')}</button>`;
}

async function cxPoolAdd(part){
  const k = state.cx;
  if(!k || !k.d || k.busy) return;
  const name = (k.w && k.w.name) || (k.pick >= 0 ? k.d.characters[k.pick].name : '');
  const gender = (k.w && k.w.gender) || 'male';
  const shown = prompt(tt('stratchar.what_should_the_player_read_for_prompt',{part}),
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
  if(!confirm(tt('stratchar.write_name_pool_confirm',{
    changes:(p.changes || []).join('\n') || tt('common.no_visible_change'),
    warnings:(p.warnings || []).length ? (p.warnings || []).slice(0, 3).join('\n') + '\n\n' : '',
    files:(p.files || []).join(', ')}))) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/namekeys/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('stratchar.is_in_s_pool_log_can',{part,faction:k.faction}));
  activity('character', tt('stratchar.pool',{mod:k.mod,faction:k.faction,part}));
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
    ${tt('stratchar.line',{line:r.line,names:esc(r.names[0] || ''),names2:esc(r.names[1] || tt('stratchar.nobody')),x:r.names.length > 2 ? '&rarr; ' + r.names.slice(2).map(esc).join(', ') : ''})}
  </div>`).join('');
  const rec = (d.records || []).map(r => `<div class="cxfam">
    ${tt('stratchar.line_age',{line:r.line,name:esc(r.name),gender:esc(r.gender),age:r.age,x:r.dead === null || r.dead === undefined ? tt('stratchar.alive') : tt('stratchar.dead_at',{dead:r.dead}),x2:r.leadership ? ' · ' + esc(r.leadership) : ''})}
  </div>`).join('');
  return `<div class="k">${ttN('stratchar.relative_line_count',(d.relatives || []).length)}</div>
    <div class="cxfams">${rel || `<div class="count">${tt('common.none_3')}</div>`}</div>
    <div class="k">${ttN('stratchar.character_record_count',(d.records || []).length)}</div>
    <div class="cxfams">${rec || `<div class="count">${tt('common.none_3')}</div>`}</div>
    ${(d.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`).join('')}`;
}
