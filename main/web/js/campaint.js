/* campaint.js - Campaign Map: the paint tool, its palettes and its undo

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE BRUSH - Phase 16e.

   campmap.js draws the map and names what is under the cursor. This paints it,
   and the division of labour with the server is the whole design:

     THE BROWSER decides which tiles the pointer went over and draws a
     provisional trail so the cursor tells the truth during a drag.
     PYTHON decides which pixels change. It expands the same samples, snaps the
     colour, refuses what must not be written, and answers with the tiles that
     actually moved.
     THE BROWSER throws its trail away and writes that answer into its own copy.

   So a disagreement between what you see and what the file would say cannot
   outlive one pointer-up, there is exactly one brush that decides bytes, and
   the undo stack, the backups and every refusal live on the side that owns the
   pixels. Demir's editor paints in the browser and writes what the browser has;
   that is why its water brush can put a sea tile on a region the file still
   thinks is land.

   ONE REQUEST PER STROKE, never per pointer event. A drag accumulates samples
   and posts them once, on release. That is also the undo granularity, which is
   the granularity anybody actually wants: one press, one step back.

   REGION-COLOUR SNAPPING. Painting map_regions.tga never sends a colour. It
   sends the NAME of the selected region, and the server writes that region's
   own RGB out of descr_regions.txt. A province cannot drift a channel, the two
   marker colours cannot be produced by a brush at all, and the palette for that
   layer is the region list rather than a colour picker.

   THE WIZARD is three steps because the order is a real dependency: the record
   is decided first (the colour has to exist before the brush can snap to it),
   then the province is painted, then the settlement pixel goes on one of its own
   tiles, then the port or a skip. Every step is measured off the pixels rather
   than remembered, so the panel cannot claim a step is done when the map says
   otherwise.
   ===================================================================== */

//: How wide the palette swatch grid gets before it scrolls instead.
const CPAINT_PAL_MAX = 520;
//: Tools that use the size slider. The bucket and the pipette are a click.
const CPAINT_SIZED = ['brush', 'water'];

/* ---------- state ---------- */

/* The paint tool's whole state, made when the map screen opens.

   Kept beside `state.cmap` rather than inside it: `loadCampmap` rebuilds that
   object whenever the mod changes or a save reloads the screen, and the tool
   settings - which brush, how big, which layer - are habits rather than facts
   about the map. `st` is the server's own answer about what is unsaved, and it
   is never guessed at here: every stroke, undo and redo comes back with it. */
function cpaintNew(mod){
  return {
    mod, on: false, tool: 'brush', size: 3, shape: 'round',
    target: 'regions', region: '', sea: false, rgb: null,
    marker: '', pal: null, palErr: '', busy: false, err: '', note: '',
    filter: '', wiz: null, wizOpen: false, prog: null,
    st: {dirty: [], files: [], undo: 0, redo: 0, dropped: 0, last: '',
         next: '', new_region: null},
    samples: [], trail: null, painting: false,
  };
}

function cpaintOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cpaint || state.cpaint.mod !== c.mod) state.cpaint = cpaintNew(c.mod);
  cpaintPaint();
  if(state.cpaint.on && !state.cpaint.pal) cpaintLoadPalette();
}

//: Whether the left button paints rather than pans. Read by campmap.js's
//: pointer handler on every press, so it has to be cheap and total.
function cpaintArmed(){
  const p = state.cpaint;
  return !!(p && p.on && state.cmap && state.mode === 'campmap');
}

function cpaintToggle(){
  const p = state.cpaint;
  if(!p) return;
  // A campaign that reads its own map is drawn from it, and the brush paints
  // world/maps/base: arming it there would paint a map nobody can see. The
  // server refuses the stroke too; this says so before anybody tries one.
  const h = state.cmap && state.cmap.man && state.cmap.man.campaign_map;
  if(!p.on && h && h.paints === false){
    p.err = (h.readers || []).length
      ? tt('campaint.own_map_open_with_readers',{campaign:h.campaign,folder:h.folder,readers:h.readers.join(' or ')})
      : tt('campaint.own_map_no_readers',{campaign:h.campaign,folder:h.folder});
    cpaintPaint();
    return;
  }
  p.on = !p.on;
  if(p.on && state.cmap) state.cmap.selectMode = false;
  p.err = ''; p.note = '';
  activity(tt('campaint.map_paint'), p.on ? tt('campaint.armed_the_brush') : tt('campaint.put_the_brush_down'));
  if(p.on && !p.pal) cpaintLoadPalette();
  if(p.on) cpaintSync();
  cpaintPaint();
}

async function cpaintLoadPalette(){
  const p = state.cpaint;
  p.palErr = '';
  try{ p.pal = await api.get(`/api/map/palette?mod=${enc(p.mod)}`); }
  catch(e){ p.palErr = errText(e); }
  if(state.cpaint !== p) return;
  // open on the region the map is already showing, if one is selected
  if(!p.region && state.cmap && state.cmap.det && state.cmap.det.name)
    p.region = state.cmap.det.name;
  cpaintPaint();
}

//: What is unsaved, asked without changing anything. Run when the tool is armed
//: so a session left over from earlier in the sitting is on the screen rather
//: than a surprise at the first stroke.
async function cpaintSync(){
  const p = state.cpaint;
  const r = await cpaintPost('paint_state', {});
  if(r && r.state) p.st = r.state;
  cpaintPaint();
}

/* ---------- the wire ---------- */

/* Every paint request goes through here, so the four things that are true of
   all of them are said once: the mod, the busy flag the buttons read, the
   server's own sentence when it refuses, and `reset` - the one answer that
   means work was lost, which is a toast rather than a line in a panel. */
async function cpaintPost(action, body){
  const p = state.cpaint;
  p.busy = true;
  cpaintWorkspacePaint();
  let r;
  // the campaign on the screen, so the server can refuse a stroke that
  // campaign would never show (campaint.paints_for)
  const camp = (state.cmap && state.cmap.campaign) || '';
  try{ r = await api.post(`/api/map/${action}`,
                          Object.assign({mod: p.mod, campaign: camp}, body)); }
  catch(e){ r = {error: errText(e)}; }
  finally{ p.busy = false; }
  if(state.cpaint !== p) return null;
  if(r.reset){
    toast('⚠ ' + r.reset, 8000);
    p.st = r.state || p.st;
  }
  p.err = r.error || '';
  p.note = r.note || '';
  if(r.state) p.st = r.state;
  if(r.map_markers && typeof cmkSyncMapMarkers === 'function') cmkSyncMapMarkers(r.map_markers);
  cpaintWorkspacePaint();
  return r;
}

/* ---------- the stroke ---------- */

//: The canvas campmap.js blits as the provisional trail, or null when there is
//: no stroke in progress.
function cpaintTrail(){
  const p = state.cpaint;
  return (p && p.painting && p.trail) ? p.trail : null;
}

function cpaintTrailCanvas(){
  const p = state.cpaint, c = state.cmap;
  if(!p.trail || p.trail.width !== c.man.width || p.trail.height !== c.man.height){
    p.trail = document.createElement('canvas');
    p.trail.width = c.man.width; p.trail.height = c.man.height;
  }
  const x = p.trail.getContext('2d');
  return x;
}

//: The colour the trail is drawn in: the one that is going to be written, so
//: the promise on screen looks like the result. Falls back to the accent when
//: nothing is picked yet, which is also the case in which the stroke is going
//: to be refused and say why.
function cpaintTrailColour(){
  const rgb = cpaintColour();
  return rgb ? `rgb(${rgb.join(',')})` : 'rgba(200,164,92,.85)';
}

function cpaintDown(tile){
  const p = state.cpaint, c = state.cmap;
  if(!p || !c) return;
  if(p.tool === 'pipette'){ cpaintPipette(tile); return; }
  p.painting = true;
  p.samples = [];
  const x = cpaintTrailCanvas();
  x.clearRect(0, 0, p.trail.width, p.trail.height);
  x.fillStyle = cpaintTrailColour();
  cpaintMove(tile);
}

function cpaintMove(tile){
  const p = state.cpaint, c = state.cmap;
  if(!p || !p.painting) return;
  const [tx, ty] = tile;
  const last = p.samples[p.samples.length - 1];
  if(last && last[0] === tx && last[1] === ty) return;
  p.samples.push([tx, ty]);
  cpaintStamp(tx, ty, last);
  cmapPaint();
}

/* The trail's own copy of the brush, and the one place this file duplicates
   something the server does.

   It is a cursor, not a result: what lands is whatever Python made of the same
   samples, and that replaces this on pointer-up. Keeping the two shapes the
   same is what stops the cursor lying in the meantime, so the rule is written
   the same way in both - a disc of radius size-1 stamped at every tile of a
   straight line between consecutive samples. */
function cpaintStamp(tx, ty, from){
  const p = state.cpaint;
  const x = p.trail.getContext('2d');
  // size is the brush's WIDTH in tiles, as it is on the server: tiles either
  // side of the centre is (size-1)/2, and only odd widths exist because a brush
  // is centred on the tile under the cursor
  const r = ((CPAINT_SIZED.indexOf(p.tool) >= 0 ? p.size : 1) - 1) >> 1;
  const pts = from ? cpaintLine(from[0], from[1], tx, ty) : [[tx, ty]];
  for(const [cx, cy] of pts){
    if(!r){ x.fillRect(cx, cy, 1, 1); continue; }
    for(let y = cy - r; y <= cy + r; y++)
      for(let xx = cx - r; xx <= cx + r; xx++){
        if(p.shape !== 'square'
           && (xx - cx) * (xx - cx) + (y - cy) * (y - cy) > r * r) continue;
        x.fillRect(xx, y, 1, 1);
      }
  }
}

function cpaintLine(x0, y0, x1, y1){
  const out = [];
  let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for(;;){
    out.push([x0, y0]);
    if(x0 === x1 && y0 === y1) return out;
    const e2 = 2 * err;
    if(e2 >= dy){ err += dy; x0 += sx; }
    if(e2 <= dx){ err += dx; y0 += sy; }
  }
}

function cpaintCancel(){
  const p = state.cpaint;
  if(!p) return;
  p.painting = false; p.samples = [];
  cmapPaint();
}

async function cpaintUp(){
  const p = state.cpaint;
  if(!p || !p.painting) return;
  const points = p.samples;
  p.painting = false; p.samples = [];
  if(!points.length){ cmapPaint(); return; }
  const body = {tool: p.tool === 'pencil' ? 'pencil' : p.tool,
                target: p.target, size: p.size, shape: p.shape, points};
  if(p.marker){ body.tool = 'pencil'; body.marker = p.marker; body.target = 'regions'; }
  if(p.target === 'regions' || p.tool === 'water' || p.marker){
    body.region = p.region; body.sea = p.sea && !p.marker;
  }
  if(p.target !== 'regions' && p.rgb) body.rgb = p.rgb;
  const r = await cpaintPost('paint', body);
  cmapPaint();                                   // the trail goes, either way
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 7000); cpaintPaint(); return; }
  cpaintApply(r.changed);
  // While the wizard is open, every stroke can move a step - painting the
  // province is step two and the marker is step three - so the count is taken
  // again rather than left to whichever stroke somebody expected to matter.
  if(p.st.new_region) cpaintProgress();
  cpaintPaint();
}

/* One tile of the map, picked apart on every layer at once.

   The pipette is a probe rather than a read of the browser's own pixels, and
   that is on purpose: it has to work on a layer that is not ticked and
   therefore not loaded, and the answer names the colour as well as giving it.
   Picking on the region layer selects the region, which is what "pick this
   colour" means when the palette is the region list. */
async function cpaintPipette(tile){
  const p = state.cpaint, c = state.cmap;
  const [tx, ty] = tile;
  let r;
  try{ r = await api.get(`/api/map/probe?mod=${enc(p.mod)}&x=${tx}&y=${ty}`
                         + cmapCampQ()); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  if(state.cpaint !== p) return;
  const L = (r.layers || []).find(l => l.code === p.target);
  if(!L || !L.rgb){ toast(tt('campaint.has_no_value_at',{target:p.target,tx,ty}), 5000); return; }
  if(p.target === 'regions'){
    const reg = c.byKey.get((L.rgb[0] << 16) | (L.rgb[1] << 8) | L.rgb[2]);
    if(reg && reg.name){ p.region = reg.name; p.sea = false; }
    else if(r.sea){ p.sea = true; p.region = ''; }
    else { toast(tt('campaint.that_tile_is_not_painted_any'), 5000); return; }
  }else{
    p.rgb = L.rgb.slice();
  }
  toast(tt('campaint.picked',{x:L.name || L.rgb.join(', ')}));
  cpaintPaint();
}

/* ---------- writing the server's answer into the browser's copy ---------- */

//: `{code: {rgb, xy}}` as a stroke answers, or `{code: {runs:[…]}}` as an undo
//: does. Both end up here, because both are "these tiles are now these colours".
function cpaintApply(changed){
  const codes = [];
  for(const code in changed){
    const c = changed[code];
    const runs = c.runs || [{rgb: c.rgb, xy: c.xy}];
    if(cpaintWrite(code, runs)) codes.push(code);
  }
  if(codes.length) cmapAfterPaint(codes);
  return codes;
}

/* One layer's tiles, written through one ImageData.

   A bucket fill of an ocean is 70,000 tiles. Seventy thousand 1x1 fillRects is
   a visible pause; the writes into the layer's bytes and one putImageData of
   the bounding box is a few milliseconds. The bounding box matters as much as
   the single call - a pencil dot should not rewrite the whole map. */
function cpaintWrite(code, runs){
  const cv = cmapPixels(code);
  if(!cv) return false;
  let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
  for(const run of runs)
    for(let i = 0; i < run.xy.length; i += 2){
      const x = run.xy[i], y = run.xy[i + 1];
      if(x < x0) x0 = x;
      if(x > x1) x1 = x;
      if(y < y0) y0 = y;
      if(y > y1) y1 = y;
    }
  if(x1 < 0) return false;
  const w = x1 - x0 + 1, h = y1 - y0 + 1;
  const L = state.cmap.layers[code], R = cmapRawOf(L);
  // into the layer's bytes first - they are what every lookup reads - and then
  // the bounding box out of them onto the canvas. Nothing is read back off the
  // canvas: a browser may alter what it hands back (see cmapFetchLayer).
  for(const run of runs){
    const r = (run.rgb >> 16) & 255, g = (run.rgb >> 8) & 255, b = run.rgb & 255;
    for(let i = 0; i < run.xy.length; i += 2){
      const p = (run.xy[i + 1] * R.w + run.xy[i]) * 4;
      R.data[p] = r; R.data[p + 1] = g; R.data[p + 2] = b; R.data[p + 3] = 255;
    }
  }
  const box = new Uint8ClampedArray(w * h * 4);
  for(let y = 0; y < h; y++){
    const from = ((y0 + y) * R.w + x0) * 4;
    box.set(R.data.subarray(from, from + w * 4), y * w * 4);
  }
  L.px.putImageData(cmapImageData(box, w, h), x0, y0);
  return true;
}

/* ---------- undo, redo, save ---------- */

async function cpaintUndo(){
  const p = state.cpaint;
  if(p.busy || !p.st.undo) return;
  const r = await cpaintPost('paint_undo', {});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  cpaintApply(r.restored);
  if(p.st.new_region) cpaintProgress();
  cpaintPaint();
}

async function cpaintRedo(){
  const p = state.cpaint;
  if(p.busy || !p.st.redo) return;
  const r = await cpaintPost('paint_redo', {});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  cpaintApply(r.changed);
  if(p.st.new_region) cpaintProgress();
  cpaintPaint();
}

async function cpaintDiscard(){
  const p = state.cpaint;
  if(p.busy) return;
  if(p.st.undo && !confirm(ttN('campaint.throw_away_unsaved_strokes',p.st.undo))) return;
  await cpaintPost('paint_discard', {});
  toast(tt('campaint.the_map_was_re_read_from'));
  await loadCampmap();
}

async function cpaintSave(){
  const p = state.cpaint;
  if(p.busy) return;
  const plan = await cpaintPost('paint_plan', {});
  if(!plan) return;
  if(plan.error){ toast('✗ ' + plan.error, 9000); cpaintPaint(); return; }
  const q = plan.plan || {};
  const warn = (q.warnings || []).map(w => '⚠ ' + w);
  if(!confirm(tt('campaint.write_save_the_painted_map_confirm',{
    changes:(q.changes || []).join('\n') || tt('common.no_visible_change'),
    warnings:warn.length ? '\n\n' + warn.join('\n') : ''}))) return;
  const res = await cpaintPost('paint_apply', {});
  if(!res) return;
  if(res.error){ toast('✗ ' + res.error, 9000); cpaintPaint(); return; }
  const camp = (q.texts || []).length;
  toast(tt('campaint.saved_layers_done',{
    layers:res.region ? ttN('campaint.saved_layers_and_record',(res.layers || []).length,{region:res.region})
      : ttN('campaint.saved_layer_count',(res.layers || []).length),
    camp:camp ? ttN('campaint.and_campaign_file_count',camp) : ''}), 6000);
  p.wiz = null; p.wizOpen = false; p.prog = null;
  await loadCampmap();
}

/* ---------- the new-region wizard ---------- */

//: A colour no record claims and no pixel of the map carries. Walked rather
//: than random, so two people adding a region to the same mod get the same
//: first suggestion and a diff of the file is readable.
function cpaintFreeColour(){
  const c = state.cmap;
  const taken = new Set();
  for(const r of c.man.regions) taken.add(r.key);
  taken.add((c.man.markers.settlement[0] << 16) | (c.man.markers.settlement[1] << 8)
            | c.man.markers.settlement[2]);
  taken.add((c.man.markers.port[0] << 16) | (c.man.markers.port[1] << 8)
            | c.man.markers.port[2]);
  for(let r = 8; r < 250; r += 9)
    for(let g = 8; g < 250; g += 11)
      for(let b = 8; b < 250; b += 13)
        if(!taken.has((r << 16) | (g << 8) | b)) return [r, g, b];
  return [1, 2, 3];
}

async function cpaintWizOpen(){
  const p = state.cpaint;
  if(p.st.new_region){ p.wizOpen = true; cpaintPaint(); return; }
  // B1. The three pickers - who built it, who holds it, what plays over it -
  // and which campaigns will be written, asked before the form is drawn so the
  // creator is a list and not a free-text box with `slave` in it.
  const r = await cpaintPost('region_vocab', {});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  p.voc = r.vocab; p.vocCamps = r.campaigns || [];
  p.wiz = {name: '', settlement: '', shown: '', settlement_shown: '',
           rgb: cpaintFreeColour(), faction: '',
           owner: p.voc.owner_default || '', music: '',
           rebels: '', resources: '', religions: '', port: true};
  p.wizOpen = true;
  cpaintPaint();
}

function cpaintWizSet(slot, value){
  const p = state.cpaint;
  if(!p.wiz) return;
  if(slot === 'rgb'){
    const n = value.split(/[\s,]+/).map(v => parseInt(v, 10)).filter(v => v === v);
    if(n.length === 3) p.wiz.rgb = n;
    return;                                 // no repaint: the caret is in the box
  }
  p.wiz[slot] = value;
}

//: "Gondor (sicily)", or the slot when the mod names it nothing.
function cpaintFac(code){
  const v = state.cpaint.voc || {};
  return (v.labels && v.labels[code]) || code;
}

/* Open the record. Everything about it is decided before a pixel is painted,
   because the colour has to exist for the brush to snap to and because nobody
   should spend ten minutes painting with a colour that turns out to be taken. */
async function cpaintWizStart(){
  const p = state.cpaint, w = p.wiz;
  if(!w) return;
  const rel = {};
  for(const bit of (w.religions || '').split(',')){
    const m = bit.trim().match(/^(\S+)\s+(\d+)$/);
    if(m) rel[m[1]] = parseInt(m[2], 10);
  }
  const r = await cpaintPost('region_start', {
    name: w.name.trim(), settlement: w.settlement.trim(), rgb: w.rgb,
    shown: (w.shown || '').trim(),
    settlement_shown: (w.settlement_shown || '').trim(),
    faction: w.faction.trim(), rebels: w.rebels.trim(),
    owner: (w.owner || '').trim(), music: (w.music || '').trim(),
    resources: (w.resources || '').split(',').map(s => s.trim()).filter(Boolean),
    religions: rel, port: !!w.port});
  if(!r) return;
  if(r.error){ toast('✗ ' + r.error, 8000); cpaintPaint(); return; }
  // so the hover readout names the new province from its first painted tile
  const c = state.cmap;
  const spec = p.st.new_region;
  c.byKey.set(spec.key, {key: spec.key, rgb: spec.rgb, name: spec.name, id: -1,
                         pixels: 0, sea: 0, anchor: null, settlement: null,
                         port: null, declared: false});
  p.region = spec.name; p.sea = false; p.target = 'regions'; p.tool = 'brush';
  p.on = true;
  toast(tt('campaint.is_open_paint_it_then_place',{name:spec.name}), 6000);
  cpaintProgress();
}

async function cpaintWizCancel(){
  const p = state.cpaint;
  if(p.st.new_region && !confirm(tt('campaint.drop_the_new_region_confirm'))) return;
  await cpaintPost('region_cancel', {});
  p.wiz = null; p.wizOpen = false; p.prog = null; p.marker = '';
  cpaintPaint();
}

//: Where the wizard has got to, counted off the pixels by the server rather
//: than remembered here. A step counter that can disagree with the map is a
//: step counter that will.
async function cpaintProgress(){
  const p = state.cpaint;
  const r = await cpaintPost('paint_plan', {});
  if(!r) return;
  p.prog = (r.plan && r.plan.region && r.plan.region.progress) || null;
  p.wizFindings = (r.plan && r.plan.findings) || [];
  // B1. What the save would refuse over that is not about the pixels - a blank
  // shown name, a campaign that could not take the settlement - so it is on
  // the wizard before Save is pressed, not only in the dialog after
  const told = new Set(p.wizFindings.map(f => f.message));
  p.wizPlanErrors = ((r.plan && r.plan.errors) || []).filter(e => !told.has(e));
  p.wizMusic = (r.plan && r.plan.region && r.plan.region.music_chosen) || '';
  p.err = '';                       // a plan that refuses is the wizard's state,
  cpaintPaint();                    // not an error about the last stroke
}

function cpaintMarker(kind){
  const p = state.cpaint;
  p.marker = p.marker === kind ? '' : kind;
  if(p.marker){ p.tool = 'pencil'; p.target = 'regions'; }
  cpaintPaint();
}

/* ---------- the panel ---------- */

//: 28b: two places now - the panel in the Paint tab and the row on the map's
//: own toolbar. Both are rebuilt whole, which is what every other repaint on
//: this screen does; the one control that must not be is the size slider, and
//: `cpaintWireIn` writes its number without a repaint because the slider has
//: the pointer.
function cpaintPaint(){
  const el = document.getElementById('cmPaint');
  if(el){
    el.innerHTML = cpaintHtml();
    cpaintWireIn(el);
  }
  cpaintBarPaint();
  cpaintDockPaint();       // 49: the colours, in the column on the left
}

function cpaintHtml(){
  const p = state.cpaint;
  if(!p) return '';
  const st = p.st;
  const unsaved = st.undo || st.dirty.length || st.new_region;
  const head = `<div class="cpbar">
    ${tt('campaint.paint',{x:unsaved ? `<span class="cpun" title="${esc(st.files.join(', '))}">${ttN('campaint.strokes_unsaved',st.undo,{layers:st.dirty.length
        ? ttN('campaint.layer_count',st.dirty.length) : ''})}</span>` : ''})}
  </div>`;
  if(!p.on) return head + `<div class="cppanel">${p.err
    ? `<div class="w-warn">${esc(p.err)}</div>`
    : `<span class="count">${tt('campaint.the_brush_is_put_down_paint')}</span>`}</div>`;
  if(p.palErr) return head + `<div class="cppanel"><div class="w-bad">${
    esc(p.palErr)}</div></div>`;
  if(!p.pal) return head + `<div class="cppanel"><span class="count">${tt('campaint.reading_the_palettes')}</span></div>`;
  return head + `<div class="cppanel">
    ${cpaintWaterHtml()}
    ${cpaintChosenHtml()}
    <div class="count">${tt('campaint.the_layer_and_its_colours_are')}</div>
    ${cpaintWizHtml()}
    ${cpaintFootHtml()}
  </div>`;
}

const CPAINT_TOOLS = [
  ['pencil', '✏', tt('campaint.pencil'), tt('campaint.one_tile_per_click_or_drag')],
  ['brush', '\u{1F58C}', tt('campaint.brush'), tt('campaint.a_disc_or_square_of_tiles')],
  ['bucket', '\u{1FAA3}', tt('campaint.bucket'), tt('campaint.bucket_hint')],
  ['pipette', '\u{1F489}', tt('campaint.pipette'), tt('campaint.pipette_hint')],
  ['water', '\u{1F30A}', tt('campaint.water'), tt('campaint.water_hint')],
];

//: 28b: the five tool buttons and nothing else - the size and the water note
//: were in here and are now their own, because the bar wants one and the panel
//: wants the other.
function cpaintToolsHtml(){
  const p = state.cpaint;
  return `<div class="cptools">${CPAINT_TOOLS.map(([code, glyph, label, why]) =>
    `<button class="cptool${p.tool === code && !p.marker ? ' on' : ''}"
      data-tool="${code}" title="${esc(label)}: ${esc(why)}"
      >${glyph}<span>${esc(label)}</span></button>`).join('')}</div>`;
}

//: The size slider and the brush shape, for the two tools that have a size.
//: The bucket and the pipette are a click, so the row is not drawn for them
//: rather than drawn disabled: on the toolbar it would be width taken from the
//: map to say nothing.
function cpaintSizeHtml(){
  const p = state.cpaint;
  if(CPAINT_SIZED.indexOf(p.tool) < 0 || p.marker) return '';
  return `<span class="cpsized">
    <label class="cpsz">${tt('campaint.size')}
      <input type="range" min="1" max="${p.pal.brush_max}" step="2"
        value="${p.size}" data-size></label>
    <b class="cpszn">${tt('campaint.across',{p_n:p.size})}</b>
    <button class="cpshape${p.shape === 'round' ? ' on' : ''}" data-shape="round"
      title="${ttA('campaint.a_disc')}">●</button>
    <button class="cpshape${p.shape === 'square' ? ' on' : ''}" data-shape="square"
      title="${ttA('campaint.a_square')}">■</button></span>`;
}

//: What the water brush is about to write, in this map's own sea colours. It
//: stays in the panel: it is four sentences and a swatch list, which is reading
//: rather than reaching.
function cpaintWaterHtml(){
  const p = state.cpaint;
  const w = p.pal.water || {};
  return `${p.tool === 'water' ? `<div class="cpnote">${w.ok
      ? tt('campaint.writes_layers_at_once_in_the',{n:Object.keys(w.layers).length,layers:Object.keys(w.layers).map(c =>
         `<i style="background:rgb(${w.layers[c].rgb.join(',')})"></i>${esc(c)}`
         ).join(' '),sea_tiles:w.sea_tiles.toLocaleString()})
      : `<span class="w-bad">${esc(w.problem
         || tt('campaint.no_tile_of_this_map_reads'))
         }</span>`}</div>` : ''}`;
}

function cpaintLayer(){
  const p = state.cpaint;
  return p.pal.layers.find(L => L.code === p.target) || null;
}

//: The colour that is going to be written, as three numbers, or null when
//: nothing is picked. The one place the panel and the trail agree.
function cpaintColour(){
  const p = state.cpaint;
  if(!p.pal) return null;
  if(p.marker) return p.marker === 'settlement'
    ? p.pal.markers.settlement : p.pal.markers.port;
  if(p.tool === 'water'){
    const w = p.pal.water;
    return (w && w.ok) ? w.layers.regions.rgb : null;
  }
  if(p.target === 'regions'){
    if(p.sea){
      const w = p.pal.water;
      return (w && w.layers && w.layers.regions) ? w.layers.regions.rgb : null;
    }
    const L = cpaintLayer();
    const hit = L && L.colours.find(k => k.region === p.region);
    if(hit) return hit.rgb;
    const spec = p.st.new_region;
    return (spec && spec.name === p.region) ? spec.rgb : null;
  }
  return p.rgb;
}

/* What is going to be written, said before it is. Shown in both places that
   matter now - the dock that picks it and the panel that saves it - because it
   is one line and the alternative is a panel that cannot tell you what the
   brush is holding. */
function cpaintChosenHtml(){
  const p = state.cpaint;
  if(!p.pal) return '';
  const L = p.tool === 'water' ? null : cpaintLayer();
  if(L && L.problem) return `<div class="cpnote w-bad">${esc(L.problem)}</div>`;
  const rgb = cpaintColour();
  return `<div class="cppick">
    <i style="background:${rgb ? `rgb(${rgb.join(',')})` : 'transparent'}"></i>
    <span>${rgb ? cpaintColourName() : `<span class="w-warn">${tt('campaint.nothing_picked_a')} `
      + `${tt('campaint.stroke_would_be_refused_and_say')}</span>`}</span></div>`;
}

/* 49: the layer being painted, as a toggle rather than a dropdown.

   It was a `<select>` on the toolbar, which is the one control on this screen
   you cannot read without opening: the thing a stroke is about to change was a
   word behind a click. Eight buttons, one per paintable layer, with the one
   that is up lit - and they sit on top of the colours, because the colours ARE
   the layer's and change with it.

   A layer the server could not read is disabled with its reason on the title,
   not left out: "heights is not in this mod" is worth saying once. */
function cpaintLayerTogHtml(){
  const p = state.cpaint;
  if(!p.pal) return '';
  if(p.tool === 'water') return `<div class="cpnote">${tt('campaint.the_water_brush_writes_regions_heights')}</div>`;
  return `<div class="k">${tt('campaint.layer_2')}</div>
    <div class="cmpallay">${p.pal.layers.map(L =>
      `<button class="${L.code === p.target ? 'on' : ''}" data-target-btn="${L.code}"
        ${L.problem ? 'disabled' : ''} title="${esc(L.label)}${
        L.problem ? ' - ' + esc(L.problem) : ' · ' + esc(L.file || '')}"
        >${esc(L.label)}</button>`).join('')}</div>`;
}

/* The colours of the layer that is up. The list only - what is CHOSEN is
   `cpaintChosenHtml`, which the panel wants as well. */
function cpaintPaletteHtml(){
  const p = state.cpaint;
  if(p.tool === 'water') return '';
  const L = cpaintLayer();
  if(!L || L.problem) return '';
  const rgb = cpaintColour();

  if(p.target === 'regions'){
    const spec = p.st.new_region;
    const f = (p.filter || '').toLowerCase();
    const rows = L.colours.filter(k => !f || (k.name + ' ' + k.code_name)
        .toLowerCase().indexOf(f) >= 0);
    const list = rows.slice(0, 400).map(k =>
      `<button class="cprg${k.region === p.region && !p.sea ? ' on' : ''}"
        data-region="${esc(k.region)}" title="${esc(k.code_name)} · ${
        k.rgb.join(', ')}"><i style="background:rgb(${k.rgb.join(',')})"></i>${
        esc(k.name)}</button>`).join('');
    const w = p.pal.water;
    return `<div class="cprow">
        <input class="cpsearch" placeholder="${ttA('campaint.find_a_region')}"
          value="${esc(p.filter)}" data-filter>
        <button class="cprg${p.sea ? ' on' : ''}" data-sea
          title="${w && w.layers && w.layers.regions
            ? tt('campaint.sea_colour_title',{rgb:w.layers.regions.rgb.join(', ')})
            : tt('campaint.this_map_has_no_sea_colour')}"
          ${w && w.layers && w.layers.regions ? '' : 'disabled'}>${tt('campaint.sea',{x:w && w.layers && w.layers.regions
            ? `<i style="background:rgb(${w.layers.regions.rgb.join(',')})"></i>`
            : ''})}</button>
        ${spec ? `<button class="cprg${spec.name === p.region ? ' on' : ''}"
          data-region="${esc(spec.name)}"><i style="background:rgb(${
          spec.rgb.join(',')})"></i>${tt('campaint.new',{name:esc(spec.name)})}</button>` : ''}
      </div>
      <div class="cppal">${list || `<span class="count">${tt('campaint.no_region_matches')}</span>`}
      </div>
      ${rows.length > 400 ? `<div class="count">${tt('campaint.match_the_first_400_are_listed',{rows_n:rows.length})}</div>` : ''}
      <div class="cpnote">${esc(L.note)}</div>`;
  }

  const list = L.colours.map(k =>
    `<button class="cpsw2${rgb && k.key === ((rgb[0] << 16) | (rgb[1] << 8) | rgb[2])
      ? ' on' : ''}" data-rgb="${k.rgb.join(',')}"
      title="${esc(k.name || tt('campaint.no_table_names_this_colour'))} · ${k.rgb.join(', ')}${
      k.count ? ttN('campaint.tile_count_suffix',k.count) : ''}"
      ><i style="background:rgb(${k.rgb.join(',')})"></i><span>${
      esc(k.name || k.rgb.join(', '))}</span></button>`).join('');
  return `<div class="cppal">${list}</div>
    <div class="cpnote">${esc(L.note)}${L.closed ? ''
      : tt('campaint.colour_outside_list_note')}</div>`;
}

/* ---------- 49: the dock on the left of the map ----------

   **The colours belong beside the tiles they go on.** They were in the right
   column behind the Paint tab, which is where you read about a stroke; picking
   one meant leaving whatever else that column was showing - the region record,
   the validator - and coming back. This column is on the other side of the
   stage, it is only there while the brush is armed, and it holds the three
   things a stroke needs and nothing else: which layer, which colour, and what
   is about to be written.

   It is wired by `cpaintWireIn` like the panel and the toolbar are, so the same
   five controls behave the same in all three and none of the three knows where
   the others put them. */
function cpaintDockPaint(){
  const el = document.getElementById('cmPalCol');
  if(!el) return;
  const p = state.cpaint;
  const show = !!(p && p.on && p.pal && !p.palErr);
  el.hidden = !show;
  el.innerHTML = show ? cpaintDockHtml() : '';
  if(show) cpaintWireIn(el);
}

function cpaintDockHtml(){
  return `${cpaintLayerTogHtml()}
    <div class="cmpalbox">
      ${cpaintChosenHtml()}
      ${cpaintPaletteHtml()}
    </div>`;
}

function cpaintColourName(){
  const p = state.cpaint;
  if(p.marker) return tt('campaint.the_marker_pixel',{marker:p.marker});
  if(p.tool === 'water') return tt('campaint.this_maps_own_sea_on_three');
  if(p.target === 'regions')
    return p.sea ? tt('campaint.sea_declared_in_no_record')
      : esc(p.region) + ` <span class="count">${tt('campaint.its_own_colour_out_of')} `
        + 'descr_regions.txt</span>';
  const L = cpaintLayer();
  const rgb = p.rgb || [];
  const hit = L && L.colours.find(k => k.rgb.join(',') === rgb.join(','));
  return hit ? `${esc(hit.name)} <span class="count">${
    hit.code_name ? '(' + esc(hit.code_name) + ') · ' : ''}${rgb.join(', ')}</span>`
    : `<span class="count">${rgb.join(', ')}</span>`;
}

/* The wizard. Three steps, and every one of them is a question about the map
   rather than a flag: how many tiles carry this colour, is there a settlement
   pixel beside them, is there a port pixel. */
function cpaintWizHtml(){
  const p = state.cpaint;
  const spec = p.st.new_region;
  if(!spec && !p.wizOpen)
    return `<div class="cprow"><button class="cpnew" onclick="cpaintWizOpen()"
      title="${ttA('campaint.add_a_province_decide_its_record')}"
      >${tt('campaint.new_region')}</button></div>`;
  if(!spec){
    const w = p.wiz || {};
    const box = (slot, label, ph, hint) => `<div class="cpfield">
      <label>${esc(label)}${hint ? ` <span class="count">${hint}</span>` : ''}</label>
      <input value="${esc(w[slot] === undefined ? '' : String(w[slot]))}"
        placeholder="${esc(ph)}" data-wiz="${slot}"></div>`;
    const pick = (slot, label, opts, hint) => `<div class="cpfield">
      <label>${esc(label)}${hint ? ` <span class="count">${hint}</span>` : ''}</label>
      <select data-wiz="${slot}">${opts.map(([v, t]) =>
        `<option value="${esc(v)}"${(w[slot] || '') === v ? ' selected' : ''}>${
        esc(t)}</option>`).join('')}</select></div>`;
    const v = p.voc || {creators: [], owners: [], music: []};
    const creators = [['', '- the faction that built it -']].concat(
      v.creators.filter(f => f !== 'slave').map(f => [f, cpaintFac(f)]));
    const owners = v.owners.map(o => [o.name, cpaintFac(o.name)
      + (o.name === 'slave' ? ' - the rebels' : '')]);
    const music = v.music.length
      ? [['', tt('campaint.the_neighbour_it_shares_the_most')]].concat(
          v.music.map(m => [m.name, tt('campaint.regions',{name:m.name,regions:m.regions})]))
      : [];
    const camps = p.vocCamps || [];
    const reach = camps.filter(c => c.reads_base).map(c => c.campaign);
    const miss = camps.filter(c => !c.reads_base).map(c => c.campaign);
    return `<div class="cpwiz">
      <div class="k">${tt('campaint.a_new_province_step_1_of')}</div>
      ${box('name', tt('campaint.region_name'), 'New_Province', 'no spaces - it is a key')}
      ${box('settlement', tt('campaint.settlement_name'), tt('campaint.newtown'), tt('campaint.no_spaces_same_reason'))}
      ${box('shown', tt('campaint.shown_on_the_map'), tt('campaint.new_province'),
        tt('campaint.required_the_game_asserts_on_a'))}
      ${box('settlement_shown', tt('campaint.settlement_shown'), tt('campaint.newtown'),
        tt('campaint.required_for_the_same_reason'))}
      <div class="cpfield"><label>${tt('campaint.colour_on_map_regions_tga_free')}</label>
        <div class="cprow"><i class="cpsw" style="background:rgb(${
          (w.rgb || [0, 0, 0]).join(',')})"></i>
        <input value="${(w.rgb || []).join(' ')}" data-wiz="rgb"></div></div>
      ${v.creators.length
        ? pick('faction', tt('campaint.creator_faction'), creators,
            tt('campaint.whose_architecture_it_is_built_in'))
        : box('faction', tt('campaint.creator_faction'), 'england',
            tt('campaint.nothing_on_disk_lists_the_factions'))}
      ${owners.length ? pick('owner', tt('campaint.starts_held_by'), owners,
        tt('campaint.a_village_last_in_that_factions')) : ''}
      ${music.length ? pick('music', tt('campaint.music_type'), music,
        tt('campaint.the_game_logs_a_province_with')) : ''}
      <div class="count">${reach.length
        ? tt('campaint.written_into_a_settlement_the_music',{reach:reach.map(esc).join(', ')})
        : tt('campaint.no_campaign_reads_this_map_note')}${miss.length
        ? ` <span class="w-warn">${ttN('campaint.miss_own_map',miss.length,{miss:miss.map(esc).join(', ')})}</span>`
        : ''}</div>
      ${box('rebels', tt('campaint.rebel_type'), 'brigands')}
      ${box('resources', tt('common.resources'), tt('campaint.gold_wine'), tt('campaint.comma_separated'))}
      ${box('religions', tt('common.religions'), tt('campaint.catholic_100'), tt('campaint.religions_hint'))}
      <div class="cprow">
        <button class="primary" onclick="cpaintWizStart()">${tt('campaint.open_it_and_paint')}</button>
        <button onclick="cpaintWizCancel()">${tt('common.cancel')}</button></div>
    </div>`;
  }
  const pr = p.prog || {tiles: 0, settlement: null, port: null};
  const bad = (p.wizFindings || []).filter(f => f.fatal);
  const soft = (p.wizFindings || []).filter(f => !f.fatal);
  const step = (n, done, label, extra) => `<div class="cpstep${done ? ' done' : ''}">
    <b>${done ? '✓' : n}</b><span>${label}</span>${extra || ''}</div>`;
  return `<div class="cpwiz">
    <div class="k">${tt('campaint.rgb',{name:esc(spec.name),x:spec.rgb.join(', '),settlement:esc(spec.settlement)})}</div>
    ${step(1, true, tt('campaint.the_record_is_open'), spec.shown && spec.settlement_shown
      ? `<span class="count">${tt('campaint.built_by_held_by',{shown:esc(spec.shown),settlement_shown:esc(spec.settlement_shown),x:esc(cpaintFac(spec.faction)),x2:esc(cpaintFac(spec.owner || 'slave')),x3:p.wizMusic
          ? tt('campaint.plays_music',{music:esc(p.wizMusic)}) : ''})}</span>`
      : `<span class="w-bad" title="${ttA('campaint.the_game_asserts_on_a_province')}">${tt('campaint.a_shown_name_is_missing')}</span>`)}
    ${step(2, pr.tiles > 0, tt('campaint.paint_the_province'),
      `<span class="count">${ttN('campaint.tile_count',pr.tiles)}</span>`)}
    ${step(3, !!pr.settlement, tt('campaint.place_the_settlement_pixel'),
      `<button class="cpmk${p.marker === 'settlement' ? ' on' : ''}"
        data-marker="settlement">${pr.settlement
        ? `at ${pr.settlement.join(', ')}` : 'place'}</button>`)}
    ${step(4, !!pr.port, tt('campaint.place_the_port_pixel_or_skip'),
      `<button class="cpmk${p.marker === 'port' ? ' on' : ''}"
        data-marker="port">${pr.port ? `at ${pr.port.join(', ')}` : 'place'}</button>`)}
    ${bad.map(f => `<div class="w-bad">${esc(f.message)}</div>`).join('')}
    ${(p.wizPlanErrors || []).map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${soft.map(f => `<div class="w-warn">${esc(f.message)}</div>`).join('')}
    <div class="cprow"><button onclick="cpaintWizCancel()">${tt('campaint.drop_this_region')}</button>
      <button onclick="cpaintProgress()" title="${ttA('campaint.count_the_pixels_again')}">${tt('campaint.recheck')}</button>
    </div>
  </div>`;
}

function cpaintFootHtml(){
  const p = state.cpaint, st = p.st;
  return `${p.err ? `<div class="w-bad cpnote">${esc(p.err)}</div>` : ''}
    ${p.note ? `<div class="w-warn cpnote">${esc(p.note)}</div>` : ''}
    <div class="cprow cpundo">
      <button ${st.undo ? '' : 'disabled'} onclick="cpaintUndo()"
        title="${esc(st.last || tt('campaint.nothing_to_undo'))} (Ctrl+Z)"
        >${tt('campaint.undo',{x:st.undo ? ` (${st.undo})` : ''})}</button>
      <button ${st.redo ? '' : 'disabled'} onclick="cpaintRedo()"
        title="${esc(st.next || tt('campaint.nothing_to_redo'))} (Ctrl+Y)"
        >${tt('campaint.redo',{x:st.redo ? ` (${st.redo})` : ''})}</button>
      <span class="count">${st.last ? esc(st.last) : tt('campaint.no_stroke_yet')}</span>
    </div>
    ${st.dropped ? `<div class="count">${ttN('campaint.of_the_oldest_stroke_been_let',st.dropped)}</div>` : ''}
    ${(st.dirty.length || st.new_region) ? `<div class="cprow">
      <button class="primary" onclick="cpaintSave()">${tt('campaint.save_the_map')}</button>
      <button onclick="cpaintDiscard()"
        title="${ttA('campaint.re_read_every_layer_from_disk')}"
        >${tt('campaint.discard')}</button>
      <span class="count">${esc(st.files.join(', ')) || 'descr_regions.txt'}</span>
    </div>` : `<div class="count">${tt('campaint.nothing_is_unsaved_map_rwm_is')}</div>`}`;
}

//: 28b: wires whichever box it is handed - the panel or the toolbar row - so
//: the same five controls behave the same in both places and neither file
//: knows where the other one put them.
function cpaintWireIn(box){
  if(!box) return;
  const p = state.cpaint;
  box.querySelectorAll('[data-tool]').forEach(b => b.onclick = () => {
    p.tool = b.dataset.tool; p.marker = '';
    if(p.tool === 'water') p.target = 'regions';
    cpaintPaint();
  });
  const sz = box.querySelector('[data-size]');
  if(sz) sz.oninput = () => {
    p.size = +sz.value;
    // no repaint: the slider has the pointer, and rebuilding the row under it
    // drops the drag. Both copies of the number are written instead.
    document.querySelectorAll('.cpszn').forEach(n => n.textContent = sz.value + ' across');
  };
  box.querySelectorAll('[data-shape]').forEach(b => b.onclick = () => {
    p.shape = b.dataset.shape; cpaintPaint();
  });
  // 49: one button per layer, in the dock, in place of the toolbar's <select>
  box.querySelectorAll('[data-target-btn]').forEach(b => b.onclick = () => {
    p.target = b.dataset.targetBtn; p.marker = ''; p.rgb = null; cpaintPaint();
  });
  const fl = box.querySelector('[data-filter]');
  if(fl) fl.oninput = () => {
    p.filter = fl.value;
    // the list is the point of the box, so this one does repaint - and it
    // puts the caret back where it was, because the box is inside what it redrew
    const at = fl.selectionStart;
    cpaintPaint();
    const again = document.querySelector('[data-filter]');
    if(again){ again.focus(); again.setSelectionRange(at, at); }
  };
  box.querySelectorAll('[data-region]').forEach(b => b.onclick = () => {
    p.region = b.dataset.region; p.sea = false; p.marker = ''; cpaintPaint();
  });
  const sea = box.querySelector('[data-sea]');
  if(sea) sea.onclick = () => { p.sea = !p.sea; p.marker = ''; cpaintPaint(); };
  box.querySelectorAll('[data-rgb]').forEach(b => b.onclick = () => {
    p.rgb = b.dataset.rgb.split(',').map(Number); cpaintPaint();
  });
  box.querySelectorAll('[data-marker]').forEach(b => b.onclick = () =>
    cpaintMarker(b.dataset.marker));
  box.querySelectorAll('[data-wiz]').forEach(inp => inp.oninput = inp.onchange =
    () => cpaintWizSet(inp.dataset.wiz, inp.value));
}

/* ---------- 28b: the controls that make a stroke, over the map ----------

   **A stroke is made with the eyes on the map**, and a control you look away
   from to reach is a control you lose the stroke to. Mylae's `MapPaintToolbar`
   is his brush controls as a strip across the top of his canvas and that is
   plainly the right place for them, so the arm button, the five tools, the size
   and shape and the target layer moved out of `#cmPaint` and onto `.cmbar`,
   which has carried Fit, 1:1, the zooms, Names, Labels and Reset over the stage
   since 16c. A second row on a toolbar that exists, not a new piece of
   furniture.

   **What stayed in the panel is what you read rather than reach for**: the
   palette, the new-region wizard, undo and redo, the save, and the count of
   what is unsaved. 28a has just given all of it a tab.

   **Two of the five tools have no counterpart in his row and neither is worth
   losing to a copy of it**: the water brush, which writes regions, heights and
   ground types together in the sea colours measured off this map, and a pipette
   that selects the region on the region layer rather than only taking a colour.
   His row is pencil, bucket and pipette plus a heights mode, which is our
   palette one level down. */

//: Whether the second row is showing. A habit, so it rides in
//: `cmapLayerState` with the rest and a named view puts it back - unlike
//: `p.on`, which arms the brush and is a thing somebody is doing right now.
function cpaintRowOpen(){
  const m = state.settings && state.settings.map_layers;
  return !m || m.paint_row !== false;
}

function cpaintRowToggle(){
  const m = cmapSettings();
  m.paint_row = !cpaintRowOpen();
  cpaintBarPaint();
  cmapSaveLayers();
}

//: The toolbar's paint controls, repainted on their own so that a stroke does
//: not redraw the side panel and a palette click does not redraw the bar.
function cpaintBarPaint(){
  cpaintWorkspacePaint();
  const bar = document.getElementById('cmBar');
  if(bar) bar.classList.toggle('painting', !!(state.cpaint && state.cpaint.on));
  const el = document.getElementById('cmPaintBar');
  if(!el) return;
  el.innerHTML = cpaintBarHtml();
  cpaintWireIn(el);
}

// Paint state and recovery actions stay reachable from every inspector tab.
function cpaintWorkspacePaint(){
  const el = document.getElementById('cmWorkState'), p = state.cpaint;
  if(!el || !p) return;
  const st = p.st, dirty = !!(st.dirty.length || st.new_region);
  const locked = p.busy || p.painting;
  el.classList.toggle('is-painting', !!p.on);
  el.innerHTML = `<div class="cmworkmode"><span class="cmstatedot"></span>
    <b class="cmselectionname">${p.on ? tt('campaint.painting') : state.cmap && state.cmap.sel
      ? esc(state.cmap.sel.shown || state.cmap.sel.name || tt('campaint.selected_region')) : tt('campaint.select_a_region')}</b>
    <span>${p.on ? tt('campaint.tool_right_drag_to_pan',{tool:p.pal ? esc(cpaintToolName()) : tt('campaint.loading_palette')}) : tt('campaint.click_a_province_to_inspect_drag')}</span>
    ${p.on ? `<button onclick="cpaintToggle()">${tt('campaint.stop_painting')}</button>` : ''}</div>
    <div class="cmworksave">
      <span role="status">${p.busy ? tt('common.working') : dirty ? tt('campaint.unsaved_map_changes') : tt('campaint.paint_changes_saved')}</span>
      <button onclick="cpaintUndo()" ${locked || !st.undo ? 'disabled' : ''} title="${esc(st.last || tt('campaint.nothing_to_undo_2'))}">${tt('campaint.undo_2')}</button>
      <button onclick="cpaintRedo()" ${locked || !st.redo ? 'disabled' : ''} title="${esc(st.next || tt('campaint.nothing_to_redo_2'))}">${tt('campaint.redo_2')}</button>
      <button class="primary" onclick="cpaintSave()" ${locked || !dirty ? 'disabled' : ''}>${tt('campaint.review_save')}</button>
    </div>`;
}

// A right-click samples the province for the next stroke without arming paint.
function cpaintPickRegion(region){
  const p = state.cpaint;
  if(!p || !region || !region.name) return;
  p.region = region.name;
  p.target = 'regions';
  p.sea = false; p.marker = ''; p.rgb = null; p.filter = '';
  if(p.tool === 'water' || p.tool === 'pipette') p.tool = 'brush';
  cpaintPaint();
}

function cpaintSelectRegion(){
  if(!state.cmap || !state.cpaint) return;
  if(state.cpin && typeof cpinCancel === 'function') cpinCancel();
  if(state.cpaint.on) cpaintToggle();
  state.cmap.selectMode = true;
  cmapSub('place', 'record');
  cpaintBarPaint();
}

function cpaintBarHtml(){
  const p = state.cpaint;
  if(!p) return '';
  const open = cpaintRowOpen();
  const arm = `<button class="cptog${p.on ? ' on' : ''}" onclick="cpaintToggle()"
      title="${ttA('campaint.arm_the_brush_the_left_button')}"
      >${tt('campaint.paint_2',{on:p.on ? ' ✓' : ''})}</button>`;
  if(!p.on) return `<button class="${state.cmap && state.cmap.selectMode ? 'on' : ''}"
    aria-pressed="${!!(state.cmap && state.cmap.selectMode)}" onclick="cpaintSelectRegion()"
    title="${ttA('campaint.select_a_province_without_moving_map')}">${tt('campaint.select_region')}</button>` + arm;
  if(p.palErr) return arm + `<span class="w-bad">${esc(p.palErr)}</span>`;
  if(!p.pal) return arm + `<span class="count">${tt('campaint.reading_the_palettes')}</span>`;
  const fold = `<button class="cpfold" onclick="cpaintRowToggle()"
      title="${open ? tt('campaint.fold_the_tools_away_and_keep')
                    : tt('campaint.show_the_tools_again')}">${open ? '▴' : '▾'}</button>`;
  if(!open) return arm + fold + `<span class="count">${esc(cpaintToolName())}</span>`;
  // 49: the target layer left this row for the dock on the left, where the
  // colours it decides are. The folded summary below still names it.
  return arm + fold + cpaintToolsHtml() + cpaintSizeHtml();
}

//: What the folded row says instead of showing itself: which tool is up, and
//: what it is about to write. The bar is the only place either is said now.
function cpaintToolName(){
  const p = state.cpaint;
  const t = CPAINT_TOOLS.find(x => x[0] === p.tool);
  const L = p.tool === 'water' ? null : cpaintLayer();
  return (p.marker ? p.marker : t ? t[2] : p.tool)
    + (L ? ` · ${L.label}` : '');
}

/* ---------- keys ---------- */

/* Ctrl+Z and Ctrl+Y, taken from undo.js while the brush is armed.

   In the CAPTURE phase, and that is the whole trick: undo.js binds its handler
   at the document too, four files earlier, and a listener added later cannot
   stop one added first from running. Capture runs before every bubble listener
   whatever the order, so this is the one way for the paint stack to own the
   keys without moving anything in undo.js. It only claims them while the brush
   is armed and the caret is not in a box; the region form's own Ctrl+Z is
   untouched the rest of the time. */
document.addEventListener('keydown', e => {
  if(!cpaintArmed()) return;
  const t = (e.target && e.target.tagName) || '';
  if(t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
  const k = (e.key || '').toLowerCase();
  if(e.ctrlKey || e.metaKey){
    if(k !== 'z' && k !== 'y') return;
    e.preventDefault(); e.stopPropagation();
    if(k === 'y' || e.shiftKey) cpaintRedo(); else cpaintUndo();
    return;
  }
  if(e.altKey) return;
  const tool = {b: 'brush', p: 'pencil', g: 'bucket', i: 'pipette', w: 'water'}[k];
  if(tool){
    e.preventDefault(); e.stopPropagation();
    state.cpaint.tool = tool; state.cpaint.marker = '';
    if(tool === 'water') state.cpaint.target = 'regions';
    cpaintPaint();
  }else if(k === '[' || k === ']'){
    e.preventDefault();
    const p = state.cpaint;
    p.size = Math.max(1, Math.min(p.pal ? p.pal.brush_max : 33,
                                  p.size + (k === ']' ? 2 : -2)));
    cpaintPaint();
  }
}, true);
