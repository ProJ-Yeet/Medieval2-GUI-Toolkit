"""A faction's whole emblem set from one picture (96e6).

Taken from the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW / M2TW
Campaign Editor's ``emblem.py``, with its author's permission, and fitted to
Medieval II's own files and this toolkit's plan / apply.

The game shows a faction's emblem in many places and sizes: the campaign
menus' buttons (24 and 48 px, each normal, mouse over, selected and greyed
out), the faction-select screen's 80 px symbol, the in-game panels' symbol and
the loading screen's logo. One picture makes every one of them, each at the
size the mod (or the base game) already uses, fitted into the place the old
emblem took so a button's margin and a selected button's glow stay free. The
states are made the way the mod's own are: mouse over brighter, selected
brighter with the old picture's glow redrawn round the new shape, greyed out
grey and darker - by how much is measured from the faction's old pictures, so
a mod with another look keeps it.

Nothing is written by :func:`plan`; :func:`apply` writes TGA files with a
backup and a log record, so the Log's Undo takes it back. The faction's
``logo_index`` sprite (a sheet the game packs) is a separate job.
"""
from __future__ import annotations

import base64
import io
import shutil
import statistics
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, gamepack
from . import i18n as _i18n
from .logutil import file_op, log

#: (kind, template, the size the game uses when neither the mod nor the game has one)
TARGETS: Tuple[Tuple[str, str, Tuple[int, int]], ...] = (
    ("button24", "menu/symbols/fe_buttons_24/symbol24_{f}{v}.tga", (24, 24)),
    ("button48", "menu/symbols/fe_buttons_48/symbol48_{f}{v}.tga", (48, 48)),
    ("select80", "menu/symbols/fe_symbols_80/{f}.tga", (80, 80)),
    ("panels", "ui/faction_symbols/{f}.tga", (64, 64)),
    ("panels_small", "ui/faction_symbols_small/{f}.tga", (32, 32)),
    ("loading128", "loading_screen/symbols/symbol128_{f}.tga", (128, 128)),
    ("loading64", "loading_screen/symbols/symbol64_{f}.tga", (64, 64)),
)
#: the button states and their file suffixes; only the buttons have them
STATES = (("", None), ("_roll", "roll"), ("_select", "select"), ("_grey", "grey"))
DEFAULT = {"roll": 1.4, "grey": 0.75}
#: kinds the game needs even when neither the mod nor the game has them
ALWAYS = {"button24", "button48", "loading128"}


class EmblemError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _open(path: Path):
    from PIL import Image
    try:
        return Image.open(path).convert("RGBA")
    except (OSError, ValueError):
        return None


def targets(mod, slot: str) -> List[Dict]:
    """Every emblem picture of ``slot``: ``{rel, kind, state, size, where}``,
    ``where`` saying whether the mod has it, the game has it, or it is new."""
    out = []
    for kind, tmpl, size in TARGETS:
        states = STATES if kind.startswith("button") else (("", None),)
        for suffix, state in states:
            rel = tmpl.format(f=slot, v=suffix)
            path, where = gamepack.lookup(rel, mod)
            if not path and kind not in ALWAYS:
                continue
            old = _open(path) if path else None
            out.append({"rel": rel, "kind": kind, "state": state,
                        "size": list(old.size if old else size),
                        "where": where or "new", "path": str(path) if path else ""})
    return out


def measure(normal, other, variant: str) -> Optional[float]:
    """How much brighter (roll / select) or grey-dark (grey) ``other`` is than
    ``normal``, the median over the pixels both cover; None when it cannot be told."""
    if normal is None or other is None or normal.size != other.size:
        return None
    vals = []
    for p, q in zip(normal.getdata(), other.getdata()):
        if p[3] > 200 and q[3] > 200:
            if variant == "grey":
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if lum > 20:
                    vals.append(q[0] / lum)
            elif sum(p[:3]) > 60:
                vals.append(sum(q[:3]) / float(sum(p[:3])))
    return statistics.median(vals) if len(vals) > 20 else None


def footprint(old) -> Optional[Tuple[int, int, int, int]]:
    """Where the old picture's emblem lies (its solid part): (x, y, w, h)."""
    if old is None:
        return None
    box = old.split()[3].point(lambda a: 255 if a >= 40 else 0).getbbox()
    return (box[0], box[1], box[2] - box[0], box[3] - box[1]) if box else None


def fit(src, size, box=None):
    """``src`` at ``size``, its shape kept, fitted into ``box`` (the old
    emblem's place) or the whole picture, centred on a clear ground."""
    from PIL import Image
    im = src.convert("RGBA")
    solid = footprint(im)
    if solid:
        x, y, w, h = solid
        im = im.crop((x, y, x + w, y + h))
    bx, by, bw, bh = box or (0, 0, size[0], size[1])
    k = min(bw / im.size[0], bh / im.size[1])
    new = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    out = Image.new("RGBA", tuple(size), (0, 0, 0, 0))
    out.paste(new, (bx + (bw - new.size[0]) // 2, by + (bh - new.size[1]) // 2))
    return out


def _bright(im, k):
    from PIL import Image
    r, g, b, a = im.split()
    r, g, b = (c.point(lambda x: min(255, int(x * k + 0.5))) for c in (r, g, b))
    return Image.merge("RGBA", (r, g, b, a))


def _grey(im, k):
    from PIL import Image
    r, g, b, a = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L").point(lambda x: min(255, int(x * k + 0.5)))
    return Image.merge("RGBA", (lum, lum, lum, a))


def _glow(old_normal, old_select, new):
    """A selected button's glow round the NEW shape: its colour, strength and
    width taken from the old selected picture where the old normal one is clear."""
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    if old_normal is None or old_select is None or old_normal.size != old_select.size:
        return None
    clear = old_normal.split()[3].point(lambda a: 255 if a < 40 else 0)
    halo = ImageChops.multiply(old_select.split()[3], clear)
    if not halo.getbbox():
        return None
    st = ImageStat.Stat(old_select.convert("RGB"), halo.point(lambda a: 255 if a > 30 else 0))
    colour = tuple(int(c) for c in st.mean)
    strength = max(halo.getextrema()[1], 1)
    width = max(1, int(round(halo.point(lambda a: 255 if a > 30 else 0).histogram()[255] /
                             max(1.0, 2.0 * (old_normal.size[0] + old_normal.size[1])))))
    shape = new.split()[3].point(lambda a: 255 if a >= 40 else 0)
    grown = shape.filter(ImageFilter.MaxFilter(2 * width + 1)).filter(ImageFilter.GaussianBlur(width * 0.7))
    glow = Image.new("RGBA", new.size, colour + (0,))
    glow.putalpha(grown.point(lambda a: a * strength // 255))
    return glow


def build(src, tgts: List[Dict]) -> Dict[str, object]:
    """``{rel: new picture}`` for every target, from one source picture."""
    from PIL import Image
    olds = {t["rel"]: (_open(Path(t["path"])) if t["path"] else None) for t in tgts}
    normal_of = {(t["kind"]): t for t in tgts if t["state"] is None}
    out = {}
    for t in tgts:
        size = tuple(t["size"])
        n0 = normal_of.get(t["kind"])
        ref = olds.get(n0["rel"]) if n0 else olds.get(t["rel"])
        box = footprint(ref) if ref is not None and ref.size == size else None
        base = fit(src, size, box)
        v = t["state"]
        if v is None:
            out[t["rel"]] = base
            continue
        old_n = olds.get(n0["rel"]) if n0 else None
        old_v = olds.get(t["rel"])
        if v == "grey":
            out[t["rel"]] = _grey(base, measure(old_n, old_v, "grey") or DEFAULT["grey"])
            continue
        lit = _bright(base, measure(old_n, old_v, "roll") or DEFAULT["roll"])
        if v == "select":
            glow = _glow(old_n, old_v, lit)
            if glow is not None:
                under = Image.new("RGBA", size, (0, 0, 0, 0))
                under.alpha_composite(glow)
                under.alpha_composite(lit)
                lit = under
        out[t["rel"]] = lit
    return out


def _png(im) -> str:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _source(raw: bytes):
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except (OSError, ValueError, SyntaxError):
        raise EmblemError(_i18n.msg("eng.emblem.not_a_picture", "that file is not a picture this can read (PNG, JPG, TGA, BMP)")) from None
    im = im.convert("RGBA")
    if footprint(im) is None:
        raise EmblemError(_i18n.msg("eng.emblem.empty", "the picture is fully transparent, so there is no emblem in it"))
    return im


def plan(mod, slot: str, raw: bytes) -> Dict:
    """What a new emblem would write, with a preview of each picture and of the
    old one beside it. Writes nothing."""
    slot = (slot or "").strip().lower()
    if not slot:
        raise EmblemError(_i18n.msg("eng.emblem.no_faction", "pick a faction"))
    src = _source(raw)
    tgts = targets(mod, slot)
    made = build(src, tgts)
    rows = []
    for t in tgts:
        old = _open(Path(t["path"])) if t["path"] else None
        rows.append({"rel": t["rel"], "kind": t["kind"], "state": t["state"] or "",
                     "size": t["size"], "where": t["where"],
                     "old": _png(old) if old is not None else "", "new": _png(made[t["rel"]])})
    return {"faction": slot, "rows": rows}


def apply(mod, slot: str, raw: bytes, only: Optional[List[str]] = None) -> Dict:
    """Write the emblem set as TGA files, each backed up first."""
    slot = (slot or "").strip().lower()
    src = _source(raw)
    tgts = [t for t in targets(mod, slot) if not only or t["rel"] in only]
    if not tgts:
        raise EmblemError(_i18n.msg("eng.emblem.nothing", "nothing picked to write"))
    made = build(src, tgts)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    data = Path(mod.data)
    for t in tgts:
        target = data / t["rel"]
        if target.exists():
            b = backup_root / "data" / t["rel"]
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, b)
            manifest["backed_up"].append(t["rel"])
            file_op("BACKUP", target, f"-> {b}")
        else:
            manifest["created"].append(t["rel"])
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".new")
        made[t["rel"]].save(tmp, "TGA")
        tmp.replace(target)
        file_op("WRITE", target, "emblem")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "factions",
           "action": "emblem", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": slot, "resolved_type": slot,
           "options": {}, "applied": True, "undone": False, "note": "",
           "summary": _i18n.msg("eng.emblem.summary", "a new emblem for {faction}: {n} pictures", faction=slot, n=len(tgts)),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("EMBLEM %s in %s, %d pictures, id=%s", slot, mod.name, len(tgts), tid)
    return rec
