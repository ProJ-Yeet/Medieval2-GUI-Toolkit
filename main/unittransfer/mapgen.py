"""Phase 27, M11. Layers made from something else: the real world, or each other.

Mylae's ``BboxLayerGenerator``, ``FeaturesLayerGenerator`` and
``autoGroundTypes``, rebuilt. Four generators, each a plan that says what it
would write and shows it before anything is written, then one write with one
backup set and one Undo in the Log:

``heights``   the real ground under the map's box, from elevation tiles
              (Terrarium, the AWS Open Data set Mylae uses), onto
              ``map_heights.tga``;
``ground``    ground types from the heights, by bands of altitude, onto the land
              of ``map_ground_types.tga``;
``climates``  climates from the ground types, onto ``map_climates.tga``;
``features``  rivers, cliffs and volcanoes from OpenStreetMap, onto
              ``map_features.tga``;
``adjust``    (87c) brightness, contrast, gamma and equalize on the land of
              ``map_heights.tga``, Mylae's ``HeightmapAdjustPanel``.

The first and the last use the network and are under Phase 25's switch: off
until Settings turns it on, and the box is the Real world tab's. The middle two
read only the map.

**Measured against the engine, not copied.** Three things differ from the
reference, and each is the engine's own rule:

* **The heights are true to scale.** The engine reads a land pixel as
  ``max_land_height * grey / 255`` metres and a sea pixel's blue as a depth
  down to ``min_sea_height`` (``world_map.cpp``, and the radar draws it back the
  same way). So a real mountain is written at the grey its height is, against
  this map's own ``descr_terrain.txt``, rather than stretched so the highest
  peak in the box is white. Stretching is still there, as a choice.
* **Sea depths are real too**, when the whole map is written: Terrarium carries
  the sea floor, and the blue channel is the engine's depth.
* **A river is drawn the way the engine can build it.** Mylae's generator draws
  eight-connected Bresenham lines and puts a source at the start of every
  chain; the tutorial and our own validator say diagonal steps are gaps, loops
  have no mouth and a river under a city is a crash. Here a river is walked in
  cardinal steps, a step that would close a loop ends it, a tributary ends
  where it meets its trunk, a settlement tile cuts the river in two, and each
  course gets one source at its upstream end. OSM draws a waterway downstream,
  so the upstream end is the first point.

**Land only, by default.** A generator that writes heights over the whole box
also moves the coastline, and the regions and ground types do not follow. So
the default writes land where the map already has land and leaves the sea as
it is; *the whole map* is a choice, and the plan says what it leaves behind.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from array import array

from PIL import Image, ImageChops, ImageMath

from . import campmap, config, mapvocab, osmmap
from .campmap import RWM_REL, MapError
from .maptga import encode
from .mapnew import corner_view

KINDS = ("heights", "adjust", "ground", "climates", "features",
         "landuse", "landcover", "koppen")

#: Terrarium elevation tiles: ``R*256 + G + B/256 - 32768`` metres. AWS Open
#: Data, the set Mylae's editor reads.
DEFAULT_ELEVATION = ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"]
#: The most elevation tiles one plan may ask for.
ELEVATION_BUDGET = 400

#: Mylae's default bands: a land pixel's grey, up to and including ``max``,
#: is that ground type. The first band that fits wins.
GROUND_BANDS: List[Tuple[str, int]] = [
    ("beach", 5), ("fertility_low", 40), ("fertility_medium", 80),
    ("fertility_high", 120), ("hills", 160), ("mountains_low", 200),
    ("mountains_high", 255)]

#: Mylae's ground -> climate table, by the vanilla climate names. A mod that
#: does not declare one of these climates keeps that ground type's climate as
#: it is, and the plan says which. His temperate grassland and swamp are the
#: slots vanilla calls ``unused1`` and ``unused2`` (his colours are theirs);
#: until 87d this table named two climates no mod declares.
CLIMATE_OF: Dict[str, str] = {
    "beach": "mediterranean", "fertility_low": "mediterranean",
    "fertility_medium": "unused1",
    "fertility_high": "temperate_deciduous_forest", "wilderness": "steppe",
    "forest_sparse": "temperate_deciduous_forest",
    "forest_dense": "temperate_coniferous_forest", "swamp": "unused2",
    "hills": "highland", "mountains_low": "alpine", "mountains_high": "alpine",
    "impassable_land": "alpine"}

#: How much of OSM's waterways a detail level takes.
RIVER_DETAIL = {"major": "river", "medium": "river|canal",
                "all": "river|stream|canal"}
#: A river shorter than this, in tiles, is not worth a course.
MIN_RIVER = 4
#: How far a river may run out into the sea, which the tutorial asks for: two
#: tiles past the coast make a mouth.
MOUTH = 2


class GenError(ValueError):
    """The form, the map or the answer from the network will not do."""


# ---------------------------------------------------------------------------
# the plan


@dataclass
class GenPlan:
    """One generator's output, worked out without writing."""

    mod: object = None
    kind: str = ""
    home: str = ""
    data: Dict[str, bytes] = field(default_factory=dict)
    #: a small PNG of the layer as it would be, for the panel
    preview: bytes = b""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        head = f"generate {self.kind} for {getattr(self.mod, 'name', '?')}"
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        import base64
        return {"kind": self.kind, "files": sorted(self.data),
                "preview": ("data:image/png;base64,"
                            + base64.b64encode(self.preview).decode("ascii"))
                           if self.preview else "",
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.data)}


def _png(img: Image.Image, longest: int = 420) -> bytes:
    scale = longest / max(img.size)
    small = img.convert("RGB").resize(
        (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
        Image.NEAREST)
    buf = io.BytesIO()
    small.save(buf, "PNG")
    return buf.getvalue()


def _layer(cm, code: str) -> Tuple[Image.Image, object, str]:
    """``(image, info, data-relative path)`` of the file this map reads."""
    img = cm.layer(code).convert("RGB")
    return img, cm.info(code), campmap.rel_of(cm, campmap.LAYER_BY_CODE[code]["file"])


def _put(p: GenPlan, cm, code: str, img: Image.Image, info, rel: str) -> None:
    p.data[rel] = encode(img.convert(info.mode), info)
    p.preview = _png(img)


def _sea_corners(cm) -> Image.Image:
    """255 on every corner of the 2W+1 grid whose tile the engine reads as sea."""
    w, h = cm.terrain.width, cm.terrain.height
    tiles = Image.frombytes("L", (w, h), bytes(255 if v else 0 for v in cm.sea))
    return corner_view(tiles)


def _count(mask: Image.Image) -> int:
    """How many pixels of an 'L' mask are set."""
    return mask.histogram()[255]


def _math(expr: str, **images) -> Image.Image:
    """``ImageMath`` under whichever name this Pillow gives it."""
    if hasattr(ImageMath, "unsafe_eval"):
        return ImageMath.unsafe_eval(expr, **images)
    return ImageMath.eval(expr, **images)                 # Pillow before 10.3


def plan(mod, cm, body: dict) -> GenPlan:
    kind = str(body.get("kind") or "")
    p = GenPlan(mod=mod, kind=kind)
    if kind not in KINDS:
        p.errors.append(f"no generator called {kind!r}; there are {', '.join(KINDS)}")
        return p
    try:
        if kind in ("landuse", "landcover", "koppen"):
            from . import mapreal          # 87d, which builds on this module
            mapreal.plan(p, cm, body)
        else:
            {"heights": _plan_heights, "adjust": _plan_adjust, "ground": _plan_ground,
             "climates": _plan_climates, "features": _plan_features}[kind](p, cm, body)
    except (GenError, osmmap.OsmError, MapError) as exc:
        p.errors.append(str(exc))
    return p


# ---------------------------------------------------------------------------
# heights, from the real world


def elevation_servers() -> List[str]:
    s = config.load_settings()
    v = s.get("osm_elevation")
    if isinstance(v, str):
        v = [x.strip() for x in v.splitlines()]
    v = [str(x).strip() for x in (v or []) if str(x).strip()]
    return v or list(DEFAULT_ELEVATION)


def elevation_tile(z: int, x: int, y: int) -> Image.Image:
    """One Terrarium tile as metres (an 'F' picture), kept on disk like the
    backdrop's tiles."""
    path = config.cache_dir("elevation") / str(z) / str(x) / f"{y}.png"
    raw = None
    try:
        if path.is_file() and time.time() - path.stat().st_mtime < osmmap.TILE_DAYS * 86400:
            raw = path.read_bytes()
    except OSError:
        raw = None
    if raw is None:
        osmmap.require_on()
        last = None
        for tpl in elevation_servers():
            try:
                raw = osmmap._fetch(tpl.replace("{z}", str(z)).replace("{x}", str(x))
                                    .replace("{y}", str(y)), timeout=30)
                break
            except (OSError, ValueError) as e:            # URLError is an OSError
                last = e
        if raw is None:
            raise GenError(f"no elevation server answered ({last})")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        except OSError:
            pass
    r, g, b = Image.open(io.BytesIO(raw)).convert("RGB").split()
    return _math("float(r) * 256.0 + float(g) + float(b) / 256.0 - 32768.0",
                 r=r, g=g, b=b)


def _lon2x(lon: float, z: int) -> float:
    return (lon + 180) / 360 * (2 ** z) * 256


def _lat2y(lat: float, z: int) -> float:
    lat = max(-osmmap.MAX_LAT, min(osmmap.MAX_LAT, lat))
    r = math.radians(lat)
    return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * (2 ** z) * 256


def elevation(box, cols: int, rows: int) -> Image.Image:
    """Metres at every corner of a ``cols x rows`` grid spread over ``box``.

    Corner ``(i, j)`` stands where tile coordinate ``((i-1)/2, (j-1)/2)`` does
    in the Real world tab's projection, so the heights line up with the
    backdrop and the coastline. The zoom is Mylae's rule - the first at which
    the tiles cover the grid one and a half times over - and the samples are
    bilinear between the tile pixels.

    Longitude is linear across both the tiles and the map, and so is the
    Mercator of the latitude, so the whole resampling is one affine transform
    of the stitched picture: Pillow does it, in C. A turned box (87a) is still
    one affine transform, since turning is linear in the same two, and only the
    tiles under its envelope are fetched.
    """
    w, h = (cols - 1) // 2, (rows - 1) // 2
    proj = osmmap.Projection(box, w, h)
    env = box.envelope()
    z = 12
    for zz in range(3, 13):
        wide = _lon2x(env.east, zz) - _lon2x(env.west, zz)
        tall = _lat2y(env.south, zz) - _lat2y(env.north, zz)
        if wide >= 1.5 * cols and tall >= 1.5 * rows:
            z = zz
            break

    def span(zz):
        return (int(_lon2x(env.west, zz) // 256), int(_lon2x(env.east, zz) // 256),
                int(_lat2y(env.north, zz) // 256), int(_lat2y(env.south, zz) // 256))

    x0, x1, y0, y1 = span(z)
    while (x1 - x0 + 1) * (y1 - y0 + 1) > ELEVATION_BUDGET and z > 3:
        z -= 1
        x0, x1, y0, y1 = span(z)
    big = Image.new("F", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            big.paste(elevation_tile(z, tx % (2 ** z), ty),
                      ((tx - x0) * 256, (ty - y0) * 256))
    # corner (i, j) -> the stitched picture's continuous coordinates (a pixel's
    # centre at k + .5, where its sample stands): affine in (i, j), so three
    # corners fix it. Corner i stands at tile (i - 1) / 2. Pillow samples output
    # pixel (x, y) at the continuous point a * (x + .5) + b * (y + .5) + c.
    size = 2 ** z * 256

    def pix(i, j):
        lon, m = proj.to_lonmerc((i - 1) / 2, (j - 1) / 2)
        return ((lon + 180) / 360 * size - x0 * 256,
                (1 - m / math.pi) / 2 * size - y0 * 256)

    (p0x, p0y), (p1x, p1y), (p2x, p2y) = pix(1, 1), pix(3, 1), pix(1, 3)
    a, b = (p1x - p0x) / 2, (p2x - p0x) / 2
    d, e = (p1y - p0y) / 2, (p2y - p0y) / 2
    c, f = p0x - a - b, p0y - d - e
    return big.transform((cols, rows), Image.AFFINE,
                         (a, b, c - 0.5 * a - 0.5 * b, d, e, f - 0.5 * d - 0.5 * e),
                         Image.BILINEAR)


def _floats(img: Image.Image) -> array:
    return array("f", img.tobytes())


def _plan_heights(p: GenPlan, cm, body: dict) -> None:
    box, where = osmmap.box_for(cm)
    if box is None:
        raise GenError("the map has no real-world box yet; set one on the Real "
                       "world tab first")
    img, info, rel = _layer(cm, "heights")
    cols, rows = img.size
    metres = elevation(box, cols, rows)
    t = cm.terrain
    whole = str(body.get("area") or "land") == "whole"
    stretch = str(body.get("scale") or "true") == "stretch"
    land_now = ImageChops.invert(_sea_corners(cm))
    if whole:
        new_land = _math("convert((m > 0) * 255, 'L')", m=metres)
    else:
        new_land = land_now
    m, mask = _floats(metres), new_land.tobytes()
    top = max((v for v, k in zip(m, mask) if k), default=1.0)
    if stretch:
        scale = 255.0 / max(top, 1.0)
        what = f"stretched so the highest ground, {top:,.0f} m, is white"
    else:
        scale = 255.0 / max(t.max_land_height, 1.0)
        what = (f"true to scale against descr_terrain.txt's max_land_height of "
                f"{t.max_land_height:,.0f} m (the highest ground here is "
                f"{top:,.0f} m)")
        if top > t.max_land_height:
            p.warnings.append(
                f"the highest ground in the box, {top:,.0f} m, is above "
                f"max_land_height ({t.max_land_height:,.0f} m), so it is cut off "
                f"at white. Raise max_land_height, or stretch instead.")
    # grey = metres * scale, rounded, never under 1: black reads as sea
    grey = ImageChops.lighter(metres.point(lambda v: v * scale + 0.5).convert("L"),
                              Image.new("L", img.size, 1))
    out = img.copy()
    out.paste(Image.merge("RGB", (grey, grey, grey)), mask=new_land)
    if whole:
        depth = ImageChops.lighter(
            metres.point(lambda v: 255.0 - 255.0 * v / min(t.min_sea_height, -1.0) + 0.5)
            .convert("L"), Image.new("L", img.size, 1))
        zero = Image.new("L", img.size, 0)
        out.paste(Image.merge("RGB", (zero, zero, depth)),
                  mask=ImageChops.invert(new_land))
        moved = _count(ImageChops.difference(new_land, land_now).point(
            lambda v: 255 if v else 0))
        p.warnings.append(
            f"the whole map is written, so {moved:,} corner(s) change between "
            f"land and sea. map_regions.tga and map_ground_types.tga do not "
            f"follow; the validator will list where they disagree, and the Real "
            f"world tab's coastline can repaint the regions.")
    _put(p, cm, "heights", out, info, rel)
    p.changes.append(f"{rel}: {'every corner' if whole else 'the land'} from the "
                     f"real ground under the box ({where}), {what}")


# ---------------------------------------------------------------------------
# 87c: the heights adjusted, land only


def _num(body: dict, key: str, default: float, lo: float, hi: float) -> float:
    try:
        v = float(body.get(key, default))
    except (TypeError, ValueError):
        raise GenError(f"{key} has to be a number") from None
    if not lo <= v <= hi:
        raise GenError(f"{key} runs from {lo:g} to {hi:g}")
    return v


def adjust_lut(brightness: float = 0, contrast: float = 0, gamma: float = 1.0) -> List[int]:
    """Mylae's three sliders as one table, grey in to grey out: contrast about
    the middle, then brightness, then the gamma curve. Never under 1, which
    would read as sea."""
    b, c = brightness * 2.55, contrast * 2.55
    factor = (259 * (c + 255)) / (255 * (259 - c))
    out = []
    for v in range(256):
        r = max(0.0, min(255.0, factor * (v - 128) + 128 + b))
        r = 255 * (r / 255) ** (1 / gamma)
        out.append(max(1, min(255, round(r))))
    return out


def _plan_adjust(p: GenPlan, cm, body: dict) -> None:
    """Mylae's heightmap adjust, on land only. His works on the red and green
    of every pixel and keeps the blue, which turns a sea pixel (0, 0, 255) into
    (v, v, 255), land by the engine's rule, and a land pixel into one that is
    not grey. Here a pixel the engine reads as sea (red and green 0, blue above
    0) is never touched, and a land pixel's three channels move together."""
    br = _num(body, "brightness", 0, -100, 100)
    ct = _num(body, "contrast", 0, -100, 100)
    ga = _num(body, "gamma", 1, 0.1, 3)
    eq = bool(body.get("equalize"))
    if not eq and br == 0 and ct == 0 and ga == 1:
        raise GenError("move a slider or tick equalize first: as it stands, nothing changes")
    img, info, rel = _layer(cm, "heights")
    r, g, bch = img.split()
    sea = _math("convert(((r == 0) & (g == 0) & (b > 0)) * 255, 'L')", r=r, g=g, b=bch)
    land = ImageChops.invert(sea)
    lut = list(range(256))
    if eq:
        hist = r.histogram(mask=land)
        total = sum(hist)
        cdf, run = [], 0
        for n in hist:
            run += n
            cdf.append(run)
        low = next((v for v in cdf if v), 0)
        # one grey all over has nothing to spread (Mylae's leaves it too); below
        # the lowest land grey nothing is mapped, so those stay as they are
        if total - low > 0:
            lut = [max(1, round(1 + (cdf[i] - low) * 254 / (total - low))) if cdf[i] else i
                   for i in range(256)]
    tone = adjust_lut(br, ct, ga)
    lut = [tone[v] for v in lut]
    grey = r.point(lut)
    out = img.copy()
    out.paste(Image.merge("RGB", (grey, grey, grey)), mask=land)
    moved = _count(ImageChops.difference(out.convert("L"), img.convert("L"))
                   .point(lambda v: 255 if v else 0))
    off_grey = _count(ImageChops.multiply(
        _math("convert(((r != g) | (g != b)) * 255, 'L')", r=r, g=g, b=bch), land))
    _put(p, cm, "heights", out, info, rel)
    what = ", ".join(x for x in (
        "equalized" if eq else "", f"brightness {br:+g}" if br else "",
        f"contrast {ct:+g}" if ct else "", f"gamma {ga:g}" if ga != 1 else "") if x)
    p.changes.append(f"{rel}: the land {what}; {moved:,} corner(s) change, the sea none")
    if off_grey:
        p.warnings.append(f"{off_grey:,} land corner(s) were not grey (red, green and blue "
                          f"not equal); they come out grey, from their red")


# ---------------------------------------------------------------------------
# ground and climates, from the map itself


def _bands(body: dict) -> List[Tuple[str, int]]:
    got = body.get("bands")
    if not got:
        return list(GROUND_BANDS)
    out = []
    for row in got:
        code, top = str(row[0]), int(row[1])
        if mapvocab.ground(code) is None:
            raise GenError(f"{code!r} is not a ground type")
        out.append((code, top))
    out.sort(key=lambda r: r[1])
    if not out or out[-1][1] < 255:
        raise GenError("the last band has to reach 255, or some ground has no type")
    return out


def _land_corners(heights: Image.Image) -> Image.Image:
    """255 where a ``map_heights.tga`` pixel is land: grey and not black."""
    r, g, b = heights.convert("RGB").split()
    spread = ImageChops.lighter(ImageChops.difference(r, g), ImageChops.difference(g, b))
    grey = spread.point(lambda v: 255 if v == 0 else 0)
    lit = r.point(lambda v: 255 if v else 0)
    return ImageChops.multiply(grey, lit)


def _plan_ground(p: GenPlan, cm, body: dict) -> None:
    bands = _bands(body)
    heights = cm.layer("heights").convert("RGB")
    img, info, rel = _layer(cm, "ground_types")
    land = _land_corners(heights)
    table = [(0, 0, 0)] * 256
    lo = 0
    for code, top in bands:
        for v in range(lo, top + 1):
            table[v] = mapvocab.ground(code)["rgb"]
        lo = top + 1
    r = heights.split()[0]
    typed = Image.merge("RGB", tuple(r.point([table[v][c] for v in range(256)])
                                     for c in range(3)))
    out = img.copy()
    out.paste(typed, mask=land)
    hist = r.histogram(mask=land)
    counts, lo = {}, 0
    for code, top in bands:
        counts[code] = counts.get(code, 0) + sum(hist[lo:top + 1])
        lo = top + 1
    _put(p, cm, "ground_types", out, info, rel)
    p.changes.append(f"{rel}: {_count(land):,} land corner(s) typed by height - "
                     + ", ".join(f"{c} {n:,}" for c, n in counts.items() if n))
    p.changes.append("the sea is left as it is; on land every corner is "
                     "replaced, forests and swamps too")


def _equal(img: Image.Image, rgb) -> Image.Image:
    """255 where ``img`` is exactly ``rgb``."""
    parts = [band.point(lambda v, want=want: 255 if v == want else 0)
             for band, want in zip(img.split(), rgb)]
    return ImageChops.multiply(ImageChops.multiply(parts[0], parts[1]), parts[2])


def _plan_climates(p: GenPlan, cm, body: dict) -> None:
    have = {c["code"]: c for c in mapvocab.climates(p.mod) if c.get("rgb")}
    fill = str(body.get("fill") or "").strip()
    if fill:
        # 87d: Mylae's "fill the entire map with one climate", sea and all
        clim = have.get(fill)
        if clim is None:
            raise GenError(f"this mod declares no climate called {fill!r}")
        img, info, rel = _layer(cm, "climates")
        _put(p, cm, "climates", Image.new("RGB", img.size, tuple(clim["rgb"])), info, rel)
        p.changes.append(f"{rel}: every corner {fill}, the sea too")
        return
    mapping = dict(CLIMATE_OF)
    mapping.update({str(k): str(v) for k, v in (body.get("mapping") or {}).items()})
    ground = cm.layer("ground_types").convert("RGB")
    img, info, rel = _layer(cm, "climates")
    if img.size != ground.size:
        raise GenError("map_climates.tga and map_ground_types.tga are not the "
                       "same size")
    out = img.copy()
    done, missing = {}, []
    for gcode, ccode in mapping.items():
        gt = mapvocab.ground(gcode)
        if gt is None or ccode in ("", "-"):
            continue                      # "-" is the panel's "leave as it is"
        clim = have.get(ccode)
        if clim is None:
            missing.append(f"{gcode} -> {ccode}")
            continue
        mask = _equal(ground, gt["rgb"])
        out.paste(tuple(clim["rgb"]), mask=mask)
        done[gcode] = _count(mask)
    if not done:
        raise GenError("this mod declares none of the climates the table names; "
                       "choose a climate for each ground type first")
    _put(p, cm, "climates", out, info, rel)
    p.changes.append(f"{rel}: " + ", ".join(
        f"{g} {n:,} -> {mapping[g]}" for g, n in done.items() if n))
    if missing:
        p.warnings.append("this mod has no climate for " + "; ".join(missing)
                          + ", so those corners keep the climate they have")


# ---------------------------------------------------------------------------
# rivers, cliffs and volcanoes, from OpenStreetMap


def _osm_features(box, detail: str) -> dict:
    """The waterways, cliffs and volcanoes in the box, kept on disk by the box."""
    key = hashlib.sha1(json.dumps([box.payload(), detail], sort_keys=True)
                       .encode()).hexdigest()[:16]
    path = config.cache_dir("osm_features") / f"{key}.json.gz"
    try:
        if path.is_file():
            return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError):
        pass
    osmmap.require_on()
    out = {"rivers": {}, "cliffs": {}, "volcanoes": []}

    def one(c):
        bb = f"({c.south},{c.west},{c.north},{c.east})"
        q = (f"[out:json][timeout:180][maxsize:536870912];("
             f"way[\"waterway\"~\"^({RIVER_DETAIL[detail]})$\"]{bb};"
             f"way[\"natural\"=\"cliff\"]{bb};"
             f"node[\"natural\"=\"volcano\"]{bb};);out geom;")
        try:
            data = osmmap.overpass(q)
        except osmmap.OsmError:
            if (c.north - c.south) / 2 < osmmap.CHUNK_MIN:
                raise
            mlat, mlon = (c.north + c.south) / 2, (c.east + c.west) / 2
            for part in (osmmap.Bbox(c.north, mlat, c.west, mlon),
                         osmmap.Bbox(c.north, mlat, mlon, c.east),
                         osmmap.Bbox(mlat, c.south, c.west, mlon),
                         osmmap.Bbox(mlat, c.south, mlon, c.east)):
                one(part)
            return
        for e in data.get("elements", []):
            tags = e.get("tags") or {}
            if e.get("type") == "node" and tags.get("natural") == "volcano":
                out["volcanoes"].append((e["lat"], e["lon"]))
                continue
            geo = [(round(q["lat"], 6), round(q["lon"], 6))
                   for q in (e.get("geometry") or []) if q]
            if len(geo) < 2:
                continue
            bucket = "cliffs" if tags.get("natural") == "cliff" else "rivers"
            out[bucket][str(e["id"])] = geo

    for c in osmmap._chunks(box, osmmap.CHUNK_DEG):
        one(c)
    try:
        path.write_bytes(gzip.compress(json.dumps(out).encode("utf-8")))
    except OSError:
        pass
    return out


def chain(ways: Sequence[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
    """Waterways joined end to start, keeping OSM's downstream direction.

    A way is joined onto the one it starts where that one ends, but only when
    that end is where no other way also starts: a fork is two rivers, not one.
    """
    # points come back from the JSON cache as lists; a point is a key here
    ways = [[tuple(pt) for pt in w] for w in ways if len(w) > 1]
    starts: Dict[Tuple[float, float], List[int]] = {}
    ends: Dict[Tuple[float, float], List[int]] = {}
    for i, w in enumerate(ways):
        starts.setdefault(w[0], []).append(i)
        ends.setdefault(w[-1], []).append(i)
    nxt, has_prev = {}, set()
    for i, w in enumerate(ways):
        after = starts.get(w[-1], [])
        if len(after) == 1 and len(ends.get(w[-1], [])) == 1 and after[0] != i:
            nxt[i] = after[0]
            has_prev.add(after[0])
    out, used = [], set()
    for i in range(len(ways)):
        if i in has_prev or i in used:
            continue
        line, j = list(ways[i]), i
        used.add(i)
        while j in nxt and nxt[j] not in used:
            j = nxt[j]
            used.add(j)
            line += ways[j][1:]
        out.append(line)
    for i in range(len(ways)):                 # a loop of ways nobody starts
        if i not in used:
            used.add(i)
            out.append(list(ways[i]))
    return out


def cardinal(points: Sequence[Tuple[float, float]]) -> List[Tuple[int, int]]:
    """A line through tile centres as four-connected tiles, no repeats in a row."""
    out: List[Tuple[int, int]] = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        for x, y in osmmap._line(int(round(x0)), int(round(y0)),
                                 int(round(x1)), int(round(y1))):
            if out and out[-1] == (x, y):
                continue
            if out and abs(out[-1][0] - x) == 1 and abs(out[-1][1] - y) == 1:
                out.append((x, out[-1][1]))          # the corner, stepped round
            out.append((x, y))
    if len(points) == 1:
        out.append((int(round(points[0][0])), int(round(points[0][1]))))
    return out


class Rivers:
    """The river network as it is drawn, kept a tree by union-find."""

    def __init__(self, w: int, h: int, sea: bytes, blocked: set):
        self.w, self.h, self.sea, self.blocked = w, h, sea, blocked
        self.parent: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.sources: List[Tuple[int, int]] = []

    def _find(self, a):
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def _around(self, t):
        x, y = t
        return [(x + dx, y + dy) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                if (x + dx, y + dy) in self.parent]

    def add(self, tiles: Sequence[Tuple[int, int]]) -> int:
        """Draw one course; returns how many tiles went in, 0 if none did."""
        course: List[Tuple[int, int]] = []
        local = set()
        seen_sea = 0
        started = False
        joined = False
        for t in tiles:
            x, y = t
            if not (0 <= x < self.w and 0 <= y < self.h):
                if started:
                    break
                continue
            wet = bool(self.sea[y * self.w + x])
            if not started:
                if wet:
                    continue                           # a river starts on land
                started = True
            if wet:
                seen_sea += 1
                if seen_sea > MOUTH:
                    break
            if t in self.blocked:
                break                                  # a city: the river ends
            if t in self.parent:
                break                                  # met the trunk
            if t in local:
                break                                  # doubled back
            # the tiles this one would touch: the last of the course, and any
            # river already drawn. Touching two of the same tree is a loop.
            near = self._around(t)
            others = [self._find(n) for n in near]
            if len(set(others)) != len(others):
                break                                  # two taps on one tree
            if any(abs(c[0] - x) + abs(c[1] - y) == 1 for c in course[:-1]):
                break                                  # runs alongside itself
            if any(len(self._around(n)) >= 3 for n in near):
                break                                  # would make a four-way
            course.append(t)
            local.add(t)
            if near:
                joined = True
                break                                  # a tributary, joined
        if len(course) < MIN_RIVER and not (joined and len(course) >= 2):
            return 0
        for t in course:
            self.parent[t] = t
        for a, b in zip(course, course[1:]):
            self.parent[self._find(a)] = self._find(b)
        for n in self._around(course[-1]):
            if n not in course:
                self.parent[self._find(n)] = self._find(course[-1])
        self.sources.append(course[0])
        return len(course)


def _plan_features(p: GenPlan, cm, body: dict) -> None:
    box, where = osmmap.box_for(cm)
    if box is None:
        raise GenError("the map has no real-world box yet; set one on the Real "
                       "world tab first")
    detail = str(body.get("detail") or "major")
    if detail not in RIVER_DETAIL:
        raise GenError(f"detail is one of {', '.join(RIVER_DETAIL)}")
    got = _osm_features(box, detail)
    w, h = cm.terrain.width, cm.terrain.height
    proj = osmmap.Projection(box, w, h)
    img, info, rel = _layer(cm, "features")
    out = img.copy()
    px = out.load()
    f = mapvocab.feature
    replace = str(body.get("mode") or "replace") == "replace"
    rivers = {tuple(f(c)["rgb"]) for c in mapvocab.RIVER_CODES}
    drop = rivers | ({tuple(f("cliff")["rgb"]), tuple(f("volcano")["rgb"])}
                     if replace else set())
    none = tuple(f("none")["rgb"])
    old: List[Tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if c in drop:
                if replace:
                    px[x, y] = none
                elif c in rivers:
                    old.append((x, y))
    sea = cm.sea
    idx = cm.index
    blocked = set(idx.settlements) | set(idx.ports)
    net = Rivers(w, h, sea, blocked)
    for t in old:
        net.parent[t] = t
    for t in old:
        for n in net._around(t):
            net.parent[net._find(n)] = net._find(t)
    # a settlement or a port on a river's line cuts it in two: the water above
    # the city is one river, the water below it another with its own source
    courses = []
    for line in chain(list(got["rivers"].values())):
        piece: List[Tuple[int, int]] = []
        for t in cardinal([proj.to_tile(lat, lon) for lat, lon in line]):
            if t in blocked:
                if piece:
                    courses.append(piece)
                piece = []
                continue
            piece.append(t)
        if piece:
            courses.append(piece)
    courses.sort(key=len, reverse=True)
    drawn = tiles = 0
    for course in courses:
        n = net.add(course)
        if n:
            drawn += 1
            tiles += n
    river = tuple(f("river")["rgb"])
    for (x, y) in net.parent:
        px[x, y] = river
    for (x, y) in net.sources:
        px[x, y] = tuple(f("river_source")["rgb"])

    def free(x: int, y: int) -> bool:
        return (0 <= x < w and 0 <= y < h and not sea[y * w + x]
                and (x, y) not in net.parent and (x, y) not in blocked)

    cliffs = 0
    for line in got["cliffs"].values():
        for x, y in cardinal([proj.to_tile(lat, lon) for lat, lon in line]):
            if free(x, y):
                px[x, y] = tuple(f("cliff")["rgb"])
                cliffs += 1
    volc = 0
    for lat, lon in got["volcanoes"]:
        fx, fy = proj.to_tile(lat, lon)
        x, y = int(round(fx)), int(round(fy))
        if free(x, y):
            px[x, y] = tuple(f("volcano")["rgb"])
            volc += 1
    _put(p, cm, "features", out, info, rel)
    p.changes.append(
        f"{rel}: {drawn} river course(s), {tiles:,} tiles, one source each, from "
        f"OSM's {RIVER_DETAIL[detail].replace('|', ', ')} ({len(got['rivers'])} "
        f"way(s) under the box, {where}); {cliffs:,} cliff tile(s); {volc} volcano(es)")
    p.changes.append("drawn in cardinal steps, a tributary ending where it meets "
                     "its trunk, cut at every settlement and port, never "
                     "closing a loop" + ("; the old rivers, cliffs and volcanoes "
                                         "were cleared first" if replace else
                                         "; the old rivers are kept and joined"))
    if len(courses) > drawn:
        p.warnings.append(f"{len(courses) - drawn} OSM course(s) were too short "
                          f"to draw at this map's scale (under {MIN_RIVER} tiles "
                          f"of land)")


# ---------------------------------------------------------------------------
# the save


def apply(p: GenPlan) -> dict:
    """Write the layer, with one backup set and one Undo, and drop map.rwm."""
    import shutil

    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data:
        raise ValueError("nothing to write")
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

    for rel, blob in sorted(p.data.items()):
        keep(rel).write_bytes(blob)
        file_op("WRITE", Path(mod.data) / rel, f"{len(blob)} bytes")
    for rw in sorted({str(Path(rel).parent.as_posix() + "/" + Path(RWM_REL).name)
                      for rel in p.data}):
        rwm = Path(mod.data) / rw
        if rwm.exists():
            keep(rw)
            rwm.unlink()
            manifest["deleted"].append(rw)
            file_op("DELETE", rwm, "stale compiled map - the game would load it")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "map_generate",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": f"generate {p.kind}", "resolved_type": p.kind,
        "options": {"kind": p.kind}, "applied": True, "undone": False,
        "note": "", "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("MAPGEN %s - %s, id=%s", mod.name, p.kind, tid)
    return {"id": tid, "kind": p.kind, "files": sorted(p.data), "record": rec}


def view(mod) -> dict:
    """What the panel offers: the bands, the climate table, the mod's climates."""
    return {"bands": [list(b) for b in GROUND_BANDS],
            "grounds": [g["code"] for g in mapvocab.GROUND_TYPES
                        if g["code"] not in mapvocab.SEA_GROUND],
            "climate_of": dict(CLIMATE_OF),
            "climates": [{"code": c["code"], "name": c["name"]}
                         for c in mapvocab.climates(mod) if c.get("rgb")],
            "detail": list(RIVER_DETAIL), "network": osmmap.settings()["enabled"],
            "elevation": elevation_servers(), "real": _real_view(mod)}


def _real_view(mod) -> dict:
    from . import mapreal                  # 87d
    return mapreal.view(mod)
