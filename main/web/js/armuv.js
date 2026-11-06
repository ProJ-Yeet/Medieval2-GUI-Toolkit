/* Armory Studio - the UV editor (100m).

   One object's UVs over its sheet, as Blender's UV editor: vertices or
   whole islands picked (Shift adds, a drag draws a box), dragged, or moved,
   turned and scaled with G, R and S (X or Y holds an axis; a click or Enter
   keeps, Esc or the right button puts back), snapped to the sheet's texels.
   The wheel zooms and the middle button pans. The sheet shown can be any
   loaded one, and worn; the M2 view lays an entry's main and attachment
   sheets side by side as the game does.

   An edit lives on the object's piece as ``pc.uv`` - {asset vertex: [u, v]} -
   copied before it is changed, since a piece can be shared after a merge or
   a split. armory.js draws it, armanim.js poses it, and armory.object_mesh
   carries it into the bake and the export. */

ARM_UV_BUF = typeof ARM_UV_BUF !== 'undefined' ? ARM_UV_BUF : new WeakMap();

// the UV buffer of a piece with moved UVs: the asset's, with the moves on it
function armUvBuffer(live, pc){
  const sig = JSON.stringify(pc.uv);
  const hit = ARM_UV_BUF.get(pc);
  if(hit && hit.sig === sig && hit.live === live) return hit.buf;
  const gl = armGl();
  const uv = new Float32Array(live.geo.uvs || new Float32Array(live.geo.positions.length / 3 * 2));
  for(const k in pc.uv){ const v = +k; uv[v * 2] = pc.uv[k][0]; uv[v * 2 + 1] = pc.uv[k][1]; }
  if(hit && hit.buf) gl.deleteBuffer(hit.buf);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, uv, gl.STATIC_DRAW);
  ARM_UV_BUF.set(pc, {sig, live, buf});
  return buf;
}

/* --- opening, and what is being edited ---------------------------------------------- */

function armUvOpen(){
  const o = armSelected()[0];
  if(!o || armSelected().length !== 1 || !(o.src || []).length){ toast(tt('armory.uv_pick_one')); return; }
  ARM.uvEd = {id: o.id, mode: 'vertex', view: 'sheet', show: '', snap: true, sel: new Set(),
              z: 1, ox: 0, oy: 0, drag: null, xf: null};
  armUvBuild();
  armUvPanel();
}
function armUvClose(){
  if(ARM.uvEd && ARM.uvEd.xf) armUvXfEnd(true);
  const el = document.getElementById('armUvPanel');
  if(el) el.remove();
  ARM.uvEd = null;
}
// the object's UV vertices, one per piece and asset vertex, and its triangles
function armUvBuild(){
  const e = ARM.uvEd, o = armObj(e.id);
  e.pts = []; e.tris = [];
  const at = new Map();
  (o.src || []).forEach((pc, pi) => {
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo) return;
    const U = live.geo.uvs, flat = [];
    armPieceEach(live, pc, v => flat.push(v));
    for(const v of flat){
      const k = pi + ':' + v;
      if(at.has(k)) continue;
      const mv = pc.uv && pc.uv[v];
      at.set(k, e.pts.length);
      e.pts.push({pi, v, u: mv ? mv[0] : U ? U[v * 2] : 0, w: mv ? mv[1] : U ? U[v * 2 + 1] : 0});
    }
    for(let t = 0; t + 2 < flat.length; t += 3)
      e.tris.push([at.get(pi + ':' + flat[t]), at.get(pi + ':' + flat[t + 1]), at.get(pi + ':' + flat[t + 2])]);
  });
  // islands: triangles that share a vertex (the asset splits its vertices
  // along every seam, so a shared vertex is a shared UV)
  const up = e.pts.map((_, i) => i);
  const find = i => { while(up[i] !== i){ up[i] = up[up[i]]; i = up[i]; } return i; };
  for(const [a, b, c] of e.tris){ up[find(b)] = find(a); up[find(c)] = find(a); }
  e.island = e.pts.map((_, i) => find(i));
}

/* --- the sheet behind, and where a UV lands on the canvas ----------------------------- */

function armUvSheet(){
  const e = ARM.uvEd, o = armObj(e.id);
  const pc = o.src[0], live = ARM.assets.get(pc.asset) || {};
  const atlas = !o.sheet && !live.objTex && !!live.img && (live.uScale || 0.5) === 0.5;
  // the tile the object is mostly on: 0 the main sheet, 1 the attachment
  const mean = e.pts.length ? e.pts.reduce((s, p) => s + p.u, 0) / e.pts.length : 0;
  const tile = Math.floor(mean);
  if(e.show){
    const hit = ARM.uvShowImg;
    return {img: hit && hit.src === e.show ? hit.img : null, sx: 0, sw: 0, tile0: tile, span: 1, texels: 0};
  }
  let img = null;
  if(o.sheet){ const h = ARM.sheetCache.get(o.sheet); img = h && h.img; if(!h) armSheetTex(o.sheet); }
  else if(live.objImg) img = live.objImg[pc.group];
  else img = live.img;
  if(atlas && e.view === 'm2') return {img, sx: 0, sw: img ? img.width : 0, tile0: 0, span: 2, atlas: true};
  if(atlas){
    const half = img ? img.width / 2 : 0, t = ((tile % 2) + 2) % 2;
    return {img, sx: t * half, sw: half, tile0: tile, span: 1, atlas: true};
  }
  return {img, sx: 0, sw: img ? img.width : 0, tile0: tile, span: 1};
}
function armUvGeom(c){
  const e = ARM.uvEd, sh = armUvSheet();
  const iw = sh.sw || (sh.img ? sh.img.width : 1), ih = sh.img ? sh.img.height : 1;
  // fitted into the canvas, then the user's zoom and pan
  const fit = Math.min(c.width / (iw || 1), c.height / (ih || 1)) * 0.92;
  const W = (iw || 1) * fit * e.z, H = (ih || 1) * fit * e.z;
  const x0 = (c.width - W) / 2 + e.ox, y0 = (c.height - H) / 2 + e.oy;
  return {sh, W, H, x0, y0, iw, ih,
          to: p => [x0 + (p.u - sh.tile0) / sh.span * W, y0 + p.w * H],
          from: (X, Y) => [(X - x0) / W * sh.span + sh.tile0, (Y - y0) / H]};
}

/* --- the panel ------------------------------------------------------------------------- */

function armUvPanel(){
  const host = document.getElementById('armView');
  if(!host || !ARM.uvEd) return;
  let el = document.getElementById('armUvPanel');
  if(!el){
    el = Object.assign(document.createElement('div'), {id: 'armUvPanel', className: 'armuvpanel'});
    // the viewport under the panel never sees its mouse or its wheel
    ['mousedown', 'wheel', 'click', 'dblclick', 'pointerdown'].forEach(t => el.addEventListener(t, ev => ev.stopPropagation()));
    host.appendChild(el);
  }
  const e = ARM.uvEd, o = armObj(e.id);
  const live = ARM.assets.get(o.src[0].asset) || {};
  const entry = !o.sheet && !live.objTex;
  const rows = typeof armTexSheets === 'function' ? armTexSheets() : [];
  el.innerHTML = `<div class="armuvhead">
      <b>${tt('armory.uv_edit')}</b> <span class="count">${esc(o.mesh)}</span><span style="flex:1"></span>
      <button class="mini" onclick="armUvClose()">✕</button></div>
    <div class="armuvbar">
      <button class="mini${e.mode === 'vertex' ? ' on' : ''}" onclick="armUvSet('mode','vertex')">${tt('armory.uv_vertex')}</button>
      <button class="mini${e.mode === 'island' ? ' on' : ''}" onclick="armUvSet('mode','island')">${tt('armory.uv_island')}</button>
      ${entry ? `<button class="mini${e.view === 'sheet' ? ' on' : ''}" onclick="armUvSet('view','sheet')" title="${esc(tt('armory.uv_sheet_title'))}">${tt('armory.uv_sheet')}</button>
        <button class="mini${e.view === 'm2' ? ' on' : ''}" onclick="armUvSet('view','m2')" title="${esc(tt('armory.uv_m2_title'))}">${tt('armory.uv_m2')}</button>` : ''}
      <label class="armcheck"><input type="checkbox"${e.snap ? ' checked' : ''} onchange="ARM.uvEd.snap=this.checked"> ${tt('armory.uv_snap')}</label>
    </div>
    <div class="armuvbar">
      <select onchange="armUvShow(this.value)" title="${esc(tt('armory.uv_show_title'))}">
        <option value="">${tt('armory.uv_own_sheet')}</option>${rows.map(r => `<option value="${esc(armTexUrl(r.src))}"${e.show === armTexUrl(r.src) ? ' selected' : ''}>${esc(r.label)}</option>`).join('')}</select>
      <button class="mini" onclick="armUvWear()"${e.show ? '' : ' disabled'} title="${esc(tt('armory.uv_wear_title'))}">${tt('armory.uv_wear')}</button>
      <button class="mini" onclick="armUvReset()" title="${esc(tt('armory.uv_reset_title'))}">${tt('armory.uv_reset')}</button>
    </div>
    <canvas id="armUvCanvas" width="460" height="460" tabindex="0"></canvas>
    <div class="count armuvhint">${tt('armory.uv_hint')}</div>`;
  const c = el.querySelector('canvas');
  c.addEventListener('mousedown', armUvDown);
  c.addEventListener('wheel', armUvWheel, {passive: false});
  c.addEventListener('keydown', armUvKey);
  c.addEventListener('mousemove', ev => { const [x,y]=armUvAt(ev); e.lastX=x; e.lastY=y; });
  c.addEventListener('contextmenu', ev => ev.preventDefault());
  c.addEventListener('mouseenter', () => c.focus({preventScroll: true}));
  armUvPaint();
}
function armUvSet(k, v){ ARM.uvEd[k] = v; armUvPanel(); }
async function armUvShow(url){
  const e = ARM.uvEd;
  e.show = url;
  if(url){
    try{ ARM.uvShowImg = {src: url, img: await armImage(url)}; }catch(err){ ARM.uvShowImg = null; }
  }
  armUvPanel();
}
// the sheet shown is worn by this object from now on (the Textures tab's way)
async function armUvWear(){
  const e = ARM.uvEd, o = armObj(e.id);
  const r = (armTexSheets() || []).find(x => armTexUrl(x.src) === e.show);
  if(!r) return;
  try{
    const path = await armTexFile(r.src, false);
    o.sheet = path; ARM.sheetCache.delete(path);
    e.show = '';
    armRepaint(); armUvPanel();
  }catch(err){ toast(errText(err), 6000); }
}
function armUvReset(){
  const e = ARM.uvEd, o = armObj(e.id);
  for(const pc of o.src) delete pc.uv;
  e.sel.clear();
  armSave(); armFrame(); armUvBuild(); armUvPaint();
}

function armUvPaint(){
  const c = document.getElementById('armUvCanvas');
  const e = ARM.uvEd;
  if(!c || !e) return;
  const x = c.getContext('2d'), g = armUvGeom(c);
  x.fillStyle = '#1b1d21'; x.fillRect(0, 0, c.width, c.height);
  if(g.sh.img){
    x.imageSmoothingEnabled = e.z < 3;
    if(g.sh.sw) x.drawImage(g.sh.img, g.sh.sx, 0, g.sh.sw, g.sh.img.height, g.x0, g.y0, g.W, g.H);
    else x.drawImage(g.sh.img, g.x0, g.y0, g.W, g.H);
  }
  x.strokeStyle = 'rgba(255,255,255,0.25)'; x.strokeRect(g.x0, g.y0, g.W, g.H);
  if(g.sh.span === 2){ x.beginPath(); x.moveTo(g.x0 + g.W / 2, g.y0); x.lineTo(g.x0 + g.W / 2, g.y0 + g.H); x.stroke(); }
  const P = e.pts.map(g.to);
  x.lineWidth = 1;
  x.strokeStyle = 'rgba(255, 200, 60, 0.8)';
  x.beginPath();
  for(const [a, b, cc] of e.tris){ x.moveTo(P[a][0], P[a][1]); x.lineTo(P[b][0], P[b][1]); x.lineTo(P[cc][0], P[cc][1]); x.closePath(); }
  x.stroke();
  if(e.sel.size){
    x.fillStyle = 'rgba(255, 140, 30, 0.25)';
    x.beginPath();
    for(const [a, b, cc] of e.tris){
      if(!e.sel.has(a) || !e.sel.has(b) || !e.sel.has(cc)) continue;
      x.moveTo(P[a][0], P[a][1]); x.lineTo(P[b][0], P[b][1]); x.lineTo(P[cc][0], P[cc][1]); x.closePath();
    }
    x.fill();
    x.fillStyle = '#ff8c1e';
    for(const i of e.sel) x.fillRect(P[i][0] - 2, P[i][1] - 2, 4, 4);
  }
  if(e.drag && e.drag.box){
    const b = e.drag;
    x.strokeStyle = '#fff'; x.setLineDash([4, 3]);
    x.strokeRect(Math.min(b.x0, b.x1), Math.min(b.y0, b.y1), Math.abs(b.x1 - b.x0), Math.abs(b.y1 - b.y0));
    x.setLineDash([]);
  }
  if(e.xf){
    x.fillStyle = '#fff'; x.font = '12px sans-serif';
    x.fillText(`${e.xf.op.toUpperCase()}${e.xf.axis ? ' ' + e.xf.axis.toUpperCase() : ''}`, 8, c.height - 10);
  }
}

/* --- picking ---------------------------------------------------------------------------- */

function armUvAt(ev){
  const c = document.getElementById('armUvCanvas');
  const r = c.getBoundingClientRect();
  return [(ev.clientX - r.left) * c.width / r.width, (ev.clientY - r.top) * c.height / r.height];
}
function armUvNearest(X, Y, within){
  const e = ARM.uvEd, g = armUvGeom(document.getElementById('armUvCanvas'));
  let best = -1, bd = within * within;
  e.pts.forEach((p, i) => { const [px, py] = g.to(p); const d = (px - X) ** 2 + (py - Y) ** 2; if(d < bd){ bd = d; best = i; } });
  return best;
}
function armUvPick(i, add){
  const e = ARM.uvEd;
  const set = e.mode === 'island' ? e.pts.map((_, k) => k).filter(k => e.island[k] === e.island[i]) : [i];
  const on = !(add && set.every(k => e.sel.has(k)));
  if(!add) e.sel.clear();
  set.forEach(k => on ? e.sel.add(k) : e.sel.delete(k));
}

/* --- the mouse ----------------------------------------------------------------------------- */

function armUvDown(ev){
  const e = ARM.uvEd;
  if(!e) return;
  ev.preventDefault();
  const [X, Y] = armUvAt(ev);
  if(e.xf){ armUvXfEnd(ev.button !== 0); return; }
  if(ev.button === 1 || (ev.button === 0 && ev.altKey)){
    e.drag = {pan: true, X, Y, ox: e.ox, oy: e.oy};
  }else if(ev.button === 0){
    const hit = armUvNearest(X, Y, 8);
    if(hit >= 0 && e.sel.has(hit) && !ev.shiftKey){
      e.drag = {move: true, X, Y, start: armUvSnapshot()};
    }else if(hit >= 0){
      armUvPick(hit, ev.shiftKey);
      e.drag = {move: true, X, Y, start: armUvSnapshot()};
    }else{
      if(!ev.shiftKey) e.sel.clear();
      e.drag = {box: true, x0: X, y0: Y, x1: X, y1: Y, add: ev.shiftKey};
    }
  }
  armUvPaint();
  const move = m => armUvMove(m), up = u => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); armUvUp(u); };
  window.addEventListener('mousemove', move);
  window.addEventListener('mouseup', up);
}
function armUvMove(ev){
  const e = ARM.uvEd;
  if(!e) return;
  const [X, Y] = armUvAt(ev);
  if(e.xf){ armUvXfMove(X, Y); return; }
  const d = e.drag;
  if(!d) return;
  if(d.pan){ e.ox = d.ox + X - d.X; e.oy = d.oy + Y - d.Y; }
  else if(d.box){ d.x1 = X; d.y1 = Y; }
  else if(d.move){
    const g = armUvGeom(document.getElementById('armUvCanvas'));
    const du = (X - d.X) / g.W * g.sh.span, dv = (Y - d.Y) / g.H;
    armUvApply(d.start, p => [p.u + du, p.w + dv]);
  }
  armUvPaint();
}
function armUvUp(){
  const e = ARM.uvEd;
  if(!e || !e.drag) return;
  const d = e.drag;
  e.drag = null;
  if(d.box){
    const g = armUvGeom(document.getElementById('armUvCanvas'));
    const lx = Math.min(d.x0, d.x1), hx = Math.max(d.x0, d.x1), ly = Math.min(d.y0, d.y1), hy = Math.max(d.y0, d.y1);
    e.pts.forEach((p, i) => { const [px, py] = g.to(p); if(px >= lx && px <= hx && py >= ly && py <= hy) e.sel.add(i); });
    if(e.mode === 'island'){ const isl = new Set([...e.sel].map(i => e.island[i])); e.pts.forEach((_, i) => isl.has(e.island[i]) && e.sel.add(i)); }
  }
  if(d.move && d.start.moved) armUvCommit();
  armUvPaint();
}
function armUvWheel(ev){
  const e = ARM.uvEd;
  ev.preventDefault();
  const [X, Y] = armUvAt(ev), c = document.getElementById('armUvCanvas');
  const k = ev.deltaY < 0 ? 1.2 : 1 / 1.2, z = Math.min(40, Math.max(0.2, e.z * k));
  // zoom about the pointer
  const cx = c.width / 2 + e.ox, cy = c.height / 2 + e.oy;
  e.ox += (X - cx) * (1 - z / e.z); e.oy += (Y - cy) * (1 - z / e.z);
  e.z = z;
  armUvPaint();
}

/* --- G, R and S ------------------------------------------------------------------------------ */

function armUvKey(ev){
  const e = ARM.uvEd;
  if(!e) return;
  const k = ev.key.toLowerCase();
  ev.stopPropagation();
  if((ev.ctrlKey || ev.metaKey) && (k === 'z' || k === 'y')){
    ev.preventDefault();
    if(e.xf) armUvXfEnd(true);
    e.drag = null; armUndo(k === 'y' || !!ev.shiftKey); return;
  }
  if(e.xf){
    if(k === 'escape'){ armUvXfEnd(true); ev.preventDefault(); }
    else if(k === 'enter'){ armUvXfEnd(false); ev.preventDefault(); }
    else if(e.xf.op === 's' && (/^[0-9.\-]$/.test(k) || k === 'backspace')){
      ev.preventDefault();
      e.xf.number = k === 'backspace' ? (e.xf.number || '').slice(0,-1) : (e.xf.number || '') + k;
      armUvXfMove(e.xf.X, e.xf.Y);
    }
    else if(k === 'x' || k === 'y'){ e.xf.axis = e.xf.axis === k ? '' : k; armUvXfMove(e.xf.X, e.xf.Y); }
    return;
  }
  if(k === 'a' && !ev.ctrlKey){ ev.preventDefault(); if(e.sel.size === e.pts.length) e.sel.clear(); else e.pts.forEach((_, i) => e.sel.add(i)); armUvPaint(); return; }
  if(k === 'escape'){ armUvClose(); return; }
  if((k === 'g' || k === 'r' || k === 's') && e.sel.size){
    ev.preventDefault();
    const c = document.getElementById('armUvCanvas'), g = armUvGeom(c);
    const sel = [...e.sel].map(i => e.pts[i]);
    const cu = sel.reduce((s, p) => s + p.u, 0) / sel.length, cv = sel.reduce((s, p) => s + p.w, 0) / sel.length;
    const [CX, CY] = g.to({u: cu, w: cv});
    const X = e.lastX != null ? e.lastX : CX + 40, Y = e.lastY != null ? e.lastY : CY;
    e.xf = {op: k, axis: '', X, Y, X0: X, Y0: Y, cu, cv, CX, CY, start: armUvSnapshot()};
    const track = m => { const [mx, my] = armUvAt(m); e.lastX = mx; e.lastY = my; if(e.xf) armUvXfMove(mx, my); else window.removeEventListener('mousemove', track); };
    e.xf.track = track;
    window.addEventListener('mousemove', track);
    armUvPaint();
  }
}
function armUvXfMove(X, Y){
  const e = ARM.uvEd, f = e.xf;
  if(!f) return;
  f.X = X; f.Y = Y;
  const g = armUvGeom(document.getElementById('armUvCanvas'));
  if(f.op === 'g'){
    let du = (X - f.X0) / g.W * g.sh.span, dv = (Y - f.Y0) / g.H;
    if(f.axis === 'x') dv = 0; if(f.axis === 'y') du = 0;
    armUvApply(f.start, p => [p.u + du, p.w + dv]);
  }else if(f.op === 'r'){
    const a0 = Math.atan2(f.Y0 - f.CY, f.X0 - f.CX), a1 = Math.atan2(Y - f.CY, X - f.CX), a = a1 - a0;
    // turned in texels, so a non-square sheet turns true
    const ku = g.W / g.sh.span, kv = g.H, cs = Math.cos(a), sn = Math.sin(a);
    armUvApply(f.start, p => {
      const x = (p.u - f.cu) * ku, y = (p.w - f.cv) * kv;
      return [f.cu + (x * cs - y * sn) / ku, f.cv + (x * sn + y * cs) / kv];
    });
  }else{
    const d0 = Math.hypot(f.X0 - f.CX, f.Y0 - f.CY) || 1;
    const typed = f.number && Number(f.number);
    const s = f.number && Number.isFinite(typed) ? typed : Math.hypot(X - f.CX, Y - f.CY) / d0;
    const su = f.axis === 'y' ? 1 : s, sv = f.axis === 'x' ? 1 : s;
    armUvApply(f.start, p => [f.cu + (p.u - f.cu) * su, f.cv + (p.w - f.cv) * sv]);
  }
  armUvPaint();
}
function armUvXfEnd(cancel){
  const e = ARM.uvEd, f = e.xf;
  e.xf = null;
  if(!f) return;
  window.removeEventListener('mousemove', f.track);
  if(cancel){ armUvApply(f.start, p => [p.u, p.w], false); f.start.moved = false; armUvPush(); }
  else if(f.start.moved) armUvCommit();
  armUvPaint();
}

/* --- moving the selection, and keeping it ---------------------------------------------------- */

function armUvSnapshot(){
  const e = ARM.uvEd;
  return {at: [...e.sel].map(i => ({i, u: e.pts[i].u, w: e.pts[i].w})), moved: false};
}
function armUvApply(start, fn, snap=true){
  const e = ARM.uvEd, g = armUvGeom(document.getElementById('armUvCanvas'));
  // a texel of the sheet shown, in UV units
  const perU = g.sh.span === 2 ? g.iw / 2 : g.iw;
  for(const s of start.at){
    let [u, w] = fn(s);
    if(snap && e.snap && !(e.xf && e.xf.op === 's' && e.xf.number) && perU > 1){ u = Math.round(u * perU) / perU; w = Math.round(w * (g.ih || 1)) / (g.ih || 1); }
    e.pts[s.i].u = u; e.pts[s.i].w = w;
    if(u !== s.u || w !== s.w) start.moved = true;
  }
  armUvPush();
}
// the points as they stand onto the pieces, a copy of each map changed
function armUvPush(){
  const e = ARM.uvEd, o = armObj(e.id);
  const fresh = new Set();
  for(const i of e.sel){
    const p = e.pts[i], pc = o.src[p.pi];
    if(!fresh.has(p.pi)){ pc.uv = Object.assign({}, pc.uv || {}); fresh.add(p.pi); }
    pc.uv[p.v] = [Math.round(p.u * 1e6) / 1e6, Math.round(p.w * 1e6) / 1e6];
  }
  armFrame();
}
function armUvCommit(){ armSave(); }
