"""Bake any PBR texture set into one lit colour texture, from the textures alone.

No mesh and no Blender: the surface is taken as flat, facing out of the
picture, and each texel is lit through its own maps:

* base colour (``_d``, ``_albedo``, ``_basecolor``, ``_diffuse`` ...);
* metal and roughness as separate maps (``_metallic``, ``_roughness``, or
  ``_gloss`` / ``_smoothness``), or packed: Bannerlord's ``_s`` (red metal,
  green gloss, blue AO), glTF/Unreal's ``_orm`` / ``_arm`` (red AO, green
  roughness, blue metal), glTF's ``_metallicroughness`` (green roughness, blue
  metal), Unity HDRP's ``_maskmap`` (red metal, green AO, alpha smoothness);
* a normal map (``_n``, ``_normal``, ``_nrm`` ...). Green points down the
  image (DirectX, Bannerlord's ``_n``), as :mod:`armlit` reads it; a map
  named ``_normalgl`` / ``_opengl`` is flipped on its own, and
  ``flip_green`` flips the ones whose name does not say;
* ambient occlusion (``_ao``, ``_occlusion``), opacity (``_opacity``,
  ``_alpha``) and emission (``_emissive``, ``_emission``).

Light: an even ambient light (darkened by AO, and a little where the normal
map tilts away), a reflection of that light that metal takes its colour
from, and a key light with a direction round the picture (0 = from the top),
a height above the surface, a softness and a strength. No cast shadows: with
no mesh there is nothing to cast them. :mod:`armlit` bakes on the mesh.

:func:`find_maps` names a set's maps, :func:`bake` is the arithmetic on
arrays, :func:`bake_files` reads and writes ``<name>_lit.png``.
"""
from __future__ import annotations

import base64
import io
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from . import i18n as _i18n

#: each setting's default and its range
RANGES = {
    "ambient": (0.7, 0.0, 2.0),
    "strength": (0.8, 0.0, 3.0),
    "direction": (30.0, -180.0, 180.0),     # degrees round the picture, 0 = from its top
    "height": (45.0, 5.0, 90.0),            # degrees above the surface
    "softness": (0.3, 0.0, 1.0),
    "shine": (1.0, 0.0, 2.0),
    "ao": (1.0, 0.0, 1.0),                  # how much of the AO map is used
}
GAMMA = 2.2
EXTS = (".png", ".tga", ".dds", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".texture")
PREVIEW = 512

#: each kind of map and the name endings that mark it, longest tried first
KINDS = {
    "colour": ("basecolor", "basecolour", "base_color", "base_colour", "albedo", "diffuse", "diff",
               "color", "colour", "col", "d"),
    "normal": ("normalgl", "normal_gl", "normal_opengl", "normalopengl", "nor_gl", "normaldx", "normal_dx",
               "normal_directx", "normaldirectx", "nor_dx", "normalmap", "normal_map", "normal", "norm",
               "nrm", "nor", "n"),
    "metal": ("metallic", "metalness", "metal", "met"),
    "rough": ("roughness", "rough", "rgh"),
    "gloss": ("glossiness", "smoothness", "gloss"),
    "spec": ("specular", "spec", "s"),
    "orm": ("occlusionroughnessmetallic", "occlusion_roughness_metallic", "orm", "arm"),
    "mr": ("metallicroughness", "metallic_roughness", "metalrough"),
    "mask": ("maskmap", "mask_map"),
    "ao": ("ambientocclusion", "ambient_occlusion", "occlusion", "ao"),
    "opacity": ("opacity", "transparency", "alpha"),
    "emit": ("emissive", "emission", "emit", "glow"),
}
_GL = ("gl", "opengl")
_DX = ("dx", "directx")
_TOKENS = sorted(((t, k) for k, ts in KINDS.items() for t in ts), key=lambda x: -len(x[0]))


class BakeError(ValueError):
    pass


def settings_of(raw: Optional[dict]) -> dict:
    """The settings with every number inside its range, defaults where absent."""
    raw = raw or {}
    out = {}
    for key, (default, lo, hi) in RANGES.items():
        try:
            out[key] = min(hi, max(lo, float(raw.get(key, default))))
        except (TypeError, ValueError):
            out[key] = default
    out["key"] = bool(raw.get("key", True))
    out["flip_green"] = bool(raw.get("flip_green", False))
    return out


def split_name(stem: str):
    """``(base, kind, token)`` for a file stem: ``Helmet_BaseColor`` ->
    ``("helmet", "colour", "basecolor")``; ``(stem, None, "")`` when its end
    names no kind of map. One-letter ends need a separator before them."""
    s = stem.lower()
    for token, kind in _TOKENS:
        for t in {token, token.replace("_", ""), token.replace("_", "-"), token.replace("_", " ")}:
            if not s.endswith(t) or len(s) == len(t):
                continue
            base = s[:-len(t)]
            if base[-1] in "_-. ":
                return base.rstrip("_-. "), kind, t
            if len(t) >= 4 and base[-1].isalnum():
                return base, kind, t
    return s, None, ""


def find_maps(path: str) -> Dict[str, str]:
    """Every map of the set ``path`` belongs to, ``{kind: path}``: the files
    beside it with the same name and another ending. ``path`` may be any map
    of the set; a file whose name ends in no known kind counts as the colour."""
    p = Path(path)
    base, kind, _ = split_name(p.stem)
    found: Dict[str, str] = {}
    if p.parent.is_dir():
        for q in sorted(p.parent.iterdir()):
            if q.suffix.lower() not in EXTS or not q.is_file():
                continue
            b, k, _ = split_name(q.stem)
            if b == base and k and k not in found:
                found[k] = str(q)
    if kind is None:
        found["colour"] = str(p)
    elif kind not in found:
        found[kind] = str(p)
    return found


def normal_flip(path: str, flip_green: bool) -> bool:
    """Whether the normal map's green is turned round: by its name when it
    says OpenGL or DirectX, else by ``flip_green``."""
    _, _, token = split_name(Path(path).stem)
    t = token.replace("_", "").replace("-", "").replace(" ", "")
    if t.endswith(_DX):
        return False
    if t.endswith(_GL):
        return True
    return flip_green


def read_image(path: str) -> np.ndarray:
    """A map as RGBA bytes; ``.dds`` and ``.texture`` through the toolkit's decoder."""
    p = Path(path)
    if p.suffix.lower() in (".dds", ".texture"):
        from . import icons
        data = icons._decode_to_png(p, 0)
        if data is None:
            raise BakeError(_i18n.msg("eng.pbrbake.unreadable", "{path} will not decode", path=path))
        im = Image.open(io.BytesIO(data))
    else:
        im = Image.open(p)
    return np.asarray(im.convert("RGBA")).copy()


def _fit(img: np.ndarray, h: int, w: int) -> np.ndarray:
    """A map at the colour texture's size, as 0..1 floats."""
    if img.shape[:2] != (h, w):
        img = np.asarray(Image.fromarray(img).resize((w, h), Image.BILINEAR))
    return img.astype(np.float64) / 255.0


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def light_dir(st: dict) -> np.ndarray:
    """The unit vector towards the key light: x right, y down the picture, z out of it."""
    a, h = math.radians(st["direction"]), math.radians(st["height"])
    return np.array([math.cos(h) * math.sin(a), -math.cos(h) * math.cos(a), math.sin(h)])


def bake(maps: Dict[str, np.ndarray], settings: Optional[dict] = None, flip: bool = False) -> np.ndarray:
    """The colour map (RGBA bytes, ``maps["colour"]``) with the light painted in.

    ``maps`` holds RGBA byte arrays by kind (see :data:`KINDS`), any size;
    ``flip`` turns the normal map's green round.
    """
    st = settings_of(settings)
    if maps.get("colour") is None:
        raise BakeError(_i18n.msg("eng.pbrbake.no_colour", "no colour map"))
    colour = maps["colour"]
    h, w = colour.shape[:2]
    get = {k: _fit(v, h, w) for k, v in maps.items() if v is not None}
    base = get["colour"][..., :3] ** GAMMA
    ones = np.ones((h, w))
    metal, rough, ao = np.zeros((h, w)), np.full((h, w), 0.6), ones
    if "spec" in get:
        s = get["spec"]
        metal, rough, ao = s[..., 0], 1 - s[..., 1], s[..., 2]
    if "orm" in get:
        s = get["orm"]
        ao, rough, metal = s[..., 0], s[..., 1], s[..., 2]
    if "mr" in get:
        rough, metal = get["mr"][..., 1], get["mr"][..., 2]
    if "mask" in get:
        s = get["mask"]
        metal, ao, rough = s[..., 0], s[..., 1], 1 - s[..., 3]
    if "metal" in get:
        metal = get["metal"][..., 0]
    if "gloss" in get:
        rough = 1 - get["gloss"][..., 0]
    if "rough" in get:
        rough = get["rough"][..., 0]
    if "ao" in get:
        ao = get["ao"][..., 0]
    ao = 1 - st["ao"] * (1 - ao)

    if "normal" in get:
        m = get["normal"]
        nx, ny = m[..., 0] * 2 - 1, m[..., 1] * 2 - 1
        if flip:
            ny = -ny
        nz = np.sqrt(np.maximum(1 - nx * nx - ny * ny, 0.01))
        n = _unit(np.stack([nx, ny, nz], -1))
    else:
        n = np.zeros((h, w, 3))
        n[..., 2] = 1.0

    gloss = 1 - rough
    f0 = 0.04 * (1 - metal)[..., None] + base * metal[..., None]
    diffuse = base * (1 - metal)[..., None]
    # ambient: even, a little less where the normal map tilts away (so
    # engravings and seams read), and in the AO's hollows
    amb = st["ambient"] * (0.6 + 0.4 * n[..., 2]) * ao
    # its reflection: brighter from the top of the picture, the sharper the glossier
    refl_y = 2 * n[..., 2] * n[..., 1]
    env = st["ambient"] * ao * (1 + 0.5 * gloss * np.clip(-refl_y, -1, 1))
    lit = diffuse * amb[..., None] + f0 * (env * st["shine"])[..., None]
    if st["key"] and st["strength"] > 0:
        to = light_dir(st)
        raw = n @ to
        wrap = st["softness"] * 0.5
        ndl = np.clip((raw + wrap) / (1 + wrap), 0.0, 1.0)
        hv = _unit(to + np.array([0.0, 0.0, 1.0]))
        ndh = np.clip(n @ hv, 0.0, 1.0)
        power = 2.0 ** (1 + 10 * gloss)
        spec = (power + 2) / 8 * ndh ** power * np.clip(raw, 0, 1)
        key = st["strength"] * ao
        lit += diffuse * (key * ndl)[..., None] + f0 * (key * spec * st["shine"])[..., None]
    if "emit" in get:
        lit += get["emit"][..., :3] ** GAMMA
    out = colour.copy()
    out[..., :3] = np.floor(np.clip(lit, 0.0, 1.0) ** (1 / GAMMA) * 255 + 0.5).astype(np.uint8)
    if "opacity" in get:
        out[..., 3] = np.floor(get["opacity"][..., 0] * 255 + 0.5).astype(np.uint8)
    return out


def _load(found: Dict[str, str], preview: bool) -> Dict[str, np.ndarray]:
    maps = {k: read_image(p) for k, p in found.items()}
    if preview:
        c = maps["colour"]
        f = max(c.shape[:2]) / PREVIEW
        if f > 1:
            size = (max(1, round(c.shape[1] / f)), max(1, round(c.shape[0] / f)))
            maps["colour"] = np.asarray(Image.fromarray(c).resize(size, Image.BILINEAR))
    return maps


def bake_files(paths: List[str], settings: Optional[dict] = None, out_dir: Optional[str] = None,
               preview: bool = False) -> dict:
    """Bake each texture set named by a file of it into ``<name>_lit.png``,
    beside the colour map or in ``out_dir``.

    ``{"baked": [{"source", "path", "maps"}], "skipped": [{"path", "why"}]}``;
    with ``preview`` nothing is written and each bake comes back at most
    :data:`PREVIEW` texels across, as ``"image"`` (a PNG data URL).
    """
    st = settings_of(settings)
    baked: List[dict] = []
    skipped: List[dict] = []
    seen = set()
    for path in paths or []:
        found = find_maps(path)
        key = found["colour"].lower() if "colour" in found else path.lower()
        if key in seen:
            continue
        seen.add(key)
        if "colour" not in found:
            skipped.append({"path": path, "why": "no_colour"})
            continue
        try:
            maps = _load(found, preview)
        except (OSError, ValueError) as e:
            skipped.append({"path": path, "why": str(e)})
            continue
        flip = normal_flip(found["normal"], st["flip_green"]) if "normal" in found else False
        lit = bake(maps, st, flip)
        src = Path(found["colour"])
        entry = {"source": str(src), "maps": found}
        if preview:
            buf = io.BytesIO()
            Image.fromarray(lit, "RGBA").save(buf, "PNG")
            entry["image"] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        else:
            folder = Path(out_dir) if out_dir else src.parent
            folder.mkdir(parents=True, exist_ok=True)
            base, kind, _ = split_name(src.stem)
            stem = src.stem[:len(base)] if kind else src.stem
            out = folder / f"{stem or src.stem}_lit.png"
            Image.fromarray(lit, "RGBA").save(out)
            entry["path"] = str(out)
        baked.append(entry)
    return {"baked": baked, "skipped": skipped, "settings": st}
