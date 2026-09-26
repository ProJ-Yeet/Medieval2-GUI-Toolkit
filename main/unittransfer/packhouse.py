r"""Pack housekeeping: what a mod's animation packs hold that nothing plays, and a compacted pack (Phase 85).

The "cleanup" asked about on Discord. Mods append to their packs, and over the
years a pack gathers copies nobody reads. This module says what is there, and,
as a job of its own with its own Undo, writes the packs again holding only
what is played.

What is played
--------------
A skeleton is known by its name, and the first of two skeletons with one name
is the one the game keeps (Phase 82's question 5). An animation is known by
its path **and** its scale (:func:`animpack.resolve_slot`): each kept
skeleton's slots play the first copy of a path at the skeleton's own scale, or
failing that the first copy at the smallest scale, rescaled. Everything else
in ``pack.dat`` is one of:

* **a dead copy** - the same path at the same scale as an earlier entry, which
  the game never reaches (Reforged has 102 paths twice, DaC 916);
* **a copy at a scale nothing plays** - the path at a scale no skeleton has,
  while another copy is the one played;
* **unused** - a path no slot of any skeleton names.

And in ``skeletons.dat``, **a skeleton listed twice**: the later copy is dead.
Skeletons **no battle model or strat model names** are reported and never
removed, since other files and the engine itself may ask for one by name.

A compaction
------------
Writes ``pack.dat`` (and ``skeletons.dat``, when it has a dead copy) holding
the played entries only, in their order, so every slot plays exactly what it
played before. The new files are written beside the old, read back, and
swapped in; the old ones are kept, whole, in the mod's ``.ut_compacted``
folder until the job is undone or its backup forgotten, so it needs the free
space of the new pack. It is logged like a transfer, and ``transfer.undo``
puts the old files back, refusing when the packs have been written since.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import animpack


@dataclass
class Copy:
    entry: animpack.PackEntry
    #: "played", "dead copy", "scale nothing plays" or "unused"
    state: str
    same_as_first: Optional[bool] = None

    def payload(self) -> dict:
        return {"offset": self.entry.offset, "size": self.entry.size, "scale": self.entry.scale,
                "state": self.state, "same_as_first": self.same_as_first}


@dataclass
class Report:
    anim_dir: Optional[Path]
    error: str = ""
    anims: int = 0
    skels: int = 0
    anim_bytes: int = 0
    skel_bytes: int = 0
    #: every entry of pack.dat not played, by its state
    dead: List[animpack.PackEntry] = field(default_factory=list)
    other_scale: List[animpack.PackEntry] = field(default_factory=list)
    unused: List[animpack.PackEntry] = field(default_factory=list)
    #: the paths listed more than once, each copy with its state
    duplicates: Dict[str, List[Copy]] = field(default_factory=dict)
    #: skeleton names listed more than once: the later copies, dead
    skel_twice: Dict[str, List[animpack.PackEntry]] = field(default_factory=dict)
    #: skeletons no battle model or strat model names (reported only)
    unnamed: List[str] = field(default_factory=list)
    keep_anims: List[animpack.PackEntry] = field(default_factory=list)
    keep_skels: List[animpack.PackEntry] = field(default_factory=list)
    #: slots whose path pack.idx has not got at all (the viewer's red rows)
    missing_slots: int = 0

    @property
    def anim_freed(self) -> int:
        return sum(e.size for e in self.dead + self.other_scale + self.unused)

    @property
    def skel_freed(self) -> int:
        return sum(e.size for copies in self.skel_twice.values() for e in copies[1:])

    @property
    def worth_compacting(self) -> bool:
        return bool(self.anim_freed or self.skel_freed)

    def payload(self, rows: int = 200) -> dict:
        dup_same = sum(1 for cs in self.duplicates.values()
                       if len({c.entry.scale for c in cs}) < len(cs))
        return {
            "packs": str(self.anim_dir) if self.anim_dir else None, "error": self.error,
            "anims": self.anims, "skeletons": self.skels,
            "anim_bytes": self.anim_bytes, "skel_bytes": self.skel_bytes,
            "dead": len(self.dead), "dead_bytes": sum(e.size for e in self.dead),
            "other_scale": len(self.other_scale),
            "other_scale_bytes": sum(e.size for e in self.other_scale),
            "unused": len(self.unused), "unused_bytes": sum(e.size for e in self.unused),
            "duplicate_paths": len(self.duplicates), "duplicate_paths_same_scale": dup_same,
            "skel_twice": sorted(self.skel_twice), "unnamed": self.unnamed,
            "missing_slots": self.missing_slots,
            "anim_freed": self.anim_freed, "skel_freed": self.skel_freed,
            "keep_anims": len(self.keep_anims), "keep_skels": len(self.keep_skels),
            "worth_compacting": self.worth_compacting,
            "duplicates": [{"path": cs[0].entry.name, "copies": [c.payload() for c in cs]}
                           for cs in list(self.duplicates.values())[:rows]],
            "unused_paths": [e.name for e in self.unused[:rows]],
        }


def _named_skeletons(mod) -> set:
    """Every skeleton a battle model (body or weapon) or a strat model names."""
    out = set()
    if mod is None:
        return out
    try:
        for e in mod.modeldb.entries:
            out.update(animpack._key(s) for s in e.skeletons() + e.weapon_skeletons())
    except (OSError, ValueError):
        pass
    strat = Path(mod.data) / "descr_model_strat.txt"
    if strat.is_file():
        for line in strat.read_text(encoding="latin-1", errors="replace").splitlines():
            w = line.split(";", 1)[0].split()
            if len(w) > 1 and w[0].lower() == "skeleton":
                out.add(animpack._key(w[1]))
    return out


def report(data_dir, mod=None) -> Report:
    """What ``data_dir``'s own packs hold that nothing plays. ``mod`` (a
    :class:`unittransfer.mod.Mod`) adds the skeletons no model names."""
    packs = animpack.for_data(data_dir)
    if packs is None or packs.anims is None or packs.skels is None:
        return Report(None, error="This mod has no animation packs of its own; it plays vanilla's")
    out = Report(packs.dir, anims=len(packs.anims), skels=len(packs.skels))
    out.anim_bytes = sum(e.size for e in packs.anims.entries)
    out.skel_bytes = sum(e.size for e in packs.skels.entries)
    # skeletons: the first of each name is the one played
    firsts: Dict[str, animpack.PackEntry] = {}
    for e in packs.skels.entries:
        k = animpack._key(e.name)
        if k in firsts:
            out.skel_twice.setdefault(firsts[k].name, [firsts[k]]).append(e)
        else:
            firsts[k] = e
    out.keep_skels = list(firsts.values())
    # animations: what each kept skeleton's slots resolve to
    played = set()
    named = set()
    with open(packs.skels.dat_path, "rb") as f:
        for e in out.keep_skels:
            sk = animpack.PackedSkeleton(packs.skels.read_entry(e, f), e.name)
            for _i, s in sk.filled():
                named.add(animpack._key(s.path))
                hit = animpack.resolve_slot(packs.anims, s.path, sk.scale)
                if hit is None:
                    out.missing_slots += 1
                else:
                    played.add(hit.offset)
    seen_key = set()
    for e in packs.anims.entries:
        if e.offset in played:
            out.keep_anims.append(e)
            seen_key.add((animpack._key(e.name), e.scale))
            continue
        k = animpack._key(e.name)
        if (k, e.scale) in seen_key:
            out.dead.append(e)
        elif k in named:
            out.other_scale.append(e)
        else:
            out.unused.append(e)
        seen_key.add((k, e.scale))
    state = {id(e): s for s, rows in (("dead copy", out.dead), ("scale nothing plays", out.other_scale),
                                      ("unused", out.unused)) for e in rows}
    with open(packs.anims.dat_path, "rb") as f:
        for k, copies in packs.anims.duplicates().items():
            first = packs.anims.read_entry(copies[0], f)
            out.duplicates[k] = [Copy(c, state.get(id(c), "played"),
                                      None if i == 0 else (c.size == copies[0].size
                                                           and packs.anims.read_entry(c, f) == first))
                                 for i, c in enumerate(copies)]
    if mod is not None:
        names = _named_skeletons(mod)
        out.unnamed = sorted((e.name for e in out.keep_skels if animpack._key(e.name) not in names),
                             key=str.lower)
    return out


def compact(mod, reason: str = "") -> dict:
    """Compact ``mod``'s packs as one logged job, undoable like a transfer.
    Returns the log record. Raises :class:`animpack.PackError` when there is
    nothing to do, or it cannot be done now."""
    from . import config
    from .logutil import file_op, log

    rep = report(mod.data, mod)
    if rep.error:
        raise animpack.PackError(rep.error)
    if not rep.worth_compacting:
        raise animpack.PackError("The packs hold nothing that is not played; there is nothing to compact")
    keep: Dict[str, List[animpack.PackEntry]] = {}
    if rep.anim_freed:
        keep["pack"] = rep.keep_anims
    if rep.skel_freed:
        keep["skeletons"] = rep.keep_skels
    tid = config.new_transfer_id()
    root = Path(mod.root)
    kept = root / animpack.COMPACT_DIR / tid
    rows = animpack.write_compacted(rep.anim_dir, keep, kept)
    for r in rows:
        file_op("COMPACT", rep.anim_dir / f"{r['stem']}.dat", f"{r['dat_size']:,} bytes now")
    freed = rep.anim_freed + rep.skel_freed
    summary = (f"animation packs of {mod.name} compacted: {len(rep.dead) + len(rep.other_scale) + len(rep.unused)} "
               f"animation(s) and {sum(len(v) - 1 for v in rep.skel_twice.values())} skeleton(s) nothing plays "
               f"left out, {freed / 1e6:.1f} MB")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "pack compact",
        "source": mod.name, "source_root": str(root), "dest": mod.name, "dest_root": str(root),
        "unit_type": "", "resolved_type": "", "options": {},
        "applied": True, "undone": False, "note": reason, "summary": summary, "warnings": [],
        "manifest": {"backed_up": [], "created": [],
                     "compacted": {"anim_dir": rep.anim_dir.relative_to(root).as_posix(),
                                   "kept": kept.relative_to(root).as_posix(), "rows": rows}},
        "backup_root": str(config.backup_root_for(tid)),
    }
    config.append_log(rec)
    log.info("COMPACT %s, id=%s", summary, tid)
    return rec


def undo(root, block: dict) -> None:
    """``transfer.undo``'s part for a ``compacted`` manifest block."""
    root = Path(root)
    animpack.undo_compacted(root / block["anim_dir"], root / block["kept"], block["rows"])


def forget_backup(root, block: dict) -> int:
    """Delete the replaced packs a compaction kept, giving the space back and
    the Undo up. Returns the bytes freed."""
    import shutil
    kept = Path(root) / block["kept"]
    if not kept.is_dir():
        return 0
    size = sum(p.stat().st_size for p in kept.rglob("*") if p.is_file())
    shutil.rmtree(kept)
    try:
        kept.parent.rmdir()
    except OSError:
        pass
    return size
