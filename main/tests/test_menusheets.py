"""96f: the menus' sprite sheets, page by page, and a sprite's picture replaced.

Run:  python -m tests.test_menusheets

A made-up mod with ``ui/strategy.sd`` of two pages and three sprites, and
``northern_european``'s pages: page 0 is a 64 by 32 grey picture, page 1 is
not shipped. What has to hold:

* the overview lists the sheet's pages and every sprite's box, and the mod's
  one culture;
* a page is the mod's own when it ships it, and missing otherwise;
* a box runs from left/top to right/bottom, those being one past it;
* fit: stretched, kept in shape (a clear ground round it) and filling the box
  all come out the box's size;
* Replace paints only inside the box, keeps the page's size, backs the page
  up and logs it, and the Log's Undo puts the old page back;
* a sprite, a culture or a sheet that is not there, and a file that is not a
  picture, are refused before anything is written.
"""
import io
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from tests import _tmp  # noqa: E402
from unittransfer import config, menusheets, transfer               # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def lp(s):
    b = s.encode("latin-1")
    return struct.pack("<I", len(b)) + b


def sheet(pages, sprites):
    out = struct.pack("<3I", 6, len(pages), len(sprites))
    for name, w, h in pages:
        mask = b"\xff" * ((w * h + 7) // 8)
        out += lp(name) + b"\x01" + struct.pack("<2I", w, h) + struct.pack("<I", len(mask)) + mask
    for name, page, l, r, t, b in sprites:
        out += lp(name) + struct.pack("<5h", page, l, r, t, b) + b"\x01\x00\x00\x00\x00\x00"
    return out


def png(w, h, colour):
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


root = Path(_tmp.mkdtemp(prefix="ut_menusheets_")) / "M"
data = root / "data"
(data / "ui" / "northern_european" / "interface").mkdir(parents=True)
SD = sheet([("ut_page_a.tga", 64, 32), ("ut_page_b.tga", 16, 16)],
           [("UT_BUTTON", 0, 10, 30, 4, 14), ("UT_WIDE", 0, 0, 64, 20, 32), ("UT_ELSEWHERE", 1, 0, 8, 0, 8)])
(data / "ui" / "strategy.sd").write_bytes(SD)
page = data / "ui" / "northern_european" / "interface" / "ut_page_a.tga"
Image.new("RGBA", (64, 32), (128, 128, 128, 255)).save(page, "TGA")
before = page.read_bytes()
mod = Mod(root)

o = menusheets.overview(mod)
s = next((x for x in o["sheets"] if x["rel"] == "ui/strategy.sd"), None)
check("the overview has the sheet, its two pages and three sprites",
      s and s["pages"] == ["ut_page_a.tga", "ut_page_b.tga"] and len(s["sprites"]) == 3)
check("  each sprite's page and box", s and s["sprites"][0] == {"name": "UT_BUTTON", "page": 0, "box": [10, 4, 30, 14]})
check("  and the mod's one culture", o["cultures"] == ["northern_european"])

p, where = menusheets.page_file(mod, "northern_european", "ut_page_a.tga")
check("a page the mod ships is its own", p == page and where == "mod")
p, where = menusheets.page_file(mod, "northern_european", "ut_page_nowhere.tga")
check("a page nobody has is missing", p is None and where == "")

sp = menusheets._sheet(mod, "ui/strategy.sd").sprites
check("a box is right minus left by bottom minus top", menusheets.box_size(sp[0]) == (20, 10)
      and menusheets.box_size(sp[1]) == (64, 12))

pic = Image.new("RGBA", (40, 10), (255, 0, 0, 255))
sizes = {how: menusheets.fit(pic, 20, 20, how).size for how in menusheets.FITS}
check("every fit comes out the box's size", set(sizes.values()) == {(20, 20)})
kept = menusheets.fit(pic, 20, 20, "keep")
check("  kept in shape leaves a clear ground above and below",
      kept.getpixel((10, 0))[3] == 0 and kept.getpixel((10, 10)) == (255, 0, 0, 255))
filled = menusheets.fit(pic, 20, 20, "fill")
check("  filling the box leaves no clear pixel", filled.getpixel((0, 0))[3] == 255 and filled.getpixel((19, 19))[3] == 255)

rec = menusheets.replace(mod, "ui/strategy.sd", "northern_european", "UT_BUTTON", png(5, 5, (255, 0, 0, 255)))
after = Image.open(page).convert("RGBA")
check("Replace keeps the page's size", after.size == (64, 32))
check("  paints the box", after.getpixel((10, 4)) == (255, 0, 0, 255) and after.getpixel((29, 13)) == (255, 0, 0, 255))
check("  and nothing outside it", after.getpixel((9, 4)) == (128, 128, 128, 255)
      and after.getpixel((30, 13)) == (128, 128, 128, 255) and after.getpixel((10, 14)) == (128, 128, 128, 255))
check("  backed the page up and logged it",
      rec["manifest"]["backed_up"] == ["ui/northern_european/interface/ut_page_a.tga"]
      and any(r["id"] == rec["id"] for r in config.load_log()))
check("  the sheet itself is untouched", (data / "ui" / "strategy.sd").read_bytes() == SD)
transfer.undo(rec["id"])
check("the Log's Undo puts the old page back", page.read_bytes() == before)


def refused(label, **kw):
    args = dict(sheet_rel="ui/strategy.sd", culture="northern_european", name="UT_BUTTON",
                raw=png(4, 4, (0, 0, 255, 255)))
    args.update(kw)
    try:
        menusheets.replace(mod, **args)
        check(label, False)
    except menusheets.MenuSheetError:
        check(label, page.read_bytes() == before)


refused("a sprite not in the sheet is refused", name="UT_NOPE")
refused("a culture with no pages is refused", culture="greek")
refused("a sheet that is not the game's is refused", sheet_rel="ui/other.sd")
refused("a file that is not a picture is refused", raw=b"not a picture")
refused("a page nobody has is refused", name="UT_ELSEWHERE")

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
