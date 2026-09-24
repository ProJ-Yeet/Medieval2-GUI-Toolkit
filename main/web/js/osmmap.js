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

//: [fx, fy] in tile space, a tile's centre at its whole number
function osmToTile(b, W, H, lat, lon){
  const mn = osmMerc(b.north), ms = osmMerc(b.south);
  return [(lon - b.west) / (b.east - b.west) * (W - 1),
          (mn - osmMerc(lat)) / (mn - ms) * (H - 1)];
}

//: the same, for a Mercator value rather than a latitude (a slippy tile's edge)
function osmMercRow(b, H, m){
  const mn = osmMerc(b.north), ms = osmMerc(b.south);
  return (mn - m) / (mn - ms) * (H - 1);
}

function osmBoxOk(b){
  return b && [b.north, b.south, b.west, b.east].every(v => typeof v === 'number' && isFinite(v))
    && b.north > b.south && b.east > b.west && b.north <= 85.05 && b.south >= -85.05;
}

/* ---------- drawing, called by cmapPaint inside its clip ---------- */

const _osmTiles = new Map();

function osmTileImg(z, x, y){
  const url = `/api/osm/tile/${z}/${x}/${y}`;
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
  _osmSoon = setTimeout(() => { _osmSoon = 0; cmapPaint(); }, 60);
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
  // the zoom whose tiles come out about 256 screen pixels wide
  const span = b.east - b.west;
  let z = Math.round(Math.log2(360 * (W - 1) * v.zoom / (span * OSM_TILE_PX)));
  z = Math.max(0, Math.min(18, z));
  // the visible part of the box, in degrees and in Mercator
  const lon = fx => b.west + fx / (W - 1) * span;
  const mn = osmMerc(b.north), ms = osmMerc(b.south);
  const merc = fy => mn - fy / (H - 1) * (mn - ms);
  const lonA = Math.max(b.west, lon(s0 - 0.5)), lonB = Math.min(b.east, lon(s1 - 0.5));
  const mA = Math.min(mn, merc(t0 - 0.5)), mB = Math.max(ms, merc(t1 - 0.5));
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
  for(let ty = Math.max(0, ys[0]); ty <= Math.min(n - 1, ys[1]); ty++){
    const top = osmMercRow(b, H, Math.PI * (1 - 2 * ty / n));
    const bot = osmMercRow(b, H, Math.PI * (1 - 2 * (ty + 1) / n));
    for(let tx = Math.max(0, xs[0]); tx <= Math.min(n - 1, xs[1]); tx++){
      const img = osmTileImg(z, tx, ty);
      if(!img) continue;
      const left = (tx / n * 360 - 180 - b.west) / span * (W - 1);
      const right = ((tx + 1) / n * 360 - 180 - b.west) / span * (W - 1);
      const sx = cmapX(left + 0.5), sy = cmapY(top + 0.5);
      x.drawImage(img, sx, sy, cmapX(right + 0.5) - sx, cmapY(bot + 0.5) - sy);
    }
  }
  x.restore();
}

//: The coastline's overlay, one pixel a tile like the composite: the line in
//: cyan, every tile the stroke would make sea in a see-through red.
function osmBuildOver(){
  const k = state.osm, c = state.cmap;
  k.over = null;
  if(!k.coast || !c) return;
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
  put(k.coast.to_sea_xy || [], 255, 70, 70, 150);
  put(k.coast.line_xy || [], 0, 240, 255, 255);
  x.putImageData(im, 0, 0);
  k.over = cv;
}

/* ---------- the box ---------- */

function osmBoxSet(field, value){
  const k = state.osm;
  if(!k.box) k.box = {north: 0, south: 0, west: 0, east: 0};
  k.box[field] = parseFloat(value);
  k.coast = null; k.over = null;
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
  k.st.box = r.box; k.st.box_from = r.box_from; k.st.file = r.file;
  k.box = r.box ? Object.assign({}, r.box) : null;
  k.coast = null; k.over = null;
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
  const b = k.box || {north: '', south: '', west: '', east: ''};
  const box = ['north', 'south', 'west', 'east'].map(f => `<label style="flex:1 1 90px">${f}
      <input type="number" step="0.01" value="${esc(String(b[f] ?? ''))}"
        onchange="osmBoxSet('${f}',this.value)"></label>`).join('');
  const kept = k.st.box_from === 'kept' ? 'kept for this map'
    : k.st.box_from === 'file' ? 'read from bbox_coords.txt beside the map' : 'not set yet';
  const co = k.coast;
  const res = k.results || [];
  const regions = (c.man.regions || []).filter(r => r.name).map(r => r.name).sort();
  return `${head}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="bsec"><h4>The box <span class="count">${esc(kept)}</span></h4>
      <div class="brow" style="flex-wrap:wrap">${box}</div>
      <div class="cmbar2">
        <button class="primary" onclick="osmBoxPost({box: state.osm.box})"
          ${osmBoxOk(k.box) ? '' : 'disabled'}>Keep</button>
        <label class="btnlike">Import bbox_coords.txt…
          <input type="file" accept=".txt" style="display:none" onchange="osmBoxFile(this)"></label>
        <button onclick="osmBoxDownload()" ${k.st.file ? '' : 'disabled'}>Export</button>
        <button onclick="osmBoxPost({clear: true})" ${k.st.box_from === 'kept' ? '' : 'disabled'}>Clear</button>
      </div>
      <div class="count">Where the map’s edges are in the real world. Change a number and the
        backdrop moves at once; Keep saves it in the toolkit, not in the mod.</div>
    </div>
    <div class="bsec"><h4>Backdrop</h4>
      <label class="chk"><input type="checkbox" ${k.show ? 'checked' : ''}
        onchange="state.osm.show=this.checked;cmapPaint()"> Show OpenStreetMap over the map</label>
      <label>Opacity <input type="range" min="0.1" max="1" step="0.05" value="${k.alpha}"
        oninput="state.osm.alpha=+this.value;cmapPaint()"></label>
    </div>
    <div class="bsec"><h4>Coastline</h4>
      <div class="cmbar2"><button onclick="osmCoast()" ${k.busy || !osmBoxOk(k.box) ? 'disabled' : ''}
        >${k.busy && k.label ? esc(k.label) : co ? '↺ Again' : 'Fetch the real coastline'}</button></div>
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
