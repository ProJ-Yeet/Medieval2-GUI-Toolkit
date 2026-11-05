/* =========================================================================
   Armory Studio: importing from disk, previews, and an import that waits

   * A folder: the import dialog's "From disk" tab lists every model under a
     folder (armory.folder_models), grouped by the folder each sits in, with a
     find box, as rows or as tiles (gallery.js draws a file from disk too, the
     GAL_EXT tiles), each with a closer look. A path typed in the box that is
     a folder lists it rather than importing it.
   * A closer look at a file on disk: one big turning tile over the dialog,
     the dialog back as it was when it closes (v3Open is for model entries).
   * An import that fails is tried again before it is given up on: a file a
     program has only just finished writing, or a server still reading the
     first of many, answered the first time and was there the second. The
     dialog stays open saying what it is doing; what still fails stays listed
     there with Try again, and what worked is in.

   Paths never go into an onclick: a Windows path's backslashes are escapes
   in a JavaScript string. Rows and tiles name a model by its index.
   ========================================================================= */

const ARM_IMPORT_TRIES = 4;            // a model is asked for this many times
const ARM_IMPORT_WAIT = [600, 1200, 2400];

/* --- the folder view ------------------------------------------------------------ */

function armDiskState(){
  const imp = state.armImp;
  imp.disk = imp.disk || {folder: null, picked: new Set(), q: '', folded: []};
  return imp.disk;
}
function armDiskBodyHtml(){
  const imp = state.armImp, d = armDiskState();
  const f = d.folder;
  return `<div class="count" style="margin:8px 0">${tt('armory.disk_intro')}</div>
    <div class="armpathrow"><input id="armImpPath" value="${esc(imp.path || '')}" placeholder="${esc(tt('armory.disk_placeholder'))}"
        oninput="state.armImp.path=this.value" onkeydown="if(event.key==='Enter')armDiskList(this.value)">
      <button onclick="armImportBrowse()">${tt('armory.browse_file')}</button>
      <button onclick="armDiskBrowse()">${tt('armory.browse_folder')}</button></div>
    ${f ? `<div class="armimpctl">
        <span class="count" title="${esc(f.folder || '')}">${esc(f.loading ? tt('armory.reading') : f.err ? '' : ttN('armory.disk_found', (f.models || []).length))}</span>
        <input id="armDiskQ" placeholder="${esc(tt('armory.find'))}" value="${esc(d.q)}" oninput="armDiskState().q=this.value;armDiskRows()">
        <button class="mini" onclick="armDiskAll(true)">${tt('armory.disk_pick_shown')}</button>
        <button class="mini" onclick="armDiskAll(false)">${tt('armory.disk_pick_none')}</button></div>
      <div class="armimprows" id="armImpRows"></div>` : ''}`;
}
async function armDiskBrowse(){
  let r;
  try{ r = await api.post('/api/browse_folder', {title: tt('armory.disk_folder_title')}); }
  catch(e){ toast(errText(e)); return; }
  if(r && r.path) armDiskList(r.path);
}
const armDiskIsModel = p => /\.(obj|glb|gltf|dae|mesh)$/i.test((p || '').trim().replace(/"/g, ''));
async function armDiskList(path){
  path = (path || '').trim().replace(/^"|"$/g, '');
  if(!path) return;
  const imp = state.armImp, d = armDiskState();
  imp.path = path;
  if(armDiskIsModel(path)){ const el = document.getElementById('armImpPath'); if(el) el.value = path; return; }
  d.folder = {folder: path, loading: true};
  d.picked.clear();
  armImportPaint();
  let r;
  try{ r = await api.get('/api/armory/folder?path=' + enc(path), 1); }
  catch(e){ r = {folder: path, err: errText(e)}; }
  if(armDiskState().folder !== d.folder) return;
  d.folder = r;
  armImportPaint();
}
function armDiskShown(){
  const d = armDiskState(), q = d.q.trim().toLowerCase();
  const all = (d.folder && d.folder.models) || [];
  return all.map((m, i) => ({m, i})).filter(({m}) => !q || m.rel.toLowerCase().includes(q));
}
/* The rows under the find box, never the box (memory: never repaint the box
   being typed in). */
function armDiskRows(){
  const el = document.getElementById('armImpRows');
  const d = armDiskState(), f = d.folder;
  if(!el || !f) return;
  if(f.loading){ el.innerHTML = `<div class="count">${tt('armory.reading')}</div>`; return; }
  if(f.err){ el.innerHTML = `<div class="w-bad">${esc(f.err)}</div>`; return; }
  const shown = armDiskShown();
  if(!(f.models || []).length){ el.innerHTML = `<div class="count">${tt('armory.disk_none')}</div>`; return; }
  const tiles = armImpGallery();
  const groups = new Map();
  for(const s of shown){ if(!groups.has(s.m.dir)) groups.set(s.m.dir, []); groups.get(s.m.dir).push(s); }
  const look = i => `<button class="mini armimplook" onclick="event.preventDefault();event.stopPropagation();armDiskLook(${i})" title="${esc(tt('armory.look_closer_title'))}">🔍</button>`;
  const kb = n => n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
  let html = '';
  for(const [dir, items] of groups){
    const folded = d.folded.includes(dir);
    const head = `<button class="armfold" onclick="armDiskFold(${JSON.stringify(dir).replace(/"/g, '&quot;')})">${folded ? '▸' : '▾'} ${esc(dir || tt('armory.disk_top'))}</button>
      <span class="count">${items.length}</span>`;
    if(folded){ html += `<div class="armlibgroup">${head}</div>`; continue; }
    const body = tiles
      ? `<div class="galgrid">${items.map(({m, i}) => `<div class="gtile armimptile${d.picked.has(i) ? ' picked' : ''}" data-mod="${GAL_EXT}"
            data-name="${esc(m.path)}" data-k="${i}" title="${esc(m.rel)}"><canvas></canvas>
            <span class="gname">${esc(m.name)}</span><span class="armimptick">✓</span>${look(i)}</div>`).join('')}</div>`
      : items.map(({m, i}) => `<label class="armimprow"><input type="checkbox"${d.picked.has(i) ? ' checked' : ''}
            onchange="armDiskPick(${i}, this.checked)"> <b>${esc(m.name)}</b>
            <span class="count">${esc(m.suffix.slice(1))} · ${kb(m.size)}</span>${look(i)}</label>`).join('');
    html += `<div class="armlibgroup">${head}${body}</div>`;
  }
  if(f.truncated) html += `<div class="count">${tt('armory.disk_truncated', {n: f.models.length})}</div>`;
  el.innerHTML = html || `<div class="count">${tt('armory.nothing_matches')}</div>`;
  el.classList.toggle('armimpgal', tiles);
  if(tiles && typeof galMount === 'function') galMount(el, (name, t) => armDiskTile(t));
}
function armDiskFold(dir){
  const f = armDiskState().folded, i = f.indexOf(dir);
  if(i < 0) f.push(dir); else f.splice(i, 1);
  armDiskRows();
}
function armDiskTile(t){
  const d = armDiskState(), i = +t.dataset.k;
  if(d.picked.has(i)) d.picked.delete(i); else d.picked.add(i);
  t.classList.toggle('picked', d.picked.has(i));
  armImportCount();
}
function armDiskPick(i, on){
  const d = armDiskState();
  if(on) d.picked.add(i); else d.picked.delete(i);
  armImportCount();
}
function armDiskAll(on){
  const d = armDiskState();
  if(on) armDiskShown().forEach(({i}) => d.picked.add(i)); else d.picked.clear();
  armDiskRows(); armImportCount();
}
/* What the From disk tab imports: the models ticked in the folder, else the
   one file in the box. A folder in the box is listed, and nothing imported. */
function armDiskAdds(){
  const imp = state.armImp, d = armDiskState();
  if(d.picked.size && d.folder && d.folder.models)
    return [...d.picked].sort((a, b) => a - b).map(i => d.folder.models[i]).filter(Boolean)
      .map(m => ({kind: 'external', path: m.path}));
  const path = (imp.path || '').trim().replace(/^"|"$/g, '');
  if(!path) return [];
  if(!armDiskIsModel(path)){ armDiskList(path); return null; }
  return [{kind: 'external', path}];
}

/* --- a closer look at a file on disk ----------------------------------------------- */

function armDiskLook(i){
  const f = armDiskState().folder, m = f && f.models && f.models[i];
  if(m) armExtLook(m.path, m.name);
}
function armExtLook(path, name){
  const back = {html: modal.innerHTML, cls: modal.className,
                rows: (document.getElementById('armImpRows') || {}).scrollTop || 0};
  ARM.extLookBack = back;
  modal.className = 'modal wide';
  modal.innerHTML = `<h3>${esc(name || path.split(/[\\/]/).pop())}</h3>
    <div class="count" style="margin-bottom:6px">${esc(path)}</div>
    <div class="armextlook"><div class="gtile" data-mod="${GAL_EXT}" data-name="${esc(path)}"><canvas></canvas></div></div>
    <div class="armimpfoot"><span style="flex:1"></span><button onclick="armExtLookClose()">${tt('common.close')}</button></div>`;
  if(typeof galMount === 'function') galMount(modal, () => {});
}
/* The dialog back as it stood: repainted from its state (the old HTML holds
   no live tiles) and its list where it was scrolled to. */
function armExtLookClose(){
  const back = ARM.extLookBack;
  ARM.extLookBack = null;
  if(state.armImp && document.getElementById('modal')){
    armImportPaint();
    if(state.armImp.tab === 'mod') armImportRows();
    const el = document.getElementById('armImpRows');
    if(el && back) el.scrollTop = back.rows;
  }else if(back){ modal.className = back.cls; modal.innerHTML = back.html; }
  else closeModal();
}

/* --- the import, tried again before it is given up on ------------------------------ */

/* One model, asked for up to ARM_IMPORT_TRIES times; `say` hears each try. */
async function armLoadAssetPatient(a, say){
  const key = armAssetKey(a);
  let live = null;
  for(let n = 1; n <= ARM_IMPORT_TRIES; n++){
    say(n);
    live = await armLoadAsset(a);
    if(!live.err) return live;
    ARM.assets.delete(key);
    if(n < ARM_IMPORT_TRIES) await new Promise(r => setTimeout(r, ARM_IMPORT_WAIT[n - 1] || 2400));
  }
  return live;
}

/* The dialog's footer while it works: which model, which try, how far. */
function armImportProgress(i, total, label, n){
  const el = document.getElementById('armImpCount');
  if(el) el.textContent = n > 1
    ? tt('armory.import_retry', {i, total, name: label, n, of: ARM_IMPORT_TRIES})
    : tt('armory.import_loading', {i, total, name: label});
}

/* What failed, kept on the dialog with Try again, the rest already in. */
function armImportFailed(failed, said){
  const foot = document.getElementById('armImpCount');
  const body = document.getElementById('armImpBody');
  ARM.importFailed = failed;
  const html = `<div class="armimpfail">
    <div class="w-bad">${ttN('armory.import_failed_n', failed.length)}</div>
    ${failed.map(f => `<div class="count">${esc(armAssetLabel(f.a))}: ${esc(f.err)}</div>`).join('')}
    ${said.length ? `<div class="count">${esc(said.join(' · '))}</div>` : ''}
    <button class="primary" onclick="armImportRetry()">${tt('armory.import_try_again')}</button></div>`;
  if(body) body.insertAdjacentHTML('afterbegin', html);
  if(foot) foot.textContent = '';
  const btn = document.getElementById('armImpGo');
  if(btn) btn.disabled = false;
}
async function armImportRetry(){
  const failed = ARM.importFailed || [];
  ARM.importFailed = null;
  document.querySelectorAll('.armimpfail').forEach(x => x.remove());
  if(failed.length) await armImportRun(failed.map(f => f.a));
}
