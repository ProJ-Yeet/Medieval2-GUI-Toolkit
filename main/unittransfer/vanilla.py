"""The game's own copy of a data file, for the vanilla value beside a rule (96e7).

Every rule screen edits the mod's copy of a file - ``descr_campaign_db.xml``,
``descr_settlement_mechanics.xml`` - and a value somebody changed three
versions ago has nothing beside it to say what the game shipped. The shipped
copy is in the base game's ``packs/data_*.pack``, which :mod:`gamepack` reads
without unpacking. Only the packs count: the game's loose ``data/`` is where an
unpacker, M2EX or another mod's installer has already written, so it is not
vanilla.

Nothing here writes. A screen asks :func:`text` for a file, parses it with its
own parser, and hands the page ``{key: value}``; a Reset on the page is only
the vanilla value typed into the box, saved by the screen's own plan and apply
like any other edit, so the change log can undo it.
"""
from __future__ import annotations

import threading
from typing import Dict, Optional, Tuple

from . import gamepack

_cache: Dict[Tuple[str, str], Optional[str]] = {}
_lock = threading.Lock()


def text(rel: str, mod=None, encoding: str = "latin-1") -> Optional[str]:
    """The game's own copy of ``data/<rel>``, or None when the packs are not
    found or do not hold it. Read once per game folder."""
    root = gamepack.game_root_of(mod)
    if root is None:
        return None
    key = (str(root).casefold(), rel.replace("\\", "/").lower())
    with _lock:
        if key in _cache:
            return _cache[key]
    try:
        raw = gamepack.read_bytes(rel, root)
    except (OSError, gamepack.PackError, ValueError):
        raw = None
    out = raw.decode(encoding, errors="replace") if raw is not None else None
    with _lock:
        _cache[key] = out
    return out


def values(rel: str, mod, parse, pairs) -> Dict[str, str]:
    """``{key: value}`` from the game's copy, through the screen's own parser:
    ``parse(text)`` builds its file, ``pairs(file)`` yields ``(key, value)``.
    Empty when there is no game copy or it does not parse."""
    src = text(rel, mod)
    if src is None:
        return {}
    try:
        return {str(k): str(v) for k, v in pairs(parse(src))}
    except Exception:  # noqa: BLE001 - a game copy this parser cannot read has no vanilla values
        return {}


def clear_cache() -> None:
    with _lock:
        _cache.clear()
