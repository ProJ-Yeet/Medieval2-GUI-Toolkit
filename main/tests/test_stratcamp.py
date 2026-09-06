"""``descr_strat.txt``, write: the campaign's own settings - 16j's first half.

16h proved a settlement block could be rewritten without disturbing a byte it
did not mean to, and 16i proved it again on 479 character blocks. This is the
same gate on what is left at depth zero, and its own version of the strong
check is the diplomacy matrix: **all 99 faction rows across vanilla's two
campaigns and Third Age Reforged are re-rendered with no edits and must come
back byte for byte** - the three tabs after ``hre,``, the five spaces before
Third Age Reforged's ``1.00``, its habit of restating that value in front of
every target, and the tab left hanging off the end of the line, all included.

Two things this suite exists to hold down, and both were found by writing it:

**A standings line is a list of pairs and the value is sticky.** Vanilla never
repeats the value, so the old reading - first number, then a list of factions -
was right on all 46 of its lines by accident. Third Age Reforged repeats it on
nearly all of its 204, and under the old reading Sicily held an opinion of a
faction called ``1.00``. Part 1 checks the grammar directly.

**A row's lines are its shape, not just their whitespace.** Grouping the cells
by value and writing one line per value looked right and rewrote 13 rows nobody
had touched: vanilla puts Egypt's two -0.6 opinions on separate lines and Third
Age Reforged gives the Aztecs twelve lines all reading -1.00. Part 2 is the
byte-for-byte gate that catches it.

The exit criteria, in the order they are checked:

    the header, a roster, a diplomacy row and a faction's scalars each save
    the file outside the declared runs is byte-identical, and the guard says so
    a faction block moved after the diplomacy section is refused
    the save backs up, and the log's undo puts the file back byte-exact

Five parts, the last two of which need a real game install:

    1  the file, read: the sticky value, the contiguous row, the dead flag
    2  every real campaign: 99 diplomacy rows re-rendered byte for byte
    3  the rules: what is fatal, what is a warning, and what is not checked
    4  the five saves, and the guard that refuses what they did not declare
    5  the two routes, a real save and its undo, on a throwaway mod

    python -m tests.test_stratcamp
"""
import json
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import (campmap, campstrat, config, mapquery, stratcamp,
                          winconds)
from unittransfer.keyblock import read_text
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


# a whole small campaign, with every shape this phase writes into
TOY = joined(
    "campaign\t\ttest_campaign",
    "playable",
    "\tengland",
    "end",
    "unlockable",
    "\tfrance",
    "end",
    "nonplayable",
    "\tslave",
    "end",
    "",
    "start_date\t1080 summer",
    "end_date\t1530 winter",
    "timescale\t2.00",
    "night_battles_enabled",
    "brigand_spawn_value 20",
    "",
    "faction\tengland, balanced smith",
    "ai_label\t\tcatholic",
    "denari\t10000",
    "denari_kings_purse\t2500",
    "settlement",
    "{",
    "\tlevel town",
    "\tregion London_Province",
    "}",
    "",
    "faction\tfrance, balanced caesar",
    "ai_label\t\tcatholic",
    "denari\t8000",
    "",
    "faction\tslave, default",
    "ai_label\t\tdefault",
    "",
    "faction_standings\tengland,\t\t-0.2\tfrance",
    "faction_standings\tengland,\t\t-1.0\tslave",
    "faction_relationships \tengland, at_war_with \tslave",
    "",
    "region London_Province",
    "farming_level 3",
)


class _Fake:
    """Just enough of a Mod for the vocabulary; no faction file on disk."""

    def __init__(self, root):
        self.root, self.name = Path(root), Path(root).name
        self.data = Path(root) / "data"


class _Facts:
    """The fact table's two questions, answered without a map."""

    def __init__(self, mod, cultures=None, campaign="test_campaign"):
        self.mod, self.campaign = mod, campaign
        self.faction_cultures = cultures or {}
        self.strat_rel = "world/maps/campaign/test_campaign/descr_strat.txt"
        self.strat = None

    def faction_label(self, name):
        return name.title()


sf = campstrat.parse_strat(TOY)
mod = _Fake(_tmp.mkdtemp(prefix="ut_sc_"))
facts = _Facts(mod)
facts.strat = sf
voc = stratcamp.Vocabulary(facts, sf)

# ---- 1) the file, read ---------------------------------------------------------
print("1) the file as it is read")

check("the toy campaign parses with three factions and no problems",
      len(sf.of_kind("faction")) == 3 and not sf.problems)

sticky = campstrat.parse_strat(joined(
    "faction_standings\tsicily,\t\t1.00\tdenmark, 1.00\tmilan",
    "faction_standings\tdenmark,\t1.00\tsicily, milan"))
rows = sticky.of_kind("faction_standings")
check("a repeated value on a standings line is a value, not a faction",
      rows[0].get("toward") == ["denmark", "milan"]
      and rows[0].get("pairs") == [("denmark", 1.0), ("milan", 1.0)])
check("a target with no value in front of it takes the last one stated",
      rows[1].get("pairs") == [("sicily", 1.0), ("milan", 1.0)])

check("a faction's whole opinion is read off however many lines it is on",
      stratcamp.standings_of(sf, "england")
      == {"france": -0.2, "slave": -1.0})
check("and its relationships the same way",
      stratcamp.relations_of(sf, "england") == {"slave": "at_war_with"})
check("a faction's diplomacy lines are one contiguous run",
      stratcamp.row_span(stratcamp.rows_of(sf, "faction_standings", "england"))
      == (34, 35))

check("the header ends where the first block begins",
      stratcamp.header_end(sf) == 17)
check("the diplomacy section is found even when there are no standings",
      stratcamp.diplomacy_start(campstrat.parse_strat(joined(
          "faction\tengland, balanced smith",
          "faction_relationships \tengland, at_war_with \tslave"))) == 1)

dead = campstrat.parse_strat(joined("campaign\t\tx",
                                    "marian_reforms_activated"))
check("marian_reforms_activated survives the parse instead of vanishing",
      dead.globals.get("marian_reforms_activated") is True)

check("a faction's own scalars are read without its settlements",
      stratcamp.faction_scalars(sf, sf.faction("england"))
      == {"name": "england", "ai": "balanced smith", "ai_label": "catholic",
          "denari": 10000, "denari_kings_purse": 2500,
          "dead_until_resurrected": False, "re_emergent": False,
          "undiscovered": False})

# ---- 2) every real campaign: the rows re-render byte for byte -------------------
print("\n2) every installed campaign: every diplomacy row, re-rendered")

roots = [p for p in [_realmod.MODS.parent] + _realmod.installed() if p.is_dir()]
total = {"rows": 0, "off": 0}
for root in roots:
    real = Mod(root)
    names = campstrat.campaigns(real)
    if not names:
        continue
    for name in names:
        f = campstrat.read_strat(real, name)
        t0 = time.time()
        exact = off = 0
        for kind, read, render in (
                ("faction_standings", stratcamp.standings_of,
                 stratcamp.standings_rows),
                ("faction_relationships", stratcamp.relations_of,
                 stratcamp.relation_rows)):
            for who in sorted({n.name for n in f.of_kind(kind)}):
                a, b = stratcamp.row_span(stratcamp.rows_of(f, kind, who))
                if render(f, who, read(f, who)) == f.lines[a:b + 1]:
                    exact += 1
                else:
                    off += 1
        total["rows"] += exact + off
        total["off"] += off
        if exact + off:
            check(f"{root.name}/{name}: all {exact + off} diplomacy rows "
                  f"re-render byte for byte "
                  f"({(time.time() - t0) * 1000:.0f} ms)", off == 0)
        check(f"{root.name}/{name}: the header's own words are all read",
              not [w for _i, w in stratcamp.header_words(f)
                   if w not in stratcamp.VALUES + stratcamp.FLAGS
                   + stratcamp.ROSTERS + ("campaign", "end")
                   and not f.faction(w)])
if total["rows"]:
    check(f"{total['rows']} diplomacy rows over every installed campaign, "
          f"{total['off']} of them not byte-exact", total["off"] == 0)

# ---- 3) the rules --------------------------------------------------------------
print("\n3) what is fatal, what warns, and what is not checked")


def codes(found):
    return {x["code"] for x in found}


def fatal(found):
    return {x["code"] for x in found if x["fatal"]}


check("a season the engine does not have is fatal",
      "camp.season" in fatal(stratcamp.check_globals(
          {"start_date": "1080 spring"}, [])))
check("a year that is not a number is fatal",
      "camp.date" in fatal(stratcamp.check_globals(
          {"start_date": "eleventy summer"}, [])))
check("a campaign that ends before it starts only warns",
      stratcamp.check_globals({"start_date": "1200 summer",
                               "end_date": "1100 winter"}, [])[0]["fatal"]
      is False)
check("a spawn value that is not a whole number is fatal",
      "camp.number" in fatal(stratcamp.check_globals(
          {"brigand_spawn_value": "lots"}, [])))
check("a timescale of zero warns rather than refuses",
      "camp.timescale_zero" in codes(stratcamp.check_globals(
          {"timescale": "0"}, []))
      and not fatal(stratcamp.check_globals({"timescale": "0"}, [])))
check("marian_reforms_activated is reported as the dead line it is, and warns",
      "camp.dead_flag" in codes(stratcamp.check_globals(
          {}, ["marian_reforms_activated"]))
      and not fatal(stratcamp.check_globals(
          {}, ["marian_reforms_activated"])))
check("a header flag the engine has never had is fatal",
      "camp.flag" in fatal(stratcamp.check_globals({}, ["turn_off_winter"])))
check("a clean header reports nothing at all",
      stratcamp.check_globals({"start_date": "1080 summer",
                               "end_date": "1530 winter", "timescale": "2.00",
                               "brigand_spawn_value": "20"},
                              ["night_battles_enabled"]) == [])

full = {"playable": ["england"], "unlockable": ["france"],
        "nonplayable": ["slave"]}
check("the three lists as the toy campaign writes them report nothing",
      stratcamp.check_rosters(voc, full) == [])
check("a roster naming a faction with no block is fatal",
      "camp.roster_unknown" in fatal(stratcamp.check_rosters(
          voc, {**full, "playable": ["england", "burgundy"]})))
check("a faction with a block and no place in any list is fatal",
      "camp.block_unlisted" in fatal(stratcamp.check_rosters(
          voc, {**full, "nonplayable": []})))
check("a faction in two lists at once warns, because the engine takes the first",
      "camp.roster_twice" in codes(stratcamp.check_rosters(
          voc, {**full, "unlockable": ["france", "england"]})))
check("no playable faction at all warns",
      "camp.no_playable" in codes(stratcamp.check_rosters(
          voc, {**full, "playable": []})))

all_three = stratcamp.Vocabulary(
    _Facts(mod, {"england": "northern_european", "france": "northern_european",
                 "slave": "southern_european"}), sf)
one_only = stratcamp.Vocabulary(_Facts(mod, {"england": "northern_european"}),
                                sf)
check("with descr_sm_factions.txt on disk, a slot it does not declare is fatal",
      stratcamp.check_rosters(all_three, full) == []
      and "camp.roster_slot" in fatal(stratcamp.check_rosters(one_only, full)))
check("and without it, that check does not run at all - the stock game's case",
      not voc.slots_known
      and "camp.roster_slot" not in codes(stratcamp.check_rosters(voc, full)))

check("an opinion of a faction with no block is fatal",
      "camp.standing_toward" in fatal(stratcamp.check_standings(
          voc, "england", {"burgundy": 0.5})))
check("an opinion outside -1 to 1 warns",
      "camp.standing_range" in codes(stratcamp.check_standings(
          voc, "england", {"france": 3.0}))
      and not fatal(stratcamp.check_standings(voc, "england",
                                              {"france": 3.0})))
check("an opinion that is not a number is fatal",
      "camp.standing_value" in fatal(stratcamp.check_standings(
          voc, "england", {"france": "friendly"})))
check("a faction with an opinion of itself warns",
      "camp.standing_self" in codes(stratcamp.check_standings(
          voc, "england", {"england": 1.0})))
check("a relationship word that is not one of the two is fatal",
      "camp.relation_word" in fatal(stratcamp.check_relations(
          voc, "england", {"france": "suzerain_of"})))
check("both words the engine does read pass",
      stratcamp.check_relations(voc, "england",
                                {"france": "allied_to",
                                 "slave": "at_war_with"}) == [])

check("money that is not a whole number is fatal",
      "camp.faction_number" in fatal(stratcamp.check_faction(
          {"name": "england", "ai": "balanced smith", "denari": "lots"})))
check("negative money warns rather than refuses",
      "camp.faction_negative" in codes(stratcamp.check_faction(
          {"name": "england", "ai": "balanced smith", "denari": -50})))
check("a faction with no AI personality warns",
      "camp.faction_ai" in codes(stratcamp.check_faction(
          {"name": "england", "ai": ""})))

late = campstrat.parse_strat(joined(
    "faction\tengland, balanced smith",
    "faction_standings\tengland,\t-1.0\tslave",
    "faction\tslave, default"))
check("a faction block after the diplomacy section is fatal, by line number",
      "camp.faction_after_diplomacy" in fatal(stratcamp.check_order(late))
      and "line 3" in stratcamp.check_order(late)[0]["message"])
check("and a file in the right order says nothing",
      stratcamp.check_order(sf) == [])

# ---- 4) the five saves ---------------------------------------------------------
print("\n4) the five saves, and the guard")

toy_root = Path(_tmp.mkdtemp(prefix="ut_sc_mod_"))
camp_dir = toy_root / "data" / campstrat.CAMPAIGN_DIR_REL / "test_campaign"
camp_dir.mkdir(parents=True)
(camp_dir / "descr_strat.txt").write_text(TOY, encoding=campstrat.ENCODING,
                                          newline="")
toy = _Fake(toy_root)
toy_facts = _Facts(toy)
toy_facts.strat = sf


def plan(**body):
    return stratcamp.plan_campaign(toy, toy_facts,
                                   {"campaign": "test_campaign", **body})


p = plan(what="globals", values={"brigand_spawn_value": "35"},
         flags=["night_battles_enabled"])
back = campstrat.parse_strat(p.text) if p.text else None
check("the header's own line is rewritten and nothing else moves",
      not p.errors and back is not None
      and back.globals["brigand_spawn_value"] == "35"
      and back.counts() == sf.counts()
      and sum(a != b for a, b in zip(sf.lines, back.lines)) == 1)
check("and the change is said the way somebody would say it",
      p.changes == ["brigand_spawn_value: 20 -> 35"])

p = plan(what="globals", values={}, flags=["night_battles_enabled",
                                           "show_date_as_turns"])
back = campstrat.parse_strat(p.text)
check("a flag turned on is one line inserted, in the shape of the flags there",
      not p.errors and back.globals.get("show_date_as_turns") is True
      and len(back.lines) == len(sf.lines) + 1)
p = plan(what="globals", values={}, flags=[])
back = campstrat.parse_strat(p.text)
check("and turned off is its own line gone, because a flag is a line or nothing",
      not p.errors and "night_battles_enabled" not in back.globals
      and len(back.lines) == len(sf.lines) - 1)

p = plan(what="rosters", rosters={"playable": ["england", "france"],
                                  "unlockable": [], "nonplayable": ["slave"]})
back = campstrat.parse_strat(p.text)
check("a faction moved between two lists lands in the right one",
      not p.errors
      and back.rosters["playable"] == ["england", "france"]
      and back.rosters["unlockable"] == []
      and back.rosters["nonplayable"] == ["slave"])
check("and the roster lists keep the tab their own entries are indented with",
      all(l.startswith("\t") for l in back.lines
          if l.strip() in ("england", "france", "slave")))

p = plan(what="standings", faction="england",
         standings={"france": 0.4, "slave": -1.0})
back = campstrat.parse_strat(p.text)
check("one cell of the diplomacy matrix is changed and the row keeps its shape",
      not p.errors
      and stratcamp.standings_of(back, "england")
      == {"france": 0.4, "slave": -1.0}
      and len(back.lines) == len(sf.lines)
      and sum(a != b for a, b in zip(sf.lines, back.lines)) == 1)
p = plan(what="standings", faction="england", standings={"slave": -1.0})
back = campstrat.parse_strat(p.text)
check("a cell removed takes its line with it when nothing else is on it",
      not p.errors
      and stratcamp.standings_of(back, "england") == {"slave": -1.0}
      and len(back.lines) == len(sf.lines) - 1)
p = plan(what="standings", faction="france", standings={"england": 0.6})
back = campstrat.parse_strat(p.text)
check("a faction with no row at all gets one, after the last standings line",
      not p.errors
      and stratcamp.standings_of(back, "france") == {"england": 0.6}
      and back.of_kind("faction_standings")[-1].name == "france")

p = plan(what="relationships", faction="england",
         relationships={"slave": "at_war_with", "france": "allied_to"})
back = campstrat.parse_strat(p.text)
check("an alliance added is a second line under the war it already had",
      not p.errors
      and stratcamp.relations_of(back, "england")
      == {"slave": "at_war_with", "france": "allied_to"})

p = plan(what="faction", faction="england", scalars={"denari": 4444},
         flags=[])
back = campstrat.parse_strat(p.text)
check("a faction's money is one line rewritten, and its other fields stand",
      not p.errors and back.faction("england").get("denari") == 4444
      and back.faction("england").get("ai") == "balanced smith"
      and back.faction("england").get("denari_kings_purse") == 2500
      and sum(a != b for a, b in zip(sf.lines, back.lines)) == 1)
p = plan(what="faction", faction="england", scalars={}, flags=[])
check("a save that sends no field and changes no flag has nothing to change",
      p.errors == ["nothing to change"])
p = plan(what="faction", faction="england", scalars={},
         flags=["undiscovered"])
back = campstrat.parse_strat(p.text)
check("a faction flag turned on lands under ai_label, where all five real ones sit",
      not p.errors and back.faction("england").get("undiscovered") is True
      and back.lines[back.faction("england").field_lines["ai_label"] + 1]
      == "undiscovered")

check("a save naming a faction with no block is refused, and says where to go",
      "second half of 16j" in "; ".join(
          plan(what="standings", faction="burgundy",
               standings={}).errors))
check("a save naming something that is not one of the five is refused by name",
      "no such save" in "; ".join(plan(what="win_conditions").errors))

# the guard: a splice that reaches outside what it declared
sf2 = campstrat.parse_strat(TOY)
bad = list(sf2.lines)
bad[19] = "ai_label\t\torthodox"          # a line no save declared
errs = stratcamp._guard(sf2, campstrat.parse_strat(joined(*bad)),
                        "globals", [(15, 15, 1)])
check("the guard names, by line, a difference the save never declared",
      any("line 20" in e for e in errs))
check("and a save that stays inside its own runs passes it",
      not stratcamp._guard(sf2, sf2, "globals", [(15, 15, 1)]))
check("a run that miscounts what it puts back is caught below itself, "
      "because everything under it has moved",
      any("below everything this save asked about" in e
          for e in stratcamp._guard(
              sf2, campstrat.parse_strat(joined(*bad)), "globals",
              [(15, 15, 1), (19, 19, 0)])))

moved = list(sf2.lines)
block = moved[31:33]
del moved[31:33]
moved[-2:-2] = block                      # slave's block, after the diplomacy
errs = stratcamp._guard(sf2, campstrat.parse_strat(joined(*moved)), "rosters",
                        [(0, len(sf2.lines) - 1, len(moved))])
check("a faction block that ends up after the diplomacy section is refused",
      any("after the diplomacy section" in e for e in errs))

print("\n4b) a whole faction, made and unmade (16j-2)")

p = plan(what="create", faction="burgundy", donor="france",
         roster="unlockable", diplomacy=True, scalars={"denari": 7000})
back = campstrat.parse_strat(p.text) if p.text else None
made = back.faction("burgundy") if back else None
check("a new faction is a block, a place in a list and the donor's diplomacy",
      not p.errors and made is not None
      and back.rosters["unlockable"] == ["france", "burgundy"]
      and back.counts()["faction"] == sf.counts()["faction"] + 1)
check("and its block sits before the diplomacy section, which is the file's "
      "own order",
      made.start < stratcamp.diplomacy_start(back)
      and not stratcamp.check_order(back))
check("it is written in the shape of the donor's own lines, not this phase's",
      back.lines[made.start] == "faction\tburgundy, balanced caesar"
      and back.lines[made.field_lines["ai_label"]] == "ai_label\t\tcatholic")
check("nothing of the donor's campaign is copied - no settlement, nobody",
      not back.children_of(made, "settlement")
      and not back.descendants_of(made, "character"))
check("and that is said out loud rather than left to be found at turn one",
      {"camp.new_homeless", "camp.new_leaderless"}
      <= {f["code"] for f in p.findings}
      and not [f for f in p.findings if f["fatal"]])

p2 = plan(what="create", faction="burgundy", donor="france", roster="playable",
          diplomacy=False)
back2 = campstrat.parse_strat(p2.text)
check("with the diplomacy left out it starts neutral toward everybody, and "
      "the plan says so",
      "camp.new_neutral" in {f["code"] for f in p2.findings}
      and not stratcamp.standings_of(back2, "burgundy")
      and not stratcamp.relations_of(back2, "burgundy"))

check("a name that is already a faction is refused",
      "camp.new_taken" in {f["code"] for f in
                           stratcamp.check_new_name(voc, "england")})
check("a name that is not a faction slot is refused by what a slot looks like",
      "camp.new_shape" in {f["code"] for f in
                           stratcamp.check_new_name(voc, "New Burgundy")})
check("a donor with no block of its own is refused, and says why there is one",
      "written in the shape of one that already works"
      in "; ".join(plan(what="create", faction="burgundy",
                        donor="atlantis").errors))

# and unmade again, on the file the create would have written
made_root = Path(_tmp.mkdtemp(prefix="ut_sc_made_"))
made_dir = made_root / "data" / campstrat.CAMPAIGN_DIR_REL / "test_campaign"
made_dir.mkdir(parents=True)
(made_dir / "descr_strat.txt").write_text(p.text, encoding=campstrat.ENCODING,
                                          newline="")
made_mod = _Fake(made_root)
gone = stratcamp.plan_campaign(made_mod, toy_facts,
                               {"campaign": "test_campaign", "what": "delete",
                                "faction": "burgundy"})
check("deleting it again puts the file back byte for byte - the block, its "
      "separator, its place in the list and every line that named it",
      not gone.errors and gone.text == TOY)

check("a faction that still holds anything is not deleted, and is told what",
      "still holds" in "; ".join(plan(what="delete", faction="england").errors)
      and "London_Province" in "; ".join(
          plan(what="delete", faction="england").errors))
gone2 = plan(what="delete", faction="slave")
back3 = campstrat.parse_strat(gone2.text) if gone2.text else None
check("a faction that holds nothing goes, and takes England's opinion of it",
      not gone2.errors and back3 is not None
      and back3.faction("slave") is None
      and "slave" not in stratcamp.standings_of(back3, "england")
      and "slave" not in stratcamp.relations_of(back3, "england")
      and "slave" not in back3.rosters["nonplayable"])
shutil.rmtree(made_root, ignore_errors=True)


# ---- 4c) what a faction has to do to win (16j-2) --------------------------------
print("\n4c) descr_win_conditions.txt, read and written")

WINS = joined(
    "; the two hordes are left out on purpose",
    "england",
    "hold_regions London_Province Caen_Province",
    "take_regions 45",
    "outlive france",
    "short_campaign hold_regions London_Province",
    "take_regions 15",
    "",
    "france",
    "hold_regions Paris_Province",
    "take_regions 40",
    "",
    "slave",
    "take_regions 1",
)
wf = winconds.parse_wins(WINS)
check("the win file round-trips byte for byte, comment and all",
      wf.serialise() == WINS and len(wf.records) == 3)
eng = wf.find("england")
check("a record is read as six slots, long campaign then short",
      eng.get("hold") == ["London_Province", "Caen_Province"]
      and eng.get("take") == 45 and eng.get("outlive") == ["france"]
      and eng.get("short_hold") == ["London_Province"]
      and eng.get("short_take") == 15 and eng.get("short_outlive") == [])
check("short_campaign is read as the switch it is, not as a slot of its own",
      eng.lines["short_hold"] == eng.short_at)
check("a record with no short campaign has none, rather than an empty one",
      wf.find("france").get("short_take") == 0)

empty = winconds.parse_wins(joined("x", "short_campaign hold_regions",
                                   "take_regions 3"))
check("hold_regions with nothing after it is a real line, and the common "
      "case - 45 of the 74 real short campaigns are that shape",
      empty.records[0].get("short_hold") == []
      and empty.records[0].get("short_take") == 3)


class _WinFacts(_Facts):
    """The fact table's two questions for a win condition: provinces, factions."""

    class _Region:
        def __init__(self, name):
            self.name, self.shown = name, name

    def __init__(self, mod, regions, strat, campaign="test_campaign"):
        _Facts.__init__(self, mod, campaign=campaign)
        # keyed lower case and holding the province's own spelling, which is how
        # the real fact table keys it
        self.by_name = {r.lower(): _WinFacts._Region(r) for r in regions}
        self.strat = strat

    def label_of(self, rf):
        return rf.name


wvoc = winconds.Vocabulary(_WinFacts(
    mod, ["London_Province", "Caen_Province", "Paris_Province"], sf))
check("a province the map does not declare is fatal",
      "win.region" in {f["code"] for f in winconds.check_record(
          wvoc, "england", {"hold": ["Atlantis_Province"]}) if f["fatal"]})
check("a count that is not a number is fatal",
      "win.count" in {f["code"] for f in winconds.check_record(
          wvoc, "england", {"take": "loads"}) if f["fatal"]})
check("asking for more provinces than the map has warns, with both numbers",
      "win.too_many" in {f["code"] for f in winconds.check_record(
          wvoc, "england", {"hold": ["London_Province"], "take": 99})})
check("a short campaign harder than the long one warns",
      "win.short_harder" in {f["code"] for f in winconds.check_record(
          wvoc, "england", {"take": 10, "short_take": 40,
                            "hold": ["London_Province"]})})
check("outliving yourself warns, and outliving a faction with no block warns",
      {"win.outlive_self", "win.outlive_unknown"}
      <= {f["code"] for f in winconds.check_record(
          wvoc, "england", {"take": 5, "outlive": ["england", "burgundy"]})})
check("a long campaign that asks for nothing warns that it is already won",
      "win.nothing" in {f["code"] for f in winconds.check_record(
          wvoc, "england", {})})
check("and a record this map can satisfy reports nothing at all",
      winconds.check_record(wvoc, "england",
                            {"hold": ["London_Province"], "take": 3,
                             "short_take": 2}) == [])
check("a faction with a block and no win record warns, the way vanilla's two "
      "hordes do",
      "win.missing" in {f["code"] for f in winconds.check_file(
          wvoc, winconds.parse_wins(joined("england", "take_regions 2")))})

win_root = Path(_tmp.mkdtemp(prefix="ut_sc_win_"))
win_dir = win_root / "data" / campstrat.CAMPAIGN_DIR_REL / "test_campaign"
win_dir.mkdir(parents=True)
(win_dir / winconds.REL_NAME).write_text(WINS, encoding=winconds.ENCODING,
                                         newline="")
win_mod = _Fake(win_root)
wfacts = _WinFacts(win_mod, ["London_Province", "Caen_Province",
                             "Paris_Province"], sf)


def winplan(**body):
    return winconds.plan_win(win_mod, wfacts,
                             {"campaign": "test_campaign", **body})


w = winplan(action="edit", faction="england", values={"take": "30"})
back = winconds.parse_wins(w.text) if w.text else None
check("one condition edited is one line rewritten and nothing else moved",
      not w.errors and back is not None
      and back.find("england").get("take") == 30
      and len(back.lines) == len(wf.lines)
      and sum(a != b for a, b in zip(wf.lines, back.lines)) == 1)
check("a slot the form did not send is a slot nobody edited",
      back.find("england").get("outlive") == ["france"]
      and back.find("england").get("short_take") == 15)

w = winplan(action="edit", faction="france",
            values={"short_take": "12", "short_outlive": ["england"]})
back = winconds.parse_wins(w.text)
check("a record that gains a whole short campaign gains the switch with it",
      not w.errors
      and back.lines[back.find("france").short_at]
      == "short_campaign hold_regions"
      and back.find("france").get("short_take") == 12)

w = winplan(action="edit", faction="england",
            values={"short_hold": [], "short_take": "", "short_outlive": []})
back = winconds.parse_wins(w.text)
check("and a record that loses its whole short campaign loses all of it",
      not w.errors and back.find("england").short_at == -1
      and len(back.lines) == len(wf.lines) - 2)

w = winplan(action="edit", faction="england",
            values={"short_hold": [], "short_take": "8"})
back = winconds.parse_wins(w.text)
check("a short campaign whose provinces go keeps the line that carries the "
      "switch - 45 of the 74 real ones are that shape",
      not w.errors
      and back.lines[back.find("england").short_at]
      == "short_campaign hold_regions"
      and back.find("england").get("short_take") == 8)

w = winplan(action="add", faction="burgundy",
            values={"hold": ["Paris_Province"], "take": "20"})
check("a faction with no block cannot be given a win condition",
      "win.faction" in {f["code"] for f in w.findings if f["fatal"]})
w = winplan(action="add", faction="france", values={"take": "5"})
check("and a faction that already has one is refused by line number",
      "already has a win condition on line 9" in "; ".join(w.errors))

w = winplan(action="delete", faction="france")
back = winconds.parse_wins(w.text)
check("a record deleted takes its own blank separator with it",
      not w.errors and back.find("france") is None
      and len(back.records) == 2
      and len(back.lines) == len(wf.lines) - 4)
check("and the two records either side of it are untouched",
      [r.faction for r in back.records] == ["england", "slave"]
      and back.lines[0] == wf.lines[0])
shutil.rmtree(win_root, ignore_errors=True)

# ---- 5) the two routes, a real save and its undo -------------------------------
print("\n5) /api/map/campaign and /api/map/campaign_plan|_apply")

src_root = _realmod.pick(
    "Third_Age_Reforged",
    need=f"{campstrat.CAMPAIGN_DIR_REL}/imperial_campaign/{campstrat.STRAT_NAME}")
camp = campstrat.campaigns(Mod(src_root))[0]
cfg = Path(_tmp.mkdtemp(prefix="ut_sccfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

# the map's own layers and one campaign file, and nothing else. A whole mod is
# gigabytes and the two routes read exactly these.
med2 = Path(_tmp.mkdtemp(prefix="ut_scmed2_"))
data = med2 / "mods" / "CampMod" / "data"
(data / campmap.BASE_REL).mkdir(parents=True)
for pth in (src_root / "data" / campmap.BASE_REL).iterdir():
    if pth.is_file():
        shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
camp_dir = data / campstrat.CAMPAIGN_DIR_REL / camp
camp_dir.mkdir(parents=True, exist_ok=True)
for got in (campstrat.STRAT_NAME, winconds.REL_NAME):
    here = src_root / "data" / campstrat.CAMPAIGN_DIR_REL / camp / got
    if here.is_file():
        shutil.copy2(here, camp_dir / got)
for extra in ("descr_sm_factions.txt", "descr_regions.txt"):
    got = src_root / "data" / extra
    if got.is_file():
        shutil.copy2(got, data / extra)
config.save_settings(med2_root=str(med2), run_full_cleaner=False)

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"  serving {BASE} - {camp} copied from {src_root.name}")

strat_path = camp_dir / campstrat.STRAT_NAME
rel = f"{campstrat.CAMPAIGN_DIR_REL}/{camp}/{campstrat.STRAT_NAME}"
was = strat_path.read_bytes()


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
    t0 = time.time()
    det = get(f"/api/map/campaign?mod=CampMod&campaign={camp}")
    check(f"GET /api/map/campaign answers with the whole campaign "
          f"({(time.time() - t0) * 1000:.0f} ms)",
          det.get("factions") and det.get("rosters")
          and set(det["values"]) == set(stratcamp.VALUES)
          and det["diplomacy_line"] > 0)
    check("and every faction carries its own row of the matrix, both ways",
          all("standings" in f and "relationships" in f
              for f in det["factions"]))
    check("and every faction with a block is in one of the three lists",
          all(f["roster"] for f in det["factions"]))

    who = det["factions"][0]["name"]
    mine = dict(det["factions"][0]["standings"])
    other = next(f["name"] for f in det["factions"][1:] if f["name"] != who)
    t0 = time.time()
    res = post("/api/map/campaign_plan",
               {"mod": "CampMod", "campaign": camp, "what": "standings",
                "faction": who, "standings": {**mine, other: 0.25}})
    check(f"POST campaign_plan previews the row without writing "
          f"({(time.time() - t0) * 1000:.0f} ms)",
          res.get("plan", {}).get("ok")
          and strat_path.read_bytes() == was
          and res["plan"]["block"])

    res = post("/api/map/campaign_apply",
               {"mod": "CampMod", "campaign": camp, "what": "globals",
                "values": {"brigand_spawn_value": "42"},
                "flags": det["flags"]})
    after = read_text(strat_path, campstrat.ENCODING)
    done = campstrat.parse_strat(after)
    before = was.decode(campstrat.ENCODING)
    check("POST campaign_apply writes the header and backs the file up",
          res.get("id") and done.globals["brigand_spawn_value"] == "42"
          and after != before
          and res["record"]["manifest"]["backed_up"] == [rel])
    check("and it changed exactly the one line it said it would",
          sum(a != b for a, b in zip(before.splitlines(),
                                     after.splitlines())) == 1
          and len(after.splitlines()) == len(before.splitlines()))

    again = get(f"/api/map/campaign?mod=CampMod&campaign={camp}")
    check("and the panel, re-read, is holding what was written",
          again["values"]["brigand_spawn_value"] == "42")

    post("/api/undo", {"id": res["record"]["id"]})
    check("undo puts descr_strat.txt back byte-exact",
          strat_path.read_bytes() == was)

    wins_path = camp_dir / winconds.REL_NAME
    if wins_path.is_file():
        win_was = wins_path.read_bytes()
        wd = get(f"/api/map/wins?mod=CampMod&campaign={camp}")
        check(f"GET /api/map/wins answers with every faction's conditions "
              f"({len(wd['records'])} of them)",
              wd.get("records") and wd.get("vocab", {}).get("regions"))
        who = wd["records"][0]["faction"]
        res = post("/api/map/wins_apply",
                   {"mod": "CampMod", "campaign": camp, "action": "edit",
                    "faction": who, "values": {"take": "33"}})
        done = winconds.parse_wins(
            read_text(wins_path, winconds.ENCODING))
        check("POST wins_apply writes one line and backs the file up",
              res.get("id") and done.find(who).get("take") == 33
              and len(done.lines) == len(winconds.parse_wins(
                  win_was.decode(winconds.ENCODING)).lines))
        post("/api/undo", {"id": res["record"]["id"]})
        check("and undo puts descr_win_conditions.txt back byte-exact",
              wins_path.read_bytes() == win_was)
finally:
    httpd.shutdown()
    shutil.rmtree(med2, ignore_errors=True)
    shutil.rmtree(cfg, ignore_errors=True)
    shutil.rmtree(toy_root, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
