"""Every picture in a mod, by kind (96f, the art browser).

The toolkit shows pictures where they are used - a unit's card in the unit
editor, a building's in the building browser, a pip in the religions form -
and :mod:`unittransfer.images` replaces any of them from a right click. What
was missing is the other way in: *what pictures does this mod have?* This
module walks the mod's ``data/`` once and sorts every ``.tga`` / ``.dds`` by
the folder the game reads it from, so the page can show them kind by kind,
each one replaceable through the same right click.

Only the mod's own loose files: a picture the game reads from its packs is not
the mod's to show here (Phase 10a's ruling on packed art).
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

#: (kind, the path under data/ it matches), first match wins. The order is the
#: order the page lists them in.
KINDS: List[Tuple[str, re.Pattern]] = [
    ("unit_cards", re.compile(r"^ui/units/[^/]+/[^/]+$", re.I)),
    ("unit_info", re.compile(r"^ui/unit_info/[^/]+/[^/]+$", re.I)),
    ("buildings", re.compile(r"^ui/[^/]+/buildings/", re.I)),
    ("portraits", re.compile(r"^ui/[^/]+/portraits/", re.I)),
    ("ancillaries", re.compile(r"^ui/ancillaries/", re.I)),
    ("events", re.compile(r"^ui/eventpics/", re.I)),
    ("pips", re.compile(r"^ui/pips/", re.I)),
    ("resources", re.compile(r"^ui/resources/", re.I)),
    ("settlements", re.compile(r"^ui/[^/]+/settlements/", re.I)),
    ("interface_pages", re.compile(r"^ui/[^/]+/interface/", re.I)),
    ("campaign", re.compile(r"^world/maps/campaign/", re.I)),
    ("map", re.compile(r"^world/maps/(base|battle)/", re.I)),
    ("loading", re.compile(r"^(loading_screen|ui/loading_screen)/", re.I)),
    ("symbols", re.compile(r"^(menu/symbols|banners)/", re.I)),
    ("menu", re.compile(r"^menu/", re.I)),
    ("interface", re.compile(r"^ui/", re.I)),
]
OTHER = "other"
EXTS = {".tga", ".dds"}
#: top folders of data/ that hold no picture a player sees on a screen, or far
#: too many to list: the models' textures have the Models editor, the ground's
#: the map
SKIP_TOP = {"unit_models", "models_strat", "models_building", "models_wonders", "animations", "terrain",
            "sounds", "text", "prefab", "sprites", "vegetation", "fmv", "battlefield", "settlements",
            "unit_sprites", "models", "banners_textures"}

_CACHE: Dict[str, Tuple[float, Dict[str, List[Tuple[str, int]]]]] = {}
CACHE_SECONDS = 300.0


def kind_of(rel: str) -> str:
    for kind, rx in KINDS:
        if rx.search(rel):
            return kind
    return OTHER


def _walk(mod) -> Dict[str, List[Tuple[str, int]]]:
    """``{kind: [(rel, bytes), ...]}``, sorted, read again at most every
    :data:`CACHE_SECONDS`."""
    data = Path(mod.data)
    key = str(data).lower()
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    out: Dict[str, List[Tuple[str, int]]] = {}
    if data.is_dir():
        import os
        for here, dirs, names in os.walk(data):
            if Path(here) == data:
                # pruned before they are walked: the models' folders are most
                # of a mod's files, and their textures have the Models editor
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_TOP]
            base = Path(here).relative_to(data).as_posix()
            for n in names:
                if os.path.splitext(n)[1].lower() not in EXTS:
                    continue
                rel = n if base == "." else f"{base}/{n}"
                try:
                    size = os.path.getsize(os.path.join(here, n))
                except OSError:
                    continue
                out.setdefault(kind_of(rel), []).append((rel, size))
    for rows in out.values():
        rows.sort(key=lambda r: r[0].lower())
    _CACHE[key] = (time.monotonic(), out)
    return out


def forget(mod) -> None:
    """Read the folder again on the next ask (Refresh)."""
    _CACHE.pop(str(Path(mod.data)).lower(), None)


def overview(mod) -> Dict:
    """Each kind the mod has a picture of, and how many."""
    found = _walk(mod)
    order = [k for k, _ in KINDS] + [OTHER]
    return {"mod": mod.name,
            "kinds": [{"kind": k, "count": len(found[k])} for k in order if found.get(k)],
            "total": sum(len(v) for v in found.values())}


def files(mod, kind: str, q: str = "", offset: int = 0, limit: int = 120) -> Dict:
    """One kind's pictures, filtered by ``q`` in the path, a page at a time."""
    rows = _walk(mod).get(kind, [])
    words = [w for w in (q or "").lower().split() if w]
    if words:
        rows = [r for r in rows if all(w in r[0].lower() for w in words)]
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or 120), 500))
    return {"kind": kind, "count": len(rows),
            "files": [{"rel": r, "bytes": b} for r, b in rows[offset:offset + limit]],
            "offset": offset}
