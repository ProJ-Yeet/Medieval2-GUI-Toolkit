"""The game's own pieces for the card maker, and the sizes a mod's cards are.

Taken, with the author's leave, from Pfadfinder-Adam's RTW-M2TW-Campaign-Editor
(``campaign_editor/cardmaker.py``: ``game_sprite``, ``paper``, ``framed``, the
picture sizes): the card maker in Unit cards > Generate lays a card on the
game's own card ground, an info picture on the game's scroll paper inside the
game's portrait frame, and makes them at the size the mod's own pictures are.

* :func:`game_sprite` - a named sprite (``STRAT_CARD_BACKGROUND``,
  ``BATTLE_CARD_BACKGROUND``, ``SCROLL_MID``, ``PORTRAIT_FRAME``,
  ``PORTRAIT_FRAME_INT``) cut from its page. The interface sheets are
  ``data/ui/*.sd.xml``: a ``<page file="...">`` and its ``<sprite name x y w
  h>`` boxes, the page a picture in ``ui/<culture>/interface/``. Looked up the
  way the game finds a file (:func:`gamepack.lookup`: the mod, the game's
  loose data, its packs), the culture's own page first, else any culture's.
* :func:`mod_sizes` - the size most of the mod's unit cards and unit info
  pictures are, read off the files' headers.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from . import gamepack

#: the interface sheets, in the order the game's pieces are looked for
SHEETS = ("shared.sd.xml", "battle.sd.xml", "strategy.sd.xml", "shared2.sd.xml",
          "battle3.sd.xml", "strat3.sd.xml")
#: what the card maker may ask for, and nothing else
NAMES = ("STRAT_CARD_BACKGROUND", "BATTLE_CARD_BACKGROUND", "SCROLL_MID",
         "PORTRAIT_FRAME", "PORTRAIT_FRAME_INT")
#: every culture folder Medieval II ships, tried when the asked one has no page
CULTURES = ("northern_european", "southern_european", "eastern_european",
            "middle_eastern", "greek", "mesoamerican")

_PAGE = re.compile(r'<page\s+file="([^"]+)"', re.I)
_SPRITE = re.compile(r'<sprite\s+name="([^"]+)"\s+x="(\d+)"\s+y="(\d+)"\s+w="(\d+)"\s+h="(\d+)"', re.I)


def _read(rel: str, mod) -> Optional[bytes]:
    path, _where = gamepack.lookup(rel, mod)
    if path is None:
        return None
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def _culture_dirs(mod) -> List[str]:
    """The culture folders under the mod's ``data/ui``, then the game's own."""
    out: List[str] = []
    ui = Path(mod.data) / "ui" if mod is not None else None
    if ui is not None and ui.is_dir():
        out += sorted(d.name for d in ui.iterdir() if d.is_dir() and (d / "interface").is_dir())
    return out + [c for c in CULTURES if c not in out]


def find_sprite(mod, name: str) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
    """``(page file, (x, y, w, h))`` of a sprite, from the first sheet that names it."""
    want = (name or "").upper()
    for sheet in SHEETS:
        raw = _read("ui/" + sheet, mod)
        if not raw:
            continue
        page = None
        for line in raw.decode("latin-1").splitlines():
            m = _PAGE.search(line)
            if m:
                page = m.group(1)
            m = _SPRITE.search(line)
            if m and page and m.group(1).upper() == want:
                return page, tuple(int(v) for v in m.groups()[1:])
    return None


def game_sprite(mod, name: str, culture: str = "") -> Optional[Image.Image]:
    """A piece of the game's own interface as an RGBA picture, or None."""
    if (name or "").upper() not in NAMES:
        return None
    hit = find_sprite(mod, name)
    if hit is None:
        return None
    page, (x, y, w, h) = hit
    tries = ([culture] if culture else []) + [c for c in _culture_dirs(mod) if c != culture]
    from . import icons
    for c in tries:
        path, _where = gamepack.lookup(f"ui/{c}/interface/{page}", mod)
        if path is None:
            continue
        # the toolkit's own reader: TGA (run-length too), DDS, PNG
        data = icons._decode_to_png(Path(path), 0)
        if data is None:
            continue
        try:
            im = Image.open(io.BytesIO(data)).convert("RGBA")
        except (OSError, ValueError):
            continue
        return im.crop((x, y, x + w, y + h))
    return None


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _tga_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with open(path, "rb") as f:
            head = f.read(18)
    except OSError:
        return None
    if len(head) < 18:
        return None
    w, h = int.from_bytes(head[12:14], "little"), int.from_bytes(head[14:16], "little")
    return (w, h) if 0 < w <= 4096 and 0 < h <= 4096 else None


def mod_sizes(mod, cap: int = 400) -> Dict[str, Optional[List[int]]]:
    """``{"card": [w, h], "info": [w, h]}``: the size most of the mod's own
    unit cards (``ui/units/<faction>/#*.tga``) and unit info pictures
    (``ui/unit_info/<faction>/*.tga``) are. None for a kind the mod has none of
    (the game's own are then used). At most ``cap`` files of each are read."""
    out: Dict[str, Optional[List[int]]] = {}
    data = Path(mod.data)
    for kind, rel, pat in (("card", "ui/units", "#*.tga"), ("info", "ui/unit_info", "*.tga")):
        seen: Counter = Counter()
        base = data / rel
        n = 0
        if base.is_dir():
            for fac in sorted(base.iterdir()):
                if not fac.is_dir():
                    continue
                for f in fac.glob(pat):
                    s = _tga_size(f)
                    if s:
                        seen[s] += 1
                    n += 1
                    if n >= cap:
                        break
                if n >= cap:
                    break
        out[kind] = list(seen.most_common(1)[0][0]) if seen else None
    return out
