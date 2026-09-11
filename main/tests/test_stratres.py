"""Phase 22b: trade resources, placed, moved, changed and taken out, and D10's
snap to the nearest tile that would do.

    python -m tests.test_stratres

1. A small campaign file written here, with no map: a resource is one line, its
   gaps and its comment survive an edit, a new one goes where the file groups
   its own - under its province's heading, after the last of its name, under a
   banner that says "resource" - and a name the mod does not declare is fatal.
2. The search: nearest first, the start first, a radius it gives up at, and a
   start off the grid searched from the edge.
3. The map a campaign reads: its own copy of a file wins, file by file, and a
   campaign that ships none reads the base map's object as it is.
4. Every installed campaign: the panel's findings agree with the validator's on
   the rules they share, every D10 answer is a tile the same rules accept, and
   an add, an edit, a delete and a heading move each touch only their lines.
5. The snap reaches the other two writers: a character on the wrong side of the
   shore, and a settlement pixel the four marker rules refuse.
6. The routes, a real save of each kind and its undo on a copy of a campaign.
"""
import difflib
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import (campaint, campmap, campstrat, config, mapcheck, mapquery,
                          mapsnap, stratchar, stratobj)
from unittransfer.keyblock import write_text
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


def lines_of(text):
    return (text[:-len(CR)] if text.endswith(CR) else text).split(CR)


def hunks(before, after):
    """``[(tag, old lines, new lines)]`` for everything that differs."""
    a, b = lines_of(before), lines_of(after)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(t, a[i1:i2], b[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes()
            if t != "equal"]


TOP = ("campaign imperial_campaign", "playable", "\tengland", "end",
       "nonplayable", "\tslave", "end", "start_date 1080 summer",
       "free_upkeep_forts 4", "")

TAIL = (";#### England ####", "faction england, balanced smith",
        "settlement", "{", "\tlevel town", "\tregion London_Province",
        "\tyear_founded 0", "\tpopulation 800", "\tplan_set default_set",
        "\tfaction_creator england", "}",
        "character\tWilliam, named character, male, leader, age 30, x 10, y 20",
        "army", "unit\t\tNE Bodyguard\t\texp 1 armour 0 weapon_lvl 0", "",
        "faction_standings england, 0.0 slave",
        "faction_relationships england, at_war_with slave", "",
        "script", "campaign_script.txt")

#: DaC's shape: every name's lines together, a comment on each
BY_NAME = joined(*TOP, "; Resources", "",
                 "resource\tdogs,\t\t26,\t43 ; Anduin (Horses)",
                 "resource\tdogs,\t\t27,\t39 ; Anduin (Horses)",
                 "resource\ttimber,\t\t41,\t17 ;mordor",
                 "", *TAIL)

#: Reforged's: a heading naming the province over each group
BY_PROVINCE = joined(*TOP, "; >>>> start of resources section <<<<", "",
                     ";London_Province", "resource\ttimber,\t29,\t33",
                     "resource\tiron,\t29,\t32", "",
                     ";York_Province", "resource\tfish,\t63,\t43", "",
                     "; >>>> end of resources section <<<<", *TAIL)

#: none at all, with and without a banner that says where they go
BANNERED = joined(*TOP, ";;;;;;;;", "; >>>> start of resources section <<<<",
                  "", *TAIL)
BARE = joined(*TOP, *TAIL)


class Facts:
    """What a plan asks the fact table for, with no map behind it."""

    def __init__(self, mod, campaign, cm=None):
        self.mod, self.campaign, self.cm = mod, campaign, cm
        self.strat_rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{campaign}/"
                          f"{campstrat.STRAT_NAME}")
        self.strat = campstrat.read_strat(mod, campaign)


tmp = Path(_tmp.mkdtemp(prefix="ut_stratres_"))
CAMP = "imperial_campaign"


def make(text, name="ResMod", resources=None):
    root = tmp / name
    d = root / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
    d.mkdir(parents=True, exist_ok=True)
    write_text(d / campstrat.STRAT_NAME, text, campstrat.ENCODING)
    sm = root / "data" / "descr_sm_resources.txt"
    if resources:
        write_text(sm, "\r\n".join(
            f"type {r}\r\ntrade_value 5\r\nitem {r}.cas\r\nicon {r}.tga\r\n"
            for r in resources), "latin-1")
    elif sm.exists():
        sm.unlink()
    mod = Mod(root)
    return mod, Facts(mod, CAMP)


def plan(mod, facts, **body):
    return stratobj.plan(mod, facts, dict(body, campaign=CAMP))


# ---- 1) the writer, with no map -----------------------------------------------
print("\n1) one line at a time, in a file written here")

mod, facts = make(BY_NAME, resources=["dogs", "timber", "iron"])
sf = facts.strat
dogs = sf.of_kind("resource")[0]
p = plan(mod, facts, kind="resource", action="edit", line=dogs.start + 1,
         at=[26, 43], x=30, y=44)
check(f"a resource moved is its line rewritten, gaps and comment kept: {p.changes}",
      p.payload()["ok"] and hunks(BY_NAME, p.text) == [
          ("replace", ["resource\tdogs,\t\t26,\t43 ; Anduin (Horses)"],
           ["resource\tdogs,\t\t30,\t44 ; Anduin (Horses)"])])
p = plan(mod, facts, kind="resource", action="edit", line=dogs.start + 1,
         at=[26, 43], name="iron")
check("a new name is the name and nothing else",
      hunks(BY_NAME, p.text) == [
          ("replace", ["resource\tdogs,\t\t26,\t43 ; Anduin (Horses)"],
           ["resource\tiron,\t\t26,\t43 ; Anduin (Horses)"])]
      and "name: dogs -> iron" in p.changes)
p = plan(mod, facts, kind="resource", action="add", name="dogs", x=5, y=6)
check("in a file that keeps each name together, a new one follows the last of "
      "its name, in the file's own gaps",
      p.payload()["ok"] and hunks(BY_NAME, p.text) == [
          ("insert", [], ["resource\tdogs,\t\t5,\t6"])]
      and lines_of(p.text).index("resource\tdogs,\t\t5,\t6")
      == lines_of(BY_NAME).index("resource\tdogs,\t\t27,\t39 ; Anduin (Horses)") + 1)
p = plan(mod, facts, kind="resource", action="add", name="iron", x=5, y=6)
check("a name the file has none of yet goes after the last resource",
      lines_of(p.text).index("resource\tiron,\t\t5,\t6")
      == lines_of(BY_NAME).index("resource\ttimber,\t\t41,\t17 ;mordor") + 1)
p = plan(mod, facts, kind="resource", action="delete", line=dogs.start + 1,
         at=[26, 43])
check("a delete takes out that one line",
      hunks(BY_NAME, p.text) == [
          ("delete", ["resource\tdogs,\t\t26,\t43 ; Anduin (Horses)"], [])])
p = plan(mod, facts, kind="resource", action="add", name="plutonium", x=5, y=6)
check("a name descr_sm_resources.txt does not declare is fatal, with the list",
      not p.payload()["ok"] and "plutonium is not a resource" in "; ".join(p.errors)
      and "dogs, timber, iron" in "; ".join(p.errors))
p = plan(mod, facts, kind="resource", action="add", name="Timber", x=5, y=6)
check("and a case slip is named for what it is",
      "it writes timber" in "; ".join(p.errors))
p = plan(mod, facts, kind="resource", action="add", name="", x=5, y=6)
check("a resource with no name is fatal",
      not p.payload()["ok"] and "names nothing" in "; ".join(p.errors))
p = plan(mod, facts, kind="resource", action="add", name="timber", x="n", y=6)
check("a coordinate that is not a whole number is fatal",
      "not a whole number" in "; ".join(p.errors))
p = plan(mod, facts, kind="resource", action="move", line=dogs.start + 1,
         at=[26, 43], x=3, y=3, region="York_Province")
check("in a file with no headings a 'move' is only an edit: there is nowhere "
      "else to file it", p.action == "edit" and len(hunks(BY_NAME, p.text)) == 1)
p = plan(mod, facts, kind="resource", action="edit", line=dogs.start + 1,
         at=[99, 99], x=1, y=1)
check("a record that is not on the tile the panel saw is refused, not guessed",
      not p.text and "any more" in "; ".join(p.errors))

mod2, facts2 = make(BY_NAME, name="NoList")
p = plan(mod2, facts2, kind="resource", action="add", name="plutonium", x=5, y=6)
check("with descr_sm_resources.txt not on disk, no name is refused",
      p.payload()["ok"])
voc = stratobj.Vocabulary(mod2, facts2.strat)
names = [r["name"] for r in voc.resource_names()]
check("and the name box offers the file's own and the 28 every mod ships",
      "dogs" in names and "wool" in names and voc.payload()["have_resources"] is False)

# the heading rule needs provinces, which come off a map; the layout is read
# with a list handed to it, the way the Vocabulary hands it one
mod3, facts3 = make(BY_PROVINCE, name="Headed")
s3 = facts3.strat
provs = ["London_Province", "York_Province", "Kent_Province"]
lay = stratobj.layout_of(s3, provs)
check(f"Reforged's shape reads as grouped by province: {sorted(lay.heads)}",
      lay.by == "province" and lay.prefix == ";"
      and sorted(lay.heads) == ["london_province", "york_province"])
at, block, opened = stratobj.resource_home(s3, lay, "wool", "York_Province",
                                           "resource\twool,\t1,\t2")
check("a new one in a province with a heading joins the end of its group",
      s3.lines[at - 1] == "resource\tfish,\t63,\t43" and block == ["resource\twool,\t1,\t2"]
      and not opened)
at, block, opened = stratobj.resource_home(s3, lay, "wool", "Kent_Province",
                                           "resource\twool,\t1,\t2")
check("a province with no heading gets one of its own after the last group",
      block == ["", ";Kent_Province", "resource\twool,\t1,\t2"]
      and opened == "Kent_Province" and s3.lines[at - 1] == "resource\tfish,\t63,\t43")
check("DaC's shape reads as grouped by name",
      stratobj.layout_of(sf, provs).by == "name")

for label, text, want in (
        ("under the banner that says where they go", BANNERED,
         ["; >>>> start of resources section <<<<", "resource\tdogs,\t5,\t6", ""]),
        ("in front of the first faction's banner", BARE,
         ["free_upkeep_forts 4", "", "resource\tdogs,\t5,\t6", "", ";#### England ####"])):
    m, f = make(text, name="None" + str(len(text)), resources=["dogs"])
    p = plan(m, f, kind="resource", action="add", name="dogs", x=5, y=6)
    got = lines_of(p.text)
    i = got.index("resource\tdogs,\t5,\t6")
    window = got[i - want.index("resource\tdogs,\t5,\t6"):][:len(want)]
    check(f"with no resource at all, the first goes {label}",
          p.payload()["ok"] and window == want
          and all(t == "insert" for t, _, _ in hunks(text, p.text)))


# ---- 2) the search -------------------------------------------------------------
print("\n2) mapsnap: the nearest tile the caller's own rule accepts")

offs = mapsnap.offsets(3)
check("the start is asked first, then the four beside it",
      offs[0] == (0, 0) and set(offs[1:5]) == {(0, -1), (0, 1), (-1, 0), (1, 0)})
d2 = [dx * dx + dy * dy for dx, dy in offs]
check("and nothing further is asked before anything nearer", d2 == sorted(d2))
check(f"it stops at its radius: {len(mapsnap.offsets())} tiles within "
      f"{mapsnap.RADIUS}", all(dx * dx + dy * dy <= mapsnap.RADIUS ** 2
                               for dx, dy in mapsnap.offsets()))
wall = lambda x, y: x >= 7                                     # noqa: E731
check("on a 10x10 grid, the nearest tile right of a wall at x=7 from 2,5 is 7,5",
      mapsnap.nearest(10, 10, 2, 5, wall) == (7, 5))
check("a start off the grid is searched from its edge",
      mapsnap.nearest(10, 10, 40, 5, wall) == (9, 5))
check("and nothing inside the radius is None, not a far tile",
      mapsnap.nearest(200, 10, 0, 5, lambda x, y: x > 150) is None)
check("the sentence says where, how far and in which province",
      mapsnap.sentence((7, 5), (2, 5), "York") ==
      " The nearest tile that would do is 7,5, 5 tiles away, in York."
      and "no tile that would do within 40" in mapsnap.sentence(None, (0, 0)))


# ---- 3) the map a campaign reads -----------------------------------------------
print("\n3) campmap.campaign_map: a campaign's own copy wins, file by file")

roots = [m for m in _realmod.installed()
         if (m / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]
if not roots:
    print("  SKIPPED - no installed mod with a map")
for root in roots:
    rmod = Mod(root)
    base = campmap.CampaignMap(rmod)
    for camp in campstrat.campaign_paths(rmod):
        home = rmod.data / campstrat.CAMPAIGN_DIR_REL / campstrat.campaign_rel(camp)
        own = [n for n in campmap.MAP_FILES if (home / n).is_file()]
        got = campmap.campaign_map(rmod, camp, base)
        if own:
            check(f"{root.name}/{camp} ships {len(own)} map files of its own and "
                  f"reads them: {got.path('regions').parent.name}",
                  got is not base and got.path("regions") == home / "map_regions.tga"
                  and got is campmap.campaign_map(rmod, camp, base))
        else:
            check(f"{root.name}/{camp} ships none and reads the base map's object",
                  got is base)

if roots:
    src = roots[0]
    fake = tmp / "Split"
    (fake / "data" / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file() and pth.suffix in (".tga", ".txt"):
            shutil.copy2(pth, fake / "data" / campmap.BASE_REL / pth.name)
    cdir = fake / "data" / campstrat.CAMPAIGN_DIR_REL / "custom" / "Mine"
    cdir.mkdir(parents=True)
    shutil.copy2(src / "data" / campmap.BASE_REL / "map_heights.tga",
                 cdir / "map_heights.tga")
    fm = Mod(fake)
    split = campmap.campaign_map(fm, "custom/Mine")
    check("a campaign with only its own heights reads those and the base's regions",
          split.path("heights") == cdir / "map_heights.tga"
          and split.path("regions") == fm.data / campmap.BASE_REL / "map_regions.tga")


# ---- 4) every installed campaign ------------------------------------------------
print("\n4) the real files")

for root in roots:
    rmod = Mod(root)
    cm = campmap.CampaignMap(rmod)
    for camp in campstrat.campaign_paths(rmod):
        rf = mapquery.Facts(rmod, cm, camp)
        rs = rf.strat
        if rs is None or not rs.of_kind("resource"):
            continue
        v = stratobj.view(rf)
        res = [r for r in v["rows"] if r["kind"] == "resource"]
        codes = [f["code"] for r in res for f in r["findings"]]
        rep = mapcheck.run(rmod, campmap.map_of(rf), camp)
        dup = sum(1 for f in rep.findings if f.code == "strat.resource_duplicate")
        sea = sum(1 for f in rep.findings if f.code == "strat.resource_position"
                  and f.severity == "warn")
        check(f"{root.name}/{camp}: the panel and the validator agree - "
              f"{dup} duplicates, {sea} on sea",
              codes.count("res.duplicate") == dup and codes.count("res.sea") == sea)
        check("  no resource line has a fatal finding on a mod that loads",
              not [f for r in res for f in r["findings"] if f["fatal"]])
        voc = stratobj.Vocabulary(rmod, rs, campmap.map_of(rf))
        cen = stratobj.census(rs, voc)
        snapped = [(r, f) for r in v["rows"] for f in r["findings"] if f.get("near")]
        bad = []
        for r, f in snapped:
            nx, ny = f["near"]
            if voc.sea(nx, ny) or not voc.province_at(nx, ny) or \
                    (voc.ground(nx, ny) or {}).get("code") == "impassable_land":
                bad.append((r["line"], f["near"]))
            elif r["kind"] != "resource" and voc.marker(nx, ny):
                bad.append((r["line"], f["near"]))
            elif r["kind"] != "resource" and cen.tiles.get((nx, ny), set()) & {
                    "fort", "watchtower", "resource"}:
                bad.append((r["line"], f["near"]))
        check(f"  every one of the {len(snapped)} D10 answers is land, in a "
              f"province, and free", not bad)
        orig = rs.serialise()

        def rplan(**body):
            return stratobj.plan(rmod, rf, dict(body, campaign=camp))

        r = res[0]
        p = rplan(kind="resource", action="edit", line=r["line"], at=[r["x"], r["y"]],
                  x=r["x"] + 1, name=r["name"])
        h = hunks(orig, p.text)
        check(f"  an edit rewrites line {r['line']} and no other",
              p.payload()["ok"] and len(h) == 1 and h[0][1] == [r["text"]])
        p = rplan(kind="resource", action="delete", line=r["line"], at=[r["x"], r["y"]])
        check("  a delete takes out that one line",
              hunks(orig, p.text) == [("delete", [r["text"]], [])])
        reg = next((x for x in cm.index.regions if x.name and x.settlement), None)
        gx, gy = cm.game_xy(reg.settlement[0], reg.settlement[1])
        p = rplan(kind="resource", action="add", name=r["name"], x=gx, y=gy)
        check(f"  a {r['name']} on {reg.name}'s settlement pixel is allowed, and "
              f"said nothing about: the province that owns the marker owns it",
              p.payload()["ok"] and not [w for w in p.warnings if "settlement" in w]
              and all(t == "insert" for t, _, _ in hunks(orig, p.text)))
        if v["vocab"]["grouped_by"] == "province":
            lay = voc.layout
            mover = next(x for x in res if x["region"])
            other = next(x["region"] for x in res
                         if x["region"] and x["region"] != mover["region"])
            p = rplan(kind="resource", action="edit", line=mover["line"],
                      at=[mover["x"], mover["y"]], name=mover["name"], region=other)
            h = hunks(orig, p.text)
            check(f"  refiled from {mover['region']} to {other}: that line out and "
                  f"the same line in under the other heading",
                  p.action == "move" and [t for t, _, _ in h] == ["delete", "insert"]
                  and h[0][1] == h[1][2])
            none = next(x.name for x in cm.index.regions
                        if x.name and x.name.lower() not in lay.heads and x.settlement)
            nreg = next(x for x in cm.index.regions if x.name == none)
            nx, ny = cm.game_xy(nreg.settlement[0] + 1, nreg.settlement[1])
            p = rplan(kind="resource", action="add", name="iron", x=nx, y=ny)
            h = hunks(orig, p.text)
            prov = voc.province_at(nx, ny)
            check(f"  a new one in {prov}, which has no heading, opens one",
                  p.opened == prov and h and h[-1][2][-2:] == [f";{prov}", p.block.split("\n")[-1]])
        # D10 through a plan: a resource dropped on the sea is told where land is
        sea_tile = next(((x, y) for y in range(cm.terrain.height)
                         for x in range(0, cm.terrain.width, 7)
                         if voc.sea(x, y)), None)
        if sea_tile:
            p = rplan(kind="resource", action="add", name=r["name"], x=sea_tile[0],
                      y=sea_tile[1])
            if p.near:
                q = rplan(kind="resource", action="add", name=r["name"],
                          x=p.near[0], y=p.near[1])
                check(f"  a {r['name']} put on the sea at {sea_tile} is offered "
                      f"{p.near[0]},{p.near[1]}, and a plan there has no finding "
                      f"about the tile",
                      q.payload()["ok"] and not [f for f in q.findings
                                                 if f["code"] in stratobj.SNAPPED])


# ---- 5) the other two writers --------------------------------------------------
print("\n5) the snap for a character and for a settlement pixel")

if roots:
    rmod = Mod(roots[0])
    cm = campmap.CampaignMap(rmod)
    w, h = cm.terrain.width, cm.terrain.height
    sea = cm.sea
    # a sea tile with land three tiles east of it: a coast, not mid-ocean
    row = h // 2
    sx = next(x for x in range(w - 3) if sea[row * w + x] and sea[row * w + x + 1]
              and not sea[row * w + x + 3])
    gx, gy = cm.game_xy(sx, row)
    rf0 = mapquery.Facts(rmod, cm, CAMP)
    cv = stratchar.Vocabulary(rf0, rf0.strat)
    spec = stratchar.Spec(name="Bob", type="general", gender="male", age=30,
                          x=gx, y=gy)
    got = [f for f in stratchar.check_character(cv, spec, cm)
           if f["code"] == "char.adrift"]
    near = got[0].get("near") if got else None
    check(f"a general put on the sea at {gx},{gy} is told the nearest land: {near}",
          near is not None and not sea[cm.image_xy(*near)[1] * w + near[0]]
          and "nearest land" in got[0]["message"])
    spec.type = "admiral"
    spec.x, spec.y = near or (gx, gy)
    got = [f for f in stratchar.check_character(cv, spec, cm)
           if f["code"] == "char.aground"]
    near2 = got[0].get("near") if got else None
    check(f"and an admiral put on that land is told the nearest sea: {near2}",
          near2 is not None and sea[cm.image_xy(*near2)[1] * w + near2[0]])

    # a region tile the four marker rules refuse, and the wizard's answer
    data = cm.tiles("regions").tobytes()
    ground = mapcheck._triples(cm.tiles("ground_types"))
    feats = mapcheck._triples(cm.tiles("features"))
    found = None
    for r in cm.index.regions:
        if not r.name or not r.settlement:
            continue
        home = campmap.key(r.rgb)
        x0, y0 = r.settlement
        for dx, dy in mapsnap.offsets(6)[1:]:
            x, y = x0 + dx, y0 + dy
            if not (0 <= x < w and 0 <= y < h):
                continue
            p3 = (y * w + x) * 3
            if (data[p3] << 16) | (data[p3 + 1] << 8) | data[p3 + 2] != home:
                continue
            if any(f["fatal"] for f in mapcheck.marker_faults(
                    cm, (x, y), "settlement", ground, feats, sea)):
                found = (r, home, (x, y))
                break
        if found:
            break
    if found is None:
        print("  [skip] no refused tile near a settlement on this map")
    else:
        r, home, at = found
        said = campaint._marker_near(cm, data, home, at, "settlement")
        nums = [int(n) for n in said.split(" is ")[1].split(",")[:2]] \
            if " is " in said else None
        check(f"a settlement pixel refused at {at} in {r.name} is told: {said.strip()}",
              nums is not None and not any(f["fatal"] for f in mapcheck.marker_faults(
                  cm, tuple(nums), "settlement", ground, feats, sea)))


# ---- 6) the routes, a save and its undo ----------------------------------------
print("\n6) /api/map/object_plan|_apply for a resource")

if not roots:
    print("  SKIPPED - no campaign to serve")
else:
    from unittransfer.server import Handler, Registry, _Server
    cfg = Path(_tmp.mkdtemp(prefix="ut_stratres_cfg_"))
    config.CONFIG_DIR = cfg
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"
    config.BACKUP_DIR = cfg / "backups"
    src = next((m for m in roots if m.name.lower().startswith("divide")), roots[0])
    med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "ResMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file():
            shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
    camp_dir = data / campstrat.CAMPAIGN_DIR_REL / CAMP
    camp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
                 / campstrat.STRAT_NAME, camp_dir / campstrat.STRAT_NAME)
    if (src / "data" / "descr_sm_resources.txt").is_file():
        shutil.copy2(src / "data" / "descr_sm_resources.txt",
                     data / "descr_sm_resources.txt")
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} - {CAMP} copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    strat_path = camp_dir / campstrat.STRAT_NAME
    was = strat_path.read_bytes()
    try:
        d = get("/api/map/objects?mod=ResMod")
        check(f"/api/map/objects carries the resources: {d['counts']}",
              d["counts"].get("resource", 0) > 0
              and any(r["kind"] == "resource" and r["name"] for r in d["rows"])
              and d["vocab"]["resources"])
        cm = campmap.CampaignMap(Mod(med2 / "mods" / "ResMod"))
        reg = next(x for x in cm.index.regions if x.name and x.settlement)
        gx, gy = cm.game_xy(reg.settlement[0] + 1, reg.settlement[1])
        name = d["vocab"]["resources"][0]["name"]
        body = {"mod": "ResMod", "campaign": CAMP, "kind": "resource",
                "action": "add", "name": name, "x": gx, "y": gy}
        pl = post("/api/map/object_plan", body)
        check("a plan says what it would add and writes nothing",
              pl["plan"]["ok"] and strat_path.read_bytes() == was)
        res = post("/api/map/object_apply", body)
        check("the save answers with its line and a Log entry of its own kind",
              not res.get("error") and res["line"] > 0
              and res["record"]["action"] == "resource")
        marks = get("/api/map/markers?mod=ResMod")
        check("the markers layer draws it",
              any(i["kind"] == "resource" and i["x"] == gx and i["y"] == gy
                  and i["name"] == name for i in marks["items"]))
        mv = post("/api/map/object_apply", {
            "mod": "ResMod", "campaign": CAMP, "kind": "resource",
            "action": "edit", "line": res["line"], "at": [gx, gy], "name": name,
            "x": gx, "y": gy + 1})
        check("dragging it a tile is the same route with the new numbers",
              not mv.get("error"))
        post("/api/undo", {"id": mv["record"]["id"]})
        post("/api/undo", {"id": res["record"]["id"]})
        check("two undos put descr_strat.txt back byte for byte",
              strat_path.read_bytes() == was)
    finally:
        httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
