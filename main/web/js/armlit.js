/* Armory Studio - Pre-render lighting.

   A lit colour texture for each colour texture the chosen objects wear: the
   colour, its spec map (red metal, green gloss, blue ambient occlusion) and
   its normal map, with an ambient light and a key light painted in, on the
   object's own UVs. Not the export's bake, which packs the sheets: this one
   changes what an object wears, and the export then packs that.

   The work is armlit.py on the server. The viewport draws the bake's light
   light live, its own arithmetic in the shader (armory.js armFrag): the colour,
   spec and normal maps the bake would use (armlit.maps), the ambient light,
   the key light and up to three more (sun or point, as the card maker's),
   the highlights, and each light's soft shadow from a shadow map made as the
   bake makes it (armLitShadows). So a slider shows what it does as it moves.
   After a bake the objects are drawn with that texture and no light over it,
   until a slider moves again. 2026-11-25: Render mode, in the viewport bar,
   draws every object that way with the panel closed too.

   On an object: o.sheet is the lit texture, o.lit = {src, settings} what it
   wore before (null: its source's own) and how it was lit, so a second bake
   starts from the source and Remove puts it back. */

// bake: 'light' (Light Bake, armlit.py) or 'pbr' (PBR Bake, Keyforce Tools' Cycles bake in Blender)
const ARM_LIT_DEFAULT = {ambient: 0.8, key: true, direction: 30, height: 50, softness: 0.5,
                         strength: 0.5, shadows: 0.5, flip_green: false, lights: [], bake: 'light', unstack: false};
// 2026-11-25: the extra lights (armlit.LAMP_RANGES): a new one, and each slider
const ARM_LIT_LAMPS_MAX = 3;
const ARM_LIT_LAMP = {type: 'sun', direction: -120, height: 25, strength: 0.5, distance: 2};
const ARM_LIT_LAMP_RANGES = {direction: [-180, 180, 1], height: [-90, 90, 1], strength: [0, 3, 0.01], distance: [0.2, 10, 0.1]};
// what a point light's distance is measured from (armlit.LAMP_CENTRE): a metre above the origin
const ARM_LIT_CENTRE = [0, 1, 0];
// each slider: its range and step
const ARM_LIT_RANGES = {ambient: [0, 2, 0.01], direction: [-180, 180, 1], height: [-90, 90, 1],
                        softness: [0, 1, 0.01], strength: [0, 3, 0.01], shadows: [0, 1, 0.01]};

function armLit(){ return ARM.lit = ARM.lit || {open: false, live: true, busy: false}; }
// 2026-11-25: the key light is built in and the normal map is read one way:
// no switch for either any more (Flip green was for TpacTool's exports)
function armLitOpts(){
  const s = (state.settings || {}).armory_lit;
  return Object.assign({}, ARM_LIT_DEFAULT, s && typeof s === 'object' ? s : {}, {key: true, flip_green: false});
}
// quiet: a slider on its way (drawn, not saved yet)
function armLitSet(k, v, quiet){
  const o = armLitOpts();
  o[k] = v;
  state.settings = state.settings || {};
  state.settings.armory_lit = o;
  armLit().live = true;
  if(!quiet) api.post('/api/settings', {armory_lit: o}).catch(() => {});
  const out = typeof document !== 'undefined' && document.getElementById('armLitVal_' + k);
  if(out) out.textContent = v;
  armFrame();
}
/* --- 2026-11-25: the maps the bake would use, for the viewport's live light ------
   armlit.maps on the server, asked again whenever what the objects wear
   changes. Until 2026-11-25 the viewport drew a small bake from the server
   instead (armlit.bake_objects preview), which came late and blurred. */
// an object the bake can light: its colour texture found
function armLitMapsOf(ob){
  const m = ARM.litMaps && ARM.litMaps.byId[ob.id];
  return m && m.colour ? m : null;
}
function armLitMapsCheck(){
  const p = armProj();
  const sig = JSON.stringify([(p.objects || []).map(o => [o.id, o.sheet || '', o.lit ? o.lit.src || '' : '',
    (o.src || []).map(pc => pc.asset + ':' + pc.group)]), (p.assets || []).length]);
  const k = ARM.litMaps = ARM.litMaps || {sig: '', byId: {}, busy: false};
  if(k.sig === sig || k.busy) return;
  k.busy = true;
  api.post('/api/armory/lit_maps', {project: p, ids: (p.objects || []).map(o => o.id)})
    .then(r => {
      k.sig = sig;
      k.byId = r && !r.error ? r : {};
      for(const m of Object.values(k.byId)) for(const path of [m.colour, m.spec, m.normal]) if(path) ARM.sheetAllowed.add(path);
    })
    .catch(() => { k.sig = sig; })
    .finally(() => { k.busy = false; armFrame(); });
}
// the selected objects, or every visible one when none is
function armLitTargets(){
  const sel = armSelected();
  return sel.length ? sel : armVisibleObjects();
}
function armLitToggle(){
  const l = armLit();
  l.open = !l.open;
  l.live = true;
  // 2026-11-25: opened, the view is the bake's: Render mode ticks itself
  if(l.open && !armRenderOn()){
    armRenderToggle(true);
    if(typeof armPaintBar === 'function') armPaintBar();
  }
  armPaintObjects();
  armFrame();
}

/* --- Render mode (2026-11-25) ------------------------------------------------
   The viewport bar's switch: every object the bake can light is drawn, live,
   under the light the chosen bake will paint in (Light Bake: these settings;
   PBR Bake: the Cycles bake's look, armcycles.js), and one already baked with
   its baked texture as it is. Off, the viewport's own light. */
const armRenderOn = () => (state.settings || {}).armory_render_mode === true;
function armRenderToggle(on){
  state.settings = state.settings || {};
  state.settings.armory_render_mode = !!on;
  api.post('/api/settings', {armory_render_mode: !!on}).catch(() => {});
  armFrame();
}
function armLitBarHtml(){
  return `<label class="armcheck" title="${esc(tt('armory.render_mode_title'))}"><input type="checkbox"${armRenderOn() ? ' checked' : ''}
    onchange="armRenderToggle(this.checked)"> ${tt('armory.render_mode')}</label>`;
}

/* --- what the viewport draws ------------------------------------------------- */

const armLitPbr = () => armLitOpts().bake === 'pbr';
// PBR Bake's light is measured in Blender: asked for only once it is shown
const armLitPbrWanted = () => armLitPbr() && (armRenderOn() || armLit().open);
// 0: the viewport's own light; 1: Light Bake's light, live; 2: the baked texture
// as it is; 3: PBR Bake's (the Cycles look), live, once Blender has measured it
function armLitMode(ob){
  const l = armLit();
  const live = () => armLitPbr() ? (typeof armCyReady === 'function' && armCyReady() ? 3 : 0) : 1;
  if(l.open && armLitTargets().includes(ob)) return ob.lit && !l.live ? 2 : live();
  // 2026-11-25: baked, its texture as it is, Render mode or not: the light is in it
  if(ob.lit) return 2;
  if(!armRenderOn()) return 0;
  return armLitMapsOf(ob) ? live() : 0;
}
// the sheet an object is drawn with: under the live light, the colour the
// bake starts from (what it wore before a bake)
function armLitSheetOf(ob){
  const mode = armLitMode(ob);
  if(mode !== 1 && mode !== 3) return ob.sheet || null;
  const m = ARM.litMaps && ARM.litMaps.byId[ob.id];
  if(m && m.colour) return m.colour;
  return ob.lit ? (ob.lit.src || null) : (ob.sheet || null);
}
// towards a light at (direction, height) in degrees, in the bake's space
function armLitToward(direction, height){
  const a = direction * Math.PI / 180, h = height * Math.PI / 180;
  return [Math.cos(h) * Math.sin(a), Math.sin(h), Math.cos(h) * Math.cos(a)];
}
/* Every light that shines, as armlit.lamps has them: the key light, then the
   extra ones, in the page's space (the viewport mirrors x: ARM_MIRROR). dir
   points towards the light (a point's from ARM_LIT_CENTRE: its shadow's). */
function armLitLamps(){
  const o = armLitOpts(), out = [];
  const m = v => [-v[0], v[1], v[2]];
  if(o.key && o.strength > 0) out.push({dir: m(armLitToward(o.direction, o.height)), strength: o.strength, point: false, pos: [0, 0, 0]});
  for(const x of (Array.isArray(o.lights) ? o.lights : []).slice(0, ARM_LIT_LAMPS_MAX)){
    if(!(x.strength > 0)) continue;
    const d = armLitToward(x.direction, x.height), point = x.type === 'point';
    out.push({dir: m(d), strength: x.strength, point,
              pos: point ? m(ARM_LIT_CENTRE.map((c, i) => c + d[i] * x.distance)) : [0, 0, 0]});
  }
  return out;
}
// the light's uniforms for a frame (armRender)
function armLitUniforms(gl, L){
  const o = armLitOpts(), lamps = armLitLamps().slice(0, 4);
  const dir = new Float32Array(12), pos = new Float32Array(12), pt = new Float32Array(4), str = new Float32Array(4);
  lamps.forEach((x, i) => { dir.set(x.dir, i * 3); pos.set(x.pos, i * 3); pt[i] = x.point ? 1 : 0; str[i] = x.strength; });
  gl.uniform1f(L.uLitAmb, o.ambient);
  gl.uniform1f(L.uLitSoft, o.softness);
  gl.uniform1f(L.uLitSh, o.shadows);
  gl.uniform1f(L.uKN, lamps.length);
  gl.uniform3fv(L.uKDir, dir); gl.uniform3fv(L.uKPos, pos);
  gl.uniform1fv(L.uKPt, pt); gl.uniform1fv(L.uKStr, str);
}

/* An object under the live light: its spec and normal maps, and its shadow
   atlas, bound for the shader (armory.js bindTex). The colour is armLitSheetOf. */
function armLitBindMaps(gl, L, ob, lit){
  const m = (lit === 1 || lit === 3) && ARM.litMaps ? ARM.litMaps.byId[ob.id] : null;
  const spec = m && m.spec ? armSheetTex(m.spec) : null;
  const nrm = m && m.normal ? armSheetTex(m.normal) : null;
  gl.uniform1f(L.uHasS, spec ? 1 : 0);
  gl.uniform1f(L.uLitN, nrm ? 1 : 0);
  gl.uniform1f(L.uFlipG, lit === 1 && armLitOpts().flip_green ? -1 : 1);
  if(spec){ gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, spec); gl.uniform1i(L.uSTex, 2); }
  if(nrm){ gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, nrm); gl.uniform1i(L.uNTex, 1); }
  const sh = lit === 1 && ARM.litShadow ? ARM.litShadow.get(ob.id) : null;
  gl.uniform1f(L.uHasSh, sh && sh.ready ? 1 : 0);
  if(sh && sh.ready){
    gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, sh.tex); gl.uniform1i(L.uShTex, 3);
    gl.uniform3fv(L.uShX, sh.x); gl.uniform3fv(L.uShY, sh.y);
    gl.uniform2fv(L.uShLo, sh.lo);
    gl.uniform1fv(L.uShScale, sh.scale); gl.uniform1fv(L.uShSpan, sh.span);
    gl.uniform1fv(L.uShZmax, sh.zmax); gl.uniform1fv(L.uShZspan, sh.zspan);
  }
  gl.activeTexture(gl.TEXTURE0);
}

/* --- each light's shadow, as armlit._visible makes it ------------------------------
   Per object, shadowed by itself only: its triangles drawn as seen from each
   light into a 512 x 512 slot of the object's 1024 x 1024 atlas (four
   slots: the key light and three more), each cell holding the nearest to
   the light, its depth packed into the four bytes of a texel. A slot spans
   the object across its light, with a cell of margin, as the bake's map does.
   2026-11-25: made again only when the object, its pose or a light changes
   (until then every frame, which made the viewport crawl). */
const ARM_LIT_SHADOW = 512;
const ARM_LIT_SH_VERT = `
attribute vec3 aPos;
uniform mat4 uModel;
uniform vec3 uShX, uShY, uLitDir;
uniform vec2 uShLo;
uniform float uShScale, uShZmax, uShZspan;
varying float vD;
void main(){
  vec3 w = (uModel * vec4(aPos, 1.0)).xyz;
  vec2 f = (vec2(dot(w, uShX), dot(w, uShY)) - uShLo) * uShScale + 1.0;
  vD = (uShZmax - dot(w, uLitDir)) / uShZspan;
  gl_Position = vec4(f / ${ARM_LIT_SHADOW / 2}.0 - 1.0, vD * 2.0 - 1.0, 1.0);
}`;
const ARM_LIT_SH_FRAG = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying float vD;
void main(){
  vec4 e = fract(vec4(1.0, 255.0, 65025.0, 16581375.0) * vD);
  gl_FragColor = e - e.yzww * vec4(1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0, 0.0);
}`;
function armLitShProg(gl){
  if(ARM.litShProg && ARM.litShGl === gl) return ARM.litShProg;
  const sh = (type, src) => {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, ARM_LIT_SH_VERT));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, ARM_LIT_SH_FRAG));
  gl.linkProgram(p);
  const loc = {aPos: gl.getAttribLocation(p, 'aPos')};
  for(const n of ['uModel', 'uShX', 'uShY', 'uLitDir', 'uShLo', 'uShScale', 'uShZmax', 'uShZspan'])
    loc[n] = gl.getUniformLocation(p, n);
  ARM.litShProg = {p, loc}; ARM.litShGl = gl;
  ARM.litShadow = new Map();
  return ARM.litShProg;
}
const armLitXf = (m, x, y, z) => [m[0] * x + m[4] * y + m[8] * z + m[12],
                                  m[1] * x + m[5] * y + m[9] * z + m[13],
                                  m[2] * x + m[6] * y + m[10] * z + m[14]];
// a buffer's own number, so a signature sees a model uploaded again
let ARM_LIT_BUFN = 0;
const armLitBufId = b => b ? (b._litId || (b._litId = ++ARM_LIT_BUFN)) : 0;
// items: [{ob, draws: [{model, pos, idx (buffers), idxStart, count, P (positions), I (indices) or null, bStart, bCount}], posed}]
function armLitShadows(gl, items){
  const o = armLitOpts(), lamps = armLitLamps().slice(0, 4);
  if(!(o.shadows > 0) || !lamps.length || !items.length) return;
  let prog;
  try{ prog = armLitShProg(gl); }catch(e){ return; }
  const cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const un = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return v.map(c => c / l); };
  const bases = lamps.map(lp => {
    const L = lp.dir, up = Math.abs(L[1]) < 0.99 ? [0, 1, 0] : [1, 0, 0];
    const X = un(cr(up, L));
    return {L, X, Y: cr(L, X)};
  });
  const lampSig = JSON.stringify(bases.map(b => b.L));
  const N = ARM_LIT_SHADOW, P = prog.loc;
  let bound = false;
  for(const {ob, draws, posed} of items){
    // a posed model moves every frame; anything else only when its place, its buffers or a light does
    const sig = posed ? '' : lampSig + JSON.stringify(draws.map(d => [Array.from(d.model), armLitBufId(d.pos), armLitBufId(d.idx), d.idxStart, d.count]));
    let sh = ARM.litShadow.get(ob.id);
    if(sh && sh.ready && sig && sh.sig === sig) continue;
    if(!bound){
      gl.disable(gl.SCISSOR_TEST); gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND);
      gl.useProgram(prog.p);
      // only aPos is read here: an array left on by the viewport's pass is not checked against these draws
      for(let i = 0; i < 8; i++) if(i !== P.aPos) gl.disableVertexAttribArray(i);
      bound = true;
    }
    if(!sh){
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2 * N, 2 * N, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      for(const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST],
                           [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]])
        gl.texParameteri(gl.TEXTURE_2D, k, v);
      const rb = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, 2 * N, 2 * N);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
      sh = {tex, fb, rb, ready: false};
      ARM.litShadow.set(ob.id, sh);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, sh.fb);
    gl.viewport(0, 0, 2 * N, 2 * N);
    gl.clearColor(1, 1, 1, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const x = new Float32Array(12), y = new Float32Array(12), lo = new Float32Array(8);
    const scale = new Float32Array(4), span = new Float32Array(4), zmax = new Float32Array(4), zspan = new Float32Array(4).fill(1);
    bases.forEach(({L, X, Y}, k) => {
      // the object's extent across this light and along it
      let lx = Infinity, ly = Infinity, hx = -Infinity, hy = -Infinity, lz = Infinity, hz = -Infinity;
      for(const d of draws){
        const each = v => {
          const w = armLitXf(d.model, d.P[v * 3], d.P[v * 3 + 1], d.P[v * 3 + 2]);
          const a = w[0] * X[0] + w[1] * X[1] + w[2] * X[2], b = w[0] * Y[0] + w[1] * Y[1] + w[2] * Y[2];
          const z = w[0] * L[0] + w[1] * L[1] + w[2] * L[2];
          if(a < lx) lx = a; if(a > hx) hx = a; if(b < ly) ly = b; if(b > hy) hy = b; if(z < lz) lz = z; if(z > hz) hz = z;
        };
        if(d.I) for(let i = d.bStart; i < d.bStart + d.bCount; i++) each(d.I[i]);
        else for(let v = 0; v < d.P.length / 3; v++) each(v);
      }
      if(!isFinite(lx)) return;
      const sp = Math.max(hx - lx, hy - ly, 1e-9);
      // depth 0 the nearest the light, a hair under 1 the farthest: a packed 1.0 reads 0
      x.set(X, k * 3); y.set(Y, k * 3); lo.set([lx, ly], k * 2);
      span[k] = sp; scale[k] = (N - 3) / sp; zmax[k] = hz; zspan[k] = (hz - lz) * 1.002 + 1e-6;
      gl.viewport((k % 2) * N, Math.floor(k / 2) * N, N, N);
      gl.uniform3fv(P.uShX, X); gl.uniform3fv(P.uShY, Y); gl.uniform3fv(P.uLitDir, L);
      gl.uniform2fv(P.uShLo, [lx, ly]); gl.uniform1f(P.uShScale, scale[k]);
      gl.uniform1f(P.uShZmax, zmax[k]); gl.uniform1f(P.uShZspan, zspan[k]);
      for(const d of draws){
        gl.uniformMatrix4fv(P.uModel, false, new Float32Array(d.model));
        gl.bindBuffer(gl.ARRAY_BUFFER, d.pos);
        gl.enableVertexAttribArray(P.aPos); gl.vertexAttribPointer(P.aPos, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, d.idx);
        gl.drawElements(gl.TRIANGLES, d.count, gl.UNSIGNED_SHORT, d.idxStart * 2);
      }
    });
    Object.assign(sh, {x, y, lo, scale, span, zmax, zspan, sig, ready: true});
  }
  if(bound) gl.bindFramebuffer(gl.FRAMEBUFFER, null);
}

/* --- the panel ---------------------------------------------------------------- */

function armLitHtml(){
  const l = armLit(), o = armLitOpts(), objs = armLitTargets(), pbr = o.bake === 'pbr';
  const lit = objs.filter(x => x.lit);
  const range = (k, label, title) => { const r = ARM_LIT_RANGES[k]; return `<label class="armrange" title="${esc(title || '')}">
      <span>${label} <span class="count" id="armLitVal_${k}">${o[k]}</span></span>
      <input type="range" min="${r[0]}" max="${r[1]}" step="${r[2]}" value="${o[k]}"
        oninput="armLitSet('${k}', +this.value, true)" onchange="armLitSet('${k}', +this.value)"></label>`; };
  const kind = (k, label, title) => `<button class="mini${o.bake === k ? ' on' : ''}" title="${esc(tt(title))}"${l.busy ? ' disabled' : ''}
      onclick="armLitSet('bake', '${k}'); armPaintObjects()">${tt(label)}</button>`;
  const light = `<div class="count armnote">${tt('armory.lit_intro')}</div>
    <div class="armpropsrow">${range('ambient', tt('armory.lit_ambient'), tt('armory.lit_ambient_title'))}</div>
    <div class="armpropsrow">${range('direction', tt('armory.lit_direction'), tt('armory.lit_direction_title'))}
      ${range('height', tt('armory.lit_height'), tt('armory.lit_height_title'))}</div>
    <div class="armpropsrow">${range('strength', tt('armory.strength'))}
      ${range('softness', tt('armory.lit_softness'), tt('armory.lit_softness_title'))}</div>
    <div class="armpropsrow">${range('shadows', tt('armory.lit_shadows'), tt('armory.lit_shadows_title'))}</div>
    ${armLitLampsHtml(o)}
    <div class="armpropsrow"><label class="armcheck" title="${esc(tt('armory.lit_unstack_title'))}"><input type="checkbox"${o.unstack ? ' checked' : ''}
      onchange="armLitSet('unstack', this.checked)"> ${tt('armory.lit_unstack')}</label></div>
    <div class="count armnote">${tt('armory.lit_live_note')}</div>`;
  const cy = ARM.cy || {};
  const pbrBody = `<div class="count armnote">${tt('armory.lit_pbr_intro')}</div>
    ${cy.err ? `<div class="count w-bad">${esc(tt('armory.cy_look_err', {why: cy.err}))}</div>` : cy.busy || !cy.ready ? `<div class="count">${tt('armory.cy_measuring')}</div>` : ''}
    ${armLitKfHtml(l.busy)}`;
  return `<div class="armlit">
    <div class="armsect">${tt('armory.lit')}</div>
    <div class="armpropsrow">${kind('light', 'armory.lit_light_bake', 'armory.lit_light_bake_title')}${kind('pbr', 'armory.lit_pbr_bake', 'armory.lit_pbr_bake_title')}</div>
    ${pbr ? pbrBody : light}
    <div class="armpropsrow"><span class="count">${ttN('armory.opt_scope', objs.length)}</span><span style="flex:1"></span>
      ${lit.length ? `<button class="mini" onclick="armLitRemove()" title="${esc(tt('armory.lit_remove_title'))}">${tt('armory.lit_remove')}</button>` : ''}
      <button class="primary" id="armLitGo" onclick="${pbr ? 'armLitCycles()' : 'armLitRun()'}"${objs.length && !l.busy ? '' : ' disabled'}>${l.busy ? tt('armory.working') : tt('armory.lit_bake')}</button></div>
    ${l.cycles ? `<div class="armpropsrow"><span class="count" id="armLitCycles" role="status">${l.cycles.pct}% <progress max="100" value="${l.cycles.pct}"></progress> ${esc(l.cycles.status || '')}</span>
      <span style="flex:1"></span>
      ${l.cycles.job ? `<button class="mini" onclick="armLitCyclesStop()">${tt('armory.kf_stop')}</button>` : ''}</div>` : ''}
  </div>`;
}

/* PBR Bake's settings: the Manual Bake settings of the TpacTool export dialog
   (kfOpts().adv, keyforce.ADVANCED), edited here too. The schema is asked of
   the server once. A change is drawn as soon as the look is measured again. */
function armLitKfHtml(busy){
  const k = ARM.kfSchema = ARM.kfSchema || {fields: null, asking: false};
  if(!k.fields){
    if(!k.asking){
      k.asking = true;
      api.post('/api/armory/keyforce/blender', {}).then(r => { k.fields = r.settings || []; })
        .catch(() => { k.fields = []; }).finally(() => { k.asking = false; armPaintObjects(); });
    }
    return '';
  }
  const adv = kfOpts().adv || {}, dis = busy ? ' disabled' : '';
  const field = f => {
    const [label, title] = KF_LABELS[f.key] || [f.key, ''];
    const v = f.key in adv ? adv[f.key] : f.default;
    const t = esc(title ? tt(title) : '');
    if(f.kind === 'bool') return `<label class="armcheck" title="${t}"><input type="checkbox"${v ? ' checked' : ''}${dis}
        onchange="armLitKfSet('${f.key}', this.checked)"> ${tt(label)}</label>`;
    if(f.kind === 'enum') return `<label title="${t}">${tt(label)} <select${dis} onchange="armLitKfSet('${f.key}', this.value)">
        ${f.low.map(c => `<option value="${c}"${c === v ? ' selected' : ''}>${KF_CHOICES[c] ? tt(KF_CHOICES[c]) : c}</option>`).join('')}</select></label>`;
    return `<label class="armrange" title="${t}"><span>${tt(label)} <span class="count" id="armLitKf_${f.key}">${v}</span></span>
        <input type="range" min="${f.low}" max="${f.high}" step="${f.step}" value="${v}"${dis}
        oninput="armLitKfSet('${f.key}', +this.value, true)" onchange="armLitKfSet('${f.key}', +this.value)"></label>`;
  };
  return Object.keys(KF_GROUPS).map(g => `<div class="armsect">${tt(KF_GROUPS[g])}</div>
      <div class="armpropsrow" style="flex-wrap:wrap">${k.fields.filter(f => f.group === g).map(field).join('')}</div>`).join('')
    + (Object.keys(adv).length && !busy ? `<div class="armpropsrow"><span style="flex:1"></span><button class="mini" onclick="armLitKfReset()">${tt('armory.kf_reset')}</button></div>` : '');
}
// quiet: a slider on its way (shown, not saved yet)
function armLitKfSet(key, v, quiet){
  const o = kfOpts();
  o.adv = Object.assign({}, o.adv || {}, {[key]: v});
  state.settings = state.settings || {};
  state.settings.keyforce_bake = o;
  const out = typeof document !== 'undefined' && document.getElementById('armLitKf_' + key);
  if(out) out.textContent = v;
  if(quiet) return;
  api.post('/api/settings', {keyforce_bake: o}).catch(() => {});
  armLit().live = true;
  armFrame();
}
function armLitKfReset(){
  const o = kfOpts();
  o.adv = {};
  state.settings.keyforce_bake = o;
  api.post('/api/settings', {keyforce_bake: o}).catch(() => {});
  armPaintObjects();
  armFrame();
}

/* 2026-11-25: up to three more lights, each a sun or a point, as the unit card
   maker's are; the bake and the live light use them both (armlit.lamps). */
function armLitLampsHtml(o){
  const lamps = Array.isArray(o.lights) ? o.lights : [];
  const range = (i, k, label, x) => { const r = ARM_LIT_LAMP_RANGES[k]; return `<label class="armrange">
      <span>${label} <span class="count" id="armLitLamp_${i}_${k}">${x[k]}</span></span>
      <input type="range" min="${r[0]}" max="${r[1]}" step="${r[2]}" value="${x[k]}"
        oninput="armLitLamp(${i}, '${k}', +this.value, true)" onchange="armLitLamp(${i}, '${k}', +this.value)"></label>`; };
  return lamps.map((x, i) => `<div class="armlitlamp">
      <div class="armpropsrow"><b>${tt('cards.gen_light_n', {n: i + 2})}</b>
        <select onchange="armLitLamp(${i}, 'type', this.value); armPaintObjects()">${['sun', 'point'].map(k =>
          `<option value="${k}"${x.type === k ? ' selected' : ''}>${tt(k === 'sun' ? 'cards.gen_light_sun' : 'cards.gen_light_point')}</option>`).join('')}</select>
        <span style="flex:1"></span><button class="mini" title="${esc(tt('cards.gen_light_remove'))}" onclick="armLitLampRemove(${i})">✕</button></div>
      <div class="armpropsrow">${range(i, 'direction', tt('armory.lit_direction'), x)}${range(i, 'height', tt('armory.lit_height'), x)}</div>
      <div class="armpropsrow">${range(i, 'strength', tt('armory.strength'), x)}${x.type === 'point'
        ? range(i, 'distance', `<span title="${esc(tt('armory.lit_distance_title'))}">${tt('armory.lit_distance')}</span>`, x) : ''}</div></div>`).join('')
    + (lamps.length < ARM_LIT_LAMPS_MAX ? `<div class="armpropsrow"><button class="mini" onclick="armLitLampAdd()">${tt('cards.gen_light_add')}</button></div>` : '');
}
function armLitLamps_(){ return (Array.isArray(armLitOpts().lights) ? armLitOpts().lights : []).map(x => Object.assign({}, x)); }
function armLitLampAdd(){
  const lamps = armLitLamps_();
  if(lamps.length >= ARM_LIT_LAMPS_MAX) return;
  armLitSet('lights', [...lamps, Object.assign({}, ARM_LIT_LAMP)]);
  armPaintObjects();
}
function armLitLampRemove(i){
  armLitSet('lights', armLitLamps_().filter((_, k) => k !== i));
  armPaintObjects();
}
// quiet: a slider on its way (drawn, not saved yet)
function armLitLamp(i, k, v, quiet){
  const lamps = armLitLamps_();
  if(!lamps[i]) return;
  lamps[i][k] = v;
  armLitSet('lights', lamps, quiet);
  const out = typeof document !== 'undefined' && document.getElementById(`armLitLamp_${i}_${k}`);
  if(out) out.textContent = v;
}

/* --- a TpacTool export through Blender (keyforce.py) -------------------------
   Keyforce Tools' own Cycles bake, in a hidden Blender: an export folder, its
   LOD and a size in, one <source texture>.png per colour texture out, in
   <folder>/Pre-rendered. The dialog polls the job once a second. */

let KF = null;               // {root, lod, size, adv, glb, job, st: last status, blender, schema, open, timer}

// keyforce.ADVANCED's keys: what each is called and what it does
const KF_LABELS = {
  world: ['armory.kf_s_world', 'armory.kf_s_world_title'],
  bake_ambient: ['armory.kf_s_ambient', 'armory.kf_s_ambient_title'],
  bake_world: ['armory.kf_s_world_metal', 'armory.kf_s_world_metal_title'],
  bake_surround: ['armory.kf_s_surround', 'armory.kf_s_surround_title'],
  bake_surround_diffuse: ['armory.kf_s_surround_diffuse', 'armory.kf_s_surround_diffuse_title'],
  bake_tilt: ['armory.kf_s_tilt', 'armory.kf_s_tilt_title'],
  bake_key: ['armory.kf_s_key', 'armory.kf_s_key_title'],
  bake_azimuth: ['armory.lit_direction', 'armory.kf_s_azimuth_title'],
  bake_elevation: ['armory.lit_height', 'armory.lit_height_title'],
  bake_soft: ['armory.lit_softness', 'armory.kf_s_soft_title'],
  bake_shadows: ['armory.lit_shadows', 'armory.kf_s_shadows_title'],
  bake_floor: ['armory.kf_s_floor', 'armory.kf_s_floor_title'],
  bake_samples: ['armory.kf_s_samples', 'armory.kf_s_samples_title'],
  bake_margin: ['armory.kf_s_margin', 'armory.kf_s_margin_title'],
  bake_denoise: ['armory.kf_s_denoise', 'armory.kf_s_denoise_title'],
  bake_indirect: ['armory.kf_s_indirect', 'armory.kf_s_indirect_title'],
  bake_view: ['armory.kf_s_view', 'armory.kf_s_view_title'],
  match: ['armory.kf_s_match', 'armory.kf_s_match_title'],
  precision: ['armory.kf_s_precision', 'armory.kf_s_precision_title'],
  tolerance: ['armory.kf_s_tolerance', 'armory.kf_s_tolerance_title'],
  into_tile: ['armory.kf_s_into_tile', 'armory.kf_s_into_tile_title']};
const KF_GROUPS = {light: 'armory.kf_g_light', quality: 'armory.kf_g_quality', parts: 'armory.kf_g_parts'};
const KF_CHOICES = {PREVIEW: 'armory.kf_c_preview', CITY: 'armory.kf_c_city', COURTYARD: 'armory.kf_c_courtyard',
  FOREST: 'armory.kf_c_forest', INTERIOR: 'armory.kf_c_interior', NIGHT: 'armory.kf_c_night',
  STUDIO: 'armory.kf_c_studio', SUNRISE: 'armory.kf_c_sunrise', SUNSET: 'armory.kf_c_sunset',
  UV: 'armory.kf_c_uv', SHAPE: 'armory.kf_c_shape', EXACT: 'armory.kf_c_exact'};

function kfOpts(){
  const s = (state.settings || {}).keyforce_bake;
  return Object.assign({lod: 0, size: 2048, adv: {}, glb: true}, s && typeof s === 'object' ? s : {});
}
async function kfOpen(){
  const o = kfOpts();
  KF = {root: o.root || '', lod: o.lod, size: o.size, adv: Object.assign({}, o.adv), glb: o.glb !== false,
        job: null, st: null, blender: null, schema: [], open: false, timer: 0};
  document.getElementById('modal').className = 'modal wide';
  document.getElementById('overlay').classList.add('open');
  kfRender();
  let r;
  try{ r = await api.post('/api/armory/keyforce/blender', {}); }catch(e){ r = {path: ''}; }
  if(!KF) return;
  KF.blender = r.path || '';
  KF.schema = r.settings || [];
  kfRender();
}
function kfKeep(){
  state.settings = state.settings || {};
  state.settings.keyforce_bake = {root: KF.root, lod: KF.lod, size: KF.size, adv: KF.adv, glb: KF.glb};
  api.post('/api/settings', {keyforce_bake: state.settings.keyforce_bake}).catch(() => {});
}
async function kfBrowse(){
  let r;
  try{ r = await api.post('/api/browse_folder', {title: tt('armory.kf_pick_title'), dir: KF.root}); }
  catch(e){ toast(errText(e), 6000); return; }
  if(!KF || !r || !r.path) return;
  KF.root = r.path;
  kfKeep();
  kfRender();
}
async function kfStart(){
  if(!KF || KF.job || !KF.root) return;
  kfKeep();
  let r;
  try{ r = await api.post('/api/armory/keyforce/start', {root: KF.root, lod: KF.lod, size: KF.size,
                                                          settings: KF.adv, glb: KF.glb}); }
  catch(e){ r = {error: '' + e}; }
  if(!KF) return;
  if(r.error){ toast(r.error, 8000); return; }
  KF.job = r.job;
  KF.st = {running: true, fraction: 0, status: '', out: r.out};
  kfRender();
  kfPoll();
}
async function kfPoll(){
  if(!KF || !KF.job) return;
  let r;
  try{ r = await api.post('/api/armory/keyforce/status', {job: KF.job}); }catch(e){ r = {error: '' + e, done: true}; }
  if(!KF) return;
  KF.st = r;
  if(r.done || r.error) KF.job = null;
  else KF.timer = setTimeout(kfPoll, 1000);
  kfRender();
}
async function kfStop(){
  if(!KF || !KF.job) return;
  try{ await api.post('/api/armory/keyforce/stop', {job: KF.job}); }catch(e){}
}
function kfClose(){
  if(KF) clearTimeout(KF.timer);
  KF = null;
  closeModal();
}
// Manual Bake's settings, folded away; an untouched one is the add-on's recommended value
function kfSetAdv(k, v){
  KF.adv[k] = v;
  kfKeep();
  const out = document.getElementById('kfVal_' + k);
  if(out) out.textContent = v;
}
function kfAdvanced(busy){
  if(!KF.schema.length) return '';
  const head = `<div class="armpropsrow"><button class="mini" onclick="KF.open = !KF.open; kfRender()">${KF.open ? '▾' : '▸'} ${tt('armory.kf_advanced')}</button>
      <span style="flex:1"></span>${KF.open && Object.keys(KF.adv).length && !busy ? `<button class="mini" onclick="KF.adv = {}; kfKeep(); kfRender()">${tt('armory.kf_reset')}</button>` : ''}</div>`;
  if(!KF.open) return head;
  const dis = busy ? ' disabled' : '';
  const field = f => {
    const [label, title] = KF_LABELS[f.key] || [f.key, ''];
    const v = f.key in KF.adv ? KF.adv[f.key] : f.default;
    const t = esc(title ? tt(title) : '');
    if(f.kind === 'bool') return `<label class="armcheck" title="${t}"><input type="checkbox"${v ? ' checked' : ''}${dis}
        onchange="kfSetAdv('${f.key}', this.checked)"> ${tt(label)}</label>`;
    if(f.kind === 'enum') return `<label title="${t}">${tt(label)} <select${dis} onchange="kfSetAdv('${f.key}', this.value)">
        ${f.low.map(c => `<option value="${c}"${c === v ? ' selected' : ''}>${KF_CHOICES[c] ? tt(KF_CHOICES[c]) : c}</option>`).join('')}</select></label>`;
    return `<label class="armrange" title="${t}"><span>${tt(label)} <span class="count" id="kfVal_${f.key}">${v}</span></span>
        <input type="range" min="${f.low}" max="${f.high}" step="${f.step}" value="${v}"${dis}
        oninput="kfSetAdv('${f.key}', +this.value)"></label>`;
  };
  return head + Object.keys(KF_GROUPS).map(g => `<div class="armsect">${tt(KF_GROUPS[g])}</div>
      <div class="armpropsrow" style="flex-wrap:wrap">${KF.schema.filter(f => f.group === g).map(field).join('')}</div>`).join('');
}
function kfRender(){
  if(!KF) return;
  const st = KF.st, busy = !!KF.job;
  const pct = st ? Math.round((st.fraction || 0) * 100) : 0;
  let out = '';
  if(busy) out = `<div class="count" role="status">${pct}% <progress max="100" value="${pct}"></progress> ${esc(st.status || '')}</div>`;
  else if(st && st.error) out = `<div class="count w-bad">${esc(st.error)}</div>${st.log ? `<pre class="count">${esc(st.log)}</pre>` : ''}`;
  else if(st && st.done) out = `<div class="count w-good">${ttN('armory.kf_done', (st.results || []).length, {folder: esc(st.out || '')})}</div>
      ${(st.results || []).map(x => `<div class="count">${esc(x.path.split(/[\\/]/).pop())}</div>`).join('')}
      ${st.glb ? `<div class="count">${tt('armory.kf_glb_done', {path: esc(st.glb)})}</div>` : ''}
      ${st.missing ? `<div class="count w-bad">${ttN('armory.kf_missing', st.missing)}</div>` : ''}`;
  const blender = KF.blender === null ? tt('armory.kf_looking')
    : KF.blender ? tt('armory.kf_blender', {path: esc(KF.blender)}) : `<span class="w-bad">${tt('armory.kf_no_blender')}</span>`;
  document.getElementById('modal').innerHTML = `<h2>${tt('armory.kf_title')}</h2>
    <div class="mbody">
      <div class="count armnote">${tt('armory.kf_intro')}</div>
      <div class="count armnote">${blender}</div>
      <div class="armpropsrow"><span class="count" style="flex:1">${KF.root ? esc(KF.root) : tt('armory.kf_no_folder')}</span>
        <button onclick="kfBrowse()"${busy ? ' disabled' : ''}>${tt('armory.kf_folder')}</button></div>
      <div class="armpropsrow">
        <label>${tt('armory.kf_lod')} <input type="number" min="0" max="9" value="${KF.lod}" style="width:4em"${busy ? ' disabled' : ''}
          onchange="KF.lod = Math.max(0, Math.min(9, +this.value || 0))"></label>
        <label>${tt('armory.kf_size')} <select${busy ? ' disabled' : ''} onchange="KF.size = +this.value">
          ${[512, 1024, 2048, 4096].map(s => `<option value="${s}"${s === KF.size ? ' selected' : ''}>${s}</option>`).join('')}</select></label>
        <label class="armcheck" title="${esc(tt('armory.kf_glb_title'))}"><input type="checkbox"${KF.glb ? ' checked' : ''}${busy ? ' disabled' : ''}
          onchange="KF.glb = this.checked; kfKeep()"> ${tt('armory.kf_glb')}</label></div>
      ${kfAdvanced(busy)}
      ${out}
    </div>
    <div class="foot"><span style="flex:1"></span>
      ${busy ? `<button onclick="kfStop()">${tt('armory.kf_stop')}</button>` : `<button onclick="kfClose()">${tt('common.close')}</button>`}
      <button class="primary" onclick="kfStart()"${KF.root && KF.blender && !busy ? '' : ' disabled'}>${busy ? tt('armory.working') : tt('armory.lit_bake')}</button></div>`;
}

// the same through Keyforce Tools' Cycles bake, in a hidden Blender (keyforce.py),
// with the Manual Bake settings of the export dialog; the objects wear what it
// writes exactly as they wear armLitRun's
async function armLitCycles(){
  const l = armLit(), objs = armLitTargets();
  if(!objs.length || l.busy) return;
  const st = {cycles: true, settings: kfOpts().adv || {}};
  l.busy = true;
  l.cycles = {pct: 0, status: ''};
  armPaintObjects();
  let r;
  try{
    r = await api.post('/api/armory/keyforce/objects', {project: armProj(), ids: objs.map(o => o.id), settings: st.settings});
    if(r.error) throw new Error(r.error);
    l.cycles.job = r.job;
    for(;;){
      await new Promise(res => setTimeout(res, 1000));
      r = await api.post('/api/armory/keyforce/status', {job: l.cycles.job});
      if(r.error || r.done) break;
      l.cycles.pct = Math.round((r.fraction || 0) * 100);
      l.cycles.status = r.status || '';
      const el = typeof document !== 'undefined' && document.getElementById('armLitCycles');
      if(el){ el.textContent = l.cycles.pct + '% ' + l.cycles.status; }
    }
    if(r.error) throw new Error(r.error);
  }catch(e){ l.busy = false; l.cycles = null; toast(errText(e), 8000); armPaintObjects(); return; }
  l.busy = false;
  l.cycles = null;
  armLitApply(r, st);
}
async function armLitCyclesStop(){
  const l = armLit();
  if(l.cycles && l.cycles.job) try{ await api.post('/api/armory/keyforce/stop', {job: l.cycles.job}); }catch(e){}
}

async function armLitRun(){
  const l = armLit(), objs = armLitTargets(), st = armLitOpts();
  if(!objs.length || l.busy) return;
  l.busy = true;
  armPaintObjects();
  let r;
  try{
    r = await api.post('/api/armory/lit', {project: armProj(), ids: objs.map(o => o.id), settings: st});
    if(r.error) throw new Error(r.error);
  }catch(e){ l.busy = false; toast(errText(e), 6000); armPaintObjects(); return; }
  l.busy = false;
  armLitApply(r, st);
}

// a bake's answer worn: each object on its lit texture, what was skipped said
function armLitApply(r, st){
  const l = armLit();
  let n = 0;
  for(const b of r.baked || []){
    ARM.sheetAllowed.add(b.path);
    ARM.sheetCache.delete(b.path);            // the file was written again: read it again
    ARM.sheetStamp[b.path] = Date.now();
    for(const id of b.objects || []){
      const o = armObj(id);
      if(!o) continue;
      // what it wore before its first bake, so a second one starts there too
      const src = o.lit ? o.lit.src : (o.sheet || null);
      const before = o.lit && o.lit.uv_before;
      o.lit = {src, settings: st};
      o.sheet = b.path;
      // 2026-11-25: Unstack moved its UVs into a layer of the taller sheet; the
      // ones it had before are kept, for Remove and the next bake
      const moved = b.uv && b.uv[String(id)];
      if(moved){
        o.lit.uv_before = before || (o.src || []).map(pc => pc.uv ? JSON.parse(JSON.stringify(pc.uv)) : null);
        o.src = (o.src || []).map((pc, k) => moved[String(k)] ? Object.assign({}, pc, {uv: moved[String(k)]}) : pc);
      }else if(before) armLitUvBack(o, before);
      n++;
    }
  }
  // 2026-11-25: the baked textures shown, as they are, and Render mode off
  if(n){
    l.live = false;
    if(armRenderOn()) armRenderToggle(false);
    if(typeof armPaintBar === 'function') armPaintBar();
  }
  const skipped = (r.skipped || []).map(s => {
    const o = armObj(s.id);
    const name = o ? o.name : s.id;
    return s.why === 'two_sheets' ? tt('armory.lit_skip_two_sheets', {name}) : tt('armory.lit_skip_no_texture', {name});
  });
  toast(skipped.length ? skipped.join(' ') : ttN('armory.lit_done', n), skipped.length ? 8000 : 3000);
  armRepaint();
}

// an unstacked object's pieces on the UVs they had before (each a copy: a piece
// can be shared after a merge or a split)
function armLitUvBack(o, before){
  o.src = (o.src || []).map((pc, k) => {
    const c = Object.assign({}, pc);
    if(before[k]) c.uv = before[k]; else delete c.uv;
    return c;
  });
}
// the piece the viewport draws: under the live light an unstacked object shows
// its source texture, so its UVs from before (kept per bake, so its buffer stays)
const ARM_LIT_PIECES = new WeakMap();
function armLitPiece(ob, pc){
  const before = ob.lit && ob.lit.uv_before;
  if(!before || armLitMode(ob) !== 1) return pc;
  let list = ARM_LIT_PIECES.get(ob.lit);
  if(!list || list.src !== ob.src){
    list = {src: ob.src, pcs: ob.src.map((p, k) => before[k] ? Object.assign({}, p, {uv: before[k]}) : Object.assign({}, p, {uv: null}))};
    ARM_LIT_PIECES.set(ob.lit, list);
  }
  return list.pcs[ob.src.indexOf(pc)] || pc;
}
// each object back in what it wore before the bake; the lit files stay on disk
function armLitRemove(ids){
  const objs = ids ? ids.map(armObj).filter(Boolean) : armLitTargets();
  for(const o of objs){
    if(!o.lit) continue;
    o.sheet = o.lit.src || null;
    if(o.lit.uv_before) armLitUvBack(o, o.lit.uv_before);
    delete o.lit;
  }
  armLit().live = true;
  armRepaint();
}
