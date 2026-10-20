"""A deep check: a change set's port rehearsed on a copy, every check run on it (96e2).

The Pfadfinder-Adam (formerly MasterOogwayHomebrew) campaign editor applies its
pending edits to an in-memory copy of the mod and reports what would break,
writing nothing. This toolkit writes as each screen saves, so what is pending
here is a **change set** not yet put onto the mod: a port onto a new version
of it, or a set made on another folder. Its port is planned as it always is
(:func:`changesets.plan_port`), and every record that would go in by default
- or the ones the caller ticked - is laid into a rehearsal copy.

**The copy costs no space.** It is a folder in the temp directory whose files
are hard links to the mod's own; only the files the port changes are written,
and each is unlinked first, so the mod's own file is never opened for writing.
A folder the port does not touch is a directory junction to the mod's
own, so a mod of forty thousand files is mirrored in well under a second. The
copy is removed when the check is done, each junction by its own name first. Where the temp folder is on
another drive than the mod, links cannot be made and the text files are copied
instead (the checks read text; textures and models are only looked for).

**What comes back** is :func:`health.run` on the mod and on the copy, compared
finding by finding: what the port would add, what it would clear, and what is
there either way. A finding is the same finding when its source, code, file and
``what`` match, or its message once its numbers are taken out, so a line number
that moved does not read as a new fault.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import changesets, health
from . import i18n as _i18n

#: what a check reads when a copy has to be made instead of links
TEXT_EXT = {".txt", ".xml", ".db", ".modeldb", ".lua", ".cfg", ".ini", ".json",
            ".bin", ".lnt", ".csv", ".nut"}


class RehearseError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _junction(src: str, dst: Path) -> bool:
    """A directory junction (Windows; no rights needed), else False."""
    try:
        import _winapi
        _winapi.CreateJunction(str(src), str(dst))
        return True
    except (ImportError, OSError, AttributeError):
        return False


def _mirror(src: Path, dst: Path, touched: List[str], joins: List[Path]) -> Tuple[int, int]:
    """``src`` under ``dst`` without copying it: a folder that holds none of the
    ``touched`` files is a junction to the mod's own, the rest are folders of
    hard links; where neither can be made, the text files are copied. Every
    junction made is recorded in ``joins``. Returns (linked, copied)."""
    linked = copied = 0
    can_link = [True]
    want = [t.replace("\\", "/").lower() for t in touched]

    def walk(a: Path, b: Path, rel: str) -> None:
        nonlocal linked, copied
        b.mkdir(parents=True, exist_ok=True)
        for e in os.scandir(a):
            r = f"{rel}{e.name}".lower()
            if e.is_dir(follow_symlinks=False):
                if not any(w.startswith(r + "/") for w in want) and _junction(e.path, b / e.name):
                    joins.append(b / e.name)
                    linked += 1
                    continue
                walk(Path(e.path), b / e.name, r + "/")
                continue
            if can_link[0]:
                try:
                    os.link(e.path, b / e.name)
                    linked += 1
                    continue
                except OSError:
                    can_link[0] = False
            if os.path.splitext(e.name)[1].lower() in TEXT_EXT:
                shutil.copy2(e.path, b / e.name)
                copied += 1
    walk(src, dst, "")
    return linked, copied


def _remove(work: Path, joins: List[Path]) -> None:
    """Take the copy away: each junction by its own name first, so nothing is
    ever deleted through one, then the rest (hard links are names only)."""
    for j in reversed(joins):
        try:
            os.rmdir(j)
        except OSError:
            try:
                os.unlink(j)
            except OSError:
                pass
    shutil.rmtree(work, ignore_errors=True)


def _put(path: Path, data: Optional[bytes]) -> None:
    """Write one file of the copy without ever writing through a link."""
    if path.exists() or path.is_symlink():
        os.remove(path)                      # the name only - the mod's file is untouched
    if data is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".rehearse")
    with open(tmp, "xb") as fh:
        fh.write(data)
    os.replace(tmp, path)


_NUM = re.compile(r"\d+")


def _ident(f: Dict) -> Tuple:
    return (f.get("source"), f.get("code"), f.get("file"),
            f.get("what") or _NUM.sub("#", f.get("message") or ""))


def run(mod, set_name: str, picks: Optional[Dict] = None) -> Dict:
    from .mod import Mod

    try:
        port = changesets.plan_port(set_name, mod)
    except (changesets.ChangeSetError, OSError, KeyError) as e:
        raise RehearseError(getattr(e, "message", None) or str(e)) from None
    if picks:
        chosen = {int(k): "mine" for k, v in picks.items() if v == "mine"}
    else:
        chosen = {i.id: "mine" for i in port.items if i.default}
    if not chosen:
        raise RehearseError(_i18n.msg("eng.rehearse.nothing", "nothing in {set} would go onto this mod, so there is nothing to rehearse", set=set_name))
    rels = sorted({i.rel for i in port.items if i.id in chosen})

    work = Path(tempfile.mkdtemp(prefix="ut_rehearse_"))
    joins: List[Path] = []
    try:
        root = work / Path(mod.root).name
        root.mkdir()
        linked, copied = _mirror(Path(mod.data), root / "data", rels, joins)
        for rel in rels:
            changesets._safe_rel(rel)
            _put(root / "data" / rel, changesets._assemble(port, rel, chosen))
        copy = Mod(root)
        copy.flag_root = Path(mod.root)
        before = health.run(mod)
        after = health.run(copy)
    finally:
        _remove(work, joins)

    old = {_ident(f): f for f in before["findings"]}
    new = {_ident(f): f for f in after["findings"]}
    root_s = str(root)

    def clean(f: Dict) -> Dict:
        f = dict(f)
        f["message"] = (f.get("message") or "").replace(root_s, str(mod.root))
        return f
    added = [clean(f) for k, f in new.items() if k not in old]
    cleared = [f for k, f in old.items() if k not in new]
    sev = {s: i for i, s in enumerate(health.SEVERITIES)}
    added.sort(key=lambda f: sev.get(f.get("severity"), 9))
    cleared.sort(key=lambda f: sev.get(f.get("severity"), 9))
    return {"mod": getattr(mod, "name", ""), "set": set_name,
            "files": rels, "records": len(chosen), "counts": port.counts(),
            "linked": linked, "copied": copied,
            "added": added, "cleared": cleared,
            "same": len([k for k in new if k in old]),
            "failed": [s for s in after["sources"] if s["state"] == "failed"
                       and not any(b["id"] == s["id"] and b["state"] == "failed" for b in before["sources"])],
            "ms": before["ms"] + after["ms"]}
