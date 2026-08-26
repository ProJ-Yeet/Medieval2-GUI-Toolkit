"""Unit cards and info cards — the same picture, filed under thirty factions.

The game looks a unit's card up under the *player's* faction folder:
``data/ui/units/<faction>/#<dictionary>.tga`` for the little recruitment card,
``data/ui/unit_info/<faction>/<dictionary>_info.tga`` for the big one. So a unit
that thirty factions can field needs its card in thirty folders — and mods do
exactly that, byte for byte identical, thirty times over. Divide and Conquer
ships 4,294 info cards for 917 units: 1.2 GB where 264 MB of it is art for units
that no longer exist and most of the rest is the same picture copied out.

The way out is the folder the engine falls back to. ``data/ui/units/mercs`` and
``data/ui/unit_info/merc`` are searched for any unit whose own faction folder has
nothing — which is why DaC already keeps 1,181 of its 1,554 cards there and
nowhere else. One copy in the merc folder does the job of thirty, and this module
is the pass that gets a mod from one to the other:

  * **cards for units that are gone.** A dictionary no unit in the mod claims —
    ``export_descr_unit.txt`` and any M2TWEOP unit file — is art the game can
    never reach. Offered for removal.
  * **the same picture in several folders.** Every copy hashed; when they all
    agree, one goes to the merc folder and the rest are removed. Nothing to
    decide, because there is only one picture.
  * **genuinely different pictures per faction.** Some mods really do give a
    unit a different card per faction. Those are NOT consolidated on their own —
    the module lists the distinct pictures and who holds each, and the choice of
    which becomes the single copy (or to leave the set alone) is the user's.

**Nothing is deleted.** Everything removed is copied to an export folder in the
mod's own layout first and backed up second, so 🕑 Log → Undo restores the mod
exactly — the contract :mod:`unittransfer.bmdb` and :mod:`unittransfer.stratmap`
make.

Two deliberate refusals, both of them "we cannot prove this is safe":

  * a unit whose ``card_pic_dir`` / ``info_pic_dir`` is **pinned** to a folder of
    its own is left out of consolidation. The pin is a mod saying "look here",
    and this pass is not the place to find out whether the fallback still runs
    after it;
  * a file in these folders that is **not** shaped like a card — the agent
    pictures (``spy.tga``, ``diplomat.tga``), loose art somebody dropped in — is
    counted, reported and never touched. Its name says nothing about which unit
    it belongs to, so there is no honest way to call it unused.
"""
from __future__ import annotations

import hashlib
import logging
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import config, edit, luascan
from .logutil import counted, file_op, fingerprint, log
from .mod import Mod

#: Extensions the game reads a card from, in the order :meth:`Mod._find_icon`
#: prefers them.
EXTS = (".tga", ".dds")

UNUSED_SUBDIR = "unused_files"
README_NAME = "README.txt"

Progress = Optional[Callable[[int, str], None]]


@dataclass(frozen=True)
class Kind:
    """One of the two pictures a unit has, and how the game files it."""
    key: str                 # "card" | "info"
    base: str                # under data/
    merc: str                # the fallback folder inside `base`
    label: str               # what to call it on screen
    pattern: "re.Pattern"    # filename -> the dictionary it belongs to
    stem: str                # dictionary -> filename stem

    def filename(self, dictionary: str, ext: str = ".tga") -> str:
        return self.stem.format(dictionary) + ext

    def rel(self, folder: str, dictionary: str, ext: str = ".tga") -> str:
        return f"{self.base}/{folder}/{self.filename(dictionary, ext)}"


#: The card folder is ``mercs`` and the info folder is ``merc`` — not a typo on
#: either side, that is what the game ships and what :meth:`edu.Unit.card_dirs`
#: already searches.
CARD = Kind("card", "ui/units", "mercs", "unit card",
            re.compile(r"^#(.+)\.(?:tga|dds)$", re.IGNORECASE), "#{}")
INFO = Kind("info", "ui/unit_info", "merc", "info card",
            re.compile(r"^(.+)_info\.(?:tga|dds)$", re.IGNORECASE), "{}_info")
KINDS = (CARD, INFO)
BY_KEY = {k.key: k for k in KINDS}


def _reporter(progress: Progress) -> Callable[[float, str], None]:
    def report(pct: float, label: str) -> None:
        if progress is None:
            return
        try:
            progress(max(0, min(100, int(pct))), label)
        except Exception:
            logging.getLogger(__name__).debug("progress sink raised", exc_info=True)
    return report


def _digest(path: Path) -> str:
    """A content fingerprint, so "the same picture" is a fact and not a guess.

    Byte-identical is the only test used. Two visually identical TGAs saved by
    different tools are different files, and treating them as one would mean
    silently choosing which of two pictures a mod ships — this pass never does
    that. They come out as a variant set instead, and the user picks.
    """
    h = hashlib.blake2b(digest_size=16)
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


# ---------------------------------------------------------------------------
# what is on disk


@dataclass
class Copy:
    """One card file: which folder it is in, and what it is."""
    folder: str              # the faction folder's name, as it is on disk
    rel: str                 # data-relative path
    size: int = 0
    digest: str = ""


def scan(mod: Mod, kind: Kind,
         report: Optional[Callable[[float, str], None]] = None
         ) -> Tuple[Dict[str, List[Copy]], List[dict]]:
    """``dictionary -> [every copy of its picture]``, plus the files that are not one.

    One pass, hashing as it goes: on a mod with 4,000 info cards the hashing is
    the whole cost of the audit, and doing it here means the "are these the same
    picture" question is answered once rather than per caller.
    """
    base = mod.data / Path(kind.base)
    out: Dict[str, List[Copy]] = {}
    strays: List[dict] = []
    if not base.is_dir():
        return out, strays
    try:
        folders = sorted((p for p in base.iterdir() if p.is_dir()),
                         key=lambda p: p.name.lower())
    except OSError:
        return out, strays
    total = len(folders) or 1
    for i, folder in enumerate(folders):
        if report:
            report(i / total, folder.name)
        try:
            files = sorted(folder.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for f in files:
            if not f.is_file():
                continue
            rel = f.relative_to(mod.data).as_posix()
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            m = kind.pattern.match(f.name)
            if not m:
                strays.append({"rel": rel, "size": size})
                continue
            out.setdefault(m.group(1).lower(), []).append(
                Copy(folder=folder.name, rel=rel, size=size, digest=_digest(f)))
    if report:
        report(1.0, "")
    return out, strays


def _pinned(mod: Mod, kind: Kind) -> Dict[str, str]:
    """``dictionary -> the folder its *_pic_dir pins it to``, for units that pin one.

    Only a pin that is NOT the merc folder counts: pinning a unit at the very
    folder this pass consolidates into is agreement, not an obstacle.
    """
    out: Dict[str, str] = {}
    for u in mod.edu.units:
        raw = (u.card_pic_dir if kind is CARD else u.info_pic_dir) or ""
        pin = raw.strip().lower()
        if pin and pin not in (CARD.merc, INFO.merc) and u.dictionary:
            out[u.dictionary.lower()] = pin
    return out


def _live_dictionaries(mod: Mod) -> Dict[str, str]:
    """``dictionary -> the unit type that claims it``, EOP units included.

    This is the whole test for "is this card reachable": the game finds a card by
    the unit's ``dictionary``, so a dictionary no unit claims is art nothing can
    ever draw. ``Mod.edu.units`` already holds both the EDU's units and any
    M2TWEOP ones, which is exactly the roster wanted here — an EOP unit's card
    is filed the same way and must not look unused for living somewhere else.
    """
    return {u.dictionary.lower(): u.type for u in mod.edu.units if u.dictionary}


# ---------------------------------------------------------------------------
# the audit


def audit(mod: Mod, progress: Progress = None) -> dict:
    """Everything the card dialog needs: what is gone, what is duplicated, what differs."""
    say = _reporter(progress)
    say(3, "reading the mod's units")
    live = _live_dictionaries(mod)
    say(6, "reading the mod's .lua scripts")
    # Same safety net the other cleanups use: an M2TWEOP script can create a unit
    # with a dictionary that appears in no .txt, and its card must not look dead.
    if "lua_tokens" not in mod.__dict__:
        mod.__dict__["lua_tokens"] = luascan.scan(
            mod, lambda frac, where: say(6 + 10 * frac,
                                         f"reading .lua scripts{' — ' + where if where else ''}"))
    lua = mod.lua_tokens

    kinds = []
    span = 80 / len(KINDS)
    for n, kind in enumerate(KINDS):
        at = 16 + n * span
        say(at, f"reading data/{kind.base}")
        found, strays = scan(
            mod, kind,
            lambda frac, where, at=at: say(at + span * frac,
                                           f"reading data/{kind.base}"
                                           f"{'/' + where if where else ''}"))
        kinds.append(_classify(mod, kind, found, strays, live, lua))
    say(100, "done")
    out = {
        "mod": mod.name,
        "root": str(mod.root),
        "units": len(live),
        "lua_files": len(mod.lua_files),
        "kinds": kinds,
    }
    _log_audit(mod, out)
    return out


def _classify(mod: Mod, kind: Kind, found: Dict[str, List[Copy]], strays: List[dict],
              live: Dict[str, str], lua: dict) -> dict:
    """Sort one kind's dictionaries into gone / duplicated / different / already done."""
    pins = _pinned(mod, kind)
    merc = kind.merc.lower()
    unused: List[dict] = []
    dup: List[dict] = []
    variants: List[dict] = []
    pinned_rows: List[dict] = []
    lua_kept: List[dict] = []
    already = 0
    for name in sorted(found):
        copies = found[name]
        if name not in live:
            hit = lua.get(name)
            if hit:
                # named by a script and by nothing else — the same rule that
                # protects a battle model, for the same reason
                lua_kept.append({"name": name, "file": hit.label(),
                                 "in_comment": hit.in_comment,
                                 "files": [c.rel for c in copies]})
                continue
            unused.append({
                "name": name, "folders": [c.folder for c in copies],
                "files": [c.rel for c in copies],
                "bytes": sum(c.size for c in copies),
                "showing": copies[0].rel,
            })
            continue
        if name in pins:
            # a unit that pins its own folder: counted, never consolidated
            if len(copies) > 1 or copies[0].folder.lower() != merc:
                pinned_rows.append({"name": name, "unit": live[name], "pin": pins[name],
                                    "folders": [c.folder for c in copies]})
            continue
        if len(copies) == 1 and copies[0].folder.lower() == merc:
            already += 1
            continue
        by_digest: Dict[str, List[Copy]] = {}
        for c in copies:
            by_digest.setdefault(c.digest, []).append(c)
        row = {
            "name": name, "unit": live[name],
            "folders": [c.folder for c in copies],
            "options": [{
                "digest": d,
                "rel": _preferred(group, merc).rel,
                "folders": [c.folder for c in group],
                "size": group[0].size,
                "in_merc": any(c.folder.lower() == merc for c in group),
            } for d, group in sorted(by_digest.items(),
                                     key=lambda kv: (-len(kv[1]), kv[0]))],
        }
        # What consolidating saves: every copy but the one that stays.
        row["bytes_saved"] = sum(c.size for c in copies) - max(c.size for c in copies)
        (dup if len(by_digest) == 1 else variants).append(row)
    return {
        "kind": kind.key, "label": kind.label, "base": kind.base, "merc": kind.merc,
        "dictionaries": len(found),
        "file_count": sum(len(v) for v in found.values()),
        "bytes": sum(c.size for v in found.values() for c in v),
        "unused": unused,
        "unused_bytes": sum(u["bytes"] for u in unused),
        "duplicates": dup,
        "duplicate_bytes": sum(d["bytes_saved"] for d in dup),
        "variants": variants,
        "variant_bytes": sum(v["bytes_saved"] for v in variants),
        "already": already,
        "pinned": pinned_rows,
        "lua_kept": lua_kept,
        "strays": strays[:300],
        "stray_count": len(strays),
        "stray_bytes": sum(s["size"] for s in strays),
    }


def _preferred(group: List[Copy], merc: str) -> Copy:
    """Which copy of one identical set to keep: the merc one if there is one.

    Keeping the copy that is already where it is going means the common case
    writes no new file at all — it only deletes the other twenty-nine.
    """
    for c in group:
        if c.folder.lower() == merc:
            return c
    return group[0]


def _log_audit(mod: Mod, a: dict) -> None:
    log.info("CARDS  audit %s: %d units", mod.name, a["units"])
    for k in a["kinds"]:
        log.info("  %-5s %d dictionaries in %d file(s), %.1f MB — %d gone (%.1f MB), "
                 "%d duplicated (%.1f MB to save), %d with different pictures, "
                 "%d already merc-only, %d pinned, %d not a card",
                 k["kind"], k["dictionaries"], k["file_count"], k["bytes"] / 1048576,
                 len(k["unused"]), k["unused_bytes"] / 1048576,
                 len(k["duplicates"]), k["duplicate_bytes"] / 1048576,
                 len(k["variants"]), k["already"], len(k["pinned"]), k["stray_count"])


# ---------------------------------------------------------------------------
# cleanup


@dataclass
class CleanupRequest:
    target: str
    #: ``{"card": [dictionary, …], "info": […]}`` — art for units that are gone.
    remove: Dict[str, List[str]] = field(default_factory=dict)
    #: ``{"card": [dictionary, …]}`` — identical copies to fold into the merc folder.
    consolidate: Dict[str, List[str]] = field(default_factory=dict)
    #: ``{"card": {dictionary: digest}}`` — a variant set the user resolved by
    #: choosing which picture survives. Anything not in here is left alone.
    choose: Dict[str, Dict[str, str]] = field(default_factory=dict)


def cleanup_request_from_dict(d: dict) -> CleanupRequest:
    def names(key: str) -> Dict[str, List[str]]:
        raw = d.get(key) or {}
        return {k: [str(x).lower() for x in (raw.get(k) or [])] for k in BY_KEY}
    raw_choose = d.get("choose") or {}
    return CleanupRequest(
        target=(d.get("target") or "").strip(),
        remove=names("remove"),
        consolidate=names("consolidate"),
        choose={k: {str(n).lower(): str(h) for n, h in (raw_choose.get(k) or {}).items()}
                for k in BY_KEY},
    )


@dataclass
class CleanupPlan:
    mod: Mod
    request: CleanupRequest
    target: Optional[Path] = None
    #: ``(src abs, rel under data/)`` — the one copy that moves into the merc folder.
    copies: List[Tuple[Path, str]] = field(default_factory=list)
    exports: List[Tuple[Path, str]] = field(default_factory=list)
    deletes: List[str] = field(default_factory=list)
    removed: int = 0                       # dictionaries whose art went entirely
    consolidated: int = 0                  # dictionaries folded into the merc folder
    freed: int = 0                         # bytes that stop shipping
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"tidy {self.mod.name}'s unit and info cards"]
        lines += ["  " + c for c in self.changes]
        lines += ["  ! " + w for w in self.warnings]
        return "\n".join(lines)


def _resolve_target(mod: Mod, raw: str) -> Tuple[Optional[Path], str]:
    if not raw:
        return None, "choose a folder to move the removed cards into"
    try:
        target = Path(raw).expanduser().resolve()
    except OSError as exc:
        return None, f"bad destination: {exc}"
    if target == mod.root.resolve() or mod.root.resolve() in target.parents:
        return None, (f"'{target}' is inside {mod.name} — pick a folder outside the mod, "
                      "otherwise the files never actually leave it")
    if target.exists() and not target.is_dir():
        return None, f"'{target}' is a file, not a folder"
    return target, ""


def plan_cleanup(mod: Mod, req: CleanupRequest) -> CleanupPlan:
    """Work out exactly which files move, which are written and which go."""
    plan = CleanupPlan(mod=mod, request=req)
    target, err = _resolve_target(mod, req.target)
    plan.target = target
    if err:
        plan.errors.append(err)

    # Re-read the folders rather than trusting the request: an audit can be older
    # than the mod it describes, and this is the pass that deletes.
    live = _live_dictionaries(mod)
    for kind in KINDS:
        found, _strays = scan(mod, kind)
        pins = _pinned(mod, kind)
        merc = kind.merc.lower()

        for name in req.remove.get(kind.key, []):
            copies = found.get(name)
            if not copies:
                plan.warnings.append(f"no {kind.label} for '{name}' any more — skipped")
                continue
            if name in live:
                plan.warnings.append(
                    f"'{name}' is {live[name]}'s dictionary after all — its "
                    f"{kind.label} is kept")
                continue
            for c in copies:
                plan.exports.append((mod.data / c.rel, f"{UNUSED_SUBDIR}/data/{c.rel}"))
                plan.deletes.append(c.rel)
                plan.freed += c.size
            plan.removed += 1

        wanted = list(req.consolidate.get(kind.key, []))
        chosen = dict(req.choose.get(kind.key, {}))
        for name in wanted + [n for n in chosen if n not in wanted]:
            copies = found.get(name)
            if not copies:
                plan.warnings.append(f"no {kind.label} for '{name}' any more — skipped")
                continue
            if name not in live:
                plan.warnings.append(
                    f"no unit claims '{name}' — its {kind.label} is not consolidated")
                continue
            if name in pins:
                plan.warnings.append(
                    f"'{name}' pins its {kind.label} to '{pins[name]}' — left alone")
                continue
            digests = {c.digest for c in copies}
            if len(digests) > 1 and name not in chosen:
                plan.warnings.append(
                    f"'{name}' has {len(digests)} different {kind.label}s and none was "
                    f"chosen — left alone")
                continue
            want = chosen.get(name) or next(iter(digests))
            group = [c for c in copies if c.digest == want]
            if not group:
                plan.warnings.append(
                    f"the {kind.label} chosen for '{name}' is not there any more — skipped")
                continue
            keeper = _preferred(group, merc)
            dest = kind.rel(kind.merc, name, Path(keeper.rel).suffix.lower())
            if keeper.rel != dest:
                plan.copies.append((mod.data / keeper.rel, dest))
            # everything that is not the file we are keeping AT its destination
            for c in copies:
                if c.rel == dest:
                    continue
                plan.exports.append((mod.data / c.rel, f"data/{c.rel}"))
                plan.deletes.append(c.rel)
                if c.rel != keeper.rel:
                    plan.freed += c.size
            plan.consolidated += 1

    if plan.removed:
        plan.changes.append(f"{plan.removed} dictionary/ies worth of card art removed — "
                            f"no unit in the mod claims them")
    if plan.consolidated:
        plan.changes.append(f"{plan.consolidated} card(s) folded into the merc folder")
    if plan.copies:
        plan.changes.append(f"{len(plan.copies)} card(s) written into the merc folder "
                            f"(the rest were already there)")
    if plan.deletes:
        plan.changes.append(f"{len(plan.deletes)} file(s) moved out, freeing "
                            f"{plan.freed / 1048576:.1f} MB")
    if not plan.changes and not plan.errors:
        plan.warnings.append("nothing is ticked")
    return plan


_README = """{mod} — unit and info cards taken out
Moved out by the Medieval 2 GUI Toolkit on {when}.

data\\ui\\...
    Copies of a card that were folded into the merc folder. The mod keeps ONE
    of each, in data/ui/units/mercs or data/ui/unit_info/merc, which is where
    the game looks when a faction's own folder has nothing.

{unused}\\data\\ui\\...
    Cards for dictionaries no unit in the mod claims any more. Nothing in the
    game could reach these.

Copy either `data` folder back over the mod's `data` to restore what is in it.
Nothing here was removed from the mod without a backup: the toolkit's
Log → Undo restores the mod exactly, and does not need this folder.
"""


def apply_cleanup(plan: CleanupPlan, progress: Progress = None) -> Dict:
    """Write the cleanup: export first, then the merc copies, then the removals."""
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
    log.info("CARDS  cleanup id=%s  %s -> %s", tid, mod.name, target)
    log.info("  backups -> %s", backup_root)
    _log_cleanup_plan(plan)

    # 1) copy everything out BEFORE touching the mod, so a failure half-way
    #    leaves the mod intact rather than the art gone and nowhere to be.
    target.mkdir(parents=True, exist_ok=True)
    n_exports = len(plan.exports) or 1
    for i, (src, rel) in enumerate(plan.exports):
        if i % 25 == 0:
            say(2 + 58 * i / n_exports, f"copying cards out — {i}/{len(plan.exports)}")
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dest)
        except OSError as exc:
            plan.warnings.append(f"could not copy {rel} out: {exc}")
            continue
        file_op("EXPORT", dest, f"copied out of the mod from {src}")
    (target / README_NAME).write_text(
        _README.format(mod=mod.name, when=time.strftime("%Y-%m-%d %H:%M:%S"),
                       unused=UNUSED_SUBDIR),
        encoding="utf-8")

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

    # 2) the surviving copy goes into the merc folder FIRST. Written before a
    #    single faction copy is removed, so a run that dies in the middle leaves
    #    a mod with too many cards rather than one with none.
    say(62, "writing the merc folder's copies")
    for i, (src, rel) in enumerate(plan.copies):
        t = backup_and(rel)
        t.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, t)
            file_op("WRITE", t, f"the copy that stays, from {src}")
        except OSError as exc:
            plan.warnings.append(f"could not write data/{rel}: {exc}")
            log.warning("  could not write %s: %s", t, exc)

    n_deletes = len(plan.deletes) or 1
    for i, rel in enumerate(plan.deletes):
        if i % 25 == 0:
            say(70 + 28 * i / n_deletes, f"taking cards out of the mod — {i}/{len(plan.deletes)}")
        t = mod.data / rel
        if t.exists():
            backup_and(rel)                # backed up, then removed: Undo puts it back
            try:
                t.unlink()
                manifest.setdefault("deleted", []).append(rel)
                file_op("DELETE", t, "taken out of the mod (Undo puts it back)")
            except OSError as exc:
                plan.warnings.append(f"could not remove data/{rel}: {exc}")
                log.warning("  could not remove %s: %s", t, exc)
    say(99, "writing the log entry")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "cards",
        "action": "consolidate" if plan.consolidated else "cleanup",
        "source": mod.name,
        "source_root": str(mod.root),
        "dest": mod.name,
        "dest_root": str(mod.root),
        "unit_type": "",
        "resolved_type": ", ".join(
            [f"{n} {word}" for n, word in
             ((plan.consolidated, "card(s) folded into the merc folder"),
              (plan.removed, "card(s) for units that are gone"))
             if n]) or "nothing",
        "options": {"target": str(target), "freed": plan.freed},
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
    counted(manifest, [f"{len(plan.exports)} file(s) copied out to {target}",
                       f"{plan.freed / 1048576:.1f} MB no longer shipped"])
    log.info("CARDS  cleanup done id=%s", tid)
    edit._invalidate(mod)
    return rec


def _log_cleanup_plan(plan: CleanupPlan) -> None:
    log.info("  removing the art of %d dictionary/ies nothing claims", plan.removed)
    log.info("  folding %d card(s) into the merc folder", plan.consolidated)
    for _src, rel in plan.copies[:200]:
        log.info("    + %s", rel)
    log.info("  taking %d file(s) out, freeing %.1f MB",
             len(plan.deletes), plan.freed / 1048576)
    for rel in plan.deletes[:200]:
        log.info("    - %s", rel)
    for w in plan.warnings:
        log.warning("  ! %s", w)
