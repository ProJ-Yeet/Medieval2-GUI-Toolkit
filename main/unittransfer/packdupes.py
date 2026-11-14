r"""Duplicate animations in a mod's packs: compared, chosen, merged (101h).

Phase 85 (:mod:`packhouse`) drops what nothing plays. This is the other half
of a cleanup: the animations a pack holds more than once.

Two kinds
---------
**One path, several different animations.** A pack can list a path twice at
the same scale, each copy with bytes of its own. The game plays the first
(:func:`animpack.resolve_slot`) and never reaches the others, so a later copy
that was meant to replace the first does nothing. Here the copies are laid
side by side, and whichever is chosen becomes the one played: it takes the
first copy's place in the pack and the other copies at that scale go.

**One animation, several paths.** The same motion stored under two or more
paths, each named by its own skeleton slots. Paths are interchangeable only
when every copy of each, scale by scale, is the same bytes, so that is the
test. A merge keeps one path: every skeleton slot naming another is pointed
at it, the other paths' entries leave ``pack.dat``, and the anim lines of
``descr_skeleton.txt`` follow when the mod ships one.

The job
-------
Every choice and merge is written as one job through
:func:`animpack.write_compacted`: the new packs beside the old, read back,
swapped in, the old kept whole in ``.ut_compacted`` and logged like a
transfer, so the Log's Undo puts back the packs (and the text, from the job's
backup). Copies of a path the job leaves alone are written exactly as they
were, in their order.
"""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import animpack
from . import i18n as _i18n

#: rows a report sends at most, per kind
ROWS = 300


def _sha(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _copy_facts(e: animpack.PackEntry, plays: bool) -> dict:
    return {"offset": e.offset, "size": e.size, "scale": e.scale, "frames": e.frames,
            "rot_bones": e.rot_bones, "pos_bones": e.pos_bones, "plays": plays}


def _played_skeletons(packs) -> List[Tuple[animpack.PackEntry, animpack.PackedSkeleton]]:
    """The skeletons the game keeps (the first of each name), parsed."""
    firsts: Dict[str, animpack.PackEntry] = {}
    for e in packs.skels.entries:
        firsts.setdefault(animpack._key(e.name), e)
    out = []
    with open(packs.skels.dat_path, "rb") as f:
        for e in firsts.values():
            out.append((e, animpack.PackedSkeleton(packs.skels.read_entry(e, f), e.name)))
    return out


def _slot_users(skels) -> Dict[str, List[str]]:
    """``path key -> [skeleton names]`` whose slots name the path."""
    users: Dict[str, List[str]] = {}
    for e, sk in skels:
        for k in {animpack._key(s.path) for _i, s in sk.filled()}:
            users.setdefault(k, []).append(e.name)
    return users


def find(data_dir) -> dict:
    """Both kinds of duplicate in ``data_dir``'s own packs.

    ``conflicts``: ``[{path, scale, copies: [facts + sha]}]``, a path and scale
    with copies whose bytes differ (the first plays). ``identical``: ``[{paths:
    [{path, users}], scales, size}]``, paths whose every copy matches another
    path's, scale by scale. ``same_bytes``: how many same-path copies are byte
    for byte the first (Phase 85's compaction drops those)."""
    packs = animpack.for_data(data_dir)
    if packs is None or packs.anims is None or packs.skels is None:
        return {"error": _i18n.msg("eng.packdupes.no_packs",
                                   "This mod has no animation packs of its own; it plays vanilla's"),
                "conflicts": [], "identical": [], "same_bytes": 0}
    skels = _played_skeletons(packs)
    users = _slot_users(skels)
    by_path: Dict[str, List[animpack.PackEntry]] = {}
    for e in packs.anims.entries:
        by_path.setdefault(animpack._key(e.name), []).append(e)
    conflicts, same_bytes = [], 0
    # per path: the copy played at each scale, for the "one animation, several
    # paths" test - later copies at a scale are never reached, so not compared
    signature: Dict[str, Tuple] = {}
    shas: Dict[int, str] = {}
    with open(packs.anims.dat_path, "rb") as f:
        for k, copies in by_path.items():
            per_scale: Dict[float, List[animpack.PackEntry]] = {}
            for c in copies:
                per_scale.setdefault(c.scale, []).append(c)
            sig = []
            for scale, cs in sorted(per_scale.items()):
                for c in cs:
                    shas[id(c)] = _sha(packs.anims.read_entry(c, f))
                sig.append((scale, shas[id(cs[0])]))
                if len(cs) < 2:
                    continue
                if len({shas[id(c)] for c in cs}) == 1:
                    same_bytes += len(cs) - 1
                    continue
                conflicts.append({"path": cs[0].name, "scale": scale, "users": sorted(users.get(k, [])),
                                  "copies": [dict(_copy_facts(c, i == 0), sha=shas[id(c)],
                                                  same_as_first=(i > 0 and shas[id(c)] == shas[id(cs[0])]))
                                             for i, c in enumerate(cs)]})
            signature[k] = tuple(sig)
    groups: Dict[Tuple, List[str]] = {}
    for k, sig in signature.items():
        groups.setdefault(sig, []).append(k)
    identical = []
    for sig, keys in groups.items():
        if len(keys) < 2:
            continue
        first = {k: by_path[k][0] for k in keys}
        rows = sorted(({"path": first[k].name, "users": sorted(users.get(k, []))} for k in keys),
                      key=lambda r: (-len(r["users"]), r["path"].lower()))
        # one path's played copies; a merge takes every other path's out
        one = sum(c.size for c in {sc: next(e for e in by_path[keys[0]] if e.scale == sc)
                                   for sc, _h in sig}.values())
        identical.append({"paths": rows, "scales": [s for s, _h in sig],
                          "size": one, "freed": one * (len(keys) - 1)})
    conflicts.sort(key=lambda c: c["path"].lower())
    identical.sort(key=lambda g: -g["freed"])
    return {"error": "", "packs": str(packs.dir), "conflicts": conflicts[:ROWS],
            "conflicts_total": len(conflicts), "identical": identical[:ROWS],
            "identical_total": len(identical), "same_bytes": same_bytes,
            "identical_freed": sum(g["freed"] for g in identical)}


# ---------------------------------------------------------------------------
# side by side

def _angle(q1, q2) -> float:
    """Degrees between two unit quaternions."""
    d = abs(sum(a * b for a, b in zip(q1, q2)))
    n = math.sqrt(sum(a * a for a in q1) * sum(b * b for b in q2)) or 1.0
    return math.degrees(2 * math.acos(min(1.0, d / n)))


def motion_difference(a: animpack.PackedAnimation, b: animpack.PackedAnimation) -> Optional[dict]:
    """How far apart two copies move: the bones' rotations compared frame by
    frame (``b``'s frames stretched to ``a``'s length when they differ), as
    the mean and the largest angle in degrees. None when the bone counts
    differ, since then no bone can be matched to another."""
    if a.rot_bones != b.rot_bones or not a.frames or not b.frames:
        return None
    nq = a.rot_bones
    worst = total = 0.0
    n = 0
    for f in range(a.frames):
        g = min(b.frames - 1, round(f * (b.frames - 1) / max(1, a.frames - 1)))
        for bone in range(nq):
            i, j = (f * nq + bone) * 4, (g * nq + bone) * 4
            ang = _angle(a.rotations[i:i + 4], b.rotations[j:j + 4])
            worst = max(worst, ang)
            total += ang
            n += 1
    return {"mean": round(total / n, 2) if n else 0.0, "max": round(worst, 2)}


def compare(data_dir, path: str, scale: float) -> dict:
    """Every copy of ``path`` at ``scale``, with what each holds and how far
    each one's motion is from the copy that plays."""
    packs = animpack.for_data(data_dir)
    if packs is None or packs.anims is None:
        return {"error": _i18n.msg("eng.packdupes.no_packs",
                                   "This mod has no animation packs of its own; it plays vanilla's")}
    copies = [c for c in packs.anims.find(path) if c.scale == scale]
    if not copies:
        return {"error": _i18n.msg("eng.packdupes.no_such_path", "pack.idx has no {path} at scale {scale}",
                                   path=path, scale=scale)}
    rows = []
    with open(packs.anims.dat_path, "rb") as f:
        first = None
        for i, c in enumerate(copies):
            raw = packs.anims.read_entry(c, f)
            row = dict(_copy_facts(c, i == 0), sha=_sha(raw))
            try:
                anim = animpack.PackedAnimation(raw, c.name)
            except animpack.PackError as exc:
                row["error"] = str(exc)
                rows.append(row)
                continue
            # 20 frames a second, the rate the game plays a battle animation at
            row["seconds"] = round(anim.frames / 20.0, 2)
            if first is None:
                first = anim
                row["difference"] = {"mean": 0.0, "max": 0.0}
            else:
                row["difference"] = motion_difference(first, anim)
            rows.append(row)
    return {"error": "", "path": copies[0].name, "scale": scale, "copies": rows}


# ---------------------------------------------------------------------------
# the job

_ANIM_LINE = re.compile(r"^(\s*anim\s+\S+\s+)(\S+)(.*)$", re.I)


def _plan(packs, choices: List[dict], merges: List[dict]):
    """What the job writes: the pack's entries in order, the skeletons with
    their new bytes, and the path renames for the text. Raises PackError on a
    request that does not match the packs as they are now."""
    entries = list(packs.anims.entries)
    by_offset = {e.offset: e for e in entries}
    drop: set = set()
    place: Dict[int, animpack.PackEntry] = {}      # id(first copy) -> chosen copy
    for ch in choices:
        path, scale, want = ch.get("path", ""), ch.get("scale"), ch.get("offset")
        copies = [c for c in packs.anims.find(path) if c.scale == scale]
        chosen = by_offset.get(want)
        if len(copies) < 2 or chosen is None or not any(c is chosen for c in copies):
            raise animpack.PackError(_i18n.msg(
                "eng.packdupes.choice_stale", "{path} has changed since it was read; read the duplicates again",
                path=path))
        place[id(copies[0])] = chosen
        drop.update(id(c) for c in copies if c is not copies[0])
    renames: Dict[str, str] = {}
    for mg in merges:
        keep = mg.get("keep", "")
        others = [p for p in mg.get("paths", []) if animpack._key(p) != animpack._key(keep)]
        if not keep or not others or not packs.anims.find(keep):
            raise animpack.PackError(_i18n.msg(
                "eng.packdupes.merge_stale", "{path} has changed since it was read; read the duplicates again",
                path=keep or "?"))
        for p in others:
            hits = packs.anims.find(p)
            if not hits:
                raise animpack.PackError(_i18n.msg(
                    "eng.packdupes.merge_stale", "{path} has changed since it was read; read the duplicates again",
                    path=p))
            drop.update(id(e) for e in hits)
            renames[animpack._key(p)] = keep
    kept = [place.get(id(e), e) for e in entries if id(e) not in drop]
    # skeletons whose slots name a merged-away path, rewritten to the kept one
    swaps: Dict[int, bytes] = {}
    moved_slots = 0
    if renames:
        for e, sk in _played_skeletons(packs):
            hit = False
            for _i, s in sk.filled():
                to = renames.get(animpack._key(s.path))
                if to is not None:
                    s.path = to
                    hit = True
                    moved_slots += 1
            if hit:
                swaps[id(e)] = sk.to_bytes()
    return kept, swaps, renames, moved_slots


def _rename_text(text: str, renames: Dict[str, str]) -> Tuple[str, int]:
    """``descr_skeleton.txt`` with its anim lines following ``renames``."""
    out, n = [], 0
    for line in text.splitlines(keepends=True):
        m = _ANIM_LINE.match(line.rstrip("\r\n"))
        if m:
            to = renames.get(animpack._key(m.group(2)))
            if to is not None:
                end = line[len(line.rstrip("\r\n")):]
                line = m.group(1) + to + m.group(3) + end
                n += 1
        out.append(line)
    return "".join(out), n


def apply(mod, choices: List[dict], merges: List[dict], reason: str = "") -> dict:
    """Write ``choices`` (``[{path, scale, offset}]``: the copy to play) and
    ``merges`` (``[{paths, keep}]``) as one logged job. Returns the log record."""
    from . import config
    from .logutil import file_op, log

    if not choices and not merges:
        raise animpack.PackError(_i18n.msg("eng.packdupes.nothing_chosen", "Nothing is chosen or merged"))
    packs = animpack.for_data(mod.data)
    if packs is None or packs.anims is None or packs.skels is None:
        raise animpack.PackError(_i18n.msg("eng.packdupes.no_packs",
                                           "This mod has no animation packs of its own; it plays vanilla's"))
    kept_entries, swaps, renames, moved_slots = _plan(packs, choices, merges)
    keep = {"pack": kept_entries}
    if swaps:
        keep["skeletons"] = list(packs.skels.entries)
    tid = config.new_transfer_id()
    root = Path(mod.root)
    kept_dir = root / animpack.COMPACT_DIR / tid
    manifest = {"backed_up": [], "created": []}
    # the text first, backed up where Undo looks: a pack that fails to write
    # then leaves nothing half done, since the text goes back too
    text_path = Path(mod.data) / "descr_skeleton.txt"
    text_lines = 0
    backup_root = config.backup_root_for(tid)
    if renames and text_path.is_file():
        # bytes, not read_text: its newline translation would turn every \r\n
        # into \n, and the write below would then change every line of the file
        old = text_path.read_bytes().decode("latin-1")
        new, text_lines = _rename_text(old, renames)
        if text_lines:
            dst = backup_root / "data" / "descr_skeleton.txt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(text_path, dst)
            manifest["backed_up"].append("descr_skeleton.txt")
    rows = animpack.write_compacted(packs.dir, keep, kept_dir, swaps=swaps)
    if text_lines:
        text_path.write_text(new, encoding="latin-1", newline="")
        file_op("WRITE", text_path, f"{text_lines} anim line(s) point at the kept paths")
    for r in rows:
        file_op("REWRITE", packs.dir / f"{r['stem']}.dat", f"{r['dat_size']:,} bytes now")
    summary = (f"duplicate animations in {mod.name}: {len(choices)} chosen, "
               f"{len(renames)} path(s) merged into another, {moved_slots} skeleton slot(s) moved")
    manifest["compacted"] = {"anim_dir": packs.dir.relative_to(root).as_posix(),
                             "kept": kept_dir.relative_to(root).as_posix(), "rows": rows}
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "pack duplicates",
        "source": mod.name, "source_root": str(root), "dest": mod.name, "dest_root": str(root),
        "unit_type": "", "resolved_type": "", "options": {},
        "applied": True, "undone": False, "note": reason, "summary": summary, "warnings": [],
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("DUPES  %s, id=%s", summary, tid)
    return rec
