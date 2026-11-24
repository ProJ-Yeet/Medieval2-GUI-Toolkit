const CG_SIZE_KEYS = {card:'cards.gen_size_card',large:'cards.gen_size_large',info:'cards.gen_size_info',custom:'cards.gen_size_custom',modcard:'cards.gen_size_modcard',modinfo:'cards.gen_size_modinfo'};
const CG_POSE_KEYS = {tpose:'cards.gen_pose_tpose',guard:'cards.gen_pose_guard',brace:'cards.gen_pose_brace',draw:'cards.gen_pose_draw',riding:'cards.gen_pose_riding',march:'cards.gen_pose_march',anim:'cards.gen_pose_anim',rig:'cards.gen_pose_rig'};
const CG_PART_KEYS = {whole:'cards.gen_part_whole',arms:'cards.gen_part_arms',legs:'cards.gen_part_legs',head:'cards.gen_part_head',posture:'cards.gen_part_posture'};
const CG_FRAME_KEYS = {whole:'cards.gen_frame_whole',knees:'cards.gen_frame_knees',thighs:'cards.gen_frame_thighs',waist:'cards.gen_frame_waist'};
const CG_GROUND_KEYS = {none:'cards.gen_ground_none',colour:'cards.gen_ground_colour',pic:'cards.gen_ground_pic',scroll:'cards.gen_ground_scroll',strat:'cards.gen_ground_strat',battle:'cards.gen_ground_battle'};
const CG_LIGHT_KEYS = {sun:'cards.gen_light_sun',point:'cards.gen_light_point'};
const CG_FINISH_KEYS = {blur:'cards.gen_blur',exposure:'cards.gen_exposure',brightness:'cards.gen_brightness',contrast:'cards.gen_contrast',gamma:'cards.gen_gamma',saturation:'cards.gen_saturation',hue:'cards.gen_hue',sharpen:'cards.gen_sharpen',outline:'cards.gen_outline'};
/* Armory unit-card and information-picture maker. */

const CG_WORK = {sizes: null, mod: null, library: null, rigs: {}, art: new Map(), serial: 0, draw: 0, handles: [], xfObjs: new WeakMap()};
/* 2026-11-23: two sources, each with its own settings. An existing unit of
   the mod, the default: its soldier model loaded here alone, posed by its own
   animations. Or Armory Studio's model, reached from Armory Studio, whose
   settings travel with the Armory project (armsess.js, state.cg). */
const cgSrc = () => state.cgSrc === 'armory' ? 'armory' : 'unit';
function cg(src){
  // 2026-11-24: the IK rig is the pose a card starts on; gear, the weapon set drawn
  const defaults = {size:'card',mult:1,w:48,h:64,ss:10,oneEach:true,gear:'primary',guide:true,pose:'rig',name:'',unit:'',
    cam:{yaw:20,pitch:4,scale:1.2,height:0,pan:0,persp:false},xf:{t:[0,0,0],r:[0,0,0],s:1},overlay:true,lights:[],
    rig:{type:'auto',basis:{},handles:true,cat:'',pick:'',part:'whole',camReset:true,autoFor:''},
    light:{type:'sun',azimuth:35,elevation:40,amount:0.95,level:1,ambient:0.38,flat:false},
    post:{blur:0.5,exposure:0,brightness:0,contrast:1,gamma:1,saturation:1,hue:0,sharpen:0.2,outline:0.3},
    fit:{part:'thighs',auto:true},ground:{kind:'none',colour:'#5d4d36',pic:''},gframe:false,paint:{on:false,strength:1}};
  const c = (src || cgSrc()) === 'armory' ? (state.cg = state.cg || {}) : (state.cgUnit = state.cgUnit || {});
  for(const [key,value] of Object.entries(defaults)){
    if(c[key] == null) c[key] = value;
    else if(value && typeof value === 'object' && !Array.isArray(value)) for(const [n,v] of Object.entries(value)) if(c[key][n] == null) c[key][n] = v;
  }
  return c;
}
function cgHere(){ return state.mode === 'cards' && cardsSubNow() === 'generate'; }
/* 2026-11-24: the models, animations and poses this page reads keep off the
   loading bar (core.js): the view says what it is reading itself, and the bar
   only blinked on for an instant when one took a little over 180 ms. */
function cgQuiet(u){ return cgHere() && /^\/api\/(armory\/(asset|poses)|model\/(anims?|engine|mounts))\b/.test(u); }
/* 2026-11-23: every section folds; which are shut is this browser's own. */
const CG_SHUT = (() => { try{ return new Set(JSON.parse(localStorage.getItem('cardgen_shut') || localStorage.getItem(['cardgen', 'shut'].join('.')) || '[]')); }catch(e){ return new Set(); } })();
function cgSec(key, title, body){
  return `<details class="cgsec"${CG_SHUT.has(key) ? '' : ' open'} ontoggle="cgSecToggle(${esc(JSON.stringify(key))},this.open)"><summary>${title}</summary><div class="cgsecbody">${body}</div></details>`;
}
function cgSecToggle(key, open){
  if(open) CG_SHUT.delete(key); else CG_SHUT.add(key);
  try{ localStorage.setItem('cardgen_shut', JSON.stringify([...CG_SHUT])); }catch(e){}
}
/* One part of a model: a horse's Body is not the rider's, nor a copy's its source's. */
const cgPartKey = o => (o.grp ? o.grp + '|' : '') + (((o.src || [])[0] || {}).asset || '') + '|' + String(o.name || '').toLowerCase();
function cgAllObjects(){
  const base = (cgSrc() === 'unit' ? CG_UNIT.objects : armProj().objects).filter(o => !o.hidden && !armCollHidden(o));
  return base.concat(cgCopies(base));
}
/* --- 2026-11-24: the models a card is made of ------------------------------
   Each model (the rider, his mount, an engine; in Armory Studio a collection)
   is a group of its own in the object list, moved and scaled as a whole
   (c.gxf). A model or one object can be copied (c.dups): a mumak carries
   several riders. A copy is the same objects under ids of its own, posed as
   its source is. */
function cgGroupOf(o){
  if(o.grp) return o.grp;
  if(cgSrc() === 'armory' && o.coll != null) return 'coll:' + o.coll;
  return 'asset:' + (((o.src || [])[0] || {}).asset || '');
}
const cgDupId = (k,id) => 1e9 + k*1e6 + id + 500000;
function cgCopies(base){
  const dups = cg().dups || [], out = [];
  CG_WORK.copyMemo = CG_WORK.copyMemo || new WeakMap();
  for(const d of dups){
    const ids = new Set(d.ids);
    for(const o of base) if(ids.has(o.id)){
      // one copy object per source object and copy, so caches keyed by it hold
      let memo = CG_WORK.copyMemo.get(o);
      if(!memo) CG_WORK.copyMemo.set(o, memo = new Map());
      if(!memo.has(d.k)) memo.set(d.k, {...o, id: cgDupId(d.k, o.id), grp: 'dup:' + d.k, dupOf: o.id});
      out.push(memo.get(d.k));
    }
  }
  return out;
}
function cgGroups(){
  const groups = new Map();
  for(const o of cgAllObjects()){ const k = cgGroupOf(o); if(!groups.has(k)) groups.set(k, []); groups.get(k).push(o); }
  return groups;
}
function cgGroupName(gk, objs){
  const o = objs[0], dup = (cg().dups || []).find(d => 'dup:' + d.k === gk);
  if(dup) return tt('cards.gen_grp_copy', {name: dup.name});
  if(gk.startsWith('coll:')){ const coll = armProj().collections.find(x => x.id === o.coll); return coll ? coll.name : gk; }
  const live = ARM.assets.get(((o.src || [])[0] || {}).asset), entry = live && live.asset ? live.asset.entry : o.mesh;
  return o.still === 'mount' ? tt('cards.gen_grp_mount', {name: entry}) : o.still === 'engine' ? tt('cards.gen_grp_engine', {name: entry}) : entry;
}
/* The point a model is scaled about: the middle of its objects as they stand. */
function cgGroupPivot(gk){
  const memo = CG_WORK.gpivot = CG_WORK.gpivot || new Map(), objs = cgGroups().get(gk) || [];
  const sig = objs.map(o => o.id).join(','), hit = memo.get(gk);
  if(hit && hit.sig === sig) return hit.p;
  const b = armBounds(objs), p = b ? b[0].map((v,i) => (v+b[1][i])/2) : [0,0,0];
  if(b) memo.set(gk, {sig, p});
  return p;
}
function cgGroupXf(gk){ return ((cg().gxf || {})[gk]) || {t:[0,0,0],s:1}; }
function cgGroupSet(gk, fn){
  const c = cg(); c.gxf = {...(c.gxf || {})};
  const g = c.gxf[gk] = JSON.parse(JSON.stringify(cgGroupXf(gk)));
  fn(g); cgFitChanged(); cgDraw();
}
function cgGroupScale(gk, v){
  if(!isFinite(v) || v <= 0) return;
  cgGroupSet(gk, g => { g.s = v; });
  const out = document.querySelector(`[data-cggs="${CSS.escape(gk)}"]`); if(out) out.textContent = Math.round(v*100)/100;
}
function cgGroupHide(gk){
  const c = cg(), ids = (cgGroups().get(gk) || []).map(o => o.id), off = new Set(c.off || []);
  const all = ids.every(id => off.has(id));
  for(const id of ids) if(all) off.delete(id); else off.add(id);
  c.off = [...off]; cgFitChanged(); cgPaint();
}
/* 2026-11-24: an elephant's riders where the game puts them: descr_mount.txt
   lists a rider_offset per rider (a mumak fifteen), the first the driver's.
   The rider is set on the first and a copy of him on each of the others; the
   offsets are the game's, so they are kept relative to the driver's when the
   mount carries him, and taken as they are when it stands. */
function cgRiderSpotsHtml(gk, objs){
  if(cgSrc() !== 'unit' || !objs.some(o => o.still === 'mount')) return '';
  return `<button class="mini" title="${ttA('cards.gen_riders_spots_title')}" onclick="cgRidersOnSpots()">${tt('cards.gen_riders_spots')}</button>`;
}
async function cgRidersOnSpots(){
  const c = cg(), u = ((CG_UNIT.units || {}).list || []).find(x => x.type === CG_UNIT.unit);
  if(!u || !u.mount) return;
  let rows = [];
  try{ rows = (await cgGet(`/api/model/mounts?mod=${enc(CG_UNIT.mod)}&entry=${enc(CG_UNIT.entry)}&mount=${enc(u.mount)}`)).mounts || []; }catch(e){ toast(errText(e)); return; }
  const row = rows.find(r => (r.type || '').toLowerCase() === u.mount.toLowerCase() || (r.entry || '').toLowerCase() === u.mount.toLowerCase());
  const spots = (row && row.offsets) || [];
  if(spots.length < 2){ toast(tt('cards.gen_riders_spots_none')); return; }
  const riders = CG_UNIT.objects.filter(o => !o.still), gk = riders.length ? cgGroupOf(riders[0]) : '';
  if(!gk) return;
  const carried = !!armAnim().mount, first = spots[0];
  const at = p => carried ? p.map((v,i) => v-first[i]) : p.slice();
  const kept = (c.dups || []).filter(d => !d.spot), gxf = {...(c.gxf || {})};
  for(const d of c.dups || []) if(d.spot) delete gxf['dup:' + d.k];
  let k = kept.reduce((m,d) => Math.max(m,d.k), 0);
  const ids = riders.map(o => o.id), name = cgGroupName(gk, riders), dups = kept.slice();
  if(!carried) gxf[gk] = {...cgGroupXf(gk), t: at(first)};
  spots.slice(1).forEach((p,i) => { k++; dups.push({k, ids, name: name + ' ' + (i+2), spot: true}); gxf['dup:' + k] = {t: at(p), s: 1}; });
  c.dups = dups; c.gxf = gxf;
  toast(tt('cards.gen_riders_spots_done', {n: spots.length}));
  cgFitChanged(); cgPaint();
}
/* A copy of a model, or of one object, set down beside its source. */
function cgDuplicate(ids, name){
  const c = cg(), k = (c.dups || []).reduce((m,d) => Math.max(m,d.k), 0)+1;
  const base = cgAllObjects().filter(o => ids.includes(o.id));
  const real = base.map(o => o.dupOf != null ? o.dupOf : o.id);
  c.dups = [...(c.dups || []), {k, ids: real, name}];
  const b = armBounds(base), w = b ? Math.max(0.3, b[1][0]-b[0][0]) : 1;
  c.gxf = {...(c.gxf || {}), ['dup:' + k]: {t:[w*1.1,0,0], s:1}};
  cgFitChanged(); cgPaint();
}
function cgDupRemove(k){
  const c = cg(); c.dups = (c.dups || []).filter(d => d.k !== k);
  c.gxf = {...(c.gxf || {})}; delete c.gxf['dup:' + k];
  if(CG_WORK.grpSel === 'dup:' + k) CG_WORK.grpSel = '';
  cgFitChanged(); cgPaint();
}
/* What is drawn: the objects not switched off in the card's object list and,
   with One of each part, one variant of each part (the one picked there, else
   the first). */
function cgObjects(){
  const c = cg(), off = new Set(c.off || []), pick = c.pick || {};
  const list = cgAllObjects().filter(o => !off.has(o.id) && !cgGearOff(o));
  if(!c.oneEach) return list.map(cgXf);
  const chosen = new Map();
  for(const o of list){ const k = cgPartKey(o); if(!chosen.has(k) || pick[k] === o.id) chosen.set(k, o.id); }
  return list.filter(o => chosen.get(cgPartKey(o)) === o.id).map(cgXf);
}
/* 2026-11-24: the weapon set drawn. Primary is the first weapon (its active
   parts, the second one's carried), Secondary the one drawn later; Custom
   leaves every part to the object list. The prefixes are the game's group
   types (armobj.js, armPrefixHelp). */
const CG_GEAR_OFF = {primary: /^(secondaryactive|primarypassive|shieldactive)/i, secondary: /^(primaryactive|secondarypassive|shieldpassive)/i};
function cgGearOff(o){ const re = CG_GEAR_OFF[cg().gear]; return !!(re && re.test(String(o.name || ''))); }
function cgGearHtml(){
  const g = cg().gear, label = {primary: 'cards.gen_gear_primary', secondary: 'cards.gen_gear_secondary', custom: 'cards.gen_gear_custom'};
  return `<div class="armexprow" title="${ttA('cards.gen_gear_title')}"><span>${tt('cards.gen_gear')}</span>${['primary','secondary','custom'].map(k =>
    `<button class="mini${g === k ? ' on' : ''}" onclick="cgGear('${k}')">${tt(label[k])}</button>`).join('')}</div>`;
}
/* The set's skeleton for that weapon is played too, when it has one. */
async function cgGear(mode){
  const c = cg(), a = armAnim(), set = a.set;
  c.gear = mode; cgFitChanged();
  const want = (set && mode !== 'custom' ? (mode === 'secondary' ? set.secondary : set.primary) || '' : '').toLowerCase();
  if(want && c.pose !== 'tpose' && ((a.list || {}).skeletons || {})[want] && want !== (a.skel || '').toLowerCase()){
    armAnimSkel(want);
    try{ await cgPreparePose(); }catch(e){ c.err = errText(e); }
  }
  cgPaint();
}
/* An object as the card draws it: moved, turned and scaled by the card's own
   transform for it (c.oxf), never the Armory project's. */
function cgXf(o){
  const x = (cg().oxf || {})[o.id], gk = cgGroupOf(o), g = (cg().gxf || {})[gk];
  if(!x && !g) return o;
  const sig = JSON.stringify([o.t, o.r, o.s, x, g]), hit = CG_WORK.xfObjs.get(o);
  if(hit && hit.sig === sig) return hit.obj;
  // 2026-11-24: a matrix on top of the object as it is drawn (armRender's
  // o.post), after its pose: added to o.t before the skinning, a move was
  // turned with the bones and a rider set on a mumak's spot flew off
  let post = null;
  if(x){ const p = armPivot(o).map((v,i) => v + o.t[i]);
    post = armMul(armTrans(p[0]+x.t[0],p[1]+x.t[1],p[2]+x.t[2]),armMul(armRot(...x.r),armMul(armScale(...x.s),armTrans(-p[0],-p[1],-p[2])))); }
  if(g){ const k = Number(g.s) || 1, P = cgGroupPivot(gk);
    const m = armMul(armTrans(P[0]+g.t[0],P[1]+g.t[1],P[2]+g.t[2]),armMul(armScale(k,k,k),armTrans(-P[0],-P[1],-P[2])));
    post = post ? armMul(m,post) : m; }
  const obj = {...o, post};
  CG_WORK.xfObjs.set(o, {sig, obj});
  return obj;
}
/* A mount stands still beside its rider until it carries him (a.mount), then it
   plays its own action under him; an engine always stands. */
const cgStill = o => !!o.still && !(o.still === 'mount' && armAnim().mount);
const cgMoving = objects => objects.filter(o => !cgStill(o));
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
/* The unit source's own model and animation state. ARM.anim is Armory's; while
   a unit is shown here it is held aside (CG_UNIT.held) and given back when
   Armory Studio, or its model here, is shown again. */
const CG_UNIT = {objects: [], unit: '', entry: '', mod: '', held: null, anim: null, units: null, q: ''};
function cgUnitAnimIn(){
  if(CG_UNIT.held) return;
  CG_UNIT.held = {anim: ARM.anim};
  ARM.anim = CG_UNIT.anim;
  armAnim();
  CG_UNIT.anim = ARM.anim;
}
function cgUnitAnimOut(){
  if(!CG_UNIT.held) return;
  CG_UNIT.anim = ARM.anim;
  ARM.anim = CG_UNIT.held.anim; CG_UNIT.held = null;
}
function cgSource(src){
  state.cgSrc = src; CG_WORK.view = null;
  if(src === 'armory') cgUnitAnimOut();
  CG_WORK.fit = null;
  renderCardGen();
}
/* model: one of the unit's armour_ug_models, its soldier model when none is given */
/* --- 2026-11-24: a card's session, kept per unit -----------------------------
   Everything the card maker holds for a unit's card (its model, pose, camera,
   lights, objects, copies, textures) is kept in this browser under the mod and
   the unit, saved as the card is drawn. Picking a unit that has one asks:
   Continue the earlier card, or Start anew (which forgets it). */
const CG_SESS_SKIP = new Set(['saved','give','err','poseNote','poseNote2']);
const cgSessKey = (mod, type) => 'cardgen_sess|' + mod + '|' + type;
function cgSessGet(mod, type){ try{ return JSON.parse(localStorage.getItem(cgSessKey(mod, type)) || 'null'); }catch(e){ return null; } }
function cgSessSave(){
  if(cgSrc() !== 'unit' || !CG_UNIT.unit || !CG_UNIT.objects.length) return;
  const c = cg(), keep = {};
  for(const [k, v] of Object.entries(c)) if(!CG_SESS_SKIP.has(k)) keep[k] = v;
  const rec = JSON.stringify({entry: CG_UNIT.entry, when: Date.now(), c: keep});
  try{ localStorage.setItem(cgSessKey(CG_UNIT.mod, CG_UNIT.unit), rec); }
  catch(e){
    // a picture for the ground can be too big for the browser's store: kept without it
    try{ keep.ground = {...keep.ground, pic: ''}; localStorage.setItem(cgSessKey(CG_UNIT.mod, CG_UNIT.unit), JSON.stringify({entry: CG_UNIT.entry, when: Date.now(), c: keep})); }catch(e2){}
  }
}
function cgSessDrop(mod, type){ try{ localStorage.removeItem(cgSessKey(mod, type)); }catch(e){} }
/* how: 'continue' or 'new' from the picker's buttons; 'level' for another
   armour upgrade of the unit already shown. Left out (a double click), a unit
   with a session is shown in the picker to ask. */
async function cgUnitLoad(type, model, how){
  const mod = state.src, units = (CG_UNIT.units || {}).list || [];
  const u = units.find(x => x.type === type);
  if(!u) return;
  const sess = how === 'level' ? null : cgSessGet(mod, type);
  if(sess && !how){ CG_UNIT.picking = true; cgPaint(); cgUnitPeek(type, model); return; }
  // Start anew on a unit with a session: the defaults, not the last unit's settings
  if(how === 'new' && sess){ cgSessDrop(mod, type); state.cgUnit = {}; }
  const resume = how === 'continue' && sess;
  if(resume && !model) model = sess.entry;
  const entry = (model || cgUnitModel(u)).toLowerCase(), c = cg();
  CG_UNIT.unit = type; CG_UNIT.entry = entry; CG_UNIT.mod = mod; CG_UNIT.objects = []; CG_UNIT.picking = false; CG_WORK.view = null;
  c.unit = type; c.name = type.replace(/[^A-Za-z0-9_\-]/g, '_'); c.saved = null; c.give = null; c.err = ''; c.off = []; c.pick = {}; c.oxf = {};
  c.gxf = {}; c.dups = []; c.texFaction = '';
  c.rig.autoFor = '';
  if(resume){ for(const [k, v] of Object.entries(sess.c || {})) if(!CG_SESS_SKIP.has(k)) c[k] = JSON.parse(JSON.stringify(v)); cg(); CG_WORK.fit = null; }
  CG_WORK.boneSel = ''; CG_WORK.objSel = 0;
  cgPaint();
  const a = {kind: 'entry', mod, entry}, key = armAssetKey(a);
  const live = await armLoadAsset(a);
  if(CG_UNIT.unit !== type) return;
  if(!live || !live.view){ c.err = (live && live.err) || tt('cards.gen_unit_unreadable', {entry}); cgPaint(); return; }
  CG_UNIT.skins = live.view.skins || [];
  const objects = live.view.objects.map((ob, i) => ({id: -1 - i, src: [{asset: key, group: ob.index}], name: ob.name, mesh: ob.mesh,
    flag: ob.flag, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1]}));
  const extras = await cgExtras(u, mod, -5000);
  if(CG_UNIT.unit !== type) return;
  // the mount under the rider, the engine beside the crew
  cgBeside(objects, extras.filter(o => o.still !== 'mount'));
  CG_UNIT.objects = objects.concat(extras);
  // its own animations, in the held-aside state
  cgUnitAnimIn();
  ARM.anim = null; const an = armAnim(); CG_UNIT.anim = an; an.fromMod = mod;
  try{ an.list = await cgGet(`/api/model/anims?mod=${enc(mod)}&entry=${enc(entry)}`); }catch(e){ an.list = {error: errText(e)}; }
  if(ARM.anim !== an) return;
  const set = (an.list.sets || [])[0];
  an.skel = set ? ((c.gear === 'secondary' && set.secondary) || set.primary || set.secondary || '') : Object.keys(an.list.skeletons || {})[0] || '';
  an.set = set || null;
  an.mountFor = u.mount ? cgMountFor(mod, entry, u.mount.toLowerCase()) : null;
  CG_WORK.fit = null;
  await cgPreparePose();
  if(resume && c.texFaction) await cgTexPick(c.texFaction);
  cgPaint();
}
/* 2026-11-24: a cavalry unit's mount and a siege unit's engine, standing still
   beside it (o.still: never posed by the soldier's animation). The mount is its
   descr_mount.txt model, the engine its descr_engines.txt mesh as the unit
   editor's preview draws it (editor.js, edPrevEngineLoad). */
async function cgExtras(u, mod, base){
  const out = [], add = (live, key, kind, from) => live.view.objects.forEach((ob, i) => out.push({id: base - from - i, src: [{asset: key, group: ob.index}],
    name: ob.name, mesh: ob.mesh, flag: ob.flag, still: kind, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1]}));
  if(u.mount){
    const a = {kind: 'entry', mod, entry: u.mount.toLowerCase()}, live = await armLoadAsset(a);
    if(live && live.view && live.geo) add(live, armAssetKey(a), 'mount', 0);
  }
  if(u.engine){
    const live = await cgEngineLoad(mod, u.engine);
    if(live) add(live, live.key, 'engine', 500);
  }
  return out;
}
async function cgEngineLoad(mod, name){
  const key = 'engine|' + mod + '|' + name.toLowerCase();
  CG_WORK.engines = CG_WORK.engines || new Map();
  if(!CG_WORK.engines.has(key)) CG_WORK.engines.set(key, (async () => {
    const sc = await cgGet(`/api/model/engine?mod=${enc(mod)}&engine=${enc(name)}`);
    if(!sc.mesh || !sc.mesh_exists) return null;
    const r = await fetch(`/api/model/engine_geometry?mod=${enc(mod)}&rel=${enc(sc.mesh)}`);
    if(!r.ok) return null;
    const geo = v3Parse(await r.arrayBuffer()), stem = sc.mesh.split('/').pop().replace(/\.mesh$/i, '');
    const live = {asset: {kind: 'engine', mod, entry: name}, key, geo, uScale: 1,
      view: {objects: geo.groups.map((g, i) => ({index: i, name: 'engine', mesh: stem + (geo.groups.length > 1 ? ' ' + (i + 1) : '')}))}};
    ARM.assets.set(key, live); armUpload(live);
    if(sc.main){ try{ live.tex = armTexture(await armImage(`/model_texture?mod=${enc(mod)}&rel=${enc(sc.main)}`), 1); }catch(e){} }
    return live;
  })().catch(() => null));
  return CG_WORK.engines.get(key);
}
/* 2026-11-24: the unit's mount playing under its rider: its descr_mount.txt
   row (skeleton, rider_offset) and the action for the rider's slot, as
   armAnimMountLoad does for an Armory project. */
function cgMountFor(mod, rider, mount){
  let rows = null, list = null;
  return async slot => {
    if(!rows){ try{ rows = (await cgGet(`/api/model/mounts?mod=${enc(mod)}&entry=${enc(rider)}&mount=${enc(mount)}`)).mounts || []; }catch(e){ rows = []; } }
    const row = rows.find(r => (r.entry || '').toLowerCase() === mount);
    if(!row) return null;
    if(!list){ try{ list = await cgGet(`/api/model/anims?mod=${enc(mod)}&entry=${enc(mount)}`); }catch(e){ return null; } }
    const sk = ((list && list.skeletons) || {})[(row.skeleton || '').toLowerCase()];
    const r = sk && v3aMountRow(sk.actions, slot).row;
    if(!r) return null;
    let data;
    try{ data = await api.get(`/api/model/anim?mod=${enc(mod)}&${r.rel ? `rel=${enc(r.rel)}` : `pack=${enc(r.path)}`}&skel=${enc(row.skeleton)}` + (r.slot != null ? `&slot=${r.slot}` : '')); }
    catch(e){ return null; }
    if(!data || data.error || !data.bones) return null;
    return {key: armAssetKey({kind: 'entry', mod, entry: mount}), data, bind: v3aBind(data), travel: v3aTravel(data),
            hub: data.bones.findIndex(b => b.parent === 0), offset: row.offset || [0, 0, 0]};
  };
}
/* 2026-11-24: a model that did not come ("Failed to fetch") asked for again:
   armLoadAsset tries four times itself, this is the button after that. */
function cgRetry(type, entry, peek){
  for(const [key, live] of ARM.assets) if(!live.loading && !live.geo) ARM.assets.delete(key);
  if(CG_WORK.engines) for(const [key] of CG_WORK.engines) CG_WORK.engines.delete(key);
  if(peek) cgUnitPeek(type, entry); else cgUnitLoad(type, entry, 'level');
}
/* An API read tried again a few times before it counts as failed. */
async function cgGet(url){
  for(let i = 0; ; i++){
    try{ return await api.get(url); }
    catch(e){ if(i >= 3 || e && e.deliberate) throw e; await new Promise(ok => setTimeout(ok, 500 * (i + 1))); }
  }
}
/* Beside the unit, on the same ground, clear of it. */
function cgBeside(objects, extras){
  const a = armBounds(objects), b = armBounds(extras);
  if(!a || !b) return;
  const t = [a[1][0] - b[0][0] + 0.3, a[0][1] - b[0][1], (a[0][2] + a[1][2] - b[0][2] - b[1][2]) / 2];
  for(const o of extras) o.t = t.slice();
}
/* The unit picker: a search and the unit editor's faction, category and
   class filters, its rows repainted alone. */
function cgUnitPickHtml(){
  const L = (CG_UNIT.units || {}).list || [], f = CG_UNIT.f = CG_UNIT.f || {q: '', faction: '', category: '', cls: ''};
  const uniq = list => [...new Set(list.filter(Boolean))].sort((x, y) => x.localeCompare(y));
  const sel = (k, label, list) => `<select onchange="CG_UNIT.f.${k}=this.value;cgUnitRows()"><option value="">${label}</option>
    ${list.map(v => `<option${f[k] === v ? ' selected' : ''}>${esc(v)}</option>`).join('')}</select>`;
  setTimeout(cgUnitRows, 0);
  return `<div class="armexprow"><input placeholder="${ttA('armory.find')}" value="${esc(f.q)}" oninput="CG_UNIT.f.q=this.value;cgUnitRows()">
      ${sel('faction', tt('armory.exp_all_factions'), uniq(L.flatMap(u => u.factions || [])))}
      ${sel('category', tt('armory.exp_all_categories'), uniq(L.map(u => u.category)))}
      ${sel('cls', tt('armory.exp_all_classes'), uniq(L.map(u => u['class'])))}</div>
    <div class="grid cgunitcards" id="cgUnitRows"></div>`;
}
function cgUnitRows(){
  const el = document.getElementById('cgUnitRows');
  if(!el) return;
  const f = CG_UNIT.f, q = (f.q || '').trim().toLowerCase();
  const rows = ((CG_UNIT.units || {}).list || []).filter(u => (!q || u.type.toLowerCase().includes(q) || cgUnitModel(u).toLowerCase().includes(q))
    && (!f.faction || (u.factions || []).includes(f.faction)) && (!f.category || u.category === f.category) && (!f.cls || u['class'] === f.cls));
  const peek = (CG_UNIT.peek || {}).type;
  // 2026-11-24: the unit editor's own cards, picture and all
  el.innerHTML = rows.slice(0, 400).map(u => { const t = esc(JSON.stringify(u.type));
    return `<div class="card${u.type === peek ? ' sel' : ''}" onclick="cgUnitPeek(${t})" ondblclick="cgUnitLoad(${t})" title="${esc(u.type)}">
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src, u.type, 'card')}" alt="">
      <div class="meta"><div class="nm">${esc(u.type)}</div><div class="sub">${esc(u.category)} · ${esc(u['class'])}</div><div class="sub">${esc(cgUnitModel(u))}</div></div></div>`; }).join('')
    || `<div class="count">${tt('armory.nothing_matches')}</div>`;
}
const cgPicking = () => cgSrc() === 'unit' && (CG_UNIT.picking || !CG_UNIT.unit);
/* 2026-11-23: a unit picked from the list is shown first, turning in 3D where
   the HD view stands, and taken with Use this unit (or a double click). */
async function cgUnitPeek(type, model){
  const u = ((CG_UNIT.units || {}).list || []).find(x => x.type === type);
  if(!u) return;
  const mod = state.src, entry = (model || cgUnitModel(u)).toLowerCase(), a = {kind: 'entry', mod, entry}, key = armAssetKey(a);
  const old = CG_UNIT.peek || {};
  const pk = CG_UNIT.peek = {type, entry, info: u, objects: [], yaw: old.yaw != null ? old.yaw : 0.5, pitch: old.pitch != null ? old.pitch : 0.12, loading: true, err: '',
    zoom: old.type === type ? old.zoom : 1, pan: old.type === type ? old.pan : null};
  cgUnitRows(); cgPeekPaint();
  const live = await armLoadAsset(a);
  if(CG_UNIT.peek !== pk) return;
  pk.loading = false;
  if(!live || !live.view){ pk.err = (live && live.err) || tt('cards.gen_unit_unreadable', {entry}); cgPeekPaint(); return; }
  const seen = new Set();
  const one = list => list.filter(o => { const k = cgPartKey(o); if(seen.has(k)) return false; seen.add(k); return true; });
  pk.objects = one(live.view.objects.map((ob, i) => ({id: -100000 - i, src: [{asset: key, group: ob.index}], name: ob.name, mesh: ob.mesh, t: [0, 0, 0], r: [0, 0, 0], s: [1, 1, 1]})));
  cgPeekPaint();
  // its mount or engine beside it, once they come
  const extras = one(await cgExtras(u, mod, -200000));
  if(CG_UNIT.peek !== pk || !extras.length) return;
  cgBeside(pk.objects, extras); pk.objects = pk.objects.concat(extras);
  cgPeekPaint();
}
function cgPeekHtml(){
  return `<div class="cgpeek"><div class="armexprow" id="cgPeekHead"></div><canvas id="cgPeek"></canvas><div id="cgPeekV3" class="cgpeekv3" hidden></div>
    <p class="count">${tt('cards.gen_peek_hint')}</p></div>`;
}
/* 2026-11-24: a cavalry unit seen Mounted: the rider on his mount, playing
   their actions, in the Models viewer (viewer3d.js) docked where the turning
   view stands; its own "On his mount", with the mount the unit rides. */
function cgPeekMounted(){ const pk = CG_UNIT.peek; return !!(CG_UNIT.mounted && pk && pk.info && pk.info.mount && !pk.err && !pk.noRide); }
async function cgPeekV3(pk){
  if(typeof v3Mount !== 'function') return;
  await v3Mount('cgPeekV3', state.src, pk.entry);
  const want = (pk.info.mount || '').toLowerCase();
  // its mount list comes a moment after the model; the unit's own mount picked from it
  for(let i = 0; i < 60 && CG_UNIT.peek === pk && cgPeekMounted(); i++){
    const here = typeof v3 !== 'undefined' && v3 && v3.host === 'cgPeekV3' ? v3 : null, m = here && here.anim && here.anim.mount;
    // its actions read and none a rider's: nothing to carry him, the turntable again
    if(here && here.anim && here.anim.list && !m){ pk.noRide = true; cgPeekPaint(); return; }
    if(m && m.list){
      const rows = m.list.mounts || [], at = rows.findIndex(r => (r.type || '').toLowerCase() === want || (r.entry || '').toLowerCase() === want);
      if(at >= 0 && at !== m.pick){ m.pick = at; m.x = null; m.data = null; }
      // the viewer carries him only while a riding action plays: his mounted
      // skeleton set and its standing idle
      const a = v3.anim, si = (a.list.sets || []).findIndex(x => (x.mount || 'none').toLowerCase() !== 'none');
      if(si >= 0 && si !== a.set) v3AnimSet(si);
      const acts = ((v3AnimSk() || {}).actions || []).filter(x => x.playable);
      const row = ['stand_a_idle', 'stand_idle', 'idle'].map(n => acts.find(x => x.action.toLowerCase() === n)).find(Boolean) || acts[0];
      if(row && !a.data) await v3AnimPick(v3AnimKey(row));
      if(!m.on) v3AnimMountOn(true);
      return;
    }
    await new Promise(ok => setTimeout(ok, 250));
  }
}
function cgPeekMount(on){ CG_UNIT.mounted = !!on; cgPeekPaint(); }
function cgPeekPaint(){
  const head = document.getElementById('cgPeekHead'), canvas = document.getElementById('cgPeek');
  if(!head || !canvas) return;
  const pk = CG_UNIT.peek, u = pk && pk.info;
  const t = pk && esc(JSON.stringify(pk.type));
  head.innerHTML = pk ? `<b>${esc(pk.type)}</b><span class="count">${esc(u.category)} · ${esc(u['class'])} · ${esc(pk.entry)}</span>
      ${cgUgSelect(u, pk.entry, `cgUnitPeek(${t},this.value)`)}<span style="flex:1"></span>
      ${pk.err ? `<button class="mini" onclick="cgRetry(${t},${esc(JSON.stringify(pk.entry))},true)">${tt('cards.gen_retry')}</button>` : ''}
      ${pk.noRide && CG_UNIT.mounted ? `<span class="count">${tt('cards.gen_peek_no_ride')}</span>` : ''}
      ${u.mount ? `<button class="mini${CG_UNIT.mounted ? ' on' : ''}" title="${ttA('cards.gen_peek_mounted_title')}" onclick="cgPeekMount(${!CG_UNIT.mounted})">${tt('cards.gen_peek_mounted')}</button>` : ''}
      ${CG_UNIT.unit ? `<button class="mini" onclick="CG_UNIT.picking=false;cgPaint()">${tt('cards.gen_peek_cancel')}</button>` : ''}
      ${cgSessGet(state.src, pk.type) ? `<span class="count">${tt('cards.gen_sess_found')}</span>
        <button class="primary" title="${ttA('cards.gen_sess_continue_title')}" onclick="cgUnitLoad(${t},null,'continue')">${tt('cards.gen_sess_continue')}</button>
        <button title="${ttA('cards.gen_sess_new_title')}" onclick="cgUnitLoad(${t},${esc(JSON.stringify(pk.entry))},'new')">${tt('cards.gen_sess_new')}</button>`
      : `<button class="primary" onclick="cgUnitLoad(${t},${esc(JSON.stringify(pk.entry))},'new')">${tt('cards.gen_peek_use')}</button>`}`
    : `<span class="count">${tt('cards.gen_peek_none')}</span>`;
  const dock = document.getElementById('cgPeekV3'), mounted = cgPeekMounted();
  if(dock){
    canvas.hidden = mounted; dock.hidden = !mounted;
    if(mounted && dock.dataset.entry !== pk.entry){ dock.dataset.entry = pk.entry; cgPeekV3(pk); }
    if(!mounted && dock.dataset.entry){ dock.dataset.entry = ''; if(typeof v3 !== 'undefined' && v3 && v3.host === 'cgPeekV3'){ v3Stop(); v3 = null; } dock.innerHTML = ''; }
    if(mounted) return;
  }
  const box = canvas.getBoundingClientRect(), ratio = Math.min(2, devicePixelRatio || 1);
  const w = Math.max(64, Math.round(box.width * ratio)), h = Math.max(64, Math.round(box.height * ratio));
  if(canvas.width !== w || canvas.height !== h){ canvas.width = w; canvas.height = h; }
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#353d47'; ctx.fillRect(0, 0, w, h);
  cgPeekWire(canvas);
  const say = text => { ctx.fillStyle = '#c9d1d9'; ctx.font = `${14 * ratio}px sans-serif`; ctx.textAlign = 'center'; ctx.fillText(text, w / 2, h / 2); };
  if(!pk) return;
  if(pk.loading) return say(tt('armory.reading'));
  if(pk.err) return say(pk.err);
  const b = armBounds(pk.objects);
  if(!b) return;
  const [lo, hi] = b, pan = pk.pan || [0, 0, 0], target = [-(lo[0] + hi[0]) / 2 + pan[0], (lo[1] + hi[1]) / 2 + pan[1], (lo[2] + hi[2]) / 2 + pan[2]];
  // across the ground its diagonal, so a mount or engine beside it fits at any turn
  const size = Math.max(hi[1] - lo[1], Math.hypot(hi[0] - lo[0], hi[2] - lo[2]) * h / w) * 0.62 / 0.42;
  const dist = Math.max(0.05, size * 1.1 / (pk.zoom || 1));
  pk.span = 2 * dist * Math.tan(0.375) / h * ratio;      // the world across one CSS pixel, for a pan
  const eye = [target[0] + dist * Math.cos(pk.pitch) * Math.sin(pk.yaw), target[1] + dist * Math.sin(pk.pitch), target[2] + dist * Math.cos(pk.pitch) * Math.cos(pk.yaw)];
  const cam = {proj: v3Perspective(0.75, w / h, dist / 100, dist * 10), view: v3LookAt(eye, target, [0, 1, 0])};
  if(!armRender(pk.objects, w, h, cam, {plain: true, bg: [0.21, 0.24, 0.28]})) return;
  ctx.drawImage(ARM.glCanvas, 0, 0, w, h, 0, 0, w, h);
}
function cgTexturesIn(){
  if(!cgHere() || CG_WORK.texTimer) return;
  CG_WORK.texTimer = setTimeout(() => { CG_WORK.texTimer = 0; if(!cgHere()) return; if(cgPicking()) cgPeekPaint(); else cgDraw(); }, 120);
}
function cgPeekWire(canvas){
  if(canvas.dataset.wired) return;
  canvas.dataset.wired = '1';
  let last = null, pan = false;
  // 2026-11-24: a left drag turns it, a right (or middle) drag moves it
  canvas.addEventListener('pointerdown', e => { last = [e.clientX, e.clientY]; pan = e.button !== 0; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    const pk = CG_UNIT.peek;
    if(!last || !pk) return;
    const dx = e.clientX - last[0], dy = e.clientY - last[1];
    if(pan){
      const s = pk.span || 0.005, right = [Math.cos(pk.yaw), 0, -Math.sin(pk.yaw)];
      const up = [-Math.sin(pk.pitch) * Math.sin(pk.yaw), Math.cos(pk.pitch), -Math.sin(pk.pitch) * Math.cos(pk.yaw)];
      pk.pan = (pk.pan || [0, 0, 0]).map((v, k) => v - right[k] * dx * s + up[k] * dy * s);
    }else{
      // Armory Studio's turn: a drag right swings the eye left round the model
      pk.yaw -= dx * 0.0035;
      pk.pitch = Math.max(-1.4, Math.min(1.4, pk.pitch + dy * 0.0035));
    }
    last = [e.clientX, e.clientY]; cgPeekPaint();
  });
  canvas.addEventListener('dblclick', () => { const pk = CG_UNIT.peek; if(pk){ pk.pan = null; pk.zoom = 1; cgPeekPaint(); } });
  canvas.addEventListener('pointerup', () => { last = null; });
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  canvas.addEventListener('wheel', e => { const pk = CG_UNIT.peek; if(!pk) return; e.preventDefault(); pk.zoom = Math.max(0.3, Math.min(8, (pk.zoom || 1) * Math.exp(-e.deltaY * 0.0015))); cgPeekPaint(); }, {passive: false});
}
function cgSourceHtml(){
  const src = cgSrc();
  let html = `<div class="armexprow">
      <button class="mini${src === 'unit' ? ' on' : ''}" onclick="cgSource('unit')">${tt('cards.gen_src_unit')}</button>
      <button class="mini${src === 'armory' ? ' on' : ''}" onclick="cgSource('armory')">${tt('cards.gen_src_armory')}</button>
      ${src === 'armory' ? `<span style="flex:1"></span><button class="mini" onclick="setAppMode('armory')">${tt('cards.gen_back_armory')}</button>` : ''}</div>`;
  if(src === 'unit'){
    html += `<div class="armexprow"><b>${CG_UNIT.unit ? esc(CG_UNIT.unit) : `<span class="count">${tt('armory.exp_unit_none')}</span>`}</b>
        ${CG_UNIT.entry ? `<span class="count">${esc(CG_UNIT.entry)}</span>` : ''}
        ${CG_UNIT.unit ? `<button class="mini${CG_UNIT.picking ? ' on' : ''}" onclick="cgUnitChange()">${tt('armory.exp_unit_change')}</button>` : ''}</div>
      ${cgUgHtml()}`;
    if(cgPicking()) html += cgUnitPickHtml();
  }else html += `<div class="count">${tt('cards.gen_src_armory_note')}</div>`;
  return cgSec('source', tt('cards.gen_source_legend'), html);
}
/* 2026-11-24: which of the unit's armour upgrade models the card is of. */
function cgUgHtml(){
  const u = ((CG_UNIT.units || {}).list || []).find(x => x.type === CG_UNIT.unit);
  if(!u || CG_UNIT.picking) return '';
  return cgUgSelect(u, CG_UNIT.entry, `cgUnitLoad(${esc(JSON.stringify(u.type))},this.value,'level')`) + cgTexHtml();
}
/* 2026-11-24: whose textures the model wears. A model lists a texture per
   group of factions (its modeldb skins); the faction picked here wears its
   own, and comes first when the card is saved. */
function cgTexHtml(){
  const skins = (CG_UNIT.skins || []).filter(k => k.exists !== false);
  if(skins.length < 2) return '';
  const c = cg();
  return cgField(tt('cards.gen_tex'), `<select onchange="cgTexPick(this.value)"><option value="">${tt('cards.gen_tex_default')}</option>
    ${(CG_UNIT.skins || []).map((k,i) => k.exists === false ? '' : `<optgroup label="${esc(tt('cards.gen_tex_n',{n:i+1}))}">${(k.factions || []).map(f =>
      `<option value="${esc(f)}"${c.texFaction === f ? ' selected' : ''}>${esc(f)}</option>`).join('')}</optgroup>`).join('')}</select>`, tt('cards.gen_tex_title'));
}
const cgSkinOf = f => f ? Math.max(0, (CG_UNIT.skins || []).findIndex(k => (k.factions || []).includes(f))) : 0;
async function cgTexPick(f){
  const c = cg(); c.texFaction = f; c.give = null;
  const a = {kind: 'entry', mod: CG_UNIT.mod, entry: CG_UNIT.entry}, live = ARM.assets.get(armAssetKey(a));
  if(live) await armLoadSkin({...a, skin: cgSkinOf(f)}, live);
  cgDraw();
}
/* armour_ug_models lists a model per upgrade level from 0. 2026-11-24: only
   those are offered and loaded; the soldier line's model only for a unit with
   no such list. One model at every level: the list greyed out, and said so.
   Also in the unit picker's 3D view. */
const cgUnitModel = u => ((u.ug || [])[0] || u.soldier || '');
function cgUgSelect(u, current, onchange){
  const ug = (u.ug || []).map(m => m.toLowerCase()), soldier = (u.soldier || '').toLowerCase();
  const models = ug.length ? ug.map((m,i) => [m, tt('cards.gen_ug_level',{level:i})]) : soldier ? [[soldier, tt('cards.gen_ug_base')]] : [];
  if(!models.length) return '';
  const same = new Set(models.map(m => m[0])).size < 2, at = models.findIndex(m => m[0] === current);
  return cgField(tt('cards.gen_ug'), `<select${same ? ' disabled' : ''} onchange="${onchange}">${models.map(([m,label],i) =>
    `<option value="${esc(m)}"${i === at ? ' selected' : ''}>${esc(label)} · ${esc(m)}</option>`).join('')}</select>${same ? `<span class="count">${tt('cards.gen_ug_same')}</span>` : ''}`);
}
/* 2026-11-24: a label beside its drop-down, not round it: a <label> round a
   <select> opened it from a click anywhere along the row. */
function cgField(label, inner, title){
  return `<div class="cgfield"${title ? ` title="${esc(title)}"` : ''}><span>${label}</span>${inner}</div>`;
}
function cgUnitChange(){
  CG_UNIT.picking = !CG_UNIT.picking;
  if(CG_UNIT.picking && CG_UNIT.unit && (!CG_UNIT.peek || CG_UNIT.peek.type !== CG_UNIT.unit)) cgUnitPeek(CG_UNIT.unit);
  cgPaint();
}
async function renderCardGen(){
  const serial = ++CG_WORK.serial, mod = state.src;
  if(cgSrc() === 'unit'){
    if(CG_UNIT.mod && CG_UNIT.mod !== mod){ CG_UNIT.objects = []; CG_UNIT.unit = ''; CG_UNIT.entry = ''; CG_UNIT.anim = null; }
    if(!CG_UNIT.units || CG_UNIT.units.mod !== mod){
      try{ CG_UNIT.units = {mod, list: (await api.get('/api/armory/templates?mod=' + enc(mod))).units || []}; }
      catch(e){ CG_UNIT.units = {mod, list: []}; }
    }
    if(CG_UNIT.unit) cgUnitAnimIn();
  }else cgUnitAnimOut();
  if(cgHere()) main.innerHTML = bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit')) + cardsSubTabsHtml() + `<div class="armempty">${tt('armory.reading')}</div>`;
  try{
    await armEnsureLoaded(); await ARM.loading;
    const reads = [];
    if(CG_WORK.mod !== mod){
      CG_WORK.mod = mod; CG_WORK.sizes = null;
      reads.push(api.get('/api/armory/card_sizes?mod=' + enc(mod)).then(r => { if(CG_WORK.mod === mod) CG_WORK.sizes = r; }).catch(() => {}));
    }
    if(!CG_WORK.library) reads.push(api.get('/api/armory/poses').then(r => { CG_WORK.library = r; }).catch(() => {}));
    if(!CG_WORK.saved) reads.push(api.get('/api/armory/poses/saved').then(r => { CG_WORK.saved = r.poses || []; }).catch(() => {}));
    await Promise.all(reads);
    if(serial !== CG_WORK.serial || !cgHere() || state.src !== mod) return;
    if(cg().fit.auto) CG_WORK.fit = null;
    if(cgObjects().length && (cgSrc() === 'armory' || ARM.anim && ARM.anim.list)) await cgPreparePose();
    if(serial !== CG_WORK.serial || !cgHere() || state.src !== mod) return;
    cgPaint();
  }catch(e){ if(cgHere() && serial === CG_WORK.serial){ cg().err = errText(e); cgPaint(); } }
}
function cgSelectHtml(group, key, choices){
  const value = group ? cg()[group][key] : cg()[key];
  // a choice of null is a bar between groups of them
  return `<select onchange="cgSet('${group}','${key}',this.value,true)">${choices.map(([v,l]) => v == null ? '<option disabled>──────────</option>'
    : `<option value="${esc(v)}"${String(value) === String(v) ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
}
function cgCheckHtml(group,key,label){
  const value = group ? cg()[group][key] : cg()[key];
  return `<label class="armcheck"><input type="checkbox" ${value ? 'checked' : ''} onchange="cgSet('${group}','${key}',this.checked,true)">${tt(label)}</label>`;
}
function cgRange(group,key,label,min,max,step){
  const value = cg()[group][key];
  return `<label class="cgrange"><span>${tt(label)}</span><input type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-cg-group="${group}" data-cg-key="${key}" oninput="cgSet('${group}','${key}',+this.value,false)"><span id="cgv_${group}_${key}">${Math.round(value*100)/100}</span></label>`;
}
function cgSizeHtml(){
  const c = cg(), sizes = CG_WORK.sizes || {};
  // 2026-11-23: a drop-down, not six radio buttons
  return cgSec('size', tt('cards.gen_size'), `<select title="${ttA('cards.gen_size_mod_title')}" onchange="cgSet('','size',this.value,true)">${['card','large','info','custom','modcard','modinfo'].map(k => {
    const unavailable = k === 'modcard' && !sizes.card || k === 'modinfo' && !sizes.info;
    return `<option value="${k}"${c.size === k ? ' selected' : ''}${unavailable ? ' disabled' : ''}>${unavailable ? tt('cards.gen_size_mod_none',{size:tt(CG_SIZE_KEYS[k])}) : tt(CG_SIZE_KEYS[k])}</option>`;
  }).join('')}</select>
    ${c.size === 'custom' ? `<div class="armexprow"><input class="armnum" type="number" min="8" value="${c.w}" onchange="cgSet('','w',Math.max(8,+this.value),true)"> × <input class="armnum" type="number" min="8" value="${c.h}" onchange="cgSet('','h',Math.max(8,+this.value),true)"></div>` : ''}
    ${cgField(tt('cards.gen_mult'), cgSelectHtml('','mult',[1,2,3,4].map(n => [n,String(n)])), tt('cards.gen_mult_title'))}
    ${cgField(tt('cards.gen_render_at'), cgSelectHtml('','ss',[10,15,20,25,30,35,40].map(n => [n,String(n) + '×'])))}`);
}
function cgPoseHtml(){
  const c = cg(), a = armAnim(), entries = cgSrc() === 'unit' ? [] : armAnimEntries(), skels = a.list && a.list.skeletons || {};
  const actions = (skels[a.skel.toLowerCase()] || {}).actions || [];
  return cgSec('pose', tt('cards.gen_pose'), `${cgSelectHtml('','pose',['rig','anim','tpose',null,'guard','brace','draw','riding','march'].map(x => x ? [x,tt(CG_POSE_KEYS[x])] : [null,'']))}
    ${cgSrc() === 'unit' ? '' : `<select onchange="cgEntry(this.value)"><option value="">${tt('cards.gen_pick_entry')}</option>`}${entries.map(e => `<option value="${esc(armAssetKey(e))}"${(armProj().anim || {}).asset === armAssetKey(e) ? ' selected' : ''}>${esc(armAssetLabel(e))}</option>`).join('')}${cgSrc() === 'unit' ? '' : '</select>'}
    ${Object.keys(skels).length ? `<select onchange="cgSkeleton(this.value)">${Object.keys(skels).map(s => `<option value="${esc(s)}"${s === a.skel.toLowerCase() ? ' selected' : ''}>${esc(s)}</option>`).join('')}</select>` : ''}
    ${c.pose === 'anim' ? `<select onchange="cgAction(this.value)">${actions.filter(x => x.playable).map(x => { const key = x.slot != null ? String(x.slot) : 'a:' + x.action; return `<option value="${esc(key)}"${a.key === key ? ' selected' : ''}>${esc(x.action)}</option>`; }).join('')}</select><input type="range" min="0" max="1000" value="${armAnimFrac()}" oninput="cgScrub(+this.value)">` : ''}
    <div class="count">${esc(c.poseNote || '')}</div><div class="count">${esc(c.poseNote2 || '')}</div>
    ${c.pose === 'rig' ? cgRigHtml() : ''}`) + (c.pose === 'rig' ? cgLibraryHtml() : '');
}
function cgRigHtml(){
  const r = cg().rig;
  return `<div class="cgrig">${cgField(tt('cards.gen_rig'), cgSelectHtml('rig','type',[['auto',tt('cards.gen_rig_auto',{rig:cgRigType()})],...['infantry','archer','dwarf'].map(t => [t,t])]))}
    <label class="armcheck" title="${ttA('cards.gen_two_hands_title')}"><input type="checkbox" ${((r.basis.Switch || {}).l || [0,0])[1] > 0 ? 'checked' : ''} onchange="cgTwoHands(this.checked)">${tt('cards.gen_two_hands')}</label>
    <button class="mini" onclick="cg().rig.basis={};cgFitChanged();cgPaint()">${tt('cards.gen_rig_reset')}</button>
    <div id="cgBone">${cgBoneHtml()}</div></div>`;
}
/* 2026-11-23: the pose library as pictures, each pose drawn on this model
   (cgPoseThumbs), as the Blender kit's asset browser shows them. */
/* 2026-11-24: a folder shows the poses in the folders under it too, IK Full
   the first shown; the head, legs, posture and Med2 skeleton folders are left
   out. Poses saved here (config/armory/poses.json) are in Saved. */
const CG_POSE_HIDE = /^(Med2 Skeletons|IK Bodyparts\/IK (Head|Legs|Posture))(\/|$)/;
function cgLibPoses(){ return [...((CG_WORK.library || {}).poses || []),...(CG_WORK.saved || [])]; }
/* The folder armory.save_pose puts a saved pose in, whatever its case. */
const cgSavedFolder = c => String(c || '').toLowerCase() === 'saved';
const cgInFolder = (p,cat) => p.c === cat || p.c.startsWith(cat + '/');
function cgLibraryHtml(){
  const r = cg().rig, poses = cgLibPoses(), folders = new Set();
  for(const p of poses){
    if(CG_POSE_HIDE.test(p.c)) continue;
    const parts = p.c.split('/');
    for(let i=1;i<=parts.length;i++) folders.add(parts.slice(0,i).join('/'));
  }
  const cats = [...folders].sort();
  if(!cats.includes(r.cat)) r.cat = cats.includes('IK Full') ? 'IK Full' : cats[0] || '';
  const label = x => cgSavedFolder(x) ? tt('cards.gen_pose_folder_saved') : '  '.repeat(x.split('/').length-1) + x.split('/').pop();
  return cgSec('library', tt('cards.gen_library'), `${cgSelectHtml('rig','cat',cats.map(x => [x,label(x)]))}${cgField(tt('cards.gen_apply_to'), cgSelectHtml('rig','part',['whole','arms','legs','head','posture'].map(x => [x,tt(CG_PART_KEYS[x])])))}
    <div title="${ttA('cards.gen_pose_cam_reset_title')}">${cgCheckHtml('rig','camReset','cards.gen_pose_cam_reset')}</div>
    <div class="armexprow"><input id="cgPoseName" placeholder="${ttA('cards.gen_pose_name')}" style="flex:1;min-width:0"><button class="mini" onclick="cgPoseSave()">${tt('cards.gen_pose_save')}</button></div>
    <div class="cgposes">${poses.map((p,i) => cgInFolder(p,r.cat) && !CG_POSE_HIDE.test(p.c) ? `<button class="cgpose${r.pick === p.n ? ' on' : ''}" onclick="cgLibraryPose(${i})" title="${esc(p.n)}"><img data-cgpose="${i}" alt=""><span>${esc(p.n)}</span>${cgSavedFolder(p.c) ? `<i class="cgposex" title="${ttA('cards.gen_pose_delete')}" onclick="event.stopPropagation();cgPoseDelete(${esc(JSON.stringify(p.n))})">✕</i>` : ''}</button>` : '').join('')}</div>`);
}
async function cgPoseSave(){
  const input = document.getElementById('cgPoseName'), r = cg().rig;
  const name = (input && input.value.trim()) || tt('cards.gen_pose_default',{n:(CG_WORK.saved || []).length+1});
  try{
    const res = await api.post('/api/armory/poses/save',{name,b:r.basis});
    CG_WORK.saved = res.poses || []; r.cat = (CG_WORK.saved[0] || {}).c || r.cat; r.pick = name;
    if(CG_WORK.poseThumbs) CG_WORK.poseThumbs.delete('Saved|' + name);
    toast(tt('cards.gen_pose_saved',{name})); cgPaint();
  }catch(e){ toast(errText(e)); }
}
async function cgPoseDelete(name){
  try{ const res = await api.post('/api/armory/poses/delete',{name}); CG_WORK.saved = res.poses || []; cgPaint(); }catch(e){ toast(errText(e)); }
}
function cgCameraHtml(){
  return cgSec('camera', tt('cards.gen_camera'), `${[['yaw','cards.gen_turn',-180,180,1],['pitch','cards.gen_tilt',-30,45,1],['scale','cards.gen_ortho_scale',0.4,3,0.05],['height','cards.gen_height',-1.5,1.5,0.02]].map(x => cgRange('cam',...x)).join('')}
    ${cgField(tt('cards.gen_framing'), cgSelectHtml('fit','part',['whole','knees','thighs','waist'].map(x => [x,tt(CG_FRAME_KEYS[x])])), tt('cards.gen_framing_hint'))}
    ${cgCheckHtml('fit','auto','cards.gen_fit_auto')}
    ${cgIsInfo() ? '' : `<div title="${ttA('cards.gen_guide_title')}">${cgCheckHtml('','guide','cards.gen_guide')}</div>`}
    <button class="mini" id="cgReset" ${cgPlacementReset() ? 'disabled' : ''} onclick="cg().xf={t:[0,0,0],r:[0,0,0],s:1};cg().cam.pan=0;cgPaint()">${tt('cards.gen_place_reset')}</button>
    <span class="armnav" title="${esc(tt('armory.nav_title'))}">${tt('armory.nav')}
      <button class="mini${armNav() === 'simple' ? ' on' : ''}" onclick="armNavSet('simple');cgPaint()">${tt('armory.nav_simple')}</button>
      <button class="mini${armNav() === 'blender' ? ' on' : ''}" onclick="armNavSet('blender');cgPaint()">${tt('armory.nav_blender')}</button></span>
    <p class="count">${tt(armNav() === 'simple' ? 'cards.gen_view_hint_simple' : 'cards.gen_view_hint')}</p>`);
}
function cgGroundHtml(){
  const c = cg();
  const choices = ['none','colour','pic',...(cgIsInfo() ? ['scroll'] : ['strat','battle'])];
  return cgSec('ground', tt('cards.gen_ground'), `${cgSelectHtml('ground','kind',choices.map(x => [x,tt(CG_GROUND_KEYS[x])]))}
    ${c.ground.kind === 'colour' ? `<input type="color" value="${esc(c.ground.colour)}" oninput="cgSet('ground','colour',this.value,false)">` : ''}
    ${c.ground.kind === 'pic' ? `<label class="btn">${tt('cards.gen_ground_pick')}<input type="file" accept="image/*" onchange="cgPickGround(this.files[0])"></label>` : ''}
    <p class="count">${tt('cards.gen_ground_none_note')}</p>${cgIsInfo() ? cgCheckHtml('','gframe','cards.gen_game_frame') : ''}`);
}
function cgLightHtml(){
  const c = cg(), flat = !!c.light.flat, extra = c.lights || [];
  const lamp = ['azimuth','cards.gen_azimuth',-180,180,1], tilt = ['elevation','cards.gen_elevation',-60,89,1], amount = ['amount','cards.gen_amount',0,2,0.01];
  const more = extra.map((x,i) => `<div class="cglamp"><div class="armexprow"><b>${tt('cards.gen_light_n',{n:i+2})}</b>
      <select onchange="cgLamp(${i},'type',this.value)">${['sun','point'].map(k => `<option value="${k}"${x.type === k ? ' selected' : ''}>${tt(CG_LIGHT_KEYS[k])}</option>`).join('')}</select>
      <span style="flex:1"></span><button class="mini" title="${ttA('cards.gen_light_remove')}" onclick="cgLampRemove(${i})">✕</button></div>
    ${[lamp,tilt,amount].map(([k,label,min,max,step]) => `<label class="cgrange"><span>${tt(label)}</span><input type="range" min="${min}" max="${max}" step="${step}" value="${x[k]}" oninput="cgLamp(${i},'${k}',+this.value);this.nextElementSibling.textContent=Math.round(this.value*100)/100"><span>${Math.round(x[k]*100)/100}</span></label>`).join('')}</div>`).join('');
  return cgSec('light', tt('cards.gen_light'), `<div class="armexprow" title="${ttA('cards.gen_light_flat_title')}">
      <button class="mini${flat ? '' : ' on'}" onclick="cgSet('light','flat',false,true)">${tt('cards.gen_light_lit')}</button>
      <button class="mini${flat ? ' on' : ''}" onclick="cgSet('light','flat',true,true)">${tt('cards.gen_light_flat')}</button></div>
    ${flat ? '' : `<div>${['sun','point'].map(x => `<label><input type="radio" name="cgLight" ${c.light.type === x ? 'checked' : ''} onchange="cgSet('light','type','${x}',false)">${tt(CG_LIGHT_KEYS[x])}</label>`).join('')}</div>
    ${[lamp,tilt,amount,['level','cards.gen_level',0.2,2.5,0.01],['ambient','cards.gen_ambient',0,1,0.01]].map(x => cgRange('light',...x)).join('')}
    ${more}${extra.length < CG_LIGHTS_MAX-1 ? `<button class="mini" onclick="cgLampAdd()">${tt('cards.gen_light_add')}</button>` : ''}`}`);
}
function cgLampAdd(){ const c = cg(); c.lights = [...(c.lights || []),{type:'sun',azimuth:-120,elevation:25,amount:0.5}].slice(0,CG_LIGHTS_MAX-1); cgPaint(); }
function cgLampRemove(i){ const c = cg(); c.lights = (c.lights || []).filter((x,k) => k !== i); cgPaint(); }
function cgLamp(i,key,value){ const c = cg(); c.lights = (c.lights || []).map((x,k) => k === i ? {...x,[key]:value} : x); cgDraw(); }
function cgFinishHtml(){
  return cgSec('painted', tt('cards.gen_painted'), `${cgCheckHtml('paint','on','cards.gen_painted_on')}
    <div title="${ttA('cards.gen_painted_title')}">${cgRange('paint','strength','cards.gen_painted_strength',0.3,2,0.05)}</div>`)
    + cgSec('finish', tt('cards.gen_finish'), `${[['blur',0,2,0.05],['exposure',-2,2,0.05],['brightness',-0.5,0.5,0.01],['contrast',0.3,2,0.01],['gamma',0.3,3,0.01],['saturation',0,2,0.01],['hue',-180,180,1],['sharpen',0,1,0.01],['outline',0,1.5,0.05]].map(([k,...range]) => cgRange('post',k,CG_FINISH_KEYS[k],...range)).join('')}`);
}
function cgPaint(){
  if(!cgHere()) return;
  const c = cg(), objects = cgObjects(), picking = cgPicking(), keep = cgScrollKeep();
  const nav = bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit')) + cardsSubTabsHtml();
  if(!picking && !cgAllObjects().length){
    main.innerHTML = nav + `<div class="cggrid"><div class="cgctl">${cgSourceHtml()}<div class="armexperr" id="cgError">${esc(c.err || '')}</div></div>
      <div class="armempty">${cgSrc() === 'unit' ? (CG_UNIT.unit ? (c.err ? `<button class="btn" onclick="cgRetry(${esc(JSON.stringify(CG_UNIT.unit))},${esc(JSON.stringify(CG_UNIT.entry))})">${tt('cards.gen_retry')}</button>` : tt('armory.reading')) : tt('cards.gen_pick_unit_first'))
        : `${tt('cards.gen_no_model')}<br><button class="btn" onclick="setAppMode('armory')">${tt('core.armory_studio')}</button>`}</div></div>`;
    cgLayout(); keep();
    return;
  }
  const [w,h] = cgDimensions(), ss = Math.min(Number(c.ss),4096/Math.max(w,h)), hw = Math.min(4096,Math.round(w*ss)), hh = Math.min(4096,Math.round(h*ss));
  CG_WORK.hdSize = [hw,hh];
  const controls = picking ? '' : `<div class="count">${cgSrc() === 'unit' ? ttN('cards.gen_source_unit',objects.length,{entry:esc(CG_UNIT.entry)}) : ttN('cards.gen_source',objects.length)}</div>
    <div class="armexprow">${cgCheckHtml('','oneEach','cards.gen_one_each')}<button class="mini" title="${ttA('cards.gen_random_title')}" onclick="cgRandom()">${tt('cards.gen_random')}</button></div>
    ${cgGearHtml()}
    ${cgSizeHtml()}${cgPoseHtml()}${cgCameraHtml()}${cgGroundHtml()}${cgLightHtml()}${cgFinishHtml()}
    ${cgSec('save', tt('cards.gen_save_legend'), `${cgSrc() === 'unit' ? '' : `<input value="${esc(c.name)}" placeholder="${ttA('cards.gen_name_hint')}" oninput="cg().name=this.value">`}
    <div class="armexprow"><button class="primary" onclick="cgSave(false)">${tt('cards.gen_save')}</button><button onclick="cgSave(true)">${tt('cards.gen_save_hd')}</button></div>
    <div id="cgSaveResult">${cgSavedHtml()}</div>`)}`;
  const right = picking ? cgPeekHtml() : `<div class="cgout"><div class="cghd"><div class="armexprow cgviewbar" id="cgViewBar">${cgViewBarHtml(hw,hh)}</div><div class="cghdview" id="cgHdView"><canvas id="cgHd" tabindex="0" width="${hw}" height="${hh}"></canvas><canvas id="cgHdUi"></canvas>${cgKeysHtml()}</div></div>
    <div class="cgcard"><span class="count">${tt('cards.gen_card',{w,h})}</span><canvas id="cgCard" width="${w}" height="${h}" style="image-rendering:pixelated;width:${w*3}px;max-width:100%;height:auto"></canvas>
    <div id="cgObjs">${cgObjListHtml()}</div></div></div>`;
  main.innerHTML = nav + `<div class="cggrid"><div class="cgctl">${cgSourceHtml()}${controls}<div class="armexperr" id="cgError">${esc(c.err || '')}</div></div>${right}</div>`;
  cgLayout(); keep();
  if(picking){ cgPeekPaint(); return; }
  cgWire(); cgDraw(); cgPoseThumbs();
  if(armObjGallery()) armThumbsPaint();
}
/* 2026-11-23: a repaint leaves each column scrolled where it was. */
function cgScrollKeep(){
  const parts = ['.cgctl','.cgcard','.cgout'], tops = parts.map(k => { const el = main.querySelector(k); return el ? el.scrollTop : 0; });
  return () => parts.forEach((k,i) => { const el = main.querySelector(k); if(el) el.scrollTop = tops[i]; });
}
/* The page fits the window: each column scrolls on its own, the page never. */
function cgLayout(){
  const grid = main.querySelector('.cggrid');
  if(!grid) return;
  const pad = parseFloat(getComputedStyle(main).paddingBottom) || 0;
  const bottom = Math.min(innerHeight, main.getBoundingClientRect().bottom) - pad;
  const h = Math.max(320, Math.floor(bottom - grid.getBoundingClientRect().top - 2));
  // one column (a narrow window): the page scrolls as any other
  const one = getComputedStyle(grid).gridTemplateColumns.trim().split(/\s+/).length < 2;
  grid.style.height = one ? '' : h + 'px'; grid.style.setProperty('--cgh', h + 'px');
  // 2026-11-24: what the page still runs over by (margins, a border) taken
  // off, so it never gets a second scroll bar that moves a few pixels
  const over = one ? 0 : Math.max(main.scrollHeight - main.clientHeight, document.documentElement.scrollHeight - innerHeight);
  if(over > 0){ const fit = Math.max(320, h - over - 1); grid.style.height = fit + 'px'; grid.style.setProperty('--cgh', fit + 'px'); }
  if(!CG_WORK.layoutWired){
    CG_WORK.layoutWired = true;
    addEventListener('resize', () => { if(cgHere()){ cgLayout(); if(cgPicking()) cgPeekPaint(); } });
  }
}
/* The card's object list, under the card: Armory Studio's, by part. A click
   picks the variant of its part drawn with One of each part; the eye leaves
   an object out of the card. */
function cgObjListHtml(){
  const c = cg(), all = cgAllObjects(), off = new Set(c.off || []), drawn = new Set(cgObjects().map(o => o.id)), gal = armObjGallery();
  const groups = new Map();
  for(const o of all){ const k = cgPartKey(o); if(!groups.has(k)) groups.set(k, []); groups.get(k).push(o); }
  const row = o => {
    const cls = `${drawn.has(o.id) ? ' sel' : ''}${off.has(o.id) ? ' off' : ''}${CG_WORK.objSel === o.id ? ' cur' : ''}`, eye = `<button class="mini armeye" onclick="event.stopPropagation();cgObjOff(${o.id})" title="${ttA('armory.hide_show')}">${off.has(o.id) ? '◌' : '●'}</button>`;
    const pc = (o.src || [])[0];
    return gal ? `<div class="armotile${cls}" onclick="cgObjPick(${o.id})" title="${esc(o.name + '__' + o.mesh)}"><img class="armthumb" data-thumb="${pc ? esc(pc.asset + '|' + pc.group) : ''}" alt="">
        <span class="armotilename">${esc(o.mesh)}</span>${eye}</div>`
      : `<div class="armrow${cls}" onclick="cgObjPick(${o.id})">${eye}<span class="armrowname">${esc(o.mesh)}${o.flag ? ` <i class="count">${tt('armory.opt')}</i>` : ''}</span></div>`;
  };
  const part = ([k, objs]) => `<div class="armfoldbox"><div class="armfoldhead"><b class="armfoldname">${esc(objs[0].name)}</b><span class="count">${objs.length}</span>
      <span style="flex:1"></span><button class="mini" title="${ttA('cards.gen_dup_part')}" onclick="cgDuplicate(${esc(JSON.stringify(objs.map(o => o.id)))},${esc(JSON.stringify(objs[0].name))})">⧉</button></div>
      ${gal ? `<div class="armotiles">${objs.map(row).join('')}</div>` : `<div class="armrows">${objs.map(row).join('')}</div>`}</div>`;
  // 2026-11-24: a fold per model, its parts' folds inside
  const body = [...cgGroups()].map(([gk, objs]) => {
    const name = cgGroupName(gk, objs), g = cgGroupXf(gk), dup = gk.startsWith('dup:') ? +gk.slice(4) : 0, q = esc(JSON.stringify(gk));
    const shown = objs.filter(o => drawn.has(o.id)).length, parts = new Map();
    for(const o of objs){ const k = cgPartKey(o); if(!parts.has(k)) parts.set(k, []); parts.get(k).push(o); }
    return `<details class="cggroup"${CG_SHUT.has('grp:' + gk) ? '' : ' open'} ontoggle="cgSecToggle(${esc(JSON.stringify('grp:' + gk))},this.open)">
      <summary><b>${esc(name)}</b> <span class="count">${shown} / ${objs.length}</span></summary>
      <div class="armexprow"><button class="mini${CG_WORK.grpSel === gk ? ' on' : ''}" title="${ttA('cards.gen_grp_pick_title')}" onclick="cgGroupPick(${q})">${tt('cards.gen_grp_pick')}</button>
        <button class="mini" title="${ttA('armory.hide_show')}" onclick="cgGroupHide(${q})">${objs.every(o => off.has(o.id)) ? '◌' : '●'}</button>
        <button class="mini" title="${ttA('cards.gen_dup_model_title')}" onclick="cgDuplicate(${esc(JSON.stringify(objs.map(o => o.id)))},${esc(JSON.stringify(name))})">${tt('cards.gen_dup_model')}</button>
        ${cgRiderSpotsHtml(gk, objs)}
        ${dup ? `<button class="mini" title="${ttA('cards.gen_dup_remove')}" onclick="cgDupRemove(${dup})">✕</button>` : ''}</div>
      <label class="cgrange"><span>${tt('cards.gen_grp_scale')}</span><input type="range" min="0.2" max="3" step="0.01" value="${Number(g.s) || 1}" oninput="cgGroupScale(${q},+this.value)"><span data-cggs="${esc(gk)}">${Math.round((Number(g.s) || 1)*100)/100}</span></label>
      ${[...parts].map(part).join('')}</details>`;
  }).join('');
  return cgSec('objects', `${tt('armory.objects')} <span class="count">${drawn.size} / ${all.length}</span>`, `<div class="armexprow"><span style="flex:1"></span>
      <button class="mini${gal ? '' : ' on'}" onclick="cgObjView('list')">${tt('armory.as_list')}</button>
      <button class="mini${gal ? ' on' : ''}" onclick="cgObjView('gallery')">${tt('armory.as_gallery')}</button></div>
    ${cgObjXfHtml()}<div class="armobjlist cgobjlist">${body}</div>`);
}
/* 2026-11-24: the object picked in the list moved, turned and scaled on the
   card alone (c.oxf, see cgXf). */
function cgObjXfHtml(){
  const id = CG_WORK.objSel, o = id && cgAllObjects().find(x => x.id === id);
  if(!o) return `<p class="count">${tt('cards.gen_obj_pick')}</p>`;
  const x = (cg().oxf || {})[id] || {t:[0,0,0],r:[0,0,0],s:[1,1,1]};
  const num = (k,i,v,step) => `<input class="armnum" type="number" step="${step}" value="${Math.round(v*1000)/1000}" data-cgxf="${k}${i}" onchange="cgObjXf('${k}',${i},+this.value)">`;
  return `<div class="cgobjxf"><div class="armexprow"><b>${esc(o.mesh)}</b><span class="count">${esc(o.name)}</span><span style="flex:1"></span>
      <button class="mini" onclick="cgObjXfReset()">${tt('cards.gen_obj_reset')}</button><button class="mini" title="${ttA('common.close')}" onclick="CG_WORK.objSel=0;cgPaint()">✕</button></div>
    <div class="cgbonegrid"><span>${tt('cards.gen_bone_loc')}</span>${x.t.map((v,i) => num('t',i,v,0.01)).join('')}
      <span>${tt('cards.gen_bone_rot')}</span>${x.r.map((v,i) => num('r',i,v,1)).join('')}
      <span>${tt('cards.gen_obj_scale')}</span>${x.s.map((v,i) => num('s',i,v,0.05)).join('')}</div>
    <label class="cgrange"><span>${tt('cards.gen_obj_size')}</span><input type="range" min="0.2" max="3" step="0.01" value="${x.s[0]}" oninput="cgObjXfAll(+this.value)"><span id="cgObjSize">${Math.round(x.s[0]*100)/100}</span></label></div>`;
}
function cgObjXfOf(){
  const c = cg(), id = CG_WORK.objSel;
  c.oxf = {...(c.oxf || {})};
  const x = c.oxf[id] = JSON.parse(JSON.stringify(c.oxf[id] || {t:[0,0,0],r:[0,0,0],s:[1,1,1]}));
  return x;
}
function cgObjXf(k,i,v){
  if(!CG_WORK.objSel || !isFinite(v)) return;
  const x = cgObjXfOf(); x[k][i] = k === 's' ? Math.max(0.01,v) : v;
  cgDraw();
}
function cgObjXfAll(v){
  if(!CG_WORK.objSel || !isFinite(v)) return;
  const x = cgObjXfOf(); x.s = [v,v,v];
  for(let i=0;i<3;i++){ const el = document.querySelector(`[data-cgxf="s${i}"]`); if(el) el.value = v; }
  const out = document.getElementById('cgObjSize'); if(out) out.textContent = Math.round(v*100)/100;
  cgDraw();
}
function cgObjXfReset(){
  const c = cg(); if(!c.oxf) return;
  c.oxf = {...c.oxf}; delete c.oxf[CG_WORK.objSel];
  cgPaint();
}
function cgObjView(v){
  state.settings.armory_obj_view = v;
  api.post('/api/settings', {armory_obj_view: v}).catch(() => {});
  cgPaint();
}
function cgObjPick(id){
  const c = cg(), o = cgAllObjects().find(x => x.id === id);
  if(!o) return;
  if(cgGearOff(o)) c.gear = 'custom';
  CG_WORK.objSel = id; CG_WORK.mode = 'object'; CG_WORK.selAll = false; CG_WORK.grpSel = '';
  c.pick = {...c.pick, [cgPartKey(o)]: id}; c.off = (c.off || []).filter(x => x !== id);
  cgFitChanged(); cgPaint();
}
function cgObjOff(id){
  const c = cg(), off = new Set(c.off || []);
  if(off.has(id)) off.delete(id); else off.add(id);
  c.off = [...off]; cgFitChanged(); cgPaint();
}
/* 2026-11-23: another of each part's variants, picked at random. */
function cgRandom(){
  const c = cg(), off = new Set(c.off || []), drawn = new Set(cgObjects().map(o => o.id)), groups = new Map();
  for(const o of cgAllObjects()) if(!off.has(o.id)){ const k = cgPartKey(o); if(!groups.has(k)) groups.set(k, []); groups.get(k).push(o); }
  const pick = {...c.pick};
  for(const [k, objs] of groups){
    if(objs.length < 2) continue;
    const others = objs.filter(o => !drawn.has(o.id));
    pick[k] = others[Math.floor(Math.random() * others.length)].id;
  }
  c.pick = pick; c.oneEach = true; cgFitChanged(); cgPaint();
}
function cgPlacementReset(){ const c = cg(); return !c.cam.pan && (c.xf.s || 1) === 1 && [...c.xf.t,...c.xf.r].every(v => !v); }
function cgSet(group,key,value,redraw){
  const c = cg(); (group ? c[group] : c)[key] = value;
  const out = document.getElementById('cgv_' + group + '_' + key); if(out) out.textContent = typeof value === 'number' ? Math.round(value*100)/100 : value;
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
async function cgPreparePose(){ await cgPoseAnim(); cgPoseAuto(); }
async function cgPoseAnim(){
  const c = cg(), a = armAnim(); c.poseNote = ''; c.poseNote2 = '';
  if(c.pose === 'tpose'){ armAnimRest(); a.playing = false; return; }
  // a rider and his horse both loaded: Riding is the rider's action, on the horse
  if(cgSrc() === 'armory' && c.pose === 'riding'){ const rider = await armAnimRider(); if(rider && (armProj().anim || {}).asset !== armAssetKey(rider)) await armAnimFrom(armAssetKey(rider)); }
  if(cgSrc() === 'armory' && !a.list){ const entry = armAnimEntries()[0]; if(entry) await armAnimFrom(armAssetKey(entry)); }
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
  await cgSeat();
}
/* 2026-11-24: a cavalry unit whose model has foot skeletons only (its actions
   are not a rider's, so nothing carried him): the unit's mount is set under
   him all the same, at its rider_offset, playing its standing action. */
async function cgSeat(){
  const a = armAnim();
  if(cgSrc() !== 'unit' || a.mount || !a.mountFor || !a.data || !cgSeated()) return;
  const slot = /^\d+$/.test(a.key || '') ? +a.key : null;
  const m = await a.mountFor(slot);
  if(m && armAnim() === a && a.data && !a.mount){ a.mount = m; CG_WORK.fit = null; }
}
/* A horse rides under its man; an elephant's crew stand in its howdah, beside. */
function cgSeated(){
  const u = ((CG_UNIT.units || {}).list || []).find(x => x.type === CG_UNIT.unit);
  return !!(u && u.mount && !u.engine && !/elephant|mumak|oliphaunt|howdah/i.test(u.mount));
}
function cgTwoHands(on){
  const basis = cg().rig.basis; basis.Switch = {...basis.Switch,l:[0,on ? 0.05 : 0,0]}; cgFitChanged(); cgDraw();
}
function cgLibraryPose(index,auto){
  const p = cgLibPoses()[index], r = cg().rig;
  r.basis = crApply(auto ? {} : r.basis,p,auto ? 'whole' : r.part); r.pick = p.n;
  if(r.camReset) cgCamDefault();
  cgFitChanged();
  if(!auto) cgPaint();
}
/* 2026-11-24: the camera the pose library's poses are made for: the card's
   default turn, tilt and size, nothing moved. */
function cgCamDefault(){
  const c = cg();
  c.cam = {yaw:20,pitch:4,scale:1.2,height:0,pan:0,persp:!!c.cam.persp}; c.xf = {t:[0,0,0],r:[0,0,0],s:1};
  CG_WORK.view = null; CG_WORK.fit = null;
}
/* 2026-11-24: the library opens on the folder for the skeleton played (a spear
   skeleton on Spears, a bow on Archer, orcs and dwarves on their own folders)
   with its first pose on the rig; once per skeleton, so a folder picked by
   hand stays. */
function cgPoseFolder(){
  const a = armAnim(), skel = (a.skel || '').toLowerCase(), cats = new Set(cgLibPoses().map(p => p.c));
  // a rider's set names his mount (modeldb's mount line), whatever its skeletons are called
  // 2026-11-24: an elephant's crew stand in a howdah: posed as men on foot
  const beast = /elephant|mumak|oliphaunt|howdah|crew/;
  // 2026-11-24: or the unit's own mount (EDU mount line): a cavalry model may
  // carry foot skeletons only, and was posed from Spears
  const u = cgSrc() === 'unit' ? ((CG_UNIT.units || {}).list || []).find(x => x.type === CG_UNIT.unit) : null;
  const rides = (a.set && a.set.mount && a.set.mount.toLowerCase() !== 'none') ? a.set.mount : u && u.mount && !u.engine ? u.mount : '';
  const riding = !!rides && !beast.test(rides.toLowerCase() + ' ' + skel);
  const base = cgRigType() === 'dwarf' ? 'IK Dwarves Full' : /orc|goblin|uruk|snaga/.test(skel) ? 'IK Orcs Full' : 'IK Full';
  // the subfolder by its name in the kit's library, any case
  const sub = /crossbow/.test(skel) ? 'crossbow' : /bow|archer|sling/.test(skel) ? 'archer' : /javelin/.test(skel) ? 'javelin'
    : riding || !beast.test(skel) && /cavalry|mounted|horse|lance|camel|_cav|rider/.test(skel) ? 'mounted'
    : /pike|halberd|polearm|poleaxe|glaive|bill|partisan|voulge/.test(skel) ? 'polearm' : /spear/.test(skel) ? 'spears'
    : /2h|two_?hand|2handed|great|maul|zweihand/.test(skel) ? '2h' : '1h';
  const under = top => [...cats].find(x => x.toLowerCase() === (top + '/' + sub).toLowerCase());
  return under(base) || under('IK Full') || [base, 'IK Full'].find(x => cats.has(x)) || '';
}
function cgPoseAuto(){
  const c = cg(), r = c.rig, skel = (armAnim().skel || '').toLowerCase();
  if(c.pose !== 'rig' || !skel || r.autoFor === skel || !CG_WORK.library) return;
  const folder = cgPoseFolder();
  if(!folder) return;
  r.autoFor = skel; r.cat = folder;
  const i = cgLibPoses().findIndex(p => p.c === folder);
  if(i >= 0) cgLibraryPose(i,true);
}
function cgCanvas(w,h){ const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h; return canvas; }
function cgBounds(objects){
  let b = armBounds(objects);
  const a = armAnim();
  if(a.data){
    const lo = [Infinity,Infinity,Infinity], hi = [-Infinity,-Infinity,-Infinity];
    for(const o of objects){ const g = a.geos.get(o.id); if(cgStill(o) || !g || !g.posed) continue; const p = g.outPos, m = o.post;
      for(let i=0;i<p.length;i+=3){ const q = m ? cgMatrixPoint(m,[p[i],p[i+1],p[i+2]]) : [p[i],p[i+1],p[i+2]];
        for(let k=0;k<3;k++){ lo[k]=Math.min(lo[k],q[k]); hi[k]=Math.max(hi[k],q[k]); } }
    }
    // a mount or engine beside the unit stands as it is
    const still = objects.some(cgStill) && armBounds(objects.filter(cgStill));
    if(still && isFinite(lo[0])) for(let k=0;k<3;k++){ lo[k] = Math.min(lo[k],still[0][k]); hi[k] = Math.max(hi[k],still[1][k]); }
    if(isFinite(lo[0])) b = [lo,hi];
  }
  return b || [[-0.5,0,-0.5],[0.5,2,0.5]];
}
function cgMatrixPoint(m,p){ return [0,1,2].map(k => m[k]*p[0]+m[k+4]*p[1]+m[k+8]*p[2]+m[k+12]); }
/* Through a projection: divided by w, so a perspective camera's points land too. */
function cgProject(m,p){ const q = cgMatrixPoint(m,p), w = m[3]*p[0]+m[7]*p[1]+m[11]*p[2]+m[15] || 1; return q.map(v => v/w); }
/* 2026-11-24: Orthographic (the game's cards) or Perspective, for the view and
   the card alike. A perspective eye stands where the same height fills the
   frame at the model's middle. */
const CG_FOV = 0.6;
function cgLens(target,yaw,pitch,height,width){
  const persp = !!cg().cam.persp, dist = persp ? height/2/Math.tan(CG_FOV/2) : 10;
  const eye = [target[0]+dist*Math.cos(pitch)*Math.sin(yaw),target[1]+dist*Math.sin(pitch),target[2]+dist*Math.cos(pitch)*Math.cos(yaw)];
  const proj = persp ? v3Perspective(CG_FOV,width/height,dist/50,dist*20) : [2/width,0,0,0,0,2/height,0,0,0,0,-0.01,0,0,0,0,1];
  return {eye,proj,view:v3LookAt(eye,target,[0,1,0])};
}
function cgCamera(objects,w,h){
  const c = cg(), [lo,hi] = cgBounds(objects), center = lo.map((v,i) => (v+hi[i])/2);
  const r = c.xf.r, t = c.xf.t;
  const k = Number(c.xf.s) || 1;
  const pre = armMul(armTrans(center[0]+t[0],center[1]+t[1],center[2]+t[2]),armMul(armRot(...r),armMul(armScale(k,k,k),armTrans(-center[0],-center[1],-center[2]))));
  if(!CG_WORK.fit){
    const fraction = {whole:1,knees:0.78,thighs:0.64,waist:0.5}[c.fit.part] || 1;
    const height = Math.max(0.1,hi[1]-lo[1]);
    CG_WORK.fit = {height:Math.max(height*fraction*1.12,(hi[0]-lo[0])*h/w*1.12),target:[-center[0],hi[1]-height*fraction/2,center[2]],
      center:[-center[0],center[1],center[2]],full:Math.max(height,hi[0]-lo[0],hi[2]-lo[2])};
  }
  const fit = CG_WORK.fit, height = fit.height * c.cam.scale, width = height*w/h;
  const target = [...fit.target]; target[0] += c.cam.pan; target[1] += c.cam.height;
  const {eye,proj,view} = cgLens(target,c.cam.yaw*Math.PI/180,c.cam.pitch*Math.PI/180,height,width);
  return {proj,view,eye,pre,height,width,target};
}
/* 2026-11-24: the main lamp and up to three more (c.lights), each a sun or a
   point turning with the camera; Flat is no lamp and a full ambient, Blender's
   Flat lighting with the texture's own colour. */
const CG_LIGHTS_MAX = 4;
function cgLight(camera,yaw){
  const c = cg(), l = c.light;
  if(l.flat) return {ambient:1,level:1,list:[]};
  const lamp = x => {
    const az = (Number(x.azimuth)+Number(yaw != null ? yaw : c.cam.yaw))*Math.PI/180, el = Number(x.elevation)*Math.PI/180;
    const dir = [Math.sin(az)*Math.cos(el),Math.sin(el),Math.cos(az)*Math.cos(el)];
    return {point:x.type === 'point',amount:Number(x.amount),dir,pos:camera.target.map((v,i) => v+dir[i]*4)};
  };
  return {ambient:l.ambient,level:l.level,list:[l,...(c.lights || [])].slice(0,CG_LIGHTS_MAX).map(lamp)};
}
/* 2026-11-23: the HD view is a viewport of its own, as Armory Studio's is: it
   turns about a fixed point (the model's middle, set when the model is
   shown), the wheel zooms it, a pan moves it, and the card's frame is drawn
   where the card's camera sees. It is drawn plain, at the screen's own size,
   every frame; the card (the HD render, its outline and finish) is made a
   moment after the last change (cgCardDraw), so a drag stays smooth. */
function cgViewState(){ return CG_WORK.view = CG_WORK.view || {zoom:1,pivot:null,full:0}; }
function cgViewReset(){ CG_WORK.view = null; cgViewAsk(); }
function cgViewCamera(card,w,h){
  const c = cg(), v = cgViewState(), fit = CG_WORK.fit;
  // first shown: the whole model and the card's frame in view
  if(!v.pivot){ v.pivot = fit.center.slice(); v.full = Math.max(fit.full,2*(Math.abs(card.target[1]-fit.center[1])+card.height/2),card.width*h/w); }
  const yaw = c.cam.yaw*Math.PI/180, pitch = c.cam.pitch*Math.PI/180;
  const height = v.full*1.1/v.zoom, width = height*w/h;
  const target = v.pivot.slice(), {eye,proj,view} = cgLens(target,yaw,pitch,height,width);
  // the card's frame: its camera looks the same way, so its corners, upright
  // across the line of sight at its middle, are enough
  const right = [Math.cos(yaw),0,-Math.sin(yaw)], up = [-Math.sin(pitch)*Math.sin(yaw),Math.cos(pitch),-Math.sin(pitch)*Math.cos(yaw)], m = armMul(proj,view);
  const corner = (a,b) => { const q = cgProject(m,card.target.map((x,k) => x+right[k]*a*card.width/2+up[k]*b*card.height/2)); return [(q[0]+1)*w/2,(1-q[1])*h/2]; };
  const p0 = corner(-1,1), p1 = corner(1,-1);
  return {camera:{proj,view,eye,pre:card.pre,height,width,target},cut:{x:Math.min(p0[0],p1[0]),y:Math.min(p0[1],p1[1]),w:Math.abs(p1[0]-p0[0]),h:Math.abs(p1[1]-p0[1])}};
}
/* A pan moves the point the view turns about (Blender's Shift + middle drag). */
function cgViewPan(dx,dy){
  const v = cgViewState(), cam = CG_WORK.camera, hd = document.getElementById('cgHd');
  if(!v.pivot || !cam || !hd) return;
  const yaw = cg().cam.yaw*Math.PI/180, pitch = cg().cam.pitch*Math.PI/180;
  const right = [Math.cos(yaw),0,-Math.sin(yaw)], up = [-Math.sin(pitch)*Math.sin(yaw),Math.cos(pitch),-Math.sin(pitch)*Math.cos(yaw)];
  const sx = -dx*cam.width/hd.width, sy = dy*cam.height/hd.height;
  v.pivot = v.pivot.map((x,k) => x+right[k]*sx+up[k]*sy);
  cgViewAsk();
}
function cgViewAsk(){
  if(CG_WORK.viewAsked) return;
  CG_WORK.viewAsked = true;
  const go = () => { CG_WORK.viewAsked = false; cgView(); };
  // requestAnimationFrame never fires in a hidden tab
  if(document.hidden) setTimeout(go,0); else requestAnimationFrame(go);
}
function cgView(){
  const hd = document.getElementById('cgHd');
  if(!hd || !cgHere()) return;
  const box = hd.getBoundingClientRect(), ratio = Math.min(2,devicePixelRatio || 1);
  const w = Math.max(64,Math.round(box.width*ratio)), h = Math.max(64,Math.round(box.height*ratio));
  if(hd.width !== w || hd.height !== h){ hd.width = w; hd.height = h; }
  const c = cg(), objects = cgObjects(), [cw,ch] = CG_WORK.hdSize || [480,640];
  try{
    if(CG_WORK.posed !== CG_WORK.poseGen){ cgPose(cgMoving(objects)); CG_WORK.posed = CG_WORK.poseGen; }
    const card = cgCamera(objects,cw,ch), seen = cgViewCamera(card,w,h);
    CG_WORK.camera = seen.camera; CG_WORK.cut = seen.cut; CG_WORK.cardCam = card;
    // the objects picked in Object mode lit up, as Armory Studio's hover is
    const hi = cgMode() === 'object' ? new Set(cgSelected()) : null;
    if(!armRender(objects,w,h,seen.camera,{plain:true,card:true,pre:card.pre,light:cgLight(card),bg:[0.2,0.22,0.26],hi})) return;
    const ctx = hd.getContext('2d'); ctx.drawImage(ARM.glCanvas,0,0,w,h,0,0,w,h);
    cgOverlay();
  }catch(e){ c.err = errText(e); const error = document.getElementById('cgError'); if(error) error.textContent = c.err; }
}
/* --- 2026-11-24: the HD view's own bar, as Blender's header is -------------
   Object mode picks the model's objects (a click, A for all) and G, R and S
   move, turn and scale them; Pose mode the rig's controllers; Rest shows the
   rig at rest. On the right: the card's frame and guide (Overlay), the rig's
   handles (Bones) and the lens. */
function cgMode(){ const m = CG_WORK.mode || 'pose'; return m === 'pose' && !cgRigActive() ? 'object' : m; }
function cgViewBarHtml(hw,hh){
  const c = cg(), mode = cgMode(), rig = cgRigActive(), b = (on,label,title,click,off) =>
    `<button class="mini${on ? ' on' : ''}" title="${ttA(title)}" onclick="${click}"${off ? ' disabled' : ''}>${tt(label)}</button>`;
  return `${b(mode === 'object','cards.gen_mode_object','cards.gen_mode_object_title',"cgModeSet('object')")}
    ${b(mode === 'pose','cards.gen_mode_pose','cards.gen_mode_pose_title',"cgModeSet('pose')",!rig)}
    ${b(CG_WORK.rest && rig,'cards.gen_mode_rest','cards.gen_mode_rest_title','cgRestToggle()',!rig)}
    <span class="count">${tt('cards.gen_hd',{w:hw,h:hh})}</span><span style="flex:1"></span>
    ${b(c.overlay,'cards.gen_overlay','cards.gen_overlay_title',"cgToggle('overlay')")}
    ${b(rig && c.rig.handles,'cards.gen_bones','cards.gen_bones_title',"cgToggle('handles')",!rig)}
    ${b(false,c.cam.persp ? 'cards.gen_lens_persp' : 'cards.gen_lens_ortho','cards.gen_lens_title',"cgToggle('persp')")}`;
}
function cgViewBarPaint(){ const el = document.getElementById('cgViewBar'); if(el) el.innerHTML = cgViewBarHtml(...(CG_WORK.hdSize || [480,640])); }
function cgKeysHtml(){
  return `<details class="cgkeys"${CG_SHUT.has('keys') ? ' open' : ''} ontoggle="cgSecToggle('keys',!this.open)"><summary>${tt('cards.gen_keys')}</summary>
    <div>${['cards.gen_keys_turn','cards.gen_keys_select','cards.gen_keys_all','cards.gen_keys_gsr','cards.gen_keys_axis','cards.gen_keys_keep'].map(k => `<div>${tt(k)}</div>`).join('')}</div></details>`;
}
function cgModeSet(mode){
  CG_WORK.mode = mode; CG_WORK.selAll = false; CG_WORK.op = null;
  if(mode === 'object') CG_WORK.boneSel = ''; else CG_WORK.objSel = 0;
  cgViewBarPaint(); cgBoneRefresh(); cgObjsRefresh(); cgViewAsk();
}
function cgRestToggle(){ CG_WORK.rest = !CG_WORK.rest; cgViewBarPaint(); cgDraw(); }
function cgToggle(what){
  const c = cg();
  if(what === 'overlay') c.overlay = !c.overlay;
  else if(what === 'handles') c.rig.handles = !c.rig.handles;
  else if(what === 'persp'){ c.cam.persp = !c.cam.persp; CG_WORK.view = null; }
  cgViewBarPaint();
  if(what === 'persp') cgMoved(); else cgViewAsk();
}
/* Rest: the rig's controllers all at rest, for the view and the card alike. */
function cgPose(objects){
  if(!CG_WORK.rest || !cgRigActive()){ armAnimPose(objects); return; }
  const r = cg().rig, keep = r.basis;
  r.basis = {};
  try{ armAnimPose(objects); }finally{ r.basis = keep; }
}
function cgObjsRefresh(){ const el = document.getElementById('cgObjs'); if(el){ el.innerHTML = cgObjListHtml(); if(armObjGallery()) armThumbsPaint(); } }
/* The objects G, R and S act on: every one (A), the one picked, or none, when
   they act on the whole model. */
function cgSelected(){
  if(CG_WORK.selAll) return cgObjects().map(o => o.id);
  if(CG_WORK.grpSel) return (cgGroups().get(CG_WORK.grpSel) || []).map(o => o.id);
  return CG_WORK.objSel ? [CG_WORK.objSel] : [];
}
function cgSelectAll(){
  CG_WORK.selAll = !CG_WORK.selAll; CG_WORK.objSel = 0; CG_WORK.boneSel = ''; CG_WORK.grpSel = '';
  cgBoneRefresh(); cgObjsRefresh(); cgViewAsk();
}
/* The object under a point of the view: each drawn in a colour of its own
   and the pixel there read back. */
function cgPickObject(point){
  const cam = CG_WORK.camera, hd = document.getElementById('cgHd'), gl = armGl();
  if(!cam || !hd || !gl) return 0;
  const objects = cgObjects(), w = hd.width, h = hd.height;
  objects.forEach((o,i) => armRender([o],w,h,cam,{plain:true,card:true,pre:cam.pre,mask:true,noClear:i > 0,bg:[0,0,0],
    maskCol:[((i+1)&255)/255,((i+1)>>8&255)/255,0]}));
  const px = new Uint8Array(4), x = Math.round(point[0]), y = Math.round(point[1]);
  if(x < 0 || y < 0 || x >= w || y >= h) return 0;
  gl.readPixels(x,ARM.glCanvas.height-1-y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
  cgViewAsk();
  const i = px[0]+px[1]*256-1;
  return i >= 0 && objects[i] ? objects[i].id : 0;
}
function cgGroupPick(gk){
  CG_WORK.grpSel = CG_WORK.grpSel === gk ? '' : gk; CG_WORK.objSel = 0; CG_WORK.selAll = false;
  CG_WORK.mode = 'object'; cgViewBarPaint(); cgObjsRefresh(); cgViewAsk();
}
function cgObjClick(point){
  const id = cgPickObject(point);
  CG_WORK.objSel = id; CG_WORK.selAll = false; CG_WORK.grpSel = '';
  cgObjsRefresh(); cgViewAsk();
}
/* The picked object's numbers kept up with a G, R or S under way. */
function cgObjXfSync(){
  const x = (cg().oxf || {})[CG_WORK.objSel];
  if(!x) return;
  for(const k of 'trs') for(let i=0;i<3;i++){ const el = document.querySelector(`[data-cgxf="${k}${i}"]`); if(el) el.value = Math.round(x[k][i]*1000)/1000; }
}
/* Something changed: the view now, the card once the changes stop. */
function cgDraw(){
  if(!cgHere()) return;
  CG_WORK.poseGen = (CG_WORK.poseGen || 0)+1;
  cgMoved();
}
/* Only the camera moved: nothing to pose again. */
function cgMoved(){
  cgViewAsk();
  clearTimeout(CG_WORK.cardTimer);
  CG_WORK.cardTimer = setTimeout(() => { cgCardDraw(); },180);
}
async function cgCardDraw(){
  if(!cgHere()) return;
  cgSessSave();
  const token = ++CG_WORK.draw, card = document.getElementById('cgCard');
  if(!card) return;
  const c = cg(), objects = cgObjects(), [w,h] = CG_WORK.hdSize || [480,640];
  const hd = CG_WORK.hdCanvas && CG_WORK.hdCanvas.width === w && CG_WORK.hdCanvas.height === h ? CG_WORK.hdCanvas : (CG_WORK.hdCanvas = cgCanvas(w,h));
  try{
    cgPose(cgMoving(objects)); CG_WORK.posed = CG_WORK.poseGen;
    const camera = cgCamera(objects,w,h);
    const options = {plain:true,card:true,pre:camera.pre,light:cgLight(camera),bg:[0,0,0]};
    if(!armRender(objects,w,h,camera,options)) return;
    const ctx = hd.getContext('2d',{willReadFrequently:true}); ctx.clearRect(0,0,w,h); ctx.drawImage(ARM.glCanvas,0,0,w,h,0,0,w,h);
    const image = ctx.getImageData(0,0,w,h);
    armRender(objects,w,h,camera,{...options,mask:true});
    const maskCanvas = cgCanvas(w,h), maskCtx = maskCanvas.getContext('2d',{willReadFrequently:true});
    maskCtx.drawImage(ARM.glCanvas,0,0,w,h,0,0,w,h);
    const mask = maskCtx.getImageData(0,0,w,h).data;
    let alpha = new Uint8Array(w*h);
    for(let i=0;i<alpha.length;i++) alpha[i] = mask[i*4] > 0 ? 1 : 0;
    // smaller than a card pixel's worth of the HD render is a speck, not the model
    alpha = cgDespeck(alpha,w,h,Math.max(4,Math.round((w/card.width)*(h/card.height))));
    for(let i=0;i<alpha.length;i++) image.data[i*4+3] = alpha[i] ? mask[i*4] : 0;
    if(c.paint.on) cgPaintPixels(image.data,w,h,c.paint.strength);
    ctx.putImageData(image,0,0);
    if(c.post.outline > 0){
      const grown = cgDilate(alpha,w,h,c.post.outline*w/card.width), outline = ctx.createImageData(w,h);
      for(let i=0;i<grown.length;i++) outline.data[i*4+3] = grown[i] ? 255 : 0;
      maskCtx.putImageData(outline,0,0); maskCtx.drawImage(hd,0,0); ctx.clearRect(0,0,w,h); ctx.drawImage(maskCanvas,0,0);
    }
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
/* 2026-11-23: the silhouette less any patch of it smaller than minArea pixels.
   A stray triangle a few pixels across (a vertex the pose flings away) was
   grown by the outline into the black dots seen across a card. */
function cgDespeck(mask,w,h,minArea){
  const out = new Uint8Array(mask), seen = new Uint8Array(w*h), stack = [], patch = [];
  for(let s=0;s<w*h;s++){
    if(!out[s] || seen[s]) continue;
    stack.length = 0; patch.length = 0; stack.push(s); seen[s] = 1;
    while(stack.length){
      const i = stack.pop(); patch.push(i);
      const x = i % w, y = (i - x) / w;
      if(x > 0 && out[i-1] && !seen[i-1]){ seen[i-1] = 1; stack.push(i-1); }
      if(x < w-1 && out[i+1] && !seen[i+1]){ seen[i+1] = 1; stack.push(i+1); }
      if(y > 0 && out[i-w] && !seen[i-w]){ seen[i-w] = 1; stack.push(i-w); }
      if(y < h-1 && out[i+w] && !seen[i+w]){ seen[i+w] = 1; stack.push(i+w); }
    }
    if(patch.length < minArea) for(const i of patch) out[i] = 0;
  }
  return out;
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
  r.onload = () => { if(cg() === c){ c.ground.pic = String(r.result); cgDraw(); } }; r.onerror = () => toast(errText(r.error)); r.readAsDataURL(file);
}
/* --- 2026-11-24: the Save menu --------------------------------------------
   A saved card is given to units from here: every unit that uses the model
   (its soldier or armour upgrade line) is listed, the one the card was made
   for first and ticked, each with its factions. Ticked are the factions it
   owns that wear the textures drawn; a faction the model has textures for but
   the unit does not own can be ticked too, and is then added to its
   ownership. Replace all ticks every faction it owns; One mercs card puts the
   card in the mercenary folder, and with Remove the factions' own takes it
   out of every faction folder, so all of them show that one card. Preview
   plans each unit's edit (/api/edit/plan), Apply writes them, Undo as usual. */
const cgGiveMerc = kind => kind === 'info' ? 'merc' : 'mercs';
function cgGiveUnits(){ return ((CG_UNIT.units || {}).list || []); }
/* The factions the model has textures for, and those of the texture drawn. */
function cgSkinFactions(){
  const skins = cgSrc() === 'unit' ? CG_UNIT.skins || [] : [], k = skins[cgSkinOf(cg().texFaction)];
  const low = l => (l || []).map(f => f.toLowerCase());
  return {all: [...new Set(skins.flatMap(x => low(x.factions)))], drawn: low(k && k.factions)};
}
function cgGiveOpen(){
  const c = cg(), entry = cgSrc() === 'unit' ? (CG_UNIT.entry || '').toLowerCase() : '', units = cgGiveUnits();
  const uses = u => [u.soldier, ...(u.ug || [])].some(m => (m || '').toLowerCase() === entry);
  const list = [...new Set([cgSrc() === 'unit' ? CG_UNIT.unit : '', ...(entry ? units.filter(uses).map(u => u.type) : [])].filter(Boolean))];
  const g = c.give = {rows: {}, order: list, mercs: false, only: false, plans: null};
  for(const type of list) g.rows[type] = cgGiveRow(type, type === CG_UNIT.unit);
}
function cgGiveRow(type, on){
  const u = cgGiveUnits().find(x => x.type === type) || {factions: []}, owned = (u.factions || []).map(f => f.toLowerCase());
  const tf = cg().texFaction, drawn = new Set(cgSkinFactions().drawn);
  // what the card shows: the picked texture's faction, else the factions it owns wearing that texture
  let ticked = tf && owned.includes(tf) ? [tf] : owned.filter(f => !drawn.size || drawn.has(f));
  if(!ticked.length) ticked = owned.slice();
  return {on, owned, picked: new Set(ticked)};
}
function cgGiveFactions(type){
  const r = cg().give.rows[type], sk = cgSkinFactions(), tf = cg().texFaction;
  const list = [...new Set([...r.owned, ...sk.all.filter(f => f !== 'merc')])];
  // the texture picked first, then the factions it is drawn for, then the rest
  const rank = f => f === tf ? 0 : sk.drawn.includes(f) ? 1 : r.owned.includes(f) ? 2 : 3;
  return list.sort((x,y) => rank(x)-rank(y) || x.localeCompare(y));
}
function cgSavedHtml(){
  const c = cg(), s = c.saved; if(!s) return '';
  if(!c.give) cgGiveOpen();
  const g = c.give, q = v => esc(JSON.stringify(v)), tf = c.texFaction;
  const rows = g.order.map(type => {
    const r = g.rows[type];
    const chips = cgGiveFactions(type).map(f => { const own = r.owned.includes(f);
      return `<label class="armchip${r.picked.has(f) ? ' on' : ''}${f === tf ? ' cgtexf' : ''}"${own ? '' : ` title="${ttA('cards.gen_give_adds_owner')}"`}><input type="checkbox"${r.picked.has(f) ? ' checked' : ''}${g.mercs ? ' disabled' : ''}
        onchange="cgGiveTick(${q(type)},${q(f)},this.checked)">${esc(f)}${own ? '' : ' +'}</label>`; }).join('');
    return `<div class="cggive"><label class="armcheck"><input type="checkbox"${r.on ? ' checked' : ''} onchange="cgGiveUnit(${q(type)},this.checked)"><b>${esc(type)}</b></label>
      <div class="armchips">${chips}</div></div>`;
  }).join('');
  const others = cgGiveUnits().filter(u => !g.order.includes(u.type));
  const plans = g.plans ? g.plans.map(p => `<div class="cggiveplan"><b>${esc(p.unit)}</b>${p.error ? `<div class="armissue">${esc(p.error)}</div>`
      : (p.errors || []).map(e => `<div class="armissue">${esc(e)}</div>`).join('') + (p.changes || []).map(e => `<div>${esc(e)}</div>`).join('') + (p.warnings || []).map(e => `<div class="w-warn">${esc(e)}</div>`).join('')}</div>`).join('') : '';
  const ok = g.plans && g.plans.length && g.plans.every(p => !p.error && !(p.errors || []).length);
  return `<p class="ok">${tt('cards.gen_saved',{path:esc(s.path)})} <button class="mini" onclick="cgReveal(${q(s.path)})">${tt('editor.open_file_location')}</button></p>
    <div class="cggivemenu"><b>${tt(s.kind === 'info' ? 'cards.gen_give_info_head' : 'cards.gen_give_head')}</b>
    <p class="count">${tt('cards.gen_give_note')}</p>${rows}
    <div class="armexprow"><select onchange="if(this.value)cgGiveAdd(this.value)"><option value="">${tt('cards.gen_give_add')}</option>${others.map(u => `<option value="${esc(u.type)}">${esc(u.type)}</option>`).join('')}</select>
      <button class="mini" title="${ttA('cards.gen_give_all_title')}" onclick="cgGiveAll()">${tt('cards.gen_give_all')}</button></div>
    <label class="armcheck" title="${ttA('cards.gen_give_mercs_title')}"><input type="checkbox"${g.mercs ? ' checked' : ''} onchange="cgGiveSet('mercs',this.checked)">${tt('cards.gen_give_mercs')}</label>
    ${g.mercs ? `<label class="armcheck cggivesub"><input type="checkbox"${g.only ? ' checked' : ''} onchange="cgGiveSet('only',this.checked)">${tt('cards.gen_give_mercs_only')}</label>` : ''}
    <div class="armexprow"><button onclick="cgGive(false)">${tt('cards.gen_give')}</button>${ok ? `<button class="primary" onclick="cgGive(true)">${tt('cards.gen_give_apply')}</button>` : ''}</div>
    ${plans}</div>`;
}
function cgGiveRepaint(){ const c = cg(); if(c.give) c.give.plans = null; const el = document.getElementById('cgSaveResult'); if(el) el.innerHTML = cgSavedHtml(); }
function cgGiveTick(type, f, on){ const r = cg().give.rows[type]; if(on){ r.picked.add(f); r.on = true; } else r.picked.delete(f); cgGiveRepaint(); }
function cgGiveUnit(type, on){ cg().give.rows[type].on = on; cgGiveRepaint(); }
function cgGiveAdd(type){ const g = cg().give; g.order.push(type); g.rows[type] = cgGiveRow(type, true); cgGiveRepaint(); }
function cgGiveAll(){ for(const r of Object.values(cg().give.rows)) if(r.on) r.picked = new Set(r.owned); cgGiveRepaint(); }
function cgGiveSet(k, v){ const g = cg().give; g[k] = v; if(k === 'mercs' && !v) g.only = false; cgGiveRepaint(); }
/* One unit's edit request from the menu. */
function cgGiveBody(type){
  const c = cg(), g = c.give, r = g.rows[type], kind = c.saved.kind === 'info' ? 'info' : 'card';
  const body = {mod: state.src, unit: type, [kind + '_src']: c.saved.path};
  if(g.mercs){ body[kind + '_folders'] = [cgGiveMerc(kind)]; if(g.only) body[kind + '_only'] = true; return body; }
  body[kind + '_folders'] = [...r.picked];
  // a faction the model is textured for, given ownership of the unit
  const adds = [...r.picked].filter(f => !r.owned.includes(f));
  if(adds.length) body.field_overrides = {ownership: [...r.owned, ...adds].join(', ')};
  return body;
}
async function cgGive(apply){
  const c = cg(), g = c.give;
  if(!c.saved || !g) return;
  const types = g.order.filter(t => g.rows[t].on && (g.mercs || g.rows[t].picked.size));
  if(!types.length){ toast(tt('cards.gen_unit_first')); return; }
  if(apply && !(g.plans && g.plans.length)) return;
  const out = [];
  for(const type of types){
    try{
      const r = await api.post('/api/edit/' + (apply ? 'apply' : 'plan'), cgGiveBody(type));
      out.push(r.error ? {unit: type, error: r.error} : {unit: type, ...r});
    }catch(e){ out.push({unit: type, error: errText(e)}); }
  }
  if(cg() !== c || c.give !== g) return;
  if(apply){
    const bad = out.filter(p => p.error);
    toast(bad.length ? bad.map(p => p.unit + ': ' + p.error).join('; ') : tt('cards.gen_given_n', {n: out.length}));
    g.plans = null;
  }else g.plans = out;
  const el = document.getElementById('cgSaveResult'); if(el) el.innerHTML = cgSavedHtml();
}
/* 2026-11-24: Open file location for a card just saved, in its message too */
function cgReveal(path){ api.post('/api/armory/cards/reveal',{path}).then(r => { if(!r.ok) toast(tt('cards.gen_reveal_failed')); }).catch(e => toast(errText(e))); }
function cgToastReveal(path){
  const t = document.getElementById('toast'); if(!t) return;
  const b = document.createElement('button'); b.className = 'mini'; b.textContent = tt('editor.open_file_location');
  b.onclick = () => cgReveal(path); t.insertBefore(b,t.querySelector('.toastx'));
}
async function cgSave(hd){
  const c = cg(), name = c.name.trim(), mod = state.src;
  if(!name){ toast(tt('cards.gen_name_first')); return; }
  if(!document.getElementById('cgCard')) return;
  try{
    // the card made now, and its HD render (not the view) saved for Save HD
    clearTimeout(CG_WORK.cardTimer); await cgCardDraw();
    const canvas = hd ? CG_WORK.hdCanvas : document.getElementById('cgCard');
    if(!canvas) return;
    const kind = hd ? 'hd' : cgIsInfo() ? 'info' : c.size === 'custom' ? 'custom' : 'card';
    const r = await api.post('/api/armory/cards/save',{name,kind,size:[canvas.width,canvas.height],png:canvas.toDataURL('image/png')});
    if(r.error) throw new Error(r.error);
    if(hd){ toast(tt('cards.gen_saved',{path:r.path})); cgToastReveal(r.path); return; }
    if(cg() !== c) return;
    c.saved = r; c.give = null;
    // the units the menu offers: the unit picker's list, read here for Armory Studio's model
    if(!CG_UNIT.units || CG_UNIT.units.mod !== mod){
      try{ CG_UNIT.units = {mod, list: (await cgGet('/api/armory/templates?mod=' + enc(mod))).units || []}; }catch(e){ CG_UNIT.units = {mod, list: []}; }
    }
    if(cgHere() && state.src === mod && cg() === c) cgPaint();
  }catch(e){ c.err = errText(e); const el = document.getElementById('cgError'); if(el) el.textContent = c.err; }
}
function cgScreenPoint(p){
  const camera = CG_WORK.camera, hd = document.getElementById('cgHd');
  const world = cgMatrixPoint(camera.pre,p); world[0] = -world[0];
  const clip = cgProject(armMul(camera.proj,camera.view),world);
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
  const ctx = overlay.getContext('2d'), pref = typeof look === 'function' ? look() : {}, cut = CG_WORK.cut;
  // what lies outside the card dimmed, and the card's edge drawn plain
  // (2026-11-24: the view's Overlay toggle)
  if(cut && cg().overlay){
    const lw = Math.max(2,hd.width/200);
    ctx.fillStyle = 'rgba(8,10,14,0.5)'; ctx.beginPath(); ctx.rect(0,0,hd.width,hd.height); ctx.rect(cut.x,cut.y,cut.w,cut.h); ctx.fill('evenodd');
    ctx.lineWidth = lw*3; ctx.strokeStyle = 'rgba(0,0,0,0.85)'; ctx.strokeRect(cut.x-lw,cut.y-lw,cut.w+lw*2,cut.h+lw*2);
    ctx.lineWidth = lw; ctx.strokeStyle = (pref.colours || {}).accent || '#f4ce61'; ctx.strokeRect(cut.x-lw,cut.y-lw,cut.w+lw*2,cut.h+lw*2);
    if(cg().guide && !cgIsInfo()) cgGuideDraw(ctx,cut);
  }
  CG_WORK.handles = [];
  // 2026-11-24: drawn before the view's first draw (a picture landing, a hover)
  // there is no camera yet to put the handles through
  if(!CG_WORK.camera || CG_WORK.rest || cgMode() !== 'pose' || !cgRigActive() || !cg().rig.handles || !armAnim().data) return;
  const rig = cgRigLayout(), W = crSolve(rig,cg().rig.basis,cgRigType()), anim = armAnim().data;
  const pelvis = rig.bones.findIndex(b => b.c === 'm' && /pelvis/i.test(b.n));
  const ai = anim.bones.findIndex(b => /pelvis/i.test(b.name));
  const bind = armAnim().bind, origin = ai >= 0 && bind ? bind[ai] : [0,0,0];
  const rest = pelvis >= 0 ? crPos(rig.bones[pelvis].m) : [0,0,0];
  // the controllers a pose is made with (CG_BONES)
  for(const name of CG_BONES){
    const i = rig.byName.get(name); if(i === undefined) continue;
    const p = crPos(W[i]), delta = [p[0]-rest[0],p[2]-rest[2],p[1]-rest[1]];
    let game = delta.map((v,k) => v+origin[k]);
    // on a horse: carried as the man's bones are (v3aCarry)
    const k = armAnim().carry;
    if(k){ const d = v3aApply(k.root.m,game.map((v,j) => v+k.off[j])); game = d.map((v,j) => k.root.p[j]+k.lift[j]+v); }
    const point = cgScreenPoint(game);
    CG_WORK.handles.push({name,i,point,W,game});
  }
  const radius = Math.max(6,hd.width/90);
  ctx.lineWidth = Math.max(1,hd.width/400); ctx.globalAlpha = 0.85;
  for(const side of ['left','right']) for(const pair of [['elbow','frist'],['knee','angle']]){
    const a = CG_WORK.handles.find(x => x.name.includes(pair[0]) && x.name.includes(side)), b = CG_WORK.handles.find(x => x.name.includes(pair[1]) && x.name.includes(side));
    if(a && b){ ctx.strokeStyle = side === 'left' ? '#58aaff' : '#ff7766'; ctx.beginPath(); ctx.moveTo(...a.point); ctx.lineTo(...b.point); ctx.stroke(); }
  }
  for(const h of CG_WORK.handles){
    const [x,y] = h.point, picked = h.name === CG_WORK.boneSel, active = picked || h.name === CG_WORK.hover;
    const r = radius*(active ? 1.3 : 1);
    if(picked){ ctx.save(); ctx.lineWidth *= 2.5; ctx.strokeStyle = '#ffffff'; ctx.beginPath(); ctx.arc(x,y,r*1.9,0,Math.PI*2); ctx.stroke(); ctx.restore(); }
    ctx.fillStyle = /left/.test(h.name) ? '#58aaff' : /right/.test(h.name) ? '#ff7766' : (pref.colours || {}).accent || '#f4ce61';
    ctx.strokeStyle = active ? '#fff' : '#181818'; ctx.beginPath();
    if(/elbow|knee/.test(h.name)){ ctx.moveTo(x,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x,y+r); ctx.lineTo(x-r,y); ctx.closePath(); }
    else if(/angle/.test(h.name)) ctx.rect(x-r,y-r*0.6,r*2,r*1.2);
    else ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fill(); ctx.stroke();
  }
}
/* 2026-11-24: the Blender kit's camera preview (Medieval-2-Toolkit,
   assets/Camera Preview.png): the game's experience chevrons, soldier count and
   weapon and shield icons, 48x66 at 10x for a 48x64 card, its top on the card's
   top and its two spare rows below, cut off as the kit's guideOffset does. */
function cgGuideDraw(ctx,cut){
  // a picture that failed to come is asked for again on the next draw
  const img = CG_WORK.guide || (CG_WORK.guide = Object.assign(new Image(),{onload:() => { if(cgHere()) cgOverlay(); },
    onerror:() => { CG_WORK.guide = null; }, src:'/img/card_guide.png'}));
  if(!img.complete || !img.naturalWidth) return;
  ctx.save(); ctx.beginPath(); ctx.rect(cut.x,cut.y,cut.w,cut.h); ctx.clip();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(img,cut.x,cut.y,cut.w,cut.w*img.naturalHeight/img.naturalWidth);
  ctx.restore();
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
    CG_WORK.resize = new ResizeObserver(() => { if(cgHere() && document.getElementById('cgHd') === hd) cgViewAsk(); });
    CG_WORK.resize.observe(hd);
  }
  let drag = null, last = [0,0];
  CG_WORK.op = null;
  hd.addEventListener('contextmenu',e => { e.preventDefault(); });
  hd.addEventListener('auxclick',e => { if(e.button === 1) e.preventDefault(); });
  // Shift + click is a view control, never a text selection
  hd.addEventListener('mousedown',e => { if(e.shiftKey) e.preventDefault(); });
  hd.addEventListener('wheel',e => {
    e.preventDefault();
    // the wheel zooms the view; with Ctrl it zooms the card's own camera
    if(e.ctrlKey){ cg().cam.scale = Math.max(0.2,Math.min(6,cg().cam.scale*Math.exp(e.deltaY*0.001))); cgSyncCamera(); cgMoved(); return; }
    const v = cgViewState(); v.zoom = Math.max(0.3,Math.min(12,v.zoom*Math.exp(-e.deltaY*0.0015))); cgViewAsk();
  },{passive:false});
  hd.addEventListener('pointerdown',e => {
    hd.focus(); last = cgPointerPoint(e);
    // a G or R under way: a left click keeps it, a right click puts it back
    if(CG_WORK.op){ e.preventDefault(); if(e.button === 2) cgOpCancel(); else if(e.button === 0) cgOpAccept(); return; }
    // 2026-11-23: Simple (Armory's setting): a left drag off the rig's handles
    // turns the view, a right drag moves it; Blender's middle button as before.
    // A click on a handle selects that bone, a click off them lets it go.
    const simple = armNav() === 'simple';
    if(e.button === 1 || e.altKey && e.button === 0){ e.preventDefault(); drag = {kind:'camera'}; }
    else if(simple && e.button === 2){ e.preventDefault(); drag = {kind:'camera',pan:true}; }
    else if(e.button === 0){
      const hit = cgHit(e);
      if(hit){ drag = {kind:'rig',handle:hit}; cgBoneSelect(hit.name); }
      else drag = {kind:simple ? 'camera' : 'none',click:[e.clientX,e.clientY]};
    }
    if(drag) hd.setPointerCapture(e.pointerId);
  });
  hd.addEventListener('pointermove',e => {
    const p = cgPointerPoint(e), dx=p[0]-last[0],dy=p[1]-last[1]; last=p;
    const c = cg(), op = CG_WORK.op;
    if(op){
      // the first move after a G or R from a button only finds the mouse
      if(op.fresh){ op.fresh = false; return; }
      if(op.bone) cgOpBone(op,p,dx,dy);
      else if(op.grp){
        // a whole model: moved, or scaled about its middle (cgXf)
        const f = Math.exp((dx-dy)*0.006), movement = cgMoveWorld(dx,dy), i = op.axis ? 'xyz'.indexOf(op.axis) : -1;
        c.gxf = {...(c.gxf || {})};
        const g = c.gxf[op.grp] = JSON.parse(JSON.stringify(cgGroupXf(op.grp)));
        if(op.kind === 's') g.s = Math.max(0.05,Math.min(20,(Number(g.s) || 1)*f));
        else if(i >= 0) g.t[i] += (dx-dy)*CG_WORK.camera.height/hd.height;
        else g.t = g.t.map((v,k) => v+movement[k]);
        const out = document.querySelector(`[data-cggs="${CSS.escape(op.grp)}"]`); if(out) out.textContent = Math.round(g.s*100)/100;
      }else if(op.objs){
        // each picked object by the card's own transform for it (c.oxf)
        c.oxf = {...(c.oxf || {})};
        const f = Math.exp((dx-dy)*0.006), movement = cgMoveWorld(dx,dy), i = op.axis ? 'xyz'.indexOf(op.axis) : -1;
        for(const id of op.objs){
          const x = c.oxf[id] = JSON.parse(JSON.stringify(c.oxf[id] || {t:[0,0,0],r:[0,0,0],s:[1,1,1]}));
          if(op.kind === 's'){ if(i >= 0) x.s[i] = Math.max(0.01,x.s[i]*f); else x.s = x.s.map(v => Math.max(0.01,v*f)); }
          else if(op.kind === 'r'){ if(i >= 0) x.r[i] += dx*0.3; else{ x.r[1] += dx*0.3; x.r[0] += dy*0.3; } }
          else if(i >= 0) x.t[i] += (dx-dy)*CG_WORK.camera.height/hd.height;
          else x.t = x.t.map((v,k) => v+movement[k]);
        }
        cgObjXfSync();
      }else{
        if(op.kind === 's') c.xf.s = Math.max(0.05,Math.min(20,(Number(c.xf.s) || 1)*Math.exp((dx-dy)*0.006)));
        else if(op.kind === 'r'){
          if(op.axis) c.xf.r['xyz'.indexOf(op.axis)] += dx*0.3;
          else{ c.xf.r[1] += dx*0.3; c.xf.r[0] += dy*0.3; }
        }else{
          const movement = cgMoveWorld(dx,dy);
          if(op.axis){ const i='xyz'.indexOf(op.axis); c.xf.t[i] += (dx-dy)*CG_WORK.camera.height/hd.height; }
          else c.xf.t = c.xf.t.map((v,i) => v+movement[i]);
        }
        cgSyncCamera();
      }
      cgDraw(); return;
    }
    if(!drag){ const hit = cgHit(e), name = hit ? hit.name : ''; if(CG_WORK.hover !== name){ CG_WORK.hover=name; cgOverlay(); } return; }
    if(drag.click && Math.hypot(e.clientX-drag.click[0],e.clientY-drag.click[1]) > 3) drag.moved = true;
    if(drag.kind === 'camera'){
      if(e.ctrlKey) c.cam.scale = Math.max(0.2,Math.min(6,c.cam.scale*Math.exp(dy*0.005)));
      // a pan moves the view, not the card; the card's frame goes with the model
      else if(e.shiftKey || drag.pan){ cgViewPan(dx,dy); return; }
      // Armory Studio's turn: a drag right swings the eye left round the model
      else{ c.cam.yaw -= dx*0.2; c.cam.pitch = Math.max(-60,Math.min(80,c.cam.pitch+dy*0.2)); }
      cgSyncCamera(); cgMoved();
    }else if(drag.kind === 'rig'){
      const name = drag.handle.name;
      if(name === 'IK Head'){
        const ch = c.rig.basis[name] = {...c.rig.basis[name]}, angles = ch.e ? [...ch.e] : ch.q ? crToEuler(crQuat(ch.q)) : [0,0,0];
        angles[0] += dy*0.003; angles[2] += dx*0.003; ch.e = angles; delete ch.q;
      }else cgBoneMove(name,dx,dy,'');
      cgBoneRefresh(); cgDraw();
    }
  });
  hd.addEventListener('dblclick',e => { if(e.button === 0 && !cgHit(e)) cgViewReset(); });
  hd.addEventListener('pointerup',e => {
    const d = drag; drag = null;
    if(hd.hasPointerCapture(e.pointerId)) hd.releasePointerCapture(e.pointerId);
    if(d && d.click && !d.moved){ if(cgMode() === 'object') cgObjClick(cgPointerPoint(e)); else cgBoneSelect(''); }
  });
  hd.addEventListener('keydown',e => cgViewKey(e,false));
  // 2026-11-24: the keys work after a Pick in the object list too, not only
  // once the view itself has been clicked
  if(!CG_WORK.keysWired){
    CG_WORK.keysWired = true;
    document.addEventListener('keydown',e => {
      const t = e.target, hd = document.getElementById('cgHd');
      if(!cgHere() || cgPicking() || !hd || t === hd || e.ctrlKey || e.metaKey || e.altKey) return;
      if(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      cgViewKey(e,true);
    });
  }
}
function cgViewKey(e,outside){
  const key = e.key.toLowerCase(), op = CG_WORK.op;
  if(key === 'escape'){ if(!op && outside) return; e.preventDefault(); if(op) cgOpCancel(); else cgBoneSelect(''); return; }
  if(key === 'enter'){ if(!op) return; e.preventDefault(); cgOpAccept(); return; }
  if(op && ['x','y','z'].includes(key)){ e.preventDefault(); op.axis = op.axis === key ? '' : key; return; }
  // from outside the view, the first move only finds the mouse (op.fresh)
  if(!op && ['g','r','s'].includes(key)){ e.preventDefault(); cgOpStart(key,outside); }
  else if(!op && key === 'a' && !e.ctrlKey && !e.metaKey){ e.preventDefault(); cgSelectAll(); }
}
/* --- 2026-11-23: the rig's bones picked and moved as in Blender ----------------
   A click on a handle selects that controller; G moves it, R turns it (about
   the line of sight, or with X, Y or Z about Blender's axis: Z up), a click or
   Enter keeps it, Esc or a right click puts it back. With no bone selected G
   and R move and turn the whole model, as before. */
const CG_BONES = ['IK Pelvis','IK Torso Controller','IK Head','IK frist right','IK frist  left','IK angle right','IK angle left','IK elbow right','IK elbow left','IK knee right','IK knee left'];
function cgBoneSelect(name){
  if(CG_WORK.boneSel === name) return;
  CG_WORK.boneSel = name; cgBoneRefresh(); cgOverlay();
}
function cgBoneRefresh(){ const el = document.getElementById('cgBone'); if(el) el.innerHTML = cgBoneHtml(); }
function cgBoneHtml(){
  const name = CG_WORK.boneSel || '', ch = name ? cg().rig.basis[name] || {} : {};
  const l = ch.l || [0,0,0], e = ch.e || (ch.q ? crToEuler(crQuat(ch.q)) : [0,0,0]), op = CG_WORK.op;
  const num = (k,i,v,step) => `<input class="armnum" type="number" step="${step}" value="${Math.round(v*1000)/1000}" onchange="cgBoneSet('${k}',${i},+this.value)">`;
  return `${cgField(tt('cards.gen_bone'), `<select onchange="cgBoneSelect(this.value)"><option value="">${tt('cards.gen_bone_none')}</option>${CG_BONES.map(n => `<option value="${esc(n)}"${n === name ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select>`)}
    ${name ? `<div class="cgbonegrid"><span>${tt('cards.gen_bone_loc')}</span>${l.map((v,i) => num('l',i,v,0.01)).join('')}<span>${tt('cards.gen_bone_rot')}</span>${e.map((v,i) => num('e',i,v*180/Math.PI,1)).join('')}</div>
    <div class="armexprow"><button class="mini${op && op.bone && op.kind === 'g' ? ' on' : ''}" title="${ttA('cards.gen_bone_move_title')}" onclick="cgOpStart('g',true)">${tt('cards.gen_bone_move')}</button>
      <button class="mini${op && op.bone && op.kind === 'r' ? ' on' : ''}" title="${ttA('cards.gen_bone_turn_title')}" onclick="cgOpStart('r',true)">${tt('cards.gen_bone_turn')}</button>
      <button class="mini" onclick="cgBoneClear()">${tt('cards.gen_bone_reset')}</button></div>` : ''}`;
}
function cgBoneSet(k,i,v){
  const name = CG_WORK.boneSel; if(!name || !isFinite(v)) return;
  const basis = cg().rig.basis, ch = basis[name] = {...basis[name]};
  if(k === 'l'){ ch.l = [...(ch.l || [0,0,0])]; ch.l[i] = v; }
  else{ const e = ch.e ? [...ch.e] : ch.q ? crToEuler(crQuat(ch.q)) : [0,0,0]; e[i] = v*Math.PI/180; ch.e = e; delete ch.q; }
  cgDraw();
}
function cgBoneClear(){ const name = CG_WORK.boneSel; if(!name) return; delete cg().rig.basis[name]; cgBoneRefresh(); cgDraw(); }
function cgOpStart(kind,fromButton){
  // a controller is moved and turned, never scaled: S scales the model
  const c = cg(), name = kind !== 's' && cgMode() === 'pose' && cgRigActive() && CG_WORK.boneSel;
  const objs = cgMode() === 'object' && !CG_WORK.selAll && cgSelected(), grp = cgMode() === 'object' && !CG_WORK.selAll && CG_WORK.grpSel;
  if(!CG_WORK.camera) return;
  CG_WORK.op = name ? {kind,bone:name,axis:'',start:JSON.parse(JSON.stringify(c.rig.basis)),fresh:!!fromButton}
    : grp && kind !== 'r' ? {kind,grp,axis:'',start:JSON.parse(JSON.stringify(c.gxf || {})),fresh:!!fromButton}
    : objs && objs.length ? {kind,objs,axis:'',start:JSON.parse(JSON.stringify(c.oxf || {})),fresh:!!fromButton}
    : {kind,axis:kind === 'r' ? 'y' : '',start:JSON.parse(JSON.stringify(c.xf)),fresh:!!fromButton};
  if(name){ const h = CG_WORK.handles.find(x => x.name === name); CG_WORK.op.pivot = h ? h.point : null; cgBoneRefresh(); }
  const hd = document.getElementById('cgHd'); if(hd) hd.focus();
}
function cgOpCancel(){
  const op = CG_WORK.op; if(!op) return;
  CG_WORK.op = null;
  if(op.bone) cg().rig.basis = op.start; else if(op.grp) cg().gxf = op.start; else if(op.objs){ cg().oxf = op.start; cgObjXfSync(); } else cg().xf = op.start;
  cgSyncCamera(); cgBoneRefresh(); cgDraw();
}
function cgOpAccept(){ if(!CG_WORK.op) return; CG_WORK.op = null; cgSyncCamera(); cgBoneRefresh(); }
function cgOpBone(op,p,dx,dy){
  if(op.kind === 'g') cgBoneMove(op.bone,dx,dy,op.axis);
  else if(op.pivot){
    const angle = Math.atan2(p[1]-op.pivot[1],p[0]-op.pivot[0]);
    if(op.angle != null){ const d = angle-op.angle; cgBoneTurn(op.bone,Math.atan2(Math.sin(d),Math.cos(d)),op.axis); }
    op.angle = angle;
  }
  cgBoneRefresh();
}
/* Blender's axis k (Z up) in the game's space (y up), and back. */
const cgBlenderAxis = k => { const b = [0,0,0]; b[k] = 1; return [b[0],b[2],b[1]]; };
function cgBoneBase(name){
  const c = cg(), rig = cgRigLayout(), i = rig ? rig.byName.get(name) : undefined;
  if(i === undefined) return null;
  const W = crSolve(rig,c.rig.basis,cgRigType()), bone = rig.bones[i];
  return bone.p < 0 ? bone.m : crMul(W[bone.p],rig.rel[i]);
}
function cgBoneMove(name,dx,dy,axis){
  const base = cgBoneBase(name); if(!base) return;
  let game = cgMoveWorld(dx,dy);
  if(axis){
    // along the axis as it is drawn: how far the mouse went down its line on screen
    const h = CG_WORK.handles.find(x => x.name === name), o = h ? h.game : [0,0,0], g = cgBlenderAxis('xyz'.indexOf(axis));
    const s0 = cgScreenPoint(o), s1 = cgScreenPoint(o.map((v,j) => v+g[j]*0.1)), sv = [s1[0]-s0[0],s1[1]-s0[1]];
    const amount = (dx*sv[0]+dy*sv[1])/(sv[0]*sv[0]+sv[1]*sv[1] || 1)*0.1;
    game = g.map(v => v*amount);
  }
  const ch = cg().rig.basis[name] = {...cg().rig.basis[name]}, local = crR3(crT3(crRot(base)),[game[0],game[2],game[1]]);
  ch.l = (ch.l || [0,0,0]).map((v,j) => v+local[j]);
}
function cgBoneTurn(name,angle,axis){
  const base = cgBoneBase(name); if(!base) return;
  let ax;
  if(axis){ ax = [0,0,0]; ax['xyz'.indexOf(axis)] = 1; }
  else{
    // the line of sight, from the page's space (x mirrored) into the rig's
    const cam = CG_WORK.camera, v = crNorm(crSub(cam.eye,cam.target));
    ax = [-v[0],v[2],v[1]];
  }
  const ch = cg().rig.basis[name] = {...cg().rig.basis[name]}, cur = ch.q ? crQuat(ch.q) : ch.e ? crEuler(ch.e) : [1,0,0, 0,1,0, 0,0,1];
  const local = crNorm(crR3(crT3(crPure(crRot(base))),ax));
  ch.e = crToEuler(crR3Mul(crAxisAngle(local,CG_TURN*angle),cur)); delete ch.q;
}
const CG_TURN = -1;
/* --- 2026-11-23: the pose library's pictures, drawn on this model a few at a
   time and kept until the model, its parts or the rig change. */
function cgPoseThumbs(){
  const imgs = [...document.querySelectorAll('img[data-cgpose]')];
  if(!imgs.length || !cgRigActive() || !armAnim().data) return;
  // the man alone: a horse under him is not in the picture
  const objects = cgObjects().filter(o => !o.still), sig = [cgRigType(),armAnim().skel,objects.map(o => o.id + ':' + cgPartKey(o)).join(',')].join('|');
  if(CG_WORK.thumbSig !== sig || !CG_WORK.poseThumbs){ CG_WORK.thumbSig = sig; CG_WORK.poseThumbs = new Map(); }
  const poses = cgLibPoses(), keyOf = img => { const p = poses[+img.dataset.cgpose] || {}; return p.c + '|' + p.n; };
  const todo = imgs.filter(img => { const url = CG_WORK.poseThumbs.get(keyOf(img)); if(url){ img.src = url; return false; } return true; });
  if(!todo.length) return;
  const run = CG_WORK.thumbRun = (CG_WORK.thumbRun || 0) + 1;
  const step = () => {
    if(run !== CG_WORK.thumbRun || !cgHere() || CG_WORK.thumbSig !== sig || !cgRigActive()) return;
    const t0 = performance.now();
    while(todo.length && performance.now()-t0 < 40){
      const img = todo.shift();
      if(!img.isConnected) continue;
      const url = cgPoseThumb(+img.dataset.cgpose,objects);
      if(url){ CG_WORK.poseThumbs.set(keyOf(img),url); img.src = url; }
    }
    armAnimPose(objects);
    if(todo.length) setTimeout(step,0);
  };
  setTimeout(step,0);
}
/* 2026-11-24: every picture through one camera, as the Blender kit's pose
   library is: framed once on the rig's own rest pose, the card's default turn,
   so a pose that raises an arm or crouches shows it rather than being
   re-framed to fill the picture. */
function cgThumbFrame(objects){
  const f = CG_WORK.thumbFrame;
  if(f && f.sig === CG_WORK.thumbSig) return f;
  const r = cg().rig, keep = r.basis;
  r.basis = {};
  try{
    armAnimPose(objects);
    // the body, not what it carries: a spear held up made every man small.
    // As tight as the Blender kit's: head to shins, the feet just cut off.
    const body = objects.filter(o => !/^(primary|secondary|shield|weapon|equipment|ramrod)/i.test(o.name || ''));
    const [lo,hi] = cgBounds(body.length ? body : objects), tall = Math.max(0.1,hi[1]-lo[1]);
    return CG_WORK.thumbFrame = {sig:CG_WORK.thumbSig,height:tall*0.9,target:[-(lo[0]+hi[0])/2,lo[1]+tall*0.56,(lo[2]+hi[2])/2]};
  }finally{ r.basis = keep; }
}
function cgPoseThumb(index,objects){
  const r = cg().rig, keep = r.basis, W = 96, H = 112, frame = cgThumbFrame(objects);
  r.basis = crApply({},cgLibPoses()[index],'whole');
  try{
    armAnimPose(objects);
    const height = frame.height, width = height*W/H, target = frame.target;
    const yaw = 20*Math.PI/180, pitch = 4*Math.PI/180;
    const eye = [target[0]+10*Math.cos(pitch)*Math.sin(yaw),target[1]+10*Math.sin(pitch),target[2]+10*Math.cos(pitch)*Math.cos(yaw)];
    const camera = {proj:[2/width,0,0,0,0,2/height,0,0,0,0,-0.01,0,0,0,0,1],view:v3LookAt(eye,target,[0,1,0]),eye,target};
    if(!armRender(objects,W,H,camera,{plain:true,card:true,light:cgLight(camera,20),bg:[0.3,0.33,0.38]})) return '';
    const canvas = cgCanvas(W,H); canvas.getContext('2d').drawImage(ARM.glCanvas,0,0,W,H,0,0,W,H);
    return canvas.toDataURL('image/jpeg',0.85);
  }finally{ r.basis = keep; }
}
