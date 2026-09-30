"""Recruitment set up by the transfer - Phase 92b.

"Let the faction recruit them": the transfer adds the unit's recruit pools in
the same job, through the Recruitment tab's own writer (buildings.plan_edit).

    A  a renamed copy of a unit the destination has: the original's pools are
       copied for the new type, their factions narrowed to its owners
    B  a new unit: the pools that recruit it in the source, in the levels of
       the same name here
    C  neither: said, "not recruitable"
    and: applied it writes the EDB with the unit, and one Undo takes both back

Temp copies of Third Age Reforged's files, with a config of their own.

    python -m tests.test_transfer_recruit
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from tests._realmod import MODS  # noqa: E402
from unittransfer import buildings as bld, config  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


TATR, TSAR = MODS / "Third_Age_Reforged", MODS / "Tsardoms-3.0"
if not TATR.is_dir():
    print("  [skip] needs Third_Age_Reforged")
    sys.exit(0)
from unittransfer.transfer import (TransferOptions, _narrow_factions,  # noqa: E402
                                   apply_transfer, plan_transfer, undo)

print("\n0) the factions list, narrowed")
check("held to the owners", _narrow_factions("factions { sicily, denmark, }  and x 30",
                                             ["sicily"], False) == "factions { sicily, }  and x 30")
check("none of them an owner: not for this unit", _narrow_factions("factions { denmark, }", ["sicily"], False) is None)
check("  unless filling, then the owners", _narrow_factions("factions { denmark, }", ["sicily"], True) == "factions { sicily, }")
check("no list at all: one is given", _narrow_factions("x 30", ["sicily"], False) == "factions { sicily, }  and x 30")

tmp = Path(_tmp.mkdtemp(prefix="ut_recruit_"))
cfg = tmp / "cfg"
cfg.mkdir()
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"
FILES = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
         "descr_sm_factions.txt", "export_descr_buildings.txt")


def copy(name: str) -> Path:
    root = tmp / name
    for rel in FILES:
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TATR / "data" / rel, root / "data" / rel)
    return root


src = Mod(TATR)
UNIT = "Gondor Spearmen"
orig = [(bl.name, blk.name, p.requires) for bl in src.edb.buildings for blk in bl.blocks
        for p in blk.recruits if p.unit == UNIT]
print(f"\n  {UNIT}: {len(orig)} pools in Reforged")

print("\nA) a renamed copy")
a = copy("A")
edb_before = (a / "data" / bld.EDB_REL).read_bytes()
opts = TransferOptions(on_conflict="rename", new_type="Gondor Spearmen Copy",
                       new_dictionary="gondor_spearmen_copy", set_recruitment=True)
p = plan_transfer(src, UNIT, Mod(a), opts)
check(f"each of the original's pools, for the new type ({len(p.recruit_pools)})",
      p.recruit_text and len(p.recruit_pools) == len(orig))
check("  its factions held to the unit's owners",
      all("factions {" in r for _l, _v, r in p.recruit_pools))
off = plan_transfer(src, UNIT, Mod(a), TransferOptions(on_conflict="rename", new_type="Gondor Spearmen Copy",
                                                       new_dictionary="gondor_spearmen_copy"))
check("  off by default: nothing is added", not off.recruit_text and not off.recruit_pools)
rec = apply_transfer(p)
edb = bld.parse_text((a / "data" / bld.EDB_REL).read_text(encoding=bld.ENCODING))
got = [(bl.name, blk.name) for bl in edb.buildings for blk in bl.blocks
       for q in blk.recruits if q.unit == "Gondor Spearmen Copy"]
check(f"applied: the EDB trains the new type in {len(got)} places",
      sorted(got) == sorted((l, v) for l, v, _r in orig))
check("  and the EDU has the unit", "Gondor Spearmen Copy" in {u.type for u in Mod(a).edu.units})
undo(rec["id"])
check("  one Undo takes the pools back with the unit, byte for byte",
      (a / "data" / bld.EDB_REL).read_bytes() == edb_before)

print("\nB) a new unit")
b = copy("B")
edu = (b / "data" / "export_descr_unit.txt").read_text(encoding="latin-1")
blocks = re.split(r"(?m)^(?=type\s)", edu)
edu = "".join(x for x in blocks if not re.match(r"type\s+Gondor Spearmen\s*$", x.splitlines()[0] if x else ""))
(b / "data" / "export_descr_unit.txt").write_text(edu, encoding="latin-1", newline="")
et = (b / "data" / bld.EDB_REL).read_text(encoding="latin-1")
et = "".join(ln for ln in et.splitlines(True) if '"Gondor Spearmen"' not in ln)
(b / "data" / bld.EDB_REL).write_text(et, encoding="latin-1", newline="")
dst = Mod(b)
check("the destination has neither the unit nor its pools",
      UNIT not in {u.type for u in dst.edu.units})
p = plan_transfer(src, UNIT, dst, TransferOptions(set_recruitment=True))
check(f"its pools land in the levels of the same name ({len(p.recruit_pools)})",
      p.recruit_text and sorted((l, v) for l, v, _r in p.recruit_pools)
      == sorted((l, v) for l, v, _r in orig))

print("\nC) nowhere to put it")
if TSAR.is_dir():
    ts = Mod(TSAR)
    unit = next(u for u in ts.edu.units if u.type not in {x.type for x in src.edu.units}
                and any(q.unit == u.type for bl in ts.edb.buildings for blk in bl.blocks
                        for q in blk.recruits)
                and not any(src.edb.get(bl.name) and src.edb.get(bl.name).level(blk.name)
                            for bl in ts.edb.buildings for blk in bl.blocks
                            for q in blk.recruits if q.unit == u.type))
    p = plan_transfer(ts, unit.type, Mod(copy("C")), TransferOptions(set_recruitment=True))
    check(f"{unit.type} from Tsardoms: no level of its names here, and it says so",
          not p.recruit_text and "NOT RECRUITABLE" in p.recruit_none)
else:
    print("  [skip] needs Tsardoms-3.0")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
