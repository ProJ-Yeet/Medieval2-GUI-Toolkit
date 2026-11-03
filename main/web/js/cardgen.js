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

   From Pfadfinder-Adam's card maker (RTW-M2TW-Campaign-Editor,
   campaign_editor/cardmaker.py, taken with his leave): the framings (the
   whole man, to the knees, the thighs, the waist) fitted to the figure, the
   card laid on a ground (see-through as the game's own, a colour, a picture,
   or the game's own card ground), an info picture on the game's scroll paper
   inside its portrait frame, the Painted look (the Kuwahara filter, a warm
   light, a canvas grain), the mod's own card sizes and 2-4x bigger ones.
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
    size: 'card', w: 48, h: 64, ss: 10, oneEach: true, pose: 'guard', name: '', unit: '', err: '', saved: null,
    cam: {yaw: 20, pitch: 4, scale: 1.2, height: 0, pan: 0},
    xf: {t: [0, 0, 0], r: [0, 0, 0]},
    rig: {type: 'auto', basis: {}, handles: true, cat: '', pick: '', part: 'whole'},
    light: {type: 'sun', azimuth: 35, elevation: 40, amount: 0.95, level: 1.0, ambient: 0.38},
    post: {blur: 0.5, exposure: 0, brightness: 0, contrast: 1.0, gamma: 1.0, saturation: 1.0, hue: 0, sharpen: 0.2, outline: 0.3},
  };
}
/* What a maker state from before these options lacks, filled in. */
function cgFill(c){
  c.mult = c.mult || 1;
  c.fit = c.fit || {part: 'thighs', auto: true};
  c.ground = c.ground || {kind: 'none', colour: '#5d4d36', pic: ''};
  c.gframe = !!c.gframe;
  c.paint = c.paint || {on: false, strength: 1};
  return c;
}
// the base size before the 1-4x multiplier: the four of old, or the mod's own
function cgBase(){
  const c = cgFill(cg()), m = c.modSizes || {};
  if(c.size === 'custom') return [Math.max(8, c.w | 0), Math.max(8, c.h | 0)];
  if(c.size === 'modcard') return m.card || CG_SIZES.card;
  if(c.size === 'modinfo') return m.info || CG_SIZES.info;
  return CG_SIZES[c.size] || CG_SIZES.card;
}
function cgDims(){ const c = cg(), [w, h] = cgBase(), k = Math.max(1, Math.min(4, c.mult || 1)); return [w * k, h * k]; }
// the HD render's scale, held so neither side passes 4096 (a WebGL canvas
// past that is refused on many cards)
function cgSS(){ const c = cg(), [w, h] = cgDims(); return Math.max(1, Math.min(c.ss, Math.floor(4096 / Math.max(w, h)))); }
// how big the card is drawn on the page: four times the game's own card, never
// wider than the column (a 4x info picture would be 2,880 pixels)
const cgShow = w => Math.max(1, Math.min(4, 340 / w));
const cgIsInfo = () => ['info', 'modinfo'].includes(cg().size);

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
  custom: tt('cards.gen_size_custom'), modcard: tt('cards.gen_size_modcard'), modinfo: tt('cards.gen_size_modinfo')})[s] || s;
const CG_PARTS = [['whole', 1.0], ['knees', 0.78], ['thighs', 0.64], ['waist', 0.5]];
const cgFramingLabel = p => ({whole: tt('cards.gen_frame_whole'), knees: tt('cards.gen_frame_knees'),
  thighs: tt('cards.gen_frame_thighs'), waist: tt('cards.gen_frame_waist')})[p] || p;
const cgGroundLabel = g => ({none: tt('cards.gen_ground_none'), colour: tt('cards.gen_ground_colour'), pic: tt('cards.gen_ground_pic'),
  STRAT_CARD_BACKGROUND: tt('cards.gen_ground_strat'), BATTLE_CARD_BACKGROUND: tt('cards.gen_ground_battle'),
  SCROLL_MID: tt('cards.gen_ground_scroll')})[g] || g;
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
  cgFill(st);
  if(state.src && st.modSizesFor !== state.src){
    st.modSizesFor = state.src; st.modSizes = null;
    api.get('/api/armory/card_sizes?mod=' + enc(state.src)).then(r => { st.modSizes = r; cgRepaint(); }).catch(() => {});
  }
  const c = cg(), [w, h] = cgDims(), ss = cgSS();
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
          <div class="armexprow">${['modcard', 'modinfo'].map(s => { const d = (c.modSizes || {})[s === 'modcard' ? 'card' : 'info'];
              return `<label class="armcheck" title="${ttA('cards.gen_size_mod_title')}"><input type="radio" name="cgSize"${c.size === s ? ' checked' : ''}${d ? '' : ' disabled'}
              onchange="cg().size='${s}';cgRepaint()"> ${cgSizeLabel(s)} <span class="count">${d ? d.join('×') : tt('cards.gen_size_mod_none')}</span></label>`; }).join('')}</div>
          <div class="armexprow" title="${ttA('cards.gen_mult_title')}">${tt('cards.gen_mult')} ${[1, 2, 3, 4].map(k => `<button class="mini${c.mult === k ? ' on' : ''}" onclick="cg().mult=${k};cgRepaint()">${k}×</button>`).join('')}
            <span class="count">${w}×${h}</span></div>
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
        <fieldset><legend>${tt('cards.gen_framing')}</legend>
          <div class="count">${tt('cards.gen_framing_hint')}</div>
          <div class="armexprow">${CG_PARTS.map(([p]) => `<button class="mini${c.fit.part === p ? ' on' : ''}" onclick="cgFit('${p}')">${cgFramingLabel(p)}</button>`).join('')}</div>
          <label class="armcheck"><input type="checkbox"${c.fit.auto ? ' checked' : ''} onchange="cg().fit.auto=this.checked"> ${tt('cards.gen_fit_auto')}</label>
        </fieldset>
        <fieldset><legend>${tt('cards.gen_ground')}</legend>
          <div class="armexprow"><select onchange="cgGround(this.value)">${['none', 'colour', 'pic'].concat(cgIsInfo() ? ['SCROLL_MID'] : ['STRAT_CARD_BACKGROUND', 'BATTLE_CARD_BACKGROUND'])
              .map(g => `<option value="${g}"${c.ground.kind === g ? ' selected' : ''}>${esc(cgGroundLabel(g))}</option>`).join('')}</select>
            ${c.ground.kind === 'colour' ? `<input type="color" value="${esc(c.ground.colour)}" oninput="cg().ground.colour=this.value;cgRender()">` : ''}
            ${c.ground.kind === 'pic' ? `<label class="btn">${tt('cards.gen_ground_pick')}<input type="file" accept="image/*" style="display:none" onchange="cgGroundFile(this.files[0])"></label>` : ''}</div>
          ${c.ground.kind === 'none' ? `<div class="count">${tt('cards.gen_ground_none_note')}</div>` : ''}
          ${c.groundNote ? `<div class="count w-warn">${esc(c.groundNote)}</div>` : ''}
          ${cgIsInfo() ? `<label class="armcheck"><input type="checkbox"${c.gframe ? ' checked' : ''} onchange="cgFrameOn(this.checked)"> ${tt('cards.gen_game_frame')}</label>` : ''}
        </fieldset>
        <fieldset><legend>${tt('cards.gen_painted')}</legend>
          <label class="armcheck" title="${ttA('cards.gen_painted_title')}"><input type="checkbox"${c.paint.on ? ' checked' : ''} onchange="cg().paint.on=this.checked;cgRender()"> ${tt('cards.gen_painted_on')}</label>
          ${c.paint.on ? sl('paint', 'strength', 0.3, 2, 0.05, tt('cards.gen_painted_strength')) : ''}
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
        </fieldset>
      </div>
      <div class="cgout">
        <div class="cghd"><div class="count">${tt('cards.gen_hd', {w: w * ss, h: h * ss})}</div>
          <div class="cghdview" id="cgHdView"><canvas id="cgHd" tabindex="0"></canvas><canvas id="cgHdUi"></canvas></div></div>
        <div class="cgcard"><div class="count">${tt('cards.gen_card', {w, h})}</div>
          <canvas id="cgCard" width="${w}" height="${h}" style="width:${Math.round(w * cgShow(w))}px;height:${Math.round(h * cgShow(w))}px"></canvas>
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
  // Fit on its own: a new pose, size or model is framed again the way it was
  // asked for, until the camera is moved by hand
  const fitKey = [c.pose, c.size, c.mult, objs.length, (armAnim() || {}).key || '', c.fit.part].join('|');
  if(c.fit.auto && objs.length && c.fit.key !== fitKey){ c.fit.key = fitKey; cgFit(c.fit.part); }
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
  const objs = cgObjects(), [w, h] = cgDims(), ss = cgSS(), W = w * ss, H = h * ss;
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
  if(c.paint && c.paint.on) cgPaint(hi.data, mask, W, H, c.paint.strength);
  const bbox = cgMaskBox(mask, W, H);
  // the HD render: no blur, no scaling
  hdCv.width = W; hdCv.height = H;
  hdCv.getContext('2d').putImageData(hi, 0, 0);
  ARM.cgLast = {cam, W, H, objs, bbox};
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
  cgCompose(cardCv);
}

/* --- from Pfad's card maker: framing, ground, frame, painted look ---------------- */

/* The figure's box in the HD render, in its pixels: [x0, y0, x1, y1], or null. */
function cgMaskBox(m, W, H){
  let x0 = W, y0 = H, x1 = -1, y1 = -1;
  for(let y = 0; y < H; y++){ const r = y * W;
    for(let x = 0; x < W; x++) if(m[r + x]){ if(x < x0) x0 = x; if(x > x1) x1 = x; if(y < y0) y0 = y; if(y1 < y) y1 = y; } }
  return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
}
/* Fit the camera to a framing, as Pfad's region() frames the figure: a part
   (knees, thighs, waist) keeps that share of the man from the top, his head
   near the top edge with a little room, cut below; the whole man sits in the
   middle with room all round. The view is orthographic, so the figure's box
   in the last render says exactly how far to zoom and move: twice, the
   second to take up what a pitched camera leaves. */
function cgFit(part, again){
  const c = cg();
  c.fit.part = part;
  const L = ARM.cgLast;
  if(!L || !L.bbox){ cgRepaint(); return; }
  const keep = (CG_PARTS.find(p => p[0] === part) || [0, 1])[1];
  const [x0, y0, x1, y1] = L.bbox, W = L.W, H = L.H, S0 = c.cam.scale, aspect = W / H;
  const u = S0 / H;                                     // world units per pixel, both ways
  const bw = (x1 - x0) * u, bh = (y1 - y0) * u;
  const cosP = Math.max(0.2, Math.cos(c.cam.pitch * Math.PI / 180));
  let S1, want, at;
  if(keep < 1){
    const room = 0.04;
    S1 = Math.max(bh * keep * (1 + room), bw / aspect);
    at = (H / 2 - y0) * u;                              // the head, above the middle
    want = S1 / 2 - room * S1;
  }else{
    const room = 0.05;
    S1 = Math.max(bh * (1 + 2 * room), bw * (1 + 2 * room) / aspect);
    at = (H / 2 - (y0 + y1) / 2) * u;                   // the figure's middle
    want = 0;
  }
  S1 = Math.max(0.2, Math.min(6, S1));
  // the frame's middle moves by dC (world Y): -(S1-S0)/2*0.92 from the scale, plus the height
  const dC = (at - want) / cosP;
  c.cam.height = +(c.cam.height + dC + (S1 - S0) / 2 * 0.92).toFixed(4);
  c.cam.pan = +((c.cam.pan || 0) + ((x0 + x1) / 2 - W / 2) * u).toFixed(4);
  c.cam.scale = +S1.toFixed(4);
  cgRender();
  if(!again){ cgFit(part, true); cgRepaint(); }
}
/* The Kuwahara filter (each pixel the mean colour of the calmest of the four
   squares round it: flat brush areas, the edges kept), as Pfad's _kuwahara,
   on summed-area tables so its cost does not grow with the brush. */
function cgKuwahara(src, W, H, r){
  const n = r + 1, k = n * n, W1 = W + 1;
  const S1 = new Float64Array(W1 * (H + 1)), S2 = new Float64Array(W1 * (H + 1));
  const SR = new Float64Array(W1 * (H + 1)), SG = new Float64Array(W1 * (H + 1)), SB = new Float64Array(W1 * (H + 1));
  for(let y = 0; y < H; y++){
    let a1 = 0, a2 = 0, ar = 0, ag = 0, ab = 0;
    for(let x = 0; x < W; x++){
      const i = (y * W + x) * 4, R = src[i], G = src[i + 1], B = src[i + 2], l = 0.299 * R + 0.587 * G + 0.114 * B;
      a1 += l; a2 += l * l; ar += R; ag += G; ab += B;
      const o = (y + 1) * W1 + x + 1, up = y * W1 + x + 1;
      S1[o] = S1[up] + a1; S2[o] = S2[up] + a2; SR[o] = SR[up] + ar; SG[o] = SG[up] + ag; SB[o] = SB[up] + ab;
    }
  }
  const take = (T, x0, y0) => T[(y0 + n) * W1 + x0 + n] - T[y0 * W1 + x0 + n] - T[(y0 + n) * W1 + x0] + T[y0 * W1 + x0];
  const out = new Uint8ClampedArray(src.length);
  for(let y = 0; y < H; y++) for(let x = 0; x < W; x++){
    let best = Infinity, br = 0, bg = 0, bb = 0;
    for(const dy of [-r, 0]) for(const dx of [-r, 0]){
      const yy = Math.max(0, Math.min(H - n, y + dy)), xx = Math.max(0, Math.min(W - n, x + dx));
      const m = take(S1, xx, yy) / k, v = take(S2, xx, yy) / k - m * m;
      if(v < best){ best = v; br = take(SR, xx, yy) / k; bg = take(SG, xx, yy) / k; bb = take(SB, xx, yy) / k; }
    }
    const i = (y * W + x) * 4;
    out[i] = br; out[i + 1] = bg; out[i + 2] = bb; out[i + 3] = src[i + 3];
  }
  return out;
}
/* Pfad's Painted look: flat brush areas (Kuwahara twice), the colour a little
   richer and warmer, a light canvas grain; the see-through parts kept, the
   outline the maker already draws. A filter over the render - it paints
   nothing new. strength 0.3-2 is the brush's size. */
function cgPaint(d, mask, W, H, strength){
  const k = Math.max(0, +strength || 0);
  if(!k) return;
  // the clear parts a mid colour first, so the brush drags no dark fringe in
  for(let i = 0; i < W * H; i++) if(!mask[i]){ d[i * 4] = 150; d[i * 4 + 1] = 135; d[i * 4 + 2] = 110; }
  const r = Math.max(2, Math.round(Math.min(W, H) / 160 * k)) + 1;
  let f = cgKuwahara(d, W, H, r);
  f = cgKuwahara(f, W, H, Math.max(1, r >> 1));
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const gw = Math.max(8, Math.floor(W / 3)), gh = Math.max(8, Math.floor(H / 3)), grain = new Float32Array(gw * gh);
  for(let i = 0; i < grain.length; i++) grain[i] = (236 + rnd() * 19) / 255;
  const sat = 1 + 0.12 * k;
  for(let y = 0; y < H; y++) for(let x = 0; x < W; x++){
    const i = y * W + x, p = i * 4;
    if(!mask[i]) continue;
    let R = f[p], G = f[p + 1], B = f[p + 2];
    const L0 = 0.299 * R + 0.587 * G + 0.114 * B;
    R = L0 + (R - L0) * sat; G = L0 + (G - L0) * sat; B = L0 + (B - L0) * sat;
    const g = grain[Math.min(gh - 1, Math.floor(y / 3)) * gw + Math.min(gw - 1, Math.floor(x / 3))] * 1.05;
    d[p] = R * g; d[p + 1] = G * (244 / 255) * g; d[p + 2] = B * (226 / 255) * g;
  }
}
/* The game's pieces, fetched once per mod and kept as images. */
function cgArt(name){
  const key = state.src + '|' + name;
  ARM.cgArt = ARM.cgArt || {};
  const hit = ARM.cgArt[key];
  if(hit) return hit.img && hit.img.complete && hit.img.naturalWidth ? hit.img : null;
  const img = new Image();
  ARM.cgArt[key] = {img};
  img.onload = () => cgRender();
  img.onerror = () => { ARM.cgArt[key] = {img: null};
    if(cg().ground.kind === name || name === 'PORTRAIT_FRAME'){ cg().groundNote = tt('cards.gen_art_missing'); cgRepaint(); } };
  img.src = '/api/armory/card_art?mod=' + enc(state.src) + '&name=' + enc(name);
  return null;
}
function cgGround(kind){ const c = cg(); c.ground.kind = kind; c.groundNote = ''; cgRepaint(); }
function cgFrameOn(on){ const c = cg(); c.gframe = on; c.groundNote = ''; cgRepaint(); }
function cgGroundFile(file){
  if(!file) return;
  const rd = new FileReader();
  rd.onload = () => { const c = cg(); c.ground.pic = rd.result; ARM.cgPic = null; cgRepaint(); };
  rd.readAsDataURL(file);
}
function cgGroundPic(){
  const c = cg();
  if(!c.ground.pic) return null;
  if(ARM.cgPic && ARM.cgPic.src === c.ground.pic) return ARM.cgPic.complete ? ARM.cgPic : null;
  ARM.cgPic = new Image(); ARM.cgPic.onload = () => cgRender(); ARM.cgPic.src = c.ground.pic;
  return null;
}
/* An image laid to cover w x h, its middle kept (on_ground's picture case). */
function cgCover(ctx, img, w, h){
  const k = Math.max(w / img.naturalWidth, h / img.naturalHeight), iw = img.naturalWidth * k, ih = img.naturalHeight * k;
  ctx.drawImage(img, (w - iw) / 2, (h - ih) / 2, iw, ih);
}
/* The finished card: the ground under the figure, the game's frame over it.
   The game's own cards are the figure alone (the game draws their ground),
   so None is the default and what the game expects. */
function cgCompose(cv){
  const c = cg(), w = cv.width, h = cv.height, g = c.ground.kind;
  const wantFrame = cgIsInfo() && c.gframe;
  if(g === 'none' && !wantFrame) return;
  const fig = document.createElement('canvas'); fig.width = w; fig.height = h;
  fig.getContext('2d').drawImage(cv, 0, 0);
  const x = cv.getContext('2d');
  x.clearRect(0, 0, w, h);
  if(g === 'colour'){ x.fillStyle = c.ground.colour; x.fillRect(0, 0, w, h); }
  else if(g === 'pic'){ const im = cgGroundPic(); if(im) cgCover(x, im, w, h); }
  else if(g === 'SCROLL_MID'){
    // the scroll paper repeated at its own size, as the game lays it (paper())
    const im = cgArt(g);
    if(im) for(let yy = 0; yy < h; yy += im.naturalHeight) for(let xx = 0; xx < w; xx += im.naturalWidth) x.drawImage(im, xx, yy);
  }else if(g !== 'none'){ const im = cgArt(g); if(im) cgCover(x, im, w, h); }
  x.drawImage(fig, 0, 0);
  if(wantFrame){
    const fr = cgArt('PORTRAIT_FRAME');
    if(fr) cgNineSlice(x, fr, w, h, cg().mult || 1);
  }
}
/* Pfad's framed(): the frame's four corners kept, its sides stretched along
   the picture, the border scaled with the picture. The border's width is a
   share of the frame (an eighth) unless the inner opening is known. */
function cgNineSlice(x, fr, W, H, scale){
  const fw = fr.naturalWidth, fh = fr.naturalHeight;
  const bx = Math.max(1, Math.floor(fw / 8)), by = Math.max(1, Math.floor(fh / 8));
  const sx = Math.min(bx * scale, Math.floor(W / 3)), sy = Math.min(by * scale, Math.floor(H / 3));
  const P = (a, b, c2, d, e, f, g, h2) => { if(g > 0 && h2 > 0) x.drawImage(fr, a, b, c2, d, e, f, g, h2); };
  P(0, 0, bx, by, 0, 0, sx, sy); P(fw - bx, 0, bx, by, W - sx, 0, sx, sy);
  P(0, fh - by, bx, by, 0, H - sy, sx, sy); P(fw - bx, fh - by, bx, by, W - sx, H - sy, sx, sy);
  P(bx, 0, fw - 2 * bx, by, sx, 0, W - 2 * sx, sy); P(bx, fh - by, fw - 2 * bx, by, sx, H - sy, W - 2 * sx, sy);
  P(0, by, bx, fh - 2 * by, 0, sy, sx, H - 2 * sy); P(fw - bx, by, bx, fh - 2 * by, W - sx, sy, sx, H - 2 * sy);
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

function cgKind(){ const s = cg().size; return cgIsInfo() ? 'info' : s === 'custom' ? 'custom' : 'card'; }
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
