// The card maker's "Add owner" checklist (2026-11-26): its rows showed a
// checkbox and no faction name. `.cggiveowners input{width:100%}` was meant for
// the Find box but matched every row's checkbox too, which then filled the row
// and pushed the name out of its clipped label. Only the Find box is sized.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const css = fs.readFileSync(path.join(__dirname, '..', 'web', 'index.html'), 'utf8');
const rules = [...css.matchAll(/([^{}]*\.cggiveowners[^{}]*)\{([^}]*)\}/g)].map(m => [m[1].trim(), m[2]]);
for(const [sel, body] of rules){
  if(!/width/.test(body)) continue;
  for(const part of sel.split(',')){
    // a descendant `input` (not `> input`) reaches the rows' checkboxes
    assert(!/\.cggiveowners\s+input\b/.test(part.trim()),
      `"${part.trim()}" sizes the checklist's checkboxes along with the Find box`);
  }
}
const src = fs.readFileSync(path.join(__dirname, '..', 'web', 'js', 'cardgen.js'), 'utf8');
assert(/<div class="cggiveowners"><input /.test(src), 'the Find box is the checklist\'s direct child');
console.log('test_cardgen_owners: 1/1 passed');
