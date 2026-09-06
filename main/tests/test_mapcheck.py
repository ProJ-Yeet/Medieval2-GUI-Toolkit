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
from unittransfer import campmap, campstrat, config, mapcheck, mapvocab, transfer
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
check("every fix names a rule that exists, and no rule owns two fixes",
      all(f["rule"] in mapcheck.RULE_BY_CODE for f in mapcheck.FIXES.values())
      and len({f["rule"] for f in mapcheck.FIXES.values()}) == len(mapcheck.FIXES))


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

broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (0, 0, 255)
                         if (x, y) in ((0, 0), (1, 1)) else None),
       "river.diagonal", "two river tiles joined only at a corner")

broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (0, 0, 255) if (x, y) == (0, 0) else None),
       "river.isolated", "one river tile with no course through it")

broken(lambda d: repaint(d, "map_features.tga",
                         lambda x, y, c: (0, 0, 255)
                         if (x, y) in ((0, 0), (1, 0), (0, 1), (1, 1)) else None),
       "river.rejoin", "a river that closes a loop")

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
print("\n   Geomod's three debugger actions, and the Undo that reverses each")


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
finally:
    httpd.shutdown()

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(med2, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks - "
      + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
