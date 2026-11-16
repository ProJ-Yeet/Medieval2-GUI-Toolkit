"""A HydroRIVERS-shaped shapefile, written for the tests (no real data ships).

``write(stem, reaches)`` writes ``stem.shp`` and ``stem.dbf``; each reach is
``{HYRIV_ID, NEXT_DOWN, ORD_STRA, parts: [[(lon, lat), ...]]}``.
"""
import struct
from pathlib import Path

FIELDS = (("HYRIV_ID", 10), ("NEXT_DOWN", 10), ("ORD_STRA", 4))


def write(stem, reaches, shape_type=3, fields=FIELDS):
    stem = Path(stem)
    recs = []
    for i, r in enumerate(reaches, 1):
        pts = [pt for part in r["parts"] for pt in part]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        starts, at = [], 0
        for part in r["parts"]:
            starts.append(at)
            at += len(part)
        body = struct.pack("<i4dii", shape_type, min(xs), min(ys), max(xs), max(ys),
                           len(r["parts"]), len(pts))
        body += struct.pack(f"<{len(starts)}i", *starts)
        body += b"".join(struct.pack("<2d", *p) for p in pts)
        recs.append(struct.pack(">ii", i, len(body) // 2) + body)
    allx = [p[0] for r in reaches for part in r["parts"] for p in part] or [0]
    ally = [p[1] for r in reaches for part in r["parts"] for p in part] or [0]
    total = 100 + sum(len(x) for x in recs)
    head = struct.pack(">i5ii", 9994, 0, 0, 0, 0, 0, total // 2)
    head += struct.pack("<ii4d4d", 1000, shape_type, min(allx), min(ally), max(allx),
                        max(ally), 0, 0, 0, 0)
    stem.with_suffix(".shp").write_bytes(head + b"".join(recs))

    size = 1 + sum(w for _, w in fields)
    dhead = struct.pack("<BBBBIHH20x", 3, 126, 1, 1, len(reaches),
                        32 + 32 * len(fields) + 1, size)
    for name, width in fields:
        dhead += struct.pack("<11sc4xBB14x", name.encode(), b"N", width, 0)
    dhead += b"\r"
    rows = b"".join(b" " + b"".join(str(r.get(n, 0)).rjust(w).encode() for n, w in fields)
                    for r in reaches)
    stem.with_suffix(".dbf").write_bytes(dhead + rows + b"\x1a")
