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
  heights: ['Heights from the real world',
            'The real ground under the map’s box, at the engine’s own scale.'],
  adjust: ['Adjust the heights',
           'Brightness, contrast, gamma and equalize, on the land only: a sea corner is never touched.'],
  ground: ['Ground types from the heights',
           'Each land corner typed by its height, in bands. The sea is left alone.'],
  climates: ['Climates from the ground types',
             'Each ground type painted the climate chosen for it.'],
  landuse: ['Ground types from OpenStreetMap land use',
            'Mylae’s 47 tags, each painted as the ground type you give it, in the order listed, on land only. Best on a small box: farmland over a country is a big answer.'],
  landcover: ['Ground types from land cover',
              'ESA WorldCover’s eleven classes under the land, each a ground type. One class a corner, never a blend.'],
  koppen: ['Climates from the Köppen-Geiger zones',
           'The climate zone under every corner, each zone a climate of this mod. From the published map on disk, or a WMS.'],
  features: ['Rivers, cliffs and volcanoes from OpenStreetMap',
             'Drawn the way the engine can build a river: cardinal steps, no loops, a source each, cut at every city.'],
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
    k.d = await api.get(`/api/mapgen?mod=${enc(k.mod)}`, {label: 'reading the generators'});
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
  k.plan[kind] = r.plan || {errors: [r.error || 'the plan came back empty']};
  mgnPaint();
}

async function mgnApply(kind){
  const k = state.mgn;
  const p = k && k.plan[kind];
  if(!p || !p.ok || k.busy) return;
  if(!confirm(`${MGN_TITLES[kind][0]}?\n\n${(p.changes || []).join('\n')}`
    + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + '\n\nOne backup; 🕑 Log can undo it.')) return;
  k.busy = kind; mgnPaint();
  let r;
  try{ r = await api.post('/api/map/gen_apply', mgnBody(kind), {label: 'writing the layer'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = ''; }
  if(!r || r.error){ k.plan[kind] = {errors: [(r && r.error) || 'it could not be written']}; mgnPaint(); return; }
  toast(`${MGN_TITLES[kind][0]}: ${r.files.join(', ')} written. 🕑 Log can undo it.`, 7000);
  activity('map generate', `${k.mod}: ${kind}, id ${r.id}`);
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
      ${off ? `<div class="bnote">Uses the internet, and the Real world switch is off.
          <button onclick="openSettings()">⚙ Settings</button></div>` : body}
      <div class="cmbar2">
        <button onclick="mgnPlan('${kind}')" ${k.busy || off ? 'disabled' : ''}>${k.busy === kind ? 'Working…' : 'Plan'}</button>
        <button class="primary" onclick="mgnApply('${kind}')" ${p && p.ok && !k.busy ? '' : 'disabled'}>Write</button>
      </div>
      ${p ? `<div class="mszplan">
        ${p.preview ? `<img class="mgnprev" src="${p.preview}" alt="the layer as it would be">` : ''}
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
      <b>Generate</b> <span class="count">layers from the real world, or from each other</span>
      <span class="count">${k.open ? '▾' : '▸'}</span>
    </div>`;
  if(!k.open) return head;
  if(!k.d) return head + `<div class="count">${k.loading ? 'Reading…' : esc(k.err)}</div>`;
  const o = k.opt, d = k.d;
  const sel = (kind, field, pairs) => `<select onchange="mgnSet('${kind}','${field}',this.value)">${
    pairs.map(([v, t]) => `<option value="${v}"${o[kind][field] === v ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>`;
  const heights = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">Where ${sel('heights', 'area', [['land', 'the land the map has'], ['whole', 'the whole map, sea floor too']])}</label>
      <label class="mszbox">Scale ${sel('heights', 'scale', [['true', 'true, by max_land_height'], ['stretch', 'stretched to the highest peak']])}</label>
    </div>`;
  // 87c: Mylae's three sliders and his Equalize, as one plan
  const a = o.adjust;
  const slider = (f, lo, hi, step) => `<label style="display:block">${f}
      <span class="count">${f === 'gamma' ? (+a[f]).toFixed(2) : (a[f] > 0 ? '+' : '') + a[f]}</span>
      <input type="range" min="${lo}" max="${hi}" step="${step}" value="${a[f]}" style="width:100%"
        onchange="mgnSet('adjust','${f}',+this.value)"></label>`;
  const adjust = `${slider('brightness', -100, 100, 1)}${slider('contrast', -100, 100, 1)}${slider('gamma', 0.1, 3, 0.05)}
    <label class="chk"><input type="checkbox" ${a.equalize ? 'checked' : ''}
      onchange="mgnSet('adjust','equalize',this.checked)"> Equalize first (spread the land's greys evenly)</label>
    <div class="cmbar2"><button onclick="state.mgn.opt.adjust={brightness:0,contrast:0,gamma:1,equalize:false};delete state.mgn.plan.adjust;mgnPaint()">Reset</button></div>`;
  const grounds = d.grounds;
  const ground = `<div class="mgnbands">${o.ground.bands.map((b, i) => `<div>
      <select onchange="mgnBand(${i},'code',this.value)">${grounds.map(g =>
        `<option${g === b[0] ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select>
      <span class="count">up to grey</span>
      <input type="number" min="0" max="255" value="${b[1]}" onchange="mgnBand(${i},'max',this.value)">
    </div>`).join('')}</div>`;
  // 87d: the three from the real world
  const r = d.real, landGrounds = grounds;
  const gsel = (kind, key, val, blank) => `<select onchange="mgnMap('${kind}','${esc(key)}',this.value)">
      ${blank ? `<option value="">${blank}</option>` : ''}${landGrounds.map(g =>
      `<option${g === val ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select>`;
  const lt = o.landuse.tags, nOn = Object.keys(lt).length;
  const landuse = `<div class="count">${nOn ? `${nOn} tag(s) ticked` : 'Tick the tags to fetch.'}
      Each tag is its own request, kept on disk; a later tag paints over an earlier one.</div>
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
      ${gsel('landcover', String(c.class), o.landcover.mapping[c.class], '(leave as it is)')}</div>`).join('')}</div>
    <div class="count">From ${esc((r.landcover_wms[0] || '').replace(/\?.*/, ''))} (Settings lists it).</div>`;
  const ks = o.koppen.source;
  const koppen = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">From <select onchange="mgnSet('koppen','source',this.value)">
        <option value="file"${ks === 'file' ? ' selected' : ''}>the map on disk</option>
        <option value="wms"${ks === 'wms' ? ' selected' : ''}>a WMS</option></select></label></div>
    ${ks === 'file' ? (r.koppen_file_ok
        ? `<div class="count">${esc(r.koppen_file)} - no internet needed.</div>`
        : `<div class="bnote">No Köppen-Geiger map on disk yet. Download the 0.083° GeoTIFF (Beck et al.,
            CC BY 4.0, gloh2o.org/koppen) and give its path in Settings, Real-world map.
            <button onclick="openSettings()">⚙ Settings</button></div>`)
      : (r.koppen_wms ? '<div class="count">From the WMS in Settings.</div>'
        : `<div class="bnote">No Köppen WMS is set; Settings can take one. <button onclick="openSettings()">⚙ Settings</button></div>`)}
    <div class="mgnbands">${r.koppen.map(z => `<div>
      <span class="mgnsw" style="background:rgb(${z.rgb.join(',')})"></span>
      <span style="flex:1">${esc(z.code)}</span>
      <select onchange="mgnMap('koppen','${z.code}',this.value)">
        <option value="">(leave as it is)</option>
        ${d.climates.map(c => `<option value="${esc(c.code)}"${o.koppen.mapping[z.code] === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></div>`).join('')}</div>`;
  const climates = `<label class="mszbox" style="display:block">Or one climate everywhere
      <select onchange="mgnSet('climates','fill',this.value)"><option value="">(no: by ground type, below)</option>
      ${d.climates.map(c => `<option value="${esc(c.code)}"${o.climates.fill === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></label>
    ${o.climates.fill ? '' : `<div class="mgnbands">${grounds.map(g => `<div>
      <span style="flex:1">${esc(g)}</span>
      <select onchange="mgnClimate('${g}',this.value)">
        <option value="">(leave as it is)</option>
        ${d.climates.map(c => `<option value="${esc(c.code)}"${o.climates.mapping[g] === c.code ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
      </select></div>`).join('')}</div>`}`;
  const features = `<div class="brow" style="flex-wrap:wrap;gap:6px">
      <label class="mszbox">Rivers ${sel('features', 'detail', [['major', 'rivers'], ['medium', 'rivers and canals'], ['all', 'rivers, canals and streams']])}</label>
      <label class="mszbox">The old ones ${sel('features', 'mode', [['replace', 'cleared first'], ['add', 'kept, and joined']])}</label>
    </div>`;
  return `${head}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="count">The box is the Real world tab’s. Save or discard unsaved paint strokes first.</div>
    ${mgnCard('heights', heights, true)}
    ${mgnCard('adjust', adjust, false)}
    ${mgnCard('ground', ground, false)}
    ${mgnCard('landuse', landuse, true)}
    ${mgnCard('landcover', landcover, true)}
    ${mgnCard('climates', climates, false)}
    ${mgnCard('koppen', koppen, o.koppen.source === 'wms')}
    ${mgnCard('features', features, true)}`;
}
