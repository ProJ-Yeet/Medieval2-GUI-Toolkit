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
  p.on = !p.on;
  p.err = ''; p.note = '';
  activity('map paint', p.on ? 'armed the brush' : 'put the brush down');
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
  let r;
  try{ r = await api.post(`/api/map/${action}`, Object.assign({mod: p.mod}, body)); }
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
  try{ r = await api.get(`/api/map/probe?mod=${enc(p.mod)}&x=${tx}&y=${ty}`); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  if(state.cpaint !== p) return;
  const L = (r.layers || []).find(l => l.code === p.target);
  if(!L || !L.rgb){ toast(`✗ ${p.target} has no value at ${tx},${ty}`, 5000); return; }
  if(p.target === 'regions'){
    const reg = c.byKey.get((L.rgb[0] << 16) | (L.rgb[1] << 8) | L.rgb[2]);
    if(reg && reg.name){ p.region = reg.name; p.sea = false; }
    else if(r.sea){ p.sea = true; p.region = ''; }
    else { toast('✗ that tile is not painted any declared region’s colour', 5000); return; }
  }else{
    p.rgb = L.rgb.slice();
  }
  toast(`Picked ${L.name || L.rgb.join(', ')}`);
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
   a visible pause; one getImageData over the bounding box, the writes, and one
   putImageData is a few milliseconds. The bounding box matters as much as the
   single call - a pencil dot should not read and write the whole map. */
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
  const ctx = state.cmap.layers[code].px;
  const im = ctx.getImageData(x0, y0, w, h), d = im.data;
  for(const run of runs){
    const r = (run.rgb >> 16) & 255, g = (run.rgb >> 8) & 255, b = run.rgb & 255;
    for(let i = 0; i < run.xy.length; i += 2){
      const p = ((run.xy[i + 1] - y0) * w + (run.xy[i] - x0)) * 4;
      d[p] = r; d[p + 1] = g; d[p + 2] = b; d[p + 3] = 255;
    }
  }
  ctx.putImageData(im, x0, y0);
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
  if(p.st.undo && !confirm(`Throw away ${p.st.undo} unsaved stroke`
      + `${p.st.undo === 1 ? '' : 's'}?\n\nThe layers are re-read from disk. `
      + 'Nothing that has been saved is affected.')) return;
  await cpaintPost('paint_discard', {});
  toast('The map was re-read from disk.');
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
  if(!confirm(`Write: save the painted map?\n\n`
    + ((q.changes || []).join('\n') || 'no visible change')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nmap.rwm is deleted too, or the game loads the old compiled map and '
    + 'shows none of this.\n\nBacked up first, and 🕑 Log can undo the whole '
    + 'save in one go.')) return;
  const res = await cpaintPost('paint_apply', {});
  if(!res) return;
  if(res.error){ toast('✗ ' + res.error, 9000); cpaintPaint(); return; }
  toast(`Saved ${(res.layers || []).length} layer`
    + `${(res.layers || []).length === 1 ? '' : 's'}`
    + (res.region ? ` and the record for ${res.region}` : '')
    + '. map.rwm deleted. 🕑 Log can undo it.', 6000);
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

function cpaintWizOpen(){
  const p = state.cpaint, c = state.cmap;
  if(p.st.new_region){ p.wizOpen = true; cpaintPaint(); return; }
  p.wiz = {name: '', settlement: '', rgb: cpaintFreeColour(), faction: '',
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
    faction: w.faction.trim(), rebels: w.rebels.trim(),
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
  toast(`${spec.name} is open. Paint it, then place its settlement pixel.`, 6000);
  cpaintProgress();
}

async function cpaintWizCancel(){
  const p = state.cpaint;
  if(p.st.new_region && !confirm('Drop the new region’s record?\n\n'
      + 'Any tiles already painted its colour stay painted. Undo those '
      + 'separately, or they become a province nothing declares.')) return;
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

function cpaintPaint(){
  const el = document.getElementById('cmPaint');
  if(!el) return;
  el.innerHTML = cpaintHtml();
  cpaintWire();
}

function cpaintHtml(){
  const p = state.cpaint;
  if(!p) return '';
  const st = p.st;
  const unsaved = st.undo || st.dirty.length || st.new_region;
  const head = `<div class="cpbar">
    <button class="cptog${p.on ? ' on' : ''}" onclick="cpaintToggle()"
      title="Arm the brush. The left button paints; the right and middle still pan."
      >\u{1F58C} Paint${p.on ? ' ✓' : ''}</button>
    ${unsaved ? `<span class="cpun" title="${esc(st.files.join(', '))}">${
      st.undo} stroke${st.undo === 1 ? '' : 's'}${st.dirty.length
        ? ` · ${st.dirty.length} layer${st.dirty.length === 1 ? '' : 's'}` : ''
      } unsaved</span>` : ''}
  </div>`;
  if(!p.on) return head;
  if(p.palErr) return head + `<div class="cppanel"><div class="w-bad">${
    esc(p.palErr)}</div></div>`;
  if(!p.pal) return head + `<div class="cppanel"><span class="count">reading the
    palettes…</span></div>`;
  return head + `<div class="cppanel">
    ${cpaintToolsHtml()}
    ${cpaintTargetHtml()}
    ${cpaintPaletteHtml()}
    ${cpaintWizHtml()}
    ${cpaintFootHtml()}
  </div>`;
}

const CPAINT_TOOLS = [
  ['pencil', '✏', 'Pencil', 'One tile per click or drag'],
  ['brush', '\u{1F58C}', 'Brush', 'A disc or square of tiles, joined along the drag'],
  ['bucket', '\u{1FAA3}', 'Bucket', 'Flood-fill every tile of one colour joined to '
    + 'this one, four-connected'],
  ['pipette', '\u{1F489}', 'Pipette', 'Read the tile: on the region layer it '
    + 'selects the region, on the others it takes the colour'],
  ['water', '\u{1F30A}', 'Water', 'Demir’s water brush: regions, heights and '
    + 'ground types together, in this map’s own sea colours'],
];

function cpaintToolsHtml(){
  const p = state.cpaint;
  const w = p.pal.water || {};
  const rows = CPAINT_TOOLS.map(([code, glyph, label, why]) =>
    `<button class="cptool${p.tool === code && !p.marker ? ' on' : ''}"
      data-tool="${code}" title="${esc(label)}: ${esc(why)}"
      >${glyph}<span>${esc(label)}</span></button>`).join('');
  const sized = CPAINT_SIZED.indexOf(p.tool) >= 0 && !p.marker;
  return `<div class="cptools">${rows}</div>
    ${sized ? `<div class="cprow">
      <label class="cpsz">Size
        <input type="range" min="1" max="${p.pal.brush_max}" step="2"
          value="${p.size}" data-size></label>
      <b class="cpszn">${p.size} across</b>
      <button class="cpshape${p.shape === 'round' ? ' on' : ''}" data-shape="round"
        title="A disc">●</button>
      <button class="cpshape${p.shape === 'square' ? ' on' : ''}" data-shape="square"
        title="A square">■</button>
    </div>` : ''}
    ${p.tool === 'water' ? `<div class="cpnote">${w.ok
      ? `Writes ${Object.keys(w.layers).length} layers at once, in the colours
         <b>measured off this map</b>: ${Object.keys(w.layers).map(c =>
         `<i style="background:rgb(${w.layers[c].rgb.join(',')})"></i>${esc(c)}`
         ).join(' ')} · from ${w.sea_tiles.toLocaleString()} sea tiles.
         Settlement and port pixels are left alone.`
      : `<span class="w-bad">${esc(w.problem
         || 'no tile of this map reads as sea, so there is no sea colour to use')
         }</span>`}</div>` : ''}`;
}

function cpaintTargetHtml(){
  const p = state.cpaint;
  if(p.tool === 'water') return '';
  const opts = p.pal.layers.map(L =>
    `<option value="${L.code}"${L.code === p.target ? ' selected' : ''}${
      L.problem ? ' disabled' : ''}>${esc(L.label)}${
      L.problem ? ' · ' + esc(L.problem) : ''}</option>`).join('');
  return `<div class="cprow"><label class="cptg">Layer
    <select data-target>${opts}</select></label></div>`;
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

function cpaintPaletteHtml(){
  const p = state.cpaint;
  if(p.tool === 'water') return '';
  const L = cpaintLayer();
  if(!L) return '';
  if(L.problem) return `<div class="cpnote w-bad">${esc(L.problem)}</div>`;
  const rgb = cpaintColour();
  const chosen = `<div class="cppick">
    <i style="background:${rgb ? `rgb(${rgb.join(',')})` : 'transparent'}"></i>
    <span>${rgb ? cpaintColourName() : '<span class="w-warn">nothing picked - a '
      + 'stroke would be refused, and say so</span>'}</span></div>`;

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
    return chosen + `<div class="cprow">
        <input class="cpsearch" placeholder="find a region…"
          value="${esc(p.filter)}" data-filter>
        <button class="cprg${p.sea ? ' on' : ''}" data-sea
          title="${w && w.layers && w.layers.regions
            ? 'The sea colour measured off this map: '
              + w.layers.regions.rgb.join(', ')
            : 'this map has no sea colour to measure'}"
          ${w && w.layers && w.layers.regions ? '' : 'disabled'}>${
          w && w.layers && w.layers.regions
            ? `<i style="background:rgb(${w.layers.regions.rgb.join(',')})"></i>`
            : ''}Sea</button>
        ${spec ? `<button class="cprg${spec.name === p.region ? ' on' : ''}"
          data-region="${esc(spec.name)}"><i style="background:rgb(${
          spec.rgb.join(',')})"></i>${esc(spec.name)} <span class="count">new</span
          ></button>` : ''}
      </div>
      <div class="cppal">${list || '<span class="count">no region matches</span>'}
      </div>
      ${rows.length > 400 ? `<div class="count">${rows.length} match; the first
        400 are listed. Type more of the name.</div>` : ''}
      <div class="cpnote">${esc(L.note)}</div>`;
  }

  const list = L.colours.map(k =>
    `<button class="cpsw2${rgb && k.key === ((rgb[0] << 16) | (rgb[1] << 8) | rgb[2])
      ? ' on' : ''}" data-rgb="${k.rgb.join(',')}"
      title="${esc(k.name || 'no table names this colour')} · ${k.rgb.join(', ')}${
      k.count ? ' · ' + k.count.toLocaleString() + ' tiles' : ''}"
      ><i style="background:rgb(${k.rgb.join(',')})"></i><span>${
      esc(k.name || k.rgb.join(', '))}</span></button>`).join('');
  return chosen + `<div class="cppal">${list}</div>
    <div class="cpnote">${esc(L.note)}${L.closed ? ''
      : ' A colour outside this list can still be written, because the layer has '
      + 'no table to hold it to.'}</div>`;
}

function cpaintColourName(){
  const p = state.cpaint;
  if(p.marker) return `the ${p.marker} marker pixel`;
  if(p.tool === 'water') return 'this map’s own sea, on three layers';
  if(p.target === 'regions')
    return p.sea ? 'Sea <span class="count">declared in no record</span>'
      : esc(p.region) + ' <span class="count">its own colour, out of '
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
      title="Add a province: decide its record, paint it, place its settlement, then its port or skip."
      >＋ New region</button></div>`;
  if(!spec){
    const w = p.wiz || {};
    const box = (slot, label, ph, hint) => `<div class="cpfield">
      <label>${esc(label)}${hint ? ` <span class="count">${hint}</span>` : ''}</label>
      <input value="${esc(w[slot] === undefined ? '' : String(w[slot]))}"
        placeholder="${esc(ph)}" data-wiz="${slot}"></div>`;
    return `<div class="cpwiz">
      <div class="k">A new province <span class="count">step 1 of 3: the record</span></div>
      ${box('name', 'Region name', 'New_Province', 'no spaces - it is a key')}
      ${box('settlement', 'Settlement name', 'Newtown', 'no spaces, same reason')}
      <div class="cpfield"><label>Colour on map_regions.tga
          <span class="count">free on this map</span></label>
        <div class="cprow"><i class="cpsw" style="background:rgb(${
          (w.rgb || [0, 0, 0]).join(',')})"></i>
        <input value="${(w.rgb || []).join(' ')}" data-wiz="rgb"></div></div>
      ${box('faction', 'Creator faction', 'slave')}
      ${box('rebels', 'Rebel type', 'brigands')}
      ${box('resources', 'Resources', 'gold, wine', 'comma separated')}
      ${box('religions', 'Religions', 'catholic 100', 'name percent, comma '
        + 'separated; they must total 100 or the game crashes on load')}
      <div class="cprow">
        <button class="primary" onclick="cpaintWizStart()">Open it, and paint</button>
        <button onclick="cpaintWizCancel()">Cancel</button></div>
    </div>`;
  }
  const pr = p.prog || {tiles: 0, settlement: null, port: null};
  const bad = (p.wizFindings || []).filter(f => f.fatal);
  const soft = (p.wizFindings || []).filter(f => !f.fatal);
  const step = (n, done, label, extra) => `<div class="cpstep${done ? ' done' : ''}">
    <b>${done ? '✓' : n}</b><span>${label}</span>${extra || ''}</div>`;
  return `<div class="cpwiz">
    <div class="k">${esc(spec.name)}
      <span class="count">rgb(${spec.rgb.join(', ')}) · ${
      esc(spec.settlement)}</span></div>
    ${step(1, true, 'The record is open')}
    ${step(2, pr.tiles > 0, `Paint the province`,
      `<span class="count">${pr.tiles.toLocaleString()} tile${
        pr.tiles === 1 ? '' : 's'}</span>`)}
    ${step(3, !!pr.settlement, 'Place the settlement pixel',
      `<button class="cpmk${p.marker === 'settlement' ? ' on' : ''}"
        data-marker="settlement">${pr.settlement
        ? `at ${pr.settlement.join(', ')}` : 'place'}</button>`)}
    ${step(4, !!pr.port, 'Place the port pixel, or skip it',
      `<button class="cpmk${p.marker === 'port' ? ' on' : ''}"
        data-marker="port">${pr.port ? `at ${pr.port.join(', ')}` : 'place'}</button>`)}
    ${bad.map(f => `<div class="w-bad">${esc(f.message)}</div>`).join('')}
    ${soft.map(f => `<div class="w-warn">${esc(f.message)}</div>`).join('')}
    <div class="cprow"><button onclick="cpaintWizCancel()">Drop this region</button>
      <button onclick="cpaintProgress()" title="Count the pixels again">Recheck</button>
    </div>
  </div>`;
}

function cpaintFootHtml(){
  const p = state.cpaint, st = p.st;
  return `${p.err ? `<div class="w-bad cpnote">${esc(p.err)}</div>` : ''}
    ${p.note ? `<div class="w-warn cpnote">${esc(p.note)}</div>` : ''}
    <div class="cprow cpundo">
      <button ${st.undo ? '' : 'disabled'} onclick="cpaintUndo()"
        title="${esc(st.last || 'nothing to undo')} (Ctrl+Z)"
        >↶ Undo${st.undo ? ` (${st.undo})` : ''}</button>
      <button ${st.redo ? '' : 'disabled'} onclick="cpaintRedo()"
        title="${esc(st.next || 'nothing to redo')} (Ctrl+Y)"
        >↷ Redo${st.redo ? ` (${st.redo})` : ''}</button>
      <span class="count">${st.last ? esc(st.last) : 'no stroke yet'}</span>
    </div>
    ${st.dropped ? `<div class="count">${st.dropped} of the oldest stroke${
      st.dropped === 1 ? ' has' : 's have'} been let go: the stack holds every
      level there is until it is holding too many pixels to be worth it.</div>` : ''}
    ${(st.dirty.length || st.new_region) ? `<div class="cprow">
      <button class="primary" onclick="cpaintSave()">Save the map</button>
      <button onclick="cpaintDiscard()"
        title="Re-read every layer from disk and lose the unsaved strokes"
        >Discard</button>
      <span class="count">${esc(st.files.join(', ')) || 'descr_regions.txt'}</span>
    </div>` : `<div class="count">Nothing is unsaved. map.rwm is deleted on
      every save, or the game loads the old compiled map.</div>`}`;
}

function cpaintWire(){
  const box = document.getElementById('cmPaint');
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
    const n = box.querySelector('.cpszn');
    if(n) n.textContent = sz.value + ' across'; // no repaint: the slider has focus
  };
  box.querySelectorAll('[data-shape]').forEach(b => b.onclick = () => {
    p.shape = b.dataset.shape; cpaintPaint();
  });
  const tg = box.querySelector('[data-target]');
  if(tg) tg.onchange = () => {
    p.target = tg.value; p.marker = ''; p.rgb = null; cpaintPaint();
  };
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
  box.querySelectorAll('[data-wiz]').forEach(inp => inp.oninput = () =>
    cpaintWizSet(inp.dataset.wiz, inp.value));
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
