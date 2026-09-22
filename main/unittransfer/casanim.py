r"""Read an animation ``.cas``: which bones turn, and how, over time (Phase 55a).

A battle model's animations are ``.cas`` files too, under ``data/animations``,
and :mod:`unittransfer.cas` could not read one: it expects a chunk list right
after the node table, and an animation puts its key data there first. The
first file tried, ``engine/ballista/ballista_stand_to_crank.cas``, stopped
cas.py at byte 680 with a zero-length "chunk" that was really the start of a
quaternion. Nothing in ``Reference/`` documents the layout, so it was read out
of the bytes of DaC's 1 753 loose animation files, and every one of them is
held to it (``tests/test_casanim.py``).

What an animation file is
-------------------------
**The header is the model header**: version, length, node count, the parent
table, the key times, then a record per node, then the pivots. What an
animation adds is what each node's record carries after its name::

    uint32  rotation key count      0, or the file's key count
    uint32  position key count      0, or the file's key count
    uint32  rotation offset         byte offset of this node's rotations
    uint32  position offset         byte offset of this node's positions
    uint32  0
    string  the bone's properties   length-prefixed, NUL included

That last field is why cas.py calls this "25 bytes": in every soldier's file
the string is empty - a length of 1 and its NUL. DaC's siege engines fill it
with 3ds Max's physics notes ("Mass = 50.000000 ... Simulation_Geometry = 2"),
and read as a fixed 25 bytes that sent every node after it into the text.

**The offsets are into one block that follows the pivots**: every animated
node's rotations first, 16 bytes a key (a quaternion, four floats, stored as
written - which of the four is w is settled below),
then every animated node's positions, 12 bytes a key. A node with no keys of a
kind still carries the running offset, so the offsets are checkable as a
sequence and not only as numbers - which is what keeps this reader from
reading plausibly rather than correctly. After the block comes the same chunk
list a model ends with, all of it empty, and the chunk sizes must land exactly
on the last byte.

The two checks that settled it, on the first two files measured: a horse
archer's idle has 24 bones x 31 keys of rotation (11 904 bytes) then of
position (8 928), then a 62-byte chunk list, which is the file's 20 894 bytes
to the byte; the ballista's crank has three bones x 37 rotation keys (1 776)
and a 94-byte chunk list, which is the rest of its file.

**Measured, 2026-09-22**: all 10 of ROCSS's loose files read, and 1 741 of
DaC's 1 753. The twelve refused are one siege engine, the Isengard ballista -
six files and a `convertedfiles` copy of the same six - and each is cut short,
its node table ending 12 to 48 bytes before its own pivots with no chunk list.
Two of them are played by descr_engine_skeleton.txt. The rotations are not
normalised by the exporter (DaC's soldiers: 99.52% within 0.5 to 1.5 of unit
length), so they are normalised when sampled. Which component is w is left to
Phase 55b, which draws the skeleton: both (1,0,0,0) and (0,0,0,1) appear as
exact still keys, and a picture settles it where a count cannot.

**A base pose has no keys at all** - every count zero, the block empty - and is
the skeleton: node names, parents and pivots. The pivot of a node with no
position keys is its position.
"""
from __future__ import annotations

import struct
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import cas

ROT_BYTES = 16
POS_BYTES = 12


class AnimError(cas.CasError):
    pass


@dataclass
class Track:
    """One node of the skeleton and what the animation does to it."""
    name: str
    parent: int
    #: its bind position relative to its parent, from the header
    pivot: tuple
    #: per key, x y z w - empty when the node does not turn
    rot: array = field(default_factory=lambda: array("f"))
    #: per key, x y z - empty when the node does not move
    pos: array = field(default_factory=lambda: array("f"))
    #: 3ds Max's physics notes for the bone, which only siege engines carry
    properties: str = ""

    @property
    def rot_keys(self) -> int:
        return len(self.rot) // 4

    @property
    def pos_keys(self) -> int:
        return len(self.pos) // 3


@dataclass
class Animation:
    source: str
    version: float = 0.0
    #: seconds, from the header
    length: float = 0.0
    key_times: array = field(default_factory=lambda: array("f"))
    tracks: List[Track] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def animated(self) -> List[Track]:
        return [t for t in self.tracks if t.rot_keys or t.pos_keys]

    @property
    def is_pose(self) -> bool:
        """No keys at all: a base pose, which is the skeleton itself."""
        return not self.animated

    def summary(self) -> str:
        return (f"{Path(self.source).name}: {len(self.tracks)} nodes, "
                f"{len(self.animated)} animated, {len(self.key_times)} keys "
                f"over {self.length:g}s")

    def view(self) -> dict:
        """What the viewer plays: plain lists, rotations as [x, y, z, w]."""
        return {
            "source": Path(self.source).name, "length": self.length,
            "times": [round(t, 5) for t in self.key_times],
            "pose": self.is_pose,
            "bones": [{
                "name": t.name, "parent": t.parent,
                "pivot": [round(v, 6) for v in t.pivot],
                "rot": [[round(t.rot[i + j], 6) for j in range(4)]
                        for i in range(0, len(t.rot), 4)],
                "pos": [[round(t.pos[i + j], 6) for j in range(3)]
                        for i in range(0, len(t.pos), 3)],
            } for t in self.tracks],
        }


def read_anim(path) -> Animation:
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as e:
        raise AnimError(f"{p.name}: {e}") from None
    return read_anim_bytes(data, str(p))


#: The layouts a node table comes in, as (pad bytes after the node count,
#: whether each node record ends with a properties string). The first is every
#: soldier's file, stamped 3.16 and later - cas.py's layout. DaC's siege engine
#: animations stamped 3.02 write ONE pad byte and no properties string (read the
#: first way, every parent comes out as 0x01000000), and the 3.05 to 3.12 ones
#: the other two combinations. Neither the version number nor the first bytes
#: decide it reliably, so each file is decoded each way in turn and the first
#: that passes every check - parents, key times, the offsets as a sequence, the
#: chunk list landing on the last byte - is it.
LAYOUTS = ((2, True), (1, False), (2, False), (1, True))


def _header(data: bytes, source: str, pad: int, props: bool):
    """The header and node table in one layout: ``(reader, scene, records)``."""
    r = cas._Reader(data, source)
    s = cas.CasScene(source)
    s.version = r.f32()
    if not cas.MIN_VERSION <= s.version <= cas.MAX_VERSION:
        raise r.fail(f"opens with {s.version:g}, which is not a .cas version")
    r.skip(12)
    s.length = r.f32()
    r.p = cas.NODE_COUNT_AT
    n = r.count("the node count")
    if not 1 <= n <= 1024:
        raise r.fail(f"says it has {n:,} nodes")
    r.skip(pad)
    s.parents = [-1] + [r.u32() for _ in range(n - 1)]
    bad = [x for x in s.parents[1:] if not 0 <= x < n]
    if bad:
        raise r.fail(f"the parent table points at nodes {bad[:3]} of {n}")
    s.key_times = r.floats(r.count("the key count"))
    kt = list(s.key_times)
    if kt and (abs(kt[0]) > 1e-6 or any(y < x for x, y in zip(kt, kt[1:]))):
        raise r.fail("its key times do not start at 0 and rise")
    recs = []
    for _ in range(n):
        s.nodes.append(r.text())
        five = struct.unpack_from("<5I", r.skip(20), 0)
        recs.append((five, r.text() if props else ""))
    s.pivots = r.floats(n * 3)
    return r, s, recs


def read_anim_bytes(data: bytes, source: str) -> Animation:
    """Decode one animation file, or raise :class:`AnimError` saying where.

    The error raised is the first layout's, since that is every soldier's."""
    first = None
    for pad, props in LAYOUTS:
        try:
            return _decode(data, source, pad, props)
        except cas.CasError as e:
            first = first or e
    raise AnimError(str(first))


def _decode(data: bytes, source: str, pad: int, props: bool) -> Animation:
    r, scene, recs = _header(data, source, pad, props)
    out = Animation(source=source, version=scene.version, length=scene.length,
                    key_times=scene.key_times)
    keys = len(scene.key_times)
    counts = [(a, b, c, d, pr) for (a, b, c, d, _zero), pr in recs]
    base = r.p                                  # the block starts after the pivots

    rot_run = 0
    for i, (name, (nrot, npos, roff, poff, pr)) in enumerate(zip(scene.nodes, counts)):
        if nrot > keys or npos > keys:
            raise r.fail(f"node {name!r} has {nrot} rotation and {npos} position keys, "
                         f"and the file has {keys}")
        # Every soldier's track has 0, 1 or all of the keys. DaC's bomb_dead.cas,
        # which descr_engine_skeleton.txt plays, has 99 of its 101: those are
        # the first 99 times, and the last pose holds.
        short = [c for c in (nrot, npos) if c not in (0, 1, keys)]
        if short:
            out.notes.append(f"node {name!r} has {max(short)} keys of the file's "
                             f"{keys}; the last one holds")
        if roff != rot_run:
            raise r.fail(f"node {name!r}'s rotations start at {roff:,}, and the "
                         f"nodes before it end at {rot_run:,}")
        rot_run += nrot * ROT_BYTES
        out.tracks.append(Track(name=name, parent=scene.parents[i],
                                pivot=tuple(scene.pivots[i * 3:i * 3 + 3]),
                                properties=pr))

    pos_run = rot_run
    for t, (nrot, npos, roff, poff, _) in zip(out.tracks, counts):
        if poff != pos_run:
            raise r.fail(f"node {t.name!r}'s positions start at {poff:,}, and the "
                         f"block before them ends at {pos_run:,}")
        pos_run += npos * POS_BYTES
        t.rot = _floats(r, base + roff, nrot * 4)
        t.pos = _floats(r, base + poff, npos * 3)

    r.p = base + pos_run
    _check_chunks(r, out)
    return out


def _floats(r: "cas._Reader", at: int, n: int) -> array:
    if n == 0:
        return array("f")
    r.p = at
    return r.floats(n)


def _check_chunks(r: "cas._Reader", out: Animation) -> None:
    """The model's chunk list, all empty, landing on the last byte."""
    while r.p < len(r.d):
        start = r.p
        if start + 8 > len(r.d):
            raise r.fail(f"{len(r.d) - start} bytes after the key data are not a chunk")
        size, kind = r.u32(), r.u32()
        if size < 8 or start + size > len(r.d):
            raise r.fail(f"after the key data, the chunk at byte {start:,} says it is "
                         f"{size:,} bytes of the {len(r.d):,} in the file")
        if size > 24:
            # nine of DaC's siege engines carry their mesh inside the animation
            what = {1: "a static mesh", 2: "a skinned mesh", 5: "materials"}.get(kind, f"chunk kind {kind}")
            out.notes.append(f"also carries {what} ({size:,} bytes), as some siege "
                             f"engine animations do; only the keys are read here")
        r.p = start + size


def sample(anim: Animation, t: float) -> List[dict]:
    """Each node's local rotation and position at ``t`` seconds (looping).

    Rotations are slerped between the two keys around ``t``; a node with no
    rotation keys is identity, with no position keys its pivot. The viewer does
    the same in the page; this is the reference it is tested against."""
    times = anim.key_times
    if len(times) > 1 and anim.length > 0:
        t = t % max(times[-1], 1e-6)
    i, f = _bracket(times, t)
    out = []
    for tr in anim.tracks:
        rot = _slerp(_quat(tr.rot, i), _quat(tr.rot, i + 1), f) if tr.rot_keys > 1 \
            else (_quat(tr.rot, 0) if tr.rot_keys else (0.0, 0.0, 0.0, 1.0))
        if tr.pos_keys > 1:
            a, b = _vec(tr.pos, i), _vec(tr.pos, i + 1)
            pos = tuple(a[k] + (b[k] - a[k]) * f for k in range(3))
        else:
            pos = _vec(tr.pos, 0) if tr.pos_keys else tuple(tr.pivot)
        out.append({"name": tr.name, "rot": rot, "pos": pos})
    return out


def _bracket(times, t: float):
    if len(times) < 2:
        return 0, 0.0
    for i in range(len(times) - 1):
        if times[i + 1] >= t:
            span = times[i + 1] - times[i]
            return i, (0.0 if span <= 0 else (t - times[i]) / span)
    return len(times) - 2, 1.0


def _quat(a: array, i: int) -> tuple:
    n = len(a) // 4
    i = max(0, min(i, n - 1))
    return tuple(a[i * 4:i * 4 + 4])


def _vec(a: array, i: int) -> tuple:
    n = len(a) // 3
    i = max(0, min(i, n - 1))
    return tuple(a[i * 3:i * 3 + 3])


def _slerp(a: tuple, b: tuple, f: float) -> tuple:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0:                                  # the short way round
        b, dot = tuple(-x for x in b), -dot
    if dot > 0.9995:
        q = tuple(x + (y - x) * f for x, y in zip(a, b))
    else:
        th = math.acos(max(-1.0, min(1.0, dot)))
        s = math.sin(th)
        wa, wb = math.sin((1 - f) * th) / s, math.sin(f * th) / s
        q = tuple(wa * x + wb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in q)) or 1.0
    return tuple(x / n for x in q)


def resolve(data_dir, path: str) -> Optional[Path]:
    """A path from ``descr_skeleton.txt``, found in THIS mod.

    DaC's names another mod's folder for every one of its files
    (``mods/Third_Age_3/data/animations/...``) and still plays, because the same
    relative path is under its own ``data/``. So whatever precedes ``data/`` is
    dropped, and the rest is looked up case-blind, the way Windows does."""
    rel = str(path).replace("\\", "/").strip()
    low = rel.lower()
    at = low.find("data/")
    rel = rel[at + 5:] if at >= 0 else rel
    cur = Path(data_dir)
    for part in [x for x in rel.split("/") if x]:
        # the directory's own spelling, not the one typed: Windows answers
        # `exists()` for either, and the name is shown to people
        try:
            hit = next((c for c in cur.iterdir() if c.name.lower() == part.lower()), None)
        except OSError:
            hit = None
        if hit is None:
            return None
        cur = hit
    return cur if cur.is_file() else None
