"""A texture imported in the same save as a folder move lands where the entry points.

Reported by a tester: a new unit reusing another unit's model, a new texture
brought in with the Import button, and the mod did not contain it afterwards.
The import is queued for the folder it was picked in, the folder move then
repoints the entry at the new folder, and the move cannot carry a file that is
not on disk yet - so the copy went to the old folder while the modeldb named
the new one. Covered in the three orders the page (or a raw request) can send:
move set before the import, import made before the move, and a request that
names the old folder for both the import and the texture box.

Works on a throwaway copy of ROCSS's data files; the real mod is never touched.
"""
import re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, edit, modeldb
from unittransfer.mod import Mod

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
SRC_MOD = MODS / "ROCSS"

ok = []
def check(label, cond):
    ok.append(bool(cond)); print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

root = Path(_tmp.mkdtemp(prefix="ut_impmove_"))
data = root / "data"
(data / "text").mkdir(parents=True); (data / "unit_models").mkdir(parents=True)
for rel in ("export_descr_unit.txt", "text/export_units.txt",
            "unit_models/battle_models.modeldb"):
    shutil.copy2(SRC_MOD / "data" / rel, data / rel)
imports = Path(_tmp.mkdtemp(prefix="ut_import_"))
src = imports / "tripoli.texture"; src.write_bytes(b"TEX-TRIPOLI")

mod = Mod(root)
unit = next(u for u in mod.edu.units if u.model_names()
            and u.model_names()[0].lower() in mod.modeldb.by_name())
entry = mod.modeldb.by_name()[unit.model_names()[0].lower()]
cur = next(s["value"] for s in modeldb.path_slots(entry) if s["kind"] == "texture")
old_dir = cur.rsplit("/", 1)[0]
MOVE = "unit_models/_tripoli"
NEW = MOVE + "/textures/tripoli.texture"
print(f"unit={unit.type!r} entry={entry.name!r} texture dir={old_dir!r}")


def request(dest_dir, value):
    return edit.request_from_dict({"unit": unit.type, "model_edits": [{
        "entry": entry.name, "imports": [{"src": str(src), "dest_dir": dest_dir}],
        "defaults": {"texture": value}, "faction_paths": {}, "move_dir": MOVE}]})


def pointed(plan):
    raw = plan.entry_updates.get(entry.name, "")
    return sorted({p for p in re.findall(r"[\w/.]+", raw) if p.endswith("tripoli.texture")})


cases = {
    "move set, then the texture imported": (MOVE + "/textures", NEW),
    "texture imported, then the move set": (old_dir, NEW),
    "old folder named for both": (old_dir, old_dir + "/tripoli.texture"),
}
for label, (dest_dir, value) in cases.items():
    print(f"\n{label}")
    plan = edit.plan_edit(Mod(root), request(dest_dir, value))
    copied = [r for _s, r in plan.copies if r.endswith("tripoli.texture")]
    check("plans without errors", not plan.errors)
    check("the entry points at the moved folder", pointed(plan) == [NEW])
    check("the import is copied to exactly that path", copied == [NEW])
    check("no 'put the file there yourself' warning for it",
          not any("/tripoli.texture is not on disk" in w for w in plan.warnings))

print("\napply the import-then-move case")
plan = edit.plan_edit(Mod(root), request(old_dir, NEW))
res = edit.apply_edit(plan)
check("the imported texture is in the mod where the modeldb names it",
      (data / NEW).is_file() and (data / NEW).read_bytes() == b"TEX-TRIPOLI")
check("and not stranded in the old folder",
      not (data / old_dir / "tripoli.texture").exists())
from unittransfer.transfer import undo
undo(res["record"]["id"] if "record" in res else res["id"])
check("undo removes it again", not (data / NEW).exists())

print(f"\n{sum(ok)}/{len(ok)} checks passed")
shutil.rmtree(root, ignore_errors=True); shutil.rmtree(imports, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)
sys.exit(0 if all(ok) else 1)
