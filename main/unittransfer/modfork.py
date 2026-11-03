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

**From the plain game (96f, the thin mod).** The base can also be the game
itself: ``<game>/data`` becomes ``mods/<new>/data`` by the same rules, so a
mod of one's own on the plain game costs the text files and nothing more,
and every screen of the toolkit reads it as it reads any mod - there is no
second place to look a file up in. The editor's thin mod leaves the files
out altogether and reads the game's in their place; a hard link is the same
saving without teaching a hundred readers about a fallback.
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


#: what a fork from the plain game is called where a base mod's name would be
GAME = "the game"
#: packed files a fork from the game takes out of the packs as well: the text
#: and databases the toolkit edits (a Steam install keeps every one of them in
#: packs/, so a fork of its loose data/ alone had no unit list to open)
PACKED_EXT = (".modeldb", ".db")


def _packed_text(game_dir: Path):
    """``[(rel under data/, size, pack)]``: what the game's packs hold that the
    toolkit edits and its loose ``data/`` lacks."""
    from . import gamepack
    out, seen = [], set()
    data = game_dir / "data"
    for pk in gamepack.packs(game_dir):
        for key, entry in pk.entries.items():
            if not key.startswith("data/") or key in seen:
                continue
            rel = key[5:]
            base = rel.rsplit("/", 1)[-1]
            if not (_copied(base) or base.endswith(PACKED_EXT)):
                continue
            seen.add(key)
            if not (data / rel).is_file():
                out.append((rel, entry[2], pk))
    return out


def _where(base_root, name: str, game: bool):
    """(the folder walked, the folder it lands in, the new mod's root, the
    game folder). From a mod, the mod folder; from the game, its data/."""
    base_dir = Path(base_root)
    if game:
        root = base_dir / "mods" / name
        return base_dir / "data", root / "data", root, base_dir
    root = base_dir.parent / name
    return base_dir, root, root, base_dir.parent.parent


def plan(base_root, name: str, game: bool = False) -> Dict:
    """What a fork would make, without making it: the target, the file counts,
    the bytes linked and copied, and whether the target is free. ``game``: the
    base is the game's own folder, not a mod."""
    base_dir = Path(base_root)
    name = (name or "").strip()
    out: Dict = {"base": GAME if game else base_dir.name, "name": name, "errors": [], "game": game}
    if not RE_NAME.match(name):
        out["errors"].append(_i18n.msg("eng.modfork.bad_name", "a mod folder name may use letters, digits, _ and - only"))
    if game and not (base_dir / "data").is_dir():
        out["errors"].append(_i18n.msg("eng.modfork.no_game_data", "{base} has no data folder - is it the game's folder?", base=str(base_dir)))
    elif not game and base_dir.parent.name.lower() != "mods":
        out["errors"].append(_i18n.msg("eng.modfork.not_in_mods", "{base} is not in a mods folder", base=str(base_dir)))
    walk_root, _land, target, _g = _where(base_root, name, game)
    out["target"] = str(target)
    if name and name.lower() == base_dir.name.lower():
        out["errors"].append(_i18n.msg("eng.modfork.same_name", "the new mod needs a name other than its base"))
    elif name and target.exists():
        out["errors"].append(_i18n.msg("eng.modfork.exists", "{target} already exists - pick another name", target=str(target)))
    linked = copied = nl = nc = 0
    if walk_root.is_dir():
        for dirpath, dirnames, files in os.walk(walk_root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            at_top = not game and os.path.normpath(dirpath) == os.path.normpath(walk_root)
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
    packed = _packed_text(base_dir) if game and base_dir.is_dir() else []
    out.update(linked_files=nl, copied_files=nc, linked_bytes=linked, copied_bytes=copied,
               packed_files=len(packed), packed_bytes=sum(s for _r, s, _p in packed),
               ok=not out["errors"])
    return out


def create(base_root, name: str, copy_all: bool = False,
           progress: Optional[Callable[[int], None]] = None, game: bool = False) -> Dict:
    """Make ``mods/<name>`` from ``base_root`` (a mod, or with ``game`` the
    game's own folder). Returns a summary."""
    p = plan(base_root, name, game)
    if p["errors"]:
        raise ForkError("; ".join(p["errors"]))
    base_dir = Path(base_root)
    base = GAME if game else base_dir.name
    walk_root, land, target, game_dir = _where(base_root, name, game)
    stats: Dict = {"linked": 0, "copied": 0, "renamed": 0, "bytes_copied": 0,
                   "bytes_linked": 0, "skipped": []}
    link_ok = [not copy_all]
    target.mkdir(parents=True)
    try:
        for dirpath, dirnames, files in os.walk(walk_root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            rel = os.path.relpath(dirpath, walk_root)
            out_dir = os.path.normpath(os.path.join(land, rel))
            os.makedirs(out_dir, exist_ok=True)
            at_top = not game and os.path.normpath(dirpath) == os.path.normpath(walk_root)
            for n in files:
                low = n.lower()
                if n == MARKER or (at_top and low.endswith((".bat", ".cmd", ".cfg"))):
                    continue                  # the start files are written for the new name below
                src = os.path.join(dirpath, n)
                names = [n]
                # a file named after the base mod (HLR.idx): also under the new name
                if not game and re.match(r"^%s\." % re.escape(base), n, re.I):
                    names.append(name + n[len(base):])
                for dn in names:
                    try:
                        _put(src, os.path.join(out_dir, dn), link_ok, stats)
                    except OSError as e:
                        stats["skipped"].append(
                            [os.path.relpath(src, walk_root).replace("\\", "/"), e.strerror or str(e)])
                        continue
                    if dn != n:
                        stats["renamed"] += 1
                done = stats["linked"] + stats["copied"]
                if progress and done % 500 == 0:
                    progress(done)
        if game:
            stats["unpacked"] = 0
            for rel, _size, pk in _packed_text(base_dir):
                dst = Path(land) / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(pk.read("data/" + rel))
                stats["unpacked"] += 1
        for n, text in _starts(game_dir, target if game else base_dir, base, name).items():
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
#: folders no write may land in: the base game's own data/, which the toolkit
#: shows read only (the registry sets it). An edit there would change the plain
#: game under every mod that leans on it; it is made in a mod made from it.
READ_ONLY: List[str] = []


class ReadOnlyError(PermissionError):
    pass


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
    full = os.path.abspath(s).replace("\\", "/").lower()
    if any(full.startswith(ro) for ro in READ_ONLY):
        raise ReadOnlyError(_i18n.msg(
            "eng.modfork.base_game_read_only",
            "the base game is read only here: make a mod from it (Home > New mod folder from the plain game) and change that ({path})",
            path=s))
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
