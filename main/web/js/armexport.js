/* =========================================================================
   Armory Studio's export (Phase 95i): check, UV packing and the bake

   Three steps in one dialog, each answered by the server (armbake.py) on the
   project as the page holds it:

     1. CHECK  - the Blender kit's export checks that still apply (names, opt,
                 weights, the ranged objects), with its rename fix; the UV and
                 texture checks are left out, since the sheets are baked new.
                 What goes: everything visible, or the chosen collections.
     2. UVs    - every object's islands measured in its source's texels and
                 the size of sheet it needs; a list setting which sheet each
                 object goes on; the packing drawn, with what did not fit and
                 the ways out (automatic, move, scale, a smaller margin).
     3. BAKE   - the sheets and the .mesh written to a folder.
   ========================================================================= */

const ARM_SIZES = [512, 1024, 2048, 4096];

function armExp(){
  const p = armProj();
  return state.armExp = state.armExp || {step: 'check', scope: {mode: 'visible',
    collections: p.collections.filter(c => c.export).map(c => c.id)},
    settings: {size: {both: 'auto'}, margin: 0.4, obj_sheet: {}, block_sheet: {}, scale: {}, block_scale: {}, dyes: true, rotate: 'quarter'},
    check: null, plan: null, busy: false, err: '', folder: '', stem: '', done: null};
}
function armExpOutput(key, value){
  const e = armExp(); e[key] = value; e.done = null; armSave();
}
async function armExpFindExisting(){
  const e = armExp(), folder = e.folder, stem = e.stem;
  if(!folder) return false;
  try{
    const r = await api.get('/api/armory/export_exists?folder=' + enc(folder) + '&stem=' + enc(stem));
    if(e.folder !== folder || e.stem !== stem) return false;
    e.done = r.found ? r : null;
    e.exportCandidates = r.candidates || [];
    if(r.found){ e.stem = r.stem; armSave(); }
    if(e.step === 'bake') armExportPaint();
    return !!e.done;
  }catch(err){ e.err = errText(err); e.done = null; return false; }
}
function armExpHistory(){ return armExp().history || (armExp().history = {past: [], future: [], start: null}); }
function armExpEditBegin(){
  const h = armExpHistory();
  if(h.start === null) h.start = JSON.stringify(armExp().settings);
}
function armExpEditEnd(){
  const h = armExpHistory(), now = JSON.stringify(armExp().settings);
  if(h.start !== null && h.start !== now){ h.past.push(h.start); if(h.past.length > 200) h.past.shift(); h.future = []; }
  h.start = null; armSave();
}
function armExpUndo(redo){
  if(armExp().numericScale) armExpScaleEnd(true);
  armExpEditEnd();
  const e = armExp(), h = armExpHistory(), from = redo ? h.future : h.past;
  if(!from.length) return;
  (redo ? h.past : h.future).push(JSON.stringify(e.settings));
  e.settings = JSON.parse(from.pop());
  armExpReplan(); armExpDrawSheets(); armExpSyncScale(); armSave();
}
function armExpSyncScale(){
  const e = armExp(), own = (e.settings.block_scale[e.sel] || 1) * 100;
  const sl = document.getElementById('armExpScaleSlider'), num = document.getElementById('armExpScaleNumber');
  if(sl){ sl.max = Math.max(100, own); sl.value = own; }
  if(num && document.activeElement !== num) num.value = Math.round(own * 100) / 100;
}
function armExpBody(){ return {project: armProj(), scope: armExp().scope}; }

async function armExportOpen(){
  const e = armExp();
  e.err = '';
  if(!e.stem){
    const p = armProj();
    const a = p.assets.find(a => (p.objects || []).some(o => (o.src || []).some(pc => pc.asset === armAssetKey(a))));
    const imported = a && (a.kind === 'external' ? (a.path || '').split(/[\\/]/).pop().replace(/\.[^.]+$/, '') : a.entry);
    e.stem = (imported || p.name || (p.objects[0] && p.objects[0].mesh) || 'armory_model').replace(/[^A-Za-z0-9_\-]/g, '_');
  }
  e.step = 'check';
  armExportPaint();
  overlay.classList.add('open');
  armExportCheck();
  armExpFindExisting();
}

function armExportPaint(){
  const e = armExp();
  const focused = document.activeElement && document.activeElement.id;
  document.getElementById('modal').className = 'modal wide';
  const tab = (id, label) => `<button class="mftab${e.step === id ? ' on' : ''}" onclick="armExportStep('${id}')">${label}</button>`;
  const errors = e.check ? e.check.issues.filter(i => i.level === 'error').length : 0;
  modal.innerHTML = `<div class="armexp" onkeydown="if((event.ctrlKey||event.metaKey)&&['z','y'].includes(event.key.toLowerCase()) && !event.target.matches('input,textarea,select'))armExpKey(event)">
    <h3>${tt('armory.exp_title')}</h3>
    <div class="mftabs">${tab('check', tt('armory.exp_step_check'))}${tab('uv', tt('armory.exp_step_uv'))}${tab('bake', tt('armory.exp_step_bake'))}${tab('mod', tt('armory.exp_step_mod'))}</div>
    <div id="armExpBody">${e.step === 'check' ? armExpCheckHtml() : e.step === 'uv' ? armExpUvHtml() : e.step === 'mod' ? armExpModHtml() : armExpBakeHtml()}</div>
    ${e.err ? `<div class="armexperr">${esc(e.err)}</div>` : ''}
    <div class="armimpfoot"><span class="count">${e.busy ? tt('armory.reading') : ''}</span><span style="flex:1"></span>
      <button onclick="armExpScaleEnd(true);closeModal()">${tt('common.close')}</button>
      ${e.step === 'check' ? `<button class="primary" onclick="armExportStep('uv')"${errors || !e.check ? ' disabled' : ''}>${tt('armory.exp_next')}</button>` : ''}
      ${e.step === 'uv' ? `<button class="primary" onclick="armExportStep('bake')"${e.plan && e.plan.fits ? '' : ' disabled'}>${tt('armory.exp_next')}</button>` : ''}
      ${e.step === 'bake' && e.done ? `<button class="primary" onclick="armExportStep('mod')">${tt('armory.exp_next')}</button>` : ''}
    </div></div>`;
  if(e.step === 'uv'){ armExpDrawSheets(); if(focused && focused.startsWith('armExpCv_')){ const cv=document.getElementById(focused); if(cv) cv.focus({preventScroll:true}); } }
}

async function armExportStep(s){
  const e = armExp();
  if(e.numericScale) armExpScaleEnd(true);
  if(s === 'mod'){
    await armExpFindExisting();
    if(e.done){ e.step = 'mod'; e.err = ''; armExportPaint(); armExpModLoad(); return; }
  }
  if(s !== 'check' && (!e.check || e.check.issues.some(i => i.level === 'error'))){ e.step = 'check'; armExportPaint(); return; }
  if(s === 'bake' && !e.done && !(e.plan && e.plan.fits)) s = 'uv';
  if(s === 'mod' && !e.done) s = 'bake';
  e.step = s; e.err = '';
  armExportPaint();
  if(s === 'check') armExportCheck();
  if(s === 'uv') armExportPlan();
  if(s === 'mod') armExpModLoad();
}

/* --- 1. check ------------------------------------------------------------ */

async function armExportCheck(){
  const e = armExp();
  e.busy = true; armExportPaint();
  try{
    e.check = await api.post('/api/armory/check', Object.assign(armExpBody(),
      {skeleton: typeof armAnim === 'function' ? armAnim().skel || '' : ''}));
    e.err = '';
  }catch(err){ e.err = errText(err); e.check = null; }
  e.busy = false;
  if(e.step === 'check') armExportPaint();
}

function armExpCheckHtml(){
  const e = armExp(), p = armProj();
  const colls = p.collections.map(c => `<label class="armcheck"><input type="checkbox"${e.scope.collections.includes(c.id) ? ' checked' : ''}
      onchange="armExpColl(${c.id}, this.checked)"> ${esc(c.name)}</label>`).join('');
  const scope = `<div class="armexprow">
    <label class="armcheck"><input type="radio" name="armExpScope"${e.scope.mode !== 'collections' ? ' checked' : ''} onchange="armExpScope('visible')"> ${tt('armory.exp_scope_visible')}</label>
    <label class="armcheck"><input type="radio" name="armExpScope"${e.scope.mode === 'collections' ? ' checked' : ''}${p.collections.length ? '' : ' disabled'} onchange="armExpScope('collections')"> ${tt('armory.exp_scope_collections')}</label>
    ${e.scope.mode === 'collections' ? `<span class="armexpcolls">${colls}</span>` : ''}</div>`;
  if(!e.check) return scope + `<div class="count">${e.busy ? tt('armory.reading') : ''}</div>`;
  const c = e.check;
  const rows = c.issues.map(i => `<div class="armissue ${i.level}"><b>${i.level === 'error' ? tt('armory.exp_error') : tt('armory.exp_warning')}</b>
      ${esc(armChkText(i))}
      ${i.id != null ? `<button class="mini" onclick="armExpShow(${i.id})">${tt('armory.exp_show')}</button>` : ''}</div>`).join('');
  return scope + `<div class="count armnote">${tt('armory.exp_check_summary', {objects: c.objects.length, vertices: (c.vertices || 0).toLocaleString()})}
      ${c.ranged ? `<span>${tt('armory.exp_ranged')}</span>` : ''}</div>
    ${rows || `<div class="armissue ok">${tt('armory.exp_all_clear')}</div>`}
    <div class="armexprow">${c.fixable ? `<button onclick="armExpFixNames()">${tt('armory.exp_fix_names')}</button>` : ''}
      <button class="mini" onclick="armExportCheck()">${tt('armory.exp_recheck')}</button>
      <span class="count">${tt('armory.exp_check_note')}</span></div>`;
}
/* An issue in words, by its code (armbake.check_model). */
function armChkText(i){
  const p = i.params || {};
  switch(i.code){
    case 'empty_name': return tt('armory.chk_empty_name', p);
    case 'name_clash': return tt('armory.chk_name_clash', p);
    case 'name_form': return tt('armory.chk_name_form', p);
    case 'no_texture': return tt('armory.chk_no_texture', p);
    case 'no_weights': return tt('armory.chk_no_weights', p);
    case 'nothing': return tt('armory.chk_nothing', p);
    case 'opt_in_name': return tt('armory.chk_opt_in_name', p);
    case 'ranged_no_primary': return tt('armory.chk_ranged_no_primary', p);
    case 'ranged_no_secondary': return tt('armory.chk_ranged_no_secondary', p);
    case 'too_many_vertices': return tt('armory.chk_too_many_vertices', p);
    case 'unreadable': return tt('armory.chk_unreadable', p);
    default: return i.code;
  }
}
function armExpScope(m){ armExp().scope.mode = m; armExp().plan = null; armExportCheck(); }
function armExpColl(id, on){
  const s = armExp().scope;
  s.collections = s.collections.filter(x => x !== id);
  if(on) s.collections.push(id);
  armExp().plan = null;
  armExportCheck();
}
function armExpShow(id){
  closeModal();
  ARM.sel.clear(); ARM.sel.add(id);
  armRepaint();
}
/* The kit's rename fix on every object that goes, and `_opt` at the end of a
   mesh name made into the optional flag it meant. */
function armExpFixNames(){
  const ids = new Set(armExp().check.objects);
  for(const o of armProj().objects){
    if(!ids.has(o.id)) continue;
    if(/_opt$/i.test(o.mesh || '')){ o.mesh = o.mesh.replace(/_{1,2}opt$/i, ''); o.flag = 1; }
    const [n, m] = armSplitName(armFixName(armFullName(o)));
    o.name = n; o.mesh = m;
  }
  armRepaint();
  armExportCheck();
}

/* --- 2. UVs and packing ------------------------------------------------------- */

async function armExportPlan(auto){
  const e = armExp();
  e.busy = true;
  if(!e.plan && e.step === 'uv') armExportPaint();
  const seq = (e.seq || 0) + 1; e.seq = seq;
  try{
    const r = await api.post('/api/armory/uv', Object.assign(armExpBody(), {settings: Object.assign({}, e.settings, {auto: !!auto})}));
    if(seq !== e.seq) return;
    e.plan = r; e.err = '';
    if(e.sel && !armExpSelBlock()){ e.sel = null; e.selSrc = null; }
    e.drag = null;
    if(auto){
      // the way out the server found becomes the settings, to be seen and changed
      e.settings.scale = r.settings.scale; e.settings.block_sheet = r.settings.block_sheet;
    }
  }catch(err){ if(seq === e.seq){ e.err = errText(err); e.plan = null; } }
  e.busy = false;
  if(e.step === 'uv') armExportPaint();
  if(e.plan && e.art) armExpFetchArt();
}
// Live off: a change waits for Refresh, which lights up meanwhile; repainting
// the step would take the box being typed in away, so only the button changes
function armExpReplan(){
  const e = armExp();
  e.seq = (e.seq || 0) + 1;
  if(e.live === false){ e.stale = true; armExpStaleMark(); return; }
  clearTimeout(ARM.expTimer); ARM.expTimer = setTimeout(() => armExportPlan(), 250);
}
function armExpStaleMark(){
  const b = document.getElementById('armExpRefresh');
  if(b) b.classList.toggle('primary', !!armExp().stale);
}
async function armExpRefresh(){
  const e = armExp();
  e.stale = false; clearTimeout(ARM.expTimer);
  await armExportPlan();
}
function armExpLive(on){
  const e = armExp();
  e.live = !!on;
  if(on && e.stale){ e.stale = false; armExpReplan(); }
  armExpStaleMark();
}
/* Textures: each sheet drawn with the art the bake would write there (the
   bake's own render, at the canvas's size), in place of the coloured blocks.
   Blocks stand in while it renders, and for a packing it has not caught up with. */
function armExpArt(on){
  const e = armExp();
  e.art = !!on;
  if(on) armExpFetchArt(); else armExpDrawSheets();
}
async function armExpFetchArt(){
  const e = armExp(), seq = (e.artSeq || 0) + 1;
  e.artSeq = seq; e.artPeek = null;
  armExpDrawSheets();
  // it only reads, so a request lost on the way to the server is sent again
  let r = null;
  for(let i = 0; i < 4 && !r && seq === e.artSeq; i++){
    try{ r = await api.post('/api/armory/bake_preview', Object.assign(armExpBody(), {settings: e.settings, side: 512})); }
    catch(err){ await new Promise(ok => setTimeout(ok, 250 * (i + 1))); }
  }
  if(seq !== e.artSeq) return;
  e.artPeek = r;
  if(e.step === 'uv') armExpDrawSheets();
}
function armExpSet(key, v){
  armExpEditBegin();
  const s = armExp().settings;
  if(key === 'margin') s.margin = Math.max(0, Math.min(5, +v || 0));
  else if(key === 'dyes') s.dyes = !!v;
  else if(key === 'rotate') s.rotate = v ? 'free' : 'quarter';
  else if(key === 'size') s.size = {both: v === 'auto' ? 'auto' : +v};
  armExpReplan();
  armExpEditEnd();
}
function armExpObjSheet(id, v){
  armExpEditBegin();
  const s = armExp().settings;
  if(v) s.obj_sheet[id] = v; else delete s.obj_sheet[id];
  // an object's own choice beats what was said for its islands one by one
  if(armExp().plan) for(const sh of Object.values(armExp().plan.sheets))
    for(const b of sh.blocks) if(b.objs.includes(id)) delete s.block_sheet[b.id];
  armExpReplan();
  armExpEditEnd();
}
function armExpScale(id, pct){
  armExpEditBegin();
  const s = armExp().settings;
  const v = Math.max(5, Math.min(100, +pct || 100)) / 100;
  if(v >= 1) delete s.scale[id]; else s.scale[id] = v;
  armExpReplan();
  armExpEditEnd();
}
/* An island picked on a sheet: its object's row and its object's other
   islands light up, its source texture shows beside the sheets with it
   marked, and a slider scales it alone, on top of its object's scale. */
function armExpSelBlock(){
  const e = armExp();
  if(!e.sel || !e.plan) return null;
  for(const sh of ['main', 'attach']){
    const b = e.plan.sheets[sh].blocks.find(x => x.id === e.sel);
    if(b) return b;
  }
  return null;
}
function armExpPick(sh, ev){
  const e = armExp(), S = e.plan && e.plan.sheets[sh], cv = ev.currentTarget;
  if(e.noClick){ e.noClick = false; return; }
  if(!S || !S.size) return;
  const r = cv.getBoundingClientRect();
  const x = (ev.clientX - r.left) * S.size / r.width, y = (ev.clientY - r.top) * S.size / r.height;
  // the smallest box under the click, as boxes of shapes packed by shape nest
  let hit = null, best = Infinity;
  for(const b of S.blocks){
    if(!b.placed) continue;
    const shown = armExpDisplayBlock(b);
    const w = shown.rot ? shown.h : shown.w, h = shown.rot ? shown.w : shown.h;
    if(x >= b.x && x < b.x + w && y >= b.y && y < b.y + h && w * h < best){ hit = b; best = w * h; }
  }
  if(e.numericScale){ armExpScaleEnd(false); return; }
  e.drag = null;
  e.sel = hit ? hit.id : null; e.selSrc = null;
  armExportPaint();
  const focus = document.getElementById('armExpCv_' + sh);
  if(focus) focus.focus({preventScroll: true});
  if(hit) armExpFetchSel();
}
async function armExpFetchSel(){
  const e = armExp(), id = e.sel;
  try{
    const r = await api.post('/api/armory/uv_source', Object.assign(armExpBody(), {settings: e.settings, block: id}));
    if(e.sel !== id) return;
    e.selSrc = r;
  }catch(err){ if(e.sel === id) e.selSrc = {err: errText(err)}; }
  const box = document.getElementById('armExpSel');
  if(box) box.innerHTML = armExpSelHtml();
}
// an object picked from the list: its largest island, placed or not
function armExpPickObj(id, ev){
  if(ev && ev.target.closest('select,input,option,button')) return;
  const e = armExp();
  if(!e.plan) return;
  const mine = ['main', 'attach'].flatMap(sh => e.plan.sheets[sh].blocks).filter(b => b.objs.includes(id));
  if(!mine.length) return;
  mine.sort((a, b) => (b.placed - a.placed) || (b.w * b.h - a.w * a.h));
  e.sel = mine[0].id; e.selSrc = null;
  armExportPaint();
  armExpFetchSel();
}

/* A corner of the picked island dragged: the island is drawn at the new size
   from the opposite corner while the mouse moves, and the scale is set on
   release. The picture stays until the packing it asks for comes back, so it
   shows with Live off too. */
function armExpCvPoint(cv, ev){
  const r = cv.getBoundingClientRect();
  return {x: (ev.clientX - r.left) * cv.width / r.width, y: (ev.clientY - r.top) * cv.height / r.height,
          tol: 9 * cv.width / r.width};
}
function armExpSelBox(sh){
  const e = armExp(), b = armExpSelBlock();
  const S = e.plan && e.plan.sheets[sh];
  if(!b || !b.placed || !S || !S.blocks.includes(b)) return null;
  const k = 512 / S.size;
  const shown = armExpDisplayBlock(b);
  return {b, x: b.x * k, y: b.y * k, w: (shown.rot ? shown.h : shown.w) * k, h: (shown.rot ? shown.w : shown.h) * k};
}
function armExpCorner(sh, pt){
  const box = armExpSelBox(sh);
  if(!box) return null;
  for(const [cx, cy] of [[0, 0], [1, 0], [0, 1], [1, 1]]){
    if(Math.abs(pt.x - (box.x + cx * box.w)) <= pt.tol && Math.abs(pt.y - (box.y + cy * box.h)) <= pt.tol)
      return {box, cx, cy};
  }
  return null;
}
function armExpHover(sh, ev){
  const point = armExpCvPoint(ev.currentTarget, ev); armExp().pointer = Object.assign({sh}, point);
  if(armExp().numericScale || (armExp().drag && !armExp().drag.done)) return;
  const cv = ev.currentTarget, c = armExpCorner(sh, armExpCvPoint(cv, ev));
  cv.style.cursor = c ? (c.cx === c.cy ? 'nwse-resize' : 'nesw-resize') : '';
}
function armExpDown(sh, ev){
  const e = armExp(), cv = ev.currentTarget, c = armExpCorner(sh, armExpCvPoint(cv, ev));
  if(e.numericScale || !c || ev.button !== 0) return;
  ev.preventDefault();
  const own = e.settings.block_scale[c.box.b.id] || 1, B = c.box;
  e.drag = {sh, id: B.b.id, ox: B.x, oy: B.y, ow: B.w, oh: B.h, W0: B.w / own, H0: B.h / own, s: own,
            ax: B.x + (1 - c.cx) * B.w, ay: B.y + (1 - c.cy) * B.h, dx: c.cx ? 1 : -1, dy: c.cy ? 1 : -1};
  const move = mv => {
    const d = e.drag, pt = armExpCvPoint(cv, mv);
    d.s = Math.max(0.05, Math.min(10, Math.max((pt.x - d.ax) * d.dx / d.W0, (pt.y - d.ay) * d.dy / d.H0)));
    const sl = document.querySelector('#armExpSel input[type=range]');
    if(sl){ sl.value = Math.round(d.s * 100); const num = document.getElementById('armExpScaleNumber'); if(num) num.value = sl.value; }
    armExpPaintCv(sh);
  };
  const up = () => {
    window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up);
    const d = e.drag;
    if(!d) return;
    e.drag = null; e.noClick = true;
    setTimeout(() => { e.noClick = false; }, 0);
    armExpBlockScale(Math.round(d.s * 100));
    armExpDrawSheets();
  };
  window.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
}
function armExpDrawDrag(ctx, cv){
  const d = armExp().drag;
  if(!d) return;
  const w = d.W0 * d.s, h = d.H0 * d.s;
  const x = d.dx > 0 ? d.ax : d.ax - w, y = d.dy > 0 ? d.ay : d.ay - h;
  ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(d.ox, d.oy, d.ow, d.oh);
  if(cv._img){
    const r = cv._img.naturalWidth / cv.width;
    ctx.drawImage(cv._img, d.ox * r, d.oy * r, d.ow * r, d.oh * r, x, y, w, h);
  }
  ctx.setLineDash([5, 3]); ctx.lineWidth = 2; ctx.strokeStyle = '#ffd640';
  ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
  ctx.setLineDash([]); ctx.lineWidth = 1;
  armExpHandles(ctx, x, y, w, h);
  ctx.font = 'bold 13px sans-serif'; ctx.fillStyle = '#ffd640';
  ctx.fillText(Math.round(d.s * 100) + '%', x + 4, y + 15);
}
function armExpHandles(ctx, x, y, w, h){
  ctx.fillStyle = '#ffd640'; ctx.strokeStyle = '#000';
  for(const [cx, cy] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]){
    ctx.fillRect(cx - 4, cy - 4, 8, 8); ctx.strokeRect(cx - 4.5, cy - 4.5, 9, 9);
  }
}
function armExpBlockScale(pct, live=false){
  const e = armExp(), n = Number(pct);
  if(!e.sel || !Number.isFinite(n) || pct === '') return;
  armExpEditBegin();
  clearTimeout(ARM.expTimer); e.seq = (e.seq || 0) + 1;
  const v = Math.max(5, Math.min(1000, n)) / 100;
  if(v === 1) delete e.settings.block_scale[e.sel]; else e.settings.block_scale[e.sel] = v;
  armExpSyncScale();
  for(const sh of ['main','attach']) armExpPaintCv(sh);
  if(!live){ armExpEditEnd(); armExpReplan(); }
}
// Keep every pending island visible when Live is off or a replan is in flight.
function armExpDisplayBlock(b){
  const ratio = (armExp().settings.block_scale[b.id] || 1) / (b.own || 1);
  return Object.assign({}, b, {w: b.w * ratio, h: b.h * ratio});
}
function armExpDrawPending(ctx, cv, S, k){
  for(const b of S.blocks){
    const shown = armExpDisplayBlock(b);
    if(!b.placed || shown.w === b.w) continue;
    const x = b.x * k, y = b.y * k, w = (b.rot ? b.h : b.w) * k, h = (b.rot ? b.w : b.h) * k;
    ctx.fillStyle = '#1d2128'; ctx.fillRect(x, y, w, h);
    const nw = (b.rot ? shown.h : shown.w) * k, nh = (b.rot ? shown.w : shown.h) * k;
    if(cv._img){
      const r = cv._img.naturalWidth / cv.width;
      ctx.drawImage(cv._img, x*r, y*r, w*r, h*r, x, y, nw, nh);
    }else{ ctx.fillStyle = armExpColour(b.objs[0]); ctx.fillRect(x, y, nw, nh); }
  }
}
function armExpScaleEnd(cancel){
  const e = armExp(), f = e.numericScale;
  if(!f) return;
  window.removeEventListener('mousemove', f.track);
  window.removeEventListener('contextmenu', f.context);
  e.numericScale = null;
  if(cancel){ e.settings.block_scale[f.id] = f.own; armExpHistory().start = null; }
  else armExpEditEnd();
  armExpSyncScale(); armExpDrawSheets(); armExpReplan();
}
function armExpKey(ev){
  const e = armExp(), key = ev.key.toLowerCase();
  ev.stopPropagation();
  if((ev.ctrlKey || ev.metaKey) && (key === 'z' || key === 'y')){
    ev.preventDefault(); armExpUndo(key === 'y' || !!ev.shiftKey); return;
  }
  if(!e.numericScale){
    if(key !== 's' || !e.sel) return;
    armExpEditBegin(); clearTimeout(ARM.expTimer); e.seq = (e.seq || 0) + 1;
    const sh = ['main','attach'].find(sh => armExpSelBox(sh));
    const box = sh && armExpSelBox(sh), pt = e.pointer;
    const cx = box ? box.x + box.w/2 : 0, cy = box ? box.y + box.h/2 : 0;
    const f = e.numericScale = {id:e.sel, value:'', own:e.settings.block_scale[e.sel] || 1,
      sh, cx, cy, radius: pt && pt.sh === sh ? Math.max(10, Math.hypot(pt.x-cx,pt.y-cy)) : 50};
    f.track = mv => {
      if(e.numericScale !== f || f.value) return;
      const cv = document.getElementById('armExpCv_' + sh);
      if(!cv){ armExpScaleEnd(true); return; }
      const p = armExpCvPoint(cv, mv);
      e.settings.block_scale[f.id] = Math.max(.05, Math.min(10, f.own * Math.hypot(p.x-cx,p.y-cy)/f.radius));
      armExpSyncScale(); for(const sheet of ['main','attach']) armExpPaintCv(sheet);
    };
    f.context = ev => { ev.preventDefault(); armExpScaleEnd(true); };
    window.addEventListener('mousemove', f.track); window.addEventListener('contextmenu', f.context);
  }else if(key === 'escape') armExpScaleEnd(true);
  else if(key === 'enter') armExpScaleEnd(false);
  else if(/^[0-9.]$/.test(key) || key === 'backspace'){
    const f=e.numericScale;
    f.value = key === 'backspace' ? f.value.slice(0,-1) : f.value+key;
    const factor=Number(f.value);
    e.settings.block_scale[f.id] = f.value && Number.isFinite(factor) ? Math.max(.05,Math.min(10,f.own*factor)) : f.own;
    armExpSyncScale(); armExpDrawSheets();
  }else return;
  ev.preventDefault();
}
function armExpList(show){ armExp().listHidden = !show; armExportPaint(); }
function armExpSelHtml(){
  const e = armExp(), b = armExpSelBlock();
  if(!b) return `<b>${tt('armory.exp_sel_title')}</b><div class="count">${tt('armory.exp_sel_none')}</div>`;
  const names = new Map(e.plan.objects.map(o => [o.id, o.name]));
  const own = Math.round((e.settings.block_scale[b.id] || 1) * 100), src = e.selSrc;
  return `<b>${tt('armory.exp_sel_title')}</b>
    <div class="count">${esc(tt('armory.exp_sel_of', {names: b.objs.map(id => names.get(id) || id).join(', ')}))}</div>
    ${!src ? `<div class="count">${tt('armory.reading')}</div>`
      : src.err ? `<div class="armexperr">${esc(src.err)}</div>`
      : `<div class="count">${esc(tt('armory.exp_sel_from', {name: src.name || '-'}))}</div><img src="${src.picture}" alt="">`}
    <label title="${ttA('armory.exp_sel_scale_title')}">${tt('armory.exp_sel_scale')}</label>
    <div class="armexprow"><input id="armExpScaleSlider" onkeydown="if(event.ctrlKey||event.metaKey)armExpKey(event)" type="range" min="5" max="${Math.max(100, own)}" step="1" value="${own}"
        oninput="armExpBlockScale(this.value, true)" onchange="armExpBlockScale(this.value)">
      <input id="armExpScaleNumber" onkeydown="if(event.ctrlKey||event.metaKey)armExpKey(event)" type="number" class="armnum" min="5" max="1000" step="1" value="${own}" oninput="armExpBlockScale(this.value,true)" onchange="armExpBlockScale(this.value)">%
      ${own !== 100 ? `<button class="mini" onclick="armExpBlockScale(100)">${tt('armory.exp_sel_reset')}</button>` : ''}</div>
    ${Math.round(b.scale * 100) !== own ? `<div class="count">${tt('armory.exp_sel_overall', {pct: Math.round(b.scale * 100)})}</div>` : ''}
    ${b.placed ? `<div class="count">${tt('armory.exp_corner_hint')}</div>` : `<div class="armexpleftnote">${tt('armory.exp_sel_left')}</div>`}`;
}
function armExpMoveBlock(sh, i, to){
  armExpEditBegin();
  const b = armExp().plan.sheets[sh].blocks[i];
  if(b){ armExp().settings.block_sheet[b.id] = to; armExpReplan(); }
  armExpEditEnd();
}
function armExpScaleSheet(sheet, pct){
  armExpEditBegin();
  const e = armExp();
  if(!e.plan) return;
  const ids = new Set(e.plan.sheets[sheet].blocks.flatMap(b => b.objs));
  for(const id of ids) armExpScale(id, pct);
  armExpEditEnd();
}

const armExpLabel = s => s === 'attach' ? tt('armory.exp_sheet_attach') : tt('armory.exp_sheet_main');

function armExpUvHtml(){
  const e = armExp(), P = e.plan, s = e.settings;
  if(!P) return `<div class="count">${e.busy ? tt('armory.reading') : ''}</div>`;
  // both sheets are one size, as the game's skins are
  const both = (s.size && s.size.both) || 'auto';
  const sizeSel = `<label title="${esc(tt('armory.exp_sheets_title'))}">${tt('armory.exp_sheets')}<select onchange="armExpSet('size', this.value)">
      <option value="auto"${both === 'auto' ? ' selected' : ''}>${tt('armory.exp_size_auto')}</option>
      ${ARM_SIZES.map(z => `<option value="${z}"${both === z ? ' selected' : ''}>${z}</option>`).join('')}</select></label>`;
  const selB = armExpSelBlock(), selObjs = new Set(selB ? selB.objs : []);
  const leftObjs = new Set(['main', 'attach'].flatMap(sh => P.sheets[sh].blocks.filter(b => P.sheets[sh].left.includes(b.id)).flatMap(b => b.objs)));
  const rows = P.objects.map(o => `<tr class="${selObjs.has(o.id) ? 'armexpsel' : ''}${leftObjs.has(o.id) ? ' armexpleft' : ''}"
        onclick="armExpPickObj(${o.id}, event)" title="${ttA('armory.exp_pick_row_title')}">
      <td>${leftObjs.has(o.id) ? `<span class="armleftmark" title="${ttA('armory.exp_left_mark_title')}">!</span>` : ''}<span class="armswatch" style="background:${armExpColour(o.id)}"></span> ${esc(o.name)}</td>
      <td class="num">${o.islands}</td>
      <td class="num">${Math.round(Math.sqrt(o.area)).toLocaleString()}²</td>
      <td class="num">${o.needs || '-'}</td>
      <td>${o.origin === 'any' ? tt('armory.exp_origin_file') : o.origin === 'both' ? tt('armory.exp_origin_both') : armExpLabel(o.origin)}</td>
      <td><select onchange="armExpObjSheet(${o.id}, this.value)">
        <option value="">${tt('armory.exp_sheet_default')}</option>
        ${['main', 'attach'].map(x => `<option value="${x}"${s.obj_sheet[o.id] === x ? ' selected' : ''}>${armExpLabel(x)}</option>`).join('')}</select>
        <span class="count">${o.sheets.map(armExpLabel).join(' + ')}</span></td>
      <td><input type="number" class="armnum" min="5" max="100" step="5" value="${Math.round(o.scale * 100)}"
        onchange="armExpScale(${o.id}, this.value)" title="${esc(tt('armory.exp_scale_title'))}">%</td></tr>`).join('');
  const sheet = sh => {
    const S = P.sheets[sh];
    if(!S.size) return `<div class="armexpsheet"><b>${armExpLabel(sh)}</b><div class="count">${tt('armory.exp_sheet_unused')}</div></div>`;
    return `<div class="armexpsheet"><b>${armExpLabel(sh)} · ${S.size}²</b>
      <span class="count">${tt('armory.exp_sheet_facts', {fill: Math.round(S.fill * 100), needs: S.needs, margin: S.margin_px})}</span>
      ${S.left.length ? `<span class="armexpleftnote">${tt('armory.exp_sheet_left', {n: S.left.length})}</span>` : ''}
      <canvas id="armExpCv_${sh}" width="512" height="512" tabindex="0" onkeydown="armExpKey(event)" onclick="armExpPick('${sh}', event)" onmousedown="armExpDown('${sh}', event)"
        onmousemove="armExpHover('${sh}', event)" title="${ttA('armory.exp_pick_title')}"></canvas></div>`;
  };
  return `<div class="armexprow">
      <label class="armcheck" title="${ttA('armory.exp_live_title')}"><input type="checkbox"${e.live !== false ? ' checked' : ''}
        onchange="armExpLive(this.checked)"> ${tt('armory.exp_live')}</label>
      <button id="armExpRefresh" class="mini${e.stale ? ' primary' : ''}" onclick="armExpRefresh()" title="${ttA('armory.exp_refresh_title')}">${tt('armory.exp_refresh')}</button>
      <label class="armcheck" title="${ttA('armory.exp_textures_title')}"><input type="checkbox"${e.art ? ' checked' : ''}
        onchange="armExpArt(this.checked)"> ${tt('armory.exp_textures')}</label>
      <button class="mini" onclick="armExpList(${e.listHidden ? 'true' : 'false'})" title="${ttA('armory.exp_hide_list_title')}">${tt(e.listHidden ? 'armory.exp_show_list' : 'armory.exp_hide_list')}</button></div>
    <div class="armexprow">${sizeSel}
      <label>${tt('armory.exp_margin')}<input type="number" class="armnum" min="0" max="5" step="0.1" value="${s.margin}"
        onchange="armExpSet('margin', this.value)" title="${esc(tt('armory.exp_margin_title'))}">%</label>
      <label class="armcheck"><input type="checkbox"${s.dyes ? ' checked' : ''} onchange="armExpSet('dyes', this.checked)"> ${tt('armory.exp_apply_dyes')}</label>
      <label class="armcheck" title="${esc(tt('armory.exp_free_turn_title'))}"><input type="checkbox"${s.rotate === 'free' ? ' checked' : ''}
        onchange="armExpSet('rotate', this.checked)"> ${tt('armory.exp_free_turn')}</label></div>
    <div class="count armnote">${tt('armory.exp_uv_summary', {islands: P.islands, blocks: P.blocks, folded: P.folded})}</div>
    ${P.turned ? `<div class="count armnote">${tt('armory.exp_turned', {n: P.turned})}</div>` : ''}
    ${P.fits ? '' : armExpOverflowHtml()}
    ${P.auto ? `<div class="armissue warning">${P.auto.sheet ? tt('armory.exp_auto_done', {sheet: armExpLabel(P.auto.sheet), pct: Math.round(P.auto.scale * 100)})
                                                       : tt('armory.exp_auto_moved', {n: P.auto.moved})}</div>` : ''}
    <div class="armexpuv${e.listHidden ? ' nolist' : ''}">
      <div class="armexplist"${e.listHidden ? ' hidden' : ''}><table class="armexptable"><thead><tr><th>${tt('armory.exp_col_object')}</th><th>${tt('armory.exp_col_islands')}</th>
        <th>${tt('armory.exp_col_area')}</th><th>${tt('armory.exp_col_needs')}</th><th>${tt('armory.exp_col_from')}</th>
        <th>${tt('armory.exp_col_sheet')}</th><th>${tt('armory.exp_col_scale')}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="armexpsheets">${sheet('main')}${sheet('attach')}</div>
      <div id="armExpSel" class="armexpselbox">${armExpSelHtml()}</div>
    </div>`;
}

/* A sheet ran out of room: say which islands did not fit and what each
   would take, and the four ways out. */
function armExpOverflowHtml(){
  const e = armExp(), P = e.plan;
  const names = new Map(P.objects.map(o => [o.id, o.name]));
  let out = `<div class="armexpfull"><b>${tt('armory.exp_full')}</b>
    <div class="armexprow"><button onclick="armExportPlan(true)">${tt('armory.exp_auto')}</button><span class="count">${tt('armory.exp_auto_note')}</span></div>`;
  for(const sh of ['main', 'attach']){
    const S = P.sheets[sh];
    if(!S.left.length) continue;
    const other = sh === 'main' ? 'attach' : 'main';
    const left = S.blocks.filter(b => S.left.includes(b.id));
    out += `<div class="armsect">${tt('armory.exp_left_on', {sheet: armExpLabel(sh), n: left.length})}</div>`;
    out += left.map(b => `<div class="armexprow"><span>${esc(b.objs.map(id => names.get(id) || id).join(', '))}</span>
        <span class="count">${tt('armory.exp_share', {pct: (b.share * 100).toFixed(1)})}</span>
        <button class="mini" onclick="armExpMoveBlock('${sh}', ${S.blocks.indexOf(b)}, '${other}')">${tt('armory.exp_move_to', {sheet: armExpLabel(other)})}</button></div>`).join('');
    out += `<div class="armexprow"><label>${tt('armory.exp_scale_sheet')}<input type="number" class="armnum" min="5" max="100" step="5" value="90"
        onchange="armExpScaleSheet('${sh}', this.value)">%</label>
      <span class="count">${tt('armory.exp_scale_margin', {pct: S.recommended_margin})}</span>
      <span class="count">${tt('armory.exp_lower_margin')}</span></div>`;
  }
  return out + '</div>';
}

function armExpColour(id){
  const h = (id * 137.508) % 360;
  return `hsl(${h.toFixed(0)},62%,58%)`;
}
function armExpDrawSheets(){
  const e = armExp(), P = e.plan;
  if(!P) return;
  for(const sh of ['main', 'attach']){
    const cv = document.getElementById('armExpCv_' + sh), S = P.sheets[sh];
    if(!cv || !S.size) continue;
    const art = e.art && e.artPeek && e.artPeek.sheets && e.artPeek.sheets[sh];
    // 99l: else the server draws each block's shape, the texels it takes
    const pic = art && art.art ? art.art : S.picture;
    cv._img = null; cv._pic = !!pic;
    armExpPaintCv(sh);
    if(pic){
      const img = new Image();
      img.onload = () => { if(cv.isConnected){ cv._img = img; armExpPaintCv(sh); } };
      img.src = pic;
    }
  }
}
function armExpPaintCv(sh){
  const e = armExp(), P = e.plan, cv = document.getElementById('armExpCv_' + sh);
  const S = P && P.sheets[sh];
  if(!cv || !S || !S.size) return;
  const ctx = cv.getContext('2d'), k = cv.width / S.size;
  ctx.fillStyle = '#1d2128'; ctx.fillRect(0, 0, cv.width, cv.height);
  if(cv._img) ctx.drawImage(cv._img, 0, 0, cv.width, cv.height);
  else if(!cv._pic) for(const b of S.blocks){
      if(!b.placed) continue;
      const w = (b.rot ? b.h : b.w) * k, h = (b.rot ? b.w : b.h) * k;
      ctx.fillStyle = armExpColour(b.objs[0]);
      ctx.globalAlpha = 0.75; ctx.fillRect(b.x * k, b.y * k, w, h);
      ctx.globalAlpha = 1; ctx.strokeStyle = '#000'; ctx.strokeRect(b.x * k + 0.5, b.y * k + 0.5, w - 1, h - 1);
    }
  if(cv._pic && !cv._img) return;
  armExpDrawPending(ctx, cv, S, k);
  armExpDrawSel(ctx, S, k, !(e.drag && e.drag.sh === sh));
  if(e.drag && e.drag.sh === sh) armExpDrawDrag(ctx, cv);
  if(e.numericScale){ ctx.fillStyle = '#ffd640'; ctx.font = 'bold 14px sans-serif'; ctx.fillText('S ' + (e.numericScale.value || '1'), 8, 20); }
}
// the picked island boxed bright, its object's other islands fainter
function armExpDrawSel(ctx, S, k, handles){
  const sel = armExpSelBlock();
  if(!sel) return;
  const mine = new Set(sel.objs);
  for(const raw of S.blocks){
    const b = armExpDisplayBlock(raw);
    if(!b.placed) continue;
    const on = b.id === sel.id;
    if(!on && !b.objs.some(o => mine.has(o))) continue;
    const w = (b.rot ? b.h : b.w) * k, h = (b.rot ? b.w : b.h) * k;
    ctx.fillStyle = on ? 'rgba(255,214,64,0.35)' : 'rgba(255,214,64,0.14)';
    ctx.fillRect(b.x * k, b.y * k, w, h);
    ctx.lineWidth = on ? 2 : 1;
    ctx.strokeStyle = on ? '#ffd640' : 'rgba(255,214,64,0.6)';
    ctx.strokeRect(b.x * k + 1, b.y * k + 1, w - 2, h - 2);
    if(on && handles) armExpHandles(ctx, b.x * k, b.y * k, w, h);
  }
  ctx.lineWidth = 1;
}

/* --- 3. bake --------------------------------------------------------------- */

function armExpBakeHtml(){
  const e = armExp(), P = e.plan;
  const sizes = P ? ['main', 'attach'].filter(s => P.sheets[s].size).map(s => `${armExpLabel(s)} ${P.sheets[s].size}²`).join(', ') : '';
  const done = e.done ? `<div class="armissue ok">${tt('armory.exp_written', {folder: e.done.folder})}
      <div class="count">${e.done.files.map(esc).join(', ')}</div>
      <div class="count">${tt('armory.exp_written_facts', {vertices: e.done.vertices.toLocaleString(), triangles: e.done.triangles.toLocaleString(), groups: e.done.groups})}</div></div>` : '';
  return `<div class="count armnote">${tt('armory.exp_bake_intro', {sheets: sizes})}</div>
    <div class="armpathrow"><input id="armExpFolder" value="${esc(e.folder)}" placeholder="${esc(tt('armory.exp_folder'))}" oninput="armExpOutput('folder',this.value)" onchange="armExpFindExisting()">
      <button onclick="armExpBrowse()">${tt('armory.browse')}</button></div>
    <div class="armexprow"><label>${tt('armory.exp_stem')}<input value="${esc(e.stem)}" list="armExportStems" oninput="armExpOutput('stem',this.value)" onchange="armExpFindExisting()"></label>
      <datalist id="armExportStems">${(e.exportCandidates || []).map(n => `<option value="${esc(n)}">`).join('')}</datalist>
      <button onclick="armExpFindExisting()">${tt('armory.check_existing_export')}</button>
      <button class="primary" onclick="armExpBake()"${e.busy ? ' disabled' : ''}>${tt('armory.exp_bake')}</button></div>
    <div class="count">${tt('armory.exp_bake_note')}</div>
    <div class="armexprow"><label>${tt('armory.exp_normals_pick')}
      <select onchange="armExpNormMode(this.value)">${ARM_NORM_MODES.map(m =>
        `<option value="${m}"${armNormals().mode === m ? ' selected' : ''}>${esc(armNormModeLabel(m))}</option>`).join('')}</select></label>
      <button onclick="armExpPreview()"${e.peeking ? ' disabled' : ''} title="${ttA('armory.exp_preview_title')}">${tt('armory.exp_preview')}</button></div>
    <div class="count">${tt('armory.exp_normals_note')}</div>
    <div id="armBakeProgress" role="status">${e.baking ? `${e.bakePct || 0}% <progress max="100" value="${e.bakePct || 0}"></progress>` : ''}</div>
    ${armExpPreviewHtml()}${done}`;
}
/* The bake's normal maps chosen here as well as in the objects panel: the
   same project setting, so the two never disagree. A preview already shown
   is dropped, since it no longer says what will be written. */
function armExpNormMode(m){
  armNormals().mode = m;
  if(typeof armNormChanged === 'function') armNormChanged();
  armExp().peek = null;
  armExportPaint();
}
/* The actual images the bake would write, art and normal map for each sheet,
   rendered by the bake's own code on the server and nothing written. */
async function armExpPreview(){
  const e = armExp();
  e.peeking = true; e.err = ''; armExportPaint();
  try{
    e.peek = await api.post('/api/armory/bake_preview', Object.assign(armExpBody(), {settings: e.settings, side: 1024}));
  }catch(err){ e.err = errText(err); e.peek = null; }
  e.peeking = false;
  armExportPaint();
}
function armExpPreviewHtml(){
  const e = armExp(), pk = e.peek;
  if(e.peeking) return `<div class="count armnote">${tt('armory.exp_preview_busy')}</div>`;
  if(!pk) return '';
  const view = e.peekView || 'art';
  const tile = sh => {
    const S = pk.sheets[sh];
    if(!S) return '';
    const src = view === 'normal' ? S.normal : S.art;
    return `<figure class="armpeek"><a href="${src}" target="_blank" rel="noopener" title="${ttA('armory.exp_preview_open')}">
        <img src="${src}" alt=""></a>
      <figcaption>${esc(armExpLabel(sh))} · ${S.size}² · ${view === 'normal' ? tt('armory.exp_preview_normal') : tt('armory.exp_preview_art')}</figcaption></figure>`;
  };
  return `<div class="armexprow">
      <button class="mini${view === 'art' ? ' on' : ''}" onclick="armExp().peekView='art';armExportPaint()">${tt('armory.exp_preview_art')}</button>
      <button class="mini${view === 'normal' ? ' on' : ''}" onclick="armExp().peekView='normal';armExportPaint()">${tt('armory.exp_preview_normal')}</button>
      <span class="count">${tt('armory.exp_preview_mode', {mode: esc(armNormModeLabel(pk.normals))})}</span></div>
    <div class="armpeeks">${tile('main')}${tile('attach')}</div>`;
}
async function armExpBrowse(){
  let r;
  try{ r = await api.post('/api/browse_folder', {title: tt('armory.exp_folder'), dir: armExp().folder}); }catch(err){ toast(errText(err)); return; }
  if(r && r.path){ armExpOutput('folder',r.path); await armExpFindExisting(); armExportPaint(); }
}
async function armExpBake(){
  const e = armExp();
  if(!e.folder.trim()){ toast(tt('armory.exp_folder')); return; }
  if(e.baking) return;
  e.busy = true; e.baking = true; e.bakePct = 0; e.done = null; armExportPaint();
  const job = 'armbake-' + Date.now() + '-' + Math.random().toString(36).slice(2);
  const poll = async () => {
    try{
      const r = await api.get('/api/progress?job=' + enc(job));
      if(!e.baking) return;
      e.bakePct = r.pct || 0;
      const el = document.getElementById('armBakeProgress');
      if(el){ el.textContent = e.bakePct + '% '; const bar = document.createElement('progress'); bar.max=100; bar.value=e.bakePct; el.appendChild(bar); }
    }catch(err){}
  };
  const timer = setInterval(poll, 500);
  try{
    e.done = await api.post('/api/armory/bake', Object.assign(armExpBody(), {settings: e.settings, folder: e.folder, stem: e.stem, job}));
    e.err = ''; armSave();
  }catch(err){ e.err = errText(err); }
  clearInterval(timer); e.baking = false;
  e.busy = false;
  armExportPaint();
}

/* --- 4. into a mod (95k) ----------------------------------------------------------

   Three ways in, each through the toolkit's own doors (armunit.py), so My
   Changes shows what was written and the Log's Undo takes it back out:
   SKIP a new modeldb entry only; ADD it to a unit as its soldier model; or a
   NEW UNIT duplicated from a chosen one, wearing it, with a role template's
   class, formation, attributes and mount on top. An entry is a clone of one
   the mod has, for its skeletons and weapons: the unit's own soldier, a role
   template's most typical entry, or one named here. */

function armExpMod(){
  const e = armExp();
  return e.mod = e.mod || {target: state.src || (ARM.mods || [])[0] || '', choice: 'skip', name: '', folder: '',
                           template: '', clone_from: '', unit: '', new_type: '', new_name: '', data: null, plan: null};
}
async function armExpModLoad(){
  const m = armExpMod(), e = armExp();
  if(!ARM.mods){ try{ ARM.mods = (await api.get('/api/mods')).map(x => x.name); }catch(err){ ARM.mods = []; } }
  if(!m.target) m.target = state.src || ARM.mods[0] || '';
  if(!m.name) m.name = (e.stem || 'armory_model').toLowerCase().replace(/[^a-z0-9_]/g, '_');
  m.plan = null;
  if(!m.target){ armExportPaint(); return; }
  e.busy = true; armExportPaint();
  try{ m.data = await api.get('/api/armory/templates?mod=' + enc(m.target)); e.err = ''; }
  catch(err){ m.data = null; e.err = errText(err); }
  e.busy = false;
  armExportPaint();
  armExpUnitFolders();
}
function armExpRecentFolders(){
  try{ return JSON.parse(localStorage.getItem('armory.folders.' + armExpMod().target) || '[]'); }catch(err){ return []; }
}
function armExpRememberFolder(){
  const m = armExpMod(), path = m.folder.trim().replace(/\\/g,'/');
  if(!path) return;
  const memento = [path,...armExpRecentFolders().filter(p => p !== path)].slice(0,12);
  try{ localStorage.setItem('armory.folders.' + m.target, JSON.stringify(memento)); }catch(err){}
  armSave();
  const select = document.getElementById('armExpFolderChoices');
  if(select) select.innerHTML = `<option value="">${tt('armory.folder_choices')}</option>` + armExpFolderChoices();
}
function armExpFolderChoices(){
  const m = armExpMod(), rows = new Map();
  if(m.choice !== 'skip') for(const row of m.folders || []) for(const folder of row.folders || []){
    if(!rows.has(folder)) rows.set(folder, row.name + ' · ' + folder);
  }
  for(const folder of armExpRecentFolders()) if(!rows.has(folder)) rows.set(folder, tt('armory.recent_folder', {folder}));
  return [...rows].map(([folder,label]) => `<option value="${esc(folder)}"${m.folder === folder ? ' selected' : ''}>${esc(label)}</option>`).join('');
}
async function armExpUnitFolders(){
  const m=armExpMod(), target=m.target, unit=m.unit;
  m.folders=[];
  if(m.choice === 'skip' || !unit) return;
  try{
    const r=await api.get('/api/unit_models?mod='+enc(target)+'&type='+enc(unit));
    if(m.target !== target || m.unit !== unit) return;
    m.folders=r.models || [];
  }catch(err){ if(m.target === target && m.unit === unit) m.folders=[]; }
  if(armExp().step === 'mod') armExportPaint();
}
async function armExpModBrowse(){
  try{
    const r=await api.post('/api/armory/install/folder',{mod:armExpMod().target});
    if(r.path != null){ armExpModSet('folder',r.path); armExpRememberFolder(); armExportPaint(); }
  }catch(err){ toast(errText(err),6000); }
}
function armExpChooseFolder(path){
  if(!path) return;
  armExpModSet('folder',path); armExpRememberFolder();
}
const armRoleLabel = r => ({heavy_infantry: tt('armory.role_heavy_infantry'), spear: tt('armory.role_spear'),
  pike: tt('armory.role_pike'), archer: tt('armory.role_archer'), crossbow: tt('armory.role_crossbow'),
  javelin: tt('armory.role_javelin'), cavalry: tt('armory.role_cavalry')})[r] || r;

function armExpModStepTitle(st, m){
  if(st.kind === 'transfer') return tt('armory.exp_step_duplicate');
  if(st.kind === 'bmdb') return tt('armory.exp_step_entry');
  if(m.choice === 'new') return tt('armory.exp_step_new_unit_edit', {unit: st.on});
  return tt('armory.exp_step_unit_edit');
}

function armExpModHtml(){
  const m = armExpMod(), d = m.data;
  const radio = (v, label, note) => `<label class="armcheck armexpchoice"><input type="radio" name="armExpChoice"${m.choice === v ? ' checked' : ''}
      onchange="armExpModSet('choice','${v}')"> <b>${label}</b> <span class="count">${note}</span></label>`;
  const mods = (ARM.mods || []).map(x => `<option${x === m.target ? ' selected' : ''}>${esc(x)}</option>`).join('');
  let html = `<div class="armexprow"><label>${tt('armory.exp_target_mod')}<select onchange="armExpModTarget(this.value)">${mods}</select></label></div>
    <div class="armexpchoices">${radio('skip', tt('armory.exp_choice_skip'), tt('armory.exp_choice_skip_note'))}
      ${radio('add', tt('armory.exp_choice_add'), tt('armory.exp_choice_add_note'))}
      ${radio('new', tt('armory.exp_choice_new'), tt('armory.exp_choice_new_note'))}</div>`;
  if(!d) return html;
  const units = `<datalist id="armExpUnits">${d.units.map(u => `<option value="${esc(u.type)}">${esc(u.category)} · ${esc(u['class'])}</option>`).join('')}</datalist>`;
  const entries = `<datalist id="armExpEntries">${d.entries.map(n => `<option value="${esc(n)}">`).join('')}</datalist>`;
  const roles = Object.values(d.templates);
  html += `<div class="armexprow">
      <label>${tt('armory.exp_entry_name')}<input value="${esc(m.name)}" oninput="armExpModSet('name', this.value, true)"></label>
      <label>${tt('armory.exp_entry_folder')}<input class="armwide" value="${esc(m.folder)}" placeholder="unit_models/_units/armory/${esc(m.name)}" oninput="armExpModSet('folder', this.value, true)" onchange="armExpRememberFolder()"></label>
      <button onclick="armExpModBrowse()">${tt('armory.browse')}</button>
      <select id="armExpFolderChoices" aria-label="${ttA('armory.folder_choices')}" onchange="armExpChooseFolder(this.value)"><option value="">${tt('armory.folder_choices')}</option>${armExpFolderChoices()}</select></div>`;
  if(m.choice !== 'skip')
    html += `<div class="armexprow"><label>${m.choice === 'new' ? tt('armory.exp_unit_from') : tt('armory.exp_unit')}<input list="armExpUnits" value="${esc(m.unit)}"
        placeholder="${esc(tt('armory.find'))}" onchange="armExpModSet('unit', this.value)"></label>${units}</div>`;
  if(m.choice === 'new')
    html += `<div class="armexprow"><label>${tt('armory.exp_new_type')}<input value="${esc(m.new_type)}" oninput="armExpModSet('new_type', this.value, true)"></label>
      <label>${tt('armory.exp_new_name')}<input value="${esc(m.new_name)}" oninput="armExpModSet('new_name', this.value, true)"></label></div>`;
  html += `<div class="armsect">${tt('armory.exp_skeletons_from')}</div>
    <div class="armexprow"><select onchange="armExpModSet('template', this.value)">
      <option value="">${m.choice === 'skip' ? tt('armory.exp_template_entry') : tt('armory.exp_template_unit')}</option>
      ${roles.map(t => `<option value="${t.role}"${m.template === t.role ? ' selected' : ''}>${esc(tt('armory.exp_template_option', {role: armRoleLabel(t.role), n: t.units}))}</option>`).join('')}</select>
      ${m.template ? '' : `<label>${tt('armory.exp_clone_from')}<input list="armExpEntries" value="${esc(m.clone_from)}" onchange="armExpModSet('clone_from', this.value)"></label>${entries}`}</div>`;
  const t = d.templates[m.template];
  if(t){
    const fields = Object.entries(t.fields).map(([k, v]) => `${k} ${v}`).join(' · ');
    html += `<div class="count armnote">${tt('armory.exp_template_facts', {example: t.example, skeletons: t.skeletons.join(', '), fields})}</div>`;
    if(m.choice !== 'new') html += `<div class="count armnote">${tt('armory.exp_template_fields_new_only')}</div>`;
  }
  html += `<div class="armexprow"><button onclick="armExpModPlan()">${tt('armory.exp_plan')}</button>
      <button class="primary" onclick="armExpModApply()"${m.plan && m.plan.ok ? '' : ' disabled'}>${tt('armory.exp_write')}</button>
      <button class="mini" onclick="armExpCards()" title="${esc(tt('armory.exp_cards_later'))}">${tt('armory.exp_cards')}</button></div>`;
  if(m.plan) html += m.plan.steps.map((st, i) => `<div class="armissue ${st.errors.length ? 'error' : 'ok'}">
      <b>${m.plan.steps.length > 1 ? `${i + 1}. ` : ''}${armExpModStepTitle(st, m)}</b>
      ${st.lines.slice(1).map(l => `<div class="count">${esc(l)}</div>`).join('')}
      ${st.warnings.map(w => `<div class="armexpwarn">${esc(w)}</div>`).join('')}
      ${st.errors.map(w => `<div class="armexperr">${esc(w)}</div>`).join('')}</div>`).join('');
  if(m.written) html += `<div class="armissue ok">${tt('armory.exp_written_mod', {mod: m.written.mod, name: m.written.name})}</div>`;
  return html;
}
function armExpModBody(){
  const m = armExpMod(), e = armExp();
  return {mod: m.target, choice: m.choice, name: m.name.trim().toLowerCase(), folder: m.folder.trim(),
          template: m.template, clone_from: m.template ? '' : m.clone_from.trim().toLowerCase(),
          unit: m.unit, new_type: m.new_type.trim(), new_name: m.new_name.trim(),
          bake_folder: e.done ? e.done.folder : e.folder, stem: e.stem};
}
function armExpModSet(k, v, live){
  const m = armExpMod();
  m[k] = v; m.plan = null; m.written = null; armSave();
  if(k === 'unit' || k === 'choice'){ m.folders=[]; armExpUnitFolders(); }
  if(!live) armExportPaint();
}
function armExpModTarget(v){ const m=armExpMod(); m.target=v; m.folders=[]; armSave(); armExpModLoad(); }
async function armExpModPlan(){
  const m = armExpMod(), e = armExp();
  e.busy = true; armExportPaint();
  try{ m.plan = await api.post('/api/armory/install/plan', armExpModBody()); e.err = ''; }
  catch(err){ m.plan = null; e.err = errText(err); }
  e.busy = false; armExportPaint();
}
async function armExpModApply(){
  const m = armExpMod(), e = armExp();
  if(!m.plan || !m.plan.ok) return;
  e.busy = true; armExportPaint();
  try{
    await api.post('/api/armory/install/apply', armExpModBody());
    m.written = {mod: m.target, name: m.choice === 'new' ? m.new_type : m.name};
    m.plan = null; e.err = ''; armExpRememberFolder(); armSave();
    toast(tt('armory.exp_written_mod', m.written));
  }catch(err){ e.err = errText(err); }
  e.busy = false; armExportPaint();
}

/* The unit card maker (95m) on this model, for the unit it went into. */
function armExpCards(){
  const m = armExpMod(), c = cg();
  const unit = m.written && m.choice !== 'skip' ? m.written.name : m.unit;
  if(unit) c.unit = unit;
  if(!c.name) c.name = (m.choice === 'new' ? m.new_type : m.name || armExp().stem || '').replace(/[^A-Za-z0-9_\-]/g, '_');
  closeModal();
  state.cardsSub = 'generate';
  setAppMode('cards');
}
