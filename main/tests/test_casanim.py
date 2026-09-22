"""Phase 55a: the animation .cas reader.

    python -m tests.test_casanim

1. Fixtures built byte by byte in both layouts the installed files use: every
   field comes back, the offsets are checked as a sequence, a short track
   holds its last key, and a truncated file is refused rather than guessed.
2. sample(): slerped, normalised, looping, and a node with no keys at its bind.
3. resolve(): a descr_skeleton.txt path naming another mod's folder is found in
   this one, case-blind.
4. Every loose animation on the installed mods. DaC: all of them but twelve,
   and those twelve are an `isengard_ballista/convertedfiles` folder of
   leftovers nothing names, beside originals that read. Every file
   descr_skeleton.txt names that the mod ships loose reads.
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
    head += b"".join(struct.pack("<3f", i * 1.0, 0.5, 0.0) for i in range(len(names)))
    block = b"".join(struct.pack("<4f", *q) for i in range(len(names)) for q in rot.get(i, []))
    block += b"".join(struct.pack("<3f", *v) for i in range(len(names)) for v in pos.get(i, []))
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
check("positions are interpolated", abs(mid[1]["pos"][1] - 1.5) < 1e-6)
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

# ---- 4) the installed mods --------------------------------------------------------
installed = [m for m in ("Divide_and_Conquer_EUR", "ROCSS") if (MODS / m / "data" / "animations").is_dir()]
if not installed:
    print("\nno mod with loose animations installed - the real-mod half is SKIPPED")
for name in installed:
    data = MODS / name / "data"
    files = sorted((data / "animations").rglob("*.cas"))
    print(f"\n4) {name}: {len(files)} loose animation files")
    read, refused = [], []
    for f in files:
        try:
            read.append(casanim.read_anim(f))
        except casanim.AnimError:
            refused.append(f.relative_to(data).as_posix().lower())
    # Measured 2026-09-22: the only files refused are DaC's Isengard ballista,
    # six in its folder and the same six in a `convertedfiles` copy beside it,
    # and every one is cut short - its node table ends before its own pivots
    # (12 to 48 bytes missing, no chunk list). Two of the six are played by
    # descr_engine_skeleton.txt. Refusing them is the right answer, and the
    # check is that nothing ELSE is refused.
    check(f"{len(read)} read; the {len(refused)} refused are all one siege engine's "
          f"cut-short files", all("/engine/isengard_ballista/" in r for r in refused))
    reasons = set()
    for r in refused:
        try:
            casanim.read_anim(data / r)
        except casanim.AnimError as e:
            reasons.add("ran off the end" in str(e))
    check("and each is refused for ending early, not for a layout this reader lacks",
          reasons <= {True})
    soldier = [t for a in read if "/engine/" not in a.source.replace("\\", "/").lower()
               for t in a.tracks]
    norms = [math.sqrt(sum(x * x for x in t.rot[i:i + 4]))
             for t in soldier for i in range(0, len(t.rot), 4)]
    if norms:
        share = sum(1 for n in norms if 0.5 < n < 1.5) / len(norms)
        check(f"{share:.2%} of {len(norms):,} soldier rotations are near unit length "
              f"(DaC measured 99.52%: the exporter does not normalise)", share > 0.99)
    sk = data / "descr_skeleton.txt"
    if sk.is_file():
        paths = sorted(set(re.findall(r"^\s*anim\s+\S+\s+(\S+\.cas)",
                                      sk.read_text(encoding="latin-1"), re.M | re.I)))
        loose = [f for f in (casanim.resolve(data, p) for p in paths) if f]
        fails = 0
        for f in loose:
            try:
                casanim.read_anim(f)
            except casanim.AnimError:
                fails += 1
        check(f"descr_skeleton.txt names {len(paths):,} files; the {len(loose):,} this mod "
              f"ships loose all read", fails == 0)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
