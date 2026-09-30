"""A recruitment screen that lags, and its turns - Phase 94.

The lag was measured in the browser on Tsardoms 3.0's militia barracks, 1,131
recruit pools in one level (DaC's largest has 343, Reforged's 166): ten fast
clicks of a rate's ▲ took 4.2 s, each a 300-440 ms long task, and 189 ms after
the fix. The numbers are in ROADMAP.md under Phase 94. What is held here is
what the fix consists of, so it is not undone by a later edit:

    1  the page-wide resize observer takes only an added ELEMENT for a new box
       (a readout's text change re-queried a 265,000-element page per click)
    2  the dirty chip and the level chip follow a burst, not each click
    3  the building's original is parsed once, not once per level per click
    4  pool rows off screen are not laid out
    5  94b: every pool row on the Unit Editor's Recruitment tab carries its
       "= N turns", and "never" / "N turns" come from the catalogue

    python -m tests.test_bigbuilding
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS = ROOT / "web" / "js"
core = (JS / "core.js").read_text(encoding="utf-8")
undo = (JS / "undo.js").read_text(encoding="utf-8")
bld = (JS / "buildings.js").read_text(encoding="utf-8")
edr = (JS / "edrecruit.js").read_text(encoding="utf-8")
html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
cat = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8"))

print("\n94a: the lag")
bump = core[core.index("const bump=recs=>"):core.index("new MutationObserver(bump)")]
check("1  the resize observer counts an added element, never a text node",
      "n.nodeType===1" in bump and "r.addedNodes.length)worth=true" not in bump)
pd = undo[undo.index("function paintDirty(){"):undo.index("function paintDirtyNow(){")]
check("2  paintDirty coalesces a burst into one check", "setTimeout(paintDirtyNow" in pd)
note = bld[bld.index("function bldDirtyNote(){"):bld.index("function bldCvFollow(){")]
check("   and the level chip waits for the burst too",
      "setTimeout(" in note and "bldLevelDirty(lvl)" in note)
lvd = bld[bld.index("function bldLevelDirty(i){"):bld.index("function renderBuildingEditor(){")]
check("3  bldLevelDirty parses the original once per b.orig",
      "b._origFor!==b.orig" in lvd and lvd.count("JSON.parse(") == 1)
check("4  pool rows off screen skip layout",
      re.search(r"#bldBody \[data-cap\]\{content-visibility:auto", html) is not None)

print("\n94b: the turns on the Unit Editor's Recruitment tab")
check("both row kinds pass the readout to their rate's box",
      edr.count("edRecTurns(k,") == 2 and "class=\"turns\"" in edr)
check("it sits under the box, so the column keeps its width",
      ".ern .turns{flex-basis:100%" in html)
pt = bld[bld.index("function poolTurns(v){"):bld.index("const POOL_EDGE")]
check("poolTurns has no English left in it: never and N turns are catalogue strings",
      "'never'" not in pt and "' turns'" not in pt and "ttN('buildings.turns_count'" in pt)
check("and N turns is a plural", isinstance(cat.get("buildings.turns_count"), dict)
      and set(cat["buildings.turns_count"]) == {"one", "other"})

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
