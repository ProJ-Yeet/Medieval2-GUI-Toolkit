/* map3d.js - the campaign map as a mesh, orbited

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it.

   Loaded after viewer3d.js, and on purpose: `v3Program`, `v3Perspective`
   and `v3LookAt` are this file's too. A second copy of a 4x4 multiply is
   a second thing to get wrong.
   ========================================================================= */

/* =========================================================================
   M18 - THE MAP IN 3D.

   A third way of looking at the same map, beside the flat canvas and the
   front-end picture, and it is a MODE rather than a screen: the same
   campaign, the same layer stack, the same opacities, the same season and
   the same colouring, lit and seen from an angle instead of from straight
   above. Nothing here reads a file, asks the server a question or edits
   anything. Everything it draws, the screen was already holding.

   THAT IS THE WHOLE DESIGN. The reference tool's 3D view is a second map
   with controls of its own - its own ground-texture loader, its own feature
   overlay with its own opacity, its own region overlay with its own two
   modes - and the two pictures drift apart the moment you touch either.
   Ours has none of those switches because it does not need them: the
   texture IS `cmapPaint`'s stack, composed in the same order by `cm3Texture`
   below, so ticking a layer off in the Layers popover takes it out of the 3D
   picture too, at the opacity the slider is already at.

   THREE THINGS WE DO NOT HAVE TO SOLVE, and they are why this file is short:

     * THE TEXTURES ARE NOT PIXELATED. His are sampled one texel to a tile in
       the browser, which is what his tile-size slider and his "none matched"
       warning are there to manage. `mapterrain.composite` has drawn the
       ground at `mapterrain.SCALE` pixels a tile, supersampled, once a
       season, since 23a, and `c.terrain.img` is that picture already
       decoded. We blit it. There is no tile cache, no per-pixel loop and no
       folder to pick, and 37b's finding - that a picture scaled into a
       per-tile composite and back out is the artefact - is the reason.

     * THERE IS NOTHING TO DECIMATE. His mesh caps at 2048 steps and he
       records that the 512 it capped at before was dropping one-pixel
       islands and thin isthmuses. `descr_terrain.txt` caps a Medieval II map
       at 510x510 tiles and the heights layer arrives at `fit=tile`, one
       pixel a tile, sampled at the block centre the engine samples. So ONE
       VERTEX PER TILE is the whole map at 260,100 vertices worst case. No
       resampling, and the mesh is addressed in tiles like every other
       coordinate on this screen.

     * SEA IS NOT A GUESS. His rule is "the heights pixel is blue OR the
       ground type is one of the four sea colours", which is two rules
       because the first alone left sea at land elevation and the terrain
       poked through the water in stripes. Ours is `mapvocab.is_sea_height` -
       a tile is sea iff its height pixel is not greyscale, or is black -
       which TWMapReader worked out from the engine's own behaviour and which
       this project measured at the coastline: 74,317 sea tiles on DaC, and
       the ground-type version disagrees about 70 of them. `cmapHeightRamp`
       already mirrors that rule in this browser; `cm3Build` mirrors it again
       in one line, with no second layer read.

   WHAT IS DELIBERATELY NOT HERE. Markers, labels, the selected outline and
   the hover readout are all screen-space drawing on top of a flat canvas
   (`cmapOverlay`, maplabels.js) and none of them has a position in a scene.
   They stay on the 2D map, the card says so, and going back is one press.
   His does not put them in 3D either.
   ========================================================================= */

//: The live scene, or null. ONE WebGL context on this page at a time, the
//: same rule `v3Mount` keeps for the model viewer: a second context is a
//: second copy of the mesh and a second animation loop for a view nobody is
//: looking at. The model viewer is not on this screen (49 moved it to the
//: Models Editor), so the two never want a context at once, but `cm3Stop`
//: gives ours up the moment the mode is switched off all the same.
let cm3 = null;

//: How tall the highest land stands, in tiles, at the default. A map is at
//: most 510 tiles across, so the number is read against that rather than
//: against the thousands of units the reference tool's map is wide.
const CM3_HEIGHT_DEF = 24;
const CM3_HEIGHT_MIN = 0, CM3_HEIGHT_MAX = 120;

//: The sea floor and the water surface, both as a fraction of the height
//: scale. His numbers, and his reason for the gap between them: the surface
//: has to sit clearly above the floor so the two cannot z-fight, and clearly
//: below land level so a coastline is still a coastline.
const CM3_FLOOR = -0.12, CM3_WATER = -0.04;

//: The stage's backdrop and the fog's colour, one answer. It is the flat
//: map's own `#0e1013` lifted towards a horizon, because a scene that fades
//: to exactly its background has no horizon at all.
const CM3_SKY = [0.09, 0.11, 0.14];

/* Whether the mode is up. Read by the button, by `renderCampmap` and by
   `cmapPaint`, so all three agree about one answer rather than three. */
function cm3On(){
  const c = state.cmap;
  return !!(c && c.d3 && c.d3.on);
}

/* The mode's own habits, defaulted.

   Lives on `state.cmap` beside the terrain block and rides in
   `cmapLayerState`, so a named view preset carries it for nothing and
   `cmapResetView` puts it back - which is the contract the comment over
   `cmapLayerState` states for any switch added to this screen. */
function cm3State(){
  const c = state.cmap;
  if(!c) return null;
  if(!c.d3){
    const s = cmapSettings().d3;
    c.d3 = {
      on: false,                      // never remembered: see cm3Toggle
      height: (s && typeof s.height === 'number') ? s.height : CM3_HEIGHT_DEF,
      water: !(s && s.water === false),
      yaw: -0.6, pitch: 0.85, dist: 0, tx: 0, tz: 0,   // framed by cm3Fit
      fitted: false,
    };
  }
  return c.d3;
}

/* ---------- the mode switch ---------- */

/* On, off, and the one thing it costs.

   NOT REMEMBERED ACROSS SESSIONS, unlike every other switch on this screen,
   and that is a decision rather than an oversight. The habits in
   `cmapLayerState` are all ways of READING a flat map and cost nothing to
   open into; this one opens a WebGL context and builds a quarter of a
   million vertices, and somebody who looked at one map in 3D should not find
   the next mod opening that way. The height scale and the water plane ARE
   remembered, because those are habits about how the 3D looks once in it. */
function cm3Toggle(want){
  const c = state.cmap;
  if(!c) return;
  const d = cm3State();
  const on = want === undefined ? !d.on : !!want;
  if(on === d.on) return;
  d.on = on;
  activity('map view', on ? 'looked at the map in 3D'
                          : 'went back to the flat map');
  cm3Show();
  if(!on){
    cm3Stop();
    cmapResize();
    cmapPaint();
    cmapRepanel();
    return;
  }
  cm3Mount();
  cmapRepanel();
}

/* Which canvas the stage is showing, and what goes with it.

   The 2D canvas keeps its pixels while it is hidden, so going back is a
   repaint and not a reload. The tooltip is screen-space over the flat map
   and has nowhere to sit over a scene, so it goes down with it. */
function cm3Show(){
  const on = cm3On();
  const flat = document.getElementById('cmCanvas');
  const gl = document.getElementById('cm3Canvas');
  const card = document.getElementById('cm3Card');
  const tip = document.getElementById('cmTip');
  if(flat) flat.hidden = on;
  if(gl) gl.hidden = !on;
  if(card){
    card.hidden = !on;
    if(on) card.innerHTML = cm3CardHtml();
  }
  if(tip && on) tip.hidden = true;
  const btn = document.getElementById('cm3Btn');
  if(btn){
    btn.classList.toggle('on', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  const stage = document.getElementById('cmStage');
  if(stage) stage.classList.toggle('cm3on', on);
}

/* ---------- the picture on the mesh ---------- */

/* `cmapPaint`'s stack, on one canvas, at the terrain's own resolution.

   The order is the flat map's order and it is copied here rather than
   re-derived: 23a's ground underneath, then the one-pixel-per-tile composite
   of every ticked layer at its own opacity, then 16g's colouring over both
   (which in tint mode is a reading of what is under it and therefore has to
   be last). Change the order on the flat map and this changes with it; there
   is no third place that knows it.

   The size is the terrain composite's, so the ground goes on at the
   resolution Python drew it and nothing is resampled on the way in. With the
   terrain off there is nothing finer than a tile in the picture, so the
   canvas is one pixel a tile and the texture is honest about that rather
   than blown up to look detailed. */
function cm3Texture(){
  const c = state.cmap;
  if(!c || !c.comp) return null;
  const m = c.man;
  const hasTerrain = cmapTerrainOn(c);
  const scale = hasTerrain ? (c.terrain.scale || 1) : 1;
  const cv = document.createElement('canvas');
  cv.width = Math.max(1, m.width * scale);
  cv.height = Math.max(1, m.height * scale);
  const x = cv.getContext('2d');
  if(hasTerrain){
    x.drawImage(c.terrain.img, 0, 0, cv.width, cv.height);
  }else{
    // The same backdrop the flat map fills with, for the same reason: a map
    // with every layer off is the sea this tool draws around it, not a hole.
    x.fillStyle = '#0e1013';
    x.fillRect(0, 0, cv.width, cv.height);
  }
  // Magnified, so no smoothing: 23a's picture is already the detailed one and
  // the composite over it is a tile grid that has to stay a tile grid.
  x.imageSmoothingEnabled = false;
  x.drawImage(c.comp, 0, 0, cv.width, cv.height);
  if(c.overlay || c.overlayEdge){
    x.globalAlpha = c.overlayAlpha == null ? 0.85 : c.overlayAlpha;
    if(c.overlay){
      x.globalCompositeOperation = c.overlayFill === 'tint' ? 'color' : 'source-over';
      x.drawImage(c.overlay, 0, 0, cv.width, cv.height);
      x.globalCompositeOperation = 'source-over';
    }
    if(c.overlayEdge) x.drawImage(c.overlayEdge, 0, 0, cv.width, cv.height);
    x.globalAlpha = 1;
  }
  return cv;
}

/* The texture, resized to a power of two so it can have mipmaps.

   WebGL 1 will not mipmap a non-power-of-two texture, and terrain without
   mipmaps shimmers into noise the moment the camera pulls back - which is
   most of what is done in this mode. A 510-tile map at 23a's four pixels a
   tile is 2040 across and the power of two above it is 2048, so the resample
   is eight pixels in two thousand and costs nothing visible. Clamped to what
   the driver will actually take. */
function cm3Pot(cv, max){
  const pot = n => { let p = 1; while(p < n) p *= 2; return p; };
  const w = Math.min(pot(cv.width), max), h = Math.min(pot(cv.height), max);
  if(w === cv.width && h === cv.height) return cv;
  const out = document.createElement('canvas');
  out.width = w; out.height = h;
  const x = out.getContext('2d');
  x.imageSmoothingEnabled = true;
  x.drawImage(cv, 0, 0, w, h);
  return out;
}

/* ---------- the mesh ---------- */

/* Positions, normals, UVs and indices, out of the heights layer.

   One vertex per TILE, at the tile's centre, which is where the heights
   layer samples (`campmap.tile_view`: a `centre` layer is read at
   `(2t+1, 2t+1)`). The mesh is therefore addressed in tiles, the same as
   `cmapX`/`cmapY` and everything else on this screen, and a tile's vertex is
   the tile's own height rather than an average of a resampling.

   x runs east, z runs south, y is up, and the map is centred on the origin
   so the orbit has nothing to offset.

   Normals are taken from the height field by central difference rather than
   accumulated off the faces: one pass instead of two, no per-vertex face
   list, and on a regular grid it is the same answer. */
function cm3Build(raw, hScale){
  const w = raw.w, h = raw.h, d = raw.data;
  const n = w * h;
  const pos = new Float32Array(n * 3);
  const nrm = new Float32Array(n * 3);
  const uv = new Float32Array(n * 2);
  const y = new Float32Array(n);
  for(let i = 0; i < n; i++){
    const p = i * 4, r = d[p], g = d[p + 1], b = d[p + 2];
    // `mapvocab.is_sea_height`, mirrored: not greyscale, or black.
    const sea = (r === 0 || r !== g || g !== b);
    y[i] = sea ? hScale * CM3_FLOOR : (r / 255) * hScale;
  }
  for(let ty = 0; ty < h; ty++){
    for(let tx = 0; tx < w; tx++){
      const i = ty * w + tx, p = i * 3;
      pos[p] = tx - (w - 1) / 2;
      pos[p + 1] = y[i];
      pos[p + 2] = ty - (h - 1) / 2;
      // The texture is the whole map, so a tile's centre is half a tile in.
      uv[i * 2] = (tx + 0.5) / w;
      uv[i * 2 + 1] = (ty + 0.5) / h;
      // Central difference, clamped at the edges. The two tangents are
      // (1, dy/dx, 0) and (0, dy/dz, 1); their cross product is (-dy/dx, 1,
      // -dy/dz), which is what goes in, normalised.
      const xl = y[ty * w + Math.max(0, tx - 1)];
      const xr = y[ty * w + Math.min(w - 1, tx + 1)];
      const zu = y[Math.max(0, ty - 1) * w + tx];
      const zd = y[Math.min(h - 1, ty + 1) * w + tx];
      const dx = (xr - xl) / ((tx === 0 || tx === w - 1) ? 1 : 2);
      const dz = (zd - zu) / ((ty === 0 || ty === h - 1) ? 1 : 2);
      const nx = -dx, ny = 1, nz = -dz;
      const L = Math.hypot(nx, ny, nz) || 1;
      nrm[p] = nx / L; nrm[p + 1] = ny / L; nrm[p + 2] = nz / L;
    }
  }
  // Two triangles a quad. 510x510 is 518,418 triangles and 1,555,254
  // indices, which is past what a 16-bit index can name - see cm3Thin.
  const quads = Math.max(0, (w - 1) * (h - 1));
  const big = n > 65535;
  const idx = big ? new Uint32Array(quads * 6) : new Uint16Array(quads * 6);
  let k = 0;
  for(let ty = 0; ty < h - 1; ty++){
    for(let tx = 0; tx < w - 1; tx++){
      const a = ty * w + tx, b = a + 1, cc = a + w, e = cc + 1;
      // Wound so that a tile seen from above is front-facing, which is what
      // lets the back faces be culled: the underside of the map is never the
      // thing being looked at, and not drawing it halves the fill.
      idx[k++] = a; idx[k++] = cc; idx[k++] = b;
      idx[k++] = b; idx[k++] = cc; idx[k++] = e;
    }
  }
  return {w, h, pos, nrm, uv, idx, big, count: k};
}

/* The heights, thinned until a 16-bit index can name every vertex.

   Only ever reached on a driver with no `OES_element_index_uint`, a WebGL 1
   extension every browser since about 2012 has had and which `cm3Begin` asks
   for first. The fallback is a stride rather than a refusal, because a
   thinned map in 3D is worth more than a message saying no, and the card
   says what it did. */
function cm3Thin(raw, stride){
  const w = Math.ceil(raw.w / stride), h = Math.ceil(raw.h / stride);
  const data = new Uint8ClampedArray(w * h * 4);
  for(let ty = 0; ty < h; ty++){
    for(let tx = 0; tx < w; tx++){
      const s = (Math.min(raw.h - 1, ty * stride) * raw.w
               + Math.min(raw.w - 1, tx * stride)) * 4;
      const t = (ty * w + tx) * 4;
      data[t] = raw.data[s]; data[t + 1] = raw.data[s + 1];
      data[t + 2] = raw.data[s + 2]; data[t + 3] = 255;
    }
  }
  return {w, h, data};
}

/* ---------- the shaders ---------- */

/* One program for both surfaces. The land is textured and the water is a
   flat colour with an alpha, and the only difference in the fragment stage
   is whether the texture is sampled, so a uniform is cheaper than a second
   program and a second set of uniform lookups.

   The lighting is the reference tool's, which is the lighting a terrain
   wants and not a coincidence: an ambient term so nothing is black, a warm
   key from high in the west, and a cool fill from the opposite side so a
   north-facing slope is readable rather than a silhouette. Lambert, no
   specular: this is a map, and a shiny map is a map you cannot read.

   The fog is exponential in the distance from the eye and its density is
   tied to the map's own diagonal. A fixed density swallowed his large maps
   whole; ours vary by a factor of three between installed mods, so it has to
   scale with the map rather than be a number. */
const CM3_VERT = `
attribute vec3 aPos; attribute vec3 aNormal; attribute vec2 aUv;
uniform mat4 uProj, uView;
varying vec3 vNormal; varying vec2 vUv; varying float vDepth;
void main(){
  vNormal = aNormal;
  vUv = aUv;
  vec4 eye = uView * vec4(aPos, 1.0);
  vDepth = -eye.z;
  gl_Position = uProj * eye;
}`;

const CM3_FRAG = `
precision mediump float;
varying vec3 vNormal; varying vec2 vUv; varying float vDepth;
uniform sampler2D uTex;
uniform vec3 uFlat;       // the water's colour, ignored while uTextured is 1
uniform float uTextured;  // 1 land, 0 water
uniform float uAlpha;
uniform float uFog;       // density, scaled to the map's diagonal
uniform vec3 uFogColour;
void main(){
  vec3 base = uTextured > 0.5 ? texture2D(uTex, vUv).rgb : uFlat;
  vec3 n = normalize(vNormal);
  vec3 key  = normalize(vec3(0.55, 0.72, 0.42));
  vec3 fill = normalize(vec3(-0.45, 0.35, -0.38));
  float lit = 0.55
            + 1.05 * max(dot(n, key), 0.0)
            + 0.34 * max(dot(n, fill), 0.0);
  vec3 c = base * lit * vec3(1.0, 0.975, 0.93);
  float f = 1.0 - exp(-pow(vDepth * uFog, 2.0));
  c = mix(c, uFogColour, clamp(f, 0.0, 1.0));
  gl_FragColor = vec4(c, uAlpha);
}`;

/* ---------- mounting ---------- */

/* One frame, so the "Building the mesh" line is actually on screen before a
   quarter of a million vertices are built on this thread.

   A BARE `requestAnimationFrame` IS NOT ENOUGH AND THE FAULT IS NOT
   HYPOTHETICAL: a browser stops servicing rAF entirely for a tab that is not
   being rendered, so switching tab or minimising the window between pressing
   the button and the mesh being built left the promise unresolved forever and
   the screen sitting on "Building the mesh" with no scene and no error. Found
   exactly that way while testing this mode in a background tab.

   So the frame is RACED against a timer. Whichever arrives first, the build
   goes ahead; a hidden tab takes the timer and paints nothing, which is the
   right answer because there was nothing to see either. */
function cm3Yield(){
  return new Promise(ok => {
    let done = false;
    const go = () => { if(!done){ done = true; ok(); } };
    requestAnimationFrame(go);
    setTimeout(go, 120);
  });
}

/* Build the scene, or say why not.

   The heights layer is FETCHED IF IT IS NOT HERE, whether or not it is
   ticked: this mode is the heights layer read as a shape instead of as grey,
   so it needs the bytes even when nobody is looking at the layer. It goes
   through the screen's own `cmapFetchLayer`, so it arrives as raw RGB like
   every other read here, for 20c's reason - a browser may alter a picture's
   pixels and this one is measuring them. */
async function cm3Mount(){
  const c = state.cmap;
  if(!c || !cm3On()) return;
  const d = cm3State();
  cm3Stop();
  const L = c.layers.heights;
  if(!L || !L.def.present)
    return cm3Fail('This map has no map_heights.tga, so there is no shape to draw.');
  cm3Say('Reading the heights…');
  if(!L.raw && !L.loading) await cmapFetchLayer(c, 'heights');
  else if(L.loading) await new Promise(ok => {
    const t = setInterval(() => { if(!L.loading){ clearInterval(t); ok(); } }, 40);
  });
  if(state.cmap !== c || !cm3On()) return;
  const raw = cmapRawOf(L);
  if(!raw) return cm3Fail(L.failed || 'The heights layer would not load.');
  cmapCompose();
  cm3Say('Building the mesh…');
  await cm3Yield();
  if(state.cmap !== c || !cm3On()) return;
  try{
    cm3Begin(c, d, raw);
  }catch(e){
    return cm3Fail(errText(e));
  }
  if(!d.fitted) cm3Fit();
  cm3Say('');
  const card = document.getElementById('cm3Card');
  if(card) card.innerHTML = cm3CardHtml();
}

function cm3Begin(c, d, raw0){
  const cv = document.getElementById('cm3Canvas');
  if(!cv) throw new Error('the 3D canvas is not on the page');
  const gl = cv.getContext('webgl', {antialias: true, alpha: false})
          || cv.getContext('experimental-webgl');
  if(!gl) throw new Error('this browser will not give the page a WebGL context');

  let raw = raw0, thinned = 0;
  if(!gl.getExtension('OES_element_index_uint') && raw.w * raw.h > 65535){
    thinned = Math.ceil(Math.sqrt(raw.w * raw.h / 65535));
    raw = cm3Thin(raw, thinned);
  }
  const mesh = cm3Build(raw, d.height);
  const prog = v3Program(gl, CM3_VERT, CM3_FRAG);
  if(!prog) throw new Error('the terrain shader would not compile');

  const buf = (data, target) => {
    const b = gl.createBuffer();
    gl.bindBuffer(target, b);
    gl.bufferData(target, data, gl.STATIC_DRAW);
    return b;
  };
  const AB = gl.ARRAY_BUFFER, EB = gl.ELEMENT_ARRAY_BUFFER;

  const texCv = cm3Pot(cm3Texture(), gl.getParameter(gl.MAX_TEXTURE_SIZE));
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, texCv);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  // Magnified with NEAREST, which is `cmapPaint`'s own rule one step further
  // out: this is a tool for seeing which tile a thing stands on, and a tile
  // blurred up is fog over the tile you are trying to look at.
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const texKey = cm3TexKey(c);
  const aniso = gl.getExtension('EXT_texture_filter_anisotropic')
             || gl.getExtension('WEBKIT_EXT_texture_filter_anisotropic');
  if(aniso) gl.texParameteri(gl.TEXTURE_2D, aniso.TEXTURE_MAX_ANISOTROPY_EXT,
    Math.min(8, gl.getParameter(aniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));

  cm3 = {
    gl, prog, tex, mesh, thinned,
    bPos: buf(mesh.pos, AB), bNrm: buf(mesh.nrm, AB), bUv: buf(mesh.uv, AB),
    bIdx: buf(mesh.idx, EB),
    wPos: buf(cm3WaterVerts(c, d), AB),
    wNrm: buf(new Float32Array([0,1,0, 0,1,0, 0,1,0, 0,1,0, 0,1,0, 0,1,0]), AB),
    wUv: buf(new Float32Array(12), AB),
    idxType: mesh.big ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT,
    span: Math.hypot(c.man.width, c.man.height),
    raf: 0, dirty: true, texKey,
    loc: {
      aPos: gl.getAttribLocation(prog, 'aPos'),
      aNormal: gl.getAttribLocation(prog, 'aNormal'),
      aUv: gl.getAttribLocation(prog, 'aUv'),
      uProj: gl.getUniformLocation(prog, 'uProj'),
      uView: gl.getUniformLocation(prog, 'uView'),
      uTex: gl.getUniformLocation(prog, 'uTex'),
      uFlat: gl.getUniformLocation(prog, 'uFlat'),
      uTextured: gl.getUniformLocation(prog, 'uTextured'),
      uAlpha: gl.getUniformLocation(prog, 'uAlpha'),
      uFog: gl.getUniformLocation(prog, 'uFog'),
      uFogColour: gl.getUniformLocation(prog, 'uFogColour'),
    },
  };
  cm3Pointers(cv);
  cm3Loop();
}

//: The water, two triangles over the whole map and a tenth wider each way so
//: its own edge is never the thing being looked at.
function cm3WaterVerts(c, d){
  const m = c.man, ww = m.width * 0.55, wh = m.height * 0.55;
  const wy = d.height * CM3_WATER;
  return new Float32Array([
    -ww, wy, -wh,  ww, wy, -wh,  ww, wy,  wh,
    -ww, wy, -wh,  ww, wy,  wh, -ww, wy,  wh,
  ]);
}

/* ---------- the camera ---------- */

/* The whole map in the frame, from the south east, tilted.

   The distance comes out of the map's own diagonal and the field of view
   rather than being picked, so a 200-tile map and a 510-tile map are framed
   the same way.

   AGAINST THE NARROWER OF THE TWO ANGLES, which is the part worth stating.
   The vertical field of view is fixed and the horizontal one follows the
   aspect, so on this screen - a stage with a panel down one side and a bar
   across the bottom - the horizontal is usually the tighter of the two, and
   fitting to the vertical alone ran the map off both sides. The map is
   treated as a sphere around its centre with the diagonal for a diameter:
   slightly generous on a square map, and generous is the side to be on. */
function cm3Fit(){
  const c = state.cmap;
  if(!c) return;
  const d = cm3State(), m = c.man;
  const cv = document.getElementById('cm3Canvas');
  const aspect = (cv && cv.clientHeight) ? (cv.clientWidth / cv.clientHeight) : 1;
  const halfY = 0.48;                                   // 55 degrees, halved
  const halfX = Math.atan(Math.tan(halfY) * Math.max(0.2, aspect));
  const radius = Math.hypot(m.width, m.height) / 2;
  d.yaw = -0.6; d.pitch = 0.85;
  d.dist = radius / Math.sin(Math.min(halfY, halfX));
  d.tx = 0; d.tz = 0;
  d.fitted = true;
  if(cm3) cm3.dirty = true;
}

//: Where the eye is, from the three numbers the orbit keeps. Pitch is
//: clamped just short of the horizon at the bottom and just short of
//: straight down at the top: below the horizon you are under the map, and
//: exactly overhead the up vector and the view direction are parallel and
//: the matrix degenerates.
function cm3Eye(d){
  const p = Math.max(0.05, Math.min(1.52, d.pitch));
  return [d.tx + d.dist * Math.cos(p) * Math.sin(d.yaw),
          d.dist * Math.sin(p),
          d.tz + d.dist * Math.cos(p) * Math.cos(d.yaw)];
}

/* ---------- the frame ---------- */

function cm3Size(){
  const cv = document.getElementById('cm3Canvas');
  if(!cv || !cm3) return false;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round((cv.clientWidth || 1) * dpr);
  const h = Math.round((cv.clientHeight || 1) * dpr);
  if(cv.width === w && cv.height === h) return false;
  cv.width = w; cv.height = h;
  return true;
}

/* Drawn on demand, not at sixty frames a second for nothing.

   A quarter of a million vertices redrawn on a still camera is a laptop fan
   and a battery for a picture that has not changed. Every input sets
   `dirty`; the loop itself only checks the canvas for a resize. */
function cm3Loop(){
  if(!cm3 || !cm3.gl) return;
  cm3.raf = requestAnimationFrame(cm3Loop);
  if(cm3Size()) cm3.dirty = true;
  if(!cm3.dirty) return;
  cm3.dirty = false;
  cm3Draw();
}

function cm3Draw(){
  const c = state.cmap;
  if(!cm3 || !cm3.gl || !c) return;
  const gl = cm3.gl, d = cm3State(), L = cm3.loc, cv = gl.canvas;
  gl.viewport(0, 0, cv.width, cv.height);
  gl.clearColor(CM3_SKY[0], CM3_SKY[1], CM3_SKY[2], 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);
  gl.cullFace(gl.BACK);

  const aspect = cv.width / Math.max(1, cv.height);
  // near and far off the map's own scale. A 0.1 to 100000 range on a map this
  // size spends the depth buffer on distances nothing occupies, and what
  // comes out is z-fighting in bands across the terrain - which is the fault
  // he records having had and fixed the same way.
  const proj = v3Perspective(0.96, aspect, cm3.span / 500, cm3.span * 8);
  const view = v3LookAt(cm3Eye(d), [d.tx, 0, d.tz], [0, 1, 0]);

  gl.useProgram(cm3.prog);
  gl.uniformMatrix4fv(L.uProj, false, new Float32Array(proj));
  gl.uniformMatrix4fv(L.uView, false, new Float32Array(view));
  gl.uniform1f(L.uFog, 0.35 / cm3.span);
  gl.uniform3fv(L.uFogColour, new Float32Array(CM3_SKY));
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, cm3.tex);
  gl.uniform1i(L.uTex, 0);

  const bind = (b, loc, n) => {
    if(loc < 0) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, n, gl.FLOAT, false, 0, 0);
  };

  // the land
  gl.disable(gl.BLEND);
  gl.uniform1f(L.uTextured, 1);
  gl.uniform1f(L.uAlpha, 1);
  bind(cm3.bPos, L.aPos, 3); bind(cm3.bNrm, L.aNormal, 3); bind(cm3.bUv, L.aUv, 2);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, cm3.bIdx);
  gl.drawElements(gl.TRIANGLES, cm3.mesh.count, cm3.idxType, 0);

  // the water, last and blended, so the sea floor shows through it
  if(d.water){
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.uniform1f(L.uTextured, 0);
    gl.uniform1f(L.uAlpha, 0.88);
    gl.uniform3fv(L.uFlat, new Float32Array([0.10, 0.24, 0.43]));
    bind(cm3.wPos, L.aPos, 3); bind(cm3.wNrm, L.aNormal, 3); bind(cm3.wUv, L.aUv, 2);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.disable(gl.BLEND);
  }
}

/* ---------- the pointer ---------- */

/* Left drag orbits, right or middle drag pans, the wheel zooms.

   The same three gestures as the flat map's pan and zoom and the same three
   as the model viewer's, which is the point: this tool has one set of mouse
   habits and a third one would be a third thing to learn. */
function cm3Pointers(cv){
  let drag = null;
  cv.oncontextmenu = e => e.preventDefault();
  cv.onpointerdown = e => {
    try{ cv.setPointerCapture(e.pointerId); }catch(_){}
    drag = {x: e.clientX, y: e.clientY, pan: e.button === 2 || e.button === 1};
    e.preventDefault();
  };
  cv.onpointermove = e => {
    if(!drag || !cm3) return;
    const s = cm3State();
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY;
    if(drag.pan){
      // Pan in the ground plane along the camera's own axes, scaled by how
      // far away it is, so a drag moves the map under the pointer by about
      // the same amount at every zoom.
      const k = s.dist / Math.max(1, cv.clientHeight) * 1.6;
      const sin = Math.sin(s.yaw), cos = Math.cos(s.yaw);
      s.tx -= (dx * cos + dy * sin) * k;
      s.tz -= (-dx * sin + dy * cos) * k;
    }else{
      s.yaw -= dx * 0.006;
      s.pitch = Math.max(0.05, Math.min(1.52, s.pitch + dy * 0.006));
    }
    cm3.dirty = true;
  };
  const up = e => {
    if(drag){ try{ cv.releasePointerCapture(e.pointerId); }catch(_){} }
    drag = null;
  };
  cv.onpointerup = up;
  cv.onpointercancel = up;
  cv.onwheel = e => {
    e.preventDefault();
    if(!cm3) return;
    const s = cm3State();
    // A floor scaled to the map stops the wheel driving the eye through the
    // surface, and a ceiling stops it leaving the scene behind the fog.
    const lo = Math.max(2, cm3.span / 40), hi = cm3.span * 4;
    s.dist = Math.max(lo, Math.min(hi, s.dist * (e.deltaY > 0 ? 1.12 : 1 / 1.12)));
    cm3.dirty = true;
  };
}

/* ---------- the controls ---------- */

/* The card over the map. Two switches, a Fit and two sentences, because
   everything else about this picture is set on the flat map's own controls
   and saying it twice is how two screens come to disagree. */
function cm3CardHtml(){
  const d = cm3State();
  if(!d) return '';
  const thin = (cm3 && cm3.thinned)
    ? `<p class="cm3note">This driver has no 32-bit index, so the mesh is
       every ${cm3.thinned} tiles rather than every tile.</p>` : '';
  return `
    <div class="cm3row">
      <label for="cm3H">Height</label>
      <input id="cm3H" type="range" min="${CM3_HEIGHT_MIN}" max="${CM3_HEIGHT_MAX}"
        value="${d.height}" oninput="cm3Height(this.value)"
        title="How tall the highest land stands, in tiles. 0 is flat.">
      <span class="count" id="cm3HN">${d.height}</span>
    </div>
    <div class="cm3row">
      <label><input type="checkbox" ${d.water ? 'checked' : ''}
        onchange="cm3Water(this.checked)"> Water surface</label>
      <button onclick="cm3Fit()" title="Frame the whole map again">&#8676; Fit</button>
    </div>
    ${thin}
    <p class="cm3note">Drag to orbit, right-drag to pan, wheel to zoom.</p>
    <p class="cm3note">The layers, their opacities, the season and the
      colouring are the flat map's. Change them there and they change here.
      Markers, labels and the tooltip stay on the flat map.</p>`;
}

//: The height scale moves every vertex, so the mesh is rebuilt. One pass over
//: at most 260,100 tiles, and only the positions and the normals go back to
//: the card, so it is done in place rather than by tearing the scene down.
function cm3Height(v){
  const d = cm3State();
  if(!d) return;
  const want = Math.max(CM3_HEIGHT_MIN, Math.min(CM3_HEIGHT_MAX, +v || 0));
  if(d.height === want) return;
  d.height = want;
  const n = document.getElementById('cm3HN');
  if(n) n.textContent = want;
  cm3SaveLater();
  cm3Reheight();
}

function cm3Water(on){
  const d = cm3State();
  if(!d) return;
  d.water = !!on;
  cm3SaveLater();
  if(cm3) cm3.dirty = true;
}

/* The mesh at a new height scale, and the water with it.

   Rebuilt from the layer's bytes rather than scaled out of the buffer,
   because the sea floor is pinned to a FRACTION of the scale rather than
   multiplied by it: a scale of zero has to be a flat map with the sea floor
   at zero too, not a flat map with a trench in it. */
function cm3Reheight(){
  const c = state.cmap;
  if(!cm3 || !cm3.gl || !c) return;
  const d = cm3State(), gl = cm3.gl;
  const raw0 = cmapRawOf(c.layers.heights);
  if(!raw0) return;
  const raw = cm3.thinned ? cm3Thin(raw0, cm3.thinned) : raw0;
  const mesh = cm3Build(raw, d.height);
  cm3.mesh = mesh;
  gl.bindBuffer(gl.ARRAY_BUFFER, cm3.bPos);
  gl.bufferData(gl.ARRAY_BUFFER, mesh.pos, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, cm3.bNrm);
  gl.bufferData(gl.ARRAY_BUFFER, mesh.nrm, gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, cm3.wPos);
  gl.bufferData(gl.ARRAY_BUFFER, cm3WaterVerts(c, d), gl.STATIC_DRAW);
  cm3.dirty = true;
}

let cm3SaveTimer = 0;
//: Coalesced for the same reason `cmapSaveLayers` is: a slider fires `input`
//: per pixel of travel and settings.json is rewritten whole either way.
function cm3SaveLater(){
  clearTimeout(cm3SaveTimer);
  cm3SaveTimer = setTimeout(() => {
    const d = cm3State();
    if(!d) return;
    const m = cmapSettings();
    m.d3 = {height: d.height, water: !!d.water};
    api.post('/api/settings', {map_layers: m}).catch(() => {});
  }, 400);
}

/* ---------- messages ---------- */

function cm3Say(msg){
  const el = document.getElementById('cm3Msg');
  if(!el) return;
  el.textContent = msg || '';
  el.hidden = !msg;
}

function cm3Fail(why){
  const el = document.getElementById('cm3Msg');
  if(el){
    el.innerHTML = `<b>The map cannot be drawn in 3D.</b><br>${esc(why)}`;
    el.hidden = false;
  }
}

/* ---------- letting go ---------- */

/* Give the context up. Called when the mode is switched off, when the screen
   is left and when the map is reloaded under us.

   RELEASE_2_3_3 records the fault this is written against: a 3D panel left
   over from another screen kept drawing to a page that was gone, holding a
   WebGL context for a view nobody could see. A context is a scarce thing - a
   browser drops the oldest one when a page asks for too many - so this
   deletes every buffer, the texture and the program, and then asks the
   driver for the context back, rather than dropping the object and hoping.

   AND THEN REPLACES THE CANVAS, which is the part that is not obvious and
   which cost a bug here. `WEBGL_lose_context.loseContext()` does not free a
   canvas to be drawn on again: the element keeps that one context forever
   and hands the same LOST one back to the next `getContext`, so turning the
   mode off and straight back on built a scene that never drew and left the
   screen blank with no error in it. Measured exactly that way. A canvas is
   cheap and a context is not, so the context is given up properly and the
   element is swapped for a clean clone of itself. */
function cm3Stop(){
  if(!cm3) return;
  if(cm3.raf) cancelAnimationFrame(cm3.raf);
  const gl = cm3.gl;
  if(gl){
    [cm3.bPos, cm3.bNrm, cm3.bUv, cm3.bIdx, cm3.wPos, cm3.wNrm, cm3.wUv]
      .forEach(b => b && gl.deleteBuffer(b));
    if(cm3.tex) gl.deleteTexture(cm3.tex);
    if(cm3.prog) gl.deleteProgram(cm3.prog);
    const lose = gl.getExtension('WEBGL_lose_context');
    if(lose) lose.loseContext();
  }
  cm3 = null;
  cm3FreshCanvas();
}

/* A canvas that has never held a context, in place of the one that has.

   `cloneNode(false)` copies the id, the class, the aria-label and the hidden
   flag and nothing else, which is the whole of what this element is. Skipped
   when the canvas is already gone from the page, which is `cm3DropOrphan`'s
   case and needs no replacement. */
function cm3FreshCanvas(){
  const old = document.getElementById('cm3Canvas');
  if(!old || !old.parentNode) return;
  const fresh = old.cloneNode(false);
  fresh.width = 0; fresh.height = 0;
  old.parentNode.replaceChild(fresh, old);
}

/* The mode, let go of because the screen it was on is gone.

   `v3DropOrphan`'s case exactly, and called from the same place: the mode
   switched, the new screen wrote over `#main`, and the canvas this was
   drawing to is simply not in the document any more. */
function cm3DropOrphan(){
  if(!cm3) return;
  if(document.getElementById('cm3Canvas')) return;
  cm3Stop();
}

/* Everything the texture is built out of, as one string.

   `compKey` is the layer stack, its opacities, its order and its punched
   colours, which `cmapCompose` already keys. What it does NOT carry is the
   two things drawn either side of the composite: 23a's ground, whose season
   and gap change the picture without touching a single layer's key, and
   16g's colouring, which is deliberately not in the composite at all because
   a tint has to be read against the terrain under it. Those are added here,
   so this key is the whole of what `cm3Texture` would draw. */
function cm3TexKey(c){
  const t = c.terrain || {};
  return [c.compKey,
          cmapTerrainOn(c) ? `${t.key || ''}|${t.scale || 1}` : 'flat',
          c.overlayKey || '', c.overlayFill || '', c.overlayAlpha,
          c.overlayEdge ? 1 : 0].join('␟');
}

/* The picture changed under us: a layer ticked, an opacity dragged, a stroke
   painted, a season flipped, a gap recoloured, a colouring applied.

   Called from `cmapPaint`, which is the one funnel every one of those ends
   in, and keyed so that the pans, the hovers and the resizes that also end
   there cost a string compare instead of a four-megapixel upload. Only the
   TEXTURE is rebuilt, never the mesh: none of those moves a tile's height.
   Painting the HEIGHTS layer does, and `cmapAfterPaint` calls `cm3Remesh`
   for that case instead. */
function cm3Retexture(force){
  if(!cm3 || !cm3.gl || !cm3On()) return;
  const c = state.cmap;
  if(!c) return;
  const key = cm3TexKey(c);
  if(!force && key === cm3.texKey) return;
  const cv = cm3Texture();
  if(!cv) return;
  const gl = cm3.gl;
  const texCv = cm3Pot(cv, gl.getParameter(gl.MAX_TEXTURE_SIZE));
  gl.bindTexture(gl.TEXTURE_2D, cm3.tex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, texCv);
  gl.generateMipmap(gl.TEXTURE_2D);
  cm3.texKey = key;
  cm3.dirty = true;
}

//: The heights themselves moved: a stroke on that layer, an undo, a redo.
//: The texture goes with them, forced, because a stroke that changed only the
//: heights leaves every other part of the key exactly where it was.
function cm3Remesh(){
  if(!cm3 || !cm3On()) return;
  cm3Reheight();
  cm3Retexture(true);
}
