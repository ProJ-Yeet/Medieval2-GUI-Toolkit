"""96f: the game's menu pictures, sheet by sheet, page by page (Unit cards > Menu sheets).

Every picture the interface draws - buttons, scrolls, panels, the faction
shields - is a named box on a page of one of the sprite sheets the game reads,
``ui/strategy.sd``, ``ui/shared.sd``, ``ui/battle.sd`` and ``ui/radar.sd``
(:mod:`spritesheet` reads them). The table is one for every culture; the pages
are not: each culture has its own ``ui/<culture>/interface/<page>``. So a page
is shown for one culture at a time, with each sprite's box and name over it.

Where the menus are laid out is not a data file the game reads, so moving a
button is not on offer; its picture is. :func:`replace` paints a picture into
one sprite's box on one culture's page - stretched, kept in shape or filling
the box - in the mod's own copy of that page (made from the game's when the mod
ships none), backed up first and on the Log so Undo takes it back. The page's
click mask in the sheet is left as it was: a button stays clickable where the
old picture was.
"""
from __future__ import annotations

import io
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, spritesheet
from . import i18n as _i18n
from .factions import picture_path, read_path
from .logutil import file_op, log

SHEETS = ("ui/strategy.sd", "ui/shared.sd", "ui/battle.sd", "ui/radar.sd")
FITS = ("stretch", "keep", "fill")


class MenuSheetError(ValueError):
    pass


def _sheet(mod, rel: str) -> spritesheet.Sheet:
    if rel not in SHEETS:
        raise MenuSheetError(_i18n.msg("eng.menusheets.no_sheet", "{rel} is not one of the game's sprite sheets", rel=rel))
    p = read_path(mod, rel)
    if p is None:
        raise MenuSheetError(_i18n.msg("eng.menusheets.sheet_missing", "{rel} is in neither the mod nor the game", rel=rel))
    try:
        return spritesheet.parse(p.read_bytes())
    except (OSError, spritesheet.SheetError) as e:
        raise MenuSheetError(f"{rel}: {e}")


def cultures(mod) -> List[str]:
    """The cultures whose interface pages the mod ships, by folder."""
    ui = Path(mod.data) / "ui"
    try:
        return sorted(d.name for d in ui.iterdir() if (d / "interface").is_dir())
    except OSError:
        return []


def overview(mod) -> Dict:
    """Every sheet there is, with its pages and every sprite's box."""
    out = []
    for rel in SHEETS:
        try:
            s = _sheet(mod, rel)
        except MenuSheetError:
            continue
        out.append({"rel": rel, "pages": s.pages,
                    "sprites": [{"name": x.name, "page": x.page, "box": [x.left, x.top, x.right, x.bottom]}
                                for x in s.sprites]})
    return {"sheets": out, "cultures": cultures(mod)}


def page_rel(culture: str, page: str) -> str:
    return f"ui/{culture}/interface/{page}"


def page_file(mod, culture: str, page: str) -> Tuple[Optional[Path], str]:
    """The page as the game finds it for that culture: the mod's ('mod'), else
    the game's ('game'), else (None, '')."""
    rel = page_rel(culture, page)
    p = picture_path(mod, rel)
    if p is not None:
        return p, "mod"
    p = read_path(mod, rel)
    return (p, "game") if p is not None else (None, "")


def _open(path: Path):
    from PIL import Image
    try:
        return Image.open(path).convert("RGBA")
    except (OSError, ValueError):
        return None


def page_png(mod, culture: str, page: str) -> Tuple[bytes, str]:
    p, where = page_file(mod, culture, page)
    im = _open(p) if p is not None else None
    if im is None:
        raise MenuSheetError(_i18n.msg("eng.menusheets.page_missing", "{rel} is in neither the mod nor the game",
                                       rel=page_rel(culture, page)))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), where


def box_size(sprite) -> Tuple[int, int]:
    """A sprite's box, ``right`` and ``bottom`` being the first column and row
    past it (a page-wide sprite on a 512 page is 0 to 512)."""
    return max(1, sprite.right - sprite.left), max(1, sprite.bottom - sprite.top)


def fit(im, w: int, h: int, how: str):
    """``im`` made ``w`` by ``h``: stretched, kept in shape on a clear ground,
    or filling the box with what overhangs cut off."""
    from PIL import Image
    if how == "stretch":
        return im.resize((w, h), Image.LANCZOS)
    k = (min if how == "keep" else max)(w / im.width, h / im.height)
    sw, sh = max(1, round(im.width * k)), max(1, round(im.height * k))
    scaled = im.resize((sw, sh), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(scaled, ((w - sw) // 2, (h - sh) // 2))
    return out


def replace(mod, sheet_rel: str, culture: str, name: str, raw: bytes, how: str = "stretch") -> Dict:
    """Paint ``raw`` into sprite ``name``'s box on ``culture``'s page, in the
    mod's own copy of that page, and log it for Undo."""
    from PIL import Image
    if how not in FITS:
        raise MenuSheetError(f"fit {how!r}")
    if culture not in cultures(mod):
        raise MenuSheetError(_i18n.msg("eng.menusheets.no_culture", "the mod has no interface pages for {culture}", culture=culture))
    s = _sheet(mod, sheet_rel)
    sp = next((x for x in s.sprites if x.name == name), None)
    if sp is None or not 0 <= sp.page < len(s.pages):
        raise MenuSheetError(_i18n.msg("eng.menusheets.no_sprite", "{name} is not in {rel}", name=name, rel=sheet_rel))
    src, where = page_file(mod, culture, s.pages[sp.page])
    page = _open(src) if src is not None else None
    if page is None:
        raise MenuSheetError(_i18n.msg("eng.menusheets.page_missing", "{rel} is in neither the mod nor the game",
                                       rel=page_rel(culture, s.pages[sp.page])))
    try:
        pic = Image.open(io.BytesIO(raw)).convert("RGBA")
    except (OSError, ValueError):
        raise MenuSheetError(_i18n.msg("eng.menusheets.not_a_picture", "that file is not a picture"))
    w, h = box_size(sp)
    page.paste(fit(pic, w, h, how), (sp.left, sp.top))

    rel = page_rel(culture, s.pages[sp.page])
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    target = Path(mod.data) / rel
    if where == "mod":
        b = backup_root / "data" / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, b)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", target, f"-> {b}")
    else:
        manifest["created"].append(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".new")
    page.save(tmp, "TGA")
    tmp.replace(target)
    file_op("WRITE", target, "menu sprite")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "cards",
           "action": "menu_sprite", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": name, "resolved_type": name,
           "options": {"sheet": sheet_rel, "culture": culture, "fit": how}, "applied": True,
           "undone": False, "note": "",
           "summary": _i18n.msg("eng.menusheets.summary", "{name}'s picture on {culture}'s {page}",
                                name=name, culture=culture, page=s.pages[sp.page]),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("MENU SPRITE %s on %s in %s, id=%s", name, rel, mod.name, tid)
    return rec
