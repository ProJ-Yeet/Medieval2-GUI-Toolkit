"""96f: Recolour's area of like colour in one click.

    python -m tests.test_recolour_area

On a made-up picture (a red field, a blue square inside, a clear corner): a
click takes the patch of like colour joined to the point and nothing past its
edge or in the clear; Alike widens it; a later click wins where two meet;
'keep' gives an area back. Then on Divide and Conquer's milan cards: a click
changes that one picture's share, and the same `touch` reaches the sample.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from tests import _realmod  # noqa: E402
from unittransfer import artrecolour as A  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n1) the area")
im = Image.new("RGBA", (40, 40), (200, 30, 30, 255))
d = ImageDraw.Draw(im)
d.rectangle((10, 10, 29, 29), fill=(30, 30, 200, 255))
d.rectangle((0, 0, 4, 4), fill=(200, 30, 30, 0))
d.rectangle((35, 35, 39, 39), fill=(210, 35, 35, 255))          # a red a little off (20 apart)
m = A.area_mask(im, 0.5, 0.5)
check(f"the blue square, all of it and only it ({m.histogram()[255]})", m.histogram()[255] == 400)
m = A.area_mask(im, 0.05, 0.5)
n = m.histogram()[255]
check(f"the red field round it, not the clear corner ({n})", n == 1600 - 400 - 25)
tight = A.area_mask(im, 0.05, 0.5, alike=4).histogram()[255]
check(f"Alike narrowed leaves the off red out ({tight} < {n})", tight == n - 25)
e = A.touch_edits(im, [{"x": 0.5, "y": 0.5, "mode": "p"}, {"x": 0.5, "y": 0.5, "mode": "keep"}])
check("a later click wins: keep takes the square back from primary",
      e["p"].histogram()[255] == 0 and e["keep"].histogram()[255] == 400)
new, share = A.recolour(im, ((200, 30, 30), (30, 30, 200)), ((30, 160, 30), None),
                        edits=A.touch_edits(im, [{"x": 0.5, "y": 0.5, "mode": "p"}]))
check(f"a square clicked as primary is painted the new primary ({new.getpixel((20, 20))})",
      new.getpixel((20, 20))[1] > new.getpixel((20, 20))[0])

DAC = _realmod.MODS / "Divide_and_Conquer_EUR"
if not (DAC / "data/ui/units/milan").is_dir():
    print("\nDivide and Conquer is not installed - SKIPPED")
else:
    print("\n2) on Divide and Conquer")
    mod = Mod(DAC)
    rel = A.targets(mod, "milan")[0]["rel"]
    body = {"faction": "milan", "source": "milan", "target": ["#2040c0", "#f0f0f0"], "rel": rel}
    plain = A.sample(mod, body)["share"]
    clicked = A.sample(mod, dict(body, touch={rel: [{"x": 0.5, "y": 0.5, "mode": "s"}]}))["share"]
    check(f"a click changes more of {rel} ({plain} -> {clicked})", clicked > plain)
    try:
        A.sample(mod, dict(body, rel="ui/units/gondor/nothing.tga"))
        check("a picture not the faction's is refused", False)
    except A.RecolourError:
        check("a picture not the faction's is refused", True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
