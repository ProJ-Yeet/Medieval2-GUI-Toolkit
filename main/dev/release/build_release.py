"""Build the shareable release zip: the tool plus a Python runtime, ready to run.

    python main/dev/release/build_release.py          # portable (bundles Python + Pillow)
    python main/dev/release/build_release.py --no-runtime   # code only; needs Python there
    python main/dev/release/build_release.py --version v1.4.0   # name the zip
    python main/dev/release/build_release.py --no-vanilla-ui    # slim, NOT for a release

The point is that the person you send it to installs nothing. The zip carries
Python's official *embeddable* distribution with Pillow already in it, so they
unzip and double-click `Launch-Medieval 2 GUI Toolkit.bat`.

Only the bare minimum ships: `app.py`, `transfer_cli.py`, `Full Cleaner.bat`,
`unittransfer/`, `web/`, the launcher, `Install-Dependencies.bat` and a README.
Never `config/` (personal settings, backups and the transfer log), `.cache/`,
`tests/`, `graphify-out/` or `__pycache__` - shipping `config/` would hand over
someone else's mod paths and undo history.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
#: The launcher and the dependency installer are the two files a person
#: double-clicks, so they live at the top of the repo rather than under main/.
#: Both are copied into the zip, where the layout is flat again.
REPO = ROOT.parent
DIST = ROOT / "dist"
BUILD_CACHE = ROOT / ".cache" / "build"

APP_NAME = "Medieval2-GUI-Toolkit"
# The embeddable build must match the Python that resolves the Pillow wheel.
PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
PY_TAG = f"{sys.version_info.major}{sys.version_info.minor}"
EMBED_URL = (f"https://www.python.org/ftp/python/{PY_VERSION}/"
             f"python-{PY_VERSION}-embed-amd64.zip")

#: everything the tool needs at runtime, and nothing else
#: Full Cleaner.bat is not run by the tool any more - unittransfer/cleaner.py
#: deletes export_units.txt.strings.bin itself instead. It still ships so anyone
#: who wants the full sweep can copy it into a mod and run it by hand.
INCLUDE_FILES = ("app.py", "transfer_cli.py", "Full Cleaner.bat")
#: vendor/ carries nvcompress.exe + its DLLs (NVIDIA Texture Tools 2.0), which
#: Sprites mode shells out to for TGA -> DXT5. ~1MB, and without it the convert
#: step can't run at all - so it ships rather than being a manual download.
#: It used to be `tools/`, which also held seven scripts no release has any use
#: for and which went out in every zip because they happened to sit next to the
#: binary. The developer scripts are under dev/ now and nothing here reaches them.
INCLUDE_DIRS = ("unittransfer", "web", "vendor")
#: The packed vanilla building art Buildings mode falls back to. SHIPS BY
#: DEFAULT and must keep doing so: without it, Buildings mode shows a placeholder
#: wherever a mod doesn't ship its own icon, which is most of them, and the
#: release looks broken to the person who unzipped it. It used to be opt-in
#: behind a flag and was then forgotten for four releases running (2.1.1 to
#: 2.1.4 all went out at ~19 MB instead of ~51 MB) - a flag you have to remember
#: is not a decision, it is a trap. `--no-vanilla-ui` still exists for a
#: deliberately slim build; nothing routine should pass it.
BUNDLED_DIRS = ("vanilla_ui",)
#: never ship these, whatever they contain
EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def rmtree(path: Path) -> None:
    """Delete a staging tree even when Windows is being difficult.

    A previous build's runtime may still have read-only files or a handle that
    hasn't been released (antivirus, Explorer preview, or a subprocess we only
    just waited on - Windows can keep the handle alive for a moment after the
    process exits), so clear the read-only bit and retry a few times rather than
    failing the build. If it still won't go, say so here, with the real OS
    error, instead of letting the leftovers surface later as a confusing
    "refusing to package".
    """
    import os
    import stat

    # The first failure of an attempt is the cause (the locked file); the ones
    # after it are its knock-on effects ("directory not empty"), so keep the first.
    first_error: OSError | None = None

    def note(err):
        nonlocal first_error
        if first_error is None and isinstance(err, OSError):
            first_error = err

    def on_error(func, p, exc):
        note(exc[1] if isinstance(exc, tuple) else exc)
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError as e:
            note(e)

    # onerror is deprecated from 3.12 and gone in 3.14; onexc replaces it.
    handler = ({"onexc": on_error} if sys.version_info >= (3, 12)
               else {"onerror": on_error})

    for attempt in range(5):
        if not path.exists():
            return
        first_error = None
        shutil.rmtree(path, **handler)
        if not path.exists():
            return
        time.sleep(0.5 * (attempt + 1))
    detail = f"\n  {first_error}" if first_error else ""
    raise SystemExit(
        f"could not remove {path} - close anything using it and retry{detail}")


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if any(part in EXCLUDE_NAMES for part in p.parts):
            continue
        if p.is_dir():
            continue
        target = dst / p.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
    return n


def stage_app(stage: Path, with_vanilla_ui: bool = True) -> None:
    """Copy the tool's own files into the staging folder.

    ``with_vanilla_ui`` defaults to True on purpose - see :data:`BUNDLED_DIRS`.
    A missing ``vanilla_ui/`` is a hard failure rather than a shrug, because the
    whole point is that a release can never quietly go out without it.
    """
    for name in INCLUDE_FILES:
        shutil.copy2(ROOT / name, stage / name)
    total = len(INCLUDE_FILES)
    for name in INCLUDE_DIRS:
        total += _copy_tree(ROOT / name, stage / name)
    log(f"app files: {total}")
    if not with_vanilla_ui:
        log("vanilla UI: LEFT OUT (--no-vanilla-ui) - Buildings mode will show "
            "placeholders for any icon a mod doesn't ship")
        return
    for name in BUNDLED_DIRS:
        src = ROOT / name
        if not src.is_dir():
            # Not "skipped": this is the failure the flag-shaped version used to
            # let through silently, and a half-built release is worse than none.
            raise SystemExit(
                f"BUILD STOPPED: {name}/ is missing from {ROOT}.\n"
                "  It ships in every release - Buildings mode falls back to it\n"
                "  for the icons a mod doesn't provide. Restore it, or pass\n"
                "  --no-vanilla-ui if you really mean to build without it.")
        n = _copy_tree(src, stage / name)
        size = sum(p.stat().st_size for p in (stage / name).rglob("*") if p.is_file())
        log(f"vanilla UI: {n} files, {size / 1e6:.0f} MB")


def fetch_embed_zip() -> Path:
    """Download (and cache) Python's embeddable distribution."""
    BUILD_CACHE.mkdir(parents=True, exist_ok=True)
    dest = BUILD_CACHE / EMBED_URL.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size > 1_000_000:
        log(f"runtime: using cached {dest.name}")
        return dest
    log(f"runtime: downloading {EMBED_URL}")
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(EMBED_URL, timeout=120) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh)
    tmp.replace(dest)
    log(f"runtime: downloaded {dest.stat().st_size / 1e6:.1f} MB")
    return dest


def stage_runtime(stage: Path) -> None:
    """Unpack the embeddable Python and install Pillow into it."""
    runtime = stage / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(fetch_embed_zip()) as z:
        z.extractall(runtime)

    # The embeddable build REPLACES sys.path with whatever its `._pth` lists, and
    # ships with site-packages off. Every entry is relative to runtime/, so:
    #   .                  -> runtime/ itself
    #   ..                 -> the app folder, where app.py and unittransfer/ live
    #   Lib\site-packages  -> Pillow, installed below
    # Without `..` the app can't import its own package; without `import site`
    # site-packages is never added. Write the file outright rather than patching.
    for pth in runtime.glob("python*._pth"):
        pth.write_text(
            "\n".join([f"python{PY_TAG}.zip", ".", "..", "Lib\\site-packages",
                       "", "import site", ""]),
            encoding="utf-8")
        log(f"runtime: wrote {pth.name} (app folder + site-packages on sys.path)")

    site = runtime / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    log("runtime: installing Pillow…")
    res = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "--target", str(site),
         "--only-binary=:all:", "Pillow"],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("pip install Pillow failed:\n" + res.stdout + res.stderr)
    # pip's bookkeeping is dead weight in a shipped runtime
    for junk in list(site.glob("*.dist-info")) + list(site.glob("*.egg-info")):
        shutil.rmtree(junk, ignore_errors=True)
    for junk in site.rglob("__pycache__"):
        rmtree(junk)

    ok = subprocess.run([str(runtime / "python.exe"), "-c",
                         "import PIL;from PIL import Image;print(PIL.__version__)"],
                        capture_output=True, text=True)
    if ok.returncode != 0:
        raise SystemExit("bundled runtime cannot import Pillow:\n" + ok.stdout + ok.stderr)
    log(f"runtime: Pillow {ok.stdout.strip()} verified inside the bundle")

    size = sum(p.stat().st_size for p in runtime.rglob("*") if p.is_file())
    log(f"runtime: {size / 1e6:.1f} MB")


def smoke_test(stage: Path, portable: bool) -> None:
    """Run the staged copy's own preflight - catches a broken bundle before it ships.

    Uses ``--check`` so nothing is served and no browser opens. It runs against
    the staged folder, so a missing file or an unimportable package fails the
    build instead of the person who receives the zip.
    """
    exe = str(stage / "runtime" / "python.exe") if portable else sys.executable
    res = subprocess.run([exe, "app.py", "--check"], cwd=str(stage),
                         capture_output=True, text=True, timeout=120)
    tail = (res.stdout + res.stderr).strip().splitlines()[-12:]
    if res.returncode != 0 or "Startup checks passed" not in (res.stdout + res.stderr):
        raise SystemExit("staged build failed its own startup checks:\n  "
                         + "\n  ".join(tail))
    log("smoke test: the staged build passes its own startup checks")


#: paths that must never end up in a shipped zip. `config/` is the dangerous one:
#: running the staged build (the smoke test does) creates it, and it holds the
#: builder's own mod paths, transfer log and backups.
FORBIDDEN_DIRS = ("config", "__pycache__", ".cache", "dist", "tests", "graphify-out")
FORBIDDEN_SUFFIXES = (".log", ".pyc", ".pyo")
#: transcripts the launcher/troubleshooter write next to themselves at runtime
FORBIDDEN_NAMES = ("launcher-output.txt", "troubleshoot-output.txt")


def clean_stage(stage: Path) -> None:
    """Remove anything the build or the smoke test generated in the staging tree.

    The smoke test runs the staged runtime's own python.exe, which writes
    __pycache__ next to the packages it imports; Windows can still hold a handle
    on those folders for a moment after that process exits. Delete through
    ``rmtree`` so it retries - with ignore_errors the failure was silent and only
    showed up as assert_clean refusing to package.
    """
    removed = 0
    for name in FORBIDDEN_DIRS:
        for d in list(stage.rglob(name)):
            if d.is_dir():
                rmtree(d)
                removed += 1
    for p in list(stage.rglob("*")):
        if p.is_file() and (p.suffix.lower() in FORBIDDEN_SUFFIXES
                            or p.name in FORBIDDEN_NAMES):
            p.unlink(missing_ok=True)
            removed += 1
    if removed:
        log(f"cleaned {removed} generated item(s) out of the staging folder")


def assert_clean(stage: Path) -> None:
    """Refuse to ship a zip containing personal or generated files."""
    bad = []
    for p in stage.rglob("*"):
        rel = p.relative_to(stage)
        if any(part in FORBIDDEN_DIRS for part in rel.parts) or (
                p.is_file() and (p.suffix.lower() in FORBIDDEN_SUFFIXES
                                 or p.name in FORBIDDEN_NAMES)):
            bad.append(str(rel))
    if bad:
        raise SystemExit("refusing to package - these must not ship:\n  "
                         + "\n  ".join(bad[:20])
                         + (f"\n  …and {len(bad) - 20} more" if len(bad) > 20 else ""))
    log("verified: no config/, logs or caches in the package")


PORTABLE_BAT = r"""@echo off
setlocal
title Medieval 2 GUI Toolkit
cd /d "%~dp0"

rem Everything needed is in this folder - no Python install required. The window
rem shows the startup checks and the unit-card conversions, then closes itself
rem once the server is up (turn on Settings -> Show console window to keep it).
rem
rem It stays open, with the reason, whenever anything is off:
rem   exit 3 = the server started but no browser opened, so this window is the
rem            only place the address is visible.
rem   exit 4 = a DIFFERENT build of the toolkit already holds the port, so this
rem            one was not started and no window was opened.
rem   other  = a real failure.
rem Either way the full detail is in config\server.log.

if not exist "runtime\python.exe" (
    echo.
    echo The bundled Python runtime is missing.
    echo Unzip the WHOLE folder somewhere first - don't run this from inside the zip.
    echo Right-click the .zip -^> "Extract All...", then run this from the extracted folder.
    echo.
    pause
    exit /b 1
)

"runtime\python.exe" app.py %*
set "RC=%errorlevel%"

if "%RC%"=="0" (
    echo.
    echo  Started. This window closes in a few seconds.
    timeout /t 6 >nul 2>&1
    goto :done
)

echo.
if "%RC%"=="3" (
    echo ============================================================
    echo  Medieval 2 GUI Toolkit IS RUNNING - but no browser opened by itself.
    echo ============================================================
    echo.
    echo  Open this address in your browser:   http://127.0.0.1:8756/
    echo.
    echo  Keep this window open while you use the tool, or use the Quit
    echo  button in the tool's settings to stop it.
) else if "%RC%"=="4" (
    rem Code 4 = a DIFFERENT build of the toolkit is already on the port. The
    rem message box and the lines above name both builds and their folders; this
    rem window must not suggest the port is merely "taken", because the thing
    rem holding it is the tool itself and reopening it would have handed over the
    rem wrong build - a 2.x release has the Campaign Map off the menu, a beta has
    rem it on, and both look perfectly healthy.
    echo ============================================================
    echo  Another BUILD of the Medieval 2 GUI Toolkit is already running.
    echo ============================================================
    echo.
    echo  Nothing was started, and no window was opened - the one already
    echo  running is a different copy, and showing it would have given you a
    echo  build you did not launch.
    echo.
    echo  The lines above name both: what is running, and what you launched.
    echo.
    echo  To use the one you just launched, stop the other first: open
    echo  http://127.0.0.1:8756/ and press Quit in its Settings ^(gear icon^),
    echo  then run this again.
    echo.
    echo  To run both at once, give this one its own port:
    echo     "Launch-Medieval 2 GUI Toolkit.bat" --port 8757
) else (
    echo ============================================================
    echo  Medieval 2 GUI Toolkit exited with an error ^(code %RC%^).
    echo ============================================================
    echo.
    echo  * Port 8756 taken?   run:  "Launch-Medieval 2 GUI Toolkit.bat" --port 8757
    echo  * Wrong mods folder? set it in the tool's settings ^(gear icon^)
    echo  * Blocked by antivirus/SmartScreen? unblock the folder and retry.
    echo.
    echo  Full log:  config\server.log
    echo  For a diagnostic you can share, run:  Troubleshoot.bat
)
echo.
pause

:done
endlocal
exit /b %RC%
"""

TROUBLESHOOT_BAT = r"""@echo off
setlocal
title Medieval 2 GUI Toolkit - Troubleshoot
cd /d "%~dp0"

rem Run this when "Launch-Medieval 2 GUI Toolkit.bat" doesn't work. It never closes on its own,
rem and writes everything to troubleshoot-output.txt to send on for help.

echo ============================================================
echo  Medieval 2 GUI Toolkit - diagnostic
echo ============================================================
echo.

echo ==== %DATE% %TIME% ==== > "troubleshoot-output.txt"

echo [1/4] Folder contents >> "troubleshoot-output.txt"
dir /b >> "troubleshoot-output.txt" 2>&1

echo [2/4] Bundled runtime >> "troubleshoot-output.txt"
if exist "runtime\python.exe" (
    echo runtime\python.exe FOUND >> "troubleshoot-output.txt"
    "runtime\python.exe" -c "import sys;print(sys.version);print(sys.executable)" >> "troubleshoot-output.txt" 2>&1
    "runtime\python.exe" -c "import PIL;print('Pillow',PIL.__version__)" >> "troubleshoot-output.txt" 2>&1
) else (
    echo runtime\python.exe MISSING - the folder was not fully extracted >> "troubleshoot-output.txt"
)

echo [3/4] Startup checks >> "troubleshoot-output.txt"
if exist "runtime\python.exe" (
    "runtime\python.exe" app.py --check >> "troubleshoot-output.txt" 2>&1
)

echo [4/4] Recent server log >> "troubleshoot-output.txt"
if exist "config\server.log" (
    powershell -NoProfile -Command "Get-Content 'config\server.log' -Tail 60" >> "troubleshoot-output.txt" 2>&1
) else (
    echo config\server.log does not exist >> "troubleshoot-output.txt"
)

type "troubleshoot-output.txt"

echo.
echo ============================================================
echo  Saved to troubleshoot-output.txt - send that file on for help.
echo ============================================================
echo.
pause
endlocal
"""

README = """Medieval 2 GUI Toolkit - edit Medieval II: Total War mods
=======================================================

Getting started
---------------
1. Unzip this whole folder somewhere (Desktop is fine). Don't run it from
   inside the zip.
2. Double-click **Launch-Medieval 2 GUI Toolkit.bat**.
3. A window appears with the startup checks, then your browser opens the tool.
   The window closes on its own once everything is up.
4. First run only: click the gear icon and point it at your Medieval II
   install folder - the one containing a `mods` folder.

{runtime_note}

Using it
--------
* Pick a **From** mod and a **To** mod at the top.
* Browse units by faction, filter by type/class/era, or search.
* Click a unit, then **Transfer to <mod>**.
* Set the options, hit **Preview** to see exactly what will change, then
  **Apply**.
* Every transfer is undoable from the clock icon - it backs up each file it
  touches first.

The other modes
---------------
The dropdown in the top-left corner switches what you are working on:

* **Unit Editor** - one mod instead of two. Click a unit to edit every EDU
  field, its name and description, the battle-model entries it uses, to build a
  new unit from it, or to delete it.
* **BMDB Editor** - the mod's whole battle_models.modeldb. Browse and edit any
  entry, even ones no unit points at, and use **Clean up BMDB** to find the
  entries nothing references, the soldier-only entries that could share an
  existing model, and the files under unit_models nothing mentions. Nothing is
  deleted: you choose a folder and everything ticked is moved there, laid out
  like the mod itself so it can be pasted straight back - and the whole removal
  is undoable from the clock icon like anything else.
* **Unit Sounds** - the mod's voice bank, which decides what a unit's soldiers
  shout when you select them. Three tabs: units with no voice entry, units with
  one, and entries whose unit no longer exists. Pick the unit to copy the
  sounds from and the row is ready; **Set all shown to copy** does a whole
  filtered list at once. It writes the voice bank AND the matching accent /
  voice_type lines in the EDU, because a unit is silent unless those two agree.
* **Buildings** - the mod's export_descr_buildings.txt, as a picture grid of
  every building line. Open one and you get a tab per level with its icons, its
  name and description, its cost, build time, material and settlement size, its
  capabilities, its upgrade path, and - the main event - its recruitment: which
  units it trains, the starting pool, the per-turn refill, the cap, the starting
  experience and the conditions on each, as rows or as a card grid. Add or
  remove units, filter the list to one faction, and hit the pencil on any unit
  to jump straight into the Unit Editor and back again with everything you had
  typed still there.

  Requirements are edited as a list of conditions rather than typed: factions
  come as a checklist of real in-game names with the code name in brackets,
  events carry their title out of historic_events.txt, and hidden resources and
  religions show which regions they actually apply to. If you let a faction
  recruit a unit it doesn't own, the editor says so and saving puts it right.

  The upgrade path is drawn as a graph - lines branch, and one of DaC's is a
  single root with everything hanging off it - and every building in it is
  clickable.

  Building icons are per culture, so there is a culture picker in the sidebar.
  Mods ship only the art they changed, so anything missing falls back to vanilla
  art if you have it (a `vanilla_ui` folder next to the app, or the
  `vanilla_ui_root` setting), then to another culture's, then to a drawn
  placeholder. The badge on each picture says which you are looking at.

What gets carried across
------------------------
The unit's EDU entry, its localised name and description, its battle models and
all their meshes/textures/sprites, its unit card and info card, its mount, its
projectile, its voice, and - for artillery - its full siege engine: the
descr_engines block, the engine skeletons and animations, the meshes, bone maps,
collision models, and the textures baked inside those meshes.

Things it warns you about rather than guessing: missing animations, files the
destination mod overrides, and effects/sounds it can't port.

Stopping it
-----------
Close the browser tab, or use the Quit button in the tool's settings.

Something went wrong?
---------------------
**The window opened and closed and nothing happened.**
That usually means the tool started fine but your browser didn't open by
itself. The tool is still running - open this address manually:

    http://127.0.0.1:8756/

If that page loads, everything is working. (Newer builds keep the window open
and tell you when this happens.)

**Still stuck?** Run **Troubleshoot.bat**. It never closes on its own, prints
what it finds, and saves `troubleshoot-output.txt` - send that file on for help.

Every run is logged in detail to `config\\server.log` (or, if this folder can't
be written, to `%LOCALAPPDATA%\\UnitTransfer\\server.log`).

To re-run just the startup checks:

    {check_cmd}
"""


def write_docs(stage: Path, portable: bool) -> None:
    (stage / "Launch-Medieval 2 GUI Toolkit.bat").write_text(
        PORTABLE_BAT if portable else (REPO / "Launch-Medieval2-GUI-Toolkit.bat").read_text(
            encoding="utf-8"),
        encoding="utf-8")
    if portable:
        (stage / "Troubleshoot.bat").write_text(TROUBLESHOOT_BAT, encoding="utf-8")
    # Ship the standalone installer either way: even the portable build's
    # bundled runtime can be missing/blocked (antivirus, partial extract), and
    # someone running from source needs it as the auto-install fallback.
    (stage / "Install-Dependencies.bat").write_text(
        (REPO / "Install-Dependencies.bat").read_text(encoding="utf-8"),
        encoding="utf-8")
    note = ("Nothing else to install - Python and the image library are already\n"
            "inside this folder (`runtime\\`)."
            if portable else
            "This build does NOT include Python. Run Install-Dependencies.bat first:\n"
            "it installs Python for you (downloaded from python.org, your user only,\n"
            "no administrator prompt, added to PATH) along with the image library.\n"
            "After that, Launch-Medieval 2 GUI Toolkit.bat works on its own.")
    cmd = ("runtime\\python.exe app.py --check" if portable else "py app.py --check")
    (stage / "README.txt").write_text(
        README.format(runtime_note=note, check_cmd=cmd), encoding="utf-8")


def assert_bundled(out: Path, expect_vanilla_ui: bool) -> None:
    """Read the finished zip back and check the big optional payload is IN it.

    The last check before the file is handed to somebody, and it reads the
    artefact rather than the staging folder - every earlier step could be right
    and the zip still wrong. This exists because four releases in a row shipped
    without the vanilla UI and nothing in the build said a word: the size on
    screen was the only tell, and nobody reads a size.
    """
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    for name in BUNDLED_DIRS:
        prefix = f"{APP_NAME}/{name}/"
        n = sum(1 for x in names if x.startswith(prefix))
        if expect_vanilla_ui and not n:
            raise SystemExit(
                f"refusing to ship {out.name}: it contains no {name}/.\n"
                "  Buildings mode falls back to that art for every icon a mod\n"
                "  doesn't provide, so the release would look broken.")
        log(f"verified: {name}/ is in the zip ({n} files)"
            if n else f"verified: {name}/ deliberately left out")


def make_zip(stage: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    files = [p for p in sorted(stage.rglob("*")) if p.is_file()]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, Path(APP_NAME) / p.relative_to(stage))
    log(f"zipped {len(files)} files")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-runtime", action="store_true",
                    help="don't bundle Python (target PC must have it installed)")
    ap.add_argument("--out", default=None, help="output .zip path")
    ap.add_argument("--version", default=None,
                    help="name the build for a release (e.g. v1.4.0) instead of today's date")
    ap.add_argument("--no-vanilla-ui", action="store_true",
                    help="build WITHOUT vanilla_ui/ (~35 MB). Not for releases: "
                         "Buildings mode then shows a placeholder for every icon "
                         "a mod doesn't ship")
    args = ap.parse_args(argv)
    portable = not args.no_runtime

    # A release asset wants to say which version it is; a throwaway build only
    # needs to say when it was made.
    stamp = args.version or time.strftime("%Y%m%d")
    name = f"{APP_NAME}-{stamp}" + ("" if portable else "-noruntime")
    stage = DIST / name
    print(f"Building {name} ({'portable' if portable else 'code only'})")
    if stage.exists():
        rmtree(stage)
    stage.mkdir(parents=True)

    stage_app(stage, with_vanilla_ui=not args.no_vanilla_ui)
    if portable:
        stage_runtime(stage)
    write_docs(stage, portable)
    smoke_test(stage, portable)
    clean_stage(stage)        # the smoke test just created config/ and __pycache__
    assert_clean(stage)

    out = Path(args.out) if args.out else DIST / f"{name}.zip"
    make_zip(stage, out)
    assert_bundled(out, expect_vanilla_ui=not args.no_vanilla_ui)
    print(f"\n{out}")
    print(f"  {out.stat().st_size / 1e6:.1f} MB - send this to anyone; "
          f"they unzip it and run 'Launch-Medieval 2 GUI Toolkit.bat'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
