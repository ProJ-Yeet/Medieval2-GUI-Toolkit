"""Floating faction names - Phase 97b.

Each faction's name lettered over its largest connected block of land, along
that block's main axis, arched with it, sized to it, and given way by size
where two would cross. The layout is arithmetic in the browser
(`web/js/mapfactions.js`), so it is run in node on maps written here, where
the right answer can be worked by hand:

    1  the file is loaded where it has to be, and the screen reaches it
    2  a level strip, a tilted one, an arc, an island and a speck
    3  the invariants: never upside down, never steeper than 55 degrees, no
       two placed names crossing
    4  the label the server sends, cut to the name the player reads

    python -m tests.test_mapfactions
"""
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


WEB = ROOT / "web"
JS = WEB / "js" / "mapfactions.js"
src = _webtext.read(JS)

# ---------------------------------------------------------------------------
print("\n== 1) loaded where it has to be, and reached the way 20c's names are ==")

html = _webtext.read(WEB / "index.html")
tags = re.findall(r'<script src="js/([^"]+)"></script>', html)
check("index.html loads mapfactions.js after maplabels.js",
      "mapfactions.js" in tags and tags.index("maplabels.js") < tags.index("mapfactions.js"))
check("  and before map3d.js, which draws the same names in 3D",
      tags.index("mapfactions.js") < tags.index("map3d.js"))
cm = _webtext.read(WEB / "js" / "campmap.js")
check("the overlay letters them under the markers and 20c's names",
      re.search(r"cfnDraw\(x, s0, t0, s1, t1\).*?cmkDraw\(x, s0, t0, s1, t1\).*?clnDraw\(",
                cm, re.S) is not None)
check("on by default, and remembered with the view",
      "saved.faction_names === undefined ? true" in cm and "m.faction_names = !!c.fnOn" in cm)
check("a stroke on the regions lays them out again",
      "cfnRelayout()" in cm)
mv = _webtext.read(WEB / "js" / "mapviews.js")
check("a saved view puts the switch back", "c.fnOn = plan.factionNames" in mv)
m3 = _webtext.read(WEB / "js" / "map3d.js")
check("the 3D view draws them with the flat map's own lettering",
      "cfnDrawName(" in m3 and "function cfnDrawName" not in m3)
mk = _webtext.read(WEB / "js" / "campmark.js")
check("a second read of the campaign file asks for the owners again",
      "cfnStale()" in mk)
check("the words come from the Factions colouring, not a second reading",
      "/api/map/colouring?" in src and "code=faction" in src)

# ---------------------------------------------------------------------------
print("\n== 2) the layout, run for real in node ==")

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const ctx = {console, document: {createElement: () => ({getContext: () => null})},
             state: {cmap: null}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
// every letter one unit wide, so a word's length is its letter count
const measure = t => Array.from(t, () => 1);
const out = {};
// A map W x H of region colours; each case paints its own factions.
function run(name, W, H, paint, groups){
  const keys = new Int32Array(W * H);
  for(let y = 0; y < H; y++) for(let x = 0; x < W; x++) keys[y * W + x] = paint(x, y);
  const bandOf = new Map();
  groups.forEach((g, i) => bandOf.set(g.region, i));
  const labs = ctx.cfnLayout(keys, W, H, bandOf, groups, measure);
  out[name] = labs.map(L => ({key: L.key, text: L.text, mx: L.mx, my: L.my,
    ux: L.ux, uy: L.uy, c0: L.c0, c1: L.c1, c2: L.c2, h: L.h, straight: L.straight,
    w: L.unitW * L.h,
    pts: ctx.cfnChars(L).map(c => { const p = ctx.cfnAt(L, c.a); return [p.x, p.y]; })}));
}
const G = (key, region) => ({key, label: key, region, rgb: [200, 100, 50]});
// a level strip, 100 x 12, across the middle of a 140 x 60 map
run('level', 140, 60, (x, y) => (x >= 20 && x < 120 && y >= 24 && y < 36) ? 1 : 0,
    [G('Level', 1)]);
// the same strip tilted: x - 2y within a band
run('tilted', 160, 120, (x, y) => (Math.abs((y - 60) - (x - 80) * 0.5) < 6
                                   && x > 20 && x < 140) ? 1 : 0, [G('Tilted', 1)]);
// an arc: the ring between two circles, the top half
run('arc', 160, 120, (x, y) => {
  const r = Math.hypot(x - 80, y - 100);
  return (r > 60 && r < 74 && y < 100) ? 1 : 0;
}, [G('Arc', 1)]);
// a mainland and a bigger island's worth of nothing: the name goes on the
// mainland, the larger block, even though the island is nearer the corner
run('island', 160, 120, (x, y) => ((x >= 90 && x < 150 && y >= 40 && y < 80)
                                   || (x >= 5 && x < 20 && y >= 5 && y < 20)) ? 1 : 0,
    [G('Isle', 1)]);
// a speck, four tiles
run('speck', 40, 40, (x, y) => (x >= 18 && x < 20 && y >= 18 && y < 20) ? 1 : 0,
    [G('Speck', 1)]);
// a crowd: twelve stacked strips three tiles thick, so the names, which may
// overhang a thin land, are close enough that some must give way
run('crowd', 120, 40, (x, y) => (x >= 10 && x < 110 && y < 36) ? 1 + Math.floor(y / 3) : 0,
    Array.from({length: 12}, (_, i) => G('Faction' + String.fromCharCode(65 + i), i + 1)));
out.shown = [ctx.cfnShown({key: 'sicily', label: 'Kingdom of Gondor (sicily)'}),
             ctx.cfnShown({key: 'sicily', label: 'sicily'}),
             ctx.cfnShown({key: 'x', label: 'Name (with brackets)'})];
fs.writeFileSync(process.argv[3], JSON.stringify(out));
"""

node = shutil.which("node")
got = {}
if not node:
    print("  -- node is not on PATH, so the layout is not run")
else:
    with tempfile.TemporaryDirectory(prefix="ut_mapfactions_") as tmp:
        t = Path(tmp)
        (t / "h.js").write_text(HARNESS, encoding="utf-8")
        r = subprocess.run([node, str(t / "h.js"), str(JS), str(t / "out.json")],
                           capture_output=True, text=True)
        check("the harness runs", r.returncode == 0)
        if r.returncode:
            print(r.stdout or "", r.stderr or "")
        else:
            got = json.loads((t / "out.json").read_text(encoding="utf-8"))


def one(name):
    labs = got.get(name) or []
    return labs[0] if labs else None


def angle(L):
    return math.degrees(math.atan2(L["uy"], L["ux"]))


if got:
    L = one("level")
    check(f"a level strip is lettered level ({angle(L):.1f} degrees)",
          L and abs(angle(L)) < 1)
    check(f"  centred on the strip ({L['mx']:.1f}, {L['my']:.1f})",
          L and abs(L["mx"] - 70) < 1.5 and abs(L["my"] - 30) < 1.5)
    # 12 tiles thick, so the letters are held to the thickness and the word to
    # about 59 tiles of the 100; never past the 80 its length would allow
    check(f"  as tall as the strip lets it be, no longer than 80% of it "
          f"({L['h']:.1f} tall, {L['w']:.0f} of 100 long)",
          L and 8 <= L["h"] <= 12 * 1.3 and 40 <= L["w"] <= 80.0001)
    check("  and in capitals", L and L["text"] == "LEVEL")

    L = one("tilted")
    check(f"a tilted strip tilts the name with it ({angle(L):.1f}, the strip is 26.6)",
          L and abs(angle(L) - 26.57) < 3)

    L = one("arc")
    # the arc is the top of a ring centred below, so its ends are lower (larger
    # y) than its middle: in a frame whose b axis points down, c2 > 0
    ends = L and (L["pts"][0][1] + L["pts"][-1][1]) / 2
    mid = L and L["pts"][len(L["pts"]) // 2][1]
    check(f"an arc of land gets an arched name (ends {ends:.1f}, middle {mid:.1f})",
          L and not L["straight"] and ends - mid > 2)
    check("  but a gentle one: the sag no more than a fifth of its length",
          L and abs(L["c2"]) * (L["w"] / 2) ** 2 <= L["w"] * 0.2 + 1e-6)

    L = one("island")
    check(f"a faction with an island is lettered on its mainland ({L['mx']:.0f}, {L['my']:.0f})",
          L and 90 <= L["mx"] < 150 and 40 <= L["my"] < 80)

    L = one("speck")
    check("a speck of four tiles still gets its name, straight and level",
          L and L["straight"] and abs(angle(L)) < 1e-9)

    crowd = got.get("crowd") or []
    check(f"a crowd of twelve: some give way ({len(crowd)} placed)", 0 < len(crowd) < 12)
    pts = [(p, L["h"]) for L in crowd for p in L["pts"]]
    clash = 0
    for i, L in enumerate(crowd):
        for M in crowd[i + 1:]:
            r = (L["h"] + M["h"]) * 0.55
            if any(abs(a[0] - b[0]) < r and abs(a[1] - b[1]) < r
                   for a in L["pts"] for b in M["pts"]):
                clash += 1
    check("  and no two placed names cross", clash == 0)

    every = [L for k, v in got.items() if k != "shown" for L in v]
    check(f"no name on any map reads upside down ({len(every)} names)",
          all(L["ux"] > 0 for L in every))
    check("  or is steeper than 55 degrees",
          all(abs(angle(L)) <= 55.0001 for L in every))

    print("\n== 4) the name the player reads ==")
    s = got.get("shown") or []
    check("'Kingdom of Gondor (sicily)' is lettered 'Kingdom of Gondor'",
          s and s[0] == "Kingdom of Gondor")
    check("  a faction the mod gives no name keeps its code name", s and s[1] == "sicily")
    check("  and brackets that are part of the name stay", s and s[2] == "Name (with brackets)")

# ---------------------------------------------------------------------------
print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
