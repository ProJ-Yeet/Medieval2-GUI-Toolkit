"""What a pixel on each map layer is allowed to mean.

Same job as :mod:`unittransfer.edbvocab` and the same shape - a code name, the
name a person would recognise, and where it came from - except that here the
code name *is* a colour. A pixel probe that says ``(96,160,64)`` tells nobody
anything; ``Fertile Medium (fertility_medium)`` is the whole point of the
inspector.

Two of the three tables are fixed by the engine and are written down here:

**Ground types** and **features** are the arbiter's tables, cross-checked
against TWMapReader's ``TwGroundType`` and ``TwFeatureType`` enums, which are
the reverse-engineered set nobody else has written down, and against Mylae's
``autoGroundTypes.js``, which agrees on every one of the fifteen it shares and
adds a sixteenth, ``impassable_sea``.

Measured on DaC: ``map_ground_types.tga`` uses 12 of the 16 ground colours and
nothing else, and ``map_features.tga`` uses all 6 feature colours plus one stray
``(1,1,1)`` pixel - exactly the kind of thing the validator in 16f exists to
find, so an unknown colour here is *reported*, never silently rounded to the
nearest known one.

**Climates** are not fixed: every mod declares its own in ``descr_climates.txt``
with a ``colour R G B`` line per climate, and names them in the UTF-16
``text/climates.txt``. DaC renames all twelve to Middle-earth places
(``alpine`` is "Forodwaith"), which is why reading them out of the mod matters
rather than shipping vanilla's list.

The fourth layer worth a word is **heights**, and its vocabulary is a rule, not
a table: a tile is sea if its height pixel is not greyscale, or is pure black.
See :func:`is_sea_height`.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

#: Plain 8-bit game data, as everywhere else in the toolkit
ENCODING = "latin-1"

CLIMATES_REL = "descr_climates.txt"
CLIMATE_NAMES_REL = "text/climates.txt"

Rgb = Tuple[int, int, int]


def key(rgb: Rgb) -> int:
    """A colour as one integer. Packed keys, never ``"r,g,b"`` strings.

    Demir's tool builds a template-literal string per pixel in three separate
    places and looks it up in a Map; that is 1.6 M string allocations per painted
    water pixel. Every lookup in this toolkit goes through this instead.
    """
    return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]


def unkey(packed: int) -> Rgb:
    return ((packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF)


# ---------------------------------------------------------------------------
# ground types - map_ground_types.tga, sampled at (2t+1, 2t+1)

#: ``(code, display name, rgb)``. Order is the arbiter's, not alphabetical.
GROUND_TYPES: List[dict] = [
    {"code": "fertility_low", "name": "Fertile Low", "rgb": (0, 128, 128)},
    {"code": "fertility_medium", "name": "Fertile Medium", "rgb": (96, 160, 64)},
    {"code": "fertility_high", "name": "Fertile High", "rgb": (101, 124, 0)},
    {"code": "wilderness", "name": "Wilderness", "rgb": (0, 0, 0)},
    {"code": "hills", "name": "Hills", "rgb": (128, 128, 64)},
    {"code": "mountains_low", "name": "Mountains Low", "rgb": (98, 65, 65)},
    {"code": "mountains_high", "name": "Mountains High", "rgb": (196, 128, 128)},
    {"code": "forest_sparse", "name": "Forest Sparse", "rgb": (0, 128, 0)},
    {"code": "forest_dense", "name": "Forest Dense", "rgb": (0, 64, 0)},
    {"code": "swamp", "name": "Swamp", "rgb": (0, 255, 128)},
    {"code": "beach", "name": "Beach", "rgb": (255, 255, 255)},
    {"code": "sea_shallow", "name": "Sea Shallow", "rgb": (196, 0, 0)},
    {"code": "sea_deep", "name": "Sea Deep", "rgb": (128, 0, 0)},
    {"code": "ocean", "name": "Ocean", "rgb": (64, 0, 0)},
    {"code": "impassable_land", "name": "Impassable", "rgb": (64, 64, 64)},
    {"code": "impassable_sea", "name": "Impassable Sea", "rgb": (0, 0, 64)},
]

#: ``impassable_sea`` is the sixteenth, and TWMapReader's enum does not have it.
#: Mylae's ``autoGroundTypes.js`` table does, and so does every mod's
#: ``descr_aerial_map_ground_types.txt``, DaC's included - which is two
#: independent sources plus a file the game reads, against one omission. The
#: other fifteen colours are identical in both tables, checked value by value.

#: the four that are water. The *authority* on whether a tile is sea is
#: map_heights, not this - see :func:`is_sea_height` - but a paint tool writing
#: water needs to know which ground colours go with it.
SEA_GROUND = ("sea_shallow", "sea_deep", "ocean", "impassable_sea")

#: ground types a unit cannot stand on, which is what makes a settlement or port
#: placed on one a crash rather than a curiosity
BLOCKING_GROUND = ("impassable_land",) + SEA_GROUND


# ---------------------------------------------------------------------------
# features - map_features.tga, one pixel per tile

FEATURES: List[dict] = [
    {"code": "none", "name": "-", "rgb": (0, 0, 0)},
    {"code": "river", "name": "River", "rgb": (0, 0, 255)},
    {"code": "river_crossing", "name": "River Crossing", "rgb": (0, 255, 255)},
    {"code": "river_source", "name": "River Source", "rgb": (255, 255, 255)},
    {"code": "cliff", "name": "Cliff", "rgb": (255, 255, 0)},
    {"code": "volcano", "name": "Volcano", "rgb": (255, 0, 0)},
    {"code": "land_bridge", "name": "Land Bridge", "rgb": (0, 255, 0)},
]

#: a settlement or port pixel on one of these is the back-to-menu crash the
#: TWCenter index describes, so 16f checks for it and 16e refuses to paint it
FATAL_UNDER_SETTLEMENT = ("river", "river_crossing", "river_source", "volcano")


# ---------------------------------------------------------------------------
# region markers - map_regions.tga

#: black is where the settlement stands, white is where the port stands. Neither
#: is a region colour, and both are excluded from the region-id scan.
SETTLEMENT_RGB: Rgb = (0, 0, 0)
PORT_RGB: Rgb = (255, 255, 255)

#: the engine's ceiling, sea colours included. DaC is at 202 unique colours in
#: map_regions.tga, two of which are the markers above, so it is on the cap.
MAX_REGION_COLOURS = 200


# ---------------------------------------------------------------------------
# lookups

_GROUND_BY_KEY: Dict[int, dict] = {key(g["rgb"]): g for g in GROUND_TYPES}
_FEATURE_BY_KEY: Dict[int, dict] = {key(f["rgb"]): f for f in FEATURES}
_GROUND_BY_CODE: Dict[str, dict] = {g["code"]: g for g in GROUND_TYPES}
_FEATURE_BY_CODE: Dict[str, dict] = {f["code"]: f for f in FEATURES}


def ground_at(rgb: Rgb) -> Optional[dict]:
    """The ground type this colour names, or ``None`` if the table has never
    seen it. ``None`` is a finding, not a fallback."""
    return _GROUND_BY_KEY.get(key(rgb))


def feature_at(rgb: Rgb) -> Optional[dict]:
    """The feature this colour names, or ``None``. DaC's stray ``(1,1,1)``
    pixel is the reason this returns ``None`` rather than "no feature"."""
    return _FEATURE_BY_KEY.get(key(rgb))


def ground(code: str) -> Optional[dict]:
    return _GROUND_BY_CODE.get(code)


def feature(code: str) -> Optional[dict]:
    return _FEATURE_BY_CODE.get(code)


def is_sea_ground(rgb: Rgb) -> bool:
    g = ground_at(rgb)
    return bool(g and g["code"] in SEA_GROUND)


def is_sea_height(rgb: Rgb) -> bool:
    """**A tile is sea iff its height pixel is not greyscale, or is black.**

    Not from ground types - that was the old guess and it is wrong at the
    coastline. TWMapReader worked this out from the engine's own behaviour and
    left the ground-type version deprecated beside it.

    The caller owes this function one exclusion it cannot make itself: a tile
    whose *feature* is a river crossing is never sea, whatever its height says.
    :mod:`unittransfer.campmap` applies that, because only it has both layers.

    Measured on DaC at tile centres: 74,317 tiles come out sea by this rule and
    74,247 of them are also sea by ground type - the 70 that disagree are
    exactly the underwater-land tiles the region-id scan has to skip.
    """
    r, g, b = rgb
    if r == 0 and g == 0 and b == 0:
        return True
    return not (r == g == b)


# ---------------------------------------------------------------------------
# climates - read out of the mod, because every mod renames them


def _read(path: Path, encodings=(ENCODING,)) -> str:
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except (OSError, UnicodeError):
            continue
    return ""


def _read_utf16(path: Path) -> str:
    """A ``data/text`` file: UTF-16 with a BOM, falling back to 8-bit."""
    return _read(path, ("utf-16", ENCODING))


def climates(mod) -> List[dict]:
    """Every climate the mod declares, with its colour, heat and display name.

    ``descr_climates.txt`` opens with a ``climates { … }`` list that fixes the
    order, then one ``climate <name> { colour R G B / heat N / winter … }``
    block each. The order is not decoration: it is the index the engine uses,
    and ``descr_climates_lookup.txt`` is the same list again.

    Names come from ``text/climates.txt``, which is UTF-16 and keyed by the code
    name in braces. A climate with no entry there keeps its code name.
    """
    text = _read(mod.data / CLIMATES_REL)
    if not text:
        return []
    loc = dict(re.findall(r"^\{([^}]+)\}(.*)$", _read_utf16(mod.data / CLIMATE_NAMES_REL),
                          re.M))

    order: List[str] = []
    m = re.search(r"^\s*climates\s*\{(.*?)\}", text, re.S | re.M)
    if m:
        for line in m.group(1).splitlines():
            name = line.split(";", 1)[0].strip()
            if name:
                order.append(name)

    blocks: Dict[str, dict] = {}
    for bm in re.finditer(r"^\s*climate\s+(\S+)\s*\{(.*?)^\s*\}", text, re.S | re.M):
        name, body = bm.group(1), bm.group(2)
        cm = re.search(r"^\s*colour\s+(\d+)\s+(\d+)\s+(\d+)", body, re.M)
        hm = re.search(r"^\s*heat\s+(\d+)", body, re.M)
        blocks[name] = {
            "code": name,
            "name": (loc.get(name) or "").strip() or name,
            "rgb": (int(cm.group(1)), int(cm.group(2)), int(cm.group(3))) if cm else None,
            "heat": int(hm.group(1)) if hm else 0,
            "winter": bool(re.search(r"^\s*winter\s*$", body, re.M)),
        }

    # the header list is the index order; anything declared but not listed goes
    # after it rather than being dropped
    out = [blocks[n] for n in order if n in blocks]
    out += [b for n, b in blocks.items() if n not in order]
    for i, c in enumerate(out):
        c["index"] = i
    return out


def climate_index(mod) -> Dict[int, dict]:
    """Climate by packed colour, for the pixel probe."""
    return {key(c["rgb"]): c for c in climates(mod) if c["rgb"]}


def build(mod) -> dict:
    """Everything the map inspector needs to name a pixel, in one call.

    Same shape as :func:`unittransfer.edbvocab.build`: plain lists of dicts, no
    objects, so it serialises straight to the browser.
    """
    return {
        "ground_types": GROUND_TYPES,
        "features": FEATURES,
        "climates": climates(mod),
        "markers": {"settlement": SETTLEMENT_RGB, "port": PORT_RGB},
        "max_region_colours": MAX_REGION_COLOURS,
    }
