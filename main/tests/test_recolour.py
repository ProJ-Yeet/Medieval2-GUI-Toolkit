"""Changing a region's colour, and the renumbering that does not happen (36).

    python -m tests.test_recolour

One little map written here - a 12x8 regions layer with four provinces on it,
one of them in two disconnected pieces, one with a settlement pixel inside it -
plus the ``descr_regions.txt`` that declares them.

**The suite is about the write-up's premise being wrong.** Phase 36 was scoped
on "changing one colour can renumber every region after it". It cannot: a region
ID is the order a colour is first MET in a row-major scan, which is a fact about
where a province's pixels are, and a recolour moves no pixel. Section 3 proves
that on the little map and section 7 proves it on every installed one.

Section 2 is the other measured fact: the recolour is every tile of the colour,
not a bucket fill, because a province is not always one connected blob.

Section 5 is the pair that must never come apart - the pixels and the record's
colour line are one save, and a save with only half of it is refused.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campaint, campmap, config
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def ids_of(cm, recoloured="", new_key=-1):
    """``{province: region ID}`` while a recolour is pending but unsaved.

    The pixels are the new colour and ``descr_regions.txt`` in memory still
    names the old one, so the repainted province has no ``record`` hanging off
    its index entry and would silently drop out of a plain name->id sweep. That
    is a fact about the half-saved state and not about the numbering, so the one
    province being recoloured is looked up by the colour it now carries. Every
    other province is read exactly as it always is.
    """
    out = {r.name: r.region_id for r in cm.index.regions if r.record}
    if recoloured:
        reg = cm.index.by_key.get(new_key)
        if reg is not None:
            out[recoloured] = reg.region_id
    return out


# ---- the little map ----------------------------------------------------------

W, H = 12, 8
SEA = (41, 140, 233)
A = (200, 110, 100)      # Alpha - one blob
B = (100, 200, 110)      # Beta  - TWO blobs, which is the point of it
C = (110, 100, 200)      # Gamma - one blob, with a settlement pixel inside
SETT = (0, 0, 0)

#: row by row, so the map is readable as a picture and the scan order is obvious
PICTURE = [
    "............",
    ".AAA...BB...",
    ".AAA...BB...",
    ".....CCC....",
    ".....CSC....",
    ".....CCC....",
    ".BB.........",     # Beta's second blob, AFTER Gamma in the scan
    "............",
]
LETTERS = {".": SEA, "A": A, "B": B, "C": C, "S": SETT}

REGIONS = (
    ";;;;;;;;;;;;;;;;\r\n"
    "\r\n"
    "Alpha_Province\r\n"
    "\tAlphaton\r\n"
    "\tnorthmen\r\n"
    "\tNorth_Rebels\r\n"
    f"\t{A[0]} {A[1]} {A[2]}\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Beta_Province\r\n"
    "\tBetaton\r\n"
    "\tnorthmen\r\n"
    "\tNorth_Rebels\r\n"
    f"\t{B[0]} {B[1]} {B[2]}\t; two pieces, on purpose\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Gamma_Province\r\n"
    "\tGammaton\r\n"
    "\tnorthmen\r\n"
    "\tNorth_Rebels\r\n"
    f"\t{C[0]} {C[1]} {C[2]}\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
)


#: the real file's shape, block by block, because `parse_terrain` reads blocks
#: and a `dimensions 12 8` one-liner is not one.
TERRAIN = (
    "dimensions\r\n{\r\n"
    f"\twidth  {W}\r\n\theight  {H}\r\n" + "}\r\n"
    "heights\r\n{\r\n\tmin_sea_height  -3406.782\r\n"
    "\tmax_land_height  7511.272\r\n}\r\n"
    "roughness\r\n{\r\n\tmin  50.000\r\n\tmax  200.000\r\n}\r\n"
    "fractal\r\n{\r\n\tmultiplier  0.500\r\n}\r\n"
    "lattitude\r\n{\r\n\tmin  22.000\r\n\tmax  56.000\r\n}\r\n"
)


def little_mod():
    """A mod with the ten layers the reader needs, all 12x8."""
    from PIL import Image
    root = Path(_tmp.mkdtemp(prefix="ut_rcl_"))
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True)

    px = []
    for row in PICTURE:
        for ch in row:
            px.append(LETTERS[ch])
    img = Image.new("RGB", (W, H))
    img.putdata(px)
    img.save(base / "map_regions.tga")

    # Every other layer the reader wants, flat - and each at ITS OWN grid, which
    # is the rule this fixture has to obey or the map will not open: a `centre`
    # layer is 2W+1 and a `double` one is 2W. The heights matter beyond that: a
    # tile the heights call sea is skipped by the numbering, so all of it is
    # land here and every province really is counted.
    grids = {"tile": (W, H), "centre": (2 * W + 1, 2 * H + 1),
             "double": (2 * W, 2 * H), "advisory": (W, H), "free": (W, H)}
    for ly in campmap.LAYERS:
        if ly["code"] == "regions":
            continue
        fill = {"heights": (100, 100, 100), "ground_types": (0, 100, 0),
                "climates": (12, 90, 200), "fog": (255, 255, 255)
                }.get(ly["code"], (0, 0, 0))
        Image.new("RGB", grids[ly["size"]], fill).save(base / ly["file"])

    kb.write_text(base / "descr_regions.txt", REGIONS, campmap.ENCODING)
    kb.write_text(base / "descr_terrain.txt", TERRAIN, campmap.ENCODING)
    return Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

NEW = (7, 222, 31)      # a colour the little map does not use


# ---- 1: the map reads, and the IDs are the scan order ------------------------

print("\n1. the little map")

mod = little_mod()
cm = campmap.CampaignMap(mod)
ids = {r.name: r.region_id for r in cm.index.regions if r.record}
print(f"     ids: {ids}")
check(f"  three declared provinces, all numbered: {sorted(ids)}",
      len(ids) == 3 and all(v >= 0 for v in ids.values()))
check("  and the order is the scan order, not the file order: Alpha is met "
      "before Beta, Beta before Gamma",
      ids["Alpha_Province"] < ids["Beta_Province"] < ids["Gamma_Province"])


# ---- 2: it is every tile of the colour, not a bucket -------------------------

print("\n2. the whole colour, not one blob")

beta = cm.regions.by_name("Beta_Province")
whole = campaint.region_tiles(cm, beta.rgb_key)
blob = campaint.flood(cm, "regions", whole[0][0], whole[0][1])
check(f"  Beta is {len(whole)} tiles in two pieces; a bucket from the first "
      f"reaches only {len(blob)}", len(whole) == 6 and len(blob) == 4)
check("  so region_tiles finds tiles a flood from one of them never would",
      set(blob) < set(whole))
check("  and it finds nothing at all for a colour the map does not carry",
      campaint.region_tiles(cm, campmap.key(NEW)) == [])


# ---- 3: the phase's finding - a recolour does not renumber -------------------

print("\n3. the renumbering that does not happen")

for who in ("Alpha_Province", "Beta_Province", "Gamma_Province"):
    m2 = little_mod()
    c2 = campmap.CampaignMap(m2)
    before = {r.name: r.region_id for r in c2.index.regions if r.record}
    s2, _ = campaint.session(f"t3-{who}", m2, c2)
    campaint.recolour(s2, {"region": who, "rgb": list(NEW)})
    after = ids_of(c2, who, campmap.key(NEW))
    moved = {n: (before[n], after.get(n)) for n in before if before[n] != after.get(n)}
    check(f"  recolouring {who} (id {before[who]}) moves no region ID: {moved}",
          not moved)


# ---- 4: what it refuses, and the one case that WOULD renumber ---------------

print("\n4. the refusals")

m4 = little_mod()
c4 = campmap.CampaignMap(m4)
for rgb, want, why in (
        (SETT, "marker colour", "black, where a settlement stands"),
        (A, "already Alpha_Province's colour", "another province's colour"),
        (B, "is already 100 200 110", "the colour it already has"),
        (SEA, "no record declares it", "a colour painted but undeclared")):
    faults = campaint.recolour_faults(c4, "Beta_Province", tuple(rgb))
    check(f"  {why}: {(faults or ['(allowed)'])[0][:56]}",
          any(want in f for f in faults))
check("  a colour nothing uses is allowed",
      campaint.recolour_faults(c4, "Beta_Province", NEW) == [])
check("  a province that is not there is refused by name",
      any("no region called" in f
          for f in campaint.recolour_faults(c4, "Nope_Province", NEW)))

# and the merge really does renumber, which is why it is refused above
m4b = little_mod()
c4b = campmap.CampaignMap(m4b)
before = {r.name: r.region_id for r in c4b.index.regions if r.record}
s4b, _ = campaint.session("t4b", m4b, c4b)
campaint._stroke_over(s4b, campaint.region_tiles(c4b, campmap.key(B)),
                      {"regions": campmap.key(A)}, "brush", {})
after = {r.name: r.region_id for r in c4b.index.regions if r.record}
check(f"  painting Beta in Alpha's colour DOES renumber - Gamma "
      f"{before['Gamma_Province']} -> {after.get('Gamma_Province')} - which is "
      f"the merge the refusal is protecting against",
      after.get("Gamma_Province") != before["Gamma_Province"])


# ---- 5: the two halves are one save -----------------------------------------

print("\n5. the pixels and the record, together")

m5 = little_mod()
c5 = campmap.CampaignMap(m5)
s5, _ = campaint.session("t5", m5, c5)
out = campaint.recolour(s5, {"region": "Gamma_Province", "rgb": list(NEW)})
check(f"  Gamma is a 3x3 block with a settlement in the middle, so it is 8 "
      f"tiles of its own colour: {out['tiles']} repainted", out["tiles"] == 8)
# The marker guard every stroke carries cannot fire on a recolour, and that is
# worth a check rather than an assumption: the tiles are chosen BY being the
# region's colour, and a settlement pixel is black. So the settlement survives
# because it was never in the list, not because something stepped over it.
check("  and nothing had to be protected, because a marker pixel is a "
      "different colour and so was never in the list",
      out["protected"] == 0)
after5px = campaint.region_tiles(c5, campmap.key(SETT))
check(f"  the settlement pixel is still there and still black: {after5px}",
      after5px == [(6, 4)])
check("  the session carries the record half until it is saved",
      (s5.recolour or {}).get("name") == "Gamma_Province")

p5 = campaint.plan_paint(s5)
check(f"  the plan is clean: {p5.errors}", not p5.errors)
check("  it writes descr_regions.txt as well as the layer",
      bool(p5.region_text) and "regions" in p5.data)
check("  and it says, in the changes, that nothing renumbers",
      any("no region ID moves" in c for c in p5.changes))
after5 = campmap.parse_regions(p5.region_text)
check("  exactly one line of the record file differs",
      sum(1 for a, b in zip(c5.regions.lines, after5.lines) if a != b) == 1)
check(f"  and it is Gamma's colour line: "
      f"{after5.by_name('Gamma_Province').rgb}",
      after5.by_name("Gamma_Province").rgb == NEW)

# the half-save that must be refused
m5b = little_mod()
c5b = campmap.CampaignMap(m5b)
s5b, _ = campaint.session("t5b", m5b, c5b)
campaint.recolour(s5b, {"region": "Alpha_Province", "rgb": list(NEW)})
campaint.undo_stroke(s5b)
p5b = campaint.plan_paint(s5b)
check(f"  undoing the stroke and saving is refused rather than half-written: "
      f"{(p5b.errors or ['(none)'])[0][:60]}",
      any("has been undone" in e for e in p5b.errors))
campaint.cancel_recolour(s5b)
check("  and Cancel forgets it, leaving nothing to save",
      s5b.recolour is None)


# ---- 6: applied, and read back off disk -------------------------------------

print("\n6. the save")

m6 = little_mod()
c6 = campmap.CampaignMap(m6)
(Path(m6.data) / campmap.RWM_REL).write_bytes(b"stale")
s6, _ = campaint.session("t6", m6, c6)
BEFORE6 = {r.name: r.region_id for r in c6.index.regions if r.record}
campaint.recolour(s6, {"region": "Beta_Province", "rgb": list(NEW)})
res = campaint.apply_paint(campaint.plan_paint(s6))
check(f"  one log entry, id {str(res.get('id'))[:12]}…", bool(res.get("id")))
man = res["record"]["manifest"]
check("  both files are in the one backup set",
      campmap.REGIONS_REL in man["backed_up"]
      and f"{campmap.BASE_REL}/map_regions.tga" in man["backed_up"])
check("  and the stale compiled map is deleted",
      campmap.RWM_REL in man["deleted"])

c6b = campmap.CampaignMap(Mod(m6.root))
rec6 = c6b.regions.by_name("Beta_Province")
reg6 = c6b.index.by_key.get(campmap.key(NEW))
check(f"  read off disk: the record says {rec6.rgb} and {reg6.pixels if reg6 else 0} "
      f"tiles carry it", rec6.rgb == NEW and reg6 is not None and reg6.pixels == 6)
check("  not one tile is left in the old colour",
      campaint.region_tiles(c6b, campmap.key(B)) == [])
check("  no region was emptied, which is the guard that would have caught a "
      "half-write", campaint._emptied(c6b) == [])
after6 = {r.name: r.region_id for r in c6b.index.regions if r.record}
check(f"  and off disk, with fresh eyes, no ID moved: {after6}",
      BEFORE6 == after6)


# ---- 7: every installed mod, planned and never applied ----------------------

print("\n7. the installed mods")

mods = _realmod.installed()
if not mods:
    print("  SKIPPED - no installed mod")
else:
    for root in mods:
        real = Mod(root)
        try:
            rcm = campmap.CampaignMap(real)
        except Exception as exc:                          # noqa: BLE001
            print(f"  -- {real.name}: no map ({str(exc)[:40]})")
            continue
        print(f"  -- {real.name}")
        decl = [r for r in rcm.index.regions if r.record and r.region_id >= 0]
        loose = {campmap.key(c) for c in rcm.index.colours}
        free = next((r, g, 11) for r in range(1, 255) for g in range(1, 255)
                    if campmap.key((r, g, 11)) not in loose)
        # the first in the scan and one in the middle, which are the two cases
        # the write-up said would be worst
        for label, pick in (("the first", 0), ("a middle", len(decl) // 2)):
            target = sorted(decl, key=lambda r: r.region_id)[pick]
            cmx = campmap.CampaignMap(real)
            before = {r.name: r.region_id for r in cmx.index.regions if r.record}
            sx, _ = campaint.session(f"t7-{real.name}-{pick}", real, cmx)
            o = campaint.recolour(sx, {"region": target.name, "rgb": list(free)})
            after = ids_of(cmx, target.name, campmap.key(free))
            moved = [n for n in before if before[n] != after.get(n)]
            check(f"     recolouring {label} ({target.name}, id "
                  f"{target.region_id}, {o['tiles']:,} tiles) moves "
                  f"{len(moved)} region ID(s)", not moved)
            campaint.drop(f"t7-{real.name}-{pick}")
        # the bucket would not do, and this is by how much
        multi = [r for r in decl
                 if len(campaint.flood(rcm, "regions", r.anchor[0], r.anchor[1]))
                 != r.pixels]
        print(f"       {len(multi)} of {len(decl)} regions are not one blob")
        check("     and at least one of them is, or the bucket would have done",
              len(multi) > 0)


# ---- 8: the route -----------------------------------------------------------

print("\n8. POST /api/map/recolour")

import json                                                       # noqa: E402
import shutil                                                     # noqa: E402
import threading                                                  # noqa: E402
import urllib.error                                               # noqa: E402
import urllib.request                                             # noqa: E402

from unittransfer.server import Handler, Registry, _Server         # noqa: E402

med2 = Path(_tmp.mkdtemp(prefix="ut_rcl_med2_"))
staged = little_mod()
shutil.copytree(staged.root, med2 / "mods" / "Tiny")
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    r = post("/api/map/recolour",
             {"mod": "Tiny", "region": "Alpha_Province", "rgb": list(NEW)})
    check(f"  the route repaints and answers with the tiles: {r.get('tiles')}",
          r.get("tiles") == 6 and not r.get("error"))
    check("  and the session state carries the pending record change",
          ((r.get("state") or {}).get("recolour") or {}).get("name")
          == "Alpha_Province")
    check("  nothing is on disk yet",
          campmap.read_regions(Mod(med2 / "mods" / "Tiny"))
          .by_name("Alpha_Province").rgb == A)

    r = post("/api/map/paint_plan", {"mod": "Tiny"})
    check("  paint_plan sees both halves",
          any("descr_regions.txt" in c for c in r["plan"]["changes"])
          and any("map_regions.tga" in c for c in r["plan"]["changes"]))

    r = post("/api/map/paint_apply", {"mod": "Tiny"})
    check(f"  paint_apply writes them together: {bool(r.get('id'))}",
          bool(r.get("id")) and not r.get("error"))
    check("  read off disk, the record moved with the pixels",
          campmap.read_regions(Mod(med2 / "mods" / "Tiny"))
          .by_name("Alpha_Province").rgb == NEW)

    r = post("/api/map/recolour",
             {"mod": "Tiny", "region": "Beta_Province", "rgb": list(NEW)})
    check(f"  a colour now in use is refused by the route: "
          f"{str(r.get('error'))[:50]}",
          "already" in str(r.get("error", "")))
    r = post("/api/map/recolour_cancel", {"mod": "Tiny"})
    check("  and cancel clears the pending record change",
          not (r.get("state") or {}).get("recolour"))
finally:
    httpd.shutdown()


print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
