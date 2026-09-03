"""The campaign map's models and textures - the strat-map half of the cleanup.

:mod:`unittransfer.bmdb` does this for ``battle_models.modeldb`` and
``data/unit_models``: work out which entries nothing references, which files no
entry names, and move both out of the mod without deleting anything. This module
is the same job on the other model tree - ``descr_model_strat.txt`` and
``data/models_strat`` - and it is a job worth doing for the same reason. A big
overhaul carries generals, agents, heroes and faction symbols that were tried,
replaced and never taken out, and the strat map is where an unused ``.CAS`` and
its 2 MB texture sit unnoticed, because nothing in game ever draws them.

**What names a strat model type** (``type <name>`` in ``descr_model_strat.txt``):

  * ``descr_character.txt`` - ``strat_model`` lines, the overwhelming majority:
    every general, heir, leader, custom character and agent a faction fields;
  * ``model_sprite`` inside ``descr_model_strat.txt`` itself, which may name
    another *type* rather than a distance and so is a real cross-reference;
  * **every ``.lua`` script in the mod** - M2TWEOP spawns characters and swaps
    strat models from Lua, and none of it is written down in a ``.txt``
    (:mod:`unittransfer.luascan`);
  * anything else: any ``data/descr_*.txt``, and every campaign's
    ``descr_strat.txt`` / ``campaign_script.txt``, that merely *mentions* the
    name counts too, bar :data:`DESCR_SKIP`. Over-cautious on purpose - a false
    "still used" costs nothing, a false "unused" silently breaks a mod.

**What names a file under ``data/models_strat``**:

  * the ``texture`` / ``model_flexi*`` / ``shadow_model_flexi`` lines of the
    entries above;
  * ``descr_sm_factions.txt`` - ``symbol`` and ``rebel_symbol``, the ``.CAS``
    each faction's map banner is;
  * ``descr_sm_resources.txt`` - ``item`` and the file-level ``mine``, the little
    models scattered over the map;
  * ``descr_cultures.txt`` - settlements, forts, ports, watchtowers;
  * again, any other ``descr_*.txt``, campaign file or ``.lua`` that names the
    path, or even just the bare filename.

Rather than a keyword list per file, everything past the entries themselves is
found by looking for the path: a ``models_strat/...`` string is a reference to
that file whoever wrote it and whatever keyword it sits behind, which is what
makes this robust against a mod using a line this module has never heard of.

**``models_strat/residences`` is skipped entirely.** The settlement models live
there, and the game reads a faction's variant of one out of that tree *by
folder*, with nothing naming the file anywhere - so "no file names it" would be
wrong about the whole subtree. It also cannot hold anything unused worth finding:
a settlement nobody can see is the first thing a player notices.

Nothing is deleted outright. Everything ticked moves to an export folder in the
mod's own layout, every rewritten file is backed up first, and 🕑 Log → Undo puts
it all back - the same contract :mod:`unittransfer.bmdb` makes.
"""
from __future__ import annotations

import logging
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import config, edit, keyblock as kb, luascan
from .logutil import counted, file_op, fingerprint, log
from .mod import Mod

#: ``descr_model_strat.txt`` is latin-1 like every other game text file, and it
#: is read and written through :mod:`unittransfer.keyblock` so a mod that mixes
#: CRLF and lone LF comes back byte for byte the way it went in.
ENCODING = "latin-1"

#: Relative to ``data/``. The file is ``descr_model_strat.txt`` - singular - in
#: every version of the game; the plural spelling is a common slip and a mod that
#: ships it would be one the game ignores, so only the real name is read.
REL = "descr_model_strat.txt"

#: The tree this module cleans, relative to ``data/``.
MODELS_DIR = "models_strat"

#: The one subtree left alone - see the module docstring.
SKIP_SUBDIR = "residences"

#: Keywords whose value is a file under ``models_strat``. ``texture`` and
#: ``texture_no_move`` put a faction in front of the path; the model keywords put
#: a distance after it. Both shapes are handled by taking the one comma-separated
#: field that looks like a path.
FILE_KEYS = ("texture", "texture_no_move", "model_flexi", "model_flexi_m",
             "model_flexi_c", "model_flexi_a", "shadow_model_flexi", "model_mesh")

#: data/descr_*.txt files the "somebody still mentions it" net skips.
DESCR_SKIP = {
    # Where the types are *defined*: every entry names itself on its `type` line,
    # so including this would mark all of them mentioned and nothing could ever
    # be removed. Its real cross-references (`model_sprite <other type>`) are
    # read structurally instead - see `entry_users`.
    REL,
}

#: The campaign files that can name a strat model, relative to each campaign
#: folder. Same two :mod:`unittransfer.bmdb` reads, for the same reason: they
#: are the scripts that create characters.
CAMPAIGN_FILES = ("descr_strat.txt", "campaign_script.txt")

#: Same identifier shape :mod:`unittransfer.bmdb` and :mod:`unittransfer.luascan`
#: tokenise with, so a name matches identically wherever it turns up.
_TOKEN_RE = re.compile(r"[a-z0-9_.\-]+")

#: A path into the strat-model tree, however it was written: with or without the
#: leading ``data/``, either slash, any of the extensions the tree holds.
_PATH_RE = re.compile(
    r"(?:data[/\\])?" + MODELS_DIR + r"[/\\][A-Za-z0-9_./\\ -]*?"
    r"\.(?:cas|tga|dds|txt|ini)", re.IGNORECASE)

_TYPE_RE = re.compile(r"^\s*type\s+(\S+)", re.IGNORECASE)
_STRAT_MODEL_RE = re.compile(r"^\s*strat_model\s+(\S+)", re.IGNORECASE | re.MULTILINE)

#: Name of the file the removed blocks are written to in the export folder.
#: Deliberately NOT descr_model_strat.txt: the export mirrors the mod's own tree
#: so it can be pasted back, and a file with that name would overwrite the real
#: one the next time somebody did exactly that.
EXPORT_FILE_NAME = "removed_model_strat.txt"
UNUSED_SUBDIR = "unused_files"          # files no entry mentions at all
README_NAME = "README.txt"

Progress = Optional[Callable[[int, str], None]]


def _reporter(progress: Progress) -> Callable[[float, str], None]:
    """Wrap an optional sink so the callers below can report unconditionally."""
    def report(pct: float, label: str) -> None:
        if progress is None:
            return
        try:
            progress(max(0, min(100, int(pct))), label)
        except Exception:                       # a sink must never break the job
            logging.getLogger(__name__).debug("progress sink raised", exc_info=True)
    return report


def _read(path: Path) -> str:
    try:
        return kb.read_text(path, ENCODING)
    except OSError:
        return ""


def _strip_comments(text: str) -> str:
    """``text`` with ``;`` comments blanked out, newlines and offsets preserved.

    Blanked rather than deleted so a line number or a span computed on the result
    still points at the same place in the file the user will open.
    """
    out = []
    for line in text.splitlines(keepends=True):
        i = line.find(";")
        out.append(line if i < 0 else line[:i] + re.sub(r"[^\r\n]", " ", line[i:]))
    return "".join(out)


def norm(rel: str) -> str:
    """A models_strat path as the one string every net compares against.

    Lower-cased, forward slashes, no leading ``data/`` and no leading slash - so
    ``data\\models_strat\\Textures\\X.TGA`` and ``models_strat/textures/x.tga``
    are recognised as the one file they are.
    """
    p = (rel or "").strip().replace("\\", "/").lstrip("./").lower()
    if p.startswith("data/"):
        p = p[5:]
    return p


def _skipped(rel: str) -> bool:
    """Is this path inside the one subtree the whole module leaves alone?"""
    return norm(rel).startswith(f"{MODELS_DIR}/{SKIP_SUBDIR}/")


#: Longest first, so ``x.tga.dds`` is recognised as one suffix and not as ``.dds``
#: on a file called ``x.tga``.
_TEX_EXT = (".tga.dds", ".tga", ".dds")


def texture_siblings(rel: str) -> List[str]:
    """Every spelling of ONE texture: ``x.tga``, ``x.tga.dds`` and ``x.dds``.

    This is the rule that stops the cleanup being a disaster. A line writes
    ``models_strat/textures/durin.tga`` and the mod ships ``durin.tga.dds``
    beside it (or instead of it): M2TW prefers the DDS and loads it for a name
    ending ``.tga``, which is why every texture optimiser in the scene leaves the
    tree looking like that. Divide and Conquer has 541 such files, 387 MB of
    them, and every single one would have looked like a file nothing names.

    So a reference to any one of the three counts as a reference to all three,
    and removing an entry takes all three with it. Non-textures - the ``.CAS``
    meshes - have no second spelling and come back as themselves.
    """
    p = norm(rel)
    for ext in _TEX_EXT:
        if p.endswith(ext):
            stem = p[:-len(ext)]
            return [stem + e for e in (".tga", ".tga.dds", ".dds")]
    return [p]


def expand(rels) -> set:
    """A set of paths widened to every spelling of each - see :func:`texture_siblings`."""
    out: set = set()
    for rel in rels:
        out.update(texture_siblings(rel))
    return out


def on_disk_rel(mod: Mod, rel: str) -> str:
    """``rel`` with the capitalisation the file really has on disk.

    Every comparison in this module runs on lower-cased paths, because a mod
    writes ``models_strat/dead.CAS`` on one line and ``models_strat/Dead.cas`` on
    the next and means the same file. The EXPORT is different: it is a mirror of
    the mod that has to be copyable back over it, so a file must land there under
    its own name and not under the lower-cased one the matching used. Windows
    would forgive it; a mod pasted back on a case-sensitive filesystem would not.
    """
    src = mod.data / rel
    try:
        return src.resolve().relative_to(mod.data.resolve()).as_posix()
    except (OSError, ValueError):
        return rel


# ---------------------------------------------------------------------------
# the file


@dataclass
class StratEntry:
    """One ``type`` block of ``descr_model_strat.txt``, kept verbatim."""
    name: str
    raw: str                                        # the block exactly as written
    line: int = 0                                   # 1-based, for "where is it"
    skeleton: str = ""
    files: List[Tuple[str, str]] = field(default_factory=list)   # (keyword, path)
    factions: List[str] = field(default_factory=list)            # texture factions
    sprite_of: str = ""                             # a `model_sprite <other type>`

    @property
    def models(self) -> List[str]:
        return [p for k, p in self.files if k != "texture" and k != "texture_no_move"]

    @property
    def textures(self) -> List[str]:
        return [p for k, p in self.files if k in ("texture", "texture_no_move")]

    def paths(self) -> List[str]:
        """Every file this entry names, deduplicated, in the order written."""
        return list(dict.fromkeys(p for _k, p in self.files))


@dataclass
class StratFile:
    preamble: str = ""
    entries: List[StratEntry] = field(default_factory=list)

    def by_name(self) -> Dict[str, StratEntry]:
        """``lower-case name -> entry``; the FIRST wins, as the game's reader does."""
        out: Dict[str, StratEntry] = {}
        for e in self.entries:
            out.setdefault(e.name.lower(), e)
        return out

    def to_text(self) -> str:
        return self.preamble + "".join(e.raw for e in self.entries)

    def without(self, names: Sequence[str]) -> str:
        """The file's text with the named blocks spliced out, nothing else touched."""
        drop = {str(n).lower() for n in names}
        return self.preamble + "".join(e.raw for e in self.entries
                                       if e.name.lower() not in drop)

    def only(self, names: Sequence[str]) -> str:
        """Just the named blocks, in file order - what the export folder gets."""
        keep = {str(n).lower() for n in names}
        return "".join(e.raw for e in self.entries if e.name.lower() in keep)


def _entry_paths(body: str) -> Tuple[List[Tuple[str, str]], List[str], str]:
    """The files, texture factions and sprite cross-reference of one block."""
    files: List[Tuple[str, str]] = []
    factions: List[str] = []
    sprite_of = ""
    for line in _strip_comments(body).splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        key = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if key == "model_sprite":
            # `model_sprite <distance>, ...` generates a sprite; anything else in
            # that slot is the name of a type defined EARLIER in this file, whose
            # sprite this one borrows - a genuine reference between two entries.
            head = rest.split(",")[0].strip()
            if head and not head[0].isdigit():
                sprite_of = head
            continue
        if key not in FILE_KEYS:
            continue
        fields = [f.strip() for f in rest.split(",")]
        for i, f in enumerate(fields):
            if not f:
                continue
            if _PATH_RE.fullmatch(f) or MODELS_DIR + "/" in f.replace("\\", "/").lower():
                files.append((key, norm(f)))
                # `texture <faction>, <path>` - whatever came before the path on a
                # texture line is the faction it dresses
                if key.startswith("texture") and i and fields[0]:
                    factions.append(fields[0].lower())
                break
    return files, list(dict.fromkeys(factions)), sprite_of


def parse_text(text: str) -> StratFile:
    """Split the file into its ``type`` blocks, keeping every byte of each one."""
    text = kb.without_bom(text)
    lines = text.splitlines(keepends=True)
    starts: List[int] = []
    for i, line in enumerate(lines):
        if _TYPE_RE.match(line.split(";", 1)[0]):
            starts.append(i)
    if not starts:
        return StratFile(preamble=text)
    out = StratFile(preamble="".join(lines[:starts[0]]))
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        raw = "".join(lines[start:end])
        m = _TYPE_RE.match(lines[start].split(";", 1)[0])
        name = m.group(1) if m else ""
        files, factions, sprite_of = _entry_paths(raw)
        skel = ""
        for line in _strip_comments(raw).splitlines():
            p = line.split(None, 1)
            if p and p[0].lower() == "skeleton" and len(p) > 1:
                skel = p[1].strip()
                break
        out.entries.append(StratEntry(name=name, raw=raw, line=start + 1,
                                      skeleton=skel, files=files, factions=factions,
                                      sprite_of=sprite_of))
    return out


def parse_file(path: str | Path) -> StratFile:
    p = Path(path)
    if not p.is_file():
        return StratFile()
    return parse_text(_read(p))


def strat_file(mod: Mod) -> StratFile:
    """The mod's parsed ``descr_model_strat.txt``, read once per Mod object.

    A one-line alias for :attr:`Mod.strat_models` so this module reads the file
    the same way it reads every other - and so a write goes on invalidating it
    through :meth:`Mod.drop_caches` rather than through a cache only this file
    knows about.
    """
    return mod.strat_models


# ---------------------------------------------------------------------------
# who references what


def campaign_files(mod: Mod) -> List[Path]:
    """Every campaign's ``descr_strat.txt`` and ``campaign_script.txt``."""
    base = mod.data / "world" / "maps" / "campaign"
    if not base.is_dir():
        return []
    out: List[Path] = []
    try:
        for camp in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if not camp.is_dir():
                continue
            out += [camp / n for n in CAMPAIGN_FILES if (camp / n).is_file()]
    except OSError:
        pass
    return out


def _scanned_files(mod: Mod) -> List[Path]:
    """Every mod file this module reads looking for a name or a path.

    One list, used by both nets, so "which files were consulted" has a single
    answer the dialog can print rather than two that could drift apart.
    """
    out = [p for p in sorted(mod.data.glob("descr_*.txt"))
           if p.name.lower() not in DESCR_SKIP]
    return out + campaign_files(mod)


def entry_users(mod: Mod) -> Dict[str, Dict[str, List[str]]]:
    """``type name -> {kind: [referrers]}`` for the references we can name exactly.

    Two kinds, because those are the two places a strat model type is *used*
    rather than merely mentioned: ``character`` is a ``strat_model`` line in
    ``descr_character.txt``, and ``sprite`` is another entry in this same file
    borrowing this one's sprite. Everything else - a name in some other
    ``descr_*.txt``, a name in a Lua script - is a *mention*, handled by
    :func:`name_mentions`, because we cannot say what it is doing there.
    """
    out: Dict[str, Dict[str, List[str]]] = {}

    def add(name: str, kind: str, who: str) -> None:
        if not name:
            return
        slot = out.setdefault(name.lower(), {"character": [], "sprite": []})
        if who not in slot[kind]:
            slot[kind].append(who)

    text = _strip_comments(_read(mod.data / "descr_character.txt"))
    block = ""
    for line in text.splitlines():
        parts = line.split(None, 1)
        if parts and parts[0].lower() == "type" and len(parts) > 1:
            block = parts[1].strip()
        elif parts and parts[0].lower() == "strat_model" and len(parts) > 1:
            add(parts[1].split()[0], "character",
                f"character:{block or 'descr_character.txt'}")
    for e in strat_file(mod).entries:
        if e.sprite_of:
            add(e.sprite_of, "sprite", f"sprite:{e.name}")
    return out


def _descr_tokens(mod: Mod) -> Dict[str, str]:
    """``token -> the file it appeared in``, for the "somebody names it" net."""
    out: Dict[str, str] = {}
    for path in _scanned_files(mod):
        text = _read(path).lower()
        if not text:
            continue
        label = path.name if path.parent == mod.data else f"{path.parent.name}/{path.name}"
        for tok in set(_TOKEN_RE.findall(text)):
            out.setdefault(tok, label)
    return out


def name_mentions(mod: Mod,
                  report: Optional[Callable[[float, str], None]] = None
                  ) -> Dict[str, dict]:
    """``token -> {"file", "lua", "in_comment"}`` - the whole safety net.

    Exactly the shape :func:`unittransfer.bmdb.name_mentions` builds, and for the
    same reason: membership here is what keeps an entry off the unused list AND
    what makes :func:`plan_cleanup` refuse to remove it, so one dictionary is
    both the explanation and the guard. A definition file wins the label when
    both a ``.txt`` and a script name a token - it is the more concrete answer to
    "why is this still here" - and the Lua hit stays on the row either way.
    """
    if "lua_tokens" not in mod.__dict__:
        mod.__dict__["lua_tokens"] = luascan.scan(mod, report)
    elif report:
        report(1.0, "")
    out: Dict[str, dict] = {}
    for tok, hit in mod.lua_tokens.items():
        out[tok] = {"file": hit.label(), "lua": True, "in_comment": hit.in_comment}
    for tok, where in _descr_tokens(mod).items():
        row = out.get(tok)
        if row is None:
            out[tok] = {"file": where, "lua": False, "in_comment": False}
        else:
            row["file"] = where
    return out


def file_users(mod: Mod) -> Dict[str, List[str]]:
    """``normalised models_strat path -> who names it``.

    Found by looking for the PATH rather than by a keyword list per file: a
    ``models_strat/...`` string is a reference to that file whoever wrote it,
    which is what keeps this right for a mod using a line nobody here has heard
    of. Entries are credited by name; everything else by its file.
    """
    out: Dict[str, List[str]] = {}

    def add(rel: str, who: str) -> None:
        rel = norm(rel)
        if not rel:
            return
        who_list = out.setdefault(rel, [])
        if who not in who_list:
            who_list.append(who)

    for e in strat_file(mod).entries:
        for p in e.paths():
            add(p, f"entry:{e.name}")
    for path in _scanned_files(mod) + list(mod.lua_files):
        text = _read(path)
        if MODELS_DIR not in text and MODELS_DIR.upper() not in text.upper():
            continue
        try:
            label = path.relative_to(mod.root).as_posix()
        except ValueError:
            label = path.name
        for hit in _PATH_RE.findall(text):
            add(hit, label)
    return out


def basename_mentions(mod: Mod) -> Dict[str, str]:
    """``lower-case filename -> where it was named``, the second net for files.

    A script that builds a path by pasting a folder onto a name never produces a
    ``models_strat/...`` string for :func:`file_users` to find, but it does
    produce the filename, and :mod:`unittransfer.luascan` already has every token
    of every script. Keeping a file alive because its bare name turns up
    somewhere is over-cautious, which is the correct direction to be wrong in.
    """
    out: Dict[str, str] = {}
    for tok, hit in mod.lua_tokens.items():
        if "." in tok:
            out.setdefault(tok, hit.label())
    for tok, where in _descr_tokens(mod).items():
        if "." in tok:
            out[tok] = where
    return out


# ---------------------------------------------------------------------------
# the audit


def _describe(users: Dict[str, Dict[str, List[str]]], name: str) -> List[str]:
    slot = users.get(name.lower())
    if not slot:
        return []
    return list(dict.fromkeys(slot["character"] + slot["sprite"]))


def orphan_files(mod: Mod, referenced: set, named: Dict[str, str],
                 report: Optional[Callable[[float, str], None]] = None) -> List[dict]:
    """Files under ``data/models_strat`` nothing names - ``residences`` excluded.

    Walked a top-level folder at a time so the bar can say where it is: a mod
    with faction settlement variants has thousands of files down there, and one
    silent multi-second pause is exactly what the bar exists to avoid.
    """
    base = mod.data / MODELS_DIR
    if not base.is_dir():
        return []
    try:
        tops = sorted(base.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        tops = []
    tops = [p for p in tops if p.name.lower() != SKIP_SUBDIR]
    out: List[dict] = []
    total = len(tops) or 1
    for i, top in enumerate(tops):
        if report:
            report(i / total, top.name)
        for p in (top.rglob("*") if top.is_dir() else [top]):
            if not p.is_file():
                continue
            rel = p.relative_to(mod.data).as_posix()
            if norm(rel) in referenced:
                continue
            base_hit = next((named[n] for n in
                             (x.rsplit("/", 1)[-1] for x in texture_siblings(p.name))
                             if n in named), "")
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            out.append({"rel": rel, "size": size, "named_in": base_hit})
    if report:
        report(1.0, "")
    # Anything held alive only by its bare name is reported but never offered:
    # it is the same "somebody mentions it" rule the entries follow.
    out.sort(key=lambda x: x["rel"].lower())
    return out


def audit(mod: Mod, scan_orphans: bool = True, progress: Progress = None) -> dict:
    """Everything the strat-map cleanup dialog needs, in one pass over the mod."""
    say = _reporter(progress)
    say(4, f"reading {REL}")
    sf = strat_file(mod)
    entries = sf.by_name()
    say(10, "reading descr_character.txt")
    users = entry_users(mod)
    say(14, "reading data/descr_*.txt and the mod's .lua scripts")
    mentions = name_mentions(
        mod, lambda frac, where: say(14 + 16 * frac,
                                     f"reading .lua scripts{' - ' + where if where else ''}"))
    lua_count = len(mod.lua_files)

    say(34, "listing the files every entry names")
    refs = file_users(mod)
    named = basename_mentions(mod)

    say(44, f"checking {len(entries)} strat models for references")
    unused: List[dict] = []
    unused_names: set = set()
    mentioned: List[dict] = []
    seen: set = set()
    for e in sf.entries:
        key = e.name.lower()
        if key in seen:
            continue                    # a duplicated name is one piece of work
        seen.add(key)
        who = _describe(users, e.name)
        if who:
            continue
        row = mentions.get(key)
        if row:
            mentioned.append({"entry": e.name, "file": row["file"],
                              "lua": row["lua"], "in_comment": row["in_comment"]})
            continue
        unused_names.add(key)
        files = e.paths()
        unused.append({
            "entry": e.name, "skeleton": e.skeleton, "line": e.line,
            "models": len(e.models), "skins": len(set(e.textures)),
            "files": files,
            "on_disk": sum(1 for f in files if (mod.data / f).is_file()),
            "bytes": sum((mod.data / f).stat().st_size
                         for f in files if (mod.data / f).is_file()),
        })

    say(58, f"walking data/{MODELS_DIR}")
    orphans = orphan_files(
        mod, expand(refs), named,
        lambda frac, where: say(58 + 38 * frac,
                                f"walking data/{MODELS_DIR}{'/' + where if where else ''}"),
    ) if scan_orphans else []
    # Named-only files are listed apart: the dialog shows them as "kept because",
    # never as something to tick.
    held = [o for o in orphans if o["named_in"]]
    orphans = [o for o in orphans if not o["named_in"]]
    say(100, "done")

    out = {
        "mod": mod.name,
        "root": str(mod.root),
        "file": REL,
        "has_file": (mod.data / REL).is_file(),
        "entry_count": len(sf.entries),
        "name_count": len(entries),
        "unused": unused,
        "mentioned": mentioned,
        "orphans": orphans,
        "orphan_bytes": sum(o["size"] for o in orphans),
        "held_files": held[:400],
        "held_file_count": len(held),
        "referenced_files": len(refs),
        "skipped_dir": f"{MODELS_DIR}/{SKIP_SUBDIR}",
        "scanned": [p.name if p.parent == mod.data else f"{p.parent.name}/{p.name}"
                    for p in _scanned_files(mod)],
        "lua_files": lua_count,
        "lua_kept": [m for m in mentioned if m.get("lua")],
    }
    _log_audit(mod, out)
    return out


def _log_audit(mod: Mod, a: dict) -> None:
    """What the scan looked at and what it concluded, in full.

    The cleanup is a job that removes things, so "what got detected" has to be
    readable afterwards from the log alone - a broken mod can just send it.
    """
    log.info("STRAT  audit %s: %d entries (%d names), %d unused, %d mentioned only, "
             "%d orphan file(s) totalling %d bytes, %d .lua scanned",
             mod.name, a["entry_count"], a["name_count"], len(a["unused"]),
             len(a["mentioned"]), len(a["orphans"]), a["orphan_bytes"], a["lua_files"])
    for u in a["unused"]:
        log.info("  unused  %-32s %d file(s), %d on disk", u["entry"],
                 len(u["files"]), u["on_disk"])
    for m in a["mentioned"][:200]:
        log.info("  kept    %-32s named in %s%s", m["entry"], m["file"],
                 " (in a comment)" if m["in_comment"] else "")


def overview(mod: Mod, progress: Progress = None) -> dict:
    """The browse list: every strat model, with who uses it and what it names."""
    say = _reporter(progress)
    say(5, f"reading {REL}")
    sf = strat_file(mod)
    say(25, "reading descr_character.txt")
    users = entry_users(mod)
    say(45, "reading data/descr_*.txt and the mod's .lua scripts")
    mentions = name_mentions(
        mod, lambda frac, where: say(45 + 40 * frac,
                                     f"reading .lua scripts{' - ' + where if where else ''}"))
    say(90, "counting")
    counts: Dict[str, int] = {}
    for e in sf.entries:
        counts[e.name.lower()] = counts.get(e.name.lower(), 0) + 1
    rows = []
    seen: set = set()
    for e in sf.entries:
        key = e.name.lower()
        if key in seen:
            continue
        seen.add(key)
        who = _describe(users, e.name)
        row = mentions.get(key) if not who else None
        rows.append({
            "name": e.name, "line": e.line, "skeleton": e.skeleton,
            "models": len(e.models), "skins": len(set(e.textures)),
            "factions": e.factions[:8], "faction_count": len(e.factions),
            "used_by": who[:24], "use_count": len(who),
            "unused": not who and not row,
            "mentioned_in": row["file"] if row else "",
            "mentioned_in_lua": bool(row and row["lua"]),
            "files": e.paths(),
            "missing": [f for f in e.paths() if not (mod.data / f).is_file()],
        })
    say(100, "done")
    return {"mod": mod.name, "file": REL, "has_file": (mod.data / REL).is_file(),
            "count": len(sf.entries), "names": len(rows), "entries": rows}


def entry_detail(mod: Mod, name: str) -> dict:
    """One entry, with its block verbatim - what the read-only card shows."""
    e = strat_file(mod).by_name().get((name or "").lower())
    if e is None:
        return {"error": f"no strat model {name!r} in {mod.name}"}
    users = _describe(entry_users(mod), e.name)
    return {"mod": mod.name, "name": e.name, "line": e.line, "skeleton": e.skeleton,
            "raw": e.raw, "factions": e.factions,
            "files": [{"rel": p, "kind": k,
                       "exists": (mod.data / p).is_file()} for k, p in e.files],
            "used_by": users}


# ---------------------------------------------------------------------------
# cleanup


@dataclass
class CleanupRequest:
    target: str                                            # where the assets go
    entries: List[str] = field(default_factory=list)       # type names to remove
    orphans: List[str] = field(default_factory=list)       # data-relative files
    keep_shared_files: bool = True             # never move a file a kept entry uses


def cleanup_request_from_dict(d: dict) -> CleanupRequest:
    return CleanupRequest(
        target=(d.get("target") or "").strip(),
        entries=[str(x) for x in (d.get("entries") or []) if str(x).strip()],
        orphans=[str(x).replace("\\", "/") for x in (d.get("orphans") or [])],
        keep_shared_files=bool(d.get("keep_shared_files", True)),
    )


@dataclass
class CleanupPlan:
    mod: Mod
    request: CleanupRequest
    target: Optional[Path] = None
    entry_deletes: List[str] = field(default_factory=list)
    strat_text: str = ""                       # "" = descr_model_strat.txt is not rewritten
    exports: List[Tuple[Path, str]] = field(default_factory=list)   # (src abs, rel in export)
    deletes: List[str] = field(default_factory=list)                # rel under data/
    kept_files: List[str] = field(default_factory=list)             # shared, left alone
    orphan_count: int = 0
    orphan_bytes: int = 0
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def file_touched(self) -> bool:
        return bool(self.entry_deletes)

    def summary(self) -> str:
        lines = [f"clean up {self.mod.name}'s {REL}"]
        lines += ["  " + c for c in self.changes]
        lines += ["  ! " + w for w in self.warnings]
        return "\n".join(lines)


def _resolve_target(mod: Mod, raw: str) -> Tuple[Optional[Path], str]:
    """The export folder as an absolute path, refusing anywhere inside the mod."""
    if not raw:
        return None, "choose a folder to move the unused assets into"
    try:
        target = Path(raw).expanduser().resolve()
    except OSError as exc:
        return None, f"bad destination: {exc}"
    if target == mod.root.resolve() or mod.root.resolve() in target.parents:
        return None, (f"'{target}' is inside {mod.name} - pick a folder outside the mod, "
                      "otherwise the files never actually leave it")
    if target.exists() and not target.is_dir():
        return None, f"'{target}' is a file, not a folder"
    return target, ""


def plan_cleanup(mod: Mod, req: CleanupRequest) -> CleanupPlan:
    """Work out exactly what a strat-map cleanup would remove, move and rewrite."""
    plan = CleanupPlan(mod=mod, request=req)
    target, err = _resolve_target(mod, req.target)
    plan.target = target
    if err:
        plan.errors.append(err)

    sf = strat_file(mod)
    entries = sf.by_name()
    # Re-checked against the mod rather than trusted: a scan can be older than the
    # mod it describes, and a request can arrive from a saved selection. This is
    # the last line of defence, not a duplicate of the audit - the audit decides
    # what to OFFER, this decides what may actually be written.
    users = entry_users(mod)
    mentions = name_mentions(mod)

    wanted: List[str] = []
    for raw in req.entries:
        key = raw.lower()
        e = entries.get(key)
        if e is None:
            plan.warnings.append(f"{raw} is not in {REL} any more - skipped")
            continue
        who = _describe(users, e.name)
        if who:
            plan.warnings.append(
                f"{e.name} is used by {', '.join(who[:3])} - kept")
            continue
        row = mentions.get(key)
        if row:
            plan.warnings.append(
                f"{e.name} is named in {row['file']} - kept")
            continue
        if key not in [w.lower() for w in wanted]:
            wanted.append(e.name)
    plan.entry_deletes = wanted

    if wanted:
        plan.strat_text = sf.without(wanted)
        plan.changes.append(
            f"{len(wanted)} strat model{'' if len(wanted) == 1 else 's'} removed from {REL}")

    # ---- the files those entries name, minus anything a kept entry still uses.
    # Widened through `texture_siblings` on both sides: an entry that stays and
    # names `x.tga` is keeping `x.tga.dds` alive too, and a removed entry that
    # names `x.tga` takes every spelling of x with it.
    going = {n.lower() for n in wanted}
    still_used: set = set()
    for e in sf.entries:
        if e.name.lower() in going:
            continue
        still_used.update(expand(e.paths()))
    # …and minus anything named outside the file at all (a symbol, a resource, a
    # settlement): the entry may be dead, the .CAS it points at need not be.
    outside = expand(rel for rel, who in file_users(mod).items()
                     if any(not w.startswith("entry:") for w in who))

    seen_files: set = set()
    for name in wanted:
        e = entries[name.lower()]
        for rel in expand(e.paths()):
            if rel in seen_files or _skipped(rel):
                continue
            seen_files.add(rel)
            src = mod.data / rel
            if not src.is_file():
                continue                    # a spelling this mod does not ship
            if req.keep_shared_files and (rel in still_used or rel in outside):
                plan.kept_files.append(rel)
                continue
            plan.exports.append((src, f"data/{on_disk_rel(mod, rel)}"))
            plan.deletes.append(rel)

    # ---- files nothing names at all
    for rel in req.orphans:
        key = norm(rel)
        if not key.startswith(MODELS_DIR + "/") or _skipped(key):
            plan.warnings.append(f"{rel} is not a file this cleanup may touch - skipped")
            continue
        src = mod.data / key
        if not src.is_file():
            plan.warnings.append(f"{rel} is not there any more - skipped")
            continue
        if key in seen_files or key in still_used or key in outside:
            plan.kept_files.append(key)
            continue
        seen_files.add(key)
        plan.exports.append((src, f"{UNUSED_SUBDIR}/data/{on_disk_rel(mod, key)}"))
        plan.deletes.append(key)
        plan.orphan_count += 1
        try:
            plan.orphan_bytes += src.stat().st_size
        except OSError:
            pass

    if plan.orphan_count:
        plan.changes.append(f"{plan.orphan_count} file(s) nothing names moved to "
                            f"{UNUSED_SUBDIR}\\")
    moved = len(plan.deletes) - plan.orphan_count
    if moved:
        plan.changes.append(f"{moved} mesh/texture file(s) of those entries moved out")
    if plan.kept_files:
        plan.changes.append(f"{len(plan.kept_files)} file(s) left in place - something "
                            f"that stays still names them")
    if not plan.changes and not plan.errors:
        plan.warnings.append("nothing is ticked")
    return plan


_README = """{mod} - unused strat-map models and textures
Moved out by the Medieval 2 GUI Toolkit on {when}.

{file}
    The {n} `type` block(s) removed from the mod's {rel}, verbatim.
    Paste them back at the end of that file to restore them.

data\\{dir}\\...
    The meshes and textures those blocks named, in the mod's own layout.
    Copy `data` back over the mod's `data` to put them back.

{unused}\\data\\{dir}\\...
    Files under data/{dir} that nothing in the mod named at all.
    Same layout, one folder deeper so the two kinds stay apart.

Nothing here was deleted from the mod without a backup. The toolkit's
Log → Undo restores the mod exactly, and does not need this folder.
"""


def apply_cleanup(plan: CleanupPlan, progress: Progress = None) -> Dict:
    """Write the cleanup: export first, then rewrite the mod (with backups)."""
    if plan.errors:
        raise ValueError("cannot apply: " + "; ".join(plan.errors))
    mod, target = plan.mod, plan.target
    if target is None:
        raise ValueError("cannot apply: no export folder")
    say = _reporter(progress)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    fingerprint(mod)
    log.info("STRAT  cleanup id=%s  %s -> %s", tid, mod.name, target)
    log.info("  backups -> %s", backup_root)
    _log_cleanup_plan(plan)

    # 1) copy everything out BEFORE touching the mod, so a failure half-way
    #    leaves the mod intact rather than the assets gone and nowhere to be.
    target.mkdir(parents=True, exist_ok=True)
    n_exports = len(plan.exports) or 1
    for i, (src, rel) in enumerate(plan.exports):
        if i % 10 == 0:
            say(2 + 68 * i / n_exports, f"copying files out - {i}/{len(plan.exports)}")
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        file_op("EXPORT", dest, f"copied out of the mod from {src}")
    say(72, "writing the export folder's strat-model file")
    if plan.entry_deletes:
        kb.write_text(target / EXPORT_FILE_NAME,
                      strat_file(mod).only(plan.entry_deletes), ENCODING)
    (target / README_NAME).write_text(
        _README.format(mod=mod.name, when=time.strftime("%Y-%m-%d %H:%M:%S"),
                       file=EXPORT_FILE_NAME, rel=REL, dir=MODELS_DIR,
                       n=len(plan.entry_deletes), unused=UNUSED_SUBDIR),
        encoding="utf-8")

    # 2) now rewrite the mod, backing up every file first
    def backup_and(rel: str) -> Path:
        t = mod.data / rel
        if t.exists():
            bpath = backup_root / "data" / rel
            bpath.parent.mkdir(parents=True, exist_ok=True)
            if not bpath.exists():
                shutil.copy2(t, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", t, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        return t

    if plan.file_touched:
        say(76, f"rewriting {REL}")
        t = backup_and(REL)
        kb.write_text(t, plan.strat_text, ENCODING)
        file_op("WRITE", t, f"{ENCODING}, {len(plan.strat_text)} chars")

    n_deletes = len(plan.deletes) or 1
    for i, rel in enumerate(plan.deletes):
        if i % 10 == 0:
            say(84 + 15 * i / n_deletes, f"taking files out of the mod - {i}/{len(plan.deletes)}")
        t = mod.data / rel
        if t.exists():
            backup_and(rel)                     # backed up, then removed: Undo puts it back
            try:
                t.unlink()
                manifest.setdefault("deleted", []).append(rel)
                file_op("DELETE", t, "taken out of the mod (Undo puts it back)")
            except OSError as exc:
                plan.warnings.append(f"could not remove data/{rel}: {exc}")
                log.warning("  could not remove %s: %s", t, exc)
    say(99, "writing the log entry")

    n = len(plan.entry_deletes)
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "stratmap",
        "action": "cleanup",
        "source": mod.name,
        "source_root": str(mod.root),
        "dest": mod.name,
        "dest_root": str(mod.root),
        "unit_type": "",
        "resolved_type": (f"{n} unused strat model{'' if n == 1 else 's'}"
                          if n else f"{plan.orphan_count} unused file(s)"),
        "options": {"target": str(target)},
        "applied": True,
        "undone": False,
        "note": "",
        "summary": plan.summary(),
        "warnings": list(plan.warnings),
        "manifest": manifest,
        "backup_root": str(backup_root),
        "export_root": str(target),
    }
    config.append_log(rec)
    counted(manifest, [f"{len(plan.exports)} file(s) copied out to {target}"])
    log.info("STRAT  cleanup done id=%s", tid)
    edit._invalidate(mod)
    return rec


def _log_cleanup_plan(plan: CleanupPlan) -> None:
    """Exactly what the cleanup is about to remove and move - by name."""
    log.info("  removing %d strat model(s) from %s", len(plan.entry_deletes), REL)
    for name in plan.entry_deletes:
        log.info("    - %s", name)
    log.info("  exporting %d file(s), %d of them named by nothing",
             len(plan.exports), plan.orphan_count)
    for _src, rel in plan.exports[:200]:
        log.info("    > %s", rel)
    if plan.kept_files:
        log.info("  leaving %d shared file(s) in place", len(plan.kept_files))
        for rel in plan.kept_files[:100]:
            log.info("    = %s", rel)
    for w in plan.warnings:
        log.warning("  ! %s", w)
