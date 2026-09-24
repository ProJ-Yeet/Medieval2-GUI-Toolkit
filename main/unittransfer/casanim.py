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
table, the key times, then a record per node. What an animation adds is what
each node's record carries after its name::

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

**The offsets are into one block that follows the node table**: every animated
node's rotations first, 16 bytes a key (a quaternion, x y z w), then every
animated node's positions, 12 bytes a key. A node with no keys of a kind still
carries the running offset, so the offsets are checkable as a sequence and not
only as numbers. **Then the pivots**, three floats a node, and then the same
chunk list a model ends with, all of it empty, whose sizes must land exactly on
the last byte - or nothing at all: 220 of DaC's siege engine files and all 10
of ROCSS's end at their pivots (measured by Phase 57a's writer, which puts
every file back byte for byte).

**The pivots are AFTER the keys, and 55a had them before.** Both orders account
for every byte of every file, so every check above passed either way, and a
base pose (no keys) cannot tell them apart. What gave it away was drawing:
read before the keys, a soldier's idle has the pelvis quaternion repeated
through its "pivots" and every rotation read 252 bytes late, twelve bytes into
a key - which is why 55a found (1,0,0,0) and (0,0,0,1) both common as still
keys and could not say which component was w. Read after, the pivots are the
base pose's to three decimals and the first key of MTW2_Mace's idle is
``(0.052, 0.002, -0.000, 0.999)``: **w is last**, and every one of DaC's 1.23 M
soldier rotations is unit length to within 2e-7. The exporter does normalise.

**A position key is an offset from the pivot, not a position.** A soldier's
pelvis has pivot 0 and keys at its height (0.966 in MTW2_Mace's idle); every
other soldier bone keys zero and sits at its pivot. A siege engine's
destruction flings its wood chunks by keying a few centimetres from pivots a
metre out.

**Measured, 2026-09-23**: all 10 of ROCSS's loose files read, and 1 741 of
DaC's 1 753. The twelve refused are one siege engine, the Isengard ballista -
six files and a `convertedfiles` copy of the same six - and each ends twelve
bytes short: the keys are whole, the last node's pivot is missing and there is
no chunk list. Two of them are played by descr_engine_skeleton.txt.

**A base pose has no keys at all** - every count zero, the block empty - and is
the skeleton: node names, parents and pivots.
"""
from __future__ import annotations

import os
import struct
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    #: its bind position relative to its parent, from after the key block
    pivot: tuple
    #: per key, x y z w - empty when the node does not turn
    rot: array = field(default_factory=lambda: array("f"))
    #: per key, x y z, an offset from :attr:`pivot` - empty when the node
    #: does not move
    pos: array = field(default_factory=lambda: array("f"))
    #: 3ds Max's physics notes for the bone, which only siege engines carry
    properties: str = ""
    #: the bytes the file spells the name and the properties with, length and
    #: NUL included - :func:`write_anim` puts them back as they were (57a)
    name_raw: bytes = b""
    props_raw: bytes = b""
    #: the fifth integer of the node record, zero in every file measured
    extra: int = 0

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
    #: what :func:`write_anim` needs to write the file back byte for byte: the
    #: layout it was read in, the header's first 0x32 bytes, and the chunk list
    layout: tuple = (2, True)
    head: bytes = b""
    #: None for an animation made from nothing; b"" for a file that has no
    #: chunk list at all, as 230 of DaC's siege engine files do not
    tail: Optional[bytes] = None

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


def read_anim(path, skeleton: str = "", data_dir=None) -> Animation:
    """A loose ``.cas``, or a ``pack.dat`` entry written out under a ``.cas``
    name. The second is what an unpack of the pack leaves (see
    :func:`read_packed_bytes`), and reading one needs its ``skeleton``'s
    bones, from the unpacked skeleton under ``data_dir`` (the mod's ``data``
    folder, found from the path when not given)."""
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as e:
        raise AnimError(f"{p.name}: {e}") from None
    if packed_counts(data) is not None:
        if not skeleton:
            raise AnimError(f"{p.name} is an animation from the pack, not a loose .cas, "
                            "and reading one needs to know its skeleton")
        root = Path(data_dir) if data_dir is not None else _data_of(p)
        bones = skeleton_bones(root, skeleton) if root is not None else None
        if bones is None:
            raise AnimError(f"{p.name} is an animation from the pack, and this mod has no "
                            f"unpacked skeleton {skeleton!r} (animations/skeleton/"
                            f"{skeleton}) to give it its bones")
        return read_packed_bytes(data, str(p), bones, skeleton)
    return read_anim_bytes(data, str(p))


def _data_of(p: Path) -> Optional[Path]:
    """The ``data`` folder a file under ``data/animations`` is in: the
    OUTERMOST one, since an unpacked pack nests ``mods/<mod>/data`` inside."""
    for parent in reversed(p.parents):
        if parent.name.lower() == "data" and (parent / "animations").is_dir():
            return parent
    return None


# ---------------------------------------------------------------------------
# an animation from the pack (the unpacked pack.dat entries)
#
# An unpack of ``animations/pack.dat`` writes each entry out under the path it
# was packed from, with a ``.cas`` name, but the bytes are the pack's own
# format, not a loose .cas: three counts, then plain float32 arrays, frame by
# frame. Measured on Divide and Conquer's 10 396 unpacked files, every one of
# which is this size to the byte:
#
#   uint16 frames, uint16 rotation bones nq, uint8 position bones np
#   float32 x y z w         frames * nq   every bone's turn, frame by frame
#   float32 x y z           frames * np   the moving bones' LOCAL positions
#                                         (the pivot plus the offset)
#   float32 dx dz           frames        per-frame step of the root motion
#   float32                 frames        distance left to travel
#   float32 x y z           frames        the root motion itself
#   float32                 8             length, distance, speed, derived
#   uint64                                which bones move, one bit a bone
#
# The bones' names, parents and pivots are not in it: they are the skeleton's,
# from the unpacked ``skeletons.dat`` entry of the same name. The frames run at
# 20 a second. Turned into the loose shape this module already plays: a Scene
# Root, then a node per bone (parent + 1), positions as offsets from each
# bone's pivot, and the pelvis given the root motion rather than its in-place
# track, which is what a loose .cas of a walk carries.

PACKED_FPS = 20.0


def packed_counts(data: bytes) -> Optional[Tuple[int, int, int]]:
    """``(frames, nq, np)`` when ``data`` is a pack entry to the byte, else
    None. A loose .cas opens with a float version and never fits."""
    if len(data) < 45:
        return None
    nf, nq, npb = struct.unpack_from("<HHB", data, 0)
    if not nf or not nq or npb > nq or npb > 64:
        return None
    if len(data) != 5 + nf * (16 * nq + 12 * npb + 24) + 40:
        return None
    mask = int.from_bytes(data[-8:], "little")
    return (nf, nq, npb) if bin(mask).count("1") == npb else None


def packed_skeleton_bones(data: bytes, source: str = "") -> List[Tuple[str, int, tuple]]:
    """``[(name, parent, pivot)]`` from an unpacked ``skeletons.dat`` entry:
    a float scale, a uint16 bone count, a float, then per bone an int type,
    the position relative to its parent, the parent (-1 for the pelvis), 56
    bytes this does not need, and the name."""
    try:
        _scale, n, _ik = struct.unpack_from("<fHf", data, 0)
        o, out = 10, []
        for _ in range(n):
            x, y, z, parent = struct.unpack_from("<3fi", data, o + 4)
            end = data.index(b"\0", o + 76)
            out.append((data[o + 76:end].decode("latin-1"), parent, (x, y, z)))
            o = end + 1
    except (struct.error, ValueError):
        raise AnimError(f"{Path(source).name or 'skeleton'}: not a skeleton from the pack") from None
    if not out or any(not name for name, _p, _v in out):
        raise AnimError(f"{Path(source).name or 'skeleton'}: not a skeleton from the pack")
    return out


def skeleton_bones(data_dir, name: str) -> Optional[List[Tuple[str, int, tuple]]]:
    """The bones of skeleton ``name`` from the mod's unpacked skeletons:
    ``animations/skeleton/<name>``, or the same wherever an unpack nested it."""
    where = (str(data_dir), name.lower())
    hit = _SKEL_PATHS.get(where)
    try:
        st = hit.stat() if hit is not None else None
    except OSError:
        st = None
    if st is None:
        # looked up through the whole tree only when the file is not where it
        # was last time: the index checks every folder it walked, ~600 on DaC
        index = loose_index(data_dir)
        want = f"skeleton/{name.lower()}"
        hit = index.get(f"animations/{want}") or next(
            (f for k, f in index.items() if k.endswith("/" + want)), None)
        if hit is None:
            return None
        try:
            st = hit.stat()
        except OSError:
            return None
        _SKEL_PATHS[where] = hit
    key = (str(hit), st.st_mtime_ns, st.st_size)
    if key not in _BONES_CACHE:
        if len(_BONES_CACHE) > 512:
            _BONES_CACHE.clear()
        _BONES_CACHE[key] = packed_skeleton_bones(hit.read_bytes(), str(hit))
    return _BONES_CACHE[key]


_BONES_CACHE: Dict[tuple, List[Tuple[str, int, tuple]]] = {}
_SKEL_PATHS: Dict[tuple, Path] = {}


def read_packed_bytes(data: bytes, source: str, bones: List[Tuple[str, int, tuple]],
                      skeleton: str = "") -> Animation:
    """A pack entry as an :class:`Animation`, with ``bones`` from its skeleton."""
    counts = packed_counts(data)
    name = Path(source).name
    if counts is None:
        raise AnimError(f"{name}: not an animation from the pack")
    nf, nq, npb = counts
    if len(bones) < nq:
        raise AnimError(f"{name} turns {nq} bones and the skeleton {skeleton or ''} has "
                        f"{len(bones)}: it is another skeleton's animation")
    o = 5
    rot = array("f", data[o:o + nf * nq * 16]); o += nf * nq * 16
    pos = array("f", data[o:o + nf * npb * 12]); o += nf * npb * 12
    o += nf * 8 + nf * 4                      # the steps and distances, derived
    ctrl = array("f", data[o:o + nf * 12])
    mask = int.from_bytes(data[-8:], "little")
    moving = [b for b in range(64) if mask >> b & 1]
    out = Animation(source=source, version=3.2, length=(nf - 1) / PACKED_FPS,
                    key_times=array("f", [i / PACKED_FPS for i in range(nf)]),
                    layout=(2, True), head=b"", tail=None)
    out.tracks.append(Track("Scene Root", -1, (0.0, 0.0, 0.0)))
    for b, (bname, parent, pivot) in enumerate(bones):
        par = parent + 1 if 0 <= parent < b else 0
        t = Track(bname, par, tuple(float(v) for v in pivot))
        if b < nq:
            for f in range(nf):
                at = (f * nq + b) * 4
                t.rot.extend(rot[at:at + 4])
        if b in moving:
            src, stride, at = (ctrl, 3, 0) if b == 0 else (pos, npb * 3, moving.index(b) * 3)
            px, py, pz = t.pivot
            for f in range(nf):
                x, y, z = src[f * stride + at:f * stride + at + 3]
                t.pos.extend((x - px, y - py, z - pz))
        out.tracks.append(t)
    out.notes.append(f"from the pack's own format, with {skeleton or 'its skeleton'}'s bones")
    return out


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
    """The header and node table in one layout: ``(reader, scene, records)``.

    The reader is left on the byte after the last node record, which is where
    the key block starts; the pivots come after the keys, see :func:`_decode`."""
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
        at = r.p
        s.nodes.append(r.text())
        name_raw = data[at:r.p]
        five = struct.unpack_from("<5I", r.skip(20), 0)
        at = r.p
        pr = r.text() if props else ""
        recs.append((five, pr, name_raw, data[at:r.p]))
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
                    key_times=scene.key_times, layout=(pad, props),
                    head=data[:cas.NODE_COUNT_AT])
    keys = len(scene.key_times)
    counts = [(a, b, c, d, pr) for (a, b, c, d, _zero), pr, _n, _p in recs]
    base = r.p                           # the key block follows the node table

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
        out.tracks.append(Track(name=name, parent=scene.parents[i], pivot=(),
                                properties=pr, name_raw=recs[i][2],
                                props_raw=recs[i][3], extra=recs[i][0][4]))

    pos_run = rot_run
    for t, (nrot, npos, roff, poff, _) in zip(out.tracks, counts):
        if poff != pos_run:
            raise r.fail(f"node {t.name!r}'s positions start at {poff:,}, and the "
                         f"block before them ends at {pos_run:,}")
        pos_run += npos * POS_BYTES
        t.rot = _floats(r, base + roff, nrot * 4)
        t.pos = _floats(r, base + poff, npos * 3)

    r.p = base + pos_run
    pivots = r.floats(len(out.tracks) * 3)
    for i, t in enumerate(out.tracks):
        t.pivot = tuple(pivots[i * 3:i * 3 + 3])
    at = r.p
    _check_chunks(r, out)
    out.tail = data[at:]
    return out


def _text_bytes(value: str) -> bytes:
    raw = value.encode("latin-1") + b"\x00"
    return struct.pack("<I", len(raw)) + raw


def write_anim(a: Animation) -> bytes:
    """An animation as the bytes of a ``.cas``, in the layout it was read in.

    Phase 57a. Everything the reader checks is written from the object, so an
    edit that changes the key count, a track's keys or the times comes out with
    its offsets, counts and length consistent; the parts no edit touches - the
    header's other bytes, each name and property string, the chunk list - are
    the file's own bytes. So an unedited file comes back byte for byte, which is
    what ``tests/test_animedit.py`` holds on every loose file of both mods."""
    pad, props = a.layout
    keys = len(a.key_times)
    head = bytearray(a.head or bytes(cas.NODE_COUNT_AT))
    if len(head) < cas.NODE_COUNT_AT:
        head += bytes(cas.NODE_COUNT_AT - len(head))
    struct.pack_into("<f", head, 0, a.version or 3.2)
    struct.pack_into("<f", head, 16, a.length)
    out = [bytes(head[:cas.NODE_COUNT_AT]), struct.pack("<I", len(a.tracks)), b"\x00" * pad]
    out += [struct.pack("<I", t.parent) for t in a.tracks[1:]]
    out.append(struct.pack("<I", keys))
    out.append(array("f", a.key_times).tobytes())
    roffs, run = [], 0
    for t in a.tracks:
        if t.rot_keys > keys or t.pos_keys > keys:
            raise AnimError(f"{t.name!r} has more keys than the file's {keys}")
        roffs.append(run)
        run += t.rot_keys * ROT_BYTES
    poffs = []
    for t in a.tracks:
        poffs.append(run)
        run += t.pos_keys * POS_BYTES
    for t, ro, po in zip(a.tracks, roffs, poffs):
        out.append(t.name_raw or _text_bytes(t.name))
        out.append(struct.pack("<5I", t.rot_keys, t.pos_keys, ro, po, t.extra))
        if props:
            out.append(t.props_raw or _text_bytes(t.properties))
    out += [array("f", t.rot).tobytes() for t in a.tracks]
    out += [array("f", t.pos).tobytes() for t in a.tracks]
    out.append(array("f", [v for t in a.tracks for v in t.pivot]).tobytes())
    out.append(a.tail if a.tail is not None else _EMPTY_CHUNKS)
    return b"".join(out)


#: A chunk list for a file made from nothing, the shape every soldier's ends
#: with: two empty chunks. Only used when there is no file's own tail to keep.
_EMPTY_CHUNKS = struct.pack("<II", 18, 1) + b"\x00" * 10 + struct.pack("<II", 12, 5) + b"\x00" * 4


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
    rotation keys is identity. The position is the pivot plus the key, which is
    an offset (see the module docstring). The viewer does the same in the page;
    this is the reference it is tested against."""
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
            off = tuple(a[k] + (b[k] - a[k]) * f for k in range(3))
        else:
            off = _vec(tr.pos, 0) if tr.pos_keys else (0.0, 0.0, 0.0)
        pos = tuple(p + o for p, o in zip(tr.pivot, off))
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
    dropped, and the rest is looked up case-blind, the way Windows does. An
    unpacked ``pack.dat`` keeps that whole path under ``data/animations``, and
    is found as well: see :func:`find`."""
    return find(data_dir, path)[0]


# ---------------------------------------------------------------------------
# the chain: a model's skeleton, its actions, and which of them are loose (55b)


@dataclass
class SkeletonType:
    """One ``type`` block of ``descr_skeleton.txt``: its actions, in file order."""
    name: str
    scale: float = 1.0
    #: (action, path as the file writes it)
    anims: List[Tuple[str, str]] = field(default_factory=list)


_SKEL_CACHE: Dict[str, tuple] = {}


def skeleton_types(data_dir) -> Dict[str, SkeletonType]:
    """``descr_skeleton.txt`` as ``{lower-case type: SkeletonType}``.

    DaC's is 9.5 MB and 49 083 ``anim`` lines, and the viewer asks for one
    skeleton at a time, so the parse is kept until the file changes. Only the
    three keywords playback needs are read: ``type``, ``anim`` and ``scale``;
    ``strike_distances``, the ``in_*`` refpoints and the rest are battle AI."""
    path = Path(data_dir) / "descr_skeleton.txt"
    try:
        st = path.stat()
    except OSError:
        return {}
    key = str(path)
    hit = _SKEL_CACHE.get(key)
    if hit and hit[0] == (st.st_mtime_ns, st.st_size):
        return hit[1]
    out: Dict[str, SkeletonType] = {}
    cur = None
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            w = line.split(";", 1)[0].split()
            if not w:
                continue
            kw = w[0].lower()
            if kw == "type" and len(w) > 1:
                cur = out.setdefault(w[1].lower(), SkeletonType(w[1]))
            elif cur is None:
                continue
            elif kw == "anim" and len(w) > 2:
                cur.anims.append((w[1], w[2]))
            elif kw == "scale" and len(w) > 1:
                try:
                    cur.scale = float(w[1])
                except ValueError:
                    pass
    _SKEL_CACHE[key] = ((st.st_mtime_ns, st.st_size), out)
    return out


def loose_index(data_dir) -> Dict[str, Path]:
    """Every file under ``data/animations``, keyed by its lower-case path from
    ``data/``. One walk answers a whole skeleton's worth of :func:`resolve`,
    which looks each path up a folder at a time and takes seconds over the
    two hundred actions a soldier's skeleton names.

    Kept until one of the folders it walked changes: a file added or removed
    moves its folder's mtime, and a folder added moves its parent's, so
    stat-ing the folders from the last walk (16 on DaC) is enough to know."""
    root = Path(data_dir)
    hit = _LOOSE_CACHE.get(str(root))
    if hit is not None:
        try:
            if all(os.stat(d).st_mtime_ns == m for d, m in hit[0]):
                return hit[1]
        except OSError:
            pass
    out: Dict[str, Path] = {}
    seen = []
    for dirpath, _dirs, files in os.walk(root / "animations"):
        try:
            seen.append((dirpath, os.stat(dirpath).st_mtime_ns))
        except OSError:
            continue
        for f in files:
            full = Path(dirpath) / f
            out[full.relative_to(root).as_posix().lower()] = full
    try:
        # a mod with no animations folder at all is remembered by its data/
        seen.append((str(root), os.stat(root).st_mtime_ns))
    except OSError:
        pass
    _LOOSE_CACHE[str(root)] = (seen, out)
    return out


_LOOSE_CACHE: Dict[str, tuple] = {}


def _data_rel(path: str) -> str:
    rel = str(path).replace("\\", "/").strip()
    at = rel.lower().find("data/")
    return (rel[at + 5:] if at >= 0 else rel).lstrip("/")


def _tail(rel: str) -> str:
    """What follows the LAST ``data/`` in a path, lower-case: the part the game
    keeps, however deep an unpacked tree puts the file."""
    low = rel.replace("\\", "/").strip().lower()
    at = low.rfind("data/")
    return (low[at + 5:] if at >= 0 else low).lstrip("/")


#: the last index :func:`_tails` was built from, and what it built
_TAILS_CACHE: List[tuple] = []


def _tails(index: Dict[str, Path]) -> Dict[str, Optional[Path]]:
    """``tail -> file`` over one :func:`loose_index`, or ``None`` for a tail two
    files share: a guess between them could play the wrong animation."""
    if _TAILS_CACHE and _TAILS_CACHE[0][0] is index:
        return _TAILS_CACHE[0][1]
    out: Dict[str, Optional[Path]] = {}
    for key, full in index.items():
        t = _tail(key)
        out[t] = full if t not in out else None
    _TAILS_CACHE[:] = [(index, out)]
    return out


#: how :func:`find` found a file
FLAT, NESTED, TAIL = "flat", "nested", "tail"


def find(data_dir, path: str, index: Optional[Dict[str, Path]] = None
         ) -> Tuple[Optional[Path], str]:
    """``(file, how)`` for a ``descr_skeleton.txt`` path, or ``(None, "")``.

    Three places, in order, all case-blind:

    * ``flat`` - the path with whatever precedes ``data/`` dropped, the way the
      game reads it: ``mods/Third_Age_3/data/animations/X/a.cas`` is
      ``data/animations/X/a.cas``;
    * ``nested`` - the whole path under ``data/animations``, which is where an
      unpacked ``pack.dat`` puts it, because the pack stores each file under the
      path it was packed from: ``data/animations/mods/Third_Age_3/data/
      animations/X/a.cas``. DaC's own pack stores its files under nine mods'
      folders;
    * ``tail`` - a file anywhere under ``data/animations`` whose path ends in
      the same ``animations/X/a.cas`` after its last ``data/``, when exactly
      one does: an unpack into a folder of its own, or a pack that stored the
      file under another mod's name than ``descr_skeleton.txt`` writes.

    A file of the same NAME in another folder is never taken: DaC has
    ``MTW2_Crew_carry_stand_idle.cas`` in a crew folder and in a crossbow
    folder, and they are not the same animation."""
    if index is None:
        index = loose_index(data_dir)
    rel = _data_rel(path).lower()
    hit = index.get(rel)
    if hit is not None:
        return hit, FLAT
    written = str(path).replace("\\", "/").strip().lstrip("/").lower()
    if not written.startswith(("data/", "animations/")):
        hit = index.get("animations/" + written)
        if hit is not None:
            return hit, NESTED
    hit = _tails(index).get(_tail(written))
    if hit is not None:
        return hit, TAIL
    return None, ""


def actions_view(data_dir, skeletons: List[str]) -> dict:
    """What the viewer's animation picker offers for a model's skeletons.

    Per skeleton, every action ``descr_skeleton.txt`` names, and where it is:
    ``rel`` (a path under ``data/``) when the mod ships the file loose, empty
    when it does not - which, for most mods, is most of them, because the
    rest are packed in ``animations/pack.dat`` and nothing here reads that.

    A mod whose pack was unpacked in place has its files nested under
    ``data/animations/mods/<mod>/data/animations``; :func:`find` looks there
    too, and ``unpacked`` counts the actions found that way."""
    types = skeleton_types(data_dir)
    index = loose_index(data_dir) if types else {}
    root = Path(data_dir)
    out = []
    for name in skeletons:
        t = types.get((name or "").lower())
        if t is None:
            out.append({"skeleton": name, "found": False, "scale": 1.0,
                        "actions": [], "loose": 0})
            continue
        acts = []
        unpacked = 0
        for action, path in t.anims:
            hit, how = find(root, path, index)
            unpacked += how in (NESTED, TAIL)
            acts.append({"action": action, "file": Path(_data_rel(path)).name,
                         "rel": hit.relative_to(root).as_posix() if hit else ""})
        out.append({"skeleton": t.name, "found": True, "scale": t.scale,
                    "actions": acts, "loose": sum(1 for a in acts if a["rel"]),
                    "unpacked": unpacked})
    return {"skeletons": out,
            "file": (root / "descr_skeleton.txt").is_file()}
