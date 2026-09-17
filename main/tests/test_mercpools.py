"""``descr_mercenaries.txt`` - Phase 32a.

Four claims under test:

    a unit line is read whole   the five fixed fields and every optional,
                                the name being everything in front of `exp`
    the file comes back         parse_text(t).text() == t on every campaign on
                                this machine, CRLF and a missing final newline
    an edit is a splice         one field set, added or taken off moves nothing
                                else on the line, and the tab columns stay
    one reader                  mapquery.parse_mercenaries and 18a's G3 writer
                                both go through this module

Five parts:

    1  unit lines written here
    2  the file's edits
    3  plan: the six actions, refusals and warnings
    4  every campaign on this machine
    5  plan and apply against a copy of a real campaign

    python -m tests.test_mercpools
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campfiles, campstrat, keyblock as kb, mapquery, mercpools as mp
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


LINE = ("\tunit Raider Warband,\t\texp 0 cost 270 replenish 0.25 - 0.35 max 4 "
        "initial 3 religions { catholic } crusading")

MERCS = (
    "; pool    --> name of mercenary pool\r\n"
    ";RATE_H replenish 0.03 - 0.15 Common Ships\t\tavg 0.09\r\n"
    "\r\n"
    "pool Mordor\r\n"
    "\tregions Gorgoroth_Province Udun_Province\r\n"
    + LINE + "\r\n"
    "\tunit Orc Maulers,\t\t\texp 0 cost 510 replenish 0.05 - 0.09 max 2 initial 1  "
    "religions { catholic orthodox } events { ND_BOH }\r\n"
    ";\tunit merc cog,\t\t\texp 0 cost 400 replenish 0.1 - 0.2 max 1 initial 0\r\n"
    "\r\n"
    "pool Rhun\r\n"
    "\tregions Rhun_Province ; the east\r\n"
    "\tunit Easterlings\texp 1 cost 300 replenish 0.1 - 0.2 max 2 initial 1 "
    "start_year 3000 events { a b } factions { timurids }\r\n"
    "\r\n"
    "pool Empty\r\n"
    "\tunit Nobody,\texp 0 cost 1 replenish 0.1 - 0.1 max 1 initial 1"
)


print("1  unit lines written here")
u = mp.parse_unit(LINE)
check("the name is everything in front of exp, the comma gone", u.name == "Raider Warband")
check("the five fixed fields", (u.exp, u.cost, u.replenish, u.max, u.initial)
      == (0, 270, (0.25, 0.35), 4, 3))
check("a list and a flag", u.religions == ["catholic"] and u.crusading)
check("nothing it did not know", not u.fault and not u.extra)
e = mp.parse_unit("\tunit Easterlings\texp 1 cost 300 replenish 0.1 - 0.2 max 2 initial 1 "
                  "start_year 3000 events { a b } factions { timurids }")
check("a name with no comma, a year, events and factions",
      e.name == "Easterlings" and e.start_year == 3000 and e.events == ["a", "b"]
      and e.factions == ["timurids"] and e.religions is None and not e.crusading)
check("`replenish lo-hi` as one word reads too",
      mp.parse_unit("unit X exp 0 cost 1 replenish 0.1-0.2 max 1 initial 1").replenish
      == (0.1, 0.2))
odd = mp.parse_unit("unit Y exp 0 cost 1 replenish 0.1 - 0.2 max 1 initial 1 garrison { x }")
check("an option word the format has not got is kept and reported",
      odd.extra[0] == "garrison" and "garrison" in odd.fault)
check("a line with no exp is a fault, not a crash",
      mp.parse_unit("unit Broken cost 5").fault == "no `exp` on the line")
check("a missing fixed field is a fault",
      "initial" in mp.parse_unit("unit Z exp 0 cost 1 replenish 0.1 - 0.2 max 1").fault)

check("setting a value replaces only its characters",
      mp.set_field(LINE, "cost", 999) == LINE.replace("cost 270", "cost 999"))
check("the same replenish written shorter is not an edit",
      mp.set_field(LINE.replace("0.35", "0.350"), "replenish", [0.25, 0.35])
      == LINE.replace("0.35", "0.350"))
check("setting replenish",
      mp.set_field(LINE, "replenish", [0.1, "0.2"]) == LINE.replace("0.25 - 0.35", "0.1 - 0.2"))
check("setting a list",
      mp.set_field(LINE, "religions", ["catholic", "islam"])
      == LINE.replace("{ catholic }", "{ catholic islam }"))
check("adding an option goes on the end",
      mp.set_field(LINE, "events", "ND_BOH") == LINE + " events { ND_BOH }")
check("taking one off takes its space with it",
      mp.set_field(LINE, "religions", None) == LINE.replace(" religions { catholic }", ""))
check("the flag off, and back on",
      mp.set_field(LINE, "crusading", False) == LINE[:-len(" crusading")]
      and mp.set_field(LINE[:-len(" crusading")], "crusading", True) == LINE)
check("renaming keeps the comma and the tab columns",
      mp.set_field(LINE, "name", "Orc Raiders") == LINE.replace("Raider Warband", "Orc Raiders"))
check("a comment after the line survives an added option",
      mp.set_field("unit A exp 0 cost 1 replenish 0 - 0 max 1 initial 1 ; note",
                   "start_year", 5)
      == "unit A exp 0 cost 1 replenish 0 - 0 max 1 initial 1 start_year 5 ; note")
for key, value in [("cost", "x"), ("cost", -1), ("exp", 10), ("replenish", [1]),
                   ("religions", ["a{"]), ("cost", None), ("name", "a exp b"),
                   ("colour", 1)]:
    try:
        mp.set_field(LINE, key, value)
        refused = False
    except mp.MercError:
        refused = True
    check(f"{key} = {value!r} is refused", refused)


print("\n2  the file's edits")
mf = mp.parse_text(MERCS)
check("it comes back byte for byte", mf.text() == MERCS)
check("three pools, the commented unit not one of them",
      [(p.name, len(p.units)) for p in mf.pools] == [("Mordor", 2), ("Rhun", 1), ("Empty", 1)])
check("regions, with the comment off them", mf.pool("Rhun").regions == ["Rhun_Province"])
check("no final newline is kept", not mf.trailing_newline)
check("mapquery's reader is this one",
      [(p.name, p.regions, p.units) for p in mapquery.parse_mercenaries(MERCS)]
      == [(p.name, p.regions, p.unit_names) for p in mf.pools])
check("…and so is G3's", campfiles.parse_mercs is mp.parse_text
      and campfiles.MercFile is mp.MercFile)

t = mp.edit_unit(mf, "Mordor", 1, {"cost": 600, "events": None})
check("an edit rewrites one line",
      sum(a != b for a, b in zip(MERCS.split("\r\n"), t.split("\r\n"))) == 1
      and len(t) == len(MERCS) - len(" events { ND_BOH }"))

t = mp.add_unit(mf, "Mordor", {"name": "Uruks", "exp": 1, "cost": 700,
                               "replenish": [0.05, 0.1], "max": 2, "initial": 1,
                               "religions": ["catholic"]})
added = mp.parse_text(t).pool("Mordor").units
check("a new unit goes after the pool's last line, above the commented one",
      [x.name for x in added] == ["Raider Warband", "Orc Maulers", "Uruks"]
      and t.split("\r\n")[7] == "\tunit Uruks,\t\t\texp 1 cost 700 replenish 0.05 - 0.1 "
                                "max 2 initial 1 religions { catholic }"
      and t.split("\r\n")[8].startswith(";\tunit merc cog"))
try:
    mp.add_unit(mf, "Mordor", {"name": "Half", "exp": 0})
    refused = False
except mp.MercError:
    refused = True
check("a new unit without its fixed fields is refused", refused)

t = mp.delete_unit(mf, "Rhun", 0)
check("deleting a unit drops its line and nothing else",
      mp.parse_text(t).pool("Rhun").units == [] and t.count("\r\n") == MERCS.count("\r\n") - 1)

t = mp.add_pool(mf, "Harad", ["Harad_Province"])
check("a new pool goes on the end, laid out like the others, the missing final "
      "newline still missing",
      t.endswith("\r\n\r\npool Harad\r\n\tregions Harad_Province")
      and mp.parse_text(t).pool("Harad").regions == ["Harad_Province"])
for bad in [("Mordor", []), ("Two words", []), ("New", ["Udun_Province"])]:
    try:
        mp.add_pool(mf, *bad)
        refused = False
    except mp.MercError:
        refused = True
    check(f"pool {bad[0]!r} with {bad[1]} is refused", refused)

t = mp.delete_pool(mf, "Rhun")
check("deleting a pool takes its block and one blank line",
      [p.name for p in mp.parse_text(t).pools] == ["Mordor", "Empty"]
      and "\r\n\r\n\r\n" not in t and "Rhun" not in t)
t = mp.delete_pool(mf, "Empty")
check("…the last pool too, with the blank line in front of it",
      t.endswith("pool Rhun\r\n\tregions Rhun_Province ; the east\r\n\tunit Easterlings"
                 "\texp 1 cost 300 replenish 0.1 - 0.2 max 2 initial 1 start_year 3000 "
                 "events { a b } factions { timurids }"))

t = mp.move_region(mf, "Udun_Province", "Empty")
check("a province moves, and a pool with no regions line is given one",
      mp.parse_text(t).pool_of("Udun_Province") == "Empty")


print("\n3  plan")
tmp = Path(_tmp.mkdtemp(prefix="ut_mercpools_"))
fake = tmp / "Fake"
camp = fake / "data" / campstrat.CAMPAIGN_DIR_REL / campstrat.DEFAULT_CAMPAIGN
camp.mkdir(parents=True)
(camp / mp.MERCS_NAME).write_bytes(MERCS.encode("latin-1"))


class FakeMod:
    root = fake
    data = fake / "data"
    name = "Fake"


fm = FakeMod()
p = mp.plan(fm, {"action": "unit_edit", "pool": "Mordor", "unit": 0,
                 "edits": {"cost": 300, "crusading": False}})
check("an edit plans, and names both changes",
      p.payload()["ok"] and len(p.changes) == 2 and "cost 270 -> 300" in p.changes[0])
check("an edit to nothing is nothing to change",
      mp.plan(fm, {"action": "unit_edit", "pool": "Mordor", "unit": 0,
                   "edits": {"cost": 270}}).errors == ["nothing to change"])
check("a bad value is refused with its reason",
      "whole number" in "; ".join(mp.plan(fm, {"action": "unit_edit", "pool": "Mordor",
                                               "unit": 0, "edits": {"max": "lots"}}).errors))
check("a unit past the end of the pool is refused",
      mp.plan(fm, {"action": "unit_edit", "pool": "Rhun", "unit": 5,
                   "edits": {"cost": 1}}).errors)
check("an unknown action is refused", mp.plan(fm, {"action": "sell"}).errors)
w = mp.plan(fm, {"action": "unit_edit", "pool": "Mordor", "unit": 0,
                 "edits": {"initial": 9, "replenish": [0.5, 0.1]}})
check("initial over max and a falling replenish plan with warnings",
      w.payload()["ok"] and len(w.warnings) == 2)
check("crusading with no religions warns",
      mp.plan(fm, {"action": "unit_edit", "pool": "Mordor", "unit": 0,
                   "edits": {"religions": None}}).warnings)
d = mp.plan(fm, {"action": "unit_delete", "pool": "Mordor", "unit": 0})
check("deleting the first unit moves the second up and is not called a stray change",
      d.payload()["ok"])
check("adding a unit plans",
      mp.plan(fm, {"action": "unit_add", "pool": "Empty",
                   "values": {"name": "Ghosts", "exp": 2, "cost": 5,
                              "replenish": [0, 0.1], "max": 1, "initial": 0}}).payload()["ok"])
check("adding a pool plans", mp.plan(fm, {"action": "pool_add", "name": "Khand"}).payload()["ok"])
pd = mp.plan(fm, {"action": "pool_delete", "pool": "Rhun"})
check("deleting a pool plans and warns about the province left with none",
      pd.payload()["ok"] and pd.warnings)
check("a province move plans",
      mp.plan(fm, {"action": "region_move", "region": "Rhun_Province",
                   "pool": "Mordor"}).payload()["ok"])
try:
    mp.plan(fm, {"action": "pool_add", "name": "X", "campaign": "../../x"})
    _raises = False
except ValueError:
    _raises = True
check("a campaign that leaves the folder is refused, as a ValueError the server "
      "turns into an error", _raises)


print("\n4  every campaign on this machine")
swept = 0
for root in _realmod.installed():
    mod = Mod(root)
    for c in campfiles.campaigns(mod):
        path = mp.path_for(mod, c)
        if not path.is_file():
            continue
        swept += 1
        text = kb.read_text(path, mp.ENCODING)
        rf = mp.parse_text(text)
        units = [x for q in rf.pools for x in q.units]
        head = f"{root.name}/{c}"
        check(f"{head}: round trip, {len(rf.pools)} pools, {len(units)} unit lines",
              rf.text() == text)
        check(f"{head}: every unit line whole", not [x for x in units if x.fault])
        check(f"{head}: every field set to itself changes no line, `0.10` included",
              all(mp.set_field(rf.lines[x.line], k, getattr(x, k)
                               if k != "replenish" else list(x.replenish)) == rf.lines[x.line]
                  for x in units for k in mp.FIELDS
                  if k in x.spans and k not in mp.FLAGS))
        check(f"{head}: mapquery reads the same pools as before, name for name",
              [q.units for q in mapquery.parse_mercenaries(text)]
              == [q.unit_names for q in rf.pools])
check(f"{swept} campaign file(s) swept", swept > 0)


print("\n5  plan and apply on a copy of a real campaign")
src = _realmod.pick("Third_Age_Reforged")
real = Mod(src)
pick = next((c for c in campfiles.campaigns(real) if mp.path_for(real, c).is_file()), None)
if pick is None:
    print("  SKIPPED - no campaign with a mercenary file")
else:
    rel = mp.path_for(real, pick).relative_to(real.data)
    dest = tmp / src.name
    (dest / "data" / rel).parent.mkdir(parents=True)
    shutil.copy2(real.data / rel, dest / "data" / rel)
    mod = Mod(dest)
    before = (dest / "data" / rel).read_bytes()
    rf, _ = mp.read(mod, pick)
    q = next(x for x in rf.pools if x.units)
    pl = mp.plan(mod, {"campaign": pick, "action": "unit_edit", "pool": q.name, "unit": 0,
                       "edits": {"cost": q.units[0].cost + 1}})
    check(f"{pick}: a cost edit plans", pl.payload()["ok"])
    res = mp.apply(pl)
    now = (dest / "data" / rel).read_bytes()
    check("…writes one line and keeps the CRLFs",
          sum(a != b for a, b in zip(before.split(b"\r\n"), now.split(b"\r\n"))) == 1
          and now.count(b"\r\n") == before.count(b"\r\n"))
    check("…backs the old file up byte for byte",
          (Path(res["record"]["backup_root"]) / "data" / rel).read_bytes() == before)
    check("…and logs under its own mode", res["record"]["mode"] == "mercpools")

print("\n6  32b: the gates, resolved")
G = mp.parse_unit
years = {"start": 2980, "end": 3080, "timescale": 0.25}
evs = {"nd_boh": {"name": "ND_BOH", "how": "script", "where": "campaign_script.txt line 9"}}
cath = {"name": "france", "religion": "catholic"}
isl = {"name": "sicily", "religion": "islam"}
types = {"Raider Warband", "Clan Axemen"}


def verdict(line, fac=None, t=types, y=years):
    return mp.gates(G(line), fac, y, evs, t)


v, gs = verdict(LINE, cath)
check("a crusading line a catholic faction may hire waits on a crusade",
      v == "later" and [g["gate"] for g in gs] == ["unit", "religions", "crusading"]
      and gs[1]["state"] == "ok")
check("…and is never hired by a faction of another religion",
      verdict(LINE, isl)[0] == "no")
v, gs = verdict(LINE)
check("with no faction the religion gate says what it needs and decides nothing",
      [g["state"] for g in gs if g["gate"] == "religions"] == ["info"] and v == "later")
check("a unit the EDU does not have is never hired",
      verdict(LINE.replace("Raider Warband", "Ghost"), cath)[0] == "no")
check("…and with no EDU to read, the name is not judged",
      verdict(LINE.replace("Raider Warband", "Ghost"), cath, t=None)[0] == "later")
ax = "unit Clan Axemen, exp 0 cost 500 replenish 0.08 - 0.125 max 3 initial 1 religions { islam } events { ND_BOH }"
v, gs = verdict(ax, isl)
check("an event a script sets is a wait, and says where it is set",
      v == "later" and "campaign_script.txt line 9" in gs[-1]["say"])
check("an event nothing sets is unknown, not never",
      verdict(ax.replace("ND_BOH", "turn_25"), isl)[0] == "unknown")
fel = "unit Clan Axemen, exp 0 cost 1 replenish 0 - 0 max 1 initial 1 factions { sicily }"
check("`factions { }` names the faction outright",
      verdict(fel, isl)[0] == "yes" and verdict(fel, cath)[0] == "no"
      and verdict(fel.replace("sicily", "all"), cath)[0] == "yes")
yr = "unit Clan Axemen, exp 0 cost 1 replenish 0 - 0 max 1 initial 1 start_year {}"
check("a start year after the campaign ends is never - Reforged's 2986 in a "
      "campaign ending 2984", verdict(yr.format(3090))[0] == "no")
check("a start year inside it is a wait, and one before it is no gate",
      verdict(yr.format(3000))[0] == "later" and verdict(yr.format(2900))[0] == "yes")
check("an end year before the campaign starts is never",
      verdict(yr.replace("start_year", "end_year").format(2900))[0] == "no")
check("an empty religions list is every religion",
      verdict(fel.replace("factions { sicily }", "religions { }"), cath)[0] == "yes")

print("\n7  32b: the join on this machine, and the map colourings")
for root in _realmod.installed():
    mod = Mod(root)
    for c in campfiles.campaigns(mod):
        if not mp.path_for(mod, c).is_file():
            continue
        v = mp.hire_view(mod, c)
        head = f"{root.name}/{c}"
        n = sum(len(p["units"]) for p in v["pools"])
        check(f"{head}: every line has a verdict, and the reverse index covers "
              "every line", n == v["counts"]["lines"]
              and sum(len(u["offers"]) for u in v["units"]) == n
              and all(u["hire"] in ("yes", "later", "no", "unknown")
                      for p in v["pools"] for u in p["units"]))
        f = next((x for x in v["factions"] if x["religion"]), None)
        if f:
            vf = mp.hire_view(mod, c, f["name"])
            check(f"{head}: picking {f['name']} decides the faction gates",
                  vf["faction"]["name"] == f["name"]
                  and not any(g["state"] == "info" for p in vf["pools"]
                              for u in p["units"] for g in u["gates"]))
        check(f"{head}: every faction has a religion, `spawned_on_event` or not",
              all(x["religion"] for x in v["factions"]))
        if root.name.startswith("Divide_and_Conquer") and c == "imperial_campaign":
            ev = mp.event_sources(mod, c).get("nd_boh")
            check("DaC: ND_BOH is traced to the campaign script that sets it",
                  ev and ev["how"] == "script" and ev["where"].startswith("campaign_script.txt"))
        if root.name == "Third_Age_Reforged" and c == "imperial_campaign":
            never = [u["name"] for p in v["pools"] for u in p["units"]
                     if any(g["gate"] == "start_year" and g["state"] == "no" for g in u["gates"])]
            check(f"Reforged: {len(never)} lines start after the campaign ends", len(never) == 2)
        if c.endswith("Fellowship_Campaign"):
            check("Fellowship: 28 of its 29 unit names are not in the EDU",
                  len(v["unknown_units"]) == 28 and v["counts"]["units"] == 29)
            check("…and Mt-Gram_Province is in two pools", "mt-gram_province" in v["in_two"])

from types import SimpleNamespace as NS          # noqa: E402
facts = NS(pools=[mapquery.MercPool(name="A", regions=["P1"], units=["X", "Y", "X"]),
                  mapquery.MercPool(name="B", regions=["P2"], units=[])],
           regions=[NS(name="P1", merc_pools=["A"], pixels=4, region_id=0),
                    NS(name="P2", merc_pools=["B"], pixels=2, region_id=1),
                    NS(name="P3", merc_pools=[], pixels=1, region_id=2)])
cnt = mapquery.info_merc_count(facts)
check("merc_count bands a province by the lines its pools sell",
      cnt.of_region == {"p1": 2, "p2": 0, "p3": 0})
anyc = mapquery.info_merc_any(facts)
check("merc_any is yes only where something is sold",
      anyc.groups[0].regions == ["P1"] and sorted(anyc.groups[1].regions) == ["P2", "P3"])
one = mapquery.colouring(facts, "merc:Y")
check("merc:<unit> lights the provinces selling that unit",
      one.groups[0].regions == ["P1"] and not one.off)
check("…and says so when nothing sells it",
      bool(mapquery.colouring(facts, "merc:Nobody").off))

print("\n8  32c: the six rules, and the one repair")
from unittransfer import campmap, mapcheck         # noqa: E402

MERC_RULES = ("merc.unit_unknown", "merc.region_twice", "merc.region_unknown",
              "merc.religion_unknown", "merc.event_unknown", "merc.year_outside")
check("all six are registered, every one a warning",
      all(mapcheck.RULE_BY_CODE[c].severity == "warn" for c in MERC_RULES))
expect = {
    ("Divide_and_Conquer_EUR", "imperial_campaign"):
        {"merc.event_unknown": 4},
    ("Third_Age_Reforged", "custom/Fellowship_Campaign"):
        {"merc.unit_unknown": 49, "merc.region_twice": 1},
    ("Third_Age_Reforged", "imperial_campaign"):
        {"merc.year_outside": 2},
}
for (name, c), want in expect.items():
    root = _realmod.MODS / name
    if not (root / "data").is_dir():
        continue
    mod = Mod(root)
    try:
        cm = campmap.campaign_map(mod, c)
    except Exception as exc:                          # noqa: BLE001
        check(f"{name}/{c}: the map reads ({exc})", False)
        continue
    ck = mapcheck.Check(mod, cm, c)
    got = {code: len(list(mapcheck.RULE_BY_CODE[code].fn(ck) or ())) for code in MERC_RULES}
    check(f"{name}/{c}: {', '.join(f'{k} {v}' for k, v in want.items())}, nothing else",
          got == {code: want.get(code, 0) for code in MERC_RULES})
    if c.endswith("Fellowship_Campaign"):
        two = list(mapcheck.RULE_BY_CODE["merc.region_twice"].fn(ck))[0]
        check("…a finding's identity carries no line number",
              "|" not in two.what and str(two.line) not in two.what)
        # the repair: keep it in one pool, through region_move, on a copy
        rel = mp.path_for(mod, c).relative_to(mod.data)
        dest = tmp / "fellowship_repair"
        (dest / "data" / rel).parent.mkdir(parents=True)
        shutil.copy2(mod.data / rel, dest / "data" / rel)
        pl = mp.plan(Mod(dest), {"campaign": c, "action": "region_move",
                                 "region": "Mt-Gram_Province", "pool": "Gram"})
        check("keeping Mt-Gram_Province in Gram alone plans", pl.payload()["ok"])
        after = mp.parse_text(pl.text)
        check("…and leaves it in exactly one pool, the one picked",
              [q.name for q in after.pools
               if any(r.lower() == "mt-gram_province" for r in q.regions)] == ["Gram"])

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
