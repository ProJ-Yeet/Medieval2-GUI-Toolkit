"""Phase 79: transfer holds a model's skeletons against the destination's pack.

    python -m tests.test_transfer_skeletons

1. The modeldb's weapon lists read as skeleton names.
2. known_skeletons: a mod's own skeletons.idx when it has one, case-blind;
   every body and weapon name its modeldb uses when it has none.
3. A DaC unit planned into a throwaway copy of ROCSS's four files with a
   small skeletons.idx: with every ROCSS skeleton listed nothing is missing;
   with its body skeleton left out of the pack it is reported missing although
   the destination's modeldb names it; a weapon skeleton left out is reported
   apart, with the rule that says when it matters. Without a pack the old
   modeldb check is what runs.
4. Health: ROCSS's own pack lacks exactly three weapon skeletons, DaC's
   nothing, a mod with no pack is not checked.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, config, health, skelslots  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer.transfer import TransferOptions, plan_transfer  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROCSS, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt",
       "unit_models/battle_models.modeldb", "descr_mount.txt")
# The detection is what this suite is about, so every plan here has Phase 83's
# "bring its animations" off: on, a missing skeleton is brought, not reported
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


if not (ROCSS.is_dir() and DAC.is_dir()):
    print("SKIPPED: needs ROCSS and Divide_and_Conquer_EUR installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"


def write_skeleton_index(anim_dir: Path, names):
    """A skeletons.idx naming ``names``, each an empty entry: what a transfer
    reads is the list of names, never a skeleton's bytes."""
    anim_dir.mkdir(parents=True, exist_ok=True)
    idx = animpack.PackIndex(animpack.SKEL_MAGIC,
                             [animpack.PackEntry(n, animpack.HEADER_SIZE, 0) for n in names], 14, 24)
    (anim_dir / "skeletons.idx").write_bytes(idx.to_bytes())
    (anim_dir / "skeletons.dat").write_bytes(idx.header())


# ---- 1) weapon lists -----------------------------------------------------------------
print("\n1) the modeldb's weapon lists")
rocss, dac = Mod(ROCSS), Mod(DAC)
e = rocss.modeldb.get("mounted_luchniki")
check("an entry's weapon skeletons, primary then secondary",
      e is not None and "MTW2_axe_Primary" in e.weapon_skeletons()
      and not set(e.weapon_skeletons()) & set(e.skeletons()))

# ---- 2) known_skeletons --------------------------------------------------------------
print("\n2) what the destination has")
k = animpack.known_skeletons(rocss.data, rocss.modeldb)
check(f"ROCSS: its own pack, {len(k)} skeletons", k.source == "pack" and len(k) == 208)
check("looked up case-blind", "mtw2_2hswordsman" in k and "MTW2_2HSWORDSMAN" in k and "" not in k)
check("a weapon skeleton its modeldb names but its pack has not got is not there",
      "MTW2_axe_Primary" not in k)
bare = Path(_tmp.mkdtemp(prefix="ut_skel_")) / "data"
(bare / "unit_models").mkdir(parents=True)
shutil.copy2(ROCSS / "data" / REL[2], bare / REL[2])
k2 = animpack.known_skeletons(bare, Mod(bare.parent).modeldb)
check("no pack: every body and weapon name the modeldb uses, weapons included",
      k2.source == "modeldb" and "MTW2_axe_Primary" in k2 and "mtw2_2hswordsman" in k2)

# ---- 3) a transfer ------------------------------------------------------------------
print("\n3) a DaC unit into a copy of ROCSS")
dest_root = Path(_tmp.mkdtemp(prefix="ut_dest_"))
for rel in REL:
    (dest_root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROCSS / "data" / rel, dest_root / "data" / rel)
anim_dir = dest_root / "data" / "animations"
all_rocss = [x.name for x in animpack.for_data(rocss.data).skels.entries]

UNIT = "Uruk Bodyguard"
write_skeleton_index(anim_dir, all_rocss)
plan = plan_transfer(dac, UNIT, Mod(dest_root), TransferOptions(bring_animations=False))
body = sorted({s for _n, x in plan.add_entries for s in x.skeletons()})
weapons = sorted({s for _n, x in plan.add_entries for s in x.weapon_skeletons()})
check(f"'{UNIT}' with every ROCSS skeleton in the pack: nothing missing, read from the pack "
      f"({len(body)} body, {len(weapons)} weapon skeletons named)",
      plan.skeletons_from == "pack" and not plan.missing_skeletons
      and not plan.missing_weapon_skeletons and body and weapons)

gone_body, gone_weapon = body[0], weapons[0]
dest_db = Mod(dest_root).modeldb
check(f"the destination's modeldb names '{gone_body}'",
      any(gone_body in x.skeletons() for x in dest_db.entries))
write_skeleton_index(anim_dir, [n for n in all_rocss
                                if n.lower() not in (gone_body.lower(), gone_weapon.lower())])
plan = plan_transfer(dac, UNIT, Mod(dest_root), TransferOptions(bring_animations=False))
check("left out of the pack, it is missing although the modeldb names it",
      gone_body in plan.missing_skeletons and plan.skeleton_models.get(gone_body))
check("a weapon skeleton left out is reported apart, with the models naming it",
      plan.missing_weapon_skeletons == [gone_weapon]
      and gone_weapon not in plan.missing_skeletons
      and plan.weapon_skeleton_models.get(gone_weapon))
text = plan.summary()
check("the summary says it was the skeleton pack that was read",
      "skeleton pack" in text and "'s modeldb" not in text)
check("  ... the weapon line names Makanyane's rule",
      "WEAPON ANIMATION" in text and "weighted to the weapon bones" in text)

shutil.rmtree(anim_dir)
plan = plan_transfer(dac, UNIT, Mod(dest_root), TransferOptions(bring_animations=False))
check("with no pack the modeldb is read, as before, and says so",
      plan.skeletons_from == "modeldb" and gone_body not in plan.missing_skeletons
      and "skeleton pack" not in plan.summary())

plan = plan_transfer(dac, "Goblin Bodyguards", rocss, TransferOptions(bring_animations=False))
check("into ROCSS itself: 'Goblin Bodyguards' needs MTW2_Goblin_Mace, and its weapon "
      "skeleton is listed apart",
      "MTW2_Goblin_Mace" in plan.missing_skeletons
      and plan.missing_weapon_skeletons == ["MTW2_Goblin_Mace_Primary"])

# ---- 4) Health ----------------------------------------------------------------------
print("\n4) Health")
src = next(s for s in health.SOURCES if s.id == "skeletons")
found = src.run(rocss, None)
check("ROCSS: exactly the three weapon skeletons its own pack has not got",
      sorted((f.what, f.severity) for f in found) == [
          ("mounted_al_mushat|MTW2_HR_mace_Primary", "warn"),
          ("mounted_luchniki_ug1|MTW2_axe_Primary", "warn"),
          ("mounted_luchniki|MTW2_axe_Primary", "warn")])
check("each opens its entry on the Models Editor",
      all(f.open == {"mode": "bmdb", "name": f.what.split("|")[0]} for f in found))
check("DaC: none", src.run(dac, None) == [])
check("a mod with no pack of its own is not checked",
      skelslots.modeldb_findings(Mod(bare.parent)) == [])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
