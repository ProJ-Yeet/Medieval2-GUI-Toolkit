"""Phase 87d: ground types and climates from the real world.

    python -m tests.test_mapreal

Nothing here touches the network: Overpass and the WMS are replaced in the
process, and the Köppen-Geiger map is a file written here.

1. Land use: the tags ticked are fetched one by one, each painted as its
   ground type in the order listed (a later tag over an earlier one), on land
   only, holes cut back out; nothing ticked is refused, a sea type too.
2. Land cover: a WMS picture in the legend colours, each class its ground
   type; a colour near a legend colour is that class, one far from all is
   none; only palette colours come out (never his blend); a class left out
   is left; the request is for the envelope in metres.
3. Köppen from a file on disk, with the switch off: a plain global picture, a
   palette PNG and a GeoTIFF with its own tie point all read; each zone its
   climate; a climate the mod lacks is said; a map too big to read is refused.
4. Köppen from a WMS, in the legend colours.
5. One climate everywhere, and Phase 27's table naming vanilla's slots.
6. A turned box: the zones follow the turn.
"""
import io
import json
import math
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, TiffImagePlugin  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import campmap, config, mapgen, mapreal, mapvocab, osmmap, transfer  # noqa: E402
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

# ---- a 60x40 map over 0-15 E, 40-50 N: land from 4 to 55 across, 4 to 31 down --
W, H = 60, 40
SEA = (41, 140, 233)


def is_land(x, y):
    return 4 <= x <= 55 and 4 <= y <= 31


def corner_land(vx, vy):
    return is_land(max(0, (vx - 1) // 2), max(0, (vy - 1) // 2))


def write_tga(path, img):
    info = TgaInfo(image_type=2, width=img.width, height=img.height, depth=24, descriptor=0x20)
    path.write_bytes(encode(img.convert(info.mode), info))


def img_of(w, h, fn):
    im = Image.new("RGB", (w, h))
    im.putdata([fn(x, y) for y in range(h) for x in range(w)])
    return im


V, U = 2 * W + 1, 2 * H + 1
root = Path(_tmp.mkdtemp(prefix="ut_real_")) / "mods" / "Real"
base = root / "data" / campmap.BASE_REL
base.mkdir(parents=True)
(base / "descr_terrain.txt").write_text(
    "dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n\tmin_sea_height  -1000.000\n"
    "\tmax_land_height  3000.000\n}\n" % (W, H), encoding="latin-1")
(base / "descr_regions.txt").write_bytes(
    b"A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n\tgold\r\n\t5\r\n\t4\r\n"
    b"\treligions { catholic 100 }\r\n")
write_tga(base / "map_regions.tga", img_of(W, H, lambda x, y: (10, 20, 30) if is_land(x, y) else SEA))
write_tga(base / "map_heights.tga", img_of(V, U, lambda x, y: (60, 60, 60) if corner_land(x, y) else (0, 0, 200)))
OLD_GROUND = mapvocab.ground("wilderness")["rgb"]
SEA_GROUND = mapvocab.ground("sea_deep")["rgb"]
write_tga(base / "map_ground_types.tga",
          img_of(V, U, lambda x, y: OLD_GROUND if corner_land(x, y) else SEA_GROUND))
OLD_CLIM = (1, 2, 3)
write_tga(base / "map_climates.tga", img_of(V, U, lambda x, y: OLD_CLIM))
for name, size in (("map_features.tga", (W, H)), ("map_fog.tga", (V, U)),
                   ("map_trade_routes.tga", (W, H)), ("map_roughness.tga", (2 * W, 2 * H))):
    write_tga(base / name, Image.new("RGB", size))
(root / "data" / mapvocab.CLIMATES_REL).parent.mkdir(parents=True, exist_ok=True)
(root / "data" / mapvocab.CLIMATES_REL).write_text(
    "climates\n{\n\tmediterranean\n\tunused1\n\ttemperate_deciduous_forest\n}\n"
    "climate mediterranean\n{\n\tcolour 236 0 140\n\theat 3\n}\n"
    "climate unused1\n{\n\tcolour 237 20 91\n\theat 2\n}\n"
    "climate temperate_deciduous_forest\n{\n\tcolour 242 101 34\n\theat 2\n}\n", encoding="latin-1")
BOX = osmmap.Bbox(50.0, 40.0, 0.0, 15.0)


def fresh():
    mod = Mod(root)
    return mod, campmap.CampaignMap(mod)


mod, cm = fresh()
osmmap.keep_box(cm, BOX)
proj = osmmap.Projection(BOX, W, H)


def corner_at(lat, lon):
    fx, fy = proj.to_tile(lat, lon)
    return round(2 * fx + 1), round(2 * fy + 1)


def _decode(raw):
    t = cfg / "tmp.tga"
    t.write_bytes(raw)
    return read(t)[0].convert("RGB")


# ---- the fakes ------------------------------------------------------------------
QUERIES = []


def ring(pts):
    return [{"lat": a, "lon": o} for a, o in pts + pts[:1]]


def fake_overpass(q):
    QUERIES.append(q)
    els = []
    if '["landuse"="farmland"]' in q:
        els.append({"type": "relation", "id": 1, "tags": {"landuse": "farmland"}, "members": [
            {"type": "way", "role": "outer", "geometry": ring([(48, 2), (48, 8), (43, 8), (43, 2)])},
            {"type": "way", "role": "inner", "geometry": ring([(46.4, 4.4), (46.4, 5.6), (45.6, 5.6), (45.6, 4.4)])}]})
    if '["natural"="wood"]' in q:
        # half under the farmland, half east of it
        els.append({"type": "way", "id": 2, "tags": {"natural": "wood"},
                    "geometry": ring([(47, 6), (47, 11), (44, 11), (44, 6)])})
    if '["natural"="beach"]' in q:
        # all of it at sea
        els.append({"type": "way", "id": 3, "tags": {"natural": "beach"},
                    "geometry": ring([(40.4, 1), (40.4, 3), (40.1, 3), (40.1, 1)])})
    return {"elements": els}


real_overpass = osmmap.overpass
osmmap.overpass = fake_overpass
config.save_settings(osm_enabled=True)

print("\n== 1) land use ==")
p = mapgen.plan(mod, cm, {"kind": "landuse", "tags": {}})
check("nothing ticked is refused, and nothing is asked", not p.payload()["ok"] and not QUERIES)
p = mapgen.plan(mod, cm, {"kind": "landuse", "tags": {"landuse=farmland": "sea_deep"}})
check("a sea ground type is refused", not p.payload()["ok"] and "sea" in p.errors[0])
p = mapgen.plan(mod, cm, {"kind": "landuse", "tags": {
    "landuse=farmland": "fertility_high", "natural=wood": "forest_dense",
    "natural=beach": "beach"}})
chunks = len(osmmap._chunks(BOX, osmmap.CHUNK_DEG))
check(f"three tags, asked one by one ({len(QUERIES)} requests: {chunks} chunks each), "
      f"each naming only its own tag",
      p.payload()["ok"] and len(QUERIES) == 3 * chunks
      and all(len({f for f in ('farmland', 'wood', 'beach') if f in q}) == 1 for q in QUERIES))
g = _decode(next(iter(p.data.values())))
FH, FD = mapvocab.ground("fertility_high")["rgb"], mapvocab.ground("forest_dense")["rgb"]
check("farmland comes after wood in his list, so where both lie it is farmland",
      g.getpixel(corner_at(45, 7)) == FH)
check("wood east of the farmland is wood", g.getpixel(corner_at(45.5, 10)) == FD)
check("the hole in the farmland keeps its old type", g.getpixel(corner_at(46, 5)) == OLD_GROUND)
check("outside every outline the land keeps its type", g.getpixel(corner_at(49, 13)) == OLD_GROUND)
check("the beach out at sea is not painted: the sea is left alone",
      g.getpixel(corner_at(40.25, 2)) == SEA_GROUND and "Beach (natural=beach, 1 outline(s)) 0 ->" in p.changes[0])
n = len(QUERIES)
mapgen.plan(mod, cm, {"kind": "landuse", "tags": {"landuse=farmland": "fertility_high"}})
check("a second look at a tag asks nothing", len(QUERIES) == n)
pz = mapgen.plan(mod, cm, {"kind": "landuse", "tags": {"natural=beach": "beach"}})
check("a tag with nothing over the land is refused: nothing would change",
      not pz.payload()["ok"] and "nothing would change" in pz.errors[0])
out = mapgen.apply(p)
check("written as one file with one Undo", out["files"] == [campmap.rel_of(cm, "map_ground_types.tga")])
transfer.undo(out["id"])
mod, cm = fresh()

print("\n== 2) land cover ==")
URLS = []
real_fetch = osmmap._fetch
WC = {c: rgb for c, _, rgb, _ in mapreal.WORLDCOVER}


def wms_picture(url):
    """West of 7.5 E cropland, east tree cover; one column a shade off the
    cropland colour, one row a colour in no legend."""
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    w, h = int(qs["WIDTH"][0]), int(qs["HEIGHT"][0])
    x0, y0, x1, y1 = (float(v) for v in qs["BBOX"][0].split(","))
    im = Image.new("RGB", (w, h))
    px = im.load()
    for i in range(w):
        lon = math.degrees((x0 + (i + 0.5) / w * (x1 - x0)) / 6378137.0)
        for j in range(h):
            c = WC[40] if lon < 7.5 else WC[10]
            if abs(lon - 3) < 0.1:
                c = (c[0] - 12, c[1] + 9, c[2] - 7)        # close enough: still cropland
            px[i, j] = c
    for i in range(w):
        px[i, h // 2] = (13, 13, 250)                      # nothing
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def fake_fetch(url, data=None, timeout=60):
    URLS.append(url)
    if "KOPPEN" in url:
        return koppen_wms_picture(url)
    return wms_picture(url)


osmmap._fetch = fake_fetch
config.save_settings(osm_landcover_wms=["http://wms.test/?LAYERS=WC&BBOX={bbox}&WIDTH={width}&HEIGHT={height}"])
p = mapgen.plan(mod, cm, {"kind": "landcover"})
check(f"planned: {p.changes[:1]}", p.payload()["ok"])
qs = urllib.parse.parse_qs(urllib.parse.urlsplit(URLS[-1]).query)
x0, y0, x1, y1 = (float(v) for v in qs["BBOX"][0].split(","))
check("the request is the box in EPSG:3857 metres, sized for the map",
      abs(x0) < 1 and abs(x1 - 6378137 * math.radians(15)) < 1
      and abs(y1 - 6378137 * osmmap.merc(50)) < 1 and int(qs["WIDTH"][0]) >= V)
g = _decode(next(iter(p.data.values())))
check("cropland west is fertility_high, tree cover east forest_sparse",
      g.getpixel(corner_at(45, 4)) == FH
      and g.getpixel(corner_at(45, 12)) == mapvocab.ground("forest_sparse")["rgb"])
check("a shade off the legend colour is still that class", g.getpixel(corner_at(46.5, 3)) == FH)
palette = {tuple(t["rgb"]) for t in mapvocab.GROUND_TYPES}
check("only ground-type colours come out: never a blend of two",
      {c for _, c in g.getcolors(1 << 20)} <= palette)
check("the sea is left alone", g.getpixel((0, 0)) == SEA_GROUND)
p2 = mapgen.plan(mod, cm, {"kind": "landcover", "mapping": {"10": "-"}})
g2 = _decode(next(iter(p2.data.values())))
check("a class left out keeps the ground it had, and is said",
      g2.getpixel(corner_at(45, 12)) == OLD_GROUND and any("Tree cover" in w for w in p2.warnings))

print("\n== 3) Köppen from a file, with the switch off ==")
config.save_settings(osm_enabled=False)
URLS.clear()
CSA, CFB = mapreal.KOPPEN_INDEX["Csa"], mapreal.KOPPEN_INDEX["Cfb"]


def zones(lat, lon):
    if lat < 44:
        return CSA
    return CFB if lon < 20 else 0


def world(w, h, fn):
    im = Image.new("L", (w, h))
    im.putdata([fn(90 - (j + 0.5) * 180 / h, -180 + (i + 0.5) * 360 / w)
                for j in range(h) for i in range(w)])
    return im


tif = cfg / "koppen_0p5.tif"
world(720, 360, zones).save(tif, compression="tiff_deflate")
config.save_settings(koppen_file=str(tif))
p = mapgen.plan(mod, cm, {"kind": "koppen"})
check(f"planned from the file with the switch off, nothing sent: {p.changes[:1]}",
      p.payload()["ok"] and not URLS)
c = _decode(next(iter(p.data.values())))
check("south of 44 N is Csa, mediterranean; north Cfb, temperate deciduous",
      c.getpixel(corner_at(42, 5)) == (236, 0, 140) and c.getpixel(corner_at(47, 5)) == (242, 101, 34))
check("his table by the engine's names: Cfb is temperate_deciduous_forest",
      dict((z, cl) for z, _, cl in mapreal.KOPPEN)["Cfb"] == "temperate_deciduous_forest")
p3 = mapgen.plan(mod, cm, {"kind": "koppen", "mapping": {"Csa": "alpine"}})
check("a climate the mod does not declare is said, and those corners keep theirs",
      any("Csa -> alpine" in w for w in p3.warnings)
      and _decode(next(iter(p3.data.values()))).getpixel(corner_at(42, 5)) == OLD_CLIM)
pal = Image.frombytes("P", (720, 360), world(720, 360, zones).tobytes())
pal.putpalette([v for i in range(256) for v in (i * 7 % 256, i * 3 % 256, i)])
png = cfg / "koppen.png"
pal.save(png)
pp = mapgen.plan(mod, cm, {"kind": "koppen", "file": str(png)})
check("a palette picture's numbers are read as numbers, not colours",
      pp.payload()["ok"] and _decode(next(iter(pp.data.values()))).getpixel(corner_at(42, 5)) == (236, 0, 140))
# a GeoTIFF of just Europe at 0.1 degrees, with its own tie point and scale
eu = Image.new("L", (300, 250))
eu.putdata([zones(60 - (j + 0.5) * 0.1, -10 + (i + 0.5) * 0.1)
            for j in range(250) for i in range(300)])
ifd = TiffImagePlugin.ImageFileDirectory_v2()
ifd[33550] = (0.1, 0.1, 0.0)
ifd.tagtype[33550] = 12
ifd[33922] = (0.0, 0.0, 0.0, -10.0, 60.0, 0.0)
ifd.tagtype[33922] = 12
geo = cfg / "koppen_eu.tif"
eu.save(geo, tiffinfo=ifd)
pg = mapgen.plan(mod, cm, {"kind": "koppen", "file": str(geo)})
cg = _decode(next(iter(pg.data.values())))
check("a GeoTIFF's own tie point and scale place it",
      pg.payload()["ok"] and cg.getpixel(corner_at(42, 5)) == (236, 0, 140)
      and cg.getpixel(corner_at(47, 5)) == (242, 101, 34))
mapreal.KOPPEN_MAX_PIXELS, keep = 1000, mapreal.KOPPEN_MAX_PIXELS
pb = mapgen.plan(mod, cm, {"kind": "koppen"})
mapreal.KOPPEN_MAX_PIXELS = keep
check("a map too big to read whole is refused, saying which to use",
      not pb.payload()["ok"] and "0.083" in pb.errors[0])
pn = mapgen.plan(mod, cm, {"kind": "koppen", "file": str(cfg / "nowhere.tif")})
check("a file that is not there is said", not pn.payload()["ok"] and "no file" in pn.errors[0])

print("\n== 4) Köppen from a WMS ==")
KR = [rgb for _, rgb, _ in mapreal.KOPPEN]


def koppen_wms_picture(url):
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    w, h = int(qs["WIDTH"][0]), int(qs["HEIGHT"][0])
    x0, y0, x1, y1 = (float(v) for v in qs["BBOX"][0].split(","))
    im = Image.new("RGB", (w, h))
    px = im.load()
    for j in range(h):
        m = (y1 - (j + 0.5) / h * (y1 - y0)) / 6378137.0
        lat = math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)
        for i in range(w):
            px[i, j] = KR[zones(lat, 5) - 1]
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


config.save_settings(osm_enabled=True, koppen_file="",
                     osm_koppen_wms=["http://koppen.test/?L=KOPPEN&BBOX={bbox}&WIDTH={width}&HEIGHT={height}"])
pw = mapgen.plan(mod, cm, {"kind": "koppen", "source": "wms"})
cw = _decode(next(iter(pw.data.values())))
check("the zones read off their legend colours",
      pw.payload()["ok"] and cw.getpixel(corner_at(42, 5)) == (236, 0, 140)
      and cw.getpixel(corner_at(47, 5)) == (242, 101, 34) and any("KOPPEN" in u for u in URLS))
config.save_settings(osm_koppen_wms=[])
pe = mapgen.plan(mod, cm, {"kind": "koppen", "source": "wms"})
check("with neither a file nor a WMS, it says where to give one",
      not pe.payload()["ok"] and "Settings" in pe.errors[0])

print("\n== 5) one climate everywhere, and the ground table ==")
pf = mapgen.plan(mod, cm, {"kind": "climates", "fill": "unused1"})
cf = _decode(next(iter(pf.data.values())))
check("every corner the climate asked for, the sea too",
      cf.getcolors() == [(V * U, (237, 20, 91))])
check("a climate the mod does not declare is refused",
      not mapgen.plan(mod, cm, {"kind": "climates", "fill": "swamp"}).payload()["ok"])
check("Phase 27's table names vanilla's slots: fertility_medium unused1, swamp unused2",
      mapgen.CLIMATE_OF["fertility_medium"] == "unused1" and mapgen.CLIMATE_OF["swamp"] == "unused2")

print("\n== 6) a turned box ==")
config.save_settings(osm_enabled=False, koppen_file=str(tif))
osmmap.keep_box(cm, osmmap.Bbox(50.0, 40.0, 0.0, 15.0, 90.0))
tp = osmmap.Projection(osmmap.Bbox(50.0, 40.0, 0.0, 15.0, 90.0), W, H)
pt = mapgen.plan(mod, cm, {"kind": "koppen"})
ct = _decode(next(iter(pt.data.values())))
wrong = 0
for vy in range(3, U - 3, 7):
    for vx in range(3, V - 3, 7):
        la, lo = tp.to_geo((vx - 1) / 2, (vy - 1) / 2)
        want = (236, 0, 140) if zones(la, lo) == CSA else (242, 101, 34)
        if abs(la - 44) > 0.3 and ct.getpixel((vx, vy)) != want:
            wrong += 1
check(f"turned a quarter, every probed corner has the zone under its turned position "
      f"({wrong} wrong)", pt.payload()["ok"] and wrong == 0)

osmmap.overpass, osmmap._fetch = real_overpass, real_fetch
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
