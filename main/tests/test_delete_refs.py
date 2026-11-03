"""Deleting a unit takes its lines out of every other file (unitrefs.remove_refs).

    python -m tests.test_delete_refs

Nothing installed is needed: a two-unit mod with recruitment, a campaign's
armies, mercenary pools, rebels and a campaign script is written to a temp folder.

1. the lines that only name the unit go: its recruit lines, its army and
   garrison lines, its mercenary pool line, its rebels line - and only its:
   a unit whose name holds it (`Spearmen Heavy` against `Spearmen`) stays
2. a campaign script naming it is left alone and reported
3. an army left with no unit is warned about
4. the box can be unticked: nothing outside the EDU changes
5. apply writes it, Undo puts every file back byte for byte
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import config, edit  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def s(x):
    return f"{len(x)} {x}"


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = Path(_tmp.mkdtemp(prefix="ut_delrefs_"))
data = root / "data"
camp = data / "world/maps/campaign/imperial_campaign"
for d in ("unit_models", "text", camp):
    (data / d).mkdir(parents=True, exist_ok=True)
(data / "unit_models/battle_models.modeldb").write_bytes(
    ("22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n").encode("latin-1"))
edu = ""
for t, d in (("Spearmen", "spearmen"), ("Spearmen Heavy", "spearmen_heavy")):
    edu += (f"type             {t}\ndictionary       {d}\ncategory         infantry\nclass            spearmen\n"
            f"voice_type       Light\nsoldier          none, 40, 0, 1\nownership        england\n\n")
(data / "export_descr_unit.txt").write_text(edu, encoding="latin-1")
(data / "text/export_units.txt").write_text("", encoding="utf-16")
files = {
    "export_descr_buildings.txt": (
        "building barracks\n{\n    levels militia\n    {\n        militia requires factions { england, }\n        {\n"
        '            capability\n            {\n                recruit_pool "Spearmen"  1   0.7   2  0  requires factions { england, }\n'
        '                recruit_pool "Spearmen Heavy"  1   0.7   2  0  requires factions { england, }\n'
        "            }\n        }\n    }\n}\n"),
    "descr_mercenaries.txt": ("pool Europe\n\tregions London\n\tunit Spearmen,\t\texp 0 cost 400 replenish 0.1 - 0.2 max 2 initial 1\n"
                              "\tunit Spearmen Heavy,\texp 0 cost 500 replenish 0.1 - 0.2 max 2 initial 1\n"),
    "descr_rebel_factions.txt": "rebel_type Brigands\n\tcategory brigands\n\tunit Spearmen\n\tunit Spearmen Heavy\n",
    "world/maps/campaign/imperial_campaign/descr_strat.txt": (
        "faction england\ncharacter\tWilliam, named character, leader, age 30, x 1, y 2\n"
        "army\nunit\t\tSpearmen Heavy\t\texp 1 armour 0 weapon_lvl 0\nunit\t\tSpearmen\t\texp 0 armour 0 weapon_lvl 0\n\n"
        "character\tsub_faction england, Odo, general, age 30, x 3, y 4\narmy\nunit\t\tSpearmen\t\texp 0 armour 0 weapon_lvl 0\n\n"
        "faction france\n"),
    "world/maps/campaign/imperial_campaign/campaign_script.txt": (
        "script\nmonitor_event FactionTurnStart FactionType england\n"
        "    spawn_army\n        faction england\n        character Bob, general, age 20, x 5, y 5\n"
        "        unit Spearmen exp 1 armour 0 weapon_bonus 0\n    end\nend_monitor\nend_script\n"),
}
for rel, text in files.items():
    (data / rel).write_text(text, encoding="latin-1")
before = {rel: (data / rel).read_bytes() for rel in files}
before["export_descr_unit.txt"] = (data / "export_descr_unit.txt").read_bytes()


def plan(remove_refs=True):
    req = edit.request_from_dict({"unit": "Spearmen", "delete": True,
                                  "delete_options": {"remove_models": False, "remove_refs": remove_refs}})
    return edit.plan_edit(Mod(root), req)


try:
    print("1) the lines that only name it")
    p = plan()
    texts = {k.relative_to(data).as_posix(): v for k, v in p.ref_texts.items()}
    edb = texts.get("export_descr_buildings.txt", "")
    check("its recruit line goes", 'recruit_pool "Spearmen" ' not in edb)
    check("the unit whose name holds it stays", 'recruit_pool "Spearmen Heavy"' in edb)
    merc = texts.get("descr_mercenaries.txt", "")
    check("its mercenary pool line goes, the other stays", "unit Spearmen," not in merc and "unit Spearmen Heavy," in merc)
    reb = texts.get("descr_rebel_factions.txt", "")
    check("its rebels line goes, the other stays", "\tunit Spearmen\n" not in reb and "unit Spearmen Heavy" in reb)
    strat = texts.get("world/maps/campaign/imperial_campaign/descr_strat.txt", "")
    check("its army lines go, the other unit's stays",
          strat.count("unit\t\tSpearmen\t") == 0 and "unit\t\tSpearmen Heavy" in strat)
    check("the change is listed with the files", any("line(s) naming 'Spearmen' removed" in c for c in p.changes))

    print("2) a script naming it")
    check("the campaign script is not changed", "world/maps/campaign/imperial_campaign/campaign_script.txt" not in texts)
    check("and is reported to check by hand", any("campaign_script.txt" in w for w in p.warnings))

    print("3) an army left empty")
    check("Odo's army had only it: warned", any("descr_strat.txt" in w and "only this unit" in w for w in p.warnings))
    check("William's army still has a unit: not warned about",
          sum("only this unit" in w for w in p.warnings) == 1)

    print("4) unticked")
    check("nothing outside the EDU changes", not plan(False).ref_texts)

    print("5) apply and undo")
    res = edit.apply_edit(plan())
    check("the recruit line is gone on disk", 'recruit_pool "Spearmen" ' not in (data / "export_descr_buildings.txt").read_text(encoding="latin-1"))
    check("the unit is gone from the EDU", "type             Spearmen\n" not in (data / "export_descr_unit.txt").read_text(encoding="latin-1"))
    from unittransfer.transfer import undo
    undo(res["record"]["id"] if "record" in res else res["id"])
    check("Undo puts every file back byte for byte",
          all((data / rel).read_bytes() == b for rel, b in before.items()))
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
