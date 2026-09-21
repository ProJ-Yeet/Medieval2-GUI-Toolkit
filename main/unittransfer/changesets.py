"""Change sets: your edits to a mod, recorded, and ported onto its next version. Phase 52.

Asked for as outside feedback on 2026-09-21: edits made to a big mod (AGO, EUR)
are lost the moment its next release overwrites the files, and a mod that size
cannot simply be copied into a folder of its own to keep them. The idea was a
file listing every change, which can be exported and PORTED onto another
version of the same mod, with a checklist and a warning wherever a unit was
removed, a record was edited upstream too, or a building no longer exists.

**No duplicate of the mod.** Every writer in this toolkit copies a file before
its first change and logs ``BACKUP`` through :func:`unittransfer.logutil.file_op`
- that function's own docstring is the promise that nothing reaches the disk
without passing it. So :func:`capture` hangs off it: the first time a file of a
mod under ``<Medieval II>/mods`` is backed up, its original goes into this mod's
set as the **baseline**; every time one is written, the result goes in as
**mine**. Both live under ``config/changesets/<mod>/``, outside the mod folder,
so an update that overwrites the mod cannot overwrite either. That is a handful
of files out of thousands, not a copy.

**The change list is derived, not logged.** Nothing here keeps a journal of
edits that a missed write could make wrong: the list is the baseline and mine
compared record by record - an EDU unit by its ``type``, an EDB building by its
name, a region by its name, a text key by its key - and a file with no record
shape is compared as one record, line by line.

**A port is a three-way merge per record.** The baseline is the old version as
it shipped, mine is the old version as edited, and theirs is the version being
ported onto - the same mod after an update overwrote it, or another folder.
Each record comes out as one of:

* ``clean``     theirs still equals the baseline, so mine applies as it is
* ``already``   theirs already says what mine says
* ``merged``    both changed it, in lines that do not overlap: merged, and shown
* ``conflict``  both changed the same lines: all three shown, you pick
* ``gone``      you edited it and the new version no longer has it
* and a ``dangling`` warning on a change that applies but names something the
  result no longer has - a recruit pool for a unit that is not in the EDU.

Nothing is merged without being listed, and nothing is written without a tick.
The write is one backup and one log entry like every other job, so the Log's
Undo takes a port back.

Phase 53 (switching a set off and on in place) builds on this and is not here.
"""
from __future__ import annotations

import difflib
import io
import json
import re
import shutil
import threading
import time
import zipfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from . import config, rawtext

#: The verbs :func:`logutil.file_op` is called with once a file's new bytes are
#: on disk. BACKUP is the one called before.
_AFTER = {"WRITE", "COPY", "MOVE", "RESTORE", "CONVERT"}
#: A file bigger than this is not worth a second copy of (no text file a mod
#: ships comes near it; a map texture might).
MAX_BYTES = 64 * 1024 * 1024
#: One record's text sent to the page for a side-by-side, at most.
SHOW_CHARS = 20000
#: Records listed per file in the summary before the rest are counted.
LIST_MAX = 200

_lock = threading.RLock()


class ChangeSetError(Exception):
    pass


# ---------------------------------------------------------------------------
# where a set lives


def root_dir() -> Path:
    # read at call time: the tests point config.CONFIG_DIR somewhere temporary
    return Path(config.CONFIG_DIR) / "changesets"


def _safe_name(name: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_.\- ()]+", "_", str(name or "")).strip(" .")
    if not out:
        raise ChangeSetError("a change set needs a name")
    return out


def set_dir(name: str) -> Path:
    return root_dir() / _safe_name(name)


def _safe_rel(rel: str) -> str:
    """A path inside ``data/``, or an error. A set can be imported from
    somebody else, so its file list is not trusted to stay inside the mod."""
    p = PurePosixPath(str(rel).replace("\\", "/"))
    if not str(p) or p.is_absolute() or ".." in p.parts or ":" in str(p):
        raise ChangeSetError(f"not a path inside data/: {rel}")
    return str(p)


def load(name: str) -> dict:
    p = set_dir(name) / "set.json"
    if not p.is_file():
        raise ChangeSetError(f"no change set called {name}")
    return json.loads(p.read_text(encoding="utf-8"))


def _save(meta: dict) -> None:
    d = set_dir(meta["name"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "set.json.tmp"
    tmp.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    tmp.replace(d / "set.json")


def _new(name: str, mod: str, mod_root: str = "") -> dict:
    return {"name": _safe_name(name), "mod": mod, "mod_root": mod_root,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {}}


def _open_or_new(name: str, mod: str, mod_root: str) -> dict:
    try:
        return load(name)
    except ChangeSetError:
        return _new(name, mod, mod_root)


def sets() -> List[dict]:
    out = []
    base = root_dir()
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        try:
            meta = json.loads((d / "set.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"name": meta.get("name", d.name), "mod": meta.get("mod", ""),
                    "files": len(meta.get("files") or {}),
                    "created": meta.get("created", ""),
                    "imported": bool(meta.get("imported"))})
    return out


def _blob(name: str, side: str, rel: str) -> Path:
    return set_dir(name) / side / _safe_rel(rel)


def _read_side(meta: dict, side: str, rel: str) -> Optional[bytes]:
    """The baseline's or mine's bytes for one file, or None where it is absent."""
    entry = (meta.get("files") or {}).get(rel) or {}
    if entry.get(side) != "present":
        return None
    p = _blob(meta["name"], side, rel)
    return p.read_bytes() if p.is_file() else None


# ---------------------------------------------------------------------------
# recording, from inside the write helpers


def _mod_of(path) -> Optional[Tuple[str, Path, str]]:
    """``(mod name, mod root, rel under data/)`` for a file of an installed mod."""
    root = config.get_med2_root()
    if not root:
        return None
    try:
        mods = (Path(root) / "mods").resolve()
        p = Path(path).resolve()
        parts = p.relative_to(mods).parts
    except (ValueError, OSError):
        return None
    if len(parts) < 3 or parts[1].lower() != "data":
        return None
    return parts[0], mods / parts[0], "/".join(parts[2:])


def capture(verb: str, path) -> None:
    """Called by :func:`logutil.file_op` for every file the toolkit touches.

    Never raises: a change set that cannot be written must not stop the write
    it is recording. It only ever reads the file and copies it elsewhere.
    """
    try:
        _capture(verb, path)
    except Exception:                                    # noqa: BLE001
        pass


def _capture(verb: str, path) -> None:
    if verb not in _AFTER and verb not in ("BACKUP", "DELETE"):
        return
    hit = _mod_of(path)
    if hit is None:
        return
    mod, mod_root, rel = hit
    p = Path(path)
    with _lock:
        meta = _open_or_new(mod, mod, str(mod_root))
        files = meta["files"]
        entry = files.get(rel)
        changed = False
        if verb == "BACKUP":
            # before the write: the first sight of a file is its original
            if entry is None and p.is_file() and p.stat().st_size <= MAX_BYTES:
                dst = _blob(mod, "base", rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                files[rel] = {"base": "present", "mine": "unset"}
                changed = True
        elif verb == "DELETE":
            if entry is not None:
                entry["mine"] = "absent"
                changed = True
        else:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                return
            if entry is None:
                # written with no backup first: the toolkit created it
                entry = files[rel] = {"base": "absent", "mine": "unset"}
            dst = _blob(mod, "mine", rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            entry["mine"] = "present"
            changed = True
        if changed:
            _save(meta)


def refresh(mod_root, rels) -> None:
    """Undo put files back without going through a write helper: re-read them."""
    for rel in rels or []:
        path = Path(mod_root) / "data" / rel
        capture("WRITE" if path.is_file() else "DELETE", path)


def undone(rec: dict) -> None:
    """Called by :func:`unittransfer.transfer.undo` once a job's files are back.

    A port onto its own mod saved the set as it was (see :func:`apply_port`),
    and that is what comes back - baseline and mine together. Any other job
    only changed files, so the set re-reads the ones it put back.
    """
    snap = (rec.get("changeset_snapshot") or {})
    path = Path(snap.get("path") or "")
    if snap.get("name") and path.is_dir():
        with _lock:
            d = set_dir(snap["name"])
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(path, d)
        return
    manifest = rec.get("manifest") or {}
    refresh(rec.get("dest_root", ""), list(manifest.get("backed_up", []))
            + list(manifest.get("created", [])))


# ---------------------------------------------------------------------------
# records


#: Which files have a record shape, and the line that starts a record.
_SPLIT = (
    (lambda r: r == "export_descr_unit.txt",
     re.compile(r"^[ \t]*type[ \t]+([^;\r\n]*?)[ \t]*(?:;.*)?$"), "unit"),
    (lambda r: r == "export_descr_buildings.txt",
     re.compile(r"^building[ \t]+([^\s;]+)"), "building"),
    (lambda r: r.endswith("descr_regions.txt"),
     re.compile(r"^([A-Za-z0-9_\-]+)[ \t]*(?:;.*)?$"), "region"),
    (lambda r: r.startswith("text/") and r.endswith(".txt"),
     re.compile(r"^\{([^}]+)\}"), "text key"),
)
FILE_KEY = "(whole file)"
HEAD_KEY = "(top of file)"


def _splitter(rel: str):
    low = rel.lower()
    for test, rx, what in _SPLIT:
        if test(low):
            return rx, what
    return None, "file"


def _lines(text: str) -> List[str]:
    return text.splitlines(keepends=True)


def split(rel: str, text: str) -> "OrderedDict[str, str]":
    """The file as ordered ``key -> record text``, losslessly: joined back in
    order the values are the text exactly. A file with no record shape is one
    record."""
    rx, _ = _splitter(rel)
    out: "OrderedDict[str, str]" = OrderedDict()
    if rx is None:
        out[FILE_KEY] = text
        return out
    key, buf = HEAD_KEY, []
    seen: Dict[str, int] = {}

    def flush():
        if key == HEAD_KEY and not buf:
            return
        out[key] = "".join(buf)

    for line in _lines(text):
        m = rx.match(line.rstrip("\r\n"))
        if m and m.group(1).strip():
            flush()
            name = m.group(1).strip()
            n = seen.get(name.lower(), 0) + 1
            seen[name.lower()] = n
            key, buf = (name if n == 1 else f"{name} #{n}"), [line]
        else:
            buf.append(line)
    flush()
    return out


def _decode(raw: Optional[bytes]):
    """``(text, codec)``, or ``(None, None)`` for an absent or binary file."""
    if raw is None:
        return None, None
    if b"\x00" in raw[:4096] and raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):
        return None, None
    codec = rawtext.sniff(raw)
    try:
        return rawtext.decode(raw, codec), codec
    except UnicodeDecodeError:
        return None, None


def _is_text(*raws: Optional[bytes]) -> bool:
    return all(r is None or _decode(r)[0] is not None for r in raws)


# ---------------------------------------------------------------------------
# a three-way merge of lines


def _regions(a: List[str], b: List[str]):
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(i1, i2, b[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes()
            if tag != "equal"]


def _touch(s1, e1, s2, e2) -> bool:
    # Touching counts, not only overlapping: a line inserted directly under one
    # the other side rewrote is usually part of the same edit (a pool added
    # under a pool upstream re-tuned), which is git's rule for the same reason.
    return max(s1, s2) <= min(e1, e2)


def merge3(base: str, mine: str, theirs: str) -> Optional[str]:
    """Both sides' changes to ``base``, or None where they overlap.

    Overlap is the ordinary diff3 sense: the two sides changed the same lines,
    or both inserted at the same point. The same change made on both sides is
    not a conflict.
    """
    b, m, t = _lines(base), _lines(mine), _lines(theirs)
    marks = sorted([(s, e, rep, "m") for s, e, rep in _regions(b, m)] +
                   [(s, e, rep, "t") for s, e, rep in _regions(b, t)],
                   key=lambda r: (r[0], r[1]))
    out: List[str] = []
    pos = i = 0
    while i < len(marks):
        grp = [marks[i]]
        gs, ge = marks[i][0], marks[i][1]
        j = i + 1
        while j < len(marks) and _touch(gs, ge, marks[j][0], marks[j][1]):
            grp.append(marks[j])
            ge = max(ge, marks[j][1])
            j += 1
        out += b[pos:gs]

        def side(who):
            p, acc = gs, []
            for s, e, rep, w in grp:
                if w != who:
                    continue
                acc += b[p:s] + rep
                p = e
            return acc + b[p:ge]

        whos = {w for *_, w in grp}
        if len(whos) == 1:
            out += side(whos.pop())
        else:
            a, c = side("m"), side("t")
            if a != c:
                return None
            out += a
        pos, i = ge, j
    out += b[pos:]
    return "".join(out)


# ---------------------------------------------------------------------------
# what the set says you changed


def _record_diff(rel: str, base: Optional[bytes], mine: Optional[bytes]) -> List[dict]:
    bt, _ = _decode(base)
    mt, _ = _decode(mine)
    if bt is None and base is not None or mt is None and mine is not None:
        return [{"key": FILE_KEY, "kind": "edited"}] if base != mine else []
    b = split(rel, bt) if bt is not None else OrderedDict()
    m = split(rel, mt) if mt is not None else OrderedDict()
    out = []
    for k in list(m.keys()) + [k for k in b if k not in m]:
        if k not in b:
            out.append({"key": k, "kind": "added"})
        elif k not in m:
            out.append({"key": k, "kind": "removed"})
        elif b[k] != m[k]:
            out.append({"key": k, "kind": "edited"})
    return out


def summary(mod) -> dict:
    """The set for this mod: every file it tracks, what changed in it record by
    record, and whether the disk still says what you last wrote."""
    name = getattr(mod, "name", str(mod))
    data = Path(getattr(mod, "data", ""))
    try:
        meta = load(name)
    except ChangeSetError:
        return {"set": None, "mod": name, "files": [], "sets": sets()}
    rows = []
    for rel in sorted(meta["files"]):
        base, mine = _read_side(meta, "base", rel), _read_side(meta, "mine", rel)
        entry = meta["files"][rel]
        if entry.get("mine") == "unset":
            continue                       # backed up, never written: nothing yet
        disk_p = data / rel
        disk = disk_p.read_bytes() if disk_p.is_file() else None
        if base == mine:
            continue                       # edited and put back: no change
        recs = _record_diff(rel, base, mine)
        state = ("created" if base is None else "deleted" if mine is None else "edited")
        rows.append({
            "rel": rel, "state": state, "what": _splitter(rel)[1],
            "records": recs[:LIST_MAX], "more": max(0, len(recs) - LIST_MAX),
            "count": len(recs),
            # the disk moved under the set: an update, or a hand edit
            "disk": ("same" if disk == mine else "original" if disk == base
                     else "missing" if disk is None else "changed"),
        })
    return {"set": meta["name"], "mod": name, "created": meta.get("created", ""),
            "imported": bool(meta.get("imported")), "files": rows, "sets": sets()}


# ---------------------------------------------------------------------------
# a port


@dataclass
class Item:
    id: int
    rel: str
    key: str
    outcome: str                  # clean | already | merged | conflict | gone
    kind: str                     # added | removed | edited
    base: Optional[str] = None
    mine: Optional[str] = None
    theirs: Optional[str] = None
    merged: Optional[str] = None
    dangling: List[str] = field(default_factory=list)
    binary: bool = False

    @property
    def default(self) -> bool:
        return self.outcome in ("clean", "merged")

    def payload(self) -> dict:
        cut = lambda s: None if s is None else s[:SHOW_CHARS]    # noqa: E731
        show = self.outcome in ("merged", "conflict", "gone") and not self.binary
        return {"id": self.id, "rel": self.rel, "key": self.key,
                "outcome": self.outcome, "kind": self.kind,
                "default": self.default, "dangling": self.dangling,
                "binary": self.binary,
                **({"base": cut(self.base), "mine": cut(self.mine),
                    "theirs": cut(self.theirs), "merged": cut(self.merged)} if show else {})}


@dataclass
class Port:
    set_name: str
    target: object                # the Mod being written to
    items: List[Item] = field(default_factory=list)
    files: Dict[str, dict] = field(default_factory=dict)   # rel -> sides, codec
    warnings: List[str] = field(default_factory=list)

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for it in self.items:
            out[it.outcome] = out.get(it.outcome, 0) + 1
        return out

    def payload(self) -> dict:
        return {"set": self.set_name, "target": getattr(self.target, "name", ""),
                "items": [i.payload() for i in self.items],
                "counts": self.counts(), "warnings": self.warnings}


def _outcome(b, m, t, text: bool) -> Tuple[str, Optional[str]]:
    """What happens to one record: ``(outcome, merged text)``."""
    if t == m:
        return "already", None
    if b is None:                              # you added it
        return ("clean", None) if t is None else ("conflict", None)
    if m is None:                              # you removed it
        if t == b:
            return "clean", None
        return ("gone" if t is None else "conflict"), None
    if t is None:
        return "gone", None
    if t == b:
        return "clean", None
    if text:
        merged = merge3(b, m, t)
        if merged is not None:
            return "merged", merged
    return "conflict", None


def plan_port(set_name: str, target) -> Port:
    """Every record the set changed, against the target's files as they are."""
    meta = load(set_name)
    port = Port(set_name, target)
    data = Path(target.data)
    n = 0
    for rel in sorted(meta["files"]):
        rel = _safe_rel(rel)
        entry = meta["files"][rel]
        if entry.get("mine") == "unset":
            continue
        base, mine = _read_side(meta, "base", rel), _read_side(meta, "mine", rel)
        if base == mine:
            continue
        tp = data / rel
        theirs = tp.read_bytes() if tp.is_file() else None
        port.files[rel] = {"base": base, "mine": mine, "theirs": theirs}
        if not _is_text(base, mine, theirs):
            o, _ = _outcome(base, mine, theirs, False)
            kind = "added" if base is None else "removed" if mine is None else "edited"
            port.items.append(Item(n, rel, FILE_KEY, o, kind, binary=True))
            n += 1
            continue
        bt, mt, tt = (_decode(x)[0] for x in (base, mine, theirs))
        b = split(rel, bt) if bt is not None else OrderedDict()
        m = split(rel, mt) if mt is not None else OrderedDict()
        t = split(rel, tt) if tt is not None else OrderedDict()
        for k in list(m.keys()) + [k for k in b if k not in m]:
            bv, mv, tv = b.get(k), m.get(k), t.get(k)
            if bv == mv:
                continue
            o, merged = _outcome(bv, mv, tv, True)
            kind = "added" if bv is None else "removed" if mv is None else "edited"
            port.items.append(Item(n, rel, k, o, kind, bv, mv, tv, merged))
            n += 1
    _mark_dangling(port)
    return port


_POOL = re.compile(r'^\s*recruit_pool\s+"([^"]+)"', re.M)
_TYPE = re.compile(r"^[ \t]*type[ \t]+([^;\r\n]*?)[ \t]*(?:;[^\r\n]*)?\r?$", re.M)


def _mark_dangling(port: Port) -> None:
    """A recruit pool that would name a unit the result's EDU does not have.

    The feedback's own example: an update moves units around, and an old edit
    recruits one the new version dropped. The EDU compared against is the one
    the port would leave behind - yours if this port rewrites it, theirs if not.
    """
    edu_rel = "export_descr_unit.txt"
    sides = port.files.get(edu_rel)
    if sides is not None:
        # every EDU change that would apply by default, laid over theirs
        edu = _assemble(port, edu_rel, {i.id: "mine" for i in port.items
                                        if i.rel == edu_rel and i.default})
        text = _decode(edu)[0] if edu is not None else ""
    else:
        p = Path(port.target.data) / edu_rel
        text = _decode(p.read_bytes())[0] if p.is_file() else ""
    if not text:
        return
    units = {t.strip().lower() for t in _TYPE.findall(text)}
    for it in port.items:
        if it.rel != "export_descr_buildings.txt" or it.mine is None:
            continue
        missing = sorted({u for u in _POOL.findall(it.mine) if u.lower() not in units})
        it.dangling = missing


def _assemble(port: Port, rel: str, picks: Dict[int, str]) -> Optional[bytes]:
    """One file of the result: theirs, with the picked records laid over it.

    ``picks`` maps an item id to ``"mine"`` (take your version, or the merge
    where there is one) - an item not in it keeps theirs. Returns None for a
    file the result should not have.
    """
    sides = port.files[rel]
    base, mine, theirs = sides["base"], sides["mine"], sides["theirs"]
    items = [i for i in port.items if i.rel == rel and i.id in picks]
    if not items:
        return theirs
    if items[0].binary:
        return mine
    tt, tcodec = _decode(theirs)
    mt, mcodec = _decode(mine)
    codec = tcodec or mcodec or rawtext.Codec("latin-1")
    order_mine = list(split(rel, mt).keys()) if mt is not None else []
    res = split(rel, tt) if tt is not None else OrderedDict()
    for it in items:
        if it.outcome == "already":
            continue
        new = it.merged if it.merged is not None else it.mine
        if new is None:
            res.pop(it.key, None)
            continue
        if it.key in res:
            res[it.key] = new
            continue
        # a record the result lacks goes where it sits in yours: after the
        # nearest record before it that the result has, else before the
        # nearest one after it, else at the end
        keys = list(res.keys())
        idx = order_mine.index(it.key) if it.key in order_mine else len(order_mine)
        at = next((keys.index(k) + 1 for k in reversed(order_mine[:idx]) if k in res),
                  None)
        if at is None:
            at = next((keys.index(k) for k in order_mine[idx + 1:] if k in res),
                      len(keys))
        pairs = list(res.items())
        pairs.insert(at, (it.key, new))
        res = OrderedDict(pairs)
    if not res:
        return None
    parts = list(res.values())
    nl = "\r\n" if "\r\n" in "".join(parts[:3]) else "\n"
    for k in range(len(parts) - 1):          # a record that ended the file had no newline
        if parts[k] and not parts[k].endswith(("\n", "\r")):
            parts[k] += nl
    return rawtext.encode("".join(parts), codec)


def apply_port(port: Port, picks: Dict[int, str]) -> dict:
    """Write the picked records, with a backup and a log entry, so Undo works.

    After it, the set's baseline for every file written is the version it was
    ported onto - that is what the next update will be compared against - and
    mine is the result.
    """
    from .logutil import file_op, log

    picks = {int(k): v for k, v in (picks or {}).items() if v == "mine"}
    if not picks:
        raise ChangeSetError("nothing ticked to port")
    target = port.target
    data = Path(target.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    written, removed = [], []
    same_mod = False
    try:
        same_mod = load(port.set_name).get("mod") == getattr(target, "name", "")
    except ChangeSetError:
        pass
    snapshot = ""
    if same_mod:
        # A port moves this set's baseline onto the version ported onto. Undo
        # must move it back, or undoing a port would leave a set whose baseline
        # and mine both say the new version - every edit forgotten. So the set
        # as it stands goes beside the job's backups, and undo restores it.
        snap = backup_root / "changeset"
        shutil.copytree(set_dir(port.set_name), snap)
        snapshot = str(snap)
    for rel in sorted({i.rel for i in port.items if i.id in picks}):
        rel = _safe_rel(rel)
        out = _assemble(port, rel, picks)
        theirs = port.files[rel]["theirs"]
        if out == theirs:
            continue
        if same_mod:
            # the version ported onto is the new baseline for this file
            _rebase(port.set_name, rel, theirs)
        path = data / rel
        bpath = backup_root / "data" / rel
        if path.exists():
            bpath.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", path, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        if out is None:
            path.unlink()
            file_op("DELETE", path, "change set port (Undo puts it back)")
            removed.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(out)
        file_op("WRITE", path, f"{len(out)} bytes (change set port)")
        written.append(rel)
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "changeset", "action": "port",
        "source": port.set_name, "source_root": "",
        "dest": getattr(target, "name", ""), "dest_root": str(target.root),
        "unit_type": port.set_name, "resolved_type": port.set_name,
        "options": {"picked": len(picks)}, "applied": True, "undone": False,
        "note": "", "summary": f"ported {len(picks)} change(s) from {port.set_name}",
        "warnings": list(port.warnings), "manifest": manifest,
        "backup_root": str(backup_root),
        "changeset_snapshot": {"name": port.set_name, "path": snapshot} if snapshot else None,
    }
    config.append_log(rec)
    log.info("PORT   %s -> %s: %d change(s), %d file(s), id=%s", port.set_name,
             getattr(target, "name", ""), len(picks), len(written) + len(removed), tid)
    return {"id": tid, "written": written, "removed": removed, "record": rec}


def _rebase(name: str, rel: str, theirs: Optional[bytes]) -> None:
    with _lock:
        meta = load(name)
        entry = meta["files"].setdefault(rel, {"mine": "unset"})
        p = _blob(name, "base", rel)
        if theirs is None:
            entry["base"] = "absent"
            if p.exists():
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(theirs)
            entry["base"] = "present"
        _save(meta)


# ---------------------------------------------------------------------------
# the set as one file, both ways; and starting over


def export_bytes(name: str) -> bytes:
    """The whole set as one zip: ``set.json`` and the two copies of each file."""
    d = set_dir(name)
    load(name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.name != "set.json.tmp":
                z.write(p, p.relative_to(d).as_posix())
    return buf.getvalue()


def import_bytes(raw: bytes, name: str = "") -> str:
    """A set exported somewhere else, under a name of its own."""
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        meta = json.loads(z.read("set.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise ChangeSetError(f"not a change set file ({e})")
    want = _safe_name(name or f"{meta.get('mod') or 'mod'} (imported "
                      f"{time.strftime('%Y-%m-%d %H%M')})")
    d = set_dir(want)
    if d.exists():
        raise ChangeSetError(f"there is already a change set called {want}")
    files = {}
    for rel, entry in (meta.get("files") or {}).items():
        files[_safe_rel(rel)] = {"base": entry.get("base", "absent"),
                                 "mine": entry.get("mine", "absent")}
    for info in z.infolist():
        if info.is_dir() or info.filename == "set.json":
            continue
        side, _, rel = info.filename.partition("/")
        if side not in ("base", "mine"):
            continue
        dst = d / side / _safe_rel(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(z.read(info))
    _save({"name": want, "mod": meta.get("mod", ""), "mod_root": "",
           "created": meta.get("created", ""), "imported": True, "files": files})
    return want


def adopt(name: str, mod) -> int:
    """Take the disk as yours, for every file the set tracks: for hand edits
    made outside the toolkit. Not after an update - that is what a port is for."""
    data = Path(mod.data)
    n = 0
    with _lock:
        meta = load(name)
        for rel, entry in meta["files"].items():
            p = data / _safe_rel(rel)
            dst = _blob(name, "mine", rel)
            if p.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                entry["mine"] = "present"
            else:
                entry["mine"] = "absent"
            n += 1
        _save(meta)
    return n


def forget(name: str) -> None:
    """Drop the set. The mod is not touched; its changes are simply no longer
    recorded against an original, and the next write starts a new set."""
    d = set_dir(name)
    load(name)
    shutil.rmtree(d)
