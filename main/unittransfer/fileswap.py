"""One file out of a mod, or one file into it (Phase 62, B3).

Mylae's tool pushes a single file into a mod or pulls one out, and the pieces
here were all shaped for one job each - the map export, a faction's TGA, a
unit import. This is the general one: **any file under ``data/``** can be
downloaded as it is, and **any file can be put in**, replacing one that is
there (backed up) or adding one that is not, with one Undo either way.

Putting a file in is where a mod gets broken, so the plan says what it knows
before anything is written, and each check is one the files themselves prove:

* **an encoding change is named.** The game's ``text/*.txt`` files are UTF-16
  with a byte-order mark, and a copy saved by an editor that "helpfully" wrote
  UTF-8 is the classic way a mod's text stops loading. The old file's encoding
  is read off its own bytes (:func:`unittransfer.rawtext.sniff`) and compared.
* **the readers are asked.** For the five files Raw text already knows how to
  read back - ``descr_strat.txt``, ``descr_regions.txt``, the win conditions,
  the roster and the EDU - the new text is read by the same reader, and
  anything new it reports is listed (:func:`unittransfer.rawtext._reader_notes`).
* **``text/*.txt`` recompiles its ``.strings.bin``**, as every text save here
  does, since the game reads the compiled copy.
* **a ``.dds`` put onto a ``.texture`` is wrapped** in the game's 48-byte
  header (:mod:`unittransfer.modelexport`), because that is what a modder
  holding a DDS from an image editor means.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

#: 64 MB is more than any single mod file measured (DaC's pack.dat aside, which
#: is not a file anyone swaps by hand), and it keeps a mistaken upload from
#: filling a backup folder.
MAX_BYTES = 64 * 1024 * 1024

_SAFE = re.compile(r"^[A-Za-z0-9_ .\-()'#&+,!\[\]{}~@$%=]+$")


class SwapError(ValueError):
    pass


def resolve(mod, rel: str) -> Path:
    """``data/<rel>`` for a path from the page, held inside ``data/``."""
    rel = str(rel or "").replace("\\", "/").strip().lstrip("/")
    if rel.lower().startswith("data/"):
        rel = rel[5:]
    parts = [x for x in rel.split("/") if x]
    if not parts or any(x in (".", "..") or ":" in x or not _SAFE.match(x) for x in parts):
        raise SwapError(f"{rel or 'that'} is not a path inside the mod's data folder")
    data = Path(mod.data).resolve()
    path = (data / "/".join(parts)).resolve()
    if data not in path.parents:
        raise SwapError(f"{rel} is not inside the mod's data folder")
    return path


def export(mod, rel: str) -> bytes:
    path = resolve(mod, rel)
    if not path.is_file():
        raise SwapError(f"{getattr(mod, 'name', '?')} has no data/{rel}")
    return path.read_bytes()


@dataclass
class PutPlan:
    mod: object = None
    rel: str = ""
    data: bytes = b""
    replaces: bool = False
    before: int = 0
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {"rel": self.rel, "bytes": len(self.data), "before": self.before,
                "replaces": self.replaces, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.data)}


def plan_put(mod, rel: str, data: bytes, replace: bool = False) -> PutPlan:
    """What putting ``data`` at ``data/<rel>`` would do. ``replace`` must be
    true to write over a file that is there - a put never overwrites by
    accident."""
    from . import modelexport, rawtext
    p = PutPlan(mod=mod, rel=str(rel or "").replace("\\", "/").strip().lstrip("/"))
    if p.rel.lower().startswith("data/"):
        p.rel = p.rel[5:]
    try:
        path = resolve(mod, p.rel)
    except SwapError as e:
        p.errors.append(str(e))
        return p
    if not data:
        p.errors.append("the file is empty")
        return p
    if len(data) > MAX_BYTES:
        p.errors.append(f"{len(data) / 1048576:.0f} MB is more than the {MAX_BYTES // 1048576} MB "
                        f"a single put takes")
        return p
    if path.is_dir():
        p.errors.append(f"data/{p.rel} is a folder")
        return p
    if p.rel.lower().endswith(".texture") and data[:4] == b"DDS ":
        from . import sprites
        try:
            data = modelexport.dds_to_texture(data)
        except sprites.SpriteError as e:
            p.errors.append(f"this DDS cannot go into a .texture: {e}")
            return p
        p.changes.append("a DDS image, wrapped in the game's 48-byte .texture header")
    p.data = data
    if path.is_file():
        p.replaces = True
        old = path.read_bytes()
        p.before = len(old)
        if not replace:
            p.errors.append(f"data/{p.rel} is already in the mod; say to replace it")
            return p
        if old == data:
            p.errors.append("it is the same file, byte for byte")
            return p
        p.changes.append(f"data/{p.rel} replaced ({len(old):,} -> {len(data):,} bytes), "
                         f"the old one backed up")
        if p.rel.lower().endswith(rawtext.TEXT_SUFFIXES):
            was, now = rawtext.sniff(old), rawtext.sniff(data)
            if was.name != now.name or was.bom != now.bom:
                p.warnings.append(f"the file was {was.label} and this one is {now.label} - "
                                  f"the game reads the file as it finds it, so a text file "
                                  f"that changes encoding is read as noise")
            try:
                p.warnings += rawtext._reader_notes(p.rel, rawtext.decode(old, was),
                                                    rawtext.decode(data, now))
            except (UnicodeDecodeError, LookupError):
                p.warnings.append(f"this file does not decode as {now.label}")
    else:
        p.changes.append(f"+ data/{p.rel} ({len(data):,} bytes), a new file")
        if p.rel.lower().endswith(rawtext.TEXT_SUFFIXES) and p.rel.lower().startswith("text/") \
                and not rawtext.sniff(data).name.startswith("utf-16"):
            p.warnings.append("the game's text/ files are UTF-16 with a byte-order mark, "
                              "and this one is not")
    if p.rel.lower().startswith("text/") and p.rel.lower().endswith(".txt"):
        p.changes.append(f"data/{p.rel}.strings.bin recompiled, which is the copy the game reads")
    return p


def apply_put(p: PutPlan) -> Dict:
    from . import cleaner, config
    from .logutil import file_op, log

    if p.errors or not p.data:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to put"))
    mod = p.mod
    data_dir = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = data_dir / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    target = keep(p.rel)
    target.write_bytes(p.data)
    file_op("WRITE", target, f"{len(p.data)} bytes (put)")
    out: Dict = {"id": tid, "rel": p.rel, "bytes": len(p.data)}
    if p.rel.lower().startswith("text/") and p.rel.lower().endswith(".txt"):
        keep(p.rel + ".strings.bin")
        out["strings_bin"] = cleaner.refresh_strings_bin(mod.root, "data/" + p.rel + ".strings.bin")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "rawtext", "action": "put",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.rel, "resolved_type": p.rel,
        "options": {"replaces": p.replaces}, "applied": True, "undone": False, "note": "",
        "summary": f"put data/{p.rel} in {mod.name}", "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("PUT    data/%s in %s, %d bytes, id=%s", p.rel, mod.name, len(p.data), tid)
    out["record"] = rec
    return out
