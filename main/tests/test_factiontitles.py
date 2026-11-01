"""96f: a faction's leader and heir titles, edited on the faction itself.

Run:  python -m tests.test_factiontitles

One small mod: ``england`` with its name and leader title in ``expanded.txt``,
no heir title and no strengths yet. What has to hold:

* **the faction's detail offers all five keys**, each saying whether the text
  has it, and carries the ones it has;
* **a changed title is rewritten, a missing one added**, the strengths written
  across lines and read back whole;
* **an emptied title is left alone**, and a key of another faction is ignored;
* **one Undo** puts ``expanded.txt`` back byte for byte.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config                                    # noqa: E402
from unittransfer import factions as fac                           # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
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
RECORD = """faction						england
culture						northern_european
religion					catholic
symbol						models_strat/symbol_england.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				red 200, green 10, blue 10
secondary_colour			red 130, green 20, blue 30
loading_logo				loading_screen/symbols/symbol128_england.tga
standard_index				6
logo_index					FACTION_LOGO_ENGLAND
small_logo_index			SMALL_FACTION_LOGO_ENGLAND
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes
"""
TEXT = """{ENGLAND}England
{EMT_ENGLAND_FACTION_LEADER_TITLE}King %S
{EMT_FRANCE_FACTION_LEADER_TITLE}Roi %S
"""

tmp = Path(_tmp.mkdtemp(prefix="ut_titles_"))
data = tmp / "Here" / "data"
(data / "text").mkdir(parents=True)
kb.write_text(data / "descr_sm_factions.txt", NL.join(RECORD.split("\n")), fac.ENCODING)
kb.write_text(data / "text" / "expanded.txt", NL.join(TEXT.split("\n")), "utf-16")
mod = Mod(tmp / "Here")
before = (data / "text" / "expanded.txt").read_bytes()

print("\n1) what the form is offered")
d = fac.detail(mod, "england")
rows = {t["key"]: t for t in d["titles"]}
check("five keys, the clone's", set(rows) == {"leader", "heir", "former", "strength", "weakness"})
check("the leader's is had and carried",
      rows["leader"]["has"] and d["loc"]["EMT_ENGLAND_FACTION_LEADER_TITLE"] == "King %S")
check("the heir's is not had", rows["heir"]["tag"] == "EMT_ENGLAND_FACTION_HEIR_TITLE" and not rows["heir"]["has"])

print("\n2) a save")
body = {"mod": "Here", "faction": "england", "action": "edit", "edits": {}, "loc": {
    "EMT_ENGLAND_FACTION_LEADER_TITLE": "Duke %S",
    "EMT_ENGLAND_FACTION_HEIR_TITLE": "Prince %S",
    "EMT_ENGLAND_FORMER_FACTION_LEADER_TITLE": "",
    "ENGLAND_STRENGTH": " Longbows\n Strong castles",
    "EMT_FRANCE_FACTION_LEADER_TITLE": "Empereur %S"}}
p = fac.plan(mod, body)
check("the plan is clean and touches only the text",
      not p.errors and not p.text and p.touched())
check("leader changed, heir and strength added",
      p.loc_writes == {"EMT_ENGLAND_FACTION_LEADER_TITLE": "Duke %S",
                       "EMT_ENGLAND_FACTION_HEIR_TITLE": "Prince %S",
                       "ENGLAND_STRENGTH": " Longbows\n Strong castles"})
check("  the two new ones counted new",
      sorted(p.loc_new) == ["EMT_ENGLAND_FACTION_HEIR_TITLE", "ENGLAND_STRENGTH"])
res = fac.apply(p)
now = fac.loc(Mod(tmp / "Here"))
check("read back: the new leader title", now.get("EMT_ENGLAND_FACTION_LEADER_TITLE") == "Duke %S")
check("read back: the strengths across two lines, whole",
      now.get("ENGLAND_STRENGTH") == " Longbows\n Strong castles")
check("another faction's title untouched", now.get("EMT_FRANCE_FACTION_LEADER_TITLE") == "Roi %S")

print("\n3) undo")
transfer.undo(res["record"]["id"])
check("expanded.txt back byte for byte", (data / "text" / "expanded.txt").read_bytes() == before)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
