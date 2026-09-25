"""Phase 87f: historic sites out of OpenStreetMap.

    python -m tests.test_osmsites

Nothing here touches the network: a small HTTP server on this machine plays
Overpass and counts what it is asked.

1. His table: 21 tags in his two groups, each in his colour (checked against
   his ``tagColor`` run in JavaScript, 2026-09-25).
2. Off by default: a fetch is refused and the fake is asked nothing.
3. The fetch: one query a chunk for every tag asked, a node's point, ``out
   center``'s centre, his mean of the geometry, an element under two tags in
   both, one on the corner of four chunks once, a failed chunk split in four,
   and each tag kept on disk so the next fetch asks only for a new one.
4. Onto a map: each site's pixel (his rounding) and the strat's tile (y from
   the bottom); off a turned map, said; ``historic_features.txt`` in his shape.
5. The world picker's form: a box and no map, the sites outside a turned box
   left out.
6. A fake answer's castle becomes a fort on the tile it names, through 22a's
   writer, and reads back from the file.
7. The route, with a mod and with a box.
"""
import json
import math
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
from unittransfer import campmap, campstrat, config, osmmap, osmsites, stratobj  # noqa: E402
from unittransfer.keyblock import write_text  # noqa: E402
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
# the fake Overpass

N, S, WEST, EAST = 50.0, 40.0, 0.0, 15.0
QUERIES = []
FAIL = {"n": 0}


def node(i, lat, lon, **tags):
    return {"type": "node", "id": i, "lat": lat, "lon": lon, "tags": tags}


ELEMENTS = [
    node(1, 47.0, 7.5, historic="castle", castle_type="defensive", name="Bodiam"),
    {"type": "way", "id": 2, "center": {"lat": 44.0, "lon": 3.0},
     "tags": {"historic": "fort", "name:en": "Old Fort"}},
    {"type": "relation", "id": 3, "tags": {"historic": "monastery"},
     "members": [{"type": "way", "geometry": [{"lat": 41.9, "lon": 11.9},
                                              {"lat": 42.1, "lon": 12.1}]}]},
    node(4, 49.9, 14.9, historic="tower", name="Lookout"),
    node(5, 45.0, 5.0, historic="church", name="St Nobody"),
    node(6, 46.0, 6.0, historic="fort", name="Crossroads"),
]


def point(e):
    return osmsites._centre(e)


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
        q = urllib.parse.unquote(body)
        QUERIES.append(q)
        if FAIL["n"] > 0:
            FAIL["n"] -= 1
            self.send_error(504)
            return
        found = {}
        for k, v, s, w, n, e in re.findall(
                r'nwr\["([^"]+)"="([^"]+)"\]\(([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\)', q):
            s, w, n, e = map(float, (s, w, n, e))
            for el in ELEMENTS:
                la, lo = point(el)
                if (el["tags"].get(k) == v and s <= la <= n and w <= lo <= e):
                    found[el["id"]] = el
        raw = json.dumps({"elements": list(found.values())}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
FAKE = f"http://127.0.0.1:{fake.server_address[1]}"
threading.Thread(target=fake.serve_forever, daemon=True).start()
config.save_settings(osm_overpass=[FAKE + "/interpreter"])

box = osmmap.Bbox(N, S, WEST, EAST)
W, H = 60, 40
proj = osmmap.Projection(box, W, H)

# ---------------------------------------------------------------------------
print("1) his table")
tags = osmsites.tags_payload()
check("21 tags: eleven historic=*, ten castle_type=*",
      len(tags) == 21 and sum(t["key"] == "historic" for t in tags) == 11
      and sum(t["key"] == "castle_type" for t in tags) == 10)
check("in his colours: a castle (87,219,100), a castle_type watchtower (219,87,180)",
      osmsites.colour("historic", "castle") == [87, 219, 100]
      and osmsites.colour("castle_type", "watchtower") == [219, 87, 180])
check("a castle suggests a fort, a tower a watchtower, a monastery a settlement",
      osmsites.BY_KEY["historic=castle"][4] == "fort"
      and osmsites.BY_KEY["historic=tower"][4] == "watchtower"
      and osmsites.BY_KEY["historic=monastery"][4] == "settlement")
for bad, why in ((["historic=pyramid"], "not a historic tag"), ([], "at least one")):
    try:
        osmsites.pick_tags(bad)
        check(f"{bad or 'nothing'} is refused", False)
    except osmmap.OsmError as e:
        check(f"{bad or 'nothing'} is refused: {e}", why in str(e))

# ---------------------------------------------------------------------------
print("\n2) off by default")
try:
    osmsites.fetch(box, ["historic=castle"])
    check("a fetch is refused while it is off", False)
except osmmap.OsmOff:
    check("a fetch is refused while it is off", True)
check("and the fake was asked nothing", not QUERIES)
config.save_settings(osm_enabled=True)

# ---------------------------------------------------------------------------
print("\n3) the fetch")
FAIL["n"] = 1
four = ["historic=castle", "historic=fort", "historic=monastery", "castle_type=defensive"]
got = osmsites.fetch(box, four)
parts = len(osmmap._chunks(box, osmmap.CHUNK_DEG))
check(f"one query a chunk for all four tags ({parts} chunks), the failed one split in "
      f"four: {len(QUERIES)} asked",
      len(QUERIES) == parts + 4 and all(q.count("nwr[") == 4 for q in QUERIES))
check("a castle node at its own point",
      got["historic=castle"] == [{"id": "node/1", "lat": 47.0, "lon": 7.5, "name": "Bodiam"}])
check("the same castle under castle_type=defensive too",
      [e["id"] for e in got["castle_type=defensive"]] == ["node/1"])
forts = {e["id"]: e for e in got["historic=fort"]}
check("a way's centre from `out center`, its name:en when it has no name",
      forts.get("way/2", {}).get("lat") == 44.0 and forts["way/2"]["name"] == "Old Fort")
check("a fort on the corner of four chunks is listed once",
      [e["id"] for e in got["historic=fort"]].count("node/6") == 1)
m = got["historic=monastery"]
check("a relation with only geometry at his mean of its points, no name",
      len(m) == 1 and abs(m[0]["lat"] - 42.0) < 1e-9 and abs(m[0]["lon"] - 12.0) < 1e-9
      and m[0]["name"] == "")
asked = len(QUERIES)
again = osmsites.fetch(box, four)
check("a second fetch of the same tags asks nothing", len(QUERIES) == asked and again == got)
more = osmsites.fetch(box, four + ["historic=tower"])
new = QUERIES[asked:]
check(f"one tag more asks for that tag alone ({len(new)} queries)",
      new and all(q.count("nwr[") == 1 and '"tower"' in q for q in new)
      and [e["name"] for e in more["historic=tower"]] == ["Lookout"])
check("the church, never asked for, never came back", "historic=church" not in more)

# ---------------------------------------------------------------------------
print("\n4) onto a map")
ss = osmsites.sites(more, proj)
castle = next(s for s in ss if s["tag"] == "historic=castle")
fx, fy = proj.to_tile(47.0, 7.5)
check(f"the castle's pixel is his rounding of the projection: {castle['x']}, {castle['y']}",
      (castle["x"], castle["y"]) == (math.floor(fx + 0.5), math.floor(fy + 0.5)))
check("and its strat tile counts y from the bottom",
      castle["gx"] == castle["x"] and castle["gy"] == H - 1 - castle["y"] and castle["on_map"])
check("each site carries its tag's colour and suggestion",
      castle["colour"] == [87, 219, 100] and castle["suggest"] == "fort")
text = osmsites.features_text(more, proj)
lines = text.split("\n")
check("historic_features.txt opens with his two header lines",
      lines[0] == "; OSM Historic Features - Bulk Export" and lines[1] == f"; Map size: {W}x{H}")
check("a block a tag with its count",
      "; === Castle (historic=castle) - 1 features ===" in lines
      and "; === Fort (historic=fort) - 2 features ===" in lines)
check("a line a site, his shape",
      f'Castle; x{castle["x"]}; y{castle["y"]}; name: "Bodiam"' in lines
      and any(ln.startswith("Monastery; x") and ln.endswith('name: "(no name)"') for ln in lines))
check("no long dash anywhere in it", chr(0x2014) not in text)

turned = osmmap.Bbox(N, S, WEST, EAST, 30.0)
tproj = osmmap.Projection(turned, W, H)
ts = osmsites.sites(osmsites.fetch(turned, ["historic=tower"]), tproj)
check("on a turned map, a site in the envelope's corner is off the map",
      ts and all(not s["on_map"] for s in ts))

# ---------------------------------------------------------------------------
print("\n5) the world picker's form: a box, no map")
wb = osmsites.for_box(box, ["historic=castle", "historic=tower"])
check("every site inside the plain box, each only its point",
      {s["name"] for s in wb["sites"]} == {"Bodiam", "Lookout"}
      and all("x" not in s for s in wb["sites"])
      and wb["counts"] == {"historic=castle": 1, "historic=tower": 1})
wt = osmsites.for_box(turned, ["historic=castle", "historic=tower"])
check("a turned box leaves out the site in its envelope's corner and keeps its middle",
      {s["name"] for s in wt["sites"]} == {"Bodiam"})

# ---------------------------------------------------------------------------
print("\n6) the castle becomes a fort on its tile")
CR = "\r\n"
STRAT = CR.join((
    "campaign imperial_campaign", "playable", "\tengland", "end",
    "nonplayable", "\tslave", "end", "start_date 1080 summer",
    "faction england, balanced smith",
    "settlement", "{", "\tlevel town", "\tregion London_Province",
    "\tyear_founded 0", "\tpopulation 800", "\tplan_set default_set",
    "\tfaction_creator england", "}",
    "character\tWilliam, named character, male, leader, age 30, x 10, y 20",
    "army", "unit\t\tNE Bodyguard\t\texp 1 armour 0 weapon_lvl 0", "",
    "faction_standings england, 0.0 slave",
    "faction_relationships england, at_war_with slave", "",
    "region London_Province", "farming_level 0", "famine_threat 0", "",
    ";;;;;;;;", "; the scripts", "", "script", "campaign_script.txt")) + CR
tmp = Path(_tmp.mkdtemp(prefix="ut_osmsites_"))
CAMP = "imperial_campaign"
sroot = tmp / "FortMod"
sdir = sroot / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
sdir.mkdir(parents=True, exist_ok=True)
write_text(sdir / campstrat.STRAT_NAME, STRAT, campstrat.ENCODING)
smod = Mod(sroot)


class Facts:
    def __init__(self, mod, campaign):
        self.mod, self.campaign, self.cm = mod, campaign, None
        self.strat_rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{campaign}/"
                          f"{campstrat.STRAT_NAME}")
        self.strat = campstrat.read_strat(mod, campaign)


p = stratobj.plan(smod, Facts(smod, CAMP), {
    "campaign": CAMP, "kind": castle["suggest"], "action": "add",
    "x": castle["gx"], "y": castle["gy"], "region": "London_Province"})
check(f"the plan for a fort on the castle's tile passes: {p.changes}", p.payload()["ok"])
stratobj.apply(p)
back = campstrat.read_strat(smod, CAMP)
check(f"and the file now has a fort on {castle['gx']}, {castle['gy']}",
      [(n.get("x"), n.get("y")) for n in back.of_kind("fort")]
      == [(castle["gx"], castle["gy"])])

# ---------------------------------------------------------------------------
print("\n7) the route")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

med2 = Path(_tmp.mkdtemp(prefix="ut_osmsites_m2_"))
root = med2 / "mods" / "Sites"
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


def tga(path, w, h, rgb, depth=32, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=w, height=h, depth=depth, descriptor=desc)
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


st = get("/api/osm?mod=Sites")
check("GET /api/osm carries his 21 tags",
      len(st.get("historic_tags") or []) == 21, ) or print("   ", str(st)[:300])
r = post("/api/osm/historic", {"mod": "Sites", "tags": ["historic=castle", "historic=fort"]})
c = next((s for s in r.get("sites", []) if s["tag"] == "historic=castle"), {})
check("POST /api/osm/historic with a mod: the sites on its map and the file",
      (c.get("gx"), c.get("gy")) == (castle["gx"], castle["gy"])
      and r.get("counts") == {"historic=castle": 1, "historic=fort": 2}
      and r.get("text", "").startswith("; OSM Historic Features")) or print("   ", str(r)[:300])
r = post("/api/osm/historic", {"box": box.payload(), "tags": ["historic=tower"]})
check("and with a box and no mod, the world picker's form",
      [s["name"] for s in r.get("sites", [])] == ["Lookout"])
r = post("/api/osm/historic", {"box": box.payload(), "tags": ["historic=pyramid"]})
check("an unknown tag is an error, not a crash", "not a historic tag" in (r.get("error") or ""))
config.save_settings(osm_enabled=False)
r = post("/api/osm/historic", {"box": box.payload(), "tags": ["historic=church"]})
check("switched off, a tag not on disk is refused", "off" in (r.get("error") or ""))
httpd.shutdown()
fake.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
