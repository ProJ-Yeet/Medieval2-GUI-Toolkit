"""Deleting a unit for one faction only (Delete unit, "For faction").

    python -m tests.test_delete_faction

Nothing installed is needed: a mod where England and France both own Spearmen,
with recruitment, a campaign's armies, a mercenary pool, a script and cards, is
written to a temp folder.

1. the EDU keeps the unit: France leaves its ownership and era lines, England stays
2. the EDB: France leaves a `factions { }` list that has England too; a line
   for France alone goes; a culture's line and a `not factions` line are left
   and said
3. descr_strat: France's army lines go, England's stay; France's army left
   empty is warned about
4. what is not France's is untouched: the mercenary pool, the text entry,
   England's card; the script is reported, not cut
5. the box "and its card" takes France's card only
6. the only owner is refused: that is deleting the unit
7. apply writes it, Undo puts every file back byte for byte
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


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = Path(_tmp.mkdtemp(prefix="ut_delfac_"))
data = root / "data"
camp = data / "world/maps/campaign/imperial_campaign"
for d in ("unit_models", "text", camp, "ui/units/england", "ui/units/france", "ui/unit_info/france"):
    (data / d).mkdir(parents=True, exist_ok=True)
(data / "unit_models/battle_models.modeldb").write_bytes(
    ("22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n").encode("latin-1"))
edu = ("type             Spearmen\ndictionary       spearmen\ncategory         infantry\nclass            spearmen\n"
       "voice_type       Light\nsoldier          none, 40, 0, 1\nownership        england, france\n"
       "era 0            england, france\nera 1            france\n\n"
       "type             Knights\ndictionary       knights\ncategory         cavalry\nclass            heavy\n"
       "voice_type       Heavy\nsoldier          none, 20, 0, 1\nownership        england\n\n")
(data / "export_descr_unit.txt").write_text(edu, encoding="latin-1")
(data / "text/export_units.txt").write_text("{spearmen}Spearmen\n", encoding="utf-16")
for rel in ("ui/units/england/#spearmen.tga", "ui/units/france/#spearmen.tga",
            "ui/unit_info/france/spearmen_info.tga"):
    (data / rel).write_bytes(b"tga")
files = {
    "export_descr_buildings.txt": (
        "building barracks\n{\n    levels militia\n    {\n        militia requires factions { england, france, }\n        {\n"
        "            capability\n            {\n"
        '                recruit_pool "Spearmen"  1   0.7   2  0  requires factions { england, france, }\n'
        '                recruit_pool "Spearmen"  1   0.5   1  0  requires factions { france, } and event_counter x 1\n'
        '                recruit_pool "Spearmen"  1   0.5   1  0  requires factions { northern_european, }\n'
        '                recruit_pool "Spearmen"  1   0.5   1  0  requires not factions { france, }\n'
        '                recruit_pool "Knights"  1   0.7   2  0  requires factions { france, }\n'
        "            }\n        }\n    }\n}\n"),
    "descr_mercenaries.txt": "pool Europe\n\tregions London\n\tunit Spearmen,\t\texp 0 cost 400 replenish 0.1 - 0.2 max 2 initial 1\n",
    "world/maps/campaign/imperial_campaign/descr_strat.txt": (
        "faction england, comfortable caderdisc\ncharacter\tWilliam, named character, leader, age 30, x 1, y 2\n"
        "army\nunit\t\tSpearmen\t\texp 0 armour 0 weapon_lvl 0\n\n"
        "faction france, comfortable caderdisc\ncharacter\tPhilip, named character, leader, age 30, x 3, y 4\n"
        "army\nunit\t\tSpearmen\t\texp 0 armour 0 weapon_lvl 0\n"
        "unit\t\tSpearmen\t\texp 1 armour 0 weapon_lvl 0\n\n"
        "faction slave, comfortable caderdisc\n"),
    "world/maps/campaign/imperial_campaign/campaign_script.txt": (
        "script\n    spawn_army\n        faction france\n        character Bob, general, age 20, x 5, y 5\n"
        "        unit Spearmen exp 1 armour 0 weapon_bonus 0\n    end\nend_script\n"),
}
for rel, text in files.items():
    (data / rel).write_text(text, encoding="latin-1")
watched = list(files) + ["export_descr_unit.txt", "ui/units/france/#spearmen.tga",
                         "ui/unit_info/france/spearmen_info.tga", "ui/units/england/#spearmen.tga"]
before = {rel: (data / rel).read_bytes() for rel in watched}


def plan(faction="france", unit="Spearmen", icons=False):
    req = edit.request_from_dict({"unit": unit, "delete": True,
                                  "delete_options": {"faction": faction, "remove_icons": icons}})
    return edit.plan_edit(Mod(root), req)


try:
    p = plan()
    check("the plan has no errors", not p.errors)
    texts = {k.relative_to(data).as_posix(): v for k, v in p.ref_texts.items()}

    print("1) the EDU")
    new_edu = p.edu_text
    check("the unit is still there", "type             Spearmen\n" in new_edu)
    check("France leaves its ownership", "ownership        england\n" in new_edu)
    check("France leaves era 0", "era 0            england\n" in new_edu)
    check("era 1 named only France: the line goes", "era 1" not in new_edu)
    check("the other unit is untouched", "ownership        england\n\n" in new_edu.split("Knights", 1)[1])

    print("2) the EDB")
    edb = texts.get("export_descr_buildings.txt", "")
    check("a list with England keeps England only",
          'recruit_pool "Spearmen"  1   0.7   2  0  requires factions { england, }' in edb)
    check("the line for France alone goes", "event_counter x 1" not in edb)
    check("the culture's line is left", "northern_european" in edb)
    check("the not factions line is left", "requires not factions { france, }" in edb)
    check("another unit's line for France stays", 'recruit_pool "Knights"  1   0.7   2  0  requires factions { france, }' in edb)
    check("the building's own condition stays", "militia requires factions { england, france, }" in edb)
    check("the lines left are said", any("export_descr_buildings.txt" in w and "ownership" in w for w in p.warnings))

    print("3) descr_strat")
    strat = texts.get("world/maps/campaign/imperial_campaign/descr_strat.txt", "")
    eng, fra = strat.split("faction france", 1)
    check("England's army keeps it", "unit\t\tSpearmen" in eng)
    check("France's army lines go", "unit\t\tSpearmen" not in fra)
    check("France's army left empty is warned about", any("only this unit" in w for w in p.warnings))

    print("4) what is not France's")
    check("the mercenary pool is untouched", "descr_mercenaries.txt" not in texts)
    check("the text entry is kept", p.loc_text == "")
    check("no card goes without the box", not p.deletes)
    check("the script is not cut", "world/maps/campaign/imperial_campaign/campaign_script.txt" not in texts)
    check("and is reported", any("campaign_script.txt" in w for w in p.warnings))

    print("5) and its card")
    pi = plan(icons=True)
    check("France's card and info card go, England's stays",
          sorted(pi.deletes) == ["ui/unit_info/france/spearmen_info.tga", "ui/units/france/#spearmen.tga"])

    print("6) the only owner")
    check("Knights for England: refused", plan("england", "Knights").errors)
    check("a faction that does not own it: refused", plan("france", "Knights").errors)

    print("7) apply and undo")
    res = edit.apply_edit(plan(icons=True))
    check("the EDU on disk lost France", "ownership        england\n" in (data / "export_descr_unit.txt").read_text(encoding="latin-1"))
    check("France's card is gone on disk", not (data / "ui/units/france/#spearmen.tga").exists())
    from unittransfer.transfer import undo
    undo(res["record"]["id"] if "record" in res else res["id"])
    check("Undo puts every file back byte for byte",
          all((data / rel).exists() and (data / rel).read_bytes() == b for rel, b in before.items()))
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
