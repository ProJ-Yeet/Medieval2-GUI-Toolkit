"""Events and disasters - Phase 18b: M3 and M4.

    M3  descr_events.txt      the historical events a campaign fires, and where
    M4  descr_disasters.txt   the eight natural disasters, and where they may be

Six claims, and every one of them is something the reference tool's two parsers
get wrong on their own files:

    every file comes back        parse(t).text() == t, on the game's own two
                                 files and on every copy in every installed mod.
                                 The game's descr_events.txt is 6,194 bytes, of
                                 which the whole top half is commented-out test
                                 cases, and it ends WITHOUT a newline
    dates repeat                 one event may carry four `date` lines; Third
                                 Age Reforged's Fellowship campaign does. A
                                 parser holding one loses three
    a slot is a line             vanilla's `plague` block has no `warning` line.
                                 An absent slot is a line to add, in the file's
                                 own key order, and one cleared is a line to
                                 remove - never `warning` with nothing after it
    the categories are the       the file's own header names `counter`,
    file's own header            `historic`, `volcano`, `plague` and
                                 `emergent_faction`, and its live lines also use
                                 `earthquake`. It does NOT name the five extra
                                 disaster types the reference tool offers
    `the sea` is not a region    vanilla's `storm` and `horde` both write
                                 `region the sea`, and there is no such region
                                 in descr_regions.txt. A rule that did not know
                                 that would report the shipping game as broken
    a position is on the map     off the grid refuses the save and names the
                                 coordinate; in the sea is a finding mapcheck
                                 raises, because that one needs the layers

Seven parts:

    1  the disaster file: parse, edit, add, delete
    2  the event file: the same, plus repeated dates and the movie line
    3  the checks, each shown firing and shown silent with no evidence
    4  every copy of either file on this machine, round-tripped
    5  plan and apply against a copy of a real folder
    6  the positions the marker layer is drawn from
    7  mapcheck's own rule over the two files

    python -m tests.test_campevents
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campevents as ce
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


codes = lambda fs: sorted({f["code"] for f in fs})
msgs = lambda fs: " | ".join(f["message"] for f in fs)

#: The game's own install, when it is on this machine. Both installed mods ship
#: these two files EMPTY - measured, 0 bytes each - so the only real content
#: either parser can be held against is the unpacked stock data.
GAME = _realmod.MODS.parent

# Vanilla's descr_disasters.txt, entire. 1,567 bytes in the game and quoted here
# because it is the format arbiter: the file documents itself in its own header,
# `plague` is missing a `warning` line, and `storm` and `horde` name a region
# that is not one.
DISASTERS = (
    "\r\n"
    "; event\t\t\tevent_type\r\n"
    "; frequency\t\tin years\r\n"
    "; min_scale\t\tminimum size for event\r\n"
    "\r\n"
    "event\t\tearthquake\r\n"
    "frequency\t20\r\n"
    "winter\t\tfalse\r\n"
    "summer\t\tfalse\r\n"
    "warning\t\tfalse\r\n"
    "climate\t\trocky_desert\r\n"
    "min_scale\t2\r\n"
    "max_scale\t5\r\n"
    "\r\n"
    "event\t\tstorm\r\n"
    "frequency\t4\r\n"
    "winter\t\ttrue\r\n"
    "summer\t\tfalse\r\n"
    "warning\t\tfalse\r\n"
    "region\t\tthe sea\r\n"
    "min_scale\t2\r\n"
    "max_scale\t5\r\n"
    "\r\n"
    "event\t\tplague\r\n"
    "frequency\t20\r\n"
    "winter\t\tfalse\r\n"
    "summer\t\tfalse\r\n"
    "min_scale\t2\r\n"
    "max_scale\t5\r\n"
)

# An excerpt of the game's own descr_events.txt, keeping the three things that
# make it awkward: a commented-out block above the live ones, a `date` range,
# and NO trailing newline on the last line, which is itself a comment.
EVENTS = (
    "; historical events and when they occur\r\n"
    ";\r\n"
    "; Currently supported categories are:\r\n"
    "; counter  - just increase a counter\r\n"
    "; emergent_faction - triggers the emergence of the given faction.\r\n"
    "\r\n"
    ";event\thistoric\tmongols_invasion_warn\r\n"
    ";date\t2\r\n"
    "\r\n"
    "event\thistoric \tfirst_windmill\r\n"
    "date\t50\r\n"
    "\r\n"
    "event\tearthquake\tearthquake_in_aleppo\r\n"
    "date\t58\r\n"
    "position\t257, 73\r\n"
    "\r\n"
    "event\thistoric\tgunpowder_discovered\r\n"
    "date\t210 220\r\n"
    "movie\tevent/gunpowder_invented.bik\r\n"
    "\r\n"
    "event\tplague \t\tblack_death_hits\r\n"
    "date\t266\r\n"
    "position\t281, 163\r\n"
    "position\t258, 134\r\n"
    "\r\n"
    ";event\tvolcano\t\teruption_at_vesuvius\r\n"
    ";date\t99\r\n"
    ";position\t103, 65"
)

# Third Age Reforged's Fellowship campaign, uncommented: four `date` lines on
# one event, which is the case a parser holding a single date loses.
MANY_DATES = (
    "event\thistoric\tlarge_city_barracks\r\n"
    "date\t7 8\r\n"
    "date\t28 32 turns 1.4\r\n"
    "date\t32 40 turns 1.3\r\n"
)


# ---- 1) descr_disasters.txt --------------------------------------------------
print("1) descr_disasters.txt")

df = ce.parse_disasters(DISASTERS)
check("the file comes back byte for byte", df.text() == DISASTERS)
check("three blocks, and the comment header is not one of them",
      [b.kind for b in df.blocks] == ["earthquake", "storm", "plague"])
check("nothing in it is a warning", not df.warnings)

plague = df.by_name("plague")
check("vanilla's plague really has no `warning` line",
      not plague.has("warning") and plague.first("warning") == "")
check("a repeatable key comes back as a list",
      df.by_name("storm").all("region") == ["the sea"])

out, changed = ce.render_disaster(df, plague, {"warning": True})
lines_before = DISASTERS.split("\r\n")
lines_after = out.split("\r\n")
check("giving plague a warning adds exactly one line",
      len(lines_after) == len(lines_before) + 1 and changed == ["+ warning true"])
check("…in the file's own key order, under `summer`",
      lines_after[lines_after.index("warning\t\ttrue") - 1] == "summer\t\tfalse")
check("…and in the file's own column, not with a copied gap",
      "warning\t\ttrue" in lines_after)

out, changed = ce.render_disaster(df, df.by_name("earthquake"), {"warning": ""})
check("clearing it removes the line rather than writing it empty",
      "warning" not in out.split("event\t\tstorm")[0].split("climate")[0]
      and changed == ["- warning false"])

out, changed = ce.render_disaster(df, df.by_name("earthquake"), {"frequency": 30})
check("one number changed rewrites one line",
      sum(1 for a, b in zip(lines_before, out.split("\r\n")) if a != b) == 1)

out, changed = ce.render_disaster(
    df, df.by_name("earthquake"),
    {"climates": ["rocky_desert", "sandy_desert"], "positions": [[10, 20]]})
after = ce.parse_disasters(out).by_name("earthquake")
check("a climate added and a position added land in key order",
      after.all("climate") == ["rocky_desert", "sandy_desert"]
      and [(p.x, p.y) for p in after.positions] == [(10, 20)])
check("…and `position` sits above `min_scale`, where the file puts it",
      after.lines["position"][0] < after.lines["min_scale"][0])

rows = ce.new_disaster_lines("flood", {"frequency": 10, "climates": ["swamp"]},
                             ce._column(df))
grown = ce.insert_block(df, rows)
gf = ce.parse_disasters(grown)
check("a new block parses, and is the eight-key block vanilla writes",
      gf.by_name("flood") is not None
      and [r.split("\t")[0] for r in rows]
      == ["event", "frequency", "winter", "summer", "warning", "climate",
          "min_scale", "max_scale"])
check("adding a block and deleting it again restores the file exactly",
      ce.remove_block(gf, gf.by_name("flood")) == DISASTERS)


# ---- 2) descr_events.txt -----------------------------------------------------
print("\n2) descr_events.txt")

ef = ce.parse_events(EVENTS)
check("the file comes back byte for byte, with no trailing newline",
      ef.text() == EVENTS and not ef.trailing_newline)
check("only the five live blocks are blocks",
      [b.name for b in ef.blocks]
      == ["first_windmill", "earthquake_in_aleppo", "gunpowder_discovered",
          "black_death_hits"] + [])
check("a commented-out block is not read as one",
      ef.by_name("mongols_invasion_warn") is None
      and ef.by_name("eruption_at_vesuvius") is None)
check("the head line's trailing space does not become part of the category",
      ef.by_name("first_windmill").kind == "historic")
check("a date range is one date line, kept as written",
      ef.by_name("gunpowder_discovered").all("date") == ["210 220"])
check("two positions come back as two",
      [(p.x, p.y) for p in ef.by_name("black_death_hits").positions]
      == [(281, 163), (258, 134)])

mf = ce.parse_events(MANY_DATES)
check("four `date` lines on one event are four, not one",
      mf.blocks[0].all("date")
      == ["7 8", "28 32 turns 1.4", "32 40 turns 1.3"])

out, changed = ce.render_event(ef, ef.by_name("earthquake_in_aleppo"),
                               {"dates": ["59"]})
check("changing a date rewrites one line, and reads as one change",
      sum(1 for a, b in zip(EVENTS.split("\r\n"), out.split("\r\n")) if a != b) == 1
      and changed == ["date 58 -> 59"])

out, _ = ce.render_event(ef, ef.by_name("first_windmill"),
                         {"movie": "event/windmill.bik"})
grown_lines = out.split("\r\n")
check("a movie line is added under the date, where the file puts it",
      grown_lines[grown_lines.index("movie\tevent/windmill.bik") - 1] == "date\t50")

out, changed = ce.render_event(ef, ef.by_name("gunpowder_discovered"),
                               {"movie": ""})
check("a movie cleared loses its line",
      "gunpowder_invented" not in out and changed == ["- movie event/gunpowder_invented.bik"])

out, changed = ce.render_event(
    ef, ef.by_name("black_death_hits"),
    {"positions": [[281, 163], [258, 134], [99, 44]]})
check("a third position is appended after the second",
      [(p.x, p.y) for p in ce.parse_events(out).by_name("black_death_hits").positions]
      == [(281, 163), (258, 134), (99, 44)]
      and changed == ["+ position 99, 44"])

out, changed = ce.render_event(ef, ef.by_name("black_death_hits"),
                               {"positions": [[281, 163]]})
check("a position removed takes one line and says so as a removal",
      changed == ["- position 258, 134"])

out, changed = ce.render_event(ef, ef.by_name("first_windmill"),
                               {"name": "first_watermill"})
check("a rename rewrites the head line and makes no second block",
      "event\thistoric \tfirst_watermill" in out
      and len(ce.parse_events(out).blocks) == len(ef.blocks))

try:
    ce.render_event(ef, ef.by_name("first_windmill"), {"dates": []})
    dated = False
except ce.CampEventError:
    dated = True
check("an event may not be left with no date at all", dated)

rows = ce.new_event_lines("emergent_faction", "mongols", {"dates": ["128 144"]},
                          ce._pad(ef))
grown = ce.insert_block(ef, rows)
gf = ce.parse_events(grown)
check("a new event parses and is separated by a blank line",
      gf.by_name("mongols") is not None and grown.split("\r\n")[-3] == "")
check("adding an event and deleting it again restores the file exactly",
      ce.remove_block(gf, gf.by_name("mongols")) == EVENTS)


# ---- 3) the checks -----------------------------------------------------------
print("\n3) what each file is checked for, and what it says nothing about")

f = ce.check_disasters(ce.parse_disasters(DISASTERS))
check("vanilla's own disaster file produces no finding at all: " + msgs(f), not f)
f = ce.check_disasters(ce.parse_disasters(DISASTERS),
                       regions=["Aleppo_Province", "Naples_Province"])
check("…including with a region list, because `the sea` is not a region and is "
      "still right", not f)
f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("region\t\tthe sea", "region\t\tAtlantis")),
    regions=["Aleppo_Province"])
check("…but a region that really is not one is reported: " + msgs(f),
      codes(f) == ["unknown_region"])

f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("event\t\tstorm", "event\t\ttempest")))
check("a type outside the eight is a warning, not a refusal",
      codes(f) == ["unknown_type"] and not any(x["fatal"] for x in f))
f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("min_scale\t2\r\nmax_scale\t5\r\n\r\nevent\t\tstorm",
                      "min_scale\t9\r\nmax_scale\t5\r\n\r\nevent\t\tstorm")))
check("min_scale above max_scale is fatal: " + msgs(f),
      codes(f) == ["scale_order"] and all(x["fatal"] for x in f))
f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("climate\t\trocky_desert", "climate\t\tmordor")),
    climates=["rocky_desert", "swamp"])
check("a climate the mod does not declare is reported: " + msgs(f),
      codes(f) == ["unknown_climate"])
f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("climate\t\trocky_desert", "climate\t\tmordor")))
check("…and with no climate list, nothing is said about any climate", not f)
f = ce.check_disasters(ce.parse_disasters(DISASTERS), size=(295, 189))
check("no disaster in vanilla has a position, so the grid rule finds nothing",
      not f)
f = ce.check_disasters(ce.parse_disasters(
    DISASTERS.replace("min_scale\t2\r\nmax_scale\t5\r\n\r\nevent\t\tstorm",
                      "position\t900, 900\r\nmin_scale\t2\r\nmax_scale\t5"
                      "\r\n\r\nevent\t\tstorm")), size=(295, 189))
check("a position off the grid is fatal and names the coordinate: " + msgs(f),
      codes(f) == ["position_off"] and "900,900" in msgs(f))

f = ce.check_events(ce.parse_events(EVENTS))
check("vanilla's own event blocks produce no finding: " + msgs(f), not f)
f = ce.check_events(ce.parse_events(
    EVENTS.replace("event\thistoric \tfirst_windmill", "event\tflood \tfirst_windmill")))
check("a category the file's own header does not name is a warning: " + msgs(f),
      codes(f) == ["unknown_category"] and not any(x["fatal"] for x in f))
check("…and the message names the five the header does",
      "emergent_faction" in msgs(f) and "counter" in msgs(f))
f = ce.check_events(ce.parse_events(EVENTS.replace("date\t50\r\n", "")))
check("an event with no date is fatal: " + msgs(f),
      codes(f) == ["no_date"] and all(x["fatal"] for x in f))
f = ce.check_events(ce.parse_events(EVENTS.replace("date\t50", "date\t1")))
check("a date of 0 or 1 is a warning, because it never appears: " + msgs(f),
      codes(f) == ["date_zero"])
f = ce.check_events(ce.parse_events(
    EVENTS.replace("position\t257, 73\r\n", "")))
check("an earthquake with no position does nothing, and is said to: " + msgs(f),
      codes(f) == ["no_position"])
f = ce.check_events(ce.parse_events(EVENTS), factions=["england", "france"])
check("with a faction list and no emergent_faction event, nothing is said",
      not f)
f = ce.check_events(ce.parse_events(
    EVENTS + "\r\n\r\nevent\temergent_faction\tmongols\r\ndate\t128"),
    factions=["england", "france"])
check("an emergent faction with no block in descr_strat is reported: " + msgs(f),
      codes(f) == ["unknown_faction"])
f = ce.check_events(ce.parse_events(
    EVENTS + "\r\n\r\nevent\temergent_faction\tmongols\r\ndate\t128"))
check("…and with no faction list, nothing is said about any faction", not f)
f = ce.check_events(ce.parse_events(
    EVENTS + "\r\n\r\nevent\thistoric\tfirst_windmill\r\ndate\t99"))
check("the same label twice is a warning naming the first line: " + msgs(f),
      codes(f) == ["duplicate"] and "line 10" in msgs(f))


# ---- 4) every copy of either file on this machine ----------------------------
print("\n4) every descr_events.txt and descr_disasters.txt on disk")

roots = [GAME] if (GAME / "data").is_dir() else []
roots += _realmod.installed()
seen = 0
for root in roots:
    data = root / "data"
    files = sorted(data.glob("world/maps/campaign/**/descr_events.txt"))
    files += sorted(data.glob("world/maps/**/descr_disasters.txt"))
    for path in files:
        raw = kb.read_text(path, ce.ENCODING)
        parse = (ce.parse_events if path.name == ce.EVENTS_NAME
                 else ce.parse_disasters)
        bf = parse(raw)
        seen += 1
        check(f"{root.name}/{path.name} ({len(raw)} bytes, {len(bf.blocks)} "
              f"block(s)) comes back byte for byte", bf.text() == raw)
        if bf.warnings:
            for w in bf.warnings[:3]:
                print(f"       ! {w}")
if not seen:
    print("  (no copy of either file found - nothing to round-trip)")
else:
    print(f"  {seen} file(s) round-tripped")


# ---- 5) plan and apply -------------------------------------------------------
print("\n5) a save against a copy of a real folder")

tmp = Path(_tmp.mkdtemp(prefix="ut_campevents_"))
dest = tmp / "TestMod"
camp = ce.DEFAULT_CAMPAIGN
(dest / "data" / ce.CAMPAIGN_DIR_REL / camp).mkdir(parents=True)
(dest / "data" / "world/maps/base").mkdir(parents=True)
kb.write_text(dest / "data" / ce.DISASTERS_REL, DISASTERS, ce.ENCODING)
kb.write_text(dest / "data" / ce.CAMPAIGN_DIR_REL / camp / ce.EVENTS_NAME,
              EVENTS, ce.ENCODING)
# descr_terrain.txt, so the off-the-grid rule has a grid to be off. Copied from
# a real mod when there is one, because its shape is not this suite's business.
src = _realmod.pick("Third_Age_Reforged", need="world/maps/base/descr_terrain.txt")
shutil.copy2(src / "data/world/maps/base/descr_terrain.txt",
             dest / "data/world/maps/base/descr_terrain.txt")
mod = Mod(dest)
size = ce._map_size(mod)
check(f"the copy has a {size[0]}x{size[1]} grid to be checked against", bool(size))

before = (dest / "data" / ce.DISASTERS_REL).read_bytes()
p = ce.plan(mod, {"what": "disasters", "name": "plague",
                  "edits": {"warning": "true", "frequency": "25"}})
check(f"a disaster save plans two changes: {p.changes}",
      p.payload()["ok"] and p.changes == ["frequency 20 -> 25", "+ warning true"])
check("nothing is written by a plan",
      (dest / "data" / ce.DISASTERS_REL).read_bytes() == before)
res = ce.apply(p)
now = kb.read_text(dest / "data" / ce.DISASTERS_REL, ce.ENCODING)
check("the file is written and the block reads back",
      ce.parse_disasters(now).by_name("plague").first("warning") == "true")
check("…and exactly one line differs plus one added",
      len(now.split("\r\n")) == len(DISASTERS.split("\r\n")) + 1)
check("the file is in the backup set",
      res["record"]["manifest"]["backed_up"] == [ce.DISASTERS_REL])
check("the backup is byte-exact",
      (Path(res["record"]["backup_root"]) / "data"
       / ce.DISASTERS_REL).read_bytes() == before)
check("the log records it as a campevents job",
      res["record"]["mode"] == "campevents"
      and res["record"]["options"]["what"] == "disasters")

p = ce.plan(mod, {"what": "events", "campaign": camp, "name": "earthquake_in_aleppo",
                  "edits": {"positions": [[9000, 9000]]}})
check("a position off the map refuses the save and names the coordinate: "
      + "; ".join(p.errors),
      not p.payload()["ok"] and any("9000,9000" in e for e in p.errors))
try:
    ce.apply(p)
    refused = False
except ValueError:
    refused = True
check("…and applying it anyway raises rather than writing", refused)

p = ce.plan(mod, {"what": "events", "campaign": camp, "action": "add",
                  "name": "test_event", "edits": {"category": "historic",
                                                  "dates": ["2"]}})
check("adding an event plans one change", p.payload()["ok"] and len(p.changes) == 1)
ce.apply(p)
v = ce.events_view(mod, camp)
check("the new event is in the view", any(r["name"] == "test_event" for r in v["rows"]))
gone = ce.plan(mod, {"what": "events", "campaign": camp, "action": "delete",
                     "name": "test_event"})
ce.apply(gone)
check("deleting it restores the file exactly",
      kb.read_text(dest / "data" / ce.CAMPAIGN_DIR_REL / camp / ce.EVENTS_NAME,
                   ce.ENCODING) == EVENTS)

p = ce.plan(mod, {"what": "disasters", "action": "add", "name": "earthquake",
                  "edits": {}})
check("a disaster the file already declares is refused: " + "; ".join(p.errors),
      not p.payload()["ok"] and "already" in "; ".join(p.errors))
p = ce.plan(mod, {"what": "nonsense", "name": "x", "edits": {}})
check("a save about neither file is refused by name", not p.payload()["ok"])


# ---- 6) the marker layer -----------------------------------------------------
print("\n6) what 17d's marker layer is given")

pos = ce.positions(mod, camp)
kinds = sorted({p["kind"] for p in pos})
check(f"{len(pos)} position(s) over two files, of kinds {kinds}",
      kinds == ["event"] and len(pos) == 3)
check("each one carries the coordinates the FILE writes, unflipped",
      {(p["x"], p["y"]) for p in pos} == {(257, 73), (281, 163), (258, 134)})
check("an event marker says its date and a disaster its frequency",
      all("date" in p for p in pos if p["kind"] == "event"))
check("every marker names the block it came from",
      all(p["name"] for p in pos))
check("a mod with neither file gets an empty list, not an error",
      ce.positions(Mod(src)) is not None)


# ---- 7) mapcheck's own rule --------------------------------------------------
print("\n7) mapcheck learns about a position off the map or in the sea")

from unittransfer import mapcheck                                   # noqa: E402

check("the rule is registered with a source, like every other one",
      any(r.code == "event.position" and r.source for r in mapcheck.RULES))
if (GAME / "data").is_dir():
    rep = mapcheck.run(Mod(GAME))
    mine = [f for f in rep.findings if f.code == "event.position"]
    check(f"the game's own map has {len(mine)} of them: "
          + "; ".join(f.message for f in mine)[:110],
          all(f.file.endswith(ce.EVENTS_NAME) or f.file == ce.DISASTERS_REL
              for f in mine))
    check("each one carries the line it is on and the tile to jump to",
          all(f.line > 0 for f in mine)
          and all(f.tile for f in mine if f.severity == "warn"))
    check("the fingerprint holds no line number, so adding a line above one "
          "does not make it a new finding",
          all(str(f.line) not in f.what for f in mine))
else:
    print("  (the unpacked game is not on this machine - rule not run against it)")


print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
