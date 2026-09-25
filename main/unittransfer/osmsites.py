"""Phase 87f. Historic sites out of OpenStreetMap, for a map or a new one.

Mylae's ``OsmHistoricTagFetcher``: castles, forts, monasteries and eighteen
more, each an OSM tag (eleven ``historic=*``, ten ``castle_type=*``), fetched
for the box and put on the map as points, one colour a tag, with a
``historic_features.txt`` listing every point by its pixel.

**His tags, his colours, his file.** The table below is his, in his order and
with his labels, and a tag's colour is his hash of ``key=value`` through the
same HSL, so a castle is the same red here as there. The file is his format
line for line (``Castle; x12; y34; name: "Bodiam"``, ``x`` and ``y`` the pixel
counted from the top-left of the regions map); the only change is a hyphen
where his comment lines have a long dash, and a comment is not read.

**Where it departs from his.**

* One query a chunk for every tag asked, not one a tag, and each tag kept on
  disk by the box: ticking a twelfth tag asks only for that one.
* ``out center`` rather than ``out geom``: a castle's point is the middle of
  its outline rather than the mean of its nodes, which is the same tile at any
  scale a campaign map has, and a city wall comes back as one point instead of
  every stone of it. An answer that does carry geometry is still read his way.
* A chunk that fails is split in four, as the coastline's is, rather than the
  whole fetch failing.
* **A site becomes a thing on the map**, not only a line in a file: each point
  carries the tile it stands on in the strat's own coordinates (``y`` counted
  from the bottom), so the page can put a fort or a watchtower there through
  22a's writer, start a region there, or, on the world picker, make it a city
  of 87e's new campaign. Which of those a tag suggests is in the table: a
  castle a fort, a tower a watchtower, a monastery or a mosque a settlement.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from typing import Callable, Dict, List, Optional, Sequence

from . import config, osmmap
from .osmmap import Bbox, OsmError, Projection

#: (key, value, label, what it is, what it suggests on the map). His order.
TAGS = (
    ("historic", "castle", "Castle", "A (former) castle, fortress or palace.", "fort"),
    ("historic", "caravanserai", "Caravanserai", "Roadside inn along trade routes.", "settlement"),
    ("historic", "church", "Historic Church", "A church building of historic importance.", "settlement"),
    ("historic", "city_wall", "City Walls", "Walls encircling a settlement for defence.", "settlement"),
    ("historic", "fort", "Fort", "A military fortification.", "fort"),
    ("historic", "mine", "Historic Mine", "A historic mine.", ""),
    ("historic", "monastery", "Monastery", "A historic monastery, convent or abbey.", "settlement"),
    ("historic", "mosque", "Historic Mosque", "A mosque of historic significance.", "settlement"),
    ("historic", "road", "Historic Road", "A historic road or track.", ""),
    ("historic", "temple", "Temple", "A historic temple.", "settlement"),
    ("historic", "tower", "Historic Tower", "A tower of historic interest.", "watchtower"),
    ("castle_type", "defensive", "Defensive Castle", "Built primarily for military defence.", "fort"),
    ("castle_type", "palace", "Palace", "A castle that is also a palace.", "settlement"),
    ("castle_type", "stately", "Stately Home", "A large country house of historic significance.", ""),
    ("castle_type", "manor", "Manor House", "A manor house.", ""),
    ("castle_type", "kremlin", "Kremlin", "A Russian fortified complex.", "settlement"),
    ("castle_type", "fortress", "Fortress", "A large fortified military complex.", "fort"),
    ("castle_type", "castrum", "Castrum", "A Roman military camp or fort.", "fort"),
    ("castle_type", "hill_fort", "Hill Fort", "An Iron Age fortified settlement on a hilltop.", "fort"),
    ("castle_type", "citadel", "Citadel", "A fortified core of a city.", "fort"),
    ("castle_type", "watchtower", "Watchtower", "A tower used for observation.", "watchtower"),
)

#: His two groups, by key.
GROUPS = (("historic", "Historic"), ("castle_type", "Castle types (castle_type=*)"))

#: What a new fetch ticks, when nothing was asked for yet.
DEFAULT = ("historic=castle", "historic=fort", "historic=monastery", "historic=tower")

HEAD = "[out:json][timeout:180][maxsize:536870912];"

BY_KEY = {f"{k}={v}": (k, v, label, desc, hint) for k, v, label, desc, hint in TAGS}


def colour(key: str, value: str) -> List[int]:
    """His ``tagColor``: a hash of ``key=value`` as a hue, saturation 65%,
    lightness 60%, in RGB. Rounded as JavaScript rounds, half up."""
    h = 0
    for ch in f"{key}={value}":
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    hue, s, l = h % 360, 65, 60
    a = s * min(l, 100 - l) / 100

    def f(n):
        k = (n + hue / 30) % 12
        return math.floor(255 * (l / 100 - a / 100 * max(-1, min(k - 3, min(9 - k, 1)))) + 0.5)

    return [f(0), f(8), f(4)]


def tags_payload() -> List[dict]:
    """The table for the page: each tag with its group, colour and suggestion."""
    return [{"tag": f"{k}={v}", "key": k, "value": v, "label": label, "desc": desc,
             "suggest": hint, "colour": colour(k, v),
             "group": dict(GROUPS)[k]} for k, v, label, desc, hint in TAGS]


def pick_tags(asked) -> List[str]:
    """The tags asked for, in the table's order; an unknown one is refused."""
    if isinstance(asked, str):
        asked = [t.strip() for t in asked.split(",") if t.strip()]
    asked = [str(t) for t in (asked or [])]
    bad = [t for t in asked if t not in BY_KEY]
    if bad:
        raise OsmError(f"not a historic tag this knows: {', '.join(bad)}")
    if not asked:
        raise OsmError("tick at least one kind of historic site")
    return [t for t in BY_KEY if t in asked]


# ---------------------------------------------------------------------------
# the fetch


def _centre(e: dict) -> Optional[tuple]:
    """A point for an element: a node's own, ``out center``'s centre, or his
    mean of the geometry when the answer carries one."""
    if e.get("lat") is not None and e.get("lon") is not None:
        return float(e["lat"]), float(e["lon"])
    c = e.get("center")
    if c and c.get("lat") is not None:
        return float(c["lat"]), float(c["lon"])
    pts = e.get("geometry") or [p for m in e.get("members") or []
                                for p in (m.get("geometry") or [])]
    pts = [p for p in pts if p and p.get("lat") is not None]
    if not pts:
        return None
    return (sum(p["lat"] for p in pts) / len(pts), sum(p["lon"] for p in pts) / len(pts))


def _chunk(c: Bbox, tags: Sequence[str], out: Dict[str, Dict[str, dict]],
           progress: Callable[[str], None]) -> None:
    bb = f"({c.south},{c.west},{c.north},{c.east})"
    body = "".join(f'nwr["{BY_KEY[t][0]}"="{BY_KEY[t][1]}"]{bb};' for t in tags)
    try:
        data = osmmap.overpass(f"{HEAD}({body});out center tags;")
    except OsmError:
        if (c.north - c.south) / 2 < osmmap.CHUNK_MIN:
            raise
        progress("splitting a crowded stretch in four")
        midlat, midlon = (c.north + c.south) / 2, (c.east + c.west) / 2
        for part in (Bbox(c.north, midlat, c.west, midlon),
                     Bbox(c.north, midlat, midlon, c.east),
                     Bbox(midlat, c.south, c.west, midlon),
                     Bbox(midlat, c.south, midlon, c.east)):
            _chunk(part, tags, out, progress)
        return
    for e in data.get("elements", []):
        at = _centre(e)
        if at is None:
            continue
        et = e.get("tags") or {}
        key = f"{e.get('type')}/{e.get('id')}"
        for t in tags:
            k, v = BY_KEY[t][:2]
            if et.get(k) == v and key not in out[t]:
                out[t][key] = {"id": key, "lat": round(at[0], 6), "lon": round(at[1], 6),
                               "name": et.get("name") or et.get("name:en") or ""}


def _cache_path(b: Bbox, tag: str):
    key = hashlib.sha1(json.dumps([b.envelope().payload(), tag]).encode()).hexdigest()[:16]
    return config.cache_dir("osm_historic") / f"{key}.json.gz"


def fetch(b: Bbox, tags: Sequence[str],
          progress: Optional[Callable[[int, str], None]] = None) -> Dict[str, List[dict]]:
    """Every element of each tag over the box: ``{tag: [{id, lat, lon, name}]}``.

    A tag already fetched for this box is read off disk; the rest are asked in
    one query a chunk, and each kept apart, so the next fetch with one tag
    more sends only that tag."""
    tags = pick_tags(tags)
    got: Dict[str, List[dict]] = {}
    missing = []
    for t in tags:
        try:
            p = _cache_path(b, t)
            if p.is_file():
                got[t] = json.loads(gzip.decompress(p.read_bytes()).decode("utf-8"))
                continue
        except (OSError, ValueError):
            pass
        missing.append(t)
    if missing:
        osmmap.require_on()
        parts = osmmap._chunks(b, osmmap.CHUNK_DEG)
        found: Dict[str, Dict[str, dict]] = {t: {} for t in missing}
        for n, c in enumerate(parts):
            pct = int(100 * n / len(parts))
            if progress:
                progress(pct, f"historic sites: {n + 1} of {len(parts)} stretches, "
                              f"{sum(len(v) for v in found.values())} found")
            _chunk(c, missing, found,
                   lambda msg: progress and progress(pct, f"historic sites: {msg}"))
        for t in missing:
            got[t] = list(found[t].values())
            try:
                _cache_path(b, t).write_bytes(
                    gzip.compress(json.dumps(got[t]).encode("utf-8")))
            except OSError:
                pass
    return {t: got[t] for t in tags}


# ---------------------------------------------------------------------------
# onto a map


def sites(found: Dict[str, List[dict]], proj: Optional[Projection] = None) -> List[dict]:
    """Every element as a site the page draws and acts on.

    With a projection each carries its pixel (``x``, ``y`` from the top-left,
    his rounding) and the strat's tile (``gx``, ``gy``, ``y`` from the bottom),
    and ``on_map``; one off the map is kept but says so. Without one (the world
    picker, before a map exists) a site is only its point."""
    out = []
    for t, els in found.items():
        k, v, label, _, hint = BY_KEY[t]
        rgb = colour(k, v)
        for e in els:
            s = {"id": e["id"], "tag": t, "label": label, "name": e.get("name") or "",
                 "lat": e["lat"], "lon": e["lon"], "colour": rgb, "suggest": hint}
            if proj is not None:
                fx, fy = proj.to_tile(e["lat"], e["lon"])
                x, y = math.floor(fx + 0.5), math.floor(fy + 0.5)
                s.update(x=x, y=y, gx=x, gy=proj.h - 1 - y,
                         on_map=0 <= x < proj.w and 0 <= y < proj.h)
            out.append(s)
    return out


def features_text(found: Dict[str, List[dict]], proj: Projection) -> str:
    """``historic_features.txt`` in his shape: a block a tag, a line a point on
    the map, the pixel counted from the regions map's top-left."""
    lines = ["; OSM Historic Features - Bulk Export", f"; Map size: {proj.w}x{proj.h}", ""]
    for t in found:
        placed = [s for s in sites({t: found[t]}, proj) if s["on_map"]]
        label = BY_KEY[t][2]
        lines.append(f"; === {label} ({t}) - {len(placed)} features ===")
        for s in placed:
            name = f'"{s["name"]}"' if s["name"] else '"(no name)"'
            lines.append(f"{label}; x{s['x']}; y{s['y']}; name: {name}")
        lines.append("")
    return "\n".join(lines)


def for_map(cm, tags, progress=None) -> dict:
    """The sites over a campaign map's kept box: the page's points and list,
    counts by tag, and the file."""
    box, _ = osmmap.box_for(cm)
    if box is None:
        raise OsmError("give the map its real-world box first")
    proj = Projection(box, cm.terrain.width, cm.terrain.height)
    found = fetch(box, tags, progress)
    got = sites(found, proj)
    return {"sites": got, "text": features_text(found, proj),
            "counts": {t: sum(1 for s in got if s["tag"] == t and s["on_map"])
                       for t in found},
            "off_map": sum(1 for s in got if not s["on_map"])}


def for_box(b: Bbox, tags, progress=None) -> dict:
    """The sites under a box with no map yet (the world picker), each only its
    point, the ones outside a turned box left out."""
    found = fetch(b, tags, progress)
    got = []
    if b.rotated:
        # inside the turned rectangle: turned back, it is inside the plain one
        for s in sites(found):
            lat, lon = b.turn(s["lat"], s["lon"], -b.rotation)
            if b.south <= lat <= b.north and b.west <= lon <= b.east:
                got.append(s)
    else:
        got = [s for s in sites(found)
               if b.south <= s["lat"] <= b.north and b.west <= s["lon"] <= b.east]
    return {"sites": got, "counts": {t: sum(1 for s in got if s["tag"] == t) for t in found}}
