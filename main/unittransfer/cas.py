r"""Decode M2TW strat-map models (``.cas``) to plain geometry the web UI can draw.

Phase 15 read the battle models and said, at the bottom of :mod:`unittransfer.mesh`,
that a ``.cas`` is not a variation on the ``.mesh`` format but a different one, and
handed it to the campaign map. This is that job. Nothing describes the format:
upstream's ``src/lib/casCodec.js`` documents a ``.cas`` as "uint32 numVerts, uint32
numFaces, no magic header", and every real file opens with a float, so its spec
matches no file that exists. The layout below was read out of the bytes of the 484
strat, terrain, effect and missile models installed here and checked against every
one of them: **472 decode**, and the twelve that do not each say why by name -
six are stamped version 2.19 or 2.23 and lay their header out differently, three
are Third Age Reforged settlements whose own chunk size points past the end of a
chunk, two are zero bytes long, and one is a material chunk one byte short of
what it claims. Not one of them is a model this reader read wrongly and kept.

What a ``.cas`` is
------------------
A **3ds-max scene export**, and it is laid out as a scene rather than as a model:
a frame rate and a table of key times, a node hierarchy with a parent table, then
a **chunk list**, and the meshes are one kind of chunk among several. So there is
no single vertex pool and no single object - a settlement is several named meshes
with a material each, all in one file.

The file, in order::

    float32  version - 3.2 for most, and 2.19 to 3.21 across the installed set
    uint32   38, uint32 9, uint32 0        - constant in every file measured
    float32  the scene's length in seconds
    uint32   1, uint32 0                   - constant
    22 bytes scene settings: two RGB triples (light and ambient) and a count
    uint32   node count, uint16 pad
    uint32   parent index, one per node after the root
    uint32   key count, then that many float32 key times, starting at 0.0
    per node: uint32 length, name with its NUL, then 5 uint32 (rotation and
              position key counts, their offsets into the key block, 0) and
              the bone's properties string - 25 bytes when it is empty
    the key block, when a node has keys: 16 bytes a rotation, 12 a position
    per node: 3 float32 - the node's pivot, relative to its parent
    then chunks to the end of the file:
        uint32 size (the whole chunk, header included), uint32 kind, payload

**The two RGB triples are why the header looks misaligned.** Six bytes of colour
in the middle of a run of 32-bit fields puts everything after them two bytes off
the grid, which is why the node count sits at 0x32 and not at 0x30, and why two
pad bytes follow it to put the parent table back on the grid. Nothing here is
guesswork: :data:`NODE_COUNT_AT` is where the count is in every file from 3.02
on, and a 2.x file is refused by version rather than read at the wrong offset.

**The parent table is one index per node except the root**, and it reads exactly
as a skeleton: on ``shadow_staff.cas`` it gives bone_pelvis the Scene Root,
bone_Rlowerleg the bone_RThigh, and the three cloak bones a chain of their own.
That is the check that the header is being read correctly rather than plausibly.

The chunk kinds
---------------
Five kinds turn up, and every file has all five - empty ones included, which is
what makes the chain checkable::

    1  static meshes      2  skinned meshes      5  materials
    3, 8, 10             always empty in every file measured

An empty mesh chunk is 16 or 18 bytes - the 8-byte header, a zero object count,
and the chunk's own trailer - so a static model still carries an empty *skinned*
chunk and a skinned model still carries an empty *static* one. That is the tell
for which of the two a model is, and it is also how the trailer lengths below
were pinned down.

An object, in either mesh chunk::

    uint32 length, name with its NUL
    uint32 length, 3ds-max user properties with their NUL - usually just the NUL
    37 bytes (static) or 28 bytes (skinned): a flag and the object's quaternion
    uint16 vertices, uint16 triangles, uint8 has UVs, uint8 has colours
    uint32 bone index per vertex          - skinned objects only
    float32 position, 3 per vertex
    float32 normal,   3 per vertex
    uint16  index triples
    uint32  the material this object is painted with, or -1 for none
    float32 u, v per vertex               - only when the UV flag is set
    uint32  colour per vertex             - only when the colour flag is set
    uint32  0

**The material index is the field that was nearly missed.** It sits between the
indices and the UVs, reads 0 in three quarters of all objects, and would have
passed for padding - except that a settlement has three meshes and three
materials, and reading it as padding leaves nothing saying which wall gets which
texture. On ``evil_men_huge_city.cas`` it hands its four objects materials 2, 1,
3 and 0, in that order, which is not an order anything else in the file would
have produced. 31 objects across the installed set write -1, which is a real
value: they have no material at all.

**A model is painted from ONE texture, named in the file.** This is the plain
difference from a ``.mesh``, which addresses a pair of sheets glued side by side
and needs its modeldb entry to say which two. A ``.cas`` material carries its own
path - ``textures\#banner_symbol_wales.tga`` - so a renderer needs the file and
nothing else. UVs are stored as the renderer wants them, and are not doubled.

What is measured and not decoded
--------------------------------
The 25 bytes after a node's name, the 37 or 28 bytes after an object's name
beyond the quaternion, and the per-material tail past the two colours. They are
constant or near-constant across every file here, they are counted so that a
file that disagrees is caught rather than mis-read, and they are reported in
:attr:`CasScene.notes` when they do.

**A chunk that goes wrong loses that chunk and not the file.** Chunk sizes are
absolute, so the next chunk's offset survives whatever happens inside this one,
and :func:`_read_meshes` uses that: a mesh it cannot read stops that chunk's
list, writes the sentence into the notes, and the walk carries on. That is what
makes ``se_fort.cas`` name its problem instead of dying on it: it opens with a
``CaozSceneCustomAttribNode``, a 3ds-max attribute holder rather than a mesh,
whose record runs to a length nothing in the file states, so the fort behind it
is lost - but the file still says so, in one sentence, with its three materials
and its node read. **This is the one place a note means geometry is missing**,
and it is why :func:`as_mesh` hands the notes on to the page.

The animation tracks are a separate job (:mod:`unittransfer.casanim`), but a
model can carry one: **Phase 75 found 53 of ROCSS's models, its diplomat among
them, with a baked animation's key block between the node records and the
pivots.** Read as a fixed 25 bytes a node, their pivots came out of the keys
and the chunk list read as a size in the billions; they now decode, and every
file that read before reads exactly as it did.

The pivots place a skinned model's vertices (:func:`bind_world`): drawn as
stored, a character is its pieces piled on the origin.
"""
from __future__ import annotations

import struct
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from unittransfer import mesh

#: Where the node count sits. Two RGB triples earlier in the header push every
#: field after them two bytes off the 32-bit grid; see the module docstring.
NODE_COUNT_AT = 0x32

#: Exporter versions seen across the installed set. A file outside this range is
#: refused by number rather than parsed into nonsense.
MIN_VERSION, MAX_VERSION = 2.0, 4.0

#: Bytes between an object's user-properties string and its vertex counts, by
#: the chunk it is in. The static form carries nine floats - the object's
#: quaternion is four of them - and the skinned form nine bytes fewer.
OBJECT_HEADER = {1: 37, 2: 28}

#: What a mesh chunk has after its last object, by chunk kind. The static
#: trailer lost three bytes before version 3.17; :func:`_trailer` picks.
CHUNK_TRAILER = {1: 6, 2: 4}
CHUNK_TRAILER_OLD = {1: 3, 2: 4}
TRAILER_VERSION = 3.17

STATIC_MESHES, SKINNED_MESHES, MATERIALS = 1, 2, 5

#: Chunk kinds that are empty in every file measured. Named so that a file that
#: puts something in one says so instead of being walked past.
ALWAYS_EMPTY = (3, 8, 10)

#: Bytes a key takes in the key block: a rotation is a quaternion, a position
#: three floats (the layout :mod:`unittransfer.casanim` reads).
ROT_BYTES, POS_BYTES = 16, 12

#: A material with this index is no material at all - 31 objects write it.
NO_MATERIAL = 0xFFFFFFFF

#: Bytes a material writes after its diffuse and specular colours: three more
#: float triples and a scalar. Measured, not decoded.
MATERIAL_TAIL = 29

#: A ceiling on any count read out of the file, so a corrupt uint32 cannot make
#: us allocate gigabytes before we notice it is nonsense.
MAX_COUNT = 4_000_000


class CasError(Exception):
    """A strat model could not be read. Carries a sentence, not a traceback."""


# ---------------------------------------------------------------------------
# result types


@dataclass
class CasMaterial:
    """One material: the texture a mesh is painted with, and its two colours."""

    name: str = ""
    #: the path as the file writes it, backslashes and all:
    #: ``textures\\#banner_symbol_wales.tga``. Some mods lead with a backslash.
    texture: str = ""
    diffuse: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    specular: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @property
    def texture_name(self) -> str:
        """Just the file name, for looking the texture up next to the model."""
        return self.texture.replace("\\", "/").rsplit("/", 1)[-1]


@dataclass
class CasObject:
    """One named mesh in the scene, with its own vertices and its own material."""

    name: str
    #: 3ds-max user properties, verbatim. Usually empty; ``barrel.cas`` writes
    #: 227 bytes of ``Mass = 0.000000`` and friends.
    properties: str = ""
    skinned: bool = False
    #: index into :attr:`CasScene.materials`, or ``None`` where the file says -1
    material: Optional[int] = None
    positions: array = field(default_factory=lambda: array("f"))
    normals: array = field(default_factory=lambda: array("f"))
    #: two per vertex, or empty when the object's UV flag is clear
    uvs: array = field(default_factory=lambda: array("f"))
    #: one per vertex, ``0xAABBGGRR`` as the file writes it, or empty
    colours: array = field(default_factory=lambda: array("I"))
    #: one node index per vertex on a skinned object, empty otherwise
    bones: array = field(default_factory=lambda: array("I"))
    indices: array = field(default_factory=lambda: array("H"))

    @property
    def vertices(self) -> int:
        return len(self.positions) // 3

    @property
    def triangles(self) -> int:
        return len(self.indices) // 3


@dataclass
class CasScene:
    """A decoded strat model: its nodes, its meshes and its materials."""

    source: str
    version: float = 0.0
    #: seconds the scene's animation runs for, from the header
    length: float = 0.0
    #: node names in file order, ``Scene Root`` first
    nodes: List[str] = field(default_factory=list)
    #: parent node index per node; the root's is ``-1``
    parents: List[int] = field(default_factory=list)
    #: each node's pivot, 3 floats per node
    pivots: array = field(default_factory=lambda: array("f"))
    #: the animation's key times in seconds, starting at 0.0
    key_times: array = field(default_factory=lambda: array("f"))
    #: bytes of baked animation keys between the node records and the pivots;
    #: 0 for the plain model every settlement is (Phase 75)
    baked_keys: int = 0
    objects: List[CasObject] = field(default_factory=list)
    materials: List[CasMaterial] = field(default_factory=list)
    #: anything read but not understood, said out loud rather than swallowed
    notes: List[str] = field(default_factory=list)

    @property
    def vertices(self) -> int:
        return sum(o.vertices for o in self.objects)

    @property
    def triangles(self) -> int:
        return sum(o.triangles for o in self.objects)

    def textures(self) -> List[str]:
        """Every texture the scene names, in material order, without repeats."""
        out: List[str] = []
        for m in self.materials:
            if m.texture and m.texture not in out:
                out.append(m.texture)
        return out

    def summary(self) -> str:
        return (f"{Path(self.source).name}: {len(self.objects)} meshes, "
                f"{self.vertices} vertices, {self.triangles} triangles, "
                f"{len(self.nodes)} nodes, {len(self.materials)} materials")


# ---------------------------------------------------------------------------
# the cursor


class _Reader:
    """A bounded cursor over the file, so a bad count is a sentence not a crash."""

    def __init__(self, data: bytes, source: str):
        self.d = data
        self.p = 0
        self.source = source

    def fail(self, why: str) -> "CasError":
        return CasError(f"{Path(self.source).name}: {why}")

    def need(self, n: int) -> None:
        if n < 0 or self.p + n > len(self.d):
            raise self.fail(f"ran off the end at byte {self.p:,} wanting {n:,} "
                            f"more of {len(self.d):,}")

    def u16(self) -> int:
        self.need(2)
        v, = struct.unpack_from("<H", self.d, self.p)
        self.p += 2
        return v

    def u32(self) -> int:
        self.need(4)
        v, = struct.unpack_from("<I", self.d, self.p)
        self.p += 4
        return v

    def f32(self) -> float:
        self.need(4)
        v, = struct.unpack_from("<f", self.d, self.p)
        self.p += 4
        return v

    def u8(self) -> int:
        self.need(1)
        v = self.d[self.p]
        self.p += 1
        return v

    def count(self, what: str) -> int:
        n = self.u32()
        if n > MAX_COUNT:
            raise self.fail(f"{what} says {n:,}, which is not a real count")
        return n

    def floats(self, n: int) -> array:
        self.need(n * 4)
        a = array("f")
        a.frombytes(self.d[self.p:self.p + n * 4])
        self.p += n * 4
        return a

    def u16s(self, n: int) -> array:
        self.need(n * 2)
        a = array("H")
        a.frombytes(self.d[self.p:self.p + n * 2])
        self.p += n * 2
        return a

    def u32s(self, n: int) -> array:
        self.need(n * 4)
        a = array("I")
        a.frombytes(self.d[self.p:self.p + n * 4])
        self.p += n * 4
        return a

    def text(self) -> str:
        """A length-prefixed string. The length counts the NUL it ends with."""
        n = self.count("a string length")
        if n == 0:
            return ""
        self.need(n)
        raw = self.d[self.p:self.p + n]
        self.p += n
        return raw.rstrip(b"\x00").decode("latin-1")

    def cstring(self) -> str:
        """A bare NUL-terminated string - how a material writes its two."""
        end = self.d.find(b"\x00", self.p)
        if end < 0:
            raise self.fail(f"a string starting at byte {self.p:,} never ends")
        out = self.d[self.p:end].decode("latin-1")
        self.p = end + 1
        return out

    def skip(self, n: int) -> bytes:
        self.need(n)
        out = self.d[self.p:self.p + n]
        self.p += n
        return out


# ---------------------------------------------------------------------------
# the header and the node hierarchy


def _read_header(r: _Reader, out: CasScene) -> None:
    """Version, scene length, node hierarchy and key times."""
    out.version = r.f32()
    if not MIN_VERSION <= out.version <= MAX_VERSION:
        raise r.fail(f"opens with {out.version:g}, which is not a .cas version "
                     f"(the installed set runs {MIN_VERSION:g} to {MAX_VERSION:g})")
    r.skip(8)                                   # 38 and 9, constant everywhere
    r.skip(4)                                   # 0, constant everywhere
    out.length = r.f32()
    r.p = NODE_COUNT_AT                         # over the two RGB triples
    nodes = r.count("the node count")
    r.skip(2)                                   # pad, back onto the 32-bit grid
    out.parents = [-1] + [r.u32() for _ in range(max(nodes - 1, 0))]
    keys = r.count("the key count")
    out.key_times = r.floats(keys)

    # Phase 75. A node's record after its name is what casanim reads in an
    # animation: rotation and position key counts, their offsets into one key
    # block, a zero, and the bone's properties string (the "25 bytes" when that
    # string is empty). A model with a baked animation - ROCSS's diplomat and
    # 79 more - fills them in, and the key block then sits between the node
    # records and the pivots. Read as a fixed 25 bytes, the pivots came out of
    # the keys and the chunk list after them read as a size in the billions.
    block = 0
    for _ in range(nodes):
        try:
            out.nodes.append(r.text())
        except CasError:
            # Six terrain models here - two bridges, two volcanoes, a river
            # wall - are stamped 2.23 and lay their header out differently.
            # Saying so by version beats a string length in the billions.
            raise r.fail(f"its header is version {out.version:g}, and the layout "
                         f"this reader knows starts at 3.02 - the node names are "
                         f"not where {out.version:g} puts them") from None
        nrot, npos, roff, poff, zero = struct.unpack_from("<5I", r.skip(20), 0)
        r.text()                                # the bone's properties
        if nrot > len(out.key_times) or npos > len(out.key_times) or zero:
            raise r.fail(f"node {out.nodes[-1]!r} has {nrot} rotation and {npos} "
                         f"position keys of the file's {len(out.key_times)}")
        block += nrot * ROT_BYTES + npos * POS_BYTES
    if block:
        r.skip(block)
        out.baked_keys = block
    out.pivots = r.floats(nodes * 3)

    bad = [p for p in out.parents[1:] if not 0 <= p < nodes]
    if bad:
        raise r.fail(f"the parent table points at nodes {bad[:4]} of {nodes} - "
                     f"the header is not being read where it really is")


# ---------------------------------------------------------------------------
# the chunks


def _trailer(version: float, kind: int) -> int:
    table = CHUNK_TRAILER if version >= TRAILER_VERSION else CHUNK_TRAILER_OLD
    return table[kind]


def _read_object(r: _Reader, kind: int, out: CasScene) -> CasObject:
    """One mesh: its name, its counts, and the arrays those counts size."""
    obj = CasObject(name=r.text(), skinned=(kind == SKINNED_MESHES))
    obj.properties = r.text()
    r.skip(OBJECT_HEADER[kind])
    verts = r.u16()
    faces = r.u16()
    has_uvs = r.u8()
    has_colours = r.u8()
    if has_uvs > 1 or has_colours > 1:
        raise r.fail(f"mesh {obj.name!r} says its UV flag is {has_uvs} and its "
                     f"colour flag is {has_colours}; both are 0 or 1 in every "
                     f"file measured, so the record is not where we think")

    if obj.skinned:
        obj.bones = r.u32s(verts)
    obj.positions = r.floats(verts * 3)
    obj.normals = r.floats(verts * 3)
    obj.indices = r.u16s(faces * 3)
    material = r.u32()
    obj.material = None if material == NO_MATERIAL else material
    if has_uvs:
        obj.uvs = r.floats(verts * 2)
    if has_colours:
        obj.colours = r.u32s(verts)
    r.skip(4)                                   # 0 between one mesh and the next

    if verts and obj.indices and max(obj.indices) >= verts:
        raise r.fail(f"mesh {obj.name!r} indexes vertex {max(obj.indices)} of "
                     f"{verts}")
    if obj.bones:
        stray = [b for b in obj.bones if b >= len(out.nodes)]
        if stray:
            out.notes.append(f"mesh {obj.name!r} weights vertices to node "
                             f"{stray[0]} of {len(out.nodes)}")
    return obj


def _read_meshes(r: _Reader, kind: int, end: int, out: CasScene) -> None:
    """Every mesh in one chunk, and what to do when one of them will not read.

    **A chunk that goes wrong loses that chunk and not the file.** Chunk sizes
    are absolute, so the next chunk's offset is known whatever happens inside
    this one: a mesh that will not parse stops this list, puts the decoder's
    own sentence in :attr:`CasScene.notes`, and the walk carries on at the
    chunk's end. Four settlement models in Third Age Reforged need that -
    ``se_fort`` and the three dwarven cities each open with a
    ``CaozSceneCustomAttribNode``, a 3ds-max scene-attribute holder rather than
    a mesh, whose record is a length nothing in the file states. Refusing the
    whole file over it would lose the meshes that did read and the materials
    after them, which is a worse answer than a named warning.
    """
    count = r.count("an object count")
    for i in range(count):
        try:
            out.objects.append(_read_object(r, kind, out))
        except CasError as exc:
            out.notes.append(f"{str(exc).split(': ', 1)[-1]} - mesh {i + 1} of "
                             f"{count} in the {_kind_name(kind)} chunk and every "
                             f"mesh after it was left out")
            r.p = end
            return
    want = _trailer(out.version, kind)
    if r.p + want != end:
        out.notes.append(f"the {_kind_name(kind)} chunk ends at byte {end:,} and "
                         f"its {count} meshes end at {r.p:,}, {end - r.p - want:+,} "
                         f"bytes out - what was read may not be the whole of it")
    r.p = end


def _kind_name(kind: int) -> str:
    return "skinned mesh" if kind == SKINNED_MESHES else "static mesh"


def _looks_like_path(text: str) -> bool:
    """Whether a material's second string is a file path and not raw bytes."""
    return (text.isprintable() and len(text) > 4
            and text.lower().rsplit(".", 1)[-1] in ("tga", "dds", "png", "bmp"))


def _read_materials(r: _Reader, end: int, out: CasScene) -> None:
    """The material list: a name, a texture path, and two colours each.

    **The leading flag is whether the material is named at all**, and it has to
    be read before the strings and not after. A material with the flag clear
    writes no name and no path - not two empty strings - and 31 objects across
    the installed set point at one. Reading two strings anyway eats the first
    two bytes of the diffuse colour and slides every material after it.

    The 29 bytes past the two colours are three more triples and a scalar, and
    are not decoded. They are skipped by length and the chunk is required to
    close on them, so a file that writes something else says so.
    """
    count = r.count("a material count")
    for _ in range(count):
        named = r.u32()
        mat = CasMaterial()
        if named:
            mat.name = r.cstring()
            mat.texture = r.cstring()
            if mat.texture and not _looks_like_path(mat.texture):
                # The 22 tree models in Reference/ EMBED their bitmap in this
                # chunk - one of them is 262,253 bytes for a 256x256 sheet -
                # instead of naming a file, and the strings around it do not
                # read as a name and a path. Their geometry is fine and their
                # texture is not a path at all, so it is dropped by name rather
                # than handed to a renderer that would go looking for it.
                out.notes.append(f"material {len(out.materials)} names "
                                 f"{mat.texture[:24]!r}, which is not a texture "
                                 f"path - this material's sheet is inside the "
                                 f"file rather than beside it")
                mat.texture = ""
        mat.diffuse = tuple(r.floats(4))        # type: ignore[assignment]
        mat.specular = tuple(r.floats(3))       # type: ignore[assignment]
        r.skip(MATERIAL_TAIL)
        out.materials.append(mat)
    if r.p != end:
        out.notes.append(f"the material chunk has {end - r.p:+,} bytes after its "
                         f"{count} materials that this reader does not read")
    r.p = end


def _read_chunks(r: _Reader, out: CasScene) -> None:
    while r.p < len(r.d):
        start = r.p
        if start + 8 > len(r.d):
            out.notes.append(f"{len(r.d) - start} bytes after the last chunk, "
                             f"too few to be another one")
            return
        size = r.u32()
        kind = r.u32()
        if size < 8 or start + size > len(r.d):
            raise r.fail(f"the chunk at byte {start:,} says it is {size:,} bytes "
                         f"of the {len(r.d):,} in the file")
        end = start + size
        if kind in (STATIC_MESHES, SKINNED_MESHES):
            _read_meshes(r, kind, end, out)
        elif kind == MATERIALS:
            _read_materials(r, end, out)
        else:
            if kind not in ALWAYS_EMPTY:
                out.notes.append(f"chunk kind {kind} at byte {start:,} is not one "
                                 f"of the five this format writes; {size:,} bytes "
                                 f"skipped")
            elif size > 20:
                out.notes.append(f"chunk kind {kind} is {size:,} bytes and is "
                                 f"empty in every file measured")
            r.p = end
        r.p = end


# ---------------------------------------------------------------------------
# the front door


def read_cas(path) -> CasScene:
    """Decode a strat-map model. Raises :class:`CasError` with a sentence."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CasError(f"{path.name} could not be read: {exc}") from exc
    return read_cas_bytes(data, str(path))


def read_cas_bytes(data: bytes, source: str) -> CasScene:
    """The same, from bytes already in hand - which is what the tests hold."""
    if mesh.probe_bytes(data) != "cas":
        found = mesh.probe_bytes(data)
        if found == "mesh":
            raise CasError(f"{Path(source).name} is a battle .mesh, not a "
                           f"strat-map .cas - unittransfer.mesh reads that one")
        raise CasError(f"{Path(source).name} is not a Medieval II model file "
                       f"(first bytes: {data[:8].hex(' ') or 'empty'})")
    out = CasScene(source=source)
    r = _Reader(data, source)
    _read_header(r, out)
    _read_chunks(r, out)
    for obj in out.objects:
        if obj.material is not None and obj.material >= len(out.materials):
            out.notes.append(f"mesh {obj.name!r} asks for material "
                             f"{obj.material} of {len(out.materials)}")
            obj.material = None
    return out


# ---------------------------------------------------------------------------
# what the viewer asks for


# ---------------------------------------------------------------------------
# the bind pose (Phase 75)
#
# A skinned mesh's vertices are stored around 0,0,0, each one relative to the
# bone it is weighted to, and "moved to position by the skeleton" (Wilddog,
# IWTE's author, 2026-09-23). Drawn as stored, a character is its pieces piled
# on the origin. Every node's pivot is its position relative to its parent, so
# the bone's place is its pivots chained from the Scene Root, and a vertex's is
# that plus its own. Measured on every character model installed: ROCSS's
# assassin goes from 0.66 x 0.69 of pile to a figure 1.85 tall with a 1.81 arm
# span, the T-pose the animations start from; all 66 skinned models in ROCSS
# and 195 in DaC carry pivots of their own. Every static model - the
# settlements, the resources, the banners - has all its pivots at zero and
# no bone per vertex, so nothing here moves one of them.


def bind_world(scene: CasScene, skeleton: Optional[CasScene] = None
               ) -> List[Tuple[float, float, float]]:
    """Each node's position, its pivots chained from the root.

    ``skeleton`` is another scene to take the pivots from, by node name, for a
    model whose own hierarchy carries none (a unit's skeleton is often in a
    ``.cas`` of its own); a node it does not name keeps the model's own.
    A parent table that loops is cut where it loops rather than followed.
    """
    n = len(scene.nodes)
    piv = [tuple(scene.pivots[3 * i:3 * i + 3]) if 3 * i + 2 < len(scene.pivots)
           else (0.0, 0.0, 0.0) for i in range(n)]
    if skeleton is not None:
        theirs = {name.lower(): i for i, name in enumerate(skeleton.nodes)}
        for i, name in enumerate(scene.nodes):
            j = theirs.get(name.lower())
            if j is not None and 3 * j + 2 < len(skeleton.pivots):
                piv[i] = tuple(skeleton.pivots[3 * j:3 * j + 3])
    world: List[Optional[Tuple[float, float, float]]] = [None] * n
    for start in range(n):
        chain, i = [], start
        while i >= 0 and world[i] is None and i not in chain:
            chain.append(i)
            i = scene.parents[i] if i < len(scene.parents) else -1
        base = world[i] if i >= 0 and world[i] is not None else (0.0, 0.0, 0.0)
        for j in reversed(chain):
            p = piv[j]
            base = (base[0] + p[0], base[1] + p[1], base[2] + p[2])
            world[j] = base
    return [w or (0.0, 0.0, 0.0) for w in world]


def has_pivots(scene: CasScene) -> bool:
    """Whether any node sits anywhere but the origin."""
    return any(abs(v) > 1e-6 for v in scene.pivots)


def is_skinned(scene: CasScene) -> bool:
    return any(o.skinned and o.bones for o in scene.objects)


def find_skeleton(path: Path, scene: CasScene) -> Optional[Tuple[Path, CasScene]]:
    """A ``.cas`` beside a skinned model with no pivots of its own that has the
    same bones and does carry them: the "actual skeleton in another .cas".

    Looked for in the model's own folder only, and taken only when it names
    every bone the model's vertices are weighted to."""
    used = {scene.nodes[b].lower() for o in scene.objects for b in set(o.bones)
            if b < len(scene.nodes)}
    folder = Path(path).parent
    try:
        others = sorted(p for p in folder.iterdir()
                        if p.suffix.lower() == ".cas" and p != Path(path))
    except OSError:
        return None
    for p in others:
        try:
            s = read_cas(p)
        except CasError:
            continue
        if has_pivots(s) and used <= {n.lower() for n in s.nodes}:
            return p, s
    return None


def posed_positions(obj: CasObject, world: Sequence[Tuple[float, float, float]]) -> array:
    """A skinned object's vertices moved to their bones; a static one as it is."""
    if not obj.skinned or not obj.bones:
        return obj.positions
    out = array("f", obj.positions)
    for i, b in enumerate(obj.bones):
        if b < len(world):
            x, y, z = world[b]
            out[3 * i] += x
            out[3 * i + 1] += y
            out[3 * i + 2] += z
    return out


def as_mesh(scene: CasScene, skeleton: Optional[CasScene] = None,
            pose: bool = True) -> mesh.MeshFile:
    """The scene as a :class:`~unittransfer.mesh.MeshFile`, so one viewer draws both.

    With ``pose`` (the default) a skinned object's vertices are placed by their
    bones (:func:`bind_world`, Phase 75), from ``skeleton`` when given; a
    static object is handed over as stored, which is every settlement.

    A ``.cas`` gives every mesh its own vertices and a ``.mesh`` gives all its
    groups one pool, so the objects are laid end to end and each one's indices
    are shifted by where its vertices landed. That is the only difference the
    page ever sees, and it is why :func:`unittransfer.mesh.geometry_payload`
    serves a settlement without knowing what a ``.cas`` is.

    An object with no UVs of its own gets zeros rather than being left out: the
    payload's UV array is one run over the whole pool, so a hole in it would
    slide every mesh after it onto the wrong corner of the texture.
    """
    out = mesh.MeshFile(source=scene.source, format="cas")
    out.notes = list(scene.notes)
    out.bones = list(scene.nodes)
    out.textures = scene.textures()
    any_uvs = any(o.uvs for o in scene.objects)
    world = bind_world(scene, skeleton) if pose and is_skinned(scene) else []
    if world and not has_pivots(scene) and skeleton is None:
        out.notes.append("its bones all sit at the origin and no skeleton was "
                         "found beside it, so it is drawn as stored, its pieces "
                         "on top of one another")
    base = 0
    for obj in scene.objects:
        out.positions.extend(posed_positions(obj, world) if world else obj.positions)
        out.normals.extend(obj.normals)
        if any_uvs:
            out.uvs.extend(obj.uvs if obj.uvs else array("f", [0.0]) * (obj.vertices * 2))
        texture = ""
        if obj.material is not None and obj.material < len(scene.materials):
            texture = scene.materials[obj.material].texture
        out.groups.append(mesh.MeshGroup(
            name=obj.name,
            texture_group=texture,
            indices=array("H", (i + base for i in obj.indices)),
            texture=texture,
            sheets="main",
        ))
        base += obj.vertices
    if base > 0xFFFF:
        raise CasError(f"{Path(scene.source).name}: its {len(scene.objects)} "
                       f"meshes come to {base:,} vertices, past what 16-bit "
                       f"indices can name")
    return out


#: Where a mod keeps the models the campaign map draws. ``residences`` is the
#: settlements and ``faction_variants`` under it the per-faction versions of
#: them; everything loose in ``models_strat`` is a character, a resource or a
#: faction banner.
STRAT_MODELS = "models_strat"


def list_models(data: Path) -> List[dict]:
    """Every strat model in a mod, as the picker needs it.

    Sorted so the settlements come first and the loose models after, because
    that is the order a map editor wants them: a settlement is the thing on the
    map, and a character is the thing standing next to it.
    """
    root = data / STRAT_MODELS
    if not root.is_dir():
        return []
    out = []
    for src in root.rglob("*"):
        if not src.is_file() or src.suffix.lower() != ".cas":
            continue
        rel = src.relative_to(data).as_posix()
        parts = src.relative_to(root).parts
        out.append({
            "rel": rel,
            "name": src.stem,
            "group": "/".join(parts[:-1]) or "characters and banners",
            "bytes": src.stat().st_size,
        })
    return sorted(out, key=lambda r: (r["group"] == "characters and banners",
                                      r["group"], r["name"].lower()))


def texture_path(model: Path, texture: str) -> Optional[Path]:
    """Where a material's texture really is, or ``None``.

    A ``.cas`` writes its texture the way 3ds-max saw it -
    ``textures\\NE_stone_castle.tga``, and some mods lead with a backslash -
    and it is relative to the folder the model is in, not to ``data/``. Three
    things then have to be forgiven, all of them measured on the installed set:

    * **case.** The castle names ``NE_stone_castle.tga`` and the folder holds
      ``ne_stone_castle.tga``. NTFS does not care and a zip on another machine
      would, so the lookup is case-insensitive by hand.
    * **the extension.** The game reads ``.tga`` or ``.dds`` and mods ship
      whichever; the vanilla strat folder holds both for nearly every texture.
      A named ``.tga`` that is not there is tried as ``.dds`` and as
      ``.tga.dds``, which is how the packer leaves them.
    * **nothing at all**, which is not an error: 31 objects have no material.

    And one thing has to be *preferred*, which is Phase 29's root. A mod's
    packer converts each ``.tga`` to a DDS named ``<name>.tga.dds`` and leaves
    the original truncated to nothing rather than deleting it, so the named
    file is there, is first in the candidate list, and is zero bytes. Measured
    on both installed mods: Divide and Conquer has 1,172 of them under
    ``data/models_strat`` and Third Age Reforged two, and 1,171 of the 1,174
    have their real DDS beside them under exactly that name. The three that do
    not are all named ``XXXX...``, the modders' own mark for a file they have
    switched off.

    So an empty candidate never wins over a later one that has bytes in it -
    taking the stub is how the strat viewer ended up drawing a bare cube. An
    empty file is still returned when it is the ONLY thing there, because
    "present and unreadable" is a fault the layers above now report and
    "absent" is not, and collapsing the two is the mistake this phase undid.
    """
    if not texture:
        return None
    rel = texture.replace("\\", "/").lstrip("/")
    folder = model.parent
    target = folder / rel
    wanted = [target.name, target.stem + ".dds", target.name + ".dds"]
    here = target.parent
    if not here.is_dir():
        return None
    have = {p.name.lower(): p for p in here.iterdir() if p.is_file()}
    empty = None
    for name in wanted:
        hit = have.get(name.lower())
        if hit is None:
            continue
        if _has_bytes(hit):
            return hit
        if empty is None:
            empty = hit
    return empty


def _has_bytes(path: Path) -> bool:
    """Is there anything in this file at all?

    One stat, and it is the whole of the stub test. Nothing tries to decode
    here: this module's errand is to say which file a material means, and
    whether the bytes in it are a picture is :mod:`unittransfer.icons`'s
    question, asked once and cached.
    """
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def scene_view(scene: CasScene) -> dict:
    """What the picker shows before anything is drawn: the meshes and textures."""
    return {
        "source": Path(scene.source).name,
        # The viewer's picker is shaped for a modeldb entry - a list of LODs and
        # a list of skins - and a .cas has neither: one model at one detail,
        # naming its own textures. The two lists are here and empty so the panel
        # that reads them draws nothing rather than throwing, and the strat
        # branch of v3Render hides both selects.
        "lods": [],
        "skins": [],
        "version": round(scene.version, 3),
        "length": round(scene.length, 4),
        "nodes": scene.nodes,
        "parents": scene.parents,
        "keys": len(scene.key_times),
        "vertices": scene.vertices,
        "triangles": scene.triangles,
        "meshes": [{
            "name": o.name,
            "vertices": o.vertices,
            "triangles": o.triangles,
            "skinned": o.skinned,
            "uvs": bool(o.uvs),
            "colours": bool(o.colours),
            "material": o.material,
            "texture": (scene.materials[o.material].texture
                        if o.material is not None and o.material < len(scene.materials)
                        else ""),
            "properties": o.properties,
        } for o in scene.objects],
        "materials": [{"name": m.name, "texture": m.texture,
                       "diffuse": list(m.diffuse), "specular": list(m.specular)}
                      for m in scene.materials],
        "skinned": any(o.skinned for o in scene.objects),
        #: Phase 75: how the viewer places it - "bones" (its own pivots),
        #: "skeleton" (another .cas's, see pose_of), "stored" (no bones to place
        #: it by, or none worth the name), or "static" (a settlement)
        "pose": "stored" if is_skinned(scene) and not has_pivots(scene)
                else "bones" if is_skinned(scene) else "static",
        "notes": scene.notes,
    }


def pose_of(path: Path, scene: CasScene) -> Tuple[Optional[CasScene], str]:
    """``(skeleton or None, the sentence saying which)`` for the viewer.

    A skinned model with pivots of its own is placed by them; one without is
    placed by a skeleton ``.cas`` beside it when one names its bones
    (:func:`find_skeleton`), and drawn as stored otherwise."""
    if not is_skinned(scene) or has_pivots(scene):
        return None, ""
    got = find_skeleton(path, scene)
    if got is None:
        return None, ""
    return got[1], (f"placed by the skeleton in {got[0].name}, since its own bones "
                    f"all sit at the origin")
