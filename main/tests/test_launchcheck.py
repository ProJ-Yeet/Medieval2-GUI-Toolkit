"""Phase 58: will this mod even launch?

    python -m tests.test_launchcheck

1. The Large Address Aware bit, read out of a PE header built here.
2. A game folder built in a temp dir, one fault at a time: a ROCSS-shaped .bat
   that tries M2EX.exe and falls back, a .cfg naming another mod, a .cfg with
   no file_first, an executable that is not there or not LAA, the EOP
   launcher's uiCfg.json naming a .cfg that is missing, and a mod with no way
   to start at all.
3. Both installed mods start (DaC through M2TWEOP, ROCSS through its .bat
   and M2TWEOP), which is what their players do.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import launchcheck as lc  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def pe(laa: bool) -> bytes:
    """The smallest file that is a PE as far as the header goes."""
    head = bytearray(512)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", head, 0x80 + 22, 0x0102 | (0x20 if laa else 0))
    return bytes(head)


class FakeMod:
    def __init__(self, root: Path):
        self.root = root
        self.data = root / "data"


# ---- 1) the PE bit ---------------------------------------------------------------
print("\n1) Large Address Aware, from the PE header")
tmp = Path(_tmp.mkdtemp(prefix="ut_launch_"))
(tmp / "yes.exe").write_bytes(pe(True))
(tmp / "no.exe").write_bytes(pe(False))
(tmp / "junk.exe").write_bytes(b"not an exe")
check("the bit set reads True", lc.large_address_aware(tmp / "yes.exe") is True)
check("the bit clear reads False", lc.large_address_aware(tmp / "no.exe") is False)
check("something that is not a PE reads None, not False", lc.large_address_aware(tmp / "junk.exe") is None)

# ---- 2) a game folder, one fault at a time ----------------------------------------
print("\n2) a game folder built here")
ROCSS_BAT = ("@echo off\r\ncd ..\\..\r\nIF EXIST M2EX.exe (start M2EX.exe @%0\\..\\Configuration.cfg) ELSE (\r\n"
             "IF EXIST medieval2.exe (\r\nstart medieval2.exe @%0\\.\\Configuration.cfg) ELSE (\r\n"
             "    echo ERROR\r\n  )\r\n)\r\n")
GOOD_CFG = "[features]\nmod = mods/{name}\n\n[io]\nfile_first = 1  # look up sequence of files: mod, main game, packs\n"


def game(case: str, laa=True, exe="medieval2.exe"):
    g = tmp / case
    (g / "mods" / "MyMod" / "data").mkdir(parents=True)
    if exe:
        (g / exe).write_bytes(pe(laa))
    return g, g / "mods" / "MyMod"


g, m = game("bat")
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text(GOOD_CFG.format(name="MyMod"))
r = lc.check(FakeMod(m))
row = r["routes"][0] if r["routes"] else {}
check(f"a .bat that tries M2EX.exe then medieval2.exe is one route, and it starts ({r['verdict']})",
      r["verdict"] == "ready" and len(r["routes"]) == 1 and row.get("exe") == "medieval2.exe")
check("and it says M2EX.exe was tried first and is not here",
      any("M2EX.exe first" in n for n in row.get("notes", [])))
check("the .cfg is read past the `)` that closes the .bat's IF", row.get("cfg") == "Configuration.cfg")

g, m = game("other")
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text(GOOD_CFG.format(name="SomeoneElse"))
r = lc.check(FakeMod(m))
check("a .cfg naming another mod's folder is a fault that names both",
      r["verdict"] == "broken" and any("mods/SomeoneElse" in f and "mods/MyMod" in f
                                       for f in r["routes"][0]["faults"]))

g, m = game("case")
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text(GOOD_CFG.format(name="mymod"))
check("the folder is matched case-blind, as Windows opens it", lc.check(FakeMod(m))["verdict"] == "ready")

g, m = game("nofirst")
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text("[features]\nmod = mods/MyMod\n")
r = lc.check(FakeMod(m))
check("no file_first is a warning, and the mod still starts",
      r["verdict"] == "warn" and any("file_first" in w for w in r["routes"][0]["warnings"]))

g, m = game("noexe", exe="")
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text(GOOD_CFG.format(name="MyMod"))
r = lc.check(FakeMod(m))
check("neither executable in the game folder is a fault", r["verdict"] == "broken"
      and any("neither" in f for f in r["routes"][0]["faults"]))

g, m = game("nolaa", laa=False)
(m / "Launch.bat").write_bytes(ROCSS_BAT.encode())
(m / "Configuration.cfg").write_text(GOOD_CFG.format(name="MyMod"))
r = lc.check(FakeMod(m))
check("an executable without the LAA bit is a warning naming it",
      r["verdict"] == "warn" and r["routes"][0]["laa"] is False
      and any("medieval2.exe is not Large Address Aware" in w for w in r["routes"][0]["warnings"]))

g, m = game("eop")
(m / "M2TWEOP_GUI.exe").write_bytes(pe(True))
(m / "eopData" / "config").mkdir(parents=True)
(m / "eopData" / "config" / "uiCfg.json").write_text(json.dumps({"modCfgFile": "TATW.cfg",
                                                                  "useVanillaCfg": False}))
r = lc.check(FakeMod(m))
check("the EOP launcher naming a .cfg that is not there is a fault",
      r["verdict"] == "broken" and "TATW.cfg" in r["routes"][0]["faults"][0])
(m / "TATW.cfg").write_text(GOOD_CFG.format(name="MyMod"))
check("and with the file there, it starts", lc.check(FakeMod(m))["verdict"] == "ready")
(m / "eopData" / "config" / "uiCfg.json").write_text(json.dumps({"modCfgFile": "TATW.cfg",
                                                                  "useVanillaCfg": True}))
check("told to use the vanilla cfg, it names no .cfg of the mod's, which is a fault",
      lc.check(FakeMod(m))["verdict"] == "broken")

g, m = game("bare")
(m / "mymod.cfg").write_text(GOOD_CFG.format(name="MyMod"))
r = lc.check(FakeMod(m))
check("with no .bat and no launcher, a .cfg carrying mod = is what a shortcut would pass",
      r["routes"] and r["routes"][0]["kind"] == "cfg" and r["verdict"] == "ready")
g, m = game("nothing")
check("a mod with no way to start at all says so", lc.check(FakeMod(m))["verdict"] == "none")

# ---- 3) the installed mods ----------------------------------------------------------
print("\n3) the installed mods")
for name in ("Divide_and_Conquer_EUR", "ROCSS"):
    if not (MODS / name).is_dir():
        continue
    r = lc.check(FakeMod(MODS / name))
    hows = [x["how"] for x in r["routes"] if x["ok"]]
    check(f"{name} starts ({r['verdict']}): {', '.join(hows)}", r["verdict"] in ("ready", "warn") and hows)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
