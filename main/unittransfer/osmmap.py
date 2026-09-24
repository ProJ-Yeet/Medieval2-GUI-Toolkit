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

from PIL import Image, ImageDraw

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


@dataclass
class Bbox:
    north: float
    south: float
    west: float
    east: float

    def payload(self) -> dict:
        return {"north": self.north, "south": self.south,
                "west": self.west, "east": self.east}

    def problems(self) -> List[str]:
        out = []
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
    bad = b.problems()
    if bad:
        raise OsmError("; ".join(bad))
    return b


def bbox_text(b: Bbox, width: int, height: int) -> str:
    """The box as a ``bbox_coords.txt``, in the shape Mylae's editor reads."""
    return "\n".join([
        "# the campaign map's real-world box, written by the Medieval 2 GUI Toolkit",
        f"# {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"north={b.north:.6f}", f"south={b.south:.6f}",
        f"west={b.west:.6f}", f"east={b.east:.6f}",
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


class Projection:
    def __init__(self, b: Bbox, width: int, height: int):
        self.b, self.w, self.h = b, width, height
        self.mn, self.ms = merc(b.north), merc(b.south)

    def to_tile(self, lat: float, lon: float) -> Tuple[float, float]:
        b = self.b
        return ((lon - b.west) / (b.east - b.west) * (self.w - 1),
                (self.mn - merc(lat)) / (self.mn - self.ms) * (self.h - 1))

    def to_geo(self, fx: float, fy: float) -> Tuple[float, float]:
        b = self.b
        lon = b.west + fx / (self.w - 1) * (b.east - b.west)
        m = self.mn - fy / (self.h - 1) * (self.mn - self.ms)
        return math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2), lon


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


def tile(z: int, x: int, y: int) -> bytes:
    """One map tile, off the disk if it was fetched in the last 30 days."""
    if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        raise OsmError(f"{z}/{x}/{y} is not a map tile")
    path = config.cache_dir("osm_tiles") / str(z) / str(x) / f"{y}.png"
    try:
        if path.is_file() and time.time() - path.stat().st_mtime < TILE_DAYS * 86400:
            return path.read_bytes()
    except OSError:
        pass
    s = require_on()
    with _TILE_LOCK:
        now = time.time()
        while _TILE_TIMES and now - _TILE_TIMES[0] > 60:
            _TILE_TIMES.popleft()
        if len(_TILE_TIMES) >= TILE_BUDGET:
            raise OsmError("the backdrop has asked for a lot of tiles in the last "
                           "minute - it will carry on shortly")
        _TILE_TIMES.append(now)
    last = None
    for tpl in s["tiles"]:
        try:
            raw = _fetch(tpl.replace("{z}", str(z)).replace("{x}", str(x))
                         .replace("{y}", str(y)), timeout=20)
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            continue
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        except OSError:
            pass
        return raw
    raise OsmError(f"no tile server answered ({last})")


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
# places and their boundaries


def search(b: Bbox, proj: Projection, q: str) -> List[dict]:
    """Places matching ``q`` inside the box, each with the tile it falls on."""
    q = (q or "").strip()
    if not q:
        raise OsmError("search for a place by name")
    got = nominatim("search", {
        "q": q, "format": "jsonv2", "limit": 12, "bounded": 1, "extratags": 1,
        "viewbox": f"{b.west},{b.north},{b.east},{b.south}"})
    out = []
    for r in got or []:
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        fx, fy = proj.to_tile(lat, lon)
        x, y = round(fx), round(fy)
        level = (r.get("extratags") or {}).get("admin_level")
        name = (r.get("name") or (r.get("display_name") or "").split(",")[0]).strip()
        out.append({"name": name, "display": r.get("display_name") or name,
                    "lat": lat, "lon": lon, "x": x, "y": y,
                    "on_map": 0 <= x < proj.w and 0 <= y < proj.h,
                    "osm_type": r.get("osm_type") or "", "osm_id": r.get("osm_id"),
                    "kind": r.get("addresstype") or r.get("type") or "",
                    "admin_level": int(level) if str(level or "").isdigit() else None,
                    "boundary": r.get("osm_type") == "relation"})
    return out


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
