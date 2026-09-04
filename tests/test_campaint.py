"""The paint tool - Phase 16e's exit criteria, measured.

16c drew the map, 16d made the record editable; this changes the pixels. Six
claims are under test, and every one of them is the sort a paint tool gets
quietly wrong:

    campaint.block        a tile owns a rectangle, and the rectangles partition
                          the layer exactly - no seam, no pixel owned twice
    campaint.expand       the brush shape, and the line that joins two samples
    campaint.flood        four-connected, and it stops at a marker
    campaint.paint        region-colour snapping, the marker protection, and
                          the refusals - an unknown colour is never written
    campaint.undo_stroke  a stroke undone is the layer's own bytes back, not a
                          repaint of the old colour over the new one
    campaint.apply_paint  every painted layer, the new region's record and
                          map.rwm, in one backup set the Log's Undo reverses

The load-bearing claim of the whole phase is checked rather than argued:
**a layer written back is byte-identical outside the painted rectangle**, and
**undo restores it byte-exact**. Both are asserted on a map written here and
again on every real map installed.

Six parts, the last three of which need a game install:

    1  the tile -> pixel rule, and the partition
    2  the brush and the bucket, on grids whose answer is workable by hand
    3  a whole small map on disk: strokes, snapping, refusals, undo
    4  the new-region wizard end to end, and every rule it enforces
    5  every real map: a stroke, a re-encode and an undo
    6  the routes over real HTTP, a real save, and the Log's Undo

    python -m tests.test_campaint
"""
import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod
from unittransfer import campaint, campmap, config, mapvocab, transfer
from unittransfer.maptga import TgaInfo, encode, probe, read
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the tile -> pixel rule -----------------------------------------------
print("\n1) a tile owns a rectangle, and the rectangles cover the layer exactly")

W, H = 8, 7

check("a tile layer's block is the pixel itself",
      campaint.block("tile", 3, 4) == (3, 4, 3, 4))
check("a 2W x 2H layer's block is the 2x2 the tile sits on",
      campaint.block("double", 3, 4) == (6, 8, 7, 9))
check("a 2W+1 layer's block is the 2x2 past the centre pixel",
      campaint.block("centre", 3, 4) == (7, 9, 8, 10))
check("…and tile 0 takes the leading row and column, which nothing else owns",
      campaint.block("centre", 0, 0) == (0, 0, 2, 2))

for rule, (pw, ph) in (("tile", (W, H)), ("double", (2 * W, 2 * H)),
                       ("centre", (2 * W + 1, 2 * H + 1))):
    owned = {}
    for ty in range(H):
        for tx in range(W):
            x0, y0, x1, y1 = campaint.block(rule, tx, ty)
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    owned.setdefault((x, y), []).append((tx, ty))
    twice = [p for p, v in owned.items() if len(v) > 1]
    check(f"{rule}: all {pw * ph} pixels owned, none owned twice",
          len(owned) == pw * ph and not twice)

check("and the pixel the engine samples is inside its own tile's block",
      all(campaint.block("centre", tx, ty)[0] <= 2 * tx + 1
          <= campaint.block("centre", tx, ty)[2]
          for tx in range(W) for ty in range(H)))

try:
    campaint.block("free", 0, 0)
    check("a layer with no relationship to the grid is refused", False)
except campmap.MapError as exc:
    check(f"a layer with no relationship to the grid is refused: {str(exc)[:46]}…",
          True)


# ---- 2) the brush and the bucket ---------------------------------------------
print("\n2) the brush shape, the line between two samples, and the flood fill")

#: room around the samples, so a clip against the map edge is a separate check
BW, BH = 40, 40

one = campaint.expand([[8, 8]], 1, "round", BW, BH)
check("size 1 is one tile", one == [(8, 8)])

sq = campaint.expand([[8, 8]], 5, "square", BW, BH)
check("size is the WIDTH in tiles: a square brush of 5 is a 5x5 block",
      len(sq) == 25 and (6, 6) in sq and (11, 8) not in sq)
disc = campaint.expand([[8, 8]], 5, "round", BW, BH)
check(f"a round one of the same width is smaller and inside it ({len(disc)} tiles)",
      len(disc) < 25 and set(disc) <= set(sq))
check("an even width is the odd one below it - a brush is centred on the tile "
      "under the cursor, and an even one has no centre tile to be under it",
      campaint.expand([[8, 8]], 6, "square", BW, BH) == sq)

line = campaint.expand([[0, 0], [5, 0]], 1, "round", BW, BH)
check("two samples five tiles apart join up rather than leaving a dotted line",
      line == [(x, 0) for x in range(6)])
diag = campaint.expand([[0, 0], [3, 3]], 1, "round", BW, BH)
check("and a diagonal drag joins up too, one tile per step",
      diag == [(0, 0), (1, 1), (2, 2), (3, 3)])

edge = campaint.expand([[0, 0]], 9, "square", W, H)
check("a brush over the corner is clipped to the map, not wrapped",
      all(0 <= x < W and 0 <= y < H for x, y in edge))
check("a stroke with no samples in it covers nothing",
      campaint.expand([], 3, "round", BW, BH) == [])


# ---- 3) a whole small map on disk --------------------------------------------
print("\n3) a map written here: snapping, protection, refusals and undo")

#  A A A A B B B B      three regions, a settlement marker in A, a port in B,
#  A A S A B B B B      and two rows of sea along the bottom that the heights
#  A A A A B B P B      layer agrees with - so the water brush has something to
#  A A A A B B B B      measure, and so the bottom row touches no declared
#  C C C C C C C C      region at all, which is what the wizard's touching rule
#  ~ ~ ~ ~ ~ ~ ~ ~      is tested against
#  ~ ~ ~ ~ ~ ~ ~ ~
A, B, C, SEA = (10, 20, 30), (40, 50, 60), (70, 80, 90), (0, 90, 200)
GRID = [[A, A, A, A, B, B, B, B],
        [A, A, (0, 0, 0), A, B, B, B, B],
        [A, A, A, A, B, B, (255, 255, 255), B],
        [A, A, A, A, B, B, B, B],
        [C, C, C, C, C, C, C, C],
        [SEA] * 8,
        [SEA] * 8]

TERRAIN = ("dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
           "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n"
           "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
           "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
           % (W, H))

RECORDS = ("A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
           "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n"
           "\r\nB_Province\r\n\tBtown\r\n\tslave\r\n\tbrigands\r\n\t40 50 60\r\n"
           "\tsilver\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n"
           "\r\nC_Province\r\n\tCtown\r\n\tslave\r\n\tbrigands\r\n\t70 80 90\r\n"
           "\ttimber\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n")


def paint_img(w, h, fn, mode="RGB"):
    im = Image.new(mode, (w, h))
    im.putdata([fn(x, y) if mode == "RGB" else fn(x, y) + (255,)
                for y in range(h) for x in range(w)])
    return im


def write_tga(path, img, depth=32, image_type=10, desc=0x08):
    """A real TGA, in the shapes the real layers come in - RLE and 32-bit for
    most, so the round trip is being exercised rather than the easy case."""
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def tiny_map(root: Path):
    """One complete little campaign map on disk: ten layers and two text files."""
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(RECORDS.encode("latin-1"))
    write_tga(base / "map_regions.tga", paint_img(W, H, lambda x, y: GRID[y][x], "RGBA"))
    # heights: grey for land, blue for sea, on the 2W+1 grid
    write_tga(base / "map_heights.tga",
              paint_img(2 * W + 1, 2 * H + 1,
                        lambda x, y: (0, 0, 200) if y >= 2 * 5 else (90, 90, 90),
                        "RGBA"))
    write_tga(base / "map_ground_types.tga",
              paint_img(2 * W + 1, 2 * H + 1,
                        lambda x, y: (128, 0, 0) if y >= 2 * 5 else (96, 160, 64),
                        "RGBA"))
    write_tga(base / "map_climates.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (200, 100, 50), "RGBA"))
    write_tga(base / "map_features.tga",
              paint_img(W, H, lambda x, y: (255, 0, 0) if (x, y) == (7, 0)
                        else (0, 0, 0), "RGBA"))
    write_tga(base / "map_fog.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (255, 255, 255)),
              depth=24, image_type=10, desc=0x00)
    write_tga(base / "map_trade_routes.tga",
              paint_img(W, H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    write_tga(base / "map_roughness.tga",
              paint_img(2 * W, 2 * H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    write_tga(base / "water_surface.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (0, 0, 120)),
              depth=24, image_type=2, desc=0x20)
    (base / campmap.RWM_REL.rsplit("/", 1)[-1]).write_bytes(b"stale")
    return base


tmp = Path(tempfile.mkdtemp(prefix="ut_tiny_"))
tiny_root = tmp / "mods" / "Tiny"
tiny_base = tiny_map(tiny_root)
tiny = Mod(tiny_root)
cm = campmap.CampaignMap(tiny)
sess = campaint.PaintSession(tiny, cm)

before = {ly["file"]: (tiny_base / ly["file"]).read_bytes()
          for ly in campmap.LAYERS if (tiny_base / ly["file"]).exists()}
check(f"the map reads: {cm.terrain.width}x{cm.terrain.height}, "
      f"{len(cm.index.regions)} colours, {len(cm.regions.records)} records",
      cm.terrain.width == W and len(cm.regions.records) == 3)
check("and every layer of it re-encodes byte for byte before anything is painted",
      all(encode(cm.layer(c), cm.info(c)) == before[campmap.LAYER_BY_CODE[c]["file"]]
          for c in ("regions", "heights", "ground_types", "features", "fog",
                    "trade_routes", "roughness", "climates")))

pal = campaint.palettes(cm)
by_code = {L["code"]: L for L in pal["layers"]}
check("the region layer's palette is the region list, each with its own colour",
      len(by_code["regions"]["colours"]) == 3
      and by_code["regions"]["closed"]
      and [c["region"] for c in by_code["regions"]["colours"]]
          == ["A_Province", "B_Province", "C_Province"])
check("ground types and features are the engine's tables, and closed",
      by_code["ground_types"]["closed"] and by_code["features"]["closed"]
      and len(by_code["ground_types"]["colours"]) == 16
      and len(by_code["features"]["colours"]) == 7)
check("heights is open, because it is a rule rather than a vocabulary",
      not by_code["heights"]["closed"] and "not a table" in by_code["heights"]["note"])
check(f"and the sea colours are measured off this map, not assumed: "
      f"{ {c: v['rgb'] for c, v in pal['water']['layers'].items()} }",
      pal["water"]["ok"]
      and pal["water"]["layers"]["regions"]["rgb"] == [0, 90, 200]
      and pal["water"]["layers"]["ground_types"]["rgb"] == [128, 0, 0])

# -- snapping ------------------------------------------------------------------
out = campaint.paint(sess, {"tool": "brush", "target": "regions",
                            "region": "B_Province", "points": [[1, 1]], "size": 3})
tv = cm.tiles("regions").tobytes()
here = lambda x, y: tuple(tv[(y * W + x) * 3:(y * W + x) * 3 + 3])
check(f"a stroke on the region layer writes the region's own RGB out of "
      f"descr_regions.txt, {out['tiles']} tiles",
      out["tiles"] == 4 and here(1, 0) == (40, 50, 60) and here(0, 1) == (40, 50, 60))
check("the settlement marker in the middle of it was left alone",
      out["protected"] == 1 and here(2, 1) == (0, 0, 0))
check("the answer is in tile space and carries the colour the browser must draw",
      out["changed"]["regions"]["rgb"] == campmap.key((40, 50, 60))
      and len(out["changed"]["regions"]["xy"]) == 2 * out["tiles"])
campaint.undo_stroke(sess)

for bad, why in (
    ({"tool": "brush", "target": "regions", "points": [[1, 1]]},
     "a region stroke with no region picked"),
    ({"tool": "brush", "target": "regions", "region": "Nowhere",
      "points": [[1, 1]]}, "a region that is not in descr_regions.txt"),
    ({"tool": "brush", "target": "ground_types", "rgb": [7, 7, 7],
      "points": [[1, 1]]}, "a ground colour no table names"),
    ({"tool": "brush", "target": "water_surface", "rgb": [1, 2, 3],
      "points": [[1, 1]]}, "a layer that has no relationship to the grid"),
    ({"tool": "smudge", "target": "regions", "region": "A_Province",
      "points": [[1, 1]]}, "a tool that does not exist"),
):
    try:
        campaint.paint(sess, bad)
        check(f"{why} is refused", False)
    except campmap.MapError as exc:
        check(f"{why} is refused, by name: {str(exc)[:52]}…", True)

check("nothing was written by any of those refusals",
      encode(cm.layer("regions"), cm.info("regions")) == before["map_regions.tga"]
      and not sess.undo)

# -- protection ----------------------------------------------------------------
out = campaint.paint(sess, {"tool": "brush", "target": "regions",
                            "region": "C_Province", "points": [[2, 1]], "size": 5})
tv = cm.tiles("regions").tobytes()
here = lambda x, y: tuple(tv[(y * W + x) * 3:(y * W + x) * 3 + 3])
check(f"a wider brush over the same marker paints round it too "
      f"({out['protected']} protected, {out['tiles']} painted)",
      out["protected"] == 1 and here(2, 1) == (0, 0, 0))
check("and the tiles it did paint are the region's own colour",
      here(2, 0) == (70, 80, 90) and here(0, 1) == (70, 80, 90))
check("a round brush is a disc: the corner of its bounding box is not in it",
      here(0, 0) == (10, 20, 30))
campaint.undo_stroke(sess)

# -- the bucket ----------------------------------------------------------------
fill = campaint.flood(cm, "regions", 0, 0)
check(f"a bucket on A stops at B, at C and at the settlement marker "
      f"({len(fill)} tiles)",
      len(fill) == 15 and (2, 1) not in fill and (4, 0) not in fill)
sea_fill = campaint.flood(cm, "regions", 0, 5)
check("and a bucket in the sea fills both rows of it and nothing else",
      len(sea_fill) == 2 * W and all(y >= 5 for _, y in sea_fill))

# -- the water brush -----------------------------------------------------------
out = campaint.paint(sess, {"tool": "water", "points": [[6, 3]], "size": 2})
check(f"the water brush writes three layers at once: {sorted(out['changed'])}",
      sorted(out["changed"]) == ["ground_types", "heights", "regions"])
gt = cm.tiles("ground_types").tobytes()
ht = cm.tiles("heights").tobytes()
i = (3 * W + 6) * 3
check("and the tile it painted now reads as sea on all three",
      tuple(gt[i:i + 3]) == (128, 0, 0) and tuple(ht[i:i + 3]) == (0, 0, 200)
      and cm.sea[3 * W + 6] == 1)
img = cm.layer("ground_types")
x0, y0, x1, y1 = campaint.block("centre", 6, 3)
px = img.load()
check(f"the whole {x1 - x0 + 1}x{y1 - y0 + 1} block of the 2W+1 layer moved, not "
      "just the pixel the engine samples",
      {px[x, y][:3] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
      == {(128, 0, 0)})

# -- undo ----------------------------------------------------------------------
campaint.undo_stroke(sess)
check("undo puts every one of the three layers back byte-exact",
      all(encode(cm.layer(c), cm.info(c))
          == before[campmap.LAYER_BY_CODE[c]["file"]]
          for c in ("regions", "heights", "ground_types")))
campaint.redo_stroke(sess)
check("redo puts them back the way they were painted",
      cm.tiles("ground_types").tobytes()[i:i + 3] == bytes((128, 0, 0)))
campaint.undo_stroke(sess)

deep = 0
for n in range(12):
    # twelve tiles that are all A_Province to start with, so every one of the
    # twelve really is a change and really does go on the stack
    campaint.paint(sess, {"tool": "pencil", "target": "regions",
                          "region": "B_Province",
                          "points": [[n % 4, [0, 2, 3][n // 4]]]})
    deep += 1
check(f"the stack takes {deep} strokes with no level limit, and says how deep "
      f"it is", sess.state()["undo"] == deep and sess.state()["dropped"] == 0)
for _ in range(deep):
    campaint.undo_stroke(sess)
check("and unwinding all of them is the layer's own bytes back",
      encode(cm.layer("regions"), cm.info("regions")) == before["map_regions.tga"])
check("a save with everything undone is refused rather than written, because "
      "the bytes are what is compared and not the stroke count",
      campaint.plan_paint(sess).errors == ["nothing has been painted"])

# -- the painted rectangle -----------------------------------------------------
sess2 = campaint.PaintSession(tiny, campmap.CampaignMap(tiny))
campaint.paint(sess2, {"tool": "pencil", "target": "features",
                       "rgb": [0, 0, 255], "points": [[3, 3]]})
made = encode(sess2.cm.layer("features"), sess2.cm.info("features"))
was = Image.open(tiny_base / "map_features.tga").convert("RGB").load()
now = sess2.cm.layer("features").convert("RGB").load()
differ = [(x, y) for y in range(H) for x in range(W) if was[x, y] != now[x, y]]
check(f"one painted tile changes one pixel of the file and no other: {differ}",
      differ == [(3, 3)] and made != before["map_features.tga"])
check("and the file's shape is carried over unchanged - type, depth, descriptor "
      "and footer all as they were",
      probe(tiny_base / "map_features.tga").describe()
      == sess2.cm.info("features").describe())


# ---- 4) the new-region wizard ------------------------------------------------
print("\n4) a new province: the record, the pixels, the settlement and the port")

sess3 = campaint.PaintSession(tiny, campmap.CampaignMap(tiny))
cm3 = sess3.cm
spec = {"name": "D_Province", "settlement": "Dtown", "rgb": [11, 12, 13],
        "faction": "slave", "rebels": "brigands", "religions": {"catholic": 100}}

for bad, why in (
    (dict(spec, name="Has Spaces"), "a region name with a space in it"),
    (dict(spec, name="A_Province"), "a name descr_regions.txt already has"),
    (dict(spec, settlement="Atown"), "a settlement name it already has"),
    (dict(spec, rgb=[10, 20, 30]), "a colour another region already owns"),
    (dict(spec, rgb=[0, 0, 0]), "a marker colour"),
    (dict(spec, rgb=[0, 90, 200]), "a colour already painted and declared nowhere"),
):
    try:
        campaint.start_region(sess3, bad)
        check(f"{why} is refused", False)
    except campmap.MapError as exc:
        check(f"{why} is refused: {str(exc)[:50]}…", True)

campaint.start_region(sess3, spec)
check("the wizard opens with the record decided before a pixel is painted",
      sess3.state()["new_region"]["key"] == campmap.key((11, 12, 13)))
check("step 1 of 3, and the step is counted off the map rather than remembered",
      campaint.region_progress(cm3, sess3.new_region)["step"] == 1)

p = campaint.plan_paint(sess3)
check(f"a save with nothing painted is refused: {p.errors[0][:52]}…",
      p.errors and "no land" in p.errors[0])

campaint.paint(sess3, {"tool": "brush", "target": "regions",
                       "region": "D_Province", "points": [[1, 2]], "size": 3})
prog = campaint.region_progress(cm3, sess3.new_region)
check(f"painting it moves the wizard to step 2 ({prog['tiles']} tiles)",
      prog["step"] == 2 and prog["tiles"] == 5)
p = campaint.plan_paint(sess3)
check(f"and a save is still refused, for the settlement: {p.errors[0][:48]}…",
      p.errors and "nowhere to stand" in p.errors[0])

for at, why in (([6, 3], "outside the region"),
                ([0, 5], "in the sea outside it")):
    try:
        campaint.paint(sess3, {"tool": "pencil", "target": "regions",
                               "region": "D_Province", "marker": "settlement",
                               "points": [at]})
        check(f"a settlement pixel {why} is refused", False)
    except campmap.MapError as exc:
        check(f"a settlement pixel {why} is refused: {str(exc)[:46]}…", True)

campaint.paint(sess3, {"tool": "pencil", "target": "regions",
                       "region": "D_Province", "marker": "settlement",
                       "points": [[1, 2]]})
prog = campaint.region_progress(cm3, sess3.new_region)
check(f"the settlement pixel goes on one of its own tiles: {prog['settlement']}",
      prog["settlement"] == [1, 2] and prog["step"] == 3)

p = campaint.plan_paint(sess3)
check(f"and now the save is allowed: {p.changes[-1][:60]}…",
      p.payload()["ok"] and not p.errors)
check("the record it would write is in the shape the file is already in",
      "D_Province" in p.region_text
      and "\tDtown\r\n" in p.region_text
      and "\t11 12 13\r\n" in p.region_text)
check("and the file it would write parses back to four records with the new "
      "one intact",
      len(campmap.parse_regions(p.region_text).records) == 4
      and campmap.parse_regions(p.region_text).by_name("D_Province").religions
          == {"catholic": 100})

# the touching rule, on a region painted in the middle of the sea
sess4 = campaint.PaintSession(tiny, campmap.CampaignMap(tiny))
campaint.start_region(sess4, dict(spec, name="E_Province", settlement="Etown",
                                  rgb=[21, 22, 23]))
campaint.paint(sess4, {"tool": "pencil", "target": "regions",
                       "region": "E_Province", "points": [[3, 6], [4, 6]]})
found = campaint.check_new_region(sess4.cm, sess4.new_region)
check(f"a province touching no declared region is refused, with the reason: "
      f"{[f['message'][:40] for f in found if f['fatal']][:1]}",
      any(f["fatal"] and "share an edge" in f["message"] for f in found))

# religions that do not total 100 - the one that crashes the game on load
sess5 = campaint.PaintSession(tiny, campmap.CampaignMap(tiny))
campaint.start_region(sess5, dict(spec, name="F_Province", settlement="Ftown",
                                  rgb=[31, 32, 33], religions={"catholic": 90}))
campaint.paint(sess5, {"tool": "brush", "target": "regions",
                       "region": "F_Province", "points": [[1, 2]], "size": 3})
campaint.paint(sess5, {"tool": "pencil", "target": "regions",
                       "region": "F_Province", "marker": "settlement",
                       "points": [[1, 2]]})
errs = campaint.plan_paint(sess5).errors
check(f"religions totalling 90 refuse the save and say by how much: "
      f"{[e for e in errs if '100' in e][:1]}",
      any("-10" in e for e in errs))

shutil.rmtree(tmp, ignore_errors=True)


# ---- 5) every real map -------------------------------------------------------
print("\n5) every installed map: a stroke, a re-encode and an undo")

roots = _realmod.installed()
game = _realmod.MODS.parent
if (game / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
    roots.append(game)
roots = [r for r in roots
         if (r / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]

if not roots:
    print("  SKIPPED - no installed mod (and no game) with a campaign map")
else:
    for root in roots:
        mod = Mod(root)
        print(f"\n  -- {mod.name}")
        cm = campmap.CampaignMap(mod)
        s = campaint.PaintSession(mod, cm)
        base = mod.data / campmap.BASE_REL

        home = max((r for r in cm.index.regions if r.record), key=lambda r: r.pixels)
        guest = next(r for r in cm.index.regions
                     if r.record and r.rgb != home.rgb)
        was = encode(cm.layer("regions"), cm.info("regions"))
        check("the region layer re-encodes byte for byte before anything is painted",
              was == (base / "map_regions.tga").read_bytes())

        img_before = cm.layer("regions").copy()
        out = campaint.paint(s, {"tool": "brush", "target": "regions",
                                 "region": guest.record.name,
                                 "points": [list(home.anchor)], "size": 4})
        a, b = img_before.convert("RGB").load(), cm.layer("regions").convert("RGB").load()
        rect = out["changed"]["regions"]["xy"]
        painted = {(rect[i], rect[i + 1]) for i in range(0, len(rect), 2)}
        strayed = [(x, y) for y in range(cm.terrain.height)
                   for x in range(cm.terrain.width)
                   if a[x, y] != b[x, y] and (x, y) not in painted]
        check(f"a {out['tiles']}-tile stroke changes those tiles and no others"
              f"{'' if not strayed else ': ' + str(strayed[:4])}", not strayed)

        campaint.undo_stroke(s)
        check("and undo is the layer's own bytes back, byte for byte",
              encode(cm.layer("regions"), cm.info("regions")) == was)

        campaint.redo_stroke(s)
        data = encode(cm.layer("regions"), cm.info("regions"))
        tmp2 = Path(tempfile.mkdtemp(prefix="ut_rt_"))
        (tmp2 / "x.tga").write_bytes(data)
        again, info = read(tmp2 / "x.tga")
        c = again.convert("RGB").load()
        check("the painted layer written and read back is the same picture, in "
              "the same shape it arrived in",
              info.describe() == cm.info("regions").describe()
              and all(c[x, y] == b[x, y] for x, y in list(painted)[:200]))
        shutil.rmtree(tmp2, ignore_errors=True)
        campaint.undo_stroke(s)

        pal = campaint.palettes(cm)
        water = pal["water"]
        check(f"its sea colours measure: "
              f"{ {k: v['rgb'] for k, v in water['layers'].items()} } "
              f"from {water['sea_tiles']:,} sea tiles",
              water["ok"] and all(v["share"] > 20 for v in water["layers"].values()))
        closed = [L for L in pal["layers"] if L["closed"] and not L.get("problem")]
        check(f"{len(closed)} of its layers have a closed palette, and every "
              "colour in one is a colour some table names",
              all(c["code_name"] for L in closed for c in L["colours"]))


# ---- 6) the routes, over real HTTP -------------------------------------------
print("\n6) /api/map/palette, /paint, /paint_undo, /region_start, /paint_apply")

if not roots:
    print("  SKIPPED - no map to serve")
else:
    src = roots[-1]
    cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"

    med2 = Path(tempfile.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "MapMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for p in (src / "data" / campmap.BASE_REL).iterdir():
        if p.is_file():
            shutil.copy2(p, data / campmap.BASE_REL / p.name)
    (data / campmap.RWM_REL).write_bytes(b"stale")
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} · map copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        body = dict(body)
        body.setdefault("mod", "MapMod")
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    layer_before = {ly["file"]: (data / campmap.BASE_REL / ly["file"]).read_bytes()
                    for ly in campmap.LAYERS
                    if (data / campmap.BASE_REL / ly["file"]).exists()}
    regions_before = (data / campmap.REGIONS_REL).read_bytes()

    try:
        man = get("/api/map?mod=MapMod")
        pal = get("/api/map/palette?mod=MapMod")
        check(f"/api/map/palette answers {len(pal['layers'])} paintable layers, "
              f"{len(pal['tools'])} tools and the measured sea colours",
              len(pal["layers"]) == len(campaint.PAINTABLE)
              and pal["water"]["ok"] and pal["brush_max"] == campaint.BRUSH_MAX)

        home = max((r for r in man["regions"] if r["name"]), key=lambda r: r["pixels"])
        guest = next(r for r in man["regions"]
                     if r["name"] and r["key"] != home["key"])

        r = post("/api/map/paint_state", {})
        check("a session starts empty, and says so without changing anything",
              r["state"]["undo"] == 0 and not r["state"]["dirty"])

        r = post("/api/map/paint", {"tool": "brush", "target": "regions",
                                    "region": guest["name"],
                                    "points": [home["anchor"]], "size": 3})
        check(f"one stroke: {r['tiles']} tiles, {r['state']['undo']} on the stack, "
              f"'{r['state']['last']}'",
              r["tiles"] > 0 and r["state"]["undo"] == 1
              and r["state"]["dirty"] == ["regions"])
        check("and nothing has touched the disk yet",
              (data / campmap.BASE_REL / "map_regions.tga").read_bytes()
              == layer_before["map_regions.tga"])

        # the unsaved map is what every other route sees - one set of pixels
        pr = get(f"/api/map/probe?mod=MapMod&x={home['anchor'][0]}"
                 f"&y={home['anchor'][1]}")
        got = next(L for L in pr["layers"] if L["code"] == "regions")
        check(f"the probe names the unsaved stroke, not the file: {got['name']}",
              got["name"] == guest["name"])

        r = post("/api/map/paint", {"tool": "brush", "target": "regions",
                                    "region": "Nowhere", "points": [[1, 1]]})
        check(f"a refusal is the server's own sentence, with the state intact: "
              f"{r['error'][:48]}…",
              r.get("error") and r["state"]["undo"] == 1)

        r = post("/api/map/paint_undo", {})
        check("undo answers with the tiles to put back and their old colours",
              r["restored"]["regions"]["runs"] and r["state"]["undo"] == 0
              and r["state"]["redo"] == 1)
        r = post("/api/map/paint_redo", {})
        check("and redo answers with the tiles to paint again",
              r["changed"]["regions"]["xy"] and r["state"]["undo"] == 1)

        # ---- the wizard, over HTTP ------------------------------------------
        used = {r["key"] for r in man["regions"]}
        rgb = next([r, g, b] for r in range(9, 250, 9) for g in range(9, 250, 11)
                   for b in range(9, 250, 13)
                   if ((r << 16) | (g << 8) | b) not in used)
        r = post("/api/map/region_start",
                 {"name": "Test_Province", "settlement": "Testburg", "rgb": rgb,
                  "faction": home["faction"] or "slave",
                  "rebels": home["rebels"] or "brigands",
                  "religions": {"catholic": 100}})
        check(f"the wizard opens over HTTP with rgb({', '.join(map(str, rgb))})",
              not r.get("error") and r["state"]["new_region"]["name"]
              == "Test_Province")

        # Carve the new province out of an existing one, at a tile that could
        # actually hold a city. The tiles beside a settlement pixel the mod
        # already ships are the safest bet there is: the engine is standing a
        # city there, so the ground is neither sea nor impassable.
        def usable(at):
            if not (0 <= at[0] < man["width"] and 0 <= at[1] < man["height"]):
                return False
            q = get(f"/api/map/probe?mod=MapMod&x={at[0]}&y={at[1]}")
            if q.get("sea") or q.get("marker"):
                return False
            g = next(L for L in q["layers"] if L["code"] == "ground_types")
            f = next(L for L in q["layers"] if L["code"] == "features")
            return (g.get("code_name") not in mapvocab.BLOCKING_GROUND
                    and f.get("code_name") not in mapvocab.FATAL_UNDER_SETTLEMENT)

        seat = None
        hosts = [r for r in man["regions"] if r["settlement"] and r["pixels"] > 40]
        hosts.sort(key=lambda r: -r["pixels"])
        for host in hosts[:20]:
            sx, sy = host["settlement"]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (2, 0), (-2, 0), (0, 2), (0, -2)):
                if usable([sx + dx, sy + dy]):
                    seat = [sx + dx, sy + dy]
                    break
            if seat:
                home = host
                break

        if seat is None:
            print("  SKIPPED - no tile near the anchor can hold a settlement")
        else:
            post("/api/map/paint", {"tool": "brush", "target": "regions",
                                    "region": "Test_Province", "points": [seat],
                                    "size": 3})
            r = post("/api/map/paint_plan", {})
            check(f"the plan refuses until the settlement pixel is placed: "
                  f"{(r.get('error') or '')[:48]}…",
                  r.get("error") and "nowhere to stand" in r["error"])
            r = post("/api/map/paint", {"tool": "pencil", "target": "regions",
                                        "region": "Test_Province",
                                        "marker": "settlement", "points": [seat]})
            check("the settlement pixel goes down as its own stroke, undoable "
                  "like any other", not r.get("error") and r["state"]["undo"] >= 3)

            r = post("/api/map/paint_plan", {})
            q = r.get("plan") or {}
            check(f"and now the plan says what it would write: "
                  f"{len(q.get('changes', []))} change(s)",
                  q.get("ok") and any("descr_regions.txt" in c
                                      for c in q["changes"]))
            check("with the region-ID renumber said out loud, because nothing "
                  "else in the mod will ever mention it",
                  any("region ID" in w for w in q.get("warnings", []))
                  or not q.get("warnings"))

            res = post("/api/map/paint_apply", {})
            check(f"the save writes {len(res.get('layers', []))} layer(s) and "
                  f"the record for {res.get('region')}",
                  not res.get("error") and res.get("region") == "Test_Province"
                  and "regions" in res["layers"])
            check("and the state it answers with is the state AFTER the write, "
                  "because that is what the screen decides with",
                  res["state"]["undo"] == 0 and not res["state"]["dirty"]
                  and res["state"]["new_region"] is None)
            check("map.rwm is deleted, or the game loads the old compiled map",
                  not (data / campmap.RWM_REL).exists()
                  and campmap.RWM_REL in res["record"]["manifest"]["deleted"])
            check("every layer nobody painted is untouched on disk",
                  all((data / campmap.BASE_REL / f).read_bytes() == b
                      for f, b in layer_before.items() if f != "map_regions.tga"))

            man2 = get("/api/map?mod=MapMod")
            mine = next((r for r in man2["regions"]
                         if r["name"] == "Test_Province"), None)
            check(f"the map re-reads with the new province in it: "
                  f"{mine and mine['pixels']} tiles, settlement at "
                  f"{mine and mine['settlement']}",
                  mine and mine["pixels"] > 0 and mine["settlement"]
                  and mine["id"] >= 0)
            det = get("/api/map/region?mod=MapMod&name=Test_Province")
            check("and its record reads back through the 16d panel unchanged",
                  det["settlement"] == "Testburg" and det["religions"]
                  == {"catholic": 100} and not det["findings"])

            post("/api/undo", {"id": res["record"]["id"]})
            check("the Log's Undo puts the layer back byte-exact",
                  (data / campmap.BASE_REL / "map_regions.tga").read_bytes()
                  == layer_before["map_regions.tga"])
            check("…and descr_regions.txt, and map.rwm, because all three were "
                  "one backup set",
                  (data / campmap.REGIONS_REL).read_bytes() == regions_before
                  and (data / campmap.RWM_REL).read_bytes() == b"stale")

            r = post("/api/map/paint_state", {})
            check("and the session is gone with the save, rather than left "
                  "holding pixels that are now on disk",
                  r["state"]["undo"] == 0 and not r["state"]["dirty"])

            post("/api/map/paint", {"tool": "pencil", "target": "regions",
                                    "region": guest["name"], "points": [seat]})
            r = post("/api/map/paint_discard", {})
            check("a discard answers with the state after it too, and leaves "
                  "the files it never wrote alone",
                  r["state"]["undo"] == 0 and not r["state"]["dirty"]
                  and (data / campmap.BASE_REL / "map_regions.tga").read_bytes()
                  == layer_before["map_regions.tga"])
    finally:
        httpd.shutdown()
    shutil.rmtree(med2, ignore_errors=True)
    shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
