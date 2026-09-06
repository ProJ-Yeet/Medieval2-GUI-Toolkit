"""Take the screenshots the README shows, from the real tool.

    python main/dev/docs/screenshots.py
    python main/dev/docs/screenshots.py --mod Third_Age_Reforged --only home bmdb

Starts the toolkit on a port of its own, drives a headless Chromium through
each major screen, and writes a PNG per screen into ``main/docs/images/``.
Nothing is written to any mod: every shot is a screen the tool has *read* into,
and the two that involve a dialog (the duplicate scan and the model viewer) are
both read-only.

Why a script rather than hand-taken shots: they go stale. Six of these screens
change every phase, and a README carrying a picture of a version that no longer
exists is worse than one carrying no picture, because a reader cannot tell.
Re-running this after a release is one command, so there is no excuse.

Needs Playwright with Chromium::

    pip install playwright
    python -m playwright install chromium
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "images"

#: 1600x1000 is the shape a README picture is actually looked at in: wide enough
#: that the toolkit's two- and three-column screens are not folded into one, and
#: short enough that GitHub does not scale it down to unreadable.
VIEWPORT = {"width": 1600, "height": 1000}

#: Each shot: the file it writes, the mode to switch into, and a bit of the page
#: that must be on screen before the shutter goes. Waiting on a *selector* rather
#: than a sleep is what keeps these honest - a screen that failed to load takes a
#: picture of the failure instead of quietly shooting an empty frame.
SHOTS = [
    dict(name="home", title="Home",
         setup="setAppMode('home')", wait=".modcard, .mod, .homegrid"),
    # The two unit grids draw a card per unit, each converted from TGA on first
    # sight, so the shutter waits for the conversions to land rather than
    # photographing a wall of empty frames.
    dict(name="unit-editor", title="Unit Editor",
         setup="setAppMode('edit')", wait=".unit, .ucard, .grid", settle=9000),
    dict(name="unit-transfer", title="Unit Transfer",
         setup="setAppMode('transfer')", wait=".unit, .ucard, .grid", settle=9000),
    dict(name="bmdb", title="BMDB + Sprites",
         setup="setAppMode('bmdb')", wait=".dbrow"),
    dict(name="bmdb-3d", title="Model viewer",
         setup="setAppMode('bmdb')", wait=".dbrow",
         then="const r=state.bmdb.entries.find(e=>e.lods>0&&e.skins>0);"
              "v3Open(state.src, r.name);",
         then_wait="#v3canvas", settle=6000),
    dict(name="bmdb-duplicates", title="Duplicate entries",
         setup="setAppMode('bmdb')", wait=".dbrow",
         then="openDupes();", then_wait="#modal fieldset", settle=2500),
    dict(name="buildings", title="Buildings",
         setup="setAppMode('buildings')", wait=".faction-group, .bldcard"),
    dict(name="campaign-map", title="Campaign Map",
         setup="setAppMode('campmap')", wait="canvas", settle=9000),
    dict(name="factions", title="Factions",
         setup="setAppMode('factions')", wait=".trwrap"),
    dict(name="traits", title="Traits",
         setup="setAppMode('traits')", wait=".trwrap"),
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port: int, proc, timeout: float = 90) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            raise SystemExit(f"the server exited early (code {proc.returncode})")
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.4)
    raise SystemExit(f"the server never opened port {port}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mod", default="", help="which mod to open the screens on "
                                              "(default: whatever the tool lists first)")
    ap.add_argument("--only", nargs="*", default=[], help="just these shot names")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed:\n"
                         "  pip install playwright\n"
                         "  python -m playwright install chromium")

    shots = [s for s in SHOTS if not args.only or s["name"] in args.only]
    if not shots:
        raise SystemExit(f"no shot named {args.only}")
    OUT.mkdir(parents=True, exist_ok=True)

    port = args.port or free_port()
    print(f"starting the toolkit on port {port}")
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py"), "--serve", "--no-browser",
         "--port", str(port)],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_port(port, proc)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_function("typeof setAppMode === 'function'", timeout=60000)
            page.wait_for_function("state && state.src", timeout=60000)
            # Which mod is on screen is remembered in settings, so picking one
            # here would quietly change the user's own last-opened mod. Put it
            # back on the way out.
            was = page.evaluate("[state.settings.last_source, state.settings.last_dest]")
            if args.mod:
                _pick_mod(page, args.mod)
            mod = page.evaluate("state.src")
            print(f"showing {mod}")

            for shot in shots:
                took = _one(page, shot)
                print(f"  {'ok  ' if took else 'MISS'} {shot['name']}.png"
                      f"  {shot['title']}")
            if args.mod and was[0]:
                page.evaluate("([s, d]) => api.post('/api/settings',"
                              "{last_source: s, last_dest: d})", was)
                page.wait_for_timeout(500)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"\nwritten to {OUT}")
    return 0


def _pick_mod(page, mod: str) -> None:
    """Choose the mod the way a person does, through the picker.

    Assigning ``state.src`` looks like it works and does not: the toolbar's
    select still shows the old mod, and every mode reloads from the picker's
    value the moment it renders. So the change goes through the element, and
    then this waits for the load it starts rather than guessing at a delay.

    Not a click, though: the picker is hidden on Home, which is where the tool
    opens, and Playwright will not operate a control it cannot see. Setting the
    value and firing the event is the same thing the control would have done.
    """
    page.evaluate("""m => {
        const s = document.getElementById('srcSel');
        s.value = m;
        s.dispatchEvent(new Event('change'));
    }""", mod)
    page.wait_for_function("m => state.src === m", arg=mod, timeout=60000)
    page.wait_for_timeout(1500)


def _trim(path: Path) -> None:
    """Cut the dead band off the bottom, if there is one.

    Every screen is shot at the same height so they sit together on a page, but
    Home fills a third of it and the Unit Editor fills all of it. Trimming the
    rows that are one flat colour keeps each picture as tall as it has content
    and no taller, which is what stops the short screens reading as broken.
    """
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(path).convert("RGB")
    w, h = im.size
    bottom = h
    while bottom > 200:
        row = im.crop((0, bottom - 1, w, bottom))
        # None means "more colours than the cap", which is the opposite of the
        # flat row being looked for. Reading that as flat trimmed every shot
        # down to a 224-pixel sliver, so it is spelled out rather than folded
        # into a falsy default.
        colours = row.getcolors(maxcolors=4)
        if colours is None or len(colours) > 1:
            break
        bottom -= 1
    if bottom < h - 8:
        im.crop((0, 0, w, min(h, bottom + 24))).save(path)


def _one(page, shot) -> bool:
    """One screen. Returns False rather than raising when it will not load.

    A mod with no campaign map, or a build with that mode switched off, is an
    ordinary thing to run this against - the other nine shots are still worth
    having, so a missing screen is reported and skipped rather than taking the
    run down with it.
    """
    from playwright.sync_api import TimeoutError as PwTimeout
    try:
        # A dialog left open by the shot before this one sits over whatever
        # comes next: the campaign map's first picture was the duplicate scan
        # floating over a map nobody could see. Modes do not close it, so this
        # does, every time, rather than only after the shots that open one.
        page.evaluate("if (typeof closeModal === 'function') closeModal();")
        page.evaluate(shot["setup"])
        page.wait_for_selector(shot["wait"], timeout=60000)
        if shot.get("then"):
            page.evaluate(shot["then"])
            page.wait_for_selector(shot["then_wait"], timeout=60000)
        page.wait_for_timeout(shot.get("settle", 1200))
        out = OUT / f"{shot['name']}.png"
        page.screenshot(path=str(out))
        _trim(out)
        return True
    except PwTimeout:
        return False
    except Exception as exc:                       # a mode that is not in this build
        print(f"       ({exc.__class__.__name__}: {str(exc).splitlines()[0][:80]})")
        return False


if __name__ == "__main__":
    raise SystemExit(main())
