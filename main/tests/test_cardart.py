"""The card maker's game pieces and the mod's own card sizes (cardart.py).

    python -m tests.test_cardart

Nothing installed is needed: a mod with an interface sheet, its page picture
and some cards is written to a temp folder.

1. a sprite named in ui/*.sd.xml is cut from its page, the culture asked for
   first, any culture's page else; a name the card maker does not use is
   refused; a mod without the sheet gives None
2. the size most of the mod's cards and info pictures are, from the headers
3. over HTTP: the PNG, a 404 for a missing piece, the sizes as JSON
"""
import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import cardart, config  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


class FakeMod:
    def __init__(self, root):
        self.root = root
        self.data = root / "data"
        self.name = root.name


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
root = Path(_tmp.mkdtemp(prefix="ut_cardart_")) / "Card_Mod"
data = root / "data"
(data / "ui/southern_european/interface").mkdir(parents=True)
(data / "ui/northern_european/interface").mkdir(parents=True)
(data / "ui/shared.sd.xml").write_text(
    '<sprite_sheets>\n <page file="cards_page.tga">\n'
    '  <sprite name="STRAT_CARD_BACKGROUND" x="4" y="2" w="10" h="12"/>\n'
    '  <sprite name="PORTRAIT_FRAME" x="20" y="0" w="16" h="16"/>\n </page>\n</sprite_sheets>\n',
    encoding="latin-1")
page = Image.new("RGBA", (40, 20), (0, 0, 0, 255))
page.paste((200, 10, 10, 255), (4, 2, 14, 14))
page.save(data / "ui/southern_european/interface/cards_page.tga")
other = Image.new("RGBA", (40, 20), (0, 0, 0, 255))
other.paste((10, 200, 10, 255), (4, 2, 14, 14))
other.save(data / "ui/northern_european/interface/cards_page.tga")
for fac in ("england", "france"):
    (data / "ui/units" / fac).mkdir(parents=True)
    (data / "ui/unit_info" / fac).mkdir(parents=True)
    for i in range(3):
        Image.new("RGBA", (68, 90)).save(data / "ui/units" / fac / f"#unit{i}.tga")
        Image.new("RGBA", (160, 210)).save(data / "ui/unit_info" / fac / f"unit{i}_info.tga")
Image.new("RGBA", (48, 64)).save(data / "ui/units/england/#odd.tga")
mod = FakeMod(root)

try:
    print("1) a piece of the game's interface")
    a = cardart.game_sprite(mod, "STRAT_CARD_BACKGROUND", "southern_european")
    check("cut from its page at its box", a is not None and a.size == (10, 12) and a.getpixel((0, 0)) == (200, 10, 10, 255))
    b = cardart.game_sprite(mod, "STRAT_CARD_BACKGROUND", "northern_european")
    check("the culture asked for first", b is not None and b.getpixel((0, 0)) == (10, 200, 10, 255))
    c = cardart.game_sprite(mod, "STRAT_CARD_BACKGROUND", "greek")
    check("a culture without the page takes another's", c is not None and c.size == (10, 12))
    check("a name the card maker does not use is refused", cardart.game_sprite(mod, "SOMETHING_ELSE") is None)
    check("a piece the sheet does not name is None", cardart.game_sprite(mod, "SCROLL_MID") is None)
    bare = FakeMod(Path(_tmp.mkdtemp(prefix="ut_cardart_bare_")))
    (bare.data).mkdir(parents=True)
    check("a mod with no sheet (and no game found) is None", cardart.game_sprite(bare, "STRAT_CARD_BACKGROUND") is None)

    print("2) the mod's own sizes")
    sz = cardart.mod_sizes(mod)
    check(f"cards: the size most are ({sz['card']}), not the odd one out", sz["card"] == [68, 90])
    check(f"info pictures ({sz['info']})", sz["info"] == [160, 210])
    check("a mod with none says None for both", cardart.mod_sizes(bare) == {"card": None, "info": None})

    print("3) over HTTP")
    from unittransfer.server import Handler, Registry, _Server
    reg = Registry(cfg / "icons")
    reg.get = lambda n: mod if n == mod.name else None
    reg.names = lambda: [mod.name]
    Handler.registry = reg
    httpd = _Server(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    with urllib.request.urlopen(f"{base}/api/armory/card_art?mod=Card_Mod&name=STRAT_CARD_BACKGROUND&culture=southern_european") as r:
        check("the piece comes as a PNG", r.headers.get("Content-Type", "").startswith("image/png") and r.read()[:4] == b"\x89PNG")
    try:
        urllib.request.urlopen(f"{base}/api/armory/card_art?mod=Card_Mod&name=SCROLL_MID")
        check("a missing piece is a 404", False)
    except urllib.error.HTTPError as e:
        check("a missing piece is a 404", e.code == 404)
    with urllib.request.urlopen(f"{base}/api/armory/card_sizes?mod=Card_Mod") as r:
        check("the sizes as JSON", json.loads(r.read()) == {"card": [68, 90], "info": [160, 210]})
    httpd.shutdown()
finally:
    shutil.rmtree(root.parent, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
