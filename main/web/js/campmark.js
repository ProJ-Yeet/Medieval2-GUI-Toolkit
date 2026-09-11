/* campmark.js - Campaign Map: everything descr_strat.txt stands on a tile

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE MARKERS LAYER - Phase 17d.

   Every name here starts `cmk`, and there was no `cmk` name anywhere in the
   tree before this phase - checked, the way 16e checked `cp`, 16f `cchk`, 16g
   `cq`, 16h `cs` and 16i `cx`.

   WHAT IS TAKEN FROM MYLAE'S `StratOverlay.jsx`, AND WHAT IS CHANGED. It is the
   thing that map reads best: everything in descr_strat.txt with a coordinate
   gets an icon at that tile.

     * TAKEN - the pixel-grouping rule. Items on the same tile become one marker
       with a count badge and fan out sideways once the zoom is high enough. A
       general standing on his own city is the normal case, not the exception:
       246 of Third Age Reforged's characters stand on 196 settlements, and
       Denethor is on Minas Tirith's own settlement pixel. Two icons on one tile
       is unreadable.
     * TAKEN - the mod's own resource art. `data/ui/resources/resource_<name>.tga`
       when the mod ships one, a drawn glyph when it does not. Third Age
       Reforged ships six of about forty and lets the game fall back to its own
       for the rest, so the fallback is the ordinary case rather than a fault -
       and the stock art is inside a .pack archive nothing here reads, so the
       glyph is what honesty looks like.
     * CHANGED - the projection. Theirs converts M2TW tiles to Leaflet lat/lng
       through an OSM bounding box; there is no Leaflet here and no bounding
       box, and 16c's canvas already maps a tile to a pixel exactly. `cmapX`
       and `cmapY` are that map, and they are what every glyph is drawn from.
     * CHANGED - the drag. Theirs moves a character by dragging its icon and
       writes on pointer-up. A drop here PLANS: the same `/api/map/character_plan` the
       form beside it uses, with the same confirmation and the same undo. 22a
       added forts and watchtowers, whose drop plans through 22a's panel. What
       the drag itself previews is only what the browser can answer exactly -
       whether the tile is on the map, and whether it is sea by the measured
       rule (map_heights, river crossings excluded), which is the same test
       `stratchar.check_character` applies on the server.
     * The layer is OFF by default and its categories are separate, because a
       map carrying 1,131 resources (DaC) or 413 (Reforged) drawn over the
       provinces is not a map any more.
   ===================================================================== */

//: Tile size in CSS pixels at which a group of markers stops being one badge
//: and fans out into its own icons. Below it there is no room to fan into.
const CMK_FAN_ZOOM = 14;

//: Icon size in CSS pixels, and the zoom band it grows through. Constant on
//: screen rather than in tiles: a marker is a label, and a label that shrinks
//: with the map cannot be read at the zoom somebody is looking for it at.
const CMK_ICON_MIN = 9, CMK_ICON_MAX = 22;

//: The categories, in the order the panel lists them, with the toggle default.
//: Resources are off for the reason at the top of this file; the two 18b ones
//: are on, because the largest set of them anywhere is the game's own 106 and
//: because a coordinate being edited on the panel below has to be visible.
const CMK_CATS = [
  {id: 'settlement', label: 'Settlements', on: true},
  {id: 'character', label: 'Characters', on: true},
  {id: 'fort', label: 'Forts', on: true},
  {id: 'watchtower', label: 'Watchtowers', on: true},
  {id: 'resource', label: 'Trade resources', on: false},
  {id: 'event', label: 'Event positions', on: true},
  {id: 'disaster', label: 'Disaster positions', on: true},
];

/* One letter per character type, because eleven kinds of person will not fit
   as eleven drawn shapes at nine pixels. The words are descr_strat.txt's own
   (`campstrat.CHARACTER_TYPES`); anything else is a defect in the file, not a
   kind, and gets the question mark rather than a guess. */
const CMK_CHAR = {
  'named character': 'N', general: 'G', admiral: 'A', spy: 'S', merchant: 'M',
  diplomat: 'D', priest: 'P', assassin: 'X', princess: 'R', heretic: 'H',
  witch: 'W', inquisitor: 'I',
};

//: Settlement levels, smallest to largest, so a village is a smaller mark than
//: a huge city. Both ladders are the same six words - see stratedit.py.
const CMK_LEVELS = ['village', 'town', 'large_town', 'city', 'large_city', 'huge_city'];

/* ---------- state ----------

   Beside `state.cmap` like every other campaign-map panel. The markers belong
   to a campaign file, not to the map, so they are fetched once per mod and
   thrown away with the screen. */
function cmkNew(mod){
  const cats = {};
  for(const c of CMK_CATS) cats[c.id] = c.on;
  return {mod, on: false, cats, loading: false, err: '', d: null,
          groups: [], byTile: new Map(), art: {}, drag: null, open: true};
}

function cmkOpen(){
  const c = state.cmap;
  if(!c) return;
  const k = state.cmk;
  if(!k || k.mod !== c.mod) state.cmk = cmkNew(c.mod);
  else { state.cmk.groups = []; state.cmk.byTile = new Map(); cmkIndex(); }
  cmkPaint();
  if(state.cmk.on && !state.cmk.d) cmkLoad();
}

/* The whole layer in one request, when it is first asked for.

   855 markers on Third Age Reforged, about 110 KB of JSON, and it is fetched
   when somebody ticks the layer rather than with the map: most visits to this
   screen are about the pixels, and a screen that opens slower for everybody so
   that one panel can open faster is the trade this phase exists to refuse. */
async function cmkLoad(){
  const c = state.cmap, k = state.cmk;
  if(!c || !k || k.loading) return;
  k.loading = true; k.err = '';
  cmkPaint();
  let d;
  try{ d = await api.get(`/api/map/markers?mod=${enc(k.mod)}${cmapCampQ()}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cmk !== k || !state.cmap || state.cmap.mod !== k.mod) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cmkPaint(); return; }
  k.d = d;
  cmkIndex();
  cmkArt();
  cmkPaint();
  cmkStale();
  cmapPaint();
}

/* Tile to the things standing on it.

   A settlement carries no coordinate of its own - it stands where its
   province's black marker pixel is on map_regions.tga - so this is where the
   campaign file's word about a settlement is joined to the map's pixel for it,
   by region name. Everything else is in the file's own coordinates and is
   flipped here, once, which is the only place in the browser that flip is
   made. */
function cmkIndex(){
  const c = state.cmap, k = state.cmk;
  if(!c || !k || !k.d) return;
  const H = c.man.height;
  const byRegion = new Map();
  for(const r of c.man.regions) if(r.name) byRegion.set(r.name, r);
  const tiles = new Map();
  for(const it of k.d.items){
    let tx, ty;
    if(it.kind === 'settlement'){
      const r = byRegion.get(it.region);
      if(!r || !r.settlement) continue;   // the read already reports an orphan
      [tx, ty] = r.settlement;
    }else{
      tx = it.x; ty = H - 1 - it.y;
    }
    if(!(tx >= 0 && ty >= 0 && tx < c.man.width && ty < H)) continue;
    const key = `${tx},${ty}`;
    let g = tiles.get(key);
    if(!g){ g = {tx, ty, items: []}; tiles.set(key, g); }
    g.items.push(it);
  }
  k.byTile = tiles;
  k.groups = [...tiles.values()];
}

/* The mod's own resource pictures, one <img> each, decoded once.

   Through the icon route every other picture in the toolkit goes through, so
   the TGA is decoded to PNG on the server and cached on disk by mtime. A
   resource the mod ships no art for is simply absent from `art` and draws its
   glyph instead - see the note at the top of this file. */
function cmkArt(){
  const k = state.cmk;
  if(!k || !k.d) return;
  for(const [name, rel] of Object.entries(k.d.art || {})){
    if(k.art[name]) continue;
    const img = new Image();
    img.onload = () => { if(state.cmk === k){ k.art[name] = img; cmapPaint(); } };
    img.onerror = () => {};
    // `/icon`, not `/api/icon`: the picture routes are the one family that
    // predates the /api prefix, and the wrong one 404s rather than falling back
    // to a blank PNG, because it never reaches the handler that promises that.
    img.src = `/icon?mod=${enc(k.mod)}&kind=modfile&rel=${enc(rel)}`;
    k.art[name] = img;                 // held while it loads; `complete` gates use
  }
}

/* ---------- drawing ---------- */

//: Which of a group's items are drawn at all, in the order they stack.
function cmkShown(g){
  const k = state.cmk;
  return g.items.filter(it => k.cats[it.kind]);
}

function cmkIconSize(z){
  return Math.max(CMK_ICON_MIN, Math.min(CMK_ICON_MAX, z * 0.9));
}

/* Every marker inside the tile range this frame is repainting.

   Called from `cmapOverlay`, which is already clipped to that range, so a
   dirty-rect frame walks the group list once and draws almost nothing - the
   list is 800 entries and the test is two comparisons, which is what keeps
   rule 4 (nothing O(pixels) on the interaction path) true of this layer too. */
function cmkDraw(x, s0, t0, s1, t1){
  const c = state.cmap, k = state.cmk;
  if(!c || !k || !k.on || !k.groups.length) return;
  const z = c.view.zoom, size = cmkIconSize(z);
  const fan = z >= CMK_FAN_ZOOM;
  x.save();
  x.lineWidth = 1;
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  for(const g of k.groups){
    if(g.tx < s0 - 1 || g.tx > s1 || g.ty < t0 - 1 || g.ty > t1) continue;
    const shown = cmkShown(g);
    if(!shown.length) continue;
    const cx = cmapX(g.tx) + z / 2, cy = cmapY(g.ty) + z / 2;
    if(fan && shown.length > 1){
      // fanned sideways, centred on the tile, so the tile they are all on is
      // still the middle of the row
      const step = size * 0.9;
      const x0 = cx - step * (shown.length - 1) / 2;
      shown.forEach((it, i) => cmkGlyph(x, it, x0 + i * step, cy, size));
    }else{
      cmkGlyph(x, shown[0], cx, cy, size);
      if(shown.length > 1) cmkBadge(x, shown.length, cx + size * 0.5, cy - size * 0.5, size);
    }
  }
  cmkDragGhost(x, size);
  x.restore();
}

//: A faction's own colour, or the neutral one. `descr_sm_factions.txt` is where
//: it comes from and the fact table already read it; a marker nobody owns (a
//: trade resource) is drawn in the toolkit's accent instead of black, which on
//: a dark map is invisible.
function cmkColour(it){
  const k = state.cmk;
  const f = it.faction && k.d && k.d.factions[it.faction];
  const c = f && f.colour;
  return c ? `rgb(${c[0]},${c[1]},${c[2]})` : 'rgba(200,164,92,.95)';
}

/* Ink that can be read on a given faction colour.

   Third Age Reforged flies white, near-white and near-black, and a white letter
   on a white circle is a white circle. Rec. 709 luminance, the same line every
   other contrast test uses. */
function cmkInk(fill){
  const m = /rgb\((\d+),\s*(\d+),\s*(\d+)\)/.exec(fill);
  if(!m) return 'rgba(255,255,255,.95)';
  const lum = (0.2126 * +m[1] + 0.7152 * +m[2] + 0.0722 * +m[3]) / 255;
  return lum > 0.55 ? 'rgba(12,14,18,.95)' : 'rgba(255,255,255,.95)';
}

/* One marker, drawn at a screen point. Every shape is stroked in white first
   and filled in the faction's colour, because a faction colour on a province
   painted that same colour is otherwise invisible - which is exactly where a
   faction's own markers are. */
function cmkGlyph(x, it, px, py, size){
  const r = size / 2;
  const fill = cmkColour(it);
  x.strokeStyle = 'rgba(255,255,255,.92)';
  x.fillStyle = fill;
  if(it.kind === 'settlement'){
    // a square that grows with the settlement's level, castles turned 45°
    const lv = Math.max(0, CMK_LEVELS.indexOf(it.level || 'village'));
    const s = r * (0.62 + 0.09 * lv);
    x.beginPath();
    if((it.settlement_type || '') === 'castle'){
      x.moveTo(px, py - s); x.lineTo(px + s, py);
      x.lineTo(px, py + s); x.lineTo(px - s, py); x.closePath();
    }else{
      x.rect(px - s, py - s, s * 2, s * 2);
    }
    x.fill(); x.stroke();
    return;
  }
  if(it.kind === 'character'){
    x.beginPath();
    x.arc(px, py, r * 0.72, 0, Math.PI * 2);
    x.fill(); x.stroke();
    if(size >= 12){
      x.fillStyle = cmkInk(fill);
      x.font = `${Math.round(size * 0.55)}px ui-monospace,Consolas,monospace`;
      x.fillText(CMK_CHAR[it.type] || '?', px, py + 0.5);
    }
    return;
  }
  /* 18b - an event or a disaster position. Both are drawn as a burst rather
     than a solid shape, so that a coordinate nothing owns is not mistaken for
     one of the four things above that a faction does: these are places where
     something happens TO the map, and the shape says so. A disaster is the
     bigger burst of the two because it is the one that recurs. */
  if(it.kind === 'event' || it.kind === 'disaster'){
    const arms = it.kind === 'disaster' ? 8 : 6;
    const outer = r * (it.kind === 'disaster' ? 0.95 : 0.8);
    x.beginPath();
    for(let i = 0; i < arms * 2; i++){
      const a = Math.PI * i / arms - Math.PI / 2;
      const rr = i % 2 ? outer * 0.42 : outer;
      const fx = px + Math.cos(a) * rr, fy = py + Math.sin(a) * rr;
      if(i) x.lineTo(fx, fy); else x.moveTo(fx, fy);
    }
    x.closePath();
    x.fillStyle = it.kind === 'disaster' ? 'rgba(233,105,105,.95)'
                                         : 'rgba(200,164,92,.95)';
    x.fill(); x.stroke();
    return;
  }
  if(it.kind === 'fort' || it.kind === 'watchtower'){
    const s = r * 0.7;
    x.beginPath();
    if(it.kind === 'fort') x.rect(px - s, py - s, s * 2, s * 2);
    else { x.moveTo(px, py - s); x.lineTo(px + s, py + s); x.lineTo(px - s, py + s);
           x.closePath(); }
    x.fill(); x.stroke();
    return;
  }
  // a resource: the mod's own picture when it ships one, its initial when not
  const img = state.cmk.art[it.name];
  if(img && img.complete && img.naturalWidth){
    x.drawImage(img, px - r, py - r, size, size);
    return;
  }
  x.beginPath();
  x.arc(px, py, r * 0.6, 0, Math.PI * 2);
  x.fillStyle = 'rgba(18,20,26,.9)';
  x.fill(); x.stroke();
  if(size >= 11){
    x.fillStyle = 'rgba(255,255,255,.9)';
    x.font = `${Math.round(size * 0.5)}px ui-monospace,Consolas,monospace`;
    x.fillText((it.name || '?')[0].toUpperCase(), px, py + 0.5);
  }
}

//: How many things are on this tile, when they are not fanned out.
function cmkBadge(x, n, px, py, size){
  const r = Math.max(5, size * 0.34);
  x.beginPath();
  x.arc(px, py, r, 0, Math.PI * 2);
  x.fillStyle = 'rgba(12,14,18,.92)';
  x.fill();
  x.strokeStyle = 'rgba(255,255,255,.8)';
  x.stroke();
  x.fillStyle = 'rgba(255,255,255,.95)';
  x.font = `${Math.round(r * 1.25)}px ui-monospace,Consolas,monospace`;
  x.fillText(String(n), px, py + 0.5);
}

//: Where a dragged character would land, and whether it may. Drawn every frame
//: the drag repaints, which is a whole frame - a drag is a pan-sized change.
function cmkDragGhost(x, size){
  const k = state.cmk, c = state.cmap;
  if(!k.drag || !k.drag.tile) return;
  const [tx, ty] = k.drag.tile, z = c.view.zoom;
  const px = cmapX(tx) + z / 2, py = cmapY(ty) + z / 2;
  const bad = k.drag.fault;
  x.globalAlpha = 0.85;
  cmkGlyph(x, k.drag.item, px, py, Math.max(size, 12));
  x.globalAlpha = 1;
  x.strokeStyle = bad ? 'rgba(233,105,105,.95)' : 'rgba(120,220,140,.95)';
  x.lineWidth = 2;
  x.strokeRect(cmapX(tx) - 1, cmapY(ty) - 1, z + 2, z + 2);
  x.lineWidth = 1;
}

/* ---------- what is on a tile ---------- */

//: Everything drawn on one tile, for the tooltip and for the pick. Empty when
//: the layer is off, so nothing below has to ask twice.
function cmkAt(tx, ty){
  const k = state.cmk;
  if(!k || !k.on || !k.byTile.size) return [];
  const g = k.byTile.get(`${tx},${ty}`);
  return g ? cmkShown(g) : [];
}

//: One marker said in a line, for 17e's tooltip.
function cmkLabel(it){
  const k = state.cmk;
  const f = it.faction && k.d && k.d.factions[it.faction];
  const who = f ? f.label : it.faction;
  if(it.kind === 'settlement'){
    // the two ladders are one ladder - a castle's `level` is written with the
    // same six city words - so the kind is said and the level is qualified,
    // rather than reading "huge city city"
    const lv = (it.level || '').replace(/_/g, ' ');
    return ((it.settlement_type === 'castle') ? `castle, ${lv} level` : lv)
      + (who ? ` · ${who}` : '');
  }
  if(it.kind === 'character')
    return `${it.name}${it.type ? ` · ${it.type}` : ''}`
      + (it.army ? ` · ${it.army} unit${it.army === 1 ? '' : 's'}` : '')
      + (who ? ` · ${who}` : '');
  if(it.kind === 'resource') return it.name;
  // 18b. A date and a frequency are the whole reason one of these is here, so
  // each says its own: an event happens once, a disaster happens again.
  if(it.kind === 'event')
    return `${it.name}${it.type ? ` · ${it.type}` : ''}`
      + (it.date ? ` · turn ${it.date}` : '');
  if(it.kind === 'disaster')
    return `${it.name}${it.frequency ? ` · every ${it.frequency} years` : ''}`;
  // A fort and a watchtower name a province rather than an owner: DaC writes
  // all 105 and all 295 of them inside the `region` blocks at the end of the
  // file, where nobody owns them, so that is what is worth saying about one.
  return `${it.kind}${it.type ? `, ${it.type}` : ''}`
    + (who ? ` · ${who}` : it.region ? ` · ${it.region}` : '');
}

/* ---------- the drag ----------

   A character, a fort, a watchtower and a trade resource move this way, and
   the reason is worth stating: each one's tile IS two numbers on its own line
   in descr_strat.txt, so moving one is an edit this toolkit already knows how
   to plan - 16i's for a character, 22a's and 22b's for the other three. A
   settlement's tile is a black pixel on map_regions.tga - moving it is
   repainting the map, which is the paint tool's job and not a drag's. */
const CMK_DRAGGABLE = ['character', 'fort', 'watchtower', 'resource'];
function cmkCanDrag(it){ return !!it && CMK_DRAGGABLE.indexOf(it.kind) >= 0; }

//: The character under the pointer, if the drag should start here rather than a
//: pan. Topmost first, which is the order they are drawn in.
function cmkPickAt(tx, ty){
  const on = cmkAt(tx, ty).filter(cmkCanDrag);
  return on.length ? on[on.length - 1] : null;
}

function cmkDragStart(tile){
  const it = cmkPickAt(tile[0], tile[1]);
  if(!it) return false;
  // the preview's sea test reads map_heights and map_features, which 17e's
  // tooltip fetches on first hover and nothing else does. Ask for them here
  // too, so a drag that starts before any hover is not a drag with no opinion.
  if(typeof cmapTipLoad === 'function') cmapTipLoad();
  state.cmk.drag = {item: it, from: tile.slice(), tile: tile.slice(), fault: ''};
  cmkDragCheck();
  cmapPaint();
  return true;
}

function cmkDragMove(tile){
  const k = state.cmk;
  if(!k.drag) return;
  if(k.drag.tile[0] === tile[0] && k.drag.tile[1] === tile[1]) return;
  k.drag.tile = tile.slice();
  cmkDragCheck();
  cmapPaint();
  cmapTipPaint();
}

/* What the browser may say about the tile under a drag, and no more.

   Two rules, both exact and both answerable here: the tile is on the map, and
   whether it is sea. Sea is the measured rule 16a banked - a tile is sea iff
   its map_heights pixel is not greyscale or is pure black, with river crossings
   force-excluded - read off the very layers 17e already loaded to name a tile.
   An admiral belongs on the sea and everybody else on land, which is
   `stratchar.check_character`'s own test, so the preview and the plan agree.

   Everything else the save might say - a general with no bodyguard, a name
   already taken - is the server's, arrives with the plan, and is not guessed
   at here. */
function cmkDragCheck(){
  const k = state.cmk, c = state.cmap;
  if(!k.drag) return;
  const [tx, ty] = k.drag.tile;
  k.drag.fault = '';
  if(!(tx >= 0 && ty >= 0 && tx < c.man.width && ty < c.man.height)){
    k.drag.fault = 'off the tile grid';
    return;
  }
  // 22a: a fort on the sea is a warning the plan gives, not a refusal - one of
  // DaC's watchtowers stands on it, and 22b's resources are the same - so the
  // ghost only refuses the grid
  if(k.drag.item.kind !== 'character') return;
  const sea = cmkSeaAt(tx, ty);
  if(sea === null) return;                       // the layers are not here to say
  const admiral = k.drag.item.type === 'admiral';
  if(admiral && !sea) k.drag.fault = 'an admiral stands on his ship, and this is land';
  if(!admiral && sea) k.drag.fault = 'this tile is sea';
}

//: The sea test, in the browser, off the same two layers the tooltip names.
//: `null` means the layers are not loaded and nothing may be claimed.
function cmkSeaAt(tx, ty){
  const h = cmapLayerRgb('heights', tx, ty);
  if(!h) return null;
  const f = cmapLayerRgb('features', tx, ty);
  if(f){
    const n = cmapNameColour('features', f);
    if(n.code === 'river_crossing') return false;   // never sea, whatever the height
  }
  if(h[0] === 0 && h[1] === 0 && h[2] === 0) return true;
  return !(h[0] === h[1] && h[1] === h[2]);
}

/* The drop. It plans, it does not write.

   The character panel beside the map already owns every part of this - the
   working copy, the debounce, the plan, the confirmation that lists the changed
   lines, the apply and the undo entry - so a drop opens that panel on this
   character, moves the two numbers and calls the save it would have called. One
   writer, one confirmation, one undo. */
async function cmkDrop(){
  const k = state.cmk, c = state.cmap;
  if(!k.drag) return;
  const d = k.drag;
  k.drag = null;
  cmapPaint();
  if(!d.tile || (d.tile[0] === d.from[0] && d.tile[1] === d.from[1])) return;
  if(d.fault){
    toast(`✗ ${d.item.name} cannot stand there: ${d.fault}.`, 6000);
    return;
  }
  const gy = c.man.height - 1 - d.tile[1];
  if(d.item.kind === 'fort' || d.item.kind === 'watchtower' || d.item.kind === 'resource'){
    activity('map marker', `${k.mod} drag ${d.item.kind} -> ${d.tile[0]},${gy}`);
    await cftDrop(d.item, [d.tile[0], gy]);
    return;
  }
  await cxOpen(d.item.faction);
  const kx = state.cx;
  if(!kx || !kx.d){ toast('✗ that faction’s people could not be read', 6000); return; }
  const i = kx.d.characters.findIndex(ch => ch.line === d.item.line
    || (ch.name && ch.name === d.item.name));
  if(i < 0){ toast(`✗ ${d.item.name} is not in ${d.item.faction}'s list any more`, 6000);
    return; }
  cxPick(i);
  if(!state.cx.w) return;
  state.cx.w.x = d.tile[0];
  state.cx.w.y = gy;
  cxPaint();
  activity('map marker', `${k.mod} drag ${d.item.name} -> ${d.tile[0]},${gy}`);
  cxSave('edit');
}

/* ---------- the panel ---------- */

//: The tooltip is cached by tile - it only rebuilds when the pointer changes
//: tile - so a layer that has just appeared or gone has to say the cache is out
//: of date, or the panel keeps naming markers that are no longer drawn.
function cmkStale(){
  if(state.cmap){ state.cmap.tipKey = ''; state.cmap.saidTip = ''; }
}

function cmkToggleLayer(){
  const k = state.cmk;
  if(!k) return;
  k.on = !k.on;
  if(k.on && !k.d && !k.loading) cmkLoad();
  cmkPaint();
  cmkStale();
  cmapPaint();
  cmapTipPaint();
}

function cmkToggleCat(id){
  const k = state.cmk;
  if(!k) return;
  k.cats[id] = !k.cats[id];
  cmkPaint();
  cmkStale();
  cmapPaint();
  cmapTipPaint();
}

function cmkFold(){
  const k = state.cmk;
  if(!k) return;
  k.open = !k.open;
  cmkPaint();
}

function cmkPaint(){
  const el = document.getElementById('cmMarks');
  if(!el) return;
  el.innerHTML = cmkHtml();
}

function cmkHtml(){
  const k = state.cmk;
  if(!k) return '';
  const counts = (k.d && k.d.counts) || {};
  const head = `<div class="cmkhead">
    <label class="chk" title="Draw everything descr_strat.txt puts on a tile.
Off by default: a map carrying hundreds of trade resources drawn over the
provinces is not a map any more.">
      <input type="checkbox" ${k.on ? 'checked' : ''} onchange="cmkToggleLayer()">
      <b>Markers</b></label>
    <span class="sp"></span>
    ${k.loading ? '<span class="count">reading descr_strat.txt…</span>'
      : k.d ? `<button class="cmkfold" onclick="cmkFold()">${k.open ? '▾' : '▸'}</button>`
            : ''}</div>`;
  if(k.err) return `<div class="cmmark">${head}<div class="w-bad">${esc(k.err)}</div></div>`;
  if(!k.on || !k.d || !k.open) return `<div class="cmmark">${head}</div>`;
  const rows = CMK_CATS.map(cat => {
    const n = counts[cat.id] || 0;
    return `<label class="chk cmkcat${n ? '' : ' none'}">
      <input type="checkbox" ${k.cats[cat.id] ? 'checked' : ''}
        ${n ? '' : 'disabled'} onchange="cmkToggleCat('${cat.id}')">
      ${esc(cat.label)} <span class="count">${n.toLocaleString()}</span></label>`;
  }).join('');
  const art = Object.keys(k.d.art || {}).length;
  const res = counts.resource || 0;
  return `<div class="cmmark">${head}
    <div class="cmkcats">${rows}</div>
    <div class="count">Drag a character, a fort, a watchtower or a resource to move it: the
      drop plans the same save its panel does, with the same confirmation and the
      same undo.
      ${res ? `This mod ships its own picture for ${art} of the
        ${new Set((k.d.items || []).filter(i => i.kind === 'resource')
          .map(i => i.name)).size} trade resources here; the rest draw a glyph,
        because the stock art is inside a .pack archive.` : ''}</div>
  </div>`;
}
