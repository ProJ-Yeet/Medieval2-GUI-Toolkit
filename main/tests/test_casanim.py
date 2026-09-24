"""Phase 55a: the animation .cas reader (the layout corrected in 55b).

    python -m tests.test_casanim

1. Fixtures built byte by byte in both layouts the installed files use: every
   field comes back, the offsets are checked as a sequence, a short track
   holds its last key, and a truncated file is refused rather than guessed.
2. sample(): slerped, normalised, looping, and a node with no keys at its bind.
3. resolve(): a descr_skeleton.txt path naming another mod's folder is found in
   this one, case-blind.
3b. An unpacked pack.dat: its files found where the unpack nested them
   (animations/mods/<mod>/data/animations) or by what follows their last
   data/, never by name alone; an entry in the pack's own format read with its
   skeleton's bones into the loose shape, and saved back out as a loose .cas.
4. The installed mods. Every loose animation reads but one siege engine's
   cut-short files. Where a mod's pack was unpacked in place (DaC, 2026-09-23),
   MTW2_Mace's every action reads out of it, its walk measures what the loose
   file did, and a sample of every other skeleton reads.
"""
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import casanim  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def text(s: str) -> bytes:
    raw = s.encode("latin-1") + b"\x00"
    return struct.pack("<I", len(raw)) + raw


def make_anim(names, parents, times, rot, pos, pad=2, props=True, version=3.2):
    """``rot``/``pos`` map node index -> list of keys. Laid out as the files are."""
    head = struct.pack("<fIIIf", version, 38, 9, 0, times[-1] if times else 0.0)
    head += b"\x00" * (0x32 - len(head))
    head += struct.pack("<I", len(names)) + b"\x00" * pad
    head += b"".join(struct.pack("<I", p) for p in parents[1:])
    head += struct.pack("<I", len(times)) + b"".join(struct.pack("<f", t) for t in times)
    roff, off = [], 0
    for i in range(len(names)):
        roff.append(off)
        off += len(rot.get(i, [])) * 16
    poff = []
    for i in range(len(names)):
        poff.append(off)
        off += len(pos.get(i, [])) * 12
    for i, n in enumerate(names):
        head += text(n) + struct.pack("<5I", len(rot.get(i, [])), len(pos.get(i, [])),
                                      roff[i], poff[i], 0)
        if props:
            head += text("")
    block = b"".join(struct.pack("<4f", *q) for i in range(len(names)) for q in rot.get(i, []))
    block += b"".join(struct.pack("<3f", *v) for i in range(len(names)) for v in pos.get(i, []))
    # the pivots come AFTER the keys (55b; 55a had them before, see casanim)
    block += b"".join(struct.pack("<3f", i * 1.0, 0.5, 0.0) for i in range(len(names)))
    chunks = struct.pack("<II", 18, 1) + b"\x00" * 10 + struct.pack("<II", 12, 5) + b"\x00" * 4
    return head + block + chunks


# ---- 1) fixtures ---------------------------------------------------------------
print("\n1) both layouts, built byte by byte")
names = ["Scene Root", "bone_pelvis", "bone_head"]
parents = [-1, 0, 1]
times = [0.0, 0.5, 1.0]
q0, q1 = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4))
rot = {1: [q0, q1, q0], 2: [q1]}
pos = {1: [(0, 1, 0), (0, 2, 0), (0, 1, 0)]}
for pad, props, label in ((2, True, "3.2 soldier layout"), (1, False, "3.02 engine layout")):
    a = casanim.read_anim_bytes(make_anim(names, parents, times, rot, pos, pad, props), label)
    check(f"{label}: names, parents and keys come back",
          [t.name for t in a.tracks] == names and [t.parent for t in a.tracks] == parents
          and list(a.key_times) == times)
    check(f"{label}: the pelvis turns and moves, the head holds one key, the root neither",
          (a.tracks[1].rot_keys, a.tracks[1].pos_keys, a.tracks[2].rot_keys,
           a.tracks[0].rot_keys) == (3, 3, 1, 0))
    check(f"{label}: the keys are the floats written",
          tuple(round(x, 6) for x in a.tracks[1].rot[4:8]) == tuple(round(x, 6) for x in q1))
pose = casanim.read_anim_bytes(make_anim(names, parents, times, {}, {}), "pose")
check("a file with no keys is a base pose", pose.is_pose)
short = casanim.read_anim_bytes(
    make_anim(names, parents, [0.0, 0.5, 1.0], {1: [q0, q1]}, {}), "short")
check("a track shorter than the key table reads, and says so (DaC's bomb_dead.cas)",
      short.tracks[1].rot_keys == 2 and short.notes)
good = make_anim(names, parents, times, rot, pos)
for cut, what in ((40, "the key data"), (8, "the chunk list")):
    try:
        casanim.read_anim_bytes(good[:-cut], "cut")
        check(f"a file cut short in {what} is refused", False)
    except casanim.AnimError:
        check(f"a file cut short in {what} is refused", True)
bad = bytearray(good)
# the head's rotation offset, moved: the sequence no longer holds
at = good.index(text("bone_head")) + len(text("bone_head"))
struct.pack_into("<I", bad, at + 8, 999)
try:
    casanim.read_anim_bytes(bytes(bad), "offset")
    check("an offset out of sequence is refused, not read wherever it points", False)
except casanim.AnimError:
    check("an offset out of sequence is refused, not read wherever it points", True)

# ---- 2) sampling -----------------------------------------------------------------
print("\n2) sample()")
a = casanim.read_anim_bytes(good, "good")
mid = casanim.sample(a, 0.25)
qm = mid[1]["rot"]
check("halfway between identity and 90 degrees is 45 degrees",
      abs(qm[2] - math.sin(math.pi / 8)) < 1e-4 and abs(qm[3] - math.cos(math.pi / 8)) < 1e-4)
check("positions are interpolated, as an offset from the pivot (1, 0.5, 0)",
      abs(mid[1]["pos"][1] - 2.0) < 1e-6 and abs(mid[1]["pos"][0] - 1.0) < 1e-6)
check("a node with no position keys sits at its pivot", mid[2]["pos"] == (2.0, 0.5, 0.0))
check("a node with no rotation keys is identity", mid[0]["rot"] == (0.0, 0.0, 0.0, 1.0))
check("it loops", casanim.sample(a, 1.25)[1]["rot"] == mid[1]["rot"])
lopsided = casanim.read_anim_bytes(
    make_anim(names, parents, [0.0, 1.0], {1: [(0, 0, 0, 2.0), (0, 0, 0, 2.0)]}, {}), "norm")
check("an unnormalised key comes out unit length (the exporter does not normalise)",
      abs(math.sqrt(sum(x * x for x in casanim.sample(lopsided, 0.5)[1]["rot"])) - 1) < 1e-6)

# ---- 3) resolving a descr_skeleton.txt path ---------------------------------------
print("\n3) resolve()")
tmp = Path(_tmp.mkdtemp(prefix="ut_anim_")) / "data"
(tmp / "animations" / "AGO_Troll").mkdir(parents=True)
(tmp / "animations" / "AGO_Troll" / "MTW2_Mace_walk.cas").write_bytes(good)
hit = casanim.resolve(tmp, "mods/Third_Age_3/data/animations/ago_troll/mtw2_mace_walk.CAS")
check("another mod's folder, in another case, is found in this mod", hit is not None
      and hit.name == "MTW2_Mace_walk.cas")
check("a plain data/ path resolves", casanim.resolve(tmp, "data/animations/AGO_Troll/MTW2_Mace_walk.cas"))
check("a file that is not there is None, not a guess",
      casanim.resolve(tmp, "data/animations/AGO_Troll/nope.cas") is None)

# ---- 3b) an unpacked pack: found where it nests, and read in its own format -------
print("\n3b) an unpacked pack.dat")
tmp = Path(_tmp.mkdtemp(prefix="ut_animpk_")) / "data"
nest = tmp / "animations" / "mods" / "Third_Age_3" / "data" / "animations"
(nest / "AGO_Troll").mkdir(parents=True)
(nest / "AGO_Troll" / "MTW2_Mace_walk.cas").write_bytes(good)
hit, how = casanim.find(tmp, "mods/Third_Age_3/data/animations/ago_troll/mtw2_mace_walk.CAS")
check("a file an unpack nested under animations/mods/<mod>/data is found", hit is not None
      and how == casanim.NESTED)
hit, how = casanim.find(tmp, "mods/Another_Mod/data/animations/AGO_Troll/MTW2_Mace_walk.cas")
check("...and by what follows its last data/, when the path names another mod", hit is not None
      and how == casanim.TAIL)
(tmp / "animations" / "mods" / "Other" / "data" / "animations" / "AGO_Troll").mkdir(parents=True)
(tmp / "animations" / "mods" / "Other" / "data" / "animations" / "AGO_Troll" / "MTW2_Mace_walk.cas").write_bytes(good)
check("two files with that tail are not guessed between",
      casanim.find(tmp, "mods/Another_Mod/data/animations/AGO_Troll/MTW2_Mace_walk.cas")[0] is None)
check("a file of the same name in another folder is never taken",
      casanim.find(tmp, "data/animations/Somewhere_Else/MTW2_Mace_walk.cas")[0] is None)


def packed(nf, bones_rot, moving, pos, ctrl):
    """A pack entry: counts, rotations frame-major, the moving bones' local
    positions, steps and distances (zero here), the root motion, the summary
    (zero), the mask."""
    nq, npb = len(bones_rot[0]), len(moving)
    out = struct.pack("<HHB", nf, nq, npb)
    out += b"".join(struct.pack("<4f", *bones_rot[f][b]) for f in range(nf) for b in range(nq))
    out += b"".join(struct.pack("<3f", *pos[f][k]) for f in range(nf) for k in range(npb))
    out += bytes(nf * 12)
    out += b"".join(struct.pack("<3f", *ctrl[f]) for f in range(nf))
    out += bytes(32) + sum(1 << b for b in moving).to_bytes(8, "little")
    return out


def skel_entry(bones):
    out = struct.pack("<fHf", 1.0, len(bones), 0.5)
    for name, parent, pivot in bones:
        out += struct.pack("<i3fi", 0, *pivot, parent) + bytes(56) + name.encode() + b"\0"
    return out + bytes(40)


BONES = [("bone_pelvis", -1, (0.0, 0.0, 0.0)), ("bone_spine", 0, (0.0, 0.2, 0.0)),
         ("bone_head", 1, (0.0, 0.5, 0.1))]
qa, qb = (0.0, 0.0, 0.0, 1.0), (0.0, 0.7071068, 0.0, 0.7071068)
rotf = [[qa, qb, qa], [qb, qa, qb], [qa, qa, qa]]
blob = packed(3, rotf, [0, 2], [[(0, .9, 0), (0, .5, .1)], [(0, .9, 0), (0, .6, .1)],
                                [(0, .9, 0), (0, .5, .1)]],
              [(0, .95, 0), (0, .95, .5), (0, .95, 1.0)])
check("a pack entry is known by its size to the byte, and a loose .cas is not",
      casanim.packed_counts(blob) == (3, 3, 2) and casanim.packed_counts(good) is None
      and casanim.packed_counts(blob + b"\0") is None)
(tmp / "animations" / "skeleton").mkdir(parents=True)
(tmp / "animations" / "skeleton" / "Test_Skel").write_bytes(skel_entry(BONES))
(nest / "AGO_Troll" / "packed_walk.cas").write_bytes(blob)
try:
    casanim.read_anim(nest / "AGO_Troll" / "packed_walk.cas")
    check("reading one without its skeleton is refused, and says why", False)
except casanim.AnimError as e:
    check("reading one without its skeleton is refused, and says why", "skeleton" in str(e))
a = casanim.read_anim(nest / "AGO_Troll" / "packed_walk.cas", "test_skel")
check("the skeleton is found under animations/skeleton, case-blind, from the path alone",
      [t.name for t in a.tracks] == ["Scene Root", "bone_pelvis", "bone_spine", "bone_head"])
check("a Scene Root, then each bone with its parent moved up one, and the skeleton's pivots",
      [t.parent for t in a.tracks] == [-1, 0, 1, 2]
      and tuple(round(v, 6) for v in a.tracks[3].pivot) == (0.0, 0.5, 0.1))
check("20 frames a second: three frames are 0.1 s long", abs(a.length - 0.1) < 1e-6
      and [round(t, 3) for t in a.key_times] == [0.0, 0.05, 0.1])
spine = [tuple(round(v, 4) for v in a.tracks[2].rot[i:i + 4]) for i in (0, 4, 8)]
check("each bone's own rotations, transposed out of the frame-by-frame block",
      spine == [tuple(round(v, 4) for v in q) for q in (qb, qa, qa)])
check("the pelvis carries the root motion, as an offset from its pivot",
      [round(a.tracks[1].pos[i], 4) for i in (1, 2, 5, 8)] == [0.95, 0.0, 0.5, 1.0])
check("a moving bone's local position becomes an offset from its pivot; a still one has none",
      [round(v, 4) for v in a.tracks[3].pos[3:6]] == [0.0, 0.1, 0.0] and not a.tracks[2].pos)
back = casanim.read_anim_bytes(casanim.write_anim(a), "back.cas")
check("and it saves as a loose .cas that reads back the same",
      [t.name for t in back.tracks] == [t.name for t in a.tracks]
      and list(back.tracks[2].rot) == list(a.tracks[2].rot))
try:
    casanim.read_anim(nest / "AGO_Troll" / "packed_walk.cas", "No_Such_Skeleton")
    check("a skeleton the mod has not unpacked is named in the refusal", False)
except casanim.AnimError as e:
    check("a skeleton the mod has not unpacked is named in the refusal", "No_Such_Skeleton" in str(e))

# ---- 4) the installed mods --------------------------------------------------------
installed = [m for m in ("Divide_and_Conquer_EUR", "ROCSS") if (MODS / m / "data" / "animations").is_dir()]
if not installed:
    print("\nno mod with loose animations installed - the real-mod half is SKIPPED")
for name in installed:
    data = MODS / name / "data"
    files = sorted((data / "animations").rglob("*.cas"))
    loose_files, packed_files = [], []
    for f in files:
        (packed_files if casanim.packed_counts(f.read_bytes()) else loose_files).append(f)
    print(f"\n4) {name}: {len(loose_files)} loose animation files, {len(packed_files)} "
          f"from an unpacked pack")
    read, refused = [], []
    for f in loose_files:
        try:
            read.append(casanim.read_anim(f))
        except casanim.AnimError:
            refused.append(f.relative_to(data).as_posix().lower())
    # Measured 2026-09-23: the only loose files refused were DaC's Isengard
    # ballista, six in its folder and the same six in a `convertedfiles` copy
    # beside it, every one cut short - twelve bytes, the last node's pivot, and
    # no chunk list after it. Refusing them is the right answer, and the check
    # is that nothing ELSE is refused.
    check(f"{len(read)} loose files read; the {len(refused)} refused are all one siege "
          f"engine's cut-short files", all("/engine/isengard_ballista/" in r for r in refused))
    soldier = [t for a in read if "/engine/" not in a.source.replace("\\", "/").lower()
               for t in a.tracks]
    norms = [math.sqrt(sum(x * x for x in t.rot[i:i + 4]))
             for t in soldier for i in range(0, len(t.rot), 4)]
    if norms:
        worst = max(abs(n - 1) for n in norms)
        check(f"all {len(norms):,} loose soldier rotations are unit length, x y z w "
              f"(worst {worst:.1e})", worst < 1e-4)
    types = casanim.skeleton_types(data)
    index = casanim.loose_index(data)
    paths = sorted({p for t in types.values() for _a, p in t.anims})
    found = {p: casanim.find(data, p, index) for p in paths}
    hows = {h: sum(1 for _f, x in found.values() if x == h)
            for h in (casanim.FLAT, casanim.NESTED, casanim.TAIL)}
    print(f"   descr_skeleton.txt names {len(paths):,} files: {hows[casanim.FLAT]:,} loose "
          f"where the game reads them, {hows[casanim.NESTED]:,} nested by an unpack, "
          f"{hows[casanim.TAIL]:,} by their tail")
    mace = types.get("mtw2_mace")
    if packed_files and mace:
        # Divide and Conquer's pack, unpacked in place. MTW2_Mace's walk as a
        # loose file measured 1.62 of travel over 0.9 s, the pelvis at ~0.97
        # (v3anim.js's header); read out of the pack it must say the same.
        rows = [(act, casanim.find(data, p, index)) for act, p in mace.anims]
        got = [(act, f) for act, (f, _h) in rows if f]
        anims, bad = [], 0
        for act, f in got:
            try:
                anims.append((act, casanim.read_anim(f, mace.name, data)))
            except casanim.AnimError:
                bad += 1
        check(f"MTW2_Mace: {len(got)} of {len(rows)} actions found, and all read with its "
              f"unpacked skeleton's bones", got and not bad)
        walk = next(a for act, a in anims if act.lower() == "walk")
        pel = walk.tracks[1]
        travel = pel.pos[-1] - pel.pos[2]
        check(f"its walk: {walk.length:g} s, pelvis at {pel.pos[1]:.3f}, {travel:.3f} of travel "
              f"- what the loose file measured", abs(walk.length - 0.9) < 1e-6
              and 0.9 < pel.pos[1] < 1.0 and abs(travel - 1.62) < 0.01)
        qn = [math.sqrt(sum(x * x for x in t.rot[i:i + 4]))
              for _act, a in anims for t in a.tracks for i in range(0, len(t.rot), 4)]
        check(f"all {len(qn):,} of its rotations are unit length", max(abs(n - 1) for n in qn) < 1e-3)
        # a sample of every other skeleton, three actions each, to keep the run short
        sample = [(t, f) for t in types.values()
                  for f in [x for x in (found[p][0] for _a, p in t.anims[:3]) if x]]
        missing_skel, wrong = 0, 0
        for t, f in sample:
            try:
                casanim.read_anim(f, t.name, data)
            except casanim.AnimError as e:
                if "no unpacked skeleton" in str(e):
                    missing_skel += 1
                elif "loose" not in str(e):
                    wrong += 1
        check(f"{len(sample):,} actions sampled across {len(types)} skeletons read, bar "
              f"{missing_skel} whose skeleton the unpack does not have", wrong == 0)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
