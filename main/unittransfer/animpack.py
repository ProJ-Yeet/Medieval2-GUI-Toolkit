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
every copy, :meth:`PackIndex.first` the first. An animation's copies are,
on every installed pack, the same animation at other scales, and a slot plays
the one at its skeleton's scale: see :func:`resolve_slot` (Phase 85).

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

A port (Phase 81)
-----------------
:func:`plan_port` says what bringing some skeletons and every animation their
slots name from one mod into another would do, reusing what the destination
already has byte for byte under any path or name; :func:`apply_port` appends
the rest to the destination's two ``.dat`` files, writes each ``.idx`` anew
and swaps it in, then updates the ``.dat`` header's count; and
:func:`undo_appended` truncates each ``.dat`` back to the length it had, having
first checked it is still the file that was appended to. The 352 MB ``.dat`` is
never copied or rewritten, and never backed up whole.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
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


def packs_for(data_dir) -> Tuple[Optional[Packs], str]:
    """The packs a mod plays: its own (``"mod"``), or vanilla's when it ships
    none (``"vanilla"``, found two folders up from ``mods/<mod>/data``), as the
    game does. ``(None, "")`` when neither can be found."""
    own = for_data(data_dir)
    if own is not None and own.skels is not None:
        return own, "mod"
    data = Path(data_dir)
    if data.parent.parent.name.lower() == "mods":
        van = for_data(data.parent.parent.parent / "data")
        if van is not None and van.skels is not None:
            return van, "vanilla"
    return None, ""


# ---------------------------------------------------------------------------
# a port: skeletons and their animations from one mod's packs into another's
# (Phase 81). Nothing is unpacked and nothing is rewritten: what the
# destination lacks is appended to the end of its .dat, its small .idx is
# written anew, and undo truncates the .dat back to the length it had.

#: How much of a .dat, back from the length it had, undo checks is unchanged.
TAIL_CHECK = 64 * 1024
#: Spare room a port asks for on top of what it writes.
SPACE_MARGIN = 32 * 1024 * 1024
#: The games that hold the packs open while they run.
GAME_EXES = ("M2EX.exe", "kingdoms.exe", "medieval2.exe")


def _sha(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


class ContentIndex:
    """A pack's entries by their bytes. Only entries of the same size as the
    bytes asked about are ever read and hashed, so a lookup reads a handful of
    entries, not the pack. Only the FIRST entry under a name is offered, since
    a path resolves to its first copy (the lookup this module makes; which one
    the game plays is Phase 82's question 5)."""

    def __init__(self, idx: PackIndex):
        self.idx = idx
        self.by_size: Dict[int, List[PackEntry]] = {}
        for e in idx.entries:
            if idx.first(e.name) is e:
                self.by_size.setdefault(e.size, []).append(e)
        self._hash: Dict[int, str] = {}

    def find(self, data: bytes, fid=None) -> Optional[PackEntry]:
        cands = self.by_size.get(len(data))
        if not cands:
            return None
        want = _sha(data)
        for e in cands:
            h = self._hash.get(e.offset)
            if h is None:
                h = self._hash[e.offset] = _sha(self.idx.read_entry(e, fid))
            if h == want:
                return e
        return None


_CONTENT: Dict[str, Tuple[tuple, "ContentIndex"]] = {}


def content_index(packs: Packs, kind: str) -> Optional[ContentIndex]:
    """``kind`` is ``"anims"`` or ``"skels"``; cached on the four files' stamp."""
    idx = getattr(packs, kind)
    if idx is None:
        return None
    key = os.path.normcase(str(idx.path.resolve()))
    stamp = _stamp(packs.dir)
    hit = _CONTENT.get(key)
    if hit is None or hit[0] != stamp:
        if len(_CONTENT) > 8:
            _CONTENT.clear()
        hit = _CONTENT[key] = (stamp, ContentIndex(idx))
    return hit[1]


class PortAnim:
    """One animation path a port touches. ``action`` is ``reuse`` (the
    destination has the path with these bytes), ``reuse_content`` (it has the
    bytes under ``dest_path``), ``shared`` (another animation of this port
    brings the same bytes, under ``dest_path``), ``append`` (added under its
    own path) or ``append_renamed`` (added under ``dest_path``, because the
    destination has the path with other bytes)."""

    __slots__ = ("path", "action", "dest_path", "size", "entry")

    def __init__(self, path, action, dest_path, size, entry):
        self.path, self.action, self.dest_path = path, action, dest_path
        self.size, self.entry = size, entry

    @property
    def appends(self) -> bool:
        return self.action in ("append", "append_renamed")

    def payload(self) -> dict:
        return {"path": self.path, "action": self.action, "dest_path": self.dest_path,
                "bytes": self.size}


class PortSkeleton:
    """One skeleton a port brings. ``action`` is ``reuse`` (the destination
    has it, byte for byte once its slot paths are rewritten), ``reuse_as``
    (it has those bytes under ``dest_name``), ``add`` (added under its own
    name) or ``rename`` (added as ``dest_name``, its name being taken by
    another skeleton there)."""

    __slots__ = ("name", "action", "dest_name", "size", "slots", "rewrites", "counts", "data")

    def __init__(self, name):
        self.name, self.action, self.dest_name = name, "", name
        self.size, self.slots, self.rewrites = 0, 0, 0
        self.counts: Dict[str, int] = {}
        self.data = b""

    @property
    def appends(self) -> bool:
        return self.action in ("add", "rename")

    def payload(self) -> dict:
        return {"name": self.name, "action": self.action, "dest_name": self.dest_name,
                "bytes": self.size, "slots": self.slots, "rewrites": self.rewrites,
                "animations": dict(self.counts)}


class PortPlan:
    """What :func:`plan_port` found: per skeleton and per animation, what
    happens, and the bytes each pack gains. ``renames`` maps a source
    skeleton's name to the one the destination plays it under, for the
    modeldb (Phase 83)."""

    def __init__(self, source_dir, dest_dir, tag: str):
        self.source_dir, self.dest_dir, self.tag = Path(source_dir), Path(dest_dir), tag
        self.source_packs = ""
        self.skeletons: List[PortSkeleton] = []
        self.anims: List[PortAnim] = []
        self.errors: List[str] = []
        self.notes: List[str] = []
        self.stamp: tuple = ()
        self.anim_dir: Optional[Path] = None

    @property
    def renames(self) -> Dict[str, str]:
        return {s.name: s.dest_name for s in self.skeletons if s.dest_name != s.name}

    def appended(self) -> Tuple[int, int]:
        """Bytes added to ``pack.dat`` and to ``skeletons.dat``."""
        return (sum(a.size for a in self.anims if a.appends),
                sum(s.size for s in self.skeletons if s.appends))

    def totals(self) -> dict:
        count = lambda rows, act: sum(1 for r in rows if r.action == act)
        a, s = self.appended()
        return {"skeletons": len(self.skeletons),
                **{f"skeletons {k}": count(self.skeletons, k) for k in ("reuse", "reuse_as", "add", "rename")},
                "animations": len(self.anims),
                **{f"animations {k}": count(self.anims, k)
                   for k in ("reuse", "reuse_content", "shared", "append", "append_renamed")},
                "slot paths rewritten": sum(x.rewrites for x in self.skeletons),
                "anim bytes appended": a, "skeleton bytes appended": s}

    @property
    def ok(self) -> bool:
        return not self.errors

    def payload(self) -> dict:
        return {"source": str(self.source_dir), "dest": str(self.dest_dir), "tag": self.tag,
                "source_packs": self.source_packs, "ok": self.ok, "errors": list(self.errors),
                "notes": list(self.notes), "totals": self.totals(), "renames": self.renames,
                "skeletons": [s.payload() for s in self.skeletons],
                "animations": [a.payload() for a in self.anims]}


def _tail_of(path: str) -> str:
    """A slot path from ``animations/`` on, or its file name."""
    p = path.replace("\\", "/")
    at = p.lower().find("animations/")
    return p[at + len("animations/"):] if at >= 0 else p.rsplit("/", 1)[-1]


def _unique(name: str, taken) -> str:
    """``name``, or ``name`` with ``_2``, ``_3``... before its extension,
    whichever ``taken`` (a set of lower-case keys) has not got."""
    if _key(name) not in taken:
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot or "/" in ext:
        stem, dot, ext = name, "", ""
    n = 2
    while True:
        cand = f"{stem}_{n}{dot}{ext}"
        if _key(cand) not in taken:
            return cand
        n += 1


def plan_port(source_dir, dest_dir, skeletons: Iterable[str], tag: str = "") -> PortPlan:
    """What bringing ``skeletons`` (and every animation their slots name)
    from the mod at ``source_dir`` into the one at ``dest_dir`` would do.
    Nothing is written.

    The source plays its own packs or vanilla's; the destination must have
    its own. For each animation, in the order the design fixes: the same path
    with the same bytes is reused; the same bytes under another path are
    reused and the slot pointed there; bytes this port already brings are
    shared; otherwise the animation is appended under its own path, or under
    ``mods/<dest>/data/animations/ported/<tag>/...`` when the destination has
    that path with other bytes. Then each skeleton, its slot paths rewritten:
    the same name with the same bytes is reused; the same bytes under another
    name are reused under that name; otherwise it is added, as
    ``<name>_<tag>`` when its name is taken."""
    plan = PortPlan(source_dir, dest_dir, tag)
    src, whose = packs_for(source_dir)
    plan.source_packs = whose
    dst = for_data(dest_dir)
    if src is None or src.anims is None or src.skels is None:
        plan.errors.append(f"{Path(source_dir)} has no animation packs, and vanilla's were not found")
        return plan
    if dst is None or dst.anims is None or dst.skels is None:
        plan.errors.append(f"{Path(dest_dir)} has no animation packs of its own (it plays vanilla's); "
                           "there is nothing to append to")
        return plan
    dest_mod = Path(dest_dir).parent.name
    if not tag:
        tag = "".join(ch for ch in Path(source_dir).parent.name.lower() if ch.isalnum())[:16] or "ported"
        plan.tag = tag
    plan.anim_dir, plan.stamp = dst.dir, _stamp(dst.dir)
    a_content, s_content = content_index(dst, "anims"), content_index(dst, "skels")
    taken_paths = set(dst.anims._names())
    taken_skels = set(dst.skels._names())
    decided: Dict[str, PortAnim] = {}        # source path key -> its row
    brought: Dict[str, PortAnim] = {}        # sha of appended bytes -> its row
    skel_brought: Dict[str, PortSkeleton] = {}
    seen = set()
    with open(src.anims.dat_path, "rb") as sfid, open(dst.anims.dat_path, "rb") as dfid, \
            open(dst.skels.dat_path, "rb") as dsfid:
        for name in skeletons:
            if not name or _key(name) in seen:
                continue
            seen.add(_key(name))
            row = PortSkeleton(name)
            sent = src.skels.first(name)
            if sent is None:
                plan.errors.append(f"the source's skeleton pack has no {name!r}")
                continue
            sk = PackedSkeleton(src.skels.read_entry(sent), sent.name)
            row.name = sent.name
            for _i, slot in sk.filled():
                row.slots += 1
                k = _key(slot.path)
                a = decided.get(k)
                if a is None:
                    e = src.anims.first(slot.path)
                    if e is None:
                        plan.errors.append(f"{sent.name}: pack.idx has no {slot.path!r}")
                        continue
                    data = src.anims.read_entry(e, sfid)
                    here = dst.anims.first(slot.path)
                    if here is not None and here.size == len(data) and \
                            dst.anims.read_entry(here, dfid) == data:
                        a = PortAnim(e.name, "reuse", here.name, len(data), e)
                    else:
                        hit = a_content.find(data, dfid)
                        if hit is not None:
                            a = PortAnim(e.name, "reuse_content", hit.name, len(data), e)
                        elif _sha(data) in brought:
                            a = PortAnim(e.name, "shared", brought[_sha(data)].dest_path, len(data), e)
                        elif here is None and k not in taken_paths:
                            a = PortAnim(e.name, "append", e.name, len(data), e)
                        else:
                            new = _unique(f"mods/{dest_mod}/data/animations/ported/{tag}/{_tail_of(e.name)}",
                                          taken_paths)
                            a = PortAnim(e.name, "append_renamed", new, len(data), e)
                        if a.appends:
                            taken_paths.add(_key(a.dest_path))
                            brought[_sha(data)] = a
                    decided[k] = a
                    plan.anims.append(a)
                row.counts[a.action] = row.counts.get(a.action, 0) + 1
                if a.dest_path != slot.path and _key(a.dest_path) != k:
                    slot.path = a.dest_path
                    row.rewrites += 1
            new = sk.to_bytes()
            row.data, row.size = new, len(new)
            here = dst.skels.first(sent.name)
            same = None
            if here is not None and here.size == len(new) and dst.skels.read_entry(here, dsfid) == new:
                row.action, row.dest_name = "reuse", here.name
            elif (same := s_content.find(new, dsfid)) is not None:
                row.action, row.dest_name = "reuse_as", same.name
            elif _sha(new) in skel_brought:
                row.action, row.dest_name = "reuse_as", skel_brought[_sha(new)].dest_name
            elif here is None and _key(sent.name) not in taken_skels:
                row.action = "add"
            else:
                row.action = "rename"
                row.dest_name = _unique(f"{sent.name}_{tag}", taken_skels)
            if row.appends:
                taken_skels.add(_key(row.dest_name))
                skel_brought[_sha(new)] = row
            plan.skeletons.append(row)
    if whose == "vanilla":
        plan.notes.append("the source ships no packs of its own, so it plays vanilla's and they are what is ported")
    return plan


# ---------------------------------------------------------------------------
# writing a port, and taking it back

def game_running() -> List[str]:
    """The game executables running now (Windows; elsewhere, none known)."""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                             timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    names = {line.split('","', 1)[0].strip('"').lower() for line in out.splitlines() if line.strip()}
    return [x for x in GAME_EXES if x.lower() in names]


def _tail_sha(fid, length: int) -> str:
    start = max(HEADER_SIZE, length - TAIL_CHECK)
    fid.seek(start)
    return _sha(fid.read(length - start))


def check_writable(plan: PortPlan) -> List[str]:
    """Why ``plan`` cannot be written now: the game running, the packs changed
    since it was planned, the space it needs, or a .dat another program holds."""
    why: List[str] = []
    running = game_running()
    if running:
        why.append(f"{', '.join(running)} is running and holds the packs open; close the game first")
    if plan.anim_dir is None:
        return why + ["nothing was planned"]
    if _stamp(plan.anim_dir) != plan.stamp:
        why.append("the destination's packs changed since this port was planned; plan it again")
    a, s = plan.appended()
    idx = sum((plan.anim_dir / n).stat().st_size for n in ("pack.idx", "skeletons.idx")
              if (plan.anim_dir / n).is_file())
    need = a + s + 2 * idx + SPACE_MARGIN
    try:
        free = shutil.disk_usage(plan.anim_dir).free
    except OSError:
        free = None
    if free is not None and free < need:
        why.append(f"it needs {need / 1e6:.0f} MB free on that drive and {free / 1e6:.0f} MB is")
    for n in ("pack.dat", "skeletons.dat"):
        try:
            with open(plan.anim_dir / n, "r+b"):
                pass
        except OSError as exc:
            why.append(f"{n} cannot be opened for writing: {exc.strerror or exc}")
    return why


def _append(idx: PackIndex, blobs: List[Tuple[PackEntry, bytes]], rel_dat: str) -> dict:
    """Append ``blobs`` to ``idx``'s .dat, write the new .idx beside it and
    swap it in, then put the new count in the .dat's header, in that order:
    killed midway, the process leaves at worst bytes nothing indexes, which
    the game never reads. An exception midway is put right here: the .dat is
    cut back and its header and the .idx rewritten as they were, and the
    exception goes on. Returns undo's record."""
    dat = idx.dat_path
    old_idx = idx.path.read_bytes()
    with open(dat, "r+b") as f:
        f.seek(0, os.SEEK_END)
        length = f.tell()
        f.seek(0)
        head_before = f.read(HEADER_SIZE)
        rec = {"rel": rel_dat, "length": length, "head_before": head_before.hex(),
               "tail_sha": _tail_sha(f, length)}
    tmp = idx.path.with_name(idx.path.name + ".tmp")
    try:
        with open(dat, "r+b") as f:
            f.seek(length)
            at = length
            for entry, data in blobs:
                entry.offset = at
                f.write(data)
                at += len(data)
            f.flush()
            os.fsync(f.fileno())
        new = PackIndex(idx.magic, list(idx.entries) + [e for e, _d in blobs], idx.version,
                        idx.version2, idx.filler, idx.path)
        tmp.write_bytes(new.to_bytes())
        os.replace(tmp, idx.path)
        head_after = new.header()
        with open(dat, "r+b") as f:
            f.write(head_after)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        _put_back(rec, dat, idx.path, old_idx)
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    rec["head_after"] = head_after.hex()
    rec["added"] = at - length
    return rec


def _put_back(rec: dict, dat: Path, idx_path: Path, old_idx: bytes) -> None:
    """A .dat cut back to ``rec``'s length with its old header, and its .idx."""
    with open(dat, "r+b") as f:
        f.truncate(rec["length"])
        f.seek(0)
        f.write(bytes.fromhex(rec["head_before"]))
        f.flush()
        os.fsync(f.fileno())
    idx_path.write_bytes(old_idx)


def apply_port(plan: PortPlan, backup_root) -> dict:
    """Write ``plan`` into the destination's packs. The two ``.idx`` files are
    backed up whole under ``backup_root``; the ``.dat`` files are only
    appended to, and the manifest's ``appended`` rows are what
    :func:`undo_appended` truncates them back with. Returns the manifest."""
    if not plan.ok:
        raise PackError("cannot port: " + "; ".join(plan.errors))
    why = check_writable(plan)
    if why:
        raise PackError("cannot port: " + "; ".join(why))
    src, _whose = packs_for(plan.source_dir)
    dst = open_packs(plan.anim_dir)
    data_dir = Path(plan.dest_dir)
    rel_dir = plan.anim_dir.relative_to(data_dir).as_posix()
    backup_root = Path(backup_root)
    manifest: Dict[str, list] = {"backed_up": [], "created": [], "appended": []}
    anims = [a for a in plan.anims if a.appends]
    skels = [s for s in plan.skeletons if s.appends]
    jobs = []
    if anims:
        with open(src.anims.dat_path, "rb") as sfid:
            jobs.append((dst.anims, "pack", [(PackEntry(a.dest_path, 0, a.size, a.entry.scale, a.entry.frames,
                                                         a.entry.rot_bones, a.entry.pos_bones),
                                               src.anims.read_entry(a.entry, sfid)) for a in anims]))
    if skels:
        jobs.append((dst.skels, "skeletons", [(PackEntry(s.dest_name, 0, s.size), s.data) for s in skels]))
    for idx, stem, _blobs in jobs:
        rel = f"{rel_dir}/{stem}.idx"
        b = backup_root / "data" / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(idx.path, b)
        manifest["backed_up"].append(rel)
    done = []
    try:
        for idx, stem, blobs in jobs:
            old = idx.path.read_bytes()
            manifest["appended"].append(_append(idx, blobs, f"{rel_dir}/{stem}.dat"))
            done.append((idx, old))
    except BaseException:
        # the pair that failed put itself back; the ones before it go back too
        for (idx, old), rec in zip(reversed(done), reversed(manifest["appended"])):
            _put_back(rec, idx.dat_path, idx.path, old)
        raise
    return manifest


def undo_appended(data_dir, rows: List[dict]) -> None:
    """Truncate each ``.dat`` a port appended to back to the length it had and
    put its old header back. Every row is checked before any file is
    touched, and nothing is done when one of them is no longer the file the
    port wrote (the game rebuilt it, or another tool wrote to it): its length,
    its header and the 64 KB before the old end must be as the port left
    them. The ``.idx`` files come back from their backups (``backed_up``)."""
    data = Path(data_dir)
    if rows and game_running():
        raise PackError(f"{', '.join(game_running())} is running and holds the packs open; "
                        "close the game before undoing")
    for r in rows:
        p = data / r["rel"]
        if not p.is_file():
            raise PackError(f"cannot undo: {r['rel']} is gone")
        size = p.stat().st_size
        want = r["length"] + r.get("added", 0)
        with open(p, "rb") as f:
            head = f.read(HEADER_SIZE)
            ok = size >= r["length"] and _tail_sha(f, r["length"]) == r["tail_sha"]
        if not ok or head.hex() != r["head_after"] or size != want:
            raise PackError(f"cannot undo: {r['rel']} is no longer the file this port appended to "
                            f"({size:,} bytes, {want:,} expected); the game or another tool has "
                            "rewritten it, so truncating it would cut away someone else's work")
    for r in rows:
        p = data / r["rel"]
        with open(p, "r+b") as f:
            f.truncate(r["length"])
            f.seek(0)
            f.write(bytes.fromhex(r["head_before"]))
            f.flush()
            os.fsync(f.fileno())


class KnownSkeletons:
    """The skeleton names a mod can play, looked up case-blind. ``source`` is
    ``"pack"`` when they are its own ``skeletons.idx`` (the packs are the
    truth), ``"modeldb"`` when it has no pack and they are every body and
    weapon skeleton its modeldb already names."""

    def __init__(self, names: Iterable[str], source: str):
        self.source = source
        self._names = {_key(n) for n in names if n}

    def __contains__(self, name) -> bool:
        return bool(name) and _key(name) in self._names

    def __len__(self) -> int:
        return len(self._names)

    @property
    def where(self) -> str:
        return "skeleton pack" if self.source == "pack" else "modeldb"


def known_skeletons(data_dir, modeldb=None) -> KnownSkeletons:
    """What a transfer holds a model's skeletons against (Phase 79)."""
    packs = for_data(data_dir)
    if packs is not None and packs.skels is not None:
        return KnownSkeletons((e.name for e in packs.skels.entries), "pack")
    names: List[str] = []
    for e in (modeldb.entries if modeldb is not None else ()):
        names += e.skeletons() + e.weapon_skeletons()
    return KnownSkeletons(names, "modeldb")


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


def port(plan: PortPlan, mod_name: str, mod_root, source_name: str = "") -> dict:
    """Write ``plan`` as one job in the transfer log, undoable like every
    other (``transfer.undo`` truncates the packs back). Returns the record."""
    import time

    from . import config
    from .logutil import file_op, log

    tid = config.new_transfer_id()
    manifest = apply_port(plan, config.backup_root_for(tid))
    for r in manifest["appended"]:
        file_op("APPEND", Path(plan.dest_dir) / r["rel"], f"+{r['added']} bytes (pack port)")
    t = plan.totals()
    summary = (f"animations from {source_name or plan.source_dir.parent.name} into {mod_name}: "
               f"{t['skeletons']} skeleton(s), {t['animations append'] + t['animations append_renamed']} "
               f"animation(s) appended, {(t['anim bytes appended'] + t['skeleton bytes appended']) / 1e6:.1f} MB")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "pack port",
        "source": source_name or plan.source_dir.parent.name, "source_root": str(plan.source_dir.parent),
        "dest": mod_name, "dest_root": str(mod_root),
        "unit_type": ", ".join(s.name for s in plan.skeletons), "resolved_type": "",
        "options": {"tag": plan.tag, "renames": plan.renames},
        "applied": True, "undone": False, "note": "", "summary": summary,
        "warnings": list(plan.notes), "manifest": manifest,
        "backup_root": str(config.backup_root_for(tid)),
    }
    config.append_log(rec)
    log.info("PORT   %s, id=%s", summary, tid)
    return rec


# ---------------------------------------------------------------------------
# which entry a slot plays, and a compacted pack (Phase 85)

def resolve_slot(idx: PackIndex, path: str, scale: float) -> Optional[PackEntry]:
    """The entry a skeleton at ``scale`` plays for the slot path ``path``.

    An animation is known by its path **and** its scale: DaC holds
    ``Knife_Default.cas`` four times, at 0.89, 1.0, 1.3 and 2.1, and each is a
    different entry to the game. A skeleton plays the first copy at exactly
    its own scale; when there is none, the first copy at the smallest scale,
    rescaled as it loads. So two copies of a path are duplicates only when
    their scales are the same, and then the later one is never played (Phase
    82's question 5: the first wins)."""
    hits = idx.find(path)
    if not hits:
        return None
    for h in hits:
        if h.scale == scale:
            return h
    low = min(h.scale for h in hits)
    return next(h for h in hits if h.scale == low)


#: Where a compaction keeps the four files it replaced, under the mod's own
#: folder (never inside ``data/``, so the game and the toolkit never read them)
COMPACT_DIR = ".ut_compacted"


def _write_pack(idx: PackIndex, keep: List[PackEntry], dat_out: Path, idx_out: Path) -> None:
    """``keep``'s entries, in the order given, copied out of ``idx``'s .dat
    into a new pair of files, touching end to end from byte 20."""
    new: List[PackEntry] = []
    at = HEADER_SIZE
    for e in keep:
        new.append(PackEntry(e.name, at, e.size, e.scale, e.frames, e.rot_bones, e.pos_bones))
        at += e.size
    out = PackIndex(idx.magic, new, idx.version, idx.version2, idx.filler, idx_out)
    with open(idx.dat_path, "rb") as src, open(dat_out, "wb") as dst:
        dst.write(out.header())
        for e in keep:
            dst.write(idx.read_entry(e, src))
        dst.flush()
        os.fsync(dst.fileno())
    idx_out.write_bytes(out.to_bytes())
    if dat_out.stat().st_size != at:
        raise PackError(f"{dat_out.name}: written {dat_out.stat().st_size:,} bytes, "
                        f"{at:,} expected")


def write_compacted(anim_dir, keep: Dict[str, List[PackEntry]], kept_dir) -> List[dict]:
    """Rewrite the packs in ``anim_dir`` holding only ``keep`` (``{"pack":
    [...], "skeletons": [...]}``; a stem left out is not touched). Each new
    pair is written beside the old one and read back, and only then are the
    old files moved into ``kept_dir`` and the new ones put in their place;
    any failure puts every file back. Returns undo's rows."""
    anim_dir, kept_dir = Path(anim_dir), Path(kept_dir)
    running = game_running()
    if running:
        raise PackError(f"{', '.join(running)} is running and holds the packs open; close the game first")
    packs = open_packs(anim_dir)
    jobs = []
    for stem, entries in keep.items():
        idx = packs.anims if stem == "pack" else packs.skels
        if idx is None:
            raise PackError(f"{anim_dir} has no {stem}.idx")
        jobs.append((stem, idx, entries))
    need = sum(HEADER_SIZE + sum(e.size for e in ents) for _s, _i, ents in jobs) + SPACE_MARGIN
    free = shutil.disk_usage(anim_dir).free
    if free < need:
        raise PackError(f"a compaction needs {need / 1e6:.0f} MB free beside the packs and "
                        f"{free / 1e6:.0f} MB is")
    made: List[Path] = []
    try:
        for stem, idx, entries in jobs:
            dat_new, idx_new = anim_dir / f"{stem}.dat.compact", anim_dir / f"{stem}.idx.compact"
            made += [dat_new, idx_new]
            _write_pack(idx, entries, dat_new, idx_new)
            back = PackIndex.read(idx_new)
            if [e.name for e in back.entries] != [e.name for e in entries]:
                raise PackError(f"{idx_new.name} does not read back as written")
    except BaseException:
        for p in made:
            try:
                p.unlink()
            except OSError:
                pass
        raise
    kept_dir.mkdir(parents=True, exist_ok=True)
    moved: List[Tuple[Path, Path]] = []
    rows: List[dict] = []
    try:
        for stem, _idx, _entries in jobs:
            for ext in (".idx", ".dat"):
                live = anim_dir / f"{stem}{ext}"
                os.replace(live, kept_dir / live.name)
                moved.append((kept_dir / live.name, live))
                os.replace(anim_dir / f"{stem}{ext}.compact", live)
                moved.append((live, anim_dir / f"{stem}{ext}.compact"))
            dat = anim_dir / f"{stem}.dat"
            size = dat.stat().st_size
            with open(dat, "rb") as f:
                head = f.read(HEADER_SIZE)
                tail = _tail_sha(f, size)
            rows.append({"stem": stem, "idx_sha": _sha((anim_dir / f"{stem}.idx").read_bytes()),
                         "dat_size": size, "dat_head": head.hex(), "dat_tail_sha": tail})
    except BaseException:
        for a, b in reversed(moved):
            try:
                os.replace(a, b)
            except OSError:
                pass
        for p in made:
            try:
                p.unlink()
            except OSError:
                pass
        raise
    return rows


def undo_compacted(anim_dir, kept_dir, rows: List[dict]) -> None:
    """Put back the packs a compaction replaced. Every file is checked first,
    and nothing is done when one is no longer the file the compaction wrote
    (the game rebuilt it, or another tool or a later port wrote to it)."""
    anim_dir, kept_dir = Path(anim_dir), Path(kept_dir)
    if rows and game_running():
        raise PackError(f"{', '.join(game_running())} is running and holds the packs open; "
                        "close the game before undoing")
    for r in rows:
        stem = r["stem"]
        idx, dat = anim_dir / f"{stem}.idx", anim_dir / f"{stem}.dat"
        for p in (kept_dir / idx.name, kept_dir / dat.name):
            if not p.is_file():
                raise PackError(f"cannot undo: the replaced {p.name} is gone from {kept_dir}")
        if not (idx.is_file() and dat.is_file()):
            raise PackError(f"cannot undo: {stem}.idx or {stem}.dat is gone")
        size = dat.stat().st_size
        with open(dat, "rb") as f:
            head = f.read(HEADER_SIZE)
            same = (size == r["dat_size"] and head.hex() == r["dat_head"]
                    and _tail_sha(f, size) == r["dat_tail_sha"]
                    and _sha(idx.read_bytes()) == r["idx_sha"])
        if not same:
            raise PackError(f"cannot undo: {stem}.dat is no longer the file the compaction wrote "
                            "(the game or another tool has written it since); undo the later "
                            "change first")
    for r in rows:
        for ext in (".idx", ".dat"):
            live = anim_dir / f"{r['stem']}{ext}"
            live.unlink()
            os.replace(kept_dir / live.name, live)
    for d in (kept_dir, kept_dir.parent):
        try:
            d.rmdir()
        except OSError:
            break
