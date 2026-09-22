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
**mine**. Both live under ``config/changesets/<set>/``, outside the mod folder,
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

**Switching in place (Phase 53).** A mod can carry several sets - versions of
it, in effect - and one is ON at a time: its records are what the mod's files
say. :func:`plan_switch` takes the active set's records back OUT (the same
three-way merge, run the other way: yours as the base, the original as the
change, the disk as theirs) and puts another set's records IN, as one job with
one Undo. A switch is mechanical or it does not happen: any record that would
conflict, or that the disk no longer has, refuses it and names the record, and
a port is how to settle that. While every set of a mod is off, the next save
starts a new one, so "the original, plus a fresh set of edits" is simply what
turning the last one off leaves.
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
#: Set while a switch writes: its writes put a set's records in or take them
#: out, which is not an edit of yours, and recording them would overwrite the
#: very copy being switched to.
_quiet = threading.local()


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
            "created": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {},
            "active": True}


def is_active(meta: dict) -> bool:
    # a set from before Phase 53 has no flag and was the mod's only one; an
    # imported set is somebody else's until it is switched on here
    return bool(meta.get("active", not meta.get("imported")))


def sets_of(mod: str) -> List[dict]:
    """Every set belonging to ``mod``, as loaded ``set.json`` dicts."""
    out = []
    base = root_dir()
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        try:
            meta = json.loads((d / "set.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(meta.get("mod", "")).lower() == str(mod).lower():
            out.append(meta)
    return out


def active_of(mod: str) -> Optional[str]:
    return next((m["name"] for m in sets_of(mod) if is_active(m)), None)


def _free_name(mod: str) -> str:
    n, name = 1, _safe_name(mod)
    while set_dir(name).exists():
        n += 1
        name = _safe_name(f"{mod} ({n})")
    return name


def _recording_set(mod: str, mod_root: str) -> dict:
    """The set a write to ``mod`` is recorded in: the active one, or a new one
    when every set of the mod is off (or there is none yet)."""
    name = active_of(mod)
    if name:
        return load(name)
    return _new(_free_name(mod), mod, mod_root)


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
                    "imported": bool(meta.get("imported")),
                    "active": is_active(meta)})
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
    if getattr(_quiet, "on", False):
        return
    if verb not in _AFTER and verb not in ("BACKUP", "DELETE"):
        return
    hit = _mod_of(path)
    if hit is None:
        return
    mod, rel = hit[0], hit[2]
    p = Path(path)
    with _lock:
        meta = _recording_set(mod, str(hit[1]))
        mod = meta["name"]                 # the blobs go under the SET's folder
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
    snaps = list(rec.get("changeset_snapshots") or [])
    if rec.get("changeset_snapshot"):
        snaps.append(rec["changeset_snapshot"])
    snaps = [x for x in snaps if x and x.get("name") and Path(x.get("path") or "").is_dir()]
    if snaps:
        with _lock:
            for x in snaps:
                d = set_dir(x["name"])
                if d.exists():
                    shutil.rmtree(d)
                shutil.copytree(x["path"], d)
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


def _versions(mod: str) -> List[dict]:
    out = []
    for m in sets_of(mod):
        n = 0
        for rel, entry in (m.get("files") or {}).items():
            if entry.get("mine") == "unset":
                continue
            if _read_side(m, "base", rel) != _read_side(m, "mine", rel):
                n += 1
        out.append({"name": m["name"], "active": is_active(m), "files": n,
                    "created": m.get("created", ""), "imported": bool(m.get("imported"))})
    return out


def summary(mod, name: str = "") -> dict:
    """One set of this mod - the active one unless another is named: every file
    it tracks, what changed in it record by record, and whether the disk still
    says what you last wrote. With the mod's other sets, for switching."""
    modname = getattr(mod, "name", str(mod))
    data = Path(getattr(mod, "data", ""))
    versions = _versions(modname)
    name = name or active_of(modname) or ""
    try:
        meta = load(name) if name else None
    except ChangeSetError:
        meta = None
    if meta is None:
        return {"set": None, "mod": modname, "files": [], "sets": sets(),
                "versions": versions, "active": None}
    name = modname
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
            "imported": bool(meta.get("imported")), "files": rows, "sets": sets(),
            "versions": versions, "active": active_of(name),
            "on": is_active(meta)}


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


def _file_items(port: Port, rel: str, base, mine, theirs) -> None:
    """Every record of one file that ``mine`` changed from ``base``, against
    ``theirs``, appended to the port."""
    port.files[rel] = {"base": base, "mine": mine, "theirs": theirs}
    n = len(port.items)
    if not _is_text(base, mine, theirs):
        o, _ = _outcome(base, mine, theirs, False)
        kind = "added" if base is None else "removed" if mine is None else "edited"
        port.items.append(Item(n, rel, FILE_KEY, o, kind, binary=True))
        return
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


def _changed(meta: dict):
    """``(rel, base, mine)`` for every file the set really changed."""
    for rel in sorted(meta["files"]):
        rel = _safe_rel(rel)
        if meta["files"][rel].get("mine") == "unset":
            continue
        base, mine = _read_side(meta, "base", rel), _read_side(meta, "mine", rel)
        if base != mine:
            yield rel, base, mine


def plan_port(set_name: str, target) -> Port:
    """Every record the set changed, against the target's files as they are."""
    meta = load(set_name)
    port = Port(set_name, target)
    data = Path(target.data)
    for rel, base, mine in _changed(meta):
        tp = data / rel
        _file_items(port, rel, base, mine, tp.read_bytes() if tp.is_file() else None)
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
# switching in place (Phase 53)


@dataclass
class Switch:
    mod: object
    off: Optional[str]                 # the set taken out, if one is on
    on: Optional[str]                  # the set put in, if one is asked for
    files: Dict[str, dict] = field(default_factory=dict)  # rel -> before, middle, after
    blocked: List[dict] = field(default_factory=list)
    steps: List[dict] = field(default_factory=list)

    def payload(self) -> dict:
        return {"mod": getattr(self.mod, "name", ""), "off": self.off, "on": self.on,
                "files": sorted(self.files), "blocked": self.blocked, "steps": self.steps}


def plan_switch(mod, to: Optional[str]) -> Switch:
    """Take the mod's active set out and put ``to`` in (``to=None``: just out).

    Out is the port run backwards - base and mine swapped, so every record you
    changed goes back to the original - against the disk. In is an ordinary
    port of ``to`` onto what that leaves. Every record must come out ``clean``,
    ``merged`` or ``already``; anything else is listed in ``blocked`` and the
    switch does not happen.
    """
    name = getattr(mod, "name", str(mod))
    data = Path(mod.data)
    off = active_of(name)
    if to is not None:
        meta_to = load(to)
        if str(meta_to.get("mod", "")).lower() != name.lower():
            raise ChangeSetError(f"{to} is a set of {meta_to.get('mod')}, not of {name}")
        if to == off:
            raise ChangeSetError(f"{to} is already on")
    sw = Switch(mod, off, to)
    current: Dict[str, Optional[bytes]] = {}

    def disk(rel):
        if rel not in current:
            p = data / rel
            current[rel] = p.read_bytes() if p.is_file() else None
        return current[rel]

    for step, name_, reverse in ((1, off, True), (2, to, False)):
        if not name_:
            continue
        meta = load(name_)
        port = Port(name_, mod)
        for rel, base, mine in _changed(meta):
            a, b = (mine, base) if reverse else (base, mine)
            _file_items(port, rel, a, b, disk(rel))
        bad = [i for i in port.items if i.outcome not in ("clean", "merged", "already")]
        for i in bad:
            sw.blocked.append({"set": name_, "rel": i.rel, "key": i.key,
                               "outcome": i.outcome, "step": "out" if reverse else "in"})
        sw.steps.append({"set": name_, "step": "out" if reverse else "in",
                         "records": len(port.items), "counts": port.counts()})
        if bad:
            continue
        picks = {i.id: "mine" for i in port.items}
        for rel in port.files:
            before = sw.files.get(rel, {}).get("before", disk(rel))
            after = _assemble(port, rel, picks)
            sw.files.setdefault(rel, {"before": before})
            if reverse:
                sw.files[rel]["middle"] = after
            current[rel] = after
            sw.files[rel]["after"] = after
    return sw


def apply_switch(sw: Switch) -> dict:
    """Write a planned switch: one backup, one log entry, one Undo.

    The writes are not recorded as edits (``_quiet``). The set switched on is
    rebased onto what it was put into, exactly as a port rebases, so the next
    update is compared against the right thing; the set switched off keeps its
    two copies untouched, ready to go back in.
    """
    from .logutil import file_op, log

    if sw.blocked:
        raise ChangeSetError("the switch would conflict: port instead")
    mod = sw.mod
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    snaps = []
    for name in {n for n in (sw.off, sw.on) if n}:
        snap = backup_root / "changeset_sets" / _safe_name(name)
        shutil.copytree(set_dir(name), snap)
        snaps.append({"name": name, "path": str(snap)})
    written = []
    _quiet.on = True
    try:
        for rel in sorted(sw.files):
            rel = _safe_rel(rel)
            f = sw.files[rel]
            if f["after"] == f["before"]:
                continue
            path = data / rel
            if path.exists():
                bpath = backup_root / "data" / rel
                bpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, bpath)
                manifest["backed_up"].append(rel)
                file_op("BACKUP", path, f"-> {bpath}")
            else:
                manifest["created"].append(rel)
            if f["after"] is None:
                path.unlink()
                file_op("DELETE", path, "change set switched (Undo puts it back)")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f["after"])
                file_op("WRITE", path, f"{len(f['after'])} bytes (change set switched)")
            written.append(rel)
    finally:
        _quiet.on = False
    with _lock:
        if sw.off:
            meta = load(sw.off)
            meta["active"] = False
            _save(meta)
        if sw.on:
            meta = load(sw.on)
            for rel, base, mine in list(_changed(meta)):
                f = sw.files.get(rel)
                if not f:
                    continue
                middle = f.get("middle", f["before"])
                for side, raw in (("base", middle), ("mine", f["after"])):
                    p = _blob(sw.on, side, rel)
                    if raw is None:
                        meta["files"][rel][side] = "absent"
                        if p.exists():
                            p.unlink()
                    else:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(raw)
                        meta["files"][rel][side] = "present"
            meta["active"] = True
            meta["imported"] = False
            _save(meta)
    what = (f"switched {sw.off} off and {sw.on} on" if sw.off and sw.on
            else f"switched {sw.off} off" if sw.off else f"switched {sw.on} on")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "changeset", "action": "switch",
        "source": sw.on or sw.off or "", "source_root": "",
        "dest": getattr(mod, "name", ""), "dest_root": str(mod.root),
        "unit_type": sw.on or sw.off or "", "resolved_type": sw.on or sw.off or "",
        "options": {"off": sw.off, "on": sw.on}, "applied": True, "undone": False,
        "note": "", "summary": what, "warnings": [], "manifest": manifest,
        "backup_root": str(backup_root), "changeset_snapshots": snaps,
    }
    config.append_log(rec)
    log.info("SWITCH %s: %s, %d file(s), id=%s", getattr(mod, "name", ""), what,
             len(written), tid)
    return {"id": tid, "written": written, "record": rec}


def rename(name: str, new: str) -> str:
    """A set under a name you will recognise - "AGO with my Rohan", say."""
    new = _safe_name(new)
    if new == _safe_name(name):
        return new
    with _lock:
        meta = load(name)
        if set_dir(new).exists():
            raise ChangeSetError(f"there is already a change set called {new}")
        set_dir(name).rename(set_dir(new))
        meta["name"] = new
        _save(meta)
    return new


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


#: The note at the top of a files export, beside `data/`.
FILES_NOTE = "CHANGED_FILES.txt"


def export_files_bytes(name: str) -> Tuple[bytes, dict]:
    """Every file the set changed, as you last wrote it, at its own path.

    Asked for on 2026-09-22, and different from :func:`export_bytes`: that one
    is the set (both copies and ``set.json``) for porting with this tool, this
    one is plain files for anybody. The zip holds ``data/<rel>`` so it unzips
    onto a mod folder as it stands, plus :data:`FILES_NOTE` listing what is in
    it and what is not.

    It is YOUR copy of each file (the set's ``mine``), not the disk's: the disk
    may have been overwritten by an update since, which is the case this module
    exists for. A file the set deleted cannot be exported and is named in the
    note instead. Returns ``(zip bytes, {"files", "created", "deleted"})``.
    """
    meta = load(name)
    files, created, deleted = [], [], []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, base, mine in _changed(meta):
            if mine is None:
                deleted.append(rel)
                continue
            z.writestr("data/" + rel, mine)
            files.append(rel)
            if base is None:
                created.append(rel)
        lines = [f"Changed files from {meta.get('mod', '?')} (change set {meta['name']}),",
                 f"exported {time.strftime('%Y-%m-%d %H:%M')} by the Medieval 2 GUI Toolkit.",
                 "",
                 "Unzip into the mod's own folder (the one holding data/) to put them in place.",
                 "Each file is the version you last saved with the toolkit.", ""]
        lines += [f"{len(files)} file(s):"] + [
            f"  data/{r}{'  (new)' if r in created else ''}" for r in files]
        if deleted:
            lines += ["", f"{len(deleted)} file(s) your edits deleted, so not in this zip:"]
            lines += [f"  data/{r}" for r in deleted]
        z.writestr(FILES_NOTE, "\r\n".join(lines) + "\r\n")
    return buf.getvalue(), {"files": files, "created": created, "deleted": deleted}


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
           "created": meta.get("created", ""), "imported": True, "active": False,
           "files": files})
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
