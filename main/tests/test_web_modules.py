"""The UI's split JavaScript: one global scope, so nothing may collide.

`web/index.html` loads `web/js/*.js` as plain <script> tags - no build step, no
module system. Everything therefore shares ONE global scope, which makes two
mistakes silent and expensive:

  * **a duplicate top-level name.** Whichever declaration loads last wins, and
    function declarations hoist, so the loser's callers quietly call the winner.
    This already happened once: the composer's `setMode` swallowed the burger
    menu's until it was renamed `setAppMode`.
  * **a file that stops being loaded.** Deleting a <script> tag, or adding a
    module file and forgetting the tag, leaves the page half-wired at runtime
    rather than failing at build time - there is no build.

So this test reads the script tags out of index.html and holds them against the
files on disk, then scans every top-level declaration for collisions. It needs
no game install and no browser. Node, if present, also syntax-checks each file.

    python -m tests.test_web_modules
"""
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WEB = ROOT / "web"
JS = WEB / "js"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


#: A top-level declaration starts at column 0 - everything nested is indented.
#: That is the file's own convention and the split preserved it.
DECL = re.compile(
    r"^(?:async\s+function|function)\s+([A-Za-z_$][\w$]*)"
    r"|^(?:const|let|var)\s+([A-Za-z_$][\w$]*)"
    r"|^class\s+([A-Za-z_$][\w$]*)")


def declarations(path: Path) -> list[str]:
    names = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line or line[0].isspace():
            continue
        m = DECL.match(line)
        if m:
            names.append(next(g for g in m.groups() if g))
    return names


print("== index.html and web/js agree ==")
html = (WEB / "index.html").read_text(encoding="utf-8")
tags = re.findall(r'<script src="js/([A-Za-z0-9_.-]+\.js)"></script>', html)
on_disk = sorted(p.name for p in JS.glob("*.js"))

check("index.html has script tags", bool(tags))
check("no file is loaded twice", len(tags) == len(set(tags)))
check(f"every tag exists on disk ({len(tags)} tags)",
      all((JS / t).is_file() for t in tags))
missing = sorted(set(on_disk) - set(tags))
check(f"every file on disk is loaded{': ' + ', '.join(missing) if missing else ''}",
      not missing)
check("core.js is loaded first - it declares the state everything reads",
      tags and tags[0] == "core.js")
check("boot.js is loaded last - it calls init()", tags and tags[-1] == "boot.js")
check("no inline <script> block is left in index.html",
      not re.search(r"<script>\s*\n", html))

print("\n== one global scope: no duplicate top-level names ==")
where = defaultdict(list)
for name in tags:
    for decl in declarations(JS / name):
        where[decl].append(name)
dupes = {n: f for n, f in where.items() if len(f) > 1}
for n, files in sorted(dupes.items()):
    print(f"       {n} declared in {', '.join(files)}")
check(f"{len(where)} top-level names, none declared twice", not dupes)

print("\n== the modules are syntactically valid ==")
node = shutil.which("node")
if not node:
    print("  [skip] node not on PATH - syntax check needs it")
else:
    bad = []
    for name in tags:
        r = subprocess.run([node, "--check", str(JS / name)],
                           capture_output=True, text=True)
        if r.returncode:
            bad.append(f"{name}: {r.stderr.strip().splitlines()[0] if r.stderr else '?'}")
    for b in bad:
        print(f"       {b}")
    check(f"all {len(tags)} module files parse", not bad)

    # Loaded together they must also be one valid program - a stray brace in one
    # file can parse alone and still break the page.
    joined = "\n".join((JS / n).read_text(encoding="utf-8") for n in tags)
    # encoding= is not optional: the UI is full of emoji and the Windows default
    # for a pipe is cp1252, which cannot carry them.
    r = subprocess.run(
        [node, "-e", "new (require('vm').Script)(require('fs').readFileSync(0,'utf8'))"],
        input=joined, capture_output=True, text=True, encoding="utf-8")
    check("concatenated in load order, they parse as one program", r.returncode == 0)

print("\n== every menu module is on the Home readiness matrix ==")
# 17a: Home filters MODES down to the non-`sub` modes and reads
# `report.modules[id]`; a module with no entry there renders '' and vanishes
# with no error, which is how Campaign Map was missing from every mod card for a
# whole phase. This asserts the class of bug rather than the one instance.
from unittransfer import campfiles, campmap, modfiles           # noqa: E402

core = (JS / "core.js").read_text(encoding="utf-8")
block = re.search(r"^const MODES=\[(.*?)^\];", core, re.S | re.M)
check("core.js declares MODES", bool(block))
menu = re.findall(r"\{id:'([a-z]+)',(.*?)\}", block.group(1) if block else "")
top = [mid for mid, rest in menu
       if mid != "home" and "sub:true" not in rest and "off:true" not in rest]
subs = [mid for mid, rest in menu if "sub:true" in rest]
# `off:true` is a mode that is in the build and offered nowhere. It is how the
# 2.x line ships without the Campaign Map editor, and it must still have its
# MODULES entry so that clearing the flag needs no second edit.
off = [mid for mid, rest in menu if "off:true" in rest]
check(f"MODES parsed: {len(top)} menu modules, {len(subs)} sub modes, "
      f"{len(off)} off", len(top) > 5)
gap = [m for m in top + off if m not in modfiles.MODULES]
check("every menu module has a MODULES entry"
      + (": " + ", ".join(gap) if gap else ""), not gap)
# A sub mode may still have a MODULES entry - Traits and Sprites do, and their
# rows are what the file table under a mod card is built from. What must not
# happen is a card per sub mode, so Home's filter is the thing checked. All
# three readers - the menu, the Home cards and the resume button - go through
# `menuModes()`/`modeOffered()` so that hiding a mode is one edit, not three.
core_js = core
check("core.js declares menuModes() dropping both sub and off",
      "const menuModes=()=>MODES.filter(m=>!m.sub&&!m.off);" in core_js)
check("the burger menu is built from menuModes()",
      "navModes.innerHTML=menuModes().map(" in core_js)
home = (JS / "home.js").read_text(encoding="utf-8")
check(f"Home's module cards drop the {len(subs)} sub modes and {len(off)} off",
      "menuModes().filter(d => d.id !== 'home')" in home)
check("the resume button only offers a mode that is on the menu",
      "!modeOffered(last)" in home)
# 17f routed the Factions tab into the map's combined screen when the mod had a
# map, and to `factions` when it did not. No public build ever took the first
# road - every 2.x ships with the map off - so on master the same button went
# somewhere else and left the tab unlit behind it. Reverted 2026-09-12: one
# destination on both lines, and the map's own faction screen is reached from
# inside the map. The check is that the branch is GONE, not that the fallback
# is merely present.
_mf = core_js.split("function minorFactions(){")[1].split("}")[0]
check("the Factions tab goes to the factions mode",
      "setAppMode('factions')" in _mf)
check("no build-dependent branch is left in the Factions tab",
      "modeOffered('campmap')" not in _mf and "setAppMode('campmap')" not in _mf)
check("the campmap handoff flag is gone with it",
      "campmapWantFactions" not in core_js
      and "campmapWantFactions" not in (JS / "campmap.js").read_text(encoding="utf-8"))

# The campmap rows are spelled out in modfiles rather than imported from here,
# so that drawing a mod card does not cost a Pillow import. This is what stops
# the two lists drifting apart.
rows = {k.rel.rsplit("/", 1)[-1]: k for k in modfiles.KNOWN if "campmap" in k.modules}
layers = {ly["file"]: ly for ly in campmap.LAYERS}
absent = sorted(set(layers) - set(rows))
check("all ten map layers are declared" + (": " + ", ".join(absent) if absent else ""),
      not absent)
wrong = [f for f, ly in layers.items()
         if f in rows and rows[f].required != ly["required"]]
check("each layer's `required` matches campmap.LAYERS"
      + (": " + ", ".join(wrong) if wrong else ""), not wrong)


print("\n== 28a: the campaign map's side column is a grouping table ==")
# The same class of bug as MODES above, one screen down. `#cmSide` used to be
# sixteen panel divs written out by hand in `renderCampmap`; they are now built
# from `CMAP_TABS`, so a panel that is in no group is a panel that is never in
# the DOM at all and whose module writes into nothing - silently, because
# `getElementById` returning null is what every one of those modules already
# guards against. These read the table the way the block above reads MODES.
campmap_js = (JS / "campmap.js").read_text(encoding="utf-8")
tabs_block = re.search(r"^const CMAP_TABS = \[(.*?)^\];", campmap_js, re.S | re.M)
check("campmap.js declares CMAP_TABS", bool(tabs_block))
tabs_src = tabs_block.group(1) if tabs_block else ""
# 49: a tab is a GROUP of SUB-TABS and a sub-tab is the panels shown together,
# so the table is two levels deep. Split on the top-level `{id: 'x', label:` -
# every sub carries `panels: [...]`, and a group's panels are its subs' put end
# to end, which is exactly what `cmapTabPanels` does in the file.
_tops = re.split(r"\n  \{id: '", tabs_src)[1:]
grouped, subbed = {}, {}
for block in _tops:
    tid = block.split("'", 1)[0]
    grouped[tid] = re.findall(r"'([A-Za-z_][\w]*)'",
                              " ".join(re.findall(r"panels: \[(.*?)\]", block, re.S)))
    subbed[tid] = re.findall(r"\{id: '([a-z]+)', label:", block)
flat = [p for ids in grouped.values() for p in ids]
check(f"CMAP_TABS parsed: {len(grouped)} tabs over "
      f"{sum(len(v) for v in subbed.values())} sub-tabs over {len(flat)} panels",
      len(grouped) >= 4 and len(flat) >= 12)
check("every tab has at least one sub-tab",
      all(subbed.get(t) for t in grouped))
check("no sub-tab id repeats inside its own tab",
      all(len(v) == len(set(v)) for v in subbed.values()))
# The second strip, and the one thing that makes it worth having: choosing a
# sub-tab presses that panel's own toggle, so `Forts` is forts rather than a
# button that says Forts.
check("campmap.js draws the second strip",
      "function cmapSubsHtml(" in campmap_js and 'class="cmsubs"' in campmap_js)
check("and choosing one opens the panel behind it",
      "function cmapSubOpen(" in campmap_js
      and "cmapSubOpen(sb);" in campmap_js)
# Every `open:` names a toggle that exists and a key on `state` some module
# writes - a wrong name here is a sub-tab that silently opens nothing.
_opens = re.findall(r"open: \{fn: '(\w+)', at: '(\w+)'\}", tabs_src)

# A panel in two groups is not a syntax error and not a visible one either:
# `cmapTabOf` takes the first match, so the second tab would hold a div that
# the first tab keeps hidden.
twice = sorted({p for p in flat if flat.count(p) > 1})
check("no panel is in two tabs" + (": " + ", ".join(twice) if twice else ""),
      not twice)

# Every id in the table has to be one a module actually writes into, or the
# table is describing a panel that does not exist.
js_all = "\n".join(f.read_text(encoding="utf-8") for f in sorted(JS.glob("*.js")))
orphan = [p for p in flat
          if p != "cmFindings" and f"'{p}'" not in js_all.replace(tabs_src, "")]
check("every panel in the table is one some module writes into"
      + (": " + ", ".join(orphan) if orphan else ""), not orphan)

# 49: and every `open:` names a toggle some module declares and a key on
# `state` some module writes. A wrong name here is a sub-tab that silently
# opens nothing, which is exactly the bug the sub-tabs exist to remove.
_nofn = [fn for fn, _at in _opens if f"function {fn}(" not in js_all]
check(f"all {len(_opens)} sub-tab toggles are declared"
      + (": " + ", ".join(_nofn) if _nofn else ""), _opens and not _nofn)
_noat = [at for _fn, at in _opens if f"state.{at} =" not in js_all]
check("and each names the key its module keeps `open` on"
      + (": " + ", ".join(_noat) if _noat else ""), not _noat)

# The user asked for Validate by name, and it is a tab rather than a section in
# a stack of sixteen - see the phase note in campmap.js.
check("Validate is a tab of its own and holds the check panel",
      "cmCheck" in grouped.get("check", []))

# 20a's ruling, asserted rather than remembered: the layer stack is the ten
# files the map is made of and is what the number keys tick, so it is not
# behind a tab and stays visible whichever one is up.
check("the layer stack is in no tab", "cmLayers" not in flat)
check("and it is rendered outside the tab body",
      '<div class="cmlayers" id="cmLayers">' in campmap_js
      and 'id="cmBody"' in campmap_js)

# `cmapSurface` is the one thing that keeps the strip from being worse than the
# stack it replaced, and it is addressed by panel id - a name that is not in
# the table surfaces nothing, quietly.
surfaced = sorted(set(re.findall(r"cmapSurface\('([\w]+)'\)", js_all)))
missed = [p for p in surfaced if p not in flat]
check(f"all {len(surfaced)} cmapSurface() calls name a panel in the table"
      + (": " + ", ".join(missed) if missed else ""), surfaced and not missed)

# The three habits 28a added ride in `cmapLayerState`, which is the one
# description of the reading - so a named view carries them for nothing. Same
# check the phase's exit criteria ask for.
state_fn = campmap_js.split("function cmapLayerState(){")[1].split("\nfunction ")[0]
for key in ("m.tab", "m.side_hid", "m.side_px"):
    check(f"cmapLayerState carries {key.split('.')[1]}", key in state_fn)
check("and the column's width is splitInstall's, not a second implementation",
      "splitInstall(split, side, CMAP_SIDE_KEY" in campmap_js)


print("\n== 28b: the brush over the map, and a tooltip that holds still ==")
# The controls that make a stroke are on `.cmbar` over the canvas; the palette,
# the wizard and the save stay in the panel. These are the two halves stated as
# checks, because both are the kind of thing a later edit puts back by accident.
campaint_js = (JS / "campaint.js").read_text(encoding="utf-8")
index_html = (WEB / "index.html").read_text(encoding="utf-8")

check("the toolbar has a row for the paint controls",
      'id="cmPaintBar"' in campmap_js and 'class="cmbarrow cmpaint"' in campmap_js)
_bar = campaint_js.split("function cpaintBarHtml(){")[1].split("\nfunction ")[0]
for want in ("cpaintToolsHtml()", "cpaintSizeHtml()", "cpaintToggle()"):
    check(f"the bar builds {want}", want in _bar)
# and the panel is what is READ rather than reached for
_panel = campaint_js.split("function cpaintHtml(){")[1].split("\nfunction ")[0]
for gone in ("cpaintToolsHtml()", "cpaintSizeHtml()", "cpaintPaletteHtml()"):
    check(f"the panel no longer builds {gone}", gone not in _panel)
for kept in ("cpaintWizHtml()", "cpaintFootHtml()", "cpaintChosenHtml()"):
    check(f"the panel still builds {kept}", kept in _panel)

# 49: the colours are in a column on the left of the map, and the layer they
# belong to is a toggle above them rather than a <select> on the toolbar.
check("the map screen has the left palette column",
      'id="cmPalCol"' in campmap_js and ".cmpalcol{" in
      (WEB / "index.html").read_text(encoding="utf-8"))
_dock = campaint_js.split("function cpaintDockHtml(){")[1].split("\nfunction ")[0]
for want in ("cpaintLayerTogHtml()", "cpaintChosenHtml()", "cpaintPaletteHtml()"):
    check(f"the dock builds {want}", want in _dock)
check("the toolbar's layer <select> is gone",
      "cpaintTargetHtml" not in campaint_js and "[data-target]" not in campaint_js)
check("and the layer toggle is buttons the same wiring reads",
      "data-target-btn" in campaint_js and "[data-target-btn]" in campaint_js)
# 49: the Models Editor is what the BMDB mode is called, and the strat map tab
# has the BMDB browser's own 3D panel - a second docked viewer, which is why the
# orphan drop below exists at all.
_core = (JS / "core.js").read_text(encoding="utf-8")
_stm = (JS / "stratmap.js").read_text(encoding="utf-8")
check("the bmdb mode is the Models Editor",
      "'Models Editor'" in _core and "BMDB + Sprites Editor" not in _core)
check("the strat map tab has a 3D panel beside the list",
      'id="stmSplit"' in _stm and "function stmPrevMount(" in _stm
      and "v3MountCas(STM_PREV_HOST" in _stm)
check("and its rows offer only meshes the mod actually ships",
      "e.meshes" in _stm
      and '"meshes"' in (ROOT / "unittransfer" / "stratmap.py").read_text(encoding="utf-8"))
check("16k's model browser writes into the panel, not the map screen",
      "cmodBrowse" in _stm and "cmodBrowse" in (JS / "stratview.js").read_text(encoding="utf-8")
      and "cmModels" not in (JS / "campmap.js").read_text(encoding="utf-8"))
# Two docked viewers and one WebGL context: leaving a mode has to stop the one
# whose host the next screen wrote over, or it goes on drawing to nothing.
check("a mode switch drops a docked viewer whose host is gone",
      "function v3DropOrphan(" in (JS / "viewer3d.js").read_text(encoding="utf-8")
      and "v3DropOrphan();" in _core)

check("the dock is painted from the same entry point as the other two",
      "cpaintDockPaint();" in campaint_js.split("function cpaintPaint(){")[1]
      .split("\n}")[0])
check("both places are painted from one entry point",
      "cpaintBarPaint();" in campaint_js.split("function cpaintPaint(){")[1]
      .split("\n}")[0])
check("and all three are wired by the same function, handed the box",
      "function cpaintWireIn(box)" in campaint_js
      and campaint_js.count("cpaintWireIn(") >= 4)

# Whether the row is open is a habit and rides with the rest; arming the brush
# is not, and must stay out of a saved view.
check("cmapLayerState carries paint_row", "m.paint_row" in state_fn)
# `p.on` is a thing somebody is doing right now, not a habit, so a named view
# must not be able to arm the brush. The snapshot reads the settings and never
# the paint session, which is what this says.
check("and arming the brush does not ride with it",
      "state.cpaint" not in state_fn and "cpaintArmed" not in state_fn)

# The tooltip's frame. Every one of these was a way the box moved under a
# pointer that was itself moving - see the note above `cmapTipHtml`.
_row = campmap_js.split("function cmapTipRow(ly, tx, ty){")[1].split("\n}")[0]
check("cmapTipRow never returns nothing - a row per layer the manifest names",
      "return '';" not in _row and _row.count("none(") >= 3)
check("the markers block is a fixed number of lines",
      "const CMAP_TIP_MARKS" in campmap_js
      and "lines.length < CMAP_TIP_MARKS" in campmap_js)
check("the head reserves its two lines whether or not it has them",
      'class="cmtiphead"' in campmap_js and 'class="cmtipsub' in campmap_js)
check("the tooltip has a width rather than a maximum",
      ".cmtip{" in index_html
      and "width:320px" in index_html.split(".cmtip{")[1].split("}")[0]
      and "max-width:290px" not in index_html)
check("and nothing in it wraps, so no row can change the box's height",
      "text-overflow:ellipsis;white-space:nowrap" in index_html
      and ".cmtiprow{" in index_html
      and "height:1.5em" in index_html.split(".cmtiprow{")[1].split("}")[0])


print("\n== 33: the copy key, the music picker and the legion row ==")
from unittransfer import mapquery, namekeys                      # noqa: E402

# T10. The form is measured off vanilla's own descr_strat.txt - every one of its
# `character` lines ends `x 109, y 147` - and the y is the GAME one, which
# counts from the bottom. A copy that handed over the image y would put a
# general on the wrong side of the map, so the arithmetic is asserted here
# rather than left to be noticed in a save game.
check("the copy is built in campmap.js", "function cmapCopyText()" in campmap_js)
_copy = campmap_js.split("function cmapCopyText(){")[1].split("\n}")[0]
check("and it copies the game y, not the image one",
      "c.man.height - 1 - ty" in _copy)
check("`c` copies what is under the pointer",
      "cmapCopyTile();" in campmap_js
      and "e.key === 'c'" in campmap_js)
check("and the picked tile has a button of its own",
      'class="cmcopy" onclick="cmapCopyTile()"' in campmap_js)

# G2. The third and last call against descr_sounds_music_types.txt, beside the
# parser and the other two - one module owns that file.
check("mapquery owns all three calls against the music file",
      all(hasattr(mapquery, n) for n in
          ("parse_music_types", "add_music_region", "drop_music_region",
           "set_music_region", "music_view")))
check("a music save is one of campfiles' four",
      "music" in campfiles.WHAT and hasattr(campfiles, "_plan_music"))
check("the region route hands the panel its music",
      'out["music"] = mapquery.music_view(' in
      (ROOT / "unittransfer" / "server.py").read_text(encoding="utf-8"))
check("and the panel saves it on its own, like the pool and the names",
      "function cmapMusicSave()" in campmap_js
      and "'/api/campfiles/plan'" in campmap_js.split("function cmapMusicSave()")[1]
      .split("\n}")[0])
# It is a fact about the MAP, so no campaign is sent - that is the one way this
# picker differs from the mercenary pool's beside it.
_save = campmap_js.split("function cmapMusicSave()")[1].split("\n}")[0]
check("without a campaign, because the file is beside the map layers",
      "campaign" not in _save)

# G4. The legion is the third key one province is read through.
check("namekeys reads the legion key too", "legion" in namekeys.ROW_WHAT)
_rows = namekeys.region_names.__doc__ or ""
check("and the panel has a label for it", "legion: 'Legion'" in campmap_js)
check("a legion key that is another record's says so",
      "another record" in campmap_js)


print("\n== 30: a missing texture without the pink ==")
from unittransfer import mapterrain                               # noqa: E402

# The colour is baked in Python and served as a PNG, so the browser's list and
# the drawing's have to be the same list. The control is built from the
# server's `gap_fills`; this is the fallback, and a drift between them is a
# button that asks for a colour the drawing will not give.
_gaps = re.search(r"^const CMAP_GAPS = \[(.*?)\];", campmap_js, re.M)
check("campmap.js declares CMAP_GAPS", bool(_gaps))
check("and it is mapterrain.GAP_FILLS, in the same order",
      re.findall(r"'([a-z]+)'", _gaps.group(1) if _gaps else "")
      == list(mapterrain.GAP_FILLS))
check("every fill has a label", all(f"{g}:" in campmap_js.split(
      "const CMAP_GAP_LABELS = {")[1].split("}")[0] for g in mapterrain.GAP_FILLS))
check("the control is built from what the server sent",
      "f.gap_fills" in campmap_js and "data-lgap" in campmap_js)
check("and it is wired", "cmapTerrainGap(b.dataset.lgap)" in campmap_js)

# The colour is in the picture, so it is in what the browser caches and in what
# the server caches. Either one missing it hands back the wrong colour.
check("the fetch asks for it and the browser keys its copy on it",
      "&gap=${enc(gap)}" in campmap_js
      and "|${season}|${gap}" in campmap_js)
_srv = (ROOT / "unittransfer" / "server.py").read_text(encoding="utf-8")
check("and the server's disk cache keys on it too",
      'token = f"mapterrain|{p.key}|gap|{gap}"' in _srv)

# A habit, so it rides with the season and a saved view puts it back.
check("cmapLayerState carries terrain_gap", "m.terrain_gap" in state_fn)
check("and a named view carries it",
      "terrainGap" in (JS / "mapviews.js").read_text(encoding="utf-8"))

print(f"\n{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
