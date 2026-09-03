"""The campaign map, read: the terrain header, the ten layers and the regions.

This is the read half of the map editor's engine. Nothing here paints, saves or
validates - 16e and 16f own those - but everything they do stands on the index
this module builds, so the rules it gets right are the rules the whole editor
gets right.

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
    """
    lines, newline, trailing = _split_lines(text)
    out = RegionsFile(lines=lines, newline=newline, trailing_newline=trailing)

    def is_header(ln: str) -> bool:
        if not ln.strip() or ln.lstrip().startswith(";"):
            return False
        if ln[:1] in (" ", "\t"):
            return False
        # Third Age 6 writes its religions line flush left too; treating that as
        # a new region both loses the religions and invents a phantom record
        return not ln.lstrip().lower().startswith("religions")

    starts = [i for i, ln in enumerate(lines) if is_header(ln)]
    for n, start in enumerate(starts):
        end = (starts[n + 1] - 1) if n + 1 < len(starts) else len(lines) - 1
        out.records.append(_parse_record(lines, start, end))
    return out


def _parse_record(lines: List[str], start: int, end: int) -> RegionRecord:
    rec = RegionRecord(name=lines[start].strip(), name_line=start, span=(start, end))

    body: List[Tuple[int, str]] = []
    for i in range(start + 1, end + 1):
        s = lines[i].split(";", 1)[0].strip()
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


class CampaignMap:
    """One mod's campaign map, read on demand.

    Layers are decoded the first time they are asked for and kept, because the
    editor asks for the same three over and over and the whole set is only
    117 ms; the index is built once and rebuilt only when something paints.
    """

    def __init__(self, mod):
        self.mod = mod
        self.base = mod.data / BASE_REL
        self.terrain = read_terrain(mod)
        self.regions = read_regions(mod)
        self._layers: Dict[str, Image.Image] = {}
        self._infos: Dict[str, TgaInfo] = {}
        self._index: Optional[RegionIndex] = None
        self._sea: Optional[bytes] = None

    # -- layers --------------------------------------------------------------

    def path(self, code: str) -> Path:
        return self.base / LAYER_BY_CODE[code]["file"]

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
            p = self.base / ly["file"]
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

    def invalidate(self, *codes: str) -> None:
        """Forget decoded layers and everything derived from them.

        The paint tool calls this after it writes; keeping a stale index would
        put the next stroke on the wrong region.
        """
        for c in codes or tuple(self._layers):
            self._layers.pop(c, None)
            self._infos.pop(c, None)
        self._index = None
        self._sea = None

    # -- coordinates ---------------------------------------------------------

    def game_xy(self, x: int, y: int) -> Tuple[int, int]:
        """Image coordinates to the ones ``descr_strat.txt`` writes."""
        return x, self.terrain.game_y(y)

    def image_xy(self, x: int, game_y: int) -> Tuple[int, int]:
        """And back. The transform is its own inverse; the names are not."""
        return x, self.terrain.game_y(game_y)

    def probe_pixel(self, x: int, y: int) -> dict:
        """Everything every layer says about one tile, named, for the inspector.

        Image coordinates in. Values come back as ``{code, name, rgb}`` so the
        UI can show the localised name with the code name in brackets, and an
        unknown colour comes back with ``code: None`` rather than a guess.
        """
        t = self.terrain
        if not t.in_bounds(x, y):
            return {}
        out: dict = {"image": (x, y), "game": self.game_xy(x, y)}

        reg = self.index.at(x, y)
        out["region"] = {
            "rgb": reg.rgb if reg else None,
            "name": reg.name if reg else "",
            "region_id": reg.region_id if reg else -1,
        }
        px = self.layer("regions").convert("RGB").getpixel((x, y))
        if px == SETTLEMENT_RGB:
            out["marker"] = "settlement"
        elif px == PORT_RGB:
            out["marker"] = "port"

        for code, table in (("ground_types", mapvocab.ground_at),
                            ("features", mapvocab.feature_at)):
            colour = self.centres(code).convert("RGB").getpixel((x, y))
            hit = table(colour)
            out[code] = {"rgb": colour, "code": hit["code"] if hit else None,
                         "name": hit["name"] if hit else ""}

        colour = self.centres("climates").convert("RGB").getpixel((x, y))
        hit = mapvocab.climate_index(self.mod).get(key(colour))
        out["climates"] = {"rgb": colour, "code": hit["code"] if hit else None,
                           "name": hit["name"] if hit else ""}

        out["sea"] = bool(self.sea[y * t.width + x])
        return out


# ---------------------------------------------------------------------------
# the browser's view of the map (16c)
#
# The renderer never sees a TGA. Python decodes, projects and encodes; the
# browser gets PNGs and one JSON manifest, and it owns nothing but the
# compositing and the pointer. That is the "one engine" rule, and it is what
# lets 16e's undo, backups and server-side validation exist at all.

#: How a layer's pixels are handed to the browser.
#:
#: ``tile``    one pixel per tile, sampled the way the engine samples it. Every
#:             layer that has a relationship to the grid comes back ``W x H``,
#:             so the composite is one canvas and a picked pixel is a tile.
#: ``native``  the file's own pixels, untouched.
#:
#: Tile fit is what the editor speaks: ``descr_strat.txt`` writes tiles, the
#: region index is one byte per tile, and a stroke in 16e paints tiles. It does
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


def layer_view(cm: "CampaignMap", code: str) -> dict:
    """What the renderer needs to know about one layer before it asks for it.

    Never raises. A layer that is missing, or whose header will not read, comes
    back ``present: False`` with the reason in ``problem`` - the screen has to
    be able to say *which* file is wrong, and a manifest that died on the first
    bad one would say nothing about the other nine.
    """
    ly = LAYER_BY_CODE[code]
    d = DISPLAY.get(code, {"order": 99, "on": False, "opacity": 1.0})
    out = {"code": code, "label": ly["label"], "file": ly["file"],
           "size": ly["size"], "required": ly["required"],
           "order": d["order"], "on": d["on"], "opacity": d["opacity"],
           "aligned": ly["size"] in ("tile", "double", "centre"),
           "present": False, "problem": "", "fit": "native",
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


def region_view(r: Region, sea: int = 0) -> dict:
    """One region, for the manifest. Image coordinates throughout.

    ``declared`` is whether the colour on the map and a record in
    ``descr_regions.txt`` agree. False is a real state a real mod is in, not an
    error to hide: DaC paints a 517-pixel province the file never declares.
    ``sea`` is how many of its tiles are sea, which is what separates that from
    the ocean - see :func:`sea_pixels`.
    """
    rec = r.record
    return {
        "id": r.region_id, "rgb": list(r.rgb), "key": key(r.rgb),
        "name": r.name, "pixels": r.pixels, "sea": sea,
        "bbox": list(r.bbox), "anchor": list(r.anchor),
        "centroid": [round(r.centroid[0], 1), round(r.centroid[1], 1)],
        "settlement": list(r.settlement) if r.settlement else None,
        "port": list(r.port) if r.port else None,
        "settlement_name": rec.settlement if rec else "",
        "faction": rec.faction if rec else "",
        "rebels": rec.rebels if rec else "",
        "declared": rec is not None,
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
        "regions": [region_view(r, sea.get(key(r.rgb), 0)) for r in regions],
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
