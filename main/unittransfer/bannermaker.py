"""Repaint a faction's battle-banner texture sheets in new colours, pattern and symbol.

Written independently from a description of the behaviour (2026-11-06); the
feature follows Pfadfinder-Adam's campaign editor.

Every faction's banner sheet has the same layout: cloth, poles and trim sit in
the same places, only the heraldry differs. Taking what all the sheets share
(the median) leaves a white template: grey cloth that still carries its folds,
and poles and trim in their real colours. ``paint`` dyes the cloth of that
template with a pattern of up to three colours and an optional symbol.

    template(mod)        the white template built from the mod's own sheets
    paint(sheet, ...)    one painted picture
    plan(mod, body)      preview, writes nothing
    apply(mod, body)     writes the sheet, backs up, logs for Undo
"""
from __future__ import annotations

import base64
import binascii
import io
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config, gamepack
from . import i18n as _i18n
from .emblem import footprint  # noqa: F401  (kept available here)
from .logutil import file_op, log

XML_REL = "descr_banners_new.xml"

_SHARED_TOL = 16          # how far a sheet may stray from the median and still "look the same"
_GREY = 200.0             # the grey level a cloth of average light gets in the template
_OPAQUE = 128


class BannerError(Exception):
    """Something about the request or the mod that this cannot paint. Carries a sentence."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# patterns: banner-relative (u, v) in 0..1 -> colour index


def _bands(n, along_u):
    def sel(u, v):
        t = u if along_u else v
        return np.minimum(np.floor(np.asarray(t) * n), n - 1).astype(int)
    return sel


def _flag(test):
    def sel(u, v):
        return np.where(test(np.asarray(u, dtype=float), np.asarray(v, dtype=float)), 1, 0)
    return sel


def _plain(u, v):
    return np.zeros(np.shape(u), dtype=int)


def _three_slanting(u, v):
    return np.minimum(2, np.floor((np.asarray(u) + np.asarray(v)) * 1.5)).astype(int)


PATTERNS: Dict[str, Tuple[int, object]] = {
    "plain": (1, _plain),
    "two stripes, upright": (2, _bands(2, True)),
    "three stripes, upright": (3, _bands(3, True)),
    "two stripes, across": (2, _bands(2, False)),
    "three stripes, across": (3, _bands(3, False)),
    "halves, slanting /": (2, _flag(lambda u, v: u + v >= 1)),
    "halves, slanting \\": (2, _flag(lambda u, v: u <= v)),
    "three bands, slanting": (3, _three_slanting),
    "quarters": (2, _flag(lambda u, v: (u >= .5) ^ (v >= .5))),
    "a cross": (2, _flag(lambda u, v: (np.abs(u - .5) < .1) | (np.abs(v - .4) < .08))),
    "a slanting cross": (2, _flag(lambda u, v: (np.abs(u - v) < .1) | (np.abs(u + v - 1) < .1))),
    "a border": (2, _flag(lambda u, v: np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < .1)),
    "a stripe in the middle, upright": (2, _flag(lambda u, v: np.abs(u - .5) < .17)),
    "a stripe in the middle, across": (2, _flag(lambda u, v: np.abs(v - .5) < .12)),
}


# ---------------------------------------------------------------------------
# reading pictures and the XML


def faction_sheet(name: str) -> bool:
    base = re.split(r"[\\/]", name or "")[-1].lower()
    if not base.startswith("faction_banner_"):
        return False
    return not any(bad in base for bad in ("ally", "enemy", "test_", "_trans"))


def read_picture(path) -> Image.Image:
    """Any picture the toolkit handles (.texture, .dds, .tga, .png ...) as RGBA."""
    p = Path(path)
    if p.suffix.lower() == ".texture":
        from . import sprites
        data = sprites.texture_to_dds(p.read_bytes())
        with Image.open(io.BytesIO(data)) as im:
            out = im.convert("RGBA")
    else:
        with Image.open(p) as im:
            out = im.convert("RGBA")
    out.load()
    return out


def _clean(ref: str) -> str:
    c = (ref or "").replace("\\", "/").strip()
    if c.lower().startswith("data/"):
        c = c[5:]
    return c


_DIFFUSE = re.compile(r'DiffuseMap\s*=\s*"([^"]*)"', re.I)


def sheet_refs(text: str) -> List[str]:
    seen, out = set(), []
    for m in _DIFFUSE.finditer(text or ""):
        raw = m.group(1)
        if not faction_sheet(raw):
            continue
        c = _clean(raw)
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


_BANNER = re.compile(r"<Banner\s([^>]*)>(.*?)</Banner\s*>", re.I | re.S)
_MESH_ATTR = re.compile(r'\b(Main|Mini|General|Building)Mesh\s*=\s*"([^"]*)"', re.I)


def mesh_refs(mod, text: str) -> List[Tuple[str, Path]]:
    out, seen = [], set()
    for m in _BANNER.finditer(text or ""):
        if not any(faction_sheet(d) for d in _DIFFUSE.findall(m.group(2))):
            continue
        for a in _MESH_ATTR.finditer(m.group(1)):
            ref = _clean(a.group(2))
            if not ref:
                continue
            found = gamepack.lookup(ref, mod)[0]
            if found is None or str(found).lower() in seen:
                continue
            seen.add(str(found).lower())
            out.append((a.group(1).capitalize(), Path(found)))
    return out


_TEXTURE_TAG = re.compile(r"<Texture\b[^>]*>", re.I)
_FACTION = re.compile(r'\bFaction\s*=\s*"([^"]*)"', re.I)


def target_of(text: str, slot: str) -> Tuple[str, bool]:
    want = (slot or "").strip().lower()
    ref = ""
    rows = []
    for tag in _TEXTURE_TAG.findall(text or ""):
        f, d = _FACTION.search(tag), _DIFFUSE.search(tag)
        if f and d:
            rows.append((f.group(1).strip().lower(), d.group(1)))
    for f, d in rows:
        if f == want and faction_sheet(d):
            ref = d
            break
    if not ref:
        return "", False
    mine = ref.replace("\\", "/").lower()
    shared = any(f != want and d.replace("\\", "/").lower() == mine for f, d in rows)
    return ref, shared


# ---------------------------------------------------------------------------
# small image helpers


def _components(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    """8-connected labelling of a bool mask: (labels 0 = none, 1..n, n)."""
    h, w = mask.shape
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    rows = []
    prev = []
    for y in range(h):
        row = mask[y]
        if row.any():
            d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
            starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        else:
            starts = ends = []
        cur = []
        for s, e in zip(starts, ends):
            lab = 0
            for ps, pe, pl in prev:
                if ps <= e and pe >= s:
                    r = find(pl)
                    if lab == 0:
                        lab = r
                    elif r != lab:
                        parent[r] = lab
            if lab == 0:
                parent.append(len(parent))
                lab = len(parent) - 1
            cur.append((int(s), int(e), lab))
        rows.append(cur)
        prev = cur
    remap, n = {}, 0
    labels = np.zeros((h, w), dtype=np.int32)
    for y, cur in enumerate(rows):
        for s, e, lab in cur:
            r = find(lab)
            if r not in remap:
                n += 1
                remap[r] = n
            labels[y, s:e] = remap[r]
    return labels, n


def _close(mask: np.ndarray, size: int) -> np.ndarray:
    im = Image.fromarray((mask * 255).astype(np.uint8), "L")
    im = im.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size))
    return np.asarray(im) > 127


def _mesh_cover(path, size) -> Optional[np.ndarray]:
    """The pixels of the sheet a mesh covers, or None when it will not read."""
    from . import mesh as _mesh
    try:
        m = _mesh.read_mesh(path)
    except Exception:
        return None
    if not m.uvs or not m.groups:
        return None
    w, h = size
    uv = np.frombuffer(m.uvs.tobytes(), dtype=np.float32).reshape(-1, 2).astype(float)
    px = np.clip(uv[:, 0] / 2.0, 0.0, 1.0) * w          # the reader doubles u
    py = np.clip(uv[:, 1], 0.0, 1.0) * h
    im = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(im)
    for g in m.groups:
        idx = np.frombuffer(g.indices.tobytes(), dtype=np.uint16)
        for i in range(0, len(idx) - 2, 3):
            a, b, c = idx[i], idx[i + 1], idx[i + 2]
            if max(a, b, c) >= len(px):
                continue
            dr.polygon([(px[a], py[a]), (px[b], py[b]), (px[c], py[c])], fill=255, outline=255)
    return np.asarray(im) > 0


# ---------------------------------------------------------------------------
# the white template


class Sheet:
    """The white template: the sheet with every faction's own dye and heraldry taken out."""

    def __init__(self, base, cloth, labels, panels, copies, light, count):
        self._base = base                      # uint8 H x W x 4
        self.blank = Image.fromarray(base, "RGBA")
        self.size = self.blank.size
        self.cloth = cloth                     # bool H x W
        self.labels = labels                   # int32, panel index or -1
        self.panels: List[Tuple[int, int, int, int]] = panels
        self.copies: List[tuple] = copies      # (dx, dy, box, mask)
        self.light = light                     # float32 H x W, 1.0 = average cloth light
        self.count = count


def _luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def make_sheet(pictures, mesh_paths=(), mini_paths=()) -> Sheet:
    pics = list(pictures)
    if not pics:
        raise BannerError(_i18n.msg("eng.bannermaker.no_sheets",
                                    "this mod names no faction banner sheets in {rel}, so there is no template to paint",
                                    rel=XML_REL))
    size = pics[0].size
    pics = [p.convert("RGBA") for p in pics if p.size == size]
    n = len(pics)
    w, h = size
    stack = np.stack([np.asarray(p) for p in pics]).astype(np.int16)        # n,h,w,4
    med = np.median(stack, axis=0)
    base = np.rint(med).astype(np.uint8)
    alpha = base[..., 3]
    opaque = alpha >= _OPAQUE

    if n > 2:
        near = (np.abs(stack - med).max(axis=3) <= _SHARED_TOL).sum(axis=0)
        shared = near >= min(n - 1, max(3, int(np.ceil(n * 0.4))))
    else:
        shared = np.zeros((h, w), dtype=bool)

    # which pixels a mesh covers: exactly one mesh means cloth, and each mesh's
    # cloth is its own banner (or banners), never merged with its neighbour's
    live = opaque & ~shared
    cover = np.zeros((h, w), dtype=np.int16)
    picks = []
    for path, is_mini in [(p, False) for p in mesh_paths] + [(p, True) for p in mini_paths]:
        got = _mesh_cover(path, size)
        if got is None or not got.any():
            continue
        cover += got
        picks.append((got, is_mini))
    regions, mini_flags = [], []
    if picks:
        for got, is_mini in picks:
            reg = got & (cover == 1) & ~shared
            if reg.any():
                regions.append(reg)
                mini_flags.append(is_mini)
    if not regions:
        regions, mini_flags = [live], [False]

    # narrow slits inside a banner are cloth too
    k = 2 * max(1, w // 256) + 3
    allraw = np.zeros((h, w), dtype=bool)
    for reg in regions:
        allraw |= reg
    labels = np.zeros((h, w), dtype=np.int32)
    mini_cover = np.zeros((h, w), dtype=bool)
    cnt = 0
    min_area = max(12, w * h // 4000)
    found = []
    for reg, is_mini in zip(regions, mini_flags):
        reg = reg | (_close(reg, k) & ~(opaque & shared) & ~(allraw & ~reg))
        lab, c = _components(reg)
        areas_ = np.bincount(lab.ravel(), minlength=c + 1)
        found.extend((lab, i, int(areas_[i]), is_mini) for i in range(1, c + 1))
    biggest = {m: max([a_ for _l, _i, a_, mm in found if mm == m] or [0]) for m in (False, True)}
    for lab, i, area_, is_mini in found:
        # crumbs beside a banner (rails, trim) are not banners of their own
        if area_ < min_area or (len(regions) > 1 and area_ * 3 < biggest[is_mini]):
            continue
        sel = lab == i
        cnt += 1
        labels[sel] = cnt
        if is_mini:
            mini_cover |= sel
    cloth = labels > 0

    # panels; small pennants that look like another are copies of it
    boxes, areas = {}, {}
    for i in range(1, cnt + 1):
        yy, xx = np.nonzero(labels == i)
        boxes[i] = (int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1)
        areas[i] = len(yy)
    order = sorted(range(1, cnt + 1), key=lambda i: -areas[i])
    dark = (_luma(med[..., :3]) < 16) | (med[..., 3] < _OPAQUE)
    copy_masks = []                      # (dx, dy, box, mask)
    if mini_cover.any():
        for i in order:
            if (labels == i)[mini_cover].sum() * 2 < areas[i]:
                continue
            x0, y0, x1, y1 = boxes[i]
            src = labels[y0:y1, x0:x1] == i
            for dx, dy in ((w // 4, 0), (0, h // 2), (w // 4, h // 2)):
                if x1 + dx > w or y1 + dy > h:
                    continue
                if (dark[y0:y1, x0:x1] == dark[y0 + dy:y1 + dy, x0 + dx:x1 + dx]).mean() < 0.97:
                    continue
                if cloth[y0 + dy:y1 + dy, x0 + dx:x1 + dx][src].mean() > 0.05:
                    continue
                keep = (live & ~shared)[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
                copy_masks.append((dx, dy, (x0 + dx, y0 + dy, x1 + dx, y1 + dy), src & keep))
    copies = []
    for dx, dy, box, mask in copy_masks:
        cloth[box[1]:box[3], box[0]:box[2]] |= mask
        copies.append((dx, dy, box, mask))
    panel_labels = np.full((h, w), -1, dtype=np.int32)
    panels = []
    for new, i in enumerate(order):
        panel_labels[labels == i] = new
        panels.append(boxes[i])

    # the grey of the cloth: each sheet's light relative to its own average, median across sheets
    ys, xs = np.nonzero(cloth)
    if len(ys):
        lum = _luma(stack[:, ys, xs, :3].astype(float))                 # n,N
        ok = stack[:, ys, xs, 3] >= _OPAQUE
        lum = np.where(ok, lum, np.nan)
        mean = np.nanmean(lum, axis=1)
        mean = np.where(np.isfinite(mean) & (mean > 1), mean, 1.0)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = np.nanmedian(lum / mean[:, None], axis=0)
        r = np.where(np.isfinite(r), r, 1.0)
        grey = np.clip(r * _GREY, 0, 255)
        base[ys, xs, 0] = base[ys, xs, 1] = base[ys, xs, 2] = np.rint(grey).astype(np.uint8)

    light = np.ones((h, w), dtype=np.float32)
    if len(ys):
        valid = alpha[ys, xs] >= _OPAQUE
        g = base[ys, xs, 0].astype(float)
        ref = float(np.median(g[valid])) if valid.any() else _GREY
        ref = max(ref, 8.0)
        light[ys, xs] = np.clip(g / ref, 0.15, 2.0)
    return Sheet(base, cloth, panel_labels, panels, copies, light, n)


def _dye(c, k):
    k = np.asarray(k, dtype=float)[:, None]
    lo = c * np.minimum(k, 1.0)
    hi = (255.0 - c) * np.maximum(k - 1.0, 0.0) * 0.8
    return np.clip(lo + hi, 0, 255)


def _symbol_spot(inside, pw, ph, s):
    """Top-left (x, y) in panel coordinates for an s-square on the cloth, nearest the wanted place."""
    wx = (pw - s) // 2
    wy = int(round(ph * 0.42 - s / 2))
    wy = max(0, min(wy, ph - s))
    ii = np.pad(inside.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    tot = ii[s:, s:] - ii[:-s, s:] - ii[s:, :-s] + ii[:-s, :-s]
    ok = tot == s * s
    if ok[wy, wx] if (wy < ok.shape[0] and wx < ok.shape[1]) else False:
        return wx, wy
    yy, xx = np.nonzero(ok)
    if not len(yy):
        return wx, wy
    d = (xx - wx) ** 2 + (yy - wy) ** 2
    j = int(d.argmin())
    return int(xx[j]), int(yy[j])


def paint(sheet: Sheet, colours, symbol=None, pattern="plain") -> Image.Image:
    count, select = PATTERNS.get(pattern, PATTERNS["plain"])
    cols = np.array([tuple(c[:3]) for c in colours], dtype=float)
    if not len(cols):
        cols = np.array([[255.0, 255.0, 255.0]])
    out = sheet._base.astype(float)
    h, w = out.shape[:2]
    lab = sheet.labels
    ys, xs = np.nonzero(lab >= 0)
    if len(ys):
        pid = lab[ys, xs]
        bx = np.array(sheet.panels, dtype=float)
        u = (xs + 0.5 - bx[pid, 0]) / (bx[pid, 2] - bx[pid, 0])
        v = (ys + 0.5 - bx[pid, 1]) / (bx[pid, 3] - bx[pid, 1])
        idx = np.clip(np.asarray(select(u, v)).astype(int), 0, len(cols) - 1)
        out[ys, xs, :3] = _dye(cols[idx], sheet.light[ys, xs])

    if symbol is not None:
        fp = footprint(symbol)
        if fp is not None:
            crop = symbol.convert("RGBA").crop((fp[0], fp[1], fp[0] + fp[2], fp[1] + fp[3]))
            for n_, (x0, y0, x1, y1) in enumerate(sheet.panels):
                pw, ph = x1 - x0, y1 - y0
                s = int(min(pw * 0.6, ph * 0.5))
                if s < 2:
                    continue
                inside = lab[y0:y1, x0:x1] == n_
                sx, sy = _symbol_spot(inside, pw, ph, s)
                k = min(s / crop.width, s / crop.height)
                nw, nh = max(1, round(crop.width * k)), max(1, round(crop.height * k))
                sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
                sq.paste(crop.resize((nw, nh), Image.LANCZOS), ((s - nw) // 2, (s - nh) // 2))
                a = np.asarray(sq).astype(float)
                gx, gy = x0 + sx, y0 + sy
                region = (slice(gy, gy + s), slice(gx, gx + s))
                cl = (lab[region] == n_)
                alpha = a[..., 3] / 255.0 * cl
                shaded = _dye(a[..., :3].reshape(-1, 3), sheet.light[region].reshape(-1)).reshape(s, s, 3)
                cur = out[region]
                cur[..., :3] = cur[..., :3] * (1 - alpha[..., None]) + shaded * alpha[..., None]
                out[region] = cur

    for dx, dy, (x0, y0, x1, y1), mask in sheet.copies:
        sy, sx = np.nonzero(mask)
        ty, tx = sy + y0, sx + x0
        fy, fx = ty - dy, tx - dx
        good = (fy >= 0) & (fy < h) & (fx >= 0) & (fx < w)
        out[ty[good], tx[good], :3] = out[fy[good], fx[good], :3]

    res = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    res[..., 3] = sheet._base[..., 3]
    return Image.fromarray(res, "RGBA")


# ---------------------------------------------------------------------------
# the template of a mod, cached

_cache_lock = threading.Lock()
_cache: Dict[str, object] = {"key": None, "sheet": None}


def _xml_text(mod) -> str:
    path = gamepack.lookup(XML_REL, mod)[0]
    if path is None:
        return ""
    return Path(path).read_bytes().decode("latin-1")


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def template(mod) -> Optional[Sheet]:
    text = _xml_text(mod)
    sheets = []
    for ref in sheet_refs(text):
        found = gamepack.lookup(ref, mod)[0]
        if found is not None:
            sheets.append(Path(found))
    if not sheets:
        return None
    meshes = mesh_refs(mod, text)
    key = (str(mod.root),
           tuple((str(p), _mtime(p)) for p in sheets),
           tuple((k, str(p), _mtime(p)) for k, p in meshes))
    with _cache_lock:
        if _cache["key"] == key:
            return _cache["sheet"]
        pics = []
        for p in sheets:
            try:
                pic = read_picture(p)
            except Exception:
                continue
            if not pics or pic.size == pics[0].size:
                pics.append(pic)
        if not pics:
            return None
        sheet = make_sheet(pics,
                           [p for k, p in meshes if k != "Mini"],
                           [p for k, p in meshes if k == "Mini"])
        _cache["key"], _cache["sheet"] = key, sheet
        return sheet


# ---------------------------------------------------------------------------
# the request


_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _pattern_of(raw) -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "plain"
    names = list(PATTERNS)
    if isinstance(raw, int) and not isinstance(raw, bool):
        n = raw
    elif isinstance(raw, str) and raw.strip().isdigit():
        n = int(raw.strip())
    else:
        n = None
    if n is not None and 0 <= n < len(names):
        return names[n]
    name = str(raw).strip() if n is None else str(n)
    if name not in PATTERNS:
        raise BannerError(_i18n.msg("eng.bannermaker.bad_pattern", "no pattern called {p}", p=name))
    return name


def _colours_of(raw, need: int) -> List[Tuple[int, int, int]]:
    items = list(raw or [])[:3]
    if not items:
        raise BannerError(_i18n.msg("eng.bannermaker.no_colour", "pick at least one colour"))
    out = []
    for c in items:
        text = str(c).strip()
        m = _HEX.match(text)
        if not m:
            raise BannerError(_i18n.msg("eng.bannermaker.bad_colour", "{c} is not a colour like #c81e1e",
                                        c=text or "''"))
        v = int(m.group(1), 16)
        out.append((v >> 16, (v >> 8) & 255, v & 255))
    while len(out) < need:
        out.append(out[-1])
    return out


def _symbol_of(raw) -> Optional[Image.Image]:
    if not raw or not str(raw).strip():
        return None
    try:
        data = base64.b64decode(str(raw).strip())
        with Image.open(io.BytesIO(data)) as im:
            pic = im.convert("RGBA")
        pic.load()
        return pic
    except Exception:
        raise BannerError(_i18n.msg("eng.bannermaker.bad_symbol", "the symbol is not a picture this can read"))


def _data_uri(im: Image.Image, box: Tuple[int, int]) -> str:
    small = im.copy()
    small.thumbnail(box, Image.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _prepare(mod, body: dict) -> dict:
    sheet = template(mod)
    if sheet is None:
        raise BannerError(_i18n.msg("eng.bannermaker.no_sheets",
                                    "this mod names no faction banner sheets in {rel}, so there is no template to paint",
                                    rel=XML_REL))
    slot = str(body.get("faction") or "").strip()
    pattern = _pattern_of(body.get("pattern"))
    colours = _colours_of(body.get("colours"), PATTERNS[pattern][0])
    symbol = _symbol_of(body.get("symbol"))
    text = _xml_text(mod)
    ref, shared = target_of(text, slot)
    was = _clean(ref)
    target = f"banners/textures/faction_banner_{slot}.texture" if (shared or not ref) else was
    return {"sheet": sheet, "slot": slot, "image": paint(sheet, colours, symbol, pattern),
            "target": target, "was": was, "shared": shared, "text": text}


def plan(mod, body: dict) -> dict:
    p = _prepare(mod, body)
    s = p["sheet"]
    return {
        "faction": p["slot"],
        "sheets": s.count,
        "panels": len(s.panels),
        "copies": len(s.copies),
        "preview": _data_uri(p["image"], (768, 384)),
        "template": _data_uri(s.blank, (384, 192)),
        "target": p["target"],
        "was": p["was"],
        "shared": p["shared"],
        "patterns": list(PATTERNS),
    }


def _repoint(text: str, slot: str, old: str, new: str) -> str:
    want = slot.lower()

    def row(m):
        tag = m.group(0)
        f = _FACTION.search(tag)
        if not f or f.group(1).strip().lower() != want:
            return tag
        return _DIFFUSE.sub(
            lambda d: 'DiffuseMap="%s"' % new if _clean(d.group(1)).lower() == old.lower() else d.group(0), tag)

    return _TEXTURE_TAG.sub(row, text)


def apply(mod, body: dict) -> dict:
    from . import armbake, sprites
    p = _prepare(mod, body)
    slot, target, was = p["slot"], p["target"], p["was"]
    tex = sprites.dds_to_texture(armbake.dds_with_mipmaps(p["image"]))

    writes: List[Tuple[str, bytes, str]] = [(target, tex, f"{len(tex)} bytes")]
    if target.lower() != was.lower():
        new_text = _repoint(p["text"], slot, was, target.replace("/", "\\"))
        writes.append((XML_REL, new_text.encode("latin-1"), "banner rows point at the faction's own sheet"))

    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    backed_up, created = [], []
    for rel, _data, _note in writes:
        dest = Path(mod.data) / rel
        if dest.exists():
            keep = backup_root / "data" / rel
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, keep)
            file_op("BACKUP", dest, f"-> {keep}")
            backed_up.append(rel)
        else:
            created.append(rel)
    for rel, data, note in writes:
        dest = Path(mod.data) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".new")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        file_op("WRITE", dest, note)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "factions",
        "action": "banners",
        "source": mod.name,
        "source_root": str(mod.root),
        "dest": mod.name,
        "dest_root": str(mod.root),
        "unit_type": slot,
        "resolved_type": slot,
        "options": {},
        "applied": True,
        "undone": False,
        "note": "",
        "summary": _i18n.msg("eng.bannermaker.summary", "new battle banners for {faction} in {rel}",
                             faction=slot, rel=target),
        "warnings": [],
        "manifest": {"backed_up": backed_up, "created": created},
        "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("BANNER %s in %s -> %s, id=%s", slot, mod.name, target, tid)
    return rec
