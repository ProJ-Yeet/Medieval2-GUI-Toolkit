"""MilkShape animations to .cas and back, weapon bones kept.

    python -m tests.test_animconvert

1. Rotations: MilkShape Euler angles to quaternions and back, and the mirror
   into the .cas axes, against the rotation matrices written out by hand.
2. Real files out to .ms3d and back, against the original as template: a
   soldier's walk, DaC's weapon pose, a siege engine with shield bones, and
   vanilla's packed weapon animations (the crossbow moves bone_Weapon02). Names,
   parents and pivots come back exactly, positions and times bit for bit,
   rotations within float tolerance; a file with no keys comes back byte for
   byte.
3. A GOAT-made weapon file (its bone list in a material comment, the weapon
   bone after the hand): bone_weapon01 and its keys are written and the node
   table matches the records, which is what GOAT itself gets wrong.
4. An extra bone the template does not have (a blade under bone_weapon01) is
   written with --keep, and refused when its parent is left out.
5. Hiding bone_weapon01 for a whole clip: every key moves it 100 m, and the
   file reads back.
6. The header's size field is written from the bytes, so a converted file with
   more bones than its template says its own size.
"""
import math
import random
import struct
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod  # noqa: E402
from unittransfer import animconvert as ac  # noqa: E402
from unittransfer import animpack, casanim  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def mat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def mmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def close(a, b, tol):
    return all(abs(i - j) <= tol for i, j in zip(a, b)) and len(a) == len(b)


def same_rot(a, b, tol=2e-5):
    """Two rotation tracks key by key, q and -q being the same turn."""
    if len(a) != len(b):
        return False
    for i in range(0, len(a), 4):
        p, q = a[i:i + 4], b[i:i + 4]
        if not (close(p, q, tol) or close(p, [-v for v in q], tol)):
            return False
    return True


def round_trip(a: casanim.Animation, label: str):
    ms = ac.read_ms3d(ac.write_ms3d(ac.cas_to_ms3d(a)), label)
    back = ac.ms3d_to_anim(ms, a, source=label)
    data = casanim.write_anim(back)
    again = casanim.read_anim_bytes(data, label)
    names = [t.name for t in again.tracks] == [t.name for t in a.tracks]
    parents = [t.parent for t in again.tracks] == [t.parent for t in a.tracks]
    pivots = all(t.pivot == u.pivot for t, u in zip(again.tracks, a.tracks))
    times = list(again.key_times) == list(a.key_times)
    counts = all((t.rot_keys, t.pos_keys) == (u.rot_keys, u.pos_keys)
                 for t, u in zip(again.tracks, a.tracks))
    pos = all(list(t.pos) == list(u.pos) for t, u in zip(again.tracks, a.tracks))
    rot = all(same_rot(t.rot, u.rot) for t, u in zip(again.tracks, a.tracks))
    worst = max((abs(abs(t.rot[i]) - abs(u.rot[i]))
                 for t, u in zip(again.tracks, a.tracks) for i in range(len(t.rot))),
                default=0.0)
    check(f"{label}: {len(a.tracks)} nodes, {len(a.key_times)} keys; names, parents, "
          f"pivots, times and key counts the same", names and parents and pivots and times and counts)
    check(f"{label}: positions bit for bit, rotations within 2e-5 (worst {worst:.1e})", pos and rot)
    return a, again, data


# ---- 1) rotations -----------------------------------------------------------------
print("\n1) Euler angles and the mirror")
rnd = random.Random(7)
bad = 0
for _ in range(2000):
    e = [rnd.uniform(-math.pi, math.pi), rnd.uniform(-1.5, 1.5), rnd.uniform(-math.pi, math.pi)]
    q = ac.quat_from_euler(e)
    want = mmul(rz(e[2]), mmul(ry(e[1]), rx(e[0])))
    got = mat(q)
    if any(abs(got[i][j] - want[i][j]) > 1e-9 for i in range(3) for j in range(3)):
        bad += 1
    e2 = ac.euler_from_quat(q)
    if any(abs(mat(ac.quat_from_euler(e2))[i][j] - want[i][j]) > 1e-9 for i in range(3) for j in range(3)):
        bad += 1
    # the mirror: X negated on both sides of the rotation
    m = [[-1, 0, 0], [0, 1, 0], [0, 0, 1]]
    if any(abs(mat(ac._mirror_q(q))[i][j] - mmul(m, mmul(want, m))[i][j]) > 1e-9
           for i in range(3) for j in range(3)):
        bad += 1
check("2000 random angles: X then Y then Z, back again, and mirrored, all match the matrices", bad == 0)
gl = ac.euler_from_quat(ac.quat_from_euler([0.3, math.pi / 2, 0.2]))
check("straight up (Y at 90 degrees) still comes back as the same turn",
      all(abs(mat(ac.quat_from_euler(gl))[i][j] - mat(ac.quat_from_euler([0.3, math.pi / 2, 0.2]))[i][j]) < 1e-6
          for i in range(3) for j in range(3)))

# ---- 2) real files ----------------------------------------------------------------
print("\n2) real animations out to .ms3d and back")
game = _realmod.game()
mods = _realmod.mods()
dac = None
for name in ("Divide_and_Conquer_EUR",):
    if (mods / name / "data" / "animations").is_dir():
        dac = mods / name / "data" / "animations"
if dac is None:
    for folder in sorted(mods.iterdir()) if mods.is_dir() else []:
        if (folder / "data" / "animations").is_dir():
            dac = folder / "data" / "animations"
            break
loose = {}
if dac is not None:
    for f in dac.rglob("*"):
        if f.suffix.lower() == ".cas":
            loose[f.relative_to(dac).as_posix().lower()] = f

walk = loose.get("mtw2_mace/mtw2_mace_walk.cas")
if walk:
    round_trip(casanim.read_anim(walk), "MTW2_Mace_walk.cas")
pose = loose.get("mtw2_mace/weapon/mtw2_mace_default.cas")
if pose:
    a = casanim.read_anim(pose)
    _a, _b, data = round_trip(a, "weapon/MTW2_Mace_default.cas")
    check("the weapon pose (no keys, bone_weapon01 a node of its own) comes back byte for byte",
          data == pose.read_bytes())
ram = loose.get("engine/ram_destruction.cas")
if ram:
    round_trip(casanim.read_anim(ram), "engine/ram_destruction.CAS (shield bones, properties strings)")
if not (walk or pose or ram):
    print("  (no loose animations installed: the real-file part is skipped)")

packs = animpack.for_data(game / "data")
crossbow = None
if packs is not None:
    for skel in ("MTW2_Crossbow_Primary", "MTW2_2HSwordsman_Primary"):
        sk = packs.skeleton(skel)
        if sk is None:
            continue
        for path in sk.animation_paths():
            raw = packs.animation_bytes(path)
            if raw is None:
                continue
            a = casanim.read_packed_bytes(raw, path, sk.bone_table(), skel)
            # as a loose file first: what a modder gets from an unpack and convert
            a = casanim.read_anim_bytes(casanim.write_anim(a), path)
            round_trip(a, Path(path).name)
            if crossbow is None and "Crossbow_default" in path:
                crossbow = a
    if crossbow is not None:
        w2 = [t for t in crossbow.tracks if t.name == "bone_Weapon02"][0]
        check("vanilla's crossbow animates its extra bone, bone_Weapon02, by position keys",
              w2.pos_keys == len(crossbow.key_times))
else:
    print("  (vanilla's pack.dat not found: the packed weapon part is skipped)")

# ---- 3) a GOAT-made weapon file ---------------------------------------------------
print("\n3) a weapon file as GOAT's animmerge leaves it")


def goat_ms3d(joints, bones, extra=b""):
    """A skeleton-only .ms3d with GOAT's material comment: header line,
    parent line, the .cas bone names joined by %."""
    base = ac.write_ms3d(ac.Ms3d(fps=20.0, frames=20, joints=joints))
    header = "3.200000 38 9 0 1.0 1 0 0 0 0 1 0 102 102 102"
    text = (header + "\r\n0 0 1\r\n" + "%".join(bones) + "\r\n").encode("latin-1")
    comments = struct.pack("<ii", 1, 0) + struct.pack("<iii", 1, 0, len(text)) + text
    return base + comments + struct.pack("<ii", 0, 0) + extra


ts = [i * 0.05 for i in range(20)]
hand = ac.Joint("bone_Rhand", "", pos=(-0.764, 0.51, -0.011),
                rot_keys=[(t, 0.0, 0.0, 0.0) for t in ts], pos_keys=[(t, 0.0, 0.0, 0.0) for t in ts])
weapon = ac.Joint("bone_weapon01", "bone_Rhand", pos=(-0.085, -0.023, 0.0),
                  rot_keys=[(t, 0.0, 0.0, t) for t in ts],
                  pos_keys=[(t, 0.0, -100.0 if t >= 0.5 else 0.0, 0.0) for t in ts])
ms = ac.read_ms3d(goat_ms3d([hand, weapon], ["bone_Rhand", "bone_weapon01"]), "goat.ms3d")
check("the GOAT bone list is read from the material comment", ms.goat_bones() == ["bone_Rhand", "bone_weapon01"])
a = ac.ms3d_to_anim(ms)
data = casanim.write_anim(a)
back = casanim.read_anim_bytes(data, "goat.cas")
w = [t for t in back.tracks if t.name == "bone_weapon01"]
check("bone_weapon01 is written, after bone_Rhand and parented to it",
      [t.name for t in back.tracks] == ["Scene Root", "bone_Rhand", "bone_weapon01"]
      and w and w[0].parent == 1)
check("its 20 rotation and 20 position keys are kept, the drop of 100 m from 0.5 s on included",
      w and w[0].rot_keys == 20 and w[0].pos_keys == 20
      and [round(w[0].pos[i * 3 + 1], 3) for i in range(20)] == [0.0] * 10 + [-100.0] * 10)
q = ac._mirror_q(ac.quat_from_euler((0.0, 0.0, 0.95)))
check("a turn about Z keyed in MilkShape comes out mirrored (z negated) in the .cas",
      w and close(w[0].rot[19 * 4:19 * 4 + 4], q, 1e-6))
nodes = struct.unpack_from("<I", data, 0x32)[0]
check(f"the node table says {nodes} and there are {len(back.tracks)} node records", nodes == len(back.tracks))
check("pivots are the .ms3d bind positions, X mirrored",
      w and close(w[0].pivot, (0.085, -0.023, 0.0), 1e-6))

# ---- 4) a bone the template does not have -----------------------------------------
print("\n4) an extra bone")
blade = ac.Joint("bone_blade", "bone_weapon01", pos=(0.0, 0.0, 0.3),
                 pos_keys=[(t, 0.0, 0.0, -0.3 if t >= 0.5 else 0.0) for t in ts])
tmpl = casanim.read_anim_bytes(data, "goat.cas")
ms2 = ac.read_ms3d(goat_ms3d([hand, weapon, blade], ["bone_Rhand", "bone_weapon01"]), "blade.ms3d")
b = casanim.read_anim_bytes(casanim.write_anim(ac.ms3d_to_anim(ms2, tmpl, keep=["bone_blade"])), "blade.cas")
bl = [t for t in b.tracks if t.name == "bone_blade"]
check("--keep bone_blade adds it under bone_weapon01 with its 20 position keys",
      bl and bl[0].parent == 2 and bl[0].pos_keys == 20 and bl[0].rot_keys == 0)
try:
    ac.ms3d_to_anim(ms2, None, bones=["bone_Rhand", "bone_blade"])
    refused = False
except ac.ConvertError as e:
    refused = "parent" in str(e)
check("a bone whose parent is left out is refused, saying so", refused)

# ---- 5) hiding ---------------------------------------------------------------------
print("\n5) hiding bone_weapon01 for a whole animation")
src = crossbow
if packs is not None:
    sk = packs.skeleton("MTW2_2HSwordsman_Primary")
    path = sk.animation_paths()[0] if sk else ""
    raw = packs.animation_bytes(path) if path else None
    if raw:
        src = casanim.read_anim_bytes(casanim.write_anim(
            casanim.read_packed_bytes(raw, path, sk.bone_table(), "MTW2_2HSwordsman_Primary")), path)
if src is None:
    src = casanim.read_anim_bytes(data, "goat.cas")
bone = [t for t in src.tracks if t.name.lower() == "bone_weapon01"][0].name
hidden = ac.hide_bone(casanim.read_anim_bytes(casanim.write_anim(src), src.source), bone)
hb = casanim.write_anim(hidden)
h = casanim.read_anim_bytes(hb, "hidden.cas")
t = [x for x in h.tracks if x.name == bone][0]
o = [x for x in src.tracks if x.name == bone][0]
n = len(h.key_times)
check(f"{Path(src.source).name}: {bone} gets a position key at every one of the {n} keys, each 100 m down",
      t.pos_keys == n and all(abs(t.pos[i * 3 + 1] - (o.pos[min(i, o.pos_keys - 1) * 3 + 1] if o.pos_keys else 0) + 100) < 1e-4
                              for i in range(n)))
check("its rotations and every other bone are untouched",
      list(t.rot) == list(o.rot) and all(list(x.rot) == list(y.rot) and list(x.pos) == list(y.pos)
                                         for x, y in zip(h.tracks, src.tracks) if x.name != bone))
try:
    ac.hide_bone(casanim.read_anim_bytes(hb, "x"), "bone_nothere")
    refused = False
except ac.ConvertError:
    refused = True
check("a bone the file does not have is refused", refused)

# ---- 6) the size field --------------------------------------------------------------
print("\n6) the header's size field")
for label, blob in (("bone_blade.cas", casanim.write_anim(b)), ("hidden.cas", hb)):
    a2 = casanim.read_anim_bytes(blob, label)
    size = struct.unpack_from("<I", blob, casanim.SIZE_AT)[0]
    check(f"{label}: says {size:,}, the bytes from it to the end of the pivots",
          size == len(blob) - casanim.SIZE_AT - len(a2.tail or b""))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
