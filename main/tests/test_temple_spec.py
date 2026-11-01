"""96f: a religion's temples from nothing.

    python -m tests.test_temple_spec

``buildings.temple_spec`` builds a new-tree spec from the mod's own temple
lines, and ``plan_new_tree`` writes it. On Divide and Conquer: three city
levels, the usual costs, turns and town sizes, a growing ``religion_level``,
the ``religion`` line naming the new faith, built by the factions picked, and a
plan with no errors. A mod with no temple lines gets three steps of faith.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _realmod  # noqa: E402
from unittransfer import buildings as B  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n1) the text a spec writes")
txt = B.new_tree_text({"name": "t", "religion": "r", "levels": [
    {"name": "a", "settlement": "city", "capabilities": ["religion_level bonus 1"]}]})
check("the religion line and the capability inside its block",
      "\treligion r\n" in txt and "capability\n\t\t\t{\n\t\t\t\treligion_level bonus 1\n\t\t\t}" in txt)


class NoTemples:
    class edb:
        buildings = []


print("\n2) a mod with no temple lines")
s = B.temple_spec(NoTemples, "valar", [])
check("three levels, each a step of faith",
      [lv["capabilities"] for lv in s["levels"]] == [["religion_level bonus 1"], ["religion_level bonus 2"],
                                                     ["religion_level bonus 3"]])
check("built by everyone when no faction is picked", s["requires"] == "")

DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
if not (DAC / "data" / "export_descr_buildings.txt").is_file():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    print("\n3) on Divide and Conquer")
    mod = Mod(DAC)
    s = B.temple_spec(mod, "valar", ["sicily", "turks"])
    lv = s["levels"]
    check(f"the usual number of levels ({len(lv)}), from {s['from_temples']} temple lines", len(lv) == 3)
    check("costs and turns grow along the chain",
          int(lv[0]["cost"]) < int(lv[1]["cost"]) < int(lv[2]["cost"])
          and int(lv[0]["construction"]) < int(lv[2]["construction"]))
    check("the usual town sizes", [x["settlement_min"] for x in lv] == ["village", "town", "large_town"])
    check("faith grows: 1, 3, 5", [x["capabilities"][0] for x in lv]
          == ["religion_level bonus 1", "religion_level bonus 3", "religion_level bonus 5"])
    check("built by the factions picked", s["requires"] == "factions { sicily, turks, }")
    p = B.plan_new_tree(mod, s)
    check(f"the plan is clean ({p.errors})", not p.errors)
    block = B.new_tree_text(B.new_tree_spec(mod, s))
    check("it names the new faith", "\treligion valar\n" in block and "building temple_valar" in block)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
