/* campmap.js - Campaign Map: the renderer

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE CAMPAIGN MAP - ten TGA layers, one canvas.

   Phase 16c built the renderer: it draws, it pans, it zooms and it tells you
   which tile is under the cursor. Phase 16d added the three things that make
   it readable and the one that makes it an editor - the layer stack remembered
   between sessions, a legend in which a layer's "nothing here" colour stops
   being drawn, a probe naming one tile on all ten layers at once, and the
   region record itself with its Code View. Phase 16e made it an editor of the
   pixels as well: campaint.js arms a brush over this canvas, writes through
   `cmapPixels` and repaints through `cmapAfterPaint`, and everything in this
   file that reads a layer reads the painted copy rather than the picture that
   arrived. It still does not validate; 16f is the validator.

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

/* 20a, D8: what the river overlay is drawn in until somebody picks otherwise.

   Not any of the three colours it replaces. `map_features.tga` writes a river
   (0,0,255), a crossing (0,255,255) and a source (255,255,255), and the first
   of those is near-black against the ground types the overlay is meant to be
   read over. This is a light blue with enough luminance to sit on both the
   ground layer's greens and the region layer's darker provinces. */
const CMAP_RIVER_RGB = [86, 180, 255];

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
    // 17f: somebody asked for this mod's factions through the Minor Files tab
    // and this mod has no map to put them on. The old mode is where they are.
    if(campmapWantFactions){ campmapWantFactions = false; setAppMode('factions'); }
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
/* ---------- what the screen remembers ---------- */

/* The layer stack, kept across sessions in `map_layers` on /api/settings.

   Same reasoning and the same road as `pane_sizes` in core.js: which layers a
   person works with, how transparent they want the provinces over the ground,
   and which draw on top are facts about how they read a map, not about the mod
   they happen to have open. 16c built all three controls and remembered none of
   them, so every visit started at the defaults.

   Kept per USER, not per mod, and that is deliberate: the layer codes are the
   engine's own ten and mean the same thing in every mod there is. What is not
   kept is anything about a particular map - the view, the selection and the
   picked tile all start fresh, because they are about a place rather than a
   habit. */
function cmapSettings(){
  const s = state.settings || (state.settings = {});
  const m = s.map_layers && typeof s.map_layers === 'object' ? s.map_layers : {};
  if(!m.on || typeof m.on !== 'object') m.on = {};
  if(!m.opacity || typeof m.opacity !== 'object') m.opacity = {};
  if(!m.hide || typeof m.hide !== 'object') m.hide = {};
  if(!Array.isArray(m.order)) m.order = [];
  // 20a's two ways of reading a layer rather than looking at it. Both are
  // habits rather than facts about a mod, so they are kept beside the rest.
  if(!m.river || typeof m.river !== 'object') m.river = {};
  if(!Array.isArray(m.river.rgb) || m.river.rgb.length !== 3)
    m.river.rgb = CMAP_RIVER_RGB.slice();
  s.map_layers = m;
  return m;
}

/* The layer stack as one plain object, in the shape settings.json keeps it.

   Split out of `cmapSaveLayers` by 20b, T9, and the split is the whole of that
   item's design: a named view preset is this same snapshot with a name on it,
   so there is one description of what the layer stack is and `mapviews.js`
   copies rather than re-derives it. Adding a switch to this screen adds it to
   both the remembered stack and every preset, in one place. */
function cmapLayerState(){
  const c = state.cmap;
  if(!c) return {};
  const m = {order: c.order.slice(), on: {}, opacity: {}, hide: {}};
  for(const [code, L] of Object.entries(c.layers)){
    m.on[code] = !!L.on;
    m.opacity[code] = L.opacity;
    if(L.hide.size) m.hide[code] = [...L.hide];
  }
  m.river = {on: !!c.rivers, rgb: c.riverRgb.slice()};
  m.height_alpha = !!c.heightAlpha;
  m.tip = c.tip !== false;
  return m;
}

let cmapSaveTimer = 0;
//: Coalesced: dragging an opacity slider fires `input` per pixel of travel, and
//: settings.json is rewritten whole either way.
function cmapSaveLayers(){
  const c = state.cmap, m = cmapSettings();
  if(!c) return;
  Object.assign(m, cmapLayerState());
  clearTimeout(cmapSaveTimer);
  cmapSaveTimer = setTimeout(() => {
    try{ api.post('/api/settings', {map_layers:m}); }catch(e){}
  }, 400);
}

/* The saved draw order, reconciled with the layers this manifest actually has.

   A saved order is a list of codes written by an older run of the tool, and the
   two ways it can be wrong are both ordinary: a layer the manifest no longer
   lists (it was renamed, or this build knows fewer) and a layer the saved list
   never saw. Codes that are still real keep their saved place, anything new
   goes where the server put it, and nothing is dropped or invented. */
function cmapOrder(man, saved){
  const real = man.layers.map(l => l.code);
  // Not a list at all is one of the ways it can be wrong, and 20b is what made
  // that reachable: a preset comes out of settings.json, which is a file a
  // person can open. Reconciling against the manifest means not trusting the
  // type either.
  const out = (Array.isArray(saved) ? saved : []).filter(c => real.includes(c));
  for(let i = 0; i < real.length; i++)
    if(!out.includes(real[i])) out.splice(Math.min(i, out.length), 0, real[i]);
  return out;
}

/* The screen's whole state, in one object, rebuilt whenever the mod changes.

   `layers` is keyed by code and each entry owns its own <img>: a layer is
   fetched once and stays, so ticking it off and on again is free. `comp` is the
   composite - one canvas at map size that everything on screen is copied out
   of. `sel` and `hover` are tile coordinates or null, never a pixel colour,
   because the colour is a lookup away and a stale one would be a lie.

   A layer also carries a `hide` set of packed colour keys and the `masked`
   canvas that set produced. Both start from the manifest's own `blank` - the
   colour that layer uses for "there is nothing here" - so features and trade
   routes open as overlays rather than as a sheet over the map, before any
   legend has been fetched. */
function cmapNew(mod, man){
  const byKey = new Map();
  for(const r of man.regions) byKey.set(r.key, r);
  const saved = cmapSettings();
  const layers = {};
  for(const l of man.layers){
    const hide = (l.code in saved.hide) ? (saved.hide[l.code] || [])
               : (l.blank ? [l.blank.key] : []);
    layers[l.code] = {
      def: l,
      on: (l.code in saved.on ? !!saved.on[l.code] : l.on) && l.present,
      opacity: typeof saved.opacity[l.code] === 'number'
        ? saved.opacity[l.code] : l.opacity,
      img: null, loading: false, failed: '',
      hide: new Set(hide), masked: null, maskKey: '',
      // 20a: how many tiles the river overlay drew out of this layer, and the
      // 256-entry height ramp T2's transparency is read off. Both are produced
      // by the mask pass and both are null until it has run.
      rivertiles: 0, ramp: null,
      // the browser's own readable/writable copy of this layer's pixels, made
      // on first need and from then on the truth about the layer - see
      // cmapPixels. 16c kept one of these for the region layer alone.
      cv: null, px: null,
      legend: null, legendBusy: false, legendErr: '', open: false,
    };
  }
  return {
    mod, man, byKey,
    /* 20b, D14: which campaign every route that takes one is asked for.

       Empty means the server's own fallback (`imperial_campaign`), which is
       what every request on this screen carried before 20b, so an empty string
       is the same behaviour rather than a missing value. It starts empty on
       every mod and is NOT remembered between sessions, which is the mirror of
       16d's ruling about the layer stack: the layer codes are the engine's own
       ten and mean the same thing everywhere, so they are a habit worth
       keeping; a campaign is one mod's own folder and remembering it would mean
       opening a mod into a campaign that only the last mod had. */
    campaign: '',
    // draw order is the server's until somebody has moved a layer, and then it
    // is theirs - the arrows move a layer within this array and nothing else
    // has to know
    order: cmapOrder(man, saved.order),
    layers,
    comp: null, compKey: '',
    // 16g's colouring: the region layer recoloured through a table the server
    // built, drawn over the whole stack. Null when nothing is themed.
    overlay: null, overlayKey: '', overlayAlpha: 0.85,
    // 20a's two readings. `rivers` lifts the three river colours out of the
    // features layer and draws them in `riverRgb` alone; `heightAlpha` draws
    // the heights layer as transparency instead of as grey. Both live on the
    // screen rather than on the layer because each belongs to exactly one
    // layer and there is nothing to key them by.
    rivers: !!(saved.river && saved.river.on),
    riverRgb: (saved.river && saved.river.rgb) || CMAP_RIVER_RGB.slice(),
    heightAlpha: !!saved.height_alpha,
    view: {zoom: 1, ox: 0, oy: 0, fitted: false},
    hover: null, sel: null, outline: null, outlineKey: -1,
    // 17e's tooltip: where the pointer is in the stage, whether the panel is
    // wanted at all, and whether a drag is holding it down
    ptr: null, tip: saved.tip !== false, tipHold: false, saidTip: '', tipKey: '',
    stageW: 0, stageH: 0,
    // the picked tile, what all ten layers say about it, and the region record
    // it belongs to with the working copy the form edits
    pick: null, probe: null, probeErr: '', det: null, busy: false,
    // which marker the pick landed on, if any, and the tile->region index 17c
    // answers it from
    marker: '', markerAt: null,
    ms: 0,
  };
}

/* `&campaign=…` for a request that takes one, or nothing at all.

   Every campaign-fed route on this screen has accepted a campaign since 16g and
   none of them was ever sent one: the server's fallback was the only campaign
   the browser could name. This is the one place that appends it, so a route
   added later cannot forget - and an empty `c.campaign` appends nothing, which
   is byte-for-byte the request 16g to 19b were making. */
function cmapCampQ(){
  const c = state.cmap;
  return (c && c.campaign) ? `&campaign=${enc(c.campaign)}` : '';
}

/* Read a different campaign, and drop everything that was read out of the last
   one. 20b, D14 - the browser lists and asks; this is what a pick costs.

   Five panels hold a parse of `descr_strat.txt` or something joined to it, and
   every one of them keys its state on the mod alone, because until now the
   campaign could not change without the mod changing. Rather than teach five
   files a second key, the screen that owns the campaign nulls what it
   invalidates and re-renders: each panel's own `…Open` then rebuilds from
   scratch and re-reads if it was open.

   Two things are deliberately kept. The paint session, because unsaved strokes
   are pixels on the base map and the base map is the same map whichever
   campaign reads it - throwing them away here would be a campaign switch that
   destroys work it has nothing to do with. And the view: the zoom and the pan
   are where you were looking, and a province does not move. */
function cmapSetCampaign(rel){
  const c = state.cmap;
  if(!c) return;
  const want = String(rel || '');
  if(want === (c.campaign || '')) return;
  // The one panel here with a dirty test of its own. The settlement and people
  // forms save per field through their own debounce and hold no unsaved copy
  // worth warning about; the events panel builds a whole block before it writes
  // anything, and that is the one somebody can lose.
  if(typeof cevDirty === 'function' && cevDirty()
     && !confirm('Read a different campaign?\n\n'
        + 'The events panel has an unsaved block in it, and it is a block in '
        + 'the campaign you are leaving.')) return;
  c.campaign = want;
  // Which panels were open, so that switching campaign is not also a panel
  // switch: every one of these keys its state on the mod alone, so the reset
  // below takes it back to closed. They are re-opened through their own
  // toggles rather than by writing their flags, because a toggle is also what
  // knows to re-read - and re-reading is the point.
  const was = {cbr: state.cbr && state.cbr.open,
               cj: state.cj && state.cj.open,
               cev: state.cev && state.cev.open,
               cq: state.cq && state.cq.open,
               cchk: state.cchk && state.cchk.open,
               cmk: state.cmk && state.cmk.on};
  // what was read out of the campaign that is being left
  state.cj = null; state.cx = null; state.cset = null;
  state.cmk = null; state.cev = null; state.cq = null; state.cchk = null;
  c.det = null; c.cv = null; c.overlay = null; c.overlayKey = '';
  activity('campaign browser', `read ${want || 'the default campaign'}`);
  renderCampmap();
  if(was.cj) cjToggle();
  if(was.cev) cevToggle();
  if(was.cq) cqToggle();
  if(was.cchk) cchkToggle();
  if(was.cmk) cmkToggleLayer();
  if(was.cbr && state.cbr && !state.cbr.open) cbrToggle();
  // the region that was open, re-read out of the campaign now being read: who
  // holds it and what is standing in it are the campaign's answers, not the
  // map's, and the province itself has not moved
  if(c.sel && c.sel.name){
    cmapOpenRegion(c.sel.name);
    csOpen(c.sel.name);
    cmapOpenPeople(c.sel.name);
  }
}

/* Centre the map on a tile and pick it.

   One copy of six lines that were written three times: the query panel's jump
   to a province, the validator's jump to a finding, and 20b's find box. Three
   callers is where a third copy stops being a coincidence - and the rule this
   file states about the two transform lines applies to arriving as well as to
   drawing. `zoom` is a floor rather than a setting: somebody already zoomed
   further in than that was looking at something.

   `region` is the province the caller already knows this tile is in, and it
   closes a half-arrival all three of them had. `cmapPick` resolves a province
   by reading the colour under the tile off the region layer's own pixels, so
   with that layer never fetched - it is one tick away from off, and off is a
   perfectly ordinary way to read a map - a jump would centre on the tile and
   select nothing, with only the probe's sentence to say where you were. Every
   caller that HAS the name passes it: a query row is a province and a find hit
   is one. A finding is not - `mapcheck` reports a tile and a sentence about
   what is wrong there, and half of those are faults with no province at all -
   so the validator's jump passes nothing and is unchanged. The pick is given a
   second chance from the manifest rather than a layer being turned on behind
   somebody's back, which is the call 20a made about controls that rearrange
   the stack. */
function cmapGoTile(tile, zoom, region){
  const c = state.cmap;
  if(!c || !tile) return;
  const [w, h] = cmapCanvasSize();
  const v = c.view;
  v.zoom = Math.max(v.zoom, zoom || 6);
  v.ox = w / 2 - (tile[0] + 0.5) * v.zoom;
  v.oy = h / 2 - (tile[1] + 0.5) * v.zoom;
  v.fitted = true;
  cmapPick(tile);
  if(!region || c.sel) return;
  const r = c.man.regions.find(x => x.name === region);
  if(!r) return;
  c.sel = r;
  cmapOutline(r);                 // a no-op without the layer's pixels, by design
  cmapPaint();
  cmapOpenRegion(r.name);
  csOpen(r.name);
  cmapOpenPeople(r.name);
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
          <button onclick="cmapFit()" title="Fit the whole map (Shift+0).
The bare number keys tick a layer - 1 to 0, one for each of the ten.">⤢ Fit</button>
          <button onclick="cmapZoomTo(1)"
            title="One screen pixel per tile (Shift+1)">1:1</button>
          <button onclick="cmapZoomBy(1/1.4)" title="Zoom out (−)">−</button>
          <button onclick="cmapZoomBy(1.4)" title="Zoom in (+)">+</button>
          <button id="cmTipBtn" class="${c.tip === false ? '' : 'on'}"
            onclick="cmapTipToggle()"
            title="Name the tile under the pointer on every layer at once (T).
Answered here, out of the map you were already sent - no request per pixel.">ⓘ Names</button>
          <span class="count" id="cmZoom"></span>
        </div>
        <div class="cmread" id="cmRead">move the pointer over the map</div>
        <div class="cmtip" id="cmTip" hidden></div>
        <div class="cmperf" id="cmPerf"></div>
      </div>
      <div class="cmside" id="cmSide">
        <div class="cmhead">
          <b>${esc(c.mod)}</b>
          <span class="count">${m.width}×${m.height} tiles ·
            ${m.regions.filter(r => r.id >= 0).length} regions ·
            ${m.regions.filter(r => r.settlement).length} settlements ·
            ${m.regions.filter(r => r.port).length} ports</span>
        </div>
        ${cmapFindingsHtml(m.findings)}
        <div id="cmCamps"></div>
        <div id="cmFind"></div>
        <div id="cmViews"></div>
        <div id="cmCheck"></div>
        <div id="cmQuery"></div>
        <div id="cmPaint"></div>
        <div id="cmMarks"></div>
        <div id="cmEvents"></div>
        <div class="cmlayers" id="cmLayers">${cmapLayersHtml()}</div>
        <div class="cmpick" id="cmPick"></div>
        <div class="cmsettle" id="cmSettle"></div>
        <div class="cmchars" id="cmChars"></div>
        <div class="cmcamp" id="cmCamp"></div>
        <div class="cmmodels" id="cmModels"></div>
      </div>
    </div>`;
  cmapWire();
  cbrOpen();          // 20b, D14, and it reads nothing until somebody opens it
  cfdOpen();          // 20b, T8, and it never reads anything at all
  cvwOpen();          // 20b, T9, out of the settings the page already has
  cchkOpen();
  cqOpen();
  cpaintOpen();
  cmkOpen();          // 17d, and it reads nothing until the layer is ticked
  cevOpen();          // 18b, and it reads its two files only once opened
  cmapPickPaint();
  csPaint();          // 16h: kept out of cmapPickPaint, which owns #cmPick only
  cxPaint();          // 16i, for the same reason
  cjOpen();           // 16j, and it reads nothing until somebody opens it
  cmodOpen();         // 16k, the strat models, and the same on both counts
  cmapResize();
  // 17f: arrived here from Minor Files' Factions tab, which is now a route to
  // the combined faction screen rather than to a mode of its own
  if(campmapWantFactions){
    campmapWantFactions = false;
    if(!state.cj || !state.cj.open) cjToggle();
    cjTab('faction');
  }
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
    // how much of this layer is not being drawn, so a layer that is on and
    // invisible is never a mystery
    const hid = L.hide.size && !(code === 'features' && c.rivers)
      ? ` <span class="cmhid" title="colours punched through">
      ${L.hide.size} hidden</span>` : '';
    // 20a, T11: the key that ticks this layer, printed on the row it ticks. The
    // digit is the server's - campmap.HOTKEYS - so the panel cannot promise a
    // key the handler does not answer to.
    const key = d.hotkey ? `<b class="cmkey" title="Press ${d.hotkey} to show or hide
      this layer">${esc(d.hotkey)}</b>` : '';
    return `<div class="cmlayer${L.on ? ' on' : ''}${d.present ? '' : ' off'}" data-code="${code}">
      <label class="chk"><input type="checkbox" ${L.on ? 'checked' : ''}
        ${d.present ? '' : 'disabled'} data-lcheck="${code}">
        ${key}<span class="cmnm">${esc(d.label)}</span></label>
      <span class="cmmove">
        <button data-lleg="${code}" ${d.present ? '' : 'disabled'} class="${L.open ? 'on' : ''}"
          title="What every colour on this layer means, and how much of the map it covers"
          >${L.open ? '▾' : '▸'}</button>
        <button data-lup="${code}" ${i === 0 ? 'disabled' : ''} title="Draw later (up)">▲</button>
        <button data-ldn="${code}" ${i === c.order.length - 1 ? 'disabled' : ''}
          title="Draw earlier (down)">▼</button></span>
      <input type="range" min="0" max="100" value="${Math.round(L.opacity * 100)}"
        data-lop="${code}" ${d.present && L.on ? '' : 'disabled'}>
      <span class="cmpct">${Math.round(L.opacity * 100)}%</span>
      <div class="cmnote">${note}${hid}</div>
      ${d.present ? cmapModeHtml(code) : ''}
      ${L.open ? cmapLegendHtml(code) : ''}
    </div>`;
  }).reverse().join('');
}

/* The two layers 20a gave a second way of being read, and their controls.

   Neither is a layer of its own and that is the decision worth stating. The
   stack is the ten files the map is made of - it is what the ten number keys
   count, what the draw order orders and what `check_layers` validates - so a
   river overlay that is `map_features.tga` read differently belongs ON that
   layer's row rather than beside it as an eleventh entry. Same for the heights.
   Ticking either one ticks its layer on, because a reading of a layer that is
   not being drawn is a control that appears to do nothing. */
function cmapModeHtml(code){
  const c = state.cmap;
  if(code === 'features'){
    const n = c.layers.features.rivertiles;
    return `<div class="cmmode">
      <label class="chk" title="Draw only the river network - river, crossing and source -
in one colour of your own, instead of three colours inside a layer that is almost
all 'nothing here'. Open the legend for this map's own figure.">
        <input type="checkbox" data-lriver ${c.rivers ? 'checked' : ''}>
        <span>Rivers only</span></label>
      <input type="color" data-lrivercol value="${cmapHex(c.riverRgb)}"
        title="What the river network is drawn in" ${c.rivers ? '' : 'disabled'}>
      ${c.rivers ? `<span class="count">${n.toLocaleString()} river
        tile${n === 1 ? '' : 's'}${c.layers.features.hide.size
          ? ' · the hidden colours do not apply while this is on' : ''}</span>` : ''}
    </div>`;
  }
  if(code === 'heights'){
    // A layer drawn as transparency is a layer you see THROUGH, so anything
    // still drawn over it hides it whatever its alpha says - and the default
    // stack has the ground types over the heights. Said, and offered, rather
    // than done: the draw order is one of the three things this screen keeps
    // between sessions, and a control that quietly rearranged it would be
    // taking a habit away to make its own feature look better.
    const over = c.heightAlpha
      ? c.order.slice(c.order.indexOf('heights') + 1)
          .filter(x => c.layers[x].on && c.layers[x].def.present) : [];
    // this map's own median land height, counted by the pass that built the
    // ramp. Zero until that pass has run, and then the sentence appears.
    const med = (c.layers.heights.ramp || {}).median || 0;
    return `<div class="cmmode">
      <label class="chk" title="Darker is more transparent, so what is under the heights
shows through the low ground">
        <input type="checkbox" data-lalpha ${c.heightAlpha ? 'checked' : ''}>
        <span>Height as transparency</span></label>
      ${c.heightAlpha ? `<span class="count">the sea is not drawn, and the ramp is spread
        over the heights THIS map has${med
          ? ` - half its land is no higher than ${med} of 255` : ''}</span>` : ''}
      ${over.length ? `<span class="w-warn">${esc(c.layers[over[over.length - 1]].def.label)}${
        over.length > 1 ? ` and ${over.length - 1} more` : ''} still draw${
        over.length > 1 ? '' : 's'} over it.</span>
        <button data-ltop="heights" title="Put the heights at the top of the stack, so what
is under them shows through">Put it on top</button>` : ''}
    </div>`;
  }
  return '';
}

//: `#rrggbb` for an `<input type="color">`, and back. The screen keeps a triple
//: because everything else about a map colour is one.
function cmapHex(rgb){
  return '#' + rgb.map(v => Math.max(0, Math.min(255, v | 0))
    .toString(16).padStart(2, '0')).join('');
}
function cmapUnhex(hex){
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''));
  if(!m) return CMAP_RIVER_RGB.slice();
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/* A layer shown or hidden, from the tickbox or from its number key.

   One path for both, which is 20a's doing: T11 gave every layer a key, and two
   places that tick a layer are two places to forget to save the setting or to
   fetch the picture. `want` omitted flips it, which is what a key does. */
function cmapToggleLayer(code, want){
  const c = state.cmap, L = c && c.layers[code];
  // a layer this mod does not ship has a disabled tickbox, and its key does the
  // same nothing rather than turning on a layer there is no picture for
  if(!L || !L.def.present) return;
  L.on = want === undefined ? !L.on : !!want;
  activity('map layer', `${L.on ? 'showed' : 'hid'} ${code}`);
  cmapLoadLayers();
  cmapSaveLayers();
  cmapRepanel();
}

/* One of 20a's two readings, switched. `field` is the flag on the screen state
   and `code` is the layer it is a reading OF - the pair is fixed, and the panel
   is the only caller.

   The layer is ticked on when the reading is: `cmapCompose` draws what `on`
   says, and a river overlay on a features layer nobody has ticked is a control
   that does nothing and does not say why. */
function cmapMode(code, field, on){
  const c = state.cmap, L = c.layers[code];
  c[field] = on;
  if(on && L.def.present && !L.on){
    L.on = true;
    activity('map layer', `showed ${code}`);
  }
  L.maskKey = '';
  if(L.img) cmapMask(c, code);
  cmapCompose(); cmapPaint(); cmapSaveLayers(); cmapRepanel();
  if(!L.img && L.on) cmapLoadLayers();
}

/* The canvas's handlers, bound ONCE per screen.

   Kept apart from the panel's on purpose, and that separation is a bug fix
   rather than tidiness: `cmapRepanel` rebuilds the layer list and re-wires it,
   and it used to re-wire this too - so every tick of a layer added another full
   set of pointer listeners to the same canvas and a 10-pixel drag moved the map
   by 10 pixels per listener. Measured at 110 after eleven repanels. 16d ticks
   far more often than 16c did (every legend opened, every colour hidden), which
   is what made it visible.

   `state.cmapBound` is the canvas element itself rather than a flag, because a
   new mod rebuilds the markup and hands us a different <canvas> that does need
   wiring. */
function cmapWireCanvas(){
  const cv = document.getElementById('cmCanvas');
  if(!cv || state.cmapBound === cv) return;
  state.cmapBound = cv;
  cmapPointers(cv);
  cmapKeys();
  // The canvas is a flex child of a stage that moves with the window, and it is
  // the one thing on the page that has to be told.
  if(state.cmapRO) state.cmapRO.disconnect();
  state.cmapRO = new ResizeObserver(() => { cmapResize(); cmapPaint(); });
  state.cmapRO.observe(document.getElementById('cmStage'));
}

function cmapWire(){
  cmapWireCanvas();
  cmapWireLayers();
}

//: The layer list's own handlers. Re-run every time that markup is rebuilt,
//: which is often - and nothing outside the list is touched by it.
function cmapWireLayers(){
  const box = document.getElementById('cmLayers');
  if(!box) return;
  box.querySelectorAll('[data-lcheck]').forEach(cb => cb.onchange = () =>
    cmapToggleLayer(cb.dataset.lcheck, cb.checked));
  // `input` rather than `change`: an opacity slider that only answers on release
  // is a slider you cannot judge a blend with
  box.querySelectorAll('[data-lop]').forEach(sl => sl.oninput = () => {
    state.cmap.layers[sl.dataset.lop].opacity = (+sl.value) / 100;
    sl.parentElement.querySelector('.cmpct').textContent = sl.value + '%';
    cmapCompose(); cmapPaint(); cmapSaveLayers();
  });
  box.querySelectorAll('[data-lup]').forEach(b => b.onclick = () => cmapMove(b.dataset.lup, 1));
  box.querySelectorAll('[data-ldn]').forEach(b => b.onclick = () => cmapMove(b.dataset.ldn, -1));
  box.querySelectorAll('[data-lleg]').forEach(b => b.onclick = () => {
    const L = state.cmap.layers[b.dataset.lleg];
    L.open = !L.open;
    cmapRepanel();
    if(L.open) cmapLegend(b.dataset.lleg);
  });
  box.querySelectorAll('[data-lhide]').forEach(cb => cb.onchange = () =>
    cmapHideColour(cb.dataset.lhide, +cb.dataset.key, cb.checked));
  // 20a's two readings
  box.querySelectorAll('[data-lriver]').forEach(cb => cb.onchange = () => {
    activity('map layer', `${cb.checked ? 'lifted the rivers out of' : 'put the rivers back into'} map_features.tga`);
    cmapMode('features', 'rivers', cb.checked);
  });
  // `input` rather than `change`, same as the opacity slider: a colour you can
  // only judge after closing the picker is a colour you pick twice
  box.querySelectorAll('[data-lrivercol]').forEach(el => el.oninput = () => {
    const c = state.cmap;
    c.riverRgb = cmapUnhex(el.value);
    const L = c.layers.features;
    L.maskKey = '';
    if(L.img) cmapMask(c, 'features');
    cmapCompose(); cmapPaint(); cmapSaveLayers();
  });
  box.querySelectorAll('[data-ltop]').forEach(b => b.onclick = () => cmapMoveTop(b.dataset.ltop));
  box.querySelectorAll('[data-lalpha]').forEach(cb => cb.onchange = () => {
    activity('map layer', `drew the heights as ${cb.checked ? 'transparency' : 'grey'}`);
    cmapMode('heights', 'heightAlpha', cb.checked);
  });
}

//: Redraw the panel in place. The canvas is deliberately not in it - rebuilding
//: the markup would throw away the <canvas> and its context with it.
function cmapRepanel(){
  const box = document.getElementById('cmLayers');
  if(!box) return;
  box.innerHTML = cmapLayersHtml();
  cmapWireLayers();
}

function cmapMove(code, dir){
  const o = state.cmap.order, i = o.indexOf(code), j = i + dir;
  if(i < 0 || j < 0 || j >= o.length) return;
  o[i] = o[j]; o[j] = code;
  cmapCompose(); cmapPaint(); cmapSaveLayers(); cmapRepanel();
}

//: All the way up, in one press. The arrows are one step each and 20a made a
//: nine-press journey worth having a button for - see `cmapModeHtml`.
function cmapMoveTop(code){
  const o = state.cmap.order, i = o.indexOf(code);
  if(i < 0 || i === o.length - 1) return;
  o.splice(i, 1); o.push(code);
  activity('map layer', `drew ${code} last`);
  cmapCompose(); cmapPaint(); cmapSaveLayers(); cmapRepanel();
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
  for(const code of want) cmapMask(c, code);
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
  // what the mask pass did is in the key: punching a colour through, lifting
  // the rivers out or drawing the heights as transparency all change the
  // picture, and a composite that did not notice would show the old one
  const key = shown.map(code => `${code}:${c.layers[code].opacity}`
    + `:${cmapModeKey(c, code)}`).join('|')
    + `|${c.overlayKey || ''}:${c.overlayAlpha}`;
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
    x.drawImage(L.masked || L.cv || L.img, 0, 0, m.width, m.height);
  }
  // 16g's colouring, drawn over everything. It is a recolour of the region
  // layer rather than another layer, so it belongs on top of the stack and not
  // in it: the stack stays the ten files the map is made of, and ticking one
  // off while a theme is on still does what it says.
  if(c.overlay){
    x.globalAlpha = c.overlayAlpha == null ? 0.85 : c.overlayAlpha;
    x.drawImage(c.overlay, 0, 0, m.width, m.height);
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
  // The stage's size, kept here because 17e's tooltip decides which side of the
  // cursor to sit on from it, and reading it back per pointer event would force
  // a layout on the one path that is not allowed to cost anything.
  const c = state.cmap, st = document.getElementById('cmStage');
  if(c && st){ c.stageW = st.clientWidth; c.stageH = st.clientHeight; }
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

  /* 17b - the trail the hover box left behind.

     A dirty rectangle is worked out in CSS pixels and the canvas is backed at
     devicePixelRatio, which on a 150% Windows display is 1.5. A rectangle on a
     CSS pixel boundary therefore lands half way through a device pixel, and the
     clip, the fill and the blit are all antialiased against that edge - so the
     boundary pixel keeps half of the frame before it. One tile of hover leaves
     a one-pixel darker outline, and a pointer sweep leaves a trail of them:
     1,330 pixels of residue over two sweeps on this machine, measured by
     diffing the dirty-rect frame against a full repaint of the same view.

     Snapping the rectangle outwards to whole device pixels costs at most one
     pixel of extra repaint per edge and removes the class of fault, rather than
     the hover box's instance of it. */
  const snap = r => [Math.floor(r[0] * dpr) / dpr, Math.floor(r[1] * dpr) / dpr,
                     Math.ceil(r[2] * dpr) / dpr, Math.ceil(r[3] * dpr) / dpr];
  const R = dirty ? snap(dirty) : [0, 0, w, h];
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

  /* The stroke being drawn right now, before the server has answered.

     A map-sized canvas that tiles are added to as the pointer passes over them
     and blitted here like the outline, rather than a few thousand strokeRects
     per frame. It is a promise, not a result: what lands is what Python did
     with the same samples, and this is thrown away and replaced by that on
     pointer-up. */
  const trail = cpaintTrail();
  if(trail){
    x.imageSmoothingEnabled = false;
    x.globalAlpha = 0.7;
    x.drawImage(trail, s0, t0, s1 - s0, t1 - t0,
                cmapX(s0), cmapY(t0), (s1 - s0) * v.zoom, (t1 - t0) * v.zoom);
    x.globalAlpha = 1;
  }

  if(v.zoom >= CMAP_GLYPH_ZOOM){
    // A glyph is drawn ON the tile, from the same two lines as everything else,
    // so it cannot drift off the pixel it is about however far you zoom in.
    // 17d: with the markers layer drawing settlements, this glyph is the same
    // pixel said twice - the campaign file's icon stands on it. The port glyph
    // stays either way: no record in descr_strat.txt is a port, so nothing else
    // draws one.
    const settleGlyph = !(state.cmk && state.cmk.on && state.cmk.cats.settlement
                          && state.cmk.groups.length);
    for(const r of c.man.regions){
      for(const [p, kind] of [[r.settlement, 's'], [r.port, 'p']]){
        if(!p || (kind === 's' && !settleGlyph)) continue;
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

  // 17d's markers sit above the layers and below the hover cell, so the cell
  // the pointer is on is never hidden by what is standing on it
  if(typeof cmkDraw === 'function') cmkDraw(x, s0, t0, s1, t1);

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
/* …and one thing 16e adds: which of the two the left button is for.

   With the paint tool armed the left button draws and the other two still pan,
   because a tool you have to put down to move the view is a tool you fight.
   With it off, nothing below behaves differently from 16c. */
function cmapPointers(cv){
  let last = null, moved = 0, mode = '';
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('pointerdown', e => {
    last = [e.clientX, e.clientY]; moved = 0;
    cv.setPointerCapture(e.pointerId);
    mode = (e.button === 0 && cpaintArmed()) ? 'paint' : 'pan';
    // 17d: with the brush down the left button paints, as 16e settled. With it
    // up, a left press that starts on a character takes the button off the pan
    // and onto that character - the same rule, one layer further out.
    if(mode === 'pan' && e.button === 0 && typeof cmkDragStart === 'function'
       && cmkDragStart(cmapEventTile(cv, e))) mode = 'mark';
    if(mode === 'paint') cpaintDown(cmapEventTile(cv, e));
  });
  cv.addEventListener('pointerup', e => {
    if(mode === 'paint') cpaintUp();
    else if(mode === 'mark'){
      // a press on a character that never travelled is still a pick, exactly as
      // it is anywhere else on the map - taking the click away from the tile
      // because something is standing on it is how 17c happened
      if(last && moved < CMAP_DRAG_SLOP){
        if(state.cmk) state.cmk.drag = null;
        cmapPaint();
        cmapPick(cmapEventTile(cv, e));
      }else cmkDrop();
    }
    else if(last && moved < CMAP_DRAG_SLOP && state.cmap) cmapPick(cmapEventTile(cv, e));
    last = null; mode = '';
    if(state.cmap){ state.cmap.tipHold = false; cmapTipPaint(); }
    try{ cv.releasePointerCapture(e.pointerId); }catch(err){}
  });
  cv.addEventListener('pointercancel', () => {
    if(mode === 'paint') cpaintCancel();
    if(mode === 'mark' && state.cmk){ state.cmk.drag = null; cmapPaint(); }
    last = null; mode = '';
  });
  cv.addEventListener('pointerleave', () => {
    const c = state.cmap;
    if(!c) return;
    c.ptr = null;
    if(!c.hover){ cmapTipPaint(); return; }
    const was = cmapCellRect(...c.hover);
    c.hover = null;
    cmapPaint(was);
    cmapTipPaint();
  });
  cv.addEventListener('pointermove', e => {
    const c = state.cmap;
    if(!c) return;
    // where the panel goes, in the stage's own pixels. 17e.
    const b = cv.getBoundingClientRect(), st = document.getElementById('cmStage');
    const s = st ? st.getBoundingClientRect() : b;
    c.ptr = [e.clientX - s.left, e.clientY - s.top];
    // A drag is not a read: the panel would sit under the stroke being painted
    // and follow a pan it is not about, so it stands down until the button is up
    c.tipHold = !!(mode || last);
    if(mode === 'paint'){
      cpaintMove(cmapEventTile(cv, e));
      cmapHover(cmapEventTile(cv, e));
      return;
    }
    if(mode === 'mark'){
      cmkDragMove(cmapEventTile(cv, e));
      cmapHover(cmapEventTile(cv, e));
      return;
    }
    if(last){
      const dx = e.clientX - last[0], dy = e.clientY - last[1];
      moved += Math.abs(dx) + Math.abs(dy);
      last = [e.clientX, e.clientY];
      c.view.ox += dx; c.view.oy += dy;
      // a pan moves everything, so this is the one interaction that is a whole
      // frame - and a whole frame is one drawImage of a sub-rect
      cmapPaint();
      cmapTipPaint();
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
  if(same){ cmapReadout(); cmapTipPaint(); return; }
  const was = c.hover ? cmapCellRect(...c.hover) : null;
  c.hover = next;
  if(next) cmapPaint(cmapCellRect(tx, ty));
  if(was) cmapPaint(was);
  if(!next && !was) cmapReadout();
  cmapTipPaint();
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

  // 17e: with the pointer on the map the tooltip beside it says all of this and
  // nine layers more, so the corner line would be the same tile twice, two
  // centimetres apart. It goes back to being the affordance it started as.
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
  // 17d: a drag holds the tooltip down, so this is the only line on screen
  // while one is in progress - and where it would land, and why it may not, is
  // the whole of what somebody dragging wants to read.
  const drag = state.cmk && state.cmk.drag;
  if(drag && drag.tile){
    html = `<b>${esc(drag.item.name || drag.item.kind)}</b> → `
      + `<b>${drag.tile[0]}, ${c.man.height - 1 - drag.tile[1]}</b> game`
      + (drag.fault ? ` · <span class="w-bad">${esc(drag.fault)}</span>`
                    : ' · <span class="w-good">drop to plan the move</span>');
  }
  const hide = !drag && !!(c.hover && c.tip !== false);
  if(el.hidden !== hide) el.hidden = hide;
  if(!hide && c.saidRead !== html){ el.innerHTML = html; c.saidRead = html; }
}

/* ---------- the hover tooltip (17e) ----------

   Mylae's `MapPixelTooltip` is the thing his map reads best: hover a tile and a
   small panel beside the cursor names it on every layer at once. 16d had the
   same answer already - `campmap.probe_pixel` names one tile across all ten
   layers in 0.17 ms on vanilla and 0.80 ms on DaC - but put it behind a CLICK,
   because a round trip on the pointer is what this screen's rules exist to
   prevent. So this is the probe's answer, worked out in the browser: the layer
   pixels are the ones it was already served and the three tables it cannot
   derive travel with the manifest (`_vocab_view`).

   Two things his version gets wrong and this one does not. He nearest-colour
   matches a layer's legend within a distance of 30, which names colours that
   are not in the file at all, and tolerance-matches regions within 6, which on
   a map carrying a one-channel painting slip - and both real maps carry
   several - confidently names the wrong province. Every match here is exact,
   and a colour no table claims is said to be one. */

/* The panel on or off, remembered with the layer settings.

   It is on by default: naming what is under the pointer is the whole point of
   a map editor, and the cost is ten 1x1 reads. Off is for painting a long
   stroke, or for a screenshot. */
function cmapTipToggle(){
  const c = state.cmap;
  if(!c) return;
  c.tip = c.tip === false;
  const b = document.getElementById('cmTipBtn');
  if(b) b.classList.toggle('on', c.tip !== false);
  c.saidRead = null;
  cmapReadout();
  cmapTipPaint();
  cmapSaveLayers();
}

/* What one layer's colour at this tile is called, and its code name.

   A mirror of `campmap._colour_name`, and deliberately a small one: the tables
   arrive in the manifest and the four rules are four rules. `code` of null is
   the load-bearing half - it means NO TABLE THIS TOOLKIT HAS NAMES THIS
   COLOUR, which on DaC is a real answer (a stray (1,1,1) in map_features.tga,
   five colours in map_climates.tga that no climate declares) and is never
   rounded to the nearest thing that is named. */
function cmapNameColour(code, rgb){
  const c = state.cmap, v = (c.man && c.man.vocab) || {};
  const [r, g, b] = rgb;
  const k = (r << 16) | (g << 8) | b;
  const hit = list => (list || []).find(e => e.rgb && ((e.rgb[0] << 16) | (e.rgb[1] << 8) | e.rgb[2]) === k);
  if(code === 'regions'){
    const mk = c.man.markers;
    if(k === ((mk.settlement[0] << 16) | (mk.settlement[1] << 8) | mk.settlement[2]))
      return {name: 'Settlement marker', code: 'settlement'};
    if(k === ((mk.port[0] << 16) | (mk.port[1] << 8) | mk.port[2]))
      return {name: 'Port marker', code: 'port'};
    const reg = c.byKey.get(k);
    if(reg && reg.name) return {name: reg.name, code: reg.name, region: reg};
    return {name: '', code: null, region: reg || null};
  }
  if(code === 'heights'){
    // the measured rule, not the ground types: sea iff not greyscale, or black
    if(r === 0 && g === 0 && b === 0) return {name: 'Sea (pure black)', code: 'sea'};
    if(!(r === g && g === b)) return {name: 'Sea (not greyscale)', code: 'sea'};
    return {name: `Land, height ${r} of 255`, code: 'land'};
  }
  if(code === 'ground_types'){
    const e = hit(v.ground_types);
    return e ? {name: e.name, code: e.code} : {name: '', code: null};
  }
  if(code === 'features'){
    const e = hit(v.features);
    if(!e) return {name: '', code: null};
    return {name: e.code === 'none' ? 'Nothing here' : e.name, code: e.code};
  }
  if(code === 'climates'){
    const e = hit(v.climates);
    return e ? {name: e.name, code: e.code} : {name: '', code: null};
  }
  if(code === 'trade_routes')
    return k === 0 ? {name: 'No trade route', code: 'none'}
                   : {name: 'Trade route', code: 'route'};
  if(code === 'roughness'){
    if(!(r === g && g === b)) return {name: '', code: null};
    return r === 0 ? {name: 'Flat', code: 'flat'}
                   : {name: `Roughness ${r} of 255`, code: 'rough'};
  }
  if(code === 'fog'){
    if(r === 255 && g === 255 && b === 255) return {name: 'Unmarked', code: 'unmarked'};
    if(r === 0 && g === 0 && b === 0) return {name: 'Marked', code: 'marked'};
    return {name: '', code: null};
  }
  return {name: '', code: null};
}

/* One layer's pixel at one tile, or null.

   Layers are served at tile fit, so this is a 1x1 read at the tile's own
   coordinates - O(1) per layer, ten of them, which is what keeps rule 4. A
   layer that is not aligned to the grid has no value at a tile and says so
   rather than being sampled at coordinates that mean nothing in it. */
function cmapLayerRgb(code, tx, ty){
  const cv = cmapPixels(code);
  if(!cv || tx < 0 || ty < 0 || tx >= cv.width || ty >= cv.height) return null;
  const d = state.cmap.layers[code].px.getImageData(tx, ty, 1, 1).data;
  return [d[0], d[1], d[2]];
}

function cmapTipRow(ly, tx, ty){
  if(!ly.present || !ly.aligned){
    // A layer that is missing is the side panel's news, not the pointer's; a
    // layer that is present and the wrong shape is the classic map crash, and
    // it is worth saying where somebody is looking.
    if(!ly.present || !ly.problem) return '';
    return `<div class="cmtiprow"><i class="none"></i>
      <span class="cmtipk">${esc(ly.label)}</span>
      <span class="w-bad">${esc(ly.problem)}</span></div>`;
  }
  const rgb = cmapLayerRgb(ly.code, tx, ty);
  if(!rgb) return '';
  const n = cmapNameColour(ly.code, rgb);
  const val = n.code
    ? `${esc(n.name)}${n.code !== n.name ? ` <span class="count">(${esc(n.code)})</span>` : ''}`
    : `<span class="w-warn">no table names this colour</span>
       <span class="count">rgb(${rgb.join(', ')})</span>`;
  return `<div class="cmtiprow"><i style="background:rgb(${rgb.join(',')})"></i>
    <span class="cmtipk">${esc(ly.label)}</span>
    <span class="cmtipv">${val}</span></div>`;
}

/* The panel's contents. Region first, because it is what the map is about. */
function cmapTipHtml(tx, ty){
  const c = state.cmap, m = c.man;
  const gy = m.height - 1 - ty;
  const rgb = cmapLayerRgb('regions', tx, ty);
  const n = rgb ? cmapNameColour('regions', rgb) : null;
  let head = '';
  if(n && (n.code === 'settlement' || n.code === 'port')){
    // 17c again: the marker belongs to the region around it, and saying which
    // is the whole difference between a readout and an answer
    const own = cmapMarkerOwner(tx, ty);
    head = `<div class="cmtipn w-good">${esc(n.name)}</div>`
      + (own ? `<div class="count">${esc(own.region.settlement_name
                                        || own.region.name)} · ${esc(own.region.name)}</div>`
             : `<div class="w-warn">no region claims this marker</div>`);
  }else if(n && n.region && n.region.name){
    const r = n.region;
    head = `<div class="cmtipn">${esc(r.name)}
        ${r.id >= 0 ? `<span class="count">#${r.id}</span>` : ''}</div>`
      + (r.settlement_name ? `<div class="count">${esc(r.settlement_name)}${
          r.faction ? ` · ${esc(r.faction)}` : ''}</div>` : '');
  }else if(n){
    // the sea, or a colour descr_regions.txt never declares - which is a real
    // state both real maps are in, and the sentence cmapRegionName already owns
    head = `<div class="cmtipn count">${n.region ? cmapRegionName(n.region)
                                                 : 'no region'}</div>`;
  }
  const rows = m.layers.map(ly => cmapTipRow(ly, tx, ty)).join('');
  // 17d: what descr_strat.txt stands on this tile, when that layer is on. It is
  // above the layer rows because a general is what somebody is pointing AT and
  // the ground under him is context.
  const on = (typeof cmkAt === 'function') ? cmkAt(tx, ty) : [];
  const marks = on.length
    ? `<div class="cmtipmk">${on.slice(0, 6).map(it =>
        `<div>${esc(cmkLabel(it))}</div>`).join('')}${
        on.length > 6 ? `<div class="count">…and ${on.length - 6} more</div>` : ''}</div>`
    : '';
  return `${head}
    <div class="cmtipxy"><b>${tx}, ${ty}</b> image · <b>${tx}, ${gy}</b> game</div>
    ${marks}${rows}`;
}

/* The layers the panel needs, which are not the layers on screen.

   Naming every layer means holding every layer, and only the ticked ones are
   fetched - so the first hover asks for the rest, once, and never again. They
   are not ticked by asking: `cmapCompose` draws what `on` says, and these
   arrive with it false, so the picture does not change. Each is one PNG the
   server already has on disk, keyed by the file's mtime.

   A layer that will not load is not retried here and not complained about
   twice: `cmapFetchLayer` has already put the server's own sentence on the
   layer row in the side panel, and the tooltip just has one row fewer. */
function cmapTipLoad(){
  const c = state.cmap;
  if(!c || c.tipLoad) return;
  const want = Object.keys(c.layers).filter(code => {
    const L = c.layers[code];
    return L.def.present && L.def.aligned && !L.img && !L.loading && !L.failed;
  });
  if(!want.length){ c.tipLoad = !Object.values(c.layers).some(L => L.loading); return; }
  c.tipLoad = true;
  Promise.all(want.map(code => cmapFetchLayer(c, code))).then(() => {
    if(state.cmap !== c) return;
    c.saidTip = ''; c.tipKey = '';   // the panel can say more now than it could
    cmapTipPaint();
  });
}

/* Draw it, and put it where it can be read.

   Beside the cursor, flipped to the other side when it would run off the stage,
   so the panel never leaves the window and never sits under the pointer. The
   HTML is rebuilt only when it changed, for the same reason the corner readout
   is: writing into the DOM forces a style recalculation whether the text is
   different or not, and this runs per pointer event. */
function cmapTipPaint(){
  const c = state.cmap, el = document.getElementById('cmTip');
  if(!el || !c) return;
  if(!c.hover || !c.ptr || c.tip === false || c.tipHold){
    if(!el.hidden){ el.hidden = true; c.saidTip = ''; }
    return;
  }
  cmapTipLoad();
  /* The panel is about a TILE and it follows a POINTER, and at any zoom over
     1:1 most pointer events are still inside the tile the last one was in. So
     the contents are worked out when the tile changes and only the two edge
     offsets below are written when it does not: 0.65 ms against 0.17 ms,
     measured on Third Age Reforged with all eight aligned layers named. */
  const tile = `${c.hover[0]},${c.hover[1]}`;
  if(c.tipKey !== tile){
    const html = cmapTipHtml(c.hover[0], c.hover[1]);
    if(c.saidTip !== html){ el.innerHTML = html; c.saidTip = html; }
    c.tipKey = tile;
  }
  if(el.hidden) el.hidden = false;
  /* Which side of the cursor, decided from the pointer and the stage rather
     than from the panel's own width. Asking the panel how big it is means
     reading `offsetWidth` right after writing its HTML, which forces a layout
     per pointer event - so the panel is anchored by whichever two edges are
     furthest from the cursor and CSS lays it out afterwards. It also means the
     panel cannot leave the stage however long a province name is. */
  const [px, py] = c.ptr;
  const W = c.stageW || 0, H = c.stageH || 0;
  if(W && px > W * 0.55){ el.style.left = 'auto'; el.style.right = `${Math.round(W - px + 18)}px`; }
  else { el.style.right = 'auto'; el.style.left = `${Math.round(px + 18)}px`; }
  if(H && py > H * 0.6){ el.style.top = 'auto'; el.style.bottom = `${Math.round(H - py + 14)}px`; }
  else { el.style.bottom = 'auto'; el.style.top = `${Math.round(py + 14)}px`; }
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

/* One layer's pixels as a canvas the browser can read AND write.

   16c kept one of these for the region layer alone and called it `scratch`,
   because the hover readout needs a colour per pointer event and a round trip
   there is the exact thing this screen's rules exist to prevent. 16e paints, so
   any layer can need one - and once a layer has been painted, this canvas
   rather than its <img> is the truth about it. So everything that reads or
   draws a layer goes through here: there is one copy per layer, and never two
   that can disagree.

   Layers are served at tile fit, so one pixel here is one tile, which is the
   coordinate system every stroke and every answer from the server is in. */
function cmapPixels(code){
  const c = state.cmap, L = c && c.layers[code];
  if(!L || !L.img) return null;
  if(!L.cv){
    L.cv = document.createElement('canvas');
    L.cv.width = L.img.naturalWidth || L.img.width;
    L.cv.height = L.img.naturalHeight || L.img.height;
    L.px = L.cv.getContext('2d', {willReadFrequently: true});
    L.px.imageSmoothingEnabled = false;
    L.px.drawImage(L.img, 0, 0);
  }
  return L.cv;
}

/* The region a settlement or port marker belongs to, from the manifest.

   Built once and kept: 200 regions is 265 markers on this map, and a Map keyed
   by the tile answers a click in one lookup. `null` is a real answer - a marker
   the read could not pair with a region is exactly what `findings.orphan_
   settlements` and `extra_settlements` are about, and 17c's rule is that a dead
   click says why rather than doing nothing. */
function cmapMarkerOwner(tx, ty){
  const c = state.cmap;
  if(!c.markerAt){
    c.markerAt = new Map();
    for(const r of c.man.regions){
      if(r.settlement) c.markerAt.set(r.settlement.join(','), {region: r, kind: 'settlement'});
      if(r.port) c.markerAt.set(r.port.join(','), {region: r, kind: 'port'});
    }
  }
  return c.markerAt.get(`${tx},${ty}`) || null;
}

function cmapRegionAt(tx, ty){
  const c = state.cmap;
  if(tx < 0 || ty < 0 || tx >= c.man.width || ty >= c.man.height) return null;
  if(!cmapPixels('regions')) return null;
  const d = c.layers.regions.px.getImageData(tx, ty, 1, 1).data;
  const k = (d[0] << 16) | (d[1] << 8) | d[2];
  const mk = c.man.markers;
  if(k === ((mk.settlement[0] << 16) | (mk.settlement[1] << 8) | mk.settlement[2]))
    return 'settlement';
  if(k === ((mk.port[0] << 16) | (mk.port[1] << 8) | mk.port[2])) return 'port';
  return c.byKey.get(k) || null;
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
  const W = c.man.width, H = c.man.height;
  if(!cmapPixels('regions')){ c.outline = null; return; }
  const src = c.layers.regions.px.getImageData(0, 0, W, H).data;
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

/* ---------- the legend ---------- */

/* One layer's colours, named. Fetched once per layer, on the disclosure.

   16c composited every layer honestly and that is what made two of them
   useless: `map_features.tga` is 97.7% black on DaC, black there means "nothing
   here", and ticking the layer at full opacity therefore hid the map under a
   black sheet with a few rivers on it. The fix is not a blend mode - it is
   knowing what the colours MEAN, which is the server's to say, because the
   vocabularies and the mod's own descr_climates.txt live there. */
async function cmapLegend(code){
  const c = state.cmap, L = c.layers[code];
  if(L.legend || L.legendBusy) return;
  L.legendBusy = true; L.legendErr = '';
  cmapRepanel();
  let r;
  try{ r = await api.get(`/api/map/legend?mod=${enc(c.mod)}&code=${enc(code)}`); }
  catch(e){ r = null; L.legendErr = errText(e); }
  if(state.cmap !== c) return;
  L.legendBusy = false;
  if(r) L.legend = r;
  cmapRepanel();
}

function cmapLegendHtml(code){
  const L = state.cmap.layers[code];
  if(L.legendBusy) return `<div class="cmleg"><span class="count">reading the layer…</span></div>`;
  if(L.legendErr) return `<div class="cmleg"><span class="w-bad">${esc(L.legendErr)}</span></div>`;
  const g = L.legend;
  if(!g) return '';
  // 20a: the river overlay is a whitelist and it supersedes the hide set, so
  // these say so rather than silently doing nothing while it is on
  const whitelisted = code === 'features' && state.cmap.rivers;
  const rows = g.colours.map(k => {
    const pct = g.total ? (k.count * 100 / g.total) : 0;
    // the localised name first and the code name in brackets, which is the
    // shape every other picker in this toolkit uses - and an empty code name
    // is a colour no table knows, said as that rather than rounded to a guess
    const nm = k.code_name
      ? `${esc(k.name)} <span class="count">(${esc(k.code_name)})</span>`
      : `<span class="w-warn">no table names this colour</span>`;
    return `<div class="cmlegrow${L.hide.has(k.key) ? ' hid' : ''}">
      <label class="chk" title="${whitelisted
        ? 'Rivers only is on, and it draws the three river colours and nothing else'
        : 'Stop drawing this colour, so what is under it shows through'}">
        <input type="checkbox" data-lhide="${code}" data-key="${k.key}"
          ${whitelisted ? 'disabled' : ''}
          ${L.hide.has(k.key) ? 'checked' : ''}></label>
      <i style="background:rgb(${k.rgb.join(',')})"></i>
      <span class="cmlegnm">${nm}</span>
      <span class="count">${k.count.toLocaleString()} ·
        ${pct >= 0.1 ? pct.toFixed(1) : '<0.1'}%</span>
    </div>`;
  }).join('');
  const b = g.blank;
  return `<div class="cmleg">
    ${whitelisted ? `<div class="count"><b>Rivers only</b> is on: the three river
      colours are drawn in one colour of yours and every other colour on this
      layer is punched through, so these tickboxes decide nothing until it is
      off.</div>` : ''}
    ${b ? `<div class="count">Hiding <b style="color:rgb(${b.rgb.join(',')})">
      rgb(${b.rgb.join(', ')})</b> makes this an overlay: it means ${esc(b.why)}.
      ${b.sourced ? '' : 'Measured on both real maps rather than stated by any reference.'}
      </div>` : ''}
    ${rows || '<span class="count">nothing to list</span>'}
    ${g.note ? `<div class="count">${esc(g.note)}</div>` : ''}
  </div>`;
}

/* Which packed colours are a river, off the manifest's own vocabulary.

   20a, D8. `mapvocab.RIVER_CODES` says which feature codes make up a river
   network and `_vocab_view` sends both the codes and the table out with the
   manifest, so the three colours are looked up here rather than written down a
   second time. mapcheck's four-connected river graph walks exactly these, which
   is the point: the overlay draws the tiles the validator complains about. */
function cmapRiverKeys(){
  const v = (state.cmap.man && state.cmap.man.vocab) || {};
  const want = new Set(v.rivers || []);
  const out = new Set();
  for(const f of v.features || [])
    if(want.has(f.code) && f.rgb)
      out.add((f.rgb[0] << 16) | (f.rgb[1] << 8) | f.rgb[2]);
  return out;
}

/* Grey level -> alpha for the heights layer, over the heights THIS map has.

   20a, T2. TWMapReader's rule is "darker means more transparent", and taken
   literally - alpha = the grey itself - it does not work on a real map. Land on
   both installed mods runs 1 to 255 but is nowhere near evenly spread: the
   median land tile is 32 of 255 on Divide and Conquer and 31 on Third Age
   Reforged, and a quarter of the land is under 19. A linear ramp draws half the
   continent at under 13% alpha, which is a layer you have ticked and cannot
   see.

   So the ramp is the land's own distribution: a tile's alpha is how much of the
   land is no higher than it. Darker is still more transparent - the mapping is
   monotonic, so no two heights swap places - but the ramp is spread over the
   heights the map actually contains rather than over a 0-255 nothing uses the
   top of. The panel says this in a sentence, because a ramp that is not the
   obvious one has to be readable off the screen.

   Sea is not on the ramp at all. `mapvocab.is_sea_height`'s measured rule - sea
   iff the pixel is not greyscale, or is black - is the same one `cmapNameColour`
   mirrors, and sea has no height to be a depth of.

   Comes back with the map's own median land height beside the ramp, because the
   panel has to be able to say what the ramp is spread over and the histogram is
   already in hand. The two installed mods happen to agree at 32 and 31; that is
   not a reason to print either of them over somebody else's map.

   One pass to count and one to write, both inside the mask pass's own budget.
   Cached on the layer and thrown away with the mask whenever the pixels move. */
function cmapHeightRamp(img){
  const w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const x = cv.getContext('2d', {willReadFrequently: true});
  x.imageSmoothingEnabled = false;
  x.drawImage(img, 0, 0);
  const d = x.getImageData(0, 0, w, h).data;
  const hist = new Float64Array(256);
  let land = 0;
  for(let i = 0, n = w * h; i < n; i++){
    const p = i * 4, r = d[p];
    if(r === 0 || r !== d[p + 1] || d[p + 1] !== d[p + 2]) continue;   // sea
    hist[r]++; land++;
  }
  const alpha = new Uint8Array(256);
  if(!land) return {alpha, median: 0, land: 0};
  // the midpoint of its own band, so the lowest land is not invisible and the
  // highest is not the only thing that is solid
  let below = 0, median = 0;
  for(let v = 1; v < 256; v++){
    alpha[v] = Math.round(255 * (below + hist[v] / 2) / land);
    below += hist[v];
    if(!median && below * 2 >= land) median = v;
  }
  return {alpha, median, land};
}

//: Everything about a layer that changes its pixels rather than where they are
//: drawn. Empty means the layer is drawn as it arrived and no copy is needed.
function cmapModeKey(c, code){
  const L = c.layers[code];
  const bits = [...L.hide].sort().join('.');
  const riv = (code === 'features' && c.rivers) ? `riv:${c.riverRgb.join(',')}` : '';
  const alp = (code === 'heights' && c.heightAlpha) ? 'alpha' : '';
  return [bits, riv, alp].filter(Boolean).join('|');
}

/* A layer picture with its colours punched out, lifted out, or turned into
   transparency.

   One pass over at most a megapixel, on the tick that changes what the pass
   does, cached by that. Never per frame, never per pointer event: rule 4 of
   this phase holds, and 20a added two more reasons to run it without adding
   one to run it more often.

   Three transforms, and the order they are in is the order they mean:

     the river overlay   a whitelist. Every colour that is not one of the three
                         river colours goes, and the three that stay become one
                         colour - which is D8's whole point, because those three
                         inside a layer that is 97.7% black are not a picture of
                         a river system. It supersedes the hide set rather than
                         combining with it, and the legend says so by disabling
                         those tickboxes while it is on.
     the hide set        16d's, unchanged: named colours stop being drawn.
     height as alpha     T2's, and it is not a colour transform at all - the
                         grey stays and the alpha is read off the ramp. */
function cmapMask(c, code){
  const L = c.layers[code];
  const want = cmapModeKey(c, code);
  if(!L.img || !want){ L.masked = null; L.maskKey = ''; L.rivertiles = 0; return; }
  if(L.masked && L.maskKey === want) return;
  const w = L.img.naturalWidth || L.img.width, h = L.img.naturalHeight || L.img.height;
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const x = cv.getContext('2d', {willReadFrequently: true});
  x.imageSmoothingEnabled = false;
  // from the painted copy when there is one - a hidden colour has to be punched
  // out of the layer as it is NOW, not as it arrived
  x.drawImage(L.cv || L.img, 0, 0);
  const im = x.getImageData(0, 0, w, h), d = im.data;
  const riv = (code === 'features' && c.rivers) ? cmapRiverKeys() : null;
  const rgb = c.riverRgb;
  const ramp = (code === 'heights' && c.heightAlpha)
    ? (L.ramp || (L.ramp = cmapHeightRamp(L.cv || L.img))) : null;
  let drawn = 0;
  for(let i = 0, n = w * h; i < n; i++){
    const p = i * 4, r = d[p], g = d[p + 1], b = d[p + 2];
    if(riv){
      if(riv.has((r << 16) | (g << 8) | b)){
        d[p] = rgb[0]; d[p + 1] = rgb[1]; d[p + 2] = rgb[2];
        drawn++;
      }else d[p + 3] = 0;
      continue;
    }
    if(L.hide.has((r << 16) | (g << 8) | b)){ d[p + 3] = 0; continue; }
    // sea has no height, and the ramp's own zero is the rest of the rule
    if(ramp) d[p + 3] = (r === g && g === b) ? ramp.alpha[r] : 0;
  }
  x.putImageData(im, 0, 0);
  L.masked = cv; L.maskKey = want; L.rivertiles = drawn;
}

/* The layers whose pixels just changed, put back on screen.

   Called by the paint tool after it has written the server's answer into
   `cmapPixels`. Three things are stale after that and all three are named here
   rather than left to a cache key that cannot see pixels: the punched-through
   copy of a layer whose hidden colours may now cover different tiles, the
   composite (whose key is the layer SET, which has not changed), and the
   selected region's outline when it was the region layer that moved. */
function cmapAfterPaint(codes){
  const c = state.cmap;
  if(!c) return;
  for(const code of codes){
    const L = c.layers[code];
    if(!L) continue;
    // 20a: the height ramp is a count of the pixels, so a stroke on the heights
    // layer invalidates it exactly as it invalidates the mask
    L.maskKey = ''; L.ramp = null;
    cmapMask(c, code);
  }
  c.compKey = '';
  if(codes.indexOf('regions') >= 0){
    c.outline = null; c.outlineKey = -1;
    // A colouring is a recolour of THIS layer, so a stroke on it makes the one
    // on screen a picture of pixels that have moved. It is dropped rather than
    // rebuilt: rebuilding would need the table for a province the server has
    // not been told about yet, and a stale theme is worse than none.
    if(c.overlay){ c.overlay = null; c.overlayKey = ''; }
  }
  cmapCompose();
  cmapPaint();
}

function cmapHideColour(code, key, on){
  const c = state.cmap, L = c.layers[code];
  if(on) L.hide.add(key); else L.hide.delete(key);
  cmapMask(c, code);
  cmapCompose(); cmapPaint(); cmapSaveLayers();
  cmapRepanel();
}

/* ---------- the picked tile ---------- */

/* A pick is two questions and they have two different answers.

   "What is this tile?" is every layer at once, and only Python can name the
   colours - the ground and feature tables are the arbiter's, and the climate
   names come out of this mod's own descr_climates.txt, because DaC renames all
   twelve. "What is this region?" is a record in descr_regions.txt plus what the
   pixels say about it, and it is editable.

   Both are one small request on a CLICK. The hover readout stays where 16c put
   it - answered in the browser off the region layer it already has - because
   that one runs per pointer event and a round trip there would be the exact
   thing this phase's rules exist to prevent. */
async function cmapPick(tile){
  const c = state.cmap;
  const [tx, ty] = tile;
  const hit = cmapRegionAt(tx, ty);
  let r = (hit && typeof hit === 'object') ? hit : null;
  /* 17c - the settlement is the thing people click on, and it was the one tile
     that answered nothing.

     A settlement pixel is black and a port pixel is white, neither is a region
     colour, and both are excluded from the region-id scan - so the colour under
     the pointer named no region and the panel said "no region record on this
     tile" while the pointer was on Nottingham. Measured on Third Age Reforged:
     199 of its 200 settlements and all 65 ports behaved that way, which is most
     of "not every region is clickable".

     The marker belongs to whatever region surrounds it and the manifest already
     says which - `descr_regions.txt` names the settlement, and the read paired
     it with the pixel. This is the same hole `mapquery` had to close for a
     resource standing on a marker, closed the same way. */
  c.marker = '';
  if(!r && (hit === 'settlement' || hit === 'port')){
    const own = cmapMarkerOwner(tx, ty);
    if(own){ r = own.region; c.marker = own.kind; }
    else c.marker = `${hit}-orphan`;
  }
  c.sel = r;
  c.pick = (tx >= 0 && ty >= 0 && tx < c.man.width && ty < c.man.height) ? [tx, ty] : null;
  c.probe = null; c.probeErr = '';
  activity('map pick', `${c.mod} ${tx},${ty} -> ${r ? r.name || 'undeclared' : hit || 'nothing'}`
    + (c.marker ? ` (on the ${c.marker} marker)` : ''));
  cmapOutline(r);
  cmapPaint();
  cmapPickPaint();
  if(!c.pick) return;
  const want = c.pick.join(',');
  cmapProbe(c, tx, ty, want);
  // A region with no record has nothing to edit, and saying so is better than
  // an empty form: the ocean is the usual case, and a colour nobody declared is
  // the interesting one - both are named by cmapRegionName.
  if(r && r.name){ cmapOpenRegion(r.name); csOpen(r.name); cmapOpenPeople(r.name); }
  else { c.det = null; c.cv = null; state.cset = null; state.cx = null;
         cmapPickPaint(); csPaint(); cxPaint(); }
}

async function cmapProbe(c, tx, ty, want){
  let p;
  try{ p = await api.get(`/api/map/probe?mod=${enc(c.mod)}&x=${tx}&y=${ty}`); }
  catch(e){ if(state.cmap === c && c.pick && c.pick.join(',') === want){
    c.probeErr = errText(e); cmapPickPaint(); } return; }
  if(state.cmap !== c || !c.pick || c.pick.join(',') !== want) return;
  c.probe = p;
  cmapPickPaint();
}

/* Whose people to show beside a province: the faction that starts holding it.

   16i's panel is about a faction rather than about a tile, and the map has no
   other way to name one - so picking a province opens the people of whoever
   owns it, which is what somebody clicking on Nottingham to find its garrison
   is asking for. A province nobody holds leaves the panel where it was rather
   than emptying it, because that is a click on the sea, not a decision. */
async function cmapOpenPeople(region){
  const c = state.cmap;
  let owner = '';
  try{
    const d = await api.get(`/api/map/settlement?mod=${enc(c.mod)}`
      + `&region=${enc(region)}${cmapCampQ()}`);
    owner = d.owner || '';
  }catch(e){ return; }
  if(state.cmap !== c || !owner) return;
  cxOpen(owner);
}

/* One region's record, its pixels and the pickers its boxes need.

   `w` is the working copy every box edits and every save is built from - the
   same shape the traits, ancillaries, factions and minor-file editors use, and
   the shape Ctrl+Z snapshots (see UNDO_SCOPES). The values beside it are what
   came off disk, so whether anything has changed is a comparison rather than a
   flag somebody has to remember to set. */
async function cmapOpenRegion(name){
  const c = state.cmap;
  if(c.det && c.det.name === name && !c.det.error) return;
  c.det = {name, loading: true};
  c.cv = null;
  cmapPickPaint();
  let d;
  try{ d = await api.get(`/api/map/region?mod=${enc(c.mod)}&name=${enc(name)}`
    + cmapCampQ()); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cmap !== c || !c.det || c.det.name !== name) return;
  c.det = d.error ? {name, error: d.error} : Object.assign({name}, d, {
    w: {legion: d.legion, faction: d.faction, rebels: d.rebels,
        resources: d.resources.slice(), triumph: d.triumph, farming: d.farming,
        religions: Object.assign({}, d.religions)},
    raw: '',
  });
  cmapPickPaint();
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
}

//: Everything below the layer stack: what the tile is, and what the region is.
//: The canvas is deliberately not in it - rebuilding that markup would throw
//: away the <canvas> and its 2d context with it.
function cmapPickPaint(){
  const el = document.getElementById('cmPick');
  if(!el) return;
  el.innerHTML = cmapProbeHtml() + cmapRegionHtml();
  const c = state.cmap;
  const side = document.getElementById('cmSide');
  if(side) side.classList.toggle('wide', !!(c.det && c.det.cv));
  if(c.det && c.det.cv){
    cvWire(c.det.cv);
    cvBindHover(c.det.cv, document.getElementById('cmGui'));
  }
}

//: The form only, never the pane - the caret is in the pane.
function cmapRegionPaint(){
  const el = document.getElementById('cmGui');
  if(!el) return;
  el.innerHTML = cmapFormHtml();
  const d = state.cmap.det;
  if(d && d.cv) cvBindHover(d.cv, el);
}

function cmapProbeHtml(){
  const c = state.cmap;
  if(!c.pick) return `<div class="k">This tile</div>
    <div class="count">Click the map to name a tile on every layer at once.</div>`;
  const [tx, ty] = c.pick;
  const head = `<div class="k">This tile
    <span class="count">${tx}, ${ty} image · ${tx}, ${c.man.height - 1 - ty} game</span></div>`;
  if(c.probeErr) return head + `<div class="w-bad">${esc(c.probeErr)}</div>`;
  if(!c.probe) return head + `<div class="count">reading the ten layers…</div>`;
  const p = c.probe;
  const rows = p.layers.map(L => {
    const val = L.problem
      ? `<span class="count">${esc(L.problem)}</span>`
      : L.code_name
        ? `${esc(L.name)} <span class="count">(${esc(L.code_name)})</span>`
        : `<span class="w-warn">${esc(L.name) || 'no table names this colour'}</span>`;
    // one line per layer, and it has to READ as one line at 336px: the label,
    // the value and the raw triple in that order, wrapping rather than each
    // fighting the others for a column of its own
    return `<div class="cmtrow">
      <i style="background:${L.rgb ? `rgb(${L.rgb.join(',')})` : 'transparent'}"></i>
      <span class="cmtval"><span class="cmtnm">${esc(L.label)}</span> ${val}${
        L.rgb ? ` <span class="count">· ${L.rgb.join(', ')}</span>` : ''}</span>
    </div>`;
  }).join('');
  const marker = p.marker
    ? `<div class="w-good">This is the ${esc(p.marker)} marker pixel. It belongs to
       whichever region surrounds it, and it is skipped when the engine numbers
       regions.</div>` : '';
  return head + marker + `<div class="cmprobe">${rows}</div>
    <div class="count">The engine treats this tile as
    <b>${p.sea === null ? 'unknown' : p.sea ? 'sea' : 'land'}</b> - from map_heights, not
    from the ground type, with river crossings excluded.</div>`;
}

/* ---------- the region, editable ---------- */

function cmapRegionHtml(){
  const c = state.cmap, d = c.det;
  if(!c.pick) return '';
  if(!d){
    // 17c: a click that opens no form says which of the three reasons it is,
    // rather than the one sentence that used to cover all of them.
    if(c.marker && c.marker.endsWith('-orphan')){
      const kind = c.marker.split('-')[0];
      return `<div class="k">This region</div>
        <div class="w-warn">This is a ${esc(kind)} marker pixel and no region in
        <code>descr_regions.txt</code> claims it. The read calls that an orphan
        ${esc(kind)}; Check lists them.</div>`;
    }
    return `<div class="k">This region</div>
      <div class="count">${c.sel ? esc(cmapRegionName(c.sel)).replace(/<[^>]+>/g, '')
        : 'No region record on this tile'} - nothing in
      <code>descr_regions.txt</code> to edit.</div>`;
  }
  if(d.loading) return `<div class="k">This region</div>
    <div class="count">reading ${esc(d.name)}…</div>`;
  if(d.error) return `<div class="k">This region</div>
    <div class="w-bad">${esc(d.error)}</div>`;
  return `<div class="cmbar2">
      <div><b>${esc(d.shown || d.name)}</b>
        <span class="count">${esc(d.file)}, lines ${d.lines[0]}-${d.lines[1]}</span></div>
      <span class="sp"></span>
      <button class="${d.cv ? 'on' : ''}" onclick="cmapCvToggle()"
        title="Show this region exactly as descr_regions.txt stores it, beside the form."
        >&lt;/&gt; Code view</button>
      <button class="primary" onclick="cmapSave()">Save</button>
    </div>
    <div id="cmGui">${cmapFormHtml()}</div>
    ${d.cv ? `<div id="cmCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}`;
}

//: The three fields nobody may retype here, and why. Said on the form rather
//: than only when a save is refused, because a box you cannot use should look
//: like one before you have typed into it.
/* 19b corrected the settlement sentence. It used to say descr_strat.txt points
   at a settlement's name, and measured over both installed mods it does not: a
   settlement block carries `region <province>` and never names itself. Every
   whole-word hit in either mod's descr_strat.txt is a unit type, a portrait or
   a comment. */
const CMAP_LOCKED = {
  name: 'Descr_strat.txt, the win conditions, the mercenary pools, the campaign '
      + 'script and every legion: line point at this name. Rename follows all of '
      + 'them and reports the script',
  settlement: 'Its province’s record, the lookup file and the settlement name '
      + 'text file point at this name, and so does the campaign script. Rename '
      + 'follows the three files and reports the script',
  rgb: 'This is the colour the region is painted on map_regions.tga. Changing '
     + 'the number without repainting the pixels would leave the region with no '
     + 'tiles at all. Arm the brush above and repaint them instead',
};

/* ---- renaming the province or its settlement (19b, D2) ----

   The box stays read-only and the rename is its own dialog, because it is its
   own save: it rewrites files this panel has never opened - the win conditions,
   the mercenary pools, the music types, a second campaign's descr_strat - and it
   is one backup set over all of them rather than a field on this form.

   Afterwards the panel re-opens under the NEW name: the record it was showing
   does not exist any more, so repainting the old one would find nothing. */
function cmapRename(subject){
  const c = state.cmap, d = c.det;
  if(!d || c.busy) return;
  const was = d.name;
  renameOpen(c.mod, subject, subject === 'region' ? d.name : d.settlement,
             async (name) => { c.det = null;
                               await cmapOpenRegion(subject === 'region' ? name : was); });
}

function cmapFormHtml(){
  const d = state.cmap.det, w = d.w, v = d.vocab;
  //: `rename` is the subject the rename dialog opens on, for the two fields a
  //: rename can follow. The colour is not one of them: it is pixels, not a name.
  const lock = (label, value, why, extra, rename) => `<div class="cmfield">
    <label>${esc(label)} <span class="cmlock" title="${esc(why)}">locked</span>
      ${rename ? `<button class="cmrename" title="${esc(why)}"
        onclick="cmapRename('${esc(rename)}')">Rename…</button>` : ''}</label>
    <input value="${esc(value)}" readonly>
    ${extra ? `<div class="count">${extra}</div>` : ''}</div>`;
  const pick = (label, slot, list, labels) => `<div class="cmfield">
    <label>${esc(label)}</label>
    <input list="cml-${slot}" value="${esc(w[slot] || '')}"
      oninput="cmapSet('${slot}', this.value)">
    <datalist id="cml-${slot}">${(list || []).map(x =>
      `<option value="${esc(x)}">${esc((labels && labels[x]) || '')}</option>`).join('')}
    </datalist></div>`;
  const total = cmapReligionTotal();
  const px = d.pixels;
  return cmapFindingsHtml2() + `
    <div class="cmform">
      ${lock('Region name', d.name, CMAP_LOCKED.name,
             d.shown ? `shown in game as <b>${esc(d.shown)}</b>`
                     : '<span class="w-warn">no line in the names file - the '
                       + 'player reads this key</span>', 'region')}
      ${d.has.settlement ? lock('Settlement', d.settlement, CMAP_LOCKED.settlement,
             d.settlement_shown ? `shown in game as <b>${esc(d.settlement_shown)}</b>`
                                : '<span class="w-warn">no line in the names file'
                                  + '</span>', 'settlement')
        : `<div class="count">This is the short wasteland form: no settlement, no
           creator and no rebel type. The arbiter says such a province must be the
           last entry in the file.</div>`}
      ${lock('Colour', d.rgb.join(' '), CMAP_LOCKED.rgb,
             `<i class="cmsw" style="background:rgb(${d.rgb.join(',')})"></i>
              region ID ${px && px.region_id >= 0 ? px.region_id : '-'}`)}
      ${pick('Legion', 'legion', [d.name])}
      ${d.has.faction ? pick('Creator faction', 'faction', v.factions, v.faction_labels) : ''}
      ${d.has.rebels ? pick('Rebel type', 'rebels', v.rebels) : ''}
      ${d.has.resources || !d.wasteland ? cmapResourceHtml() : ''}
      ${d.has.triumph ? `<div class="cmfield"><label>Triumph value</label>
        <input type="number" value="${w.triumph}" min="0" max="20"
          oninput="cmapSet('triumph', this.value)">
        <div class="count">Geomod's manual: leave it at 5, other numbers may cause
        a crash.</div></div>` : ''}
      ${d.has.farming ? `<div class="cmfield"><label>Base farming level</label>
        <input type="number" value="${w.farming}" min="0" max="7"
          oninput="cmapSet('farming', this.value)">
        <div class="count">4 is about average, 6-7 highly fertile.</div></div>` : ''}
    </div>
    ${cmapNamesHtml()}
    ${cmapMercHtml()}
    ${d.has.religions ? `<div class="k">Religions
      <span class="${total === 100 ? 'count' : 'w-bad'}">total ${total}${
        total === 100 ? '' : ` - the game crashes on load unless this is 100 (${
        total > 100 ? '+' : ''}${total - 100})`}</span></div>
      <div class="cmrels">${cmapReligionRows()}</div>` : ''}
    ${cmapPixelHtml()}`;
}

/* ---- the words the player reads (19a, D4) ----

   `imperial_campaign_regions_and_settlement_names.txt` keys a province and its
   settlement by their own code names. 16f has reported a missing key since it
   was written and nothing in the toolkit could write one, which is a fault the
   new-region wizard was creating and then complaining about.

   Its own save, for 17f's reason and the mercenary pool's: a third file, a
   third undo entry, each naming what it put back. The region record is not
   touched by this button and this button does not touch the region record. */
function cmapNamesHtml(){
  const d = state.cmap.det, n = d.names;
  if(!n) return '';
  if(!n.have) return `<div class="k">Names the player reads
    <span class="count">${esc(n.problem || 'no names file')}</span></div>`;
  const pick = d.namePick || {};
  const rows = (n.rows || []).map(r => {
    const now = pick[r.slot] === undefined ? r.value : pick[r.slot];
    return `<div class="cmfield">
      <label>${r.slot === 'region' ? 'Province' : 'Settlement'}
        <span class="count">{${esc(r.key)}}</span></label>
      <input value="${esc(now)}" placeholder="${esc(r.key)}"
        oninput="cmapNameSet('${esc(r.slot)}', this.value)">
      ${r.set ? '' : '<div class="w-warn">no line in this file yet</div>'}</div>`;
  }).join('');
  const dirty = (n.rows || []).some(r =>
    pick[r.slot] !== undefined && pick[r.slot] !== r.value);
  return `<div class="k">Names the player reads
      <span class="count">${esc(n.file)}, ${n.keys} key${
        n.keys === 1 ? '' : 's'}</span></div>
    <div class="cmform">${rows}
      <div class="count">${dirty
        ? 'Not saved yet - ' + esc(n.file) + ' is a third file, so it is a third '
          + 'save and a third undo. The compiled .strings.bin beside it is '
          + 'rebuilt, because that is the one the game reads.'
        : 'Blank here and the campaign map shows the code name instead.'}</div>
      ${dirty ? `<button class="primary" style="margin-top:6px"
        onclick="cmapNamesSave()">Save names</button>` : ''}
    </div>`;
}

function cmapNameSet(slot, value){
  const d = state.cmap.det;
  if(!d) return;
  d.namePick = Object.assign({}, d.namePick || {}, {[slot]: value});
  cmapRegionPaint();
}

async function cmapNamesSave(){
  const c = state.cmap, d = c.det;
  if(!d || c.busy || !d.namePick) return;
  const edits = {};
  for(const r of (d.names.rows || []))
    if(d.namePick[r.slot] !== undefined && d.namePick[r.slot] !== r.value)
      edits[r.slot] = d.namePick[r.slot];
  if(!Object.keys(edits).length) return;
  const body = {mod: c.mod, what: 'region_names', region: d.name, edits};
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/namekeys/plan', body); }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write: ${(p.changes || []).join('\n') || 'no visible change'}?\n\n`
    + ((p.warnings || []).length ? (p.warnings || []).slice(0, 3).join('\n') + '\n\n' : '')
    + `${(p.files || []).join(', ')} only - the region record is not touched.\n\n`
    + 'Backed up first, and 🕑 Log can undo it.')) return;
  c.busy = true;
  let res;
  try{ res = await api.post('/api/namekeys/apply', body); }
  finally{ c.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Names saved, and the compiled archive rebuilt. 🕑 Log can undo it.');
  const name = d.name;
  c.det = null;
  await cmapOpenRegion(name);
}

/* ---- the province's mercenary pool (18a, G3) ----

   `descr_mercenaries.txt` groups provinces into pools and sells a different
   roster in each. 16b read it and the picker has been deferred ever since.

   It saves on its own rather than riding on the region save, and that is 17f's
   ruling rather than a shortcut: this is one screen over two files, and the
   pool is not a field of the region record - it is a word on a `regions` line
   in another file, in the campaign folder. Two files, two saves, two undo
   entries, each naming the file it put back.

   Measured across both installed mods: 84 pools over 341 provinces, and not one
   province is in two pools. That is what lets this be a single choice rather
   than a set of tick boxes. */
function cmapMercHtml(){
  const d = state.cmap.det, m = d.mercenaries;
  if(!m) return '';
  if(!m.have) return `<div class="k">Mercenaries
    <span class="count">${esc(m.problem || 'no pool file')}</span></div>`;
  const now = d.mercPick === undefined ? m.pool : d.mercPick;
  const dirty = now !== m.pool;
  return `<div class="k">Mercenaries
      <span class="count">which pool this province hires from</span></div>
    <div class="cmform">
      <div class="cmfield">
        <label>Pool</label>
        <select onchange="cmapMercSet(this.value)">
          <option value="" ${now ? '' : 'selected'}>(none - nothing is hired here)</option>
          ${(m.pools || []).map(p => `<option value="${esc(p.name)}"
            ${p.name === now ? 'selected' : ''}>${esc(p.name)} · ${p.regions} province${
              p.regions === 1 ? '' : 's'}, ${p.units} unit${
              p.units === 1 ? '' : 's'}</option>`).join('')}
        </select>
        <div class="count">${m.units && m.units.length && !dirty
          ? 'Sells ' + m.units.map(esc).join(', ')
          : dirty ? 'Not saved yet - ' + esc(m.file) + ' is a second file, so it is '
                    + 'a second save and a second undo'
          : 'This province is in no pool, so no mercenary is ever recruitable here'}</div>
        ${dirty ? `<button class="primary" style="margin-top:6px"
          onclick="cmapMercSave()">Save mercenary pool</button>` : ''}
      </div>
    </div>`;
}

function cmapMercSet(value){
  const d = state.cmap.det;
  if(!d) return;
  d.mercPick = value;
  cmapRegionPaint();
}

async function cmapMercSave(){
  const c = state.cmap, d = c.det;
  if(!d || c.busy || d.mercPick === undefined) return;
  const body = {mod:c.mod, what:'mercenaries', campaign:d.campaign,
                name:d.name, edits:{pool:d.mercPick}};
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/campfiles/plan', body); }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 7000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write: ${(p.changes || []).join('\n') || 'no visible change'}?\n\n`
    + ((p.warnings || []).length ? (p.warnings || []).slice(0, 3).join('\n') + '\n\n' : '')
    + `${d.mercenaries.file} only - the region record is not touched.\n\n`
    + 'Backed up first, and 🕑 Log can undo it.')) return;
  c.busy = true;
  let res;
  try{ res = await api.post('/api/campfiles/apply', body); }
  finally{ c.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 7000); return; }
  toast('Mercenary pool saved. 🕑 Log can undo it.');
  const name = d.name;
  c.det = null;
  await cmapOpenRegion(name);
}

function cmapFindingsHtml2(){
  const d = state.cmap.det;
  return (d.findings || []).map(f =>
    `<div class="cmfind2 ${f.fatal ? 'w-bad' : 'w-warn'}">line ${f.line}:
      ${esc(f.message)}</div>`).join('');
}

/* The resource line, and what the tool makes of it.

   One box, comma separated, because that is what the line is - and beneath it
   the split into the two kinds, which is the thing no reference tool shows.
   A name in neither list is not silently dropped: it is shown as unknown,
   which is 16f's rule brought forward to where somebody can fix it. */
function cmapResourceHtml(){
  const d = state.cmap.det, w = d.w, v = d.vocab;
  const hidden = new Set(v.hidden_resources.map(x => x.toLowerCase()));
  const trade = new Set(v.trade_resources.map(x => x.toLowerCase()));
  const chip = (r) => {
    const k = r.toLowerCase();
    const cls = hidden.has(k) ? 'h' : trade.has(k) ? 't' : 'u';
    const why = cls === 'h' ? 'hidden resource (the EDB declares it)'
      : cls === 't' ? 'trade resource (descr_sm_resources.txt names it)'
      : 'neither a hidden resource nor a trade resource this mod has';
    return `<span class="cmchip ${cls}" title="${esc(why)}">${esc(r)}</span>`;
  };
  const all = v.hidden_resources.concat(v.trade_resources);
  return `<div class="cmfield"><label>Resources</label>
    <input list="cml-res" value="${esc(w.resources.join(', '))}"
      oninput="cmapSetResources(this.value)">
    <datalist id="cml-res">${all.map(x =>
      `<option value="${esc(x)}">`).join('')}</datalist>
    <div class="cmchips">${w.resources.map(chip).join('') ||
      '<span class="count">none</span>'}</div>
    <div class="count">${v.hidden_resources.length} hidden resources on the EDB's
      own line, ${v.trade_resources.length} trade resources in
      descr_sm_resources.txt.</div></div>`;
}

//: Every religion the mod declares, plus any this region names that it does
//: not - because a percentage pointing at a religion nobody declared is read
//: and ignored by the engine, and dropping the box would hide it.
function cmapReligionNames(){
  const d = state.cmap.det;
  const out = (d.vocab.religions || []).slice();
  for(const n of Object.keys(d.w.religions))
    if(!out.some(x => x.toLowerCase() === n.toLowerCase())) out.push(n);
  return out;
}
function cmapReligionTotal(){
  return Object.values(state.cmap.det.w.religions)
    .reduce((a, b) => a + (parseInt(b, 10) || 0), 0);
}
function cmapReligionRows(){
  const d = state.cmap.det, known = new Set((d.vocab.religions || [])
    .map(x => x.toLowerCase()));
  return cmapReligionNames().map(n => {
    const has = n in d.w.religions;
    return `<div class="cmrel${known.has(n.toLowerCase()) ? '' : ' odd'}">
      <span>${esc(n)}${known.has(n.toLowerCase()) ? ''
        : ' <span class="w-warn" title="descr_religions.txt does not declare this'
        + ' one, so the engine reads the number and ignores it">?</span>'}</span>
      <input type="number" min="0" max="100" value="${has ? d.w.religions[n] : ''}"
        placeholder="${has ? '' : '-'}"
        oninput="cmapSetReligion('${esc(n)}', this.value)"></div>`;
  }).join('');
}

//: What the pixels say. Read-only in this panel on purpose: moving a border or
//: a settlement means painting map_regions.tga, which is what the brush above
//: is for - a number typed into a box here could not move a pixel.
function cmapPixelHtml(){
  const d = state.cmap.det, px = d.pixels;
  if(d.pixels_problem) return `<div class="k">On the map</div>
    <div class="w-bad">${esc(d.pixels_problem)}</div>`;
  if(!px) return '';
  if(!px.count) return `<div class="k">On the map</div>
    <div class="w-bad">This region is declared in descr_regions.txt and not one
    pixel of map_regions.tga is painted its colour. That is legal to write and
    fatal to play.</div>`;
  const g = p => p ? `${p[0]}, ${p[1]}` : '-';
  return `<div class="k">On the map <span class="count">counted off the
      pixels - arm the brush to change them</span></div>
    <div class="cmkv">
      <span>Region ID</span><b>${px.region_id >= 0 ? px.region_id : '-'}</b>
      <span>Tiles</span><b>${px.count.toLocaleString()}${px.sea
        ? ` <span class="count">${px.sea.toLocaleString()} of them sea</span>` : ''}</b>
      <span>Settlement at</span><b>${g(px.settlement_game)}
        <span class="count">game</span> · ${g(px.settlement)}
        <span class="count">image</span></b>
      <span>Port at</span><b>${px.port_game ? `${g(px.port_game)}
        <span class="count">game</span> · ${g(px.port)}
        <span class="count">image</span>` : 'none'}</b>
      <span>Bounding box</span><b>${px.bbox.join(', ')}</b>
    </div>
    <div class="k">Neighbours <span class="count">${px.neighbours.length} sharing an
      edge on map_regions.tga</span></div>
    <div class="cmnb">${px.neighbours.map(n => `<button class="cmchip n"
      onclick="cmapGoRegion(${n.key})"
      title="${esc(n.declared ? 'region ' + n.region_id : 'declared nowhere in descr_regions.txt')}"
      ><i style="background:rgb(${n.rgb.join(',')})"></i>${
      esc(n.name || 'undeclared')}</button>`).join('')}</div>
    <div class="count">Adjacency on the region layer alone. Land bridges and
      river crossings connect provinces these pixels do not, and that rule is
      16f's.</div>`;
}

//: Click a neighbour: select it on the canvas exactly as a click on its own
//: pixels would, so the outline, the probe and the form all follow.
function cmapGoRegion(key){
  const c = state.cmap, r = c.byKey.get(key);
  if(!r || !r.anchor) return;
  cmapPick(r.anchor);
}

/* ---- the working copy ---- */
function cmapSet(slot, value){
  const d = state.cmap.det; if(!d || !d.w) return;
  d.w[slot] = value;
  cmapTouched(false);
}
function cmapSetResources(text){
  const d = state.cmap.det; if(!d || !d.w) return;
  d.w.resources = text.split(',').map(v => v.trim()).filter(Boolean);
  // the chips under the box are the point of it, so this one does repaint -
  // and it repaints the FORM, not the pane, because the caret is in the box
  cmapTouched(true);
}
function cmapSetReligion(name, value){
  const d = state.cmap.det; if(!d || !d.w) return;
  const v = value.trim();
  if(v === '') delete d.w.religions[name];
  else d.w.religions[name] = parseInt(v, 10) || 0;
  cmapTouched(true);
}
function cmapTouched(repaint){
  const d = state.cmap.det;
  if(repaint) cmapRegionPaint();
  else{
    // the running total is the one thing that has to move on every keystroke,
    // because it is the rule a save is refused by
    const el = document.querySelector('.cmrels');
    const k = el && el.previousElementSibling
      ? el.previousElementSibling.querySelector('span') : null;
    if(k){
      const t = cmapReligionTotal();
      k.className = t === 100 ? 'count' : 'w-bad';
      k.textContent = `total ${t}` + (t === 100 ? ''
        : ` - the game crashes on load unless this is 100 (${t > 100 ? '+' : ''}${t - 100})`);
    }
  }
  if(d && d.cv) cvFromGui(d.cv);
}

/* ---- the code view ---- */
async function cmapCvToggle(){
  const c = state.cmap, d = c.det;
  if(!d || !d.w) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); cmapPickPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate({kind:'regions', mod:c.mod, id:d.name, where:'data/' + d.file,
    edits:() => cmapEdits(),
    adopt:cv => { const s = state.cmap.det;
      if(!cv.detail) return;
      s.w = {legion:cv.detail.legion, faction:cv.detail.faction,
             rebels:cv.detail.rebels, resources:cv.detail.resources.slice(),
             triumph:cv.detail.triumph, farming:cv.detail.farming,
             religions:Object.assign({}, cv.detail.religions)};
      // `base`, never `text`: with comment hiding on, `text` is the view with
      // the comment-only lines cut out, and saving that would delete every one
      s.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => cmapRegionPaint()});
  cmapPickPaint();
  await cvLoad(d.cv);
  if(state.cmap !== c || state.cmap.det !== d || !d.cv) return;
  cmapPickPaint();
}

/* ---- writing ----
   `edits` is exactly what campmap.render_block takes, so the pane and the save
   cannot produce different bytes. */
function cmapEdits(){
  const w = state.cmap.det.w;
  return {legion:(w.legion || '').trim(), faction:(w.faction || '').trim(),
          rebels:(w.rebels || '').trim(),
          resources:w.resources.map(r => r.trim()).filter(Boolean),
          triumph:w.triumph, farming:w.farming,
          religions:Object.assign({}, w.religions)};
}

async function cmapSave(){
  const c = state.cmap, d = c.det;
  if(!d || !d.w || c.busy) return;
  const total = cmapReligionTotal();
  if(total !== 100 && d.has.religions){
    toast(`✗ The religion percentages total ${total}. The game crashes on load `
      + `unless they total 100 - ${total > 100 ? 'take' : 'add'} `
      + `${Math.abs(total - 100)} ${total > 100 ? 'off' : 'on'} before saving.`, 7000);
    return;
  }
  const body = {mod:c.mod, region:d.name, edits:cmapEdits()};
  if(d.raw) body.raw_block = d.raw;
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/plan', body); }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 7000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  if(!confirm(`Write: save ${d.name}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14 ? `\n…and ${p.changes.length - 14} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nmap.rwm is deleted too, or the game loads the old compiled map and '
    + 'shows none of this.\n\nBacked up first, and 🕑 Log can undo it.')) return;
  c.busy = true;
  let res;
  try{ res = await api.post('/api/map/apply', body); }
  finally{ c.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 7000); return; }
  toast('Saved. map.rwm deleted. 🕑 Log can undo it.');
  const at = c.pick;
  await loadCampmap();
  if(at && state.cmap) cmapPick(at);
}

/* ---------- keys ---------- */

//: Bound once and left bound: the handler asks whether this screen is on top
//: before it does anything, which is cheaper than wiring and unwiring it.
/* Which number key this is, whatever it prints.

   20a, T11. `e.key` for a digit is what the layout produces, and the top row
   produces a digit only unshifted and only on some layouts: shift it on a US
   keyboard and `1` is `!`, and on AZERTY the same key is `&` before it is
   anything. `e.code` is the physical key, which is what "the number keys" means
   when somebody is looking at their keyboard rather than at their layout. The
   `e.key` arm is the fallback for anything that does not report one. */
function cmapDigit(e){
  const m = /^Digit([0-9])$/.exec(e.code || '');
  if(m) return m[1];
  return /^[0-9]$/.test(e.key) ? e.key : '';
}

/* The layer a number key ticks, or null. The manifest carries the digit with
   each layer (`campmap.HOTKEYS`), so this is a lookup rather than a second
   opinion about which key is which. */
function cmapLayerForKey(digit){
  const c = state.cmap;
  for(const l of c.man.layers) if(l.hotkey === digit) return l.code;
  return null;
}

/* The keyboard, and the one thing 20a had to take away to give T11 what it
   asks for.

   Ten layers and ten number keys leaves no digit for the two zoom commands 16c
   put on `0` and `1`, so those moved to Shift and the toolbar's own tooltips
   say so. Shift rather than a letter because the digit is the mnemonic - fit is
   still zero - and because Ctrl+1 and Ctrl+0 are the browser's own and a page
   cannot have them.

   The point of the whole item is what it does NOT disturb: a layer is ticked
   without the pointer moving, so the tile under it and the tooltip naming that
   tile on all ten layers stay exactly where they were. `cmapMode`'s repanel
   rebuilds the side panel and nothing else; the canvas, the hover and the
   readout are untouched. */
function cmapKeys(){
  if(state.cmapKeys) return;
  state.cmapKeys = true;
  document.addEventListener('keydown', e => {
    if(state.mode !== 'campmap' || !state.cmap) return;
    if(overlay.classList.contains('open')) return;
    const t = e.target.tagName;
    if(t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
    const digit = (e.ctrlKey || e.metaKey || e.altKey) ? '' : cmapDigit(e);
    if(digit && e.shiftKey){
      if(digit === '0') cmapFit();
      else if(digit === '1') cmapZoomTo(1);
      else return;
    }
    else if(digit){
      const code = cmapLayerForKey(digit);
      if(!code) return;
      cmapToggleLayer(code);
    }
    else if(e.key === '+' || e.key === '='){ cmapZoomBy(1.4); }
    else if(e.key === '-' || e.key === '_'){ cmapZoomBy(1 / 1.4); }
    else if(e.key === 't' || e.key === 'T'){ cmapTipToggle(); }
    // 20b, T8. A letter and not a digit, because the ten digits are the ten
    // layers; `f` for find, beside `t` for the tooltip, and the handler above
    // has already returned if the cursor is in a box - including this one.
    else if(e.key === 'f' || e.key === 'F'){
      const k = state.cfd;
      if(!k) return;
      if(!k.open) cfdToggle(); else cfdFocus();
    }
    else if(e.key === 'Escape' && (state.cmap.sel || state.cmap.pick)){
      const c = state.cmap;
      c.sel = null; c.pick = null; c.probe = null; c.det = null;
      state.cset = null; state.cx = null;
      cmapOutline(null); cmapPaint(); cmapPickPaint(); csPaint(); cxPaint();
    }
    else return;
    e.preventDefault();
  });
}
