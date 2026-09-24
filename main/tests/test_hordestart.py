"""A horde start for a faction that holds nothing (Phase 72, D13).

    python -m tests.test_hordestart

A little map (two provinces, sea round them, one impassable tile), a
``descr_strat.txt`` with a faction that holds a city and one that holds
nothing, a small EDU, and a campaign script in the shape the real ones have.

What the suite holds down, in order:

    1  the script's shape: where a block goes, and the scripts refused
    2  the checks: what is fatal, what is a warning
    3  a write: the block, the flag, every other line untouched, and it
       reads back through 37a's reader and this module's own
    4  a rewrite and a remove leave the script byte for byte as it was
    5  a campaign with no script gets one; apply and the log's undo
    6  the installed mods, read only: every script placed, nothing written
    7  the two routes over HTTP: the tab's read, a plan, a write, a remove
"""
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, hordestart, mapquery, spawns
from unittransfer import keyblock as kb
from unittransfer.keyblock import read_text
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

CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


SCRIPT = joined(
    ";;; a campaign script",
    "script",
    "",
    "monitor_event PreFactionTurnStart FactionType england",
    "    spawn_army",
    "        faction\tengland",
    "        character\tAlfred, named character, age 30, x 3, y 6, family",
    "        unit\t\tPeasant Spearmen\t\texp 1 armour 0 weapon_lvl 0",
    "    end",
    "    terminate_monitor",
    "end_monitor",
    "",
    "wait_monitors",
    "end_script",
)

STRAT = joined(
    "campaign\t\timperial_campaign",
    "playable",
    "\tengland",
    "end",
    "unlockable",
    "end",
    "nonplayable",
    "\tmongols",
    "\tslave",
    "end",
    "",
    "start_date\t1080 summer",
    "end_date\t1530 winter",
    "timescale\t2.00",
    "",
    "faction\tengland, balanced smith",
    "ai_label\t\tcatholic",
    "denari\t10000",
    "settlement",
    "{",
    "\tlevel town",
    "\tregion Alpha_Province",
    "}",
    "character\tWilliam, named character, male, leader, age 40, , x 2, y 5",
    "army",
    "unit\t\tPeasant Spearmen\t\t\t\texp 1 armour 0 weapon_lvl 0",
    "",
    "faction\tmongols, balanced smith",
    "ai_label\t\tdefault",
    "denari\t10000",
    "",
    "faction\tslave, default",
    "ai_label\t\tdefault",
    "",
    "faction_standings\tengland,\t\t-1.0\tslave",
    "faction_relationships \tengland, at_war_with \tslave",
)

EDU = joined(
    "type             Peasant Spearmen",
    "dictionary       Peasant_Spearmen",
    "category         infantry",
    "class            spearmen",
    "ownership        england, slave",
    "",
    "type             Mongol Bodyguard",
    "dictionary       Mongol_Bodyguard",
    "category         cavalry",
    "class            heavy",
    "attributes       general_unit",
    "ownership        mongols",
    "",
    "type             Mongol Horse Archers",
    "dictionary       Mongol_Horse_Archers",
    "category         cavalry",
    "class            missile",
    "ownership        mongols",
)

W, H = 12, 8
SEA = (41, 140, 233)
A = (200, 110, 100)
B = (100, 200, 110)
PICTURE = [
    "............",
    ".AAA........",
    ".AAA........",
    "............",
    "............",
    "........BBB.",
    "........BBB.",
    "............",
]
LETTERS = {".": SEA, "A": A, "B": B}
REGIONS = (
    "Alpha_Province\r\n\tAlphaton\r\n\tnorthmen\r\n\tNorth_Rebels\r\n"
    f"\t{A[0]} {A[1]} {A[2]}\r\n\tnone\r\n\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Beta_Province\r\n\tBetaton\r\n\tnorthmen\r\n\tNorth_Rebels\r\n"
    f"\t{B[0]} {B[1]} {B[2]}\r\n\tnone\r\n\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
)
TERRAIN = (
    "dimensions\r\n{\r\n" + f"\twidth  {W}\r\n\theight  {H}\r\n" + "}\r\n"
    "heights\r\n{\r\n\tmin_sea_height  -3406.782\r\n"
    "\tmax_land_height  7511.272\r\n}\r\n"
    "roughness\r\n{\r\n\tmin  50.000\r\n\tmax  200.000\r\n}\r\n"
    "fractal\r\n{\r\n\tmultiplier  0.500\r\n}\r\n"
    "lattitude\r\n{\r\n\tmin  22.000\r\n\tmax  56.000\r\n}\r\n"
)
#: one tile of Beta is impassable: image (10, 6), which is game (10, 1)
IMPASSABLE = (10, 6)


def little_mod(script=SCRIPT, root=None):
    from PIL import Image
    from unittransfer import mapvocab
    root = Path(root or _tmp.mkdtemp(prefix="ut_hs_"))
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True)
    img = Image.new("RGB", (W, H))
    img.putdata([LETTERS[ch] for row in PICTURE for ch in row])
    img.save(base / "map_regions.tga")
    grids = {"tile": (W, H), "centre": (2 * W + 1, 2 * H + 1),
             "double": (2 * W, 2 * H), "advisory": (W, H), "free": (W, H)}
    for ly in campmap.LAYERS:
        if ly["code"] == "regions":
            continue
        if ly["code"] == "heights":
            hi = Image.new("RGB", grids["centre"], (0, 0, 0))
            for ri, row in enumerate(PICTURE):
                for ci, ch in enumerate(row):
                    if ch != ".":
                        for dy in (0, 1, 2):
                            for dx in (0, 1, 2):
                                hi.putpixel((2 * ci + dx, 2 * ri + dy), (200, 200, 200))
            hi.save(base / ly["file"])
            continue
        fill = {"ground_types": (0, 100, 0), "climates": (12, 90, 200),
                "fog": (255, 255, 255)}.get(ly["code"], (0, 0, 0))
        im = Image.new("RGB", grids[ly["size"]], fill)
        if ly["code"] == "ground_types":
            imp = mapvocab.ground("impassable_land")["rgb"]
            gx, gy = IMPASSABLE
            for dy in (0, 1):
                for dx in (0, 1):
                    im.putpixel((2 * gx + dx, 2 * gy + dy), tuple(imp))
        im.save(base / ly["file"])
    kb.write_text(base / "descr_regions.txt", REGIONS, campmap.ENCODING)
    kb.write_text(base / "descr_terrain.txt", TERRAIN, campmap.ENCODING)
    home = root / "data" / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
    home.mkdir(parents=True)
    kb.write_text(home / campstrat.STRAT_NAME, STRAT, campstrat.ENCODING)
    if script is not None:
        kb.write_text(home / "campaign_script.txt", script, campmap.ENCODING)
    kb.write_text(root / "data" / "export_descr_unit.txt", EDU, "latin-1")
    return Mod(root)


def facts_of(mod):
    return mapquery.Facts(mod, campmap.CampaignMap(mod), campstrat.DEFAULT_CAMPAIGN)


HORDE = [{"name": "Hulagu", "type": "named character", "age": 45, "x": 9, "y": 2,
          "units": [{"unit": "Mongol Bodyguard", "exp": 2},
                    {"unit": "Mongol Horse Archers", "exp": 1, "armour": 1}]},
         {"name": "Baidar", "type": "general", "age": 30, "x": 8, "y": 2,
          "units": [{"unit": "Mongol Horse Archers"}]}]


def plan(mod, facts, **body):
    return hordestart.plan(mod, facts, {"campaign": campstrat.DEFAULT_CAMPAIGN,
                                        "faction": "mongols", "turn": 40,
                                        "armies": HORDE, **body})


# ---- 1 ----------------------------------------------------------------------
print("\n1. the script's shape")

sh = hordestart.shape_of(SCRIPT)
check(f"a block goes in front of the last wait_monitors (line {sh.insert + 1})",
      not sh.error and sh.lines[sh.insert].strip() == "wait_monitors")
check("no script prologue is refused",
      "`script`" in hordestart.shape_of(joined("monitor_event X", "end_monitor",
                                                "wait_monitors", "end_script")).error)
check("no wait_monitors is refused, since no monitor would fire",
      "wait_monitors" in hordestart.shape_of(joined("script", "end_script")).error)
check("a marker opened and never closed is refused",
      "never closed" in hordestart.shape_of(joined(
          "script", ";;; horde start: mongols", "wait_monitors", "end_script")).error)
check("a wait_monitors in a comment does not count",
      hordestart.shape_of(joined("script", "; wait_monitors", "end_script")).error)


# ---- 2 ----------------------------------------------------------------------
print("\n2. the checks")

mod = little_mod()
facts = facts_of(mod)
sf = campstrat.read_strat(mod, campstrat.DEFAULT_CAMPAIGN)
arm = hordestart.armies_from_body


def codes(found):
    return {f["code"] for f in found}


def fatal(found):
    return {f["code"] for f in found if f["fatal"]}


clean = hordestart.check_armies(facts, sf, "mongols", 40, arm(HORDE))
check(f"the horde on dry land is clean of anything fatal: {sorted(codes(clean))}",
      not fatal(clean))
check("a turn that is not a whole number is fatal",
      "horde.turn" in fatal(hordestart.check_armies(facts, sf, "mongols", "soon", arm(HORDE))))
check("an army at sea is said, and not refused",
      "char.adrift" in codes(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], x=5, y=4)]))))
check("an army on impassable land is fatal",
      "horde.ground" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], x=10, y=1)]))))
check("an army off the map is fatal",
      "char.offmap" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], x=40, y=1)]))))
check("a unit the EDU lacks is fatal",
      "army.unknown" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], units=[{"unit": "Tanks"}])]))))
check("a unit whose ownership leaves the faction out is a warning",
      "horde.owner" in codes(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], units=[{"unit": "Peasant Spearmen"}])])))
      and "horde.owner" not in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], units=[{"unit": "Peasant Spearmen"}])]))))
check("21 regiments is one more than a stack holds",
      "horde.stack" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1,
          arm([dict(HORDE[0], units=[{"unit": "Mongol Horse Archers"}] * 21)]))))
check("an army with no regiment is fatal",
      "horde.no_units" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], units=[])]))))
check("a spy does not lead a spawned army",
      "horde.type" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], type="spy")]))))
check("a comma in a name is fatal, since the line is split on commas",
      "horde.name" in fatal(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], name="Hulagu, Khan")]))))
check("two armies on one tile warn",
      "horde.shared" in codes(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([HORDE[0], dict(HORDE[1], x=9, y=2)]))))
check("a tile a descr_strat.txt character starts on warns",
      "horde.occupied" in codes(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([dict(HORDE[0], x=2, y=5)]))))
check("no named character warns: nobody joins the family tree",
      "horde.leaderless" in codes(hordestart.check_armies(
          facts, sf, "mongols", 1, arm([HORDE[1]]))))


# ---- 3 ----------------------------------------------------------------------
print("\n3. a write")

p = plan(mod, facts)
check(f"the plan is clean: {p.errors}", not p.errors and p.script_text)
check("it writes two files: the script and descr_strat.txt",
      len(p.files()) == 2 and p.strat is not None)
before = SCRIPT.split("\n")
after = p.script_text.split("\n")
at = sh.insert
check("every line before the insertion point is the line that was there",
      after[:at] == before[:at])
check("and so is every line after the block, wait_monitors onwards",
      after[-(len(before) - at):] == before[at:])
check("the block is written with the script's own CRLF",
      all(ln.endswith("\r") for ln in after[at:len(after) - (len(before) - at)]))
back = [s for s in spawns.scan_text(p.script_text) if s.faction == "mongols"]
check(f"37a's reader finds both armies: {[(s.name, s.x, s.y, s.units) for s in back]}",
      [(s.name, s.type, s.x, s.y) for s in back]
      == [("Hulagu", "named character", 9, 2), ("Baidar", "general", 8, 2)]
      and back[0].units == ["Mongol Bodyguard", "Mongol Horse Archers"])
check("the named character is written into the family tree",
      "x 9, y 2, family" in p.script_text and "x 8, y 2, family" not in p.script_text)
check("the monitor fires on the rebels' turn at the turn asked for, once",
      "monitor_event FactionTurnStart FactionType slave" in p.script_text
      and "and I_TurnNumber = 40" in p.script_text
      and "terminate_monitor" in p.block)
got = hordestart.read_block(after, hordestart.shape_of(p.script_text).blocks["mongols"])
check(f"and this module reads its own block back: turn {got['turn']}",
      got["turn"] == 40 and [a["name"] for a in got["armies"]] == ["Hulagu", "Baidar"]
      and got["armies"][0]["units"][1] == {"unit": "Mongol Horse Archers", "exp": 1,
                                           "armour": 1, "weapon_lvl": 0}
      and got["armies"][0]["age"] == 45)
new_sf = campstrat.parse_strat(p.strat.text)
check("descr_strat.txt: mongols gets dead_until_resurrected",
      new_sf.faction("mongols").get("dead_until_resurrected"))
check("and england's block is untouched",
      p.strat.text.split(CR)[:28] == STRAT.split(CR)[:28])

p2 = plan(mod, facts, faction="england")
check("a faction that holds a city is not given the flag, and the plan says so",
      not p2.errors and p2.strat is None
      and any("reinforcements" in w for w in p2.warnings))
check("a faction with no block is refused",
      plan(mod, facts, faction="timurids").errors)
check("an opened script that changed on disk is refused",
      "changed on disk" in plan(mod, facts, sig="0" * 16).errors[0])


# ---- 4 ----------------------------------------------------------------------
print("\n4. a rewrite and a remove")

res = hordestart.apply(p)
check("applied, with both files backed up", sorted(res["record"]["manifest"]["backed_up"])
      == sorted(p.files()))
facts = facts_of(mod)
written = read_text(Path(mod.data) / p.script_rel, "latin-1")
d = hordestart.detail(facts)
row = next(r for r in d["factions"] if r["name"] == "mongols")
check("the tab finds the start it wrote, and the flag",
      row["start"] and row["start"]["turn"] == 40 and "dead_until_resurrected" in row["flags"]
      and row["homeless"])
check("england's scripted army is counted as scripted, not as a horde start",
      next(r for r in d["factions"] if r["name"] == "england")["scripted"] == 1)
p3 = plan(mod, facts, turn=55, armies=HORDE[:1], sig=d["sig"])
check("a second write replaces the block where it stands, and adds no flag twice",
      not p3.errors and p3.strat is None and written.count(";;; horde start") == 1
      and p3.script_text.count(";;; horde start") == 1
      and "I_TurnNumber = 55" in p3.script_text and "Baidar" not in p3.script_text)
w_lines = written.split("\n")
blk = hordestart.shape_of(written).blocks["mongols"]
n_lines = p3.script_text.split("\n")
nb = hordestart.shape_of(p3.script_text).blocks["mongols"]
check("and outside it the script is the same, line for line",
      n_lines[:nb[0]] == w_lines[:blk[0]] and n_lines[nb[1] + 1:] == w_lines[blk[1] + 1:])
rm = plan(mod, facts, action="remove")
check("remove gives back the script as it was before the first write, byte for byte",
      not rm.errors and rm.script_text == SCRIPT)
check("remove leaves descr_strat.txt alone and says so",
      rm.strat is None and any("Each faction" in w for w in rm.warnings))
check("remove with nothing written is refused",
      plan(little_mod(), facts_of(little_mod()), action="remove").errors)


# ---- 5 ----------------------------------------------------------------------
print("\n5. no script, apply and undo")

bare = little_mod(script=None)
bfacts = facts_of(bare)
pb = plan(bare, bfacts)
check(f"a campaign with no script gets one: {pb.script_rel}",
      not pb.errors and pb.script_new
      and pb.script_text.startswith("script\r\n")
      and pb.script_text.rstrip().endswith("wait_monitors\r\nend_script"))
check("which reads back as a script this module can place a block in",
      not hordestart.shape_of(pb.script_text).error)
rb = hordestart.apply(pb)
check("the new script is recorded as created, descr_strat.txt as backed up",
      rb["record"]["manifest"]["created"] == [pb.script_rel]
      and rb["record"]["manifest"]["backed_up"]
      == [f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.DEFAULT_CAMPAIGN}/descr_strat.txt"])
from unittransfer import transfer
transfer.undo(res["id"])
check("the log's undo puts both files of the first write back byte-exact",
      read_text(Path(mod.data) / p.script_rel, "latin-1") == SCRIPT
      and read_text(Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
                    / campstrat.DEFAULT_CAMPAIGN / "descr_strat.txt",
                    "latin-1") == STRAT)
transfer.undo(rb["id"])
check("and undoing the one that made a script takes the script away",
      not (Path(bare.data) / pb.script_rel).exists())


# ---- 6 ----------------------------------------------------------------------
print("\n6. the installed mods, read only")

mods = _realmod.installed()
if not mods:
    print("  SKIPPED - no installed mod to read")
for m in mods[:3]:
    real = Mod(m)
    for camp in (campstrat.DEFAULT_CAMPAIGN,):
        paths = spawns.script_paths(real, camp)
        if not paths:
            continue
        text = read_text(paths[0], "latin-1")
        s = hordestart.shape_of(text)
        check(f"{m.name}/{camp}: a block has a place ({s.error or 'line ' + str(s.insert + 1)})",
              not s.error)


# ---- 7 ----------------------------------------------------------------------
print("\n7. the routes")

from unittransfer.server import Handler, Registry, _Server

med2 = Path(_tmp.mkdtemp(prefix="ut_hsmed2_"))
little_mod(root=med2 / "mods" / "HordeMod")
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    det = get("/api/map/horde?mod=HordeMod")
    check("GET /api/map/horde lists every faction, mongols holding nothing",
          [f["name"] for f in det["factions"]] == ["england", "mongols", "slave"]
          and next(f for f in det["factions"] if f["name"] == "mongols")["homeless"]
          and det["exists"] and not det["error"])
    body = {"mod": "HordeMod", "faction": "mongols", "turn": 12, "armies": HORDE,
            "sig": det["sig"]}
    pl = post("/api/map/horde_plan", body)
    check("POST horde_plan answers with the plan and writes nothing",
          pl["plan"]["ok"] and "error" not in pl
          and ";;; horde start" not in read_text(
              med2 / "mods" / "HordeMod" / "data" / pl["plan"]["files"][0], "latin-1"))
    ap = post("/api/map/horde_apply", body)
    check("POST horde_apply writes it, with a log record",
          ap.get("id") and ap["record"]["action"] == "horde")
    det = get("/api/map/horde?mod=HordeMod")
    row = next(f for f in det["factions"] if f["name"] == "mongols")
    check("and the tab reads it back on turn 12, with the flag",
          row["start"]["turn"] == 12 and "dead_until_resurrected" in row["flags"])
    marks = get("/api/map/spawns?mod=HordeMod")
    check("the markers layer's spawn reader sees both armies",
          len([r for r in marks.get("rows", []) if r["faction"] == "mongols"]) == 2)
    rm = post("/api/map/horde_apply", {"mod": "HordeMod", "faction": "mongols",
                                        "action": "remove", "sig": det["sig"]})
    check("remove through the route gives the script back as it was",
          rm.get("id") and read_text(med2 / "mods" / "HordeMod" / "data"
                                     / det["script"], "latin-1") == SCRIPT)
finally:
    httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
