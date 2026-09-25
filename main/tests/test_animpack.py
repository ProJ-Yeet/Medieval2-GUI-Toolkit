"""Phase 77: the animation and skeleton packs, read without unpacking.

    python -m tests.test_animpack

1. Built byte by byte: an animation and a skeleton (an event name ended by a
   01 byte, empty slots, the default slot, a tail) read and serialize back to
   their own bytes; the wrong size, a short skeleton and a bad index record
   are refused with the file named.
2. A small pack built from a handful of vanilla's real entries (never a copy
   of a 70-352 MB pack: the suites' temp folders already leak): found by
   name case-blind and either slash, a duplicate path kept with its own
   bytes, the structural checks clean, the cache kept until a file changes.
3. A packed animation read with its packed skeleton's bones into casanim's
   loose shape, with no unpacked file anywhere.
4. The installs: every structural check on vanilla, ROCSS and DaC, and every
   one of their skeletons and indexes serialized back byte for byte.
"""
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, casanim  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
INSTALLS = {"vanilla": GAME / "data", "ROCSS": GAME / "mods/ROCSS/data",
            "DaC": GAME / "mods/Divide_and_Conquer_EUR/data"}
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def refused(fn, *words):
    try:
        fn()
    except animpack.PackError as e:
        return all(w in str(e) for w in words)
    return False


def write_pack(folder: Path, stem: str, magic: bytes, items, version, version2):
    """``items`` is ``[(entry template, bytes)]``: the entries are laid end
    to end from byte 20 and the index written to match."""
    entries, blobs, at = [], [], animpack.HEADER_SIZE
    for tmpl, data in items:
        entries.append(animpack.PackEntry(tmpl.name, at, len(data), tmpl.scale, tmpl.frames,
                                          tmpl.rot_bones, tmpl.pos_bones))
        blobs.append(data)
        at += len(data)
    idx = animpack.PackIndex(magic, entries, version, version2, b"\x12\x34\x56")
    (folder / f"{stem}.idx").write_bytes(idx.to_bytes())
    (folder / f"{stem}.dat").write_bytes(idx.header() + b"".join(blobs))


# ---- 1) byte by byte --------------------------------------------------------------
print("\n1) an animation and a skeleton, built byte by byte")
nf, nq, npb = 3, 2, 1
anim = struct.pack("<HHB", nf, nq, npb)
anim += b"".join(struct.pack("<4f", 0.0, 0.0, 0.1 * f, 1.0) for f in range(nf) for _b in range(nq))
anim += b"".join(struct.pack("<3f", 0.0, 0.9, 0.0) for _f in range(nf))
anim += b"".join(struct.pack("<2f", 0.0, 0.5) for _f in range(nf))
anim += b"".join(struct.pack("<f", 1.0 - 0.5 * f) for f in range(nf))
anim += b"".join(struct.pack("<3f", 0.0, 0.9, 0.5 * f) for f in range(nf))
anim += struct.pack("<8f", 0.1, 1.0, 0.0, 0.0, 1.0, 10.0, 1.0, 0.33)
anim += (1).to_bytes(8, "little")
a = animpack.PackedAnimation(anim, "walk.cas")
check("the size formula holds for the fixture", len(anim) == animpack.anim_size(nf, nq, npb))
check("counts, moving bones, duration and speed", (a.frames, a.rot_bones, a.pos_bones, a.moving,
      round(a.duration, 3), a.speed) == (3, 2, 1, [0], 0.1, 10.0))
check("bone 1's rotation at frame 2 is the one written",
      [round(v, 4) for v in a.rotation(2, 1)] == [0.0, 0.0, 0.2, 1.0])
check("the root motion is the control bone", round(a.control[2 * 3 + 2], 4) == 1.0)
check("serializes back to its own bytes", a.to_bytes() == anim)
check("a byte short is refused, the file named",
      refused(lambda: animpack.PackedAnimation(anim[:-1], "walk.cas"), "walk.cas"))
check("a mask that disagrees with the count is refused",
      refused(lambda: animpack.PackedAnimation(anim[:-8] + (3).to_bytes(8, "little")), "mask"))


def bone(name, parent, pos, btype=0):
    return (struct.pack("<i3fi4si12f", btype, *pos, parent, b"\1\2\3\4", -1, *range(12))
            + name.encode() + b"\0")


def slot(path, events=()):
    out = path.encode() + b"\0" + struct.pack("<h3fhfhfhh3f", 1, 0.1, 0.2, 0.3, 2, 0.5, 7, 1.5,
                                              -16384, 16384, 0.0, 0.0, 1.0)
    out += struct.pack("<I", len(events))
    for name, stop in events:
        out += struct.pack("<IHH", 1, 3, 5) + name.encode() + bytes((stop, 0, 1))
    return out + struct.pack("<ih", 0, 100)


skel = struct.pack("<fHf", 1.0, 2, 0.5) + bone("bone_pelvis", -1, (0, 0, 0), 9)
skel += bone("bone_head", 0, (0, 0.6, 0), 6)
slots = [b"\0"] * animpack.SKELETON_SLOTS
slots[0] = slot("mods/x/data/animations/a/stand.cas", [("step_sound", 0), ("shout", 1)])
slots[686] = slot("mods/x/data/animations/a/default.cas")
tail = struct.pack("<3f", 1.8, 3.1, 4.3) + b"\0\0\0\0" + b"\x05" * 21
skel += b"".join(slots) + tail
s = animpack.PackedSkeleton(skel, "Fixture")
check("bones: names, parents, types and pivots", [(b.name, b.parent, b.type, b.pos[1])
      for b in s.bones] == [("bone_pelvis", -1, 9, 0.0), ("bone_head", 0, 6, 0.6000000238418579)])
check("687 slots, two filled, the tail kept whole",
      (len(s.slots), [i for i, _s in s.filled()], s.tail) == (687, [0, 686], tail))
ev = s.slots[0].events
check("an event name ended by a 01 byte keeps its 01",
      [(e.name, e.stop, e.start, e.end) for e in ev] == [("step_sound", 0, 3, 5), ("shout", 1, 3, 5)])
check("speeds from the tail", [round(v, 2) for v in s.speeds] == [1.8, 3.1, 4.3])
check("serializes back to its own bytes", s.to_bytes() == skel)
check("the bone table casanim takes", s.bone_table()[1][:2] == ("bone_head", 0))
check("a skeleton cut inside its slots is refused, the name given",
      refused(lambda: animpack.PackedSkeleton(skel[:200], "Fixture"), "Fixture", "cut short"))
check("a path rewritten in a slot is what comes back out",
      (lambda sk: (setattr(sk.slots[686], "path", "mods/y/ported/default.cas"),
                   animpack.PackedSkeleton(sk.to_bytes()).slots[686].path)[1])(
          animpack.PackedSkeleton(skel)) == "mods/y/ported/default.cas")

bad = animpack.PackIndex(animpack.SKEL_MAGIC, [animpack.PackEntry("abc", 20, 5)], 14, 24).to_bytes()
bad = bad[:20] + struct.pack("<i", 9) + bad[24:]
check("an index record whose size is wrong is refused",
      refused(lambda: animpack.PackIndex.from_bytes(bad, "skeletons.idx"), "skeletons.idx", "record 0"))
check("an index cut short is refused",
      refused(lambda: animpack.PackIndex.from_bytes(bad[:-2] + b"", "x.idx"), "x.idx"))
check("a file that is not an index is refused",
      refused(lambda: animpack.PackIndex.from_bytes(b"CAS" + b"\0" * 30, "x.idx"), "not a pack"))

# ---- 2) a small pack from real entries ---------------------------------------------
print("\n2) a small pack built from a handful of vanilla's real entries")
van = animpack.for_data(INSTALLS["vanilla"]) if INSTALLS["vanilla"].is_dir() else None
if van is None:
    print("  SKIPPED: vanilla is not installed here")
else:
    tmp = Path(_tmp.mkdtemp(prefix="ut_animpack_")) / "animations"
    tmp.mkdir()
    names = ["MTW2_2H_Axe_primary", "fs_test_shield", "MTW2_2HSwordsman"]
    sk_items = [(van.skels.first(n), van.skels.read_entry(van.skels.first(n))) for n in names]
    want = []
    for n in names[:2]:
        want += van.skeleton(n).animation_paths()
    idle = van.skeleton("MTW2_2HSwordsman").slots[0].path
    want.append(idle)
    an_items = [(van.anims.first(p), van.anims.read_entry(van.anims.first(p))) for p in want]
    dup = van.anims.first("data/animations/navy_selected.cas")
    dup_bytes = van.anims.read_entry(dup)
    other = dup_bytes[:5] + struct.pack("<4f", 0.5, 0.5, 0.5, 0.5) + dup_bytes[21:]
    an_items += [(dup, dup_bytes), (dup, other)]
    write_pack(tmp, "pack", animpack.ANIM_MAGIC, an_items, 9, 0)
    write_pack(tmp, "skeletons", animpack.SKEL_MAGIC, sk_items, 14, 24)
    mine = animpack.open_packs(tmp)
    check(f"{len(an_items)} animations and {len(sk_items)} skeletons, "
          f"{sum(len(b) for _e, b in an_items + sk_items):,} bytes in all",
          (len(mine.anims), len(mine.skels)) == (len(an_items), len(sk_items)))
    shield = want[2]
    check("found case-blind and with backslashes",
          mine.anims.first(shield.upper().replace("/", "\\")) is not None
          and shield.swapcase() in mine.anims)
    check("the duplicate path: both copies listed, each with its own bytes",
          [mine.anims.read_entry(e) for e in mine.anims.find("DATA/animations/NAVY_selected.cas")]
          == [dup_bytes, other]
          and list(mine.anims.duplicates()) == ["data/animations/navy_selected.cas"])
    check("first() is the first listed", mine.animation_bytes(dup.name) == dup_bytes)
    a = mine.animation(idle)
    e = mine.anims.first(idle)
    check("an animation read out of the .dat matches its index record",
          (a.frames, a.rot_bones, a.pos_bones) == (e.frames, e.rot_bones, e.pos_bones))
    sw = mine.skeleton("mtw2_2hswordsman")
    check("a skeleton read out of the .dat is the same bytes back",
          sw.to_bytes() == sk_items[2][1] and len(sw.filled()) > 150)
    check("parsed once, then served from the cache", mine.skeleton("MTW2_2HSwordsman") is sw)
    c = animpack.check(tmp)
    check("the structural checks: contiguous, headers, index round-trips",
          all(c[k] == 1 for k in c if k.endswith(("contiguous to the end", "header",
                                                    "round-trips")) and "skel round" not in k))
    check("every animation reads and every skeleton round-trips",
          (c["anim reads"], c["skel reads"], c["skel round-trips"], c["problems"])
          == (len(an_items), 3, 3, []))
    check("the slots of the two small skeletons all name something in this pack",
          sum(len(mine.skeleton(n).filled()) for n in names[:2]) + 1
          <= c["skel slot paths in pack.idx"] < c["skel slot paths"])
    check("open_packs keeps the same object while nothing changes",
          animpack.open_packs(tmp) is mine)
    time.sleep(0.01)
    write_pack(tmp, "pack", animpack.ANIM_MAGIC, an_items[:-1], 9, 0)
    again = animpack.open_packs(tmp)
    check("and reads again when a file changes", again is not mine and len(again.anims) == len(an_items) - 1)
    (tmp / "skeletons.dat").unlink()
    only = animpack.open_packs(tmp)
    check("a folder with one pair has that pair and None for the other",
          only.skels is None and only.anims is not None and only.skeleton("x") is None)
    bare = Path(_tmp.mkdtemp(prefix="ut_animpack_"))
    (bare / "Animations").mkdir()
    check("a data folder with neither pack gives None, and one with no animations folder",
          animpack.for_data(bare) is None and animpack.for_data(bare / "Animations") is None)

    # ---- 3) into casanim ------------------------------------------------------------
    print("\n3) a packed animation drawn with its packed skeleton's bones")
    sk = van.skeleton("MTW2_2HSwordsman")
    walk = next(s.path for _i, s in sk.filled() if "walk" in s.path.lower())
    loose = casanim.read_packed_bytes(van.animation_bytes(walk), walk, sk.bone_table(),
                                      "MTW2_2HSwordsman")
    packed = van.animation(walk)
    check(f"{Path(walk).name}: {len(loose.tracks) - 1} bone tracks, {packed.frames} frames",
          len(loose.tracks) == len(sk.bones) + 1 and len(loose.key_times) == packed.frames)
    pelvis = loose.tracks[1]
    check("the pelvis carries the root motion", round(pelvis.pos[-1], 4)
          == round(packed.control[-1] - sk.bones[0].pos[2], 4) and packed.distance > 0.1)

# ---- 4) the installs ------------------------------------------------------------------
print("\n4) the installs, whole")
total = 0
for label, data in INSTALLS.items():
    packs = animpack.for_data(data) if data.is_dir() else None
    if packs is None:
        print(f"  SKIPPED: {label} is not installed here")
        continue
    t = time.time()
    c = animpack.check(packs.dir)
    total += c.get("skel reads", 0)
    n_a, n_s = c["anim entries"], c["skel entries"]
    check(f"{label}: {n_a:,} animations and {n_s} skeletons, "
          f"checked in {time.time() - t:.1f} s",
          c["problems"] == [] and c["anim reads"] == c["anim counts = index"] == n_a
          and c["anim odd frame count"] == n_a)
    check(f"{label}: both .dat files contiguous from byte 20 to the end, headers matching",
          c["anim contiguous to the end"] == c["skel contiguous to the end"] == 1
          and c["anim .dat header = .idx header"] == c["skel .dat header = .idx header"] == 1)
    check(f"{label}: both indexes serialize back to their own files",
          c["anim index round-trips"] == c["skel index round-trips"] == 1)
    check(f"{label}: every skeleton serializes back byte for byte, default slot filled",
          c["skel round-trips"] == c["skel default slot filled"] == n_s)
    check(f"{label}: all {c['skel slot paths']:,} slot paths are in pack.idx",
          c["skel slot paths in pack.idx"] == c["skel slot paths"])
if total:
    print(f"  ({total} skeletons round-tripped across the installs)")
    check("vanilla, ROCSS and DaC together are the 730 the roadmap counts",
          total == 730 or not all(d.is_dir() for d in INSTALLS.values()))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
