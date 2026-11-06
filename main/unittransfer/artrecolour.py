"""Move a faction's pictures from one pair of faction colours to another, keeping light and shade.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.

A faction's pictures are its unit cards, its unit-info pictures, its battle
textures (found through its records in the modeldb) and its symbols. The module
has three steps, all on a request body naming the mod, the faction, the colours
the pictures are in now (``source``) and the colours they should take
(``target``):

``plan``
    Writes nothing. Counts the pictures and shows a few before and after.
``sample``
    One picture again, with the hand touch-ups (an area clicked and given to the
    primary, the secondary, or "keep as it is").
``apply``
    Writes the pictures, with a backup of every file overwritten and a record
    in the log so Undo puts every byte back. A texture another faction also
    wears is never painted over: the faction gets a copy of its own, and only
    its own modeldb records are pointed at it.

Finding what is faction colour is the hard part. The hue says where the colour
is; the same picture in another faction's colours (the "comparison copies")
says what is not faction colour at all (faces, metal, wood); a click by hand
settles what both got wrong.
"""
from __future__ import annotations

import base64
import io
import os
import re
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

from . import config, factions, modeldb, modeltext
from . import i18n as _i18n
from .logutil import file_op, log

#: how far, summed over R, G and B, a pixel may be from the one clicked and
#: still count as the same patch of colour
ALIKE = 32
#: what a click can do: give the area to the primary, the secondary, or keep it
AREA_MODES = ("p", "s", "keep")
#: the most comparison pictures one picture is shown against
OTHERS_MAX = 6

_PICTURE_SUFFIXES = (".tga", ".dds", ".png")
_MODELDB_REL = "unit_models/battle_models.modeldb"
_SPACE_MARGIN = 50_000_000

# tuning of the colour finding (see recolour)
_HUE_NEAR = 0.07            # how close a pixel's hue is to the source hue
_HUE_ALIKE = 0.06           # how close two factions' hues must be to be "like"
_RIM_HUE = 0.12             # a looser hue for the rim beside a found part
_SAT_MIN = 0.20             # below this a pixel is not "clearly coloured"
_VAL_MIN = 0.12             # below this a pixel is shadow-black
_PLAIN_SAT = 0.28           # at or above this (and bright enough) a colour has a hue
_PLAIN_VAL = 0.10
_DARK, _LIGHT = 0.35, 0.70
_DIFF_MOST = 0.60           # more of the picture than this differs: the copies are other drawings
_SAME_COPY = 0.002          # a copy differing less than this is the same picture
_RIM_DEPTH = 2
_PLAIN_NEAR = 45            # how near the source's own colour a plain part's pixel is
_ALPHA_MIN = 16


class RecolourError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# colour arithmetic


def _hsv(rgb):
    """``(..., 3)`` array of 0..255 -> h, s, v arrays, each 0..1."""
    a = np.asarray(rgb, dtype=np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=-1)
    mn = a.min(axis=-1)
    d = mx - mn
    safe = np.where(d > 0, d, 1.0)
    h = np.zeros_like(mx)
    h = np.where(mx == r, ((g - b) / safe) % 6.0, h)
    h = np.where((mx == g) & (mx != r), (b - r) / safe + 2.0, h)
    h = np.where((mx == b) & (mx != r) & (mx != g), (r - g) / safe + 4.0, h)
    h = np.where(d > 0, h / 6.0, 0.0)
    s = np.where(mx > 0, d / np.where(mx > 0, mx, 1.0), 0.0)
    return h.astype(np.float32), s.astype(np.float32), mx.astype(np.float32)


def _rgb_of(h, s, v):
    """h, s, v arrays (0..1) -> ``(..., 3)`` uint8."""
    h = np.asarray(h, dtype=np.float32) % 1.0
    s = np.clip(s, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)
    i = np.floor(h * 6.0)
    f = h * 6.0 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i.astype(np.int32) % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    out = np.stack([r, g, b], axis=-1) * 255.0
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def _hsv1(c) -> Tuple[float, float, float]:
    h, s, v = _hsv(np.array([[c[0], c[1], c[2]]], dtype=np.float32))
    return float(h[0]), float(s[0]), float(v[0])


def _kind(c) -> str:
    """``hue`` for a colour with a hue, else ``dark`` / ``light`` / ``grey``."""
    h, s, v = _hsv1(c)
    if s >= _PLAIN_SAT and v >= _PLAIN_VAL:
        return "hue"
    if v < _DARK:
        return "dark"
    if v > _LIGHT:
        return "light"
    return "grey"


def _hdist(h, h0):
    d = np.abs(h - h0)
    return np.minimum(d, 1.0 - d)


def _like(a, b) -> bool:
    """Do two faction colours look alike (so one cannot tell the other apart)?"""
    ka, kb = _kind(a), _kind(b)
    if ka != kb:
        return False
    if ka != "hue":
        return True
    return float(_hdist(_hsv1(a)[0], _hsv1(b)[0])) < _HUE_ALIKE


def _wears_like(cols, c) -> bool:
    return any(oc and _like(oc, c) for oc in (cols or ()))


def _skin_like(c) -> bool:
    h, s, _v = _hsv1(c)
    return 0.02 <= h <= 0.15 and 0.2 <= s <= 0.8


# ---------------------------------------------------------------------------
# small image helpers


def _has_alpha(im) -> bool:
    if im.mode in ("RGBA", "LA", "RGBa", "La", "PA"):
        return True
    return im.mode == "P" and "transparency" in im.info


def _rgba(im):
    return np.array(im.convert("RGBA"))


def _grow(mask):
    """The mask one pixel wider all round (3x3)."""
    im = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    return np.array(im.filter(ImageFilter.MaxFilter(3))) > 127


def _shrink(mask):
    im = Image.fromarray(mask.astype(np.uint8) * 255, "L")
    return np.array(im.filter(ImageFilter.MinFilter(3))) > 127


def _as_mask(m, size):
    if m is None:
        return None
    if not isinstance(m, Image.Image):
        return np.asarray(m) > 127
    if m.size != size:
        return None
    return np.array(m.convert("L")) > 127


def _mask_image(m):
    return Image.fromarray(m.astype(np.uint8) * 255, "L")


# ---------------------------------------------------------------------------
# the area of like colour under a click


def _flood(cand, x, y):
    """The 4-connected patch of ``cand`` (a bool array) holding (x, y)."""
    hgt, wid = cand.shape
    seen = np.zeros_like(cand)
    if not cand[y, x]:
        return seen
    rows = [cand[i].tobytes() for i in range(hgt)]
    stack = [(x, y)]
    while stack:
        px, py = stack.pop()
        if seen[py, px] or not cand[py, px]:
            continue
        row = rows[py]
        left = row.rfind(b"\x00", 0, px) + 1
        right = row.find(b"\x00", px)
        if right < 0:
            right = wid
        seen[py, left:right] = True
        for ny in (py - 1, py + 1):
            if ny < 0 or ny >= hgt:
                continue
            seg = cand[ny, left:right] & ~seen[ny, left:right]
            if not seg.any():
                continue
            starts = seg & ~np.concatenate(([False], seg[:-1]))
            for s0 in np.flatnonzero(starts):
                stack.append((left + int(s0), ny))
    return seen


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _area(im, fx, fy, alike=ALIKE):
    a = _rgba(im)
    hgt, wid = a.shape[:2]
    x = min(max(int(_num(fx) * wid), 0), wid - 1)
    y = min(max(int(_num(fy) * hgt), 0), hgt - 1)
    try:
        alike = int(alike)
    except (TypeError, ValueError):
        alike = ALIKE
    alike = min(max(alike, 0), 255)
    rgb = a[..., :3].astype(np.int32)
    diff = np.abs(rgb - rgb[y, x]).sum(axis=-1)
    cand = (diff <= alike) & (a[..., 3] >= _ALPHA_MIN)
    return _flood(cand, x, y)


def area_mask(im, fx, fy, alike=ALIKE):
    """The patch of like colour joined to the point (fx, fy), as an 'L' mask."""
    return _mask_image(_area(im, fx, fy, alike))


def touch_edits(im, clicks):
    """The hand touch-ups of a picture as ``{"p", "s", "keep"}`` masks, or None."""
    if not clicks:
        return None
    wid, hgt = im.size
    masks = {k: np.zeros((hgt, wid), dtype=bool) for k in AREA_MODES}
    for c in clicks:
        if not isinstance(c, dict):
            continue
        mode = c.get("mode", "p")
        if mode not in AREA_MODES:
            continue
        area = _area(im, _num(c.get("x", 0)), _num(c.get("y", 0)), c.get("alike", ALIKE))
        for k in AREA_MODES:
            if k == mode:
                masks[k] |= area
            else:
                masks[k] &= ~area
    return {k: _mask_image(m) for k, m in masks.items()}


# ---------------------------------------------------------------------------
# finding and painting the faction colour


class _Look:
    """One picture's colour features, computed once."""

    def __init__(self, rgba):
        self.rgb = rgba[..., :3].astype(np.float32)
        self.alpha = rgba[..., 3]
        self.opaque = self.alpha >= _ALPHA_MIN
        self.h, self.s, self.v = _hsv(self.rgb)
        # the room for a difference to be noise: wider in the dark
        self.tol = 40.0 + 60.0 * (1.0 - np.minimum(1.0, self.v / 0.5))


def _differs(look, other_rgb):
    diff = np.abs(look.rgb - other_rgb).sum(axis=-1)
    return diff > look.tol


def _copies(look, others, size):
    """``[(rgb array, colours)]`` for each usable comparison picture."""
    out = []
    for pic, cols in others or ():
        if pic is None or getattr(pic, "size", None) != size:
            continue
        out.append((_rgba(pic)[..., :3].astype(np.float32), cols))
    return out


def _informative(look, copies, colour):
    """The ``differs`` arrays of the copies whose faction wears nothing like ``colour``,
    or [] when the copies turn out to be other drawings."""
    diffs = []
    for rgb, cols in copies:
        if _wears_like(cols, colour):
            continue
        d = _differs(look, rgb)
        frac = d[look.opaque].mean() if look.opaque.any() else 0.0
        if _SAME_COPY <= frac <= _DIFF_MOST:          # not a twin, not another drawing
            diffs.append(d)
    return diffs


def _most(diffs):
    """Where the picture differs from most (half or more) of the copies."""
    n = len(diffs)
    count = np.sum(diffs, axis=0)
    return count * 2 >= n


def _skin(look, diffs, src, strict=False):
    """Skin and hair tones that are kept (see the module notes). ``strict``
    (a card or unit-info picture) keeps every lit skin tone, whatever the colour."""
    if strict:
        return ((look.h >= 0.02) & (look.h <= 0.15) & (look.s >= 0.2) & (look.s <= 0.7)
                & (look.v >= 0.45))
    if _skin_like(src):
        return np.zeros_like(look.opaque)
    keep = ((look.h >= 0.02) & (look.h <= 0.12) & (look.s >= 0.2) & (look.s <= 0.7)
            & (look.v >= 0.25))
    if diffs:
        keep &= look.v >= 0.6
        keep &= ~np.all(diffs, axis=0)
    return keep


def _hue_part(look, src, diffs, strict=False):
    """(mask, score) of the pixels that are the chromatic colour ``src``."""
    sh, ss, sv = _hsv1(src)
    hd = _hdist(look.h, sh)
    core = (look.opaque & (look.s >= (_SAT_MIN if diffs else max(_SAT_MIN, 0.5 * ss))) & ((look.v >= _VAL_MIN) | ((look.s >= 0.6) & (look.v >= 0.04)))
            & (hd <= _HUE_NEAR))
    core &= ~_skin(look, diffs, src, strict)
    if diffs:
        core &= _most(diffs)
    score = hd * 3.0 + np.maximum(0.0, ss - look.s) + np.abs(look.v - sv) * 0.5
    return core, score


def _plain_part(look, src, diffs):
    """The pixels of the plain (black, white or grey) colour ``src``, which only
    the comparison copies can tell from the rest."""
    k = _kind(src)
    dull = look.opaque & ((look.s < _PLAIN_SAT) | (look.v < _PLAIN_VAL))
    if k == "dark":
        like = look.v < _DARK
    elif k == "light":
        like = look.v > _LIGHT
    else:
        like = (look.v >= _DARK) & (look.v <= _LIGHT)
    near = np.abs(look.rgb - np.array(src, dtype=np.float32)).sum(axis=-1) <= _PLAIN_NEAR
    cand = dull & like & near & _most(diffs)
    # only a broad flat area: it must survive a 5 px erosion
    core = _shrink(_shrink(cand))
    if not core.any():
        return np.zeros_like(cand)
    part = core
    for _ in range(2):
        part = _grow(part) & cand
    return _solid(part)


def _box_mean(mask, r):
    """Fraction of set pixels in the (2r+1) square round each pixel."""
    a = np.pad(mask.astype(np.float32), r, mode="constant")
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    tot = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return tot / float(n * n)


def _solid(mask, per=25000):
    """The mask without specks: a connected piece smaller than a few pixels
    (scaled to the picture) goes, a thin stroke that is joined up stays."""
    if not mask.any():
        return mask
    hgt, wid = mask.shape
    least = max(5, (hgt * wid) // per)
    parent: List[int] = []
    size: List[int] = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    runs = []                                  # per row: (starts, ends, first id)
    for y in range(hgt):
        row = mask[y].astype(np.int8)
        d = np.diff(np.concatenate(([0], row, [0])))
        st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        first = len(parent)
        for a0, b0 in zip(st, en):
            parent.append(len(parent))
            size.append(int(b0 - a0))
        runs.append((st, en, first))
        if y and len(st) and len(runs[y - 1][0]):
            pst, pen, pfirst = runs[y - 1]
            # 8-connected: runs overlap when they come within one pixel
            lo = np.searchsorted(pen, st - 1, side="right")       # first prev run ending at >= st
            hi = np.searchsorted(pst, en + 1, side="left")        # prev runs starting < en + 1
            for k in range(len(st)):
                for j in range(int(lo[k]), int(hi[k])):
                    ra, rb = find(first + k), find(pfirst + j)
                    if ra != rb:
                        parent[rb] = ra
                        size[ra] += size[rb]
    out = np.zeros_like(mask)
    for y, (st, en, first) in enumerate(runs):
        for k in range(len(st)):
            if size[find(first + k)] >= least:
                out[y, st[k]:en[k]] = True
    return out


def _rim(look, part, other, src, diffs, taken, strict=False):
    """The dull, dark or anti-aliased pixels beside a found part."""
    sh = _hsv1(src)[0]
    clean = (look.s >= 0.5) & (look.v >= 0.4)
    cand = (look.opaque & ~taken & ~other & (look.s >= 0.15) & (look.v >= 0.08)
            & (_hdist(look.h, sh) <= _RIM_HUE) & ~clean)
    cand &= ~_skin(look, diffs, src, strict)
    if diffs:
        cand &= _most(diffs)
    out = part.copy()
    for _ in range(_RIM_DEPTH):
        out |= _grow(out) & cand
    return out


def _paint(out, look, mask, src, tgt):
    """Write the target colour over the masked pixels of ``out`` (uint8 RGB)."""
    if not mask.any():
        return
    th, ts, tv = _hsv1(tgt)
    tk = _kind(tgt)
    sk = _kind(src) if src else None
    v = look.v[mask]
    vm = float(v.mean())
    if tk == "hue":
        if sk == "hue":
            _sh, ss, sv = _hsv1(src)
            ns = look.s[mask] * (ts / max(ss, 0.05))
            nv = v * (tv / max(sv, 0.05))
        else:
            ns = np.full_like(v, ts)
            nv = v * (tv / max(vm, 0.05))
        rgb = _rgb_of(np.full_like(v, th), ns, nv)
    else:
        if tk == "dark":
            m = 0.22
        elif tk == "light":
            m = tv if (src and vm >= _hsv1(src)[2] - 0.05) else 0.77
        else:
            m = tv
        nv = np.clip(v - vm + m, 0.0, 1.0)
        rgb = _rgb_of(np.zeros_like(v), np.zeros_like(v), nv)
    out[mask] = rgb


def recolour(im, source, target, others=(), edits=None, plain=True, kind=""):
    """``im`` with the faction colour moved from ``source`` to ``target``.

    Returns ``(image, share)``: the new picture (RGB, or RGBA with the original
    alpha) and the fraction of its pixels that were changed.
    """
    rgba = _rgba(im)
    hgt, wid = rgba.shape[:2]
    alpha_out = _has_alpha(im)
    look = _Look(rgba)
    src = tuple(source or (None, None))[:2]
    src = src + (None,) * (2 - len(src))
    tgt = tuple(target or (None, None))[:2]
    tgt = tgt + (None,) * (2 - len(tgt))
    copies = _copies(look, others, im.size)
    strict = kind in ("card", "info")      # faces and hands are never recoloured

    found: List[Optional[np.ndarray]] = [None, None]
    scores: List[Optional[np.ndarray]] = [None, None]
    diffs_of: List[list] = [[], []]
    for i in (0, 1):
        sc, tc = src[i], tgt[i]
        if not sc or not tc:
            continue
        sk, tk = _kind(sc), _kind(tc)
        if sk != "hue" and sk == tk:
            continue                                   # white to white keeps the artist's white
        diffs = _informative(look, copies, sc) if copies else []
        diffs_of[i] = diffs
        if sk == "hue":
            found[i], scores[i] = _hue_part(look, sc, diffs, strict)
        elif plain and diffs:
            found[i] = _plain_part(look, sc, diffs)

    none = np.zeros((hgt, wid), dtype=bool)
    p = found[0] if found[0] is not None else none
    s = found[1] if found[1] is not None else none
    if scores[0] is not None and scores[1] is not None:
        both = p & s
        p_wins = scores[0] <= scores[1]
        p = p & (~both | p_wins)
        s = s & ~(both & p_wins) & ~p
    s = s & ~p
    per = 6000 if kind == "texture" else 25000          # a model sheet's patches are big
    p, s = _solid(p, per) if found[0] is not None else p, _solid(s, per) if found[1] is not None else s
    # the rim beside the found chromatic parts
    for i in (0, 1):
        if found[i] is not None and scores[i] is not None:
            part, other = (p, s) if i == 0 else (s, p)
            grown = _rim(look, part, other, src[i], diffs_of[i], p | s, strict)
            if i == 0:
                p = grown
            else:
                s = grown
    s = s & ~p

    ed = edits or {}
    ep = _as_mask(ed.get("p"), im.size)
    es = _as_mask(ed.get("s"), im.size)
    ek = _as_mask(ed.get("keep"), im.size)
    if ep is not None:
        p = p | ep
        s = s & ~ep
    if es is not None:
        s = s | es
        p = p & ~es
    if ek is not None:
        p = p & ~ek
        s = s & ~ek
    if not tgt[0]:
        p = none
    if not tgt[1]:
        s = none

    out = rgba[..., :3].copy()
    _paint(out, look, p, src[0], tgt[0])
    _paint(out, look, s, src[1], tgt[1])
    share = float(p.sum() + s.sum()) / float(wid * hgt) if wid * hgt else 0.0
    if alpha_out:
        res = Image.fromarray(np.dstack([out, rgba[..., 3]]), "RGBA")
    else:
        res = Image.fromarray(out, "RGB")
    return res, min(share, 1.0)


# ---------------------------------------------------------------------------
# a faction's colours and pictures


def faction_colours(mod) -> Dict[str, tuple]:
    """``{slot: (primary, secondary)}`` from the mod's own ``descr_sm_factions.txt``."""
    try:
        rf = factions.parse_file(factions.path_for(mod))
    except OSError:
        return {}
    out = {}
    for rec in rf.records:
        out[factions.slot_of(rec.name)] = (
            factions.parse_colour(rec.get("primary_colour")),
            factions.parse_colour(rec.get("secondary_colour")))
    return out


def _norm_path(p: str) -> str:
    p = (p or "").replace("\\", "/")
    if p.lower().startswith("data/"):
        p = p[5:]
    return p


def _pictures_in(mod, folder: str, slot: str, kind: str, cols) -> List[dict]:
    d = Path(mod.data) / folder / slot
    if not d.is_dir():
        return []
    parent = d.parent
    sibs = sorted((x.name for x in parent.iterdir() if x.is_dir()), key=str)
    rows = []
    for f in sorted((x for x in d.iterdir() if x.is_file() and x.suffix.lower() in _PICTURE_SUFFIXES),
                    key=lambda x: x.name.lower()):
        others = []
        for sib in sibs:
            if len(others) >= OTHERS_MAX:
                break
            if sib.lower() == slot.lower() or sib.lower() not in cols:
                continue
            if (parent / sib / f.name).is_file():
                others.append((f"{folder}/{sib}/{f.name}", sib))
        rows.append({"rel": f"{folder}/{slot}/{f.name}", "kind": kind,
                     "others": others, "shared": [], "entries": []})
    return rows


def _texture_rows(mod, slot: str, cols) -> List[dict]:
    try:
        entries = list(mod.modeldb.entries)
    except Exception:
        return []
    low = slot.lower()
    found: Dict[str, dict] = {}
    for e in entries:
        recs = [t for t in e.main_textures if t.texture]
        for mine in recs:
            if mine.faction.lower() != low:
                continue
            path = _norm_path(mine.texture)
            row = found.get(path.lower())
            if row is None:
                row = found[path.lower()] = {"rel": path, "kind": "texture", "others": [],
                                             "shared": [], "entries": []}
            if e.name not in row["entries"]:
                row["entries"].append(e.name)
            for t in recs:
                f = t.faction.lower()
                if f == low:
                    continue
                p = _norm_path(t.texture)
                if p.lower() == path.lower():
                    if f not in row["shared"]:
                        row["shared"].append(f)
                elif (len(row["others"]) < OTHERS_MAX and f in cols
                      and f not in [o[1] for o in row["others"]]):
                    row["others"].append((p, f))
    return list(found.values())


def targets(mod, slot: str) -> List[dict]:
    """Every picture of the faction, cards first, then info, textures, symbols."""
    cols = faction_colours(mod)
    rows = _pictures_in(mod, "ui/units", slot, "card", cols)
    rows += _pictures_in(mod, "ui/unit_info", slot, "info", cols)
    rows += _texture_rows(mod, slot, cols)
    for rel in (f"ui/faction_symbols/{slot}.tga",
                f"menu/symbols/fe_symbols_80/{slot}.tga",
                f"loading_screen/symbols/symbol128_{slot}.tga"):
        rows.append({"rel": rel, "kind": "symbol", "others": [], "shared": [], "entries": []})
    data = Path(mod.data)
    return [r for r in rows if (data / r["rel"]).is_file()]


# ---------------------------------------------------------------------------
# one picture


def _read(path):
    from .bannermaker import read_picture
    return read_picture(path)


def _one(mod, row, source, target, cols, clicks=None):
    data = Path(mod.data)
    im = _read(data / row["rel"])
    others = []
    for rel, name in row.get("others") or ():
        try:
            pic = _read(data / rel)
        except Exception:
            continue
        others.append((pic, cols.get(name) or cols.get(str(name).lower())))
    edits = touch_edits(im, clicks)
    return recolour(im, source, target, others, edits, plain=(row["kind"] != "symbol"), kind=row["kind"])


def _data_uri(im) -> str:
    t = im.convert("RGBA")
    t.thumbnail((128, 128))
    buf = io.BytesIO()
    t.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# the request


def _one_colour(c):
    if c is None or c == "":
        return None
    text = str(c).strip().lstrip("#")
    if not text:
        return None
    if not re.fullmatch(r"[0-9a-fA-F]{6}", text):
        raise RecolourError(_i18n.msg("eng.artrecolour.bad_colour",
                                      "{c} is not a colour like #c81e1e", c=text))
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def _colours(spec, cols):
    if isinstance(spec, str) and spec in cols:
        return tuple(cols[spec])
    if isinstance(spec, (list, tuple)):
        pair = [_one_colour(c) for c in list(spec)[:2]]
        return tuple(pair + [None] * (2 - len(pair)))
    raise RecolourError(_i18n.msg("eng.artrecolour.no_colours",
                                  "say which colours the pictures are in now and which they should take"))


def _both(body, cols):
    return _colours(body.get("source"), cols), _colours(body.get("target"), cols)


def _touch(body) -> dict:
    t = body.get("touch")
    if not isinstance(t, dict) or not all(isinstance(v, list) for v in t.values()):
        return {}
    return {str(k).lower(): v for k, v in t.items()}


def _slot(body) -> str:
    return str(body.get("faction") or "").strip()


def sample(mod, body) -> dict:
    slot = _slot(body)
    rel = str(body.get("rel") or "")
    cols = faction_colours(mod)
    row = next((r for r in targets(mod, slot) if r["rel"].lower() == rel.lower()), None)
    if row is None:
        raise RecolourError(_i18n.msg("eng.artrecolour.not_its_picture",
                                      "{rel} is not one of {faction}'s pictures",
                                      rel=rel, faction=slot))
    source, target = _both(body, cols)
    new, share = _one(mod, row, source, target, cols, _touch(body).get(rel.lower()))
    return {"rel": row["rel"], "share": round(share, 3), "new": _data_uri(new)}


def _free_bytes(path) -> int:
    try:
        return int(shutil.disk_usage(path).free)
    except OSError:
        return 0


def _size_of(mod, rows) -> int:
    total = 0
    for r in rows:
        if r["shared"]:
            try:
                total += (Path(mod.data) / r["rel"]).stat().st_size
            except OSError:
                pass
    return total


def plan(mod, body) -> dict:
    slot = _slot(body)
    rows = targets(mod, slot)
    if not rows:
        raise RecolourError(_i18n.msg("eng.artrecolour.nothing",
                                      "{faction} has no pictures of its own in this mod to recolour",
                                      faction=slot))
    cols = faction_colours(mod)
    source, target = _both(body, cols)
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    chosen = ([r for r in rows if r["kind"] == "card"][:3]
              + [r for r in rows if r["kind"] == "texture"][:2]
              + [r for r in rows if r["kind"] == "symbol"][:1])
    samples = []
    for r in chosen:
        try:
            old = _read(Path(mod.data) / r["rel"])
            new, share = _one(mod, r, source, target, cols)
            samples.append({"rel": r["rel"], "kind": r["kind"], "share": round(share, 3),
                            "old": _data_uri(old), "new": _data_uri(new)})
        except Exception as e:
            samples.append({"rel": r["rel"], "error": str(e)})
    pair = lambda p: [list(c) if c else None for c in p]
    return {"faction": slot, "counts": counts, "samples": samples,
            "shared": sum(1 for r in rows if r["shared"]),
            "new_bytes": _size_of(mod, rows),
            "free_bytes": _free_bytes(mod.data),
            "source": pair(source), "target": pair(target)}


# ---------------------------------------------------------------------------
# writing


def _picture_bytes(im, suffix: str, tmp: Path) -> None:
    """Write ``im`` to ``tmp`` in the format the file's suffix names."""
    s = suffix.lower()
    rgba = im.convert("RGBA")
    if s in (".texture", ".dds"):
        from . import armbake, sprites
        dds = armbake.dds_with_mipmaps(rgba)
        tmp.write_bytes(sprites.dds_to_texture(dds) if s == ".texture" else dds)
    elif s == ".png":
        rgba.save(tmp, "PNG")
    else:
        rgba.save(tmp, "TGA")


def _repointed_text(mod, slot: str, moved: Dict[str, str]) -> Optional[str]:
    """The modeldb as text with ``slot``'s texture records in ``moved`` (path key -> new
    path) pointed at their new files, or None when no record changed."""
    db = mod.modeldb
    low = slot.lower()
    saved = [(e, e.raw) for e in db.entries]
    changed = 0
    try:
        for e in db.entries:
            pad = e.first_entry_pad
            idx = {}
            for sl in modeldb.path_slots_raw(e.raw, pad=pad):
                if (sl["kind"] == "texture" and sl["group"] == "main"
                        and sl["faction"].lower() == low
                        and modeldb.path_key(sl["value"]) in moved):
                    idx[sl["i"]] = moved[modeldb.path_key(sl["value"])]
            if idx:
                e.raw = modeldb.rewrite_paths_indexed(e.raw, idx, pad=pad)
                changed += len(idx)
        text = db.to_text() if changed else None
    finally:
        for e, raw in saved:
            e.raw = raw
    return text if changed else None


def apply(mod, body) -> dict:
    slot = _slot(body)
    cols = faction_colours(mod)
    source, target = _both(body, cols)
    rows = targets(mod, slot)
    data = Path(mod.data)

    new_bytes = _size_of(mod, rows)
    free = _free_bytes(data)
    if free and 2 * new_bytes + _SPACE_MARGIN > free:
        raise RecolourError(_i18n.msg(
            "eng.artrecolour.no_space",
            "the faction's own copies of the textures it shares need about {need} MB and the drive has {free} MB free; free some space first",
            need="%.0f" % (new_bytes / 1e6), free="%.0f" % (free / 1e6)))

    touch = _touch(body)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    n_written = n_own = n_skipped = 0
    moved: Dict[str, str] = {}

    def backup(rel: str) -> None:
        if rel in manifest["backed_up"] or rel in manifest["created"]:
            return
        path = data / rel
        if path.is_file():
            dest = backup_root / "data" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", path, f"-> {dest}")
        else:
            manifest["created"].append(rel)

    try:
        for row in rows:
            try:
                new, share = _one(mod, row, source, target, cols, touch.get(row["rel"].lower()))
            except Exception:
                n_skipped += 1
                continue
            if share <= 0:
                continue
            rel = row["rel"]
            pp = PurePosixPath(rel)
            if row["shared"]:
                out_rel = str(pp.with_name(f"{pp.stem}_{slot}{pp.suffix}"))
            else:
                out_rel = rel
            backup(out_rel)
            out = data / out_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + ".new")
            _picture_bytes(new, pp.suffix, tmp)
            os.replace(tmp, out)
            file_op("WRITE", out, "recoloured")
            n_written += 1
            if row["shared"]:
                n_own += 1
                moved[modeldb.path_key(rel)] = out_rel

        if moved:
            text = _repointed_text(mod, slot, moved)
            if text is not None:
                db_rel, text, enc = modeltext.redirect(mod, _MODELDB_REL, text, modeldb.ENCODING)
                backup(db_rel)
                target_path = data / db_rel
                target_path.write_text(text, encoding=enc)
                file_op("WRITE", target_path, f"{len(moved)} texture(s) of {slot} pointed at its own copies")
    except BaseException:
        from . import transfer
        transfer._put_back(data, backup_root, manifest)
        mod.__dict__.pop("modeldb", None)
        raise

    mod.__dict__.pop("modeldb", None)
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "factions", "action": "recolour",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": slot, "resolved_type": slot,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": _i18n.msg("eng.artrecolour.summary",
                             "{faction}'s pictures recoloured: {n} changed, {own} made its own",
                             faction=slot, n=n_written, own=n_own),
        "warnings": [], "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("RECOLOUR %s in %s: %d changed, %d own copies, %d skipped, id=%s",
             slot, mod.name, n_written, n_own, n_skipped, tid)
    return dict(rec, changed=n_written, own=n_own, skipped=n_skipped)
