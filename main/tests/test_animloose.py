"""Phase 84: keep a ported mod rebuildable.

    python -m tests.test_animloose

1. Every animation ROCSS's pack holds, and every tenth of DaC's skeletons',
   written as a loose .cas, reads back as one, and packs back the engine's way
   to the entry it came from.
2. Every slot on ROCSS and DaC, written as an ``anim`` line's flags, reads back
   as the slot: defence, probability, facing, impact point and frame, turn
   limits, launch direction.
3. A slot's cues, written as an .evt file, read back as its events.
4. A rendered type block reads back through the toolkit's own
   descr_skeleton.txt reader in step with the packed skeleton, slot for slot.
5. Unit Transfer on a copy of ROCSS: DaC's Hobbit Infantry brings
   EUR_Hobbit_Spear, and with it a loose .cas for each animation it plays, its
   .evt files and a block at the end of descr_skeleton.txt; the rest of that
   file, its Version line included, is as it was; the block is in step with
   the pack; each written file packs back to the pack's entry. One undo takes
   it all away, folders included, byte for byte.
6. Switched off, only the packs are written. A destination with no
   descr_skeleton.txt of its own gets nothing, and a warning.
7. Where a loose file goes.
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animloose, animpack, casanim, config, skelslots, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROCSS, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt", "descr_skeleton.txt")
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

YC = {i for n in animloose.Y_COMPENSATED for i in skelslots.slots_of(n)}


def packs_back(packs, skel, slot_i, data, scale):
    """The entry's own loose file, read and packed again the engine's way."""
    anim = casanim.read_anim_bytes(animloose.cas_bytes(data, skel.bone_table(), scale, "x.cas", skel.scale),
                                   "x.cas")
    gen = slot_i != animloose.DEFAULT_SLOT
    return any(animloose.floats_close(animloose.to_packed(anim, scale, g, slot_i in YC, r), data)
               for g in (gen, not gen) for r in (False, True))


# Measured 2026-09-26: the one entry of those checked that no .cas packs into.
# DaC holds this path four times, at scales 0.89, 1.0, 1.3 and 2.1, and the
# first, labelled 0.89, carries its pelvis at 1.3 times its still root: the
# engine's output for a file with no pelvis keys, built at 1.3.
UNPACKABLE = {"mods/third_age_3/data/animations/mtw2_knifeman/weapon/knife_default.cas"}

# ---- 1) animations ------------------------------------------------------------------
print("\n1) every animation, to a loose .cas and packed back")
for mod, every in ((ROCSS, 1), (DAC, 10)):
    packs = animpack.for_data(mod / "data")
    seen, good, bad = set(), 0, []
    with open(packs.anims.dat_path, "rb") as f:
        for n, (_e, sk) in enumerate(animpack.iter_skeletons(packs)):
            if n % every:
                continue
            for i, s in sk.filled():
                e = packs.anims.first(s.path)
                if e is None or (e.offset, sk.scale) in seen:
                    continue
                seen.add((e.offset, sk.scale))
                if packs_back(packs, sk, i, packs.anims.read_entry(e, f), e.scale):
                    good += 1
                elif animpack._key(s.path) in UNPACKABLE:
                    seen.discard((e.offset, sk.scale))
                elif len(bad) < 3:
                    bad.append(s.path)
    check(f"{mod.name}: {good:,} of {len(seen):,} animations pack back to their entry{' ' + str(bad) if bad else ''}",
          good == len(seen) and good > 1000)

# ---- 2) flags -----------------------------------------------------------------------
print("\n2) every slot as an anim line's flags")
for mod in (ROCSS, DAC):
    packs = animpack.for_data(mod / "data")
    n, bad = 0, []
    for e, sk in animpack.iter_skeletons(packs):
        for i, s in sk.filled():
            n += 1
            frames = packs.anims.first(s.path).frames
            r = animloose.read_flags(" ".join(animloose.slot_flags(s, frames)))
            same = (r.get("defence", 0) == s.evade_parry and r.get("prob", 50) == s.probability
                    and bool(r.get("fr")) == (s.delta_rot == 0)
                    and r.get("if", frames >> 1) == s.impact_frame
                    and r.get("mintd", animloose.MIN_TURN_DEFAULT) == s.min_turn
                    and r.get("maxtd", animloose.MAX_TURN_DEFAULT) == s.max_turn)
            if "id" in r:
                same &= all(abs(a - b) < 1e-5 for a, b in zip(r["id"], s.impact))
            else:
                same &= s.delta_length == 0
            if "ld" in r:
                same &= all(abs(a - b) < 1e-5 for a, b in zip(r["ld"], s.launch))
            if not same and len(bad) < 3:
                bad.append((e.name, i))
    check(f"{mod.name}: {n:,} slots read back as themselves{' ' + str(bad) if bad else ''}",
          not bad and n > 20000)

# ---- 3) cues ------------------------------------------------------------------------
print("\n3) cues as .evt files")
packs = animpack.for_data(DAC / "data")
n = bad = 0
for _e, sk in list(animpack.iter_skeletons(packs))[:60]:
    for _i, s in sk.filled():
        if not s.events:
            continue
        n += 1
        lines = [ln.split() for ln in animloose.evt_text(s.events).splitlines()]
        want = [(animloose.EVENT_TYPES[e.type], e.name, e.start, e.end, bool(e.random), bool(e.looped))
                for e in s.events if e.type in animloose.EVENT_TYPES]
        got = [(w[1], w[2], int(w[3]), int(w[4]), "RANDOM" in w[5:], "LOOPED" in w[5:]) for w in lines]
        bad += got != want
check(f"{n:,} slots' cues read back as their events", n > 1000 and not bad)

# ---- 4) a block ---------------------------------------------------------------------
print("\n4) a type block against its packed skeleton")
tmp = Path(_tmp.mkdtemp(prefix="ut_loose_block_"))
rpacks = animpack.for_data(ROCSS / "data")
names = [e.name for e in rpacks.skels.entries][:40]
text = "Version 14\n"
for name in names:
    sk = rpacks.skeleton(name)
    frames = {animpack._key(s.path): rpacks.anims.first(s.path).frames for _i, s in sk.filled()}
    block, _notes = animloose.render_block(name, sk, animloose.type_header(ROCSS / "data", name),
                                           frames, {}, animloose.DEFAULT_SLOT, False)
    text += "\n" + block
(tmp / "descr_skeleton.txt").write_text(text, encoding="latin-1")
types = casanim.skeleton_types(tmp)
steps = [skelslots.compare(rpacks.skeleton(n), types[n.lower()]).in_step for n in names]
check(f"all {len(names)} blocks read back in step with ROCSS's pack", all(steps))
first = types[names[0].lower()].anims[0][0]
check("each block names its default slot first (the file its bones are built from)", first == "default")

# ---- 5) a transfer ------------------------------------------------------------------
print("\n5) Unit Transfer, kept rebuildable")
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
animpack.game_running = lambda: []


def fresh_dest(tag, text=True):
    root = Path(_tmp.mkdtemp(prefix=f"ut_loose_{tag}_")) / "mods" / "Dest"
    for rel in REL:
        if rel == "descr_skeleton.txt" and not text:
            continue
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROCSS / "data" / rel, root / "data" / rel)
    (root / "data" / "animations").mkdir(parents=True)
    for n in animpack.FILES:
        shutil.copy2(ROCSS / "data" / "animations" / n, root / "data" / "animations" / n)
    return root


dac = Mod(DAC)
UNIT, SKEL = "Hobbit Infantry", "EUR_Hobbit_Spear"
root = fresh_dest("one")
dest = Mod(root)
plan = transfer.plan_transfer(dac, UNIT, dest, transfer.TransferOptions())
lo = plan.anim_loose
check(f"planned: {lo.payload()['cas'] if lo else 0} loose .cas, {lo.payload()['evt'] if lo else 0} .evt, "
      f"a block for {SKEL}, and the summary says so",
      lo is not None and not lo.errors and list(lo.blocks) == [SKEL]
      and lo.payload()["cas"] > 100 and "KEPT REBUILDABLE" in plan.summary())
before = shas(root / "data")
text_path = root / "data" / "descr_skeleton.txt"
old_text = text_path.read_bytes()
rec = transfer.apply_transfer(plan)
new_text = text_path.read_bytes()
check("descr_skeleton.txt is the file it was, and a block after it; the Version line unchanged",
      new_text.startswith(old_text) and len(new_text) > len(old_text)
      and re.search(rb"(?m)^\s*Version\s+\d+", new_text).group(0)
      == re.search(rb"(?m)^\s*Version\s+\d+", old_text).group(0))
check("the block is written in the file's own line endings",
      (b"\r\n" in old_text) == (b"\r\n" in new_text[len(old_text):]))
rep = skelslots.report(root / "data")
mine = [s for s in rep.skeletons if s.name.lower() == SKEL.lower()]
check(f"{SKEL}'s block is in step with the pack, slot for slot", mine and mine[0].in_step)
packs = animpack.for_data(root / "data")
sk = packs.skeleton(SKEL)
missing, wrong = [], []
for i, s in sk.filled():
    f = root / "data" / animloose.loose_rel("Dest", s.path)
    if not f.is_file():
        missing.append(s.path)
        continue
    anim = casanim.read_anim_bytes(f.read_bytes(), str(f))
    e = packs.anims.first(s.path)
    data = packs.anims.read_entry(e)
    gen = i != animloose.DEFAULT_SLOT
    if not any(animloose.floats_close(animloose.to_packed(anim, e.scale, g, i in YC), data)
               for g in (gen, not gen)):
        wrong.append(s.path)
check(f"a loose file for each of its {len(sk.filled())} slots, each packing back to the pack's entry",
      not missing and not wrong)
evt = [r for r in rec["manifest"]["created"] if r.endswith(".evt")]
types = casanim.skeleton_types(root / "data")
lines = open(text_path, encoding="latin-1").read().split(f"type            {SKEL}")[1]
named = set(re.findall(r"-evt:mods/Dest/data/(\S+)", lines))
check(f"{len(evt)} .evt files written, every one the block names", evt and named == set(evt))
check("nothing is written outside the destination's data folder",
      all(not r.startswith("..") for r in rec["manifest"]["created"]))
transfer.undo(rec["id"])
check("one undo: every file byte for byte as before, the new ones and their folders gone",
      shas(root / "data") == before and not (root / "data" / "animations" / "ported").exists()
      and not (root / "data" / "mods").exists())

# ---- 6) off, and no text ------------------------------------------------------------
print("\n6) switched off; no descr_skeleton.txt")
root = fresh_dest("off")
dest = Mod(root)
plan = transfer.plan_transfer(dac, UNIT, dest, transfer.TransferOptions(keep_rebuildable=False))
before_text = (root / "data" / "descr_skeleton.txt").read_bytes()
rec = transfer.apply_transfer(plan)
check("off: the packs only, descr_skeleton.txt untouched, no loose file",
      plan.anim_loose is None and (root / "data" / "descr_skeleton.txt").read_bytes() == before_text
      and not any(r.endswith((".cas", ".evt")) for r in rec["manifest"]["created"])
      and any("no loose .cas is written" in w for w in plan.warnings))
root = fresh_dest("notext", text=False)
dest = Mod(root)
plan = transfer.plan_transfer(dac, UNIT, dest, transfer.TransferOptions())
rec = transfer.apply_transfer(plan)
check("no descr_skeleton.txt of its own: nothing written for a rebuild, and a warning",
      not (root / "data" / "descr_skeleton.txt").exists()
      and not any(r.endswith((".cas", ".evt")) for r in rec["manifest"]["created"])
      and any("no descr_skeleton.txt of its own" in w for w in plan.warnings))

# ---- 7) where a loose file goes -----------------------------------------------------
print("\n7) where a loose file goes")
check("a path under the destination's own folder goes where it says",
      animloose.loose_rel("Dest", "mods/dest/data/animations/ported/x/a.cas") == "animations/ported/x/a.cas")
check("any other goes under its data folder, whole",
      animloose.loose_rel("Dest", "mods/Third_Age_3/data/animations/a.cas")
      == "mods/Third_Age_3/data/animations/a.cas"
      and animloose.loose_rel("Dest", "data\\animations\\a.cas") == "data/animations/a.cas")

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
