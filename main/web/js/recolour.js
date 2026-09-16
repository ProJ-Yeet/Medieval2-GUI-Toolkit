/* recolour.js - Campaign Map: changing the colour a province is painted in

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   CHANGE A REGION'S COLOUR - Phase 36, D1.

   Every name here starts `rcl`. Python owns every rule - which colours are
   refused, how many tiles move, what the save writes - and this file is the
   picker and the sentence that goes with it.

   IT DOES NOT RENUMBER, AND SAYING SO IS THE POINT. The create wizard warns
   that a new province renumbers, and the delete warns that removing one does.
   Somebody who has read those two will assume a recolour does too, and it does
   not: a region ID is the order a colour is first met scanning map_regions.tga,
   so it is a fact about where the pixels ARE, and a recolour moves no pixel.
   Measured at zero IDs moved on both installed maps. The panel says it before
   the button rather than in the confirm, because it is the reason to press it.

   THE ONE COLOUR THAT WOULD RENUMBER IS ANOTHER PROVINCE'S, and that is refused
   rather than warned about, because it is not a recolour at all - it is a merge
   that takes a province off the map. Python says so in the refusal; this file
   only shows it.

   THE PIXELS GO DOWN UNSAVED. A recolour is one stroke on the paint session's
   undo stack, so Undo takes it back and the Paint panel's own Save is what
   writes it - together with the record's colour line, which is the half this
   screen cannot do on its own. Two writes, one save, or the mod is broken. */

/* ---------- state ---------- */

function rclNew(mod, campaign, name, rgb){
  return {mod, campaign, name, was: (rgb || [128, 128, 128]).slice(),
          rgb: (rgb || [128, 128, 128]).slice(), busy: false, err: '', done: null};
}

/* Open the dialog for the province the panel is showing. The colour it opens on
   is the one the province already has, so the picker starts where the eye is. */
function rclOpen(name){
  const c = state.cmap, d = c && c.det;
  if(!c || !d) return;
  state.rcl = rclNew(c.mod, c.campaign || '', name || d.name, d.rgb);
  rclPaint();
}

function rclClose(){
  state.rcl = null;
  rclPaint();
}

function rclSet(i, value){
  const k = state.rcl;
  if(!k) return;
  const n = Math.max(0, Math.min(255, parseInt(value, 10) || 0));
  k.rgb[i] = n;
  k.err = '';
  rclPaint();
}

//: The picker and the three numbers are one value, the same ruling the climate
//: form makes: a colour typed as three numbers is a colour nobody can see.
function rclHex(rgb){
  return '#' + rgb.map(v => Math.max(0, Math.min(255, v | 0))
    .toString(16).padStart(2, '0')).join('');
}

function rclFromHex(hex){
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if(!m) return;
  const n = parseInt(m[1], 16);
  const k = state.rcl;
  if(!k) return;
  k.rgb = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  k.err = '';
  rclPaint();
}

/* Repaint. Nothing is written to disk here: the stroke goes onto the paint
   session and the Paint panel's Save is what commits it, with the record's
   colour line in the same backup set. */
async function rclApply(){
  const k = state.rcl;
  if(!k || k.busy) return;
  k.busy = true; k.err = '';
  rclPaint();
  let res;
  try{
    res = await api.post('/api/map/recolour',
      {mod: k.mod, campaign: k.campaign, region: k.name, rgb: k.rgb});
  }catch(e){
    res = {error: errText(e)};
  }finally{
    k.busy = false;
  }
  if(res.error){ k.err = res.error; rclPaint(); return; }
  k.done = {tiles: res.tiles || 0, protected: res.protected || 0};
  activity('recolour',
    `${k.mod}: ${k.name} -> ${k.rgb.join(' ')} (${k.done.tiles} tiles)`);
  toast(`${k.name}: ${k.done.tiles.toLocaleString()} tile`
    + `${k.done.tiles === 1 ? '' : 's'} repainted. Not saved yet - `
    + 'Save on the Paint panel writes the pixels and the record together.', 8000);
  rclPaint();
  // The tiles the stroke changed, written into the browser's own copy of the
  // layer - the same road every brush stroke takes, which is why the map under
  // the dialog updates without re-reading anything from the server.
  if(res.changed) cpaintApply(res.changed);
  if(typeof cpaintPaint === 'function') cpaintPaint();
}

/* ---------- drawing ---------- */

function rclPaint(){
  const el = document.getElementById('cmRecolour');
  if(!el) return;
  el.innerHTML = rclHtml();
}

function rclHtml(){
  const k = state.rcl;
  if(!k) return '';
  const same = k.rgb.join(' ') === k.was.join(' ');
  return `<div class="modal" onclick="if(event.target===this)rclClose()">
    <div class="mbox rclbox">
      <div class="k">Change the colour of ${esc(k.name)}
        <span class="count">map_regions.tga, and the colour line of its
          record</span></div>

      <div class="rclrow">
        <span class="rclsw" style="background:rgb(${k.was.join(',')})"></span>
        <span class="count">now ${k.was.join(' ')}</span>
        <span class="rclarrow">→</span>
        <span class="rclsw" style="background:rgb(${k.rgb.join(',')})"></span>
        <input type="color" value="${rclHex(k.rgb)}"
          oninput="rclFromHex(this.value)">
        ${[0, 1, 2].map(i => `<input type="number" min="0" max="255"
          value="${k.rgb[i]}" oninput="rclSet(${i}, this.value)">`).join('')}
      </div>

      <div class="count rclnote">Every tile of the old colour is repainted,
        wherever it is on the map - not just the piece under the pointer. A
        province is not always one connected blob.</div>

      <div class="w-ok rclnote"><b>No region ID moves.</b> An ID is the order a
        colour is first met scanning map_regions.tga, so it says where a
        province's tiles are, not what colour they carry - and a recolour moves
        no tile. A script that names a region by number still names the same
        one. (Creating or deleting a province is the case that does renumber.)</div>

      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${k.done ? `<div class="w-ok"><b>${k.done.tiles.toLocaleString()} tile${
        k.done.tiles === 1 ? '' : 's'} repainted.</b> Nothing is on disk yet:
        <b>Save</b> on the Paint panel writes the pixels and the record's
        colour line together, in one backup set.</div>` : ''}

      <div class="mrow">
        <span class="sp"></span>
        ${k.done
          ? `<button class="primary" onclick="rclClose()">Done</button>`
          : `<button onclick="rclClose()">Cancel</button>
             <button class="primary" ${same || k.busy ? 'disabled' : ''}
               onclick="rclApply()">${k.busy ? 'Repainting…' : 'Repaint'}</button>`}
      </div>
    </div>
  </div>`;
}
