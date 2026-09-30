"""Copy only the skins the new owners wear - Phase 92c.

A unit with a dozen faction skins brings a dozen sets of .texture files for a
faction that wears one. With ``own_skins_only`` each copied entry keeps the
records of its final owners only (plus ``slave`` for a rebel or mercenary), the
files only the dropped records named are not copied, and the plan says what
that saved. Off by default.

A Tsardoms 3.0 unit with many skins, into a temp copy of Third Age Reforged's
three DB files, with a config of its own.

    python -m tests.test_transfer_skins
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from tests._realmod import MODS  # noqa: E402
from unittransfer import config, edu as edu_mod, modeldb as mdb  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


TSAR, TATR = MODS / "Tsardoms-3.0", MODS / "Third_Age_Reforged"
if not (TSAR.is_dir() and TATR.is_dir()):
    print("  [skip] needs Tsardoms-3.0 and Third_Age_Reforged")
    sys.exit(0)

from unittransfer.transfer import TransferOptions, apply_transfer, plan_transfer  # noqa: E402

tmp = Path(_tmp.mkdtemp(prefix="ut_skins_"))
cfg = tmp / "cfg"
cfg.mkdir()
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"
root = tmp / "Dest"
for rel in ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
            "descr_sm_factions.txt"):
    (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TATR / "data" / rel, root / "data" / rel)

src, dst = Mod(TSAR), Mod(root)
have = {e.name for e in dst.modeldb.entries}
unit = max((u for u in src.edu.units if u.soldier_model and not u.mount
            and u.soldier_model.lower() not in have
            and src.modeldb.get(u.soldier_model) is not None
            and (TSAR / "data").joinpath(src.modeldb.get(u.soldier_model).main_textures[0].texture).is_file()),
           key=lambda u: len(src.modeldb.get(u.soldier_model).main_textures))
nskins = len(src.modeldb.get(unit.soldier_model).main_textures)
print(f"\n  {unit.type}: {nskins} skins on {unit.soldier_model}")

off = plan_transfer(src, unit.type, dst, TransferOptions())
on = plan_transfer(src, unit.type, dst, TransferOptions(own_skins_only=True))
block = edu_mod._parse_block
check("off by default: nothing is left out", not TransferOptions().own_skins_only
      and off.skins_dropped == 0)
owners = None
for _n, e in on.add_entries:
    facs = [t.faction for t in e.main_textures]
    owners = facs
    break
check(f"on: the entry keeps its owners' skins only ({owners})",
      owners and len(owners) < nskins)
check(f"  {on.skins_dropped} records left out, {on.skins_saved_files} files and "
      f"{on.skins_saved_bytes / 1e6:.1f} MB not copied",
      on.skins_dropped > 0 and on.skins_saved_files > 0
      and len(on.asset_files) == len(off.asset_files) - on.skins_saved_files)
check("  and the plan says so", any("ONLY THE OWNERS' SKINS" in str(w) for w in on.warnings))
rec = apply_transfer(on)
wrote = mdb.parse_file(root / "data" / "unit_models" / "battle_models.modeldb")
name = on.add_entries[0][0]
got = wrote.get(name)
check("applied: the file reads back, the entry's counts agreeing with its records",
      got is not None and [t.faction for t in got.main_textures] == owners)
kept = {t.texture.lower() for t in got.main_textures}
missing = [t for t in kept if not (root / "data" / t).is_file()
           and (TSAR / "data" / t).is_file()]
check("  every texture it keeps was copied", not missing)
shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
