"""Every file in a mod that names a unit *type*, and renaming it in all of them.

An EDU ``type`` is a string, and the rest of the mod refers to the unit by that
string from files the EDU knows nothing about:

  * ``export_descr_buildings.txt`` - every ``recruit_pool`` / ``recruit`` line
  * each campaign's ``descr_strat.txt`` - the starting armies
  * each campaign's ``campaign_script.txt`` - ``spawn_army`` and friends
  * ``descr_mercenaries.txt`` - the merc pools
  * ``export_descr_sounds_units_voice.txt`` - the ``unit <type>`` voice entries
  * ``descr_rebel_factions.txt``, ``descr_win_conditions.txt``, …
  * the mod's ``.lua`` scripts (M2TWEOP does a lot from Lua)

Renaming the EDU entry alone leaves every one of those pointing at a unit that no
longer exists - a recruitment slot that lists nothing, a campaign that fails to
start. So the editor rewrites them together with the block.

Two rules keep the rewrite honest:

**Whole names only, longest first.** Unit types contain spaces (``Ent Catapult``,
``Beorning Shapeshifters``), so this cannot tokenise the way
:mod:`unittransfer.luascan` does; it matches the literal name with identifier
boundaries on both ends. That alone would let ``Catapult`` match the tail of
``Ent Catapult`` and corrupt it, so every match is checked against the mod's
OTHER type names first: if a longer type also covers that spot, the spot belongs
to that unit and is left alone.

**Exact case rewrites, different case reports.** The engine does not care about
case, but other namespaces share these files - ``ballista`` is a unit type AND a
descr_engines entry - and rewriting case-insensitively would rename things that
are not this unit. So only exact matches are rewritten, and near-misses that
differ only in case are reported so the user can look at them.

Files are read and written as latin-1, which round-trips every byte, so a script
with characters from any codepage comes back byte-identical apart from the name
that changed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import luascan

# The identifier characters a name may not sit against. Same shape as the token
# rule the rest of the tool uses, so "gondor_archer" is not found inside
# "gondor_archer_heavy" and a name is never matched inside a longer path.
_BOUND = r"[A-Za-z0-9_]"

# Folders that hold copies rather than the mod the game runs.
SKIP_DIRS = {".git", ".svn", "__pycache__", "node_modules", "backup", "backups"}

# `data/text/` is UTF-16 and keyed by `dictionary`, not by `type` - nothing in it
# names a unit type, and reading it as latin-1 would only waste time.
SKIP_DATA_SUBDIRS = {"text"}

# Rewritten by the EDU/EOP layer itself, never here: this module would otherwise
# fight the block edit for the same bytes.
OWNED_ELSEWHERE = {"export_descr_unit.txt"}


@dataclass
class Ref:
    """One place a unit type is named."""
    path: Path
    rel: str            # mod-relative, posix-style - what the user is shown
    line: int           # 1-based
    text: str           # the line itself, stripped
    exact: bool = True  # False -> matched only when case is ignored

    def label(self) -> str:
        return f"{self.rel}:{self.line}"


@dataclass
class RenameResult:
    """What renaming a type would do outside the EDU."""
    refs: List[Ref] = field(default_factory=list)          # rewritten
    case_refs: List[Ref] = field(default_factory=list)     # found, NOT rewritten
    texts: Dict[Path, str] = field(default_factory=dict)   # path -> new content

    @property
    def files(self) -> List[str]:
        return sorted({r.rel for r in self.refs})

    def counts(self) -> List[Tuple[str, int]]:
        """``(file, hits)`` for the files that change, most hits first."""
        per: Dict[str, int] = {}
        for r in self.refs:
            per[r.rel] = per.get(r.rel, 0) + 1
        return sorted(per.items(), key=lambda kv: (-kv[1], kv[0]))


def _read(path: Path) -> str:
    """File as text, byte-for-byte reversible (see the module docstring)."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data.decode("latin-1")


def scan_paths(mod) -> List[Path]:
    """Every file in ``mod`` that could name a unit type, deduplicated.

    ``data/*.txt`` (the definition files), every ``.txt`` under
    ``data/world/`` (the campaigns and the custom battles) and every ``.lua``
    anywhere in the mod.
    """
    data = Path(getattr(mod, "data", mod))
    out: List[Path] = []
    seen: set = set()

    def add(p: Path) -> None:
        key = str(p).lower()
        if key not in seen and p.is_file():
            seen.add(key)
            out.append(p)

    if data.is_dir():
        for p in sorted(data.glob("*.txt")):
            if p.name.lower() not in OWNED_ELSEWHERE:
                add(p)
        world = data / "world"
        if world.is_dir():
            for p in sorted(world.rglob("*.txt")):
                if not any(part.lower() in SKIP_DIRS for part in p.parts):
                    add(p)
    # `Mod.lua_files` is a cached property - finding the scripts is a walk of the
    # whole mod tree (seconds on a big one), and the editor asks for this on every
    # preview, so never call the uncached function when the mod can answer.
    lua = getattr(mod, "lua_files", None)
    for p in (lua if isinstance(lua, list) else luascan.lua_files(mod)):
        add(p)
    return out


def _pattern(name: str) -> re.Pattern:
    return re.compile(rf"(?<!{_BOUND}){re.escape(name)}(?!{_BOUND})")


def _rivals(name: str, all_types: Iterable[str]) -> List[re.Pattern]:
    """Patterns for the other type names this one could be mistaken for a part of.

    Only types that actually *contain* ``name`` can overlap a match of it, so the
    list is nearly always empty and the scan stays one pass per file.
    """
    low = name.lower()
    return [_pattern(t) for t in all_types
            if t.lower() != low and low in t.lower()]


def _covered(text: str, start: int, end: int, rivals: Sequence[re.Pattern]) -> bool:
    """Is this match really part of a LONGER unit type at the same spot?"""
    for rival in rivals:
        for m in rival.finditer(text, max(0, start - 200), min(len(text), end + 200)):
            if m.start() <= start and m.end() >= end and (m.end() - m.start()) > (end - start):
                return True
    return False


def _line_starts(text: str) -> List[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _line_of(starts: List[int], pos: int) -> int:
    import bisect
    return bisect.bisect_right(starts, pos)


def find_refs(mod, unit_type: str, all_types: Optional[Iterable[str]] = None,
              paths: Optional[Sequence[Path]] = None) -> RenameResult:
    """Every reference to ``unit_type`` outside the EDU, with the rewritten text.

    ``texts`` is left empty here - :func:`rename_refs` fills it. This split lets
    the editor show what a rename would touch (and count it) without building the
    new content for files nobody is going to write.
    """
    return _scan(mod, unit_type, unit_type, all_types, paths, rewrite=False)


def rename_refs(mod, old: str, new: str,
                all_types: Optional[Iterable[str]] = None,
                paths: Optional[Sequence[Path]] = None) -> RenameResult:
    """Rewrite ``old`` -> ``new`` everywhere outside the EDU.

    Returns the references found and, per file that changes, its whole new text.
    Nothing is written - the caller backs the files up and writes them.
    """
    return _scan(mod, old, new, all_types, paths, rewrite=bool(new and new != old))


#: the lines that exist only to recruit a unit, so a deleted unit takes them
#: with it: the stock engine refuses a pool naming a unit the EDU has not got
#: (Kirsi's Bigger Map pooled five)
_POOL_LINE = re.compile(r"\s*(recruit_pool|recruit)\s", re.IGNORECASE)
_MERC_LINE = re.compile(r"\s*unit\s", re.IGNORECASE)
MERCS = "descr_mercenaries.txt"


def drop_refs(mod, unit_type: str, all_types: Optional[Iterable[str]] = None,
              paths: Optional[Sequence[Path]] = None
              ) -> Tuple[Dict[Path, str], List[Ref], List[Ref]]:
    """What deleting ``unit_type`` does outside the EDU: ``(texts, dropped,
    left)``. Every recruit / recruit_pool line and every mercenary ``unit``
    line naming it is taken out whole (``texts`` holds each changed file's new
    text); every other place that names it is ``left`` for the caller to judge.
    """
    res = find_refs(mod, unit_type, all_types, paths)
    texts: Dict[Path, str] = {}
    dropped: List[Ref] = []
    left: List[Ref] = []
    by_path: Dict[Path, List[Ref]] = {}
    for r in res.refs:
        by_path.setdefault(r.path, []).append(r)
    for path, refs in by_path.items():
        lines = _read(path).splitlines(keepends=True)
        gone = set()
        for r in refs:
            line = lines[r.line - 1] if r.line <= len(lines) else ""
            pool = (_MERC_LINE if path.name.lower() == MERCS else _POOL_LINE).match(line)
            if pool:
                if r.line not in gone:
                    gone.add(r.line)
                    dropped.append(r)
            else:
                left.append(r)
        if gone:
            texts[path] = "".join(l for i, l in enumerate(lines, 1) if i not in gone)
    return texts, dropped, left


def _scan(mod, old: str, new: str, all_types, paths, rewrite: bool) -> RenameResult:
    res = RenameResult()
    old = (old or "").strip()
    if not old:
        return res
    root = Path(getattr(mod, "root", mod))
    types = list(all_types) if all_types is not None else [
        u.type for u in getattr(mod, "edu").units]
    pat = _pattern(old)
    # the case-blind pass exists only to REPORT: see the module docstring
    ipat = re.compile(pat.pattern, re.IGNORECASE)
    rivals = _rivals(old, types)

    for path in (paths if paths is not None else scan_paths(mod)):
        text = _read(path)
        if not text or old.lower() not in text.lower():
            continue
        rel = (path.relative_to(root).as_posix()
               if path.is_relative_to(root) else path.name)
        starts = _line_starts(text)
        hits: List[Tuple[int, int]] = []
        for m in ipat.finditer(text):
            if _covered(text, m.start(), m.end(), rivals):
                continue
            exact = m.group(0) == old
            ln = _line_of(starts, m.start())
            ref = Ref(path=path, rel=rel, line=ln,
                      text=text[starts[ln - 1]:].split("\n", 1)[0].strip()[:200],
                      exact=exact)
            if exact:
                res.refs.append(ref)
                hits.append((m.start(), m.end()))
            else:
                res.case_refs.append(ref)
        if rewrite and hits:
            out = []
            pos = 0
            for start, end in hits:
                out.append(text[pos:start])
                out.append(new)
                pos = end
            out.append(text[pos:])
            res.texts[path] = "".join(out)
    return res


#: A line that exists only to name the unit, so deleting the unit deletes the
#: line (Pfadfinder-Adam's editor does the same on Delete this unit): a recruit
#: line in a building level, a `unit <type> ...` line of a campaign's armies
#: and garrisons or a battle's, a mercenary pool's `unit <type>, ...`, a
#: rebel faction's `unit <type>`. Anything else naming it (a campaign script,
#: a Lua file, the voice bank, the win conditions) is reported, never cut:
#: taking a line out of a script can change what the script does.
_REMOVABLE = (
    ("export_descr_buildings.txt", re.compile(r'^\s*(recruit_pool|recruit|retrain_pool|retrain)\s+"(?P<n>[^"]+)"', re.I)),
    # the comma is optional: the base game's own pools leave it out on most lines
    ("descr_mercenaries.txt", re.compile(r"^\s*unit\s+(?P<n>[^,]+?)\s*(,|\s+exp\b)", re.I)),
    ("descr_rebel_factions.txt", re.compile(r"^\s*unit\s+(?P<n>.+?)\s*(;.*)?$", re.I)),
)
_UNIT_LINE = re.compile(r"^\s*unit\s+(?P<n>.+?)\s+(exp|soldiers|armour|weapon_lvl)\b", re.I)


@dataclass
class RemoveResult:
    """What deleting a unit takes out of the other files, and what it leaves."""
    removed: List[Ref] = field(default_factory=list)    # lines taken out
    kept: List[Ref] = field(default_factory=list)       # still name it: check by hand
    alone: List[Ref] = field(default_factory=list)      # removed, and it was an army's only unit
    texts: Dict[Path, str] = field(default_factory=dict)

    def counts(self) -> List[Tuple[str, int]]:
        per: Dict[str, int] = {}
        for r in self.removed:
            per[r.rel] = per.get(r.rel, 0) + 1
        return sorted(per.items(), key=lambda kv: (-kv[1], kv[0]))


def _removable(rel: str, line: str, unit_type: str) -> bool:
    name = rel.rsplit("/", 1)[-1].lower()
    want = unit_type.strip().lower()
    for fname, pat in _REMOVABLE:
        if name == fname:
            m = pat.match(line)
            return bool(m and m.group("n").strip().lower() == want)
    if "/world/" in "/" + rel.lower() and name.startswith("descr_"):
        m = _UNIT_LINE.match(line)
        return bool(m and m.group("n").strip().lower() == want)
    return False


def remove_refs(mod, unit_type: str, all_types: Optional[Iterable[str]] = None,
                paths: Optional[Sequence[Path]] = None) -> RemoveResult:
    """Every line outside the EDU that exists only to name ``unit_type``, taken
    out; the other places that name it listed in ``kept``. Each file's new text
    is in ``texts``; nothing is written (``write_refs`` does, with its backup)."""
    res = RemoveResult()
    found = find_refs(mod, unit_type, all_types, paths)
    by_path: Dict[Path, List[Ref]] = {}
    for r in found.refs:
        by_path.setdefault(r.path, []).append(r)
    res.kept.extend(found.case_refs)
    for path, refs in by_path.items():
        text = _read(path)
        lines = text.split("\n")
        drop = set()
        for r in refs:
            raw = lines[r.line - 1] if 0 < r.line <= len(lines) else ""
            if _removable(r.rel, raw, unit_type):
                drop.add(r.line - 1)
                res.removed.append(r)
            else:
                res.kept.append(r)
        if not drop:
            continue
        # an army or garrison left with no unit: said, since the game may refuse it
        for i in sorted(drop):
            if not _UNIT_LINE.match(lines[i]):
                continue
            j, k = i - 1, i + 1
            while j >= 0 and (j in drop or not lines[j].strip()):
                j -= 1
            while k < len(lines) and (k in drop or not lines[k].strip()):
                k += 1
            before = lines[j].strip().lower() if j >= 0 else ""
            after = lines[k] if k < len(lines) else ""
            if before.startswith("army") and not _UNIT_LINE.match(after):
                res.alone.extend(r for r in refs if r.line - 1 == i)
        res.texts[path] = "\n".join(l for i, l in enumerate(lines) if i not in drop)
    return res


def write_refs(texts: Dict[Path, str], backup_root: Path, manifest: dict) -> List[str]:
    """Write the rewritten files, backing each one up first.

    Uses the same ``ext_backed_up`` manifest shape :mod:`unittransfer.eop` uses
    for the M2TWEOP files, because these are in the same position: some of them
    (the ``.lua`` scripts) sit outside ``data/``, so the usual data-relative undo
    list cannot describe them. ``unittransfer.eop.restore_split`` puts them back.
    """
    from .logutil import file_op

    backed = manifest.setdefault("ext_backed_up", [])
    written: List[str] = []
    for path, text in texts.items():
        n = len(backed)
        bpath = backup_root / "refs" / f"{n:03d}_{path.name}"
        bpath.parent.mkdir(parents=True, exist_ok=True)
        try:
            bpath.write_bytes(path.read_bytes())
        except OSError:
            continue                     # unreadable -> do not risk writing it
        backed.append({"path": str(path), "backup": str(bpath)})
        file_op("BACKUP", path, f"unit-name reference -> {bpath}")
        # bytes, not write_text: on Windows that turns each "\r\n" the file
        # was read with into "\r\r\n"
        path.write_bytes(text.encode("latin-1"))
        file_op("WRITE", path, f"unit name rewritten, {len(text)} chars")
        written.append(str(path))
    return written
