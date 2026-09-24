/* hordestart.js - Campaign Map: a horde start for a faction that holds nothing

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE HORDE START TAB - Phase 72, D13.

   Every name here starts `hz`, and there was no `hz` name anywhere in the
   tree before this phase - checked, the way 16i checked `cx`.

   It is the People panel's third tab, because it is about one faction's
   people: 16j-2 makes a faction with nobody in it, and this is the tab that
   fills it. It lives in its own file only because the People panel was
   already seven hundred lines.

   PYTHON OWNS THE RULES. Which tiles are free land in the province, whose
   names the pool can spare, whether the trait file declares a starter, what
   the horde keys are when the faction has none: hordestart.py decides every
   one, and the form opens on a dry plan of each mode, so what it shows before
   a box is touched is exactly what a save would write. After that it asks on
   16i's 450 ms debounce, like every other form on this map.
   ===================================================================== */

const HZ_DEBOUNCE = 450;

async function hzOpen(force){
  const k = state.cx, c = state.cmap;
  if(!k || !c) return;
  if(k.hz && k.hz.v && !force){ cxPaint(); return; }
  const z = k.hz = {v: null, w: null, preview: null, busy: false, timer: 0,
                    loading: true, err: ''};
  cxPaint();
  let v;
  try{ v = await api.get(`/api/map/horde?mod=${enc(k.mod)}`
    + `&faction=${enc(k.faction)}${cmapCampQ()}`); }
  catch(e){ v = {error: errText(e)}; }
  if(state.cx !== k || k.hz !== z) return;
  z.loading = false;
  if(v.error){ z.err = v.error; cxPaint(); return; }
  z.v = v;
  hzFrom(v.defaults.start.ok || !v.defaults.emerge.ok ? 'start' : 'emerge');
  cxPaint();
}

//: The working copy, off the dry plan of a mode: what the server used when
//: nothing was sent is what the boxes start with.
function hzFrom(mode){
  const z = state.cx.hz, v = z.v, u = (v.defaults[mode] || {}).used || {};
  const was = z.w || {};
  const other = (v.defaults[mode === 'start' ? 'emerge' : 'start'] || {}).used || {};
  z.w = {mode,
         province: u.province || was.province || v.province || '',
         count: u.count || was.count || 3,
         family: u.family !== undefined ? u.family : true,
         exp: u.exp || 0,
         army: (u.army || was.army || other.army || []).slice(),
         names: '',
         date: u.date || was.date || '10 20',
         regions: (u.regions || was.regions || [v.province]).filter(Boolean),
         movie: u.movie || '',
         horde: Object.assign({}, u.horde || other.horde || {}),
         horde_units: (u.horde_units || other.horde_units || []).slice()};
  z.preview = v.defaults[mode] || null;
}

function hzMode(mode){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w || z.w.mode === mode) return;
  const keep = z.w;
  hzFrom(mode);
  // what somebody typed survives the switch; only the mode's own boxes reset
  for(const key of ['province', 'army', 'horde', 'horde_units'])
    z.w[key] = keep[key];
  hzPlanSoon();
  cxPaint();
}

//: `quiet` is for a box being typed in: repainting the panel under it would
//: take the caret away, so the plan's answer repaints it instead.
function hzSet(slot, value, quiet){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w) return;
  z.w[slot] = value;
  hzPlanSoon();
  if(!quiet) cxPaint();
}

function hzKey(key, value){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w) return;
  z.w.horde[key] = value;
  hzPlanSoon();
}

function hzListAdd(slot, value){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w || !value) return;
  const cap = slot === 'army' ? z.v.limits.stack : 99;
  if(z.w[slot].length >= cap){ toast(`A stack holds ${cap} regiments.`, 4000); return; }
  if(slot !== 'army' && z.w[slot].includes(value)) return;
  z.w[slot].push(value);
  hzPlanSoon();
  cxPaint();
}

function hzListDrop(slot, i){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w) return;
  z.w[slot].splice(i, 1);
  hzPlanSoon();
  cxPaint();
}

function hzBody(){
  const k = state.cx, z = k.hz, w = z.w;
  const body = {mod: k.mod, campaign: z.v.campaign, faction: k.faction,
                mode: w.mode, horde: w.horde, horde_units: w.horde_units};
  if(w.mode === 'start'){
    Object.assign(body, {province: w.province, count: +w.count,
                         family: !!w.family, exp: +w.exp || 0,
                         army: w.army.map(unit => ({unit}))});
    const names = String(w.names || '').split(',').map(s => s.trim()).filter(Boolean);
    if(names.length) body.names = names;
  }else{
    Object.assign(body, {date: w.date, regions: w.regions, movie: w.movie});
  }
  return body;
}

function hzPlanSoon(){
  const z = state.cx && state.cx.hz;
  if(!z || !z.w) return;
  clearTimeout(z.timer);
  const k = state.cx;
  z.timer = setTimeout(() => hzPlanNow(k, z), HZ_DEBOUNCE);
}

async function hzPlanNow(k, z){
  if(state.cx !== k || k.hz !== z || !z.w) return;
  let res;
  try{ res = await api.post('/api/map/horde_plan', hzBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.cx !== k || k.hz !== z) return;
  z.preview = res.plan || null;
  hzPaintKeepingFocus();
}

function hzPaintKeepingFocus(){
  const el = document.activeElement;
  const at = el && el.closest && el.closest('#cmChars') && el.getAttribute('oninput');
  const caret = at && el.selectionStart;
  cxPaint();
  if(!at) return;
  const again = [...document.querySelectorAll('#cmChars [oninput]')]
    .find(x => x.getAttribute('oninput') === at);
  if(again){ again.focus(); try{ again.setSelectionRange(caret, caret); }catch(e){} }
}

async function hzSave(){
  const k = state.cx, z = k && k.hz;
  if(!z || !z.w || z.busy) return;
  const map = state.cmap, campaign = map && map.campaign;
  clearTimeout(z.timer);
  const body = hzBody();
  z.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/horde_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ z.busy = false; }
  z.preview = plan.plan || null;
  cxPaint();
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 16);
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  if(!confirm(`Write a horde start for ${k.faction}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 16 ? `\n…and ${p.changes.length - 16} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + `\n\nFiles: ${(p.files || []).join(', ')}. Backed up first, and 🕑 Log`
    + ' undoes all of them at once.')) return;
  z.busy = true;
  let res;
  try{ res = await api.post('/api/map/horde_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ z.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Horde start written. 🕑 Log can undo it.');
  activity('horde', `${k.mod} ${k.faction}: ${body.mode} (${(res.files || []).length} files)`);
  if(state.cmap !== map || !map || map.campaign !== campaign || state.cx !== k) return;
  const open = k.open;
  k.d = null;
  await cxOpen(k.faction);
  const fresh = state.cx;
  if(fresh && fresh.d){
    fresh.open = open;
    fresh.tab = body.mode === 'start' ? 'people' : 'horde';
    if(fresh.tab === 'horde') await hzOpen(true);
    else cxPaint();
  }
  if(state.cmk){ state.cmk.d = null; await cmkLoad(); }
}

//: The map's view of a game tile, the flip every other panel makes.
function hzGo(x, y){
  const c = state.cmap;
  if(!c) return;
  cmapGoTile([+x, c.man.height - 1 - +y], 8);
}

/* ---------- drawing ---------- */

function hzHtml(){
  const k = state.cx, z = k.hz;
  if(!z || z.loading) return '<div class="count">reading the faction…</div>';
  if(z.err) return `<div class="w-warn">${esc(z.err)}</div>`;
  const v = z.v, w = z.w;
  if(!v.empty){
    const held = [];
    if(v.holds.settlements) held.push(`${v.holds.settlements} settlement${v.holds.settlements === 1 ? '' : 's'}`);
    if(v.holds.characters) held.push(`${v.holds.characters} character${v.holds.characters === 1 ? '' : 's'}`);
    return `<div class="count">${esc(v.label || v.faction)} holds ${held.join(' and ')}.
      A horde start fills a faction that holds nothing - the shape a new faction
      has after <b>New faction</b> in the Campaign panel, and vanilla's Mongols
      before they arrive.</div>
      ${v.events.length ? hzEventsHtml(v) : ''}`;
  }
  const mode = (id, label, note) => `<label class="hzmode${w.mode === id ? ' on' : ''}">
    <input type="radio" name="hzmode" ${w.mode === id ? 'checked' : ''}
      onchange="hzMode('${id}')"> <b>${label}</b>
    <span class="count">${note}</span></label>`;
  return `<div class="cxform">
    <div class="count">${esc(v.label || v.faction)} holds nothing yet. Give it a
      start as a horde: no city, only armies.</div>
    ${mode('start', 'On the map from turn one',
      'named characters leading armies on free land in one province, and a family line')}
    ${mode('emerge', 'Arrives later, as vanilla’s Mongols do',
      'dead until an <code>emergent_faction</code> event raises its horde')}
    ${w.mode === 'start' ? hzStartHtml() : hzEmergeHtml()}
    ${hzHordeHtml()}
    ${hzPreviewHtml()}
    <div class="csbtns">
      <button class="primary" onclick="hzSave()" ${z.busy ? 'disabled' : ''}
        >Write horde start</button>
    </div>
    ${v.events.length ? hzEventsHtml(v) : ''}
  </div>`;
}

function hzProvinceOptions(chosen){
  const v = state.cx.hz.v;
  return v.provinces.map(p => {
    const who = v.owners[p.toLowerCase()];
    return `<option value="${esc(p)}"${p === chosen ? ' selected' : ''}>${esc(p)}${
      who ? ' · ' + esc(who) : ''}</option>`;
  }).join('');
}

function hzStartHtml(){
  const z = state.cx.hz, v = z.v, w = z.w;
  const units = v.units || [];
  const army = w.army.map((u, i) => `<span class="cxtag">${esc(u)}${
    units.some(x => x.name === u && x.general) ? ' ★' : ''}
    <button onclick="hzListDrop('army', ${i})" title="Take this regiment out">✕</button></span>`).join('');
  return `<div class="csrow2">
      <div class="cmfield"><label>Province</label>
        <select onchange="hzSet('province', this.value)">${hzProvinceOptions(w.province)}</select>
        <div class="count">the armies stand on free land in it, nearest its settlement</div></div>
      <div class="cmfield"><label>People</label>
        <input type="number" min="1" max="${v.limits.people}" value="${esc(w.count)}"
          oninput="hzSet('count', this.value, true)">
        <div class="count">1 to ${v.limits.people}: a leader, an heir, then named characters</div></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Experience</label>
        <input type="number" min="0" max="9" value="${esc(w.exp)}"
          oninput="hzSet('exp', this.value, true)">
        <div class="count">for every regiment</div></div>
      <div class="cmfield"><label><input type="checkbox" ${w.family ? 'checked' : ''}
          onchange="hzSet('family', this.checked)"> A family line</label>
        <div class="count">the leader, a wife out of the pool, and the heir as their son</div></div>
    </div>
    <div class="cmfield"><label>Names</label>
      <input value="${esc(w.names)}" oninput="hzSet('names', this.value, true)"
        placeholder="from descr_names.txt">
      <div class="count">optional, comma separated, leader first; the rest come out
        of the faction's pool (${v.pool.characters || 0} first names)</div></div>
    <div class="k">Each army <span class="count">${w.army.length} of ${v.limits.stack} regiments ·
      ★ is a bodyguard</span></div>
    <div class="cxtags">${army || '<span class="count">No regiment.</span>'}</div>
    <div class="csadd"><select onchange="hzListAdd('army', this.value); this.value=''">
      <option value="">add a regiment…</option>
      ${units.filter(u => u.category !== 'ship').map(u => `<option value="${esc(u.name)}">${
        esc(u.name)}${u.general ? ' ★' : ''}</option>`).join('')}</select>
      ${units.length ? '' : `<div class="count">${esc(v.faction)} owns no unit in
        export_descr_unit.txt yet; the Factions screen's clone gives it the donor's.</div>`}</div>`;
}

function hzEmergeHtml(){
  const z = state.cx.hz, w = z.w;
  const regions = w.regions.map((r, i) => `<span class="cxtag">${esc(r)}
    <button onclick="hzListDrop('regions', ${i})">✕</button></span>`).join('');
  return `<div class="csrow2">
      <div class="cmfield"><label>When</label>
        <input value="${esc(w.date)}" oninput="hzSet('date', this.value, true)">
        <div class="count">years after the start, or a pair to pick between</div></div>
      <div class="cmfield"><label>Movie</label>
        <input value="${esc(w.movie)}" placeholder="event/mongols_invade.bik"
          oninput="hzSet('movie', this.value, true)">
        <div class="count">optional</div></div>
    </div>
    <div class="k">Where it may appear <span class="count">vanilla's Mongols name four provinces</span></div>
    <div class="cxtags">${regions || '<span class="count">None.</span>'}</div>
    <div class="csadd"><select onchange="hzListAdd('regions', this.value); this.value=''">
      <option value="">add a province…</option>${hzProvinceOptions('')}</select></div>`;
}

//: The horde keys and the roster. Shown in both modes because both write them
//: when the faction has none; the Factions screen edits them after.
function hzHordeHtml(){
  const z = state.cx.hz, v = z.v, w = z.w;
  const used = ((z.preview || {}).used || {}).horde_from || '';
  const roster = w.horde_units.map((u, i) => `<span class="cxtag">${esc(u)}
    <button onclick="hzListDrop('horde_units', ${i})">✕</button></span>`).join('');
  return `<details class="hzhorde"${v.complete_horde ? '' : ' open'}>
    <summary>Horde settings <span class="count">${v.complete_horde
      ? 'descr_sm_factions.txt already has them'
      : 'descr_sm_factions.txt has none - these are ' + (used === 'vanilla'
        ? 'vanilla’s' : esc(used) + '’s')}</span></summary>
    <div class="hzkeys">${v.horde_keys.map(key => `<div class="cmfield">
      <label>${esc(key.replace(/^horde_/, '').replace(/_/g, ' '))}</label>
      <input type="number" value="${esc(w.horde[key] || '')}"
        oninput="hzKey('${key}', this.value)"></div>`).join('')}</div>
    <div class="k">Horde units <span class="count">what the engine raises it from</span></div>
    <div class="cxtags">${roster || '<span class="count">None.</span>'}</div>
    <div class="csadd"><select onchange="hzListAdd('horde_units', this.value); this.value=''">
      <option value="">add a horde unit…</option>
      ${(v.units || []).filter(u => !u.general && u.category !== 'ship').map(u =>
        `<option value="${esc(u.name)}">${esc(u.name)}</option>`).join('')}</select></div>
  </details>`;
}

function hzPreviewHtml(){
  const p = state.cx.hz.preview;
  if(!p) return '';
  const said = (p.findings || []).map(f => f.message);
  const errors = (p.errors || []).filter(e => e !== 'nothing to change' && !said.includes(e));
  const people = (p.people || []).map(q => `<div class="cxrow" onclick="hzGo(${+q.x}, ${+q.y})"
    title="Show this tile on the map"><b>${esc(q.name)}</b>
    <span class="count">${q.rank ? esc(q.rank) + ' · ' : ''}age ${q.age} · ${q.x},${q.y}</span></div>`).join('');
  return `<div class="csfind">
    ${errors.map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${(p.findings || []).map(f => `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${
      f.who ? `<b>${esc(f.who)}</b>: ` : ''}${esc(f.message)}</div>`).join('')}
    ${(p.warnings || []).filter(x => !said.includes(x)).map(x =>
      `<div class="w-warn">${esc(x)}</div>`).join('')}
    ${people ? `<div class="k">Who it writes</div><div class="cxlist">${people}</div>` : ''}
    ${(p.files || []).length ? `<div class="count">Writes ${(p.files || []).map(esc).join(', ')}</div>` : ''}
  </div>`;
}

function hzEventsHtml(v){
  return `<div class="k">Its emergent_faction events</div>
    ${v.events.map(e => `<div class="count">line ${e.line}: date ${esc(e.dates.join(' / '))}${
      e.regions.length ? ' · ' + e.regions.map(esc).join(', ') : ''}</div>`).join('')}`;
}
