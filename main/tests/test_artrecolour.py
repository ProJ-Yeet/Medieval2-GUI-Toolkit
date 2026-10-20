"""96e6: recolour a faction's pictures from one pair of colours to another.

What each part is here to catch:

  * **the faction's pictures are found**: its unit cards, its battle textures
    (by its records in the modeldb) and its symbol.
  * **only the faction's colour moves**: a cloak in England's red becomes the
    new colour with its folds kept; the face, which is the same in France's
    copy of the card, stays; what is not red stays.
  * **a texture another faction wears is not painted over**: England gets its
    own copy and only England's record points at it; France's stays.
  * **Undo puts every byte back**.

    python -m tests.test_artrecolour
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

from tests import _tmp
from unittransfer import artrecolour as ar, config, sprites, transfer
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


def s(x):
    return f"{len(x)} {x}"


root = Path(_tmp.mkdtemp(prefix="ut_rc_")) / "T"
data = root / "data"
(data / "unit_models" / "test" / "textures").mkdir(parents=True)
(data / "ui" / "faction_symbols").mkdir(parents=True)
(data / "descr_sm_factions.txt").write_text(
    "faction\tengland\nprimary_colour\tred 200, green 20, blue 20\nsecondary_colour\tred 230, green 230, blue 230\n\n"
    "faction\tfrance\nprimary_colour\tred 20, green 20, blue 200\nsecondary_colour\tred 230, green 200, blue 30\n",
    encoding="latin-1")


def man(cloak):
    """A card: a cloak in the faction's colour with folds, a face, a grey helmet."""
    im = Image.new("RGBA", (48, 64), (60, 60, 60, 255))
    dr = ImageDraw.Draw(im)
    for x in range(8, 40):
        k = 0.75 + 0.25 * ((x // 4) % 2)
        dr.line([(x, 30), (x, 60)], fill=tuple(int(c * k) for c in cloak) + (255,))
    dr.ellipse((16, 8, 32, 26), fill=(222, 170, 140, 255))      # the face
    dr.rectangle((16, 2, 32, 8), fill=(140, 140, 150, 255))     # the helmet
    return im


for fac, cloak in (("england", (200, 20, 20)), ("france", (20, 20, 200))):
    d = data / "ui" / "units" / fac
    d.mkdir(parents=True)
    man(cloak).save(d / "#Spearmen.tga")
man((200, 20, 20)).save(data / "ui" / "faction_symbols" / "england.tga")
tex = data / "unit_models" / "test" / "textures" / "test.texture"
from unittransfer import armbake
tex.write_bytes(sprites.dds_to_texture(armbake.dds_with_mipmaps(man((200, 20, 20)).resize((64, 64)))))
ENTRY = (" \n" + s("test_model") + " \n1 1 \n"
         + s("unit_models/test/test_lod0.mesh") + " 10000 \n2 \n"
         + s("england") + " \n" + s("unit_models/test/textures/test.texture") + " \n"
         + s("unit_models/test/textures/test_normal.texture") + " \n" + s("unit_sprites/test_sprite.spr") + " \n"
         + s("france") + " \n" + s("unit_models/test/textures/test.texture") + " \n"
         + s("unit_models/test/textures/test_normal.texture") + " \n" + s("unit_sprites/test_sprite.spr") + " \n0 \n1 \n"
         + s("MTW2_Spear") + " " + s("MTW2_Spear_Primary") + " " + s("fs_test_shield")
         + " 1 " + s("MTW2_Spear") + " 1 " + s("MTW2_Sword") + " \n0 0 0 0 0 0 0 \n")
BLANK = s("blank") + " " + " ".join(["0"] * 39) + "\n"
(data / "unit_models" / "battle_models.modeldb").write_text(
    "22 serialization::archive 3 0 0 0 0 2 0 0\n" + BLANK + ENTRY, encoding="latin-1")
mod = Mod(root)

print("the faction's pictures")
t = {r["rel"]: r for r in ar.targets(mod, "england")}
check("its unit card, compared with France's", t["ui/units/england/#Spearmen.tga"]["others"]
      == [("ui/units/france/#Spearmen.tga", "france")])
check("its battle texture, shared with France", t["unit_models/test/textures/test.texture"]["shared"] == ["france"])
check("and its symbol", "ui/faction_symbols/england.tga" in t)

print("\nonly the colour moves")
body = {"faction": "england", "source": "england", "target": ["#1eaa1e", "#e6e6e6"]}
cols = ar.faction_colours(mod)
new, share = ar._one(mod, t["ui/units/england/#Spearmen.tga"], cols["england"], ((30, 170, 30), (230, 230, 230)), cols)
c1, c2 = new.getpixel((9, 45)), new.getpixel((13, 45))
check("the cloak is green now", c1[1] > c1[0] and c1[1] > c1[2])
check("its folds kept", c1[1] != c2[1])
check("the face stays", new.getpixel((24, 17))[:3] == (222, 170, 140))
check("the helmet stays", new.getpixel((24, 4))[:3] == (140, 140, 150))
p = ar.plan(mod, body)
check("plan shows samples and counts", p["counts"].get("card") == 1 and p["samples"] and p["shared"] == 1)

print("\nthe write")
before = {q: q.read_bytes() for q in data.rglob("*") if q.is_file()}
rec = ar.apply(mod, body)
own = data / "unit_models" / "test" / "textures" / "test_england.texture"
check("England got its own texture", own.is_file())
check("the shared one is untouched", tex.read_bytes() == before[tex])
fresh = Mod(root)
recs = {x.faction: x.texture for x in fresh.modeldb.entries[0].main_textures}
check("England's record points at its own copy, France's does not move",
      recs["england"] == "unit_models/test/textures/test_england.texture"
      and recs["france"] == "unit_models/test/textures/test.texture")
check("France's card is untouched", (data / "ui/units/france/#Spearmen.tga").read_bytes()
      == before[data / "ui/units/france/#Spearmen.tga"])
transfer.undo(rec["id"])
check("Undo puts every byte back", before == {q: q.read_bytes() for q in data.rglob("*") if q.is_file()})

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
