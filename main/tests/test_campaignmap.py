"""A campaign that ships its own map files is drawn, judged and fixed on them.

    python -m tests.test_campaignmap

The engine reads each map file separately, a campaign folder's own copy first
(B1's decision). 22b made the two writers that judge a tile read the campaign's
copy; this suite covers the rest of the map screen:

1. A copy of a real mod with two campaigns written here: one that ships only
   its own ``map_FE.tga``, as every DaC and Reforged campaign does, and one
   that ships its own ``map_heights.tga`` with a settlement's tile sunk into
   the sea. Which object each is judged on, which file each layer is drawn
   from, what the screen is told, and when the brush is refused.
2. The validator on the second: the finding names the campaign's own file, the
   height fix writes that file, and the ``map.rwm`` it deletes is the one beside
   it - the base map's stays.
3. The routes: the manifest, a layer, a check and a stroke, each for the
   campaign asked for.
4. Every installed campaign: what it ships, and what the manifest says of it.
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campaint, campmap, campstrat, config, mapcheck
from unittransfer.maptga import encode
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


roots = [m for m in _realmod.installed()
         if (m / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]
if not roots:
    print("SKIPPED - no installed mod with a map to copy")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

src = roots[0]
med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
data = med2 / "mods" / "TwoMaps" / "data"
(data / campmap.BASE_REL).mkdir(parents=True)
for p in (src / "data" / campmap.BASE_REL).iterdir():
    if p.is_file():
        shutil.copy2(p, data / campmap.BASE_REL / p.name)
(data / campmap.RWM_REL).write_bytes(b"base's compiled map")
strat = next((src / "data" / campstrat.CAMPAIGN_DIR_REL / c / campstrat.STRAT_NAME)
             for c in ("imperial_campaign",)
             if (src / "data" / campstrat.CAMPAIGN_DIR_REL / c
                 / campstrat.STRAT_NAME).is_file())
FE_ONLY, OWN = "imperial_campaign", "custom/OwnHeights"
for camp in (FE_ONLY, OWN):
    d = data / campstrat.CAMPAIGN_DIR_REL / camp
    d.mkdir(parents=True)
    shutil.copy2(strat, d / campstrat.STRAT_NAME)
fe_src = next((p for p in (src / "data" / campstrat.CAMPAIGN_DIR_REL / FE_ONLY / "map_FE.tga",
                           src / "data" / campmap.BASE_REL / "map_FE.tga") if p.is_file()), None)
fe_home = data / campstrat.CAMPAIGN_DIR_REL / FE_ONLY
if fe_src is not None:
    shutil.copy2(fe_src, fe_home / "map_FE.tga")
own_home = data / campstrat.CAMPAIGN_DIR_REL / OWN
(own_home / "map.rwm").write_bytes(b"the campaign's compiled map")

mod = Mod(med2 / "mods" / "TwoMaps")
base = campmap.CampaignMap(mod)
# the settlement whose tile the campaign's own heights put in the sea
reg = next(r for r in base.index.regions if r.name and r.settlement)
tx, ty = reg.settlement
img = base.layer("heights").convert("RGB")
x0, y0, x1, y1 = campaint.block(campmap.LAYER_BY_CODE["heights"]["size"], tx, ty)
px = img.load()
for y in range(y0, y1 + 1):
    for x in range(x0, x1 + 1):
        if 0 <= x < img.width and 0 <= y < img.height:
            px[x, y] = (0, 0, 0)
(own_home / "map_heights.tga").write_bytes(encode(img, base.info("heights")))
print(f"  a copy of {src.name}'s map; {OWN} sinks {reg.name}'s settlement at "
      f"{tx},{ty}")


# ---- 1) which map, which file ------------------------------------------------
print("\n1) which map each campaign is drawn and judged on")

check(f"{FE_ONLY} ships {campmap.shipped(mod, FE_ONLY)} and {OWN} "
      f"{campmap.shipped(mod, OWN)}",
      campmap.shipped(mod, OWN) == ["map_heights.tga"]
      and (fe_src is None or campmap.shipped(mod, FE_ONLY) == ["map_FE.tga"]))
check("a campaign whose only copy is a picture nothing is decided on is judged "
      "on the base map's own object - the one the brush paints",
      campmap.campaign_map(mod, FE_ONLY, base) is base
      and campmap.campaign_map(mod, "", base) is base)
own = campmap.campaign_map(mod, OWN, base)
check("a campaign with its own heights is judged on a map reading that folder "
      "first, and the same object comes back while nothing changes on disk",
      own is not base and own.path("heights") == own_home / "map_heights.tga"
      and own.path("regions") == data / campmap.BASE_REL / "map_regions.tga"
      and campmap.campaign_map(mod, OWN, base) is own)
check("the sunk tile is sea on the campaign's map and land on the base's",
      own.sea[ty * own.terrain.width + tx] and not base.sea[ty * base.terrain.width + tx])
if fe_src is not None:
    fe = campmap.layer_map(mod, FE_ONLY, base, "fe")
    check("its front-end picture is drawn from its own folder, and every other "
          "layer from the base map's object",
          fe.path("fe") == fe_home / "map_FE.tga"
          and campmap.layer_map(mod, FE_ONLY, base, "regions") is base)
check("rel_of names the file each map reads",
      campmap.rel_of(own, "map_heights.tga") ==
      f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map_heights.tga"
      and campmap.rel_of(own, "map_regions.tga") == f"{campmap.BASE_REL}/map_regions.tga"
      and campmap.rel_of(base, "map_heights.tga") == f"{campmap.BASE_REL}/map_heights.tga")
hv = campmap.home_view(mod, OWN, own)
check(f"the screen is told: own {hv['own']}, judged {hv['judged']}, paints "
      f"{hv['paints']}, readers {hv['readers']}",
      hv["own"] == ["map_heights.tga"] and hv["judged"] and not hv["paints"]
      and FE_ONLY in hv["readers"])
hv0 = campmap.home_view(mod, "", base)
check("and of the default campaign, by its name, that the brush paints what it shows",
      hv0["campaign"] == FE_ONLY and not hv0["judged"] and hv0["paints"])
why = campaint.paints_for(mod, OWN, "paint")
check(f"a stroke is refused on the campaign that does not show the base map: {why[:90]}...",
      why and "map_heights.tga" in why and FE_ONLY in why)
check("and on the start of a new province, which paints too",
      bool(campaint.paints_for(mod, OWN, "region_start")))
check("but undo, redo, save and discard stay open - they act on strokes made "
      "on a campaign that did show them",
      not any(campaint.paints_for(mod, OWN, a)
              for a in ("paint_undo", "paint_redo", "paint_apply", "paint_discard")))
check("and nothing is refused where the base map is what is on the screen",
      not campaint.paints_for(mod, FE_ONLY, "paint")
      and not campaint.paints_for(mod, "", "paint"))


# ---- 2) the validator on the campaign's own map ----------------------------
print("\n2) Check and its height fix, on the campaign's own map")

rep_base = mapcheck.run(mod, base, FE_ONLY, use_baseline=False)
rep_own = mapcheck.run(mod, own, OWN, use_baseline=False)
mine = [f for f in rep_own.findings if f.code in ("marker.sea", "height.ambiguous")
        and f.tile == (tx, ty)]
check(f"the sunk settlement is found on the campaign's map and not on the "
      f"base's: {[f.code for f in mine]}",
      mine and not [f for f in rep_base.findings
                    if f.code == "marker.sea" and f.tile == (tx, ty)])
check(f"and the finding names the campaign's own file: {mine[0].file if mine else '?'}",
      mine and all(f.file == f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map_heights.tga"
                   for f in mine))
others = {f.file for f in rep_own.findings if f.file.endswith(".tga")}
check("every other layer's findings still name world/maps/base",
      all(f.startswith(campmap.BASE_REL) or f.startswith(
          f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map_heights") for f in others))
fx = [f for f in rep_own.findings if f.fix == "heights_black"]
if not fx:
    print("  [skip] the sunk tile reads as sea, not as an ambiguous black one")
else:
    plan = mapcheck.plan_fix(mod, ["heights_black"], own, OWN)
    check(f"the height fix writes the campaign's copy: {plan.payload()['files']}",
          plan.payload()["ok"] and plan.payload()["files"] ==
          [f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map_heights.tga"])
    base_heights = (data / campmap.BASE_REL / "map_heights.tga").read_bytes()
    own_heights = (own_home / "map_heights.tga").read_bytes()
    res = mapcheck.apply_fix(plan)
    check("and the compiled map it deletes is the campaign's, not the base's",
          not (own_home / "map.rwm").exists()
          and (data / campmap.RWM_REL).read_bytes() == b"base's compiled map"
          and f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map.rwm" in res["record"]["manifest"]["deleted"])
    check("the base map's heights were never touched",
          (data / campmap.BASE_REL / "map_heights.tga").read_bytes() == base_heights
          and (own_home / "map_heights.tga").read_bytes() != own_heights)
    # put both back by hand, for the routes below
    (own_home / "map_heights.tga").write_bytes(own_heights)
    (own_home / "map.rwm").write_bytes(b"the campaign's compiled map")


# ---- 3) the routes ------------------------------------------------------------
print("\n3) /api/map, /api/map/layer, /api/map/check and /api/map/paint")

from unittransfer.server import Handler, Registry, _Server  # noqa: E402
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"  serving {BASE}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return r.read()


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


q = f"mod=TwoMaps&campaign={OWN}"
try:
    m0 = get("/api/map?mod=TwoMaps")
    m1 = get(f"/api/map?{q}")
    rels = {ly["code"]: ly["rel"] for ly in m1["layers"]}
    check(f"the manifest for {OWN} says it reads its own map and which files: "
          f"{m1['campaign_map']['own']}",
          m1["campaign_map"]["judged"] and not m1["campaign_map"]["paints"]
          and rels["heights"].endswith(f"{OWN}/map_heights.tga")
          and rels["regions"] == f"{campmap.BASE_REL}/map_regions.tga")
    check("and the manifest with no campaign is the default one, painting what it shows",
          m0["campaign_map"]["campaign"] == FE_ONLY and m0["campaign_map"]["paints"])
    if fe_src is not None:
        fe_rel = {ly["code"]: ly["rel"] for ly in m0["layers"]}["fe"]
        check(f"the default campaign's front-end layer row names its own copy: {fe_rel}",
              fe_rel == f"{campstrat.CAMPAIGN_DIR_REL}/{FE_ONLY}/map_FE.tga")
    h_base = raw("/api/map/layer?mod=TwoMaps&code=heights&format=rgb")
    h_own = raw(f"/api/map/layer?{q}&code=heights&format=rgb")
    w = m1["width"]
    i = (ty * w + tx) * 3
    check("the heights layer served for the campaign is its own, black on the sunk "
          "tile, and the base's is not",
          h_own[i:i + 3] == b"\x00\x00\x00" and h_base[i:i + 3] != b"\x00\x00\x00")
    ck = get(f"/api/map/check?{q}")
    named = {f["file"] for f in ck["findings"] if f.get("tile") == [tx, ty]}
    check(f"/api/map/check judges the campaign's map: {sorted(named)}",
          f"{campstrat.CAMPAIGN_DIR_REL}/{OWN}/map_heights.tga" in named)
    pr = get(f"/api/map/probe?{q}&x={tx}&y={ty}")
    hrow = next(r for r in pr["layers"] if r["code"] == "heights")
    check("a probe of the tile reads the campaign's heights",
          hrow["rgb"] == [0, 0, 0])
    st = post("/api/map/paint", {"mod": "TwoMaps", "campaign": OWN, "tool": "pencil",
                                  "target": "climates", "rgb": [0, 0, 0],
                                  "points": [[tx, ty]]})
    check(f"a stroke sent with that campaign is refused, and says why: "
          f"{(st.get('error') or '')[:70]}...",
          "does not show" in (st.get("error") or ""))
    check("the palette is the base map's whichever campaign asks, since it is "
          "the brush's", get(f"/api/map/palette?{q}") == get("/api/map/palette?mod=TwoMaps"))
finally:
    httpd.shutdown()


# ---- 4) every installed campaign ----------------------------------------------
print("\n4) the installed campaigns")

for root in _realmod.installed():
    rmod = Mod(root)
    if not (rmod.data / campmap.BASE_REL / "descr_terrain.txt").exists():
        continue
    rbase = campmap.CampaignMap(rmod)
    for camp in campstrat.campaign_paths(rmod):
        mine = campmap.shipped(rmod, camp)
        cm = campmap.campaign_map(rmod, camp, rbase)
        hv = campmap.home_view(rmod, camp, cm)
        judged = any(n in campmap.MAP_FILES for n in mine)
        check(f"{root.name}/{camp}: ships {len(mine)} ({', '.join(mine) or 'none'}); "
              f"{'its own map' if judged else 'the base map'}, brush "
              f"{'off' if judged else 'on'}",
              hv["judged"] == judged and hv["paints"] == (not judged)
              and (cm is rbase) == (not judged)
              and all(hv["files"][n].startswith(f"{campstrat.CAMPAIGN_DIR_REL}/")
                      for n in mine))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
