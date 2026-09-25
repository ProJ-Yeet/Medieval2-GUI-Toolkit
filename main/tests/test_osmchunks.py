"""Phase 87g: every Overpass fetch in chunks, each chunk recorded, one fetched
again alone.

    python -m tests.test_osmchunks

Nothing here touches the network: a small HTTP server on this machine plays
Overpass. It fails every query whose box holds a "bad" point while that is
switched on, so one stretch of the map goes unanswered however far it is split.

1. The coastline: a stretch that never answers is split down to the smallest
   chunk and recorded as failed, and the rest of the fetch is kept rather than
   the whole of it failing; a fetch where nothing answered is refused and
   nothing is kept. The record: the fetches kept for a box, numbered chunks,
   which failed and why, what each found.
2. Fetched again: the failed chunk asked alone (one query, its own box), what
   it finds merged in, and the next look at the coastline sees it with nothing
   sent; a chunk that fails again stays failed and nothing is lost.
3. The same for the water, 27's rivers and 87f's historic sites.
4. The routes.
"""
import json
import re
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import campmap, config, mapgen, osmmap, osmsites  # noqa: E402
from unittransfer.maptga import TgaInfo, encode  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

# ---------------------------------------------------------------------------
# the fake Overpass

N, S, WEST, EAST = 50.0, 40.0, 0.0, 15.0
#: a point whose stretch never answers while BAD["on"]
BAD = {"on": False, "lat": 47.3, "lon": 10.2}
QUERIES = []


def way(i, pts, **tags):
    return {"type": "way", "id": i, "tags": tags,
            "geometry": [{"lat": a, "lon": o} for a, o in pts]}


#: a coastline way in each corner of the map, one right beside the bad point
COAST = [way(1, [(41.0, 1.0), (41.0, 2.0)]), way(2, [(49.0, 14.0), (49.0, 13.0)]),
         way(3, [(BAD["lat"], BAD["lon"]), (BAD["lat"], BAD["lon"] + 0.1)])]
WATER = [way(10, [(47.2, 10.1), (47.4, 10.1), (47.4, 10.3), (47.2, 10.1)], natural="water"),
         way(11, [(42.0, 3.0), (42.2, 3.0), (42.2, 3.2), (42.0, 3.0)], natural="water")]
RIVERS = [way(20, [(47.25, 10.15), (47.35, 10.25)], waterway="river"),
          way(21, [(43.0, 2.0), (43.5, 2.5)], waterway="river")]
SITES = [{"type": "node", "id": 30, "lat": BAD["lat"], "lon": BAD["lon"],
          "tags": {"historic": "castle", "name": "Hidden"}},
         {"type": "node", "id": 31, "lat": 44.0, "lon": 4.0,
          "tags": {"historic": "castle", "name": "Plain"}}]


def at(e):
    if e.get("lat") is not None:
        return e["lat"], e["lon"]
    g = e["geometry"][0]
    return g["lat"], g["lon"]


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
        q = urllib.parse.unquote(body)
        m = re.search(r"\(([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\)", q)
        s, w, n, e = map(float, m.groups())
        QUERIES.append((s, w, n, e, q))
        if BAD["on"] and s <= BAD["lat"] <= n and w <= BAD["lon"] <= e:
            self.send_error(504)
            return
        pool = (COAST if '"coastline"' in q else WATER if '"water"' in q
                else RIVERS if "waterway" in q else SITES if '"historic"' in q else [])
        found = [x for x in pool if s <= at(x)[0] <= n and w <= at(x)[1] <= e]
        raw = json.dumps({"elements": found}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
FAKE = f"http://127.0.0.1:{fake.server_address[1]}"
threading.Thread(target=fake.serve_forever, daemon=True).start()
config.save_settings(osm_overpass=[FAKE + "/interpreter"], osm_enabled=True)

box = osmmap.Bbox(N, S, WEST, EAST)


def inside(ch, lat, lon):
    return ch["south"] <= lat <= ch["north"] and ch["west"] <= lon <= ch["east"]


# ---------------------------------------------------------------------------
print("1) the coastline, with a stretch that never answers")
BAD["on"] = True
ways = osmmap.coastline(box)
check(f"the fetch is kept, not failed: {len(ways)} of 3 ways, the one in the "
      "bad stretch missing", len(ways) == 2
      and all(w[0][0] != BAD["lat"] for w in ways))
recs = osmmap.fetches_for(box)
rec = recs[0] if recs else {}
bad = [ch for ch in rec.get("chunks", []) if not ch["ok"]]
check(f"one chunk recorded failed, the smallest there is round the bad point: "
      f"{len(bad)} failed of {len(rec.get('chunks', []))}",
      len(bad) == 1 and inside(bad[0], BAD["lat"], BAD["lon"])
      and (bad[0]["north"] - bad[0]["south"]) / 2 < osmmap.CHUNK_MIN
      and rec.get("failed") == 1)
check(f"and it says why: {bad[0]['error'] if bad else ''}",
      bad and "504" in bad[0]["error"])
check("the chunks are numbered from 1 in the order they were asked",
      [ch["n"] for ch in rec["chunks"]] == list(range(1, len(rec["chunks"]) + 1)))
check("each answered chunk says how many it found, and the fetch its total",
      sum(ch["count"] for ch in rec["chunks"]) == 2 and rec.get("found") == 2
      and rec.get("kind") == "coast" and rec.get("label") == "coastline")
asked = len(QUERIES)
check("a second look reads it off disk, failed chunk and all, sending nothing",
      len(osmmap.coastline(box)) == 2 and len(QUERIES) == asked)

small = osmmap.Bbox(47.5, 47.0, 10.0, 10.5)
try:
    osmmap.coastline(small)
    check("a fetch where no chunk answered is refused", False)
except osmmap.OsmError as e:
    check(f"a fetch where no chunk answered is refused: {e}", "no Overpass server" in str(e))
check("and nothing of it is kept", osmmap.fetches_for(small) == [])

# ---------------------------------------------------------------------------
print("\n2) the failed chunk fetched again")
n = bad[0]["n"]
r = osmmap.refetch("coast", rec["key"], n)
check("still failing, it stays failed and nothing is lost",
      not r["chunks"][n - 1]["ok"] and r["added"] == 0 and r["found"] == 2)
BAD["on"] = False
asked = len(QUERIES)
r = osmmap.refetch("coast", rec["key"], n)
check("answered now: one query, for that chunk's own box",
      len(QUERIES) == asked + 1
      and QUERIES[-1][:4] == (bad[0]["south"], bad[0]["west"], bad[0]["north"], bad[0]["east"]))
check(f"the chunk is ok, and what it found is merged: {r['added']} added",
      r["chunks"][n - 1]["ok"] and r["chunks"][n - 1]["count"] == 1 and r["added"] == 1
      and r["found"] == 3 and r["failed"] == 0 and r["chunk"] == n)
asked = len(QUERIES)
check("the next look at the coastline has all three, and sends nothing",
      len(osmmap.coastline(box)) == 3 and len(QUERIES) == asked)
check("the record on disk says so too",
      osmmap.fetches_for(box)[0]["failed"] == 0)
for bad_n in (0, 999, "x"):
    try:
        osmmap.refetch("coast", rec["key"], bad_n)
        check(f"chunk {bad_n!r} is refused", False)
    except osmmap.OsmError as e:
        check(f"chunk {bad_n!r} is refused: {e}", "no chunk" in str(e))
try:
    osmmap.refetch("coast", "0000000000000000", 1)
    check("a fetch no longer kept is refused", False)
except osmmap.OsmError as e:
    check(f"a fetch no longer kept is refused: {e}", "no longer kept" in str(e))

# ---------------------------------------------------------------------------
print("\n3) the water, the rivers and the historic sites")
BAD["on"] = True
wat = osmmap.water(box, ["lake"])
riv = mapgen._osm_features(box, "major")
his = osmsites.fetch(box, ["historic=castle"])
check("each keeps what answered: one lake, one river, one castle",
      len(wat) == 1 and list(riv["rivers"]) == ["21"]
      and [e["name"] for e in his["historic=castle"]] == ["Plain"])
recs = {r["kind"]: r for r in osmmap.fetches_for(box)}
check(f"each is recorded with one failed chunk: {sorted(recs)}",
      set(recs) == {"coast", "polygons", "features", "historic"}
      and all(recs[k]["failed"] == 1 for k in ("polygons", "features", "historic"))
      and recs["polygons"]["label"] == "water")
BAD["on"] = False
for kind in ("polygons", "features", "historic"):
    rk = recs[kind]
    nn = next(ch["n"] for ch in rk["chunks"] if not ch["ok"])
    r = osmmap.refetch(kind, rk["key"], nn)
    check(f"{kind}: the failed chunk fetched again merges one more", r["added"] == 1)
asked = len(QUERIES)
check("and each reads back whole with nothing sent",
      len(osmmap.water(box, ["lake"])) == 2
      and sorted(mapgen._osm_features(box, "major")["rivers"]) == ["20", "21"]
      and sorted(e["name"] for e in osmsites.fetch(box, ["historic=castle"])["historic=castle"])
      == ["Hidden", "Plain"] and len(QUERIES) == asked)

# ---------------------------------------------------------------------------
print("\n4) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

W, H = 60, 40
med2 = Path(_tmp.mkdtemp(prefix="ut_osmchunks_m2_"))
root = med2 / "mods" / "Chunky"
base = root / "data" / campmap.BASE_REL
base.mkdir(parents=True, exist_ok=True)
(root / "data" / "text").mkdir(parents=True, exist_ok=True)
with open(root / "data" / campmap.REGION_NAMES_REL, "w", encoding="utf-16", newline="") as fh:
    fh.write("{A_Province}Aland\r\n{Atown}Ayton\r\n")
(base / "descr_terrain.txt").write_text(
    "dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
    "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n" % (W, H),
    encoding="latin-1")
(base / "descr_regions.txt").write_bytes((
    "A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
    "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n").encode("latin-1"))


def tga(path, w, h, rgb):
    info = TgaInfo(image_type=10, width=w, height=h, depth=32, descriptor=0x08)
    im = Image.new("RGBA", (w, h), rgb + (255,))
    im.putpixel((5, 5), (0, 0, 0, 255))
    path.write_bytes(encode(im.convert(info.mode), info))


tga(base / "map_regions.tga", W, H, (10, 20, 30))
for name in ("map_heights", "map_ground_types", "map_climates"):
    tga(base / f"{name}.tga", 2 * W + 1, 2 * H + 1, (90, 90, 90))
tga(base / "map_features.tga", W, H, (0, 0, 0))
(base / osmmap.BBOX_FILE).write_text(osmmap.bbox_text(box, W, H), encoding="utf-8")

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def post(path, b):
    req = urllib.request.Request(BASE + path, data=json.dumps(b).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


BAD["on"] = True
r = post("/api/osm/historic", {"mod": "Chunky", "tags": ["historic=fort"]})
asked = len(QUERIES)
st = get("/api/osm/chunks?mod=Chunky")
fs = st.get("fetches") or []
check("GET /api/osm/chunks lists this box's fetches, newest first, sending nothing",
      len(fs) == 5 and fs[0]["kind"] == "historic" and fs[0]["failed"] == 1
      and len(QUERIES) == asked)
BAD["on"] = False
nn = next(ch["n"] for ch in fs[0]["chunks"] if not ch["ok"])
r = post("/api/osm/refetch", {"kind": "historic", "key": fs[0]["key"], "n": nn})
check("POST /api/osm/refetch asks that chunk alone and gives the record back",
      r.get("chunks", [{}] * nn)[nn - 1].get("ok") and r.get("failed") == 0
      and len(QUERIES) == asked + 1)
r = post("/api/osm/refetch", {"kind": "historic", "key": fs[0]["key"], "n": 999})
check("a chunk that does not exist is an error", "no chunk" in (r.get("error") or ""))
config.save_settings(osm_enabled=False)
r = post("/api/osm/refetch", {"kind": "historic", "key": fs[0]["key"], "n": nn})
check("switched off, nothing is asked", "off" in (r.get("error") or "")
      and len(QUERIES) == asked + 1)
httpd.shutdown()
fake.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
