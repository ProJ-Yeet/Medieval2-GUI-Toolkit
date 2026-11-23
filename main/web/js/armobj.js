/* =========================================================================
   Armory Studio, the objects panel - Phase 95f (armory.js holds the rest)

   Every object of the model being edited, grouped by its group type (Body,
   Head, shield0...) into folds that hide and show at once, and the user's own
   collections, which hide, show, export and delete together. Per object:

     * its name, fixed and prefixed the way the Blender kit does it
       (Reference/Medieval-2-Toolkit, panels/qol_panel.py), and its opt flag;
     * a material, which the normal maps of 95j are made from;
     * a recolour, previewed live on the model before any bake (95i bakes the
       same arithmetic, armory.py): generic presets or the user's own, six
       blend modes, metal never tinted and white kept white, material channels
       inside the one object (cloth, leather, trim) each dyed on its own, and a
       pattern detector that clusters the part's colours into layers;
     * weights transferred from the rest of the model (server side), and
       duplicate, merge and an empty object for a variant that shows nothing;
     * a detail view: the object alone, its connected parts selected the way
       Blender's L does, or its vertices picked by hand in X-ray, and the
       selection split off into a new object.
   ========================================================================= */

const ARM_MATERIALS = ['metal', 'fabric', 'leather', 'wood', 'skin', 'hair', 'bone', 'other'];
const ARM_PREFIXES = ['weapon0', 'weapon1', 'primaryactive0', 'primaryactive1', 'primarypassive0',
  'primarypassive1', 'secondaryactive0', 'secondaryactive1', 'shield0', 'shield1', 'shieldactive0',
  'shieldactive1', 'shieldpassive0', 'shieldpassive1', 'ramrod0', 'equipment0', 'equipment20',
  // two the game spells with a space in them
  ['cannon', 'ball0'].join(' '), ['ballista', 'arrow0'].join(' ')];
const ARM_BLENDS = ['multiply', 'overlay', 'softlight', 'screen', 'hardlight', 'keepshade'];
/* Generic looks, never a named faction's. `metal` presets, the metal channel
   and an object marked metal are the only dyes that reach the grey pixels. */
const ARM_PRESETS = [
  {id: 'metal', color: [178, 182, 188], blend: 'keepshade', metal: true, desat: 1},
  {id: 'rusted_metal', color: [140, 70, 32], blend: 'overlay', metal: true, desat: 0.5},
  {id: 'dark_leather', color: [62, 40, 26], blend: 'keepshade'},
  {id: 'tan_leather', color: [168, 120, 72], blend: 'keepshade'},
  {id: 'red_cloth', color: [150, 24, 24], blend: 'keepshade'},
  {id: 'blue_cloth', color: [30, 50, 132], blend: 'keepshade'},
  {id: 'green_cloth', color: [32, 92, 42], blend: 'keepshade'},
  {id: 'yellow_cloth', color: [204, 162, 42], blend: 'keepshade'},
  {id: 'black_cloth', color: [30, 30, 32], blend: 'keepshade'},
  {id: 'white_linen', color: [226, 220, 204], blend: 'keepshade'},
  {id: 'purple_cloth', color: [92, 32, 112], blend: 'keepshade'},
  {id: 'brown_wool', color: [102, 72, 46], blend: 'keepshade'},
];
const ARM_CHANNELS = ['cloth', 'leather', 'trim', 'metal'];

/* Every label by its literal ID, so the catalogue check sees each one. */
const armMatLabel = m => ({metal: tt('armory.mat_metal'), fabric: tt('armory.mat_fabric'),
  leather: tt('armory.mat_leather'), wood: tt('armory.mat_wood'), skin: tt('armory.mat_skin'),
  hair: tt('armory.mat_hair'), bone: tt('armory.mat_bone'), other: tt('armory.mat_other')})[m] || m;
const armBlendLabel = b => ({multiply: tt('armory.blend_multiply'), overlay: tt('armory.blend_overlay'),
  softlight: tt('armory.blend_softlight'), screen: tt('armory.blend_screen'),
  hardlight: tt('armory.blend_hardlight'), keepshade: tt('armory.blend_keepshade')})[b] || b;
const armChanLabel = c => ({cloth: tt('armory.chan_cloth'), leather: tt('armory.chan_leather'),
  trim: tt('armory.chan_trim'), metal: tt('armory.chan_metal')})[c] || c;
const armWModeLabel = m => ({face: tt('armory.wmode_face'), vertex: tt('armory.wmode_vertex'),
  edge: tt('armory.wmode_edge')})[m] || m;
const armPresetLabel = id => ({metal: tt('armory.preset_metal'), rusted_metal: tt('armory.preset_rusted_metal'),
  dark_leather: tt('armory.preset_dark_leather'), tan_leather: tt('armory.preset_tan_leather'),
  red_cloth: tt('armory.preset_red_cloth'), blue_cloth: tt('armory.preset_blue_cloth'),
  green_cloth: tt('armory.preset_green_cloth'), yellow_cloth: tt('armory.preset_yellow_cloth'),
  black_cloth: tt('armory.preset_black_cloth'), white_linen: tt('armory.preset_white_linen'),
  purple_cloth: tt('armory.preset_purple_cloth'), brown_wool: tt('armory.preset_brown_wool')})[id] || id;

/* --- the panel --------------------------------------------------------------- */

/* 2026-11-23: the objects above, the selected object's properties below, half
   and half, each scrolling on its own; the properties fold away to give the
   list the room. The list is rows or tiles (each object drawn small), its
   folds open and shut all at once, and rows are dragged onto a collection or
   a group to move there. */
const armObjGallery = () => (state.settings || {}).armory_obj_view === 'gallery';
const armPropsShut = () => !!(state.settings || {}).armory_props_shut;
function armObjSetting(k, v){
  state.settings[k] = v;
  api.post('/api/settings', {[k]: v}).catch(() => {});
  armPaintObjects();
}
function armFoldAll(shut){
  const p = armProj();
  const keys = [...new Set(p.objects.filter(o => !o.coll).map(o => 'g:' + o.name))].concat(p.collections.map(c => 'c:' + c.id));
  p.ui.folded = shut ? keys : [];
  armSave(); armPaintObjects();
}
function armPaintObjects(){
  const el = document.getElementById('armRight');
  if(!el) return;
  const p = armProj();
  p.ui = p.ui || {folded: []};
  const groups = new Map();
  for(const o of p.objects){
    if(o.coll) continue;
    if(!groups.has(o.name)) groups.set(o.name, []);
    groups.get(o.name).push(o);
  }
  armActiveFix();
  const sel = armSelected();
  el.classList.toggle('armsplitpane', !armSideShut('right'));
  if(armSideShut('right')){ el.innerHTML = armStripHtml('right', tt('armory.objects'), p.objects.length); return; }
  const tops = ['armObjList', 'armPropsPane'].map(id => { const x = document.getElementById(id); return x ? x.scrollTop : 0; });
  const gal = armObjGallery(), shut = armPropsShut();
  el.innerHTML = `<div class="armhead">
      <button class="armfold" onclick="armSideToggle('right')" title="${esc(tt('armory.panel_fold'))}">▸ ${tt('armory.objects')}</button>
      <span class="count">${p.objects.length}</span><span style="flex:1"></span>
      <button class="mini" onclick="armBlank()" title="${esc(tt('armory.blank_title'))}">${tt('armory.blank')}</button>
      <button class="mini" onclick="armNewCollection()" title="${esc(tt('armory.new_collection_title'))}">${tt('armory.new_collection')}</button>
    </div>
    <div class="armtools">
      <button class="mini" onclick="armMerge()"${sel.length > 1 ? '' : ' disabled'} title="${esc(tt('armory.merge_title'))}">${tt('armory.merge')}</button>
      <button class="mini${ARM.optOpen ? ' on' : ''}" onclick="armOptOpen()"${p.objects.length ? '' : ' disabled'} title="${esc(tt('armory.optimize_title'))}">${tt('armory.optimize')} ${ARM.optOpen ? '▴' : '▾'}</button>
      <button class="mini${typeof armLit === 'function' && armLit().open ? ' on' : ''}" onclick="armLitToggle()"${p.objects.length ? '' : ' disabled'} title="${esc(tt('armory.lit_title'))}">${tt('armory.lit')}</button>
      <span style="flex:1"></span>
      <button class="mini" onclick="armFoldAll(false)" title="${esc(tt('armory.expand_all'))}">⊞</button>
      <button class="mini" onclick="armFoldAll(true)" title="${esc(tt('armory.collapse_all'))}">⊟</button>
      <button class="mini${gal ? '' : ' on'}" onclick="armObjSetting('armory_obj_view','list')">${tt('armory.as_list')}</button>
      <button class="mini${gal ? ' on' : ''}" onclick="armObjSetting('armory_obj_view','gallery')">${tt('armory.as_gallery')}</button>
    </div>
    ${ARM.optOpen && p.objects.length ? `<div class="armoptbox" id="armOptBox"></div>` : ''}
    ${p.objects.length && typeof armLit === 'function' && armLit().open ? armLitHtml() : ''}
    <div class="armobjlist" id="armObjList">
      ${p.objects.length ? '' : `<div class="empty armempty">${tt('armory.no_objects_yet')}</div>`}
      ${[...groups].map(([name, objs]) => armFoldHtml('g:' + name, name, objs, null)).join('')}
      ${p.collections.map(c => armFoldHtml('c:' + c.id, c.name, p.objects.filter(o => o.coll === c.id), c)).join('')}
    </div>
    ${shut ? '' : '<div class="armgrip armgriph armpropsgrip" id="armGripP"></div>'}
    <div class="armpropshead"><button class="armfold" onclick="armObjSetting('armory_props_shut', ${!shut})" title="${esc(tt('armory.props_fold_title'))}">${shut ? '▸' : '▾'} ${tt('armory.properties')}</button>
      <span class="count">${sel.length === 1 ? esc(armFullName(sel[0])) : sel.length ? ttN('armory.n_selected', sel.length) : ''}</span></div>
    ${shut ? '' : `<div class="armpropspane" id="armPropsPane"><div id="armProps">${sel.length === 1 ? armPropsHtml(sel[0]) : sel.length ? armMultiHtml(sel) : `<div class="count armnote">${tt('armory.nothing_selected')}</div>`}</div></div>`}`;
  armPropsGripWire();
  ['armObjList', 'armPropsPane'].forEach((id, i) => { const x = document.getElementById(id); if(x) x.scrollTop = tops[i]; });
  if(ARM.optOpen && typeof armOptPaint === 'function') armOptPaint();
  if(gal) armThumbsPaint();
  armDragWire(el);
  const tools = document.getElementById('armSelTools');
  if(tools) tools.innerHTML = armSelToolsHtml();
}
/* 2026-11-23: the bar over Properties sets how tall they are (armory_props_h),
   the objects above taking the rest; a double-click shares the room again. */
function armPropsGripWire(){
  const bar = document.getElementById('armGripP'), pane = document.getElementById('armPropsPane');
  if(!bar || !pane) return;
  const set = h => { pane.style.flex = h ? '0 0 ' + h + 'px' : ''; };
  set(armSize('props_h'));
  let h = 0;
  armGripDrag(bar, 'y', () => pane.getBoundingClientRect().height, (h0, d) => {
    const room = document.getElementById('armRight').clientHeight - 160;
    h = Math.round(Math.max(80, Math.min(h0 - d, room)));
    set(h);
  }, () => { if(h) armSizeSave('props_h', h); });
  bar.ondblclick = () => { armSizeSave('props_h', 0); set(0); };
}
// 100f: Duplicate and Detail sit beside the sliders, under Statistics
function armSelToolsHtml(){
  const n = armSelected().length;
  return `<button class="mini" onclick="armDuplicate()"${n ? '' : ' disabled'}>${tt('armory.duplicate_object')}</button>
    <button class="mini${ARM.detail ? ' on' : ''}" onclick="armDetailToggle()"${n === 1 || ARM.detail ? '' : ' disabled'} title="${esc(tt('armory.detail_title'))}">${tt('armory.detail')}</button>`;
}

function armFoldHtml(key, name, objs, coll){
  const p = armProj();
  const shut = p.ui.folded.includes(key);
  const allHidden = coll ? coll.hidden : objs.length && objs.every(o => o.hidden);
  const k = esc(key).replace(/'/g, "\\'");
  return `<div class="armfoldbox${coll ? ' coll' : ''}">
    <div class="armfoldhead" data-drop="${esc(key)}">
      <button class="armfold" onclick="armFold('${k}')">${shut ? '▸' : '▾'}</button>
      <button class="mini armeye" onclick="armFoldEye('${k}')" title="${esc(tt('armory.hide_show'))}">${allHidden ? '◌' : '●'}</button>
      <b class="armfoldname${objs.length && objs.every(o => ARM.sel.has(o.id)) ? ' sel' : ''}" onclick="armSelectFold('${k}', event)" ondblclick="armRenameFold('${k}', this)" title="${esc(tt('armory.fold_select_hint'))}">${esc(name)}</b><span class="count">${objs.length}</span>
      ${coll ? `<label class="count armexp" title="${esc(tt('armory.export_coll_title'))}"><input type="checkbox"${coll.export === false ? '' : ' checked'}
          onchange="armCollExport(${coll.id}, this.checked)"> ${tt('armory.export')}</label>
        <button class="mini armx" onclick="armCollDelete(${coll.id})" title="${esc(tt('armory.delete_collection'))}">✕</button>` : ''}
    </div>
    ${shut ? '' : armObjGallery() ? `<div class="armotiles">${objs.map(armObjTileHtml).join('')}</div>`
      : `<div class="armrows">${objs.map(armObjRowHtml).join('')}</div>`}
  </div>`;
}

/* 2026-11-23: a click on a collection's (or group's) name selects what is in
   it; Shift or Ctrl adds it to the selection. */
function armSelectFold(key, ev){
  const p = armProj();
  const objs = key.startsWith('c:') ? p.objects.filter(o => o.coll === +key.slice(2))
    : p.objects.filter(o => !o.coll && o.name === key.slice(2));
  if(!(ev && (ev.shiftKey || ev.ctrlKey))) ARM.sel.clear();
  objs.filter(o => !o.hidden).forEach(o => ARM.sel.add(o.id));
  ARM.active = objs.length ? objs[objs.length - 1].id : ARM.active;
  armPaintObjects(); armPaintSliders(); armFrame();
}

/* A tile: the object drawn small (armThumbsPaint), named under it. */
function armObjSig(o){
  let h = 5381;
  const t = JSON.stringify([o.src, o.dye, o.sheet]);
  for(let i = 0; i < t.length; i++) h = ((h << 5) + h + t.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}
function armObjTileHtml(o){
  return `<div class="armotile${ARM.sel.has(o.id) ? ' sel' : ''}${ARM.active === o.id && ARM.sel.size > 1 ? ' act' : ''}${o.hidden ? ' off' : ''}" data-id="${o.id}"
      onclick="armSelectRow(${o.id}, event)" onmouseenter="armHoverRow(${o.id})" onmouseleave="armHoverRow(null)" title="${esc(armFullName(o))}">
    <img class="armthumb" data-thumb="o:${o.id}:${armObjSig(o)}" alt="">
    <span class="armotilename" ondblclick="event.stopPropagation();armRenameRow(${o.id}, this)">${esc(o.mesh)}${o.flag ? ` <i class="count">${tt('armory.opt')}</i>` : ''}</span>
    <button class="mini armeye" onclick="event.stopPropagation();armHide(${o.id})" title="${esc(tt('armory.hide_show'))}">${o.hidden ? '◌' : '●'}</button>
  </div>`;
}

/* Rows and tiles are dragged onto a fold's head: onto a collection to go
   into it, onto a group to leave any collection and take that group type. */
function armDragWire(el){
  el.querySelectorAll('.armrow[data-id], .armotile[data-id]').forEach(r => {
    r.draggable = true;
    r.ondragstart = e => {
      const id = +r.dataset.id;
      const ids = ARM.sel.has(id) ? [...ARM.sel] : [id];
      e.dataTransfer.setData('text/x-arm-objects', JSON.stringify(ids));
      e.dataTransfer.effectAllowed = 'move';
    };
  });
  el.querySelectorAll('.armfoldhead[data-drop]').forEach(h => {
    h.ondragover = e => { if(e.dataTransfer.types.includes('text/x-arm-objects')){ e.preventDefault(); h.classList.add('armdrop'); } };
    h.ondragleave = () => h.classList.remove('armdrop');
    h.ondrop = e => {
      e.preventDefault(); h.classList.remove('armdrop');
      let ids;
      try{ ids = JSON.parse(e.dataTransfer.getData('text/x-arm-objects')); }catch(err){ return; }
      armMoveTo(ids, h.dataset.drop);
    };
  });
}
/* `to` is a fold's key: c:<id> a collection, g:<type> a group outside them. */
function armMoveTo(ids, to){
  const p = armProj();
  const objs = ids.map(armObj).filter(Boolean);
  if(!objs.length) return;
  if(to.startsWith('c:')) objs.forEach(o => { o.coll = +to.slice(2); });
  else objs.forEach(o => { o.coll = null; o.name = to.slice(2); });
  // the fold they land in opens
  const f = p.ui.folded, i = f.indexOf(to);
  if(i >= 0) f.splice(i, 1);
  armRepaint();
}

/* Blender's M: a menu by the pointer of every collection, the model outside
   them, and a new collection, for the selected objects. */
function armMoveMenu(x, y){
  const sel = armSelected();
  if(!sel.length){ toast(tt('armory.nothing_selected')); return; }
  const p = armProj();
  armMoveMenuClose();
  const m = document.createElement('div');
  m.id = 'armMoveMenu'; m.className = 'armmenu';
  m.innerHTML = `<div class="count">${ttN('armory.move_to_n', sel.length)}</div>
    <button onclick="armMoveMenuPick('none')">${tt('armory.no_collection')}</button>
    ${p.collections.map(c => `<button onclick="armMoveMenuPick('c:${c.id}')">${esc(c.name)}</button>`).join('')}
    <button onclick="armMoveMenuPick('new')">＋ ${tt('armory.new_collection_option')}</button>`;
  document.body.appendChild(m);
  m.style.left = Math.max(8, Math.min(x, innerWidth - m.offsetWidth - 8)) + 'px';
  m.style.top = Math.max(8, Math.min(y, innerHeight - m.offsetHeight - 8)) + 'px';
  ARM.moveAway = e => { if(e.type === 'keydown' ? e.key === 'Escape' : !m.contains(e.target)){ if(e.type === 'keydown') e.stopPropagation(); armMoveMenuClose(); } };
  document.addEventListener('pointerdown', ARM.moveAway, true);
  document.addEventListener('keydown', ARM.moveAway, true);
}
function armMoveMenuClose(){
  document.getElementById('armMoveMenu')?.remove();
  if(ARM.moveAway){
    document.removeEventListener('pointerdown', ARM.moveAway, true);
    document.removeEventListener('keydown', ARM.moveAway, true);
    ARM.moveAway = null;
  }
}
function armMoveMenuPick(to){
  armMoveMenuClose();
  if(to === 'new') return armNewCollection();
  if(to === 'none'){ armSelected().forEach(o => { o.coll = null; }); return armRepaint(); }
  armMoveTo([...ARM.sel], to);
}

function armObjRowHtml(o){
  const sw = o.dye && o.dye.color ? `<span class="armswatch" style="background:rgb(${o.dye.color.join(',')})"></span>` : '';
  const empty = !(o.src || []).length;
  return `<div class="armrow${ARM.sel.has(o.id) ? ' sel' : ''}${ARM.active === o.id && ARM.sel.size > 1 ? ' act' : ''}${o.hidden ? ' off' : ''}" data-id="${o.id}" onclick="armSelectRow(${o.id}, event)"
      onmouseenter="armHoverRow(${o.id})" onmouseleave="armHoverRow(null)">
    <button class="mini armeye" onclick="event.stopPropagation();armHide(${o.id})" title="${esc(tt('armory.hide_show'))}">${o.hidden ? '◌' : '●'}</button>
    <span class="armrowname" ondblclick="event.stopPropagation();armRenameRow(${o.id}, this)" title="${esc(tt('armory.rename_hint'))}">${esc(o.mesh)}${o.flag ? ` <i class="count">${tt('armory.opt')}</i>` : ''}${empty ? ` <i class="count">${tt('armory.empty_object')}</i>` : ''}</span>
    ${o.material ? `<span class="pill">${esc(armMatLabel(o.material))}</span>` : ''}${sw}
    ${o.weights ? `<span class="pill" title="${esc(tt('armory.weights_transferred'))}">W</span>` : ''}
    <button class="mini armx" onclick="event.stopPropagation();armDeleteObject(${o.id})" title="${esc(tt('armory.delete_object'))}">✕</button>
  </div>`;
}

function armSelected(){ return armProj().objects.filter(o => ARM.sel.has(o.id)); }
function armRepaint(){ armSave(); armPaintObjects(); armPaintAssets(); armPaintBar(); armFrame(); }

/* The active object is Blender's: the last one picked, outlined lighter, the
   one Merge joins the others into. Shift on a selected object makes it the
   active one, Shift on the active one lets it go; Ctrl (the list) toggles. */
function armActiveFix(){
  if(ARM.active == null || !ARM.sel.has(ARM.active)) ARM.active = ARM.sel.size ? [...ARM.sel].pop() : null;
}
function armSelect(id, ev){
  const add = ev && (ev.shiftKey || ev.ctrlKey);
  // the same one object clicked again changes nothing, and the row stays the
  // element it was: a double click on it is a rename (99h)
  if(!add && id != null && ARM.sel.size === 1 && ARM.sel.has(id)) return;
  if(!add) ARM.sel.clear();
  ARM.dyeQuiet = false;
  if(add && ARM.sel.has(id)){
    if(ev.ctrlKey || ARM.active === id){ ARM.sel.delete(id); if(ARM.active === id) ARM.active = null; }
    else ARM.active = id;
  }else if(id != null){ ARM.sel.add(id); ARM.active = id; }
  armActiveFix();
  armPaintObjects(); armFrame();
  if(typeof armPaintSliders === 'function') armPaintSliders();
}
// 100d: in the list, Ctrl adds or takes one row and Shift selects the run
// from the last row clicked, across folds and collections in the order they
// are drawn; the viewport keeps Blender's Shift-adds (armSelect)
function armSelectRow(id, ev){
  if(ev && ev.shiftKey && ARM.anchor != null && ARM.anchor !== id){
    const ids = [...document.querySelectorAll('.armrow[data-id]')].map(r => +r.dataset.id);
    const a = ids.indexOf(ARM.anchor), b = ids.indexOf(id);
    if(a >= 0 && b >= 0){
      if(!ev.ctrlKey) ARM.sel.clear();
      ids.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(x => ARM.sel.add(x));
      ARM.active = id;
      armPaintObjects(); armFrame();
      if(typeof armPaintSliders === 'function') armPaintSliders();
      return;
    }
  }
  ARM.anchor = id;
  armSelect(id, ev && {ctrlKey: ev.ctrlKey, shiftKey: ev.shiftKey && !ev.ctrlKey});
}
function armHide(id){
  const o = armObj(id); if(!o) return;
  o.hidden = !o.hidden; armRepaint();
}
function armDeleteObject(id){
  const p = armProj();
  p.objects = p.objects.filter(o => o.id !== id);
  ARM.sel.delete(id);
  armRepaint();
}
function armHoverRow(id){ ARM.hover = id; armFrame(); }

function armFold(key){
  const f = armProj().ui.folded;
  const i = f.indexOf(key);
  if(i >= 0) f.splice(i, 1); else f.push(key);
  armSave(); armPaintObjects();
}
function armFoldEye(key){
  const p = armProj();
  if(key.startsWith('c:')){
    const c = p.collections.find(x => x.id === +key.slice(2));
    if(c) c.hidden = !c.hidden;
  }else{
    const objs = p.objects.filter(o => !o.coll && o.name === key.slice(2));
    const hide = !objs.every(o => o.hidden);
    objs.forEach(o => { o.hidden = hide; });
  }
  armRepaint();
}

/* --- collections ------------------------------------------------------------- */

/* A new collection is made at once, named in its own fold (no dialog): the
   selected objects go into it and its name is ready to be typed over. */
function armNewCollection(){
  const p = armProj();
  const c = {id: p.nextId++, name: tt('armory.collection_default', {n: p.collections.length + 1}), hidden: false, export: true};
  p.collections.push(c);
  for(const o of armSelected()) o.coll = c.id;
  armRepaint();
  const head = document.querySelector(`.armfoldhead[data-drop="c:${c.id}"] .armfoldname`);
  if(head){ head.scrollIntoView({block: 'nearest'}); armRenameFold('c:' + c.id, head); }
}
function armCollExport(id, on){
  const c = armProj().collections.find(x => x.id === id);
  if(c){ c.export = on; armSave(); }
}
function armCollDelete(id){
  const p = armProj();
  const c = p.collections.find(x => x.id === id);
  if(!c) return;
  const objs = p.objects.filter(o => o.coll === id);
  if(objs.length && confirm(ttN('armory.delete_collection_objects', objs.length, {name: c.name})))
    p.objects = p.objects.filter(o => o.coll !== id);
  else objs.forEach(o => { o.coll = null; });
  p.collections = p.collections.filter(x => x.id !== id);
  armRepaint();
}
function armSetCollection(id, v){
  const o = armObj(id); if(!o) return;
  if(v === 'new'){ ARM.sel = new Set([id]); return armNewCollection(); }
  o.coll = v ? +v : null;
  armRepaint();
}

/* --- names, the Blender kit's way -------------------------------------------- */

/* `prefix__part` is the whole name; the group type is what is before the
   first `__`, the mesh name what is after (armory.split_name). */
function armFullName(o){ return `${o.name}__${o.mesh}`; }
function armSplitName(full){
  const i = full.indexOf('__');
  return i < 0 ? [full, full] : [full.slice(0, i), full.slice(i + 2)];
}
/* The kit's Fix names: `name` becomes `name__name`, `a_b` becomes `a__b`,
   `hair1`/`hair_1`/`hair__1` become `hair__hair_1`, a trailing `.001` goes. */
function armFixName(full){
  let s = full.replace(/\.\d{3}$/, '').replace(/__opt$/i, '');
  let m = s.match(/^([A-Za-z]+)_{0,2}(\d+)$/);
  if(m) return `${m[1]}__${m[1]}_${m[2]}`;
  if(!s.includes('__')){
    if(s.includes('_')){ const i = s.indexOf('_'); return `${s.slice(0, i)}__${s.slice(i + 1)}`; }
    return `${s}__${s}`;
  }
  return s;
}
function armRenameFix(id){
  const o = armObj(id); if(!o) return;
  const before = armFullName(o);
  // a name the page split from a non-kit name has the same type and mesh
  const base = o.name === o.mesh ? o.mesh : before;
  [o.name, o.mesh] = armSplitName(armFixName(base));
  toast(tt('armory.renamed', {from: before, to: armFullName(o)}));
  armRepaint();
}
/* The group type picked from a list, which replaces it: another group of the
   model (the object joins that group) or a weapon prefix (the game's slot
   names, explained by armPrefixHelp). Typing one in stays possible. */
function armGroupPickHtml(current, onchange){
  const groups = [...new Set(armProj().objects.map(o => o.name))].sort((a, b) => a.localeCompare(b));
  const opt = v => `<option value="${esc(v)}"${v === current ? ' selected' : ''}>${esc(v)}</option>`;
  return `<select class="armgrouppick" onchange="if(this.value)${onchange}" title="${esc(tt('armory.group_pick_title'))}">
    <option value="">${tt('armory.group_pick')}</option>
    <optgroup label="${esc(tt('armory.group_pick_groups'))}">${groups.map(opt).join('')}</optgroup>
    <optgroup label="${esc(tt('armory.group_pick_prefixes'))}">${ARM_PREFIXES.map(opt).join('')}</optgroup></select>`;
}
/* --- rename in place (99h) ---------------------------------------------------

   A double click on an object's row edits its mesh name where it is, and on
   a group's fold the group type of every object in it (a collection's fold,
   its name). Enter keeps, Esc puts back, leaving the box keeps; the kit's
   rules apply as Fix names applies them. */
function armInlineEdit(el, value, commit){
  const inp = document.createElement('input');
  inp.className = 'arminline';
  inp.value = value;
  let done = false;
  const end = keep => {
    if(done) return;
    done = true;
    const v = inp.value.trim();
    if(keep && v && v !== value) commit(v); else armPaintObjects();
  };
  inp.onkeydown = e => {
    e.stopPropagation();
    if(e.key === 'Enter'){ e.preventDefault(); end(true); }
    else if(e.key === 'Escape'){ e.preventDefault(); end(false); }
  };
  inp.onblur = () => end(true);
  inp.onclick = inp.ondblclick = e => e.stopPropagation();
  el.replaceWith(inp);
  inp.focus(); inp.select();
}
/* A mesh name typed: a trailing .001 and __opt go, spaces become
   underscores, and a whole name (type__mesh) is split and fixed as the kit's
   Fix names does. */
function armRenameRow(id, el){
  const o = armObj(id); if(!o) return;
  armInlineEdit(el, o.mesh, v => {
    v = v.replace(/\.\d{3}$/, '').replace(/__opt$/i, '').replace(/\s+/g, '_');
    if(v.includes('__')) [o.name, o.mesh] = armSplitName(armFixName(v));
    else o.mesh = v;
    armRepaint();
  });
}
/* A group type: no `__` inside it, since that is where the mesh name begins. */
const armCleanType = v => v.replace(/\.\d{3}$/, '').trim().replace(/_{2,}/g, '_');
function armRenameFold(key, el){
  const p = armProj();
  if(key.startsWith('c:')){
    const c = p.collections.find(x => x.id === +key.slice(2));
    if(c) armInlineEdit(el, c.name, v => { c.name = v; armRepaint(); });
    return;
  }
  const from = key.slice(2);
  armInlineEdit(el, from, v => {
    const t = armCleanType(v);
    if(!t || t === from) return armPaintObjects();
    p.objects.filter(o => !o.coll && o.name === from).forEach(o => { o.name = t; });
    // the fold stays as it was, under its new name
    const f = p.ui.folded, i = f.indexOf(key);
    if(i >= 0) f[i] = 'g:' + t;
    armRepaint();
  });
}

function armSetName(id, part, v){
  const o = armObj(id); if(!o) return;
  v = (v || '').trim();
  if(!v) return armPaintObjects();
  o[part] = v; armRepaint();
}
function armToggleOpt(id){ const o = armObj(id); if(!o) return; o.flag = o.flag ? 0 : 1; armRepaint(); }
function armSetMaterial(id, v){ const o = armObj(id); if(!o) return; o.material = v; armDyeChanged(o); armRepaint(); }

/* --- duplicate, merge, an empty object -------------------------------------- */

function armDuplicate(){
  const p = armProj();
  const made = [];
  for(const o of armSelected()){
    const c = JSON.parse(JSON.stringify(o));
    c.id = p.nextId++;
    c.mesh = armUniqueMesh(o.name, o.mesh);
    c.weights = o.weights || null;
    p.objects.splice(p.objects.indexOf(o) + 1, 0, c);
    made.push(c.id);
  }
  ARM.sel = new Set(made);
  armRepaint();
}
/* 2026-11-23: Ctrl+C and Ctrl+V. The copy carries the assets its parts come
   from, so it pastes into another project (a session opened since) too. */
function armCopy(){
  const sel = armSelected();
  if(!sel.length) return;
  const p = armProj(), keys = new Set(sel.flatMap(o => (o.src || []).map(pc => pc.asset)));
  ARM.clip = JSON.stringify({objects: sel, assets: p.assets.filter(a => keys.has(armAssetKey(a))),
    colls: p.collections.filter(c => sel.some(o => o.coll === c.id))});
  toast(ttN('armory.copied_n', sel.length));
}
function armPaste(){
  if(!ARM.clip) return;
  const clip = JSON.parse(ARM.clip), p = armProj();
  for(const a of clip.assets){
    const k = armAssetKey(a);
    if(p.assets.some(x => armAssetKey(x) === k)) continue;
    p.assets.push(a);
    if(!ARM.assets.has(k)) armLoadAsset(a);
  }
  const made = [];
  for(const o of clip.objects){
    const c = JSON.parse(JSON.stringify(o));
    c.id = p.nextId++;
    c.mesh = armUniqueMesh(c.name, c.mesh);
    // into the collection of the same name, when this project has one
    if(c.coll != null){
      const was = clip.colls.find(x => x.id === c.coll);
      const here = was && p.collections.find(x => x.name === was.name);
      c.coll = here ? here.id : null;
    }
    p.objects.push(c);
    made.push(c.id);
  }
  ARM.sel = new Set(made);
  ARM.active = made[made.length - 1];
  armRepaint();
  toast(ttN('armory.pasted_n', made.length));
}
function armUniqueMesh(type, mesh){
  const taken = new Set(armProj().objects.filter(o => o.name === type).map(o => o.mesh));
  const stem = mesh.replace(/_\d+$/, '');
  for(let i = 2; ; i++) if(!taken.has(`${stem}_${i}`)) return `${stem}_${i}`;
}
/* Merged objects keep each piece where it stood: the piece takes its old
   object's whole matrix as its own, and the new object starts at rest. */
function armMerge(){
  const objs = armSelected();
  if(objs.length < 2) return;
  const p = armProj();
  // joined into the active object: its name, place in the list and dye
  armActiveFix();
  const first = objs.find(o => o.id === ARM.active) || objs[0];
  const src = [];
  for(const o of objs){
    const om = armObjMatrix(o, armPivot(o));
    for(const pc of o.src || []) src.push(Object.assign({}, pc, {xf: pc.xf ? armMul(om, pc.xf) : om}));
  }
  const merged = {id: p.nextId++, src, name: first.name, mesh: first.mesh, flag: first.flag,
                  hidden: false, coll: first.coll, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1],
                  material: first.material, dye: first.dye, weights: null};
  const at = p.objects.indexOf(first);
  p.objects = p.objects.filter(o => !ARM.sel.has(o.id));
  p.objects.splice(Math.min(at, p.objects.length), 0, merged);
  ARM.sel = new Set([merged.id]);
  toast(ttN('armory.merged_n', objs.length));
  armRepaint();
}
/* A group with no triangles: an optional variant the game can pick that
   shows nothing (a soldier with no helmet among those with one). */
function armBlank(){
  const p = armProj();
  const like = armSelected()[0];
  // like the selected object, else like the model's first, else a helmet
  const type = like ? like.name : p.objects.length ? p.objects[0].name : 'helmet';
  const o = {id: p.nextId++, src: [], name: type, mesh: armUniqueMesh(type, 'empty'), flag: 0,
             hidden: false, coll: like ? like.coll : null, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1],
             material: '', dye: null};
  p.objects.push(o);
  ARM.sel = new Set([o.id]);
  armRepaint();
}

/* --- transfer weights --------------------------------------------------------- */

async function armTransferWeights(id){
  const o = armObj(id); if(!o) return;
  const mode = (document.getElementById('armWMode') || {}).value || 'face';
  const btn = document.getElementById('armWGo');
  if(btn){ btn.disabled = true; btn.textContent = tt('armory.working'); }
  try{
    const r = await api.post('/api/armory/transfer_weights', {project: armProj(), id, mode});
    if(r.error) throw new Error(r.error);
    o.weights = r;
    toast(ttN('armory.weights_done', r.n, {bones: r.bones.filter(Boolean).length}));
  }catch(e){ toast(errText(e), 6000); }
  armRepaint();
}
// the Med2 skeleton in the user's order (100b): head, torso, pelvis, the
// right arm from the hand in, the left, then the legs; armory.MED2_BONES
const ARM_BONES = ['bone_head', 'bone_torso', 'bone_abs', 'bone_pelvis',
  'bone_rhand', 'bone_relbow', 'bone_rupperarm', 'bone_rclavical',
  'bone_lhand', 'bone_lelbow', 'bone_lupperarm', 'bone_lclavical',
  'bone_rthigh', 'bone_rlowerleg', 'bone_rfoot', 'bone_lthigh', 'bone_llowerleg', 'bone_lfoot',
  'bone_jaw', 'bone_eyebrow'];
const armRigRowsHtml = id => `<div class="armpropsrow"><select id="armRigA" title="${esc(tt('armory.rig_first'))}">${ARM_BONES.map(b => `<option>${b}</option>`).join('')}</select>
      <select id="armRigB" title="${esc(tt('armory.rig_second_title'))}"><option value="">${tt('armory.rig_second')}</option>${ARM_BONES.map(b => `<option>${b}</option>`).join('')}</select>
      <span class="armtip" title="${esc(tt('armory.rig_second_title'))}">?</span></div>
    <div class="armpropsrow"><label class="armrange" title="${esc(tt('armory.rig_share_title'))}">${tt('armory.rig_share')}<input type="range" id="armRigShare" min="50" max="100" value="100"
        oninput="document.getElementById('armRigPct').value=this.value"></label>
      <input type="number" class="armpct" id="armRigPct" min="50" max="100" step="1" value="100"
        oninput="const v=Math.max(50,Math.min(100,+this.value||100));document.getElementById('armRigShare').value=v">%
      <button class="mini" onclick="document.getElementById('armRigShare').value=100;document.getElementById('armRigPct').value=100" title="${esc(tt('armory.rig_all_title'))}">${tt('armory.rig_all')}</button>
      <button class="mini" onclick="armRigBones(${id})" title="${esc(tt('armory.rig_bones_title'))}">${tt('armory.rig_bones')}</button></div>`;
async function armRigBones(id){
  const ids = ARM.sel.size ? [...ARM.sel] : [id];
  const val = k => (document.getElementById(k) || {}).value || '';
  const bones = [val('armRigA'), val('armRigB')].filter(Boolean);
  const share = (+val('armRigShare') || 100) / 100;
  try{
    const r = await api.post('/api/armory/rig_bones', {project: armProj(), ids, bones, share});
    if(r.error) throw new Error(r.error);
    let n = 0;
    for(const [k, w] of Object.entries(r)){ const o = armObj(+k); if(o){ o.weights = w; n++; } }
    toast(ttN('armory.rig_done', n, {bones: bones.join(' + ')}));
  }catch(e){ toast(errText(e), 6000); }
  armRepaint();
}
function armClearWeights(id){ const o = armObj(id); if(!o) return; o.weights = null; armRepaint(); }

/* --- the properties of one object ------------------------------------------ */

function armPropsHtml(o){
  const p = armProj();
  const d = o.dye || {};
  const presets = ARM_PRESETS.map(x => `<option value="g:${x.id}">${esc(armPresetLabel(x.id))}</option>`).join('')
    + (ARM.userPresets || []).map((x, i) => `<option value="u:${i}">${esc(x.name)}</option>`).join('');
  const hex = c => '#' + (c || [128, 128, 128]).map(v => v.toString(16).padStart(2, '0')).join('');
  const chan = ch => {
    const c = (d.channels || {})[ch] || {};
    return `<label class="armchan"><input type="checkbox"${c.on ? ' checked' : ''} onchange="armDyeChannel(${o.id},'${ch}','on',this.checked)">
      ${armChanLabel(ch)} <input type="color" value="${hex(c.color)}" onchange="armDyeChannel(${o.id},'${ch}','color',this.value)"></label>`;
  };
  const layers = d.pattern ? d.pattern.centers.map((c, i) => {
    const to = (d.pattern.colors || {})[i];
    return `<label class="armlayer" title="${esc(tt('armory.layer_title'))}">
      <span class="armswatch big" style="background:rgb(${c.map(Math.round).join(',')})"></span>
      <span class="count">${Math.round(d.pattern.shares[i] * 100)}%</span> →
      <input type="color" value="${to ? hex(to) : hex(c.map(Math.round))}" onchange="armDyeLayer(${o.id},${i},this.value)">
      ${to ? `<button class="mini" onclick="armDyeLayer(${o.id},${i},null)">✕</button>` : ''}</label>`;
  }).join('') : '';
  return `<div class="armprops">
    ${armSecHtml('names', tt('armory.sec_names'), `
    <div class="armpropsrow"><label>${tt('armory.group_type')}<input value="${esc(o.name)}" onchange="armSetName(${o.id},'name',this.value)"></label>
      <label>${tt('armory.mesh_name')}<input value="${esc(o.mesh)}" onchange="armSetName(${o.id},'mesh',this.value)"></label></div>
    <div class="armpropsrow">${armGroupPickHtml(o.name, `armSetName(${o.id},'name',this.value)`)}
      <button class="mini armhelp" onclick="armPrefixHelp()" title="${esc(tt('armory.prefix_help_title'))}">?</button></div>
    <div class="armpropsrow">
      <label class="armcheck"><input type="checkbox"${o.flag ? ' checked' : ''} onchange="armToggleOpt(${o.id})"> ${tt('armory.optional_short')}</label>
      <span class="armtip" title="${esc(tt('armory.optional'))}">?</span>
      <button class="mini" onclick="armRenameFix(${o.id})" title="${esc(tt('armory.fix_name_title'))}">${tt('armory.fix_name')}</button>
    </div>
    <div class="armpropsrow"><label>${tt('armory.material')}<select onchange="armSetMaterial(${o.id}, this.value)">
        <option value="">${tt('armory.mat_none')}</option>${ARM_MATERIALS.map(m => `<option value="${m}"${o.material === m ? ' selected' : ''}>${esc(armMatLabel(m))}</option>`).join('')}</select></label>
      <label>${tt('armory.collection')}<select onchange="armSetCollection(${o.id}, this.value)">
        <option value="">${tt('armory.no_collection')}</option>${p.collections.map(c => `<option value="${c.id}"${o.coll === c.id ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}
        <option value="new">${tt('armory.new_collection_option')}</option></select></label></div>`)}
    ${armSecHtml('weights', tt('armory.weights'), `
    <div class="armpropsrow"><span class="count">${!o.weights ? tt('armory.weights_from_source')
      : o.weights.mode === 'rig' ? tt('armory.weights_rigged', {bones: (o.weights.bones || []).join(' + ')})
      : tt('armory.weights_own', {mode: armWModeLabel(o.weights.mode)})}</span></div>
    ${armWeightsRowHtml(`armTransferWeights(${o.id})`)}
    ${o.weights ? `<div class="armpropsrow"><button class="mini" onclick="armClearWeights(${o.id})">${tt('armory.clear_weights')}</button></div>` : ''}
    ${armRigRowsHtml(o.id)}`)}
    ${armSecHtml('recolour', tt('armory.recolour'), `
    <div class="armpropsrow"><select onchange="armDyePreset(${o.id}, this.value)"><option value="">${tt('armory.preset')}</option>${presets}</select>
      <input type="color" value="${hex(d.color)}" onchange="armDyeSet(${o.id},'color',this.value)" title="${esc(tt('armory.dye_colour'))}">
      <button class="mini" onclick="armEyedrop(v => armDyeSet(${o.id},'color',v))" title="${esc(tt('armory.eyedrop_title'))}">💧</button>
      <select onchange="armDyeSet(${o.id},'blend',this.value)">${ARM_BLENDS.map(b => `<option value="${b}"${(d.blend || 'keepshade') === b ? ' selected' : ''}>${esc(armBlendLabel(b))}</option>`).join('')}</select></div>
    <div class="armpropsrow"><label class="armrange">${tt('armory.strength')}<input type="range" min="0" max="100" value="${Math.round((d.strength == null ? 1 : d.strength) * 100)}"
        oninput="armDyeSet(${o.id},'strength',this.value/100,true)"></label>
      <label class="armcheck" title="${esc(tt('armory.keep_white_title'))}"><input type="checkbox"${d.keepWhite === false ? '' : ' checked'} onchange="armDyeSet(${o.id},'keepWhite',this.checked)"> ${tt('armory.keep_white')}</label></div>
    <div class="armpropsrow armchans" title="${esc(tt('armory.channels_title'))}">${ARM_CHANNELS.map(chan).join('')}</div>
    <div class="armpropsrow"><button class="mini" onclick="armDetectPattern(${o.id})" title="${esc(tt('armory.detect_title'))}">${tt('armory.detect_layers')}</button>
      <button class="mini" onclick="armSavePreset(${o.id})"${o.dye ? '' : ' disabled'}>${tt('armory.save_preset')}</button>
      <button class="mini" onclick="armDyeClear(${o.id})"${o.dye ? '' : ' disabled'}>${tt('armory.clear_dye')}</button></div>
    ${layers ? `<div class="armlayers">${layers}</div>` : ''}`)}
    ${armSecHtml('stamps', tt('armory.stamps'), armStampsHtml(o))}
    ${typeof armOptimized === 'function' && armOptimized(o) ? `<div class="armpropsrow"><span class="count">${tt('armory.opt_is_on')}</span>
      <button class="mini" onclick="armOptRestore(${o.id})" title="${esc(tt('armory.opt_restore_title'))}">${tt('armory.opt_restore')}</button></div>` : ''}
    ${o.lit ? `<div class="armpropsrow"><span class="count">${tt('armory.lit_is_on')}</span>
      <button class="mini" onclick="armLitRemove([${o.id}])" title="${esc(tt('armory.lit_remove_title'))}">${tt('armory.lit_remove')}</button></div>` : ''}
    <div class="count armnote">${tt('armory.object_facts', {tris: armObjTris(o).toLocaleString(), pieces: (o.src || []).length})}</div>
  </div>`;
}

/* 2026-11-23: each part of Properties folds, and stays as it was left
   (armory_props_closed). */
function armSecHtml(key, title, body){
  const shut = ((state.settings || {}).armory_props_closed || []).includes(key);
  return `<details class="armsec"${shut ? '' : ' open'} ontoggle="armSecToggle('${key}', this.open)">
    <summary class="armsect">${title}</summary>${body}</details>`;
}
function armSecToggle(key, open){
  const list = ((state.settings || {}).armory_props_closed || []).filter(k => k !== key);
  if(!open) list.push(key);
  state.settings.armory_props_closed = list;
  api.post('/api/settings', {armory_props_closed: list}).catch(() => {});
}
/* Transfer weights, with the selection's active object named beside it. */
function armWeightsRowHtml(go){
  const act = armObj(ARM.active) || armSelected()[0];
  return `<div class="armpropsrow"><select id="armWMode">${['face', 'vertex', 'edge'].map(m => `<option value="${m}">${esc(armWModeLabel(m))}</option>`).join('')}</select>
      <button class="mini" id="armWGo" onclick="${go}" title="${esc(tt('armory.transfer_weights_title'))}">${tt('armory.transfer_weights')}</button>
      ${act ? `<span class="count armactive" title="${esc(tt('armory.active_title'))}">${tt('armory.active_short', {name: esc(armFullName(act))})}</span>` : ''}</div>`;
}

/* --- several objects at once (100e) ----------------------------------------- */

function armMultiHtml(sel){
  const presets = ARM_PRESETS.map(x => `<option value="g:${x.id}">${esc(armPresetLabel(x.id))}</option>`).join('')
    + (ARM.userPresets || []).map((x, i) => `<option value="u:${i}">${esc(x.name)}</option>`).join('');
  const same = k => sel.every(o => o[k] === sel[0][k]) ? sel[0][k] : '';
  return `<div class="armprops">
    <div class="count armnote">${ttN('armory.n_selected', sel.length)}${(() => { const a = armObj(ARM.active);
      return a ? ` · ${tt('armory.active_is', {name: esc(armFullName(a))})}` : ''; })()}</div>
    ${armSecHtml('names', tt('armory.sec_names'), `
    <div class="armpropsrow">${armGroupPickHtml(same('name'), `armMultiName('name',this.value)`)}
      <button class="mini armhelp" onclick="armPrefixHelp()" title="${esc(tt('armory.prefix_help_title'))}">?</button></div>
    <div class="armpropsrow"><label>${tt('armory.group_type')}<input value="${esc(same('name'))}" placeholder="${esc(tt('armory.multi_mixed'))}" onchange="armMultiName('name', this.value)"></label>
      <label title="${esc(tt('armory.multi_mesh_title'))}">${tt('armory.mesh_name')}<input value="${esc(same('mesh'))}" placeholder="${esc(tt('armory.multi_mixed'))}" onchange="armMultiName('mesh', this.value)"></label></div>`)}
    ${armSecHtml('weights', tt('armory.weights'), `${armWeightsRowHtml('armMultiTransfer()')}
    ${armRigRowsHtml(sel[0].id)}`)}
    ${armSecHtml('recolour', tt('armory.recolour'), `
    <div class="armpropsrow"><select onchange="armMultiDye('preset', this.value)"><option value="">${tt('armory.preset')}</option>${presets}</select>
      <input type="color" value="#962020" onchange="armMultiDye('color', this.value)" title="${esc(tt('armory.dye_colour'))}">
      <button class="mini" onclick="armEyedrop(v => armMultiDye('color', v))" title="${esc(tt('armory.eyedrop_title'))}">💧</button>
      <button class="mini" onclick="armMultiDye('clear')">${tt('armory.clear_dye')}</button></div>`)}
  </div>`;
}
// One name for all: the group type as given, the mesh name numbered where
// two would clash (helmet_01, helmet_02), as the mods number their meshes
function armMultiName(part, v){
  v = (v || '').trim();
  const sel = armSelected();
  if(!v || !sel.length) return armPaintObjects();
  if(part === 'mesh' && sel.length > 1){
    const base = v.replace(/\.\d{3}$/, '').replace(/__opt$/i, '').replace(/__+/g, '_').replace(/_?\d+$/, '') || v;
    const taken = new Set(armProj().objects.filter(o => !ARM.sel.has(o.id)).map(o => o.mesh));
    let n = 1;
    for(const o of sel){
      let name;
      do{ name = `${base}_${String(n++).padStart(2, '0')}`; }while(taken.has(name));
      o.mesh = name;
    }
  }else sel.forEach(o => o[part] = v);
  armRepaint();
}
function armMultiDye(kind, v){
  const sel = armSelected();
  for(const o of sel){
    if(kind === 'clear'){ o.dye = null; armDyeChanged(o); continue; }
    if(kind === 'preset'){
      const pr = !v ? null : v.startsWith('g:') ? ARM_PRESETS.find(x => x.id === v.slice(2)) : (ARM.userPresets || [])[+v.slice(2)];
      if(!pr) return;
      const d = armDye(o);
      Object.assign(d, {color: pr.color.slice(), blend: pr.blend || 'keepshade', metal: !!pr.metal,
                        desat: pr.desat || 0, strength: pr.strength == null ? 1 : pr.strength});
      if(pr.channels) d.channels = JSON.parse(JSON.stringify(pr.channels));
    }else{
      const d = armDye(o); d.color = armHexRgb(v); if(!d.strength) d.strength = 1;
    }
    armDyeChanged(o);
  }
  armRepaint();
}
// Each in turn, from the model as it stands, then one save: one Undo step
async function armMultiTransfer(){
  const mode = (document.getElementById('armWMode') || {}).value || 'face';
  const btn = document.getElementById('armWGo');
  if(btn){ btn.disabled = true; btn.textContent = tt('armory.working'); }
  let done = 0;
  for(const o of armSelected()){
    try{
      const r = await api.post('/api/armory/transfer_weights', {project: armProj(), id: o.id, mode});
      if(r.error) throw new Error(r.error);
      o.weights = r; done++;
    }catch(e){ toast(`${o.mesh}: ${errText(e)}`, 6000); }
  }
  toast(ttN('armory.multi_weights_done', done));
  armRepaint();
}

/* --- recolour ------------------------------------------------------------------ */

const armHexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
// a colour picked anywhere on the screen, the model included (the browser's
// own eyedropper: Chrome and Edge have it, Firefox does not yet)
async function armEyedrop(then){
  if(typeof EyeDropper !== 'function'){ toast(tt('armory.eyedrop_none'), 6000); return; }
  try{ const r = await new EyeDropper().open(); if(r && r.sRGBHex) then(r.sRGBHex); }
  catch(e){ /* Esc: nothing picked */ }
}
function armDye(o){ return o.dye = o.dye || {color: [150, 24, 24], blend: 'keepshade', strength: 1, keepWhite: true}; }
// while the colours are being chosen the selection's tint stays off the
// model, so the colour seen is the colour baked; the next pick brings it back
function armDyeChanged(o){ ARM.dyeQuiet = true; ARM_DYE.forEach((v, k) => { if(k.startsWith(o.id + ':')) v.stale = true; }); armFrame(); }
function armDyeSet(id, key, v, live){
  const o = armObj(id); if(!o) return;
  const d = armDye(o);
  d[key] = key === 'color' ? armHexRgb(v) : v;
  if(key === 'color' && !d.strength) d.strength = 1;
  armDyeChanged(o);
  if(live){ clearTimeout(ARM.dyeTimer); ARM.dyeTimer = setTimeout(() => { armSave(); }, 300); return; }
  armSave(); armPaintObjects();
}
function armDyePreset(id, v){
  if(!v) return;
  const o = armObj(id); if(!o) return;
  const pr = v.startsWith('g:') ? ARM_PRESETS.find(x => x.id === v.slice(2)) : (ARM.userPresets || [])[+v.slice(2)];
  if(!pr) return;
  const d = armDye(o);
  Object.assign(d, {color: pr.color.slice(), blend: pr.blend || 'keepshade', metal: !!pr.metal,
                    desat: pr.desat || 0, strength: pr.strength == null ? 1 : pr.strength});
  if(pr.channels) d.channels = JSON.parse(JSON.stringify(pr.channels));
  armDyeChanged(o); armSave(); armPaintObjects();
}
function armDyeChannel(id, ch, key, v){
  const o = armObj(id); if(!o) return;
  const d = armDye(o);
  d.channels = d.channels || {};
  const c = d.channels[ch] = d.channels[ch] || {on: false, color: d.color.slice()};
  c[key] = key === 'color' ? armHexRgb(v) : v;
  if(key === 'color') c.on = true;
  armDyeChanged(o); armSave(); armPaintObjects();
}
function armDyeLayer(id, i, v){
  const o = armObj(id); if(!o || !o.dye || !o.dye.pattern) return;
  const cols = o.dye.pattern.colors = o.dye.pattern.colors || {};
  if(v) cols[i] = armHexRgb(v); else delete cols[i];
  armDyeChanged(o); armSave(); armPaintObjects();
}
function armDyeClear(id){ const o = armObj(id); if(!o) return; o.dye = null; armDyeChanged(o); armRepaint(); }
async function armSavePreset(id){
  const o = armObj(id); if(!o || !o.dye) return;
  const name = prompt(tt('armory.preset_name'));
  if(!name) return;
  const d = o.dye;
  ARM.userPresets = ARM.userPresets || [];
  ARM.userPresets.push({name: name.trim(), color: d.color, blend: d.blend, strength: d.strength,
                        metal: !!d.metal, desat: d.desat || 0, channels: d.channels || null});
  await api.post('/api/armory/presets', {presets: ARM.userPresets}).catch(() => {});
  armPaintObjects();
}
async function armLoadPresets(){
  if(ARM.userPresets) return;
  try{ ARM.userPresets = (await api.get('/api/armory/presets', 1)).presets || []; }catch(e){ ARM.userPresets = []; }
}

/* The arithmetic, one pixel at a time. armory.py's dye_pixels is the same
   code in Python for the bake (95i), so a preview is what gets baked. */
function armBlend(mode, b, c){
  switch(mode){
    case 'multiply': return b * c;
    case 'screen': return 1 - (1 - b) * (1 - c);
    case 'overlay': return b < 0.5 ? 2 * b * c : 1 - 2 * (1 - b) * (1 - c);
    case 'hardlight': return c < 0.5 ? 2 * b * c : 1 - 2 * (1 - b) * (1 - c);
    case 'softlight': return (1 - 2 * c) * b * b + 2 * c * b;
    default: return c;
  }
}
/* Which part of a material a pixel is: metal (no colour to speak of), white,
   leather (warm, darker, a little saturated), trim (gold and brass), cloth. */
function armChannel(r, g, b){
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), chroma = mx - mn;
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  if(lum > 0.90 && chroma < 0.10) return 'white';
  if(chroma < 0.09) return 'metal';
  let h = 0;
  if(mx === r) h = ((g - b) / chroma) % 6; else if(mx === g) h = (b - r) / chroma + 2; else h = (r - g) / chroma + 4;
  h = (h * 60 + 360) % 360;
  const sat = chroma / mx;
  if(h >= 38 && h <= 62 && sat > 0.45 && lum > 0.42) return 'trim';
  if(h >= 10 && h <= 45 && sat > 0.25 && lum < 0.55) return 'leather';
  return 'cloth';
}
function armDyePixels(data, d, material, centers){
  const main = (d.color || [128, 128, 128]).map(v => v / 255);
  const strength = d.strength == null ? 1 : d.strength;
  const blend = d.blend || 'keepshade';
  const mainOn = material === 'fabric' ? {cloth: 1} : material === 'leather' ? {leather: 1}
               : {cloth: 1, leather: 1, trim: 1};
  const chans = d.channels || {};
  const layerCols = centers ? (d.pattern.colors || {}) : {};
  for(let i = 0; i < data.length; i += 4){
    let r = data[i] / 255, g = data[i+1] / 255, b = data[i+2] / 255;
    const ch = armChannel(r, g, b);
    let target = null, mode = blend, s = strength;
    if(centers){
      let best = 0, bd = 1e9;
      for(let k = 0; k < centers.length; k++){
        const c = centers[k];
        const dd = (data[i] - c[0]) ** 2 + (data[i+1] - c[1]) ** 2 + (data[i+2] - c[2]) ** 2;
        if(dd < bd){ bd = dd; best = k; }
      }
      // a layer given a colour of its own is recoloured whole, whatever
      // the object's dye is doing
      if(layerCols[best]){ target = layerCols[best].map(v => v / 255); mode = 'keepshade'; s = 1; }
    }
    if(!target){
      if(ch === 'white' && d.keepWhite !== false) continue;
      // grey is mail and plate: a metal preset, the metal channel, or an
      // object marked metal reaches it, and nothing else does
      if(ch === 'metal' && chans.metal && chans.metal.on) target = chans.metal.color.map(v => v / 255);
      else if(ch === 'metal' || ch === 'white'){ if(!d.metal && !(ch === 'metal' && material === 'metal')) continue; target = main; }
      else if(chans[ch] && chans[ch].on) target = chans[ch].color.map(v => v / 255);
      else if(mainOn[ch]) target = main;
      else continue;
    }
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    if(d.desat){ r += (lum - r) * d.desat; g += (lum - g) * d.desat; b += (lum - b) * d.desat; }
    let o;
    if(mode === 'keepshade'){
      // the target's colour at the pixel's own lightness: creases and
      // shadows stay where the art put them
      const tl = Math.max(0.04, 0.299 * target[0] + 0.587 * target[1] + 0.114 * target[2]);
      const k = lum / tl;
      o = [target[0] * k, target[1] * k, target[2] * k];
    }else o = [armBlend(mode, r, target[0]), armBlend(mode, g, target[1]), armBlend(mode, b, target[2])];
    if(!s) continue;
    data[i] = Math.max(0, Math.min(255, Math.round((data[i] / 255 + (o[0] - data[i] / 255) * s) * 255)));
    data[i+1] = Math.max(0, Math.min(255, Math.round((data[i+1] / 255 + (o[1] - data[i+1] / 255) * s) * 255)));
    data[i+2] = Math.max(0, Math.min(255, Math.round((data[i+2] / 255 + (o[2] - data[i+2] / 255) * s) * 255)));
  }
}

/* --- a dyed object's own crop of the sheet ------------------------------------- */

const ARM_DYE = new Map();     // "<object>:<piece>" -> {sig, tex, crop, stale}
// an image's own number, so a sheet read again (edited on disk) dyes again
const ARM_IMG_ID = new WeakMap();
let armImgSeq = 0;
function armImgId(img){ if(!ARM_IMG_ID.has(img)) ARM_IMG_ID.set(img, ++armImgSeq); return ARM_IMG_ID.get(img); }

// a vertex's UV as the object draws it: moved in the UV editor (100m) or the
// asset's own; ``us`` 1 on a sheet of the object's own or an object's texture
function armPieceU(live, pc, v){
  const m = pc.uv && pc.uv[v];
  return m ? m : [live.geo.uvs[v*2], live.geo.uvs[v*2+1]];
}
function armPieceUs(live, o){ return o && o.sheet || live.objTex ? 1 : (live.uScale || 0.5); }
function armPieceUvBox(live, pc, us){
  const U = live.geo.uvs;
  if(!U) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  armPieceEach(live, pc, v => {
    const uv = armPieceU(live, pc, v), x = uv[0] * us, y = uv[1];
    if(x < x0) x0 = x; if(x > x1) x1 = x; if(y < y0) y0 = y; if(y > y1) y1 = y;
  });
  return x0 === Infinity ? null : [x0, y0, x1, y1, us];
}

/* A piece's UV triangles drawn into a crop of its sheet, grown by two
   texels: RGBA, the alpha set where the piece is. */
function armPieceMask(live, pc, crop, W, H, w, h, us){
  if(!live.geo.uvs) return null;
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d', {willReadFrequently: true});
  x.fillStyle = x.strokeStyle = '#fff'; x.lineWidth = 4; x.lineJoin = 'round';
  const g = live.geo.groups[pc.group], I = live.geo.indices;
  const tris = pc.tris || [...Array(g.count / 3).keys()];
  for(const t of tris){
    x.beginPath();
    for(let k = 0; k < 3; k++){
      const uv = armPieceU(live, pc, I[g.start + t*3 + k]);
      const px = (uv[0] * us - crop[0]) * W, py = (uv[1] - crop[1]) * H;
      if(k) x.lineTo(px, py); else x.moveTo(px, py);
    }
    x.closePath(); x.fill(); x.stroke();
  }
  return x.getImageData(0, 0, w, h).data;
}

function armDyedTexture(o, pc){
  const stamps = o.stamps || [];
  // 95j: the normal map's preview is made from the same crop
  const ns = typeof armNormalPreviewOn === 'function' && armNormalPreviewOn() ? armNormalSetting(o) : null;
  if(!o.dye && !stamps.length && !ns) return null;
  const pi = (o.src || []).indexOf(pc);
  const key = `${o.id}:${pi}`;
  const live = ARM.assets.get(pc.asset);
  if(!live) return null;
  // a sheet worn from the Textures tab or the UV editor (100l, 100m) is the
  // art the object shows, so it is the art that is dyed
  let img;
  if(o.sheet){ const h = ARM.sheetCache.get(o.sheet); img = h && h.img; if(!h) armSheetTex(o.sheet); }
  else img = live.objImg ? live.objImg[pc.group] : live.img;
  if(!img) return null;
  const us = armPieceUs(live, o);
  const sig = JSON.stringify([o.dye, o.material, pc.asset, pc.group, pc.tris ? pc.tris.length : -1, us, o.sheet || '',
                             armImgId(img), pc.uv || null, stamps, stamps.map(st => armStampImage(st.path) ? 1 : 0), ns]);
  let hit = ARM_DYE.get(key);
  if(hit && hit.sig === sig && !hit.stale) return hit;
  const W = img.width, H = img.height;
  const box = armPieceUvBox(live, pc, us);
  let crop = [0, 0, 1, 1], px = [0, 0, W, H], cropped = false;
  if(box){
    // an edge vertex a texel past a boundary (mesh.TILE_EPS) does not make
    // a part wrap
    const e = 0.03;
    const fx = Math.floor(box[0] + e), fy = Math.floor(box[1] + e);
    // a crop only when the part's art sits inside one copy of the sheet;
    // a part that wraps round its edge keeps the whole sheet
    if(box[2] - fx <= 1 + e && box[3] - fy <= 1 + e){
      const ax = Math.max(0, Math.floor((box[0] - fx) * W) - 2), ay = Math.max(0, Math.floor((box[1] - fy) * H) - 2);
      const bx = Math.min(W, Math.ceil((box[2] - fx) * W) + 2), by = Math.min(H, Math.ceil((box[3] - fy) * H) + 2);
      px = [ax, ay, Math.max(1, bx - ax), Math.max(1, by - ay)];
      crop = [fx + ax / W, fy + ay / H, px[2] / W, px[3] / H];
      cropped = true;
    }
  }
  const c = document.createElement('canvas');
  c.width = px[2]; c.height = px[3];
  const ctx = c.getContext('2d', {willReadFrequently: true});
  ctx.drawImage(img, px[0], px[1], px[2], px[3], 0, 0, px[2], px[3]);
  const im = ctx.getImageData(0, 0, px[2], px[3]);
  // 99l: as the bake, only the texels under the piece's UV triangles (and
  // the two beside them that filtering reads) are dyed and stamped
  const keep = cropped ? armPieceMask(live, pc, crop, W, H, px[2], px[3], us) : null;
  const was = keep ? im.data.slice() : null;
  if(o.dye){
    const centers = o.dye.pattern && Object.keys(o.dye.pattern.colors || {}).length ? o.dye.pattern.centers : null;
    armDyePixels(im.data, o.dye, o.material, centers);
  }
  if(box && stamps.length){
    // the part's art in this crop's pixels, which is where armbake.py
    // places a stamp too: a share of the box, its centre and its width
    const ab = [(box[0] - crop[0]) * W, (box[1] - crop[1]) * H, (box[2] - crop[0]) * W, (box[3] - crop[1]) * H];
    for(const st of stamps){
      const simg = armStampImage(st.path);
      if(simg) armStampPixels(im.data, px[2], px[3], st, simg, ab);
    }
  }
  if(keep) for(let i = 0, n = px[2] * px[3]; i < n; i++) if(!keep[i * 4 + 3]){
    im.data[i*4] = was[i*4]; im.data[i*4+1] = was[i*4+1]; im.data[i*4+2] = was[i*4+2];
  }
  ctx.putImageData(im, 0, 0);
  let nTex = null;
  if(ns){
    const nc = document.createElement('canvas'); nc.width = px[2]; nc.height = px[3];
    nc.getContext('2d').putImageData(new ImageData(armNormalPixels(im.data, px[2], px[3], ns), px[2], px[3]), 0, 0);
    nTex = armTexture(nc, 1);
  }
  if(hit && hit.tex && ARM.gl) ARM.gl.deleteTexture(hit.tex);
  if(hit && hit.nTex && ARM.gl) ARM.gl.deleteTexture(hit.nTex);
  hit = {sig, tex: armTexture(c, 1), nTex, crop, stale: false, canvas: c};
  ARM_DYE.set(key, hit);
  return hit;
}

/* --- coat of arms and emblems (95i) ---------------------------------------------

   An image stamped onto an object's art: its centre and width a share of the
   part's own box on its sheet, turned, blended as the dye's modes or laid on
   as it is, and baked in by armbake.py's stamp_pixels the same way. */

const ARM_STAMP_BLENDS = ['normal'].concat(ARM_BLENDS);
const ARM_STAMP_IMG = new Map();   // path -> Image, or 'loading', or null
function armStampImage(path){
  const hit = ARM_STAMP_IMG.get(path);
  if(hit instanceof Image) return hit;
  if(hit === undefined && path){
    ARM_STAMP_IMG.set(path, 'loading');
    // the server serves only an image it was given, and forgets on a restart
    armAllow(path)
      .then(() => armImage('/api/armory/texture?hd=1&path=' + enc(path)))
      .then(img => { ARM_STAMP_IMG.set(path, img); armFrame(); })
      .catch(() => ARM_STAMP_IMG.set(path, null));
  }
  return null;
}
function armStampsHtml(o){
  const blendLabel = b => b === 'normal' ? tt('armory.blend_normal') : armBlendLabel(b);
  const rows = (o.stamps || []).map((st, i) => {
    const sl = (key, label, min, max, k) => `<label class="armrange">${label}<input type="range" min="${min}" max="${max}"
        value="${Math.round((st[key] == null ? 0 : st[key]) * k)}" oninput="armStampSet(${o.id},${i},'${key}',this.value/${k},true)"></label>`;
    return `<div class="armstamp">
      <div class="armpropsrow"><span class="armname" title="${esc(st.path)}">${esc(st.path.split(/[\\/]/).pop())}</span>
        <button class="mini armx" onclick="armStampDel(${o.id},${i})" title="${esc(tt('armory.stamp_remove'))}">✕</button></div>
      <div class="armpropsrow">${sl('x', tt('armory.stamp_x'), 0, 100, 100)}${sl('y', tt('armory.stamp_y'), 0, 100, 100)}</div>
      <div class="armpropsrow">${sl('size', tt('armory.stamp_size'), 2, 150, 100)}${sl('rot', tt('armory.stamp_rot'), -180, 180, 1)}</div>
      <div class="armpropsrow">${sl('opacity', tt('armory.stamp_opacity'), 0, 100, 100)}
        <select onchange="armStampSet(${o.id},${i},'blend',this.value)">${ARM_STAMP_BLENDS.map(b =>
          `<option value="${b}"${(st.blend || 'normal') === b ? ' selected' : ''}>${esc(blendLabel(b))}</option>`).join('')}</select></div>
    </div>`;
  }).join('');
  return rows + `<div class="armpropsrow"><button class="mini" onclick="armStampAdd(${o.id})" title="${esc(tt('armory.stamp_add_title'))}">${tt('armory.stamp_add')}</button></div>`;
}
async function armStampAdd(id){
  const o = armObj(id); if(!o) return;
  let r;
  try{ r = await api.post('/api/browse_file', {title: tt('armory.stamp_pick_title'),
    filter: 'Images|*.png;*.tga;*.dds;*.jpg;*.jpeg;*.texture;*.bmp'}); }
  catch(e){ toast(errText(e)); return; }
  if(!r || !r.path) return;
  const ok = await api.post('/api/armory/allow_texture', {path: r.path}).catch(() => ({}));
  if(!ok.ok){ toast(tt('armory.not_an_image')); return; }
  ARM_STAMP_IMG.delete(r.path);
  (o.stamps = o.stamps || []).push({path: r.path, x: 0.5, y: 0.5, size: 0.3, rot: 0, blend: 'normal', opacity: 1});
  armDyeChanged(o); armSave(); armPaintObjects();
}
function armStampSet(id, i, key, v, live){
  const o = armObj(id); if(!o || !o.stamps || !o.stamps[i]) return;
  o.stamps[i][key] = key === 'blend' ? v : +v;
  armDyeChanged(o);
  if(live){ clearTimeout(ARM.dyeTimer); ARM.dyeTimer = setTimeout(() => { armSave(); }, 300); return; }
  armSave(); armPaintObjects();
}
function armStampDel(id, i){
  const o = armObj(id); if(!o || !o.stamps) return;
  o.stamps.splice(i, 1);
  if(!o.stamps.length) delete o.stamps;
  armDyeChanged(o); armSave(); armPaintObjects();
}
/* One stamp onto RGBA pixels (w x h); box is the part's art in them. */
function armStampPixels(data, w, h, st, img, box){
  const bw = Math.max(1, box[2] - box[0]), bh = Math.max(1, box[3] - box[1]);
  const sw = Math.max(1, Math.round(bw * (st.size == null ? 0.3 : st.size)));
  const sh = Math.max(1, Math.round(sw * img.height / Math.max(1, img.width)));
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d', {willReadFrequently: true});
  x.translate(box[0] + bw * (st.x == null ? 0.5 : st.x), box[1] + bh * (st.y == null ? 0.5 : st.y));
  x.rotate((st.rot || 0) * Math.PI / 180);
  x.drawImage(img, -sw / 2, -sh / 2, sw, sh);
  const L = x.getImageData(0, 0, w, h).data;
  const op = st.opacity == null ? 1 : st.opacity, mode = st.blend || 'normal';
  for(let i = 0; i < L.length; i += 4){
    const a = L[i+3] / 255 * op;
    if(!a) continue;
    const b = [data[i] / 255, data[i+1] / 255, data[i+2] / 255], s = [L[i] / 255, L[i+1] / 255, L[i+2] / 255];
    let o;
    if(mode === 'keepshade'){
      const lum = 0.299 * b[0] + 0.587 * b[1] + 0.114 * b[2];
      const tl = Math.max(0.04, 0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2]);
      o = s.map(v => v * lum / tl);
    }else if(mode === 'normal') o = s;
    else o = b.map((v, j) => armBlend(mode, v, s[j]));
    for(let j = 0; j < 3; j++) data[i+j] = Math.max(0, Math.min(255, Math.floor((b[j] + (o[j] - b[j]) * a) * 255 + 0.5)));
  }
}

/* --- the pattern detector ------------------------------------------------------ */

/* The part's own pixels (its UV triangles, filled), clustered by colour into
   up to five layers, each with its swatch and its share of the part. */
function armDetectPattern(id){
  const o = armObj(id); if(!o) return;
  const samples = [];
  for(const pc of o.src || []){
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo.uvs) continue;
    const sh = o.sheet && ARM.sheetCache.get(o.sheet);
    const img = o.sheet ? sh && sh.img : live.objImg ? live.objImg[pc.group] : live.img;
    if(!img) continue;
    const W = Math.min(img.width, 1024), H = Math.round(img.height * W / img.width);
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const ctx = c.getContext('2d', {willReadFrequently: true});
    ctx.drawImage(img, 0, 0, W, H);
    const art = ctx.getImageData(0, 0, W, H).data;
    const m = document.createElement('canvas'); m.width = W; m.height = H;
    const mx = m.getContext('2d', {willReadFrequently: true});
    mx.fillStyle = '#fff';
    const us = armPieceUs(live, o);
    const g = live.geo.groups[pc.group], I = live.geo.indices;
    const tris = pc.tris || [...Array(g.count / 3).keys()];
    for(const t of tris){
      mx.beginPath();
      for(let k = 0; k < 3; k++){
        const uv = armPieceU(live, pc, I[g.start + t*3 + k]);
        let x = uv[0] * us, y = uv[1];
        x = (x - Math.floor(x)) * W; y = (y - Math.floor(y)) * H;
        if(k) mx.lineTo(x, y); else mx.moveTo(x, y);
      }
      mx.closePath(); mx.fill();
    }
    const mask = mx.getImageData(0, 0, W, H).data;
    const step = Math.max(1, Math.floor(W * H / 40000));
    for(let i = 0; i < W * H; i += step)
      if(mask[i*4+3] > 128 && art[i*4+3] > 90) samples.push([art[i*4], art[i*4+1], art[i*4+2]]);
  }
  if(samples.length < 10){ toast(tt('armory.no_pixels')); return; }
  const k = Math.min(5, samples.length);
  // seeds spread through the samples by lightness
  const byLum = samples.slice().sort((a, b) => (a[0] + a[1] + a[2]) - (b[0] + b[1] + b[2]));
  let centers = [...Array(k).keys()].map(i => byLum[Math.floor((i + 0.5) * byLum.length / k)].slice());
  let counts = [];
  for(let it = 0; it < 10; it++){
    const sums = centers.map(() => [0, 0, 0]);
    counts = centers.map(() => 0);
    for(const s of samples){
      let best = 0, bd = 1e9;
      centers.forEach((c, j) => { const d = (s[0]-c[0])**2 + (s[1]-c[1])**2 + (s[2]-c[2])**2; if(d < bd){ bd = d; best = j; } });
      sums[best][0] += s[0]; sums[best][1] += s[1]; sums[best][2] += s[2]; counts[best]++;
    }
    centers = centers.map((c, j) => counts[j] ? sums[j].map(v => v / counts[j]) : c);
  }
  const order = centers.map((_, j) => j).filter(j => counts[j]).sort((a, b) => counts[b] - counts[a]);
  // an object with no dye yet gets one that does nothing until a layer, or
  // the object as a whole, is given a colour
  const fresh = !o.dye;
  const d = armDye(o);
  if(fresh) d.strength = 0;
  d.pattern = {centers: order.map(j => centers[j].map(v => Math.round(v))),
               shares: order.map(j => counts[j] / samples.length), colors: {}};
  armDyeChanged(o); armSave(); armPaintObjects();
}

/* --- picking ----------------------------------------------------------------- */

/* Every visible triangle on screen: [object, piece, triangle number, three
   screen points with depth]. Rebuilt per pick, in canvas pixels. */
function armScreenTris(only){
  const view = ARM.view;
  if(!view) return [];
  const w = view.width, h = view.height;
  const cam = armCamera(w / h);
  const vp = armMul(cam.proj, cam.view);
  const out = [];
  const objs = only ? [only] : armVisibleObjects();
  for(const o of objs){
    const om = armMul(ARM_MIRROR, armObjMatrix(o, armPivot(o)));
    (o.src || []).forEach((pc, pi) => {
      const live = ARM.assets.get(pc.asset);
      if(!live || !live.geo) return;
      const m = armMul(vp, pc.xf ? armMul(om, pc.xf) : om);
      const P = live.geo.positions, g = live.geo.groups[pc.group], I = live.geo.indices;
      if(!g) return;
      const proj = v => {
        const x = P[v*3], y = P[v*3+1], z = P[v*3+2];
        const cw = m[3]*x + m[7]*y + m[11]*z + m[15];
        if(cw <= 1e-6) return null;
        return [((m[0]*x + m[4]*y + m[8]*z + m[12]) / cw * 0.5 + 0.5) * w,
                (1 - ((m[1]*x + m[5]*y + m[9]*z + m[13]) / cw * 0.5 + 0.5)) * h,
                (m[2]*x + m[6]*y + m[10]*z + m[14]) / cw, v];
      };
      const tris = pc.tris || null;
      const n = tris ? tris.length : g.count / 3;
      for(let j = 0; j < n; j++){
        const t = tris ? tris[j] : j;
        const a = proj(I[g.start + t*3]), b = proj(I[g.start + t*3 + 1]), c = proj(I[g.start + t*3 + 2]);
        if(a && b && c) out.push([o, pi, t, a, b, c]);
      }
    });
  }
  return out;
}
function armPickAt(x, y, only){
  let best = null, bz = Infinity;
  for(const tr of armScreenTris(only)){
    const [, , , a, b, c] = tr;
    const d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]);
    if(Math.abs(d) < 1e-9) continue;
    const l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d;
    const l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d;
    const l3 = 1 - l1 - l2;
    if(l1 < 0 || l2 < 0 || l3 < 0) continue;
    const z = l1 * a[2] + l2 * b[2] + l3 * c[2];
    if(z < bz){ bz = z; best = tr; }
  }
  return best;
}
function armCanvasXY(e){
  const r = ARM.view.getBoundingClientRect();
  return [(e.clientX - r.left) * ARM.view.width / r.width, (e.clientY - r.top) * ARM.view.height / r.height];
}

/* The object under the cursor lights up (95g); in the detail view, nothing does. */
function armHoverAt(e){
  if(ARM.detail && !e){ armEditHover(null); return; }
  if(!e){ if(ARM.hover != null){ ARM.hover = null; armFrame(); } return; }
  if(ARM.hoverAsked) { ARM.hoverEv = e; return; }
  ARM.hoverAsked = true; ARM.hoverEv = e;
  requestAnimationFrame(() => {
    ARM.hoverAsked = false;
    const [x, y] = armCanvasXY(ARM.hoverEv);
    // in the detail view, the vertex, edge or face under the pointer (armedit.js)
    if(ARM.detail){ armEditHover(x, y); return; }
    const hit = armPickAt(x, y);
    const id = hit ? hit[0].id : null;
    if(id !== ARM.hover){ ARM.hover = id; armFrame(); }
  });
}
function armClick(e){
  const [x, y] = armCanvasXY(e);
  if(ARM.detail) return armEditClick(x, y, e);
  const hit = armPickAt(x, y);
  armSelect(hit ? hit[0].id : null, e);
}

/* --- the detail view: armedit.js (Blender's Edit Mode) ---------------------------- */

function armBoxDrag(drag, e){
  if(drag.button !== 0) return false;
  if(!drag.moved) return true;
  drag.box = true;
  const a = armCanvasXY({clientX: drag.x0, clientY: drag.y0}), b = armCanvasXY(e);
  ARM.box = [a[0], a[1], b[0], b[1]];
  armFrame();
  return true;
}
function armBoxEnd(drag, e){
  const d = ARM.detail, o = d && armObj(d.id);
  const bx = ARM.box; ARM.box = null;
  if(!bx){ armFrame(); return; }
  const [x0, x1] = [Math.min(bx[0], bx[2]), Math.max(bx[0], bx[2])];
  const [y0, y1] = [Math.min(bx[1], bx[3]), Math.max(bx[1], bx[3])];
  if(!d){
    // Blender's box: every object with a corner inside it; Shift adds
    if(!e.shiftKey) ARM.sel.clear();
    for(const tr of armScreenTris())
      if([tr[3], tr[4], tr[5]].some(p => p[0] >= x0 && p[0] <= x1 && p[1] >= y0 && p[1] <= y1)) ARM.sel.add(tr[0].id);
    armPaintObjects(); armPaintFoot(); armFrame();
    return;
  }
  if(!o){ armFrame(); return; }
  armEditBox(x0, y0, x1, y1, e.shiftKey);
}

/* A part keeps its place when its pivot moves: the move is corrected by what
   the turn and scale do about the old pivot against the new one. */
function armFixPivot(o, oldPivot){
  ARM_PIVOT.delete(o);
  const np = armPivot(o);
  const before = armObjMatrix(o, oldPivot), after = armObjMatrix(o, np);
  for(let k = 0; k < 3; k++) o.t[k] += before[12 + k] - after[12 + k];
}

/* --- the overlay ---------------------------------------------------------------- */

function armOverlay(ctx, w, h, cam){
  if(ARM.box){
    ctx.save(); ctx.strokeStyle = '#fff'; ctx.setLineDash([5, 4]);
    ctx.strokeRect(ARM.box[0], ARM.box[1], ARM.box[2] - ARM.box[0], ARM.box[3] - ARM.box[1]);
    ctx.restore();
  }
  if(typeof armOverlay95g === 'function') armOverlay95g(ctx, w, h, cam);
}

/* --- what the weapon prefixes mean (the ? beside the group picker) ------------

   Checked 2026-11-23 against every vanilla model (701 entries, LOD0): vanilla
   uses primaryactive, secondaryactive, shield0, equipment0 (quivers),
   equipment20 (powder), ramrod0, cannon ball0 and ballista arrow0, and the
   shieldactive0/shieldpassive0 pair on a few horse archers; no vanilla model
   has primarypassive or secondarypassive. */
function armPrefixFig(parts, caption, note){
  // the parts drawn in their colours on a figure; their names listed under it,
  // so a long prefix never runs off the picture
  const at = {
    hand: c => `<line x1="84" y1="70" x2="98" y2="16" stroke="${c}" stroke-width="4" stroke-linecap="round"/>`,
    bow: c => `<path d="M86 30 Q104 70 86 110" fill="none" stroke="${c}" stroke-width="3"/><line x1="86" y1="30" x2="86" y2="110" stroke="${c}" stroke-width="1"/>`,
    arm: c => `<ellipse cx="36" cy="70" rx="11" ry="16" fill="${c}" opacity=".9"/>`,
    back: c => `<line x1="44" y1="30" x2="78" y2="86" stroke="${c}" stroke-width="5" stroke-dasharray="5 3" opacity=".75"/>`,
    backshield: c => `<ellipse cx="66" cy="56" rx="13" ry="17" fill="none" stroke="${c}" stroke-width="3" stroke-dasharray="4 3"/>`,
    side: c => `<line x1="66" y1="82" x2="80" y2="112" stroke="${c}" stroke-width="4" stroke-linecap="round"/>`,
  };
  const body = `<circle cx="60" cy="22" r="9" fill="none" stroke="#9aa3ad" stroke-width="2"/>
    <line x1="60" y1="31" x2="60" y2="82" stroke="#9aa3ad" stroke-width="2"/>
    <line x1="60" y1="42" x2="38" y2="68" stroke="#9aa3ad" stroke-width="2"/><line x1="60" y1="42" x2="84" y2="70" stroke="#9aa3ad" stroke-width="2"/>
    <line x1="60" y1="82" x2="46" y2="124" stroke="#9aa3ad" stroke-width="2"/><line x1="60" y1="82" x2="74" y2="124" stroke="#9aa3ad" stroke-width="2"/>`;
  const names = parts.filter(([, , l]) => l).map(([, c, l]) => `<div><span style="color:${c}">■</span> <code>${esc(l)}</code></div>`).join('');
  return `<figure class="armprefixfig"><svg viewBox="0 0 120 130">${body}${parts.map(([k, c]) => at[k](c)).join('')}</svg>
    ${caption ? `<figcaption><b>${caption}</b>${note ? ` <span class="count">(${note})</span>` : ''}</figcaption>` : ''}<div class="count">${names}</div></figure>`;
}
function armPrefixHelp(){
  const A = '#f0a040', B = '#5aa9f0', C = '#7fd08a', D = '#c98be0';
  const card = (title, figs, text) => `<div class="armprefixcard"><b>${title}</b>
    ${figs.length ? `<div class="armprefixfigs">${figs.join('')}</div>` : ''}<div>${text}</div></div>`;
  document.getElementById('modal').className = 'modal wide';
  modal.innerHTML = `<div class="armimp">
    <h3>${tt('armory.prefix_help_title')}</h3>
    <div class="count">${tt('armory.prefix_help_intro')}</div>
    <div class="armprefixhelp">
      ${card(tt('armory.prefix_help_melee'), [armPrefixFig([['hand', A, 'primaryactive0'], ['arm', C, 'shield0']])],
        tt('armory.prefix_help_melee_text'))}
      ${card(tt('armory.prefix_help_two'), [
          armPrefixFig([['hand', A, 'primaryactive0'], ['arm', C, 'shield0']], tt('armory.prefix_help_first')),
          armPrefixFig([['hand', B, 'secondaryactive0'], ['arm', C, 'shield0']], tt('armory.prefix_help_second'))],
        tt('armory.prefix_help_two_text'))}
      ${card(tt('armory.prefix_help_passive'), [
          armPrefixFig([['bow', A, 'primaryactive0'], ['side', D, 'secondarypassive0'], ['backshield', C, 'shieldpassive0']], tt('armory.prefix_help_ranged')),
          armPrefixFig([['hand', B, 'secondaryactive0'], ['arm', C, 'shieldactive0'], ['back', A, 'primarypassive0']], tt('armory.prefix_help_melee_mode'))],
        tt('armory.prefix_help_passive_text'))}
      ${card(tt('armory.prefix_help_simple'), [
          armPrefixFig([['bow', A, 'primaryactive0'], ['side', A, ''], ['backshield', A, '']], tt('armory.prefix_help_ranged'), tt('armory.prefix_help_one_group')),
          armPrefixFig([['hand', B, 'secondaryactive0'], ['arm', B, ''], ['back', B, '']], tt('armory.prefix_help_melee_mode'), tt('armory.prefix_help_one_group'))],
        tt('armory.prefix_help_simple_text'))}
      ${card(tt('armory.prefix_help_other'), [], tt('armory.prefix_help_other_text'))}
    </div>
    <div class="armimpfoot"><span style="flex:1"></span><button onclick="closeModal()">${tt('common.close')}</button></div>
  </div>`;
  overlay.classList.add('open');
}
