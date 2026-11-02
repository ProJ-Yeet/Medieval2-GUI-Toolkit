"""96f: a faction's select-screen map drawn from the campaign map.

    python -m tests.test_mapdraw

On Divide and Conquer's imperial campaign: the picture is the size of the
campaign's own map_FE.tga; sea is sea and land is land; the faction's starting
regions come from descr_strat.txt and its patch is its colour; the file goes
where the faction-select screen looks for it (map_<faction>.tga in the
campaign folder); and the write is one backup and one Undo, on a temp mod.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, mapdraw, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
CAMP = "imperial_campaign"
check("where the select screen looks", mapdraw.rel_for(CAMP, "milan")
      == "world/maps/campaign/imperial_campaign/map_milan.tga")
if not (DAC / "data/world/maps/base/map_regions.tga").is_file():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    mod = Mod(DAC)
    print("\n1) the picture")
    regs = mapdraw.owned_regions(mod, CAMP, "milan")
    check(f"milan starts with {len(regs)} regions, Helm's Deep among them", "Helms_Deep_Province" in regs)
    img = mapdraw.draw(mod, CAMP, "milan", "#c02020")
    check(f"the size of the campaign's map_FE.tga ({img.size})", img.size == (768, 768))
    corner = img.getpixel((4, 4))
    check(f"a corner is sea blue ({corner})", corner[2] > corner[0] and corner[2] > corner[1])
    plain = mapdraw.draw(mod, CAMP)
    diff = sum(1 for a, b in zip(img.getdata(), plain.getdata()) if a != b)
    check(f"the faction's land changes part of the picture, not all ({diff})", 0 < diff < 768 * 768 // 4)
    red = sum(1 for p in img.getdata() if p[0] > 140 and p[1] < 90 and p[2] < 90)
    check(f"its patch is its colour ({red} red pixels)", red > 500)

    print("\n2) written and undone, on a temp mod")
    root = Path(_tmp.mkdtemp(prefix="ut_mapdraw_")) / "MapMod"
    shutil.copytree(DAC / "data/world/maps/base", root / "data/world/maps/base")
    shutil.copytree(DAC / "data/world/maps/campaign/imperial_campaign",
                    root / "data/world/maps/campaign/imperial_campaign",
                    ignore=shutil.ignore_patterns("*.tga", "custom_tiles"))
    shutil.copy2(DAC / "data/world/maps/campaign/imperial_campaign/map_FE.tga",
                 root / "data/world/maps/campaign/imperial_campaign/map_FE.tga")
    for rel in ("descr_sm_factions.txt",):
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    snap = {f.relative_to(root).as_posix(): f.stat().st_size for f in root.rglob("*") if f.is_file()}
    tm = Mod(root)
    rec = mapdraw.apply(tm, CAMP, "milan", "#c02020")
    out = root / "data" / mapdraw.rel_for(CAMP, "milan")
    with Image.open(out) as im:
        size = im.size
    check(f"map_milan.tga written, {size}", size == (768, 768))
    transfer.undo(rec["id"])
    now = {f.relative_to(root).as_posix(): f.stat().st_size for f in root.rglob("*") if f.is_file()}
    check("one undo takes it away again", now == snap)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
