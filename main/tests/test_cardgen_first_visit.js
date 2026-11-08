// "Unit cards" in the Models Editor switched the title but left the Models
// Editor on screen (2026-11-08). The cards screen sends a first visit, with no
// sub-page chosen yet, to the card maker (cardsSubNow() -> 'generate'), but the
// card maker painted only when state.cardsSub was literally 'generate'. Both
// must agree on which sub-page is showing.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const js = f => fs.readFileSync(path.join(__dirname, '..', 'web', 'js', f), 'utf8');
const pick = (src, re) => { const m = src.match(re); assert(m, 'not found: ' + re); return m[0]; };

const ctx = { state: { mode: 'cards' }, cardGenOn: () => true };
vm.createContext(ctx);
vm.runInContext(pick(js('cards.js'), /const cardsSubNow=[^\n]*/).replace('const ', 'var '), ctx);
vm.runInContext(pick(js('cardgen.js'), /function cgHere\(\)\{[^\n]*\}/), ctx);

for (const sub of [undefined, 'generate']) {
  ctx.state.cardsSub = sub;
  assert.strictEqual(ctx.cardsSubNow(), 'generate');
  assert.strictEqual(ctx.cgHere(), true, `card maker must paint when cardsSub is ${sub}`);
}
for (const sub of ['clean', 'art', 'sheets']) {
  ctx.state.cardsSub = sub;
  assert.strictEqual(ctx.cgHere(), false, `card maker must not paint over ${sub}`);
}
ctx.state.cardsSub = undefined; ctx.state.mode = 'bmdb';
assert.strictEqual(ctx.cgHere(), false, 'card maker must not paint over another mode');
console.log('PASS: the card maker paints on a first visit to Unit cards');
