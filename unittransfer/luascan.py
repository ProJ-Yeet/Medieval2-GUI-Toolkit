"""Which names a mod's Lua scripts use - the safety net for the bmdb cleanup.

M2TWEOP mods do a lot of work from Lua that no ``.txt`` in ``data/`` records. A
script can spawn a character with a named battle model, swap a unit's model at
runtime, build an EDU entry from scratch, or hand a mount name to the engine -
and *none* of that shows up in ``export_descr_unit.txt``, ``descr_mount.txt`` or
``descr_character.txt``. To :mod:`unittransfer.bmdb` those entries look like dead
weight, so without this pass the cleanup would happily delete a model the
campaign needs and the mod would break the first time that script ran.

So the rule this module exists to enforce is simple and deliberately blunt:

    read every battle_models.modeldb entry name, read every ``.lua`` under the
    mod, and if a script names an entry - anywhere, in any form - that entry is
    NOT removable.

Two details worth knowing:

* **Comments count.** Elsewhere in the tool a commented-out reference is not a
  reference (see ``bmdb._campaign_models``), but Lua is different in kind: a
  campaign script is data the game reads, whereas a Lua file is a *program* the
  modder is still working on, and a name parked behind ``--`` for a patch is one
  the mod means to keep. The hit is still reported as ``in_comment`` so the UI
  can say so, but it protects the entry either way.
* **Whole names only.** ``gondor_archer`` must not be pinned alive by
  ``gondor_archer_heavy`` appearing in a script, and a name must not match a
  fragment of a path, so both the token scan and the phrase scan below hold to
  the same identifier boundaries the rest of the tool uses.

Scanning is by *token*, not by a regex per name: a mod can have a couple of
thousand modeldb entries, and one pass over each file that collects its
identifiers gives every one of those names an O(1) answer. Mount names contain
spaces (``"gondor horse"``), which no tokeniser will produce, so those get a
second pass with a single combined pattern - the same trick
``bmdb._mount_mentions`` uses on ``descr_*.txt``.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

# Folders never worth walking for a mod's own scripts: they hold copies, not the
# thing the game runs. A false miss here is dangerous, so this list stays short
# and names only places whose contents are by definition not the live mod.
SKIP_DIRS = {".git", ".svn", "__pycache__", "node_modules"}

# Lua identifiers plus the punctuation a modeldb entry name can carry. Same shape
# as ``bmdb._TOKEN_RE`` on purpose - an entry name has to tokenise identically in
# a .lua and in a descr_*.txt or the two nets would disagree about the same name.
_TOKEN_RE = re.compile(r"[a-z0-9_.\-]+")

# Lua comments: a long bracket comment (--[[ ... ]], --[==[ ... ]==]) or a line
# comment. The long form is matched first so its opening `--` is not eaten by the
# line-comment branch, and DOTALL lets it span lines the way Lua does.
_LUA_COMMENT_RE = re.compile(r"--\[(=*)\[.*?\]\1\]|--[^\n]*", re.DOTALL)


@dataclass
class LuaHit:
    """Where a name turned up in a script, for the "kept because…" line."""
    file: str          # path relative to the mod root, posix-style
    line: int          # 1-based line of the first occurrence
    in_comment: bool   # the only occurrences found were inside Lua comments

    def label(self) -> str:
        where = f"{self.file}:{self.line}"
        return f"{where} (in a comment)" if self.in_comment else where


def strip_comments(text: str) -> str:
    """``text`` with Lua comments blanked out, newlines preserved.

    Replaced rather than deleted so a line number computed on the result still
    matches the file the user will open.
    """
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    return _LUA_COMMENT_RE.sub(blank, text)


def _files_for(mod) -> List[Path]:
    """The mod's scripts, via ``Mod.lua_files`` when the caller passed a Mod.

    Both passes below need the same list, and so does the audit that reports how
    many were read - finding them is a tree walk over the whole mod, so it is done
    once per Mod rather than once per caller.
    """
    cached = getattr(mod, "lua_files", None)
    return list(cached) if isinstance(cached, list) else lua_files(mod)


# Files that are not scripts but that the bmdb cleanup's safety nets must read
# just as widely, so they are collected by the same walk rather than by a second
# one. ``campaign`` is "a file that writes `battle_model` inline": the campaign
# and battle scripts, wherever a mod hides them - nested under
# ``campaign/custom/<name>/``, under ``world/maps/battle/custom/``, or in an
# installer's alternate tree (``Activate/``, ``extra/``) that gets copied over
# ``data/`` later.
CAMPAIGN_NAMES = {"descr_strat.txt", "campaign_script.txt", "descr_battle.txt"}
MODELDB_SUFFIX = ".modeldb"
# Anything that could hold a filename in it. Wide on purpose - reading one more
# .txt costs nothing next to missing the reference that breaks the mod - and
# collected here rather than by a walk of its own, because on an overhaul the
# walk is the expensive half and this list shares it with the other two.
#
# `.dat` is NOT here and must not be added: in M2TW that suffix belongs to the
# engine's binary containers, and `data/sounds/Music.dat` alone is two gigabytes.
# Anything else binary that slips in by suffix is caught by the NUL-byte check in
# `bmdb.unit_model_refs`, which is the real guard - this list is just the cheap
# half of it.
TEXT_SUFFIXES = {".txt", ".lua", ".xml", ".cfg", ".ini", ".csv", ".json", ".sd",
                 ".bak", ".text"}


def mod_files(mod, limit: int = 4000) -> Dict[str, List[Path]]:
    """One walk of the mod root -> ``{"lua", "campaign", "text"}``.

    The whole mod folder is walked, not just ``data/``: M2TWEOP keeps its scripts
    in ``eopData/`` beside ``data/`` rather than inside it, and mods scatter more
    of them in campaign folders. The same is true of everything else here - see
    :data:`CAMPAIGN_NAMES` - which is why one walk collects all three kinds
    instead of each caller paying for a pass over a hundred thousand files.

    ``limit`` is a runaway guard on the script list only - no real mod comes
    close, and the count is reported so a mod that does hit it says so rather
    than silently scanning half of itself.
    """
    root = Path(getattr(mod, "root", mod))
    out: Dict[str, List[Path]] = {"lua": [], "campaign": [], "text": []}
    if not root.is_dir():
        return out
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            children = sorted(cur.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for p in children:
            if p.is_dir():
                if p.name.lower() not in SKIP_DIRS:
                    stack.append(p)
                continue
            name, suffix = p.name.lower(), p.suffix.lower()
            if MODELDB_SUFFIX in name:
                # Never scanned as text, and never read as a second opinion about
                # what is alive. A modeldb names thousands of files, so reading
                # one would make every one of them "mentioned somewhere" - and the
                # extra copies a mod carries (`.modeldb.bak`, `battle_models_og`,
                # whatever another tool wrote out) are backups of older states, so
                # trusting them would pin every file the mod has EVER used and
                # nothing could ever be cleaned up again.
                continue
            if suffix == ".lua":
                if len(out["lua"]) < limit:
                    out["lua"].append(p)
            elif name in CAMPAIGN_NAMES:
                out["campaign"].append(p)
            if suffix in TEXT_SUFFIXES:
                out["text"].append(p)
    for kind, paths in out.items():
        paths.sort(key=lambda p: (len(p.relative_to(root).parts), str(p).lower()))
    return out


def lua_files(mod, limit: int = 4000) -> List[Path]:
    """Every ``.lua`` under the mod root, nearest the top first."""
    return mod_files(mod, limit)["lua"]


def _read(path: Path) -> str:
    """Lua source as text. Encoding is whatever the modder's editor wrote, and
    guessing wrong must not lose a reference, so latin-1 (which round-trips every
    byte) is used and a UTF-8 BOM is dropped by hand."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    return data.decode("latin-1")


def _line_starts(text: str) -> List[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


Report = Optional[Callable[[float, str], None]]


def scan(mod, report: Report = None) -> Dict[str, LuaHit]:
    """``token -> LuaHit`` for every identifier any of the mod's scripts names.

    One dict for the whole mod, built once: callers look their own names up in it
    (entry names, and anything else that tokenises) instead of re-reading the
    scripts per name. The first file to name a token wins, and a live (non-comment)
    hit always beats a commented one - the label should quote real code when there
    is any.
    """
    root = Path(getattr(mod, "root", mod))
    files = _files_for(mod)
    out: Dict[str, LuaHit] = {}
    total = len(files) or 1
    for i, path in enumerate(files):
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        if report:
            report(i / total, rel)
        text = _read(path).lower()
        if not text:
            continue
        live = strip_comments(text)
        starts = _line_starts(text)
        for m in _TOKEN_RE.finditer(text):
            tok = m.group(0)
            # the same slice of the blanked copy still holds the token iff the
            # occurrence was real code rather than a comment
            in_comment = live[m.start():m.end()] != tok
            prev = out.get(tok)
            if prev is not None and not (prev.in_comment and not in_comment):
                continue          # already have it, and not an upgrade to live code
            out[tok] = LuaHit(file=rel,
                              line=bisect.bisect_right(starts, m.start()),
                              in_comment=in_comment)
    if report:
        report(1.0, "")
    return out


def phrase_scan(mod, names: Sequence[str], report: Report = None) -> Dict[str, LuaHit]:
    """``name -> LuaHit`` for names a tokeniser cannot see - the ones with spaces.

    Mount types are the case that matters (``"gondor horse"``). Every name goes
    into ONE alternation so each script is read once, longest alternative first so
    at a given position ``"war horse"`` wins over ``"horse"``, and the boundary
    class keeps a name from matching inside a longer identifier or a path segment.
    """
    names = [n for n in names if n and n.strip()]
    if not names:
        return {}
    root = Path(getattr(mod, "root", mod))

    def body(name: str) -> str:
        return r"\s+".join(re.escape(p) for p in name.lower().split())

    by_key = {" ".join(n.lower().split()): n for n in names}
    alts = sorted((body(n) for n in names), key=len, reverse=True)
    rx = re.compile(r"(?<![a-z0-9_./\\-])(?:" + "|".join(alts) + r")(?![a-z0-9_./\\-])")

    files = _files_for(mod)
    out: Dict[str, LuaHit] = {}
    total = len(files) or 1
    for i, path in enumerate(files):
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        if report:
            report(i / total, rel)
        text = _read(path).lower()
        if not text:
            continue
        live = strip_comments(text)
        starts = _line_starts(text)
        for m in rx.finditer(text):
            name = by_key.get(" ".join(m.group(0).split()))
            if name is None:
                continue
            in_comment = live[m.start():m.end()].strip() == ""
            prev = out.get(name)
            if prev is not None and not (prev.in_comment and not in_comment):
                continue
            out[name] = LuaHit(file=rel,
                               line=bisect.bisect_right(starts, m.start()),
                               in_comment=in_comment)
    if report:
        report(1.0, "")
    return out


def protected(tokens: Dict[str, LuaHit], names: Iterable[str]) -> Dict[str, LuaHit]:
    """The subset of ``names`` some script mentions, as ``name -> hit``."""
    out: Dict[str, LuaHit] = {}
    for n in names:
        hit = tokens.get((n or "").lower())
        if hit is not None:
            out[n] = hit
    return out
