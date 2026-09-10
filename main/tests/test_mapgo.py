"""Getting to the thing you want - Phase 20b: T9, T8 and D14.

    T9   named view presets: the layer stack saved under a name, and reconciled
         against the manifest when it is loaded back
    T8   the find box: a province, a settlement or a region ID, in one box
    D14  the campaign browser: every campaign the mod ships, with what is in
         each one, and picking one

**The load-bearing claim of this phase is a correction, and it is checked
first.** ``campstrat.campaigns`` reads the folders directly under
``world/maps/campaign``. The roadmap said that was "every folder that really has
a descr_strat.txt"; both mods installed here keep a whole second campaign one
level down, and the map screen has never been able to open either. So the first
part of this suite is the difference between the two lists, measured on whatever
is installed, and it fails loudly if a build ever puts the shallow list back in
front of the browser.

The second claim is the one that made picking a campaign safe to offer at all:
until 20b the campaign in every request was the server's own constant, and from
20b it is a word off the page. ``campstrat.campaign_rel`` is the single choke
point between that word and a path on disk, and every module that builds a
campaign path goes through it.

The browser's own arithmetic is run in node, not reimplemented in Python to be
tested there - the same harness `tests/test_maplayers.py` set up in 20a. What is
run is the real ``cfdSearch`` over the real region tables of every installed map,
and the real ``cvwPlan`` reconciling a preset written against a map that no
longer exists.

Five parts:

    1  the two campaign lists, and the guard between a name and a path
    2  the browser's payload, on every installed mod
    3  the two names 20b added to the manifest
    4  the browser's own functions, in node
    5  /api/map/campaigns over real HTTP, on a mod with no map at all

    python -m tests.test_mapgo
"""
import json
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campfiles, campmap, campstrat, config, renames
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS_DIR = ROOT / "web" / "js"

#: Every mod on this machine with a data folder, plus the game's own unpacked
#: data - which is the only install here with two campaigns at the top level,
#: and therefore the only one that measures that half.
INSTALLED = [m for m in list(_realmod.installed()) + [_realmod.MODS.parent]
             if (m / "data").is_dir()]


# ---- 1) the two lists, and the guard ----------------------------------------

print("\n== 1) every campaign the mod ships, and the one list that says so ==")

if not INSTALLED:
    print("  SKIPPED - no installed mod to measure campaigns on")

nested_seen = 0
for m in INSTALLED:
    mod = Mod(m)
    shallow = campstrat.campaigns(mod)
    whole = campstrat.campaign_paths(mod)
    hidden = [c for c in whole if c not in shallow]
    nested_seen += len(hidden)
    check(f"{m.name}: the whole list contains the shallow one "
          f"({len(whole)} campaigns, {len(shallow)} at the top level)",
          set(shallow) <= set(whole))
    if hidden:
        print(f"  ... {m.name} hides {', '.join(hidden)} from "
              f"campstrat.campaigns")
    check(f"{m.name}: every name in it really has a {campstrat.STRAT_NAME}",
          all(campstrat.strat_path(mod, c).is_file() for c in whole))
    check(f"{m.name}: renames.campaign_dirs is the same list as paths",
          [p.name for p in renames.campaign_dirs(mod)]
          == [c.rsplit("/", 1)[-1] for c in whole])
    check(f"{m.name}: campfiles offers the whole list, not the shallow one",
          campfiles.campaigns(mod) == whole)

check("at least one installed mod keeps a campaign below the top level, "
      f"which is what D14 exists for ({nested_seen} of them)",
      nested_seen > 0 or not INSTALLED)

print("\n-- a campaign name, resolved to a path")
check("the default resolves to itself",
      campstrat.campaign_rel("imperial_campaign") == "imperial_campaign")
check("nothing at all is the default, which is what every request sent "
      "before 20b", campstrat.campaign_rel("") == campstrat.DEFAULT_CAMPAIGN)
check("a nested campaign keeps its slash - it is a real path under the folder",
      campstrat.campaign_rel("custom/Shattered_Alliances")
      == "custom/Shattered_Alliances")
check("a backslash is the same path, since this is Windows",
      campstrat.campaign_rel("custom\\Shattered_Alliances")
      == "custom/Shattered_Alliances")
check("and a doubled or trailing separator is not a different campaign",
      campstrat.campaign_rel("/custom//Shattered_Alliances/")
      == "custom/Shattered_Alliances")

for bad in ("..", "../..", "custom/../../evil", "./imperial_campaign",
            "C:/Windows", "custom/./x"):
    try:
        campstrat.campaign_rel(bad)
        refused = False
    except ValueError:
        refused = True
    check(f"a name that leaves the folder is refused: {bad!r}", refused)

try:
    campstrat.strat_path(Mod(INSTALLED[0]) if INSTALLED else None,
                         "../../../descr_strat.txt")
    guarded = False
except (ValueError, AttributeError, TypeError):
    guarded = True
check("and strat_path itself is where that refusal lands, so no caller has to "
      "remember", guarded)

check("the leaf of a nested campaign is its own folder name",
      campstrat.campaign_leaf("custom/Shattered_Alliances")
      == "Shattered_Alliances"
      and campstrat.campaign_leaf("imperial_campaign") == "imperial_campaign")
check("a description key is built from the leaf, not the path it is reached "
      "through", campfiles.descr_token("custom/Shattered_Alliances")
      == "SHATTERED_ALLIANCES"
      and campfiles.descr_key("custom/Shattered_Alliances", "sicily", "TITLE")
      == "SHATTERED_ALLIANCES_SICILY_TITLE")

# and the measurement that rule came out of: a real mod's own file
print("\n-- and the file that proves the leaf is the right word")
for m in INSTALLED:
    mod = Mod(m)
    nested = [c for c in campstrat.campaign_paths(mod) if "/" in c]
    if not nested:
        continue
    pairs = campfiles.descr_pairs(mod)
    if not pairs:
        print(f"  ... {m.name}: no description file on disk to measure against")
        continue
    for camp in nested:
        token = campfiles.descr_token(camp)
        mine = [k for k in pairs if k.startswith(token + "_")]
        path = camp.replace("/", "_").upper()
        theirs = [k for k in pairs if k.startswith(path + "_")]
        if not mine and not theirs:
            print(f"  ... {m.name}/{camp}: nothing in the file names it either "
                  f"way, so it is a campaign nobody put on the menu")
            continue
        check(f"{m.name}/{camp}: the file keys it {token}_* "
              f"({len(mine)} keys) and not by its path ({len(theirs)})",
              len(mine) > 0 and not theirs)


# ---- 2) the browser's payload ------------------------------------------------

print("\n== 2) what the browser is handed, on every installed mod ==")

for m in INSTALLED:
    mod = Mod(m)
    d = campfiles.browse(mod)
    whole = campstrat.campaign_paths(mod)
    rows = d["campaigns"]
    print(f"  ... {m.name}: {len(rows)} campaign(s) in {d['ms']} ms")
    check(f"{m.name}: one row per campaign, in the same order",
          [r["campaign"] for r in rows] == whole)
    check(f"{m.name}: every one that read says so, and one that did not "
          f"names the reason instead",
          all(bool(r["read"]) != bool(r["problem"]) for r in rows))
    check(f"{m.name}: exactly the campaigns called {campstrat.DEFAULT_CAMPAIGN} "
          f"are flagged as the fallback",
          [r["campaign"] for r in rows if r["default"]]
          == [c for c in whole if c == campstrat.DEFAULT_CAMPAIGN])
    for r in rows:
        if not r["read"]:
            continue
        sf = campstrat.read_strat(mod, r["campaign"])
        counts = sf.counts()
        check(f"{m.name}/{r['leaf']}: the counts are the parse's own "
              f"({r['counts']['faction']} factions, "
              f"{r['counts']['settlement']} settlements)",
              all(r["counts"][k] == counts.get(k, 0) for k in r["counts"])
              and r["lines"] == len(sf.lines))
        check(f"{m.name}/{r['leaf']}: the three rosters are the header's own "
              f"({len(r['rosters']['playable'])} playable)",
              all(r["rosters"][k] == list(sf.rosters.get(k, []))
                  for k in campstrat.ROSTERS))
        check(f"{m.name}/{r['leaf']}: it starts "
              f"{r['values'].get('start_date', '(nowhere)')}",
              r["values"].get("start_date", "") == str(
                  sf.globals.get("start_date", "")))
        check(f"{m.name}/{r['leaf']}: the folder-and-header disagreement is "
              f"reported when there is one (renamed={r['renamed']})",
              r["renamed"] == (bool(sf.campaign) and sf.campaign != r["leaf"]))
        check(f"{m.name}/{r['leaf']}: the menu picture is not counted as a map "
              f"layer of its own ({len(r['layers'])} layers, front-end "
              f"{r['frontend']})",
              not any(n.lower() == "map_fe.tga" for n in r["layers"]))
        for f in r["files"]:
            if f["file"] != campstrat.STRAT_NAME:
                continue
            check(f"{m.name}/{r['leaf']}: it has the one file that qualified it",
                  f["have"])

# the claim in the docstring of `browse`: a campaign with layers of its own,
# counted here off the folder rather than taken from the payload
LAYER_FILES = {ly["file"].lower() for ly in campmap.LAYERS
               if ly["code"] != "fe"}
own = 0
for m in INSTALLED:
    mod = Mod(m)
    for r in campfiles.browse(mod)["campaigns"]:
        folder = campfiles.campaign_dir(mod, r["campaign"])
        theirs = sorted(p.name for p in folder.iterdir()
                        if p.is_file() and p.name.lower() in LAYER_FILES)
        own += len(theirs) > 0
        if theirs:
            print(f"  ... {m.name}/{r['campaign']} ships {len(theirs)} map "
                  f"layer(s) of its own, and this screen draws "
                  f"{campmap.BASE_REL}")
        check(f"{m.name}/{r['leaf']}: the layers on the row are the layer files "
              f"in that folder, counted off the disk", r["layers"] == theirs)
print(f"  ... {own} campaign(s) installed here play on pixels this screen does "
      f"not draw")


# ---- 3) the two names the manifest gained ------------------------------------

print("\n== 3) what the find box searches, in the manifest ==")

maps = []
for m in INSTALLED:
    if not (m / "data" / campmap.TERRAIN_REL).is_file():
        continue
    try:
        cm = campmap.CampaignMap(Mod(m))
        man = campmap.view(cm, m.name)
    except Exception as exc:                                   # noqa: BLE001
        print(f"  [skip] {m.name}: {exc}")
        continue
    loc = campmap.shown_names(Mod(m))
    named = [r for r in man["regions"] if r["name"]]
    check(f"{m.name}: every region carries both localised names "
          f"({len(named)} provinces)",
          all("shown" in r and "shown_settlement" in r
              for r in man["regions"]))
    check(f"{m.name}: and each is the names file's own word for that key",
          all(r["shown"] == loc.get(r["name"], "") for r in named)
          and all(r["shown_settlement"] == loc.get(r["settlement_name"], "")
                  for r in named if r["settlement_name"]))
    shown = sum(1 for r in named if r["shown"])
    print(f"  ... {m.name}: {shown} of {len(named)} provinces have a word the "
          f"player reads; the rest show their code name, as in game")
    maps.append({"name": m.name, "regions": man["regions"]})

check("at least one real map to search", bool(maps) or not INSTALLED)


# ---- 4) the browser's own functions, in node ---------------------------------

print("\n== 4) the find box and the preset reconcile, run for real in node ==")

node = shutil.which("node")

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

function canvas(){
  const cv = {width: 0, height: 0};
  cv.getContext = () => ({
    imageSmoothingEnabled: true, drawImage(){}, putImageData(){},
    getImageData(){ return {data: new Uint8ClampedArray(4)}; },
  });
  return cv;
}
const ctx = {console, document: {createElement: () => canvas()}};
vm.createContext(ctx);
for(const f of process.argv[2].split(','))
  vm.runInContext(fs.readFileSync(f, 'utf8'), ctx);

//: A top-level `function` in a script becomes a property of the global object
//: and a top-level `const` does not - it goes into the realm's own lexical
//: record, which the loaded files share with each other and this file cannot
//: reach by property lookup. So a constant is read by evaluating its name.
const DEFAULT_RIVER = vm.runInContext('CMAP_RIVER_RGB', ctx);

const out = [];
const check = (label, cond) => out.push([!!cond, label]);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

// ---- 4a) the search, over every installed map's real region table ----------
for(const m of job.maps){
  const regions = m.regions, named = regions.filter(r => r.name);
  const find = q => ctx.cfdSearch(q, regions);

  check(`${m.name}: an empty box matches nothing at all`,
        find('').length === 0 && find('   ').length === 0);

  // an exact code name comes first, whatever else contains it
  const one = named.find(r => r.name && r.pixels > 0);
  const hits = find(one.name);
  check(`${m.name}: the exact code name ${one.name} is the first hit`,
        hits.length > 0 && hits[0].name === one.name && hits[0].tier === 0);
  check(`${m.name}: and it goes to a tile inside the province`,
        !!hits[0].tile && hits[0].tile.length === 2);

  // case blindness, both ways
  check(`${m.name}: matching is case-blind`,
        find(one.name.toUpperCase()).length === hits.length
        && find(one.name.toLowerCase())[0].name === one.name);

  // a prefix beats a substring: every hit's tier is sorted
  const many = find(named[0].name.slice(0, 3));
  let sorted = true;
  for(let i = 1; i < many.length; i++) if(many[i].tier < many[i-1].tier) sorted = false;
  check(`${m.name}: exact, then starts-with, then contains - never out of order`,
        sorted);

  // the localised name, which is the whole reason 20b touched the manifest
  const loc = named.find(r => r.shown && r.shown !== r.name);
  if(loc){
    const lh = find(loc.shown);
    check(`${m.name}: the words the player reads find it too (${loc.shown})`,
          lh.length > 0 && lh[0].name === loc.name && lh[0].what === 'province');
  }

  // a region ID is a subject of its own
  const withId = named.find(r => r.id > 0);
  const idh = find(String(withId.id));
  check(`${m.name}: region ID ${withId.id} finds the province the engine `
        + `numbers that`,
        idh.length > 0 && idh.some(h => h.name === withId.name
                                   && h.what === 'region ID'));

  // a settlement match prefers the settlement's own pixel
  const st = named.find(r => r.settlement_name && r.settlement
                             && r.settlement_name !== r.name);
  if(st){
    const sh = find(st.settlement_name).find(h => h.name === st.name);
    check(`${m.name}: a settlement match goes to the settlement's own pixel`,
          !!sh && sh.tile[0] === st.settlement[0] && sh.tile[1] === st.settlement[1]);
  }

  // one row a province, however many of its four names matched
  const dup = find(one.name);
  check(`${m.name}: one row a province, never one a matching field`,
        new Set(dup.map(h => h.name)).size === dup.length);

  // nothing nameless is offered - an undeclared colour has no name to match
  check(`${m.name}: a painted colour the file never declared is not a hit`,
        find('a').every(h => h.name || h.settlement));

  check(`${m.name}: a word no province is called matches nothing`,
        find('zzqxwv_not_a_province').length === 0);
}

// ---- 4b) the preset reconcile ----------------------------------------------
{
  const man = {layers: [
    {code: 'regions', on: true, opacity: 1, present: true, blank: {key: 7}},
    {code: 'heights', on: false, opacity: 0.5, present: true},
    {code: 'features', on: false, opacity: 1, present: false},
  ]};
  const plan = ctx.cvwPlan(man, {
    name: 'saved', order: ['heights', 'gone_layer', 'regions'],
    on: {heights: true, gone_layer: true, regions: false},
    opacity: {heights: 0.25},
    hide: {heights: [1, 2, 3]},
    river: {on: true, rgb: [1, 2, 3]}, height_alpha: true,
    theme: 'owner', theme_opacity: 0.4, theme_borders: false,
  });
  check('a saved order keeps its own places for the codes that are still real',
        plan.order.indexOf('heights') < plan.order.indexOf('regions'));
  check('a layer the manifest has not got is dropped and named',
        !plan.order.includes('gone_layer')
        && plan.dropped.join(',') === 'gone_layer');
  check('a layer the preset never saw is put back where the server had it',
        plan.added.includes('features') && plan.order.includes('features'));
  check('the values it saved are the values it gets back',
        plan.layers.heights.on === true
        && plan.layers.heights.opacity === 0.25
        && plan.layers.heights.hide.join(',') === '1,2,3');
  check('a layer this mod does not ship stays off whatever the preset says',
        plan.layers.features.on === false);
  check("a layer the preset never saw gets the manifest's own blank punched out",
        plan.layers.regions.hide.join(',') === '7');
  check('20a\'s two readings travel with it',
        plan.rivers === true && plan.riverRgb.join(',') === '1,2,3'
        && plan.heightAlpha === true);
  check('and so does the colouring, as a code rather than as colours',
        plan.theme === 'owner' && plan.themeOpacity === 0.4
        && plan.themeBorders === false);

  const bare = ctx.cvwPlan(man, {name: 'bare'});
  check('a preset with nothing in it is the manifest\'s own defaults',
        bare.order.length === 3 && bare.layers.regions.on === true
        && bare.layers.heights.on === false
        && bare.rivers === false && bare.heightAlpha === false
        && bare.theme === '');
  check('and its river colour is the screen\'s own default, not black',
        bare.riverRgb.join(',') === DEFAULT_RIVER.join(','));

  const junk = ctx.cvwPlan(man, {name: 'junk', order: 'not a list',
                                 on: 'nor this', opacity: {regions: 40},
                                 river: {on: true, rgb: [1]}});
  check('a settings file somebody hand-edited does not take the screen down',
        junk.order.length === 3
        && junk.layers.regions.opacity === 1
        && junk.riverRgb.join(',') === DEFAULT_RIVER.join(','));
}

fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""

if not node:
    print("  [skip] node is not on PATH, and these functions run in it")
elif not maps:
    print("  [skip] no installed map to search")
else:
    td = Path(_tmp.mkdtemp(prefix="ut_mapgo_"))
    job = td / "job.json"
    job.write_text(json.dumps({"maps": maps}), encoding="utf-8")
    run = td / "harness.js"
    run.write_text(HARNESS, encoding="utf-8")
    res = td / "out.json"
    files = ",".join(str(JS_DIR / n) for n in
                     ("campmap.js", "mapfind.js", "mapviews.js"))
    p = subprocess.run([node, str(run), files, str(job), str(res)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        check("the harness runs", False)
        print((p.stderr or p.stdout).strip()[:2000])
    else:
        for passed, label in json.loads(res.read_text(encoding="utf-8")):
            check(label, passed)


# ---- 5) the route, over real HTTP --------------------------------------------

print("\n== 5) /api/map/campaigns, on a mod with no map at all ==")

STRAT = """campaign\t\t{name}
playable
\tengland
end
unlockable
end
nonplayable
\tslave
end

start_date\t{year} summer
end_date\t1530 winter
timescale\t2.00

resource\tgold, 10, 20

faction\tengland, smith smith
\tai_label default
\tdenari\t10000
\tsettlement castle
\t{{
\t\tlevel town
\t\tregion England_Province
\t\tyear_founded 0
\t\tpopulation 1000
\t\tplan_set default_set
\t\tfaction_creator england
\t}}
\tcharacter\tWilliam, named character, age 40, x 100, y 100
\t\ttraits GoodCommander 1

faction\tslave, bureaucrat attila
\tai_label default
\tdenari\t0
"""

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
data = med2 / "mods" / "TwoCampaigns" / "data"
base = data / campstrat.CAMPAIGN_DIR_REL
for rel, year in (("imperial_campaign", 1080), ("custom/Second_Age", 3018)):
    folder = base / rel
    folder.mkdir(parents=True)
    (folder / campstrat.STRAT_NAME).write_text(
        STRAT.format(name=rel.rsplit("/", 1)[-1], year=year),
        encoding=campstrat.ENCODING)
# the nested one gets a region layer of its own, which is the state the browser
# has to report rather than draw
(base / "custom/Second_Age" / "map_regions.tga").write_bytes(b"not really a tga")
(base / "imperial_campaign" / "descr_win_conditions.txt").write_text(
    "england\n{\n}\n", encoding="latin-1")
config.save_settings(med2_root=str(med2), run_full_cleaner=False)

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"  serving {BASE} · a mod with two campaigns and no map")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def status(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=120) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


code = status("/api/map?mod=TwoCampaigns")
check(f"this mod has no map, and /api/map says so ({code})", code == 404)
d = get("/api/map/campaigns?mod=TwoCampaigns")
check("and the campaign list answers anyway - it is a folder walk, not a map",
      len(d["campaigns"]) == 2)
by = {r["campaign"]: r for r in d["campaigns"]}
check("both campaigns are there, the nested one under its own path",
      "imperial_campaign" in by and "custom/Second_Age" in by)
check("the nested one knows it is nested and knows its own leaf",
      by["custom/Second_Age"]["nested"]
      and by["custom/Second_Age"]["leaf"] == "Second_Age"
      and not by["imperial_campaign"]["nested"])
check("each one's own dates came out of its own file",
      by["imperial_campaign"]["values"]["start_date"] == "1080 summer"
      and by["custom/Second_Age"]["values"]["start_date"] == "3018 summer")
check("what stands in it is counted: two factions, one settlement, one man",
      by["imperial_campaign"]["counts"]["faction"] == 2
      and by["imperial_campaign"]["counts"]["settlement"] == 1
      and by["imperial_campaign"]["counts"]["character"] == 1)
check("the one with its own region layer is reported as having one",
      by["custom/Second_Age"]["layers"] == ["map_regions.tga"]
      and by["imperial_campaign"]["layers"] == [])
check("a file one has and the other does not is reported per campaign",
      next(f["have"] for f in by["imperial_campaign"]["files"]
           if f["file"] == "descr_win_conditions.txt")
      and not next(f["have"] for f in by["custom/Second_Age"]["files"]
                   if f["file"] == "descr_win_conditions.txt"))
check("no description file on disk, so no campaign is reported as unnamed",
      d["descriptions"]["have"] is False)
check("the default is named, because every route still falls back to it",
      d["default"] == campstrat.DEFAULT_CAMPAIGN
      and by["imperial_campaign"]["default"]
      and not by["custom/Second_Age"]["default"])

# and the nested campaign is readable through the very routes the browser's
# pick sends it to, which is the whole of D14's second half
sf = campstrat.read_strat(Mod(med2 / "mods" / "TwoCampaigns"), "custom/Second_Age")
check("a nested campaign reads through campstrat with the slash in its name",
      sf.campaign == "Second_Age" and sf.counts().get("faction") == 2)
code = status("/api/map/campaign?mod=TwoCampaigns"
              "&campaign=..%2F..%2F..%2Fdescr_strat.txt")
check(f"and a campaign that tries to leave the folder is refused, not read "
      f"({code})", code in (400, 404))

httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
