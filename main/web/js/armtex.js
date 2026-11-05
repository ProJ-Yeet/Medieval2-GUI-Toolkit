/* Armory Studio - the Textures tab (100l).

   Every sheet the model wears, which objects wear it and how big it is; a
   sheet brought in from disk, written out in another format, put on the
   selected objects in place of their own, and Edit: a PNG copy opened in the
   user's own image program and read back into the viewport whenever the file
   changes. A sheet is a file path (a working copy, an import, a file beside
   a model from disk) or a mod's own sheet; changing a mod's sheet always goes
   through a working copy, so the mod is never written.

   Where a sheet stands in for another:
     a.over = {main, attach}   an entry's main or attachment sheet
     a.textures[group]         one object of a file from disk (95e)
     o.sheet                   one object of the model, whatever it came from
   armory.js draws and armbake.py bakes all three. */

ARM.sheetStamp = ARM.sheetStamp || {};
ARM.sheetCache = ARM.sheetCache || new Map();
ARM.sheetAllowed = ARM.sheetAllowed || new Set();

function armSheetUrl(path){
  return '/api/armory/texture?path=' + enc(path) + '&v=' + (ARM.sheetStamp[path] || 0);
}
// a sheet picked or imported in an earlier run is allowed again before it is
// asked for: the server keeps that list in memory only. A post lost to a
// refused connection is sent again until it lands, or the sheet's own
// request is turned away as never given.
async function armAllow(path){
  if(!path || ARM.sheetAllowed.has(path)) return;
  for(let wait = 250;; wait = Math.min(wait * 2, 2000)){
    try{ await api.post('/api/armory/allow_texture', {path}); break; }
    catch(e){ if(e === ABORTED) return; await new Promise(ok => setTimeout(ok, wait)); }
  }
  ARM.sheetAllowed.add(path);
}
// the texture an object's own sheet draws with; null until it has loaded
function armSheetTex(path){
  const hit = ARM.sheetCache.get(path);
  if(hit) return hit.tex || null;
  const row = {tex: null, img: null};
  ARM.sheetCache.set(path, row);
  (async () => {
    try{
      await armAllow(path);
      row.img = await armImage(armSheetUrl(path));
      row.tex = armTexture(row.img, 1);
      armFrame(); armTexPeekPaint();
    }catch(e){ row.err = String(e); }
  })();
  return null;
}

/* --- what the model wears ----------------------------------------------------- */

function armTexSheets(){
  const p = armProj(), rows = new Map();
  const row = (id, label, src) => {
    if(!rows.has(id)) rows.set(id, {id, label, src, objs: new Set(), slots: [], over: false});
    return rows.get(id);
  };
  const isCopy = path => /[\\/]armory[\\/]sheets[\\/]/i.test(path || '');
  for(const a of p.assets){
    const key = armAssetKey(a), live = ARM.assets.get(key);
    if(!live || !live.view) continue;
    const users = p.objects.filter(o => !o.sheet && (o.src || []).some(pc => pc.asset === key));
    if(a.kind === 'external'){
      for(const ob of live.view.objects){
        const file = armObjTexture(a, ob.index);
        if(!file) continue;
        const r = row('f:' + file, file.split(/[\\/]/).pop(), {path: file});
        r.slots.push({asset: key, group: ob.index});
        if((a.textures || {})[ob.index]) r.over = true;
        users.filter(o => o.src.some(pc => pc.asset === key && pc.group === ob.index)).forEach(o => r.objs.add(o.id));
      }
      continue;
    }
    const skin = (live.view.skins || [])[a.skin || 0] || {};
    const over = a.over || {};
    for(const kind of ['main', 'attach']){
      const path = over[kind];
      const rel = kind === 'main' ? (skin.exists ? skin.rel : '') : (skin.attach_exists ? skin.attach : '');
      if(!path && !rel) continue;
      const r = path ? row('f:' + path, path.split(/[\\/]/).pop(), {path})
                     : row(`m:${a.mod}|${rel}`, rel.split('/').pop(), {mod: a.mod, rel});
      r.slots.push({asset: key, kind});
      if(path) r.over = true;
      r.kind = r.kind || kind;
      for(const o of users) for(const pc of o.src){
        if(pc.asset !== key) continue;
        const ob = live.view.objects[pc.group];
        const on = !ob || ob.sheets === 'both' || (ob.sheets || 'main') === kind;
        if(on) r.objs.add(o.id);
      }
    }
  }
  for(const o of p.objects){
    if(!o.sheet) continue;
    const r = row('f:' + o.sheet, o.sheet.split(/[\\/]/).pop(), {path: o.sheet});
    r.slots.push({obj: o.id}); r.objs.add(o.id); r.over = true;
  }
  for(const path of p.sheets || []) row('f:' + path, path.split(/[\\/]/).pop(), {path}).imported = true;
  for(const r of rows.values()) r.copy = !!(r.src.path && isCopy(r.src.path));
  return [...rows.values()];
}
const armTexUrl = src => src.path ? armSheetUrl(src.path) : `/model_texture?mod=${enc(src.mod)}&rel=${enc(src.rel)}`;

/* --- the dialog ------------------------------------------------------------------ */

function armTexOpen(){
  document.getElementById('modal').className = 'modal wide';
  overlay.classList.add('open');
  armTexPaint();
}
function armTexPaint(){
  const rows = armTexSheets();
  ARM.texRows = rows;
  const p = armProj();
  const sel = armSelected().length;
  const name = id => { const o = armObj(id); return o ? o.mesh : ''; };
  modal.innerHTML = `<div class="armtex">
    <h3>${tt('armory.textures')}</h3>
    <div class="count" style="margin-bottom:8px">${tt('armory.textures_intro')}</div>
    <div class="armtexctl">
      <button class="mini primary" onclick="armTexImport()">${tt('armory.tex_import')}</button>
      <label class="count" title="${esc(tt('armory.tex_editor_title'))}">${tt('armory.tex_editor')}
        <input id="armTexEd" value="${esc((state.settings || {}).image_editor || '')}" placeholder="${esc(tt('armory.tex_editor_default'))}"
          onchange="armTexEditor(this.value)"></label>
      <button class="mini" onclick="armTexEditorBrowse()">${tt('armory.browse')}</button>
    </div>
    <div class="armtexrows">${rows.length ? rows.map((r, i) => `<div class="armtexrow">
      <img class="armtexthumb" src="${armTexUrl(r.src)}" onload="armTexSize(this, ${i})" onerror="this.classList.add('bad')" alt="">
      <div class="armtexmeta">
        <b title="${esc(r.src.path || r.src.mod + ': ' + r.src.rel)}">${esc(r.label)}</b>
        <span class="count">${r.src.path ? (r.copy ? tt('armory.tex_working_copy') : tt('armory.tex_file')) : esc(r.src.mod)}${r.kind ? ' · ' + (r.kind === 'attach' ? tt('armory.sheet_attach') : tt('armory.sheet_main')) : ''}
          · <span id="armTexSz${i}">…</span></span>
        <span class="count">${r.objs.size ? ttN('armory.tex_worn_by', r.objs.size, {names: esc([...r.objs].slice(0, 6).map(name).join(', '))}) : tt('armory.tex_unused')}</span>
      </div>
      <div class="armtexbtns">
        <button class="mini primary" onclick="armTexEdit(${i})" title="${esc(tt('armory.tex_edit_title'))}">${tt('armory.tex_edit')}</button>
        <button class="mini" onclick="armTexPut(${i})"${sel ? '' : ' disabled'} title="${esc(tt('armory.tex_put_title'))}">${ttN('armory.tex_put', sel)}</button>
        <button class="mini" onclick="armTexExport(${i})">${tt('armory.tex_export')}</button>
        ${r.over ? `<button class="mini" onclick="armTexBack(${i})" title="${esc(tt('armory.tex_back_title'))}">${tt('armory.tex_back')}</button>` : ''}
        ${r.imported && !r.objs.size ? `<button class="mini armx" onclick="armTexForget(${i})">✕</button>` : ''}
      </div></div>`).join('') : `<div class="empty">${tt('armory.tex_none')}</div>`}</div>
    <div class="armimpfoot"><span style="flex:1"></span><button onclick="closeModal()">${tt('common.close')}</button></div>
  </div>`;
}
function armTexSize(img, i){
  const el = document.getElementById('armTexSz' + i);
  if(el) el.textContent = `${img.naturalWidth} × ${img.naturalHeight}`;
}
function armTexEditor(v){
  state.settings.image_editor = (v || '').trim();
  api.post('/api/settings', {image_editor: state.settings.image_editor}).catch(() => {});
}
async function armTexEditorBrowse(){
  let r;
  try{ r = await api.post('/api/browse_file', {title: tt('armory.tex_editor'), filter: 'Programs|*.exe'}); }catch(e){ toast(errText(e)); return; }
  if(r && r.path){ armTexEditor(r.path); const el = document.getElementById('armTexEd'); if(el) el.value = r.path; }
}
async function armTexImport(){
  let r;
  try{ r = await api.post('/api/browse_file', {title: tt('armory.tex_import'),
    filter: 'Images|*.png;*.tga;*.dds;*.jpg;*.jpeg;*.texture;*.bmp'}); }catch(e){ toast(errText(e)); return; }
  if(!r || !r.path) return;
  const ok = await api.post('/api/armory/allow_texture', {path: r.path}).catch(() => ({}));
  if(!ok.ok){ toast(tt('armory.not_an_image')); return; }
  ARM.sheetAllowed.add(r.path);
  const p = armProj();
  p.sheets = p.sheets || [];
  if(!p.sheets.includes(r.path)) p.sheets.push(r.path);
  armSave(); armTexPaint();
}
function armTexForget(i){
  const r = ARM.texRows[i], p = armProj();
  p.sheets = (p.sheets || []).filter(x => x !== r.src.path);
  armSave(); armTexPaint();
}
// a mod's sheet becomes a file to wear by way of a working copy
async function armTexFile(src, edit){
  if(src.path && !edit) return src.path;
  const r = await api.post('/api/armory/sheet/' + (edit ? 'edit' : 'copy'), src);
  if(r.error) throw new Error(r.error);
  ARM.sheetAllowed.add(r.path);
  return r.path;
}
// every place the row's sheet is worn now wears ``path``
function armTexRetarget(r, path){
  const p = armProj();
  for(const s of r.slots){
    const a = p.assets.find(x => armAssetKey(x) === s.asset);
    if(s.obj != null){ const o = armObj(s.obj); if(o) o.sheet = path; }
    else if(a && s.kind){ a.over = a.over || {}; a.over[s.kind] = path; }
    else if(a){ a.textures = a.textures || {}; a.textures[s.group] = path; }
  }
  armTexReload(path, r.slots);
}
function armTexReload(path, slots){
  const p = armProj();
  const keys = new Set((slots || []).filter(s => s.asset).map(s => s.asset));
  for(const a of p.assets){
    const key = armAssetKey(a);
    const uses = keys.has(key) || Object.values(a.over || {}).includes(path) || Object.values(a.textures || {}).includes(path);
    const live = ARM.assets.get(key);
    if(uses && live) armLoadSkin(a, live);
  }
  ARM.sheetCache.delete(path);
  if(typeof ARM_DYE !== 'undefined') ARM_DYE.forEach(v => { v.stale = true; });
  armFrame(); armTexPeekPaint();
}
async function armTexEdit(i){
  const r = ARM.texRows[i];
  try{
    const path = await armTexFile(r.src, true);
    if(r.src.path !== path) armTexRetarget(r, path);
    armTexWatch(path);
    armSave();
    toast(tt('armory.tex_editing', {name: path.split(/[\\/]/).pop()}), 6000);
    armTexPaint();
  }catch(e){ toast(errText(e), 6000); }
}
async function armTexPut(i){
  const r = ARM.texRows[i];
  try{
    const path = await armTexFile(r.src, false);
    for(const o of armSelected()) o.sheet = path;
    ARM.sheetCache.delete(path);
    armRepaint(); armTexPaint();
  }catch(e){ toast(errText(e), 6000); }
}
function armTexBack(i){
  const r = ARM.texRows[i], p = armProj();
  for(const s of r.slots){
    const a = p.assets.find(x => armAssetKey(x) === s.asset);
    if(s.obj != null){ const o = armObj(s.obj); if(o) o.sheet = null; }
    else if(a && s.kind && a.over){ delete a.over[s.kind]; }
    else if(a && a.textures){ delete a.textures[s.group]; }
    const live = a && ARM.assets.get(s.asset);
    if(live) armLoadSkin(a, live);
  }
  armRepaint(); armTexPaint();
}
async function armTexExport(i){
  const r = ARM.texRows[i];
  let to;
  try{
    to = await api.post('/api/browse_save', {title: tt('armory.tex_export'), name: r.label.replace(/\.[^.]+$/, '') + '.png',
      filter: 'PNG|*.png|TGA|*.tga|DDS|*.dds|Texture|*.texture|JPEG|*.jpg|BMP|*.bmp', ext: '.png'});
  }catch(e){ toast(errText(e)); return; }
  if(!to || !to.path) return;
  try{
    const out = await api.post('/api/armory/sheet/export', Object.assign({to: to.path}, r.src));
    if(out.error) throw new Error(out.error);
    toast(tt('armory.tex_exported', {path: out.path}), 6000);
  }catch(e){ toast(errText(e), 6000); }
}

/* --- watching a sheet being edited ------------------------------------------------ */

function armTexWatch(path){
  ARM.texWatch = ARM.texWatch || new Set();
  ARM.texWatch.add(path);
  if(ARM.texTimer) return;
  ARM.texTimer = setInterval(async () => {
    if(state.mode !== 'armory' || !ARM.texWatch.size) return;
    for(const path of ARM.texWatch){
      let r;
      try{ r = await api.get('/api/armory/sheet/stamp?path=' + enc(path)); }catch(e){ continue; }
      if(!r || !r.stamp) continue;
      const was = ARM.sheetStamp[path];
      ARM.sheetStamp[path] = r.stamp;
      if(was && was !== r.stamp) armTexReload(path);
    }
  }, 1500);
}

/* --- the detail view's sheet, with the object's UVs over it ------------------------ */

function armTexPeek(){
  ARM.texPeek = !ARM.texPeek;
  if(typeof armPaintDetailBar === 'function') armPaintDetailBar();
  armTexPeekPaint();
}
function armTexPeekPaint(){
  const host = document.getElementById('armView');
  let el = document.getElementById('armTexPeek');
  if(!host || !ARM.texPeek || !ARM.detail){ if(el) el.remove(); return; }
  const o = armObj(ARM.detail.id);
  if(!o) return;
  if(!el){ el = Object.assign(document.createElement('div'), {id: 'armTexPeek', className: 'armtexpeek'}); host.appendChild(el); }
  const pc0 = (o.src || [])[0];
  const live0 = pc0 && ARM.assets.get(pc0.asset);
  let img = null, us = 0.5;
  if(o.sheet){ const hit = ARM.sheetCache.get(o.sheet); img = hit && hit.img; us = 1; if(!hit) armSheetTex(o.sheet); }
  else if(live0 && live0.objImg){ img = live0.objImg[pc0.group]; us = 1; }
  else if(live0){ img = live0.img; us = live0.uScale || 0.5; }
  const side = 300;
  const w = img ? side : side, h = img ? Math.round(side * img.height / img.width) : side;
  el.innerHTML = `<div class="armtexpeekhead"><b>${tt('armory.tex_peek')}</b>${img ? `<span class="count">${img.width} × ${img.height}</span>` : ''}
    <span style="flex:1"></span><button class="mini" onclick="armTexOpen()">${tt('armory.textures')}</button>
    <button class="mini" onclick="armTexPeek()">✕</button></div><canvas width="${w}" height="${h}"></canvas>`;
  const c = el.querySelector('canvas').getContext('2d');
  c.fillStyle = '#222'; c.fillRect(0, 0, w, h);
  if(img) c.drawImage(img, 0, 0, w, h);
  else{ c.fillStyle = '#888'; c.fillText(tt('armory.tex_no_sheet'), 10, 20); }
  c.strokeStyle = 'rgba(255, 200, 60, 0.85)'; c.lineWidth = 0.6;
  for(const pc of o.src || []){
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo || !live.geo.uvs) continue;
    const UV = live.geo.uvs, idx = [];
    armPieceEach(live, pc, i => idx.push(i));
    const u = pc === pc0 ? us : (live.objImg || o.sheet ? 1 : (live.uScale || 0.5));
    c.beginPath();
    for(let t = 0; t + 2 < idx.length; t += 3){
      // a triangle drawn where its first corner's tile is, so one that
      // crosses a tile edge is not stretched over the whole sheet
      const bu = Math.floor(UV[idx[t] * 2] * u), bv = Math.floor(UV[idx[t] * 2 + 1]);
      for(let k = 0; k < 4; k++){
        const v = idx[t + (k % 3)];
        const X = (UV[v * 2] * u - bu) * w, Y = (UV[v * 2 + 1] - bv) * h;
        if(k === 0) c.moveTo(X, Y); else c.lineTo(X, Y);
      }
    }
    c.stroke();
  }
}
