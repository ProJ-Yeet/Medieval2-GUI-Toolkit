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


# ---------------------------------------------------------------------------
# a trait or an ancillary that a script gives
#
# Reported on 2026-09-22 about AGO: a mod on M2TWEOP can hand a trait out from
# Lua and never from a trigger. AGO's OldAge, the trait that ages a character
# to death, is `namedChar:addTraitPoints("OldAge", 1)` in
# eopData/eopScripts/Campaign/world.lua, and the traits screen called it "no
# trigger gives it" in bold. So the scripts are read for the calls that give,
# the calls that only look, and any bare string that is the record's name - a
# table of race traits the script loops over names every one of them and calls
# none by name.

#: EOP's character methods, per record kind: (gives, only reads or takes away)
RECORD_CALLS = {
    "trait": ({"addtrait", "addtraitpoints", "givetrait"},
              {"gettraitlevel", "hastrait", "removetrait", "removetraitpoints"}),
    "ancillary": ({"addancillary", "giveancillary"},
                  {"hasancillary", "removeancillary"}),
}
_CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(\s*(['\"])([^'\"\n]{1,80})\2")
_STR_RE = re.compile(r"(['\"])([A-Za-z_][\w.\-]{0,79})\1")
# the console command, which scripts also send: give_trait <char> <trait> <n>
_CONSOLE_RE = re.compile(r"\bgive_(trait|ancillary)\b[^\n]*", re.I)


#: Where M2TWEOP looks for a mod's scripts: it loads
#: eopData/eopScripts/luaPluginScript.lua and what that requires.
EOP_SCRIPT_DIRS = ("eopdata", "youneuoy_data")


def eop_scripts(mod) -> List[Path]:
    """The ``.lua`` files M2TWEOP can run for this mod.

    Not :func:`lua_files`: that walks the whole mod, which the modeldb cleanup
    needs (a model named anywhere must be kept) and which costs 9 s on DaC and
    15 s on ROCSS. A trait is given by a script EOP runs, and EOP runs scripts
    from ``eopData``. A mod whose full list is already built reuses it.
    """
    cached = getattr(mod, "__dict__", {}).get("lua_files")
    if isinstance(cached, list):
        return list(cached)
    root = Path(getattr(mod, "root", mod))
    out: List[Path] = []
    try:
        tops = [p for p in root.iterdir() if p.is_dir() and p.name.lower() in EOP_SCRIPT_DIRS]
    except OSError:
        return out
    for top in tops:
        out += sorted(p for p in top.rglob("*.lua") if p.is_file())
    return out


def record_mentions(mod, kind: str, names: Iterable[str]) -> Dict[str, List[dict]]:
    """``name -> [{file, line, call, how}]`` for every trait (or ancillary) a
    script names, ``how`` being ``gives``, ``reads`` or ``names``.

    Comments are blanked first: a call behind ``--`` gives nothing. Matching is
    case-blind, as the engine's lookup is. Cached on a Mod per kind, because the
    list and every record's detail ask the same question of the same scripts.
    """
    cache = getattr(mod, "_lua_record_cache", None)
    if cache is None:
        cache = {}
        try:
            mod._lua_record_cache = cache
        except AttributeError:
            pass
    want = {n.lower(): n for n in names if n}
    key = (kind, frozenset(want))
    if key in cache:
        return cache[key]
    gives, reads = RECORD_CALLS[kind]
    root = Path(getattr(mod, "root", mod))
    out: Dict[str, List[dict]] = {}
    for path in eop_scripts(mod):
        text = _read(path)
        if not text:
            continue
        # No "does this file name any of them" pre-check: that is every name
        # tested against every script, 1 457 x 112 on DaC, and it cost 13 s.
        # The three passes below are one linear scan each.
        live = strip_comments(text)
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        starts = _line_starts(live)
        taken = set()

        def add(name, pos, call, how):
            out.setdefault(want[name], []).append(
                {"file": rel, "line": bisect.bisect_right(starts, pos), "call": call, "how": how})

        for m in _CALL_RE.finditer(live):
            name = m.group(3).lower()
            if name not in want:
                continue
            fn = m.group(1).lower()
            taken.add(m.start(3))
            add(name, m.start(3), m.group(1),
                "gives" if fn in gives else "reads" if fn in reads else "names")
        for m in _CONSOLE_RE.finditer(live):
            if m.group(1).lower() != kind:
                continue
            for tok in re.findall(r"[A-Za-z_][\w]*", m.group(0)):
                if tok.lower() in want:
                    add(tok.lower(), m.start(), f"give_{kind}", "gives")
        for m in _STR_RE.finditer(live):
            name = m.group(2).lower()
            if name in want and m.start(2) not in taken:
                add(name, m.start(2), "", "names")
    cache[key] = out
    return out


def gives(hits: List[dict]) -> bool:
    return any(h["how"] == "gives" for h in hits or ())
