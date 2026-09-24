"""Phase 25: the real world behind a campaign map, opt-in.

    python -m tests.test_osmmap

Nothing here touches the network: a small HTTP server on this machine plays
the tile server, Overpass and Nominatim, and counts what it is asked.

1. Off by default: every route that would send something refuses, and the
   fake servers are asked nothing.
2. The box: a bbox_coords.txt read, bad boxes refused, kept per map, exported
   in the shape Mylae's editor reads; the projection and its inverse.
3. The coastline on a 60x40 map: its line, the water side found from the way's
   direction (land on the left), the land tiles on that side offered to become
   sea and the tiles already sea left alone; a way drawn the other way round
   puts the water on the other side; a coastline with a gap is caught.
4. Into the paint session: the water side made sea as one stroke on regions,
   heights and ground types, settlement and port pixels spared, undone byte for
   byte; a leaking coastline refused and nothing painted.
5. A place: searched inside the box with its tile, its boundary painted onto a
   region on land only, and the fallback that asks Overpass which boundary a
   point is in.
6. The tile proxy caches: the second ask of a tile sends nothing.
7. The routes.
"""
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import campaint, campmap, config, osmmap  # noqa: E402
from unittransfer.maptga import TgaInfo, encode  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

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
# the fake OpenStreetMap

N, S, WEST, EAST = 50.0, 40.0, 0.0, 15.0
COAST_LAT = 44.0
ASKED = {"tiles": 0, "overpass": 0, "search": 0, "lookup": 0}
#: what the fake Overpass answers for a coastline query; swapped per test
COAST = {"ways": []}
PNG = b""


def way(i, pts):
    return {"type": "way", "id": i, "geometry": [{"lat": a, "lon": o} for a, o in pts]}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        raw = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path.startswith("/tiles/"):
            ASKED["tiles"] += 1
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG)))
            self.end_headers()
            self.wfile.write(PNG)
        elif u.path == "/search":
            ASKED["search"] += 1
            self._json([{"lat": "47.0", "lon": "7.5", "name": "Midtown",
                         "display_name": "Midtown, Somewhere", "osm_type": "relation",
                         "osm_id": 777, "addresstype": "city",
                         "extratags": {"admin_level": "8"}},
                        {"lat": "60.0", "lon": "7.5", "name": "Farnorth",
                         "osm_type": "node", "osm_id": 5}])
        elif u.path == "/lookup":
            ASKED["lookup"] += 1
            # a square from 46 to 48 north and 6 to 9 east, with a hole
            self._json([{"geojson": {"type": "Polygon", "coordinates": [
                [[6, 46], [9, 46], [9, 48], [6, 48], [6, 46]],
                [[7, 46.8], [7.4, 46.8], [7.4, 47.2], [7, 47.2], [7, 46.8]]]}}])
        else:
            self.send_error(404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
        ASKED["overpass"] += 1
        q = urllib.parse.unquote(body)
        if "is_in" in q:
            self._json({"elements": [
                {"type": "area", "id": 3600000000 + 777,
                 "tags": {"boundary": "administrative", "admin_level": "8"}},
                {"type": "area", "id": 3600000000 + 12,
                 "tags": {"boundary": "administrative", "admin_level": "2"}}]})
        else:
            self._json({"elements": COAST["ways"]})


fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
FAKE = f"http://127.0.0.1:{fake.server_address[1]}"
threading.Thread(target=fake.serve_forever, daemon=True).start()
buf = __import__("io").BytesIO()
Image.new("RGB", (256, 256), (200, 220, 240)).save(buf, "PNG")
PNG = buf.getvalue()
config.save_settings(osm_tiles=[FAKE + "/tiles/{z}/{x}/{y}.png"],
                     osm_overpass=[FAKE + "/interpreter"], osm_nominatim=FAKE)

# ---------------------------------------------------------------------------
# a 60x40 map: all land but the bottom three rows, two provinces, a settlement
# and a port, both south of where the real coast will run

W, H = 60, 40
A, B, SEA = (10, 20, 30), (40, 50, 60), (0, 90, 200)
SETTLE, PORT = (5, 30), (40, 34)


def region_px(x, y):
    if y >= H - 3:
        return SEA
    if (x, y) == SETTLE:
        return (0, 0, 0)
    if (x, y) == PORT:
        return (255, 255, 255)
    return A if x < 30 else B


def img(w, h, fn):
    im = Image.new("RGBA", (w, h))
    im.putdata([fn(x, y) + (255,) for y in range(h) for x in range(w)])
    return im


def tga(path, im, depth=32, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=im.width, height=im.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(im.convert(info.mode), info))


def build(root: Path) -> Path:
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (root / "data" / "text").mkdir(parents=True, exist_ok=True)
    with open(root / "data" / campmap.REGION_NAMES_REL, "w", encoding="utf-16",
              newline="") as fh:
        fh.write("{A_Province}Aland\r\n{Atown}Ayton\r\n{B_Province}Bland\r\n{Btown}Beeton\r\n")
    (base / "descr_terrain.txt").write_text(
        "dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
        "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n"
        "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
        "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
        % (W, H), encoding="latin-1")
    (base / "descr_regions.txt").write_bytes((
        "A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
        "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n\r\n"
        "B_Province\r\n\tBtown\r\n\tslave\r\n\tbrigands\r\n\t40 50 60\r\n"
        "\tsilver\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n").encode("latin-1"))
    tga(base / "map_regions.tga", img(W, H, region_px))
    sea_row = 2 * (H - 3)
    tga(base / "map_heights.tga", img(2 * W + 1, 2 * H + 1,
        lambda x, y: (0, 0, 200) if y >= sea_row else (90, 90, 90)))
    tga(base / "map_ground_types.tga", img(2 * W + 1, 2 * H + 1,
        lambda x, y: (128, 0, 0) if y >= sea_row else (96, 160, 64)))
    tga(base / "map_climates.tga", img(2 * W + 1, 2 * H + 1, lambda x, y: (200, 100, 50)))
    tga(base / "map_features.tga", img(W, H, lambda x, y: (0, 0, 0)))
    tga(base / "map_fog.tga", img(2 * W + 1, 2 * H + 1, lambda x, y: (255, 255, 255)),
        depth=24, image_type=10, desc=0x00)
    tga(base / "map_trade_routes.tga", img(W, H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    tga(base / "map_roughness.tga", img(2 * W, 2 * H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    tga(base / "water_surface.tga", img(2 * W + 1, 2 * H + 1, lambda x, y: (0, 0, 120)),
        depth=24, image_type=2, desc=0x00)
    return base


med2 = Path(_tmp.mkdtemp(prefix="ut_osm_"))
root = med2 / "mods" / "Coasty"
base = build(root)
mod = Mod(root)
cm = campmap.CampaignMap(mod)


def layers():
    return {p.name: p.read_bytes() for p in base.iterdir() if p.suffix == ".tga"}


# ---------------------------------------------------------------------------
print("1) off by default")
check("the switch is off in fresh settings", not osmmap.settings()["enabled"])
box = osmmap.Bbox(N, S, WEST, EAST)
for what, fn in (("a tile", lambda: osmmap.tile(3, 1, 1)),
                 ("the coastline", lambda: osmmap.coastline(box)),
                 ("a search", lambda: osmmap.search(box, osmmap.Projection(box, W, H), "x"))):
    try:
        fn()
        check(f"{what} is refused while it is off", False)
    except osmmap.OsmOff:
        check(f"{what} is refused while it is off", True)
check("and the fake servers were asked nothing at all", sum(ASKED.values()) == 0)
check("the servers it would use are listed, and are this test's",
      osmmap.settings()["overpass"] == [FAKE + "/interpreter"]
      and osmmap.settings()["nominatim"] == FAKE)

# ---------------------------------------------------------------------------
print("\n2) the box")
text = ("# BboxLayerGenerator - Selected Area Coordinates\n\nnorth=50.000000\n"
        "south=40.000000\nwest=0.000000\neast=15.000000\n\nmap_width=60\n"
        "map_height=40\nheightmap_width=121\nheightmap_height=81\n")
b = osmmap.parse_bbox(text)
check("a bbox_coords.txt from Mylae's New Map Editor reads",
      (b.north, b.south, b.west, b.east) == (N, S, WEST, EAST))
for bad, why in (({"north": 40, "south": 50, "west": 0, "east": 1}, "above south"),
                 ({"north": 89, "south": 50, "west": 0, "east": 1}, "projection"),
                 ({"north": 50, "south": 40, "west": 5, "east": 1}, "east of west"),
                 ({"north": 50}, "needs north")):
    try:
        osmmap.parse_bbox(bad)
        check(f"a bad box is refused ({why})", False)
    except osmmap.OsmError as e:
        check(f"a bad box is refused ({why})", why in str(e))
check("no box is kept for a fresh map", osmmap.box_for(cm) == (None, ""))
(base / osmmap.BBOX_FILE).write_text(text, encoding="utf-8")
got, where = osmmap.box_for(cm)
check("a bbox_coords.txt beside the map is read when none is kept",
      where == "file" and got == b)
osmmap.keep_box(cm, osmmap.Bbox(51, 41, 1, 16))
check("a kept box wins over the file",
      osmmap.box_for(cm) == (osmmap.Bbox(51, 41, 1, 16), "kept"))
osmmap.keep_box(cm, None)
check("and clearing it falls back to the file", osmmap.box_for(cm)[1] == "file")
(base / osmmap.BBOX_FILE).unlink()
osmmap.keep_box(cm, b)
check("the kept box is keyed by mod and map folder",
      json.loads((cfg / "osm_boxes.json").read_text())["Coasty"]
      == {campmap.BASE_REL: b.payload()})
exported = osmmap.bbox_text(b, W, H)
check("exported in the shape Mylae's editor reads, sizes included",
      osmmap.parse_bbox(exported) == b and "heightmap_width=121" in exported)
proj = osmmap.Projection(b, W, H)
check("the west edge is tile 0 and the east edge tile W-1",
      proj.to_tile(45, 0)[0] == 0 and abs(proj.to_tile(45, 15)[0] - (W - 1)) < 1e-9)
check("north is row 0 and south row H-1",
      abs(proj.to_tile(50, 3)[1]) < 1e-9 and abs(proj.to_tile(40, 3)[1] - (H - 1)) < 1e-9)
check("and the rows are Mercator: stretched toward the pole, so the middle "
      "latitude falls below the middle row",
      proj.to_tile(45, 3)[1] > (H - 1) / 2)
lat, lon = proj.to_geo(*proj.to_tile(43.21, 7.65))
check("to_geo undoes to_tile", abs(lat - 43.21) < 1e-9 and abs(lon - 7.65) < 1e-9)
check("the backdrop's zoom follows the view: bigger tiles on screen, deeper zoom",
      osmmap.slippy_zoom(proj, 16) > osmmap.slippy_zoom(proj, 2))

# ---------------------------------------------------------------------------
print("\n3) the coastline on the map")
config.save_settings(osm_enabled=True)
# drawn west to east: land to the left (north), water to the right (south)
COAST["ways"] = [way(1, [(COAST_LAT, -1.0), (COAST_LAT, 7.0)]),
                 way(2, [(COAST_LAT, 7.0), (COAST_LAT, 16.0)])]
ways = osmmap.coastline(b)
check(f"fetched: {len(ways)} ways, each as drawn", len(ways) == 2
      and ways[0][0] == (COAST_LAT, -1.0))
asked = ASKED["overpass"]
osmmap.coastline(b)
check("a second look at the same box asks Overpass nothing", ASKED["overpass"] == asked)
row = round(proj.to_tile(COAST_LAT, 5)[1])
c = osmmap.analyse(ways, proj, cm.sea)
line_rows = {i // W for i, v in enumerate(c.line) if v}
check(f"the line is one row across the whole map (row {row})",
      line_rows == {row} and sum(c.line) == W)
water_rows = {i // W for i, v in enumerate(c.water) if v}
check("the water side is south of it, every row down to the bottom",
      water_rows == set(range(row + 1, H)))
check("the land tiles on the water side are offered, the sea tiles are not",
      len(c.to_sea) == W * (H - 3 - row - 1)
      and all(y < H - 3 for _, y in c.to_sea))
check("no leak on a whole coastline", c.leak == 0 and not c.leaks)
back = osmmap.analyse([list(reversed(w)) for w in ways], proj, cm.sea)
check("drawn the other way round, the water is north and the sea tiles south "
      "are reported as sea on the land side",
      {i // W for i, v in enumerate(back.water) if v} == set(range(0, row))
      and back.land_side_sea == 3 * W)
gap = osmmap.analyse([ways[0][:1] + [(COAST_LAT, 3.0)]], proj, cm.sea)
check(f"a coastline that stops half way leaks round its end and says so "
      f"({gap.leak} of {gap.seeds} land seeds reached)", gap.leaks)
none = osmmap.analyse([], proj, cm.sea)
check("no coastline at all offers nothing", not none.to_sea and not none.leaks)

# ---------------------------------------------------------------------------
print("\n4) into the paint session")
before = layers()
sess = campaint.PaintSession(mod, cm)
out = osmmap.paint_coast(sess)
check(f"one stroke: {out.get('label')}, {out['tiles']} tiles", out["ok"] and out["tiles"] == len(c.to_sea) - 2)
check("the settlement and the port were spared", out["protected"] == 2)
check("regions, heights and ground types together, as the water brush does",
      set(out["changed"]) == {"regions", "heights", "ground_types"})
check("and now the map reads those tiles as sea",
      all(cm.sea[y * W + x] for x, y in c.to_sea if (x, y) not in (SETTLE, PORT)))
check("the sea depth is the map's own, measured, not a guessed blue",
      out["changed"]["heights"]["rgb"] == (0 << 16) | (0 << 8) | 200)
again = osmmap.paint_coast(sess)
check("a second press changes nothing", again["tiles"] == 0)
campaint.undo_stroke(sess)
check("one undo puts every layer back", not sess.unsaved)
check("nothing was written to disk", layers() == before)
COAST["ways"] = [way(3, [(COAST_LAT, -1.0), (COAST_LAT, 3.0)])]
osmmap.keep_box(cm, osmmap.Bbox(50.0001, 40, 0, 15))     # a new box, a new fetch
try:
    osmmap.paint_coast(sess)
    check("a leaking coastline is refused", False)
except osmmap.OsmError as e:
    check("a leaking coastline is refused, saying why", "gap" in str(e))
check("and nothing was painted", not sess.undo)
osmmap.keep_box(cm, b)
COAST["ways"] = [way(1, [(COAST_LAT, -1.0), (COAST_LAT, 7.0)]),
                 way(2, [(COAST_LAT, 7.0), (COAST_LAT, 16.0)])]

# ---------------------------------------------------------------------------
print("\n5) a place and its boundary")
res = osmmap.search(b, proj, "Midtown")
check("a search inside the box finds the place, on its tile",
      res[0]["name"] == "Midtown" and res[0]["on_map"]
      and (res[0]["x"], res[0]["y"]) == tuple(round(v) for v in proj.to_tile(47, 7.5)))
check("and a place outside the map is said to be", not res[1]["on_map"])
check("a boundary relation is marked as one", res[0]["boundary"] and not res[1]["boundary"])
geo = osmmap.boundary(47, 7.5, "relation", 777)
tiles = set(osmmap.boundary_tiles(geo, proj))
x0, y0 = proj.to_tile(48, 6)
x1, y1 = proj.to_tile(46, 9)
hx0, hy0 = proj.to_tile(47.2, 7)
hx1, hy1 = proj.to_tile(46.8, 7.4)


def strictly(ax, ay, bx, by):
    return {(x, y) for x in range(int(ax) + 1, int(bx) + 1)
            for y in range(int(ay) + 1, int(by) + 1) if ax < x < bx and ay < y < by}


square, hole = strictly(x0, y0, x1, y1), strictly(hx0, hy0, hx1, hy1)
near_hole = {(x + dx, y + dy) for x, y in hole for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
check(f"its tiles are the square ({len(tiles)} of them)",
      square - near_hole <= tiles and all(x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1
                                          for x, y in tiles))
check(f"with the hole left out ({len(hole)} tiles)", hole and not (hole & tiles))
before_lookups = ASKED["lookup"]
out = osmmap.paint_boundary(sess, {"lat": 47, "lon": 7.5, "osm_type": "relation",
                                   "osm_id": 777, "region": "B_Province",
                                   "name": "Midtown"})
check(f"painted onto a region as one stroke: {out.get('label')}",
      out["ok"] and set(out["changed"]) == {"regions"}
      and out["changed"]["regions"]["rgb"] == (40 << 16) | (50 << 8) | 60)
check("only on the tiles that were not that region already",
      out["tiles"] == sum(1 for x, y in tiles if x < 30))
campaint.undo_stroke(sess)
asked = ASKED["overpass"]
geo2 = osmmap.boundary(47, 7.5, "node", 5)
check("a place that is not a boundary asks Overpass which one it is in, and takes "
      "the smallest", ASKED["overpass"] == asked + 1 and geo2 == geo
      and ASKED["lookup"] == before_lookups + 2)
try:
    osmmap.paint_boundary(sess, {"lat": 47, "lon": 7.5, "osm_type": "relation",
                                 "osm_id": 777, "region": ""})
    check("a boundary with no region is refused", False)
except osmmap.OsmError:
    check("a boundary with no region is refused", True)

# ---------------------------------------------------------------------------
print("\n6) the tile proxy")
n = ASKED["tiles"]
t1 = osmmap.tile(5, 16, 11)
t2 = osmmap.tile(5, 16, 11)
check("a tile comes back as the server sent it", t1 == PNG)
check("and the second ask is off the disk", t2 == PNG and ASKED["tiles"] == n + 1)
try:
    osmmap.tile(5, 99, 0)
    check("a tile number past the edge of the world is refused", False)
except osmmap.OsmError:
    check("a tile number past the edge of the world is refused", True)

# ---------------------------------------------------------------------------
print("\n7) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path, raw=False):
    try:
        with urllib.request.urlopen(BASE + path, timeout=120) as r:
            data = r.read()
            return data if raw else json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code


def post(path, b):
    req = urllib.request.Request(BASE + path, data=json.dumps(b).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))



st = get("/api/osm?mod=Coasty")
check("GET /api/osm: on, the servers, the box and its file",
      st.get("settings", {}).get("enabled") and st.get("box") == b.payload()
      and st.get("box_from") == "kept" and "north=50" in st.get("file", ""))
r = post("/api/osm/box", {"mod": "Coasty", "text": text.replace("north=50", "north=52")})
check("POST /api/osm/box keeps an imported file", r.get("box", {}).get("north") == 52)
r = post("/api/osm/box", {"mod": "Coasty", "box": {"north": 1, "south": 2, "west": 0, "east": 1}})
check("and refuses a bad box", "above south" in (r.get("error") or ""))
post("/api/osm/box", {"mod": "Coasty", "box": b.payload()})
r = post("/api/osm/coast", {"mod": "Coasty"})
check("POST /api/osm/coast reports without painting",
      r.get("coast", {}).get("to_sea") == len(c.to_sea) and layers() == before)
r = get("/api/osm/search?mod=Coasty&q=Midtown")
check("GET /api/osm/search", r.get("results", [{}])[0].get("name") == "Midtown")
check("GET /api/osm/tile serves a tile", get("/api/osm/tile/5/16/11", raw=True) == PNG)
r = post("/api/map/osm_coast", {"mod": "Coasty"})
check("POST /api/map/osm_coast paints into the session",
      r.get("tiles") == len(c.to_sea) - 2 and "heights" in r.get("state", {}).get("dirty", []))
r = post("/api/map/paint_undo", {"mod": "Coasty"})
check("and the paint tool's own undo takes it back", r.get("state", {}).get("undo") == 0)
config.save_settings(osm_enabled=False)
check("switched off, a tile not on disk is refused with 403",
      get("/api/osm/tile/4/1/1", raw=True) == 403)
r = get("/api/osm/search?mod=Coasty&q=Midtown")
check("and so is a search", "off" in (r.get("error") or ""))
httpd.shutdown()
fake.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
