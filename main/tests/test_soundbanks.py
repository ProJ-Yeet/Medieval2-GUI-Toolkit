"""The six export sound banks - Phase 47a.

Four claims under test:

    the files come back     parse_text(t).to_text() == t for all six banks on
                            every installed mod, every event inside a block
    depth is the keyword    a VnV line travels with the header under it, and
                            prebattle's mixed tabs and spaces do not matter
    an edit is a splice     an event edit, a duplicate, a rename and a remove
                            each change only the lines they name
    the save is undoable    backup byte for byte, a log record, undo restores

Four parts:

    1  a bank written here: parse, VnV, named events
    2  the edits, on that bank
    3  every installed mod: round trip and structure
    4  plan, apply and undo on a copy of a real mod

    python -m tests.test_soundbanks
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, keyblock as kb, soundbanks as sb  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer.transfer import undo  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return cond


def use_temp_config():
    tmp = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = tmp
    config.BACKUP_DIR = tmp / "backups"
    config.SETTINGS_PATH = tmp / "settings.json"
    config.LOG_PATH = tmp / "transfers.json"


PRE = ("BANK: prebattle_speech\r\n"
       "\taccent Arabic\r\n"
       "\t\telement ONE_LINER\r\n"
       "\t\t\t\tevent\r\n"
       "\t\t\t\t\tfolder data/sounds/Voice\r\n"
       "\t\t\t\t\tone.mp3\r\n"
       "\t\t\t\tend\r\n"
       "\t\telement CHEERING_3\r\n"
       "\t\t\tVnV  \r\n"
       "\t\t\ttrait Anger\r\n"
       "\t\t\t\tevent\r\n"
       "\t\t\t\t\tfolder data/sounds/Voice/Human/Generic\r\n"
       "\t\t\t\t\tCheer01.mp3\r\n"
       "\t\t\t\tend\r\n"
       "\t\t\tVnV  \r\n"
       "                           pri 9\r\n"
       "\t\t\t\tevent\r\n"
       "\t\t\t\t\tfolder data/sounds/Voice/Human/Generic\r\n"
       "\t\t\t\t\tCheer02.mp3\r\n"
       "\t\t\t\tend\r\n"
       "\r\n"
       "\t\t\trelationship Hates england\r\n"
       "\t\t\t\tevent\r\n"
       "\t\t\t\t\tfolder data/sounds/Voice/Human/Generic\r\n"
       "\t\t\t\t\tBoo.mp3\r\n"
       "\t\t\t\tend\r\n")

SOLDIER = ("BANK: unit_voice\n"
           "\taccent Arabic\n"
           "\t\tclass General\n"
           "\t\t\tvocal Individual_Attack_Grunt\n"
           "\t\t\t\tevent mindist 0.75 priority 120 volume -10 probability .4\n"
           "\t\t\t\t\tfolder data/sounds/Voice/Human/Localized/Battle_Map\n"
           "\t\t\t\t\tA_1.wav\n"
           "\t\t\t\t\tA_2.wav\n"
           "\t\t\t\t\tfolder data/sounds/Voice/Human/Generic\n"
           "\t\t\t\t\tM_01.wav\n"
           "\t\t\t\t\twillhelm.wav probability .001 \n"
           "\t\t\t\tend\n")

NARR = (";###\r\n"
        "event HASTINGS_NARRATOR_1\n"
        "         folder data/sounds/Voice/Human/Localized/Narration\n"
        "         HASTINGS_NARRATOR_1.mp3\n"
        "end\n"
        "\n"
        "event HASTINGS_NARRATOR_2a\n"
        "         folder data/sounds/Voice/Human/Localized/Narration\n"
        "         HASTINGS_NARRATOR_2a.mp3\n"
        "end")


print("\n1  a bank written here")
b = sb.parse_text("prebattle", PRE)
check("the prebattle bank comes back byte for byte", b.to_text() == PRE)
check("BANK: names the bank", b.bank == "prebattle_speech")
check("depth is the keyword: accent, element, selector",
      [(n.depth, n.kw) for n in b.nodes] == [
          (0, "accent"), (1, "element"), (1, "element"),
          (2, "trait"), (2, "pri"), (2, "relationship")])
trait = next(n for n in b.nodes if n.kw == "trait")
pri = next(n for n in b.nodes if n.kw == "pri")
check("a VnV line is the first line of the block under it",
      trait.start == trait.head - 1 and trait.label == "VnV trait Anger"
      and pri.label == "VnV pri 9")
check("  even when the header under it is indented with spaces",
      pri.parent is trait.parent and pri.parent.value == "CHEERING_3")
rel = next(n for n in b.nodes if n.kw == "relationship")
check("a blank line between blocks belongs to neither",
      pri.end == rel.start - 1 and PRE.splitlines()[pri.end] == "")
check("an element that holds an event directly owns it",
      len(b.nodes[1].events) == 1 and not b.nodes[1].children)

s = sb.parse_text("soldier_voice", SOLDIER)
ev = s.events[0]
check("an event line's attributes are read", ev.attrs.startswith("mindist 0.75"))
check("a sample line with attributes is kept as text",
      ev.lines(s.lines)[-1] == "willhelm.wav probability .001")

n = sb.parse_text("narration", NARR)
check("narration: every named event is its own block, none nested",
      [x.value for x in n.roots] == ["HASTINGS_NARRATOR_1", "HASTINGS_NARRATOR_2a"]
      and all(x.parent is None for x in n.nodes))
check("  and a file with no newline at the end comes back as it was",
      n.to_text() == NARR)
check("an unknown header is kept and reported, not guessed at",
      sb.parse_text("advice", "BANK: ADVICE\n  text A\n  mystery B\n  event\n"
                    "   folder x\n   a.mp3\n  end\n").warnings[0].find("mystery") > 0)


print("\n2  the edits")
new = sb.edit_event(s, ev.at, ev.attrs, ev.lines(s.lines)[:3] + ["A_3.wav"]
                    + ev.lines(s.lines)[3:])
check("adding a sample adds one line, with its neighbours' indent",
      new == SOLDIER.replace("A_2.wav\n", "A_2.wav\n\t\t\t\t\tA_3.wav\n"))
new = sb.edit_event(s, ev.at, "mindist 0.75 priority 90", ev.lines(s.lines))
check("changing the attributes rewrites the event line and nothing else",
      new == SOLDIER.replace("priority 120 volume -10 probability .4",
                             "priority 90"))
check("sending an event back unchanged rewrites nothing",
      sb.edit_event(s, ev.at, ev.attrs, ev.lines(s.lines)) == SOLDIER)
check("a new folder line takes the folder lines' indent",
      "\t\t\t\t\tfolder data/sounds/x\n" in sb.edit_event(
          s, ev.at, ev.attrs, ev.lines(s.lines) + ["folder data/sounds/x", "z.wav"]))

dup = sb.duplicate(b, trait.head, "Coward")
check("duplicating a VnV block copies the VnV line with it, straight after",
      dup.count("VnV") == 3 and "\t\t\tVnV  \r\n\t\t\ttrait Coward\r\n" in dup
      and dup.index("trait Coward") < dup.index("pri 9"))
check("  and the copy reads back as its own block",
      [x.label for x in sb.parse_text("prebattle", dup).nodes if x.depth == 2][:2]
      == ["VnV trait Anger", "VnV trait Coward"])
d2 = sb.duplicate(n, n.roots[-1].head, "HASTINGS_NARRATOR_9")
check("duplicating the last line of a file with no final newline keeps it so",
      d2.endswith("HASTINGS_NARRATOR_9.mp3".replace("9", "2a") + "\nend")
      and "event HASTINGS_NARRATOR_2a\n" in d2 and "event HASTINGS_NARRATOR_9\n" in d2
      and sb.parse_text("narration", d2).to_text() == d2)
check("removing a block takes its lines and leaves the rest",
      sb.remove(b, rel.head) == PRE[:PRE.index("\t\t\trelationship")])
check("renaming a block changes one word on one line",
      sb.rename(b, rel.head, "Hates france") == PRE.replace("Hates england", "Hates france"))


print("\n3  every installed mod")
mods = _realmod.installed()
seen = 0
for root in mods:
    for f, spec in sb.FILES.items():
        path = root / "data" / spec["rel"]
        if not path.exists():
            continue
        seen += 1
        t = kb.read_text(path, sb.ENCODING)
        bank = sb.parse_text(f, t)
        owned = {id(e) for x in bank.nodes for e in x.events}
        check(f"{root.name} {f}: byte for byte, {len(bank.events)} events all in a "
              f"block, no warnings",
              bank.to_text() == t and len(owned) == len(bank.events)
              and not bank.warnings)
check("at least one bank was measured", seen > 0)


print("\n4  plan, apply and undo on a copy of a real mod")
use_temp_config()
src = _realmod.pick("Divide_and_Conquer_EUR", need=sb.FILES["stratmap_voice"]["rel"])
tmp = Path(_tmp.mkdtemp(prefix="ut_sbank_"))
dest = tmp / src.name
(dest / "data").mkdir(parents=True)
for spec in sb.FILES.values():
    if (src / "data" / spec["rel"]).exists():
        shutil.copy2(src / "data" / spec["rel"], dest / "data" / spec["rel"])
mod = Mod(dest)
rel = sb.FILES["stratmap_voice"]["rel"]
before = (dest / "data" / rel).read_bytes()
ov = sb.overview(mod, "stratmap_voice")
check("the overview names the six files and this one's blocks",
      len(ov["files"]) == 6 and ov["nodes"] and ov["events"] > 0)
vocal = next(x for x in ov["nodes"] if x["kw"] == "vocal" and x["events"])
e0 = vocal["events"][0]
acc = next(x for x in ov["nodes"] if x["kw"] == "accent")
pl = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "event", "at": e0["at"], "head": e0["head_text"], "attrs": e0["attrs"],
     "lines": e0["lines"] + ["extra_line.mp3"]},
    {"op": "duplicate", "at": acc["head"], "head": acc["head_text"],
     "value": "Gondorian"}]})
check("an event edit and an accent duplicate plan together",
      pl.payload()["ok"] and len(pl.changes) == 2)
check("  and the new accent is said to be unused until something names it",
      any("does not point anything at it" in w for w in pl.warnings))
after = sb.parse_text("stratmap_voice", pl.text)
g = [x for x in after.nodes if x.kw == "accent" and x.value == "Gondorian"]
orig = [x for x in after.nodes if x.kw == "accent" and x.value == acc["value"]]
check("  the copy has the source's every type and vocal",
      len(g) == 1 and [c.label for c in g[0].children]
      == [c.label for c in orig[0].children])
check("  and carries the event edit, because it ran first (bottom up)",
      "extra_line.mp3" in pl.text and pl.text.count("extra_line.mp3") in (1, 2))
res = sb.apply(pl)
check("apply writes the planned text", (dest / "data" / rel).read_bytes()
      == pl.text.encode("latin-1"))
check("  backs the old file up byte for byte",
      (Path(res["backup_root"]) / "data" / rel).read_bytes() == before)
check("  under its own mode in the log", res["mode"] == "soundbanks")
undo(res["id"])
check("undo puts the file back byte for byte",
      (dest / "data" / rel).read_bytes() == before)

stale = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "remove", "at": acc["head"], "head": "accent Nowhere"}]})
check("an op whose line no longer says what it said is refused",
      not stale.payload()["ok"] and "changed since" in stale.errors[0])
taken = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "duplicate", "at": acc["head"], "head": acc["head_text"],
     "value": acc["value"]}]})
check("a duplicate onto a name already beside it is refused",
      not taken.payload()["ok"] and "name of its own" in taken.errors[0])
bad = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "event", "at": e0["at"], "head": e0["head_text"], "attrs": "",
     "lines": ["a.mp3"]}]})
check("an event whose first line is not a folder is refused",
      not bad.payload()["ok"] and "folder" in bad.errors[0])
bad = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "event", "at": e0["at"], "head": e0["head_text"], "attrs": "",
     "lines": ["folder x", "end", "a.mp3"]}]})
check("a line of 'end' inside an event is refused", not bad.payload()["ok"])
odd = sb.plan(mod, {"file": "stratmap_voice", "ops": [
    {"op": "event", "at": e0["at"], "head": e0["head_text"], "attrs": "loudness 3",
     "lines": e0["lines"]}]})
check("an attribute no bank in the mod uses is a warning, not a refusal",
      odd.payload()["ok"] and any("loudness" in w for w in odd.warnings))
check("the unknown file id is refused",
      not sb.plan(mod, {"file": "units_voice", "ops": []}).payload()["ok"])

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
