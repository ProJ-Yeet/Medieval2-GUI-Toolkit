"""The Keyforce Cycles bake's light, made ready for the Armory's viewport to draw live.

The bake (:mod:`keyforce`, the add-on's ``bake_prerendered_steps``) path
traces each texel looking straight down its normal, lit by:

* the world: the HDRI made small (64 x 32), averaged with its mirror image,
  at half saturation, plus an even white fill (``bake_ambient``);
* eight surround suns of the user's rig, turned by ``bake_tilt``, and a key
  sun (``bake_key``, off by default), each split between a shadowed and an
  unshadowed twin by ``bake_shadows``;

on the add-on's own material: a Principled BSDF with base colour times the
spec map's blue (AO), metallic its red, roughness one minus its green. It
bakes once with the suns alone and once with the world alone; metal takes the
brighter of the two (and a little of the other), cloth and leather the world;
a light floor keeps every texel at ``bake_floor`` of its colour at least; the
PNG is saved through the scene's colour management (AgX).

What can be measured is measured, once, in a hidden Blender (``kf_look.py``):
the worlds made small exactly as the bake makes them, the AgX curve as a 3D
table, and Cycles' light units. :func:`look` is what the page needs:

* ``env``: per world, the light the bake's material takes from it, one
  64 x 32 map per kind (diffuse, and per roughness a Fresnel-scaled and a
  constant specular part), float RGB, base64;
* ``suns``: each sun's direction towards it in the viewport's space, its
  strength and size; ``ao``: sixteen directions and how much world light each
  brings, for the world's shadow;
* ``lut``: the AgX table as a PNG data URL; ``rough``: the roughness of each
  specular level, ``albedo``: each level's integral, for the white fill.

Not modelled: light bouncing (Cycles' indirect light), its denoising, and its
sampling noise. The page draws the rest per pixel.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from . import armory, keyforce

VENDOR = keyforce.VENDOR
SCRIPT = VENDOR / "kf_look.py"
VERSION = 1
CACHE = armory.ARMORY_DIR / "cycles_look"
#: the roughness of each specular level the page interpolates between
ROUGH = tuple(i / 8 for i in range(9))
AO_DIRS = 16
#: the add-on's constants (keyforce_tools.py), held together by tests/test_cycleslook.py
SURROUND_TURNS = ((-90.1, -0.2, 184.7), (-97.0, 2.6, 266.8), (-89.9, 200.1, -4.1), (3.1, 4.0, -15.1),
                  (-98.2, 0.4, 184.6), (-178.8, 1.4, 190.2), (-81.5, 199.3, -6.9), (-98.0, -2.3, 92.7))
SURROUND_ANGLE = 4.0
WORLD_SATURATION = 0.5
METAL_OTHER_LIGHT = 0.3
GLOSSY_FROM, GLOSSY_FULL = 0.28, 0.45
METAL_OBJECT = 0.1

_LOCK = threading.Lock()
_JOB: dict = {}


def _stamp() -> str:
    """Which Blender and which kf_look.py the cache was measured with."""
    exe = keyforce.find_blender() or ""
    h = hashlib.blake2b(SCRIPT.read_bytes() + str(exe).encode("utf-8") + bytes([VERSION]), digest_size=6)
    return h.hexdigest()


def _folder() -> Path:
    return CACHE / _stamp()


def status() -> dict:
    """``{"ready": True}``, or the measuring job started (or still running),
    or why it cannot run."""
    folder = _folder()
    info = folder / "look.json"
    if info.is_file():
        data = json.loads(info.read_text(encoding="utf-8"))
        if data.get("error"):
            return {"ready": False, "error": data["error"]}
        return {"ready": True}
    with _LOCK:
        p = _JOB.get("process")
        if p is not None and p.poll() is None:
            return {"ready": False, "busy": True}
        exe = keyforce.find_blender()
        if not exe:
            return {"ready": False, "error": "no_blender"}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "job.json").write_text("{}", encoding="utf-8")
        log = open(folder / "log.txt", "w", encoding="utf-8", errors="replace")
        try:
            _JOB["process"] = subprocess.Popen(
                [str(exe), "-b", "--factory-startup", "--python", str(SCRIPT), "--", str(folder / "job.json")],
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                creationflags=keyforce.CREATE_NO_WINDOW | keyforce.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        finally:
            log.close()
    return {"ready": False, "busy": True}


# ---------------------------------------------------------------------------
# directions: the viewport's space (the game's, x mirrored) and Blender's


def blender_of(v):
    """A direction in the viewport's space as Blender's (z up). The game's
    (x, y up, z) is Blender's (x, -z, y) (kf_objects.build), and the
    viewport mirrors the game's x."""
    v = np.asarray(v, float)
    return np.stack([-v[..., 0], -v[..., 2], v[..., 1]], -1)


def viewport_of(b):
    b = np.asarray(b, float)
    return np.stack([-b[..., 0], b[..., 2], -b[..., 1]], -1)


def _euler(x, y, z):
    """Blender's XYZ Euler as a matrix (Rz @ Ry @ Rx)."""
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def suns(settings: dict) -> list:
    """Each sun: ``{"dir"`` towards it in the viewport's space, ``"energy"``,
    ``"angle"`` (degrees)}. A sun shines along its local -z."""
    tilt = math.radians(settings["bake_tilt"])
    turn = _euler(tilt * 0.5, 0.0, 0.0) @ _euler(0.0, 0.0, tilt)
    out = []
    if settings["bake_key"] > 0:
        r = _euler(math.pi / 2 - math.radians(settings["bake_elevation"]), 0.0, math.radians(settings["bake_azimuth"]))
        out.append({"dir": viewport_of(r @ [0, 0, 1]).tolist(), "energy": settings["bake_key"],
                    "angle": settings["bake_soft"]})
    if settings["bake_surround"] > 0:
        for t in SURROUND_TURNS:
            r = turn @ _euler(*[math.radians(a) for a in t])
            out.append({"dir": viewport_of(r @ [0, 0, 1]).tolist(), "energy": settings["bake_surround"],
                        "angle": SURROUND_ANGLE})
    return out


# ---------------------------------------------------------------------------
# the world as the bake lights with it


def _equirect_dirs(w: int, h: int) -> np.ndarray:
    """Blender's direction for each pixel centre, rows from the bottom
    (Cycles: u = 0.5 - atan2(y, x) / 2 pi, v = 1 - acos(z) / pi)."""
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    phi = (0.5 - u) * 2 * math.pi
    theta = (1.0 - v) * math.pi
    t, p = np.meshgrid(theta, phi, indexing="ij")
    return np.stack([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)], -1)


def _saturate(rgb: np.ndarray, s: float) -> np.ndarray:
    """Blender's Hue/Saturation node at hue 0.5, value 1: HSV saturation times ``s``."""
    mx = rgb.max(-1, keepdims=True)
    mn = rgb.min(-1, keepdims=True)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-12), 0.0)
    new = np.clip(sat * s, 0.0, 1.0)
    # each channel's distance below the max, scaled with the saturation
    scale = np.where(sat > 0, new / np.maximum(sat, 1e-12), 0.0)
    return mx - (mx - rgb) * scale


def world_light(name: str) -> np.ndarray:
    """The bake's world: the small HDRI, averaged with its mirror along x, at
    half saturation. (h, w, 3), rows from the bottom."""
    raw = np.load(_folder() / f"world_{name}.npy")[..., :3].astype(np.float64)
    # x -> -x turns atan2(y, x) into pi - atan2(y, x): u -> 0.5 - u, column i -> w/2 - 1 - i
    w = raw.shape[1]
    mirrored = raw[:, (w // 2 - 1 - np.arange(w)) % w]
    return _saturate(0.5 * (raw + mirrored), WORLD_SATURATION)


def _ggx_parts(rough: float, cos_t: np.ndarray):
    """Per unit light from a direction at angle t to the normal, the camera
    looking down the normal (as a Cycles bake does): what the specular reflects,
    split into the part scaled by F0 and the part that is not (Schlick)."""
    a = max(rough, 0.03) ** 2
    cos_t = np.clip(cos_t, 0.0, 1.0)
    cos_h = np.sqrt((1.0 + cos_t) / 2.0)                       # the half vector's angle is half t
    d = a * a / (math.pi * (cos_h * cos_h * (a * a - 1.0) + 1.0) ** 2)
    tan2 = np.where(cos_t > 0, (1.0 - cos_t * cos_t) / np.maximum(cos_t * cos_t, 1e-12), 0.0)
    g = 1.0 / (1.0 + (-1.0 + np.sqrt(1.0 + a * a * tan2)) / 2.0)   # Smith, height correlated, the view's is 0
    k = np.where(cos_t > 0, d * g / 4.0, 0.0)
    f = (1.0 - cos_h) ** 5
    return k * (1.0 - f), k * f


def _convolve(light: np.ndarray, kernel) -> np.ndarray:
    """Each direction's sum over the world of light x kernel(cos angle) x solid angle."""
    h, w = light.shape[:2]
    # finer than the world itself, so a narrow lobe still sees its neighbourhood
    up = np.stack([np.asarray(Image.fromarray(light[..., c].astype(np.float32)).resize((w * 2, h * 2), Image.BILINEAR))
                   for c in range(3)], -1).reshape(-1, 3).astype(np.float64)
    src = _equirect_dirs(w * 2, h * 2).reshape(-1, 3)
    theta = (1.0 - (np.arange(h * 2) + 0.5) / (h * 2)) * math.pi
    area = (np.sin(theta)[:, None] * np.ones(w * 2)[None, :]).reshape(-1) * (2 * math.pi / (w * 2)) * (math.pi / (h * 2))
    weighted = up * area[:, None]
    out_dirs = _equirect_dirs(w, h).reshape(-1, 3)
    out = np.zeros((len(out_dirs), 3))
    for s in range(0, len(out_dirs), 256):
        cos = out_dirs[s:s + 256] @ src.T
        out[s:s + 256] = kernel(cos) @ weighted
    return out.reshape(h, w, 3)


def env(name: str) -> dict:
    """The world's light for the bake's material, cached beside the measurement:
    level 0 diffuse (irradiance / pi), then per :data:`ROUGH` the F0 part and
    the constant part of the specular. ``{w, h, levels, data}``, float32 RGB."""
    path = _folder() / f"env_{name}.npy"
    if path.is_file():
        stack = np.load(path)
    else:
        light = world_light(name)
        levels = [_convolve(light, lambda c: np.clip(c, 0.0, None) / math.pi)]
        for r in ROUGH:
            levels.append(_convolve(light, lambda c, r=r: _ggx_parts(r, c)[0]))
            levels.append(_convolve(light, lambda c, r=r: _ggx_parts(r, c)[1]))
        stack = np.stack(levels).astype(np.float32)
        np.save(path, stack)
    n, h, w = stack.shape[:3]
    return {"w": w, "h": h, "levels": n, "data": base64.b64encode(stack.tobytes()).decode("ascii")}


def albedo() -> list:
    """Per :data:`ROUGH`: the specular's [F0 part, constant part] under an even
    white world of strength 1 (the fill light, and the diffuse's share)."""
    t = np.linspace(0.0, math.pi / 2, 4000)
    dt = t[1] - t[0]
    out = []
    for r in ROUGH:
        k1, k2 = _ggx_parts(r, np.cos(t))
        ring = 2 * math.pi * np.sin(t) * dt
        out.append([float((k1 * ring).sum()), float((k2 * ring).sum())])
    return out


def ao_dirs(name: str) -> list:
    """Sixteen directions spread over the sphere, each with the share of the
    world's light that comes from around it: ``[x, y, z, weight]`` in the
    viewport's space. The world's shadow at a texel is the weighted share of
    these its own part does not hide."""
    k = np.arange(AO_DIRS) + 0.5
    z = 1 - 2 * k / AO_DIRS
    phi = math.pi * (1 + 5 ** 0.5) * k
    dirs_b = np.stack([np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi), z], -1)
    light = world_light(name)
    h, w = light.shape[:2]
    src = _equirect_dirs(w, h).reshape(-1, 3)
    theta = (1.0 - (np.arange(h) + 0.5) / h) * math.pi
    area = (np.sin(theta)[:, None] * np.ones(w)[None, :]).reshape(-1)
    lum = (light.reshape(-1, 3) @ np.array([0.2126, 0.7152, 0.0722])) * area
    near = np.argmax(src @ dirs_b.T, 1)
    weight = np.bincount(near, lum, AO_DIRS)
    weight = weight / max(weight.sum(), 1e-12)
    return [viewport_of(d).tolist() + [float(wt)] for d, wt in zip(dirs_b, weight)]


def lut_url() -> str:
    """The AgX table as the page reads it: rows by green from the top, columns
    red + N * blue (Blender saved it bottom row first)."""
    img = Image.open(_folder() / "lut.png").convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def look(settings: Optional[dict] = None) -> dict:
    """Everything the page needs to draw the bake's light, for these Manual
    Bake settings (the add-on's recommended ones where unset)."""
    st = full_settings(settings)
    info = json.loads((_folder() / "look.json").read_text(encoding="utf-8"))
    world = "forest" if st["world"] == "PREVIEW" else st["world"].lower()
    return {"settings": st, "world": world, "units": info["units"], "view": info["view_transform"],
            "lut": lut_url(), "lut_range": info["lut"], "env": env(world), "rough": list(ROUGH),
            "albedo": albedo(), "suns": suns(st), "ao": ao_dirs(world),
            "consts": {"metal_other": METAL_OTHER_LIGHT, "glossy": [GLOSSY_FROM, GLOSSY_FULL],
                       "metal_object": METAL_OBJECT}}


def full_settings(settings: Optional[dict]) -> dict:
    """The lighting settings the bake runs with: Manual Bake's where given,
    else the add-on's defaults (keyforce.ADVANCED), angles in degrees."""
    picked = keyforce.settings_of(settings or {})
    return {key: picked.get(key, default) for key, _kind, default, *_ in keyforce.ADVANCED}


# ---------------------------------------------------------------------------
# what the metal mix needs to know of each object


def metal_info(project: dict, obj_ids, mod_of) -> dict:
    """``{id: {"metal": mean metal, "every": bool, "max_metal"}}``: each object's
    metal averaged over its faces as the bake does (metal_object_mask: the spec
    map's red at each face's centre, weighted by its UV area), whether every
    object on its texture is metal (mean at least METAL_OBJECT), and the
    texture's most metallic texel (no suns pass at all below 0.02)."""
    from . import armlit
    jobs, _skipped, sheets = armlit.gather(project, obj_ids, mod_of)
    out = {}
    for job in jobs.values():
        spec_path = armlit.sibling(job["path"], "s")
        spec = sheets.image(spec_path) if spec_path else None
        uv = np.concatenate(job["uv"]) if job["uv"] else np.zeros((0, 2))
        tris = np.array(job["tris"], int).reshape(-1, 3)
        owner = np.array(job["obj"], int)
        colour = sheets.image(job["path"])
        hh, ww = colour.shape[:2] if colour is not None else (1, 1)
        means = {}
        if spec is not None and len(tris):
            sh, sw = spec.shape[:2]
            centre = uv[tris].mean(1)
            cx = np.clip((centre[:, 0] % ww) * sw // ww, 0, sw - 1).astype(int)
            cy = np.clip((centre[:, 1] % hh) * sh // hh, 0, sh - 1).astype(int)
            metal = spec[cy, cx, 0] / 255.0
            e1, e2 = uv[tris[:, 1]] - uv[tris[:, 0]], uv[tris[:, 2]] - uv[tris[:, 0]]
            area = np.abs(e1[:, 0] * e2[:, 1] - e2[:, 0] * e1[:, 1])
            for k in np.unique(owner):
                pick = owner == k
                a = area[pick].sum()
                means[int(k)] = float((metal[pick] * area[pick]).sum() / a) if a > 0 else 0.0
        every = bool(means) and all(m >= METAL_OBJECT for m in means.values())
        top = float(spec[..., 0].max() / 255.0) if spec is not None else 0.0
        for k, oid in enumerate(job["objects"]):
            # gather numbers a texture's objects from 1
            out[str(oid)] = {"metal": means.get(k + 1, 0.0), "every": every, "max_metal": top,
                             "normal_kind": "n" if job["normal"] and Path(job["normal"]).stem.lower().endswith("_n")
                             else "m2"}
    return out
