"""Phase 87a: the world picker, and a box that can be turned.

    python -m tests.test_osmworld

Nothing here touches the network: Nominatim and the elevation tiles are
replaced in the process.

1. An unturned box is exactly the Phase 25 projection, both ways.
2. A turned box is Mylae's ``rotatedBbox``: the map's corners land where his
   ``rotatePointMerc`` puts the box's corners, and the projection goes there
   and back.
3. The box's file: ``rotation=`` written only for a turned box, read back,
   and a coordinate of exactly 0 kept (his loader drops it).
4. The shape: ``fit`` gives a box that stretches nothing, keeping the edges
   asked for; ``size_for`` and ``stretch`` agree with it; a fit that would
   pass the pole is refused.
5. The envelope covers every corner, and the Overpass chunks cover the
   envelope.
6. Heights from a turned box: one affine transform still puts every corner of
   the heights on the stitched tiles where the turned projection says.
7. The worldwide search: results with their extent, sent unbounded.
8. The same geometry in the page: osmmap.js's helpers run in node agree with
   Python, and osmworld.js holds the opposite corner still while a corner of
   a turned box is dragged, and holds the map's shape.
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import config, mapgen, osmmap  # noqa: E402

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

W, H = 80, 60
BOX = osmmap.Bbox(50.0, 40.0, 0.0, 15.0)
TURNED = osmmap.Bbox(50.0, 40.0, 0.0, 15.0, 30.0)


def close(a, b, eps=1e-6):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


# Mylae's lib/rotatedBbox.js, transcribed: the reference the turn is held to
def his_merc_y(lat):
    return math.log(math.tan(math.pi / 4 + lat * math.pi / 360)) * 180 / math.pi


def his_inv_merc_y(y):
    return (2 * math.atan(math.exp(y * math.pi / 180)) - math.pi / 2) * 180 / math.pi


def his_rotate(c_lat, c_lng, lat, lng, deg):
    a = deg * math.pi / 180
    cy = his_merc_y(c_lat)
    dx, dy = lng - c_lng, his_merc_y(lat) - cy
    return (his_inv_merc_y(cy + dy * math.cos(a) - dx * math.sin(a)),
            c_lng + dx * math.cos(a) + dy * math.sin(a))


print("\n== 1) an unturned box is the Phase 25 projection ==")
p = osmmap.Projection(BOX, W, H)
mn, ms = osmmap.merc(BOX.north), osmmap.merc(BOX.south)
pts = [(47.3, 3.1), (40.0, 0.0), (50.0, 15.0), (41.7, 12.9)]
old = [((lo - BOX.west) / (BOX.east - BOX.west) * (W - 1),
        (mn - osmmap.merc(la)) / (mn - ms) * (H - 1)) for la, lo in pts]
check("to_tile is the old two lines", all(close(p.to_tile(*q), o) for q, o in zip(pts, old)))
check("to_geo is its inverse", all(close(p.to_geo(*p.to_tile(*q)), q, 1e-9) for q in pts))
check("a rotation under the threshold is no rotation",
      not osmmap.Bbox(50, 40, 0, 15, 0.005).rotated
      and "rotation" not in osmmap.Bbox(50, 40, 0, 15, 0.005).payload())

print("\n== 2) a turned box is Mylae's rotatedBbox ==")
pt = osmmap.Projection(TURNED, W, H)
clat, clon = (TURNED.north + TURNED.south) / 2, (TURNED.east + TURNED.west) / 2
his = [his_rotate(clat, clon, la, lo, 30) for la, lo in
       ((50, 0), (50, 15), (40, 15), (40, 0))]
mine = [pt.to_geo(-0.0, 0), pt.to_geo(W - 1, 0), pt.to_geo(W - 1, H - 1), pt.to_geo(0, H - 1)]
check("the map's four corner tiles stand on his four turned corners",
      all(close(a, b, 1e-9) for a, b in zip(mine, his)))
check("and the box's own corners() agree",
      all(close(a, b, 1e-9) for a, b in zip(TURNED.corners(), his)))
check("to_tile goes back, anywhere on the map",
      all(close(pt.to_tile(*pt.to_geo(fx, fy)), (fx, fy), 1e-7)
          for fx, fy in ((0, 0), (13.5, 44.25), (79, 59), (40, 30))))
# clockwise on screen: the top edge's middle moves east
top = pt.to_geo((W - 1) / 2, 0)
check("positive is clockwise on screen: the top edge's middle moves east",
      top[1] > clon + 1)
check("to_lonmerc is affine in the tile position (so one transform resamples)",
      close([(a + b) / 2 for a, b in zip(pt.to_lonmerc(0, 0), pt.to_lonmerc(20, 10))],
            pt.to_lonmerc(10, 5), 1e-9))

print("\n== 3) the file ==")
txt = osmmap.bbox_text(TURNED, W, H)
check("a turned box writes rotation=", "rotation=30.0000" in txt)
check("an unturned one does not", "rotation" not in osmmap.bbox_text(BOX, W, H))
back = osmmap.parse_bbox(txt)
check("and it reads back, turn and all", close(
    (back.north, back.south, back.west, back.east, back.rotation), (50, 40, 0, 15, 30)))
zero = osmmap.parse_bbox("north=10\nsouth=0\nwest=0\neast=12\n")
check("a coordinate of exactly 0 is kept (Mylae's loader drops it)",
      zero.south == 0 and zero.west == 0)
for bad, why in ((dict(north=50, south=40, west=0, east=15, rotation=200), "past 180"),
                 (dict(north=85, south=80, west=0, east=60, rotation=45), "past the pole"),
                 (dict(north=10, south=0, west=170, east=179.5, rotation=60), "the date line")):
    try:
        osmmap.parse_bbox(bad)
        check(f"a turn {why} is refused", False)
    except osmmap.OsmError as e:
        check(f"a turn {why} is refused ({e})", True)

print("\n== 4) the shape ==")
f = osmmap.fit(BOX, W, H, "width")
check("fit keeps west and east and moves north and south",
      f.west == BOX.west and f.east == BOX.east and f.north != BOX.north)
check("and the result stretches nothing", abs(osmmap.stretch(f, W, H)) < 1e-9)
check("the tile is as tall as it is wide on the ground there",
      abs(osmmap.Projection(f, W, H).km_per_tile()[0]
          / osmmap.Projection(f, W, H).km_per_tile()[1] - 1) < 1e-6)
g = osmmap.fit(BOX, W, H, "height")
check("fit=height keeps north and south",
      g.north == BOX.north and g.south == BOX.south and abs(osmmap.stretch(g, W, H)) < 1e-9)
check("the rotation survives a fit", osmmap.fit(TURNED, W, H).rotation == 30)
sw, sh = osmmap.size_for(f, width=W)
check(f"size_for gives the map back from the box's shape ({sw}x{sh})", (sw, sh) == (W, H))
check("and from a height", osmmap.size_for(f, height=H) == (W, H))
check("the stock box stretches a 80x60 map, and says by how much",
      abs(osmmap.stretch(BOX, W, H)) > 0.05)
try:
    osmmap.fit(osmmap.Bbox(84, 80, 0, 90), 20, 60, "width")
    check("a fit past the pole is refused", False)
except osmmap.OsmError:
    check("a fit past the pole is refused", True)

print("\n== 5) the envelope and the chunks ==")
env = TURNED.envelope()
check("the envelope holds every corner",
      all(env.south - 1e-9 <= la <= env.north + 1e-9 and env.west - 1e-9 <= lo <= env.east + 1e-9
          for la, lo in TURNED.corners()))
check("an unturned box is its own envelope", BOX.envelope() == osmmap.Bbox(50, 40, 0, 15))
parts = osmmap._chunks(TURNED, osmmap.CHUNK_DEG)
check(f"the {len(parts)} Overpass chunks cover the envelope, no more",
      min(c.south for c in parts) == env.south and max(c.north for c in parts) == env.north
      and min(c.west for c in parts) == env.west and max(c.east for c in parts) == env.east
      and all(not c.rotated for c in parts))

print("\n== 6) heights from a turned box ==")


def column_tile(z, x, y):
    t = Image.new("F", (256, 256))
    t.putdata([float(c + 256 * x) for _ in range(256) for c in range(256)])
    return t


def row_tile(z, x, y):
    t = Image.new("F", (256, 256))
    t.putdata([float(r + 256 * y) for r in range(256) for _ in range(256)])
    return t


cols, rows = 2 * W + 1, 2 * H + 1
real_tile = mapgen.elevation_tile
try:
    mapgen.elevation_tile = column_tile
    mx = mapgen.elevation(TURNED, cols, rows)
    mapgen.elevation_tile = row_tile
    my = mapgen.elevation(TURNED, cols, rows)
finally:
    mapgen.elevation_tile = real_tile
probe = [(1, 1), (2 * W - 1, 1), (1, 2 * H - 1), (81, 61), (40, 100)]
best = None
for z in range(3, 13):
    err = 0.0
    for i, j in probe:
        la, lo = pt.to_geo((i - 1) / 2, (j - 1) / 2)
        # a tile pixel k holds the value at its centre, k + .5
        err = max(err, abs(mx.getpixel((i, j)) + 0.5 - mapgen._lon2x(lo, z)),
                  abs(my.getpixel((i, j)) + 0.5 - mapgen._lat2y(la, z)))
    if best is None or err < best[1]:
        best = (z, err)
check(f"every probed corner samples the tile pixel under its turned position "
      f"(zoom {best[0]}, worst {best[1]:.2f} px)", best[1] < 1.0)

print("\n== 7) the worldwide search ==")
ANSWER = [{"lat": "41.9", "lon": "12.5", "name": "Roma", "display_name": "Roma, Lazio, Italia",
           "osm_type": "relation", "osm_id": 41485, "addresstype": "city",
           "boundingbox": ["41.65", "42.14", "12.23", "12.86"], "extratags": {"admin_level": "8"}},
          {"lat": "x", "lon": "0"}]
SENT = []
real_fetch = osmmap._fetch


def fake_fetch(url, data=None, timeout=60):
    SENT.append(url)
    return json.dumps(ANSWER).encode()


osmmap._fetch = fake_fetch
try:
    try:
        osmmap.search_world("Rome")
        check("off, the world search refuses and sends nothing", False)
    except osmmap.OsmOff:
        check("off, the world search refuses and sends nothing", not SENT)
    config.save_settings(**{osmmap.ENABLED_KEY: True})
    got = osmmap.search_world("Rome")
    check("on, it answers with the place and its extent, the bad row dropped",
          len(got) == 1 and got[0]["name"] == "Roma" and got[0]["admin_level"] == 8
          and got[0]["extent"] == {"north": 42.14, "south": 41.65, "west": 12.23, "east": 12.86})
    check("and it asked for no box: the query is unbounded (the route is in test_osmmap)",
          "bounded" not in SENT[-1] and "viewbox" not in SENT[-1])
finally:
    osmmap._fetch = real_fetch

print("\n== 8) the same geometry in the page ==")
node = shutil.which("node")
if not node:
    print("  -- node is not on PATH, so the page's geometry is not run")
else:
    t = Path(_tmp.mkdtemp(prefix="ut_owp_"))
    harness = t / "harness.js"
    harness.write_text(r"""
const fs = require('fs'), vm = require('vm');
const ctx = {state: {}, console, Math, Map, Object, Array, JSON, isFinite, parseFloat};
vm.createContext(ctx);
for(const f of process.argv.slice(2)) vm.runInContext(fs.readFileSync(f, 'utf8'), ctx, {filename: f});
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = vm.runInContext(`(function(req){
  const b = req.box, W = req.W, H = req.H, r = {};
  r.tile = req.pts.map(p => osmToTile(b, W, H, p[0], p[1]));
  r.geo = req.tiles.map(p => osmToGeo(b, W, H, p[0], p[1]));
  r.km = osmKmPerTile(b, W, H);
  r.stretch = osmStretch(b, W, H);
  const g = osmGeoAffine(b, W, H);
  r.affine = req.pts.map(p => { const m = osmMerc(p[0]);
    return [g[0]*p[1] + g[2]*m + g[4], g[1]*p[1] + g[3]*m + g[5]]; });
  // drag corner 2 (south-east) of the turned box somewhere, the shape kept
  state.owp = {W: W, H: H, lock: true, drag: {box0: b}};
  const fixBefore = owpCorners(b)[0];
  const moved = owpCornerTo(2, [b.east + 3, osmMdeg(b.south) - 2]);
  r.fixBefore = fixBefore; r.fixAfter = owpCorners(moved)[0];
  r.movedStretch = osmStretch(moved, W, H);
  r.movedRot = moved.rotation;
  state.owp.lock = false;
  const free = owpCornerTo(2, [b.east + 3, osmMdeg(b.south) - 2]);
  r.freeFix = owpCorners(free)[0];
  r.freeCorner = owpCorners(free)[2];
  // a box drawn by dragging, the shape kept: from where the press was, as far
  // as the longer side of the drag reaches
  state.owp.lock = true;
  r.drawn = owpRect([10, 50], [22, 45], 0);
  r.drawnStretch = osmStretch(r.drawn, W, H);
  state.owp.lock = false;
  r.drawnFree = owpRect([10, 50], [22, 45], 0);
  return r;
})`, ctx)(req);
process.stdout.write(JSON.stringify(out));
""", encoding="utf-8")
    fitted = osmmap.fit(TURNED, W, H)
    req = {"box": {"north": fitted.north, "south": fitted.south, "west": fitted.west,
                   "east": fitted.east, "rotation": fitted.rotation},
           "W": W, "H": H, "pts": [list(q) for q in pts], "tiles": [[0, 0], [79, 59], [13.5, 44.25]]}
    r = subprocess.run([node, str(harness), str(ROOT / "web/js/osmmap.js"),
                        str(ROOT / "web/js/osmworld.js")],
                       input=json.dumps(req), capture_output=True, text=True, timeout=60)
    if not check("the harness runs", r.returncode == 0):
        print(r.stderr[-2000:])
    else:
        js = json.loads(r.stdout)
        pf = osmmap.Projection(fitted, W, H)
        check("osmToTile agrees with Projection.to_tile on a turned box",
              all(close(a, pf.to_tile(*q), 1e-7) for a, q in zip(js["tile"], pts)))
        check("osmToGeo agrees with Projection.to_geo",
              all(close(a, pf.to_geo(*q), 1e-9) for a, q in zip(js["geo"], req["tiles"])))
        check("osmGeoAffine is the same projection as one affine (what draws a tile)",
              all(close(a, b, 1e-6) for a, b in zip(js["affine"], js["tile"])))
        check("the km per tile agree", close(js["km"], pf.km_per_tile(), 1e-9))
        check("and so does the stretch", abs(js["stretch"] - osmmap.stretch(fitted, W, H)) < 1e-12)
        check("dragging a corner of the turned box holds the opposite corner still",
              close(js["fixBefore"], js["fixAfter"], 1e-6))
        check("keeps the turn, and holds the map's shape",
              js["movedRot"] == 30 and abs(js["movedStretch"]) < 1e-9)
        check("a drawn box keeps the map's shape, from the corner the drag began at",
              abs(js["drawnStretch"]) < 1e-9 and js["drawn"]["west"] == 10
              and abs(osmmap.merc_deg(js["drawn"]["north"]) - 50) < 1e-9)
        check("and drawn free, it is exactly the drag",
              close([js["drawnFree"]["west"], js["drawnFree"]["east"],
                     osmmap.merc_deg(js["drawnFree"]["north"]),
                     osmmap.merc_deg(js["drawnFree"]["south"])], [10, 22, 50, 45], 1e-9))
        check("and without the shape kept, the corner goes where it was dragged",
              close(js["freeCorner"], [fitted.east + 3, osmmap.merc_deg(fitted.south) - 2], 1e-6)
              and close(js["freeFix"], js["fixBefore"], 1e-6))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
