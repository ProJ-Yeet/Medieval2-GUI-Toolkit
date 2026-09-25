"""Phase 87b: the backdrop's styles, the historical map, and a picture of the box.

    python -m tests.test_osmstyles

Nothing here touches the network: a small HTTP server on this machine plays
every tile server and the elevation tiles, and counts what it is asked.

1. Every style is listed with its servers, its deepest zoom and its credit;
   off, none is fetched.
2. A style's tile comes from its own servers and is cached apart from the
   standard style's; the second ask sends nothing. ``{s}`` is tried as a, b
   and c.
3. The historical map: the year goes into ``{date}``, each year is cached
   apart, and a year that is not one is refused.
4. The relief is drawn from the elevation tiles: grey on land, blue at sea,
   one scale for every tile (Mylae stretched each tile to its own range).
5. A picture of the box: the map's shape, every pixel from the slippy tile its
   point stands in (a turned box turned with it), the credit in the corner;
   and the SVG in the map's frame.
"""
import io
import json
import math
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import config, osmmap  # noqa: E402

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

ASKED = []


def png(img):
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def terrarium(fn):
    """A Terrarium tile whose pixel (i, j) holds fn(i, j) metres."""
    im = Image.new("RGB", (256, 256))
    px = im.load()
    for j in range(256):
        for i in range(256):
            v = fn(i, j) + 32768
            px[i, j] = (int(v // 256), int(v % 256), int((v % 1) * 256))
    return png(im)


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        ASKED.append(self.path)
        parts = u.path.strip("/").split("/")
        kind = parts[0]
        if kind == "down":
            return self.send_error(503)
        if kind == "elev":
            # west half of every tile sea at -2000 m, east half land at 1500 m
            raw = terrarium(lambda i, j: -2000.0 if i < 128 else 1500.0)
        else:
            z, x, y = (int(v.split(".")[0]) for v in parts[-3:])
            colour = {"topo": (10, 200, 10), "hot": (200, 10, 10), "ohm": (90, 60, 30)}.get(
                kind, (x % 256, y % 256, 0))
            raw = png(Image.new("RGB", (256, 256), colour))
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
FAKE = f"http://127.0.0.1:{fake.server_address[1]}"
threading.Thread(target=fake.serve_forever, daemon=True).start()
config.save_settings(osm_tiles=[FAKE + "/geo/{z}/{x}/{y}.png"],
                     osm_tiles_topo=[FAKE + "/down/{z}/{x}/{y}", FAKE + "/topo/{s}/{z}/{x}/{y}"],
                     osm_tiles_hot=[FAKE + "/hot/{z}/{x}/{y}"],
                     osm_tiles_ohm=[FAKE + "/ohm/{z}/{x}/{y}?date={date}"],
                     osm_elevation=[FAKE + "/elev/{z}/{x}/{y}"])

print("\n== 1) the styles, and the switch ==")
st = osmmap.settings()["styles"]
check("five styles: the standard map, OpenTopoMap, Humanitarian, relief, historical",
      set(st) == {"osm", "topo", "hot", "relief", "ohm"})
check("each with its servers, its deepest zoom and its credit",
      st["topo"]["servers"][-1].endswith("/topo/{s}/{z}/{x}/{y}") and st["topo"]["max_zoom"] == 17
      and "OpenTopoMap" in st["topo"]["credit"] and st["relief"]["servers"] == [])
check("his year slider and his twelve era buttons",
      osmmap.settings()["ohm_years"] == [500, 1600] and len(osmmap.settings()["ohm_eras"]) == 12)
for style in ("topo", "relief", "ohm"):
    try:
        osmmap.tile(3, 1, 1, style, 1066)
        check(f"off, a {style} tile is refused", False)
    except osmmap.OsmOff:
        check(f"off, a {style} tile is refused", True)
check("and nothing was asked", not ASKED)

config.save_settings(osm_enabled=True)
print("\n== 2) a style's own servers, and its own cache ==")
t = osmmap.tile(4, 8, 5, "topo")
check("a server that fails is passed over, and {s} is tried as a, b, c",
      Image.open(io.BytesIO(t)).getpixel((5, 5)) == (10, 200, 10)
      and any("/down/" in a for a in ASKED) and any("/topo/a/4/8/5" in a for a in ASKED))
n = len(ASKED)
osmmap.tile(4, 8, 5, "topo")
check("the second ask sends nothing", len(ASKED) == n)
g = osmmap.tile(4, 8, 5)
check("the standard style is fetched apart and kept in Phase 25's folder",
      Image.open(io.BytesIO(g)).getpixel((5, 5)) == (8, 5, 0)
      and (cfg / "cache" / "osm_tiles" / "4" / "8" / "5.png").is_file()
      and (cfg / "cache" / "osm_tiles_topo" / "4" / "8" / "5.png").is_file())
for bad, why in (((4, 8, 5, "satellite"), "a style that does not exist"),
                 ((4, 99, 5, "hot"), "a tile that does not exist")):
    try:
        osmmap.tile(*bad)
        check(f"{why} is refused", False)
    except osmmap.OsmError:
        check(f"{why} is refused", True)

print("\n== 3) the historical map ==")
osmmap.tile(5, 16, 11, "ohm", 1066)
check("the year goes in as the date", any("/ohm/5/16/11?date=1066-01-01" in a for a in ASKED))
n = len(ASKED)
osmmap.tile(5, 16, 11, "ohm", 1066)
osmmap.tile(5, 16, 11, "ohm", 1200)
check("each year is kept apart: 1066 again sends nothing, 1200 is asked",
      len(ASKED) == n + 1 and ASKED[-1].endswith("date=1200-01-01")
      and (cfg / "cache" / "osm_tiles_ohm" / "1066" / "5" / "16" / "11.png").is_file())
osmmap.tile(5, 16, 11, "ohm")
check("no year is his default, 1200: already kept, so nothing is sent", len(ASKED) == n + 1)
try:
    osmmap.tile(5, 16, 11, "ohm", "soon")
    check("a year that is not a number is refused", False)
except osmmap.OsmError:
    check("a year that is not a number is refused", True)

print("\n== 4) the relief ==")
r1 = Image.open(io.BytesIO(osmmap.tile(6, 30, 20, "relief"))).convert("RGB")
r2 = Image.open(io.BytesIO(osmmap.tile(6, 31, 22, "relief"))).convert("RGB")
sea, land = r1.getpixel((60, 100)), r1.getpixel((200, 100))
check(f"land is grey {land}, the sea blue {sea}",
      land[0] == land[1] == land[2] and sea[2] > sea[0] + 40)
check("one scale for every tile: the same ground is the same grey on another tile",
      r2.getpixel((200, 100)) == land and r2.getpixel((60, 100)) == sea)
check("and it is drawn from the elevation tiles, kept apart",
      any(a.startswith("/elev/6/30/20") for a in ASKED)
      and (cfg / "cache" / "osm_tiles_relief" / "6" / "30" / "20.png").is_file())

print("\n== 5) a picture of the box ==")
W, H = 80, 60
for label, box in (("straight", osmmap.fit(osmmap.Bbox(50, 40, 0, 15), W, H)),
                   ("turned 25°", osmmap.fit(osmmap.Bbox(50, 40, 0, 15, 25.0), W, H))):
    img = osmmap.picture(box, W, H, "osm", px=640)
    check(f"{label}: the map's shape, 640 wide", img.size == (640, 480))
    proj = osmmap.Projection(box, W, H)
    bad = []
    for u, v in ((20, 30), (320, 240), (600, 400), (100, 420), (500, 60)):
        fx, fy = (u + 0.5) * W / 640 - 0.5, (v + 0.5) * H / 480 - 0.5
        lat, lon = proj.to_geo(fx, fy)
        n = 2 ** img.info["zoom"]
        gx = (lon + 180) / 360 * n * 256
        gy = (1 - osmmap.merc(lat) / math.pi) / 2 * n * 256
        if img.getpixel((u, v))[:2] != (int(gx // 256) % 256, int(gy // 256) % 256):
            # a pixel on a tile's edge blends the two; one step away must not
            near = [img.getpixel((u + du, v + dv))[:2] for du in (-2, 2) for dv in (-2, 2)]
            bad.append(((u, v), img.getpixel((u, v)), near))
    check(f"{label}: every probed pixel comes from the tile its point stands in", not bad)
    if bad:
        print("     ", bad[:2])
    c = img.getpixel((630, 474))
    check(f"{label}: the credit is in the corner", c != img.getpixel((320, 240)))
svg = osmmap.picture_svg(img, box, W, H, "osm")
check("the SVG is in the map's frame, the picture inside, the box and turn named",
      'viewBox="0 0 80 60"' in svg and "data:image/png;base64," in svg
      and "turned 25.00" in svg and "OpenStreetMap contributors" in svg)
turned_ohm = osmmap.picture(osmmap.Bbox(50, 40, 0, 15), W, H, "ohm", 1066, px=256)
check("a picture of the historical map asks for its year",
      turned_ohm.size[0] == 256 and any("date=1066-01-01" in a for a in ASKED))

fake.shutdown()
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
