/* mapgen.js - Campaign Map: layers made from the real world, or each other (Phase 27)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   GENERATE - Phase 27, Mylae's BboxLayerGenerator, FeaturesLayerGenerator
   and autoGroundTypes.

   Every name here starts `mgn`. It is a sub-tab of Map, four cards, one per
   generator (unittransfer/mapgen.py). Each is Plan, which shows the layer as
   it would be, then Write, one backup and one Undo in the Log. The two that
   use the network (heights, rivers) are under the Real world switch and use
   the Real world tab's box; the two that do not (ground types, climates) read
   only the map.
   ===================================================================== */

const MGN_TITLES = {
  heights: [tt('mapgen.heights_from_the_real_world'),
            tt('mapgen.the_real_ground_under_the_maps')],
  adjust: [tt('mapgen.adjust_the_heights'),
           tt('mapgen.brightness_contrast_gamma_and_equalize_on')],
  ground: [tt('mapgen.ground_types_from_the_heights'),
           tt('mapgen.each_land_corner_typed_by_its')],
  climates: [tt('mapgen.climates_from_the_ground_types'),
             tt('mapgen.each_ground_type_painted_the_climate')],
  landuse: [tt('mapgen.ground_types_from_openstreetmap_land_use'),
            tt('mapgen.mylaes_47_tags_each_painted_as')],
  landcover: [tt('mapgen.ground_types_from_land_cover'),
              tt('mapgen.esa_worldcovers_eleven_classes_under_the')],
  koppen: [tt('mapgen.climates_from_the_k_ppen_geiger'),
           tt('mapgen.the_climate_zone_under_every_corner')],
  features: [tt('mapgen.rivers_cliffs_and_volcanoes_from_openstreetmap'),
             tt('mapgen.drawn_the_way_the_engine_can')],
};

function mgnOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.mgn || state.mgn.mod !== c.mod)
    state.mgn = {mod: c.mod, open: false, d: null, loading: false, err: '',
                 opt: {heights: {area: 'land', scale: 'true'},
                       adjust: {brightness: 0, contrast: 0, gamma: 1, equalize: false},
                       ground: {bands: null}, climates: {mapping: null, fill: ''},
                       landuse: {tags: {}}, landcover: {mapping: null},
                       koppen: {mapping: null, source: ''},
                       features: {detail: 'major', mode: 'replace'}},
                 plan: {}, busy: ''};
  mgnPaint();
}

async function mgnToggle(){
  const k = state.mgn;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.d && !k.loading) await mgnLoad();
  mgnPaint();
}

async function mgnLoad(){
  const k = state.mgn;
  k.loading = true; mgnPaint();
  try{
    k.d = await api.get(`/api/mapgen?mod=${enc(k.mod)}`, {label: tt('mapgen.reading_the_generators')});
    k.opt.ground.bands = k.d.bands.map(b => b.slice());
    const have = new Set(k.d.climates.map(c => c.code));
    k.opt.climates.mapping = {};
    for(const g of k.d.grounds){
      const want = k.d.climate_of[g];
      k.opt.climates.mapping[g] = have.has(want) ? want : '';
    }
    // 87d: his defaults, a climate this mod lacks left blank (as it is)
    const r = k.d.real;
    if(!k.opt.landcover.mapping){
      k.opt.landcover.mapping = {};
      for(const c of r.worldcover) k.opt.landcover.mapping[c.class] = c.ground;
    }
    if(!k.opt.koppen.mapping){
      k.opt.koppen.mapping = {};
      for(const z of r.koppen) k.opt.koppen.mapping[z.code] = have.has(z.climate) ? z.climate : '';
    }
    if(!k.opt.koppen.source) k.opt.koppen.source = r.koppen_file_ok || !r.koppen_wms ? 'file' : 'wms';
  }catch(e){ k.err = errText(e); }
  finally{ k.loading = false; }
}

function mgnSet(kind, field, value){
  const k = state.mgn;
  k.opt[kind][field] = value;
  delete k.plan[kind];
  mgnPaint();
}

function mgnBand(i, field, value){
  const k = state.mgn;
  const b = k.opt.ground.bands[i];
  if(field === 'code') b[0] = value; else b[1] = Math.max(0, Math.min(255, parseInt(value, 10) || 0));
  delete k.plan.ground;
  mgnPaint();
}

function mgnClimate(g, value){
  const k = state.mgn;
  k.opt.climates.mapping[g] = value;
  delete k.plan.climates;
  mgnPaint();
}

function mgnBody(kind){
  const k = state.mgn, c = state.cmap;
  const body = {mod: c.mod, campaign: c.campaign || '', kind};
  if(kind === 'heights') Object.assign(body, k.opt.heights);
  if(kind === 'ground') body.bands = k.opt.ground.bands;
  if(kind === 'climates'){
    // an empty choice leaves that ground type's climate as it is
    body.mapping = {};
    for(const [g, v] of Object.entries(k.opt.climates.mapping)) body.mapping[g] = v || '-';
  }
  if(kind === 'features') Object.assign(body, k.opt.features);
  if(kind === 'adjust') Object.assign(body, k.opt.adjust);
  if(kind === 'climates' && k.opt.climates.fill) body.fill = k.opt.climates.fill;
  if(kind === 'landuse') body.tags = Object.assign({}, k.opt.landuse.tags);
  if(kind === 'landcover'){
    body.mapping = {};
    for(const [c, g] of Object.entries(k.opt.landcover.mapping)) body.mapping[c] = g || '-';
  }
  if(kind === 'koppen'){
    body.source = k.opt.koppen.source;
    body.mapping = {};
    for(const [z, c] of Object.entries(k.opt.koppen.mapping)) body.mapping[z] = c || '-';
  }
  return body;
}

async function mgnPlan(kind){
  const k = state.mgn;
  if(!k || k.busy) return;
  k.busy = kind; k.err = ''; mgnPaint();
  let r;
  try{ r = await api.post('/api/map/gen_plan', mgnBody(kind),
                          {label: MGN_TITLES[kind][0].toLowerCase()}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = ''; }
  k.plan[kind] = r.plan || {errors: [r.error || tt('common.the_plan_came_back_empty')]};
  mgnPaint();
}

async function mgnApply(kind){
  const k = state.mgn;
  const p = k && k.plan[kind];
  if(!p || !p.ok || k.busy) return;
  if(!confirm(`${MGN_TITLES[kind][0]}?\n\n${(p.changes || []).join('\n')}`
    + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + tt('mapgen.one_backup_log_can_undo_it'))) return;
  k.busy = kind; mgnPaint();
  let r;
  try{ r = await api.post('/api/map/gen_apply', mgnBody(kind), {label: tt('mapgen.writing_the_layer')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = ''; }
  if(!r || r.error){ k.plan[kind] = {errors: [(r && r.error) || tt('mapgen.it_could_not_be_written')]}; mgnPaint(); return; }
  toast(tt('mapgen.written_log_can_undo_it',{x:MGN_TITLES[kind][0],files:r.files.join(', ')}), 7000);
  activity(tt('mapgen.map_generate'), tt('mapgen.id',{mod:k.mod,kind,id:r.id}));
  delete k.plan[kind];
  if(typeof loadCampmap === 'function') loadCampmap();
}

//: 87d: a tag ticked takes his ground type; unticked, it is not fetched
function mgnTag(key, on, ground){
  const t = state.mgn.opt.landuse.tags;
  if(on) t[key] = ground; else delete t[key];
  delete state.mgn.plan.landuse;
  mgnPaint();
}

function mgnMap(kind, key, value){
  const k = state.mgn;
  if(kind === 'landuse') k.opt.landuse.tags[key] = value;
  else k.opt[kind].mapping[key] = value;
  delete k.plan[kind];
  mgnPaint();
}

function mgnPaint(){
  const el = document.getElementById('cmGen');
  if(!el) return;
  el.innerHTML = mgnHtml();
}

function mgnCard(kind, body, network){
  const k = state.mgn, p = k.plan[kind];
  const off = network && !k.d.network;
  return `<div class="bsec mgncard">
      <h4>${esc(MGN_TITLES[kind][0])}</h4>
      <div class="count">${esc(MGN_TITLES[kind][1])}</div>
      ${off ? `<div class="bnote">${tt('mapgen.uses_the_internet_and_the_real')}
          <button onclick="openSettings()">${tt('mapgen.settings')}</button></div>` : body}
      <div class="cmbar2">
        <button onclick="mgnPlan('${kind}')" ${k.busy || off ? 'disabled' : ''}>${k.busy === kind ? tt('common.working') : tt('mapgen.plan')}</button>
        <button class="primary" onclick="mgnApply('${kind}')" ${p && p.ok && !k.busy ? '' : 'disabled'}>${tt('mapgen.write')}</button>
      </div>
      ${p ? `<div class="mszplan">
        ${p.preview ? `<img class="mgnprev" src="${p.preview}" alt="${ttA('mapgen.the_layer_as_it_would_be')}">` : ''}
        ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
        ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
        ${(p.errors || []).map(x => `<div class="w-bad">${esc(x)}</div>`).join('')}
      </div>` : ''}
    </div>`;
}

function mgnHtml(){
  const k = state.mgn;
  if(!k) return '';
  const head = `<div class="cmrow cmhdr" onclick="mgnToggle()">
      ${tt('mapgen.generate_layers_from_the_real_world',{open:k.open ? '▾' : '▸'})}
    </div>`;
  if(!k.open) return head;
  if(!k.d) return head + `<div class="count">${k.loading ? tt('common.reading_3') : esc(k.err)}</div>`;
  const o = k.opt, d = k.d;
  const sel = (kind, field, pairs) => `<select onchange="mgnSet('${kind}','${field}',this.value)">${
    pairs.map(([v, t]) => `<option value="${v}"${o[kind][field] === v ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>`;
  const heights = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">${tt('mapgen.where',{sel:sel('heights', 'area', [['land', tt('mapgen.the_land_the_map_has')], ['whole', tt('mapgen.the_whole_map_sea_floor_too')]])})}</label>
      <label class="mszbox">${tt('mapgen.scale',{sel:sel('heights', 'scale', [['true', tt('mapgen.true_by_max_land_height')], ['stretch', tt('mapgen.stretched_to_the_highest_peak')]])})}</label>
    </div>`;
  // 87c: Mylae's three sliders and his Equalize, as one plan
  const a = o.adjust;
  const slider = (f, lo, hi, step) => `<label style="display:block">${f}
      <span class="count">${f === 'gamma' ? (+a[f]).toFixed(2) : (a[f] > 0 ? '+' : '') + a[f]}</span>
      <input type="range" min="${lo}" max="${hi}" step="${step}" value="${a[f]}" style="width:100%"
        onchange="mgnSet('adjust','${f}',+this.value)"></label>`;
  const adjust = `${slider('brightness', -100, 100, 1)}${slider('contrast', -100, 100, 1)}${slider('gamma', 0.1, 3, 0.05)}
    <label class="chk"><input type="checkbox" ${a.equalize ? 'checked' : ''}
      onchange="mgnSet('adjust','equalize',this.checked)"> ${tt('mapgen.equalize_first_spread_the_lands_greys')}</label>
    <div class="cmbar2"><button onclick="state.mgn.opt.adjust={brightness:0,contrast:0,gamma:1,equalize:false};delete state.mgn.plan.adjust;mgnPaint()">${tt('mapgen.reset')}</button></div>`;
  const grounds = d.grounds;
  const ground = `<div class="mgnbands">${o.ground.bands.map((b, i) => `<div>
      <select onchange="mgnBand(${i},'code',this.value)">${grounds.map(g =>
        `<option${g === b[0] ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select>
      <span class="count">${tt('mapgen.up_to_grey')}</span>
      <input type="number" min="0" max="255" value="${b[1]}" onchange="mgnBand(${i},'max',this.value)">
    </div>`).join('')}</div>`;
  // 87d: the three from the real world
  const r = d.real, landGrounds = grounds;
  const gsel = (kind, key, val, blank) => `<select onchange="mgnMap('${kind}','${esc(key)}',this.value)">
      ${blank ? `<option value="">${blank}</option>` : ''}${landGrounds.map(g =>
      `<option${g === val ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select>`;
  const lt = o.landuse.tags, nOn = Object.keys(lt).length;
  const landuse = `<div class="count">${tt('mapgen.each_tag_is_its_own_request',{nOn:nOn ? tt('mapgen.tag_s_ticked',{nOn}) : tt('mapgen.tick_the_tags_to_fetch')})}</div>
    ${r.landuse.map(g => `<details class="mgngroup"${g.tags.some(t => lt[t.key + '=' + t.value]) ? ' open' : ''}>
      <summary>${esc(g.group)} <span class="count">${g.tags.filter(t => lt[t.key + '=' + t.value]).length}/${g.tags.length}</span></summary>
      <div class="mgnbands">${g.tags.map(t => { const key = t.key + '=' + t.value, on = key in lt; return `<div>
        <label class="chk" style="flex:1" title="${esc(key)}"><input type="checkbox" ${on ? 'checked' : ''}
          onchange="mgnTag('${esc(key)}',this.checked,'${esc(t.ground)}')"> ${esc(t.label)}</label>
        ${on ? gsel('landuse', key, lt[key]) : `<span class="count">${esc(t.ground)}</span>`}</div>`; }).join('')}</div>
    </details>`).join('')}`;
  const landcover = `<div class="mgnbands">${r.worldcover.map(c => `<div>
      <span class="mgnsw" style="background:rgb(${c.rgb.join(',')})"></span>
      <span style="flex:1">${esc(c.name)}</span>
      ${gsel('landcover', String(c.class), o.landcover.mapping[c.class], tt('mapgen.leave_as_it_is'))}</div>`).join('')}</div>
    <div class="count">${tt('mapgen.from_settings_lists_it',{landcover_wms:esc((r.landcover_wms[0] || '').replace(/\?.*/, ''))})}</div>`;
  const ks = o.koppen.source;
  const koppen = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">${tt('common.from')} <select onchange="mgnSet('koppen','source',this.value)">
        <option value="file"${ks === 'file' ? ' selected' : ''}>${tt('mapgen.the_map_on_disk')}</option>
        <option value="wms"${ks === 'wms' ? ' selected' : ''}>${tt('mapgen.a_wms')}</option></select></label></div>
    ${ks === 'file' ? (r.koppen_file_ok
        ? `<div class="count">${tt('mapgen.no_internet_needed',{koppen_file:esc(r.koppen_file)})}</div>`
        : `<div class="bnote">${tt('mapgen.no_k_ppen_geiger_map_on')}
            <button onclick="openSettings()">${tt('mapgen.settings')}</button></div>`)
      : (r.koppen_wms ? `<div class="count">${tt('mapgen.from_the_wms_in_settings')}</div>`
        : `<div class="bnote">${tt('mapgen.no_k_ppen_wms_is_set')} <button onclick="openSettings()">${tt('mapgen.settings')}</button></div>`)}
    <div class="mgnbands">${r.koppen.map(z => `<div>
      <span class="mgnsw" style="background:rgb(${z.rgb.join(',')})"></span>
      <span style="flex:1">${esc(z.code)}</span>
      <select onchange="mgnMap('koppen','${z.code}',this.value)">
        <option value="">${tt('mapgen.leave_as_it_is')}</option>
        ${d.climates.map(c => `<option value="${esc(c.code)}"${o.koppen.mapping[z.code] === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></div>`).join('')}</div>`;
  const climates = `<label class="mszbox" style="display:block">${tt('mapgen.or_one_climate_everywhere')}
      <select onchange="mgnSet('climates','fill',this.value)"><option value="">${tt('mapgen.no_by_ground_type_below')}</option>
      ${d.climates.map(c => `<option value="${esc(c.code)}"${o.climates.fill === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></label>
    ${o.climates.fill ? '' : `<div class="mgnbands">${grounds.map(g => `<div>
      <span style="flex:1">${esc(g)}</span>
      <select onchange="mgnClimate('${g}',this.value)">
        <option value="">${tt('mapgen.leave_as_it_is')}</option>
        ${d.climates.map(c => `<option value="${esc(c.code)}"${o.climates.mapping[g] === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></div>`).join('')}</div>`}`;
  const features = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">${tt('mapgen.rivers',{sel:sel('features', 'detail', [['major', 'rivers'], ['medium', tt('mapgen.rivers_and_canals')], ['all', tt('mapgen.rivers_canals_and_streams')]])})}</label>
      <label class="mszbox">${tt('mapgen.the_old_ones',{sel:sel('features', 'mode', [['replace', tt('mapgen.cleared_first')], ['add', tt('mapgen.kept_and_joined')]])})}</label>
    </div>`;
  return `${head}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="count">${tt('mapgen.the_box_is_the_real_world')}</div>
    ${mgnCard('heights', heights, true)}
    ${mgnCard('adjust', adjust, false)}
    ${mgnCard('ground', ground, false)}
    ${mgnCard('landuse', landuse, true)}
    ${mgnCard('landcover', landcover, true)}
    ${mgnCard('climates', climates, false)}
    ${mgnCard('koppen', koppen, o.koppen.source === 'wms')}
    ${mgnCard('features', features, true)}`;
}
