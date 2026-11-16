"""Mylae's standings rule, as :mod:`unittransfer.standcalc`.

    python -m tests.test_standcalc
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import campstrat, standcalc

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


META = {"england": ("catholic", "northern_european"),
        "france": ("catholic", "northern_european"),
        "egypt": ("islam", "middle_eastern"),
        "milan": ("catholic", "southern_european")}
F = ["england", "france", "egypt", "milan", "slave"]
REL = {frozenset(("england", "france")): {"allied_to"},
       frozenset(("england", "egypt")): {"at_war_with"},
       frozenset(("milan", "france")): {"protectorate_of"}}

print("\n1) his numbers")
got = standcalc.compute(F, META, REL, {})
check(f"same religion and culture, allied: 0.15 + 0.10 + 0.20 = 0.45, got {got['england'].get('france')}",
      got["england"]["france"] == 0.45 and got["france"]["england"] == 0.45)
check(f"different both, at war: -0.15 - 0.10 - 0.50 = -0.75, got {got['england'].get('egypt')}",
      got["england"]["egypt"] == -0.75)
check(f"same religion, different culture, nothing stated: 0.05, got {got['england'].get('milan')}",
      got["england"]["milan"] == 0.05)
check("a protectorate counts as allied (the game starts the two allied)",
      got["milan"]["france"] == round(0.15 - 0.10 + 0.20, 2))
check("the rebels are left out on both sides",
      "slave" not in got and all("slave" not in c for c in got.values()))

print("\n2) what is kept, what is skipped")
got = standcalc.compute(F, {}, {}, {"england": {"slave": -1.0, "france": 0.3}})
check("no religion or culture known and nothing stated: no new cell is written",
      got["france"] == {} and "milan" not in got["england"])
check("a cell that already was, recalculated to 0, is written as 0",
      got["england"]["france"] == 0.0)
check("a cell toward the rebels is kept as it was",
      got["england"]["slave"] == -1.0)

print("\n3) add, the clamp and the weights")
got = standcalc.compute(F, META, REL, {"england": {"france": 0.8}}, mode="add")
check(f"add puts the points on top and stops at 1, got {got['england']['france']}",
      got["england"]["france"] == 1.0)
got = standcalc.compute(F, META, REL, {}, weights={"war": -90})
check(f"a weight of the user's own: at war -0.90 instead, got {got['england']['egypt']}",
      got["england"]["egypt"] == -1.0)
got = standcalc.compute(F, META, REL, {}, weights={"war": -30})
check(f"...and -0.30 gives -0.55, got {got['england']['egypt']}", got["england"]["egypt"] == -0.55)

print("\n4) relationships read off descr_strat.txt")
sf = campstrat.parse_strat("faction england, x\nfaction france, x\nfaction milan, x\n"
                           "faction_relationships england, allied_to france\n"
                           "faction_relationships milan, protectorate_of france\n")
rel = standcalc.relations(sf)
check("allied_to and protectorate_of are both read, as unordered pairs",
      rel.get(frozenset(("france", "england"))) == {"allied_to"}
      and rel.get(frozenset(("france", "milan"))) == {"protectorate_of"})

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
