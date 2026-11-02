/* =========================================================================
   Unit cards, Generate (Phase 95m): the card maker

   The Unit cards tab is in two: GENERATE, this, and CLEAN UP, the menu that
   was there (cards.js). The maker follows the Blender kit's card procedure
   (tasks/card_renderer.py) on the model Armory Studio holds:

     1. POSE  - a preset (T-pose, guard, spear brace, archer draw, riding,
                march), each a frame of the real animation of that name, or
                any animation stopped at any point;
     2. LIGHT - one lamp, a sun or a point, its direction, amount, level and
                an ambient;
     3. RENDER at 10x the card's size (up to 40x), orthographic, from a
                camera that stays put; a second pass draws the silhouette,
                from which the black outline is drawn (0.30 card pixels);
     4. SCALE DOWN through a blur, then colour (exposure, brightness,
                contrast, gamma, saturation, hue) and a sharpen.

   99n adds the Blender kit's IK rig and pose library (cgrig.js): its
   controllers drawn over the HD view and dragged with the mouse, its poses
   browsed by catalog and applied whole or by body part. 99m gives the HD
   view the viewport's mouse and keys: the middle button orbits (Shift pans,
   Ctrl or the wheel zooms), G and R move and turn the model in the frame,
   X, Y or Z holding them to an axis.

   The HD render is beside the controls, the finished pixel card beside it. Cards are 48x64, 68x90 (large) or 180x230 (info), or a size of the
   user's. Saving writes a .tga (and a .png) under config/armory/cards/, and
   Give to a unit hands it to the unit editor's own card import, which copies
   it to every owning faction's folder through the edit door.
   ========================================================================= */

const CG_SIZES = {card: [48, 64], large: [68, 90], info: [180, 230]};
const CG_POSES = [
  {id: 'tpose', acts: []},
  {id: 'guard', acts: ['stand_a_idle', 'stand_idle', 'idle'], f: 0.3},
  {id: 'brace', acts: ['ready', 'ready_hf_idle_1'], f: 0.3},
  {id: 'draw', acts: ['attack_missile_hold', 'attack_missile_ready'], f: 0.5},
  {id: 'riding', acts: ['stand_a_idle', 'ready'], f: 0.3, skel: /(^|_)hr_|mounted|cav|horse/i},
  {id: 'march', acts: ['walk', 'march'], f: 0.25},
];

function cg(){
  return state.cg = state.cg || {
    size: 'card', mult: 1, w: 48, h: 64, ss: 10, oneEach: true, pose: 'guard', name: '', unit: '', err: '', saved: null,
    cam: {yaw: 20, pitch: 4, scale: 1.2, height: 0, pan: 0},
    xf: {t: [0, 0, 0], r: [0, 0, 0]},
    rig: {type: 'auto', basis: {}, handles: true, cat: '', pick: '', part: 'whole'},
    light: {type: 'sun', azimuth: 35, elevation: 40, amount: 0.95, level: 1.0, ambient: 0.38},
    post: {blur: 0.5, exposure: 0, brightness: 0, contrast: 1.0, gamma: 1.0, saturation: 1.0, hue: 0, sharpen: 0.2, outline: 0.3,
           painted: false},
  };
}
// 96f: a standard size can be made two to four times bigger, for sharper cards
function cgDims(){ const c = cg(); return c.size === 'custom' ? [Math.max(8, c.w | 0), Math.max(8, c.h | 0)]
  : CG_SIZES[c.size].map(v => v * (c.mult || 1)); }

/* What is drawn: the model's visible objects, one of each group type (the
   first, as the game would choose one variant per soldier) unless all. */
function cgObjects(){
  const objs = armProj().objects.filter(o => !o.hidden && !armCollHidden(o));
  if(!cg().oneEach) return objs;
  const seen = new Set();
  return objs.filter(o => { const k = (o.name || '').toLowerCase(); if(seen.has(k)) return false; seen.add(k); return true; });
}

/* --- the tab ----------------------------------------------------------------- */

const cgSizeLabel = s => ({card: tt('cards.gen_size_card'), large: tt('cards.gen_size_large'), info: tt('cards.gen_size_info'),
  custom: tt('cards.gen_size_custom')})[s] || s;
const cgLightLabel = t => t === 'point' ? tt('cards.gen_light_point') : tt('cards.gen_light_sun');
const cgPoseLabel = id => ({tpose: tt('cards.gen_pose_tpose'), guard: tt('cards.gen_pose_guard'), brace: tt('cards.gen_pose_brace'),
  draw: tt('cards.gen_pose_draw'), riding: tt('cards.gen_pose_riding'), march: tt('cards.gen_pose_march'),
  anim: tt('cards.gen_pose_anim'), rig: tt('cards.gen_pose_rig')})[id] || id;

async function renderCardGen(){
  await armEnsureLoaded();
  if(ARM.loading) await ARM.loading;
  const st = cg();
  // a maker state from before 99m/99n gets what it lacks
  st.cam.pan = st.cam.pan || 0;
  st.xf = st.xf || {t: [0, 0, 0], r: [0, 0, 0]};
  st.rig = st.rig || {type: 'auto', basis: {}, handles: true, cat: '', pick: '', part: 'whole'};
  if(state.mode !== 'cards' || (state.cardsSub || 'generate') !== 'generate') return;
  const c = cg(), [w, h] = cgDims();
  const sl = (path, key, min, max, step, label) => {
    const v = c[path][key];
    return `<label class="cgrange">${label}<input type="range" min="${min}" max="${max}" step="${step}" value="${v}"
      oninput="cgSet('${path}','${key}',+this.value)"><span class="count" id="cgv_${path}_${key}">${(+v).toFixed(step < 1 ? 2 : 0)}</span></label>`;
  };
  const objs = cgObjects();
  const a = armAnim(), entries = armAnimEntries();
  const sk = a.list && a.list.skeletons ? a.list.skeletons[(a.skel || '').toLowerCase()] : null;
  const actions = sk ? (sk.actions || []).filter(r => r.playable) : [];
  main.innerHTML = bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit')) + cardsSubTabsHtml() + `
    <div class="cggrid">
      <div class="cgctl">
        ${objs.length ? `<div class="count">${ttN('cards.gen_source', objs.length)}
            <label class="armcheck"><input type="checkbox"${c.oneEach ? ' checked' : ''} onchange="cg().oneEach=this.checked;cgRepaint()"> ${tt('cards.gen_one_each')}</label></div>`
          : `<div class="empty armempty">${tt('cards.gen_no_model')} <button class="mini" onclick="setAppMode('armory')">${tt('core.armory_studio')}</button></div>`}
        <fieldset><legend>${tt('cards.gen_size')}</legend>
          <div class="armexprow">${['card', 'large', 'info', 'custom'].map(s => `<label class="armcheck"><input type="radio" name="cgSize"${c.size === s ? ' checked' : ''}
              onchange="cg().size='${s}';cgRepaint()"> ${cgSizeLabel(s)}${s !== 'custom' ? ` <span class="count">${CG_SIZES[s].join('×')}</span>` : ''}</label>`).join('')}</div>
          ${c.size !== 'custom' ? `<div class="armexprow"><label>${tt('cards.gen_bigger')} <select onchange="cg().mult=+this.value;cgRepaint()">${
            [1, 2, 3, 4].map(m => `<option value="${m}"${(c.mult || 1) === m ? ' selected' : ''}>${m === 1 ? tt('cards.gen_mod_size') : m + '×'}</option>`).join('')}</select></label></div>` : ''}
          ${c.size === 'custom' ? `<div class="armexprow"><input type="number" class="armnum" value="${c.w}" onchange="cg().w=+this.value;cgRepaint()"> ×
            <input type="number" class="armnum" value="${c.h}" onchange="cg().h=+this.value;cgRepaint()"></div>` : ''}
          <label class="cgrange">${tt('cards.gen_render_at')}<input type="range" min="10" max="40" step="5" value="${c.ss}" onchange="cg().ss=+this.value;cgRepaint()"><span class="count">${c.ss}×</span></label>
        </fieldset>
        <fieldset><legend>${tt('cards.gen_pose')}</legend>
          <div class="armexprow">${CG_POSES.concat([{id: 'anim'}, {id: 'rig'}]).map(p => `<button class="mini${c.pose === p.id ? ' on' : ''}" onclick="cgPose('${p.id}')">${cgPoseLabel(p.id)}</button>`).join('')}</div>
          <div class="armexprow"><label>${tt('armory.skeleton_of')}<select onchange="cgAnimFrom(this.value)">
              <option value="">${tt('cards.gen_pick_entry')}</option>${entries.map(x => `<option value="${esc(armAssetKey(x))}"${(armProj().anim || {}).asset === armAssetKey(x) ? ' selected' : ''}>${esc(armAssetLabel(x))}</option>`).join('')}</select></label>
            ${a.list && a.list.skeletons ? `<select onchange="armAnimSkel(this.value);cgRepaint()">${Object.keys(a.list.skeletons).map(s => `<option${s === (a.skel || '').toLowerCase() ? ' selected' : ''}>${esc(s)}</option>`).join('')}</select>` : ''}</div>
          ${c.pose === 'anim' && actions.length ? `<div class="armexprow"><select onchange="cgAnimPick(this.value)">${actions.map(r => {
              const k = r.slot != null ? String(r.slot) : 'a:' + r.action;
              return `<option value="${esc(k)}"${a.key === k ? ' selected' : ''}>${esc(r.action)}</option>`; }).join('')}</select>
            <input type="range" min="0" max="1000" value="${armAnimFrac()}" oninput="cgScrub(+this.value)"></div>` : ''}
          ${c.pose === 'rig' ? cgRigHtml() : ''}
          ${c.poseNote ? `<div class="count">${esc(c.poseNote)}</div>` : ''}
          ${c.poseNote2 ? `<div class="count">${esc(c.poseNote2)}</div>` : ''}
        </fieldset>
        <fieldset><legend>${tt('cards.gen_camera')}</legend>
          <div class="count">${tt('cards.gen_view_hint')}</div>
          <div class="armexprow"><button class="mini" onclick="cgPlaceReset()"${c.xf.t.some(Boolean) || c.xf.r.some(Boolean) || c.cam.pan ? '' : ' disabled'}>${tt('cards.gen_place_reset')}</button></div>
          ${sl('cam', 'yaw', -180, 180, 1, tt('cards.gen_turn'))}${sl('cam', 'pitch', -30, 45, 1, tt('cards.gen_tilt'))}
          ${sl('cam', 'scale', 0.4, 3, 0.05, tt('cards.gen_ortho_scale'))}${sl('cam', 'height', -1.5, 1.5, 0.02, tt('cards.gen_height'))}
        </fieldset>
        <fieldset><legend>${tt('cards.gen_light')}</legend>
          <div class="armexprow">${['sun', 'point'].map(t => `<label class="armcheck"><input type="radio" name="cgLight"${c.light.type === t ? ' checked' : ''}
              onchange="cg().light.type='${t}';cgRender()"> ${cgLightLabel(t)}</label>`).join('')}</div>
          ${sl('light', 'azimuth', -180, 180, 1, tt('cards.gen_azimuth'))}${sl('light', 'elevation', -60, 89, 1, tt('cards.gen_elevation'))}
          ${sl('light', 'amount', 0, 2, 0.01, tt('cards.gen_amount'))}${sl('light', 'level', 0.2, 2.5, 0.01, tt('cards.gen_level'))}
          ${sl('light', 'ambient', 0, 1, 0.01, tt('cards.gen_ambient'))}
        </fieldset>
        <fieldset><legend>${tt('cards.gen_finish')}</legend>
          ${sl('post', 'blur', 0, 2, 0.05, tt('cards.gen_blur'))}${sl('post', 'exposure', -2, 2, 0.05, tt('cards.gen_exposure'))}
          ${sl('post', 'brightness', -0.5, 0.5, 0.01, tt('cards.gen_brightness'))}${sl('post', 'contrast', 0.3, 2, 0.01, tt('cards.gen_contrast'))}
          ${sl('post', 'gamma', 0.3, 3, 0.01, tt('cards.gen_gamma'))}${sl('post', 'saturation', 0, 2, 0.01, tt('cards.gen_saturation'))}
          ${sl('post', 'hue', -180, 180, 1, tt('cards.gen_hue'))}${sl('post', 'sharpen', 0, 1, 0.01, tt('cards.gen_sharpen'))}
          ${sl('post', 'outline', 0, 1.5, 0.05, tt('cards.gen_outline'))}
          <label class="armcheck"><input type="checkbox"${c.post.painted ? ' checked' : ''}
            onchange="cg().post.painted=this.checked;cgRender()"> ${tt('cards.gen_painted')}</label>
          <div class="count">${tt('cards.gen_painted_hint')}</div>
        </fieldset>
      </div>
      <div class="cgout">
        <div class="cghd"><div class="count">${tt('cards.gen_hd', {w: w * c.ss, h: h * c.ss})}</div>
          <div class="cghdview" id="cgHdView"><canvas id="cgHd" tabindex="0"></canvas><canvas id="cgHdUi"></canvas></div></div>
        <div class="cgcard"><div class="count">${tt('cards.gen_card', {w, h})}</div>
          <canvas id="cgCard" width="${w}" height="${h}" style="width:${w * 4}px;height:${h * 4}px"></canvas>
          <div class="armexprow"><label>${tt('cards.gen_name')}<input value="${esc(c.name)}" placeholder="${esc(tt('cards.gen_name_hint'))}" oninput="cg().name=this.value"></label>
            <button class="primary" onclick="cgSave()">${tt('cards.gen_save')}</button>
            <button onclick="cgSaveHd()">${tt('cards.gen_save_hd')}</button></div>
          ${c.saved ? `<div class="armissue ok">${tt('cards.gen_saved', {path: c.saved.path})}</div>
            <div class="armexprow"><label>${tt('cards.gen_unit')}<input list="cgUnits" value="${esc(c.unit)}" onchange="cg().unit=this.value"></label>
              <datalist id="cgUnits">${(c.units || []).map(u => `<option value="${esc(u)}">`).join('')}</datalist>
              <button onclick="cgGive(false)">${tt('cards.gen_give')}</button>
              ${c.givePlan ? `<button class="primary" onclick="cgGive(true)">${tt('cards.gen_give_apply')}</button>` : ''}</div>
            ${c.givePlan ? `<div class="count">${c.givePlan.map(esc).join('<br>')}</div>` : ''}` : ''}
          ${c.err ? `<div class="armexperr">${esc(c.err)}</div>` : ''}
        </div>
      </div>
    </div>`;
  cgRender();
  cgViewWire();
}
function cgRepaint(){ renderCardGen(); }
function cgSet(path, key, v){
  cg()[path][key] = v;
  const el = document.getElementById(`cgv_${path}_${key}`);
  if(el) el.textContent = (+v).toFixed(Math.abs(v) < 10 && v % 1 ? 2 : (String(v).includes('.') ? 2 : 0));
  clearTimeout(ARM.cgTimer); ARM.cgTimer = setTimeout(cgRender, 60);
}

/* --- posing ------------------------------------------------------------------------ */

async function cgAnimFrom(key){ await armAnimFrom(key); cgRepaint(); }
async function cgAnimPick(key){
  await armAnimPick(key);
  const a = armAnim(); a.playing = false;
  cgRender();
}
function cgScrub(v){ const a = armAnim(); a.playing = false; a.t = armAnimLength() * v / 1000; cgRender(); }

/* A preset is a frame of the real animation of that name, from the first
   loaded entry whose skeletons have it. */
async function cgPose(id){
  const c = cg(), a = armAnim();
  c.pose = id; c.poseNote = ''; c.poseNote2 = '';
  if(id === 'anim'){ cgRepaint(); return; }
  if(id === 'rig'){ await cgRigStart(); cgRepaint(); return; }
  if(id === 'tpose'){ armAnimRest(); cgRepaint(); return; }
  const p = CG_POSES.find(x => x.id === id);
  if(!(armProj().anim || {}).asset){
    const first = armAnimEntries()[0];
    if(!first){ c.poseNote = tt('cards.gen_no_entry'); armAnimRest(); cgRepaint(); return; }
    await armAnimFrom(armAssetKey(first));
  }
  const skels = Object.keys((a.list && a.list.skeletons) || {});
  const order = p.skel ? skels.filter(s => p.skel.test(s)).concat(skels.filter(s => !p.skel.test(s))) : [a.skel.toLowerCase()].concat(skels);
  for(const s of order){
    const sk = a.list.skeletons[s];
    for(const name of p.acts){
      const row = (sk && sk.actions || []).find(r => r.playable && r.action.toLowerCase() === name);
      if(!row) continue;
      if(s !== (a.skel || '').toLowerCase()) armAnimSkel(s);
      await armAnimPick(row.slot != null ? String(row.slot) : 'a:' + row.action);
      a.playing = false;
      a.t = armAnimLength() * p.f;
      c.poseNote = tt('cards.gen_pose_from', {action: row.action, skeleton: s});
      c.poseNote2 = p.skel && !p.skel.test(s) ? tt('cards.gen_pose_no_mount') : '';
      cgRepaint();
      return;
    }
  }
  c.poseNote = tt('cards.gen_pose_missing', {pose: cgPoseLabel(id)});
  armAnimRest();
  cgRepaint();
}

/* --- rendering ---------------------------------------------------------------------- */

function cgCamera(objs, w, h){
  const c = cg().cam, b = armBounds(objs);
  if(!b) return null;
  // the game's x is mirrored on the way to the screen (ARM_MIRROR)
  const cx = -(b[0][0] + b[1][0]) / 2, cz = (b[0][2] + b[1][2]) / 2;
  const halfH = c.scale / 2, halfW = halfH * w / h;
  const yaw = c.yaw * Math.PI / 180, pitch = c.pitch * Math.PI / 180, d = 10;
  // 99m: a pan moves the frame sideways, along the camera's own right
  const pan = c.pan || 0;
  const target = [cx + Math.cos(yaw) * pan, b[1][1] - halfH * 0.92 + c.height, cz - Math.sin(yaw) * pan];
  const eye = [target[0] + d * Math.cos(pitch) * Math.sin(yaw), target[1] + d * Math.sin(pitch), target[2] + d * Math.cos(pitch) * Math.cos(yaw)];
  const n = 0.01, f = 40;
  return {proj: [1/halfW,0,0,0, 0,1/halfH,0,0, 0,0,-2/(f-n),0, 0,0,-(f+n)/(f-n),1], view: v3LookAt(eye, target, [0, 1, 0]), eye, target};
}
function cgLight(cam){
  const l = cg().light, az = l.azimuth * Math.PI / 180, el = l.elevation * Math.PI / 180;
  const yaw = cg().cam.yaw * Math.PI / 180;
  // the lamp is placed about the camera's own direction, as the kit's lamp
  // stays put beside its camera
  const dir = [Math.cos(el) * Math.sin(yaw + az), Math.sin(el), Math.cos(el) * Math.cos(yaw + az)];
  return {amount: l.amount * 1.6, ambient: l.ambient, level: l.level, point: l.type === 'point', dir,
          pos: [cam.target[0] + dir[0] * 2.2, cam.target[1] + dir[1] * 2.2, cam.target[2] + dir[2] * 2.2]};
}
function cgPass(objs, W, H, cam, opts){
  armRender(objs, W, H, cam, Object.assign({plain: true, card: true, bg: [0, 0, 0], pre: cgModelMatrix(objs)}, opts));
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  const x = cv.getContext('2d', {willReadFrequently: true});
  x.drawImage(ARM.glCanvas, 0, 0, W, H, 0, 0, W, H);
  return x.getImageData(0, 0, W, H);
}

/* Square dilation of a 0/1 mask by r pixels, rows then columns. */
function cgDilate(m, W, H, r){
  if(r <= 0) return m.slice();
  const t = new Uint8Array(W * H), o = new Uint8Array(W * H);
  for(let y = 0; y < H; y++){
    let run = -1e9;
    for(let x = 0; x < W + r; x++){
      if(x < W && m[y * W + x]) run = x;
      const at = x - r;
      if(at >= 0 && at < W && x - run <= 2 * r) t[y * W + at] = 1;
    }
  }
  for(let x = 0; x < W; x++){
    let run = -1e9;
    for(let y = 0; y < H + r; y++){
      if(y < H && t[y * W + x]) run = y;
      const at = y - r;
      if(at >= 0 && at < H && y - run <= 2 * r) o[at * W + x] = 1;
    }
  }
  return o;
}

function cgRender(){
  const c = cg(), hdCv = document.getElementById('cgHd'), cardCv = document.getElementById('cgCard');
  if(!hdCv || !cardCv) return;
  const objs = cgObjects(), [w, h] = cgDims(), ss = c.ss, W = w * ss, H = h * ss;
  if(!objs.length || !armGl()) return;
  if(typeof armAnimPose === 'function') armAnimPose(objs);
  const cam = cgCamera(objs, W, H);
  if(!cam) return;
  const col = cgPass(objs, W, H, cam, {light: cgLight(cam)});
  const sil = cgPass(objs, W, H, cam, {mask: true});
  const mask = new Uint8Array(W * H);
  for(let i = 0; i < W * H; i++) mask[i] = sil.data[i * 4] > 127 ? 1 : 0;
  const grown = cgDilate(mask, W, H, Math.round(c.post.outline * ss));
  const hi = new ImageData(W, H);
  for(let i = 0; i < W * H; i++){
    if(mask[i]){ hi.data[i*4] = col.data[i*4]; hi.data[i*4+1] = col.data[i*4+1]; hi.data[i*4+2] = col.data[i*4+2]; hi.data[i*4+3] = 255; }
    else if(grown[i]) hi.data[i*4+3] = 255;
  }
  if(c.post.painted) cgPainted(hi.data, mask, W, H, ss);
  // the HD render: no blur, no scaling
  hdCv.width = W; hdCv.height = H;
  hdCv.getContext('2d').putImageData(hi, 0, 0);
  ARM.cgLast = {cam, W, H, objs};
  cgHandlesDraw();
  // the card: blurred, scaled down, coloured and sharpened
  const big = document.createElement('canvas'); big.width = W; big.height = H;
  const bx = big.getContext('2d');
  // a CSS filter, built from its parts
  bx.filter = c.post.blur > 0 ? ['blur', '(', (c.post.blur * ss).toFixed(2), 'px', ')'].join('') : 'none';
  bx.drawImage(hdCv, 0, 0);
  const cx = cardCv.getContext('2d', {willReadFrequently: true});
  cardCv.width = w; cardCv.height = h;
  cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = 'high';
  cx.clearRect(0, 0, w, h);
  cx.drawImage(big, 0, 0, w, h);
  const im = cx.getImageData(0, 0, w, h);
  cgFinish(im.data, w, h, c.post);
  cx.putImageData(im, 0, 0);
}

/* 96f: the painted look, on the HD render before it is scaled down: the
   colours evened out over about a card pixel, flattened to a few steps each
   (flat brush areas), and a thin dark line where two areas meet, about a
   fifth of a card pixel wide. Only inside the model; the outline is left. */
const CG_PAINT_LEVELS = 6;
function cgPainted(d, mask, W, H, ss){
  const r = Math.max(1, Math.round(ss / 2)), n = W * H;
  // even out: a box average over the model's own pixels, rows then columns
  const tmp = new Float32Array(n * 3), out = new Float32Array(n * 3);
  for(let pass = 0; pass < 2; pass++){
    const src = pass ? tmp : null, dst = pass ? out : tmp;
    for(let y = 0; y < H; y++) for(let x = 0; x < W; x++){
      const i = y * W + x;
      if(!mask[i]) continue;
      let s0 = 0, s1 = 0, s2 = 0, k = 0;
      for(let t = -r; t <= r; t++){
        const xx = pass ? x : x + t, yy = pass ? y + t : y;
        if(xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
        const j = yy * W + xx;
        if(!mask[j]) continue;
        if(src){ s0 += src[j*3]; s1 += src[j*3+1]; s2 += src[j*3+2]; }
        else { s0 += d[j*4]; s1 += d[j*4+1]; s2 += d[j*4+2]; }
        k++;
      }
      dst[i*3] = s0 / k; dst[i*3+1] = s1 / k; dst[i*3+2] = s2 / k;
    }
  }
  // flatten to a few steps a channel
  const step = 255 / (CG_PAINT_LEVELS - 1), q = new Int32Array(n);
  for(let i = 0; i < n; i++){
    if(!mask[i]) continue;
    const a = Math.round(out[i*3] / step), b = Math.round(out[i*3+1] / step), c = Math.round(out[i*3+2] / step);
    q[i] = (a * 8 + b) * 8 + c + 1;
    d[i*4] = Math.round(a * step); d[i*4+1] = Math.round(b * step); d[i*4+2] = Math.round(c * step);
  }
  // the line where two areas meet, grown to its width
  const edge = new Uint8Array(n);
  for(let y = 0; y < H; y++) for(let x = 0; x < W; x++){
    const i = y * W + x;
    if(!mask[i]) continue;
    if((x + 1 < W && mask[i+1] && q[i+1] !== q[i]) || (y + 1 < H && mask[i+W] && q[i+W] !== q[i])) edge[i] = 1;
  }
  const line = cgDilate(edge, W, H, Math.max(0, Math.round(ss * 0.1)));
  for(let i = 0; i < n; i++) if(line[i] && mask[i]){
    d[i*4] = Math.round(d[i*4] * 0.3); d[i*4+1] = Math.round(d[i*4+1] * 0.3); d[i*4+2] = Math.round(d[i*4+2] * 0.3);
  }
}

/* The colour and sharpen steps, on the card's own pixels. */
function cgFinish(d, w, h, p){
  const ex = Math.pow(2, p.exposure), hue = p.hue * Math.PI / 180, ch = Math.cos(hue), sh = Math.sin(hue);
  for(let i = 0; i < d.length; i += 4){
    if(!d[i+3]) continue;
    let r = d[i] / 255 * ex + p.brightness, g = d[i+1] / 255 * ex + p.brightness, b = d[i+2] / 255 * ex + p.brightness;
    r = (r - 0.5) * p.contrast + 0.5; g = (g - 0.5) * p.contrast + 0.5; b = (b - 0.5) * p.contrast + 0.5;
    r = Math.pow(Math.max(r, 0), 1 / p.gamma); g = Math.pow(Math.max(g, 0), 1 / p.gamma); b = Math.pow(Math.max(b, 0), 1 / p.gamma);
    // hue turned and saturation scaled in YIQ, which keeps the lightness
    const Y = 0.299 * r + 0.587 * g + 0.114 * b, I0 = 0.596 * r - 0.274 * g - 0.322 * b, Q0 = 0.211 * r - 0.523 * g + 0.312 * b;
    const I = (I0 * ch - Q0 * sh) * p.saturation, Q = (I0 * sh + Q0 * ch) * p.saturation;
    d[i] = Math.max(0, Math.min(255, Math.round((Y + 0.956 * I + 0.621 * Q) * 255)));
    d[i+1] = Math.max(0, Math.min(255, Math.round((Y - 0.272 * I - 0.647 * Q) * 255)));
    d[i+2] = Math.max(0, Math.min(255, Math.round((Y - 1.106 * I + 1.703 * Q) * 255)));
  }
  if(p.sharpen > 0){
    const src = Uint8ClampedArray.from(d);
    for(let y = 0; y < h; y++) for(let x = 0; x < w; x++){
      const i = (y * w + x) * 4;
      if(!src[i+3]) continue;
      for(let k = 0; k < 3; k++){
        let s = 0, n = 0;
        for(let dy = -1; dy <= 1; dy++) for(let dx = -1; dx <= 1; dx++){
          const xx = x + dx, yy = y + dy;
          if(xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
          s += src[(yy * w + xx) * 4 + k]; n++;
        }
        d[i+k] = Math.max(0, Math.min(255, Math.round(src[i+k] + p.sharpen * (src[i+k] - s / n))));
      }
    }
  }
}

/* --- saving --------------------------------------------------------------------------- */

function cgKind(){ const s = cg().size; return s === 'info' ? 'info' : s === 'custom' ? 'custom' : 'card'; }
async function cgSave(){
  const c = cg(), cv = document.getElementById('cgCard');
  if(!cv) return;
  const name = (c.name || '').trim();
  if(!name){ toast(tt('cards.gen_name_first')); return; }
  try{
    const r = await api.post('/api/armory/cards/save', {name, kind: cgKind(), size: cgDims(), png: cv.toDataURL('image/png')});
    c.saved = r; c.err = ''; c.givePlan = null;
    if(!c.units){ try{ c.units = (await api.get('/api/armory/templates?mod=' + enc(state.src))).units.map(u => u.type); }catch(e){ c.units = []; } }
  }catch(e){ c.err = errText(e); }
  cgRepaint();
}
async function cgSaveHd(){
  const c = cg(), cv = document.getElementById('cgHd');
  const name = (c.name || '').trim();
  if(!cv || !name){ toast(tt('cards.gen_name_first')); return; }
  try{ const r = await api.post('/api/armory/cards/save', {name, kind: 'hd', size: [cv.width, cv.height], png: cv.toDataURL('image/png')});
       toast(tt('cards.gen_saved', {path: r.path}), 5000); }
  catch(e){ toast(errText(e)); }
}
/* The saved card handed to the unit editor's own import, planned first. */
async function cgGive(apply){
  const c = cg();
  if(!c.saved || !c.unit){ toast(tt('cards.gen_unit_first')); return; }
  const body = {mod: state.src, unit: c.unit};
  body[c.saved.kind === 'info' ? 'info_src' : 'card_src'] = c.saved.path;
  try{
    if(!apply){
      const r = await api.post('/api/edit/plan', body);
      if(r.errors && r.errors.length){ c.err = r.errors.join('; '); c.givePlan = null; }
      else{ c.givePlan = (r.changes || []).concat(r.warnings || []); c.err = ''; }
    }else{
      await api.post('/api/edit/apply', body);
      toast(tt('cards.gen_given', {unit: c.unit}));
      c.givePlan = null;
    }
  }catch(e){ c.err = errText(e); }
  cgRepaint();
}

/* --- the model's place in the frame (99m) ------------------------------------------- */

/* The card maker's move and turn of the whole model, in the game's space,
   about the model's own middle, so a turn turns it where it stands. */
function cgModelMatrix(objs){
  const x = cg().xf;
  if(!x || (!x.t.some(Boolean) && !x.r.some(Boolean))) return null;
  const b = armBounds(objs);
  const c = b ? [0, 1, 2].map(k => (b[0][k] + b[1][k]) / 2) : [0, 0, 0];
  let m = armTrans(-c[0], -c[1], -c[2]);
  m = armMul(armRot(x.r[0], x.r[1], x.r[2]), m);
  return armMul(armTrans(c[0] + x.t[0], c[1] + x.t[1], c[2] + x.t[2]), m);
}
function cgPlaceReset(){ const c = cg(); c.xf = {t: [0, 0, 0], r: [0, 0, 0]}; c.cam.pan = 0; cgRepaint(); }

/* --- the IK rig and the pose library (99n, cgrig.js) ---------------------------------- */

async function cgRigLoad(){
  if(ARM.poses) return ARM.poses;
  try{
    const d = await api.get('/api/armory/poses', 1);
    ARM.poses = d;
    ARM.rigs = {};
    for(const [k, bones] of Object.entries(d.rigs || {})) ARM.rigs[k] = crRig(bones);
  }catch(e){ ARM.poses = {rigs: {}, poses: [], err: errText(e)}; ARM.rigs = {}; }
  return ARM.poses;
}
/* The layout for the skeleton in use: the kit's dwarf for a dwarf's or a
   hobbit's, its archer for a bowman's, its infantry otherwise. */
function cgRigType(){
  const r = cg().rig;
  if(r.type && r.type !== 'auto') return r.type;
  const sk = (armAnim().skel || '').toLowerCase();
  if(/dwarf|hobbit|halfling/.test(sk)) return 'dwarf';
  if(/bow|archer/.test(sk)) return 'archer';
  return 'infantry';
}
function cgRigActive(){ return cg().pose === 'rig' && !!(ARM.rigs && ARM.rigs[cgRigType()]); }
function cgRigSolved(){
  const rig = ARM.rigs[cgRigType()];
  return {rig, W: crSolve(rig, cg().rig.basis, cgRigType())};
}
function cgRigPose(anim){ const s = cgRigSolved(); return crPoseOn(s.rig, s.W, anim); }

/* The rig poses a skeleton, so a skeleton is needed: the chosen entry's,
   any of its actions read once for its bones, and nothing played. */
async function cgRigStart(){
  const c = cg(), a = armAnim();
  await cgRigLoad();
  if(ARM.poses.err){ c.poseNote = ARM.poses.err; return; }
  if(!a.list){
    // the entry the project's animations come from, else the first loaded
    const first = armAnimEntries()[0];
    const key = (armProj().anim || {}).asset || (first ? armAssetKey(first) : '');
    if(!key){ c.poseNote = tt('cards.gen_no_entry'); return; }
    await armAnimFrom(key);
  }
  if(!a.data && a.list && a.list.skeletons){
    const sk = a.list.skeletons[(a.skel || '').toLowerCase()];
    const row = sk && (sk.actions || []).find(r => r.playable);
    if(row) await armAnimPick(row.slot != null ? String(row.slot) : 'a:' + row.action);
  }
  a.playing = false;
  if(!c.rig.cat) c.rig.cat = cgRigType() === 'dwarf' ? 'IK Dwarves Full/1H' : 'IK Full/1H';
  c.poseNote = a.data ? tt('cards.gen_rig_on', {rig: cgRigLabel(cgRigType()), skeleton: a.skel}) : tt('cards.gen_no_entry');
}
const cgRigLabel = t => ({infantry: 'IK_Infantry', archer: 'IK_Archer', dwarf: 'IK_Dwarf'})[t] || t;
const cgPartLabel = p => ({whole: tt('cards.gen_part_whole'), arms: tt('cards.gen_part_arms'), legs: tt('cards.gen_part_legs'),
  head: tt('cards.gen_part_head'), posture: tt('cards.gen_part_posture')})[p] || p;

function cgRigHtml(){
  const c = cg(), r = c.rig, P = ARM.poses;
  if(!P) return `<div class="count">${tt('armory.reading')}</div>`;
  const cats = [...new Set(P.poses.map(p => p.c))].sort();
  const list = P.poses.map((p, i) => [p, i]).filter(([p]) => p.c === r.cat);
  const two = ((r.basis.Switch || {}).l || [0, 0, 0])[1] > 0;
  return `<div class="cgrig">
    <div class="armexprow"><label>${tt('cards.gen_rig')}<select onchange="cg().rig.type=this.value;cgRepaint()">${['auto', 'infantry', 'archer', 'dwarf'].map(t =>
        `<option value="${t}"${r.type === t ? ' selected' : ''}>${t === 'auto' ? esc(tt('cards.gen_rig_auto', {rig: cgRigLabel(cgRigType())})) : cgRigLabel(t)}</option>`).join('')}</select></label>
      <label class="armcheck" title="${esc(tt('cards.gen_two_hands_title'))}"><input type="checkbox"${two ? ' checked' : ''} onchange="cgRigTwoHands(this.checked)"> ${tt('cards.gen_two_hands')}</label>
      <label class="armcheck"><input type="checkbox"${r.handles ? ' checked' : ''} onchange="cg().rig.handles=this.checked;cgHandlesDraw()"> ${tt('cards.gen_handles')}</label>
      <button class="mini" onclick="cgRigReset()">${tt('cards.gen_rig_reset')}</button></div>
    <div class="count">${tt('cards.gen_rig_hint')}</div>
    <div class="armexprow"><label>${tt('cards.gen_library')}<select onchange="cg().rig.cat=this.value;cgRepaint()">${cats.map(k =>
        `<option${k === r.cat ? ' selected' : ''}>${esc(k)}</option>`).join('')}</select></label>
      <label>${tt('cards.gen_apply_to')}<select onchange="cg().rig.part=this.value">${['whole', 'arms', 'legs', 'head', 'posture'].map(p =>
        `<option value="${p}"${r.part === p ? ' selected' : ''}>${esc(cgPartLabel(p))}</option>`).join('')}</select></label></div>
    <select class="cgposes" size="8" onchange="cgRigApply(+this.value)">${list.map(([p, i]) =>
      `<option value="${i}"${r.pick === p.n ? ' selected' : ''}>${esc(p.n)}</option>`).join('')}</select>
    <div class="count">${ttN('cards.gen_library_note', P.poses.length)}</div>
  </div>`;
}
function cgRigApply(i){
  const c = cg(), p = ARM.poses.poses[i];
  if(!p) return;
  c.rig.basis = crApply(c.rig.basis, p, c.rig.part);
  c.rig.pick = p.n;
  cgRender();
}
function cgRigReset(){ cg().rig.basis = {}; cg().rig.pick = ''; cgRepaint(); }
function cgRigTwoHands(on){
  const b = cg().rig.basis;
  if(on) b.Switch = {l: [0, 0.05, 0]}; else delete b.Switch;
  cgRender();
}

/* --- the controllers over the HD view ------------------------------------------------ */

/* What the kit lets an animator take hold of: the pelvis, the torso, the
   head, the hands and feet, the poles for the elbows and knees. */
const CG_HANDLES = [
  {n: 'IK Pelvis', col: '#f0c040', r: 8}, {n: 'IK Torso Controller', col: '#f0c040', r: 6},
  {n: 'IK Head', col: '#f0c040', r: 6, turn: true},
  {n: 'IK frist right', col: '#e8555f', r: 7}, {n: 'IK frist  left', col: '#4f8fe8', r: 7},
  {n: 'IK elbow right', col: '#e8555f', r: 5, pole: true}, {n: 'IK elbow left', col: '#4f8fe8', r: 5, pole: true},
  {n: 'IK angle right', col: '#e8555f', r: 7, foot: true}, {n: 'IK angle left', col: '#4f8fe8', r: 7, foot: true},
  {n: 'IK knee right', col: '#e8555f', r: 5, pole: true}, {n: 'IK knee left', col: '#4f8fe8', r: 5, pole: true},
  {n: 'Pole', col: '#c8a45c', r: 5, two: true},
];
/* The HD canvas's picture inside its box (object-fit: contain), in CSS px. */
function cgHdBox(){
  const cv = document.getElementById('cgHd');
  if(!cv || !cv.width) return null;
  const r = cv.getBoundingClientRect(), k = Math.min(r.width / cv.width, r.height / cv.height);
  const w = cv.width * k, h = cv.height * k;
  return {r, k, x: (r.width - w) / 2, y: (r.height - h) / 2, w, h};
}
/* A point of the rig (Blender's space) on the HD view, in CSS px of the box. */
function cgRigToView(p, L, box){
  let g = [p[0], p[2], p[1]];
  const pre = cgModelMatrix(L.objs);
  if(pre) g = [pre[0]*g[0] + pre[4]*g[1] + pre[8]*g[2] + pre[12], pre[1]*g[0] + pre[5]*g[1] + pre[9]*g[2] + pre[13], pre[2]*g[0] + pre[6]*g[1] + pre[10]*g[2] + pre[14]];
  const m = armMul(L.cam.proj, L.cam.view), x = -g[0], y = g[1], z = g[2];
  const w = m[3]*x + m[7]*y + m[11]*z + m[15] || 1;
  const nx = (m[0]*x + m[4]*y + m[8]*z + m[12]) / w, ny = (m[1]*x + m[5]*y + m[9]*z + m[13]) / w;
  return [box.x + (nx * 0.5 + 0.5) * box.w, box.y + (1 - (ny * 0.5 + 0.5)) * box.h];
}
function cgHandlesAt(){
  const L = ARM.cgLast, box = cgHdBox();
  if(!L || !box || !cgRigActive() || !cg().rig.handles) return [];
  const {rig, W} = cgRigSolved();
  const two = ((cg().rig.basis.Switch || {}).l || [0, 0, 0])[1] > 0;
  return CG_HANDLES.filter(h => rig.byName.has(h.n) && (!h.two || two)).map(h => {
    const i = rig.byName.get(h.n);
    return Object.assign({at: cgRigToView(crPos(W[i]), L, box)}, h);
  });
}
function cgHandlesDraw(){
  const ui = document.getElementById('cgHdUi'), box = cgHdBox();
  if(!ui || !box) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  Object.assign(ui.style, {left: box.x + 'px', top: box.y + 'px', width: box.w + 'px', height: box.h + 'px'});
  ui.width = Math.round(box.w * dpr); ui.height = Math.round(box.h * dpr);
  const x = ui.getContext('2d');
  x.setTransform(dpr, 0, 0, dpr, -box.x * dpr, -box.y * dpr);
  x.clearRect(box.x, box.y, box.w, box.h);
  const hs = cgHandlesAt();
  // each limb's hand or foot joined to its pole, so a pole reads as its joint's
  const at = n => (hs.find(h => h.n === n) || {}).at;
  x.strokeStyle = 'rgba(255,255,255,.35)'; x.setLineDash([3, 3]); x.lineWidth = 1;
  for(const [a, b] of [['IK frist right', 'IK elbow right'], ['IK frist  left', 'IK elbow left'], ['IK angle right', 'IK knee right'], ['IK angle left', 'IK knee left']]){
    const p = at(a), q = at(b);
    if(p && q){ x.beginPath(); x.moveTo(p[0], p[1]); x.lineTo(q[0], q[1]); x.stroke(); }
  }
  x.setLineDash([]);
  const hot = ARM.cgDrag && ARM.cgDrag.h ? ARM.cgDrag.h.n : ARM.cgHover;
  for(const h of hs){
    const [px, py] = h.at;
    x.beginPath();
    if(h.pole){ x.moveTo(px, py - h.r); x.lineTo(px + h.r, py); x.lineTo(px, py + h.r); x.lineTo(px - h.r, py); x.closePath(); }
    else if(h.foot) x.rect(px - h.r, py - h.r * 0.7, h.r * 2, h.r * 1.4);
    else x.arc(px, py, h.r, 0, Math.PI * 2);
    x.fillStyle = h.n === hot ? '#fff' : h.col;
    x.globalAlpha = 0.85; x.fill(); x.globalAlpha = 1;
    x.strokeStyle = '#111'; x.lineWidth = 1.2; x.stroke();
    if(h.turn){ x.beginPath(); x.arc(px, py, h.r + 4, -0.6, 0.6); x.strokeStyle = h.col; x.stroke(); }
  }
}
function cgHandleHit(e){
  const box = cgHdBox();
  if(!box) return null;
  const px = e.clientX - box.r.left, py = e.clientY - box.r.top;
  let best = null, bd = 12;
  for(const h of cgHandlesAt()){ const d = Math.hypot(h.at[0] - px, h.at[1] - py); if(d < bd){ bd = d; best = h; } }
  return best;
}

/* A move on screen as a move in the game's space: the camera's right and up
   (page space), then the page's mirror taken off. One CSS pixel is the
   frame's height over the box's. */
function cgScreenToGame(dx, dy){
  const L = ARM.cgLast, box = cgHdBox();
  if(!L || !box) return [0, 0, 0];
  const v = L.cam.view, k = cg().cam.scale / box.h;
  const right = [v[0], v[4], v[8]], up = [v[1], v[5], v[9]];
  const page = [0, 1, 2].map(i => (right[i] * dx - up[i] * dy) * k);
  return [-page[0], page[1], page[2]];
}
function cgDragHandle(h, dx, dy){
  const c = cg(), {rig, W} = cgRigSolved(), i = rig.byName.get(h.n), b = rig.bones[i];
  const ch = c.rig.basis[h.n] = Object.assign({}, c.rig.basis[h.n] || {});
  if(h.turn){
    // the head turns: across the screen about the up axis, up and down about its own
    const e = crToEuler(ch.q ? crQuat(ch.q) : [1,0,0, 0,1,0, 0,0,1]);
    e[2] -= dx * 0.012; e[0] += dy * 0.012;
    ch.q = crToQuat(crEuler(e));
    return;
  }
  let g = cgScreenToGame(dx, dy);
  const x = c.xf;
  if(x && x.r.some(Boolean)){
    const R = armRot(x.r[0], x.r[1], x.r[2]);      // column-major; its transpose turns back
    g = [R[0]*g[0] + R[1]*g[1] + R[2]*g[2], R[4]*g[0] + R[5]*g[1] + R[6]*g[2], R[8]*g[0] + R[9]*g[1] + R[10]*g[2]];
  }
  const d = [g[0], g[2], g[1]];
  const F = crRot(b.p < 0 ? b.m : crMul(W[b.p], rig.rel[i]));
  const loc = crR3(crT3(F), d);
  const l = ch.l || [0, 0, 0];
  ch.l = [l[0] + loc[0], l[1] + loc[1], l[2] + loc[2]];
}

/* --- the HD view's mouse and keys (99m) --------------------------------------------- */

function cgViewWire(){
  const cv = document.getElementById('cgHd');
  if(!cv || cv.dataset.wired) return;
  cv.dataset.wired = '1';
  let drag = null;
  const later = () => { if(ARM.cgFrame) return; ARM.cgFrame = requestAnimationFrame(() => { ARM.cgFrame = 0; cgRender(); }); };
  cv.addEventListener('pointerdown', e => {
    cv.focus({preventScroll: true});
    if(ARM.cgXform){ e.preventDefault(); cgXformEnd(e.button !== 2); return; }
    const h = e.button === 0 && !e.altKey ? cgHandleHit(e) : null;
    const button = e.button === 0 && e.altKey ? 1 : e.button;
    drag = ARM.cgDrag = {x: e.clientX, y: e.clientY, button, h, moved: false};
    cv.setPointerCapture(e.pointerId);
    if(button === 1) e.preventDefault();
  });
  cv.addEventListener('pointermove', e => {
    ARM.cgMouse = [e.clientX, e.clientY];
    if(ARM.cgXform){ cgXformMove(e); later(); return; }
    if(!drag){
      const h = cgHandleHit(e), n = h ? h.n : null;
      if(n !== ARM.cgHover){ ARM.cgHover = n; cv.style.cursor = n ? 'grab' : ''; cgHandlesDraw(); }
      return;
    }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY; drag.moved = true;
    const c = cg().cam;
    if(drag.h){ cgDragHandle(drag.h, dx, dy); later(); return; }
    if(drag.button !== 1) return;
    if(e.shiftKey){
      const box = cgHdBox(), k = c.scale / (box ? box.h : 400);
      c.pan = (c.pan || 0) - dx * k; c.height += dy * k;
    }else if(e.ctrlKey) c.scale = Math.max(0.2, Math.min(6, c.scale * Math.exp(dy * 0.01)));
    else{ c.yaw = ((c.yaw - dx * 0.5 + 540) % 360) - 180; c.pitch = Math.max(-60, Math.min(80, c.pitch + dy * 0.4)); }
    later();
  });
  cv.addEventListener('pointerup', () => {
    const d = drag; drag = ARM.cgDrag = null;
    if(d && d.moved && !d.h) cgRepaint();             // the camera's sliders show where it went
    else cgHandlesDraw();
  });
  cv.addEventListener('wheel', e => {
    e.preventDefault();
    const c = cg().cam;
    c.scale = Math.max(0.2, Math.min(6, c.scale * Math.exp(e.deltaY * 0.0012)));
    later();
    clearTimeout(ARM.cgWheel); ARM.cgWheel = setTimeout(cgRepaint, 500);
  }, {passive: false});
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('auxclick', e => e.preventDefault());
  cv.addEventListener('keydown', e => {
    const k = e.key.toLowerCase(), x = ARM.cgXform;
    if(x){
      e.preventDefault();
      if(k === 'escape') return cgXformEnd(false);
      if(k === 'enter') return cgXformEnd(true);
      const ax = {x: 0, y: 1, z: 2}[k];
      if(ax !== undefined){ x.axis = x.axis === ax ? null : ax; cgXformMove(null); later(); }
      return;
    }
    if(e.ctrlKey || e.altKey || e.metaKey) return;
    if(k === 'g' || k === 'r'){ e.preventDefault(); cgXformStart(k === 'g' ? 'grab' : 'rotate'); }
  });
}
/* G and R, as the viewport has them: the mouse moves or turns the model in
   the frame until a click or Enter keeps it and Esc or the right button puts
   it back. R turns about the up axis unless X, Y or Z is pressed. */
function cgXformStart(kind){
  const c = cg();
  ARM.cgXform = {kind, axis: null, start: ARM.cgMouse ? ARM.cgMouse.slice() : null,
                 t: c.xf.t.slice(), r: c.xf.r.slice()};
}
function cgXformMove(e){
  const x = ARM.cgXform, c = cg();
  if(!x) return;
  if(e && !x.start) x.start = [e.clientX, e.clientY];
  const m = ARM.cgMouse || x.start;
  if(!x.start || !m) return;
  const dx = m[0] - x.start[0], dy = m[1] - x.start[1];
  if(x.kind === 'grab'){
    let g = cgScreenToGame(dx, dy);
    if(x.axis != null) g = g.map((v, i) => i === x.axis ? v : 0);
    c.xf.t = x.t.map((v, i) => v + g[i]);
  }else{
    const axis = x.axis == null ? 1 : x.axis;
    c.xf.r = x.r.slice();
    c.xf.r[axis] = x.r[axis] + dx * 0.5;
  }
}
function cgXformEnd(keep){
  const x = ARM.cgXform, c = cg();
  ARM.cgXform = null;
  if(!x) return;
  if(!keep){ c.xf.t = x.t; c.xf.r = x.r; }
  cgRepaint();
}
