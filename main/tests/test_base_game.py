"""The base game, opened read only beside the mods.

Run:  python -m tests.test_base_game

What has to hold:

* the game's own packs name its files ``data/...``, a Kingdoms campaign's
  ``mods/<name>/data/...``, and a plain mod has no prefix;
* nothing can be written under the base game's ``data/`` once it is
  registered: every write through ``open`` (and so ``write_text`` and
  ``shutil.copy``) is refused with words that say how to change it instead;
  a mod beside it is written as before;
* on this install, if the game is set: the base game lists its units and
  building lines out of its packs, and a mod made from it would take the
  packed text files out with it.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import gamepack, modfork                       # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


class Root:
    def __init__(self, root):
        self.root = root


tmp = Path(_tmp.mkdtemp(prefix="ut_basegame_"))
game = tmp / "Game"
for d in ("packs", "data", "mods/crusades/packs", "mods/crusades/data", "mods/Mine/data"):
    (game / d).mkdir(parents=True)

print("\n1) how each one's packs name its files")
check("the game: data/", gamepack.own_prefix(Root(game)) == "data/")
check("a Kingdoms campaign: mods/<name>/data/",
      gamepack.own_prefix(Root(game / "mods" / "crusades")) == "mods/crusades/data/")
check("a mod with no packs: none", gamepack.own_prefix(Root(game / "mods" / "Mine")) == "")

print("\n2) the base game's data/ refuses writes")
modfork.install_write_guard()
ro = str(game / "data").replace("\\", "/").lower() + "/"
modfork.READ_ONLY.append(ro)
try:
    for label, act in (("write_text", lambda: (game / "data" / "x.txt").write_text("x")),
                       ("open for append", lambda: open(game / "data" / "y.txt", "a").close()),
                       ("shutil.copy into it", lambda: shutil.copy(__file__, game / "data" / "z.py"))):
        try:
            act()
            refused, why = False, ""
        except modfork.ReadOnlyError as e:
            refused, why = True, str(e)
        check(f"{label} is refused", refused and not any((game / "data").iterdir()))
    check("  saying how to change it instead", "make a mod from it" in why)
    with open(__file__) as fh:
        check("reading is untouched", bool(fh.read(10)))
    (game / "mods" / "Mine" / "data" / "ok.txt").write_text("fine")
    check("a mod beside it is written as before", (game / "mods" / "Mine" / "data" / "ok.txt").read_text() == "fine")
finally:
    modfork.READ_ONLY.remove(ro)

print("\n3) this install's base game")
from unittransfer import config                                   # noqa: E402
real = config.get_med2_root()
if not real or not (Path(real) / "packs").is_dir():
    print("  (skipped: no packed install is set)")
else:
    from unittransfer.mod import Mod                              # noqa: E402
    base = Mod(Path(real))
    check("its units are read out of its packs", len(base.edu.units) > 300)
    check("  and its building lines", len(base.edb.lines) > 40 if hasattr(base.edb, "lines")
          else bool(base.edb))
    check("  and the cultures its buildings are drawn for", "northern_european" in base.cultures)
    p = modfork.plan(Path(real), "ut_never_made", game=True)
    check("a mod made from it takes the packed text out too",
          p["packed_files"] > 100 and not (Path(real) / "mods" / "ut_never_made").exists())

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
