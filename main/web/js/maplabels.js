/* maplabels.js - Campaign Map: settlement names on the map

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   SETTLEMENT NAMES ON THE MAP - Phase 20c, T4.

   Every name here starts `cln`, and there was no `cln` name anywhere in the
   tree before this phase - checked, the way every panel on this screen was.

   WHAT IS TAKEN FROM TWMAPREADER, AND WHAT IS CHANGED. Its `MapView` is the
   only one of the four references that places names at all, and its author's
   own verdict is "fairly limited but better than none at all", which is the
   bar this is held to.

     * TAKEN - the candidate positions. A name starts to the RIGHT of its
       marker, centred on it; when that collides it is nudged down and then up a
       little at a time, and then the same again on the LEFT. That order is the
       one a reader's eye expects, and it is his.
     * CHANGED - a name that fits nowhere is NOT drawn. His is drawn anyway with
       an `overlapping` flag, which is two names on top of each other and
       neither of them readable. Here it is left off and counted - the readout
       says "84 of 199 named" - and the next zoom level up has room for it. The
       tooltip names every settlement regardless.
     * CHANGED - the order. His walks the file; this places the biggest
       provinces first, so what a zoomed-out map keeps is the names worth
       keeping rather than whichever came first in descr_regions.txt.
     * CHANGED - markers are obstacles. A name may not cover somebody else's
       settlement, only other names; his tests name against name.
     * ADDED - above and below, as the last two places to try.

   CONSTANT ON SCREEN, WHATEVER THE ZOOM. The font is one size, and the marker a
   name sits beside is drawn at one size when nothing else is marking the
   settlement. A name that grew with the map would be unreadable at one end and
   a wall at the other, and 17d already made the same ruling about markers.

   PAN IS FREE; ZOOM IS ONE LAYOUT. The placement is worked out in the map's
   own pixels at one zoom - a tile's centre times the zoom - so a pan, which
   moves everything by the same amount, is the same layout drawn somewhere else.
   Only a zoom asks again, and it costs a few milliseconds for two hundred
   names. A dirty-rect frame draws the names whose boxes it touches and no
   others, which is rule 4 kept.

   A NAME IS NOT A LAYER. The stack is the ten files the map is made of (20a),
   so this is a switch on the toolbar beside 17e's tooltip, and it is part of
   `cmapLayerState` so a saved view keeps it.
   ===================================================================== */

//: The one size a name is drawn at, in CSS pixels.
const CLN_FONT_PX = 11;
const CLN_FONT = `600 ${CLN_FONT_PX}px system-ui,"Segoe UI",sans-serif`;
//: A name's box: the text plus room for the dark halo it is drawn with.
const CLN_BOX_H = CLN_FONT_PX + 4;
const CLN_HALO = 2;
//: Between a marker's edge and the name beside it.
const CLN_GAP = 3;
//: The marker drawn under a name when nothing else marks the settlement - at a
//: zoom where 16c's diamond is not drawn and 17d's layer is off.
const CLN_DOT = 5;
//: How far a name is nudged up or down before the other side is tried, as a
//: share of its own height, and in what steps. His `maxYShift`, in his units.
const CLN_NUDGE_STEP = 2;

/* ---------- the layout, which is pure ---------- */

/* Where every name goes at one zoom. No state, no DOM - node runs this.

   `items`    [{key, tx, ty, text, prio}] - a tile, the words, and how much it
              matters. Higher prio is placed first.
   `zoom`     CSS pixels per tile.
   `measure`  text -> its width in CSS pixels. The browser passes the canvas's
              own measureText; a test passes something it can predict.
   `obstacle` the side of the square each marker occupies, in CSS pixels.

   Returns {boxes, hidden, total}: a box is {key, text, ax, ay, x, y, w, h} in
   the map's own pixels at this zoom (a tile's centre is (tx + .5) * zoom), so
   drawing one is adding the view's offset and nothing else. */
function clnLayout(items, zoom, measure, obstacle){
  const grid = new Map(), CELL = 64;
  const cells = b => {
    const out = [];
    for(let gx = Math.floor(b.x / CELL); gx <= Math.floor((b.x + b.w) / CELL); gx++)
      for(let gy = Math.floor(b.y / CELL); gy <= Math.floor((b.y + b.h) / CELL); gy++)
        out.push(gx + ',' + gy);
    return out;
  };
  const put = b => { for(const k of cells(b)){
    let a = grid.get(k); if(!a) grid.set(k, a = []); a.push(b); } };
  const hits = b => {
    for(const k of cells(b)) for(const o of (grid.get(k) || []))
      if(b.x < o.x + o.w && o.x < b.x + b.w && b.y < o.y + o.h && o.y < b.y + b.h)
        return true;
    return false;
  };

  const half = Math.max(1, obstacle) / 2;
  // every marker first, so no name is ever laid over a settlement
  for(const it of items){
    const ax = (it.tx + 0.5) * zoom, ay = (it.ty + 0.5) * zoom;
    put({x: ax - half, y: ay - half, w: half * 2, h: half * 2});
  }

  const order = items.slice().sort((a, b) => (b.prio - a.prio)
    || (a.text < b.text ? -1 : a.text > b.text ? 1 : 0));
  const h = CLN_BOX_H, g = half + CLN_GAP;
  const nudges = [0];
  for(let s = CLN_NUDGE_STEP; s <= h; s += CLN_NUDGE_STEP) nudges.push(s, -s);

  const boxes = [], hidden = [];
  for(const it of order){
    if(!it.text) continue;
    const w = Math.ceil(measure(it.text)) + CLN_HALO * 2;
    const ax = (it.tx + 0.5) * zoom, ay = (it.ty + 0.5) * zoom;
    const tries = [];
    for(const s of nudges) tries.push([g, -h / 2 + s]);            // right
    for(const s of nudges) tries.push([-g - w, -h / 2 + s]);       // left
    tries.push([-w / 2, -g - h], [-w / 2, g]);                     // above, below
    let got = null;
    for(const [dx, dy] of tries){
      const b = {x: ax + dx, y: ay + dy, w, h};
      if(!hits(b)){ got = b; break; }
    }
    if(!got){ hidden.push(it.key); continue; }
    put(got);
    boxes.push({key: it.key, text: it.text, ax, ay,
                x: got.x, y: got.y, w: got.w, h: got.h});
  }
  return {boxes, hidden, total: order.filter(it => it.text).length};
}

/* The names to place, out of the manifest.

   One per province with a settlement pixel, in the words the player reads
   (20b put them in the manifest) and the code name when the mod has none for
   it - the rule the whole toolkit follows, and the one the game follows too. A
   bigger province is placed first. */
function clnItems(regions){
  const out = [];
  for(const r of regions || []){
    if(!r.settlement || !r.name) continue;
    out.push({key: r.name, tx: r.settlement[0], ty: r.settlement[1],
              text: r.shown_settlement || r.settlement_name || r.name,
              prio: r.pixels || 0});
  }
  return out;
}

/* ---------- the browser half ---------- */

let clnMeasureCtx = null;
const clnWidths = new Map();
//: A name's width in the font it is drawn in, measured once.
function clnMeasure(text){
  if(clnWidths.has(text)) return clnWidths.get(text);
  if(!clnMeasureCtx){
    clnMeasureCtx = document.createElement('canvas').getContext('2d');
  }
  let w = text.length * CLN_FONT_PX * 0.56;         // a context that cannot measure
  if(clnMeasureCtx && clnMeasureCtx.measureText){
    clnMeasureCtx.font = CLN_FONT;
    const m = clnMeasureCtx.measureText(text);
    if(m && m.width) w = m.width;
  }
  clnWidths.set(text, w);
  return w;
}

/* What a settlement is marked with on screen right now, and so how much room a
   name has to leave it. Whichever of the three is drawing it: 17d's icon, 16c's
   diamond, or the constant dot this file draws when neither is. */
function clnObstacle(z){
  const k = state.cmk;
  if(k && k.on && k.cats.settlement && k.groups.length) return cmkIconSize(z);
  if(z >= CMAP_GLYPH_ZOOM) return z * 1.7;
  return CLN_DOT;
}

//: True when 16c's diamond and 17d's icon are both absent, so the dot is ours.
function clnDotted(z){
  const k = state.cmk;
  return z < CMAP_GLYPH_ZOOM && !(k && k.on && k.cats.settlement && k.groups.length);
}

//: The layout for the zoom on screen, worked out when the zoom changes.
function clnCurrent(){
  const c = state.cmap;
  if(!c || !c.labels) return null;
  const z = c.view.zoom, ob = clnObstacle(z);
  const key = `${z}|${ob}|${c.man.regions.length}`;
  if(!c.lab || c.lab.key !== key){
    const t0 = performance.now();
    const lay = clnLayout(clnItems(c.man.regions), z, clnMeasure, ob);
    lay.key = key;
    lay.ms = performance.now() - t0;
    c.lab = lay;
  }
  return c.lab;
}

/* Every name inside the rectangle this frame repaints.

   Called from `cmapOverlay`, which is clipped to that rectangle. A name's box
   can reach past the tiles the frame covers, so the test is the box against the
   rectangle in screen pixels, not the anchor against the tile range: a hover
   frame that clips half a name repaints that half and no more. */
function clnDraw(x, s0, t0, s1, t1){
  const c = state.cmap;
  const lay = clnCurrent();
  if(!lay) return;
  const v = c.view, z = v.zoom;
  const R = [cmapX(s0) - 1, cmapY(t0) - 1, cmapX(s1) + 1, cmapY(t1) + 1];
  x.save();
  if(clnDotted(z)){
    x.fillStyle = 'rgba(245,240,228,.95)';
    x.strokeStyle = 'rgba(8,10,14,.9)';
    x.lineWidth = 1.5;
    for(const r of c.man.regions){
      const p = r.settlement;
      if(!p || p[0] < s0 - 1 || p[0] > s1 || p[1] < t0 - 1 || p[1] > t1) continue;
      x.beginPath();
      x.arc(cmapX(p[0]) + z / 2, cmapY(p[1]) + z / 2, CLN_DOT / 2, 0, Math.PI * 2);
      x.fill(); x.stroke();
    }
  }
  x.font = CLN_FONT;
  x.textBaseline = 'middle';
  x.textAlign = 'left';
  x.lineJoin = 'round';
  x.lineWidth = 3;
  x.strokeStyle = 'rgba(8,10,14,.88)';
  const sel = c.sel && c.sel.name;
  for(const b of lay.boxes){
    const sx = v.ox + b.x, sy = v.oy + b.y;
    if(sx > R[2] || sy > R[3] || sx + b.w < R[0] || sy + b.h < R[1]) continue;
    const tx = sx + CLN_HALO, ty = sy + b.h / 2 + 0.5;
    x.strokeText(b.text, tx, ty);
    x.fillStyle = b.key === sel ? 'rgba(236,200,120,1)' : 'rgba(245,240,228,.97)';
    x.fillText(b.text, tx, ty);
  }
  x.restore();
}

/* The switch. Remembered with the layer stack, and carried by a saved view. */
function clnToggle(){
  const c = state.cmap;
  if(!c) return;
  c.labels = !c.labels;
  c.lab = null;
  const b = document.getElementById('cmLabBtn');
  if(b) b.classList.toggle('on', !!c.labels);
  activity('map labels', c.labels ? 'showed settlement names' : 'hid settlement names');
  c.saidZoom = null;
  cmapPaint();
  cmapSaveLayers();
}

//: "84 of 199 named", for the toolbar's count, or nothing when the switch is off.
function clnCount(){
  const c = state.cmap;
  if(!c || !c.labels || !c.lab) return '';
  const n = c.lab.boxes.length, t = c.lab.total;
  return n === t ? `${t} named` : `${n} of ${t} named`;
}
