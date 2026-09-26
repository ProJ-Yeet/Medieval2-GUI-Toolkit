"""Phase 85: pack housekeeping.

    python -m tests.test_packhouse

1. Which entry a slot plays: the first copy at the skeleton's own scale, else
   the first at the smallest scale; a skeleton name's first copy.
2. The report on all three installs: every entry accounted for, every slot
   resolved. Measured 2026-09-26: nothing unplayed in any of them; DaC's 808
   and Reforged's 102 paths listed more than once are all at scales of their
   own, and every copy is played.
3. A copy of ROCSS given one of each kind of waste (a dead copy, a copy at a
   scale no skeleton has, a path no slot names, a skeleton listed twice): the
   report finds each, and a compaction writes the four files back to ROCSS's
   own, byte for byte, logged as one job. Undo puts the wasteful ones back.
4. Refused: nothing to compact; the game running; an undo after the packs
   were written again. Forgetting the kept packs frees them and ends the Undo.
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, animview, casanim, config, packhouse, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROCSS = MODS / "ROCSS"
INSTALLS = [MODS / n for n in ("ROCSS", "Divide_and_Conquer_EUR", "Third_Age_Reforged")]
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def shas(anim_dir: Path) -> dict:
    return {n: hashlib.sha1((anim_dir / n).read_bytes()).hexdigest() for n in animpack.FILES}


def refused(fn, *words):
    try:
        fn()
    except animpack.PackError as e:
        return all(w in str(e) for w in words)
    return False


if not ROCSS.is_dir():
    print("SKIPPED: needs ROCSS installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
animpack.game_running = lambda: []

# ---- 1) resolution ------------------------------------------------------------------
print("\n1) which entry a slot plays")
E = animpack.PackEntry
idx = animpack.PackIndex(animpack.ANIM_MAGIC, [
    E("a.cas", 20, 1, 2.0, 1, 1, 1), E("a.cas", 21, 1, 1.0, 1, 1, 1), E("A.CAS", 22, 1, 1.0, 1, 1, 1),
    E("b.cas", 23, 1, 3.0, 1, 1, 1), E("b.cas", 24, 1, 0.5, 1, 1, 1), E("b.cas", 25, 1, 0.5, 1, 1, 1)],
    9, 0)
check("its own scale when there is a copy at it, the first of two",
      animpack.resolve_slot(idx, "a.cas", 1.0).offset == 21)
check("else the first copy at the smallest scale, rescaled",
      animpack.resolve_slot(idx, "b.cas", 1.0).offset == 24)
check("a path the pack has not got plays nothing", animpack.resolve_slot(idx, "c.cas", 1.0) is None)

# ---- 2) the installs ----------------------------------------------------------------
print("\n2) the report on every install")
for mod_root in INSTALLS:
    if not mod_root.is_dir():
        continue
    mod = Mod(mod_root)
    r = packhouse.report(mod.data, mod)
    p = r.payload()
    whole = len(r.keep_anims) + len(r.dead) + len(r.other_scale) + len(r.unused) == r.anims
    check(f"{mod_root.name}: {r.anims:,} animations, {r.skels} skeletons, every entry accounted for, "
          f"every slot resolved; {p['duplicate_paths']} path(s) listed more than once, "
          f"{p['duplicate_paths_same_scale']} at one scale twice; {len(r.unnamed)} skeleton(s) no model names",
          not r.error and whole and r.missing_slots == 0 and len(r.keep_skels) + sum(
              len(v) - 1 for v in r.skel_twice.values()) == r.skels)
    check(f"{mod_root.name}: nothing unplayed (measured 2026-09-26)",
          not r.worth_compacting and p["duplicate_paths_same_scale"] == 0)

# ---- 3) a wasteful copy of ROCSS ----------------------------------------------------
print("\n3) a copy of ROCSS with waste in it, compacted and undone")


def fresh(tag):
    root = Path(_tmp.mkdtemp(prefix=f"ut_house_{tag}_")) / "mods" / "Dest"
    for rel in REL:
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROCSS / "data" / rel, root / "data" / rel)
    (root / "data" / "animations").mkdir(parents=True)
    for n in animpack.FILES:
        shutil.copy2(ROCSS / "data" / "animations" / n, root / "data" / "animations" / n)
    return root


original = shas(ROCSS / "data" / "animations")
root = fresh("waste")
anim_dir = root / "data" / "animations"
packs = animpack.open_packs(anim_dir)
sk_entry = packs.skels.entries[5]
sk = packs.skeleton(sk_entry.name)
slot_path = sk.filled()[3][1].path
played = animpack.resolve_slot(packs.anims, slot_path, sk.scale)
body = packs.anims.read_entry(played)
junk = [(E(played.name, 0, played.size, played.scale, played.frames, played.rot_bones, played.pos_bones), body),
        (E(played.name, 0, played.size, 3.7, played.frames, played.rot_bones, played.pos_bones), body),
        (E("mods/Dest/data/animations/nobody/plays_this.cas", 0, played.size, 1.0, played.frames,
           played.rot_bones, played.pos_bones), body)]
animpack._append(packs.anims, junk, "animations/pack.dat")
animpack._append(packs.skels, [(E(sk_entry.name, 0, sk_entry.size), packs.skels.read_entry(sk_entry))],
                 "animations/skeletons.dat")
wasteful = shas(anim_dir)
mod = Mod(root)
r = packhouse.report(mod.data, mod)
check("the report finds the dead copy, the copy at a scale nothing plays, the unused path, "
      "and the skeleton listed twice",
      [e.name for e in r.dead] == [played.name]
      and len(r.other_scale) == 1 and abs(r.other_scale[0].scale - 3.7) < 1e-6
      and [e.name for e in r.unused] == [junk[2][0].name]
      and list(r.skel_twice) == [sk_entry.name] and r.anim_freed == 3 * played.size
      and r.skel_freed == sk_entry.size)
rec = packhouse.compact(mod)
check("compacted: the four files are ROCSS's own again, byte for byte", shas(anim_dir) == original)
c = animpack.check(anim_dir)
check("every structural check passes, every slot path indexed",
      c["problems"] == [] and c["skel slot paths"] == c["skel slot paths in pack.idx"])
bad = []
for e, s in list(animpack.iter_skeletons(animpack.open_packs(anim_dir)))[:20]:
    for i, slot in s.filled()[:5]:
        try:
            animview.read(root / "data", e.name, path=slot.path)
        except casanim.AnimError as err:
            bad.append(str(err)[:40])
check("the viewer plays the first twenty skeletons' slots out of the compacted pack", not bad)
block = rec["manifest"]["compacted"]
kept = root / block["kept"]
check("logged as one job; the replaced packs kept whole outside data/",
      rec["action"] == "pack compact" and kept.is_dir() and not str(block["kept"]).startswith("data")
      and hashlib.sha1((kept / "pack.dat").read_bytes()).hexdigest() == wasteful["pack.dat"])
transfer.undo(rec["id"])
check("undone: the wasteful four back, byte for byte, the kept folder gone",
      shas(anim_dir) == wasteful and not (root / animpack.COMPACT_DIR).exists())

# ---- 4) refusals, and forgetting ----------------------------------------------------
print("\n4) refused, and forgotten")
clean = fresh("clean")
check("nothing to compact on ROCSS as it is",
      refused(lambda: packhouse.compact(Mod(clean)), "nothing to compact"))
animpack.game_running = lambda: ["medieval2.exe"]
check("refused with the game running, nothing written",
      refused(lambda: packhouse.compact(mod), "running") and shas(anim_dir) == wasteful)
animpack.game_running = lambda: []
rec = packhouse.compact(mod)
p2 = animpack.open_packs(anim_dir)
animpack._append(p2.anims, [junk[2]], "animations/pack.dat")
after = shas(anim_dir)
try:
    transfer.undo(rec["id"])
    undo_refused = False
except animpack.PackError as e:
    undo_refused = "no longer the file" in str(e)
check("an undo after the pack was written again is refused, and touches nothing",
      undo_refused and shas(anim_dir) == after)
freed = packhouse.forget_backup(root, rec["manifest"]["compacted"])
check(f"forgotten: the kept packs deleted, {freed / 1e6:.0f} MB freed",
      freed > 60e6 and not (root / animpack.COMPACT_DIR).exists())

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
