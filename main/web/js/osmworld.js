/* osmworld.js - Campaign Map: the world picker (Phase 87a)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE WORLD PICKER - 87a, from Mylae's New Map Editor (SelectionBox,
   SelectionPanel, the Select Area and Set Resolution steps).

   Every name here starts `owp`. A dialog over the Campaign Map: the whole
   world as OpenStreetMap, where the map's box is drawn by dragging, moved by
   its centre, resized by its corners and turned by the handle above it.
   It works before any box exists, which is the point: the Real world tab's
   four number boxes can only be filled by someone who already knows them.

   THE BOX IS OSMMAP'S BOX. Its four edges are the unturned rectangle and the
   rotation turns it about its centre in degree-scaled Mercator, so the
   helpers in osmmap.js (osmTurnLM, osmMdeg, osmInvMdeg) do the geometry. On
   the slippy map, longitude and Mercator degrees are the same scale, so a
   turn there is a turn on screen and a turned rectangle stays one.

   THE SHAPE. With "keep this map's shape" on, the box is held to the map's
   (W-1):(H-1) in longitude against Mercator, the one shape that does not
   stretch a tile (osmmap.fit), while it is drawn and while a corner is
   dragged; Keep sends it with fit=width so Python makes it exact.

   It sends nothing but through Python, and nothing at all while the switch in
   Settings is off: the tiles through /api/osm/tile, the search through
   /api/osm/world.
   ===================================================================== */

//: How near (screen pixels) a press has to be to a handle to take it.
const OWP_GRAB = 9;
//: The most slippy tiles one frame may ask for; past it the zoom steps down.
const OWP_MAX_TILES = 80;

function owpNew(){
  return {open: false, box: null, lock: true, draw: false, view: null,
          q: '', results: null, busy: false, err: '', drag: null, hover: ''};
}

/* ---------- opening and closing ---------- */

function owpOpen(){
  const k = state.osm, c = state.cmap;
  if(!k || !c || !k.st) return;
  const o = state.owp = owpNew();
  o.open = true;
  o.W = c.man.width; o.H = c.man.height;
  o.box = osmBoxOk(k.box) ? Object.assign({rotation: 0}, k.box) : null;
  const m = document.getElementById('modal');
  m.className = 'modal wide owp';
  m.innerHTML = owpShell();
  overlay.classList.add('open');
  owpBind();
  owpSide();
  requestAnimationFrame(() => { owpResize(); owpHome(); owpDraw(); });
}

function owpClose(){
  if(state.owp) state.owp.open = false;
  closeModal();
}

function owpShell(){
  return `<h2>Pick the map's box on the world <span class="count">OpenStreetMap</span></h2>
    <div class="owpbody">
      <div class="owpstage" id="owpStage"><canvas id="owpCanvas"></canvas>
        <div class="owptip" id="owpTip"></div></div>
      <div class="owpside" id="owpSide"></div>
    </div>
    <div class="foot">
      <span class="count" style="margin-right:auto">Drag to pan, wheel to zoom. Drag the
        box's corners to resize it, its middle to move it, the violet handle to turn it.</span>
      <button onclick="owpClose()">Cancel</button>
      <button class="primary" id="owpUse" onclick="owpUse()">Use for this map</button>
    </div>`;
}

/* ---------- the view: world pixels at zoom z, a centre, a canvas ---------- */

const owpWorld = z => 256 * 2 ** z;

function owpResize(){
  const cv = document.getElementById('owpCanvas');
  if(!cv) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round((cv.clientWidth || 1) * dpr), h = Math.round((cv.clientHeight || 1) * dpr);
  if(cv.width !== w || cv.height !== h){ cv.width = w; cv.height = h; }
}

function owpSize(){
  const cv = document.getElementById('owpCanvas');
  return cv ? [cv.clientWidth || 1, cv.clientHeight || 1] : [1, 1];
}

//: [lon, Mercator degrees] -> the canvas point
function owpToScreen(lon, md){
  const o = state.owp, v = o.view, S = owpWorld(v.z), [cw, ch] = owpSize();
  return [(lon + 180) / 360 * S - v.cx + cw / 2, (1 - md / 180) / 2 * S - v.cy + ch / 2];
}

//: and back: the canvas point -> [lon, Mercator degrees]
function owpFromScreen(sx, sy){
  const o = state.owp, v = o.view, S = owpWorld(v.z), [cw, ch] = owpSize();
  return [(sx - cw / 2 + v.cx) / S * 360 - 180, (1 - 2 * (sy - ch / 2 + v.cy) / S) * 180];
}

//: the view that shows [west, east] x [Mercator south, north] with a margin
function owpLook(west, east, mdS, mdN){
  const o = state.owp, [cw, ch] = owpSize();
  const fw = (east - west) / 360, fh = (mdN - mdS) / 360;
  let z = Math.log2(Math.min(cw / Math.max(fw * 256, 1e-9), ch / Math.max(fh * 256, 1e-9)) * 0.7);
  z = Math.max(1, Math.min(17, z));
  const S = owpWorld(z);
  o.view = {z, cx: ((west + east) / 2 + 180) / 360 * S, cy: (1 - (mdN + mdS) / 360) / 2 * S};
}

//: where the dialog opens: on the box, or on Mylae's Europe (45N 15E, zoom 4)
function owpHome(){
  const o = state.owp;
  if(o.box){
    const cs = owpCorners(o.box);
    owpLook(Math.min(...cs.map(p => p[0])), Math.max(...cs.map(p => p[0])),
            Math.min(...cs.map(p => p[1])), Math.max(...cs.map(p => p[1])));
  } else {
    const S = owpWorld(4);
    o.view = {z: 4, cx: (15 + 180) / 360 * S, cy: (1 - osmMdeg(45) / 180) / 2 * S};
  }
}

function owpZoomAbout(z, sx, sy){
  const o = state.owp, v = o.view;
  z = Math.max(1, Math.min(18, z));
  const [lon, md] = owpFromScreen(sx, sy);
  const S = owpWorld(z), [cw, ch] = owpSize();
  v.z = z;
  v.cx = (lon + 180) / 360 * S - (sx - cw / 2);
  v.cy = (1 - md / 180) / 2 * S - (sy - ch / 2);
  owpDraw();
}

/* ---------- the box's geometry, in [lon, Mercator degrees] ---------- */

//: the four corners as they stand, north-west first, clockwise
function owpCorners(b){
  const r = osmRot(b), mn = osmMdeg(b.north), ms = osmMdeg(b.south);
  return [[b.west, mn], [b.east, mn], [b.east, ms], [b.west, ms]]
    .map(([l, m]) => osmTurnLM(b, l, m, r));
}

//: the box's pivot, as osmmap turns it: the plain middle of its edges
const owpPivot = b => [(b.east + b.west) / 2, osmMdeg((b.north + b.south) / 2)];

//: where the rotation handle stands: above the top edge's middle
function owpRotHandle(b){
  const mn = osmMdeg(b.north), ms = osmMdeg(b.south);
  return osmTurnLM(b, (b.east + b.west) / 2, mn + (mn - ms) * 0.18, osmRot(b));
}

//: the map's shape, as longitude per Mercator degree
const owpWant = () => (state.owp.W - 1) / Math.max(state.owp.H - 1, 1);

//: A box from two opposite corners in the box's own (unturned) frame, held to
//: the map's shape when asked: the fixed corner stays, the other gives way.
function owpRect(fix, mov, rotation){
  const o = state.owp;
  let dx = mov[0] - fix[0], dy = mov[1] - fix[1];
  if(o.lock){
    const want = owpWant(), ax = Math.abs(dx), ay = Math.abs(dy);
    if(ax / Math.max(ay, 1e-9) > want) dy = Math.sign(dy || 1) * ax / want;
    else dx = Math.sign(dx || 1) * ay * want;
  }
  const w = Math.min(fix[0], fix[0] + dx), e = Math.max(fix[0], fix[0] + dx);
  const s = Math.min(fix[1], fix[1] + dy), n = Math.max(fix[1], fix[1] + dy);
  return {north: osmInvMdeg(n), south: osmInvMdeg(s), west: w, east: e, rotation: rotation || 0};
}

//: a vector [dlon, dMercator degrees] turned by `ang`, as osmTurnLM turns a point
function owpVec(v, ang){
  const a = ang * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  return [v[0] * c + v[1] * s, v[1] * c - v[0] * s];
}

//: Dragging corner `i` to `p`, the opposite corner held where it stands on
//: screen. The box's own frame is only turned, so the diagonal in it is the
//: drag turned back, whatever the pivot. The pivot is the one thing that
//: moves: osmmap turns about the plain middle of the latitudes, a hair off
//: the Mercator middle, so the offset `t` along the box's "up" is found by a
//: few steps of t = -delta(t), each a thousand times smaller than the last.
function owpCornerTo(i, p){
  const o = state.owp, b0 = o.drag.box0, r = osmRot(b0);
  const F = owpCorners(b0)[(i + 2) % 4];
  const d = owpVec([p[0] - F[0], p[1] - F[1]], -r);
  if(o.lock){
    const want = owpWant(), ax = Math.abs(d[0]), ay = Math.abs(d[1]);
    if(ax / Math.max(ay, 1e-9) > want) d[1] = Math.sign(d[1] || 1) * ax / want;
    else d[0] = Math.sign(d[0] || 1) * ay * want;
  }
  const hw = Math.abs(d[0]) / 2, hh = Math.abs(d[1]) / 2, dd = owpVec(d, r);
  const G = [F[0] + dd[0] / 2, F[1] + dd[1] / 2];          // the middle, as it stands
  const u = owpVec([0, 1], r);                              // the box's up, as it stands
  const delta = y => osmMdeg((osmInvMdeg(y + hh) + osmInvMdeg(y - hh)) / 2) - y;
  let t = 0;
  for(let k = 0; k < 6; k++) t = -delta(G[1] + t * (1 - u[1]));
  const px = G[0] - t * u[0], gy = G[1] - t * u[1] + t;
  return {north: osmInvMdeg(gy + hh), south: osmInvMdeg(gy - hh),
          west: px - hw, east: px + hw, rotation: r};
}

//: the whole box moved by [dlon, dMercator degrees]
function owpMoved(b, dl, dm){
  return {north: osmInvMdeg(osmMdeg(b.north) + dm), south: osmInvMdeg(osmMdeg(b.south) + dm),
          west: b.west + dl, east: b.east + dl, rotation: b.rotation || 0};
}

//: a box that stays on the map of the world: poles, date line, a real size
function owpSane(b){
  return b && b.east - b.west > 1e-4 && b.north - b.south > 1e-4
    && owpCorners(b).every(([l, m]) => l > -180 && l < 180 && Math.abs(osmInvMdeg(m)) < 85.05);
}

/* ---------- drawing ---------- */

function owpDraw(){
  const o = state.owp, cv = document.getElementById('owpCanvas');
  if(!o || !o.open || !cv || !o.view) return;
  owpResize();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const x = cv.getContext('2d'), [cw, ch] = owpSize();
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.fillStyle = '#aac9d6';
  x.fillRect(0, 0, cw, ch);
  owpDrawTiles(x, cw, ch);
  if(o.results) owpDrawPlaces(x);
  if(o.box) owpDrawBox(x);
  if(o.drag && o.drag.kind === 'draw' && o.drag.rect) owpDrawRect(x, o.drag.rect);
}

function owpDrawTiles(x, cw, ch){
  const v = state.owp.view;
  let tz = Math.max(0, Math.min(osmMaxZoom(), Math.round(v.z)));
  let x0, x1, y0, y1, n, sc;
  for(;; tz--){
    n = 2 ** tz; sc = 2 ** (v.z - tz);
    const left = (v.cx - cw / 2) / sc, top = (v.cy - ch / 2) / sc;
    x0 = Math.max(0, Math.floor(left / 256)); x1 = Math.min(n - 1, Math.floor((left + cw / sc) / 256));
    y0 = Math.max(0, Math.floor(top / 256)); y1 = Math.min(n - 1, Math.floor((top + ch / sc) / 256));
    if(tz === 0 || (x1 - x0 + 1) * (y1 - y0 + 1) <= OWP_MAX_TILES) break;
  }
  const size = 256 * sc;
  x.imageSmoothingEnabled = true;
  for(let ty = y0; ty <= y1; ty++){
    for(let tx = x0; tx <= x1; tx++){
      const img = osmTileImg(tz, tx, ty);
      if(!img) continue;
      // a hair of overlap hides the seam antialiasing leaves between tiles
      x.drawImage(img, tx * size - v.cx + cw / 2, ty * size - v.cy + ch / 2, size + 0.5, size + 0.5);
    }
  }
}

function owpPath(x, pts){
  x.beginPath();
  pts.forEach(([l, m], i) => { const [sx, sy] = owpToScreen(l, m); i ? x.lineTo(sx, sy) : x.moveTo(sx, sy); });
  x.closePath();
}

function owpDrawRect(x, b){
  x.save();
  owpPath(x, owpCorners(b));
  x.fillStyle = 'rgba(245,158,11,0.15)'; x.fill();
  x.strokeStyle = '#f59e0b'; x.lineWidth = 2; x.stroke();
  x.restore();
}

function owpDrawBox(x){
  const o = state.owp, b = o.box, cs = owpCorners(b);
  x.save();
  owpPath(x, cs);
  x.fillStyle = 'rgba(245,158,11,0.08)'; x.fill();
  x.setLineDash([6, 4]); x.strokeStyle = '#f59e0b'; x.lineWidth = 2; x.stroke();
  x.setLineDash([]);
  // the rotation handle's stalk, from the top edge's middle
  const top = osmTurnLM(b, (b.east + b.west) / 2, osmMdeg(b.north), osmRot(b));
  const rh = owpRotHandle(b), [ax, ay] = owpToScreen(...top), [rx, ry] = owpToScreen(...rh);
  x.strokeStyle = '#a78bfa'; x.lineWidth = 1.5;
  x.beginPath(); x.moveTo(ax, ay); x.lineTo(rx, ry); x.stroke();
  const dot = (sx, sy, fill, round, hot) => {
    x.fillStyle = fill; x.strokeStyle = '#1e293b'; x.lineWidth = 2;
    x.beginPath();
    const r = hot ? 8 : 6;
    if(round) x.arc(sx, sy, r, 0, Math.PI * 2); else x.rect(sx - r, sy - r, 2 * r, 2 * r);
    x.fill(); x.stroke();
  };
  cs.forEach(([l, m], i) => { const [sx, sy] = owpToScreen(l, m); dot(sx, sy, '#f59e0b', false, o.hover === 'c' + i); });
  const [px, py] = owpToScreen(...owpCentre(b));
  dot(px, py, '#38bdf8', true, o.hover === 'move');
  dot(rx, ry, '#a78bfa', true, o.hover === 'rot');
  x.restore();
}

//: the box's middle as it stands (the middle of its corners)
function owpCentre(b){
  const cs = owpCorners(b);
  return [(cs[0][0] + cs[2][0]) / 2, (cs[0][1] + cs[2][1]) / 2];
}

function owpDrawPlaces(x){
  const o = state.owp;
  x.save();
  x.font = '11px sans-serif';
  o.results.forEach((p, i) => {
    const [sx, sy] = owpToScreen(p.lon, osmMdeg(p.lat));
    x.fillStyle = i === o.pick ? '#ef4444' : '#b91c1c';
    x.beginPath(); x.arc(sx, sy, i === o.pick ? 6 : 4, 0, Math.PI * 2); x.fill();
    if(i === o.pick){
      x.fillStyle = '#111'; x.fillText(p.name, sx + 8, sy + 4);
    }
  });
  x.restore();
}

/* ---------- the pointer ---------- */

function owpHit(sx, sy){
  const o = state.owp, b = o.box;
  if(!b) return '';
  const near = (l, m) => { const [px, py] = owpToScreen(l, m); return Math.hypot(px - sx, py - sy) <= OWP_GRAB; };
  if(near(...owpRotHandle(b))) return 'rot';
  const cs = owpCorners(b);
  for(let i = 0; i < 4; i++) if(near(...cs[i])) return 'c' + i;
  if(near(...owpCentre(b))) return 'move';
  return '';
}

function owpBind(){
  const cv = document.getElementById('owpCanvas');
  if(!cv) return;
  const at = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  cv.addEventListener('pointerdown', e => {
    const o = state.owp;
    if(!o || e.button !== 0) return;
    const [sx, sy] = at(e), hit = owpHit(sx, sy);
    cv.setPointerCapture(e.pointerId);
    const kind = hit || (o.draw || e.shiftKey ? 'draw' : 'pan');
    o.drag = {kind, sx, sy, cx: o.view.cx, cy: o.view.cy, box0: o.box ? Object.assign({}, o.box) : null,
              at: owpFromScreen(sx, sy)};
  });
  cv.addEventListener('pointermove', e => {
    const o = state.owp;
    if(!o) return;
    const [sx, sy] = at(e), d = o.drag;
    if(!d){
      const h = owpHit(sx, sy);
      cv.style.cursor = h === 'rot' ? 'crosshair' : h === 'move' ? 'move' : h ? 'nwse-resize'
        : o.draw ? 'crosshair' : 'grab';
      if(h !== o.hover){ o.hover = h; owpDraw(); }
      owpTip(sx, sy);
      return;
    }
    const p = owpFromScreen(sx, sy);
    if(d.kind === 'pan'){
      o.view.cx = d.cx - (sx - d.sx); o.view.cy = d.cy - (sy - d.sy);
    } else if(d.kind === 'draw'){
      d.rect = owpRect(d.at, p, 0);
    } else if(d.kind === 'move'){
      const nb = owpMoved(d.box0, p[0] - d.at[0], p[1] - d.at[1]);
      if(owpSane(nb)) o.box = nb;
    } else if(d.kind === 'rot'){
      const [pl, pm] = owpPivot(d.box0);
      let a = Math.atan2(p[0] - pl, p[1] - pm) * 180 / Math.PI;
      a = e.shiftKey ? Math.round(a / 5) * 5 : Math.round(a * 10) / 10;
      const nb = Object.assign({}, d.box0, {rotation: a});
      if(owpSane(nb)) o.box = nb;
    } else if(d.kind[0] === 'c'){
      const nb = owpCornerTo(+d.kind.slice(1), p);
      if(owpSane(nb)) o.box = nb;
    }
    owpDraw();
    if(d.kind !== 'pan') owpSide(true);
  });
  const up = e => {
    const o = state.owp;
    if(!o || !o.drag) return;
    const d = o.drag;
    o.drag = null;
    if(d.kind === 'draw' && d.rect && owpSane(d.rect)){
      const [ax, ay] = owpToScreen(d.rect.west, osmMdeg(d.rect.north));
      const [bx, by] = owpToScreen(d.rect.east, osmMdeg(d.rect.south));
      if(Math.abs(bx - ax) > 6 && Math.abs(by - ay) > 6){ o.box = d.rect; o.draw = false; }
    }
    owpDraw(); owpSide();
  };
  cv.addEventListener('pointerup', up);
  cv.addEventListener('pointercancel', up);
  cv.addEventListener('pointerleave', () => { const t = document.getElementById('owpTip'); if(t) t.style.display = 'none'; });
  cv.addEventListener('wheel', e => {
    e.preventDefault();
    const [sx, sy] = at(e);
    owpZoomAbout(state.owp.view.z + (e.deltaY > 0 ? -0.5 : 0.5), sx, sy);
  }, {passive: false});
  window.addEventListener('resize', () => { if(state.owp && state.owp.open) owpDraw(); });
}

//: the latitude and longitude under the pointer, in the corner
function owpTip(sx, sy){
  const t = document.getElementById('owpTip');
  if(!t) return;
  const [lon, md] = owpFromScreen(sx, sy), lat = osmInvMdeg(md);
  t.style.display = 'block';
  t.textContent = `${Math.abs(lat).toFixed(3)}°${lat >= 0 ? 'N' : 'S'}  ${Math.abs(lon).toFixed(3)}°${lon >= 0 ? 'E' : 'W'}`;
}

/* ---------- the side panel ---------- */

//: `quiet` repaints only the numbers, so a drag does not rebuild inputs under
//: the pointer or steal the focus from a box being typed in
function owpSide(quiet){
  const el = document.getElementById('owpSide'), o = state.owp;
  if(!el || !o) return;
  if(quiet){
    const f = document.getElementById('owpNums');
    if(f && o.box){
      ['north', 'south', 'west', 'east', 'rotation'].forEach(k => {
        const i = document.getElementById('owpF_' + k);
        if(i && document.activeElement !== i) i.value = (+o.box[k] || 0).toFixed(k === 'rotation' ? 1 : 4);
      });
      const r = document.getElementById('owpRead');
      if(r) r.innerHTML = owpReadout();
      return;
    }
  }
  el.innerHTML = owpSideHtml();
  const use = document.getElementById('owpUse');
  if(use) use.disabled = !owpSane(o.box);
}

function owpReadout(){
  const o = state.owp, b = o.box;
  if(!b) return '';
  const [ew, ns] = osmKmPerTile(b, o.W, o.H), st = osmStretch(b, o.W, o.H);
  const f = v => v >= 10 ? v.toFixed(0) : v.toFixed(1);
  return `One tile of this ${o.W}×${o.H} map: <b>${f(ew)} km</b> east-west, <b>${f(ns)} km</b>
    north-south, at the box's middle.
    ${Math.abs(st) < 0.005 ? '<span class="w-good">The box is this map’s shape.</span>'
      : `<span class="w-warn">The box would stretch the map ${Math.abs(st * 100).toFixed(1)}%
        ${st > 0 ? 'wider' : 'taller'} than the real ground.</span>`}`;
}

function owpSideHtml(){
  const o = state.owp, b = o.box;
  const res = o.results || [];
  const num = (k, step) => `<label style="flex:1 1 90px">${k}
      <input type="number" id="owpF_${k}" step="${step}"
        value="${b ? (+b[k] || 0).toFixed(k === 'rotation' ? 1 : 4) : ''}"
        onchange="owpField('${k}',this.value)" ${b ? '' : 'disabled'}></label>`;
  return `
    ${o.err ? `<div class="w-bad">${esc(o.err)}</div>` : ''}
    <div class="bsec"><h4>The world as</h4>${osmStyleHtml()}</div>
    <div class="bsec"><h4>Find a place</h4>
      <div class="brow"><input id="owpQ" value="${esc(o.q)}" placeholder="a town, a region, a country"
        onkeydown="if(event.key==='Enter')owpSearch()">
        <button onclick="owpSearch()" ${o.busy ? 'disabled' : ''}>Search</button></div>
      ${res.map((p, i) => `<div class="osmres">
          <div><b>${esc(p.name)}</b> <span class="count">${esc(p.kind)}${p.admin_level ? ' ' + p.admin_level : ''}</span></div>
          <div class="count">${esc(p.display)}</div>
          <div class="cmbar2"><button onclick="owpGo(${i})">Go</button>
            <button onclick="owpFitPlace(${i})" ${p.extent ? '' : 'disabled'}>Fit the box around it</button></div>
        </div>`).join('')}
      ${o.results && !res.length ? '<div class="count">Nothing found.</div>' : ''}
    </div>
    <div class="bsec"><h4>The box</h4>
      <div class="cmbar2">
        <button class="${o.draw ? 'primary' : ''}" onclick="owpDrawMode()">${o.draw
          ? 'Drag on the map…' : b ? '✚ Draw it again' : '✚ Draw the box'}</button>
        <label class="btnlike">Import bbox_coords.txt…
          <input type="file" accept=".txt" style="display:none" onchange="owpFile(this)"></label>
      </div>
      <div class="count">Or hold Shift and drag anywhere on the map.</div>
      <div class="brow" id="owpNums" style="flex-wrap:wrap">${num('north', 0.01)}${num('south', 0.01)}
        ${num('west', 0.01)}${num('east', 0.01)}${num('rotation', 1)}</div>
      <label class="chk"><input type="checkbox" ${o.lock ? 'checked' : ''}
        onchange="owpLock(this.checked)"> Keep this map’s shape (${o.W}×${o.H})</label>
      ${b ? `<div class="count" id="owpRead">${owpReadout()}</div>
        <div class="cmbar2"><button onclick="owpShape()">Give it this map’s shape</button>
          <button onclick="owpField('rotation',0)" ${osmRot(b) ? '' : 'disabled'}>Straighten</button></div>`
        : '<div class="count">No box yet: draw one, import a bbox_coords.txt, or fit it around a place you found.</div>'}
    </div>`;
}

function owpField(k, v){
  const o = state.owp;
  if(!o.box) return;
  const nb = Object.assign({}, o.box, {[k]: parseFloat(v)});
  if(!isFinite(nb[k])){ owpSide(); return; }
  if(osmBoxOk(nb) && owpSane(nb)){ o.box = nb; o.err = ''; }
  else o.err = `That ${k} would put the box past the pole, across the date line, or inside out.`;
  owpSide(); owpDraw();
}

function owpLock(on){
  const o = state.owp;
  o.lock = on;
  owpSide();
}

//: the box given the map's shape, keeping its width (osmmap.fit, keep=width)
function owpShape(){
  const o = state.owp, b = o.box;
  if(!b) return;
  const half = (b.east - b.west) / owpWant() / 2, mid = (osmMdeg(b.north) + osmMdeg(b.south)) / 2;
  const nb = Object.assign({}, b, {north: osmInvMdeg(mid + half), south: osmInvMdeg(mid - half)});
  if(owpSane(nb)){ o.box = nb; o.err = ''; }
  else o.err = 'The box cannot take this map’s shape there without going past the pole.';
  owpSide(); owpDraw();
}

function owpDrawMode(){
  const o = state.owp;
  o.draw = !o.draw;
  owpSide();
}

async function owpFile(input){
  const f = input.files && input.files[0];
  if(!f) return;
  const txt = await f.text(), o = state.owp, v = {};
  txt.split(/\r?\n/).forEach(line => {
    const m = line.match(/^\s*(north|south|east|west|rotation)\s*=\s*([-+\d.eE]+)/i);
    if(m) v[m[1].toLowerCase()] = parseFloat(m[2]);
  });
  // a coordinate of exactly 0 is a coordinate: Mylae's loader drops it
  const nb = {north: v.north, south: v.south, west: v.west, east: v.east, rotation: v.rotation || 0};
  if(!osmBoxOk(nb) || !owpSane(nb)){ o.err = 'That file has no usable north, south, west and east.'; owpSide(); return; }
  o.box = nb; o.err = '';
  owpHome(); owpSide(); owpDraw();
}

/* ---------- places, anywhere ---------- */

async function owpSearch(){
  const o = state.owp, el = document.getElementById('owpQ');
  if(el) o.q = el.value;
  if(!o.q.trim() || o.busy) return;
  o.busy = true; o.err = ''; owpSide();
  let r;
  try{ r = await api.get(`/api/osm/world?q=${enc(o.q)}`, {label: 'searching OpenStreetMap'}); }
  catch(e){ r = {error: errText(e)}; }
  if(state.owp !== o) return;
  o.busy = false;
  if(r.error){ o.err = r.error; o.results = null; }
  else { o.results = r.results || []; o.pick = o.results.length ? 0 : -1; }
  owpSide(); owpDraw();
}

function owpGo(i){
  const o = state.owp, p = o.results[i];
  if(!p) return;
  o.pick = i;
  if(p.extent){
    const e = p.extent;
    owpLook(e.west, e.east, osmMdeg(e.south), osmMdeg(e.north));
  } else {
    const [cw, ch] = owpSize();
    o.view.z = Math.max(o.view.z, 8);
    const S = owpWorld(o.view.z);
    o.view.cx = (p.lon + 180) / 360 * S; o.view.cy = (1 - osmMdeg(p.lat) / 180) / 2 * S;
  }
  owpDraw();
}

//: A box around a place's extent, unturned, grown to the map's shape when that
//: is kept (never shrunk, so the whole place stays inside)
function owpFitPlace(i){
  const o = state.owp, p = o.results[i];
  if(!p || !p.extent) return;
  const e = p.extent;
  let w = e.west, ea = e.east, n = osmMdeg(e.north), s = osmMdeg(e.south);
  if(o.lock){
    const want = owpWant();
    if((ea - w) / Math.max(n - s, 1e-9) > want){
      const half = (ea - w) / want / 2, mid = (n + s) / 2; n = mid + half; s = mid - half;
    } else {
      const half = (n - s) * want / 2, mid = (w + ea) / 2; w = mid - half; ea = mid + half;
    }
  }
  const nb = {north: osmInvMdeg(n), south: osmInvMdeg(s), west: w, east: ea, rotation: 0};
  if(!owpSane(nb)){ o.err = 'That place is too big for a box at this map’s shape.'; owpSide(); return; }
  o.box = nb; o.err = ''; o.pick = i;
  owpHome(); owpSide(); owpDraw();
}

/* ---------- out ---------- */

async function owpUse(){
  const o = state.owp;
  if(!o || !owpSane(o.box)) return;
  const b = Object.assign({}, o.box);
  if(!osmRot(b)) delete b.rotation;
  owpClose();
  // Python makes the shape exact (osmmap.fit) when the shape is being kept
  await osmBoxPost(Object.assign({box: b}, o.lock ? {fit: 'width'} : {}));
}
