"""Phase 87h: the map bundle, a campaign map as one zip in Mylae's layout.

    python -m tests.test_mapbundle

Nothing here touches the network: a small HTTP server on this machine plays
Overpass and the tile server, and counts what it is asked.

1. With no box: every layer on disk and reference/map_regions.txt, and the
   notes say why there is no bbox_coords.txt.
2. With a box and a historic fetch kept: his names (his six layers at the top
   under the game's names, reference/ beside them), each TGA the file on disk
   byte for byte and the size the map's grid says, bbox_coords.txt with the
   rotation, map_regions.txt in his columns, historic_features.txt and one
   transparent PNG a tag; and making it asked nothing of anybody.
3. A reference picture, asked for, from the tile server.
4. The route.
"""
import io
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import campmap, config, mapbundle, osmmap, osmsites  # noqa: E402
from unittransfer.maptga import TgaInfo, encode, read  # noqa: E402
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

ASKED = {"overpass": 0, "tiles": 0}
CASTLE = {"type": "node", "id": 1, "lat": 47.0, "lon": 7.5,
          "tags": {"historic": "castle", "name": "Bodiam"}}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, raw, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        ASKED["tiles"] += 1
        buf = io.BytesIO()
        Image.new("RGB", (256, 256), (200, 220, 240)).save(buf, "PNG")
        self._send(buf.getvalue(), "image/png")

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        ASKED["overpass"] += 1
        self._send(json.dumps({"elements": [CASTLE]}).encode(), "application/json")


fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
FAKE = f"http://127.0.0.1:{fake.server_address[1]}"
threading.Thread(target=fake.serve_forever, daemon=True).start()
config.save_settings(osm_tiles=[FAKE + "/tiles/{z}/{x}/{y}.png"],
                     osm_overpass=[FAKE + "/interpreter"], osm_enabled=True)

# ---------------------------------------------------------------------------
# a 60x40 map with all ten layers: two provinces, a city in each, one port

W, H = 60, 40
A, B, SEA = (10, 20, 30), (40, 50, 60), (0, 90, 200)
CITY_A, CITY_B, PORT_B = (5, 30), (45, 20), (40, 36)


def region_px(x, y):
    if y >= H - 3:
        return SEA
    if (x, y) in (CITY_A, CITY_B):
        return (0, 0, 0)
    if (x, y) == PORT_B:
        return (255, 255, 255)
    return A if x < 30 else B


def tga(path, w, h, fn, depth=32, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=w, height=h, depth=depth, descriptor=desc)
    im = Image.new("RGBA", (w, h))
    im.putdata([fn(x, y) + (255,) for y in range(h) for x in range(w)])
    path.write_bytes(encode(im.convert(info.mode), info))


med2 = Path(_tmp.mkdtemp(prefix="ut_bundle_"))
root = med2 / "mods" / "Bundly"
base = root / "data" / campmap.BASE_REL
base.mkdir(parents=True, exist_ok=True)
(root / "data" / "text").mkdir(parents=True, exist_ok=True)
with open(root / "data" / campmap.REGION_NAMES_REL, "w", encoding="utf-16", newline="") as fh:
    fh.write("{A_Province}Aland\r\n{Atown}Ayton\r\n{B_Province}Bland\r\n{Btown}Beeton\r\n")
(base / "descr_terrain.txt").write_text(
    "dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
    "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n" % (W, H),
    encoding="latin-1")
(base / "descr_regions.txt").write_bytes((
    "A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
    "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n\r\n"
    "B_Province\r\n\tBtown\r\n\tslave\r\n\tbrigands\r\n\t40 50 60\r\n"
    "\tsilver\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n").encode("latin-1"))
sea_row = 2 * (H - 3)
tga(base / "map_regions.tga", W, H, region_px)
tga(base / "map_heights.tga", 2 * W + 1, 2 * H + 1,
    lambda x, y: (0, 0, 200) if y >= sea_row else (90, 90, 90))
tga(base / "map_ground_types.tga", 2 * W + 1, 2 * H + 1,
    lambda x, y: (128, 0, 0) if y >= sea_row else (96, 160, 64))
tga(base / "map_climates.tga", 2 * W + 1, 2 * H + 1, lambda x, y: (200, 100, 50))
tga(base / "map_features.tga", W, H, lambda x, y: (0, 0, 0))
tga(base / "map_fog.tga", 2 * W + 1, 2 * H + 1, lambda x, y: (255, 255, 255), depth=24, desc=0)
tga(base / "map_trade_routes.tga", W, H, lambda x, y: (0, 0, 0), depth=24, desc=0)
tga(base / "map_roughness.tga", 2 * W, 2 * H, lambda x, y: (0, 0, 0), depth=24, desc=0)
tga(base / "water_surface.tga", 2 * W + 1, 2 * H + 1, lambda x, y: (0, 0, 120),
    depth=24, image_type=2, desc=0)
tga(base / "map_FE.tga", 300, 200, lambda x, y: (x % 256, y % 256, 0), depth=24, desc=0)

cm = campmap.CampaignMap(Mod(root))
ON_DISK = {ly["file"]: (base / ly["file"]).read_bytes() for ly in campmap.LAYERS}


def unzip(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    return {n: z.read(n) for n in z.namelist()}


# ---------------------------------------------------------------------------
print("1) with no box")
got = mapbundle.build(cm)
zf = unzip(got["data"])
check("every one of the ten layers and reference/map_regions.txt, nothing else",
      set(zf) == set(ON_DISK) | {"reference/map_regions.txt"})
check(f"and the notes say why there is no box: {got['notes']}",
      any("no real-world box" in n for n in got["notes"]))
check("the zip is named for the mod, his name's shape", got["name"] == "Bundly_map_layers.zip")

# ---------------------------------------------------------------------------
print("\n2) with a box and a historic fetch kept")
box = osmmap.Bbox(50.0, 40.0, 0.0, 15.0, 10.0)
osmmap.keep_box(cm, box)
osmsites.fetch(box, ["historic=castle"])
asked = dict(ASKED)
got = mapbundle.build(cm)
zf = unzip(got["data"])
check("making it asked nothing of Overpass or the tile server", ASKED == asked)
HIS = ["map_heights.tga", "map_ground_types.tga", "map_climates.tga",
       "map_regions.tga", "map_features.tga", "map_fog.tga"]
check("his six layers at the top of the zip under the game's names",
      all(n in zf for n in HIS))
check("with the four he does not draw beside them",
      all(n in zf for n in ("map_trade_routes.tga", "map_roughness.tga",
                            "water_surface.tga", "map_FE.tga")))
check("every TGA is the file on disk byte for byte",
      all(zf[n] == ON_DISK[n] for n in ON_DISK))
sizes = {}
for n in ON_DISK:
    p = cfg / "unz" / n
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(zf[n])
    sizes[n] = read(p)[0].size
check("each the size the map's grid says: tile, centre, double",
      sizes["map_regions.tga"] == (W, H) and sizes["map_features.tga"] == (W, H)
      and sizes["map_heights.tga"] == (2 * W + 1, 2 * H + 1)
      and sizes["map_ground_types.tga"] == (2 * W + 1, 2 * H + 1)
      and sizes["map_roughness.tga"] == (2 * W, 2 * H))
bb = zf.get("bbox_coords.txt", b"").decode()
check("bbox_coords.txt at the top, with the rotation, reading back as the box",
      "rotation=10" in bb and osmmap.parse_bbox(bb) == box)
lines = zf["reference/map_regions.txt"].decode().split("\n")
check("map_regions.txt opens with his column line",
      lines[1] == "; province_name  r g b  city_x city_y  port_x port_y")
check(f"a province with a city and no port: {lines[3]!r}",
      lines[3] == f"A_Province  10 20 30  {CITY_A[0]} {CITY_A[1]}  0 0")
check(f"a province with a city and a port: {lines[4]!r}",
      lines[4] == f"B_Province  40 50 60  {CITY_B[0]} {CITY_B[1]}  {PORT_B[0]} {PORT_B[1]}")
proj = osmmap.Projection(box, W, H)
found = osmsites.fetch(box, ["historic=castle"])
check("historic_features.txt is 87f's file for what was fetched",
      zf.get("reference/historic_features.txt", b"").decode()
      == osmsites.features_text(found, proj))
png = Image.open(io.BytesIO(zf.get("reference/historic_castle.png", b"")))
site = osmsites.sites(found, proj)[0]
check("his per-tag PNG: the map's size, the castle a pixel in its colour, the rest clear",
      png.size == (W, H) and png.getpixel((site["x"], site["y"])) == (87, 219, 100, 255)
      and png.getpixel((0, 0))[3] == 0
      and sum(1 for p in png.getdata() if p[3]) == 1)
check("no long dash in either text file",
      all(chr(0x2014) not in zf[n].decode() for n in zf if n.endswith(".txt")))

# ---------------------------------------------------------------------------
print("\n3) a reference picture, asked for")
got = mapbundle.build(cm, picture="osm", picture_px=300)
zf = unzip(got["data"])
name = f"reference/reference_osm_{W}x{H}.png"
pic = Image.open(io.BytesIO(zf.get(name, b"")))
check(f"{name} in the map's shape", pic.size == (300, round(300 * H / W)))
check("and the tile server was asked for it", ASKED["tiles"] > asked["tiles"])

# ---------------------------------------------------------------------------
print("\n4) the route")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


code, head, body = get("/api/osm/bundle?mod=Bundly")
zf = unzip(body) if code == 200 else {}
check("GET /api/osm/bundle gives the zip as an attachment",
      code == 200 and 'filename="Bundly_map_layers.zip"' in head.get("Content-Disposition", "")
      and head.get("X-Bundle-Files") == str(len(zf))
      and zf.get("map_regions.tga") == ON_DISK["map_regions.tga"])
config.save_settings(osm_enabled=False)
code, _, body = get("/api/osm/bundle?mod=Bundly")
check("switched off, a bundle without a picture still comes (it sends nothing)", code == 200)
code, _, body = get("/api/osm/bundle?mod=Bundly&picture=osm&width=300")
check("a picture whose tiles are on disk still comes, sending nothing", code == 200)
code, _, body = get("/api/osm/bundle?mod=Bundly&picture=hot&width=300")
check("one whose tiles would have to be fetched is refused with 403", code == 403)
code, _, _ = get("/api/osm/bundle?mod=Nobody")
check("an unknown mod is a 400", code == 400)
httpd.shutdown()
fake.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
