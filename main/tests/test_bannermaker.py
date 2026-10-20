"""96e6: a faction's battle banners painted new on a white template.

What each part is here to catch:

  * **the template is what every sheet shares**: each faction's heraldry sits
    somewhere else, so the median of the sheets drops it and keeps the cloth's
    light; the pole, alike in every sheet, is not cloth and keeps its colour.
  * **the paint takes the colours and the pattern**, the folds kept, and the
    see-through parts stay the template's.
  * **a sheet only this faction uses is written over**; a sheet it shares
    becomes its own copy and only its rows in descr_banners_new.xml move.
  * **the sheet is written as a .texture the game reads**, and Undo puts every
    byte back.

    python -m tests.test_bannermaker
"""
import base64
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

from tests import _tmp
from unittransfer import bannermaker as bm, config, transfer
from unittransfer.mod import Mod

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


root = Path(_tmp.mkdtemp(prefix="ut_ban_")) / "T"
tex = root / "data" / "banners" / "textures"
tex.mkdir(parents=True)


def sheet(colour, mark_at):
    """A 256 x 128 sheet: a cloth of the faction's colour with folds, heraldry
    somewhere of its own, a brown pole every sheet shares, the rest clear."""
    im = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for x in range(10, 110):
        k = 0.8 + 0.2 * ((x // 10) % 2)          # folds
        dr.line([(x, 10), (x, 110)], fill=tuple(int(c * k) for c in colour) + (255,))
    dr.rectangle((112, 0, 120, 127), fill=(90, 60, 30, 255))   # the pole
    dr.ellipse((mark_at, 40, mark_at + 20, 60), fill=(250, 250, 0, 255))
    return im


for name, colour, at in (("england", (200, 20, 20), 15), ("france", (20, 20, 200), 40),
                         ("spain", (200, 200, 20), 65), ("milan", (20, 160, 20), 85)):
    sheet(colour, at).save(tex / f"faction_banner_{name}.tga")
rows = "\n".join(f'\t\t\t<Texture Faction="{f}" DiffuseMap="banners\\textures\\faction_banner_{s}.tga"/>'
                 for f, s in (("england", "england"), ("france", "france"), ("spain", "spain"),
                              ("milan", "milan"), ("venice", "milan")))
XML = f"<Banners>\n\t<FactionBanners>\n\t\t<Banner Name=\"main_infantry\">\n\t\t\t<Textures>\n{rows}\n\t\t\t</Textures>\n\t\t</Banner>\n\t</FactionBanners>\n</Banners>\n"
(root / "data" / "descr_banners_new.xml").write_text(XML, encoding="latin-1")
mod = Mod(root)

print("the white template")
s = bm.template(mod)
check("it is made from all four sheets", s is not None and s.count == 4)
px = s.blank.getpixel((50, 50))
check("each faction's heraldry is gone from it (grey, not yellow)", abs(px[0] - px[2]) < 20)
check("the pole every sheet shares keeps its colour", s.blank.getpixel((116, 64))[:3] == (90, 60, 30))
check("one banner of cloth is found", len(s.panels) >= 1 and s.panels[0][0] <= 16 and s.panels[0][2] >= 100)

print("\nthe paint")
sym = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
ImageDraw.Draw(sym).rectangle((5, 5, 35, 35), fill=(255, 255, 255, 255))
b = io.BytesIO(); sym.save(b, "PNG")
body = {"faction": "england", "colours": ["#000080", "#ff0000"], "pattern": "two stripes, upright",
        "symbol": base64.b64encode(b.getvalue()).decode("ascii")}
out = bm.paint(s, [(0, 0, 128), (255, 0, 0)], None, "two stripes, upright")
left, right = out.getpixel((20, 100)), out.getpixel((95, 100))
check("the pattern's two colours, left and right", left[2] > left[0] and right[0] > right[2])
check("the folds are kept", out.getpixel((15, 100))[2] != out.getpixel((25, 100))[2])
check("what was see-through stays so", out.getpixel((200, 120))[3] == 0)
try:
    bm.plan(mod, dict(body, colours=["red"]))
    check("a colour that is not #rrggbb is refused", False)
except bm.BannerError:
    check("a colour that is not #rrggbb is refused", True)

print("\nwhere it goes")
before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
p = bm.plan(mod, body)
check("England's own sheet is written over", p["target"] == "banners/textures/faction_banner_england.tga"
      and not p["shared"])
check("and plan wrote nothing", before == {q: q.read_bytes() for q in root.rglob("*") if q.is_file()})
pv = bm.plan(mod, dict(body, faction="venice"))
check("Venice shares Milan's, so it gets its own", pv["shared"]
      and pv["target"] == "banners/textures/faction_banner_venice.texture")
rec = bm.apply(mod, dict(body, faction="venice"))
xml = (root / "data" / "descr_banners_new.xml").read_text(encoding="latin-1")
check("Venice's row points at its own sheet", 'Faction="venice" DiffuseMap="banners\\textures\\faction_banner_venice.texture"' in xml)
check("Milan's row is untouched", 'Faction="milan" DiffuseMap="banners\\textures\\faction_banner_milan.tga"' in xml)
written = bm.read_picture(tex / "faction_banner_venice.texture")
check("the sheet is a .texture the readers open, at the template's size", written.size == (256, 128))
transfer.undo(rec["id"])
check("Undo puts every byte back", before == {q: q.read_bytes() for q in root.rglob("*") if q.is_file()})

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
