"""Phase 87d. Ground types and climates from the real world.

Three generators beside Phase 27's four, on the same plan-then-write rails
(``mapgen.plan`` hands these kinds here), each a preview and one Undo:

``landuse``    Mylae's ``OsmTagOverlayEditor``: 47 OpenStreetMap tags
               (farmland, wood, marsh, bare rock...) in his five groups, each
               painted as the ground type chosen for it, in the order listed;
``landcover``  his ``LandCoverFetcher``: ESA WorldCover's eleven classes, each
               a ground type;
``koppen``     his ``KoppenClimateFetcher``: the Köppen-Geiger zone under every
               corner, each a climate.

**Where each departs from his, and why.**

* **Land only, and holes kept.** His tag overlay fills every ring of a
  multipolygon, holes too, and means to spare the sea by skipping (0, 0, 255),
  which on a ground-type layer is never the sea's colour, so it paints the sea.
  Here only land corners (grey on the heights) are painted and an inner ring is
  cut back out.
* **Palette colours only.** His land cover blends the ground colours of the
  four nearest pixels, which makes colours in no palette where two classes
  meet. Here each corner takes one class: the most common in the block around
  it when the picture is finer than the map.
* **No borrowed key.** His Köppen map comes from a service with a private key
  written into his source, which is not ours to use. Here the zones come from
  **the published Köppen-Geiger map as a file on disk** (Beck et al., CC BY
  4.0; the 0.083° or 0.5° GeoTIFF, values 1-30 in the standard order, which
  Pillow reads), so it needs no network at all; or from a WMS address put in
  Settings, empty until someone has one.
* **No LERC.** His land cover reads LERC-compressed ArcGIS tiles, which need a
  decoder the release does not carry. Here it is a WMS that serves the classes
  as a picture in ESA's own legend colours (the address in Settings), which
  Pillow reads.

The network parts are under Phase 25's switch; the Köppen file is not.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import config, mapvocab, osmmap
from .mapgen import GenError, GenPlan, _count, _land_corners, _layer, _put

# ---------------------------------------------------------------------------
# the tables, his defaults with the engine's names

#: His five groups of OSM tags, each ``(key, value, label, ground type)``. His
#: names are Mylae's palette ids; ``fertile_*`` are the engine's
#: ``fertility_*``.
LANDUSE_GROUPS: List[Tuple[str, List[Tuple[str, str, str, str]]]] = [
    ("Water", [
        ("water", "lake", "Lake", "swamp"), ("water", "lagoon", "Lagoon", "swamp"),
        ("water", "river", "River (area)", "swamp"), ("water", "oxbow", "Oxbow lake", "swamp"),
        ("water", "pond", "Pond", "swamp"), ("water", "basin", "Basin", "swamp")]),
    ("Wetland", [
        ("wetland", "bog", "Bog", "swamp"), ("wetland", "fen", "Fen", "swamp"),
        ("wetland", "marsh", "Marsh", "swamp"), ("wetland", "swamp", "Swamp", "swamp"),
        ("wetland", "reedbed", "Reedbed", "swamp"), ("wetland", "saltmarsh", "Saltmarsh", "swamp"),
        ("wetland", "wet_meadow", "Wet meadow", "fertility_medium"),
        ("wetland", "tidalflat", "Tidal flat", "beach"),
        ("wetland", "mangrove", "Mangrove", "swamp")]),
    ("Natural", [
        ("natural", "wood", "Wood", "forest_sparse"), ("natural", "scrub", "Scrub", "wilderness"),
        ("natural", "heath", "Heath", "wilderness"),
        ("natural", "grassland", "Grassland", "fertility_medium"),
        ("natural", "wetland", "Wetland", "swamp"), ("natural", "beach", "Beach", "beach"),
        ("natural", "sand", "Sand / dunes", "beach"),
        ("natural", "bare_rock", "Bare rock", "mountains_high"),
        ("natural", "scree", "Scree", "mountains_low"),
        ("natural", "glacier", "Glacier", "mountains_high"), ("natural", "fell", "Fell", "hills"),
        ("natural", "moor", "Moor", "wilderness"), ("natural", "mud", "Mud", "swamp"),
        ("natural", "shingle", "Shingle", "beach"),
        ("natural", "cliff", "Cliff", "mountains_high"),
        ("natural", "valley", "Valley", "fertility_medium"),
        ("natural", "volcano", "Volcano", "mountains_high")]),
    ("Land use", [
        ("landuse", "farmland", "Farmland", "fertility_high"),
        ("landuse", "farmyard", "Farmyard", "fertility_medium"),
        ("landuse", "meadow", "Meadow", "fertility_high"),
        ("landuse", "orchard", "Orchard", "fertility_high"),
        ("landuse", "vineyard", "Vineyard", "fertility_medium"),
        ("landuse", "forest", "Forest (land use)", "forest_sparse"),
        ("landuse", "residential", "Residential", "fertility_low"),
        ("landuse", "industrial", "Industrial", "impassable_land"),
        ("landuse", "quarry", "Quarry", "mountains_low"),
        ("landuse", "cemetery", "Cemetery", "wilderness"),
        ("landuse", "allotments", "Allotments", "fertility_medium"),
        ("landuse", "village_green", "Village green", "fertility_high"),
        ("landuse", "wetland", "Wetland (land use)", "swamp")]),
    ("Leisure", [
        ("leisure", "park", "Park", "fertility_low"),
        ("leisure", "garden", "Garden", "fertility_high")]),
]
LANDUSE = [t for _, tags in LANDUSE_GROUPS for t in tags]

#: ESA WorldCover 2021: class, name, the legend colour its WMS draws, and his
#: default ground type.
WORLDCOVER: List[Tuple[int, str, Tuple[int, int, int], str]] = [
    (10, "Tree cover", (0, 100, 0), "forest_sparse"),
    (20, "Shrubland", (255, 187, 34), "wilderness"),
    (30, "Grassland", (255, 255, 76), "fertility_medium"),
    (40, "Cropland", (240, 150, 255), "fertility_high"),
    (50, "Built-up", (250, 0, 0), "fertility_low"),
    (60, "Bare / sparse vegetation", (180, 180, 180), "mountains_low"),
    (70, "Snow and ice", (240, 240, 240), "mountains_high"),
    (80, "Permanent water", (0, 100, 200), "swamp"),
    (90, "Herbaceous wetland", (0, 150, 160), "swamp"),
    (95, "Mangroves", (0, 207, 117), "swamp"),
    (100, "Moss and lichen", (250, 230, 160), "wilderness"),
]
#: A WMS for it, in EPSG:3857: {bbox} is metres, west,south,east,north.
DEFAULT_LANDCOVER_WMS = [
    "https://services.terrascope.be/wms/v2?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
    "&LAYERS=WORLDCOVER_2021_MAP&STYLES=&FORMAT=image/png&TRANSPARENT=FALSE"
    "&SRS=EPSG:3857&BBOX={bbox}&WIDTH={width}&HEIGHT={height}"]

#: The Köppen-Geiger zones in the published map's order (value 1 is Af, 30 is
#: EF), each with the legend colour and his default climate, by the engine's
#: climate names: his temperate_grassland is the slot vanilla calls
#: ``unused1``, his deciduous and coniferous the ``temperate_*_forest`` ones.
KOPPEN: List[Tuple[str, Tuple[int, int, int], str]] = [
    ("Af", (0, 0, 255), "tropical"), ("Am", (0, 120, 255), "tropical"),
    ("Aw", (70, 170, 250), "tropical"),
    ("BWh", (255, 0, 0), "sandy_desert"), ("BWk", (255, 150, 150), "rocky_desert"),
    ("BSh", (245, 165, 0), "steppe"), ("BSk", (255, 220, 100), "steppe"),
    ("Csa", (255, 255, 0), "mediterranean"), ("Csb", (200, 200, 0), "mediterranean"),
    ("Csc", (150, 150, 0), "mediterranean"),
    ("Cwa", (150, 255, 150), "tropical"), ("Cwb", (100, 200, 100), "highland"),
    ("Cwc", (50, 150, 50), "highland"),
    ("Cfa", (200, 255, 80), "unused1"), ("Cfb", (100, 255, 80), "temperate_deciduous_forest"),
    ("Cfc", (50, 200, 0), "temperate_coniferous_forest"),
    ("Dsa", (255, 0, 255), "mediterranean"), ("Dsb", (200, 0, 200), "mediterranean"),
    ("Dsc", (150, 50, 150), "steppe"), ("Dsd", (150, 100, 150), "alpine"),
    ("Dwa", (170, 175, 255), "unused1"), ("Dwb", (90, 120, 220), "temperate_deciduous_forest"),
    ("Dwc", (75, 80, 180), "temperate_coniferous_forest"), ("Dwd", (50, 0, 135), "alpine"),
    ("Dfa", (0, 255, 255), "unused1"), ("Dfb", (55, 200, 255), "temperate_deciduous_forest"),
    ("Dfc", (0, 125, 125), "temperate_coniferous_forest"), ("Dfd", (0, 70, 95), "alpine"),
    ("ET", (178, 178, 178), "alpine"), ("EF", (102, 102, 102), "alpine"),
]
KOPPEN_INDEX = {code: i + 1 for i, (code, _, _) in enumerate(KOPPEN)}
#: His one colour past a match: further than this from every legend colour is
#: nothing (Euclidean, his 50; checked here on the largest channel, 40).
COLOUR_TOL = 40
#: Past this many pixels the file is refused rather than read into memory
#: (the 1 km map is 933 million).
KOPPEN_MAX_PIXELS = 60_000_000

KINDS = ("landuse", "landcover", "koppen")


def settings() -> dict:
    s = config.load_settings()

    def lst(key, default):
        v = s.get(key)
        if isinstance(v, str):
            v = v.splitlines()
        v = [str(x).strip() for x in (v or []) if str(x).strip()]
        return v or list(default)

    return {"landcover_wms": lst("osm_landcover_wms", DEFAULT_LANDCOVER_WMS),
            "koppen_wms": lst("osm_koppen_wms", []),
            "koppen_file": str(s.get("koppen_file") or "").strip()}


# ---------------------------------------------------------------------------
# geometry: the corner grid against the real world


def _proj(cm) -> Tuple[osmmap.Bbox, osmmap.Projection]:
    box, _ = osmmap.box_for(cm)
    if box is None:
        raise GenError("the map has no real-world box yet; set one on the Real "
                       "world tab first")
    return box, osmmap.Projection(box, cm.terrain.width, cm.terrain.height)


def _merc_size(env: osmmap.Bbox, cols: int, rows: int, cap: int = 2048,
               over: float = 3.0) -> Tuple[int, int]:
    """A picture of the envelope, Mercator-true, ``over`` pixels to a corner
    at most and no side past ``cap``."""
    wide = math.radians(env.east - env.west)
    tall = osmmap.merc(env.north) - osmmap.merc(env.south)
    w = max(64, min(cap, round(cols * over)))
    h = round(w * tall / max(wide, 1e-12))
    if h > cap:
        w, h = max(64, round(w * cap / h)), cap
    return w, max(16, h)


def _to_corners(src: Image.Image, env: osmmap.Bbox, proj: osmmap.Projection,
                cols: int, rows: int) -> Image.Image:
    """``src``, a Mercator-true picture of ``env``, sampled at every corner of
    the ``cols x rows`` grid (corner i at tile (i-1)/2), nearest pixel: a
    class is never blended. One affine transform, the map turned or not."""
    sw, sh = src.size
    mn, ms = osmmap.merc(env.north), osmmap.merc(env.south)

    def at(i, j):
        lon, m = proj.to_lonmerc((i - 1) / 2, (j - 1) / 2)
        return ((lon - env.west) / (env.east - env.west) * sw,
                (mn - m) / (mn - ms) * sh)

    (p0x, p0y), (p1x, p1y), (p2x, p2y) = at(0, 0), at(1, 0), at(0, 1)
    a, b, d, e = p1x - p0x, p2x - p0x, p1y - p0y, p2y - p0y
    return src.transform((cols, rows), Image.AFFINE,
                         (a, b, p0x - 0.5 * a - 0.5 * b, d, e, p0y - 0.5 * d - 0.5 * e),
                         Image.NEAREST, fillcolor=0)


def classify(img: Image.Image, legend: Sequence[Tuple[int, Tuple[int, int, int]]],
             tol: int = COLOUR_TOL) -> Image.Image:
    """An 'L' picture of class numbers from a picture drawn in legend colours:
    each pixel the nearest legend colour, 0 where none is within ``tol``."""
    rgb = img.convert("RGB")
    pal = Image.new("P", (1, 1))
    flat = [c for _, rgb_ in legend for c in rgb_]
    pal.putpalette(flat + flat[:3] * (256 - len(legend)))
    q = rgb.quantize(palette=pal, dither=Image.Dither.NONE)
    back = q.convert("RGB")
    far = ImageChops.difference(rgb, back)
    r, g, b = far.split()
    worst = ImageChops.lighter(ImageChops.lighter(r, g), b)
    ok = worst.point(lambda v: 255 if v <= tol else 0)
    codes = Image.frombytes("L", q.size, q.tobytes()).point(
        [legend[i][0] if i < len(legend) else 0 for i in range(256)])
    return Image.composite(codes, Image.new("L", q.size, 0), ok)


# ---------------------------------------------------------------------------
# the plans


def plan(p: GenPlan, cm, body: dict) -> None:
    {"landuse": _plan_landuse, "landcover": _plan_landcover,
     "koppen": _plan_koppen}[p.kind](p, cm, body)


def _ground(code: str) -> dict:
    g = mapvocab.ground(code)
    if g is None:
        raise GenError(f"{code!r} is not a ground type")
    if code in mapvocab.SEA_GROUND:
        raise GenError(f"{code} is a sea ground type, and these paint land")
    return g


def _plan_landuse(p: GenPlan, cm, body: dict) -> None:
    """The tags asked for, in the order listed, each painted as its ground type
    on the land corners inside its polygons, holes cut back out."""
    chosen = body.get("tags") or {}
    todo = [(k, v, label, str(chosen.get(f"{k}={v}")))
            for k, v, label, _ in LANDUSE if chosen.get(f"{k}={v}") not in (None, "", "-")]
    if not todo:
        raise GenError("tick at least one OpenStreetMap tag and give it a ground type")
    box, proj = _proj(cm)
    img, info, rel = _layer(cm, "ground_types")
    cols, rows = img.size
    land = _land_corners(cm.layer("heights").convert("RGB"))
    out = img.copy()
    counts = []
    for k, v, label, code in todo:
        g = _ground(code)
        polys = osmmap.polygons(box, [f'["{k}"="{v}"]'], f"{k}={v}")
        fill = Image.new("L", (cols, rows), 0)
        holes = Image.new("L", (cols, rows), 0)
        df, dh = ImageDraw.Draw(fill), ImageDraw.Draw(holes)
        for poly in polys:
            for ring in poly.get("outer") or []:
                pts = [(2 * fx + 1, 2 * fy + 1)
                       for fx, fy in (proj.to_tile(la, lo) for la, lo in ring)]
                if len(pts) >= 3:
                    df.polygon(pts, fill=255)
            for ring in poly.get("inner") or []:
                pts = [(2 * fx + 1, 2 * fy + 1)
                       for fx, fy in (proj.to_tile(la, lo) for la, lo in ring)]
                if len(pts) >= 3:
                    dh.polygon(pts, fill=255)
        mask = ImageChops.multiply(ImageChops.subtract(fill, holes), land)
        n = _count(mask)
        out.paste(tuple(g["rgb"]), mask=mask)
        counts.append(f"{label} ({k}={v}, {len(polys)} outline(s)) {n:,} -> {code}")
    if all(c.endswith(f" 0 -> {code}") for c, (_, _, _, code) in zip(counts, todo)):
        raise GenError("none of those tags has an outline over this map's land, so "
                       "nothing would change: " + "; ".join(counts))
    _put(p, cm, "ground_types", out, info, rel)
    p.changes.append(f"{rel}: land corners from OpenStreetMap, in this order - "
                     + "; ".join(counts))
    p.changes.append("the sea is left as it is; land outside every outline keeps its type")


def _plan_landcover(p: GenPlan, cm, body: dict) -> None:
    """ESA WorldCover under every land corner, each class its ground type."""
    mapping = {str(c): g for c, _, _, g in WORLDCOVER}
    mapping.update({str(k): str(v) for k, v in (body.get("mapping") or {}).items()})
    box, proj = _proj(cm)
    img, info, rel = _layer(cm, "ground_types")
    cols, rows = img.size
    env = box.envelope()
    sw, sh = _merc_size(env, cols, rows)
    pic = wms(settings()["landcover_wms"], env, sw, sh, "land cover")
    codes = classify(pic, [(c, rgb) for c, _, rgb, _ in WORLDCOVER])
    # finer than the map: each corner the most common class around it
    if sw >= 2.5 * cols * (env.east - env.west) / max(box.east - box.west, 1e-9):
        codes = codes.filter(ImageFilter.ModeFilter(3))
    at = _to_corners(codes, env, proj, cols, rows)
    land = _land_corners(cm.layer("heights").convert("RGB"))
    out = img.copy()
    done, left = [], []
    hist = at.histogram(mask=land)
    for c, name, _, _ in WORLDCOVER:
        code = mapping.get(str(c), "-")
        if code in ("", "-"):
            if hist[c]:
                left.append(f"{name} {hist[c]:,}")
            continue
        g = _ground(code)
        mask = ImageChops.multiply(at.point(lambda v, c=c: 255 if v == c else 0), land)
        out.paste(tuple(g["rgb"]), mask=mask)
        if hist[c]:
            done.append(f"{name} {hist[c]:,} -> {code}")
    if not done:
        raise GenError("the land cover picture has none of the classes over this "
                       "map's land; check the address in Settings")
    _put(p, cm, "ground_types", out, info, rel)
    p.changes.append(f"{rel}: ESA WorldCover under the land - " + ", ".join(done))
    none = hist[0]
    if none:
        p.warnings.append(f"{none:,} land corner(s) had no class in the picture "
                          "and keep their type")
    if left:
        p.warnings.append("left as they are, as asked: " + ", ".join(left))


def _plan_koppen(p: GenPlan, cm, body: dict) -> None:
    """The Köppen-Geiger zone under every corner, each zone its climate."""
    mapping = {code: clim for code, _, clim in KOPPEN}
    mapping.update({str(k): str(v) for k, v in (body.get("mapping") or {}).items()})
    have = {c["code"]: c for c in mapvocab.climates(p.mod) if c.get("rgb")}
    box, proj = _proj(cm)
    img, info, rel = _layer(cm, "climates")
    cols, rows = img.size
    env = box.envelope()
    sw, sh = _merc_size(env, cols, rows, over=1.5)
    st = settings()
    source = str(body.get("source") or ("file" if st["koppen_file"] else "wms"))
    if source == "file":
        where = str(body.get("file") or st["koppen_file"])
        codes = koppen_from_file(where, env, sw, sh)
        said = f"the Köppen-Geiger map in {Path(where).name}"
    else:
        if not st["koppen_wms"]:
            raise GenError("no Köppen source: give the Köppen-Geiger map's file in "
                           "Settings, Real-world map (no internet needed), or a WMS "
                           "address that draws the zones in the standard colours")
        pic = wms(st["koppen_wms"], env, sw, sh, "Köppen")
        codes = classify(pic, [(i + 1, rgb) for i, (_, rgb, _) in enumerate(KOPPEN)])
        said = "the Köppen WMS"
    at = _to_corners(codes, env, proj, cols, rows)
    hist = at.histogram()
    out = img.copy()
    done, missing, left = [], [], []
    for i, (code, _, _) in enumerate(KOPPEN):
        n = hist[i + 1]
        if not n:
            continue
        clim = mapping.get(code, "-")
        if clim in ("", "-"):
            left.append(f"{code} {n:,}")
            continue
        c = have.get(clim)
        if c is None:
            missing.append(f"{code} -> {clim}")
            continue
        out.paste(tuple(c["rgb"]), mask=at.point(lambda v, k=i + 1: 255 if v == k else 0))
        done.append(f"{code} {n:,} -> {clim}")
    if not done:
        raise GenError("no zone under this map has a climate this mod declares; "
                       "choose a climate for each zone first")
    _put(p, cm, "climates", out, info, rel)
    p.changes.append(f"{rel}: climates from {said} - " + ", ".join(done))
    if hist[0]:
        p.warnings.append(f"{hist[0]:,} corner(s) have no zone (the sea, mostly) and "
                          "keep their climate")
    if missing:
        p.warnings.append("this mod has no climate for " + "; ".join(missing)
                          + ", so those corners keep theirs")
    if left:
        p.warnings.append("left as they are, as asked: " + ", ".join(left))


# ---------------------------------------------------------------------------
# the sources


def wms(templates: List[str], env: osmmap.Bbox, width: int, height: int,
        what: str) -> Image.Image:
    """A WMS picture of the envelope, Mercator-true, kept on disk by its
    address. ``{bbox}`` is EPSG:3857 metres (west, south, east, north),
    ``{bbox4326}`` degrees, ``{width}`` and ``{height}`` pixels."""
    import hashlib
    import io
    import time
    import urllib.error
    osmmap.require_on()
    r = 6378137.0
    bbox = (f"{r * math.radians(env.west):.3f},{r * osmmap.merc(env.south):.3f},"
            f"{r * math.radians(env.east):.3f},{r * osmmap.merc(env.north):.3f}")
    last = None
    for tpl in templates:
        url = (tpl.replace("{bbox}", bbox)
               .replace("{bbox4326}", f"{env.west},{env.south},{env.east},{env.north}")
               .replace("{width}", str(width)).replace("{height}", str(height)))
        path = config.cache_dir("osm_wms") / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".img")
        try:
            if path.is_file() and time.time() - path.stat().st_mtime < osmmap.TILE_DAYS * 86400:
                return Image.open(io.BytesIO(path.read_bytes())).convert("RGB")
        except OSError:
            pass
        try:
            raw = osmmap._fetch(url, timeout=120)
            pic = Image.open(io.BytesIO(raw))
            pic.load()
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            continue
        try:
            path.write_bytes(raw)
        except OSError:
            pass
        return pic.convert("RGB")
    raise GenError(f"no {what} server sent a picture ({last})")


def _georef(img: Image.Image) -> Tuple[float, float, float, float]:
    """``(west, north, degrees per column, degrees per row)`` of a GeoTIFF, from
    its tie point and pixel scale, or the whole world when it carries none."""
    tags = getattr(img, "tag_v2", None) or {}
    scale, tie = tags.get(33550), tags.get(33922)
    if scale and tie and len(scale) >= 2 and len(tie) >= 6:
        return float(tie[3]) - float(tie[0]) * float(scale[0]), \
            float(tie[4]) + float(tie[1]) * float(scale[1]), float(scale[0]), float(scale[1])
    return -180.0, 90.0, 360.0 / img.width, 180.0 / img.height


def koppen_from_file(where: str, env: osmmap.Bbox, width: int, height: int) -> Image.Image:
    """The zone numbers (1-30, 0 for none) of the Köppen-Geiger map on disk,
    as a Mercator-true picture of the envelope: the file's latitude rows
    picked for each Mercator row, its longitude columns stretched."""
    if not where:
        raise GenError("give the Köppen-Geiger map's file first (Settings, Real-world map)")
    f = Path(where)
    if not f.is_file():
        raise GenError(f"there is no file at {where}")
    limit, Image.MAX_IMAGE_PIXELS = Image.MAX_IMAGE_PIXELS, None   # checked just below
    try:
        src = Image.open(f)
    except OSError as e:
        raise GenError(f"{f.name} is not a picture Pillow can read ({e})") from None
    finally:
        Image.MAX_IMAGE_PIXELS = limit
    if src.width * src.height > KOPPEN_MAX_PIXELS:
        raise GenError(f"{f.name} is {src.width}x{src.height}, too big to read whole; "
                       "use the 0.083° (or 0.5°) map from the same download")
    west, north, dx, dy = _georef(src)
    try:
        if src.mode == "P":
            codes = Image.frombytes("L", src.size, src.tobytes())
        elif src.mode in ("L", "I;8"):
            codes = src.convert("L") if src.mode != "L" else src
        elif src.mode.startswith("I") or src.mode == "F":
            codes = src.point(lambda v: v).convert("L")
        else:
            codes = classify(src, [(i + 1, rgb) for i, (_, rgb, _) in enumerate(KOPPEN)])
    except OSError as e:
        raise GenError(f"{f.name} could not be decoded ({e})") from None
    codes = codes.point([v if v <= len(KOPPEN) else 0 for v in range(256)])
    # the columns under the envelope, stretched to the picture's width
    c0 = (env.west - west) / dx
    c1 = (env.east - west) / dx
    cols = codes.transform((width, codes.height), Image.AFFINE,
                           ((c1 - c0) / width, 0, c0, 0, 1, 0), Image.NEAREST, fillcolor=0)
    out = Image.new("L", (width, height), 0)
    mn, ms = osmmap.merc(env.north), osmmap.merc(env.south)
    for r in range(height):
        m = mn - (r + 0.5) / height * (mn - ms)
        lat = math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)
        row = int((north - lat) / dy)
        if 0 <= row < cols.height:
            out.paste(cols.crop((0, row, width, row + 1)), (0, r))
    return out


def view(mod) -> dict:
    """What the panel offers: the tags, the classes, the zones, the sources."""
    st = settings()
    return {"landuse": [{"group": g, "tags": [{"key": k, "value": v, "label": lab,
                                                "ground": gr} for k, v, lab, gr in tags]}
                        for g, tags in LANDUSE_GROUPS],
            "worldcover": [{"class": c, "name": n, "rgb": list(rgb), "ground": g}
                           for c, n, rgb, g in WORLDCOVER],
            "koppen": [{"code": c, "rgb": list(rgb), "climate": cl} for c, rgb, cl in KOPPEN],
            "koppen_file": st["koppen_file"],
            "koppen_file_ok": bool(st["koppen_file"]) and Path(st["koppen_file"]).is_file(),
            "koppen_wms": bool(st["koppen_wms"]),
            "landcover_wms": st["landcover_wms"]}
