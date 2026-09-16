/* mapfe.js - Campaign Map: the front-end picture, framed (37b, T3)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE FRONT-END PANEL - Phase 37b.

   Every name here starts `cfe`, and none of them existed anywhere else in the
   tree before this phase - checked, the way 16g checked `cq` and 36 checked
   `rcl`.

   WHAT THIS SCREEN WAS DOING WRONG, AND IT IS WORTH SAYING PLAINLY. Every
   ticked layer went into `cmapCompose`'s canvas, which is width-by-height
   TILES - 510x487 on both big mods - and the view then scaled that canvas onto
   the stage. map_FE.tga has no relationship to the tile grid at all, so DaC's
   768x768 picture was being squeezed into 510x487 and then scaled back up, and
   Third Age Reforged's 320x275 stretched up and scaled back down. That is
   exactly the "scaling up and then scaling down again" T3 exists to avoid, and
   it was happening every frame.

   SO THE PICTURE IS NOT IN THE COMPOSITE ANY MORE. `cmapCompose` skips it and
   `cfeDraw` puts it on the canvas itself, as one drawImage of the whole file
   onto the frame's rectangle. At the FE zoom that rectangle is exactly the
   file's own pixel size, so the picture goes down one image pixel per screen
   pixel and nothing resamples it at all.

   THE FRAME IS THE AUTHOR'S AND THE PANEL NEVER COMPUTES ONE. Python proposes
   it - the smallest rect of the picture's shape that holds the whole grid -
   and this file drags it about and posts it back. A front-end picture cannot
   be registered onto the map from its own pixels (unittransfer/mapfe.py has
   the measurements and the mod whose picture has a painted border round it),
   so there is nothing here to be clever with and being clever would be wrong.

   ONE ZOOM DOES IT BECAUSE THE FRAME CARRIES THE PICTURE'S ASPECT. The view
   transform in campmap.js is a single scalar - `cmapX(tx) = ox + tx*zoom` -
   and it stays that way. A frame shaped like the picture is what makes one
   number enough; that is the whole trick and it belongs to `mapfe.frame`.
   ===================================================================== */

//: How thick the frame's outline is drawn, in CSS pixels. One line, not a
//: shaded overlay: the point of the frame is to see the map under it.
const CFE_LINE = 1.5;

//: The handle squares at the frame's corners, in CSS pixels.
const CFE_GRIP = 9;

//: Python refuses a frame under four tiles a side (mapfe.MIN_TILES); stop at
//: the refusal rather than posting something that will come back an error.
const CFE_MIN_TILES = 4;

//: The layers a fresh export starts from - the two that are on when the map
//: opens, so the first export is a picture of what is on the screen.
const CFE_START = ['ground_types', 'regions'];


function cfeNew(mod){
  return {mod, open: false, on: false, view: null, frame: null,
          drag: null, busy: false, msg: '', wrote: null};
}


function cfeOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cfe || state.cfe.mod !== c.mod) state.cfe = cfeNew(c.mod);
  cfePaint();
}


function cfeToggle(){
  const k = state.cfe;
  if(!k) return;
  k.open = !k.open;
  activity('front-end map', k.open ? 'opened the front-end panel'
                                   : 'closed the front-end panel');
  if(k.open && !k.view) cfeLoad(); else cfePaint();
}


/* What the picture is, and the frame Python proposes for it.

   Read once per campaign and kept. Nothing here is asked again on a drag: the
   frame moves in this file and only goes back to Python when something is
   exported. */
async function cfeLoad(){
  const c = state.cmap, k = state.cfe;
  if(!c || !k) return;
  k.busy = true; k.msg = ''; cfePaint();
  try{
    const r = await api.post('/api/map/fe_view',
      {mod: c.mod, campaign: c.campaign || ''}, {label: 'front-end map'});
    if(r.error){ k.msg = r.error; k.view = null; }
    else { k.view = r; k.frame = Object.assign({}, r.frame); }
  }catch(e){
    if(e === ABORTED) return;
    k.msg = String(e && e.message || e);
  }finally{
    k.busy = false; cfePaint(); cmapPaint();
  }
}


/* ---------- the zoom that makes the picture 1:1 ---------- */

/* Put the view where one image pixel is one screen pixel.

   `view.zoom` came from Python as picture-width over frame-width, and the
   frame has the picture's aspect, so the same number is picture-height over
   frame-height and the one scalar the view transform holds is enough. The
   canvas is then centred on the frame rather than on the map, because the
   frame is what is being authored. */
function cfeZoom(){
  const c = state.cmap, k = state.cfe;
  if(!c || !k || !k.view || !k.frame) return;
  const [w, h] = cmapCanvasSize();
  const v = c.view, f = k.frame;
  v.zoom = k.view.zoom;
  v.ox = w / 2 - (f.x + f.w / 2) * v.zoom;
  v.oy = h / 2 - (f.y + f.h / 2) * v.zoom;
  v.fitted = false;
  activity('front-end map',
    `FE zoom: ${k.view.native ? k.view.native.join('×') : 'the frame'} at 1:1`);
  cmapPaint();
}


//: Is the view at the FE zoom right now? Within a thousandth, because the
//: wheel lands on values that print the same and are not equal.
function cfeAtZoom(){
  const c = state.cmap, k = state.cfe;
  return !!(c && k && k.view && Math.abs(c.view.zoom - k.view.zoom) < 1e-3);
}


/* ---------- the picture on the canvas ---------- */

/* The front-end picture, at its own resolution, on the frame's rectangle.

   Called from `cmapPaint` before the composite, because the picture's draw
   order is 0 - it is the bottom of the stack and everything else is drawn on
   top of it. It is deliberately NOT clipped to the map: the frame runs past
   the grid's edge on every installed mod, and a picture cut off at the
   coastline would be a lie about what is being authored.

   `imageSmoothingEnabled` is off at or above 1:1 for the reason the rest of
   this screen turns it off - a picture being traced wants a hard pixel - and
   on below it, where a 768-pixel image in a 200-pixel box aliases badly
   without it. */
function cfeDraw(x){
  const c = state.cmap, k = state.cfe;
  if(!c || !k || !k.frame) return;
  const L = c.layers && c.layers.fe;
  if(!L || !L.on || !(L.cv || L.img)) return;
  const f = k.frame, v = c.view;
  const dx = cmapX(f.x), dy = cmapY(f.y);
  const dw = f.w * v.zoom, dh = f.h * v.zoom;
  if(dw <= 0 || dh <= 0) return;
  const img = L.cv || L.img;
  const nat = img.naturalWidth || img.width || 1;
  x.save();
  x.globalAlpha = L.opacity;
  x.imageSmoothingEnabled = dw < nat;
  x.drawImage(img, dx, dy, dw, dh);
  x.restore();
}


/* The frame's outline and its four corner handles.

   Drawn last, over everything, because it is a control rather than a layer.
   Only while the panel is open: the frame is not a thing the map has, it is a
   thing this panel is editing, and leaving it on the canvas after the panel
   closes would be one more line nobody asked for. */
function cfeDrawFrame(x){
  const c = state.cmap, k = state.cfe;
  if(!c || !k || !k.open || !k.frame) return;
  const f = k.frame, v = c.view;
  const dx = cmapX(f.x), dy = cmapY(f.y);
  const dw = f.w * v.zoom, dh = f.h * v.zoom;
  x.save();
  x.lineWidth = CFE_LINE;
  x.setLineDash([6, 4]);
  x.strokeStyle = 'rgba(255,255,255,0.9)';
  x.strokeRect(dx, dy, dw, dh);
  x.setLineDash([]);
  x.fillStyle = 'rgba(255,255,255,0.9)';
  const g = CFE_GRIP;
  [[dx, dy], [dx + dw, dy], [dx, dy + dh], [dx + dw, dy + dh]]
    .forEach(([px, py]) => x.fillRect(px - g / 2, py - g / 2, g, g));
  x.restore();
}


/* ---------- moving the frame ---------- */

/* Which grip a canvas point is on, or 'move' inside, or null outside.

   Answered in CSS pixels rather than tiles, so a grip stays the same size to
   the hand at every zoom - the same rule 17d's markers follow. */
function cfeHit(px, py){
  const c = state.cmap, k = state.cfe;
  if(!c || !k || !k.open || !k.frame) return null;
  const f = k.frame, v = c.view;
  const x0 = cmapX(f.x), y0 = cmapY(f.y);
  const x1 = x0 + f.w * v.zoom, y1 = y0 + f.h * v.zoom;
  const near = (a, b) => Math.abs(a - b) <= CFE_GRIP;
  if(near(px, x0) && near(py, y0)) return 'nw';
  if(near(px, x1) && near(py, y0)) return 'ne';
  if(near(px, x0) && near(py, y1)) return 'sw';
  if(near(px, x1) && near(py, y1)) return 'se';
  if(px >= x0 && px <= x1 && py >= y0 && py <= y1) return 'move';
  return null;
}


function cfeDragStart(px, py){
  const k = state.cfe, c = state.cmap;
  const grip = cfeHit(px, py);
  if(!grip) return false;
  k.drag = {grip, px, py, from: Object.assign({}, k.frame)};
  return true;
}


/* Move or resize, holding the aspect ratio.

   THE ASPECT IS NOT NEGOTIABLE and that is why a corner drag reads one axis
   and computes the other. A frame that stopped being the picture's shape would
   need two zooms to draw the picture 1:1, the view transform has one, and the
   panel would quietly start lying about "native size". The corner opposite the
   one being dragged is held still, which is what makes it feel like a resize
   rather than a scale about the middle. */
function cfeDragMove(px, py){
  const k = state.cfe, c = state.cmap;
  if(!k || !k.drag || !c) return;
  const d = k.drag, v = c.view, f0 = d.from;
  const dtx = (px - d.px) / v.zoom, dty = (py - d.py) / v.zoom;
  if(d.grip === 'move'){
    k.frame = {x: f0.x + dtx, y: f0.y + dty, w: f0.w, h: f0.h};
  }else{
    const ar = f0.w / f0.h;
    const east = d.grip === 'ne' || d.grip === 'se';
    const south = d.grip === 'se' || d.grip === 'sw';
    let w = east ? f0.w + dtx : f0.w - dtx;
    w = Math.max(CFE_MIN_TILES, w);
    const h = w / ar;
    k.frame = {x: east ? f0.x : f0.x + f0.w - w,
               y: south ? f0.y : f0.y + f0.h - h,
               w, h};
  }
  cmapPaint();
  cfeFigures();
}

function cfeDragEnd(){
  const k = state.cfe;
  if(!k || !k.drag) return;
  k.drag = null;
  cfePaint();
}


function cfeReset(){
  const k = state.cfe;
  if(!k || !k.view) return;
  k.frame = Object.assign({}, k.view.frame);
  activity('front-end map', 'put the frame back to the proposed one');
  cfePaint(); cmapPaint();
}


/* ---------- the export ---------- */

async function cfeExport(){
  const c = state.cmap, k = state.cfe;
  if(!c || !k || !k.frame || k.busy) return;
  k.busy = true; k.msg = ''; k.wrote = null; cfePaint();
  try{
    // the layers that are ticked, in the order the screen draws them, minus
    // the picture itself - Python refuses that one by name and is right to
    const layers = c.order.filter(code => code !== 'fe' && c.layers[code].on)
      .map(code => ({code, opacity: c.layers[code].opacity}));
    const r = await api.post('/api/map/fe_export', {
      mod: c.mod, campaign: c.campaign || '', frame: k.frame,
      layers: layers.length ? layers : CFE_START.map(code => ({code, opacity: 1})),
      reveal: true}, {label: 'front-end export'});
    if(r.error) k.msg = r.error;
    else {
      k.wrote = r;
      activity('front-end map',
        `wrote ${(r.files[0] || {}).name} (${(r.files[0] || {}).width}×${(r.files[0] || {}).height})`);
    }
  }catch(e){
    if(e === ABORTED) return;
    k.msg = String(e && e.message || e);
  }finally{
    k.busy = false; cfePaint();
  }
}


/* ---------- drawing the panel ---------- */

function cfePaint(){
  const el = document.getElementById('cmFE');
  if(!el) return;
  el.innerHTML = cfeHtml();
  cfeWire();
}


//: The two numbers that change on every drag, updated without rebuilding the
//: panel - a drag that reran innerHTML would drop the pointer capture.
function cfeFigures(){
  const el = document.getElementById('cfeFigs');
  const k = state.cfe;
  if(!el || !k || !k.frame) return;
  el.textContent = cfeFigureText();
}


function cfeFigureText(){
  const k = state.cfe;
  if(!k || !k.frame || !k.view) return '';
  const f = k.frame, size = k.view.size || [0, 0];
  const per = f.w ? size[0] / f.w : 0;
  return `${f.w.toFixed(1)}×${f.h.toFixed(1)} tiles at `
       + `${f.x.toFixed(1)},${f.y.toFixed(1)} · ${per.toFixed(3)} px per tile`;
}


function cfeHtml(){
  const k = state.cfe, c = state.cmap;
  if(!k) return '';
  const head = `<div class="cmrow cmhdr" onclick="cfeToggle()">
      <b>Front-end map</b>
      <span class="count">${k.open ? '▾' : '▸'}</span>
    </div>`;
  if(!k.open) return head;
  if(k.busy && !k.view) return head + `<div class="cmnote">reading…</div>`;
  const v = k.view;
  if(!v) return head + `<div class="cmnote w-warn">${esc(k.msg || 'nothing read')}</div>`;

  const rows = [];
  if(v.present){
    rows.push(`<div class="cmrow"><span>The file</span>
      <span class="count">${v.native[0]}×${v.native[1]}, ${v.depth}-bit</span></div>`);
    rows.push(`<div class="cmnote"><code>${esc(v.rel)}</code></div>`);
  }else{
    rows.push(`<div class="cmnote w-warn">${esc(v.problem)}</div>`);
  }
  if(v.was){
    rows.push(`<div class="cmnote">Before this panel the picture was
      ${esc(v.was)} to get onto the canvas. It is now drawn at its own size on
      the frame below, so nothing resamples it.</div>`);
  }
  rows.push(`<div class="cmrow"><span>The frame</span>
    <span class="count" id="cfeFigs">${esc(cfeFigureText())}</span></div>`);
  rows.push(`<div class="cmnote">The frame is which rectangle of the map the
    picture is a picture of. It starts as the smallest one the picture's shape
    can be and still hold the whole map; drag it or its corners to move it, and
    the shape is held because that is what lets one zoom draw the picture 1:1.
    Nothing can work it out from the picture - one installed mod's has a
    painted border round the map and two are not maps at all.</div>`);
  rows.push(`<div class="cmbarrow">
    <button onclick="cfeZoom()" class="${cfeAtZoom() ? 'on' : ''}"
      title="Put the view where one screen pixel is one pixel of map_FE.tga.
No resampling in either direction - that is the whole point of the mode.">
      ⊹ FE zoom</button>
    <button onclick="cfeReset()">↺ Proposed frame</button>
    <button onclick="cfeExport()" ${k.busy ? 'disabled' : ''}
      title="Compose the ticked layers at the picture's own size and write a TGA
into the cache, through this mod's own map_FE.tga header.">
      ⭳ Export at ${v.size[0]}×${v.size[1]}</button>
  </div>`);
  if(k.msg) rows.push(`<div class="cmnote w-warn">${esc(k.msg)}</div>`);
  if(k.wrote && k.wrote.files && k.wrote.files[0]){
    const f = k.wrote.files[0];
    rows.push(`<div class="cmnote">Wrote <b>${esc(f.name)}</b> -
      ${f.width}×${f.height}, ${f.depth}-bit, ${(f.bytes).toLocaleString()} bytes,
      header ${esc(f.header)}. It is in the export cache, not in the mod.</div>`);
  }
  if(!(c && c.layers && c.layers.fe && c.layers.fe.on)){
    rows.push(`<div class="cmnote">The front-end layer is not ticked, so the
      picture is not on the canvas - the frame is. Key <b>1</b> ticks it.</div>`);
  }
  return head + rows.join('');
}


function cfeWire(){
  // every control is an inline onclick; nothing here needs a listener. Kept as
  // a function so the panel's shape matches every other one on this screen.
}
