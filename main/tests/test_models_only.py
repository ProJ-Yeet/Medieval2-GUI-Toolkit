"""`models` mode: import a unit's battle-model entries and nothing else.

The fourth transfer mode. "New unit", "based on an existing one" and "replace an
existing one" all write a UNIT; this one writes none - only the
battle_models.modeldb records the unit is drawn from, and the mesh/texture files
those records name. It is the mode for taking a mod's ART without its roster, and
for getting models into a mod before anything is built on them. Checked here:

  * `unit_model_index` names every entry the unit is affiliated with - soldier
    line, mount, officers, armour upgrades - with the folder each one's files sit
    in, which is half of what the composer's list shows
  * the plan copies those entries and their assets and NOTHING else: no EDU
    block, no localisation, no cards, no mount / projectile / engine definition,
    no voice entry, and it adds no unit to the destination's count
  * `models_only` narrows the import to the ticked entries; an empty list means
    all of them, and a name that is not one of the unit's models is reported
  * applying writes battle_models.modeldb and the asset files, leaves
    export_descr_unit.txt and text/export_units.txt byte-identical, and undo puts
    the modeldb back
  * the mode ignores a stale base_type / replace_type left over from another mode

    python -m tests.test_models_only
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, modeldb
from unittransfer.mod import Mod
from unittransfer.transfer import (TransferOptions, apply_transfer, plan_transfer,
                                   unit_model_index, undo)

from tests._realmod import pick

DST_MOD = pick("Divide_and_Conquer_EUR", need="export_descr_unit.txt")
SRC_MOD = pick("Third_Age_6", "Third_Age_Reforged", exclude=[DST_MOD],
               need="export_descr_unit.txt")

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

DEST_RELS = ("export_descr_unit.txt", "text/export_units.txt",
             "unit_models/battle_models.modeldb")


def fresh_dest():
    root = Path(_tmp.mkdtemp(prefix="ut_dest_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    for rel in DEST_RELS:
        shutil.copy2(DST_MOD / "data" / rel, data / rel)
    return root


src = Mod(SRC_MOD)


def pick_unit():
    """A source unit with officers AND an armour-upgrade list, so the entry list
    spans more than one slot and unticking one really means something."""
    for u in src.edu.units:
        if u.soldier_model and u.officers and u.armour_ug_models:
            return u.type
    raise SystemExit("no unit with officers + armour upgrades in the installed mods")


UNIT = pick_unit()
src_unit = src.edu.by_type()[UNIT]
print(f"source unit {UNIT!r} ({SRC_MOD.name})  ->  models only into {DST_MOD.name}")

# ---- 1) the entry list the composer ticks off -------------------------------
index = unit_model_index(src, UNIT)
names = [r["name"] for r in index]
check("lists at least two entries", len(index) >= 2)
check("names the soldier-line model",
      src_unit.soldier_model.lower() in names)
check("names every officer",
      all(o.lower() in names for o in src_unit.officers))
check("names every armour-upgrade model",
      all(m.lower() in names for m in src_unit.armour_ug_models))
check("each entry carries the slot it fills",
      all(r["slot"] in ("soldier", "mount", "officer", "armour") for r in index))
found = [r for r in index if r["found"]]
check("every found entry names the folder its files live in",
      bool(found) and all(r["folders"] for r in found))
check("folders are data-relative, not absolute",
      all(not Path(f).is_absolute() for r in found for f in r["folders"]))
check("mesh and texture counts are reported",
      all(r["meshes"] >= 1 and r["textures"] >= 1 for r in found))
try:
    unit_model_index(src, "no such unit at all")
    check("an unknown unit raises", False)
except KeyError:
    check("an unknown unit raises", True)

# ---- 2) the plan writes models and nothing else -----------------------------
dest_root = fresh_dest()
dest = Mod(dest_root)
before_units = len(dest.edu.units)
edu_before = (dest_root / "data/export_descr_unit.txt").read_bytes()
loc_before = (dest_root / "data/text/export_units.txt").read_bytes()
db_before = (dest_root / "data/unit_models/battle_models.modeldb").read_bytes()

plan = plan_transfer(src, UNIT, dest, TransferOptions(mode="models"))
check("plan is in models mode", plan.models_mode)
check("no base error", not plan.base_error)
check("no option error", not plan.option_error)
check("adds no unit to the destination", plan.dest_new_units == 0)
check("no unit-name conflict to settle", plan.unit_conflict is False)
check("no icons planned", not plan.icon_files)
check("no mount definition planned", plan.mount_action == "")
check("no projectiles planned", not plan.projectile_raws)
check("no siege engine planned", not plan.engine_raws and not plan.mounted_engine_raws)
check("no voice entry planned", plan.sound_text == "")
check("no M2TWEOP file chosen", plan.eop_file == "")
check("not marked a mercenary", plan.mercenary is False)
check("something is actually being imported",
      bool(plan.add_entries) or bool(plan.model_actions))
check("every planned entry is one of the unit's models",
      all(a.source_name in names for a in plan.model_actions))
check("the summary says no unit is written",
      "BMDB ENTRIES ONLY" in plan.summary())
check("the summary does not claim a unit was written",
      "export_descr_unit.txt" not in plan.summary())

# ---- 3) models_only narrows the import --------------------------------------
one = next(a.source_name for a in plan.model_actions)
narrow = plan_transfer(src, UNIT, dest,
                       TransferOptions(mode="models", models_only=[one]))
check("one ticked entry plans one entry", len(narrow.model_actions) == 1)
check("…and it is the one that was ticked", narrow.model_actions[0].source_name == one)
check("fewer assets than the whole unit's",
      len(narrow.asset_files) <= len(plan.asset_files))

allof = plan_transfer(src, UNIT, dest,
                      TransferOptions(mode="models", models_only=names))
check("naming every model matches naming none",
      len(allof.model_actions) == len(plan.model_actions))

bogus = plan_transfer(src, UNIT, dest,
                      TransferOptions(mode="models",
                                      models_only=[one, "not_a_model_of_this_unit"]))
check("a name that is not one of the unit's models is reported",
      any("not_a_model_of_this_unit" in w for w in bogus.warnings))
check("…and is not imported", len(bogus.model_actions) == 1)

none = plan_transfer(src, UNIT, dest,
                     TransferOptions(mode="models",
                                     models_only=["not_a_model_of_this_unit"]))
check("naming only unknown models is refused", bool(none.option_error))

# ---- 4) a stale base / replace pick is ignored ------------------------------
other = next(u.type for u in dest.edu.units if u.type != UNIT)
stale = plan_transfer(src, UNIT, dest,
                      TransferOptions(mode="models", base_type=other,
                                      replace_type=other))
check("a left-over base_type does not become a base", stale.base_unit is None)
check("…and nothing is replaced", stale.replace_type == "")
check("…and it still writes no unit", stale.dest_new_units == 0)

# ---- 5) apply: the modeldb and the assets, nothing else ---------------------
rec = apply_transfer(plan)
check("applied", rec["applied"])
check("the record is marked a models-only run", rec.get("action") == "models")
check("export_descr_unit.txt untouched",
      (dest_root / "data/export_descr_unit.txt").read_bytes() == edu_before)
check("text/export_units.txt untouched",
      (dest_root / "data/text/export_units.txt").read_bytes() == loc_before)
db_after = (dest_root / "data/unit_models/battle_models.modeldb").read_bytes()
check("battle_models.modeldb rewritten", db_after != db_before)
after = Mod(dest_root)
check("still the same number of units", len(after.edu.units) == before_units)
final_names = {n for n, _ in plan.add_entries}
have = after.modeldb.by_name()
check("every added entry is in the destination modeldb",
      bool(final_names) and all(n in have for n in final_names))
copied = [rel for _, rel in plan.asset_files]
check("the asset files were copied",
      bool(copied) and all((dest_root / "data" / rel).exists() for rel in copied))
check("the modeldb still parses",
      len(modeldb.parse_file(dest_root / "data/unit_models/battle_models.modeldb").entries)
      > 0)

# ---- 6) undo ----------------------------------------------------------------
undo(rec["id"])
check("undo restores battle_models.modeldb byte-for-byte",
      (dest_root / "data/unit_models/battle_models.modeldb").read_bytes() == db_before)
check("undo leaves export_descr_unit.txt alone",
      (dest_root / "data/export_descr_unit.txt").read_bytes() == edu_before)
shutil.rmtree(dest_root, ignore_errors=True)

shutil.rmtree(cfg, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
