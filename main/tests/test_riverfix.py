"""Mylae's river Auto-Fix, as :mod:`unittransfer.riverfix`.

Shapes drawn by hand on a small grid, each with what the repair must and must
not do, then every installed map, where it may change only what the validator
reports.

    python -m tests.test_riverfix
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod
from unittransfer import mapcheck, riverfix
from unittransfer.campmap import CampaignMap
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


KEY = {".": (0, 0, 0), "~": (0, 0, 255), "S": (255, 255, 255), "F": (0, 255, 255),
       "C": (128, 128, 128)}       # C: some other feature (a cliff), never touched
BACK = {v: k for k, v in KEY.items()}


def grid(rows):
    w, h = len(rows[0]), len(rows)
    return b"".join(bytes(KEY[c]) for r in rows for c in r), w, h


def draw(data, w):
    return ["".join(BACK[tuple(data[3 * (y * w + x):3 * (y * w + x) + 3])]
                    for x in range(w)) for y in range(len(data) // 3 // w)]


def net(rows):
    """Components, loops, 2x2 blocks and each component's ends and sources."""
    data, w, h = grid(rows)
    g = riverfix.Grid(data, w, h)
    _, comps = g.components()
    loops = sum(max(0, sum(len(g.nb(n)) for n in c) // 2 - len(c) + 1) for c in comps)
    blocks = sum(1 for n in range(w * h) if g.mask[n] and n % w < w - 1 and n + w + 1 < w * h
                 and g.mask[n + 1] and g.mask[n + w] and g.mask[n + w + 1])
    return g, comps, loops, blocks


def run(rows, sea=None):
    data, w, h = grid(rows)
    out, n = riverfix.repair(data, w, h, sea)
    return draw(out, w), n


print("\n1) a clean network is left exactly as it is")
clean = ["S~~~~.",
         "....~.",
         "..C.~~",
         ".....~"]
got, n = run(clean)
check(f"nothing changes, got {n}", got == clean and not any(n.values()))

print("\n2) a river three tiles wide is thinned to one, ends and source kept")
thick = ["S~~~~~~.",
         ".~~~~~~.",
         ".~~~~~~~",
         "........"]
got, n = run(thick)
g, comps, loops, blocks = net(got)
check(f"one course, no loop, no block left ({n['thinned']} thinned, "
      f"{n['opened']} opened)", len(comps) == 1 and not loops and not blocks)
check("the source and the far end are where they were",
      got[0][0] == "S" and got[2][7] == "~")

print("\n3) an island in the river: one arm goes whole, not a hole in it")
island = ["S~~~~~..",
          ".~...~..",
          ".~~~~~~~",
          "........"]
got, n = run(island)
g, comps, loops, blocks = net(got)
check(f"no loop, one course, every original end kept: {got}",
      not loops and len(comps) == 1 and got[0][0] == "S" and got[2][7] == "~")
check("no stub left behind: the course has exactly two ends",
      sum(1 for n_ in comps[0] if len(g.nb(n_)) == 1) == 2)

print("\n4) a ring with a branch on every tile: the cheapest cut, sources kept")
ring = [".~.~.",
        "~~~~~",
        ".~.~.",
        "~~~~~",
        ".S.~."]
got, n = run(ring)
g, comps, loops, blocks = net(got)
check(f"the loop is open ({n['opened']} tile(s) removed): {got}", not loops)
check("the source survived", any("S" in r for r in got))

print("\n5) fords are kept on their course")
forded = ["S~F~~.",
          ".~~~~.",
          "......"]
got, n = run(forded)
g, comps, loops, blocks = net(got)
check(f"the block is gone and the ford is still on the course: {got}",
      not blocks and not loops and sum(r.count("F") for r in got) == 1)

print("\n6) a corner join is bridged through a blank tile, never through a feature")
corner = ["S~~...",
          "...~..",
          "......"]
got, n = run(corner)
check(f"bridged: {got}", n["joined"] == 1 and len(net(got)[1]) == 1)
blocked = ["S~~C..",
           "..C~..",
           "......"]
got, n = run(blocked)
check(f"with both bridge tiles a feature, nothing is joined or cleared: {got}",
      n["joined"] == 0 and got == blocked)
apart = ["S~~...",
         "...~~S",
         "......"]
got, n = run(apart)
check("two courses whose ends pass at a corner, each with a side neighbour, are "
      "two rivers and are left apart (river.diagonal does not report them)",
      got == apart and not any(n.values()))

print("\n7) a course with no source gets one at its inland end")
sea_rows = [".......", ".~~~~..", "......."]
data, w, h = grid(sea_rows)
sea = bytearray(w * h)
sea[1 * w + 5] = 1                           # the sea is just east of the east end
out, n = riverfix.repair(data, w, h, bytes(sea))
check(f"the source is at the west end, away from the sea: {draw(out, w)}",
      n["sources"] == 1 and draw(out, w)[1][1] == "S")
sea[1 * w + 5] = 0
sea[1 * w + 0] = 1                           # and now the sea is to the west
out, n = riverfix.repair(data, w, h, bytes(sea))
check(f"...and at the east end when the sea is west: {draw(out, w)}",
      draw(out, w)[1][4] == "S")

print("\n8) only river tiles ever change")
messy = ["S~~C~~.",
         "C~~~~C.",
         ".~~~~~~",
         "..C...."]
got, n = run(messy)
check("every cliff tile is where it was",
      all((a == "C") == (b == "C") for ra, rb in zip(messy, got) for a, b in zip(ra, rb)))

print("\n9) every installed map: only what the validator reports changes")
game = _realmod.MODS.parent
roots = ([game] if (game / "data").is_dir() else []) + _realmod.installed()
RIV = ("river.diagonal", "river.rejoin", "river.isolated", "river.no_source")
for root in roots:
    mod = Mod(root)
    try:
        cm = CampaignMap(mod)
        img = cm.layer("features").convert("RGB")
    except Exception as exc:                          # noqa: BLE001
        print(f"     {root.name}: no map ({type(exc).__name__})")
        continue
    ck = mapcheck.Check(mod, cm)
    before = sum(len(list(mapcheck.RULE_BY_CODE[c].fn(ck))) for c in RIV)
    raw = img.tobytes()
    out, n = riverfix.repair(raw, img.width, img.height, ck.sea)
    changed = sum(1 for i in range(0, len(raw), 3) if raw[i:i + 3] != out[i:i + 3])
    ck2 = mapcheck.Check(mod, cm)
    ck2._px["features"] = out
    after = sum(len(list(mapcheck.RULE_BY_CODE[c].fn(ck2))) for c in RIV)
    check(f"{root.name}: {before} river finding(s) before, {after} after, "
          f"{changed} tile(s) changed", after == 0 and changed <= max(before, 0) * 4)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
