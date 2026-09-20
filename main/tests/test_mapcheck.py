"""The validator - Phase 16f's exit criteria, measured.

16e changed the pixels; this says whether what came out will load. Three claims
are under test, and all three are the sort a validator is usually only asserted
to have:

    every rule fires   a clean map written here reports nothing at all, and a
                       deliberately broken copy of it - one break per rule -
                       reports that rule and, wherever the break is local, only
                       that rule
    the baseline holds a stamped finding is still shown, still counted and no
                       longer blocking, and its fingerprint survives the file
                       being edited above it
    a fix is undoable  each of Geomod's three actions writes through one backup
                       set, and the Log's Undo puts every file back byte-exact

The map the phase was scoped against is not installed, and vanilla turned out to
be the better measurement anyway: its own ``map_heights.tga`` has 55 tiles that
are land in every layer but the one the engine believes, and two of them have a
port standing on them - **Nottingham's and Ragusa's**. Ragusa's port is the bug
Geomod's manual names its debugger action after, and it is in the stock game.

Five parts, the last two of which need a game install:

    1  the fingerprint, and what it is allowed to depend on
    2  a clean map written here: every rule runs, nothing is reported
    3  one break per rule, and the rule that has to catch it
    4  every real map: the whole rule set inside a second, and what it finds
    5  the routes over real HTTP, a real fix and the Log's Undo

    python -m tests.test_mapcheck
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, mapcheck, mapterrain, mapvocab, transfer
from unittransfer.maptga import TgaInfo, encode, read
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the fingerprint ------------------------------------------------------
print("\n1) a finding is identified by what it is about, never by its line")

f1 = mapcheck.Finding("region.no_pixels", "fatal", "Aland has no tiles",
                      file=campmap.REGIONS_REL, line=40, what="Aland")
f2 = mapcheck.Finding("region.no_pixels", "fatal", "Aland has no tiles at all",
                      file=campmap.REGIONS_REL, line=91, what="Aland")
f3 = mapcheck.Finding("region.no_pixels", "fatal", "Bland has no tiles",
                      file=campmap.REGIONS_REL, line=40, what="Bland")
check("the same fault at a different line is the same finding", f1.key == f2.key)
check("a different fault at the same line is not", f1.key != f3.key)
check("and the wording of the message is not part of it either",
      f1.key == f2.key and f1.message != f2.message)
check("every rule has a source, a label and one of the three severities",
      all(r.source and r.label and r.severity in mapcheck.SEVERITIES
          for r in mapcheck.RULES))
check("every fix names a rule that exists, including the two resource choices",
      all(f["rule"] in mapcheck.RULE_BY_CODE for f in mapcheck.FIXES.values())
      and mapcheck.FIXES["resource_move"]["rule"]
      == mapcheck.FIXES["resource_position"]["rule"])


# ---- 2) a clean map ----------------------------------------------------------
print("\n2) a map with nothing wrong with it: every rule runs, nothing fires")

#  A A A A B B B B      three regions, one settlement marker each, a port on C
#  A A S A B B B B      with sea on one side, and one row of sea along the
#  A A A A B B S B      bottom that the heights and ground layers agree with.
#  A A A A B B B B      Every rule this phase has is meant to be silent on it.
#  C C C C C C C C
#  C C S C C C P C
#  ~ ~ ~ ~ ~ ~ ~ ~
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

#: the first pixel row of the 2W+1 layers that belongs to the sea tile row
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

#: A campaign small enough to read by eye and complete enough for every
#: descr_strat.txt rule to have something to look at: three settlements, one per
#: region, a port building on the region that has the port pixel, two resources,
#: and the diplomacy section after the faction blocks. Written as a list of
#: lines rather than one literal, because half the rules below rewrite one of
#: them and a triple-quoted block full of tabs is not something to edit by hand.
STRAT_LINES = [
    "campaign imperial_campaign",
    "playable",
    "\tengland",
    "end",
    "unlockable",
    "end",
    "nonplayable",
    "\tslave",
    "end",
    "",
    "start_date 1080 summer",
    "end_date 1500 winter",
    "",
    "resource gold, 1, 5",
    "resource silver, 5, 4",
    "",
    "faction england, balanced smith",
    "\tai_label default",
    "\tdenari 10000",
    "\tsettlement",
    "\t{",
    "\t\tlevel town",
    "\t\tregion A_Province",
    "\t\tyear_founded 0",
    "\t\tpopulation 1000",
    "\t\tplan_set default_set",
    "\t\tfaction_creator england",
    "\t}",
    "\tsettlement",
    "\t{",
    "\t\tlevel town",
    "\t\tregion B_Province",
    "\t\tyear_founded 0",
    "\t\tpopulation 1000",
    "\t\tplan_set default_set",
    "\t\tfaction_creator england",
    "\t}",
    "",
    "faction slave, comfort caesar",
    "\tai_label default",
    "\tdenari 1000",
    "\tsettlement",
    "\t{",
    "\t\tlevel town",
    "\t\tregion C_Province",
    "\t\tyear_founded 0",
    "\t\tpopulation 800",
    "\t\tplan_set default_set",
    "\t\tfaction_creator slave",
    "\t\tbuilding",
    "\t\t{",
    "\t\t\ttype port port",
    "\t\t}",
    "\t}",
    "",
    "faction_standings england, -0.5 slave",
    "",
    "region A_Province",
    "farming_level 3",
    "",
    "script",
    "campaign_script.txt",
    "",
]
STRAT = "\r\n".join(STRAT_LINES)

#: ``{key}text`` lines, so the localisation rule has something to check against
NAMES = "".join(f"{{{k}}}{v}\r\n" for k, v in (
    ("A_Province", "Aland"), ("Atown", "Atown"),
    ("B_Province", "Bland"), ("Btown", "Btown"),
    ("C_Province", "Cland"), ("Ctown", "Ctown")))


def paint_img(w, h, fn, mode="RGB"):
    im = Image.new(mode, (w, h))
    im.putdata([fn(x, y) if mode == "RGB" else fn(x, y) + (255,)
                for y in range(h) for x in range(w)])
    return im


def write_tga(path, img, depth=32, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def tiny_map(root: Path) -> Path:
    """One complete little mod on disk: ten layers and four text files."""
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(RECORDS.encode("latin-1"))
    write_tga(base / "map_regions.tga",
              paint_img(W, H, lambda x, y: GRID[y][x], "RGBA"))
    write_tga(base / "map_heights.tga",
              paint_img(2 * W + 1, 2 * H + 1,
                        lambda x, y: (0, 0, 200) if y >= SEA_PX else (90, 90, 90),
                        "RGBA"))
    write_tga(base / "map_ground_types.tga",
              paint_img(2 * W + 1, 2 * H + 1,
                        lambda x, y: (196, 0, 0) if y >= SEA_PX else (96, 160, 64),
                        "RGBA"))
    write_tga(base / "map_climates.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (200, 100, 50), "RGBA"))
    write_tga(base / "map_features.tga",
              paint_img(W, H, lambda x, y: (0, 0, 0), "RGBA"))
    write_tga(base / "map_fog.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (255, 255, 255)),
              depth=24, image_type=10, desc=0x00)
    write_tga(base / "map_trade_routes.tga",
              paint_img(W, H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    write_tga(base / "map_roughness.tga",
              paint_img(2 * W, 2 * H, lambda x, y: (0, 0, 0)), depth=24, desc=0x00)
    write_tga(base / "water_surface.tga",
              paint_img(2 * W + 1, 2 * H + 1, lambda x, y: (0, 0, 120)),
              depth=24, image_type=2, desc=0x20)
    (base / "map.rwm").write_bytes(b"stale")

    data = root / "data"
    (data / mapvocab.CLIMATES_REL).parent.mkdir(parents=True, exist_ok=True)
    (data / mapvocab.CLIMATES_REL).write_text(CLIMATES, encoding="latin-1")
    # 23a: a texture for every ground type a tile of this map can be, so that
    # `terrain.texture` runs rather than skipping - a rule that skips on the
    # clean map is a rule none of the breaks below could be measured against.
    # The sea types are deliberately left out, which is what every real mod's
    # file does: the engine draws the sea from another folder entirely.
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
    (data / "text").mkdir(parents=True, exist_ok=True)
    (data / campmap.REGION_NAMES_REL).write_bytes(
        b"\xff\xfe" + NAMES.encode("utf-16-le"))
    return base


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"                      # the baseline lives here

tmp = Path(_tmp.mkdtemp(prefix="ut_check_"))
clean_root = tmp / "mods" / "Clean"
tiny_map(clean_root)
clean = Mod(clean_root)

rep = mapcheck.run(clean, use_baseline=False)
check(f"the map reads and every rule runs: {len(mapcheck.RULES)} rules, "
      f"{rep.ms} ms, {len(rep.failed)} of them raised",
      not rep.failed and len(mapcheck.RULES) >= 25)
check(f"nothing could not be checked: {[s['what'] for s in rep.skipped]}",
      not rep.skipped)
check(f"and nothing at all is reported: {[f.code for f in rep.findings]}",
      not rep.findings)


# ---- 3) one break per rule ---------------------------------------------------
print("\n3) a deliberately broken copy of each rule, and the rule that catches it")


def broken(fn, want, label, *, others=True):
    """Copy the clean mod, break it with ``fn``, and check ``want`` fires.

    ``others`` asks the harder question as well: did breaking one thing report
    only that thing? It is off for the handful of breaks that really do have a
    second consequence - taking a region's colour away also takes its tiles away
    - and the reason is written beside the call.
    """
    root = tmp / "mods" / f"B_{want.replace('.', '_')}_{len(ok)}"
    shutil.copytree(clean_root, root)
    fn(root / "data")
    got = mapcheck.run(Mod(root), use_baseline=False)
    codes = {f.code for f in got.findings}
    first = next((f for f in got.findings if f.code == want), None)
    detail = (f": {first.message[:72]}" if first
              else f", got {sorted(codes) or 'nothing'}")
    check(f"{label}{detail}",
          want in codes and (not others or not (codes - {want})))
    return got


def repaint(data: Path, name: str, fn):
    """Rewrite one layer through the same encoder the paint tool saves with."""
    p = data / campmap.BASE_REL / name
    img, info = read(p)
    img = img.convert("RGB")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            new = fn(x, y, px[x, y])
            if new is not None:
                px[x, y] = new
    p.write_bytes(encode(img.convert(info.mode), info))


def edit(data: Path, rel: str, old: str, new: str, count=1):
    p = data / rel
    text = p.read_bytes().decode("latin-1")
    assert old in text, f"{old!r} is not in {rel}"
    p.write_bytes(text.replace(old, new, count).encode("latin-1"))


STRAT_REL = (f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.DEFAULT_CAMPAIGN}/"
             f"{campstrat.STRAT_NAME}")

broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (1, 1, 1) if (x, y) == (0, 0) else None),
       "feature.unknown",
       "the stray (1,1,1) pixel this phase exists to report is reported")

broken(lambda d: repaint(d, "map_ground_types.tga",
                         lambda x, y, c: (7, 7, 7) if (x, y) == (1, 1) else None),
       "ground.unknown", "a ground colour no table names")

broken(lambda d: repaint(d, "map_climates.tga",
                         lambda x, y, c: (9, 9, 9) if (x, y) == (1, 1) else None),
       "climate.unknown", "a colour descr_climates.txt does not declare")

broken(lambda d: (d / campmap.BASE_REL / "map_features.tga").write_bytes(
           encode(paint_img(3, 3, lambda x, y: (0, 0, 0), "RGBA"),
                  TgaInfo(image_type=10, width=3, height=3, depth=32,
                          descriptor=0x08))),
       "layer.size", "a layer that is not the shape descr_terrain.txt implies",
       others=False)   # a 3x3 features layer also stops the sea mask being built

broken(lambda d: edit(d, campmap.REGIONS_REL, "\t40 50 60", "\t10 20 30"),
       "region.duplicate_colour", "two records sharing one colour",
       others=False)   # B_Province then owns no tiles, which is the next rule

broken(lambda d: edit(d, campmap.REGIONS_REL, "\t40 50 60", "\t0 0 0"),
       "region.reserved_colour", "a record claiming the settlement marker",
       others=False)   # and its tiles become a province nobody declares

broken(lambda d: edit(d, campmap.REGIONS_REL, "\t40 50 60", "\t44 55 66"),
       "region.no_pixels", "a declared region with no tiles on the map",
       others=False)   # its pixels become a province nobody declares, too

broken(lambda d: repaint(d, "map_regions.tga",
                         lambda x, y, c: (99, 99, 99) if (x, y) == (0, 0) else None),
       "region.undeclared", "land painted a colour no record claims")

broken(lambda d: edit(d, campmap.REGIONS_REL, "religions { catholic 100 }",
                      "religions { catholic 90 }"),
       "region.record", "religion percentages that do not total 100")

broken(lambda d: repaint(d, "map_regions.tga",
                         lambda x, y, c: MARK if (x, y) == (0, 0) else None),
       "marker.extra", "a second settlement pixel in one region")

broken(lambda d: repaint(d, "map_regions.tga",
                         lambda x, y, c: A if (x, y) == (2, 1) else None),
       "marker.no_settlement", "a region whose settlement pixel was painted over")

broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (255, 0, 0) if (x, y) == (2, 1) else None),
       "marker.feature", "a settlement standing on a volcano")

broken(lambda d: repaint(d, "map_ground_types.tga",
                         lambda x, y, c: (64, 64, 64)
                         if 5 <= x <= 6 and 3 <= y <= 4 else None),
       "marker.ground", "a settlement standing on impassable land")

broken(lambda d: repaint(d, "map_heights.tga",
                         lambda x, y, c: (0, 0, 0)
                         if 13 <= x <= 14 and 11 <= y <= 12 else None),
       "marker.sea", "a port standing on a pure-black altitude - the Ragusa bug",
       others=False)   # the same pixels are the ambiguous-altitude warning too

broken(lambda d: repaint(d, "map_regions.tga",
                         lambda x, y, c: PORT if (x, y) == (1, 2) else None),
       "port.inland", "a port with no sea on any of its four sides",
       others=False)   # A_Province then has a port as well, which is not wrong

# Both tiles are sources, so each of the two one-tile components has one and
# river.no_source (31) stays quiet; white is a river colour, so the rule under
# test sees exactly what it saw before.
broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (255, 255, 255)
                         if (x, y) in ((0, 0), (1, 1)) else None),
       "river.diagonal", "two river tiles joined only at a corner")

# The source itself, standing alone - which is Mylae's check 4 and the vanilla
# pixel at (175,14) this rule was measured against in the first place.
broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (255, 255, 255) if (x, y) == (0, 0) else None),
       "river.isolated", "a river source with no course leading out of it")

# One corner of the block is the source, so the loop is a loop and nothing
# else. No tile of a 2x2 has four cardinal neighbours, so river.fourway (31)
# has nothing to say about it either - the two rules really are independent.
broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (255, 255, 255) if (x, y) == (0, 0)
                         else (0, 0, 255)
                         if (x, y) in ((1, 0), (0, 1), (1, 1)) else None),
       "river.rejoin", "a river that closes a loop")

# Phase 31. A plus of five tiles, with one arm the white source so the course
# is not also sourceless - the two rules are independent and the fixture has to
# say so. Centred at (5,3), which is clear of all four markers on the grid: a
# river tile under a settlement is a crash of its own and would be the finding
# reported instead.
broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (255, 255, 255) if (x, y) == (5, 2)
                         else (0, 0, 255)
                         if (x, y) in ((5, 3), (5, 4), (4, 3), (6, 3)) else None),
       "river.fourway", "a river tile with river on all four sides")

# Two tiles of course and no white pixel anywhere on them. Cardinally joined,
# so neither river.diagonal nor river.isolated has anything to say, and two
# tiles cannot close a loop.
broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (0, 0, 255)
                         if (x, y) in ((3, 3), (4, 3)) else None),
       "river.no_source", "a river with no source pixel anywhere along it")


def _ford_in_sea(d):
    """A ford at (1,3) with the four tiles around it dropped into the sea.

    The heights layer is 2W+1 a side and a tile's centre is the pixel the sea
    mask reads, so making a tile sea means painting (2x+1, 2y+1). Four tiles
    of a province become open water here, which is a real second consequence
    and is why this call turns `others` off.
    """
    repaint(d, "map_features.tga",
            lambda x, y, c: (0, 255, 255) if (x, y) == (1, 3) else None)
    # the ford's own centre as well as its four neighbours: the rule needs the
    # tile to read sea itself, or there is no hole for the crossing to punch
    wet = {(2 * x + 1, 2 * y + 1)
           for x, y in ((1, 3), (1, 2), (1, 4), (0, 3), (2, 3))}
    repaint(d, "map_heights.tga",
            lambda x, y, c: (0, 0, 200) if (x, y) in wet else None)


broken(_ford_in_sea, "feature.ford_in_sea",
       "a river crossing with sea on all four sides",
       others=False)   # four land tiles became ocean, which is its own finding

broken(lambda d: repaint(d, "map_heights.tga",
                         lambda x, y, c: (0, 0, 0) if (x, y) == (5, 5) else None),
       "height.ambiguous", "an altitude that is pure black on a land tile")

broken(lambda d: edit(d, campmap.REGIONS_REL,
                      "A_Province\r\n\tAtown\r\n", "A_Province\r\n"),
       "region.wasteland_last",
       "a settlement-less record that is not the last one in the file",
       others=False)   # it also stops being a settlement any faction can own

broken(lambda d: (d / campmap.REGION_NAMES_REL).write_bytes(
           b"\xff\xfe" + "{A_Province}Aland\r\n".encode("utf-16-le")),
       "loc.missing", "region and settlement names with no line in the text file")

broken(lambda d: edit(d, STRAT_REL, "resource silver, 5, 4",
                      "resource gold, 1, 5"),
       "strat.resource_duplicate", "the same resource twice on one tile")

broken(lambda d: edit(d, STRAT_REL, "resource silver, 5, 4",
                      "resource silver, 5, 0"),
       "strat.resource_position", "a resource sitting in the sea")

broken(lambda d: edit(d, STRAT_REL, "resource silver, 5, 4",
                      "resource silver, 500, 4"),
       "strat.resource_position", "a resource off the map altogether")

broken(lambda d: edit(d, STRAT_REL, "\t\tregion B_Province", "\t\tregion Nowhere"),
       "strat.settlement_region", "a settlement in a region nobody declares",
       others=False)   # B_Province is then a region no settlement block claims

broken(lambda d: edit(d, STRAT_REL, "faction_standings england, -0.5 slave",
                      "faction_standings england, -0.5 slave\r\n"
                      "faction milan, balanced smith\r\n\tai_label default"),
       "strat.faction_after_diplomacy",
       "a faction block after the diplomacy section")

broken(lambda d: repaint(d, "map_regions.tga",
                         lambda x, y, c: C if (x, y) == (6, 5) else None),
       "strat.port_building", "a port building in a region with no port pixel")

broken(lambda d: edit(d, STRAT_REL, "\t\tregion C_Province",
                      "\t\tregion A_Province"),
       "strat.region_unowned", "a region no settlement block claims",
       others=False)   # A_Province is then claimed twice, which nothing forbids


# ---- the baseline ------------------------------------------------------------
print("\n   the baseline: shown, counted, and no longer blocking")

base_root = tmp / "mods" / "Baselined"
shutil.copytree(clean_root, base_root)
repaint(base_root / "data", "map_features.tga",
        lambda x, y, c: (1, 1, 1) if (x, y) == (0, 0) else None)
based = Mod(base_root)

first = mapcheck.run(based)
check(f"before the stamp, the inherited fault blocks: "
      f"{[f.code for f in first.blocking]}",
      [f.code for f in first.blocking] == ["feature.unknown"])

stamp = mapcheck.take_baseline(based)
after = mapcheck.run(based)
check(f"after it, the same fault is still shown and counted: {after.counts()}",
      len(after.findings) == len(first.findings))
check("and it no longer blocks", not after.blocking and after.baseline_keys == 1)
check("the stamp holds keys and a date, and no message text",
      set(stamp) == {"mod", "taken", "keys"} and len(stamp["keys"]) == 1)

repaint(base_root / "data", "map_ground_types.tga",
        lambda x, y, c: (7, 7, 7) if (x, y) == (3, 3) else None)
mixed = mapcheck.run(Mod(base_root))
check(f"a NEW fault on top of a stamped one blocks, and only it: "
      f"{[f.code for f in mixed.blocking]}",
      [f.code for f in mixed.blocking] == ["ground.unknown"])

edit(base_root / "data", campmap.REGIONS_REL, "A_Province\r\n",
     "; a comment nobody had written before\r\nA_Province\r\n")
shifted = mapcheck.run(Mod(base_root))
check("a comment inserted above a finding does not make it a new one",
      not any(f.code == "feature.unknown" and not f.baseline
              for f in shifted.findings))

check("clearing the stamp puts it back to blocking",
      mapcheck.clear_baseline(based)
      and len(mapcheck.run(Mod(base_root)).blocking) == 2)


# ---- the three fixes ---------------------------------------------------------
print("\n   Campaign-map repair actions, and the Undo that reverses each")


def fixture(breaker) -> Path:
    root = tmp / "mods" / f"F_{len(ok)}"
    shutil.copytree(clean_root, root)
    breaker(root / "data")
    return root


def files_of(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


def black_port(d: Path):
    """The Ragusa bug, made on purpose: the port tile's altitude goes black."""
    repaint(d, "map_heights.tga",
            lambda x, y, c: (0, 0, 0) if 13 <= x <= 14 and 11 <= y <= 12 else None)


for code, breaker, expect in (
    ("heights_black", black_port, "height.ambiguous"),
    ("resource_duplicate",
     lambda d: edit(d, STRAT_REL, "resource silver, 5, 4", "resource gold, 1, 5"),
     "strat.resource_duplicate"),
    ("resource_position",
     lambda d: edit(d, STRAT_REL, "resource silver, 5, 4", "resource silver, 5, 0"),
     "strat.resource_position"),
):
    root = fixture(breaker)
    mod = Mod(root)
    was = files_of(root)
    before_rep = mapcheck.run(mod, use_baseline=False)
    check(f"{code}: the break is reported first ({expect})",
          any(f.code == expect for f in before_rep.findings))

    plan = mapcheck.plan_fix(mod, [code])
    check(f"{code}: the plan says what it would write: "
          f"{plan.changes[0][:70] if plan.changes else plan.errors}",
          not plan.errors and plan.changes)
    out = mapcheck.apply_fix(plan)
    fixed = mapcheck.run(Mod(root), use_baseline=False)
    check(f"{code}: applying it clears the finding "
          f"({len(before_rep.findings)} -> {len(fixed.findings)})",
          not any(f.code == expect for f in fixed.findings))
    check(f"{code}: and reports nothing new",
          not ({f.code for f in fixed.findings}
               - {f.code for f in before_rep.findings}))

    transfer.undo(out["id"])
    now = files_of(root)
    changed = [k for k in set(was) | set(now) if was.get(k) != now.get(k)]
    check(f"{code}: the Log's Undo puts every file back byte-exact"
          + (f", except {changed}" if changed else ""), not changed)

# the ambiguous altitude is a picture that does not change
root = fixture(black_port)
was_img, _ = read(root / "data" / campmap.BASE_REL / "map_heights.tga")
mapcheck.apply_fix(mapcheck.plan_fix(Mod(root), ["heights_black"]))
now_img, _ = read(root / "data" / campmap.BASE_REL / "map_heights.tga")
a, b = was_img.convert("RGB").load(), now_img.convert("RGB").load()
moved = [(x, y) for y in range(was_img.height) for x in range(was_img.width)
         if a[x, y] != b[x, y]]
check(f"heights_black moves {len(moved)} pixel(s), every one of them (0,0,0) to "
      f"(1,1,1) and nothing else",
      moved and all(a[x, y] == (0, 0, 0) and b[x, y] == (1, 1, 1) for x, y in moved))
check("and map.rwm is deleted with it, because a layer changed",
      not (root / "data" / campmap.RWM_REL).exists())

# A sea resource has two deliberate choices: deletion keeps the old repair,
# while move uses the land coordinate the finding itself calculated.  Plan it
# by key as the row button does, so no neighbouring finding can move with it.
root = fixture(lambda d: edit(d, STRAT_REL, "resource silver, 5, 4",
                              "resource silver, 5, 0"))
mod = Mod(root)
was = files_of(root)
sea_finding = next(f for f in mapcheck.run(mod, use_baseline=False).findings
                   if f.code == "strat.resource_position")
move_plan = mapcheck.plan_fix(mod, ["resource_move"], keys=[sea_finding.key])
check("a sea resource offers its calculated nearest land as a move target",
      sea_finding.move == (5, 1) and move_plan.payload()["ok"]
      and len(move_plan.cleared) == 1
      and "resource silver, 5, 1" in move_plan.text[STRAT_REL])
move_out = mapcheck.apply_fix(move_plan)
moved_text = (root / "data" / STRAT_REL).read_text(encoding="latin-1")
check("moving rewrites only its coordinates and clears the sea finding",
      "resource silver, 5, 1" in moved_text
      and not any(f.code == "strat.resource_position"
                  for f in mapcheck.run(Mod(root), use_baseline=False).findings))
transfer.undo(move_out["id"])
check("Undo restores the moved resource byte-exact", files_of(root) == was)

# Row selections are sent by action, not as one shared key list: otherwise
# selecting gold to move and silver to delete would delete both resources.
root = fixture(lambda d: (edit(d, STRAT_REL, "resource gold, 1, 5",
                               "resource gold, 1, 0"),
                          edit(d, STRAT_REL, "resource silver, 5, 4",
                               "resource silver, 500, 4")))
mod = Mod(root)
positions = [f for f in mapcheck.run(mod, use_baseline=False).findings
             if f.code == "strat.resource_position"]
gold = next(f for f in positions if f.what.startswith("gold|"))
silver = next(f for f in positions if f.what.startswith("silver|"))
batch_plan = mapcheck.plan_fix(
    mod, ["resource_move", "resource_position"],
    keys={"resource_move": [gold.key], "resource_position": [silver.key]})
batch_text = batch_plan.text[STRAT_REL]
check("one plan can move selected resources and delete different selected resources",
      batch_plan.payload()["ok"] and len(batch_plan.cleared) == 2
      and "resource gold, 1, 1" in batch_text
      and "resource silver, 500, 4" not in batch_text)

root = fixture(lambda d: edit(d, STRAT_REL, "resource silver, 5, 4",
                              "resource silver, 500, 4"))
off_plan = mapcheck.plan_fix(Mod(root), ["resource_move"])
check("a resource off the map stays delete-only",
      "nothing left to fix" in " ".join(off_plan.errors))

clean_plan = mapcheck.plan_fix(clean, ["heights_black", "resource_duplicate"])
check(f"a fix on a clean map refuses and says so: {clean_plan.errors[:1]}",
      clean_plan.errors and not clean_plan.data and not clean_plan.text)


# ---- 4) every real map -------------------------------------------------------
print("\n4) every installed map: the whole rule set, and what it reports")

roots = _realmod.installed()
game = _realmod.MODS.parent
if (game / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
    roots.append(game)
roots = [r for r in roots
         if (r / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]

if not roots:
    print("  SKIPPED - no installed mod (and no game) with a campaign map")
else:
    for root in roots:
        mod = Mod(root)
        print(f"\n  -- {mod.name}")
        rep = mapcheck.run(mod, use_baseline=False)
        check(f"the whole rule set runs in {rep.ms} ms, under the one-second bar",
              rep.ms < 1000)
        check(f"and no rule raised: {[f['code'] for f in rep.failed]}",
              not rep.failed)
        tally = {}
        for f in rep.findings:
            tally[f.code] = tally.get(f.code, 0) + 1
        print(f"     {rep.counts()}  ·  "
              + ", ".join(f"{c} x{n}" for c, n in sorted(tally.items())))
        for s in rep.skipped:
            print(f"     not checked - {s['what']}: {s['why'][:86]}")
        for f in rep.findings:
            if f.severity == "fatal":
                print(f"     FATAL {f.code}: {f.message[:94]}")
        check("every finding carries a place to go and look",
              all(f.tile or f.file for f in rep.findings))
        check("every finding that offers a fix names a fix that exists",
              all(f.fix in mapcheck.FIXES for f in rep.findings if f.fix))

    if (game / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
        rep = mapcheck.run(Mod(game), use_baseline=False)
        ports = [f for f in rep.findings if f.code == "marker.sea"]
        check(f"the stock game's own map reports its two ambiguous ports: "
              f"{[f.message.split(chr(39))[0] for f in ports]}",
              len(ports) == 2
              and any("Ragusa" in f.message for f in ports)
              and all(f.fix == "heights_black" for f in ports))


# ---- 5) the routes, over real HTTP -------------------------------------------
print("\n5) /api/map/check, /baseline, /fix_plan and /fix_apply")

med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
http_root = med2 / "mods" / "CheckMod"
tiny_map(http_root)
black_port(http_root / "data")
config.save_settings(med2_root=str(med2), run_full_cleaner=False)

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"  serving {BASE}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    body = dict(body)
    body.setdefault("mod", "CheckMod")
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


was = files_of(http_root)
try:
    rep = get("/api/map/check?mod=CheckMod")
    check(f"/api/map/check answers {len(rep['findings'])} finding(s), "
          f"{rep['blocking']} blocking, in {rep['ms']} ms",
          rep["blocking"] == 1
          and any(f["code"] == "marker.sea" for f in rep["findings"]))
    check("every finding on the wire carries its key, its severity and a place",
          all(f["key"] and f["severity"] in mapcheck.SEVERITIES
              and (f["tile"] or f["file"]) for f in rep["findings"]))
    check("a tile finding also carries the coordinates descr_strat.txt writes",
          all(f["game"] and f["game"][1] == H - 1 - f["tile"][1]
              for f in rep["findings"] if f["tile"]))
    check("and the answer carries the rule list and the fixes, for the panel",
          len(rep["rules"]) == len(mapcheck.RULES)
          and len(rep["fixes"]) == len(mapcheck.FIXES))

    r = post("/api/map/baseline", {"action": "take"})
    check(f"/api/map/baseline stamps {r['baseline']['keys']} finding(s), after "
          f"which nothing blocks",
          r["baseline"]["keys"] == len(rep["findings"])
          and r["report"]["blocking"] == 0)
    check("and stamping a baseline touched no file in the mod",
          files_of(http_root) == was)
    r = post("/api/map/baseline", {"action": "clear"})
    check("clearing it puts the block back", r["report"]["blocking"] == 1)

    r = post("/api/map/fix_plan", {"fixes": ["heights_black"]})
    check(f"/api/map/fix_plan says what it would write without writing: "
          f"{r['plan']['changes'][:1]}",
          r["plan"]["ok"] and r["plan"]["cleared"] >= 1
          and files_of(http_root) == was)

    r = post("/api/map/fix_apply", {"fixes": ["heights_black"]})
    check(f"/api/map/fix_apply writes {len(r['files'])} file(s) and answers with "
          f"the map re-checked: {r['report']['counts']}",
          r["report"]["blocking"] == 0
          and not any(f["code"] == "marker.sea" for f in r["report"]["findings"]))
    check("the layer really changed on disk, and map.rwm went with it",
          files_of(http_root) != was
          and not (http_root / "data" / campmap.RWM_REL).exists())

    post("/api/undo", {"id": r["id"]})
    check("and the Log's Undo over HTTP puts every file back byte-exact",
          files_of(http_root) == was)

    bad = post("/api/map/fix_plan", {"fixes": ["not_a_fix"]})
    check(f"an unknown fix is refused by name: {bad.get('error', '')[:50]}",
          bad.get("error"))

    edit(http_root / "data", STRAT_REL, "resource silver, 5, 4",
         "resource silver, 5, 0")
    move_was = files_of(http_root)
    sea = next(f for f in get("/api/map/check?mod=CheckMod")["findings"]
               if f["code"] == "strat.resource_position")
    r = post("/api/map/fix_plan",
             {"fixes": ["resource_move"], "keys": [sea["key"]]})
    check("the move plan over HTTP targets just the selected sea resource",
          r["plan"]["ok"] and r["plan"]["cleared"] == 1
          and "5,0 -> 5,1" in " ".join(r["plan"]["changes"]))
    r = post("/api/map/fix_apply",
             {"fixes": ["resource_move"], "keys": [sea["key"]]})
    check("the move apply over HTTP writes the calculated land coordinates",
          not r.get("error") and "resource silver, 5, 1" in
          (http_root / "data" / STRAT_REL).read_text(encoding="latin-1"))
    post("/api/undo", {"id": r["id"]})
    check("the HTTP move can also be undone byte-exact",
          files_of(http_root) == move_was)
finally:
    httpd.shutdown()

# ---- Phase 31: the one repair of the three that has a safe answer -----------
print("\n31) a ford standing in open water, cleared")

fordroot = tmp / "mods" / "FordFix"
shutil.copytree(clean_root, fordroot)
_ford_in_sea(fordroot / "data")
fordmod = Mod(fordroot)
before_feat = (fordroot / "data" / campmap.BASE_REL / "map_features.tga").read_bytes()

fp = mapcheck.plan_fix(fordmod, ["ford_none"])
check(f"the plan finds the one ford and says what it would write: "
      f"{(fp.changes or ['-'])[0][:60]}",
      fp.payload()["ok"] and len(fp.cleared) == 1
      and fp.cleared[0].code == "feature.ford_in_sea")
check("and it writes map_features.tga and nothing else",
      len(fp.data) == 1 and list(fp.data)[0].endswith("map_features.tga")
      and not fp.text)
check("nothing has touched the disk yet",
      (fordroot / "data" / campmap.BASE_REL / "map_features.tga").read_bytes()
      == before_feat)

mapcheck.apply_fix(fp)
after_img, _ = read(fordroot / "data" / campmap.BASE_REL / "map_features.tga")
after_px = after_img.convert("RGB").load()
check("the ford tile is no feature at all now",
      after_px[1, 3] == (0, 0, 0))
check("and every other tile of the layer is what it was",
      all(after_px[x, y] == (0, 0, 0)
          for y in range(H) for x in range(W)))

again = mapcheck.run(fordmod, use_baseline=False)
check("the finding is gone on a re-run, which is what a repair has to mean",
      "feature.ford_in_sea" not in {f.code for f in again.findings})
check("a second pass has nothing left to do and says so rather than writing",
      "nothing left to fix" in " ".join(
          mapcheck.plan_fix(fordmod, ["ford_none"]).errors))
check("the sea mask closes over it: the tile the heights called sea is sea "
      "again, which is the hole the rule was about",
      campmap.CampaignMap(fordmod).sea[3 * W + 1] == 1)

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(med2, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks - "
      + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
