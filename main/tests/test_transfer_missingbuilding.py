"""96f: Unit Transfer names the buildings that train a unit and the destination lacks.

Run:  python -m tests.test_transfer_missingbuilding

The source trains ``Khans Guard`` at ``khan_stables`` (a line the destination
has not at all) and at ``barracks / militia_barracks`` (a line it has, with that
level). What has to hold:

* the pool at the shared level is planned as before;
* ``khan_stables`` is named as missing, once, for the building import to bring;
* a destination with every line names none.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def line(name, level, pools):
    caps = "".join(f'                recruit_pool "{u}"  1   0.5   2  0  requires factions {{ mongols, }}\n'
                   for u in pools)
    return (f"building {name}\n{{\n    levels {level}\n    {{\n"
            f"        {level} city requires factions {{ all, }}\n        {{\n"
            f"            capability\n            {{\n{caps}            }}\n"
            "            construction 2\n            cost 400\n            upgrades\n            {\n            }\n"
            "        }\n    }\n}\n")


UNIT = ("type             Khans Guard\ndictionary       Khans_Guard\ncategory         cavalry\n"
        "class            heavy\nownership        mongols\n")


def mod_at(root: Path, edb: str) -> Mod:
    data = root / "data"
    data.mkdir(parents=True)
    (data / "export_descr_buildings.txt").write_text("hidden_resources river\n\n" + edb, encoding="latin-1")
    (data / "export_descr_unit.txt").write_text(UNIT, encoding="latin-1")
    return Mod(root)


tmp = Path(_tmp.mkdtemp(prefix="ut_missbld_"))
src = mod_at(tmp / "Src", line("khan_stables", "khan_tent", ["Khans Guard"])
             + line("khan_stables2", "khan_yurt", ["Khans Guard"]).replace("khan_stables2", "khan_stables_b")
             + line("barracks", "militia_barracks", ["Khans Guard"]))
dst = mod_at(tmp / "Dst", line("barracks", "militia_barracks", ["Town Militia"]))
full = mod_at(tmp / "Full", line("barracks", "militia_barracks", [])
              + line("khan_stables", "khan_tent", []) + line("khan_stables_b", "khan_yurt", []))


def planned(dest):
    p = transfer.TransferPlan(unit_type="Khans Guard", dictionary="Khans_Guard", source=src,
                              dest=dest, options=transfer.TransferOptions())
    p.resolved_type = "Khans Guard"
    transfer._plan_recruitment(p, src, dest, UNIT)
    return p


print("\n1) a destination missing two of the three lines")
p = planned(dst)
check("the shared level's pool is planned",
      [(a, b) for a, b, _ in p.recruit_pools] == [("barracks", "militia_barracks")])
check("both missing lines are named, each once",
      p.recruit_missing_lines == ["khan_stables", "khan_stables_b"])

print("\n2) a destination with every line")
q = planned(full)
check("names none", q.recruit_missing_lines == [])
check("  and plans all three pools", len(q.recruit_pools) == 3)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
