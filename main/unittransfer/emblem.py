"""A faction's whole set of emblem pictures from one source picture.

Given one picture, this makes every emblem a faction has: the menu buttons in
their four states, the faction-select symbol, the in-game panel symbols and the
loading-screen logos. Each is made at the size the mod already uses, with the
emblem placed where the old one sat. The mouse-over, selected and greyed states
copy how the mod's own old pictures differ from their normal one. plan() shows
old beside new and writes nothing; apply() writes TGA files, backs up what it
replaces and logs the change so Undo puts every byte back.

Written independently from a description of the behaviour (2026-11-06); the
feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import base64
import io
import os
import shutil
import statistics
import time
from pathlib import Path

from . import config, gamepack, logutil
from . import i18n as _i18n

# (kind, path under data/, default size)
TARGETS = (
    ("button24", "menu/symbols/fe_buttons_24/symbol24_{f}{v}.tga", (24, 24)),
    ("button48", "menu/symbols/fe_buttons_48/symbol48_{f}{v}.tga", (48, 48)),
    ("select80", "menu/symbols/fe_symbols_80/{f}.tga", (80, 80)),
    ("panels", "ui/faction_symbols/{f}.tga", (64, 64)),
    ("panels_small", "ui/faction_symbols_small/{f}.tga", (32, 32)),
    ("loading128", "loading_screen/symbols/symbol128_{f}.tga", (128, 128)),
    ("loading64", "loading_screen/symbols/symbol64_{f}.tga", (64, 64)),
)

# file suffix, state name
STATES = (("", None), ("_roll", "roll"), ("_select", "select"), ("_grey", "grey"))

# brightness factors to fall back on when the old pictures cannot be measured
DEFAULT = {"grey": 0.75, "roll": 1.4}

# kinds made even when no picture of them exists yet
ALWAYS = {"button24", "button48", "loading128"}

_SOLID = 40  # alpha at or above this counts as part of the shape


class EmblemError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _open(path):
    """The picture at path as RGBA, or None when it cannot be read."""
    from PIL import Image
    try:
        with Image.open(path) as im:
            return im.convert("RGBA")
    except Exception:
        return None


def targets(mod, slot):
    """One dict per picture to write, in TARGETS order, buttons by state."""
    out = []
    for kind, tmpl, default in TARGETS:
        states = STATES if kind.startswith("button") else (("", None),)
        for suffix, state in states:
            rel = tmpl.format(f=slot, v=suffix)
            path, where = gamepack.lookup(rel, mod)
            if path:
                im = _open(path)
                size = list(im.size) if im is not None else list(default)
                out.append({"rel": rel, "kind": kind, "state": state, "size": size,
                            "where": where, "path": str(path)})
            elif kind in ALWAYS:
                out.append({"rel": rel, "kind": kind, "state": state, "size": list(default),
                            "where": "new", "path": ""})
    return out


def measure(normal, other, variant):
    """The median brightness ratio of other against normal, or None."""
    if None in (normal, other) or normal.size != other.size:
        return None
    ratios = []
    for a, b in zip(normal.getdata(), other.getdata()):
        if a[3] <= 200 or b[3] <= 200:
            continue
        if variant == "grey":
            lum = 0.299 * a[0] + 0.587 * a[1] + 0.114 * a[2]
            if lum > 20:
                ratios.append(b[0] / lum)
        else:
            base = a[0] + a[1] + a[2]
            if base > 60:
                ratios.append((b[0] + b[1] + b[2]) / base)
    if len(ratios) <= 20:
        return None
    return statistics.median(ratios)


def footprint(old):
    """(x, y, w, h) of the solid part of an RGBA image, or None."""
    if old is None:
        return None
    mask = old.getchannel("A").point(lambda v: 255 if v >= _SOLID else 0)
    box = mask.getbbox()
    if box is None:
        return None
    return (box[0], box[1], box[2] - box[0], box[3] - box[1])


def fit(src, size, box=None):
    """src cropped to its shape, scaled to fill box as far as it fits, centred."""
    from PIL import Image
    w, h = size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fp = footprint(src)
    if fp is None:
        return out
    bx, by, bw, bh = box if box else (0, 0, w, h)
    crop = src.crop((fp[0], fp[1], fp[0] + fp[2], fp[1] + fp[3]))
    k = min(bw / crop.width, bh / crop.height)
    nw = max(1, round(crop.width * k))
    nh = max(1, round(crop.height * k))
    crop = crop.resize((nw, nh), Image.LANCZOS)
    out.paste(crop, (bx + (bw - nw) // 2, by + (bh - nh) // 2))
    return out


def _merge(r, g, b, a):
    from PIL import Image
    return Image.merge("RGBA", [r, g, b, a])


def _brighten(im, k):
    r, g, b, a = im.split()
    lut = [min(255, round(i * k)) for i in range(256)]
    return _merge(r.point(lut), g.point(lut), b.point(lut), a)


def _grey(im, k):
    a = im.getchannel("A")
    lut = [min(255, round(i * k)) for i in range(256)]
    lum = im.convert("L").point(lut)
    return _merge(lum, lum, lum, a)


def _halo(old_normal, old_select):
    """(colour, strength, width) of the glow in the old selected picture."""
    if None in (old_normal, old_select) or old_select.size != old_normal.size:
        return None
    n_alpha = old_normal.getchannel("A").getdata()
    sel = [p for p, na in zip(old_select.getdata(), n_alpha) if na < _SOLID and p[3] > 0]
    if not sel:
        return None
    total = sum(p[3] for p in sel)
    colour = tuple(round(sum(p[i] * p[3] for p in sel) / total) for i in range(3))
    strength = max(p[3] for p in sel)
    w, h = old_normal.size
    width = max(1, round(len(sel) / (2 * (w + h))))
    return colour, strength, width


def _glow(shape, halo):
    """A glow layer round the solid area of shape, from a measured halo."""
    from PIL import Image, ImageFilter
    colour, strength, width = halo
    mask = shape.getchannel("A").point(lambda v: 255 if v >= _SOLID else 0)
    mask = mask.filter(ImageFilter.MaxFilter(2 * width + 1))
    mask = mask.filter(ImageFilter.GaussianBlur(max(0.5, width / 2)))
    mask = mask.point(lambda v: round(v * strength / 255))
    layer = Image.new("RGBA", shape.size, tuple(colour) + (0,))
    layer.putalpha(mask)
    return layer


def build(src, tgts):
    """One new picture per target, at the target's size."""
    from PIL import Image
    olds = {t["rel"]: (_open(t["path"]) if t["path"] else None) for t in tgts}
    normals = {t["kind"]: t for t in tgts if t["state"] is None}
    new_normal = {}
    out = {}

    def normal_for(t):
        kind = t["kind"]
        if kind not in new_normal:
            ref = olds.get(normals.get(kind, t)["rel"])
            size = tuple(t["size"])
            box = None if ref is None or ref.size != size else footprint(ref)
            new_normal[kind] = fit(src, size, box)
        return new_normal[kind]

    for t in tgts:
        base = normal_for(t)
        state = t["state"]
        old_n = olds.get(normals[t["kind"]]["rel"]) if t["kind"] in normals else None
        old_t = olds.get(t["rel"])
        if state is None:
            out[t["rel"]] = base
        elif state == "grey":
            k = measure(old_n, old_t, "grey")
            out[t["rel"]] = _grey(base, DEFAULT["grey"] if k is None else k)
        else:
            k = measure(old_n, old_t, "roll")
            lit = _brighten(base, DEFAULT["roll"] if k is None else k)
            if state == "select":
                halo = _halo(old_n, old_t)
                if halo and old_t.size == base.size:
                    lit = Image.alpha_composite(_glow(base, halo), lit)
            out[t["rel"]] = lit
    return out


def _png_uri(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _source(raw):
    """Decode the uploaded bytes into a usable RGBA picture."""
    from PIL import Image
    try:
        src = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        raise EmblemError(_i18n.msg("eng.emblem.not_a_picture",
                                    "that file is not a picture this can read (PNG, JPG, TGA, BMP)"))
    if footprint(src) is None:
        raise EmblemError(_i18n.msg("eng.emblem.empty",
                                    "the picture is fully transparent, so there is no emblem in it"))
    return src


def _slot(slot):
    slot = (slot or "").strip().lower()
    if not slot:
        raise EmblemError(_i18n.msg("eng.emblem.no_faction", "pick a faction"))
    return slot


def plan(mod, slot, raw):
    """Old beside new for every picture. Writes nothing."""
    slot = _slot(slot)
    src = _source(raw)
    tg = targets(mod, slot)
    made = build(src, tg)
    rows = []
    for t in tg:
        old = _open(t["path"]) if t["path"] else None
        rows.append({"rel": t["rel"], "kind": t["kind"], "state": t["state"] or "",
                     "size": t["size"], "where": t["where"],
                     "old": _png_uri(old) if old is not None else "",
                     "new": _png_uri(made[t["rel"]])})
    return {"faction": slot, "rows": rows}


def apply(mod, slot, raw, only=None):
    """Write the set as TGA files, with backups and a log record for Undo."""
    slot = _slot(slot)
    src = _source(raw)
    tg = targets(mod, slot)
    if only:
        wanted = set(only)
        tg = [t for t in tg if t["rel"] in wanted]
    if not tg:
        raise EmblemError(_i18n.msg("eng.emblem.nothing", "nothing picked to write"))
    made = build(src, tg)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    backed_up, created = [], []
    for t in tg:
        rel = t["rel"]
        dest = Path(mod.data) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            keep = backup_root / "data" / rel
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, keep)
            logutil.file_op("BACKUP", dest, f"-> {keep}")
            backed_up.append(rel)
        else:
            created.append(rel)
        tmp = dest.with_name(dest.name + ".tmp")
        made[rel].save(tmp, "TGA")
        os.replace(tmp, dest)
        logutil.file_op("WRITE", dest, "emblem")
    n = len(tg)
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "factions",
        "action": "emblem",
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
        "summary": _i18n.msg("eng.emblem.summary", "a new emblem for {faction}: {n} pictures",
                             faction=slot, n=n),
        "warnings": [],
        "manifest": {"backed_up": backed_up, "created": created},
        "backup_root": str(backup_root),
    }
    config.append_log(rec)
    logutil.log.info("EMBLEM %s in %s, %d pictures, id=%s", slot, mod.name, n, tid)
    return rec
