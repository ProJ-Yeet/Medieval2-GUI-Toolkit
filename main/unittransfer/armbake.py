"""Armory Studio's export: the check, the UV packing and the bake (Phase 95i).

The model being edited is objects taken out of other models, each still
pointing at its source's sheets. Exporting it makes it a model of its own:

* :func:`check_model` runs the Blender kit's export checks that still apply
  (names, opt, weights, the ranged objects, the size of the vertex pool). Its
  UV and texture checks are left out, since the sheets are baked new here.
* :func:`uv_plan` cuts every object's UVs into **islands** (triangles joined
  by a shared vertex), measures each in its source's own texels, folds the
  islands whose art overlaps in the same source into one **block**, so the
  same art never takes room twice, and packs the blocks onto the main and the
  attachment sheet. A block moves and turns by quarter turns, never scales
  unless the user asks, and keeps a margin round it as a share of the sheet.
  From 99l a block is its **shape**, not its rectangle: the texels under its
  UV triangles grown by the margin, a mask. Islands fold only where their
  texels truly overlap, and blocks are packed by their masks, so one slides
  into another's empty corner; only the masked texels are copied.
  From 99p a block goes wherever its mask meets nothing yet on the sheet, a
  hole under another block or a pocket at its side included, every place
  weighed at once on a coarse grid and then slid tight at the exact texels;
  and with ``rotate: "free"`` a block may also take the turn that boxes it
  smallest, which resamples it.
  When a sheet runs out of room it says which blocks did not fit and what each
  would take, and ``auto`` picks a way out (said to cost quality).
* :func:`bake` copies each block's source texels onto its sheet, the margin
  bleeding the art past the island's edge, dyed and stamped as the page
  previews it, and writes the ``.mesh`` with the new UVs beside the sheets.

The dye arithmetic is ``armDyePixels`` in ``web/js/armobj.js`` in numpy, the
same numbers, so what was previewed is what is baked. Nothing is resampled
except a block the user scaled or one given a free turn.
"""
from __future__ import annotations

import io
import math
import re
import struct
from array import array
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from . import armory, mesh
from . import i18n as _i18n

#: the sheet sizes offered, smallest first
SIZES = (512, 1024, 2048, 4096)
#: the default margin round each block, a share of the sheet in per cent
MARGIN_PCT = 0.4
#: the margin a scaled block should keep, in pixels of the sheet
SCALED_MARGIN_PX = 4
#: room left for the packing's own waste when a size is recommended
PACK_SLACK = 1.15
SHEETS = ("main", "attach")
#: what an object with no sheet at all is baked as (the viewer's own grey)
NO_ART = (184, 168, 143, 255)

#: A ranged unit's skeletons, by name: ``MTW2_HR_Bow``, ``MTW2_Fast_Bowman``,
#: ``MTW2_Crossbow``, ``MTW2_Javelin``, the gunners'.
_RANGED_SKELETON = re.compile(r"archer|bow|javelin|sling|gun|musket|throw|arquebus|pistol", re.I)


class BakeError(armory.ArmoryError):
    """The export cannot go on, said as a sentence."""


# ---------------------------------------------------------------------------
# names, as the page fixes them (armFixName)


def fix_name(full: str) -> str:
    """The kit's *Fix names*: ``name`` becomes ``name__name``, ``a_b``
    becomes ``a__b``, ``hair1``/``hair_1``/``hair__1`` become
    ``hair__hair_1``, and a trailing ``.001`` goes."""
    s = re.sub(r"\.\d{3}$", "", full)
    s = re.sub(r"__opt$", "", s, flags=re.I)
    m = re.match(r"^([A-Za-z]+)_{0,2}(\d+)$", s)
    if m:
        return f"{m.group(1)}__{m.group(1)}_{m.group(2)}"
    if "__" not in s:
        if "_" in s:
            i = s.index("_")
            return f"{s[:i]}__{s[i + 1:]}"
        return f"{s}__{s}"
    return s


def full_name(obj: dict) -> str:
    return f"{obj.get('name') or ''}__{obj.get('mesh') or ''}"


# ---------------------------------------------------------------------------
# which objects go


def in_scope(project: dict, scope: Optional[dict]) -> List[dict]:
    """The objects an export takes: every visible one, or the ones in the
    chosen collections (by default those ticked *export*)."""
    scope = scope or {}
    objs = project.get("objects") or []
    colls = {c.get("id"): c for c in project.get("collections") or []}
    if scope.get("mode") == "collections":
        chosen = scope.get("collections")
        if chosen is None:
            chosen = [cid for cid, c in colls.items() if c.get("export")]
        chosen = set(chosen)
        return [o for o in objs if o.get("coll") in chosen]
    out = []
    for o in objs:
        if o.get("hidden"):
            continue
        c = colls.get(o.get("coll"))
        if c is not None and c.get("hidden"):
            continue
        out.append(o)
    return out


# ---------------------------------------------------------------------------
# the check


def _entry_skeletons(asset: dict, mod_of) -> List[str]:
    if asset.get("kind") != "entry" or mod_of is None:
        return []
    try:
        entry = mod_of(asset.get("mod") or "").modeldb.by_name().get((asset.get("entry") or "").lower())
    except Exception:          # a mod since removed
        return []
    return [str(s) for s in entry.skeletons()] if entry is not None else []


def _issue(level: str, code: str, obj: Optional[dict] = None, **params) -> dict:
    out = {"level": level, "code": code, "params": params}
    if obj is not None:
        out["id"] = obj.get("id")
        out["params"].setdefault("name", full_name(obj))
    return out


def check_model(project: dict, mod_of, scope: Optional[dict] = None,
                skeleton: str = "") -> dict:
    """The kit's export checks on the objects in scope.

    Each issue is ``{level, code, params, id?}``; the page words it from the
    code (``armory.chk_<code>``). ``fixable`` says whether the rename fix
    would change anything.
    """
    objs = in_scope(project, scope)
    assets = armory.project_assets(project)
    issues: List[dict] = []
    if not objs:
        issues.append(_issue("error", "nothing"))
        return {"objects": [], "issues": issues, "fixable": False, "vertices": 0}
    seen: Dict[Tuple[str, str, int], dict] = {}
    fixable = False
    verts = 0
    types: set = set()
    for o in objs:
        name, part = (o.get("name") or "").strip(), (o.get("mesh") or "").strip()
        if not name or not part:
            issues.append(_issue("error", "empty_name", o))
            continue
        full = full_name(o)
        fixed = fix_name(full)
        if fixed != full:
            fixable = True
            issues.append(_issue("warning", "name_form", o, fixed=fixed))
        if re.search(r"_opt$", part, re.I):
            issues.append(_issue("warning", "opt_in_name", o))
        key = (fixed.lower(), int(o.get("flag") or 0))
        if key in seen:
            issues.append(_issue("error", "name_clash", o, other=full_name(seen[key])))
        else:
            seen[key] = o
        types.add(name.lower())
        try:
            om = armory.object_mesh(o, assets, mod_of)
        except (armory.ArmoryError, mesh.MeshError, KeyError) as e:
            issues.append(_issue("error", "unreadable", o, why=str(e)))
            continue
        verts += om.vertices
        if om.triangles and not armory.has_weights(om):
            issues.append(_issue("error", "no_weights", o))
        for pc in o.get("src") or []:
            a = assets.get(pc.get("asset"))
            if a is not None and a.get("kind") == "external" and not _external_texture(a, pc.get("group", 0)):
                issues.append(_issue("warning", "no_texture", o))
                break
    if verts > 0xFFFF + 1:
        issues.append(_issue("error", "too_many_vertices", count=verts))
    if not skeleton:
        # the skeletons the entries the parts came out of name
        names = []
        for key in {pc.get("asset") for o in objs for pc in o.get("src") or []}:
            names += _entry_skeletons(assets.get(key) or {}, mod_of)
        skeleton = " ".join(names)
    ranged = bool(_RANGED_SKELETON.search(skeleton))
    if ranged:
        if not any(t.startswith("primaryactive0") for t in types):
            issues.append(_issue("warning", "ranged_no_primary"))
        if not any(t.startswith("secondaryactive0") for t in types):
            issues.append(_issue("warning", "ranged_no_secondary"))
    return {"objects": [o.get("id") for o in objs], "issues": issues,
            "fixable": fixable, "vertices": verts, "ranged": ranged}


# ---------------------------------------------------------------------------
# the source sheets


ImageOf = Callable[[str], Image.Image]
_IMAGES: Dict[str, tuple] = {}


def default_image_of(path: str) -> Image.Image:
    """An image file read whole, kept while it is unchanged."""
    p = Path(path)
    st = p.stat()
    hit = _IMAGES.get(path)
    if hit and hit[0] == (st.st_size, st.st_mtime_ns):
        return hit[1]
    from . import icons
    data = icons._decode_to_png(p, 0)
    if data is None:
        raise BakeError(_i18n.msg("eng.armbake.sheet_unreadable", "{path} will not decode", path=path))
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    _IMAGES[path] = ((st.st_size, st.st_mtime_ns), img)
    return img


def _external_texture(asset: dict, group: int) -> str:
    over = (asset.get("textures") or {}).get(str(group)) or (asset.get("textures") or {}).get(group)
    if over:
        return over
    try:
        return armory.read_external(asset.get("path") or "")[2].get(int(group)) or ""
    except armory.ArmoryError:
        return ""


def _entry_sheets(asset: dict, mod_of) -> Tuple[str, str]:
    """An entry's chosen skin as the paths of its main and attachment sheets."""
    from . import factions
    mod = mod_of(asset.get("mod") or "")
    entry = mod.modeldb.by_name().get((asset.get("entry") or "").lower())
    if entry is None:
        return "", ""
    skins = mesh.entry_view(entry, mod.data, mod)["skins"]
    if not skins:
        return "", ""
    skin = skins[min(int(asset.get("skin") or 0), len(skins) - 1)]
    main = factions.read_path(mod, skin.get("rel") or "") if skin.get("exists") else None
    att = None
    if skin.get("attach") and skin.get("attach_exists"):
        att = factions.read_path(mod, skin["attach"])
    # 100l: a sheet edited or swapped in the Textures tab stands in for the mod's
    over = asset.get("over") or {}
    return (over.get("main") or (str(main) if main else "")), (over.get("attach") or (str(att) if att else ""))


class _Sheets:
    """Each piece's source images, read once per export."""

    def __init__(self, assets: Dict[str, dict], mod_of, image_of: ImageOf):
        self.assets, self.mod_of, self.image_of = assets, mod_of, image_of
        self._paths: Dict[Tuple[str, int], Tuple[str, str]] = {}
        self._img: Dict[str, Optional[np.ndarray]] = {}

    def paths(self, pc: dict) -> Tuple[str, str]:
        """``(main, attachment)`` for a piece; an external piece has one."""
        key = (pc.get("asset"), int(pc.get("group") or 0), pc.get("sheet") or "")
        if key not in self._paths:
            a = self.assets.get(key[0]) or {}
            if key[2]:
                # 100l: the object wears a sheet of its own, the one image
                # standing for both halves of the game's layout
                self._paths[key] = (key[2], "" if self.external(pc) else key[2])
            elif a.get("kind") == "external":
                p = _external_texture(a, key[1])
                self._paths[key] = (p, "")
            else:
                try:
                    self._paths[key] = _entry_sheets(a, self.mod_of)
                except Exception:          # a mod since removed: baked as no art
                    self._paths[key] = ("", "")
        return self._paths[key]

    def external(self, pc: dict) -> bool:
        """A file whose UVs address its one image; a loose ``.mesh`` speaks
        the game's main|attachment layout, as an entry does."""
        a = self.assets.get(pc.get("asset")) or {}
        return a.get("kind") == "external" and not (a.get("path") or "").lower().endswith(".mesh")

    def image(self, path: str) -> Optional[np.ndarray]:
        if not path:
            return None
        if path not in self._img:
            try:
                self._img[path] = np.asarray(self.image_of(path).convert("RGBA")).copy()
            except (OSError, ValueError, armory.ArmoryError):
                self._img[path] = None
        return self._img[path]


def _glue(main: np.ndarray, att: Optional[np.ndarray]) -> np.ndarray:
    """The main and attachment sheets side by side, as the game lays them out,
    the attachment brought to the main one's size."""
    if att is None:
        att = main
    elif att.shape[:2] != main.shape[:2]:
        att = np.asarray(Image.fromarray(att).resize((main.shape[1], main.shape[0]), Image.LANCZOS))
    return np.concatenate([main, att], axis=1)


# ---------------------------------------------------------------------------
# dyes and stamps, as armDyePixels and armStampPixels do them


def _blend(mode: str, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    if mode == "multiply":
        return b * c
    if mode == "screen":
        return 1 - (1 - b) * (1 - c)
    if mode == "overlay":
        return np.where(b < 0.5, 2 * b * c, 1 - 2 * (1 - b) * (1 - c))
    if mode == "hardlight":
        return np.where(c < 0.5, 2 * b * c, 1 - 2 * (1 - b) * (1 - c))
    if mode == "softlight":
        return (1 - 2 * c) * b * b + 2 * c * b
    return np.broadcast_to(c, b.shape).copy()


def channels(rgb: np.ndarray) -> np.ndarray:
    """``armChannel`` per pixel: 0 white, 1 metal, 2 trim, 3 leather, 4 cloth."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    chroma = mx - mn
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    safe = np.where(chroma > 0, chroma, 1.0)
    h = np.where(mx == r, np.fmod((g - b) / safe, 6.0),
                 np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4))
    h = np.fmod(h * 60 + 360, 360)
    sat = chroma / np.where(mx > 0, mx, 1.0)
    out = np.full(r.shape, 4, dtype=np.uint8)
    leather = (h >= 10) & (h <= 45) & (sat > 0.25) & (lum < 0.55)
    trim = (h >= 38) & (h <= 62) & (sat > 0.45) & (lum > 0.42)
    out[leather] = 3
    out[trim] = 2
    out[chroma < 0.09] = 1
    out[(lum > 0.90) & (chroma < 0.10)] = 0
    return out


_CHANNEL_NAMES = ("white", "metal", "trim", "leather", "cloth")


def dye_pixels(arr: np.ndarray, d: dict, material: str = "") -> np.ndarray:
    """An RGBA image dyed in place of a copy, exactly as the preview dyes it."""
    out = arr.copy()
    src = arr[..., :3].astype(np.float64) / 255.0
    main = np.array(d.get("color") or [128, 128, 128], dtype=np.float64) / 255.0
    strength = 1.0 if d.get("strength") is None else float(d.get("strength"))
    blend = d.get("blend") or "keepshade"
    main_on = ({"cloth"} if material == "fabric" else {"leather"} if material == "leather"
               else {"cloth", "leather", "trim"})
    chans = d.get("channels") or {}
    ch = channels(src)
    h, w = ch.shape
    target = np.zeros((h, w, 3))
    active = np.zeros((h, w), bool)
    is_layer = np.zeros((h, w), bool)
    pattern = d.get("pattern") or {}
    layer_cols = pattern.get("colors") or {}
    if layer_cols and pattern.get("centers"):
        centers = np.array(pattern["centers"], dtype=np.float64)
        px = arr[..., :3].astype(np.float64)
        dist = ((px[:, :, None, :] - centers[None, None, :, :]) ** 2).sum(-1)
        best = dist.argmin(-1)
        for k, col in layer_cols.items():
            m = best == int(k)
            target[m] = np.array(col, dtype=np.float64) / 255.0
            is_layer |= m
        active |= is_layer
    rest = ~is_layer
    keep_white = d.get("keepWhite") is not False
    for i, name in enumerate(_CHANNEL_NAMES):
        m = rest & (ch == i)
        if name == "white" and keep_white:
            continue
        if name == "metal" and (chans.get("metal") or {}).get("on"):
            target[m] = np.array(chans["metal"].get("color") or d.get("color"), dtype=np.float64) / 255.0
        elif name in ("metal", "white"):
            # grey is mail and plate: a metal preset, the metal channel or an
            # object marked metal reaches it, and nothing else does
            if not d.get("metal") and not (name == "metal" and material == "metal"):
                continue
            target[m] = main
        elif (chans.get(name) or {}).get("on"):
            target[m] = np.array(chans[name].get("color") or d.get("color"), dtype=np.float64) / 255.0
        elif name in main_on:
            target[m] = main
        else:
            continue
        active |= m
    lum = 0.299 * src[..., 0] + 0.587 * src[..., 1] + 0.114 * src[..., 2]
    work = src.copy()
    desat = float(d.get("desat") or 0)
    if desat:
        work += (lum[..., None] - work) * desat
    tl = np.maximum(0.04, 0.299 * target[..., 0] + 0.587 * target[..., 1] + 0.114 * target[..., 2])
    shade = target * (lum / tl)[..., None]
    mixed = shade if blend == "keepshade" else _blend(blend, work, target)
    o = np.where(is_layer[..., None], shade, mixed)
    s = np.where(is_layer, 1.0, strength)[..., None]
    res = np.clip(np.floor((src + (o - src) * s) * 255 + 0.5), 0, 255)
    sel = active & (s[..., 0] != 0)
    out[..., :3][sel] = res[sel].astype(np.uint8)
    return out


def stamp_pixels(arr: np.ndarray, stamp_img: Image.Image, st: dict,
                 box: Tuple[float, float, float, float]) -> np.ndarray:
    """A coat of arms or emblem stamped onto an RGBA image.

    ``box`` is the part's art on this image in pixels, ``(x0, y0, x1, y1)``;
    the stamp's ``x``/``y`` are its centre as a share of that box, ``size`` its
    width as a share of the box's width, ``rot`` degrees clockwise, ``blend``
    one of the dye's modes or ``normal``, ``opacity`` 0..1.
    """
    x0, y0, x1, y1 = box
    bw = max(1.0, x1 - x0)
    sw = max(1, int(round(bw * float(st.get("size") or 0.3))))
    sh = max(1, int(round(sw * stamp_img.height / max(1, stamp_img.width))))
    layer = stamp_img.convert("RGBA").resize((sw, sh), Image.BICUBIC)
    rot = float(st.get("rot") or 0)
    if rot:
        layer = layer.rotate(-rot, resample=Image.BICUBIC, expand=True)
    cx = x0 + bw * float(st.get("x", 0.5))
    cy = y0 + max(1.0, y1 - y0) * float(st.get("y", 0.5))
    lx, ly = int(round(cx - layer.width / 2)), int(round(cy - layer.height / 2))
    H, W = arr.shape[:2]
    ax, ay = max(0, lx), max(0, ly)
    bx, by = min(W, lx + layer.width), min(H, ly + layer.height)
    out = arr.copy()
    if bx <= ax or by <= ay:
        return out
    lay = np.asarray(layer).astype(np.float64)[ay - ly:by - ly, ax - lx:bx - lx] / 255.0
    base = out[ay:by, ax:bx, :3].astype(np.float64) / 255.0
    c = lay[..., :3]
    a = lay[..., 3:4] * float(1.0 if st.get("opacity") is None else st.get("opacity"))
    mode = st.get("blend") or "normal"
    if mode == "keepshade":
        lum = (0.299 * base[..., 0] + 0.587 * base[..., 1] + 0.114 * base[..., 2])[..., None]
        tl = np.maximum(0.04, 0.299 * c[..., 0:1] + 0.587 * c[..., 1:2] + 0.114 * c[..., 2:3])
        o = c * (lum / tl)
    elif mode == "normal":
        o = c
    else:
        o = _blend(mode, base, c)
    res = np.clip(np.floor((base + (o - base) * a) * 255 + 0.5), 0, 255).astype(np.uint8)
    out[ay:by, ax:bx, :3] = res
    return out


# ---------------------------------------------------------------------------
# islands and blocks


def _object_parts(obj: dict, assets, mod_of):
    """The object's mesh, and for each piece its first vertex, its count and
    the piece itself, in the order :func:`armory.object_mesh` lays them out."""
    om = armory.object_mesh(obj, assets, mod_of)
    parts, start = [], 0
    for pc in obj.get("src") or []:
        a = assets.get(pc.get("asset"))
        if a is None:
            continue
        m = armory.asset_mesh(a, mod_of)
        n = len(set(armory.piece_indices(m, pc)))
        parts.append((start, n, pc))
        start += n
    return om, parts


def _islands(indices: Sequence[int], lo: int, hi: int) -> List[List[int]]:
    """Triangles (by number) joined through a shared vertex, for the
    triangles whose vertices fall in ``lo..hi``."""
    parent: Dict[int, int] = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tris = []
    for t in range(len(indices) // 3):
        a, b, c = indices[t * 3], indices[t * 3 + 1], indices[t * 3 + 2]
        if not (lo <= a < hi):
            continue
        tris.append(t)
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    groups: Dict[int, List[int]] = {}
    for t in tris:
        groups.setdefault(find(indices[t * 3]), []).append(t)
    return list(groups.values())


class _Island:
    __slots__ = ("obj", "verts", "src", "rect", "tile", "origin", "polys", "_mask")

    def __init__(self, obj, verts, src, rect, tile, origin, polys=()):
        self.obj, self.verts, self.src, self.rect, self.tile, self.origin = obj, verts, src, rect, tile, origin
        #: its triangles, each three points in its source's texels (99l)
        self.polys = list(polys)
        self._mask = None

    def mask(self) -> np.ndarray:
        """Its texels at scale 1 over its own rect, without a margin."""
        if self._mask is None:
            self._mask = raster(self.polys, self.rect, 1.0, 0,
                                self.rect[2] - self.rect[0], self.rect[3] - self.rect[1])
        return self._mask


def _source_of(sheets: _Sheets, pc: dict, umin: float, umax: float):
    """Which image an island's art is on, and how its UVs reach it:
    ``(id, image or None, base u, u span, tile)``."""
    eps = mesh.TILE_EPS
    base = math.floor(umin + eps)
    main, att = sheets.paths(pc)
    if sheets.external(pc):
        return (main, sheets.image(main), base, 1.0, 0)
    tile = base % 2
    if umax - base <= 1 + eps:
        path = att if (tile == 1 and att) else main
        img = sheets.image(path)
        return (path + "|" + str(tile), img, base, 1.0, tile)
    m = sheets.image(main)
    a = sheets.image(att) if att else None
    glued = _glue(m, a) if m is not None else None
    even = base - (base % 2)
    return (main + "|" + att + "|glued", glued, even, 2.0, 0)


def gather(project: dict, objs: List[dict], mod_of, sheets: _Sheets):
    """Every island of every object, measured in its source's texels."""
    assets = armory.project_assets(project)
    meshes: Dict[int, mesh.MeshFile] = {}
    islands: List[_Island] = []
    for o in objs:
        om, parts = _object_parts(o, assets, mod_of)
        meshes[o.get("id")] = om
        uvs = om.uvs
        ix = om.groups[0].indices if om.groups else array("H")
        for start, n, pc in parts:
            if o.get("sheet"):
                pc = dict(pc, sheet=o["sheet"])
            for tris in _islands(ix, start, start + n):
                verts = sorted({ix[t * 3 + k] for t in tris for k in range(3)})
                us = [uvs[v * 2] for v in verts]
                vs = [uvs[v * 2 + 1] for v in verts]
                sid, img, base, span, tile = _source_of(sheets, pc, min(us), max(us))
                W, H = (img.shape[1], img.shape[0]) if img is not None else (64, 64)
                xs = [(u - base) * W / span for u in us]
                ys = [v * H for v in vs]
                rect = [math.floor(min(xs)), math.floor(min(ys)),
                        max(math.ceil(max(xs)), math.floor(min(xs)) + 1),
                        max(math.ceil(max(ys)), math.floor(min(ys)) + 1)]
                origin = "main" if sheets.external(pc) else ("attach" if tile == 1 else "main")
                if not sheets.external(pc) and span == 2.0:
                    origin = "both"
                at = {v: ((uvs[v * 2] - base) * W / span, uvs[v * 2 + 1] * H) for v in verts}
                polys = [(at[ix[t * 3]], at[ix[t * 3 + 1]], at[ix[t * 3 + 2]]) for t in tris]
                islands.append(_Island(o, verts, (sid, img, base, span, pc), rect, tile, origin, polys))
    return meshes, islands


def _dye_key(o: dict, dyes: bool) -> str:
    if not dyes:
        return ""
    import json
    return json.dumps([o.get("dye"), o.get("material"), o.get("stamps")], sort_keys=True)


# ---------------------------------------------------------------------------
# shapes (99l): the texels under the UV triangles, as masks


def raster(polys, rect, scale: float, margin: int, w: int, h: int) -> np.ndarray:
    """``polys`` (triangles in source texels) drawn into a ``h + 2 margin``
    by ``w + 2 margin`` mask whose art corner is ``rect``'s, at ``scale``,
    then grown by the margin. No triangles is the whole rectangle."""
    if not polys:
        return np.ones((h + 2 * margin, w + 2 * margin), bool)
    ox, oy = rect[0], rect[1]
    return _draw([[((x - ox) * scale, (y - oy) * scale) for x, y in tri] for tri in polys], margin, w, h)


def _draw(polys, margin: int, w: int, h: int) -> np.ndarray:
    """``polys`` (triangles from the art corner, in texels of the sheet)
    drawn into a ``h + 2 margin`` by ``w + 2 margin`` mask, then grown by the
    margin. A texel a triangle touches at all is in it: the edge is drawn as
    well as the inside, so the texel a vertex sits on is kept, and the margin
    (at least one texel) keeps the one bilinear filtering reads beside it."""
    from PIL import ImageDraw
    W, H = w + 2 * margin, h + 2 * margin
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    for tri in polys:
        dr.polygon([(x + margin, y + margin) for x, y in tri], fill=1, outline=1)
    m = np.asarray(im, bool).copy()
    return grow(m, margin) if margin else m


def grow(m: np.ndarray, r: int) -> np.ndarray:
    """A square dilation by ``r`` texels, rows then columns."""
    if r <= 0 or not m.any():
        return m
    out = m.copy()
    for _ in range(r):
        prev = out.copy()
        out[:, 1:] |= prev[:, :-1]
        out[:, :-1] |= prev[:, 1:]
    for _ in range(r):
        prev = out.copy()
        out[1:, :] |= prev[:-1, :]
        out[:-1, :] |= prev[1:, :]
    return out


def _masks_meet(a: "_Island", b: "_Island") -> bool:
    """Whether two islands of one source use a texel in common."""
    ra, rb = a.rect, b.rect
    x0, y0, x1, y1 = max(ra[0], rb[0]), max(ra[1], rb[1]), min(ra[2], rb[2]), min(ra[3], rb[3])
    if x0 >= x1 or y0 >= y1:
        return False
    ma = a.mask()[y0 - ra[1]:y1 - ra[1], x0 - ra[0]:x1 - ra[0]]
    mb = b.mask()[y0 - rb[1]:y1 - rb[1], x0 - rb[0]:x1 - rb[0]]
    return bool((ma & mb).any())


class Block:
    """Islands whose art overlaps in one source, packed and baked as one."""
    __slots__ = ("id", "islands", "src", "rect", "objs", "sheet", "scale", "w", "h",
                 "x", "y", "rot", "angle", "placed", "dkey", "_shape", "_free")

    def __init__(self, islands, src, rect, dkey):
        self.islands, self.src, self.rect, self.dkey = islands, src, rect, dkey
        self.objs = sorted({i.obj.get("id") for i in islands})
        self.id = f"{src[0]}@{rect[0]},{rect[1]},{rect[2]},{rect[3]}#{','.join(map(str, self.objs))}"
        self.sheet, self.scale = "main", 1.0
        self.w = self.h = self.x = self.y = 0
        self.rot = False
        #: a free turn in degrees (99p), before the quarter turn; 0 is none
        self.angle = 0.0
        self.placed = False
        self._shape = {}
        self._free = None

    def _polys(self):
        """Its triangles from its art corner, at its scale; a block with none
        is its rectangle."""
        k, ox, oy = self.scale, self.rect[0], self.rect[1]
        polys = [t for i in self.islands for t in i.polys]
        if not polys:
            w, h = self.src_w, self.src_h
            polys = [((ox, oy), (ox + w, oy), (ox + w, oy + h)), ((ox, oy), (ox + w, oy + h), (ox, oy + h))]
        return [[((x - ox) * k, (y - oy) * k) for x, y in tri] for tri in polys]

    def frame(self) -> Tuple[int, int, float, float]:
        """``(w, h, ox, oy)``: its size at its scale and free turn, and where
        the turned art's corner falls."""
        if not self.angle:
            return (max(1, int(math.ceil(self.src_w * self.scale))),
                    max(1, int(math.ceil(self.src_h * self.scale))), 0.0, 0.0)
        pts = [_spin(p, self.angle) for tri in self._polys() for p in tri]
        ox, oy = min(p[0] for p in pts), min(p[1] for p in pts)
        return (max(1, int(math.ceil(max(p[0] for p in pts) - ox))),
                max(1, int(math.ceil(max(p[1] for p in pts) - oy))), ox, oy)

    def local(self, sx: float, sy: float) -> Tuple[float, float]:
        """A point in its source's texels, on the block before its quarter turn."""
        lx, ly = (sx - self.rect[0]) * self.scale, (sy - self.rect[1]) * self.scale
        if self.angle:
            _w, _h, ox, oy = self.frame()
            lx, ly = _spin((lx, ly), self.angle)
            lx, ly = lx - ox, ly - oy
        return lx, ly

    def free_angle(self) -> float:
        """The turn that leaves its art in the smallest rectangle (99p), or 0
        when that is near a quarter turn or saves little."""
        if self._free is None:
            self._free = _least_box_angle([p for tri in self._polys() for p in tri])
        return self._free

    def shape(self, margin: int) -> np.ndarray:
        """Its mask on the sheet, the margin round it included, turned as it
        was placed: the texels it takes and the only ones baked (99l)."""
        key = (self.scale, margin, self.angle)
        if key not in self._shape:
            w, h, ox, oy = self.frame()
            if not self.angle and not any(i.polys for i in self.islands):
                m = np.ones((h + 2 * margin, w + 2 * margin), bool)
            else:
                polys = self._polys()
                if self.angle:
                    polys = [[_spin(p, self.angle) for p in tri] for tri in polys]
                m = _draw([[(x - ox, y - oy) for x, y in tri] for tri in polys], margin, w, h)
            self._shape[key] = m
        m = self._shape[key]
        return np.rot90(m, k=-1) if self.rot else m

    @property
    def src_w(self):
        return self.rect[2] - self.rect[0]

    @property
    def src_h(self):
        return self.rect[3] - self.rect[1]


def _spin(p, deg: float) -> Tuple[float, float]:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return p[0] * c - p[1] * s, p[0] * s + p[1] * c


def _least_box_angle(pts) -> float:
    """The turn, in degrees in 0..90, that puts ``pts`` in the rectangle of
    least area: one of its convex hull's edges lies along it."""
    P = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    if len(P) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    hull = np.array(lo[:-1] + hi[:-1], float)
    xs, ys = hull[:, 0], hull[:, 1]
    base = (xs.max() - xs.min()) * (ys.max() - ys.min())
    best, best_a = base, 0.0
    for i in range(len(hull)):
        dx, dy = hull[(i + 1) % len(hull)] - hull[i]
        if not dx and not dy:
            continue
        a = -math.degrees(math.atan2(dy, dx)) % 90.0
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        rx, ry = xs * c - ys * s, xs * s + ys * c
        area = (rx.max() - rx.min()) * (ry.max() - ry.min())
        if area < best - 1e-9:
            best, best_a = area, a
    # a turn within a degree of square, or one that saves under 2 per cent
    # of the rectangle, is not worth its resample
    if best_a < 1.0 or best_a > 89.0 or best > base * 0.98:
        return 0.0
    return round(best_a, 3)


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def make_blocks(islands: List[_Island], dyes: bool = True, scales: Optional[dict] = None) -> List[Block]:
    """Islands folded into blocks: the same source image, dyed the same way,
    at the same scale, and their art overlapping."""
    scales = scales or {}
    buckets: Dict[tuple, List[_Island]] = {}
    for isl in islands:
        sc = float(scales.get(str(isl.obj.get("id")), 1.0) or 1.0)
        key = (isl.src[0], isl.src[2], isl.src[3], _dye_key(isl.obj, dyes), sc)
        buckets.setdefault(key, []).append(isl)
    blocks: List[Block] = []
    for key, items in buckets.items():
        # 99l: two islands fold when a texel is under both, not when their
        # rectangles cross: rectangles chained most of a sheet into one block
        parent = list(range(len(items)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        order = sorted(range(len(items)), key=lambda i: items[i].rect[0])
        for n, i in enumerate(order):
            ri = items[i].rect
            for j in order[n + 1:]:
                rj = items[j].rect
                if rj[0] >= ri[2]:
                    break
                if find(i) != find(j) and _overlap(ri, rj) and _masks_meet(items[i], items[j]):
                    parent[find(j)] = find(i)
        groups: Dict[int, List[_Island]] = {}
        for i in range(len(items)):
            groups.setdefault(find(i), []).append(items[i])
        for members in groups.values():
            r = [min(m.rect[0] for m in members), min(m.rect[1] for m in members),
                 max(m.rect[2] for m in members), max(m.rect[3] for m in members)]
            b = Block(members, members[0].src, r, key[3])
            b.scale = key[4]
            blocks.append(b)
    return blocks


# ---------------------------------------------------------------------------
# packing: by shape (99l), into every hole (99p), quarter turns allowed


def margin_px(pct: float, size: int) -> int:
    return max(0, int(math.ceil(size * float(pct) / 100.0)))


def _coarse(m: np.ndarray, cell: int) -> np.ndarray:
    """A mask on a grid of ``cell`` texels, a cell taken if any texel is."""
    if cell == 1:
        return m
    h, w = m.shape
    H, W = -(-h // cell) * cell, -(-w // cell) * cell
    pad = np.zeros((H, W), bool)
    pad[:h, :w] = m
    return pad.reshape(H // cell, cell, W // cell, cell).any(axis=(1, 3))


def _fast(n: int) -> int:
    """The least length of at least ``n`` with no prime factor past 5: the
    FFT's quick sizes."""
    while True:
        m = n
        for p in (2, 3, 5):
            while m % p == 0:
                m //= p
        if m == 1:
            return n
        n += 1


class _Profile:
    """The sheet as columns, each filled down to a depth (99l), kept beside
    :class:`_Occupancy` (99p) as the quick first try: a block's mask
    is set down from the top as far as each of its columns lets it, so a
    block's empty top corner takes another's bottom one. Masks never overlap;
    a hole left under a block is not used again.

    ``score`` is how a place is chosen: ``"gap"`` the room left empty under
    the block, ``"mix"`` that and how low the block's bottom reaches, ``"end"``
    the bottom alone (bottom-left)."""

    def __init__(self, size: int, cell: int, score: str = "mix"):
        self.cols = self.rows = -(-size // cell)
        self.sky = np.zeros(self.cols, np.int64)
        self.score = score

    def place(self, shapes) -> Optional[Tuple[int, int, int]]:
        """The best of ``shapes`` (coarse masks, one per turn) and where it
        goes, ``(x, y, which)`` in cells."""
        from numpy.lib.stride_tricks import sliding_window_view
        low = np.iinfo(np.int64).min // 4
        best = None
        for which, m in enumerate(shapes):
            h, w = m.shape
            if w > self.cols or h > self.rows:
                continue
            filled = m.any(axis=0)
            top = np.where(filled, m.argmax(axis=0), 0)
            bottom = np.where(filled, h - m[::-1].argmax(axis=0), 0)
            need = np.where(filled, -top, low)
            win = sliding_window_view(self.sky, w)
            ys = np.maximum((win + need).max(axis=1), 0)
            ok = ys + h <= self.rows
            if not ok.any():
                continue
            ends = ys + int(bottom.max())
            if self.score == "end":
                rank = ends
            else:
                gap = (((ys[:, None] + top[None, :]) - win) * filled[None, :]).sum(axis=1)
                rank = gap + ends * w if self.score == "mix" else gap
            rank = np.where(ok, rank, np.iinfo(np.int64).max)
            x = int(rank.argmin())
            score = (int(rank[x]), int(ys[x]), x)
            if best is None or score < best[0]:
                best = (score, x, int(ys[x]), which, filled, bottom)
        if best is None:
            return None
        _s, x, y, which, filled, bottom = best
        seg = self.sky[x:x + len(filled)]
        self.sky[x:x + len(filled)] = np.where(filled, np.maximum(seg, y + bottom), seg)
        return x, y, which


class _Occupancy:
    """The sheet as the texels taken (99p): a block may go wherever its mask
    meets none of them, a hole under another block or a pocket at its side as
    well as the open sheet. Every place is weighed at once on a coarse grid
    (``cell`` texels, a cell taken if any texel of it is) by correlating the
    block's mask with the grid through an FFT; the place chosen is then slid
    up and left texel by texel against the exact texels, so it sits as close
    as the art allows.

    ``score`` is how a place is chosen: ``"contact"`` the share of the block's
    outline that touches what is already there or the sheet's edge, ``"tl"``
    the first place from the top left."""

    def __init__(self, side: int, cell: int, score: str = "contact", kernels: Optional[dict] = None):
        self.cell, self.score = cell, score
        #: each mask's coarse grid, outline and their transforms, kept across
        #: the ways :func:`pack` tries (the grid's size is the same for all)
        self.kernels = {} if kernels is None else kernels
        n = -(-side // cell)
        self.n = n
        # the coarse grid with a ring of taken cells round it, then taken
        # padding up to a quick FFT size
        self.N = _fast(n + 2)
        # the exact texels, the ones past the sheet's own side taken (a mask
        # whose last row or column is empty may hang over them)
        self.E = np.ones((self.N * cell, self.N * cell), bool)
        self.E[:side, :side] = False
        self.G = np.ones((self.N, self.N), bool)
        self.G[1:n + 1, 1:n + 1] = _coarse(self.E[:n * cell, :n * cell], cell)
        self._F = None

    def _corr(self, K: np.ndarray, h: int, w: int) -> np.ndarray:
        """For every place of an ``h`` by ``w`` kernel's corner on the grid,
        how many of its cells fall on taken ones; ``K`` is its transform."""
        N = self.N
        if self._F is None:
            self._F = np.fft.rfft2(self.G.astype(np.float32))
        r = np.fft.irfft2(self._F * K, s=(N, N))
        return r[:N - h + 1, :N - w + 1]

    def _kernel(self, m: np.ndarray):
        got = self.kernels.get(id(m))
        if got is None or got[0] is not m:
            N, cell = self.N, self.cell
            S = _coarse(m, cell)
            pad = np.zeros((S.shape[0] + 2, S.shape[1] + 2), bool)
            pad[1:-1, 1:-1] = S
            ring = grow(pad, 1) & ~pad
            KS = np.conj(np.fft.rfft2(S.astype(np.float32), s=(N, N)))
            KR = np.conj(np.fft.rfft2(ring.astype(np.float32), s=(N, N))) if self.score == "contact" else None
            got = (m, S.shape, KS, ring, KR)
            self.kernels[id(m)] = got
        if self.score == "contact" and got[4] is None:
            got = got[:4] + (np.conj(np.fft.rfft2(got[3].astype(np.float32), s=(self.N, self.N))),)
            self.kernels[id(m)] = got
        return got

    def place(self, shapes) -> Optional[Tuple[int, int, int]]:
        """The best of ``shapes`` (exact masks, one per turn) and where it
        goes, ``(x, y, which)`` in texels."""
        N, cell = self.N, self.cell
        best = None
        for which, m in enumerate(shapes):
            _m, (hs, ws), KS, ring, KR = self._kernel(m)
            if hs > self.n or ws > self.n:
                continue
            ov = self._corr(KS, hs, ws)[1:N - hs, 1:N - ws]
            free = ov < 0.5
            if not free.any():
                continue
            if self.score == "contact":
                ct = np.rint(self._corr(KR, hs + 2, ws + 2)[:N - hs - 1, :N - ws - 1]) / max(1, int(ring.sum()))
                top = ct[free].max()
                pick = free & (ct >= top - 1e-9)
                key0 = -round(float(top), 4)
            else:
                pick, key0 = free, 0.0
            i = int(pick.argmax())
            gy, gx = divmod(i, pick.shape[1])
            key = (key0, gy, gx)
            if best is None or key < best[0]:
                best = (key, gx * cell, gy * cell, which)
        if best is None:
            return None
        _k, x, y, which = best
        m = shapes[which]
        h, w = m.shape
        E = self.E

        def clear(yy, xx):
            return not (E[yy:yy + h, xx:xx + w] & m).any()
        for _ in range(64):
            moved = False
            while y > 0 and clear(y - 1, x):
                y -= 1
                moved = True
            while x > 0 and clear(y, x - 1):
                x -= 1
                moved = True
            if not moved:
                break
        E[y:y + h, x:x + w] |= m
        cy0, cx0 = y // cell, x // cell
        cy1, cx1 = -(-(y + h) // cell), -(-(x + w) // cell)
        self.G[1 + cy0:1 + cy1, 1 + cx0:1 + cx1] = _coarse(E[cy0 * cell:cy1 * cell, cx0 * cell:cx1 * cell], cell)
        self._F = None
        return x, y, which


def pack(blocks: List[Block], size: int, margin: int, free: bool = False,
         quick: bool = False, ways: Optional[tuple] = None) -> List[Block]:
    """Blocks placed on one sheet by their shapes (99l), into any room their
    masks fit (99p); the ones that did not fit come back. ``free`` lets a
    block take its own turn as well as the quarter turns (99p), at the cost
    of resampling it. ``quick`` is for a yes or no: a way stops at the
    first block it cannot place. ``ways`` is :data:`_PACK_WAYS` unless said."""
    # the margin keeps blocks apart, and may run off the sheet's own edge,
    # where no bleed is ever sampled: a block as wide as the sheet still fits.
    # Its art stops a texel short of the right and bottom edges, though: a
    # vertex on the edge itself has u = 1, which the game reads as the next
    # sheet along (99p). The coarse grid is a 256th of the sheet, for time.
    cell = max(1, size // int(_GRID))
    opts = {}
    for b in blocks:
        b.placed, b.rot = False, False
        mine = []
        # with free rotation the block's own turn is offered first, so it
        # wins a tie: it is what the user asked for
        for ang in ((b.free_angle(), 0.0) if free and b.free_angle() else (0.0,)):
            b.angle = ang
            w, h, _ox, _oy = b.frame()
            m = b.shape(margin)
            mine.append((ang, False, w, h, m))
            mine.append((ang, True, w, h, np.rot90(m, k=-1)))
        b.angle = 0.0
        b.w, b.h = mine[-1][2], mine[-1][3]
        opts[id(b)] = mine
    # no one way of choosing wins on every model, so the next is tried
    # while blocks are left over, and the one leaving the least is kept
    best = None
    kernels: dict = {}
    # 99l's column profile, on a grid of a 1024th of the sheet, goes first:
    # it costs no FFT, and when it fits the rest is never run
    pcell = max(1, size // 1024)
    coarse = {}
    for kind, score, order in (ways or _PACK_WAYS):
        if kind == "profile":
            occ = _Profile(size + 2 * margin - 1, pcell, score)
        else:
            occ = _Occupancy(size + 2 * margin - 1, cell, score, kernels)
        left, spots = [], {}
        for b in sorted(blocks, key=order):
            if quick and left:
                left.append(b)
                continue
            if kind == "profile":
                if id(b) not in coarse:
                    coarse[id(b)] = [_coarse(o[4], pcell) for o in opts[id(b)]]
                got = occ.place(coarse[id(b)])
                if got is not None:
                    got = (got[0] * pcell, got[1] * pcell, got[2])
            else:
                got = occ.place([o[4] for o in opts[id(b)]])
            if got is None:
                left.append(b)
            else:
                spots[id(b)] = got
        lost = sum(b.w * b.h for b in left)
        if best is None or lost < best[0]:
            best = (lost, left, spots)
        if not left:
            break
    _lost, left, spots = best
    for b in blocks:
        got = spots.get(id(b))
        b.placed = got is not None
        if got is not None:
            ang, rot, w, h, _m = opts[id(b)][got[2]]
            b.x, b.y, b.rot, b.angle, b.w, b.h = got[0], got[1], rot, ang, w, h
    return left


#: How :func:`pack` chooses, in the order tried: the placer, a place's
#: score, and the order the blocks are set down in. 99l's three ways first,
#: then the hole-filling ones (99p). Measured on four soldiers at 512, the
#: scale each needed: 99l's ways alone, the Dunedain knights 0.542, Mordor's
#: bodyguard 0.690, the peasants 0.844, the reference horse 0.968; each new
#: way was the best on one of them (top left by area the knights' attachment
#: sheet, by height the knights at 0.555 and the peasants at 0.848, contact
#: the horse at 1.000), and contact by height or by width never was.
_GRID = 256
_PACK_WAYS = (
    ("profile", "mix", lambda b: -b.w * b.h),
    ("profile", "gap", lambda b: (-b.h, -b.w)),
    ("profile", "end", lambda b: (-b.h, -b.w)),
    ("occupancy", "tl", lambda b: -b.w * b.h),
    ("occupancy", "tl", lambda b: (-b.h, -b.w)),
    ("occupancy", "contact", lambda b: -b.w * b.h),
)


def _needs(area: float, margin_pct: float = MARGIN_PCT) -> int:
    for s in SIZES:
        pad = margin_px(margin_pct, s) * 2
        if s * s >= area * PACK_SLACK + pad * math.sqrt(max(area, 1)) * 2:
            return s
    return SIZES[-1]


# ---------------------------------------------------------------------------
# the plan


def _colour(oid) -> Tuple[int, int, int]:
    """An object's colour in the export dialog, as ``armExpColour`` makes it."""
    import colorsys
    h = (float(oid or 0) * 137.508) % 360
    r, g, b = colorsys.hls_to_rgb(h / 360.0, 0.58, 0.62)
    return int(r * 255), int(g * 255), int(b * 255)


def _sheet_picture(blocks: List[Block], size: int, margin: int, side: int = 320) -> str:
    """The sheet as the export dialog shows it (99l): each placed block's
    shape in its object's colour, a PNG data URL ``side`` pixels wide."""
    import base64
    k = side / float(size)
    pic = np.zeros((side, side, 3), np.float32)
    pic[:] = (29, 33, 40)
    for b in blocks:
        if not b.placed:
            continue
        m = b.shape(margin)
        h, w = m.shape
        x0, y0 = int((b.x - margin) * k), int((b.y - margin) * k)
        tw, th = max(1, int(round(w * k))), max(1, int(round(h * k)))
        small = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((tw, th), Image.BILINEAR)) > 40
        ax, ay, bx, by = max(0, x0), max(0, y0), min(side, x0 + tw), min(side, y0 + th)
        if ax >= bx or ay >= by:
            continue
        sub = small[ay - y0:by - y0, ax - x0:bx - x0]
        region = pic[ay:by, ax:bx]
        region[sub] = region[sub] * 0.25 + np.array(_colour(b.objs[0] if b.objs else 0), np.float32) * 0.75
    buf = io.BytesIO()
    Image.fromarray(pic.astype(np.uint8), "RGB").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _sheet_of(b: Block, settings: dict, rooms: Dict[str, float]) -> str:
    over = (settings.get("block_sheet") or {}).get(b.id)
    if over in SHEETS:
        return over
    for oid in b.objs:
        s = (settings.get("obj_sheet") or {}).get(str(oid))
        if s in SHEETS:
            return s
    origins = {i.origin for i in b.islands}
    if origins == {"attach"}:
        return "attach"
    if origins == {"main"}:
        return "main"
    return min(SHEETS, key=lambda s: rooms[s])


def plan(project: dict, mod_of, settings: Optional[dict] = None, image_of: ImageOf = default_image_of,
         scope: Optional[dict] = None, _state: Optional[dict] = None) -> dict:
    """The UV menu's answer: islands measured, blocks packed, room left.

    ``settings``: ``size`` ``{main, attach}`` (a number or ``"auto"``),
    ``margin`` per cent, ``obj_sheet`` ``{id: main|attach}``, ``block_sheet``
    ``{block id: main|attach}``, ``scale`` ``{id: 0..1}``, ``dyes`` (true),
    ``auto`` (true to find a way out of a full sheet on its own), ``rotate``
    (``"quarter"``, the default, or ``"free"``: a block may also take the turn
    that boxes it smallest, which resamples it, 99p).
    """
    settings = dict(settings or {})
    objs = in_scope(project, scope)
    if not objs:
        raise BakeError(_i18n.msg("eng.armbake.nothing_to_export", "nothing to export: no object is visible or in a chosen collection"))
    assets = armory.project_assets(project)
    sheets = _Sheets(assets, mod_of, image_of)
    meshes, islands = gather(project, objs, mod_of, sheets)
    ext = {o.get("id") for o in objs if all((assets.get(pc.get("asset")) or {}).get("kind") == "external"
                                              for pc in o.get("src") or [])}
    for isl in islands:
        if isl.obj.get("id") in ext:
            isl.origin = "any"
    margin_pct = float(settings.get("margin", MARGIN_PCT))
    dyes = settings.get("dyes", True) is not False
    free_turn = settings.get("rotate") == "free"
    auto_note = None
    scales = dict(settings.get("scale") or {})
    sizes_in = settings.get("size") or {}

    # both sheets are always one size (the game's skins are pairs of a size)
    one = sizes_in.get("both") or sizes_in.get("main") or "auto"

    def fits(mine, size, ways=None):
        return not pack(mine, size, margin_px(margin_pct, size), free_turn, True, ways)

    def run(scales, block_sheet, quick=False, ways=None):
        blocks = make_blocks(islands, dyes, scales)
        st = dict(settings, block_sheet=block_sheet)
        rooms = {"main": 0.0, "attach": 0.0}
        order = sorted(blocks, key=lambda b: -(b.src_w * b.src_h))
        fixed = [b for b in order if {i.origin for i in b.islands} <= {"main", "attach"}
                 or (st.get("block_sheet") or {}).get(b.id)
                 or any(str(o) in (st.get("obj_sheet") or {}) for o in b.objs)]
        loose = [b for b in order if b not in fixed]
        for b in fixed + loose:
            b.sheet = _sheet_of(b, st, rooms)
            rooms[b.sheet] += b.src_w * b.src_h * b.scale * b.scale
        out = {}
        mines = {s: [b for b in blocks if b.sheet == s] for s in SHEETS}
        if one == "auto":
            size = SIZES[-1]
            for cand in SIZES:
                if all(fits(mines[s], cand, ways) for s in SHEETS if mines[s]):
                    size = cand
                    break
        else:
            size = int(one)
        for s in SHEETS:
            mine = mines[s]
            area = sum(b.src_w * b.src_h * b.scale * b.scale for b in mine)
            if not mine:
                out[s] = {"size": 0, "blocks": [], "left": [], "area": 0, "needs": 0}
                continue
            left = pack(mine, size, margin_px(margin_pct, size), free_turn, quick, ways)
            out[s] = {"size": size, "blocks": mine, "left": left, "area": area, "needs": _needs(area, margin_pct)}
        return blocks, out

    block_sheet = dict(settings.get("block_sheet") or {})
    blocks, per = run(scales, block_sheet)
    moved = 0
    if settings.get("auto") and any(per[s]["left"] for s in SHEETS):
        # first the cheap way out: blocks that did not fit go to the other
        # sheet while it has room; then, if a sheet is still full, every
        # block on it is scaled down as one, as little as will do
        for s in SHEETS:
            other = "attach" if s == "main" else "main"
            for b in sorted(per[s]["left"], key=lambda b: b.src_w * b.src_h):
                trial = dict(block_sheet, **{b.id: other})
                _b2, p2 = run(scales, trial)
                if not p2[other]["left"] and len(p2[s]["left"]) < len(per[s]["left"]):
                    block_sheet, blocks, per = trial, _b2, p2
                    moved += 1
        for s in SHEETS:
            if not per[s]["left"]:
                continue
            ids = {o for b in per[s]["blocks"] for o in b.objs}

            def full(k, ways=None):
                trial = dict(scales, **{str(o): round(float(scales.get(str(o), 1.0)) * k, 4) for o in ids})
                return not run(trial, block_sheet, True, ways)[1][s]["left"]
            # 99p: the hole-filling ways cost an FFT a block, so the scale is
            # first found with 99l's profile alone, which is quick and always
            # tried first; the full search then only looks above it, and a
            # trial stops at the first block that will not go
            lo, hi = 0.05, 1.0
            for _ in range(9):
                mid = (lo + hi) / 2
                if full(mid, _PACK_WAYS[:3]):
                    lo = mid
                else:
                    hi = mid
            top = min(1.0, lo * 1.12)
            if full(top):
                lo, hi = top, 1.0
            else:
                hi = top
            while hi - lo > 0.003:
                mid = (lo + hi) / 2
                if full(mid):
                    lo = mid
                else:
                    hi = mid
            scales = dict(scales, **{str(o): round(float(scales.get(str(o), 1.0)) * lo, 4) for o in ids})
            blocks, per = run(scales, block_sheet)
            auto_note = {"sheet": s, "scale": round(lo, 3), "moved": moved}
        if moved and auto_note is None:
            auto_note = {"moved": moved}
    # the answer
    objects = []
    by_obj: Dict[int, List[Block]] = {}
    for b in blocks:
        for o in b.objs:
            by_obj.setdefault(o, []).append(b)
    for o in objs:
        mine = by_obj.get(o.get("id"), [])
        area = sum(b.src_w * b.src_h for b in mine)
        origins = {i.origin for b in mine for i in b.islands if i.obj is o}
        objects.append({"id": o.get("id"), "name": full_name(o), "area": area,
                        "needs": _needs(area, margin_pct) if area else 0,
                        "origin": (origins.pop() if len(origins) == 1 else "both") if origins else "main",
                        "sheets": sorted({b.sheet for b in mine}),
                        "scale": float(scales.get(str(o.get("id")), 1.0)),
                        "islands": sum(1 for i in islands if i.obj is o)})
    sheets_out = {}
    for s in SHEETS:
        p = per[s]
        size = p["size"]
        sheets_out[s] = {
            "size": size, "needs": p["needs"], "area": p["area"],
            "fill": (sum(int(b.shape(margin_px(margin_pct, size)).sum())
                         for b in p["blocks"] if b.placed) / (size * size)) if size else 0,
            "picture": _sheet_picture(p["blocks"], size, margin_px(margin_pct, size)) if size else "",
            "margin_px": margin_px(margin_pct, size) if size else 0,
            "recommended_margin": round(SCALED_MARGIN_PX * 100.0 / size, 2) if size else 0,
            "blocks": [{"id": b.id, "objs": b.objs, "x": b.x, "y": b.y, "w": b.w, "h": b.h,
                        "rot": b.rot, "angle": b.angle, "placed": b.placed, "islands": len(b.islands),
                        "share": (b.w * b.h) / (size * size) if size else 0}
                       for b in p["blocks"]],
            "left": [b.id for b in p["left"]],
        }
    if _state is not None:
        _state.update(blocks=blocks, meshes=meshes, objs=objs, sheets=sheets, per=per,
                      margin_pct=margin_pct, dyes=dyes, islands=islands)
    folded = len(islands) - len(blocks)
    return {"objects": objects, "sheets": sheets_out, "islands": len(islands), "blocks": len(blocks),
            "folded": folded, "fits": not any(per[s]["left"] for s in SHEETS),
            "settings": {"scale": scales, "block_sheet": block_sheet, "margin": margin_pct,
                         "rotate": "free" if free_turn else "quarter"},
            "turned": sum(1 for b in blocks if b.placed and b.angle),
            "auto": auto_note}



# ---------------------------------------------------------------------------
# normal maps (95j)

#: Measured on 30 skins in Heirs of Elendil and the Americas campaign, each
#: shipped normal map against its own diffuse: the map tilts AGAINST the
#: lightness gradient in both x and y (correlations -0.58 and -0.82), and its
#: spread is 1.27 times the gradient's (the median; 1.03 to 1.57 between the
#: quartiles). Encoded as ``0.5 + n / 2``, that is a gain of 2.53 at strength 1.
NORMAL_GAIN = 2.53
#: A flat map: what the Blender kit ships, and *Skip*. The alpha is left
#: empty, as the shipped maps all but leave it (a median of 0.01 to 0.03).
NORMAL_FLAT = (128, 128, 255, 0)
NORMAL_MODES = ("skip", "generic", "specialized")
#: Generic's one setting, and Specialized's per material: metal keeps its
#: fine scratches sharp and shallow, cloth and leather are softened and deeper,
#: wood's grain is deepest, skin barely raised.
NORMAL_GENERIC = {"strength": 1.0, "blur": 0.8, "invert": False}
NORMAL_MATERIALS = {
    "metal": {"strength": 0.7, "blur": 0.0, "invert": False},
    "fabric": {"strength": 1.0, "blur": 1.0, "invert": False},
    "leather": {"strength": 1.2, "blur": 0.8, "invert": False},
    "wood": {"strength": 1.4, "blur": 0.5, "invert": False},
    "skin": {"strength": 0.5, "blur": 1.5, "invert": False},
    "hair": {"strength": 1.2, "blur": 0.0, "invert": False},
    "bone": {"strength": 0.8, "blur": 0.8, "invert": False},
    "other": {"strength": 1.0, "blur": 0.8, "invert": False},
}


def normal_setting(normals: Optional[dict], obj: dict) -> Optional[dict]:
    """The setting an object's part of the map is made with; None for Skip.

    ``armNormalSetting`` in armobj.js is the same choice."""
    normals = normals or {}
    mode = normals.get("mode") or "skip"
    if mode == "generic":
        return dict(NORMAL_GENERIC, **(normals.get("generic") or {}))
    if mode != "specialized":
        return None
    mat = obj.get("material") or "other"
    out = dict(NORMAL_MATERIALS.get(mat, NORMAL_MATERIALS["other"]),
               **((normals.get("materials") or {}).get(mat) or {}))
    own = obj.get("normal")
    if own:
        out.update({k: own[k] for k in ("strength", "blur", "invert") if k in own})
    return out


def _kernel(sigma: float) -> np.ndarray:
    r = int(math.ceil(3 * sigma))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-x * x / (2 * sigma * sigma))
    return k / k.sum()


def _blur_height(h: np.ndarray, sigma: float) -> np.ndarray:
    """A separable Gaussian, edges held, exactly as ``armBlurHeight`` does it."""
    if sigma <= 0.05:
        return h
    k = _kernel(sigma)
    r = len(k) // 2
    p = np.pad(h, ((0, 0), (r, r)), mode="edge")
    h = sum(k[i] * p[:, i:i + h.shape[1]] for i in range(len(k)))
    p = np.pad(h, ((r, r), (0, 0)), mode="edge")
    return sum(k[i] * p[i:i + h.shape[0], :] for i in range(len(k)))


def normal_pixels(rgba: np.ndarray, setting: dict) -> np.ndarray:
    """A tangent-space normal map of RGBA art: its lightness taken as height,
    blurred by ``blur`` texels, tilted ``strength`` times the measured gain
    against the slope (``invert`` turns it the other way)."""
    rgb = rgba[..., :3].astype(np.float64) / 255.0
    h = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    h = _blur_height(h, float(setting.get("blur") or 0))
    p = np.pad(h, 1, mode="edge")
    dx = (p[1:-1, 2:] - p[1:-1, :-2]) / 2
    dy = (p[2:, 1:-1] - p[:-2, 1:-1]) / 2
    s = float(setting.get("strength", 1.0)) * NORMAL_GAIN * (-1.0 if setting.get("invert") else 1.0)
    nx, ny = -s * dx, -s * dy
    ln = np.sqrt(nx * nx + ny * ny + 1.0)
    out = np.empty(rgba.shape[:2] + (4,), np.uint8)
    for i, c in enumerate((nx / ln, ny / ln, 1.0 / ln)):
        out[..., i] = np.clip(np.floor((c * 0.5 + 0.5) * 255 + 0.5), 0, 255)
    out[..., 3] = 0
    return out


def dds_with_mipmaps(im: Image.Image) -> bytes:
    """A DXT5 ``.dds`` with its whole mipmap chain down to 1x1, each level
    made from the full image. Measured on 800 of Heirs of Elendil's unit
    sheets: 797 carry a full chain (11 levels at 1024, 12 at 2048)."""
    levels = []
    cur = im
    while True:
        buf = io.BytesIO()
        cur.save(buf, "DDS", pixel_format="DXT5")
        levels.append(buf.getvalue())
        if cur.width == 1 and cur.height == 1:
            break
        cur = im.resize((max(1, cur.width // 2), max(1, cur.height // 2)), Image.LANCZOS)
    head = bytearray(levels[0][:128])
    flags, = struct.unpack_from("<I", head, 8)
    struct.pack_into("<I", head, 8, flags | 0x20000)            # DDSD_MIPMAPCOUNT
    struct.pack_into("<I", head, 28, len(levels))
    caps, = struct.unpack_from("<I", head, 108)
    struct.pack_into("<I", head, 108, caps | 0x400008)          # COMPLEX | MIPMAP
    return bytes(head) + b"".join(lv[128:] for lv in levels)


def _write_sheet(out: Path, name: str, canvas: np.ndarray) -> List[str]:
    from . import sprites
    im = Image.fromarray(canvas, "RGBA")
    im.save(out / f"{name}.png")
    (out / f"{name}.texture").write_bytes(sprites.dds_to_texture(dds_with_mipmaps(im)))
    return [f"{name}.texture", f"{name}.png"]


# ---------------------------------------------------------------------------
# the bake


def _crop_wrapped(img: np.ndarray, x0: int, y0: int, w: int, h: int) -> np.ndarray:
    """``w`` x ``h`` pixels from ``(x0, y0)``, the image repeating past its edges."""
    H, W = img.shape[:2]
    xs = np.arange(x0, x0 + w) % W
    ys = np.arange(y0, y0 + h) % H
    return img[ys][:, xs]


def _processed(st: dict, b: Block, image_of: ImageOf) -> Optional[np.ndarray]:
    """The block's source image, dyed and stamped as its object asks."""
    sid, img, base, span, pc = b.src
    if img is None:
        return None
    if not st["dyes"]:
        return img
    o = b.islands[0].obj
    if not o.get("dye") and not o.get("stamps"):
        return img
    cache = st.setdefault("_done", {})
    key = (sid, b.dkey, base, span)
    if key in cache:
        return cache[key]
    out = img
    if o.get("dye"):
        out = dye_pixels(out, o["dye"], o.get("material") or "")
    for stamp in o.get("stamps") or []:
        path = stamp.get("path") or ""
        # read here and baked, never served: an image file the project names
        if not path or Path(path).suffix.lower() not in armory.IMAGE_SUFFIXES or not Path(path).is_file():
            continue
        try:
            simg = image_of(path)
        except (OSError, ValueError, armory.ArmoryError):
            continue
        box = _art_box(st, o, sid, base, span, img)
        if box is not None:
            out = stamp_pixels(out, simg, stamp, box)
    cache[key] = out
    return out


def _art_box(st, o, sid, base, span, img):
    """Every island of ``o`` on this image, as one box in its pixels."""
    rects = [i.rect for i in st["islands"] if i.obj is o and i.src[0] == sid and i.src[2] == base]
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects))


def _block_pixels(st: dict, b: Block, margin: int, image_of: ImageOf) -> np.ndarray:
    """The block's art with its margin, at its size on the sheet, turned."""
    tw, th = b.w + 2 * margin, b.h + 2 * margin
    img = _processed(st, b, image_of)
    if img is None:
        return np.broadcast_to(np.array(NO_ART, np.uint8), (th, tw, 4)).copy() if not b.rot             else np.broadcast_to(np.array(NO_ART, np.uint8), (tw, th, 4)).copy()
    x0, y0 = b.rect[0], b.rect[1]
    if b.scale == 1.0 and not b.angle:
        px = _crop_wrapped(img, x0 - margin, y0 - margin, tw, th)
    else:
        # only a block the user scaled, or one given a free turn (99p), is
        # resampled: its source with the margin round it, turned and scaled
        # into its size on the sheet. A sheet texel (X, Y) is the source
        # point the block's turn and scale undone, from the crop's corner.
        k = b.scale
        pad = int(math.ceil(margin * (1.5 if b.angle else 1.0) / k)) + 2
        src = _crop_wrapped(img, x0 - pad, y0 - pad, b.src_w + 2 * pad, b.src_h + 2 * pad)
        _w, _h, ox, oy = b.frame()
        c, s = math.cos(math.radians(b.angle)), math.sin(math.radians(b.angle))
        u0, v0 = ox - margin, oy - margin
        coeffs = (c / k, s / k, (c * u0 + s * v0) / k + pad,
                  -s / k, c / k, (-s * u0 + c * v0) / k + pad)
        im = Image.fromarray(src).transform((tw, th), Image.AFFINE, coeffs, resample=Image.BICUBIC)
        px = np.asarray(im)
    if b.rot:
        px = np.rot90(px, k=-1)
    return px


def _new_uv(b: Block, sx: float, sy: float, size: int, sheet: str) -> Tuple[float, float]:
    lx, ly = b.local(sx, sy)
    if b.rot:
        tx, ty = b.x + (b.h - ly), b.y + lx
    else:
        tx, ty = b.x + lx, b.y + ly
    return tx / size + (1.0 if sheet == "attach" else 0.0), ty / size


def bake(project: dict, mod_of, settings: Optional[dict], out_dir: str, stem: str,
         image_of: ImageOf = default_image_of, scope: Optional[dict] = None) -> dict:
    """The model and its new sheets, written to ``out_dir``.

    Writes ``<stem>.mesh``, ``<stem>.texture`` (and ``<stem>_attach.texture``
    when the attachment sheet is used) and a ``_normal`` map for each (95j:
    flat for *Skip*), with a ``.png`` of every sheet beside it.
    Refuses while a sheet still has blocks that do not fit.
    """
    stem = re.sub(r"[^A-Za-z0-9_\-]", "_", (stem or "").strip()) or "armory_model"
    st: dict = {}
    answer = plan(project, mod_of, settings, image_of, scope, _state=st)
    if not answer["fits"]:
        raise BakeError(_i18n.msg("eng.armbake.does_not_fit", "a sheet still has islands that do not fit; scale, move or lower the margin first"))
    out = Path(out_dir)
    if not str(out_dir).strip():
        raise BakeError(_i18n.msg("eng.armbake.no_folder", "choose a folder to export to"))
    out.mkdir(parents=True, exist_ok=True)
    blocks, meshes, objs, per = st["blocks"], st["meshes"], st["objs"], st["per"]
    normals = (settings or {}).get("normals") or project.get("normals") or {}
    # the sheets
    written = []
    sheet_files = {}
    for s in SHEETS:
        size = per[s]["size"]
        if not size:
            continue
        margin = margin_px(st["margin_pct"], size)
        canvas = np.zeros((size, size, 4), np.uint8)
        for b in per[s]["blocks"]:
            px = _block_pixels(st, b, margin, image_of)
            x, y = b.x - margin, b.y - margin
            h, w = px.shape[:2]
            ax, ay = max(0, x), max(0, y)
            bx, by = min(size, x + w), min(size, y + h)
            # 99l: only the texels under the block's triangles, with its margin
            keep = b.shape(margin)[ay - y:by - y, ax - x:bx - x]
            canvas[ay:by, ax:bx][keep] = px[ay - y:by - y, ax - x:bx - x][keep]
        name = stem if s == "main" else stem + "_attach"
        written += _write_sheet(out, name, canvas)
        sheet_files[s] = name
        # its normal map: each block's own part made from its baked art with
        # its object's setting, the margin included; flat where no art is
        nmap = np.empty_like(canvas)
        nmap[:] = NORMAL_FLAT
        for b in per[s]["blocks"]:
            setting = normal_setting(normals, b.islands[0].obj)
            if setting is None:
                continue
            fw = (b.h if b.rot else b.w) + 2 * margin
            fh = (b.w if b.rot else b.h) + 2 * margin
            x, y = max(0, b.x - margin), max(0, b.y - margin)
            x1, y1 = min(size, b.x - margin + fw), min(size, b.y - margin + fh)
            # blocks nest into each other's rectangles: each writes its shape
            ox, oy = b.x - margin, b.y - margin
            keep = b.shape(margin)[y - oy:y1 - oy, x - ox:x1 - ox]
            nmap[y:y1, x:x1][keep] = normal_pixels(canvas[y:y1, x:x1], setting)[keep]
        written += _write_sheet(out, name + "_normal", nmap)
    # the UVs: each vertex goes where its island's block went
    new_uv: Dict[int, Dict[int, Tuple[float, float]]] = {}
    for b in blocks:
        size = per[b.sheet]["size"]
        for isl in b.islands:
            om = meshes[isl.obj.get("id")]
            sid, img, base, span, _pc = isl.src
            W, H = (img.shape[1], img.shape[0]) if img is not None else (64, 64)
            d = new_uv.setdefault(isl.obj.get("id"), {})
            for v in isl.verts:
                sx = (om.uvs[v * 2] - base) * W / span
                sy = om.uvs[v * 2 + 1] * H
                d[v] = _new_uv(b, sx, sy, size, b.sheet)
    model = assemble(objs, meshes, new_uv, bone_table(objs, armory.project_assets(project), mod_of))
    from . import meshwrite
    meshwrite.write_mesh(model, out / f"{stem}.mesh")
    written.insert(0, f"{stem}.mesh")
    return {"folder": str(out), "files": written, "vertices": model.vertices,
            "triangles": model.triangles, "groups": len(model.groups),
            "sheets": {s: per[s]["size"] for s in SHEETS if per[s]["size"]},
            "normals": (normals.get("mode") or "skip"), "bones": len(model.bones),
            "missing_bones": list(model.notes)}


#: The bone table 682 of 756 soldier meshes in Heirs of Elendil and the
#: Americas campaign carry, the melee skeletons' (the bows add bone_bowoffset,
#: bone_bowstring and bone_sling, the slingers theirs): each bone's name and its
#: slot in the skeleton, the weapon and shield bones sharing slots. A model
#: whose parts bring no table of their own is written with this one.
STANDARD_BONES = [
    ("bone_pelvis", 0), ("bone_rthigh", 1), ("bone_rlowerleg", 2), ("bone_rfoot", 3), ("bone_abs", 4),
    ("bone_torso", 5), ("bone_head", 6), ("bone_jaw", 7), ("bone_eyebrow", 8), ("bone_rclavical", 9),
    ("bone_rupperarm", 10), ("bone_relbow", 11), ("bone_rhand", 12), ("bone_lclavical", 13),
    ("bone_lupperarm", 14), ("bone_lelbow", 15), ("bone_lhand", 16), ("bone_lthigh", 17),
    ("bone_llowerleg", 18), ("bone_lfoot", 19), ("bone_weapon01", 20), ("bone_weapon", 20),
    ("bone_weapon02", 21), ("bone_weapon03", 22), ("bone_shield01", 22), ("bone_shield", 22)]


def _real_table(m: mesh.MeshFile) -> bool:
    """A table a model the game loads would carry: every bone named, slot 0
    first, the slots never going down (a soldier's starts at the pelvis, a
    horse's at the saddle). A table this toolkit wrote before the fix (bones
    in the order met, one unnamed) is not one."""
    if not m.bones or len(m.bone_links) != len(m.bones) or any(not b for b in m.bones):
        return False
    if m.bone_links[0] != 0:
        return False
    return all(b >= a for a, b in zip(m.bone_links, m.bone_links[1:]))


def bone_table(objs: List[dict], assets: Dict[str, dict], mod_of) -> List[Tuple[str, int]]:
    """The bone table to write: the one the source models carry, by the
    vertices each brings; the standard melee table if none brings one.

    The game reads each bone's second number as its slot in the skeleton
    (``bone_weapon01`` and ``bone_weapon`` both 20). A table made up of the
    bones the parts happen to use, numbered in order, puts every vertex on the
    wrong bone and leaves the weapon with no ``bone_weapon`` to hang from: the
    crash of 2026-10-15."""
    from collections import Counter
    votes: Counter = Counter()
    for o in objs:
        for pc in o.get("src") or []:
            a = assets.get(pc.get("asset"))
            if a is None:
                continue
            try:
                m = armory.asset_mesh(a, mod_of)
            except (armory.ArmoryError, mesh.MeshError, OSError):
                continue
            if _real_table(m):
                votes[tuple(zip(m.bones, m.bone_links))] += len(set(armory.piece_indices(m, pc)))
    return list(votes.most_common(1)[0][0]) if votes else list(STANDARD_BONES)


def assemble(objs: List[dict], meshes: Dict[int, mesh.MeshFile],
             new_uv: Dict[int, Dict[int, Tuple[float, float]]],
             table: Optional[List[Tuple[str, int]]] = None) -> mesh.MeshFile:
    """The objects as one model: one vertex pool, a group each, written with
    ``table`` (:func:`bone_table`), each vertex's bones found in it by name
    (case aside); a bone it has not got goes to the pelvis and is named in
    ``out.notes``."""
    out = mesh.MeshFile(source="armory", format="mesh")
    table = list(table or STANDARD_BONES)
    out.bones = [n for n, _l in table]
    out.bone_links = [l for _n, l in table]
    slot: Dict[str, int] = {}
    for i, n in enumerate(out.bones):
        slot.setdefault(n.lower(), i)
    pelvis = slot.get("bone_pelvis", 0)
    missing: set = set()
    weights, ids = array("f"), bytearray()
    for o in objs:
        om = meshes[o.get("id")]
        base = out.vertices
        out.positions.extend(om.positions)
        out.normals.extend(om.normals)
        uv = new_uv.get(o.get("id"), {})
        for v in range(om.vertices):
            out.uvs.extend(uv.get(v, (om.uvs[v * 2], om.uvs[v * 2 + 1])))
        remap = []
        for name in om.bones:
            hit = slot.get((name or "").lower())
            if hit is None:
                hit = pelvis
                if name:
                    missing.add(name)
            remap.append(hit)
        skinned = len(om.weights) >= om.vertices * 2 and len(om.bone_ids) >= om.vertices * 4
        for v in range(om.vertices):
            if skinned:
                w0, w1 = om.weights[v * 2], om.weights[v * 2 + 1]
                b = om.bone_ids[v * 4:v * 4 + 4]
                first = remap[b[2]] if b[2] < len(remap) else pelvis
                second = remap[b[1]] if b[1] < len(remap) else pelvis
                if w1 <= 0:
                    second = first
                weights.extend((w0, w1))
                ids += bytes((0, second, first, 0))
            else:
                weights.extend((1.0, 0.0))
                ids += bytes((0, pelvis, pelvis, 0))
        g = om.groups[0] if om.groups else mesh.MeshGroup(o.get("name") or "part", o.get("mesh") or "part", array("H"))
        out.groups.append(mesh.MeshGroup(o.get("name") or g.name, o.get("mesh") or g.texture_group,
                                         array("H", (i + base for i in g.indices)), int(o.get("flag") or 0)))
    if out.vertices > 0xFFFF + 1:
        raise BakeError(_i18n.msg("eng.armory.too_many_vertices", "{n:,} vertices: a .mesh indexes at most 65,536", n=out.vertices))
    out.weights, out.bone_ids = weights, bytes(ids)
    out.lod_name = "characterlod0"
    out.notes = sorted(missing)
    return out
