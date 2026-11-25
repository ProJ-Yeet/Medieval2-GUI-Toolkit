/* gallery.js - Phase 95a: every battle model in the mod at once, as tiles

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE GALLERY - Model entries as tiles instead of rows.

   ONE WebGL context draws every tile. A browser hands out a handful of
   contexts (Chrome sixteen) and takes the oldest back without asking, so a
   canvas of its own per tile would lose the models off the top of the page as
   the bottom ones drew. The gallery's context is on a canvas that is never on
   the page: a tile is drawn there and copied into the tile's own 2D canvas,
   which costs nothing a browser rations.

   Only the tiles on screen are loaded and drawn. Each is the entry's second
   LOD (the first is a thousand triangles too many for 200 pixels) with its
   first skin at 256 pixels, and the models furthest from the screen are let go
   once more than GAL_KEEP are held. The shaders, the geometry format and the
   framing are the docked viewer's (viewer3d.js), so a tile is that viewer's
   picture, smaller.

   The two traps of this UI are both in play (see the viewer): the loop is
   driven by requestAnimationFrame, which never fires in a hidden tab, so it
   is started again on `visibilitychange`; and a context the browser takes away
   is rebuilt on a new canvas, never `loseContext`'d by us, since that is for
   good.
   ===================================================================== */
const GAL_KEEP = 60;            // models held at once, on the GPU and off it
const GAL_LOADS = 4;            // fetched at once
const GAL_VARY_MS = 2600;       // auto variation: a new soldier this often

let gal = null;                 // {canvas, gl, prog, loc, mod, models, ...}

const galOn = () => ['gallery', 'units'].includes(state.settings.bmdb_view);
const galUnits = () => state.settings.bmdb_view === 'units';
const galSpinOn = () => state.settings.gallery_spin !== false;
const galVaryOn = () => state.settings.gallery_vary !== false;
/* The soldier model of a unit with armour upgrades is never seen in game (its
   first upgrade model stands in for it), so it is left out unless asked for.
   A unit with no upgrades keeps its soldier: that one is what the game shows. */
const galSoldierOn = () => state.settings.gallery_show_soldier === true;
const galSoldierShown = hasUpgrades => !hasUpgrades || galSoldierOn();

function galSet(key, value){
  state.settings[key] = value;
  api.post('/api/settings', {[key]: value});
}
function galView(how){ galSet('bmdb_view', how); render(); }
function galToggle(key){
  const now = {gallery_spin: galSpinOn, gallery_vary: galVaryOn, gallery_show_soldier: galSoldierOn}[key]();
  galSet(key, !now);
  if(gal) gal.dirty = true;
  galBarPaint();
  // the soldier tiles come and go with the switch: the page is rewritten
  if(key === 'gallery_show_soldier') render();
}

/* The view toggle and, in the gallery, its two switches. */
function galBarHtml(){
  return `<span class="galbar" id="galBar">${galBarInner()}</span>`;
}
function galBarInner(){
  const on = galOn(), units = galUnits();
  return `<button class="${on?'':'on'}" onclick="galView('list')">${tt('bmdb.view_list')}</button>
    <button class="${on&&!units?'on':''}" onclick="galView('gallery')">${tt('bmdb.view_gallery')}</button>
    <button class="${units?'on':''}" onclick="galView('units')"
      title="${ttA('bmdb.view_units_title')}">${tt('bmdb.view_units')}</button>
    ${on?`<button class="${galSpinOn()?'on':''}" onclick="galToggle('gallery_spin')"
        title="${ttA('bmdb.gallery_spin_title')}">${tt('bmdb.gallery_spin')}</button>
      <button class="${galVaryOn()?'on':''}" onclick="galToggle('gallery_vary')"
        title="${ttA('bmdb.gallery_vary_title')}">${tt('bmdb.gallery_vary')}</button>`:''}
    ${units?`<button class="${galSoldierOn()?'on':''}" onclick="galToggle('gallery_show_soldier')"
        title="${ttA('bmdb.show_soldier_title')}">${tt('bmdb.show_soldier')}</button>`:''}`;
}
function galBarPaint(){
  const el = document.getElementById('galBar');
  if(el) el.innerHTML = galBarInner();
}

/* ---- the tiles ---------------------------------------------------------- */

function galTileHtml(n, showing, role){
  return `<div class="gtile${n === showing ? ' showing' : ''}" data-name="${esc(n)}" title="${esc(n)}">
    <canvas></canvas><span class="gname">${role ? `<b>${esc(role)}</b> ` : ''}${esc(n)}</span></div>`;
}
function galTilesHtml(names, showing){
  return `<div class="galgrid">${names.map(n => galTileHtml(n, showing)).join('')}</div>`;
}
/* 95b: one row per unit, its soldier and every officer side by side, then its
   armour upgrades; the row scrolls sideways rather than wrap, so a unit stays
   one line however many models it has. */
function galUnitsHtml(units, showing, known){
  return `<div class="galunits">${units.map(u => {
    const tiles = (galSoldierShown(u.upgrades.length) ? [[u.soldier, tt('bmdb.role_soldier')]] : [])
      .concat(u.officers.map((o, i) => [o, tt('bmdb.role_officer', {n: i + 1})]))
      .concat(u.upgrades.map((a, i) => [a, tt('bmdb.role_upgrade', {n: i + 1})]));
    return `<div class="gunit"><div class="gulabel"><b>${esc(u.type)}</b>
        <span class="count">${esc([u.category, u.class].filter(Boolean).join(' · '))}</span></div>
      <div class="gurow">${tiles.map(([n, role]) => known.has(n) ? galTileHtml(n, showing, role)
        : `<div class="gtile gmissing" title="${ttA('bmdb.no_entry_called', {name: esc(n)})}">
            <canvas></canvas><span class="gname"><b>${esc(role)}</b> ${esc(n)}</span></div>`).join('')}</div></div>`;
  }).join('')}</div>`;
}

/* Called after the page under it is (re)written: the tiles are new elements
   every time, the models behind them are not. A model is held by its mod and
   name, so the import dialog of Armory Studio (99g) draws any installed mod's
   entries, and its library several mods' at once, through the same context:
   the mod is the tile's own data-mod, else the one given, else the open mod. */
function galMount(host, onPick, mod){
  galStart();
  if(!gal) return;
  mod = mod || state.src;
  if(gal.watch) gal.watch.disconnect();
  gal.tiles = new Map();
  gal.watch = new IntersectionObserver(seen => {
    for(const s of seen){
      const t = s.target, from = t.dataset.mod || mod;
      if(s.isIntersecting){ gal.tiles.set(t, galWant(from, t.dataset.name)); }
      else gal.tiles.delete(t);
    }
    gal.dirty = true;
    galPump();
    galLoop();
  }, {rootMargin: '300px 0px'});
  host.querySelectorAll('.gtile[data-name]').forEach(t => {
    gal.watch.observe(t);
    t.onclick = () => onPick(t.dataset.name, t);
  });
}

function galStart(){
  if(gal && gal.gl) return;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 2;
  const gl = canvas.getContext('webgl', {antialias: true, alpha: true, premultipliedAlpha: false});
  if(!gl){ gal = null; return; }
  const prog = v3Program(gl, V3_VERT, V3_FRAG);
  if(!prog){ gal = null; return; }
  const loc = {};
  ['aPos', 'aNormal', 'aUv'].forEach(k => { loc[k] = gl.getAttribLocation(prog, k); });
  ['uProj', 'uView', 'uModel', 'uTex', 'uHasTex', 'uKey', 'uEye', 'uFlat', 'uUScale',
   'uPair', 'uUv', 'uCutout'].forEach(k => { loc[k] = gl.getUniformLocation(prog, k); });
  const was = gal;
  gal = {canvas, gl, prog, loc, models: was ? was.models : new Map(),
         tiles: was ? was.tiles : new Map(), watch: was ? was.watch : null, queue: [], busy: 0,
         yaw: 0.6, dirty: true, raf: 0, varyAt: 0, seq: 0};
  // a context taken away is replaced, and every model put back on the GPU
  canvas.addEventListener('webglcontextlost', e => {
    e.preventDefault();
    if(!gal || gal.canvas !== canvas) return;
    gal.models.forEach(m => { m.gpu = null; });
    gal.gl = null;
    setTimeout(() => { if(gal && !gal.gl){ galStart(); galLoop(); } }, 50);
  });
  gl.enable(gl.DEPTH_TEST);
}

function galFree(m){
  if(gal && gal.gl && m.gpu){
    const gl = gal.gl;
    ['pos', 'nrm', 'uv', 'idx'].forEach(k => gl.deleteBuffer(m.gpu[k]));
    ['tex', 'spec', 'nmap'].forEach(k => { if(m.gpu[k]) gl.deleteTexture(m.gpu[k]); });
  }
  m.gpu = null;
}

/* ---- loading ------------------------------------------------------------ */

function galWant(mod, name){
  const key = mod + '|' + name;
  let m = gal.models.get(key);
  if(!m){
    m = {key, mod, name, status: 'queued', used: 0};
    gal.models.set(key, m);
    gal.queue.push(m);
  }else if(m.status === 'idle'){
    m.status = 'queued';
    gal.queue.push(m);
  }
  m.used = performance.now();
  return key;
}

function galPump(){
  if(!gal) return;
  // the tiles on screen first, newest scroll first
  const want = new Set(gal.tiles.values());
  gal.queue = gal.queue.filter(m => m.status === 'queued' && want.has(m.key));
  while(gal.busy < GAL_LOADS && gal.queue.length){
    const m = gal.queue.shift();
    gal.busy++;
    galLoad(m, gal.seq).finally(() => {
      if(!gal) return;
      gal.busy--;
      gal.dirty = true;
      galEvict();
      galPump();
      galLoop();
    });
  }
}

/* A tile whose data-mod is GAL_EXT draws a model file from disk, data-name
   being its path: Armory Studio's folder import and the asset library's files.
   Read through the import's own routes. Its sheets are put on as a model
   entry's are (galLoad below): the main sheet and the attachment glued side
   by side, u halved, since a battle model's UVs run 0..2 across the pair. It
   used to be the FIRST object's texture over the whole model, and an export
   whose first object is a bag wore its attachment sheet everywhere. */
const GAL_EXT = '@ext';
async function galLoadExt(m, seq){
  const view = await api.get('/api/armory/external?path=' + enc(m.name), 2);
  const r = await fetch('/api/armory/geometry?ext=' + enc(view.id), {cache: 'no-store'});
  if(!r.ok) throw new Error(String(r.status));
  const geo = v3Parse(await r.arrayBuffer());
  const objs = (view.objects || []).filter(o => o.texture_file);
  const pick = want => (objs.find(o => want.includes(o.sheets)) || {}).texture_file || '';
  const mainFile = pick(['main', 'both']) || (objs[0] || {}).texture_file || '';
  const attFile = pick(['attach']);
  const img = f => galImage('/api/armory/texture?path=' + enc(f));
  const tex = mainFile ? await img(mainFile) : null;
  const glued = attFile && attFile.toLowerCase() !== mainFile.toLowerCase();
  const att = glued ? await img(attFile) : null;
  if((mainFile && !tex) || (glued && !att)) throw new Error('texture');
  if(!gal || seq !== gal.seq) return;
  // the game's layout when any object sits on the attachment, or the file is a
  // battle .mesh; a plain .obj or .glb on one sheet keeps u as it is
  const paired = objs.some(o => o.sheets === 'attach' || o.sheets === 'both') || /\.mesh$/i.test(m.name);
  // 2026-11-25: a file on one PBR colour texture is drawn as the Cycles bake
  // will bake it (armcycles.js), its spec and normal maps with it, no shadows
  const pbr = view.pbr && galCyLook() ? view.pbr : null;
  const spec = pbr && pbr.spec ? await img(pbr.spec) : null;
  const nrm = pbr && pbr.normal ? await img(pbr.normal) : null;
  if(!gal || seq !== gal.seq) return;
  m.pbr = pbr ? {info: pbr, spec, nrm} : null;
  m.geo = geo; m.tex = tex; m.att = pbr ? null : att; m.uScale = pbr ? 1.0 : paired ? 0.5 : 1.0;
  m.parts = galParts(geo);
  m.variant = {}; m.hidden = {};
  const tall = geo.max[1] - geo.min[1];
  const wide = Math.max(geo.max[0] - geo.min[0], geo.max[2] - geo.min[2]);
  m.centre = [0, 1, 2].map(k => (geo.min[k] + geo.max[k]) / 2);
  m.dist = (Math.max(tall, wide * 0.8) || 1) * 1.12;
  m.status = 'ready';
}

/* A picture asked for again, with a growing pause, before it is given up:
   under load the server drops one now and then, and a tile without its sheet
   drew white (the user's report, 2026-11-23). */
async function galImage(url, tries = 5){
  for(let n = 0, wait = 300;; n++, wait = Math.min(wait * 2, 3000)){
    const got = await new Promise(ok => {
      const i = new Image();
      i.onload = () => ok(i); i.onerror = () => ok(null);
      i.src = n ? url + (url.includes('?') ? '&' : '?') + 'try=' + n : url;
    });
    if(got || n + 1 >= tries) return got;
    await new Promise(r => setTimeout(r, wait));
  }
}

/* A model that failed to load is put back in the queue after a pause, up to
   GAL_RETRIES times, so a tile does not stay empty or half drawn. */
const GAL_RETRIES = 8;
function galRetry(m, seq){
  m.tries = (m.tries || 0) + 1;
  if(m.tries > GAL_RETRIES){ m.status = 'none'; return; }
  m.status = 'retry';
  setTimeout(() => {
    if(!gal || seq !== gal.seq || m.status !== 'retry') return;
    m.status = 'queued';
    gal.queue.push(m);
    galPump();
    galLoop();
  }, Math.min(500 * 2 ** (m.tries - 1), 8000));
}

async function galLoad(m, seq){
  m.status = 'loading';
  if(m.mod === GAL_EXT){
    try{ await galLoadExt(m, seq); }catch(e){ galRetry(m, seq); }
    return;
  }
  const mod = m.mod, q = `mod=${enc(mod)}&entry=${enc(m.name)}`;
  try{
    const info = await api.get(`/api/model?${q}`);
    const lods = (info.lods || []).filter(l => l.exists);
    if(!lods.length){ m.status = 'none'; return; }
    const lod = (lods[1] || lods[0]).index;
    const r = await fetch(`/api/model/geometry?${q}&lod=${lod}`);
    if(!r.ok) throw new Error(String(r.status));
    const geo = v3Parse(await r.arrayBuffer());
    const skin = (info.skins || []).find(s => s.exists) || null;
    const img = rel => galImage(`/model_texture?mod=${enc(mod)}&rel=${enc(rel)}&small=1`);
    const tex = skin ? await img(skin.rel) : null;
    const glued = skin && skin.attach && skin.attach_exists && skin.attach.toLowerCase() !== skin.rel.toLowerCase();
    const att = glued ? await img(skin.attach) : null;
    // a sheet that is on disk but did not come is a half-loaded tile: try the
    // whole model again rather than keep it white
    if((skin && !tex) || (glued && !att)) throw new Error('texture');
    if(!gal || seq !== gal.seq) return;
    m.geo = geo; m.tex = tex; m.att = att;
    // the viewer's rule, v3Apply: u is halved for a glued pair and for an entry
    // that names no attachment; one naming an attachment it did not glue keeps it
    m.uScale = (!skin || !skin.attach || att) ? 0.5 : 1.0;
    m.parts = galParts(geo);
    m.variant = {}; m.hidden = {};
    m.parts.forEach(p => { m.hidden[p.key] = v3SlotHidden(p.key); });
    if(galVaryOn()) galRandomize(m);
    // framed nearly as the viewer frames a standing figure (v3Frame), with
    // more room for width: a tile spins, so a horse's length comes round to
    // face the camera, and the viewer's halving of it cut every mount in two
    const tall = geo.max[1] - geo.min[1];
    const wide = Math.max(geo.max[0] - geo.min[0], geo.max[2] - geo.min[2]);
    m.centre = [0, 1, 2].map(k => (geo.min[k] + geo.max[k]) / 2);
    m.dist = (Math.max(tall, wide * 0.8) || 1) * 1.12;
    m.status = 'ready';
    m.tries = 0;
  }catch(e){
    galRetry(m, seq);
  }
}

/* The model's groups as parts with their variants, as v3PartMap folds them. */
function galParts(geo){
  const parts = new Map();
  geo.groups.forEach((g, idx) => {
    const key = (g.name || '(unnamed)').toLowerCase();
    if(!parts.has(key)) parts.set(key, {key, list: []});
    parts.get(key).list.push({g, idx});
  });
  parts.forEach(p => { p.optional = p.list.every(v => v.g.optional); });
  return parts;
}

/* One soldier's worth of choices, as v3Randomize makes them. */
function galRandomize(m){
  m.parts.forEach(p => {
    m.variant[p.key] = p.list[Math.floor(Math.random() * p.list.length)].idx;
    m.hidden[p.key] = v3SlotHidden(p.key) || (p.optional && Math.random() < 0.5);
  });
}

/* Past GAL_KEEP, the models not on screen go, longest unseen first. */
function galEvict(){
  const held = [...gal.models.values()].filter(m => m.status === 'ready');
  if(held.length <= GAL_KEEP) return;
  const want = new Set(gal.tiles.values());
  held.filter(m => !want.has(m.key))
      .sort((a, b) => a.used - b.used)
      .slice(0, held.length - GAL_KEEP)
      .forEach(m => { galFree(m); m.geo = m.tex = m.att = null; m.status = 'idle'; });
}

function galUpload(m){
  const gl = gal.gl, g = m.geo;
  const buf = (data, target) => {
    const b = gl.createBuffer();
    gl.bindBuffer(target, b); gl.bufferData(target, data, gl.STATIC_DRAW);
    return b;
  };
  m.gpu = {
    pos: buf(g.positions, gl.ARRAY_BUFFER),
    nrm: buf(g.normals || new Float32Array(g.vertices * 3).fill(0.577), gl.ARRAY_BUFFER),
    uv: buf(g.uvs || new Float32Array(g.vertices * 2), gl.ARRAY_BUFFER),
    idx: buf(g.indices, gl.ELEMENT_ARRAY_BUFFER),
    tex: null,
  };
  if(m.tex){
    const sheet = m.att ? v3Atlas(m.tex, m.att) : m.tex;
    const t = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, sheet);
    const pot = n => n > 0 && (n & (n - 1)) === 0;
    if(pot(sheet.width) && pot(sheet.height)){
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    }else{
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    m.gpu.tex = t;
  }
}

/* ---- drawing ------------------------------------------------------------ */

function galLoop(){
  if(!gal || gal.raf || document.hidden) return;
  gal.raf = requestAnimationFrame(galFrame);
}

function galFrame(now){
  gal.raf = 0;
  // tiles of a page or dialog since rewritten or closed are let go
  gal.tiles.forEach((k, t) => { if(!t.isConnected) gal.tiles.delete(t); });
  if(!gal.gl || !gal.tiles.size) return;
  const spin = galSpinOn();
  if(spin){ gal.yaw += 0.012; gal.dirty = true; }
  if(galVaryOn() && now - gal.varyAt > GAL_VARY_MS){
    gal.varyAt = now;
    new Set(gal.tiles.values()).forEach(key => {
      const m = gal.models.get(key);
      if(m && m.status === 'ready') galRandomize(m);
    });
    gal.dirty = true;
  }
  if(gal.dirty){
    gal.dirty = false;
    gal.tiles.forEach((key, tile) => {
      const m = gal.models.get(key);
      if(!m) return;
      m.used = now;
      tile.classList.toggle('gnone', m.status === 'none');
      if(m.status === 'ready') galDraw(m, tile.querySelector('canvas'));
    });
  }
  // keep going while something moves or is still on its way
  const pending = [...gal.tiles.values()].some(n => {
    const m = gal.models.get(n);
    return m && ['queued', 'loading', 'retry'].includes(m.status);
  });
  if(spin || galVaryOn() || pending) galLoop();
}

/* --- 2026-11-25: the Cycles bake's look on a PBR tile (armcycles.js) -------------- */
const galCyLook = () => {
  if(typeof armCyOn !== 'function' || !armCyOn()) return null;
  if(!(ARM.cy && ARM.cy.look) && typeof armCyCheck === 'function') armCyCheck();
  return ARM.cy && ARM.cy.look ? ARM.cy.look : null;
};
function galTex(gl, img, data){
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  if(data) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, data.w, data.h, 0, gl.RGBA, gl.FLOAT, data.px);
  else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  const pot = n => n > 0 && (n & (n - 1)) === 0;
  const w = data ? data.w : img.width, h = data ? data.h : img.height;
  const mip = !data && pot(w) && pot(h);
  if(mip) gl.generateMipmap(gl.TEXTURE_2D);
  const lin = data && !gl.getExtension('OES_texture_float_linear') ? gl.NEAREST : gl.LINEAR;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : lin);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, lin);
  const wrap = pot(w) && pot(h) ? gl.REPEAT : gl.CLAMP_TO_EDGE;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, data ? gl.CLAMP_TO_EDGE : wrap);
  return t;
}
// the program and the light in the gallery's own context, made once per light
function galCy(gl){
  const lk = galCyLook();
  if(!lk || !gl.getExtension('OES_texture_float') || !gl.getExtension('OES_standard_derivatives')) return null;
  if(gal.cy && gal.cy.look === lk) return gal.cy;
  if(gal.cy && gal.cy.look !== lk){ gl.deleteTexture(gal.cy.env); if(gal.cy.lut) gl.deleteTexture(gal.cy.lut); }
  const vs = `attribute vec3 aPos; attribute vec3 aNormal; attribute vec2 aUv;
uniform mat4 uProj, uView, uModel;
varying vec3 vNormal; varying vec2 vUv; varying vec3 vPos; varying float vPart;
void main(){ vNormal = mat3(uModel) * aNormal; vUv = aUv; vPart = 0.0;
  vec4 w = uModel * vec4(aPos, 1.0); vPos = w.xyz; gl_Position = uProj * uView * w; }`;
  const fs = `#extension GL_OES_standard_derivatives : enable
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec3 vNormal; varying vec2 vUv; varying vec3 vPos;
uniform sampler2D uTex, uNTex, uSTex;
uniform float uHasS, uHasN;
${ARM_CY_GLSL}
void main(){
  vec4 base = texture2D(uTex, vUv);
  if(base.a < 0.35) discard;
  vec3 n = normalize(vNormal);
  if(uHasN > 0.5){
    vec3 dp1 = dFdx(vPos), dp2 = dFdy(vPos);
    vec2 d1 = dFdx(vUv), d2 = dFdy(vUv);
    float det = d1.x * d2.y - d2.x * d1.y;
    det = abs(det) < 1e-12 ? 1e-12 : det;
    vec3 T = (dp1 * d2.y - dp2 * d1.y) / det, B = (dp2 * d1.x - dp1 * d2.x) / det;
    T = normalize(T - n * dot(T, n)); B = normalize(B - n * dot(B, n));
    vec2 m = (texture2D(uNTex, vUv).xy * 2.0 - 1.0) * uCyObj.w;
    n = normalize(T * m.x + B * m.y + n * sqrt(max(1.0 - dot(m, m), 0.01)));
  }
  gl_FragColor = vec4(cyShade(base, vUv, n), 1.0);
}`;
  const p = v3Program(gl, vs, fs);
  if(!p) return null;
  const loc = {};
  ['aPos', 'aNormal', 'aUv'].forEach(k => { loc[k] = gl.getAttribLocation(p, k); });
  ['uProj', 'uView', 'uModel', 'uTex', 'uNTex', 'uSTex', 'uHasS', 'uHasN', 'uCyEnv', 'uCyLut', 'uCyRows', 'uCyView',
   'uCySunN', 'uCyHasAt', 'uCyLutR', 'uCyMix', 'uCyMix2', 'uCyObj', 'uCyAlb', 'uCySun', 'uCySunA', 'uCyAo']
    .forEach(k => { loc[k] = gl.getUniformLocation(p, k); });
  // the world's light, levels stacked and padded to 1024 rows, as armCyUpload has it
  const e = lk.env, raw = Uint8Array.from(atob(e.data), ch => ch.charCodeAt(0)), f = new Float32Array(raw.buffer);
  const px = new Float32Array(e.w * 1024 * 4);
  for(let i = 0; i < e.levels * e.h * e.w; i++){ px[i*4] = f[i*3]; px[i*4+1] = f[i*3+1]; px[i*4+2] = f[i*3+2]; px[i*4+3] = 1; }
  const cy = gal.cy = {look: lk, p, loc, env: galTex(gl, null, {w: e.w, h: 1024, px}), lut: null};
  gl.bindTexture(gl.TEXTURE_2D, cy.env);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  const im = new Image();
  im.onload = () => { if(gal && gal.cy === cy){ cy.lut = galTex(gl, im); gl.bindTexture(gl.TEXTURE_2D, cy.lut);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gal.dirty = true; galLoop(); } };
  im.src = lk.lut;
  return cy;
}
function galCyUse(gl, m){
  const cy = galCy(gl);
  if(!cy || !cy.lut) return null;
  const L = cy.loc, lk = cy.look, st = lk.settings, info = m.pbr.info;
  gl.useProgram(cy.p);
  if(!m.gpu.spec && m.pbr.spec) m.gpu.spec = galTex(gl, m.pbr.spec);
  if(!m.gpu.nmap && m.pbr.nrm) m.gpu.nmap = galTex(gl, m.pbr.nrm);
  const unit = (k, t, u) => { gl.activeTexture(gl.TEXTURE0 + u); gl.bindTexture(gl.TEXTURE_2D, t); gl.uniform1i(L[k], u); };
  unit('uCyEnv', cy.env, 4); unit('uCyLut', cy.lut, 5);
  if(m.gpu.spec) unit('uSTex', m.gpu.spec, 2);
  if(m.gpu.nmap) unit('uNTex', m.gpu.nmap, 1);
  if(m.gpu.tex) unit('uTex', m.gpu.tex, 0);
  gl.activeTexture(gl.TEXTURE0);
  gl.uniform1f(L.uHasS, m.gpu.spec ? 1 : 0); gl.uniform1f(L.uHasN, m.gpu.nmap ? 1 : 0);
  gl.uniform1f(L.uCyRows, 1024);
  gl.uniform3f(L.uCyLutR, lk.lut_range[0], lk.lut_range[1], lk.lut_range[2]);
  gl.uniform1f(L.uCyView, lk.view === 'AgX' && st.bake_view !== false ? 1 : 0);
  gl.uniform4f(L.uCyMix, st.bake_ambient, st.bake_world, st.bake_shadows, st.bake_floor);
  gl.uniform4f(L.uCyMix2, st.bake_surround_diffuse, lk.consts.metal_other, lk.consts.glossy[0], lk.consts.glossy[1]);
  const alb = new Float32Array(18); lk.albedo.forEach((a, i) => { alb[i*2] = a[0]; alb[i*2+1] = a[1]; });
  gl.uniform2fv(L.uCyAlb, alb);
  const suns = lk.suns.slice(0, 9), sv = new Float32Array(36), sa = new Float32Array(9);
  suns.forEach((x, i) => { sv.set([x.dir[0], x.dir[1], x.dir[2], x.energy], i * 4); sa[i] = x.angle * Math.PI / 180; });
  gl.uniform4fv(L.uCySun, sv); gl.uniform1fv(L.uCySunA, sa); gl.uniform1f(L.uCySunN, suns.length);
  gl.uniform1f(L.uCyHasAt, 0);
  const metalObj = info.metal >= lk.consts.metal_object;
  gl.uniform4f(L.uCyObj, metalObj ? 1 : 0, metalObj ? 1 : 0,
               st.bake_surround_diffuse > 0.02 || info.max_metal > 0.02 ? 1 : 0, info.normal_kind === 'm2' ? -1 : 1);
  return L;
}

function galDraw(m, out){
  const gl = gal.gl, c = gal.canvas, g = m.geo;
  let loc = gal.loc;
  if(!out || !out.clientWidth) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round(out.clientWidth * dpr), h = Math.round(out.clientHeight * dpr);
  if(out.width !== w || out.height !== h){ out.width = w; out.height = h; }
  if(c.width !== w || c.height !== h){ c.width = w; c.height = h; }
  if(!m.gpu) galUpload(m);
  gl.viewport(0, 0, w, h);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.useProgram(gal.prog);
  // a PBR tile under the Cycles look draws with its own program; the same
  // matrices, and the gallery's own uniforms then go nowhere
  const cyLoc = m.pbr ? galCyUse(gl, m) : null;
  if(cyLoc) loc = cyLoc;
  const pitch = 0.25, yaw = gal.yaw;
  const eye = [m.centre[0] + m.dist * Math.cos(pitch) * Math.sin(yaw),
               m.centre[1] + m.dist * Math.sin(pitch),
               m.centre[2] + m.dist * Math.cos(pitch) * Math.cos(yaw)];
  const back = v3Norm([eye[0] - m.centre[0], eye[1] - m.centre[1], eye[2] - m.centre[2]]);
  gl.uniformMatrix4fv(loc.uProj, false, v3Perspective(0.9, w / h || 1, Math.max(0.01, m.dist / 100), m.dist * 10));
  gl.uniformMatrix4fv(loc.uView, false, v3LookAt(eye, m.centre, [0, 1, 0]));
  gl.uniformMatrix4fv(loc.uModel, false, [-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  gl.uniform3fv(loc.uKey, v3Norm([0.45, 0.85, 0.7]));
  gl.uniform3fv(loc.uEye, back);
  const bind = (b, at, size) => {
    if(at < 0) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.enableVertexAttribArray(at);
    gl.vertexAttribPointer(at, size, gl.FLOAT, false, 0, 0);
  };
  bind(m.gpu.pos, loc.aPos, 3);
  bind(m.gpu.nrm, loc.aNormal, 3);
  bind(m.gpu.uv, loc.aUv, 2);
  const textured = !!(m.gpu.tex && g.has_uvs);
  if(textured){
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, m.gpu.tex);
    gl.uniform1i(loc.uTex, 0);
  }
  gl.uniform1f(loc.uHasTex, textured ? 1 : 0);
  gl.uniform1f(loc.uUScale, m.uScale);
  gl.uniform1f(loc.uPair, m.att ? 1 : 0);
  gl.uniform1f(loc.uUv, 0);
  gl.uniform1f(loc.uCutout, 1);
  gl.uniform1f(loc.uFlat, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, m.gpu.idx);
  m.parts.forEach(p => {
    if(m.hidden[p.key]) return;
    const idx = m.variant[p.key] !== undefined ? m.variant[p.key] : p.list[0].idx;
    const grp = g.groups[idx];
    gl.drawElements(gl.TRIANGLES, grp.count, gl.UNSIGNED_SHORT, grp.start * 2);
  });
  const x = out.getContext('2d');
  x.clearRect(0, 0, w, h);
  x.drawImage(c, 0, 0);
}

// a tab coming back to the front starts the loop again (see the header)
document.addEventListener('visibilitychange', () => {
  if(gal && !document.hidden){ gal.dirty = true; galLoop(); }
});
