"""An entry brought from the base game is laid out like the mod's own entries.

    python -m tests.test_bmdb_layout

The base game's battle_models.modeldb (and so every campaign read out of its
packs: americas, british_isles, crusades, teutonic) holds all 722 entries on
one line. A transferred entry used to keep that, so NE Culverin moved into
Third_Age_Reforged landed as a single 9000-character line among entries laid
out one value per line (2026-11-17).

1. A one-line entry is re-laid one value per line, and reads back the same.
2. An entry that already has its own line breaks is left exactly as it is.
3. A real transfer from americas writes the entry in lines.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import _tmp  # noqa: E402
from unittransfer import modeldb  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


ONE_LINE = (" 4 crew 1 2 13 a/crew_0.mesh 121 13 a/crew_1.mesh 900"
            " 2 7 england 15 a/t_eng.texture 13 a/t_n.texture 14 s/eng_crew.spr"
            " 5 spain 15 a/t_spa.texture 13 a/t_n.texture 14 s/spa_crew.spr"
            "  1 7 england 13 a/att.texture 15 a/att_n.texture 0"
            "  2 4 None 18 MTW2_Crew_Culverin 0  1 18 MTW2_Knife_Primary 0"
            " 5 horse 18 MTW2_HR_Non_Shield 0  1 18 MTW2_Sword_Primary 0"
            " 16 -0.090000004 0 0 -0.34999999 0.80000001 0.60000002")
WANT = "\r\n".join([
    "", "4 crew", "1 2",
    "13 a/crew_0.mesh 121", "13 a/crew_1.mesh 900",
    "2",
    "7 england", "15 a/t_eng.texture", "13 a/t_n.texture", "14 s/eng_crew.spr",
    "5 spain", "15 a/t_spa.texture", "13 a/t_n.texture", "14 s/spa_crew.spr",
    "1",
    "7 england", "13 a/att.texture", "15 a/att_n.texture 0",
    "2",
    "4 None", "18 MTW2_Crew_Culverin 0", "1", "18 MTW2_Knife_Primary", "0",
    "5 horse", "18 MTW2_HR_Non_Shield 0", "1", "18 MTW2_Sword_Primary",
    "0 16 -0.090000004 0 0 -0.34999999 0.80000001 0.60000002"])

print("\n1) a one-line entry is laid out")
got = modeldb.standard_layout(ONE_LINE, "\r\n")
check("one value per line, as the mod's own entries are", got == WANT)
if got != WANT:
    print(got)
a, b = modeldb.parse_entry_text(ONE_LINE), modeldb.parse_entry_text(got)
check("  and it reads back as the same entry", a.content_equals(b) and a.name == b.name)
check("  with the file's own line ending", "\r" not in modeldb.standard_layout(ONE_LINE, "\n"))

print("\n2) an entry with its own lines is left alone")
check("unchanged", modeldb.standard_layout(WANT, "\r\n") == WANT)
check("a padded first entry is unchanged too",
      modeldb.standard_layout(ONE_LINE, "\r\n", pad=True) == ONE_LINE)

print("\n3) a transfer from americas")
from unittransfer import config  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer.transfer import TransferOptions, plan_transfer, apply_transfer  # noqa: E402

from tests import _realmod  # noqa: E402
MODS = _realmod.mods()
src, dst_mod = MODS / "americas", MODS / "Divide_and_Conquer_EUR"
if not (src.exists() and (dst_mod / "data/unit_models/battle_models.modeldb").exists()):
    print("  SKIPPED - needs americas and a mod with a loose modeldb")
else:
    cfg = Path(_tmp.mkdtemp(prefix="ut_bml_cfg_"))
    config.CONFIG_DIR, config.BACKUP_DIR = cfg, cfg / "backups"
    config.SETTINGS_PATH, config.LOG_PATH = cfg / "settings.json", cfg / "transfers.json"
    root = Path(_tmp.mkdtemp(prefix="ut_bml_")) / "dst"
    for rel in ["export_descr_unit.txt", "text/export_units.txt",
                "unit_models/battle_models.modeldb", "descr_projectile.txt", "descr_engines.txt"]:
        f = dst_mod / "data" / rel
        if f.exists():
            (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, root / "data" / rel)
    p = plan_transfer(Mod(src), "NE Culverin", Mod(root),
                      TransferOptions(asset_conflict="reroute",
                                      asset_reroute_dir="unit_models/_units/eredluin"))
    apply_transfer(p)
    db = modeldb.parse_file(root / "data/unit_models/battle_models.modeldb")
    e = db.get("ne_culverin_crew")
    check("the entry is there", e is not None)
    if e:
        check("  laid out in lines", e.raw.count("\n") > 20)
        check("  no line longer than a path and its numbers",
              max(len(x) for x in e.raw.splitlines()) < 160)
        check("  and it points at eredluin", all("eredluin" in m for m in e.mesh_files()))

print(f"\n{sum(ok)}/{len(ok)} checks" + ("" if all(ok) else " - SOME FAILED"))
sys.exit(0 if all(ok) else 1)
