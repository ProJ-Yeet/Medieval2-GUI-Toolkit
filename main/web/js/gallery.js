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

function galSet(key, value){
  state.settings[key] = value;
  api.post('/api/settings', {[key]: value});
}
function galView(how){ galSet('bmdb_view', how); render(); }
function galToggle(key){
  galSet(key, !(key === 'gallery_spin' ? galSpinOn() : galVaryOn()));
  if(gal) gal.dirty = true;
  galBarPaint();
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
        title="${ttA('bmdb.gallery_vary_title')}">${tt('bmdb.gallery_vary')}</button>`:''}`;
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
    const tiles = [[u.soldier, tt('bmdb.role_soldier')]]
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
    if(m.gpu.tex) gl.deleteTexture(m.gpu.tex);
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
   Read through the import's own routes, its first object's texture on it. */
const GAL_EXT = '@ext';
async function galLoadExt(m, seq){
  const view = await api.get('/api/armory/external?path=' + enc(m.name), 2);
  const r = await fetch('/api/armory/geometry?ext=' + enc(view.id), {cache: 'no-store'});
  if(!r.ok) throw new Error(String(r.status));
  const geo = v3Parse(await r.arrayBuffer());
  const file = ((view.objects || []).find(o => o.texture_file) || {}).texture_file;
  const tex = file ? await new Promise(ok => {
    const i = new Image();
    i.onload = () => ok(i); i.onerror = () => ok(null);
    i.src = '/api/armory/texture?path=' + enc(file);
  }) : null;
  if(!gal || seq !== gal.seq) return;
  m.geo = geo; m.tex = tex; m.att = null; m.uScale = 1.0;
  m.parts = galParts(geo);
  m.variant = {}; m.hidden = {};
  const tall = geo.max[1] - geo.min[1];
  const wide = Math.max(geo.max[0] - geo.min[0], geo.max[2] - geo.min[2]);
  m.centre = [0, 1, 2].map(k => (geo.min[k] + geo.max[k]) / 2);
  m.dist = (Math.max(tall, wide * 0.8) || 1) * 1.12;
  m.status = 'ready';
}

async function galLoad(m, seq){
  m.status = 'loading';
  if(m.mod === GAL_EXT){
    try{ await galLoadExt(m, seq); }catch(e){ m.status = 'none'; }
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
    const img = rel => new Promise(ok => {
      const i = new Image();
      i.onload = () => ok(i); i.onerror = () => ok(null);
      i.src = `/model_texture?mod=${enc(mod)}&rel=${enc(rel)}&small=1`;
    });
    const tex = skin ? await img(skin.rel) : null;
    const glued = skin && skin.attach && skin.attach_exists && skin.attach.toLowerCase() !== skin.rel.toLowerCase();
    const att = glued ? await img(skin.attach) : null;
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
  }catch(e){
    m.status = 'none';
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
    return m && (m.status === 'queued' || m.status === 'loading');
  });
  if(spin || galVaryOn() || pending) galLoop();
}

function galDraw(m, out){
  const gl = gal.gl, c = gal.canvas, loc = gal.loc, g = m.geo;
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
