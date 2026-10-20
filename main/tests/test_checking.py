"""96e2: checking - the game's log explained, the contents report, the deep check.

What each part is here to catch:

  * **the log is read the way the game writes it**: timed lines with an area
    and a level, a Script Error's reason on the untimed lines after it, and
    the same complaint about a hundred units folded into one row whose
    explanation names X and Y rather than the first unit.
  * **the crash comes first**: the last ASSERT or unspecified error is the
    stop, its cause the engine's own detail line, else the Script Error just
    before it; a fatal line the game went on after is "serious", not the stop.
  * **the log is found where the mod's .cfg sends it**, before the game
    folder's own.
  * **the contents report never dies of one part**: a mod with no EDU still
    gets its factions, with the EDU named as failed.
  * **a rehearsal writes nothing to the mod**: every byte of it is the same
    afterwards, the temp copy is gone, and the finding the port would add is
    reported as added.

    python -m tests.test_checking
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import changesets, gamelog, health, modreport, rehearse
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


LOG = (
    "09:00:00.000 [system.io] [info] reading\n"
    "09:00:01.000 [script.err] [error] Script Error in mods/T/data/world/maps/campaign/imperial_campaign/"
    "campaign_script.txt, at line 3, column 1\n"
    "   unrecognised condition 'IsFoo'\n"
    "09:00:02.000 [game.script] [error] unit(Peasants) does not match up to the ownership for faction(england)\n"
    "09:00:02.100 [game.script] [error] unit(Spearmen) does not match up to the ownership for faction(france)\n"
    "09:00:02.200 [data.invalid] [warning] open: data/ui/foo.tga is missing\n"
    "09:00:03.000 [system.rpt] [fatal] ERROR: Unresolved sprite definition(FACTION_LOGO_X)\n"
    "09:00:04.000 [system.rpt] [fatal] ASSERT FAILED: src\\skeleton.cpp(204): adata != 0\n"
)

print("the log, line by line")
entries = gamelog.parse(LOG)
check("every error and warning line is read, the info line is not", len(entries) == 6)
check("a Script Error carries its file, line and reason",
      entries[0]["file"].endswith("campaign_script.txt") and entries[0]["line"] == 3
      and "IsFoo" in entries[0]["why"])
groups = gamelog.summary(entries)
own = [g for g in groups if "ownership" in g[0]["msg"]][0]
check("two units with the same complaint are one row of two", own[1] == 2)
generic = gamelog.explain(own[0]["msg"], generic=len({w for _, w in own[2]}) > 1)
check("and its words name X and Y, not the first unit", "Y" in generic and "england" not in generic)
check("a fatal line comes before every error", groups[0][0]["level"] == "fatal")

print("\nthe crash doctor")
v = gamelog.verdict(LOG)
check("the last ASSERT is the stop", v and v["stopped"])
check("its cause is the known skeleton crash", "animation" in v["headline"])
check("the fatal line it went on after is serious, not the stop",
      any("FACTION_LOGO_X" in s for s in v["serious"]))
check("a log with nothing to say has no verdict",
      gamelog.verdict("09:00:00.000 [system.io] [info] fine\n") is None)
closed = gamelog.verdict("09:00:00.000 [x] [info] libs called display_close\n")
check("a game closed the usual way says so", closed and not closed["stopped"])

print("\nwhere the log is")
game = Path(_tmp.mkdtemp(prefix="ut_chk_")) / "Medieval II Total War"
mod_root = game / "mods" / "T"
(mod_root / "data").mkdir(parents=True)
(mod_root / "T.cfg").write_text("[log]\nto = mods/T/logs/t.system.log.txt\nlevel = * error\n", encoding="latin-1")
(mod_root / "logs").mkdir()
(mod_root / "logs" / "t.system.log.txt").write_text(LOG, encoding="utf-8")
(game / "system.log.txt").write_text("old\n", encoding="utf-8")
os.utime(game / "system.log.txt", (1, 1))
check("the .cfg's [log] to = path is looked at first",
      gamelog.candidates(mod_root)[0] == game / "mods/T/logs/t.system.log.txt")
got = gamelog.read(mod_root)
check("and read", got["found"] and got["path"].endswith("t.system.log.txt") and got["errors"] == 5)
(mod_root / "logs" / "t.system.log.txt").unlink()
(game / "system.log.txt").unlink()
none = gamelog.read(mod_root)
check("no log at all says how to turn it on", not none["found"] and "[log]" in none["howto"])

print("\nthe contents report")
(mod_root / "data" / "descr_sm_factions.txt").write_text(
    "faction\tengland\nculture\tnorthern_european\nreligion\tcatholic\n", encoding="latin-1")
rep = modreport.build(Mod(mod_root))
check("a mod with no EDU still gets its factions", [f["slot"] for f in rep.get("factions", [])] == ["england"])
check("with the parts it could not read named", "units" in rep["failed"])
check("and the Markdown says so too", "units" in modreport.text(rep) and "# T" in modreport.text(rep))

print("\nthe deep check")
data = mod_root / "data"
(data / "export_descr_unit.txt").write_text("type Peasants\n", encoding="latin-1")
(data / "textures").mkdir()
(data / "textures" / "a.texture").write_bytes(b"DDS")
(data / "world" / "maps").mkdir(parents=True)
(data / "world" / "maps" / "x.txt").write_text("keep\n", encoding="latin-1")
before = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
real_plan = changesets.plan_port


def fake_plan(set_name, target):
    port = changesets.Port(set_name, target)
    cur = (Path(target.data) / "descr_sm_factions.txt").read_bytes()
    mine = cur.replace(b"religion\tcatholic", b"religion\tno_such_religion")
    changesets._file_items(port, "descr_sm_factions.txt", cur, mine, cur)
    return port


changesets.plan_port = fake_plan
real_run = health.run


def only_factions(m, *a, **k):
    return real_run(m, only=("factions",))


health.run = only_factions
try:
    r = rehearse.run(Mod(mod_root), "probe")
finally:
    changesets.plan_port = real_plan
    health.run = real_run
check("the record that would go on is rehearsed", r["files"] == ["descr_sm_factions.txt"] and r["records"] == 1)
after = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
check("every byte of the mod is the same afterwards", before == after)
check("the copy is gone", not list(Path(tempfile.gettempdir()).glob("ut_rehearse_*")))
check("folders it did not touch were joined, not copied file by file", r["linked"] >= 1)
check("the rehearsal reports what the port would change",
      isinstance(r["added"], list) and isinstance(r["cleared"], list))
try:
    changesets.plan_port = lambda s, t: changesets.Port(s, t)
    rehearse.run(Mod(mod_root), "empty")
    check("a set with nothing to put on is refused", False)
except rehearse.RehearseError:
    check("a set with nothing to put on is refused", True)
finally:
    changesets.plan_port = real_plan

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
