/* v3anim.js - a battle model that moves (Phase 55b)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Loaded
   after viewer3d.js, whose `v3` state, tick loop and side panel this
   hooks into; viewer3d.js calls in here only through `typeof` guards. */
/* =========================================================================
   PLAYING A MODEL'S ANIMATIONS - the chain, then the skin.

   The chain is the server's (animview.entry_view, Phase 80): a modeldb entry
   names its skeleton sets, one per mount type, and every filled slot of each
   skeleton in the mod's skeletons.dat is an action, named by Phase 78's slot
   table and read straight out of pack.dat with the packed skeleton's bones -
   which is why every request for keys carries the skeleton's name. A loose
   file at the same path is preferred; a skeleton the pack has not got falls
   back to Phase 55's chain, descr_skeleton.txt and loose files only.

   The skin is done HERE, on the CPU, into the same position and normal buffers
   the static model draws from. A soldier is 30 000 vertices over two bones
   each, which is a millisecond a frame; skinning in the shader would mean a
   second program, a bone-count ceiling WebGL 1 sets low, and the wireframe and
   UV tools taught about it - for no frame a person could see.

   Four facts about the files drive it (casanim.py and mesh.py have the
   measurements):

     * a rotation key is a quaternion x y z w, and a position key is an OFFSET
       from the bone's pivot - a soldier's pelvis keys its height, every other
       bone keys zero and sits at its pivot;
     * the model's bind pose is the skeleton with every rotation identity and
       the pelvis at the origin: vertices sit around their bones' pivots,
       chained from zero, arms out in a T;
     * a vertex has two weights, and its two bones are named by index into the
       model's own bone table - which is tied to the skeleton by NAME, because
       the model carries weapon and shield bones the skeleton does not;
     * the animation stands the man on the ground, pelvis at about 0.97, while
       the model is framed around its pelvis at 0 - so the pose is lowered by
       the model's own lowest point, and the ground stays where the still model
       had its feet.

   80b assembles the unit as the game does. The server hangs each WEAPON
   skeleton's bones (bone_weapon01, bone_shield) under the body's hand for the
   action's slot, so a mesh weighted to them - 1 066 of ROCSS's 1 800 soldier
   meshes - moves its weapon with the arm; a rider can be drawn ON HIS MOUNT,
   the mount playing the same slot and the rider's pose carried by its root
   bone at descr_mount.txt's rider_offset; a strat .cas plays by the skeleton
   its descr_model_strat.txt entry names; and the same action out of another
   mod can stand beside it, which is how a port is checked.

   And one about the actions: a CYCLE travels. MTW2_Mace's walk carries the
   pelvis 1.62 forward over its 0.9 s and its charge 2.58, so looped as written
   the man strides out of the frame and snaps back. A cycle is known by its
   last key being its first for every bone's rotation (exactly, on those two),
   and is played in place by taking its travel out evenly over the loop - see
   v3aTravel. A death or a turn does not close, and keeps its motion.
   ========================================================================= */

/* --- the arithmetic (pure: tests/test_v3anim.py runs these under node) ---- */

/* Each track's LOCAL rotation and position at `t` seconds, looping - the
   mirror of casanim.sample(), which is the reference it is tested against. */
function v3aSample(anim, t){
  const times = anim.times || [];
  const end = times.length ? times[times.length-1] : 0;
  if(times.length > 1 && end > 0) t = ((t % end) + end) % end;
  let i = 0, f = 0;
  if(times.length > 1){
    i = times.length - 2; f = 1;
    for(let k = 0; k < times.length - 1; k++){
      if(times[k+1] >= t){
        const span = times[k+1] - times[k];
        i = k; f = span <= 0 ? 0 : (t - times[k]) / span;
        break;
      }
    }
  }
  return anim.bones.map(b => {
    const rk = b.rot.length, pk = b.pos.length;
    const at = (arr, k) => arr[Math.max(0, Math.min(k, arr.length-1))];
    let q;
    if(rk > 1) q = v3aSlerp(at(b.rot, i), at(b.rot, i+1), f);
    else q = rk ? v3aQNorm(b.rot[0]) : [0,0,0,1];
    let off = [0,0,0];
    if(pk > 1){
      const a = at(b.pos, i), c = at(b.pos, i+1);
      off = [0,1,2].map(k => a[k] + (c[k]-a[k]) * f);
    }else if(pk) off = b.pos[0];
    return {q, p: [0,1,2].map(k => b.pivot[k] + off[k])};
  });
}

function v3aQNorm(q){
  const n = Math.hypot(q[0], q[1], q[2], q[3]) || 1;
  return [q[0]/n, q[1]/n, q[2]/n, q[3]/n];
}

function v3aSlerp(a, b, f){
  let dot = a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3];
  if(dot < 0){ b = [-b[0], -b[1], -b[2], -b[3]]; dot = -dot; }   // the short way
  let q;
  if(dot > 0.9995) q = [0,1,2,3].map(k => a[k] + (b[k]-a[k]) * f);
  else{
    const th = Math.acos(Math.max(-1, Math.min(1, dot))), s = Math.sin(th);
    const wa = Math.sin((1-f)*th) / s, wb = Math.sin(f*th) / s;
    q = [0,1,2,3].map(k => wa*a[k] + wb*b[k]);
  }
  return v3aQNorm(q);
}

/* A unit quaternion as a row-major 3x3. */
function v3aMat(q){
  const [x,y,z,w] = q;
  return [1-2*(y*y+z*z), 2*(x*y-z*w),   2*(x*z+y*w),
          2*(x*y+z*w),   1-2*(x*x+z*z), 2*(y*z-x*w),
          2*(x*z-y*w),   2*(y*z+x*w),   1-2*(x*x+y*y)];
}
function v3aMul(a, b){
  const o = new Array(9);
  for(let r = 0; r < 3; r++) for(let c = 0; c < 3; c++)
    o[r*3+c] = a[r*3]*b[c] + a[r*3+1]*b[3+c] + a[r*3+2]*b[6+c];
  return o;
}
function v3aApply(m, v){
  return [m[0]*v[0]+m[1]*v[1]+m[2]*v[2],
          m[3]*v[0]+m[4]*v[1]+m[5]*v[2],
          m[6]*v[0]+m[7]*v[1]+m[8]*v[2]];
}

/* Every track's WORLD rotation and position at `t`. A parent always comes
   before its children in these files, which casanim's parent check holds. */
function v3aPose(anim, t){
  const local = v3aSample(anim, t);
  const out = [];
  anim.bones.forEach((b, i) => {
    const m = v3aMat(local[i].q);
    const par = b.parent >= 0 && b.parent < i ? out[b.parent] : null;
    if(!par){ out.push({m, p: local[i].p}); return; }
    const d = v3aApply(par.m, local[i].p);
    out.push({m: v3aMul(par.m, m),
              p: [par.p[0]+d[0], par.p[1]+d[1], par.p[2]+d[2]]});
  });
  return out;
}

/* The bind pose: identity rotations, pivots chained from the root. */
function v3aBind(anim){
  const out = [];
  anim.bones.forEach((b, i) => {
    const par = b.parent >= 0 && b.parent < i ? out[b.parent] : [0,0,0];
    out.push([par[0]+b.pivot[0], par[1]+b.pivot[1], par[2]+b.pivot[2]]);
  });
  return out;
}

/* How far a CYCLE carries the pelvis across the ground in one loop, as
   [x, z], or null for an action that is not a cycle. A cycle closes: every
   bone's last rotation key is its first (q or -q, which are one rotation).
   The hub is the root's first child, the pelvis on every soldier. */
function v3aTravel(anim){
  const hub = anim.bones.findIndex(b => b.parent === 0);
  if(hub < 0) return null;
  for(const b of anim.bones){
    if(b.rot.length < 2) continue;
    const a = b.rot[0], z = b.rot[b.rot.length-1];
    const same = Math.max(...[0,1,2,3].map(k => Math.abs(a[k] - z[k])));
    const flip = Math.max(...[0,1,2,3].map(k => Math.abs(a[k] + z[k])));
    if(Math.min(same, flip) > 0.01) return null;
  }
  const p = anim.bones[hub].pos;
  if(p.length < 2) return [0, 0];
  const a = p[0], z = p[p.length-1];
  return [z[0] - a[0], z[2] - a[2]];
}

/* A rider's action: its pelvis never leaves the origin, because a rider (the
   HR_* and CR_* folders) keeps its pelvis as the control bone and is carried
   by its mount. Such a pose is drawn where the model sits, not lowered onto
   the ground as a man on foot is. */
function v3aCarried(anim){
  const hub = anim.bones.findIndex(b => b.parent === 0);
  if(hub < 0) return false;
  const b = anim.bones[hub];
  if(Math.abs(b.pivot[1]) > 0.05) return false;
  return (b.pos || []).every(p => Math.abs(p[1]) < 0.05);
}

/* The model's bones -> the animation's tracks, by name. A bone the skeleton
   does not have (a weapon or shield bone, which soldiers carry and never
   weight a vertex to) goes with the pelvis, so anything that did hang off one
   would at least travel with the man. Returns the map and the names it could
   not place. */
function v3aBoneMap(meshBones, anim){
  const byName = new Map(anim.bones.map((b, i) => [b.name.toLowerCase(), i]));
  // the pelvis is the root's first child: the Scene Root itself never moves
  let hub = anim.bones.findIndex(b => b.parent === 0);
  if(hub < 0) hub = 0;
  const missing = [];
  const map = (meshBones || []).map(n => {
    const i = byName.get((n || '').toLowerCase());
    if(i === undefined){ missing.push(n); return hub; }
    return i;
  });
  return {map, missing};
}

/* Skin the model into `outPos` / `outNrm` for one pose. `shift` is added to
   every vertex: the lift that stands the pose where the model stood (the
   fourth fact at the top of this file), and a cycle's travel taken out. */
function v3aSkin(geo, pose, bind, map, outPos, outNrm, shift){
  const P = geo.positions, N = geo.normals, W = geo.weights, J = geo.joints;
  const nb = map.length;
  // per model bone: the matrix and the translation that take a bind-pose
  // vertex to its posed place, v' = M (v - bind) + p = M v + (p - M bind)
  const M = new Float32Array(nb * 9), T = new Float32Array(nb * 3);
  for(let b = 0; b < nb; b++){
    const k = map[b], m = pose[k].m, j = bind[k];
    const mj = v3aApply(m, j);
    for(let e = 0; e < 9; e++) M[b*9+e] = m[e];
    T[b*3]   = pose[k].p[0] - mj[0] + shift[0];
    T[b*3+1] = pose[k].p[1] - mj[1] + shift[1];
    T[b*3+2] = pose[k].p[2] - mj[2] + shift[2];
  }
  const n = geo.vertices;
  for(let v = 0; v < n; v++){
    const x = P[v*3], y = P[v*3+1], z = P[v*3+2];
    let ox = 0, oy = 0, oz = 0, nx = 0, ny = 0, nz = 0;
    for(let s = 0; s < 2; s++){
      const w = W[v*2+s];
      if(w <= 0) continue;
      let b = J[v*2+s];
      if(b >= nb) b = 0;
      const o = b*9, t = b*3;
      ox += w * (M[o]*x   + M[o+1]*y + M[o+2]*z + T[t]);
      oy += w * (M[o+3]*x + M[o+4]*y + M[o+5]*z + T[t+1]);
      oz += w * (M[o+6]*x + M[o+7]*y + M[o+8]*z + T[t+2]);
      if(N){
        const a = N[v*3], c = N[v*3+1], d = N[v*3+2];
        nx += w * (M[o]*a   + M[o+1]*c + M[o+2]*d);
        ny += w * (M[o+3]*a + M[o+4]*c + M[o+5]*d);
        nz += w * (M[o+6]*a + M[o+7]*c + M[o+8]*d);
      }
    }
    outPos[v*3] = ox; outPos[v*3+1] = oy; outPos[v*3+2] = oz;
    if(N && outNrm){ outNrm[v*3] = nx; outNrm[v*3+1] = ny; outNrm[v*3+2] = nz; }
  }
}

/* --- a sequence (80) ------------------------------------------------------
   Several actions of one skeleton back to back, as one timeline. With OVERLAP
   the next starts `blend` seconds before the last ends and the two are
   crossfaded across that window (Makanyane's "overlap": smooth playback);
   without it each plays exactly as stored, end to end, for inspecting. Pure,
   so tests/test_v3anim.py runs these under node. */

/* Where each action starts on the shared timeline, and how long the whole is. */
function v3aSeqPlan(anims, blend){
  let at = 0;
  const segs = [];
  anims.forEach((a, i) => {
    const t = (a && a.times) || [];
    const len = t.length ? t[t.length-1] : 0;
    const b = i && blend > 0 ? Math.min(blend, len / 2, segs[i-1].len / 2) : 0;
    at -= b;
    segs.push({start: at, len, blend: b});
    at += len;
  });
  return {segs, total: Math.max(0, at)};
}

/* One action's local pose at `t`, held at its last key rather than looping. */
function v3aSampleAt(anim, t){
  const times = anim.times || [];
  const end = times.length ? times[times.length-1] : 0;
  return v3aSample(anim, Math.max(0, Math.min(t, end > 0 ? end - 1e-6 : 0)));
}

/* The sequence's local pose at `t` (looping over the whole). The pelvis is
   pinned over the ground: each action's root motion starts from its own
   origin, so played end to end the man would snap back at every join. */
function v3aSeqSample(anims, t, blend){
  const {segs, total} = v3aSeqPlan(anims, blend);
  if(!segs.length) return [];
  if(total > 0) t = ((t % total) + total) % total;
  let i = segs.length - 1;
  for(let k = 0; k < segs.length; k++) if(t < segs[k].start + segs[k].len){ i = k; break; }
  const at = (k) => t - segs[k].start;
  let out = v3aSampleAt(anims[i], at(i));
  const nx = segs[i+1];
  if(nx && nx.blend > 0 && t >= nx.start){
    const f = Math.min(1, (t - nx.start) / nx.blend);
    const nxt = v3aSampleAt(anims[i+1], at(i+1));
    out = out.map((c, b) => nxt[b] ? {q: v3aSlerp(c.q, nxt[b].q, f),
                                       p: [0,1,2].map(k => c.p[k] + (nxt[b].p[k] - c.p[k]) * f)} : c);
  }
  const hub = anims[i].bones.findIndex(b => b.parent === 0);
  if(hub >= 0 && out[hub]) out[hub] = {q: out[hub].q, p: [0, out[hub].p[1], 0]};
  return out;
}

/* World pose from a local one: v3aPose's chaining, for a pose not sampled
   from one animation. */
function v3aPoseOf(bones, local){
  const out = [];
  bones.forEach((b, i) => {
    const m = v3aMat(local[i].q);
    const par = b.parent >= 0 && b.parent < i ? out[b.parent] : null;
    if(!par){ out.push({m, p: local[i].p}); return; }
    const d = v3aApply(par.m, local[i].p);
    out.push({m: v3aMul(par.m, m), p: [par.p[0]+d[0], par.p[1]+d[1], par.p[2]+d[2]]});
  });
  return out;
}

/* --- a rider on his mount (80b) -------------------------------------------
   The mount's root bone (bone_H_Saddle on a horse) carries the rider: every
   world bone of the rider's pose is taken into the root's frame, offset by
   descr_mount.txt's rider_offset, "(x, y, z) for the rider relative to horse
   or camel root node". `root` is the root's world {m, p}, `lift` what the
   mount itself was shifted by. Pure, so tests/test_v3anim.py runs it. */
function v3aCarry(pose, root, off, lift){
  const o = off || [0, 0, 0], l = lift || [0, 0, 0];
  return pose.map(b => {
    const d = v3aApply(root.m, [b.p[0] + o[0], b.p[1] + o[1], b.p[2] + o[2]]);
    return {m: v3aMul(root.m, b.m),
            p: [root.p[0] + l[0] + d[0], root.p[1] + l[1] + d[1], root.p[2] + l[2] + d[2]]};
  });
}

/* Which of the mount's actions plays under the rider's `slot`: the same slot
   when the mount fills it, else its standing idle, else its default. Returns
   the row and whether it is the same slot. */
function v3aMountRow(actions, slot){
  const rows = (actions || []).filter(r => r.playable);
  const at = n => rows.find(r => r.slot === n);
  const same = slot != null ? at(slot) : null;
  if(same) return {row: same, same: true};
  return {row: at(0) || at(686) || rows[0] || null, same: false};
}

/* --- the picker ------------------------------------------------------------
   The list is the server's (animview.entry_view): the entry's skeleton sets,
   one per mount type, and every filled slot of each skeleton in the mod's
   skeletons.dat, named, grouped by family and played straight out of
   pack.dat. A mod with no pack of its own plays vanilla's, and says so. */

/* Called by v3Load once a model's geometry is in: a skinned .mesh asks which
   actions its skeletons have. A .cas and a static model have none to ask for. */
async function v3AnimInit(){
  if(!v3 || !v3.geo || !v3.geo.skinned) return v3AnimPanel();
  if(!v3.anim) v3.anim = {list: null, set: 0, skel: '', find: '', key: '', data: null,
                          playing: true, t: 0, speed: 1, err: '',
                          seq: [], seqData: null, seqOn: false, overlap: true,
                          weapons: true, mount: null, twin: null};
  if(v3.anim.list) return v3AnimPanel();
  const mine = v3;
  let list;
  // a strat .cas is played by the skeleton its descr_model_strat.txt entry names
  const url = v3.cas ? `/api/map/model/anims?mod=${enc(v3.mod)}&rel=${enc(v3.cas)}`
                     : `/api/model/anims?mod=${enc(v3.mod)}&entry=${enc(v3.entry)}`;
  try{ list = await api.get(url); }
  catch(e){ list = {error: ''+e}; }
  if(v3 !== mine) return;
  v3.anim.list = list;
  // a rider's entry: the mounts its units ride, to show it on one
  if(!v3.cas && (list.sets || []).some(x => (x.mount || 'none').toLowerCase() !== 'none')){
    v3.anim.mount = {on: false, list: null, pick: 0, x: null, data: null, err: ''};
    api.get(`/api/model/mounts?mod=${enc(v3.mod)}&entry=${enc(v3.entry)}`)
      .then(r => { if(v3 === mine && v3.anim.mount){ v3.anim.mount.list = r; v3AnimPanel(); } })
      .catch(e => { if(v3 === mine && v3.anim.mount){ v3.anim.mount.err = '' + e; v3AnimPanel(); } });
  }
  const set = (list.sets || [])[v3.anim.set] || (list.sets || [])[0];
  if(set && !v3.anim.skel) v3.anim.skel = set.primary || set.secondary || '';
  v3AnimPanel();
  v3ExportPanel();
}

/* The skeleton being played, from the list. */
function v3AnimSk(){
  const a = v3 && v3.anim, L = a && a.list;
  return L && L.skeletons ? L.skeletons[(a.skel || '').toLowerCase()] || null : null;
}
function v3AnimKey(row){ return row.slot != null ? String(row.slot) : 'a:' + row.action; }
function v3AnimRow(key){
  const sk = v3AnimSk();
  return sk && (sk.actions || []).find(r => v3AnimKey(r) === key) || null;
}

function v3AnimStats(r){
  const bits = [];
  if(r.frames) bits.push(`${r.frames} f`);
  if(r.duration != null) bits.push(`${(+r.duration).toFixed(2)} s`);
  if(r.distance > 0.01) bits.push(`${(+r.distance).toFixed(2)} m`);
  return bits.join(' · ');
}

/* The option list, by family, filtered by the find box. */
function v3AnimListHtml(){
  const a = v3.anim, sk = v3AnimSk(), L = a.list;
  const q = (a.find || '').trim().toLowerCase();
  const rows = (sk.actions || []).filter(r => !q || r.action.toLowerCase().includes(q)
                                         || (r.file || '').toLowerCase().includes(q));
  if(!rows.length) return `<option disabled>nothing matches “${esc(a.find)}”</option>`;
  return (L.families || [{id: 'other', label: 'Actions'}]).map(f => {
    const mine = rows.filter(r => (r.family || 'other') === f.id);
    if(!mine.length) return '';
    return `<optgroup label="${esc(f.label)} (${mine.length})">${mine.map(r => {
      const k = v3AnimKey(r);
      return `<option value="${esc(k)}" ${k === a.key ? 'selected' : ''} ${r.playable ? '' : 'disabled'}
        title="${esc(r.path || r.file || '')}">${esc(r.action)}${r.playable ? '' : ' - not in the pack'}${
        v3AnimStats(r) ? ' · ' + v3AnimStats(r) : ''}</option>`;
    }).join('')}</optgroup>`;
  }).join('');
}

function v3AnimPanel(){
  const host = document.getElementById('v3anim');
  if(!host) return;
  if(!v3 || !v3.geo || !v3.geo.skinned || !v3.anim){
    host.innerHTML = '';
    return;
  }
  const a = v3.anim, L = a.list;
  if(!L){ host.innerHTML = '<div class="k">Animation <span class="count">reading the packs…</span></div>'; return; }
  if(L.error){ host.innerHTML = `<div class="k">Animation</div><div class="w-bad">${esc(L.error)}</div>`; return; }
  const sets = L.sets || [];
  if(!sets.length){
    host.innerHTML = '<div class="k">Animation</div><div class="count">This entry names no skeleton.</div>';
    return;
  }
  const set = sets[a.set] || sets[0];
  const setSel = sets.length > 1 && v3.cas
    ? `<label class="v3f"><span>Skeleton</span><select onchange="v3AnimSet(this.value)">${
        sets.map((x, n) => `<option value="${n}" ${n === a.set ? 'selected' : ''}>${esc(x.primary)}${
          x.entry ? ' · ' + esc(x.entry) : ''}</option>`).join('')}</select></label>`
    : sets.length > 1
    ? `<label class="v3f"><span>Skeleton set</span><select onchange="v3AnimSet(this.value)">${
        sets.map((x, n) => `<option value="${n}" ${n === a.set ? 'selected' : ''}>${esc(x.mount)} · ${
          esc([x.primary, x.secondary].filter(Boolean).join(' / '))}</option>`).join('')}</select></label>` : '';
  const bodies = [set.primary, set.secondary].filter(Boolean);
  const skSel = v3.cas ? '' : `<label class="v3f"><span>Skeleton</span><select onchange="v3AnimSkel(this.value)">${
    bodies.map((n, i) => {
      const s = L.skeletons[n.toLowerCase()] || {};
      return `<option value="${esc(n)}" ${n.toLowerCase() === (a.skel || '').toLowerCase() ? 'selected' : ''}>${
        i ? 'secondary' : 'primary'}: ${esc(n)} · ${s.packed ? `${(s.actions || []).length} actions`
          : s.found ? `${(s.actions || []).length} in descr_skeleton.txt` : 'not in the pack'}</option>`;
    }).join('')}</select></label>`;
  const sk = v3AnimSk();
  let body;
  if(!sk || (!sk.packed && !sk.found)){
    body = `<div class="w-warn">Neither the skeleton pack nor descr_skeleton.txt has <code>${esc(a.skel)}</code>, `
         + `so the game cannot animate this model with it either.</div>`;
  }else{
    body = `<label class="v3f"><span>Find</span><input type="search" value="${esc(a.find)}"
        placeholder="walk, charge, die, a file name…" oninput="v3AnimFind(this.value)"></label>
      <select id="v3alist" class="v3alist" size="11" onchange="v3AnimPick(this.value)">${v3AnimListHtml()}</select>
      <div class="v3btns"><button onclick="v3AnimPick('')" ${a.key || a.seqOn ? '' : 'disabled'}>Still</button>
        <button onclick="v3AnimSeqAdd()" ${a.key ? '' : 'disabled'} title="Add this action to the end of a sequence">+ Sequence</button></div>`
      + v3AnimSeqHtml()
      + (a.data ? v3AnimPlayHtml() : '')
      + `<div class="count">${sk.packed
          ? `${sk.actions.length} actions, every filled slot of <code>${esc(sk.skeleton)}</code> in `
            + `${L.packs === 'vanilla' ? 'vanilla’s skeleton pack (this mod ships none, so the game plays vanilla’s)'
                                        : 'this mod’s skeleton pack'}, played straight out of <code>pack.dat</code>.`
          : `Not in the skeleton pack; these are <code>descr_skeleton.txt</code>’s actions, and only the ones `
            + `shipped loose play.`}</div>`;
  }
  const wnote = v3AnimWeaponsHtml(set);
  const casNote = v3.cas ? (L.guessed
      ? '<div class="w-warn">No entry in descr_model_strat.txt draws this model, so its skeleton is a guess: every strat skeleton in the pack is offered.</div>'
      : `<div class="count">Played by the skeleton its descr_model_strat.txt entry names (${
          esc(set.entry || '')}).</div>`) : '';
  const notes = [];
  if(a.err) notes.push(`<div class="w-bad">${esc(a.err)}</div>`);
  if(a.data && a.missing && a.missing.length)
    notes.push(`<div class="count">Not in the skeleton, so carried with the pelvis: ${
      a.missing.map(n => `<code>${esc(n)}</code>`).join(', ')}.</div>`);
  if(a.data && !a.seqOn && a.travel && Math.hypot(a.travel[0], a.travel[1]) > 0.05)
    notes.push(`<div class="count">A cycle: it carries the model ${
      Math.hypot(a.travel[0], a.travel[1]).toFixed(2)} across the ground each loop, `
      + `which is taken out here so it plays in place.</div>`);
  if(a.data && a.carried)
    notes.push('<div class="count">A rider’s action: its pelvis rides on the mount, so it is drawn where the model sits, not stood on the ground.</div>');
  if(a.data && (a.data.notes || []).length)
    notes.push(a.data.notes.map(n => `<div class="w-warn">${esc(n)}</div>`).join(''));
  host.innerHTML = `<div class="k">Animation</div>${setSel}${skSel}${casNote}${body}${wnote}`
    + `${v3AnimMountHtml(set)}${v3AnimTwinHtml()}${notes.join('')}${v3AnimPortHtml()}`;
}

/* The weapon skeletons of the body being played: a switch, and what each one
   did with this action. */
function v3AnimWeapons(){
  const a = v3 && v3.anim, L = a && a.list;
  if(!L || !a.weapons) return [];
  const set = (L.sets || [])[a.set] || (L.sets || [])[0];
  if(!set) return [];
  const sk = (a.skel || '').toLowerCase();
  if(sk && sk === (set.secondary || '').toLowerCase() && sk !== (set.primary || '').toLowerCase())
    return set.secondary_weapons || [];
  return set.primary_weapons || [];
}
function v3AnimWeaponsHtml(set){
  const a = v3.anim, L = a.list;
  const sk = (a.skel || '').toLowerCase();
  const mine = sk && sk === (set.secondary || '').toLowerCase() && sk !== (set.primary || '').toLowerCase()
    ? set.secondary_weapons || [] : set.primary_weapons || [];
  if(!mine.length) return '';
  const got = (a.data && !a.seqOn && a.data.weapons) || [];
  const said = mine.map(n => {
    const s = L.skeletons[n.toLowerCase()] || {};
    const r = got.find(g => (g.skeleton || '').toLowerCase() === n.toLowerCase());
    let what = s.packed ? '' : ' (not in the pack)';
    if(r && r.error) what = ` - ${esc(r.error)}`;
    else if(r) what = ` - ${r.bones.length ? r.bones.map(esc).join(', ') : 'no new bone'} on ${esc(r.hangs_off)}, `
                    + `its ${r.slot === 686 ? 'default' : esc(r.action)}`;
    return `<code>${esc(n)}</code>${what}`;
  }).join('; ');
  return `<label class="count" title="The weapon skeletons move the weapon and shield bones. A mesh weighted to them carries its weapon with the arm; without them those vertices go with the pelvis"><input type="checkbox" ${
      a.weapons ? 'checked' : ''} onchange="v3AnimWeaponsOn(this.checked)"> weapon skeletons</label>
    <div class="count">${said}.</div>`;
}
function v3AnimWeaponsOn(on){
  const a = v3 && v3.anim;
  if(!a) return;
  a.weapons = !!on;
  if(a.seqOn) return v3AnimSeqPlay(true);
  return v3AnimPick(a.key);
}

/* Play, pause, scrub and speed, the clock, what the slot says about the
   action on a strip under the scrubber, and the editor for a loose file. */
function v3AnimPlayHtml(){
  const a = v3.anim;
  return `<div class="v3btns v3play">
      <button onclick="v3AnimPlay()" class="${a.playing?'on':''}">${a.playing?'Pause':'Play'}</button>
      <input type="range" id="v3atime" min="0" max="1000" value="${v3AnimFrac()}"
        oninput="v3AnimScrub(this.value)" title="Scrub through the action">
      <select onchange="v3AnimSpeed(this.value)" title="Playback speed">${
        [0.25, 0.5, 1, 2].map(s => `<option value="${s}" ${s===a.speed?'selected':''}>${s}×</option>`).join('')
      }</select></div>
    ${v3AnimMarksHtml()}
    <div class="count" id="v3aclock">${v3AnimClock()}</div>
    ${a.seqOn ? '' : a.edit ? v3AnimEditHtml()
      : '<div class="count">Played from vanilla’s pack: this mod ships none of its own to save an edit into.</div>'}`;
}

/* The slot's impact frame and events at their frames, and its turn limits. */
function v3AnimMarksHtml(){
  const a = v3.anim;
  if(a.seqOn) return '';
  const r = v3AnimRow(a.key);
  if(!r || !r.frames) return '';
  const span = Math.max(1, r.frames - 1);
  const at = f => `${Math.max(0, Math.min(100, f / span * 100)).toFixed(2)}%`;
  const ticks = [];
  if(r.impact_frame > 0)
    ticks.push(`<i class="v3aimp" style="left:${at(r.impact_frame)}" title="impact at frame ${r.impact_frame}"></i>`);
  (r.events || []).forEach(e => ticks.push(`<i class="v3aev" style="left:${at(e.start)};width:${
    e.end > e.start ? ((Math.min(e.end, span) - e.start) / span * 100).toFixed(2) : 0}%" title="${
    esc(e.type)} ${esc(e.name)}, frame ${e.start}${e.end > e.start ? ' to ' + e.end : ''}"></i>`));
  const turn = r.turn && (r.turn[0] || r.turn[1]) ? ` · turns ${r.turn[0]}° to ${r.turn[1]}°` : '';
  const said = [r.impact_frame > 0 ? `impact at frame ${r.impact_frame}` : '',
                (r.events || []).map(e => `${e.type} ${e.name} at ${e.start}`).join(', ')].filter(Boolean);
  return `<div class="v3amarks">${ticks.join('')}</div>
    ${said.length || turn ? `<div class="count">${esc(said.join('; '))}${turn}</div>` : ''}`;
}

function v3AnimSeqHtml(){
  const a = v3.anim;
  if(!a.seq.length) return '';
  const chips = a.seq.map((r, i) => `<span class="v3achip">${i + 1}. ${esc(r.action)}
    <button onclick="v3AnimSeqDrop(${i})" title="Take it out">×</button></span>`).join('');
  return `<div class="v3aseq">${chips}</div>
    <div class="v3btns"><button onclick="v3AnimSeqPlay()" class="${a.seqOn ? 'on' : ''}" ${a.seq.length > 1 ? '' : 'disabled'}>${
      a.seqOn ? '■ Stop the sequence' : '▶ Play the sequence'}</button>
      <label class="count" title="On: each action starts 0.2 s before the last ends, and the two are blended (smooth). Off: each plays exactly as stored, end to end"><input type="checkbox" ${
        a.overlap ? 'checked' : ''} onchange="v3AnimOverlap(this.checked)"> overlap</label>
      <button onclick="v3AnimSeqClear()">Clear</button></div>`;
}

function v3AnimFind(v){
  if(!v3 || !v3.anim) return;
  v3.anim.find = v;
  const el = document.getElementById('v3alist');
  if(el) el.innerHTML = v3AnimListHtml();
}

function v3AnimSet(v){
  if(!v3 || !v3.anim) return;
  const a = v3.anim, set = (a.list.sets || [])[+v];
  a.set = +v;
  a.skel = set ? set.primary || set.secondary || '' : '';
  v3AnimSeqClear(true);
  v3AnimPick('');
}

function v3AnimSkel(v){
  if(!v3 || !v3.anim) return;
  v3.anim.skel = v;
  v3AnimSeqClear(true);
  v3AnimPick('');
}

/* One action's keys: the loose file when there is one, else out of pack.dat. */
async function v3AnimFetch(row, mod, skel, weapons){
  const q = row.rel ? `rel=${enc(row.rel)}` : `pack=${enc(row.path)}`;
  const w = weapons !== undefined ? weapons : v3AnimWeapons();
  const extra = (row.slot != null ? `&slot=${row.slot}` : '') + (w.length ? `&weapons=${enc(w.join(','))}` : '');
  try{ return await api.get(`/api/model/anim?mod=${enc(mod || v3.mod)}&${q}&skel=${enc(skel || v3.anim.skel)}${extra}`); }
  catch(e){ return {error: '' + e}; }
}

async function v3AnimPick(key){
  if(!v3 || !v3.anim) return;
  const a = v3.anim;
  a.key = key; a.err = ''; a.t = 0; a.seqOn = false;
  const row = key ? v3AnimRow(key) : null;
  if(!row || !row.playable){
    a.data = null; a.rel = '';
    if(a.twin) a.twin.data = null;
    v3AnimRest();
    return v3AnimPanel();
  }
  const mine = v3;
  const data = await v3AnimFetch(row);
  if(v3 !== mine || a.key !== key) return;
  if(data.error){ a.data = null; a.err = data.error; v3AnimRest(); return v3AnimPanel(); }
  a.data = data;
  a.orig = data;              // what the editor's Reset goes back to
  a.rel = row.rel || '';
  a.slot = row.slot != null ? row.slot : null;
  a.edit = a.rel || v3AnimPackable(row) ? v3AnimEditNew(data, row) : null;
  a.bind = v3aBind(data);
  a.travel = v3aTravel(data);
  a.carried = v3aCarried(data);
  a.geo = null;               // the bone map is built against the model on the next frame
  a.last = performance.now();
  a.playing = true;
  v3AnimPanel();
  v3AnimMountAction();
  v3AnimTwinAction();
}

function v3AnimSeqAdd(){
  const a = v3 && v3.anim, row = a && v3AnimRow(a.key);
  if(!row) return;
  a.seq.push(row);
  a.seqData = null;
  v3AnimPanel();
}
function v3AnimSeqDrop(i){
  const a = v3.anim;
  a.seq.splice(i, 1);
  a.seqData = null;
  if(a.seq.length < 2 && a.seqOn){ a.seqOn = false; return v3AnimPick(a.key); }
  if(a.seqOn) return v3AnimSeqPlay(true);
  v3AnimPanel();
}
function v3AnimSeqClear(quiet){
  const a = v3 && v3.anim;
  if(!a) return;
  a.seq = []; a.seqData = null;
  if(a.seqOn){ a.seqOn = false; if(!quiet) return v3AnimPick(a.key); }
  if(!quiet) v3AnimPanel();
}
function v3AnimOverlap(on){
  const a = v3.anim;
  a.overlap = !!on; a.dirty = true;
  const c = document.getElementById('v3aclock');
  if(c) c.textContent = v3AnimClock();
}

/* Load every action of the sequence, then play them as one. */
async function v3AnimSeqPlay(restart){
  const a = v3.anim;
  if(a.seqOn && !restart){ a.seqOn = false; return v3AnimPick(a.key); }
  if(a.seq.length < 2) return;
  const mine = v3, want = a.seq.slice();
  const got = [];
  for(const r of want){
    const d = await v3AnimFetch(r);
    if(v3 !== mine) return;
    if(d.error){ a.err = `${r.action}: ${d.error}`; return v3AnimPanel(); }
    got.push(d);
  }
  a.seqData = got;
  a.seqOn = true;
  a.data = got[0];
  a.bind = v3aBind(got[0]);
  a.travel = null;
  a.carried = got.every(v3aCarried);
  a.geo = null; a.t = 0; a.playing = true; a.last = performance.now();
  v3AnimPanel();
  v3AnimMountAction();
}

const V3A_BLEND = 0.2;

function v3AnimPlay(){
  if(!v3 || !v3.anim) return;
  v3.anim.playing = !v3.anim.playing;
  v3.anim.last = performance.now();
  v3AnimPanel();
}
function v3AnimSpeed(v){ if(v3 && v3.anim) v3.anim.speed = +v || 1; }
function v3AnimLength(){
  const a = v3 && v3.anim;
  if(a && a.seqOn && a.seqData) return v3aSeqPlan(a.seqData, a.overlap ? V3A_BLEND : 0).total;
  const d = a && a.data;
  const t = d && d.times;
  return t && t.length ? t[t.length-1] : 0;
}
function v3AnimFrac(){
  const len = v3AnimLength();
  return len > 0 ? Math.round((((v3.anim.t % len) + len) % len) / len * 1000) : 0;
}
function v3AnimClock(){
  const a = v3 && v3.anim, len = v3AnimLength();
  if(!a || !a.data) return '';
  const now = len > 0 ? (((a.t % len) + len) % len) : 0;
  if(a.seqOn && a.seqData){
    const {segs} = v3aSeqPlan(a.seqData, a.overlap ? V3A_BLEND : 0);
    let i = segs.length - 1;
    for(let k = 0; k < segs.length; k++) if(now < segs[k].start + segs[k].len){ i = k; break; }
    return `${now.toFixed(2)} s of ${len.toFixed(2)} s · ${i + 1} of ${segs.length}: ${
      a.seq[i] ? a.seq[i].action : ''} · ${a.overlap ? 'overlapped' : 'end to end'}, in place`;
  }
  const frame = Math.round(now * 20);
  return `${now.toFixed(2)} s of ${len.toFixed(2)} s · frame ${frame} of ${a.data.times.length - 1} · `
       + `${a.data.bones.length - 1} bones`;
}
function v3AnimScrub(v){
  if(!v3 || !v3.anim || !v3.anim.data) return;
  v3.anim.t = (+v / 1000) * v3AnimLength();
  v3.anim.playing = false;
  v3.anim.dirty = true;
  const b = document.querySelector('#v3anim .v3play button');
  if(b){ b.textContent = 'Play'; b.classList.remove('on'); }
  const c = document.getElementById('v3aclock');
  if(c) c.textContent = v3AnimClock();
}

/* --- every frame ---------------------------------------------------------- */

/* Called from the viewer's tick before it draws. Advances the clock, poses the
   skeleton and skins the model into the buffers the draw is about to read. */
function v3AnimStep(){
  const a = v3 && v3.anim;
  if(!a || !a.data || !v3.gl || !v3.geo || !v3.geo.skinned) return;
  const now = performance.now();
  if(a.playing){
    a.t += (now - (a.last || now)) / 1000 * a.speed;
    a.dirty = true;
  }
  a.last = now;
  const g = v3.geo;
  // a repaint of the viewer builds a new canvas and new buffers holding the
  // bind pose, so a paused pose has to be written into them again
  if(a.buf !== v3.bPos){ a.buf = v3.bPos; a.dirty = true; }
  if(a.geo !== g){
    // a new LOD is a new bone table and new buffers to write into
    const bm = v3aBoneMap(g.bones, a.data);
    // only a missing bone something hangs off is worth saying: every soldier
    // carries weapon and shield bones that no vertex is weighted to
    const used = new Set();
    for(let v = 0; v < g.vertices * 2; v++) if(g.weights[v] > 0) used.add(g.joints[v]);
    a.map = bm.map;
    a.missing = bm.missing.filter(n => used.has(g.bones.indexOf(n)));
    a.pos = new Float32Array(g.vertices * 3);
    a.nrm = g.normals ? new Float32Array(g.vertices * 3) : null;
    a.geo = g; a.dirty = true;
    v3AnimPanel();
  }
  if(!a.dirty) return;
  a.dirty = false;
  let pose, shift;
  if(a.seqOn && a.seqData){
    pose = v3aPoseOf(a.data.bones, v3aSeqSample(a.seqData, a.t, a.overlap ? V3A_BLEND : 0));
    shift = [0, a.carried ? 0 : g.min[1], 0];
  }else{
    // a cycle walks in place: its travel so far this loop is taken back out
    const len = v3AnimLength(), f = len > 0 ? ((a.t % len) + len) % len / len : 0;
    const tr = a.travel || [0, 0];
    pose = v3aPose(a.data, a.t);
    shift = [-tr[0] * f, a.carried ? 0 : g.min[1], -tr[1] * f];
  }
  // on his mount: the mount is posed and skinned first, and carries the rider
  const root = v3AnimMountStep(g.min[1]);
  if(root){
    pose = v3aCarry(pose, root.at, root.off, root.lift);
    shift = [0, 0, 0];
  }
  v3aSkin(g, pose, a.bind, a.map, a.pos, a.nrm, shift);
  v3AnimTwinStep(g);
  const gl = v3.gl;
  gl.bindBuffer(gl.ARRAY_BUFFER, v3.bPos);
  gl.bufferSubData(gl.ARRAY_BUFFER, 0, a.pos);
  if(a.nrm){
    gl.bindBuffer(gl.ARRAY_BUFFER, v3.bNormal);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, a.nrm);
  }
  // the scrubber follows the clock, a few times a second rather than every frame
  if(a.playing && (!a.painted || now - a.painted > 200)){
    a.painted = now;
    const r = document.getElementById('v3atime');
    if(r) r.value = v3AnimFrac();
    const c = document.getElementById('v3aclock');
    if(c) c.textContent = v3AnimClock();
  }
}

/* --- the mount and the twin (80b) -----------------------------------------
   Both are drawn by viewer3d.js's v3DrawExtra; this keeps them. The mount is
   its own model with its own skin and skeleton, playing the rider's slot. The
   twin is this model posed by another mod's action for the same skeleton and
   slot, standing to its right. */

function v3AnimExtras(){
  const a = v3 && v3.anim;
  if(!a || !a.data) return [];
  const out = [];
  const m = a.mount;
  if(m && m.on && m.x && m.x.pos && m.data) out.push(m.x);
  const t = a.twin;
  if(t && t.x && t.x.pos && t.data && !a.seqOn && !(m && m.on)) out.push(t.x);
  return out;
}

function v3AnimMountHtml(set){
  const a = v3.anim, m = a.mount;
  if(!m || v3.cas) return '';
  if(m.err) return `<div class="w-bad">The mounts: ${esc(m.err)}</div>`;
  if(!m.list) return '<div class="count">Finding its mounts…</div>';
  const rows = m.list.mounts || [];
  if(!rows.length) return `<div class="count">No mount in descr_mount.txt is a ${esc((m.list.classes || []).join(' or '))} with a model in the modeldb, so it cannot be shown mounted.</div>`;
  const opts = rows.map((r, n) => `<option value="${n}" ${n === m.pick ? 'selected' : ''}>${esc(r.type)} · ${
    esc(r.entry)}${r.units.length ? ` · ridden by ${r.units.length} unit${r.units.length === 1 ? '' : 's'}` : ''}</option>`).join('');
  const r = rows[m.pick] || rows[0];
  const said = [];
  if(m.on && m.state === 'loading') said.push('reading the mount…');
  if(m.on && m.data && m.row) said.push(m.same ? `the mount plays its own ${esc(m.row.action)}`
    : `the mount has no ${esc((v3AnimRow(a.key) || {}).action || 'such action')}, so it plays its ${esc(m.row.action)}`);
  if(m.on && m.note) said.push(esc(m.note));
  if(m.on && r && !r.offset_given) said.push('its descr_mount.txt block gives no rider_offset, so the rider sits on its root bone');
  return `<label class="count" title="The mount plays the same slot and carries the rider on its root bone, at descr_mount.txt's rider_offset"><input type="checkbox" ${
      m.on ? 'checked' : ''} onchange="v3AnimMountOn(this.checked)"> on his mount</label>
    ${m.on ? `<label class="v3f"><span>Mount</span><select onchange="v3AnimMountPick(this.value)">${opts}</select></label>
      <div class="count">rider at ${(r.offset || [0, 0, 0]).map(v => (+v).toFixed(2)).join(', ')} from its root bone${
        said.length ? ' · ' + said.join(' · ') : ''}</div>` : ''}`;
}

function v3AnimMountOn(on){
  const a = v3 && v3.anim, m = a && a.mount;
  if(!m) return;
  m.on = !!on;
  if(m.on && !m.x) return v3AnimMountLoad();
  a.dirty = true;
  if(!m.on) v3AnimFrameBack();
  v3AnimPanel();
}
function v3AnimMountPick(v){
  const m = v3 && v3.anim && v3.anim.mount;
  if(!m) return;
  m.pick = +v || 0;
  m.x = null; m.data = null;
  v3AnimMountLoad();
}

/* The mount's model, first LOD on disk, first skin the mod ships, and its
   skeleton's actions. */
async function v3AnimMountLoad(){
  const a = v3.anim, m = a.mount, mine = v3;
  const r = ((m.list || {}).mounts || [])[m.pick];
  if(!r) return;
  m.state = 'loading'; m.note = ''; v3AnimPanel();
  let info, geo, list;
  try{
    info = await api.get(`/api/model?mod=${enc(v3.mod)}&entry=${enc(r.entry)}`);
    if(info.error) throw new Error(info.error);
    const lod = (info.lods.find(l => l.exists) || {index: 0}).index;
    const res = await fetch(`/api/model/geometry?mod=${enc(v3.mod)}&entry=${enc(r.entry)}&lod=${lod}`);
    if(!res.ok){ let msg = `the server answered ${res.status}`; try{ msg = (await res.json()).error || msg; }catch(e){} throw new Error(msg); }
    geo = v3Parse(await res.arrayBuffer());
    list = await api.get(`/api/model/anims?mod=${enc(v3.mod)}&entry=${enc(r.entry)}`);
  }catch(e){
    if(v3 !== mine) return;
    m.state = ''; m.err = `${r.entry}: ${e.message || e}`; return v3AnimPanel();
  }
  if(v3 !== mine || a.mount !== m) return;
  if(!geo.skinned){ m.state = ''; m.note = `${r.entry} is not a skinned model`; return v3AnimPanel(); }
  // one variant a part, the stances a model does not wear at once left off
  const parts = new Map();
  geo.groups.forEach((g, idx) => { const k = (g.name || '').toLowerCase(); if(!parts.has(k)) parts.set(k, idx); });
  const groups = [...parts.entries()].filter(([k]) => !v3SlotHidden(k)).map(([, idx]) => idx);
  const skin = (info.skins || []).find(s => s.exists) || null;
  m.x = {geo, info, list, groups, entry: r.entry, uScale: skin && skin.attach ? 1.0 : 0.5,
         pos: new Float32Array(geo.vertices * 3), nrm: geo.normals ? new Float32Array(geo.vertices * 3) : null};
  m.skel = r.skeleton || (((list.sets || [])[0] || {}).primary || '');
  if(skin) v3AnimExtraSkin(m.x, skin, mine);
  m.state = '';
  await v3AnimMountAction();
  v3AnimFrameMounted();
}

/* A mount's sheets, glued as the model's are (v3Apply's rule for u). */
function v3AnimExtraSkin(x, skin, mine){
  const load = rel => new Promise(res => {
    if(!rel) return res(null);
    const img = new Image();
    img.onload = () => res(v3Degenerate(img) ? null : img);
    img.onerror = () => res(null);
    img.src = v3TexUrl(rel);
  });
  const same = skin.attach && skin.rel && skin.attach.toLowerCase() === skin.rel.toLowerCase();
  Promise.all([load(skin.rel), load(skin.attach_exists && !same ? skin.attach : '')]).then(([main, att]) => {
    if(v3 !== mine || !main) return;
    x.img = main; x.imgAtt = att;
    // glued, or one sheet over the two units: halved; named and not glued: full
    x.uScale = att ? 0.5 : (skin.attach ? 1.0 : 0.5);
    if(v3.anim) v3.anim.dirty = true;
  });
}

/* The mount's action for the rider's (or, in a sequence, one for each). */
async function v3AnimMountAction(){
  const a = v3 && v3.anim, m = a && a.mount;
  if(!m || !m.on || !m.x || !a.data) return;
  const mine = v3;
  const sk = (m.x.list.skeletons || {})[(m.skel || '').toLowerCase()];
  if(!sk || !sk.actions){ m.data = null; m.note = `${m.skel || 'its skeleton'} is not in the skeleton pack`; return v3AnimPanel(); }
  const rows = a.seqOn ? a.seq : [v3AnimRow(a.key)];
  const picks = rows.map(r => v3aMountRow(sk.actions, r ? r.slot : null));
  if(picks.some(p => !p.row)){ m.data = null; m.note = 'the mount has no action to play'; return v3AnimPanel(); }
  const got = [];
  for(const p of picks){
    const d = await v3AnimFetch(p.row, v3.mod, m.skel, []);
    if(v3 !== mine) return;
    if(d.error){ m.data = null; m.note = d.error; return v3AnimPanel(); }
    got.push(d);
  }
  m.row = picks[0].row; m.same = picks.every(p => p.same);
  m.data = got[0]; m.seqData = a.seqOn ? got : null;
  m.bind = v3aBind(got[0]);
  m.travel = a.seqOn ? null : v3aTravel(got[0]);
  const bm = v3aBoneMap(m.x.geo.bones, got[0]);
  m.map = bm.map;
  m.hub = got[0].bones.findIndex(b => b.parent === 0);
  a.dirty = true;
  v3AnimPanel();
}

/* Pose and skin the mount at the rider's clock, and hand back its root bone's
   world place for the rider to be carried by. */
function v3AnimMountStep(ground){
  const a = v3.anim, m = a.mount;
  if(!m || !m.on || !m.x || !m.data || m.hub < 0) return null;
  let pose, lift;
  if(a.seqOn && m.seqData){
    pose = v3aPoseOf(m.data.bones, v3aSeqSample(m.seqData, a.t, a.overlap ? V3A_BLEND : 0));
    lift = [0, ground, 0];
  }else{
    const t = m.data.times || [], len = t.length ? t[t.length - 1] : 0;
    const f = len > 0 ? ((a.t % len) + len) % len / len : 0;
    const tr = m.travel || [0, 0];
    pose = v3aPose(m.data, a.t);
    lift = [-tr[0] * f, ground, -tr[1] * f];
  }
  v3aSkin(m.x.geo, pose, m.bind, m.map, m.x.pos, m.x.nrm, lift);
  v3ExtraUpload(m.x);
  const r = ((m.list || {}).mounts || [])[m.pick] || {};
  return {at: pose[m.hub], off: r.offset || [0, 0, 0], lift};
}

/* Mounted, the scene is a horse and a man on it: frame the two. */
function v3AnimFrameMounted(){
  const m = v3.anim.mount;
  if(!m || !m.x || m.framed) return;
  const g = v3.geo, h = m.x.geo;
  const tall = (h.max[1] - h.min[1]) + (g.max[1] - g.min[1]) * 0.6;
  const long = h.max[2] - h.min[2];
  v3.centre = [0, g.min[1] + tall / 2, (h.max[2] + h.min[2]) / 2];
  v3.dist = Math.max(tall, long / 2) * 1.2;
  m.framed = true;
}
function v3AnimFrameBack(){
  const m = v3.anim.mount;
  if(m) m.framed = false;
  const t = v3.anim.twin;
  if(t) t.framed = 0;
  v3Frame();
}

/* Side by side: the mods to set against this one. */
function v3AnimTwinHtml(){
  const a = v3.anim;
  const mods = (state.mods || []).filter(x => !x.pack && x.name !== v3.mod);
  if(!mods.length) return '';
  const t = a.twin || {};
  const opts = `<option value="">nothing beside it</option>` + mods.map(x =>
    `<option value="${esc(x.name)}" ${x.name === t.mod ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
  let said = '';
  if(t.mod){
    const c = t.cmp;
    if(a.mount && a.mount.on) said = 'Taken off while the rider is on his mount.';
    else if(a.seqOn) said = 'Not shown while a sequence plays.';
    else if(!a.key) said = 'Pick an action to see it in both.';
    else if(t.err) said = esc(t.err);
    else if(!c) said = 'reading…';
    else if(!c.has_skeleton) said = `${esc(t.mod)}’s skeleton pack has no <code>${esc(c.skeleton)}</code>: a port would have to bring it.`;
    else if(!c.has_slot) said = `${esc(t.mod)}’s <code>${esc(c.skeleton)}</code> leaves ${esc(c.action)} empty.`;
    else said = `On the right, ${esc(t.mod)}${c.packs === 'vanilla' ? ' (vanilla’s packs)' : ''}: `
      + (c.same_bytes ? 'the same animation, byte for byte' + (c.same_path ? '' : `, under <code>${esc(c.path)}</code>`)
         : `a different animation, <code>${esc(c.path)}</code>`)
      + (c.frames ? `, ${c.frames} f · ${(+c.duration).toFixed(2)} s` : '')
      + (c.same_bones ? '' : '; its skeleton’s bones differ from this one’s') + '.'
      + (!c.same_bytes && c.playable && a.slot != null && v3AnimPackable(v3AnimRow(a.key))
         ? ` <button onclick="v3AnimTwinTake()" title="Put ${esc(t.mod)}’s animation in this slot of this mod’s pack">Use it here</button>` : '');
  }
  return `<label class="v3f" title="The same skeleton and slot out of another mod, drawn to the right of this one"><span>Beside it</span>
    <select onchange="v3AnimTwinMod(this.value)">${opts}</select></label>${said ? `<div class="count">${said}</div>` : ''}`;
}

function v3AnimTwinMod(mod){
  const a = v3 && v3.anim;
  if(!a) return;
  a.twin = mod ? {mod, cmp: null, data: null, x: null, err: '', framed: 0} : null;
  if(!mod){ v3AnimFrameBack(); return v3AnimPanel(); }
  v3AnimTwinAction();
}

/* The other mod's take on the action being played. */
async function v3AnimTwinAction(){
  const a = v3 && v3.anim, t = a && a.twin;
  if(!t) return;
  t.cmp = null; t.data = null; t.err = '';
  const row = v3AnimRow(a.key);
  if(!row || row.slot == null || a.seqOn){ v3AnimPanel(); return; }
  const mine = v3, key = a.key;
  let c;
  try{ c = await api.get(`/api/model/compare?mod=${enc(v3.mod)}&other=${enc(t.mod)}&skel=${enc(a.skel)}&slot=${row.slot}`); }
  catch(e){ c = {error: '' + e}; }
  if(v3 !== mine || a.twin !== t || a.key !== key) return;
  if(c.error){ t.err = c.error; return v3AnimPanel(); }
  t.cmp = c;
  if(c.has_slot && c.playable){
    const d = await v3AnimFetch({path: c.path, slot: row.slot}, t.mod, a.skel);
    if(v3 !== mine || a.twin !== t || a.key !== key) return;
    if(d.error) t.err = d.error;
    else{
      t.data = d;
      t.bind = v3aBind(d);
      t.travel = v3aTravel(d);
      t.carried = v3aCarried(d);
      t.geo = null;
      v3AnimTwinPlace();
    }
  }
  a.dirty = true;
  v3AnimPanel();
}

/* To the right of the model, clear of its widest reach, and the camera moved
   to look between the two. */
function v3AnimTwinPlace(){
  const t = v3.anim.twin, g = v3.geo;
  const gap = Math.max(1.0, (g.max[0] - g.min[0]) + 0.3);
  if(!t.x) t.x = {geo: g, shared: true, pos: null, nrm: null};
  t.x.world = [gap, 0, 0];
  if(t.framed !== gap){
    v3.centre[0] += (gap - (t.framed || 0)) / 2;
    v3.dist = Math.max(v3.dist, gap * 1.3);
    t.framed = gap;
  }
}

function v3AnimTwinStep(g){
  const a = v3.anim, t = a.twin;
  if(!t || !t.data || a.seqOn || (a.mount && a.mount.on)) return;
  if(t.geo !== g){
    t.map = v3aBoneMap(g.bones, t.data).map;
    t.x = {geo: g, shared: true, world: t.x ? t.x.world : [0, 0, 0],
           pos: new Float32Array(g.vertices * 3), nrm: g.normals ? new Float32Array(g.vertices * 3) : null};
    t.geo = g;
    v3AnimTwinPlace();
  }
  const d = t.data.times || [], len = d.length ? d[d.length - 1] : 0;
  const f = len > 0 ? ((a.t % len) + len) % len / len : 0;
  const tr = t.travel || [0, 0];
  v3aSkin(g, v3aPose(t.data, a.t), t.bind, t.map, t.x.pos, t.x.nrm,
          [-tr[0] * f, t.carried ? 0 : g.min[1], -tr[1] * f]);
  v3ExtraUpload(t.x);
}

/* Back to the model as modelled: the bind pose, straight from the file. */
function v3AnimRest(){
  if(!v3 || !v3.gl || !v3.geo) return;
  const gl = v3.gl, g = v3.geo;
  gl.bindBuffer(gl.ARRAY_BUFFER, v3.bPos);
  gl.bufferSubData(gl.ARRAY_BUFFER, 0, g.positions);
  if(g.normals){
    gl.bindBuffer(gl.ARRAY_BUFFER, v3.bNormal);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, g.normals);
  }
  if(v3.anim) v3.anim.geo = null;
}


/* --- the editor (57a) ------------------------------------------------------
   M16's editor half. Every edit is sent to the server, which applies it to the
   file's own keys (animedit.apply_edits) and hands back keys to play - so what
   plays here is what Save writes, and there is one implementation of each edit.
   The bind stays the unedited file's: the model was built on that skeleton. */

/* 86: whether an edit to this action can be saved into the mod's own pack -
   a slot of a packed skeleton, in a mod that ships packs of its own. */
function v3AnimPackable(row){
  const L = v3 && v3.anim && v3.anim.list, sk = v3AnimSk();
  return !!(row && row.slot != null && sk && sk.packed && L && L.packs && L.packs !== 'vanilla');
}

function v3AnimEditNew(data, row){
  const keys = (data.times || []).length;
  const name = (row.rel || '').replace(/\.cas$/i, '');
  const packable = v3AnimPackable(row);
  const base = (row.path || row.rel || 'action').replace(/^.*[\\/]/, '').replace(/\.cas$/i, '');
  return {open: false, speed: 1, trim: [0, Math.max(0, keys - 1)], in_place: false,
          scale: [1, 1, 1], offsets: {}, keys: [], bone: '', turn: [0, 0, 0],
          saveAs: name + '_edited.cas', packName: base + '_edited', packable,
          target: packable ? 'pack' : 'loose', keep: true,
          assign: false, busy: false, msg: '', bad: false};
}

/* The edits as animedit takes them, leaving out whatever is at its default. */
function v3AnimEdits(){
  const e = v3.anim.edit, keys = (v3.anim.orig.times || []).length, out = {};
  if(e.trim[0] > 0 || e.trim[1] < keys - 1) out.trim = e.trim.slice();
  if(+e.speed !== 1) out.speed = +e.speed;
  if(e.in_place) out.in_place = true;
  if(e.scale.some(v => +v !== 1)) out.scale = e.scale.map(Number);
  const offs = Object.entries(e.offsets).filter(([, d]) => d.some(v => +v));
  if(offs.length) out.offsets = offs.map(([bone, euler]) => ({bone, euler: euler.map(Number)}));
  if(e.keys.length) out.keys = e.keys.slice();
  return out;
}

function v3AnimEditCount(){
  const o = v3AnimEdits();
  return Object.values(o).reduce((n, v) => n + (Array.isArray(v) && typeof v[0] === 'object' ? v.length : 1), 0);
}

/* The key under the scrubber, in the file's own numbering. */
function v3AnimKeyNow(){
  const a = v3.anim, t = a.data.times, len = v3AnimLength();
  if(!t || t.length < 2 || len <= 0) return 0;
  const now = ((a.t % len) + len) % len;
  let k = 0;
  for(let i = 0; i < t.length; i++) if(Math.abs(t[i] - now) < Math.abs(t[k] - now)) k = i;
  return k;
}

function v3AnimEditHtml(){
  const a = v3.anim, e = a.edit;
  if(!e) return '';
  const n = v3AnimEditCount(), keys = (a.orig.times || []).length;
  const head = `<button class="v3aedbtn ${e.open ? 'on' : ''}" onclick="v3AnimEditFold()">✎ Edit this action${
    n ? ` · ${n} edit${n === 1 ? '' : 's'}` : ''}</button>`;
  if(!e.open) return `<div class="v3btns">${head}</div>`;
  const bones = a.orig.bones.map(b => b.name).filter(x => !/^scene root$/i.test(x));
  const bone = e.bone || bones[0] || '';
  const bi = a.data.bones.findIndex(b => b.name === bone);
  const k = v3AnimKeyNow();
  const eul = bi >= 0 ? ((a.data.bones[bi].euler || [])[Math.min(k, (a.data.bones[bi].euler || []).length - 1)]
                         || [0, 0, 0]) : [0, 0, 0];
  const num = (val, on, step, w) => `<input type="number" step="${step}" value="${val}"
    style="width:${w || 58}px" onchange="${on}">`;
  const turn = e.offsets[bone] || [0, 0, 0];
  return `<div class="v3btns">${head}</div>
  <div class="v3aed">
    <div class="v3aedrow"><span>Keep keys</span>${num(e.trim[0], "v3AnimEditSet('trim0', this.value)", 1)}
      to ${num(e.trim[1], "v3AnimEditSet('trim1', this.value)", 1)}
      <span class="count">of 0 to ${keys - 1}</span></div>
    <div class="v3aedrow"><span>Speed</span>${num(e.speed, "v3AnimEditSet('speed', this.value)", 0.05)}
      <label><input type="checkbox" ${e.in_place ? 'checked' : ''} onchange="v3AnimEditSet('in_place', this.checked)">
        in place</label></div>
    <div class="v3aedrow" title="Every pivot and position key, per axis - for a skeleton taller or shorter than the one the action was made on"><span>Scale</span>
      ${[0, 1, 2].map(i => num(e.scale[i], `v3AnimEditSet('scale${i}', this.value)`, 0.01, 52)).join('')}</div>
    <div class="v3aedrow"><span>Bone</span><select onchange="v3AnimEditSet('bone', this.value)">${
      bones.map(b => `<option ${b === bone ? 'selected' : ''}>${esc(b)}</option>`).join('')}</select></div>
    <div class="v3aedrow" title="Degrees about the bone's own X, Y and Z, added at every key"><span>Turn, every key</span>
      ${[0, 1, 2].map(i => num(turn[i], `v3AnimEditTurn(${i}, this.value)`, 1, 52)).join('')}°</div>
    <div class="v3aedrow" title="Scrub to a key, then set this bone's rotation there outright"><span>At key ${k}</span>
      ${[0, 1, 2].map(i => `<input type="number" step="1" id="v3aek${i}" value="${(+eul[i]).toFixed(1)}" style="width:52px">`).join('')}°
      <button onclick="v3AnimEditKey()">Set</button></div>
    ${e.packable && a.rel ? `<div class="v3aedrow"><span>Save</span><select onchange="v3AnimEditSet('target', this.value)">
      <option value="pack" ${e.target === 'pack' ? 'selected' : ''}>into the pack</option>
      <option value="loose" ${e.target === 'loose' ? 'selected' : ''}>as a loose file</option></select></div>` : ''}
    ${e.target === 'pack' ? `<div class="v3aedrow"><span>Name</span><input type="text" value="${esc(e.packName)}" style="flex:1;min-width:0"
      onchange="v3AnimEditSet('packName', this.value)" spellcheck="false"><span class="count">.cas</span></div>
    <label class="count" title="The new animation also written loose, and descr_skeleton.txt's line pointed at it, so a rebuild of the packs keeps it">
      <input type="checkbox" ${e.keep ? 'checked' : ''} onchange="v3AnimEditSet('keep', this.checked)"> keep the mod rebuildable</label>`
    : `<div class="v3aedrow"><span>Save as</span><input type="text" value="${esc(e.saveAs)}" style="flex:1;min-width:0"
      onchange="v3AnimEditSet('saveAs', this.value)" spellcheck="false"></div>
    <label class="count"><input type="checkbox" ${e.assign ? 'checked' : ''} onchange="v3AnimEditSet('assign', this.checked)">
      Make it this skeleton's <b>${esc((v3AnimRow(a.key) || {}).action || '')}</b> in descr_skeleton.txt</label>`}
    <div class="v3btns"><button onclick="v3AnimEditReset()" ${n || a.data !== a.orig ? '' : 'disabled'}>Reset</button>
      <button class="primary" onclick="v3AnimEditSave()" ${e.busy ? 'disabled' : ''}>Save…</button></div>
    ${e.msg ? `<div class="${e.bad ? 'w-bad' : 'count'}">${esc(e.msg)}</div>` : ''}
    <div class="count">${e.target === 'pack'
      ? `Saved into <code>animations/pack.dat</code> under a new name, and <code>${esc(a.skel)}</code>’s slot pointed there, so the game plays it: every model on this skeleton.`
      : e.packable
      ? `The game plays this action from <code>animations/pack.dat</code>, and a loose file does not override a packed one: a loose save reaches the game only if the packs are removed and rebuilt.`
      : `This mod plays vanilla’s packs, so a loose file reaches the game only when packs of its own are built.`}</div>
  </div>`;
}

function v3AnimEditFold(){
  const e = v3 && v3.anim && v3.anim.edit;
  if(!e) return;
  e.open = !e.open;
  if(e.open) v3.anim.playing = false;       // editing is done on a still frame
  v3AnimPanel();
}

function v3AnimEditSet(key, value){
  const e = v3.anim.edit;
  const keys = (v3.anim.orig.times || []).length;
  if(key === 'trim0') e.trim[0] = Math.max(0, Math.min(+value | 0, e.trim[1] - 1));
  else if(key === 'trim1') e.trim[1] = Math.max(e.trim[0] + 1, Math.min(+value | 0, keys - 1));
  else if(key.startsWith('scale')) e.scale[+key.slice(5)] = +value || 1;
  else if(key === 'speed') e.speed = Math.max(0.05, Math.min(20, +value || 1));
  else e[key] = value;
  if(['bone', 'saveAs', 'assign', 'target', 'packName', 'keep'].includes(key)) return v3AnimPanel();
  v3AnimEditPreview();
}

function v3AnimEditTurn(i, value){
  const e = v3.anim.edit;
  const bone = e.bone || v3.anim.orig.bones.map(b => b.name).find(x => !/^scene root$/i.test(x));
  const d = (e.offsets[bone] || [0, 0, 0]).slice();
  d[i] = +value || 0;
  e.offsets[bone] = d;
  v3AnimEditPreview();
}

/* Set the chosen bone's rotation at the key under the scrubber. The key is the
   EDITED animation's key once a trim has run, so a key set is always stated in
   the numbering the file had when it was opened, which is what the server
   applies it to - trims come first there. */
function v3AnimEditKey(){
  const a = v3.anim, e = a.edit;
  const bone = e.bone || a.orig.bones.map(b => b.name).find(x => !/^scene root$/i.test(x));
  const k = v3AnimKeyNow() + (e.trim[0] || 0);
  const euler = [0, 1, 2].map(i => +(document.getElementById('v3aek' + i) || {}).value || 0);
  e.keys = e.keys.filter(x => !(x.bone === bone && x.key === k)).concat([{bone, key: k, euler}]);
  v3AnimEditPreview();
}

async function v3AnimEditPreview(){
  const a = v3.anim, e = a.edit, mine = v3;
  e.busy = true; e.msg = ''; e.bad = false;
  let data;
  try{
    data = a.rel ? await api.post('/api/model/anim/preview', {mod: v3.mod, rel: a.rel, edits: v3AnimEdits(),
                                                              skeleton: a.skel || ''})
      // 86: the bytes a save into the pack would write, read back
      : await api.post('/api/model/anim/pack_preview', {mod: v3.mod, skeleton: a.skel, slot: a.slot,
                                                        edits: v3AnimEdits(), weapons: v3AnimWeapons()});
  }
  catch(err){ data = {error: '' + err}; }
  if(v3 !== mine || v3.anim !== a) return;
  e.busy = false;
  if(data.error){ e.msg = data.error; e.bad = true; return v3AnimPanel(); }
  a.data = data;
  a.travel = v3aTravel(data);
  a.dirty = true;
  v3AnimPanel();
}

function v3AnimEditReset(){
  const a = v3.anim;
  const open = a.edit.open;
  a.edit = v3AnimEditNew(a.orig, {rel: a.rel});
  a.edit.open = open;
  a.data = a.orig;
  a.travel = v3aTravel(a.orig);
  a.dirty = true;
  v3AnimPanel();
}

async function v3AnimEditSave(){
  const a = v3.anim, e = a.edit;
  if(e.target === 'pack') return v3AnimPackSave();
  const act = (v3AnimRow(a.key) || {}).action || '';
  const body = {mod: v3.mod, rel: a.rel, edits: v3AnimEdits(), save_as: e.saveAs,
                skeleton: a.skel || '',
                assign: e.assign && a.skel && !act.includes(' / ') ? {skeleton: a.skel, action: act} : null};
  let r;
  try{ r = await api.post('/api/model/anim/save_plan', body); }
  catch(err){ r = {error: '' + err}; }
  const p = r.plan;
  if(r.error || !p || !p.ok){ e.msg = r.error || 'nothing to save'; e.bad = true; return v3AnimPanel(); }
  if(!confirm(`Save ${p.target}?\n\n`
    + (p.overwrites ? '  It replaces the file of that name; the old one is backed up.\n' : '  A new file.\n')
    + (p.notes || []).map(n => '  ' + n).join('\n\n')
    + '\n\n🕑 Log undoes it.')) return;
  e.busy = true; v3AnimPanel();
  let w;
  try{ w = await api.post('/api/model/anim/save_apply', body); }
  catch(err){ w = {error: '' + err}; }
  e.busy = false;
  if(w.error){ e.msg = w.error; e.bad = true; return v3AnimPanel(); }
  e.msg = `Saved ${w.target}. 🕑 Log can undo it.`;
  if(typeof activity === 'function') activity('saved animation', `${w.target} in ${v3.mod}`);
  // the saved file is loose now, and it may be this action's: ask again
  a.list = null;
  const keep = a;
  await v3AnimInit();
  if(v3 && v3.anim === keep) v3AnimPanel();
}


/* --- saving into the pack (86) ----------------------------------------------
   An edit, or another mod's take on the slot, appended to this mod's pack.dat
   under a new name and the skeleton's slot pointed there: the game plays the
   first of two entries with one name, so neither can go under the old one. */

function v3AnimPackMsg(p){
  return (p.reuse ? `  The pack holds these bytes already, as ${p.new_path}: the slot is pointed there.\n`
                  : `  Appended to pack.dat as ${p.new_path} (${(p.bytes / 1024).toFixed(0)} KB, ${p.frames} frames).\n`)
    + `  ${p.skeleton}’s ${p.action} is pointed at it, for every model on that skeleton.\n`
    + (p.loose ? `  Kept rebuildable: ${p.loose}${p.descr_skeleton ? ', and descr_skeleton.txt’s line' : ''}.\n` : '')
    + (p.notes || []).map(n => '  ' + n).join('\n');
}

async function v3AnimPackAfter(w, what){
  if(typeof activity === 'function') activity(what, w.summary);
  const a = v3.anim, key = a.key;
  a.list = null;
  await v3AnimInit();
  if(v3 && v3.anim === a && key) await v3AnimPick(key);
}

async function v3AnimPackSave(){
  const a = v3.anim, e = a.edit;
  const body = {mod: v3.mod, skeleton: a.skel, slot: a.slot, edits: v3AnimEdits(), name: e.packName,
                rel: a.rel || '', keep_rebuildable: e.keep};
  let r;
  try{ r = await api.post('/api/model/anim/pack_plan', body); }
  catch(err){ r = {error: '' + err}; }
  const p = r.plan;
  if(r.error || !p || !p.ok){ e.msg = r.error || 'nothing to save'; e.bad = true; return v3AnimPanel(); }
  if(!confirm(`Save this edit into ${v3.mod}’s pack?\n\n${v3AnimPackMsg(p)}\n\nClose the game first. 🕑 Log undoes it.`)) return;
  e.busy = true; v3AnimPanel();
  let w;
  try{ w = await api.post('/api/model/anim/pack_apply', body); }
  catch(err){ w = {error: '' + err}; }
  e.busy = false;
  if(w.error){ e.msg = w.error; e.bad = true; return v3AnimPanel(); }
  await v3AnimPackAfter(w, 'saved an animation into the pack');
  if(v3 && v3.anim && v3.anim.edit){ v3.anim.edit.msg = `Saved as ${w.new_path}. 🕑 Log can undo it.`; v3AnimPanel(); }
}

/* The other mod's take on this slot, played here from now on. */
async function v3AnimTwinTake(){
  const a = v3 && v3.anim, t = a && a.twin;
  if(!t || a.slot == null) return;
  const body = {mod: v3.mod, skeleton: a.skel, slot: a.slot, source: t.mod, source_skeleton: a.skel,
                keep_rebuildable: true};
  let r;
  try{ r = await api.post('/api/model/anim/bring_plan', body); }
  catch(err){ r = {error: '' + err}; }
  const p = r.plan;
  if(r.error || !p || !p.ok){ t.err = r.error || 'nothing to bring'; return v3AnimPanel(); }
  if(!confirm(`Play ${t.mod}’s ${p.action} in ${v3.mod}?\n\n  From ${p.source}.\n${v3AnimPackMsg(p)}\n\nClose the game first. 🕑 Log undoes it.`)) return;
  let w;
  try{ w = await api.post('/api/model/anim/bring_apply', body); }
  catch(err){ w = {error: '' + err}; }
  if(w.error){ t.err = w.error; return v3AnimPanel(); }
  await v3AnimPackAfter(w, 'brought an animation');
}

/* A skeleton from another mod's pack, with every animation it plays. */
function v3AnimPortHtml(){
  const a = v3.anim, L = a.list;
  if(!L || !L.packs || L.packs === 'vanilla') return '';
  const f = a.port;
  if(!f) return `<div class="v3btns"><button onclick="v3AnimPortOpen()" title="A skeleton and every animation it plays, from another mod's pack into this mod's">Bring a skeleton from another mod…</button></div>`;
  const mods = (state.mods || []).filter(x => !x.pack && x.name !== v3.mod);
  const p = f.plan;
  const bodies = v3.cas ? [] : [...new Set(((L.sets || []).flatMap(x => [x.primary, x.secondary])).filter(Boolean))];
  const t = p && p.port ? p.port.totals : null;
  return `<div class="v3aed">
    <div class="v3aedrow"><span>From</span><select onchange="v3AnimPortSet('mod', this.value)">
      <option value="">pick a mod</option>${mods.map(x => `<option ${x.name === f.mod ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select></div>
    <div class="v3aedrow"><span>Skeleton</span><input type="text" list="v3aportnames" value="${esc(f.name)}" style="flex:1;min-width:0"
      onchange="v3AnimPortSet('name', this.value)" spellcheck="false" placeholder="${f.names ? f.names.length + ' in its pack' : ''}">
      <datalist id="v3aportnames">${(f.names || []).map(n => `<option value="${esc(n)}">`).join('')}</datalist></div>
    ${bodies.length ? `<div class="v3aedrow"><span>Then</span><select onchange="v3AnimPortSet('point', this.value)">
      <option value="">leave ${esc(v3.entry)} as it is</option>${bodies.map(n =>
        `<option value="${esc(n)}" ${n === f.point ? 'selected' : ''}>point ${esc(v3.entry)}’s ${esc(n)} at it</option>`).join('')}</select></div>` : ''}
    <div class="v3btns"><button onclick="v3.anim.port = null; v3AnimPanel()">Cancel</button>
      <button onclick="v3AnimPortPlan()" ${f.mod && f.name && !f.busy ? '' : 'disabled'}>Check</button>
      <button class="primary" onclick="v3AnimPortApply()" ${p && p.ok && !f.busy ? '' : 'disabled'}>Bring it</button></div>
    ${f.msg ? `<div class="${f.bad ? 'w-bad' : 'count'}">${esc(f.msg)}</div>` : ''}
    ${t ? `<div class="count">${esc(p.port.skeletons.map(s => `${s.name} ${s.action === 'rename' ? 'comes in as ' + s.dest_name
        : s.action === 'add' ? 'is added' : s.action === 'reuse' ? 'is here already' : 'is here as ' + s.dest_name}`).join('; '))}: ${
        t['animations append'] + t['animations append_renamed']} of ${t.animations} animations appended, ${
        ((t['anim bytes appended'] + t['skeleton bytes appended']) / 1e6).toFixed(1)} MB${
        p.loose && p.loose.files ? `; ${p.loose.files} loose file(s) kept for a rebuild` : ''}.</div>
      ${(p.notes || []).map(n => `<div class="count">${esc(n)}</div>`).join('')}` : ''}
  </div>`;
}

function v3AnimPortOpen(){
  v3.anim.port = {mod: '', name: '', point: '', names: null, plan: null, msg: '', bad: false, busy: false};
  v3AnimPanel();
}

async function v3AnimPortSet(k, v){
  const f = v3.anim.port;
  f[k] = v; f.plan = null; f.msg = ''; f.bad = false;
  if(k === 'mod'){
    f.names = null;
    if(v){
      try{ f.names = (await api.get(`/api/model/skeleton_names?mod=${enc(v)}`)).names || []; }
      catch(e){ f.msg = '' + e; f.bad = true; }
    }
  }
  v3AnimPanel();
}

function v3AnimPortBody(){
  const f = v3.anim.port;
  return {mod: v3.mod, source: f.mod, skeleton: f.name, entry: f.point ? v3.entry : '',
          entry_skeleton: f.point, keep_rebuildable: true};
}

async function v3AnimPortPlan(){
  const f = v3.anim.port;
  f.busy = true; f.msg = 'reading both packs…'; f.bad = false; v3AnimPanel();
  let r;
  try{ r = await api.post('/api/model/skeleton/port_plan', v3AnimPortBody()); }
  catch(e){ r = {error: '' + e}; }
  f.busy = false; f.msg = r.error || ''; f.bad = !!r.error; f.plan = r.plan || null;
  v3AnimPanel();
}

async function v3AnimPortApply(){
  const f = v3.anim.port;
  if(!confirm(`Bring ${f.name} from ${f.mod} into ${v3.mod}’s packs?\n\nClose the game first. 🕑 Log undoes it.`)) return;
  f.busy = true; f.msg = 'writing…'; v3AnimPanel();
  let w;
  try{ w = await api.post('/api/model/skeleton/port_apply', v3AnimPortBody()); }
  catch(e){ w = {error: '' + e}; }
  f.busy = false;
  if(w.error){ f.msg = w.error; f.bad = true; return v3AnimPanel(); }
  if(typeof activity === 'function') activity('ported a skeleton', w.summary);
  v3.anim.port = null;
  v3.anim.list = null;
  await v3AnimInit();
  if(v3 && v3.anim){ v3.anim.err = ''; }
}


/* --- export and convert (57b) ----------------------------------------------
   The model out of the game's formats: a .glb that Blender opens with its
   skeleton, skin, texture and actions, or an .obj zipped with its texture -
   both of exactly what is on screen, the parts shown and the skin chosen. And
   a converter for a .texture or .dds file from disk, which touches no mod. */

function v3ExportPanel(){
  const host = document.getElementById('v3export');
  if(!host) return;
  if(!v3 || v3.cas || !v3.geo){ host.innerHTML = ''; return; }
  const a = v3.anim, sk = a && a.list ? v3AnimSk() : null;
  const loose = sk ? (sk.actions || []).filter(r => r.rel).length : 0;
  const all = v3.exportAll !== false;
  host.innerHTML = `<div class="k">Export</div>
    <div class="v3btns">
      <button onclick="v3Export('glb')" title="glTF binary: Blender imports it with nothing installed - the parts shown, this skin, the skeleton and ${
        loose ? 'the actions' : 'no actions (none are loose)'}">⇩ .glb for Blender</button>
      <button onclick="v3Export('obj')" title="Geometry, UVs and the texture, zipped. OBJ has no skeleton">⇩ .obj + texture</button>
      <button onclick="v3ConvertPick()" title="A .texture from disk to .dds, or a .dds to .texture. Nothing in the mod is touched">Convert a file…</button>
    </div>
    ${v3.geo.skinned ? `<label class="count"><input type="checkbox" ${all ? 'checked' : ''}
      onchange="v3.exportAll = this.checked; v3ExportPanel()"> ${loose
        ? `with all ${loose} loose action${loose === 1 ? '' : 's'} of ${esc(sk.skeleton)}`
        : 'with its actions - none are loose in this mod, so the .glb carries the skeleton alone'}</label>` : ''}
    <input type="file" id="v3conv" accept=".texture,.dds" style="display:none" onchange="v3Convert(this)">`;
}

function v3Export(fmt){
  if(!v3 || !v3.geo) return;
  const q = new URLSearchParams({mod: v3.mod, entry: v3.entry, lod: v3.lod, skin: v3.skin, fmt,
                                 groups: v3Visible().join(','), hd: v3HdOn() ? '1' : '0'});
  const a = v3.anim;
  if(fmt === 'glb' && a){
    // the export's own list: the entry's body skeletons, once each, in order
    const bodies = [];
    ((a.list && a.list.sets) || []).forEach(x => [x.primary, x.secondary].forEach(n => {
      if(n && !bodies.includes(n)) bodies.push(n);
    }));
    q.set('skel', Math.max(0, bodies.indexOf(a.skel)));
    q.set('actions', v3.exportAll !== false ? '*' : ((v3AnimRow(a.key) || {}).action || ''));
  }
  const link = document.createElement('a');
  link.href = '/api/model/export?' + q.toString();
  link.download = '';
  document.body.appendChild(link); link.click(); link.remove();
  toast(fmt === 'glb' ? 'Building the .glb…' : 'Building the .obj zip…', 2500);
}

function v3ConvertPick(){ const i = document.getElementById('v3conv'); if(i){ i.value = ''; i.click(); } }

async function v3Convert(input){
  const f = input.files && input.files[0];
  if(!f) return;
  const to = /\.dds$/i.test(f.name) ? 'texture' : 'dds';
  const buf = new Uint8Array(await f.arrayBuffer());
  let bin = '';
  for(let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
  let r;
  try{ r = await api.post('/api/convert/texture', {to, data: btoa(bin)}); }
  catch(e){ r = {error: '' + e}; }
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  const raw = atob(r.data), out = new Uint8Array(raw.length);
  for(let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([out]));
  link.download = f.name.replace(/\.(texture|dds)$/i, '') + '.' + to;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
  toast(`${f.name} → ${link.download} (${(r.bytes / 1048576).toFixed(1)} MB)`, 4000);
}
