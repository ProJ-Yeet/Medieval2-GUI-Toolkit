"""Find EDU units whose type is not mentioned anywhere else in a mod."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional


OPTIONAL_SOUND_FILES = {
    "data/export_descr_sounds_units_voice.txt",
    "data/descr_sounds_weapons.txt",
}
EDU_FILE = "data/export_descr_unit.txt"
# This file supplies display names/descriptions only; it cannot make a unit
# reachable by the game.
LOCALISATION_FILE = "data/text/export_units.txt"
_WORD = r"A-Za-z0-9_"
_VCS_DIRS = {".git", ".hg", ".svn", ".bzr", "_darcs", "cvs"}


def _text(path: Path) -> Optional[str]:
    """Return text, or ``None`` when the file looks binary."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            return None
    sample = raw[:8192]
    if b"\0" in sample:
        return None
    if sample and sum(b < 32 and b not in (9, 10, 13) for b in sample) / len(sample) > .02:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("cp1252")
        except UnicodeDecodeError:
            return None


def scan(mod, include_sound_registrations: bool = True,
         progress: Optional[Callable[[int, str], None]] = None,
         cancelled: Optional[Callable[[], bool]] = None) -> dict:
    """Return main-EDU types and every textual file that names each one."""
    types = sorted({u.type for u in mod.edu.main_units if u.type}, key=str.lower)
    found: Dict[str, set[str]] = {t: set() for t in types}
    if not types:
        return {"units": [], "files_scanned": 0, "binary_skipped": 0}
    by_fold = {t.casefold(): t for t in types}
    choices = "|".join(re.escape(t) for t in sorted(types, key=len, reverse=True))
    pattern = re.compile(rf"(?<![{_WORD}])({choices})(?![{_WORD}])", re.IGNORECASE)
    paths: List[Path] = [p for p in mod.root.rglob("*") if p.is_file()
                         and not any(x.lower() in _VCS_DIRS | {"__pycache__"} for x in p.parts)]
    binary = 0
    for i, path in enumerate(paths, 1):
        if cancelled and cancelled():
            return {"units": [], "files_scanned": i - 1, "binary_skipped": binary,
                    "cancelled": True}
        if progress and (i == 1 or i == len(paths) or i % 20 == 0):
            progress(round(i * 100 / max(1, len(paths))), f"scanning {i}/{len(paths)} files")
        body = _text(path)
        if body is None:
            binary += 1
            continue
        rel = path.relative_to(mod.root).as_posix()
        for match in pattern.finditer(body):
            typ = by_fold.get(match.group(1).casefold())
            if typ:
                found[typ].add(rel)
    allowed = {EDU_FILE, LOCALISATION_FILE}
    if include_sound_registrations:
        allowed.update(OPTIONAL_SOUND_FILES)
    return {"units": [{"type": typ, "files": sorted(found[typ]),
                         "unused": found[typ].issubset(allowed)} for typ in types],
            "files_scanned": len(paths), "binary_skipped": binary}
