// The card maker's HD view and unit models (2026-11-24).
// 1. Mumakil's card maker broke with "Cannot read properties of undefined
//    (reading 'pre')": the frame and rig handles were drawn (a picture landing,
//    a hover) before the view's first draw had set its camera.
// 2. Only a unit's armour_ug_models are offered and loaded; its soldier line's
//    model only when it has no such list.
// 3. Lights: Flat is no lamp and a full ambient; extra lamps join the main one.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const src = fs.readFileSync(path.join(__dirname, '..', 'web', 'js', 'cardgen.js'), 'utf8');
const canvas = () => ({ width: 100, height: 100, style: {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
  getContext: () => new Proxy({}, { get: (t, k) => k in t ? t[k] : () => {}, set: (t, k, v) => { t[k] = v; return true; } }) });
const els = { cgHdUi: canvas(), cgHd: canvas(), cgHdView: canvas() };
const ctx = {
  state: { mode: 'cards', cgSrc: 'unit' }, console,
  tt: (k, o) => k + (o ? JSON.stringify(o) : ''), ttA: k => k, ttN: k => k, esc: s => String(s),
  document: { getElementById: id => els[id] || null, querySelector: () => null }, CSS: { escape: s => String(s) },
};
vm.createContext(ctx);
vm.runInContext(src, ctx);

// 1: the overlay with the rig showing and no camera yet
vm.runInContext(`cgRigActive = () => true; armAnim = () => ({data: {bones: []}}); cgRigLayout = () => ({bones: [], byName: new Map()});
  crSolve = () => []; look = () => ({}); CG_WORK.cut = null; CG_WORK.mode = 'pose'; cg().rig.handles = true; delete CG_WORK.camera;`, ctx);
assert.doesNotThrow(() => vm.runInContext('cgOverlay()', ctx), 'the overlay must wait for the view\'s camera');

// 2: armour upgrade models only
const opts = html => [...html.matchAll(/<option value="([^"]*)"/g)].map(m => m[1]);
const ug = vm.runInContext(`cgUgSelect({soldier: 'Turkish_Archers', ug: ['Elephant_Crew2', 'Elephant_Crew3']}, 'elephant_crew2', '')`, ctx);
assert.deepStrictEqual(opts(ug), ['elephant_crew2', 'elephant_crew3'], 'the soldier line\'s model is not offered beside the upgrade models');
assert.strictEqual(vm.runInContext(`cgUnitModel({soldier: 'Turkish_Archers', ug: ['Elephant_Crew2']})`, ctx), 'Elephant_Crew2');
const bare = vm.runInContext(`cgUgSelect({soldier: 'Peasants', ug: []}, 'peasants', '')`, ctx);
assert.deepStrictEqual(opts(bare), ['peasants'], 'a unit with no upgrade models still has its soldier model');
assert.strictEqual(vm.runInContext(`cgUnitModel({soldier: 'Peasants'})`, ctx), 'Peasants');

// 3: lights
const camera = '{target: [0, 1, 0]}';
let lit = vm.runInContext(`cg().light.flat = true; cgLight(${camera})`, ctx);
assert.strictEqual(lit.list.length, 0); assert.strictEqual(lit.ambient, 1); assert.strictEqual(lit.level, 1);
lit = vm.runInContext(`cg().light.flat = false; cg().lights = [{type: 'point', azimuth: 0, elevation: 0, amount: 0.5}]; cgLight(${camera})`, ctx);
assert.strictEqual(lit.list.length, 2, 'the main lamp and the added one');
assert.strictEqual(lit.list[1].point, true); assert.strictEqual(lit.list[1].amount, 0.5);
lit = vm.runInContext(`cg().lights = Array(9).fill({type: 'sun', azimuth: 0, elevation: 0, amount: 1}); cgLight(${camera})`, ctx);
assert.strictEqual(lit.list.length, 4, 'the shader takes four lamps at most');

// 4: copies of a model (a mumak's riders) are objects of their own, in a group
// of their own, each choosing its own variant of every part
const copies = vm.runInContext(`cg().dups = [{k: 1, ids: [-1, -2], name: 'crew'}, {k: 2, ids: [-1], name: 'crew'}];
  const base = [{id: -1, name: 'Body', src: [{asset: 'A'}]}, {id: -2, name: 'Head', src: [{asset: 'A'}]}, {id: -3, name: 'Legs', src: [{asset: 'A'}]}];
  cgCopies(base)`, ctx);
assert.strictEqual(copies.length, 3);
assert.strictEqual(new Set(copies.map(o => o.id).concat([-1, -2, -3])).size, 6, 'a copy never shares an id');
assert.strictEqual(JSON.stringify(copies.map(o => o.grp)), JSON.stringify(['dup:1', 'dup:1', 'dup:2']));
assert.notStrictEqual(vm.runInContext('cgPartKey', ctx)(copies[0]), vm.runInContext('cgPartKey', ctx)({id: -1, name: 'Body', src: [{asset: 'A'}]}),
  'a copy picks its own variant of a part');
assert.strictEqual(vm.runInContext('cgCopies(base)', ctx)[0], copies[0], 'the same copy object each time, so caches hold');

// 5: the Save menu. A card is for its unit: the menu opens on it alone, the
// picked texture's faction marked; slave beside real owners is not (the game
// never looks there). + adds a faction as a new owner; mercs alone, with
// "only", takes the card out of every faction folder.
vm.runInContext(`cgGet = async () => ({icon_variants: {card: [{rel: 'ui/units/spain/#m.tga', factions: ['spain']}]}});
  CG_UNIT.units = {list: [{type: 'Mumakil', soldier: 'Turkish_Archers', ug: ['Elephant_Crew2'], factions: ['spain', 'slave']},
    {type: 'Other', soldier: 'x', ug: ['elephant_crew2'], factions: ['khand', 'slave']}]};
  CG_UNIT.unit = 'Mumakil'; CG_UNIT.entry = 'elephant_crew2';
  CG_UNIT.skins = [{factions: ['england']}, {factions: ['spain', 'khand']}];
  cg().texFaction = ''; cg().saved = {path: 'C:/cards/#Mumakil.tga', kind: 'card'}; cg().give = null; cgGiveOpen();`, ctx);
let g = vm.runInContext('cg().give', ctx);
assert.strictEqual(JSON.stringify(g.order), JSON.stringify(['Mumakil']), 'only the unit the card was made for');
assert.strictEqual(JSON.stringify([...g.rows.Mumakil.picked]), JSON.stringify(['spain']), 'its owners, slave left out beside a real one');
vm.runInContext(`cgGiveAdd('Other')`, ctx);
assert.strictEqual(JSON.stringify(vm.runInContext('cg().give.order', ctx)), JSON.stringify(['Mumakil', 'Other']), 'another unit, from the picker');
let body = vm.runInContext(`cgGiveOwnerSet('Mumakil', 'khand', true); cgGiveBody('Mumakil')`, ctx);
assert.strictEqual(JSON.stringify(body.card_folders), JSON.stringify(['spain', 'khand']));
assert.strictEqual(body.field_overrides.ownership, 'spain, slave, khand', '+ gives khand ownership');
body = vm.runInContext(`cgGiveTick('Mumakil', 'khand'); cgGiveBody('Mumakil')`, ctx);
assert.strictEqual(body.field_overrides, undefined, 'a + faction unmarked again changes no ownership');
body = vm.runInContext(`cgGiveSet('mercs', true); cgGiveSet('only', true); cgGiveBody('Mumakil')`, ctx);
assert.strictEqual(JSON.stringify(body.card_folders), JSON.stringify(['mercs'])); assert.strictEqual(body.card_only, true);
body = vm.runInContext(`cg().saved.kind = 'info'; cgGiveBody('Mumakil')`, ctx);
assert.strictEqual(JSON.stringify(body.info_folders), JSON.stringify(['merc']), "an info card's mercenary folder is merc");

// 6: the pose library: the kit's Mounted folder split by the poses' names,
// and the folders in the kit's order
const sub = vm.runInContext(`[cgPoseSub({c: 'IK Full/Mounted', n: 'IK Mounted Crossbow Full 2'}).c, cgPoseSub({c: 'IK Full/Mounted', n: 'IK Mounted Spear Full 1'}).c,
  cgPoseSub({c: 'IK Full/1H', n: 'IK Spear Full 1'}).c]`, ctx);
assert.strictEqual(JSON.stringify(sub), JSON.stringify(['IK Full/Mounted/crossbow', 'IK Full/Mounted/spears', 'IK Full/1H']));
const order = vm.runInContext(`['IK Bodyparts/IK Arms', 'IK Orcs Full', 'Saved', 'IK Dwarves Full', 'IK Full/2H', 'IK Full'].sort((x,y) => cgFolderRank(x)-cgFolderRank(y) || x.localeCompare(y))`, ctx);
assert.strictEqual(JSON.stringify(order), JSON.stringify(['IK Full', 'IK Full/2H', 'IK Dwarves Full', 'IK Orcs Full', 'IK Bodyparts/IK Arms', 'Saved']));

// 7: an elephant's crew as the game has it: the riders stand by their skeleton's
// standing idle (only the driver plays er_stand_a_idle), and the model wears
// its owner's sheet (Mumakil's Elephant_Crew2 lists a generic one first)
const beastList = {sets: [{primary: 'fs_gorgoroth_beast_rider'}], skeletons: {fs_gorgoroth_beast_rider: {actions: [
  {action: 'er_stand_a_idle', playable: true, slot: 1}, {action: 'stand_a_idle', playable: true, slot: 2}]}}};
vm.runInContext(`enc = encodeURIComponent; api = {get: async url => ({bones: [{}]})}; v3aBind = () => null;`, ctx);
vm.runInContext(`cgCrewAnim('m', ${JSON.stringify(beastList)}).then(r => globalThis.__crew = r)`, ctx);
setImmediate(() => {
  assert.strictEqual(ctx.__crew.action, 'stand_a_idle', 'the riders stand as men on foot, not in the driver\'s rider idle');
  const skins = [{factions: ['england', 'slave'], exists: true}, {factions: ['spain'], exists: true}];
  assert.strictEqual(vm.runInContext(`cgOwnerSkin({factions: ['slave', 'spain']}, ${JSON.stringify(skins)})`, ctx), 'spain', 'the owner before the rebels');
  assert.strictEqual(vm.runInContext(`cgOwnerSkin({factions: ['spain']}, [{factions: ['spain'], exists: true}])`, ctx), '', 'one sheet: nothing to pick');
  console.log('PASS: card maker view waits for its camera, offers upgrade models only, lights, copies, the Save menu, the pose folders and an elephant\'s crew');
});
