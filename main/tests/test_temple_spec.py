"""96f: a religion's temples from nothing.

    python -m tests.test_temple_spec

``buildings.temple_spec`` builds a new-tree spec from the mod's own temple
lines, and ``plan_new_tree`` writes it. On Divide and Conquer: three city
levels, the usual costs, turns and town sizes, a growing ``religion_level``,
the ``religion`` line naming the new faith, built by the factions picked, and a
plan with no errors. A mod with no temple lines gets three steps of faith.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, transfer  # noqa: E402
from unittransfer import buildings as B  # noqa: E402
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


print("\n1) the text a spec writes")
txt = B.new_tree_text({"name": "t", "religion": "r", "levels": [
    {"name": "a", "settlement": "city", "capabilities": ["religion_level bonus 1"]}]})
check("the religion line and the capability inside its block",
      "\treligion r\n" in txt and "capability\n\t\t\t{\n\t\t\t\treligion_level bonus 1\n\t\t\t}" in txt)


class NoTemples:
    class edb:
        buildings = []


print("\n2) a mod with no temple lines")
s = B.temple_spec(NoTemples, "valar", [])
check("three levels, each a step of faith",
      [lv["capabilities"] for lv in s["levels"]] == [["religion_level bonus 1"], ["religion_level bonus 2"],
                                                     ["religion_level bonus 3"]])
check("built by everyone when no faction is picked", s["requires"] == "")

DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
if not (DAC / "data" / "export_descr_buildings.txt").is_file():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    print("\n3) on Divide and Conquer")
    mod = Mod(DAC)
    s = B.temple_spec(mod, "valar", ["sicily", "turks"])
    lv = s["levels"]
    check(f"the usual number of levels ({len(lv)}), from {s['from_temples']} temple lines", len(lv) == 3)
    check("costs and turns grow along the chain",
          int(lv[0]["cost"]) < int(lv[1]["cost"]) < int(lv[2]["cost"])
          and int(lv[0]["construction"]) < int(lv[2]["construction"]))
    check("the usual town sizes", [x["settlement_min"] for x in lv] == ["village", "town", "large_town"])
    check("faith grows: 1, 3, 5", [x["capabilities"][0] for x in lv]
          == ["religion_level bonus 1", "religion_level bonus 3", "religion_level bonus 5"])
    check("built by the factions picked", s["requires"] == "factions { sicily, turks, }")
    p = B.plan_new_tree(mod, s)
    check(f"the plan is clean ({p.errors})", not p.errors)
    block = B.new_tree_text(B.new_tree_spec(mod, s))
    check("it names the new faith", "\treligion valar\n" in block and "building temple_valar" in block)
    p = B.plan_edit(mod, {"temples": {"religion": "valar", "factions": ["sicily"]}})
    cult = B.faction_cultures(mod).get("sicily")
    check(f"plain cards drawn for the picked faction's culture only ({cult}, {len(p.drawn)})",
          len(p.drawn) == 6 and all(f"/{cult}/" in r for r, _ in p.drawn))

    print("\n4) written and undone, on a temp mod built from DaC's files")
    root = Path(_tmp.mkdtemp(prefix="ut_temple_")) / "TempleMod"
    for rel in ("export_descr_buildings.txt", "text/export_buildings.txt", "descr_sm_factions.txt",
                "descr_cultures.txt"):
        if (DAC / "data" / rel).is_file():
            (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    (root / "data" / "ui" / cult / "buildings").mkdir(parents=True)
    snap = {f.relative_to(root).as_posix(): f.read_bytes() for f in root.rglob("*") if f.is_file()}
    tm = Mod(root)
    p = B.plan_edit(tm, {"temples": {"religion": "valar", "factions": ["sicily"]}})
    check(f"the plan is clean ({p.errors})", not p.errors and p.drawn)
    rec = B.apply_edit(p)
    card = root / "data" / p.drawn[0][0]
    check("the line and its first card are written",
          "building temple_valar" in (root / "data/export_descr_buildings.txt").read_text(encoding="latin-1")
          and card.is_file())
    transfer.undo(rec["id"])
    now = {f.relative_to(root).as_posix(): f.read_bytes() for f in root.rglob("*") if f.is_file()}
    check("one undo puts the files back and takes the cards away", now == snap)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
