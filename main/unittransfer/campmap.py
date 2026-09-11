"""The campaign map, read: the terrain header, the ten layers and the regions.

This is the read half of the map editor's engine. Nothing here paints, saves or
validates - :mod:`unittransfer.campaint` paints and 16f will validate - but
everything they do stands on the index this module builds, so the rules it gets
right are the rules the whole editor gets right.

**Not** :mod:`unittransfer.stratmap`. That name has belonged to the
``descr_model_strat.txt`` cleaner since Phase 15 and it is a different concern
entirely; an earlier draft of the roadmap pointed this session at it by mistake.

Four things live here, in the order the editor needs them:

``descr_terrain.txt``
    Five small blocks, and one of them is load-bearing: ``dimensions`` is the
    tile grid every other file is measured against, and the engine caps both
    sides at 510.

The ten TGA layers
    Three different sizes off one grid, and getting the relationship wrong is
    the classic map crash::

        W x H         map_regions, map_features, map_trade_routes
        2W x 2H       map_roughness
        2W+1 x 2H+1   map_heights, map_fog, map_ground_types, map_climates
        advisory      water_surface (nominally 256x256; DaC ships 1021x975)
        free          map_FE.tga, the front-end picture

    The odd-sized four are sampled at the **block centre**: tile ``(tx,ty)`` is
    pixel ``(2tx+1, 2ty+1)``. Corner sampling is the mistake that makes a
    coastline look one tile out.

``descr_regions.txt``
    A positional record, not ``keyword value``, which is why
    :mod:`unittransfer.flatrecord` does not fit it and :mod:`keyblock`'s splice
    discipline does. Every field carries the index of the line it came from, and
    the file is kept as its own lines, so re-serialising a file nobody edited
    returns the bytes that were read - CRLF, tabs, comments and all.

The region index
    Colour to region, the label image, pixel counts, bounding boxes, centroids,
    label anchors, settlement and port pixels, port ownership and region IDs.

Three coordinate systems, and every accessor here says which one it means:

    image     (0,0) top-left, y down. What Pillow hands back and what the
              browser draws.
    game      (0,0) bottom-left, y up. What ``descr_strat.txt`` writes.
              ``game_y = height - 1 - image_y``.
    double    the 2W+1 layers: ``(2x+1, 2y+1)`` of the tile's image coordinates.

Measured on DaC (510x487, 198 regions, 202 region colours), the whole read is
about half a second and none of it is on the interaction path:

    all ten layers decoded              117 ms
    unique region colours (getcolors)    13 ms
    exact label image                    61 ms
    per-region stats in one pass        180 ms
    sea mask, in Pillow's C              ~5 ms

The label image is built by an exact dictionary pass over the raw bytes, and
that is deliberate: ``Image.quantize`` with a fixed palette is four times
faster and **wrong**, because its nearest-colour matching is approximate. It
put 1,320 of DaC's pixels on the wrong region. An index that is 99.5% right is
not an index.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops

from . import mapvocab
from .maptga import TgaError, TgaInfo, probe, read
from .mapvocab import PORT_RGB, SETTLEMENT_RGB, Rgb, key

#: Plain 8-bit game data, as everywhere else
ENCODING = "latin-1"

BASE_REL = "world/maps/base"
TERRAIN_REL = f"{BASE_REL}/descr_terrain.txt"
REGIONS_REL = f"{BASE_REL}/descr_regions.txt"
#: deleted whenever the map changes, or the game loads the stale binary instead
RWM_REL = f"{BASE_REL}/map.rwm"

#: The engine's ceiling on either side of the tile grid, per the arbiter.
MAX_DIMENSION = 510

#: ``size`` says how the layer's pixels relate to the tile grid.
#:   ``tile``      W x H, one pixel per tile
#:   ``double``    2W x 2H
#:   ``centre``    2W+1 x 2H+1, sampled at (2t+1, 2t+1)
#:   ``advisory``  a size the arbiter states but real mods ignore
#:   ``free``      no relationship to the grid at all
LAYERS: Tuple[dict, ...] = (
    {"code": "regions", "file": "map_regions.tga", "size": "tile", "required": True,
     "label": "Regions"},
    {"code": "heights", "file": "map_heights.tga", "size": "centre", "required": True,
     "label": "Heights"},
    {"code": "ground_types", "file": "map_ground_types.tga", "size": "centre",
     "required": True, "label": "Ground types"},
    {"code": "climates", "file": "map_climates.tga", "size": "centre",
     "required": True, "label": "Climates"},
    {"code": "features", "file": "map_features.tga", "size": "tile",
     "required": True, "label": "Features"},
    {"code": "fog", "file": "map_fog.tga", "size": "centre", "required": False,
     "label": "Fog"},
    {"code": "trade_routes", "file": "map_trade_routes.tga", "size": "tile",
     "required": False, "label": "Trade routes"},
    {"code": "roughness", "file": "map_roughness.tga", "size": "double",
     "required": False, "label": "Roughness"},
    {"code": "water_surface", "file": "water_surface.tga", "size": "advisory",
     "required": False, "label": "Water surface"},
    {"code": "fe", "file": "map_FE.tga", "size": "free", "required": False,
     "label": "Front-end map"},
)

LAYER_BY_CODE: Dict[str, dict] = {ly["code"]: ly for ly in LAYERS}

#: The key that ticks a layer on the map screen: ten layers, ten number keys,
#: ``1`` to ``0`` in the order :data:`LAYERS` declares them (20a, T11).
#:
#: Declaration order, deliberately, and not the draw order the manifest sorts
#: by. Draw order puts the front-end picture first and the region layer seventh,
#: which would make the key nobody wants the easiest one to reach; declaration
#: order is the five required layers first, and it is the same in every mod
#: because it is this file's own list rather than anything a mod ships.
#:
#: It lives here rather than in the browser for the reason everything else on
#: this screen does: the manifest carries it out with each layer, so the panel
#: prints the key it will actually answer to and the two cannot drift.
HOTKEYS: Dict[str, str] = {
    ly["code"]: "1234567890"[i] if i < 10 else ""
    for i, ly in enumerate(LAYERS)
}


class MapError(ValueError):
    """The map cannot be read at all - a missing layer, or a broken header."""


# ---------------------------------------------------------------------------
# descr_terrain.txt


@dataclass
class Terrain:
    """``descr_terrain.txt``: the tile grid and the numbers hung off it."""

    width: int = 0
    height: int = 0
    min_sea_height: float = 0.0
    max_land_height: float = 0.0
    roughness_min: float = 0.0
    roughness_max: float = 0.0
    fractal_multiplier: float = 0.0
    latitude_min: float = 0.0
    latitude_max: float = 0.0
    path: Optional[Path] = None

    @property
    def tiles(self) -> int:
        return self.width * self.height

    def game_y(self, image_y: int) -> int:
        """Image row to the y ``descr_strat.txt`` writes, and back again."""
        return self.height - 1 - image_y

    #: the transform is its own inverse
    image_y = game_y

    def centre(self, tx: int, ty: int) -> Tuple[int, int]:
        """The pixel a 2W+1 layer is sampled at for tile ``(tx, ty)``."""
        return 2 * tx + 1, 2 * ty + 1

    def in_bounds(self, tx: int, ty: int) -> bool:
        return 0 <= tx < self.width and 0 <= ty < self.height

    def expected_size(self, size_rule: str) -> Optional[Tuple[int, int]]:
        if size_rule == "tile":
            return self.width, self.height
        if size_rule == "double":
            return 2 * self.width, 2 * self.height
        if size_rule == "centre":
            return 2 * self.width + 1, 2 * self.height + 1
        return None


_BLOCK = re.compile(r"^\s*(\w+)\s*$\s*\{(.*?)^\s*\}", re.S | re.M)


def parse_terrain(text: str) -> Terrain:
    """Read the header. Missing blocks are zeros, not an exception.

    A mod with no ``lattitude`` block (the game's own spelling) is unusual, not
    broken, and the map still draws - so only ``dimensions`` is worth refusing
    over, and that is :func:`read_terrain`'s call, not this one's.
    """
    t = Terrain()
    blocks = {m.group(1).lower(): m.group(2) for m in _BLOCK.finditer(text)}

    def num(block: str, keyname: str, default=0.0) -> float:
        body = blocks.get(block, "")
        m = re.search(rf"^\s*{keyname}\s+(-?[\d.]+)", body, re.M)
        return float(m.group(1)) if m else default

    t.width = int(num("dimensions", "width"))
    t.height = int(num("dimensions", "height"))
    t.min_sea_height = num("heights", "min_sea_height")
    t.max_land_height = num("heights", "max_land_height")
    t.roughness_min = num("roughness", "min")
    t.roughness_max = num("roughness", "max")
    t.fractal_multiplier = num("fractal", "multiplier")
    # the game spells it with two Ts; accept both so a corrected mod still reads
    lat = "lattitude" if "lattitude" in blocks else "latitude"
    t.latitude_min = num(lat, "min")
    t.latitude_max = num(lat, "max")
    return t


def read_terrain(mod) -> Terrain:
    path = mod.data / TERRAIN_REL
    try:
        text = path.read_text(encoding=ENCODING)
    except OSError as exc:
        raise MapError(f"descr_terrain.txt: {exc}") from exc
    t = parse_terrain(text)
    t.path = path
    if t.width <= 0 or t.height <= 0:
        raise MapError(f"descr_terrain.txt has no usable dimensions block "
                       f"(read {t.width}x{t.height})")
    return t


# ---------------------------------------------------------------------------
# descr_regions.txt - positional, line-indexed, byte-exact on the way out


#: a bare ``R G B`` line, which is the anchor the rest of the record hangs off
_RGB_LINE = re.compile(r"^(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})$")
_NUM_LINE = re.compile(r"^-?\d+$")


@dataclass
class RegionRecord:
    """One region, and the line each field came from.

    Every ``*_line`` is an index into :attr:`RegionsFile.lines`. An edit rewrites
    that one line and nothing else, which is what keeps a file full of hand
    formatting intact through a save.
    """

    name: str = ""
    name_line: int = -1
    legion: str = ""
    legion_line: int = -1
    settlement: str = ""
    settlement_line: int = -1
    faction: str = ""
    faction_line: int = -1
    rebels: str = ""
    rebels_line: int = -1
    rgb: Rgb = (0, 0, 0)
    rgb_line: int = -1
    resources: List[str] = field(default_factory=list)
    resources_line: int = -1
    triumph: int = 0
    triumph_line: int = -1
    farming: int = 0
    farming_line: int = -1
    religions: Dict[str, int] = field(default_factory=dict)
    religions_line: int = -1
    #: the short form with no settlement. The arbiter says such a province must
    #: be the last entry in the file, so the validator has to know which it is.
    wasteland: bool = False
    #: [first, last] line indices of the whole record, comments included
    span: Tuple[int, int] = (-1, -1)
    #: what could not be placed, for the validator rather than for a crash here
    problems: List[str] = field(default_factory=list)

    @property
    def rgb_key(self) -> int:
        return key(self.rgb)

    @property
    def religion_total(self) -> int:
        """Must be 100 or the game crashes on load."""
        return sum(self.religions.values())


@dataclass
class RegionsFile:
    """``descr_regions.txt`` as lines plus an index over them."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    records: List[RegionRecord] = field(default_factory=list)
    path: Optional[Path] = None

    def serialise(self) -> str:
        """The file, exactly as it would go back to disk."""
        return self.newline.join(self.lines) + (self.newline if self.trailing_newline else "")

    def by_name(self, name: str) -> Optional[RegionRecord]:
        low = name.lower()
        return next((r for r in self.records if r.name.lower() == low), None)

    def by_rgb(self, rgb: Rgb) -> Optional[RegionRecord]:
        k = key(rgb)
        return next((r for r in self.records if r.rgb_key == k), None)


def _split_lines(text: str) -> Tuple[List[str], str, bool]:
    """The same split :func:`unittransfer.triggers.split_lines` does.

    Imported rather than copied would be better still, except that importing
    the trigger engine to read a map file drags in half of Phase 8. The rule it
    encodes is the one that matters: a line number means the same thing in every
    editor in this toolkit.
    """
    from .triggers import split_lines
    return split_lines(text)


def parse_regions(text: str) -> RegionsFile:
    """Read every record. Never raises: a record that will not parse is kept.

    The record is positional and two shapes of it are in the wild::

        Region_Name              Region_Name
            legion: Some_Legion      Settlement
            Settlement               faction
            faction                  rebel_type
            rebel_type               R G B
            R G B                    res, res, res
            res, res, res            5
            5                        1
            1                        religions { … }
            religions { … }

    Mylae's ``parseDescrRegions`` hard-codes the RGB at line offset 4 and
    resynchronises when it does not find one, which silently drops **every DaC
    region**, because DaC writes the ``legion:`` form. So the anchor here is the
    ``R G B`` line itself, found by shape: the three lines before it are the
    settlement, its creator faction and its rebel type, and the lines after it
    are the resources, then the two bare numbers, then the religions.

    The two bare numbers are **triumph value then base farming level**, settled
    twice over: vanilla writes 5 for the first on 110 of its 112 regions while
    the second runs 1 to 6, and Geomod's manual says of them "Victory … leave it
    at 5" and "Agriculture … 4 is approximately average".

    **The indent is not part of the format.** Both shapes above are drawn with
    one because vanilla, DaC and Third Age Reforged all write one, and reading
    the record off it alone was wrong: a beta mod ships the same records flush
    left, which the engine plays and which came out here as one record per line
    with a colour on none of them. Every province on that map then read as
    painted and declared nowhere - no name in the hover, nothing to click, and a
    query table of 1,592 rows that were single lines of the file. So the indent
    is the **first** reading and :func:`_starts_by_shape` is the second, and
    which one a file gets is decided by which of them finds the colours.
    """
    lines, newline, trailing = _split_lines(text)
    out = RegionsFile(lines=lines, newline=newline, trailing_newline=trailing)

    starts = _starts_by_indent(lines)
    recs = _records_at(lines, starts)
    # A file with no indentation at all reads as one record per line, every one
    # of them missing its colour. The indent is not part of the format - the
    # engine's own parser ignores whitespace - so a mod that writes the records
    # flush left is a mod this read has to answer for, not refuse.
    if sum(1 for r in recs if r.rgb_line >= 0) < sum(1 for r in recs
                                                     if r.rgb_line < 0):
        by_shape = _records_at(lines, _starts_by_shape(lines))
        if sum(1 for r in by_shape if r.rgb_line >= 0) > sum(
                1 for r in recs if r.rgb_line >= 0):
            recs = by_shape
    out.records.extend(recs)
    return out


def _records_at(lines: List[str], starts: List[int]) -> List[RegionRecord]:
    """One record per start, each running to the line before the next."""
    return [_parse_record(lines, start,
                          (starts[n + 1] - 1) if n + 1 < len(starts)
                          else len(lines) - 1)
            for n, start in enumerate(starts)]


def _starts_by_indent(lines: List[str]) -> List[int]:
    """The first line of every record, by the indent the three big mods write.

    Vanilla, Third Age Reforged and DaC all indent the body of a record and
    leave the name flush left, so the name is the whole signal and a malformed
    record still shows up as a record with :attr:`RegionRecord.problems` on it -
    which is what the validator reports. That is worth keeping, so this stays
    the first reading and :func:`_starts_by_shape` is only the fallback.
    """
    def is_header(ln: str) -> bool:
        if not ln.strip() or ln.lstrip().startswith(";"):
            return False
        if ln[:1] in (" ", "\t"):
            return False
        # Third Age 6 writes its religions line flush left too; treating that as
        # a new region both loses the religions and invents a phantom record
        return not ln.lstrip().lower().startswith("religions")

    return [i for i, ln in enumerate(lines) if is_header(ln)]


def _starts_by_shape(lines: List[str]) -> List[int]:
    """The same, for a file that gives no indent to read it off.

    The ``R G B`` line is already this module's anchor, so the walk is
    backwards from each one over the three lines the grammar puts in front of
    it - settlement, creator faction, rebel type - and then the name, with an
    optional ``legion:`` in between. It stops early at the previous record's
    colour, its religions line or a bare number, none of which can be any of
    those four. That terminator is what makes the wasteland short form, which
    has no settlement line, fall out of the same walk rather than need a case
    of its own.
    """
    starts: List[int] = []
    prev_rgb = -1
    for j, ln in enumerate(lines):
        if not _RGB_LINE.match(_clean_line(ln)):
            continue
        back: List[int] = []
        i = j - 1
        while i > prev_rgb and len(back) < 5:
            s = _clean_line(lines[i])
            if not s:
                i -= 1
                continue
            if (s.lower().startswith("religions") or _NUM_LINE.match(s)
                    or _RGB_LINE.match(s)):
                break
            back.append(i)
            i -= 1
        starts.append(back[-1] if back else j)
        prev_rgb = j
    return starts


def _clean_line(line: str) -> str:
    """One line with its comment and its surrounding whitespace gone."""
    return line.split(";", 1)[0].strip()


def _strip_bom(s: str) -> str:
    """A byte-order mark in front of the first region's name, either way it comes.

    These files are read as latin-1, so a UTF-8 BOM arrives as the three
    characters ``ï»¿`` rather than as ``\\ufeff``. It is not part of the name
    either way, and a name carrying one matches nothing in ``descr_strat.txt``,
    the names file or the campaign script. The line itself is left alone, so
    the BOM survives a save of every line but the one an edit rewrites.
    """
    for mark in ("﻿", "\xef\xbb\xbf"):
        if s.startswith(mark):
            return s[len(mark):]
    return s


def _parse_record(lines: List[str], start: int, end: int) -> RegionRecord:
    rec = RegionRecord(name=_strip_bom(lines[start].strip()), name_line=start,
                       span=(start, end))

    body: List[Tuple[int, str]] = []
    for i in range(start + 1, end + 1):
        s = _clean_line(lines[i])
        if not s:
            continue
        if s.lower().startswith("legion:"):
            rec.legion = s.split(":", 1)[1].strip()
            rec.legion_line = i
            continue
        body.append((i, s))

    at_rgb = next((n for n, (_, s) in enumerate(body) if _RGB_LINE.match(s)), None)
    if at_rgb is None:
        rec.problems.append("no R G B line")
        return rec
    line_no, s = body[at_rgb]
    m = _RGB_LINE.match(s)
    rec.rgb = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    rec.rgb_line = line_no

    head = body[:at_rgb]
    if len(head) >= 3:
        (rec.settlement_line, rec.settlement) = head[-3]
        (rec.faction_line, rec.faction) = head[-2]
        (rec.rebels_line, rec.rebels) = head[-1]
    else:
        # the wasteland short form: no settlement, and the arbiter says such a
        # province must be the last entry in the file
        rec.wasteland = True
        for slot, (ln, val) in zip(("faction", "rebels"), head):
            setattr(rec, slot, val)
            setattr(rec, f"{slot}_line", ln)

    tail = body[at_rgb + 1:]
    rel_at = next((n for n, (_, s) in enumerate(tail) if "religions" in s.lower()), None)
    if rel_at is not None:
        ln, s = tail[rel_at]
        rec.religions_line = ln
        toks = re.search(r"religions\s*\{([^}]*)\}", s, re.I)
        if toks:
            parts = toks.group(1).split()
            for i in range(0, len(parts) - 1, 2):
                try:
                    rec.religions[parts[i]] = int(parts[i + 1])
                except ValueError:
                    rec.problems.append(f"religion {parts[i]!r} has no number")
        tail = tail[:rel_at]
    elif not rec.wasteland:
        rec.problems.append("no religions line")

    # the last two bare numbers before the religions line are triumph then farming;
    # anything left in front of them is the resource list, blank or not
    nums = [(n, ln, s) for n, (ln, s) in enumerate(tail) if _NUM_LINE.match(s)]
    if len(nums) >= 2:
        (n_t, ln_t, s_t), (n_f, ln_f, s_f) = nums[-2], nums[-1]
        rec.triumph, rec.triumph_line = int(s_t), ln_t
        rec.farming, rec.farming_line = int(s_f), ln_f
        rest = tail[:n_t]
    else:
        if not rec.wasteland:
            rec.problems.append("triumph value and farming level not both present")
        rest = tail

    if rest:
        ln, s = rest[0]
        rec.resources_line = ln
        rec.resources = [t.strip() for t in s.split(",") if t.strip()]
        if len(rest) > 1:
            rec.problems.append(f"{len(rest) - 1} unrecognised line(s) in the record")
    return rec


def read_regions(mod) -> RegionsFile:
    from .keyblock import read_text
    path = mod.data / REGIONS_REL
    try:
        text = read_text(path, ENCODING)
    except OSError as exc:
        raise MapError(f"descr_regions.txt: {exc}") from exc
    out = parse_regions(text)
    out.path = path
    return out


# ---------------------------------------------------------------------------
# the region index


@dataclass
class Region:
    """One region as the map sees it, which is not quite what the file says.

    A record in ``descr_regions.txt`` with no pixels is legal to write and fatal
    to play, so the two halves are kept apart: this is the pixels, and
    :class:`RegionRecord` is the text. :attr:`record` links them when they agree.
    """

    rgb: Rgb
    pixels: int = 0
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)      # image coords, inclusive
    centroid: Tuple[float, float] = (0.0, 0.0)          # image coords
    #: a pixel that is actually inside the region, for drawing its name on
    anchor: Tuple[int, int] = (0, 0)
    settlement: Optional[Tuple[int, int]] = None        # image coords
    port: Optional[Tuple[int, int]] = None              # image coords
    #: the order the engine numbers regions in, or -1 for a colour it skips
    region_id: int = -1
    record: Optional[RegionRecord] = None

    @property
    def name(self) -> str:
        return self.record.name if self.record else ""


@dataclass
class RegionIndex:
    """Everything derived from ``map_regions.tga``, built once."""

    width: int
    height: int
    #: one byte per tile, the index into :attr:`colours`. The label image every
    #: border, mask, recolour and hit test reads instead of RGB triples.
    labels: bytes
    colours: List[Rgb]
    regions: List[Region]
    by_key: Dict[int, Region] = field(default_factory=dict)
    settlements: List[Tuple[int, int]] = field(default_factory=list)
    ports: List[Tuple[int, int]] = field(default_factory=list)
    #: ports whose owning region the cardinal rule cannot decide
    undecided_ports: List[Tuple[int, int]] = field(default_factory=list)
    #: settlement pixels with no region on any cardinal side. DaC has one, at
    #: image (339,65), sitting inside a colour ``descr_regions.txt`` never
    #: declares - a province painted on the map and never written down.
    orphan_settlements: List[Tuple[int, int]] = field(default_factory=list)
    #: markers past the first for a region that already had one
    extra_settlements: List[Tuple[int, int]] = field(default_factory=list)
    extra_ports: List[Tuple[int, int]] = field(default_factory=list)
    #: colours in the image that no record in descr_regions.txt claims
    unclaimed: List[Rgb] = field(default_factory=list)
    #: records whose colour is nowhere in the image
    empty_records: List[RegionRecord] = field(default_factory=list)

    def at(self, x: int, y: int) -> Optional[Region]:
        """The region owning image pixel ``(x, y)``, markers included."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        return self.by_key.get(key(self.colours[self.labels[y * self.width + x]]))

    def label_at(self, x: int, y: int) -> int:
        return self.labels[y * self.width + x]


def _label_image(rgb: Image.Image) -> Tuple[bytes, List[Rgb], List[int]]:
    """``(labels, colours, counts)`` - one byte per pixel, exactly.

    Exact is the requirement, not fast. See the note in the module docstring
    about ``Image.quantize``; this pass is 61 ms on DaC and it is right.
    """
    census = rgb.getcolors(maxcolors=1 << 20)
    if census is None:                       # more colours than a byte can index
        raise MapError("map_regions.tga has more than a million colours")
    if len(census) > 256:
        raise MapError(f"map_regions.tga has {len(census)} distinct colours; the "
                       f"engine's ceiling is {mapvocab.MAX_REGION_COLOURS}")
    # most-used first, so the biggest regions get the low label numbers
    census.sort(key=lambda t: -t[0])
    colours = [c for _, c in census]
    counts = [n for n, _ in census]
    lut = {bytes(c): i for i, c in enumerate(colours)}
    raw = rgb.tobytes()
    labels = bytes(map(lut.__getitem__,
                       (raw[o:o + 3] for o in range(0, len(raw), 3))))
    return labels, colours, counts


def _mask01(band: Image.Image, keep) -> Image.Image:
    """An 8-bit 0/1 mask of one band, ``keep`` deciding per value."""
    return band.point([1 if keep(v) else 0 for v in range(256)])


def sea_mask(heights_centres: Image.Image, features: Image.Image) -> bytes:
    """One byte per tile: 1 where the engine treats the tile as sea.

    **A tile is sea iff its height pixel is not greyscale, or is pure black** -
    not from ground types, which was the old guess and is wrong at the
    coastline. A river crossing is never sea whatever its height says, which is
    the one exclusion neither layer can make on its own.

    All of it in Pillow's C: three band differences, two thresholds and a
    subtraction, about 5 ms on DaC's grid.
    """
    r, g, b = heights_centres.split()[:3]
    spread = ImageChops.lighter(
        ImageChops.lighter(ImageChops.difference(r, g), ImageChops.difference(g, b)),
        ImageChops.difference(r, b))
    brightest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    sea = ImageChops.lighter(_mask01(spread, bool), _mask01(brightest, lambda v: not v))

    fr, fg, fb = features.split()[:3]
    cross_rgb = mapvocab.feature("river_crossing")["rgb"]
    crossing = ImageChops.darker(
        ImageChops.darker(_mask01(fr, lambda v: v == cross_rgb[0]),
                          _mask01(fg, lambda v: v == cross_rgb[1])),
        _mask01(fb, lambda v: v == cross_rgb[2]))
    return ImageChops.subtract(sea, crossing).tobytes()


def _stats(labels: bytes, width: int, height: int, n: int):
    """Bounding box, centroid and pixel count for every label, in one pass.

    One loop rather than four, because the loop is the cost: 180 ms over DaC's
    248,370 tiles, once, at load.
    """
    minx = [width] * n
    maxx = [-1] * n
    miny = [height] * n
    maxy = [-1] * n
    sumx = [0] * n
    sumy = [0] * n
    count = [0] * n
    i = 0
    for y in range(height):
        for x in range(width):
            k = labels[i]
            i += 1
            if x < minx[k]:
                minx[k] = x
            if x > maxx[k]:
                maxx[k] = x
            if y < miny[k]:
                miny[k] = y
            if y > maxy[k]:
                maxy[k] = y
            sumx[k] += x
            sumy[k] += y
            count[k] += 1
    return minx, miny, maxx, maxy, sumx, sumy, count


def _anchor(labels: bytes, width: int, height: int, k: int,
            cx: int, cy: int, bbox) -> Tuple[int, int]:
    """A pixel of label ``k`` near ``(cx, cy)``, for hanging a name on.

    A centroid is only inside its own region when the region is convex, and a
    province wrapped round a bay is not. So the centroid is tried first and,
    when it belongs to somebody else, rings of increasing radius are walked
    outward from it until one of them lands back on the right region. Bounded by
    the bounding box, so a region always finds itself.
    """
    if 0 <= cx < width and 0 <= cy < height and labels[cy * width + cx] == k:
        return cx, cy
    x0, y0, x1, y1 = bbox
    limit = max(x1 - x0, y1 - y0, 1)
    for r in range(1, limit + 1):
        for x in range(max(x0, cx - r), min(x1, cx + r) + 1):
            for y in (cy - r, cy + r):
                if y0 <= y <= y1 and labels[y * width + x] == k:
                    return x, y
        for y in range(max(y0, cy - r), min(y1, cy + r) + 1):
            for x in (cx - r, cx + r):
                if x0 <= x <= x1 and labels[y * width + x] == k:
                    return x, y
    # a region with pixels always matched above; this is the empty-region case
    return cx, cy


#: the four the engine consults, in TWMapReader's order
_CARDINALS = ((0, -1, "N"), (-1, 0, "W"), (1, 0, "E"), (0, 1, "S"))


def _owner_of_marker(labels: bytes, colours: List[Rgb], width: int, height: int,
                     x: int, y: int, region_keys) -> Optional[Rgb]:
    """Which region a settlement pixel belongs to: any cardinal neighbour.

    Gigantus established that the engine looks only at N, W, E and S. Two
    different regions touching one settlement pixel is a map error, and the
    validator says so in 16f; here the first one found wins so the index still
    builds.
    """
    for dx, dy, _ in _CARDINALS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            c = colours[labels[ny * width + nx]]
            if key(c) in region_keys:
                return c
    return None


def _owner_of_port(labels: bytes, colours: List[Rgb], width: int, height: int,
                   x: int, y: int, sea: bytes) -> Optional[Tuple[Rgb, Tuple[int, int]]]:
    """Which region a port pixel belongs to, by TWMapReader's dock rule.

    A cardinal direction is a *dock* if that neighbour is sea and the neighbour
    **opposite** it is on the map and not sea - the port faces the water one way
    and the land the other. Then:

        three docks  the middle one of the three
        two docks    the more northerly (N, else E, else W)
        one dock     itself
        none or four undeterminable, and the game's answer is anyone's guess

    Returns ``(rgb, (x, y))`` of the tile on the land side, or ``None`` when the
    rule cannot decide. This is the only part of the index that is a *finding*
    rather than a format rule, and it is flagged as such: TWMapReader's author
    asked to be told when the game disagreed.
    """
    docks = {}
    opposite = {}
    for dx, dy, name in _CARDINALS:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < width and 0 <= ny < height):
            continue
        if not sea[ny * width + nx]:
            continue
        ox, oy = x - dx, y - dy
        if not (0 <= ox < width and 0 <= oy < height):
            continue                                   # opposite is off the map
        if sea[oy * width + ox]:
            continue                                   # water both sides
        docks[name] = True
        opposite[name] = (ox, oy)

    n = len(docks)
    if n in (0, 4):
        return None
    if n == 3:
        missing = ({"N", "W", "E", "S"} - set(docks)).pop()
        chosen = {"W": "E", "N": "S", "E": "W", "S": "N"}[missing]
    elif n == 2:
        chosen = "N" if "N" in docks else ("E" if "E" in docks else "W")
    else:
        chosen = next(iter(docks))
    ox, oy = opposite[chosen]
    return colours[labels[oy * width + ox]], (ox, oy)


def build_index(regions_img: Image.Image, sea: bytes,
                records: Sequence[RegionRecord]) -> RegionIndex:
    """The whole region index off the regions layer and the sea mask.

    ``sea`` is one byte per tile from :func:`sea_mask`; it is needed here and
    not only in the validator because the engine's own region numbering depends
    on it.
    """
    rgb = regions_img.convert("RGB")
    width, height = rgb.size
    labels, colours, counts = _label_image(rgb)

    marker_keys = {key(SETTLEMENT_RGB), key(PORT_RGB)}
    by_record = {r.rgb_key: r for r in records if r.rgb_line >= 0}
    region_keys = {k for k in by_record if k not in marker_keys}

    minx, miny, maxx, maxy, sumx, sumy, count = _stats(labels, width, height, len(colours))

    index = RegionIndex(width=width, height=height, labels=labels, colours=colours,
                        regions=[])
    for k, colour in enumerate(colours):
        if key(colour) in marker_keys:
            continue
        n = count[k]
        bbox = (minx[k], miny[k], maxx[k], maxy[k])
        cx, cy = (sumx[k] / n, sumy[k] / n) if n else (0.0, 0.0)
        reg = Region(rgb=colour, pixels=n, bbox=bbox, centroid=(cx, cy),
                     anchor=_anchor(labels, width, height, k, int(cx), int(cy), bbox),
                     record=by_record.get(key(colour)))
        index.regions.append(reg)
        index.by_key[key(colour)] = reg

    index.unclaimed = [r.rgb for r in index.regions if r.record is None]
    claimed = {key(r.rgb) for r in index.regions}
    index.empty_records = [r for r in records
                           if r.rgb_line >= 0 and r.rgb_key not in claimed]

    _place_markers(index, sea, region_keys)
    _number_regions(index, sea, region_keys)
    return index


def _place_markers(index: RegionIndex, sea: bytes, region_keys) -> None:
    """Find every settlement and port pixel and give it to a region.

    Settlements go first, because a port can land on one. DaC's port at image
    (75,107) has its dock west and a **settlement pixel** on the land side, so
    the dock rule returns black rather than a region colour; the port plainly
    belongs to whatever region that settlement belongs to, so it is resolved
    through the marker rather than dropped. That last step is ours, not the
    arbiter's - no source states it - but a port attached to the settlement it
    is standing next to beats a port attached to nothing.
    """
    labels, colours = index.labels, index.colours
    width, height = index.width, index.height
    marker_kind = {}
    for i, c in enumerate(colours):
        if key(c) == key(SETTLEMENT_RGB):
            marker_kind[i] = "settlement"
        elif key(c) == key(PORT_RGB):
            marker_kind[i] = "port"
    if not marker_kind:
        return

    ports: List[Tuple[int, int]] = []
    for i, lab in enumerate(labels):
        kind = marker_kind.get(lab)
        if kind is None:
            continue
        x, y = i % width, i // width
        if kind == "port":
            ports.append((x, y))
            index.ports.append((x, y))
            continue
        index.settlements.append((x, y))
        owner = _owner_of_marker(labels, colours, width, height, x, y, region_keys)
        reg = index.by_key.get(key(owner)) if owner is not None else None
        if reg is None:
            index.orphan_settlements.append((x, y))
        elif reg.settlement is None:
            reg.settlement = (x, y)
        else:
            index.extra_settlements.append((x, y))

    for x, y in ports:
        found = _owner_of_port(labels, colours, width, height, x, y, sea)
        if found is None:
            index.undecided_ports.append((x, y))
            continue
        owner, (ox, oy) = found
        if key(owner) in (key(SETTLEMENT_RGB), key(PORT_RGB)):
            owner = _owner_of_marker(labels, colours, width, height, ox, oy,
                                     region_keys)
        reg = index.by_key.get(key(owner)) if owner is not None else None
        if reg is None:
            index.undecided_ports.append((x, y))
        elif reg.port is None:
            reg.port = (x, y)
        else:
            index.extra_ports.append((x, y))


def _number_regions(index: RegionIndex, sea: bytes, region_keys) -> None:
    """Region IDs: the order a colour is first met scanning row-major.

    Two exclusions, both TWMapReader's, both invisible in every other tool:
    settlement and port pixels are not counted, and a tile that ``map_regions``
    calls land while ``map_heights`` calls it sea is skipped - the engine does
    not count an underwater land tile towards its region's number. Get this
    wrong and every ``descr_strat`` reference past the first mistake points at
    the wrong province.
    """
    labels, colours = index.labels, index.colours
    width = index.width
    marker_keys = {key(SETTLEMENT_RGB), key(PORT_RGB)}
    seen = set()
    order: List[int] = []
    for i, lab in enumerate(labels):
        k = key(colours[lab])
        if k in marker_keys or k in seen:
            continue
        if sea[i] and k in region_keys:
            continue                       # land by map_regions, sea by heights
        seen.add(k)
        order.append(k)
    for n, k in enumerate(order):
        reg = index.by_key.get(k)
        if reg is not None:
            reg.region_id = n


# ---------------------------------------------------------------------------
# the front door


def _adjacency(index: RegionIndex) -> Dict[int, List[int]]:
    """``{packed key: [packed keys]}`` - which regions share an edge.

    Reads the label image, never RGB triples: one byte per tile, compared with
    its right and lower neighbour so each shared edge is visited once rather
    than four times. The two marker colours are dropped on both sides - a
    settlement pixel sits inside a region and touching it says nothing about
    who its neighbours are.

    The answer is symmetric and each list is sorted by the neighbour's region
    id, so the panel reads in the engine's own order rather than in whatever
    order the scan happened to find them.
    """
    labels, colours = index.labels, index.colours
    w, h = index.width, index.height
    skip = {i for i, c in enumerate(colours) if c in (SETTLEMENT_RGB, PORT_RGB)}
    pairs: set = set()
    for y in range(h):
        row = y * w
        for x in range(w):
            a = labels[row + x]
            if a in skip:
                continue
            if x + 1 < w:
                b = labels[row + x + 1]
                if b != a and b not in skip:
                    pairs.add((a, b) if a < b else (b, a))
            if y + 1 < h:
                b = labels[row + w + x]
                if b != a and b not in skip:
                    pairs.add((a, b) if a < b else (b, a))
    out: Dict[int, List[int]] = {key(c): [] for i, c in enumerate(colours)
                                 if i not in skip}
    for a, b in pairs:
        out[key(colours[a])].append(key(colours[b]))
        out[key(colours[b])].append(key(colours[a]))
    rank = {key(r.rgb): (r.region_id if r.region_id >= 0 else 1 << 20)
            for r in index.regions}
    for k in out:
        out[k].sort(key=lambda n: (rank.get(n, 1 << 21), n))
    return out


class CampaignMap:
    """One mod's campaign map, read on demand.

    Layers are decoded the first time they are asked for and kept, because the
    editor asks for the same three over and over and the whole set is only
    117 ms; the index is built once and rebuilt only when something paints.
    """

    def __init__(self, mod, home: Optional[Path] = None):
        self.mod = mod
        self.base = mod.data / BASE_REL
        #: a campaign folder whose own copy of a map file wins over the base
        #: one, file by file - :func:`campaign_map`. None is the base map.
        self.home = home
        self.terrain = read_terrain(mod)
        self.regions = read_regions(mod)
        if home is not None:
            from .keyblock import read_text
            own = home / Path(TERRAIN_REL).name
            if own.is_file():
                self.terrain = parse_terrain(own.read_text(encoding=ENCODING))
                self.terrain.path = own
            own = home / Path(REGIONS_REL).name
            if own.is_file():
                self.regions = parse_regions(read_text(own, ENCODING))
                self.regions.path = own
        self._layers: Dict[str, Image.Image] = {}
        self._infos: Dict[str, TgaInfo] = {}
        self._tiles: Dict[str, Image.Image] = {}
        self._index: Optional[RegionIndex] = None
        self._sea: Optional[bytes] = None
        self._neighbours: Optional[Dict[int, List[int]]] = None

    # -- layers --------------------------------------------------------------

    def path(self, code: str) -> Path:
        name = LAYER_BY_CODE[code]["file"]
        if self.home is not None and (self.home / name).is_file():
            return self.home / name
        return self.base / name

    def layer(self, code: str) -> Image.Image:
        """One decoded layer, in image coordinates. Raises for a missing one."""
        if code not in self._layers:
            if code not in LAYER_BY_CODE:
                raise MapError(f"no such layer {code!r}")
            try:
                img, info = read(self.path(code))
            except TgaError as exc:
                raise MapError(str(exc)) from exc
            self._layers[code], self._infos[code] = img, info
        return self._layers[code]

    def info(self, code: str) -> TgaInfo:
        self.layer(code)
        return self._infos[code]

    def centres(self, code: str) -> Image.Image:
        """A 2W+1 layer resampled to one pixel per tile, at the block centre.

        ``transform`` with an affine of ``(2,0,0, 0,2,0)`` and nearest
        neighbour samples output pixel ``(x, y)`` at input ``(2x+1, 2y+1)``,
        which is the rule - verified pixel for pixel against an explicit scan,
        and 30 times quicker because it runs in Pillow's C.
        """
        img = self.layer(code)
        rule = LAYER_BY_CODE[code]["size"]
        if rule != "centre":
            return img
        return img.transform((self.terrain.width, self.terrain.height),
                             Image.AFFINE, (2, 0, 0, 0, 2, 0), Image.NEAREST)

    def tiles(self, code: str) -> Image.Image:
        """One layer at one pixel per tile, in RGB, and kept.

        The projection is :func:`tile_view`'s; what is added here is that the
        result is held. The probe reads ten layers at one tile and the legend
        censuses one, and both used to pay for the resample and the
        ``convert("RGB")`` every time they were asked - about 30 ms a layer,
        which on a click that names all ten is a third of a second of nothing.
        Dropped by :meth:`invalidate` with everything else the pixels imply.
        """
        if code not in self._tiles:
            self._tiles[code] = tile_view(self, code).convert("RGB")
        return self._tiles[code]

    def check_layers(self) -> List[str]:
        """Every layer's header against its size rule. A list of complaints.

        Cheap - headers only, no pixels - so it runs before anything is decoded
        and can say *which* file is the wrong shape rather than failing later
        with a size mismatch nobody can place.
        """
        out: List[str] = []
        if self.terrain.width > MAX_DIMENSION or self.terrain.height > MAX_DIMENSION:
            out.append(f"descr_terrain.txt: {self.terrain.width}x{self.terrain.height} "
                       f"is over the engine's {MAX_DIMENSION} cap")
        for ly in LAYERS:
            p = self.path(ly["code"])
            if not p.exists():
                if ly["required"]:
                    out.append(f"{ly['file']}: missing")
                continue
            try:
                info = probe(p)
            except TgaError as exc:
                out.append(str(exc))
                continue
            want = self.terrain.expected_size(ly["size"])
            if want and (info.width, info.height) != want:
                out.append(f"{ly['file']}: {info.width}x{info.height}, "
                           f"expected {want[0]}x{want[1]}")
        return out

    # -- derived -------------------------------------------------------------

    def require_grid(self, *codes: str) -> None:
        """Refuse, by name, before reading a layer that is the wrong shape.

        The sea mask and the region index are one byte per tile and index each
        other, so a layer whose size does not match ``descr_terrain.txt`` walks
        off the end of the other one. It did: a 7x5 ``map_features.tga`` on a
        510x487 map came out of :func:`_owner_of_port` as an ``IndexError``,
        which is the least useful sentence there is about a map whose layers
        disagree - and being told is the whole reason someone opens this screen.

        A layer the wrong shape is the classic map crash, so this is a refusal
        rather than a reshape. :func:`view` catches it and still serves the
        manifest, because the manifest is what says which file is wrong.
        """
        for code in codes:
            want = self.terrain.expected_size(LAYER_BY_CODE[code]["size"])
            if not want:
                continue
            got = self.layer(code).size
            if got != want:
                raise MapError(
                    f"{LAYER_BY_CODE[code]['file']} is {got[0]}x{got[1]}, and "
                    f"descr_terrain.txt says the map is {self.terrain.width}x"
                    f"{self.terrain.height}, so it should be {want[0]}x{want[1]}")

    @property
    def sea(self) -> bytes:
        """One byte per tile: 1 where the engine treats the tile as sea."""
        if self._sea is None:
            self.require_grid("heights", "features")
            self._sea = sea_mask(self.centres("heights"), self.layer("features"))
        return self._sea

    @property
    def index(self) -> RegionIndex:
        if self._index is None:
            self.require_grid("regions")
            self._index = build_index(self.layer("regions"), self.sea,
                                      self.regions.records)
        return self._index

    @property
    def neighbours(self) -> Dict[int, List[int]]:
        """Which regions touch which, by packed colour key.

        One pass over the label image comparing each tile with the one to its
        right and the one below - so every shared edge is seen exactly once -
        and the marker labels are skipped, because a settlement pixel touching
        two provinces does not make them neighbours.

        **Four-connected, not eight.** A province that meets another only at a
        corner is not adjacent to it in the engine either: land movement is
        cardinal. Sea is left in rather than filtered out, because a region
        whose only neighbour is the ocean is exactly what someone opening this
        panel wants to be told.

        Land bridges and river crossings connect regions the label image does
        not - that is TWMapReader's finding and it is 16f's rule, not this
        one. This is adjacency on the region layer alone, and the panel says so.

        Measured: 27 ms on DaC (248,370 tiles), 6 ms on vanilla, once, cached.
        """
        if self._neighbours is None:
            self._neighbours = _adjacency(self.index)
        return self._neighbours

    def invalidate(self, *codes: str) -> None:
        """Forget decoded layers and everything derived from them.

        For a layer that changed **on disk**. The paint tool does not use this:
        it changes the image this object is holding, which is a different thing
        - see :meth:`repixel`.
        """
        for c in codes or tuple(self._layers):
            self._layers.pop(c, None)
            self._infos.pop(c, None)
            self._tiles.pop(c, None)
        self._index = None
        self._sea = None
        self._neighbours = None

    def repixel(self, *codes: str) -> None:
        """A layer's pixels changed **in memory**. Drop what was derived.

        The decoded image and its header stay - they are the thing that just
        changed and the thing a save will re-encode - and everything computed
        off them goes, so the next probe, legend or PNG is of the painted map
        rather than of the one that was read.

        The index, the sea mask and the adjacency are dropped only when a layer
        that feeds them moved, because rebuilding them is a quarter of a second
        on DaC and a stroke on ``map_climates.tga`` cannot change which tile
        belongs to which province.
        """
        for c in codes:
            self._tiles.pop(c, None)
        if set(codes) & {"regions", "heights", "features"}:
            self._index = None
            self._sea = None
            self._neighbours = None

    # -- coordinates ---------------------------------------------------------

    def game_xy(self, x: int, y: int) -> Tuple[int, int]:
        """Image coordinates to the ones ``descr_strat.txt`` writes."""
        return x, self.terrain.game_y(y)

    def image_xy(self, x: int, game_y: int) -> Tuple[int, int]:
        """And back. The transform is its own inverse; the names are not."""
        return x, self.terrain.game_y(game_y)

    def probe_pixel(self, x: int, y: int) -> dict:
        """Everything all ten layers say about one tile, named.

        Image coordinates in. Every layer answers in the same shape -
        ``{rgb, name, code_name, problem}`` - so the panel is one loop rather
        than ten special cases, and ``code_name: None`` means *no table this
        toolkit has names this colour*. That is a finding, never a guess: DaC's
        ``map_features.tga`` carries a stray ``(1,1,1)`` and its
        ``map_climates.tga`` five colours no climate declares, and rounding
        either to the nearest known value would hide exactly the thing someone
        opened the probe to see.

        Layers are read through :meth:`tiles`, so the samples are the pixels
        the browser was served and sampled the way the engine samples them -
        ``(2t+1, 2t+1)`` for a ``2W+1`` layer, ``(2t, 2t)`` for a ``2W x 2H``
        one. A layer that is missing, unreadable or the wrong shape answers
        with its reason instead of a colour; a layer with no relationship to
        the tile grid at all (the water surface, the front-end picture) says so
        rather than being sampled at coordinates that mean nothing in it.
        """
        t = self.terrain
        if not t.in_bounds(x, y):
            return {}
        out: dict = {"image": [x, y], "game": list(self.game_xy(x, y)),
                     "marker": "", "layers": []}

        reg = None
        try:
            reg = self.index.at(x, y)
        except MapError as exc:
            out["region"] = {"rgb": None, "key": 0, "name": "", "region_id": -1,
                             "declared": False, "problem": str(exc)}
        else:
            out["region"] = {
                "rgb": list(reg.rgb) if reg else None,
                "key": key(reg.rgb) if reg else 0,
                "name": reg.name if reg else "",
                "region_id": reg.region_id if reg else -1,
                "declared": bool(reg and reg.record is not None),
                "problem": "",
            }
        try:
            out["sea"] = bool(self.sea[y * t.width + x])
        except MapError as exc:
            out["sea"] = None
            out["sea_problem"] = str(exc)

        climates = mapvocab.climate_index(self.mod)
        for ly in LAYERS:
            code = ly["code"]
            row = {"code": code, "label": ly["label"], "file": ly["file"],
                   "rgb": None, "name": "", "code_name": None, "problem": ""}
            out["layers"].append(row)
            if ly["size"] in ("advisory", "free"):
                row["problem"] = ("no relationship to the tile grid, so it has no "
                                  "value at this tile")
                continue
            want = t.expected_size(ly["size"])
            try:
                got = self.layer(code).size
            except MapError as exc:
                row["problem"] = str(exc)
                continue
            if want and got != want:
                row["problem"] = (f"{got[0]}x{got[1]}, expected {want[0]}x{want[1]} - "
                                  "sampling it per tile would be a lie about where "
                                  "its pixels are")
                continue
            rgb = self.tiles(code).getpixel((x, y))
            row["rgb"] = list(rgb)
            if code == "regions":
                if rgb == SETTLEMENT_RGB:
                    out["marker"] = "settlement"
                elif rgb == PORT_RGB:
                    out["marker"] = "port"
            row["name"], row["code_name"] = _colour_name(self, code, rgb, climates)
        return out


# ---------------------------------------------------------------------------
# the map one campaign reads (22b)
#
# The engine takes each map file separately: a campaign folder's own copy wins
# and a file it does not ship is read from world/maps/base (B1's decision).
# Third Age Reforged's Fellowship_Campaign ships the lot - the same 510x487,
# other pixels - so a tile there is judged on its own layers, not the base's.

#: the files a judgement about a tile reads: whose province, sea, what ground.
#: Every DaC and Reforged campaign ships a map_FE.tga and Reforged's imperial
#: one a map_<faction>.tga per faction; none of those decide anything here, and
#: a campaign whose only copies are those reads the base map's object as it is.
MAP_FILES = ("map_regions.tga", "map_heights.tga", "map_ground_types.tga",
             "map_features.tga", Path(TERRAIN_REL).name, Path(REGIONS_REL).name)

_OWN: Dict[Tuple[str, str], Tuple[tuple, "CampaignMap"]] = {}


def campaign_map(mod, campaign: str, base: Optional["CampaignMap"] = None
                 ) -> "CampaignMap":
    """The map ``campaign`` reads: ``base`` when it ships none of its own.

    Kept while none of the files it was read from has changed on disk, so a
    plan pays for decoding a campaign's own layers once rather than per save.
    """
    from .campstrat import CAMPAIGN_DIR_REL, DEFAULT_CAMPAIGN, campaign_rel
    home = Path(mod.data) / CAMPAIGN_DIR_REL / campaign_rel(campaign or DEFAULT_CAMPAIGN)
    own = [n for n in MAP_FILES if (home / n).is_file()]
    if not own:
        return base if base is not None else CampaignMap(mod)
    key = (str(Path(mod.data).resolve()).lower(), str(campaign).lower())
    stamp = tuple(sorted((n, (home / n).stat().st_mtime_ns) for n in own)) + (
        tuple((n, (Path(mod.data) / BASE_REL / n).stat().st_mtime_ns)
              for n in MAP_FILES if n not in own
              and (Path(mod.data) / BASE_REL / n).is_file()),)
    hit = _OWN.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    cm = CampaignMap(mod, home)
    _OWN[key] = (stamp, cm)
    return cm


def map_of(facts, campaign: str = "") -> Optional["CampaignMap"]:
    """The map a fact table's campaign reads, or None when the table has no map.

    What a check about a tile should be judged on: the table's own map, or the
    campaign's copy of any of its files (:func:`campaign_map`).
    """
    cm = getattr(facts, "cm", None)
    if cm is None:
        return None
    try:
        return campaign_map(facts.mod, campaign or facts.campaign, cm)
    except (MapError, OSError):
        return cm


# ---------------------------------------------------------------------------
# the browser's view of the map (16c)
#
# The renderer never sees a TGA. Python decodes, projects and encodes; the
# browser gets PNGs and one JSON manifest, and it owns nothing but the
# compositing and the pointer. That is the "one engine" rule, and it is what
# lets the paint tool's undo, its backups and server-side validation exist
# at all.

#: How a layer's pixels are handed to the browser.
#:
#: ``tile``    one pixel per tile, sampled the way the engine samples it. Every
#:             layer that has a relationship to the grid comes back ``W x H``,
#:             so the composite is one canvas and a picked pixel is a tile.
#: ``native``  the file's own pixels, untouched.
#:
#: Tile fit is what the editor speaks: ``descr_strat.txt`` writes tiles, the
#: region index is one byte per tile, and a stroke paints tiles. It does
#: throw something away and this is where to say so - a ``2W+1`` layer carries
#: values *between* the tile centres (the shared corners the terrain mesh is
#: interpolated across), and tile fit does not show them. ``native`` does.
FITS = ("tile", "native")


def _block_sample(img: Image.Image, width: int, height: int,
                  offset: float) -> Image.Image:
    """Downsample 2:1 by picking one pixel of each 2x2 block, in Pillow's C.

    ``AFFINE`` maps output pixel centre ``x + 0.5`` through the matrix, so a
    scale of 2 with ``offset`` 0 samples input ``2x + 1`` - which is exactly the
    centre rule the ``2W+1`` layers are read by. ``offset`` ``-0.5`` takes
    ``2x`` instead, the top-left of the block, which is all a ``2W x 2H`` layer
    can be said to have: it has no centre pixel, only a block.
    """
    return img.transform((width, height), Image.AFFINE,
                         (2, 0, offset, 0, 2, offset), Image.NEAREST)


#: Draw order, and what the map looks like before anybody touches a control.
#:
#: ``order`` is bottom-first, so the last entry paints over everything. The two
#: defaults are the view the map is actually read in - the ground under the
#: provinces, the provinces half-transparent over it - because a first frame
#: that shows nothing teaches nothing, and both a layer's opacity and its place
#: in the order are visible from the moment the screen opens.
DISPLAY: Dict[str, dict] = {
    "fe":            {"order": 0, "on": False, "opacity": 1.0},
    "water_surface": {"order": 1, "on": False, "opacity": 1.0},
    "heights":       {"order": 2, "on": False, "opacity": 1.0},
    "ground_types":  {"order": 3, "on": True,  "opacity": 1.0},
    "climates":      {"order": 4, "on": False, "opacity": 1.0},
    "roughness":     {"order": 5, "on": False, "opacity": 1.0},
    "regions":       {"order": 6, "on": True,  "opacity": 0.55},
    "trade_routes":  {"order": 7, "on": False, "opacity": 1.0},
    "features":      {"order": 8, "on": False, "opacity": 1.0},
    "fog":           {"order": 9, "on": False, "opacity": 1.0},
}


def tile_view(cm: "CampaignMap", code: str) -> Image.Image:
    """One layer at one pixel per tile, sampled the way the engine samples it.

    ``tile``    already is. ``centre`` takes ``(2t+1, 2t+1)``, the block centre.
    ``double``  takes ``(2t, 2t)``, the block's top-left, because a ``2W x 2H``
                layer has no centre pixel to take.

    ``advisory`` and ``free`` have no relationship to the grid at all, so they
    come back at their own size and the caller is told - :func:`layer_view`'s
    ``aligned`` - that stretching one over the map is a guess, not a mapping.
    """
    img = cm.layer(code)
    rule = LAYER_BY_CODE[code]["size"]
    if rule == "centre":
        return cm.centres(code)
    if rule == "double":
        return _block_sample(img, cm.terrain.width, cm.terrain.height, -0.5)
    return img


def layer_png(cm: "CampaignMap", code: str, fit: str = "tile") -> bytes:
    """One layer as PNG bytes, ready to hand to a canvas.

    Always RGB: DaC's layers decode to RGBA and vanilla's to RGB, and a colour
    the browser picks off the canvas has to be the same triple :mod:`mapvocab`
    names, with no fourth number to disagree about.
    """
    if code not in LAYER_BY_CODE:
        raise MapError(f"no such layer {code!r}")
    if fit not in FITS:
        raise MapError(f"no such fit {fit!r} - it is one of {', '.join(FITS)}")
    img = cm.layer(code) if fit == "native" else tile_view(cm, code)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=False)
    return buf.getvalue()


def layer_rgb(cm: "CampaignMap", code: str, fit: str = "tile") -> Tuple[int, int, bytes]:
    """One layer as ``(width, height, raw RGB bytes)`` - what the browser reads.

    The PNG above is a picture, and a picture is what the browser is entitled to
    change: a page reading pixels back out of a canvas can be handed values that
    are not the file's. Measured on a user's machine after 20c - the hover panel
    said "no region" over most of Third Age Reforged and read dense forest,
    ``0,64,0`` in every table, as ``0,65,1``. Canvas anti-fingerprinting (Brave's
    default shields, Firefox's resist-fingerprinting, several privacy extensions)
    adds exactly that one-step noise to every read, and colour management can
    shift an image the same way. A region is identified by an exact colour, so
    one step is a different region or none. Bytes fetched as bytes are not a
    picture and nothing rewrites them, so the screen reads THESE and only ever
    writes to its canvases.
    """
    if code not in LAYER_BY_CODE:
        raise MapError(f"no such layer {code!r}")
    if fit not in FITS:
        raise MapError(f"no such fit {fit!r} - it is one of {', '.join(FITS)}")
    img = (cm.layer(code) if fit == "native" else tile_view(cm, code)).convert("RGB")
    return img.width, img.height, img.tobytes()


def layer_view(cm: "CampaignMap", code: str) -> dict:
    """What the renderer needs to know about one layer before it asks for it.

    Never raises. A layer that is missing, or whose header will not read, comes
    back ``present: False`` with the reason in ``problem`` - the screen has to
    be able to say *which* file is wrong, and a manifest that died on the first
    bad one would say nothing about the other nine.
    """
    ly = LAYER_BY_CODE[code]
    d = DISPLAY.get(code, {"order": 99, "on": False, "opacity": 1.0})
    b = BLANK.get(code)
    out = {"code": code, "label": ly["label"], "file": ly["file"],
           "size": ly["size"], "required": ly["required"],
           "hotkey": HOTKEYS.get(code, ""),
           "order": d["order"], "on": d["on"], "opacity": d["opacity"],
           "aligned": ly["size"] in ("tile", "double", "centre"),
           "present": False, "problem": "", "fit": "native",
           # which colour on this layer means "nothing here", so the renderer
           # can punch it through and make an overlay of the layer without
           # waiting for the legend to arrive. See BLANK for the sources.
           "blank": ({"rgb": list(b["rgb"]), "key": key(b["rgb"]),
                      "why": b["why"], "sourced": b["sourced"]} if b else None),
           "native": None, "width": 0, "height": 0}
    path = cm.base / ly["file"]
    if not path.exists():
        out["problem"] = "missing" if ly["required"] else "not in this mod"
        return out
    try:
        info = probe(path)
    except TgaError as exc:
        out["problem"] = str(exc)
        return out
    out["present"] = True
    out["native"] = [info.width, info.height]
    want = cm.terrain.expected_size(ly["size"])
    if want and (info.width, info.height) != want:
        # Reported, not corrected. A layer the wrong shape is the classic map
        # crash, and serving it at tile fit would be a lie about it: it would
        # come back the right size with its pixels silently off the grid.
        out["problem"] = f"{info.width}x{info.height}, expected {want[0]}x{want[1]}"
        out["aligned"] = False
    if out["aligned"]:
        out["fit"] = "tile"
        out["width"], out["height"] = cm.terrain.width, cm.terrain.height
    else:
        out["width"], out["height"] = info.width, info.height
    return out


# ---------------------------------------------------------------------------
# the legend (16d)
#
# 16c composited every layer honestly, and that is exactly what made two of
# them useless: map_features.tga is 97.7% black on DaC and 96.4% on vanilla,
# and black there means "nothing here", so ticking it at full opacity hides the
# map under a black sheet with a few rivers drawn on it. The answer is not a
# blend mode, it is a legend - say what each colour in the layer MEANS, and let
# the one that means nothing stop being drawn.
#
# Every colour below is measured on both real maps, and where no reference
# states which colour is the empty one, that is said rather than guessed.

#: The colour that means "there is nothing here on this layer", and where the
#: claim comes from. ``sourced`` is whether a reference states it, or whether
#: it is ours from measuring the two real maps.
#:
#:   features       (0,0,0) is ``none`` in the arbiter's own table. Sourced.
#:   trade_routes   vanilla paints 995 white tiles out of 54,760 and DaC paints
#:                  none at all, so black is the empty one. Measured.
#:   roughness      a greyscale magnitude and black is its zero. DaC's whole
#:                  layer is black; vanilla's is 236 grey levels off it.
#:   fog            white is 87% of vanilla's layer and 98% of DaC's. Which way
#:                  round the engine reads this layer is written down nowhere in
#:                  the four references, so the panel says "the colour most of
#:                  the map is" and claims nothing further.
#:
#: The four layers with a real vocabulary - regions, ground types, climates,
#: heights - have no empty colour, and that is why they have no entry here:
#: black ground is `wilderness`, black heights is sea, and a black region pixel
#: is a settlement marker. Punching any of those through would delete data from
#: the picture, so the checkbox is not offered for them at all.
BLANK: Dict[str, dict] = {
    "features": {"rgb": (0, 0, 0), "sourced": True,
                 "why": "none - no river, ford, source, cliff, volcano or land bridge"},
    "trade_routes": {"rgb": (0, 0, 0), "sourced": False,
                     "why": "no trade route: vanilla marks 995 tiles out of 54,760, "
                            "and DaC marks none at all"},
    "roughness": {"rgb": (0, 0, 0), "sourced": False,
                  "why": "flat - the layer is a greyscale magnitude and black is its zero"},
    "fog": {"rgb": (255, 255, 255), "sourced": False,
            "why": "the colour most of the map is (87% of vanilla, 98% of DaC); no "
                   "reference says which way round the engine reads this layer"},
}

#: How many colours a legend lists before it starts counting instead. Heights
#: has 308 on DaC and roughness 236 on vanilla, and both are magnitudes rather
#: than vocabularies - a list of 308 near-identical greys is not a legend.
LEGEND_MAX = 48

#: …except the region layer, whose colours ARE the vocabulary. DaC has 202 of
#: them and every one is a province someone wants to find, so the ceiling there
#: is the engine's own plus the two markers rather than a display limit.
LEGEND_MAX_REGIONS = mapvocab.MAX_REGION_COLOURS + 56


def _height_name(rgb: Rgb) -> Tuple[str, Optional[str]]:
    """Heights has a rule where the other layers have a table - see mapvocab."""
    if mapvocab.is_sea_height(rgb):
        return (("Sea (pure black)", "sea") if rgb == (0, 0, 0)
                else ("Sea (not greyscale)", "sea"))
    return f"Land, height {rgb[0]} of 255", "land"


def _colour_name(cm: "CampaignMap", code: str, rgb: Rgb,
                 climates: Dict[int, dict]) -> Tuple[str, Optional[str]]:
    """``(what a person would call this colour, its code name)``.

    ``None`` for the code name is the important half: a colour no table claims
    is *reported* as unknown, never rounded to the nearest known one. DaC's
    stray ``(1,1,1)`` in map_features.tga is exactly that - 16f's job is to
    complain about it, and this one's is to make it visible.
    """
    if code == "regions":
        if rgb == SETTLEMENT_RGB:
            return "Settlement marker", "settlement"
        if rgb == PORT_RGB:
            return "Port marker", "port"
        reg = cm.index.by_key.get(key(rgb))
        if reg is not None and reg.record is not None:
            return reg.record.name, reg.record.name
        return "", None
    if code == "heights":
        return _height_name(rgb)
    if code == "ground_types":
        hit = mapvocab.ground_at(rgb)
        return (hit["name"], hit["code"]) if hit else ("", None)
    if code == "features":
        hit = mapvocab.feature_at(rgb)
        if not hit:
            return "", None
        # the table writes `none` as "-", which is right in a picker and reads
        # as a missing value in a legend
        return ("Nothing here" if hit["code"] == "none" else hit["name"]), hit["code"]
    if code == "climates":
        hit = climates.get(key(rgb))
        return (hit["name"], hit["code"]) if hit else ("", None)
    if code == "trade_routes":
        return ("No trade route", "none") if rgb == (0, 0, 0) else ("Trade route", "route")
    if code == "roughness":
        r, g, b = rgb
        if r != g or g != b:
            return "", None
        return ("Flat", "flat") if r == 0 else (f"Roughness {r} of 255", "rough")
    if code == "fog":
        if rgb == (255, 255, 255):
            return "Unmarked", "unmarked"
        if rgb == (0, 0, 0):
            return "Marked", "marked"
        return "", None
    return "", None


def layer_legend(cm: "CampaignMap", code: str) -> dict:
    """Every colour actually in one layer, named, biggest first.

    A census of the pixels the browser was served - tile fit, so the counts are
    tiles and they add up to the tile grid - joined to whatever vocabulary that
    layer has. Three things come out of it that nothing else says:

      * **which colour means nothing**, so the layer can be an overlay instead
        of a sheet laid over the map. That is 16c's one deferred item, and
        :data:`BLANK` is where the claim and its source live.
      * **which colours no table knows.** ``code_name`` is ``None`` for those,
        and they are listed with the rest rather than dropped, because a colour
        nobody declared is the interesting one on a real mod's map.
      * how much of the map each one covers, which is what tells the ocean from
        a hole in the mod at a glance.

    The two pictures - ``water_surface`` and ``map_FE`` - are refused by name.
    They are artwork with no relationship to the tile grid and no vocabulary
    naming their colours; a photograph does not have a legend.
    """
    if code not in LAYER_BY_CODE:
        raise MapError(f"no such layer {code!r}")
    ly = LAYER_BY_CODE[code]
    out: dict = {"code": code, "label": ly["label"], "file": ly["file"],
                 "colours": [], "total": 0, "listed": 0, "more": 0, "note": "",
                 "blank": None}
    if ly["size"] in ("advisory", "free"):
        out["note"] = (f"{ly['file']} is a picture, not a coded layer. It has no "
                       "relationship to the tile grid and no vocabulary names its "
                       "colours, so there is nothing to list.")
        return out
    b = BLANK.get(code)
    if b:
        out["blank"] = {"rgb": list(b["rgb"]), "key": key(b["rgb"]),
                        "why": b["why"], "sourced": b["sourced"]}

    census = cm.tiles(code).getcolors(1 << 20)
    if census is None:
        out["note"] = f"{ly['file']} has more than a million distinct colours."
        return out
    census.sort(key=lambda t: -t[0])
    out["total"] = sum(n for n, _ in census)
    climates = mapvocab.climate_index(cm.mod) if code == "climates" else {}
    blank_key = key(b["rgb"]) if b else None
    cap = LEGEND_MAX_REGIONS if code == "regions" else LEGEND_MAX
    for n, rgb in census[:cap]:
        name, cname = _colour_name(cm, code, rgb, climates)
        out["colours"].append({"rgb": list(rgb), "key": key(rgb), "count": n,
                               "name": name, "code_name": cname,
                               "blank": key(rgb) == blank_key})
    out["listed"] = len(out["colours"])
    out["more"] = max(0, len(census) - cap)
    notes = []
    if out["more"]:
        notes.append(f"{len(census)} distinct colours in {ly['file']}; the {cap} "
                     "largest are listed. A layer carrying this many is a "
                     "magnitude rather than a vocabulary.")
    unknown = sum(1 for c in out["colours"] if c["code_name"] is None)
    if unknown:
        notes.append(f"{unknown} of the colours listed "
                     f"{'is one' if unknown == 1 else 'are ones'} no table this "
                     "toolkit has names.")
    out["note"] = " ".join(notes)
    return out



def sea_pixels(cm: "CampaignMap") -> Dict[int, int]:
    """How many tiles of each region colour the engine treats as sea.

    One pass over the label image and the sea mask together - 6 ms on vanilla,
    43 ms on DaC - and it is what tells the ocean from a province nobody wrote
    down. Both maps have colours ``descr_regions.txt`` never declares, and the
    two kinds are not alike:

        vanilla   four undeclared colours, all four 100% sea. Three of them
                  are near-misses of the ocean's own (41,140,233) -
                  (41,141,243), (41,140,235), (41,141,237) - the same
                  one-channel slips of a lossy paint that 16a found in
                  ``map_climates.tga``.
        DaC       two. The ocean, 73,904 of 73,950 tiles sea, and a 517-tile
                  province at (318,54)-(372,68) with **not one sea tile in
                  it** - which is the hole in the mod 16a reported, now
                  measured rather than inferred.

    Exact, not sampled. 16f owns the rule that turns this into a complaint;
    this is the count it will be built on, and it is here because a screen that
    calls the Atlantic an undeclared province is not worth looking at.
    """
    labels, sea = cm.index.labels, cm.sea
    counts = [0] * len(cm.index.colours)
    for i, lab in enumerate(labels):
        if sea[i]:
            counts[lab] += 1
    return {key(rgb): counts[i] for i, rgb in enumerate(cm.index.colours)}


def region_view(r: Region, sea: int = 0, loc: Optional[Dict[str, str]] = None) -> dict:
    """One region, for the manifest. Image coordinates throughout.

    ``declared`` is whether the colour on the map and a record in
    ``descr_regions.txt`` agree. False is a real state a real mod is in, not an
    error to hide: DaC paints a 517-pixel province the file never declares.
    ``sea`` is how many of its tiles are sea, which is what separates that from
    the ocean - see :func:`sea_pixels`.

    ``loc`` is :func:`shown_names`, and the two words it adds are 20b's doing.
    The manifest is what the find box searches, and searching a map for
    ``Anorien_Province`` when the game and the player both call it Anórien is a
    box only somebody who has read the files can use. Two short strings a
    region, once, against a request per keystroke - which is the rule this
    screen is built on.
    """
    rec = r.record
    loc = loc or {}
    settlement_name = rec.settlement if rec else ""
    return {
        "id": r.region_id, "rgb": list(r.rgb), "key": key(r.rgb),
        "name": r.name, "pixels": r.pixels, "sea": sea,
        "bbox": list(r.bbox), "anchor": list(r.anchor),
        "centroid": [round(r.centroid[0], 1), round(r.centroid[1], 1)],
        "settlement": list(r.settlement) if r.settlement else None,
        "port": list(r.port) if r.port else None,
        "settlement_name": settlement_name,
        "shown": loc.get(r.name, ""),
        "shown_settlement": loc.get(settlement_name, ""),
        "faction": rec.faction if rec else "",
        "rebels": rec.rebels if rec else "",
        "declared": rec is not None,
    }


def _vocab_view(cm: "CampaignMap") -> dict:
    """The three tables that name a colour, small enough to travel with the map.

    17e's hover tooltip names every layer under the cursor, and it does that in
    the browser: a round trip per pointer event is the one thing this screen's
    rules exist to prevent, which is why 16d put the full probe behind a click.
    These are the only tables it cannot derive - the arbiter's ground types and
    features, and this mod's own climates, because DaC renames all twelve. Three
    dozen rows in total, sent once with the manifest.

    The layers that have a *rule* rather than a table - heights, roughness,
    trade routes, fog - are not here: their rule is stated in
    :func:`_colour_name` and mirrored in `cmapNameColour`, and neither end
    nearest-colour matches. A colour no table claims is reported as unnamed.

    ``rivers`` is 20a's: which of the feature codes make up a river network, so
    the screen's river overlay draws the tiles :mod:`unittransfer.mapcheck`
    walks rather than a second opinion about which blue is which.
    """
    return {
        "ground_types": mapvocab.GROUND_TYPES,
        "features": mapvocab.FEATURES,
        "climates": mapvocab.climates(cm.mod),
        "rivers": list(mapvocab.RIVER_CODES),
    }


def _terrain_view(t: Terrain) -> dict:
    """``descr_terrain.txt``'s numbers, for the inspector 16d builds."""
    return {"min_sea_height": t.min_sea_height, "max_land_height": t.max_land_height,
            "roughness_min": t.roughness_min, "roughness_max": t.roughness_max,
            "fractal_multiplier": t.fractal_multiplier,
            "latitude_min": t.latitude_min, "latitude_max": t.latitude_max}


def view(cm: "CampaignMap", name: str = "") -> dict:
    """The whole manifest in one call: what to draw, and what a pixel means.

    Everything here is small and everything here is wanted before the first
    frame, so it is one request rather than five. The pixels are not in it -
    they arrive as PNG, one request per layer, cached on disk.

    The region table is why picking costs nothing at run time. The browser
    reads the colour under the cursor off its own copy of ``map_regions.tga``
    and looks it up here by packed key; there is no round trip per pixel, and
    no second parser to disagree with this one.
    """
    t = cm.terrain
    layers = sorted((layer_view(cm, ly["code"]) for ly in LAYERS),
                    key=lambda d: d["order"])
    try:
        idx = cm.index
    except MapError as exc:
        # A map whose layers disagree still has a manifest, and it is the only
        # thing that will tell anyone which file to fix. The layer list above is
        # built from headers alone and already carries the sizes; what is lost
        # is the region table, so picking is off until the shape is fixed.
        return {"mod": name or getattr(cm.mod, "name", ""),
                "width": t.width, "height": t.height, "tiles": t.tiles,
                "terrain": _terrain_view(t), "layers": layers, "regions": [],
                "vocab": _vocab_view(cm),
                "markers": {"settlement": list(SETTLEMENT_RGB),
                            "port": list(PORT_RGB)},
                "findings": {"layers": cm.check_layers() or [str(exc)],
                             "unclaimed": [], "undeclared_land": [],
                             "sea_colours": 0, "empty_records": [],
                             "orphan_settlements": [], "extra_settlements": [],
                             "extra_ports": [], "undecided_ports": [],
                             "record_problems": [{"name": r.name,
                                                  "problems": r.problems}
                                                 for r in cm.regions.records
                                                 if r.problems]}}
    # numbered regions first, in engine order, then the ones the engine skips
    regions = sorted(idx.regions, key=lambda r: (r.region_id < 0, r.region_id))
    sea = sea_pixels(cm)
    # 20b: read once for the whole manifest, not once a region. A mod with no
    # names file at all answers an empty dict and every region shows its code
    # name, which is what the game does too.
    loc = shown_names(cm.mod)
    # Which undeclared colours are the ocean, and which are holes in the mod.
    # The line is drawn at half, and the measurements say it is nowhere near
    # anything: vanilla's four undeclared colours are 100% sea, DaC's ocean is
    # 99.94% (46 of its 73,950 tiles are the underwater land the region scan
    # skips), and DaC's undeclared province is 0%. Three orders of magnitude of
    # daylight either side, so the exact threshold decides nothing.
    undeclared = [r for r in idx.regions if r.record is None]
    is_sea = lambda r: r.pixels and sea.get(key(r.rgb), 0) * 2 >= r.pixels
    return {
        "mod": name or getattr(cm.mod, "name", ""),
        "width": t.width, "height": t.height, "tiles": t.tiles,
        "terrain": _terrain_view(t),
        "layers": layers,
        "vocab": _vocab_view(cm),
        "regions": [region_view(r, sea.get(key(r.rgb), 0), loc) for r in regions],
        "markers": {"settlement": list(SETTLEMENT_RGB), "port": list(PORT_RGB)},
        "findings": {
            "layers": cm.check_layers(),
            "unclaimed": [list(c) for c in idx.unclaimed],
            "undeclared_land": [{"rgb": list(r.rgb), "pixels": r.pixels,
                                 "sea": sea.get(key(r.rgb), 0),
                                 "bbox": list(r.bbox), "anchor": list(r.anchor)}
                                for r in undeclared if not is_sea(r)],
            "sea_colours": sum(1 for r in undeclared if is_sea(r)),
            "empty_records": [r.name for r in idx.empty_records],
            "orphan_settlements": [list(p) for p in idx.orphan_settlements],
            "extra_settlements": [list(p) for p in idx.extra_settlements],
            "extra_ports": [list(p) for p in idx.extra_ports],
            "undecided_ports": [list(p) for p in idx.undecided_ports],
            "record_problems": [{"name": r.name, "problems": r.problems}
                                for r in cm.regions.records if r.problems],
        },
    }


# ---------------------------------------------------------------------------
# the region record, written (16d)
#
# Rule 3 of this phase - parse once, splice after. An edit rewrites the ONE line
# the field came from and nothing else, so a file full of hand formatting comes
# back out with its comments, its tabs and its CRLF intact. Demir's editor
# re-parses the whole of descr_strat.txt eight to ten times to save one faction
# detail; this writes a line.
#
# WHAT IS NOT EDITABLE HERE, AND WHY. A region's own name and its settlement's
# name are keys: descr_strat.txt, descr_win_conditions.txt, the campaign script,
# the region and settlement name text file and every `legion:` line in this very
# file point at them, so renaming one in a box would orphan all of it. That is
# the same ruling a trait, an ancillary and a building line already make, and
# the text pane makes it too. The colour is not editable either, for a different
# reason: it is the map's own pixels, and changing the number without repainting
# them would hand the region to no tiles at all. Repainting them is the brush's
# job, in :mod:`unittransfer.campaint`.

#: The fields of a record this session will write, in the order they appear.
#: `legion` is in the list and may be absent from a record - the two forms of
#: the file differ by exactly that line - so adding and removing it is part of
#: the job rather than a refusal.
EDITABLE = ("legion", "faction", "rebels", "resources", "triumph", "farming",
            "religions")

#: Geomod's manual, on the first of the two bare numbers: "Victory ... leave it
#: at 5, other numbers may cause a crash". Vanilla writes 5 on 110 of its 112
#: regions. So a different value is a warning with a source, not a refusal.
TRIUMPH_USUAL = 5

#: …and on the second: "Agriculture ... 4 is approximately average, 6-7 highly
#: fertile". Nothing states a ceiling, so the check is for a number outside the
#: range any real file uses rather than for an engine limit nobody wrote down.
FARMING_RANGE = (0, 7)


def _indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _comment_of(line: str) -> str:
    """The ``;`` tail of a line, kept through an edit because it is the modder's."""
    at = line.find(";")
    return line[at:] if at >= 0 else ""


def _set_line(lines: List[str], idx: int, value: str) -> None:
    """Rewrite one line's value, keeping its indent and its trailing comment."""
    old = lines[idx]
    tail = _comment_of(old)
    lines[idx] = _indent_of(old) + value + ((" " + tail) if tail else "")


def _religions_text(religions: Dict[str, int]) -> str:
    inner = " ".join(f"{n} {v}" for n, v in religions.items())
    return "religions { " + inner + " }" if inner else "religions { }"


def parse_block(text: str) -> RegionRecord:
    """One record's own lines, read. Raises :class:`MapError` for anything else.

    The header line is the one that is not indented, so a block that has lost
    its first line - or that carries two records - is caught here rather than
    quietly writing one region's values into another's lines.
    """
    rf = parse_regions(text if text.endswith("\n") else text + "\n")
    real = [r for r in rf.records if r.name]
    if not real:
        raise MapError("this is not a region record - no unindented region name "
                       "line to start it")
    if len(real) > 1:
        raise MapError(f"this is {len(real)} region records, not one: "
                       + ", ".join(r.name for r in real[:4]))
    return real[0]


def render_block(base: str, edits: dict) -> str:
    """``base`` with ``edits`` spliced into it, line by line.

    ``edits`` is the panel's own save body and the text pane takes the same
    road, so what the pane shows is what a save would write - down to the tab
    the mod indents with and the ``; kept from 2007`` on the end of a line.

    Three of the fields can be absent from a record and present in the edit, so
    this inserts a line where the record has none: ``legion:`` goes straight
    under the name (which is where both real forms of the file put it), and a
    resource line goes immediately above the triumph value. Clearing a legion
    removes its line rather than leaving ``legion:`` with nothing after it.
    """
    text = base if base.endswith("\n") else base + "\n"
    rec = parse_block(text)
    lines, newline, trailing = _split_lines(text)
    drop: List[int] = []
    insert: List[Tuple[int, str]] = []
    # the indent this record actually uses, so an inserted line matches its
    # neighbours instead of announcing itself
    body = [lines[i] for i in range(rec.span[0] + 1, min(rec.span[1], len(lines) - 1) + 1)
            if lines[i].strip()]
    indent = _indent_of(body[0]) if body else "\t"

    if "legion" in edits:
        want = str(edits["legion"] or "").strip()
        if rec.legion_line >= 0 and want:
            _set_line(lines, rec.legion_line, f"legion: {want}")
        elif rec.legion_line >= 0:
            drop.append(rec.legion_line)
        elif want:
            insert.append((rec.name_line + 1, f"{indent}legion: {want}"))

    for slot in ("faction", "rebels"):
        if slot not in edits:
            continue
        at = getattr(rec, f"{slot}_line")
        want = str(edits[slot] or "").strip()
        if at < 0:
            raise MapError(f"this record has no {slot} line to write to - it is "
                           "the short wasteland form, and the arbiter says a "
                           "wasteland has no settlement, creator or rebel type")
        if not want:
            raise MapError(f"a region's {slot} cannot be blank")
        _set_line(lines, at, want)

    if "resources" in edits:
        res = [str(r).strip() for r in (edits["resources"] or []) if str(r).strip()]
        line = ", ".join(res)
        if rec.resources_line >= 0:
            if res:
                _set_line(lines, rec.resources_line, line)
            else:
                drop.append(rec.resources_line)
        elif res:
            at = rec.triumph_line if rec.triumph_line >= 0 else rec.rgb_line + 1
            insert.append((at, indent + line))

    for slot in ("triumph", "farming"):
        if slot not in edits:
            continue
        at = getattr(rec, f"{slot}_line")
        try:
            n = int(str(edits[slot]).strip())
        except (TypeError, ValueError):
            raise MapError(f"{slot} must be a whole number, "
                           f"not {edits[slot]!r}") from None
        if at < 0:
            raise MapError(f"this record has no {slot} line to write to")
        _set_line(lines, at, str(n))

    if "religions" in edits:
        rel: Dict[str, int] = {}
        for name, value in (edits["religions"] or {}).items():
            name = str(name).strip()
            if not name:
                continue
            try:
                rel[name] = int(str(value).strip() or 0)
            except ValueError:
                raise MapError(f"religion {name} must be a whole "
                               f"percentage, not {value!r}") from None
        if rec.religions_line < 0:
            raise MapError("this record has no religions line to write to")
        _set_line(lines, rec.religions_line, _religions_text(rel))

    for at, line in sorted(insert, reverse=True):
        lines.insert(at, line)
    for at in sorted(drop, reverse=True):
        lines.pop(at)
    return newline.join(lines) + (newline if trailing else "")


def block_fields(text: str) -> List[Tuple[str, str]]:
    """``[(label, value)]`` for one record, in the order its lines appear."""
    rec = parse_block(text)
    rows: List[Tuple[int, str, str]] = [(rec.name_line, "name", rec.name)]
    for slot in ("legion", "settlement", "faction", "rebels"):
        at = getattr(rec, f"{slot}_line")
        if at >= 0:
            rows.append((at, slot, getattr(rec, slot)))
    if rec.rgb_line >= 0:
        rows.append((rec.rgb_line, "rgb", " ".join(str(v) for v in rec.rgb)))
    if rec.resources_line >= 0:
        rows.append((rec.resources_line, "resources", ", ".join(rec.resources)))
    for slot in ("triumph", "farming"):
        at = getattr(rec, f"{slot}_line")
        if at >= 0:
            rows.append((at, slot, str(getattr(rec, slot))))
    if rec.religions_line >= 0:
        rows.append((rec.religions_line, "religions",
                     " ".join(f"{n} {v}" for n, v in rec.religions.items())))
    rows.sort()
    return [(label, value) for _, label, value in rows]


def block_spans(text: str) -> Dict[str, List[List[int]]]:
    """``{label: [[first, last]]}``, 1-based, for one record.

    One line each, because that is what this format is: every field IS a line,
    which is also why an edit here can be a splice rather than a re-render.
    """
    rec = parse_block(text)
    spans: Dict[str, List[List[int]]] = {}
    for slot in ("name", "legion", "settlement", "faction", "rebels", "rgb",
                 "resources", "triumph", "farming", "religions"):
        at = getattr(rec, f"{slot}_line")
        if at >= 0:
            spans[slot] = [[at + 1, at + 1]]
    return spans


def record_text(rf: RegionsFile, rec: RegionRecord) -> str:
    """The record's own lines, exactly as the file holds them.

    The span runs to the line before the next record's header, comments and
    blank lines included, because those belong to the record a person is
    looking at and a save that dropped them would be a save that edits things
    nobody asked it to.
    """
    first, last = rec.span
    return rf.newline.join(rf.lines[first:last + 1]) + rf.newline


def replace_record(rf: RegionsFile, rec: RegionRecord, block: str) -> str:
    """The whole file with one record's lines swapped for ``block``."""
    first, last = rec.span
    body, _, _ = _split_lines(block if block.endswith("\n") else block + "\n")
    while body and not body[-1].strip():
        body.pop()
    lines = rf.lines[:first] + body + rf.lines[last + 1:]
    return rf.newline.join(lines) + (rf.newline if rf.trailing_newline else "")


def check_record(rec: RegionRecord, vocab: Optional[dict] = None) -> List[dict]:
    """What is wrong with one record. ``fatal`` is what stops a save.

    Two of these are crashes with a source behind them and the rest are
    warnings, and the difference is kept because a real mod's file is full of
    the warnings. The religion total is the one everybody meets: the arbiter
    says the percentages must sum to 100 or the game crashes on load, and
    nothing in the file or the game says which of ten numbers is wrong, so it
    is refused at the point where the person can still see what they typed.
    """
    v = vocab or {}
    out: List[dict] = []

    def add(fatal: bool, field_name: str, message: str) -> None:
        at = getattr(rec, f"{field_name}_line", -1)
        out.append({"fatal": fatal, "field": field_name, "message": message,
                    "line": at + 1})

    for problem in rec.problems:
        add(False, "name", problem)

    if rec.religions_line >= 0:
        total = rec.religion_total
        if total != 100:
            add(True, "religions",
                f"the religion percentages total {total}, and the game crashes on "
                f"load unless they total 100 ({total - 100:+d})")
        for name, value in rec.religions.items():
            if value < 0:
                add(True, "religions", f"{name} is {value}; a percentage cannot be "
                                       "negative")
        known = {r.lower() for r in (v.get("religions") or ())}
        if known:
            for name in rec.religions:
                if name.lower() not in known:
                    add(False, "religions",
                        f"{name} is not one of the religions descr_religions.txt "
                        "declares, so the game reads the line and ignores it")

    if rec.triumph_line >= 0 and rec.triumph != TRIUMPH_USUAL:
        add(False, "triumph",
            f"triumph value {rec.triumph}. Geomod's manual says to leave it at "
            f"{TRIUMPH_USUAL}, and that other numbers may cause a crash")
    lo, hi = FARMING_RANGE
    if rec.farming_line >= 0 and not lo <= rec.farming <= hi:
        add(False, "farming",
            f"base farming level {rec.farming} is outside {lo}-{hi}; the manual "
            "calls 4 average and 6-7 highly fertile")

    rebels = {r.lower() for r in (v.get("rebels") or ())}
    if rebels and rec.rebels and rec.rebels.lower() not in rebels:
        add(False, "rebels",
            f"{rec.rebels} is not a rebel type descr_rebel_factions.txt declares")
    factions = {f.lower() for f in (v.get("factions") or ())}
    if factions and rec.faction and rec.faction.lower() not in factions:
        add(False, "faction",
            f"{rec.faction} is not a faction this mod has")

    hidden = {h.lower() for h in (v.get("hidden_resources") or ())}
    trade = {t.lower() for t in (v.get("trade_resources") or ())}
    if hidden or trade:
        for name in rec.resources:
            if name.lower() not in hidden and name.lower() not in trade:
                add(False, "resources",
                    f"{name} is neither a hidden resource the EDB declares nor a "
                    "trade resource descr_sm_resources.txt names")
    seen = set()
    for name in rec.resources:
        if name.lower() in seen:
            add(False, "resources", f"{name} is listed twice")
        seen.add(name.lower())
    return out


def region_vocab(mod) -> dict:
    """Every list the region panel offers a value from, in one call.

    All four come out of the modules that own those files rather than from a
    regex beside them - the one-engine rule, same as :mod:`edbvocab`'s three.
    A mod missing one of the files gets an empty list, and an empty list turns
    the picker into a plain box rather than into a refusal.
    """
    from . import edbvocab, minorfiles
    out = {"religions": [], "rebels": [], "trade_resources": [],
           "hidden_resources": [], "factions": [], "faction_labels": {}}
    try:
        out["religions"] = list(minorfiles.religion_names(mod))
    except Exception:                                  # noqa: BLE001 - a mod file
        pass                                           # that will not read is not
    try:                                               # a reason to lose the panel
        out["rebels"] = sorted(r.name for r in
                               minorfiles.parse_rebels(_read_mod_text(
                                   mod, minorfiles.REBELS.rel)).records)
    except Exception:                                  # noqa: BLE001
        pass
    try:
        out["trade_resources"] = sorted(edbvocab.resources(mod))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        out["hidden_resources"] = sorted(mod.edb.hidden_resources)
    except Exception:                                  # noqa: BLE001
        pass
    try:
        out["factions"] = sorted(mod.faction_cultures)
        out["faction_labels"] = {f: mod.faction_label(f) for f in out["factions"]}
    except Exception:                                  # noqa: BLE001
        pass
    return out


def _read_mod_text(mod, rel: str) -> str:
    from .keyblock import read_text
    try:
        return read_text(mod.data / rel, ENCODING)
    except OSError:
        return ""


REGION_NAMES_REL = "text/imperial_campaign_regions_and_settlement_names.txt"


def shown_names(mod) -> Dict[str, str]:
    """``{code name: what the player reads}`` for regions and settlements.

    The same UTF-16 file :mod:`edbvocab` reads. It is here as well because the
    panel names a region twice - the words on the campaign map and the key the
    rest of the mod points at - and showing only the second is what makes a
    region editor feel like a hex editor.
    """
    from . import edbvocab
    text = edbvocab._read_utf16(mod.data / REGION_NAMES_REL)
    if not text:
        return {}
    return {k.strip(): v.strip()
            for k, v in re.findall(r"^\{([^}]+)\}(.*)$", text, re.M)}


def region_detail(cm: "CampaignMap", name: str) -> dict:
    """One region, everything the panel shows, in one call.

    Three sources joined: the record in ``descr_regions.txt`` (editable), what
    the pixels say (read-only here - the brush is what moves them) and every
    picker in the panel offers. The neighbours come from the region layer alone
    - land bridges and river crossings connect provinces the pixels do not, and
    that is 16f's rule, not this one.
    """
    rec = cm.regions.by_name(name)
    if rec is None:
        raise MapError(f"no region called {name!r} in descr_regions.txt")
    loc = shown_names(cm.mod)
    vocab = region_vocab(cm.mod)
    out = {
        "name": rec.name,
        "shown": loc.get(rec.name, ""),
        "settlement": rec.settlement,
        "settlement_shown": loc.get(rec.settlement, ""),
        "legion": rec.legion,
        "faction": rec.faction,
        "rebels": rec.rebels,
        "rgb": list(rec.rgb),
        "key": rec.rgb_key,
        "resources": list(rec.resources),
        "triumph": rec.triumph,
        "farming": rec.farming,
        "religions": dict(rec.religions),
        "religion_total": rec.religion_total,
        "wasteland": rec.wasteland,
        "has": {slot: getattr(rec, f"{slot}_line") >= 0
                for slot in ("legion", "settlement", "faction", "rebels", "rgb",
                             "resources", "triumph", "farming", "religions")},
        "lines": [rec.span[0] + 1, rec.span[1] + 1],
        "text": record_text(cm.regions, rec),
        "findings": check_record(rec, vocab),
        "vocab": vocab,
        "file": REGIONS_REL,
        "pixels": None,
    }
    hidden = {h.lower() for h in vocab["hidden_resources"]}
    out["hidden_resources"] = [r for r in rec.resources if r.lower() in hidden]
    out["trade_resources"] = [r for r in rec.resources if r.lower() not in hidden]
    try:
        reg = cm.index.by_key.get(rec.rgb_key)
    except MapError as exc:
        out["pixels_problem"] = str(exc)
        return out
    out["pixels_problem"] = ""
    if reg is None:
        # legal to write and fatal to play: 16f's rule, said here because this
        # is the screen where somebody can see it and fix it
        out["pixels"] = {"count": 0, "region_id": -1}
        return out
    names = {}
    try:
        names = {key(r.rgb): r for r in cm.index.regions}
        near = cm.neighbours.get(rec.rgb_key, [])
    except MapError as exc:
        out["pixels_problem"] = str(exc)
        near = []
    out["pixels"] = {
        "count": reg.pixels,
        "region_id": reg.region_id,
        "bbox": list(reg.bbox),
        "anchor": list(reg.anchor),
        "centroid": [round(reg.centroid[0], 1), round(reg.centroid[1], 1)],
        "settlement": list(reg.settlement) if reg.settlement else None,
        "settlement_game": (list(cm.game_xy(*reg.settlement))
                            if reg.settlement else None),
        "port": list(reg.port) if reg.port else None,
        "port_game": list(cm.game_xy(*reg.port)) if reg.port else None,
        "sea": sea_pixels(cm).get(rec.rgb_key, 0),
        "neighbours": [{"key": k, "rgb": list(names[k].rgb),
                        "name": names[k].name,
                        "region_id": names[k].region_id,
                        "declared": names[k].record is not None}
                       for k in near if k in names],
    }
    return out


@dataclass
class RegionPlan:
    """One region's save, worked out without touching the disk."""

    mod: object = None
    name: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the record's new lines, for the preview
    block: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"edit region {self.name} in {getattr(self.mod, 'name', '?')} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"name": self.name, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "block": self.block,
                "ok": not self.errors and bool(self.text)}


def _describe(before: RegionRecord, after: RegionRecord) -> List[str]:
    """What changed, said the way somebody would say it out loud."""
    out: List[str] = []
    for slot, label in (("legion", "legion"), ("faction", "creator faction"),
                        ("rebels", "rebel type")):
        a, b = getattr(before, slot), getattr(after, slot)
        if a != b:
            out.append(f"{label}: {a or '(none)'} -> {b or '(none)'}")
    if before.resources != after.resources:
        gone = [r for r in before.resources if r not in after.resources]
        new = [r for r in after.resources if r not in before.resources]
        if new:
            out.append("resources added: " + ", ".join(new))
        if gone:
            out.append("resources removed: " + ", ".join(gone))
    if before.triumph != after.triumph:
        out.append(f"triumph value: {before.triumph} -> {after.triumph}")
    if before.farming != after.farming:
        out.append(f"base farming level: {before.farming} -> {after.farming}")
    if before.religions != after.religions:
        for name in sorted(set(before.religions) | set(after.religions)):
            a = before.religions.get(name)
            b = after.religions.get(name)
            if a != b:
                out.append(f"religion {name}: {a if a is not None else '(none)'}"
                           f" -> {b if b is not None else '(none)'}")
        out.append(f"religions now total {after.religion_total}")
    return out


def plan_region(mod, body: dict) -> RegionPlan:
    """Work out the whole new ``descr_regions.txt`` for one save.

    ``body`` is ``{mod, region, edits, raw_block}``. ``raw_block`` is text the
    user hand-edited in the Code View, and it wins over ``edits`` and reaches
    disk verbatim - the same ruling every other editor in this toolkit makes.

    Nothing is written. What comes back is the whole file as it would be, the
    record as it would read, and the reasons it would be refused.
    """
    p = RegionPlan(mod=mod, name=str(body.get("region") or "").strip())
    try:
        rf = read_regions(mod)
    except MapError as exc:
        p.errors.append(str(exc))
        return p
    p.path = rf.path
    rec = rf.by_name(p.name)
    if rec is None:
        p.errors.append(f"no region called {p.name!r} in descr_regions.txt")
        return p

    base = record_text(rf, rec)
    raw = str(body.get("raw_block") or "")
    try:
        block = raw if raw.strip() else render_block(base, dict(body.get("edits") or {}))
        after = parse_block(block)
    except MapError as exc:
        p.errors.append(str(exc))
        return p
    if after.name != rec.name:
        p.errors.append(
            f"this region is `{rec.name}` - renaming it HERE would orphan every "
            "descr_strat.txt settlement, win condition, mercenary pool, script "
            "line and `legion:` entry that names it. The Rename button beside "
            "the name follows all of them at once (19b)")
        return p
    if after.rgb != rec.rgb:
        p.errors.append(
            f"this region is painted {rec.rgb[0]} {rec.rgb[1]} {rec.rgb[2]} on "
            "map_regions.tga. Changing the number here without repainting the "
            "pixels would leave the region with no tiles at all - arm the "
            "brush and repaint them instead")
        return p
    if after.settlement != rec.settlement:
        p.errors.append(
            f"this settlement is `{rec.settlement}` - the lookup file, the "
            "settlement name text file and the campaign script point at that "
            "name. The Rename button beside it follows the first two and "
            "reports the third (19b). Measured over both installed mods, "
            "descr_strat.txt is NOT one of them: a settlement block names its "
            "province and never itself")
        return p

    vocab = region_vocab(mod)
    p.findings = check_record(after, vocab)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.block = block
    p.changes = _describe(rec, after)
    text = replace_record(rf, rec, block)
    p.text = "" if text == rf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def apply_region(p: RegionPlan) -> dict:
    """Write a planned save, with the same backups and undo as any other job.

    The old ``descr_regions.txt`` goes to ``config/backups/<id>/data/…`` and
    the manifest goes in the transfer log, so the Log's Undo puts it back
    byte-exact.

    ``map.rwm`` is deleted, and that is not housekeeping: the game reads the
    compiled binary in preference to the text files, so a mod whose
    ``descr_regions.txt`` has changed under a stale ``map.rwm`` loads the old
    map and shows none of the edit. It goes into the backup set like everything
    else, so an undo puts it back too.
    """
    import shutil
    import time

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [], "deleted": []}

    def keep(rel: str) -> Path:
        target = Path(mod.data) / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    target = keep(REGIONS_REL)
    write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rwm = Path(mod.data) / RWM_REL
    if rwm.exists():
        keep(RWM_REL)
        rwm.unlink()
        manifest["deleted"].append(RWM_REL)
        file_op("DELETE", rwm, "stale compiled map - the game would load it instead")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        "action": "region",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("REGION %s in %s - %d change(s), id=%s",
             p.name, mod.name, len(p.changes), tid)
    return {"id": tid, "region": p.name, "record": rec}
