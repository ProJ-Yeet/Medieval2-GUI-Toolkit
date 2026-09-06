"""``export_descr_guilds.txt`` - Phase 18a, M13.

The file the toolkit has refused against since Phase 12 and could not open. Four
claims under test, and the first one is the one the whole module turns on:

    a definition is two words   `Guild x` opens a block and `Guild x s 25`
                                inside a trigger does not. Read without that
                                rule every guild trigger ends at its own first
                                effect and the effects become definitions
    the file comes back         parse_text(t).text() == t on every installed
                                mod, and every block re-renders to itself
    the cross-checks fire       points awarded to a guild nothing declares, and
                                a guild no trigger ever feeds
    a save is a splice          one field edited rewrites one line and leaves
                                the comment banners and the tab stops alone

Five parts:

    1  the two-word rule, on text written here
    2  a file written here: parse, render, add, delete
    3  the checks, against faults built on purpose
    4  every installed mod: round trip, re-render, and what it finds
    5  plan and apply against a copy of a real mod

    python -m tests.test_guilds
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import guilds, triggers
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


SAMPLE = """\
;===============================================================
;== GUILD DATA ==
;===============================================================

;------------------------------------------
Guild assassins_guild
    building guild_assassins_guild
    levels  100 250 500

;------------------------------------------
Guild masons_guild
    building guild_masons_guild
    levels  150 350 650

;===============================================================
;== TRIGGER DATA ==
;===============================================================

;------------------------------------------
Trigger 0010_Recruit_Assassin
    WhenToTest AgentCreated

    Condition TrainedAgentType = assassin

    Guild assassins_guild s  10
    Guild assassins_guild o  2

;------------------------------------------
Trigger 0020_Build_Something
    WhenToTest BuildingCompleted

    Condition SettlementBuildingFinished = stone_wall

    Guild masons_guild s 25
"""


# ---- 1) the two-word rule ----------------------------------------------------
print("\n1) a definition is two words, an effect is four")

tf = triggers.parse_text(SAMPLE)
check("both triggers are read", len(tf.triggers) == 2)
check("the first trigger keeps all three of its lines",
      len(tf.triggers[0].effects) == 2 and len(tf.triggers[0].conditions) == 1)
check("the effect lines are not collected as definitions",
      tf.definitions.get("Guild") == ["assassins_guild", "masons_guild"])
check("an effect line carries guild, scope and points",
      tf.triggers[0].effects[0].args == ["assassins_guild", "s", "10"])
check("DEFINITION_WORDS is the rule, not a magic number",
      triggers.DEFINITION_WORDS == 2)


# ---- 2) a file written here --------------------------------------------------
print("\n2) parse, render, add and delete")

gf = guilds.parse_text(SAMPLE)
check("the file comes back byte for byte", gf.text() == SAMPLE)
check("both guilds are read", [g.name for g in gf.guilds]
      == ["assassins_guild", "masons_guild"])
check("a guild knows its building and its levels",
      gf.guilds[0].building == "guild_assassins_guild"
      and gf.guilds[0].levels == ["100", "250", "500"])
check("the trigger section is found", gf.trigger_start > gf.guilds[-1].end)

base = gf.block_text(gf.guilds[1])
check("a block re-renders to itself when nothing is edited",
      guilds.render_block(base, {}) == base)

edited = guilds.render_block(base, {"levels": "200 400 700"})
check("one field edited rewrites one line",
      sum(1 for a, b in zip(base.split("\n"), edited.split("\n")) if a != b) == 1)
check("…and the building line is untouched", "guild_masons_guild" in edited)

whole = guilds.replace_block(gf, gf.guilds[1], edited)
check("the rest of the file is byte-identical",
      whole.replace("200 400 700", "150 350 650") == SAMPLE)
check("the comment banners survive", whole.count(";---") == SAMPLE.count(";---"))

added = guilds.insert_block(gf, guilds.new_block(
    {"name": "woodsmens_guild", "building": "guild_woodsmens_guild"}))
after = guilds.parse_text(added)
check("a new guild lands above the trigger section",
      [g.name for g in after.guilds][-1] == "woodsmens_guild"
      and after.get("woodsmens_guild").start < after.trigger_start)
check("…and the trigger section still parses",
      len(triggers.parse_text(added).triggers) == 2)

dropped = guilds.parse_text(SAMPLE)
lines = list(dropped.lines)
g = dropped.get("masons_guild")
del lines[g.start:g.end]
check("deleting a block takes only its own lines",
      "masons_guild" not in "\n".join(lines[:g.start]))

try:
    guilds.parse_block("Trigger x\n")
    bad = False
except guilds.GuildError:
    bad = True
check("text that is not a guild is refused", bad)


# ---- 3) the checks -----------------------------------------------------------
print("\n3) the checks, against faults built on purpose")

known = {"guild_assassins_guild", "guild_masons_guild"}
codes = lambda fs: sorted({f["code"] for f in fs})

clean = guilds.check_file(guilds.parse_text(SAMPLE),
                          triggers.parse_text(SAMPLE), known)
check("a sound file reports nothing", clean == [], )

undeclared = SAMPLE.replace("Guild masons_guild s 25",
                            "Guild ghost_guild s 25")
fs = guilds.check_file(guilds.parse_text(undeclared),
                       triggers.parse_text(undeclared), known)
check("points to a guild nobody declared are reported",
      "undeclared" in codes(fs))
check("…and the guild nothing feeds any more is reported too",
      "never_awarded" in codes(fs))

for word in guilds.EFFECT_KEYWORDS:
    txt = SAMPLE.replace("Guild masons_guild s 25", f"Guild {word} s 25")
    fs = guilds.check_file(guilds.parse_text(txt), triggers.parse_text(txt), known)
    check(f"`Guild {word}` is an engine word, not an undeclared guild",
          "undeclared" not in codes(fs))

backwards = SAMPLE.replace("levels  150 350 650", "levels  650 350")
fs = guilds.check_file(guilds.parse_text(backwards),
                       triggers.parse_text(backwards), known)
check("thresholds that count down are reported", "levels_order" in codes(fs))
check("…and so is a levels line that is not three long",
      "levels_count" in codes(fs))
check("neither of them is fatal - the mod loads today",
      not any(f["fatal"] for f in fs))

noedb = guilds.check_file(guilds.parse_text(SAMPLE),
                          triggers.parse_text(SAMPLE), {"guild_masons_guild"})
check("a building line no EDB declares is reported",
      "unknown_building" in codes(noedb))
check("…and with no EDB to read, the rule does not run at all",
      "unknown_building" not in codes(guilds.check_file(
          guilds.parse_text(SAMPLE), triggers.parse_text(SAMPLE), None)))

twice = SAMPLE.replace("Guild masons_guild\n", "Guild assassins_guild\n", 1)
fs = guilds.check_file(guilds.parse_text(twice), triggers.parse_text(twice), known)
check("a guild declared twice is reported", "duplicate" in codes(fs))

scope = SAMPLE.replace("Guild masons_guild s 25", "Guild masons_guild z 25")
fs = guilds.check_file(guilds.parse_text(scope), triggers.parse_text(scope), known)
check("a scope letter outside s/o/a is reported", "unknown_scope" in codes(fs))
check("the three real scope letters are all accepted",
      sorted(guilds.SCOPES) == ["a", "o", "s"])


# ---- 4) every installed mod --------------------------------------------------
print("\n4) every export_descr_guilds.txt on this machine")

swept = 0
for root in _realmod.installed():
    path = root / "data" / guilds.GUILDS_REL
    if not path.exists():
        continue
    swept += 1
    mod = Mod(root)
    gf, text = guilds.read(mod)
    tf = triggers.parse_text(text)
    check(f"{root.name}: {len(gf.guilds)} guilds come back byte for byte",
          gf.text() == text)
    check(f"{root.name}: every block re-renders to itself unchanged",
          all(guilds.render_block(gf.block_text(g), {}) == gf.block_text(g)
              for g in gf.guilds))
    check(f"{root.name}: replacing a block with itself changes nothing",
          all(guilds.replace_block(gf, g, gf.block_text(g)) == text
              for g in gf.guilds))
    check(f"{root.name}: every block is a valid one-block pane",
          all(guilds.parse_block(gf.block_text(g) + "\n").name == g.name
              for g in gf.guilds))
    check(f"{root.name}: the span map covers every line of every block",
          all(set(guilds.block_spans(gf.block_text(g))) >= {"name"} | set(g.lines)
              for g in gf.guilds))
    ov = guilds.overview(mod)
    check(f"{root.name}: {len(ov['findings'])} findings, and not a flood",
          len(ov["findings"]) <= max(3, len(gf.guilds) // 2))
    check(f"{root.name}: no definition line is read as an effect",
          all(not g.name.split()[1:] for g in gf.guilds))
    awarded = {a.guild for a in guilds.awards(tf)}
    check(f"{root.name}: {len(awarded)} guild names are awarded points",
          bool(awarded))
    for f in ov["findings"]:
        print(f"       - {f['code']}: {f['message'][:96]}")
print(f"  swept {swept} file(s)")


# ---- 5) plan and apply -------------------------------------------------------
print("\n5) a save against a copy of a real mod")

src = _realmod.pick("Third_Age_Reforged", need=guilds.GUILDS_REL)
tmp = Path(_tmp.mkdtemp(prefix="ut_guilds_"))
dest = tmp / src.name
(dest / "data").mkdir(parents=True)
shutil.copy2(src / "data" / guilds.GUILDS_REL, dest / "data" / guilds.GUILDS_REL)
mod = Mod(dest)
before = (dest / "data" / guilds.GUILDS_REL).read_bytes()

gf, _ = guilds.read(mod)
name = gf.guilds[0].name
was = gf.guilds[0].get("levels")

p = guilds.plan(mod, {"guild": name, "edits": {"levels": "111 222 333"}})
check("the plan is ok and its diff names the one line that moved",
      p.payload()["ok"] and len(p.changes) == 2
      and all("levels" in c for c in p.changes))
check("nothing is written by a plan",
      (dest / "data" / guilds.GUILDS_REL).read_bytes() == before)

p2 = guilds.plan(mod, {"guild": name, "edits": {"levels": was}})
check("a save that changes nothing is refused, and says so",
      not p2.payload()["ok"] and "nothing to change" in p2.errors)

p3 = guilds.plan(mod, {"guild": name, "raw_block": f"Guild renamed_{name}\n"
                                                   "    building guild_x\n"
                                                   "    levels 1 2 3"})
check("renaming a guild in the raw pane is refused with the reason",
      p3.errors and "orphan" in p3.errors[0])

res = guilds.apply(p)
now = (dest / "data" / guilds.GUILDS_REL).read_bytes()
check("apply writes the file", now != before)
check("…and it is still the same file, one line different",
      sum(1 for a, b in zip(before.decode("latin-1").splitlines(),
                            now.decode("latin-1").splitlines()) if a != b) == 1)
check("the backup is byte-exact",
      (Path(res["record"]["backup_root"]) / "data"
       / guilds.GUILDS_REL).read_bytes() == before)
check("the log records it as a guilds job", res["record"]["mode"] == "guilds")
after_gf, _ = guilds.read(mod)
check("the edit is what was asked for",
      after_gf.get(name).get("levels") == "111 222 333")
check("every other guild is untouched",
      [g.name for g in after_gf.guilds] == [g.name for g in gf.guilds])

added = guilds.plan(mod, {"guild": "test_guild", "action": "add",
                          "edits": {"building": "guild_test_guild"}})
check("a new guild plans cleanly", added.payload()["ok"])
guilds.apply(added)
fresh, _ = guilds.read(mod)
check("…and lands above the trigger section",
      fresh.get("test_guild") is not None
      and fresh.get("test_guild").start < fresh.trigger_start)
check("…and the triggers all still parse",
      len(triggers.parse_file(dest / "data" / guilds.GUILDS_REL).triggers)
      == len(triggers.parse_text(before.decode("latin-1")).triggers))

gone = guilds.plan(mod, {"guild": "test_guild", "action": "delete"})
guilds.apply(gone)
check("deleting it puts the file back exactly as the first save left it - "
      "the separator banner goes with the block",
      (dest / "data" / guilds.GUILDS_REL).read_bytes() == now)

banner = guilds.parse_text(SAMPLE)
check("a `;===` section header is never taken for a block's banner",
      guilds._banner_span(banner, banner.guilds[0])[0]
      == banner.guilds[0].start - 2
      and banner.lines[banner.guilds[0].start - 1].strip().strip(";") == "-" * 42)


print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
