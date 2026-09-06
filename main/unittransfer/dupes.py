"""Entries ``battle_models.modeldb`` lists more than once.

A modeldb is a flat stream of entry blocks, and nothing in the format stops the
same name appearing twice. Real mods are full of it: an entry gets pasted in
again during a merge, a submod ships its own copy of a model the base mod
already had, a name gets reused for a model that was meant to replace the first
one. Third Age Reforged has eight such names, Divide and Conquer five.

**The game reads the first block with a name and ignores every later one.** A
unit that names the model gets the first block's meshes, the first block's
skins and the first block's animations; the second block is bytes the engine
walks past. That is what makes this worth a screen of its own rather than a
line in the cleanup dialog: a modder who pasted a fixed model in at the bottom
of the file is looking at a mod that does not use it and no error anywhere
saying so.

So there are exactly two useful things to do with a block that is not the first
of its name, and this module plans and applies both:

``rename``
    Give it a name of its own. The block stops being dead and becomes a real
    entry that a unit can be pointed at. Nothing references the new name yet,
    which the plan says out loud so it does not read as a finished job.

``remove``
    Drop the block. When it is byte-identical to the first one this loses
    nothing at all; when it differs, it discards a model, so the plan spells
    out what was different before anything is written.

The first block of a name is never touched by either. It is the one the game
actually reads, and every reference in the mod resolves to it, so removing or
renaming it would change what units draw with. Everything here is keyed by the
block's index in :attr:`ModelDb.entries` rather than by name, because a name is
exactly the thing these blocks do not have to themselves.

This is deliberately not part of :mod:`unittransfer.bmdb`'s cleanup. That one
answers "is anything still using this?" and moves assets out of the mod; this
one never touches a file on disk other than the modeldb itself, and its
question is the opposite - the entries here are ones the mod may well want, it
just cannot reach them.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence

from . import bmdb, config, modeldb
from .logutil import file_op, log
from .mod import Mod

#: Where the file sits under a mod's ``data``. Same constant the edit path uses;
#: it is spelled out here so this module can back up and write without going
#: through a plan that knows about units.
REL = "unit_models/battle_models.modeldb"

#: What ``suggest_name`` appends, then counts up from, when it is asked for a
#: free name for a second block. ``_2`` reads as "the second one" to anybody
#: opening the file afterwards, which ``_dup`` or a hash would not.
SUFFIX = "_"


# ---------------------------------------------------------------------------
# finding them


def _differences(first: "modeldb.ModelEntry",
                 later: "modeldb.ModelEntry") -> List[str]:
    """Which parts of ``later`` are not what ``first`` says, in plain words.

    Only reached for blocks that are not identical, and only to be shown: the
    decision this informs is whether the later block is worth keeping under its
    own name, and "different meshes" is the answer to that. Comparing the parsed
    entry rather than the raw text is deliberate - two blocks written with
    different whitespace are the same model, and saying they differ would send
    somebody looking for a difference that is not there.
    """
    out: List[str] = []
    if round(first.scale, 4) != round(later.scale, 4):
        out.append(f"scale {first.scale:g} vs {later.scale:g}")
    if first.lods != later.lods:
        fm, lm = first.mesh_files(), later.mesh_files()
        if fm != lm:
            gained = [m for m in lm if m not in fm]
            out.append(f"{len(lm)} mesh file(s) vs {len(fm)}" if len(fm) != len(lm)
                       else f"different mesh file(s): {', '.join(gained[:2]) or 'same names, other LOD distances'}")
        else:
            out.append("same meshes at different LOD distances")
    ftex = {(t.faction, t.texture, t.normal, t.sprite) for t in first.main_textures}
    ltex = {(t.faction, t.texture, t.normal, t.sprite) for t in later.main_textures}
    if ftex != ltex:
        ff = {t.faction for t in first.main_textures}
        lf = {t.faction for t in later.main_textures}
        if ff != lf:
            extra = sorted(lf - ff)
            out.append(f"skins for {len(lf)} faction(s) vs {len(ff)}"
                       + (f" (adds {', '.join(extra[:3])})" if extra else ""))
        else:
            out.append("the same factions painted with different files")
    fatt = {(t.faction, t.texture, t.normal, t.sprite) for t in first.attach_textures}
    latt = {(t.faction, t.texture, t.normal, t.sprite) for t in later.attach_textures}
    if fatt != latt:
        out.append("different attachment skins")
    fa = [(a.mount_type, a.primary_skeleton, a.secondary_skeleton) for a in first.animations]
    la = [(a.mount_type, a.primary_skeleton, a.secondary_skeleton) for a in later.animations]
    if fa != la:
        out.append("different animation skeletons")
    if first.torch_index != later.torch_index or first.torch != later.torch:
        out.append("a different torch")
    return out


def _entry_files(e: "modeldb.ModelEntry") -> List[str]:
    return e.mesh_files() + e.texture_files()


def find(mod: Mod) -> List[dict]:
    """Every name with more than one block, first block first.

    The rows carry the block's ``index`` in the parsed entry list, and that
    index is what a request names. It is stable for as long as the file is not
    rewritten, which is exactly as long as a plan built from these rows is
    worth anything - :func:`plan` re-derives the duplicates from the mod rather
    than trusting the numbers, so a stale page cannot delete the wrong block.
    """
    entries = mod.modeldb.entries
    order: List[str] = []
    where: Dict[str, List[int]] = {}
    for i, e in enumerate(entries):
        if e.name not in where:
            where[e.name] = []
            order.append(e.name)
        where[e.name].append(i)

    users = bmdb.entry_users(mod)
    lines = _line_index(mod)
    taken = set(where)
    rows: List[dict] = []
    for name in order:
        idx = where[name]
        if len(idx) < 2:
            continue
        first = entries[idx[0]]
        blocks = []
        for n, i in enumerate(idx):
            e = entries[i]
            same = n == 0 or first.content_equals(e)
            files = _entry_files(e)
            blocks.append({
                "index": i,
                "ordinal": n + 1,
                "first": n == 0,
                "line": lines[i],
                "identical": same,
                "differs": [] if same else _differences(first, e),
                "lods": len(e.lods),
                "skins": len(e.main_textures),
                "factions": e.factions(),
                "files": files,
                "on_disk": sum(1 for f in files if (mod.data / f).is_file()),
                "bytes": len(e.raw),
                "suggested": "" if n == 0 else suggest_name(name, n, taken),
            })
        rows.append({
            "name": name,
            "copies": len(idx),
            "identical": all(b["identical"] for b in blocks),
            "used_by": bmdb.describe_users(users, name),
            "blocks": blocks,
        })
    return rows


def _line_index(mod: Mod) -> List[int]:
    """The 1-based line every block starts on, in one walk of the file.

    Worked out by adding up the raw spans rather than searching the file for
    each name, because a duplicated name is in the file more than once by
    definition and a search would find the wrong one. One walk rather than one
    per block: a mod with a dozen duplicated names would otherwise re-count the
    newlines in a multi-megabyte file a dozen times over. Only for showing - a
    person checking this against the file wants somewhere to jump to.
    """
    db = mod.modeldb
    line = 1 + (db.header_raw or "").count("\n") + db.blank_raw.count("\n")
    out: List[int] = []
    for e in db.entries:
        out.append(line)
        line += e.raw.count("\n")
    return out


def suggest_name(name: str, n: int, taken: set) -> str:
    """A free name for the ``n``-th copy: ``name_2``, then ``_3``, and so on."""
    i = n + 1
    while f"{name}{SUFFIX}{i}" in taken:
        i += 1
    return f"{name}{SUFFIX}{i}"


def audit(mod: Mod) -> dict:
    """:func:`find` plus the counts the dialog opens on."""
    rows = find(mod)
    extra = sum(r["copies"] - 1 for r in rows)
    return {
        "mod": mod.name,
        "root": str(mod.root),
        "entry_count": len(mod.modeldb.entries),
        "names": len({e.name for e in mod.modeldb.entries}),
        "rows": rows,
        "duplicated": len(rows),
        "extra_blocks": extra,
        "extra_bytes": sum(b["bytes"] for r in rows for b in r["blocks"] if not b["first"]),
    }


# ---------------------------------------------------------------------------
# planning


@dataclass
class DupeAction:
    index: int
    action: str                 # "remove" | "rename"
    new_name: str = ""


@dataclass
class DupeRequest:
    actions: List[DupeAction] = field(default_factory=list)


def request_from_dict(d: dict) -> DupeRequest:
    out: List[DupeAction] = []
    for a in d.get("actions") or []:
        act = str(a.get("action") or "").strip().lower()
        if act not in ("remove", "rename"):
            continue                       # "leave alone" arrives as anything else
        out.append(DupeAction(index=int(a.get("index", -1)), action=act,
                              new_name=str(a.get("new_name") or "").strip().lower()))
    return DupeRequest(actions=out)


@dataclass
class DupePlan:
    mod: Mod
    request: DupeRequest
    text: str = ""                                   # "" = nothing is written
    removes: List[dict] = field(default_factory=list)
    renames: List[dict] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def touched(self) -> bool:
        return bool(self.removes or self.renames)

    def summary(self) -> str:
        lines = [f"tidy duplicate entries in {self.mod.name}'s battle_models.modeldb"]
        lines += ["  " + c for c in self.changes]
        lines += ["  ! " + w for w in self.warnings]
        return "\n".join(lines)


def plan(mod: Mod, req: DupeRequest) -> DupePlan:
    """Work out exactly what the file would lose and gain, and refuse the rest.

    Everything is re-derived from the mod here. A request arrives from a page
    built on an older read of the file, or from a saved selection, and an index
    that meant one block then can mean another now - so which blocks are
    duplicates, and which of them is the first, is decided again from the parse
    in hand rather than taken from the request.
    """
    p = DupePlan(mod=mod, request=req)
    entries = mod.modeldb.entries
    firsts: Dict[str, int] = {}
    for i, e in enumerate(entries):
        firsts.setdefault(e.name, i)
    counts: Dict[str, int] = {}
    for e in entries:
        counts[e.name] = counts.get(e.name, 0) + 1

    taken = set(counts)
    seen: set = set()
    acts: Dict[int, DupeAction] = {}
    for a in req.actions:
        if not 0 <= a.index < len(entries):
            p.errors.append(f"there is no entry block {a.index} in this modeldb")
            continue
        e = entries[a.index]
        if a.index in seen:
            p.errors.append(f"'{e.name}' block {a.index} is in the request twice")
            continue
        seen.add(a.index)
        if counts[e.name] < 2:
            # the file changed under the page, or the request was hand-made
            p.errors.append(f"'{e.name}' is only in the file once - nothing to tidy")
            continue
        if firsts[e.name] == a.index:
            p.errors.append(
                f"'{e.name}': that is the FIRST block of the name, which is the one "
                "the game reads and everything in the mod resolves to. Only a later "
                "copy may be renamed or removed")
            continue
        if a.action == "rename":
            new = a.new_name
            if not new:
                p.errors.append(f"'{e.name}': a rename needs a new name")
                continue
            if " " in new:
                p.errors.append(f"'{new}': model entry names cannot contain spaces")
                continue
            if new in taken:
                p.errors.append(f"a model entry called '{new}' already exists")
                continue
            taken.add(new)
        acts[a.index] = a

    if p.errors:
        return p

    for i in sorted(acts):
        a, e = acts[i], entries[i]
        same = entries[firsts[e.name]].content_equals(e)
        row = {"index": i, "name": e.name, "ordinal": _ordinal(entries, i),
               "identical": same, "bytes": len(e.raw),
               "differs": [] if same else _differences(entries[firsts[e.name]], e)}
        if a.action == "remove":
            p.removes.append(row)
        else:
            row["new_name"] = a.new_name
            p.renames.append(row)

    if not p.touched():
        p.errors.append("nothing is ticked")
        return p

    if p.removes:
        lost = [r for r in p.removes if not r["identical"]]
        p.changes.append(
            f"{len(p.removes)} duplicate block(s) removed "
            f"({len(entries)} -> {len(entries) - len(p.removes)} entries)")
        if lost:
            # not a warning about the write, a warning about what it means: an
            # identical copy costs nothing to drop, a different one is a model
            p.warnings.append(
                f"{len(lost)} of the removed block(s) is not a copy of the entry the "
                "game reads, so a model goes with it: "
                + "; ".join(f"{r['name']} ({', '.join(r['differs'][:2]) or 'differs'})"
                            for r in lost[:4]))
    if p.renames:
        p.changes.append(
            f"{len(p.renames)} duplicate block(s) renamed: "
            + ", ".join(f"{r['name']} -> {r['new_name']}" for r in p.renames[:6]))
        p.warnings.append(
            "a renamed block is a real entry now, but nothing in the mod names it yet. "
            "Point a unit's `soldier` line at it, or the next cleanup will offer to "
            "remove it as unused")
        idle = [r for r in p.renames if r["identical"]]
        if idle:
            p.warnings.append(
                f"{len(idle)} of the renamed block(s) is byte-identical to the entry the "
                "game already reads, so this makes a second name for the same model: "
                + ", ".join(r["name"] for r in idle[:4]))

    p.text = _text(mod, acts)
    return p


def _ordinal(entries: Sequence["modeldb.ModelEntry"], index: int) -> int:
    """Which copy of its name the block at ``index`` is, counting from 1."""
    name = entries[index].name
    return sum(1 for e in entries[:index + 1] if e.name == name)


def _text(mod: Mod, acts: Dict[int, DupeAction]) -> str:
    """The modeldb with the removes dropped and the renames applied.

    Built by swapping the entry list under the cached parse and swapping it
    back, the way every other writer in this package does it, so the header's
    entry count follows the removes and an untouched entry is never
    re-serialised - its raw span goes out exactly as it came in.
    """
    db = mod.modeldb
    original = list(db.entries)
    rebuilt: List["modeldb.ModelEntry"] = []
    for i, e in enumerate(original):
        a = acts.get(i)
        if a is None:
            rebuilt.append(e)
            continue
        if a.action == "remove":
            continue
        rebuilt.append(modeldb.ModelEntry(
            name=a.new_name, scale=e.scale, lods=e.lods,
            main_textures=e.main_textures, attach_textures=e.attach_textures,
            animations=e.animations, torch_index=e.torch_index, torch=e.torch,
            raw=modeldb.rename_entry_raw(e.raw, a.new_name),
            first_entry_pad=e.first_entry_pad))
    try:
        db.entries = rebuilt
        return db.to_text()
    finally:
        db.entries = original              # keep the cached parse pristine


# ---------------------------------------------------------------------------
# applying


def path_for(mod: Mod) -> Path:
    return mod.data / REL


def apply(p: DupePlan) -> Dict:
    """Write the plan, with the same backup and undo record as any other job."""
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.touched():
        raise ValueError("nothing to change")

    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    target = path_for(mod)
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    manifest["backed_up"].append(REL)
    file_op("BACKUP", target, f"-> {bpath}")

    target.write_text(p.text, encoding=modeldb.ENCODING)
    file_op("WRITE", target, f"{modeldb.ENCODING}, {len(p.text)} chars")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "bmdb",
        "action": "tidy duplicate model entries",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": "", "resolved_type": "",
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("BMDB   duplicates in %s - %d removed, %d renamed, id=%s",
             mod.name, len(p.removes), len(p.renames), tid)
    mod.drop_caches()
    return {"id": tid, "removed": len(p.removes), "renamed": len(p.renames),
            "record": rec}
