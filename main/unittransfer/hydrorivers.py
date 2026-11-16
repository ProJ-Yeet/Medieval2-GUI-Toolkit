"""HydroRIVERS, read from the file a user downloaded, as the map's rivers.

**From Mylae's M2TW Editor** (github.com/Machiavello-1441/m2tw-editor, used with
the author's permission): his HydroRIVERS import, ``src/components/newmap/
hydrorivers/`` (``shpReader.js``, ``dbfReader.js``, ``network.js``,
2026-10-14). OpenStreetMap's waterways are drawn by whoever mapped them, with
side channels, canals and loops; HydroRIVERS (Lehner & Grill 2013, from
hydrosheds.org, free under its own licence) is one clean network in which
every reach names the reach it flows into (``NEXT_DOWN``) and carries its
Strahler order (``ORD_STRA``), so "only the big rivers" is a number rather than
a guess at tags. The toolkit never downloads it: the user fetches the regional
shapefile ZIP from hydrosheds.org and names it, as in his panel.

What is his, written again in Python:

    the shapefile (.shp polylines, types 3, 13 and 23) and its .dbf table, read
    for HYRIV_ID, NEXT_DOWN and ORD_STRA; WGS84 longitude and latitude only
    every reach of at least the chosen order, plus everything it flows into
    each reach turned to run downstream: its far end is the one nearest the
    reach it flows into, else the one furthest from what flows into it

What is ours: the file is read as a stream, the .shp and the .dbf in step, so
a 300 MB continent costs no more memory than a county, from a ZIP or from the
two loose files; and the reaches go on to :func:`mapgen.draw_features`, the
same drawer OpenStreetMap's waterways go through, which keeps every river a
tree, cuts it at settlements and ports and puts one source at its head. Where
neither neighbour says which way a reach runs, the file's own order is kept,
which in HydroRIVERS is downstream.
"""
from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from typing import BinaryIO, Dict, Iterator, List, Optional, Tuple

from . import i18n as _i18n

FIELDS = ("HYRIV_ID", "NEXT_DOWN", "ORD_STRA")
LINES = (3, 13, 23)

Point = Tuple[float, float]          # (lon, lat), as the file has it


class HydroError(ValueError):
    pass


# ---------------------------------------------------------------------------
# the two files


def _read(f: BinaryIO, n: int) -> bytes:
    got = f.read(n)
    if len(got) != n:
        raise HydroError(_i18n.msg("eng.hydrorivers.truncated", "the river file stops in the middle of a record"))
    return got


class _Dbf:
    """The attribute table, one row at a time, in the .shp's order."""

    def __init__(self, f: BinaryIO):
        self.f = f
        head = _read(f, 32)
        self.count = struct.unpack("<I", head[4:8])[0]
        header, self.size = struct.unpack("<HH", head[8:12])
        self.fields: Dict[str, Tuple[int, int]] = {}
        at = 1
        rest = _read(f, header - 32)
        for pos in range(0, len(rest) - 1, 32):
            if rest[pos] == 13:
                break
            name = rest[pos:pos + 11].split(b"\0")[0].decode("ascii", "replace").strip().upper()
            width = rest[pos + 16]
            self.fields[name] = (at, width)
            at += width
        missing = [k for k in FIELDS if k not in self.fields]
        if missing:
            raise HydroError(_i18n.msg("eng.hydrorivers.not_hydrorivers", "this is not a HydroRIVERS table: it has no {fields}. Use the official regional shapefile ZIP", fields=", ".join(missing)))

    def next(self) -> Optional[Dict[str, int]]:
        row = _read(self.f, self.size)
        if row[:1] == b"*":                     # a deleted record
            return None
        out = {}
        for k in FIELDS:
            at, width = self.fields[k]
            text = row[at:at + width].strip()
            out[k] = int(float(text)) if text else 0
        return out


def _reaches(shp: BinaryIO, dbf: BinaryIO, box) -> Iterator[dict]:
    """Every reach whose own box meets ``box``: ``{HYRIV_ID, NEXT_DOWN,
    ORD_STRA, parts: [[(lon, lat), ...], ...]}``."""
    table = _Dbf(dbf)
    head = _read(shp, 100)
    if struct.unpack(">i", head[:4])[0] != 9994:
        raise HydroError(_i18n.msg("eng.hydrorivers.not_shapefile", "this is not a shapefile"))
    if struct.unpack("<i", head[32:36])[0] not in LINES:
        raise HydroError(_i18n.msg("eng.hydrorivers.not_lines", "this shapefile holds polygons or points, and HydroRIVERS is lines"))
    n = 0
    while True:
        rh = shp.read(8)
        if not rh:
            break
        if len(rh) < 8:
            raise HydroError(_i18n.msg("eng.hydrorivers.truncated", "the river file stops in the middle of a record"))
        size = struct.unpack(">i", rh[4:8])[0] * 2
        body = _read(shp, size)
        if n >= table.count:
            raise HydroError(_i18n.msg("eng.hydrorivers.counts", "the river file and its table do not hold the same number of reaches"))
        row = table.next()
        n += 1
        kind = struct.unpack("<i", body[:4])[0]
        if kind == 0 or row is None:
            continue
        west, south, east, north = struct.unpack("<4d", body[4:36])
        if west < -180 or east > 180 or south < -90 or north > 90:
            raise HydroError(_i18n.msg("eng.hydrorivers.not_wgs84", "the river coordinates are not longitude and latitude; use the official WGS84 HydroRIVERS data"))
        if east < box.west or west > box.east or north < box.south or south > box.north:
            continue
        nparts, npoints = struct.unpack("<ii", body[36:44])
        starts = list(struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])) + [npoints]
        base = 44 + 4 * nparts
        xy = struct.unpack(f"<{2 * npoints}d", body[base:base + 16 * npoints])
        parts = [[(xy[2 * i], xy[2 * i + 1]) for i in range(a, b)]
                 for a, b in zip(starts, starts[1:]) if b - a > 1]
        if parts:
            yield dict(row, parts=parts)
    if n != table.count:
        raise HydroError(_i18n.msg("eng.hydrorivers.counts", "the river file and its table do not hold the same number of reaches"))


def read(path, box) -> List[dict]:
    """The reaches under ``box`` (a :class:`osmmap.Bbox`, its envelope is
    used) from a HydroRIVERS ZIP, a ``.shp`` with its ``.dbf`` beside it, or a
    folder holding them."""
    p = Path(str(path).strip().strip('"'))
    env = box.envelope() if hasattr(box, "envelope") else box
    if p.is_dir():
        shps = sorted(p.glob("*.shp"))
        if not shps:
            raise HydroError(_i18n.msg("eng.hydrorivers.no_shp", "{path} holds no .shp file", path=p))
        p = shps[0]
    if not p.is_file():
        raise HydroError(_i18n.msg("eng.hydrorivers.no_file", "{path} is not a file", path=p))
    out: List[dict] = []
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            shps = [n for n in names if n.lower().endswith(".shp")]
            if not shps:
                raise HydroError(_i18n.msg("eng.hydrorivers.zip_no_shp", "this ZIP holds no shapefile; download the shapefile version, not the geodatabase"))
            for s in shps:
                d = next((n for n in names if n.lower() == s[:-4].lower() + ".dbf"), None)
                if d is None:
                    raise HydroError(_i18n.msg("eng.hydrorivers.no_dbf", "{name} has no .dbf table beside it", name=s))
                with z.open(s) as a, z.open(d) as b:
                    out += _reaches(a, b, env)
        return out
    if p.suffix.lower() != ".shp":
        raise HydroError(_i18n.msg("eng.hydrorivers.which_file", "name a HydroRIVERS ZIP, a .shp file or the folder holding one"))
    d = next((q for q in p.parent.iterdir() if q.name.lower() == p.stem.lower() + ".dbf"), None)
    if d is None:
        raise HydroError(_i18n.msg("eng.hydrorivers.no_dbf", "{name} has no .dbf table beside it", name=p.name))
    with open(p, "rb") as a, open(d, "rb") as b:
        out += _reaches(a, b, env)
    return out


# ---------------------------------------------------------------------------
# the network


def select(reaches: List[dict], min_order: int) -> Dict[int, dict]:
    """Every reach of order ``min_order`` or more, and every reach below it."""
    by_id = {r["HYRIV_ID"]: r for r in reaches}
    out: Dict[int, dict] = {}
    for seed in reaches:
        if seed["ORD_STRA"] < min_order:
            continue
        r = seed
        while r is not None and r["HYRIV_ID"] not in out:
            out[r["HYRIV_ID"]] = r
            r = by_id.get(r["NEXT_DOWN"])
    return out


def _ends(r: dict) -> Tuple[Point, Point]:
    return r["parts"][0][0], r["parts"][-1][-1]


def _d2(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def downstream(reach: dict, chosen: Dict[int, dict],
               feeders: Dict[int, List[dict]]) -> List[Point]:
    """The reach as one line running downstream (his ``upstreamEndpoint``)."""
    line = [pt for part in reach["parts"] for pt in part]
    a, b = _ends(reach)
    nxt = chosen.get(reach["NEXT_DOWN"])
    if nxt is not None:
        t = _ends(nxt)
        da, db = min(_d2(a, x) for x in t), min(_d2(b, x) for x in t)
        if abs(da - db) > 1e-16:
            return line if db < da else line[::-1]
    up = [e for f in feeders.get(reach["HYRIV_ID"], ()) for e in _ends(f)]
    if up:
        da, db = min(_d2(a, x) for x in up), min(_d2(b, x) for x in up)
        if abs(da - db) > 1e-16:
            return line if da < db else line[::-1]
    return line


def rivers(reaches: List[dict], min_order: int) -> Dict[str, List[Tuple[float, float]]]:
    """``{id: [(lat, lon), ...]}`` downstream, the shape :func:`mapgen.chain`
    and :func:`mapgen.draw_features` take OpenStreetMap's waterways in."""
    chosen = select(reaches, min_order)
    feeders: Dict[int, List[dict]] = {}
    for r in chosen.values():
        feeders.setdefault(r["NEXT_DOWN"], []).append(r)
    return {str(i): [(round(lat, 6), round(lon, 6)) for lon, lat in downstream(r, chosen, feeders)]
            for i, r in chosen.items()}
