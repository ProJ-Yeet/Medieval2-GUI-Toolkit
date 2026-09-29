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
                          {label: tt('mapsize.working_out_the_resize')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(state.msz !== k) return;
  k.plan = r.plan || null;
  if(!k.plan) k.err = r.error || tt('common.the_plan_came_back_empty');
  mszPaint();
}

async function mszApply(){
  const k = state.msz;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(tt('mapsize.resize_confirm',{old:p.old.join('x'),new:p.new.join('x'),
    changes:(p.changes || []).join('\n')
      + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')}))) return;
  k.busy = true;
  mszPaint();
  let r;
  try{ r = await api.post('/api/map/resize_apply', mszBody(),
                          {label: tt('mapsize.resizing_the_map')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!r || r.error){
    k.err = (r && r.error) || tt('mapsize.the_resize_failed');
    mszPaint();
    return;
  }
  toast(tt('mapsize.map_now_files_written_log_can_undo',{new:r.new.join('x'),files_n:r.files.length}), 7000);
  activity(tt('mapsize.map_resize'), tt('mapsize.id',{mod:k.mod,old:r.old.join('x'),new:r.new.join('x'),id:r.id}));
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
      ${tt('mapsize.resize_x_tiles',{width:c.man.width,height:c.man.height,open:k.open ? '▾' : '▸'})}
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
      <div class="count">${tt('mapsize.tiles_to_add_on_each_edge')}</div>
      <div class="cmbar2">
        <button onclick="mszPlan()" ${k.busy ? 'disabled' : ''}>${k.busy ? tt('common.working') : tt('mapsize.plan')}</button>
        <button class="primary" onclick="mszApply()" ${p && p.ok && !k.busy ? '' : 'disabled'}>${tt('mapsize.resize')}</button>
      </div>
      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${p ? `<div class="mszplan">
        ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
        ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
        ${(p.errors || []).map(x => `<div class="w-bad">${esc(x)}</div>`).join('')}
        ${off.length ? `<div class="mszoff">${off.map(([f, rows]) => `
          <div><b>${esc(f)}</b></div>
          ${rows.map(([ln, t]) => `<div class="count">${ln ? tt('mapsize.line',{ln}) : ''}${esc(t)}</div>`).join('')}`
          ).join('')}${p.off_total > off.reduce((a, [, r]) => a + r.length, 0)
            ? `<div class="count">${tt('mapsize.and_more',{x:p.off_total - off.reduce((a, [, r]) => a + r.length, 0)})}</div>` : ''}
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
      k.d = await api.get(`/api/mapnew?mod=${enc(k.mod)}`, {label: tt('mapsize.reading_factions_and_climates')});
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
                              else toast(tt('mapsize.turn_the_real_world_switch_on'), 6000); });
}

async function mnwPlan(){
  const k = state.mnw;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.plan = null; mszPaint();
  let r;
  try{ r = await api.post('/api/mapnew/plan', mnwBody(), {label: tt('mapsize.drawing_the_new_map')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  k.plan = r.plan || null;
  if(!k.plan) k.err = r.error || tt('common.the_plan_came_back_empty');
  mszPaint();
}

async function mnwApply(){
  const k = state.mnw;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(tt('mapsize.make_campaign_confirm',{name:p.name,width:p.width,height:p.height,
    changes:(p.changes || []).join('\n')}))) return;
  k.busy = true; mszPaint();
  let r;
  try{ r = await api.post('/api/mapnew/apply', mnwBody(), {label: tt('mapsize.making_name',{name:p.name})}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!r || r.error){ k.err = (r && r.error) || tt('mapsize.it_could_not_be_made'); mszPaint(); return; }
  toast(tt('mapsize.made_file_s_opening_it_log',{name:r.name,files:r.files}), 7000);
  activity(tt('mapsize.new_map'), tt('mapsize.x_id',{mod:k.mod,name:r.name,width:p.width,height:p.height,id:r.id}));
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
  return `<div class="bnote">${tt('mapsize.the_map_is_the_real_ground')} <button class="primary" onclick="mnwPickReal()">${tt('mapsize.pick_the_box_and_the_cities')}</button></div>
    ${b ? `<div class="count">${tt('mapsize.box_n_s_w_e',{north:(+b.north).toFixed(3),south:(+b.south).toFixed(3),west:(+b.west).toFixed(3),east:(+b.east).toFixed(3),osmRot:osmRot(b) ? tt('mapsize.turned',{rotation:(+b.rotation).toFixed(1)}) : '',x:f.settlements.length ? tt('mapsize.cit_ies',{settlements_n:f.settlements.length,x:esc(f.settlements.map(s => s.name).join(', '))})
        : tt('mapsize.no_cities_picked_so_they_are')})}</div>` : `<div class="count">${tt('mapsize.no_box_yet')}</div>`}
    <div class="mszgrid">
      ${num('width', tt('mapsize.width_tiles'), 1, d.limits.min, d.limits.max)}
      <label class="mszbox">${tt('common.height')} <span class="count">${hh ? tt('mapsize.height_the_boxs_shape',{height:hh}) : '-'}</span></label>
      ${f.settlements.length ? '' : num('provinces', tt('mapsize.cities_to_spread'), 1, 1, 199)}
    </div>
    <div class="mszgrid">
      <label class="mszbox">${tt('mapsize.climates',{sel:sel('climates', [['ground', tt('mapsize.from_the_ground_types')],
        ['koppen', tt('mapsize.from_the_k_ppen_zones')], ['one', tt('mapsize.one_climate_below')]])})}</label>
      <label class="mszbox">${tt('mapsize.rivers',{sel:sel('rivers', [['major', tt('mapsize.rivers_only')], ['medium', tt('mapsize.rivers_and_canals')],
        ['all', tt('mapsize.rivers_canals_and_streams')], ['none', 'none']])})}</label>
      ${num('min_island', tt('mapsize.smallest_island_tiles'), 1, 0, 1000)}
    </div>
    <div class="brow" style="gap:12px">
      <label class="chk"><input type="checkbox" ${f.coast ? 'checked' : ''} onchange="mnwSet('coast', this.checked)">
        ${tt('mapsize.the_real_coastline')}</label>
      <label class="chk"><input type="checkbox" ${f.lakes ? 'checked' : ''} onchange="mnwSet('lakes', this.checked)">
        ${tt('mapsize.lakes_and_lagoons_as_sea')}</label>
    </div>`;
}

function mnwHtml(){
  const k = mnwState();
  if(!k) return '';
  const head = `<div class="cmrow cmhdr" onclick="mnwToggle()">
      ${tt('mapsize.new_map_a_new_campaign_on',{open:k.open ? '▾' : '▸'})}
    </div>`;
  if(!k.open) return head;
  if(!k.d) return head + `<div class="count">${k.loading ? tt('common.reading_3') : esc(k.err)}</div>`;
  const f = k.f, d = k.d, p = k.plan;
  const num = (field, label, step, min, max) => `<label class="mszbox">${label}
      <input type="number" step="${step}" min="${min}" max="${max}" value="${f[field]}"
        onchange="mnwSet('${field}', +this.value)"></label>`;
  return `${head}
    <div class="bsec">
      <div class="brow" style="flex-wrap:wrap;gap:6px">
        <label class="mszbox" style="flex:1 1 140px">${tt('mapsize.folder_name')}
          <input value="${esc(f.name)}" placeholder="${ttA('mapsize.iceland')}" onchange="mnwSet('name', this.value)"></label>
        <label class="mszbox" style="flex:1 1 140px">${tt('mapsize.menu_title')}
          <input value="${esc(f.title)}" placeholder="${ttA('mapsize.what_the_new_game_menu_shows')}"
            onchange="mnwSet('title', this.value)"></label>
      </div>
      <div class="brow" style="gap:12px">
        <label class="chk"><input type="radio" name="mnwShape" ${f.shape !== 'real' ? 'checked' : ''}
          onchange="mnwSet('shape','island')"> ${tt('mapsize.an_island_from_nothing')}</label>
        <label class="chk"><input type="radio" name="mnwShape" ${f.shape === 'real' ? 'checked' : ''}
          onchange="mnwSet('shape','real')"> ${tt('mapsize.the_real_world')}</label>
      </div>
      ${f.shape === 'real' ? mnwRealHtml() : `<div class="mszgrid">
        ${num('width', tt('mapsize.width_tiles'), 1, d.limits.min, d.limits.max)}
        ${num('height', tt('mapsize.height_tiles'), 1, d.limits.min, d.limits.max)}
        ${num('provinces', tt('mapsize.provinces'), 1, 1, 199)}
      </div>`}
      <div class="mszgrid">
        ${f.shape === 'real' ? '' : num('land', tt('mapsize.land_share'), 0.05, 0.1, 0.85)}
        <label class="mszbox">${tt('mapsize.climate')} <select onchange="mnwSet('climate', this.value)">
          ${(d.climates || []).map(c => `<option value="${esc(c.code)}"${c.code === f.climate ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
        </select></label>
        <label class="mszbox">${tt('mapsize.copy_the_rest_from')} <select onchange="mnwSet('source', this.value)">
          ${(d.sources || []).map(s => `<option value="${esc(s.campaign)}"${s.campaign === f.source ? ' selected' : ''}>${esc(s.campaign)}</option>`).join('')}
        </select></label>
      </div>
      <div class="count">${tt('mapsize.factions_to_play_one_province_and')}</div>
      <div class="mnwfac">${(d.factions || []).map(n => `<label class="chk"><input type="checkbox"
          ${f.factions.includes(n) ? 'checked' : ''} onchange="mnwFaction('${esc(n)}', this.checked)"> ${esc(n)}</label>`).join('')}</div>
      <div class="cmbar2">
        <button onclick="mnwPlan()" ${k.busy ? 'disabled' : ''}>${k.busy ? tt('common.working') : tt('mapsize.plan')}</button>
        <button class="primary" onclick="mnwApply()" ${p && p.ok && !k.busy ? '' : 'disabled'}>${tt('mapsize.make_it')}</button>
      </div>
      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${p ? `<div class="mszplan">
        ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
        ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
        ${(p.errors || []).map(x => `<div class="w-bad">${esc(x)}</div>`).join('')}
      </div>` : ''}
    </div>`;
}
