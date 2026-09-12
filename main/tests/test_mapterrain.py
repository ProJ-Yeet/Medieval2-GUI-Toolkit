"""The map drawn with the game's own ground textures (23a, D7 and T1).

    python -m tests.test_mapterrain

One little mod written here, six tiles by four, with every rule of the feature
given a tile of its own so that each one can be read off the picture by
coordinate rather than inferred from a total:

    climate    ground              what should be drawn
    alpine     fertility_medium    a_med.tga, its own entry
    alpine     hills               d_hills.tga, inherited from the default block
    alpine     wilderness          a_low.tga, TWMapReader's fertility_low
                                   substitution
    alpine     impassable_land     gone.tga, which is not on disk: PINK
    medit.     forest_dense        d_dense.tga, inherited, one column, so its
                                   winter is its summer
    medit.     impassable_land     nothing names one anywhere: PINK
    medit.     sea_deep on land    the heights say land and the ground says sea:
                                   PINK, and the finding names the two layers
    (1,2,3)    fertility_medium    a climate colour nobody declared, so the
                                   default block: d_med.tga
    anything   the bottom row      sea by height: SEA_RGB, no texture looked up

Then the winter column and its two fallbacks, the composite's phase (two
neighbouring tiles of one texture continue each other rather than each showing
a copy), the validator's rule, the two routes, and finally every installed mod,
which is where the timings in the module docstring come from.
"""
import json
import sys
import threading
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, mapcheck, mapterrain, mapvocab
from unittransfer.maptga import TgaInfo, encode
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little mod ----------------------------------------------------------

W, H = 6, 4

FM = mapvocab.ground("fertility_medium")["rgb"]
FD = mapvocab.ground("forest_dense")["rgb"]
WL = mapvocab.ground("wilderness")["rgb"]
HI = mapvocab.ground("hills")["rgb"]
IM = mapvocab.ground("impassable_land")["rgb"]
SD = mapvocab.ground("sea_deep")["rgb"]

#: one ground type per tile, read top row first
GROUND = [[FM, FM, HI, WL, IM, FD],
          [FM, FM, FD, IM, SD, FM],
          [FM, FM, FM, FM, FM, FM],
          [FM, FM, FM, FM, FM, FM]]

ALPINE, MEDIT, NOBODY = (200, 100, 50), (60, 160, 60), (1, 2, 3)
CLIMATE = [[ALPINE] * 6, [MEDIT] * 6, [NOBODY] * 6, [ALPINE] * 6]

#: the bottom row is sea, by the only rule that decides it: the heights
SEA_ROW = H - 1

TERRAIN = ("dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
           "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n"
           "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
           "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
           % (W, H))

RECORDS = ("A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t96 160 64\r\n"
           "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n")

#: ``mediterranean`` deliberately has no ``winter`` line, which is the second of
#: the two winter fallbacks: a climate without one is drawn in its summer
#: textures all year, whatever its own block writes in the second column.
CLIMATES_TXT = ("climates\n{\n\talpine\n\tmediterranean\n}\n"
                "climate alpine\n{\n\tcolour 200 100 50\n\theat 1\n\twinter\n}\n"
                "climate mediterranean\n{\n\tcolour 60 160 60\n\theat 4\n}\n")

AERIAL = """;  the default block, which every climate below inherits from
climate default
{
\tfertility_low\t\td_low.tga\t\td_low_w.tga
\tfertility_medium\td_med.tga\t\td_med_w.tga
\tforest_dense\t\td_dense.tga
\thills\t\t\t\td_hills.tga\t\td_hills_w.tga
\tbeach\t\t\t\td_beach.tga
\tcultivated_high\t\td_farm.tga\t\td_farm_w.tga
}

climate alpine ; the one with a block of its own for nearly everything
{
\tfertility_low\t\ta_low.tga\t\ta_low_w.tga
\tfertility_medium\ta_med.tga\t\ta_med_w.tga
\tforest_dense\t\ta_dense.tga\t\ta_dense_w.tga
\timpassable_land\t\tgone.tga\t\tgone.tga
}

climate mediterranean
{
\tfertility_medium\tm_med.tga\t\tm_med_w.tga
}
"""

#: every texture the file names, and the colour each is painted, except
#: ``gone.tga`` - which is named and never written, and is the whole of
#: TWMapReader's pink rule
PAINT = {
    "d_low.tga": (10, 10, 10), "d_low_w.tga": (11, 11, 11),
    "d_med.tga": (20, 20, 20), "d_med_w.tga": (21, 21, 21),
    "d_dense.tga": (30, 30, 30),
    "d_hills.tga": (40, 40, 40), "d_hills_w.tga": (41, 41, 41),
    "d_beach.tga": (50, 50, 50),
    "d_farm.tga": (55, 55, 55), "d_farm_w.tga": (56, 56, 56),
    "a_low.tga": (60, 60, 60), "a_low_w.tga": (61, 61, 61),
    "a_dense.tga": (80, 80, 80), "a_dense_w.tga": (81, 81, 81),
    "m_med.tga": (90, 90, 90), "m_med_w.tga": (91, 91, 91),
}

#: `a_med.tga` is the one that is not a flat colour: a vertical ramp, so that
#: two neighbouring tiles drawn with it can be told apart from two copies of it
TEX_PX = 64


def write_tga(path, img, depth=24, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def flat(rgb, n=TEX_PX):
    return Image.new("RGB", (n, n), rgb)


def ramp(n=TEX_PX):
    im = Image.new("RGB", (n, n))
    im.putdata([(x * 4 % 256, 128, 200) for _ in range(n) for x in range(n)])
    return im


def grid_img(rows, mode="RGB"):
    im = Image.new(mode, (W, H))
    im.putdata([rows[y][x] + ((255,) if mode == "RGBA" else ())
                for y in range(H) for x in range(W)])
    return im


def centre_img(rows, mode="RGB"):
    """A ``2W+1 x 2H+1`` layer whose block centres carry ``rows``.

    Everything else in it is a colour nothing names, deliberately: the centre
    rule is what this feature reads by, and a layer that is uniform per block
    would pass whether the rule was applied or not.
    """
    im = Image.new(mode, (2 * W + 1, 2 * H + 1), (7, 7, 7) + ((255,) if mode == "RGBA" else ()))
    px = im.load()
    for y in range(H):
        for x in range(W):
            px[2 * x + 1, 2 * y + 1] = rows[y][x] + ((255,) if mode == "RGBA" else ())
    return im


def tiny_mod(root: Path) -> Mod:
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(RECORDS.encode("latin-1"))
    write_tga(base / "map_regions.tga", grid_img([[FM] * W for _ in range(H)]))
    write_tga(base / "map_features.tga", grid_img([[(0, 0, 0)] * W for _ in range(H)]))
    write_tga(base / "map_ground_types.tga", centre_img(GROUND))
    write_tga(base / "map_climates.tga", centre_img(CLIMATE))
    heights = [[(0, 0, 200) if y == SEA_ROW else (90, 90, 90) for _ in range(W)]
               for y in range(H)]
    write_tga(base / "map_heights.tga", centre_img(heights))

    data = root / "data"
    (data / mapvocab.CLIMATES_REL).write_text(CLIMATES_TXT, encoding="latin-1")
    (data / mapterrain.AERIAL_REL).write_text(AERIAL, encoding="latin-1")
    tex = data / mapterrain.TEXTURE_DIR_REL
    tex.mkdir(parents=True, exist_ok=True)
    for name, rgb in PAINT.items():
        write_tga(tex / name, flat(rgb))
    write_tga(tex / "a_med.tga", ramp())
    write_tga(tex / "a_med_w.tga", flat((70, 70, 70)))
    camp = data / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
    camp.mkdir(parents=True, exist_ok=True)
    (camp / campstrat.STRAT_NAME).write_bytes(b"campaign imperial_campaign\r\n")
    return Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

med2 = Path(_tmp.mkdtemp(prefix="ut_terrain_"))
mod = tiny_mod(med2 / "mods" / "Tiny")
cm = campmap.CampaignMap(mod)
print(f"  a {W}x{H} map with {len(PAINT) + 2} textures, one of them named and "
      f"never written")


# ---- 1) the file -------------------------------------------------------------
print("\n1) descr_aerial_map_ground_types.txt, as written")

blocks = mapterrain.parse(AERIAL)
check(f"three climate blocks: {sorted(blocks)}",
      sorted(blocks) == ["alpine", "default", "mediterranean"])
check("a line with two textures is (summer, winter)",
      blocks["default"]["fertility_medium"] == ("d_med.tga", "d_med_w.tga"))
check("a line with one is (summer, summer) - the first winter fallback",
      blocks["default"]["forest_dense"] == ("d_dense.tga", "d_dense.tga"))
check("the comment above the first block is not a block, and the } closes one",
      "fertility_medium" not in blocks.get("default", {}).get("hills", "")
      and set(blocks["mediterranean"]) == {"fertility_medium"})
check("a ground type the map can never be - cultivated_high, which the engine "
      "grows at runtime - is parsed and kept rather than dropped",
      blocks["default"]["cultivated_high"] == ("d_farm.tga", "d_farm_w.tga")
      and "cultivated_high" in mapterrain.RUNTIME_GROUND)

v = mapterrain.read_vocabulary(mod)
check(f"the vocabulary reads: present={v.present}, "
      f"climates={[c['code'] for c in v.climates]}",
      v.present and [c["code"] for c in v.climates] == ["alpine", "mediterranean"])
check("a climate's own entry wins",
      v.texture("alpine", "fertility_medium") == "a_med.tga")
check("one it does not name is inherited from the default block",
      v.texture("alpine", "hills") == "d_hills.tga")
check("wilderness is drawn as fertility_low - TWMapReader's substitution",
      v.texture("alpine", "wilderness") == "a_low.tga"
      and v.texture("mediterranean", "wilderness") == "d_low.tga")
check("a climate nothing declares is drawn with the default block",
      v.texture(mapterrain.DEFAULT_CLIMATE, "fertility_medium") == "d_med.tga")
check("a ground type nothing names anywhere has no texture",
      v.texture("mediterranean", "impassable_land") == "")
check("winter takes the second column where the climate has a winter",
      v.texture("alpine", "fertility_medium", "winter") == "a_med_w.tga"
      and v.texture("alpine", "hills", "winter") == "d_hills_w.tga")
check("and the summer one where it has not, whatever the second column says",
      not v.has_winter("mediterranean")
      and v.texture("mediterranean", "fertility_medium", "winter") == "m_med.tga")
check("a one-column line's winter is its summer",
      v.texture("mediterranean", "forest_dense", "winter") == "d_dense.tga")


# ---- 2) which texture each tile asks for -------------------------------------
print("\n2) the plan: one texture per tile, and every reason a tile has none")

p = mapterrain.plan(mod, cm)


def tex_at(plan, tx, ty):
    k = plan.slots.tobytes()[ty * W + tx]
    return plan.names[k - 1] if k else ""


check("its own entry", tex_at(p, 0, 0) == "a_med.tga")
check("the inherited one", tex_at(p, 2, 0) == "d_hills.tga")
check("the wilderness substitution", tex_at(p, 3, 0) == "a_low.tga")
check("a one-column inherited line", tex_at(p, 2, 1) == "d_dense.tga")
check("an undeclared climate colour falls to the default block",
      tex_at(p, 0, 2) == "d_med.tga")
check("a sea tile asks for nothing at all",
      all(tex_at(p, x, SEA_ROW) == "" for x in range(W)))
check(f"{p.used} textures are used out of {len(p.names)} the table could name",
      p.used == 8 and len(p.names) > p.used)

gaps = {(g["climate"], g["ground"], g["file"]): g for g in p.gaps}
check(f"three tiles have no texture, for three different reasons: "
      f"{sorted(k[2] or f'{k[0]}/{k[1]}' for k in gaps)}", len(gaps) == 3)
g = gaps.get(("", "", "gone.tga"))
check("the file names a texture the folder does not hold - TWMapReader's case - "
      "and the finding names the file and a tile it is used on",
      g and g["tiles"] == 1 and g["tile"] == [4, 0]
      and mapterrain.TEXTURE_DIR_REL in g["why"])
g = gaps.get(("mediterranean", "impassable_land", ""))
check("nothing names a texture for this pair, the default block included",
      g and g["tiles"] == 1 and g["tile"] == [3, 1]
      and "no texture for impassable_land" in g["why"])
g = gaps.get(("mediterranean", "sea_deep", ""))
check("and a tile the ground calls sea and the heights call land is named as "
      "the quarrel it is, rather than as a hole in the texture table",
      g and g["tiles"] == 1 and g["tile"] == [4, 1]
      and "map_heights.tga calls it land" in g["why"]
      and mapterrain.AERIAL_REL in g["why"])
check(f"{p.pink} tiles will be pink, and no other land tile will be",
      p.pink == 3)
check("nothing in the folder fails to read", not mapterrain.check_textures(mod, p))

pw = mapterrain.plan(mod, cm, season="winter")
check("the winter plan takes the second column, and leaves a climate with no "
      "winter on its summer",
      tex_at(pw, 0, 0) == "a_med_w.tga" and tex_at(pw, 0, 1) == "m_med.tga"
      and tex_at(pw, 2, 1) == "d_dense.tga")
check("and it is a different plan with a different key",
      pw.key != p.key and mapterrain.plan(mod, cm) is p)
try:
    mapterrain.plan(mod, cm, season="autumn")
    check("a season nobody has is refused", False)
except mapterrain.TerrainError as exc:
    check(f"a season nobody has is refused: {exc}", "summer" in str(exc))


# ---- 3) the picture ----------------------------------------------------------
print("\n3) the composite, one pixel at a time")

S = mapterrain.SCALE
comp = mapterrain.composite(mod, p)
px = comp.load()
check(f"it is {comp.width}x{comp.height} - {S} pixels a tile",
      comp.size == (W * S, H * S))


def tile_px(tx, ty, dx=0, dy=0):
    return px[tx * S + dx, ty * S + dy]


check("a flat texture lands as itself, everywhere in its tile",
      all(tile_px(2, 0, dx, dy) == PAINT["d_hills.tga"]
          for dx in range(S) for dy in range(S)))
check("the substitution is drawn, not skipped",
      tile_px(3, 0) == PAINT["a_low.tga"])
check("the inherited one-column line is drawn",
      tile_px(2, 1) == PAINT["d_dense.tga"])
check("an undeclared climate's tile is drawn with the default block's texture",
      tile_px(0, 2) == PAINT["d_med.tga"])
check(f"a tile whose texture is not on disk is rgb{mapterrain.MISSING_RGB}, "
      f"every pixel of it",
      all(tile_px(4, 0, dx, dy) == mapterrain.MISSING_RGB
          for dx in range(S) for dy in range(S)))
check("so is one nothing names a texture for",
      tile_px(3, 1) == mapterrain.MISSING_RGB)
check("and so is the tile the two layers disagree about",
      tile_px(4, 1) == mapterrain.MISSING_RGB)
check(f"every sea tile is rgb{mapterrain.SEA_RGB}",
      all(tile_px(x, SEA_ROW, dx, dy) == mapterrain.SEA_RGB
          for x in range(W) for dx in range(S) for dy in range(S)))

# the phase. `a_med.tga` is a ramp, so two neighbouring tiles of it are two
# different parts of one repeat rather than two copies of the same square.
left, right = [tile_px(0, 0, dx) for dx in range(S)], [tile_px(1, 0, dx) for dx in range(S)]
check(f"two neighbouring tiles of one texture continue each other rather than "
      f"repeating it: {left[0]} then {right[0]}", left != right)
check("and the repeat is anchored to the map, so the texture's own width "
      f"({TEX_PX * S // mapterrain.TEXTURE_SPAN} pixels here) is where it comes "
      f"round again",
      TEX_PX * S // mapterrain.TEXTURE_SPAN == 8 and left + right
      == [px[x, 0] for x in range(2 * S)])

vw = mapterrain.view(mod, cm)
check(f"the screen is told: {vw['textures']} textures, {vw['pink_tiles']} pink "
      f"tiles, {vw['width']}x{vw['height']} at {vw['scale']} a tile",
      vw["have"] and vw["textures"] == 8 and vw["pink_tiles"] == 3
      and vw["width"] == W * S and len(vw["gaps"]) == 3)

# and a mod with no aerial file at all turns the whole thing off by name
bare = Path(_tmp.mkdtemp(prefix="ut_bare_"))
bare_mod = tiny_mod(bare / "mods" / "Bare")
(bare_mod.data / mapterrain.AERIAL_REL).unlink()
bv = mapterrain.view(bare_mod, campmap.CampaignMap(bare_mod))
check(f"a mod with no {mapterrain.AERIAL_REL} is told so by name, rather than "
      f"drawn blank: {bv['problem'][:60]}...",
      not bv["have"] and mapterrain.AERIAL_REL in bv["problem"]
      and not bv["vocabulary"]["present"])


# ---- 4) the validator --------------------------------------------------------
print("\n4) the validator's rule, which is what the Check panel shows")

rep = mapcheck.run(mod, cm, use_baseline=False)
found = [f for f in rep.findings if f.code == "terrain.texture"]
check(f"three findings, one per pink reason: {[f.count for f in found]}",
      len(found) == 3 and not rep.failed)
check("each names a tile to jump to and how many tiles it stands for",
      all(f.tile and f.count == 1 for f in found))
files = {f.file for f in found}
check(f"and the file to open, which is not always the texture table: {sorted(files)}",
      f"{mapterrain.TEXTURE_DIR_REL}/gone.tga" in files
      and mapterrain.AERIAL_REL in files
      and f"{campmap.BASE_REL}/map_ground_types.tga" in files)
check("every finding says the tiles are drawn pink rather than left out",
      all("255, 0, 255" in f.message for f in found))

bare_rep = mapcheck.run(bare_mod, use_baseline=False)
check("a mod with no texture table skips the rule by name instead of reporting "
      "every tile",
      not [f for f in bare_rep.findings if f.code == "terrain.texture"]
      and any(s["what"] == mapterrain.AERIAL_REL for s in bare_rep.skipped))


# ---- 5) the routes -----------------------------------------------------------
print("\n5) /api/map/terrain, as facts and as a picture")

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return r.read(), dict(r.headers)


try:
    facts = get("/api/map/terrain?mod=Tiny")
    check(f"the facts come back without the picture: {facts['textures']} "
          f"textures, {facts['pink_tiles']} pink",
          facts["have"] and facts["textures"] == 8 and facts["pink_tiles"] == 3
          and facts["scale"] == S and len(facts["gaps"]) == 3)
    body, head = raw("/api/map/terrain?mod=Tiny&format=png")
    got = Image.open(__import__("io").BytesIO(body)).convert("RGB")
    check(f"and the picture is a {got.width}x{got.height} PNG with the same "
          f"pixels the module built",
          head.get("Content-Type") == "image/png" and got.size == comp.size
          and got.tobytes() == comp.tobytes()
          and head.get("X-Map-Scale") == str(S))
    body2, _ = raw("/api/map/terrain?mod=Tiny&format=png")
    check("served again out of the disk cache, byte for byte", body2 == body)
    winter = get("/api/map/terrain?mod=Tiny&season=winter")
    check("the winter set is its own answer",
          winter["season"] == "winter" and winter["have"])
    try:
        get("/api/map/terrain?mod=Nope")
        check("an unknown mod is refused", False)
    except urllib.error.HTTPError as exc:
        check(f"an unknown mod is refused with {exc.code}", exc.code == 404)
finally:
    httpd.shutdown()


# ---- 6) every installed mod --------------------------------------------------
print("\n6) every installed mod with a map and a texture table")

seen = 0
for root in _realmod.installed():
    rmod = Mod(root)
    if not (rmod.data / campmap.BASE_REL / "descr_terrain.txt").exists():
        continue
    if not (rmod.data / mapterrain.AERIAL_REL).is_file():
        print(f"  -- {root.name}: no {mapterrain.AERIAL_REL}, nothing to draw")
        continue
    seen += 1
    rcm = campmap.CampaignMap(rmod)
    import time
    # the campaign the validator asks for, so the rule below shares this plan
    # rather than measuring a second one
    t0 = time.perf_counter()
    rp = mapterrain.plan(rmod, rcm, campstrat.DEFAULT_CAMPAIGN)
    plan_ms = int((time.perf_counter() - t0) * 1000)
    t0 = time.perf_counter()
    rimg = mapterrain.composite(rmod, rp)
    draw_ms = int((time.perf_counter() - t0) * 1000)
    tiles = rp.width * rp.height
    print(f"  -- {root.name}: {rp.width}x{rp.height} tiles, {rp.used} textures, "
          f"plan {plan_ms} ms, draw {draw_ms} ms")
    check(f"     the composite is {rimg.width}x{rimg.height} and every tile of "
          f"it is drawn or counted",
          rimg.size == (rp.width * S, rp.height * S))
    pink = (rimg.getcolors(1 << 16) or [])
    drawn = dict((c, n) for n, c in pink).get(mapterrain.MISSING_RGB, 0)
    check(f"     {rp.pink:,} of {tiles:,} tiles have no texture, and the "
          f"picture has {drawn // (S * S):,} pink tiles' worth of pixels",
          drawn == rp.pink * S * S)
    check(f"     every texture it draws with is really in "
          f"{mapterrain.TEXTURE_DIR_REL}",
          all((mapterrain.texture_dir(rmod) / n).is_file()
              for n, c in zip(rp.names, rp.counts)
              if c and not any(g["file"] == n for g in rp.gaps)))
    # the C index against the tile-at-a-time one, on a real map with a real
    # vocabulary. Exactness is the whole claim of the fast path, and a map with
    # twelve climates and twelve ground colours is where it would fail.
    glut = {bytes(g["rgb"]): i + 1 for i, g in enumerate(mapvocab.GROUND_TYPES)}
    tiles_img = rcm.tiles("ground_types").convert("RGB")
    t0 = time.perf_counter()
    fast = mapterrain._index(tiles_img, glut)
    fast_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    slow = mapterrain._index_slow(tiles_img, glut)
    slow_ms = (time.perf_counter() - t0) * 1000
    check(f"     the packed index is byte for byte the tile-at-a-time one, and "
          f"{slow_ms / max(fast_ms, 0.01):.0f}x quicker ({fast_ms:.0f} ms vs "
          f"{slow_ms:.0f})", fast == slow)
    # and the validator says exactly what the plan measured, from the same object
    rrep = mapcheck.run(rmod, rcm, campstrat.DEFAULT_CAMPAIGN, use_baseline=False)
    rows = [f for f in rrep.findings if f.code == "terrain.texture"]
    check(f"     the validator reports the same {len(rows)} gap(s) the plan "
          f"measured, over {sum(f.count for f in rows):,} tiles, and runs the "
          f"whole rule set in {rrep.ms} ms",
          len(rows) == len(rp.gaps) + len(mapterrain.check_textures(rmod, rp))
          and sum(f.count for f in rows) == rp.pink and not rrep.failed)

if not seen:
    print("  SKIPPED - no installed mod ships a texture table")

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
