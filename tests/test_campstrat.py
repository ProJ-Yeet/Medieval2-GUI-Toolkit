"""``descr_strat.txt``, read - Phase 16b's exit criteria, measured.

:mod:`unittransfer.campstrat` turns the file the whole campaign is defined in
into a tree of line spans. 16h to 16j write into it, so the gate on all three is
here: the file has to come back out exactly as it went in.

Two halves. The first needs no mod - the record forms, the brace-depth rule that
tells a settlement's ``region`` field from the regions section, the block
terminators, and the malformed lines a real mod actually contains. The second
runs over vanilla's two campaigns and every installed mod, and where the mod is
DaC it checks the numbers this phase was scoped against:

    13,153 lines and no trailing newline, round-tripping byte-exact
    31 factions, 199 settlements, 1,044 buildings
    305 characters, 286 armies, 1,468 units
    161 character_records, 79 relatives
    812 faction_standings, 57 faction_relationships
    126 regions, 105 forts, 295 watchtowers, 1,131 resources

    python -m tests.test_campstrat
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod
from unittransfer import campstrat
from unittransfer.keyblock import read_text
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


# ---- 1) the shape of the file, on text written here --------------------------
print("\n1) the sections, in order")

SAMPLE = joined(
    "campaign imperial_campaign",
    "",
    ";##### Factions #####",
    "playable",
    "\tengland",
    "\tfrance",
    "end",
    "unlockable",
    "\tspain",
    "end",
    "nonplayable",
    "\tslave",
    "end",
    "",
    "start_date\t1080 summer",
    "end_date\t1530 winter",
    "timescale\t2.00",
    "night_battles_enabled",
    "brigand_spawn_value 32",
    "",
    "resource\tgold,\t\t120,\t45 ; a comment",
    "resource\tsilk, 200, 90",
    "",
    "faction\tengland, balanced smith",
    "\tai_label\tdefault",
    "\tdenari\t10000",
    "\tdenari_kings_purse\t2500",
    "",
    "settlement castle",
    "{",
    "\tlevel town",
    "\tregion London_Province",
    "\tyear_founded 0",
    "\tpopulation 1200",
    "\tplan_set default_set",
    "\tfaction_creator england",
    "\tbuilding",
    "\t{",
    "\t\ttype core_castle_building wooden_castle",
    "\t}",
    "\tbuilding",
    "\t{",
    "\t\ttype castle_barracks garrison_quarters",
    "\t}",
    "}",
    "",
    "character\tWilliam, named character, male, leader, age 40, x 10, y 20, "
    "portrait william, battle_model king, hero_ability SHIELD, label william_1",
    "traits\t\tGoodCommander 2, Loyal 1",
    "ancillaries\tdrillmaster, standard",
    "army",
    "unit\t\tKnights\t\texp 2 armour 1 weapon_lvl 1",
    "unit\t\tSpearmen\texp 0 armour 0 weapon_lvl 0",
    "",
    "character\tsub_faction spain, El_Cid, general, male, age 30, x 5, y 6",
    "army",
    "unit\t\tScouts\t\texp 0 armour 0 weapon_lvl 0",
    "",
    "character_record\tMatilda, female, age 38, alive, never_a_leader",
    "relative\t\tWilliam, Matilda, Rufus, end",
    "",
    "faction\tfrance, balanced smith",
    "\tai_label\tdefault",
    "\tdenari\t8000",
    "\tdenari_kings_purse\t2000",
    "\tundiscovered",
    "",
    "faction_standings\tengland,\t0.80\tfrance",
    "faction_relationships\tengland,\tat_war_with\t\tspain, slave",
    "",
    "region London_Province",
    "farming_level 3",
    "famine_threat 0",
    "fort 100 200",
    "fort 110 210 gondor_fort culture gondor",
    "watchtower 120 220",
    "",
    "script",
    "campaign_script.txt",
)

sf = campstrat.parse_strat(SAMPLE)
check("byte-exact round trip", sf.serialise() == SAMPLE)
check("the campaign names itself", sf.campaign == "imperial_campaign")
check("all three rosters read, in their own lists",
      sf.rosters == {"playable": ["england", "france"], "unlockable": ["spain"],
                     "nonplayable": ["slave"]})
check("campaign globals read, values and flags alike",
      sf.globals.get("start_date") == "1080 summer"
      and sf.globals.get("timescale") == "2.00"
      and sf.globals.get("night_battles_enabled") is True
      and sf.globals.get("brigand_spawn_value") == "32")
check("a global carries the line it came from",
      sf.lines[sf.global_lines["end_date"]].startswith("end_date"))

counts = sf.counts()
check(f"every kind counted once: {counts}",
      counts == {"resource": 2, "faction": 2, "settlement": 1, "building": 2,
                 "character": 2, "army": 2, "unit": 3, "character_record": 1,
                 "relative": 1, "faction_standings": 1, "faction_relationships": 1,
                 "region": 1, "fort": 2, "watchtower": 1, "script": 1})
check("nothing in a well-formed file is a problem", not sf.problems)

res = sf.of_kind("resource")
check("a resource reads through its tabs and its comment",
      res[0].fields == {"name": "gold", "x": 120, "y": 45}
      and res[1].fields == {"name": "silk", "x": 200, "y": 90})

eng = sf.faction("england")
check("a faction reads its name, its AI text and its money",
      eng and eng.get("ai") == "balanced smith" and eng.get("ai_label") == "default"
      and eng.get("denari") == 10000 and eng.get("denari_kings_purse") == 2500)
check("the AI tail is kept whole and split, and no meaning is invented",
      eng.get("ai_words") == ["balanced", "smith"])
fr = sf.faction("france")
check("a single-word faction flag is read (undiscovered, on vanilla's Aztecs)",
      fr and fr.get("undiscovered") is True)

st = sf.of_kind("settlement")[0]
check("a settlement reads its type and every field",
      st.get("settlement_type") == "castle" and st.get("level") == "town"
      and st.get("region") == "London_Province" and st.get("population") == 1200
      and st.get("faction_creator") == "england")
check("its buildings are its children, in file order",
      [b.name for b in sf.children_of(st, "building")]
      == ["core_castle_building", "castle_barracks"])
check("a building keeps the whole `type` text and its level",
      sf.children_of(st, "building")[0].get("type")
      == "core_castle_building wooden_castle"
      and sf.children_of(st, "building")[0].get("level") == "wooden_castle")

will = sf.of_kind("character")[0]
check("a character reads name, type, sex, rank, age and position",
      (will.name, will.get("type"), will.get("gender"), will.get("rank"),
       will.get("age"), will.get("x"), will.get("y"))
      == ("William", "named character", "male", "leader", 40, 10, 20))
check("and the tail keys, DaC's hero_ability and label included",
      will.get("portrait") == "william" and will.get("battle_model") == "king"
      and will.get("hero_ability") == "SHIELD" and will.get("label") == "william_1")
check("traits come back as name to level, ancillaries as a list",
      will.get("traits") == {"GoodCommander": 2, "Loyal": 1}
      and will.get("ancillaries") == ["drillmaster", "standard"])
check("his army is his, and holds both regiments",
      [u.name for u in sf.descendants_of(will, "unit")] == ["Knights", "Spearmen"])
cid = sf.of_kind("character")[1]
check("a sub_faction character keeps both the faction and the name",
      cid.get("sub_faction") == "spain" and cid.name == "El_Cid")

rec = sf.of_kind("character_record")[0]
check("an off-map character_record reads",
      (rec.name, rec.get("gender"), rec.get("age"), rec.get("dead"),
       rec.get("leadership")) == ("Matilda", "female", 38, None, "never_a_leader"))
rel = sf.of_kind("relative")[0]
check("a relative line is names in order, with `end` dropped",
      rel.get("names") == ["William", "Matilda", "Rufus"])

sta = sf.of_kind("faction_standings")[0]
check("a standing reads its value and who it is toward",
      sta.get("faction") == "england" and sta.get("value") == 0.80
      and sta.get("toward") == ["france"])
rl = sf.of_kind("faction_relationships")[0]
check("a relationship reads its kind and its list",
      rl.get("relation") == "at_war_with" and rl.get("toward") == ["spain", "slave"])

reg = sf.of_kind("region")[0]
check("a region in the regions section reads its two levels",
      reg.name == "London_Province" and reg.get("farming_level") == 3
      and reg.get("famine_threat") == 0)
forts = sf.of_kind("fort")
check("both fort forms read, and both belong to their region",
      forts[0].fields == {"x": 100, "y": 200, "type": "", "culture": "",
                          "region": "London_Province"}
      and forts[1].fields == {"x": 110, "y": 210, "type": "gondor_fort",
                              "culture": "gondor", "region": "London_Province"})
check("a watchtower is two numbers and its region",
      sf.of_kind("watchtower")[0].fields
      == {"x": 120, "y": 220, "region": "London_Province"})
check("the script line names its file",
      sf.of_kind("script")[0].get("file") == "campaign_script.txt")

# ---- 2) where a block ends ---------------------------------------------------
print("\n2) brace depth, and where a block ends")

check("a faction block runs to the next faction header",
      sf.lines[eng.start].startswith("faction\tengland")
      and sf.lines[eng.end + 1].startswith("faction\tfrance"))
check("and the last one ends at the diplomacy section",
      sf.lines[fr.end + 1].startswith("faction_standings"))
check("every settlement, character and unit sits inside a faction",
      all(sf.node_at(n.start).start >= 0 and
          any(f.start <= n.start <= f.end for f in sf.of_kind("faction"))
          for n in sf.of_kind("settlement") + sf.of_kind("character")))

DEPTH = joined(
    "faction\tengland, balanced smith",
    "settlement",
    "{",
    "\tlevel town",
    "\tregion Inside_The_Braces",     # a settlement field, not a section
    "\t; } a brace in a comment is not a brace",
    "\tbuilding",
    "\t{",
    "\t\ttype core_building wooden_pallisade",
    "\t}",
    "}",
    "region Outside_The_Braces",      # the regions section
    "watchtower 1 2",
)
df = campstrat.parse_strat(DEPTH)
check("a `region` line inside the braces is the settlement's province",
      df.of_kind("settlement")[0].get("region") == "Inside_The_Braces")
check("a `region` line outside them opens the regions section",
      [r.name for r in df.of_kind("region")] == ["Outside_The_Braces"])
check("a brace inside a comment does not move the depth",
      df.of_kind("building")[0].get("type") == "core_building wooden_pallisade"
      and df.of_kind("watchtower")[0].get("region") == "Outside_The_Braces")
check("the depth rule leaves the file byte-exact", df.serialise() == DEPTH)

# ---- 3) the lines a real mod actually contains -------------------------------
print("\n3) malformed lines, all six of them from DaC")

BROKEN = joined(
    "faction\torcs, balanced smith",
    "settlement tyuiop",                                    # 8464
    "{",
    "\tlevel town",
    "\tregion Somewhere",
    "}",
    "character\tMagor, named character, male, age 23,  x 300, y 344, portrait Magor,",
    "army",                                                 # 3747
    "unit\t\tWarg Skirmishers\texp 0 rmour 0 weapon_lvl 1",  # 9983
    "unit\t\tTrolls\t\texp 1 armour 1 weapon_lv",            # 10581
    "character\tsub_faction hre, Kothug, named character, general, male, age 39, x 1, y 2",
    "character\tSauron, named character, male, leader, x 505, y 480",   # 5376
)
bf = campstrat.parse_strat(BROKEN)
check("the file still round-trips byte-exact", bf.serialise() == BROKEN)
check("nothing was dropped: 1 settlement, 3 characters, 2 units",
      (len(bf.of_kind("settlement")), len(bf.of_kind("character")),
       len(bf.of_kind("unit"))) == (1, 3, 2))
msgs = " | ".join(m for _, _, m in bf.problems)
check("an invented settlement type is reported, with the word it wrote",
      "tyuiop" in msgs and bf.of_kind("settlement")[0].get("level") == "town")
check("a misspelled `armour` still gives up the unit and its numbers",
      bf.of_kind("unit")[0].name == "Warg Skirmishers"
      and bf.of_kind("unit")[0].get("armour") == 0 and "rmour" in msgs)
check("a truncated `weapon_lvl` is reported and the rest of the unit survives",
      bf.of_kind("unit")[1].name == "Trolls"
      and bf.of_kind("unit")[1].get("exp") == 1
      and "weapon level has no value" in msgs)
check("a trailing comma is reported, and the fields before it still read",
      bf.of_kind("character")[0].get("age") == 23
      and "trailing comma" in msgs)
check("two type words are reported, and the first one counts",
      bf.of_kind("character")[1].get("type") == "named character"
      and "only the first counts" in msgs)
check("a character with no age is reported, not silently aged 0",
      "age" not in bf.of_kind("character")[2].fields
      and "character has no age" in msgs)

# ---- 4) line endings, comments and the index ---------------------------------
print("\n4) line endings, comments and the index")

lf = campstrat.parse_strat(SAMPLE.replace(CR, "\n"))
check("a LF file comes back as a LF file",
      lf.newline == "\n" and lf.serialise() == SAMPLE.replace(CR, "\n"))
no_nl = SAMPLE[:-2]
check("a file with no trailing newline does not grow one",
      campstrat.parse_strat(no_nl).serialise() == no_nl)

check("node_at finds the innermost node holding a line",
      sf.node_at(st.start + 1) is st
      and sf.node_at(sf.children_of(st, "building")[1].start).kind == "building")
check("node_at on a faction's own field line returns the faction",
      sf.node_at(eng.start + 1) is eng)
check("node_at outside every node is None, not a guess",
      sf.node_at(0) is None)
check("descendants_of is a slice, and counts what is inside",
      len(sf.descendants_of(eng, "unit")) == 3
      and len(sf.descendants_of(fr, "unit")) == 0)
check("index_of finds a node without scanning", sf.index_of(will) >= 0
      and sf.nodes[sf.index_of(will)] is will)

# ---- 5) the real files --------------------------------------------------------
print("\n5) vanilla's campaigns and every installed mod")

roots = []
game = _realmod.MODS.parent
if (game / "data").is_dir():
    roots.append(game)
roots += _realmod.installed()
roots = [r for r in roots if (r / "data" / campstrat.CAMPAIGN_DIR_REL).is_dir()]

if not roots:
    print(f"  SKIPPED - nothing with {campstrat.CAMPAIGN_DIR_REL} under {_realmod.MODS}")
else:
    for root in roots:
        mod = Mod(root)
        names = campstrat.campaigns(mod)
        if not names:
            continue
        print(f"\n  -- {mod.name}: {', '.join(names)}")
        for name in names:
            t0 = time.time()
            f = campstrat.read_strat(mod, name)
            ms = (time.time() - t0) * 1000
            raw = read_text(f.path, campstrat.ENCODING)
            c = f.counts()
            check(f"{name}: {len(f.lines)} lines parse in one pass in {ms:.0f} ms "
                  f"({len(f.nodes)} nodes)", len(f.nodes) > 0)
            check(f"{name}: round-trips byte-exact", f.serialise() == raw)
            check(f"{name}: every faction is enumerated ({c.get('faction', 0)}) "
                  f"and every settlement ({c.get('settlement', 0)})",
                  c.get("faction", 0) > 0 and c.get("settlement", 0) > 0)
            inside = sum(len(f.descendants_of(x, "settlement"))
                         for x in f.of_kind("faction"))
            chars = sum(len(f.descendants_of(x, "character"))
                        for x in f.of_kind("faction"))
            check(f"{name}: every settlement and character belongs to a faction",
                  inside == c.get("settlement", 0) and chars == c.get("character", 0))
            check(f"{name}: every node sits inside its parent's span",
                  all(f.nodes[n.parent].start <= n.start
                      and n.end <= f.nodes[n.parent].end
                      for n in f.nodes if n.parent >= 0))
            check(f"{name}: node_at returns the innermost node on every "
                  f"node's own first line",
                  all((f.node_at(n.start) or n).start == n.start for n in f.nodes))
            if f.problems:
                print(f"       {len(f.problems)} line(s) the mod itself got wrong:")
                for line, kind, msg in f.problems:
                    print(f"         {line + 1:>6} {kind:<16} {msg[:78]}")
            else:
                check(f"{name}: nothing in it is malformed", True)

            if mod.name.lower().startswith("divide_and_conquer"):
                print("    (DaC: the numbers this phase was scoped against)")
                check("13,153 newlines, 13,154 lines, and no trailing newline",
                      len(f.lines) == 13154 and not f.trailing_newline)
                check("105 forts, 295 watchtowers, 1,131 resources",
                      (c["fort"], c["watchtower"], c["resource"]) == (105, 295, 1131))
                check("305 characters, 1,468 units, 79 relatives",
                      (c["character"], c["unit"], c["relative"]) == (305, 1468, 79))
                check("812 faction_standings, 57 faction_relationships",
                      (c["faction_standings"], c["faction_relationships"]) == (812, 57))
                check("31 factions, 199 settlements, 1,044 buildings, "
                      "286 armies, 161 character_records, 126 regions",
                      (c["faction"], c["settlement"], c["building"], c["army"],
                       c["character_record"], c["region"])
                      == (31, 199, 1044, 286, 161, 126))
                check("the nine lines DaC itself got wrong are all reported",
                      sorted({line + 1 for line, _, _ in f.problems})
                      == [3747, 5376, 8464, 9703, 9983, 10438, 10581, 10947, 10948])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
