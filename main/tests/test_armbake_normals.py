"""Armory Studio's bake: the source normal maps and the preview of the baked images.

    python -m tests.test_armbake_normals

Nothing installed is needed: the blocks and their source images are made here.

1. ``turn_normals``: a normal map moved with its art keeps pointing the same
   way on the model - a quarter turn and a free turn turn X and Y with it
2. ``render_sheets`` in *source* mode: a block's own source normal map lands
   under it, copied texel for texel, turned with a block laid on its side; a
   block whose source has none is made from its art instead
3. the art is what it was (the bake's sheets did not change with the refactor)
4. ``preview``: each used sheet's art and normal map as PNG data URLs, from
   the same renderer, with nothing written
"""
import base64
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import armbake  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def enc(x, y):
    """A normal pointing (x, y) up the image, encoded as the maps are."""
    z = max(0.0, 1 - x * x - y * y) ** 0.5
    return [int(np.floor((c * 0.5 + 0.5) * 255 + 0.5)) for c in (x, y, z)] + [255]


print("1) a normal map turned with its art")
right = np.array([[enc(1, 0)]], np.uint8)
q = armbake.turn_normals(right, 0, True)[0, 0]
check(f"a quarter turn clockwise: pointing right becomes pointing down ({q[0]}, {q[1]})",
      abs(int(q[0]) - 128) <= 1 and q[1] <= 1)
f = armbake.turn_normals(right, 90, False)[0, 0]
check("a free turn of 90 degrees is the same quarter turn", abs(int(f[0]) - int(q[0])) <= 1 and abs(int(f[1]) - int(q[1])) <= 1)
flat = np.array([[armbake.NORMAL_FLAT]], np.uint8)
check("a flat normal stays flat whatever the turn",
      (armbake.turn_normals(flat, 37, True)[0, 0, :3].astype(int) - [128, 128, 255]).__abs__().max() <= 1)
check("no turn is no change", armbake.turn_normals(right, 0, False) is right)


class FakeSheets:
    """What ``_source_normal`` asks of the export's image cache."""

    def __init__(self, normals):
        self.normals = normals

    def normal_paths(self, pc):
        return (pc.get("n", ""), "")

    def external(self, pc):
        return True

    def image(self, path):
        return self.normals.get(path)


W = 64
yy, xx = np.mgrid[0:W, 0:W]
art = np.stack([xx * 4, yy * 4, np.full_like(xx, 90), np.full_like(xx, 255)], -1).astype(np.uint8)
nrm = np.zeros((W, W, 4), np.uint8)
nrm[:] = enc(0.6, 0.0)                          # every texel leans right


def block(n_path, rot, x, y, rect=(8, 8, 24, 40)):
    obj = {"id": 1 if n_path else 2}
    isl = armbake._Island(obj, [], ("art", art, 0, 1.0, {"n": n_path}), list(rect), 0, "main")
    b = armbake.Block([isl], ("art", art, 0, 1.0, {"n": n_path}), list(rect), "")
    b.w, b.h, b.x, b.y, b.rot, b.placed = rect[2] - rect[0], rect[3] - rect[1], x, y, rot, True
    return b


def state(blocks):
    return {"per": {"main": {"size": 128, "blocks": blocks}, "attach": {"size": 0, "blocks": []}},
            "margin_pct": 0.0, "dyes": False, "islands": [i for b in blocks for i in b.islands],
            "sheets": FakeSheets({"n.png": nrm}), "blocks": blocks}


print("2) source normal maps")
b1 = block("n.png", False, 4, 4)                # upright: 16 wide, 32 tall
b2 = block("n.png", True, 40, 4)                # on its side: 32 wide, 16 tall
b3 = block("", False, 4, 60)                    # its source has no normal map
st = state([b1, b2, b3])
out = armbake.render_sheets(st, {"mode": "source"}, None)
canvas, nmap = out["main"]
under1 = nmap[4:36, 4:20, :3].reshape(-1, 3)
check("an upright block's own normal map is copied under it, texel for texel",
      (under1 == np.array(enc(0.6, 0)[:3])).all())
under2 = nmap[4:20, 40:72, :3].reshape(-1, 3).astype(int)
want2 = np.array(enc(0, -0.6)[:3])               # leaning right, turned clockwise: leaning down
check(f"a block laid on its side has its normals turned with it ({under2[0].tolist()} for {want2.tolist()})",
      np.abs(under2 - want2).max() <= 1)
under3 = nmap[60:92, 4:20, :3].astype(int)
check("a block whose source has none is made from its art (not flat, not copied)",
      np.abs(under3[..., :2] - 128).mean() > 0.5 and not (under3.reshape(-1, 3) == np.array(enc(0.6, 0)[:3])).all())
check("where no block is, the map is flat", (nmap[120:, 120:, :3] == [128, 128, 255]).all())

print("3) the art")
check("each block's art is its source's texels, copied", (canvas[4:36, 4:20] == art[8:40, 8:24]).all())
check("a block on its side is its art turned a quarter clockwise",
      (canvas[4:20, 40:72] == np.rot90(art[8:40, 8:24], k=-1)).all())
gen = armbake.render_sheets(state([block("n.png", False, 4, 4)]), {"mode": "generic"}, None)["main"][1]
check("Generic still makes the map from the art, ignoring the source's",
      not (gen[4:36, 4:20, :3].reshape(-1, 3) == np.array(enc(0.6, 0)[:3])).all())
skip = armbake.render_sheets(state([block("n.png", False, 4, 4)]), {"mode": "skip"}, None)["main"][1]
check("Skip is flat everywhere", (skip[..., :3] == [128, 128, 255]).all())

print("4) the preview")
real_plan = armbake.plan


def fake_plan(project, mod_of, settings=None, image_of=None, scope=None, _state=None):
    _state.update(state([block("n.png", False, 4, 4), block("n.png", True, 40, 4)]))
    return {"fits": True}


armbake.plan = fake_plan
try:
    pv = armbake.preview({}, None, {"normals": {"mode": "source"}}, side=64)
finally:
    armbake.plan = real_plan


def decode(url):
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))))


check("the main sheet comes back, art and normal map, and no attachment sheet",
      set(pv["sheets"]) == {"main"} and pv["normals"] == "source" and pv["fits"])
a = decode(pv["sheets"]["main"]["art"])
n = decode(pv["sheets"]["main"]["normal"])
check(f"shrunk to the size asked ({a.shape[1]} and {n.shape[1]} wide)", a.shape[1] == 64 and n.shape[1] == 64)
full = armbake.render_sheets(state([block("n.png", False, 4, 4), block("n.png", True, 40, 4)]),
                             {"mode": "source"}, None)["main"][0]
small = np.asarray(Image.fromarray(full, "RGBA").resize((64, 64), Image.LANCZOS))
check("and it is the bake's own sheet, shrunk", np.abs(a.astype(int) - small.astype(int)).max() <= 1)


print("5) zero-alpha source normals survive filtering")
transparent = nrm.copy()
transparent[..., 3] = 0
b = block("n.png", False, 4, 4)
b.scale = 0.5
b.w, b.h = 8, 16
st = state([b])
st["sheets"].normals["n.png"] = transparent
px = armbake._block_pixels(st, b, 0, None, transparent, True)
check("scaling filters normal RGB independently from its zero alpha",
      np.abs(px[..., :3].astype(int) - np.array(enc(0.6, 0)[:3])).max() <= 1 and (px[..., 3] == 0).all())
st["sheets"].normals["n.png"] = transparent[::2, ::2]
resized = armbake._source_normal(st, b)
check("a normal at a different resolution keeps its RGB and alpha",
      resized.shape == art.shape and np.abs(resized[..., :3].astype(int) - np.array(enc(0.6, 0)[:3])).max() <= 1)
reports = []
armbake.render_sheets(st, {"mode": "source"}, None, progress=lambda pct, label: reports.append(pct))
check("render progress advances monotonically within its allotted range",
      reports == sorted(reports) and min(reports) >= 20 and max(reports) <= 70)


from unittest.mock import patch
levels = []
original_save = Image.Image.save
def capture_mip(im, *args, **kwargs):
    levels.append(np.array(im))
    return original_save(im, *args, **kwargs)
with patch.object(Image.Image, "save", capture_mip):
    armbake.dds_with_mipmaps(Image.fromarray(transparent), normal=True)
check("normal mipmaps preserve zero-alpha RGB at every level",
      len(levels) == 7 and all(np.abs(lv[..., :3].astype(int) - np.array(enc(0.6, 0)[:3])).max() <= 1 for lv in levels))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
