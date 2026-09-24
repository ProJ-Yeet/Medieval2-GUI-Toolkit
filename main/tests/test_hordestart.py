"""Phase 72, D13 - a horde start for a faction that holds nothing.

Built on a throwaway mod written here, so it runs with no game installed: one
settled faction, one horde to copy from (``mongols``), and one new faction
(``khazars``) in the shape 16j-2 leaves - a block with a purse and nothing in
it. The map is a stand-in with the one thing the rules ask of it, which tiles
are sea.

    1  what the tab is shown: the donor, the owned units, the free names
    2  the horde in descr_sm_factions.txt: all seven numbers and the units, in place
    3  a start on the map: generals written by 16i's writer, the flag taken off
    4  a start on a date: the flag, the event, its text and its picture
    5  what is refused, and what is only said
    6  the save: every file under one backup, and one Undo puts all of it back

    python -m tests.test_hordestart
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import (campevents, campstrat, config, factions, hordestart,
                          transfer)
from unittransfer import keyblock as kb

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


cfg = Path(_tmp.mkdtemp(prefix="ut_hs_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

SM = joined(
    ";; factions",
    "faction\t\t\t\t\tengland",
    "culture\t\t\t\t\tnorthern_european",
    "religion\t\t\t\tcatholic",
    "can_sap\t\t\t\t\tno",
    "",
    "faction\t\t\t\t\tmongols",
    "culture\t\t\t\t\tmiddle_eastern",
    "religion\t\t\t\tpagan",
    "horde_min_units\t\t\t\t12",
    "horde_max_units\t\t\t\t18",
    "horde_max_units_reduction_every_horde\t6",
    "horde_unit_per_settlement_population\t300",
    "horde_min_named_characters\t\t3",
    "horde_max_percent_army_stack\t\t70",
    "horde_disband_percent_on_settlement_capture\t5",
    "horde_unit\t\t\t\tMongol Horse Archers",
    "horde_unit\t\t\t\tMongol Lancers",
    "can_sap\t\t\t\t\tno",
    "",
    "faction\t\t\t\t\tkhazars",
    "culture\t\t\t\t\tmiddle_eastern",
    "religion\t\t\t\tpagan",
    "can_sap\t\t\t\t\tno",
    "prefers_naval_invasions\t\tno",
)

STRAT = joined(
    "campaign\t\timperial_campaign",
    "playable",
    "\tengland",
    "end",
    "nonplayable",
    "\tmongols",
    "\tkhazars",
    "end",
    "",
    "start_date\t1080 summer",
    "end_date\t1530 winter",
    "",
    "faction\tengland, balanced smith",
    "ai_label\t\tcatholic",
    "denari\t10000",
    "settlement",
    "{",
    "\tlevel town",
    "\tregion London_Province",
    "}",
    "",
    "character\tWilliam, named character, leader, age 30, , x 10, y 10 ",
    "army",
    "unit\t\tNE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0",
    "",
    "faction\tmongols, fs_fort",
    "ai_label\t\tdefault",
    "dead_until_resurrected",
    "denari\t10000",
    "",
    "faction\tkhazars, fs_fort",
    "ai_label\t\tdefault",
    "denari\t5000",
    "",
    "faction_standings\tengland,\t\t-0.2\tmongols",
    "",
    "region London_Province",
    "farming_level 3",
)

EVENTS = (
    "; emergent_faction - triggers the emergence of the given faction.\r\n"
    "\r\n"
    "event\thistoric\tfirst_windmill\r\n"
    "date\t50\r\n"
    "\r\n"
    "event\temergent_faction\tmongols\r\n"
    "date\t128 144\r\n"
    "position\t30, 5"
)

NAMES = ("faction: khazars\n\tcharacters\n\t\tBulan\n\t\tObadiah\n\t\tJoseph\n"
         "faction: england\n\tcharacters\n\t\tWilliam\n")


class _Unit:
    def __init__(self, name, owners, general=False):
        self.type, self.ownership = name, owners
        self.category, self.class_type = "cavalry", "missile"
        self.attributes = ["general_unit"] if general else []


class _Edu:
    units = [_Unit("NE Bodyguard", ["england"], True),
             _Unit("Khazar Bodyguard", ["khazars"], True),
             _Unit("Khazar Horse Archers", ["khazars"]),
             _Unit("Mongol Horse Archers", ["mongols"]),
             _Unit("Mongol Lancers", ["mongols"]),
             _Unit("Peasants", ["all"])]


class _Mod:
    def __init__(self, root):
        self.root = Path(root)
        self.name = self.root.name
        self.data = self.root / "data"
        self.edu = _Edu()


class _Terrain:
    def __init__(self, w, h):
        self.width, self.height = w, h

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def game_y(self, y):
        return self.height - 1 - y


class _Map:
    """A 40x20 map whose left half is land and right half sea."""

    def __init__(self):
        self.terrain = _Terrain(40, 20)
        self.sea = [x >= 20 for y in range(20) for x in range(40)]

    def image_xy(self, x, gy):
        return x, self.terrain.game_y(gy)

    def game_xy(self, x, y):
        return x, self.terrain.game_y(y)


class _Facts:
    def __init__(self, mod):
        self.mod, self.campaign, self.skipped = mod, "imperial_campaign", []
        self.cm = _Map()


def fresh(events=True, pictures=True, text=True):
    root = Path(_tmp.mkdtemp(prefix="ut_hs_"))
    data = root / "data"
    camp = data / "world/maps/campaign/imperial_campaign"
    camp.mkdir(parents=True)
    (data / "descr_sm_factions.txt").write_bytes(SM.encode("latin-1"))
    (camp / "descr_strat.txt").write_bytes(STRAT.encode("latin-1"))
    if events:
        (camp / "descr_events.txt").write_bytes(EVENTS.encode("latin-1"))
    (data / "descr_names.txt").write_bytes(NAMES.encode("latin-1"))
    if text:
        (data / "text").mkdir()
        (data / "text/historic_events.txt").write_text(
            "﻿¬ events\r\n{FIRST_WINDMILL_TITLE}Windmill\r\n"
            "{FIRST_WINDMILL_BODY}A windmill.\r\n", encoding="utf-16-le")
    if pictures:
        for culture in ("middle_eastern", "northern_european"):
            pics = data / "ui" / culture / "eventspic"
            pics.mkdir(parents=True)
            (pics / "first_windmill.tga").write_bytes(b"TGA-" + culture.encode())
            (pics / "mongols.tga").write_bytes(b"MONGOL-" + culture.encode())
    mod = _Mod(root)
    return mod, _Facts(mod)


def snapshot(mod):
    return {p.relative_to(mod.data).as_posix(): p.read_bytes()
            for p in sorted(mod.data.rglob("*")) if p.is_file()}


DONOR = {"horde_min_units": "12", "horde_max_units": "18",
         "horde_max_units_reduction_every_horde": "6",
         "horde_unit_per_settlement_population": "300",
         "horde_min_named_characters": "3", "horde_max_percent_army_stack": "70",
         "horde_disband_percent_on_settlement_capture": "5"}
UNITS = ["Khazar Horse Archers", "Peasants"]


# ---- 1) the view ---------------------------------------------------------------
print("1) what the Horde start tab is shown")

mod, facts = fresh()
v = hordestart.view(mod, facts)
f = v["faction"]
check("with no faction asked for, the first one that holds nothing is offered",
      f and f["name"] == "mongols")
v = hordestart.view(mod, facts, "khazars")
f = v["faction"]
check("each faction is listed with what it holds",
      [(x["name"], x["settlements"], x["characters"], x["dormant"])
       for x in v["factions"]]
      == [("england", 1, 1, False), ("mongols", 0, 0, True),
          ("khazars", 0, 0, False)])
check("the mod's own horde is the donor, with all seven numbers and its units",
      [d["faction"] for d in f["donors"]] == ["mongols"]
      and f["donors"][0]["keys"] == DONOR
      and f["donors"][0]["units"] == ["Mongol Horse Archers", "Mongol Lancers"])
check("the units the EDU lets it own come first, `all` included",
      f["owned"] == ["Khazar Bodyguard", "Khazar Horse Archers", "Peasants"]
      and f["bodyguards"] == ["Khazar Bodyguard"])
check("names come out of its own pool", f["names"] == ["Bulan", "Obadiah", "Joseph"])
check("it has no event, no text and no picture yet, and the picture to copy is "
      "one every folder has",
      f["event"] is None and not f["text"]["title"] and not f["has_picture"]
      and f["pictures"] == ["first_windmill", "mongols"]
      and len(f["eventspic"]) == 2)
check("the map's size is handed over for the position boxes", v["size"] == [40, 20])
check("the donor's event is read back as dates and positions",
      hordestart.view(mod, facts, "mongols")["faction"]["event"]["positions"]
      == [[30, 5]])


# ---- 2) descr_sm_factions ------------------------------------------------------
print("\n2) the horde, in descr_sm_factions.txt")

gen = {"name": "Bulan", "age": 40, "x": 5, "y": 5,
       "army": ["Khazar Bodyguard", "Khazar Horse Archers"]}
p = hordestart.plan(mod, facts, {"faction": "khazars", "mode": "map",
                                 "keys": DONOR, "units": UNITS,
                                 "generals": [gen]})
check("a clean plan: " + "; ".join(p.errors), p.payload()["ok"])
sm = p.texts["descr_sm_factions.txt"]
rec = factions.parse_text(sm).get("khazars")
check("all seven numbers are written, so 11's all-or-none rule holds",
      all(rec.get(k) == DONOR[k] for k in factions.HORDE_KEYS)
      and not [x for x in factions.check_file(factions.parse_text(sm))
               if x["name"] == "khazars" and "horde" in x["kind"]])
check("and the units, in order", [r.value for r in rec.repeats] == UNITS)
lines = sm.split(CR)
at = lines.index("horde_unit\t\t\t\tKhazar Horse Archers")
check("the first horde_unit lines go under the last horde number, before can_sap",
      lines[at - 1].startswith("horde_disband_percent_on_settlement_capture")
      and lines[at + 2].startswith("can_sap"))
check("in the column the record's own values are in",
      kb.value_column(lines[at], "horde_unit")
      == kb.value_column("culture\t\t\t\t\tmiddle_eastern", "culture"))
before = SM.split(CR)
check("nothing outside khazars' record moves",
      sm.split(CR)[:21] == before[:21])

p2 = hordestart.plan(mod, facts, {"faction": "mongols", "mode": "emerge",
                                  "keys": dict(DONOR, horde_max_units="20"),
                                  "units": ["Mongol Lancers"],
                                  "dates": ["128 144"], "positions": [[30, 5]],
                                  "picture_from": "mongols"})
sm2 = p2.texts.get("descr_sm_factions.txt", "")
rec2 = factions.parse_text(sm2).get("mongols")
check("a horde that is already there is edited in place: " + "; ".join(p2.errors),
      rec2 and rec2.get("horde_max_units") == "20"
      and [r.value for r in rec2.repeats] == ["Mongol Lancers"]
      and "horde_max_units\t\t\t\t20" in sm2.split(CR))


# ---- 3) on the map -------------------------------------------------------------
print("\n3) a start on the map")

strat = p.texts["world/maps/campaign/imperial_campaign/descr_strat.txt"]
sf = campstrat.parse_strat(strat)
k = sf.faction("khazars")
people = sf.descendants_of(k, "character")
check("the general is in khazars' block, the leader, where he was put",
      [(c.name, c.get("rank"), c.get("x"), c.get("y")) for c in people]
      == [("Bulan", "leader", 5, 5)])
check("with his army",
      [u.name for u in sf.descendants_of(k, "unit")]
      == ["Khazar Bodyguard", "Khazar Horse Archers"])
check("and every other faction's block is byte for byte what it was",
      strat.split(CR)[:30] == STRAT.split(CR)[:30]
      and strat.split(CR)[-6:] == STRAT.split(CR)[-6:])

two = hordestart.plan(mod, facts, {
    "faction": "khazars", "mode": "map", "keys": DONOR, "units": UNITS,
    "generals": [gen, {"name": "Obadiah", "x": 8, "y": 12,
                       "army": ["Khazar Horse Archers"]}]})
sf2 = campstrat.parse_strat(two.texts[
    "world/maps/campaign/imperial_campaign/descr_strat.txt"])
people = sf2.descendants_of(sf2.faction("khazars"), "character")
check("two generals, one leader, in the order given, the second at the default age",
      [(c.name, c.get("rank") or "", c.get("age")) for c in people]
      == [("Bulan", "leader", 40), ("Obadiah", "", 30)])

m = hordestart.plan(mod, facts, {
    "faction": "mongols", "mode": "map", "keys": DONOR, "units": UNITS,
    "generals": [dict(gen, army=["Mongol Lancers"])]})
ms = campstrat.parse_strat(m.texts[
    "world/maps/campaign/imperial_campaign/descr_strat.txt"])
check("a dormant faction started on the map loses its dead_until_resurrected",
      not ms.faction("mongols").get("dead_until_resurrected")
      and any("dead_until_resurrected" in c for c in m.changes))
check("and the emergence it still has is said, not deleted",
      any("emergent_faction mongols" in w for w in m.warnings)
      and "descr_events.txt" not in " ".join(m.texts))


# ---- 4) on a date --------------------------------------------------------------
print("\n4) a start on a date")

e = hordestart.plan(mod, facts, {
    "faction": "khazars", "mode": "emerge", "keys": DONOR, "units": UNITS,
    "dates": ["100 110"], "positions": [[4, 6], "9, 3"],
    "title": "The Khazars", "text": "They come.",
    "picture_from": "first_windmill"})
check("a clean plan: " + "; ".join(e.errors), e.payload()["ok"])
es = campstrat.parse_strat(e.texts[
    "world/maps/campaign/imperial_campaign/descr_strat.txt"])
check("khazars starts dormant, the flag where vanilla's Mongols write theirs",
      es.faction("khazars").get("dead_until_resurrected")
      and es.lines[es.faction("khazars").start + 2] == "dead_until_resurrected")
ev = e.texts["world/maps/campaign/imperial_campaign/descr_events.txt"]
bf = campevents.parse_events(ev)
b = [x for x in bf.blocks if x.kind == "emergent_faction" and x.name == "khazars"]
check("the event is appended, with its date and both positions",
      len(b) == 1 and b[0].all("date") == ["100 110"]
      and [(q.x, q.y) for q in b[0].positions] == [(4, 6), (9, 3)])
check("…after the file's last line, which had no newline, and nothing above it "
      "changes", ev.startswith(EVENTS + CR + CR))
check("its title and body are written as {KHAZARS_TITLE} and {KHAZARS_BODY}",
      e.loc_writes == {"KHAZARS_TITLE": "The Khazars", "KHAZARS_BODY": "They come."})
check("and a picture is copied into both eventspic folders",
      sorted(t for _f, t in e.copies)
      == ["ui/middle_eastern/eventspic/khazars.tga",
          "ui/northern_european/eventspic/khazars.tga"])

again = hordestart.plan(mod, facts, {
    "faction": "mongols", "mode": "emerge", "keys": DONOR,
    "units": ["Mongol Lancers"], "dates": ["130"], "positions": [[31, 6]]})
ab = campevents.parse_events(again.texts[
    "world/maps/campaign/imperial_campaign/descr_events.txt"])
mb = [x for x in ab.blocks if x.kind == "emergent_faction"]
check("an emergence already there is rewritten in place, not added twice",
      len(mb) == 1 and mb[0].all("date") == ["130"]
      and [(q.x, q.y) for q in mb[0].positions] == [(31, 6)])
check("a faction already dormant is not flagged twice",
      "world/maps/campaign/imperial_campaign/descr_strat.txt" not in again.texts)
check("a picture it already has is not copied", not again.copies)
check("sea is said, not refused: " + "; ".join(again.warnings),
      any("31,6 is sea" in w for w in again.warnings) and not again.errors)

nomod = fresh(events=False, pictures=False, text=False)
n = hordestart.plan(nomod[0], nomod[1], {
    "faction": "khazars", "mode": "emerge", "keys": DONOR, "units": UNITS,
    "dates": ["100"], "positions": [[4, 6]]})
check("a campaign with no descr_events.txt gets one with the event in it",
      campevents.parse_events(n.texts[
          "world/maps/campaign/imperial_campaign/descr_events.txt"]).blocks[0].name
      == "khazars" and not n.errors)
check("with no text file at all, that is said rather than written",
      not n.loc_writes and any("historic_events" in w for w in n.warnings))
check("and with no eventspic folder there is no picture to copy", not n.copies)


# ---- 5) refusals ---------------------------------------------------------------
print("\n5) what is refused, and what is only said")


def errs(body, where=(mod, facts)):
    got = hordestart.plan(where[0], where[1],
                          dict({"keys": DONOR, "units": UNITS}, **body))
    return " | ".join(got.errors), got


msg, _ = errs({"faction": "england", "mode": "map", "generals": [gen]})
check("a faction with a settlement is refused, and the settlement is named: " + msg,
      "London_Province" in msg)
msg, _ = errs({"faction": "nobody", "mode": "map", "generals": [gen]})
check("a faction with no block points at the New faction tab: " + msg,
      "New faction" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "generals": []})
check("a map start with no general is refused", "at least one general" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map",
               "generals": [dict(gen, army=[])]})
check("a general with no army is refused", "no army" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map",
               "generals": [dict(gen, army=["Peasants"] * 21)]})
check("a stack of 21 is refused", "a stack holds 20" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map",
               "generals": [dict(gen, x=50)]})
check("a general off the map is refused (16i's own rule): " + msg,
      "off the 40x20" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map",
               "generals": [gen, dict(gen, x=6)]})
check("two generals of one name are refused", "Two generals are called" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "units": ["Nobody"],
               "generals": [gen]})
check("a horde unit the EDU does not declare is refused", "Nobody" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "units": [],
               "generals": [gen]})
check("no horde unit at all is refused", "nothing to spawn" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "generals": [gen],
               "keys": dict(DONOR, horde_min_units="30")})
check("fewer most units than least is refused", "more than the most" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "generals": [gen],
               "keys": dict(DONOR, horde_max_percent_army_stack="120")})
check("a share over 100 is refused", "share of 100" in msg)
msg, _ = errs({"faction": "khazars", "mode": "map", "generals": [gen],
               "keys": dict(DONOR, horde_min_units="")})
check("a blank number is refused, so a half horde is never written",
      "not a whole number" in msg)
msg, _ = errs({"faction": "khazars", "mode": "emerge", "dates": [],
               "positions": [[4, 6]], "picture_from": "mongols"})
check("an emergence with no date is refused", "never fires" in msg)
msg, _ = errs({"faction": "khazars", "mode": "emerge", "dates": ["100"],
               "positions": [[4, 6]]})
check("an emergence with no picture to copy is refused, because a missing one "
      "crashes", "crashes the campaign" in msg)
msg, _ = errs({"faction": "khazars", "mode": "emerge", "dates": ["100"],
               "positions": [[4, 99]], "picture_from": "mongols"})
check("a position off the map is refused", "off the 40x20" in msg)
_, got = errs({"faction": "khazars", "mode": "emerge", "dates": ["100"],
               "positions": [], "picture_from": "mongols"})
check("no position is a warning, not a refusal",
      not got.errors and any("where the horde comes in" in w for w in got.warnings))
_, got = errs({"faction": "khazars", "mode": "map",
               "generals": [dict(gen, name="Zog")]})
check("a name outside the faction's pool is 16i's warning",
      not got.errors and any("Zog is not in khazars" in w for w in got.warnings))

# a dormant faction whose block already holds a person cannot emerge
mod3, facts3 = fresh()
path = mod3.data / "world/maps/campaign/imperial_campaign/descr_strat.txt"
path.write_bytes(p.texts["world/maps/campaign/imperial_campaign/descr_strat.txt"]
                 .encode("latin-1"))
msg, _ = errs({"faction": "khazars", "mode": "emerge", "dates": ["100"],
               "positions": [[4, 6]], "picture_from": "mongols"}, (mod3, facts3))
check("an emergence for a faction with people in it is refused: " + msg,
      "already has 1 character" in msg)
msg, _ = errs({"faction": "khazars", "mode": "sideways", "generals": [gen]})
check("an unknown start is refused", "not 'sideways'" in msg)


# ---- 6) the save and its undo ---------------------------------------------------
print("\n6) the save, and one Undo")

mod4, facts4 = fresh()
was = snapshot(mod4)
body = {"faction": "khazars", "mode": "emerge", "keys": DONOR, "units": UNITS,
        "dates": ["100 110"], "positions": [[4, 6]], "title": "The Khazars",
        "text": "They come.", "picture_from": "first_windmill"}
res = hordestart.apply(hordestart.plan(mod4, facts4, body))
now = snapshot(mod4)
changed = sorted(k for k in now if now.get(k) != was.get(k))
check("every file the plan named is written, and nothing else: "
      + ", ".join(changed),
      changed == ["descr_sm_factions.txt",
                  "text/historic_events.txt",
                  "text/historic_events.txt.strings.bin",
                  "ui/middle_eastern/eventspic/khazars.tga",
                  "ui/northern_european/eventspic/khazars.tga",
                  "world/maps/campaign/imperial_campaign/descr_events.txt",
                  "world/maps/campaign/imperial_campaign/descr_strat.txt"])
check("the picture is the one it was copied from",
      now["ui/middle_eastern/eventspic/khazars.tga"] == b"TGA-middle_eastern")
pairs = campevents.event_text_pairs(mod4)
check("the text reads back", pairs.get("KHAZARS_TITLE") == "The Khazars"
      and pairs.get("FIRST_WINDMILL_TITLE") == "Windmill")
check("the event file now passes 18b's own checks for this event",
      not [x for x in campevents.check_events(
          campevents.read_events(mod4)[0], mod4) if x.get("name") == "khazars"])
check("one log entry", res["record"]["action"] == "horde_start")
transfer.undo(res["id"])
check("and one Undo puts every byte back, the new files removed",
      snapshot(mod4) == was)

mod5, facts5 = fresh()
was = snapshot(mod5)
res = hordestart.apply(hordestart.plan(mod5, facts5, {
    "faction": "khazars", "mode": "map", "keys": DONOR, "units": UNITS,
    "generals": [gen]}))
check("a map start writes two files",
      sorted(res["files"]) == ["descr_sm_factions.txt",
                               "world/maps/campaign/imperial_campaign/descr_strat.txt"])
transfer.undo(res["id"])
check("and undoes to the byte", snapshot(mod5) == was)


# ---- 7) the routes ---------------------------------------------------------------
print("\n7) /api/map/horde and /api/map/horde_plan|_apply")

import json  # noqa: E402
import threading  # noqa: E402
import urllib.request  # noqa: E402

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

mod6, facts6 = fresh()
reg = Registry(cfg / "icons")
reg.names = lambda: [mod6.name]
reg.describe = lambda name: mod6
reg.map_facts = lambda name, campaign="": facts6
reg.invalidate = lambda name: None
# every detail route reads the map first; this mod's map is the stand-in
reg.campaign_map = lambda name: facts6.cm
reg.map_for = lambda name, campaign="": facts6.cm
Handler.registry = reg
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


got = call(f"/api/map/horde?mod={mod6.name}&faction=khazars")
check("the tab's view comes back over HTTP",
      got.get("faction", {}).get("name") == "khazars"
      and got["faction"]["donors"][0]["faction"] == "mongols")
was = snapshot(mod6)
body = {"mod": mod6.name, "faction": "khazars", "mode": "map", "keys": DONOR,
        "units": UNITS, "generals": [gen]}
got = call("/api/map/horde_plan", body)
check("a plan writes nothing", got["plan"]["ok"] and snapshot(mod6) == was)
got = call("/api/map/horde_plan", dict(body, generals=[dict(gen, x=99)]))
check("a refused plan comes back with its reason as the error",
      "off the 40x20" in got.get("error", ""))
got = call("/api/map/horde_apply", body)
check("apply writes both files and logs one entry",
      got.get("record", {}).get("action") == "horde_start"
      and sorted(got["files"]) == ["descr_sm_factions.txt",
                                   "world/maps/campaign/imperial_campaign/descr_strat.txt"])
transfer.undo(got["id"])
check("and its undo puts the mod back", snapshot(mod6) == was)
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
if not all(ok):
    print("FAILED")
    sys.exit(1)
print("ALL PASSED")
