"""The campaign map renderer's engine - Phase 16c's exit criteria, measured.

16a read the map; this is what the browser is handed. Three things under test:

    campmap.tile_view / layer_png    the projection and the PNG
    campmap.view                     the manifest the renderer opens on
    /api/map, /api/map/layer         the two routes, over real HTTP

The load-bearing claim of the whole picking design is checked here rather than
argued: **the colour the browser reads off a layer PNG is the colour the Python
index is built on**. Picking a region in the browser is one lookup in the
manifest's table by packed RGB key, with no round trip and no second parser, and
that is only sound if the two agree pixel for pixel. So every region on every
installed map is checked at its own anchor.

Four halves, the last two of which need a real game install:

    1  the projection, on grids written here
    2  the manifest and its refusals, on grids written here
    3  every real map: vanilla's and every installed mod's
    4  the two HTTP routes, against a throwaway mod

    python -m tests.test_campview
"""
import io
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod
from unittransfer import campmap, config, maptga, mapvocab
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def png_pixels(data: bytes) -> Image.Image:
    """A PNG as the browser would decode it - RGB, no alpha to disagree over."""
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGB")


# ---- 1) the projection, on grids written here -------------------------------
print("\n1) one pixel per tile, sampled the way the engine samples it")

#: A 4x3 tile map. Each layer below is painted so that the value at a tile is
#: derivable from the tile alone, which is what makes a wrong sample visible
#: rather than merely different.
W, H = 4, 3


def paint(w, h, fn):
    im = Image.new("RGB", (w, h))
    im.putdata([fn(x, y) for y in range(h) for x in range(w)])
    return im


class FakeMap:
    """Just enough of :class:`campmap.CampaignMap` for the projection tests."""

    def __init__(self, imgs):
        self.imgs = imgs
        self.terrain = campmap.Terrain(width=W, height=H)
        self.base = Path("nowhere")

    def layer(self, code):
        return self.imgs[code]

    def centres(self, code):
        return campmap.CampaignMap.centres(self, code)


# a 2W+1 layer whose every pixel encodes its own position, so only the right
# sample lands on the value the tile is supposed to have
centre_layer = paint(2 * W + 1, 2 * H + 1, lambda x, y: (x * 10, y * 10, 0))
# a 2W x 2H layer, same trick
double_layer = paint(2 * W, 2 * H, lambda x, y: (x * 10, y * 10, 0))
tile_layer = paint(W, H, lambda x, y: (x, y, 7))

fm = FakeMap({"heights": centre_layer, "roughness": double_layer,
              "regions": tile_layer, "water_surface": paint(9, 9, lambda x, y: (1, 2, 3))})

got = campmap.tile_view(fm, "heights")
check(f"a 2W+1 layer comes back {W}x{H}", got.size == (W, H))
check("and it is sampled at the BLOCK CENTRE, (2t+1, 2t+1)",
      [got.getpixel((x, y)) for y in range(H) for x in range(W)]
      == [((2 * x + 1) * 10, (2 * y + 1) * 10, 0) for y in range(H) for x in range(W)])
check("corner sampling would have given a different answer, so the check bites",
      got.getpixel((1, 1)) != centre_layer.getpixel((2, 2)))

got = campmap.tile_view(fm, "roughness")
check(f"a 2W x 2H layer comes back {W}x{H}, sampled at the block's top-left",
      got.size == (W, H)
      and [got.getpixel((x, 0)) for x in range(W)] == [(x * 20, 0, 0) for x in range(W)])

got = campmap.tile_view(fm, "regions")
check("a W x H layer is handed back untouched",
      got.size == (W, H) and got.tobytes() == tile_layer.tobytes())

got = campmap.tile_view(fm, "water_surface")
check("a layer with no relationship to the grid keeps its own size",
      got.size == (9, 9))

# ---- 2) the PNG, and the refusals -------------------------------------------
print("\n2) the PNG the browser is handed")

data = campmap.layer_png(fm, "heights", "tile")
check("PNG magic", data[:8] == b"\x89PNG\r\n\x1a\n")
back = png_pixels(data)
check("it decodes to exactly the projected pixels",
      back.size == (W, H) and back.tobytes() == campmap.tile_view(fm, "heights").tobytes())
native = png_pixels(campmap.layer_png(fm, "heights", "native"))
check("native fit is the layer's own pixels, untouched",
      native.size == centre_layer.size and native.tobytes() == centre_layer.tobytes())

for bad, why in ((("nosuch", "tile"), "layer"), (("heights", "sideways"), "fit")):
    try:
        campmap.layer_png(fm, *bad)
        check(f"an unknown {why} is refused", False)
    except campmap.MapError as exc:
        check(f"an unknown {why} is refused, by name: {exc}", bad[0 if why == "layer" else 1] in str(exc))

# a 32-bit layer with an alpha channel must still hand the browser three numbers,
# because the colour tables and the region index are keyed on three
rgba = Image.new("RGBA", (W, H), (10, 20, 30, 128))
check("an RGBA layer is served as RGB - a fourth number nothing agrees on",
      png_pixels(campmap.layer_png(FakeMap({"regions": rgba}), "regions", "tile"))
      .getpixel((0, 0)) == (10, 20, 30))

# ---- 3) every real map -------------------------------------------------------
print("\n3) vanilla's map and every installed mod's")

roots = []
game = _realmod.MODS.parent
if (game / "data" / campmap.REGIONS_REL).exists():
    roots.append(game)
roots += [m for m in _realmod.installed()
          if (m / "data" / campmap.REGIONS_REL).exists()]

if not roots:
    print(f"  SKIPPED - nothing with {campmap.REGIONS_REL} under {_realmod.MODS}")
else:
    for root in roots:
        mod = Mod(root)
        print(f"\n  -- {mod.name}")
        cm = campmap.CampaignMap(mod)
        t0 = time.perf_counter()
        man = campmap.view(cm, mod.name)
        built = (time.perf_counter() - t0) * 1000
        size = len(json.dumps(man))
        check(f"the manifest builds in {built:.0f} ms and is {size / 1024:.0f} KB "
              f"({man['width']}x{man['height']}, {len(man['regions'])} regions)",
              man["width"] > 0 and man["regions"] and size < 400_000)
        check("it declares all ten layers, in draw order",
              len(man["layers"]) == len(campmap.LAYERS)
              and [l["order"] for l in man["layers"]]
              == sorted(l["order"] for l in man["layers"]))

        aligned = [l for l in man["layers"] if l["present"] and l["aligned"]]
        check(f"every layer on the tile grid is served at {man['width']}x{man['height']} "
              f"({len(aligned)} of {sum(1 for l in man['layers'] if l['present'])} present)",
              all(l["fit"] == "tile" and (l["width"], l["height"])
                  == (man["width"], man["height"]) for l in aligned))
        loose = [l for l in man["layers"] if l["present"] and not l["aligned"]]
        check(f"and the ones that are not say so rather than being stretched by the "
              f"server ({', '.join(l['code'] for l in loose) or 'none'})",
              all(l["fit"] == "native" and (l["width"], l["height"]) == tuple(l["native"])
                  for l in loose))

        t0 = time.perf_counter()
        sizes = {}
        for l in man["layers"]:
            if not l["present"]:
                continue
            blob = campmap.layer_png(cm, l["code"], l["fit"])
            sizes[l["code"]] = len(blob)
            img = png_pixels(blob)
            if img.size != (l["width"], l["height"]):
                sizes[l["code"]] = -1
        encoded = (time.perf_counter() - t0) * 1000
        check(f"all {len(sizes)} layers encode to a PNG of the size the manifest "
              f"promised, in {encoded:.0f} ms, {sum(sizes.values()) / 1024:.0f} KB total",
              all(v > 0 for v in sizes.values()))

        # THE claim the picking design rests on
        regions = png_pixels(campmap.layer_png(cm, "regions", "tile"))
        by_key = {r["key"]: r for r in man["regions"]}
        wrong = []
        for r in man["regions"]:
            if not r["pixels"]:
                continue
            px = regions.getpixel(tuple(r["anchor"]))
            k = (px[0] << 16) | (px[1] << 8) | px[2]
            if by_key.get(k) is not r:
                wrong.append((r["name"] or r["rgb"], px))
        check(f"every region's anchor pixel in the served PNG looks up to that same "
              f"region in the manifest's table ({len(man['regions'])} regions"
              f"{'' if not wrong else ', wrong: ' + str(wrong[:3])})", not wrong)

        idx = cm.index
        check("the markers the manifest names are the markers the index used",
              tuple(man["markers"]["settlement"]) == mapvocab.SETTLEMENT_RGB
              and tuple(man["markers"]["port"]) == mapvocab.PORT_RGB)
        check(f"every settlement and port pixel is on the region it belongs to "
              f"({len(idx.settlements)} settlements, {len(idx.ports)} ports)",
              all(regions.getpixel(tuple(r["settlement"])) == mapvocab.SETTLEMENT_RGB
                  for r in man["regions"] if r["settlement"])
              and all(regions.getpixel(tuple(r["port"])) == mapvocab.PORT_RGB
                      for r in man["regions"] if r["port"]))

        ids = [r["id"] for r in man["regions"] if r["id"] >= 0]
        check(f"regions come out in engine order, ids 0..{len(ids) - 1}",
              ids == sorted(ids) and ids == list(range(len(ids))))

        # the sea count, which is what tells the ocean from a hole in the mod
        f = man["findings"]
        seaish = [r for r in man["regions"]
                  if not r["declared"] and r["pixels"] and r["sea"] * 2 >= r["pixels"]]
        holes = f["undeclared_land"]
        check(f"{f['sea_colours']} undeclared colour(s) are sea, "
              f"{len(holes)} are land the game has no region for",
              f["sea_colours"] == len(seaish)
              and f["sea_colours"] + len(holes)
              == sum(1 for r in man["regions"] if not r["declared"]))
        for h in holes:
            print(f"          hole: rgb{tuple(h['rgb'])}, {h['pixels']} tiles at "
                  f"{h['bbox']}, {h['sea']} of them sea")

        if mod.name.lower().startswith("divide_and_conquer"):
            print("    (DaC: the numbers 16c was measured against)")
            check("510x487, 200 numbered regions", (man["width"], man["height"]) == (510, 487)
                  and len(ids) == 200)
            check("the ocean is one undeclared colour, 73,904 of its 73,950 tiles sea",
                  any(r["pixels"] == 73950 and r["sea"] == 73904 and not r["declared"]
                      for r in man["regions"]))
            check("and the other undeclared colour is the 517-tile province with "
                  "NOT ONE sea tile in it - the hole 16a found, now measured",
                  [(h["rgb"], h["pixels"], h["sea"]) for h in holes]
                  == [[100, 160, 100], 517, 0] or
                  [(tuple(h["rgb"]), h["pixels"], h["sea"]) for h in holes]
                  == [((100, 160, 100), 517, 0)])
            check("water_surface is 1021x975 and is NOT claimed to be on the grid",
                  any(l["code"] == "water_surface" and l["native"] == [1021, 975]
                      and not l["aligned"] for l in man["layers"]))

        if mod.name.lower().startswith("total war medieval"):
            print("    (vanilla: a second real map, a different size)")
            check("295x189", (man["width"], man["height"]) == (295, 189))
            check("all four of its undeclared colours are sea - three of them "
                  "one-channel misses of the ocean's own (41,140,233)",
                  f["sea_colours"] == 4 and not holes)

# ---- 4) the two routes, over real HTTP ---------------------------------------
print("\n4) /api/map and /api/map/layer")

if not roots:
    print("  SKIPPED - no map to serve")
else:
    src = roots[-1]
    cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"

    med2 = Path(tempfile.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "MapMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for p in (src / "data" / campmap.BASE_REL).iterdir():
        if p.is_file() and p.name != "map.rwm":
            shutil.copy2(p, data / campmap.BASE_REL / p.name)
    # a second mod with a data/ and no map at all: the ordinary case, and it has
    # to answer with a sentence rather than an empty screen
    (med2 / "mods" / "NoMapMod" / "data").mkdir(parents=True)
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} · map copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def raw(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return r.read(), dict(r.headers)

    def status(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=300) as r:
                return r.status, ""
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8")).get("error", "")
            except Exception:
                return e.code, ""

    try:
        t0 = time.perf_counter()
        man = get("/api/map?mod=MapMod")
        cold = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        again = get("/api/map?mod=MapMod")
        warm = (time.perf_counter() - t0) * 1000
        check(f"/api/map answers the manifest in {cold:.0f} ms cold, {warm:.0f} ms warm "
              f"- the index is read once and kept",
              man["width"] > 0 and again == man and warm < cold)

        blob, hdr = raw("/api/map/layer?mod=MapMod&code=regions")
        check("/api/map/layer defaults to tile fit and says which it served",
              blob[:8] == b"\x89PNG\r\n\x1a\n" and hdr.get("X-Map-Fit") == "tile"
              and hdr.get("Content-Type") == "image/png")
        img = png_pixels(blob)
        check(f"and it is the tile grid, {img.size[0]}x{img.size[1]}",
              img.size == (man["width"], man["height"]))

        t0 = time.perf_counter()
        blob2, _ = raw("/api/map/layer?mod=MapMod&code=regions")
        cached = (time.perf_counter() - t0) * 1000
        check(f"the same layer again is byte-identical, off the disk cache "
              f"({cached:.0f} ms)", blob2 == blob)

        nat, hdr = raw("/api/map/layer?mod=MapMod&code=heights&fit=native")
        want = maptga.probe(data / campmap.BASE_REL / "map_heights.tga")
        check(f"native fit serves the file's own {want.width}x{want.height}",
              png_pixels(nat).size == (want.width, want.height)
              and hdr.get("X-Map-Fit") == "native")

        code, why = status("/api/map?mod=NoMapMod")
        check(f"a mod with no map is a 404 carrying the reason ({code})",
              code == 404 and len(why) > 10)
        print(f"          it said: {why[:100]}")
        check("an unknown mod is a 404", status("/api/map?mod=Nope")[0] == 404)
        check("an unknown layer is a 404 naming it",
              status("/api/map/layer?mod=MapMod&code=nosuch")
              == (404, "no such layer 'nosuch'"))
        code, why = status("/api/map/layer?mod=MapMod&code=regions&fit=sideways")
        check(f"an unknown fit is a 400 listing the ones there are: {why}",
              code == 400 and "tile" in why and "native" in why)

        # a layer the mod does not ship: refused by name, not served blank. An
        # icon may fall back to a placeholder; a map layer may not, because a
        # blank one reads as a map with nothing on it.
        (data / campmap.BASE_REL / "map_fog.tga").unlink(missing_ok=True)
        Handler.registry.invalidate("MapMod")
        code, why = status("/api/map/layer?mod=MapMod&code=fog")
        check(f"a layer the mod does not ship is refused by name, never blank ({code})",
              code == 404 and "map_fog.tga" in why)
        check("and the manifest already said so, so the screen never asks",
              any(l["code"] == "fog" and not l["present"] and l["problem"]
                  for l in get("/api/map?mod=MapMod")["layers"]))

        # a layer the wrong shape is the classic map crash. Serving it at tile
        # fit would hide it: it would come back the right size with its pixels
        # silently off the grid.
        Image.new("RGB", (7, 5)).save(data / campmap.BASE_REL / "map_features.tga")
        Handler.registry.invalidate("MapMod")
        bad = next(l for l in get("/api/map?mod=MapMod")["layers"]
                   if l["code"] == "features")
        check(f"a layer the wrong shape is reported, not reshaped: {bad['problem']}",
              bad["present"] and not bad["aligned"] and bad["fit"] == "native"
              and "expected" in bad["problem"])
    finally:
        httpd.shutdown()
    shutil.rmtree(med2, ignore_errors=True)
    shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
