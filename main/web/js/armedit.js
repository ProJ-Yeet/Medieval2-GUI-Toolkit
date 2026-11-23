/* =========================================================================
   Armory Studio, the viewport's shading and Edit Mode (2026-11-23)

   Shading, as Blender's header has it: Solid or Wireframe, each with an
   X-ray of its own (off for Solid, on for Wireframe, as Blender starts
   them). Z swaps the shading, Alt+Z the X-ray.

   Selected objects are outlined, not tinted: the active one (the last one
   clicked, which Merge keeps) light orange, the others darker. The object
   under the pointer is tinted light blue.

   The detail view is Blender's Edit Mode for one object. 1 picks vertices,
   2 edges, 3 faces; Shift with a number adds that mode, so vertices and
   edges are picked together as RetopoFlow does. Ctrl+click selects the
   shortest path from the last element picked. Connected mode, or L, takes
   whole linked parts. A box takes what is inside it, and without X-ray only
   what can be seen. What is under the pointer lights up before a click.
   Split takes the selected faces into a new object, cut out of this one or
   copied from it.

   The overlays are drawn with the viewport's own context (armory.js armGl),
   after the model and before the picture is copied to the page. What can be
   seen is read from a picture of face numbers drawn off screen (armEditIds).
   ========================================================================= */

const armXrayOn = () => ARM.shade === 'wire' ? ARM.xrayWire !== false : !!ARM.xraySolid;
const ARM_COL = {wire: [0.62, 0.65, 0.7, 0.9], sel: [0.93, 0.45, 0.08, 1], active: [1, 0.72, 0.3, 1],
  hover: [0.45, 0.72, 1, 1], editWire: [0.04, 0.04, 0.05, 0.9], editWireLight: [0.78, 0.8, 0.84, 0.7]};

function armShadeSet(v){ ARM.shade = v; armPaintShade(); armFrame(); }
function armXrayToggle(){
  if(ARM.shade === 'wire') ARM.xrayWire = !armXrayOn(); else ARM.xraySolid = !ARM.xraySolid;
  armPaintShade(); armFrame();
}
function armShadeHtml(){
  const sh = ARM.shade === 'wire' || ARM.shade === 'both' ? ARM.shade : 'solid';
  return `<button class="mini${sh === 'solid' ? ' on' : ''}" onclick="armShadeSet('solid')" title="${esc(tt('armory.shade_solid_title'))}">${tt('armory.shade_solid')}</button>
    <button class="mini${sh === 'both' ? ' on' : ''}" onclick="armShadeSet('both')" title="${esc(tt('armory.shade_both_title'))}">${tt('armory.shade_both')}</button>
    <button class="mini${sh === 'wire' ? ' on' : ''}" onclick="armShadeSet('wire')" title="${esc(tt('armory.shade_wire_title'))}">${tt('armory.shade_wire')}</button>
    <button class="mini${armXrayOn() ? ' on' : ''}" onclick="armXrayToggle()" title="${esc(tt('armory.xray_title'))}">${tt('armory.xray')}</button>`;
}
function armPaintShade(){ const el = document.getElementById('armShade'); if(el) el.innerHTML = armShadeHtml(); }

/* --- one program for lines, points and flat triangles ----------------------- */

const ARM_OV_VS = `attribute vec3 aPos; attribute vec4 aCol;
uniform mat4 uMVP; uniform float uPt, uBias; varying vec4 vCol;
void main(){ vCol = aCol; gl_Position = uMVP * vec4(aPos, 1.0); gl_Position.z -= uBias * gl_Position.w; gl_PointSize = uPt; }`;
const ARM_OV_FS = `precision mediump float; varying vec4 vCol; void main(){ gl_FragColor = vCol; }`;
// the outline: outside the selected silhouettes, within a few pixels of one
const ARM_LINE_VS = `attribute vec2 aXY; void main(){ gl_Position = vec4(aXY, 0.0, 1.0); }`;
const ARM_LINE_FS = `precision mediump float;
uniform sampler2D uM; uniform vec2 uPx; uniform float uR;
void main(){
  vec2 uv = gl_FragCoord.xy * uPx;
  vec4 c = texture2D(uM, uv);
  if(c.r + c.g > 0.5) discard;
  float a = 0.0, s = 0.0;
  for(int i = -3; i <= 3; i++) for(int j = -3; j <= 3; j++){
    if(float(i * i + j * j) > uR * uR) continue;
    vec4 t = texture2D(uM, uv + vec2(float(i), float(j)) * uPx);
    a = max(a, t.r); s = max(s, t.g);
  }
  if(a > 0.5) gl_FragColor = vec4(1.0, 0.72, 0.3, 1.0);
  else if(s > 0.5) gl_FragColor = vec4(0.93, 0.45, 0.08, 1.0);
  else discard;
}`;

function armProgram(gl, vs, fs, attrs, unis){
  const sh = (type, src) => {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, vs));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  const out = {p, a: {}, u: {}};
  attrs.forEach(n => { out.a[n] = gl.getAttribLocation(p, n); });
  unis.forEach(n => { out.u[n] = gl.getUniformLocation(p, n); });
  return out;
}
// the programs and buffers belong to one context: a restored one builds them anew
function armOv(){
  const gl = armGl();
  if(!gl) return null;
  if(ARM.ov && ARM.ov.gl === gl) return ARM.ov;
  ARM.ov = {gl, fb: null,
    prog: armProgram(gl, ARM_OV_VS, ARM_OV_FS, ['aPos', 'aCol'], ['uMVP', 'uPt', 'uBias']),
    line: armProgram(gl, ARM_LINE_VS, ARM_LINE_FS, ['aXY'], ['uM', 'uPx', 'uR']),
    pos: gl.createBuffer(), col: gl.createBuffer(), quad: gl.createBuffer()};
  gl.bindBuffer(gl.ARRAY_BUFFER, ARM.ov.quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  return ARM.ov;
}

/* Draws `pos` (x,y,z each) as `mode`: one colour for all ([r,g,b,a]) or a
   Float32Array of one per vertex. Or, with opt.buf and opt.idx, a vertex
   buffer already on the GPU through an index buffer of lines. */
function armOvDraw(mode, pos, col, mvp, opt){
  opt = opt || {};
  const ov = armOv();
  if(!ov) return;
  const gl = ov.gl, P = ov.prog;
  const n = opt.idx ? opt.count : pos.length / 3;
  if(!n) return;
  gl.useProgram(P.p);
  gl.bindBuffer(gl.ARRAY_BUFFER, opt.buf || ov.pos);
  if(!opt.buf) gl.bufferData(gl.ARRAY_BUFFER, pos, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(P.a.aPos);
  gl.vertexAttribPointer(P.a.aPos, 3, gl.FLOAT, false, 0, 0);
  if(Array.isArray(col)){
    gl.disableVertexAttribArray(P.a.aCol);
    gl.vertexAttrib4f(P.a.aCol, col[0], col[1], col[2], col[3]);
  }else{
    gl.bindBuffer(gl.ARRAY_BUFFER, ov.col);
    gl.bufferData(gl.ARRAY_BUFFER, col, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(P.a.aCol);
    gl.vertexAttribPointer(P.a.aCol, 4, gl.FLOAT, false, 0, 0);
  }
  gl.uniformMatrix4fv(P.u.uMVP, false, new Float32Array(mvp));
  gl.uniform1f(P.u.uPt, opt.pt || 1);
  gl.uniform1f(P.u.uBias, opt.bias || 0);
  if(opt.depth === false) gl.disable(gl.DEPTH_TEST); else { gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); }
  gl.depthMask(!!opt.write);
  if(opt.blend === false) gl.disable(gl.BLEND);
  else { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); }
  if(opt.idx){ gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, opt.idx); gl.drawElements(mode, n, gl.UNSIGNED_SHORT, 0); }
  else gl.drawArrays(mode, 0, n);
  // what the model's program finds as it was: an attribute left on with a
  // short buffer behind it fails its next draw
  gl.disableVertexAttribArray(P.a.aPos);
  gl.disableVertexAttribArray(P.a.aCol);
  gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LESS); gl.depthMask(true); gl.disable(gl.BLEND);
  gl.useProgram(ARM.prog);
}

/* An off-screen picture the size of the context's canvas, with depth: the
   selection's silhouettes for the outline, and the face numbers of Edit Mode. */
function armFbo(){
  const ov = armOv(), gl = ov.gl, W = ARM.glCanvas.width, H = ARM.glCanvas.height;
  let f = ov.fb;
  if(f && f.w === W && f.h === H) return f;
  if(f){ gl.deleteFramebuffer(f.fb); gl.deleteTexture(f.tex); gl.deleteRenderbuffer(f.rb); }
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, W, H, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const rb = gl.createRenderbuffer();
  gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
  gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, W, H);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  ov.fb = f = {fb, tex, rb, w: W, h: H};
  return f;
}

/* --- object mode: wires and the outline ---------------------------------------- */

/* A piece's edges as an index buffer of lines, made once per triangle list. */
const ARM_WIRE = new WeakMap();
function armWireIdx(key, corners){
  const gl = ARM.gl;
  let hit = ARM_WIRE.get(key);
  if(hit && hit.gl === gl && hit.sig === corners.sig) return hit;
  const flat = corners.list, seen = new Set(), lines = [];
  for(let i = 0; i + 2 < flat.length; i += 3) for(const [a, b] of [[flat[i], flat[i+1]], [flat[i+1], flat[i+2]], [flat[i+2], flat[i]]]){
    if(a === b) continue;
    const k = a < b ? a * 65536 + b : b * 65536 + a;
    if(seen.has(k)) continue;
    seen.add(k); lines.push(a, b);
  }
  if(hit && hit.gl === gl) gl.deleteBuffer(hit.buf);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(lines), gl.STATIC_DRAW);
  hit = {gl, buf, count: lines.length, sig: corners.sig};
  ARM_WIRE.set(key, hit);
  return hit;
}
function armWireColour(ob){
  if(ARM.hover === ob.id) return ARM_COL.hover;
  if(ARM.sel.has(ob.id)) return ARM.active === ob.id ? ARM_COL.active : ARM_COL.sel;
  return ARM.shade === 'both' ? ARM_COL.editWire : ARM_COL.wire;
}
/* Wireframe shading: every visible object's edges, in its selection's colour. */
function armWireDraw(objs, cam, top){
  const vp = armMul(cam.proj, cam.view), xr = armXrayOn();
  for(const ob of objs){
    if(ARM.detail && ob.id === ARM.detail.id) continue;        // Edit Mode draws its own
    const col = armWireColour(ob);
    const posed = typeof armAnimGeoFor === 'function' ? armAnimGeoFor(ob) : null;
    if(posed && posed.idx){
      const w = armWireIdx(posed, {list: posed.idx, sig: posed.sig});
      armOvDraw(ARM.gl.LINES, null, col, armMul(vp, top), {buf: posed.glPos, idx: w.buf, count: w.count, depth: !xr, bias: 0.0004});
      continue;
    }
    const om = armMul(top, armObjMatrix(ob, armPivot(ob)));
    for(const pc of ob.src || []){
      const live = ARM.assets.get(pc.asset);
      if(!live || !live.buf || !live.geo || !live.geo.groups[pc.group]) continue;
      let w = ARM_WIRE.get(pc);
      if(!w || w.gl !== ARM.gl || w.tris !== pc.tris || w.weld !== pc.weld || w.flip !== pc.flip){
        const list = [];
        armPieceEach(live, pc, v => list.push(v));
        w = armWireIdx(pc, {list, sig: [pc.tris, pc.weld, pc.flip]});
        Object.assign(w, {tris: pc.tris, weld: pc.weld, flip: pc.flip});
      }
      armOvDraw(ARM.gl.LINES, null, col, armMul(vp, pc.xf ? armMul(om, pc.xf) : om),
        {buf: live.buf.pos, idx: w.buf, count: w.count, depth: !xr, bias: 0.0004});
    }
  }
}

/* Solid shading: the selected objects' silhouettes drawn off screen (red the
   active one, green the rest), then a ring round them on the picture. */
function armOutlineDraw(objs, cam, w, h){
  if(ARM.detail || ARM.shade === 'wire') return;
  const sel = objs.filter(o => ARM.sel.has(o.id));
  if(!sel.length) return;
  const ov = armOv();
  if(!ov) return;
  const gl = ov.gl, f = armFbo();
  gl.bindFramebuffer(gl.FRAMEBUFFER, f.fb);
  const rest = sel.filter(o => o.id !== ARM.active), act = sel.filter(o => o.id === ARM.active);
  armRender(rest, w, h, cam, {mask: true, maskCol: [0, 1, 0], bg: [0, 0, 0]});
  if(act.length) armRender(act, w, h, cam, {mask: true, maskCol: [1, 0, 0], noClear: true});
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  const H = ARM.glCanvas.height, L = ov.line;
  gl.viewport(0, H - h, w, h);
  gl.useProgram(L.p);
  gl.disable(gl.DEPTH_TEST);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, f.tex);
  gl.uniform1i(L.u.uM, 0);
  gl.uniform2f(L.u.uPx, 1 / f.w, 1 / f.h);
  gl.uniform1f(L.u.uR, Math.min(3, 1.5 * Math.min(window.devicePixelRatio || 1, 2)));
  gl.bindBuffer(gl.ARRAY_BUFFER, ov.quad);
  gl.enableVertexAttribArray(L.a.aXY);
  gl.vertexAttribPointer(L.a.aXY, 2, gl.FLOAT, false, 0, 0);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  gl.disableVertexAttribArray(L.a.aXY);
  gl.enable(gl.DEPTH_TEST);
  gl.useProgram(ARM.prog);
}

/* --- Edit Mode: the mesh as vertices, edges and faces ---------------------------- */

const armEditModes = () => {
  const m = (state.settings || {}).armory_edit_mode || 'f';
  return {v: m.includes('v'), e: m.includes('e'), f: m.includes('f')};
};
/* 1, 2 or 3 alone picks that mode; with Shift it is added or taken away,
   never leaving none. */
function armEditMode(kind, add){
  const m = armEditModes();
  if(add){ m[kind] = !m[kind]; if(!m.v && !m.e && !m.f) m[kind] = true; }
  else { m.v = m.e = m.f = false; m[kind] = true; }
  const v = ['v', 'e', 'f'].filter(k => m[k]).join('');
  state.settings.armory_edit_mode = v;
  api.post('/api/settings', {armory_edit_mode: v}).catch(() => {});
  if(ARM.detail){ ARM.detail.hover = null; ARM.detail.hoverKey = ''; }
  armPaintDetailBar(); armFrame();
}

/* Corners at one place are one vertex (a seam splits them for the UVs), as
   Blender would weld them; faces are the game's triangles. */
function armEditTopo(){
  const d = ARM.detail, o = d && armObj(d.id);
  if(!o) return null;
  const sig = JSON.stringify(o.src || []);
  if(d.topo && d.topo.sig === sig) return d.topo;
  const verts = [], faces = [], edges = [], vKey = new Map(), eKey = new Map();
  (o.src || []).forEach((pc, pi) => {
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo) return;
    const g = live.geo.groups[pc.group], I = live.geo.indices, P = live.geo.positions;
    if(!g) return;
    const W = pc.weld || {}, F = armFlipSet(pc);
    const vid = gi => {
      const v = W[gi] != null ? W[gi] : gi;
      const k = `${pi}:${P[v*3].toFixed(5)},${P[v*3+1].toFixed(5)},${P[v*3+2].toFixed(5)}`;
      let id = vKey.get(k);
      if(id == null){ id = verts.length; verts.push({pi, v}); vKey.set(k, id); }
      return id;
    };
    const n = pc.tris ? pc.tris.length : g.count / 3;
    for(let i = 0; i < n; i++){
      const t = pc.tris ? pc.tris[i] : i;
      let c = [I[g.start + t*3], I[g.start + t*3 + 1], I[g.start + t*3 + 2]];
      if(F.has(t)) c = [c[0], c[2], c[1]];
      const vs = c.map(vid);
      const es = [[0, 1], [1, 2], [2, 0]].map(([x, y]) => {
        const a = Math.min(vs[x], vs[y]), b = Math.max(vs[x], vs[y]);
        if(a === b) return -1;
        let id = eKey.get(a * 1e7 + b);
        if(id == null){ id = edges.length; edges.push([a, b]); eKey.set(a * 1e7 + b, id); }
        return id;
      });
      faces.push({pi, t, v: vs, e: es});
    }
  });
  const vFaces = verts.map(() => []), eFaces = edges.map(() => []), vEdges = verts.map(() => []);
  faces.forEach((f, i) => { f.v.forEach(v => vFaces[v].push(i)); f.e.forEach(e => { if(e >= 0) eFaces[e].push(i); }); });
  edges.forEach(([a, b], i) => { vEdges[a].push(i); vEdges[b].push(i); });
  // the linked parts, by shared vertices (Blender's L)
  const comp = new Int32Array(faces.length).fill(-1);
  let nc = 0;
  for(let s = 0; s < faces.length; s++){
    if(comp[s] >= 0) continue;
    const todo = [s]; comp[s] = nc;
    while(todo.length){
      const f = todo.pop();
      for(const v of faces[f].v) for(const u of vFaces[v]) if(comp[u] < 0){ comp[u] = nc; todo.push(u); }
    }
    nc++;
  }
  const fresh = d.topo != null;
  d.topo = {sig, verts, faces, edges, vFaces, eFaces, vEdges, comp};
  // a selection is of the mesh it was made on
  if(fresh){ d.sv.clear(); d.se.clear(); d.sf.clear(); d.last = null; }
  return d.topo;
}

/* Every vertex where it is drawn: the object's move, turn and scale and the
   page's mirror applied. */
function armEditWorld(T){
  const o = armObj(ARM.detail.id);
  const om = armMul(ARM_MIRROR, armObjMatrix(o, armPivot(o)));
  const mats = (o.src || []).map(pc => pc.xf ? armMul(om, pc.xf) : om);
  const out = new Float32Array(T.verts.length * 3);
  T.verts.forEach(({pi, v}, i) => {
    const P = ARM.assets.get(o.src[pi].asset).geo.positions, m = mats[pi];
    const x = P[v*3], y = P[v*3+1], z = P[v*3+2];
    out[i*3] = m[0]*x + m[4]*y + m[8]*z + m[12];
    out[i*3+1] = m[1]*x + m[5]*y + m[9]*z + m[13];
    out[i*3+2] = m[2]*x + m[6]*y + m[10]*z + m[14];
  });
  return out;
}
/* And on the canvas, in its pixels: x, y and depth (NaN behind the eye). */
function armEditScreen(){
  const d = ARM.detail, T = armEditTopo(), view = ARM.view;
  if(!T || !view) return null;
  const o = armObj(d.id), w = view.width, h = view.height;
  const sig = JSON.stringify([ARM.cam, w, h, T.sig, o.t, o.r, o.s]);
  if(d.scr && d.scr.sig === sig) return d.scr;
  const wp = armEditWorld(T), cam = armCamera(w / h), m = armMul(cam.proj, cam.view);
  const S = new Float32Array(T.verts.length * 3);
  for(let i = 0; i < T.verts.length; i++){
    const x = wp[i*3], y = wp[i*3+1], z = wp[i*3+2];
    const cw = m[3]*x + m[7]*y + m[11]*z + m[15];
    if(cw <= 1e-6){ S[i*3] = S[i*3+1] = S[i*3+2] = NaN; continue; }
    S[i*3] = ((m[0]*x + m[4]*y + m[8]*z + m[12]) / cw * 0.5 + 0.5) * w;
    S[i*3+1] = (1 - ((m[1]*x + m[5]*y + m[9]*z + m[13]) / cw * 0.5 + 0.5)) * h;
    S[i*3+2] = (m[2]*x + m[6]*y + m[10]*z + m[14]) / cw;
  }
  d.scr = {sig, S, wp, w, h, vp: m};
  return d.scr;
}

/* The faces as numbers (one more than the face, 0 for none), drawn with
   depth off screen and read back: what can be seen, at each pixel. */
function armEditIds(){
  const d = ARM.detail, sc = armEditScreen(), T = d && d.topo;
  if(!sc || !T) return null;
  if(d.ids && d.ids.sig === sc.sig) return d.ids;
  const ov = armOv();
  if(!ov) return null;
  const gl = ov.gl, f = armFbo(), H = ARM.glCanvas.height, w = sc.w, h = sc.h;
  const pos = new Float32Array(T.faces.length * 9), col = new Float32Array(T.faces.length * 12);
  T.faces.forEach((fc, i) => {
    const n = i + 1, c = [(n & 255) / 255, ((n >> 8) & 255) / 255, ((n >> 16) & 255) / 255, 1];
    for(let k = 0; k < 3; k++){
      const v = fc.v[k];
      pos.set([sc.wp[v*3], sc.wp[v*3+1], sc.wp[v*3+2]], i*9 + k*3);
      col.set(c, i*12 + k*4);
    }
  });
  gl.bindFramebuffer(gl.FRAMEBUFFER, f.fb);
  gl.viewport(0, H - h, w, h);
  gl.enable(gl.SCISSOR_TEST); gl.scissor(0, H - h, w, h);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.disable(gl.SCISSOR_TEST);
  armOvDraw(gl.TRIANGLES, pos, col, sc.vp, {blend: false, write: true});
  const data = new Uint8Array(w * h * 4);
  gl.readPixels(0, H - h, w, h, gl.RGBA, gl.UNSIGNED_BYTE, data);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  d.ids = {sig: sc.sig, w, h, data};
  return d.ids;
}
function armEditIdAt(ids, x, y){
  x = Math.round(x); y = Math.round(y);
  if(x < 0 || y < 0 || x >= ids.w || y >= ids.h) return -1;
  const i = ((ids.h - 1 - y) * ids.w + x) * 4;
  return (ids.data[i] | (ids.data[i+1] << 8) | (ids.data[i+2] << 16)) - 1;
}
/* Seen: one of `faces` shows within a few pixels of (x, y). */
function armEditSeen(ids, x, y, faces){
  if(!ids) return true;
  const want = new Set(faces), r = 3;
  for(let dy = -r; dy <= r; dy++) for(let dx = -r; dx <= r; dx++)
    if(want.has(armEditIdAt(ids, x + dx, y + dy))) return true;
  return false;
}

/* What a click at (x, y) would pick, in the modes that are on: the nearest
   vertex or edge within reach, else the face under it. */
function armEditPick(x, y){
  const d = ARM.detail, sc = armEditScreen(), T = d && d.topo;
  if(!sc) return null;
  const m = armEditModes(), xr = armXrayOn(), ids = xr ? null : armEditIds();
  const dpr = ARM.view.width / (ARM.view.getBoundingClientRect().width || ARM.view.width);
  const S = sc.S, R = 12 * dpr;
  let best = null, bd = Infinity;
  if(m.v){
    for(let i = 0; i < T.verts.length; i++){
      const dd = Math.hypot(S[i*3] - x, S[i*3+1] - y);
      // a vertex is nearer than an edge it ends by the width of a finger
      if(dd < R && dd - 4 * dpr < bd && armEditSeen(ids, S[i*3], S[i*3+1], T.vFaces[i])){ bd = dd - 4 * dpr; best = {type: 'v', id: i}; }
    }
  }
  if(m.e){
    T.edges.forEach(([a, b], i) => {
      const ax = S[a*3], ay = S[a*3+1], bx = S[b*3], by = S[b*3+1];
      if(!(ax === ax && bx === bx)) return;
      const L2 = (bx - ax) ** 2 + (by - ay) ** 2;
      const t = L2 ? Math.max(0, Math.min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / L2)) : 0;
      const px = ax + t * (bx - ax), py = ay + t * (by - ay), dd = Math.hypot(px - x, py - y);
      if(dd < R * 0.8 && dd < bd && armEditSeen(ids, px, py, T.eFaces[i])){ bd = dd; best = {type: 'e', id: i}; }
    });
  }
  if(!best && m.f){
    if(ids){
      const id = armEditIdAt(ids, x, y);
      if(id >= 0) best = {type: 'f', id};
    }else{
      // X-ray: the face whose middle is nearest, as Blender's face dots
      let fd = 40 * dpr;
      T.faces.forEach((fc, i) => {
        const cx = (S[fc.v[0]*3] + S[fc.v[1]*3] + S[fc.v[2]*3]) / 3, cy = (S[fc.v[0]*3+1] + S[fc.v[1]*3+1] + S[fc.v[2]*3+1]) / 3;
        const dd = Math.hypot(cx - x, cy - y);
        if(dd < fd){ fd = dd; best = {type: 'f', id: i}; }
      });
    }
  }
  return best;
}

const armEditHas = (d, hit) => (hit.type === 'v' ? d.sv : hit.type === 'e' ? d.se : d.sf).has(hit.id);
/* One element in or out, with what it implies, as Blender flushes it: the
   corners of a face or edge come with it, and an edge or face whose corners
   are all chosen is chosen too. */
function armEditSet(type, id, on){
  const d = ARM.detail, T = d.topo;
  const put = (s, k, v) => { if(v) s.add(k); else s.delete(k); };
  const flushFaces = fs => fs.forEach(f => put(d.sf, f, T.faces[f].e.every(e => e < 0 || d.se.has(e))));
  if(type === 'f'){
    const fc = T.faces[id];
    put(d.sf, id, on);
    if(on){ fc.v.forEach(v => d.sv.add(v)); fc.e.forEach(e => { if(e >= 0) d.se.add(e); }); }
    else{
      fc.e.forEach(e => { if(e >= 0 && !T.eFaces[e].some(f => d.sf.has(f))) d.se.delete(e); });
      fc.v.forEach(v => { if(!T.vFaces[v].some(f => d.sf.has(f))) d.sv.delete(v); });
    }
  }else if(type === 'e'){
    const [a, b] = T.edges[id];
    put(d.se, id, on);
    if(on){ d.sv.add(a); d.sv.add(b); }
    else [a, b].forEach(v => { if(!T.vEdges[v].some(e => d.se.has(e))) d.sv.delete(v); });
    flushFaces(T.eFaces[id]);
  }else{
    put(d.sv, id, on);
    T.vEdges[id].forEach(e => { const [a, b] = T.edges[e]; put(d.se, e, d.sv.has(a) && d.sv.has(b)); });
    flushFaces(T.vFaces[id]);
  }
}
/* A (Blender) and Ctrl+A: every vertex, edge and face in the modes on; Alt+A none. */
function armEditSelectAll(on){
  const d = ARM.detail;
  if(!d || !armEditTopo()) return;
  const T = d.topo, m = armEditModes();
  armEditClear();
  if(on){
    if(m.v) for(let v = 0; v < T.verts.length; v++) armEditSet('v', v, true);
    if(m.e) for(let i = 0; i < T.edges.length; i++) armEditSet('e', i, true);
    if(m.f) for(let f = 0; f < T.faces.length; f++) armEditSet('f', f, true);
  }
  armPaintDetailBar(); armFrame();
}
function armEditClear(){ const d = ARM.detail; d.sv.clear(); d.se.clear(); d.sf.clear(); d.last = null; }
/* The linked part an element belongs to, as faces. */
function armEditPart(hit){
  const T = ARM.detail.topo;
  const f = hit.type === 'f' ? hit.id : hit.type === 'e' ? T.eFaces[hit.id][0] : T.vFaces[hit.id][0];
  if(f == null) return [];
  const c = T.comp[f], out = [];
  for(let i = 0; i < T.faces.length; i++) if(T.comp[i] === c) out.push(i);
  return out;
}

/* Ctrl+click: the shortest way from the last element picked to this one,
   over the edges (vertices, edges) or across shared edges (faces). */
function armEditPath(from, to){
  const d = ARM.detail, T = d.topo, wp = armEditScreen().wp;
  const dist = (a, b) => Math.hypot(wp[a*3] - wp[b*3], wp[a*3+1] - wp[b*3+1], wp[a*3+2] - wp[b*3+2]);
  const dijkstra = (n, starts, goal, next) => {
    const best = new Float64Array(n).fill(Infinity), prev = new Int32Array(n).fill(-1), done = new Uint8Array(n);
    starts.forEach(s => { best[s] = 0; });
    for(;;){
      let u = -1, bu = Infinity;
      // the meshes here are a few thousand elements: a plain scan is enough
      for(let i = 0; i < n; i++) if(!done[i] && best[i] < bu){ bu = best[i]; u = i; }
      if(u < 0) return null;
      if(goal.has(u)){ const path = []; for(let x = u; x >= 0; x = prev[x]) path.push(x); return path; }
      done[u] = 1;
      next(u, (v, w) => { if(best[u] + w < best[v]){ best[v] = best[u] + w; prev[v] = u; } });
    }
  };
  const viaVerts = (u, go) => T.vEdges[u].forEach(e => { const [a, b] = T.edges[e]; const v = a === u ? b : a; go(v, dist(u, v)); });
  if(from.type === 'v'){
    const path = dijkstra(T.verts.length, [from.id], new Set([to.id]), viaVerts);
    if(path) path.forEach(v => armEditSet('v', v, true));
  }else if(from.type === 'e'){
    const path = dijkstra(T.verts.length, T.edges[from.id], new Set(T.edges[to.id]), viaVerts);
    if(path){
      for(let i = 0; i + 1 < path.length; i++){
        const a = Math.min(path[i], path[i+1]), b = Math.max(path[i], path[i+1]);
        const e = T.vEdges[a].find(x => T.edges[x][0] === a && T.edges[x][1] === b);
        if(e != null) armEditSet('e', e, true);
      }
    }
    armEditSet('e', to.id, true);
  }else{
    const mid = f => { const v = T.faces[f].v; return [0, 1, 2].map(k => (wp[v[0]*3+k] + wp[v[1]*3+k] + wp[v[2]*3+k]) / 3); };
    const path = dijkstra(T.faces.length, [from.id], new Set([to.id]), (u, go) => {
      const a = mid(u);
      T.faces[u].e.forEach(e => { if(e >= 0) T.eFaces[e].forEach(f => { if(f !== u){ const b = mid(f); go(f, Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2])); } }); });
    });
    if(path) path.forEach(f => armEditSet('f', f, true));
  }
  d.last = to;
}

/* --- Edit Mode's clicks, hover and box ---------------------------------------- */

function armEditClick(x, y, e){
  const d = ARM.detail;
  if(!armEditTopo()) return;
  const hit = armEditPick(x, y);
  if(e.ctrlKey && hit && d.last && d.last.type === hit.type && !d.connected){
    armEditPath(d.last, hit);
  }else{
    if(!e.shiftKey) armEditClear();
    if(hit){
      const on = !(e.shiftKey && armEditHas(d, hit));
      if(d.connected) armEditPart(hit).forEach(f => armEditSet('f', f, on));
      else armEditSet(hit.type, hit.id, on);
      d.last = on ? hit : null;
    }
  }
  armPaintDetailBar(); armFrame();
}
function armEditHover(x, y){
  const d = ARM.detail;
  if(!armEditTopo()) return;
  const hit = x == null ? null : armEditPick(x, y);
  const key = hit ? hit.type + hit.id : '';
  if(key === d.hoverKey) return;
  d.hoverKey = key; d.hover = hit;
  armFrame();
}
/* L, and the button: every part linked to what is under the pointer, else
   to what is selected. */
function armDetailConnected(){
  const d = ARM.detail;
  if(!d || !armEditTopo()) return;
  const seeds = d.hover ? [d.hover] : [...d.sf].map(id => ({type: 'f', id}))
    .concat([...d.se].map(id => ({type: 'e', id})), [...d.sv].map(id => ({type: 'v', id})));
  if(!seeds.length){ toast(tt('armory.pick_a_triangle')); return; }
  const faces = new Set();
  seeds.forEach(h => armEditPart(h).forEach(f => faces.add(f)));
  faces.forEach(f => armEditSet('f', f, true));
  armPaintDetailBar(); armFrame();
}
/* A box: the vertices and edges inside it in their modes, the faces seen
   inside it (with X-ray, those whose middle is inside it). */
function armEditBox(x0, y0, x1, y1, add){
  const d = ARM.detail, sc = armEditScreen(), T = d && d.topo;
  if(!sc) return;
  if(!add) armEditClear();
  const m = armEditModes(), xr = armXrayOn(), ids = xr ? null : armEditIds(), S = sc.S;
  const inside = v => S[v*3] >= x0 && S[v*3] <= x1 && S[v*3+1] >= y0 && S[v*3+1] <= y1;
  const seen = v => armEditSeen(ids, S[v*3], S[v*3+1], T.vFaces[v]);
  if(m.v) for(let v = 0; v < T.verts.length; v++) if(inside(v) && seen(v)) armEditSet('v', v, true);
  if(m.e) T.edges.forEach(([a, b], i) => { if(inside(a) && inside(b) && seen(a) && seen(b)) armEditSet('e', i, true); });
  if(m.f){
    if(ids){
      const got = new Set();
      for(let y = Math.max(0, Math.floor(y0)); y <= Math.min(ids.h - 1, y1); y += 1)
        for(let x = Math.max(0, Math.floor(x0)); x <= Math.min(ids.w - 1, x1); x += 1){
          const id = armEditIdAt(ids, x, y);
          if(id >= 0) got.add(id);
        }
      got.forEach(f => armEditSet('f', f, true));
    }else T.faces.forEach((fc, i) => {
      const cx = (S[fc.v[0]*3] + S[fc.v[1]*3] + S[fc.v[2]*3]) / 3, cy = (S[fc.v[0]*3+1] + S[fc.v[1]*3+1] + S[fc.v[2]*3+1]) / 3;
      if(cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1) armEditSet('f', i, true);
    });
  }
  armPaintDetailBar(); armFrame();
}

/* --- Edit Mode drawn ----------------------------------------------------------- */

function armEditDraw(){
  const d = ARM.detail;
  if(!d || !armObj(d.id) || !armEditTopo()) return;
  const sc = armEditScreen();
  if(!sc) return;
  const T = d.topo, wp = sc.wp, gl = ARM.gl, xr = armXrayOn(), m = armEditModes();
  const depth = !xr;
  const P = v => [wp[v*3], wp[v*3+1], wp[v*3+2]];
  const hov = d.hover;
  const hovFaces = !hov ? [] : d.connected ? armEditPart(hov) : hov.type === 'f' ? [hov.id] : [];
  // faces: the chosen orange, the one under the pointer blue
  const tris = (list, col) => {
    if(!list.length) return;
    const pos = new Float32Array(list.length * 9);
    list.forEach((f, i) => T.faces[f].v.forEach((v, k) => pos.set(P(v), i*9 + k*3)));
    armOvDraw(gl.TRIANGLES, pos, col, sc.vp, {depth, bias: 0.0002});
  };
  tris([...d.sf], [1, 0.6, 0.1, 0.3]);
  tris(hovFaces, [0.45, 0.72, 1, 0.3]);
  // edges: dark (light in Wireframe), the chosen orange, the one under the pointer blue
  const base = ARM.shade === 'wire' ? ARM_COL.editWireLight : ARM_COL.editWire;
  const hovEdge = hov && hov.type === 'e' && !d.connected ? hov.id : -1;
  const pos = new Float32Array(T.edges.length * 6), col = new Float32Array(T.edges.length * 8);
  T.edges.forEach(([a, b], i) => {
    pos.set(P(a), i*6); pos.set(P(b), i*6 + 3);
    const c = i === hovEdge ? ARM_COL.hover : d.se.has(i) ? [1, 0.6, 0.1, 1] : base;
    col.set(c, i*8); col.set(c, i*8 + 4);
  });
  armOvDraw(gl.LINES, pos, col, sc.vp, {depth, bias: 0.0004});
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  if(m.v){
    const vp = new Float32Array(T.verts.length * 3), vc = new Float32Array(T.verts.length * 4);
    const hv = hov && hov.type === 'v' && !d.connected ? hov.id : -1;
    for(let v = 0; v < T.verts.length; v++){
      vp.set(P(v), v*3);
      vc.set(v === hv ? ARM_COL.hover : d.sv.has(v) ? [1, 0.6, 0.1, 1] : ARM.shade === 'wire' ? [0.85, 0.86, 0.9, 1] : [0.05, 0.05, 0.06, 1], v*4);
    }
    armOvDraw(gl.POINTS, vp, vc, sc.vp, {depth, bias: 0.0006, pt: 4 * dpr});
  }
  if(m.f && xr){
    // Blender's face dots, which X-ray picks by
    const fp = new Float32Array(T.faces.length * 3), fcol = new Float32Array(T.faces.length * 4);
    T.faces.forEach((fc, i) => {
      for(let k = 0; k < 3; k++) fp[i*3+k] = (wp[fc.v[0]*3+k] + wp[fc.v[1]*3+k] + wp[fc.v[2]*3+k]) / 3;
      fcol.set(d.sf.has(i) ? [1, 0.6, 0.1, 1] : hovFaces.includes(i) ? ARM_COL.hover : [0.6, 0.62, 0.66, 0.8], i*4);
    });
    armOvDraw(gl.POINTS, fp, fcol, sc.vp, {depth: false, pt: 3 * dpr});
  }
}

/* --- the detail view opened, closed, and its bar ----------------------------------- */

function armDetailOpen(){
  const o = armSelected()[0];
  if(!o || !(o.src || []).length) return;
  ARM.detail = {id: o.id, sv: new Set(), se: new Set(), sf: new Set(), last: null, hover: null, hoverKey: '',
                connected: !!ARM.editConnected, topo: null};
  armPaintDetailBar();
  const b = armBounds([o]);
  if(b){
    const [lo, hi] = b;
    ARM.cam.target = [-(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    ARM.cam.dist = Math.max(0.1, Math.hypot(hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]) * 1.4);
  }
  if(typeof armPaintSliders === 'function') armPaintSliders();
  armFrame();
}
function armDetailClose(){
  ARM.detail = null;
  armPaintDetailBar(); armFrame();
  if(typeof armPaintSliders === 'function') armPaintSliders();
}
function armDetailToggle(){ if(ARM.detail) armDetailClose(); else armDetailOpen(); }
function armEditConnectedToggle(){
  const d = ARM.detail;
  ARM.editConnected = !ARM.editConnected;
  if(d){ d.connected = ARM.editConnected; d.hoverKey = ''; }
  armPaintDetailBar(); armFrame();
}
function armDetailClear(){ armEditClear(); armPaintDetailBar(); armFrame(); }

/* Drawn once per object; after that only its counts and buttons change, so
   the name being typed for a split is never repainted under the cursor. */
function armPaintDetailBar(){
  const el = document.getElementById('armDetailBar');
  const host = document.getElementById('armView');
  if(!host) return;
  if(!ARM.detail){ if(el) el.remove(); return; }
  const d = ARM.detail, o = armObj(d.id), m = armEditModes();
  let bar = el;
  if(!bar || bar.dataset.id !== String(d.id)){
    if(bar) bar.remove();
    bar = Object.assign(document.createElement('div'), {id: 'armDetailBar', className: 'armdetailbar'});
    bar.dataset.id = d.id;
    d.splitName = o ? armUniqueMesh(o.name, o.mesh.replace(/\.\d{3,}(?=$|_)/g, '')) : '';
    bar.innerHTML = `<b>${esc(o ? armFullName(o) : '')}</b>
      <span class="armselmode" id="armSelMode"></span>
      <button class="mini" id="armEditConn" onclick="armEditConnectedToggle()" title="${esc(tt('armory.connected_mode_title'))}">${tt('armory.connected_mode')}</button>
      <button class="mini" onclick="armDetailClear()">${tt('armory.clear_selection')}</button>
      <span class="count" id="armEditCount"></span>
      <span class="armsplit"><input id="armSplitName" value="${esc(d.splitName)}" title="${esc(tt('armory.split_name'))}"
          oninput="ARM.detail.splitName=this.value" onkeydown="event.stopPropagation();if(event.key==='Enter')armSplit(false)">
        <button class="mini primary" id="armSplitCut" onclick="armSplit(false)" title="${esc(tt('armory.split_cut_title'))}">${tt('armory.split_cut')}</button>
        <button class="mini" id="armSplitCopy" onclick="armSplit(true)" title="${esc(tt('armory.split_copy_title'))}">${tt('armory.split_copy')}</button></span>
      <button class="mini" onclick="armDetailClose()">${tt('armory.leave_detail')}</button>`;
    host.appendChild(bar);
  }
  const modes = [['v', 'armory.sel_vertex', '1'], ['e', 'armory.sel_edge', '2'], ['f', 'armory.sel_face', '3']];
  document.getElementById('armSelMode').innerHTML = modes.map(([k, label, key]) =>
    `<button class="mini${m[k] ? ' on' : ''}" onclick="armEditMode('${k}', event.shiftKey)" title="${esc(tt('armory.sel_mode_title', {key}))}">${tt(label)}</button>`).join('');
  document.getElementById('armEditConn').classList.toggle('on', !!d.connected);
  const nF = d.sf.size;
  document.getElementById('armEditCount').textContent = ttN('armory.n_tris_selected', nF);
  document.getElementById('armSplitCut').disabled = !nF;
  document.getElementById('armSplitCopy').disabled = !nF;
}

/* The selected faces into a new object: cut out of this one, or copied from
   it with this one left whole. Named from the bar, not a dialog. */
function armSplit(copy){
  const d = ARM.detail, o = d && armObj(d.id), T = d && d.topo;
  if(!o || !T || !d.sf.size) return;
  const name = (d.splitName || '').trim();
  if(!name){ toast(tt('armory.split_name')); document.getElementById('armSplitName')?.focus(); return; }
  const p = armProj();
  const byPiece = new Map();
  for(const f of d.sf){
    const {pi, t} = T.faces[f];
    if(!byPiece.has(pi)) byPiece.set(pi, new Set());
    byPiece.get(pi).add(t);
  }
  const newSrc = [];
  const kept = o.src.map((pc, pi) => {
    const take = byPiece.get(pi);
    if(!take) return pc;
    const live = ARM.assets.get(pc.asset);
    const g = live.geo.groups[pc.group];
    const all = pc.tris || [...Array(g.count / 3).keys()];
    newSrc.push(Object.assign({}, pc, {tris: all.filter(t => take.has(t))}));
    const rest = all.filter(t => !take.has(t));
    return rest.length ? Object.assign({}, pc, {tris: rest}) : null;
  }).filter(Boolean);
  const parts = armSplitName(name.includes('__') ? name : `${o.name}__${name}`);
  const made = Object.assign(JSON.parse(JSON.stringify(o)), {id: p.nextId++, src: newSrc,
    name: parts[0], mesh: parts[1], weights: null});
  // the split part keeps its place: same move, turn and scale as before, about
  // the pivot the whole object had
  const pv = armPivot(o);
  p.objects.splice(p.objects.indexOf(o) + 1, 0, made);
  if(!copy){
    o.src = kept;
    if(!o.src.length) p.objects = p.objects.filter(x => x !== o);
    o.weights = null;
    if(o.src.length) armFixPivot(o, pv);
  }
  armFixPivot(made, pv);
  ARM.sel = new Set([made.id]);
  ARM.active = made.id;
  const n = d.sf.size;
  armDetailClose();
  toast(ttN(copy ? 'armory.split_copied' : 'armory.split_done', n, {name: armFullName(made)}));
  armRepaint();
}
