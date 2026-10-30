"""M2EX's text vegetation (vegtext.py): the game started with its own switch,
waited for, and its file taken into the mod.

The game is never started: a stand-in process records the command line and,
when it "exits", writes what M2EX would.

    python -m tests.test_vegtext
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import config, vegtext  # noqa: E402
from unittransfer import keyblock as kb  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


tmp = Path(_tmp.mkdtemp(prefix="ut_veg_"))
cfg = tmp / "cfg"
cfg.mkdir()
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

game = tmp / "Medieval II Total War"
mod_root = game / "mods" / "My Mod"
(mod_root / "data").mkdir(parents=True)
(game / "M2EX.exe").write_bytes(b"")
(mod_root / "My Mod.cfg").write_text("[features]\nmod = mods/My Mod\n")
kb.write_text(mod_root / "data" / "descr_caps_ex.txt", "; caps\r\nmodel_battle_source text\r\n", "latin-1")


class FakeMod:
    def __init__(self, root):
        self.root, self.name, self.data = root, root.name, root / "data"


class FakeProc:
    """Up for `polls` asks, then gone, having written `writes` (or nothing)."""
    last = None

    def __init__(self, cmd, cwd=None, polls=1, writes="veg body\r\n"):
        FakeProc.last = self
        self.cmd, self.cwd, self.left, self.writes = cmd, cwd, polls, writes

    def poll(self):
        if self.left > 0:
            self.left -= 1
            return None
        if self.writes is not None:
            out = Path(self.cwd) / "mods" / "My Mod" / "data" / vegtext.OUT_REL
            if not out.exists():
                kb.write_text(out, self.writes, "latin-1")
        return 0


mod = FakeMod(mod_root)

print("\n1) the command, as the batch file runs it")
g, cmd = vegtext.command(mod)
check("from the game folder, M2EX.exe, the mod's cfg as a relative path, the switch",
      g == game and cmd == [str(game / "M2EX.exe"), "@mods\\My Mod\\My Mod.cfg", "--util.vegetation_decompile"])

print("\n2) a run: started, waited for, taken in")
check("no run yet is idle", vegtext.status(mod).get("idle"))
# up for two asks: the refused second start asks once, the status below once
vegtext.start(mod, popen=lambda c, cwd=None: FakeProc(c, cwd, polls=2))
check("the game started in the game folder", FakeProc.last.cwd == str(game))
try:
    vegtext.start(mod, popen=lambda c, cwd=None: FakeProc(c, cwd))
    refused = False
except vegtext.VegError:
    refused = True
check("a second start while it runs is refused", refused)
check("while it is up, status says running", vegtext.status(mod).get("running"))
done = vegtext.status(mod)
d = done.get("done") or {}
check("once it is gone, the file is the mod's descr_vegetation.txt",
      d.get("written") and not d.get("kept")
      and kb.read_text(mod.data / vegtext.TEXT_REL, "latin-1") == "veg body\r\n"
      and not (mod.data / vegtext.OUT_REL).exists())
caps = kb.read_text(mod.data / "descr_caps_ex.txt", "latin-1")
check("and the caps file says vegetation_source text, its other lines kept",
      caps == "; caps\r\nmodel_battle_source text\r\nvegetation_source text\r\n"
      and vegtext.vegetation_text(mod))
rec = config.load_log()[-1]
check("one Undo: the caps file backed up, the text listed as made",
      rec["manifest"] == {"backed_up": ["descr_caps_ex.txt"], "created": [vegtext.TEXT_REL]})

print("\n3) a mod that already has the file, and a game quit too soon")
vegtext.start(mod, popen=lambda c, cwd=None: FakeProc(c, cwd, polls=0, writes="new\r\n"))
d = vegtext.status(mod).get("done") or {}
check("its own descr_vegetation.txt is kept, the game's left beside it",
      d.get("kept") and kb.read_text(mod.data / vegtext.TEXT_REL, "latin-1") == "veg body\r\n"
      and (mod.data / vegtext.OUT_REL).is_file())
vegtext.start(mod, popen=lambda c, cwd=None: FakeProc(c, cwd, polls=0, writes=None))
d = vegtext.status(mod).get("done") or {}
check("a game quit before the main menu wrote nothing, and says so (the old file not taken for it)",
      not d.get("written") and d.get("error"))

print("\n4) refused before anything starts")
(game / "M2EX.exe").unlink()
try:
    vegtext.command(mod)
    no_exe = False
except vegtext.VegError:
    no_exe = True
check("no M2EX.exe in the game folder", no_exe)
(game / "M2EX.exe").write_bytes(b"")
(mod_root / "My Mod.cfg").unlink()
try:
    vegtext.command(mod)
    no_cfg = False
except vegtext.VegError:
    no_cfg = True
check("no .cfg in the mod", no_cfg)

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
