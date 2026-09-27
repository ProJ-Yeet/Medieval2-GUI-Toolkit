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
          htags: null, hist: null, hq: '', hshow: true, hpick: -1,
          chunks: null, cpick: 0, cshow: true, bpic: false,
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
  if(state.osm === k && k.st && k.box) osmChunksLoad(false);
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
  return (s && s[osmStyle()]) || {name: 'OpenStreetMap', max_zoom: 19, credit: tt('osmmap.openstreetmap_contributors')};
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
  if(k.hshow && k.hist) osmDrawSites(x, s0, t0, s1, t1);
  if(k.cshow && k.chunks && k.chunks[k.cpick]) osmDrawChunks(x);
}

//: 87g: the chunks of the fetch picked, each its box on the map (turned with
//: the map), numbered at its middle; a failed one filled red
function osmDrawChunks(x){
  const k = state.osm, c = state.cmap, f = k.chunks[k.cpick];
  const W = c.man.width, H = c.man.height, b = k.box;
  x.save();
  x.lineWidth = 1.5;
  x.textAlign = 'center'; x.textBaseline = 'middle';
  x.font = 'bold 13px sans-serif';
  for(const ch of f.chunks){
    const pts = [[ch.north, ch.west], [ch.north, ch.east], [ch.south, ch.east], [ch.south, ch.west]]
      .map(([la, lo]) => { const [fx, fy] = osmToTile(b, W, H, la, lo); return [cmapX(fx + 0.5), cmapY(fy + 0.5)]; });
    x.beginPath();
    pts.forEach(([px, py], i) => i ? x.lineTo(px, py) : x.moveTo(px, py));
    x.closePath();
    if(!ch.ok){ x.fillStyle = 'rgba(255,40,40,0.28)'; x.fill(); }
    x.strokeStyle = ch.ok ? 'rgba(40,120,255,0.85)' : 'rgba(255,40,40,0.95)';
    x.stroke();
    const mx = pts.reduce((a, p) => a + p[0], 0) / 4, my = pts.reduce((a, p) => a + p[1], 0) / 4;
    x.lineWidth = 3; x.strokeStyle = '#000'; x.strokeText(String(ch.n), mx, my);
    x.fillStyle = ch.ok ? '#fff' : '#ff6b6b'; x.fillText(String(ch.n), mx, my);
    x.lineWidth = 1.5;
  }
  x.restore();
}

//: 87f: each historic site a square in its tag's colour on the tile it names,
//: big enough to see at any zoom, outlined so it shows on any ground
function osmDrawSites(x, s0, t0, s1, t1){
  const k = state.osm, v = state.cmap.view;
  const r = Math.max(2.5, Math.min(6, v.zoom * 0.4));
  x.save();
  x.lineWidth = 1;
  x.strokeStyle = '#000';
  k.hist.sites.forEach((s, i) => {
    if(!s.on_map || s.x < s0 - 1 || s.x > s1 || s.y < t0 - 1 || s.y > t1) return;
    const cx = cmapX(s.x + 0.5), cy = cmapY(s.y + 0.5);
    x.fillStyle = `rgb(${s.colour.join(',')})`;
    const rr = i === k.hpick ? r + 3 : r;
    x.fillRect(cx - rr, cy - rr, 2 * rr, 2 * rr);
    x.strokeRect(cx - rr, cy - rr, 2 * rr, 2 * rr);
  });
  x.restore();
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
  return `<label style="display:block">${tt('osmmap.style')} <select onchange="osmSetStyle(this.value)">${Object.entries(styles).map(([id, s]) =>
      `<option value="${id}" ${id === k.style ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select></label>
    ${k.style === 'ohm' ? `<div class="brow"><input type="range" class="osmYearR" min="${lo}" max="${hi}" step="1"
        value="${Math.max(lo, Math.min(hi, k.year))}" oninput="osmSetYear(this.value)" style="flex:1">
        <input type="number" class="osmYearN" min="1" max="2100" value="${k.year}" style="width:70px"
          onchange="osmSetYear(this.value)"> ${tt('osmmap.ad')}</div>
      <div class="cmbar2">${(st.ohm_eras || []).map(y =>
        `<button class="${y === k.year ? 'primary' : ''}" onclick="osmSetYear(${y});osmPaint();if(state.owp&&state.owp.open)owpSide()">${y}</button>`).join('')}</div>
      <div class="count">${tt('osmmap.the_historical_borders_as_openhistoricalmap_has')}</div>` : ''}
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
      || tt('osmmap.reference',{x:fmt});
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
  k.coast = null; k.water = null; k.over = null; k.hist = null; k.chunks = null; k.cpick = 0;
  osmPaint(); cmapPaint();
  toast(r.box ? tt('osmmap.box_kept_for_this_map') : tt('osmmap.box_cleared'));
  if(r.box) osmChunksLoad(false);
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
                          {label: tt('osmmap.fetching_the_coastline')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ clearInterval(poll); }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; osmPaint(); return; }
  k.coast = r.coast;
  osmBuildOver();
  osmPaint(); cmapPaint();
  osmChunksLoad(true);
}

async function osmCoastApply(){
  const k = state.osm;
  if(!k || !k.coast || !state.cpaint) return;
  if(!confirm(tt('osmmap.make_land_tiles_on_the_water',{to_sea:k.coast.to_sea})
    + tt('osmmap.it_is_one_stroke_of_the')
    + tt('osmmap.in_this_maps_own_sea_colours')
    + tt('osmmap.tabs_undo_takes_it_back_and'))) return;
  const r = await cpaintPost('osm_coast', {});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(r.tiles ? tt('osmmap.tiles_made_sea_save_it_from',{tiles:r.tiles,x:r.note ? ' - ' + r.note : ''})
                : (r.note || tt('osmmap.nothing_to_change')), 7000);
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
                          {label: tt('osmmap.fetching_the_water')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ clearInterval(poll); }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; osmPaint(); return; }
  k.water = r.water;
  osmBuildOver();
  osmPaint(); cmapPaint();
  osmChunksLoad(true);
}

async function osmWaterApply(){
  const k = state.osm;
  if(!k || !k.water || !state.cpaint) return;
  if(!confirm(tt('osmmap.make_land_tiles_inside_openstreetmaps_water',{to_sea:k.water.to_sea})
    + tt('osmmap.it_is_one_stroke_of_the_2')
    + tt('osmmap.together_in_this_maps_own_sea')
    + tt('osmmap.the_paint_tabs_undo_takes_it'))) return;
  const r = await cpaintPost('osm_water', osmWaterBody());
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(r.tiles ? tt('osmmap.tiles_made_sea_save_it_from_2',{tiles:r.tiles}) : (r.note || tt('osmmap.nothing_to_change')), 7000);
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
                         {label: tt('osmmap.searching_openstreetmap')}); }
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
  .replace(/\s+/g, '_').replace(/[^A-Za-z0-9_]/g, '') || tt('osmmap.place');

async function osmNewRegion(i){
  return osmNewRegionAt(state.osm.results[i]);
}

async function osmNewRegionAt(p){
  const pt = state.cpaint;
  if(!p || !pt) return;
  if(p.on_map) cmapGoTile([p.x, p.y], 6);
  await cmapCreateRegion();
  if(!pt.wiz) return;
  const key = osmKey(p.name);
  Object.assign(pt.wiz, {name: key + '_Province', settlement: key,
                         shown: p.name, settlement_shown: p.name});
  cpaintPaint();
  toast(tt('osmmap.the_new_region_is_filled_in',{name:p.name})
        + tt('osmmap.its_boundary_from_real_world_or'), 7000);
}

async function osmBoundary(i){
  const k = state.osm, p = k.results[i];
  const el = document.getElementById('osmTarget');
  if(el) k.target = el.value.trim();
  const region = k.target || (state.cpaint && state.cpaint.st.new_region
                              && state.cpaint.st.new_region.name) || '';
  if(!region){ toast(tt('osmmap.name_the_region_the_boundary_is'), 5000); return; }
  const r = await cpaintPost('osm_boundary', {region, name: p.name, lat: p.lat,
                                              lon: p.lon, osm_type: p.osm_type,
                                              osm_id: p.osm_id});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  cpaintApply(r.changed || {});
  cpaintPaint();
  toast(tt('osmmap.tiles_of_painted_onto_save_it',{tiles:r.tiles,name:p.name,region}), 7000);
}

/* ---------- historic sites (87f) ---------- */

//: The tags ticked: what was ticked last, else his four commonest
function osmHistTags(){
  const k = state.osm;
  if(!k.htags) k.htags = ['historic=castle', 'historic=fort', 'historic=monastery', 'historic=tower'];
  return k.htags;
}

function osmHistTick(tag, on){
  const k = state.osm, t = osmHistTags().filter(x => x !== tag);
  if(on) t.push(tag);
  k.htags = t;
}

//: The 21 tags in his two groups, each with its colour; the same boxes on the
//: panel and the world picker. `repaint` is what a tick redraws.
function osmHistTagsHtml(repaint){
  const k = state.osm, all = (k.st && k.st.historic_tags) || [], on = osmHistTags();
  const groups = [...new Set(all.map(t => t.group))];
  return groups.map(g => {
    const tags = all.filter(t => t.group === g), n = tags.filter(t => on.includes(t.tag)).length;
    return `<details class="osmhg"><summary>${tt('osmmap.of_ticked',{x:esc(g),x2:n,tags_n:tags.length})}</summary>
      <div class="brow" style="flex-wrap:wrap;gap:2px 10px">${tags.map(t => `<label class="chk" title="${esc(t.tag)}: ${esc(t.desc)}">
        <input type="checkbox" ${on.includes(t.tag) ? 'checked' : ''}
          onchange="osmHistTick('${t.tag}',this.checked);${repaint}">
        <span class="osmsw" style="background:rgb(${t.colour.join(',')})"></span>${esc(t.label)}</label>`).join('')}</div>
    </details>`;
  }).join('');
}

async function osmHist(){
  const k = state.osm, c = state.cmap;
  if(!k || k.busy || !osmHistTags().length) return;
  k.busy = true; k.err = ''; k.job = 'osmh' + Date.now(); k.pct = 0; k.label = '';
  osmPaint();
  const poll = setInterval(async () => {
    try{
      const p = await api.get(`/api/progress?job=${enc(k.job)}`);
      if(p && p.label){ k.pct = p.pct; k.label = p.label; osmPaint(); }
    }catch(e){}
  }, 800);
  let r;
  try{ r = await api.post('/api/osm/historic', {mod: c.mod, job: k.job, tags: osmHistTags()},
                          {label: tt('osmmap.fetching_the_historic_sites')}); }
  catch(e){ r = {error: errText(e)}; }
  finally{ clearInterval(poll); }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ k.err = r.error; osmPaint(); return; }
  k.hist = r; k.hpick = -1;
  osmPaint(); cmapPaint();
  osmChunksLoad(true);
}

//: The sites the list shows: on the map, matching the filter, in tag order
function osmHistRows(){
  const k = state.osm, q = (k.hq || '').trim().toLowerCase();
  return k.hist.sites.map((s, i) => [s, i]).filter(([s]) => s.on_map
    && (!q || s.name.toLowerCase().includes(q) || s.label.toLowerCase().includes(q)));
}

function osmSiteGo(i){
  const k = state.osm, s = k.hist && k.hist.sites[i];
  if(!s || !s.on_map) return;
  k.hpick = i;
  cmapGoTile([s.x, s.y], 8);
  osmPaint();
}

//: A fort or a watchtower on the site's tile: 22a's form, filled in and planned,
//: so its checks and its Save are the ones every fort goes through
async function osmSiteObject(i, kind){
  const k = state.osm, s = k.hist && k.hist.sites[i];
  if(!s || !s.on_map || typeof cftPlace !== 'function') return;
  osmSiteGo(i);
  if(!state.cft) cftOpen();
  const f = state.cft;
  if(!f) return;
  f.open = true;
  if(!f.d) await cftLoad();
  if(state.cft !== f) return;
  cftPlace(kind, [s.gx, s.gy]);
  // asked for, so shown: not 28a's once-per-map switch meant for map clicks
  const where = typeof cmapSubOf === 'function' && cmapSubOf('cmForts');
  if(where) cmapSub(where.tab, where.sub);
  toast(tt('osmmap.a_planned_on_where_stands',{kind,gx:s.gx,gy:s.gy,x:s.name || 'the ' + s.label.toLowerCase()})
        + tt('osmmap.check_it_and_save_it_from'), 7000);
}

function osmSiteRegion(i){
  const s = state.osm.hist && state.osm.hist.sites[i];
  if(s) osmNewRegionAt({name: s.name || s.label, x: s.x, y: s.y, on_map: s.on_map});
}

function osmHistSave(){
  const k = state.osm;
  if(!k.hist || !k.hist.text) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([k.hist.text], {type: 'text/plain'}));
  a.download = 'historic_features.txt';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

//: The filter box: redrawn after a pause, the caret put back where it was
let _osmHq = 0;
function osmHistFilter(v){
  state.osm.hq = v;
  clearTimeout(_osmHq);
  _osmHq = setTimeout(() => {
    osmPaint();
    const e = document.getElementById('osmHq');
    if(e){ e.focus(); e.setSelectionRange(e.value.length, e.value.length); }
  }, 250);
}

//: The most rows the list draws; the filter narrows the rest
const OSM_HIST_ROWS = 150;

function osmHistHtml(){
  const k = state.osm, h = k.hist;
  const busy = k.busy && k.label && k.job.startsWith('osmh');
  const btn = `<div class="cmbar2"><button onclick="osmHist()" ${k.busy || !osmBoxOk(k.box) || !osmHistTags().length ? 'disabled' : ''}
      >${busy ? esc(k.label) : h ? tt('osmmap.again') : tt('osmmap.fetch_the_sites')}</button></div>`;
  if(!h) return `${osmHistTagsHtml('osmPaint()')}${btn}
    <div class="count">${tt('osmmap.mylaes_historic_features_castles_forts_monasteri')}</div>`;
  const all = k.st.historic_tags || [];
  const lab = t => (all.find(x => x.tag === t) || {}).label || t;
  const rows = osmHistRows(), shown = rows.slice(0, OSM_HIST_ROWS);
  const counts = Object.entries(h.counts || {}).map(([t, n]) => `${n} ${esc(lab(t))}`).join(', ');
  const act = (i, s, kind, txt) => `<button class="${s.suggest === kind ? 'primary' : ''}"
      onclick="${kind === 'settlement' ? `osmSiteRegion(${i})` : `osmSiteObject(${i},'${kind}')`}">${txt}</button>`;
  return `${osmHistTagsHtml('osmPaint()')}${btn}
    <div class="count">${tt('osmmap.on_the_map',{counts:counts || tt('osmmap.nothing'),off_map:h.off_map ? tt('osmmap.in_the_boxs_corners_off_the',{off_map:h.off_map}) : ''})}</div>
    <label class="chk"><input type="checkbox" ${k.hshow ? 'checked' : ''}
      onchange="state.osm.hshow=this.checked;cmapPaint()"> ${tt('osmmap.show_them_on_the_map')}</label>
    <div class="cmbar2"><button onclick="osmHistSave()">${tt('osmmap.save_historic_features_txt')}</button>
      <span class="count">${tt('osmmap.his_format_a_line_a_site')}</span></div>
    <input id="osmHq" value="${esc(k.hq)}" placeholder="${ttA('osmmap.filter_by_name_or_kind')}" oninput="osmHistFilter(this.value)">
    ${shown.map(([s, i]) => `<div class="osmres">
        <div><span class="osmsw" style="background:rgb(${s.colour.join(',')})"></span><b>${esc(s.name || tt('common.no_name'))}</b>
          <span class="count">${tt('osmmap.tile',{label:esc(s.label),gx:s.gx,gy:s.gy})}</span></div>
        <div class="cmbar2"><button class="${i === k.hpick ? 'primary' : ''}" onclick="osmSiteGo(${i})">${tt('osmmap.go')}</button>
          ${act(i, s, 'fort', tt('osmmap.fort_here'))}${act(i, s, 'watchtower', tt('osmmap.watchtower_here'))}
          ${act(i, s, 'settlement', tt('osmmap.new_region_here'))}</div></div>`).join('')}
    ${rows.length > shown.length ? `<div class="count">${tt('osmmap.more_narrow_them_with_the_filter',{n:rows.length - shown.length})}</div>` : ''}`;
}

/* ---------- the Overpass chunks (87g) ---------- */

//: The fetches kept for this box, off disk (nothing is sent). After a fetch,
//: `fresh` says so when some of its chunks failed.
async function osmChunksLoad(fresh){
  const k = state.osm, c = state.cmap;
  if(!k || !c) return;
  let r;
  try{ r = await api.get(`/api/osm/chunks?mod=${enc(c.mod)}`); }
  catch(e){ return; }
  if(state.osm !== k || !r || r.error) return;
  k.chunks = r.fetches || [];
  // the newest fetch shows; one with a failed chunk before one without
  const bad = k.chunks.findIndex(f => f.failed);
  k.cpick = fresh && bad >= 0 ? bad : Math.min(k.cpick, Math.max(0, k.chunks.length - 1));
  if(fresh && k.chunks[0] && k.chunks[0].failed)
    toast(tt('osmmap.of_chunks_of_the',{x:k.chunks[0].failed,n:k.chunks[0].chunks.length,x2:k.chunks[0].label})
          + tt('osmmap.fetch_got_no_answer_they_are'), 9000);
  osmPaint(); cmapPaint();
}

function osmChunkPickFetch(i){
  state.osm.cpick = +i || 0;
  osmPaint(); cmapPaint();
}

//: One chunk asked again alone, and what the panel shows fetched again off
//: disk with it merged in
async function osmChunkAgain(n){
  const k = state.osm, f = k.chunks && k.chunks[k.cpick];
  if(!f || k.busy) return;
  k.busy = true; k.err = ''; osmPaint();
  let r;
  try{ r = await api.post('/api/osm/refetch', {kind: f.kind, key: f.key, n},
                          {label: tt('osmmap.fetching_chunk_again',{x:n})}); }
  catch(e){ r = {error: errText(e)}; }
  if(state.osm !== k) return;
  k.busy = false;
  if(r.error){ toast('✗ ' + r.error, 8000); osmPaint(); return; }
  const ch = r.chunks[n - 1];
  k.chunks[k.cpick] = r;
  osmPaint(); cmapPaint();
  if(!ch.ok){ toast(tt('osmmap.chunk_failed_again',{x:n,error:ch.error}), 9000); return; }
  toast(tt('osmmap.chunk_found_new_to_this_fetch',{x:n,count:ch.count,added:r.added}), 6000);
  if(!r.added) return;
  if(f.kind === 'coast' && k.coast) osmCoast();
  else if(f.kind === 'polygons' && f.label === 'water' && k.water) osmWater();
  else if(f.kind === 'historic' && k.hist) osmHist();
  else if(f.kind !== 'coast' && f.kind !== 'historic' && f.label !== 'water')
    toast(tt('osmmap.chunk_new_plan_it_again_on',{x:n,added:r.added}), 7000);
}

//: The pin's answer: the chunk under the clicked tile, a failed one first
function osmChunkPicked(game, tile){
  const k = state.osm, c = state.cmap, f = k.chunks && k.chunks[k.cpick];
  if(!f || !osmBoxOk(k.box)) return;
  const [lat, lon] = osmToGeo(k.box, c.man.width, c.man.height, tile[0], tile[1]);
  const inside = f.chunks.filter(ch => ch.south <= lat && lat <= ch.north && ch.west <= lon && lon <= ch.east);
  const ch = inside.find(x => !x.ok) || inside[0];
  if(!ch){ toast(tt('osmmap.no_chunk_of_that_fetch_covers'), 5000); return; }
  osmChunkAgain(ch.n);
}

function osmChunksHtml(){
  const k = state.osm, fs = k.chunks || [];
  if(!fs.length) return `<div class="count">${tt('osmmap.nothing_fetched_from_overpass_for_this')}</div>`;
  const f = fs[Math.min(k.cpick, fs.length - 1)];
  const when = t => new Date(t * 1000).toLocaleString();
  const bad = f.chunks.filter(ch => !ch.ok);
  return `<label style="display:block">${tt('osmmap.fetch')} <select onchange="osmChunkPickFetch(this.value)">${fs.map((x, i) =>
      `<option value="${i}" ${i === k.cpick ? 'selected' : ''}>${tt('osmmap.chunks',{label:esc(x.label),chunks_n:x.chunks.length,failed:x.failed
        ? tt('osmmap.failed',{failed:x.failed}) : ''})}</option>`).join('')}</select></label>
    <div class="count">${tt('osmmap.chunks_things_found_asked',{chunks_n:f.chunks.length,found:f.found,x:esc(when(f.when)),x2:f.failed
      ? tt('osmmap.got_no_answer_so_what_is',{failed:f.failed,x:f.failed === 1 ? 'it' : 'them'}) : '.'})}</div>
    <label class="chk"><input type="checkbox" ${k.cshow ? 'checked' : ''}
      onchange="state.osm.cshow=this.checked;cmapPaint()"> ${tt('osmmap.show_them_on_the_map_numbered')}</label>
    <div class="cmbar2">${tt('osmmap.or_click_a_chunk_on_the',{x:typeof cpinButton === 'function' ? cpinButton(tt('osmmap.a_chunk_to_fetch_again'), 'osmChunkPicked', []) : ''})}</div>
    ${bad.map(ch => `<div class="osmres">${tt('osmmap.chunk_to_n_to_e',{ch:ch.n,x:ch.south.toFixed(2),x2:ch.north.toFixed(2),x3:ch.west.toFixed(2),x4:ch.east.toFixed(2)})}
        <div class="w-bad">${esc(ch.error)}</div>
        <div class="cmbar2"><button class="primary" onclick="osmChunkAgain(${ch.n})" ${k.busy ? 'disabled' : ''}>${tt('osmmap.fetch_it_again')}</button></div></div>`).join('')}
    <details><summary class="count">${tt('osmmap.every_chunk')}</summary>${f.chunks.map(ch => `<div class="brow" style="gap:6px">
        <span style="min-width:24px">${ch.n}</span><span class="count" style="flex:1">${ch.ok ? `${ch.count} found` : 'failed'}</span>
        <button onclick="osmChunkAgain(${ch.n})" ${k.busy ? 'disabled' : ''}>↺</button></div>`).join('')}</details>`;
}

/* ---------- the map bundle (87h) ---------- */

//: The zip in Mylae's layout, made by Python from the files on disk
async function osmBundle(){
  const k = state.osm, c = state.cmap;
  if(!k || !c || k.busy) return;
  const q = `mod=${enc(c.mod)}` + (k.bpic && osmBoxOk(k.box)
    ? `&picture=${enc(k.style)}&year=${k.year}&width=${k.picW}` : '');
  k.busy = true; osmPaint();
  try{
    const r = await fetch(`/api/osm/bundle?${q}`);
    if(!r.ok){ toast('✗ ' + (await r.text()).slice(0, 300), 8000); return; }
    const name = ((r.headers.get('Content-Disposition') || '').match(/filename="([^"]+)"/) || [])[1]
      || 'm2tw_map_layers.zip';
    const n = r.headers.get('X-Bundle-Files') || '?', notes = r.headers.get('X-Bundle-Notes') || '';
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await r.blob());
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    toast(tt('osmmap.files',{name,x:n,x2:notes ? ' ' + notes + '.' : ''}), notes ? 9000 : 5000);
  }catch(e){ toast('✗ ' + errText(e), 8000); }
  finally{ k.busy = false; osmPaint(); }
}

function osmBundleHtml(){
  const k = state.osm, pt = state.cpaint;
  const dirty = pt && pt.st && (pt.st.dirty || []).length;
  return `${dirty ? `<div class="w-warn">${tt('osmmap.the_paint_tab_has_changes_not')}</div>` : ''}
    <label class="chk"><input type="checkbox" ${k.bpic ? 'checked' : ''} ${osmBoxOk(k.box) ? '' : 'disabled'}
      onchange="state.osm.bpic=this.checked"> ${tt('osmmap.with_a_reference_picture_the_backdrop',{picW:k.picW})}</label>
    <div class="cmbar2"><button class="primary" onclick="osmBundle()" ${k.busy ? 'disabled' : ''}>${tt('osmmap.export_the_map_bundle')}</button></div>
    <div class="count">${tt('osmmap.mylaes_layout_the_maps_layers_as')}</div>`;
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
      ${tt('osmmap.real_world_openstreetmap_behind_the_map',{open:k.open ? '▾' : '▸'})}
    </div>`;
  if(!k.open) return head;
  if(!k.st) return head + `<div class="count">${k.busy ? tt('common.reading_3') : esc(k.err || '')}</div>`;
  const s = k.st.settings;
  if(!s.enabled) return head + `<div class="bnote">${docPoints(
      tt('osmmap.off_this_is_the_one_part'), [
      tt('osmmap.it_sends_the_maps_real_world'),
      tt('osmmap.to_and_settings_real_world_map',{tiles:esc(s.tiles[0]),overpass:esc(s.overpass[0]),nominatim:esc(s.nominatim)}),
      tt('osmmap.tiles_are_kept_on_disk_for')])}</div>
    <button onclick="openSettings()">${tt('osmmap.open_settings_to_turn_it_on')}</button>`;
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
    shape = `<div class="count">${tt('osmmap.one_tile_km_east_west_km',{x:f(ew),x2:f(ns),x3:Math.abs(st) < 0.005 ? '' : `<span class="w-warn">${tt('osmmap.the_box_stretches_the_map_than',{st:Math.abs(st * 100).toFixed(1),st2:st > 0 ? 'wider' : 'taller'})}</span>`})}</div>`;
  }
  const kept = k.st.box_from === 'kept' ? tt('osmmap.kept_for_this_map')
    : k.st.box_from === 'file' ? tt('osmmap.read_from_bbox_coords_txt_beside') : tt('osmmap.not_set_yet');
  const co = k.coast;
  const res = k.results || [];
  const regions = (c.man.regions || []).filter(r => r.name).map(r => r.name).sort();
  return `${head}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="bsec"><h4>${tt('osmmap.the_box')} <span class="count">${esc(kept)}</span></h4>
      <div class="cmbar2"><button class="primary" onclick="owpOpen()">${tt('osmmap.pick_it_on_a_world_map')}</button></div>
      <div class="brow" style="flex-wrap:wrap">${box}</div>
      ${shape}
      <div class="cmbar2">
        <button class="primary" onclick="osmBoxPost({box: state.osm.box})"
          ${osmBoxOk(k.box) ? '' : 'disabled'}>${tt('osmmap.keep')}</button>
        <label class="btnlike">${tt('osmmap.import_bbox_coords_txt')}
          <input type="file" accept=".txt" style="display:none" onchange="osmBoxFile(this)"></label>
        <button onclick="osmBoxDownload()" ${k.st.file ? '' : 'disabled'}>${tt('common.export')}</button>
        <button onclick="osmBoxPost({clear: true})" ${k.st.box_from === 'kept' ? '' : 'disabled'}>${tt('common.clear')}</button>
      </div>
      <div class="count">${tt('osmmap.where_the_maps_edges_are_in')}</div>
    </div>
    <div class="bsec"><h4>${tt('osmmap.backdrop')}</h4>
      <label class="chk"><input type="checkbox" ${k.show ? 'checked' : ''}
        onchange="state.osm.show=this.checked;cmapPaint()"> ${tt('osmmap.show_the_real_world_over_the')}</label>
      <label style="display:block">${tt('osmmap.opacity')} <input type="range" min="0.1" max="1" step="0.05" value="${k.alpha}"
        oninput="state.osm.alpha=+this.value;cmapPaint()"></label>
      ${osmStyleHtml()}
      <div class="cmbar2"><label>${tt('osmmap.save_a_picture_of_the_box')}
          <select onchange="state.osm.picW=+this.value">${[1024, 2048, 4096].map(w =>
            `<option value="${w}" ${w === k.picW ? 'selected' : ''}>${tt('osmmap.px_wide',{x:w})}</option>`).join('')}</select></label>
        <button onclick="osmPicture('png')" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}>${tt('osmmap.png')}</button>
        <button onclick="osmPicture('svg')" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}>${tt('osmmap.svg')}</button></div>
      <div class="count">${tt('osmmap.the_style_above_cut_to_the')}</div>
    </div>
    <div class="bsec"><h4>${tt('osmmap.coastline')}</h4>
      <div class="cmbar2"><button onclick="osmCoast()" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}
        >${k.busy && k.label && !k.job.startsWith('osmw') ? esc(k.label) : co ? tt('osmmap.again') : tt('osmmap.fetch_the_real_coastline')}</button></div>
      ${co ? `<div class="count">${tt('osmmap.coastline_ways_tiles_of_line_cyan',{way_count:co.way_count,line:co.line,to_sea:co.to_sea,land_side_sea:co.land_side_sea})}</div>
        <label class="chk"><input type="checkbox" ${k.showCoast ? 'checked' : ''}
          onchange="state.osm.showCoast=this.checked;cmapPaint()"> ${tt('osmmap.show_it_on_the_map')}</label>
        ${co.leaks ? `<div class="w-warn">${tt('osmmap.the_coastline_has_a_gap_the',{leak:co.leak})}</div>`
        : `<div class="cmbar2"><button class="primary" onclick="osmCoastApply()"
            ${co.to_sea ? '' : 'disabled'}>${tt('osmmap.make_the_red_tiles_sea')}</button>
            <span class="count">${tt('osmmap.one_stroke_the_paint_tab_undoes')}</span></div>`}` : ''}
    </div>
    <div class="bsec"><h4>${tt('osmmap.lakes_lagoons_and_seas')}</h4>
      <div class="brow" style="flex-wrap:wrap">${[['sea', 'seas'], ['lagoon', 'lagoons'], ['lake', 'lakes']].map(([w, t]) =>
        `<label class="chk"><input type="checkbox" ${k.wkinds[w] ? 'checked' : ''}
          onchange="osmWaterSet('${w}',this.checked)"> ${t}</label>`).join('')}</div>
      <label>${tt('osmmap.leave_out_any_smaller_than')} <input type="number" min="0" max="10000" value="${k.wmin}" style="width:70px"
        onchange="state.osm.wmin=Math.max(0,+this.value||0);state.osm.water=null;osmBuildOver();osmPaint();cmapPaint()"> ${tt('osmmap.tiles')}</label>
      <div class="cmbar2"><button onclick="osmWater()" ${k.busy || !osmBoxOk(k.box) || !osmWaterBody().kinds.length ? 'disabled' : ''}
        >${k.busy && k.label && k.job.startsWith('osmw') ? esc(k.label) : k.water ? tt('osmmap.again') : tt('osmmap.fetch_the_water')}</button></div>
      ${k.water ? `<div class="count">${tt('osmmap.water_outline_s_island_s_kept',{rings:k.water.rings,x:Object.entries(k.water.by_kind || {}).map(([w, n]) =>
          ` (${n} ${w})`).join(''),holes:k.water.holes,small:k.water.small,to_sea:k.water.to_sea,sea_already:k.water.sea_already})}</div>
        <div class="cmbar2"><button class="primary" onclick="osmWaterApply()" ${k.water.to_sea ? '' : 'disabled'}>${tt('osmmap.make_the_blue_tiles_sea')}</button>
          <span class="count">${tt('osmmap.one_stroke_the_paint_tab_undoes')}</span></div>` : ''}
      <div class="count">${tt('osmmap.mylaes_water_step_openstreetmaps_sea_lagoon')}</div>
    </div>
    <div class="bsec"><h4>${tt('osmmap.historic_sites')}</h4>${osmHistHtml()}</div>
    <div class="bsec"><h4>${tt('osmmap.overpass_chunks',{x:(k.chunks || []).some(f => f.failed)
      ? `<span class="w-warn">${tt('osmmap.some_failed')}</span>` : ''})}</h4>${osmChunksHtml()}</div>
    <div class="bsec"><h4>${tt('osmmap.the_map_bundle')}</h4>${osmBundleHtml()}</div>
    <div class="bsec"><h4>${tt('osmmap.find_a_place')}</h4>
      <div class="brow"><input id="osmQ" value="${esc(k.q)}" placeholder="${ttA('osmmap.a_town_a_region_a_country')}"
        onkeydown="if(event.key==='Enter')osmSearch()">
        <button onclick="osmSearch()" ${k.busy ? 'disabled' : ''}>${tt('osmmap.search')}</button></div>
      ${res.length ? `<label>${tt('osmmap.paint_boundaries_onto')}
          <input id="osmTarget" list="osmRegions" value="${esc(k.target)}" placeholder="${ttA('osmmap.a_region')}"
            onchange="state.osm.target=this.value.trim()"></label>
        <datalist id="osmRegions">${regions.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
        ${res.map((p, i) => `<div class="osmres">
          <div><b>${esc(p.name)}</b> <span class="count">${esc(p.kind)}${p.admin_level
            ? ' ' + p.admin_level : ''}${p.on_map ? tt('osmmap.tile_2',{x:p.x,x2:p.y}) : tt('osmmap.off_the_map')}</span></div>
          <div class="count">${esc(p.display)}</div>
          <div class="cmbar2">
            <button onclick="osmGo(${i})" ${p.on_map ? '' : 'disabled'}>${tt('osmmap.go')}</button>
            <button onclick="osmNewRegion(${i})" ${p.on_map ? '' : 'disabled'}>${tt('osmmap.new_region_here')}</button>
            <button onclick="osmBoundary(${i})">${tt('osmmap.paint_its_boundary')}</button>
          </div></div>`).join('')}`
      : k.results ? `<div class="count">${tt('osmmap.nothing_found_inside_the_box')}</div>` : ''}
    </div>`;
}
