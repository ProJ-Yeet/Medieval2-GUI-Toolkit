"""96e3: the family tree edited as a tree; portraits of one's own; the portrait library.

What each part is here to catch:

  * **the tree is what the relative lines say**: father, wife, children, the
    people on the map and off it.
  * **an edit touches only its lines**: a new record goes after the last
    record, written like it; a father's changed line keeps its own spacing and
    its comment; a new line goes after the last one.
  * **what the game would trip on is said**: a name nobody has, a wife who is a
    man, a child in two families; a name that is taken is refused.
  * **a portrait of his own**: three pictures at the mod's portrait size, and
    `portrait <folder>` added to his line only when it has none.
  * **the library adds at the next free number of every age at once**.
  * **Undo puts every byte back**.

    python -m tests.test_family
"""
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _tmp
from unittransfer import campstrat, config, stratfamily as sfm, transfer
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


root = Path(_tmp.mkdtemp(prefix="ut_fam_")) / "T"
data = root / "data"
camp = data / campstrat.CAMPAIGN_DIR_REL / "imperial_campaign"
camp.mkdir(parents=True)
(data / "descr_sm_factions.txt").write_text("faction\tengland\nculture\tnorthern_european\n", encoding="latin-1")
STRAT = (
    "campaign\t\timperial_campaign\r\n"
    "playable\r\n\tengland\r\nend\r\n"
    "faction\tengland, balanced smith\r\n"
    "denari\t1000\r\n"
    "character\tHenry, named character, male, leader, age 40, x 10, y 10\r\n"
    "army\r\n"
    "unit\t\tPeasants\t\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
    "\r\n"
    "character\tEdward, named character, male, heir, age 18, x 11, y 10, portrait edward_own\r\n"
    "army\r\n"
    "unit\t\tPeasants\t\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
    "\r\n"
    "character_record\tMatilda, female, age 38, alive, never_a_leader\r\n"
    "character_record\tWilliam, male, age 70, dead 2, past_leader\r\n"
    "\r\n"
    "relative \t\tWilliam, nobody, Henry, end\r\n"
    "relative \t\tHenry, Matilda, Edward, end\t; the king's own\r\n"
    "\r\n"
)
(camp / "descr_strat.txt").write_bytes(STRAT.encode("latin-1"))
pdir = data / "ui" / "northern_european" / "portraits" / "portraits"
for age in ("young", "old"):
    (pdir / age / "generals").mkdir(parents=True)
    for n in range(3):
        Image.new("RGBA", (60, 80), (90, 90, 90, 255)).save(pdir / age / "generals" / f"{n:03d}.tga")
(pdir / "dead").mkdir()
for n in range(3):
    Image.new("RGBA", (60, 80), (40, 40, 40, 255)).save(pdir / "dead" / f"{n:03d}.tga")
mod = Mod(root)

print("the tree")
r = sfm.read(mod, "imperial_campaign", "england")
check("its lines", [(t["father"], t["wife"], t["children"]) for t in r["tree"]]
      == [("William", "nobody", ["Henry"]), ("Henry", "Matilda", ["Edward"])])
check("its people on the map and off it",
      {(p["name"], p["source"]) for p in r["people"]} >= {("Henry", "map"), ("Matilda", "record"), ("William", "record")})
check("a sound tree has nothing to say", r["findings"] == [])

print("\nan edit touches only its lines")
p = sfm.plan(mod, "imperial_campaign", "england",
             [{"op": "record", "name": "Alice", "sex": "female", "age": 16},
              {"op": "family", "father": "Henry", "wife": "Matilda", "children": ["Edward", "Alice"]},
              {"op": "record", "name": "Robert", "sex": "male", "age": 35},
              {"op": "family", "father": "Robert", "wife": "nobody", "children": []}])
lines = p["text"].split("\r\n")
old = STRAT.split("\r\n")
check("plans clean", p["ok"] and not p["errors"])
check("the new records go after the last record, written like it",
      lines[lines.index("character_record\tWilliam, male, age 70, dead 2, past_leader") + 1]
      == "character_record\tAlice, female, age 16, alive, never_a_leader")
check("Henry's line keeps its own spacing and its comment",
      "relative \t\tHenry, Matilda, Edward, Alice, end\t; the king's own" in lines)
check("Robert's new line goes after the last one", lines.index("relative \t\tRobert, nobody, end")
      > lines.index("relative \t\tHenry, Matilda, Edward, Alice, end\t; the king's own"))
check("and nothing else moved", len(lines) == len(old) + 3
      and all(x in lines for x in old if not x.startswith("relative \t\tHenry")))

print("\nwhat the game would trip on")
bad = sfm.plan(mod, "imperial_campaign", "england",
               [{"op": "family", "father": "Henry", "wife": "Nobodyknown", "children": []}])
check("a name nobody has is refused", bad["errors"] and not bad["text"])
taken = sfm.plan(mod, "imperial_campaign", "england", [{"op": "record", "name": "Matilda", "sex": "female"}])
check("a name that is taken is refused", taken["errors"])
odd = sfm.plan(mod, "imperial_campaign", "england",
               [{"op": "family", "father": "William", "wife": "Henry", "children": ["Edward"]}])
check("a wife who is a man, and a child in two families, are said",
      any("male" in w for w in odd["warnings"]) and any("both" in w for w in odd["warnings"]))

print("\nwrite and undo")
before = {q: q.read_bytes() for q in data.rglob("*") if q.is_file()}
rec = sfm.apply(mod, "imperial_campaign", "england",
                [{"op": "record", "name": "Alice", "sex": "female", "age": 16},
                 {"op": "family", "father": "Henry", "wife": "Matilda", "children": ["Edward", "Alice"]}])
check("written", "Alice" in (camp / "descr_strat.txt").read_bytes().decode("latin-1"))
transfer.undo(rec["id"])
check("Undo puts every byte back", before == {q: q.read_bytes() for q in data.rglob("*") if q.is_file()})

print("\nportraits")
pic = io.BytesIO(); Image.new("RGBA", (300, 400), (200, 150, 120, 255)).save(pic, "PNG")
rec = sfm.set_portrait(mod, "imperial_campaign", "england", "Henry", pic.getvalue())
folder = data / "ui" / "custom_portraits" / "england_Henry"
check("his own portrait at every age, at the mod's portrait size",
      all(Image.open(folder / f"portrait_{a}.tga").size == (60, 80) for a in ("young", "old", "dead")))
check("his line gains portrait <folder>",
      "character\tHenry, named character, male, leader, age 40, x 10, y 10, portrait england_Henry"
      in (camp / "descr_strat.txt").read_bytes().decode("latin-1"))
transfer.undo(rec["id"])
sfm.set_portrait(mod, "imperial_campaign", "england", "Edward", pic.getvalue())
check("a line that has one keeps it", (data / "ui/custom_portraits/edward_own/portrait_young.tga").is_file()
      and (camp / "descr_strat.txt").read_bytes() == before[camp / "descr_strat.txt"])
lib = sfm.library(mod, "northern_european")
check("the library counts each group and age", lib["groups"]["generals"] == {"young": 3, "old": 3, "dead": 3})
sfm.add_to_library(mod, "northern_european", "generals", [pic.getvalue(), pic.getvalue()])
check("new portraits go in at the next number of every age at once",
      all((pdir / a / "generals" / "004.tga").is_file() for a in ("young", "old")) and (pdir / "dead" / "004.tga").is_file())

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
