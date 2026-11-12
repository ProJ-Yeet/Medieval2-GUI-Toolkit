/* Armory Studio - Pre-render lighting.

   A lit colour texture for each colour texture the chosen objects wear: the
   colour, its spec map (red metal, green gloss, blue ambient occlusion) and
   its normal map, with an ambient light and a key light painted in, on the
   object's own UVs. Not the export's bake, which packs the sheets: this one
   changes what an object wears, and the export then packs that.

   The work is armlit.py on the server. While the panel is open the viewport
   draws the chosen objects under the same ambient and key light, with the
   bake's own numbers, so a slider shows what it does as it moves. Shadows,
   the spec map and the normal map are only in the baked texture: after a
   bake the objects are drawn with that texture and no light over it, until a
   slider moves again.

   On an object: o.sheet is the lit texture, o.lit = {src, settings} what it
   wore before (null: its source's own) and how it was lit, so a second bake
   starts from the source and Remove puts it back. */

const ARM_LIT_DEFAULT = {ambient: 0.8, key: true, direction: 30, height: 50, softness: 0.5,
                         strength: 0.5, shadows: 0.5, flip_green: false};
// each slider: its range and step
const ARM_LIT_RANGES = {ambient: [0, 2, 0.01], direction: [-180, 180, 1], height: [-90, 90, 1],
                        softness: [0, 1, 0.01], strength: [0, 3, 0.01], shadows: [0, 1, 0.01]};

function armLit(){ return ARM.lit = ARM.lit || {open: false, live: true, busy: false}; }
function armLitOpts(){
  const s = (state.settings || {}).armory_lit;
  return Object.assign({}, ARM_LIT_DEFAULT, s && typeof s === 'object' ? s : {});
}
// quiet: a slider on its way (drawn, not saved yet)
function armLitSet(k, v, quiet){
  const o = armLitOpts();
  o[k] = v;
  state.settings = state.settings || {};
  state.settings.armory_lit = o;
  armLit().live = true;
  if(!quiet) api.post('/api/settings', {armory_lit: o}).catch(() => {});
  const out = typeof document !== 'undefined' && document.getElementById('armLitVal_' + k);
  if(out) out.textContent = v;
  armFrame();
}
// the selected objects, or every visible one when none is
function armLitTargets(){
  const sel = armSelected();
  return sel.length ? sel : armVisibleObjects();
}
function armLitToggle(){
  const l = armLit();
  l.open = !l.open;
  l.live = true;
  armPaintObjects();
  armFrame();
}

/* --- what the viewport draws ------------------------------------------------- */

// 0: the viewport's own light; 1: the bake's light, live; 2: the baked texture as it is
function armLitMode(ob){
  const l = armLit();
  if(!l.open || !armLitTargets().includes(ob)) return 0;
  return ob.lit && !l.live ? 2 : 1;
}
// the sheet an object is drawn with: under the live light, what it wore before the bake
function armLitSheetOf(ob){
  return ob.lit && armLitMode(ob) === 1 ? (ob.lit.src || null) : (ob.sheet || null);
}
// towards the key light, in the page's space (the viewport mirrors x: ARM_MIRROR)
function armLitDir(){
  const o = armLitOpts(), a = o.direction * Math.PI / 180, h = o.height * Math.PI / 180;
  return [-Math.cos(h) * Math.sin(a), Math.sin(h), Math.cos(h) * Math.cos(a)];
}
// the light's uniforms for a frame (armRender)
function armLitUniforms(gl, L){
  const o = armLitOpts();
  gl.uniform1f(L.uLitAmb, o.ambient);
  gl.uniform1f(L.uLitStr, o.key ? o.strength : 0);
  gl.uniform1f(L.uLitSoft, o.softness);
  gl.uniform3fv(L.uLitDir, armLitDir());
}

/* --- the panel ---------------------------------------------------------------- */

function armLitHtml(){
  const l = armLit(), o = armLitOpts(), objs = armLitTargets();
  const lit = objs.filter(x => x.lit);
  const range = (k, label, title) => { const r = ARM_LIT_RANGES[k]; return `<label class="armrange" title="${esc(title || '')}">
      <span>${label} <span class="count" id="armLitVal_${k}">${o[k]}</span></span>
      <input type="range" min="${r[0]}" max="${r[1]}" step="${r[2]}" value="${o[k]}"
        oninput="armLitSet('${k}', +this.value, true)" onchange="armLitSet('${k}', +this.value)"></label>`; };
  const box = (k, label, title) => `<label class="armcheck" title="${esc(title || '')}"><input type="checkbox"${o[k] ? ' checked' : ''}
      onchange="armLitSet('${k}', this.checked); armPaintObjects()"> ${label}</label>`;
  return `<div class="armlit">
    <div class="armsect">${tt('armory.lit')}</div>
    <div class="count armnote">${tt('armory.lit_intro')}</div>
    <div class="armpropsrow">${range('ambient', tt('armory.lit_ambient'), tt('armory.lit_ambient_title'))}</div>
    <div class="armpropsrow">${box('key', tt('armory.lit_key'), tt('armory.lit_key_title'))}</div>
    ${o.key ? `<div class="armpropsrow">${range('direction', tt('armory.lit_direction'), tt('armory.lit_direction_title'))}
      ${range('height', tt('armory.lit_height'), tt('armory.lit_height_title'))}</div>
    <div class="armpropsrow">${range('strength', tt('armory.strength'))}
      ${range('softness', tt('armory.lit_softness'), tt('armory.lit_softness_title'))}</div>
    <div class="armpropsrow">${range('shadows', tt('armory.lit_shadows'), tt('armory.lit_shadows_title'))}</div>` : ''}
    <div class="armpropsrow">${box('flip_green', tt('armory.lit_flip_green'), tt('armory.lit_flip_green_title'))}</div>
    <div class="count armnote">${tt('armory.lit_live_note')}</div>
    <div class="armpropsrow"><span class="count">${ttN('armory.opt_scope', objs.length)}</span><span style="flex:1"></span>
      ${lit.length ? `<button class="mini" onclick="armLitRemove()" title="${esc(tt('armory.lit_remove_title'))}">${tt('armory.lit_remove')}</button>` : ''}
      <button class="primary" id="armLitGo" onclick="armLitRun()"${objs.length && !l.busy ? '' : ' disabled'}>${l.busy ? tt('armory.working') : tt('armory.lit_bake')}</button></div>
  </div>`;
}

async function armLitRun(){
  const l = armLit(), objs = armLitTargets(), st = armLitOpts();
  if(!objs.length || l.busy) return;
  l.busy = true;
  armPaintObjects();
  let r;
  try{
    r = await api.post('/api/armory/lit', {project: armProj(), ids: objs.map(o => o.id), settings: st});
    if(r.error) throw new Error(r.error);
  }catch(e){ l.busy = false; toast(errText(e), 6000); armPaintObjects(); return; }
  l.busy = false;
  let n = 0;
  for(const b of r.baked || []){
    ARM.sheetAllowed.add(b.path);
    ARM.sheetCache.delete(b.path);            // the file was written again: read it again
    ARM.sheetStamp[b.path] = Date.now();
    for(const id of b.objects || []){
      const o = armObj(id);
      if(!o) continue;
      // what it wore before its first bake, so a second one starts there too
      const src = o.lit ? o.lit.src : (o.sheet || null);
      o.lit = {src, settings: st};
      o.sheet = b.path;
      n++;
    }
  }
  if(n) l.live = false;
  const skipped = (r.skipped || []).map(s => {
    const o = armObj(s.id);
    const name = o ? o.name : s.id;
    return s.why === 'two_sheets' ? tt('armory.lit_skip_two_sheets', {name}) : tt('armory.lit_skip_no_texture', {name});
  });
  toast(skipped.length ? skipped.join(' ') : ttN('armory.lit_done', n), skipped.length ? 8000 : 3000);
  armRepaint();
}

// each object back in what it wore before the bake; the lit files stay on disk
function armLitRemove(ids){
  const objs = ids ? ids.map(armObj).filter(Boolean) : armLitTargets();
  for(const o of objs){
    if(!o.lit) continue;
    o.sheet = o.lit.src || null;
    delete o.lit;
  }
  armLit().live = true;
  armRepaint();
}
