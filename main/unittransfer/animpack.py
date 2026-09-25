r"""The battle animation packs, read without unpacking them (Phase 77).

A mod's battle animations live in ``data/animations/pack.idx`` + ``pack.dat``,
its compiled skeletons in ``skeletons.idx`` + ``skeletons.dat``. The ``.idx``
is a table of contents, the ``.dat`` the files one after another. This module
is the one place the four files are read (and, from Phase 81, written): the
rest of the toolkit asks it for an index, one animation, or one skeleton, and
never opens a pack itself. :mod:`unittransfer.casanim` keeps the loose
``.cas`` files and is handed arrays from here.

Nothing is unpacked. An entry is read straight out of the ``.dat`` by the
offset its index record gives, so DaC's 352 MB ``pack.dat`` is opened, seeked
and read a few kilobytes at a time.

The container
-------------
Both files open with the same 20 bytes, little endian::

    char[9]  magic          ANIM.PACK or SKEL.PACK, no NUL
    byte[3]  filler         differs on every install (56 3C 7C vanilla,
                            00 00 00 ROCSS, 00 36 05 DaC); never read
    uint16   version        9 for animations, 14 for skeletons
    uint16   second value   0 for animations, 24 for skeletons
    uint32   entry count

then, in the ``.idx`` only, a record per entry::

    int32    record size    bytes after these three ints
    int32    offset         of the file in the .dat (the first is 20)
    int32    size           of the file
    float32  scale          ) animations only: the scale is the one value
    uint16   frames         ) not also in the entry; the three counts are
    uint16   rotation bones ) copies of its first five bytes
    uint8    position bones )
    char[]   name + NUL     a skeleton's name, or an animation's full path

In the ``.dat`` the files run from byte 20 to the last byte, in index order,
touching. A pack can list a name twice, each with its own bytes (DaC 916
animation paths, vanilla 3 and one skeleton): :meth:`PackIndex.find` returns
every copy, :meth:`PackIndex.first` the first. Which copy the game plays is
Phase 82's question 5.

A packed animation
------------------
Not a loose ``.cas``: three counts and then plain float32 arrays, frame by
frame. ``5 + frames * (16 nq + 12 np + 24) + 40`` bytes, which every one of
the 21 195 installed entries is to the byte::

    uint16 frames, uint16 rotation bones nq, uint8 position bones np
    float32 x y z w     frames * nq   each bone's rotation (w last)
    float32 x y z       frames * np   the moving bones' local positions
    float32 dx dz       frames        per-frame step of the root motion
    float32             frames        distance still to travel
    float32 x y z       frames        the root motion (the control bone)
    float32             8             duration, distance, dx dy dz, speed...
    uint64                            which bones move, one bit a bone

A packed skeleton
-----------------
One ``descr_skeleton.txt`` type, compiled: a header (scale, bone count, a
float), the bones, then **exactly 687 animation slots** in the engine's fixed
order (an empty slot is one ``00`` byte, the last is ``default`` and always
filled), then the speeds and the combat tables. The bones and slots are parsed
here; everything after the last slot is kept as bytes and written back
untouched, since nothing in this toolkit builds a combat table. A slot's path
is exactly a ``pack.idx`` name, which is how a skeleton names its animations.

**Held to**: every skeleton on vanilla, ROCSS and DaC (730) serializes back to
its own bytes, and every index serializes back to its own file
(``tests/test_animpack.py``).
"""
from __future__ import annotations

import os
import struct
from array import array
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

HEADER_SIZE = 20
ANIM_MAGIC = b"ANIM.PACK"
SKEL_MAGIC = b"SKEL.PACK"
#: The engine's fixed slot count; the last (686) is ``default``.
SKELETON_SLOTS = 687
FPS = 20.0

#: The four files, by the name each has in ``data/animations``.
FILES = ("pack.idx", "pack.dat", "skeletons.idx", "skeletons.dat")

BONE_TYPES = {0: "normal", 1: "saddle", 2: "platform", 4: "left hand", 5: "right hand",
              6: "head", 7: "torso", 8: "abs", 9: "pelvis"}


class PackError(ValueError):
    """A pack file that does not read as one, with the file and where."""


# ---------------------------------------------------------------------------
# the index

class PackEntry:
    """One ``.idx`` record. ``scale``/``frames``/``rot_bones``/``pos_bones``
    are None for a skeleton."""

    __slots__ = ("name", "offset", "size", "scale", "frames", "rot_bones", "pos_bones")

    def __init__(self, name: str, offset: int, size: int, scale: Optional[float] = None,
                 frames: Optional[int] = None, rot_bones: Optional[int] = None,
                 pos_bones: Optional[int] = None):
        self.name, self.offset, self.size = name, offset, size
        self.scale, self.frames = scale, frames
        self.rot_bones, self.pos_bones = rot_bones, pos_bones

    @property
    def is_anim(self) -> bool:
        return self.frames is not None

    def record(self) -> bytes:
        name = self.name.encode("latin-1") + b"\0"
        if self.is_anim:
            body = struct.pack("<fHHB", self.scale, self.frames, self.rot_bones,
                               self.pos_bones) + name
        else:
            body = name
        return struct.pack("<iii", len(body), self.offset, self.size) + body

    def __repr__(self):
        return f"<PackEntry {self.name} @{self.offset} +{self.size}>"


def _key(name: str) -> str:
    return name.replace("\\", "/").lower()


class PackIndex:
    """A ``pack.idx`` or ``skeletons.idx``: the header, then one record per
    entry. ``path`` is the ``.idx``; its ``.dat`` is beside it."""

    def __init__(self, magic: bytes, entries: List[PackEntry], version: int, version2: int,
                 filler: bytes = b"\0\0\0", path: Optional[Path] = None):
        self.magic, self.entries = magic, entries
        self.version, self.version2, self.filler = version, version2, filler
        self.path = Path(path) if path is not None else None
        self._by_name: Optional[Dict[str, List[PackEntry]]] = None

    @classmethod
    def read(cls, path) -> "PackIndex":
        path = Path(path)
        return cls.from_bytes(path.read_bytes(), path)

    @classmethod
    def from_bytes(cls, b: bytes, path=None) -> "PackIndex":
        where = Path(path).name if path is not None else "index"
        magic = bytes(b[:9])
        if len(b) < HEADER_SIZE or magic not in (ANIM_MAGIC, SKEL_MAGIC):
            raise PackError(f"{where}: not a pack index (starts {magic!r})")
        version, version2, count = struct.unpack_from("<HHI", b, 12)
        anim = magic == ANIM_MAGIC
        entries, p = [], HEADER_SIZE
        try:
            for _ in range(count):
                rsize, offset, size = struct.unpack_from("<iii", b, p)
                p += 12
                start = p
                if anim:
                    scale, frames, rot, pos = struct.unpack_from("<fHHB", b, p)
                    p += 9
                else:
                    scale = frames = rot = pos = None
                end = b.index(b"\0", p)
                name = b[p:end].decode("latin-1")
                p = end + 1
                if p - start != rsize:
                    raise PackError(f"{where}: record {len(entries)} ({name!r}) says "
                                    f"{rsize} bytes and is {p - start}")
                entries.append(PackEntry(name, offset, size, scale, frames, rot, pos))
        except (struct.error, ValueError) as e:
            if isinstance(e, PackError):
                raise
            raise PackError(f"{where}: cut short at record {len(entries)} of {count}") from None
        if p != len(b):
            raise PackError(f"{where}: {len(b) - p} bytes after the last record")
        return cls(magic, entries, version, version2, bytes(b[9:12]), path)

    def header(self, count: Optional[int] = None) -> bytes:
        """The 20 bytes both the ``.idx`` and the ``.dat`` open with."""
        n = len(self.entries) if count is None else count
        return self.magic + self.filler + struct.pack("<HHI", self.version, self.version2, n)

    def to_bytes(self) -> bytes:
        return self.header() + b"".join(e.record() for e in self.entries)

    @property
    def is_anim(self) -> bool:
        return self.magic == ANIM_MAGIC

    @property
    def dat_path(self) -> Optional[Path]:
        return self.path.with_suffix(".dat") if self.path is not None else None

    def _names(self) -> Dict[str, List[PackEntry]]:
        if self._by_name is None:
            out: Dict[str, List[PackEntry]] = {}
            for e in self.entries:
                out.setdefault(_key(e.name), []).append(e)
            self._by_name = out
        return self._by_name

    def find(self, name: str) -> List[PackEntry]:
        """Every entry under ``name``, case-blind, slashes either way."""
        return list(self._names().get(_key(name), ()))

    def first(self, name: str) -> Optional[PackEntry]:
        hits = self._names().get(_key(name))
        return hits[0] if hits else None

    def __contains__(self, name: str) -> bool:
        return _key(name) in self._names()

    def __len__(self) -> int:
        return len(self.entries)

    def duplicates(self) -> Dict[str, List[PackEntry]]:
        """The names listed more than once, keyed by their lower-case name."""
        return {k: v for k, v in self._names().items() if len(v) > 1}

    def read_entry(self, entry: PackEntry, fid=None) -> bytes:
        """The entry's bytes out of the ``.dat``. Pass an open ``fid`` when
        reading many, to open the file once."""
        if fid is None:
            with open(self.dat_path, "rb") as f:
                return self.read_entry(entry, f)
        fid.seek(entry.offset)
        data = fid.read(entry.size)
        if len(data) != entry.size:
            raise PackError(f"{self.dat_path.name}: {entry.name} runs past the end "
                            f"({entry.offset}+{entry.size})")
        return data


# ---------------------------------------------------------------------------
# a packed animation

def anim_size(frames: int, nq: int, npb: int) -> int:
    return 5 + frames * (16 * nq + 12 * npb + 24) + 40


class PackedAnimation:
    """One ``pack.dat`` entry, as flat float arrays (frame-major, as stored).

    ``rotations[(f * nq + b) * 4:][:4]`` is bone ``b``'s quaternion at frame
    ``f``, x y z w; ``positions`` holds only the bones in :attr:`moving`,
    in bone order; ``control`` is the root motion, three floats a frame."""

    __slots__ = ("frames", "rot_bones", "pos_bones", "rotations", "positions", "steps",
                 "distance_left", "control", "summary", "mask")

    def __init__(self, data: bytes, source: str = ""):
        where = source or "animation"
        if len(data) < 45:
            raise PackError(f"{where}: {len(data)} bytes is too short for an animation")
        nf, nq, npb = struct.unpack_from("<HHB", data, 0)
        if len(data) != anim_size(nf, nq, npb):
            raise PackError(f"{where}: {len(data)} bytes, and {nf} frames of {nq} bones "
                            f"({npb} moving) is {anim_size(nf, nq, npb)}")
        self.frames, self.rot_bones, self.pos_bones = nf, nq, npb
        o = 5

        def take(n: int) -> array:
            nonlocal o
            a = array("f")
            a.frombytes(data[o:o + 4 * n])
            o += 4 * n
            return a

        self.rotations = take(nf * nq * 4)
        self.positions = take(nf * npb * 3)
        self.steps = take(nf * 2)
        self.distance_left = take(nf)
        self.control = take(nf * 3)
        self.summary = take(8)
        self.mask = int.from_bytes(data[o:o + 8], "little")
        if bin(self.mask).count("1") != npb:
            raise PackError(f"{where}: {npb} moving bones and {bin(self.mask).count('1')} "
                            "bits set in the mask")

    def to_bytes(self) -> bytes:
        return (struct.pack("<HHB", self.frames, self.rot_bones, self.pos_bones)
                + self.rotations.tobytes() + self.positions.tobytes() + self.steps.tobytes()
                + self.distance_left.tobytes() + self.control.tobytes()
                + self.summary.tobytes() + self.mask.to_bytes(8, "little"))

    @property
    def moving(self) -> List[int]:
        """The bones with a position track, in the order ``positions`` holds them."""
        return [b for b in range(64) if self.mask >> b & 1]

    @property
    def duration(self) -> float:
        return (self.frames - 1) / FPS

    @property
    def distance(self) -> float:
        """How far the root motion travels, across the ground."""
        return float(self.summary[1])

    @property
    def speed(self) -> float:
        return float(self.summary[5])

    def rotation(self, frame: int, bone: int) -> Tuple[float, float, float, float]:
        at = (frame * self.rot_bones + bone) * 4
        return tuple(self.rotations[at:at + 4])


# ---------------------------------------------------------------------------
# a packed skeleton

_STRUCTS: Dict[str, struct.Struct] = {}


class _Reader:
    __slots__ = ("b", "p", "where")

    def __init__(self, b: bytes, where: str):
        self.b, self.p, self.where = b, 0, where

    def f(self, fmt: str):
        s = _STRUCTS.get(fmt)
        if s is None:
            s = _STRUCTS[fmt] = struct.Struct("<" + fmt)
        v = s.unpack_from(self.b, self.p)
        self.p += s.size
        return v

    def cstr(self, stops=b"\0") -> Tuple[str, int]:
        """The string up to the first byte in ``stops``, and that byte."""
        e = self.p
        b = self.b
        while b[e] not in stops:
            e += 1
        v = b[self.p:e].decode("latin-1")
        self.p = e + 1
        return v, b[e]


class Bone:
    """A skeleton bone. ``pos`` is relative to the parent (the loose ``.cas``
    pivot); ``flags``, ``other`` and ``matrix`` are carried, not interpreted."""

    __slots__ = ("name", "type", "pos", "parent", "flags", "other", "matrix")
    _FMT = struct.Struct("<i3fi4si12f")

    def __init__(self, name, type_, pos, parent, flags, other, matrix):
        self.name, self.type, self.pos, self.parent = name, type_, pos, parent
        self.flags, self.other, self.matrix = flags, other, matrix

    def to_bytes(self) -> bytes:
        return (self._FMT.pack(self.type, *self.pos, self.parent, self.flags, self.other,
                               *self.matrix)
                + self.name.encode("latin-1") + b"\0")


class Event:
    """A sound or effect cue on a slot, from frame ``start`` to ``end``.
    ``stop`` is the byte that ended the name, ``00`` or ``01``: both occur."""

    __slots__ = ("type", "start", "end", "name", "stop", "random", "looped")

    def __init__(self, type_, start, end, name, stop, random, looped):
        self.type, self.start, self.end, self.name = type_, start, end, name
        self.stop, self.random, self.looped = stop, random, looped

    def to_bytes(self) -> bytes:
        return (struct.pack("<IHH", self.type, self.start, self.end)
                + self.name.encode("latin-1") + bytes((self.stop, self.random, self.looped)))


class Slot:
    """A filled animation slot: the animation's pack path and its timing.
    The turn limits are stored as int16 (times pi/32768 for radians)."""

    __slots__ = ("path", "delta_rot", "impact", "delta_angle", "delta_length",
                 "impact_frame", "impact_dist", "min_turn", "max_turn", "launch",
                 "events", "evade_parry", "probability")
    _MID = struct.Struct("<h3fhfhfhh3f")
    _END = struct.Struct("<ih")

    def to_bytes(self) -> bytes:
        return (self.path.encode("latin-1") + b"\0"
                + self._MID.pack(self.delta_rot, *self.impact, self.delta_angle,
                                 self.delta_length, self.impact_frame, self.impact_dist,
                                 self.min_turn, self.max_turn, *self.launch)
                + struct.pack("<I", len(self.events))
                + b"".join(e.to_bytes() for e in self.events)
                + self._END.pack(self.evade_parry, self.probability))


class PackedSkeleton:
    """One ``skeletons.dat`` entry: the bones, the 687 slots (None where
    empty), and ``tail``, everything after the last slot, as bytes."""

    def __init__(self, data: bytes, source: str = ""):
        where = source or "skeleton"
        r = _Reader(data, where)
        try:
            self.scale, nbones, self.ik_lerp = r.f("fHf")
            self.bones: List[Bone] = []
            for _ in range(nbones):
                btype, x, y, z, parent, flags, other, *matrix = r.f("i3fi4si12f")
                name, _stop = r.cstr()
                self.bones.append(Bone(name, btype, (x, y, z), parent, flags, other,
                                       tuple(matrix)))
            self.slots: List[Optional[Slot]] = []
            for _ in range(SKELETON_SLOTS):
                if data[r.p] == 0:
                    r.p += 1
                    self.slots.append(None)
                    continue
                s = Slot()
                s.path, _stop = r.cstr()
                (s.delta_rot, ix, iy, iz, s.delta_angle, s.delta_length, s.impact_frame,
                 s.impact_dist, s.min_turn, s.max_turn, lx, ly, lz) = r.f("h3fhfhfhh3f")
                s.impact, s.launch = (ix, iy, iz), (lx, ly, lz)
                s.events = []
                for _ in range(r.f("I")[0]):
                    etype, start, end = r.f("IHH")
                    name, stop = r.cstr(b"\0\1")
                    rnd, looped = r.f("BB")
                    s.events.append(Event(etype, start, end, name, stop, rnd, looped))
                s.evade_parry, s.probability = r.f("ih")
                self.slots.append(s)
        except (struct.error, IndexError):
            raise PackError(f"{where}: cut short at byte {r.p} of {len(data)}") from None
        if len(data) - r.p < 12:
            raise PackError(f"{where}: {len(data) - r.p} bytes after the slots, "
                            "too few for the speeds")
        self.tail = bytes(data[r.p:])

    def to_bytes(self) -> bytes:
        return b"".join([struct.pack("<fHf", self.scale, len(self.bones), self.ik_lerp),
                         *(b.to_bytes() for b in self.bones),
                         *(s.to_bytes() if s else b"\0" for s in self.slots),
                         self.tail])

    @property
    def speeds(self) -> Tuple[float, float, float]:
        """Walk, run and charge speed: the first twelve bytes of the tail."""
        return struct.unpack_from("<3f", self.tail, 0)

    def filled(self) -> List[Tuple[int, Slot]]:
        return [(i, s) for i, s in enumerate(self.slots) if s is not None]

    def animation_paths(self) -> List[str]:
        """Each distinct animation path the slots name, in slot order."""
        seen, out = set(), []
        for s in self.slots:
            if s is not None and _key(s.path) not in seen:
                seen.add(_key(s.path))
                out.append(s.path)
        return out

    def bone_table(self) -> List[Tuple[str, int, tuple]]:
        """``[(name, parent, pivot)]``, the shape
        :func:`unittransfer.casanim.read_packed_bytes` takes."""
        return [(b.name, b.parent, b.pos) for b in self.bones]


# ---------------------------------------------------------------------------
# a mod's packs, cached

def animations_dir(data_dir) -> Optional[Path]:
    """``<data>/animations``, whatever its case (vanilla's is ``Animations``)."""
    d = Path(data_dir)
    direct = d / "animations"
    if direct.is_dir():
        return direct
    try:
        for child in d.iterdir():
            if child.name.lower() == "animations" and child.is_dir():
                return child
    except OSError:
        pass
    return None


class Packs:
    """The two packs in one ``data/animations`` folder. Either index is None
    when that pair is not there (most mods ship neither and play vanilla's)."""

    def __init__(self, anim_dir):
        self.dir = Path(anim_dir)
        self.anims = self._index("pack.idx")
        self.skels = self._index("skeletons.idx")
        self._skel_cache: Dict[int, PackedSkeleton] = {}

    def _index(self, name: str) -> Optional[PackIndex]:
        idx, dat = self.dir / name, (self.dir / name).with_suffix(".dat")
        if not (idx.is_file() and dat.is_file()):
            return None
        return PackIndex.read(idx)

    def animation_bytes(self, path: str) -> Optional[bytes]:
        e = self.anims.first(path) if self.anims else None
        return self.anims.read_entry(e) if e else None

    def animation(self, path: str) -> Optional[PackedAnimation]:
        data = self.animation_bytes(path)
        return PackedAnimation(data, path) if data is not None else None

    def skeleton(self, name: str) -> Optional[PackedSkeleton]:
        """The first skeleton listed under ``name``, parsed once."""
        e = self.skels.first(name) if self.skels else None
        if e is None:
            return None
        if e.offset not in self._skel_cache:
            self._skel_cache[e.offset] = PackedSkeleton(self.skels.read_entry(e), e.name)
        return self._skel_cache[e.offset]

    def skeleton_names(self) -> List[str]:
        return [e.name for e in self.skels.entries] if self.skels else []


def _stamp(anim_dir: Path) -> tuple:
    out = []
    for name in FILES:
        try:
            st = (anim_dir / name).stat()
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


_CACHE: Dict[str, Tuple[tuple, Packs]] = {}


def open_packs(anim_dir) -> Packs:
    """The packs in ``anim_dir``, read once and read again only when one of
    the four files changes its time or size."""
    anim_dir = Path(anim_dir)
    key, stamp = os.path.normcase(str(anim_dir.resolve())), _stamp(anim_dir)
    hit = _CACHE.get(key)
    if hit is None or hit[0] != stamp:
        if len(_CACHE) > 16:
            _CACHE.clear()
        hit = _CACHE[key] = (stamp, Packs(anim_dir))
    return hit[1]


def for_data(data_dir) -> Optional[Packs]:
    """A mod's (or vanilla's) packs from its ``data`` folder, or None when it
    has neither pack."""
    d = animations_dir(data_dir)
    if d is None:
        return None
    packs = open_packs(d)
    return packs if (packs.anims or packs.skels) else None


# ---------------------------------------------------------------------------
# the structural checks

def check(anim_dir) -> dict:
    """Every structural rule above, counted over a whole ``data/animations``
    folder. Each count should equal the matching entry count; ``problems``
    lists the first few that do not."""
    packs = open_packs(anim_dir)
    c: dict = {}
    problems: List[str] = []

    def add(k: str, n: int = 1):
        c[k] = c.get(k, 0) + n

    for kind, idx in (("anim", packs.anims), ("skel", packs.skels)):
        if idx is None:
            continue
        dat = idx.dat_path
        c[f"{kind} entries"] = len(idx)
        spans = sorted((e.offset, e.offset + e.size) for e in idx.entries)
        touching = (not spans or spans[0][0] == HEADER_SIZE) and all(
            a[1] == b[0] for a, b in zip(spans, spans[1:]))
        c[f"{kind} contiguous to the end"] = int(
            touching and (spans[-1][1] if spans else HEADER_SIZE) == dat.stat().st_size)
        with open(dat, "rb") as f:
            head = f.read(HEADER_SIZE)
        c[f"{kind} .dat header = .idx header"] = int(head == idx.header())
        c[f"{kind} index round-trips"] = int(idx.to_bytes() == idx.path.read_bytes())
        c[f"{kind} duplicate names"] = sum(len(v) - 1 for v in idx.duplicates().values())
    if packs.anims is not None:
        with open(packs.anims.dat_path, "rb") as f:
            for e in packs.anims.entries:
                data = packs.anims.read_entry(e, f)
                try:
                    a = PackedAnimation(data, e.name)
                except PackError as err:
                    if len(problems) < 8:
                        problems.append(str(err))
                    continue
                add("anim reads")
                add("anim counts = index", (a.frames, a.rot_bones, a.pos_bones)
                    == (e.frames, e.rot_bones, e.pos_bones))
                add("anim odd frame count", a.frames % 2)
    if packs.skels is not None:
        known = set(packs.anims._names()) if packs.anims else set()
        with open(packs.skels.dat_path, "rb") as f:
            for e in packs.skels.entries:
                data = packs.skels.read_entry(e, f)
                try:
                    sk = PackedSkeleton(data, e.name)
                except PackError as err:
                    if len(problems) < 8:
                        problems.append(str(err))
                    continue
                add("skel reads")
                add("skel round-trips", sk.to_bytes() == data)
                add("skel default slot filled", sk.slots[-1] is not None)
                for _i, s in sk.filled():
                    add("skel slot paths")
                    add("skel slot paths in pack.idx", _key(s.path) in known)
    c["problems"] = problems
    return c


def iter_skeletons(packs: Packs) -> Iterable[Tuple[PackEntry, PackedSkeleton]]:
    """Every skeleton in the pack, duplicates included, in index order."""
    if packs.skels is None:
        return
    with open(packs.skels.dat_path, "rb") as f:
        for e in packs.skels.entries:
            yield e, PackedSkeleton(packs.skels.read_entry(e, f), e.name)
