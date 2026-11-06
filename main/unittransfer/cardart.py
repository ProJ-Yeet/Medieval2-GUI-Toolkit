"""The game's own interface pieces for the card maker, and a mod's card sizes.

The card maker (Armory > Unit cards > Generate) lays its cards on the art the
game itself uses: card backgrounds, the scroll, the portrait frame. This module
finds such a piece in the interface sheets (ui/*.sd.xml), cuts it from its page
picture, and hands it out as a PNG. It also reads the picture size a mod's unit
cards and info pictures use, from the TGA headers alone.

Written independently from a description of the behaviour (2026-11-06); the idea of laying cards on the game's own art follows Pfadfinder-Adam's campaign editor.
"""
import io
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import gamepack

SHEETS = ("shared.sd.xml", "battle.sd.xml", "strategy.sd.xml",
          "shared2.sd.xml", "battle3.sd.xml", "strat3.sd.xml")
NAMES = ("STRAT_CARD_BACKGROUND", "BATTLE_CARD_BACKGROUND", "SCROLL_MID",
         "PORTRAIT_FRAME", "PORTRAIT_FRAME_INT")
CULTURES = ("northern_european", "southern_european", "eastern_european",
            "middle_eastern", "greek", "mesoamerican")

_PAGE_TAG = re.compile(r'<page\s+file\s*=\s*"([^"]*)"', re.I)
_SPRITE = re.compile(
    r'<sprite\s+name\s*=\s*"([^"]*)"\s+x\s*=\s*"(-?\d+)"\s+y\s*=\s*"(-?\d+)"'
    r'\s+w\s*=\s*"(\d+)"\s+h\s*=\s*"(\d+)"', re.I)


def _sheet_text(mod, sheet: str) -> str:
    try:
        path, _where = gamepack.lookup("ui/" + sheet, mod)
        if path is None:
            return ""
        return Path(path).read_text(encoding="latin-1")
    except Exception:
        return ""


def find_sprite(mod, name: str) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
    """(page file, (x, y, w, h)) of a named sprite, or None."""
    if not name:
        return None
    want = name.lower()
    for sheet in SHEETS:
        page = None
        for line in _sheet_text(mod, sheet).splitlines():
            m = _PAGE_TAG.search(line)
            if m:
                page = m.group(1)
                continue
            s = _SPRITE.search(line)
            if s and page is not None and s.group(1).lower() == want:
                x, y, w, h = (int(s.group(i)) for i in range(2, 6))
                return page, (x, y, w, h)
    return None


def _cultures(mod, culture: str) -> List[str]:
    out: List[str] = []

    def add(c):
        if c and c not in out:
            out.append(c)

    add(culture)
    ui = Path(mod.data) / "ui" if mod is not None else None
    if ui is not None and ui.is_dir():
        try:
            for d in sorted(ui.iterdir()):
                if d.is_dir() and (d / "interface").is_dir():
                    add(d.name)
        except OSError:
            pass
    for c in CULTURES:
        add(c)
    return out


def game_sprite(mod, name: str, culture: str = ""):
    """The named piece as an RGBA image cut from its page, or None."""
    if not name or name.upper() not in NAMES:
        return None
    found = find_sprite(mod, name)
    if found is None:
        return None
    page, (x, y, w, h) = found
    try:
        from PIL import Image
        from .icons import _decode_to_png
    except Exception:
        return None
    for cul in _cultures(mod, culture):
        try:
            path, _where = gamepack.lookup(f"ui/{cul}/interface/{page}", mod)
            if path is None:
                continue
            png = _decode_to_png(Path(path), 0)
            if not png:
                continue
            with Image.open(io.BytesIO(png)) as im:
                return im.convert("RGBA").crop((x, y, x + w, y + h))
        except Exception:
            continue
    return None


def png_bytes(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _tga_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with open(path, "rb") as f:
            head = f.read(18)
    except OSError:
        return None
    if len(head) < 18:
        return None
    w = head[12] | head[13] << 8
    h = head[14] | head[15] << 8
    if not (1 <= w <= 4096 and 1 <= h <= 4096):
        return None
    return w, h


def _common_size(folder: Path, pattern: str, cap: int) -> Optional[List[int]]:
    if not folder.is_dir():
        return None
    counts: Counter = Counter()   # insertion order keeps first seen on ties
    seen = 0
    try:
        factions = sorted(d for d in folder.iterdir() if d.is_dir())
    except OSError:
        return None
    for fac in factions:
        try:
            files = sorted(fac.glob(pattern))
        except OSError:
            continue
        for f in files:
            if seen >= cap:
                break
            seen += 1
            size = _tga_dimensions(f)
            if size is not None:
                counts[size] += 1
        if seen >= cap:
            break
    if not counts:
        return None
    best = max(counts.values())
    for size, n in counts.items():
        if n == best:
            return [size[0], size[1]]
    return None


def mod_sizes(mod, cap: int = 400) -> Dict[str, Optional[List[int]]]:
    """The commonest card and info picture size in the mod's own data."""
    data = Path(mod.data)
    return {"card": _common_size(data / "ui" / "units", "#*.tga", cap),
            "info": _common_size(data / "ui" / "unit_info", "*.tga", cap)}
