const CG_SIZE_KEYS = {card:'cards.gen_size_card',large:'cards.gen_size_large',info:'cards.gen_size_info',custom:'cards.gen_size_custom',modcard:'cards.gen_size_modcard',modinfo:'cards.gen_size_modinfo'};
const CG_POSE_KEYS = {tpose:'cards.gen_pose_tpose',guard:'cards.gen_pose_guard',brace:'cards.gen_pose_brace',draw:'cards.gen_pose_draw',riding:'cards.gen_pose_riding',march:'cards.gen_pose_march',anim:'cards.gen_pose_anim',rig:'cards.gen_pose_rig'};
const CG_PART_KEYS = {whole:'cards.gen_part_whole',arms:'cards.gen_part_arms',legs:'cards.gen_part_legs',head:'cards.gen_part_head',posture:'cards.gen_part_posture'};
const CG_FRAME_KEYS = {whole:'cards.gen_frame_whole',knees:'cards.gen_frame_knees',thighs:'cards.gen_frame_thighs',waist:'cards.gen_frame_waist'};
const CG_GROUND_KEYS = {none:'cards.gen_ground_none',colour:'cards.gen_ground_colour',pic:'cards.gen_ground_pic',scroll:'cards.gen_ground_scroll',strat:'cards.gen_ground_strat',battle:'cards.gen_ground_battle'};
const CG_LIGHT_KEYS = {sun:'cards.gen_light_sun',point:'cards.gen_light_point'};
const CG_FINISH_KEYS = {blur:'cards.gen_blur',exposure:'cards.gen_exposure',brightness:'cards.gen_brightness',contrast:'cards.gen_contrast',gamma:'cards.gen_gamma',saturation:'cards.gen_saturation',hue:'cards.gen_hue',sharpen:'cards.gen_sharpen',outline:'cards.gen_outline'};
/* Armory unit-card and information-picture maker. Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor. */

const CG_WORK = {sizes: null, mod: null, library: null, rigs: {}, art: new Map(), serial: 0, draw: 0, handles: []};
function cg(){
  const defaults = {size:'card',mult:1,w:48,h:64,ss:10,oneEach:true,pose:'guard',name:'',unit:'',
    cam:{yaw:20,pitch:4,scale:1.2,height:0,pan:0},xf:{t:[0,0,0],r:[0,0,0]},
    rig:{type:'auto',basis:{},handles:true,cat:'',pick:'',part:'whole'},
    light:{type:'sun',azimuth:35,elevation:40,amount:0.95,level:1,ambient:0.38},
    post:{blur:0.5,exposure:0,brightness:0,contrast:1,gamma:1,saturation:1,hue:0,sharpen:0.2,outline:0.3},
    fit:{part:'thighs',auto:true},ground:{kind:'none',colour:'#5d4d36',pic:''},gframe:false,paint:{on:false,strength:1}};
  const c = state.cg = state.cg || {};
  for(const [key,value] of Object.entries(defaults)){
    if(c[key] == null) c[key] = value;
    else if(value && typeof value === 'object' && !Array.isArray(value)) for(const [n,v] of Object.entries(value)) if(c[key][n] == null) c[key][n] = v;
  }
  return c;
}
function cgHere(){ return state.mode === 'cards' && cardsSubNow() === 'generate'; }
function cgObjects(){
  const seen = new Set();
  return armProj().objects.filter(o => {
    if(o.hidden || armCollHidden(o)) return false;
    // one of each part per model: a horse's Body is not the rider's
    const key = (((o.src || [])[0] || {}).asset || '') + '|' + String(o.name || '').toLowerCase();
    if(cg().oneEach && seen.has(key)) return false;
    seen.add(key); return true;
  });
}
function cgDimensions(){
  const c = cg(), s = CG_WORK.sizes || {};
  const pair = {card:[48,64],large:[68,90],info:[180,230],custom:[Math.max(8,Number(c.w)||8),Math.max(8,Number(c.h)||8)],modcard:s.card,modinfo:s.info}[c.size] || [48,64];
  return pair.map(n => Math.max(8,Math.round(n * Math.max(1,Math.min(4,Number(c.mult)||1)))));
}
function cgIsInfo(){ return ['info','modinfo'].includes(cg().size); }
function cgRigType(){
  const r = cg().rig;
  if(r.type !== 'auto') return r.type;
  const name = armAnim().skel || '';
  return /dwarf|hobbit|halfling/i.test(name) ? 'dwarf' : /bow|archer/i.test(name) ? 'archer' : 'infantry';
}
function cgRigActive(){ return !!(cg().pose === 'rig' && CG_WORK.library && CG_WORK.library.rigs && CG_WORK.library.rigs[cgRigType()]); }
function cgRigLayout(){
  const type = cgRigType();
  if(!CG_WORK.rigs[type] && CG_WORK.library && CG_WORK.library.rigs[type]) CG_WORK.rigs[type] = crRig(CG_WORK.library.rigs[type]);
  return CG_WORK.rigs[type];
}
function cgRigPose(anim){
  const rig = cgRigLayout();
  if(!rig || !anim) return null;
  return crPoseOn(rig,crSolve(rig,cg().rig.basis,cgRigType()),anim);
}
async function renderCardGen(){
  const serial = ++CG_WORK.serial, mod = state.src;
  if(cgHere()) main.innerHTML = bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit')) + cardsSubTabsHtml() + `<div class="armempty">${tt('armory.reading')}</div>`;
  try{
    await armEnsureLoaded(); await ARM.loading;
    const reads = [];
    if(CG_WORK.mod !== mod){
      CG_WORK.mod = mod; CG_WORK.sizes = null;
      reads.push(api.get('/api/armory/card_sizes?mod=' + enc(mod)).then(r => { if(CG_WORK.mod === mod) CG_WORK.sizes = r; }).catch(() => {}));
    }
    if(!CG_WORK.library) reads.push(api.get('/api/armory/poses').then(r => { CG_WORK.library = r; }).catch(() => {}));
    await Promise.all(reads);
    if(serial !== CG_WORK.serial || !cgHere() || state.src !== mod) return;
    if(cg().fit.auto) CG_WORK.fit = null;
    if(cgObjects().length) await cgPreparePose();
    if(serial !== CG_WORK.serial || !cgHere() || state.src !== mod) return;
    cgPaint();
  }catch(e){ if(cgHere() && serial === CG_WORK.serial){ cg().err = errText(e); cgPaint(); } }
}
function cgSelectHtml(group, key, choices){
  const value = group ? cg()[group][key] : cg()[key];
  return `<select onchange="cgSet('${group}','${key}',this.value,true)">${choices.map(([v,l]) => `<option value="${esc(v)}"${String(value) === String(v) ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
}
function cgCheckHtml(group,key,label){
  const value = group ? cg()[group][key] : cg()[key];
  return `<label class="armcheck"><input type="checkbox" ${value ? 'checked' : ''} onchange="cgSet('${group}','${key}',this.checked,true)">${tt(label)}</label>`;
}
function cgRange(group,key,label,min,max,step){
  const value = cg()[group][key];
  return `<label class="cgrange"><span>${tt(label)}</span><input type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-cg-group="${group}" data-cg-key="${key}" oninput="cgSet('${group}','${key}',+this.value,false)"><span id="cgv_${group}_${key}">${value}</span></label>`;
}
function cgSizeHtml(){
  const c = cg(), sizes = CG_WORK.sizes || {};
  return `<fieldset><legend>${tt('cards.gen_size')}</legend>${['card','large','info','custom','modcard','modinfo'].map(k => {
    const unavailable = k === 'modcard' && !sizes.card || k === 'modinfo' && !sizes.info;
    return `<label title="${k.startsWith('mod') ? ttA('cards.gen_size_mod_title') : ''}"><input type="radio" name="cgSize" value="${k}" ${c.size === k ? 'checked' : ''} ${unavailable ? 'disabled' : ''} onchange="cgSet('','size',this.value,true)">${tt(CG_SIZE_KEYS[k])} ${unavailable ? tt('cards.gen_size_mod_none') : ''}</label>`;
  }).join('')}
    ${c.size === 'custom' ? `<div class="armexprow"><input class="armnum" type="number" min="8" value="${c.w}" onchange="cgSet('','w',Math.max(8,+this.value),true)"> × <input class="armnum" type="number" min="8" value="${c.h}" onchange="cgSet('','h',Math.max(8,+this.value),true)"></div>` : ''}
    <label title="${ttA('cards.gen_mult_title')}">${tt('cards.gen_mult')} ${cgSelectHtml('','mult',[1,2,3,4].map(n => [n,String(n)]))}</label>
    <label>${tt('cards.gen_render_at')} ${cgSelectHtml('','ss',[10,15,20,25,30,35,40].map(n => [n,String(n) + '×']))}</label></fieldset>`;
}
function cgPoseHtml(){
  const c = cg(), a = armAnim(), entries = armAnimEntries(), skels = a.list && a.list.skeletons || {};
  const actions = (skels[a.skel.toLowerCase()] || {}).actions || [];
  return `<fieldset><legend>${tt('cards.gen_pose')}</legend>${cgSelectHtml('','pose',['tpose','guard','brace','draw','riding','march','anim','rig'].map(x => [x,tt(CG_POSE_KEYS[x])]))}
    <select onchange="cgEntry(this.value)"><option value="">${tt('cards.gen_pick_entry')}</option>${entries.map(e => `<option value="${esc(armAssetKey(e))}"${(armProj().anim || {}).asset === armAssetKey(e) ? ' selected' : ''}>${esc(armAssetLabel(e))}</option>`).join('')}</select>
    ${Object.keys(skels).length ? `<select onchange="cgSkeleton(this.value)">${Object.keys(skels).map(s => `<option value="${esc(s)}"${s === a.skel.toLowerCase() ? ' selected' : ''}>${esc(s)}</option>`).join('')}</select>` : ''}
    ${c.pose === 'anim' ? `<select onchange="cgAction(this.value)">${actions.filter(x => x.playable).map(x => { const key = x.slot != null ? String(x.slot) : 'a:' + x.action; return `<option value="${esc(key)}"${a.key === key ? ' selected' : ''}>${esc(x.action)}</option>`; }).join('')}</select><input type="range" min="0" max="1000" value="${armAnimFrac()}" oninput="cgScrub(+this.value)">` : ''}
    <div class="count">${esc(c.poseNote || '')}</div><div class="count">${esc(c.poseNote2 || '')}</div>
    ${c.pose === 'rig' ? cgRigHtml() : ''}</fieldset>`;
}
function cgRigHtml(){
  const r = cg().rig, lib = CG_WORK.library || {poses:[]}, categories = [...new Set((lib.poses || []).map(p => p.c))].sort();
  if(!categories.includes(r.cat)) r.cat = categories[0] || '';
  return `<div class="cgrig"><label>${tt('cards.gen_rig')} ${cgSelectHtml('rig','type',[['auto',tt('cards.gen_rig_auto',{rig:cgRigType()})],...['infantry','archer','dwarf'].map(t => [t,t])])}</label>
    <label class="armcheck" title="${ttA('cards.gen_two_hands_title')}"><input type="checkbox" ${((r.basis.Switch || {}).l || [0,0])[1] > 0 ? 'checked' : ''} onchange="cgTwoHands(this.checked)">${tt('cards.gen_two_hands')}</label>
    ${cgCheckHtml('rig','handles','cards.gen_handles')}<button class="mini" onclick="cg().rig.basis={};cgFitChanged();cgPaint()">${tt('cards.gen_rig_reset')}</button>
    <p class="count">${tt('cards.gen_rig_on',{rig:cgRigType(),skeleton:esc(armAnim().skel)})}</p><p class="count">${tt('cards.gen_rig_hint')}</p>
    <h4>${tt('cards.gen_library')}</h4><p class="count">${ttN('cards.gen_library_note',(lib.poses || []).length)}</p>
    ${cgSelectHtml('rig','cat',categories.map(x => [x,x]))}<label>${tt('cards.gen_apply_to')} ${cgSelectHtml('rig','part',['whole','arms','legs','head','posture'].map(x => [x,tt(CG_PART_KEYS[x])]))}</label>
    <div class="cgposes">${(lib.poses || []).map((p,i) => p.c === r.cat ? `<button class="mini${r.pick === p.n ? ' on' : ''}" onclick="cgLibraryPose(${i})">${esc(p.n)}</button>` : '').join('')}</div></div>`;
}
function cgCameraHtml(){
  return `<fieldset><legend>${tt('cards.gen_camera')}</legend>${[['yaw','cards.gen_turn',-180,180,1],['pitch','cards.gen_tilt',-30,45,1],['scale','cards.gen_ortho_scale',0.4,3,0.05],['height','cards.gen_height',-1.5,1.5,0.02]].map(x => cgRange('cam',...x)).join('')}
    <label title="${ttA('cards.gen_framing_hint')}">${tt('cards.gen_framing')} ${cgSelectHtml('fit','part',['whole','knees','thighs','waist'].map(x => [x,tt(CG_FRAME_KEYS[x])]))}</label>
    ${cgCheckHtml('fit','auto','cards.gen_fit_auto')}
    <button class="mini" id="cgReset" ${cgPlacementReset() ? 'disabled' : ''} onclick="cg().xf={t:[0,0,0],r:[0,0,0]};cg().cam.pan=0;cgPaint()">${tt('cards.gen_place_reset')}</button><p class="count">${tt('cards.gen_view_hint')}</p></fieldset>`;
}
function cgGroundHtml(){
  const c = cg();
  const choices = ['none','colour','pic',...(cgIsInfo() ? ['scroll'] : ['strat','battle'])];
  return `<fieldset><legend>${tt('cards.gen_ground')}</legend>${cgSelectHtml('ground','kind',choices.map(x => [x,tt(CG_GROUND_KEYS[x])]))}
    ${c.ground.kind === 'colour' ? `<input type="color" value="${esc(c.ground.colour)}" oninput="cgSet('ground','colour',this.value,false)">` : ''}
    ${c.ground.kind === 'pic' ? `<label class="btn">${tt('cards.gen_ground_pick')}<input type="file" accept="image/*" onchange="cgPickGround(this.files[0])"></label>` : ''}
    <p class="count">${tt('cards.gen_ground_none_note')}</p>${cgIsInfo() ? cgCheckHtml('','gframe','cards.gen_game_frame') : ''}</fieldset>`;
}
function cgLightHtml(){
  const c = cg();
  return `<fieldset><legend>${tt('cards.gen_light')}</legend><div>${['sun','point'].map(x => `<label><input type="radio" name="cgLight" ${c.light.type === x ? 'checked' : ''} onchange="cgSet('light','type','${x}',false)">${tt(CG_LIGHT_KEYS[x])}</label>`).join('')}</div>
    ${[['azimuth','cards.gen_azimuth',-180,180,1],['elevation','cards.gen_elevation',-60,89,1],['amount','cards.gen_amount',0,2,0.01],['level','cards.gen_level',0.2,2.5,0.01],['ambient','cards.gen_ambient',0,1,0.01]].map(x => cgRange('light',...x)).join('')}</fieldset>`;
}
function cgFinishHtml(){
  return `<fieldset><legend>${tt('cards.gen_painted')}</legend>${cgCheckHtml('paint','on','cards.gen_painted_on')}
    <div title="${ttA('cards.gen_painted_title')}">${cgRange('paint','strength','cards.gen_painted_strength',0.3,2,0.05)}</div></fieldset>
    <fieldset><legend>${tt('cards.gen_finish')}</legend>${[['blur',0,2,0.05],['exposure',-2,2,0.05],['brightness',-0.5,0.5,0.01],['contrast',0.3,2,0.01],['gamma',0.3,3,0.01],['saturation',0,2,0.01],['hue',-180,180,1],['sharpen',0,1,0.01],['outline',0,1.5,0.05]].map(([k,...range]) => cgRange('post',k,CG_FINISH_KEYS[k],...range)).join('')}</fieldset>`;
}
function cgPaint(){
  if(!cgHere()) return;
  const c = cg(), objects = cgObjects();
  const nav = bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit')) + cardsSubTabsHtml();
  if(!objects.length){ main.innerHTML = nav + `<div class="armempty">${tt('cards.gen_no_model')}<br><button class="btn" onclick="setAppMode('armory')">${tt('core.armory_studio')}</button></div>`; return; }
  const [w,h] = cgDimensions(), ss = Math.min(Number(c.ss),4096/Math.max(w,h)), hw = Math.min(4096,Math.round(w*ss)), hh = Math.min(4096,Math.round(h*ss));
  main.innerHTML = nav + `<div class="cggrid"><div class="cgctl"><div class="count">${ttN('cards.gen_source',objects.length)}</div>
    ${cgCheckHtml('','oneEach','cards.gen_one_each')}${cgSizeHtml()}${cgPoseHtml()}${cgCameraHtml()}${cgGroundHtml()}${cgLightHtml()}${cgFinishHtml()}
    <fieldset><legend>${tt('cards.gen_name')}</legend><input value="${esc(c.name)}" placeholder="${ttA('cards.gen_name_hint')}" oninput="cg().name=this.value">
    <div class="armexprow"><button class="primary" onclick="cgSave(false)">${tt('cards.gen_save')}</button><button onclick="cgSave(true)">${tt('cards.gen_save_hd')}</button></div>
    <div id="cgSaveResult">${cgSavedHtml()}</div></fieldset><div class="armexperr" id="cgError">${esc(c.err || '')}</div></div>
    <div class="cgout"><div class="cghd"><span class="count">${tt('cards.gen_hd',{w:hw,h:hh})}</span><div class="cghdview" id="cgHdView"><canvas id="cgHd" tabindex="0" width="${hw}" height="${hh}"></canvas><canvas id="cgHdUi"></canvas></div></div>
    <div class="cgcard"><span class="count">${tt('cards.gen_card',{w,h})}</span><canvas id="cgCard" width="${w}" height="${h}" style="image-rendering:pixelated;width:${w*3}px;max-width:100%;height:auto"></canvas></div></div></div>`;
  cgWire(); cgDraw();
}
function cgPlacementReset(){ const c = cg(); return !c.cam.pan && [...c.xf.t,...c.xf.r].every(v => !v); }
function cgSet(group,key,value,redraw){
  const c = cg(); (group ? c[group] : c)[key] = value;
  const out = document.getElementById('cgv_' + group + '_' + key); if(out) out.textContent = value;
  if(!group && ['size','w','h','mult','oneEach'].includes(key) || group === 'fit') cgFitChanged();
  if(group === 'fit' && key === 'part') CG_WORK.fit = null;
  if(group === 'rig' && key === 'type') cgFitChanged();
  if(!group && key === 'size' && (cgIsInfo() ? ['strat','battle'].includes(c.ground.kind) : c.ground.kind === 'scroll')) c.ground.kind = 'none';
  if(key === 'pose') cgPreparePose().then(() => { cgFitChanged(); cgPaint(); }).catch(e => { c.err = errText(e); cgPaint(); });
  else if(redraw) cgPaint(); else cgDraw();
}
function cgFitChanged(){ if(cg().fit.auto) CG_WORK.fit = null; }
async function cgEntry(key){ await armAnimFrom(key); await cgPreparePose(); cgFitChanged(); cgPaint(); }
async function cgSkeleton(name){ armAnimSkel(name); await cgPreparePose(); cgFitChanged(); cgPaint(); }
async function cgAction(key){ await armAnimPick(key); armAnim().playing = false; cgFitChanged(); cgPaint(); }
function cgScrub(value){ const a = armAnim(); a.playing = false; a.t = armAnimLength()*value/1000; cgFitChanged(); cgDraw(); }
async function cgPreparePose(){
  const c = cg(), a = armAnim(); c.poseNote = ''; c.poseNote2 = '';
  if(c.pose === 'tpose'){ armAnimRest(); a.playing = false; return; }
  // a rider and his horse both loaded: Riding is the rider's action, on the horse
  if(c.pose === 'riding'){ const rider = await armAnimRider(); if(rider && (armProj().anim || {}).asset !== armAssetKey(rider)) await armAnimFrom(armAssetKey(rider)); }
  if(!a.list){ const entry = armAnimEntries()[0]; if(entry) await armAnimFrom(armAssetKey(entry)); }
  if(!a.list){ c.poseNote = tt('cards.gen_no_entry'); return; }
  const skels = a.list.skeletons || {};
  const presets = {guard:[['stand_a_idle','stand_idle','idle'],0.3],brace:[['ready','ready_hf_idle_1'],0.3],draw:[['attack_missile_hold','attack_missile_ready'],0.5],riding:[['stand_a_idle','ready'],0.3],march:[['walk','march'],0.25]};
  let selected = null, skeleton = a.skel;
  if(c.pose === 'anim' && a.data){ a.playing = false; return; }
  const names = Object.keys(skels).sort((x,y) => {
    if(c.pose === 'riding') return Number(/mount|cavalry|horse/i.test(y))-Number(/mount|cavalry|horse/i.test(x));
    return Number(y === a.skel.toLowerCase())-Number(x === a.skel.toLowerCase());
  });
  for(const sk of names){
    const actions = (skels[sk].actions || []).filter(x => x.playable);
    if(presets[c.pose]) for(const name of presets[c.pose][0]){ selected = actions.find(x => x.action.toLowerCase() === name); if(selected) break; }
    else selected = actions.find(x => String(x.slot != null ? x.slot : 'a:' + x.action) === a.key) || actions[0];
    if(selected){ skeleton = sk; break; }
  }
  if(!selected){ armAnimRest(); c.poseNote = tt('cards.gen_pose_missing',{pose:tt(CG_POSE_KEYS[c.pose])}); return; }
  if(skeleton !== a.skel) armAnimSkel(skeleton);
  const key = selected.slot != null ? String(selected.slot) : 'a:' + selected.action;
  if(a.key !== key || !a.data) await armAnimPick(key);
  a.playing = false; a.tpose = false;
  if(presets[c.pose]) a.t = armAnimLength()*presets[c.pose][1];
  c.poseNote = tt('cards.gen_pose_from',{action:selected.action,skeleton});
  if(c.pose === 'riding' && !a.carried && !/mount|cavalry|horse/i.test(skeleton)) c.poseNote2 = tt('cards.gen_pose_no_mount');
}
function cgTwoHands(on){
  const basis = cg().rig.basis; basis.Switch = {...basis.Switch,l:[0,on ? 0.05 : 0,0]}; cgFitChanged(); cgDraw();
}
function cgLibraryPose(index){ const p = CG_WORK.library.poses[index], r = cg().rig; r.basis = crApply(r.basis,p,r.part); r.pick = p.n; cgFitChanged(); cgPaint(); }
function cgCanvas(w,h){ const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h; return canvas; }
function cgBounds(objects){
  let b = armBounds(objects);
  const a = armAnim();
  if(a.data){
    const lo = [Infinity,Infinity,Infinity], hi = [-Infinity,-Infinity,-Infinity];
    for(const o of objects){ const g = a.geos.get(o.id); if(!g || !g.posed) continue; const p = g.outPos;
      for(let i=0;i<p.length;i+=3) for(let k=0;k<3;k++){ lo[k]=Math.min(lo[k],p[i+k]); hi[k]=Math.max(hi[k],p[i+k]); }
    }
    if(isFinite(lo[0])) b = [lo,hi];
  }
  return b || [[-0.5,0,-0.5],[0.5,2,0.5]];
}
function cgMatrixPoint(m,p){ return [0,1,2].map(k => m[k]*p[0]+m[k+4]*p[1]+m[k+8]*p[2]+m[k+12]); }
function cgCamera(objects,w,h){
  const c = cg(), [lo,hi] = cgBounds(objects), center = lo.map((v,i) => (v+hi[i])/2);
  const r = c.xf.r, t = c.xf.t;
  const pre = armMul(armTrans(center[0]+t[0],center[1]+t[1],center[2]+t[2]),armMul(armRot(...r),armTrans(-center[0],-center[1],-center[2])));
  if(!CG_WORK.fit){
    const fraction = {whole:1,knees:0.78,thighs:0.64,waist:0.5}[c.fit.part] || 1;
    const height = Math.max(0.1,hi[1]-lo[1]);
    CG_WORK.fit = {height:Math.max(height*fraction*1.12,(hi[0]-lo[0])*h/w*1.12),target:[-center[0],hi[1]-height*fraction/2,center[2]]};
  }
  const fit = CG_WORK.fit, height = fit.height * c.cam.scale, width = height*w/h;
  const target = [...fit.target]; target[0] += c.cam.pan; target[1] += c.cam.height;
  const yaw = c.cam.yaw*Math.PI/180, pitch = c.cam.pitch*Math.PI/180, dist = 10;
  const eye = [target[0]+dist*Math.cos(pitch)*Math.sin(yaw),target[1]+dist*Math.sin(pitch),target[2]+dist*Math.cos(pitch)*Math.cos(yaw)];
  const proj = [2/width,0,0,0,0,2/height,0,0,0,0,-0.01,0,0,0,0,1];
  return {proj,view:v3LookAt(eye,target,[0,1,0]),eye,pre,height,width,target};
}
function cgLight(camera){
  const c = cg(), l = c.light, az = (Number(l.azimuth)+Number(c.cam.yaw))*Math.PI/180, el = l.elevation*Math.PI/180;
  const dir = [Math.sin(az)*Math.cos(el),Math.sin(el),Math.cos(az)*Math.cos(el)];
  return {...l,point:l.type === 'point',dir,pos:camera.target.map((v,i) => v+dir[i]*4)};
}
async function cgDraw(){
  if(!cgHere()) return;
  const token = ++CG_WORK.draw, hd = document.getElementById('cgHd'), card = document.getElementById('cgCard');
  if(!hd || !card) return;
  const c = cg(), objects = cgObjects(), w = hd.width, h = hd.height;
  try{
    armAnimPose(objects);
    const camera = cgCamera(objects,w,h); CG_WORK.camera = camera;
    const options = {plain:true,card:true,pre:camera.pre,light:cgLight(camera),bg:[0,0,0]};
    if(!armRender(objects,w,h,camera,options)) return;
    const ctx = hd.getContext('2d',{willReadFrequently:true}); ctx.clearRect(0,0,w,h); ctx.drawImage(ARM.glCanvas,0,0,w,h,0,0,w,h);
    const image = ctx.getImageData(0,0,w,h);
    armRender(objects,w,h,camera,{...options,mask:true});
    const maskCanvas = cgCanvas(w,h), maskCtx = maskCanvas.getContext('2d',{willReadFrequently:true});
    maskCtx.drawImage(ARM.glCanvas,0,0,w,h,0,0,w,h);
    const mask = maskCtx.getImageData(0,0,w,h).data, alpha = new Uint8Array(w*h);
    for(let i=0;i<alpha.length;i++){ alpha[i] = mask[i*4] > 0 ? 1 : 0; image.data[i*4+3] = mask[i*4]; }
    if(c.paint.on) cgPaintPixels(image.data,w,h,c.paint.strength);
    ctx.putImageData(image,0,0);
    if(c.post.outline > 0){
      const grown = cgDilate(alpha,w,h,c.post.outline*w/card.width), outline = ctx.createImageData(w,h);
      for(let i=0;i<grown.length;i++) outline.data[i*4+3] = grown[i] ? 255 : 0;
      maskCtx.putImageData(outline,0,0); maskCtx.drawImage(hd,0,0); ctx.clearRect(0,0,w,h); ctx.drawImage(maskCanvas,0,0);
    }
    cgOverlay();
    const reduced = cgCanvas(card.width,card.height), small = reduced.getContext('2d',{willReadFrequently:true});
    small.filter = c.post.blur ? ['blur(',c.post.blur,'px)'].join('') : 'none'; small.drawImage(hd,0,0,card.width,card.height); small.filter = 'none';
    const pixels = small.getImageData(0,0,card.width,card.height); cgFinish(pixels.data,card.width,card.height,c.post); small.putImageData(pixels,0,0);
    const ground = await cgGroundImage(c.ground.kind), frame = cgIsInfo() && c.gframe ? await cgArt('PORTRAIT_FRAME') : null;
    if(token !== CG_WORK.draw || !cgHere() || document.getElementById('cgCard') !== card) return;
    const dst = card.getContext('2d'); dst.clearRect(0,0,card.width,card.height);
    if(c.ground.kind === 'colour'){ dst.fillStyle = c.ground.colour; dst.fillRect(0,0,card.width,card.height); }
    if(ground){
      if(c.ground.kind === 'scroll'){ dst.fillStyle = dst.createPattern(ground,'repeat'); dst.fillRect(0,0,card.width,card.height); }
      else cgCover(dst,ground,card.width,card.height);
    }
    dst.drawImage(reduced,0,0);
    if(frame) cgFrame(dst,frame,card.width,card.height);
    const error = document.getElementById('cgError'); if(error) error.textContent = c.err || (CG_WORK.artMissing ? tt('cards.gen_art_missing') : '');
  }catch(e){ c.err = errText(e); const error = document.getElementById('cgError'); if(error) error.textContent = c.err; }
}
// A square maximum filter with two sliding windows, so large HD outlines stay linear.
function cgDilate(mask,w,h,radius){
  const r = Math.max(0,Math.ceil(radius)), temp = new Uint8Array(w*h), out = new Uint8Array(w*h);
  for(let y=0;y<h;y++){
    let sum=0; for(let x=0;x<=Math.min(r,w-1);x++) sum += !!mask[y*w+x];
    for(let x=0;x<w;x++){ temp[y*w+x]=sum>0; if(x-r>=0) sum-=!!mask[y*w+x-r]; if(x+r+1<w) sum+=!!mask[y*w+x+r+1]; }
  }
  for(let x=0;x<w;x++){
    let sum=0; for(let y=0;y<=Math.min(r,h-1);y++) sum+=temp[y*w+x];
    for(let y=0;y<h;y++){ out[y*w+x]=sum>0; if(y-r>=0) sum-=temp[(y-r)*w+x]; if(y+r+1<h) sum+=temp[(y+r+1)*w+x]; }
  }
  return out;
}
function cgFinish(data,w,h,post){
  const p = {exposure:0,brightness:0,contrast:1,gamma:1,saturation:1,hue:0,sharpen:0,...post};
  const angle = p.hue*Math.PI/180, co = Math.cos(angle), si = Math.sin(angle), gain = Math.pow(2,p.exposure);
  for(let i=0;i<data.length;i+=4){
    if(!data[i+3]) continue;
    let rgb = [data[i],data[i+1],data[i+2]].map(v => Math.pow(Math.max(0,((v/255*gain+p.brightness)-0.5)*p.contrast+0.5),1/p.gamma));
    const grey = rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
    rgb = rgb.map(v => grey+(v-grey)*p.saturation);
    if(p.hue){
      const [r,g,b] = rgb, y=0.299*r+0.587*g+0.114*b, u=0.596*r-0.274*g-0.322*b, v=0.211*r-0.523*g+0.312*b;
      const U=u*co-v*si,V=u*si+v*co; rgb=[y+0.956*U+0.621*V,y-0.272*U-0.647*V,y-1.106*U+1.703*V];
    }
    for(let k=0;k<3;k++) data[i+k]=Math.max(0,Math.min(255,Math.round(rgb[k]*255)));
  }
  if(p.sharpen){
    const src = new Uint8ClampedArray(data);
    for(let y=1;y<h-1;y++) for(let x=1;x<w-1;x++){
      const i=(y*w+x)*4; if(!src[i+3]) continue;
      const neighbors=[i-4,i+4,i-w*4,i+w*4].filter(j => src[j+3]);
      for(let k=0;k<3;k++){ const mean=neighbors.reduce((sum,j) => sum+src[j+k],0)/(neighbors.length || 1); if(neighbors.length) data[i+k]=src[i+k]+p.sharpen*(src[i+k]-mean); }
    }
  }
}
function cgPaintPixels(data,w,h,strength){
  const src = new Uint8ClampedArray(data), s = Number(strength), quantum = 12+s*14;
  for(let y=0;y<h;y++) for(let x=0;x<w;x++){
    const i=(y*w+x)*4; if(!src[i+3]) continue;
    const grain = (Math.sin(x*12.9898+y*78.233)*43758.5453)%1;
    for(let k=0;k<3;k++){
      let total=src[i+k]*2, count=2;
      for(const [dx,dy] of [[-2,0],[2,0],[0,-2],[0,2]]){
        const xx=x+dx,yy=y+dy; if(xx<0||xx>=w||yy<0||yy>=h) continue;
        const j=(yy*w+xx)*4; if(src[j+3] && Math.abs(src[j+k]-src[i+k])<35){ total+=src[j+k];count++; }
      }
      const value=total/count, flat=Math.round(value/quantum)*quantum;
      data[i+k]=value+(flat-value)*Math.min(0.8,s*0.4)+(k===0 ? 4 : k===2 ? -3 : 1)*s+grain*s*2;
    }
  }
}
function cgLoadImage(url){ return new Promise((resolve,reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = url; }); }
async function cgArt(name){
  const key = state.src + '|' + name;
  if(!CG_WORK.art.has(key)) CG_WORK.art.set(key,cgLoadImage(`/api/armory/card_art?mod=${enc(state.src)}&name=${enc(name)}`).catch(() => { CG_WORK.artMissing = true; return null; }));
  const result = await CG_WORK.art.get(key); if(!result) CG_WORK.artMissing = true; return result;
}
async function cgGroundImage(kind){
  CG_WORK.artMissing = false;
  if(kind === 'pic' && cg().ground.pic){ try{ return await cgLoadImage(cg().ground.pic); }catch(e){ return null; } }
  const art = {strat:'STRAT_CARD_BACKGROUND',battle:'BATTLE_CARD_BACKGROUND',scroll:'SCROLL_MID'}[kind];
  return art ? cgArt(art) : null;
}
function cgCover(ctx,image,w,h){ const scale = Math.max(w/image.width,h/image.height); ctx.drawImage(image,(w-image.width*scale)/2,(h-image.height*scale)/2,image.width*scale,image.height*scale); }
function cgFrame(ctx,image,w,h){
  // Nine slices keep the original corners and repeatable border recognisable.
  const sx=Math.max(1,Math.floor(image.width/4)),sy=Math.max(1,Math.floor(image.height/4));
  const dx=Math.min(sx,w/3),dy=Math.min(sy,h/3),xs=[0,sx,image.width-sx,image.width],ys=[0,sy,image.height-sy,image.height],xd=[0,dx,w-dx,w],yd=[0,dy,h-dy,h];
  for(let y=0;y<3;y++) for(let x=0;x<3;x++) if(x!==1 || y!==1) ctx.drawImage(image,xs[x],ys[y],xs[x+1]-xs[x],ys[y+1]-ys[y],xd[x],yd[y],xd[x+1]-xd[x],yd[y+1]-yd[y]);
}
function cgPickGround(file){
  if(!file) return; const c = cg(), r = new FileReader();
  r.onload = () => { if(state.cg === c){ c.ground.pic = String(r.result); cgDraw(); } }; r.onerror = () => toast(errText(r.error)); r.readAsDataURL(file);
}
function cgSavedHtml(){
  const c = cg(), s = c.saved; if(!s) return '';
  const p = c.givePlan;
  return `<p class="ok">${tt('cards.gen_saved',{path:esc(s.path)})}</p><label>${tt('cards.gen_unit')}<input list="cgUnits" value="${esc(c.unit)}" oninput="cg().unit=this.value;cg().givePlan=null"></label>
    <datalist id="cgUnits">${(c.units || []).map(u => `<option value="${esc(u)}"></option>`).join('')}</datalist><button onclick="cgGive(false)">${tt('cards.gen_give')}</button>
    ${p ? (p.errors || []).length ? p.errors.map(e => `<div class="armissue">${esc(e)}</div>`).join('') : (p.changes || []).map(e => `<div>${esc(e)}</div>`).join('') + (p.warnings || []).map(e => `<div class="w-warn">${esc(e)}</div>`).join('') + `<button class="primary" onclick="cgGive(true)">${tt('cards.gen_give_apply')}</button>` : ''}`;
}
async function cgSave(hd){
  const c = cg(), name = c.name.trim(), mod = state.src;
  if(!name){ toast(tt('cards.gen_name_first')); return; }
  const canvas = document.getElementById(hd ? 'cgHd' : 'cgCard'); if(!canvas) return;
  try{
    await cgDraw();
    const kind = hd ? 'hd' : cgIsInfo() ? 'info' : c.size === 'custom' ? 'custom' : 'card';
    const r = await api.post('/api/armory/cards/save',{name,kind,size:[canvas.width,canvas.height],png:canvas.toDataURL('image/png')});
    if(r.error) throw new Error(r.error);
    if(hd){ toast(tt('cards.gen_saved',{path:r.path})); return; }
    if(state.cg !== c) return;
    c.saved = r; c.givePlan = null; c.units = [];
    try{ const units = await api.get('/api/armory/templates?mod=' + enc(mod)); c.units = (units.units || []).map(u => u.type); }catch(e){ c.units = []; }
    if(cgHere() && state.src === mod && state.cg === c) cgPaint();
  }catch(e){ c.err = errText(e); const el = document.getElementById('cgError'); if(el) el.textContent = c.err; }
}
async function cgGive(apply){
  const c = cg();
  if(!c.saved || !c.unit.trim()){ toast(tt('cards.gen_unit_first')); return; }
  const body = {mod:state.src,unit:c.unit.trim(),[c.saved.kind === 'info' ? 'info_src' : 'card_src']:c.saved.path};
  if(apply && (!c.givePlan || (c.givePlan.errors || []).length || CG_WORK.giveBody !== JSON.stringify(body))) return;
  try{
    const r = await api.post('/api/edit/' + (apply ? 'apply' : 'plan'),body); if(r.error) throw new Error(r.error);
    if(apply){ toast(tt('cards.gen_given',{unit:body.unit})); c.givePlan = null; }
    else{ c.givePlan = r; CG_WORK.giveBody = JSON.stringify(body); }
    if(state.cg === c && cgHere()) cgPaint();
  }catch(e){ toast(errText(e)); }
}
function cgScreenPoint(p){
  const camera = CG_WORK.camera, hd = document.getElementById('cgHd');
  const world = cgMatrixPoint(camera.pre,p); world[0] = -world[0];
  const clip = cgMatrixPoint(armMul(camera.proj,camera.view),world);
  return [(clip[0]+1)*hd.width/2,(1-clip[1])*hd.height/2];
}
function cgOverlay(){
  const overlay = document.getElementById('cgHdUi'), hd = document.getElementById('cgHd');
  if(!overlay || !hd) return;
  const box = hd.getBoundingClientRect(), host = document.getElementById('cgHdView').getBoundingClientRect();
  const scale = Math.min(box.width/hd.width,box.height/hd.height);
  const width = hd.width*scale,height = hd.height*scale;
  Object.assign(overlay.style,{left:(box.left-host.left+(box.width-width)/2)+'px',top:(box.top-host.top+(box.height-height)/2)+'px',width:width+'px',height:height+'px'});
  overlay.width = hd.width; overlay.height = hd.height;
  CG_WORK.handles = [];
  if(!cgRigActive() || !cg().rig.handles || !armAnim().data) return;
  const rig = cgRigLayout(), W = crSolve(rig,cg().rig.basis,cgRigType()), anim = armAnim().data;
  const pelvis = rig.bones.findIndex(b => b.c === 'm' && /pelvis/i.test(b.n));
  const ai = anim.bones.findIndex(b => /pelvis/i.test(b.name));
  const bind = armAnim().bind, origin = ai >= 0 && bind ? bind[ai] : [0,0,0];
  const rest = pelvis >= 0 ? crPos(rig.bones[pelvis].m) : [0,0,0];
  const controlNames = ['IK Pelvis','IK Torso Controller','IK Head','IK frist right','IK frist  left','IK angle right','IK angle left','IK elbow right','IK elbow left','IK knee right','IK knee left'];
  for(const name of controlNames){
    const i = rig.byName.get(name); if(i === undefined) continue;
    const p = crPos(W[i]), delta = [p[0]-rest[0],p[2]-rest[2],p[1]-rest[1]];
    const game = delta.map((v,k) => v+origin[k]), point = cgScreenPoint(game);
    CG_WORK.handles.push({name,i,point,W});
  }
  const ctx = overlay.getContext('2d'), radius = Math.max(6,hd.width/90);
  const pref = typeof look === 'function' ? look() : {};
  ctx.lineWidth = Math.max(1,hd.width/400); ctx.globalAlpha = 0.85;
  for(const side of ['left','right']) for(const pair of [['elbow','frist'],['knee','angle']]){
    const a = CG_WORK.handles.find(x => x.name.includes(pair[0]) && x.name.includes(side)), b = CG_WORK.handles.find(x => x.name.includes(pair[1]) && x.name.includes(side));
    if(a && b){ ctx.strokeStyle = side === 'left' ? '#58aaff' : '#ff7766'; ctx.beginPath(); ctx.moveTo(...a.point); ctx.lineTo(...b.point); ctx.stroke(); }
  }
  for(const h of CG_WORK.handles){
    const [x,y] = h.point, active = h.name === CG_WORK.hover;
    const r = radius*(active ? 1.3 : 1);
    ctx.fillStyle = /left/.test(h.name) ? '#58aaff' : /right/.test(h.name) ? '#ff7766' : (pref.colours || {}).accent || '#f4ce61';
    ctx.strokeStyle = active ? '#fff' : '#181818'; ctx.beginPath();
    if(/elbow|knee/.test(h.name)){ ctx.moveTo(x,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x,y+r); ctx.lineTo(x-r,y); ctx.closePath(); }
    else if(/angle/.test(h.name)) ctx.rect(x-r,y-r*0.6,r*2,r*1.2);
    else ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fill(); ctx.stroke();
  }
}
function cgPointerPoint(event){
  const hd = document.getElementById('cgHd'), box = hd.getBoundingClientRect();
  const s = Math.min(box.width/hd.width,box.height/hd.height);
  return [(event.clientX-box.left-(box.width-hd.width*s)/2)/s,(event.clientY-box.top-(box.height-hd.height*s)/2)/s];
}
function cgHit(event){
  const p = cgPointerPoint(event), hd = document.getElementById('cgHd');
  const radius = Math.max(10,hd.width/60);
  return CG_WORK.handles.find(h => Math.hypot(h.point[0]-p[0],h.point[1]-p[1]) < radius);
}
function cgSyncCamera(){
  const c = cg();
  for(const key of ['yaw','pitch','scale','height']){
    const input = document.querySelector(`[data-cg-group="cam"][data-cg-key="${key}"]`), label = document.getElementById('cgv_cam_' + key);
    if(input){ input.min = Math.min(Number(input.min),c.cam[key]); input.max = Math.max(Number(input.max),c.cam[key]); input.value = c.cam[key]; }
    if(label) label.textContent = Math.round(c.cam[key]*100)/100;
  }
  const reset = document.getElementById('cgReset'); if(reset) reset.disabled = cgPlacementReset();
}
function cgMoveWorld(dx,dy){
  const c = cg(), camera = CG_WORK.camera, hd = document.getElementById('cgHd');
  const yaw = c.cam.yaw*Math.PI/180,pitch = c.cam.pitch*Math.PI/180;
  const right = [Math.cos(yaw),0,-Math.sin(yaw)], up = [-Math.sin(pitch)*Math.sin(yaw),Math.cos(pitch),-Math.sin(pitch)*Math.cos(yaw)];
  const v = right.map((x,k) => x*dx*camera.width/hd.width-up[k]*dy*camera.height/hd.height); v[0] = -v[0]; return v;
}
function cgWire(){
  const hd = document.getElementById('cgHd'); if(!hd) return;
  if(CG_WORK.resize) CG_WORK.resize.disconnect();
  if(typeof ResizeObserver === 'function'){
    CG_WORK.resize = new ResizeObserver(() => { if(cgHere() && document.getElementById('cgHd') === hd) cgOverlay(); });
    CG_WORK.resize.observe(hd);
  }
  let drag = null, operation = null, last = [0,0];
  const cancel = () => { if(operation){ cg().xf = operation.start; operation = null; cgSyncCamera(); cgDraw(); } };
  const accept = () => { operation = null; cgSyncCamera(); };
  hd.addEventListener('contextmenu',e => { e.preventDefault(); cancel(); });
  hd.addEventListener('auxclick',e => { if(e.button === 1) e.preventDefault(); });
  hd.addEventListener('wheel',e => {
    e.preventDefault(); cg().cam.scale = Math.max(0.2,Math.min(6,cg().cam.scale*Math.exp(e.deltaY*0.001)));
    cgSyncCamera(); cgDraw();
  },{passive:false});
  hd.addEventListener('pointerdown',e => {
    hd.focus(); last = cgPointerPoint(e);
    if(e.button === 2){ e.preventDefault(); cancel(); return; }
    if(operation && e.button === 0){ accept(); return; }
    if(e.button === 1 || e.altKey && e.button === 0){ e.preventDefault(); drag = {kind:'camera'}; }
    else if(e.button === 0){
      const hit = cgHit(e);
      if(hit) drag = {kind:'rig',handle:hit};
    }
    if(drag) hd.setPointerCapture(e.pointerId);
  });
  hd.addEventListener('pointermove',e => {
    const p = cgPointerPoint(e), dx=p[0]-last[0],dy=p[1]-last[1]; last=p;
    const c = cg();
    if(operation){
      if(operation.kind === 'r'){
        if(operation.axis) c.xf.r['xyz'.indexOf(operation.axis)] += dx*0.3;
        else{ c.xf.r[1] += dx*0.3; c.xf.r[0] += dy*0.3; }
      }else{
        const movement = cgMoveWorld(dx,dy);
        if(operation.axis){ const i='xyz'.indexOf(operation.axis); const amount = (dx-dy)*CG_WORK.camera.height/hd.height; c.xf.t[i] += amount; }
        else c.xf.t = c.xf.t.map((v,i) => v+movement[i]);
      }
      cgSyncCamera(); cgDraw(); return;
    }
    if(!drag){ const hit = cgHit(e), name = hit ? hit.name : ''; if(CG_WORK.hover !== name){ CG_WORK.hover=name; cgOverlay(); } return; }
    if(drag.kind === 'camera'){
      if(e.ctrlKey) c.cam.scale = Math.max(0.2,Math.min(6,c.cam.scale*Math.exp(dy*0.005)));
      else if(e.shiftKey){ c.cam.pan -= dx*CG_WORK.camera.width/hd.width; c.cam.height += dy*CG_WORK.camera.height/hd.height; }
      else{ c.cam.yaw += dx*0.3; c.cam.pitch = Math.max(-60,Math.min(80,c.cam.pitch+dy*0.3)); }
      cgSyncCamera();
    }else{
      const rig = cgRigLayout(), h = drag.handle, ch = c.rig.basis[h.name] = {...c.rig.basis[h.name]};
      if(h.name === 'IK Head'){
        const angles = ch.e ? [...ch.e] : ch.q ? crToEuler(crQuat(ch.q)) : [0,0,0];
        angles[0] += dy*0.003; angles[2] += dx*0.003; ch.e = angles; delete ch.q;
      }else{
        const W = crSolve(rig,c.rig.basis,cgRigType()), bone = rig.bones[h.i];
        const base = bone.p < 0 ? bone.m : crMul(W[bone.p],rig.rel[h.i]);
        const game = cgMoveWorld(dx,dy), blender = [game[0],game[2],game[1]];
        const local = crR3(crT3(crRot(base)),blender);
        ch.l = (ch.l || [0,0,0]).map((v,i) => v+local[i]);
      }
    }
    cgDraw();
  });
  hd.addEventListener('pointerup',e => { drag=null; if(hd.hasPointerCapture(e.pointerId)) hd.releasePointerCapture(e.pointerId); });
  hd.addEventListener('keydown',e => {
    const key=e.key.toLowerCase();
    if(key === 'escape'){ e.preventDefault(); cancel(); return; }
    if(key === 'enter'){ e.preventDefault(); accept(); return; }
    if(operation && ['x','y','z'].includes(key)){ e.preventDefault(); operation.axis=operation.axis === key ? '' : key; return; }
    if(!operation && ['g','r'].includes(key)){ e.preventDefault(); operation={kind:key,axis:key === 'r' ? 'y' : '',start:JSON.parse(JSON.stringify(cg().xf))}; }
  });
}
