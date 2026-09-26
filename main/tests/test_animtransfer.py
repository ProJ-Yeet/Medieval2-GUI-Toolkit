"""Phase 83: port the animations with a unit.

    python -m tests.test_animtransfer

On a throwaway copy of ROCSS's unit files and its four pack files:

1. Planned: DaC's Hobbit Infantry, on EUR_Hobbit_Spear, which ROCSS has not
   got. With "bring its animations" (the default) the skeleton is brought and
   nothing is reported missing; with it off, the old warning stands.
2. Applied: the packs grow by what was planned, every structural check
   passes, the unit's modeldb entry names a skeleton the pack now has, and
   every one of its slots plays out of it.
3. One undo takes the unit, its files and the pack appends away, byte for
   byte.
4. A batch: two units on the same two skeletons, both planned first; the
   second reuses what the first brought.
5. Refused: with the game running nothing is written at all.
6. The modeldb rename of a skeleton, weapon lists included.
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, animview, casanim, config, modeldb, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROCSS, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def shas(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


if not (ROCSS.is_dir() and DAC.is_dir()):
    print("SKIPPED: needs ROCSS and Divide_and_Conquer_EUR installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
real_running = animpack.game_running
animpack.game_running = lambda: []


def fresh_dest(tag):
    root = Path(_tmp.mkdtemp(prefix=f"ut_animxfer_{tag}_")) / "mods" / "Dest"
    for rel in REL:
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROCSS / "data" / rel, root / "data" / rel)
    (root / "data" / "animations").mkdir(parents=True)
    for n in animpack.FILES:
        shutil.copy2(ROCSS / "data" / "animations" / n, root / "data" / "animations" / n)
    return root


dac = Mod(DAC)
UNIT, SKEL = "Hobbit Infantry", "EUR_Hobbit_Spear"

# ---- 1) planned ---------------------------------------------------------------------
print("\n1) planned")
root = fresh_dest("one")
dest = Mod(root)
plan = transfer.plan_transfer(dac, UNIT, dest, transfer.TransferOptions())
port = plan.anim_port
check(f"{SKEL} is not in ROCSS's pack, and the plan brings it",
      port is not None and [s.name for s in port.skeletons] == [SKEL] and port.skeletons[0].action == "add")
check("nothing is reported missing, and the summary says what comes into the packs",
      not plan.missing_skeletons and not plan.soldier_skeletons_missing()
      and "ANIMATIONS BROUGHT" in plan.summary() and SKEL in plan.summary())
t = port.totals()
check(f"{t['animations']} animations, {t['animations append']} to append ({t['anim bytes appended'] / 1e6:.2f} MB)",
      t["animations"] > 100 and t["anim bytes appended"] > 0)
off = transfer.plan_transfer(dac, UNIT, dest, transfer.TransferOptions(bring_animations=False))
check("with bring_animations off, the skeleton is reported missing as before, nothing planned",
      off.anim_port is None and SKEL in off.missing_skeletons and SKEL in off.soldier_skeletons_missing())

# ---- 2) applied ---------------------------------------------------------------------
print("\n2) applied")
before = shas(root / "data")
dat = root / "data" / "animations" / "pack.dat"
size0 = dat.stat().st_size
rec = transfer.apply_transfer(plan)
dest = Mod(root)
c = animpack.check(root / "data" / "animations")
check("every structural check passes on the packs, every slot path indexed",
      c["problems"] == [] and c["anim reads"] == c["anim entries"] and c["skel reads"] == c["skel entries"]
      and c["skel slot paths"] == c["skel slot paths in pack.idx"]
      and c["anim contiguous to the end"] == c["skel contiguous to the end"] == 1)
check(f"pack.dat grew by exactly the planned {t['anim bytes appended']:,} bytes",
      dat.stat().st_size - size0 == t["anim bytes appended"])
u = dest.edu.by_type().get(plan.resolved_type)
e = dest.modeldb.get(u.soldier_model) if u else None
known = animpack.known_skeletons(dest.data, dest.modeldb)
check(f"the unit {plan.resolved_type!r} is written, its entry {e.name if e else '?'} on {SKEL}, "
      "which the pack now has", e is not None and e.skeletons() == [SKEL] and SKEL in known)
sk = animpack.for_data(dest.data).skeleton(SKEL)
bad = []
for i, s in sk.filled():
    try:
        animview.read(dest.data, SKEL, path=s.path)
    except casanim.AnimError as err:
        bad.append((i, str(err)[:50]))
check(f"all {len(sk.filled())} of its slots play out of the destination's own pack", not bad)
check("the log's one job carries the appends and the indexes' backups",
      [r["rel"] for r in rec["manifest"]["appended"]] == ["animations/pack.dat", "animations/skeletons.dat"]
      and {"animations/pack.idx", "animations/skeletons.idx"} <= set(rec["manifest"]["backed_up"]))

# ---- 3) undone ----------------------------------------------------------------------
print("\n3) undone")
transfer.undo(rec["id"])
after = shas(root / "data")
check("every file byte for byte as before, the four packs included (created files gone)",
      after == before)

# ---- 4) a batch ---------------------------------------------------------------------
print("\n4) two units on the same skeletons")
root2 = fresh_dest("batch")
d2 = Mod(root2)
A, B = "Bandobras Archers", "Dwarven Travellers"
pa = transfer.plan_transfer(dac, A, d2, transfer.TransferOptions())
pb = transfer.plan_transfer(dac, B, d2, transfer.TransferOptions())
SHARED = ["MTW2_Hobbit_Bowman", "MTW2_Hobbit_Bowman_Primary", "MTW2_Hobbit_Mace", "MTW2_Hobbit_Mace_Primary"]
names = lambda p: {s.name for s in p.anim_port.skeletons}
check("planned side by side, both would bring the two skeletons and their weapon skeletons",
      set(SHARED) <= names(pa) and set(SHARED) <= names(pb))
ra = transfer.apply_transfer(pa)
rb = transfer.apply_transfer(pb)
acts = {s.name: s.action for s in pb.anim_port.skeletons}
others = sorted(n for n in acts if n not in SHARED)
check(f"applied after the first, the second reuses the four the first brought "
      f"(and brings only its other models' own: {', '.join(others)})",
      all(acts[n] == "reuse" for n in SHARED))
idx = animpack.for_data(root2 / "data").skels
check("no skeleton is in the pack twice", not idx.duplicates())
d2 = Mod(root2)
check("both units written, each entry on skeletons the pack has",
      all(all(s in animpack.known_skeletons(d2.data, d2.modeldb)
              for s in d2.modeldb.get(d2.edu.by_type()[x].soldier_model).skeletons())
          for x in (pa.resolved_type, pb.resolved_type)))
transfer.undo(rb["id"])
transfer.undo(ra["id"])
check("undone newest first, the packs are ROCSS's again",
      all(hashlib.sha1((root2 / "data" / "animations" / n).read_bytes()).digest()
          == hashlib.sha1((ROCSS / "data" / "animations" / n).read_bytes()).digest() for n in animpack.FILES))

# ---- 5) refused ---------------------------------------------------------------------
print("\n5) refused")
root3 = fresh_dest("refused")
p3 = transfer.plan_transfer(dac, UNIT, Mod(root3), transfer.TransferOptions())
b3 = shas(root3 / "data")
animpack.game_running = lambda: ["medieval2.exe"]
try:
    transfer.apply_transfer(p3)
    said = ""
except animpack.PackError as err:
    said = str(err)
animpack.game_running = lambda: []
check("with the game running the transfer is refused, saying why", "medieval2.exe is running" in said)
check("  ... and nothing at all was written, the unit's text files included", shas(root3 / "data") == b3)

# ---- 6) the rename in the modeldb ------------------------------------------------------
print("\n6) a skeleton renamed in a modeldb entry")
ro = Mod(ROCSS)
ent = ro.modeldb.by_name()["duukunasi"]
ren = {"MTW2_Fast_Javelin": "MTW2_Fast_Javelin_dac", "fs_test_shield": "fs_test_shield_dac"}
raw = modeldb.rename_skeletons(ent.raw, ren, pad=ent.first_entry_pad)
spans = modeldb.animation_spans(raw, pad=ent.first_entry_pad)
check("body and weapon names both rewritten, every other name as it was",
      spans[0]["primary"][2] == "MTW2_Fast_Javelin_dac" and spans[0]["secondary"][2] == "MTW2_2HSwordsman"
      and [w[2] for w in spans[0]["weapons"]] == ["MTW2_Javelin_primary", "fs_test_shield_dac",
                                                  "MTW2_2HSwordsman_Primary", "fs_test_shield_dac"])
check("the parsed records say the same", [(a.primary_skeleton, a.pri_weapons) for a in
                                          modeldb.renamed_animations(ent.animations, ren)]
      == [("MTW2_Fast_Javelin_dac", ["MTW2_Javelin_primary", "fs_test_shield_dac"])])
check("an empty map changes nothing", modeldb.rename_skeletons(ent.raw, {}) == ent.raw)
animpack.game_running = real_running

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
