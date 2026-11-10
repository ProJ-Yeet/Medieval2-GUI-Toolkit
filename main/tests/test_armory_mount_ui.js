// "Horses are broken in unit card maker" (2026-11-10). A cavalry project in
// Armory Studio holds two models, the rider and his horse, and was posed by
// one skeleton: posed by the rider's, every horse bone was missing from it and
// went with the rider's pelvis, so the horse stood in its bind pose and the
// rider sat at its root without descr_mount.txt's rider_offset, behind the
// saddle. The game poses the horse by its own skeleton and carries the rider
// at its root bone (bone_H_Saddle) plus rider_offset, as the Models viewer
// does (v3aCarry, 80b). The card maker's Riding pose also picked the horse's
// skeleton, and "One of each part" kept one Body for rider and horse together.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const js = f => fs.readFileSync(path.join(__dirname, '..', 'web', 'js', f), 'utf8');
const pick = (src, re) => { const m = src.match(re); assert(m, 'not found: ' + re); return m[0]; };

const H = {kind: 'entry', mod: 'M', entry: 'mount_h'}, R = {kind: 'entry', mod: 'M', entry: 'rider', unit: 'Knights'};
// one triangle each, every vertex on its root bone: the horse's saddle point
// at the origin with its hooves 1.9 below, the rider's pelvis at the origin
const tri = (verts, bone) => ({geo: {positions: verts.flat(), normals: null, uvs: null,
  weights: [1, 0, 1, 0, 1, 0], joints: [0, 0, 0, 0, 0, 0], bones: [bone],
  indices: [0, 1, 2], groups: [{start: 0, count: 3}]}});
const oH = {id: 'h', name: 'Body', src: [{asset: 'M|mount_h', group: 0}]};
const oR = {id: 'r', name: 'Body', src: [{asset: 'M|rider', group: 0}]};
// a helmet with no weights: it stands still on a man on foot, but rides with him
const oHelm = {id: 'm', name: 'Helmet', src: [{asset: 'M|rider', group: 1}]};
const project = {assets: [H, R], objects: [oH, oR, oHelm]};
const bone = (name, parent, pos) => ({name, parent, pivot: [0, 0, 0], pos: [pos], rot: []});
const lists = {
  rider: {sets: [{mount: 'horse', primary: 'hr_lance', primary_weapons: []}],
          skeletons: {hr_lance: {actions: [{slot: 0, action: 'stand_a_idle', playable: true, rel: 'r.cas'}]}}},
  mount_h: {sets: [{mount: 'horse', primary: 'fs_h', primary_weapons: []}],
            skeletons: {fs_h: {actions: [{slot: 0, action: 'stand_a_idle', playable: true, rel: 'h.cas'}]}}}};
const anims = {   // the rider's pelvis never leaves the origin; the horse stands its saddle 1.6 up
  hr_lance: {times: [0, 1], bones: [bone('Scene Root', -1, [0, 0, 0]), bone('bone_pelvis', 0, [0, 0, 0])]},
  fs_h: {times: [0, 1], bones: [bone('Scene Root', -1, [0, 0, 0]), bone('bone_H_Saddle', 0, [0, 1.6, 0])]}};
const asked = [];
const q = (url, k) => decodeURIComponent((url.match(new RegExp('[?&]' + k + '=([^&]*)')) || [])[1] || '');
const gl = {ARRAY_BUFFER: 1, ELEMENT_ARRAY_BUFFER: 2, STATIC_DRAW: 3, DYNAMIC_DRAW: 4,
  createBuffer: () => ({}), bindBuffer() {}, bufferData() {}, bufferSubData() {}, deleteBuffer() {}};
const c = {
  ARM: {assets: new Map([['M|mount_h', tri([[0, 0, 0], [0, -1.9, 0], [0, 0, 1]], 'bone_H_Saddle')],
                         ['M|rider', tri([[0, 0, 0], [0, -1, 0], [0, 0.5, 0]], 'bone_pelvis')]])},
  state: {}, armProj: () => project, armFrame() {}, armSave() {}, armGl: () => gl,
  armObjMatrix: () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], armPivot: () => [0, 0, 0],
  armPieceEach: (live, pc, fn) => { const g = live.geo.groups[pc.group]; for(let i = 0; i < g.count; i++) fn(live.geo.indices[g.start + i]); },
  armVisibleObjects: () => project.objects, armAssetKey: a => `${a.mod}|${a.entry}`,
  armCollHidden: () => false,
  document: {getElementById: () => null}, performance: {now: () => 0}, requestAnimationFrame() {},
  tt: x => x, esc: String, enc: encodeURIComponent, errText: String, atob: s => s,
  api: {get: async url => {
    asked.push(url);
    if(url.startsWith('/api/model/mounts')) return q(url, 'entry') === 'rider'
      ? {mounts: [{type: 'h horse', entry: 'mount_h', skeleton: 'fs_h', offset: [0, 0.38, 0.7]}]} : {mounts: []};
    if(url.startsWith('/api/model/anims')) return lists[q(url, 'entry')];
    if(url.startsWith('/api/model/anim?')) return JSON.parse(JSON.stringify(anims[q(url, 'skel')]));
    throw new Error('unexpected ' + url);
  }}};
{ const g = c.ARM.assets.get('M|rider').geo;   // group 1: three more vertices, unweighted
  g.positions.push(0, 0.6, 0, 0.1, 0.6, 0, 0, 0.7, 0); g.weights.push(0, 0, 0, 0, 0, 0);
  g.joints.push(0, 0, 0, 0, 0, 0); g.indices.push(3, 4, 5); g.groups.push({start: 3, count: 3}); }
vm.createContext(c);
vm.runInContext(js('v3anim.js'), c);
vm.runInContext(js('armanim.js'), c);
c.armAnimPaint = () => {};
c.armAnimLoop = () => {};

const near = (got, want, what) => want.forEach((v, k) =>
  assert(Math.abs(got[k] - v) < 1e-5, `${what}: got [${[...got].map(x => x.toFixed(3))}], want [${want}]`));

(async () => {
  // the rider's own action, as the Animations window picks it
  await c.armAnimFrom('M|rider');
  await c.armAnimPick('0');
  const a = c.armAnim();
  assert(a.data, 'the rider action loads');
  c.armAnimPose(project.objects);
  const gH = a.geos.get('h'), gR = a.geos.get('r');
  assert(gH.posed && gR.posed, 'both models are posed');
  // the horse plays its own action: saddle 1.6 up, lowered by the still
  // model's lowest point (its hooves, -1.9) as a man on foot is
  near(gH.outPos.slice(0, 3), [0, 1.6 - 1.9, 0], 'the horse stands on its own skeleton');
  // the rider's pelvis rides rider_offset above and ahead of the saddle bone
  near(gR.outPos.slice(0, 3), [0, 1.6 - 1.9 + 0.38, 0.7], 'the rider sits on the saddle at rider_offset');
  const gM = a.geos.get('m');
  assert(gM.posed, 'an unweighted part of the rider is carried with him');
  near(gM.outPos.slice(0, 3), [0, 1.6 - 1.9 + 0.38 + 0.6, 0.7], 'the helmet stays on the rider');
  assert(!(gH.missing || []).length, 'no horse bone is reported missing from the rider skeleton');

  // Rest drops the mount with the action
  c.armAnimRest();
  assert.equal(a.mount, null, 'Rest forgets the mount');

  // the horse's own action picked: the rider plays his action for the same
  // slot and rides it, rather than standing stiff on the saddle bone
  await c.armAnimFrom('M|mount_h');
  await c.armAnimPick('0');
  assert(a.rider && a.rider.key === 'M|rider', 'a horse action finds the rider loaded on it');
  c.armAnimPose(project.objects);
  near(a.geos.get('h').outPos.slice(0, 3), [0, 1.6 - 1.9, 0], 'the horse plays its own action');
  near(a.geos.get('r').outPos.slice(0, 3), [0, 1.6 - 1.9 + 0.38, 0.7], 'the rider rides the horse action');
  near(a.geos.get('r').outPos.slice(3, 6), [0, 1.6 - 1.9 + 0.38 - 1, 0.7], 'posed by his own skeleton, not the horse hub');
  near(a.geos.get('m').outPos.slice(0, 3), [0, 1.6 - 1.9 + 0.38 + 0.6, 0.7], 'his helmet rides with him');
  assert(!(a.geos.get('r').missing || []).length, 'no rider bone is reported missing from the horse skeleton');
  c.armAnimRest();
  assert.equal(a.rider, null, 'Rest forgets the rider');

  // the card maker: Riding picks the rider, not the horse listed first
  const cg = js('cardgen.js');
  const card = {pose: 'riding', oneEach: true, poseNote: '', poseNote2: ''};
  c.cg = () => card;
  c.armAnimEntries = () => project.assets.filter(x => x.kind === 'entry');
  c.armAnimSkel = v => { a.skel = v; a.key = ''; a.data = null; };
  vm.runInContext(pick(cg, /const CG_POSE_KEYS = [^\n]*/).replace('const ', 'var '), c);
  vm.runInContext(pick(cg, /async function cgPreparePose\(\)\{[\s\S]*?\n\}/), c);
  await c.armAnimFrom('M|mount_h');                 // the horse was loaded first
  await c.cgPreparePose();
  assert.equal((project.anim || {}).asset, 'M|rider', 'Riding poses the rider entry');
  assert.equal(a.skel, 'hr_lance', 'Riding plays the rider skeleton');
  assert(a.mount && a.mount.key === 'M|mount_h', 'and carries him on the loaded horse');
  assert.equal(card.poseNote2, '', 'a carried rider is not told there is no riding skeleton');

  // "One of each part" is one of each part per model: the horse keeps its Body
  vm.runInContext(pick(cg, /function cgObjects\(\)\{[\s\S]*?\n\}/), c);
  assert.deepEqual(c.cgObjects().map(o => o.id), ['h', 'r', 'm'], 'the horse Body and the rider Body are both drawn');
  console.log('PASS: Armory poses a horse by its own skeleton and carries the rider at rider_offset');
})().catch(err => { console.error(err); process.exitCode = 1; });
