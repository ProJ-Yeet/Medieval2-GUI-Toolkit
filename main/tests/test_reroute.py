"""End-to-end test: reroute / mod_folder asset relocation + bmdb path rewriting.

Applies a transfer with assets relocated into unit_models/<mod>, then verifies:
  * every mesh/texture actually landed under the new folder
  * the destination modeldb still parses cleanly (length prefixes correct)
  * the added entry's paths point at the new location, and the files exist
  * nothing was written to the original paths
  * undo restores the modeldb byte-exact and removes the copied files
Uses temp config + temp dest so the real mods are never touched.
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, modeldb
from unittransfer.mod import Mod
from unittransfer.transfer import TransferOptions, plan_transfer, apply_transfer, undo

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
mdb_path = data / "unit_models/battle_models.modeldb"
orig_mdb = mdb_path.read_bytes()

src = Mod(TATR)
plan = plan_transfer(src, UNIT, Mod(dest_root), TransferOptions(asset_conflict="mod_folder"))
target = plan.reroute_dir
print("reroute dir:", target, "| remapped:", len(plan.path_map))
check("reroute dir is unit_models/<mod>", target == "unit_models/Third_Age_Reforged")
check("path_map non-empty", len(plan.path_map) > 0)

rec = apply_transfer(plan)

# 1) files landed under the new folder, not the old one
new_files = [data / r for _, r in plan.asset_files]
check("all relocated files exist on disk", all(p.exists() for p in new_files))
check("all relocated files are under target", all(
    r.startswith(target + "/") for old, r in plan.path_map.items() for r in [plan.path_map[old]]))
old_written = [data / old for old in plan.path_map if (data / old).exists()]
check("original paths NOT written", not old_written)

# 2) modeldb still parses cleanly and the new entry points at the new paths
db2 = modeldb.parse_file(mdb_path)
check("destination modeldb re-parses clean", len(db2.entries) > 0)
added_names = [n for n, _ in plan.add_entries]
by_name = db2.by_name()
check("added entries present in dest modeldb", all(n in by_name for n in added_names))
bad = []
for n in added_names:
    e = by_name[n]
    for p in e.mesh_files() + e.texture_files():
        if p.startswith("unit_models/") and not p.startswith(target + "/"):
            bad.append((n, p))
check("added entries reference ONLY the new folder", not bad)
if bad:
    print("     offending:", bad[:3])

# 3) every path the entry references actually exists on disk
missing = []
for n in added_names:
    for p in by_name[n].mesh_files() + by_name[n].texture_files():
        if p.startswith(target + "/") and not (data / p).exists():
            missing.append(p)
check("every rewritten path resolves to a real file", not missing)
if missing:
    print("     missing:", missing[:3])

# 4) whole-file integrity: the written file re-serialises to itself exactly
# (compare text-to-text: on Windows read/write translate CRLF<->LF consistently)
check("modeldb round-trips exactly after edit",
      db2.to_text() == mdb_path.read_text(encoding=modeldb.ENCODING))
# and the header entry count matches the real number of entries
check("modeldb header count == entries+1",
      db2.header_ints[5] == len(db2.entries) + 1)

# 5) undo restores
undo(rec["id"])
check("undo restored modeldb byte-exact", mdb_path.read_bytes() == orig_mdb)
check("undo removed relocated files", not any(p.exists() for p in new_files))

# 6) a reroute puts the files IN the picked folder: the source's own folder
# (unit_models/_Units/<x>/) is dropped, not nested under the pick, which read
# as <pick>/_Units/<x>/ in the tester's report.
from unittransfer.transfer import _reroute_drops
pick = "unit_models/_units/umbar_swap"
rp = plan_transfer(src, UNIT, Mod(dest_root),
                   TransferOptions(asset_conflict="reroute", asset_reroute_dir=pick))
drops = _reroute_drops(rp.path_map)
print("reroute drops:", drops)
# this unit pulls from _Units/<x>/ AND AttachmentSets/, the usual pair
check("reroute: each source tree's own folder is dropped",
      len(drops) >= 2 and all(d != "unit_models" for d in drops))
check("reroute: no source tree name is repeated under the pick", not any(
    new.lower().startswith((pick + "/" + top).lower() + "/")
    for new in rp.path_map.values() for top in ("_Units", "AttachmentSets")))
check("reroute: no two files land on one path",
      len({v.lower() for v in rp.path_map.values()}) == len(rp.path_map))
# and when two would collide, the whole structure is kept instead
check("reroute: a collision keeps the full structure", _reroute_drops([
    "unit_models/_Units/A/x.texture", "unit_models/AttachmentSets/x.texture"]) == ())
check("reroute: one tree lands flat", _reroute_drops([
    "unit_models/_Units/Umbar/a.mesh", "unit_models/_units/umbar/textures/b.texture"])
    == ("unit_models/_Units/Umbar",))
rrec = apply_transfer(rp)
check("reroute: the copied files exist", all((data / r).exists() for r in rp.path_map.values()))
db3 = modeldb.parse_file(mdb_path).by_name()
check("reroute: the added entries point into the pick", all(
    p.startswith(pick + "/") for n, _ in rp.add_entries
    for p in db3[n].mesh_files() + db3[n].texture_files() if p.lower().startswith("unit_models/")))
undo(rrec["id"])
check("reroute: undo restored modeldb byte-exact", mdb_path.read_bytes() == orig_mdb)

shutil.rmtree(dest_root, ignore_errors=True); shutil.rmtree(cfg, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
