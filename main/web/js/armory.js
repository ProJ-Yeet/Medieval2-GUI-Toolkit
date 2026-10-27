/* =========================================================================
   Armory Studio - the kitbash workbench, a tab of the Models Editor (Phase 95e on)

   A port of the behaviour of Armory Studio 3D (muhamadridhomm, MIT) onto this
   toolkit: no three.js, no code of his, none of his art. One model is built out
   of the parts of others.

     * an ASSET is a model loaded to take parts from: a model entry or a unit's
       models out of any installed mod, or a .obj/.glb/.dae on disk;
     * an OBJECT is one part of the model being edited: one group of an asset,
       with what was done to it (moved, renamed, hidden, recoloured);
     * the PROJECT is the assets and the objects, kept in config/armory/ and
       never a copy of anyone's art: the export (95i) reads each source again.

   The page draws with ONE WebGL context on a canvas that is never on the page:
   it draws the viewport and copies it into the viewport's own 2D canvas, and it
   draws each object's thumbnail the same way. Both WebGL traps of this UI apply
   (memory: requestAnimationFrame never fires in a hidden tab, and loseContext is
   final): a frame is asked for, not looped, and a lost context is rebuilt.
   ========================================================================= */

const ARM = {
  gl: null, glCanvas: null, prog: null,
  assets: new Map(),      // key -> {view, geo, buf, tex, img, uScale, err, loading}
  cam: {yaw: 0.6, pitch: 0.25, dist: 4, target: [0, 1, 0]},
  hover: null, sel: new Set(),
  frameAsked: false, catalogue: {}, mods: null,
  thumbs: new Map(),      // "<asset>|<group>" -> dataURL
  saveTimer: 0, loaded: false,
};

const ARM_VERT = `
attribute vec3 aPos; attribute vec3 aNormal; attribute vec2 aUv;
uniform mat4 uProj, uView, uModel;
varying vec3 vNormal; varying vec2 vUv; varying vec3 vPos;
void main(){
  vNormal = mat3(uModel) * aNormal;
  vUv = aUv;
  vec4 w = uModel * vec4(aPos, 1.0);
  vPos = w.xyz;
  gl_Position = uProj * uView * w;
}`;
const ARM_FRAG = `#extension GL_OES_standard_derivatives : enable
precision mediump float;
varying vec3 vNormal; varying vec2 vUv; varying vec3 vPos;
uniform sampler2D uTex, uNTex;
uniform float uHasTex, uUScale, uHi, uSel, uFlip, uXray, uHasN;
uniform float uCard, uMask, uLAmt, uAmb, uLevel, uPoint;
uniform vec3 uLDir, uLPos;
uniform vec4 uCrop;
${V3_ENV}
void main(){
  // uCrop: a dyed object's own crop of the sheet, (x, y, width, height)
  // in the glued image's 0..1; the whole sheet otherwise
  vec2 st = (vec2(vUv.x * uUScale, vUv.y) - uCrop.xy) / uCrop.zw;
  vec4 base = uHasTex > 0.5 ? texture2D(uTex, st) : vec4(0.72, 0.66, 0.56, 1.0);
  if(uHasTex > 0.5 && base.a < 0.35) discard;
  // 99b: the page mirrors x (ARM_MIRROR) and keeps the game's winding, so a
  // face the game shows from outside winds clockwise here: its front is
  // what GL calls the back. The .glb export reverses the winding for the
  // same reason (modelexport.py), and Blender agrees with that.
  bool front = !gl_FrontFacing;
  vec3 n = normalize(vNormal) * (front ? 1.0 : uFlip);
  if(uHasN > 0.5){
    // 95j: the normal map's preview, its tangents worked out per pixel
    // from how the UVs run across the surface (a cotangent frame)
    vec3 dp1 = dFdx(vPos), dp2 = dFdy(vPos);
    vec2 duv1 = dFdx(st), duv2 = dFdy(st);
    vec3 dp2p = cross(dp2, n), dp1p = cross(n, dp1);
    vec3 T = dp2p * duv1.x + dp1p * duv2.x, B = dp2p * duv1.y + dp1p * duv2.y;
    float inv = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-12));
    vec3 tn = texture2D(uNTex, st).xyz * 2.0 - 1.0;
    n = normalize(T * inv * tn.x + B * inv * tn.y + n * tn.z);
  }
  vec3 light = v3Env(n) * 0.62 + vec3(1.0, 0.96, 0.9) * 0.5 * max(dot(n, normalize(vec3(0.4, 0.8, 0.5))), 0.0)
             + vec3(0.62, 0.7, 0.85) * 0.2 * max(dot(n, normalize(vec3(-0.6, 0.2, -0.7))), 0.0);
  vec3 col = pow(clamp(base.rgb * light, 0.0, 1.0), vec3(0.78));
  if(uCard > 0.5){
    // 95m: the card maker's one lamp, a sun or a point, and an ambient
    vec3 L = uPoint > 0.5 ? uLPos - vPos : uLDir;
    float att = uPoint > 0.5 ? 1.0 / (1.0 + 0.08 * dot(L, L)) : 1.0;
    float k = max(dot(n, normalize(L)), 0.0) * uLAmt * att;
    col = clamp(base.rgb * (uAmb + k) * uLevel, 0.0, 1.0);
  }
  if(uMask > 0.5){ gl_FragColor = vec4(1.0); return; }
  col = mix(col, vec3(0.36, 0.55, 0.94), uHi * 0.28);
  col = mix(col, vec3(0.97, 0.62, 0.18), uSel * 0.30);
  // face orientation, Blender's colours: blue the front, red the back
  if(uFlip < 0.0) col = mix(col, front ? vec3(0.2, 0.4, 1.0) : vec3(1.0, 0.15, 0.15), 0.55);
  gl_FragColor = vec4(col, uXray > 0.5 ? 0.45 : 1.0);
}`;

/* --- the project ----------------------------------------------------------- */

function armProj(){
  const p = state.armProj = state.armProj || {};
  // an empty project comes back from the server as {}; fill what it lacks
  if(!p.v){ Object.assign(p, {v: 1, assets: p.assets || [], objects: p.objects || [],
                              collections: p.collections || [], base: p.base || null}); }
  if(!Number.isFinite(p.nextId)){
    // ids lost to that (95e saved null ones) are given back in order
    let top = 0;
    for(const o of p.objects || []) if(Number.isFinite(o.id)) top = Math.max(top, o.id);
    for(const c of p.collections || []) if(Number.isFinite(c.id)) top = Math.max(top, c.id);
    p.nextId = top + 1;
    for(const o of p.objects || []) if(!Number.isFinite(o.id)) o.id = p.nextId++;
  }
  return p;
}
function armSave(){
  armUndoNote();
  clearTimeout(ARM.saveTimer);
  if(!ARM.projReady) return;
  ARM.saveTimer = setTimeout(() => {
    if(typeof armExtrasInto === 'function') armExtrasInto(armProj());
    api.post('/api/armory/project', {project: armProj()}).catch(() => {});
  }, 600);
}

/* --- undo and redo (99i) ------------------------------------------------------

   Every change to the project ends in armSave, so a step is the project as
   armSave last found it: a snapshot of the JSON, which holds no art and is
   small. What only changes the look of the page (folds, an asset's list or
   gallery, the animation chosen) is left out, and kept as it is on a step
   back or forward. A drag or a slider saves once, when it stops, and so is
   one step. */
const ARM_UNDO_MAX = 200;
function armUndoState(){
  const p = armProj();
  return JSON.stringify(Object.assign({}, p, {ui: undefined, anim: undefined, extra: undefined, session: undefined,
    assets: (p.assets || []).map(a => Object.assign({}, a, {open: undefined, show: undefined}))}));
}
function armUndoNote(){
  const u = ARM.undo || (ARM.undo = {past: [], future: [], last: null});
  if(u.restoring || !ARM.loaded) return;
  const now = armUndoState();
  if(u.last === null || now === u.last){ u.last = now; return; }
  u.past.push(u.last);
  if(u.past.length > ARM_UNDO_MAX) u.past.shift();
  u.future = [];
  u.last = now;
  armUndoButtons();
}
function armUndoButtons(){
  const u = ARM.undo, a = document.getElementById('armUndoBtn'), b = document.getElementById('armRedoBtn');
  if(a) a.disabled = !(u && u.past.length);
  if(b) b.disabled = !(u && u.future.length);
}
function armUndo(redo){
  if(ARM.xform) return;
  armUndoNote();             // a change still waiting on its save is a step too
  const u = ARM.undo;
  const from = u && (redo ? u.future : u.past);
  if(!from || !from.length){ toast(redo ? tt('armory.nothing_to_redo') : tt('armory.nothing_to_undo')); return; }
  (redo ? u.past : u.future).push(u.last);
  u.last = from.pop();
  armUndoApply(JSON.parse(u.last));
}
/* Puts a project back, keeping how the page shows it. */
function armUndoApply(next){
  const keep = armProj();
  next.ui = keep.ui; next.anim = keep.anim;
  for(const a of next.assets || []){
    const was = (keep.assets || []).find(x => armAssetKey(x) === armAssetKey(a));
    if(was){ a.open = was.open; a.show = was.show; }
  }
  state.armProj = next;
  // an asset a step brings back is read again
  for(const a of next.assets || []) armLoadAsset(a);
  ARM.sel = new Set([...ARM.sel].filter(id => next.objects.some(o => o.id === id)));
  if(ARM.detail && !next.objects.some(o => o.id === ARM.detail.id)) ARM.detail = null;
  const quiet = ARM.dyeQuiet;
  for(const o of next.objects) if(typeof armDyeChanged === 'function') armDyeChanged(o);
  ARM.dyeQuiet = quiet;
  const u = ARM.undo;
  u.restoring = true; armSave(); u.restoring = false;
  armPaintAssets(); armPaintObjects(); armPaintBar(); armPaintFoot();
  if(typeof armPaintDetailBar === 'function') armPaintDetailBar();
  armUndoButtons();
  armFrame();
  // the UV editor redraws the step's UVs (100m)
  if(ARM.uvEd){ if(armObj(ARM.uvEd.id)){ ARM.uvEd.sel.clear(); armUvBuild(); armUvPanel(); } else armUvClose(); }
}
/* A project opened or started afresh starts its own history. */
function armUndoReset(){ ARM.undo = {past: [], future: [], last: null}; armUndoNote(); }

function armAssetKey(a){ return a.kind === 'external' ? 'ext|' + (a.path || '').toLowerCase() : `${a.mod}|${a.entry}`; }
function armAssetLabel(a){
  if(!a) return '';
  if(a.kind === 'external') return a.path.split(/[\\/]/).pop();
  return a.unit ? `${a.entry} · ${a.unit}` : a.entry;
}
function armObj(id){ return armProj().objects.find(o => o.id === id); }

/* --- the tab --------------------------------------------------------------- */

/* The project and its assets, read once a session; the card maker (95m)
   draws the same model without the tab being opened. */
async function armEnsureLoaded(){
  if(ARM.loaded) return;
  ARM.loaded = true;
  try{ state.armProj = await api.get('/api/armory/project'); }catch(e){ state.armProj = null; }
  // 99o: from here the page's project is the one on disk, and only from
  // here may it be sent back (a page closing while it loads sends nothing)
  ARM.projReady = true;
  const p = armProj();
  p.objects = p.objects || []; p.assets = p.assets || []; p.collections = p.collections || [];
  // 95e kept one source per object; an object holds pieces from 95f on
  for(const o of p.objects) if(!o.src){ o.src = [{asset: o.asset, group: o.group}]; delete o.asset; delete o.group; }
  armUndoReset();
  // 99o: the camera and the card maker's and export's settings ride with it
  if(typeof armExtrasFrom === 'function'){ armExtrasFrom(p); armSessCheck(); }
  ARM.loading = Promise.all(p.assets.map(a => armLoadAsset(a)));
  armLoadPresets().then(() => { if(state.mode === 'armory') armPaintObjects(); });
}

async function renderArmory(){
  count.textContent = '';
  if(!ARM.loaded){
    await armEnsureLoaded();
    if(stale('armory')) return;
  }
  main.innerHTML = bmdbTabsHtml(tt('armory.tab_note')) + `<div class="armgrid${armSideShut('left') ? ' lshut' : ''}${armSideShut('right') ? ' rshut' : ''}" id="armGrid">
    <aside class="armleft" id="armLeft"></aside>
    <section class="armmid">
      <div class="armbar" id="armBar"></div>
      <div class="armview" id="armView"></div>
      <div class="armfoot" id="armFoot"></div>
    </section>
    <aside class="armright" id="armRight"></aside>
  </div>
  <button class="armfullexit" onclick="armFullView(false)" title="${esc(tt('armory.full_view_exit_title'))}">✕ ${tt('armory.full_view_exit')}</button>`;
  document.body.classList.remove('armfull');
  armMountView();
  armPaintAssets();
  armPaintObjects();
  armPaintBar();
  armPaintFoot();
  if(typeof armAnimPaint === 'function') armAnimPaint();
  armFrame();
  if(ARM.uvEd && armObj(ARM.uvEd.id)){ armUvBuild(); armUvPanel(); } else ARM.uvEd = null;
}

function armPaintBar(){
  const el = document.getElementById('armBar');
  if(!el) return;
  const p = armProj();
  const tris = p.objects.filter(o => !o.hidden).reduce((s, o) => s + armObjTris(o), 0);
  const sess = (p.session || {}).name;
  el.innerHTML = `<b>${esc(sess || p.name || tt('armory.untitled'))}</b>
    ${ARM.unclean ? `<button class="mini warn" onclick="armSessOpen()" title="${esc(tt('armory.sess_crash_title'))}">${tt('armory.sess_crash')}</button>` : ''}
    <span class="count">${tt('armory.bar_counts', {objects: p.objects.length, tris: tris.toLocaleString()})}</span>
    <span style="flex:1"></span>
    <button class="mini" id="armUndoBtn" onclick="armUndo(false)" title="${esc(tt('armory.undo_title'))}"${ARM.undo && ARM.undo.past.length ? '' : ' disabled'}>↶</button>
    <button class="mini" id="armRedoBtn" onclick="armUndo(true)" title="${esc(tt('armory.redo_title'))}"${ARM.undo && ARM.undo.future.length ? '' : ' disabled'}>↷</button>
    <button class="mini" onclick="armFullView()" title="${esc(tt('armory.full_view_title'))}">⛶ ${tt('armory.full_view')}</button>
    <button class="mini" onclick="armTexOpen()" title="${esc(tt('armory.textures_title'))}">🖼 ${tt('armory.textures')}</button>
    <button class="mini" onclick="armUvOpen()" title="${esc(tt('armory.uv_edit_title'))}">${tt('armory.uv_edit')}</button>
    <button class="mini" onclick="armFrameAll()" title="${esc(tt('armory.frame_all_title'))}">${tt('armory.frame_all')}</button>
    <button class="mini" onclick="armSessOpen()" title="${esc(tt('armory.sess_button_title'))}">${tt('armory.sess_button')}</button>
    <button class="mini" onclick="armLibOpen()" title="${esc(tt('armory.lib_open_title'))}">${tt('armory.lib_open')}</button>
    <button class="mini" onclick="armNew()">${tt('armory.new_project')}</button>
    <button class="mini" onclick="reportOpen('armory')" title="${esc(tt('armory.report_title'))}">🐞 ${tt('armory.report')}</button>
    <button class="mini primary" onclick="armExportOpen()"${p.objects.length ? '' : ' disabled'} title="${esc(tt('armory.export_title'))}">${tt('armory.export_button')}</button>`;
}
function armPaintFoot(){
  if(typeof armPaintSliders === 'function') armPaintSliders();
}
function armObjTris(o){
  let n = 0;
  for(const pc of o.src || []){
    if(pc.tris){ n += pc.tris.length; continue; }
    const a = ARM.assets.get(pc.asset);
    const ob = a && a.view && a.view.objects[pc.group];
    n += ob ? ob.triangles : 0;
  }
  return n;
}
/* An object holds pieces: a whole group of an asset, or some of its
   triangles (a split, 95f), each with a matrix of its own once merged. */
const armUses = (o, key, group) => (o.src || []).some(pc => pc.asset === key && (group == null || pc.group === group));

function armNew(){
  if(armProj().objects.length && !confirm(tt('armory.new_project_confirm'))) return;
  state.armProj = null;
  ARM.sel.clear();
  armSave();
  renderArmory();
}

/* --- the assets panel ------------------------------------------------------ */

function armPaintAssets(){
  const el = document.getElementById('armLeft');
  if(!el) return;
  const p = armProj();
  if(armSideShut('left')){ el.innerHTML = armStripHtml('left', tt('armory.loaded_assets'), p.assets.length); return; }
  armKeepScroll(el, () => {
    el.innerHTML = `<div class="armhead">
        <button class="armfold" onclick="armSideToggle('left')" title="${esc(tt('armory.panel_fold'))}">◂ ${tt('armory.loaded_assets')}</button>
        <span class="count">${p.assets.length}</span>
        <span style="flex:1"></span>
        <button class="mini primary" onclick="armImportOpen()">${tt('armory.import')}</button>
      </div>
      ${p.assets.length ? `<label class="armcheck armonlyused" title="${esc(tt('armory.only_used_title'))}"><input type="checkbox"${armOnlyUsed() ? ' checked' : ''}
        onchange="armSetOnlyUsed(this.checked)"> ${tt('armory.only_used')}</label>` : ''}
      ${p.assets.length ? p.assets.map(armAssetHtml).join('')
        : `<div class="empty armempty">${tt('armory.no_assets_yet')}</div>`}`;
  });
  armThumbsPaint();
}

/* 99a: a panel repainted keeps its scroll, and so does the page under it;
   a Pull used to move both when the rows under the cursor were rebuilt. */
function armKeepScroll(el, paint){
  const doc = document.scrollingElement, top = el.scrollTop, page = doc ? doc.scrollTop : 0;
  paint();
  el.scrollTop = top;
  if(doc && doc.scrollTop !== page) doc.scrollTop = page;
}

/* 99d: Loaded assets (left) and Objects (right) fold to a strip and open
   again, the viewport taking the room; how they were left is a setting. */
const armSideShut = side => !!(state.settings || {})['armory_' + side + '_shut'];
function armSideToggle(side){
  const k = 'armory_' + side + '_shut', v = !armSideShut(side);
  state.settings[k] = v;
  api.post('/api/settings', {[k]: v}).catch(() => {});
  const g = document.getElementById('armGrid');
  if(g){ g.classList.toggle('lshut', armSideShut('left')); g.classList.toggle('rshut', armSideShut('right')); }
  if(side === 'left') armPaintAssets(); else armPaintObjects();
  armFrame();
}
function armStripHtml(side, label, n){
  return `<button class="armstrip" onclick="armSideToggle('${side}')" title="${esc(tt('armory.panel_open'))}">
    <span>${side === 'left' ? '▸' : '◂'}</span><span class="armstriptext">${esc(label)}</span><span class="count">${n}</span></button>`;
}

// 100h: "only the parts in the model", a setting like the panels' folds
const armOnlyUsed = () => !!(state.settings || {}).armory_only_used;
function armSetOnlyUsed(v){
  state.settings.armory_only_used = v;
  api.post('/api/settings', {armory_only_used: v}).catch(() => {});
  armPaintAssets();
}
function armAssetHtml(a){
  const key = armAssetKey(a), live = ARM.assets.get(key) || {};
  const v = live.view;
  const used = v ? v.objects.filter(ob => armProj().objects.some(o => armUses(o, key, ob.index))).length : 0;
  const open = !!a.open;
  // 100j's gallery default reaches Loaded assets too (the tester's notes)
  const mode = a.show || 'gallery';
  let body = '';
  if(open){
    if(live.err) body = `<div class="w-bad armnote">${esc(live.err)}</div>`;
    else if(!v) body = `<div class="count armnote">${tt('armory.reading')}</div>`;
    else{
      const objs = v.objects.filter(ob => !armOnlyUsed() || armProj().objects.some(o => armUses(o, key, ob.index)))
        .map(o => armAssetObjHtml(a, key, o, mode)).join('');
      body = `<div class="armobjtools">
          <button class="mini${mode === 'list' ? ' on' : ''}" onclick="armAssetShow('${esc(q1(key))}','list')">${tt('armory.as_list')}</button>
          <button class="mini${mode === 'gallery' ? ' on' : ''}" onclick="armAssetShow('${esc(q1(key))}','gallery')">${tt('armory.as_gallery')}</button>
          <span style="flex:1"></span>
          <button class="mini" onclick="armPullAll('${esc(q1(key))}')" title="${esc(tt('armory.pull_all_title'))}">${tt('armory.pull_all')}</button>
        </div>
        ${armSkinPickHtml(a, key, v)}
        <div class="${mode === 'gallery' ? 'armtiles' : 'armrows'}">${objs}</div>`;
    }
  }
  const sub = a.kind === 'external' ? tt('armory.external_file') : esc(a.mod);
  const isBase = armProj().base === key;
  return `<div class="armasset${open ? ' open' : ''}">
    <div class="armassethead" onclick="armAssetToggle('${esc(q1(key))}')">
      <span class="armcaret">${open ? '▾' : '▸'}</span>
      <span class="armname" title="${esc(a.kind === 'external' ? a.path : a.mesh || '')}">${esc(armAssetLabel(a))}</span>
      ${isBase ? `<span class="pill">${tt('armory.base')}</span>` : ''}
      <span class="count">${v ? ttN('armory.asset_sub', v.objects.length, {where: sub}) : sub}</span>
      ${v ? `<span class="pill${used ? '' : ' warn'}" title="${esc(tt('armory.asset_used_title'))}">${tt('armory.asset_used', {used, n: v.objects.length})}</span>` : ''}
      ${a.kind === 'external' ? `<button class="mini" onclick="event.stopPropagation();armPickSheetsAll('${esc(q1(key))}')" title="${esc(tt('armory.sheets_all_title'))}">🎨</button>` : ''}
      <button class="mini" onclick="event.stopPropagation();armLibAddAsset('${esc(q1(key))}')" title="${esc(tt('armory.lib_add_title'))}">${tt('armory.lib_add')}</button>
      <button class="mini armx" onclick="event.stopPropagation();armRemoveAsset('${esc(q1(key))}')" title="${esc(tt('armory.remove_asset'))}">✕</button>
    </div>${body}</div>`;
}

function armSkinPickHtml(a, key, v){
  if(a.kind === 'external' || !v.skins || v.skins.length < 2) return '';
  return `<label class="count armskin">${tt('armory.skin')}
    <select onchange="armSetSkin('${esc(q1(key))}', +this.value)">${v.skins.map((s, i) =>
      `<option value="${i}"${(a.skin || 0) === i ? ' selected' : ''}>${esc(v3SkinLabel(s))}</option>`).join('')}</select></label>`;
}

/* Two objects are the same art when their triangles hash the same, or when
   their triangle count, centre and spread agree to a tenth of a millimetre:
   the second catches a copy that went through an .obj's six decimals. */
function armSameArt(a, b){
  if(a.fingerprint === b.fingerprint) return true;
  const x = a.shape, y = b.shape;
  if(!x || !y || x[0] !== y[0] || !x[0]) return false;
  for(let i = 1; i < 5; i++) if(Math.abs(x[i] - y[i]) > 1e-4) return false;
  return true;
}
function armDupOf(key, ob){
  // the same triangles somewhere else already loaded
  const hits = [];
  for(const [k, live] of ARM.assets){
    if(k === key || !live.view) continue;
    for(const o of live.view.objects)
      if(armSameArt(o, ob)){ hits.push(`${o.mesh} · ${armAssetLabel(live.asset)}`); break; }
  }
  return hits;
}

function armAssetObjHtml(a, key, ob, mode){
  const inModel = armProj().objects.some(o => armUses(o, key, ob.index));
  const dups = armDupOf(key, ob);
  const sheet = ob.sheets === 'attach' ? tt('armory.sheet_attach') : ob.sheets === 'both' ? tt('armory.sheet_both') : tt('armory.sheet_main');
  const tex = a.kind === 'external'
    ? (armObjTexture(a, ob.index) ? '' : `<button class="mini" onclick="event.stopPropagation();armPickTexture('${esc(q1(key))}',${ob.index})" title="${esc(tt('armory.no_texture_found'))}">🎨 ${tt('armory.pick_sheet')}</button>`)
    : '';
  const badge = dups.length ? `<span class="pill warn" title="${esc(tt('armory.duplicate_title', {where: dups.join(', ')}))}">${tt('armory.duplicate')}</span>` : '';
  const title = `${ob.name} / ${ob.mesh}${ob.flag ? ' (opt)' : ''}`;
  const tk = `${key}|${ob.index}`;
  if(mode === 'gallery')
    return `<div class="armtile${inModel ? ' in' : ''}" ondblclick="armPull('${esc(q1(key))}',${ob.index})" title="${esc(title)}">
      <img class="armthumb" data-thumb="${esc(tk)}" alt="">
      <div class="armtilename">${esc(ob.mesh)}</div>
      <div class="armtilefoot">${badge}${tex}
        <button class="mini" onclick="armPull('${esc(q1(key))}',${ob.index})">${inModel ? '✓' : tt('armory.pull')}</button></div>
    </div>`;
  return `<div class="armrow${inModel ? ' in' : ''}" ondblclick="armPull('${esc(q1(key))}',${ob.index})">
    <span class="armrowname" title="${esc(title)}"><b>${esc(ob.name)}</b> ${esc(ob.mesh)}${ob.flag ? ` <i class="count">${tt('armory.opt')}</i>` : ''}</span>
    <span class="count">${ob.triangles.toLocaleString()} · ${sheet}</span>${badge}${tex}
    <button class="mini" onclick="armPull('${esc(q1(key))}',${ob.index})">${inModel ? '✓' : tt('armory.pull')}</button>
  </div>`;
}

function armAssetToggle(key){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  if(!a) return;
  a.open = !a.open; armSave(); armPaintAssets();
}
function armAssetShow(key, mode){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  if(!a) return;
  a.show = mode; armSave(); armPaintAssets();
}
function armSetSkin(key, i){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  if(!a) return;
  a.skin = i; armSave();
  const live = ARM.assets.get(key);
  if(live) armLoadSkin(a, live);
}
function armRemoveAsset(key){
  const p = armProj();
  const used = p.objects.filter(o => armUses(o, key)).length;
  if(used && !confirm(ttN('armory.remove_asset_confirm', used))) return;
  p.objects = p.objects.filter(o => !armUses(o, key));
  p.assets = p.assets.filter(a => armAssetKey(a) !== key);
  if(p.base === key) p.base = null;
  const live = ARM.assets.get(key);
  if(live && live.buf && ARM.gl) armFreeBuffers(live);
  ARM.assets.delete(key);
  armSave(); armPaintAssets(); armPaintObjects(); armPaintBar(); armFrame();
}

/* --- pulling a part into the model ----------------------------------------- */

function armPull(key, group){
  const p = armProj();
  const live = ARM.assets.get(key);
  if(!live || !live.view) return;
  const ob = live.view.objects[group];
  if(p.objects.some(o => armUses(o, key, group))){
    toast(tt('armory.already_in_model', {name: ob.mesh}));
    return;
  }
  p.objects.push(armNewObject(key, ob));
  if(typeof armBoneCheck === 'function') armBoneCheck(key, [group]);
  armSave(); armPaintAssets(); armPaintObjects(); armPaintBar(); armFrame();
}
function armNewObject(key, ob){
  const p = armProj();
  return {id: p.nextId++, src: [{asset: key, group: ob.index}], name: ob.name, mesh: ob.mesh,
          flag: ob.flag, hidden: false, coll: null, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1],
          material: '', dye: null};
}
function armPullAll(key){
  const live = ARM.assets.get(key);
  if(!live || !live.view) return;
  const p = armProj();
  let added = 0;
  for(const ob of live.view.objects){
    if(p.objects.some(o => armUses(o, key, ob.index))) continue;
    p.objects.push(armNewObject(key, ob)); added++;
  }
  toast(ttN('armory.pulled_n', added));
  if(added && typeof armBoneCheck === 'function') armBoneCheck(key);
  armSave(); armPaintAssets(); armPaintObjects(); armPaintBar(); armFrameAll();
}

/* --- loading an asset ------------------------------------------------------ */

async function armLoadAsset(a){
  const key = armAssetKey(a);
  let live = ARM.assets.get(key);
  if(live && (live.view || live.loading)) return live;
  live = {asset: a, loading: true};
  ARM.assets.set(key, live);
  try{
    live.view = a.kind === 'external'
      ? await api.get('/api/armory/external?path=' + enc(a.path), 1)
      : await api.get(`/api/armory/asset?mod=${enc(a.mod)}&entry=${enc(a.entry)}`, 1);
    if(a.kind === 'external') a.id = live.view.id;
    const url = a.kind === 'external' ? '/api/armory/geometry?ext=' + enc(live.view.id)
      : `/api/model/geometry?mod=${enc(a.mod)}&entry=${enc(a.entry)}&lod=0`;
    const r = await fetch(url, {cache: 'no-store'});
    if(!r.ok) throw await httpAnswer(r);
    live.geo = v3Parse(await r.arrayBuffer());
    armUpload(live);
    armLoadSkin(a, live);
  }catch(e){ live.err = errText(e); }
  live.loading = false;
  if(state.mode === 'armory'){ armPaintAssets(); armPaintBar(); armFrame(); }
  return live;
}

/* Calls fn(vertex) for each index of a piece, every `step`-th one. */
function armPieceEach(live, pc, fn, step){
  const g = live.geo.groups[pc.group];
  if(!g) return;
  const I = live.geo.indices, k = step || 1;
  if(pc.weld || pc.flip){
    // 100n: Optimize's merges and outward turns, as armory.piece_indices reads them
    const W = pc.weld || {}, F = armFlipSet(pc);
    const n = pc.tris ? pc.tris.length : g.count / 3;
    for(let i = 0; i < n; i++){
      const t = pc.tris ? pc.tris[i] : i;
      let c3 = [I[g.start + t*3], I[g.start + t*3 + 1], I[g.start + t*3 + 2]];
      if(F.has(t)) c3 = [c3[0], c3[2], c3[1]];
      for(let c = 0; c < 3; c += k){ const v = c3[c]; fn(W[v] != null ? W[v] : v); }
    }
    return;
  }
  if(pc.tris){
    for(const t of pc.tris) for(let c = 0; c < 3; c += k) fn(I[g.start + t*3 + c]);
  }else for(let i = g.start; i < g.start + g.count; i += k) fn(I[i]);
}
/* An object's centre, which it turns and scales about: the mean of its
   pieces' indices where they stand, the way armory.object_mesh counts it. */
const ARM_PIVOT = new WeakMap();
function armPivot(o){
  const sig = JSON.stringify(o.src || []);
  const hit = ARM_PIVOT.get(o);
  if(hit && hit.sig === sig && hit.ready) return hit.p;
  let x = 0, y = 0, z = 0, n = 0, ready = true;
  for(const pc of o.src || []){
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo){ ready = false; continue; }
    const P = live.geo.positions, m = pc.xf;
    armPieceEach(live, pc, v => {
      let px = P[v*3], py = P[v*3+1], pz = P[v*3+2];
      if(m){ const q = [m[0]*px + m[4]*py + m[8]*pz + m[12], m[1]*px + m[5]*py + m[9]*pz + m[13], m[2]*px + m[6]*py + m[10]*pz + m[14]]; px = q[0]; py = q[1]; pz = q[2]; }
      x += px; y += py; z += pz; n++;
    });
  }
  const p = n ? [x/n, y/n, z/n] : [0, 0, 0];
  ARM_PIVOT.set(o, {sig, p, ready});
  return p;
}
/* A split piece's own index buffer, made once per triangle list. */
const ARM_SUB = new WeakMap();
const ARM_FLIP = new WeakMap();
function armFlipSet(pc){
  let hit = ARM_FLIP.get(pc);
  if(!hit || hit.flip !== pc.flip){ hit = {flip: pc.flip, set: new Set(pc.flip || [])}; ARM_FLIP.set(pc, hit); }
  return hit.set;
}
function armPieceBuffer(live, pc){
  let hit = ARM_SUB.get(pc);
  if(hit && hit.tris === pc.tris && hit.weld === pc.weld && hit.flip === pc.flip) return hit;
  const gl = armGl();
  const flat = [];
  armPieceEach(live, pc, v => flat.push(v));
  const idx = new Uint16Array(flat);
  if(hit && hit.buf) gl.deleteBuffer(hit.buf);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
  hit = {buf, count: idx.length, tris: pc.tris, weld: pc.weld, flip: pc.flip};
  ARM_SUB.set(pc, hit);
  return hit;
}

function armObjTexture(a, group){
  const over = (a.textures || {})[group];
  if(over) return over;
  const live = ARM.assets.get(armAssetKey(a));
  const ob = live && live.view && live.view.objects[group];
  return ob ? ob.texture_file || '' : '';
}

/* 100k: a main sheet, then an attachment sheet if wanted, for every object
   of a file from disk at once, each object taking the one it is drawn on */
async function armPickSheetsAll(key){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  const live = ARM.assets.get(key);
  if(!a || !live || !live.view) return;
  const pick = async title => {
    let r;
    try{ r = await api.post('/api/browse_file', {title, filter: 'Images|*.png;*.tga;*.dds;*.jpg;*.jpeg;*.texture;*.bmp'}); }
    catch(e){ toast(errText(e)); return ''; }
    if(!r || !r.path) return '';
    const ok = await api.post('/api/armory/allow_texture', {path: r.path}).catch(() => ({}));
    if(!ok.ok){ toast(tt('armory.not_an_image')); return ''; }
    return r.path;
  };
  const main = await pick(tt('armory.sheets_all_main'));
  if(!main) return;
  const objs = live.view.objects;
  const att = objs.some(o => o.sheets === 'attach') ? await pick(tt('armory.sheets_all_attach')) : '';
  a.textures = a.textures || {};
  for(const o of objs) a.textures[o.index] = o.sheets === 'attach' && att ? att : main;
  armSave();
  armLoadSkin(a, live);
  armPaintAssets(); armFrame();
}
async function armPickTexture(key, group){
  const a = armProj().assets.find(x => armAssetKey(x) === key);
  if(!a) return;
  let r;
  try{ r = await api.post('/api/browse_file', {title: tt('armory.pick_sheet_title'),
    filter: 'Images|*.png;*.tga;*.dds;*.jpg;*.jpeg;*.texture;*.bmp'}); }
  catch(e){ toast(errText(e)); return; }
  if(!r || !r.path) return;
  const ok = await api.post('/api/armory/allow_texture', {path: r.path}).catch(() => ({}));
  if(!ok.ok){ toast(tt('armory.not_an_image')); return; }
  a.textures = a.textures || {};
  a.textures[group] = r.path;
  armSave();
  const live = ARM.assets.get(key);
  if(live) armLoadSkin(a, live);
  armPaintAssets();
}

function armImage(url){
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => rej(new Error(url));
    img.src = url;
  });
}

/* An entry's skin is its main and attachment sheets glued side by side, the
   way the game lays them out and the viewer draws them (viewer3d.js). An
   external model's objects each have their own sheet. */
async function armLoadSkin(a, live){
  const gl = armGl();
  if(!gl || !live.view) return;
  if(a.kind === 'external'){
    live.objTex = live.objTex || {};
    for(const ob of live.view.objects){
      const file = armObjTexture(a, ob.index);
      if(!file){ live.objTex[ob.index] = null; continue; }
      try{
        await armAllow(file);
        const img = await armImage(armSheetUrl(file));
        live.objTex[ob.index] = armTexture(img, 1);
        (live.objImg = live.objImg || {})[ob.index] = img;
      }catch(e){ live.objTex[ob.index] = null; }
    }
    armFrame(); armThumbsPaint(true);
    return;
  }
  const mine = (live.view.skins || [])[a.skin || 0];
  live.tex = null; live.uScale = 0.5;
  // 100l: a sheet edited or swapped in the Textures tab stands in for the mod's
  const over = a.over || {};
  const skin = Object.assign({}, mine || {}, over.main ? {rel: over.main, exists: true} : {},
    over.attach ? {attach: over.attach, attach_exists: true} : {});
  if(!skin.exists){ armFrame(); return; }
  const url = rel => (rel === over.main || rel === over.attach) ? armSheetUrl(rel) : `/model_texture?mod=${enc(a.mod)}&rel=${enc(rel)}`;
  try{
    await armAllow(over.main); await armAllow(over.attach);
    const main = await armImage(url(skin.rel));
    const same = skin.attach && skin.attach.toLowerCase() === skin.rel.toLowerCase();
    let img = main;
    if(skin.attach && skin.attach_exists && !same){
      try{ img = v3Atlas(main, await armImage(url(skin.attach))); }catch(e){ img = main; }
    }else if(skin.attach && !same){
      live.uScale = 1.0;       // named and not here: the game repeats the main sheet
    }
    if(same) live.uScale = 1.0;
    live.tex = armTexture(img, live.uScale);
    live.img = img;
  }catch(e){ live.tex = null; }
  armFrame(); armThumbsPaint(true);
}

/* --- GL -------------------------------------------------------------------- */

function armGl(){
  if(ARM.gl && !ARM.gl.isContextLost()) return ARM.gl;
  const c = document.createElement('canvas');
  c.width = 640; c.height = 480;
  const gl = c.getContext('webgl', {antialias: true, alpha: false, preserveDrawingBuffer: true});
  if(!gl) return null;
  gl.getExtension('OES_standard_derivatives');
  c.addEventListener('webglcontextlost', e => { e.preventDefault(); });
  c.addEventListener('webglcontextrestored', () => {
    ARM.gl = null; armGl();
    for(const live of ARM.assets.values()){ live.buf = null; if(live.geo) armUpload(live); armLoadSkin(live.asset, live); }
    armFrame();
  });
  ARM.glCanvas = c; ARM.gl = gl;
  const sh = (type, src) => {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, ARM_VERT));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, ARM_FRAG));
  gl.linkProgram(p);
  ARM.prog = p;
  ARM.loc = {};
  for(const n of ['aPos', 'aNormal', 'aUv']) ARM.loc[n] = gl.getAttribLocation(p, n);
  for(const n of ['uProj', 'uView', 'uModel', 'uTex', 'uHasTex', 'uUScale', 'uHi', 'uSel', 'uFlip', 'uXray', 'uCrop', 'uNTex', 'uHasN',
                  'uCard', 'uMask', 'uLAmt', 'uAmb', 'uLevel', 'uPoint', 'uLDir', 'uLPos'])
    ARM.loc[n] = gl.getUniformLocation(p, n);
  gl.enable(gl.DEPTH_TEST);
  return gl;
}

function armUpload(live){
  const gl = armGl();
  if(!gl || !live.geo) return;
  const g = live.geo;
  const mk = (data, type) => { const b = gl.createBuffer(); gl.bindBuffer(type, b); gl.bufferData(type, data, gl.STATIC_DRAW); return b; };
  live.buf = {
    pos: mk(g.positions, gl.ARRAY_BUFFER),
    nrm: mk(g.normals || new Float32Array(g.vertices * 3), gl.ARRAY_BUFFER),
    uv: mk(g.uvs || new Float32Array(g.vertices * 2), gl.ARRAY_BUFFER),
    idx: mk(g.indices, gl.ELEMENT_ARRAY_BUFFER),
  };
}
function armFreeBuffers(live){
  const gl = ARM.gl;
  if(!gl || !live.buf) return;
  for(const b of Object.values(live.buf)) gl.deleteBuffer(b);
  live.buf = null;
}
function armTexture(img, uScale){
  const gl = armGl();
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  const pot = n => n > 0 && (n & (n - 1)) === 0;
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
  return t;
}

/* --- matrices -------------------------------------------------------------- */

function armMul(a, b){
  const o = new Array(16).fill(0);
  for(let c = 0; c < 4; c++) for(let r = 0; r < 4; r++){
    let s = 0;
    for(let k = 0; k < 4; k++) s += a[k*4 + r] * b[c*4 + k];
    o[c*4 + r] = s;
  }
  return o;
}
const armTrans = (x, y, z) => [1,0,0,0, 0,1,0,0, 0,0,1,0, x,y,z,1];
const armScale = (x, y, z) => [x,0,0,0, 0,y,0,0, 0,0,z,0, 0,0,0,1];
function armRot(rx, ry, rz){
  const d = Math.PI / 180;
  const [a, b, c] = [rx*d, ry*d, rz*d];
  const X = [1,0,0,0, 0,Math.cos(a),Math.sin(a),0, 0,-Math.sin(a),Math.cos(a),0, 0,0,0,1];
  const Y = [Math.cos(b),0,-Math.sin(b),0, 0,1,0,0, Math.sin(b),0,Math.cos(b),0, 0,0,0,1];
  const Z = [Math.cos(c),Math.sin(c),0,0, -Math.sin(c),Math.cos(c),0,0, 0,0,1,0, 0,0,0,1];
  return armMul(Z, armMul(Y, X));
}
/* An object's matrix in the game's own space: about its pivot, scale, then
   turn, then move. The page mirrors x once on top, as the viewer does. */
function armObjMatrix(o, pivot){
  const [px, py, pz] = pivot || [0, 0, 0];
  let m = armTrans(-px, -py, -pz);
  m = armMul(armScale(o.s[0], o.s[1], o.s[2]), m);
  m = armMul(armRot(o.r[0], o.r[1], o.r[2]), m);
  m = armMul(armTrans(px + o.t[0], py + o.t[1], pz + o.t[2]), m);
  return m;
}
const ARM_MIRROR = [-1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];

/* --- the viewport ---------------------------------------------------------- */

function armMountView(){
  const host = document.getElementById('armView');
  if(!host) return;
  if(!ARM.view){
    ARM.view = document.createElement('canvas');
    ARM.view.className = 'armcanvas';
    armInstallControls(ARM.view);
  }
  host.appendChild(ARM.view);
  if(typeof armViewWire === 'function') armViewWire();
  if(!ARM.resizeObs){
    ARM.resizeObs = new ResizeObserver(() => armFrame());
  }
  ARM.resizeObs.disconnect();
  ARM.resizeObs.observe(host);
}

function armFrame(){
  if(ARM.frameAsked) return;
  ARM.frameAsked = true;
  const go = () => { ARM.frameAsked = false; armDraw(); };
  // requestAnimationFrame never fires in a hidden tab (memory: two WebGL
  // traps); a draw asked for there waits for the tab to come back
  if(document.hidden){
    const back = () => { document.removeEventListener('visibilitychange', back); go(); };
    document.addEventListener('visibilitychange', back);
  }else requestAnimationFrame(go);
}

function armVisibleObjects(){
  // the detail view (armobj.js) shows its one object and nothing else
  if(ARM.detail) return armProj().objects.filter(o => o.id === ARM.detail.id);
  return armProj().objects.filter(o => !o.hidden && !armCollHidden(o));
}
function armCollHidden(o){
  if(!o.coll) return false;
  const c = armProj().collections.find(x => x.id === o.coll);
  return !!(c && c.hidden);
}

function armBounds(objs){
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for(const o of objs){
    const om = armObjMatrix(o, armPivot(o));
    for(const pc of o.src || []){
      const live = ARM.assets.get(pc.asset);
      if(!live || !live.geo) continue;
      const m = pc.xf ? armMul(om, pc.xf) : om;
      const P = live.geo.positions;
      armPieceEach(live, pc, v => {
        const x = P[v*3], y = P[v*3+1], z = P[v*3+2];
        const w = [m[0]*x + m[4]*y + m[8]*z + m[12], m[1]*x + m[5]*y + m[9]*z + m[13], m[2]*x + m[6]*y + m[10]*z + m[14]];
        for(let k = 0; k < 3; k++){ if(w[k] < lo[k]) lo[k] = w[k]; if(w[k] > hi[k]) hi[k] = w[k]; }
      }, 3);
    }
  }
  return lo[0] === Infinity ? null : [lo, hi];
}
function armFrameAll(){
  const b = armBounds(armVisibleObjects());
  if(b){
    const [lo, hi] = b;
    ARM.cam.target = [-(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    ARM.cam.dist = Math.max(0.5, Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) * 1.15);
  }
  armFrame();
}

function armCamera(aspect){
  const c = ARM.cam;
  const eye = [c.target[0] + c.dist * Math.cos(c.pitch) * Math.sin(c.yaw),
               c.target[1] + c.dist * Math.sin(c.pitch),
               c.target[2] + c.dist * Math.cos(c.pitch) * Math.cos(c.yaw)];
  return {proj: c.ortho ? armOrtho(c.dist, aspect) : v3Perspective(0.75, aspect, Math.max(0.01, c.dist / 200), c.dist * 20),
          view: v3LookAt(eye, c.target, [0, 1, 0]), eye};
}
function armOrtho(dist, aspect){
  const h = dist * 0.42, w = h * aspect, n = -dist * 20, f = dist * 20;
  return [1/w,0,0,0, 0,1/h,0,0, 0,0,-2/(f-n),0, 0,0,-(f+n)/(f-n),1];
}

/* Draws into the shared context, at `w` x `h`, the objects given. */
function armRender(objs, w, h, cam, opts){
  const gl = armGl();
  if(!gl) return false;
  const o = opts || {};
  if(ARM.glCanvas.width < w || ARM.glCanvas.height < h){
    ARM.glCanvas.width = Math.max(ARM.glCanvas.width, w);
    ARM.glCanvas.height = Math.max(ARM.glCanvas.height, h);
  }
  gl.viewport(0, ARM.glCanvas.height - h, w, h);
  gl.enable(gl.SCISSOR_TEST);
  gl.scissor(0, ARM.glCanvas.height - h, w, h);
  const bg = o.bg || [0.16, 0.18, 0.21];
  gl.clearColor(bg[0], bg[1], bg[2], 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.useProgram(ARM.prog);
  const L = ARM.loc;
  gl.uniformMatrix4fv(L.uProj, false, new Float32Array(cam.proj));
  gl.uniformMatrix4fv(L.uView, false, new Float32Array(cam.view));
  gl.uniform1f(L.uFlip, o.faceOrient ? -1 : 1);
  // the card maker's light (cardgen.js); the viewport's own otherwise
  const lt = o.light;
  gl.uniform1f(L.uCard, lt ? 1 : 0);
  gl.uniform1f(L.uMask, o.mask ? 1 : 0);
  if(lt){
    gl.uniform1f(L.uLAmt, lt.amount); gl.uniform1f(L.uAmb, lt.ambient); gl.uniform1f(L.uLevel, lt.level);
    gl.uniform1f(L.uPoint, lt.point ? 1 : 0);
    gl.uniform3fv(L.uLDir, lt.dir); gl.uniform3fv(L.uLPos, lt.pos || [0, 0, 0]);
  }
  if(!o.plain && ARM.xray){ gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); }
  const bindTex = (live, pc, ob) => {
    // a dyed object draws from its own crop of the sheet (armobj.js)
    const dyed = typeof armDyedTexture === 'function' ? armDyedTexture(ob, pc) : null;
    // 100l: an object wearing a sheet of its own (armtex.js)
    const own = !dyed && ob.sheet && typeof armSheetTex === 'function' ? armSheetTex(ob.sheet) : null;
    const tex = dyed ? dyed.tex : own ? own : live.objTex ? live.objTex[pc.group] : live.tex;
    gl.uniform1f(L.uHasTex, tex ? 1 : 0);
    // a dyed crop of a worn sheet is laid out as that sheet, one copy wide
    gl.uniform1f(L.uUScale, own || live.objTex || (dyed && ob.sheet) ? 1.0 : (live.uScale || 0.5));
    gl.uniform4fv(L.uCrop, dyed ? dyed.crop : [0, 0, 1, 1]);
    if(tex){ gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(L.uTex, 0); }
    const nTex = dyed && dyed.nTex && (!o.plain || o.card) ? dyed.nTex : null;
    gl.uniform1f(L.uHasN, nTex ? 1 : 0);
    if(nTex){ gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, nTex); gl.uniform1i(L.uNTex, 1); gl.activeTexture(gl.TEXTURE0); }
  };
  // the card maker's own move and turn of the whole model (99m), in the
  // game's space, under the page's mirror
  const top = o.pre ? armMul(ARM_MIRROR, o.pre) : ARM_MIRROR;
  for(const ob of objs){
    // posed by the animation previewer (armanim.js): already in the game's
    // space, its own move, turn and scale in it
    // a card (95m) is drawn plain, but posed
    const posed = (!o.plain || o.card) && typeof armAnimGeoFor === 'function' ? armAnimGeoFor(ob, o.card) : null;
    if(posed){
      gl.uniformMatrix4fv(L.uModel, false, new Float32Array(top));
      gl.uniform1f(L.uHi, !o.plain && ARM.hover === ob.id ? 1 : 0);
      gl.uniform1f(L.uSel, !o.plain && !ARM.dyeQuiet && ARM.sel.has(ob.id) ? 1 : 0);
      gl.uniform1f(L.uXray, !o.plain && ARM.xray ? 1 : 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, posed.glPos);
      gl.enableVertexAttribArray(L.aPos); gl.vertexAttribPointer(L.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, posed.glNrm);
      gl.enableVertexAttribArray(L.aNormal); gl.vertexAttribPointer(L.aNormal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, posed.glUv);
      gl.enableVertexAttribArray(L.aUv); gl.vertexAttribPointer(L.aUv, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, posed.glIdx);
      for(const r of posed.ranges){
        const live = ARM.assets.get(r.pc.asset);
        if(!live) continue;
        bindTex(live, r.pc, ob);
        gl.drawElements(gl.TRIANGLES, r.count, gl.UNSIGNED_SHORT, r.start * 2);
      }
      continue;
    }
    const om = armMul(top, armObjMatrix(ob, armPivot(ob)));
    for(const pc of ob.src || []){
      const live = ARM.assets.get(pc.asset);
      if(!live || !live.buf || !live.geo) continue;
      const g = live.geo.groups[pc.group];
      if(!g) continue;
      gl.uniformMatrix4fv(L.uModel, false, new Float32Array(pc.xf ? armMul(om, pc.xf) : om));
      bindTex(live, pc, ob);
      gl.uniform1f(L.uHi, !o.plain && ARM.hover === ob.id ? 1 : 0);
      gl.uniform1f(L.uSel, !o.plain && !ARM.dyeQuiet && ARM.sel.has(ob.id) ? 1 : 0);
      gl.uniform1f(L.uXray, !o.plain && ARM.xray ? 1 : 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, live.buf.pos);
      gl.enableVertexAttribArray(L.aPos); gl.vertexAttribPointer(L.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, pc.nrm ? armNrmBuffer(live, pc) : live.buf.nrm);
      gl.enableVertexAttribArray(L.aNormal); gl.vertexAttribPointer(L.aNormal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, pc.uv && typeof armUvBuffer === 'function' ? armUvBuffer(live, pc) : live.buf.uv);
      gl.enableVertexAttribArray(L.aUv); gl.vertexAttribPointer(L.aUv, 2, gl.FLOAT, false, 0, 0);
      if(pc.tris || pc.weld || pc.flip){
        const sub = armPieceBuffer(live, pc);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, sub.buf);
        gl.drawElements(gl.TRIANGLES, sub.count, gl.UNSIGNED_SHORT, 0);
      }else{
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, live.buf.idx);
        gl.drawElements(gl.TRIANGLES, g.count, gl.UNSIGNED_SHORT, g.start * 2);
      }
    }
  }
  gl.disable(gl.SCISSOR_TEST);
  gl.disable(gl.BLEND); gl.depthMask(true);
  return true;
}

function armDraw(){
  const view = ARM.view;
  if(!view || !view.isConnected || state.mode !== 'armory') return;
  const r = view.parentElement.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(64, Math.round(r.width * dpr)), h = Math.max(64, Math.round(r.height * dpr));
  if(view.width !== w || view.height !== h){ view.width = w; view.height = h; }
  const cam = armCamera(w / h);
  if(typeof armAnimPose === 'function') armAnimPose();
  if(!armRender(armVisibleObjects(), w, h, cam, {faceOrient: ARM.faceOrient})) return;
  const ctx = view.getContext('2d');
  ctx.drawImage(ARM.glCanvas, 0, 0, w, h, 0, 0, w, h);
  if(typeof armOverlay === 'function') armOverlay(ctx, w, h, cam);
}

/* --- thumbnails ------------------------------------------------------------ */

function armThumbsPaint(fresh){
  if(fresh) ARM.thumbs.clear();
  const imgs = document.querySelectorAll('img.armthumb[data-thumb]');
  if(!imgs.length) return;
  const S = 128;
  for(const img of imgs){
    const k = img.dataset.thumb;
    if(ARM.thumbs.has(k)){ img.src = ARM.thumbs.get(k); continue; }
    const cut = k.lastIndexOf('|');
    const key = k.slice(0, cut), group = +k.slice(cut + 1);
    const live = ARM.assets.get(key);
    if(!live || !live.geo || !live.buf) continue;
    const ob = {id: -1, src: [{asset: key, group}], t: [0,0,0], r: [0,0,0], s: [1,1,1]};
    const b = armBounds([ob]);
    if(!b) continue;
    const [lo, hi] = b;
    const target = [-(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    const dist = Math.max(0.05, Math.hypot(hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]) * 1.1);
    const eye = [target[0] + dist * 0.55, target[1] + dist * 0.25, target[2] + dist * 0.8];
    const cam = {proj: v3Perspective(0.75, 1, dist / 100, dist * 10), view: v3LookAt(eye, target, [0, 1, 0])};
    if(!armRender([ob], S, S, cam, {plain: true, bg: [0.21, 0.24, 0.28]})) return;
    const c = document.createElement('canvas'); c.width = c.height = S;
    c.getContext('2d').drawImage(ARM.glCanvas, 0, 0, S, S, 0, 0, S, S);
    const url = c.toDataURL('image/jpeg', 0.82);
    ARM.thumbs.set(k, url);
    img.src = url;
  }
  armFrame();
}

/* --- viewport controls (95g makes them Blender's) -------------------------- */

/* Blender's mouse (95g): middle drag orbits, Shift+middle pans, Ctrl+middle
   zooms, the wheel zooms; left click selects and left drag draws a box.
   Alt+left stands in for the middle button on a mouse or pad without one.
   A G, R or S under way (armview.js) takes the mouse while it lasts. */
function armInstallControls(c){
  let drag = null;
  c.tabIndex = 0;
  c.addEventListener('pointerdown', e => {
    c.focus({preventScroll: true});
    if(typeof armPointerDown === 'function' && armPointerDown(e)) return;
    // the view gizmo (99k): a left drag on it orbits, a click looks down an axis
    const giz = e.button === 0 && typeof armGizmoHit === 'function' ? armGizmoHit(e) : null;
    const button = giz || (e.button === 0 && e.altKey) ? 1 : e.button;
    drag = {x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, button, moved: false, giz};
    c.setPointerCapture(e.pointerId);
    if(button === 1) e.preventDefault();
  });
  c.addEventListener('pointermove', e => {
    if(typeof armXformMove === 'function' && armXformMove(e)) return;
    if(!drag){
      if(typeof armGizmoHover === 'function' && armGizmoHover(e)){ if(typeof armHoverAt === 'function') armHoverAt(null); return; }
      if(typeof armHoverAt === 'function') armHoverAt(e);
      return;
    }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if(Math.abs(e.clientX - drag.x0) + Math.abs(e.clientY - drag.y0) > 3) drag.moved = true;
    drag.x = e.clientX; drag.y = e.clientY;
    if(drag.button === 0){ if(typeof armBoxDrag === 'function') armBoxDrag(drag, e); return; }
    if(!drag.moved) return;
    if(drag.button === 1 && e.shiftKey && !drag.giz) armPan(dx, dy);
    else if(drag.button === 1 && e.ctrlKey) ARM.cam.dist = Math.max(0.05, ARM.cam.dist * Math.exp(dy * 0.01));
    else if(drag.button === 1){
      ARM.cam.yaw -= dx * 0.01;
      ARM.cam.pitch = Math.max(-1.5, Math.min(1.5, ARM.cam.pitch + dy * 0.01));
    }
    armFrame();
  });
  c.addEventListener('pointerup', e => {
    const d = drag; drag = null;
    if(!d) return;
    if(d.giz){ if(!d.moved) armGizmoClick(d.giz); return; }
    if(d.box && typeof armBoxEnd === 'function'){ armBoxEnd(d, e); return; }
    if(!d.moved && d.button === 0 && typeof armClick === 'function') armClick(e);
  });
  c.addEventListener('pointerleave', () => {
    if(typeof armHoverAt === 'function') armHoverAt(null);
    if(ARM.gizmoHover){ ARM.gizmoHover = null; armFrame(); }
  });
  c.addEventListener('contextmenu', e => e.preventDefault());
  c.addEventListener('auxclick', e => e.preventDefault());
  c.addEventListener('keydown', e => { if(typeof armKey === 'function') armKey(e); });
  c.addEventListener('wheel', e => {
    e.preventDefault();
    ARM.cam.dist = Math.max(0.05, ARM.cam.dist * Math.exp(e.deltaY * 0.0012));
    armFrame();
  }, {passive: false});
}
function armPan(dx, dy){
  const c = ARM.cam;
  const k = c.dist * 0.0016;
  const right = [Math.cos(c.yaw), 0, -Math.sin(c.yaw)];
  const up = [-Math.sin(c.pitch) * Math.sin(c.yaw), Math.cos(c.pitch), -Math.sin(c.pitch) * Math.cos(c.yaw)];
  for(let i = 0; i < 3; i++) c.target[i] += (-dx * right[i] + dy * up[i]) * k;
}

/* --- the import dialog ----------------------------------------------------- */

async function armImportOpen(){
  state.armImp = state.armImp || {tab: 'mod', mod: state.src, by: 'units', q: '', picked: new Set(), path: ''};
  const imp = state.armImp;
  if(!imp.picked) imp.picked = new Set();
  if(!ARM.mods){
    try{ ARM.mods = (await api.get('/api/mods')).map(m => m.name); }catch(e){ ARM.mods = [state.src]; }
  }
  armImportPaint();
  overlay.classList.add('open');
  if(imp.tab === 'mod') armImportCatalogue();
}

function armImportPaint(){
  const imp = state.armImp;
  document.getElementById('modal').className = 'modal wide';
  modal.innerHTML = `<div class="armimp">
    <h3>${tt('armory.import_title')}</h3>
    <div class="mftabs">
      <button class="mftab${imp.tab === 'mod' ? ' on' : ''}" onclick="armImportTab('mod')">${tt('armory.from_a_mod')}</button>
      <button class="mftab${imp.tab === 'file' ? ' on' : ''}" onclick="armImportTab('file')">${tt('armory.from_a_file')}</button>
      <button class="mftab${imp.tab === 'library' ? ' on' : ''}" onclick="armImportTab('library')">${tt('armory.from_the_library')}</button>
      ${imp.tab === 'file' ? '' : `<span style="flex:1"></span>
        <button class="mini${armImpGallery() ? '' : ' on'}" onclick="armImportView('list')">${tt('armory.as_list')}</button>
        <button class="mini${armImpGallery() ? ' on' : ''}" onclick="armImportView('gallery')">${tt('armory.as_gallery')}</button>`}
    </div>
    <div id="armImpBody">${armImportBodyHtml()}</div>
    <div class="armimpfoot">
      <span class="count" id="armImpCount"></span><span style="flex:1"></span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button class="primary" id="armImpGo" onclick="armImportGo()">${tt('armory.import')}</button>
    </div></div>`;
  armImportCount();
  armImpLibMount();
}
function armImportTab(t){ state.armImp.tab = t; armImportPaint(); if(t === 'mod') armImportCatalogue(); }

/* 99g: the dialog's lists as a List or a Gallery, as the Model entries tab
   has them: the gallery's tiles are 95a's (gallery.js), one WebGL context and
   only the tiles on screen fetched. A click on a tile picks it. Remembered. */
// 100j: the gallery is the default, under a new key so a List saved while
// List was the default does not hold it; a choice made since is kept
const armImpGallery = () => (state.settings || {}).armory_import_view2 !== 'list';
function armImportView(v){
  state.settings.armory_import_view2 = v;
  api.post('/api/settings', {armory_import_view2: v}).catch(() => {});
  armImportPaint();
  if(state.armImp.tab === 'mod') armImportRows();
}
function armImpTileHtml(k, mod, name, label, on, missing){
  if(missing) return `<div class="gtile gmissing" title="${esc(tt('armory.model_missing'))}"><canvas></canvas><span class="gname">${label}</span></div>`;
  return `<div class="gtile armimptile${on ? ' picked' : ''}" data-name="${esc(name)}" data-mod="${esc(mod)}" data-k="${esc(k)}" title="${esc(name)}">
    <canvas></canvas><span class="gname">${label}</span><span class="armimptick">✓</span>
    <button class="mini armimplook" onclick="event.stopPropagation();armImpLook('${esc(mod)}','${esc(name)}')" title="${esc(tt('armory.look_closer_title'))}">🔍</button></div>`;
}
/* 100j: a closer look before it is pulled in: the Models Editor's viewer over
   the dialog (orbit, zoom, skins, variations, animations), the dialog back
   live when it closes */
async function armImpLook(mod, name){
  // the list comes back where it was, not at its top (the tester's notes)
  const rows = document.getElementById('armImpRows'), top = rows ? rows.scrollTop : 0;
  const go = v3Open(mod, name);
  if(v3Back) v3Back.after = () => {
    armImportPaint();
    if(state.armImp.tab === 'mod') armImportRows();
    const el = document.getElementById('armImpRows');
    if(el) el.scrollTop = top;
  };
  await go;
}
function armImpTilePick(t, set, after){
  const k = t.dataset.k, on = !set.has(k);
  if(on) set.add(k); else set.delete(k);
  t.classList.toggle('picked', on);
  if(after) after();
  armImportCount();
}
function armImpLibMount(){
  const el = document.getElementById('armLibPick');
  if(!el || !armImpGallery() || state.armImp.tab !== 'library' || typeof galMount !== 'function') return;
  galMount(el, (name, t) => armLibTileToggle(t));
}
function armLibTileToggle(t){
  const s = state.armImp.libPicked, id = +t.dataset.k;
  if(s.has(id)) s.delete(id); else s.add(id);
  t.classList.toggle('picked', s.has(id));
  armImportCount();
}

function armImportBodyHtml(){
  const imp = state.armImp;
  if(imp.tab === 'file')
    return `<div class="count" style="margin:8px 0">${tt('armory.file_intro')}</div>
      <div class="armpathrow"><input id="armImpPath" value="${esc(imp.path || '')}" placeholder="${esc(tt('armory.file_placeholder'))}"
        oninput="state.armImp.path=this.value">
      <button onclick="armImportBrowse()">${tt('armory.browse')}</button></div>`;
  if(imp.tab === 'library')
    return `<div id="armLibPick">${typeof armLibPickHtml === 'function' ? armLibPickHtml() : ''}</div>`;
  return `<div class="armimpctl">
      <select onchange="state.armImp.mod=this.value;state.armImp.picked.clear();armImportCatalogue()">${(ARM.mods || []).map(m =>
        `<option${m === imp.mod ? ' selected' : ''}>${esc(m)}</option>`).join('')}</select>
      <button class="mini${imp.by === 'units' ? ' on' : ''}" onclick="state.armImp.by='units';armImportRows()">${tt('armory.units')}</button>
      <button class="mini${imp.by === 'entries' ? ' on' : ''}" onclick="state.armImp.by='entries';armImportRows()">${tt('armory.model_entries')}</button>
      <input id="armImpQ" placeholder="${esc(tt('armory.find'))}" value="${esc(imp.q)}" oninput="state.armImp.q=this.value;armImportRows()">
    </div>
    <div class="armimpctl armimpfilt" id="armImpFilt">${armImpFiltHtml()}</div>
    <div class="armimprows" id="armImpRows"><div class="count">${tt('armory.reading')}</div></div>`;
}

async function armImportCatalogue(){
  const imp = state.armImp;
  const mod = imp.mod;
  if(!ARM.catalogue[mod]){
    try{ ARM.catalogue[mod] = await api.get('/api/armory/catalogue?mod=' + enc(mod)); }
    catch(e){ const el = document.getElementById('armImpRows'); if(el) el.innerHTML = `<div class="w-bad">${esc(errText(e))}</div>`; return; }
  }
  if(state.armImp.mod !== mod) return;
  const f = document.getElementById('armImpFilt');
  if(f) f.innerHTML = armImpFiltHtml();
  armImportRows();
}

/* 100j: faction, category, class and culture, out of the units in the
   catalogue; an entry passes when a unit that passes uses it */
const ARM_IMP_FILTERS = [['fac', 'factions', 'armory.filter_faction'], ['cat', 'category', 'armory.filter_category'],
  ['cls', 'class', 'armory.filter_class'], ['cul', 'cultures', 'armory.filter_culture']];
function armImpFiltHtml(){
  const imp = state.armImp, cat = ARM.catalogue[imp.mod];
  imp.filt = imp.filt || {};
  if(!cat) return '';
  return ARM_IMP_FILTERS.map(([k, field, label]) => {
    const vals = new Set();
    for(const u of cat.units) [].concat(u[field] || []).forEach(v => v && vals.add(v));
    if(imp.filt[k] && !vals.has(imp.filt[k])) imp.filt[k] = '';
    const name = v => k === 'fac' && typeof facLabel === 'function' ? facLabel(v) : v;
    return `<select title="${esc(tt(label))}" onchange="state.armImp.filt.${k}=this.value;armImportRows()">
      <option value="">${tt(label)}: ${tt('armory.filter_any')}</option>${[...vals].sort((a, b) => name(a).localeCompare(name(b))).map(v =>
      `<option value="${esc(v)}"${imp.filt[k] === v ? ' selected' : ''}>${esc(name(v))}</option>`).join('')}</select>`;
  }).join('') + `<button class="mini" onclick="state.armImp.filt={};document.getElementById('armImpFilt').innerHTML=armImpFiltHtml();armImportRows()">${tt('armory.filter_clear')}</button>`;
}
function armImpUnitOk(u){
  const f = state.armImp.filt || {};
  return ARM_IMP_FILTERS.every(([k, field]) => !f[k] || [].concat(u[field] || []).includes(f[k]));
}
function armImpFiltering(){ const f = state.armImp.filt || {}; return ARM_IMP_FILTERS.some(([k]) => f[k]); }

/* Repaints the rows under the Find box only, never the box (memory: never
   repaint the box being typed in). */
function armImportRows(){
  const el = document.getElementById('armImpRows');
  const imp = state.armImp;
  const cat = ARM.catalogue[imp.mod];
  if(!el || !cat) return;
  document.querySelectorAll('.armimpctl .mini').forEach((b, i) => b.classList.toggle('on', (i === 0) === (imp.by === 'units')));
  const q = imp.q.trim().toLowerCase();
  const CAP = 300;
  const filtering = armImpFiltering();
  let usedBy = null;
  if(filtering){
    usedBy = new Set();
    for(const u of cat.units) if(armImpUnitOk(u)) u.models.forEach(m => usedBy.add(m.name));
  }
  const lookBtn = name => `<button class="mini armimplook" onclick="event.preventDefault();event.stopPropagation();armImpLook('${esc(imp.mod)}','${esc(name)}')" title="${esc(tt('armory.look_closer_title'))}">🔍</button>`;
  let html = '', shown = 0, total = 0;
  const tiles = armImpGallery();
  const roleOf = (m) => m.role === 'soldier' ? tt('armory.role_soldier') : m.role === 'officer'
    ? tt('armory.role_officer', {n: m.n}) : tt('armory.role_upgrade', {n: m.n});
  if(tiles && imp.by === 'units'){
    for(const u of cat.units){
      if(q && !u.type.toLowerCase().includes(q) && !u.models.some(m => m.name.includes(q))) continue;
      if(filtering && !armImpUnitOk(u)) continue;
      total++;
      if(shown >= CAP) continue;
      shown++;
      html += `<div class="gunit"><div class="gulabel"><b>${esc(u.type)}</b>
          <span class="count">${esc([u.category, u.class, u.mount].filter(Boolean).join(' · '))}</span></div>
        <div class="gurow">${u.models.map(m => { const k = `${imp.mod}|${m.name}|${u.type}`;
          return armImpTileHtml(k, imp.mod, m.name, `<b>${esc(roleOf(m))}</b> ${esc(m.name)}`, imp.picked.has(k), m.missing); }).join('')}</div></div>`;
    }
  }else if(tiles){
    let row = '';
    for(const e of cat.entries){
      if(q && !e.name.toLowerCase().includes(q) && !e.mesh.toLowerCase().includes(q)) continue;
      if(usedBy && !usedBy.has(e.name.toLowerCase())) continue;
      total++;
      if(shown >= CAP) continue;
      shown++;
      const k = `${imp.mod}|${e.name}|`;
      row += armImpTileHtml(k, imp.mod, e.name, esc(e.name), imp.picked.has(k));
    }
    html = row ? `<div class="galgrid">${row}</div>` : '';
  }else if(imp.by === 'units'){
    for(const u of cat.units){
      if(q && !u.type.toLowerCase().includes(q) && !u.models.some(m => m.name.includes(q))) continue;
      if(filtering && !armImpUnitOk(u)) continue;
      total++;
      if(shown >= CAP) continue;
      shown++;
      html += `<div class="armimprow"><span class="armimpunit"><b>${esc(u.type)}</b>
        <span class="count">${esc([u.category, u.class, u.mount].filter(Boolean).join(' · '))}</span></span>
        <span class="armchips">${u.models.map(m => {
          const k = `${imp.mod}|${m.name}|${u.type}`;
          const role = m.role === 'soldier' ? tt('armory.role_soldier') : m.role === 'officer'
            ? tt('armory.role_officer', {n: m.n}) : tt('armory.role_upgrade', {n: m.n});
          return m.missing ? `<span class="armchip off" title="${esc(tt('armory.model_missing'))}">${esc(role)}: ${esc(m.name)}</span>`
            : `<label class="armchip${imp.picked.has(k) ? ' on' : ''}"><input type="checkbox"${imp.picked.has(k) ? ' checked' : ''}
                onchange="armImportPick('${esc(k)}', this.checked, this)"> ${esc(role)}: ${esc(m.name)}</label>${lookBtn(m.name)}`;
        }).join('')}</span></div>`;
    }
  }else{
    for(const e of cat.entries){
      if(q && !e.name.toLowerCase().includes(q) && !e.mesh.toLowerCase().includes(q)) continue;
      if(usedBy && !usedBy.has(e.name.toLowerCase())) continue;
      total++;
      if(shown >= CAP) continue;
      shown++;
      const k = `${imp.mod}|${e.name}|`;
      html += `<label class="armimprow"><input type="checkbox"${imp.picked.has(k) ? ' checked' : ''}
          onchange="armImportPick('${esc(k)}', this.checked)">
        <b>${esc(e.name)}</b> <span class="count">${esc(e.mesh)} · ${esc(e.skeletons.join(', '))}</span>${lookBtn(e.name)}</label>`;
    }
  }
  if(total > shown) html += `<div class="count">${ttN('armory.more_rows', total - shown)}</div>`;
  el.innerHTML = html || `<div class="count">${tt('armory.nothing_matches')}</div>`;
  el.classList.toggle('armimpgal', tiles);
  if(tiles && typeof galMount === 'function') galMount(el, (name, t) => armImpTilePick(t, imp.picked), imp.mod);
}
function armImportPick(k, on, input){
  const imp = state.armImp;
  if(on) imp.picked.add(k); else imp.picked.delete(k);
  if(input && input.parentElement) input.parentElement.classList.toggle('on', on);
  armImportCount();
}
function armImportCount(){
  const el = document.getElementById('armImpCount');
  if(el && state.armImp.tab === 'mod') el.textContent = ttN('armory.n_picked', state.armImp.picked.size);
  else if(el && state.armImp.tab === 'library') el.textContent = ttN('armory.n_picked', (state.armImp.libPicked || new Set()).size);
  else if(el) el.textContent = '';
}

async function armImportBrowse(){
  let r;
  try{ r = await api.post('/api/browse_file', {title: tt('armory.file_title'),
    filter: 'Models|*.obj;*.glb;*.gltf;*.dae;*.mesh'}); }
  catch(e){ toast(errText(e)); return; }
  if(r && r.path){
    state.armImp.path = r.path;
    const el = document.getElementById('armImpPath');
    if(el) el.value = r.path;
  }
}

async function armImportGo(){
  const imp = state.armImp, p = armProj();
  const adds = [];
  if(imp.tab === 'file'){
    if(!(imp.path || '').trim()){ toast(tt('armory.file_first')); return; }
    adds.push({kind: 'external', path: imp.path.trim()});
  }else if(imp.tab === 'library'){
    if(typeof armLibPicked === 'function') adds.push(...armLibPicked());
  }else{
    for(const k of imp.picked){
      const [mod, entry, unit] = k.split('|');
      adds.push({kind: 'entry', mod, entry, unit: unit || ''});
    }
  }
  if(!adds.length){ toast(tt('armory.pick_something')); return; }
  const btn = document.getElementById('armImpGo');
  if(btn) btn.disabled = true;
  const said = [];
  let added = 0;
  for(const a of adds){
    const key = armAssetKey(a);
    if(p.assets.some(x => armAssetKey(x) === key)){
      said.push(tt('armory.already_loaded', {name: armAssetLabel(a)}));
      continue;
    }
    const live = await armLoadAsset(a);
    if(live.err){ ARM.assets.delete(key); said.push(`${armAssetLabel(a)}: ${live.err}`); continue; }
    // the same file under another name (an entry that points at a mesh
    // another loaded entry uses, or a model copied into a second mod)
    const twin = p.assets.find(x => { const l = ARM.assets.get(armAssetKey(x)); return l && l.view && l.view.file_hash === live.view.file_hash; });
    if(twin){
      ARM.assets.delete(key);
      said.push(tt('armory.same_file_as', {name: armAssetLabel(a), other: armAssetLabel(twin)}));
      continue;
    }
    a.open = p.assets.length < 3;
    p.assets.push(a);
    added++;
  }
  imp.picked.clear();
  armSave();
  closeModal();
  if(said.length) toast(said.join(' · '), 6000);
  if(added && !p.objects.length && p.base == null) armStartChooser();
  else renderArmory();
}

/* After the first import into an empty project: which loaded model to start
   from, its every object pulled in, or nothing at all. */
function armStartChooser(){
  const p = armProj();
  document.getElementById('modal').className = 'modal';
  modal.innerHTML = `<div style="padding:16px">
    <h3>${tt('armory.start_from')}</h3>
    <div class="count" style="margin-bottom:10px">${tt('armory.start_from_intro')}</div>
    ${p.assets.map(a => `<label class="armimprow"><input type="radio" name="armBase" value="${esc(armAssetKey(a))}">
      ${esc(armAssetLabel(a))} <span class="count">${esc(a.kind === 'external' ? a.path : a.mod)}</span></label>`).join('')}
    <label class="armimprow"><input type="radio" name="armBase" value="" checked> ${tt('armory.start_from_scratch')}</label>
    <div style="text-align:right;margin-top:12px"><button class="primary" onclick="armStartGo()">${tt('armory.start')}</button></div>
  </div>`;
  overlay.classList.add('open');
}
function armStartGo(){
  const pick = document.querySelector('input[name=armBase]:checked');
  const key = pick ? pick.value : '';
  const p = armProj();
  p.base = key || null;
  closeModal();
  if(key) armPullAll(key);
  renderArmory();
  armFrameAll();
}
