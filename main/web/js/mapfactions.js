/* mapfactions.js - Campaign Map: each faction's name lettered over its land

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   FLOATING FACTION NAMES - Phase 97b.

   Every name here starts `cfn`, and there was no `cfn` name anywhere in the
   tree before this phase.

   What the user asked for, from a picture of a Middle-earth campaign map:
   each faction's name lettered large over its territory, curved along it,
   standing off the land with a shadow, as the default look of both the flat
   map and the 3D one.

   WHERE THE WORDS COME FROM. Nothing here reads a file. The "Factions"
   colouring (`mapquery.theme_faction`) already answers all three questions:
   which faction holds each province at the start (`bands`), the faction's
   name in the mod's own text (a group's `label`) and its colour from
   descr_sm_factions.txt (a group's `rgb`). One request, the one the Colour by
   panel makes, and so the names cannot disagree with that panel.

   WHERE A NAME GOES. On the faction's LARGEST CONNECTED BLOCK of land, not on
   all of it: a faction with an island and a mainland is lettered over the
   mainland, which is where a reader looks for it. Over that block:

     * the main axis is the block's own (the larger eigenvector of its
       tiles' spread), turned so the word never reads upside down and kept
       within 55 degrees of level;
     * the curve is a parabola fitted to the block's tiles across that axis,
       by least squares, so a crescent of provinces gets an arched name;
     * the size is the smaller of what the block's length allows (the word
       across 80% of it) and what its thickness does, with a little overhang
       allowed, as a printed map lets a name run past a narrow land.

   A block too small or too scattered for a fit (under CFN_CURVE_MIN tiles, or
   under a third of the faction's land) gets a straight, level name over the
   block's centre instead. Overlapping names give way by size: the biggest
   territory is placed first and a later name that would cross it is shrunk
   twice and then left off.

   IN TILES, NOT PIXELS. Unlike 20c's settlement names, which stay one size
   whatever the zoom, these are part of the map: they are laid out once in
   tile units and grow with it. That is what makes them read as lettering on
   the land rather than as labels on the screen. A name smaller than
   CFN_MIN_PX on screen is not drawn at all.
   ===================================================================== */

//: The lettering. A serif in capitals, spaced out, which is what a map does.
const CFN_FONT_FAMILY = 'Georgia,"Times New Roman",serif';
//: Extra space between letters, as a share of the letter height.
const CFN_TRACK = 0.18;
//: The largest and smallest a name may be, in tiles of letter height.
const CFN_MAX_H = 26, CFN_MIN_H = 1.2;
//: Below this many tiles, a block is lettered straight and level.
const CFN_CURVE_MIN = 60;
//: A name smaller than this on screen is not drawn.
const CFN_MIN_PX = 7;

/* ---------- the layout, which is pure ---------- */

/* Where every faction's name goes. No state, no DOM - node runs this.

   `keys`     Int32Array, one packed region colour per tile (0xRRGGBB).
   `W`, `H`   the map in tiles.
   `bandOf`   Map from a packed region colour to a faction index, for every
              province some faction holds.
   `groups`   [{key, label, rgb}] by that index.
   `measure`  text -> its advance at a letter height of 1, per character, as
              an array. The browser measures the canvas font; a test passes
              something it can predict.

   Returns [{key, text, rgb, mx, my, ux, uy, c0, c1, c2, h, chars, tiles,
   straight}]: the word lies along `a` from -width/2 to +width/2, at the
   point (mx, my) + u * a + n * (c0 + c1 a + c2 a^2) with n = (-uy, ux), and
   `chars` is each letter's centre `a` and advance. */
function cfnLayout(keys, W, H, bandOf, groups, measure){
  const N = W * H;
  const g = new Int16Array(N).fill(-1);
  for(let i = 0; i < N; i++){
    const b = bandOf.get(keys[i]);
    if(b !== undefined) g[i] = b;
  }
  // connected blocks, four-way, with the sums a fit needs gathered on the way
  const comp = new Int32Array(N).fill(-1);
  const blocks = [];
  const stack = new Int32Array(N);
  for(let s = 0; s < N; s++){
    if(g[s] < 0 || comp[s] >= 0) continue;
    const id = blocks.length, f = g[s];
    const B = {id, f, n: 0, sx: 0, sy: 0};
    blocks.push(B);
    let top = 0;
    stack[top++] = s; comp[s] = id;
    while(top){
      const i = stack[--top], x = i % W, y = (i - x) / W;
      B.n++; B.sx += x; B.sy += y;
      if(x > 0 && comp[i - 1] < 0 && g[i - 1] === f){ comp[i - 1] = id; stack[top++] = i - 1; }
      if(x < W - 1 && comp[i + 1] < 0 && g[i + 1] === f){ comp[i + 1] = id; stack[top++] = i + 1; }
      if(y > 0 && comp[i - W] < 0 && g[i - W] === f){ comp[i - W] = id; stack[top++] = i - W; }
      if(y < H - 1 && comp[i + W] < 0 && g[i + W] === f){ comp[i + W] = id; stack[top++] = i + W; }
    }
  }
  // each faction's biggest block, and how much land it has in all
  const best = new Map(), total = new Map();
  for(const B of blocks){
    total.set(B.f, (total.get(B.f) || 0) + B.n);
    const was = best.get(B.f);
    if(!was || B.n > was.n) best.set(B.f, B);
  }
  // the tiles of each chosen block, in one pass
  const want = new Map();
  for(const B of best.values()) want.set(B.id, {B, xs: [], ys: []});
  for(let i = 0; i < N; i++){
    const w = comp[i] >= 0 ? want.get(comp[i]) : null;
    if(!w) continue;
    const x = i % W;
    w.xs.push(x + 0.5); w.ys.push((i - x) / W + 0.5);
  }

  const out = [];
  for(const {B, xs, ys} of want.values()){
    const grp = groups[B.f];
    if(!grp || !grp.label) continue;
    const text = String(grp.label).toLocaleUpperCase();
    const adv = measure(text);
    const unitW = adv.reduce((a, b) => a + b, 0) + CFN_TRACK * Math.max(0, adv.length - 1);
    if(!(unitW > 0)) continue;
    const n = xs.length;
    let mx = 0, my = 0;
    for(let i = 0; i < n; i++){ mx += xs[i]; my += ys[i]; }
    mx /= n; my /= n;
    const straight = n < CFN_CURVE_MIN || n * 3 < (total.get(B.f) || n);
    let ux = 1, uy = 0;
    if(!straight){
      let sxx = 0, syy = 0, sxy = 0;
      for(let i = 0; i < n; i++){
        const dx = xs[i] - mx, dy = ys[i] - my;
        sxx += dx * dx; syy += dy * dy; sxy += dx * dy;
      }
      let th = 0.5 * Math.atan2(2 * sxy, sxx - syy);
      // never upside down, and never steeper than a reader will tilt a head
      if(th > Math.PI / 2) th -= Math.PI;
      if(th < -Math.PI / 2) th += Math.PI;
      const lim = 55 * Math.PI / 180;
      th = Math.max(-lim, Math.min(lim, th));
      ux = Math.cos(th); uy = Math.sin(th);
    }
    const nx = -uy, ny = ux;
    // the block in its own frame: a along the axis, b across it
    const as = new Float64Array(n), bs = new Float64Array(n);
    for(let i = 0; i < n; i++){
      const dx = xs[i] - mx, dy = ys[i] - my;
      as[i] = dx * ux + dy * uy; bs[i] = dx * nx + dy * ny;
    }
    const sorted = Float64Array.from(as).sort();
    const a0 = sorted[Math.floor(n * 0.03)], a1 = sorted[Math.min(n - 1, Math.floor(n * 0.97))];
    const len = Math.max(1, a1 - a0);
    let c0 = 0, c1 = 0, c2 = 0;
    if(!straight){
      // b = c0 + c1 a + c2 a^2, least squares, solved by Cramer's rule
      let s0 = n, s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0;
      for(let i = 0; i < n; i++){
        const a = as[i], a2 = a * a, b = bs[i];
        s1 += a; s2 += a2; s3 += a2 * a; s4 += a2 * a2;
        t0 += b; t1 += a * b; t2 += a2 * b;
      }
      const det = (m) => m[0] * (m[4] * m[8] - m[5] * m[7])
                       - m[1] * (m[3] * m[8] - m[5] * m[6])
                       + m[2] * (m[3] * m[7] - m[4] * m[6]);
      const M = [s0, s1, s2, s1, s2, s3, s2, s3, s4];
      const D = det(M);
      if(Math.abs(D) > 1e-9){
        c0 = det([t0, s1, s2, t1, s2, s3, t2, s3, s4]) / D;
        c1 = det([s0, t0, s2, s1, t1, s3, s2, t2, s4]) / D;
        c2 = det([s0, s1, t0, s1, s2, t1, s2, s3, t2]) / D;
      }
      // a gentle arc: the sag across the name no more than a fifth of its length
      const half = len / 2, sag = Math.abs(c2) * half * half;
      if(sag > len * 0.2) c2 *= len * 0.2 / sag;
    }
    // how thick the block is about the curve
    let v = 0;
    for(let i = 0; i < n; i++){
      const r = bs[i] - (c0 + c1 * as[i] + c2 * as[i] * as[i]);
      v += r * r;
    }
    const thick = 2 * Math.sqrt(v / n) + 1;
    const h = Math.max(CFN_MIN_H, Math.min(len * 0.8 / unitW, thick * 1.3, CFN_MAX_H));
    // centred on the middle of the block along the axis, not on its mean
    const ac = (a0 + a1) / 2;
    const cx = mx + ux * ac, cy = my + uy * ac;
    // re-centre the curve on that middle, so the word's own a runs about 0
    const k0 = c0 + c1 * ac + c2 * ac * ac, k1 = c1 + 2 * c2 * ac;
    out.push({key: grp.key, text, rgb: grp.rgb, mx: cx, my: cy, ux, uy,
              c0: k0, c1: k1, c2, h, adv, unitW, tiles: total.get(B.f) || n,
              straight});
  }
  cfnPlace(out);
  return out.filter(L => !L.hidden);
}

//: Each letter's centre along the word and its advance, at the label's size.
function cfnChars(L){
  const out = [];
  const w = L.unitW * L.h;
  let a = -w / 2;
  for(let i = 0; i < L.adv.length; i++){
    const adv = L.adv[i] * L.h;
    out.push({ch: L.text[i], a: a + adv / 2, adv});
    a += adv + CFN_TRACK * L.h;
  }
  return out;
}

//: A point on the word's line, and the line's direction there.
function cfnAt(L, a){
  const b = L.c0 + L.c1 * a + L.c2 * a * a, db = L.c1 + 2 * L.c2 * a;
  const nx = -L.uy, ny = L.ux;
  return {x: L.mx + L.ux * a + nx * b, y: L.my + L.uy * a + ny * b,
          ang: Math.atan2(L.uy + ny * db, L.ux + nx * db)};
}

/* Biggest territory first; a name that would cross one already placed is
   shrunk to 80% twice and then left off. Collisions are tested letter by
   letter, each letter a square of its own height, so an arched name can sit
   in the hollow of another's arch. */
function cfnPlace(labels){
  const placed = [];
  const hit = (sq) => placed.some(o => Math.abs(o.x - sq.x) < (o.r + sq.r)
                                    && Math.abs(o.y - sq.y) < (o.r + sq.r));
  labels.sort((p, q) => q.tiles - p.tiles || (p.text < q.text ? -1 : 1));
  for(const L of labels){
    let ok = false;
    for(let t = 0; t < 3 && !ok; t++){
      if(t) L.h *= 0.8;
      if(L.h < CFN_MIN_H) break;
      const sqs = cfnChars(L).map(c => {
        const p = cfnAt(L, c.a);
        return {x: p.x, y: p.y, r: L.h * 0.55};
      });
      if(!sqs.some(hit)){ placed.push(...sqs); ok = true; }
    }
    L.hidden = !ok;
  }
}

//: The face colour, its depth and the outline that keeps it readable.
function cfnInks(rgb){
  const [r, g, b] = rgb || [200, 190, 170];
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return {
    face: `rgb(${r},${g},${b})`,
    depth: `rgb(${Math.round(r * 0.42)},${Math.round(g * 0.42)},${Math.round(b * 0.42)})`,
    // a dark faction (Mordor in black) is outlined in pale stone, a pale
    // one in near-black, so both read against any ground
    edge: lum < 0.3 ? 'rgba(226,214,190,.85)' : 'rgba(12,10,8,.85)',
  };
}

/* One name, drawn with the canvas already moved into the frame it is drawn
   in: `px(x, y)` turns a tile position into the canvas's own pixels and `s`
   is pixels per tile. The 2D map and the 3D view's sprites both draw through
   this, so the lettering is one piece of code. */
function cfnDrawName(x, L, px, s){
  const fs = L.h * s;
  const ink = cfnInks(L.rgb);
  const depth = Math.max(1, Math.round(fs * 0.06));
  x.font = `700 ${fs}px ${CFN_FONT_FAMILY}`;
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  x.lineJoin = 'round';
  const chars = cfnChars(L).map(c => {
    const p = cfnAt(L, c.a), q = px(p.x, p.y);
    return {ch: c.ch, x: q[0], y: q[1], ang: p.ang};
  });
  const each = (fn) => {
    for(const c of chars){
      x.save();
      x.translate(c.x, c.y);
      x.rotate(c.ang);
      fn(c.ch);
      x.restore();
    }
  };
  // the shadow it casts, down and to the right, soft by being drawn twice
  x.fillStyle = 'rgba(0,0,0,.28)';
  each(ch => { x.fillText(ch, fs * 0.09, fs * 0.13); x.fillText(ch, fs * 0.06, fs * 0.09); });
  // the depth: the same letter stepped down a pixel at a time, darker
  x.fillStyle = ink.depth;
  each(ch => { for(let d = depth; d > 0; d--) x.fillText(ch, 0, d); });
  // the face
  x.lineWidth = Math.max(1, fs * 0.05);
  x.strokeStyle = ink.edge;
  x.fillStyle = ink.face;
  each(ch => { x.strokeText(ch, 0, 0); x.fillText(ch, 0, 0); });
}

/* ---------- the browser half ---------- */

let cfnMeasureCtx = null;
const cfnWidths = new Map();
//: Each letter's advance at a letter height of 1, in the face it is drawn in.
function cfnMeasure(text){
  if(cfnWidths.has(text)) return cfnWidths.get(text);
  if(!cfnMeasureCtx) cfnMeasureCtx = document.createElement('canvas').getContext('2d');
  const out = [];
  for(const ch of text){
    let w = 0.72;                                  // a context that cannot measure
    if(cfnMeasureCtx && cfnMeasureCtx.measureText){
      cfnMeasureCtx.font = `700 100px ${CFN_FONT_FAMILY}`;
      const m = cfnMeasureCtx.measureText(ch);
      if(m && m.width) w = m.width / 100;
    }
    out.push(w);
  }
  cfnWidths.set(text, out);
  return out;
}

//: The state, on the map it belongs to. `on` is remembered with the view.
function cfnState(){
  const c = state.cmap;
  if(!c) return null;
  if(!c.fn) c.fn = {d: null, lay: null, layKey: '', loading: false, err: '', rev: 0};
  return c.fn;
}

/* The faction table, fetched once a map and again whenever something may have
   moved a settlement to another owner (`cfnStale`). */
async function cfnLoad(){
  const c = state.cmap, f = cfnState();
  if(!c || !f || f.loading || !c.fnOn) return;
  f.loading = true; f.err = '';
  let d;
  try{
    d = await api.get(`/api/map/colouring?mod=${enc(c.mod)}&code=faction${cmapCampQ()}`);
  }catch(e){ d = {error: errText(e)}; }
  if(state.cmap !== c) return;
  if(!cmapRawOf(c.layers.regions)) await cmapFetchLayer(c, 'regions');
  if(state.cmap !== c) return;
  f.loading = false;
  if(d.error){ f.err = d.error; return; }
  f.d = d; f.lay = null;
  cfnRepaint();
}

//: Ownership or the regions themselves may have changed: ask again.
function cfnStale(){
  const c = state.cmap, f = cfnState();
  if(!c || !f) return;
  f.d = null; f.lay = null; f.rev++;
  if(c.fnOn) cfnLoad();
}

//: The pixels moved but the owners did not: lay out again from what is here.
function cfnRelayout(){
  const f = cfnState();
  if(f){ f.lay = null; f.rev++; }
}

//: The layout for the data on hand, worked out when that changes.
function cfnCurrent(){
  const c = state.cmap, f = cfnState();
  if(!c || !f || !c.fnOn) return null;
  if(!f.d){ if(!f.loading && !f.err) cfnLoad(); return null; }
  if(f.lay) return f.lay;
  const R = cmapRawOf(c.layers.regions);
  if(!R) return null;
  const W = c.man.width, H = c.man.height;
  const keys = new Int32Array(W * H);
  for(let i = 0, n = W * H; i < n; i++)
    keys[i] = (R.data[i * 4] << 16) | (R.data[i * 4 + 1] << 8) | R.data[i * 4 + 2];
  const bandOf = new Map();
  // The rebels hold what nobody else does, and the game letters nothing for
  // them either: they are left off.
  // A label is `Mod.faction_label`'s "Kingdom of Gondor (sicily)"; the map
  // letters only the name the player reads, and the code name when the mod
  // gives none.
  const groups = (f.d.groups || []).map(g => g.key === 'slave' ? null
    : Object.assign({}, g, {label: cfnShown(g)}));
  for(const [k, b] of Object.entries(f.d.bands || {}))
    if(b >= 0 && groups[b]) bandOf.set(+k, b);
  const t0 = performance.now();
  f.lay = {labels: cfnLayout(keys, W, H, bandOf, groups, cfnMeasure), rev: f.rev};
  f.lay.ms = performance.now() - t0;
  return f.lay;
}

//: "Kingdom of Gondor (sicily)" -> "Kingdom of Gondor".
function cfnShown(g){
  const t = String(g.label || g.key || ''), tail = ` (${g.key})`;
  return g.key && t.endsWith(tail) ? t.slice(0, -tail.length) : t;
}

/* Every name that crosses the tiles this frame repaints, on the flat map.
   Called from `cmapOverlay`, under the markers and 20c's names. */
function cfnDraw(x, s0, t0, s1, t1){
  const c = state.cmap;
  const lay = cfnCurrent();
  if(!lay) return;
  const z = c.view.zoom;
  const px = (tx, ty) => [cmapX(0) + tx * z, cmapY(0) + ty * z];
  x.save();
  for(const L of lay.labels){
    if(L.h * z < CFN_MIN_PX) continue;
    const half = L.unitW * L.h / 2 + L.h;
    if(L.mx + half < s0 || L.mx - half > s1 || L.my + half < t0 || L.my - half > t1) continue;
    cfnDrawName(x, L, px, z);
  }
  x.restore();
}

function cfnRepaint(){
  if(typeof cm3Names === 'function') cm3Names();
  cmapPaint();
}

/* The switch. Remembered with the layer stack, and carried by a saved view. */
function cfnToggle(){
  const c = state.cmap;
  if(!c) return;
  c.fnOn = !c.fnOn;
  const b = document.getElementById('cmFacBtn');
  if(b) b.classList.toggle('on', !!c.fnOn);
  activity(tt('maplabels.map_labels'), c.fnOn ? tt('mapfactions.showed_faction_names') : tt('mapfactions.hid_faction_names'));
  cfnRepaint();
  cmapSaveLayers();
}
