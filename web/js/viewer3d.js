/* viewer3d.js - the 3D model viewer

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   THE MODEL VIEWER - a battle model, drawn, from the entry that names it.

   Plain WebGL, no library. A static textured model needs one shader, one
   orbit camera and a texture bind, and the alternative was vendoring 600 KB
   of three.js into a project whose whole point is that it has no build step.

   The geometry arrives from /api/model/geometry as ONE binary payload, not
   as JSON: a soldier is a few thousand vertices and spelling those floats
   out as text costs about six times the bytes and a parse on top. The header
   is JSON, the arrays are raw, and each one goes straight into a buffer.

   Four things about the format drive the whole UI here (see mesh.py):

     * indices are GLOBAL into one shared vertex pool, so a group is a face
       range rather than a mesh of its own - one buffer, one draw call per
       visible group, no per-group vertex data;
     * a group is named `type` + `mesh name` - the two halves of the Blender
       addon's `objectname__comment` - and carries a required/optional flag,
       its `__opt`. Groups sharing a TYPE are variants of one part and the game
       picks one per soldier. Drawing them all at once puts three heads on one
       man, so the viewer picks one per part and offers the others, which is
       also how you look at what a mod actually shipped;
     * a model is painted from the main and attachment textures GLUED into
       one image, main in u 0..1 and attachment in u 1..2, tiling in both
       axes outside that. The UVs address the pair, so they go to the
       shader untouched and no code chooses a sheet for a part;
     * the models are LEFT-handed (Direct3D). Handed straight to a right-handed
       viewer they come out mirrored - shield on the wrong arm - so the model
       matrix negates X.
   ========================================================================= */

/* --- small matrix helpers -------------------------------------------------
   Only the four operations a fixed-function camera needs. Column-major, the
   order WebGL wants, so they go to uniformMatrix4fv untransposed. */
function v3Perspective(fovY, aspect, near, far){
  const f = 1 / Math.tan(fovY / 2), d = near - far;
  return [f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)/d,-1, 0,0,2*far*near/d,0];
}
function v3LookAt(eye, at, up){
  const z = v3Norm([eye[0]-at[0], eye[1]-at[1], eye[2]-at[2]]);
  const x = v3Norm(v3Cross(up, z));
  const y = v3Cross(z, x);
  return [x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
          -v3Dot(x,eye), -v3Dot(y,eye), -v3Dot(z,eye), 1];
}
function v3Cross(a,b){ return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]; }
function v3Dot(a,b){ return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
function v3Norm(a){
  const L = Math.hypot(a[0],a[1],a[2]) || 1;
  return [a[0]/L, a[1]/L, a[2]/L];
}

/* --- the environment ------------------------------------------------------
   A procedural stand-in for the studio HDRI Blender lights its viewport with.
   Shipping a real .hdr would mean a megabyte of asset and a decoder for it, and
   for an inspection viewer the part of an HDRI that matters is the part this
   reproduces: sky above, ground below, a bright band at the horizon, and light
   arriving from every direction rather than from one lamp. The SAME function
   paints the backdrop and lights the model, which is what makes a model look
   like it is standing in the scene instead of floating on a flat colour.

   It is also why the background is no longer near-black: a dark unit on a dark
   field is unreadable, and armour has nothing to reflect. */
const V3_ENV = `
vec3 v3Env(vec3 d){
  vec3 sky     = vec3(0.36, 0.45, 0.62);
  vec3 horizon = vec3(0.78, 0.79, 0.80);
  vec3 ground  = vec3(0.24, 0.22, 0.20);
  float t = clamp(d.y, -1.0, 1.0);
  return t > 0.0 ? mix(horizon, sky, pow(t, 0.55))
                 : mix(horizon, ground, pow(-t, 0.40));
}`;

const V3_VERT = `
attribute vec3 aPos; attribute vec3 aNormal; attribute vec2 aUv;
uniform mat4 uProj, uView; uniform mat4 uModel;
varying vec3 vNormal; varying vec2 vUv;
void main(){
  // uModel mirrors X (see v3Draw), and for a mirror the inverse-transpose that
  // normals want is the matrix itself - so mat3(uModel) is right here.
  vNormal = mat3(uModel) * aNormal;
  vUv = aUv;
  gl_Position = uProj * uView * uModel * vec4(aPos, 1.0);
}`;

/* ONE texture, and it is usually the two sheets side by side.

   This is how the game does it and it is not the same thing as picking a sheet
   per part. A model's modeldb entry names a main texture and an attachment
   texture; the game lays them out as one image twice as wide, main on the left
   and attachment on the right, and the mesh's single UV set addresses THAT.
   So u 0..1 lands on the main sheet, u 1..2 lands on the attachment sheet, and
   anything outside repeats - the whole pair tiles, infinitely, in both axes.

   Which is why the shader does nothing clever: the UVs go in as the modeller
   authored them and only the scaling that turns "the sheets the entry named"
   into "one texture wide" is applied. That scaling is NOT redundant with
   anything the decoder does, and removing it is the bug to not reintroduce: the
   FILE stores u normalised over the pair (main 0..0.5), mesh.py doubles it on
   read into the space above - the space IWTE and the Blender addon use - and
   this brings it back down to land in the bound texture. Take either step out
   and every model samples a squeezed stripe of one sheet. Nothing is wrapped,
   folded or normalised into 0..1, and no branch decides a part's sheet - the
   coordinate already says. The 112 groups with u < 0 and the 268 with v outside
   0..1 in one mod alone are the proof that the tiling is real and must not be
   clamped away.

   `uUScale` is 0.5 whenever what is bound SPANS those two units, and 1.0 only
   when it is one sheet the game would have glued to a copy of itself. Three
   cases, not two, and collapsing them to two was a bug that hit every mount in
   every mod (see `v3Apply`):

     * a real pair, glued here into one image two sheets wide - halved;
     * an entry naming NO attachment texture, which is every ordinary mount.
       There is nothing to glue and no second half to reach: its one sheet is
       the whole space, so it is halved too. Binding it at full u instead tiles
       it twice across the model, which is a horse painted in texels twice as
       wide as they are tall;
     * an entry that NAMES an attachment this viewer did not glue - the main
       file over again (which mods write all the time, and which is what the
       Blender addon exports for an empty slot), or one the mod does not ship.
       The GAME glues two sheets there, so the art really does repeat every
       unit, and binding the one sheet at FULL u reproduces main-glued-to-main
       exactly - no canvas, no second decode, half the texture memory, and a
       1024 skin stays a power of two instead of pushing the atlas to 2048. */
/* UV mode paints the coordinate instead of the art, in the SAME space the
   texture sample uses - `vUv` as the modeller authored it, main sheet 0..1,
   attachment sheet 1..2, everything outside a repeat. Nothing is clamped or
   folded here either, for the same reason the sampler does not: the wrapping is
   the thing being shown.

   Four facts, one picture:

     * **the checker** - 32 cells to a sheet, so a stretched cell is art
       stretched over that triangle and a mirrored one is a flipped shell.
       32 is measured, not picked: the parts of a real unit span 0.07 to 0.33
       of u each (a head 0.07, a body 0.30, a leg 0.33), so a coarser grid
       gives a head less than one whole cell and says nothing about it;
     * **the tint** - blue is the main sheet, amber the attachment sheet, and it
       is `mod(floor(u), 2.0)` that decides, never a per-part rule, because a
       group whose UVs run 0.41..1.38 really is one piece of art crossing the
       seam and has to read as both;
     * **the dimming** - the two units of u the model was UNWRAPPED in stay
       bright and everything past them goes dark. Always two, for every model:
       the file normalises u over the pair and mesh.py doubles it whatever the
       entry turns out to name;
     * **the lines** - white at a sheet edge, red where the art starts over.
       Those are two different places for a sheet glued to a copy of itself,
       which is why the red line is on its own period. Fixed width in UV space,
       not screen space, because `fwidth` wants an extension this viewer does
       not ask for.

   An entry with no attachment sheet has no amber on it - there is no second
   sheet to tell apart - but it still fills both units, and its red line still
   falls every second one. */
const V3_UV = `
vec3 v3UvPaint(vec2 uv, float wide, float pair){
  // "wide" is whether one copy of the ART is two units of u (a glued pair, or a
  // lone sheet spanning the space) or one (a sheet glued to a copy of itself).
  // "pair" is the different question of whether there are two sheets to tell
  // apart - only then does amber mean anything.
  float period = wide > 0.5 ? 2.0 : 1.0;
  float attach = pair > 0.5 ? mod(floor(uv.x), 2.0) : 0.0;
  vec3 col = mix(vec3(0.29, 0.51, 0.80), vec3(0.88, 0.56, 0.20), attach);
  vec2 cell = floor(uv * 32.0);
  col *= mix(0.60, 1.0, mod(cell.x + cell.y, 2.0));
  // tile (0,0) is the art as authored; everything else on screen is the wrap
  if(floor(uv.x / period) != 0.0 || floor(uv.y) != 0.0) col *= 0.42;
  const float w = 0.004;   // a third of a cell; thicker and it eats the grid
  float edge = min(abs(uv.x - floor(uv.x + 0.5)), abs(uv.y - floor(uv.y + 0.5)));
  col = mix(col, vec3(1.0), (1.0 - smoothstep(0.0, w, edge)) * 0.85);
  float restart = abs(uv.x / period - floor(uv.x / period + 0.5)) * period;
  col = mix(col, vec3(1.0, 0.24, 0.34), (1.0 - smoothstep(0.0, w, restart)) * 0.9);
  return col;
}`;

const V3_FRAG = `
precision mediump float;
varying vec3 vNormal; varying vec2 vUv;
uniform sampler2D uTex;
uniform float uHasTex, uFlat, uUScale, uUv, uPair;
uniform vec3 uKey, uEye;
${V3_ENV}
${V3_UV}
void main(){
  vec4 base = uHasTex > 0.5
    ? texture2D(uTex, vec2(vUv.x * uUScale, vUv.y))
    : vec4(0.72, 0.66, 0.56, 1.0);
  if(base.a < 0.35) discard;          // the alpha channel is a cut-out mask
  if(uFlat > 0.5){ gl_FragColor = vec4(0.92, 0.94, 0.98, 1.0); return; }
  // the coordinate stands in for the art, and is then lit like the art, so the
  // form still reads and you can see which way a shell is wrapped over it
  if(uUv > 0.5) base.rgb = v3UvPaint(vUv, uUScale < 0.75 ? 1.0 : 0.0, uPair);

  vec3 n = normalize(vNormal);
  // ambient straight out of the environment, so a surface facing the sky picks
  // up the sky and one facing the floor goes warm and dark
  vec3 light = v3Env(n) * 0.62;
  light += vec3(1.00, 0.96, 0.90) * 0.50 * max(dot(n, normalize(uKey)), 0.0);
  light += vec3(0.62, 0.70, 0.85) * 0.20 * max(dot(n, normalize(vec3(-0.6, 0.2, -0.7))), 0.0);
  light += vec3(1.0) * 0.18 * max(dot(n, normalize(uEye)), 0.0);   // fill from the camera
  // Unit art is sRGB and this multiply is linear, so a light of 0.5 lands far
  // darker than half-lit looks - which is how a viewer of dark armour and dark
  // cloth ends up a viewer of silhouettes. The curve lifts the mid-tones back
  // without touching what is already fully lit. An inspection tool, not a
  // render: you have to be able to SEE the thing.
  gl_FragColor = vec4(pow(clamp(base.rgb * light, 0.0, 1.0), vec3(0.78)), 1.0);
}`;

/* The backdrop: one full-screen triangle, each pixel asking the environment
   what lies along its own view ray - so the horizon sits still while the model
   turns, and pitching the camera up shows sky and down shows ground. */
const V3_BG_VERT = `
attribute vec2 aQuad;
uniform vec3 uRight, uUp, uFwd; uniform vec2 uScale;
varying vec3 vDir;
void main(){
  vDir = normalize(uFwd + uRight * aQuad.x * uScale.x + uUp * aQuad.y * uScale.y);
  gl_Position = vec4(aQuad, 0.999, 1.0);
}`;

const V3_BG_FRAG = `
precision mediump float;
varying vec3 vDir;
${V3_ENV}
void main(){
  // a touch darker than the light it casts, so the model reads against it
  gl_FragColor = vec4(v3Env(normalize(vDir)) * 0.55, 1.0);
}`;

let v3 = null;          // the live viewer, or null when the dialog is closed
let v3Back = null;      // the dialog we opened over, to put back on close

/* --- opening -------------------------------------------------------------- */

async function v3Open(mod, entry){
  const modal = document.getElementById('modal');
  const overlay = document.getElementById('overlay');
  const wasOpen = overlay.classList.contains('open');
  // The unit editor's preview column is a live canvas parked in the modal, and
  // `modal.innerHTML` would stash a DEAD COPY of it - restored on the way out as
  // a blank canvas nothing is drawing to, beside a real one with no parent. Take
  // it out before the snapshot; v3Close puts it back properly.
  if(typeof edPrevDetach === 'function') edPrevDetach();
  if(typeof cmpPrevDetach === 'function') cmpPrevDetach();
  v3Back = wasOpen ? {html: modal.innerHTML, cls: modal.className, scroll: stashPlace()} : {};
  modal.className = 'modal wide';
  modal.innerHTML = `<h2>Model - ${esc(entry)}</h2>
    <div class="mbody"><div class="empty">Reading ${esc(entry)}…</div></div>
    <div class="foot"><button onclick="v3Close()">Close</button></div>`;
  overlay.classList.add('open');
  await v3Begin(mod, entry, '');
}

/* --- the same viewer, in a panel the page owns -----------------------------
   `v3Open` takes the modal over, which is right when looking at a model IS what
   you came to do. It is the wrong shape for the two places that want the model
   BESIDE something else: the unit editor, where the preview sits next to the
   fields being edited, and the BMDB browser, where it sits next to the list.
   Both hand in the id of an element to paint into instead, and everything below
   this line - the controls, the parts list, the orbit, the WebGL - is the same
   code either way.

   Still ONE viewer at a time. A second WebGL context on the same page is a
   second copy of a 30 MB mesh and a second animation loop, for a second view of
   a model nobody is looking at; mounting somewhere new drops what was there. */
async function v3Mount(hostId, mod, entry){
  if(v3 && v3.host === hostId && v3.entry === entry && v3.mod === mod) return;
  v3Stop();
  v3Back = null; v3 = null;
  const host = document.getElementById(hostId);
  if(!host) return;
  host.innerHTML = `<div class="empty">Reading ${esc(entry)}…</div>`;
  await v3Begin(mod, entry, hostId);
}

/* Let go of a docked viewer without touching the modal. */
function v3Unmount(){
  if(!v3 || !v3.host) return;
  const host = document.getElementById(v3.host);
  v3Stop();
  if(host) host.innerHTML = '';
  v3 = null;
}

/* --- the strat map's models, 16k -------------------------------------------
   A .cas is the campaign map's model - a settlement, a general, a resource -
   and it is a different file format read by a different decoder. It reaches
   this viewer as the same payload a .mesh does, because cas.as_mesh lays a
   scene's meshes into one vertex pool and hands back the same MeshFile; what
   is different is everything ABOVE the geometry, and all of it is here:

     * there are no LODs and no skins. A .cas is one model at one detail, and
       it names its own textures instead of getting them from a modeldb entry;
     * it can want SEVERAL textures at once. A settlement is walls, buildings
       and a faction banner with a material each, so the draw loop binds per
       group rather than once for the model;
     * u is not halved. A .mesh addresses a pair of sheets glued side by side
       and this one does not - its UVs run 0 to 1 on the one sheet named
       against that mesh, which is the reason v3Apply asks v3.cas first.

   Everything else - the orbit, the framing, the wireframe, the grip bar - is
   the same code, and that is the point of routing it through here at all. */
async function v3OpenCas(mod, rel){
  const modal = document.getElementById('modal');
  const overlay = document.getElementById('overlay');
  const wasOpen = overlay.classList.contains('open');
  if(typeof edPrevDetach === 'function') edPrevDetach();
  if(typeof cmpPrevDetach === 'function') cmpPrevDetach();
  v3Back = wasOpen ? {html: modal.innerHTML, cls: modal.className, scroll: stashPlace()} : {};
  const name = rel.split('/').pop();
  modal.className = 'modal wide';
  modal.innerHTML = `<h2>Strat model - ${esc(name)}</h2>
    <div class="mbody"><div class="empty">Reading ${esc(name)}…</div></div>
    <div class="foot"><button onclick="v3Close()">Close</button></div>`;
  overlay.classList.add('open');
  await v3Begin(mod, name, '', rel);
}

/* The same, docked into a panel the page owns - see v3Mount. */
async function v3MountCas(hostId, mod, rel){
  if(v3 && v3.host === hostId && v3.cas === rel && v3.mod === mod) return;
  v3Stop();
  v3Back = null; v3 = null;
  const host = document.getElementById(hostId);
  if(!host) return;
  host.innerHTML = `<div class="empty">Reading ${esc(rel.split('/').pop())}…</div>`;
  await v3Begin(mod, rel.split('/').pop(), hostId, rel);
}

async function v3Begin(mod, entry, host, cas){
  // Whatever was showing goes first. Two WebGL contexts on one page is two
  // copies of a 30 MB mesh and two animation loops, one of them for a view
  // nobody can see any more.
  v3Stop();
  v3 = null;
  let info;
  const url = cas ? `/api/map/model?mod=${enc(mod)}&rel=${enc(cas)}`
                  : `/api/model?mod=${enc(mod)}&entry=${enc(entry)}`;
  try{ info = await api.get(url); }
  catch(e){ return v3Fail(''+e, host); }
  if(info.error) return v3Fail(info.error, host);

  // `skin` indexes info.skins, because a skin is a PAIR of files now - the
  // main sheet and the attachment sheet a faction uses together - and a pair
  // has no one path to name it by
  v3 = {mod, entry, info, cas: cas || '', host: host || '', lod: 0, skin: 0,
        geo: null, tex: null, texAtt: null, hidden: {}, variant: {},
        wire: false, spin: false, uv: false,
        // the UV layout pane: whether it is open, how it is framed (null until
        // it first opens and can measure itself), and which island is named
        uved: false, uvv: null, uvSel: null, uvOpt: {tex: true, solo: false},
        yaw: 0.6, pitch: 0.25, dist: 3, centre: [0,0,0], gl: null, err: ''};
  if(cas){
    // material path as the file writes it -> where that file really is under
    // data/, which the server resolved because only it can look on disk
    v3.casRel = new Map((info.materials||[])
      .filter(m => m.texture).map(m => [m.texture, m.rel || '']));
  }else{
    // open on the first LOD the mod actually ships - an entry whose lod0 lives
    // in a .pack still has lod1 and lod2 on disk more often than not
    const there = info.lods.find(l => l.exists);
    v3.lod = there ? there.index : 0;
  }
  v3Render();
  await v3Load();
}

// Where the viewer paints: the modal's body, or the element whose id was handed
// to `v3Mount`. Everything that repaints part of the viewer looks it up through
// here, so nothing below has to know which of the two it is in.
function v3HostEl(host){
  const id = host !== undefined ? host : (v3 ? v3.host : '');
  return id ? document.getElementById(id) : document.querySelector('#modal .mbody');
}

/* What to call a skin in the picker: the faction that uses it, and how many
   others share it. A skin used by everyone is named for the file instead -
   there is no one faction it belongs to. */
function v3SkinLabel(s){
  const n = (s.factions||[]).length;
  if(n === 0) return (s.rel || 'no texture').split('/').pop();
  if(n === 1) return facLabel(s.factions[0]);
  return `${facLabel(s.factions[0])} +${n-1} more`;
}

/* The skin the viewer is on, and its two sheets. */
function v3Skin(){ return (v3.info.skins || [])[v3.skin] || null; }

function v3Fail(msg, host){
  const b = v3HostEl(host);
  if(b) b.innerHTML = `<div class="w-bad">${esc(msg)}</div>`;
}

function v3Close(){
  if(v3 && v3.host) return v3Unmount();
  v3Stop();
  const modal = document.getElementById('modal');
  if(v3Back && v3Back.html !== undefined){
    modal.className = v3Back.cls; modal.innerHTML = v3Back.html;
    usePlace(v3Back.scroll);
    // the restored markup is inert until its own module rebinds it, and only
    // the model card ever opens this - so it is the one that gets asked
    if(typeof edRenderTab === 'function' && state.ed) edRenderTab();
    // the live preview column, taken out above, goes back where it belongs
    if(typeof edPrevAttach === 'function' && state.ed) edPrevAttach();
    if(typeof cmpPrevAttach === 'function' && !state.ed) cmpPrevAttach();
  }else{
    document.getElementById('overlay').classList.remove('open');
    modal.className = 'modal'; modal.innerHTML = '';
  }
  v3Back = null; v3 = null;
}

// Stop drawing without giving anything up. See the tick loop in v3Start.
function v3Pause(on){ if(v3) v3.paused = !!on; }

function v3Stop(){
  if(v3 && v3.raf) cancelAnimationFrame(v3.raf);
  if(v3 && v3.gl){
    const gl = v3.gl;
    [v3.bPos, v3.bNormal, v3.bUv, v3.bIdx, v3.bLines, v3.bQuad]
      .forEach(b => b && gl.deleteBuffer(b));
    if(v3.texture) gl.deleteTexture(v3.texture);
    [v3.prog, v3.bg].forEach(p => p && gl.deleteProgram(p));
  }
  if(v3) v3.gl = null;
}

/* --- the dialog ----------------------------------------------------------- */

function v3Render(){
  if(!v3) return;
  const i = v3.info;
  const lods = i.lods.map(l =>
    `<option value="${l.index}" ${l.index===v3.lod?'selected':''} ${l.exists?'':'disabled'}>
       LOD ${l.index}${l.distance?` · from ${l.distance}m`:''}${l.exists?'':' - not in this mod'}
     </option>`).join('');
  // one option per PAIR of files: an entry that lists 29 factions against the
  // same main and attachment textures has one skin, and saying so is more use
  // than 29 identical rows
  const skins = i.skins.length
    ? i.skins.map((s, n) => `<option value="${n}" ${n===v3.skin?'selected':''}
        ${s.exists?'':'disabled'}>${esc(v3SkinLabel(s))}${s.exists?'':' - not in this mod'}</option>`).join('')
    : '<option>no skins on this entry</option>';

  const host = v3HostEl();
  if(!host) return;
  // Docked, the panel is a column: the controls go UNDER the canvas rather than
  // beside it, because 300px of width does not hold both.
  host.innerHTML = `
    <div class="v3wrap${v3.host ? ' dock' : ''}">
      <div class="v3stage${v3.uved ? ' uv' : ''}" id="v3stage">
        <div class="v3gl">
          <canvas id="v3canvas"></canvas>
          <div class="v3hint">drag to turn · wheel to zoom · right-drag to pan</div>
          <div class="v3msg" id="v3msg"></div>
        </div>
        <div class="v3uvpane">
          <div class="v3uvbar">
            <label><input type="checkbox" ${v3.uvOpt.tex?'checked':''}
              onchange="v3UvOpt('tex', this.checked)"> Sheet</label>
            <label title="Draw only the island you picked, for a part buried under the others"><input
              type="checkbox" ${v3.uvOpt.solo?'checked':''}
              onchange="v3UvOpt('solo', this.checked)"> Just this part</label>
            <button onclick="v3UvFit()">Fit</button>
          </div>
          <div class="v3uvsel" id="v3uvsel"></div>
          <div class="v3uvstage">
            <canvas id="v3uvcanvas"></canvas>
            <div class="v3hint" id="v3uvpos">drag to pan · wheel to zoom · click an island</div>
          </div>
        </div>
      </div>
      ${v3.host ? `<div class="v3grip" onpointerdown="v3GripDown(event)"
        ondblclick="v3GripReset()"
        title="Drag to give the model more room, or its controls more · double-click for the default"></div>` : ''}
      <aside class="v3side">
        ${v3.cas ? '' : `<button class="v3roll" onclick="v3Randomize()" title="Pick a variant for every part the way the game does, one soldier at a time">🎲 Randomize variations</button>
        <label class="v3f"><span>Level of detail</span>
          <select onchange="v3SetLod(this.value)">${lods}</select></label>
        <label class="v3f"><span>Skin</span>
          <select onchange="v3SetSkin(this.value)" ${i.skins.length?'':'disabled'}>${skins}</select></label>`}
        <div class="v3btns">
          <button id="v3spin" class="${v3.spin?'on':''}" onclick="v3Toggle('spin')">Rotate</button>
          <button id="v3wire" class="${v3.wire?'on':''}" onclick="v3Toggle('wire')">Wireframe</button>
          <button id="v3uv" class="${v3.uv?'on':''}" onclick="v3Toggle('uv')"
            ${(v3.geo && !v3.geo.has_uvs) ? 'disabled title="This model carries no UV set"' : 'title="Paint the UV coordinate instead of the art: blue is the main sheet, amber the attachment sheet, and the dark tiles are the sheets repeating"'}>Show UVs</button>
          <button id="v3uved" class="${v3.uved?'on':''}" onclick="v3Toggle('uved')"
            ${(v3.geo && !v3.geo.has_uvs) ? 'disabled title="This model carries no UV set"' : 'title="Open the UV layout beside the model: the texture sheet with this model&#39;s islands drawn over it, the way a UV editor shows them"'}>UV layout</button>
          <button onclick="v3Frame()">Recentre</button>
        </div>
        <div id="v3uvkey"></div>
        <div class="v3parts" id="v3parts"></div>
        <div class="v3facts" id="v3facts"></div>
      </aside>
    </div>`;
  v3Parts();
  v3Facts();
  v3UvKey();
  const c = document.getElementById('v3canvas');
  if(c && v3.geo) v3Start(c);
  // The pane is in the markup whether or not it is showing - CSS hides it - so
  // opening it is a class flip rather than a rebuild, and a rebuild does not
  // tear down the GL context the model is living in.
  const uc = document.getElementById('v3uvcanvas');
  if(uc && v3.geo){ v3UvPointers(uc); v3UvBar(); if(v3.uved) v3UvEdDraw(); }
  v3GripInstall();
}

/* --- the grab bar between the canvas and its controls (docked only) --------
   `splitInstall` gives the docked viewer a draggable LEFT edge, so the column
   can be made wider than the list beside it. Inside that column the same
   argument runs the other way and had no answer: the canvas took what was left
   over after a parts list that had grown to twenty-one rows, and on a tall
   model that left a letterbox. This is the same bargain on the other axis -
   the controls are given a height, and the canvas takes the rest.

   Docked only. In the dialog the two are side by side with the whole page's
   height to share, which is a different split and not one anybody has run out
   of room in. Persisted like the other one, and for the same reason: how much
   of the panel the model deserves depends on what you are doing with it. */
const V3_MIN_STAGE = 150;   // below this the model is a thumbnail
const V3_MIN_SIDE  = 74;    // below this not one whole parts row is left showing

/* What the drag moves is the CANVAS, not the controls under it.

   The obvious way round - give the controls a height and let the canvas take
   what is left - does nothing here, because the docked column is as tall as its
   contents rather than a fixed box: the stage sits at the stylesheet's 240px
   floor and the panel scrolls. Growing the controls in that layout grows the
   panel and leaves the model exactly where it was. Sizing the stage moves the
   boundary whichever way the column is sized, which is what the bar looks like
   it should do. */
function v3GripSet(stage, room, want){
  const cap = Math.max(V3_MIN_STAGE, (room || 0) - V3_MIN_SIDE);
  const px = Math.round(Math.max(V3_MIN_STAGE, Math.min(want, cap)));
  stage.style.flex = '0 0 ' + px + 'px';
  stage.style.minHeight = px + 'px';   // the stylesheet floors it at 240
  return px;
}

/* The panel's own scrolling box is the room there is to share: past it the
   column scrolls, so a stage taller than that is a canvas you cannot see the
   bottom of without scrolling the controls off. */
function v3GripRoom(){
  const host = v3HostEl();
  return (host && host.clientHeight) || Math.round(window.innerHeight * 0.7);
}

function v3GripStage(){
  const host = v3HostEl();
  const wrap = host && host.querySelector('.v3wrap.dock');
  return wrap ? wrap.querySelector('.v3stage') : null;
}

/* v3Render rebuilds the panel's markup, so the dragged height is re-applied
   from settings each time rather than living on the element. */
function v3GripInstall(){
  const stage = v3GripStage();
  const saved = +(state.settings && state.settings.v3_dock_px) || 0;
  if(stage && saved > 0) v3GripSet(stage, v3GripRoom(), saved);
}

function v3GripDown(ev){
  if(ev.button) return;              // left button only
  ev.preventDefault();               // and never let the drag select the list
  const grip = ev.currentTarget;
  const stage = grip.parentNode && grip.parentNode.querySelector('.v3stage');
  if(!stage) return;
  const startY = ev.clientY, startH = stage.getBoundingClientRect().height;
  const room = v3GripRoom();
  try{ grip.setPointerCapture(ev.pointerId); }catch(e){}
  grip.classList.add('drag');
  document.body.classList.add('vsplitting');
  // The bar sits UNDER the canvas, so dragging down (a rising clientY) makes it
  // taller. The canvas re-reads its own size every frame, so nothing has to be
  // told the stage changed.
  const move = e => v3GripSet(stage, room, startH + (e.clientY - startY));
  const up = () => {
    grip.removeEventListener('pointermove', move);
    grip.removeEventListener('pointerup', up);
    grip.removeEventListener('pointercancel', up);
    grip.classList.remove('drag');
    document.body.classList.remove('vsplitting');
    splitSave('v3_dock_px', Math.round(stage.getBoundingClientRect().height));
  };
  grip.addEventListener('pointermove', move);
  grip.addEventListener('pointerup', up);
  grip.addEventListener('pointercancel', up);
}

/* Back to the height the stylesheet picks. Written through `api.post` rather
   than `splitSave`, which refuses to store a zero - and zero is exactly what
   "no saved height" has to be written as to clear one. */
function v3GripReset(){
  const stage = v3GripStage();
  if(stage){ stage.style.flex = ''; stage.style.minHeight = ''; }
  state.settings.v3_dock_px = 0;
  api.post('/api/settings', {v3_dock_px: 0});
}

/* --- parts ----------------------------------------------------------------
   A group's first string is its TYPE: the slot the game fills. Most are the
   modeller's own words for a body part (Body, Head, hair, bracers), but the
   equipment slots are a fixed vocabulary the engine knows - the same list the
   Blender addon offers under "Apply Prefix" (panels/qol_panel.PART_PREFIXES).
   Spelling them out beats showing "shieldpassive0" and leaving you to work out
   which shield that is. */
const V3_SLOTS = {
  weapon0: 'Weapon', weapon1: 'Weapon 2',
  primaryactive0: 'Primary weapon - drawn', primaryactive1: 'Primary weapon 2 - drawn',
  primarypassive0: 'Primary weapon - stowed', primarypassive1: 'Primary weapon 2 - stowed',
  secondaryactive0: 'Secondary weapon - drawn', secondaryactive1: 'Secondary weapon 2 - drawn',
  secondarypassive0: 'Secondary weapon - stowed', secondarypassive1: 'Secondary weapon 2 - stowed',
  shield0: 'Shield', shield1: 'Shield 2',
  shieldactive0: 'Shield - carried', shieldactive1: 'Shield 2 - carried',
  shieldpassive0: 'Shield - slung', shieldpassive1: 'Shield 2 - slung',
  ramrod0: 'Ramrod', 'cannon ball0': 'Cannon ball', 'ballista arrow0': 'Ballista bolt'
};

/* Which slots start hidden. A model ships both stances of the same kit - the
   shield on the arm AND the shield on the back, the drawn sword AND the
   sheathed one - and showing every one of them at once hangs three swords off
   one soldier. The addon's importer makes the same call in hideVariations: it
   hides `shieldpassive` and `secondaryactive` and leaves the primary stance
   showing. Tick them back on to see the rest. */
function v3SlotHidden(key){
  return key.indexOf('shieldpassive') === 0 || key.indexOf('secondaryactive') === 0;
}

/* The model's groups folded into parts: one entry per group TYPE, holding its
   variants. Case-folded, because the same part is spelled `Arms` in one mod's
   mesh and `arms` in another's - and, in nineteen files across both installed
   mods, both ways inside ONE mesh, where they are plainly the same arms. */
function v3PartMap(){
  const parts = new Map();
  if(!v3 || !v3.geo) return parts;
  v3.geo.groups.forEach((g, idx) => {
    const key = (g.name || '(unnamed)').toLowerCase();
    if(!parts.has(key))
      parts.set(key, {key, label: V3_SLOTS[key] || g.name || '(unnamed)', list: []});
    parts.get(key).list.push({g, idx});
  });
  // a part every one of whose variants is flagged optional is one the game
  // only puts on some soldiers - the addon's __opt marker
  parts.forEach(p => { p.optional = p.list.every(v => v.g.optional); });
  return parts;
}

function v3Chosen(part){
  return v3.variant[part.key] !== undefined ? v3.variant[part.key] : part.list[0].idx;
}

/* One row per part: a checkbox to drop it, and a picker when it has variants,
   because showing two heads at once is the wrong answer to "what does this
   model look like". */
function v3Parts(){
  const host = document.getElementById('v3parts');
  if(!host || !v3 || !v3.geo) return;
  if(v3.cas) return v3CasParts(host);
  const parts = v3PartMap();
  const att = [...parts.values()].filter(p => p.list.some(v => v.g.sheets !== 'main')).length;
  host.innerHTML = `<div class="k">Parts <span class="count">${parts.size} slots`
    + (att ? ` · ${att} reaching the ${v3TexCase() === 'pair'
        ? 'attachment sheet' : 'right half of the sheet'}` : '') + `</span></div>`
    + [...parts.values()].map((p, n) => {
    const box = `<input type="checkbox" ${v3.hidden[p.key]?'':'checked'}
        onchange="v3TogglePart('${q1(esc(p.key))}')">`;
    /* While the UV layout is open every row carries the colour its island is
       drawn in - that pairing is what turns a wireframe into a map you can
       read. The chip selects too, and has to call off the click first: it sits
       inside the row's <label>, and a click on a label is a click on its
       checkbox, so without this, naming a part would also hide it. */
    const dot = v3.uved
      ? `<i class="v3dot" title="find this part in the UV layout"
           style="background:${v3UvColour(n, v3.uvSel === p.key)}"
           onclick="event.preventDefault();event.stopPropagation();v3UvSelect('${q1(esc(p.key))}')"></i>`
      : '';
    const rowcls = v3.uvSel === p.key && v3.uved ? ' sel' : '';
    // Which sheet the art is ON, said rather than acted on - the UVs do the
    // choosing themselves, and a part can genuinely straddle the two. mesh.py
    // labels the HALF of the space a group sits in; on an entry with no second
    // sheet the halves are halves of the one it has, and calling that an
    // "attach sheet" would name a texture the entry does not carry.
    const two = v3TexCase() === 'pair';
    const far = two ? 'attach sheet' : 'right half';
    const straddle = two ? 'both sheets' : 'both halves';
    const sheet = p.list.some(v => v.g.sheets === 'both') ? straddle
                : p.list.every(v => v.g.sheets === 'attach') ? far
                : p.list.some(v => v.g.sheets !== 'main') ? straddle : '';
    const tags = (p.optional ? '<span class="v3tag">optional</span>' : '')
               + (sheet ? `<span class="v3tag">${sheet}</span>` : '');
    if(p.list.length === 1){
      const {g} = p.list[0];
      return `<label class="v3part${rowcls}">${box}${dot}
        <span class="v3nm">${esc(p.label)}</span>${tags}
        <span class="count">${esc(g.texture_group||'')} · ${g.count/3} tris</span></label>`;
    }
    const chosen = v3Chosen(p);
    return `<div class="v3part v3var${rowcls}"><label class="v3nm">${box}${dot} ${esc(p.label)} ${tags}</label>
      <select onchange="v3SetVariant('${q1(esc(p.key))}', this.value)">
        ${p.list.map(({g, idx}) => `<option value="${idx}" ${idx===chosen?'selected':''}
          >${esc(g.texture_group || ('variant ' + (idx+1)))} · ${g.count/3} tris</option>`).join('')}
      </select>
      <span class="count">${p.list.length} variants - the game picks one per soldier</span></div>`;
  }).join('');
}

/* One soldier's worth of choices: a variant per part, and a coin toss on the
   parts the mesh flags optional - which is what the game itself does as it
   fills a unit out of one model. */
function v3Randomize(){
  if(!v3 || !v3.geo) return;
  v3PartMap().forEach(p => {
    v3.variant[p.key] = p.list[Math.floor(Math.random() * p.list.length)].idx;
    v3.hidden[p.key] = v3SlotHidden(p.key) || (p.optional && Math.random() < 0.5);
  });
  v3Parts();
  v3UvEdDraw();
}

function v3Facts(){
  const host = document.getElementById('v3facts');
  if(!host || !v3) return;
  const g = v3.geo;
  if(!g) return host.innerHTML = '';
  if(v3.cas) return v3CasFacts(host, g);
  const size = [0,1,2].map(k => (g.max[k]-g.min[k]).toFixed(2));
  const skin = v3Skin();
  const onAtt = g.groups.filter(x => x.sheets !== 'main').length;
  host.innerHTML = docPoints('This model:', [
    `<b>${g.vertices.toLocaleString()}</b> vertices, <b>${g.triangles.toLocaleString()}</b> triangles`,
    `${g.groups.length} group${g.groups.length===1?'':'s'} over one shared vertex pool`,
    `${size[0]} × ${size[1]} × ${size[2]} in game units`,
    g.bones.length ? `rigged to ${g.bones.length} bones` : 'no skeleton - a static model',
    skin && skin.rel ? `main texture <code>${esc(skin.rel)}</code>${skin.exists?'':' - <b>not in this mod</b>'}`
                     : 'no texture listed on this entry',
    v3TexCase() === 'pair'
      ? `attachment texture <code>${esc(skin.attach)}</code>${skin.attach_exists?'':' - <b>not in this mod</b>'}`
      : v3TexCase() === 'self'
        ? `its attachment slot names <code>${esc((skin&&skin.attach)||'')}</code>`
          + `${skin && skin.attach_exists ? ' - the main file again, so the game glues that sheet to a copy of itself and u wraps at 1'
                                          : ' - <b>not in this mod</b>, so u wraps at 1 on the main sheet instead'}`
        : 'no attachment texture on this entry, so this one sheet is the whole '
          + 'space and u wraps at 2 - every ordinary mount is built this way',
    // the honest answer to "why does this look right in the game and not here":
    // an entry can name an attachment sheet that no group's UVs ever reach
    onAtt ? `${onAtt} group${onAtt===1?'':'s'} reach past u 1 - into the `
            + (v3TexCase() === 'pair' ? 'attachment sheet' : 'right half of that sheet')
          : 'every group stays in the left half of the space, u 0 to 1',
    v3.info.skins.length === 1 && (v3.info.skins[0].factions||[]).length > 1
      ? `every one of its ${v3.info.skins[0].factions.length} factions uses that same skin`
      : `${v3.info.skins.length} distinct skin${v3.info.skins.length===1?'':'s'} across its factions`,
    g.lod_name ? `the file calls itself <code>${esc(g.lod_name)}</code>` : ''
  ]) + (g.notes||[]).map(n => `<div class="w-warn" style="margin-top:6px">${esc(n)}</div>`).join('');
}

/* --- loading -------------------------------------------------------------- */

async function v3Load(){
  if(!v3) return;
  const want = ++v3Gen;
  v3Note('Reading the model…');
  let buf;
  try{
    const r = await fetch(v3.cas
      ? `/api/map/model/geometry?mod=${enc(v3.mod)}&rel=${enc(v3.cas)}`
      : `/api/model/geometry?mod=${enc(v3.mod)}&entry=${enc(v3.entry)}&lod=${v3.lod}`);
    if(!r.ok){
      // the decoder's own sentence is the useful part, so it is shown as-is
      let msg = `the server answered ${r.status}`;
      try{ msg = (await r.json()).error || msg; }catch(e){}
      throw new Error(msg);
    }
    buf = await r.arrayBuffer();
  }catch(e){ if(want===v3Gen) v3Note(''+(e.message||e), true); return; }
  if(want !== v3Gen || !v3) return;

  try{ v3.geo = v3Parse(buf); }
  catch(e){ return v3Note(''+(e.message||e), true); }
  v3.variant = {};
  // a new LOD is new islands: the framing and the named part belonged to the
  // old one, and a part key that survives the change is a coincidence
  v3.uvv = null; v3.uvSel = null;
  // the stances a model ships but does not wear at once start off
  v3.hidden = {};
  v3PartMap().forEach(p => { if(v3SlotHidden(p.key)) v3.hidden[p.key] = true; });
  v3Note('');
  v3Render();
  await v3LoadSkin(want);
}

let v3Gen = 0;          // so a slow LOD cannot land after a newer one

/* One image per sheet. They land independently and either may be missing - a
   mod that references vanilla art ships neither - so each one applies as it
   arrives rather than waiting for the pair. */
function v3Fetch(rel, want, into){
  if(!rel){ v3[into] = null; v3Apply(); return; }
  const img = new Image();
  img.onload = () => { if(want===v3Gen && v3){ v3[into] = img; v3Apply(); } };
  img.onerror = () => { if(want===v3Gen && v3){ v3[into] = null; v3Apply(); } };
  img.src = `/model_texture?mod=${enc(v3.mod)}&rel=${enc(rel)}`;
}

async function v3LoadSkin(want){
  if(!v3) return;
  if(v3.cas) return v3LoadCasSkins(want);
  const skin = v3Skin();
  v3.tex = null; v3.texAtt = null; v3.uScale = 1.0;
  v3Fetch(skin && skin.exists ? skin.rel : '', want, 'tex');
  // An attachment sheet that IS the main sheet is not a second sheet. Mods write
  // the main file into the attach slot all the time (it is what the Blender
  // addon exports when the slot is empty), and taking it at face value would
  // glue a picture to a copy of itself for nothing.
  const same = skin && skin.attach && skin.rel
            && skin.attach.toLowerCase() === skin.rel.toLowerCase();
  v3Fetch(skin && skin.attach_exists && !same ? skin.attach : '', want, 'texAtt');
}

function v3Note(msg, bad){
  const el = document.getElementById('v3msg');
  if(el) el.innerHTML = msg ? `<span class="${bad?'w-bad':'count'}">${esc(msg)}</span>` : '';
}

/* The payload mesh.py builds: "M2GT", a JSON header, then the arrays raw. */
function v3Parse(buf){
  const view = new DataView(buf);
  const magic = String.fromCharCode(view.getUint8(0), view.getUint8(1),
                                    view.getUint8(2), view.getUint8(3));
  if(magic !== 'M2GT') throw new Error('that response is not model geometry');
  const hlen = view.getUint32(4, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 8, hlen)));
  let at = 8 + hlen;
  const n = head.vertices;
  head.positions = new Float32Array(buf, at, n*3); at += n*12;
  if(head.has_normals){ head.normals = new Float32Array(buf, at, n*3); at += n*12; }
  if(head.has_uvs){ head.uvs = new Float32Array(buf, at, n*2); at += n*8; }
  const total = head.groups.reduce((s,g) => s + g.count, 0);
  head.indices = new Uint16Array(buf, at, total); at += total*2;
  if(at !== buf.byteLength)
    throw new Error(`the geometry is ${buf.byteLength-at} bytes longer than its header describes`);
  return head;
}

/* --- controls ------------------------------------------------------------- */

function v3SetLod(v){ if(!v3) return; v3.lod = +v; v3Stop(); v3.geo = null; v3Load(); }
function v3SetSkin(v){ if(!v3) return; v3.skin = +v; v3LoadSkin(v3Gen); v3Facts(); }
// the 3D view redraws itself every frame; the UV pane draws on demand, so
// anything that changes WHICH groups are drawn has to say so
function v3SetVariant(part, idx){ if(!v3) return; v3.variant[part] = +idx; v3UvEdDraw(); }
function v3TogglePart(key){ if(!v3) return; v3.hidden[key] = !v3.hidden[key]; v3UvEdDraw(); }
function v3Toggle(what){
  if(!v3) return;
  v3[what] = !v3[what];
  const b = document.getElementById('v3' + what);
  if(b) b.classList.toggle('on', v3[what]);
  if(what === 'uv') v3UvKey();
  // the parts list grows a colour chip per row while the layout is open, so it
  // is repainted either way round
  if(what === 'uved'){ v3UvEdOn(); v3Parts(); }
}

/* What the colours mean, on screen only while they are on screen. The amber row
   is dropped for an entry with no second sheet, because that model has no amber
   on it to explain - and which of the three shapes it is in decides what the
   blue row can honestly claim. See `v3TexCase`. */
function v3UvKey(){
  const host = document.getElementById('v3uvkey');
  if(!host) return;
  if(!v3 || !v3.uv){ host.className = ''; host.innerHTML = ''; return; }
  const kind = v3TexCase();
  const row = (css, text) => `<i style="background:${css}"></i><span>${text}</span>`;
  host.className = 'v3uvkey';
  host.innerHTML = '<b>UV mode</b>'
    + (kind === 'pair'
        ? row('#4a82cc', 'the main sheet - u 0 to 1')
          + row('#e08f33', 'the attachment sheet - u 1 to 2')
        : kind === 'self'
          ? row('#4a82cc', 'the sheet - and u 1 to 2 is that same file again, '
                         + 'which is what this entry names in its attachment slot')
          : row('#4a82cc', 'the sheet - it has no attachment beside it, so it '
                         + 'spans all of u 0 to 2 on its own'))
    + row('#2a3a4d', 'outside u 0 to 2 - past the space the model was unwrapped in')
    + row('#ff3d57', `where the art starts over - every ${
        v3UvSpan() === 2 ? 'second unit' : 'unit'} of u`)
    + `<span style="grid-column:1/-1">32 checker cells to a sheet: a stretched
       cell is art stretched over that triangle.</span>`;
}

/* --- the UV layout --------------------------------------------------------
   The other half of "check the UVs": Blender's UV editor, which is the sheet
   itself with the mesh's islands drawn over it. `Show UVs` paints the
   coordinate onto the MODEL and answers "is this shell stretched, and which
   sheet is it on". This answers the question that one cannot - "where on the
   art does this part sit, and what is under it" - and it is the view a
   retexture is actually done against.

   Plain 2D canvas, not a second WebGL context. The whole drawing is an image
   and a few thousand lines; a second context on the page is a second copy of
   the mesh on the GPU for a picture the CPU draws in a millisecond.

   Three things it has to get right, and they are the same three the shader
   already fights with (see V3_UV):

     * **the space is the modeller's, untouched.** u 0..1 is the main sheet,
       1..2 the attachment sheet, and everything outside is the pair repeating.
       Nothing is wrapped or folded into 0..1 here either - an island running to
       u 1.38 is DRAWN at 1.38, over the repeat it really lands on, because
       "this part leaves its sheet" is exactly what you opened this to see;
     * **v goes DOWN.** M2TW is a Direct3D game and puts v=0 at the top, which
       is why the texture is bound unflipped in v3Apply - so the sheet is drawn
       from its top-left corner at (0,0) and v grows downward, and an island
       sits over the art it names rather than over its mirror image;
     * **one colour per part.** The parts list carries the same colour beside
       each row, so an island and the slot that wears it can be read off one
       another. That is the whole reason this is not one flat wireframe.

   Only the groups the viewer is DRAWING are drawn here - one variant per part,
   minus the parts switched off. A model ships three heads and two shields, and
   laying every one of them over the same sheet is a plate of spaghetti rather
   than a UV map. */

/* Islands are coloured by walking the wheel at the golden angle, so twenty
   consecutive parts come out twenty distinguishable hues instead of twenty
   blues. */
function v3UvColour(n, sel){
  return `hsla(${((n * 137.508) % 360).toFixed(0)}, 85%, ${sel ? 70 : 58}%, ${sel ? 1 : 0.78})`;
}

/* Which part each drawable group belongs to, and where that part sits in the
   list - the colour and the parts row both key off that position. */
function v3UvOwners(){
  const map = new Map();
  [...v3PartMap().values()].forEach((p, n) => p.list.forEach(v => map.set(v.idx, {p, n})));
  return map;
}

/* The layout is drawn in the BOUND IMAGE's own space: one square per sheet,
   at the size the art really is, and the UVs put through the same scaling the
   sampler puts them through to land on it.

   Which means it does not matter here that the mesh's u runs 0..2 on a mount
   and 0..2 on a pair for different reasons - `uUScale` already holds the
   difference, and going through it is what keeps a 1024 square sheet drawn as
   a square. Stretching one across two tiles because the mesh's u happens to
   span two is a picture of the coordinate rather than a picture of the art,
   and the art is what you are trying to paint. */

/* One copy of the bound art, measured in units of u: two for anything that
   spans the space (a glued pair, or a mount's lone sheet), one for the sheet
   the game glues to a copy of itself. This is `uUScale` inverted. */
function v3UvSpan(){ return v3TexCase() === 'self' ? 1 : 2; }

/* And how many SHEETS wide that copy is drawn - the only thing that decides
   the picture's aspect, so a lone sheet is one square and a pair is two. */
function v3UvSheets(){ return v3TexCase() === 'pair' ? 2 : 1; }

/* Pixels across one unit of u, given the pixels across one unit of v. The two
   differ by exactly the scaling above: a mount's sheet is one square holding
   two units of u, so a unit of u is half a square. */
function v3UvPxU(px){ return px * v3UvSheets() / v3UvSpan(); }

/* Which of the three shapes an entry's texture set is in. It is not a two-way
   question, and reading it as one is what put every mount in the game on the
   wrong half of its own sheet - see `v3Apply`.

     'pair'  two different sheets, glued: main in u 0..1, attachment in 1..2
     'self'  the entry NAMES an attachment and it is the main file again (or a
             file this mod does not ship). The game glues main to main, so the
             art repeats every ONE unit of u
     'solo'  the entry names no attachment at all. There is nothing to glue, so
             the one sheet IS the two-unit space and the art repeats every TWO
*/
function v3TexCase(){
  if(!v3) return 'solo';
  if(v3.texAtt) return 'pair';
  const skin = v3Skin();
  return skin && skin.attach ? 'self' : 'solo';
}

/* Turning the button on is what sizes the view: the pane has no width until
   the class lands, so the fit has to happen after it. */
function v3UvEdOn(){
  if(!v3) return;
  const stage = document.getElementById('v3stage');
  if(stage) stage.classList.toggle('uv', !!v3.uved);
  if(!v3.uved) return;
  if(!v3.uvv) v3UvFit(false);
  v3UvBar();
  v3UvEdDraw();
}

/* The bound image in the pane, at its own aspect, with a little air round it.
   `px` is pixels across one unit of v - one sheet's height - so the fit is
   against how many SHEETS wide the picture is, not how many units of u it
   happens to be written in. */
function v3UvFit(redraw){
  if(!v3) return;
  const c = document.getElementById('v3uvcanvas');
  const w = (c && c.clientWidth) || 480, h = (c && c.clientHeight) || 360;
  v3.uvv = {u: v3UvSpan()/2, v: 0.5,
            px: Math.max(24, Math.min(w/(v3UvSheets()*1.06), h/1.06))};
  if(redraw !== false) v3UvEdDraw();
}

function v3UvOpt(what, on){
  if(!v3) return;
  v3.uvOpt[what] = !!on;
  v3UvEdDraw();
}

/* Clicking an island names it; clicking it again, or clicking bare sheet, lets
   it go. */
function v3UvSelect(key){
  if(!v3) return;
  v3.uvSel = (key && key !== v3.uvSel) ? key : null;
  v3Parts();
  v3UvBar();
  v3UvEdDraw();
}

/* The box one part's UVs really occupy. Read off the variant being DRAWN, not
   off the part as a whole: two variants of a head are two different islands,
   and the numbers under the picture have to be the picture's. */
function v3UvBounds(p){
  const g = v3.geo, uvs = g.uvs, ind = g.indices;
  const grp = g.groups[v3Chosen(p)];
  let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
  for(let t = grp.start; t < grp.start + grp.count; t++){
    const i = ind[t]*2, u = uvs[i], v = uvs[i+1];
    if(u < u0) u0 = u;
    if(u > u1) u1 = u;
    if(v < v0) v0 = v;
    if(v > v1) v1 = v;
  }
  const span = v3UvSpan();
  return {u0, u1, v0, v1,
          out: u0 < -0.001 || u1 > span + 0.001 || v0 < -0.001 || v1 > 1.001};
}

/* The caption under the toolbar: which part is selected, and where it lives. */
function v3UvBar(){
  const el = document.getElementById('v3uvsel');
  if(!el || !v3 || !v3.geo) return;
  const parts = [...v3PartMap().values()];
  const n = parts.findIndex(p => p.key === v3.uvSel);
  if(n < 0){
    el.innerHTML = '<span class="count">click an island to name the part wearing it</span>';
    return;
  }
  const p = parts[n], b = v3UvBounds(p);
  el.innerHTML = `<i class="v3dot" style="background:${v3UvColour(n, true)}"></i>`
    + `<b>${esc(p.label)}</b> <span class="count">u ${b.u0.toFixed(2)}–${b.u1.toFixed(2)} ·`
    + ` v ${b.v0.toFixed(2)}–${b.v1.toFixed(2)}`
    + (b.out ? ' · runs outside the sheet it was authored in' : '') + '</span>';
}

/* --- drawing --------------------------------------------------------------- */

function v3UvEdDraw(){
  const c = document.getElementById('v3uvcanvas');
  if(!c || !v3 || !v3.uved || !v3.geo) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = c.clientWidth || 480, h = c.clientHeight || 360;
  if(c.width !== Math.round(w*dpr) || c.height !== Math.round(h*dpr)){
    c.width = Math.round(w*dpr); c.height = Math.round(h*dpr);
  }
  const x = c.getContext('2d');
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.fillStyle = '#0b0d11';
  x.fillRect(0, 0, w, h);
  if(!v3.geo.has_uvs){
    x.fillStyle = '#8a93a3';
    x.font = '13px system-ui, sans-serif';
    x.textAlign = 'center';
    x.fillText('this model carries no UV set', w/2, h/2);
    return;
  }
  if(!v3.uvv) v3UvFit(false);
  // pixels across a unit of v is pixels across a SHEET; a unit of u is worth
  // whatever the sampler's scaling makes it, which is what keeps the art square
  const s = v3.uvv, px = s.px, pxU = v3UvPxU(px);
  const X = u => w/2 + (u - s.u) * pxU;
  const Y = v => h/2 + (v - s.v) * px;
  const span = v3UvSpan(), sheets = v3UvSheets();

  // which copies of the art are on screen - capped, because zoomed far enough
  // out the honest answer is "thousands", and none of them readable
  const uMin = s.u - (w/2)/pxU, uMax = s.u + (w/2)/pxU;
  const vMin = s.v - (h/2)/px, vMax = s.v + (h/2)/px;
  const i0 = Math.max(-8, Math.floor(uMin/span)), i1 = Math.min(8, Math.floor(uMax/span));
  const j0 = Math.max(-8, Math.floor(vMin)), j1 = Math.min(8, Math.floor(vMax));

  // crisp texels once one is bigger than a screen pixel: this is a tool for
  // seeing where a seam falls, and blur is the enemy of that
  x.imageSmoothingEnabled = px < 1200;
  for(let i = i0; i <= i1; i++){
    for(let j = j0; j <= j1; j++){
      // tile (0,0) is the art as it was authored; every other tile on screen is
      // the wrap, and is dimmed so the difference reads
      x.globalAlpha = (i === 0 && j === 0) ? 1 : 0.30;
      const top = Y(j), left = X(i*span);
      if(v3.uvOpt.tex && v3.tex){
        // one square per sheet, whatever span of u that square is addressed by
        x.drawImage(v3.tex, left, top, px, px);
        if(v3.texAtt) x.drawImage(v3.texAtt, left + px, top, px, px);
      }else{
        x.fillStyle = '#171b21';
        x.fillRect(left, top, px*sheets, px);
      }
      x.globalAlpha = 1;
    }
  }

  // the vertical lines: red where the art starts over, white for the seam
  // between a pair's two sheets, which is a change of picture and not a repeat
  x.lineWidth = 1;
  for(let n = i0; n <= i1 + 1; n++){
    for(let k = 0; k < sheets; k++){
      const u = (n + k/sheets) * span;
      x.strokeStyle = k === 0 ? 'rgba(255,61,87,0.85)' : 'rgba(255,255,255,0.35)';
      x.beginPath(); x.moveTo(X(u) + 0.5, 0); x.lineTo(X(u) + 0.5, h); x.stroke();
    }
  }
  x.strokeStyle = 'rgba(255,61,87,0.85)';
  for(let v = Math.floor(vMin); v <= Math.ceil(vMax); v++){
    x.beginPath(); x.moveTo(0, Y(v) + 0.5); x.lineTo(w, Y(v) + 0.5); x.stroke();
  }

  // the islands, one path per group so the whole of a part strokes at once
  const g = v3.geo, uvs = g.uvs, ind = g.indices, owners = v3UvOwners();
  x.lineJoin = 'round';
  for(const gi of v3Visible()){
    const o = owners.get(gi);
    if(!o) continue;
    const sel = v3.uvSel === o.p.key;
    if(v3.uvOpt.solo && v3.uvSel && !sel) continue;
    const grp = g.groups[gi];
    const path = new Path2D();
    for(let t = grp.start; t < grp.start + grp.count; t += 3){
      const a = ind[t]*2, b = ind[t+1]*2, cc = ind[t+2]*2;
      path.moveTo(X(uvs[a]), Y(uvs[a+1]));
      path.lineTo(X(uvs[b]), Y(uvs[b+1]));
      path.lineTo(X(uvs[cc]), Y(uvs[cc+1]));
      path.closePath();
    }
    if(sel){
      x.fillStyle = `hsla(${((o.n * 137.508) % 360).toFixed(0)}, 85%, 60%, 0.18)`;
      x.fill(path);
    }
    x.strokeStyle = v3UvColour(o.n, sel);
    x.lineWidth = sel ? 1.7 : 0.9;
    x.stroke(path);
  }
}

/* Resize is the one change nothing else notices: the pane is a flex child of a
   stage that moves with the window, and the canvas only learns about it here.
   Everything else that changes the picture calls the draw itself. */
function v3UvEdTick(){
  const c = document.getElementById('v3uvcanvas');
  if(!c) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  if(c.width !== Math.round((c.clientWidth||0)*dpr)
  || c.height !== Math.round((c.clientHeight||0)*dpr)) v3UvEdDraw();
}

/* --- pan, zoom and picking ------------------------------------------------- */

function v3UvAt(canvas, e){
  const r = canvas.getBoundingClientRect(), s = v3.uvv;
  return {u: s.u + (e.clientX - r.left - r.width/2)/v3UvPxU(s.px),
          v: s.v + (e.clientY - r.top - r.height/2)/s.px};
}

function v3UvPointers(canvas){
  let last = null, moved = 0;
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  canvas.addEventListener('pointerdown', e => {
    last = [e.clientX, e.clientY]; moved = 0;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointerup', e => {
    // a press that never travelled is a pick; one that did was a pan
    if(last && moved < 4 && v3 && v3.uvv) v3UvSelect(v3UvPick(v3UvAt(canvas, e)));
    last = null;
    try{ canvas.releasePointerCapture(e.pointerId); }catch(err){}
  });
  canvas.addEventListener('pointermove', e => {
    if(!v3 || !v3.uvv) return;
    v3UvReadout(v3UvAt(canvas, e));
    if(!last) return;
    const dx = e.clientX - last[0], dy = e.clientY - last[1];
    moved += Math.abs(dx) + Math.abs(dy);
    last = [e.clientX, e.clientY];
    v3.uvv.u -= dx / v3UvPxU(v3.uvv.px);
    v3.uvv.v -= dy / v3.uvv.px;
    v3UvEdDraw();
  });
  canvas.addEventListener('wheel', e => {
    if(!v3 || !v3.uvv) return;
    e.preventDefault();
    // zoom about the cursor: the texel under it has to stay under it, or you
    // lose the seam you leaned in to look at
    const before = v3UvAt(canvas, e);
    v3.uvv.px = Math.max(16, Math.min(60000, v3.uvv.px * (e.deltaY > 0 ? 1/1.12 : 1.12)));
    const after = v3UvAt(canvas, e);
    v3.uvv.u += before.u - after.u;
    v3.uvv.v += before.v - after.v;
    v3UvEdDraw();
  }, {passive:false});
}

/* Where the cursor is, in the coordinate the mesh is written in - and, when it
   is over the art rather than a repeat of it, which pixel of which sheet that
   is. A retexture is done in pixels, so the pixel is worth saying. */
function v3UvReadout(at){
  const el = document.getElementById('v3uvpos');
  if(!el) return;
  const home = at.u >= 0 && at.u < v3UvSpan() && at.v >= 0 && at.v < 1;
  // Where in the BOUND image this coordinate falls: one copy of the art is
  // `art` units of u wide, so this is the position across that copy.
  const span = v3UvSpan();
  const a = (((at.u % span) + span) % span) / span;
  const kind = v3TexCase();
  // naming an "attachment sheet" on an entry that has none would be a lie, and
  // on the one that has the main file twice the honest word is "again"
  const sheet = !home ? 'outside the space'
              : kind === 'pair' ? (a < 0.5 ? 'main sheet' : 'attachment sheet')
              : kind === 'self' ? (at.u < 1 ? 'the sheet' : 'the same sheet again')
              : 'the sheet';
  const img = (kind === 'pair' && a >= 0.5) ? v3.texAtt : v3.tex;
  const across = kind === 'pair' ? (a % 0.5) * 2 : a;
  const px = (home && img)
    ? ` · ${Math.floor(across * img.width)}, ${Math.floor(at.v * img.height)} px` : '';
  el.textContent = `u ${at.u.toFixed(3)}  v ${at.v.toFixed(3)} · ${sheet}${px}`;
}

/* Which part is under the cursor. Every drawn triangle, tested - a few thousand
   of them on a click, which is nothing, and it is exact where a nearest-island
   guess would be wrong on the overlapping shells a soldier is made of. */
function v3UvPick(at){
  const g = v3.geo;
  if(!g || !g.uvs) return null;
  const uvs = g.uvs, ind = g.indices, owners = v3UvOwners();
  for(const gi of v3Visible()){
    const o = owners.get(gi);
    if(!o) continue;
    if(v3.uvOpt.solo && v3.uvSel && o.p.key !== v3.uvSel) continue;
    const grp = g.groups[gi];
    for(let t = grp.start; t < grp.start + grp.count; t += 3){
      if(v3UvHit(at.u, at.v, uvs, ind[t], ind[t+1], ind[t+2])) return o.p.key;
    }
  }
  return null;
}

function v3UvHit(u, v, a, i, j, k){
  const x1 = a[i*2], y1 = a[i*2+1], x2 = a[j*2], y2 = a[j*2+1],
        x3 = a[k*2], y3 = a[k*2+1];
  const d = (y2-y3)*(x1-x3) + (x3-x2)*(y1-y3);
  if(!d) return false;
  const s = ((y2-y3)*(u-x3) + (x3-x2)*(v-y3)) / d;
  const t = ((y3-y1)*(u-x3) + (x1-x3)*(v-y3)) / d;
  return s >= 0 && t >= 0 && s + t <= 1;
}

function v3Frame(){
  if(!v3 || !v3.geo) return;
  const g = v3.geo;
  v3.centre = [0,1,2].map(k => (g.min[k]+g.max[k])/2);
  /* A unit is a standing figure, and its HEIGHT is what should fill the frame.

     Fitting the largest extent instead let a spear held straight out - two
     metres of it, and not the subject - decide how far away the man stood, so
     every unit sat in the middle distance with most of the panel empty. Height
     leads now, and the width only takes the framing back on something that is
     genuinely wide rather than long-armed: a spear roughly doubles a man's
     width, which is where the halving comes from, while a siege engine is wide
     all the way through and still gets fitted.

     A weapon that runs off the sides is the intended trade. The wheel zooms out,
     and Recentre comes back here. */
  const tall = g.max[1] - g.min[1];
  const wide = Math.max(g.max[0]-g.min[0], g.max[2]-g.min[2]);
  /* A strat model is not a standing figure and must not be framed as one. A
     settlement is WIDER than it is tall - vanilla's northern castle is 1.17 by
     0.77 - so the halving above puts the camera 0.86 away from something 1.17
     across, which is inside its own courtyard looking at the back of a wall.
     The subject here is the footprint, so the whole box is fitted and the
     camera is lifted: a building is looked down on, the way the campaign map
     looks down on it, and a general standing beside one is small in the frame
     for the same reason he is small on the map. */
  /* And the file says which of the two it is, so this is not a guess: a strat
     model with a SKELETON is a person - a general, a diplomat, an assassin -
     and gets the figure's framing below. One without is a settlement, a
     resource or a banner, and gets the footprint's. */
  if(v3.cas && !v3.info.skinned){
    v3.centre[1] = g.min[1] + (g.max[1]-g.min[1]) * 0.4;
    v3.dist = (Math.max(tall, wide) || 1) * 1.7;
    v3.yaw = 0.6; v3.pitch = 0.5;
    return;
  }
  const span = Math.max(tall, wide/2) || 1;
  v3.dist = span * 1.12;
  v3.yaw = 0.6; v3.pitch = 0.25;
}

/* Which group indices to draw: one variant per part, minus the parts that are
   switched off. */
function v3Visible(){
  const out = [];
  // A .cas draws EVERY mesh it is not asked to hide. Folding same-named meshes
  // into variants and drawing one is right for a .mesh - three heads on one
  // soldier is one soldier's head - and wrong here: vanilla's northern castle
  // is two meshes both called NE_castle, its walls and its buildings, and they
  // stand together or the castle is half there.
  // Keyed by POSITION and not by name, for the same reason: two meshes called
  // NE_castle are two meshes, and one checkbox for the pair would drop half a
  // castle for anyone who wanted a look behind its walls.
  if(v3.cas){
    v3.geo.groups.forEach((grp, idx) => { if(!v3.hidden['m' + idx]) out.push(idx); });
    return out;
  }
  v3PartMap().forEach(p => { if(!v3.hidden[p.key]) out.push(v3Chosen(p)); });
  return out;
}

/* --- WebGL ---------------------------------------------------------------- */

function v3Start(canvas){
  const gl = canvas.getContext('webgl', {antialias:true, alpha:false})
          || canvas.getContext('experimental-webgl');
  if(!gl) return v3Note('this browser has no WebGL, so the model cannot be drawn', true);
  v3.gl = gl;
  const prog = v3Program(gl, V3_VERT, V3_FRAG);
  if(!prog) return v3Note('the viewer’s shaders would not compile here', true);
  v3.prog = prog;
  v3.loc = {
    aPos: gl.getAttribLocation(prog,'aPos'),
    aNormal: gl.getAttribLocation(prog,'aNormal'),
    aUv: gl.getAttribLocation(prog,'aUv'),
    uProj: gl.getUniformLocation(prog,'uProj'),
    uView: gl.getUniformLocation(prog,'uView'),
    uModel: gl.getUniformLocation(prog,'uModel'),
    uTex: gl.getUniformLocation(prog,'uTex'),
    uHasTex: gl.getUniformLocation(prog,'uHasTex'),
    uKey: gl.getUniformLocation(prog,'uKey'),
    uEye: gl.getUniformLocation(prog,'uEye'),
    uFlat: gl.getUniformLocation(prog,'uFlat'),
    uUScale: gl.getUniformLocation(prog,'uUScale'),
    uPair: gl.getUniformLocation(prog,'uPair'),
    uUv: gl.getUniformLocation(prog,'uUv')
  };
  // the backdrop: its own tiny program over one full-screen quad
  v3.bg = v3Program(gl, V3_BG_VERT, V3_BG_FRAG);
  if(v3.bg) v3.bgLoc = {
    aQuad: gl.getAttribLocation(v3.bg,'aQuad'),
    uRight: gl.getUniformLocation(v3.bg,'uRight'),
    uUp: gl.getUniformLocation(v3.bg,'uUp'),
    uFwd: gl.getUniformLocation(v3.bg,'uFwd'),
    uScale: gl.getUniformLocation(v3.bg,'uScale')
  };
  v3.bQuad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, v3.bQuad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
  v3Buffers(gl);
  v3Apply();
  v3Frame();
  v3Wire(canvas);
  gl.enable(gl.DEPTH_TEST);
  const tick = () => {
    if(!v3 || !v3.gl) return;
    // Paused (the editor's preview column folded away) keeps the loop alive but
    // draws nothing: everything is still on the GPU, so unfolding is instant,
    // and a canvas nobody can see costs no frames in the meantime.
    if(!v3.paused){
      if(v3.spin && !v3.drag) v3.yaw += 0.006;
      v3Draw();
      if(v3.uved) v3UvEdTick();
    }
    v3.raf = requestAnimationFrame(tick);
  };
  v3.raf = requestAnimationFrame(tick);
}

function v3Program(gl, vs, fs){
  const build = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)){
      console.error('viewer3d shader:', gl.getShaderInfoLog(s)); return null;
    }
    return s;
  };
  const v = build(gl.VERTEX_SHADER, vs), f = build(gl.FRAGMENT_SHADER, fs);
  if(!v || !f) return null;
  const p = gl.createProgram();
  gl.attachShader(p, v); gl.attachShader(p, f); gl.linkProgram(p);
  gl.deleteShader(v); gl.deleteShader(f);
  return gl.getProgramParameter(p, gl.LINK_STATUS) ? p : null;
}

function v3Buffers(gl){
  const g = v3.geo;
  const buf = (data, target) => {
    const b = gl.createBuffer();
    gl.bindBuffer(target, b); gl.bufferData(target, data, gl.STATIC_DRAW);
    return b;
  };
  v3.bPos = buf(g.positions, gl.ARRAY_BUFFER);
  // a model with no normal stream still has to shade: face the camera flat
  v3.bNormal = buf(g.normals || new Float32Array(g.vertices*3).fill(0.577), gl.ARRAY_BUFFER);
  v3.bUv = buf(g.uvs || new Float32Array(g.vertices*2), gl.ARRAY_BUFFER);
  v3.bIdx = buf(g.indices, gl.ELEMENT_ARRAY_BUFFER);
  // one line-index buffer for the wireframe, built once from the triangles
  const lines = new Uint16Array(g.indices.length * 2);
  for(let t = 0, o = 0; t < g.indices.length; t += 3){
    const [a,b2,c] = [g.indices[t], g.indices[t+1], g.indices[t+2]];
    lines[o++]=a; lines[o++]=b2; lines[o++]=b2; lines[o++]=c; lines[o++]=c; lines[o++]=a;
  }
  v3.bLines = buf(lines, gl.ELEMENT_ARRAY_BUFFER);
}

/* The two sheets glued into the one image the UVs are addressing: main in the
   left half, attachment in the right, each exactly one unit of u wide however
   big the source files are.

   Gluing beats binding two textures and choosing per part, which is what this
   did before and what got it wrong: the choice is not the viewer's to make.
   A group whose UVs run 0.41 to 1.38 is one piece of art crossing from one
   sheet onto the other, and any per-part rule has to put the whole of it on
   one sheet or the other and be wrong about half of it.

   Only ever called for an entry that really names two sheets. One that names a
   single sheet used to be glued to a copy of ITSELF here, which is a canvas, a
   second draw and twice the texture for a result the wrap mode already gives -
   see `uUScale` on the fragment shader. */
function v3Atlas(main, att){
  const w = main.width, h = main.height;
  const c = document.createElement('canvas');
  c.width = w * 2; c.height = h;
  const x = c.getContext('2d');
  x.drawImage(main, 0, 0, w, h);
  // scaled into its half, so u 1..2 is the whole attachment sheet whatever
  // size it came in at
  x.drawImage(att, w, 0, w, h);
  return c;
}

function v3Apply(){
  if(!v3 || !v3.gl) return;
  const gl = v3.gl;
  if(v3.texture){ gl.deleteTexture(v3.texture); v3.texture = null; }
  if(v3.casTexGl){ v3.casTexGl.forEach(t => gl.deleteTexture(t)); v3.casTexGl = null; }
  if(!v3.cas && !v3.tex){ v3UvEdDraw(); return; }
  /* Whatever is bound has to fill the two units of u the mesh was unwrapped in,
     and how far u has to be scaled to do that is NOT the same question as how
     many sheets were bound. Reading it as one question was a real bug, and its
     victims were the mounts:

       * a glued pair spans the two units, so u is halved - as it always was;
       * an entry naming NO attachment has nothing to glue, and its one sheet
         spans those same two units, so u is halved TOO. This is the fix. It
         used to bind that sheet at full u, which tiles it twice across the
         model and paints every horse in the game with texels twice as wide as
         they are tall;
       * an entry that NAMES an attachment this viewer did not glue - the main
         file over again, or one the mod does not ship - is the one case that
         keeps full u, and it is the case the old comment was describing. There
         the GAME really does glue two sheets, so the art repeats every unit,
         and wrapping one sheet at full u reproduces main-glued-to-main exactly.

     Measured, not reasoned: map each triangle's texel-space edges onto its own
     3D plane and the two singular values of that Jacobian say how far from
     square its texels are. Over whole models, a real pair comes out 1.21 at
     half u and 2.02 at full u; `mount_naru_horse` (attachment slot empty) comes
     out 2.00 at full u and 1.08 at half. Three pairs and four mounts, and the
     2.0 is the tell - it is the factor of two, standing up to be counted. */
  if(v3.cas){ v3.uScale = 1.0; return v3CasApply(); }
  const solo = v3TexCase() !== 'self';
  v3.uScale = solo ? 0.5 : 1.0;
  const atlas = v3.texAtt ? v3Atlas(v3.tex, v3.texAtt) : v3.tex;
  const t = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, t);
  // NOT flipped. WebGL's own habit is to flip, because OpenGL puts v=0 at the
  // bottom - M2TW is a Direct3D game and puts it at the top, so flipping sends
  // every UV to the mirrored half of the sheet. Checked against the art rather
  // than assumed: on a Lossarnach noble the head groups' UVs (v 0.00..0.10)
  // land exactly on the faces painted along the TOP edge of its texture, and
  // the same for every body and skirt group on that sheet.
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, atlas);
  // REPEAT is the whole point - the sheets tile, and UVs really do run past the
  // two tiles and below zero. A skin is served square and no bigger than 1024,
  // so a glued pair is 2048 wide at most and a power of two in both axes, which
  // is what WebGL 1 demands before it will repeat anything at all.
  const pot = n => n > 0 && (n & (n-1)) === 0;
  if(pot(atlas.width) && pot(atlas.height)){
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  }else{
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    v3Note('this skin is not a power of two, so the tiled parts of it cannot '
         + 'repeat here', true);
  }
  v3.texture = t;
  // Which of the three shapes this entry is in is decided right here, and a
  // skin loads asynchronously - so everything that SAYS which shape it is was
  // drawn before the answer existed, and is describing a pair as a lone sheet
  // (or the other way round after a skin change). Repainting them with the
  // decision keeps every surface in step: the legend, the parts list's
  // half-of-the-space tags, and the facts panel.
  v3UvKey();
  v3Parts();
  v3Facts();
  // and the layout is drawn from those same two images, so it waits on this
  // too - a pane opened before the skin landed is showing bare wireframe
  v3UvEdDraw();
}

function v3Draw(){
  const gl = v3.gl, c = gl.canvas, g = v3.geo;
  // narrow, the UV pane takes the whole stage and the model's canvas is laid
  // out at nothing - there is no frame to draw, and sizing to a made-up 640
  // would only throw the aspect ratio away for when it comes back
  if(!c.clientWidth || !c.clientHeight) return;
  const w = c.clientWidth || 640, h = c.clientHeight || 420;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  if(c.width !== Math.round(w*dpr) || c.height !== Math.round(h*dpr)){
    c.width = Math.round(w*dpr); c.height = Math.round(h*dpr);
  }
  gl.viewport(0, 0, c.width, c.height);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

  // M2TW models stand up the Y axis. Measured, not assumed: across six DaC
  // soldiers the Head group's centroid sits 1.4 above the Legs group's in Y
  // and level with it in X and Z. Orbit the wrong axis and every man in the
  // game lies on his side.
  const cp = Math.cos(v3.pitch), sp = Math.sin(v3.pitch);
  const eye = [v3.centre[0] + v3.dist*cp*Math.sin(v3.yaw),
               v3.centre[1] + v3.dist*sp,
               v3.centre[2] + v3.dist*cp*Math.cos(v3.yaw)];
  const fovY = 0.9, aspect = (c.width/c.height)||1;
  const back = v3Norm([eye[0]-v3.centre[0], eye[1]-v3.centre[1], eye[2]-v3.centre[2]]);
  const right = v3Norm(v3Cross([0,1,0], back));
  const up = v3Cross(back, right);

  // the environment behind the model, before anything else and behind
  // everything else: depth writes off, so the model still sorts normally
  if(v3.bg){
    gl.useProgram(v3.bg);
    gl.bindBuffer(gl.ARRAY_BUFFER, v3.bQuad);
    gl.enableVertexAttribArray(v3.bgLoc.aQuad);
    gl.vertexAttribPointer(v3.bgLoc.aQuad, 2, gl.FLOAT, false, 0, 0);
    gl.uniform3fv(v3.bgLoc.uRight, right);
    gl.uniform3fv(v3.bgLoc.uUp, up);
    gl.uniform3fv(v3.bgLoc.uFwd, [-back[0], -back[1], -back[2]]);
    const t = Math.tan(fovY/2);
    gl.uniform2f(v3.bgLoc.uScale, t*aspect, t);
    gl.depthMask(false);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.depthMask(true);
    gl.disableVertexAttribArray(v3.bgLoc.aQuad);
  }

  gl.useProgram(v3.prog);
  gl.uniformMatrix4fv(v3.loc.uProj, false,
    v3Perspective(fovY, aspect, Math.max(0.01, v3.dist/100), v3.dist*10));
  gl.uniformMatrix4fv(v3.loc.uView, false, v3LookAt(eye, v3.centre, [0,1,0]));
  // X negated: M2TW models are LEFT-handed (right +X, up +Y, forward +Z, the
  // Direct3D convention) and this camera is right-handed. Handed over as they
  // are, every soldier came out mirrored - shield arm and sword arm swapped.
  // Measured from the models themselves: shield0 sits at -X and primaryactive0
  // at +X, which is shield in the left hand and weapon in the right.
  gl.uniformMatrix4fv(v3.loc.uModel, false,
    [-1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
  gl.uniform3fv(v3.loc.uKey, v3Norm([0.45, 0.85, 0.7]));   // above, front, left
  gl.uniform3fv(v3.loc.uEye, back);

  const bind = (buf, loc, size) => {
    if(loc < 0) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  };
  bind(v3.bPos, v3.loc.aPos, 3);
  bind(v3.bNormal, v3.loc.aNormal, 3);
  bind(v3.bUv, v3.loc.aUv, 2);

  // One texture for the whole model - the glued pair - so every group is the
  // same bind and the UVs alone decide which sheet a triangle lands on.
  const textured = !!(v3.cas ? (v3.casTexGl && v3.casTexGl.size && g.has_uvs)
                             : (v3.texture && g.has_uvs));
  if(textured){
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, v3.texture);
    gl.uniform1i(v3.loc.uTex, 0);
  }
  gl.uniform1f(v3.loc.uHasTex, textured ? 1 : 0);
  // 0.5 for a glued pair, 1.0 for a lone sheet - v3Apply sets it with the bind
  gl.uniform1f(v3.loc.uUScale, v3.uScale || 0.5);
  // whether there are two sheets to tell apart, which is not the same as how
  // far u was scaled - a lone sheet spanning the space is halved too
  gl.uniform1f(v3.loc.uPair, v3.texAtt ? 1 : 0);
  // UV mode needs the coordinate, not the art, so it survives a missing texture
  gl.uniform1f(v3.loc.uUv, (v3.uv && g.has_uvs) ? 1 : 0);

  const visible = v3Visible();
  gl.uniform1f(v3.loc.uFlat, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, v3.bIdx);
  for(const idx of visible){
    const grp = g.groups[idx];
    // A .cas names a texture per mesh, so the bind moves inside the loop: a
    // settlement is walls on one sheet, buildings on another and the faction
    // banner on a third, and one bind for the model would paint two of the
    // three with the wrong art. A .mesh keeps the single bind above - its two
    // sheets are glued and the UVs alone say which one a triangle lands on.
    if(v3.cas){
      const t = v3.casTexGl && v3.casTexGl.get(grp.texture || '');
      if(t){
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.uniform1i(v3.loc.uTex, 0);
      }
      gl.uniform1f(v3.loc.uHasTex, (t && g.has_uvs) ? 1 : 0);
    }
    gl.drawElements(gl.TRIANGLES, grp.count, gl.UNSIGNED_SHORT, grp.start*2);
  }
  if(v3.wire){
    gl.uniform1f(v3.loc.uFlat, 1);
    gl.uniform1f(v3.loc.uHasTex, 0);
    gl.uniform1f(v3.loc.uUv, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, v3.bLines);
    for(const idx of visible){
      const grp = g.groups[idx];
      gl.drawElements(gl.LINES, grp.count*2, gl.UNSIGNED_SHORT, grp.start*4);
    }
  }
}

/* --- orbit ---------------------------------------------------------------- */

function v3Wire(canvas){
  let last = null, pan = false;
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  canvas.addEventListener('pointerdown', e => {
    last = [e.clientX, e.clientY]; pan = (e.button === 2 || e.shiftKey);
    if(v3) v3.drag = true;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointerup', e => {
    last = null; if(v3) v3.drag = false;
    try{ canvas.releasePointerCapture(e.pointerId); }catch(err){}
  });
  canvas.addEventListener('pointermove', e => {
    if(!last || !v3) return;
    const dx = e.clientX - last[0], dy = e.clientY - last[1];
    last = [e.clientX, e.clientY];
    if(pan){
      // pan across the screen plane, scaled so the model keeps up with the cursor
      const k = v3.dist / 500;
      v3.centre[0] -= dx * k * Math.cos(v3.yaw);
      v3.centre[2] += dx * k * Math.sin(v3.yaw);
      v3.centre[1] += dy * k;
    }else{
      v3.yaw -= dx * 0.01;
      v3.pitch = Math.max(-1.5, Math.min(1.5, v3.pitch + dy * 0.01));
    }
  });
  canvas.addEventListener('wheel', e => {
    if(!v3) return;
    e.preventDefault();
    v3.dist = Math.max(0.05, v3.dist * (e.deltaY > 0 ? 1.12 : 0.89));
  }, {passive:false});
}


/* --- the strat model's own three panels, 16k --------------------------------
   A .cas has no LODs, no skins and no part variants, so the three surfaces a
   .mesh fills with those say something else here: which meshes the scene holds
   and what each is painted with, and what the decoder could not read. */

/* One image per material, each applying as it lands. A settlement wants three
   and a banner wants one, and a mod that names a texture it does not ship is
   ordinary rather than an error - the mesh draws untextured and the facts
   panel says which file is missing. */
function v3LoadCasSkins(want){
  v3.tex = null; v3.texAtt = null; v3.uScale = 1.0;
  v3.casTex = new Map();
  const rels = new Map();
  (v3.geo ? v3.geo.groups : []).forEach(grp => {
    const tex = grp.texture || '';
    if(tex && v3.casRel && v3.casRel.get(tex)) rels.set(tex, v3.casRel.get(tex));
  });
  if(!rels.size){ v3Apply(); return; }
  rels.forEach((rel, tex) => {
    const img = new Image();
    img.onload = () => { if(want===v3Gen && v3){ v3.casTex.set(tex, img); v3Apply(); } };
    img.onerror = () => { if(want===v3Gen && v3){ v3.casTex.delete(tex); v3Apply(); } };
    img.src = `/model_texture?mod=${enc(v3.mod)}&rel=${enc(rel)}`;
  });
}

/* The GL side of the above: one texture object per sheet, keyed by the path
   the material writes, which is the key the draw loop has on each group. */
function v3CasApply(){
  const gl = v3.gl;
  v3.casTexGl = new Map();
  (v3.casTex || new Map()).forEach((img, tex) => {
    const t = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, t);
    // NOT flipped, for the reason v3Apply gives: M2TW is a Direct3D game and
    // puts v=0 at the top. The strat models are exported by the same tool.
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    const pot = n => n > 0 && (n & (n-1)) === 0;
    if(pot(img.width) && pot(img.height)){
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    }else{
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    v3.casTexGl.set(tex, t);
  });
  v3Parts();
  v3Facts();
}

/* One row per mesh in the scene, with the texture it is painted with. The
   checkbox is the same one a .mesh part gets - a settlement's faction banner
   is worth being able to drop to see the walls behind it. */
function v3CasParts(host){
  const groups = v3.geo.groups;
  host.innerHTML = `<div class="k">Meshes <span class="count">${groups.length}`
    + ` in this scene</span></div>`
    + groups.map((grp, n) => {
    const key = 'm' + n;
    const rel = grp.texture ? (v3.casRel && v3.casRel.get(grp.texture)) : '';
    const paint = !grp.texture ? '<span class="v3tag">no material</span>'
      : rel ? `<span class="count">${esc(grp.texture.split(/[\\/]/).pop())}</span>`
            : `<span class="v3tag">${esc(grp.texture.split(/[\\/]/).pop())} not in this mod</span>`;
    return `<label class="v3part">
      <input type="checkbox" ${v3.hidden[key]?'':'checked'}
        onchange="v3TogglePart('${q1(esc(key))}')">
      <span class="v3nm">${esc(grp.name || '(unnamed)')}</span>${paint}
      <span class="count">${grp.count/3} tris</span></label>`;
  }).join('');
}

function v3CasFacts(host, g){
  const i = v3.info;
  const size = [0,1,2].map(k => (g.max[k]-g.min[k]).toFixed(2));
  const missing = (i.materials||[]).filter(m => m.texture && !m.rel);
  host.innerHTML = docPoints('This model:', [
    `<b>${g.vertices.toLocaleString()}</b> vertices, <b>${g.triangles.toLocaleString()}</b> triangles`,
    `${g.groups.length} mesh${g.groups.length===1?'':'es'}, each with its own vertices`,
    `${size[0]} × ${size[1]} × ${size[2]} in game units`,
    `exported by 3ds max, file version ${i.version}`,
    i.nodes && i.nodes.length > 1
      ? `${i.nodes.length} nodes - a skeleton, ${esc(i.nodes[1])} first`
      : 'one node, Scene Root - a static model',
    i.keys ? `${i.keys} animation keys over ${i.length}s, which this viewer does not play`
           : 'no animation keys',
    (i.materials||[]).length
      ? `${i.materials.length} material${i.materials.length===1?'':'s'}: `
        + (i.materials.map(m => m.texture
            ? `<code>${esc(m.texture)}</code>` : 'one with no texture').join(', '))
      : 'no materials',
    missing.length
      ? `<b>${missing.length}</b> of those texture${missing.length===1?' is':'s are'} `
        + 'not in this mod, so what uses them draws bare'
      : ''
  ]) + (g.notes||[]).map(n => `<div class="w-warn" style="margin-top:6px">${esc(n)}</div>`).join('');
}
