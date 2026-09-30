"""A watchtower's line of sight on the campaign map - Phase 89c.

A modder placing watchtowers asked to see what one covers before choosing its
tile, drawn one of two ways: FILLED (every tile it sees tinted) or OUTLINE (the
edge only), with a switch to show or hide it.

What is held here, run for real in node on campmark.js:

    1  the reach: 10 tiles, a disc and not a square, 21 tiles across
    2  what gets one: every tower when switched on, none when off or when the
       watchtower markers are hidden; the tower being dragged where it is NOW;
       the tile under the pointer while a new watchtower is being placed, and
       only a watchtower
    3  the two looks: filled paints the disc's rows, outline draws one circle
    4  the switch and the look are remembered in Settings, and `w` is the key

    python -m tests.test_mapsight
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _tmp, _webtext  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS_DIR = ROOT / "web" / "js"

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const posts = [];
const ctx = {
  console, state: {settings: {}},
  document: {getElementById: () => null},
  api: {post: (u, b) => { posts.push([u, b]); return Promise.resolve({}); }},
  esc: s => (s == null ? '' : '' + s),
};
ctx.window = ctx;
vm.createContext(ctx);
for(const f of process.argv[2].split(','))
  vm.runInContext(fs.readFileSync(f, 'utf8'), ctx);
const out = [];
const check = (label, cond) => out.push([!!cond, label]);

// 1) the reach
const R = vm.runInContext('CMK_SIGHT', ctx);
check('the reach is 10 tiles', R === 10);
const spans = ctx.cmkSightSpans(R);
const tiles = spans.reduce((n, [dy, h]) => n + 2 * h + 1, 0);
check(`a disc of ${tiles} tiles, 21 across, not the 441 of a square`,
      spans.length === 21 && spans[10][1] === 10 && spans[0][1] === 0
      && tiles > 300 && tiles < 441);
check('every tile it counts is within 10, and every tile within 10 is counted',
      spans.every(([dy, h]) => dy * dy + h * h <= 100 && dy * dy + (h + 1) * (h + 1) > 100));

// 2) what gets one
const tower = {kind: 'watchtower', line: 5}, tower2 = {kind: 'watchtower', line: 9};
const fort = {kind: 'fort', line: 7};
ctx.state.cmap = {view: {zoom: 4}, man: {width: 100, height: 100}, hover: null};
ctx.cmkPaint = () => {}; ctx.cmapPaint = () => {}; ctx.cmkLoad = () => {};
ctx.cmkStale = () => {}; ctx.cmapTipPaint = () => {};
const k = ctx.cmkNew('Mod');
k.groups = [{tx: 20, ty: 30, items: [tower, fort]}, {tx: 60, ty: 10, items: [tower2]}];
ctx.state.cmk = k;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
check('off by default: no tower draws a sight', k.sight.on === false
      && ctx.cmkSightCentres().length === 0);
ctx.cmkSightToggle();
check('switched on: every watchtower, and not the fort beside one',
      same(ctx.cmkSightCentres(), [[20, 30], [60, 10]]));
k.cats.watchtower = false;
check('hidden with the watchtower markers', ctx.cmkSightCentres().length === 0);
k.cats.watchtower = true;
k.drag = {item: tower, from: [20, 30], tile: [25, 33]};
check('a dragged tower is drawn where it is now, not where it was',
      same(ctx.cmkSightCentres(), [[60, 10], [25, 33]]));
ctx.cmkSightToggle();
check('and while dragged it is drawn with the switch off',
      same(ctx.cmkSightCentres(), [[25, 33]]));
k.drag = {item: fort, from: [20, 30], tile: [25, 33]};
check('a dragged fort draws none', ctx.cmkSightCentres().length === 0);
k.drag = null;
ctx.state.cmap.hover = [44, 55];
ctx.state.cpin = {what: 'x', fn: 'cftPlace', args: ['watchtower']};
check('placing a new watchtower: drawn under the pointer',
      ctx.cmkSightPlacing() && same(ctx.cmkSightCentres(), [[44, 55]]));
ctx.state.cpin = {what: 'x', fn: 'cmapCreateObjectAt', args: ['fort']};
check('placing a fort: none', !ctx.cmkSightPlacing() && ctx.cmkSightCentres().length === 0);
ctx.state.cpin = null;

// 3) the two looks
function canvas(){
  const calls = [];
  return {calls, save(){}, restore(){}, beginPath(){}, stroke(){ calls.push('stroke'); },
    fillRect(x, y, w, h){ calls.push(['rect', x, y, w, h]); },
    arc(x, y, r){ calls.push(['arc', x, y, r]); }};
}
ctx.cmapX = t => t * 4; ctx.cmapY = t => t * 4;
ctx.cmkSightToggle();
let cv = canvas();
ctx.cmkSightDraw(cv, 0, 0, 100, 100);
const rects = cv.calls.filter(c => c[0] === 'rect');
check('filled: one rectangle per row of each disc, 21 rows a tower',
      rects.length === 42 && !cv.calls.some(c => c[0] === 'arc'));
const mid = rects.find(r => r[2] === 30 * 4);
check('  the middle row is 21 tiles wide and starts 10 tiles left of the tower',
      mid && mid[1] === 10 * 4 && mid[3] === 21 * 4);
ctx.cmkSightLook('outline');
cv = canvas();
ctx.cmkSightDraw(cv, 0, 0, 100, 100);
const arcs = cv.calls.filter(c => c[0] === 'arc');
check('outline: one circle per tower, around the tile, 10.5 tiles out',
      arcs.length === 2 && !cv.calls.some(c => c[0] === 'rect')
      && arcs[0][1] === 20 * 4 + 2 && arcs[0][3] === 10.5 * 4);
cv = canvas();
ctx.cmkSightDraw(cv, 80, 80, 100, 100);
check('a repaint of tiles no sight reaches draws nothing', cv.calls.length === 0);

// 4) remembered
const last = posts[posts.length - 1];
check('the switch and the look are saved to Settings',
      last && last[0] === '/api/settings' && last[1].map_sight.on === true
      && last[1].map_sight.look === 'outline');
ctx.state.settings.map_sight = {on: true, look: 'outline'};
const k2 = ctx.cmkNew('Mod');
check('and a map opened later starts with them', k2.sight.on && k2.sight.look === 'outline');
ctx.state.settings.map_sight = {on: true, look: 'bogus'};
check('a look it does not know falls back to filled', ctx.cmkNew('Mod').sight.look === 'filled');

fs.writeFileSync(process.argv[3], JSON.stringify(out));
"""

print("\n== 89c: a watchtower's line of sight, run in node ==")
node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH, and these functions run in it")
else:
    td = Path(_tmp.mkdtemp(prefix="ut_mapsight_"))
    run = td / "harness.js"
    run.write_text(HARNESS, encoding="utf-8")
    res = td / "out.json"
    files = ",".join(str(_webtext.english_copy(JS_DIR / n)) for n in ("campmark.js",))
    p = subprocess.run([node, str(run), files, str(res)], capture_output=True, text=True)
    if p.returncode != 0:
        check("the harness runs", False)
        print((p.stderr or p.stdout).strip()[:2000])
    else:
        for passed, label in json.loads(res.read_text(encoding="utf-8")):
            check(label, passed)
    shutil.rmtree(td, ignore_errors=True)

src = _webtext.read(JS_DIR / "campmap.js")
check("`w` switches it, in the map's own key handler",
      "e.key === 'w'" in src and "cmkSightToggle()" in src)
check("drawn under the markers, from the overlay",
      src.index("cmkSightDraw(x, s0, t0, s1, t1)") < src.index("cmkDraw(x, s0, t0, s1, t1)"))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
