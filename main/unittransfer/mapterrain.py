"""The map drawn with the game's own ground textures (23a, D7 and T1).

Every other layer on the map screen is a picture of *values*: a colour stands
for a region, a climate, a ground type, and the whole screen is built on reading
that colour back exactly. This module is the one place that turns two of those
value layers into a picture of the **place** - the aerial-map terrain the player
sees when the campaign loads - by doing what the engine does:

    for each tile:  climate colour -> climate
                    ground colour  -> ground type
                    (climate, ground) -> one .tga in
                                         data/terrain/aerial_map/ground_types
                    draw that texture there

The rules are TWMapReader's, which is the only one of the four references that
implements this at all, and they are taken as they stand:

* **A texture that cannot be found is drawn pink and reported.** Not skipped,
  not rounded to a neighbour, not filled with the average of something else.
  It is this project's "a rule with no evidence reports nothing" applied to a
  picture, and somebody else arrived at it independently, which is the strongest
  argument in the reference audit for taking his version over Demir's.
  ``MISSING_RGB`` is his magenta, and :func:`plan` is what counts and names
  them so the ✓ Check panel can say which file and which tile.
* **A climate the map uses and ``descr_climates.txt`` does not declare falls
  back to the ``default`` block**, rather than leaving a hole. The engine has a
  default climate and so does the file.
* **Every climate inherits the ``default`` block** for any ground type it does
  not name itself.
* **Wilderness is drawn as fertility_low.** It has a colour in
  ``map_ground_types.tga`` and no entry in
  ``descr_aerial_map_ground_types.txt``; this is the substitution TWMapReader
  found and it is why wilderness is not a hole in every mod.
* **A missing winter column falls back to the summer one**, and so does a whole
  climate that ``descr_climates.txt`` does not mark ``winter``.
* **A texture spans ``TEXTURE_SPAN`` tiles**, whatever its own size: his
  ``SCALING = 1f/32``, so a 512-pixel texture covers 32 tiles of map at its own
  32-pixel-per-tile scale and repeats. The repeat is anchored to the map's
  origin rather than to each tile, so neighbouring tiles of one texture join up
  instead of showing 248,000 copies of the same square.

Two ground types in the file can never match a tile and are parsed anyway:
``cultivated_low/medium/high`` and ``scorched`` are states the engine puts a
tile into while a campaign runs - farmland a settlement has grown, land an army
has burned - and no colour in ``map_ground_types.tga`` says either. They are
kept because they are in the file and a reader that drops what it does not use
is a reader nobody can write with later.

The sea is not textured here, and that is not a gap: the engine draws it from
``terrain/aerial_map/sea`` and ``water.tga`` by a different mechanism entirely,
so a flat :data:`SEA_RGB` is the honest thing to put where we do not know.
TWMapReader does the same, and its sea is the one before ours.

**Cost, and the rule it has to meet.** 16c's rule is that the composite is
built once and that a pan or a zoom never rebuilds it. Measured on DaC's
510x487 map with 50 distinct textures on it:

    the two layers, decoded and sampled per tile      30 ms
    climate and ground index, both, exactly           10 ms   (:func:`_index`)
    the pair table and the gaps, in Pillow's C          5 ms
    50 textures read, scaled and tiled into place     620 ms
    PNG, 2040x1948                                    230 ms  (3.1 MB)

The first three are :func:`plan`, which is all the ✓ Check panel's rule needs
and is about 130 ms cold; the last two are the picture, and they are behind
:meth:`IconCache.cached_png`'s disk cache. The browser fetches that picture once
and blits it: nothing here is on the interaction path, and nothing here runs
again for a pan, a zoom or a stroke on another layer.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageChops

from . import campmap, mapvocab
from .campmap import CampaignMap, MapError
from .maptga import TgaError, probe, read
from .mapvocab import Rgb

#: Plain 8-bit game data, as everywhere else
ENCODING = "latin-1"

#: Which texture goes with which (climate, ground type) pair.
AERIAL_REL = "descr_aerial_map_ground_types.txt"
#: And where the textures themselves live, relative to the mod's ``data/``.
TEXTURE_DIR_REL = "terrain/aerial_map/ground_types"

#: The block every climate inherits from, and the one an undeclared climate
#: colour is drawn with. It is a real ``climate default`` block in the file,
#: not a name this module invented.
DEFAULT_CLIMATE = "default"

#: Composite pixels per tile. Four, and the reason is the texture scale below:
#: at four, a 512-pixel texture becomes 64 pixels and covers a whole number of
#: tiles, so the repeat lands on a tile boundary and never drifts. It is also
#: the zoom at which a tile is already a visible block on screen, so the detail
#: is there when it can be seen and not paid for when it cannot: DaC comes out
#: 2040x1948 and 3.1 MB, against 6.2 megapixels at TWMapReader's five.
SCALE = 4

#: How many tiles of map one texture covers, at its own size. TWMapReader's
#: ``TextureImage.SCALING = 1f/32``: the texture is drawn at 32 of its own
#: pixels per tile, so a 512-pixel one spans 16 tiles and then repeats.
TEXTURE_SPAN = 32

#: TWMapReader's magenta, under the whole composite, so anything not drawn is
#: this and is obvious. Never a colour any texture is.
MISSING_RGB: Rgb = (255, 0, 255)

#: What a sea tile is filled with. Flat on purpose: the aerial ground-type file
#: has no sea entry, and the engine's sea comes from another folder and another
#: mechanism, so this is a placeholder that says so rather than a guess dressed
#: up as terrain.
SEA_RGB: Rgb = (26, 51, 92)

#: The two texture columns, in the order the file writes them.
SEASONS = ("summer", "winter")

#: A ground type in the file with no colour in ``map_ground_types.tga``: a
#: state the engine puts a tile into while a campaign runs, never something the
#: map declares. Parsed, kept, and never matched against a tile.
RUNTIME_GROUND = ("cultivated_low", "cultivated_medium", "cultivated_high",
                  "scorched")

#: The substitution TWMapReader found: ``map_ground_types.tga`` has a colour for
#: wilderness and ``descr_aerial_map_ground_types.txt`` has no line for it, so
#: the engine draws it with fertility_low's texture. Without this, every
#: wilderness tile in every mod would be a hole.
SUBSTITUTE: Dict[str, str] = {"wilderness": "fertility_low"}

#: Ground types that are water. They have no texture entry and, unlike
#: wilderness, they must not borrow one: a sea tile is filled with
#: :data:`SEA_RGB` before any texture is looked up. A tile with one of these
#: ground types that the *heights* layer calls land is therefore drawn by
#: nothing, and :func:`plan` says so in those words rather than in the file's.
SEA_GROUND = frozenset(mapvocab.SEA_GROUND)


class TerrainError(ValueError):
    """The composite cannot be built, with the file that stops it named."""


# ---------------------------------------------------------------------------
# descr_aerial_map_ground_types.txt


_CLIMATE = re.compile(r"^climate\s+(\S+)", re.I)


def parse(text: str) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """``{climate: {ground type: (summer tga, winter tga)}}``, as written.

    No inheritance and no substitution: this is the file, and
    :class:`Vocabulary` is the file plus the engine's rules about it. Keeping
    them apart is what lets a test say which of the two a wrong texture came
    from.

    A line is ``<ground type> <summer.tga> [<winter.tga>]``, separated by tabs
    in every mod and by whatever the modder typed in principle, so it is split
    on whitespace. A second filename is optional and everything after it is
    ignored; a line whose second field is not a ``.tga`` is not an entry.
    """
    out: Dict[str, Dict[str, Tuple[str, str]]] = {}
    block: Optional[Dict[str, Tuple[str, str]]] = None
    for line in text.splitlines():
        s = line.split(";", 1)[0].strip()
        if not s:
            continue
        m = _CLIMATE.match(s)
        if m:
            block = out.setdefault(m.group(1), {})
            continue
        if s.startswith("}"):
            block = None
            continue
        if block is None:
            continue
        parts = s.split()
        if len(parts) < 2 or not parts[1].lower().endswith(".tga"):
            continue
        winter = (parts[2] if len(parts) > 2 and parts[2].lower().endswith(".tga")
                  else parts[1])
        block[parts[0]] = (parts[1], winter)
    return out


@dataclass
class Vocabulary:
    """The file, plus the four rules the engine reads it by.

    ``blocks`` is what :func:`parse` returned. ``climates`` is
    ``descr_climates.txt``'s list, which is where the winter flag lives and
    where a colour becomes a climate name. :meth:`texture` is the only thing
    that answers a tile, and it is where inheritance, substitution and the two
    winter fallbacks are applied - once, in one place, rather than at each of
    the three call sites that want a texture name.
    """

    #: relative to the mod's ``data/``, for a finding to name
    rel: str = AERIAL_REL
    present: bool = False
    problem: str = ""
    blocks: Dict[str, Dict[str, Tuple[str, str]]] = field(default_factory=dict)
    climates: List[dict] = field(default_factory=list)
    #: texture folder, absolute
    textures: Optional[Path] = None

    @property
    def by_key(self) -> Dict[int, dict]:
        """Climate by packed colour - the lookup one per tile goes through."""
        return {mapvocab.key(c["rgb"]): c for c in self.climates if c["rgb"]}

    def has_winter(self, climate: str) -> bool:
        """Whether this climate has a winter of its own.

        ``descr_climates.txt``'s ``winter`` line, and TWMapReader's rule that a
        climate without one is drawn in its summer textures all year. The
        ``default`` block is not a declared climate and is treated as having
        one, because it writes two columns.
        """
        if climate == DEFAULT_CLIMATE:
            return True
        for c in self.climates:
            if c["code"] == climate:
                return bool(c.get("winter"))
        return False

    def texture(self, climate: str, ground: str, season: str = "summer") -> str:
        """The texture one tile is drawn with, or ``""`` if the file names none.

        In order: the ground type's own entry in this climate's block, then the
        same entry in ``default``'s, which is the inheritance every climate gets
        for anything it leaves out. Wilderness asks for fertility_low's entry
        first (:data:`SUBSTITUTE`). Winter falls back to summer twice over - a
        line with one filename, and a climate with no winter at all.
        """
        ground = SUBSTITUTE.get(ground, ground)
        pair = (self.blocks.get(climate) or {}).get(ground)
        if pair is None:
            pair = (self.blocks.get(DEFAULT_CLIMATE) or {}).get(ground)
        if pair is None:
            return ""
        if season == "winter" and self.has_winter(climate):
            return pair[1]
        return pair[0]

    def payload(self) -> dict:
        return {"file": self.rel, "present": self.present,
                "problem": self.problem,
                "climates": [c["code"] for c in self.climates],
                "blocks": sorted(self.blocks),
                "folder": TEXTURE_DIR_REL}


def texture_dir(mod) -> Path:
    return Path(mod.data) / TEXTURE_DIR_REL


def read_vocabulary(mod) -> Vocabulary:
    """The mod's aerial ground types, never raising.

    A mod without the file comes back ``present: False`` with the reason, and
    every caller turns itself off rather than reporting a map with no textures
    as a map whose textures are all missing. That is the same ruling
    ``climate.unknown`` was written for: the game's own copy is inside a
    ``.pack``, so "not on disk" is the ordinary state of a mod that changed
    nothing about its terrain.
    """
    v = Vocabulary(climates=mapvocab.climates(mod), textures=texture_dir(mod))
    path = Path(mod.data) / AERIAL_REL
    if not path.is_file():
        v.problem = (f"{AERIAL_REL} is not in this mod's data folder, so which "
                     f"texture goes with which climate and ground type is not "
                     f"known here. The game keeps its own copy inside a .pack.")
        return v
    try:
        v.blocks = parse(path.read_text(encoding=ENCODING))
    except OSError as exc:
        v.problem = f"{AERIAL_REL} could not be read: {exc}"
        return v
    if not v.blocks:
        v.problem = f"{AERIAL_REL} declares no climate block"
        return v
    v.present = True
    return v


# ---------------------------------------------------------------------------
# which texture every tile wants


@dataclass
class Plan:
    """Which texture each tile asks for, before a single pixel is drawn.

    The expensive half of this module is the drawing, and none of the reporting
    needs it: the ✓ Check panel wants to know which textures are missing and
    where, which is this and nothing more. So the two are separate calls, the
    validator pays about 150 ms rather than a second, and the composite and the
    findings cannot disagree because they are built from the same object.
    """

    width: int = 0
    height: int = 0
    season: str = "summer"
    #: one byte per tile: 0 for "no texture", otherwise 1-based into :attr:`names`
    slots: Optional[Image.Image] = None
    #: the texture filenames, in slot order
    names: List[str] = field(default_factory=list)
    #: tiles per slot, same order
    counts: List[int] = field(default_factory=list)
    #: 1 where the tile is sea and no texture is drawn at all
    sea: bytes = b""
    #: one row per reason a tile has no texture - see :func:`plan`
    gaps: List[dict] = field(default_factory=list)
    #: :func:`signature`'s answer for the pixels this plan was built from, and
    #: the picture's disk-cache key. One key for both, so a composite can never
    #: be served for a state of the map the plan was not measured on.
    key: str = ""
    vocab: Vocabulary = field(default_factory=Vocabulary)

    @property
    def pink(self) -> int:
        """Tiles that will come out :data:`MISSING_RGB`."""
        return sum(g["tiles"] for g in self.gaps)

    @property
    def used(self) -> int:
        """Distinct textures a tile actually asks for.

        Not ``len(names)``: the pair table is built over every climate and every
        ground type, and a mod declares combinations its map never uses. What
        the panel should say is how many pictures this map is made of.
        """
        return sum(1 for n in self.counts if n)

    def payload(self) -> dict:
        return {"season": self.season,
                "textures": self.used,
                "declared": len(self.names),
                "tiles": self.width * self.height,
                "sea_tiles": sum(self.sea),
                "pink_tiles": self.pink,
                "gaps": self.gaps,
                "vocabulary": self.vocab.payload()}


def _index_slow(img: Image.Image, lut: Dict[bytes, int]) -> bytes:
    """One byte per tile, a tile at a time. :func:`campmap._label_image`'s idiom.

    Exact, and the reference the fast path below is measured against: an
    approximate match here would put a tile in the wrong climate, and the whole
    point of naming a colour is that it is the colour that was written.
    """
    raw = img.tobytes()
    return bytes(map(lambda k: lut.get(k, 0),
                     (raw[o:o + 3] for o in range(0, len(raw), 3))))


def _rank(values) -> Tuple[List[int], int]:
    """A 256-entry table giving each of ``values`` a rank from 1, and the count.

    Rank 0 is kept for "not one of them", which is what makes the packing below
    collision-proof rather than merely unlikely.
    """
    order = sorted(set(values))
    table = [0] * 256
    for i, v in enumerate(order):
        table[v] = i + 1
    return table, len(order)


def _index(img: Image.Image, lut: Dict[bytes, int]) -> bytes:
    """One byte per tile: ``lut``'s value for that pixel, or 0 for a miss.

    In Pillow's C, in seven operations, and **exactly** - which is the whole
    difficulty, because the obvious way of doing a colour lookup in C is
    ``Image.quantize`` with a fixed palette and that is approximate. 16a already
    measured what approximate costs on this map: 1,320 of DaC's tiles on the
    wrong region with every colour present in the palette.

    A layer of values has few colours - twelve on both of DaC's - so each band
    can be replaced by the *rank* of its value among the ones that occur, and
    the three ranks packed into one byte. It does not fit in one step: the
    climates layer has 10 x 12 x 12 possible rank triples, which is 1,859. So it
    is two, and the middle step is the trick - the red and green ranks are packed
    together and then ranked again over the pairs that really occur, of which
    there are only ever as many as there are colours::

        rg    = rank(r) * (ng + 1) + rank(g)          one add, two points
        pair  = rank of that among the pairs that occur, 0 for any other
        code  = pair * (nb + 1) + rank(b)             one add, two points
        index = lut's value for the colour with that code, 0 for any other

    Rank 0 means "not a value this layer uses", and every known colour's ranks
    are 1 or more, so a pixel that misses in any band lands on a code no known
    colour has: 20 ms over both of DaC's layers rather than 160, and the same
    bytes. Anything that will not pack falls back to :func:`_index_slow`, and
    ``UT_TERRAIN_SLOW`` forces that path so the suite can compare the two.
    """
    img = img.convert("RGB")
    census = img.getcolors(1 << 16)
    if census is None or os.environ.get("UT_TERRAIN_SLOW"):
        # more colours than a census can hold is a picture rather than a layer
        # of values; mapcheck reports that itself, and this still answers
        return _index_slow(img, lut)
    colours = [c for _, c in census]
    lut_r, nr = _rank(c[0] for c in colours)
    lut_g, ng = _rank(c[1] for c in colours)
    lut_b, nb = _rank(c[2] for c in colours)
    # each bound is checked before the step that would overflow it, not after:
    # a packed value over 255 does not merely give a wrong answer, it walks off
    # the end of the 256-entry table it is about to index
    if nr * (ng + 1) + ng > 255:
        return _index_slow(img, lut)
    pairs, npair = _rank(lut_r[c[0]] * (ng + 1) + lut_g[c[1]] for c in colours)
    if npair * (nb + 1) + nb > 255:
        return _index_slow(img, lut)

    r, g, b = img.split()
    rg = ImageChops.add(r.point([v * (ng + 1) for v in lut_r]), g.point(lut_g))
    code = ImageChops.add(rg.point([v * (nb + 1) for v in pairs]), b.point(lut_b))
    table = [0] * 256
    for c in colours:
        hit = lut.get(bytes(c))
        if hit:
            table[pairs[lut_r[c[0]] * (ng + 1) + lut_g[c[1]]] * (nb + 1)
                  + lut_b[c[2]]] = hit
    return code.point(table).tobytes()


def _first_tile(data: bytes, width: int, value: int) -> Optional[Tuple[int, int]]:
    i = data.find(bytes([value]))
    return (i % width, i // width) if i >= 0 else None


#: One plan per (mod, campaign, season), while nothing it was built from has
#: changed. Three callers want the same object within a second of each other -
#: the panel's facts, the picture, and the ✓ Check panel's rule - and the pass
#: that builds it is the only expensive thing that is not the drawing.
_PLANS: Dict[Tuple[str, str, str], Tuple[str, "Plan"]] = {}


def plan(mod, cm: CampaignMap, campaign: str = "", season: str = "summer") -> Plan:
    """Every tile's texture, and every reason a tile has none. Kept per map.

    A gap row is one of three things, and all three come out pink:

    ``no entry``  the file names no texture for this climate and ground type,
                  ``default`` included. The live case is the handful of tiles
                  whose height says land and whose ground type says sea - DaC
                  has fifteen - because there is no sea texture to fall back to.
    ``no file``   the file names one and it is not in the texture folder. This
                  is TWMapReader's case, the one the pink rule was written for.
    ``unreadable`` it is there and it will not decode.

    The layers are resolved per file rather than per map, because 22c's rule is
    that a campaign is drawn on its own copies: a campaign shipping only
    ``map_climates.tga`` is still drawn in its own climates.

    Kept in :data:`_PLANS` under :func:`signature`, so the panel, the picture
    and the validator's rule build it once between them. The layers are read
    *before* the key is taken, deliberately: the key is a hash of their pixels,
    so an unsaved stroke on the ground types is a different plan and a different
    picture. Decoding is cached on the map object, so paying for the read on a
    cache hit costs the hash and nothing else.
    """
    if season not in SEASONS:
        raise TerrainError(f"no such season {season!r} - it is one of "
                           f"{', '.join(SEASONS)}")
    v = read_vocabulary(mod)
    p = Plan(width=cm.terrain.width, height=cm.terrain.height, season=season,
             vocab=v)
    if not v.present:
        raise TerrainError(v.problem)

    try:
        ground = campmap.layer_map(mod, campaign, cm, "ground_types").tiles("ground_types")
        clim = campmap.layer_map(mod, campaign, cm, "climates").tiles("climates")
        p.sea = cm.sea
    except (MapError, TgaError, OSError) as exc:
        raise TerrainError(str(exc)) from exc

    sig = signature(mod, cm, campaign, season, SCALE,
                    (ground.tobytes(), clim.tobytes(), p.sea))
    memo = (str(Path(mod.data)).lower(), campaign, season)
    hit = _PLANS.get(memo)
    if hit is not None and hit[0] == sig:
        return hit[1]
    p.key = sig

    want = (p.width, p.height)
    for img, code in ((ground, "ground_types"), (clim, "climates")):
        if img.size != want:
            raise TerrainError(
                f"{campmap.LAYER_BY_CODE[code]['file']} comes out "
                f"{img.width}x{img.height} per tile and descr_terrain.txt says "
                f"the map is {want[0]}x{want[1]}")

    # 0 is "no climate declared this colour", which the engine draws with the
    # default block, so slot 0 IS the default climate rather than a hole
    names = [DEFAULT_CLIMATE] + [c["code"] for c in v.climates]
    clut = {bytes(c["rgb"]): i + 1 for i, c in enumerate(v.climates) if c["rgb"]}
    glut = {bytes(g["rgb"]): i + 1 for i, g in enumerate(mapvocab.GROUND_TYPES)}
    cidx = _index(clim, clut)
    gidx = _index(ground, glut)

    n_ground = len(mapvocab.GROUND_TYPES) + 1
    if len(names) * n_ground > 256:
        raise TerrainError(
            f"{len(v.climates)} climates against {n_ground - 1} ground types is "
            f"more pairs than a byte can index; the engine's own climate list "
            f"is twelve")

    # (climate, ground) -> texture slot, as a 256-entry table, so the whole
    # per-tile lookup is one Pillow point() in C rather than a quarter of a
    # million dictionary hits
    slots: Dict[str, int] = {}
    table = [0] * 256
    gaps: Dict[Tuple[str, str], dict] = {}
    for ci, cname in enumerate(names):
        for gi in range(1, n_ground):
            gcode = mapvocab.GROUND_TYPES[gi - 1]["code"]
            combo = ci * n_ground + gi
            name = v.texture(cname, gcode, season)
            if not name:
                gaps.setdefault((cname, gcode),
                                {"climate": cname, "ground": gcode, "file": "",
                                 "why": "no entry", "tiles": 0, "tile": None,
                                 "combo": combo})
                continue
            if name not in slots:
                slots[name] = len(slots) + 1
            table[combo] = slots[name]
    p.names = [""] * len(slots)
    for name, k in slots.items():
        p.names[k - 1] = name

    combo_img = ImageChops.add(
        Image.frombytes("L", want, cidx).point(lambda x: x * n_ground),
        Image.frombytes("L", want, gidx))
    # a sea tile asks for nothing, so it is taken out before anything is counted
    land = Image.frombytes("L", want, p.sea).point(lambda x: 0 if x else 255)
    p.slots = ImageChops.darker(combo_img.point(table), land)
    census = dict((v_, n) for n, v_ in (p.slots.getcolors(1 << 16) or []))
    p.counts = [census.get(k + 1, 0) for k in range(len(p.names))]

    # the gaps, measured: a pair with no entry that no tile is actually on is
    # not a finding, which is this project's oldest rule about rules
    combo_land = ImageChops.darker(combo_img, land).tobytes()
    for gap in gaps.values():
        combo = gap.pop("combo")
        if combo > 255:
            continue
        n = combo_land.count(bytes([combo]))
        if not n:
            continue
        gap["tiles"] = n
        at = _first_tile(combo_land, p.width, combo)
        gap["tile"] = list(at) if at else None
        if gap["ground"] in SEA_GROUND:
            # The disagreement 16a measured: map_heights says land and
            # map_ground_types says sea. The aerial file is not the fault here
            # and saying it names no sea entry would send somebody to edit it,
            # so the finding names the two layers that actually disagree.
            gap["why"] = (
                f"map_ground_types.tga calls {n:,} tile{'' if n == 1 else 's'} "
                f"{gap['ground']} and map_heights.tga calls "
                f"{'it' if n == 1 else 'them'} land, so neither the terrain nor "
                f"the sea is drawn there. The engine draws the sea from "
                f"terrain/aerial_map, which is why {AERIAL_REL} has no entry "
                f"for a sea ground type.")
        else:
            gap["why"] = (f"{AERIAL_REL} names no texture for {gap['ground']} in "
                          f"climate {gap['climate']}, and its default block "
                          f"names none either")
        p.gaps.append(gap)

    # and the ones the file does name and the folder does not hold
    raw_slots = p.slots.tobytes()
    for k, name in enumerate(p.names, start=1):
        if not p.counts[k - 1]:
            continue
        path = texture_dir(mod) / name
        if path.is_file():
            continue
        at = _first_tile(raw_slots, p.width, k)
        p.gaps.append({"climate": "", "ground": "", "file": name,
                       "tiles": p.counts[k - 1], "tile": list(at) if at else None,
                       "why": f"{AERIAL_REL} draws {p.counts[k - 1]:,} tile"
                              f"{'' if p.counts[k - 1] == 1 else 's'} with "
                              f"{name}, and it is not in {TEXTURE_DIR_REL}"})
    p.gaps.sort(key=lambda g: -g["tiles"])
    _PLANS[memo] = (sig, p)
    return p


# ---------------------------------------------------------------------------
# the picture


def _scaled(path: Path, scale: int) -> Image.Image:
    """One texture at the size it is drawn: its own pixels over
    :data:`TEXTURE_SPAN` tiles, times ``scale`` composite pixels a tile."""
    img, _ = read(path)
    w = max(1, round(img.width * scale / TEXTURE_SPAN))
    h = max(1, round(img.height * scale / TEXTURE_SPAN))
    return img.convert("RGB").resize((w, h), Image.BICUBIC)


def _tiled(texture: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    """``texture`` repeated over ``box``, in phase with the map's origin.

    The phase is what makes this terrain rather than wallpaper. Tiling each map
    tile with its own copy of the texture puts a seam on every tile edge and a
    quarter of a million of them across DaC; anchoring the repeat at (0,0) and
    cropping out the part this region needs means two neighbouring tiles of the
    same ground continue one another, which is what the game does and what a
    picture of a forest has to do to look like one.
    """
    x0, y0, x1, y1 = box
    tw, th = texture.size
    pw, ph = x1 - x0, y1 - y0
    big = Image.new("RGB", (pw + tw, ph + th))
    for yy in range(0, ph + th, th):
        for xx in range(0, pw + tw, tw):
            big.paste(texture, (xx, yy))
    ox, oy = x0 % tw, y0 % th
    return big.crop((ox, oy, ox + pw, oy + ph))


def composite(mod, p: Plan, scale: int = SCALE) -> Image.Image:
    """The whole map as one picture, ``scale`` pixels a tile.

    Pink underneath, so anything not drawn is pink without a second pass;
    then one paste per distinct texture, masked to the tiles that asked for it
    and cropped to their bounding box; then the sea over the top.

    One paste a texture and not one a tile: fifty pastes on DaC rather than a
    hundred and seventy thousand, and every one of them in Pillow's C. The
    bounding-box crop is what makes it fifty *small* pastes - a climate covers
    a corner of a map, not the whole of it - and it is worth about a third of
    the drawing time.
    """
    cw, ch = p.width * scale, p.height * scale
    out = Image.new("RGB", (cw, ch), MISSING_RGB)
    if p.slots is None:
        return out
    folder = texture_dir(mod)
    for k, name in enumerate(p.names, start=1):
        if not p.counts[k - 1]:
            continue
        path = folder / name
        if not path.is_file():
            continue                        # pink, and already a gap row
        try:
            texture = _scaled(path, scale)
        except (TgaError, OSError, ValueError):
            continue                        # pink, and reported by check_textures
        mask = p.slots.point([255 if i == k else 0 for i in range(256)])
        bb = mask.getbbox()
        if not bb:
            continue
        box = (bb[0] * scale, bb[1] * scale, bb[2] * scale, bb[3] * scale)
        cut = mask.crop(bb).resize((box[2] - box[0], box[3] - box[1]), Image.NEAREST)
        out.paste(_tiled(texture, box), (box[0], box[1]), cut)
    sea = Image.frombytes("L", (p.width, p.height), p.sea).point(
        lambda x: 255 if x else 0).resize((cw, ch), Image.NEAREST)
    out.paste(SEA_RGB, (0, 0), sea)
    return out


def check_textures(mod, p: Plan) -> List[dict]:
    """The textures a tile asks for whose header will not read. Gap rows.

    Headers only, through :func:`~unittransfer.maptga.probe`, which is the
    whole point: decoding the fifty textures DaC uses is about six hundred
    milliseconds and this runs on the validator's path, where there is a
    one-second bar over the entire rule set. A header catches what is actually
    seen in the wild - a ``.dds`` saved under a ``.tga`` name, a truncated
    file - and a texture that passes the header and then fails on its pixels is
    still left pink by :func:`composite`, which is the same answer arrived at
    one step later.
    """
    out: List[dict] = []
    folder = texture_dir(mod)
    raw = p.slots.tobytes() if p.slots is not None else b""
    for k, name in enumerate(p.names, start=1):
        if not p.counts[k - 1]:
            continue
        path = folder / name
        if not path.is_file():
            continue                        # plan already said so
        try:
            probe(path)
        except (TgaError, OSError, ValueError) as exc:
            at = _first_tile(raw, p.width, k)
            out.append({"climate": "", "ground": "", "file": name,
                        "tiles": p.counts[k - 1],
                        "tile": list(at) if at else None,
                        "why": f"{name} is in {TEXTURE_DIR_REL} and will not "
                               f"read: {exc}"})
    return out


def png(mod, p: Plan, scale: int = SCALE) -> bytes:
    buf = io.BytesIO()
    composite(mod, p, scale).save(buf, "PNG", optimize=False)
    return buf.getvalue()


def signature(mod, cm: CampaignMap, campaign: str, season: str, scale: int,
              pixels: Tuple[bytes, ...] = ()) -> str:
    """Everything that could change the picture, as one cache token.

    ``pixels`` is the tile-per-pixel bytes of the layers it is drawn from,
    hashed: **not** their files' timestamps. That is the difference between a
    picture of the map on disk and a picture of the map on the screen, and this
    screen has a paint tool on it. A stroke on ``map_ground_types.tga`` changes
    the pixels this object is holding and nothing about the file until somebody
    saves, and a composite keyed on the file would go on showing the terrain
    before the stroke. Hashing them is about four milliseconds on DaC's three
    quarters of a megabyte, against a second to rebuild.

    The rest is stats: the two text files that say what a colour means, and
    every texture the aerial file names - not only the ones this map uses,
    because which ones it uses is the answer rather than the question. About
    140 of them on DaC, and the folder is warm after the first.
    """
    bits = [f"mapterrain|{Path(mod.data)}|{campaign}|{season}|{scale}"]
    if pixels:
        h = hashlib.sha1()
        for buf in pixels:
            h.update(buf)
        bits.append(f"pixels|{h.hexdigest()}")
    data = Path(mod.data)
    bits.append(f"aerial|{_sig(data / AERIAL_REL)}")
    bits.append(f"climates|{_sig(data / mapvocab.CLIMATES_REL)}")
    folder = texture_dir(mod)
    names = set()
    try:
        names = {n for block in parse((data / AERIAL_REL).read_text(encoding=ENCODING)).values()
                 for pair in block.values() for n in pair}
    except OSError:
        pass
    for name in sorted(names):
        bits.append(f"{name}|{_sig(folder / name)}")
    return "|".join(bits)


def _sig(path: Path) -> str:
    try:
        st = path.stat()
        return f"{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        return "-"


def view(mod, cm: CampaignMap, campaign: str = "", season: str = "summer",
         scale: int = SCALE) -> dict:
    """What the map screen is told before it asks for the picture. Never raises.

    A mod with no aerial file, or a map whose two layers will not read, comes
    back ``have: False`` with the sentence that says which file and why - the
    same shape :func:`campmap.layer_view` answers in, and for the same reason:
    the screen has to be able to name the file rather than show an empty
    control that appears to be broken.
    """
    out = {"have": False, "problem": "", "scale": scale, "season": season,
           "width": 0, "height": 0, "textures": 0, "pink_tiles": 0,
           "sea_tiles": 0, "gaps": [],
           "vocabulary": read_vocabulary(mod).payload()}
    try:
        p = plan(mod, cm, campaign, season)
    except TerrainError as exc:
        out["problem"] = str(exc)
        return out
    except (MapError, OSError) as exc:
        out["problem"] = str(exc)
        return out
    out.update(p.payload())
    out["gaps"] = p.gaps + check_textures(mod, p)
    out["pink_tiles"] = sum(g["tiles"] for g in out["gaps"])
    out["have"] = True
    out["width"] = p.width * scale
    out["height"] = p.height * scale
    return out
