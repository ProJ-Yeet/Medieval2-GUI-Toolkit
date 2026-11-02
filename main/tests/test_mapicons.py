"""The icons switch - Phase 97c.

One button that shows or hides every icon on the campaign map, remembered
with the view. What is checked is that every place an icon is drawn asks the
one switch, and that an icon that is not drawn cannot be clicked or dragged:
the two ways a master switch goes wrong are an icon kind it forgot and an
invisible thing that still answers the mouse.

    python -m tests.test_mapicons
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS = ROOT / "web" / "js"
cm = _webtext.read(JS / "campmap.js")
lab = _webtext.read(JS / "maplabels.js")
mark = _webtext.read(JS / "campmark.js")
create = _webtext.read(JS / "campcreate.js")
views = _webtext.read(JS / "mapviews.js")

print("\n== 1) every icon the flat map draws asks the one switch ==")
overlay = re.search(r"function cmapOverlay\(.*?\n\}\n", cm, re.S).group(0)
check("16c's settlement and port glyphs",
      "if(icons && v.zoom >= CMAP_GLYPH_ZOOM)" in overlay)
check("17d's markers, every category at once",
      "if(icons && typeof cmkDraw === 'function')" in overlay)
check("89c's watchtower sight",
      "if(icons && typeof cmkSightDraw === 'function')" in overlay)
check("  all three off the one answer, read once a frame",
      "const icons = cmapIconsOn();" in overlay)
check("20c's dot under a settlement name",
      "if(clnDotted(z) && cmapIconsOn())" in lab)
check("  and a character's name, which is a label on its icon",
      re.search(r"function clnObjectItems\(\)\{.*?cmapIconsOn\(\)", lab, re.S) is not None)
check("the faction names and settlement names are NOT icons, and stay",
      "cfnDraw(x, s0, t0, s1, t1);" in overlay
      and re.search(r"if\(icons && typeof clnDraw", overlay) is None)

print("\n== 2) nothing hidden answers the mouse ==")
check("a hidden character cannot be dragged",
      re.search(r"function cmkPickAt\(tx, ty\)\{\s*if\(typeof cmapIconsOn === 'function' && !cmapIconsOn\(\)\) return null;",
                mark) is not None)
check("or clicked: the press goes to the tile",
      re.search(r"function cmapObjectPick\(tile\)\{.*?if\(!cmapIconsOn\(\)\) return false;",
                create, re.S) is not None)

print("\n== 3) a habit, kept like the others ==")
check("on with nothing saved", "icons: saved.icons !== false" in cm)
check("written with the layer stack", "m.icons = c.icons !== false" in cm)
check("put back by Reset", "c.icons = true;" in cm)
check("carried by a saved view, and a view from before it shows them",
      "icons: p.icons !== false" in views and "c.icons = plan.icons" in views)
check("the button is on the toolbar beside the faction names",
      re.search(r'id="cmFacBtn".*?id="cmIcoBtn"', cm, re.S) is not None)
check("and the 3D view is told", "typeof cm3Icons === 'function'" in cm)

print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
