"""Cloning a faction for real: write it, check it, undo it, check that too.

Run:  python -m tests.test_factionclone_apply

The read-only suite (``test_factionclone``) measures the nine cloners against
the real mods. This one is the other half - the part that touches the disk - and
it deliberately does NOT use a real mod. It builds a small one in a temp folder
with the same shapes and the same CRLF line endings, clones into it, and then
undoes the clone through the toolkit's own :func:`unittransfer.transfer.undo`.

Two things only a real write can prove:

* **the art copy is undoable.** ``undo`` removes a created path with
  ``Path.unlink()``, which raises on a directory and is swallowed - so an entry
  copied with ``copytree`` and listed in the manifest as a folder would survive
  the undo, leaving the clone's unit cards behind after the faction was taken
  back out. The manifest therefore lists files, and this test is what says so.
* **undo really restores, not approximately.** Every one of the nine files is
  compared byte for byte against what it held before the clone.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittransfer import config                                    # noqa: E402
from unittransfer import factionclone as fc                        # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


NL = chr(13) + chr(10)          # the game's line ending, written out


def crlf(text: str) -> str:
    return NL.join(text.strip("\n").split("\n")) + NL


#: A mod small enough to read in one screen and shaped exactly like a real one.
#: Three factions: `sicily` is the donor, `milan` is a bystander, and
#: `sicily_clone` exists purely to prove the donor's name is matched as a whole
#: slot - its art must not be dragged along by a clone of `sicily`.
FILES = {
"descr_sm_factions.txt": """
faction						sicily
culture						southern_european
religion					catholic
symbol						models_strat/symbol_sicily.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				red 245, green 245, blue 245
secondary_colour			red 130, green 20, blue 30
loading_logo				loading_screen/symbols/symbol128_sicily.tga
standard_index				6
logo_index					FACTION_LOGO_SICILY
small_logo_index			SMALL_FACTION_LOGO_SICILY
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes

faction						sicily_clone
culture						southern_european
religion					catholic
symbol						models_strat/symbol_sicily.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				red 200, green 200, blue 200
secondary_colour			red 130, green 20, blue 30
loading_logo				loading_screen/symbols/symbol128_sicily.tga
standard_index				8
logo_index					FACTION_LOGO_SICILY
small_logo_index			SMALL_FACTION_LOGO_SICILY
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes

faction						milan
culture						southern_european
religion					catholic
symbol						models_strat/symbol_milan.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				red 10, green 90, blue 40
secondary_colour			red 255, green 255, blue 255
loading_logo				loading_screen/symbols/symbol128_milan.tga
standard_index				7
logo_index					FACTION_LOGO_MILAN
small_logo_index			SMALL_FACTION_LOGO_MILAN
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes
""",

"export_descr_unit.txt": """
type             Sicilian Spearmen
dictionary       Sicilian_Spearmen
category         infantry
class            light
ownership        sicily
type             Shared Militia
dictionary       Shared_Militia
category         infantry
class            light
ownership        sicily, milan
type             Milanese Only
dictionary       Milanese_Only
category         infantry
class            light
ownership        milan
""",

"export_descr_buildings.txt": """
building hinterland_castle
{
	levels motte_and_bailey
	{
		motte_and_bailey requires factions { sicily, milan, }
		{
			recruit_pool "Sicilian Spearmen"  1  0.5  4  0  requires factions { sicily, }
			recruit_pool "Shared Militia"  1  0.5  4  0  requires factions { sicily, milan, }
			recruit_pool "Milanese Only"  1  0.5  4  0  requires factions { milan }
		}
	}
}
""",

"descr_sounds_accents.txt": """
accent English
    factions milan, sicily, slave

accent Scottish
    factions scotland
""",

"descr_faction_standing.txt": """
FactionStanding exclude_factions { sicily, milan } normalise -1.0 20
FactionStanding exclude_factions { milan } normalise -1.0 80
""",

"export_descr_ancillaries.txt": """
Ancillary tutor
	Condition FactionType sicily
	Effect Command 1
""",

"descr_character.txt": """
type					spy
faction			sicily, milan
strat_model		sm_spy
type					diplomat
faction			sicily
strat_model		sm_diplomat
type					assassin
faction			milan
strat_model		sm_assassin
""",

"descr_model_strat.txt": """
type				sm_spy
skeleton			strat_spy
texture				sicily, models_strat/textures/spy_sicily.tga
texture				milan, models_strat/textures/spy_milan.tga
model_flexi_m		data/models_strat/spy.CAS, max

type				sm_diplomat
skeleton			strat_diplomat
texture				sicily, models_strat/textures/diplomat_sicily.tga
model_flexi_m		data/models_strat/diplomat.CAS, max
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
		Matteo
""",

"descr_lbc_db.txt": """
faction sicily
model southern_peasant			 40
model southern_female_peasant    60

faction milan
model southern_peasant			 40
model southern_female_peasant    60
""",

"descr_offmap_models.txt": """
navy
{
	faction sicily
	{
		large 	data/models_off_map/bireme.CAS	100 0
		small	data/models_off_map/bireme.CAS	100 0
	}

	faction milan
	{
		large 	data/models_off_map/bireme.CAS	100 0
		small	data/models_off_map/bireme.CAS	100 0
	}
}
""",
}

#: ``text/expanded.txt`` is UTF-16, so it is written apart from the rest
EXPANDED = """
{SICILY}	Kingdom of Sicily
{SICILY_DESCR}	The Kingdom of Sicily, rich and contested.
{EMT_SICILY_SPY}	Sicilian Spy
{EMT_SICILY_DIPLOMAT}	Sicilian Diplomat
{EMT_VICTORY_SICILY}	Sicily is victorious!
{MILAN}	Duchy of Milan
{EMT_MILAN_SPY}	Milanese Spy
"""

#: art named by convention, which is what the copier is allowed to take
ART = ["ui/units/sicily/#sicilian_spearmen.tga",
       "ui/units/sicily/#shared_militia.tga",
       "ui/unit_info/sicily/sicilian_spearmen_info.tga",
       "ui/faction_symbols/sicily.tga",
       "ui/captain banners/captain_card_sicily.tga",
       "menu/symbols/fe_buttons_24/symbol24_sicily.tga",
       "menu/symbols/fe_buttons_24/symbol24_sicily_grey.tga",
       "banners/textures/faction_banner_sicily.texture",
       # a longer slot that merely CONTAINS the donor's name: must be left alone
       "ui/faction_symbols/sicily_clone.tga",
       # art the copier must not touch, because a line points at it by path
       "models_strat/textures/spy_sicily.tga"]


def build(root: Path) -> None:
    """Write the fixture with the endings it says it has.

    ``Path.write_text`` translates on Windows, so a CRLF string handed to it
    comes back with its carriage return doubled; ``Path.read_text`` translates
    the other way and would hide a line-ending bug rather than catch one -- it
    is why four checks here first "failed" against a file that was perfectly
    correct on disk. Both sides therefore go through ``keyblock``, which is what
    the toolkit itself uses and never lets the platform decide.
    """
    data = root / "data"
    for rel, body in FILES.items():
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(path, crlf(body), fc.ENCODING)
    exp = data / "text" / "expanded.txt"
    exp.parent.mkdir(parents=True, exist_ok=True)
    kb.write_text(exp, crlf(EXPANDED), "utf-16")
    for rel in ART:
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"TGA" + rel.encode("utf-8"))


tmp = Path(tempfile.mkdtemp(prefix="m2gui_clone_"))
root = tmp / "TestMod"
build(root)
mod = Mod(root)
print(f"=== synthetic mod at {root} ===")

# what everything looked like before, to compare against after the undo
before = {p.relative_to(root).as_posix(): p.read_bytes()
          for p in root.rglob("*") if p.is_file()}

plan = fc.plan(mod, {"source": "sicily", "new": "sicily_two",
                     "label": "Second Sicily", "art": True})
check("the plan is clean", not plan.errors and plan.touched())
written = {e.rel for e in plan.written()}
# the modeldb is the one job this mod has no file for
check(f"every file this mod has is planned ({len(written)})", len(written) == 11)
check("the modeldb is skipped, and says why",
      any(e.rel.endswith(".modeldb") and not e.text and "no such file" in e.skipped
          for e in plan.edits))

srcs = {a.src for a in plan.assets}
check("the art named by convention is taken",
      "ui/units/sicily" in srcs and "ui/faction_symbols/sicily.tga" in srcs)
check("art a LINE points at is left alone (models_strat is not an art root)",
      not any(s.startswith("models_strat/") for s in srcs))
check("a longer slot's art is not stolen (sicily_clone stays sicily_clone's)",
      "ui/faction_symbols/sicily_clone.tga" not in srcs)

res = fc.apply(plan)
tid = res["id"]
print(f"  applied as {tid}: {len(res['files'])} file(s), "
      f"{res['asset_files']} art file(s)")


# ---------------------------------------------------------------------------
# what landed on disk

data = root / "data"
roster = kb.read_text(data / "descr_sm_factions.txt", fc.ENCODING)
check("the roster gained the new slot", "faction sicily_two" in roster)
check("the roster kept the donor", "faction						sicily" in roster)
check("the roster kept CRLF", NL in roster and "\n" not in roster.replace(NL, ""))

edu = kb.read_text(data / "export_descr_unit.txt", fc.ENCODING)
check("the clone joined the donor's ownership lines",
      "ownership        sicily, sicily_two" in edu
      and "ownership        sicily, milan, sicily_two" in edu)
check("a unit the donor never had stays out of it",
      "ownership        milan" + NL in edu)

names = kb.read_text(data / "descr_names.txt", fc.ENCODING)
check("descr_names cloned one section and stopped",
      "faction: sicily_two" in names and names.count("Ottone") == 1
      and names.count("Ruggiero") == 2)

off = kb.read_text(data / "descr_offmap_models.txt", fc.ENCODING)
check("the braced block cloned and the braces still balance",
      "faction sicily_two" in off and off.count("{") == off.count("}"))

edb = kb.read_text(data / "export_descr_buildings.txt", fc.ENCODING)
check("every `requires factions` clause the donor was in gained the clone",
      edb.count("sicily_two") == 3
      and "{ sicily, milan, sicily_two, }" in edb
      and "{ sicily, sicily_two, }" in edb)
check("a clause the donor was not in is untouched",
      "requires factions { milan }" in edb)

acc = kb.read_text(data / "descr_sounds_accents.txt", fc.ENCODING)
check("the clone speaks with the donor's accent",
      "factions milan, sicily, slave, sicily_two" in acc
      and "factions scotland" + NL in acc)

fs = kb.read_text(data / "descr_faction_standing.txt", fc.ENCODING)
check("the standing rules naming the donor name the clone too",
      "{ sicily, milan, sicily_two }" in fs and fs.count("sicily_two") == 1)

anc = kb.read_text(data / "export_descr_ancillaries.txt", fc.ENCODING)
check("an ancillary CONDITION is left alone and reported, never rewritten",
      "sicily_two" not in anc
      and any(r["rel"] == "export_descr_ancillaries.txt" for r in plan.review))

strat = kb.read_text(data / "descr_model_strat.txt", fc.ENCODING)
check("every donor texture line got a twin",
      strat.count("texture				sicily_two,") == 2)

exp = kb.read_text(data / "text" / "expanded.txt", "utf-16")
check("the shown name is the one that was asked for",
      "{SICILY_TWO}	Second Sicily" in exp)
check("the rest of the key family came too, values unchanged",
      "{EMT_SICILY_TWO_SPY}" in exp and "Sicilian Spy" in exp
      and "{EMT_VICTORY_SICILY_TWO}" in exp)
check("milan's keys were not touched", exp.count("{MILAN}") == 1)

check("the unit card folder was copied",
      (data / "ui/units/sicily_two/#sicilian_spearmen.tga").is_file())
check("the symbols were copied and renamed",
      (data / "menu/symbols/fe_buttons_24/symbol24_sicily_two_grey.tga").is_file())
check("the other faction's art was NOT copied",
      not (data / "ui/faction_symbols/sicily_two_clone.tga").exists())

# and the new roster still parses as a roster
reread = Mod(root)
from unittransfer import factions as fa                            # noqa: E402
rf = fa.parse_file(fa.path_for(reread))
check(f"the written roster re-parses with every faction ({len(rf.records)})",
      len(rf.records) == 4 and rf.get("sicily_two") is not None)
# `start`/`end` are where the record sits in the file and `name` is the slot
# itself - everything else has to have come across untouched
drop = ("name", "start", "end")
vals = lambda r: {k: v for k, v in r.as_dict(fa.SHAPE).items() if k not in drop}
check("the clone's every value is the donor's",
      vals(rf.get("sicily_two")) == vals(rf.get("sicily")))


# ---------------------------------------------------------------------------
# and back out again

transfer.undo(tid)
after = {p.relative_to(root).as_posix(): p.read_bytes()
         for p in root.rglob("*") if p.is_file()}

check("undo restored every file byte for byte",
      all(after.get(k) == v for k, v in before.items()))
left = sorted(set(after) - set(before))
check(f"undo left no file behind ({len(left)} extra)" + (f": {left[:3]}" if left else ""),
      not left)
check("the roster is the donor's again",
      "sicily_two" not in kb.read_text(data / "descr_sm_factions.txt", fc.ENCODING))

config.update_log(tid, note="test_factionclone_apply - synthetic mod, discarded")
shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
