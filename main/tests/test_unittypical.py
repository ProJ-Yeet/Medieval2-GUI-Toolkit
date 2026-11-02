"""96f: the usual unit of a kind, to start a new unit from.

    python -m tests.test_unittypical

numbers() reads a unit's main numbers from its own EDU lines, melee from
stat_sec when the unit shoots; on Divide and Conquer each kind has units,
every middle lies between its lowest and highest, general's bodyguards are
left out, and the unit named is of the kind.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _realmod  # noqa: E402
from unittransfer import unittypical as T  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


class U:
    raw = ("soldier  Archer, 60, 0, 1\nstat_pri  5, 2, arrow, 120, 30, missile, missile_mechanical, piercing, none, 25, 1\n"
           "stat_sec  4, 1, no, 0, 0, melee, melee_blade, piercing, knife, 25, 1\n"
           "stat_pri_armour  3, 4, 0, leather\nstat_mental  9, normal, trained\nstat_cost  1, 400, 150, 30, 20, 400, 4, 100\n")


print("\n1) numbers")
n = T.numbers(U)
check(f"a shooter's melee comes from stat_sec ({n})", n["attack"] == 4 and n["charge"] == 1 and n["missile"] == 5)
check("men, armour, morale, cost, upkeep, turns", (n["men"], n["armour"], n["defence"], n["morale"], n["cost"],
      n["upkeep"], n["turns"]) == (60, 3, 4, 9, 400, 150, 1))

DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
if not (DAC / "data/export_descr_unit.txt").is_file():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    print("\n2) on Divide and Conquer")
    mod = Mod(DAC)
    for kind in T.KINDS:
        r = T.typical(mod, kind)
        u = mod.edu.by_type().get(r["type"])
        cat, classes = T.KINDS[kind]
        check(f"{kind}: {r['count']} units, {r['type']} is of the kind",
              r["count"] > 10 and u is not None and u.category == cat and u.class_type in classes)
        check(f"{kind}: every middle between its lowest and highest",
              all(s["low"] <= s["middle"] <= s["high"] for s in r["stats"]))
    every = [u for k in T.KINDS for u in T.of_kind(mod, k)]
    check("no general's bodyguard", not any("general_unit" in [a.lower() for a in u.attributes] for u in every))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
