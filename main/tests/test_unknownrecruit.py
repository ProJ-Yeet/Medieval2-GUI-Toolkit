"""Health's check for a recruit pool or mercenary pool naming a unit the
mod's export_descr_unit.txt has not got.

Run:  python -m tests.test_unknownrecruit

Kirsi's Bigger Map recruited "Greek Firethrower" twice in its buildings and
twice in its mercenary pools, after the unit had gone from its unit file.
What has to hold:

* both building lines and both mercenary lines are found, each at its line;
* a unit the file has is not, whatever its case;
* the rule is one Health runs (it is in crashrules' RULES).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import crashrules                                 # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


EDU = "type             Spearmen\ndictionary       Spearmen\ncategory         infantry\n\n"
EDB = ("building barracks\n{\n    levels town_watch\n    {\n        town_watch city requires factions { england, }\n"
       "        {\n            capability\n            {\n"
       '                recruit_pool "spearmen"  1  0.7  6  0  requires factions { england, }\n'
       '                recruit_pool "Greek Firethrower"  1  0.7  6  0  requires factions { byzantium, }\n'
       "            }\n        }\n    }\n}\n")
MERC = ("pool Thrace\n\tregions Constantinople_Province\n"
        "\tunit Spearmen,\t\texp 0 cost 300 replenish 0.1 - 0.2 max 2 initial 1\n"
        "\tunit Greek Firethrower\t\texp 0 cost 1280 replenish 0.02 - 0.06 max 2 initial 1 religions { orthodox }\n"
        "end\n")

tmp = Path(_tmp.mkdtemp(prefix="ut_unknownrecruit_"))
data = tmp / "M" / "data"
(data / "world" / "maps" / "base").mkdir(parents=True)
(data / "export_descr_unit.txt").write_text(EDU, encoding="latin-1")
(data / "export_descr_buildings.txt").write_text(EDB, encoding="latin-1")
(data / "world" / "maps" / "base" / "descr_mercenaries.txt").write_text(MERC, encoding="latin-1")
mod = Mod(tmp / "M")

found = crashrules._unknown_recruits(mod)
where = sorted((f.file, f.line) for f in found)
check("the two lines naming Greek Firethrower are found, and nothing else",
      len(found) == 2 and all("Greek Firethrower" in f.message for f in found))
check("  the building line, at its line", ("export_descr_buildings.txt", 10) in where)
check("  the mercenary line, at its line", ("world/maps/base/descr_mercenaries.txt", 4) in where)
check("  both fatal", all(f.severity == "fatal" for f in found))
check("the rule is one Health runs", any(r.code == "unit.unknown_recruit" for r in crashrules.RULES))

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
