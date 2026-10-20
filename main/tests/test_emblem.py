"""96e6: a faction's whole emblem set from one picture.

What each part is here to catch:

  * **every picture is made at the size the mod uses**, not the game's
    default: a mod's 59 px "24 px" button stays 59 px.
  * **the states are measured from the mod's own**: a mouse-over twice as
    bright as its normal makes the new one twice as bright; a greyed one is
    grey; a selected one gets the old glow round the new shape.
  * **the emblem sits where the old one sat**, the margin kept.
  * **what is not a picture, or a blank one, is refused**; plan writes nothing,
    apply writes TGA files the game reads, and Undo puts every byte back.

    python -m tests.test_emblem
"""
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

from tests import _tmp
from unittransfer import config, emblem, transfer
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


root = Path(_tmp.mkdtemp(prefix="ut_em_")) / "T"
d24 = root / "data/menu/symbols/fe_buttons_24"
d24.mkdir(parents=True)


def disc(size, colour, glow=None):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if glow:
        dr.ellipse((2, 2, size - 3, size - 3), fill=glow + (160,))
    dr.ellipse((8, 8, size - 9, size - 9), fill=colour + (255,))
    return im


disc(40, (60, 60, 60)).save(d24 / "symbol24_england.tga")
disc(40, (120, 120, 120)).save(d24 / "symbol24_england_roll.tga")
disc(40, (120, 120, 120), glow=(250, 220, 40)).save(d24 / "symbol24_england_select.tga")
disc(40, (30, 30, 30)).save(d24 / "symbol24_england_grey.tga")
mod = Mod(root)

src = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
ImageDraw.Draw(src).rectangle((20, 10, 180, 90), fill=(200, 40, 40, 255))
buf = io.BytesIO(); src.save(buf, "PNG"); raw = buf.getvalue()

print("the targets")
t = {x["rel"]: x for x in emblem.targets(mod, "england")}
check("the mod's 40 px buttons keep their size",
      t["menu/symbols/fe_buttons_24/symbol24_england.tga"]["size"] == [40, 40])
check("each state is its own target", t["menu/symbols/fe_buttons_24/symbol24_england_grey.tga"]["state"] == "grey")

print("\nthe pictures")
made = emblem.build(src, list(t.values()))
n = made["menu/symbols/fe_buttons_24/symbol24_england.tga"]
roll = made["menu/symbols/fe_buttons_24/symbol24_england_roll.tga"]
grey = made["menu/symbols/fe_buttons_24/symbol24_england_grey.tga"]
sel = made["menu/symbols/fe_buttons_24/symbol24_england_select.tga"]
box = emblem.footprint(n)
check("the emblem sits inside the old one's place, the margin kept", box[0] >= 8 and box[2] <= 24)
check("its shape is kept (wider than high)", box[2] > box[3])
c = n.getpixel((20, 20)); r = roll.getpixel((20, 20))
check("mouse over is brighter by the mod's own measure, about twice", 1.6 < (r[0] + 1) / (c[0] + 1) < 2.2 or r[0] == 255)
g = grey.getpixel((20, 20))
check("greyed out is grey", g[0] == g[1] == g[2])
check("selected has the old glow round the new shape",
      sel.getpixel((3, 20))[3] > 0 and n.getpixel((3, 20))[3] == 0)

print("\nplan and apply")
before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
p = emblem.plan(mod, "england", raw)
check("plan shows old beside new for each", all(row["new"].startswith("data:image/png") for row in p["rows"]))
check("and writes nothing", before == {q: q.read_bytes() for q in root.rglob("*") if q.is_file()})
for bad in (b"not a picture", None):
    try:
        if bad is None:
            b2 = io.BytesIO(); Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(b2, "PNG"); bad = b2.getvalue()
        emblem.plan(mod, "england", bad)
        check("a file that is not a picture, or a blank one, is refused", False)
    except emblem.EmblemError:
        check("a file that is not a picture, or a blank one, is refused", True)
rec = emblem.apply(mod, "england", raw)
w = Image.open(d24 / "symbol24_england.tga")
check("the TGA is written at its size", w.size == (40, 40) and w.format == "TGA")
check("the loading logo is made too, at 128", (root / "data/loading_screen/symbols/symbol128_england.tga").is_file())
transfer.undo(rec["id"])
check("Undo puts every byte back", before == {q: q.read_bytes() for q in root.rglob("*") if q.is_file()})

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
