"""A new mod folder from an installed one, its unchanged files hard links (96e7).

Taken from the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW / M2TW
Campaign Editor's ``newmod.py``, with its author's permission, and fitted to
this toolkit. ``mods/<new>`` is made from ``mods/<base>``: the text files (the
ones a person or this toolkit edits) are real copies, everything else - the
textures, models, sounds, animations and packs that make a mod gigabytes - is a
hard link, the same file on disk under a second name, so the new mod costs
almost nothing until a file in it changes. Links need both folders on one NTFS
drive; where one fails, every file from there on is copied.

**The one thing a hard link changes.** A program that writes into a linked file
*in place* writes into both mods, because they are one file. Replacing a file
(write a new one, rename it over) only ever touches the name it replaces.
:func:`install_write_guard` makes every in-place write this toolkit does to a
file under a ``mods`` folder that has a second name break the link first, so a
save in either mod stays in that mod. An image editor or text editor outside
the toolkit gets no such guard, which the page says.

The start files are written for the new name: ``<new>.cfg`` from the base's
own with its ``mods/<base>`` turned into ``mods/<new>``, and a ``.bat`` that
starts the game with it.
"""
from __future__ import annotations

import builtins
import io
import json
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import i18n as _i18n

MARKER = "toolkit_linked_mod.json"
#: written by people and by this toolkit, so real copies; the rest is linked
COPY_EXT = {".txt", ".json", ".xml", ".nut", ".lua", ".ini", ".cfg", ".csv",
            ".yml", ".yaml", ".bat", ".cmd", ".log"}
#: what the game itself rebuilds in a mod folder - copied too, since the game
#: writes them back in place
COPY_NAMES = {"map.rwm"}
#: never carried: the toolkit's and the editors' own working folders
SKIP_DIRS = {"__pycache__", ".git", "backups", "saves", "logs"}
M2_EXES = ("M2EX.exe", "medieval2.exe", "kingdoms.exe")
RE_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")


class ForkError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _copied(name: str) -> bool:
    low = name.lower()
    return (os.path.splitext(low)[1] in COPY_EXT or low in COPY_NAMES
            or low.endswith(".strings.bin"))


def _cfg(base_dir: Path, base: str, name: str) -> str:
    """``<name>.cfg``: the base mod's own with its folder renamed, else a plain one."""
    rx = re.compile(r"mods[/\\]%s\b" % re.escape(base), re.I)
    for p in sorted(base_dir.iterdir()) if base_dir.is_dir() else []:
        if p.is_file() and p.suffix.lower() == ".cfg":
            text = p.read_bytes().decode("latin-1")
            if rx.search(text):
                return rx.sub("mods/" + name, text)
    return ("[features]\r\nmod = mods/%s\r\n\r\n[log]\r\nto = mods/%s/system.log.txt\r\n"
            "level = * error\r\n" % (name, name))


def _starts(game: Path, base_dir: Path, base: str, name: str) -> Dict[str, str]:
    exe = next((e for e in M2_EXES if (game / e).is_file()), "medieval2.exe")
    # M2EX's own start files name the mod folder on the command line, not a .cfg
    how = ("--features.mod=mods/%s" % name if exe.lower() == "m2ex.exe"
           else "@mods\\%s\\%s.cfg" % (name, name))
    return {"%s.cfg" % name: _cfg(base_dir, base, name),
            "Start_%s.bat" % name: 'cd /d "%%~dp0..\\.."\r\nstart "" %s %s\r\n' % (exe, how)}


def plan(base_root, name: str) -> Dict:
    """What a fork would make, without making it: the target, the file counts,
    the bytes linked and copied, and whether the target is free."""
    base_dir = Path(base_root)
    name = (name or "").strip()
    out: Dict = {"base": base_dir.name, "name": name, "errors": []}
    if not RE_NAME.match(name):
        out["errors"].append(_i18n.msg("eng.modfork.bad_name", "a mod folder name may use letters, digits, _ and - only"))
    if base_dir.parent.name.lower() != "mods":
        out["errors"].append(_i18n.msg("eng.modfork.not_in_mods", "{base} is not in a mods folder", base=str(base_dir)))
    target = base_dir.parent / name
    out["target"] = str(target)
    if name and name.lower() == base_dir.name.lower():
        out["errors"].append(_i18n.msg("eng.modfork.same_name", "the new mod needs a name other than its base"))
    elif name and target.exists():
        out["errors"].append(_i18n.msg("eng.modfork.exists", "{target} already exists - pick another name", target=str(target)))
    linked = copied = nl = nc = 0
    if base_dir.is_dir():
        for dirpath, dirnames, files in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            at_top = os.path.normpath(dirpath) == os.path.normpath(base_dir)
            for f in files:
                if f == MARKER or (at_top and f.lower().endswith((".bat", ".cmd", ".cfg"))):
                    continue                  # written fresh for the new name
                try:
                    size = os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    continue
                if _copied(f):
                    copied += size; nc += 1
                else:
                    linked += size; nl += 1
    out.update(linked_files=nl, copied_files=nc, linked_bytes=linked, copied_bytes=copied,
               ok=not out["errors"])
    return out


def create(base_root, name: str, copy_all: bool = False,
           progress: Optional[Callable[[int], None]] = None) -> Dict:
    """Make ``mods/<name>`` from ``base_root``. Returns a summary."""
    p = plan(base_root, name)
    if p["errors"]:
        raise ForkError("; ".join(p["errors"]))
    base_dir = Path(base_root)
    base = base_dir.name
    target = Path(p["target"])
    game = base_dir.parent.parent
    stats: Dict = {"linked": 0, "copied": 0, "renamed": 0, "bytes_copied": 0,
                   "bytes_linked": 0, "skipped": []}
    link_ok = [not copy_all]
    target.mkdir(parents=True)
    try:
        for dirpath, dirnames, files in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            rel = os.path.relpath(dirpath, base_dir)
            out_dir = os.path.normpath(os.path.join(target, rel))
            os.makedirs(out_dir, exist_ok=True)
            at_top = os.path.normpath(dirpath) == os.path.normpath(base_dir)
            for n in files:
                low = n.lower()
                if n == MARKER or (at_top and low.endswith((".bat", ".cmd", ".cfg"))):
                    continue                  # the start files are written for the new name below
                src = os.path.join(dirpath, n)
                names = [n]
                # a file named after the base mod (HLR.idx): also under the new name
                if re.match(r"^%s\." % re.escape(base), n, re.I):
                    names.append(name + n[len(base):])
                for dn in names:
                    try:
                        _put(src, os.path.join(out_dir, dn), link_ok, stats)
                    except OSError as e:
                        stats["skipped"].append(
                            [os.path.relpath(src, base_dir).replace("\\", "/"), e.strerror or str(e)])
                        continue
                    if dn != n:
                        stats["renamed"] += 1
                done = stats["linked"] + stats["copied"]
                if progress and done % 500 == 0:
                    progress(done)
        for n, text in _starts(game, base_dir, base, name).items():
            (target / n).write_bytes(text.encode("latin-1"))
        (target / MARKER).write_text(json.dumps(
            {"base": base, "linked": link_ok[0]}, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    if stats["skipped"] and not (stats["linked"] + stats["copied"]):
        shutil.rmtree(target, ignore_errors=True)
        rel, why = stats["skipped"][0]
        raise ForkError(_i18n.msg("eng.modfork.nothing_copied", "no file of {base} could be copied (the first: {rel} - {why})", base=base, rel=rel, why=why))
    stats.update(target=str(target), base=base, name=name, hard_links=link_ok[0])
    return stats


def _put(src: str, dst: str, link_ok: List[bool], stats: Dict) -> None:
    if link_ok[0] and not _copied(os.path.basename(src)):
        try:
            os.link(src, dst)
            stats["linked"] += 1
            stats["bytes_linked"] += os.path.getsize(dst)
            return
        except OSError:
            link_ok[0] = False          # another drive or no NTFS: copy from here on
    shutil.copy2(src, dst)
    stats["copied"] += 1
    stats["bytes_copied"] += os.path.getsize(dst)


def info(mod_root) -> Optional[Dict]:
    """The mark a fork leaves in its folder, or None."""
    try:
        got = json.loads((Path(mod_root) / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) else None


# ---------------------------------------------------------------------------
# the write guard


def break_link(path) -> bool:
    """Give ``path`` a file of its own when it shares one with another name.
    Returns whether it did."""
    p = os.fspath(path)
    try:
        if os.stat(p).st_nlink < 2:
            return False
    except OSError:
        return False
    tmp = p + ".unlinking"
    shutil.copy2(p, tmp)
    os.replace(tmp, p)
    return True


_WRITE = re.compile(r"[wax+]")
_installed = threading.Lock()
_on = [False]


def _guarded(path, mode) -> None:
    if not isinstance(mode, str) or not _WRITE.search(mode):
        return
    if isinstance(path, int):
        return
    try:
        s = os.fspath(path)
    except TypeError:
        return
    if isinstance(s, bytes):
        s = s.decode(errors="replace")
    low = s.replace("\\", "/").lower()
    if "/mods/" not in low:
        return
    break_link(s)


def install_write_guard() -> None:
    """Make every in-place write through ``open`` (and so ``Path.write_text``,
    ``shutil.copy`` onto an existing file) break a hard link under a ``mods``
    folder first. Idempotent."""
    with _installed:
        if _on[0]:
            return
        real = io.open

        def guarded_open(file, mode="r", *args, **kwargs):
            _guarded(file, mode)
            return real(file, mode, *args, **kwargs)

        io.open = guarded_open
        builtins.open = guarded_open
        _on[0] = True
