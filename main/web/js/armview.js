/* =========================================================================
   Armory Studio, the viewport - Phase 95g (armory.js draws, armobj.js picks)

   Behaves like Blender's: the object under the cursor lights up, a click
   selects and Shift adds, a left drag draws a box, the middle button orbits
   (Shift pans, Ctrl zooms), the wheel zooms, and the numpad turns the view.
   G, R and S move, turn and scale what is selected, X, Y or Z holds them to
   an axis, a number typed sets the amount, Enter or a click keeps it and Esc
   or the right button puts it back. H hides, Alt+H shows everything. Every
   one of these keys can be changed (config/armory/keys.json).

   Move, turn and scale are also sliders under the view. Several objects move
   about their middle, as Blender's median point does, and with **Head as
   one** the head parts (helmet, coif, face, hair, beard) go together
   whichever of them is picked. Face orientation paints fronts blue and backs
   red; the statistics overlay counts what is shown against a triangle budget
   measured from real units, not Armory Studio's 3,500.
   ========================================================================= */

/* The budget, measured on 2026-10-14 over every unit's soldier model at LOD0:
   the base game's 411 have a median of 5,432 triangles and a 95th percentile
   of 8,540; Heirs of Elendil's 380 have 5,780 and 14,417. */
const ARM_BUDGET = {typical: 5500, high: 8540, heavy: 14417};

const ARM_KEY_DEFAULTS = {
  grab: 'g', rotate: 'r', scale: 's', hide: 'h', unhideAll: 'alt+h', selectAll: 'a',
  deselectAll: 'alt+a', delete: 'x', frameSelected: 'numpad' + '.', frameAll: 'home',
  viewFront: 'numpad1', viewBack: 'ctrl+numpad1', viewRight: 'numpad3', viewLeft: 'ctrl+numpad3',
  viewTop: 'numpad7', viewBottom: 'ctrl+numpad7', ortho: 'numpad5', selectConnected: 'l',
  faceOrient: '', stats: '', detail: 'numpad/',
  // 99i and 99j
  undo: 'ctrl+z', redo: 'ctrl+shift+z', redoAlt: 'ctrl+y', tpose: '',
  // 100i, Blender's own key for a maximised area
  fullView: 'ctrl+space',
};
const armKeyLabel = k => ({grab: tt('armory.key_grab'), rotate: tt('armory.key_rotate'), scale: tt('armory.key_scale'),
  hide: tt('armory.key_hide'), unhideAll: tt('armory.key_unhide_all'), selectAll: tt('armory.key_select_all'),
  deselectAll: tt('armory.key_deselect_all'), delete: tt('armory.key_delete'), frameSelected: tt('armory.key_frame_selected'),
  frameAll: tt('armory.key_frame_all'), viewFront: tt('armory.key_view_front'), viewBack: tt('armory.key_view_back'),
  viewRight: tt('armory.key_view_right'), viewLeft: tt('armory.key_view_left'), viewTop: tt('armory.key_view_top'),
  viewBottom: tt('armory.key_view_bottom'), ortho: tt('armory.key_ortho'), selectConnected: tt('armory.select_connected'),
  faceOrient: tt('armory.face_orientation'), stats: tt('armory.statistics'), detail: tt('armory.detail'),
  undo: tt('armory.key_undo'), redo: tt('armory.key_redo'), redoAlt: tt('armory.key_redo_alt'), tpose: tt('armory.tpose'),
  fullView: tt('armory.full_view')})[k] || k;

function armKeys(){ return Object.assign({}, ARM_KEY_DEFAULTS, ARM.keys || {}); }
async function armLoadKeys(){
  if(ARM.keys) return;
  try{ ARM.keys = (await api.get('/api/armory/keys', 1)).keys || {}; }catch(e){ ARM.keys = {}; }
}
/* A key press as the keymap writes it: modifiers, then the key; the numpad
   is told apart from the row of numbers above the letters. */
function armKeyName(e){
  let k;
  if(e.code && e.code.startsWith('Numpad')){
    const rest = e.code.slice(6);
    k = 'numpad' + ({Decimal: '.', Divide: '/', Multiply: '*', Add: '+', Subtract: '-', Enter: 'enter'}[rest] || rest.toLowerCase());
  }else k = e.key === ' ' ? 'space' : (e.key || '').toLowerCase();
  if(['control', 'shift', 'alt', 'meta'].includes(k)) return '';
  // Shift is written for a named key, and for a letter with Ctrl or Alt
  // (Ctrl+Shift+Z is not Ctrl+Z); a lone Shift+letter stays the letter
  const shifted = e.shiftKey && !k.startsWith('numpad') && (k.length > 1 || ((e.ctrlKey || e.altKey) && /^[a-z]$/.test(k)));
  return (e.ctrlKey ? 'ctrl+' : '') + (e.altKey ? 'alt+' : '') + (shifted ? 'shift+' : '') + k;
}

/* Keys reach the workbench from the viewport, or from anywhere while the
   pointer is over it - never from a box being typed in. */
let armKeysWired = false;
function armWireKeys(){
  if(armKeysWired) return;
  armKeysWired = true;
  window.addEventListener('keydown', e => {
    if(state.mode !== 'armory' || !ARM.view) return;
    if(document.activeElement === ARM.view) return;          // the canvas's own listener has it
    const t = e.target, tag = t && t.tagName;
    if(tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return;
    // undo, redo and full view work anywhere in the workbench, the rest over the view
    const keys = armKeys(), name = armKeyName(e);
    // a dialog takes the keys, but Optimize's stays open on what it did: undo and redo reach past it
    if(overlay.classList.contains('open')){
      if(!document.querySelector('#modal .armopt') || !name || !['undo', 'redo', 'redoAlt'].some(k => keys[k] === name)) return;
      e.preventDefault();
      armUndo(keys.undo !== name);
      ARM.optReport = null;
      armOptPaint();
      return;
    }
    const anywhere = name && ['undo', 'redo', 'redoAlt', 'fullView'].some(k => keys[k] === name);
    if(!ARM.overView && !anywhere) return;
    armKey(e);
  });
}

function armKey(e){
  if(ARM.rebind){ return armRebindTake(e); }
  if(ARM.xform) return armXformKey(e);
  const name = armKeyName(e);
  if(!name) return;
  const keys = armKeys();
  const act = Object.keys(keys).find(k => keys[k] && keys[k] === name);
  if(!act) return;
  e.preventDefault();
  const sel = armSelected();
  switch(act){
    case 'grab': case 'rotate': case 'scale':
      if(sel.length && !ARM.detail) armXformStart(act);
      break;
    case 'hide': sel.forEach(o => { o.hidden = true; }); ARM.sel.clear(); armRepaint(); break;
    case 'unhideAll': armProj().objects.forEach(o => { o.hidden = false; }); armRepaint(); break;
    case 'selectAll': armVisibleObjects().forEach(o => ARM.sel.add(o.id)); armPaintObjects(); armPaintSliders(); armFrame(); break;
    case 'deselectAll': ARM.sel.clear(); armPaintObjects(); armPaintSliders(); armFrame(); break;
    case 'delete':
      if(sel.length && confirm(ttN('armory.delete_n_confirm', sel.length))){
        const p = armProj();
        p.objects = p.objects.filter(o => !ARM.sel.has(o.id));
        ARM.sel.clear(); armRepaint();
      }
      break;
    case 'frameSelected': armFrameObjects(sel.length ? sel : armVisibleObjects()); break;
    case 'frameAll': armFrameAll(); break;
    case 'viewFront': armView(0, 0); break;
    case 'viewBack': armView(Math.PI, 0); break;
    case 'viewRight': armView(Math.PI / 2, 0); break;
    case 'viewLeft': armView(-Math.PI / 2, 0); break;
    case 'viewTop': armView(ARM.cam.yaw, 1.5607); break;
    case 'viewBottom': armView(ARM.cam.yaw, -1.5607); break;
    case 'ortho': ARM.cam.ortho = !ARM.cam.ortho; armPaintSliders(); armFrame(); break;
    case 'selectConnected': if(ARM.detail) armDetailConnected(); break;
    case 'faceOrient': armToggle('faceOrient'); break;
    case 'stats': armToggle('stats'); break;
    case 'detail': ARM.detail ? armDetailClose() : armDetailOpen(); break;
    case 'undo': armUndo(false); break;
    case 'redo': case 'redoAlt': armUndo(true); break;
    case 'tpose': armTpose(); break;
    case 'fullView': armFullView(); break;
  }
}
/* 100i: the viewport alone in the window, every panel and bar hidden; the
   same key, the corner button or Esc brings them back as they were */
function armFullView(on){
  const b = document.body.classList;
  on = on == null ? !b.contains('armfull') : on;
  b.toggle('armfull', on);
  if(on && !ARM.fullEsc){
    ARM.fullEsc = e => {
      if(e.key === 'Escape' && !ARM.xform && document.body.classList.contains('armfull')){ e.stopPropagation(); armFullView(false); }
    };
    document.addEventListener('keydown', ARM.fullEsc, true);
  }
  armFrame();
}
function armView(yaw, pitch){ ARM.cam.yaw = yaw; ARM.cam.pitch = pitch; armFrame(); }
function armFrameObjects(objs){
  const b = armBounds(objs);
  if(!b) return;
  const [lo, hi] = b;
  ARM.cam.target = [-(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
  ARM.cam.dist = Math.max(0.1, Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) * 1.3);
  armFrame();
}
function armToggle(what){
  ARM[what] = !ARM[what];
  armPaintSliders(); armFrame();
}

/* --- rotation as a 3x3, row-major, Z * Y * X: the order armRot and
       armory.rotation() use --------------------------------------------------- */

function m3(rx, ry, rz){
  const r = armRot(rx, ry, rz);       // column-major 4x4
  return [[r[0], r[4], r[8]], [r[1], r[5], r[9]], [r[2], r[6], r[10]]];
}
const m3mul = (a, b) => a.map((row, i) => [0, 1, 2].map(j => row[0] * b[0][j] + row[1] * b[1][j] + row[2] * b[2][j]));
const m3vec = (m, v) => m.map(row => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]);
function m3axis(axis, deg){
  const r = [0, 0, 0]; r[axis] = deg;
  return m3(r[0], r[1], r[2]);
}
/* Degrees back out of a Z * Y * X matrix. */
function m3euler(m){
  const d = 180 / Math.PI;
  const sy = Math.max(-1, Math.min(1, -m[2][0]));
  const y = Math.asin(sy);
  if(Math.abs(sy) < 0.99999)
    return [Math.atan2(m[2][1], m[2][2]) * d, y * d, Math.atan2(m[1][0], m[0][0]) * d];
  return [Math.atan2(-m[1][2], m[1][1]) * d, y * d, 0];
}
const armRound = (v, k) => Math.round(v * k) / k;

/* --- several objects as one -------------------------------------------------- */

const ARM_HEAD = /^(head|helm|helmet|coif|face|hair|beard|moustache|mustache)/i;
/* What a transform moves: the selection, and with Head as one every head
   part when any is picked. */
function armXformSet(){
  const sel = armSelected();
  if(ARM.headLink && sel.some(o => ARM_HEAD.test(o.name)))
    for(const o of armVisibleObjects()) if(ARM_HEAD.test(o.name) && !sel.includes(o)) sel.push(o);
  return sel;
}
/* An object's origin in the game's space: its pivot, moved. */
function armOrigin(o, t){ const pv = armPivot(o); return [pv[0] + t[0], pv[1] + t[1], pv[2] + t[2]]; }
function armSnapshot(objs){
  return objs.map(o => ({o, t: o.t.slice(), r: o.r.slice(), s: o.s.slice()}));
}
function armMedian(snap){
  const c = [0, 0, 0];
  for(const x of snap){ const p = armOrigin(x.o, x.t); for(let k = 0; k < 3; k++) c[k] += p[k] / snap.length; }
  return c;
}
/* Apply one move, turn or scale to a snapshot, about `c` in the game's space. */
function armGroupApply(snap, c, kind, v){
  for(const x of snap){
    const o = x.o, pv = armPivot(o), p0 = armOrigin(o, x.t);
    if(kind === 'grab'){
      o.t = [x.t[0] + v[0], x.t[1] + v[1], x.t[2] + v[2]];
    }else if(kind === 'rotate'){
      const R = m3mul(v, m3(x.r[0], x.r[1], x.r[2]));
      o.r = m3euler(R).map(a => armRound(a, 1000));
      const q = m3vec(v, [p0[0] - c[0], p0[1] - c[1], p0[2] - c[2]]);
      o.t = [q[0] + c[0] - pv[0], q[1] + c[1] - pv[1], q[2] + c[2] - pv[2]];
    }else{
      o.s = [x.s[0] * v[0], x.s[1] * v[1], x.s[2] * v[2]];
      o.t = [0, 1, 2].map(k => c[k] + v[k] * (p0[k] - c[k]) - pv[k]);
    }
    o.t = o.t.map(a => armRound(a, 100000));
  }
}

/* --- G, R and S ---------------------------------------------------------------- */

/* The camera's right and up in the GAME's space (the page mirrors x), and
   the world length one pixel of the view is at the target. */
function armCamAxes(){
  const view = ARM.view;
  const cam = armCamera(view.width / view.height);
  const t = ARM.cam.target, e = cam.eye;
  const f = v3Norm([t[0] - e[0], t[1] - e[1], t[2] - e[2]]);
  const right = v3Norm(v3Cross(f, [0, 1, 0]));
  const up = v3Cross(right, f);
  const cssH = view.getBoundingClientRect().height || 1;
  const k = ARM.cam.ortho ? 2 * ARM.cam.dist * 0.42 / cssH : 2 * ARM.cam.dist * Math.tan(0.375) / cssH;
  const g = v => [-v[0], v[1], v[2]];
  return {right: g(right), up: g(up), fwd: g(f), k, cam};
}
/* Where a point of the game's space lands on the view, in CSS pixels. */
function armToScreen(p){
  const view = ARM.view;
  const cam = armCamera(view.width / view.height);
  const m = armMul(cam.proj, cam.view);
  const x = -p[0], y = p[1], z = p[2];
  const w = m[3] * x + m[7] * y + m[11] * z + m[15];
  const r = view.getBoundingClientRect();
  return [((m[0] * x + m[4] * y + m[8] * z + m[12]) / w * 0.5 + 0.5) * r.width + r.left,
          (1 - ((m[1] * x + m[5] * y + m[9] * z + m[13]) / w * 0.5 + 0.5)) * r.height + r.top];
}

function armXformStart(kind){
  const objs = armXformSet();
  if(!objs.length) return;
  const snap = armSnapshot(objs);
  const c = armMedian(snap);
  const ax = armCamAxes();
  // R with no axis turns about whichever of x, y and z faces the viewer most
  const f = ax.fwd.map(Math.abs);
  const viewAxis = f.indexOf(Math.max(...f));
  ARM.xform = {kind, snap, c, axis: null, viewAxis, typed: '', mouse: ARM.lastMouse || null,
               start: ARM.lastMouse || null, centre: armToScreen(c), value: null};
  armXformUpdate();
}
function armPointerDown(e){
  if(!ARM.xform) return false;
  e.preventDefault();
  if(e.button === 2) armXformEnd(false); else armXformEnd(true);
  return true;
}
function armXformMove(e){
  ARM.lastMouse = [e.clientX, e.clientY];
  ARM.overView = true;
  if(!ARM.xform) return false;
  if(!ARM.xform.start) ARM.xform.start = [e.clientX, e.clientY];
  ARM.xform.mouse = [e.clientX, e.clientY];
  armXformUpdate();
  return true;
}
function armXformKey(e){
  const x = ARM.xform, k = e.key;
  e.preventDefault();
  if(k === 'Escape') return armXformEnd(false);
  if(k === 'Enter') return armXformEnd(true);
  const ax = {x: 0, y: 1, z: 2}[k.toLowerCase()];
  if(ax !== undefined){ x.axis = x.axis === ax ? null : ax; return armXformUpdate(); }
  if(/^[0-9.]$/.test(k) || (k === '-' && !x.typed)){ x.typed += k; return armXformUpdate(); }
  if(k === 'Backspace'){ x.typed = x.typed.slice(0, -1); return armXformUpdate(); }
}
function armXformUpdate(){
  const x = ARM.xform;
  if(!x) return;
  const typed = x.typed !== '' && x.typed !== '-' && !isNaN(+x.typed) ? +x.typed : null;
  let v;
  if(x.kind === 'grab'){
    let d = [0, 0, 0];
    if(typed != null){
      d[x.axis == null ? 0 : x.axis] = typed;
    }else if(x.start && x.mouse){
      const ax = armCamAxes();
      const dx = (x.mouse[0] - x.start[0]) * ax.k, dy = -(x.mouse[1] - x.start[1]) * ax.k;
      d = [0, 1, 2].map(i => ax.right[i] * dx + ax.up[i] * dy);
      if(x.axis != null) d = d.map((a, i) => i === x.axis ? a : 0);
    }
    v = d;
    x.value = d.map(a => a.toFixed(3)).join(', ');
  }else if(x.kind === 'rotate'){
    let deg = 0;
    if(typed != null) deg = typed;
    else if(x.start && x.mouse){
      const a0 = Math.atan2(x.start[1] - x.centre[1], x.start[0] - x.centre[0]);
      const a1 = Math.atan2(x.mouse[1] - x.centre[1], x.mouse[0] - x.centre[0]);
      deg = (a1 - a0) * 180 / Math.PI;
    }
    const axis = x.axis == null ? x.viewAxis : x.axis;
    // the page mirrors x: a turn the mouse makes one way on screen is the
    // other way in the game's space about y and z; a typed angle is the
    // game's own
    v = m3axis(axis, typed != null || axis === 0 ? deg : -deg);
    x.value = `${'XYZ'[axis]} ${deg.toFixed(1)}°`;
  }else{
    let f = 1;
    if(typed != null) f = typed;
    else if(x.start && x.mouse){
      const d0 = Math.hypot(x.start[0] - x.centre[0], x.start[1] - x.centre[1]) || 1;
      f = Math.hypot(x.mouse[0] - x.centre[0], x.mouse[1] - x.centre[1]) / d0;
    }
    v = [0, 1, 2].map(i => x.axis == null || i === x.axis ? f : 1);
    x.value = f.toFixed(3);
  }
  for(const s of x.snap){ s.o.t = s.t.slice(); s.o.r = s.r.slice(); s.o.s = s.s.slice(); }
  armGroupApply(x.snap, x.c, x.kind, v);
  armFrame();
}
function armXformEnd(keep){
  const x = ARM.xform;
  ARM.xform = null;
  if(!x) return;
  if(!keep) for(const s of x.snap){ s.o.t = s.t; s.o.r = s.r; s.o.s = s.s; }
  armSave(); armPaintSliders(); armPaintBar(); armFrame();
}

/* --- the sliders under the view, and the toggles -------------------------------- */

function armPaintSliders(){
  const el = document.getElementById('armFoot');
  if(!el) return;
  const sel = armSelected();
  const o = sel[0];
  const row = (kind, label, vals, step) => `<div class="armslrow"><b>${label}</b>${[0, 1, 2].map(i =>
    `<label>${'XYZ'[i]}<input type="number" step="${step}" value="${o ? armRound(vals[i], 1000) : ''}"${o ? '' : ' disabled'}
      onchange="armSlider('${kind}', ${i}, this.value)" onwheel="armSliderWheel(event, '${kind}', ${i}, ${step})"></label>`).join('')}</div>`;
  el.innerHTML = `<div class="armslwrap"><div class="armsliders">
      ${row('t', tt('armory.move'), o ? o.t : [], 0.01)}
      ${row('r', tt('armory.rotate'), o ? o.r : [], 1)}
      ${row('s', tt('armory.scale'), o ? o.s : [], 0.01)}
      <div class="armslrow"><label class="armcheck"><input type="checkbox"${ARM.uniform !== false ? ' checked' : ''}
        onchange="ARM.uniform=this.checked"> ${tt('armory.uniform_scale')}</label>
        <span class="count">${o ? ttN('armory.n_selected', sel.length) : tt('armory.nothing_selected')}</span></div>
    </div>
    <div class="armslside">
      <label class="armcheck"><input type="checkbox"${ARM.stats ? ' checked' : ''} onchange="armToggle('stats')"> ${tt('armory.statistics')}</label>
      <span id="armSelTools">${typeof armSelToolsHtml === 'function' ? armSelToolsHtml() : ''}</span>
    </div></div>
    <div class="armtoggles">
      <label class="armcheck"><input type="checkbox"${ARM.faceOrient ? ' checked' : ''} onchange="armToggle('faceOrient')"> ${tt('armory.face_orientation')}</label>
      <label class="armcheck" title="${esc(tt('armory.head_as_one_title'))}"><input type="checkbox"${ARM.headLink ? ' checked' : ''} onchange="armToggle('headLink')"> ${tt('armory.head_as_one')}</label>
      <button class="mini${ARM.cam.ortho ? ' on' : ''}" onclick="armToggleOrtho()">${tt('armory.ortho')}</button>
      <button class="mini" onclick="armShortcutsOpen()">${tt('armory.shortcuts')}</button>
      <span class="count armhint">${tt('armory.view_hint')}</span>
    </div>
    <div class="armanimhost" id="armAnimHost"></div>`;
  if(typeof armAnimPaint === 'function') armAnimPaint();
}
function armToggleOrtho(){ ARM.cam.ortho = !ARM.cam.ortho; armPaintSliders(); armFrame(); }

/* A slider sets the first selected object's value; the others move by as
   much, each about its own pivot, or as one about their middle when there
   are several (or the head goes together). */
function armSlider(kind, axis, value){
  const v = +value;
  if(!isFinite(v)) return;
  const objs = armXformSet();
  const o = armSelected()[0];
  if(!o || !objs.length) return;
  const snap = armSnapshot(objs);
  const c = armMedian(snap);
  if(kind === 't'){
    const d = [0, 0, 0]; d[axis] = v - o.t[axis];
    armGroupApply(snap, c, 'grab', d);
  }else if(kind === 'r'){
    if(objs.length === 1){ o.r[axis] = v; }
    else armGroupApply(snap, c, 'rotate', m3axis(axis, v - o.r[axis]));
  }else{
    const old = o.s[axis] || 1;
    const f = ARM.uniform !== false ? [v / old, v / old, v / old] : [0, 1, 2].map(i => i === axis ? v / old : 1);
    if(objs.length === 1) o.s = o.s.map((x, i) => x * f[i]);
    else armGroupApply(snap, c, 'scale', f);
  }
  if(!ARM.wheeling) armSave();
  armPaintSliders(); armPaintBar(); armFrame();
}

/* 100g: the wheel over a number steps it, Shift a tenth of a step, Ctrl ten;
   the run of turns is saved once when it stops, so it is one Undo step */
function armSliderWheel(ev, kind, axis, step){
  if(!armSelected().length) return;
  ev.preventDefault();
  const k = ev.shiftKey ? 0.1 : ev.ctrlKey ? 10 : 1;
  const cur = +ev.target.value || 0;
  const next = Math.round((cur + (ev.deltaY < 0 ? 1 : -1) * step * k) * 10000) / 10000;
  if(kind === 's' && next <= 0) return;
  ARM.wheeling = true;
  armSlider(kind, axis, next);
  ARM.wheeling = false;
  clearTimeout(ARM.wheelTimer);
  ARM.wheelTimer = setTimeout(armSave, 400);
}

/* --- the statistics overlay ------------------------------------------------------ */

const ARM_VCOUNT = new WeakMap();
function armObjVerts(o){
  const sig = JSON.stringify(o.src || []);
  const hit = ARM_VCOUNT.get(o);
  if(hit && hit.sig === sig) return hit.n;
  let n = 0, ready = true;
  for(const pc of o.src || []){
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo){ ready = false; continue; }
    const set = new Set();
    armPieceEach(live, pc, v => set.add(v));
    n += set.size;
  }
  if(ready) ARM_VCOUNT.set(o, {sig, n});
  return n;
}
function armOverlay95g(ctx, w, h){
  const x = ARM.xform;
  const dpr = w / (ARM.view.getBoundingClientRect().width || w);
  ctx.save();
  ctx.font = `${Math.round(12 * dpr)}px "Segoe UI", system-ui, sans-serif`;
  ctx.textBaseline = 'top';
  if(x){
    const verb = {grab: tt('armory.key_grab'), rotate: tt('armory.key_rotate'), scale: tt('armory.key_scale')}[x.kind];
    const axis = x.axis == null ? '' : ` · ${'XYZ'[x.axis]}`;
    const line = `${verb}${axis}: ${x.typed ? x.typed + ' ✎' : x.value}  ${tt('armory.xform_hint')}`;
    ctx.fillStyle = 'rgba(15,17,21,.82)';
    ctx.fillRect(8 * dpr, h - 30 * dpr, ctx.measureText(line).width + 16 * dpr, 22 * dpr);
    ctx.fillStyle = '#f3c26b';
    ctx.fillText(line, 16 * dpr, h - 26 * dpr);
  }
  if(ARM.stats){
    const objs = armVisibleObjects();
    const tris = objs.reduce((s, o) => s + armObjTris(o), 0);
    const verts = objs.reduce((s, o) => s + armObjVerts(o), 0);
    const selT = armSelected().reduce((s, o) => s + armObjTris(o), 0);
    const level = tris <= ARM_BUDGET.high ? 'ok' : tris <= ARM_BUDGET.heavy ? 'high' : 'heavy';
    const lines = [
      tt('armory.stat_objects', {n: objs.length.toLocaleString()}),
      tt('armory.stat_vertices', {n: verts.toLocaleString()}),
      tt('armory.stat_triangles', {n: tris.toLocaleString()}),
      tt('armory.stat_selected', {n: selT.toLocaleString()}),
    ];
    const badge = level === 'ok' ? tt('armory.budget_ok', {high: ARM_BUDGET.high.toLocaleString()})
      : level === 'high' ? tt('armory.budget_high', {high: ARM_BUDGET.high.toLocaleString()})
      : tt('armory.budget_heavy', {heavy: ARM_BUDGET.heavy.toLocaleString()});
    const lh = 16 * dpr;
    const width = Math.max(...[...lines, badge].map(l => ctx.measureText(l).width)) + 16 * dpr;
    ctx.fillStyle = 'rgba(15,17,21,.78)';
    ctx.fillRect(8 * dpr, 8 * dpr, width, lh * (lines.length + 1) + 10 * dpr);
    ctx.fillStyle = '#e6e9ee';
    lines.forEach((l, i) => ctx.fillText(l, 16 * dpr, 13 * dpr + i * lh));
    ctx.fillStyle = level === 'ok' ? '#5cc98a' : level === 'high' ? '#e0b341' : '#e06c6c';
    ctx.fillText(badge, 16 * dpr, 13 * dpr + lines.length * lh);
  }
  ctx.restore();
  armGizmoDraw(ctx, w, h);
}

/* --- the view gizmo (99k) --------------------------------------------------------

   Blender's, at the top right: the three axes as balls turning with the view,
   X red, Y green, Z blue, the positive ends filled and lettered, the negative
   ends hollow. They are the game's axes, the ones the sliders and G, R and S
   with X, Y or Z use: Y is up. A click on a ball looks down that axis at the
   model, a drag on the gizmo orbits. */
const ARM_GIZMO = {r: 46, ball: 9, pad: 14};
const ARM_GIZMO_AXES = [
  {axis: 0, sign: 1, label: 'X', col: '#e8555f'}, {axis: 1, sign: 1, label: 'Y', col: '#7cc843'}, {axis: 2, sign: 1, label: 'Z', col: '#4f8fe8'},
  {axis: 0, sign: -1, label: '', col: '#e8555f'}, {axis: 1, sign: -1, label: '', col: '#7cc843'}, {axis: 2, sign: -1, label: '', col: '#4f8fe8'},
];
/* The gizmo's centre and the balls, in CSS pixels of the view. */
function armGizmoLayout(){
  const view = ARM.view;
  if(!view) return null;
  const r = view.getBoundingClientRect();
  const g = ARM_GIZMO, top = ARM.detail ? 44 : 0;
  const c = [r.width - g.r - g.pad, g.r + g.pad + top];
  const cam = armCamera(view.width / view.height), m = cam.view;
  const balls = ARM_GIZMO_AXES.map(a => {
    // a game axis in the page's space (x mirrored), turned by the view
    const d = [0, 0, 0]; d[a.axis] = a.sign;
    const q = [-d[0], d[1], d[2]];
    const vx = m[0] * q[0] + m[4] * q[1] + m[8] * q[2];
    const vy = m[1] * q[0] + m[5] * q[1] + m[9] * q[2];
    const vz = m[2] * q[0] + m[6] * q[1] + m[10] * q[2];
    return Object.assign({x: c[0] + vx * (g.r - g.ball), y: c[1] - vy * (g.r - g.ball), z: vz}, a);
  });
  return {c, balls, rect: r};
}
function armGizmoDraw(ctx, w){
  const L = armGizmoLayout();
  if(!L) return;
  const k = w / (L.rect.width || w), g = ARM_GIZMO;
  ctx.save();
  ctx.scale(k, k);
  if(ARM.gizmoHover){
    ctx.fillStyle = 'rgba(255,255,255,.08)';
    ctx.beginPath(); ctx.arc(L.c[0], L.c[1], g.r + 2, 0, Math.PI * 2); ctx.fill();
  }
  ctx.font = `bold 11px "Segoe UI", system-ui, sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  // the far side first, so a near ball covers a far one
  for(const b of L.balls.slice().sort((a, c) => a.z - c.z)){
    const hot = ARM.gizmoHover && ARM.gizmoHover.axis === b.axis && ARM.gizmoHover.sign === b.sign;
    if(b.sign > 0){
      ctx.strokeStyle = b.col; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(L.c[0], L.c[1]); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(b.x, b.y, g.ball, 0, Math.PI * 2);
    if(b.sign > 0){
      ctx.fillStyle = hot ? '#fff' : b.col; ctx.fill();
      ctx.fillStyle = '#15181d'; ctx.fillText(b.label, b.x, b.y + 0.5);
    }else{
      ctx.fillStyle = hot ? 'rgba(255,255,255,.55)' : 'rgba(21,24,29,.65)'; ctx.fill();
      ctx.strokeStyle = b.col; ctx.lineWidth = 1.6; ctx.stroke();
    }
  }
  ctx.restore();
}
/* What is under the pointer: a ball, the gizmo's disk, or nothing. */
function armGizmoHit(e){
  const L = armGizmoLayout();
  if(!L) return null;
  const x = e.clientX - L.rect.left, y = e.clientY - L.rect.top;
  const hits = L.balls.filter(b => Math.hypot(b.x - x, b.y - y) <= ARM_GIZMO.ball + 1).sort((a, c) => c.z - a.z);
  if(hits.length) return hits[0];
  return Math.hypot(L.c[0] - x, L.c[1] - y) <= ARM_GIZMO.r + 2 ? {disk: true} : null;
}
function armGizmoHover(e){
  const h = e ? armGizmoHit(e) : null;
  const was = ARM.gizmoHover;
  ARM.gizmoHover = h;
  if(!!was !== !!h || (h && was && (h.axis !== was.axis || h.sign !== was.sign))) armFrame();
  return !!h;
}
/* Looks down an axis: the eye on that axis's side of the model. */
function armGizmoClick(b){
  if(!b || b.disk) return;
  if(b.axis === 1) return armView(ARM.cam.yaw, b.sign > 0 ? 1.5607 : -1.5607);
  // the game's +x is the page's -x (ARM_MIRROR); the eye sits at yaw where
  // sin(yaw) is its x and cos(yaw) its z
  if(b.axis === 0) return armView(b.sign > 0 ? -Math.PI / 2 : Math.PI / 2, 0);
  armView(b.sign > 0 ? 0 : Math.PI, 0);
}

/* --- shortcuts, every one editable ---------------------------------------------- */

function armShortcutsOpen(){
  const keys = armKeys();
  document.getElementById('modal').className = 'modal';
  modal.innerHTML = `<div class="armimp">
    <h3>${tt('armory.shortcuts')}</h3>
    <div class="count">${tt('armory.shortcuts_intro')}</div>
    <div class="armkeys">${Object.keys(ARM_KEY_DEFAULTS).map(k => `<div class="armkeyrow">
      <span>${esc(armKeyLabel(k))}</span>
      <button class="mini${ARM.rebind === k ? ' on' : ''}" onclick="armRebind('${k}')">${ARM.rebind === k ? tt('armory.press_a_key') : esc(keys[k] || tt('armory.no_key'))}</button>
      <button class="mini" onclick="armUnbind('${k}')" title="${esc(tt('armory.no_key'))}">✕</button></div>`).join('')}</div>
    <div class="armimpfoot"><button onclick="armKeysReset()">${tt('armory.reset_keys')}</button><span style="flex:1"></span>
      <button class="primary" onclick="ARM.rebind=null;closeModal()">${tt('common.close')}</button></div></div>`;
  overlay.classList.add('open');
}
function armRebind(k){
  ARM.rebind = k;
  armShortcutsOpen();
  // the dialog takes the next key itself, while it is open
  const take = e => { if(!ARM.rebind){ window.removeEventListener('keydown', take, true); return; }
    e.preventDefault(); e.stopPropagation(); armRebindTake(e);
    window.removeEventListener('keydown', take, true); };
  window.addEventListener('keydown', take, true);
}
function armRebindTake(e){
  const name = armKeyName(e);
  if(!name) return;
  const k = ARM.rebind;
  ARM.rebind = null;
  if(name !== 'escape'){
    ARM.keys = ARM.keys || {};
    // a key belongs to one action: whatever held it lets it go
    const keys = armKeys();
    for(const other of Object.keys(keys)) if(other !== k && keys[other] === name) ARM.keys[other] = '';
    ARM.keys[k] = name;
    api.post('/api/armory/keys', {keys: ARM.keys}).catch(() => {});
  }
  armShortcutsOpen();
}
function armUnbind(k){
  ARM.keys = ARM.keys || {};
  ARM.keys[k] = '';
  api.post('/api/armory/keys', {keys: ARM.keys}).catch(() => {});
  armShortcutsOpen();
}
function armKeysReset(){
  ARM.keys = {};
  api.post('/api/armory/keys', {keys: {}}).catch(() => {});
  armShortcutsOpen();
}

/* --- bone names, on pulling a part in -------------------------------------------- */

/* The skeleton in use: the one 95h plays, else the base model's, else the
   first model entry loaded. */
function armSkeletonAsset(){
  const p = armProj();
  const key = (p.anim && p.anim.asset) || p.base || (p.assets.find(a => a.kind === 'entry') ? armAssetKey(p.assets.find(a => a.kind === 'entry')) : null);
  return key ? ARM.assets.get(key) : null;
}
/* An object from a skeleton that spells its bones another way (the archer
   bone_rhand against the melee bone_Rhand) takes the spelling of the one in
   use: the export and the animations match bones without regard to case, so
   the renaming is said here and done there. */
function armBoneCheck(key, groups){
  const sk = armSkeletonAsset(), live = ARM.assets.get(key);
  if(!sk || !sk.view || !live || !live.view || !live.geo || sk === live) return;
  const target = new Map((sk.view.bones || []).map(b => [b.toLowerCase(), b]));
  // only the bones the pulled parts are weighted to
  const geo = live.geo, used = new Set();
  if(geo.weights && geo.joints)
    for(const g of groups || live.view.objects.map(o => o.index))
      armPieceEach(live, {group: g}, v => {
        for(let s = 0; s < 2; s++) if(geo.weights[v*2+s] > 0) used.add((geo.bones || [])[geo.joints[v*2+s]]);
      });
  let renamed = 0;
  const missing = [];
  for(const b of used){
    const t = target.get(b.toLowerCase());
    if(t === undefined){ if(b) missing.push(b); }
    else if(t !== b) renamed++;
  }
  const said = [];
  if(renamed) said.push(ttN('armory.bones_renamed', renamed));
  if(missing.length) said.push(tt('armory.bones_missing', {names: missing.slice(0, 4).join(', ')}));
  if(said.length) toast(said.join(' '), 6000);
}

/* --- hover tracking for the keys ------------------------------------------------- */

function armViewWire(){
  armWireKeys();
  armLoadKeys();
  if(!ARM.view || ARM.view.dataset.wired95g) return;
  ARM.view.dataset.wired95g = '1';
  ARM.view.addEventListener('pointerenter', () => { ARM.overView = true; });
  ARM.view.addEventListener('pointerleave', () => { ARM.overView = false; });
}
