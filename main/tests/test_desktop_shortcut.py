"""Install-Dependencies.bat's desktop shortcut (2026-11-26).

It asks in a popup, makes a shortcut to the launcher wearing the toolkit's
icon on a yes, makes nothing on a no, and refreshes one already there without
asking. The real .bat runs from a copy of the repository's layout, with
UT_SHORTCUT_DIR for the desktop and UT_SHORTCUT_ANSWER for the popup.
Windows only: it needs cmd, PowerShell and WScript.Shell.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests import _tmp  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


if os.name != "nt":
    print("  (skipped: Windows only)")
    sys.exit(0)

NO_WINDOW = 0x08000000
base = Path(_tmp.mkdtemp(prefix="ut_shortcut_"))
repo = base / "Tool's folder"          # a quote in the path must not break it
(repo / "main" / "web" / "img").mkdir(parents=True)
shutil.copy(ROOT.parent / "Install-Dependencies.bat", repo)
(repo / "Launch-Medieval2-GUI-Toolkit.bat").write_text("@echo off\r\n", encoding="utf-8")
shutil.copy(ROOT / "web" / "img" / "guitoolkit.ico", repo / "main" / "web" / "img")
desk = base / "desk"
desk.mkdir()
lnk = desk / "Medieval 2 GUI Toolkit.lnk"


def run(answer):
    env = dict(os.environ, UT_SHORTCUT_DIR=str(desk), UT_SHORTCUT_ANSWER=answer)
    r = subprocess.run(["cmd", "/c", str(repo / "Install-Dependencies.bat")], input="\r\n" * 5,
                       capture_output=True, text=True, env=env, timeout=300,
                       creationflags=NO_WINDOW)
    return r.stdout


def read_lnk():
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:L);"
          "$s.TargetPath; $s.IconLocation; $s.WorkingDirectory")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                       env=dict(os.environ, L=str(lnk)), creationflags=NO_WINDOW)
    return r.stdout.splitlines()


try:
    out = run("no")
    check("a no makes no shortcut", not lnk.exists() and "No desktop shortcut made" in out)

    out = run("yes")
    check("a yes makes the shortcut", lnk.exists() and "shortcut is on your desktop" in out)
    target, icon, work = (read_lnk() + ["", "", ""])[:3]
    check("it starts the launcher", Path(target) == repo / "Launch-Medieval2-GUI-Toolkit.bat")
    check("it wears the toolkit's icon",
          icon.lower() == str(repo / "main" / "web" / "img" / "guitoolkit.ico").lower() + ",0")
    check("it runs in the toolkit's folder", Path(work) == repo)

    lnk.write_bytes(b"")                 # stands for a stale one; a no must not stop the refresh
    out = run("no")
    target = (read_lnk() + [""])[0]
    check("one already there is refreshed without asking",
          "shortcut is on your desktop" in out and Path(target) == repo / "Launch-Medieval2-GUI-Toolkit.bat")
finally:
    shutil.rmtree(base, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
