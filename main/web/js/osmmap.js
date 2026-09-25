/* osmmap.js - Campaign Map: the real world behind the map (Phase 25)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   REAL WORLD - Phase 25, from Mylae's OsmBackground, OsmRegionSearch and
   CoastlineTracer.

   Every name here starts `osm`. It is a sub-tab of Map. Nothing on it talks to
   the network until the switch in Settings is on, and nothing it does goes
   anywhere but through Python: the tiles come through /api/osm/tile (cached on
   disk there), the coastline and the search through /api/osm, and the two
   things that change the map are strokes of the paint tool, so the paint
   tool's own Undo and Save are theirs too.

   THE BOX IS THE WHOLE ALIGNMENT. A tile's centre is where the box puts it -
   tile 0 on the west edge, tile W-1 on the east, Mercator down the rows -
   which is Mylae's latLngToPixel, so a bbox_coords.txt from his New Map Editor
   lines up here as it did there. Edited in the boxes, the backdrop follows at
   once; Keep sends it to Python.

   THE BACKDROP IS OVER THE MAP, not under it: the map's layers are opaque, and
   a picture under them would be a picture nobody sees. It has its own opacity.
   ===================================================================== */

const OSM_TILE_PX = 256;
//: The most OSM tiles one frame of the backdrop may ask for. Past it the zoom
//: steps down, so a whole-map view never fires a hundred requests.
const OSM_MAX_TILES = 48;

function osmNew(mod){
  return {mod, open: false, st: null, busy: false, err: '', box: null,
          show: true, alpha: 0.5, coast: null, showCoast: true, over: null,
          water: null, wkinds: {sea: true, lagoon: false, lake: false}, wmin: 16,
          style: 'osm', year: 1200, picW: 2048,
          q: '', results: null, target: '', job: '', pct: 0, label: ''};
}

function osmOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.osm || state.osm.mod !== c.mod) state.osm = osmNew(c.mod);
  osmPaint();
}

function osmToggle(){
  const k = state.osm;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.st) osmLoad(); else osmPaint();
}

async function osmLoad(){
  const k = state.osm, c = state.cmap;
  if(!k || !c) return;
  k.busy = true; k.err = ''; osmPaint();
  try{
    const r = await api.get(`/api/osm?mod=${enc(c.mod)}`, {label: 'real-world map'});
    if(state.osm !== k) return;
    if(r.error){ k.err = r.error; }
    else { k.st = r; k.box = r.box ? Object.assign({}, r.box) : null; }
  }catch(e){ if(state.osm === k) k.err = errText(e); }
  finally{ if(state.osm === k){ k.busy = false; osmPaint(); cmapPaint(); } }
}

const osmOn = () => !!(state.osm && state.osm.st && state.osm.st.settings.enabled);

/* ---------- the projection, the same two lines as osmmap.Projection ---------- */

function osmMerc(lat){
  const r = Math.max(-85.05112878, Math.min(85.05112878, lat)) * Math.PI / 180;
  return Math.log(Math.tan(Math.PI / 4 + r / 2));
}

/* 87a - A TURNED BOX. The rectangle is turned about its centre (the plain
   midpoint of its edges) in degree-scaled Mercator, positive clockwise on
   screen: osmmap.Bbox.turn, and Mylae's rotatedBbox, line for line. Turning is
   linear in (longitude, Mercator), so the whole projection stays affine in
   those two, which is what lets a slippy tile be drawn with one transform. */
const OSM_ROT_EPS = 0.01;
const osmMdeg = lat => osmMerc(lat) * 180 / Math.PI;
const osmInvMdeg = y => (2 * Math.atan(Math.exp(y * Math.PI / 180)) - Math.PI / 2) * 180 / Math.PI;
const osmRot = b => { const r = +(b && b.rotation) || 0; return Math.abs(r) >= OSM_ROT_EPS ? r : 0; };

//: [lon, Mercator degrees] turned about the box's centre by `ang` degrees
function osmTurnLM(b, lon, md, ang){
  if(!ang) return [lon, md];
  const a = ang * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const clon = (b.east + b.west) / 2, cy = osmMdeg((b.north + b.south) / 2);
  const dx = lon - clon, dy = md - cy;
  return [clon + dx * c + dy * s, cy + dy * c - dx * s];
}

//: [fx, fy] in tile space for a longitude and a Mercator value in radians
function osmTileOfLonMerc(b, W, H, lon, m){
  let md = m * 180 / Math.PI;
  const r = osmRot(b);
  if(r) [lon, md] = osmTurnLM(b, lon, md, -r);
  const mn = osmMdeg(b.north), ms = osmMdeg(b.south);
  return [(lon - b.west) / (b.east - b.west) * (W - 1), (mn - md) / (mn - ms) * (H - 1)];
}

//: [fx, fy] in tile space, a tile's centre at its whole number
function osmToTile(b, W, H, lat, lon){
  return osmTileOfLonMerc(b, W, H, lon, osmMerc(lat));
}

//: and back: [lat, lon] of a point in tile space
function osmToGeo(b, W, H, fx, fy){
  const mn = osmMdeg(b.north), ms = osmMdeg(b.south);
  let lon = b.west + fx / (W - 1) * (b.east - b.west), md = mn - fy / (H - 1) * (mn - ms);
  const r = osmRot(b);
  if(r) [lon, md] = osmTurnLM(b, lon, md, r);
  return [osmInvMdeg(md), lon];
}

//: The box's whole projection as an affine [a, b, c, d, e, f] in canvas order:
//: fx = a*lon + c*m + e, fy = b*lon + d*m + f, with m the Mercator in radians.
function osmGeoAffine(b, W, H){
  const o = osmTileOfLonMerc(b, W, H, 0, 0), p = osmTileOfLonMerc(b, W, H, 1, 0),
        q = osmTileOfLonMerc(b, W, H, 0, 1);
  return [p[0] - o[0], p[1] - o[1], q[0] - o[0], q[1] - o[1], o[0], o[1]];
}

//: a number for a box field: rounded for the eye, trailing zeros dropped
const osmNum = (v, dp) => typeof v === 'number' && isFinite(v) ? String(+v.toFixed(dp)) : String(v ?? '');

function osmBoxOk(b){
  return b && [b.north, b.south, b.west, b.east].every(v => typeof v === 'number' && isFinite(v))
    && b.north > b.south && b.east > b.west && b.north <= 85.05 && b.south >= -85.05
    && Math.abs(+b.rotation || 0) <= 180;
}

//: Degrees of longitude per degree of Mercator: osmmap.Bbox.aspect
const osmAspect = b => (b.east - b.west) / Math.max(osmMdeg(b.north) - osmMdeg(b.south), 1e-12);

//: How far a box stretches a W x H map: 0 is square tiles (osmmap.stretch)
const osmStretch = (b, W, H) => osmAspect(b) / ((W - 1) / Math.max(H - 1, 1)) - 1;

//: [km east-west, km north-south] one tile reaches (Projection.km_per_tile)
function osmKmPerTile(b, W, H){
  const cl = (b.north + b.south) / 2 * Math.PI / 180;
  const m = (osmMerc(b.north) - osmMerc(b.south)) / Math.max(H - 1, 1);
  const r = 6378.137 * Math.cos(cl);                 // osmmap.EARTH_KM, per radian there
  return [(b.east - b.west) * Math.PI / 180 / Math.max(W - 1, 1) * r, m * r];
}

/* ---------- drawing, called by cmapPaint inside its clip ---------- */

const _osmTiles = new Map();

/* 87b - THE STYLE. Mylae's reference layers and his historical map, one at a
   time, chosen on the panel and shared with the world picker. The standard
   style keeps Phase 25's URL; the others name themselves, and the historical
   map carries its year. */
const osmStyle = () => (state.osm && state.osm.style) || 'osm';
function osmStyleInfo(){
  const st = state.osm && state.osm.st, s = st && st.settings && st.settings.styles;
  return (s && s[osmStyle()]) || {name: 'OpenStreetMap', max_zoom: 19, credit: '© OpenStreetMap contributors'};
}
const osmMaxZoom = () => Math.min(18, osmStyleInfo().max_zoom || 18);

function osmTileUrl(z, x, y){
  const s = osmStyle();
  if(s === 'osm') return `/api/osm/tile/${z}/${x}/${y}`;
  return `/api/osm/tile/${s}/${z}/${x}/${y}` + (s === 'ohm' ? `?year=${state.osm.year}` : '');
}

function osmTileImg(z, x, y){
  const url = osmTileUrl(z, x, y);
  let t = _osmTiles.get(url);
  if(t) return t.ok ? t.img : null;
  const img = new Image();
  t = {img, ok: false};
  _osmTiles.set(url, t);
  img.onload = () => { t.ok = true; osmRepaintSoon(); };
  img.onerror = () => { t.failed = true; };
  img.src = url;
  return null;
}

let _osmSoon = 0;
function osmRepaintSoon(){
  if(_osmSoon) return;
  _osmSoon = setTimeout(() => {
    _osmSoon = 0;
    if(state.cmap) cmapPaint();
    if(typeof owpDraw === 'function' && state.owp && state.owp.open) owpDraw();   // 87a
  }, 60);
}

function osmDraw(x, s0, t0, s1, t1){
  const k = state.osm, c = state.cmap;
  if(!k || !c || !osmOn() || !osmBoxOk(k.box)) return;
  const W = c.man.width, H = c.man.height, v = c.view, b = k.box;
  if(k.show) osmDrawTiles(x, b, W, H, v, s0, t0, s1, t1);
  if(k.showCoast && k.over){
    x.save();
    x.imageSmoothingEnabled = false;
    x.globalAlpha = 0.9;
    x.drawImage(k.over, s0, t0, s1 - s0, t1 - t0,
                cmapX(s0), cmapY(t0), (s1 - s0) * v.zoom, (t1 - t0) * v.zoom);
    x.restore();
  }
}

function osmDrawTiles(x, b, W, H, v, s0, t0, s1, t1){
  const k = state.osm;
  // the zoom whose tiles come out about 256 screen pixels wide (a turn does
  // not change the scale)
  const span = b.east - b.west;
  let z = Math.round(Math.log2(360 * (W - 1) * v.zoom / (span * OSM_TILE_PX)));
  z = Math.max(0, Math.min(osmMaxZoom(), z));
  // the visible part of the map as geography: the envelope of its four
  // corners, which for an unturned box is the old rectangle exactly
  const fa = Math.max(-0.5, s0 - 0.5), fb = Math.min(W - 0.5, s1 - 0.5);
  const ga = Math.max(-0.5, t0 - 0.5), gb = Math.min(H - 0.5, t1 - 0.5);
  if(fb <= fa || gb <= ga) return;
  const cs = [[fa, ga], [fb, ga], [fa, gb], [fb, gb]].map(([p, q]) => osmToGeo(b, W, H, p, q));
  const lonA = Math.max(-180, Math.min(...cs.map(g => g[1])));
  const lonB = Math.min(180, Math.max(...cs.map(g => g[1])));
  const mA = osmMerc(Math.max(...cs.map(g => g[0]))), mB = osmMerc(Math.min(...cs.map(g => g[0])));
  if(lonB <= lonA || mA <= mB) return;
  let xs, ys;
  for(;; z--){
    const n = 2 ** z;
    xs = [Math.floor((lonA + 180) / 360 * n), Math.floor((lonB + 180) / 360 * n)];
    ys = [Math.floor((1 - mA / Math.PI) / 2 * n), Math.floor((1 - mB / Math.PI) / 2 * n)];
    if(z === 0 || (xs[1] - xs[0] + 1) * (ys[1] - ys[0] + 1) <= OSM_MAX_TILES) break;
  }
  const n = 2 ** z;
  x.save();
  // a tile is 256 pixels of somewhere; only the part over the map is the map's
  x.beginPath();
  x.rect(cmapX(0), cmapY(0), W * v.zoom, H * v.zoom);
  x.clip();
  x.globalAlpha = k.alpha;
  x.imageSmoothingEnabled = true;
  // a tile's pixel (u, v) is longitude L0 + u*dl and Mercator M0 + v*dm; the
  // box's affine takes those to tile space, and the view to the canvas
  const g = osmGeoAffine(b, W, H), zm = v.zoom;
  const dl = 360 / (n * OSM_TILE_PX), dm = -2 * Math.PI / (n * OSM_TILE_PX);
  for(let ty = Math.max(0, ys[0]); ty <= Math.min(n - 1, ys[1]); ty++){
    const M0 = Math.PI * (1 - 2 * ty / n);
    for(let tx = Math.max(0, xs[0]); tx <= Math.min(n - 1, xs[1]); tx++){
      const img = osmTileImg(z, tx, ty);
      if(!img) continue;
      const L0 = tx / n * 360 - 180;
      x.save();
      x.transform(g[0] * dl * zm, g[1] * dl * zm, g[2] * dm * zm, g[3] * dm * zm,
                  v.ox + (g[0] * L0 + g[2] * M0 + g[4] + 0.5) * zm,
                  v.oy + (g[1] * L0 + g[3] * M0 + g[5] + 0.5) * zm);
      x.drawImage(img, 0, 0, OSM_TILE_PX, OSM_TILE_PX);
      x.restore();
    }
  }
  x.restore();
}

//: The coastline's overlay, one pixel a tile like the composite: the line in
//: cyan, every tile the stroke would make sea in a see-through red.
function osmBuildOver(){
  const k = state.osm, c = state.cmap;
  k.over = null;
  if((!k.coast && !k.water) || !c) return;
  const W = c.man.width, H = c.man.height;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const x = cv.getContext('2d');
  const im = x.createImageData(W, H), d = im.data;
  const put = (xy, r, g, bl, a) => {
    for(let i = 0; i < xy.length; i += 2){
      const p = (xy[i + 1] * W + xy[i]) * 4;
      d[p] = r; d[p + 1] = g; d[p + 2] = bl; d[p + 3] = a;
    }
  };
  if(k.coast){
    put(k.coast.to_sea_xy || [], 255, 70, 70, 150);
    put(k.coast.line_xy || [], 0, 240, 255, 255);
  }
  // 87c: the land inside OSM's water, in a see-through blue
  if(k.water) put(k.water.to_sea_xy || [], 60, 110, 255, 170);
  x.putImageData(im, 0, 0);
  k.over = cv;
}

/* ---------- the style, and a picture of the box (87b) ---------- */

function osmSetStyle(style){
  const k = state.osm;
  k.style = style;
  osmPaint(); cmapPaint();
  if(state.owp && state.owp.open){ owpSide(); owpDraw(); }
}

function osmSetYear(y){
  const k = state.osm, st = k.st && k.st.settings;
  const [lo, hi] = (st && st.ohm_years) || [500, 1600];
  y = Math.round(+y);
  if(!isFinite(y)) return;
  k.year = Math.max(1, Math.min(2100, y));
  // the panel and the world picker each have a pair
  document.querySelectorAll('.osmYearN').forEach(n => { if(document.activeElement !== n) n.value = k.year; });
  document.querySelectorAll('.osmYearR').forEach(r => { r.value = Math.max(lo, Math.min(hi, k.year)); });
  cmapPaint();
  if(state.owp && state.owp.open) owpDraw();
}

//: The style picker, the year for the historical map, and its credit: the same
//: controls on the panel and in the world picker.
function osmStyleHtml(){
  const k = state.osm, st = k.st.settings, styles = st.styles || {};
  const [lo, hi] = st.ohm_years || [500, 1600];
  return `<label style="display:block">Style <select onchange="osmSetStyle(this.value)">${Object.entries(styles).map(([id, s]) =>
      `<option value="${id}" ${id === k.style ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select></label>
    ${k.style === 'ohm' ? `<div class="brow"><input type="range" class="osmYearR" min="${lo}" max="${hi}" step="1"
        value="${Math.max(lo, Math.min(hi, k.year))}" oninput="osmSetYear(this.value)" style="flex:1">
        <input type="number" class="osmYearN" min="1" max="2100" value="${k.year}" style="width:70px"
          onchange="osmSetYear(this.value)"> AD</div>
      <div class="cmbar2">${(st.ohm_eras || []).map(y =>
        `<button class="${y === k.year ? 'primary' : ''}" onclick="osmSetYear(${y});osmPaint();if(state.owp&&state.owp.open)owpSide()">${y}</button>`).join('')}</div>
      <div class="count">The historical borders as OpenHistoricalMap has them for 1 January of that
        year: a tracing guide for the regions.</div>` : ''}
    <div class="count">${esc(osmStyleInfo().credit)}</div>`;
}

async function osmPicture(fmt){
  const k = state.osm, c = state.cmap;
  if(!k || !c || k.busy) return;
  const q = `mod=${enc(c.mod)}&style=${enc(k.style)}&year=${k.year}&width=${k.picW}&format=${fmt}`;
  k.busy = true; osmPaint();
  try{
    const r = await fetch(`/api/osm/picture?${q}`);
    if(!r.ok){ toast('✗ ' + (await r.text()).slice(0, 300), 8000); return; }
    const name = ((r.headers.get('Content-Disposition') || '').match(/filename="([^"]+)"/) || [])[1]
      || `reference.${fmt}`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await r.blob());
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }catch(e){ toast('✗ ' + errText(e), 8000); }
  finally{ k.busy = false; osmPaint(); }
}

/* ---------- the box ---------- */

function osmBoxSet(field, value){
  const k = state.osm;
  if(!k.box) k.box = {north: 0, south: 0, west: 0, east: 0, rotation: 0};
  k.box[field] = parseFloat(value);
  k.coast = null; k.water = null; k.over = null;
  cmapPaint();                      // the backdrop follows before anything is kept
}

async function osmBoxPost(body){
  const k = state.osm, c = state.cmap;
  let r;
  try{ r = await api.post('/api/osm/box', Object.assign({mod: c.mod}, body),
                          {label: 'the real-world box'}); }
  catch(e){ r = {error: errText(e)}; }
  if(state.osm !== k) return;
  if(r.error){ toast('✗ ' + r.error, 7000); return; }
  k.st.box = r.box; k.st.box_from = r.box_from; k.st.file = r.file; k.st.shape = r.shape;
  k.box = r.box ? Object.assign({}, r.box) : null;
  k.coast = null; k.water = null; k.over = null;
  osmPaint(); cmapPaint();
  toast(r.box ? 'Box kept for this map.' : 'Box cleared.');
}

async function osmBoxFile(input){
  const f = input.files && input.files[0];
  if(!f) return;
  osmBoxPost({text: await f.text()});
}

function osmBoxDownload(){
  const k = state.osm;
  if(!k.st || !k.st.file) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([k.st.file], {type: 'text/plain'}));
  a.download = 'bbox_coords.txt';
  a.click();
}

/* ---------- the coastline ---------- */

async function osmCoast(){
  const k = state.osm, c = state.cmap;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.job = 'osm' + Date.now(); k.pct = 0; k.label = '';
  osmPaint();
  const poll = setInterval(async () => {
    try{
      const p = await api.get(`/api/progress?job=${enc(k.job)}`);
      if(p && p.label){ k.pct = p.pct; k.label = p.label; osmPaint(); }
    }catch(e){}
  }, 800);
  let r;
  try{ r = await api.post('/api/osm/coast', {mod: c.mod, job: k.job},
                          {label: 'fetching the coastline'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ clearInterval(poll); }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; osmPaint(); return; }
  k.coast = r.coast;
  osmBuildOver();
  osmPaint(); cmapPaint();
}

async function osmCoastApply(){
  const k = state.osm;
  if(!k || !k.coast || !state.cpaint) return;
  if(!confirm(`Make ${k.coast.to_sea} land tiles on the water side of the coastline sea?\n\n`
    + 'It is one stroke of the paint tool: regions, heights and ground types together, '
    + 'in this map’s own sea colours, settlements and ports left alone. The Paint '
    + 'tab’s Undo takes it back, and nothing is written until you save there.')) return;
  const r = await cpaintPost('osm_coast', {});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(r.tiles ? `${r.tiles} tiles made sea${r.note ? ' - ' + r.note : ''}. Save it from Paint.`
                : (r.note || 'Nothing to change.'), 7000);
  osmCoast();                       // the red goes where it became sea
}

/* ---------- lakes, lagoons and seas (87c) ---------- */

function osmWaterBody(){
  const k = state.osm;
  return {kinds: Object.keys(k.wkinds).filter(x => k.wkinds[x]), min_tiles: k.wmin};
}

async function osmWater(){
  const k = state.osm, c = state.cmap;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.job = 'osmw' + Date.now(); k.pct = 0; k.label = '';
  osmPaint();
  const poll = setInterval(async () => {
    try{
      const p = await api.get(`/api/progress?job=${enc(k.job)}`);
      if(p && p.label){ k.pct = p.pct; k.label = p.label; osmPaint(); }
    }catch(e){}
  }, 800);
  let r;
  try{ r = await api.post('/api/osm/water', Object.assign({mod: c.mod, job: k.job}, osmWaterBody()),
                          {label: 'fetching the water'}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ clearInterval(poll); }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; osmPaint(); return; }
  k.water = r.water;
  osmBuildOver();
  osmPaint(); cmapPaint();
}

async function osmWaterApply(){
  const k = state.osm;
  if(!k || !k.water || !state.cpaint) return;
  if(!confirm(`Make ${k.water.to_sea} land tiles inside OpenStreetMap’s water sea?\n\n`
    + 'It is one stroke of the paint tool, like the coastline: regions, heights and ground types '
    + 'together, in this map’s own sea colours, islands kept dry, settlements and ports left alone. '
    + 'The Paint tab’s Undo takes it back, and nothing is written until you save there.')) return;
  const r = await cpaintPost('osm_water', osmWaterBody());
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(r.tiles ? `${r.tiles} tiles made sea. Save it from Paint.` : (r.note || 'Nothing to change.'), 7000);
  osmWater();                       // the blue goes where it became sea
}

function osmWaterSet(kind, on){
  const k = state.osm;
  k.wkinds[kind] = on;
  k.water = null; osmBuildOver(); osmPaint(); cmapPaint();
}

/* ---------- places ---------- */

async function osmSearch(){
  const k = state.osm, c = state.cmap;
  const el = document.getElementById('osmQ');
  if(el) k.q = el.value;
  if(!k.q.trim() || k.busy) return;
  k.busy = true; k.err = ''; osmPaint();
  let r;
  try{ r = await api.get(`/api/osm/search?mod=${enc(c.mod)}&q=${enc(k.q)}`,
                         {label: 'searching OpenStreetMap'}); }
  catch(e){ r = {error: errText(e)}; }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; k.results = null; }
  else k.results = r.results || [];
  osmPaint();
}

function osmGo(i){
  const p = state.osm.results[i];
  if(p && p.on_map) cmapGoTile([p.x, p.y], 6);
}

//: A name the engine can carry: letters, digits and underscores
const osmKey = s => (s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
  .replace(/\s+/g, '_').replace(/[^A-Za-z0-9_]/g, '') || 'Place';

async function osmNewRegion(i){
  const p = state.osm.results[i], pt = state.cpaint;
  if(!p || !pt) return;
  if(p.on_map) cmapGoTile([p.x, p.y], 6);
  await cmapCreateRegion();
  if(!pt.wiz) return;
  const key = osmKey(p.name);
  Object.assign(pt.wiz, {name: key + '_Province', settlement: key,
                         shown: p.name, settlement_shown: p.name});
  cpaintPaint();
  toast(`The new region is filled in from ${p.name}. Check it, open it, then paint `
        + 'its boundary from Real world or by hand.', 7000);
}

async function osmBoundary(i){
  const k = state.osm, p = k.results[i];
  const el = document.getElementById('osmTarget');
  if(el) k.target = el.value.trim();
  const region = k.target || (state.cpaint && state.cpaint.st.new_region
                              && state.cpaint.st.new_region.name) || '';
  if(!region){ toast('Name the region the boundary is painted onto.', 5000); return; }
  const r = await cpaintPost('osm_boundary', {region, name: p.name, lat: p.lat,
                                              lon: p.lon, osm_type: p.osm_type,
                                              osm_id: p.osm_id});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(`${r.tiles} tiles of ${p.name} painted onto ${region}. Save it from Paint.`, 7000);
}

/* ---------- the panel ---------- */

function osmPaint(){
  const el = document.getElementById('cmOsm');
  if(!el) return;
  el.innerHTML = osmHtml();
}

function osmHtml(){
  const k = state.osm, c = state.cmap;
  if(!k || !c) return '';
  const head = `<div class="cmrow cmhdr" onclick="osmToggle()">
      <b>Real world</b> <span class="count">OpenStreetMap behind the map</span>
      <span class="count">${k.open ? '▾' : '▸'}</span>
    </div>`;
  if(!k.open) return head;
  if(!k.st) return head + `<div class="count">${k.busy ? 'Reading…' : esc(k.err || '')}</div>`;
  const s = k.st.settings;
  if(!s.enabled) return head + `<div class="bnote">${docPoints(
      'Off. This is the one part of the toolkit that uses the internet, so it waits to be turned on.', [
      'It sends the map’s real-world box, the numbers of the map tiles it draws, and the words you search for. Nothing about the mod.',
      `To: ${esc(s.tiles[0])}, ${esc(s.overpass[0])} and ${esc(s.nominatim)}. Settings, Real-world map, lists them all and can change them.`,
      'Tiles are kept on disk for 30 days, and searches are sent at most once a second, as OpenStreetMap asks.'])}</div>
    <button onclick="openSettings()">⚙ Open Settings to turn it on</button>`;
  const b = k.box || {north: '', south: '', west: '', east: '', rotation: ''};
  const box = ['north', 'south', 'west', 'east', 'rotation'].map(f => `<label style="flex:1 1 90px">${f}
      <input type="number" step="${f === 'rotation' ? 1 : 0.01}" value="${esc(osmNum(b[f] ?? (f === 'rotation' && k.box ? 0 : ''), f === 'rotation' ? 1 : 6))}"
        onchange="osmBoxSet('${f}',this.value)"></label>`).join('');
  // 87a: how the box sits on this map - the size of a tile, and any stretch
  const W = c.man.width, H = c.man.height;
  let shape = '';
  if(osmBoxOk(k.box)){
    const [ew, ns] = osmKmPerTile(k.box, W, H), st = osmStretch(k.box, W, H);
    const f = v => v >= 10 ? v.toFixed(0) : v.toFixed(1);
    shape = `<div class="count">One tile: ${f(ew)} km east-west, ${f(ns)} km north-south.
      ${Math.abs(st) < 0.005 ? '' : `<span class="w-warn">The box stretches the map
      ${Math.abs(st * 100).toFixed(1)}% ${st > 0 ? 'wider' : 'taller'} than the real ground:
      the world picker can give it the map’s shape.</span>`}</div>`;
  }
  const kept = k.st.box_from === 'kept' ? 'kept for this map'
    : k.st.box_from === 'file' ? 'read from bbox_coords.txt beside the map' : 'not set yet';
  const co = k.coast;
  const res = k.results || [];
  const regions = (c.man.regions || []).filter(r => r.name).map(r => r.name).sort();
  return `${head}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="bsec"><h4>The box <span class="count">${esc(kept)}</span></h4>
      <div class="cmbar2"><button class="primary" onclick="owpOpen()">🌍 Pick it on a world map…</button></div>
      <div class="brow" style="flex-wrap:wrap">${box}</div>
      ${shape}
      <div class="cmbar2">
        <button class="primary" onclick="osmBoxPost({box: state.osm.box})"
          ${osmBoxOk(k.box) ? '' : 'disabled'}>Keep</button>
        <label class="btnlike">Import bbox_coords.txt…
          <input type="file" accept=".txt" style="display:none" onchange="osmBoxFile(this)"></label>
        <button onclick="osmBoxDownload()" ${k.st.file ? '' : 'disabled'}>Export</button>
        <button onclick="osmBoxPost({clear: true})" ${k.st.box_from === 'kept' ? '' : 'disabled'}>Clear</button>
      </div>
      <div class="count">Where the map’s edges are in the real world, and how far the map is
        turned (degrees, clockwise). Change a number and the backdrop moves at once; Keep saves
        it in the toolkit, not in the mod.</div>
    </div>
    <div class="bsec"><h4>Backdrop</h4>
      <label class="chk"><input type="checkbox" ${k.show ? 'checked' : ''}
        onchange="state.osm.show=this.checked;cmapPaint()"> Show the real world over the map</label>
      <label style="display:block">Opacity <input type="range" min="0.1" max="1" step="0.05" value="${k.alpha}"
        oninput="state.osm.alpha=+this.value;cmapPaint()"></label>
      ${osmStyleHtml()}
      <div class="cmbar2"><label>Save a picture of the box
          <select onchange="state.osm.picW=+this.value">${[1024, 2048, 4096].map(w =>
            `<option value="${w}" ${w === k.picW ? 'selected' : ''}>${w} px wide</option>`).join('')}</select></label>
        <button onclick="osmPicture('png')" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}>PNG</button>
        <button onclick="osmPicture('svg')" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}>SVG</button></div>
      <div class="count">The style above, cut to the box and turned with it, in the map’s own
        frame: a reference to paint from in another program.</div>
    </div>
    <div class="bsec"><h4>Coastline</h4>
      <div class="cmbar2"><button onclick="osmCoast()" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}
        >${k.busy && k.label && !k.job.startsWith('osmw') ? esc(k.label) : co ? '↺ Again' : 'Fetch the real coastline'}</button></div>
      ${co ? `<div class="count">${co.way_count} coastline ways: ${co.line} tiles of line
          (<span style="color:#00f0ff">cyan</span>), ${co.to_sea} land tiles on the water side
          (<span style="color:#ff4646">red</span>), ${co.land_side_sea} sea tiles on the land side
          (lakes among them; left as they are).</div>
        <label class="chk"><input type="checkbox" ${k.showCoast ? 'checked' : ''}
          onchange="state.osm.showCoast=this.checked;cmapPaint()"> Show it on the map</label>
        ${co.leaks ? `<div class="w-warn">The coastline has a gap: the water side reaches ${co.leak}
          tiles that are land by its own reckoning, so it cannot be filled. Use the line as a guide
          for the water brush.</div>`
        : `<div class="cmbar2"><button class="primary" onclick="osmCoastApply()"
            ${co.to_sea ? '' : 'disabled'}>Make the red tiles sea</button>
            <span class="count">one stroke; the Paint tab undoes and saves it</span></div>`}` : ''}
    </div>
    <div class="bsec"><h4>Lakes, lagoons and seas</h4>
      <div class="brow" style="flex-wrap:wrap">${[['sea', 'seas'], ['lagoon', 'lagoons'], ['lake', 'lakes']].map(([w, t]) =>
        `<label class="chk"><input type="checkbox" ${k.wkinds[w] ? 'checked' : ''}
          onchange="osmWaterSet('${w}',this.checked)"> ${t}</label>`).join('')}</div>
      <label>Leave out any smaller than <input type="number" min="0" max="10000" value="${k.wmin}" style="width:70px"
        onchange="state.osm.wmin=Math.max(0,+this.value||0);state.osm.water=null;osmBuildOver();osmPaint();cmapPaint()"> tiles</label>
      <div class="cmbar2"><button onclick="osmWater()" ${k.busy || !osmBoxOk(k.box) || !osmWaterBody().kinds.length ? 'disabled' : ''}
        >${k.busy && k.label && k.job.startsWith('osmw') ? esc(k.label) : k.water ? '↺ Again' : 'Fetch the water'}</button></div>
      ${k.water ? `<div class="count">${k.water.rings} water outline(s)${Object.entries(k.water.by_kind || {}).map(([w, n]) =>
          ` (${n} ${w})`).join('')}, ${k.water.holes} island(s) kept dry, ${k.water.small} too small and left out:
          ${k.water.to_sea} land tiles inside (<span style="color:#3c6eff">blue</span>), ${k.water.sea_already} sea already.</div>
        <div class="cmbar2"><button class="primary" onclick="osmWaterApply()" ${k.water.to_sea ? '' : 'disabled'}>Make the blue tiles sea</button>
          <span class="count">one stroke; the Paint tab undoes and saves it</span></div>` : ''}
      <div class="count">Mylae’s water step: OpenStreetMap’s sea, lagoon and lake outlines made sea on
        the map. An inland lake is sea to the engine, as the Caspian is.</div>
    </div>
    <div class="bsec"><h4>Find a place</h4>
      <div class="brow"><input id="osmQ" value="${esc(k.q)}" placeholder="a town, a region, a country"
        onkeydown="if(event.key==='Enter')osmSearch()">
        <button onclick="osmSearch()" ${k.busy ? 'disabled' : ''}>Search</button></div>
      ${res.length ? `<label>Paint boundaries onto
          <input id="osmTarget" list="osmRegions" value="${esc(k.target)}" placeholder="a region"
            onchange="state.osm.target=this.value.trim()"></label>
        <datalist id="osmRegions">${regions.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
        ${res.map((p, i) => `<div class="osmres">
          <div><b>${esc(p.name)}</b> <span class="count">${esc(p.kind)}${p.admin_level
            ? ' ' + p.admin_level : ''}${p.on_map ? ` · tile ${p.x}, ${p.y}` : ' · off the map'}</span></div>
          <div class="count">${esc(p.display)}</div>
          <div class="cmbar2">
            <button onclick="osmGo(${i})" ${p.on_map ? '' : 'disabled'}>Go</button>
            <button onclick="osmNewRegion(${i})" ${p.on_map ? '' : 'disabled'}>New region here</button>
            <button onclick="osmBoundary(${i})">Paint its boundary</button>
          </div></div>`).join('')}`
      : k.results ? '<div class="count">Nothing found inside the box.</div>' : ''}
    </div>`;
}
