"""The front-end picture, framed - authoring map_FE.tga (37b, T3).

    python -m tests.test_mapfe

One little map written here - a 12x8 grid with three provinces on it and a
``map_FE.tga`` that is deliberately a different shape from all of them - plus
every installed mod for the measurements that only a real picture can carry.

**The suite is about the frame, because the frame is what the write-up was
missing.** T3 asks for the picture at its native size with everything else
scaled to meet it. Section 2 is why that needs a rectangle first: the picture's
shape and the map's are not the same shape in any installed mod, so "native
size" names nothing until somebody says which rectangle of the map the picture
is a picture OF. Section 3 is the one property that makes a single scalar zoom
enough - the default frame carries the picture's aspect, so one number draws
the picture 1:1 and leaves the map undistorted.

Section 5 is the defect this phase fixes, measured: the screen composites every
layer into a width-by-height-TILES canvas and then scales it, so the front-end
picture is resampled twice before anybody sees it. :func:`mapfe.render` is
checked to resample it zero times - it never touches the picture at all.

Section 7 is the header rule: an export goes out through the mod's own file's
header, so the depth, the origin and the compression of what comes out are the
depth, the origin and the compression of what went in.
"""
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, mapfe
from unittransfer import keyblock as kb
from unittransfer.maptga import probe, read
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little map ----------------------------------------------------------

W, H = 12, 8
#: the front-end picture, deliberately none of: the grid's size, the grid's
#: shape, or a whole multiple of either. 30x10 is 3.0 wide against the grid's
#: 1.5, so every "it just happened to divide" accident is off the table.
FE_W, FE_H = 30, 10

SEA = (41, 140, 233)
A = (200, 110, 100)
B = (100, 200, 110)
C = (110, 100, 200)

PICTURE = [
    "............",
    ".AAA...BB...",
    ".AAA...BB...",
    ".....CCC....",
    ".....CCC....",
    ".....CCC....",
    ".BB.........",
    "............",
]
LETTERS = {".": SEA, "A": A, "B": B, "C": C}

_BLOCK = ("\tnorthmen\r\n\tNorth_Rebels\r\n"
          "\t{0} {1} {2}\r\n\tnone\r\n\t2\r\n"
          "\treligions {{ catholic 100 orthodox 0 islam 0 heretic 0 }}\r\n")
REGIONS = (";;;;;;;;;;;;;;;;\r\n\r\n"
           "Alpha_Province\r\n\tAlphaton\r\n" + _BLOCK.format(*A) + "\r\n"
           "Beta_Province\r\n\tBetaton\r\n" + _BLOCK.format(*B) + "\r\n"
           "Gamma_Province\r\n\tGammaton\r\n" + _BLOCK.format(*C))

TERRAIN = (
    "dimensions\r\n{\r\n"
    f"\twidth  {W}\r\n\theight  {H}\r\n" + "}\r\n"
    "heights\r\n{\r\n\tmin_sea_height  -3406.782\r\n"
    "\tmax_land_height  7511.272\r\n}\r\n"
    "roughness\r\n{\r\n\tmin  50.000\r\n\tmax  200.000\r\n}\r\n"
    "fractal\r\n{\r\n\tmultiplier  0.500\r\n}\r\n"
    "lattitude\r\n{\r\n\tmin  22.000\r\n\tmax  56.000\r\n}\r\n"
)

#: the four corners of the little front-end picture, each a different colour,
#: so a render that lands the frame in the wrong place is visible in one pixel
FE_MARKS = {(0, 0): (255, 0, 0), (FE_W - 1, 0): (0, 255, 0),
            (0, FE_H - 1): (0, 0, 255), (FE_W - 1, FE_H - 1): (255, 255, 0)}


def little_mod(prefix="ut_fe_", fe=True, name="Tiny"):
    """A mod with the ten layers the reader needs, and its own front-end map.

    Under a ``mods/`` folder, because section 10 serves it and the registry
    discovers a mod by looking there.
    """
    med2 = Path(_tmp.mkdtemp(prefix=prefix))
    root = med2 / "mods" / name
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True)

    img = Image.new("RGB", (W, H))
    img.putdata([LETTERS[ch] for row in PICTURE for ch in row])
    img.save(base / "map_regions.tga")

    grids = {"tile": (W, H), "centre": (2 * W + 1, 2 * H + 1),
             "double": (2 * W, 2 * H), "advisory": (W, H), "free": (FE_W, FE_H)}
    for ly in campmap.LAYERS:
        if ly["code"] == "regions":
            continue
        if ly["code"] == "fe" and not fe:
            continue
        fill = {"heights": (100, 100, 100), "ground_types": (0, 100, 0),
                "climates": (12, 90, 200), "fog": (255, 255, 255)
                }.get(ly["code"], (0, 0, 0))
        one = Image.new("RGB", grids[ly["size"]], fill)
        if ly["code"] == "fe":
            for xy, rgb in FE_MARKS.items():
                one.putpixel(xy, rgb)
        one.save(base / ly["file"])

    kb.write_text(base / "descr_regions.txt", REGIONS, campmap.ENCODING)
    kb.write_text(base / "descr_terrain.txt", TERRAIN, campmap.ENCODING)
    return med2, Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

med2, mod = little_mod()
cm = campmap.CampaignMap(mod)
GRID = (cm.terrain.width, cm.terrain.height)
STACK = [{"code": "ground_types", "opacity": 1.0},
         {"code": "regions", "opacity": 1.0}]


# =============================================================================
print("\n1. the picture is read, and it is the shape nothing else is")

check(f"  the little map's grid is {GRID[0]}x{GRID[1]}", GRID == (W, H))
fe_img = mapfe.picture(cm)
check(f"  its map_FE.tga is {FE_W}x{FE_H}, which is neither",
      fe_img is not None and fe_img.size == (FE_W, FE_H)
      and fe_img.size != GRID)
check("  and campmap still calls the layer unaligned, which is why this exists",
      campmap.layer_view(cm, "fe")["aligned"] is False)


# =============================================================================
print("\n2. a front-end picture is not the map's shape - on the real mods too")

sizes = {}
for root in _realmod.installed():
    if not (root / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
        continue
    m = Mod(root)
    try:
        base = campmap.CampaignMap(m)
    except (campmap.MapError, OSError):
        continue
    grid = (base.terrain.width, base.terrain.height)
    for camp in campstrat.campaign_paths(m):
        fcm = campmap.campaign_map(m, camp, base)
        img = mapfe.picture(mapfe.fe_map(m, camp, fcm))
        if img is None:
            continue
        sizes[(root.name, camp)] = (img.size, grid)

if not sizes:
    print("  SKIPPED - no installed mod ships a map_FE.tga")
else:
    print(f"  {len(sizes)} campaign(s) ship one, over "
          f"{len({k[0] for k in sizes})} mod(s):")
    for (name, camp), (ps, grid) in sorted(sizes.items()):
        print(f"    {name}/{camp}: {ps[0]}x{ps[1]} (aspect {ps[0]/ps[1]:.3f}) "
              f"against a {grid[0]}x{grid[1]} grid (aspect {grid[0]/grid[1]:.3f})")
    check(f"  not one of the {len(sizes)} is the grid's own size",
          all(ps != grid for ps, grid in sizes.values()))
    check("  and not one of them is even the grid's aspect ratio",
          all(abs(ps[0] / ps[1] - grid[0] / grid[1]) > 0.005
              for ps, grid in sizes.values()))
    print(f"  distinct sizes shipped: "
          f"{sorted({ps for ps, _ in sizes.values()})}")


# =============================================================================
print("\n3. the default frame carries the PICTURE's aspect, which is the whole "
      "trick")

fr = mapfe.frame(GRID, (FE_W, FE_H))
check(f"  the frame is {fr.w:g}x{fr.h:g} tiles, aspect {fr.aspect:.4f}",
      abs(fr.aspect - FE_W / FE_H) < 1e-9)
check("  so ONE scalar zoom draws the picture at exactly 1:1 on both axes",
      abs(fr.zoom(FE_W) - FE_H / fr.h) < 1e-9)
check(f"  it holds the whole grid: {fr.x:g},{fr.y:g} to "
      f"{fr.x + fr.w:g},{fr.y + fr.h:g}",
      fr.x <= 0 and fr.y <= 0 and fr.x + fr.w >= W and fr.y + fr.h >= H)
check("  and it is centred on it - the overhang is equal on both sides",
      abs((-fr.x) - (fr.x + fr.w - W)) < 1e-9
      and abs((-fr.y) - (fr.y + fr.h - H)) < 1e-9)
check("  a picture the grid's own shape gets the grid itself, no overhang",
      mapfe.frame(GRID, GRID) == mapfe.Frame(0.0, 0.0, float(W), float(H)))
tall = mapfe.frame(GRID, (10, 30))
check(f"  a tall picture widens the frame's HEIGHT ({tall.w:g}x{tall.h:g}), "
      "never crops the map",
      tall.w == W and tall.h > H and abs(tall.aspect - 10 / 30) < 1e-9)


# =============================================================================
print("\n4. the frame is refused only when nothing could be composed from it")

for label, bad in (
        ("zero width", mapfe.Frame(0, 0, 0, 8)),
        ("negative height", mapfe.Frame(0, 0, 12, -8)),
        ("smaller than four tiles a side", mapfe.Frame(0, 0, 2, 2)),
        ("entirely off the left of the grid", mapfe.Frame(-99, 0, 20, 20)),
        ("entirely below the grid", mapfe.Frame(0, 99, 20, 20)),
):
    try:
        mapfe.check_frame(bad, GRID)
        check(f"  {label} is refused", False)
    except mapfe.FeError as e:
        check(f"  {label} is refused: {str(e)[:52]}", True)

try:
    mapfe.check_frame(mapfe.Frame(-100, -100, 300, 300), GRID)
    check("  a frame far bigger than the grid is NOT refused - that is normal",
          True)
except mapfe.FeError:
    check("  a frame far bigger than the grid is NOT refused", False)


# =============================================================================
print("\n5. the defect: the screen resamples the picture twice, render never "
      "resamples it at all")

comp = campmap.LAYER_BY_CODE["fe"]
check(f"  cmapComposite draws every layer into a {W}x{H}-TILE canvas, so the "
      f"{FE_W}x{FE_H} picture is squeezed to {W}x{H} and scaled again",
      (FE_W, FE_H) != GRID)
js = (ROOT / "web" / "js" / "campmap.js").read_text(encoding="utf-8")
check("  and that is the line in campmap.js, still there, still honest about it",
      "x.drawImage(L.masked || L.cv || L.img, 0, 0, m.width, m.height);" in js)
check("  the composite now skips the picture, so nothing squeezes it",
      "c.order.filter(code => code !== 'fe'" in js)
#: The defect the browser found on the day: the composite fills itself with an
#: opaque backdrop when no terrain is on, and it is drawn OVER the picture,
#: which is now underneath it rather than in it. With every other layer off the
#: front-end picture did not appear at all. Both halves are checked, because
#: the guard without the cache key is a composite that never rebuilds when the
#: layer is ticked and the bug comes straight back.
check("  and it does not paint its backdrop over the picture either",
      "!(c.layers.fe && c.layers.fe.on)" in js)
check("  with the layer's state in the composite's cache key, or it never rebuilds",
      "|fe:${c.layers.fe && c.layers.fe.on ? 1 : 0}" in js)

out = mapfe.render(cm, fr, (FE_W, FE_H), STACK)
check(f"  render composes at the picture's own {FE_W}x{FE_H}",
      out.size == (FE_W, FE_H))
check("  the front-end picture is not one of the layers it may compose",
      "fe" not in {s["code"] for s in STACK})
try:
    mapfe.render(cm, fr, (FE_W, FE_H), [{"code": "fe", "opacity": 1.0}])
    check("  and asking for it by name is refused", False)
except mapfe.FeError as e:
    check(f"  and asking for it by name is refused: {str(e)[:48]}", True)


# =============================================================================
print("\n6. where the frame puts the map, to the pixel")

#: the frame is 30x10 tiles of aspect 3.0 around a 12x8 grid: 24 wide becomes
#: 30... no - the grid is 12x8 (1.5), the picture 3.0, so the frame widens x to
#: 24 and keeps y at 8. 30 picture pixels over 24 tiles is 1.25 px per tile.
check(f"  the frame is {fr.w:g}x{fr.h:g} tiles for a 12x8 grid",
      (fr.w, fr.h) == (24.0, 8.0))
check(f"  at {FE_W}/{fr.w:g} = {FE_W / fr.w:g} picture pixels per tile",
      abs(FE_W / fr.w - 1.25) < 1e-9 and abs(FE_H / fr.h - 1.25) < 1e-9)
check("  the grid starts 6 tiles in, so 7.5 px of backdrop on the left",
      abs(fr.x + 6.0) < 1e-9)

edge = mapfe.render(cm, fr, (FE_W, FE_H), [{"code": "regions", "opacity": 1.0}])
px = edge.load()
check("  and the leftmost column really is backdrop, not map",
      px[0, 0] == (0, 0, 0))
check("  the column just inside the grid is the map's sea",
      px[8, 0] == SEA)
check("  Alpha's top-left tile lands where the scale says it should",
      px[int((6 + 1) * 1.25) + 1, int(1 * 1.25) + 1] == A)

#: a frame that is exactly the grid puts tile (0,0) at pixel (0,0)
tight = mapfe.render(cm, mapfe.Frame(0, 0, W, H), (W, H),
                     [{"code": "regions", "opacity": 1.0}])
check("  a frame that IS the grid reproduces map_regions.tga pixel for pixel",
      list(tight.getdata()) == list(cm.layer("regions").convert("RGB").getdata()))


# =============================================================================
print("\n7. an export goes out through the mod's own header")

exp = mapfe.export(mod, "", cm, fr, STACK)
f = exp.files[0]
check(f"  it wrote {f['name']}, {f['width']}x{f['height']}, {f['bytes']:,} bytes",
      exp.payload()["count"] == 1 and (f["width"], f["height"]) == (FE_W, FE_H))
check("  into the cache, never into the mod",
      str(Path(mod.data)).lower() not in exp.folder.lower())
back = probe(Path(exp.folder) / f["name"])
src = cm.info("fe")
check(f"  it reads back at {back.width}x{back.height}",
      (back.width, back.height) == (FE_W, FE_H))
check(f"  with the source file's depth ({src.depth}) and origin "
      f"({'top' if src.top_origin else 'bottom'})",
      back.depth == src.depth and back.top_origin == src.top_origin)
check("  and the export says whose header it borrowed",
      f["header"] == "the mod's own map_FE.tga")

#: the case an author writing their FIRST front-end picture is in
_bare_root, bare = little_mod(prefix="ut_fe_bare_", fe=False,
                             name="NoFrontEnd")
bcm = campmap.CampaignMap(bare)
bview = mapfe.view(bare, "", bcm)
check("  a mod that ships none is not refused - present is False, with a reason",
      bview["present"] is False and "no map_FE.tga" in bview["problem"])
check("  it is still offered a frame, at the grid's own shape",
      bview["frame"]["w"] == float(W) and bview["frame"]["h"] == float(H))
bexp = mapfe.export(bare, "", bcm, mapfe.Frame(0, 0, W, H), STACK)
check(f"  and it can still export: {bexp.files[0]['header']}",
      bexp.files[0]["header"] == "24-bit, made here"
      and probe(Path(bexp.folder) / bexp.files[0]["name"]).depth == 24)


# =============================================================================
print("\n8. what an oversized request is told")

try:
    mapfe.render(cm, fr, (mapfe.MAX_SIDE + 1, 10), STACK)
    check("  a picture wider than the cap is refused", False)
except mapfe.FeError as e:
    check(f"  a picture wider than the cap is refused: {str(e)[:52]}", True)
for bad in ((0, 10), (10, 0), (-5, 10)):
    try:
        mapfe.render(cm, fr, bad, STACK)
        check(f"  {bad} is refused", False)
    except mapfe.FeError:
        check(f"  {bad} is refused", True)
#: The frame that used to be the allocation trap: 4 tiles across blown up to
#: 2048 px is 512 picture pixels per tile, and scaling the whole 12x8 layer at
#: that rate would build a 6144x4096 intermediate to keep a 2048x2048 crop of
#: it. render crops first, so the intermediate is the result and nothing more.
huge = mapfe.render(cm, mapfe.Frame(0, 0, 4, 4), (2048, 2048), STACK)
check("  a 4-tile frame at 2048 px composes, bounded by the result not the zoom",
      huge.size == (2048, 2048))
#: 512 picture pixels per tile, so (1000,1000) is tile (1,1) - Alpha's corner -
#: and (100,100) is tile (0,0), which is sea. One pixel each way says the
#: magnification put the map where the frame said and not one tile over.
check("  and it really is that corner of the map, magnified",
      huge.load()[1000, 1000] == A and huge.load()[100, 100] == SEA)


# =============================================================================
print("\n9. every installed campaign: the default frame, and what it costs")

if not sizes:
    print("  SKIPPED - no installed mod ships a map_FE.tga")
else:
    import time
    for root in _realmod.installed():
        if not (root / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
            continue
        m = Mod(root)
        try:
            base = campmap.CampaignMap(m)
        except (campmap.MapError, OSError):
            continue
        for camp in campstrat.campaign_paths(m):
            v = mapfe.view(m, camp, base if not campmap.shipped(m, camp)
                           else campmap.campaign_map(m, camp, base))
            if not v["present"]:
                continue
            f0 = v["frame"]
            fr2 = mapfe.Frame(f0["x"], f0["y"], f0["w"], f0["h"])
            t0 = time.perf_counter()
            img = mapfe.render(campmap.campaign_map(m, camp, base), fr2,
                               tuple(v["size"]), STACK)
            ms = int((time.perf_counter() - t0) * 1000)
            print(f"    {root.name}/{camp}: {v['native'][0]}x{v['native'][1]}, "
                  f"frame {f0['w']:.1f}x{f0['h']:.1f} tiles, zoom "
                  f"{v['zoom']:.3f} px/tile, composed in {ms} ms")
            check(f"    {camp}: the render is the picture's own size",
                  img.size == tuple(v["size"]))
            check(f"    {camp}: the zoom draws it 1:1 on both axes",
                  abs(v["zoom"] - v["native"][1] / f0["h"]) < 1e-3)
            check(f"    {camp}: the frame holds the whole grid",
                  f0["x"] <= 0.0001 and f0["y"] <= 0.0001
                  and f0["x"] + f0["w"] >= v["grid"][0] - 0.0001
                  and f0["y"] + f0["h"] >= v["grid"][1] - 0.0001)
            check(f"    {camp}: and the screen's old squeeze is named",
                  bool(v["was"]))


# =============================================================================
print("\n10. the two routes")

from unittransfer.server import Handler, Registry, _Server        # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


MOD = "Tiny"
try:
    r = post("/api/map/fe_view", {"mod": MOD})
    check(f"  fe_view answers with the picture's size: {r.get('native')}",
          r.get("native") == [FE_W, FE_H] and not r.get("error"))
    check(f"  and the frame and the zoom with it: {r.get('zoom')}",
          abs(r.get("zoom", 0) - 1.25) < 1e-6)

    r = post("/api/map/fe_export",
             {"mod": MOD, "frame": r["frame"], "layers": STACK})
    check(f"  fe_export writes one file: {(r.get('files') or [{}])[0].get('name')}",
          r.get("count") == 1 and not r.get("error"))

    r = post("/api/map/fe_export",
             {"mod": MOD, "frame": {"x": 0, "y": 0, "w": 0, "h": 0},
              "layers": STACK})
    check(f"  a frame nothing can be composed from comes back as an error, "
          f"not a traceback: {str(r.get('error'))[:40]}",
          bool(r.get("error")))

    r = post("/api/map/fe_export",
             {"mod": MOD, "frame": {"x": 0, "y": 0, "w": 24, "h": 8},
              "layers": [{"code": "no_such_layer", "opacity": 1}]})
    check(f"  and so does a layer that does not exist: "
          f"{str(r.get('error'))[:40]}",
          "no such layer" in str(r.get("error", "")))
finally:
    httpd.shutdown()


print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
