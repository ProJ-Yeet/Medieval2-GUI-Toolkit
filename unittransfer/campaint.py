"""The paint tool: strokes, unlimited undo, and the write. Phase 16e.

:mod:`unittransfer.campmap` reads the map and owns the region record. This is
the other half - the one that changes pixels - and the split is deliberate:
everything here mutates, and a module that mutates should not also be the one
everything else reads through.

**Python owns the bytes.** The browser draws a provisional trail under the
cursor and posts the pointer samples; this module expands them, snaps the
colour, refuses what must not be written, applies it to the layer image the
whole server is already reading, and answers with the tiles that actually
changed. The browser replaces its trail with that answer. So there is one brush
that decides pixels, one undo stack, one backup and one file writer, and a
disagreement between the preview and the file cannot outlive a pointer-up.

Five tools, from the two reference editors that have any::

    pencil   one tile
    brush    a disc or square of tiles, interpolated along the drag
    bucket   four-connected flood fill of one colour on one layer
    pipette  reads - it never writes, and is answered by /api/map/probe
    water    Demir's water brush: regions, heights and ground types together

**Region-colour snapping** is the rule that makes the first four safe. Painting
``map_regions.tga`` never writes a colour picked off the screen: it writes the
selected region's canonical RGB out of ``descr_regions.txt``, or the sea colour
measured off this mod's own map. Drift is therefore impossible - a province
painted one channel off is a province the engine cannot see, and DaC ships
exactly that mistake in a 517-tile hole at (318,54) - and the two marker colours
can never be produced by accident, because they are not in the palette at all.
They are placed by the wizard, one tile at a time, and a stroke that would cover
one skips it and says how many it protected.

**One colour per layer per stroke.** Every tool here writes a single value, so a
stroke is a tile list plus one RGB rather than a bitmap. That is what makes the
undo stack cheap enough to be unlimited: Geomod has one level, Mylae keeps one
snapshot of the whole layer and Demir has no undo at all, and all three are
paying for a model where a stroke could have been anything.

**The tile is the unit, and the block is what a tile owns.** Three of the ten
layers are one pixel per tile; the others are 2W x 2H or 2W+1 x 2H+1, and a
tile there is a block of pixels rather than one. :func:`block` is that rule,
and it partitions the layer exactly - every pixel of an aligned layer belongs
to exactly one tile, the ``2W+1`` layers' leading row and column included, so
painting cannot leave a stale seam between two tiles that were both painted.
The block always contains the pixel the engine samples, which is the invariant
the tests hold it to: paint a tile, and :meth:`CampaignMap.centres` at that
tile is the colour that was painted.

Nothing here writes to disk until :func:`apply_paint`. Until then the strokes
live in the layer images the server is already serving from, so the probe, the
legend and the layer PNGs all show the unsaved state - there is no second copy
of the pixels to disagree with the first. What that costs is stated in
:class:`PaintSession`: a map re-read from disk underneath an unsaved session
drops it, and says so rather than saving over what changed.
"""
from __future__ import annotations

import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from PIL import Image

from . import campmap, mapvocab
from .campmap import (BASE_REL, ENCODING, LAYER_BY_CODE, REGIONS_REL, RWM_REL,
                      CampaignMap, MapError, Rgb, key)
from .maptga import encode
from .mapvocab import PORT_RGB, SETTLEMENT_RGB, unkey

#: The layers a brush may touch: the eight with a fixed relationship to the tile
#: grid. ``water_surface`` and ``map_FE`` are pictures - they are stretched over
#: the map for looks and a tile means nothing in them - so they are not offered.
PAINTABLE: Tuple[str, ...] = ("regions", "heights", "ground_types", "climates",
                              "features", "trade_routes", "roughness", "fog")

#: ``pipette`` is not here because it does not write; it is one probe request.
TOOLS: Tuple[str, ...] = ("pencil", "brush", "bucket", "water")

#: The three layers Demir's water brush writes together. A tile that is sea on
#: one and land on another is the mismatch that puts a ship on a hill.
WATER_LAYERS: Tuple[str, ...] = ("regions", "heights", "ground_types")

#: The widest brush, in tiles across. **Size is the width, not the radius**,
#: and only odd widths exist - a brush is a disc or a square centred on the tile
#: under the cursor, and an even one has no centre tile to be under it. 33 is a
#: sixteenth of DaC's map in one stroke, which is as coarse as a tool whose
#: whole point is placing single pixels has any business being; a bucket does
#: the big areas.
BRUSH_MAX = 33

#: How many pixel deltas the undo stack holds before the oldest stroke is let
#: go. Unlimited in the sense that matters - there is no level count - with the
#: one bound being memory, and the answer says when it bites. Three ints per
#: delta, so this is about 48 MB in the worst case anyone can reach by hand.
UNDO_BUDGET = 4_000_000

#: A tile whose region pixel is one of these is skipped by every stroke and
#: counted. Painting over a settlement marker deletes a city.
PROTECTED: Tuple[int, ...] = (key(SETTLEMENT_RGB), key(PORT_RGB))


# ---------------------------------------------------------------------------
# the tile -> pixel rule


def block(size_rule: str, x: int, y: int) -> Tuple[int, int, int, int]:
    """The inclusive pixel rectangle tile ``(x, y)`` owns on a layer.

    ``tile``    the pixel itself.
    ``double``  ``(2x, 2y)`` to ``(2x+1, 2y+1)`` - an exact 2x2 partition.
    ``centre``  ``(2x+1, 2y+1)`` to ``(2x+2, 2y+2)``, and tile 0 takes the
                leading row and column as well, because otherwise nothing owns
                them and a painted coastline keeps a one-pixel seam of the old
                map along two edges.

    The engine's own sample point - ``(2x+1, 2y+1)`` on a ``centre`` layer,
    ``(2x, 2y)`` on a ``double`` one - is inside the rectangle in every case,
    which is the whole point: what the tile view shows after a stroke is what
    was painted.
    """
    if size_rule == "tile":
        return x, y, x, y
    if size_rule == "double":
        return 2 * x, 2 * y, 2 * x + 1, 2 * y + 1
    if size_rule == "centre":
        return (2 * x if x == 0 else 2 * x + 1,
                2 * y if y == 0 else 2 * y + 1,
                2 * x + 2, 2 * y + 2)
    raise MapError(f"a {size_rule!r} layer has no relationship to the tile "
                   f"grid, so a tile cannot be painted on it")


# ---------------------------------------------------------------------------
# palettes - what a layer is allowed to be painted


def _census(cm: CampaignMap, code: str, cap: int) -> List[dict]:
    """The colours a layer actually uses, biggest first. The fallback palette.

    Heights, roughness, fog and trade routes have a rule or a magnitude rather
    than a vocabulary, so the only honest palette for them is the map's own
    colours - which is also the palette somebody wants, because matching the
    height of the tile next door is the whole job.
    """
    # the same ceiling layer_legend counts to, and for the same reason: a
    # bigger one allocates a table sixteen times the size for no more answers
    got = cm.tiles(code).getcolors(1 << 20) or []
    got.sort(key=lambda c: -c[0])
    climates = mapvocab.climate_index(cm.mod) if code == "climates" else {}
    out = []
    for count, rgb in got[:cap]:
        name, code_name = campmap._colour_name(cm, code, rgb, climates)
        out.append({"rgb": list(rgb), "key": key(rgb), "count": count,
                    "name": name, "code_name": code_name})
    return out


def palette(cm: CampaignMap, code: str) -> dict:
    """What may be written to one layer, and where the list came from.

    Four layers have a real vocabulary and their palette is that table, so a
    colour outside it is refused rather than written - an unknown colour on
    ``map_ground_types.tga`` is precisely what 16f exists to report, and a paint
    tool that can create one is a tool that manufactures its own bug reports.
    The other four get the map's own colours and are open, with the rule that
    governs them said on the screen.
    """
    ly = LAYER_BY_CODE[code]
    out = {"code": code, "label": ly["label"], "file": ly["file"],
           "size": ly["size"], "closed": True, "note": "", "problem": "",
           "colours": []}
    if code == "regions":
        # the region list IS the palette, and every entry is a canonical RGB out
        # of descr_regions.txt rather than a colour read off the picture
        out["note"] = ("Every colour here is a region's own, out of "
                       "descr_regions.txt. The brush writes that number and "
                       "nothing else, so a province cannot drift a channel.")
        out["colours"] = [{"rgb": list(r.rgb), "key": r.rgb_key,
                           "name": r.settlement or r.name, "code_name": r.name,
                           "region": r.name} for r in cm.regions.records]
        return out
    if code == "ground_types":
        out["note"] = ("The engine's sixteen, cross-checked between "
                       "TWMapReader's enum and Mylae's table.")
        out["colours"] = [{"rgb": list(g["rgb"]), "key": key(g["rgb"]),
                           "name": g["name"], "code_name": g["code"]}
                          for g in mapvocab.GROUND_TYPES]
        return out
    if code == "features":
        out["note"] = ("The arbiter's own table. Black is `none`, and a "
                       "settlement or port standing on a river, ford, source or "
                       "volcano is the back-to-menu crash, so a marker is "
                       "refused over those four.")
        out["colours"] = [{"rgb": list(f["rgb"]), "key": key(f["rgb"]),
                           "name": f["name"], "code_name": f["code"]}
                          for f in mapvocab.FEATURES]
        return out
    if code == "climates":
        climates = mapvocab.climates(cm.mod)
        out["note"] = (f"{len(climates)} climates, read out of this mod's own "
                       f"descr_climates.txt - every mod renames them.")
        out["colours"] = [{"rgb": list(c["rgb"]), "key": key(c["rgb"]),
                           "name": c["name"], "code_name": c["code"]}
                          for c in climates if c["rgb"]]
        if not out["colours"]:
            out["closed"] = False
            out["note"] = ("This mod declares no climate colours, so there is "
                           "no table to hold a stroke to - the palette is the "
                           "colours already on the map.")
            out["colours"] = _census(cm, code, campmap.LEGEND_MAX)
        return out
    out["closed"] = False
    out["colours"] = _census(cm, code, campmap.LEGEND_MAX)
    out["note"] = ("Heights is a rule, not a table: a tile is sea when its "
                   "pixel is not greyscale, or is pure black. These are the "
                   "colours already on this map, biggest first."
                   if code == "heights" else
                   "This layer is a magnitude rather than a vocabulary, so the "
                   "palette is the colours already on this map.")
    return out


def water_palette(cm: CampaignMap) -> dict:
    """The three colours this mod paints its own sea, measured off the map.

    Demir's water brush writes a hard-coded triple per layer. That is right for
    one mod and wrong for the next, because the region layer's sea colour is
    declared nowhere - ``descr_regions.txt`` has no ocean record - so it is
    whatever the mod's author happened to use, and vanilla and DaC do not agree.

    So it is measured: the commonest colour on each of the three layers among
    the tiles the engine treats as sea, with the count beside it, so the number
    is a measurement on the screen rather than a constant in the source.
    """
    sea = cm.sea
    idx = [i for i, s in enumerate(sea) if s]
    out: Dict[str, dict] = {}
    for code in WATER_LAYERS:
        data = cm.tiles(code).tobytes()
        counts: Dict[int, int] = {}
        for i in idx:
            p = i * 3
            k = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
            counts[k] = counts.get(k, 0) + 1
        # the markers are never the sea, whatever a census says: a port pixel
        # stands in the water by definition
        for k in PROTECTED:
            counts.pop(k, None)
        if not counts:
            continue
        k, n = max(counts.items(), key=lambda kv: kv[1])
        out[code] = {"rgb": list(unkey(k)), "key": k, "tiles": n,
                     "share": round(n * 100.0 / max(1, len(idx)), 1)}
    return {"sea_tiles": len(idx), "layers": out,
            "ok": len(out) == len(WATER_LAYERS)}


def palettes(cm: CampaignMap) -> dict:
    """Every paintable layer's palette and the water brush's, in one call.

    All of it is small and all of it is wanted before the first stroke, so it is
    one request rather than nine - the same trade :func:`campmap.view` makes.
    """
    out: dict = {"layers": [], "tools": list(TOOLS), "brush_max": BRUSH_MAX,
                 "markers": {"settlement": list(SETTLEMENT_RGB),
                             "port": list(PORT_RGB)}}
    for code in PAINTABLE:
        try:
            cm.require_grid(code)
            cm.layer(code)
            out["layers"].append(palette(cm, code))
        except MapError as exc:
            ly = LAYER_BY_CODE[code]
            out["layers"].append({"code": code, "label": ly["label"],
                                  "file": ly["file"], "size": ly["size"],
                                  "closed": True, "colours": [], "note": "",
                                  "problem": str(exc)})
    try:
        out["water"] = water_palette(cm)
    except MapError as exc:
        out["water"] = {"sea_tiles": 0, "layers": {}, "ok": False,
                        "problem": str(exc)}
    return out


# ---------------------------------------------------------------------------
# the brush geometry
#
# The browser draws a provisional trail with the same two shapes, so the cursor
# tells the truth while the drag is happening; it then throws that away for what
# comes back from here. This is the copy that decides pixels.


def _stamp(out: Set[Tuple[int, int]], cx: int, cy: int, radius: int,
           round_: bool, w: int, h: int) -> None:
    r2 = radius * radius
    for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
            if round_ and (x - cx) ** 2 + (y - cy) ** 2 > r2:
                continue
            out.add((x, y))


def _line(x0: int, y0: int, x1: int, y1: int) -> Iterable[Tuple[int, int]]:
    """Bresenham, integers only. A drag samples at 60 Hz and moves faster."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def expand(points: Sequence[Sequence[int]], size: int, shape: str,
           w: int, h: int) -> List[Tuple[int, int]]:
    """The tiles a drag covers: every sample stamped, and the gaps joined.

    A pointer at 60 Hz over a map moving 40 tiles a second leaves gaps, and a
    brush that paints only where an event happened writes a dotted line. So
    consecutive samples are joined with a straight line of tiles before
    stamping.
    """
    size = max(1, min(BRUSH_MAX, int(size or 1)))
    radius = (size - 1) // 2                  # width in tiles -> tiles either side
    round_ = shape != "square"
    out: Set[Tuple[int, int]] = set()
    prev: Optional[Tuple[int, int]] = None
    for p in points:
        try:
            x, y = int(p[0]), int(p[1])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if prev is None:
            _stamp(out, x, y, radius, round_, w, h)
        else:
            for lx, ly in _line(prev[0], prev[1], x, y):
                _stamp(out, lx, ly, radius, round_, w, h)
        prev = (x, y)
    return sorted(out)


def flood(cm: CampaignMap, code: str, sx: int, sy: int) -> List[Tuple[int, int]]:
    """Every tile four-connected to ``(sx, sy)`` and the same colour as it.

    Four-connected rather than eight, and that is the same ruling
    :attr:`CampaignMap.neighbours` makes for the same reason: the engine moves
    cardinally, so two areas that meet only at a corner are two areas.

    On the tile view, never on the native pixels. A bucket on a ``2W+1`` layer
    that flooded native pixels would run through the seams between tiles and
    fill by a rule nobody can see on the screen.
    """
    w, h = cm.terrain.width, cm.terrain.height
    if not (0 <= sx < w and 0 <= sy < h):
        raise MapError(f"{sx},{sy} is off the {w}x{h} tile grid")
    data = cm.tiles(code).tobytes()

    def at(i: int) -> int:
        p = i * 3
        return (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]

    want = at(sy * w + sx)
    seen = bytearray(w * h)
    start = sy * w + sx
    seen[start] = 1
    stack = [start]
    out: List[Tuple[int, int]] = []
    while stack:
        i = stack.pop()
        if at(i) != want:
            continue
        x, y = i % w, i // w
        out.append((x, y))
        if x > 0 and not seen[i - 1]:
            seen[i - 1] = 1
            stack.append(i - 1)
        if x < w - 1 and not seen[i + 1]:
            seen[i + 1] = 1
            stack.append(i + 1)
        if y > 0 and not seen[i - w]:
            seen[i - w] = 1
            stack.append(i - w)
        if y < h - 1 and not seen[i + w]:
            seen[i + w] = 1
            stack.append(i + w)
    out.sort()
    return out


# ---------------------------------------------------------------------------
# a stroke, and the session that holds them


@dataclass
class Stroke:
    """One tool, one press, one entry on the undo stack.

    ``px`` is the whole of what undo needs: for each layer, a flat
    ``[x, y, before, x, y, before, …]`` of the pixels this stroke changed, in
    that layer's own native coordinates. The colour written is uniform per
    layer, so the forward direction needs no list at all - that is the model,
    and it is why the stack can be unlimited.

    ``tiles`` and ``was`` are the same thing said in tile space, which is what
    the browser draws and what its own copy of the layer is indexed by.
    """

    label: str = ""
    tool: str = ""
    #: code -> packed RGB written
    rgb: Dict[str, int] = field(default_factory=dict)
    #: code -> array("i") of x, y, before-packed triples, native coordinates
    px: Dict[str, array] = field(default_factory=dict)
    #: code -> array("i") of x, y, before-packed triples, tile coordinates
    tiles: Dict[str, array] = field(default_factory=dict)
    protected: int = 0
    when: float = field(default_factory=time.time)

    @property
    def deltas(self) -> int:
        return sum(len(a) // 3 for a in self.px.values())

    @property
    def tile_count(self) -> int:
        return max((len(a) // 3 for a in self.tiles.values()), default=0)

def _xy(a: array) -> List[int]:
    """``[x, y, x, y, …]`` out of an ``[x, y, before, …]`` array."""
    out: List[int] = []
    for i in range(0, len(a), 3):
        out.append(a[i])
        out.append(a[i + 1])
    return out


def _painted(stroke: Stroke) -> dict:
    """The stroke as the browser applies it: one colour and a tile list."""
    return {c: {"rgb": stroke.rgb[c], "xy": _xy(a)}
            for c, a in stroke.tiles.items()}


def _reverted(stroke: Stroke) -> dict:
    """And backwards: every tile with the colour it had, which may differ."""
    out: Dict[str, dict] = {}
    for c, a in stroke.tiles.items():
        by: Dict[int, List[int]] = {}
        for i in range(0, len(a), 3):
            by.setdefault(a[i + 2], []).extend((a[i], a[i + 1]))
        out[c] = {"runs": [{"rgb": k, "xy": v} for k, v in by.items()]}
    return out


class PaintSession:
    """Every unsaved stroke on one mod's map, and the pixels they made.

    The strokes are applied to the very layer images
    :class:`~unittransfer.server.Registry` hands every other route, so the
    probe, the legend and the layer PNGs all show the unsaved state. There is
    no second copy of the pixels, which is the only way the picture on screen
    and the file that would be written can be guaranteed to agree.

    The cost of that is stated rather than hidden: the session holds the
    :class:`~unittransfer.campmap.CampaignMap` it painted, and the registry
    drops that object whenever a file the map was read from changes on disk. So
    a layer edited in Photoshop under an unsaved session ends the session - the
    next request is told the map was re-read and the strokes are gone, which is
    a sentence somebody can act on, and better than writing a mixture of the two.
    """

    def __init__(self, mod, cm: CampaignMap):
        self.mod = mod
        self.cm = cm
        self.undo: List[Stroke] = []
        self.redo: List[Stroke] = []
        self.dirty: Set[str] = set()
        self.dropped = 0
        #: the wizard's pending region, or None - see :func:`start_region`
        self.new_region: Optional[dict] = None
        self._bufs: Dict[str, bytearray] = {}

    # -- pixels --------------------------------------------------------------

    def buffer(self, code: str) -> Tuple[bytearray, int, int]:
        """``(bytes, stride, width)`` of one layer, held for the session.

        A ``bytearray`` rather than Pillow's pixel access: a bucket fill of an
        ocean is a million scattered writes, and ``PixelAccess.__setitem__``
        costs about a microsecond each. Pushed back into the image after every
        stroke by :meth:`flush`, so nothing else ever sees a half-written layer.
        """
        if code not in self._bufs:
            img = self.cm.layer(code)
            self._bufs[code] = bytearray(img.tobytes())
        img = self.cm.layer(code)
        return self._bufs[code], len(img.mode), img.width

    def flush(self, codes: Iterable[str]) -> None:
        for code in codes:
            img = self.cm.layer(code)
            img.frombytes(bytes(self._bufs[code]))
            self.dirty.add(code)
        self.cm.repixel(*codes)

    # -- the stack -----------------------------------------------------------

    def push(self, stroke: Stroke) -> None:
        self.undo.append(stroke)
        self.redo.clear()
        held = sum(s.deltas for s in self.undo)
        while len(self.undo) > 1 and held > UNDO_BUDGET:
            held -= self.undo.pop(0).deltas
            self.dropped += 1

    def apply_px(self, stroke: Stroke, forward: bool) -> None:
        """Write one stroke's pixels, or put back what they covered.

        Backwards is not "paint the old colour over it": the pixels a stroke
        covered were not all one colour, so the old value is stored per pixel
        and put back per pixel. That is what makes an undo byte-exact rather
        than merely plausible.
        """
        for code, a in stroke.px.items():
            buf, stride, width = self.buffer(code)
            if forward:
                rgb = stroke.rgb[code]
                r, g, b = (rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255
                for i in range(0, len(a), 3):
                    p = (a[i + 1] * width + a[i]) * stride
                    buf[p] = r
                    buf[p + 1] = g
                    buf[p + 2] = b
            else:
                for i in range(0, len(a), 3):
                    was = a[i + 2]
                    p = (a[i + 1] * width + a[i]) * stride
                    buf[p] = (was >> 16) & 255
                    buf[p + 1] = (was >> 8) & 255
                    buf[p + 2] = was & 255
        self.flush(stroke.px)

    @property
    def unsaved(self) -> List[str]:
        """The layers that differ from disk, said without re-encoding them.

        ``dirty`` is every layer a stroke has ever touched, and after enough
        Undos that is a list of layers which are now byte for byte what was
        read. An empty undo stack means every stroke has been reversed, so
        nothing differs - unless the budget let an old one go, and then the
        stack being empty proves nothing and the honest answer is the long one.
        """
        return sorted(self.dirty) if (self.undo or self.dropped) else []

    def state(self) -> dict:
        return {
            "dirty": self.unsaved,
            "files": [LAYER_BY_CODE[c]["file"] for c in self.unsaved],
            "undo": len(self.undo), "redo": len(self.redo),
            "dropped": self.dropped,
            "deltas": sum(s.deltas for s in self.undo),
            "last": self.undo[-1].label if self.undo else "",
            "next": self.redo[-1].label if self.redo else "",
            "new_region": dict(self.new_region) if self.new_region else None,
        }


#: One session per mod, held until it is saved, discarded, or the map under it
#: is re-read. Module level for the same reason the icon cache is: the server
#: builds a new handler per request and a session that lived on one would last
#: exactly one stroke.
_SESSIONS: Dict[str, PaintSession] = {}


def session(name: str, mod, cm: CampaignMap) -> Tuple[PaintSession, bool]:
    """``(session, was_reset)`` for one mod, made if there is not one.

    ``was_reset`` is true when a session existed and was thrown away because the
    map had been re-read from disk underneath it. The caller says so out loud;
    silently starting a fresh one would lose work without a word.
    """
    held = _SESSIONS.get(name)
    if held is not None and held.cm is cm:
        return held, False
    reset = held is not None
    _SESSIONS[name] = PaintSession(mod, cm)
    return _SESSIONS[name], reset


def peek(name: str) -> Optional[PaintSession]:
    return _SESSIONS.get(name)


def drop(name: str) -> None:
    _SESSIONS.pop(name, None)


# ---------------------------------------------------------------------------
# one stroke


def _own_key(cm: CampaignMap, sess: PaintSession, name: str) -> int:
    """The canonical colour of the region a stroke belongs to. The snapping.

    Out of ``descr_regions.txt``, or out of the wizard's pending record when the
    region does not exist yet - never out of a pixel somebody clicked. That is
    the whole of the rule, and it is one function so there is one place it can
    be got wrong.
    """
    if not name:
        raise MapError("pick the region to paint first - the brush writes its "
                       "colour out of descr_regions.txt, never one read off "
                       "the screen")
    pending = sess.new_region
    if pending and pending["name"].lower() == name.lower():
        return key(tuple(pending["rgb"]))
    rec = cm.regions.by_name(name)
    if rec is None:
        raise MapError(f"no region called {name!r} in descr_regions.txt")
    if rec.rgb_key in PROTECTED:
        raise MapError(f"{rec.name} is declared as "
                       f"{rec.rgb[0]} {rec.rgb[1]} {rec.rgb[2]}, which is a "
                       f"marker colour, not a province colour")
    return rec.rgb_key


def _resolve(cm: CampaignMap, sess: PaintSession, body: dict) -> Dict[str, int]:
    """``{layer code: packed RGB}`` this stroke will write. The snapping rule.

    Three ways a colour is decided, and none of them is "the number the browser
    sent for the region layer":

      * ``regions``  by region NAME, out of ``descr_regions.txt``, or the sea
        colour measured off the map, or the wizard's pending region. A marker
        colour is refused by name here rather than protected against later.
      * a closed layer  the colour must be in that layer's table.
      * an open layer  any triple, because the layer is a magnitude.
    """
    tool = body.get("tool")
    if tool == "water":
        w = water_palette(cm)
        if not w["ok"]:
            raise MapError("this map's sea colours cannot be measured - "
                           + (w.get("problem") or "no tile on it reads as sea"))
        return {c: w["layers"][c]["key"] for c in WATER_LAYERS}

    code = body.get("target") or ""
    if code not in PAINTABLE:
        raise MapError(f"{code!r} is not a layer this tool paints - it is one "
                       f"of {', '.join(PAINTABLE)}")
    cm.require_grid(code)

    if code == "regions":
        if body.get("sea"):
            w = water_palette(cm)
            if "regions" not in w["layers"]:
                raise MapError("no tile of this map reads as sea, so there is "
                               "no sea colour to snap to")
            return {code: w["layers"]["regions"]["key"]}
        marker = str(body.get("marker") or "")
        if marker:
            if marker not in ("settlement", "port"):
                raise MapError(f"{marker!r} is not a marker - map_regions.tga "
                               f"has two, the settlement and the port")
            return {code: key(SETTLEMENT_RGB if marker == "settlement"
                              else PORT_RGB)}
        return {code: _own_key(cm, sess, str(body.get("region") or "").strip())}

    rgb = body.get("rgb")
    try:
        k = key((int(rgb[0]), int(rgb[1]), int(rgb[2])))
    except (TypeError, ValueError, IndexError, KeyError):
        raise MapError("a colour is three numbers 0-255") from None
    pal = palette(cm, code)
    if pal["closed"] and k not in {c["key"] for c in pal["colours"]}:
        r, g, b = unkey(k)
        raise MapError(f"{r} {g} {b} is not a colour {pal['file']} has a "
                       f"meaning for. Painting it would put a pixel on the map "
                       f"that no table names - which is the fault 16f exists to "
                       f"report, so it is refused here instead")
    return {code: k}


def _check_marker(cm: CampaignMap, sess: PaintSession, body: dict,
                  tiles: Sequence[Tuple[int, int]]) -> None:
    """A settlement or port pixel is one tile, and it has rules of its own.

    The one that matters most is not a game rule, it is an arithmetic one: the
    tile has to already be painted the region's own colour. That single check
    does the work of three - a marker cannot land in the sea outside the
    province, it cannot land in the province next door, and it cannot overwrite
    another region's marker, because none of those tiles is this colour.

    The rest are the crash the TWCenter index describes: a marker on impassable
    or sea ground, or on a river, ford, source or volcano. Refused here rather
    than reported at the save, because the pixel is placed by clicking a tile
    and the click is where the answer belongs.
    """
    kind = str(body.get("marker"))
    if len(tiles) != 1:
        raise MapError(f"a {kind} pixel is one tile - place it with the pencil")
    home = _own_key(cm, sess, str(body.get("region") or "").strip())
    tx, ty = tiles[0]
    data = cm.tiles("regions").tobytes()
    p = (ty * cm.terrain.width + tx) * 3
    now = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
    if now != home:
        r, g, b = unkey(home)
        raise MapError(f"{tx},{ty} is not painted {r} {g} {b}, so it is not "
                       f"inside this region. A {kind} marker stands on one of "
                       f"its own region's tiles - paint the tile first.")
    for fatal, message in _marker_problems(cm, (tx, ty), kind):
        if fatal:
            raise MapError(message)


def _label(tool: str, codes: Iterable[str], tiles: int, body: dict) -> str:
    marker = str(body.get("marker") or "")
    if marker:
        return f"place the {marker} pixel"
    what = ", ".join(LAYER_BY_CODE[c]["label"].lower() for c in codes)
    return f"{tool} on {what}, {tiles} tile{'' if tiles == 1 else 's'}"


def paint(sess: PaintSession, body: dict) -> dict:
    """One press of one tool. The whole of what a stroke is.

    Answers with the tiles that changed and the colour they changed to, which
    is what the browser writes into its own copy. Tiles that were already the
    colour being painted are not in it - a stroke over ground that is already
    right is not a change, and undoing it should not repaint anything.
    """
    cm = sess.cm
    w, h = cm.terrain.width, cm.terrain.height
    tool = str(body.get("tool") or "")
    if tool not in TOOLS:
        raise MapError(f"{tool!r} is not a tool - it is one of "
                       f"{', '.join(TOOLS)} (the pipette reads, it never writes)")
    colours = _resolve(cm, sess, body)

    if tool == "bucket":
        pt = body.get("points") or []
        if not pt:
            raise MapError("a bucket needs the tile it was clicked on")
        seed = (int(pt[-1][0]), int(pt[-1][1]))
        tiles = flood(cm, body.get("target") or "regions", seed[0], seed[1])
    elif tool == "pencil":
        tiles = expand(body.get("points") or [], 1, "square", w, h)
    else:
        tiles = expand(body.get("points") or [], body.get("size") or 1,
                       str(body.get("shape") or "round"), w, h)
    if not tiles:
        raise MapError("that stroke covered no tile of the map")

    marker = str(body.get("marker") or "")
    if marker:
        _check_marker(cm, sess, body, tiles)

    # Markers are protected on every stroke that is not itself placing one: a
    # brush that ran over a settlement pixel would delete a city, and a bucket
    # that flooded a sea would delete every port on its coast.
    guard = not body.get("marker")
    reg = cm.tiles("regions").tobytes() if guard else b""
    protected = 0

    stroke = Stroke(tool=tool, rgb=dict(colours))
    for code, k in colours.items():
        stroke.px[code] = array("i")
        stroke.tiles[code] = array("i")
    rule = {c: LAYER_BY_CODE[c]["size"] for c in colours}
    views = {c: cm.tiles(c).tobytes() for c in colours}

    for (tx, ty) in tiles:
        i = ty * w + tx
        if guard:
            p = i * 3
            if ((reg[p] << 16) | (reg[p + 1] << 8) | reg[p + 2]) in PROTECTED:
                protected += 1
                continue
        for code, k in colours.items():
            data = views[code]
            p = i * 3
            was = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
            if was == k:
                continue                   # already right: not a change
            stroke.tiles[code].extend((tx, ty, was))
            buf, stride, width = sess.buffer(code)
            x0, y0, x1, y1 = block(rule[code], tx, ty)
            for py in range(y0, y1 + 1):
                base = py * width
                for px in range(x0, x1 + 1):
                    q = (base + px) * stride
                    stroke.px[code].extend(
                        (px, py, (buf[q] << 16) | (buf[q + 1] << 8) | buf[q + 2]))

    stroke.protected = protected
    stroke.px = {c: a for c, a in stroke.px.items() if a}
    stroke.tiles = {c: a for c, a in stroke.tiles.items() if a}
    if not stroke.px:
        return {"ok": True, "changed": {}, "tiles": 0, "protected": protected,
                "note": ("every tile in that stroke was already this colour"
                         if not protected else
                         f"{protected} marker pixel"
                         f"{'' if protected == 1 else 's'} protected, and every "
                         f"other tile was already this colour"),
                "state": sess.state()}
    stroke.rgb = {c: colours[c] for c in stroke.px}
    stroke.label = _label(tool, stroke.px, stroke.tile_count, body)
    sess.apply_px(stroke, True)
    sess.push(stroke)
    return {"ok": True, "changed": _painted(stroke), "tiles": stroke.tile_count,
            "protected": protected, "label": stroke.label,
            "note": (f"{protected} settlement or port pixel"
                     f"{'' if protected == 1 else 's'} left alone"
                     if protected else ""),
            "state": sess.state()}


def undo_stroke(sess: PaintSession) -> dict:
    if not sess.undo:
        raise MapError("there is nothing to undo")
    s = sess.undo.pop()
    sess.apply_px(s, False)
    sess.redo.append(s)
    return {"ok": True, "restored": _reverted(s), "label": s.label,
            "state": sess.state()}


def redo_stroke(sess: PaintSession) -> dict:
    if not sess.redo:
        raise MapError("there is nothing to redo")
    s = sess.redo.pop()
    sess.apply_px(s, True)
    sess.undo.append(s)
    return {"ok": True, "changed": _painted(s), "label": s.label,
            "state": sess.state()}


# ---------------------------------------------------------------------------
# the new-region wizard
#
# Mylae's three steps - paint the province, place its settlement, place its port
# or skip - with the rule Mylae states and the four the two file formats state.
# It is a wizard rather than a form because the order matters: a settlement
# cannot be checked against a province that has no pixels yet.

#: A new record is written in the shape the rest of the file is in, and these
#: are the defaults, each with the source that fixes it.
NEW_REGION_DEFAULTS = {
    "triumph": campmap.TRIUMPH_USUAL,     # Geomod: "leave it at 5"
    "farming": 4,                         # Geomod: "4 is approximately average"
}


def start_region(sess: PaintSession, body: dict) -> dict:
    """Open the wizard: the record the painting is going to be for.

    Everything about the record is decided before a pixel is painted, and that
    is the point of doing it first: the colour has to exist before the brush can
    snap to it, and it has to be checked for being free before anyone spends ten
    minutes painting with it.
    """
    cm = sess.cm
    name = str(body.get("name") or "").strip()
    settlement = str(body.get("settlement") or "").strip()
    if not name or " " in name:
        raise MapError("a region needs a name with no spaces in it - it is a "
                       "key descr_strat.txt and the campaign script point at")
    if not settlement or " " in settlement:
        raise MapError("a settlement needs a name with no spaces in it, for the "
                       "same reason the region does")
    if cm.regions.by_name(name):
        raise MapError(f"descr_regions.txt already has a region called {name}")
    if any(r.settlement.lower() == settlement.lower() for r in cm.regions.records):
        raise MapError(f"descr_regions.txt already has a settlement called "
                       f"{settlement}")
    try:
        rgb = (int(body["rgb"][0]), int(body["rgb"][1]), int(body["rgb"][2]))
    except (TypeError, ValueError, IndexError, KeyError):
        raise MapError("a region colour is three numbers 0-255") from None
    k = key(rgb)
    if k in PROTECTED:
        raise MapError(f"{rgb[0]} {rgb[1]} {rgb[2]} is a marker colour - black "
                       f"is where a settlement stands and white is where a port "
                       f"does, so neither can be a province")
    taken = cm.regions.by_rgb(rgb)
    if taken is not None:
        raise MapError(f"{rgb[0]} {rgb[1]} {rgb[2]} is already "
                       f"{taken.name}'s colour")
    if k in cm.index.by_key:
        raise MapError(f"{rgb[0]} {rgb[1]} {rgb[2]} is already painted on "
                       f"map_regions.tga, on "
                       f"{cm.index.by_key[k].pixels} tile(s), and no record "
                       f"declares it - fix that hole before adding to it")
    sess.new_region = {
        "name": name, "settlement": settlement, "rgb": list(rgb), "key": k,
        "legion": str(body.get("legion") or ""),
        "faction": str(body.get("faction") or "").strip(),
        "rebels": str(body.get("rebels") or "").strip(),
        "resources": [r.strip() for r in (body.get("resources") or []) if str(r).strip()],
        "triumph": int(body.get("triumph", NEW_REGION_DEFAULTS["triumph"])),
        "farming": int(body.get("farming", NEW_REGION_DEFAULTS["farming"])),
        "religions": {str(a): int(b) for a, b in (body.get("religions") or {}).items()},
        "port": bool(body.get("port")),
    }
    return {"ok": True, "state": sess.state()}


def cancel_region(sess: PaintSession) -> dict:
    sess.new_region = None
    return {"ok": True, "state": sess.state()}


def region_progress(cm: CampaignMap, spec: dict) -> dict:
    """Where the wizard has got to, measured off the painted pixels.

    Not remembered - counted. The wizard's three steps are three questions about
    the map as it stands, and a step counter that could disagree with the pixels
    is a step counter that will.
    """
    w, h = cm.terrain.width, cm.terrain.height
    data = cm.tiles("regions").tobytes()
    want = spec["key"]
    own = [i for i in range(w * h)
           if ((data[i * 3] << 16) | (data[i * 3 + 1] << 8) | data[i * 3 + 2]) == want]
    seat = _marker_in(cm, data, want, key(SETTLEMENT_RGB))
    port = _marker_in(cm, data, want, key(PORT_RGB))
    return {"tiles": len(own), "settlement": seat, "port": port,
            "step": 1 if not own else 2 if seat is None else 3}


def _marker_in(cm: CampaignMap, data: bytes, want: int, marker: int):
    """The marker pixel this region owns, by the engine's own rule, or None.

    **Gigantus's cardinal rule, not "a marker somewhere near my tiles".** The
    engine gives a settlement pixel to the first of N, W, E, S that is a region,
    which is what :func:`campmap._owner_of_marker` already implements for the
    index - and on a real map that distinction is the whole answer, because
    every province borders another and a marker one tile the wrong side of a
    border belongs to the neighbour. A wizard that counted proximity would
    cheerfully report the city next door as this region's.

    The pending region counts as a region here, which the index cannot do: the
    index only knows colours ``descr_regions.txt`` declares, and this one is not
    declared until the save. Everything else is the same rule, so what the panel
    says now is what the index will say once the record is written.
    """
    w, h = cm.terrain.width, cm.terrain.height
    known = {r.rgb_key for r in cm.regions.records if r.rgb_line >= 0}
    known.discard(key(SETTLEMENT_RGB))
    known.discard(key(PORT_RGB))
    known.add(want)

    def at(i):
        p = i * 3
        return (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]

    for i in range(w * h):
        if at(i) != marker:
            continue
        x, y = i % w, i // w
        for dx, dy, _ in campmap._CARDINALS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            k = at(ny * w + nx)
            if k not in known:
                continue
            if k == want:
                return [x, y]
            break                  # this one is the neighbour's; try the next
    return None


def check_new_region(cm: CampaignMap, spec: dict) -> List[dict]:
    """Every rule a new province has to pass, with what said so.

    ``fatal`` refuses the save; the rest are warnings with their source, in the
    shape :func:`campmap.check_record` already uses.
    """
    out: List[dict] = []

    def add(fatal: bool, message: str) -> None:
        out.append({"fatal": fatal, "field": "region", "message": message})

    w, h = cm.terrain.width, cm.terrain.height
    data = cm.tiles("regions").tobytes()
    want = spec["key"]
    own = [i for i in range(w * h)
           if ((data[i * 3] << 16) | (data[i * 3 + 1] << 8) | data[i * 3 + 2]) == want]
    if not own:
        add(True, f"not one tile of map_regions.tga is painted "
                  f"{spec['rgb'][0]} {spec['rgb'][1]} {spec['rgb'][2]}, so "
                  f"{spec['name']} would be a region with no land")
        return out

    # contiguous, four-connected. A province in two pieces is two provinces as
    # far as movement is concerned, and the engine numbers it as one.
    ours = set(own)
    stack = [own[0]]
    seen = {own[0]}
    while stack:
        i = stack.pop()
        x = i % w
        for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1),
                      (i - w, i >= w), (i + w, i + w < w * h)):
            if ok and j in ours and j not in seen:
                seen.add(j)
                stack.append(j)
    if len(seen) != len(ours):
        add(False, f"{spec['name']} is painted in more than one piece "
                   f"({len(ours) - len(seen)} tile(s) are not joined to the "
                   f"rest). The engine will treat it as one region, and an army "
                   f"cannot walk between the pieces.")

    # Mylae's rule: a new region has to touch an existing one, or nothing can
    # ever reach it. Sea does not count - a province whose only neighbour is
    # the ocean needs a port, and the port is step three.
    touches: Set[int] = set()
    for i in ours:
        x = i % w
        for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1),
                      (i - w, i >= w), (i + w, i + w < w * h)):
            if not ok or j in ours:
                continue
            p = j * 3
            k = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2]
            if k in PROTECTED:
                continue
            reg = cm.index.by_key.get(k)
            if reg is not None and reg.record is not None:
                touches.add(k)
    if not touches:
        add(True, f"{spec['name']} does not share an edge with any declared "
                  f"region. A province nothing borders is a province no army "
                  f"can walk into, and only a port would ever reach it.")

    seat = _marker_in(cm, data, want, key(SETTLEMENT_RGB))
    if seat is None:
        add(True, f"{spec['settlement']} has nowhere to stand - place the "
                  f"settlement pixel inside {spec['name']} before saving")
    else:
        for fatal, message in _marker_problems(cm, seat, "settlement"):
            add(fatal, message)
    port = _marker_in(cm, data, want, key(PORT_RGB))
    if spec.get("port") and port is None:
        add(False, "no port pixel was placed, so this province has no harbour. "
                   "That is legal; the wizard's third step is a skip.")
    if port is not None:
        for fatal, message in _marker_problems(cm, port, "port"):
            add(fatal, message)

    total = sum(spec.get("religions", {}).values())
    if spec.get("religions") and total != 100:
        add(True, f"the religion percentages total {total}, and the game "
                  f"crashes on load unless they total 100 ({total - 100:+d})")
    if not spec.get("faction"):
        add(True, "a region needs a creator faction - it is the third line of "
                  "the record and the engine reads it positionally")
    return out


def _marker_problems(cm: CampaignMap, at: Sequence[int], kind: str):
    """What is wrong with the tile a settlement or a port is standing on.

    The two rules that crash rather than annoy, both from the TWCenter index:
    a marker on impassable or sea ground, and a marker on a river, ford, source
    or volcano. A port is the exception to the first - it stands on the coast
    and its dock is in the water - so its ground is checked the other way round.
    """
    x, y = int(at[0]), int(at[1])
    i = y * cm.terrain.width + x
    out = []
    try:
        g = cm.tiles("ground_types").tobytes()
        f = cm.tiles("features").tobytes()
    except MapError as exc:
        return [(False, str(exc))]
    ground = mapvocab.ground_at(((g[i * 3]), g[i * 3 + 1], g[i * 3 + 2]))
    feat = mapvocab.feature_at((f[i * 3], f[i * 3 + 1], f[i * 3 + 2]))
    if kind == "settlement":
        if ground and ground["code"] in mapvocab.BLOCKING_GROUND:
            out.append((True, f"the settlement pixel at {x},{y} stands on "
                              f"{ground['name']} ground, which nothing can stand "
                              f"on - the game drops back to the menu"))
        if cm.sea[i]:
            out.append((True, f"the settlement pixel at {x},{y} stands on a tile "
                              f"map_heights.tga says is sea"))
    if feat and feat["code"] in mapvocab.FATAL_UNDER_SETTLEMENT:
        out.append((True, f"the {kind} pixel at {x},{y} stands on a "
                          f"{feat['name'].lower()} on map_features.tga, which is "
                          f"the back-to-menu crash"))
    if kind == "port":
        w, h = cm.terrain.width, cm.terrain.height
        near = [j for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1),
                                (i - w, y > 0), (i + w, y < h - 1)) if ok]
        if not any(cm.sea[j] for j in near):
            out.append((False, f"the port pixel at {x},{y} has no sea tile beside "
                               f"it, so it is a harbour inland - the ships have "
                               f"nowhere to sail from"))
    return out


def new_record_lines(cm: CampaignMap, spec: dict) -> List[str]:
    """The new record, in the shape the rest of the file is written in.

    The indent and whether a ``legion:`` line is written are read off the file
    rather than chosen: DaC writes the legion form on 197 of its 198 records and
    vanilla writes none at all, and a new record that does not match its
    neighbours is a new record somebody has to tidy up after the tool.
    """
    recs = cm.regions.records
    lines = cm.regions.lines
    indent = "\t"
    for r in recs:
        if r.settlement_line >= 0:
            got = lines[r.settlement_line]
            indent = got[:len(got) - len(got.lstrip())] or "\t"
            break
    legion = spec.get("legion")
    if legion is None or legion == "":
        # match the file: write one when most records have one
        if recs and sum(1 for r in recs if r.legion_line >= 0) * 2 > len(recs):
            legion = spec["name"]
        else:
            legion = ""
    out = [spec["name"]]
    if legion:
        out.append(f"{indent}legion: {legion}")
    out.append(f"{indent}{spec['settlement']}")
    out.append(f"{indent}{spec['faction']}")
    out.append(f"{indent}{spec['rebels'] or 'brigands'}")
    out.append(f"{indent}{spec['rgb'][0]} {spec['rgb'][1]} {spec['rgb'][2]}")
    if spec.get("resources"):
        out.append(indent + ", ".join(spec["resources"]))
    out.append(f"{indent}{spec['triumph']}")
    out.append(f"{indent}{spec['farming']}")
    rel = spec.get("religions") or {}
    body = " ".join(f"{n} {v}" for n, v in rel.items())
    out.append(f"{indent}religions {{ {body} }}" if body
               else f"{indent}religions {{ }}")
    return out


def regions_with_record(cm: CampaignMap, spec: dict) -> str:
    """``descr_regions.txt`` with the new record spliced in.

    Appended, with one exception that is the arbiter's: a record with no
    settlement is a wasteland and **must be the last entry in the file**, so a
    new province goes in front of it rather than after it.
    """
    rf = cm.regions
    lines = list(rf.lines)
    at = len(lines)
    waste = next((r for r in rf.records if r.wasteland), None)
    if waste is not None and waste.span[0] >= 0:
        at = waste.span[0]
    # a blank line between records, the way the file already separates them
    body = new_record_lines(cm, spec)
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    return rf.newline.join(lines[:at] + [""] + body + lines[at:]) + (
        rf.newline if rf.trailing_newline else "")


# ---------------------------------------------------------------------------
# the save


@dataclass
class PaintPlan:
    """Everything one save would write, worked out without touching the disk."""

    mod: object = None
    session: Optional[PaintSession] = None
    layers: List[dict] = field(default_factory=list)
    region: Optional[dict] = None
    region_text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: code -> the whole file as it would be written
    data: Dict[str, bytes] = field(default_factory=dict)

    def summary(self) -> str:
        head = (f"paint {getattr(self.mod, 'name', '?')}'s campaign map "
                f"({len(self.layers)} layer(s)"
                + (f", + region {self.region['name']}" if self.region else "")
                + ")")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"layers": list(self.layers), "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings),
                "region": dict(self.region) if self.region else None,
                "ok": not self.errors and bool(self.data or self.region_text)}


def plan_paint(sess: PaintSession) -> PaintPlan:
    """What a save would write, and everything that would refuse it.

    The bytes are built here rather than at apply time, and that is the same
    ruling :func:`campmap.plan_region` makes: a layer that will not encode is a
    layer that must fail before the backup is taken, not half way through
    writing the third of eight files.
    """
    cm = sess.cm
    p = PaintPlan(mod=sess.mod, session=sess)
    if not sess.unsaved and not sess.new_region:
        p.errors.append("nothing has been painted")
        return p

    for code in sess.unsaved:
        info = cm.info(code)
        img = cm.layer(code)
        try:
            data = encode(img, info)
        except Exception as exc:                        # noqa: BLE001
            p.errors.append(f"{info.path.name if info.path else code} could not "
                            f"be re-encoded: {exc}")
            continue
        # A layer that has been painted and then undone back to where it started
        # is not a change, and writing it would put a file in the backup set and
        # a line in the log for nothing. The comparison is the bytes, not the
        # stroke count: two strokes that cancel each other out are also nothing.
        try:
            if info.path and info.path.read_bytes() == data:
                continue
        except OSError:
            pass
        p.data[code] = data
        p.layers.append({"code": code, "file": LAYER_BY_CODE[code]["file"],
                         "shape": info.describe(),
                         "was": info.size_bytes, "now": len(data)})
        p.changes.append(f"{LAYER_BY_CODE[code]['file']}: "
                         f"{info.size_bytes:,} -> {len(data):,} bytes, "
                         f"{info.describe()}")

    # A region left with no pixels is legal to write and fatal to play, and it
    # is the one thing painting the region layer can do by accident, so it is
    # counted rather than trusted to the validator that comes after this phase.
    if "regions" in p.data:
        gone = _emptied(cm)
        if gone:
            p.errors.append(
                f"{len(gone)} region(s) would be left with no tiles at all: "
                + ", ".join(gone[:6]) + ("…" if len(gone) > 6 else "")
                + ". That is legal to write and fatal to play.")
        colours = len(cm.index.by_key)
        if colours > mapvocab.MAX_REGION_COLOURS:
            p.warnings.append(
                f"map_regions.tga now has {colours} colours and the engine's "
                f"cap is {mapvocab.MAX_REGION_COLOURS}, markers included")

    if sess.new_region:
        spec = sess.new_region
        p.findings = check_new_region(cm, spec)
        p.errors += [f["message"] for f in p.findings if f["fatal"]]
        p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
        p.region = dict(spec)
        prog = region_progress(cm, spec)
        p.region["progress"] = prog
        if not p.errors:
            p.region_text = regions_with_record(cm, spec)
            p.changes.append(
                f"descr_regions.txt: a new record for {spec['name']} "
                f"({prog['tiles']:,} tiles, settlement at "
                f"{prog['settlement'][0]},{prog['settlement'][1]})")
            # A region ID is the engine's scan order over map_regions.tga, not a
            # number written in any file, so a new province quietly renumbers
            # every one the scan reaches after it. Nothing in the mod has to be
            # edited for that - names are the keys - but a script that hard-codes
            # a region number is now pointing somewhere else, and this is the one
            # moment anybody could be told.
            mine = cm.index.by_key.get(spec["key"])
            after = sum(1 for r in cm.index.regions
                        if r.region_id > (mine.region_id if mine else -1))
            if after:
                p.warnings.append(
                    f"{spec['name']} takes region ID "
                    f"{mine.region_id if mine else '?'}, and the {after} "
                    f"region(s) the engine scans after it each move up by one. "
                    f"A region ID is the scan order of map_regions.tga rather "
                    f"than anything written down, so no file needs editing - but "
                    f"a script that names a region by number now names a "
                    f"different one.")
    if not p.data and not p.region_text and not p.errors:
        p.errors.append("nothing has been painted")
    return p


def _emptied(cm: CampaignMap) -> List[str]:
    """Declared regions whose colour is no longer on the map at all."""
    present = {k for k in cm.index.by_key}
    return [r.name for r in cm.regions.records if r.rgb_key not in present]


def apply_paint(p: PaintPlan) -> dict:
    """Write the painted layers, with the same backups and undo as any job.

    Every layer that changed, plus ``descr_regions.txt`` when a province was
    added, plus ``map.rwm`` deleted - all of it in one backup set and one log
    entry, so the Log's Undo puts the whole save back byte-exact in one go
    rather than leaving a mod half-painted.
    """
    import shutil

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data and not p.region_text:
        raise ValueError("nothing has been painted")
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

    for code, data in p.data.items():
        rel = f"{BASE_REL}/{LAYER_BY_CODE[code]['file']}"
        target = keep(rel)
        target.write_bytes(data)
        file_op("WRITE", target, f"{len(data)} bytes")

    if p.region_text:
        target = keep(REGIONS_REL)
        write_text(target, p.region_text, ENCODING)
        file_op("WRITE", target, f"{len(p.region_text)} bytes")

    rwm = Path(mod.data) / RWM_REL
    if rwm.exists():
        keep(RWM_REL)
        rwm.unlink()
        manifest["deleted"].append(RWM_REL)
        file_op("DELETE", rwm, "stale compiled map - the game would load it instead")

    what = p.region["name"] if p.region else ", ".join(
        LAYER_BY_CODE[c]["label"] for c in sorted(p.data))
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "paint",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": what, "resolved_type": what,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("PAINT  %s - %d layer(s)%s, id=%s", mod.name, len(p.data),
             f", + region {p.region['name']}" if p.region else "", tid)
    return {"id": tid, "layers": sorted(p.data),
            "region": p.region["name"] if p.region else "", "record": rec}
