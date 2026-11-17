"""A mod with no building-art folders of its own reads the base game's cultures.

    python -m tests.test_culture_fallback

A released mod often ships no ``data/ui/<culture>/buildings`` at all and lets
the game draw every building out of its own packs (kirsi_biggermap_medieval2,
2026-11-17). The building browser then had no culture to show, asked for
``#_<level>.tga`` and painted a placeholder on every level, and bringing lines
from another mod copied no building cards, since it copies one per culture.

1. Such a mod's cultures are the base game's.
2. Its levels find the base game's art under them.
3. A mod with its own folders keeps exactly its own list.
4. Lines brought into it take their cards, under the base game's cultures.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import _tmp  # noqa: E402
from unittransfer import buildings as B, edbimport as E  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def bare_mod(name: str) -> Path:
    root = Path(_tmp.mkdtemp(prefix="ut_cfb_")) / name
    (root / "data").mkdir(parents=True)
    return root


plain = Mod(bare_mod("no_art"))
game = B.game_ui(plain)
if not game:
    print("SKIPPED - needs the base game's packs (Settings' game folder)")
    sys.exit(0)

print("\n1) a mod with no culture folders")
check("its cultures are the base game's", B.cultures_of(plain) == game.cultures)
check("  and there are some", len(B.cultures_of(plain)) >= 4)

print("\n2) its levels find the base game's art")
cul = "northern_european" if "northern_european" in game.cultures else game.cultures[0]
hit, where = B.find_icon(plain, cul, "roads", "small")
check(f"roads under {cul} is the game's own picture", hit is not None and where == "vanilla")
hit, where = B.find_icon(plain, cul, "barracks", "large")
check("  and so is a constructed one", hit is not None and where == "vanilla")

print("\n3) a mod with its own folders keeps its own list")
own_root = bare_mod("own_art")
(own_root / "data/ui/gondor/buildings").mkdir(parents=True)
check("only its own culture", B.cultures_of(Mod(own_root)) == ["gondor"])

print("\n4) lines brought into it take their cards")
src_root = bare_mod("src_art")
art = src_root / "data/ui" / cul / "buildings"
art.mkdir(parents=True)
for f in (f"#{cul}_forge_x.tga", f"#{cul}_forge_x_1.tga", f"#{cul}_forge_x_1_constructed.tga"):
    (art / f).write_bytes(b"TGA " + f.encode())
p = E.TreePlan(dst=Mod(bare_mod("dst_no_art")), source="src_art", lines=["forge_x"])
E._pictures(p, Mod(src_root), {"forge_x": ["forge_x_1"]}, {}, {})
got = sorted(rel for _f, rel in p.pictures)
check("the line's card and the level's two are copied",
      got == sorted([f"ui/{cul}/buildings/#{cul}_forge_x.tga",
                     f"ui/{cul}/buildings/#{cul}_forge_x_1.tga",
                     f"ui/{cul}/buildings/#{cul}_forge_x_1_constructed.tga"]))

print(f"\n{sum(ok)}/{len(ok)} checks" + ("" if all(ok) else " - SOME FAILED"))
sys.exit(0 if all(ok) else 1)
