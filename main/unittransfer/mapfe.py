"""The front-end picture, framed - authoring ``map_FE.tga`` (37b, T3).

``map_FE.tga`` is the one picture on the map screen that nothing here helps
anybody author. It is the layer whose ``size`` rule is ``free``: it has no
relationship to the tile grid, :func:`campmap.layer_view` says ``aligned:
false`` about it rather than pretending otherwise, and that honest refusal is
where the toolkit stopped. This module is what turns the refusal into the
workflow the layer exists for.

The upstream ask (T3) is one sentence: keep the picture at its native size and
scale everything else to meet it, so a front-end map can be traced and saved
with *"no loss of quality due to scaling up and then scaling down again"*.

**The frame is what the ask was missing, and it is the whole module.** A
front-end picture is a picture of *some rectangle of the map at some scale*,
and until that rectangle is named there is no such thing as "native size" -
the picture's shape and the map's are not the same shape in any installed mod:

===========================  =========  =======  ==================
file                         pixels     aspect   the grid's aspect
===========================  =========  =======  ==================
DaC ``imperial_campaign``    768x768    1.000    1.047 (510x487)
Third Age Reforged (all 3)   320x275    1.164    1.047
DaC base, Shattered All.     245x170    1.441    1.047
BCBuff (both)                384x275    1.396    1.448 (420x290)
===========================  =========  =======  ==================

**Eight files, six of them distinct, four distinct sizes, three mods, and not
one of them is its own map's shape** - the closest, BCBuff's, is still 3.6%
out. Reforged ships one file in three places, byte for byte; DaC's two 245x170
files are a different picture each; and BCBuff's prologue spells it
``map_fe.tga`` in lower case, which is the only reason to say that this module
asks :mod:`campmap` for the path rather than building one.

So :func:`frame` makes the rectangle carry the *picture's* aspect
instead: the smallest rect of the picture's shape that contains the whole grid.
With a frame of the picture's shape a single scalar zoom draws the picture at
exactly one image pixel per screen pixel and leaves the map underneath
undistorted, which is what the view transform in ``web/js/campmap.js`` can
express and an anisotropic stretch is not.

**The default is not a guess - it is what the artists used.** Registering each
real picture against its own ``map_regions.tga`` by the moments of the two land
masks gives the scale that mod's author actually drew at. Against
:func:`frame`'s default:

* DaC ``imperial_campaign``: default 1.506 px per tile, measured 1.524 in x -
  **1.2% apart**.
* Third Age Reforged: default 0.565, measured 0.566 in y - **0.2% apart**.

Only one axis of each is quoted, and that is deliberate: the land mask is taken
from colour, DaC's front-end map has a pale blue-green sea against tan land and
separates cleanly, and Reforged's is a sepia painting whose sea and land are
the same parchment - the mask there reads 98.2% land and its x figure is the
mask's fault, not a measurement. **A picture cannot be registered from its own
pixels in general**, which is exactly why the frame is the author's and this
module proposes rather than derives.

**Two of the eight are not maps at all, and one of the six that are does not
fill its own frame.** DaC's ``base`` picture is the "DAC EUR" logo - mountains
and lettering - and its ``Shattered_Alliances`` one is four faction emblems
over the word "DaC"; neither has any geography in it. BCBuff's is a map, but a
map inside a painted ornamental border, so the geography stops short of the
picture's edge on all four sides.

Nothing here detects any of that and nothing here should. A front-end picture
is whatever the mod wants on that screen, :mod:`mapcheck`'s baseline rule is
that somebody else's choice is not a finding, and "is this a map" is not a
question pixels answer - which is the same reason the frame is *proposed* and
then the author's to move. A bordered picture wants a frame inset from the
edges and this module cannot know by how much; an author drags it in, and the
default is the right starting point for the six that are maps.

**The double resampling is real and this is the fix.** ``cmapComposite`` draws
every layer into one canvas that is ``width x height`` *tiles* - 510x487 - and
the view then scales that canvas onto the stage. DaC's 768x768 picture is
therefore squashed into 510x487 and scaled again before anybody sees it, and
Reforged's 320x275 is stretched up and scaled back down. That is the loss T3
names, in this toolkit, today. :func:`render` never resamples the picture at
all: it composes at the picture's own pixel size and the picture goes in 1:1.

**An export reuses the file's own header**, the rule :func:`mapquery._write_tga`
already follows for the per-faction pictures: the depth, the origin, the
run-length flag and the trailer are the mod's, so what comes out can be dropped
straight back over what went in. A mod that ships no ``map_FE.tga`` has no
header to reuse, so :func:`header_for` makes a plain 24-bit top-origin one and
says so, rather than refusing an author their first one.

Nothing here writes into the mod. An export lands in the cache beside every
other, through :func:`mapquery.export_dir`, for the reason that function gives.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image

from . import campmap, campstrat
from .maptga import TYPE_RAW, TgaError, TgaInfo, encode

#: The layer this module is about. One place, so a rename is one edit.
CODE = "fe"

#: How big an export is allowed to get. A ``free`` layer has no size rule at
#: all, so a frame and a size arrive from the browser with nothing in the
#: format to bound them, and "compose an image at whatever you were sent" is
#: how a tool runs a machine out of memory. Vanilla's own is 510x487 and the
#: largest installed is 768x768; four thousand a side is far past any of them
#: and still only 48 MB of RGB.
MAX_SIDE = 4096

#: The smallest frame worth composing, in tiles. Below this the scale is such
#: that no two provinces are distinguishable and the request is a slip.
MIN_TILES = 4


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


class FeError(ValueError):
    """The front-end picture cannot be framed, rendered or written."""


# ---------------------------------------------------------------------------
# the frame


@dataclass
class Frame:
    """A rectangle of the tile grid, carrying the picture's shape.

    Tile coordinates, and they are deliberately floats: the frame's whole job
    is to have the *picture's* aspect ratio, and a rect snapped to whole tiles
    can only do that when the numbers happen to divide. ``x`` and ``y`` may be
    negative and ``x + w`` may run past the grid - a picture that shows sea
    beyond the map's edge is the normal case, not an error, and DaC's is one.
    """

    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0

    @property
    def aspect(self) -> float:
        return self.w / self.h if self.h else 0.0

    def zoom(self, px_w: int) -> float:
        """Screen pixels per tile that draws a ``px_w``-wide picture at 1:1."""
        return px_w / self.w if self.w else 0.0

    def payload(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4),
                "w": round(self.w, 4), "h": round(self.h, 4)}


def frame(grid: Tuple[int, int], picture: Tuple[int, int]) -> Frame:
    """The default frame: the smallest rect of the picture's shape holding the
    whole grid, centred on it.

    Around the grid and not inside it. A frame inside would crop the map, and
    an author who opens this panel wants to see the map they are drawing, all
    of it; the sea a "fit around" frame adds at the short edge is sea the
    finished picture wants anyway. Both installed mods' own pictures agree -
    see the module docstring for the two figures.
    """
    gw, gh = grid
    pw, ph = picture
    if gw <= 0 or gh <= 0:
        raise FeError(f"the tile grid is {gw}x{gh}")
    if pw <= 0 or ph <= 0:
        raise FeError(f"the picture is {pw}x{ph}")
    want = pw / ph
    w, h = float(gw), float(gh)
    if want > w / h:
        w = h * want
    else:
        h = w / want
    return Frame(x=(gw - w) / 2.0, y=(gh - h) / 2.0, w=w, h=h)


def check_frame(fr: Frame, grid: Tuple[int, int]) -> None:
    """Refuse a frame nothing could be composed from. Never warns about one
    that merely leaves the grid - that is the normal case."""
    gw, gh = grid
    if not (fr.w > 0 and fr.h > 0):
        raise FeError(f"the frame is {fr.w:g}x{fr.h:g} tiles")
    if fr.w < MIN_TILES or fr.h < MIN_TILES:
        raise FeError(f"the frame is {fr.w:g}x{fr.h:g} tiles, and fewer than "
                      f"{MIN_TILES} a side is not a picture of anything")
    if fr.x >= gw or fr.y >= gh or fr.x + fr.w <= 0 or fr.y + fr.h <= 0:
        raise FeError(f"the frame at ({fr.x:g},{fr.y:g}) {fr.w:g}x{fr.h:g} "
                      f"does not touch the {gw}x{gh} grid")


# ---------------------------------------------------------------------------
# the file, and the header an export is written through


def fe_map(mod, campaign: str, cm: "campmap.CampaignMap") -> "campmap.CampaignMap":
    """The map object the front-end picture is read from for this campaign.

    :func:`campmap.layer_map`'s job, named here because every caller in this
    module wants it and because it is the one thing about this layer that
    surprises: ``campaign_map`` hands back the *base* map for a campaign whose
    only own file is ``map_FE.tga``, since nothing is decided on a picture, and
    both of DaC's campaigns are that case.
    """
    return campmap.layer_map(mod, campaign, cm, CODE)


def picture(cm: "campmap.CampaignMap") -> Optional[Image.Image]:
    """The front-end picture, or ``None`` when this campaign ships none."""
    try:
        return cm.layer(CODE)
    except (campmap.MapError, TgaError, OSError):
        return None


def header_for(cm: "campmap.CampaignMap", size: Tuple[int, int]
               ) -> Tuple[TgaInfo, bool]:
    """``(header, borrowed)`` for an export of ``size``.

    ``borrowed`` is True when it is the mod's own file's header with the width
    and height swapped in - the depth, the origin, the compression and the
    trailer are all the mod's, so the file that comes out is the shape of the
    file that went in. False when the mod ships no front-end picture and this
    is a plain 24-bit top-origin header made here, which is the case an author
    writing their *first* ``map_FE.tga`` is in and is not a reason to refuse.
    """
    w, h = size
    try:
        info = cm.info(CODE)
    except (campmap.MapError, TgaError, OSError):
        info = None
    if info is None:
        return TgaInfo(image_type=TYPE_RAW, width=w, height=h, depth=24,
                       descriptor=0x20), False
    # Same fields, new size. `replace` rather than mutation: the CampaignMap
    # keeps this object and hands the same one to the next caller.
    import dataclasses
    return dataclasses.replace(info, width=w, height=h), True


# ---------------------------------------------------------------------------
# composing at the picture's own size


def render(cm: "campmap.CampaignMap", fr: Frame, size: Tuple[int, int],
           layers: Sequence[dict], backdrop: Tuple[int, int, int] = (0, 0, 0),
           ) -> Image.Image:
    """The frame's contents, composed at ``size`` - the picture's own pixels.

    ``layers`` is ``[{"code": ..., "opacity": ...}, ...]``, bottom first, the
    order the screen draws them in. Every one of them is sampled through
    :func:`campmap.tile_view`, so what lands here is what the engine reads at a
    tile, not the raw file: a ``centre`` layer's block centres and a ``double``
    layer's top-left corners, the same rule the canvas uses.

    The front-end picture itself is not in ``layers`` and cannot be - it is the
    thing being authored, it is what ``size`` came from, and drawing it into
    its own frame is how a tracing tool produces a copy of the last export
    instead of a picture of the map. :func:`compare` is what puts the two side
    by side.

    Nearest neighbour throughout, and up as well as down. A province colour is
    a key, ``map_regions.tga``'s colours are exact or they are a different
    province, and an interpolated pixel between two provinces belongs to
    neither. This picture is traced over, not shipped, so a hard edge is the
    useful artefact and a soft one is a lie about where the coast is.
    """
    w, h = size
    if not (0 < w <= MAX_SIDE and 0 < h <= MAX_SIDE):
        raise FeError(f"{w}x{h} is not a size this can compose - "
                      f"it is 1 to {MAX_SIDE} a side")
    check_frame(fr, (cm.terrain.width, cm.terrain.height))

    out = Image.new("RGB", (w, h), backdrop)
    sx, sy = w / fr.w, h / fr.h          # picture pixels per tile
    for spec in layers:
        code = str(spec.get("code") or "")
        if code == CODE:
            raise FeError("the front-end picture cannot be one of the layers "
                          "traced onto it - that is a copy of itself")
        if code not in campmap.LAYER_BY_CODE:
            raise FeError(f"no such layer {code!r}")
        try:
            tile = campmap.tile_view(cm, code).convert("RGB")
        except (campmap.MapError, TgaError, OSError):
            # a layer that will not read is left out, not fatal: the other
            # eight still make a picture and the caller is told which went
            continue
        opacity = float(spec.get("opacity", 1.0))
        if opacity <= 0:
            continue
        # Where the whole layer WOULD land, then clipped to the picture before
        # anything is scaled. Cropping first is not an optimisation: scaling the
        # layer up and then throwing most of it away is how a 4-tile frame at
        # 4096 px allocates a 300 MB intermediate for a 50 MB result. Bounded by
        # the output this way, and no frame can make it otherwise.
        dx0, dy0 = -fr.x * sx, -fr.y * sy
        dx1, dy1 = dx0 + tile.width * sx, dy0 + tile.height * sy
        cx0, cy0 = max(0, math.floor(dx0)), max(0, math.floor(dy0))
        cx1, cy1 = min(w, math.ceil(dx1)), min(h, math.ceil(dy1))
        if cx1 <= cx0 or cy1 <= cy0:
            continue                      # this layer is entirely outside
        # The part of the layer that maps onto that rectangle, in layer pixels,
        # clamped into the layer. The clamp matters and only ever at an edge:
        # the destination rectangle is whole pixels and the layer's own corner
        # rarely falls on one, so the box would otherwise start a fraction of a
        # pixel outside the image and PIL refuses that outright. Clamping moves
        # the outermost row or column by under one picture pixel; every pixel
        # that is not on an edge is exactly where the frame puts it, and a frame
        # that lands on whole pixels - the whole grid at its own size - is exact
        # throughout.
        box = (_clamp((cx0 - dx0) / sx, 0.0, float(tile.width)),
               _clamp((cy0 - dy0) / sy, 0.0, float(tile.height)),
               _clamp((cx1 - dx0) / sx, 0.0, float(tile.width)),
               _clamp((cy1 - dy0) / sy, 0.0, float(tile.height)))
        if box[2] - box[0] <= 0 or box[3] - box[1] <= 0:
            continue
        part = tile.resize((cx1 - cx0, cy1 - cy0), Image.NEAREST, box=box)
        if opacity >= 1.0:
            out.paste(part, (cx0, cy0))
        else:
            under = out.crop((cx0, cy0, cx1, cy1))
            out.paste(Image.blend(under, part, opacity), (cx0, cy0))
    return out


def compare(cm: "campmap.CampaignMap", fr: Frame, layers: Sequence[dict],
            ) -> Optional[Image.Image]:
    """The map under the frame at the *existing* picture's size, for checking
    a frame against the picture already on disk. ``None`` when there is none.

    This is the one thing that tells an author whether their frame is right:
    the two images are the same size, so flipping between them moves nothing
    and a coastline that does not sit still is a frame that is off.
    """
    img = picture(cm)
    if img is None:
        return None
    return render(cm, fr, img.size, layers)


# ---------------------------------------------------------------------------
# what the panel asks for when it opens


def view(mod, campaign: str, cm: "campmap.CampaignMap") -> dict:
    """Everything the FE panel needs before it draws anything.

    Never raises for a mod that ships no front-end picture: ``present`` is
    False, ``frame`` is still offered - at the grid's own shape, since there is
    no picture to take one from - and the panel can still author and export.
    """
    fcm = fe_map(mod, campaign, cm)
    grid = (cm.terrain.width, cm.terrain.height)
    out: dict = {"code": CODE, "file": campmap.LAYER_BY_CODE[CODE]["file"],
                 "campaign": campstrat.campaign_rel(campaign),
                 "grid": list(grid), "present": False, "problem": "",
                 "native": None, "rel": "", "depth": 0, "borrowed": False,
                 "max_side": MAX_SIDE}
    path = fcm.path(CODE)
    out["rel"] = path.relative_to(Path(fcm.mod.data)).as_posix()
    img = picture(fcm)
    if img is None:
        out["problem"] = ("this campaign ships no map_FE.tga, so there is no "
                          "size to match - the frame below is the grid's own "
                          "shape and the export is 24-bit")
        fr = frame(grid, grid)
        out["frame"] = fr.payload()
        out["size"] = list(grid)
        out["zoom"] = round(fr.zoom(grid[0]), 6)
        return out
    out["present"] = True
    out["native"] = [img.width, img.height]
    out["size"] = [img.width, img.height]
    try:
        info = fcm.info(CODE)
        out["depth"] = info.depth
        out["rle"] = info.rle
        out["top_origin"] = info.top_origin
        out["borrowed"] = True
    except (campmap.MapError, TgaError, OSError) as exc:
        out["problem"] = str(exc)
    fr = frame(grid, (img.width, img.height))
    out["frame"] = fr.payload()
    out["zoom"] = round(fr.zoom(img.width), 6)
    # what the screen was doing before this panel existed, said plainly,
    # because it is the reason the panel is worth opening
    out["was"] = (f"{img.width}x{img.height} squeezed into {grid[0]}x{grid[1]} "
                  f"and scaled again" if (img.width, img.height) != grid else "")
    return out


# ---------------------------------------------------------------------------
# the export


@dataclass
class Export:
    """What one front-end export wrote."""

    folder: str = ""
    files: List[dict] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    ms: int = 0

    def payload(self) -> dict:
        return {"folder": self.folder, "files": self.files,
                "skipped": self.skipped, "count": len(self.files),
                "bytes": sum(f["bytes"] for f in self.files), "ms": self.ms}


def export(mod, campaign: str, cm: "campmap.CampaignMap", fr: Frame,
           layers: Sequence[dict], size: Optional[Tuple[int, int]] = None,
           name: str = "") -> Export:
    """The frame, written as a TGA at the picture's own size.

    ``size`` defaults to the existing picture's, which is the whole point: an
    export that is the size of the file it is meant to replace drops straight
    over it. A caller may name another - an author making a larger one than the
    mod ships - and then the header is the mod's with that size in it.
    """
    from .mapquery import export_dir

    t0 = time.perf_counter()
    out = Export()
    fcm = fe_map(mod, campaign, cm)
    if size is None:
        img = picture(fcm)
        size = (img.width, img.height) if img is not None else (
            cm.terrain.width, cm.terrain.height)
    img = render(cm, fr, size, layers)
    info, borrowed = header_for(fcm, size)
    try:
        data = encode(img, info)
    except TgaError as exc:
        raise FeError(str(exc)) from exc
    folder = export_dir(mod, "fe")
    out.folder = str(folder)
    slug = campstrat.campaign_rel(campaign).replace("/", "_") or "base"
    path = folder / (name or f"map_FE_{slug}.tga")
    path.write_bytes(data)
    out.files.append({
        "name": path.name, "bytes": len(data), "label": "Front-end map",
        "width": size[0], "height": size[1], "depth": info.depth,
        "header": "the mod's own map_FE.tga" if borrowed else "24-bit, made here",
        "frame": fr.payload(), "layers": [s.get("code") for s in layers]})
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out
