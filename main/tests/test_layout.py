"""The layout at every interface size - Phase 90.

The sweep itself (every screen at 1280, 1600 and 1920 px times 60, 80, 100 and
125%, and 375 px at 100%) is a browser measurement, recorded in ROADMAP.md
under Phase 90. What is held here is what keeps it true in the source:

    1  no breakpoint is a media query: each is a container query on the body,
       which measures the page as zoomed, not the window
    2  the Minor Files tab strip is one row that scrolls in itself, with the
       file's path on a line of its own, outside it
    3  the "+ New ..." buttons sit in a row, the size of their labels
    4  the list and the record stack at one shared width, and the filters go
       above the list on a page that narrow

    python -m tests.test_layout
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))

print("\n1) breakpoints that see the page")
check("no @media (max-width) left: Settings' zoom is invisible to one",
      not re.search(r"@media\s*\(\s*max-width", css))
n = len(re.findall(r"@container page \(max-width:", css))
check(f"every breakpoint is a container query on the page ({n})", n >= 13)
check("and the body is that container", "body{container:page/inline-size}" in css)

print("\n2) the tab strip")
check("the strip scrolls sideways inside itself",
      re.search(r"\.mftabs\{overflow-x:auto", css) is not None)
check("and a tab keeps its width and its one line",
      ".mftab{flex:0 0 auto;white-space:nowrap}" in css)
core = _webtext.read(ROOT / "web" / "js" / "core.js")
body = core[core.index("function minorTabsHtml"):core.index("function mfTabsReveal")]
check("the path is its own line, after the strip closes, not inside it",
      body.index("</div>${note?") < body.index('class="mfpath'))

print("\n3) the action buttons")
for f in ("traits", "ancillaries", "guilds", "minorfiles"):
    src = _webtext.read(ROOT / "web" / "js" / f"{f}.js")
    bare = [m.start() for m in re.finditer(r'<button class="trnew"', src)
            if 'class="trnewrow"' not in src[max(0, m.start() - 200):m.start()]
            and "margin:4px 4px 0 0" not in src[m.start():m.start() + 120]]
    check(f"{f}.js: every + New button is in a row of its own size", not bare)
check("the row does not stretch them", ".trnewrow .trnew{flex:0 0 auto}" in css)

print("\n4) stacking")
check("list and record stack at one width for every screen built on them",
      re.search(r"@container page \(max-width:760px\)\{\s*\.trwrap\{flex-direction:column", css)
      is not None)
check("the filters go above the list on a narrow page",
      re.search(r"@container page \(max-width:600px\)\{\s*\.layout\{flex-direction:column", css)
      is not None)
check("a wide table scrolls in its own box", ".smxtab{display:block;max-width:100%;overflow-x:auto}" in css)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
