"""The layer generators - Phase 27's exit criteria, measured.

Nothing here touches the network. Phase 25's rule stands: sending anything to
the real servers is the user's switch to throw. The two generators that use the
network are fed synthetic elevation tiles and a synthetic Overpass answer, laid
over a map written here, and what they make is judged by the validator:

    heights    land where the map has land, at the engine's own scale, sea left
               alone; the whole map writes real depths into the blue
    ground     each land corner typed by its band, sea left alone
    climates   each ground type's climate, or left and said when the mod has
               none of that name
    features   rivers the validator has nothing to say about: cardinal steps,
               no loops, a source each, cut at a city, a tributary joined

and each writes one file with one Undo.

    python -m tests.test_mapgen
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image

import io

from tests import _realmod, _tmp
from unittransfer import (campmap, campstrat, config, mapcheck, mapgen, mapresize,
                          mapvocab, osmmap, transfer)
from unittransfer.maptga import TgaInfo, encode, read
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

# ---- the fixture: 60x40, land from 4 to 55 across and 4 to 31 down ----------
W, H = 60, 40
A, B, SEA = (10, 20, 30), (40, 50, 60), (41, 140, 233)
MARK = mapvocab.SETTLEMENT_RGB
SEATS = [(15, 18), (44, 18)]


def is_land(x, y):
    return 4 <= x <= 55 and 4 <= y <= 31


def region_px(x, y):
    if (x, y) in SEATS:
        return MARK
    if not is_land(x, y):
        return SEA
    return A if x < 30 else B


def write_tga(path, img, depth=24, image_type=2, desc=0x20):
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def img_of(w, h, fn):
    im = Image.new("RGB", (w, h))
    im.putdata([fn(x, y) for y in range(h) for x in range(w)])
    return im


def corner_land(vx, vy):
    return is_land(max(0, (vx - 1) // 2), max(0, (vy - 1) // 2))


TERRAIN = ("dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
           "\tmin_sea_height  -1000.000\n\tmax_land_height  3000.000\n}\n"
           "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
           "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
           % (W, H))
RECORDS = ("A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
           "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n\r\n"
           "B_Province\r\n\tBtown\r\n\tslave\r\n\tbrigands\r\n\t40 50 60\r\n"
           "\tsilver\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n")
CLIMATES = ("climates\n{\n\tmediterranean\n\talpine\n\thighland\n}\n"
            "climate mediterranean\n{\n\tcolour 236 0 140\n\theat 3\n}\n"
            "climate alpine\n{\n\tcolour 57 181 74\n\theat 1\n}\n"
            "climate highland\n{\n\tcolour 141 198 63\n\theat 2\n}\n")
STRAT = "\r\n".join([
    "campaign imperial_campaign", "playable", "\tslave", "end", "unlockable",
    "end", "nonplayable", "end", "", "start_date 1080 summer",
    "end_date 1500 winter", "",
    "faction slave, comfort caesar", "\tai_label default", "\tdenari 1000",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion A_Province",
    "\t\tyear_founded 0", "\t\tpopulation 800", "\t\tplan_set default_set",
    "\t\tfaction_creator slave", "\t}",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion B_Province",
    "\t\tyear_founded 0", "\t\tpopulation 800", "\t\tplan_set default_set",
    "\t\tfaction_creator slave", "\t}", "", "script", "campaign_script.txt", ""])


def build(root: Path) -> Mod:
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(RECORDS.encode("latin-1"))
    write_tga(base / "map_regions.tga", img_of(W, H, region_px))
    V, U = 2 * W + 1, 2 * H + 1
    write_tga(base / "map_heights.tga", img_of(
        V, U, lambda x, y: (60, 60, 60) if corner_land(x, y) else (0, 0, 200)))
    write_tga(base / "map_ground_types.tga", img_of(
        V, U, lambda x, y: (96, 160, 64) if corner_land(x, y) else (128, 0, 0)))
    write_tga(base / "map_climates.tga", img_of(V, U, lambda x, y: (236, 0, 140)))
    write_tga(base / "map_features.tga", img_of(W, H, lambda x, y: (0, 0, 0)))
    write_tga(base / "map_fog.tga", img_of(V, U, lambda x, y: (255, 255, 255)))
    write_tga(base / "map_trade_routes.tga", img_of(W, H, lambda x, y: (0, 0, 0)))
    write_tga(base / "map_roughness.tga", img_of(2 * W, 2 * H, lambda x, y: (0, 0, 0)))
    data = root / "data"
    (data / mapvocab.CLIMATES_REL).parent.mkdir(parents=True, exist_ok=True)
    (data / mapvocab.CLIMATES_REL).write_text(CLIMATES, encoding="latin-1")
    camp = data / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
    camp.mkdir(parents=True)
    (camp / campstrat.STRAT_NAME).write_bytes(STRAT.encode("latin-1"))
    return Mod(root)


def files_of(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


tmp = Path(_tmp.mkdtemp(prefix="ut_gen_"))
root = tmp / "mods" / "Gen"
mod = build(root)
cm = campmap.CampaignMap(mod)
BOX = osmmap.Bbox(52.0, 48.0, 0.0, 6.0)
osmmap.keep_box(cm, BOX)
proj = osmmap.Projection(BOX, W, H)

# ---- 0) the network is never asked -------------------------------------------
print("\n0) with the switch off, nothing is sent and the plan says why")
p = mapgen.plan(mod, cm, {"kind": "heights"})
check(f"heights refuses with the switch off: {p.errors[:1]}",
      not p.payload()["ok"] and "off" in " ".join(p.errors).lower())
p = mapgen.plan(mod, cm, {"kind": "features"})
check("so do the rivers", not p.payload()["ok"] and "off" in " ".join(p.errors).lower())


# the network, replaced: a hill 3,000 m high in the middle, sea floor at -500
def fake_elevation(box, cols, rows):
    ys, xs = np.mgrid[0:rows, 0:cols]
    cx, cy = (cols - 1) / 2, (rows - 1) / 2
    r = np.hypot((xs - cx) / cols, (ys - cy) / rows)
    return np.where(r < 0.35, 3000 * (1 - r / 0.35), -500.0)


REAL_ELEVATION = mapgen.elevation
mapgen.elevation = fake_elevation

# ---- 1) heights ----------------------------------------------------------------
print("\n1) heights, from the (synthetic) real world")
p = mapgen.plan(mod, cm, {"kind": "heights"})
d = p.payload()
check(f"land only: the plan writes map_heights.tga: {d['errors']}",
      d["ok"] and d["files"] == [f"{campmap.BASE_REL}/map_heights.tga"])
out = mapgen.apply(p)
hts, _ = read(root / "data" / campmap.BASE_REL / "map_heights.tga")
hp = hts.convert("RGB").load()
cx, cy = W, H                                     # the middle corner
check(f"the top of the hill is 3,000 m of a 3,000 m scale: {hp[cx, cy]}",
      hp[cx, cy] == (255, 255, 255))
check("the sea is left exactly as it was", hp[0, 0] == (0, 0, 200))
check("land that the real ground puts below sea level stays land, at grey 1",
      hp[2 * 5 + 1, 2 * 5 + 1] == (1, 1, 1))
check("and the validator finds no tile that changed between land and sea",
      not any(f.code in ("marker.sea", "region.sea_mismatch")
              for f in mapcheck.run(Mod(root), use_baseline=False).findings))
transfer.undo(out["id"])
cm = campmap.CampaignMap(Mod(root))
p = mapgen.plan(Mod(root), cm, {"kind": "heights", "area": "whole"})
whole = mapresize._decode(io.BytesIO(p.data[f"{campmap.BASE_REL}/map_heights.tga"]))
wpx = whole.convert("RGB").load()
check(f"the whole map writes the sea floor into the blue: 500 m of a 1,000 m "
      f"sea is {wpx[0, 0]}", wpx[0, 0] == (0, 0, 128))
check("and says what it leaves behind",
      any("do not follow" in w for w in p.warnings))

# ---- 2) ground -----------------------------------------------------------------
print("\n2) ground types from the heights")
cm = campmap.CampaignMap(Mod(root))
p = mapgen.plan(Mod(root), cm, {"kind": "ground"})
d = p.payload()
check(f"every land corner at grey 60 is fertility_medium: {d['changes'][:1]}",
      d["ok"] and "fertility_medium" in d["changes"][0])
out = mapgen.apply(p)
gt, _ = read(root / "data" / campmap.BASE_REL / "map_ground_types.tga")
gp = gt.convert("RGB").load()
check("land is typed, the sea is not touched",
      gp[W, H] == mapvocab.ground("fertility_medium")["rgb"] and gp[0, 0] == (128, 0, 0))
p = mapgen.plan(Mod(root), campmap.CampaignMap(Mod(root)),
                {"kind": "ground", "bands": [["hills", 100], ["mountains_high", 255]]})
check("bands can be given, and grey 60 under 100 is hills then",
      p.payload()["ok"] and "hills" in p.changes[0])
check("a band list that stops short of 255 is refused",
      not mapgen.plan(Mod(root), campmap.CampaignMap(Mod(root)),
                      {"kind": "ground", "bands": [["hills", 100]]}).payload()["ok"])
transfer.undo(out["id"])

# ---- 3) climates ---------------------------------------------------------------
print("\n3) climates from the ground types")
p = mapgen.plan(Mod(root), campmap.CampaignMap(Mod(root)), {"kind": "climates",
                "mapping": {"fertility_medium": "highland"}})
d = p.payload()
check(f"fertile ground becomes highland: {d['changes'][:1]}",
      d["ok"] and "highland" in d["changes"][0])
check("a climate this mod does not have is said, not invented",
      any("no climate" in w for w in d["warnings"]))
p2 = mapgen.plan(Mod(root), campmap.CampaignMap(Mod(root)), {"kind": "climates",
                 "mapping": {g: "nowhere" for g in mapgen.CLIMATE_OF}})
check("a table naming none of the mod's climates is refused",
      not p2.payload()["ok"])

# ---- 4) rivers -----------------------------------------------------------------
print("\n4) rivers, cliffs and volcanoes from (synthetic) OpenStreetMap")


def geo(points):
    return [list(proj.to_geo(x, y)) for x, y in points]


RIVERS = {
    # the trunk, west to east and down into the sea past the coast
    "1": geo([(8, 10), (20, 12), (40, 12), (47, 25), (47, 36)]),
    # a tributary from the north that meets it
    "2": geo([(30, 5), (30, 11)]),
    # one through the western settlement at (15, 18)
    "3": geo([(10, 26), (15, 18), (15, 8.5)]),
    # a river that turns back on itself, which would close a loop
    "4": geo([(36, 20), (40, 20), (40, 24), (36, 24), (36, 19)]),
    # a scrap too short to be a river at this scale
    "5": geo([(50, 28), (51, 28)]),
}
FEATS = {"rivers": RIVERS,
         "cliffs": {"9": geo([(20, 28), (26, 28)])},
         "volcanoes": [list(proj.to_geo(52, 8))]}
mapgen._osm_features = lambda box, detail: FEATS
s = config.load_settings()
s[osmmap.ENABLED_KEY] = True
config._write_json(config.SETTINGS_PATH, s)
p = mapgen.plan(Mod(root), campmap.CampaignMap(Mod(root)), {"kind": "features"})
d = p.payload()
check(f"the plan draws rivers: {d['changes'][:1]} {d['errors']}", d["ok"])
out = mapgen.apply(p)
rep = mapcheck.run(Mod(root), use_baseline=False)
bad = [(f.code, f.message[:60]) for f in rep.findings
       if f.code.startswith("river.") or f.code == "marker.feature"]
check(f"the validator has nothing to say about the rivers: {bad}", not bad)
ft, _ = read(root / "data" / campmap.BASE_REL / "map_features.tga")
fa = np.array(ft.convert("RGB"))
src = np.all(fa == mapvocab.feature("river_source")["rgb"], axis=2)
riv = np.all(fa == mapvocab.feature("river")["rgb"], axis=2) | src
import re
drawn = int(re.search(r"(\d+) river course", d["changes"][0]).group(1))
check(f"{int(src.sum())} source(s) for {drawn} course(s): one each, and the city "
      f"cut two rivers into four", int(src.sum()) == drawn == 6)
check("no river under either settlement",
      not any(riv[y, x] for x, y in SEATS))
check("the trunk reaches the sea, two tiles past the coast and no further",
      riv[32, 47] and riv[33, 47] and not riv[34, 47])
check("the cliff is drawn and the volcano stands where OSM puts it",
      np.all(fa == mapvocab.feature("cliff")["rgb"], axis=2).sum() >= 5
      and tuple(fa[8, 52]) == mapvocab.feature("volcano")["rgb"])
check("the scrap too short to be a river is left out and said",
      not riv[28, 50:52].any() and any("too short" in w for w in d["warnings"]))
now = files_of(root)
transfer.undo(out["id"])
check("and one Undo takes the rivers away again",
      not np.array(read(root / "data" / campmap.BASE_REL / "map_features.tga")[0]
                   .convert("RGB")).any())

# ---- 5) the pieces on their own ------------------------------------------------
print("\n5) the pieces")
line = mapgen.cardinal([(0, 0), (5, 3)])
steps = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(line, line[1:])]
check(f"a diagonal line is walked in cardinal steps only: {steps}",
      set(steps) == {1} and line[0] == (0, 0) and line[-1] == (5, 3))
joined = mapgen.chain([[(0, 0), (1, 1)], [(1, 1), (2, 2)], [(5, 5), (6, 6)]])
check("two waterways end to start are one river, a third on its own is another",
      sorted(len(c) for c in joined) == [2, 3])
forked = mapgen.chain([[(0, 0), (1, 1)], [(1, 1), (2, 2)], [(1, 1), (3, 0)]])
check("a fork is two rivers, not one", len(forked) == 3)

# the stitching: a tile whose every pixel is its own global column number
mapgen.elevation_tile = lambda z, x, y: np.tile(np.arange(256, dtype=float) + 256 * x,
                                                (256, 1))
m = REAL_ELEVATION(BOX, 2 * W + 1, 2 * H + 1)
zs = [z for z in range(3, 13)
      if abs(m[5, 1] - mapgen._lon2x(BOX.west, z)) < 1.5
      and abs(m[5, 2 * W - 1] - mapgen._lon2x(BOX.east, z)) < 1.5]
check(f"tiles are stitched and sampled where the box puts each corner (zoom {zs})",
      bool(zs) and np.all(np.diff(m[5]) >= 0) and np.allclose(m[:, 7], m[0, 7]))

# the real mods: the two local generators, planned and not written
print("\n6) the installed mods: ground and climates from their own maps")
for real in _realmod.installed():
    rmod = Mod(real)
    rcm = campmap.CampaignMap(rmod)
    g = mapgen.plan(rmod, rcm, {"kind": "ground"})
    c = mapgen.plan(rmod, rcm, {"kind": "climates"})
    check(f"{real.name}: ground types plan from its heights "
          f"({g.changes[0][:70] if g.changes else g.errors})", g.payload()["ok"])
    check(f"{real.name}: the climate table plans or says why not "
          f"({(c.changes or c.errors)[0][:70]})", c.payload()["ok"] or c.errors)

print(f"\n{sum(ok)}/{len(ok)} checks" + ("" if all(ok) else
      f" - {len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
