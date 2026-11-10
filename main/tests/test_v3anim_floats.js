// "The shield floats", "sometimes the bow also floats" (2026-11-10). Two ways a
// carried part was left in mid-air while its man moved:
// 1. A rigid part (a vanilla knight's heater shield, his helmet, a horse
//    archer's quiver) names one bone on every vertex with weight 0. The game
//    holds it fully on that bone; the previewer treated it as unweighted and
//    left it standing where it was modelled.
// 2. A part weighted to a bone the playing skeleton has not got (bone_shield,
//    a bow's bone_bowoffset when the skeleton plays without the bow's weapon
//    skeleton) went with the pelvis. It now goes to the limb that holds it:
//    a shield to the left elbow, a bow and its string to the left hand (one
//    hand, so the bow keeps its shape), a weapon to the right hand, and only
//    an unknown bone to the pelvis.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const c = {Math, Float32Array, Uint8Array, Map, Set};
vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'web', 'js', 'v3anim.js'), 'utf8'), c);

const bone = (name, parent, pivot, pos) => ({name, parent, pivot, pos: pos ? [pos] : [], rot: []});
// a man whose left elbow is moved 1 up by the action
const anim = {times: [0, 1], bones: [
  bone('Scene Root', -1, [0, 0, 0]), bone('bone_pelvis', 0, [0, 0, 0]),
  bone('bone_lelbow', 1, [-0.5, 0.4, 0], [0, 1, 0]), bone('bone_lhand', 2, [-0.3, 0, 0]),
  bone('bone_rhand', 1, [0.8, 0.4, 0])]};

// 2: the bones it has not got
const bm = c.v3aBoneMap(['bone_shield', 'bone_bowoffset', 'bone_bowstring', 'bone_weapon01', 'bone_tail', 'bone_LElbow'], anim);
assert.deepEqual([...bm.map], [2, 3, 3, 4, 1, 2], 'shield->left elbow, bow and string->left hand, weapon->right hand, unknown->pelvis');
assert.deepEqual([...bm.missing], ['bone_tail'], 'only a bone with no holder is said to go with the pelvis');
// with no hand in the skeleton, a shield or bow still goes to the left elbow
const noHand = {times: [0, 1], bones: anim.bones.filter(b => b.name !== 'bone_lhand')};
assert.equal(c.v3aBoneMap(['bone_bowoffset'], noHand).map[0], 2, 'a bow with no left hand goes to the left elbow');

// 1: a shield on the left elbow, weight 0 on every vertex
const geo = {vertices: 2, positions: Float32Array.from([-0.6, 0.4, 0.1, -0.6, 0.2, 0.1]),
  normals: Float32Array.from([0, 0, 1, 0, 0, 1]), weights: new Float32Array(4), joints: Uint8Array.from([0, 0, 0, 0])};
const pos = new Float32Array(6), nrm = new Float32Array(6);
c.v3aSkin(geo, c.v3aPose(anim, 0), c.v3aBind(anim), c.v3aBoneMap(['bone_lelbow'], anim).map, pos, nrm, [0, 0, 0]);
assert.deepEqual([...pos].map(v => +v.toFixed(4)), [-0.6, 1.4, 0.1, -0.6, 1.2, 0.1], 'a weight-0 shield rides its elbow up 1');
console.log('PASS: rigid and unheld parts follow the limb that holds them');
