/* =========================================================================
   Armory Studio, the animation previewer - Phase 95h

   A window at the bottom right of the viewport: choose a skeleton, play its
   actions on the model being edited, and see whether every part follows.
   The skeletons and actions are the ones a loaded model entry names
   (animview.entry_view, /api/model/anims), played from the mod's packs the
   way the Models viewer plays them; the arithmetic is v3anim.js's own
   (v3aPose, v3aBind, v3aBoneMap, v3aSkin), so a pose here is a pose there.

   Each object is laid out in the game's space as the export will write it,
   its own move, turn and scale applied, then skinned by its weights: the
   source model's, or the ones 95f transferred onto it. Bones match by name
   without regard to case, which is the bone renaming 95g speaks of: an
   archer's bone_rhand follows a melee skeleton's bone_Rhand. A part weighted
   to a bone the skeleton has not got goes with the pelvis and is named.
   ========================================================================= */

function armAnim(){ return ARM.anim = ARM.anim || {open: true, list: null, asset: '', skel: '', key: '', find: '',
  data: null, t: 0, playing: true, speed: 1, err: '', geos: new Map()}; }

function armAnimEntries(){ return armProj().assets.filter(a => a.kind === 'entry'); }

/* --- the window ------------------------------------------------------------------- */

function armAnimPaint(){
  const host = document.getElementById('armView');
  if(!host) return;
  let el = document.getElementById('armAnimWin');
  if(!el){ el = document.createElement('div'); el.id = 'armAnimWin'; el.className = 'armanimwin'; }
  if(el.parentNode !== host) host.appendChild(el);
  const a = armAnim(), p = armProj();
  const entries = armAnimEntries();
  const tp = `<button class="mini${a.tpose ? ' on' : ''}" onclick="armTpose()" title="${esc(tt('armory.tpose_title'))}">${tt('armory.tpose')}</button>`;
  if(!a.open){
    el.innerHTML = `<div class="armhead"><button class="armfold" onclick="armAnimFold()">▸ ${tt('armory.animations')}</button><span style="flex:1"></span>${tp}</div>`;
    return;
  }
  const chosen = (p.anim && p.anim.asset) || '';
  const L = a.list;
  const skels = L && L.skeletons ? Object.keys(L.skeletons) : [];
  const sk = L && L.skeletons ? L.skeletons[(a.skel || '').toLowerCase()] : null;
  el.innerHTML = `<div class="armhead"><button class="armfold" onclick="armAnimFold()">▾ ${tt('armory.animations')}</button>
      ${a.data ? `<span class="count">${esc(a.data.name || '')}</span>` : ''}<span style="flex:1"></span>${tp}</div>
    <label class="count">${tt('armory.skeleton_of')}<select onchange="armAnimFrom(this.value)">
      <option value="">${tt('armory.pick_model_entry')}</option>${entries.map(e => { const k = armAssetKey(e);
        return `<option value="${esc(k)}"${k === chosen ? ' selected' : ''}>${esc(armAssetLabel(e))}</option>`; }).join('')}
      <option value="@mod"${armAnimByMod() ? ' selected' : ''}>${tt('armory.skeleton_from_mod')}</option></select></label>
    ${armAnimByMod() ? armAnimModHtml() : ''}
    ${L && L.error ? `<div class="w-bad">${esc(L.error)}</div>` : ''}
    ${skels.length ? `<label class="count">${tt('armory.skeleton')}<select onchange="armAnimSkel(this.value)">${skels.map(s =>
      `<option${s === (a.skel || '').toLowerCase() ? ' selected' : ''}>${esc(L.skeletons[s].name || s)}</option>`).join('')}</select></label>` : ''}
    ${sk ? `<input placeholder="${esc(tt('armory.find'))}" value="${esc(a.find)}" oninput="armAnimFind(this.value)">
      <select size="6" class="armanimlist" id="armAnimList" onchange="armAnimPick(this.value)">${armAnimListHtml(sk)}</select>` : ''}
    ${a.data ? `<div class="armslrow">
        <button class="mini" onclick="armAnimPlay()">${a.playing ? '⏸' : '▶'}</button>
        <input type="range" id="armAnimT" min="0" max="1000" value="${armAnimFrac()}" oninput="armAnimScrub(this.value)">
        <select onchange="armAnim().speed=+this.value">${[0.25, 0.5, 1, 2].map(v => `<option value="${v}"${a.speed === v ? ' selected' : ''}>${v}×</option>`).join('')}</select>
        <button class="mini" onclick="armAnimRest()" title="${esc(tt('armory.rest_title'))}">${tt('armory.rest')}</button></div>
      <div class="count" id="armAnimNote">${armAnimNote()}</div>${armAnimScaleHtml()}` : ''}
    ${a.err ? `<div class="w-bad">${esc(a.err)}</div>` : ''}`;
}
function armAnimFold(){ const a = armAnim(); a.open = !a.open; armAnimPaint(); }

/* 99j: T-pose. Animation off, every part standing in its bind pose, and
   back on where it was: the action, its time and whether it played are kept.
   The card maker (95m) poses its card whatever this is. */
function armTpose(){
  const a = armAnim();
  a.tpose = !a.tpose;
  if(!a.tpose){ a.last = performance.now(); armAnimLoop(); }
  armAnimPaint(); armFrame();
}

function armAnimListHtml(sk){
  const a = armAnim();
  const q = (a.find || '').trim().toLowerCase();
  const rows = (sk.actions || []).filter(r => !q || (r.action || '').toLowerCase().includes(q));
  if(!rows.length) return `<option disabled>${tt('armory.nothing_matches')}</option>`;
  return rows.map(r => { const k = r.slot != null ? String(r.slot) : 'a:' + r.action;
    return `<option value="${esc(k)}"${k === a.key ? ' selected' : ''}${r.playable ? '' : ' disabled'}>${esc(r.action)}</option>`; }).join('');
}
function armAnimFind(v){
  const a = armAnim(); a.find = v;
  const sk = a.list && a.list.skeletons && a.list.skeletons[(a.skel || '').toLowerCase()];
  const el = document.getElementById('armAnimList');
  if(el && sk) el.innerHTML = armAnimListHtml(sk);         // the rows only, never the box
}

/* A skeleton straight out of a mod's packs, with no model loaded: the mod and
   the skeleton picked here, its actions read as an entry's would be
   (/api/armory/skeleton), played from that mod. Kept in the project as
   {mod, skel}, and read again when the window opens on it. */
const armAnimByMod = () => { const p = armProj(); return !!(p.anim && p.anim.mod !== undefined && !p.anim.asset); };
function armAnimModHtml(){
  const p = armProj(), a = armAnim(), mod = p.anim.mod || '';
  if(!ARM.mods){
    api.get('/api/mods').then(r => { ARM.mods = r.map(m => m.name); armAnimPaint(); }).catch(() => { ARM.mods = [state.src]; armAnimPaint(); });
    return `<div class="count">${tt('armory.reading')}</div>`;
  }
  if(mod && !(ARM.skelNames || {})[mod]) armAnimModNames(mod);
  if(mod && p.anim.skel && !a.list && !a.loadingSk) armAnimFromMod(mod, p.anim.skel);
  const names = (ARM.skelNames || {})[mod];
  return `<label class="count">${tt('armory.skeleton_mod')}<select onchange="armAnimSetMod(this.value)">
      <option value="">${tt('armory.pick_mod')}</option>${ARM.mods.map(m => `<option${m === mod ? ' selected' : ''}>${esc(m)}</option>`).join('')}</select></label>
    ${mod ? names ? (names.length ? `<label class="count">${tt('armory.skeleton')}<select onchange="armAnimFromMod('${esc(mod)}', this.value)">
        <option value="">${tt('armory.pick_skeleton')}</option>${names.map(n => `<option${n === p.anim.skel ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>`
        : `<div class="count">${tt('armory.no_skeletons')}</div>`) : `<div class="count">${tt('armory.reading')}</div>` : ''}`;
}
async function armAnimModNames(mod){
  ARM.skelNames = ARM.skelNames || {};
  if(ARM.skelNames[mod] || (ARM.skelAsk || {})[mod]) return;
  (ARM.skelAsk = ARM.skelAsk || {})[mod] = true;
  let r;
  try{ r = await api.get('/api/model/skeleton_names?mod=' + enc(mod)); }catch(e){ r = {names: []}; }
  ARM.skelNames[mod] = [...new Set(r.names || [])].sort((x, y) => x.localeCompare(y));
  delete ARM.skelAsk[mod];
  armAnimPaint();
}
function armAnimSetMod(mod){
  const p = armProj(), a = armAnim();
  p.anim = {mod, skel: ''};
  Object.assign(a, {list: null, skel: '', key: '', data: null, err: '', set: null});
  armSave(); armAnimRest(); armAnimPaint();
}
async function armAnimFromMod(mod, skel){
  const p = armProj(), a = armAnim();
  p.anim = {mod, skel};
  armSave();
  Object.assign(a, {list: null, skel: '', key: '', data: null, err: '', set: null});
  armAnimRest();
  if(!skel) return armAnimPaint();
  a.loadingSk = true;
  armAnimPaint();
  try{ a.list = await api.get(`/api/armory/skeleton?mod=${enc(mod)}&skel=${enc(skel)}`); }
  catch(e){ a.list = {error: errText(e)}; }
  a.loadingSk = false;
  a.skel = skel;
  armAnimPaint();
}

async function armAnimFrom(key){
  const p = armProj(), a = armAnim();
  if(key === '@mod') return armAnimSetMod(state.src || '');
  p.anim = key ? {asset: key} : null;
  armSave();
  Object.assign(a, {list: null, skel: '', key: '', data: null, err: '', mount: null, rider: null});
  armAnimRest();
  if(!key) return armAnimPaint();
  const asset = p.assets.find(x => armAssetKey(x) === key);
  armAnimPaint();
  try{ a.list = await api.get(`/api/model/anims?mod=${enc(asset.mod)}&entry=${enc(asset.entry)}`); }
  catch(e){ a.list = {error: errText(e)}; }
  const set = (a.list.sets || [])[0];
  a.skel = set ? (set.primary || set.secondary || '') : Object.keys(a.list.skeletons || {})[0] || '';
  a.set = set || null;
  armAnimPaint();
}
function armAnimSkel(v){ const a = armAnim(); a.skel = v; a.key = ''; a.data = null; armAnimRest(); armAnimPaint(); }

/* The weapon skeletons the set hangs off the hand for this skeleton, so a
   part weighted to bone_weapon moves with the arm (Phase 80b). */
function armAnimWeapons(){
  const a = armAnim(), set = a.set;
  if(!set) return [];
  const sk = (a.skel || '').toLowerCase();
  if(sk && sk === (set.secondary || '').toLowerCase() && sk !== (set.primary || '').toLowerCase())
    return set.secondary_weapons || [];
  return set.primary_weapons || [];
}

async function armAnimPick(key){
  const a = armAnim(), p = armProj();
  const sk = a.list && a.list.skeletons && a.list.skeletons[(a.skel || '').toLowerCase()];
  const row = sk && (sk.actions || []).find(r => (r.slot != null ? String(r.slot) : 'a:' + r.action) === key);
  if(!row || !row.playable) return;
  a.key = key; a.err = ''; a.source=null;
  const pick=a.pickSerial=(a.pickSerial || 0)+1;
  const asset = p.assets.find(x => armAssetKey(x) === (p.anim || {}).asset);
  const from = asset ? asset.mod : (p.anim || {}).mod;
  if(!from) return;
  const q = row.rel ? `rel=${enc(row.rel)}` : `pack=${enc(row.path)}`;
  const w = armAnimWeapons();
  let data;
  try{ data = await api.get(`/api/model/anim?mod=${enc(from)}&${q}&skel=${enc(a.skel)}`
    + (row.slot != null ? `&slot=${row.slot}` : '') + (w.length ? `&weapons=${enc(w.join(','))}` : '')); }
  catch(e){ a.err = errText(e); return armAnimPaint(); }
  if(a.key !== key || a.pickSerial !== pick) return;
  // a rider's action, with his horse loaded too: the horse plays its own
  const mount = asset && v3aCarried(data) ? await armAnimMountLoad(armAssetKey(asset), row.slot) : null;
  // a horse's action, with its rider loaded too: he plays his own on it
  const rider = asset && !mount && !v3aCarried(data) ? await armAnimRiderLoad(armAssetKey(asset), row.slot) : null;
  if(a.key !== key || a.pickSerial !== pick) return;
  a.mount = mount; a.rider = rider;
  data.name = row.action;
  a.data = data;
  a.orig = data;
  a.source = {mod:from, rel:row.rel || '', skeleton:a.skel, slot:row.slot, weapons:w};
  a.scale = [1,1,1]; a.scalePlan = null; a.scaleBusy = false; a.scaleMsg = '';
  a.saveAs = (row.rel || 'animations/action.cas').replace(/\.cas$/i,'') + '_scaled.cas';
  a.packName = (row.path || row.rel || 'action').replace(/^.*[\\/]/,'').replace(/\.cas$/i,'') + '_scaled';
  a.saveTarget = sk.packed && row.slot != null && a.list.packs && a.list.packs !== 'vanilla' ? 'pack' : 'loose';
  if(!row.rel) a.saveTarget = 'pack';
  a.bind = v3aBind(data);
  a.travel = v3aTravel(data);
  a.carried = v3aCarried(data);
  a.t = 0; a.playing = true; a.last = performance.now();
  a.geos.forEach(g => { g.map = null; });
  armAnimPaint();
  armAnimLoop();
}

function armAnimScaleEdits(){
  const scale=armAnim().scale || [1,1,1];
  return scale.some(v=>+v !== 1) ? {scale:scale.map(Number)} : {};
}
function armAnimScaleBody(){
  const a=armAnim();
  return Object.assign({},a.source,{edits:armAnimScaleEdits(),target:a.saveTarget,
    save_as:a.saveAs,name:a.packName,keep_rebuildable:true});
}
function armAnimScaleHtml(){
  const a=armAnim();
  if(!a.source) return '';
  const scale=a.scale || [1,1,1];
  const input=(i,value)=>`<input type="number" min="0.001" step="0.01" value="${esc(value)}" style="width:64px" onchange="armAnimScaleSet(${i},this.value)"${a.scaleBusy ? ' disabled' : ''}>`;
  return `<div class="count">${tt('armory.anim_scale_note')}</div>
    <label>${tt('armory.anim_scale')}${input(-1,scale.every(v=>v===scale[0]) ? scale[0] : '')}</label>
    <details${a.scaleAxes ? ' open' : ''} ontoggle="armAnim().scaleAxes=this.open"><summary>${tt('armory.anim_scale_axes')}</summary>
      ${['X','Y','Z'].map((axis,i)=>`<label>${axis}${input(i,scale[i])}</label>`).join('')}</details>
    <label>${tt('armory.anim_scale_target')}<select onchange="armAnimScaleOption('saveTarget',this.value)">
      ${a.source.slot != null ? `<option value="pack"${a.saveTarget === 'pack' ? ' selected' : ''}>${tt('armory.anim_scale_pack')}</option>` : ''}
      ${a.source.rel ? `<option value="loose"${a.saveTarget === 'loose' ? ' selected' : ''}>${tt('armory.anim_scale_loose')}</option>` : ''}</select></label>
    <label>${tt('armory.anim_scale_name')}<input value="${esc(a.saveTarget === 'pack' ? a.packName : a.saveAs)}"
      onchange="armAnimScaleOption(armAnim().saveTarget === 'pack' ? 'packName' : 'saveAs',this.value)"></label>
    <button onclick="armAnimScaleSave()"${a.scaleBusy || !armAnimScaleEdits().scale ? ' disabled' : ''}>${tt('armory.anim_scale_save')}</button>
    ${a.scalePlan ? `<pre class="count">${esc(a.scalePlan.target || '')}\n${esc((a.scalePlan.notes || []).join('\n'))}</pre>` : ''}
    ${a.scaleMsg ? `<div class="count">${esc(a.scaleMsg)}</div>` : ''}`;
}
function armAnimScaleOption(key,value){
  const a=armAnim(); a[key]=value; a.scalePlan=null; a.scaleMsg=''; armAnimPaint();
}
async function armAnimScaleSet(axis,value){
  const a=armAnim(), n=Number(value);
  if(!a.source || !Number.isFinite(n) || n<=0){ a.scaleMsg=tt('armory.anim_scale_invalid'); armAnimPaint(); return; }
  const scale=(a.scale || [1,1,1]).slice();
  if(axis<0) scale.fill(n); else scale[axis]=n;
  a.scale=scale; a.scalePlan=null; a.scaleMsg='';
  const source=a.source, serial=a.scaleSerial=(a.scaleSerial || 0)+1;
  if(!armAnimScaleEdits().scale){
    a.data=a.orig; a.travel=v3aTravel(a.data); a.carried=v3aCarried(a.data);
    a.scaleBusy=false; armAnimPaint(); armFrame(); return;
  }
  a.scaleBusy=true; armAnimPaint();
  try{
    const data=await api.post('/api/model/anim/preview',armAnimScaleBody());
    if(a.source !== source || a.scaleSerial !== serial) return;
    if(data.error) throw new Error(data.error);
    data.name=a.orig.name;
    a.data=data; a.travel=v3aTravel(data); a.carried=v3aCarried(data);
    a.geos.forEach(g=>{g.map=null;});
    armFrame();
  }catch(err){ if(a.source === source && a.scaleSerial === serial) a.scaleMsg=errText(err); }
  finally{ if(a.source === source && a.scaleSerial === serial){ a.scaleBusy=false; armAnimPaint(); } }
}
async function armAnimScaleSave(){
  const a=armAnim();
  if(!a.source || a.scaleBusy || !armAnimScaleEdits().scale) return;
  const body=armAnimScaleBody(), source=a.source;
  a.scaleBusy=true; a.scaleMsg=''; armAnimPaint();
  try{
    const r=await api.post('/api/model/anim/save_plan',body);
    if(a.source !== source) return;
    if(r.error || !r.plan || !r.plan.ok) throw new Error(r.error || tt('armory.anim_scale_no_plan'));
    a.scalePlan=r.plan; armAnimPaint();
    const text=JSON.stringify(r.plan,null,2);
    if(!confirm(tt('armory.anim_scale_confirm',{plan:text}))) return;
    const written=await api.post('/api/model/anim/save_apply',body);
    if(written.error) throw new Error(written.error);
    if(a.source !== source) return;
    a.scalePlan=null;
    // Read the source again: the next scale is relative to the saved action.
    await armAnimPick(a.key);
    a.scaleMsg=tt('armory.anim_scale_saved'); armAnimPaint();
  }catch(err){ if(a.source === source) a.scaleMsg=errText(err); }
  finally{ if(a.source === source){ a.scaleBusy=false; armAnimPaint(); } }
}

function armAnimLength(){ const d = armAnim().data; return d && d.times && d.times.length ? d.times[d.times.length - 1] : 0; }
function armAnimFrac(){ const a = armAnim(), len = armAnimLength(); return len > 0 ? Math.round((((a.t % len) + len) % len) / len * 1000) : 0; }
function armAnimPlay(){ const a = armAnim(); a.playing = !a.playing; a.last = performance.now(); armAnimPaint(); armAnimLoop(); }
function armAnimScrub(v){ const a = armAnim(); a.playing = false; a.t = armAnimLength() * v / 1000; armFrame(); }
/* Back to the bind pose: the model as it stands still. */
function armAnimRest(){
  const a = armAnim();
  a.data = null; a.key = ''; a.source=null; a.mount = null; a.rider = null; a.pickSerial=(a.pickSerial || 0)+1;
  armFrame();
}

/* --- a rider on his horse ----------------------------------------------------------
   A cavalry model is two entries: the rider, and the mount descr_mount.txt
   gives his units. Loaded together and posed by the rider's action, the
   horse's parts play the horse's own action for the same slot (v3aMountRow)
   and the rider is carried at its root bone, bone_H_Saddle, offset by
   rider_offset (v3aCarry), as the Models viewer (80b) and the game do. Posed
   by one skeleton, every horse bone went with the rider's pelvis: the horse
   stood in its bind pose and the rider sat behind the saddle. */

/* The loaded entry that is a mount of the rider entry `key`, with its
   descr_mount.txt row ({entry, skeleton, offset}), or null. */
async function armAnimMountOf(key){
  const p = armProj(), asset = p.assets.find(x => armAssetKey(x) === key);
  if(!asset || asset.kind !== 'entry') return null;
  ARM.mountRows = ARM.mountRows || {};
  if(!ARM.mountRows[key]){
    let r;
    try{ r = await api.get(`/api/model/mounts?mod=${enc(asset.mod)}&entry=${enc(asset.entry)}`); }catch(e){ r = null; }
    ARM.mountRows[key] = (r && r.mounts) || [];
  }
  for(const row of ARM.mountRows[key]){
    const m = p.assets.find(x => x !== asset && x.kind === 'entry' && (x.entry || '').toLowerCase() === (row.entry || '').toLowerCase());
    if(m) return {row, asset: m};
  }
  return null;
}
/* The loaded entry that rides another loaded entry, for the card maker's Riding. */
async function armAnimRider(){
  for(const e of armAnimEntries()) if(await armAnimMountOf(armAssetKey(e))) return e;
  return null;
}
async function armAnimMountLoad(key, slot){
  const found = await armAnimMountOf(key);
  if(!found) return null;
  const {row, asset} = found;
  let list, data;
  try{ list = await api.get(`/api/model/anims?mod=${enc(asset.mod)}&entry=${enc(asset.entry)}`); }catch(e){ return null; }
  const sk = ((list && list.skeletons) || {})[(row.skeleton || '').toLowerCase()];
  const r = sk && v3aMountRow(sk.actions, slot).row;
  if(!r) return null;
  const q = r.rel ? `rel=${enc(r.rel)}` : `pack=${enc(r.path)}`;
  try{ data = await api.get(`/api/model/anim?mod=${enc(asset.mod)}&${q}&skel=${enc(row.skeleton)}` + (r.slot != null ? `&slot=${r.slot}` : '')); }
  catch(e){ return null; }
  if(!data || data.error || !data.bones) return null;
  return {key: armAssetKey(asset), data, bind: v3aBind(data), travel: v3aTravel(data),
          hub: data.bones.findIndex(b => b.parent === 0), offset: row.offset || [0, 0, 0]};
}
/* The other way round: the horse's action picked, and a loaded entry that
   rides it plays his first skeleton's action for the same slot (or his idle),
   with the weapons his set hangs off the hand. */
async function armAnimRiderLoad(key, slot){
  let found = null, rider = null;
  for(const e of armAnimEntries()){
    const k = armAssetKey(e);
    if(k === key) continue;
    const f = await armAnimMountOf(k);
    if(f && armAssetKey(f.asset) === key){ found = f; rider = e; break; }
  }
  if(!found) return null;
  let list, data;
  try{ list = await api.get(`/api/model/anims?mod=${enc(rider.mod)}&entry=${enc(rider.entry)}`); }catch(e){ return null; }
  const set = ((list && list.sets) || [])[0] || {}, skel = set.primary || '';
  const sk = ((list && list.skeletons) || {})[skel.toLowerCase()];
  const r = sk && v3aMountRow(sk.actions, slot).row;
  if(!r) return null;
  const q = r.rel ? `rel=${enc(r.rel)}` : `pack=${enc(r.path)}`, w = set.primary_weapons || [];
  try{ data = await api.get(`/api/model/anim?mod=${enc(rider.mod)}&${q}&skel=${enc(skel)}`
    + (r.slot != null ? `&slot=${r.slot}` : '') + (w.length ? `&weapons=${enc(w.join(','))}` : '')); }
  catch(e){ return null; }
  if(!data || data.error || !data.bones) return null;
  return {key: armAssetKey(rider), data, bind: v3aBind(data),
          hub: data.bones.findIndex(b => b.parent === 0), offset: found.row.offset || [0, 0, 0]};
}
const armAnimAssetOf =o => ((o && o.src) || [])[0] ? o.src[0].asset : '';
function armAnimNote(){
  const a = armAnim();
  const bits = [];
  const missing = new Set(), still = [];
  for(const g of a.geos.values()){
    (g.missing || []).forEach(n => missing.add(n));
    if(g.unweighted && g.obj && !g.obj.hidden) still.push(g.obj.mesh);
  }
  if(missing.size) bits.push(tt('armory.anim_missing', {names: [...missing].slice(0, 5).join(', ')}));
  if(still.length) bits.push(tt('armory.anim_unweighted', {names: still.slice(0, 5).join(', ')}));
  return bits.length ? esc(bits.join(' ')) : tt('armory.anim_all_follow');
}

/* --- each object, laid out and skinned -------------------------------------------- */

function armAnimGeo(o){
  const a = armAnim();
  const sig = JSON.stringify([o.src, o.t, o.r, o.s, o.weights ? o.weights.data.length : 0]);
  let g = a.geos.get(o.id);
  if(g && g.sig === sig) return g;
  if(g) armAnimFree(g);
  const om = armObjMatrix(o, armPivot(o));
  const pos = [], nrm = [], uv = [], W = [], J = [], bones = [], ranges = [], idx = [];
  const boneOf = name => { let i = bones.indexOf(name); if(i < 0){ i = bones.length; bones.push(name); } return i; };
  for(const pc of o.src || []){
    const live = ARM.assets.get(pc.asset);
    if(!live || !live.geo) return null;
    const geo = live.geo, P = geo.positions, N = geo.normals, U = geo.uvs;
    const m = pc.xf ? armMul(om, pc.xf) : om;
    const flat = [];
    armPieceEach(live, pc, v => flat.push(v));
    // the vertices in index order, as armory.object_mesh lays them out, so
    // weights transferred on the server line up
    const used = [...new Set(flat)].sort((x, y) => x - y);
    const base = pos.length / 3, remap = new Map(used.map((v, i) => [v, base + i]));
    for(const v of used){
      const x = P[v*3], y = P[v*3+1], z = P[v*3+2];
      pos.push(m[0]*x + m[4]*y + m[8]*z + m[12], m[1]*x + m[5]*y + m[9]*z + m[13], m[2]*x + m[6]*y + m[10]*z + m[14]);
      const rn = pc.nrm && pc.nrm[v];        // 100n: normals Optimize worked out
      if(rn || N){
        const nx = rn ? rn[0] : N[v*3], ny = rn ? rn[1] : N[v*3+1], nz = rn ? rn[2] : N[v*3+2];
        const q = [m[0]*nx + m[4]*ny + m[8]*nz, m[1]*nx + m[5]*ny + m[9]*nz, m[2]*nx + m[6]*ny + m[10]*nz];
        const l = Math.hypot(q[0], q[1], q[2]) || 1;
        nrm.push(q[0]/l, q[1]/l, q[2]/l);
      }else nrm.push(0, 1, 0);
      // 100m: UVs moved in the UV editor
      const mv = pc.uv && pc.uv[v];
      uv.push(mv ? mv[0] : U ? U[v*2] : 0, mv ? mv[1] : U ? U[v*2+1] : 0);
      if(geo.weights && geo.joints){
        W.push(geo.weights[v*2], geo.weights[v*2+1]);
        J.push(boneOf((geo.bones || [])[geo.joints[v*2]] || ''), boneOf((geo.bones || [])[geo.joints[v*2+1]] || ''));
      }else{ W.push(0, 0); J.push(0, 0); }
    }
    const start = idx.length;
    for(const v of flat) idx.push(remap.get(v));
    ranges.push({pc, start, count: flat.length});
  }
  const n = pos.length / 3;
  // weights of its own, transferred in 95f, replace the source's
  if(o.weights && o.weights.n === n){
    const raw = Uint8Array.from(atob(o.weights.data), c => c.charCodeAt(0));
    const wf = new Float32Array(raw.buffer.slice(0, n * 8));
    const ids = raw.subarray(n * 8);
    bones.length = 0;
    for(let v = 0; v < n; v++){
      W[v*2] = wf[v*2]; W[v*2+1] = wf[v*2+1];
      J[v*2] = boneOf(o.weights.bones[ids[v*4+2]] || '');
      J[v*2+1] = boneOf(o.weights.bones[ids[v*4+1]] || '');
    }
  }
  // weight 0 on a named bone is a rigid part held by that bone (v3aSkin);
  // unweighted is a part that names no bone at all
  const unweighted = !W.some(w => w > 0) && !bones.some(Boolean);
  const gl = armGl();
  const buf = (data, type, usage) => { const b = gl.createBuffer(); gl.bindBuffer(type, b); gl.bufferData(type, data, usage); return b; };
  g = {sig, obj: o, vertices: n, positions: new Float32Array(pos), normals: new Float32Array(nrm),
       weights: new Float32Array(W), joints: new Uint8Array(J), bones, ranges, unweighted,
       outPos: new Float32Array(pos.length), outNrm: new Float32Array(nrm.length), map: null};
  g.glPos = buf(g.positions, gl.ARRAY_BUFFER, gl.DYNAMIC_DRAW);
  g.glNrm = buf(g.normals, gl.ARRAY_BUFFER, gl.DYNAMIC_DRAW);
  g.glUv = buf(new Float32Array(uv), gl.ARRAY_BUFFER, gl.STATIC_DRAW);
  g.glIdx = buf(new Uint16Array(idx), gl.ELEMENT_ARRAY_BUFFER, gl.STATIC_DRAW);
  a.geos.set(o.id, g);
  return g;
}
function armAnimFree(g){
  const gl = ARM.gl;
  if(!gl) return;
  [g.glPos, g.glNrm, g.glUv, g.glIdx].forEach(b => b && gl.deleteBuffer(b));
}

/* Called by armRender for each object while an action is chosen: the posed
   object, or null to draw it still. */
function armAnimGeoFor(o, card){
  const a = ARM.anim;
  if(!a || !a.data || ARM.detail || (a.tpose && !card)) return null;
  const g = armAnimGeo(o);
  return g && g.posed ? g : null;
}

/* Pose every visible object for the clock's time; the card maker passes its
   own objects, posed even in T-pose. */
function armAnimPose(objs){
  const a = ARM.anim;
  if(!a || !a.data || (a.tpose && !objs)) return;
  const card = !!objs;
  objs = objs || armVisibleObjects();
  const geos = objs.map(armAnimGeo).filter(Boolean);
  if(!geos.length) return;
  // stood on the ground as the still model stood: lowered by its lowest point
  let low = Infinity;
  for(const g of geos) for(let i = 1; i < g.positions.length; i += 3) if(g.positions[i] < low) low = g.positions[i];
  const len = armAnimLength(), f = len > 0 ? ((a.t % len) + len) % len / len : 0;
  const tr = a.travel || [0, 0];
  // 99n: the card maker's IK rig poses the skeleton itself, about the bind
  // pose's own pelvis, so the model stays where it stood
  const rig = card && typeof cgRigActive === 'function' && cgRigActive();
  let pose = rig ? cgRigPose(a.data) : v3aPose(a.data, a.t);
  let shift = rig ? [0, 0, 0] : [-tr[0] * f, a.carried ? 0 : (isFinite(low) ? low : 0), -tr[1] * f];
  a.ground = shift[1];      // armBonesDraw lowers the skeleton with the model
  // a man on his horse: whichever of the two was picked, the horse stands as
  // a man on foot does and carries the man at its root plus rider_offset
  const own = {key: '', data: a.data, bind: a.bind, pose, shift};
  let horse = null, man = null;
  const m = !rig && a.mount && a.mount.hub >= 0 ? a.mount : null;
  const r = !rig && !m && a.rider && a.rider.hub >= 0 ? a.rider : null;
  if(m){
    const mt = m.data.times || [], ml = mt.length ? mt[mt.length - 1] : 0;
    const mf = ml > 0 ? ((a.t % ml) + ml) % ml / ml : 0, mtr = m.travel || [0, 0];
    horse = {key: m.key, data: m.data, bind: m.bind, pose: v3aPose(m.data, a.t),
             shift: [-mtr[0] * mf, isFinite(low) ? low : 0, -mtr[1] * mf]};
    man = own;
    man.pose = v3aCarry(pose, horse.pose[m.hub], m.offset, horse.shift);
    man.shift = [0, 0, 0];
  }else if(r){
    const hub = a.data.bones.findIndex(b => b.parent === 0);
    horse = own;
    man = {key: r.key, data: r.data, bind: r.bind, shift: [0, 0, 0],
           pose: v3aCarry(v3aPose(r.data, a.t), pose[Math.max(0, hub)], r.offset, shift)};
  }
  const gl = armGl();
  for(const g of geos){
    const k = armAnimAssetOf(g.obj);
    // the picked action's own model is everything not the other one
    const by = horse && horse.key && k === horse.key ? horse : man && man.key && k === man.key ? man : own;
    if(g.unweighted){
      // with no weights a part stands still; on a horse it rides with the man
      if(!man || by !== man){ g.posed = false; continue; }
      const hub = by.data.bones.findIndex(b => b.parent === 0);
      const W = new Float32Array(g.vertices * 2);
      for(let v = 0; v < g.vertices; v++) W[v*2] = 1;
      v3aSkin(Object.assign({}, g, {weights: W, joints: new Uint8Array(g.vertices * 2)}), by.pose, by.bind,
              [Math.max(0, hub)], g.outPos, g.outNrm, by.shift);
    }else{
      const d = by.data;
      if(!g.map || g.mapOf !== d){
        const bm = v3aBoneMap(g.bones, d);
        const used = new Set();
        for(let v = 0; v < g.vertices * 2; v++) if(g.weights[v] > 0) used.add(g.joints[v]);
        g.map = bm.map; g.mapOf = d;
        g.missing = bm.missing.filter(n => n && used.has(g.bones.indexOf(n)));
      }
      v3aSkin(g, by.pose, by.bind, g.map, g.outPos, g.outNrm, by.shift);
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, g.glPos); gl.bufferSubData(gl.ARRAY_BUFFER, 0, g.outPos);
    gl.bindBuffer(gl.ARRAY_BUFFER, g.glNrm); gl.bufferSubData(gl.ARRAY_BUFFER, 0, g.outNrm);
    g.posed = true;
  }
}

/* The clock: a frame asked for while playing, never in a hidden tab (memory:
   requestAnimationFrame does not fire there), picked up again on return. */
function armAnimLoop(){
  const a = ARM.anim;
  if(!a || !a.data || !a.playing || a.looping || a.tpose) return;
  if(document.hidden){
    const back = () => { document.removeEventListener('visibilitychange', back); a.last = performance.now(); armAnimLoop(); };
    document.addEventListener('visibilitychange', back);
    return;
  }
  a.looping = true;
  requestAnimationFrame(() => {
    a.looping = false;
    if(state.mode !== 'armory' || !a.data || !a.playing || a.tpose) return;
    const now = performance.now();
    a.t += (now - (a.last || now)) / 1000 * a.speed;
    a.last = now;
    armDraw();
    const r = document.getElementById('armAnimT');
    if(r && (!a.painted || now - a.painted > 200)){ a.painted = now; r.value = armAnimFrac(); }
    armAnimLoop();
  });
}
