"""Phase 70, T6: every tile of the campaign map as text.

    python -m tests.test_maptiles

1. Both installed mods: a row per tile, the header the export promises, both
   coordinate systems agreeing with the map's own conversion, and a sample of
   rows agreeing with the tile probe (region, ground, feature, climate, sea).
2. The options: land only drops exactly the sea tiles; the query's provinces
   only keep exactly those; the extended columns are each layer's colour.
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402,F401
from unittransfer import campmap, config  # noqa: E402
from unittransfer import mapquery as mq  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


# the exports go to the cache: keep this run's out of the user's
cache = Path(_tmp.mkdtemp(prefix="ut_tiles_"))
config.CONFIG_DIR = cache
config._cache_dir = cache / "cache"
(cache / "cache").mkdir()


def rows_of(export):
    f = Path(export.folder) / export.files[0]["name"]
    lines = f.read_text(encoding="utf-8").splitlines()
    return lines[0].split("\t"), [ln.split("\t") for ln in lines[1:]]


for name in ("ROCSS", "Divide_and_Conquer_EUR"):
    if not (MODS / name / "data" / campmap.BASE_REL).is_dir():
        continue
    print(f"\n1) {name}")
    mod = Mod(MODS / name)
    cm = campmap.CampaignMap(mod)
    facts = mq.Facts(mod, cm)
    w, h = cm.terrain.width, cm.terrain.height
    e = mq.export_tiles(facts)
    head, rows = rows_of(e)
    check(f"a row per tile: {len(rows):,} for a {w}x{h} map, in {e.ms} ms",
          len(rows) == w * h and not e.skipped)
    check("the header is the columns the export promises", head == list(mq.TILE_COLUMNS))
    col = {c: i for i, c in enumerate(head)}
    random.seed(7)
    sample = random.sample(rows, 60)
    agree = True
    for r in sample:
        ix, iy = int(r[col["image_x"]]), int(r[col["image_y"]])
        gx, gy = cm.game_xy(ix, iy)
        probe = cm.probe_pixel(ix, iy)
        names = {ly["code"]: ly["code_name"] for ly in probe["layers"]}
        want = [str(gx), str(gy), probe["region"]["name"], names.get("ground_types"),
                names.get("features"), names.get("climates"), "1" if probe["sea"] else "0"]
        got = [r[col["x"]], r[col["y"]], r[col["region"]], r[col["ground"]], r[col["feature"]],
               r[col["climate"]], r[col["sea"]]]
        # a colour no table names is written as what it is, where the probe
        # says None (ROCSS's climate layer has one at sea)
        got = [None if isinstance(g, str) and g.startswith("unknown ") else g for g in got]
        if want != got:
            agree = False
            print("     differs:", got, "probe:", want)
            break
    check("60 rows chosen at random agree with the tile probe, coordinates both ways included "
          "(a colour no table names is written as `unknown r,g,b`)", agree)
    land = [r for r in rows if r[col["sea"]] == "0"]
    check("a height on every land tile and none at sea",
          all(r[col["height"]].isdigit() for r in land)
          and all(r[col["height"]] == "" for r in rows if r[col["sea"]] == "1"))
    owned = [r for r in land if r[col["region"]]]
    rf = facts.by_name.get(owned[0][col["region"]].lower())
    check(f"a province's settlement and owner come from the fact table ({owned[0][col['region']]}: "
          f"{owned[0][col['settlement']]}, {owned[0][col['owner']]})",
          rf is not None and owned[0][col["settlement"]] == rf.settlement and owned[0][col["owner"]] == rf.owner)
    marks = {r[col["marker"]] for r in rows}
    check("the settlement and port markers are named", {"settlement", "port"} <= marks)

    print(f"\n2) {name}: the options")
    e2 = mq.export_tiles(facts, extended=True, land_only=True)
    head2, rows2 = rows_of(e2)
    check(f"land only: {len(rows2):,} rows, exactly the land tiles", len(rows2) == len(land)
          and all(r[head2.index("sea")] == "0" for r in rows2))
    check("extended adds each layer's colour as r,g,b",
          head2[len(mq.TILE_COLUMNS):] == ["regions_rgb", "ground_types_rgb", "features_rgb",
                                           "climates_rgb", "heights_rgb"]
          and all(len(r[-1].split(",")) == 3 for r in rows2[:50]))
    pick = owned[0][col["region"]]
    res = mq.run_query(facts, [{"code": "name", "value": pick}], "all")
    if res.matched:
        e3 = mq.export_tiles(facts, res)
        _h3, rows3 = rows_of(e3)
        want = {rr.name.lower() for rr in res.matched}
        check(f"the query's provinces only: {len(rows3):,} rows, all in {len(want)} province(s)",
              rows3 and all(r[col["region"]].lower() in want for r in rows3)
              and len(rows3) == sum(1 for r in rows if r[col["region"]].lower() in want))
    else:
        print("  -- the name filter matched nothing here; SKIPPED")

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
