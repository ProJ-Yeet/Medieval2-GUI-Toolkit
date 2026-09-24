"""A new campaign on a map made from nothing - Phase 26b, measured.

The shape first, on no mod at all: an island of the share asked for, every
province one piece with a city that has its own province on all four sides,
colours that are neither the sea's nor a marker's.

Then each installed mod, on a copy of the files a campaign reads - the top-level
text files, text/, the base map and the campaign it copies - so nothing is
written to the mod itself:

    the plan         says the size, the provinces, who holds them, and names
                     every file
    the write        makes the folder, its own ten layers and two text files, a
                     strat that owns every province, and a name for each
    the validator    finds nothing fatal about the new map
    the undo         takes it all away again

    python -m tests.test_mapnew
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from tests import _realmod, _tmp
from unittransfer import (campmap, campstrat, config, mapcheck, mapnew, mapvocab,
                          namekeys, transfer)
from unittransfer.maptga import read
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

# ---- 1) the shape ------------------------------------------------------------
print("\n1) the island, on no mod at all")
isl = mapnew.island(120, 90, 10, 0.5)
share = isl.land.mean()
check(f"the land is about the share asked for: {share:.2f} of 0.50",
      0.42 < share < 0.58)
check("the edge of the map is sea all the way round",
      not isl.land[0].any() and not isl.land[-1].any()
      and not isl.land[:, 0].any() and not isl.land[:, -1].any())
from scipy import ndimage
four = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
pieces = [ndimage.label(isl.owner == i, structure=four)[1] for i in range(10)]
check(f"every province is one piece: {pieces}", pieces == [1] * 10)
seats_ok = all(isl.owner[y + dy, x + dx] == i
               for i, (x, y) in enumerate(isl.seats)
               for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))
check("every city has its own province on all four sides", seats_ok)
check("every province has at least the minimum of land",
      min(int((isl.owner == i).sum()) for i in range(10)) >= mapnew.MIN_TILES)
cols = mapnew.region_colours(199)
check("199 province colours, all different, none a marker's or the sea's",
      len(set(cols)) == 199 and mapnew.SEA_REGION not in cols
      and mapvocab.SETTLEMENT_RGB not in cols and mapvocab.PORT_RGB not in cols)
try:
    mapnew.island(30, 30, 40, 0.3)
    refused = False
except mapnew.NewMapError:
    refused = True
check("forty provinces on a tiny island are refused, not squeezed", refused)


# ---- 2) each installed mod, on a copy ---------------------------------------
def partial_copy(src: Path, dst: Path) -> None:
    """What a campaign reads: top-level text, text/, the base map and
    imperial_campaign. Not the models, the textures or the battles."""
    data = src / "data"
    out = dst / "data"
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


print("\n2) every installed mod: a new campaign on a new map, on a copy")
for real in _realmod.installed():
    dst = Path(_tmp.mkdtemp(prefix="ut_newmap_")) / real.name
    partial_copy(real, dst)
    mod = Mod(dst)
    before = files_of(dst)
    v = mapnew.view(mod)
    fs = [f for f in v["factions"] if f.lower() != "scripts"][:3]
    body = {"source": campstrat.DEFAULT_CAMPAIGN, "name": "Newland",
            "title": "Newland", "blurb": "a test", "width": 160, "height": 120,
            "provinces": 9, "land": 0.5, "factions": fs,
            "climate": v["climates"][0]["code"]}
    p = mapnew.plan(mod, body)
    d = p.payload()
    check(f"{real.name}: the plan is a {d['width']}x{d['height']} map of "
          f"{len(d['provinces'])} provinces: {d['errors']}",
          d["ok"] and len(d["provinces"]) == 9)
    held = sorted(x["faction"] for x in d["provinces"] if x["faction"] != "slave")
    check(f"  each faction holds one province: {held}", held == sorted(fs))
    out = mapnew.apply(p)
    home = dst / "data" / campstrat.CAMPAIGN_DIR_REL / "Newland"
    got = {ly["file"] for ly in campmap.LAYERS if (home / ly["file"]).is_file()}
    check(f"  the folder has its own layers ({len(got)}) and both text files",
          len(got) >= 9 and (home / "descr_terrain.txt").is_file()
          and (home / "descr_regions.txt").is_file())
    reg, _ = read(home / "map_regions.tga")
    check("  map_regions.tga is the size descr_terrain.txt says",
          reg.size == (160, 120)
          and "width  160" in (home / "descr_terrain.txt").read_text(encoding="latin-1")
          .replace("\t", "  ").replace("width 160", "width  160"))
    names = namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL)
    check("  every province and town has a name in the text file",
          all(x["name"] in names and x["town"] in names for x in d["provinces"]))
    cm = campmap.campaign_map(Mod(dst), "Newland")
    rep = mapcheck.run(Mod(dst), cm, "Newland", use_baseline=False)
    fatal = [f for f in rep.findings if f.severity == "fatal"
             and not f.code.startswith("terrain.")]
    check(f"  the validator finds nothing fatal about it: "
          f"{[(f.code, f.message[:70]) for f in fatal][:3]}", not fatal)
    codes = sorted({f.code for f in rep.findings if not f.code.startswith("terrain.")})
    print(f"      (what it does say: {codes})")
    check("  the base map is not touched",
          all(files_of(dst).get(k) == v for k, v in before.items()
              if k.startswith(f"data/{campmap.BASE_REL}/")))
    transfer.undo(out["id"])
    now = files_of(dst)
    changed = [k for k in set(before) | set(now) if before.get(k) != now.get(k)]
    check("  one Undo takes the whole campaign away again"
          + (f", except {changed[:4]}" if changed else ""), not changed)

print(f"\n{sum(ok)}/{len(ok)} checks" + ("" if all(ok) else
      f" - {len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
