"""A unit whose DICTIONARY the destination already uses is a conflict too.

Two EDU entries on one dictionary share one export_units record and one set of
cards, so the second transfer used to rewrite the first unit's name and text
(a tester's report: "two EDU entries and one export_units entry"). Checks:
  * a dictionary-only clash is reported, keeps the unit's own type, and gets a
    dictionary of its own; "overwrite" turns into a rename, since there is no
    unit of this type to overwrite
  * the other unit's export_units record is left exactly as it was
  * a rename never lands on a type or dictionary the destination already has
Uses temp config + temp dest so the real mods are never touched.
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, localization
from unittransfer.mod import Mod
from unittransfer.transfer import TransferOptions, plan_transfer, apply_transfer

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR, DAC = MODS / "Third_Age_Reforged", MODS / "Divide_and_Conquer_EUR"
UNIT = "Numenorean Marines"

ok = []
def check(label, cond):
    ok.append(bool(cond)); print(f"  [{'OK ' if cond else 'FAIL'}] {label}")

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

dest_root = Path(_tmp.mkdtemp(prefix="ut_dest_"))
data = dest_root / "data"
(data / "text").mkdir(parents=True); (data / "unit_models").mkdir(parents=True)
shutil.copy2(DAC / "data/export_descr_unit.txt", data / "export_descr_unit.txt")
shutil.copy2(DAC / "data/text/export_units.txt", data / "text/export_units.txt")
shutil.copy2(DAC / "data/unit_models/battle_models.modeldb", data / "unit_models/battle_models.modeldb")
edu_path, loc_path = data / "export_descr_unit.txt", data / "text/export_units.txt"

src = Mod(TATR)
unit = src.edu.by_type()[UNIT]
DICT = unit.dictionary

# 1) DaC already has its own unit on this dictionary, under another type
OTHER = next(t for t, u in Mod(dest_root).edu.by_type().items()
             if u.dictionary.lower() == DICT.lower() and t != UNIT)
print("dictionary", DICT, "belongs to", OTHER)
other_rec = localization.parse_file(loc_path).get(DICT)
check("setup: the other unit has a record", other_rec is not None)

# 2) bring the unit in, asking to overwrite
dest = Mod(dest_root)
plan = plan_transfer(src, UNIT, dest, TransferOptions(asset_conflict="mod_folder",
                                                       on_conflict="overwrite",
                                                       new_name="My Marines"))
check("a dictionary-only clash is a conflict", plan.unit_conflict)
check("it names the unit that owns the dictionary", plan.dict_conflict == OTHER)
check("overwrite became rename", plan.options.on_conflict == "rename")
check("the type stays its own", plan.resolved_type == UNIT)
check("the dictionary is new", plan.resolved_dict.lower() != DICT.lower())
apply_transfer(plan)
loc = localization.parse_file(loc_path)
after = loc.get(DICT)
check("the other unit's record is untouched",
      after is not None and (after.name, after.descr, after.descr_short)
      == (other_rec.name, other_rec.descr, other_rec.descr_short))
check("the new unit has a record of its own",
      loc.get(plan.resolved_dict) is not None
      and loc.get(plan.resolved_dict).name == "My Marines")
units = Mod(dest_root).edu.by_type()
check("both units are in the EDU", UNIT in units and OTHER in units)
check("on different dictionaries",
      units[UNIT].dictionary.lower() != units[OTHER].dictionary.lower())

# 3) a rename never lands on a name the destination already has
taken_dict = plan.resolved_dict
again = plan_transfer(src, UNIT, Mod(dest_root),
                      TransferOptions(asset_conflict="mod_folder", on_conflict="rename",
                                      new_dictionary=taken_dict, new_type=OTHER))
check("a taken type is not reused", again.resolved_type.lower() != OTHER.lower())
check("a taken dictionary is not reused", again.resolved_dict.lower() != taken_dict.lower())
check("and the plan says so", sum("already taken" in w for w in again.warnings) == 2)

shutil.rmtree(dest_root, ignore_errors=True); shutil.rmtree(cfg, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
