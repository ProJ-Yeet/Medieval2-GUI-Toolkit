"""The campaign map's legend, probe and region editor - Phase 16d, measured.

16c handed the browser pixels; this is what it hands the person. Five things
under test:

    campmap.layer_legend      every colour in a layer, named and counted
    campmap.neighbours        which regions share an edge, from the label image
    campmap.probe_pixel       one tile as all ten layers name it
    campmap.render_block      a field edit as a one-line splice
    campmap.plan_region       what a save refuses, and why

The load-bearing claim of the write half is checked here rather than argued:
**an edit rewrites one line and nothing else.** Every record of every installed
map is re-rendered with no edits and must come back byte for byte, and a real
edit must leave the whole file identical outside the record it touched -
comments, tabs, CRLF and the modder's own trailing notes included.

The religion rule has its own section because it is the one the game crashes on:
percentages must total 100, and a set that does not is refused with the reason
at the plan stage, before anything is written.

Six parts, the last three of which need a real game install:

    1  the legend and the blank colours, on grids written here
    2  adjacency, on a grid whose answer can be worked out by hand
    3  the record writer: splices, insertions and refusals
    4  every real map: legends, probes and a no-op re-render of every record
    5  the four routes over real HTTP
    6  a real save on a throwaway mod, and the undo that reverses it

    python -m tests.test_campedit
"""
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod
from unittransfer import campmap, codeview, config, mapvocab
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the legend, on grids written here ------------------------------------
print("\n1) the legend: every colour named, and the one that means nothing")

W, H = 4, 3


def paint(w, h, fn):
    im = Image.new("RGB", (w, h))
    im.putdata([fn(x, y) for y in range(h) for x in range(w)])
    return im


class FakeMap:
    """Just enough of :class:`campmap.CampaignMap` for the legend and the probe."""

    def __init__(self, imgs, mod=None):
        self.imgs = imgs
        self.mod = mod
        self.terrain = campmap.Terrain(width=W, height=H)
        self._tiles = {}

    def layer(self, code):
        return self.imgs[code]

    def centres(self, code):
        return campmap.CampaignMap.centres(self, code)

    tiles = campmap.CampaignMap.tiles


#: a features layer that is mostly `none` with one river and one colour the
#: table has never seen - which is the shape of every real one
FEATURES = paint(W, H, lambda x, y: (0, 0, 255) if (x, y) == (1, 1)
                 else (1, 1, 1) if (x, y) == (3, 2) else (0, 0, 0))
fake = FakeMap({"features": FEATURES})
leg = campmap.layer_legend(fake, "features")
by = {tuple(c["rgb"]): c for c in leg["colours"]}

check("every colour in the layer is listed, biggest first",
      [tuple(c["rgb"]) for c in leg["colours"]] == [(0, 0, 0), (0, 0, 255), (1, 1, 1)])
check("the counts are tiles and they add up to the tile grid",
      leg["total"] == W * H and by[(0, 0, 0)]["count"] == 10)
check("a known colour carries its display name and its code name",
      by[(0, 0, 255)]["name"] == "River" and by[(0, 0, 255)]["code_name"] == "river")
check("a colour NO table knows comes back code_name None - reported, never "
      "rounded to the nearest known one",
      by[(1, 1, 1)]["code_name"] is None and "no table" in leg["note"])
check("and the layer's 'nothing here' colour is flagged, with its source",
      by[(0, 0, 0)]["blank"] and leg["blank"]["key"] == 0
      and leg["blank"]["sourced"] is True)
check("only the flagged colour is - a river is not nothing",
      not by[(0, 0, 255)]["blank"] and not by[(1, 1, 1)]["blank"])

check("every layer with a blank colour is one this toolkit can name, and none "
      "of the four with a real vocabulary has one",
      set(campmap.BLANK) == {"features", "trade_routes", "roughness", "fog"}
      and not ({"regions", "heights", "ground_types", "climates"} & set(campmap.BLANK)))
check("and each claim says whether a reference states it or we measured it",
      all(isinstance(b["sourced"], bool) and b["why"] for b in campmap.BLANK.values())
      and campmap.BLANK["features"]["sourced"]
      and not campmap.BLANK["fog"]["sourced"])

pic = FakeMap({"water_surface": paint(8, 8, lambda x, y: (x * 8, y * 8, 0))})
leg = campmap.layer_legend(pic, "water_surface")
check(f"a picture is refused a legend by name: {leg['note'][:58]}…",
      not leg["colours"] and "picture" in leg["note"] and leg["blank"] is None)

# a magnitude, not a vocabulary: more colours than a legend should list
many = FakeMap({"roughness": paint(2 * W, 2 * H, lambda x, y: (x * 8 + y, ) * 3)})
leg = campmap.layer_legend(many, "roughness")
check(f"a greyscale magnitude is listed to the cap and the rest counted "
      f"({leg['listed']} listed, {leg['more']} more)",
      leg["listed"] <= campmap.LEGEND_MAX and leg["listed"] + leg["more"] > 0)


# ---- 2) adjacency, on a grid whose answer is workable by hand ----------------
print("\n2) which regions share an edge")

#  A A B      the marker column is deliberate: a settlement pixel between A and
#  A S B      C must NOT make them neighbours, and A meets C only at a corner,
#  C C C      which is not adjacency either
A, B, C = (10, 0, 0), (0, 10, 0), (0, 0, 10)
GRID = [[A, A, B, B],
        [A, (0, 0, 0), B, B],
        [C, C, C, (255, 255, 255)]]
regions_img = paint(W, H, lambda x, y: GRID[y][x])
recs = campmap.parse_regions(
    "".join(f"{n}_Province\n\tSet\n\tfac\n\treb\n\t{c[0]} {c[1]} {c[2]}\n\tres\n"
            f"\t5\n\t1\n\treligions {{ catholic 100 }}\n"
            for n, c in (("A", A), ("B", B), ("C", C)))).records
sea = bytes(W * H)
idx = campmap.build_index(regions_img, sea, recs)
adj = campmap._adjacency(idx)
name = {campmap.key(c): n for n, c in (("A", A), ("B", B), ("C", C))}
got = {name[k]: sorted(name[n] for n in v) for k, v in adj.items() if k in name}
check(f"four-connected, and symmetric: {got}",
      got == {"A": ["B", "C"], "B": ["A", "C"], "C": ["A", "B"]})
check("the two marker colours are not regions and are in nobody's list",
      campmap.key((0, 0, 0)) not in adj and campmap.key((255, 255, 255)) not in adj)

#  A A | B B     A and B share a whole edge; D touches nothing but the edge of
#  A A | B B     the map, so its list is empty rather than missing
FAR = [[A, A, B, B], [A, A, B, B], [A, A, B, B]]
idx2 = campmap.build_index(paint(W, H, lambda x, y: FAR[y][x]), sea, recs)
adj2 = campmap._adjacency(idx2)
check("a region with no neighbour at all still answers, with an empty list",
      adj2.get(campmap.key(C)) is None
      and adj2[campmap.key(A)] == [campmap.key(B)])


# ---- 3) the record writer ----------------------------------------------------
print("\n3) an edit is one line, and the rest of the file is untouched")

RECORD = ("Dunland_Province\r\n"
          "\tlegion: Dunland_Province\r\n"
          "\tDunland\t\t; the settlement, since 2007\r\n"
          "\taztecs\r\n"
          "\tDunland_Rebels\r\n"
          "\t100 150 100\r\n"
          "\tgrassland, unlocked, boats\r\n"
          "\t5\r\n"
          "\t1\r\n"
          "\treligions { catholic 7 elven 5 wildmen 88 }\r\n")

check("no edits is byte-identical, CRLF, tabs and trailing comment included",
      campmap.render_block(RECORD, {}) == RECORD)

one = campmap.render_block(RECORD, {"farming": 4})
check("one field changed is one line changed",
      sum(1 for a, b in zip(RECORD.split("\r\n"), one.split("\r\n")) if a != b) == 1
      and campmap.parse_block(one).farming == 4)
check("and the modder's own trailing comment survives it",
      "; the settlement, since 2007" in one)

no_leg = campmap.render_block(RECORD, {"legion": ""})
back = campmap.render_block(no_leg, {"legion": "Dunland_Province"})
check("a legion line can be removed and put back, and the record is the same "
      "bytes it started as",
      "legion" not in no_leg and back == RECORD)
check("an inserted line takes the indent its neighbours use",
      back.split("\r\n")[1].startswith("\t"))

nores = campmap.render_block(RECORD, {"resources": []})
withres = campmap.render_block(nores, {"resources": ["grassland", "boats"]})
check("a resource line can be emptied away and written back above the triumph "
      "value, which is where the format puts it",
      campmap.parse_block(nores).resources_line < 0
      and campmap.parse_block(withres).resources == ["grassland", "boats"]
      and campmap.parse_block(withres).triumph == 5)

rel = campmap.render_block(RECORD, {"religions": {"catholic": 50, "wildmen": 50}})
check("religions are rewritten whole, in the order the panel sends them",
      "religions { catholic 50 wildmen 50 }" in rel)

for bad, why in (({"triumph": "five"}, "a word where a number goes"),
                 ({"faction": ""}, "a blank creator faction"),
                 ({"religions": {"catholic": "half"}}, "a word where a percentage goes")):
    try:
        campmap.render_block(RECORD, bad)
        check(f"{why} is refused", False)
    except campmap.MapError as exc:
        check(f"{why} is refused, by name: {str(exc)[:52]}…", True)

for text, why in (("\tDunland\n\taztecs\n", "a block with no region name line"),
                  (RECORD + RECORD.replace("Dunland", "Other"), "two records at once")):
    try:
        campmap.parse_block(text)
        check(f"{why} is refused", False)
    except campmap.MapError as exc:
        check(f"{why} is refused: {str(exc)[:52]}…", True)

VOCAB = {"religions": ["catholic", "elven", "wildmen"], "rebels": ["Dunland_Rebels"],
         "hidden_resources": ["grassland", "unlocked", "boats"],
         "trade_resources": ["gold"], "factions": ["aztecs"]}
check("a record the mod agrees with has nothing to report",
      not campmap.check_record(campmap.parse_block(RECORD), VOCAB))

short = campmap.render_block(RECORD, {"religions": {"catholic": 50, "wildmen": 40}})
found = campmap.check_record(campmap.parse_block(short), VOCAB)
check(f"religions totalling 90 is FATAL and says by how much: "
      f"{found[0]['message'][:60]}…",
      len(found) == 1 and found[0]["fatal"] and found[0]["field"] == "religions"
      and "-10" in found[0]["message"])

soft = campmap.check_record(campmap.parse_block(campmap.render_block(
    RECORD, {"triumph": 9, "farming": 12, "rebels": "Nope",
             "resources": ["grassland", "nonsuch", "grassland"]})), VOCAB)
kinds = {f["field"] for f in soft}
check(f"and the five things that are wrong rather than fatal are warnings: {sorted(kinds)}",
      kinds == {"triumph", "farming", "rebels", "resources"}
      and not any(f["fatal"] for f in soft))
check("a resource listed twice is one of them",
      any("listed twice" in f["message"] for f in soft))

check("every finding carries the 1-based line it is about",
      all(f["line"] >= 1 for f in soft))

fields = dict(campmap.block_fields(RECORD))
check("the code view's field list is every line of the record",
      fields["name"] == "Dunland_Province" and fields["legion"] == "Dunland_Province"
      and fields["rgb"] == "100 150 100" and fields["triumph"] == "5")
spans = campmap.block_spans(RECORD)
check("and each field's span is the one line it came from",
      spans["name"] == [[1, 1]] and spans["religions"] == [[10, 10]]
      and all(len(v) == 1 and v[0][0] == v[0][1] for v in spans.values()))


# ---- 4) every real map -------------------------------------------------------
print("\n4) every installed map: legends, probes, and every record re-rendered")

roots = _realmod.installed()
game = _realmod.MODS.parent
if (game / "data" / campmap.BASE_REL / "descr_terrain.txt").exists():
    roots.append(game)
roots = [r for r in roots
         if (r / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]

if not roots:
    print("  SKIPPED - no installed mod (and no game) with a campaign map")
else:
    for root in roots:
        mod = Mod(root)
        print(f"\n  -- {mod.name}")
        cm = campmap.CampaignMap(mod)

        # (a) every record re-renders byte-exact with no edits. This is the
        # claim the whole write half stands on, checked on every record of a
        # real hand-written file rather than on the one in section 3.
        rf = campmap.read_regions(mod)
        bad = [r.name for r in rf.records
               if campmap.render_block(campmap.record_text(rf, r), {})
               != campmap.record_text(rf, r)]
        check(f"all {len(rf.records)} records re-render byte-exact with no edits"
              f"{'' if not bad else ': ' + str(bad[:4])}", not bad)
        worst = max(rf.records, key=lambda r: r.span[1] - r.span[0])
        whole = campmap.replace_record(rf, worst, campmap.record_text(rf, worst))
        check("and putting a record back unchanged returns the whole file's bytes",
              whole == rf.serialise())

        # (b) a real edit changes exactly the lines it should
        target = next((r for r in rf.records if r.farming_line >= 0), None)
        if target is not None:
            edited = campmap.replace_record(
                rf, target,
                campmap.render_block(campmap.record_text(rf, target),
                                     {"farming": target.farming + 1}))
            a, b = rf.serialise().split("\n"), edited.split("\n")
            diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
            check(f"one field edited on {target.name} changes exactly one line of "
                  f"{len(a)} in the whole file",
                  len(a) == len(b) and len(diff) == 1
                  and diff[0] == target.farming_line)

        # (c) the legend, on every layer the mod ships
        legends = {}
        for ly in campmap.LAYERS:
            if not (cm.base / ly["file"]).exists():
                continue
            try:
                cm.require_grid(ly["code"])
            except campmap.MapError:
                continue
            legends[ly["code"]] = campmap.layer_legend(cm, ly["code"])
        counted = [c for c, g in legends.items()
                   if g["colours"] and campmap.LAYER_BY_CODE[c]["size"] != "free"]
        check(f"{len(counted)} layers get a legend, and every one's counts add up "
              "to the tile grid",
              counted and all(legends[c]["total"] == cm.terrain.tiles
                              for c in counted))
        if "features" in legends:
            g = legends["features"]
            blank = next(c for c in g["colours"] if c["blank"])
            share = blank["count"] * 100 / g["total"]
            check(f"the features layer is {share:.1f}% 'nothing here' - which is "
                  "why compositing it honestly hid the map, and why 16d punches "
                  "it through", share > 90 and blank["rgb"] == [0, 0, 0])
        if "regions" in legends:
            check("the region layer's legend is its whole vocabulary, not a "
                  f"capped list ({legends['regions']['listed']} colours, "
                  f"{legends['regions']['more']} left out)",
                  legends["regions"]["more"] == 0)

        # (d) the probe names every layer, at a tile that is definitely inside a
        # region rather than at a random coordinate
        anchor = cm.index.regions[0].anchor
        pr = cm.probe_pixel(*anchor)
        rows = {r["code"]: r for r in pr["layers"]}
        check(f"the probe answers all ten layers at {anchor[0]},{anchor[1]}",
              set(rows) == {ly["code"] for ly in campmap.LAYERS})
        check("a layer the mod does not ship says so instead of being sampled",
              all(rows[c]["rgb"] is not None or rows[c]["problem"]
                  for c in rows))
        check("the probe's game coordinates are the image ones through the same "
              "transform descr_strat.txt is written in",
              pr["game"] == [anchor[0], cm.terrain.height - 1 - anchor[1]])

        t0 = time.perf_counter()
        for _ in range(20):
            cm.probe_pixel(*anchor)
        ms = (time.perf_counter() - t0) * 1000 / 20
        check(f"and it costs {ms:.2f} ms warm, which is what makes it a click "
              "rather than a round trip nobody would wait for", ms < 20)

        # (e) adjacency on a real map
        t0 = time.perf_counter()
        adj = cm.neighbours
        took = (time.perf_counter() - t0) * 1000
        both = all(k in adj.get(n, []) for k, ns in adj.items() for n in ns)
        check(f"{len(adj)} regions get their neighbours in {took:.0f} ms, and "
              "every adjacency is symmetric", both and len(adj) > 1)
        check("no region is its own neighbour, and no marker colour is anyone's",
              all(k not in ns for k, ns in adj.items())
              and campmap.key(mapvocab.SETTLEMENT_RGB) not in adj)

        # (f) one region's whole panel payload
        named = next(r for r in rf.records if r.rgb_line >= 0)
        det = campmap.region_detail(cm, named.name)
        check(f"region_detail({named.name}) carries the record, the pixels, the "
              "neighbours and the pickers in one call",
              det["name"] == named.name and det["pixels"] is not None
              and isinstance(det["vocab"]["religions"], list)
              and det["text"] == campmap.record_text(rf, named))
        check("its resources are split into the two kinds the file mixes",
              sorted(det["hidden_resources"] + det["trade_resources"])
              == sorted(named.resources))

        doc = codeview.region_document(mod, named.name)
        check("and the Code View reads the same bytes, with a span per field",
              doc.text == det["text"] and doc.ident == named.name
              and len(doc.spans) >= 6)
        try:
            codeview.parse("regions", doc.text.replace(named.name, "Renamed", 1),
                           codeview.context("regions", mod, named.name))
            check("the text pane refuses a rename", False)
        except codeview.CodeViewError as exc:
            check(f"the text pane refuses a rename: {exc.message[:56]}…",
                  "orphan" in exc.message)


# ---- 5) the four routes, over real HTTP --------------------------------------
print("\n5) /api/map/legend, /api/map/probe, /api/map/region, /api/map/plan|apply")

if not roots:
    print("  SKIPPED - no map to serve")
else:
    src = roots[-1]
    cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"

    med2 = Path(tempfile.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "MapMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for p in (src / "data" / campmap.BASE_REL).iterdir():
        if p.is_file():
            shutil.copy2(p, data / campmap.BASE_REL / p.name)
    # a stale compiled map, which a save has to delete or the game loads it
    # instead and shows none of the edit
    (data / campmap.RWM_REL).write_bytes(b"stale")
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} · map copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def status(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=300) as r:
                return r.status, ""
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8")).get("error", "")
            except Exception:
                return e.code, ""

    regions_path = data / campmap.REGIONS_REL
    before = regions_path.read_bytes()

    try:
        man = get("/api/map?mod=MapMod")
        check("the manifest carries each layer's 'nothing here' colour, so the "
              "renderer can make an overlay of it before any legend arrives",
              any(l["code"] == "features" and l["blank"]["key"] == 0
                  for l in man["layers"])
              and all(l["blank"] is None for l in man["layers"]
                      if l["code"] in ("regions", "heights", "ground_types")))

        leg = get("/api/map/legend?mod=MapMod&code=features")
        check(f"/api/map/legend names {leg['listed']} colours of map_features.tga",
              leg["listed"] >= 2 and leg["total"] == man["width"] * man["height"])
        check("an unknown layer is a 404 naming it",
              status("/api/map/legend?mod=MapMod&code=nosuch")[0] == 404)

        anchor = next(r["anchor"] for r in man["regions"] if r["name"])
        pr = get(f"/api/map/probe?mod=MapMod&x={anchor[0]}&y={anchor[1]}")
        check("/api/map/probe answers one tile on all ten layers",
              len(pr["layers"]) == len(campmap.LAYERS) and pr["image"] == anchor)
        code, why = status("/api/map/probe?mod=MapMod&x=99999&y=0")
        check(f"a tile off the grid is a 404 saying how big the grid is: {why[:56]}…",
              code == 404 and "tile grid" in why)
        check("x that is not a number is a 400, not a traceback",
              status("/api/map/probe?mod=MapMod&x=over&y=there")[0] == 400)

        name = next(r["name"] for r in man["regions"] if r["name"])
        det = get(f"/api/map/region?mod=MapMod&name={urllib.parse.quote(name)}")
        check(f"/api/map/region answers {name} with its record, its pixels and "
              "its pickers", det["name"] == name and det["pixels"]["count"] > 0
              and "religions" in det["vocab"])
        check("an unknown region is a 404 naming it",
              status("/api/map/region?mod=MapMod&name=Nowhere")[0] == 404)

        # the refusals, at the plan stage, before anything is written
        broken = dict(det["religions"])
        if broken:
            first = sorted(broken)[0]
            broken[first] = broken[first] + 7
        else:
            broken = {"catholic": 107}
        r = post("/api/map/plan", {"mod": "MapMod", "region": name,
                                   "edits": {"religions": broken}})
        check(f"a religion set that does not total 100 is refused with the "
              f"reason: {r.get('error', '')[:56]}…",
              r.get("error") and "100" in r["error"] and not r["plan"]["ok"])
        check("and nothing was written by asking", regions_path.read_bytes() == before)

        r = post("/api/map/plan", {"mod": "MapMod", "region": name,
                                   "raw_block": det["text"].replace(name, "Zzz", 1)})
        check(f"renaming a region in the text pane is refused: {r.get('error','')[:56]}…",
              r.get("error") and "orphan" in r["error"])

        rgb = det["rgb"]
        r = post("/api/map/plan", {"mod": "MapMod", "region": name,
                                   "raw_block": det["text"].replace(
                                       f"{rgb[0]} {rgb[1]} {rgb[2]}", "1 2 3", 1)})
        check(f"changing the colour without repainting the pixels is refused: "
              f"{r.get('error','')[:56]}…",
              r.get("error") and "repaint" in r["error"])

        r = post("/api/map/plan", {"mod": "MapMod", "region": name, "edits": {}})
        check("a save with nothing in it is refused rather than written",
              r.get("error") == "nothing to change")

        # ---- 6) a real save, and the undo that reverses it -------------------
        print("\n6) one region saved, and the log's undo")
        was = det["farming"]
        body = {"mod": "MapMod", "region": name,
                "edits": {"legion": det["legion"], "faction": det["faction"],
                          "rebels": det["rebels"], "resources": det["resources"],
                          "triumph": det["triumph"], "farming": was + 1,
                          "religions": det["religions"]}}
        plan = post("/api/map/plan", body)
        check(f"the plan says what would change: {plan['plan']['changes']}",
              plan["plan"]["ok"] and len(plan["plan"]["changes"]) == 1)
        res = post("/api/map/apply", body)
        check("the save answers with a log record that can undo it",
              res.get("record", {}).get("id") and not res.get("error"))
        after = regions_path.read_bytes()
        check("the file changed, and by one line",
              after != before
              and sum(1 for a, b in zip(before.split(b"\n"), after.split(b"\n"))
                      if a != b) == 1)
        check("the region reads back with the new value",
              get(f"/api/map/region?mod=MapMod&name={urllib.parse.quote(name)}"
                  )["farming"] == was + 1)
        check("map.rwm is deleted, or the game loads the old compiled map and "
              "shows none of this",
              not (data / campmap.RWM_REL).exists()
              and campmap.RWM_REL in res["record"]["manifest"]["deleted"])

        post("/api/undo", {"id": res["record"]["id"]})
        check("undo puts descr_regions.txt back byte-exact",
              regions_path.read_bytes() == before)
        check("and puts map.rwm back too, because it went into the same backup set",
              (data / campmap.RWM_REL).read_bytes() == b"stale")

        # the layer stack, remembered
        post("/api/settings", {"map_layers": {"order": ["regions", "features"],
                                              "on": {"features": True},
                                              "opacity": {"regions": 0.3},
                                              "hide": {"features": [0]}}})
        s = get("/api/settings")
        check("the layer stack is remembered on /api/settings, like pane_sizes",
              s["map_layers"]["opacity"]["regions"] == 0.3
              and s["map_layers"]["hide"]["features"] == [0])
    finally:
        httpd.shutdown()
    shutil.rmtree(med2, ignore_errors=True)
    shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
