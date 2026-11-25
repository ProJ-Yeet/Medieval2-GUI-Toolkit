"""The Cycles bake's light made ready for the viewport (unittransfer/cycleslook.py).

Run:  python -m tests.test_cycleslook

What has to hold:

* the add-on's constants copied into cycleslook.py are the add-on's own
  (vendor/keyforce/keyforce_tools.py), so the live look follows the bake;
* the viewport's space and Blender's turn into each other;
* the eight surround suns point where the add-on's Euler turns put them, and a
  key sun is only there with a strength;
* the world is averaged with its mirror (u -> 0.5 - u) and half saturated as
  Blender's Hue/Saturation node does it;
* the specular's share under an even white world falls with roughness and
  never passes 1, and the diffuse kernel gives a white world back as 1;
* each object's metal, as the bake's metal mix reads it, from its spec map.
"""
import math
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittransfer import armory, cycleslook as cl  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("1) the add-on's own numbers")
src = (cl.VENDOR / "keyforce_tools.py").read_text(encoding="utf-8")
turns = re.search(r"SURROUND_TURNS = (\(.*?\)\))\n", src, re.S)
check("the surround suns' turns", turns and eval(turns.group(1)) == cl.SURROUND_TURNS)
for name, value in (("WORLD_SATURATION", cl.WORLD_SATURATION), ("METAL_OTHER_LIGHT", cl.METAL_OTHER_LIGHT),
                    ("METAL_OBJECT", cl.METAL_OBJECT)):
    m = re.search(rf"^{name} = ([0-9.]+)", src, re.M)
    check(f"  {name}", m and float(m.group(1)) == value)
m = re.search(r"^GLOSSY_FROM, GLOSSY_FULL = ([0-9.]+), ([0-9.]+)", src, re.M)
check("  GLOSSY_FROM, GLOSSY_FULL", m and (float(m.group(1)), float(m.group(2))) == (cl.GLOSSY_FROM, cl.GLOSSY_FULL))
m = re.search(r"^SURROUND_ANGLE = math.radians\(([0-9.]+)\)", src, re.M)
check("  SURROUND_ANGLE", m and float(m.group(1)) == cl.SURROUND_ANGLE)

print("\n2) directions")
v = np.array([[0.3, 0.5, -0.8], [1, 0, 0], [0, 1, 0]])
check("viewport -> Blender -> viewport", np.allclose(cl.viewport_of(cl.blender_of(v)), v))
check("up in the viewport is Blender's +z", np.allclose(cl.blender_of([0, 1, 0]), [0, 0, 1]))
st = cl.full_settings({})
suns = cl.suns(st)
check(f"the recommended rig: eight surround suns, no key ({len(suns)})",
      len(suns) == 8 and all(abs(s["energy"] - st["bake_surround"]) < 1e-9 for s in suns))
check("  each a unit vector", all(abs(np.linalg.norm(s["dir"]) - 1) < 1e-9 for s in suns))
check("  one from straight above, one from straight below",
      max(s["dir"][1] for s in suns) > 0.95 and min(s["dir"][1] for s in suns) < -0.95)
key = cl.suns(dict(st, bake_key=2.0, bake_elevation=90.0))
check("a key sun with a strength, from above at elevation 90",
      len(key) == 9 and key[0]["energy"] == 2.0 and key[0]["dir"][1] > 0.999)

print("\n3) the world as the bake lights with it")
rgb = np.array([[[1.0, 0.5, 0.25]]])
sat = cl._saturate(rgb, 0.5)
check(f"half saturation keeps the brightest channel and halves the spread ({sat.ravel().round(3).tolist()})",
      np.allclose(sat, [[[1.0, 0.75, 0.625]]]))
check("  grey stays grey", np.allclose(cl._saturate(np.full((1, 1, 3), 0.4), 0.5), 0.4))
w, h = 64, 32
dirs = cl._equirect_dirs(w, h)
col = (w // 2 - 1 - np.arange(w)) % w
check("the column the mirror picks is the direction with x turned round",
      np.allclose(dirs[:, col] * [-1, 1, 1], dirs))
white = np.ones((h, w, 3))
diff = cl._convolve(white, lambda c: np.clip(c, 0, None) / math.pi)
check(f"a white world lights a white surface to 1 ({diff.mean():.3f})", abs(diff.mean() - 1) < 0.02)
alb = cl.albedo()
check("the specular's share falls with roughness and never passes 1",
      all(a[0] <= 1.001 for a in alb) and alb[-1][0] < alb[2][0])

print("\n4) each object's metal")
with tempfile.TemporaryDirectory() as tmp:
    from PIL import Image
    t = Path(tmp)
    armory.ARMORY_DIR = t / "armory"
    armory.SHEETS_DIR = armory.ARMORY_DIR / "sheets"
    colour = np.full((64, 64, 4), 128, np.uint8)
    spec = np.zeros((64, 64, 4), np.uint8)
    spec[:, :32, 0] = 255                       # the left half metal
    Image.fromarray(colour, "RGBA").save(t / "kit_d.png")
    Image.fromarray(spec, "RGBA").save(t / "kit_s.png")
    (t / "kit.obj").write_text("""
v 0 0 0
v 1 0 0
v 1 0 1
v 0 0 1
vt 0 0
vt 0.4 0
vt 0.4 1
vt 0 1
vt 0.6 0
vt 1 0
vt 1 1
vt 0.6 1
vn 0 1 0
o plate
f 1/1/1 2/2/1 3/3/1 4/4/1
o cloth
f 1/5/1 2/6/1 3/7/1 4/8/1
""", encoding="utf-8")
    asset = {"kind": "external", "path": str(t / "kit.obj"),
             "textures": {"0": str(t / "kit_d.png"), "1": str(t / "kit_d.png")}}
    key = armory.asset_key(asset)
    proj = {"assets": [asset], "objects": [{"id": i + 1, "name": n, "mesh": n, "src": [{"asset": key, "group": i}]}
                                           for i, n in enumerate(("plate", "cloth"))]}
    info = cl.metal_info(proj, [1, 2], None)
    check(f"the plate on the metal half is metal, the cloth not ({info.get('1', {}).get('metal')}, "
          f"{info.get('2', {}).get('metal')})",
          info.get("1", {}).get("metal", 0) > 0.9 and info.get("2", {}).get("metal", 1) < 0.1)
    check("  so not every object on the texture is metal", info.get("1", {}).get("every") is False)
    check("  and the texture's most metallic texel is full metal", info.get("1", {}).get("max_metal") == 1.0)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "FAILURES")
sys.exit(0 if all(ok) else 1)
