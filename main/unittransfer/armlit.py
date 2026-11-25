"""Armory Studio's pre-rendered bake: a lit colour texture per source texture.

Not the export's bake (:mod:`armbake` packs islands onto the game's sheets and
copies texels). This one takes objects that wear PBR maps and writes, for each
colour texture they wear, the same texture with the light painted in, on the
object's own UVs:

* the colour texture (``x_d``), its spec map (``x_s``: red metal, green gloss,
  blue ambient occlusion) and its normal map (``x_n``), found by name beside it;
* an even ambient light, and a key light with a direction, a height, a
  softness and a strength. ``shadows`` runs from 0 (none) to 1 (full): the
  key light's shadow mixed in by that much. Shadows only ever take the key
  light away, so nothing falls below its ambient light: no black. An object
  is shadowed by itself only;
* 2026-11-25: up to three more lights (``lights``), each a sun or a point
  as the unit card maker's are, with a direction, a height and a strength,
  and a point its distance from :data:`LAMP_CENTRE`. Each is lit and
  shadowed as the key light is; a point's light falls off as the card
  maker's does, and its shadow is cast along the line from the centre;
* stacked UV islands: each texel is baked from **one** island, the biggest
  that covers it. A smaller island lying on those texels reuses them, and one
  that overlaps in part bakes only the texels that are its own. So a stack is
  never half one side and half the other, nor a checker of the two;
* alpha is the source's, and so is every texel no triangle covers.

:func:`bake_image` is the arithmetic on arrays, :func:`bake_objects` reads the
project's objects and writes the files under :data:`armory.SHEETS_DIR`.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from . import armbake, armory

#: each setting's default and its range
RANGES = {
    "ambient": (0.8, 0.0, 2.0),
    "direction": (30.0, -180.0, 180.0),      # degrees round the model, 0 = from +z
    "height": (50.0, -90.0, 90.0),           # degrees above the horizon
    "softness": (0.5, 0.0, 1.0),
    "strength": (0.5, 0.0, 3.0),
    "shadows": (0.5, 0.0, 1.0),
}
#: an extra light's settings: default and range (``type`` is "sun" or "point")
LAMP_RANGES = {
    "direction": (-120.0, -180.0, 180.0),
    "height": (25.0, -90.0, 90.0),
    "strength": (0.5, 0.0, 3.0),
    "distance": (2.0, 0.2, 10.0),
}
LAMPS_MAX = 3
#: what a point light's distance is measured from: a metre above the origin
LAMP_CENTRE = np.array([0.0, 1.0, 0.0])
GAMMA = 2.2
#: how far the baked colour runs past an island's edge, in texels
BLEED = 2
SHADOW_MAP = 512
_COLOUR_END = re.compile(r"^(.*)_(d|diff|diffuse|albedo|col|color|colour|basecolor)$", re.I)
_KINDS = {"s": ("_s", "_spec", "_specular"), "n": ("_n", "_norm", "_normal", "_nrm")}


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
    lamps = []
    for one in (raw.get("lights") if isinstance(raw.get("lights"), list) else [])[:LAMPS_MAX]:
        one = one if isinstance(one, dict) else {}
        lamp = {"type": "point" if one.get("type") == "point" else "sun"}
        for key, (default, lo, hi) in LAMP_RANGES.items():
            try:
                lamp[key] = min(hi, max(lo, float(one.get(key, default))))
            except (TypeError, ValueError):
                lamp[key] = default
        lamps.append(lamp)
    out["lights"] = lamps
    return out


def light_dir(st: dict) -> np.ndarray:
    """The unit vector from the model towards the key light (y is up)."""
    a, h = math.radians(st["direction"]), math.radians(st["height"])
    return np.array([math.cos(h) * math.sin(a), math.sin(h), math.cos(h) * math.cos(a)])


def lamps(st: dict) -> List[dict]:
    """Every light that shines: the key light, then the extra ones. Each is
    ``{"dir", "strength", "point"}`` and a point's ``"pos"``; ``dir`` points
    from the model towards it (for a point, from :data:`LAMP_CENTRE`)."""
    out = []
    if st["key"] and st["strength"] > 0:
        out.append({"dir": light_dir(st), "strength": st["strength"], "point": False})
    for one in st.get("lights") or []:
        if one["strength"] <= 0:
            continue
        d = light_dir(one)
        lamp = {"dir": d, "strength": one["strength"], "point": one["type"] == "point"}
        if lamp["point"]:
            lamp["pos"] = LAMP_CENTRE + d * one["distance"]
        out.append(lamp)
    return out


def sibling(path: str, kind: str) -> str:
    """The spec (``"s"``) or normal (``"n"``) map beside a colour texture."""
    p = Path(path)
    m = _COLOUR_END.match(p.stem)
    base = m.group(1) if m else p.stem
    for end in _KINDS[kind]:
        for ext in (p.suffix, ".png", ".tga", ".dds"):
            q = p.with_name(base + end + ext)
            if q.is_file() and q.name.lower() != p.name.lower():
                return str(q)
    return ""


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _cover(pts: np.ndarray, tris: np.ndarray, order, w: int, h: int, allow=None):
    """Triangles drawn at the texel centres, in ``order``: for each texel the
    triangle that took it (-1: none) and two of its barycentric weights.
    ``allow(t, slice)`` says which texels triangle ``t`` may take."""
    tri = np.full((h, w), -1, np.int32)
    w0 = np.zeros((h, w), np.float32)
    w1 = np.zeros((h, w), np.float32)
    for t in order:
        a, b, c = pts[tris[t]]
        d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(d) < 1e-12:
            continue
        x0, x1 = max(int(math.floor(min(a[0], b[0], c[0]))), 0), min(int(math.ceil(max(a[0], b[0], c[0]))), w)
        y0, y1 = max(int(math.floor(min(a[1], b[1], c[1]))), 0), min(int(math.ceil(max(a[1], b[1], c[1]))), h)
        if x0 >= x1 or y0 >= y1:
            continue
        px = np.arange(x0, x1) + 0.5
        py = (np.arange(y0, y1) + 0.5)[:, None]
        l0 = ((b[0] - px) * (c[1] - py) - (c[0] - px) * (b[1] - py)) / d
        l1 = ((c[0] - px) * (a[1] - py) - (a[0] - px) * (c[1] - py)) / d
        m = (l0 >= -1e-5) & (l1 >= -1e-5) & (l0 + l1 <= 1 + 1e-5)
        if allow is not None:
            m &= allow(t, (slice(y0, y1), slice(x0, x1)))
        if m.any():
            tri[y0:y1, x0:x1][m] = t
            w0[y0:y1, x0:x1][m] = l0[m]
            w1[y0:y1, x0:x1][m] = l1[m]
    return tri, w0, w1


def _owners(uv: np.ndarray, tris: np.ndarray, island: np.ndarray, w: int, h: int):
    """Each texel's triangle, the biggest island first and keeping what it took."""
    p = uv[tris]
    area = np.abs((p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1])
                  - (p[:, 2, 0] - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1]))
    size = np.bincount(island, area)
    order = sorted(range(len(tris)), key=lambda t: (-size[island[t]], island[t]))
    own = np.full((h, w), -1, np.int32)

    def allow(t, sl):
        o = own[sl]
        return (o < 0) | (o == island[t])

    tri = np.full((h, w), -1, np.int32)
    w0 = np.zeros((h, w), np.float32)
    w1 = np.zeros((h, w), np.float32)
    # one island at a time, so a texel is owned before the next island asks
    start = 0
    while start < len(order):
        end = start
        while end < len(order) and island[order[end]] == island[order[start]]:
            end += 1
        t1, a1, b1 = _cover(uv, tris, order[start:end], w, h, allow)
        took = t1 >= 0
        tri[took], w0[took], w1[took] = t1[took], a1[took], b1[took]
        own[took] = island[order[start]]
        start = end
    return tri, w0, w1


def _visible(points: np.ndarray, ndl: np.ndarray, pos: np.ndarray, tris: np.ndarray,
             light: np.ndarray, soft: float) -> np.ndarray:
    """How much of the key light reaches each point past the triangles (0..1)."""
    up = np.array([0.0, 1.0, 0.0]) if abs(light[1]) < 0.99 else np.array([1.0, 0.0, 0.0])
    x = _unit(np.cross(up, light))
    y = np.cross(light, x)
    basis = np.stack([x, y, light], 1)
    q = pos @ basis
    lo = q[:, :2].min(0)
    span = max(float((q[:, :2].max(0) - lo).max()), 1e-9)
    scale = (SHADOW_MAP - 3) / span
    flat = (q[:, :2] - lo) * scale + 1.0
    # the nearest triangle to the light at each cell of the map: drawn far to near
    depth_of = q[tris][:, :, 2].mean(1)
    tri, w0, w1 = _cover(flat, tris, np.argsort(depth_of), SHADOW_MAP, SHADOW_MAP)
    z = q[tris][:, :, 2]
    safe = np.maximum(tri, 0)
    depth = np.where(tri >= 0, z[safe, 0] * w0 + z[safe, 1] * w1 + z[safe, 2] * (1 - w0 - w1), -np.inf)
    r = points @ basis
    rx = (r[:, 0] - lo[0]) * scale + 1.0
    ry = (r[:, 1] - lo[1]) * scale + 1.0
    bias = span * (0.004 + 0.03 * (1.0 - np.clip(ndl, 0.0, 1.0)))
    reach = soft * 5.0
    steps = np.linspace(-reach, reach, 5) if reach >= 0.5 else np.array([0.0])
    seen = np.zeros(len(points))
    for dy in steps:
        for dx in steps:
            ix = np.clip((rx + dx).astype(int), 0, SHADOW_MAP - 1)
            iy = np.clip((ry + dy).astype(int), 0, SHADOW_MAP - 1)
            seen += depth[iy, ix] <= r[:, 2] + bias
    return seen / (len(steps) ** 2)


def _at(img: np.ndarray, ys: np.ndarray, xs: np.ndarray, h: int, w: int) -> np.ndarray:
    """A map's texels under the colour texture's, whatever its own size."""
    return img[ys * img.shape[0] // h, xs * img.shape[1] // w].astype(np.float64) / 255.0


def bake_image(colour: np.ndarray, spec: Optional[np.ndarray], normal: Optional[np.ndarray], *,
               pos: np.ndarray, nrm: np.ndarray, uv: np.ndarray, tris: np.ndarray,
               island: np.ndarray, obj: np.ndarray, settings: Optional[dict] = None) -> np.ndarray:
    """``colour`` (RGBA bytes) with the light baked in, as a new array.

    ``pos`` and ``nrm`` are per vertex, ``uv`` per vertex in the colour
    texture's texels (x right, y down), ``tris`` three vertices each, and
    ``island`` / ``obj`` name each triangle's UV island and object.
    """
    st = settings_of(settings)
    h, w = colour.shape[:2]
    out = colour.copy()
    if not len(tris):
        return out
    tri, w0, w1 = _owners(uv, tris, island, w, h)
    ys, xs = np.nonzero(tri >= 0)
    if not len(ys):
        return out
    t = tri[ys, xs]
    a = w0[ys, xs].astype(np.float64)[:, None]
    b = w1[ys, xs].astype(np.float64)[:, None]
    c = 1.0 - a - b
    i0, i1, i2 = tris[t, 0], tris[t, 1], tris[t, 2]
    point = pos[i0] * a + pos[i1] * b + pos[i2] * c
    n = _unit(nrm[i0] * a + nrm[i1] * b + nrm[i2] * c)

    if normal is not None:
        e1, e2 = pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]]
        d1, d2 = uv[tris[:, 1]] - uv[tris[:, 0]], uv[tris[:, 2]] - uv[tris[:, 0]]
        det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)[:, None]
        tan = ((e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det)[t]        # along the image's x
        bit = ((e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det)[t]        # along the image's y, downwards
        tan = _unit(tan - n * (tan * n).sum(1, keepdims=True))
        bit = _unit(bit - n * (bit * n).sum(1, keepdims=True))
        m = _at(normal, ys, xs, h, w)
        nx = m[:, 0] * 2 - 1
        ny = m[:, 1] * 2 - 1
        # green points down the image, as the bitangent does: Bannerlord's
        # ``_n`` maps (DirectX) and the viewport's own reading (armory.js)
        if st["flip_green"]:
            ny = -ny
        nz = np.sqrt(np.maximum(1 - nx * nx - ny * ny, 0.01))
        n = _unit(tan * nx[:, None] + bit * ny[:, None] + n * nz[:, None])

    base = (out[ys, xs, :3].astype(np.float64) / 255.0) ** GAMMA
    if spec is not None:
        s = _at(spec, ys, xs, h, w)
        metal, gloss, ao = s[:, 0], s[:, 1], 0.25 + 0.75 * s[:, 2]
    else:
        metal = gloss = np.zeros(len(ys))
        ao = np.ones(len(ys))

    light = st["ambient"] * (0.85 + 0.15 * n[:, 1]) * ao
    shine = np.zeros(len(ys))
    wrap = st["softness"] * 0.5
    for lamp in lamps(st):
        if lamp["point"]:
            d = lamp["pos"] - point
            dist = np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
            to = d / dist
            fall = 1.0 / (1.0 + 0.08 * dist[:, 0] ** 2)       # the card maker's point light
        else:
            to = np.broadcast_to(lamp["dir"], n.shape)
            fall = 1.0
        raw = (n * to).sum(1)
        ndl = np.clip((raw + wrap) / (1 + wrap), 0.0, 1.0)
        reach = np.ones(len(ys))
        if st["shadows"] > 0:
            o = obj[t]
            for one in np.unique(o):
                pick = o == one
                reach[pick] = _visible(point[pick], raw[pick], pos, tris[obj == one], lamp["dir"], st["softness"])
        key = lamp["strength"] * fall * ndl * (1 - st["shadows"] * (1 - reach))
        light = light + key
        ndh = np.clip((_unit(n + to) * n).sum(1), 0.0, 1.0)
        shine = shine + key * gloss * ndh ** (4 + 60 * gloss)
    tint = 0.08 + metal[:, None] * (base - 0.08)
    lit = base * light[:, None] + tint * shine[:, None]
    out[ys, xs, :3] = np.floor(np.clip(lit, 0.0, 1.0) ** (1 / GAMMA) * 255 + 0.5).astype(np.uint8)

    # the baked colour run a little past each island's edge, so a filtered
    # read at the seam does not pick up the unlit art beside it
    filled = tri >= 0
    rgb = out[..., :3]
    for _ in range(BLEED):
        grown = filled.copy()
        # each texel's neighbour on one side, the image's own edge left alone
        for to, frm in (((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
                        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                        ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
                        ((slice(None, -1), slice(None)), (slice(1, None), slice(None)))):
            take = filled[frm] & ~grown[to]
            rgb[to][take] = rgb[frm][take]
            grown[to] |= take
        filled = grown
    return out


# ---------------------------------------------------------------------------
# the project's objects


def _source_obj(o: dict) -> dict:
    """The object wearing what it wore before it was baked: a second bake
    starts from the source again, not from the lit texture."""
    if o.get("lit"):
        return dict(o, sheet=(o["lit"] or {}).get("src") or None)
    return o


def gather(project: dict, obj_ids, mod_of, image_of=armbake.default_image_of):
    """The named objects, one job per colour texture they wear: ``(jobs,
    skipped, sheets)``. A job holds the texture's ``path``, its ``normal``
    map, the ``objects`` on it and their triangles: ``pos`` / ``nrm`` / ``uv``
    (texels, x right, y down) per vertex, ``tris``, ``island`` and ``obj``.
    Shared by :func:`bake_objects` and :mod:`keyforce`'s Cycles bake."""
    want = {int(i) for i in obj_ids or []}
    objs = [_source_obj(o) for o in project.get("objects") or [] if o.get("id") in want]
    assets = armory.project_assets(project)
    sheets = armbake._Sheets(assets, mod_of, image_of)
    jobs: Dict[str, dict] = {}
    skipped: List[dict] = []
    isle = 0
    for o in objs:
        om, parts = armbake._object_parts(o, assets, mod_of)
        ix = om.groups[0].indices if om.groups else []
        pos = np.array(om.positions, float).reshape(-1, 3)
        nrm = np.array(om.normals, float).reshape(-1, 3)
        uvs = np.array(om.uvs, float).reshape(-1, 2)
        found = []           # (path, normal path, vertices, their texels, triangles, island)
        why = ""
        for start, count, pc in parts:
            if o.get("sheet"):
                pc = dict(pc, sheet=o["sheet"])
            for tl in armbake._islands(ix, start, start + count):
                verts = sorted({ix[k * 3 + j] for k in tl for j in range(3)})
                u = uvs[verts, 0]
                sid, img, base, span, tile = armbake._source_of(sheets, pc, float(u.min()), float(u.max()))
                if span != 1.0:
                    why = "two_sheets"
                    break
                path = sid if sheets.external(pc) else sid.rsplit("|", 1)[0]
                if img is None or not path:
                    why = "no_texture"
                    break
                hh, ww = img.shape[:2]
                px = np.stack([(u - base) * ww, uvs[verts, 1] * hh], 1)
                # a whole tile up or down the image is the same texels
                px[:, 1] -= math.floor(px[:, 1].min() / hh + 1e-6) * hh
                normals = sheets.normal_paths(pc)
                found.append((path, normals[1 if tile == 1 and normals[1] else 0] or sibling(path, "n"),
                              verts, px, [[ix[k * 3 + j] for j in range(3)] for k in tl], isle))
                isle += 1
            if why:
                break
        if not why and not found:
            why = "no_texture"
        if not why and len({f[0].lower() for f in found}) > 1:
            why = "two_sheets"
        if why:
            skipped.append({"id": o.get("id"), "why": why})
            continue
        job = jobs.setdefault(found[0][0].lower(), dict(path=found[0][0], normal=found[0][1], objects=[],
                                                        pos=[], nrm=[], uv=[], tris=[], island=[], obj=[], n=0))
        job["objects"].append(o.get("id"))
        for _path, _normal, verts, px, tl, number in found:
            at = {v: job["n"] + k for k, v in enumerate(verts)}
            job["pos"].append(pos[verts]); job["nrm"].append(nrm[verts]); job["uv"].append(px)
            job["tris"] += [[at[v] for v in tr] for tr in tl]
            job["island"] += [number] * len(tl)
            job["obj"] += [len(job["objects"])] * len(tl)
            job["n"] += len(verts)
    return jobs, skipped, sheets


def maps(project: dict, obj_ids, mod_of, image_of=armbake.default_image_of) -> dict:
    """``{id: {"colour", "spec", "normal"}}``: the maps the bake would light
    each object with, found as :func:`gather` finds them, so the viewport
    can draw the same light live (2026-11-25). An object the bake skips is
    left out; a map not found is ``""``. Each path is allowed to be served."""
    jobs, _skipped, _sheets = gather(project, obj_ids, mod_of, image_of)
    out = {}
    for job in jobs.values():
        one = {"colour": job["path"], "spec": sibling(job["path"], "s"), "normal": job["normal"] or ""}
        for path in one.values():
            if path:
                armory.allow_texture(path)
        for i in job["objects"]:
            out[str(i)] = one
    return out


def _shrink(img: Optional[np.ndarray], most: int) -> Optional[np.ndarray]:
    """``img`` no more than ``most`` pixels across, for a preview."""
    if img is None or max(img.shape[:2]) <= most:
        return img
    k = most / max(img.shape[:2])
    w, h = max(1, round(img.shape[1] * k)), max(1, round(img.shape[0] * k))
    return np.asarray(Image.fromarray(img).resize((w, h), Image.BILINEAR))


def bake_objects(project: dict, obj_ids, mod_of, settings: Optional[dict] = None,
                 image_of=armbake.default_image_of, out_dir: Optional[Path] = None,
                 preview: int = 0) -> dict:
    """Bake the named objects; one lit PNG per object and colour texture.

    2026-11-25: objects that share texels (a model's head variants, a collar
    UV'd over the legs) go to different files, so each keeps its own light
    where one file could hold only the biggest one's; objects that do not
    share stay together, so a model is still a few files (:func:`_apart`). A
    part mirrored onto its own other half still shares its texels.

    ``{"baked": [{"source", "path", "objects", "spec", "normal"}],
    "skipped": [{"id", "why"}]}``. An object drawing on two sheets at once is
    skipped (``two_sheets``), one with no texture too (``no_texture``).

    ``preview`` (2026-11-24): the viewport's look at what the bake will give,
    the same bake with each sheet shrunk to that many pixels across at most,
    written under ``lit/preview`` and with no normal map copied beside it.
    """
    st = settings_of(settings)
    jobs, skipped, sheets = gather(project, obj_ids, mod_of, image_of)
    out_dir = Path(out_dir) if out_dir else armory.SHEETS_DIR / "lit" / ("preview" if preview else "")
    baked = []
    for job in jobs.values():
        src = Path(job["path"])
        colour = sheets.image(job["path"])
        spec_path = sibling(job["path"], "s")
        spec = sheets.image(spec_path) if spec_path else None
        normal = sheets.image(job["normal"]) if job["normal"] else None
        if preview:
            colour, spec, normal = (_shrink(x, int(preview)) for x in (colour, spec, normal))
        pos, nrm, uv = np.concatenate(job["pos"]), np.concatenate(job["nrm"]), np.concatenate(job["uv"])
        tris, island, obj = np.array(job["tris"], int), np.array(job["island"], int), np.array(job["obj"], int)
        for group in _apart(uv, tris, obj, colour.shape[1], colour.shape[0]):
            pick = np.isin(obj, group)
            ids = [job["objects"][k - 1] for k in group]
            lit = bake_image(colour, spec, normal, pos=pos, nrm=nrm, uv=uv, tris=tris[pick],
                             island=island[pick], obj=obj[pick], settings=st)
            tag = hashlib.blake2b((str(src).lower() + "|" + ",".join(str(i) for i in sorted(ids))).encode("utf-8"),
                                  digest_size=4).hexdigest()
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"{src.stem}_lit_{tag}.png"
            Image.fromarray(lit, "RGBA").save(out)
            if normal is not None and not preview:
                # the export looks for a sheet's normal map beside it
                Image.fromarray(normal, "RGBA").save(out.with_name(out.stem + "_norm.png"))
            baked.append({"source": job["path"], "path": str(out), "objects": ids,
                          "spec": spec is not None, "normal": normal is not None})
    return {"baked": baked, "skipped": skipped, "settings": st}


#: at what fraction of the smaller object's texels two objects count as sharing
SHARED = 0.02


def _apart(uv: np.ndarray, tris: np.ndarray, obj: np.ndarray, w: int, h: int) -> List[List[int]]:
    """The job's objects (``obj``'s numbers) in groups whose texels do not
    overlap, the fewest a greedy pass finds: each to the first group it shares
    no texels with. Covered at half size, which is plenty to tell apart."""
    hw, hh = max(1, w // 2), max(1, h // 2)
    half = uv * 0.5
    masks = {}
    for k in np.unique(obj):
        t = tris[obj == k]
        cov, _, _ = _cover(half, t, range(len(t)), hw, hh)
        masks[int(k)] = cov >= 0
    groups: List[List[int]] = []
    taken: List[np.ndarray] = []
    # the biggest first, so a small one fits round them
    for k in sorted(masks, key=lambda k: -int(masks[k].sum())):
        m, n = masks[k], max(int(masks[k].sum()), 1)
        for g, used in zip(groups, taken):
            if int((used & m).sum()) <= SHARED * n:
                g.append(k)
                used |= m
                break
        else:
            groups.append([k])
            taken.append(m.copy())
    return [sorted(g) for g in groups]
