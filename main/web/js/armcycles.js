/* =========================================================================
   Armory Studio: the Keyforce Cycles bake's look, live in the viewport

   Under PBR Bake (the Lighting settings' choice), an object the bake can
   light, not baked yet, is drawn as the Cycles bake will bake it
   (uLit 3 in armory.js armFrag): the add-on's material (base x AO, metal,
   roughness = 1 - gloss, its normal map), the bake's world (Blender's HDRI
   made small, mirrored, half saturated, plus the white fill), its eight
   surround suns and key sun, the shadows of each part on itself, the metal
   mix of the suns pass and the world pass, the light floor, and AgX. What
   Blender alone knows (the small worlds, the AgX curve, its light units) was
   measured once in a hidden Blender (cycleslook.py, kf_look.py). Not drawn:
   Cycles' bounced light and its denoising.

   It is drawn in Render mode, or on what the Lighting settings cover while
   they are open (armlit.js armLitMode); Blender measures the light only once
   one of those asks for it.

   Shadows: per object one atlas, each sun's map 512 across and each of the
   world's sixteen directions 128, depth in red, green and blue, the part in
   alpha. The bake moves every loose part apart before baking, so a part is
   shadowed by itself only: a texel is in shadow where the nearest thing to
   the light is its own part. Made again only when the object, its pose or
   the light changes.
   ========================================================================= */

const ARM_CY_SUN = 512, ARM_CY_AO = 128, ARM_CY_W = 2048;
const ARM_CY_SUNS = 9, ARM_CY_DIRS = 16;
const ARM_CY_H = 3 * ARM_CY_SUN + ARM_CY_AO;      // three rows of four suns, then one row of sixteen

// 2026-11-25: shown under PBR Bake (armlit.js armLitMode 3), in Render mode or with
// the Lighting settings open; no switch of its own any more.

/* --- the light, from the server ---------------------------------------------- */

function armCyReady(){ return !!(ARM.cy && ARM.cy.ready && ARM.cy.gl === ARM.gl); }
function armCyCheck(){
  const want = JSON.stringify((typeof kfOpts === 'function' ? kfOpts().adv : {}) || {});
  const c = ARM.cy = ARM.cy || {};
  if(c.want === want && (c.ready || c.busy || c.err) && c.gl === ARM.gl) return;
  if(c.asking) return;
  c.want = want; c.asking = true; c.busy = true;
  api.post('/api/armory/cycles_look', {settings: JSON.parse(want)}).then(r => {
    c.asking = false;
    if(r.error){ c.err = r.error === 'no_blender' ? tt('armory.cy_no_blender') : r.error; c.busy = false; return; }
    if(!r.ready){ setTimeout(() => { if(ARM.cy === c){ c.want = ''; armCyCheck(); } }, 2500); return; }
    armCyUpload(c, r.look);
  }).catch(e => { c.asking = false; c.busy = false; c.err = errText(e); })
    .finally(() => { if(typeof armPaintBar === 'function') armPaintBar(); armFrame(); });
}
function armCyUpload(c, look){
  const gl = armGl();
  if(!gl.getExtension('OES_texture_float')){ c.err = tt('armory.cy_no_float'); c.busy = false; return; }
  const lin = !!gl.getExtension('OES_texture_float_linear');
  const e = look.env, raw = Uint8Array.from(atob(e.data), ch => ch.charCodeAt(0));
  const f = new Float32Array(raw.buffer);
  // levels stacked bottom-up, padded to 1024 rows so the width can wrap
  const rows = 1024, px = new Float32Array(e.w * rows * 4);
  for(let i = 0; i < e.levels * e.h * e.w; i++){ px[i*4] = f[i*3]; px[i*4+1] = f[i*3+1]; px[i*4+2] = f[i*3+2]; px[i*4+3] = 1; }
  const env = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, env);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, e.w, rows, 0, gl.RGBA, gl.FLOAT, px);
  const filt = lin ? gl.LINEAR : gl.NEAREST;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filt);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filt);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const img = new Image();
  img.onload = () => {
    const lut = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, lut);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    Object.assign(c, {look, env, lut, rows, levels: e.levels, ready: true, busy: false, err: '', gl, sig: ''});
    if(typeof armPaintBar === 'function') armPaintBar();
    armFrame();
  };
  img.src = look.lut;
}

/* --- per frame and per object ------------------------------------------------- */

function armCyUniforms(gl, L){
  const c = ARM.cy;
  if(!armCyReady()) return;
  const lk = c.look, st = lk.settings;
  gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_2D, c.env); gl.uniform1i(L.uCyEnv, 4);
  gl.activeTexture(gl.TEXTURE5); gl.bindTexture(gl.TEXTURE_2D, c.lut); gl.uniform1i(L.uCyLut, 5);
  gl.activeTexture(gl.TEXTURE0);
  gl.uniform1f(L.uCyRows, c.rows);
  gl.uniform3f(L.uCyLutR, lk.lut_range[0], lk.lut_range[1], lk.lut_range[2]);
  gl.uniform1f(L.uCyView, lk.view === 'AgX' && st.bake_view !== false ? 1 : 0);
  gl.uniform4f(L.uCyMix, st.bake_ambient, st.bake_world, st.bake_shadows, st.bake_floor);
  gl.uniform4f(L.uCyMix2, st.bake_surround_diffuse, lk.consts.metal_other, lk.consts.glossy[0], lk.consts.glossy[1]);
  const alb = new Float32Array(9 * 2);
  lk.albedo.forEach((a, i) => { alb[i*2] = a[0]; alb[i*2+1] = a[1]; });
  gl.uniform2fv(L.uCyAlb, alb);
  const suns = lk.suns.slice(0, ARM_CY_SUNS), sv = new Float32Array(ARM_CY_SUNS * 4), sa = new Float32Array(ARM_CY_SUNS);
  suns.forEach((s, i) => { sv.set([s.dir[0], s.dir[1], s.dir[2], s.energy], i * 4); sa[i] = s.angle * Math.PI / 180; });
  gl.uniform4fv(L.uCySun, sv); gl.uniform1fv(L.uCySunA, sa); gl.uniform1f(L.uCySunN, suns.length);
  const ao = new Float32Array(ARM_CY_DIRS * 4);
  lk.ao.slice(0, ARM_CY_DIRS).forEach((d, i) => ao.set(d, i * 4));
  gl.uniform4fv(L.uCyAo, ao);
}
// an object's metal mix and normal map kind (cycleslook.metal_info), and its shadow atlas
function armCyBindObj(gl, L, ob, lit){
  if(lit !== 3) return;
  const m = (ARM.litMaps && ARM.litMaps.byId[ob.id]) || {};
  const lk = ARM.cy.look, st = lk.settings;
  const sunsOn = st.bake_surround_diffuse > 0.02 || (m.max_metal || 0) > 0.02;
  gl.uniform4f(L.uCyObj, (m.metal || 0) >= lk.consts.metal_object ? 1 : 0, m.every ? 1 : 0, sunsOn ? 1 : 0,
               m.normal_kind === 'm2' ? -1 : 1);
  const at = ARM.cyAt && ARM.cyAt.get(ob.id);
  gl.uniform1f(L.uCyHasAt, at && at.ready ? 1 : 0);
  if(at && at.ready){
    gl.activeTexture(gl.TEXTURE6); gl.bindTexture(gl.TEXTURE_2D, at.tex); gl.uniform1i(L.uCyAt, 6);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform4fv(L.uCyM1, at.m1); gl.uniform4fv(L.uCyM2, at.m2);
  }
}

/* --- parts: each loose part of a model, numbered, as a vertex attribute ------------- */

function armCyPartsOf(I, n){
  const up = new Int32Array(n).map((_, i) => i);
  const find = i => { while(up[i] !== i){ up[i] = up[up[i]]; i = up[i]; } return i; };
  for(let t = 0; t + 2 < I.length; t += 3){
    const a = find(I[t]), b = find(I[t+1]), c = find(I[t+2]);
    if(a !== b) up[b] = a;
    const a2 = find(a);
    if(a2 !== c) up[c] = a2;
  }
  const ids = new Map(), out = new Float32Array(n);
  for(let v = 0; v < n; v++){
    const r = find(v);
    if(!ids.has(r)) ids.set(r, ids.size);
    out[v] = (ids.get(r) % 250 + 1) / 255;
  }
  return out;
}
// bound for every draw (aPart); a holder is a loaded model or a posed one
function armCyPart(gl, L, holder, I, n){
  if(L.aPart < 0) return;
  if(!holder._cyPart || holder._cyPartGl !== gl){
    const b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, armCyPartsOf(I, n), gl.STATIC_DRAW);
    holder._cyPart = b; holder._cyPartGl = gl;
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, holder._cyPart);
  gl.enableVertexAttribArray(L.aPart); gl.vertexAttribPointer(L.aPart, 1, gl.FLOAT, false, 0, 0);
}

/* --- the shadow atlas ------------------------------------------------------------ */

const ARM_CY_SH_VERT = `
attribute vec3 aPos; attribute float aPart;
uniform mat4 uModel;
uniform vec3 uX, uY, uL;
uniform vec4 uM;            // lo.x, lo.y, scale, zmax
uniform vec2 uZ, uSlot;     // zspan, map size; the slot's corner in the atlas
uniform vec2 uAt;
varying float vD, vPart;
void main(){
  vec3 w = (uModel * vec4(aPos, 1.0)).xyz;
  vec2 f = (vec2(dot(w, uX), dot(w, uY)) - uM.xy) * uM.z + 1.0;
  vD = (uM.w - dot(w, uL)) / uZ.x;
  vPart = aPart;
  gl_Position = vec4((uSlot + f) / uAt * 2.0 - 1.0, vD * 2.0 - 1.0, 1.0);
}`;
const ARM_CY_SH_FRAG = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying float vD, vPart;
void main(){
  vec3 e = fract(vec3(1.0, 255.0, 65025.0) * vD);
  gl_FragColor = vec4(e - e.yzz * vec3(1.0 / 255.0, 1.0 / 255.0, 0.0), vPart);
}`;
function armCyShProg(gl){
  if(ARM.cyShProg && ARM.cyShGl === gl) return ARM.cyShProg;
  const sh = (type, src) => {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, ARM_CY_SH_VERT));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, ARM_CY_SH_FRAG));
  gl.linkProgram(p);
  const loc = {aPos: gl.getAttribLocation(p, 'aPos'), aPart: gl.getAttribLocation(p, 'aPart')};
  for(const n of ['uModel', 'uX', 'uY', 'uL', 'uM', 'uZ', 'uSlot', 'uAt']) loc[n] = gl.getUniformLocation(p, n);
  ARM.cyShProg = {p, loc}; ARM.cyShGl = gl;
  ARM.cyAt = new Map();
  return ARM.cyShProg;
}
const armCyBasis = L => {
  const up = Math.abs(L[1]) < 0.99 ? [0, 1, 0] : [1, 0, 0];
  const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const x = cr(up, L), l = Math.hypot(x[0], x[1], x[2]) || 1;
  const X = x.map(v => v / l);
  return [X, cr(L, X)];
};
// items as armLitShadowItems gives them, with each draw's part holder (part, I, n)
function armCyShadows(gl, items){
  if(!armCyReady() || !items.length) return;
  const lk = ARM.cy.look;
  if(!(lk.settings.bake_shadows > 0)) { for(const {ob} of items){ const a = ARM.cyAt && ARM.cyAt.get(ob.id); if(a) a.ready = false; } return; }
  let prog;
  try{ prog = armCyShProg(gl); }catch(e){ return; }
  const maps = lk.suns.slice(0, ARM_CY_SUNS).map((s, i) => ({L: s.dir, size: ARM_CY_SUN,
    slot: [(i % 4) * ARM_CY_SUN, Math.floor(i / 4) * ARM_CY_SUN]}));
  while(maps.length < ARM_CY_SUNS) maps.push(null);
  lk.ao.slice(0, ARM_CY_DIRS).forEach((d, i) => maps.push({L: d.slice(0, 3), size: ARM_CY_AO,
    slot: [i * ARM_CY_AO, 3 * ARM_CY_SUN]}));
  const P = prog.loc;
  let bound = false;
  for(const {ob, draws, posed} of items){
    const sig = posed ? '' : JSON.stringify([draws.map(d => Array.from(d.model)), lk.suns, lk.settings.bake_shadows]);
    let at = ARM.cyAt.get(ob.id);
    if(at && at.ready && sig && at.sig === sig) continue;
    if(!bound){
      gl.useProgram(prog.p);
      for(let i = 0; i < 8; i++) if(i !== P.aPos && i !== P.aPart) gl.disableVertexAttribArray(i);
      gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND);
      gl.uniform2f(P.uAt, ARM_CY_W, ARM_CY_H);
      bound = true;
    }
    if(!at){
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, ARM_CY_W, ARM_CY_H, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      for(const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST],
                           [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]])
        gl.texParameteri(gl.TEXTURE_2D, k, v);
      const rb = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, ARM_CY_W, ARM_CY_H);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
      at = {tex, fb, rb};
      ARM.cyAt.set(ob.id, at);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, at.fb);
    gl.enable(gl.SCISSOR_TEST);
    const m1 = new Float32Array((ARM_CY_SUNS + ARM_CY_DIRS) * 4), m2 = new Float32Array(m1.length);
    maps.forEach((mp, k) => {
      if(!mp) return;
      const [X, Y] = armCyBasis(mp.L), Ld = mp.L;
      let lx = Infinity, ly = Infinity, hx = -Infinity, hy = -Infinity, lz = Infinity, hz = -Infinity;
      for(const d of draws){
        const each = v => {
          const w = armLitXf(d.model, d.P[v*3], d.P[v*3+1], d.P[v*3+2]);
          const a = w[0]*X[0] + w[1]*X[1] + w[2]*X[2], b = w[0]*Y[0] + w[1]*Y[1] + w[2]*Y[2], z = w[0]*Ld[0] + w[1]*Ld[1] + w[2]*Ld[2];
          if(a < lx) lx = a; if(a > hx) hx = a; if(b < ly) ly = b; if(b > hy) hy = b; if(z < lz) lz = z; if(z > hz) hz = z;
        };
        if(d.I) for(let i = d.bStart; i < d.bStart + d.bCount; i++) each(d.I[i]);
        else for(let v = 0; v < d.P.length / 3; v++) each(v);
      }
      if(!isFinite(lx)) return;
      const span = Math.max(hx - lx, hy - ly, 1e-9), scale = (mp.size - 3) / span, zspan = (hz - lz) * 1.002 + 1e-6;
      m1.set([lx, ly, scale, hz], k * 4); m2.set([zspan, span, mp.slot[0], mp.slot[1]], k * 4);
      gl.viewport(0, 0, ARM_CY_W, ARM_CY_H);
      gl.scissor(mp.slot[0], mp.slot[1], mp.size, mp.size);
      gl.clearColor(1, 1, 1, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.uniform3fv(P.uX, X); gl.uniform3fv(P.uY, Y); gl.uniform3fv(P.uL, Ld);
      gl.uniform4f(P.uM, lx, ly, scale, hz); gl.uniform2f(P.uZ, zspan, mp.size); gl.uniform2fv(P.uSlot, mp.slot);
      for(const d of draws){
        gl.uniformMatrix4fv(P.uModel, false, new Float32Array(d.model));
        gl.bindBuffer(gl.ARRAY_BUFFER, d.pos);
        gl.enableVertexAttribArray(P.aPos); gl.vertexAttribPointer(P.aPos, 3, gl.FLOAT, false, 0, 0);
        armCyPart(gl, P, d.holder, d.partI, d.partN);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, d.idx);
        gl.drawElements(gl.TRIANGLES, d.count, gl.UNSIGNED_SHORT, d.idxStart * 2);
      }
    });
    gl.disable(gl.SCISSOR_TEST);
    Object.assign(at, {m1, m2, sig, ready: true});
  }
  if(bound) gl.bindFramebuffer(gl.FRAMEBUFFER, null);
}

/* --- the shader --------------------------------------------------------------------
   Pasted into armory.js armFrag; cyShade is uLit 3's colour. */
const ARM_CY_GLSL = `
uniform sampler2D uCyEnv, uCyLut, uCyAt;
uniform float uCyRows, uCyView, uCySunN, uCyHasAt;
uniform vec3 uCyLutR;                 // n, log2 low, log2 high
uniform vec4 uCyMix, uCyMix2, uCyObj;  // ambient world shadows floor; surround_diffuse other gloss_from gloss_full; metal_obj every suns_on normal_sign
uniform vec2 uCyAlb[9];
uniform vec4 uCySun[${ARM_CY_SUNS}];
uniform float uCySunA[${ARM_CY_SUNS}];
uniform vec4 uCyAo[${ARM_CY_DIRS}];
uniform vec4 uCyM1[${ARM_CY_SUNS + ARM_CY_DIRS}], uCyM2[${ARM_CY_SUNS + ARM_CY_DIRS}];
varying float vPart;
const float CY_PI = 3.14159265;
vec3 cyLin(vec3 c){ return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }
vec3 cySrgb(vec3 c){ c = clamp(c, 0.0, 1.0); return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
float cyLum(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
// the world's light of one level in a direction of the viewport's space (Blender's equirect)
vec3 cyEnv(float level, vec3 v){
  vec3 b = vec3(-v.x, -v.z, v.y);
  float u = 0.5 - atan(b.y, b.x) / (2.0 * CY_PI);
  float w = 1.0 - acos(clamp(b.z, -1.0, 1.0)) / CY_PI;
  return texture2D(uCyEnv, vec2(u, (level * 32.0 + clamp(w * 32.0, 0.5, 31.5)) / uCyRows)).rgb;
}
// GGX seen straight down the normal, per unit light at cos t: (F0 part, constant part)
vec2 cyGgx(float rough, float c, float widen){
  float a = max(rough, 0.03); a = min(a * a + widen, 1.0);
  c = clamp(c, 0.0, 1.0);
  float ch = sqrt((1.0 + c) * 0.5);
  float q = ch * ch * (a * a - 1.0) + 1.0;
  float d = a * a / (CY_PI * q * q);
  float t2 = c > 0.0 ? (1.0 - c * c) / max(c * c, 1e-8) : 0.0;
  float g = 1.0 / (1.0 + (-1.0 + sqrt(1.0 + a * a * t2)) * 0.5);
  float k = c > 0.0 ? d * g * 0.25 : 0.0;
  float f = pow(1.0 - ch, 5.0);
  return vec2(k * (1.0 - f), k * f);
}
// how much of a map's light reaches this texel past its own part
float cyVis(vec3 L, vec4 m1, vec4 m2, float size, float raw, float taps){
  vec3 up = abs(L.y) < 0.99 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
  vec3 X = normalize(cross(up, L)), Y = cross(L, X);
  vec2 r = (vec2(dot(vPos, X), dot(vPos, Y)) - m1.xy) * m1.z + 1.0;
  float me = (m1.w - dot(vPos, L)) / m2.x;
  float bias = m2.y * (0.004 + 0.03 * (1.0 - clamp(raw, 0.0, 1.0))) / m2.x;
  float seen = 0.0, n = 0.0;
  for(int j = -1; j <= 1; j++) for(int i = -1; i <= 1; i++){
    if(taps < 2.0 && (i != 0 || j != 0)) continue;
    vec2 c = clamp(floor(r + vec2(float(i), float(j))), 0.0, size - 1.0);
    vec4 t = texture2D(uCyAt, (m2.zw + c + 0.5) / vec2(${ARM_CY_W}.0, ${ARM_CY_H}.0));
    float z = dot(t.rgb, vec3(1.0, 1.0 / 255.0, 1.0 / 65025.0));
    seen += (z >= me - bias || abs(t.a - vPart) > 0.002) ? 1.0 : 0.0;
    n += 1.0;
  }
  return seen / n;
}
vec3 cyAgx(vec3 c){
  float N = uCyLutR.x;
  vec3 t = clamp((log2(max(c, vec3(1e-10))) - uCyLutR.y) / (uCyLutR.z - uCyLutR.y), 0.0, 1.0) * (N - 1.0);
  float b0 = floor(t.b), b1 = min(b0 + 1.0, N - 1.0);
  vec2 rg = t.rg + 0.5;
  vec3 a = texture2D(uCyLut, vec2((rg.x + b0 * N) / (N * N), rg.y / N)).rgb;
  vec3 b = texture2D(uCyLut, vec2((rg.x + b1 * N) / (N * N), rg.y / N)).rgb;
  return mix(a, b, t.b - b0);
}
vec3 cyShade(vec4 base, vec2 st, vec3 n){
  vec3 col = cyLin(base.rgb);
  float metal = 0.0, rough = 0.65, ao = 1.0, gloss = 0.0;
  if(uHasS > 0.5){ vec3 s = texture2D(uSTex, st).rgb; metal = s.r; gloss = s.g; rough = 1.0 - s.g; ao = s.b; }
  vec3 alb = col * ao;
  float mx = max(max(alb.r, alb.g), alb.b);
  vec3 tint = mix(mx > 0.0 ? alb / mx : vec3(1.0), vec3(1.0), metal);
  vec3 F0 = mix(0.04 * tint, alb, metal);
  // the specular levels either side of this roughness
  float fr = clamp(rough, 0.0, 1.0) * 8.0, k0 = floor(fr), f = fr - k0, k1 = min(k0 + 1.0, 8.0);
  vec2 A = vec2(0.0);
  for(int i = 0; i < 9; i++){ if(float(i) == k0) A += uCyAlb[i] * (1.0 - f); if(float(i) == k1) A += uCyAlb[i] * f; }
  float ms = 1.0 / max(A.x + A.y, 1e-3);          // multiscatter: white metal keeps all its light
  vec3 specAlb = (F0 * A.x + A.y) * ms;
  float dw = (1.0 - metal) * (1.0 - (0.04 * A.x + A.y) * ms);
  // the world pass: the world and the white fill, shadowed by the part itself
  vec3 sp = mix(cyEnv(1.0 + 2.0 * k0, n), cyEnv(1.0 + 2.0 * k1, n), f) * F0
          + mix(cyEnv(2.0 + 2.0 * k0, n), cyEnv(2.0 + 2.0 * k1, n), f);
  vec3 world = alb * cyEnv(0.0, n) * dw + sp * ms + uCyMix.x * (alb * dw + specAlb);
  if(uCyHasAt > 0.5){
    float num = 0.0, den = 0.0;
    for(int i = 0; i < ${ARM_CY_DIRS}; i++){
      vec3 d = uCyAo[i].xyz;
      float w = uCyAo[i].w * max(dot(n, d), 0.0);
      if(w <= 0.0) continue;
      num += w * cyVis(d, uCyM1[${ARM_CY_SUNS} + i], uCyM2[${ARM_CY_SUNS} + i], ${ARM_CY_AO}.0, dot(n, d), 1.0);
      den += w;
    }
    float occ = den > 0.0 ? num / den : 1.0;
    world *= 1.0 - uCyMix.z * (1.0 - occ);
  }
  // the suns pass
  vec3 sun = vec3(0.0);
  for(int i = 0; i < ${ARM_CY_SUNS}; i++){
    if(float(i) >= uCySunN) break;
    vec3 L = uCySun[i].xyz;
    float nl = dot(n, L);
    if(nl <= 0.0) continue;
    vec2 g = cyGgx(rough, nl, 0.5 * uCySunA[i]);
    vec3 lit = (alb / CY_PI * nl * dw + (F0 * g.x + g.y) * ms) * uCySun[i].w;
    float vis = uCyHasAt > 0.5 ? cyVis(L, uCyM1[i], uCyM2[i], ${ARM_CY_SUN}.0, nl, 9.0) : 1.0;
    sun += lit * (1.0 - uCyMix.z * (1.0 - vis));
  }
  // metal: the brighter of suns and world and some of the other; the rest the world
  float glossy = clamp((gloss - uCyMix2.z) / (uCyMix2.w - uCyMix2.z), 0.0, 1.0);
  float weight = max(metal + (1.0 - metal) * uCyMix2.x, uCyObj.x * (uCyObj.y > 0.5 ? 1.0 : glossy));
  vec3 res = world;
  if(uCyObj.z > 0.5){
    vec3 b = world * uCyMix.y;
    float la = pow(cyLum(sun), 4.0), lb = pow(cyLum(b), 4.0);
    float pick = la / max(la + lb, 1e-12);
    vec3 mixed = pick * (sun + uCyMix2.y * b) + (1.0 - pick) * (b + uCyMix2.y * sun);
    res = mixed * weight + world * (1.0 - weight);
  }
  res = max(res, clamp(col, 0.0, 1.0) * uCyMix.w);
  return uCyView > 0.5 ? cyAgx(res) : cySrgb(res);
}`;
