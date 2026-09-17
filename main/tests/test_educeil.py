"""The engine's ceilings on export_descr_unit.txt - Phase 39.

Three claims under test:

    the numbers are Medieval II's   the Rome list's 60 men, 244 turns and
                                    shield 31 are NOT checked; M2TW's 100 men,
                                    attack 63, HP 15, three officers, three
                                    mount effects and two formations are
    a ceiling shows, never blocks   every finding is a warning, M2EX drops the
                                    500-unit one, and an edit is never refused
    only what a save introduces     the editor's plan warns about a ceiling the
                                    edit crosses, not one the unit was past

    python -m tests.test_educeil
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod
from unittransfer import edit, educeil, modflags
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


BLOCK = """type             Test Spearmen
dictionary       Test_Spearmen
category         infantry
class            spearmen
soldier          Test_Spearmen, 60, 0, 1
officer          test_captain
mount_effect     horse +2, camel +1
formation        1.2, 1.2, 2.4, 2.4, 6, square, shield_wall
stat_health      1, 0
stat_pri         7, 4, no, 0, 0, melee, melee_blade, piercing, spear, 25, 1
stat_sec         0, 0, no, 0, 0, no, melee_simple, blunt, none, 25, 1
stat_pri_armour  5, 9, 31, metal
stat_sec_armour  0, 0, flesh
stat_cost        250, 400, 100, 50, 60, 400, 4, 110
attributes       sea_faring, hide_forest
"""


def kinds(raw):
    return sorted(f["field"] for f in educeil.unit_findings(raw))


print("1  one unit block")
check("a clean block has nothing", educeil.unit_findings(BLOCK) == [])
check("80 men is fine in Medieval II, whatever Rome's list said",
      kinds(BLOCK.replace(", 60, 0, 1", ", 80, 0, 1")) == [])
check("…and turns to build 250, shield 40, charge 70 are not checked - Rome's numbers",
      kinds(BLOCK.replace("stat_cost        250", "stat_cost        250")
            .replace("5, 9, 31, metal", "5, 9, 40, metal")
            .replace("7, 4, no", "7, 70, no")) == [])
check("101 men and 3 men are past the engine's 4 to 100",
      kinds(BLOCK.replace(", 60, 0, 1", ", 101, 0, 1")) == ["soldier"]
      and kinds(BLOCK.replace(", 60, 0, 1", ", 3, 0, 1")) == ["soldier"])
check("attack 64 on either weapon is past the cap of 63",
      kinds(BLOCK.replace("7, 4, no", "64, 4, no")) == ["stat_pri"]
      and kinds(BLOCK.replace("stat_sec         0, 0", "stat_sec         64, 0")) == ["stat_sec"])
check("either hit points value over 15",
      kinds(BLOCK.replace("stat_health      1, 0", "stat_health      16, 20"))
      == ["stat_health", "stat_health"])
check("a fourth officer",
      kinds(BLOCK.replace("officer          test_captain",
                          "officer a\nofficer b\nofficer c\nofficer d")) == ["officer"])
check("a fourth mount effect",
      kinds(BLOCK.replace("horse +2, camel +1", "horse +2, camel +1, elephant -1, "
                                                "mailed horse +1")) == ["mount_effect"])
check("three formations",
      kinds(BLOCK.replace("square, shield_wall", "square, shield_wall, wedge")) == ["formation"])
check("two formations that are both base shapes - Reforged writes square and horde",
      kinds(BLOCK.replace("square, shield_wall", "square, horde")) == ["formation"])
check("one formation is fine", kinds(BLOCK.replace("square, shield_wall", "square")) == [])
fs = educeil.unit_findings(BLOCK.replace("stat_health      1, 0", "stat_health      30, 0"))
check("every finding is a warning and names a Medieval II document",
      fs and all(not f["fatal"] and "M2TW" in f["source"] for f in fs))


class U:
    def __init__(self, eop=False):
        self.is_eop = eop
        self.ownership = []


print("\n2  the roster")
check("500 units is at the ceiling, not past it",
      educeil.mod_findings([U() for _ in range(500)]) == [])
over = educeil.mod_findings([U() for _ in range(501)])
check("501 is past it", [f["kind"] for f in over] == ["too-many-units"])
check("an M2TWEOP unit is not in the file and is not counted",
      educeil.mod_findings([U() for _ in range(500)] + [U(eop=True)]) == [])
check("and it is a finding M2EX lifts", "too-many-units" in modflags.CAP_FINDINGS)


print("\n3  every installed mod")
for root in _realmod.installed():
    mod = Mod(root)
    r = educeil.report(mod)
    check(f"{root.name}: {r['count']} finding(s) over {len(r['per_unit'])} of "
          f"{r['units']} units, every one a warning",
          all(not f["fatal"] for v in r["per_unit"].values() for f in v))
    if r["m2ex"] and r["units"] > educeil.MAX_UNITS:
        check(f"{root.name}: marked M2EX, so its {r['units']} units are lifted, not shown",
              r["roster"] == [] and r["lifted"] == 1)

print("\n4  the unit editor")
src = _realmod.pick("Third_Age_Reforged")
mod = Mod(src)
units = mod.edu.units
clean = next((u for u in units if not educeil.unit_findings(u.raw, u.type)
              and "stat_health" in u.raw), None)
if clean is None:
    print("  SKIPPED - no clean unit")
else:
    d = edit.unit_detail(mod, clean.type)
    check("the editor's unit detail carries its ceilings", d["ceilings"] == []
          and "roster_ceilings" in d)
    p = edit.plan_edit(mod, edit.request_from_dict(
        {"mod": src.name, "unit": clean.type, "field_overrides": {"stat_health": "20, 0"}}))
    check("an edit to HP 20 plans, with one ceiling warning, and is not refused",
          not p.errors and sum("engine ceiling" in w for w in p.warnings) == 1)
    p = edit.plan_edit(mod, edit.request_from_dict(
        {"mod": src.name, "unit": clean.type, "field_overrides": {"stat_health": "2, 0"}}))
    check("an edit inside the range says nothing about ceilings",
          not any("engine ceiling" in w for w in p.warnings))
past = next((u for u in units if educeil.unit_findings(u.raw, u.type)), None)
if past is not None:
    d = edit.unit_detail(mod, past.type)
    check(f"a unit already past one ({past.type}) shows it in the detail",
          bool(d["ceilings"]))
    p = edit.plan_edit(mod, edit.request_from_dict(
        {"mod": src.name, "unit": past.type, "field_overrides": {"dictionary": past.dictionary}}))
    check("…and an unrelated save does not warn about it again",
          not any("engine ceiling" in w for w in p.warnings))

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
