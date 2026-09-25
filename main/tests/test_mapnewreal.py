"""Phase 87e: a new campaign on the real world under a box.

    python -m tests.test_mapnewreal

Nothing here touches the network: the elevation tiles are a synthetic
continent (a big land from 2 to 13 E and 41 to 48 N, hills in its middle, an
island off its south-east with no city on it, a speck of rock), Overpass is a
river through one of the cities, and each installed mod is copied first, so
nothing is written to it.

1. The land is the ground above sea level; the speck is made sea.
2. The cities picked: one on the sea moved to the nearest land, one off the
   map and one next to another left out, each said.
3. The provinces are grown from their cities, one piece of mainland each;
   the island with no city joins the nearest; every city has its own
   province on a cardinal side and nobody else's.
4. A port on the coast of each coastal city, on land with sea beside it.
5. The heights are true to the mod's max_land_height; the ground types are
   27's bands, sea shallow along the coast; no city stands on ground nothing
   can stand on.
6. Climates from the ground types; rivers from OSM cut at the city.
7. Written: its own layers, bbox_coords.txt beside the map (so the Real world
   tab lines up at once), the validator finds nothing fatal, one Undo.
"""
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import (campmap, campstrat, config, mapcheck, mapgen, mapnew,  # noqa: E402
                          mapvocab, namekeys, osmmap, transfer)
from unittransfer.maptga import read  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"
config.save_settings(osm_enabled=True)


# the speck sits on one row of tile centres, two tiles long
_BOX = osmmap.parse_bbox({"north": 50.0, "south": 38.0, "west": 0.0, "east": 16.0})
SPECK = osmmap.Projection(_BOX, *osmmap.size_for(_BOX, width=120)).to_geo(7.5, 10)


def ground_m(lat, lon):
    """The synthetic world: metres at a point."""
    if 2 <= lon <= 13 and 41 <= lat <= 48:
        d = min(lon - 2, 13 - lon, lat - 41, 48 - lat)
        return 40 + 900 * min(d, 2.5)
    if math.hypot(lat - 40.0, lon - 14.6) < 0.5:          # the island, no city
        return 120.0
    if abs(lat - SPECK[0]) < 0.03 and abs(lon - SPECK[1]) < 0.14:  # a speck of rock
        return 50.0
    return -800.0


def fake_tile(z, x, y):
    n = 2 ** z
    t = Image.new("F", (256, 256))
    vals = []
    for j in range(256):
        m = math.pi * (1 - 2 * (y + (j + 0.5) / 256) / n)
        lat = math.degrees(math.atan(math.sinh(m)))
        for i in range(256):
            vals.append(ground_m(lat, (x + (i + 0.5) / 256) / n * 360 - 180))
    t.putdata(vals)
    return t


mapgen.elevation_tile = fake_tile
RIVER = [(47.8, 9.0), (46.9, 9.0), (46.5, 9.0), (45.5, 9.0), (43.0, 9.0), (41.2, 9.0), (40.5, 9.0)]
mapgen._osm_features = lambda box, detail: {
    "rivers": {"1": RIVER}, "cliffs": {}, "volcanoes": []}

BOX = {"north": 50.0, "south": 38.0, "west": 0.0, "east": 16.0}
PICKS = [{"name": "Roma", "lat": 44.5, "lon": 5.0},
         {"name": "Firenze", "lat": 46.5, "lon": 9.0},
         {"name": "Porto Sul Mare", "lat": 40.93, "lon": 7.0},   # just off the coast
         {"name": "Lontano", "lat": 45.0, "lon": 30.0},          # off the map
         {"name": "Vicino", "lat": 44.5, "lon": 5.14}]           # next to Roma


def partial_copy(src: Path, dst: Path) -> None:
    data, out = src / "data", dst / "data"
    out.mkdir(parents=True)
    for p in data.iterdir():
        if p.is_file() and p.suffix.lower() in (".txt", ".xml"):
            shutil.copy2(p, out / p.name)
    for sub in ("text", campmap.BASE_REL,
                f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.DEFAULT_CAMPAIGN}"):
        if (data / sub).is_dir():
            shutil.copytree(data / sub, out / sub,
                            ignore=shutil.ignore_patterns("*.zip", "*.bak"))


def files_of(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


mods = _realmod.installed()
if not mods:
    print("SKIPPED - no installed mod")
    sys.exit(0)
for real in mods:
    print(f"\n== {real.name} ==")
    dst = Path(_tmp.mkdtemp(prefix="ut_realmap_")) / real.name
    partial_copy(real, dst)
    mod = Mod(dst)
    before = files_of(dst)
    v = mapnew.view(mod)
    fs = [f for f in v["factions"] if f.lower() != "scripts"][:2]
    # a town the mod already names, to see the new campaign's key step round it
    taken = next(k for k in sorted(namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL))
                 if k.isidentifier() and not k.lower().endswith("_province"))
    body = {"shape": "real", "source": campstrat.DEFAULT_CAMPAIGN, "name": "Realland",
            "title": "Realland", "blurb": "a test", "box": BOX, "width": 120,
            "settlements": [dict(PICKS[0], faction=fs[1])] + PICKS[1:]
            + [{"name": taken, "lat": 42.6, "lon": 11.0}],
            "factions": fs, "climate": v["climates"][0]["code"],
            "climates": "ground", "rivers": "major", "min_island": 4}
    p = mapnew.plan(mod, body)
    d = p.payload()
    W, H = d["width"], d["height"]
    want_w, want_h = osmmap.size_for(osmmap.parse_bbox(BOX), width=120)
    if not check(f"planned a {W}x{H} map, the height from the box's shape "
                 f"({want_w}x{want_h}): {d['errors']}", d["ok"] and (W, H) == (want_w, want_h)):
        continue
    names = [x["shown"] for x in d["provinces"]]
    check(f"four provinces, the picked cities that stand: {names}",
          names == ["Roma", "Firenze", "Porto Sul Mare", taken])
    check("the city at sea was moved to land, and said",
          any("Porto Sul Mare stood on the sea" in w for w in d["warnings"]))
    check("the one off the map and the one next to Roma are left out, and said",
          any("Lontano is off the map" in w for w in d["warnings"])
          and any("Vicino is next to another city" in w for w in d["warnings"]))
    check("Roma is held by the faction it was given, Firenze by the other picked, "
          "the moved town the rebels'",
          [x["faction"] for x in d["provinces"]][:3] == [fs[1], fs[0], "slave"])
    home = p.cp.folder
    regions = read_layer = None

    def layer(name):
        t = cfg / "l.tga"
        t.write_bytes(p.data[f"{home}/{name}"])
        return read(t)[0].convert("RGB")

    reg = layer("map_regions.tga")
    rp = reg.load()
    proj = osmmap.Projection(osmmap.parse_bbox(BOX), W, H)

    def tile(lat, lon):
        fx, fy = proj.to_tile(lat, lon)
        return int(round(fx)), int(round(fy))

    sea_rgb = mapnew.SEA_REGION
    check("the open sea is sea and the mainland is land",
          rp[tile(39, 1)] == sea_rgb and rp[tile(45, 11)] != sea_rgb)
    check("the speck of rock is made sea, and said",
          rp[tile(*SPECK)] == sea_rgb and any("speck" in c for c in d["changes"]))
    cols = [tuple(x["rgb"]) for x in d["provinces"]]
    isl = rp[tile(40.0, 14.6)]
    check(f"the island with no city on it joins a province ({isl})",
          isl in cols and any("islands" in c for c in d["changes"]))
    good = True
    for x in d["provinces"]:
        sx, sy = x["seat"]
        sides = [rp[sx + a, sy + b] for a, b in ((0, -1), (0, 1), (-1, 0), (1, 0))
                 if 0 <= sx + a < W and 0 <= sy + b < H]
        mine = [c for c in sides if c == tuple(x["rgb"])]
        other = [c for c in sides if c in cols and c != tuple(x["rgb"])]
        good &= rp[sx, sy] == mapvocab.SETTLEMENT_RGB and bool(mine) and not other
    check("every city is a settlement pixel with its own province beside it and nobody else's", good)
    coastal = [x for x in d["provinces"] if x["port"]]
    ok_ports = all(rp[tuple(x["port"])] == mapvocab.PORT_RGB and any(
        rp[x["port"][0] + a, x["port"][1] + b] == sea_rgb for a, b in ((0, -1), (0, 1), (-1, 0), (1, 0)))
        for x in coastal)
    check(f"{len(coastal)} coastal cit(ies) have a port on the coast, sea beside it", coastal and ok_ports)
    hts = layer("map_heights.tga")
    top = float(__import__("re").search(r"max_land_height\s+([\d.]+)",
                                        p.data[f"{home}/descr_terrain.txt"].decode("latin-1")).group(1))
    fx, fy = proj.to_tile(44.5, 7.5)
    g = hts.getpixel((round(2 * fx + 1), round(2 * fy + 1)))
    check(f"the heights are true to max_land_height ({top:,.0f} m): 2,290 m reads grey {g[0]}",
          abs(g[0] - round(2290 * 255 / top)) <= 3 and g[0] == g[1] == g[2])
    gt = layer("map_ground_types.tga")
    gp = gt.load()
    blocking = set(mapvocab.BLOCKING_GROUND) | {"forest_dense"}
    check("no city stands on ground nothing can stand on",
          all(mapvocab.ground_at(gp[2 * x["seat"][0] + 1, 2 * x["seat"][1] + 1])["code"] not in blocking
              for x in d["provinces"]))
    check("sea shallow along the coast, deep beyond",
          mapvocab.ground_at(gt.getpixel((1, 1)))["code"] == "sea_deep")
    ft = layer("map_features.tga")
    riv = {tuple(mapvocab.feature(c)["rgb"]) for c in mapvocab.RIVER_CODES}
    fsx, fsy = d["provinces"][1]["seat"]
    check("a river is drawn from OSM, and not under Firenze, which cuts it",
          any(ft.getpixel((x, y)) in riv for y in range(H) for x in range(W))
          and ft.getpixel((fsx, fsy)) not in riv)
    keyed = [x["name"] for x in d["provinces"]]
    check(f"a city whose name the mod already has ({taken}) takes the campaign's in "
          f"front: {keyed[-1]}", keyed[-1] == f"Realland_{taken}_Province"
          and d["provinces"][-1]["town"] == f"Realland_{taken}")
    check("bbox_coords.txt is written beside the new map",
          f"{home}/bbox_coords.txt" in p.data and b"north=50.000000" in p.data[f"{home}/bbox_coords.txt"])

    out = mapnew.apply(p)
    cm = campmap.campaign_map(Mod(dst), "Realland")
    box, where = osmmap.box_for(cm)
    check("the new campaign's box is found beside its map, so the Real world tab lines up",
          box is not None and where == "file" and box.north == 50.0)
    rep = mapcheck.run(Mod(dst), cm, "Realland", use_baseline=False)
    fatal = [f for f in rep.findings if f.severity == "fatal" and not f.code.startswith("terrain.")]
    check(f"the validator finds nothing fatal: {[(f.code, f.message[:80]) for f in fatal][:3]}",
          not fatal)
    print(f"      (what it does say: "
          f"{sorted({f.code for f in rep.findings if not f.code.startswith('terrain.')})})")
    transfer.undo(out["id"])
    now = files_of(dst)
    changed = [k for k in set(before) | set(now) if before.get(k) != now.get(k)]
    check("one Undo takes it all away again" + (f", except {changed[:3]}" if changed else ""),
          not changed)

# with no cities picked, they are spread evenly, and the plan refuses no land
print("\n== spread cities, and no land ==")
mod = Mod(dst)
p = mapnew.plan(mod, {"shape": "real", "source": campstrat.DEFAULT_CAMPAIGN, "name": "Spread",
                      "box": BOX, "width": 120, "provinces": 6, "factions": fs[:1],
                      "climate": v["climates"][0]["code"]})
check(f"six cities spread over the land when none is picked: {p.payload()['errors']}",
      p.payload()["ok"] and len(p.provinces) == 6)
p = mapnew.plan(mod, {"shape": "real", "source": campstrat.DEFAULT_CAMPAIGN, "name": "Wet",
                      "box": {"north": 38.0, "south": 30.0, "west": 20.0, "east": 30.0},
                      "width": 80, "provinces": 3, "factions": fs[:1]})
check("a box over open sea is refused", not p.payload()["ok"] and "land" in p.errors[0])
p = mapnew.plan(mod, {"shape": "real", "source": campstrat.DEFAULT_CAMPAIGN, "name": "Empty",
                      "box": BOX, "width": 120, "factions": fs[:1]})
check("with no cities and no count, it asks for them", not p.payload()["ok"])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
