"""The real world behind a campaign map: OpenStreetMap, opt-in (Phase 25).

Three things from Mylae's editor (``OsmBackground``, ``OsmRegionSearch``,
``CoastlineTracer``), rebuilt so Python owns every byte that is written:

* **a backdrop** of OSM map tiles drawn over the map, aligned by a
  north/south/west/east box per campaign map;
* **the real coastline**, fetched from Overpass, drawn over the map, and on
  request made into sea on the water side, as one undoable stroke of the paint
  tool;
* **a place search** (Nominatim), whose results can be gone to, started as a
  new region, or have their boundary painted onto a region, again as a stroke.

**It is the first thing in the toolkit that touches the network, so it is off
until the user turns it on** (``osm_enabled`` in the settings), and every
server it talks to is listed there and can be changed. Nothing is sent but
what the question needs: the map's box, a tile's number, the words searched.
Every request carries the toolkit's name, as the OSM usage policies ask, tiles
are kept on disk for 30 days rather than fetched again, and Nominatim is asked
no more than once a second.

**The box.** The map is taken to be Web Mercator between the box's edges, the
same assumption Mylae's editor makes, and a tile's centre is where the box
puts it: tile 0 on the west edge, tile ``W-1`` on the east edge, and the same
down the latitudes in Mercator. That is his ``latLngToPixel`` exactly, so a
``bbox_coords.txt`` written by his New Map Editor lines up here as it does
there. The box is kept in the toolkit's own config, per mod and per campaign
map, and a ``bbox_coords.txt`` beside the map is read when none is kept.

**The coastline keeps its direction.** OSM draws every ``natural=coastline``
way with the land on the left and the water on the right. His tracer joins ways
end to end in either direction, which throws that away, and paints the line
itself as sea. Here each way stays as drawn, the tile to the right of every
segment seeds a four-connected fill bounded by the line, and the fill is what
becomes sea. The tile to the left seeds a check: if any of those land tiles is
reached by the fill, the coastline has a gap somewhere, the fill would spill
onto land, and the plan refuses rather than drowning half a continent.

**What sea is, from the engine**: a height pixel is sea when its red and green
are 0 and its blue is above 0, and the blue sets the depth (255 is the
shallowest, 30 below sea level). His "line only (0,0,200)" is therefore also
sea, a little deeper. Here the colours are the water brush's, measured off the
mod's own map (:func:`unittransfer.campaint.water_palette`), written to the
regions, heights and ground types together as the water brush does, and only
onto tiles that are land now: a tile that is already sea keeps its depth.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw

from . import __version__, config

#: The switch. Off until the user turns it on.
ENABLED_KEY = "osm_enabled"

#: Where the tiles come from, first that answers wins. The standard OSM tile
#: server; its usage policy allows an editor's occasional browsing with a
#: name on the request and a cache, which is what this does.
DEFAULT_TILES = ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"]
#: Overpass mirrors, tried in order. The two Mylae's editor uses.
DEFAULT_OVERPASS = ["https://overpass-api.de/api/interpreter",
                    "https://overpass.kumi.systems/api/interpreter"]
DEFAULT_NOMINATIM = "https://nominatim.openstreetmap.org"

#: 87b. The backdrop's styles, Mylae's reference layers and his historical
#: map: the settings key holding each style's servers, the servers, its name,
#: the deepest zoom it has, and the credit a picture of it has to carry.
#: ``relief`` has no server of its own: it is drawn here from the elevation
#: tiles the heights generator reads (27), on one scale for every tile, where
#: his stretched each tile to its own range and left a seam between them.
#: ``ohm`` takes a year, into ``{date}``.
STYLES = {
    "osm": ("osm_tiles", DEFAULT_TILES, "OpenStreetMap", 19,
            "© OpenStreetMap contributors"),
    "topo": ("osm_tiles_topo", ["https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
                                "https://b.tile.opentopomap.org/{z}/{x}/{y}.png",
                                "https://c.tile.opentopomap.org/{z}/{x}/{y}.png"],
             "OpenTopoMap", 17,
             "© OpenStreetMap contributors, SRTM · style © OpenTopoMap (CC-BY-SA)"),
    "hot": ("osm_tiles_hot", ["https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
                              "https://b.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"],
            "OSM Humanitarian", 19,
            "© OpenStreetMap contributors · tiles Humanitarian OSM Team, OSM France"),
    "ohm": ("osm_tiles_ohm",
            ["https://tile.openhistoricalmap.org/historicalmaps/{z}/{x}/{y}.png?date={date}"],
            "OpenHistoricalMap", 19, "© OpenHistoricalMap contributors"),
    "relief": (None, None, "Relief (from the elevation tiles)", 15,
               "elevation: Terrarium tiles, AWS Open Data (Mapzen)"),
}
#: His year slider's reach, and his twelve era buttons.
OHM_YEARS = (500, 1600)
OHM_ERAS = (500, 700, 800, 900, 1000, 1066, 1095, 1200, 1250, 1350, 1400, 1500)
OHM_DEFAULT = 1200

USER_AGENT = f"Medieval2-GUI-Toolkit/{__version__} (local campaign map editor)"

#: The file Mylae's New Map Editor writes, and the name a box is exported as.
BBOX_FILE = "bbox_coords.txt"
#: Web Mercator's own limit; past it the projection runs to infinity.
MAX_LAT = 85.05112878

#: How long a tile is kept on disk before it is fetched again. The tile policy
#: asks for at least seven days.
TILE_DAYS = 30
#: The most tiles one backdrop may ask for in a minute, from this process.
TILE_BUDGET = 600

#: The size of one Overpass request, in degrees a side. A chunk that fails is
#: split in four and asked again, down to CHUNK_MIN, so a dense coast (Norway,
#: the Aegean) costs more requests and a bare one costs one.
CHUNK_DEG = 6.0
CHUNK_MIN = 0.75

#: Nominatim's usage policy: one request a second, at most.
NOMINATIM_GAP = 1.05


class OsmError(ValueError):
    """Something about the request, the box or the answer, said plainly."""


class OsmOff(OsmError):
    """The switch is off. Nothing was sent."""


# ---------------------------------------------------------------------------
# the switch and the servers


def settings() -> dict:
    s = config.load_settings()

    def lst(key, default):
        v = s.get(key)
        if isinstance(v, str):
            v = [x.strip() for x in v.splitlines()]
        v = [str(x).strip() for x in (v or []) if str(x).strip()]
        return v or list(default)

    return {"enabled": bool(s.get(ENABLED_KEY, False)),
            "tiles": lst("osm_tiles", DEFAULT_TILES),
            "styles": {k: {"name": v[2], "max_zoom": v[3], "credit": v[4],
                           "servers": lst(v[0], v[1]) if v[0] else []}
                       for k, v in STYLES.items()},
            "ohm_years": list(OHM_YEARS), "ohm_eras": list(OHM_ERAS),
            "ohm_default": OHM_DEFAULT,
            "overpass": lst("osm_overpass", DEFAULT_OVERPASS),
            "nominatim": (str(s.get("osm_nominatim") or "").strip().rstrip("/")
                          or DEFAULT_NOMINATIM),
            "user_agent": USER_AGENT}


def require_on() -> dict:
    s = settings()
    if not s["enabled"]:
        raise OsmOff("OpenStreetMap is off. Turn it on under Settings, Real-world "
                     "map, first. Nothing was sent.")
    return s


# ---------------------------------------------------------------------------
# the box


#: The sphere Web Mercator is drawn on, in km.
EARTH_KM = 6378.137
#: Below this many degrees a box is not rotated at all (Mylae's EPS).
ROT_EPS = 0.01


@dataclass
class Bbox:
    """The map's rectangle in the real world, before it is turned.

    ``rotation`` is in degrees, positive clockwise on screen, and turns the
    rectangle about its centre (the plain midpoint of the four edges) in
    degree-scaled Mercator, where a turned rectangle stays a rectangle on the
    slippy map. That is Mylae's ``rotatedBbox`` exactly, so a box turned in his
    New Map Editor is the same box here.
    """
    north: float
    south: float
    west: float
    east: float
    rotation: float = 0.0

    @property
    def rotated(self) -> bool:
        return abs(self.rotation) >= ROT_EPS

    def payload(self) -> dict:
        out = {"north": self.north, "south": self.south,
               "west": self.west, "east": self.east}
        if self.rotated:
            out["rotation"] = self.rotation
        return out

    def centre(self) -> Tuple[float, float]:
        return (self.north + self.south) / 2, (self.east + self.west) / 2

    def turn(self, lat: float, lon: float, angle: Optional[float] = None
             ) -> Tuple[float, float]:
        """A point turned about the centre by ``angle`` (the box's own by
        default), in degree-scaled Mercator. Returns ``(lat, lon)``."""
        a = math.radians(self.rotation if angle is None else angle)
        if abs(a) < 1e-12:
            return lat, lon
        clat, clon = self.centre()
        cy = merc_deg(clat)
        dx, dy = lon - clon, merc_deg(lat) - cy
        c, s = math.cos(a), math.sin(a)
        return inv_merc_deg(cy + dy * c - dx * s), clon + dx * c + dy * s

    def corners(self) -> List[Tuple[float, float]]:
        """The four corners as they stand, north-west first, clockwise."""
        return [self.turn(la, lo) for la, lo in ((self.north, self.west),
                                                 (self.north, self.east),
                                                 (self.south, self.east),
                                                 (self.south, self.west))]

    def envelope(self) -> "Bbox":
        """The unturned box around the turned one: what a query has to cover."""
        if not self.rotated:
            return Bbox(self.north, self.south, self.west, self.east)
        pts = self.corners()
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        return Bbox(min(MAX_LAT, max(lats)), max(-MAX_LAT, min(lats)),
                    max(-180.0, min(lons)), min(180.0, max(lons)))

    def aspect(self) -> float:
        """Degrees of longitude per degree of Mercator: Mylae's ``bboxAspect``."""
        return (self.east - self.west) / max(merc_deg(self.north) - merc_deg(self.south),
                                             1e-12)

    def problems(self) -> List[str]:
        out = []
        if not -180 <= self.rotation <= 180:
            out.append(f"rotation {self.rotation} is not between -180 and 180 degrees")
        for k in ("north", "south"):
            v = getattr(self, k)
            if not -MAX_LAT <= v <= MAX_LAT:
                out.append(f"{k} {v} is past {MAX_LAT:.2f}, where the map "
                           "projection stops")
        for k in ("west", "east"):
            v = getattr(self, k)
            if not -180 <= v <= 180:
                out.append(f"{k} {v} is not a longitude")
        if self.north <= self.south:
            out.append("north has to be above south")
        if self.east <= self.west:
            out.append("east has to be east of west (a box across the date line "
                       "is not supported)")
        if not out and self.rotated:
            env = self.envelope()
            if any(abs(la) > MAX_LAT - 1e-6 for la, _ in self.corners()):
                out.append("turned this far, a corner goes past the pole")
            elif env.west <= -180 or env.east >= 180:
                out.append("turned this far, a corner crosses the date line")
        return out


def parse_bbox(body) -> Bbox:
    """A box from ``{north, south, west, east}`` or from a ``bbox_coords.txt``.

    The file is ``key=value`` lines with ``#`` comments, which is what Mylae's
    New Map Editor writes; the map and heightmap sizes it also carries are not
    needed, because the map says its own size.
    """
    if isinstance(body, str):
        vals: Dict[str, float] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            try:
                vals[k.strip().lower()] = float(v.strip())
            except ValueError:
                continue
        body = vals
    try:
        b = Bbox(*(float(body[k]) for k in ("north", "south", "west", "east")))
    except (KeyError, TypeError, ValueError):
        raise OsmError("a box needs north, south, west and east, each a number") from None
    try:
        b.rotation = float(body.get("rotation") or 0.0)
    except (TypeError, ValueError):
        raise OsmError("the rotation has to be a number of degrees") from None
    if not math.isfinite(b.rotation):
        raise OsmError("the rotation has to be a number of degrees")
    bad = b.problems()
    if bad:
        raise OsmError("; ".join(bad))
    return b


def bbox_text(b: Bbox, width: int, height: int) -> str:
    """The box as a ``bbox_coords.txt``, in the shape Mylae's editor reads.

    A turned box adds ``rotation=``, which his loader passes over (it reads
    only the four edges), so the file still opens there, unturned."""
    return "\n".join([
        "# the campaign map's real-world box, written by the Medieval 2 GUI Toolkit",
        f"# {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"north={b.north:.6f}", f"south={b.south:.6f}",
        f"west={b.west:.6f}", f"east={b.east:.6f}",
        *([f"rotation={b.rotation:.4f}"] if b.rotated else []),
        "",
        f"map_width={width}", f"map_height={height}",
        f"heightmap_width={2 * width + 1}", f"heightmap_height={2 * height + 1}",
    ]) + "\n"


def _store() -> Path:
    return config.CONFIG_DIR / "osm_boxes.json"


def map_key(cm) -> str:
    """Which campaign map a box belongs to: its folder, under ``data/``."""
    folder = cm.home if getattr(cm, "home", None) is not None else cm.base
    try:
        return Path(folder).relative_to(cm.mod.data).as_posix()
    except ValueError:
        return Path(folder).as_posix()


def box_for(cm) -> Tuple[Optional[Bbox], str]:
    """``(box, where it came from)``: ``kept``, ``file`` or ``""``."""
    kept = config._read_json(_store(), {}).get(cm.mod.name, {}).get(map_key(cm))
    if kept:
        try:
            return parse_bbox(kept), "kept"
        except OsmError:
            pass
    for folder in [cm.home, cm.base]:
        if folder is None:
            continue
        f = Path(folder) / BBOX_FILE
        if f.is_file():
            try:
                return parse_bbox(f.read_text(encoding="utf-8", errors="replace")), "file"
            except OsmError:
                continue
    return None, ""


def keep_box(cm, b: Optional[Bbox]) -> None:
    data = config._read_json(_store(), {})
    per = data.setdefault(cm.mod.name, {})
    if b is None:
        per.pop(map_key(cm), None)
    else:
        per[map_key(cm)] = b.payload()
    config._write_json(_store(), data)


# ---------------------------------------------------------------------------
# the projection: tile space, with a tile's centre where the box puts it


def merc(lat: float) -> float:
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def merc_deg(lat: float) -> float:
    """Mercator scaled to degrees, the space a box is turned in."""
    return math.degrees(merc(lat))


def inv_merc_deg(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)


class Projection:
    """Tile space against the real world. A tile's centre is where the box
    puts it before the box is turned; a turned box turns the whole map with
    it, about the box's centre."""

    def __init__(self, b: Bbox, width: int, height: int):
        self.b, self.w, self.h = b, width, height
        self.mn, self.ms = merc(b.north), merc(b.south)

    def to_tile(self, lat: float, lon: float) -> Tuple[float, float]:
        b = self.b
        if b.rotated:
            lat, lon = b.turn(lat, lon, -b.rotation)
        return ((lon - b.west) / (b.east - b.west) * (self.w - 1),
                (self.mn - merc(lat)) / (self.mn - self.ms) * (self.h - 1))

    def to_geo(self, fx: float, fy: float) -> Tuple[float, float]:
        b = self.b
        lon = b.west + fx / (self.w - 1) * (b.east - b.west)
        m = self.mn - fy / (self.h - 1) * (self.mn - self.ms)
        lat = math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)
        return b.turn(lat, lon) if b.rotated else (lat, lon)

    def to_lonmerc(self, fx: float, fy: float) -> Tuple[float, float]:
        """``(longitude, Mercator in radians)`` of a tile position: both are
        affine in ``(fx, fy)``, turned or not, which is what lets one affine
        transform resample a slippy picture onto the map."""
        lat, lon = self.to_geo(fx, fy)
        return lon, merc(lat)

    def km_per_tile(self) -> Tuple[float, float]:
        """How far one tile reaches, east-west and north-south, at the box's
        middle latitude."""
        b = self.b
        clat = math.radians((b.north + b.south) / 2)
        r = EARTH_KM * math.cos(clat)                      # km per radian there
        ew = math.radians(b.east - b.west) / max(self.w - 1, 1) * r
        m = (self.mn - self.ms) / max(self.h - 1, 1)       # radians of Mercator
        return ew, m * r


# ---------------------------------------------------------------------------
# the network


def _fetch(url: str, data: Optional[bytes] = None, timeout: float = 60) -> bytes:
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": USER_AGENT, "Accept-Language": "en",
        **({"Content-Type": "application/x-www-form-urlencoded"} if data else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


_TILE_LOCK = threading.Lock()
_TILE_TIMES: deque = deque()


def _year(style: str, year) -> Optional[int]:
    if style != "ohm":
        return None
    try:
        y = int(year) if year not in (None, "") else OHM_DEFAULT
    except (TypeError, ValueError):
        raise OsmError("the year has to be a whole number") from None
    if not 1 <= y <= 2100:
        raise OsmError(f"{y} is not a year the historical map has")
    return y


def _tile_path(style: str, year: Optional[int], z: int, x: int, y: int) -> Path:
    # the standard style keeps Phase 25's folder, so its cache stays good
    base = config.cache_dir("osm_tiles" if style == "osm" else f"osm_tiles_{style}")
    if year is not None:
        base = base / str(year)
    return base / str(z) / str(x) / f"{y}.png"


def _urls(tpl: str, z: int, x: int, y: int, year: Optional[int]) -> List[str]:
    u = (tpl.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
         .replace("{date}", f"{year or OHM_DEFAULT:04d}-01-01"))
    return [u.replace("{s}", c) for c in "abc"] if "{s}" in u else [u]


def tile(z: int, x: int, y: int, style: str = "osm", year=None) -> bytes:
    """One map tile of a style, off the disk if it was fetched in the last 30
    days. The relief is drawn here from the elevation tile under it."""
    if style not in STYLES:
        raise OsmError(f"{style} is not a backdrop style")
    if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        raise OsmError(f"{z}/{x}/{y} is not a map tile")
    yr = _year(style, year)
    path = _tile_path(style, yr, z, x, y)
    try:
        if path.is_file() and time.time() - path.stat().st_mtime < TILE_DAYS * 86400:
            return path.read_bytes()
    except OSError:
        pass
    s = require_on()
    if style == "relief":
        raw = relief_png(z, x, y)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        except OSError:
            pass
        return raw
    with _TILE_LOCK:
        now = time.time()
        while _TILE_TIMES and now - _TILE_TIMES[0] > 60:
            _TILE_TIMES.popleft()
        if len(_TILE_TIMES) >= TILE_BUDGET:
            raise OsmError("the backdrop has asked for a lot of tiles in the last "
                           "minute - it will carry on shortly")
        _TILE_TIMES.append(now)
    last = None
    for tpl in s["styles"][style]["servers"]:
        for url in _urls(tpl, z, x, y, yr):
            try:
                raw = _fetch(url, timeout=20)
            except (urllib.error.URLError, OSError, ValueError) as e:
                last = e
                continue
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            except OSError:
                pass
            return raw
    raise OsmError(f"no {STYLES[style][2]} server answered ({last})")


#: The relief's scale: land from 0 to this many metres runs dark to light, the
#: sea from 0 to this depth light to dark blue. One scale for every tile.
RELIEF_TOP = 4500.0
RELIEF_DEEP = 5000.0


def relief_png(z: int, x: int, y: int) -> bytes:
    """A relief tile: the elevation under it in grey on land and blue at sea,
    shaded from the north-west so the slopes read."""
    from . import mapgen
    e = mapgen.elevation_tile(z, x, y)
    # the neighbour to the north-west of every pixel, the edge repeated
    pad = Image.new("F", (257, 257))
    pad.paste(e, (1, 1))
    pad.paste(e.crop((0, 0, 256, 1)), (1, 0))
    pad.paste(e.crop((0, 0, 1, 256)), (0, 1))
    pad.putpixel((0, 0), e.getpixel((0, 0)))
    nw = pad.crop((0, 0, 256, 256))
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / 2 ** z))))
    m_px = 2 * math.pi * EARTH_KM * 1000 * math.cos(math.radians(lat)) / (256 * 2 ** z)
    slope = mapgen._math("(n - e) / p", n=nw, e=e,
                         p=Image.new("F", e.size, max(m_px, 1e-6)))
    shade = slope.point(lambda v: v * 350.0 + 205.0).convert("L")
    grey = e.point(lambda v: v * 255.0 / RELIEF_TOP).convert("L").point(
        [round(70 + 185 * math.sqrt(i / 255)) for i in range(256)])
    grey = ImageChops.multiply(grey, shade)
    deep = e.point(lambda v: -v * 255.0 / RELIEF_DEEP).convert("L")
    blue = deep.point([round(235 - 150 * math.sqrt(i / 255)) for i in range(256)])
    sea_rg = deep.point([round(190 - 170 * math.sqrt(i / 255)) for i in range(256)])
    land = mapgen._math("convert((e > 0) * 255, 'L')", e=e)
    rgb = Image.merge("RGB", (sea_rg, sea_rg, blue))
    rgb.paste(Image.merge("RGB", (grey, grey, grey)), mask=land)
    buf = io.BytesIO()
    rgb.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 87b: a picture of the box, to keep beside the map


#: The most tiles one picture may stitch.
PICTURE_BUDGET = 400


def picture(b: Bbox, width: int, height: int, style: str = "osm", year=None,
            px: int = 2048) -> Image.Image:
    """The box's real world as one picture in the map's own frame: ``px``
    wide, as tall as the map's shape makes it, a turned box turned with it,
    and the style's credit in the corner, as its licence asks.

    The slippy tiles under the envelope are stitched at the first zoom that
    covers the picture one and a half times over (Mylae's rule), then one
    affine transform puts them in the map's frame, as for the heights."""
    if style not in STYLES:
        raise OsmError(f"{style} is not a backdrop style")
    px = max(64, min(8192, int(px)))
    tall = max(1, round(px * height / width))
    proj = Projection(b, width, height)
    env = b.envelope()

    def lon2x(lon, z):
        return (lon + 180) / 360 * 2 ** z * 256

    def lat2y(lat, z):
        return (1 - merc(lat) / math.pi) / 2 * 2 ** z * 256

    zmax = STYLES[style][3]
    z = zmax
    for zz in range(1, zmax + 1):
        if (lon2x(env.east, zz) - lon2x(env.west, zz) >= 1.5 * px
                and lat2y(env.south, zz) - lat2y(env.north, zz) >= 1.5 * tall):
            z = zz
            break

    def span(zz):
        return (int(lon2x(env.west, zz) // 256), int(lon2x(env.east, zz) // 256),
                int(lat2y(env.north, zz) // 256), int(lat2y(env.south, zz) // 256))

    x0, x1, y0, y1 = span(z)
    while (x1 - x0 + 1) * (y1 - y0 + 1) > PICTURE_BUDGET and z > 1:
        z -= 1
        x0, x1, y0, y1 = span(z)
    n = 2 ** z
    big = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256), (170, 201, 214))
    for ty in range(max(0, y0), min(n - 1, y1) + 1):
        for tx in range(x0, x1 + 1):
            raw = tile(z, tx % n, ty, style, year)
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            if im.size != (256, 256):
                im = im.resize((256, 256), Image.BILINEAR)
            big.paste(im, ((tx - x0) * 256, (ty - y0) * 256))
    size = n * 256

    def at(u, v):
        # output pixel centre (u + .5, v + .5) -> the map's tile space -> the stitch
        fx = (u + 0.5) * width / px - 0.5
        fy = (v + 0.5) * height / tall - 0.5
        lon, m = proj.to_lonmerc(fx, fy)
        return (lon + 180) / 360 * size - x0 * 256, (1 - m / math.pi) / 2 * size - y0 * 256

    (p0x, p0y), (p1x, p1y), (p2x, p2y) = at(0, 0), at(1, 0), at(0, 1)
    a, bb, d, e = p1x - p0x, p2x - p0x, p1y - p0y, p2y - p0y
    # at(u, v) is where output pixel (u, v)'s centre lands, in the stitch's
    # continuous coordinates (a pixel's centre at k + .5); Pillow samples the
    # continuous point a * (u + .5) + b * (v + .5) + c
    c = p0x - 0.5 * a - 0.5 * bb
    f = p0y - 0.5 * d - 0.5 * e
    out = big.transform((px, tall), Image.AFFINE, (a, bb, c, d, e, f), Image.BILINEAR)
    out.info["zoom"] = z
    draw = ImageDraw.Draw(out)
    credit = STYLES[style][4] + (f" · {_year(style, year)}" if style == "ohm" else "")
    tw = draw.textlength(credit)
    draw.rectangle([px - tw - 10, tall - 16, px, tall], fill=(255, 255, 255))
    draw.text((px - tw - 5, tall - 14), credit, fill=(40, 40, 40))
    return out


def picture_svg(img: Image.Image, b: Bbox, width: int, height: int, style: str) -> str:
    """The picture as an SVG, Mylae's shape with one correction: his viewBox
    is in degrees, which misplaces every latitude on a Mercator picture, so
    this one is in the map's tiles (0 to W, 0 to H), the box and the turn
    written beside it."""
    import base64
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{img.width}" height="{img.height}">\n'
            f'  <title>{STYLES[style][2]}: N {b.north:.6f} S {b.south:.6f} '
            f'W {b.west:.6f} E {b.east:.6f}'
            f'{f" turned {b.rotation:.2f}" if b.rotated else ""}</title>\n'
            f'  <!-- one unit is one tile of the {width}x{height} campaign map; '
            f'{STYLES[style][4]} -->\n'
            f'  <image x="0" y="0" width="{width}" height="{height}" '
            f'preserveAspectRatio="none" href="data:image/png;base64,{data}"/>\n'
            f'</svg>\n')


def overpass(query: str) -> dict:
    s = require_on()
    last = None
    for url in s["overpass"]:
        try:
            raw = _fetch(url, data=("data=" + urllib.parse.quote(query)).encode(),
                         timeout=200)
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
    raise OsmError(f"no Overpass server answered ({last})")


_NOM_LOCK = threading.Lock()
_NOM_LAST = [0.0]


def nominatim(path: str, params: dict):
    s = require_on()
    url = f"{s['nominatim']}/{path}?{urllib.parse.urlencode(params)}"
    with _NOM_LOCK:
        wait = NOMINATIM_GAP - (time.time() - _NOM_LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            raw = _fetch(url, timeout=30)
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise OsmError(f"Nominatim did not answer ({e})") from None
        finally:
            _NOM_LAST[0] = time.time()
    return json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# the coastline


def _chunks(b: Bbox, size: float) -> List[Bbox]:
    """The box cut into squares of ``size`` degrees for Overpass. A turned box
    is covered by its envelope."""
    b = b.envelope()
    out = []
    lat = b.south
    while lat < b.north - 1e-9:
        top = min(b.north, lat + size)
        lon = b.west
        while lon < b.east - 1e-9:
            right = min(b.east, lon + size)
            out.append(Bbox(top, lat, lon, right))
            lon = right
        lat = top
    return out


def _coast_chunk(c: Bbox, ways: Dict[int, list],
                 progress: Callable[[str], None]) -> None:
    q = (f"[out:json][timeout:180][maxsize:536870912];"
         f"way[\"natural\"=\"coastline\"]({c.south},{c.west},{c.north},{c.east});"
         f"out geom;")
    try:
        data = overpass(q)
    except OsmError:
        if (c.north - c.south) / 2 < CHUNK_MIN:
            raise
        progress("splitting a dense stretch of coast")
        midlat, midlon = (c.north + c.south) / 2, (c.east + c.west) / 2
        for part in (Bbox(c.north, midlat, c.west, midlon),
                     Bbox(c.north, midlat, midlon, c.east),
                     Bbox(midlat, c.south, c.west, midlon),
                     Bbox(midlat, c.south, midlon, c.east)):
            _coast_chunk(part, ways, progress)
        return
    for e in data.get("elements", []):
        geo = e.get("geometry") or []
        if e.get("type") == "way" and len(geo) > 1 and e.get("id") not in ways:
            ways[e["id"]] = [(round(p["lat"], 6), round(p["lon"], 6))
                             for p in geo if p]


def coastline(b: Bbox, progress: Optional[Callable[[int, str], None]] = None
              ) -> List[List[Tuple[float, float]]]:
    """Every ``natural=coastline`` way touching the box, as drawn in OSM.

    Asked a chunk at a time and kept on disk by the box, so a second look at
    the same map sends nothing. Each way keeps its own direction: that is what
    says which side is water.
    """
    key = hashlib.sha1(json.dumps(b.payload(), sort_keys=True).encode()).hexdigest()[:16]
    path = config.cache_dir("osm_coast") / f"{key}.json.gz"
    try:
        if path.is_file():
            return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError):
        pass
    require_on()
    parts = _chunks(b, CHUNK_DEG)
    ways: Dict[int, list] = {}
    for n, c in enumerate(parts):
        if progress:
            progress(int(100 * n / len(parts)),
                     f"coastline: {n + 1} of {len(parts)} stretches, {len(ways)} ways")
        _coast_chunk(c, ways, (lambda msg: progress and progress(
            int(100 * n / len(parts)), msg)))
    out = [w for w in ways.values()]
    try:
        path.write_bytes(gzip.compress(json.dumps(out).encode("utf-8")))
    except OSError:
        pass
    return out


def _collapse(proj: Projection, way) -> List[Tuple[float, float]]:
    """A way in tile space, points closer than a quarter tile dropped."""
    out: List[Tuple[float, float]] = []
    for lat, lon in way:
        p = proj.to_tile(lat, lon)
        if out and abs(p[0] - out[-1][0]) < 0.25 and abs(p[1] - out[-1][1]) < 0.25:
            continue
        out.append(p)
    if len(out) == 1 and len(way) > 1:
        out.append(proj.to_tile(*way[-1]))
    return out


def _line(x0: int, y0: int, x1: int, y1: int):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
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


@dataclass
class Coast:
    """The coastline over one map, and what it says about the map's sea."""
    ways: List[List[Tuple[float, float]]]
    line: bytearray                  # 1 on a coastline tile
    water: bytearray                 # 1 on the water side, the line excluded
    to_sea: List[Tuple[int, int]]    # land now, water side of the coastline
    land_side_sea: int               # sea now, land side
    leak: int                        # land-side seeds the water fill reached
    seeds: int                       # land-side seeds in all
    width: int
    height: int

    @property
    def leaks(self) -> bool:
        # a handful is rounding where two coasts are a tile apart; more is a gap
        return self.leak > max(3, self.seeds // 200)

    def payload(self) -> dict:
        """The counts, and the two tile lists the map draws: the line as the
        fill sees it, and every tile the stroke would make sea. Flat
        ``[x, y, x, y, ...]``, which is what the page writes into its overlay."""
        W = self.width
        return {"way_count": len(self.ways),
                "line": sum(self.line), "water": sum(self.water),
                "to_sea": len(self.to_sea), "land_side_sea": self.land_side_sea,
                "leak": self.leak, "seeds": self.seeds, "leaks": self.leaks,
                "line_xy": [v for i, on in enumerate(self.line) if on
                            for v in (i % W, i // W)],
                "to_sea_xy": [v for xy in self.to_sea for v in xy]}


def analyse(ways, proj: Projection, sea: bytes) -> Coast:
    """Where the coastline runs over this map, and which side is water.

    ``sea`` is the map's sea mask, one byte a tile. Only tiles that are land
    now are offered to become sea; the count of the other mismatch, sea on the
    land side, is reported and left, because a new land tile needs a height, a
    ground type and a province this cannot know.
    """
    W, H = proj.w, proj.h
    tiled = [w for w in (_collapse(proj, way) for way in ways) if len(w) > 1]
    line = bytearray(W * H)
    water_seeds: List[int] = []
    land_seeds: List[int] = []

    def inside(x, y):
        return 0 <= x < W and 0 <= y < H

    for w in tiled:
        for (ax, ay), (bx, by) in zip(w, w[1:]):
            for x, y in _line(round(ax), round(ay), round(bx), round(by)):
                if inside(x, y):
                    line[y * W + x] = 1
    for w in tiled:
        for (ax, ay), (bx, by) in zip(w, w[1:]):
            dx, dy = bx - ax, by - ay
            n = math.hypot(dx, dy)
            if n < 1e-9:
                continue
            # land on the left, water on the right; y runs down the map, so the
            # right-hand normal of (dx, dy) is (-dy, dx)
            nx, ny = -dy / n, dx / n
            steps = max(1, int(n))
            for s in range(steps):
                t = (s + 0.5) / steps
                mx, my = ax + dx * t, ay + dy * t
                for side, bucket in ((1.0, water_seeds), (-1.0, land_seeds)):
                    x, y = round(mx + side * nx), round(my + side * ny)
                    if inside(x, y) and not line[y * W + x]:
                        bucket.append(y * W + x)

    water = bytearray(W * H)
    todo = deque(i for i in set(water_seeds))
    for i in todo:
        water[i] = 1
    while todo:
        i = todo.popleft()
        x, y = i % W, i // W
        for j, ok in ((i - 1, x > 0), (i + 1, x < W - 1), (i - W, y > 0), (i + W, y < H - 1)):
            if ok and not water[j] and not line[j]:
                water[j] = 1
                todo.append(j)
    land = set(land_seeds)
    leak = sum(1 for i in land if water[i])
    to_sea = [(i % W, i // W) for i in range(W * H) if water[i] and not sea[i]]
    # the land side is everything off the line and off the water side
    land_side_sea = sum(1 for i in range(W * H)
                        if sea[i] and not water[i] and not line[i]) if water_seeds else 0
    return Coast(ways=tiled, line=line, water=water, to_sea=to_sea,
                 land_side_sea=land_side_sea, leak=leak, seeds=len(land),
                 width=W, height=H)


# ---------------------------------------------------------------------------
# 87c: lakes, lagoons and seas, from OSM's water polygons

#: Mylae's three kinds of water, and the Overpass filters for each. His sea is
#: tagged three ways; a lagoon and a lake one each.
WATER_KINDS = {
    "sea": ['["natural"="water"]["water"="sea"]', '["place"="sea"]', '["place"="ocean"]'],
    "lagoon": ['["water"="lagoon"]'],
    "lake": ['["water"="lake"]'],
}
#: His slider's default: a ring smaller than this many tiles is left out.
WATER_MIN_TILES = 16


def _water_kind(tags: dict) -> str:
    if tags.get("water") == "sea" or tags.get("place") in ("sea", "ocean"):
        return "sea"
    return "lagoon" if tags.get("water") == "lagoon" else "lake"


def rings(ways: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
    """Ways joined end to end, in either direction, into closed rings: what a
    multipolygon's member ways are, one boundary cut into pieces. Mylae's
    ``chainPolylines``, matched on the exact point (OSM repeats the node), and
    a piece that never closes is closed as it stands."""
    todo = [list(w) for w in ways if len(w) >= 2]
    out = []
    while todo:
        ring = todo.pop()
        grown = True
        while ring[0] != ring[-1] and grown:
            grown = False
            for i, w in enumerate(todo):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[-2::-1]
                elif w[-1] == ring[0]:
                    ring = w[:-1] + ring
                elif w[0] == ring[0]:
                    ring = w[:0:-1] + ring
                else:
                    continue
                todo.pop(i)
                grown = True
                break
        if len(ring) >= 3:
            out.append(ring)
    return out


def _water_chunk(c: Bbox, kinds: List[str], out: Dict[str, dict]) -> None:
    bb = f"({c.south},{c.west},{c.north},{c.east})"
    body = "".join(f"{t}{f}{bb};" for k in kinds for f in WATER_KINDS[k]
                   for t in ("way", "relation"))
    try:
        data = overpass(f"[out:json][timeout:120];({body});out geom;")
    except OsmError:
        if (c.north - c.south) / 2 < CHUNK_MIN:
            raise
        midlat, midlon = (c.north + c.south) / 2, (c.east + c.west) / 2
        for part in (Bbox(c.north, midlat, c.west, midlon),
                     Bbox(c.north, midlat, midlon, c.east),
                     Bbox(midlat, c.south, c.west, midlon),
                     Bbox(midlat, c.south, midlon, c.east)):
            _water_chunk(part, kinds, out)
        return
    for e in data.get("elements", []):
        key = f"{e.get('type')}/{e.get('id')}"
        if key in out:
            continue

        def pts(geo):
            return [(round(q["lat"], 6), round(q["lon"], 6)) for q in (geo or []) if q]

        if e.get("type") == "way":
            geo = pts(e.get("geometry"))
            if len(geo) >= 3:
                out[key] = {"kind": _water_kind(e.get("tags") or {}),
                            "outer": [geo], "inner": []}
        elif e.get("type") == "relation":
            members = [m for m in e.get("members") or [] if m.get("type") == "way"]
            outer = [pts(m.get("geometry")) for m in members
                     if m.get("role") in ("outer", "")]
            inner = [pts(m.get("geometry")) for m in members if m.get("role") == "inner"]
            if not outer:            # his fallback: every member way
                outer, inner = [pts(m.get("geometry")) for m in members], []
            out[key] = {"kind": _water_kind(e.get("tags") or {}),
                        "outer": rings(outer), "inner": rings(inner)}


def water(b: Bbox, kinds: List[str],
          progress: Optional[Callable[[int, str], None]] = None) -> List[dict]:
    """Every sea, lagoon and lake polygon of the kinds asked for over the box:
    ``{kind, outer: [ring...], inner: [ring...]}``, each ring ``(lat, lon)``.
    Asked a chunk at a time and kept on disk by the box and the kinds."""
    kinds = [k for k in WATER_KINDS if k in (kinds or [])]
    if not kinds:
        raise OsmError("pick at least one kind of water: seas, lagoons or lakes")
    key = hashlib.sha1(json.dumps([b.envelope().payload(), kinds]).encode()).hexdigest()[:16]
    path = config.cache_dir("osm_water") / f"{key}.json.gz"
    try:
        if path.is_file():
            return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError):
        pass
    require_on()
    parts = _chunks(b, CHUNK_DEG)
    found: Dict[str, dict] = {}
    for n, c in enumerate(parts):
        if progress:
            progress(int(100 * n / len(parts)),
                     f"water: {n + 1} of {len(parts)} stretches, {len(found)} found")
        _water_chunk(c, kinds, found)
    out = list(found.values())
    try:
        path.write_bytes(gzip.compress(json.dumps(out).encode("utf-8")))
    except OSError:
        pass
    return out


def _area(pts: List[Tuple[float, float]]) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1)
                   in zip(pts, pts[1:] + pts[:1]))) / 2


@dataclass
class Water:
    """The water polygons over one map, and which land tiles they cover."""
    rings: int                       # outer rings kept
    small: int                       # outer rings under the size, left out
    holes: int                       # inner rings (islands) kept dry
    by_kind: Dict[str, int]
    to_sea: List[Tuple[int, int]]    # land now, inside the water
    sea_already: int                 # sea now, inside the water

    def payload(self) -> dict:
        return {"rings": self.rings, "small": self.small, "holes": self.holes,
                "by_kind": dict(self.by_kind), "to_sea": len(self.to_sea),
                "sea_already": self.sea_already,
                "to_sea_xy": [v for xy in self.to_sea for v in xy]}


def water_tiles(polys: List[dict], proj: Projection, sea: bytes,
                min_tiles: float = WATER_MIN_TILES) -> Water:
    """The tiles inside the water, islands left dry: every outer ring of at
    least ``min_tiles`` tiles filled, every inner ring cut back out."""
    W, H = proj.w, proj.h
    fill = Image.new("L", (W, H), 0)
    holes = Image.new("L", (W, H), 0)
    df, dh = ImageDraw.Draw(fill), ImageDraw.Draw(holes)
    kept = small = cut = 0
    by_kind: Dict[str, int] = {}
    for poly in polys:
        for ring in poly.get("outer") or []:
            t = [proj.to_tile(la, lo) for la, lo in ring]
            if len(t) < 3 or _area(t) < min_tiles:
                small += 1
                continue
            df.polygon(t, fill=255)
            kept += 1
            by_kind[poly.get("kind", "lake")] = by_kind.get(poly.get("kind", "lake"), 0) + 1
        for ring in poly.get("inner") or []:
            t = [proj.to_tile(la, lo) for la, lo in ring]
            if len(t) >= 3:
                dh.polygon(t, fill=255)
                cut += 1
    inside = ImageChops.subtract(fill, holes).tobytes()
    to_sea = [(i % W, i // W) for i, v in enumerate(inside) if v and not sea[i]]
    already = sum(1 for i, v in enumerate(inside) if v and sea[i])
    return Water(rings=kept, small=small, holes=cut, by_kind=by_kind,
                 to_sea=to_sea, sea_already=already)


def _water_args(body: dict) -> Tuple[List[str], float]:
    kinds = body.get("kinds") or ["sea"]
    if isinstance(kinds, str):
        kinds = [k.strip() for k in kinds.split(",")]
    try:
        size = float(body.get("min_tiles", WATER_MIN_TILES))
    except (TypeError, ValueError):
        raise OsmError("the smallest water to keep is a number of tiles") from None
    return [str(k) for k in kinds], max(0.0, size)


# ---------------------------------------------------------------------------
# places and their boundaries


def search(b: Bbox, proj: Projection, q: str) -> List[dict]:
    """Places matching ``q`` inside the box, each with the tile it falls on."""
    q = (q or "").strip()
    if not q:
        raise OsmError("search for a place by name")
    env = b.envelope()
    got = nominatim("search", {
        "q": q, "format": "jsonv2", "limit": 12, "bounded": 1, "extratags": 1,
        "viewbox": f"{env.west},{env.north},{env.east},{env.south}"})
    out = []
    for r in got or []:
        p = _place(r)
        if p is None:
            continue
        fx, fy = proj.to_tile(p["lat"], p["lon"])
        x, y = round(fx), round(fy)
        p.update(x=x, y=y, on_map=0 <= x < proj.w and 0 <= y < proj.h)
        out.append(p)
    return out


def _place(r: dict) -> Optional[dict]:
    """One Nominatim answer, in the shape the page lists."""
    try:
        lat, lon = float(r["lat"]), float(r["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    level = (r.get("extratags") or {}).get("admin_level")
    name = (r.get("name") or (r.get("display_name") or "").split(",")[0]).strip()
    out = {"name": name, "display": r.get("display_name") or name,
           "lat": lat, "lon": lon,
           "osm_type": r.get("osm_type") or "", "osm_id": r.get("osm_id"),
           "kind": r.get("addresstype") or r.get("type") or "",
           "admin_level": int(level) if str(level or "").isdigit() else None,
           "boundary": r.get("osm_type") == "relation"}
    bb = r.get("boundingbox")
    try:
        s, n, w, e = (float(v) for v in bb)
        out["extent"] = {"north": min(n, MAX_LAT), "south": max(s, -MAX_LAT),
                         "west": w, "east": e}
    except (TypeError, ValueError):
        pass
    return out


def search_world(q: str) -> List[dict]:
    """Places matching ``q`` anywhere, for the world picker: each with its
    point and, where Nominatim gives one, the extent to fit a box around."""
    q = (q or "").strip()
    if not q:
        raise OsmError("search for a place by name")
    got = nominatim("search", {"q": q, "format": "jsonv2", "limit": 12, "extratags": 1})
    return [p for p in (_place(r) for r in got or []) if p is not None]


def fit(b: Bbox, width: int, height: int, keep: str = "width") -> Bbox:
    """The box given the map's own shape, so a tile is as wide as it is tall.

    Tile 0 sits on the west edge and tile ``width-1`` on the east, so the
    shape that does not stretch is ``(width-1) : (height-1)`` in degrees of
    longitude against degrees of Mercator. ``keep`` says which pair of edges
    stays: ``width`` keeps west and east and moves north and south about their
    middle (in Mercator), ``height`` the other way round. The rotation stays.
    """
    want = (width - 1) / max(height - 1, 1)
    mn, ms = merc_deg(b.north), merc_deg(b.south)
    if keep == "height":
        half = (mn - ms) * want / 2
        mid = (b.east + b.west) / 2
        out = Bbox(b.north, b.south, mid - half, mid + half, b.rotation)
    else:
        half = (b.east - b.west) / want / 2
        mid = (mn + ms) / 2
        out = Bbox(inv_merc_deg(mid + half), inv_merc_deg(mid - half),
                   b.west, b.east, b.rotation)
    bad = out.problems()
    if bad:
        raise OsmError("the box cannot take this map's shape there: " + "; ".join(bad))
    return out


def size_for(b: Bbox, width: int = 0, height: int = 0) -> Tuple[int, int]:
    """A map size in the box's own shape: one side given, the other from the
    box (Mylae's ``bboxAspect``, counted between tile centres like ours)."""
    a = b.aspect()
    if width:
        return int(width), max(2, 1 + round((int(width) - 1) / a))
    return max(2, 1 + round((int(height) - 1) * a)), int(height)


def stretch(b: Bbox, width: int, height: int) -> float:
    """How far the box stretches a map of this size: 0 is square tiles, 0.1 is
    a tile ten per cent wider than it is tall (or narrower, negative)."""
    return b.aspect() / ((width - 1) / max(height - 1, 1)) - 1


def boundary(lat: float, lon: float, osm_type: str = "", osm_id=None) -> dict:
    """A place's administrative boundary as GeoJSON: the relation Nominatim
    named, or else the smallest one Overpass says the point is inside."""
    rel = int(osm_id) if osm_type == "relation" and osm_id else None
    if rel is None:
        got = overpass(f"[out:json][timeout:25];is_in({lat},{lon});out tags;")
        cands = sorted(
            ((int(e["tags"]["admin_level"]), e["id"] - 3600000000)
             for e in got.get("elements", [])
             if e.get("type") == "area" and (e.get("tags") or {}).get("boundary")
             == "administrative" and str(e["tags"].get("admin_level", "")).isdigit()
             and e["id"] > 3600000000),
            reverse=True)
        if not cands:
            raise OsmError("OpenStreetMap has no administrative boundary around "
                           "that point")
        rel = cands[0][1]
    got = nominatim("lookup", {"osm_ids": f"R{rel}", "format": "jsonv2",
                               "polygon_geojson": 1})
    item = got[0] if got else None
    if not item or not item.get("geojson"):
        raise OsmError("Nominatim has no outline for that place")
    return item["geojson"]


def boundary_tiles(geo: dict, proj: Projection) -> List[Tuple[int, int]]:
    """The tiles inside a GeoJSON (Multi)Polygon, holes left out."""
    if geo.get("type") == "Polygon":
        polys = [geo["coordinates"]]
    elif geo.get("type") == "MultiPolygon":
        polys = geo["coordinates"]
    else:
        raise OsmError(f"a {geo.get('type')} is not an outline")
    mask = Image.new("L", (proj.w, proj.h), 0)
    draw = ImageDraw.Draw(mask)
    for poly in polys:
        for n, ring in enumerate(poly):
            pts = [proj.to_tile(lat, lon) for lon, lat in ring]
            if len(pts) >= 3:
                draw.polygon(pts, fill=0 if n else 1)
    data = mask.tobytes()
    return [(i % proj.w, i // proj.w) for i, v in enumerate(data) if v]


def slippy_zoom(proj: Projection, px_per_tile: float) -> int:
    """The OSM zoom whose 256-pixel tiles come out about 256 pixels on screen."""
    deg = proj.b.east - proj.b.west
    want = px_per_tile * (proj.w - 1) * 360.0 / (deg * 256.0)
    return max(0, min(18, round(math.log2(max(want, 1e-9)))))


# ---------------------------------------------------------------------------
# into the paint session: one stroke each, undone and saved like any other


def _box_proj(cm) -> Tuple[Bbox, Projection]:
    box, _ = box_for(cm)
    if box is None:
        raise OsmError("give the map its real-world box first")
    return box, Projection(box, cm.terrain.width, cm.terrain.height)


def paint_coast(sess) -> dict:
    """Every land tile on the water side of the real coastline, made sea.

    The water brush's stroke: its colours, measured off this map, on the
    regions, heights and ground types together, settlement and port pixels
    left alone. Refused when the coastline leaks.
    """
    from . import campaint
    cm = sess.cm
    box, proj = _box_proj(cm)
    coast = analyse(coastline(box), proj, cm.sea)
    if coast.leaks:
        raise OsmError(
            f"the coastline has a gap: the water side reaches {coast.leak} of the "
            f"{coast.seeds} tiles that are land by the coastline's own reckoning, "
            "so filling it would put sea across land. Nothing was painted: "
            "trace the gap by hand with the water brush, using the line as a guide")
    if not coast.to_sea:
        return {"ok": True, "changed": {}, "tiles": 0,
                "note": "every tile on the water side of the coastline is sea already",
                "state": sess.state()}
    colours = campaint._resolve(cm, sess, {"tool": "water"})
    return campaint._stroke_over(sess, coast.to_sea, colours, "water", {},
                                 label="OSM coastline: the water side made sea")


def paint_water(sess, body: dict) -> dict:
    """Every land tile inside OSM's seas, lagoons or lakes (the kinds asked
    for, the small ones left out, islands kept dry), made sea: the water
    brush's stroke, as for the coastline."""
    from . import campaint
    cm = sess.cm
    box, proj = _box_proj(cm)
    kinds, size = _water_args(body)
    got = water_tiles(water(box, kinds), proj, cm.sea, size)
    if not got.to_sea:
        return {"ok": True, "changed": {}, "tiles": 0,
                "note": "every tile inside that water is sea already",
                "state": sess.state()}
    colours = campaint._resolve(cm, sess, {"tool": "water"})
    return campaint._stroke_over(sess, got.to_sea, colours, "water", {},
                                 label=f"OSM water ({', '.join(kinds)}) made sea")


def paint_boundary(sess, body: dict) -> dict:
    """A place's administrative boundary painted onto one region, land only.

    The region's own colour out of ``descr_regions.txt`` (or the wizard's
    pending region), the same snapping the brush uses; sea tiles and the two
    markers are left as they are.
    """
    from . import campaint
    cm = sess.cm
    _, proj = _box_proj(cm)
    region = str(body.get("region") or "").strip()
    if not region:
        raise OsmError("pick the region the boundary is painted onto")
    try:
        lat, lon = float(body["lat"]), float(body["lon"])
    except (KeyError, TypeError, ValueError):
        raise OsmError("a place needs its latitude and longitude") from None
    geo = boundary(lat, lon, str(body.get("osm_type") or ""), body.get("osm_id"))
    sea = cm.sea
    w = cm.terrain.width
    tiles = [(x, y) for x, y in boundary_tiles(geo, proj) if not sea[y * w + x]]
    if not tiles:
        raise OsmError("that boundary covers no land tile of this map")
    colours = campaint._resolve(cm, sess, {"target": "regions", "region": region})
    name = str(body.get("name") or "the place").strip()
    return campaint._stroke_over(sess, tiles, colours, "brush", {},
                                 label=f"OSM boundary of {name} onto {region}")
