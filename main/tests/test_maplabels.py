"""Labels, and picking a tile - Phase 20c: T4 and M8.

    T4   settlement names on the map, placed so that none covers another name
         or another settlement, at a size that does not change with the zoom
    M8   one pin control that puts the map into pick mode and writes the
         clicked tile into whichever field asked, in the file's own coordinates

**Both are arithmetic in the browser, so both are run in node** - the harness
20a set up in `tests/test_maplayers.py` and 20b extended to three files. What
runs is the real ``clnLayout`` over the real settlement table of every
installed map at six zooms, and the real ``cpinTake`` against a stubbed page.

The load-bearing claim of T4 is an invariant, not a picture: **no placed name
overlaps another placed name, and no placed name overlaps any settlement's
marker**, at every zoom, on every map. A name that has no room is left off and
counted rather than drawn over something, which is the one place this departs
from TWMapReader - and the count is checked to go up as the zoom does, which is
what makes leaving a name off honest rather than lossy.

Four parts:

    1  the settlement tables, out of every installed map's manifest
    2  the layout on grids written here, where the answer is workable by hand
    3  the layout on every real map, at six zooms
    4  the pin: the flip, the bounds, the take, and the button's own HTML

    python -m tests.test_maplabels
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS_DIR = ROOT / "web" / "js"
INSTALLED = [m for m in list(_realmod.installed()) + [_realmod.MODS.parent]
             if (m / "data" / campmap.TERRAIN_REL).is_file()]


# ---- 1) the tables -----------------------------------------------------------

print("\n== 1) every installed map's settlements, as the browser is sent them ==")

maps = []
for m in INSTALLED:
    try:
        man = campmap.view(campmap.CampaignMap(Mod(m)), m.name)
    except Exception as exc:                                   # noqa: BLE001
        print(f"  [skip] {m.name}: {exc}")
        continue
    seated = [r for r in man["regions"] if r["settlement"] and r["name"]]
    check(f"{m.name}: {len(seated)} settlements with a pixel and a name to place",
          len(seated) > 0)
    maps.append({"name": m.name, "regions": man["regions"],
                 "width": man["width"], "height": man["height"]})

# which fields a pin reaches, read off the panels' own source
pinned = {f: (JS_DIR / f).read_text(encoding="utf-8").count("cpinButton(")
          for f in ("stratchar.js", "campevents.js")}
check(f"every coordinate on the map screen's panels has a pin beside it: {pinned}",
      pinned["stratchar.js"] >= 1 and pinned["campevents.js"] >= 2)
html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
tags = re.findall(r'<script src="js/([A-Za-z0-9_.-]+\.js)"></script>', html)
check("both new files load after campmap.js, whose transforms they draw with",
      "maplabels.js" in tags and "mappin.js" in tags
      and tags.index("campmap.js") < tags.index("maplabels.js")
      and tags.index("campmap.js") < tags.index("mappin.js"))


# ---- 2-4) in node ------------------------------------------------------------

print("\n== 2-4) the layout and the pin, run for real in node ==")

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

function canvas(){
  const cv = {width: 0, height: 0};
  cv.getContext = () => ({imageSmoothingEnabled: true, drawImage(){},
    putImageData(){}, getImageData(){ return {data: new Uint8ClampedArray(4)}; }});
  return cv;
}
const toasts = [], acts = [];
const ctx = {
  console,
  document: {createElement: () => canvas(), getElementById: () => null},
  performance: {now: () => Date.now()},
  toast: m => toasts.push(m),
  activity: (a, b) => acts.push(a + ': ' + b),
  esc: s => (s == null ? '' : '' + s).replace(/[&<>"]/g,
    c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])),
};
ctx.window = ctx;
vm.createContext(ctx);
for(const f of process.argv[2].split(','))
  vm.runInContext(fs.readFileSync(f, 'utf8'), ctx);
const BOX_H = vm.runInContext('CLN_BOX_H', ctx);

const out = [];
const check = (label, cond) => out.push([!!cond, label]);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

//: what a test can predict: 6 CSS pixels a character
const measure = t => t.length * 6;
const meet = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w
                    && a.y < b.y + b.h && b.y < a.y + a.h;

/* The invariant, said once: no box over another box, none over any marker. */
function clean(lay, items, zoom, ob){
  const half = Math.max(1, ob) / 2;
  const marks = items.map(it => ({x: (it.tx + .5) * zoom - half,
    y: (it.ty + .5) * zoom - half, w: half * 2, h: half * 2}));
  for(let i = 0; i < lay.boxes.length; i++){
    for(let j = i + 1; j < lay.boxes.length; j++)
      if(meet(lay.boxes[i], lay.boxes[j])) return `${lay.boxes[i].key} over ${lay.boxes[j].key}`;
    for(const m of marks) if(meet(lay.boxes[i], m)) return `${lay.boxes[i].key} over a marker`;
  }
  return '';
}

// ---- 2) grids worked by hand -----------------------------------------------
{
  const one = [{key: 'a', tx: 5, ty: 5, text: 'Alpha', prio: 1}];
  const lay = ctx.clnLayout(one, 10, measure, 6);
  const b = lay.boxes[0];
  check('a name with room goes to the right of its marker, centred on it',
        b && b.x > b.ax && Math.abs((b.y + b.h / 2) - b.ay) < 0.01);
  check('…and starts the gap past the marker\'s edge, not on it',
        b && Math.abs(b.x - (b.ax + 3 + 3)) < 0.01);

  // two settlements side by side: the second one's right side is taken by the
  // first one's marker, so it is nudged or goes left - it is not drawn over
  const two = [{key: 'big', tx: 5, ty: 5, text: 'Bigtown', prio: 9},
               {key: 'small', tx: 4, ty: 5, text: 'Smallton', prio: 1}];
  const l2 = ctx.clnLayout(two, 12, measure, 8);
  const bb = l2.boxes.find(x => x.key === 'big'), sb = l2.boxes.find(x => x.key === 'small');
  check('the bigger province is placed first, and gets the first place it asks for',
        bb && bb.x > bb.ax && Math.abs((bb.y + bb.h / 2) - bb.ay) < 0.01);
  check(`the smaller one next door moves rather than covering it (${sb ? (sb.x < sb.ax ? 'left' : 'nudged') : 'hidden'})`,
        sb && !meet(sb, bb) && !clean(l2, two, 12, 8));

  // a crowd on one row at a low zoom: most cannot fit, and none is drawn over
  const crowd = [];
  for(let i = 0; i < 30; i++) crowd.push({key: 'c' + i, tx: i, ty: 3,
    text: 'Settlement' + i, prio: 30 - i});
  const lc = ctx.clnLayout(crowd, 2, measure, 5);
  check(`thirty on a row at 2 px a tile: ${lc.boxes.length} placed, ${lc.hidden.length} left off, none over another`,
        lc.boxes.length > 0 && lc.hidden.length > 0 && !clean(lc, crowd, 2, 5)
        && lc.boxes.length + lc.hidden.length === 30 && lc.total === 30);
  check('…and what is left off is the smaller provinces, not whichever came last',
        lc.boxes.some(b => b.key === 'c0'));
  const lc2 = ctx.clnLayout(crowd, 40, measure, 5);
  check(`at 40 px a tile the same row has room for more of them (${lc2.boxes.length})`,
        lc2.boxes.length > lc.boxes.length && !clean(lc2, crowd, 40, 5));

  check('a name with no words is not a name, and is not counted',
        ctx.clnLayout([{key: 'x', tx: 1, ty: 1, text: '', prio: 1}], 8, measure, 5).total === 0);
  check('the same map at the same zoom lays out the same way twice',
        JSON.stringify(ctx.clnLayout(crowd, 7, measure, 5))
        === JSON.stringify(ctx.clnLayout(crowd, 7, measure, 5)));
  const z4 = ctx.clnLayout(one, 4, measure, 6).boxes[0];
  const z30 = ctx.clnLayout(one, 30, measure, 6).boxes[0];
  check('a name is the same size on screen at any zoom - the font does not grow',
        z4.w === z30.w && z4.h === z30.h && z4.h === BOX_H);

  const items = ctx.clnItems([
    {name: 'A_Province', settlement: [1, 2], settlement_name: 'Atown',
     shown_settlement: 'Ayton', pixels: 50},
    {name: 'B_Province', settlement: [3, 4], settlement_name: 'Btown',
     shown_settlement: '', pixels: 20},
    {name: 'C_Province', settlement: null, settlement_name: 'Ctown', pixels: 9},
    {name: '', settlement: [5, 5], pixels: 3}]);
  check('the words the player reads first, the code name when the mod has none',
        items.length === 2 && items[0].text === 'Ayton' && items[1].text === 'Btown');
  check('and a province with no settlement pixel, or no name, has nothing to label',
        !items.some(i => i.key === 'C_Province' || i.key === ''));
}

// ---- 3) every real map ------------------------------------------------------
for(const m of job.maps){
  const items = ctx.clnItems(m.regions);
  let prev = -1, rising = true, worst = 0, fault = '';
  const said = [];
  for(const z of [1, 2, 4, 8, 16, 32]){
    const ob = z >= 3 ? z * 1.7 : 5;          // the marker the screen draws there
    const t0 = Date.now();
    const lay = ctx.clnLayout(items, z, measure, ob);
    worst = Math.max(worst, Date.now() - t0);
    fault = fault || clean(lay, items, z, ob);
    if(lay.boxes.length < prev) rising = false;
    prev = lay.boxes.length;
    said.push(`${z}:${lay.boxes.length}`);
  }
  check(`${m.name}: at six zooms no name covers another name or any settlement (${said.join(' ')} of ${items.length})`,
        !fault);
  if(fault) check(`${m.name}: ${fault}`, false);
  check(`${m.name}: zooming in never names fewer settlements`, rising);
  check(`${m.name}: at 32 px a tile nearly every settlement is named (${prev} of ${items.length})`,
        prev >= items.length * 0.95);
  check(`${m.name}: a layout costs ${worst} ms, and is only asked for on a zoom`,
        worst < 250);
}

// ---- 4) the pin ------------------------------------------------------------
{
  check('a tile is flipped into the coordinates descr_strat.txt writes',
        JSON.stringify(ctx.cpinGame([3, 0], 10, 8)) === '[3,7]'
        && JSON.stringify(ctx.cpinGame([0, 7], 10, 8)) === '[0,0]');
  check('and a tile off the map is no tile at all',
        ctx.cpinGame([10, 0], 10, 8) === null && ctx.cpinGame([-1, 2], 10, 8) === null
        && ctx.cpinGame(null, 10, 8) === null);

  vm.runInContext('var got = []; function testPinned(tag, game, tile){ got.push([tag, game, tile]); }', ctx);
  ctx.state = {cmap: {man: {width: 10, height: 8}, view: {zoom: 1, ox: 0, oy: 0}}};
  check('nothing is armed to begin with, so a click is an ordinary pick',
        !ctx.cpinArmed() && ctx.cpinTake([1, 1]) === false);
  ctx.cpinArm("Denethor's tile", 'testPinned', ['row-2']);
  check('armed, it says what it is waiting for', ctx.cpinArmed()
        && ctx.state.cpin.what === "Denethor's tile");
  check('a click off the map is taken, said, and leaves it armed',
        ctx.cpinTake([12, 2]) === true && ctx.cpinArmed() && toasts.length === 1);
  check('a click on the map is taken - the pick it would have been does not happen',
        ctx.cpinTake([4, 1]) === true);
  const g = vm.runInContext('got', ctx);
  check(`…and the caller is handed its own arguments and the tile in game coordinates: ${JSON.stringify(g[0])}`,
        g.length === 1 && g[0][0] === 'row-2' && JSON.stringify(g[0][1]) === '[4,6]'
        && JSON.stringify(g[0][2]) === '[4,1]');
  check('one pick and it is disarmed, so the next click is the map\'s again',
        !ctx.cpinArmed() && ctx.cpinTake([4, 1]) === false);
  ctx.cpinArm('x', 'testPinned', []);
  ctx.cpinCancel();
  check('Cancel disarms it with nothing written', !ctx.cpinArmed()
        && vm.runInContext('got', ctx).length === 1);
  ctx.cpinArm('x', 'notAFunctionAnywhere', []);
  check('a caller that has gone away is said out loud, not thrown',
        ctx.cpinTake([1, 1]) === true && /nothing is listening/.test(toasts[toasts.length - 1]));

  // the button: an apostrophe in the sentence must not end its onclick early
  const btn = ctx.cpinButton("Denethor's tile", 'testPinned', [3]);
  const m = /onclick="([^"]*)"/.exec(btn);
  let parses = false;
  if(m){
    const js = m[1].replace(/&quot;/g, '"').replace(/&lt;/g, '<')
                   .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
    try{ new Function(js); parses = js.indexOf("Denethor's tile") > 0; }catch(e){}
  }
  check('the button\'s onclick survives a sentence with an apostrophe in it', parses);
  ctx.cpinArm("Denethor's tile", 'testPinned', [3]);
  check('and the button that armed the pin shows it is the one waiting',
        /cpinbtn on/.test(ctx.cpinButton("Denethor's tile", 'testPinned', [3]))
        && !/cpinbtn on/.test(ctx.cpinButton('other', 'testPinned', [4])));
  ctx.cpinToggle("Denethor's tile", 'testPinned', [3]);
  check('pressed again, the same button stops it', !ctx.cpinArmed());
}

fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""

node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH, and these functions run in it")
else:
    td = Path(_tmp.mkdtemp(prefix="ut_maplabels_"))
    job = td / "job.json"
    job.write_text(json.dumps({"maps": maps}), encoding="utf-8")
    run = td / "harness.js"
    run.write_text(HARNESS, encoding="utf-8")
    res = td / "out.json"
    files = ",".join(str(JS_DIR / n) for n in
                     ("campmap.js", "maplabels.js", "mappin.js"))
    p = subprocess.run([node, str(run), files, str(job), str(res)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        check("the harness runs", False)
        print((p.stderr or p.stdout).strip()[:2000])
    else:
        for passed, label in json.loads(res.read_text(encoding="utf-8")):
            check(label, passed)
    shutil.rmtree(td, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
