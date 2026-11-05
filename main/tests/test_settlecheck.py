"""Every settlement of a campaign checked at once (after Mylae's validation tab).

The settlement form already says what is wrong with the one settlement it has
open (``stratedit.check_settlement``). Nothing said it for all of them, so a
building that is fatal in one province was found only by opening that province.
This sweeps the whole ``descr_strat.txt`` with the same rules, and adds one
Mylae's editor has: whether a settlement's population fits its level, by the
thresholds in ``descr_settlement_mechanics.xml``.

What each part is here to catch:

  * **the sweep says what the form says**, settlement by settlement, fatal first,
    and a sound settlement is left out of the list.
  * **population against level** is a note, never a warning: a town past its
    upgrade population can grow on the first turn, one under its level's base
    starts small. Neither stops the game. A castle reads the castle names
    (vanilla spells the first one ``moot_and_bailey``).
  * **a mod with no descr_settlement_mechanics.xml** of its own is not checked
    for population at all.

    python -m tests.test_settlecheck
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import campstrat, stratedit

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"
STRAT = CR.join([
    "campaign imperial_campaign",
    "playable", "\tengland", "end", "unlockable", "end", "nonplayable", "end", "",
    "faction\tengland, balanced smith",
    "\tdenari\t10000",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion London_Province",
    "\t\tyear_founded 0", "\t\tpopulation 1600", "\t\tplan_set default_set",
    "\t\tfaction_creator england",
    "\t\tbuilding", "\t\t{", "\t\t\ttype market corn_exchange", "\t\t}",
    "\t}", "",
    "\tsettlement", "\t{", "\t\tlevel town", "\t\tregion York_Province",
    "\t\tyear_founded 0", "\t\tpopulation 7000", "\t\tplan_set default_set",
    "\t\tfaction_creator england", "\t}", "",
    "\tsettlement castle", "\t{", "\t\tlevel town", "\t\tregion Nottingham_Province",
    "\t\tyear_founded 0", "\t\tpopulation 200", "\t\tplan_set default_set",
    "\t\tfaction_creator england", "\t}", "",
    "\tsettlement", "\t{", "\t\tlevel hamlet", "\t\tregion Dublin_Province",
    "\t\tyear_founded 0", "\t\tpopulation 800", "\t\tplan_set default_set",
    "\t\tfaction_creator england", "\t}", "",
]) + CR

MECH = CR.join([
    "<settlement_mechanics>",
    "\t<population_levels>",
    '\t\t<level name="village" base="400" upgrade="800" min="400" max="2000"/>',
    '\t\t<level name="town" base="800" upgrade="2000" min="400" max="6000"/>',
    '\t\t<level name="large_town" base="2000" upgrade="6000" min="400" max="12000"/>',
    '\t\t<level name="moot_and_bailey" base="400" upgrade="1000" min="400" max="2000"/>',
    '\t\t<level name="wooden_castle" base="1000" upgrade="3000" min="400" max="6000"/>',
    "\t</population_levels>",
    "</settlement_mechanics>",
]) + CR


class _Blk:
    def __init__(self, name, settlement="", **scalars):
        self.name, self.settlement, self.scalars = name, settlement, scalars


class _Line:
    def __init__(self, name, blocks):
        self.name, self.blocks = name, blocks


class _Edb:
    buildings = [_Line("market", [_Blk("corn_exchange", "city", settlement_min="large_town")])]


root = Path(_tmp.mkdtemp(prefix="ut_settle_"))


class _Mod:
    edb = _Edb()
    data = root


class _Facts:
    mod, skipped, campaign, strat_rel = _Mod(), [], "imperial_campaign", "descr_strat.txt"
    strat = campstrat.parse_strat(STRAT)


print("1) the sweep says what the form says")
r = stratedit.check_all_settlements(_Facts())
by = {s["region"]: s for s in r["settlements"]}
check("a fatal level is said", any(f["code"] == "settlement.level" and f["fatal"]
                                   for f in by.get("Dublin_Province", {}).get("findings", [])))
check("a building too big for its town is said", any(
    f["code"] == "building.min" for f in by.get("London_Province", {}).get("findings", [])))
check("fatal ones first", r["settlements"][0]["region"] == "Dublin_Province")
check("a sound settlement is left out of the list", "York_Province" not in by)
check("each carries its owner", by["London_Province"]["owner"] == "england")
check("the counts add up", r["counts"]["fatal"] == 1 and r["counts"]["settlements"] == 4)
check("no mechanics file of its own, no population check",
      not any(f["code"].startswith("population.") for s in r["settlements"] for f in s["findings"]))

print("\n2) population against level")
(root / "descr_settlement_mechanics.xml").write_text(MECH, encoding="latin-1")
r = stratedit.check_all_settlements(_Facts())
by = {s["region"]: s for s in r["settlements"]}
codes = lambda reg: [f["code"] for f in by.get(reg, {}).get("findings", [])]
check("a town past its upgrade population is noted", "population.upgrade" in codes("York_Province"))
check("a castle under its level's base is noted, by the castle's names",
      "population.base" in codes("Nottingham_Province"))
check("they are notes, never warnings or fatal",
      all(f.get("severity") == "note" and not f["fatal"]
          for s in r["settlements"] for f in s["findings"] if f["code"].startswith("population.")))
check("a town inside its band says nothing about population",
      not any(c.startswith("population.") for c in codes("London_Province")))

shutil.rmtree(root, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
