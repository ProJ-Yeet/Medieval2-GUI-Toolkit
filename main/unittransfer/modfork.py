"""Make a new mod folder from an installed mod, or from the plain game.

The heavy files (textures, models, sounds, packs) become hard links, so the
new mod costs almost no disk; the text files people edit are real copies.
Because a hard link is one file with two names, a write guard also lives
here: once installed, any in-place write under a "mods" folder first gives
that file its own copy, so saving in one mod never changes the other. The same
guard refuses every write into the read-only base game "data" folders.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
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

from . import i18n as _i18n

MARKER = "toolkit_linked_mod.json"
COPY_EXT = {".txt", ".json", ".xml", ".nut", ".lua", ".ini", ".cfg", ".csv",
            ".yml", ".yaml", ".bat", ".cmd", ".log"}
COPY_NAMES = {"map.rwm"}
SKIP_DIRS = {"__pycache__", ".git", "backups", "saves", "logs"}
M2_EXES = ("M2EX.exe", "medieval2.exe", "kingdoms.exe")
RE_NAME = re.compile(r"[A-Za-z0-9_-]+")
GAME = "the game"
PACKED_EXT = (".modeldb", ".db")

# folder prefixes (absolute, forward slashes, lower case, trailing "/") no write may land in
READ_ONLY: list = []


class ForkError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ReadOnlyError(PermissionError):
    pass


def _is_copy(name):
    low = name.lower()
    return (os.path.splitext(low)[1] in COPY_EXT or low in COPY_NAMES
            or low.endswith(".strings.bin"))


def _is_packed_kind(name):
    return _is_copy(name) or name.lower().endswith(PACKED_EXT)


def _walk(top):
    """Yield (full path, relative path with /) for every file under top."""
    top = str(top)
    for dirpath, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, top)
        for f in files:
            if f.lower() == MARKER:
                continue
            rel = f if rel_dir == "." else rel_dir.replace("\\", "/") + "/" + f
            yield os.path.join(dirpath, f), rel


def _top_start_file(rel):
    return "/" not in rel and os.path.splitext(rel.lower())[1] in (".bat", ".cmd", ".cfg")


def _packed_files(game_dir):
    """{relative path under data/: (pack, size)} for pack files the loose data lacks."""
    from . import gamepack
    data = Path(game_dir) / "data"
    loose = {rel.lower() for _p, rel in _walk(data)}
    found = {}
    for pack in gamepack.packs(game_dir):
        for key, ent in pack.entries.items():
            if not key.startswith("data/"):
                continue
            rel = key[5:]
            if not rel or rel in loose or rel in found:
                continue
            if _is_packed_kind(rel.rsplit("/", 1)[-1]):
                found[rel] = (pack, ent[2])
    return found


def plan(base_root, name, game=False):
    name = (name or "").strip()
    base = Path(base_root)
    errors = []
    if not RE_NAME.fullmatch(name):
        errors.append(_i18n.msg("eng.modfork.bad_name",
                                "a mod folder name may use letters, digits, _ and - only"))
    if game:
        target = base / "mods" / name
        walk_root = base / "data"
        if not walk_root.is_dir():
            errors.append(_i18n.msg("eng.modfork.no_game_data",
                                    "{base} has no data folder - is it the game's folder?", base=str(base)))
    else:
        target = base.parent / name
        walk_root = base
        if base.parent.name.lower() != "mods":
            errors.append(_i18n.msg("eng.modfork.not_in_mods", "{base} is not in a mods folder", base=str(base)))
    if not game and name.lower() == base.name.lower():
        errors.append(_i18n.msg("eng.modfork.same_name", "the new mod needs a name other than its base"))
    elif target.exists():
        errors.append(_i18n.msg("eng.modfork.exists", "{target} already exists - pick another name",
                                target=str(target)))

    counts = {"linked": 0, "copied": 0, "lb": 0, "cb": 0}
    if walk_root.is_dir():
        for full, rel in _walk(walk_root):
            if not game and _top_start_file(rel):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if _is_copy(rel):
                counts["copied"] += 1
                counts["cb"] += size
            else:
                counts["linked"] += 1
                counts["lb"] += size
    packed = {}
    if game and walk_root.is_dir():
        try:
            packed = _packed_files(base)
        except Exception:
            packed = {}
    return {
        "base": GAME if game else base.name,
        "name": name,
        "errors": errors,
        "game": bool(game),
        "target": str(target),
        "linked_files": counts["linked"],
        "copied_files": counts["copied"],
        "linked_bytes": counts["lb"],
        "copied_bytes": counts["cb"],
        "packed_files": len(packed),
        "packed_bytes": sum(s for _p, s in packed.values()),
        "ok": not errors,
    }


def _start_cfg_text(base, name):
    """The base mod's own cfg pointed at the new name, else a plain default."""
    pat = re.compile(r"mods[/\\]" + re.escape(base.name) + r"\b", re.I)
    if base.is_dir():
        for cfg in sorted(base.glob("*.cfg"), key=lambda p: p.name):
            try:
                text = cfg.read_bytes().decode("latin-1")
            except OSError:
                continue
            if pat.search(text):
                return pat.sub(lambda _m: "mods/" + name, text)
    return ("[features]\r\nmod = mods/%s\r\n\r\n[log]\r\nto = mods/%s/system.log.txt\r\nlevel = * error\r\n"
            % (name, name))


def create(base_root, name, copy_all=False, progress=None, game=False):
    pl = plan(base_root, name, game=game)
    if pl["errors"]:
        raise ForkError("; ".join(pl["errors"]))
    name = pl["name"]
    base = Path(base_root)
    target = Path(pl["target"])
    src_root = base / "data" if game else base
    dest_root = target / "data" if game else target
    game_dir = base if game else target.parent.parent

    st = {"linked": 0, "copied": 0, "renamed": 0, "bl": 0, "bc": 0,
          "links_ok": not copy_all, "unpacked": 0}
    skipped = []

    def tick():
        n = st["linked"] + st["copied"]
        if progress and n and n % 500 == 0:
            progress(n)

    def place(src, rel, copy_it):
        """Put src at dest_root/rel; return True when placed."""
        dst = dest_root / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            size = os.path.getsize(src)
            if not copy_it and st["links_ok"]:
                try:
                    os.link(src, dst)
                    st["linked"] += 1
                    st["bl"] += size
                    return True
                except OSError:
                    st["links_ok"] = False
                    if dst.exists():
                        dst.unlink()
            shutil.copy2(src, dst)
            st["copied"] += 1
            st["bc"] += size
            return True
        except OSError as e:
            skipped.append([rel, str(e)])
            return False

    try:
        target.mkdir(parents=True, exist_ok=False)
        prefix = (base.name + ".").lower()
        for full, rel in _walk(src_root):
            if not game and _top_start_file(rel):
                continue
            copy_it = bool(copy_all) or _is_copy(rel)
            if place(full, rel, copy_it):
                tick()
            leaf = rel.rsplit("/", 1)[-1]
            if not game and leaf.lower().startswith(prefix):
                extra = rel[:len(rel) - len(leaf)] + name + leaf[len(base.name):]
                if place(full, extra, copy_it):
                    st["renamed"] += 1
                    tick()
        if game:
            for rel, (pack, _size) in sorted(_packed_files(base).items()):
                dst = dest_root / rel
                try:
                    data = pack.read("data/" + rel)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    st["unpacked"] += 1
                except (OSError, KeyError) as e:
                    skipped.append([rel, str(e)])

        if skipped and not (st["linked"] or st["copied"] or st["unpacked"]):
            raise ForkError(_i18n.msg(
                "eng.modfork.nothing_copied",
                "no file of {base} could be copied (the first: {rel} - {why})",
                base=pl["base"], rel=skipped[0][0], why=skipped[0][1]))

        exe = next((e for e in M2_EXES if (game_dir / e).exists()), "medieval2.exe")
        how = ("--features.mod=mods/%s" % name if exe.lower() == "m2ex.exe"
               else "@mods\\%s\\%s.cfg" % (name, name))
        bat = 'cd /d "%~dp0..\\.."\r\nstart "" ' + exe + " " + how + "\r\n"
        (target / (name + ".cfg")).write_bytes(_start_cfg_text(base, name).encode("latin-1", "replace"))
        (target / ("Start_" + name + ".bat")).write_bytes(bat.encode("latin-1", "replace"))
        (target / MARKER).write_text(
            json.dumps({"base": pl["base"], "linked": st["links_ok"]}, indent=2),
            encoding="utf-8")
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise

    out = {
        "linked": st["linked"], "copied": st["copied"], "renamed": st["renamed"],
        "bytes_copied": st["bc"], "bytes_linked": st["bl"], "skipped": skipped,
        "target": str(target), "base": pl["base"], "name": name,
        "hard_links": st["links_ok"],
    }
    if game:
        out["unpacked"] = st["unpacked"]
    return out


def info(mod_root):
    try:
        data = json.loads((Path(mod_root) / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def break_link(path):
    """Give a multiply-linked file its own copy. True when it did."""
    try:
        if os.stat(path).st_nlink < 2:
            return False
    except OSError:
        return False
    tmp = os.fspath(path) + ".unlinking"
    try:
        shutil.copy2(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return True


_guard_lock = threading.Lock()
_guard_on = False


def install_write_guard():
    global _guard_on
    with _guard_lock:
        if _guard_on:
            return
        real_open = builtins.open

        def guarded_open(file, mode="r", *args, **kwargs):
            writing = isinstance(mode, str) and any(c in mode for c in "wax+")
            if writing and isinstance(file, (str, bytes, os.PathLike)):
                try:
                    p = os.fsdecode(file)
                    norm = os.path.abspath(p).replace("\\", "/").lower()
                except (TypeError, ValueError, OSError):
                    norm = ""
                if norm:
                    for pre in list(READ_ONLY):
                        if norm.startswith(pre):
                            raise ReadOnlyError(_i18n.msg(
                                "eng.modfork.base_game_read_only",
                                "the base game is read only here: make a mod from it "
                                "(Home > New mod folder from the plain game) and change that ({path})",
                                path=p))
                    if "/mods/" in norm:
                        try:
                            break_link(p)
                        except OSError:
                            pass
            return real_open(file, mode, *args, **kwargs)

        builtins.open = guarded_open
        io.open = guarded_open
        _guard_on = True
