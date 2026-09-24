"""Map resize - Phase 26a's exit criteria, measured.

Four claims:

    the layers    every layer grows or shrinks by the margins, one pixel a tile
                  on a tile layer and two on a 2W+1 or 2W one, and the new
                  ground is the map's own sea
    the numbers   every coordinate the game's files hold moves by the west and
                  south margins, and nothing else on the line changes
    the refusal   a shrink that would take a settlement, a character or a
                  resource off the map is refused and names each one
    the undo      one Undo puts every file back byte for byte

Then the installed mods, without writing to them: growing a map and shrinking it
back gives back every layer and every coordinate file exactly.

    python -m tests.test_mapresize
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod, _tmp
from unittransfer import (campmap, campstrat, config, mapcheck, mapresize,
                          mapterrain, mapvocab, transfer)
from unittransfer.maptga import TgaInfo, encode, read
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

# ---- the fixture: the validator's clean little map, with every coordinate kind
W, H = 8, 7
A, B, C, SEA = (10, 20, 30), (40, 50, 60), (70, 80, 90), (0, 90, 200)
MARK, PORT = mapvocab.SETTLEMENT_RGB, mapvocab.PORT_RGB
GRID = [[A, A, A, A, B, B, B, B],
        [A, A, MARK, A, B, B, B, B],
        [A, A, A, A, B, B, MARK, B],
        [A, A, A, A, B, B, B, B],
        [C, C, C, C, C, C, C, C],
        [C, C, MARK, C, C, C, PORT, C],
        [SEA] * 8]
SEA_PX = 2 * 6

TERRAIN = ("dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
           "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n"
           "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
           "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
           % (W, H))
RECORDS = ("A_Province\r\n\tAtown\r\n\tslave\r\n\tbrigands\r\n\t10 20 30\r\n"
           "\tgold\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n"
           "\r\nB_Province\r\n\tBtown\r\n\tslave\r\n\tbrigands\r\n\t40 50 60\r\n"
           "\tsilver\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n"
           "\r\nC_Province\r\n\tCtown\r\n\tslave\r\n\tbrigands\r\n\t70 80 90\r\n"
           "\ttimber\r\n\t5\r\n\t4\r\n\treligions { catholic 100 }\r\n")
CLIMATES = ("climates\n{\n\tsandy_desert\n\ttemperate_grassland_fertile\n}\n"
            "climate sandy_desert\n{\n\tcolour 200 100 50\n\theat 4\n}\n"
            "climate temperate_grassland_fertile\n{\n\tcolour 60 160 60\n"
            "\theat 2\n}\n")
STRAT = "\r\n".join([
    "campaign imperial_campaign", "playable", "\tengland", "end", "unlockable",
    "end", "nonplayable", "\tslave", "end", "",
    "start_date 1080 summer", "end_date 1500 winter", "",
    "resource gold, 1, 5",
    "resource\tsilver,\t5,\t4 ; a comment 9, 9 that stays",
    "",
    "faction england, balanced smith", "\tai_label default", "\tdenari 10000",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion A_Province",
    "\t\tyear_founded 0", "\t\tpopulation 1000", "\t\tplan_set default_set",
    "\t\tfaction_creator england", "\t}",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion B_Province",
    "\t\tyear_founded 0", "\t\tpopulation 1000", "\t\tplan_set default_set",
    "\t\tfaction_creator england", "\t}",
    "character\tHarold, named character, male, leader, age 30, x 2, y 5",
    "army", "unit\t\tNE Bodyguard\t\texp 1 armour 0 weapon_lvl 0", "",
    "faction slave, comfort caesar", "\tai_label default", "\tdenari 1000",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion C_Province",
    "\t\tyear_founded 0", "\t\tpopulation 800", "\t\tplan_set default_set",
    "\t\tfaction_creator slave", "\t\tbuilding", "\t\t{", "\t\t\ttype port port",
    "\t\t}", "\t}", "",
    "faction_standings england, -0.5 slave", "",
    "region A_Province", "fort 3 4 wooden_fort culture northern_european",
    "watchtower 1 6", "farming_level 3", "",
    "script", "campaign_script.txt", ""])
SCRIPT = "\r\n".join([
    "script",
    "monitor_event FactionTurnStart FactionIsLocal",
    "\tif I_CharacterTypeNearTile england named_character, 2 3,4",
    "\t\treveal_tile 1, 2",
    "\t\tsnap_strat_camera 4, 5 ; look at 7, 7",
    "\t\tconsole_command move_character Harold, 2, 3",
    "\t\treveal_area 0, 0, 3, 3",
    "\t\treveal_radius 2, 2, 4",
    "\t\tspawn_army", "\t\t\tfaction england",
    "\t\t\tcharacter\tHenry, named character, age 20, x 5, y 6",
    "\t\tend",
    "\t\tadd_money 1000",
    "\t\tset_counter turn_12 1",
    "\tend_if", "end_monitor", "end_script", ""])
EVENTS = "event\tearthquake\tquake\r\ndate\t10\r\nposition\t6, 2\r\n"
TILES = "; name x y\r\nA_Province\t\t2\t5\tfoo.wfc\t\tclear\t\tmorning\r\n"
BATTLE = ("battle\t\tTest\r\nfaction england\r\n"
          "character\tHarold, named character, male, age 20, x 2, y 5\r\n"
          "battle\t3, 4\r\nbattle_time\t12.00\t24.00\r\n")


def paint_img(w, h, fn, mode="RGBA"):
    im = Image.new(mode, (w, h))
    im.putdata([fn(x, y) + ((255,) if mode == "RGBA" else ())
                for y in range(h) for x in range(w)])
    return im


def write_tga(path, img, depth=32, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def tiny_mod(root: Path) -> Mod:
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(RECORDS.encode("latin-1"))
    write_tga(base / "map_regions.tga", paint_img(W, H, lambda x, y: GRID[y][x]))
    write_tga(base / "map_heights.tga", paint_img(
        2 * W + 1, 2 * H + 1,
        lambda x, y: (0, 0, 200) if y >= SEA_PX else (90, 90, 90)))
    write_tga(base / "map_ground_types.tga", paint_img(
        2 * W + 1, 2 * H + 1,
        lambda x, y: (196, 0, 0) if y >= SEA_PX else (96, 160, 64)))
    write_tga(base / "map_climates.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (200, 100, 50)))
    write_tga(base / "map_features.tga", paint_img(W, H, lambda x, y: (0, 0, 0)))
    write_tga(base / "map_fog.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (255, 255, 255), "RGB"),
              depth=24, desc=0x00)
    write_tga(base / "map_trade_routes.tga",
              paint_img(W, H, lambda x, y: (0, 0, 0), "RGB"), depth=24, desc=0x00)
    write_tga(base / "map_roughness.tga",
              paint_img(2 * W, 2 * H, lambda x, y: (0, 0, 0), "RGB"),
              depth=24, desc=0x00)
    write_tga(base / "water_surface.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (0, 0, 120), "RGB"),
              depth=24, image_type=2, desc=0x20)
    (base / "map.rwm").write_bytes(b"stale")
    data = root / "data"
    (data / mapvocab.CLIMATES_REL).parent.mkdir(parents=True, exist_ok=True)
    (data / mapvocab.CLIMATES_REL).write_text(CLIMATES, encoding="latin-1")
    (data / mapterrain.AERIAL_REL).write_text(
        "climate default\n{\n" + "".join(
            f"\t{g['code']}\tflat.tga\tflat.tga\n" for g in mapvocab.GROUND_TYPES
            if g["code"] not in mapvocab.SEA_GROUND) + "}\n", encoding="latin-1")
    tex = data / mapterrain.TEXTURE_DIR_REL
    tex.mkdir(parents=True, exist_ok=True)
    write_tga(tex / "flat.tga", Image.new("RGB", (32, 32), (60, 110, 40)),
              depth=24, desc=0x00)
    camp = data / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
    camp.mkdir(parents=True, exist_ok=True)
    (camp / campstrat.STRAT_NAME).write_bytes(STRAT.encode("latin-1"))
    (camp / "campaign_script.txt").write_bytes(SCRIPT.encode("latin-1"))
    (camp / "descr_events.txt").write_bytes(EVENTS.encode("latin-1"))
    (camp / "custom_tiles_db.txt").write_bytes(TILES.encode("latin-1"))
    bat = data / "world" / "maps" / "battle" / "custom" / "Test"
    bat.mkdir(parents=True, exist_ok=True)
    (bat / "descr_battle.txt").write_bytes(BATTLE.encode("latin-1"))
    (data / "text").mkdir(parents=True, exist_ok=True)
    names = "".join(f"{{{k}}}{v}\r\n" for k, v in (
        ("A_Province", "Aland"), ("Atown", "Atown"), ("B_Province", "Bland"),
        ("Btown", "Btown"), ("C_Province", "Cland"), ("Ctown", "Ctown")))
    (data / campmap.REGION_NAMES_REL).write_bytes(
        b"\xff\xfe" + names.encode("utf-16-le"))
    return Mod(root)


def files_of(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


tmp = Path(_tmp.mkdtemp(prefix="ut_resize_"))
root = tmp / "mods" / "Tiny"
mod = tiny_mod(root)
camp = root / "data" / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
base = root / "data" / campmap.BASE_REL
before = files_of(root)
check("the fixture is a clean map before anything happens",
      not mapcheck.run(mod, use_baseline=False).findings)

# ---- 1) growing ------------------------------------------------------------
print("\n1) growing the map: 2 west, 1 south, 1 north, 3 east")
p = mapresize.plan(mod, {"west": 2, "south": 1, "north": 1, "east": 3})
d = p.payload()
check(f"the plan is {d['old']} -> {d['new']} and has nothing against it: "
      f"{d['errors']}", d["ok"] and d["new"] == [13, 9])
check("coordinates move by the west and south margins only",
      d["shift"] == [2, 1])
out = mapresize.apply(p)
reg, _ = read(base / "map_regions.tga")
hts, _ = read(base / "map_heights.tga")
rgh, _ = read(base / "map_roughness.tga")
check("every layer is its new size: tile, 2W+1 and 2W",
      reg.size == (13, 9) and hts.size == (27, 19) and rgh.size == (26, 18))
rp = reg.convert("RGB").load()
check("the old map sits 2 in from the west and 1 down from the north",
      rp[2 + 2, 1 + 1] == MARK and rp[2 + 6, 1 + 5] == PORT)
check("the new ground is the map's own sea, on every side",
      rp[0, 0] == SEA and rp[12, 8] == SEA and rp[12, 0] == SEA)
check("the heights' new ground is the sea's own depth",
      hts.convert("RGB").load()[0, 0] == (0, 0, 200))
check("descr_terrain.txt says 13x9",
      "width  13" in (base / "descr_terrain.txt").read_text()
      and "height  9" in (base / "descr_terrain.txt").read_text())
check("and map.rwm is gone", not (base / "map.rwm").exists())

strat = (camp / campstrat.STRAT_NAME).read_text(encoding="latin-1")
check("a resource moves", "resource gold, 3, 6" in strat)
check("a tab-spaced resource keeps its tabs, and its comment keeps its numbers",
      "resource\tsilver,\t7,\t5 ; a comment 9, 9 that stays" in strat)
check("a character's x and y move",
      "age 30, x 4, y 6" in strat)
check("a fort and a watchtower move, and the fort keeps its type",
      "fort 5 5 wooden_fort culture northern_european" in strat
      and "watchtower 3 7" in strat)
script = (camp / "campaign_script.txt").read_text(encoding="latin-1")
check("the script's condition moves its tile and keeps its distance",
      "named_character, 2 5,5" in script)
check("reveal_tile and snap_strat_camera move, the comment does not",
      "reveal_tile 3, 3" in script and "snap_strat_camera 6, 6 ; look at 7, 7" in script)
check("console_command move_character moves the tile, not the name",
      "move_character Harold, 4, 4" in script)
check("reveal_area moves both corners, reveal_radius not its radius",
      "reveal_area 2, 1, 5, 4" in script and "reveal_radius 4, 3, 4" in script)
check("a spawned character moves",
      "x 7, y 7" in script)
check("and a line the rule does not know is left exactly",
      "add_money 1000" in script and "set_counter turn_12 1" in script)
check("an event's position moves",
      "position\t8, 3" in (camp / "descr_events.txt").read_text(encoding="latin-1"))
check("a custom battle tile moves",
      "A_Province\t\t4\t6\tfoo.wfc" in (camp / "custom_tiles_db.txt")
      .read_text(encoding="latin-1"))
bat = (root / "data/world/maps/battle/custom/Test/descr_battle.txt").read_text(
    encoding="latin-1")
check("a custom battle's location and its characters move, its name does not",
      "battle\t5, 5" in bat and "x 4, y 6" in bat and "battle\t\tTest" in bat)
after = mapcheck.run(Mod(root), use_baseline=False)
check(f"the resized map is still a clean map: {[f.code for f in after.findings]}",
      not after.findings)

transfer.undo(out["id"])
now = files_of(root)
changed = [k for k in set(before) | set(now) if before.get(k) != now.get(k)]
check("one Undo puts every file back byte for byte" +
      (f", except {changed}" if changed else ""), not changed)

# ---- 2) shrinking ----------------------------------------------------------
print("\n2) shrinking the map")
p = mapresize.plan(mod, {"west": -3})
d = p.payload()
check(f"taking three columns off the west is refused: {d['errors'][:1]}",
      not d["ok"] and d["off_total"] > 0)
offs = " ".join(t for rows in p.off.values() for _, t in rows)
check("it names the settlement pixel, the resource and the character",
      "settlement pixel at 2,1" in offs and "resource gold" in offs
      and "Harold" in offs)
check("and it writes nothing", files_of(root) == before)
p = mapresize.plan(mod, {"east": -1})
d = p.payload()
check(f"taking one empty column off the east goes through: {d['errors']}",
      d["ok"] and d["new"] == [7, 7])
check("and says which provinces lose land at the edge",
      any("lose land" in w for w in d["warnings"]))
check("nothing moves: the game counts from the west and the south",
      d["shift"] == [0, 0] and not d["moved"])
check("margins of 0 are refused rather than rewriting the map",
      not mapresize.plan(mod, {}).payload()["ok"])

# ---- 3) the installed mods, round trip in memory ---------------------------
print("\n3) every installed map: grow it and shrink it back, and nothing changed")
for rroot in _realmod.installed():
    rmod = Mod(rroot)
    home, camps = mapresize.members(rmod)
    m = {"north": 2, "south": 3, "west": 4, "east": 1}
    back = {k: -v for k, v in m.items()}
    lay_ok = True
    for ly in campmap.LAYERS:
        path = home / ly["file"]
        if ly["size"] not in ("tile", "centre", "double") or not path.is_file():
            continue
        img, _ = read(path)
        k = 1 if ly["size"] == "tile" else 2
        grown = mapresize.resized(img, m, k, (0,) * len(img.getbands()))
        lay_ok &= mapresize.resized(grown, back, k, (0,) * len(img.getbands())) \
            .tobytes() == img.tobytes()
    check(f"{rroot.name}: every layer grown and cropped back is the same pixels",
          lay_ok)
    files = mapresize.coordinate_files(rmod, camps, True)
    same, moved = True, 0
    for kind, path in files:
        text = path.read_bytes().decode("latin-1")
        there, n, _ = mapresize.shift_text(text, kind, 4, 3, (10 ** 6, 10 ** 6))
        again, _, _ = mapresize.shift_text(there, kind, -4, -3, (10 ** 6, 10 ** 6))
        same &= again == text
        moved += n
    check(f"{rroot.name}: {moved:,} coordinates in {len(files)} file(s) moved "
          f"and moved back, every file the same", same and moved > 0)

print(f"\n{sum(ok)}/{len(ok)} checks" + ("" if all(ok) else
      f" - {len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
