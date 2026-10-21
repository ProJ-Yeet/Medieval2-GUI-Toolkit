"""96f: a whole faction brought from another mod.

Run:  python -m tests.test_factionbring

Two small mods in a temp folder, shaped like real ones and CRLF like the game's
files: ``Here`` (sicily, milan) and ``Other`` (aragon, milan). ``aragon`` is
brought into ``Here`` and made on ``sicily``, the faction of the same culture.
What has to hold:

* **the frame is the same culture's**, and the clone underneath is a whole one;
* **aragon's own laid over**: its colours and religion, its symbol (the file
  brought, since ``Here`` lacks it), its texts, its name lists and their texts,
  its spy's campaign-map texture, its art in place of sicily's;
* **its units sorted**: the unit both mods have line for line is shared, the
  one only ``Other`` has is left to Unit Transfer, and sicily's own units are
  out of the new faction's ownership;
* **one Undo takes the faction back out**, every file byte for byte.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config                                    # noqa: E402
from unittransfer import factionbring as fb                        # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer import stringsbin                                # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


NL = chr(13) + chr(10)


def crlf(text: str) -> str:
    return NL.join(text.strip("\n").split("\n")) + NL


def record(slot, culture, religion, colour, symbol):
    return f"""
faction						{slot}
culture						{culture}
religion					{religion}
symbol						models_strat/symbol_{symbol}.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				{colour}
secondary_colour			red 130, green 20, blue 30
loading_logo				loading_screen/symbols/symbol128_{slot}.tga
standard_index				6
logo_index					FACTION_LOGO_{slot.upper()}
small_logo_index			SMALL_FACTION_LOGO_{slot.upper()}
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes
"""


SHARED = """
type             Shared Militia
dictionary       Shared_Militia
category         infantry
class            light
soldier          militia, 40, 0, 1
ownership        {own}
"""


def unit(name, own, soldier="spear"):
    return f"""
type             {name}
dictionary       {name.replace(' ', '_')}
category         infantry
class            light
soldier          {soldier}, 40, 0, 1
ownership        {own}
"""


HERE = {
    "descr_sm_factions.txt": record("sicily", "southern_european", "catholic",
                                    "red 245, green 245, blue 245", "sicily")
    + record("milan", "southern_european", "catholic", "red 10, green 90, blue 40", "milan"),
    "descr_religions.txt": "religions\n{\n    catholic\n    orthodox\n}\n",
    "export_descr_unit.txt": unit("Sicilian Spearmen", "sicily")
    + SHARED.format(own="sicily, milan") + unit("Milanese Only", "milan"),
    "descr_character.txt": """
type					spy
faction			sicily, milan
strat_model		sm_spy
""",
    "descr_model_strat.txt": """
type				sm_spy
skeleton			strat_spy
texture				sicily, models_strat/textures/spy_sicily.tga
texture				milan, models_strat/textures/spy_milan.tga
model_flexi_m		data/models_strat/spy.CAS, max
""",
    "descr_names.txt": """
faction: sicily

	characters
		Ruggiero
		Tancredi

faction: milan

	characters
		Ottone
""",
}
HERE_TEXT = """
{SICILY}	Kingdom of Sicily
{EMT_SICILY_SPY}	Sicilian Spy
{MILAN}	Duchy of Milan
"""
HERE_NAMES = """
{Ruggiero}Ruggiero
{Tancredi}Tancredi
{Ottone}Ottone
"""
HERE_ART = ["ui/faction_symbols/sicily.tga", "ui/units/sicily/#sicilian_spearmen.tga",
            "menu/symbols/fe_buttons_24/symbol24_sicily.tga",
            "models_strat/textures/spy_sicily.tga", "models_strat/symbol_sicily.CAS"]

OTHER = {
    "descr_sm_factions.txt": record("aragon", "southern_european", "orthodox",
                                    "red 200, green 180, blue 0", "aragon")
    + record("milan", "southern_european", "catholic", "red 10, green 90, blue 40", "milan"),
    "export_descr_unit.txt": unit("Almogavars", "aragon", "almogavar")
    + SHARED.format(own="aragon, milan") + unit("Milanese Only", "milan"),
    "descr_model_strat.txt": """
type				sm_spy
skeleton			strat_spy
texture				aragon, models_strat/textures/spy_aragon.tga
model_flexi_m		data/models_strat/spy.CAS, max
""",
    "descr_names.txt": """
faction: aragon

	characters
		Jaume
		Pere

	women
		Violant

faction: milan

	characters
		Ottone
""",
}
OTHER_TEXT = """
{ARAGON}	Crown of Aragon
{EMT_ARAGON_SPY}	Aragonese Spy
{MILAN}	Duchy of Milan
"""
OTHER_NAMES = """
{Jaume}Jaume
{Pere}Pere
{Violant}Violant
{Ottone}Ottone
"""
OTHER_ART = ["ui/faction_symbols/aragon.tga", "ui/units/aragon/#almogavars.tga",
             "models_strat/textures/spy_aragon.tga", "models_strat/symbol_aragon.CAS"]


def build(root: Path, files, text, names, art) -> Mod:
    data = root / "data"
    for rel, body in files.items():
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(path, crlf(body), fb.fac.ENCODING)
    for rel, body in (("text/expanded.txt", text), ("text/names.txt", names)):
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(path, crlf(body), "utf-16")
    for rel in art:
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"ART " + rel.encode("utf-8"))
    return Mod(root)


tmp = Path(_tmp.mkdtemp(prefix="m2gui_bring_"))
here = build(tmp / "Here", HERE, HERE_TEXT, HERE_NAMES, HERE_ART)
other = build(tmp / "Other", OTHER, OTHER_TEXT, OTHER_NAMES, OTHER_ART)
print(f"=== {tmp} ===")
before = {p.relative_to(here.root).as_posix(): p.read_bytes()
          for p in Path(here.root).rglob("*") if p.is_file()}


# ---------------------------------------------------------------------------
# what the other mod offers

rows = {r["slot"]: r for r in fb.factions_of(other)}
check("the other mod's factions are listed with their shown names",
      rows.get("aragon", {}).get("label") == "Crown of Aragon")
check("the frame is the same culture's, never the rebels",
      fb.frame_for(here, "southern_european") == "sicily")
check("own_units reads ownership by faction", fb.own_units(other, "aragon")
      == ["Almogavars", "Shared Militia"])


# ---------------------------------------------------------------------------
# the plan

p = fb.plan(here, other, {"faction": "aragon", "new": "aragon"})
pl = p.payload()
check(f"the plan is clean ({pl['errors']})", pl["ok"] and not pl["errors"])
check("made on sicily", p.frame == "sicily")
check("Shared Militia is shared, alike line for line", p.shared == ["Shared Militia"])
check("Almogavars is left to Unit Transfer", p.bring == ["Almogavars"])

ed = {e.rel: e for e in p.clone.written()}
rf = fb.fac.parse_text(kb.to_newline(ed["descr_sm_factions.txt"].text, "\n"))
rec = rf.get("aragon")
check("its colour is aragon's", rec.get("primary_colour") == "red 200, green 180, blue 0")
check("its religion is aragon's (this mod has orthodox)", rec.get("religion") == "orthodox")
check("its symbol line names aragon's symbol", rec.get("symbol") == "models_strat/symbol_aragon.CAS")
check("the roster keeps CRLF", NL in ed["descr_sm_factions.txt"].text
      and "\r\r" not in ed["descr_sm_factions.txt"].text)
check("the symbol file is brought from the other mod",
      any(a.dst == "models_strat/symbol_aragon.CAS" and a.root for a in p.clone.assets))

exp = dict(stringsbin.from_txt(ed["text/expanded.txt"].text))
check("the shown name is aragon's", exp.get("ARAGON") == "Crown of Aragon")
check("its EMT text is aragon's, not sicily's", exp.get("EMT_ARAGON_SPY") == "Aragonese Spy")

names = kb.to_newline(ed["descr_names.txt"].text, "\n")
sec = names[names.index("faction: aragon"):names.index("faction: milan")]
check("its name lists are aragon's", "Jaume" in sec and "Violant" in sec and "Ruggiero" not in sec)
check("sicily's own names are untouched",
      "Ruggiero" in names[:names.index("faction: aragon")])
nt = dict(stringsbin.from_txt(ed["text/names.txt"].text))
check("the names' texts this mod lacked are added", nt.get("Jaume") == "Jaume"
      and nt.get("Violant") == "Violant" and nt.get("Ruggiero") == "Ruggiero")

ms = kb.to_newline(ed["descr_model_strat.txt"].text, "\n")
check("the spy wears aragon's texture",
      "texture				aragon, models_strat/textures/spy_aragon.tga" in ms)
check("the texture file is brought",
      any(a.dst == "models_strat/textures/spy_aragon.tga" for a in p.clone.assets))

edu = kb.to_newline(ed["export_descr_unit.txt"].text, "\n")
blocks = {b.split("\n")[0].split(None, 1)[1].strip(): b for b in edu.split("type ")[1:]
          for b in ["type " + b] if b}
own = {k: [x.strip() for x in b.split("ownership", 1)[1].split("\n")[0].split(",")]
       for k, b in blocks.items()}
check("the shared unit is aragon's too", "aragon" in own["Shared Militia"])
check("sicily's own unit is not aragon's", "aragon" not in own["Sicilian Spearmen"])

dsts = {a.dst: a for a in p.clone.assets}
check("aragon's faction symbol replaces sicily's copy",
      dsts.get("ui/faction_symbols/aragon.tga") is not None
      and dsts["ui/faction_symbols/aragon.tga"].root)
check("aragon's unit cards replace sicily's folder",
      dsts.get("ui/units/aragon") is not None and dsts["ui/units/aragon"].root)
check("a place aragon has nothing for keeps the frame's picture",
      "menu/symbols/fe_buttons_24/symbol24_aragon.tga" in dsts
      and not dsts["menu/symbols/fe_buttons_24/symbol24_aragon.tga"].root)
check("the units left to transfer are said", any("Almogavars" in n for n in pl["notes"]))

p2 = fb.plan(here, other, {"faction": "nobody", "new": "x"})
check("a faction the other mod lacks is refused", p2.errors and not p2.payload()["ok"])
p3 = fb.plan(here, other, {"faction": "aragon", "new": "aragon", "frame_units": True})
e3 = kb.to_newline({e.rel: e for e in p3.clone.written()}["export_descr_unit.txt"].text, "\n")
check("frame_units keeps sicily's units too",
      "sicily, aragon" in e3.split("Sicilian Spearmen")[1].split("type")[0])


# ---------------------------------------------------------------------------
# the write, then one Undo

res = fb.apply(p, lambda: Mod(here.root))
data = Path(here.root) / "data"
check("the faction is written", res.get("faction") == "aragon" and res.get("id"))
check("the brought symbol landed", (data / "models_strat/symbol_aragon.CAS").read_bytes()
      == b"ART models_strat/symbol_aragon.CAS")
check("aragon's unit card landed",
      (data / "ui/units/aragon/#almogavars.tga").is_file())
check("a unit that cannot come is reported, not fatal",
      isinstance(res.get("units_failed"), list)
      and len(res.get("units") or []) + len(res["units_failed"]) == 1)
for u in res.get("units") or []:
    transfer.undo(u["id"])
undo = transfer.undo(res["id"])
after = {p_.relative_to(here.root).as_posix(): p_.read_bytes()
         for p_ in Path(here.root).rglob("*") if p_.is_file()}
check("undo puts every file back byte for byte",
      all(after.get(k) == v for k, v in before.items()))
check("undo removes every file the bring created",
      not [k for k in after if k not in before and not k.endswith(".strings.bin")])

print()
print(f"{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
