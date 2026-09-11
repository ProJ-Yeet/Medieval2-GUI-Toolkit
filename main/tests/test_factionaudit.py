"""Is this faction complete? - the audit, its repair, and its undo (21, D6).

Run:  python -m tests.test_factionaudit

Three parts:

1. **A synthetic mod** with three factions: `sicily` has everything, `milan`
   lacks its strat-map textures, and `venice` is in the roster and the campaign
   and almost nowhere else. The audit has to say exactly which rows are gaps,
   which are notes and which it could not check at all.
2. **The repair**, written and undone. It copies only the gaps (never a note),
   copies each one once, and puts every file back byte for byte on undo.
3. **The installed mods**, read-only. What is asserted is the shape of the
   answer and the one invariant the module promises - the count and the repair
   agree about what a record is - not any mod's own numbers, which change with
   the build installed (the lesson of the four DaC suites).
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config                                    # noqa: E402
from unittransfer import factionaudit as fa                        # noqa: E402
from unittransfer import factionclone as fc                        # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


NL = chr(13) + chr(10)


def crlf(text: str) -> str:
    return NL.join(text.strip("\n").split("\n")) + NL


def rec(slot, culture="southern_european"):
    return f"""
faction						{slot}
culture						{culture}
religion					catholic
primary_colour				red 245, green 245, blue 245
secondary_colour			red 130, green 20, blue 30
standard_index				6
"""


CAMP = "world/maps/campaign/imperial_campaign"

FILES = {
"descr_sm_factions.txt": rec("sicily") + rec("milan") + rec("venice"),

"export_descr_unit.txt": """
type             Sicilian Spearmen
dictionary       Sicilian_Spearmen
category         infantry
class            light
attributes       sea_faring
ownership        sicily
type             Sicilian Bodyguard
dictionary       Sicilian_Bodyguard
category         cavalry
class            heavy
attributes       general_unit
ownership        sicily, milan
""",

"export_descr_buildings.txt": """
building hinterland_castle
{
	levels motte_and_bailey
	{
		motte_and_bailey requires factions { sicily, milan, }
		{
			recruit_pool "Sicilian Spearmen"  1  0.5  4  0  requires factions { sicily, }
		}
	}
}
""",

"descr_sounds_accents.txt": """
accent English
    factions milan, sicily, slave
""",

"descr_faction_standing.txt": """
FactionStanding exclude_factions { sicily, milan } normalise -1.0 20
""",

"descr_character.txt": """
type					named character
faction			sicily, milan
strat_model		sm_general
type					spy
faction			sicily
strat_model		sm_spy
""",

"descr_model_strat.txt": """
type				sm_spy
skeleton			strat_spy
texture				sicily, models_strat/textures/spy_sicily.tga
model_flexi_m		data/models_strat/spy.CAS, max
""",

"descr_names.txt": """
faction: sicily

	characters
		Ruggiero
		Tancredi

	women
		Costanza

faction: milan

	characters
		Ottone
""",

"descr_lbc_db.txt": """
faction sicily
model southern_peasant			 40

faction milan
model southern_peasant			 40
""",

"descr_offmap_models.txt": """
navy
{
	faction sicily
	{
		large 	data/models_off_map/bireme.CAS	100 0
	}
}
""",

f"{CAMP}/descr_strat.txt": """
campaign		imperial_campaign
playable
	sicily
	venice
end
unlockable
end
nonplayable
	milan
	slave
end

start_date	1080 summer
end_date	1530 winter

faction	sicily, balanced smith
denari	5000
character	Roger, named character, male, leader, age 40, x 10, y 10

faction	venice, balanced smith
denari	5000

faction	slave, balanced smith
denari	5000
""",

f"{CAMP}/descr_win_conditions.txt": """
sicily
hold_regions Palermo
take_regions 20
""",
}

EXPANDED = """
{SICILY}	Kingdom of Sicily
{EMT_SICILY_SPY}	Sicilian Spy
{EMT_VICTORY_SICILY}	Sicily is victorious!
{MILAN}	Duchy of Milan
{EMT_MILAN_SPY}	Milanese Spy
"""


def build(root: Path) -> None:
    data = root / "data"
    for rel, body in FILES.items():
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(path, crlf(body), fc.ENCODING)
    exp = data / "text" / "expanded.txt"
    exp.parent.mkdir(parents=True, exist_ok=True)
    kb.write_text(exp, crlf(EXPANDED), "utf-16")


def rows_of(audit, slot):
    f = next(x for x in audit["factions"] if x["slot"] == slot)
    return f, {r["id"]: r for r in f["rows"]}


# ---------------------------------------------------------------------------
print("=== 1. the audit, on a synthetic mod ===")
tmp = Path(_tmp.mkdtemp(prefix="ut_facaudit_"))
root = tmp / "AuditMod"
build(root)
mod = Mod(root)
data = root / "data"

a = fa.audit(mod)
check("every roster slot is audited, then the campaign's slot the roster lacks",
      [f["slot"] for f in a["factions"]] == ["sicily", "milan", "venice", "slave"])
f, r = rows_of(a, "slave")
check("a campaign block with no roster record is a roster GAP, fixed by Add a faction",
      r["roster"]["state"] == "missing" and r["roster"]["fix"] == "addfaction"
      and not f["in_roster"] and f["template"] == "")
check("every faction has one row per check",
      all(len(f["rows"]) == len(fa.CHECKS) for f in a["factions"]))

f, r = rows_of(a, "sicily")
check(f"the complete faction has no gap ({f['gaps']})", f["gaps"] == 0)
check("…and names itself in the text key and the event keys",
      r["text"]["state"] == "ok" and "Kingdom of Sicily" in r["text"]["detail"])
check("…and its campaign block is counted, leader included",
      r["campaign"]["state"] == "ok" and "a leader" in r["campaign"]["detail"])

check("a file that is not there is UNKNOWN, not missing (the evidence rule)",
      r["skins"]["state"] == "unknown" and "modeldb" in r["skins"]["detail"])

f, r = rows_of(a, "milan")
check("milan's one gap is its strat-map textures",
      f["gaps"] == 1 and r["strat_models"]["state"] == "missing")
check("milan has no campaign block, so needs no win record (not a gap)",
      r["campaign"]["state"] == "missing" and r["campaign"]["level"] == "note"
      and r["wins"]["state"] == "ok")

f, r = rows_of(a, "venice")
gaps = sorted(x["id"] for x in f["rows"] if x["state"] == "missing" and x["level"] == "gap")
check(f"venice's gaps are exactly the eight it lacks ({', '.join(gaps)})",
      gaps == sorted(["text", "names", "characters", "units", "buildings",
                      "accent", "strat_models", "wins"]))
notes = sorted(x["id"] for x in f["rows"] if x["state"] == "missing" and x["level"] == "note")
check(f"…and its notes are the files working mods go without ({', '.join(notes)})",
      notes == sorted(["generals", "populace", "navy", "standing"]))
check("a block in the campaign and no win record IS a gap",
      r["wins"]["state"] == "missing" and r["wins"]["fix"] == "wins")
check("the template offered for venice is the one that has what it lacks (sicily)",
      f["template"] == "sicily")
check("slave is never offered as a template",
      all(x["template"] != "slave" for x in a["factions"]))

# the evidence rule, again: take a file away and the row stops claiming anything
lbc = data / "descr_lbc_db.txt"
held = lbc.read_bytes()
lbc.unlink()
f2, r2 = rows_of(fa.audit(mod), "venice")
check("with descr_lbc_db.txt gone, venice's populace row is unknown, not a note",
      r2["populace"]["state"] == "unknown" and f2["notes"] == f["notes"] - 1)
lbc.write_bytes(held)


# ---------------------------------------------------------------------------
print("\n=== 2. the repair: plan, write, re-audit, undo ===")
before = {p.relative_to(root).as_posix(): p.read_bytes()
          for p in root.rglob("*") if p.is_file()}

bad = fa.repair_plan(mod, {"faction": "venice", "template": "venice"})
check("a faction cannot be repaired from itself", bool(bad.errors))
bad = fa.repair_plan(mod, {"faction": "venice", "template": "rome"})
check("a template outside the roster is refused", bool(bad.errors))
bad = fa.repair_plan(mod, {"faction": "carthage", "template": "sicily"})
check("a slot outside the roster is sent to Add a faction",
      bad.errors and "Add a faction" in bad.errors[0])
bad = fa.repair_plan(mod, {"faction": "venice", "template": "sicily", "checks": ["wins"]})
check("the win record is not a copy - it is the Winning tab's",
      bad.errors and "Winning" in bad.errors[0])

p = fa.repair_plan(mod, {"faction": "venice", "template": "sicily"})
check("the plan is clean", not p.errors and p.action == "repair")
written = sorted(e.rel for e in p.written())
check(f"it writes the seven files with a gap, and no note ({len(written)})",
      written == sorted(["text/expanded.txt", "descr_names.txt", "descr_character.txt",
                         "export_descr_unit.txt", "export_descr_buildings.txt",
                         "descr_sounds_accents.txt", "descr_model_strat.txt"]))
check("the unit roster warning names what is being given",
      any("whole roster" in w for w in p.warnings))
check("the summary says repair, not clone",
      p.summary().startswith("repair faction venice from sicily"))

res = fc.apply(p)
tid = res["id"]
entry = next(e for e in config.load_log() if e.get("id") == tid)
check("the log entry is a repair, with its template",
      entry["action"] == "repair" and entry["options"] == {"template": "sicily"})

names = kb.read_text(data / "descr_names.txt", fc.ENCODING)
check("descr_names gained one venice section, copied from sicily's",
      names.count("faction: venice") == 1 and names.count("Ruggiero") == 2)
edu = kb.read_text(data / "export_descr_unit.txt", fc.ENCODING)
check("venice joined every ownership line sicily is on",
      "ownership        sicily, venice" in edu
      and "ownership        sicily, milan, venice" in edu)
exp = kb.read_text(data / "text" / "expanded.txt", "utf-16")
check("the shown name is a placeholder, never sicily's",
      "{VENICE}\tvenice" in exp and exp.count("Kingdom of Sicily") == 1)
check("the event keys came across with sicily's words",
      "{EMT_VENICE_SPY}\tSicilian Spy" in exp)
check("the file kept CRLF",
      NL in names and "\n" not in names.replace(NL, ""))
check("no note was written: venice still has no off-map block",
      "faction venice" not in kb.read_text(data / "descr_offmap_models.txt", fc.ENCODING))

f, r = rows_of(fa.audit(Mod(root)), "venice")
left = [x["id"] for x in f["rows"] if x["state"] == "missing" and x["level"] == "gap"]
check(f"after the repair the one gap left is the win record ({left})", left == ["wins"])

again = fa.repair_plan(Mod(root), {"faction": "venice", "template": "sicily"})
check("a second repair has nothing to do", bool(again.errors)
      and "nothing to repair" in again.errors[0])
note = fa.repair_plan(Mod(root), {"faction": "venice", "template": "sicily",
                                  "checks": ["navy"]})
check("a note can still be copied from its own row",
      not note.errors and [e.rel for e in note.written()] == ["descr_offmap_models.txt"])
had = fa.repair_plan(Mod(root), {"faction": "venice", "template": "sicily",
                                 "checks": ["names", "navy"]})
check("a row the faction already has is skipped and said so",
      any("already has it" in n for n in had.notes)
      and [e.rel for e in had.written()] == ["descr_offmap_models.txt"])

transfer.undo(tid)
after = {p.relative_to(root).as_posix(): p.read_bytes()
         for p in root.rglob("*") if p.is_file()}
check("undo restored every file byte for byte",
      all(after.get(k) == v for k, v in before.items()))
extra = sorted(set(after) - set(before))
check(f"undo left no file behind{': ' + ', '.join(extra) if extra else ''}", not extra)
config.update_log(tid, note="test_factionaudit - synthetic mod, discarded")
shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
print("\n=== 3. the installed mods, read-only ===")
from tests import _realmod                                          # noqa: E402
from unittransfer import campstrat                                  # noqa: E402

mods = _realmod.installed()
if not mods:
    print("  [skip] no installed mod")
for path in mods:
    real = Mod(path)
    camps = campstrat.campaign_paths(real) or [""]
    for camp in camps:
        started = time.perf_counter()
        au = fa.audit(real, camp)
        ms = (time.perf_counter() - started) * 1000
        check(f"{path.name}/{camp or 'default'}: {len(au['factions'])} factions "
              f"audited in {ms:.0f} ms", au["factions"] and ms < 5000)
        # every file that is on disk is actually checked
        present = {c.id for c in fa.CHECKS if c.rel and (real.data / c.rel).is_file()}
        unknown = {r["id"] for f in au["factions"] for r in f["rows"]
                   if r["state"] == "unknown" and r["id"] in present
                   and r["id"] not in ("campaign", "wins")}
        check(f"  no row is unknown for a file that is there{': ' + str(unknown) if unknown else ''}",
              not unknown)
    # the invariant: a row the census calls present, the cloner agrees has the
    # faction in it, and a row it calls missing, the cloner finds nothing to
    # collide with. Measured by asking the cloner to copy each faction onto a
    # name nobody has - the count it reports is what the census counted.
    c = fa.Census(real)
    edb = kb.read_text(real.data / "export_descr_buildings.txt", fc.ENCODING)
    edb = kb.to_newline(edb, "\n")
    wrong = [s for s in c.slots
             if fc.clone_braced_list(edb, s, "zz_probe", ("factions",))[1]
             != (c.edb or {}).get(s, 0)]
    check(f"{path.name}: the EDB count and the cloner agree for every faction"
          + (f" (not {wrong[:3]})" if wrong else ""), not wrong)
    acc = kb.to_newline(kb.read_text(real.data / "descr_sounds_accents.txt", fc.ENCODING), "\n")
    wrong = [s for s in c.slots
             if bool(fc.clone_list_lines(acc, s, "zz_probe", "factions")[1])
             != (s in (c.accents or {}))]
    check(f"{path.name}: the accent row and the cloner agree for every faction"
          + (f" (not {wrong[:3]})" if wrong else ""), not wrong)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
