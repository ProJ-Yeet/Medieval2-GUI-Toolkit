/* v3anim.js - a battle model that moves (Phase 55b)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Loaded
   after viewer3d.js, whose `v3` state, tick loop and side panel this
   hooks into; viewer3d.js calls in here only through `typeof` guards. */
/* =========================================================================
   PLAYING A MODEL'S ANIMATIONS - the chain, then the skin.

   The chain is the server's (casanim.actions_view): a modeldb entry names its
   skeletons, descr_skeleton.txt names each skeleton's file per action, and a
   file plays only when the mod ships it loose. Most mods ship most of theirs
   in animations/pack.dat, which nothing here reads, so the picker lists every
   action and greys out the packed ones rather than pretending they are not
   there. A mod whose pack was unpacked in place (the files nested under
   animations/mods/<mod>/data/animations, still in the pack's own format) plays
   too: the server finds them and reads them with the unpacked skeleton's
   bones, which is why every request for keys carries the skeleton's name.

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

/* --- the picker ----------------------------------------------------------- */

/* Called by v3Load once a model's geometry is in: a skinned .mesh asks which
   actions its skeletons have. A .cas and a static model have none to ask for. */
async function v3AnimInit(){
  if(!v3 || v3.cas || !v3.geo || !v3.geo.skinned) return v3AnimPanel();
  if(!v3.anim) v3.anim = {list: null, skel: 0, action: '', data: null,
                          playing: true, t: 0, speed: 1, err: ''};
  if(v3.anim.list) return v3AnimPanel();
  const mine = v3;
  let list;
  try{ list = await api.get(`/api/model/anims?mod=${enc(v3.mod)}&entry=${enc(v3.entry)}`); }
  catch(e){ list = {error: ''+e}; }
  if(v3 !== mine) return;
  v3.anim.list = list;
  v3AnimPanel();
  v3ExportPanel();
}

function v3AnimPanel(){
  const host = document.getElementById('v3anim');
  if(!host) return;
  if(!v3 || v3.cas || !v3.geo || !v3.geo.skinned || !v3.anim){
    host.innerHTML = '';
    return;
  }
  const a = v3.anim, L = a.list;
  if(!L){ host.innerHTML = '<div class="k">Animation <span class="count">reading descr_skeleton.txt…</span></div>'; return; }
  if(L.error){ host.innerHTML = `<div class="k">Animation</div><div class="w-bad">${esc(L.error)}</div>`; return; }
  const sks = L.skeletons || [];
  if(!L.file || !sks.length){
    host.innerHTML = `<div class="k">Animation</div><div class="count">${
      !L.file ? 'This mod has no <code>descr_skeleton.txt</code>, so there is nothing to play.'
              : 'This entry names no skeleton.'}</div>`;
    return;
  }
  const sk = sks[a.skel] || sks[0];
  const skelSel = sks.length > 1
    ? `<label class="v3f"><span>Skeleton</span><select onchange="v3AnimSkel(this.value)">${
        sks.map((s, n) => `<option value="${n}" ${n===a.skel?'selected':''}>${esc(s.skeleton)}${
          s.found ? ` · ${s.loose} of ${s.actions.length} loose` : ' - not in descr_skeleton.txt'}</option>`).join('')
      }</select></label>` : '';
  let body;
  if(!sk.found){
    body = `<div class="w-warn">descr_skeleton.txt has no <code>${esc(sk.skeleton)}</code>, `
         + `so the game cannot animate this model either.</div>`;
  }else{
    const opts = sk.actions.map(x =>
      `<option value="${esc(x.action)}" ${x.action===a.action?'selected':''} ${x.rel?'':'disabled'}>${
        esc(x.action)}${x.rel ? '' : ' - packed'}</option>`).join('');
    body = `<label class="v3f"><span>Action</span><select onchange="v3AnimPick(this.value)" ${sk.loose?'':'disabled'}>
        <option value="" ${a.action?'':'selected'}>Still - the model as modelled</option>${opts}</select></label>`
      + (a.data ? `<div class="v3btns v3play">
          <button onclick="v3AnimPlay()" class="${a.playing?'on':''}">${a.playing?'Pause':'Play'}</button>
          <input type="range" id="v3atime" min="0" max="1000" value="${v3AnimFrac()}"
            oninput="v3AnimScrub(this.value)" title="Scrub through the action">
          <select onchange="v3AnimSpeed(this.value)" title="Playback speed">${
            [0.25, 0.5, 1, 2].map(s => `<option value="${s}" ${s===a.speed?'selected':''}>${s}×</option>`).join('')
          }</select></div>
          <div class="count" id="v3aclock">${v3AnimClock()}</div>
          ${v3AnimEditHtml()}` : '')
      + `<div class="count">${sk.loose
          ? `${sk.loose} of ${sk.actions.length} actions are loose files in this mod`
            + (sk.unpacked ? ` (${sk.unpacked === sk.loose ? 'all' : sk.unpacked} of them in an unpacked copy of the pack, `
              + `under <code>animations/mods/…</code>)` : '')
            + (sk.loose < sk.actions.length ? `; the rest are packed in <code>animations/pack.dat</code>, `
              + `which this viewer does not read.` : '.')
          : `All ${sk.actions.length} of its actions are packed in <code>animations/pack.dat</code>, `
            + `which this viewer does not read, so nothing here can play.`}</div>`;
  }
  const notes = [];
  if(a.err) notes.push(`<div class="w-bad">${esc(a.err)}</div>`);
  if(a.data && a.missing && a.missing.length)
    notes.push(`<div class="count">Not in the skeleton, so carried with the pelvis: ${
      a.missing.map(n => `<code>${esc(n)}</code>`).join(', ')}.</div>`);
  if(a.data && a.travel && Math.hypot(a.travel[0], a.travel[1]) > 0.05)
    notes.push(`<div class="count">A cycle: it carries the model ${
      Math.hypot(a.travel[0], a.travel[1]).toFixed(2)} across the ground each loop, `
      + `which is taken out here so it plays in place.</div>`);
  if(a.data && (a.data.notes || []).length)
    notes.push(a.data.notes.map(n => `<div class="w-warn">${esc(n)}</div>`).join(''));
  host.innerHTML = `<div class="k">Animation</div>${skelSel}${body}${notes.join('')}`;
}

function v3AnimSkel(v){
  if(!v3 || !v3.anim) return;
  v3.anim.skel = +v;
  v3AnimPick('');
}

async function v3AnimPick(action){
  if(!v3 || !v3.anim) return;
  const a = v3.anim;
  a.action = action; a.err = ''; a.t = 0;
  if(!action){
    a.data = null;
    v3AnimRest();
    return v3AnimPanel();
  }
  const sk = (a.list.skeletons || [])[a.skel];
  const row = sk && sk.actions.find(x => x.action === action);
  if(!row || !row.rel){ a.data = null; v3AnimRest(); return v3AnimPanel(); }
  const mine = v3;
  let data;
  try{ data = await api.get(`/api/model/anim?mod=${enc(v3.mod)}&rel=${enc(row.rel)}&skel=${enc(sk.skeleton)}`); }
  catch(e){ data = {error: ''+e}; }
  if(v3 !== mine || a.action !== action) return;
  if(data.error){ a.data = null; a.err = data.error; v3AnimRest(); return v3AnimPanel(); }
  a.data = data;
  a.orig = data;              // what the editor's Reset goes back to
  a.rel = row.rel;
  a.edit = v3AnimEditNew(data, row);
  a.bind = v3aBind(data);
  a.travel = v3aTravel(data);
  a.geo = null;               // the bone map is built against the model on the next frame
  a.last = performance.now();
  a.playing = true;
  v3AnimPanel();
}

function v3AnimPlay(){
  if(!v3 || !v3.anim) return;
  v3.anim.playing = !v3.anim.playing;
  v3.anim.last = performance.now();
  v3AnimPanel();
}
function v3AnimSpeed(v){ if(v3 && v3.anim) v3.anim.speed = +v || 1; }
function v3AnimLength(){
  const d = v3 && v3.anim && v3.anim.data;
  const t = d && d.times;
  return t && t.length ? t[t.length-1] : 0;
}
function v3AnimFrac(){
  const len = v3AnimLength();
  return len > 0 ? Math.round((v3.anim.t % len) / len * 1000) : 0;
}
function v3AnimClock(){
  const a = v3 && v3.anim, len = v3AnimLength();
  if(!a || !a.data) return '';
  const now = len > 0 ? (a.t % len) : 0;
  return `${now.toFixed(2)} s of ${len.toFixed(2)} s · ${a.data.times.length} keys · `
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
  // a cycle walks in place: its travel so far this loop is taken back out
  const len = v3AnimLength(), f = len > 0 ? ((a.t % len) + len) % len / len : 0;
  const tr = a.travel || [0, 0];
  v3aSkin(g, v3aPose(a.data, a.t), a.bind, a.map, a.pos, a.nrm,
          [-tr[0] * f, g.min[1], -tr[1] * f]);
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

function v3AnimEditNew(data, row){
  const keys = (data.times || []).length;
  const name = (row.rel || '').replace(/\.cas$/i, '');
  return {open: false, speed: 1, trim: [0, Math.max(0, keys - 1)], in_place: false,
          scale: [1, 1, 1], offsets: {}, keys: [], bone: '', turn: [0, 0, 0],
          saveAs: name + '_edited.cas', assign: false, busy: false, msg: '', bad: false};
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
    <div class="v3aedrow"><span>Save as</span><input type="text" value="${esc(e.saveAs)}" style="flex:1;min-width:0"
      onchange="v3AnimEditSet('saveAs', this.value)" spellcheck="false"></div>
    <label class="count"><input type="checkbox" ${e.assign ? 'checked' : ''} onchange="v3AnimEditSet('assign', this.checked)">
      Make it this skeleton's <b>${esc(a.action)}</b> in descr_skeleton.txt</label>
    <div class="v3btns"><button onclick="v3AnimEditReset()" ${n || a.data !== a.orig ? '' : 'disabled'}>Reset</button>
      <button class="primary" onclick="v3AnimEditSave()" ${e.busy ? 'disabled' : ''}>Save…</button></div>
    ${e.msg ? `<div class="${e.bad ? 'w-bad' : 'count'}">${esc(e.msg)}</div>` : ''}
    <div class="count">The game plays this mod's animations from <code>animations/pack.dat</code>; a saved
      file reaches it once the pack is rebuilt (xidx, in the TWCenter archive).</div>
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
  if(key === 'bone' || key === 'saveAs' || key === 'assign') return v3AnimPanel();
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
  const psk = (a.list.skeletons || [])[a.skel];
  try{ data = await api.post('/api/model/anim/preview', {mod: v3.mod, rel: a.rel, edits: v3AnimEdits(),
                                                        skeleton: psk ? psk.skeleton : ''}); }
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
  const sk = (a.list.skeletons || [])[a.skel];
  const body = {mod: v3.mod, rel: a.rel, edits: v3AnimEdits(), save_as: e.saveAs,
                skeleton: sk ? sk.skeleton : '',
                assign: e.assign && sk ? {skeleton: sk.skeleton, action: a.action} : null};
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


/* --- export and convert (57b) ----------------------------------------------
   The model out of the game's formats: a .glb that Blender opens with its
   skeleton, skin, texture and actions, or an .obj zipped with its texture -
   both of exactly what is on screen, the parts shown and the skin chosen. And
   a converter for a .texture or .dds file from disk, which touches no mod. */

function v3ExportPanel(){
  const host = document.getElementById('v3export');
  if(!host) return;
  if(!v3 || v3.cas || !v3.geo){ host.innerHTML = ''; return; }
  const a = v3.anim, sk = a && a.list && (a.list.skeletons || [])[a.skel];
  const loose = sk && sk.found ? sk.loose : 0;
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
    q.set('skel', a.skel || 0);
    q.set('actions', v3.exportAll !== false ? '*' : (a.action || ''));
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
