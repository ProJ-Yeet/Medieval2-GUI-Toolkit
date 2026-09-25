/* mapsize.js - Campaign Map: resizing the map (Phase 26a)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   SIZE - Phase 26a, G6: Geomod's "add surface area".

   Every name here starts `msz`. It is a sub-tab of Map. Four boxes, one per
   edge, in tiles: positive adds, negative takes away. The plan is Python's
   (unittransfer/mapresize.py) and says everything a resize does before it
   does it - every layer's new size, how many coordinates move in which file,
   and, for a shrink, every settlement, character and resource the smaller map
   would leave standing nowhere. Nothing is written until Resize, and one Undo
   in the Log takes it all back.

   WHY WEST AND SOUTH ARE THE ONES THAT MATTER. The game counts x from the west
   edge and y from the south edge, so only those two margins move a
   coordinate. The panel says so next to the boxes, because it is the answer to
   "why did adding to the north change nothing in descr_strat.txt".
   ===================================================================== */

function mszNew(mod){
  return {mod, open: false, m: {north: 0, south: 0, west: 0, east: 0},
          plan: null, busy: false, err: ''};
}

function mszOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.msz || state.msz.mod !== c.mod) state.msz = mszNew(c.mod);
  mszPaint();
}

function mszToggle(){
  const k = state.msz;
  if(!k) return;
  k.open = !k.open;
  mszPaint();
}

function mszSet(side, value){
  const k = state.msz;
  if(!k) return;
  const n = parseInt(value, 10);
  k.m[side] = Number.isFinite(n) ? n : 0;
  k.plan = null;                  // it was worked out for different margins
  mszPaint();
}

function mszBody(){
  const k = state.msz, c = state.cmap;
  return Object.assign({mod: c.mod, campaign: c.campaign || ''}, k.m);
}

async function mszPlan(){
  const k = state.msz;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.plan = null;
  mszPaint();
  let r;
  try{ r = await api.post('/api/map/resize_plan', mszBody(),
                          {label: 'working out the resize'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(state.msz !== k) return;
  k.plan = r.plan || null;
  if(!k.plan) k.err = r.error || 'the plan came back empty';
  mszPaint();
}

async function mszApply(){
  const k = state.msz;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(`Resize the map from ${p.old.join('x')} to ${p.new.join('x')}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + '\n\nOne backup set; 🕑 Log can undo it.')) return;
  k.busy = true;
  mszPaint();
  let r;
  try{ r = await api.post('/api/map/resize_apply', mszBody(),
                          {label: 'resizing the map'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!r || r.error){
    k.err = (r && r.error) || 'the resize failed';
    mszPaint();
    return;
  }
  toast(`The map is ${r.new.join('x')} now: ${r.files.length} file(s) written. `
    + '🕑 Log can undo it.', 7000);
  activity('map resize', `${k.mod}: ${r.old.join('x')} -> ${r.new.join('x')}, id ${r.id}`);
  k.plan = null; k.m = {north: 0, south: 0, west: 0, east: 0};
  // every layer changed size, so the screen is a different map
  if(typeof loadCampmap === 'function') loadCampmap();
}

function mszPaint(){
  const el = document.getElementById('cmSize');
  if(!el) return;
  el.innerHTML = mszHtml();
}

function mszHtml(){
  const k = state.msz, c = state.cmap;
  if(!k || !c || !c.man) return '';
  const head = `<div class="cmrow cmhdr" onclick="mszToggle()">
      <b>Resize</b> <span class="count">${c.man.width}x${c.man.height} tiles</span>
      <span class="count">${k.open ? '▾' : '▸'}</span>
    </div>`;
  if(!k.open) return head + (typeof mnwHtml === 'function' ? mnwHtml() : '');
  const m = k.m;
  const box = side => `<label class="mszbox">${side}
      <input type="number" step="1" value="${m[side]}"
        onchange="mszSet('${side}',this.value)"></label>`;
  const nw = c.man.width + m.west + m.east, nh = c.man.height + m.north + m.south;
  const p = k.plan;
  const off = p && p.off ? Object.entries(p.off) : [];
  return `${head}
    <div class="bsec">
      <div class="mszgrid">
        <div></div>${box('north')}<div></div>
        ${box('west')}<div class="mszmid">${c.man.width}x${c.man.height}<br>→ <b>${nw}x${nh}</b></div>${box('east')}
        <div></div>${box('south')}<div></div>
      </div>
      <div class="count">Tiles to add on each edge; a negative number takes that many away. New
        ground is the map's own sea. The game counts from the west and south edges, so only those
        two move the coordinates in descr_strat.txt, the scripts, the events and the battles.</div>
      <div class="cmbar2">
        <button onclick="mszPlan()" ${k.busy ? 'disabled' : ''}>${k.busy ? 'Working…' : 'Plan'}</button>
        <button class="primary" onclick="mszApply()" ${p && p.ok && !k.busy ? '' : 'disabled'}>Resize</button>
      </div>
      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${p ? `<div class="mszplan">
        ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
        ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
        ${(p.errors || []).map(x => `<div class="w-bad">${esc(x)}</div>`).join('')}
        ${off.length ? `<div class="mszoff">${off.map(([f, rows]) => `
          <div><b>${esc(f)}</b></div>
          ${rows.map(([ln, t]) => `<div class="count">${ln ? `line ${ln}: ` : ''}${esc(t)}</div>`).join('')}`
          ).join('')}${p.off_total > off.reduce((a, [, r]) => a + r.length, 0)
            ? `<div class="count">and ${p.off_total - off.reduce((a, [, r]) => a + r.length, 0)} more</div>` : ''}
        </div>` : ''}
      </div>` : ''}
    </div>
    ${typeof mnwHtml === 'function' ? mnwHtml() : ''}`;
}

/* =====================================================================
   A NEW MAP - Phase 26b, the TWCenter tutorial's "mapping from scratch".

   Every name here starts `mnw`. Under the resize on the same sub-tab, because
   both are "how big is the map", and closed until opened. A new map is a new
   campaign with the map in its own folder (unittransfer/mapnew.py): the base
   map and every campaign reading it are left alone. The form asks for what the
   tutorial's first page decides - the size, how many provinces, whose - and
   the plan says the rest.
   ===================================================================== */

function mnwState(){
  const c = state.cmap;
  if(!c) return null;
  if(!state.mnw || state.mnw.mod !== c.mod)
    state.mnw = {mod: c.mod, open: false, d: null, loading: false, err: '',
                 f: {name: '', title: '', source: '', width: 160, height: 120,
                     provinces: 10, land: 0.55, climate: '', factions: [],
                     // 87e: the real world under a box, cities picked on the world map
                     shape: 'island', box: null, settlements: [], coast: true, lakes: false,
                     rivers: 'major', climates: 'ground', min_island: 4},
                 plan: null, busy: false};
  return state.mnw;
}

async function mnwToggle(){
  const k = mnwState();
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.d && !k.loading){
    k.loading = true; mszPaint();
    try{
      k.d = await api.get(`/api/mapnew?mod=${enc(k.mod)}`, {label: 'reading factions and climates'});
      k.f.source = ((k.d.sources || [])[0] || {}).campaign || '';
      k.f.climate = ((k.d.climates || [])[0] || {}).code || '';
    }catch(e){ k.err = errText(e); }
    finally{ k.loading = false; }
  }
  mszPaint();
}

function mnwSet(field, value){
  const k = state.mnw;
  if(!k) return;
  k.f[field] = value;
  k.plan = null;
  mszPaint();
}

function mnwFaction(name, on){
  const k = state.mnw;
  if(!k) return;
  const s = new Set(k.f.factions);
  if(on) s.add(name); else s.delete(name);
  k.f.factions = [...s];
  k.plan = null;
  mszPaint();
}

function mnwBody(){
  const k = state.mnw, f = k.f;
  const base = {mod: k.mod, name: f.name.trim(), title: f.title.trim(), source: f.source,
                climate: f.climate, factions: f.factions};
  if(f.shape !== 'real')
    return Object.assign(base, {width: f.width, height: f.height, provinces: f.provinces, land: f.land});
  // 87e: the height follows the box's shape (osmmap.size_for), so it is not sent
  return Object.assign(base, {shape: 'real', box: f.box, width: f.width,
    settlements: f.settlements, provinces: f.settlements.length ? 0 : f.provinces,
    coast: f.coast, water: f.lakes ? ['lake', 'lagoon'] : [], rivers: f.rivers,
    climates: f.climates, min_island: f.min_island});
}

//: 87e: the height a real-world map comes out at, the box's shape (osmmap.size_for)
function mnwRealHeight(){
  const f = state.mnw.f;
  if(!f.box || !osmBoxOk(f.box)) return 0;
  return Math.max(2, 1 + Math.round((f.width - 1) / osmAspect(f.box)));
}

//: 87e: open the world picker to choose the box and the cities
function mnwPickReal(){
  const k = state.mnw, c = state.cmap;
  if(!state.osm || state.osm.mod !== c.mod) state.osm = osmNew(c.mod);
  const go = () => owpOpen('campaign');
  if(state.osm.st) go();
  else osmLoad().then(() => { if(state.osm.st && state.osm.st.settings.enabled) go();
                              else toast('Turn the Real world switch on in Settings first.', 6000); });
}

async function mnwPlan(){
  const k = state.mnw;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.plan = null; mszPaint();
  let r;
  try{ r = await api.post('/api/mapnew/plan', mnwBody(), {label: 'drawing the new map'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  k.plan = r.plan || null;
  if(!k.plan) k.err = r.error || 'the plan came back empty';
  mszPaint();
}

async function mnwApply(){
  const k = state.mnw;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(`Make ${p.name}, a new campaign on a ${p.width}x${p.height} map?\n\n`
    + (p.changes || []).join('\n') + '\n\nNothing existing is written over, and 🕑 Log can undo it.')) return;
  k.busy = true; mszPaint();
  let r;
  try{ r = await api.post('/api/mapnew/apply', mnwBody(), {label: `making ${p.name}`}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!r || r.error){ k.err = (r && r.error) || 'it could not be made'; mszPaint(); return; }
  toast(`${r.name} made: ${r.files} file(s). Opening it. 🕑 Log can undo it.`, 7000);
  activity('new map', `${k.mod}: ${r.name}, ${p.width}x${p.height}, id ${r.id}`);
  k.plan = null;
  if(state.cbr){ state.cbr.d = null; }
  if(typeof cmapSetCampaign === 'function') cmapSetCampaign(r.name);
}

function mnwRealHtml(){
  const k = state.mnw, f = k.f, d = k.d, b = f.box;
  const num = (field, label, step, min, max) => `<label class="mszbox">${label}
      <input type="number" step="${step}" min="${min}" max="${max}" value="${f[field]}"
        onchange="mnwSet('${field}', +this.value)"></label>`;
  const sel = (field, pairs) => `<select onchange="mnwSet('${field}', this.value)">${pairs.map(([v, t]) =>
    `<option value="${v}"${f[field] === v ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>`;
  const hh = mnwRealHeight();
  return `<div class="bnote">The map is the real ground under a box, and a province grows round each
      city you pick. <button class="primary" onclick="mnwPickReal()">🌍 Pick the box and the cities…</button></div>
    ${b ? `<div class="count">Box N ${(+b.north).toFixed(3)} S ${(+b.south).toFixed(3)} W ${(+b.west).toFixed(3)}
      E ${(+b.east).toFixed(3)}${osmRot(b) ? `, turned ${(+b.rotation).toFixed(1)}°` : ''};
      ${f.settlements.length ? `${f.settlements.length} cit(ies): ${esc(f.settlements.map(s => s.name).join(', '))}`
        : 'no cities picked, so they are spread evenly'}.</div>` : '<div class="count">No box yet.</div>'}
    <div class="mszgrid">
      ${num('width', 'Width (tiles)', 1, d.limits.min, d.limits.max)}
      <label class="mszbox">Height <span class="count">${hh ? hh + ' (the box’s shape)' : '-'}</span></label>
      ${f.settlements.length ? '' : num('provinces', 'Cities to spread', 1, 1, 199)}
    </div>
    <div class="mszgrid">
      <label class="mszbox">Climates ${sel('climates', [['ground', 'from the ground types'],
        ['koppen', 'from the Köppen zones'], ['one', 'one climate, below']])}</label>
      <label class="mszbox">Rivers ${sel('rivers', [['major', 'rivers'], ['medium', 'rivers and canals'],
        ['all', 'rivers, canals and streams'], ['none', 'none']])}</label>
      ${num('min_island', 'Smallest island (tiles)', 1, 0, 1000)}
    </div>
    <div class="brow" style="gap:12px">
      <label class="chk"><input type="checkbox" ${f.coast ? 'checked' : ''} onchange="mnwSet('coast', this.checked)">
        the real coastline</label>
      <label class="chk"><input type="checkbox" ${f.lakes ? 'checked' : ''} onchange="mnwSet('lakes', this.checked)">
        lakes and lagoons as sea</label>
    </div>`;
}

function mnwHtml(){
  const k = mnwState();
  if(!k) return '';
  const head = `<div class="cmrow cmhdr" onclick="mnwToggle()">
      <b>New map</b> <span class="count">a new campaign on a map made from nothing</span>
      <span class="count">${k.open ? '▾' : '▸'}</span>
    </div>`;
  if(!k.open) return head;
  if(!k.d) return head + `<div class="count">${k.loading ? 'Reading…' : esc(k.err)}</div>`;
  const f = k.f, d = k.d, p = k.plan;
  const num = (field, label, step, min, max) => `<label class="mszbox">${label}
      <input type="number" step="${step}" min="${min}" max="${max}" value="${f[field]}"
        onchange="mnwSet('${field}', +this.value)"></label>`;
  return `${head}
    <div class="bsec">
      <div class="brow" style="flex-wrap:wrap;gap:6px">
        <label class="mszbox" style="flex:1 1 140px">Folder name
          <input value="${esc(f.name)}" placeholder="Iceland" onchange="mnwSet('name', this.value)"></label>
        <label class="mszbox" style="flex:1 1 140px">Menu title
          <input value="${esc(f.title)}" placeholder="what the new-game menu shows"
            onchange="mnwSet('title', this.value)"></label>
      </div>
      <div class="brow" style="gap:12px">
        <label class="chk"><input type="radio" name="mnwShape" ${f.shape !== 'real' ? 'checked' : ''}
          onchange="mnwSet('shape','island')"> An island from nothing</label>
        <label class="chk"><input type="radio" name="mnwShape" ${f.shape === 'real' ? 'checked' : ''}
          onchange="mnwSet('shape','real')"> The real world</label>
      </div>
      ${f.shape === 'real' ? mnwRealHtml() : `<div class="mszgrid">
        ${num('width', 'Width (tiles)', 1, d.limits.min, d.limits.max)}
        ${num('height', 'Height (tiles)', 1, d.limits.min, d.limits.max)}
        ${num('provinces', 'Provinces', 1, 1, 199)}
      </div>`}
      <div class="mszgrid">
        ${f.shape === 'real' ? '' : num('land', 'Land share', 0.05, 0.1, 0.85)}
        <label class="mszbox">Climate <select onchange="mnwSet('climate', this.value)">
          ${(d.climates || []).map(c => `<option value="${esc(c.code)}"${c.code === f.climate ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
        </select></label>
        <label class="mszbox">Copy the rest from <select onchange="mnwSet('source', this.value)">
          ${(d.sources || []).map(s => `<option value="${esc(s.campaign)}"${s.campaign === f.source ? ' selected' : ''}>${esc(s.campaign)}</option>`).join('')}
        </select></label>
      </div>
      <div class="count">Factions to play, one province and a leader each; every other province is the rebels'.</div>
      <div class="mnwfac">${(d.factions || []).map(n => `<label class="chk"><input type="checkbox"
          ${f.factions.includes(n) ? 'checked' : ''} onchange="mnwFaction('${esc(n)}', this.checked)"> ${esc(n)}</label>`).join('')}</div>
      <div class="cmbar2">
        <button onclick="mnwPlan()" ${k.busy ? 'disabled' : ''}>${k.busy ? 'Working…' : 'Plan'}</button>
        <button class="primary" onclick="mnwApply()" ${p && p.ok && !k.busy ? '' : 'disabled'}>Make it</button>
      </div>
      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${p ? `<div class="mszplan">
        ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
        ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
        ${(p.errors || []).map(x => `<div class="w-bad">${esc(x)}</div>`).join('')}
      </div>` : ''}
    </div>`;
}
