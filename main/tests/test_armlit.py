"""Armory Studio's pre-rendered bake: a lit colour texture per source texture.

    python -m tests.test_armlit

Nothing installed is needed: the meshes and their images are made here.

1. the settings: defaults, and every number held inside its range
2. the light: ambient alone is even and never black; the key light makes the
   side facing it brighter; alpha and the texels no triangle covers are kept
3. Shadows: 0 is no shadow, 1 the full one, a half between the two; an object
   is shadowed by itself only
4. stacked UV islands: each texel is baked from one island, the biggest that
   covers it, so a stack is one flat tone and never a checker
5. the maps: a normal map tilts the light, the spec map's blue darkens (AO)
6. the maps beside a colour texture are found by name (``_d`` / ``_s`` / ``_n``)
"""
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import armlit  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


S = 64
GREY = np.full((S, S, 4), 128, np.uint8)
GREY[..., 3] = 77          # an alpha of its own, to be found again


def quad(x0, z0, x1, z1, y, up=True, uv=(0, 0, S, S)):
    """A level square at height ``y`` facing up or down, on the texels ``uv``."""
    pos = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    n = (0.0, 1.0 if up else -1.0, 0.0)
    u0, v0, u1, v1 = uv
    return pos, [n] * 4, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], [(0, 1, 2), (0, 2, 3)]


def scene(*parts):
    """Quads as one mesh: ``(quad, island, object)`` each."""
    pos, nrm, uv, tris, isl, obj = [], [], [], [], [], []
    for q, i, o in parts:
        base = len(pos)
        pos += q[0]; nrm += q[1]; uv += q[2]
        tris += [tuple(base + k for k in t) for t in q[3]]
        isl += [i] * len(q[3]); obj += [o] * len(q[3])
    return dict(pos=np.array(pos, float), nrm=np.array(nrm, float), uv=np.array(uv, float),
                tris=np.array(tris, int), island=np.array(isl, int), obj=np.array(obj, int))


def bake(sc, colour=GREY, spec=None, normal=None, **st):
    return armlit.bake_image(colour, spec, normal, settings=st, **sc)


TOP = dict(direction=0, height=90, softness=0, strength=1.0)      # the key light straight overhead

print("1) the settings")
d = armlit.settings_of(None)
check("defaults: ambient, a key light, half shadows",
      d["ambient"] > 0 and d["key"] is True and d["shadows"] == 0.5)
c = armlit.settings_of({"ambient": 99, "shadows": -3, "strength": "x", "height": 500, "softness": 7})
check("every number is held inside its range",
      c["ambient"] == 2.0 and c["shadows"] == 0.0 and c["strength"] == d["strength"]
      and c["height"] == 90.0 and c["softness"] == 1.0)

print("2) the light")
up = scene((quad(0, 0, 1, 1, 0, True, (0, 0, 32, 64)), 0, 0))
both = scene((quad(0, 0, 1, 1, 0, True, (0, 0, 32, 64)), 0, 0),
             (quad(5, 0, 6, 1, 0, False, (32, 0, 64, 64)), 1, 0))
out = bake(both, ambient=0.5, key=False)
check("ambient alone: nothing is black", out[..., :3].min() > 40)
check("ambient alone: one face is one tone", int(out[10:50, 4:28, 0].max()) - int(out[10:50, 4:28, 0].min()) <= 1)
out = bake(both, ambient=0.3, shadows=1.0, **TOP)
lit, away = int(out[32, 16, 0]), int(out[32, 48, 0])
check(f"the key light: the face towards it is brighter ({lit} > {away})", lit > away + 20)
check("the face turned away keeps its ambient light, not black", away > 30)
check("alpha is the source's", (out[..., 3] == 77).all())
half = bake(up, ambient=0.3, **TOP)
check("texels no triangle covers are left as they were", (half[:, 40:, :3] == 128).all())
check("the source image is not written to", (GREY[..., :3] == 128).all())

print("3) Shadows")
floor = quad(0, 0, 4, 4, 0, True, (0, 0, 64, 64))
roof = quad(1, 1, 2, 2, 1, True, (0, 0, 0.5, 0.5))          # over the floor's texels 16..32
under, clear = (24, 24), (56, 56)
shade = {}
for amount in (0.0, 0.5, 1.0):
    o = bake(scene((floor, 0, 0), (roof, 1, 0)), ambient=0.3, shadows=amount, **TOP)
    shade[amount] = (int(o[under][0]), int(o[clear][0]))
check(f"0: under the roof is as bright as beside it {shade[0.0]}", abs(shade[0.0][0] - shade[0.0][1]) <= 1)
check(f"1: under the roof is darker {shade[1.0]}", shade[1.0][0] < shade[1.0][1] - 20)
check("1: and still not black", shade[1.0][0] > 30)
check(f"0.5 lies between the two ({shade[0.5][0]})", shade[1.0][0] < shade[0.5][0] < shade[0.0][0])
o = bake(scene((floor, 0, 0), (roof, 1, 1)), ambient=0.3, shadows=1.0, **TOP)
check("another object's roof casts nothing on this one", abs(int(o[under][0]) - int(o[clear][0])) <= 1)

print("3b) more lights (2026-11-25): sun or point, as the card maker's")
c = armlit.settings_of({"lights": [{"type": "point", "strength": 9, "distance": -1, "height": "x"}, {}, {}, {}, 5]})
check("at most three, each held inside its range",
      len(c["lights"]) == 3 and c["lights"][0] == {"type": "point", "direction": -120.0, "height": 25.0,
                                                   "strength": 3.0, "distance": 0.2}
      and c["lights"][1]["type"] == "sun")
sun_up = dict(type="sun", direction=0, height=90, strength=1.0)
a = bake(up, ambient=0.3, **TOP)
b = bake(up, ambient=0.3, key=False, direction=0, height=90, softness=0, lights=[sun_up])
check("a sun overhead with the key light off lights as the key light does", np.array_equal(a, b))
two = bake(up, ambient=0.3, **TOP, lights=[sun_up])
check(f"a second light adds to the first ({int(two[32, 16, 0])} > {int(a[32, 16, 0])})", two[32, 16, 0] > a[32, 16, 0])
dim = bake(up, ambient=0.3, key=False, softness=0, lights=[dict(sun_up, strength=0)])
check("a light at strength 0 adds nothing", np.array_equal(dim, bake(up, ambient=0.3, key=False)))
near_pt = bake(up, ambient=0.1, key=False, softness=0, lights=[dict(type="point", direction=0, height=90, strength=1, distance=1)])
far_pt = bake(up, ambient=0.1, key=False, softness=0, lights=[dict(type="point", direction=0, height=90, strength=1, distance=6)])
check(f"a point light fades with distance ({int(near_pt[32, 16, 0])} > {int(far_pt[32, 16, 0])})",
      near_pt[32, 16, 0] > far_pt[32, 16, 0] + 10)
o = bake(scene((floor, 0, 0), (roof, 1, 0)), ambient=0.3, shadows=1.0, key=False, softness=0,
         lights=[dict(sun_up)])
check("an extra light casts its own shadow", int(o[under][0]) < int(o[clear][0]) - 20)

print("4) stacked UV islands")
big_up = quad(0, 0, 1, 1, 0, True, (0, 0, 40, 40))
small_down = quad(5, 0, 6, 1, 0, False, (8, 8, 24, 24))            # wholly on the big one's texels
o = bake(scene((small_down, 0, 0), (big_up, 1, 0)), ambient=0.3, **TOP)
patch = o[2:38, 2:38, 0].astype(int)
check("an island on a bigger one's texels is skipped: the stack is one tone",
      patch.max() - patch.min() <= 1 and patch.min() > 135)
part_down = quad(5, 0, 6, 1, 0, False, (30, 30, 60, 60))           # half on, half off
o = bake(scene((part_down, 0, 0), (big_up, 1, 0)), ambient=0.3, **TOP)
check("a partly overlapping island: the shared texels are the bigger one's",
      int(o[32:38, 32:38, 0].min()) > 135)
check("and its own texels are its own", int(o[45:58, 45:58, 0].max()) < 130)

print("5) the maps")
flat_n = np.zeros((S, S, 4), np.uint8); flat_n[...] = (128, 128, 255, 255)
tilt_n = flat_n.copy(); tilt_n[:, 32:] = (230, 128, 160, 255)      # leaning along +u
side = dict(direction=90, height=20, softness=0, strength=1.0)    # light from +x
wall = scene((quad(0, 0, 1, 1, 0, True, (0, 0, 64, 64)), 0, 0))
a = bake(wall, normal=flat_n, ambient=0.2, shadows=0, **side)
b = bake(wall, normal=tilt_n, ambient=0.2, shadows=0, **side)
check("a flat normal map changes nothing", abs(int(a[32, 48, 0]) - int(bake(wall, ambient=0.2, shadows=0, **side)[32, 48, 0])) <= 1)
check(f"a normal leaning towards the light is brighter ({b[32, 48, 0]} > {a[32, 48, 0]})",
      int(b[32, 48, 0]) > int(a[32, 48, 0]) + 15)
ao = np.zeros((S, S, 4), np.uint8); ao[...] = (0, 0, 255, 255); ao[:, 32:, 2] = 60
o = bake(wall, spec=ao, ambient=0.6, key=False)
check("the spec map's blue is AO: it darkens, never to black",
      30 < int(o[32, 48, 0]) < int(o[32, 16, 0]) - 15)

print("6) the maps beside a colour texture")
with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    for name in ("helm_d.png", "helm_s.png", "helm_n.png", "cloak.png", "cloak_spec.png", "cloak_norm.png"):
        (t / name).write_bytes(b"x")
    check("x_d -> x_s and x_n", Path(armlit.sibling(str(t / "helm_d.png"), "s")).name == "helm_s.png"
          and Path(armlit.sibling(str(t / "helm_d.png"), "n")).name == "helm_n.png")
    check("x -> x_spec and x_norm", Path(armlit.sibling(str(t / "cloak.png"), "s")).name == "cloak_spec.png"
          and Path(armlit.sibling(str(t / "cloak.png"), "n")).name == "cloak_norm.png")
    check("none there: an empty answer", armlit.sibling(str(t / "helm_s.png"), "s") == "")

print("7) the project's objects, baked to files")
from PIL import Image  # noqa: E402
from unittransfer import armory  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    armory.ARMORY_DIR = t / "armory"
    armory.SHEETS_DIR = armory.ARMORY_DIR / "sheets"
    Image.fromarray(GREY, "RGBA").save(t / "plate_d.png")
    Image.fromarray(ao, "RGBA").save(t / "plate_s.png")
    Image.fromarray(flat_n, "RGBA").save(t / "plate_n.png")
    (t / "kit.obj").write_text("""
v 0 0 0
v 1 0 0
v 1 0 1
v 0 0 1
v 5 0 0
v 6 0 0
v 6 0 1
v 5 0 1
vt 0 0
vt 0.5 0
vt 0.5 1
vt 0 1
vn 0 1 0
vn 0 -1 0
o top
f 1/1/1 2/2/1 3/3/1 4/4/1
o under
f 5/1/2 6/2/2 7/3/2 8/4/2
o bare
f 5/1/2 6/2/2 7/3/2 8/4/2
""", encoding="utf-8")
    asset = {"kind": "external", "path": str(t / "kit.obj"),
             "textures": {"0": str(t / "plate_d.png"), "1": str(t / "plate_d.png"), "2": str(t / "nothing.png")}}
    key = armory.asset_key(asset)
    proj = {"assets": [asset], "objects": [
        {"id": i + 1, "name": n, "mesh": n, "src": [{"asset": key, "group": i}]}
        for i, n in enumerate(("top", "under", "bare"))]}
    res = armlit.bake_objects(proj, [1, 3], None, dict(ambient=0.3, **TOP))
    one = res["baked"][0] if res["baked"] else {}
    check("one lit texture for the one colour texture, its maps found",
          len(res["baked"]) == 1 and one["objects"] == [1] and one["spec"] and one["normal"])
    check("an object with no texture is skipped, and said so", res["skipped"] == [{"id": 3, "why": "no_texture"}])
    out_path = Path(one.get("path") or "x")
    check("written as a PNG under the armory's sheets, where the page may read it",
          out_path.suffix == ".png" and armory.texture_allowed(str(out_path)))
    check("the source's normal map is copied beside it, for the export",
          out_path.with_name(out_path.stem + "_norm.png").is_file())
    img = np.asarray(Image.open(out_path).convert("RGBA")) if out_path.is_file() else GREY
    check(f"the object's texels are lit ({img[32, 10, 0]}), the rest and the alpha kept",
          img[32, 10, 0] > 135 and (img[:, 40:, :3] == 128).all() and (img[..., 3] == 77).all())
    check("the source texture is as it was", (np.asarray(Image.open(t / "plate_d.png"))[..., :3] == 128).all())
    # baked once, the object wears the lit texture; a second bake starts from the source again
    proj["objects"][0].update(sheet=str(out_path), lit={"src": None})
    again = armlit.bake_objects(proj, [1], None, dict(ambient=0.3, **TOP))
    img2 = np.asarray(Image.open(again["baked"][0]["path"]).convert("RGBA"))
    check("a second bake starts from the source, not from the lit texture",
          again["baked"][0]["source"] == str(t / "plate_d.png") and abs(int(img2[32, 10, 0]) - int(img[32, 10, 0])) <= 1)
    # 2026-11-25: two objects stacked on the same texels each get a lit texture of
    # their own, so each wears its own light: the top one lit, the one under it not
    two = armlit.bake_objects(proj, [1, 2], None, dict(ambient=0.3, **TOP))
    by = {b["objects"][0]: b for b in two["baked"]}
    check("two objects on one texture, stacked: a file each",
          len(two["baked"]) == 2 and sorted(by) == [1, 2] and by[1]["path"] != by[2]["path"]
          and all(b["source"] == str(t / "plate_d.png") for b in two["baked"]))
    up_img = np.asarray(Image.open(by[1]["path"]).convert("RGBA")) if 1 in by else GREY
    down_img = np.asarray(Image.open(by[2]["path"]).convert("RGBA")) if 2 in by else GREY
    check(f"  each lit as its own surface faces (top {up_img[32, 10, 0]}, under {down_img[32, 10, 0]})",
          int(up_img[32, 10, 0]) > int(down_img[32, 10, 0]) + 30)
    check("  each file's texels one tone", np.ptp(up_img[4:60, 2:30, 0].astype(int)) <= 1
          and np.ptp(down_img[4:60, 2:30, 0].astype(int)) <= 1)
    check("  the lit textures beside each other's are kept apart by name",
          Path(by[1]["path"]).parent == Path(by[2]["path"]).parent)
    # 2026-11-24: the viewport's preview, the same bake at a small size, kept apart
    prev = armlit.bake_objects(proj, [1], None, dict(ambient=0.3, **TOP), preview=24)
    pp = Path(prev["baked"][0]["path"]) if prev["baked"] else Path("x")
    pimg = np.asarray(Image.open(pp).convert("RGBA")) if pp.is_file() else GREY
    check("a preview is the same bake, no bigger than asked, in a folder of its own",
          pp.parent.name == "preview" and max(pimg.shape[:2]) <= 24 and armory.texture_allowed(str(pp))
          and abs(int(pimg[12, 5, 0]) - int(img[32, 10, 0])) <= 3)
    check("a preview leaves no normal map copy beside it", not pp.with_name(pp.stem + "_norm.png").exists())
    # 2026-11-25: the maps the viewport draws the live light with, the bake's own
    mp = armlit.maps(proj, [1, 3], None)
    m1 = mp.get("1") or {}
    check("each object's colour, spec and normal map, as the bake finds them",
          Path(m1.get("colour", "")).name == "plate_d.png" and Path(m1.get("spec", "")).name == "plate_s.png"
          and Path(m1.get("normal", "")).name == "plate_n.png")
    check("  an object the bake skips is left out", "3" not in mp)
    check("  and each map may be served to the page", armory.texture_allowed(m1.get("spec", "")))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "FAILURES")
sys.exit(0 if all(ok) else 1)
