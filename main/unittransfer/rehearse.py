"""The Health screen's deep check. It takes a pending change set, lays the
records that would go onto a mod into a disposable copy of the mod, runs the
health checks on the real mod and on the copy, and reports which findings the
change would add, which it would clear and how many stay either way.

The real mod is never written. The copy is almost free: folders the change does
not touch are joined to the mod's own with junctions, and the files on the way
to a changed file are hard links. The copy is always removed before returning.

Written independently from a description of the behaviour (2026-11-06); the
feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

from . import changesets, health
from . import i18n as _i18n
from .mod import Mod

# Extensions the checks read as text; only these are copied when links fail.
TEXT_EXT = {".txt", ".xml", ".db", ".modeldb", ".lua", ".cfg", ".ini", ".json",
            ".bin", ".lnt", ".csv", ".nut"}


class RehearseError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class _Copy:
    """Builds the lookalike data folder and remembers what it made."""

    def __init__(self, touched: List[str]):
        self.touched = {r.replace("\\", "/").lower() for r in touched}
        self.junctions: List[str] = []
        self.linked = 0
        self.copied = 0
        self.links_work = True

    def _holds_change(self, rel_dir: str) -> bool:
        prefix = rel_dir.lower() + "/"
        return any(t.startswith(prefix) for t in self.touched)

    def _file(self, src: str, dst: str) -> None:
        if self.links_work:
            try:
                os.link(src, dst)
                self.linked += 1
                return
            except OSError:
                self.links_work = False
        if os.path.splitext(src)[1].lower() in TEXT_EXT:
            shutil.copyfile(src, dst)
            self.copied += 1

    def _junction(self, src: str, dst: str) -> bool:
        try:
            import _winapi
            _winapi.CreateJunction(src, dst)
        except (ImportError, AttributeError, OSError):
            return False
        self.junctions.append(dst)
        self.linked += 1
        return True

    def build(self, src: str, dst: str, rel_dir: str = "") -> None:
        os.makedirs(dst, exist_ok=True)
        with os.scandir(src) as it:
            entries = sorted(it, key=lambda e: e.name)
        for e in entries:
            rel = (rel_dir + "/" + e.name) if rel_dir else e.name
            target = os.path.join(dst, e.name)
            if e.is_dir():
                if not self._holds_change(rel) and self._junction(e.path, target):
                    continue
                self.build(e.path, target, rel)
            elif rel.lower() not in self.touched:
                self._file(e.path, target)


def _write_fresh(path: Path, content: bytes) -> None:
    """Replace a name in the copy without writing through a link."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        path.unlink()
    if content is None:
        return
    tmp = path.with_name(path.name + ".rehearse")
    with open(tmp, "xb") as f:
        f.write(content)
    os.replace(tmp, path)


def _drop(copy: _Copy, tmp: str) -> None:
    # Junctions go first, by their own names, so nothing is deleted through one.
    for j in copy.junctions:
        try:
            os.rmdir(j)
        except OSError:
            try:
                os.unlink(j)
            except OSError:
                pass
    shutil.rmtree(tmp, ignore_errors=True)


def _identity(f: dict) -> tuple:
    what = f.get("what")
    if not what:
        what = re.sub(r"\d+", "#", str(f.get("message") or ""))
    return (f.get("source"), f.get("code"), f.get("file"), what)


def _by_identity(findings: List[dict]) -> Dict[tuple, dict]:
    out: Dict[tuple, dict] = {}
    for f in findings:
        out.setdefault(_identity(f), f)
    return out


def _rank(f: dict) -> int:
    sev = f.get("severity")
    return health.SEVERITIES.index(sev) if sev in health.SEVERITIES else len(health.SEVERITIES)


def run(mod, set_name, picks=None) -> dict:
    try:
        port = changesets.plan_port(set_name, mod)
    except (changesets.ChangeSetError, OSError, KeyError) as e:
        raise RehearseError(getattr(e, "message", None) or str(e))

    if picks:
        want = {int(k) for k, v in picks.items() if v == "mine"}
        chosen = {i.id: "mine" for i in port.items if i.id in want}
    else:
        chosen = {i.id: "mine" for i in port.items if i.default}
    if not chosen:
        raise RehearseError(_i18n.msg(
            "eng.rehearse.nothing",
            "nothing in {set} would go onto this mod, so there is nothing to rehearse",
            set=set_name))
    rels = sorted({i.rel for i in port.items if i.id in chosen})
    safe = [changesets._safe_rel(r) for r in rels]

    root = Path(mod.root)
    tmp = tempfile.mkdtemp(prefix="ut_rehearse_")
    copy = _Copy(safe)
    try:
        copy_root = Path(tmp) / root.name
        copy.build(str(mod.data), str(copy_root / "data"))
        for rel, safe_rel in zip(rels, safe):
            _write_fresh(copy_root / "data" / safe_rel, changesets._assemble(port, rel, chosen))
        ghost = Mod(copy_root)
        ghost.flag_root = root
        before = health.run(mod)
        after = health.run(ghost)
    finally:
        _drop(copy, tmp)

    was = _by_identity(before.get("findings", []))
    now = _by_identity(after.get("findings", []))
    real, fake = str(root), str(copy_root)
    added = []
    for k, f in now.items():
        if k not in was:
            f = dict(f)
            if isinstance(f.get("message"), str):
                f["message"] = f["message"].replace(fake, real)
            added.append(f)
    cleared = [f for k, f in was.items() if k not in now]
    added.sort(key=_rank)
    cleared.sort(key=_rank)

    failed_before = {s.get("id") for s in before.get("sources", []) if s.get("state") == "failed"}
    failed = [s for s in after.get("sources", [])
              if s.get("state") == "failed" and s.get("id") not in failed_before]
    return {
        "mod": getattr(mod, "name", "") or "",
        "set": set_name,
        "files": rels,
        "records": len(chosen),
        "counts": port.counts(),
        "linked": copy.linked,
        "copied": copy.copied,
        "added": added,
        "cleared": cleared,
        "same": sum(1 for k in now if k in was),
        "failed": failed,
        "ms": (before.get("ms") or 0) + (after.get("ms") or 0),
    }
