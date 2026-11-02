"""96f: every picture in a mod, by kind.

    python -m tests.test_artbrowse

kind_of sorts a path by the folder the game reads it from; the models' and
ground folders are never walked; on Divide and Conquer the kinds are counted,
a page comes back at the size asked, and the filter narrows by path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _realmod  # noqa: E402
from unittransfer import artbrowse as A  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n1) kind_of")
for rel, kind in (("ui/units/milan/#knights.tga", "unit_cards"),
                  ("ui/unit_info/milan/knights_info.tga", "unit_info"),
                  ("ui/northern_european/buildings/#northern_european_church.tga", "buildings"),
                  ("ui/pips/pip_evil.tga", "pips"),
                  ("ui/gondor/interface/stratpage_02.tga", "interface_pages"),
                  ("world/maps/campaign/imperial_campaign/map_FE.tga", "campaign"),
                  ("menu/_m2_background.tga", "menu"),
                  ("ui/shared/frame.tga", "interface"),
                  ("BETTER_WATER/trail.tga", "other")):
    check(f"{rel} is {kind}", A.kind_of(rel) == kind)

DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
if not (DAC / "data/ui").is_dir():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    print("\n2) on Divide and Conquer")
    mod = Mod(DAC)
    o = A.overview(mod)
    kinds = {k["kind"]: k["count"] for k in o["kinds"]}
    check(f"{o['total']} pictures in {len(kinds)} kinds, unit cards and pips among them",
          kinds.get("unit_cards", 0) > 1000 and kinds.get("pips") == 13)
    every = [r for k in kinds for r in A._walk(mod)[k]]
    check("nothing from the models' or the ground's folders",
          not any(r.lower().startswith(("unit_models/", "battlefield/", "terrain/")) for r, _ in every))
    page = A.files(mod, "unit_cards", limit=50)
    check("a page is the size asked", len(page["files"]) == 50 and page["count"] == kinds["unit_cards"])
    milan = A.files(mod, "unit_cards", q="milan")
    check(f"the filter narrows by path ({milan['count']})",
          0 < milan["count"] < page["count"] and all("milan" in f["rel"].lower() for f in milan["files"]))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
