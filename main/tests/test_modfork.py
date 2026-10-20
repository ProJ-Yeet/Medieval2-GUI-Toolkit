"""96e7: rules and mods - the vanilla value beside a rule, and a new mod folder
of hard links.

What each part is here to catch:

  * **a fork links the heavy files and copies the text.** A texture, a model
    and a pack are one file under two names; every ``.txt``/``.xml`` and the
    ``strings.bin`` the game rebuilds are real copies.
  * **the start files name the new folder**: the base's ``.cfg`` with
    ``mods/<base>`` turned into ``mods/<new>``, and a ``.bat`` for it.
  * **a save into a linked file stays in its own mod.** With the write guard
    on, writing a linked texture in the fork leaves the base's bytes alone, and
    the other way round.
  * **a name that is taken, the base's own, or not a folder name is refused**,
    and nothing is made.
  * **the vanilla values come from the game's packs** (when a game is
    installed): every campaign constant and settlement factor has one.

    python -m tests.test_modfork
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, modfork

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


game = Path(_tmp.mkdtemp(prefix="ut_fork_")) / "Medieval II Total War"
base = game / "mods" / "BaseMod"
(base / "data" / "textures").mkdir(parents=True)
(base / "data" / "text").mkdir(parents=True)
(game / "medieval2.exe").write_bytes(b"MZ")
(base / "data" / "export_descr_unit.txt").write_text("type Peasants\n", encoding="latin-1")
(base / "data" / "descr_campaign_db.xml").write_text("<campaign_db/>\n", encoding="latin-1")
(base / "data" / "textures" / "peasant.texture").write_bytes(b"DDS original")
(base / "data" / "text" / "expanded.txt.strings.bin").write_bytes(b"\x02\x00bin")
(base / "data" / "unit.mesh").write_bytes(b"mesh bytes")
(base / "BaseMod.cfg").write_text("[features]\nmod = mods/BaseMod\n[log]\nto = mods/BaseMod/system.log.txt\n",
                                  encoding="latin-1")
(base / "BaseMod.bat").write_text("medieval2.exe @mods/BaseMod/BaseMod.cfg\n", encoding="latin-1")
(base / "saves").mkdir()
(base / "saves" / "a.sav").write_bytes(b"save")

print("the plan, before anything is made")
p = modfork.plan(base, "Fork_1")
check("a free name plans clean", p["ok"] and p["target"].endswith(os.path.join("mods", "Fork_1")))
check("the heavy files are counted as linked, the text as copied",
      p["linked_files"] == 2 and p["copied_files"] == 3)
check("a name with a space is refused", not modfork.plan(base, "My Mod")["ok"])
check("the base's own name is refused", not modfork.plan(base, "basemod")["ok"])

print("\nthe fork")
out = modfork.create(base, "Fork_1")
fork = game / "mods" / "Fork_1"
same = lambda a, b: os.path.samefile(a, b)
check("the texture and the mesh are hard links to the base's",
      same(fork / "data" / "textures" / "peasant.texture", base / "data" / "textures" / "peasant.texture")
      and same(fork / "data" / "unit.mesh", base / "data" / "unit.mesh"))
check("the EDU, the XML and the strings.bin are copies of their own",
      not same(fork / "data" / "export_descr_unit.txt", base / "data" / "export_descr_unit.txt")
      and not same(fork / "data" / "text" / "expanded.txt.strings.bin",
                   base / "data" / "text" / "expanded.txt.strings.bin"))
check("the saves are not carried", not (fork / "saves").exists())
cfg = (fork / "Fork_1.cfg").read_text(encoding="latin-1")
check("the .cfg names the new folder and not the old",
      "mods/Fork_1" in cfg and "BaseMod" not in cfg and not (fork / "BaseMod.cfg").exists())
check("a start file is written for it", "@mods\\Fork_1\\Fork_1.cfg" in
      (fork / "Start_Fork_1.bat").read_text(encoding="latin-1"))
check("the summary counts what it did", out["linked"] == 2 and out["copied"] == 3
      and out["hard_links"] is True)
check("the fork is marked", (modfork.info(fork) or {}).get("base") == "BaseMod")
check("a second fork under the same name is refused",
      not modfork.plan(base, "Fork_1")["ok"])

print("\nthe write guard")
modfork.install_write_guard()
modfork.install_write_guard()          # twice is once
(fork / "data" / "textures" / "peasant.texture").write_bytes(b"DDS recoloured")
check("a texture written in the fork stays in the fork",
      (base / "data" / "textures" / "peasant.texture").read_bytes() == b"DDS original"
      and (fork / "data" / "textures" / "peasant.texture").read_bytes() == b"DDS recoloured")
with open(base / "data" / "unit.mesh", "ab") as f:
    f.write(b"+more")
check("and an append to the base stays in the base",
      (fork / "data" / "unit.mesh").read_bytes() == b"mesh bytes"
      and (base / "data" / "unit.mesh").read_bytes() == b"mesh bytes+more")
check("reading a linked file leaves the link alone",
      (modfork.create(base, "Fork_2") and
       (game / "mods" / "Fork_2" / "data" / "unit.mesh").read_bytes() == b"mesh bytes+more"
       and os.stat(base / "data" / "unit.mesh").st_nlink == 2))
check("no stray working file is left beside it",
      not list((base / "data").glob("*.unlinking")))

print("\nthe vanilla values")
from unittransfer import campdb, settlemech, vanilla
root = config.get_med2_root()
if not root or not (Path(root) / "packs").is_dir():
    print("  (no game installed - the packs are what is read; skipped)")
else:
    cv = campdb.vanilla_values(None)
    sv = settlemech.vanilla_values(None)
    check(f"{len(cv)} campaign constants have a vanilla value",
          len(cv) > 100 and cv.get("recruitment/recruitment_slots") == "1")
    check(f"{len(sv)} settlement values have one",
          len(sv) > 50 and any(k.startswith("level/") for k in sv))
    check("a file the packs do not hold has none", vanilla.text("no_such_file.txt") is None)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
