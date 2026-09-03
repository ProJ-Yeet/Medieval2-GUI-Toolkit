/* campmap.js - Campaign Map: the renderer

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE CAMPAIGN MAP - ten TGA layers, one canvas.

   Phase 16c: the renderer core. It draws, it pans, it zooms and it tells you
   which tile is under the cursor. It does not paint, validate or edit - 16d
   adds the legend and the region panel, 16e the brush, 16f the validator.

   THE BROWSER NEVER PARSES A TGA. Python decodes every layer, projects it to
   one pixel per tile and serves PNG from /api/map/layer; the manifest at
   /api/map says what the layers are and what every region colour means. That
   is the "one engine" rule: there is one region index, one set of colour
   tables and one file writer, and they are all on the Python side. It is also
   what makes 16e's undo and backups possible at all.

   Four rules keep this fast, and all four are answers to something a reference
   tool does. Demir's editor nulls the layer canvas on every painted pixel, so
   the next render re-uploads the whole image - forty full-image uploads inside
   one 40px drag - and rebuilds its terrain composite over ~820k pixels with
   seven string-keyed Map lookups each. None of that is a language problem:

     1. ONE COMPOSITE, BUILT WHEN THE LAYER SET CHANGES. Not per frame, not
        per pointer event. Pan and zoom never touch it - they only decide which
        part of it to copy.
     2. ONLY THE VISIBLE SUB-RECT IS COPIED. At zoom 20 the screen holds a few
        hundred tiles; blitting all 248,370 of DaC's would be work thrown away.
     3. DIRTY RECTANGLES. Moving the cursor one tile repaints two small
        rectangles - the cell it left and the cell it entered - not the canvas.
     4. NOTHING O(PIXELS) ON THE INTERACTION PATH. Picking is a lookup in a
        colour table the manifest brought. The one per-pixel pass in this file
        builds a selected region's outline, and it runs on the click that
        selects, once, and is cached.

   THE PICKED PIXEL IS THE PIXEL UNDER THE CURSOR, at every zoom. The whole
   transform is two lines - a tile's left edge is `ox + tx*zoom`, and the tile
   under a point is `floor((x - ox)/zoom)` - which are exact inverses of each
   other at any zoom and any device pixel ratio. Everything drawn on the map,
   markers included, goes through the same two lines rather than a second copy
   of the arithmetic, because a second copy is how a marker ends up a pixel off
   the thing it marks.

   Three coordinate systems, same as the Python side, and every name here says
   which one it means:
     image   (0,0) top-left, y down. The canvas, and the layer PNGs.
     game    (0,0) bottom-left, y up. What descr_strat.txt writes.
     screen  CSS pixels in the canvas. Multiplied by DPR only at the very edge.
   ===================================================================== */

/* Zoom is in screen pixels per tile. The floor is below one because DaC's map
   is 510x487 and a small window should still be able to show all of it; the
   ceiling is where one tile fills a quarter of a 1080p screen, which is as far
   in as anyone can want to place a settlement pixel. */
const CMAP_ZOOM_MIN = 0.25, CMAP_ZOOM_MAX = 64;
//: A press that travelled less than this is a pick; more, and it was a pan.
//: Same rule and same number as the UV editor, so the two feel alike.
const CMAP_DRAG_SLOP = 4;
//: Below this, a tile is too small to draw a settlement or port glyph on and
//: the marker pixels in the regions layer say it better by themselves.
const CMAP_GLYPH_ZOOM = 3;

/* ---------- opening the screen ---------- */

async function loadCampmap(){
  const mod = state.src;
  // The mode is restored from settings before the mod list has arrived, and a
  // dropped startup request can leave it never arriving (see uiFailedFiles in
  // core.js). Asking for the map of no mod answers "unknown mod", which is true
  // of the request and useless about the situation.
  if(!mod){
    main.innerHTML = `<div class="empty">No mod is picked yet.<br>
      <span class="count">The campaign map is read out of one mod's
      <code>data/world/maps/base</code>, so there is nothing to draw until the mod
      list arrives. If it does not, reloading the page fetches it again.</span></div>`;
    return;
  }
  main.innerHTML = `<div class="empty">Reading ${esc(mod)}’s campaign map…<br>
    <span class="count">ten layers, the region index and descr_regions.txt</span></div>`;
  let man;
  try{ man = await api.get(`/api/map?mod=${enc(mod)}`); }
  catch(e){
    if(stale('campmap', mod)) return;
    state.cmap = null;
    // A mod with no map of its own is the ordinary case, not a failure: most
    // mods ship units and let the game's own map stand. It reads as a 404 here
    // exactly like a real fault would, so the two are told apart by what the
    // server said rather than by the status.
    const why = errText(e);
    main.innerHTML = `<div class="empty" style="max-width:520px;margin:60px auto">
      <b>${esc(mod)}</b> has no campaign map this tool can read.<br>
      <span class="count">${esc(why)}</span><br><br>
      <span class="count">A mod only has one if it ships
      <code>data/world/maps/base</code> - the terrain header, the region list and
      the ten TGA layers. Without them the game uses its own map, and there is
      nothing here to draw.</span><br><br>
      <button class="primary" onclick="loadCampmap()">Try again</button></div>`;
    return;
  }
  if(stale('campmap', mod)) return;
  state.cmap = cmapNew(mod, man);
  renderCampmap();
  cmapLoadLayers();
}

/* The screen's whole state, in one object, rebuilt whenever the mod changes.

   `layers` is keyed by code and each entry owns its own <img>: a layer is
   fetched once and stays, so ticking it off and on again is free. `comp` is the
   composite - one canvas at map size that everything on screen is copied out
   of. `sel` and `hover` are tile coordinates or null, never a pixel colour,
   because the colour is a lookup away and a stale one would be a lie. */
function cmapNew(mod, man){
  const byKey = new Map();
  for(const r of man.regions) byKey.set(r.key, r);
  return {
    mod, man, byKey,
    // draw order is the server's to start with; the arrows in the panel move a
    // layer within this array and nothing else has to know
    order: man.layers.map(l => l.code),
    layers: Object.fromEntries(man.layers.map(l =>
      [l.code, {def: l, on: l.on && l.present, opacity: l.opacity,
                img: null, loading: false, failed: ''}])),
    comp: null, compKey: '',
    view: {zoom: 1, ox: 0, oy: 0, fitted: false},
    hover: null, sel: null, outline: null, outlineKey: -1,
    ms: 0,
  };
}

function renderCampmap(){
  const c = state.cmap;
  if(!c || c.mod !== state.src) return loadCampmap();
  const m = c.man;
  count.textContent = `${m.width}×${m.height}`;
  main.innerHTML = `
    <div class="cmwrap">
      <div class="cmstage" id="cmStage">
        <canvas id="cmCanvas"></canvas>
        <div class="cmbar" id="cmBar">
          <button onclick="cmapFit()" title="Fit the whole map (0)">⤢ Fit</button>
          <button onclick="cmapZoomTo(1)" title="One screen pixel per tile (1)">1:1</button>
          <button onclick="cmapZoomBy(1/1.4)" title="Zoom out (−)">−</button>
          <button onclick="cmapZoomBy(1.4)" title="Zoom in (+)">+</button>
          <span class="count" id="cmZoom"></span>
        </div>
        <div class="cmread" id="cmRead">move the pointer over the map</div>
        <div class="cmperf" id="cmPerf"></div>
      </div>
      <div class="cmside">
        <div class="cmhead">
          <b>${esc(c.mod)}</b>
          <span class="count">${m.width}×${m.height} tiles ·
            ${m.regions.filter(r => r.id >= 0).length} regions ·
            ${m.regions.filter(r => r.settlement).length} settlements ·
            ${m.regions.filter(r => r.port).length} ports</span>
        </div>
        ${cmapFindingsHtml(m.findings)}
        <div class="cmlayers" id="cmLayers">${cmapLayersHtml()}</div>
        <div class="cmpick" id="cmPick"></div>
      </div>
    </div>`;
  cmapWire();
  cmapResize();
  if(!c.view.fitted) cmapFit(); else cmapPaint();
  if(typeof rszApply === 'function') rszApply(main);
}

/* What the read already knows is wrong with this map.

   Shown, and shown quietly. Every one of these is a real state a real mod is
   in - DaC paints a province descr_regions.txt never declares - and none of
   them stops the map being drawn. 16f is the validator; this is the read's own
   findings put where they can be seen rather than kept in a log. */
function cmapFindingsHtml(f){
  const rows = [];
  for(const line of f.layers) rows.push(['bad', line]);
  for(const u of f.undeclared_land) rows.push(['warn',
    `A ${u.pixels}-tile province at ${u.bbox[0]},${u.bbox[1]} to ${u.bbox[2]},${u.bbox[3]} is
     painted <b style="color:rgb(${u.rgb.join(',')})">rgb(${u.rgb.join(', ')})</b> and declared
     nowhere in descr_regions.txt. Not one tile of it is sea, so it is land the game has no
     region for.`]);
  if(f.sea_colours) rows.push(['note',
    `${f.sea_colours} colour${f.sea_colours === 1 ? '' : 's'} on the map
     ${f.sea_colours === 1 ? 'is' : 'are'} sea and declared nowhere, which is normal -
     the ocean has no region record.`]);
  if(f.empty_records.length) rows.push(['warn',
    `${f.empty_records.length} declared region${f.empty_records.length === 1 ? '' : 's'} with
     no pixels at all: ${esc(f.empty_records.slice(0, 4).join(', '))}`]);
  if(f.orphan_settlements.length) rows.push(['warn',
    `${f.orphan_settlements.length} settlement pixel${f.orphan_settlements.length === 1 ? '' : 's'}
     standing in no region: ${f.orphan_settlements.map(p => p.join(',')).join(' · ')}`]);
  if(f.undecided_ports.length) rows.push(['warn',
    `${f.undecided_ports.length} port pixel${f.undecided_ports.length === 1 ? '' : 's'}
     whose owning region cannot be decided`]);
  for(const p of f.record_problems.slice(0, 5))
    rows.push(['warn', `${esc(p.name)}: ${esc(p.problems.join('; '))}`]);
  if(!rows.length) return '';
  const cls = {bad: 'w-bad', warn: 'w-warn', note: 'count'};
  return `<div class="cmfind">${rows.map(([k, t]) =>
    `<div class="${cls[k]}">${t}</div>`).join('')}</div>`;
}

function cmapLayersHtml(){
  const c = state.cmap;
  return `<div class="k">Layers <span class="count">top of the list draws last</span></div>`
    + c.order.map((code, i) => {
    const L = c.layers[code], d = L.def;
    // the panel reads top-down as "what you see first", so it is the draw order
    // upside down - the arrows move a layer in what is on screen, not in an array
    const note = !d.present ? `<span class="${d.required ? 'w-bad' : 'count'}">${esc(d.problem)}</span>`
      : L.failed ? `<span class="w-bad">${esc(L.failed)}</span>`
      : d.problem ? `<span class="w-bad">${esc(d.problem)}</span>`
      : !d.aligned ? `<span class="w-warn">${d.native[0]}×${d.native[1]}, not on the tile
          grid - stretched to fit</span>`
      : `<span class="count">${d.file}${d.native[0] !== d.width
          ? ` · ${d.native[0]}×${d.native[1]}, sampled per tile` : ''}</span>`;
    return `<div class="cmlayer${L.on ? ' on' : ''}${d.present ? '' : ' off'}" data-code="${code}">
      <label class="chk"><input type="checkbox" ${L.on ? 'checked' : ''}
        ${d.present ? '' : 'disabled'} data-lcheck="${code}">
        <span class="cmnm">${esc(d.label)}</span></label>
      <span class="cmmove">
        <button data-lup="${code}" ${i === 0 ? 'disabled' : ''} title="Draw later (up)">▲</button>
        <button data-ldn="${code}" ${i === c.order.length - 1 ? 'disabled' : ''}
          title="Draw earlier (down)">▼</button></span>
      <input type="range" min="0" max="100" value="${Math.round(L.opacity * 100)}"
        data-lop="${code}" ${d.present && L.on ? '' : 'disabled'}>
      <span class="cmpct">${Math.round(L.opacity * 100)}%</span>
      <div class="cmnote">${note}</div>
    </div>`;
  }).reverse().join('');
}

function cmapWire(){
  const box = document.getElementById('cmLayers');
  box.querySelectorAll('[data-lcheck]').forEach(cb => cb.onchange = () => {
    const L = state.cmap.layers[cb.dataset.lcheck];
    L.on = cb.checked;
    activity('map layer', `${L.on ? 'showed' : 'hid'} ${cb.dataset.lcheck}`);
    cmapLoadLayers();
    cmapRepanel();
  });
  // `input` rather than `change`: an opacity slider that only answers on release
  // is a slider you cannot judge a blend with
  box.querySelectorAll('[data-lop]').forEach(sl => sl.oninput = () => {
    state.cmap.layers[sl.dataset.lop].opacity = (+sl.value) / 100;
    sl.parentElement.querySelector('.cmpct').textContent = sl.value + '%';
    cmapCompose(); cmapPaint();
  });
  box.querySelectorAll('[data-lup]').forEach(b => b.onclick = () => cmapMove(b.dataset.lup, 1));
  box.querySelectorAll('[data-ldn]').forEach(b => b.onclick = () => cmapMove(b.dataset.ldn, -1));
  cmapPointers(document.getElementById('cmCanvas'));
  cmapKeys();
  // The canvas is a flex child of a stage that moves with the window, and it is
  // the one thing on the page that has to be told.
  if(state.cmapRO) state.cmapRO.disconnect();
  state.cmapRO = new ResizeObserver(() => { cmapResize(); cmapPaint(); });
  state.cmapRO.observe(document.getElementById('cmStage'));
}

//: Redraw the panel in place. The canvas is deliberately not in it - rebuilding
//: the markup would throw away the <canvas> and its context with it.
function cmapRepanel(){
  const box = document.getElementById('cmLayers');
  if(!box) return;
  box.innerHTML = cmapLayersHtml();
  cmapWire();
}

function cmapMove(code, dir){
  const o = state.cmap.order, i = o.indexOf(code), j = i + dir;
  if(i < 0 || j < 0 || j >= o.length) return;
  o[i] = o[j]; o[j] = code;
  cmapCompose(); cmapPaint(); cmapRepanel();
}

/* ---------- the layer pictures ---------- */

/* Fetch every layer that is ticked and not already here, then compose.

   One <img> per layer, decoded by the browser, kept for the life of the
   screen. A layer is fetched at most once: the server caches the PNG on disk
   keyed by the file's mtime, so even a reload of the page is a read rather
   than a re-encode, and a layer repainted underneath us is a miss rather than
   a stale picture. */
async function cmapLoadLayers(){
  const c = state.cmap;
  const want = c.order.filter(code => c.layers[code].on
    && c.layers[code].def.present && !c.layers[code].img && !c.layers[code].loading);
  if(!want.length){ cmapCompose(); cmapPaint(); return; }
  await Promise.all(want.map(code => cmapFetchLayer(c, code)));
  if(state.cmap !== c) return;
  cmapCompose();
  cmapPaint();
  cmapRepanel();
}

//: How many times a layer picture is asked for before the failure is believed.
//: Same reasoning as core.js's `uiFailedFiles`: this server answers one request
//: per connection, the browser pools connections, and a request that never
//: makes it onto the wire is a thing that happens. It was measured happening
//: here - one of three layers asked for at once came back
//: ERR_CONNECTION_REFUSED, and the same URL answered 200 two milliseconds later.
const CMAP_LAYER_TRIES = 3;

/* One layer picture, with the retries and - only when they are all spent - the
   server's own sentence about why not.

   An <img> only ever learns *that* it failed. The server answers a broken layer
   with a reason and a status, and "map_heights.tga could not be decoded" is the
   whole of what the person needs, so it is worth one more request to get. It is
   read as JSON only when the status says it is an error: a 200 here means the
   picture was fine and the browser could not decode it, which is a different
   sentence, and parsing the PNG as JSON would print a third thing that is true
   of neither. */
function cmapFetchLayer(c, code){
  const L = c.layers[code];
  const url = `/api/map/layer?mod=${enc(c.mod)}&code=${enc(code)}&fit=${enc(L.def.fit)}`;
  L.loading = true;
  return new Promise(done => {
    const go = n => {
      const img = new Image();
      img.onload = () => { L.img = img; L.loading = false; L.failed = ''; done(); };
      img.onerror = () => {
        if(n < CMAP_LAYER_TRIES){ setTimeout(() => go(n + 1), 150 * n); return; }
        fetch(url, {cache: 'no-store'}).then(async r => {
          if(r.ok){ L.failed = 'the picture arrived, and the browser could not decode it'; return; }
          let why = `the server answered ${r.status}`;
          try{ const j = await r.json(); if(j && j.error) why = j.error; }catch(e){}
          L.failed = why;
        }).catch(e => { L.failed = errText(e); })
          .finally(() => {
            L.loading = false;
            if(state.cmap === c) cmapRepanel();
            done();
          });
      };
      // the query is what the browser keys its own failed-request cache on, so
      // a retry that looks identical can be answered from that failure
      img.src = n > 1 ? `${url}&try=${n}` : url;
    };
    go(1);
  });
}

/* THE COMPOSITE. Every ticked layer, in draw order, at one pixel per tile.

   This is the whole of the per-pixel work on this screen, it is at most a
   megapixel (descr_terrain.txt caps a map at 510x510), and it runs when the
   layer set, an opacity or the order changes - never on a pan, a zoom, a hover
   or a pick. `compKey` is what the composite was built from, so a repaint that
   changes nothing does not rebuild it. */
function cmapCompose(){
  const c = state.cmap;
  if(!c) return;
  const m = c.man;
  const shown = c.order.filter(code => c.layers[code].on && c.layers[code].img);
  const key = shown.map(code => `${code}:${c.layers[code].opacity}`).join('|');
  if(key === c.compKey && c.comp) return;
  if(!c.comp){
    c.comp = document.createElement('canvas');
    c.comp.width = m.width; c.comp.height = m.height;
  }
  const x = c.comp.getContext('2d');
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.clearRect(0, 0, m.width, m.height);
  // a map with every layer off is not a blank screen: it is the sea the tool
  // draws around the map, so the shape of the thing is still there
  x.fillStyle = '#0b0d11';
  x.fillRect(0, 0, m.width, m.height);
  x.imageSmoothingEnabled = false;
  for(const code of shown){
    const L = c.layers[code];
    x.globalAlpha = L.opacity;
    // A layer with no relationship to the tile grid - the front-end picture,
    // the water surface - is stretched over the map rather than left out. It
    // is a guess and the panel says so; leaving it out would be a different lie.
    x.drawImage(L.img, 0, 0, m.width, m.height);
  }
  x.globalAlpha = 1;
  c.compKey = key;
}

/* ---------- the view transform ---------- */

//: Where tile (tx,ty)'s top-left corner lands, in CSS pixels. Every other
//: screen coordinate in this file is built out of these two, on purpose.
function cmapX(tx){ const v = state.cmap.view; return v.ox + tx * v.zoom; }
function cmapY(ty){ const v = state.cmap.view; return v.oy + ty * v.zoom; }
//: And the exact inverse: the tile a point in the canvas is over.
function cmapTileAt(px, py){
  const v = state.cmap.view;
  return [Math.floor((px - v.ox) / v.zoom), Math.floor((py - v.oy) / v.zoom)];
}

function cmapCanvasSize(){
  const cv = document.getElementById('cmCanvas');
  return cv ? [cv.clientWidth || 1, cv.clientHeight || 1] : [1, 1];
}

/* The canvas's backing store, in device pixels.

   Kept separate from the drawing because it is the one thing that must NOT
   happen per frame: assigning to canvas.width clears the canvas and reallocates
   it, and doing that inside a pan is how a drag flickers. */
function cmapResize(){
  const cv = document.getElementById('cmCanvas');
  if(!cv) return false;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round((cv.clientWidth || 1) * dpr), h = Math.round((cv.clientHeight || 1) * dpr);
  if(cv.width === w && cv.height === h) return false;
  cv.width = w; cv.height = h;
  return true;
}

function cmapFit(){
  const c = state.cmap;
  if(!c) return;
  const [w, h] = cmapCanvasSize();
  const z = Math.min(w / c.man.width, h / c.man.height) * 0.98;
  c.view.zoom = Math.max(CMAP_ZOOM_MIN, Math.min(CMAP_ZOOM_MAX, z));
  c.view.ox = (w - c.man.width * c.view.zoom) / 2;
  c.view.oy = (h - c.man.height * c.view.zoom) / 2;
  c.view.fitted = true;
  cmapPaint();
}

//: Zoom about the middle of the canvas, for the buttons and the keys. The wheel
//: zooms about the cursor instead - see cmapPointers.
function cmapZoomBy(f){
  const [w, h] = cmapCanvasSize();
  cmapZoomAbout(state.cmap.view.zoom * f, w / 2, h / 2);
}
function cmapZoomTo(z){
  const [w, h] = cmapCanvasSize();
  cmapZoomAbout(z, w / 2, h / 2);
}

/* Zoom, keeping whatever is at (px,py) exactly where it is.

   The tile under a fixed point must not move, or you lose the coastline you
   leaned in to look at. Worked in tile coordinates rather than by scaling the
   origin, because the tile under the point is the thing being held still. */
function cmapZoomAbout(z, px, py){
  const v = state.cmap.view;
  z = Math.max(CMAP_ZOOM_MIN, Math.min(CMAP_ZOOM_MAX, z));
  if(z === v.zoom) return;
  const tx = (px - v.ox) / v.zoom, ty = (py - v.oy) / v.zoom;
  v.zoom = z;
  v.ox = px - tx * z; v.oy = py - ty * z;
  cmapPaint();
}

/* ---------- drawing ---------- */

/* One frame, or one rectangle of one.

   `dirty` is a CSS-pixel rectangle [x0,y0,x1,y1] or nothing for the whole
   canvas. Passing one is not an optimisation of the same drawing - it changes
   how much is drawn: the source rectangle is narrowed to the tiles the dirty
   rectangle covers, so moving the hover cursor one tile copies a few dozen
   pixels out of the composite instead of a screenful. */
function cmapPaint(dirty){
  const c = state.cmap;
  const cv = document.getElementById('cmCanvas');
  if(!c || !cv || !c.comp) return;
  const t0 = performance.now();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = cv.width / dpr, h = cv.height / dpr;
  const x = cv.getContext('2d');
  x.setTransform(dpr, 0, 0, dpr, 0, 0);

  const R = dirty || [0, 0, w, h];
  x.save();
  if(dirty){ x.beginPath(); x.rect(R[0], R[1], R[2] - R[0], R[3] - R[1]); x.clip(); }
  x.fillStyle = '#0e1013';
  x.fillRect(R[0], R[1], R[2] - R[0], R[3] - R[1]);

  const v = c.view, m = c.man;
  // the tiles this rectangle covers, clamped to the map
  const x0 = Math.max(0, Math.floor((R[0] - v.ox) / v.zoom));
  const y0 = Math.max(0, Math.floor((R[1] - v.oy) / v.zoom));
  const x1 = Math.min(m.width, Math.ceil((R[2] - v.ox) / v.zoom));
  const y1 = Math.min(m.height, Math.ceil((R[3] - v.oy) / v.zoom));
  if(x1 > x0 && y1 > y0){
    // Crisp once a tile is bigger than a screen pixel: this is a tool for
    // seeing which pixel a settlement stands on, and blur is the enemy of that.
    x.imageSmoothingEnabled = v.zoom < 1;
    x.drawImage(c.comp, x0, y0, x1 - x0, y1 - y0,
                cmapX(x0), cmapY(y0), (x1 - x0) * v.zoom, (y1 - y0) * v.zoom);
    cmapOverlay(x, x0, y0, x1, y1);
  }
  x.restore();

  // What the last frame cost, on screen. It is here because this sub-phase's
  // exit criterion is a frame rate, and a number nobody can see is a claim.
  c.ms = performance.now() - t0;
  cmapReadout();
}

/* Everything that is not a layer: the map's edge, the markers, the selected
   region's outline and the cell under the cursor. Clipped to the tile range the
   caller is repainting, so a dirty-rect frame does not walk 200 markers. */
function cmapOverlay(x, s0, t0, s1, t1){
  const c = state.cmap, v = c.view;

  if(c.outline && c.outline.width){
    x.imageSmoothingEnabled = false;
    x.drawImage(c.outline, s0, t0, s1 - s0, t1 - t0,
                cmapX(s0), cmapY(t0), (s1 - s0) * v.zoom, (t1 - t0) * v.zoom);
  }

  if(v.zoom >= CMAP_GLYPH_ZOOM){
    // A glyph is drawn ON the tile, from the same two lines as everything else,
    // so it cannot drift off the pixel it is about however far you zoom in.
    for(const r of c.man.regions){
      for(const [p, kind] of [[r.settlement, 's'], [r.port, 'p']]){
        if(!p) continue;
        if(p[0] < s0 - 1 || p[0] > s1 || p[1] < t0 - 1 || p[1] > t1) continue;
        const X = cmapX(p[0]), Y = cmapY(p[1]), z = v.zoom;
        x.lineWidth = Math.max(1, z / 8);
        x.strokeStyle = kind === 's' ? 'rgba(255,255,255,.9)' : 'rgba(90,200,255,.95)';
        x.beginPath();
        if(kind === 's'){
          x.moveTo(X + z / 2, Y - z * .35); x.lineTo(X + z * 1.35, Y + z / 2);
          x.lineTo(X + z / 2, Y + z * 1.35); x.lineTo(X - z * .35, Y + z / 2);
          x.closePath();
        }else{
          x.arc(X + z / 2, Y + z / 2, z * .8, 0, Math.PI * 2);
        }
        x.stroke();
      }
    }
  }

  if(c.hover){
    const [hx, hy] = c.hover;
    if(hx >= s0 - 1 && hx <= s1 && hy >= t0 - 1 && hy <= t1){
      x.lineWidth = 1;
      x.strokeStyle = 'rgba(200,164,92,.95)';
      // +0.5 so a one-pixel stroke lands on a pixel rather than across two
      x.strokeRect(cmapX(hx) - 0.5, cmapY(hy) - 0.5, v.zoom + 1, v.zoom + 1);
    }
  }

  // the map's own edge, so an all-sea corner is not mistaken for the window
  x.lineWidth = 1;
  x.strokeStyle = 'rgba(120,132,150,.55)';
  x.strokeRect(cmapX(0) - 0.5, cmapY(0) - 0.5,
               c.man.width * v.zoom + 1, c.man.height * v.zoom + 1);
}

//: The screen rectangle one tile occupies, grown by a pixel so a stroked
//: outline is inside the rectangle that repaints it.
function cmapCellRect(tx, ty){
  const z = state.cmap.view.zoom;
  return [cmapX(tx) - 2, cmapY(ty) - 2, cmapX(tx) + z + 2, cmapY(ty) + z + 2];
}

/* ---------- pan, zoom, hover and pick ---------- */

/* Lifted from the UV editor's pointer handling (viewer3d.js), including its one
   good rule: a press that never travelled is a pick, one that did was a pan. It
   is the difference between clicking a region and losing your place.

   Drawn synchronously in the handler rather than from requestAnimationFrame. A
   frame costs a fraction of a millisecond here, and scheduling it would put the
   picture one event behind the pointer - which is the exact thing named as this
   sub-phase's anti-goal. */
function cmapPointers(cv){
  let last = null, moved = 0;
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('pointerdown', e => {
    last = [e.clientX, e.clientY]; moved = 0;
    cv.setPointerCapture(e.pointerId);
  });
  cv.addEventListener('pointerup', e => {
    if(last && moved < CMAP_DRAG_SLOP && state.cmap) cmapPick(cmapEventTile(cv, e));
    last = null;
    try{ cv.releasePointerCapture(e.pointerId); }catch(err){}
  });
  cv.addEventListener('pointerleave', () => {
    const c = state.cmap;
    if(!c || !c.hover) return;
    const was = cmapCellRect(...c.hover);
    c.hover = null;
    cmapPaint(was);
  });
  cv.addEventListener('pointermove', e => {
    const c = state.cmap;
    if(!c) return;
    if(last){
      const dx = e.clientX - last[0], dy = e.clientY - last[1];
      moved += Math.abs(dx) + Math.abs(dy);
      last = [e.clientX, e.clientY];
      c.view.ox += dx; c.view.oy += dy;
      // a pan moves everything, so this is the one interaction that is a whole
      // frame - and a whole frame is one drawImage of a sub-rect
      cmapPaint();
      return;
    }
    cmapHover(cmapEventTile(cv, e));
  });
  cv.addEventListener('wheel', e => {
    if(!state.cmap) return;
    e.preventDefault();
    const r = cv.getBoundingClientRect();
    cmapZoomAbout(state.cmap.view.zoom * (e.deltaY > 0 ? 1 / 1.15 : 1.15),
                  e.clientX - r.left, e.clientY - r.top);
  }, {passive: false});
}

function cmapEventTile(cv, e){
  const r = cv.getBoundingClientRect();
  return cmapTileAt(e.clientX - r.left, e.clientY - r.top);
}

/* The hover cell, in two rectangles.

   Rule 3, and the whole reason it is worth having: the cell the pointer left
   and the cell it entered are repainted, and nothing else is. On a 4K screen
   that is two rectangles of a few hundred pixels instead of eight million. */
function cmapHover(tile){
  const c = state.cmap;
  const [tx, ty] = tile;
  const on = tx >= 0 && ty >= 0 && tx < c.man.width && ty < c.man.height;
  const next = on ? [tx, ty] : null;
  const same = (!next && !c.hover) || (next && c.hover && next[0] === c.hover[0]
                                       && next[1] === c.hover[1]);
  if(same){ cmapReadout(); return; }
  const was = c.hover ? cmapCellRect(...c.hover) : null;
  c.hover = next;
  if(next) cmapPaint(cmapCellRect(tx, ty));
  if(was) cmapPaint(was);
  if(!next && !was) cmapReadout();
}

/* What is under the cursor, said in the three things worth saying: the tile,
   the coordinates descr_strat.txt would write for it, and the region.

   No round trip and no per-pixel work. The colour comes off the composite's
   own source - the regions layer as the browser decoded it - and the region
   comes out of the manifest's table by packed key, which is the same key the
   Python index is built on. */
function cmapReadout(){
  const c = state.cmap, el = document.getElementById('cmRead');
  if(!el) return;
  // A pan is one of these per frame, and writing text into the DOM forces a
  // style recalculation whether the text changed or not. Only what moved is
  // written; `said` is what is on screen already.
  const z = c.view.zoom;
  const zt = `${z >= 1 ? z.toFixed(z < 10 ? 1 : 0) : z.toFixed(2)}× · `
           + `${c.man.width}×${c.man.height}`;
  const ze = document.getElementById('cmZoom');
  if(ze && c.saidZoom !== zt){ ze.textContent = zt; c.saidZoom = zt; }
  const pe = document.getElementById('cmPerf');
  const pt = `${c.ms.toFixed(2)} ms/frame`;
  if(pe && c.saidPerf !== pt){ pe.textContent = pt; c.saidPerf = pt; }

  let html = 'move the pointer over the map';
  if(c.hover){
    const [tx, ty] = c.hover;
    const r = cmapRegionAt(tx, ty);
    // game y, the transform descr_strat.txt is written in
    const gy = c.man.height - 1 - ty;
    html = `<b>${tx}, ${ty}</b> image · <b>${tx}, ${gy}</b> game · `
      + (r === 'settlement' ? '<span class="w-good">settlement pixel</span>'
       : r === 'port' ? '<span class="w-good">port pixel</span>'
       : r ? `${cmapRegionName(r)}${r.id >= 0 ? ` <span class="count">#${r.id}</span>` : ''}`
       : '<span class="count">no region</span>');
  }
  if(c.saidRead !== html){ el.innerHTML = html; c.saidRead = html; }
}

/* The region a tile belongs to, or the string 'settlement' / 'port' when the
   tile is one of the two markers.

   Reads the regions layer's own pixels through a 1x1 scratch canvas rather than
   keeping a full ImageData copy: a getImageData of one pixel is microseconds,
   and the alternative is another megabyte held for the life of the screen. */
/* What to call a region on screen.

   A colour with no record in descr_regions.txt is either a hole in the mod or
   it is the sea, and the manifest carries the count that tells them apart -
   how many of its tiles the engine treats as sea. Vanilla's four undeclared
   colours are all ocean; DaC's ocean is one of two, and the other is a real
   517-tile province nobody wrote down. */
function cmapRegionName(r){
  if(r.name) return esc(r.name);
  if(r.pixels && r.sea * 2 >= r.pixels) return 'sea';
  return 'a region <code>descr_regions.txt</code> never declares';
}

function cmapRegionAt(tx, ty){
  const c = state.cmap, L = c.layers.regions;
  if(!L || !L.img) return null;
  if(tx < 0 || ty < 0 || tx >= c.man.width || ty >= c.man.height) return null;
  if(!c.probe){
    c.probe = document.createElement('canvas');
    c.probe.width = c.man.width; c.probe.height = c.man.height;
    const px = c.probe.getContext('2d', {willReadFrequently: true});
    px.imageSmoothingEnabled = false;
    px.drawImage(L.img, 0, 0);
  }
  const d = c.probe.getContext('2d', {willReadFrequently: true})
              .getImageData(tx, ty, 1, 1).data;
  const k = (d[0] << 16) | (d[1] << 8) | d[2];
  const mk = c.man.markers;
  if(k === ((mk.settlement[0] << 16) | (mk.settlement[1] << 8) | mk.settlement[2]))
    return 'settlement';
  if(k === ((mk.port[0] << 16) | (mk.port[1] << 8) | mk.port[2])) return 'port';
  return c.byKey.get(k) || null;
}

function cmapPick(tile){
  const c = state.cmap;
  const [tx, ty] = tile;
  const hit = cmapRegionAt(tx, ty);
  const r = (hit && typeof hit === 'object') ? hit : null;
  c.sel = r;
  activity('map pick', `${c.mod} ${tx},${ty} -> ${r ? r.name || 'undeclared' : hit || 'nothing'}`);
  cmapOutline(r);
  cmapPaint();
  cmapPickPanel(tx, ty, hit);
}

/* The selected region, outlined.

   The one per-pixel pass in this file, and it is on the click rather than on
   the pointer: one scan of the region layer marking every pixel of this region
   that has a neighbour outside it. Cached by region, because clicking back and
   forth between two provinces should not pay for it twice. */
function cmapOutline(r){
  const c = state.cmap;
  if(!r){ c.outline = null; c.outlineKey = -1; return; }
  if(c.outlineKey === r.key) return;
  const L = c.layers.regions;
  if(!L || !L.img){ c.outline = null; return; }
  const W = c.man.width, H = c.man.height;
  if(!c.probe) cmapRegionAt(0, 0);           // builds the scratch copy
  const src = c.probe.getContext('2d', {willReadFrequently: true})
                .getImageData(0, 0, W, H).data;
  const out = document.createElement('canvas');
  out.width = W; out.height = H;
  const im = out.getContext('2d').createImageData(W, H);
  const dst = im.data;
  const want = r.key;
  // one packed key per pixel, once, so the neighbour tests below are integer
  // comparisons rather than four more shifts each
  const keys = new Int32Array(W * H);
  for(let i = 0, n = W * H; i < n; i++)
    keys[i] = (src[i * 4] << 16) | (src[i * 4 + 1] << 8) | src[i * 4 + 2];
  for(let y = 0; y < H; y++){
    for(let xx = 0; xx < W; xx++){
      const j = y * W + xx;
      if(keys[j] !== want) continue;
      // The map's own edge counts as an edge of the region: a province running
      // off the side of the map is outlined there too, rather than opening.
      const edge = xx === 0     || keys[j - 1] !== want
                || xx === W - 1 || keys[j + 1] !== want
                || y === 0      || keys[j - W] !== want
                || y === H - 1  || keys[j + W] !== want;
      if(!edge) continue;
      const i = j * 4;
      dst[i] = 200; dst[i + 1] = 164; dst[i + 2] = 92; dst[i + 3] = 255;
    }
  }
  out.getContext('2d').putImageData(im, 0, 0);
  c.outline = out; c.outlineKey = r.key;
}

/* The clicked region, as a card. Read-only here on purpose: an editable panel
   is 16d's, and it needs the religion totals and the resource vocabulary that
   16d brings with it. */
function cmapPickPanel(tx, ty, hit){
  const el = document.getElementById('cmPick');
  if(!el) return;
  const c = state.cmap;
  if(!hit){ el.innerHTML = `<div class="k">Picked</div>
    <div class="count">${tx}, ${ty} has no region on it.</div>`; return; }
  if(typeof hit === 'string'){ el.innerHTML = `<div class="k">Picked</div>
    <div class="count">${tx}, ${ty} is the ${esc(hit)} marker pixel.
    It belongs to whichever region surrounds it.</div>`; return; }
  const g = p => p ? `${p[0]}, ${c.man.height - 1 - p[1]}` : '-';
  el.innerHTML = `<div class="k">Picked <span class="count">read-only until 16d</span></div>
    <div class="cmcard">
      <div class="nm"><i style="background:rgb(${hit.rgb.join(',')})"></i>
        ${cmapRegionName(hit)}</div>
      <div class="cmkv">
        <span>Region ID</span><b>${hit.id >= 0 ? hit.id : '-'}</b>
        <span>Colour</span><b>${hit.rgb.join(', ')}</b>
        <span>Settlement</span><b>${esc(hit.settlement_name || '-')}</b>
        <span>Owner</span><b>${esc(hit.faction || '-')}</b>
        <span>Rebels</span><b>${esc(hit.rebels || '-')}</b>
        <span>Tiles</span><b>${hit.pixels}${hit.sea
          ? ` <span class="count">${hit.sea} of them sea</span>` : ''}</b>
        <span>Settlement at</span><b>${g(hit.settlement)} <span class="count">game</span></b>
        <span>Port at</span><b>${g(hit.port)} <span class="count">game</span></b>
      </div>
      ${hit.declared || hit.sea * 2 >= hit.pixels ? '' : `<div class="w-warn">This colour is
        painted on the map and declared nowhere in <code>descr_regions.txt</code>, and none
        of it is sea. The game has no region for this land.</div>`}
    </div>`;
}

/* ---------- keys ---------- */

//: Bound once and left bound: the handler asks whether this screen is on top
//: before it does anything, which is cheaper than wiring and unwiring it.
function cmapKeys(){
  if(state.cmapKeys) return;
  state.cmapKeys = true;
  document.addEventListener('keydown', e => {
    if(state.mode !== 'campmap' || !state.cmap) return;
    if(overlay.classList.contains('open')) return;
    const t = e.target.tagName;
    if(t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
    if(e.key === '0'){ cmapFit(); }
    else if(e.key === '1'){ cmapZoomTo(1); }
    else if(e.key === '+' || e.key === '='){ cmapZoomBy(1.4); }
    else if(e.key === '-' || e.key === '_'){ cmapZoomBy(1 / 1.4); }
    else if(e.key === 'Escape' && state.cmap.sel){
      state.cmap.sel = null; cmapOutline(null); cmapPaint();
      cmapPickPanel(0, 0, null);
    }
    else return;
    e.preventDefault();
  });
}
