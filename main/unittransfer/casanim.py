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


def actions_view(data_dir, skeletons: List[str]) -> dict:
    """What the viewer's animation picker offers for a model's skeletons.

    Per skeleton, every action ``descr_skeleton.txt`` names, and where it is:
    ``rel`` (a path under ``data/``) when the mod ships the file loose, empty
    when it does not - which, for most mods, is most of them, because the
    rest are packed in ``animations/pack.dat`` and nothing here reads that."""
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
        for action, path in t.anims:
            hit = index.get(_data_rel(path).lower())
            acts.append({"action": action, "file": Path(_data_rel(path)).name,
                         "rel": hit.relative_to(root).as_posix() if hit else ""})
        out.append({"skeleton": t.name, "found": True, "scale": t.scale,
                    "actions": acts, "loose": sum(1 for a in acts if a["rel"])})
    return {"skeletons": out,
            "file": (root / "descr_skeleton.txt").is_file()}
