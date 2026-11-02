"""The garrison in the settlement editor - Phase 96d.

descr_strat.txt keeps no garrison inside a settlement block: what defends a
town is the army of whoever stands on its tile. So the settlement editor lists
the characters on the settlement's tile, read off the markers layer's index,
and reaches the character editor for every change rather than growing a
second army editor. This runs the list in node against a stubbed page, where
the right answer is known, and checks the buttons reach the editor that
already writes armies.

    python -m tests.test_garrison
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS = ROOT / "web" / "js" / "stratedit.js"
src = _webtext.read(JS)
fn = re.search(r"function csGarrison\(\)\{.*?\n\}\n", src, re.S).group(0)

print("\n== 1) who is in the settlement ==")
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ctx = {state: {}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const tiles = new Map([
  ['10,20', {tx: 10, ty: 20, items: [{kind: 'settlement', region: 'A'},
     {kind: 'character', name: 'Denethor', faction: 'sicily', roster: [{unit: 'Guard'}]},
     {kind: 'character', name: 'Faramir', faction: 'sicily', roster: []},
     {kind: 'port', region: 'A'}]}],
  ['11,20', {tx: 11, ty: 20, items: [{kind: 'character', name: 'Outside'}]}]]);
const man = {height: 40, regions: [{name: 'A', settlement: [10, 20]}, {name: 'B', settlement: [30, 5]}]};
const out = {};
ctx.state = {cset: {region: 'A', d: {}}, cmap: {man}, cmk: {d: {}, byTile: tiles}};
out.a = ctx.csGarrison().map(it => it.name);
ctx.state.cset.region = 'B';
out.b = ctx.csGarrison();
ctx.state.cmk = {d: null, byTile: new Map()};
out.unread = ctx.csGarrison();
fs.writeFileSync(process.argv[3], JSON.stringify(out));
"""
node = shutil.which("node")
if not node:
    print("  -- node is not on PATH")
else:
    with tempfile.TemporaryDirectory(prefix="ut_garrison_") as tmp:
        t = Path(tmp)
        (t / "fn.js").write_text(fn, encoding="utf-8")
        (t / "h.js").write_text(HARNESS, encoding="utf-8")
        r = subprocess.run([node, str(t / "h.js"), str(t / "fn.js"), str(t / "out.json")],
                           capture_output=True, text=True)
        check("the harness runs", r.returncode == 0)
        got = json.loads((t / "out.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
        if r.returncode:
            print(r.stderr)
    check("everyone on the settlement's tile, and only the characters",
          got.get("a") == ["Denethor", "Faramir"])
    check("a character on the next tile is not in the garrison",
          "Outside" not in (got.get("a") or []))
    check("an empty settlement has nobody, not nothing to say", got.get("b") == [])
    check("before the markers are read the answer is 'not known', not 'nobody'",
          got.get("unread") is None)

print("\n== 2) the section, and where its buttons lead ==")
check("the settlement editor shows the garrison", "${csGarrisonHtml()}" in src)
check("Edit units opens the character editor at the army",
      re.search(r"function csGarrisonOpen\(it\)\{.*?cxOpen\(it\.faction\).*?cxPick\(i\).*?cxSection\('cxArmyEditor'\)",
                src, re.S) is not None)
check("Remove goes through the character editor's own delete, with its plan and confirm",
      re.search(r"function csGarrisonRemove\(i\)\{.*?cxSave\('delete'\)", src, re.S) is not None)
check("Add starts a general on the settlement's own tile, in game coordinates",
      re.search(r"function csGarrisonAdd\(\)\{.*?cxAdd\(\);.*?x\.w\.x = r\.settlement\[0\];"
                r".*?x\.w\.y = c\.man\.height - 1 - r\.settlement\[1\];", src, re.S) is not None)
mark = _webtext.read(ROOT / "web" / "js" / "campmark.js")
check("a fresh read of the campaign repaints the section",
      "if(state.cset && typeof csPaint === 'function') csPaint();" in mark)
check("no second army editor: the units are edited by cxArmyHtml alone",
      "cxUnitAdd" not in src and "army.push" not in src)

print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
