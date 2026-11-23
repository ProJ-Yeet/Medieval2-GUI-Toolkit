r"""MilkShape ``.ms3d`` animations to battle ``.cas`` and back, every bone kept.

    python -m unittransfer.animconvert to-cas  walk.ms3d walk.cas --template old.cas
    python -m unittransfer.animconvert to-ms3d walk.cas walk.ms3d
    python -m unittransfer.animconvert hide    in.cas out.cas --bone bone_weapon01
    python -m unittransfer.animconvert info    walk.cas

Why this exists
---------------
GOAT 1.1's MilkShape-to-.cas step (``animextract``, through
``ms3dJointSection.makecasBoneSection``) walks the bones and **stops at the
first one whose name contains "weapon" or "shield"** (a ``break``, not a skip,
and a case-sensitive ``find``, so ``bone_weapon01`` stops it and
``bone_Weapon01`` does not). That bone, every bone listed after it and all
their keys are left out. It then writes the parent table it saved from the
original file, so the node count there no longer matches the node records that
follow: a weapon animation (``bone_Rhand``, ``bone_weapon01``) comes out with a
table saying three nodes and two records after it. This module writes every
bone it is asked for, in one consistent table.

What a .cas animation can hold
------------------------------
Per bone: a rotation track (quaternions, x y z w) and a position track
(offsets from the bone's pivot), each with no key, one key, or a key at every
key time of the file. **There is no scale track.** A bone cannot be scaled to
zero; :func:`hide_bone` moves it far away instead (see there).

Conventions, shared with GOAT so files it made read the same here
-----------------------------------------------------------------
MilkShape's X runs the other way: a position's x is negated, and a rotation is
mirrored with it, which for a quaternion negates y and z. MilkShape keeps a
rotation as Euler angles (x, y, z) in radians, applied X first, then Y, then Z.
A joint's keys are relative to its bind rotation and position, as in
MilkShape itself: the bone's local transform is bind times key.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import casanim
from . import i18n as _i18n

MS3D_MAGIC = b"MS3D000000"


class ConvertError(ValueError):
    pass


# ---------------------------------------------------------------------------
# rotations

def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def quat_from_euler(e) -> Tuple[float, float, float, float]:
    """MilkShape Euler angles (radians, X then Y then Z) as a quaternion."""
    a, b, c = (v * 0.5 for v in e)
    qx = (math.sin(a), 0.0, 0.0, math.cos(a))
    qy = (0.0, math.sin(b), 0.0, math.cos(b))
    qz = (0.0, 0.0, math.sin(c), math.cos(c))
    return _qmul(qz, _qmul(qy, qx))


def euler_from_quat(q) -> Tuple[float, float, float]:
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    r11 = 1 - 2 * (y * y + z * z)
    r21 = 2 * (x * y + z * w)
    r31 = 2 * (x * z - y * w)
    r32 = 2 * (y * z + x * w)
    r33 = 1 - 2 * (x * x + y * y)
    sb = max(-1.0, min(1.0, -r31))
    b = math.asin(sb)
    if abs(sb) < 0.999999:
        return (math.atan2(r32, r33), b, math.atan2(r21, r11))
    r22 = 1 - 2 * (x * x + z * z)
    r23 = 2 * (y * z - x * w)
    return (math.atan2(-r23, r22), b, 0.0)


def _mirror_q(q):
    return (q[0], -q[1], -q[2], q[3])


def _mirror_v(v):
    return (-v[0], v[1], v[2])


def _rotate(q, v):
    x, y, z, w = q
    p = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return p[:3]


def _slerp(a, b, f):
    d = sum(i * j for i, j in zip(a, b))
    if d < 0:
        b, d = tuple(-v for v in b), -d
    if d > 0.9995:
        out = tuple(i + (j - i) * f for i, j in zip(a, b))
    else:
        th = math.acos(d)
        s = math.sin(th)
        wa, wb = math.sin((1 - f) * th) / s, math.sin(f * th) / s
        out = tuple(wa * i + wb * j for i, j in zip(a, b))
    n = math.sqrt(sum(v * v for v in out)) or 1.0
    return tuple(v / n for v in out)


def _hemisphere(keys: List[tuple]) -> List[tuple]:
    """Each quaternion on the same side as the one before it, so nothing
    between two keys takes the long way round."""
    out = []
    for q in keys:
        if out and sum(i * j for i, j in zip(out[-1], q)) < 0:
            q = tuple(-v for v in q)
        out.append(q)
    return out


# ---------------------------------------------------------------------------
# .ms3d

@dataclass
class Joint:
    name: str
    parent: str = ""
    #: bind rotation (Euler, radians) and position, in MilkShape's axes
    rot: tuple = (0.0, 0.0, 0.0)
    pos: tuple = (0.0, 0.0, 0.0)
    #: [(time in seconds, x, y, z)]: Euler angles, and position deltas
    rot_keys: List[tuple] = field(default_factory=list)
    pos_keys: List[tuple] = field(default_factory=list)
    flags: int = 8


@dataclass
class Ms3d:
    fps: float = 20.0
    current_time: float = 0.0
    frames: int = 0
    joints: List[Joint] = field(default_factory=list)
    material_comments: List[Tuple[int, str]] = field(default_factory=list)

    def goat_bones(self) -> List[str]:
        """The .cas bone list GOAT's animmerge saved in a material comment
        (its third line, names joined by %), or [] when there is none."""
        for _i, text in self.material_comments:
            lines = [s.strip() for s in text.replace("%%", "\r\n").split("\r\n")]
            if len(lines) >= 3 and lines[2] and len(lines[0].split()) == 15:
                return [n for n in lines[2].split("%") if n]
        return []


class _R:
    def __init__(self, data: bytes, name: str):
        self.d, self.p, self.name = data, 0, name

    def take(self, fmt: str):
        try:
            v = struct.unpack_from("<" + fmt, self.d, self.p)
        except struct.error:
            raise ConvertError(_i18n.msg("eng.animconvert.cut_short", "{name}: cut short at byte {at:,}", name=self.name, at=self.p)) from None
        self.p += struct.calcsize("<" + fmt)
        return v

    def text(self, n: int) -> str:
        raw = self.d[self.p:self.p + n]
        if len(raw) < n:
            raise ConvertError(_i18n.msg("eng.animconvert.cut_short", "{name}: cut short at byte {at:,}", name=self.name, at=self.p))
        self.p += n
        return raw.split(b"\0", 1)[0].decode("latin-1")

    @property
    def left(self) -> int:
        return len(self.d) - self.p


def read_ms3d(data: bytes, name: str = "ms3d") -> Ms3d:
    r = _R(data, name)
    if data[:10] != MS3D_MAGIC:
        raise ConvertError(_i18n.msg("eng.animconvert.not_ms3d", "{name}: not a MilkShape .ms3d file", name=name))
    r.p = 10
    (version,) = r.take("i")
    if version not in (3, 4):
        raise ConvertError(_i18n.msg("eng.animconvert.ms3d_version", "{name}: MilkShape format version {version}, this reads 3 and 4", name=name, version=version))
    (nv,) = r.take("H")
    r.p += nv * 15
    (nt,) = r.take("H")
    r.p += nt * 70
    (ng,) = r.take("H")
    for _ in range(ng):
        r.p += 1 + 32
        (n,) = r.take("H")
        r.p += 2 * n + 1
    (nm,) = r.take("H")
    r.p += nm * 361
    out = Ms3d()
    if r.left < 12:
        raise ConvertError(_i18n.msg("eng.animconvert.no_animation", "{name}: has no animation section", name=name))
    out.fps, out.current_time, out.frames = r.take("ffi")
    (nj,) = r.take("H")
    for _ in range(nj):
        (flags,) = r.take("B")
        j = Joint(r.text(32), r.text(32), flags=flags)
        vals = r.take("6f")
        j.rot, j.pos = tuple(vals[:3]), tuple(vals[3:])
        nr, np_ = r.take("HH")
        j.rot_keys = [r.take("4f") for _ in range(nr)]
        j.pos_keys = [r.take("4f") for _ in range(np_)]
        out.joints.append(j)
    # the comments, when the file has them: GOAT keeps the .cas bone list there
    if r.left >= 8:
        (sub,) = r.take("i")
        if sub == 1:
            try:
                for kind in range(3):
                    (n,) = r.take("i")
                    for _ in range(n):
                        idx, ln = r.take("ii")
                        text = r.d[r.p:r.p + ln].decode("latin-1")
                        r.p += ln
                        if kind == 1:
                            out.material_comments.append((idx, text))
            except ConvertError:
                pass
    return out


def write_ms3d(m: Ms3d) -> bytes:
    """A skeleton-only .ms3d: no mesh, the joints and their keys."""
    out = [MS3D_MAGIC, struct.pack("<iHHHH", 4, 0, 0, 0, 0),
           struct.pack("<ffiH", m.fps, m.current_time, m.frames, len(m.joints))]
    for j in m.joints:
        out.append(struct.pack("<B", j.flags))
        for s in (j.name, j.parent):
            raw = s.encode("latin-1")
            if len(raw) > 31:
                raise ConvertError(_i18n.msg("eng.animconvert.name_too_long", "bone name {name} is longer than MilkShape's 31 characters", name=repr(s)))
            out.append(raw.ljust(32, b"\0"))
        out.append(struct.pack("<6f", *j.rot, *j.pos))
        out.append(struct.pack("<HH", len(j.rot_keys), len(j.pos_keys)))
        out += [struct.pack("<4f", *k) for k in j.rot_keys]
        out += [struct.pack("<4f", *k) for k in j.pos_keys]
    return b"".join(out)


# ---------------------------------------------------------------------------
# .cas -> .ms3d

def cas_to_ms3d(a: casanim.Animation) -> Ms3d:
    """Every node but the Scene Root as a joint, bind rotation zero, its pivot
    as the bind position, its keys as MilkShape keys at the file's own times."""
    times = list(a.key_times)
    dt = (times[1] - times[0]) if len(times) > 1 else 0.05
    m = Ms3d(fps=float(round(1.0 / dt)) if dt > 0 else 20.0, frames=len(times))
    for t in a.tracks[1:]:
        par = a.tracks[t.parent].name if t.parent > 0 else ""
        j = Joint(t.name, par, pos=_mirror_v(t.pivot))
        for k in range(t.rot_keys):
            q = _mirror_q(tuple(t.rot[k * 4:k * 4 + 4]))
            j.rot_keys.append((times[k], *euler_from_quat(q)))
        for k in range(t.pos_keys):
            j.pos_keys.append((times[k], *_mirror_v(tuple(t.pos[k * 3:k * 3 + 3]))))
        m.joints.append(j)
    return m


# ---------------------------------------------------------------------------
# .ms3d -> .cas

def _sample(keys: List[tuple], t: float, rot: bool):
    """A joint's key value at ``t``: held before the first and after the last."""
    if t <= keys[0][0] + 1e-7:
        return keys[0][1]
    if t >= keys[-1][0] - 1e-7:
        return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 - 1e-7 <= t <= t1 + 1e-7:
            if abs(t - t0) <= 1e-7:
                return v0
            if abs(t - t1) <= 1e-7:
                return v1
            f = (t - t0) / (t1 - t0)
            return _slerp(v0, v1, f) if rot else tuple(i + (j - i) * f for i, j in zip(v0, v1))
    return keys[-1][1]


def _times(joints: Iterable[Joint]) -> List[float]:
    seen: Dict[int, float] = {}
    for j in joints:
        for k in list(j.rot_keys) + list(j.pos_keys):
            seen.setdefault(round(k[0] * 1e5), k[0])
    return [seen[k] for k in sorted(seen)]


def ms3d_to_anim(m: Ms3d, template: Optional[casanim.Animation] = None,
                 bones: Optional[Sequence[str]] = None, keep: Sequence[str] = (),
                 source: str = "converted.cas") -> casanim.Animation:
    """A .cas animation from a MilkShape one.

    Which bones: ``bones`` when given; else the ``template``'s nodes; else
    the list GOAT saved in the file; else every joint. ``keep`` adds bones to
    whichever list that is (a bone the modder added, a second weapon bone).
    Weapon and shield bones are bones like any other here.

    With a ``template`` (the .cas the animation started from) its header
    bytes, end chunks, names' and properties' bytes, parent table and pivots
    are kept for its own nodes, and the keys are applied as changes to its
    pivots. A bone not in the template takes its parent and pivot from the
    .ms3d; its parent has to be in the list too."""
    by_name = {j.name.lower(): j for j in m.joints}
    tmpl = {t.name.lower(): (i, t) for i, t in enumerate(template.tracks)} if template else {}
    if bones:
        names = list(bones)
    elif template is not None:
        names = [t.name for t in template.tracks[1:]]
    else:
        names = m.goat_bones() or [j.name for j in m.joints]
    have = {n.lower() for n in names}
    names += [n for n in keep if n.lower() not in have]
    missing = [n for n in names if n.lower() not in by_name]
    if missing:
        raise ConvertError(_i18n.msg("eng.animconvert.no_joint", "the .ms3d has no joint {names}", names=", ".join(missing)))

    joints = [by_name[n.lower()] for n in names]
    grid = _times(joints)
    if not grid:
        # a pose with no keys still has key times: the template's, or a frame
        # count's worth at the file's rate
        if template is not None and len(template.key_times):
            grid = [float(t) for t in template.key_times]
        else:
            step = 1.0 / m.fps if m.fps > 0 else 0.05
            grid = [i * step for i in range(max(1, m.frames))]
    t0 = grid[0]
    if template is not None and len(template.key_times) == len(grid):
        key_times = array("f", template.key_times)
    else:
        key_times = array("f", [t - t0 for t in grid])

    out = casanim.Animation(source=source)
    if template is not None:
        out.version, out.layout = template.version, template.layout
        out.head, out.tail = template.head, template.tail
        root = template.tracks[0]
        out.tracks.append(casanim.Track(root.name, -1, root.pivot, name_raw=root.name_raw,
                                        props_raw=root.props_raw, extra=root.extra))
    else:
        out.version = 3.2
        out.tracks.append(casanim.Track("Scene Root", -1, (0.0, 0.0, 0.0)))
    out.key_times = key_times
    # the header's length: kept from the template while the key count is its
    # own, else the last key time, which is what an exported file says
    same = template is not None and len(template.key_times) == len(key_times)
    out.length = template.length if same else float(key_times[-1])

    index = {n.lower(): i + 1 for i, n in enumerate(names)}
    for n, j in zip(names, joints):
        hit = tmpl.get(n.lower())
        bind_q = quat_from_euler(j.rot)
        if hit is not None:
            ti, tt = hit
            parent = index.get(template.tracks[tt.parent].name.lower(), 0) if tt.parent > 0 else 0
            pivot = tt.pivot
            track = casanim.Track(tt.name, parent, pivot, name_raw=tt.name_raw,
                                  props_raw=tt.props_raw, properties=tt.properties,
                                  extra=tt.extra)
        else:
            if j.parent and j.parent.lower() not in index:
                raise ConvertError(_i18n.msg("eng.animconvert.parent_left_out", "{bone}'s parent {parent} is not among the bones written; add it with --keep", bone=j.name, parent=j.parent))
            parent = index.get(j.parent.lower(), 0) if j.parent else 0
            pivot = _mirror_v(j.pos)
            track = casanim.Track(j.name, parent, tuple(pivot))
        if parent >= len(out.tracks):
            raise ConvertError(_i18n.msg("eng.animconvert.parent_after", "{bone} comes before its parent {parent}: list parents first", bone=j.name, parent=j.parent))

        # rotations: bind times key, mirrored into the .cas axes
        if j.rot_keys:
            rk = [(k[0] - t0, quat_from_euler(k[1:])) for k in j.rot_keys]
            if len(rk) == 1:
                qs = [rk[0][1]]
            else:
                qs = [_sample(rk, g - t0, True) for g in grid]
            qs = _hemisphere([_mirror_q(_qmul(bind_q, q)) for q in qs])
            if qs[0][3] < 0:
                qs = [tuple(-v for v in q) for q in qs]
            track.rot = array("f", [v for q in qs for v in q])
        elif any(abs(v) > 1e-9 for v in j.rot):
            q = _mirror_q(bind_q)
            track.rot = array("f", q if q[3] >= 0 else tuple(-v for v in q))
        # positions: an offset from the pivot. With a template the key is a
        # change to its pivot; without, the .ms3d bind position is the pivot.
        if j.pos_keys:
            pk = [(k[0] - t0, tuple(k[1:])) for k in j.pos_keys]
            if len(pk) == 1:
                ps = [pk[0][1]]
            else:
                ps = [_sample(pk, g - t0, False) for g in grid]
            if any(abs(v) > 1e-9 for v in j.rot):
                ps = [_rotate(bind_q, p) for p in ps]
            track.pos = array("f", [v for p in ps for v in _mirror_v(p)])
        out.tracks.append(track)
    return out


# ---------------------------------------------------------------------------
# hiding a bone

def hide_bone(a: casanim.Animation, name: str, offset=(0.0, -100.0, 0.0)) -> casanim.Animation:
    """Move bone ``name`` by ``offset`` (metres, in its parent's frame) at
    every key of the file, on top of whatever it already does.

    The .cas format has no scale track, so this is how a weapon bone is made
    to disappear for a whole animation: whatever is weighted to it is drawn
    ``offset`` away, a hundred metres by default, out of sight. To keep a
    hilt in the hand and lose only the blade, the blade needs a bone of its
    own in the mesh (a child of ``bone_weapon01``), and that bone is the one
    to move."""
    hit = [t for t in a.tracks if t.name.lower() == name.lower()]
    if not hit:
        raise ConvertError(_i18n.msg("eng.animconvert.no_bone", "{file} has no bone {bone}; it has {names}", file=Path(a.source).name, bone=name, names=", ".join(t.name for t in a.tracks[1:])))
    t = hit[0]
    n = len(a.key_times)
    if n == 0:
        raise ConvertError(_i18n.msg("eng.animconvert.no_key_times", "{file} has no key times", file=Path(a.source).name))
    base = [tuple(t.pos[min(k, t.pos_keys - 1) * 3:min(k, t.pos_keys - 1) * 3 + 3])
            if t.pos_keys else (0.0, 0.0, 0.0) for k in range(n)]
    t.pos = array("f", [p[i] + offset[i] for p in base for i in range(3)])
    return a


# ---------------------------------------------------------------------------
# command line

def _read_cas(path: str, skeleton: str = "") -> casanim.Animation:
    return casanim.read_anim(path, skeleton=skeleton)


def describe(a: casanim.Animation) -> str:
    lines = [a.summary()]
    for i, t in enumerate(a.tracks):
        lines.append(f"  {i:3d} {t.name:<24} parent {t.parent:3d}  rot {t.rot_keys:4d}  "
                     f"pos {t.pos_keys:4d}  pivot {tuple(round(v, 4) for v in t.pivot)}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m unittransfer.animconvert",
                                description="MilkShape animations to .cas and back, every bone kept.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("to-cas", help=".ms3d animation to .cas")
    c.add_argument("ms3d"); c.add_argument("cas")
    c.add_argument("--template", help="the .cas the animation started from")
    c.add_argument("--keep", nargs="*", default=[], help="extra bones to write")
    c.add_argument("--all-bones", action="store_true", help="write every joint of the .ms3d")
    m = sub.add_parser("to-ms3d", help=".cas animation to a skeleton-only .ms3d")
    m.add_argument("cas"); m.add_argument("ms3d")
    m.add_argument("--skeleton", default="", help="for a pack entry: its skeleton's name")
    h = sub.add_parser("hide", help="move a bone out of sight for a whole animation")
    h.add_argument("cas"); h.add_argument("out")
    h.add_argument("--bone", default="bone_weapon01")
    h.add_argument("--offset", nargs=3, type=float, default=[0.0, -100.0, 0.0])
    i = sub.add_parser("info", help="list a .cas animation's bones and keys")
    i.add_argument("cas")
    args = p.parse_args(argv)
    try:
        if args.cmd == "to-cas":
            ms = read_ms3d(Path(args.ms3d).read_bytes(), Path(args.ms3d).name)
            tmpl = _read_cas(args.template) if args.template else None
            bones = [j.name for j in ms.joints] if args.all_bones else None
            a = ms3d_to_anim(ms, tmpl, bones=bones, keep=args.keep, source=args.cas)
            Path(args.cas).write_bytes(casanim.write_anim(a))
            print(describe(casanim.read_anim(args.cas)))
        elif args.cmd == "to-ms3d":
            a = _read_cas(args.cas, args.skeleton)
            Path(args.ms3d).write_bytes(write_ms3d(cas_to_ms3d(a)))
            print(f"{args.ms3d}: {len(a.tracks) - 1} joints, {len(a.key_times)} keys")
        elif args.cmd == "hide":
            a = hide_bone(_read_cas(args.cas), args.bone, tuple(args.offset))
            Path(args.out).write_bytes(casanim.write_anim(a))
            print(describe(casanim.read_anim(args.out)))
        else:
            print(describe(_read_cas(args.cas)))
    except (ConvertError, casanim.AnimError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
