/* =========================================================================
   Armory Studio's asset library (Phase 95l)

   Models kept for later, each with a name and notes of the user's own beside
   its code name, in collections and categories of the user's own
   (armlib.py keeps them in config/armory/library.json, where each model is,
   never its art). By default the library sorts itself by the unit class,
   unit type, faction and tier of the units that wear each entry, worked out
   by the server from the entry's mod.

     * the Library window (the bar's Library button): grouped by any of
       those, a find box that repaints only the rows under it, each item's
       name, notes, collections and categories, Load and remove;
     * "＋ Library" on a loaded asset, which refuses a model already kept,
       by its place or by its file's bytes;
     * the import dialog's "From the asset library" tab.
   ========================================================================= */

const ARM_LIB_GROUPS = ['class', 'type', 'faction', 'tier', 'collection', 'category', 'none'];

async function armLibLoad(force){
  if(ARM.lib && !force) return ARM.lib;
  try{ ARM.lib = await api.get('/api/armory/library'); }
  catch(e){ ARM.lib = {library: {items: [], collections: [], categories: []}, facets: {}}; }
  return ARM.lib;
}
function armLib(){ return (ARM.lib && ARM.lib.library) || {items: [], collections: [], categories: []}; }
function armLibSave(){
  clearTimeout(ARM.libTimer);
  ARM.libTimer = setTimeout(() => { api.post('/api/armory/library', {library: armLib()}).catch(() => {}); }, 400);
}
function armLibNextId(list){ return list.reduce((m, x) => Math.max(m, +x.id || 0), 0) + 1; }
function armLibItem(id){ return armLib().items.find(x => x.id === id); }
function armLibCode(it){ return it.kind === 'external' ? (it.path || '').split(/[\\/]/).pop() : `${it.entry} · ${it.mod}`; }

const armLibGroupLabel = g => ({class: tt('armory.lib_by_class'), type: tt('armory.lib_by_type'), faction: tt('armory.lib_by_faction'),
  tier: tt('armory.lib_by_tier'), collection: tt('armory.lib_by_collection'), category: tt('armory.lib_by_category'),
  none: tt('armory.lib_by_none')})[g] || g;

/* The groups an item falls in under a grouping; an item can sit in several. */
function armLibKeys(it, by){
  const lib = armLib(), f = (ARM.lib.facets || {})[it.id] || {};
  if(by === 'none') return [''];
  if(by === 'collection') return (it.collections || []).map(id => (lib.collections.find(c => c.id === id) || {}).name).filter(Boolean);
  if(by === 'category') return (it.categories || []).map(id => (lib.categories.find(c => c.id === id) || {}).name).filter(Boolean);
  return f[by] || [];
}
function armLibMatches(it, q){
  if(!q) return true;
  q = q.toLowerCase();
  return [it.name, it.notes, armLibCode(it)].some(s => (s || '').toLowerCase().includes(q));
}

/* --- the window ------------------------------------------------------------------ */

async function armLibOpen(){
  state.armLibUi = state.armLibUi || {by: 'class', q: '', open: null, folded: []};
  document.getElementById('modal').className = 'modal wide';
  modal.innerHTML = `<div class="count">${tt('armory.reading')}</div>`;
  overlay.classList.add('open');
  await armLibLoad(true);
  armLibPaint();
}
function armLibPaint(){
  const ui = state.armLibUi, lib = armLib();
  const chips = (list, kind) => list.map(c => `<span class="chip">${esc(c.name)}
      <button class="mini" onclick="armLibRename('${kind}',${c.id})" title="${esc(tt('armory.lib_rename'))}">✎</button>
      <button class="mini" onclick="armLibDrop('${kind}',${c.id})" title="${esc(tt('armory.lib_delete'))}">✕</button></span>`).join('');
  modal.innerHTML = `<div class="armlib">
    <h3>${tt('armory.lib_title')}</h3>
    <div class="armexprow">
      <label>${tt('armory.lib_group_by')}<select onchange="state.armLibUi.by=this.value;armLibRows()">${ARM_LIB_GROUPS.map(g =>
        `<option value="${g}"${ui.by === g ? ' selected' : ''}>${esc(armLibGroupLabel(g))}</option>`).join('')}</select></label>
      <input id="armLibQ" placeholder="${esc(tt('armory.find'))}" value="${esc(ui.q)}" oninput="state.armLibUi.q=this.value;armLibRows()">
      <span class="count">${ttN('armory.lib_count', lib.items.length)}</span></div>
    <div class="armexprow"><b>${tt('armory.lib_collections')}</b>${chips(lib.collections, 'collections')}
      <button class="mini" onclick="armLibNew('collections')">${tt('armory.new_collection')}</button></div>
    <div class="armexprow"><b>${tt('armory.lib_categories')}</b>${chips(lib.categories, 'categories')}
      <button class="mini" onclick="armLibNew('categories')">${tt('armory.lib_new_category')}</button></div>
    <div class="armlibrows" id="armLibRows"></div>
    <div class="armimpfoot"><span class="count">${tt('armory.lib_note')}</span><span style="flex:1"></span>
      <button onclick="closeModal()">${tt('common.close')}</button></div></div>`;
  armLibRows();
}
/* Only the rows: the find box above them is never repainted while typed in. */
function armLibRows(){
  const el = document.getElementById('armLibRows');
  if(!el) return;
  const ui = state.armLibUi, lib = armLib();
  if(!lib.items.length){ el.innerHTML = `<div class="empty armempty">${tt('armory.lib_empty')}</div>`; return; }
  const groups = new Map();
  for(const it of lib.items){
    if(!armLibMatches(it, ui.q)) continue;
    const keys = armLibKeys(it, ui.by);
    for(const k of keys.length ? keys : [null]){
      if(!groups.has(k)) groups.set(k, []);
      groups.get(k).push(it);
    }
  }
  const order = [...groups.keys()].sort((a, b) => a === null ? 1 : b === null ? -1 : String(a).localeCompare(String(b)));
  el.innerHTML = order.map(k => {
    const items = groups.get(k);
    const label = k === null ? tt('armory.lib_ungrouped') : k === '' ? tt('armory.lib_all') : k;
    const fkey = ui.by + ':' + k;
    const folded = ui.folded.includes(fkey);
    return `<div class="armlibgroup"><button class="armfold" onclick="armLibFold('${esc(fkey).replace(/'/g, '&#39;')}')">${folded ? '▸' : '▾'} ${esc(label)}</button>
      <span class="count">${items.length}</span>
      ${folded ? '' : items.map(armLibRowHtml).join('')}</div>`;
  }).join('') || `<div class="empty armempty">${tt('armory.lib_none_match')}</div>`;
}
function armLibFold(k){
  const f = state.armLibUi.folded, i = f.indexOf(k);
  if(i < 0) f.push(k); else f.splice(i, 1);
  armLibRows();
}
function armLibRowHtml(it){
  const lib = armLib(), open = state.armLibUi.open === it.id, f = (ARM.lib.facets || {})[it.id] || {};
  const facts = ['type', 'class', 'faction', 'tier'].flatMap(k => (f[k] || []).slice(0, k === 'faction' ? 4 : 2))
    .map(v => `<span class="pill">${esc(v)}</span>`).join('');
  const boxes = (list, kind) => list.map(c => `<label class="armcheck"><input type="checkbox"${(it[kind] || []).includes(c.id) ? ' checked' : ''}
      onchange="armLibTick(${it.id},'${kind}',${c.id},this.checked)"> ${esc(c.name)}</label>`).join('') || `<span class="count">${tt('armory.lib_none_yet')}</span>`;
  return `<div class="armlibrow">
    <div class="armexprow"><input class="armlibname" value="${esc(it.name || '')}" onchange="armLibSet(${it.id},'name',this.value)" title="${esc(tt('armory.lib_name_title'))}">
      <span class="count" title="${esc(it.path || '')}">${esc(armLibCode(it))}</span>${facts}<span style="flex:1"></span>
      <button class="mini" onclick="armLibDetails(${it.id})">${open ? '▾' : '▸'} ${tt('armory.lib_details')}</button>
      <button class="mini" onclick="armLibLook(${it.id})" title="${esc(tt('armory.look_closer_title'))}">🔍 ${tt('armory.lib_preview')}</button>
      ${armLibMoveHtml(it, state.armLibUi.by)}
      <button class="mini" onclick="armLibLoadItem(${it.id})">${tt('armory.lib_load')}</button>
      <button class="mini armx" onclick="armLibRemove(${it.id})" title="${esc(tt('armory.lib_remove'))}">✕</button></div>
    ${it.notes && !open ? `<div class="count armlibnote">${esc(it.notes)}</div>` : ''}
    ${open ? `<textarea class="armlibnotes" placeholder="${esc(tt('armory.lib_notes'))}" onchange="armLibSet(${it.id},'notes',this.value)">${esc(it.notes || '')}</textarea>
      <div class="armexprow"><b>${tt('armory.lib_collections')}</b>${boxes(lib.collections, 'collections')}</div>
      <div class="armexprow"><b>${tt('armory.lib_categories')}</b>${boxes(lib.categories, 'categories')}</div>` : ''}
  </div>`;
}
function armLibDetails(id){ state.armLibUi.open = state.armLibUi.open === id ? null : id; armLibRows(); }
function armLibSet(id, k, v){ const it = armLibItem(id); if(!it) return; it[k] = v; armLibSave(); }
function armLibTick(id, kind, cid, on){
  const it = armLibItem(id); if(!it) return;
  it[kind] = (it[kind] || []).filter(x => x !== cid);
  if(on) it[kind].push(cid);
  armLibSave();
  if(['collection', 'category'].includes(state.armLibUi.by)) armLibRows();
}
function armLibNew(kind){
  const name = prompt(kind === 'collections' ? tt('armory.collection_name') : tt('armory.lib_category_name'));
  if(!name || !name.trim()) return;
  const list = armLib()[kind];
  list.push({id: armLibNextId(list), name: name.trim()});
  armLibSave(); armLibPaint();
}
function armLibRename(kind, id){
  const c = armLib()[kind].find(x => x.id === id); if(!c) return;
  const name = prompt(tt('armory.lib_rename'), c.name);
  if(!name || !name.trim()) return;
  c.name = name.trim(); armLibSave(); armLibPaint();
}
function armLibDrop(kind, id){
  const lib = armLib();
  lib[kind] = lib[kind].filter(x => x.id !== id);
  for(const it of lib.items) it[kind] = (it[kind] || []).filter(x => x !== id);
  armLibSave(); armLibPaint();
}
function armLibRemove(id){
  const it = armLibItem(id); if(!it) return;
  if(!confirm(tt('armory.lib_remove_confirm', {name: it.name}))) return;
  armLib().items = armLib().items.filter(x => x.id !== id);
  armLibSave(); armLibPaint();
}
function armLibAsset(it){
  return it.kind === 'external' ? {kind: 'external', path: it.path} : {kind: 'entry', mod: it.mod, entry: it.entry, unit: it.unit || ''};
}
async function armLibLoadItem(id){
  const it = armLibItem(id); if(!it) return;
  state.armImp = state.armImp || {tab: 'library', picked: new Set()};
  state.armImp.tab = 'library';
  state.armImp.libPicked = new Set([id]);
  await armImportGo();
}

/* --- adding to it ---------------------------------------------------------------- */

async function armLibAddAsset(key){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  if(!a) return;
  const live = ARM.assets.get(key) || {};
  const item = Object.assign({}, a, {name: armAssetLabel(a), file_hash: live.view && live.view.file_hash || ''});
  delete item.open; delete item.show; delete item.skin; delete item.textures;
  let r;
  try{ r = await api.post('/api/armory/library/add', {item}); }catch(e){ toast(errText(e)); return; }
  ARM.lib = {library: r.library, facets: r.facets};
  if(r.item) toast(tt('armory.lib_added', {name: r.item.name}));
  else if(r.why === 'art') toast(tt('armory.lib_same_art', {name: item.name, other: r.same.name}), 5000);
  else toast(tt('armory.lib_already', {name: r.same.name}));
}

/* --- the import dialog's tab ------------------------------------------------------- */

/* Grouped, found and looked at as the Library window has them; an item is
   moved into another collection (or category) by its Move to list, or by
   dragging it onto a group's heading while grouped by collections or
   categories. The rows repaint under the find box, never the box. */
function armLibPickUi(){
  const imp = state.armImp;
  imp.libUi = imp.libUi || {by: (state.armLibUi && state.armLibUi.by) || 'class', q: '', folded: []};
  return imp.libUi;
}
function armLibPickHtml(){
  const imp = state.armImp;
  imp.libPicked = imp.libPicked || new Set();
  if(!ARM.lib){ armLibLoad().then(() => { const el = document.getElementById('armLibPick'); if(el){ el.innerHTML = armLibPickHtml(); armLibPickRows(); } }); return `<div class="count">${tt('armory.reading')}</div>`; }
  if(!armLib().items.length) return `<div class="empty armempty">${tt('armory.lib_empty')}</div>`;
  const ui = armLibPickUi();
  setTimeout(armLibPickRows, 0);
  return `<div class="armimpctl">
      <label class="count">${tt('armory.lib_group_by')}<select onchange="armLibPickUi().by=this.value;armLibPickRows()">${ARM_LIB_GROUPS.map(g =>
        `<option value="${g}"${ui.by === g ? ' selected' : ''}>${esc(armLibGroupLabel(g))}</option>`).join('')}</select></label>
      <input id="armLibPickQ" placeholder="${esc(tt('armory.find'))}" value="${esc(ui.q)}" oninput="armLibPickUi().q=this.value;armLibPickRows()">
      <span class="count">${ttN('armory.lib_count', armLib().items.length)}</span></div>
    <div class="armimprows" id="armLibPickRows"></div>`;
}
/* The kind an item moves between under a grouping: collections, unless the
   list is grouped by categories. */
const armLibMoveKind = by => by === 'category' ? 'categories' : 'collections';
function armLibMoveHtml(it, by){
  const kind = armLibMoveKind(by), list = armLib()[kind];
  return `<select class="armlibmove" title="${esc(tt('armory.lib_move_title'))}" onclick="event.stopPropagation()"
      onchange="armLibMove(${it.id}, '${kind}', this.value);this.value=''">
    <option value="">${tt(kind === 'categories' ? 'armory.lib_move_category' : 'armory.lib_move_collection')}</option>
    ${list.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}
    <option value="new">${tt(kind === 'categories' ? 'armory.lib_new_category' : 'armory.new_collection')}</option></select>`;
}
function armLibPickRows(){
  const el = document.getElementById('armLibPickRows');
  if(!el) return;
  const imp = state.armImp, ui = armLibPickUi(), lib = armLib();
  const groups = new Map();
  for(const it of lib.items){
    if(!armLibMatches(it, ui.q)) continue;
    const keys = armLibKeys(it, ui.by);
    for(const k of keys.length ? keys : [null]){
      if(!groups.has(k)) groups.set(k, []);
      groups.get(k).push(it);
    }
  }
  const tiles = armImpGallery();
  const movable = ['collection', 'category'].includes(ui.by);
  const kind = armLibMoveKind(ui.by);
  const look = it => `<button class="mini armimplook" onclick="event.preventDefault();event.stopPropagation();armLibLook(${it.id})" title="${esc(tt('armory.look_closer_title'))}">🔍</button>`;
  const drag = it => movable ? ` data-drag="${it.id}"` : '';
  const order = [...groups.keys()].sort((a, b) => a === null ? 1 : b === null ? -1 : String(a).localeCompare(String(b)));
  el.innerHTML = order.map(k => {
    const items = groups.get(k);
    const label = k === null ? tt('armory.lib_ungrouped') : k === '' ? tt('armory.lib_all') : k;
    const fkey = ui.by + ':' + k, folded = ui.folded.includes(fkey);
    // a group's heading takes a dragged item, when the group is a collection or category
    const target = movable && k !== null ? (lib[kind].find(c => c.name === k) || {}).id : null;
    const drop = target != null ? ` data-drop="${target}"` : '';
    const body = folded ? '' : tiles
      ? `<div class="galgrid">${items.map(it => {
          const lbl = `<b>${esc(it.name)}</b> ${esc(armLibCode(it))}`;
          const mod = it.kind === 'external' ? GAL_EXT : it.mod, name = it.kind === 'external' ? it.path : it.entry;
          return `<div class="gtile armimptile${imp.libPicked.has(it.id) ? ' picked' : ''}" data-mod="${esc(mod)}" data-name="${esc(name)}"
            data-k="${it.id}" title="${esc(it.path || it.entry || '')}"${drag(it)}><canvas></canvas><span class="gname">${lbl}</span>
            <span class="armimptick">✓</span>${look(it)}</div>`; }).join('')}</div>`
      : items.map(it => `<label class="armcheck armlibpick"${drag(it)}><input type="checkbox"${imp.libPicked.has(it.id) ? ' checked' : ''}
          onchange="armLibPick(${it.id}, this.checked)"> <b>${esc(it.name)}</b> <span class="count">${esc(armLibCode(it))}</span>
          ${it.notes ? `<span class="count">· ${esc(it.notes)}</span>` : ''}<span style="flex:1"></span>${look(it)}${armLibMoveHtml(it, ui.by)}</label>`).join('');
    return `<div class="armlibgroup"><div class="armlibhead"${drop}><button class="armfold" onclick="armLibPickFold(${JSON.stringify(fkey).replace(/"/g, '&quot;')})">${folded ? '▸' : '▾'} ${esc(label)}</button>
      <span class="count">${items.length}</span></div>${body}</div>`;
  }).join('') || `<div class="empty armempty">${tt('armory.lib_none_match')}</div>`;
  el.classList.toggle('armimpgal', tiles);
  armLibWireDrag(el, kind);
  if(tiles && typeof galMount === 'function') galMount(el, (name, t) => armLibTileToggle(t));
}
/* An item dragged onto a group's heading moves into that collection or category. */
function armLibWireDrag(el, kind){
  el.querySelectorAll('[data-drag]').forEach(x => {
    x.draggable = true;
    x.addEventListener('dragstart', ev => ev.dataTransfer.setData('text/plain', x.dataset.drag));
  });
  el.querySelectorAll('[data-drop]').forEach(h => {
    h.addEventListener('dragover', ev => { ev.preventDefault(); h.classList.add('armdrop'); });
    h.addEventListener('dragleave', () => h.classList.remove('armdrop'));
    h.addEventListener('drop', ev => {
      ev.preventDefault(); h.classList.remove('armdrop');
      armLibMove(+ev.dataTransfer.getData('text/plain'), kind, +h.dataset.drop);
    });
  });
}
function armLibPickFold(k){
  const f = armLibPickUi().folded, i = f.indexOf(k);
  if(i < 0) f.push(k); else f.splice(i, 1);
  armLibPickRows();
}
/* Into one collection (or category) and out of the others of that kind. */
function armLibMove(id, kind, cid){
  const it = armLibItem(id);
  if(!it || cid === '' || cid == null) return;
  if(cid === 'new'){
    const name = prompt(kind === 'collections' ? tt('armory.collection_name') : tt('armory.lib_category_name'));
    if(!name || !name.trim()) return;
    const list = armLib()[kind];
    cid = armLibNextId(list);
    list.push({id: cid, name: name.trim()});
  }
  it[kind] = [+cid];
  armLibSave();
  if(document.getElementById('armLibPickRows')) armLibPickRows();
  if(document.getElementById('armLibRows')) armLibPaint();
}
/* A closer look: an entry in the Models viewer, a file on disk in the big tile. */
function armLibLook(id){
  const it = armLibItem(id);
  if(!it) return;
  if(it.kind === 'external') armExtLook(it.path, it.name);
  else armImpLook(it.mod, it.entry);
}
function armLibPick(id, on){
  const s = state.armImp.libPicked;
  if(on) s.add(id); else s.delete(id);
  if(typeof armImportCount === 'function') armImportCount();
}
function armLibPicked(){
  const s = (state.armImp && state.armImp.libPicked) || new Set();
  const out = armLib().items.filter(it => s.has(it.id)).map(armLibAsset);
  s.clear();
  return out;
}
