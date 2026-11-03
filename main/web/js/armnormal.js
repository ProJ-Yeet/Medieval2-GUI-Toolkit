/* =========================================================================
   Armory Studio's normal maps (Phase 95j)

   The bake (armbake.py) writes a normal map beside each sheet. Three choices,
   kept on the project as `normals`:

     * SKIP        - a flat map, what the Blender kit ships;
     * GENERIC     - one setting for everything;
     * SPECIALIZED - a setting per material (95f's dropdown), and an object
                     may have its own on top.

   A setting is a strength, a blur and an invert. The map is made from the
   art's lightness as height, tilted against its slope at a gain measured on
   the normal maps the installed mods ship (armbake.NORMAL_GAIN). This file
   is the same arithmetic as armbake.normal_pixels, so the viewport's preview,
   drawn on each object's own crop of its sheet, is what gets baked.
   ========================================================================= */

const ARM_NORM_GAIN = 2.53;
// 'source': each part's own normal map, packed and turned with its art at the
// bake (armbake.render_sheets); nothing to preview live, it is not made here
const ARM_NORM_MODES = ['skip', 'generic', 'specialized', 'source'];
const ARM_NORM_GENERIC = {strength: 1.0, blur: 0.8, invert: false};
const ARM_NORM_MATERIALS = {
  metal: {strength: 0.7, blur: 0.0, invert: false},
  fabric: {strength: 1.0, blur: 1.0, invert: false},
  leather: {strength: 1.2, blur: 0.8, invert: false},
  wood: {strength: 1.4, blur: 0.5, invert: false},
  skin: {strength: 0.5, blur: 1.5, invert: false},
  hair: {strength: 1.2, blur: 0.0, invert: false},
  bone: {strength: 0.8, blur: 0.8, invert: false},
  other: {strength: 1.0, blur: 0.8, invert: false},
};

function armNormals(){ const p = armProj(); return p.normals = p.normals || {mode: 'skip', preview: true}; }

/* The setting an object's part of the map is made with; null for Skip. */
function armNormalSetting(o, nm){
  nm = nm || armNormals();
  const mode = nm.mode || 'skip';
  if(mode === 'generic') return Object.assign({}, ARM_NORM_GENERIC, nm.generic || {});
  if(mode !== 'specialized') return null;
  const mat = o.material || 'other';
  const out = Object.assign({}, ARM_NORM_MATERIALS[mat] || ARM_NORM_MATERIALS.other, (nm.materials || {})[mat] || {});
  if(o.normal) for(const k of ['strength', 'blur', 'invert']) if(k in o.normal) out[k] = o.normal[k];
  return out;
}
function armNormalPreviewOn(){ const nm = armNormals(); return nm.mode !== 'skip' && nm.mode !== 'source' && nm.preview !== false; }

function armBlurHeight(h, w, ht, sigma){
  if(sigma <= 0.05) return h;
  const r = Math.ceil(3 * sigma), k = [];
  let sum = 0;
  for(let x = -r; x <= r; x++){ const v = Math.exp(-x * x / (2 * sigma * sigma)); k.push(v); sum += v; }
  for(let i = 0; i < k.length; i++) k[i] /= sum;
  const tmp = new Float64Array(w * ht), out = new Float64Array(w * ht);
  for(let y = 0; y < ht; y++) for(let x = 0; x < w; x++){
    let a = 0;
    for(let i = 0; i < k.length; i++){ const xx = Math.min(w - 1, Math.max(0, x + i - r)); a += k[i] * h[y * w + xx]; }
    tmp[y * w + x] = a;
  }
  for(let y = 0; y < ht; y++) for(let x = 0; x < w; x++){
    let a = 0;
    for(let i = 0; i < k.length; i++){ const yy = Math.min(ht - 1, Math.max(0, y + i - r)); a += k[i] * tmp[yy * w + x]; }
    out[y * w + x] = a;
  }
  return out;
}

/* A normal map of RGBA pixels (w x h), as a new array. */
function armNormalPixels(data, w, h, s){
  let H = new Float64Array(w * h);
  for(let i = 0; i < w * h; i++) H[i] = 0.299 * data[i*4] / 255 + 0.587 * data[i*4+1] / 255 + 0.114 * data[i*4+2] / 255;
  H = armBlurHeight(H, w, h, +s.blur || 0);
  const k = (s.strength == null ? 1 : +s.strength) * ARM_NORM_GAIN * (s.invert ? -1 : 1);
  const out = new Uint8ClampedArray(w * h * 4);
  const at = (x, y) => H[Math.min(h - 1, Math.max(0, y)) * w + Math.min(w - 1, Math.max(0, x))];
  const enc = c => Math.max(0, Math.min(255, Math.floor((c * 0.5 + 0.5) * 255 + 0.5)));
  for(let y = 0; y < h; y++) for(let x = 0; x < w; x++){
    const dx = (at(x + 1, y) - at(x - 1, y)) / 2, dy = (at(x, y + 1) - at(x, y - 1)) / 2;
    const nx = -k * dx, ny = -k * dy, ln = Math.sqrt(nx * nx + ny * ny + 1);
    const i = (y * w + x) * 4;
    out[i] = enc(nx / ln); out[i+1] = enc(ny / ln); out[i+2] = enc(1 / ln); out[i+3] = 0;
  }
  return out;
}

/* --- the side panel -------------------------------------------------------------- */

const armNormModeLabel = m => ({skip: tt('armory.norm_skip'), generic: tt('armory.norm_generic'),
  specialized: tt('armory.norm_specialized'), source: tt('armory.norm_source')})[m] || m;

function armNormRow(s, set){
  return `<label class="armrange">${tt('armory.norm_strength')}<input type="range" min="0" max="300" value="${Math.round(s.strength * 100)}"
      oninput="${set}('strength', this.value / 100, true)" onchange="${set}('strength', this.value / 100)"><span class="count">${s.strength.toFixed(2)}</span></label>
    <label class="armrange">${tt('armory.norm_blur')}<input type="range" min="0" max="40" value="${Math.round(s.blur * 10)}"
      oninput="${set}('blur', this.value / 10, true)" onchange="${set}('blur', this.value / 10)"><span class="count">${s.blur.toFixed(1)}</span></label>
    <label class="armcheck"><input type="checkbox"${s.invert ? ' checked' : ''} onchange="${set}('invert', this.checked)"> ${tt('armory.norm_invert')}</label>`;
}

function armNormalsHtml(){
  const nm = armNormals();
  const p = armProj();
  let body = '';
  if(nm.mode === 'generic'){
    body = `<div class="armpropsrow armnormrow">${armNormRow(Object.assign({}, ARM_NORM_GENERIC, nm.generic || {}), 'armNormGeneric')}</div>`;
  }else if(nm.mode === 'specialized'){
    const used = new Set(p.objects.map(o => o.material || 'other'));
    body = Object.keys(ARM_NORM_MATERIALS).filter(m => used.has(m)).map(m => {
      const s = Object.assign({}, ARM_NORM_MATERIALS[m], (nm.materials || {})[m] || {});
      return `<div class="armnormmat"><b>${esc(armMatLabel(m))}</b>
        <span class="count">${ttN('armory.norm_objects', p.objects.filter(o => (o.material || 'other') === m).length)}</span>
        <div class="armpropsrow armnormrow">${armNormRow(s, `armNormMat.bind(null,'${m}')`)}</div></div>`;
    }).join('') + `<div class="count armnote">${tt('armory.norm_specialized_note')}</div>`;
  }else if(nm.mode === 'source'){
    body = `<div class="count armnote">${tt('armory.norm_source_note')}</div>`;
  }else{
    body = `<div class="count armnote">${tt('armory.norm_skip_note')}</div>`;
  }
  return `<div class="armsect">${tt('armory.normal_maps')}</div>
    <div class="armpropsrow"><select onchange="armNormMode(this.value)">${ARM_NORM_MODES.map(m =>
      `<option value="${m}"${nm.mode === m ? ' selected' : ''}>${esc(armNormModeLabel(m))}</option>`).join('')}</select>
      ${nm.mode !== 'skip' && nm.mode !== 'source' ? `<label class="armcheck"><input type="checkbox"${nm.preview !== false ? ' checked' : ''} onchange="armNormPreview(this.checked)"> ${tt('armory.norm_preview')}</label>` : ''}</div>
    ${body}`;
}

/* An object's own setting, in its properties: Specialized only. */
function armNormalObjHtml(o){
  const nm = armNormals();
  if(nm.mode !== 'specialized') return '';
  const s = armNormalSetting(o);
  return `<div class="armsect">${tt('armory.normal_map')}</div>
    <div class="armpropsrow"><label class="armcheck"><input type="checkbox"${o.normal ? ' checked' : ''} onchange="armNormOwn(${o.id}, this.checked)"> ${tt('armory.norm_own')}</label>
      ${o.normal ? '' : `<span class="count">${tt('armory.norm_from_material', {material: armMatLabel(o.material || 'other')})}</span>`}</div>
    ${o.normal ? `<div class="armpropsrow armnormrow">${armNormRow(s, `armNormObj.bind(null,${o.id})`)}</div>` : ''}`;
}

function armNormChanged(live){
  ARM_DYE.forEach(v => { v.stale = true; });
  armFrame();
  if(live){ clearTimeout(ARM.normTimer); ARM.normTimer = setTimeout(() => { armSave(); }, 300); return; }
  armSave(); armPaintObjects();
}
function armNormMode(m){ armNormals().mode = m; armNormChanged(); }
function armNormPreview(on){ armNormals().preview = on; armNormChanged(); }
function armNormGeneric(k, v, live){ const nm = armNormals(); (nm.generic = nm.generic || {})[k] = v; armNormChanged(live); }
function armNormMat(m, k, v, live){
  const nm = armNormals(); nm.materials = nm.materials || {};
  (nm.materials[m] = nm.materials[m] || {})[k] = v;
  armNormChanged(live);
}
function armNormOwn(id, on){
  const o = armObj(id); if(!o) return;
  if(on){ const s = armNormalSetting(o); o.normal = {strength: s.strength, blur: s.blur, invert: s.invert}; }
  else delete o.normal;
  armNormChanged();
}
function armNormObj(id, k, v, live){ const o = armObj(id); if(!o || !o.normal) return; o.normal[k] = v; armNormChanged(live); }
