"""The game's own interface pieces for the card maker, and a mod's card sizes.

The card maker (Armory > Unit cards > Generate) lays its cards on the art the
game itself uses: card backgrounds, the scroll, the portrait frame. This module
finds such a piece in the interface sheets (ui/*.sd), cuts it from its page
picture, and hands it out as a PNG. It also reads the picture size a mod's unit
cards and info pictures use, from the TGA headers alone.
"""
import io
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import gamepack, spritesheet

#: the interface sprite sheets, read in their binary form (the game ships the
#: .sd in every install, inside its packs; the .sd.xml is only a modder's copy)
SHEETS = ("ui/shared.sd", "ui/strategy.sd", "ui/battle.sd")
NAMES = ("STRAT_CARD_BACKGROUND", "BATTLE_CARD_BACKGROUND", "SCROLL_MID",
         "PORTRAIT_FRAME", "PORTRAIT_FRAME_INT")
CULTURES = ("northern_european", "southern_european", "eastern_european",
            "middle_eastern", "greek", "mesoamerican")


def _sheet(mod, rel: str):
    try:
        path, _where = gamepack.lookup(rel, mod)
        if path is None:
            return None
        return spritesheet.parse(Path(path).read_bytes())
    except Exception:
        return None


def find_sprite(mod, name: str) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
    """(page file, (x, y, w, h)) of a named sprite, or None. A sprite names
    its page by number and its box by left, right, top and bottom."""
    if not name:
        return None
    want = name.lower()
    for rel in SHEETS:
        sheet = _sheet(mod, rel)
        if sheet is None:
            continue
        for sp in sheet.sprites:
            if sp.name.lower() == want and 0 <= sp.page < len(sheet.pages):
                return sheet.pages[sp.page], (sp.left, sp.top, max(1, sp.right - sp.left),
                                              max(1, sp.bottom - sp.top))
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
