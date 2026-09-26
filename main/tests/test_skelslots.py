"""Phase 78: the 687 slots named, and descr_skeleton.txt held against the packs.

    python -m tests.test_skelslots

1. The banked table: 687 slots, the known ones where they belong, every group
   k slots sharing k names, and no name on two slots outside a group.
2. descr_skeleton.txt read with a space inside a path, a " - " inside a path,
   the flags after it, and a type given twice.
3. One skeleton held against its text: agreement, a group whose names share a
   path, a path that differs, a slot only the pack fills, a name only the text
   gives, a name the table does not know.
4. A small mod built in temp: types only in the text, skeletons only in the
   pack, a type listed twice, and a mod with no pack at all.
5. The installs: every slot any installed skeleton fills has a name, and the
   report on vanilla, ROCSS and DaC says what was measured on 2026-09-25.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, casanim, skelslots  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
VANILLA_TEXT = ROOT / "Reference" / "UnitEditor11" / "vanilla"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def skeleton_bytes(slots):
    """A one-bone skeleton with ``{slot: path}`` filled and a short tail."""
    out = struct.pack("<fHf", 1.0, 1, 0.0)
    out += struct.pack("<i3fi4si12f", 9, 0, 0, 0, -1, b"\0" * 4, -1, *([0.0] * 12)) + b"bone_pelvis\0"
    for i in range(animpack.SKELETON_SLOTS):
        path = slots.get(i)
        if path is None:
            out += b"\0"
            continue
        out += path.encode() + b"\0" + struct.pack("<h3fhfhfhh3f", *([0] * 13))
        out += struct.pack("<I", 0) + struct.pack("<ih", 0, 0)
    return out + struct.pack("<3f", 1, 2, 3) + b"\0" * 20


def text_type(body):
    folder = Path(_tmp.mkdtemp(prefix="ut_skelslots_"))
    (folder / "descr_skeleton.txt").write_text(body, encoding="latin-1")
    return casanim.skeleton_types(folder)


# ---- 1) the table -------------------------------------------------------------------
print("\n1) the banked table")
table = [skelslots.names(i) for i in range(animpack.SKELETON_SLOTS)]
meas = [i for i in range(animpack.SKELETON_SLOTS) if skelslots.measured(i)]
check(f"687 slots, every one named; {len(meas)} of them measured off the packs",
      len(table) == 687 and skelslots.named() == 687 and len(meas) >= 455)
check("stand_a_idle is 0, crew_stand 159, default 686",
      (table[0], table[159], table[686]) == (("stand_a_idle",), ("crew_stand",), ("default",)))
check("one name a slot, no name on two slots",
      all(len(n) == 1 for n in table) and len({n[0] for n in table}) == 687)
import json as _json  # noqa: E402
_listed = _json.loads((ROOT / "dev" / "reference" / "m2_slot_names.json").read_text(encoding="utf-8"))["slots"]
check("the table is the friend's list, slot for slot (it agreed with every measured slot)",
      [n[0] for n in table] == _listed)
check("slots_of: one slot, case-blind, or none; the old groups told apart",
      (skelslots.slots_of("DEFAULT"), skelslots.slots_of("die_to_back_right_2"),
       skelslots.slots_of("die_to_back_left_2"), skelslots.slots_of("no_such_anim"))
      == ((686,), (91,), (93,), ()))
check("labels: 0, 655 (a group before the list), 1 (unmeasured, named by the list)",
      (skelslots.label(0), skelslots.label(655), skelslots.label(1))
      == ("stand_a_idle", "crew_right", "idle_1_short")
      and skelslots.measured(655) and not skelslots.measured(1))

# ---- 2) the text --------------------------------------------------------------------
print("\n2) descr_skeleton.txt, the paths that are not one word")
types = text_type(
    "; a comment\n"
    "type fs_camel\n"
    "anim\t\tshuffle_forward\t\tmods/x/data/animations/camel/Camel_shuffle forwards.CAS\t\t-fr\t-evt:x.evt\n"
    "anim\t\tno_mp_to_stand\t\tmods/x/data/animations/lid_84  hide to stand - strat map version.cas\n"
    "anim default data/animations/camel/camel_default.cas -fr ; trailing comment\n"
    "type fs_camel\n"
    "anim stand_a_idle data/animations/camel/idle.cas\n")
camel = types["fs_camel"]
check("a space inside a path is kept, the flags are not",
      camel.anims[0][1] == "mods/x/data/animations/camel/Camel_shuffle forwards.CAS")
check("a ' - ' inside a path is not a flag",
      camel.anims[1][1] == "mods/x/data/animations/lid_84  hide to stand - strat map version.cas")
check("a plain line and its comment", camel.anims[2] == ("default", "data/animations/camel/camel_default.cas"))
check("a type given twice is counted, its second block appended",
      camel.blocks == 2 and len(camel.anims) == 4)

# ---- 3) one skeleton --------------------------------------------------------------
print("\n3) one skeleton, text against pack")
sk = animpack.PackedSkeleton(skeleton_bytes({
    0: "data/animations/a/idle.cas", 91: "data/animations/a/die_b2.cas",
    93: "data/animations/a/die_b2.cas", 20: "data/animations/a/run.cas",
    686: "mods/m/data/animations/a/default.cas"}))
t = text_type(
    "type t\n"
    "anim stand_a_idle Data/Animations/A/IDLE.cas\n"
    "anim die_to_back_right_2 data/animations/a/die_b2.cas\n"
    "anim die_to_back_left_2 data/animations/a/die_b2.cas\n"
    "anim default data/animations/a/default.cas\n"
    "anim walk data/animations/a/walk.cas\n"
    "anim no_such_anim data/animations/a/x.cas\n")["t"]
d = skelslots.compare(sk, t)
kinds = {x.label: x.kind for x in d.diffs}
check("the same path in another case agrees, and a group sharing one path agrees",
      "stand_a_idle" not in kinds and not any("die_to_back" in k for k in kinds))
check("a path that differs, a slot only the pack fills, a name only the text gives",
      kinds == {"default": "path differs", skelslots.label(20): "pack only", "walk": "text only"})
check("a name the table does not know is listed", d.unknown == ["no_such_anim"] and not d.in_step)
check("a group whose two names give two paths is one difference, not two",
      len(skelslots.compare(animpack.PackedSkeleton(skeleton_bytes({
          0: "a.cas", 686: "d.cas", 91: "x.cas", 93: "x.cas"})), text_type(
          "type u\nanim stand_a_idle a.cas\nanim default d.cas\n"
          "anim die_to_back_right_2 x.cas\nanim die_to_back_left_2 y.cas\n")["u"]).diffs) == 1)

# ---- 4) a small mod ------------------------------------------------------------------
print("\n4) a mod built in temp")
data = Path(_tmp.mkdtemp(prefix="ut_skelslots_")) / "data"
(data / "animations").mkdir(parents=True)
blobs = {"Alpha": skeleton_bytes({0: "a/idle.cas", 686: "a/default.cas"}),
         "Beta": skeleton_bytes({686: "b/default.cas"}),
         "Twice": skeleton_bytes({686: "t/default.cas"})}
entries, at, dat = [], animpack.HEADER_SIZE, b""
for name in ("Alpha", "Beta", "Twice", "Twice"):
    entries.append(animpack.PackEntry(name, at, len(blobs[name])))
    at += len(blobs[name])
    dat += blobs[name]
idx = animpack.PackIndex(animpack.SKEL_MAGIC, entries, 14, 24)
(data / "animations" / "skeletons.idx").write_bytes(idx.to_bytes())
(data / "animations" / "skeletons.dat").write_bytes(idx.header() + dat)
(data / "descr_skeleton.txt").write_text(
    "type alpha\nanim stand_a_idle a/idle.cas\nanim default a/default.cas\n"
    "type Gamma\nanim default g/default.cas\n"
    "type twice\nanim default t/default.cas\n", encoding="latin-1")
r = skelslots.report(data)
c = r.counts()
check("Alpha in step, Gamma only in the text, Beta only in the pack, Twice listed twice",
      ([s.name for s in r.skeletons], r.text_only, r.pack_only, r.twice)
      == (["alpha"], ["Gamma"], ["Beta"], ["twice"]) and c["in step"] == 1)
check("the report as data", r.as_dict()["counts"]["pack only"] == 1
      and r.as_dict()["out_of_step"] == [])
bare = Path(_tmp.mkdtemp(prefix="ut_skelslots_"))
(bare / "descr_skeleton.txt").write_text("type solo\nanim default s.cas\n", encoding="latin-1")
r = skelslots.report(bare)
check("a mod with no pack: every type is text only, nothing compared",
      (r.anim_dir, r.text_only, r.skeletons) == (None, ["solo"], []))

# ---- 5) the installs ------------------------------------------------------------------
print("\n5) the installs")
installs = {"vanilla": GAME / "data", "ROCSS": GAME / "mods/ROCSS/data",
            "DaC": GAME / "mods/Divide_and_Conquer_EUR/data"}
unnamed, filled = set(), 0
for label, d in installs.items():
    packs = animpack.for_data(d) if d.is_dir() else None
    if packs is None:
        print(f"  SKIPPED: {label} is not installed here")
        continue
    for _e, s in animpack.iter_skeletons(packs):
        for i, _slot in s.filled():
            filled += 1
            if not skelslots.names(i):
                unnamed.add(i)
check(f"every one of {filled:,} filled slots on the installs has a name", filled and not unnamed)

if installs["DaC"].is_dir():
    c = skelslots.report(installs["DaC"]).counts()
    check("DaC: all 410 skeletons in step with its text, none missing either side",
          (c["compared"], c["in step"], c["text only"], c["pack only"]) == (410, 410, 0, 0))
if installs["ROCSS"].is_dir():
    r = skelslots.report(installs["ROCSS"])
    c = r.counts()
    bad = r.out_of_step
    check(f"ROCSS: {c['in step']} of {c['compared']} in step; the {len(bad)} that are not "
          "are weapon skeletons", (c["compared"], c["in step"]) == (208, 203)
          and all(s.name.lower().endswith("_primary") for s in bad))
    check("ROCSS: each difference is the text naming vanilla's path where the pack "
          "holds the mod's own copy",
          all(x.kind == "path differs" and x.text[0].startswith("data/animations/")
              and x.pack[0] == "mods/rocss/" + x.text[0] for s in bad for x in s.diffs))
if installs["vanilla"].is_dir() and (VANILLA_TEXT / "descr_skeleton.txt").is_file():
    c = skelslots.report(installs["vanilla"], VANILLA_TEXT).counts()
    check("vanilla against the kept text: 110 compared, the halberd listed twice, 52 of "
          "the pack's skeletons fill slots this older text does not name",
          (c["compared"], c["listed twice"], c["out of step"], c["slots, path differs"],
           c["slots, text only"]) == (110, 1, 52, 0, 0))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
