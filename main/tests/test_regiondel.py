"""Deleting a province, and giving its land to a neighbour (24, G1).

    python -m tests.test_regiondel

One little mod written here, six tiles by seven, with four provinces laid out so
that every rule of the delete has something to be right about:

    +----------------------------------+
    | ~~  Alpha Alpha Beta  Beta  Beta |  Alpha is the one being deleted
    | ~~   (P)  Alpha Beta   (S)  Beta |  Beta shares four edges: the default heir
    | ~~  Alpha Alpha Beta  Beta  Beta |  Gamma shares one
    | ~~   (S)  Alpha Beta  Beta  Beta |  Delta touches Alpha nowhere: the refusal
    | ~~   (P)  Gamma Gamma Gamma Gamma|
    | ~~  Gamma Gamma  (S)  Gamma Gamma|
    | ~~  Delta Delta Delta Delta Delta|
    | ~~  Delta Delta  (S)  Delta Delta|
    | ~~~~~~~~~~~~ sea ~~~~~~~~~~~~~~~ |
    +----------------------------------+

Every ``(S)`` is a settlement pixel and belongs to the province north of it, by
the engine's cardinal rule. The two ``(P)`` are ports, which have a rule of their
own: sea on one side and the province's own land on the other, so the upper one
is Alpha's and the lower Gamma's. Beta has none, and that is what makes "keep the
port" and "remove the port" two answers to one question rather than a setting.

The water is painted a colour no record declares, which is what a real map does:
Divide and Conquer's 73,902 sea tiles are all ``41 140 233`` and nothing in
``descr_regions.txt`` claims it.

Then the eight files a province is named in, one at a time: the record, the start
position (settlement block, the `region` section holding a fort and a tower, a
character and a resource standing on Alpha's tiles), the win conditions, the
mercenary pools, the music types, the lookup pairs and the custom battle tiles -
plus a campaign script that names it, which is listed and never written. Then the
save, re-read off disk, and finally every installed mod, where the plan is built
for a real province and checked without being applied.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import (campfiles, campmap, campstrat, config, mapquery,
                          regiondel, renames, winconds)
from unittransfer import keyblock as kb
from unittransfer.maptga import TgaInfo, encode
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little mod ----------------------------------------------------------

W, H = 6, 9

A, B, G, D = (200, 0, 0), (0, 200, 0), (0, 0, 200), (200, 200, 0)
BLACK, WHITE = (0, 0, 0), (255, 255, 255)
#: Divide and Conquer's own water colour, and declared by nothing here either
WATER = (41, 140, 233)

#: one region colour per tile, top row first. Alpha has six tiles, four edges
#: with Beta and one with Gamma; Gamma has a port of its own, Beta has none, and
#: Delta touches Alpha nowhere at all.
REGIONS = [[WATER, A, A, B, B, B],
           [WATER, WHITE, A, B, BLACK, B],
           [WATER, A, A, B, B, B],
           [WATER, BLACK, A, B, B, B],
           [WATER, WHITE, G, G, G, G],
           [WATER, G, G, BLACK, G, G],
           [WATER, D, D, D, D, D],
           [WATER, D, D, BLACK, D, D],
           [WATER, WATER, WATER, WATER, WATER, WATER]]

#: the sea, by the only rule that decides it: the heights. Column 0 all the way
#: down and the bottom row, which is what gives each port a dock.
SEA_AT = {(x, y) for y in range(H) for x in range(W)
          if x == 0 or y == H - 1}

TERRAIN = ("dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n"
           "\tmin_sea_height  -100.000\n\tmax_land_height  1000.000\n}\n"
           "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
           "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n"
           % (W, H))


def record(name, town, rgb):
    return (f"{name}\r\n\tlegion: {name}\r\n\t{town}\r\n\tengland\r\n\tbrigands\r\n"
            f"\t{rgb[0]} {rgb[1]} {rgb[2]}\r\n\tgold\r\n\t5\r\n\t4\r\n"
            f"\treligions {{ catholic 100 }}\r\n\r\n")


REGIONS_TXT = (record("Alpha", "Atown", A) + record("Beta", "Btown", B)
               + record("Gamma", "Gtown", G) + record("Delta", "Dtown", D))

STRAT = """campaign imperial_campaign
playable
\tengland
\tfrance
end
unlockable
end
nonplayable
\tslave
end

start_date 1080 summer
end_date 1530 winter

resource gold, 1, 6
resource silver, 3, 2
; game coordinates, so y counts up from the bottom: gold is on Alpha's
; (1,2) in image coordinates and silver is on Delta's (3,6)

faction\tengland, balanced smith
\tdenari\t10000

\tsettlement
\t{
\t\tlevel town
\t\tregion Alpha

\t\tyear_founded 0
\t\tpopulation 1000
\t\tplan_set default_set
\t\tfaction_creator england
\t}

\tsettlement
\t{
\t\tlevel town
\t\tregion Beta

\t\tyear_founded 0
\t\tpopulation 1000
\t\tplan_set default_set
\t\tfaction_creator england
\t}

\tcharacter\tGuy, named character, age 30, x 2, y 6
\tarmy
\t\tunit\tPeasants\t\t\t\t\texp 0 armour 0 weapon_lvl 0

faction\tfrance, balanced smith
\tdenari\t10000

\tsettlement
\t{
\t\tlevel town
\t\tregion Gamma

\t\tyear_founded 0
\t\tpopulation 1000
\t\tplan_set default_set
\t\tfaction_creator france
\t}

faction\tslave, balanced smith
\tdenari\t1000

\tsettlement
\t{
\t\tlevel village
\t\tregion Delta

\t\tyear_founded 0
\t\tpopulation 400
\t\tplan_set default_set
\t\tfaction_creator england
\t}

; >>>> start of regions section <<<<

region Alpha
farming_level 0
famine_threat 0
watchtower 1 8
fort 2 7 stone_fort culture northern_european

region Beta
farming_level 0
famine_threat 0
watchtower 5 8

region Gamma
farming_level 0
famine_threat 0
watchtower 5 4

script

end_script
"""

WINS = """england
hold_regions Alpha Beta Gamma
take_regions 3
short_campaign hold_regions Alpha
short_campaign take_regions 2

france
hold_regions Alpha
outlive england
"""

MERCS = """pool Northern
\tregions Alpha Beta
\tunit Merc Spearmen, exp 0, cost 500, replenish 0.1 - 0.2, max 2, initial 1

pool Alpine
\tregions Alpha
\tunit Merc Crossbows, exp 0, cost 500, replenish 0.1 - 0.2, max 2, initial 1
"""

MUSIC = """music_type northern
\tregions Alpha Beta
\tfactions england

music_type southern
\tregions Gamma Delta
"""

LOOKUP = "Alpha\nAtown\nBeta\nBtown\nGamma\nGtown\nDelta\nDtown\n"

TILES_DB = """; province, tile, weight
Alpha\tgrass\t1
Beta\tgrass\t1
Alpha\thills\t2
"""

SCRIPT = """script

monitor_event GeneralAssaultsResidence IsTargetRegionOneOf Alpha
end_monitor

end_script
"""


def write_tga(path, img, depth=24, image_type=10, desc=0x08):
    info = TgaInfo(image_type=image_type, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    path.write_bytes(encode(img.convert(info.mode), info))


def grid_img(rows):
    im = Image.new("RGB", (W, H))
    im.putdata([rows[y][x] for y in range(H) for x in range(W)])
    return im


def centre_img(rows):
    im = Image.new("RGB", (2 * W + 1, 2 * H + 1), (7, 7, 7))
    px = im.load()
    for y in range(H):
        for x in range(W):
            px[2 * x + 1, 2 * y + 1] = rows[y][x]
    return im


def tiny_mod(root: Path) -> Mod:
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / "descr_terrain.txt").write_text(TERRAIN, encoding="latin-1")
    (base / "descr_regions.txt").write_bytes(REGIONS_TXT.encode("latin-1"))
    write_tga(base / "map_regions.tga", grid_img(REGIONS))
    write_tga(base / "map_features.tga", grid_img([[(0, 0, 0)] * W for _ in range(H)]))
    flat = [[(0, 0, 0)] * W for _ in range(H)]
    write_tga(base / "map_ground_types.tga", centre_img(flat))
    write_tga(base / "map_climates.tga", centre_img(flat))
    heights = [[(0, 0, 200) if (x, y) in SEA_AT else (90, 90, 90)
                for x in range(W)] for y in range(H)]
    write_tga(base / "map_heights.tga", centre_img(heights))
    (base / "descr_sounds_music_types.txt").write_text(MUSIC, encoding="latin-1")
    (base / "map.rwm").write_bytes(b"stale")

    camp = (root / "data" / campstrat.CAMPAIGN_DIR_REL
            / campstrat.DEFAULT_CAMPAIGN)
    camp.mkdir(parents=True, exist_ok=True)
    (camp / campstrat.STRAT_NAME).write_text(STRAT, encoding="latin-1")
    (camp / winconds.REL_NAME).write_text(WINS, encoding="latin-1")
    (camp / campfiles.MERCS_NAME).write_text(MERCS, encoding="latin-1")
    (camp / "descr_regions_and_settlement_name_lookup.txt").write_text(
        LOOKUP, encoding="latin-1")
    (camp / "custom_tiles_db.txt").write_text(TILES_DB, encoding="latin-1")
    (camp / "campaign_script.txt").write_text(SCRIPT, encoding="latin-1")
    (camp / "map.rwm").write_bytes(b"stale")
    return Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

med2 = Path(_tmp.mkdtemp(prefix="ut_regiondel_"))
mod = tiny_mod(med2 / "mods" / "Tiny")
cm = campmap.CampaignMap(mod)
CAMP = campstrat.DEFAULT_CAMPAIGN
print(f"  a {W}x{H} map, four provinces, eight files naming one of them")


def data(rel):
    return kb.read_text(Path(mod.data) / rel, "latin-1")


def rel_of(name):
    return f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{name}"


# ---- 1) who can inherit ------------------------------------------------------
print("\n1) the heirs, and the one that is not")

hs = regiondel.heirs(cm, "Alpha")
check(f"     Alpha touches {len(hs)} declared province(s), and Delta is not one "
      f"of them", [h["name"] for h in hs] == ["Beta", "Gamma"])
check(f"     the longest border comes first: Beta {hs[0]['edges']} edges, Gamma "
      f"{hs[1]['edges']}", hs[0]["edges"] == 4 and hs[1]["edges"] == 1)
check("     each heir carries whether it already has a port, which is what the "
      "port question is answered from",
      hs[0]["port"] is False and hs[1]["port"] is True)

v = regiondel.view(mod, cm, CAMP, "Alpha")
check(f"     the panel reads Alpha in one go: {v['tiles']} tiles, settlement "
      f"{v['settlement']}, a port, region ID {v['region_id']}",
      v["ok"] and v["tiles"] == 6 and v["settlement"] == "Atown" and v["port"])
check("     a name no record declares is a refusal naming the file, not a "
      "traceback",
      not regiondel.view(mod, cm, CAMP, "Nowhere")["ok"]
      and "descr_regions.txt" in regiondel.view(mod, cm, CAMP, "Nowhere")["error"])

st = v["standing"]
check(f"     what stands on Alpha's tiles is counted rather than moved: "
      f"{st[0]['counts'] if st else None}",
      st and st[0]["counts"] == {"character": 1, "fort": 1, "watchtower": 1,
                                 "resource": 1})


# ---- 2) the refusals ---------------------------------------------------------
print("\n2) what a delete will not do")

p = regiondel.plan(mod, cm, CAMP, {"name": "Alpha", "heir": "Delta"})
check("     an heir that does not share an edge is refused, and the refusal "
      "names the ones that do",
      p.errors and "Delta does not share an edge" in p.errors[0]
      and "Beta" in p.errors[0])

p = regiondel.plan(mod, cm, CAMP, {"name": "Nowhere"})
check("     a province that is not in the file is refused by name", p.errors)

one = campmap.parse_regions(record("Only", "Otown", A))
saved, cm.regions.records = cm.regions.records, one.records
p = regiondel.plan(mod, cm, CAMP, {"name": "Only"})
cm.regions.records = saved
check("     the last region left in the file is refused - a map with no region "
      "at all will not load",
      p.errors and "only region" in p.errors[0])


# ---- 3) the plan -------------------------------------------------------------
print("\n3) what one delete would write")

p = regiondel.plan(mod, cm, CAMP, {"name": "Alpha"})
check(f"     the default heir is the longest border: {p.heir}", p.heir == "Beta")
check(f"     {p.tiles} tiles change hands", p.tiles == 6)
check("     the plan has no errors and touches every file that names Alpha "
      f"({len(p.files)} of them)", not p.errors and len(p.files) == 8)

said = "\n".join(p.changes)
for rel, what in (
        ("map_regions.tga", "6 tile(s) of Alpha become Beta's"),
        ("descr_regions.txt", "the record for Alpha"),
        ("descr_strat.txt", "england's settlement in Alpha"),
        ("descr_win_conditions.txt", "taken out of 3 hold_regions line(s)"),
        ("descr_mercenaries.txt", "taken out of the pool"),
        ("descr_sounds_music_types.txt", "taken out of the music type northern"),
        ("name_lookup.txt", "the Alpha / Atown pair removed"),
        ("custom_tiles_db.txt", "2 custom battle tile row(s) removed")):
    check(f"     {rel}: {what}", what in said and rel in said)

check("     the settlement pixel becomes ground, because Beta has Btown and a "
      "province has one seat", "settlement pixel at 1,3 becomes ground" in said)
check("     the port pixel stays and becomes Beta's, because Beta has none of "
      "its own", p.port == "keep" and "becomes Beta's harbour" in said)
check("     both map.rwm files are deleted, or the game loads the old compiled "
      "map", sorted(p.deletes) == sorted([campmap.RWM_REL, rel_of("map.rwm")]))

warned = "\n".join(p.warnings)
check("     the one script line naming Alpha is listed with its line number and "
      "never written",
      len(p.script) == 1 and p.script[0].line == 3
      and "reported and never written" in warned)
check("     france's whole win condition is now empty, and it is told so",
      "france's win condition now names no province" in warned)
check("     the pool that sold only in Alpha now sells nowhere",
      "the pool Alpine now sells in no province" in warned)
check("     the renumbering is the creation warning read backwards",
      "each move down by one" in warned)

p2 = regiondel.plan(mod, cm, CAMP, {"name": "Alpha", "heir": "Gamma"})
check("     with Gamma as the heir the port is removed instead, because Gamma "
      "already has one", p2.heir == "Gamma" and p2.port == "remove"
      and "becomes ground - Gamma already has a port" in "\n".join(p2.changes))


# ---- 4) the section that really is orphaned ----------------------------------
print("\n4) the `region` section, which is the one thing filed under a name")

strat_rel = rel_of(campstrat.STRAT_NAME)
after = campstrat.parse_strat(p.texts[strat_rel])
beta = next(n for n in after.of_kind("region") if n.get("name") == "Beta")
kids = [after.nodes[i].kind for i in beta.children]
check(f"     Alpha's fort and watchtower move into Beta's section: {kids}",
      sorted(kids) == ["fort", "watchtower", "watchtower"])
check("     and `region Alpha` is gone from the file",
      not any(n.get("name") == "Alpha" for n in after.of_kind("region")))
check("     no fort or watchtower was lost on the way",
      after.counts().get("fort", 0) == 1
      and after.counts().get("watchtower", 0) == 3)

gamma = regiondel.plan(mod, cm, CAMP, {"name": "Gamma"})
gafter = campstrat.parse_strat(gamma.texts[strat_rel])
gnames = [str(n.get("name")) for n in gafter.of_kind("region")]
check(f"     Gamma's heir is Delta, which has no section of its own, so "
      f"`region Gamma` is renamed rather than moved and keeps its watchtower: "
      f"{gnames}",
      gamma.heir == "Delta" and gnames == ["Alpha", "Beta", "Delta"]
      and gafter.counts().get("watchtower", 0) == 3)


# ---- 5) the save -------------------------------------------------------------
print("\n5) applied, and read back off disk")

res = regiondel.apply(p)
check(f"     one log entry and one backup set for all {len(p.files)} files "
      f"plus the two map.rwm", bool(res["id"]))
cm2 = campmap.CampaignMap(mod)
check("     descr_regions.txt no longer declares Alpha, and the other three are "
      "untouched",
      cm2.regions.by_name("Alpha") is None
      and [r.name for r in cm2.regions.records] == ["Beta", "Gamma", "Delta"])
check("     the map has no colour that no record declares except the water it "
      "started with, and no record with no colour - the hole 16e refuses to let "
      "anybody paint",
      cm2.index.unclaimed == [WATER] and not cm2.index.empty_records)
beta_now = cm2.index.by_key[campmap.key(B)]
check(f"     Beta has grown by Alpha's six tiles and the pixel its seat stood "
      f"on, to {beta_now.pixels}", beta_now.pixels == 11 + 6 + 1)
check("     Beta keeps its own seat, takes the port, and Alpha's seat is gone",
      beta_now.settlement == (4, 1) and beta_now.port == (1, 1)
      and not cm2.index.extra_settlements and not cm2.index.extra_ports)
check("     both map.rwm files are gone",
      not (Path(mod.data) / campmap.RWM_REL).exists()
      and not (Path(mod.data) / rel_of("map.rwm")).exists())

sf = campstrat.read_strat(mod, CAMP)
check("     no settlement block in the campaign stands in Alpha any more",
      all(str(n.get("region") or "") != "Alpha" for n in sf.of_kind("settlement")))
check("     england still holds Beta, and its capital moved up to it",
      [str(n.get("region")) for n in sf.of_kind("settlement")]
      == ["Beta", "Gamma", "Delta"])
wf = winconds.parse_wins(data(rel_of(winconds.REL_NAME)))
check("     the win conditions hold Beta and Gamma and no longer Alpha",
      wf.find("england").get("hold") == ["Beta", "Gamma"]
      and wf.find("england").get("short_hold") == []
      and wf.find("france").get("hold") == [])
check("     short_campaign is still on the line it was on, which is the switch "
      "for the whole short campaign",
      "short_campaign hold_regions" in data(rel_of(winconds.REL_NAME)))
mf = campfiles.parse_mercs(data(rel_of(campfiles.MERCS_NAME)))
check("     Alpha is out of both pools, and the one that sold only there has "
      "lost its `regions` line rather than keeping an empty one",
      mf.pool_of("Alpha") == "" and mf.pool_of("Beta") == "Northern"
      and "\tregions Beta" in data(rel_of(campfiles.MERCS_NAME))
      and mf.regions_line.get("Alpine", 0) < 0)
types = mapquery.parse_music_types(
    data(f"{campmap.BASE_REL}/descr_sounds_music_types.txt"))
check("     the music types name Beta and not Alpha",
      types == {"northern": ["Beta"], "southern": ["Gamma", "Delta"]})
check("     the lookup file lost the pair and kept the order",
      data(rel_of("descr_regions_and_settlement_name_lookup.txt")).split()
      == ["Beta", "Btown", "Gamma", "Gtown", "Delta", "Dtown"])
check("     the custom battle tiles lost both Alpha rows and kept its comment",
      data(rel_of("custom_tiles_db.txt")).startswith("; province")
      and "Alpha" not in data(rel_of("custom_tiles_db.txt")))
check("     the campaign script still names Alpha, exactly as the plan said it "
      "would", "Alpha" in data(rel_of("campaign_script.txt")))


# ---- 6) the routes -----------------------------------------------------------
print("\n6) the three routes the panel uses")

import json
import threading
import urllib.request

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    d = get("/api/map/region_delete?mod=Tiny&name=Gamma")
    # Beta grew into Alpha's land a section ago, so it now shares as much
    # border with Gamma as Delta does and the tie is broken by name
    check(f"     GET /api/map/region_delete names the heirs longest border "
          f"first: {[(h['name'], h['edges']) for h in d['heirs']]}",
          d["ok"] and [h["name"] for h in d["heirs"]] == ["Beta", "Delta"]
          and d["heirs"][0]["edges"] == d["heirs"][1]["edges"] == 4)
    bad = get("/api/map/region_delete?mod=Tiny&name=Nowhere")
    check("     and answers a name nothing declares with the reason rather than "
          "a traceback", not bad["ok"] and bad["error"])

    r = post("/api/map/region_delete_plan",
             {"mod": "Tiny", "name": "Gamma", "heir": "Beta"})
    check(f"     POST ..._plan works the whole thing out and writes nothing: "
          f"{len(r['plan']['files'])} file(s), heir {r['plan']['heir']}",
          r["plan"]["ok"] and r["plan"]["heir"] == "Beta"
          and campmap.CampaignMap(mod).regions.by_name("Gamma") is not None)
    r = post("/api/map/region_delete_plan", {"mod": "Tiny", "name": "Gamma",
                                             "heir": "Beta", "port": "keep"})
    check("     the port answer comes off the body rather than off a default",
          r["plan"]["port"] == "keep")

    r = post("/api/map/region_delete_apply", {"mod": "Tiny", "name": "Gamma"})
    check("     POST ..._apply writes it and answers with the log id",
          r.get("id") and r.get("heir") == "Beta")
    cm3 = campmap.CampaignMap(mod)
    check("     and the mod on disk is one province lighter",
          cm3.regions.by_name("Gamma") is None
          and [x.name for x in cm3.regions.records] == ["Beta", "Delta"])
    r = post("/api/map/region_delete_apply", {"mod": "Tiny", "name": "Gamma"})
    check("     a second delete of the same province is a refusal, not a crash",
          bool(r.get("error")))
finally:
    httpd.shutdown()


# ---- 7) every installed mod --------------------------------------------------
print("\n7) a real mod, planned and not applied")

import time

seen = False
for root in _realmod.installed():
    rmod = Mod(root)
    try:
        rcm = campmap.CampaignMap(rmod)
        if not rcm.regions.records:
            continue
    except Exception:                                          # noqa: BLE001
        continue
    # a province with a neighbour and a settlement: the ordinary case
    target = next((r for r in rcm.regions.records
                   if r.settlement and regiondel.heirs(rcm, r.name)), None)
    if target is None:
        continue
    seen = True
    t0 = time.perf_counter()
    rp = regiondel.plan(rmod, rcm, campstrat.DEFAULT_CAMPAIGN,
                        {"name": target.name})
    ms = int((time.perf_counter() - t0) * 1000)
    check(f"     {rmod.name}: {target.name} -> {rp.heir}, {rp.tiles:,} tiles, "
          f"{len(rp.files)} file(s), {len(rp.warnings)} warning(s), {ms} ms",
          not rp.errors and rp.heir and rp.files)
    check(f"     {rmod.name}: the record comes out of every descr_regions.txt "
          f"the affected campaigns read",
          any(t.endswith("descr_regions.txt") for t in rp.texts)
          and all(campmap.parse_regions(txt).by_name(target.name) is None
                  for rel, txt in rp.texts.items()
                  if rel.endswith("descr_regions.txt")))
    check(f"     {rmod.name}: every rewritten descr_strat.txt still parses and "
          f"holds one province fewer",
          all(campstrat.parse_strat(txt).counts().get("settlement", 0)
              < campstrat.parse_strat(
                  kb.read_text(Path(rmod.data) / rel, "latin-1")
              ).counts().get("settlement", 0)
              for rel, txt in rp.texts.items()
              if rel.endswith(campstrat.STRAT_NAME)))
    # the bytes are built at plan time exactly so that this can be true before
    # a backup is taken: the layer re-reads, is the same size, and no longer
    # carries the deleted province's colour anywhere
    from unittransfer import maptga
    raw = next(iter(rp.data.values()))
    scratch = Path(_tmp.mkdtemp(prefix="ut_rd_")) / "map_regions.tga"
    scratch.write_bytes(raw)
    back = maptga.read(scratch)[0].convert("RGB")
    check(f"     {rmod.name}: the re-encoded layer reads back at "
          f"{back.width}x{back.height} with no pixel of {target.name} left in it",
          (back.width, back.height) == (rcm.terrain.width, rcm.terrain.height)
          and tuple(target.rgb) not in set(back.getdata()))

if not seen:
    print("  SKIPPED - no installed mod has a region with a neighbour")

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
