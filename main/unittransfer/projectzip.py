"""A campaign as a zip, and any ``data/`` zip loaded back into a mod (Phase 71, D12).

TWMapReader's ``exportProject`` / ``loadProject``: everything the map editor
works on, packaged, shareable, and loadable into another copy. Half of it was
here already: *My changes* (Phase 52) exports a change set for porting and the
files it changed as a plain ``data/`` zip, and the faction screen (Phase 56)
exports a faction's files the same way. **What nothing did was take such a zip
back.** So this is the two missing halves:

* **Out: a campaign.** The map layers and text files under
  ``world/maps/base``, the campaign's own folder under ``world/maps/campaign``,
  and the region and settlement names in ``text/``, at their own paths under
  ``data/``, with a ``project.json`` saying what it is. The compiled
  ``map.rwm`` is left out: the game rebuilds it from the files beside it, and a
  stale one is the classic reason a map edit does not show. So, unless asked,
  is every file the game never reads under that name: **measured, ROCSS's
  campaign carries 22 copies (84 MB: ``campaign_script - Kopie.txt``,
  ``descr_strat hmm.txt``, ``map_regions back.tga``...) and DaC's two zips, two
  ``.bak`` files and a GIMP ``.xcf``**. A name with a space in it, an archive, a backup copy
  and an image editor's source file are left out and listed.
* **In: any zip laid out under ``data/``**, whoever made it. Each file is
  planned with Phase 62's single-file put (:func:`unittransfer.fileswap.plan_put`):
  the path held inside ``data/``, the size capped, an encoding change named, the
  file's own reader asked about the new text, ``text/*.txt`` recompiling its
  ``.strings.bin``. On top of that, per file: **new**, **the same** (skipped),
  or **replaces** with the records that differ named, by the same record split
  *My changes* ports with (an EDU unit, a region, a text key). A ``map.rwm`` in
  the zip is never written, and a compiled map that the loaded files make stale
  is deleted, backed up, as every map write here does. The whole load is one
  backup and one Undo.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import fileswap

MANIFEST = "project.json"
NOTE = "PROJECT.txt"
#: a whole load: several times the largest campaign measured (DaC's base map
#: and imperial campaign, custom tiles included), and it keeps a mistaken
#: upload from filling a backup folder
MAX_TOTAL = 512 * 1024 * 1024
#: how many records a changed file names before the rest are counted
NAME_RECORDS = 12


class ProjectError(ValueError):
    pass


def _rel(p: Path, data: Path) -> str:
    return p.relative_to(data).as_posix()


# ---------------------------------------------------------------------------
# out: a campaign


#: what marks a file the game never reads under that name
SIDE_SUFFIXES = (".zip", ".rar", ".7z", ".bak", ".old", ".orig", ".xcf", ".psd")


def side_file(name: str) -> str:
    """Why a file is a modder's side copy rather than one the game reads, or
    ``""``. The game's own names never hold a space."""
    low = name.lower()
    if " " in name:
        return "a name with a space in it, which no file the game reads has"
    if low.endswith(SIDE_SUFFIXES) or low.endswith("~"):
        return "an archive, a backup copy or an image editor's source"
    return ""


def campaign_files(mod, campaign: str = "", everything: bool = False) -> tuple:
    """``(files, left_out)`` of one campaign's map project, as paths under
    ``data/``; ``left_out`` is ``[(rel, why)]``, empty with ``everything``."""
    from . import campmap, campstrat
    data = Path(mod.data)
    camp = campstrat.campaign_rel(campaign)
    out: List[str] = []
    left: List[tuple] = []
    for folder in (data / campmap.BASE_REL, data / campstrat.CAMPAIGN_DIR_REL / camp):
        if not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*")):
            if not p.is_file():
                continue
            if p.name.lower() == campmap.RWM_NAME:
                left.append((_rel(p, data), "the compiled map, which the game builds again"))
                continue
            why = "" if everything else side_file(p.name)
            if why:
                left.append((_rel(p, data), why))
                continue
            out.append(_rel(p, data))
    for rel in (campmap.REGION_NAMES_REL, campmap.REGION_NAMES_REL + ".strings.bin"):
        if (data / rel).is_file():
            out.append(rel)
    return out, left


def export_campaign(mod, campaign: str = "", everything: bool = False) -> tuple:
    """``(zip bytes, manifest)`` for one campaign."""
    from . import __version__, campstrat
    data = Path(mod.data)
    rels, left = campaign_files(mod, campaign, everything)
    if not rels:
        raise ProjectError(f"{getattr(mod, 'name', 'this mod')} has no campaign map files to export")
    camp = campstrat.campaign_rel(campaign)
    files = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in rels:
            raw = (data / rel).read_bytes()
            z.writestr("data/" + rel, raw)
            files.append({"rel": rel, "bytes": len(raw),
                          "sha1": hashlib.sha1(raw).hexdigest()})
        manifest = {"kind": "campaign", "mod": getattr(mod, "name", ""), "campaign": camp,
                    "made": time.strftime("%Y-%m-%d %H:%M"), "tool": __version__,
                    "files": files,
                    "left_out": [{"rel": r, "why": w} for r, w in left]}
        z.writestr(MANIFEST, json.dumps(manifest, indent=1))
        z.writestr(NOTE, "\r\n".join([
            f"The {camp} campaign of {manifest['mod']}, exported {manifest['made']} by the",
            "Medieval 2 GUI Toolkit.", "",
            "Unzip into a mod's own folder (the one holding data/) to put it in place, or",
            "load it with the toolkit, which says what each file would replace first.",
            "map.rwm is not included: the game builds it again from these files.", "",
            f"{len(files)} file(s):"] + [f"  data/{f['rel']}" for f in files]
            + ([f"", f"{len(left)} file(s) left out:"] + [f"  data/{r} - {w}" for r, w in left]
               if left else [])) + "\r\n")
    return buf.getvalue(), manifest


# ---------------------------------------------------------------------------
# in: any data/ zip


@dataclass
class FilePlan:
    rel: str
    state: str                      # new, same, replaces, refused, skipped
    bytes: int = 0
    before: int = 0
    records: List[str] = field(default_factory=list)
    records_more: int = 0
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    why: str = ""
    put: object = None

    def payload(self) -> dict:
        return {"rel": self.rel, "state": self.state, "bytes": self.bytes,
                "before": self.before, "records": self.records,
                "records_more": self.records_more, "changes": self.changes,
                "warnings": self.warnings, "why": self.why}


@dataclass
class LoadPlan:
    mod: object = None
    files: List[FilePlan] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    #: map.rwm files the loaded map files make stale, deleted on apply
    stale: List[str] = field(default_factory=list)
    ignored: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def writes(self) -> List[FilePlan]:
        return [f for f in self.files if f.state in ("new", "replaces")]

    def payload(self) -> dict:
        counts: Dict[str, int] = {}
        for f in self.files:
            counts[f.state] = counts.get(f.state, 0) + 1
        return {"files": [f.payload() for f in self.files], "counts": counts,
                "manifest": {k: v for k, v in self.manifest.items() if k != "files"},
                "stale": list(self.stale), "ignored": list(self.ignored),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.writes())}


def _records(rel: str, old: bytes, new: bytes) -> tuple:
    """``(named, more)``: the records that differ between the mod's copy and
    the zip's, by *My changes*' record split."""
    from . import changesets
    try:
        diff = changesets._record_diff(rel, old, new)
    except Exception:
        return [], 0
    named = [f"{d['kind']} {d['key']}" if d["key"] != changesets.FILE_KEY else "edited"
             for d in diff]
    return named[:NAME_RECORDS], max(0, len(named) - NAME_RECORDS)


def plan_load(mod, raw: bytes, replace: bool = True) -> LoadPlan:
    """What loading the zip ``raw`` into ``mod`` would do, file by file.
    ``replace`` false keeps every file the mod already has as it is."""
    from . import campmap
    p = LoadPlan(mod=mod)
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        p.errors.append(f"not a zip ({e})")
        return p
    try:
        p.manifest = json.loads(z.read(MANIFEST).decode("utf-8"))
    except (KeyError, ValueError, UnicodeDecodeError):
        p.manifest = {}
    total = 0
    data = Path(mod.data)
    map_rels: List[str] = []
    for info in z.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace("\\", "/")
        if name in (MANIFEST, NOTE, "CHANGED_FILES.txt"):
            continue
        low = name.lower()
        if not low.startswith("data/"):
            p.ignored.append(name)
            continue
        rel = name[5:]
        if rel.rsplit("/", 1)[-1].lower() == campmap.RWM_NAME:
            p.files.append(FilePlan(rel, "skipped", info.file_size,
                                    why="a compiled map: the game builds it again from the files "
                                        "beside it, and a stale one hides the edits"))
            continue
        total += info.file_size
        if total > MAX_TOTAL:
            p.errors.append(f"more than {MAX_TOTAL // 1048576} MB in one load")
            return p
        body = z.read(info)
        try:
            target = fileswap.resolve(mod, rel)
        except fileswap.SwapError as e:
            p.files.append(FilePlan(rel, "refused", len(body), why=str(e)))
            continue
        old = target.read_bytes() if target.is_file() else None
        if old is not None and old == body:
            p.files.append(FilePlan(rel, "same", len(body), len(old)))
            continue
        if old is not None and not replace:
            p.files.append(FilePlan(rel, "skipped", len(body), len(old),
                                    why="the mod has this file, and loading was told to keep "
                                        "what is there"))
            continue
        if not body:
            # an empty descr_disasters.txt is a real file, and the put refuses
            # one only because an empty upload is usually a mistake
            put = fileswap.PutPlan(mod=mod, rel=rel, data=b"", replaces=old is not None,
                                   changes=[f"data/{rel}, an empty file"])
        else:
            put = fileswap.plan_put(mod, rel, body, replace=True)
        if put.errors:
            p.files.append(FilePlan(rel, "refused", len(body), len(old or b""),
                                    why="; ".join(put.errors)))
            continue
        fp = FilePlan(rel, "replaces" if old is not None else "new", len(put.data),
                      len(old or b""), changes=list(put.changes), warnings=list(put.warnings),
                      put=put)
        if old is not None:
            fp.records, fp.records_more = _records(rel, old, put.data)
        p.files.append(fp)
        if rel.lower().startswith("world/maps/"):
            map_rels.append(rel)
    for rel in map_rels:
        try:
            stale = campmap.stale_rwm(mod, rel)
        except Exception:
            stale = []
        for r in stale:
            if r not in p.stale and (data / r).is_file():
                p.stale.append(r)
    if not p.files and not p.errors:
        p.errors.append("the zip has no files under data/")
    elif not p.writes() and not p.errors:
        p.errors.append("nothing to load: every file is refused, skipped or already the same")
    p.files.sort(key=lambda f: ({"replaces": 0, "new": 1, "refused": 2, "skipped": 3,
                                 "same": 4}.get(f.state, 5), f.rel.lower()))
    return p


def apply_load(p: LoadPlan) -> Dict:
    """Write every file the plan would, delete the stale compiled maps, back
    all of it up first, and log one Undo."""
    from . import cleaner, config
    from .logutil import file_op, log
    if p.errors or not p.writes():
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to load"))
    mod = p.mod
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = data / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, bpath)
            if rel not in manifest["backed_up"]:
                manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        elif rel not in manifest["created"]:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    bins = []
    for f in p.writes():
        target = keep(f.rel)
        target.write_bytes(f.put.data)
        file_op("WRITE", target, f"{len(f.put.data)} bytes (loaded)")
        if f.rel.lower().startswith("text/") and f.rel.lower().endswith(".txt"):
            bin_rel = f.rel + ".strings.bin"
            if not any(x.rel == bin_rel for x in p.writes()):
                keep(bin_rel)
                bins.append(cleaner.refresh_strings_bin(mod.root, "data/" + bin_rel))
    for rel in p.stale:
        target = keep(rel)
        target.unlink()
        file_op("DELETE", target, "stale compiled map")
    counts = p.payload()["counts"]
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "projectzip", "action": "load",
        "source": p.manifest.get("mod") or "a zip", "source_root": "",
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.manifest.get("campaign") or "data/ zip",
        "resolved_type": p.manifest.get("campaign") or "data/ zip",
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": f"loaded {counts.get('new', 0)} new and {counts.get('replaces', 0)} replaced "
                   f"file(s) into {mod.name}"
                   + (f", {len(p.stale)} stale map.rwm deleted" if p.stale else ""),
        "warnings": [w for f in p.writes() for w in f.warnings],
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("LOAD   %d file(s) into %s, id=%s", len(p.writes()), mod.name, tid)
    return {"id": tid, "record": rec, "strings_bin": bins}
