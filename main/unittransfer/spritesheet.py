"""The interface's sprite sheets: ``ui/strategy.sd`` and ``ui/shared.sd`` (Phase 91).

A sheet is a table of named rectangles on a few ``.tga`` pages. The pages are
per culture (``ui/<culture>/interface/stratpage_02.tga``); the table is not -
there is **one** ``ui/strategy.sd`` and one ``ui/shared.sd`` for every culture,
read once at start-up. ``descr_sm_factions.txt`` names a faction's shield by
sprite name: ``logo_index`` in ``strategy.sd`` (the campaign map's faction
button, the diplomacy scroll), ``small_logo_index`` in ``shared.sd`` (the
settlement scroll, the family tree, the faction lists).

**A name not in the sheet is not refused.** The game loads, and draws sprite 0
of the sheet in the shield's place, which in every sheet measured is some other
button, not a shield. That is the
reported symptom: the faction button is there (the hotkey opens its screen)
and its picture is not. And the name is resolved to a position once, when the
roster is read, so a shield is its name's *position* from then on - which is
why this module only ever appends an entry and never reorders one: a mod
whose roster uses a number (``logo_index 12``) keeps every number meaning
what it meant.

The layout, byte for byte: ``version`` (6), the page count and the sprite
count; each page is a length-prefixed file name, a byte (force 32-bit), its
width and height, and a length-prefixed hit mask one bit a pixel (the shaped
buttons are clickable where it is set, which is why a shield drawn by hand
needs its mask too); each sprite is a length-prefixed name and sixteen bytes -
the page, left, right, top and bottom, the alpha flag, one more byte and a
two-short offset. Every sheet in both installed mods and the reporter's two
parse to their last byte.

Only the names are read for the checks, and the one thing written is
:func:`add_alias`: another name for a picture the sheet already has. That is
what a cloned faction needs to have a shield of its own name, drawn as its
donor's until somebody paints it, and what the audit's repair gives a faction
whose name was never added.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import i18n as _i18n

STRATEGY = "ui/strategy.sd"
SHARED = "ui/shared.sd"

#: ``descr_sm_factions.txt`` key -> the sheet its value is a name in
SHEET_OF: Dict[str, str] = {"logo_index": STRATEGY, "small_logo_index": SHARED}

#: what the clone names a new faction's shields, the convention every sheet
#: measured keeps (vanilla, DaC, Reforged, the reporter's)
PREFIX: Dict[str, str] = {"logo_index": "FACTION_LOGO_",
                          "small_logo_index": "SMALL_FACTION_LOGO_"}

VERSION = 6
DESCRIPTOR = 16                    # bytes after each sprite's name


class SheetError(ValueError):
    pass


@dataclass
class Sprite:
    name: str
    page: int
    left: int
    right: int
    top: int
    bottom: int
    #: the sixteen bytes as they are, so an alias is its original exactly
    raw: bytes = b""


@dataclass
class Sheet:
    pages: List[str] = field(default_factory=list)
    sprites: List[Sprite] = field(default_factory=list)

    def names(self) -> List[str]:
        return [s.name for s in self.sprites]

    def find(self, value: str) -> Optional[Sprite]:
        """The sprite a roster value points at: a name (exact case, as the
        engine's map compares), or a number, which is a position."""
        value = (value or "").strip()
        if value[:1].isdigit():
            try:
                i = int(value)
            except ValueError:
                return None
            return self.sprites[i] if 0 <= i < len(self.sprites) else None
        return next((s for s in self.sprites if s.name == value), None)


def parse(raw: bytes) -> Sheet:
    """Every page's file name and every sprite. Raises :class:`SheetError` on
    anything that is not a version-6 sheet read to its last byte."""
    o = 0

    def card(fmt: str) -> int:
        nonlocal o
        size = struct.calcsize(fmt)
        if o + size > len(raw):
            raise SheetError(_i18n.msg("eng.spritesheet.ends_early_at_byte", "ends early, at byte {o}", o=o))
        v = struct.unpack_from(fmt, raw, o)[0]
        o += size
        return v

    def text(limit: int = 4096) -> str:
        nonlocal o
        n = card("<I")
        if n > limit or o + n > len(raw):
            raise SheetError(_i18n.msg("eng.spritesheet.a_name_bytes_long_at", "a name {n} bytes long at byte {at}", n=n, at=o - 4))
        s = raw[o:o + n].decode("latin-1")
        o += n
        return s

    version = card("<I")
    if version != VERSION:
        raise SheetError(_i18n.msg("eng.spritesheet.version_not", "version {version}, not {want}", version=version, want=VERSION))
    npages, nsprites = card("<I"), card("<I")
    sheet = Sheet()
    for _ in range(npages):
        sheet.pages.append(text())
        o += 1 + 8                     # force-32-bit, width, height
        mask = card("<I")
        if o + mask > len(raw):
            raise SheetError(_i18n.msg("eng.spritesheet.a_page_mask_runs_past", "a page mask runs past the end, at byte {o}", o=o))
        o += mask
    for _ in range(nsprites):
        name = text()
        if o + DESCRIPTOR > len(raw):
            raise SheetError(_i18n.msg("eng.spritesheet.sprite_ends_early", "sprite {name} ends early", name=name))
        body = raw[o:o + DESCRIPTOR]
        page, left, right, top, bottom = struct.unpack_from("<5h", body)
        sheet.sprites.append(Sprite(name, page, left, right, top, bottom, body))
        o += DESCRIPTOR
    if o != len(raw):
        raise SheetError(_i18n.msg("eng.spritesheet.bytes_after_the_last_sprite", "{n} bytes after the last sprite", n=len(raw) - o))
    return sheet


def read(data: Path, rel: str) -> Optional[Sheet]:
    """The mod's own loose sheet, or ``None`` when it ships none (the game then
    reads the one in its packs, which nothing here can see) or it will not
    parse - either way there is no evidence, and no check runs."""
    path = Path(data) / rel
    if not path.is_file():
        return None
    try:
        return parse(path.read_bytes())
    except (OSError, SheetError):
        return None


def add_alias(raw: bytes, name: str, like: str) -> bytes:
    """``raw`` with one more sprite, ``name``, drawing exactly what ``like``
    draws. Appended after the last sprite with the count raised by one, so
    every existing sprite keeps its position; every other byte is unchanged."""
    sheet = parse(raw)
    if not name or not all(33 <= ord(ch) < 127 for ch in name):
        raise SheetError(_i18n.msg("eng.spritesheet.is_not_a_sprite_name", "`{name}` is not a sprite name", name=name))
    if sheet.find(name) is not None and not name[:1].isdigit():
        raise SheetError(_i18n.msg("eng.spritesheet.is_already_in_the_sheet", "{name} is already in the sheet", name=name))
    src = sheet.find(like)
    if src is None:
        raise SheetError(_i18n.msg("eng.spritesheet.is_not_in_the_sheet", "{like} is not in the sheet", like=like))
    count = struct.unpack_from("<I", raw, 8)[0]
    enc = name.encode("latin-1")
    return (raw[:8] + struct.pack("<I", count + 1) + raw[12:]
            + struct.pack("<I", len(enc)) + enc + src.raw)
