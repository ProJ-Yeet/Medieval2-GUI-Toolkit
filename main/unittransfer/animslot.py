r"""Animations on their own: one slot of a mod's pack written, and a skeleton ported alone (Phase 86).

Phases 81 and 83 bring a unit's skeletons into another mod's packs because a
unit was transferred. This is the same engine without a unit:

* **An edit saved into the pack.** An action opened in the animation editor
  (57a), edited, is packed the way the engine packs a ``.cas`` and appended to
  ``pack.dat`` under a path of its own, and the skeleton's slot is pointed
  there. It cannot go under the old path: the game plays the first of two
  entries with one name (Phase 82's question 5), so a second copy would never
  play. Nor can the skeleton be appended again under its own name, for the
  same reason, so its entry in ``skeletons.dat`` is written again with the
  slot's path changed. ``skeletons.dat`` is small (Reforged's is 9 MB) and is
  backed up whole; ``pack.dat`` is only ever appended to.
* **One animation from another mod into a chosen slot.** The same write, the
  bytes out of the other mod's pack: as they are when the two skeletons share
  their bones (the same names, in the same order), else carried across bone
  by bone, by name, and packed again for this skeleton.
* **A skeleton ported alone**, with every animation its slots name, through
  :func:`unittransfer.animpack.plan_port`, and optionally a model entry
  pointed at it: a skeleton whose name the destination already has is added
  as ``<name>_<tag>``, and nothing plays it until an entry asks for it.

Each is one job in the transfer log and one Undo. And each keeps the mod
rebuildable where it can (Phase 84): the new animation written loose at the
path its slot names, and ``descr_skeleton.txt``'s line for the action pointed
there, so a modder who later deletes the packs to have the game rebuild them
does not lose the edit.

From a pack entry to an edit and back
-------------------------------------
:func:`unittransfer.animloose.to_cas` turns an entry into the loose animation
the engine would pack back into it; the editor's edits
(:func:`unittransfer.animedit.apply_edits`) are made to that; it is put back on
the engine's 20 frames a second (a speed change moves the keys off them); and
:func:`unittransfer.animloose.to_packed` packs it at the skeleton's scale, with
the root motion worked out as a rebuild would (none for ``default`` or a
``no_deltas`` type, the rise taken out of the two climbs). An unedited action
packs back to its own entry (``tests/test_animloose.py`` holds that on every
installed animation), so an edit changes what it says it changes. The
preview the editor plays is these same bytes read back.
"""
from __future__ import annotations

import math
import shutil
import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import animedit, animloose, animpack, casanim, modeldb, skelslots

DEFAULT_SLOT = animpack.SKELETON_SLOTS - 1
FRAME_TIME = animloose.FRAME_TIME


class SlotError(ValueError):
    pass


def _tag(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())[:16] or "ported"


def _own(data_dir) -> animpack.Packs:
    """The mod's own packs, or why there are none to write to."""
    packs = animpack.for_data(data_dir)
    if packs is None or packs.anims is None or packs.skels is None:
        raise SlotError("this mod ships no animation packs of its own (the game plays vanilla's), "
                        "so there is no pack of its own to save into")
    return packs


def _skeleton(packs: animpack.Packs, name: str) -> Tuple[animpack.PackEntry, animpack.PackedSkeleton]:
    e = packs.skels.first(name)
    if e is None:
        raise SlotError(f"the skeleton pack has no {name!r}")
    return e, animpack.PackedSkeleton(packs.skels.read_entry(e), e.name)


def _rot_bones(packs: animpack.Packs, sk: animpack.PackedSkeleton, slot: int) -> int:
    """How many bones this skeleton's animations turn: the count its slot's
    entry has, else its ``default``'s, else every bone."""
    for i in (slot, DEFAULT_SLOT):
        s = sk.slots[i] if 0 <= i < len(sk.slots) else None
        if s is not None:
            e = animpack.resolve_slot(packs.anims, s.path, sk.scale)
            if e is not None and e.rot_bones:
                return min(e.rot_bones, len(sk.bones))
    return len(sk.bones)


def _climbs(slot: int) -> bool:
    return any(n in animloose.Y_COMPENSATED for n in skelslots.names(slot))


# ---------------------------------------------------------------------------
# an animation put on a skeleton, packed

def on_frames(anim: casanim.Animation) -> casanim.Animation:
    """``anim`` keyed on the engine's frames, 0.05 s apart, an odd number of
    them (the engine drops the last of an even count). An animation already on
    them is returned as it is; one a speed change or a loose file's own rate
    moved off them is sampled onto them, holding its last pose."""
    times = list(anim.key_times)
    if not times:
        return anim
    on = all(abs(t - i * FRAME_TIME) < 1e-4 for i, t in enumerate(times))
    if on and len(times) % 2:
        return anim
    end = times[-1]
    nf = max(1, int(round(end / FRAME_TIME))) + 1
    if not nf % 2:
        nf += 1
    out = casanim.Animation(source=anim.source, version=anim.version, length=(nf - 1) * FRAME_TIME,
                            key_times=array("f", [i * FRAME_TIME for i in range(nf)]),
                            layout=anim.layout, head=anim.head, tail=None)
    out.notes = list(anim.notes)
    frames = [casanim.sample(anim, min(i * FRAME_TIME, max(end - 1e-6, 0.0))) for i in range(nf)]
    for x, tr in enumerate(anim.tracks):
        t = casanim.Track(tr.name, tr.parent, tr.pivot)
        if tr.rot_keys:
            for f in frames:
                t.rot.extend(f[x]["rot"])
        if tr.pos_keys:
            for f in frames:
                t.pos.extend(p - b for p, b in zip(f[x]["pos"], tr.pivot))
        out.tracks.append(t)
    return out


def onto(anim: casanim.Animation, sk: animpack.PackedSkeleton, nq: int) -> Tuple[casanim.Animation, List[str]]:
    """``anim`` on ``sk``'s first ``nq`` bones, each bone's keys taken from the
    track of the same name (any case), its pivot the skeleton's own (over its
    scale, as a loose file has it). Returns it and the bones no track moved,
    which hold their bind pose."""
    have = {t.name.lower(): t for t in anim.tracks[1:]}
    out = casanim.Animation(source=anim.source, version=anim.version, length=anim.length,
                            key_times=array("f", anim.key_times), layout=anim.layout,
                            head=anim.head, tail=None)
    out.tracks.append(casanim.Track("Scene Root", -1, (0.0, 0.0, 0.0)))
    s = sk.scale or 1.0
    missing: List[str] = []
    for b in range(nq):
        bone = sk.bones[b]
        par = bone.parent + 1 if 0 <= bone.parent < b else 0
        t = casanim.Track(bone.name, par, tuple(float(v) / s for v in bone.pos))
        src = have.get(bone.name.lower())
        if src is None:
            missing.append(bone.name)
        else:
            t.rot = array("f", src.rot)
            t.pos = array("f", src.pos)
        out.tracks.append(t)
    return out, missing


def pack_for(packs: animpack.Packs, sk: animpack.PackedSkeleton, slot: int,
             anim: casanim.Animation) -> bytes:
    """``anim`` (on ``sk``'s bones) packed as the engine packs a ``.cas`` for
    this skeleton's ``slot``."""
    deltas = slot != DEFAULT_SLOT and not animloose._no_deltas(packs, sk)
    return animloose.to_packed(on_frames(anim), sk.scale or 1.0, generate_deltas=deltas,
                               y_compensate=_climbs(slot))


def _same_bones(a: animpack.PackedSkeleton, b: animpack.PackedSkeleton, nq: int) -> bool:
    return len(a.bones) >= nq and len(b.bones) >= nq and all(
        x.name.lower() == y.name.lower() for x, y in zip(a.bones[:nq], b.bones[:nq]))


# ---------------------------------------------------------------------------
# a plan for one slot

@dataclass
class SlotPlan:
    kind: str = ""                       # "edit" or "bring"
    mod: object = None
    skeleton: str = ""
    slot: int = -1
    action: str = ""
    old_path: str = ""
    new_path: str = ""
    data: bytes = b""                    # the entry's bytes
    scale: float = 1.0                   # its index record's scale
    reuse: bool = False                  # the pack has these bytes at new_path already
    new_slot: Optional[animpack.Slot] = None
    skeleton_bytes: bytes = b""
    loose: Optional[Tuple[str, bytes]] = None          # (rel under data/, .cas bytes)
    text_edit: Optional[Tuple[str, str]] = None        # descr_skeleton.txt, rewritten
    source: str = ""
    stamp: tuple = ()
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.data)

    def payload(self) -> dict:
        return {"kind": self.kind, "skeleton": self.skeleton, "slot": self.slot,
                "action": self.action, "old_path": self.old_path, "new_path": self.new_path,
                "bytes": len(self.data), "reuse": self.reuse, "source": self.source,
                "frames": animpack.PackedAnimation(self.data).frames if self.data else 0,
                "loose": self.loose[0] if self.loose else "",
                "descr_skeleton": bool(self.text_edit),
                "notes": list(self.notes), "errors": list(self.errors), "ok": self.ok}


def _retime(slot: animpack.Slot, lo: int, speed: float, nf: int) -> animpack.Slot:
    """A copy of ``slot`` with its impact frame and cue frames moved by a trim
    from frame ``lo`` and a speed change, and held inside ``nf`` frames."""
    import copy
    s = copy.deepcopy(slot)
    fix = lambda f: max(0, min(nf - 1, int(round((f - lo) / (speed or 1.0)))))
    if s.impact_frame > 0:
        s.impact_frame = fix(s.impact_frame)
    for e in s.events:
        e.start, e.end = fix(e.start), fix(e.end) if e.end > 0 else e.end
    return s


def _finish(p: SlotPlan, packs: animpack.Packs, sk_entry: animpack.PackEntry,
            sk: animpack.PackedSkeleton, want: str, loose_anim: Optional[casanim.Animation],
            keep_rebuildable: bool) -> SlotPlan:
    """Where the bytes go, the skeleton with its slot pointed there, and the
    rebuildable copy."""
    mod_name = Path(p.mod.data).parent.name
    hit = animpack.content_index(packs, "anims").find(p.data)
    if hit is not None and hit.scale == p.scale:
        if p.old_path and animpack._key(hit.name) == animpack._key(p.old_path):
            p.errors.append(f"{p.skeleton}'s {p.action} plays exactly these bytes already")
            return p
        p.reuse, p.new_path = True, hit.name
        p.notes.append(f"the pack already holds these bytes as {hit.name}; the slot is pointed there "
                       "and nothing is appended")
    else:
        p.new_path = animpack._unique(want, set(packs.anims._names()))
    s = p.new_slot
    s.path = p.new_path
    sk.slots[p.slot] = s
    p.skeleton_bytes = sk.to_bytes()
    p.stamp = animpack._stamp(packs.dir)
    if len(packs.skels.find(sk_entry.name)) > 1:
        p.notes.append(f"the skeleton pack lists {sk_entry.name} more than once; the first copy, "
                       "the one the game plays, is the one changed")
    if keep_rebuildable and not p.reuse:
        rel = animloose.loose_rel(mod_name, p.new_path)
        if (Path(p.mod.data) / rel).exists():
            p.notes.append(f"{rel} is a file already; it is left alone, and a rebuild would read it")
        elif loose_anim is not None:
            p.loose = (rel, casanim.write_anim(loose_anim))
        for name in skelslots.names(p.slot) or (p.action,):
            edit = animedit._assign(p.mod, p.skeleton, name, rel, full=p.new_path)
            if not isinstance(edit, str):
                p.text_edit = edit
                break
        if p.text_edit is None:
            p.notes.append(f"descr_skeleton.txt has no {p.action} line for {p.skeleton} to point at the "
                           "new file, so a rebuild of the packs would not keep it")
    return p


def plan_edit(mod, skeleton: str, slot: int, edits: Optional[Dict], name: str = "",
              rel: str = "", keep_rebuildable: bool = True) -> SlotPlan:
    """Save the editor's ``edits`` to ``skeleton``'s ``slot`` into the mod's
    own pack. The action edited is the pack's (what the game plays), or the
    loose file ``rel`` under ``data/`` when the editor opened one. ``name`` is
    the new file's name; it goes under ``animations/edited/<skeleton>/``."""
    p = SlotPlan(kind="edit", mod=mod, skeleton=skeleton, slot=int(slot),
                 action=skelslots.label(int(slot)) if 0 <= int(slot) < animpack.SKELETON_SLOTS else "")
    if not rel and not any((v not in (None, "", 1) if k == "speed" else v not in (None, "", [], {}, False))
                           for k, v in (edits or {}).items()):
        p.errors.append("nothing is edited: the slot would play what it plays now")
        return p
    try:
        packs = _own(mod.data)
        sk_entry, sk = _skeleton(packs, skeleton)
        p.skeleton = sk_entry.name
        cur = sk.slots[p.slot] if 0 <= p.slot < len(sk.slots) else None
        if cur is None:
            raise SlotError(f"{sk_entry.name} leaves {p.action or p.slot} empty; there is no action to edit")
        p.old_path = cur.path
        nq = _rot_bones(packs, sk, p.slot)
        if rel:
            src = Path(mod.data) / rel
            if not src.is_file():
                raise SlotError(f"{rel!r} is not a file in this mod")
            base, missing = onto(casanim.read_anim(src, skeleton, mod.data), sk, nq)
            if missing:
                p.notes.append(f"{len(missing)} of {sk_entry.name}'s bones are not in {Path(rel).name} "
                               f"and hold their bind pose: {', '.join(missing[:6])}"
                               f"{'...' if len(missing) > 6 else ''}")
            p.source = rel
        else:
            e = animpack.resolve_slot(packs.anims, cur.path, sk.scale)
            if e is None:
                raise SlotError(f"pack.idx has no {cur.path!r}")
            base = animloose.to_cas(packs.anims.read_entry(e), sk.bone_table(), e.scale, cur.path,
                                    bone_scale=sk.scale)
            p.source = cur.path
        edited = animedit.apply_edits(base, edits)
        p.data, p.scale = pack_for(packs, sk, p.slot, edited), sk.scale or 1.0
    except (SlotError, animpack.PackError, casanim.AnimError, animedit.EditError,
            animloose.LooseError, ValueError, TypeError) as exc:
        p.errors.append(str(exc))
        return p
    e = edits or {}
    trim = e.get("trim") or [0]
    nf = animpack.PackedAnimation(p.data).frames
    p.new_slot = _retime(cur, int(trim[0]), float(e.get("speed") or 1.0), nf) if not rel else _retime(cur, 0, 1.0, nf)
    stem = (name or Path(cur.path.replace("\\", "/")).stem + "_edited").strip().replace("\\", "/")
    stem = stem.rsplit("/", 1)[-1]
    if stem.lower().endswith(".cas"):
        stem = stem[:-4]
    if not stem or not animedit._SAFE.match(stem):
        p.errors.append(f"{stem!r}: name the file with letters, digits, _ . and -")
        return p
    mod_name = Path(mod.data).parent.name
    want = f"mods/{mod_name}/data/animations/edited/{p.skeleton}/{stem}.cas"
    return _finish(p, packs, sk_entry, sk, want, on_frames(edited), keep_rebuildable)


def preview_edit(mod, skeleton: str, slot: int, edits: Optional[Dict], rel: str = "") -> casanim.Animation:
    """What :func:`plan_edit` would write, read back as the viewer plays a
    pack entry: the preview is the bytes the game would get."""
    p = plan_edit(mod, skeleton, slot, edits, name="preview", rel=rel, keep_rebuildable=False)
    if p.errors and not p.data:
        raise SlotError("; ".join(p.errors))
    packs = _own(mod.data)
    _e, sk = _skeleton(packs, skeleton)
    return casanim.read_packed_bytes(p.data, p.old_path, sk.bone_table(), skeleton)


def plan_bring(mod, skeleton: str, slot: int, source_mod, source_skeleton: str = "",
               keep_rebuildable: bool = True) -> SlotPlan:
    """``source_skeleton``'s ``slot`` in ``source_mod`` (its own packs, or
    vanilla's when it ships none) played by this mod's ``skeleton`` in the
    same slot: appended under ``animations/ported/<source>/...`` unless this
    pack holds the bytes already."""
    p = SlotPlan(kind="bring", mod=mod, skeleton=skeleton, slot=int(slot),
                 action=skelslots.label(int(slot)) if 0 <= int(slot) < animpack.SKELETON_SLOTS else "")
    source_skeleton = source_skeleton or skeleton
    try:
        packs = _own(mod.data)
        sk_entry, sk = _skeleton(packs, skeleton)
        p.skeleton = sk_entry.name
        src, whose = animpack.packs_for(source_mod.data)
        if src is None or src.anims is None or src.skels is None:
            raise SlotError(f"{source_mod.name} has no animation packs, and vanilla's were not found")
        _se, ssk = _skeleton(src, source_skeleton)
        sslot = ssk.slots[p.slot] if 0 <= p.slot < len(ssk.slots) else None
        if sslot is None:
            raise SlotError(f"{source_mod.name}'s {_se.name} leaves {p.action} empty")
        e = animpack.resolve_slot(src.anims, sslot.path, ssk.scale)
        if e is None:
            raise SlotError(f"{source_mod.name}'s pack.idx has no {sslot.path!r}")
        raw = src.anims.read_entry(e)
        cur = sk.slots[p.slot]
        p.old_path = cur.path if cur is not None else ""
        p.source = f"{source_mod.name}: {sslot.path}" + (" (vanilla's packs)" if whose == "vanilla" else "")
        nq = e.rot_bones or len(ssk.bones)
        loose_anim = animloose.to_cas(raw, ssk.bone_table(), e.scale, sslot.path, bone_scale=ssk.scale)
        if _same_bones(ssk, sk, nq):
            p.data, p.scale = raw, e.scale
            loose_anim = animloose.to_cas(raw, sk.bone_table(), e.scale, sslot.path, bone_scale=sk.scale)
        else:
            dnq = _rot_bones(packs, sk, p.slot)
            moved, missing = onto(loose_anim, sk, dnq)
            p.data, p.scale = pack_for(packs, sk, p.slot, moved), sk.scale or 1.0
            loose_anim = on_frames(moved)
            p.notes.append(f"{_se.name} in {source_mod.name} has other bones than {p.skeleton} here, "
                           f"so the animation is carried across bone by bone, by name"
                           + (f"; {len(missing)} bone(s) it does not move hold their bind pose: "
                              f"{', '.join(missing[:6])}{'...' if len(missing) > 6 else ''}" if missing else ""))
    except (SlotError, animpack.PackError, casanim.AnimError, animloose.LooseError,
            ValueError, TypeError) as exc:
        p.errors.append(str(exc))
        return p
    nf = animpack.PackedAnimation(p.data).frames
    if cur is not None:
        # this skeleton's own timing for the slot, its cues and its combat
        # settings; only the impact frame is held inside the new frames
        p.new_slot = _retime(cur, 0, 1.0, nf)
        if cur.impact_frame > 0 and sslot.impact_frame > 0 and cur.impact_frame != sslot.impact_frame:
            p.notes.append(f"the slot keeps {p.skeleton}'s impact frame, {p.new_slot.impact_frame}; "
                           f"{source_mod.name} strikes at frame {sslot.impact_frame}")
    else:
        import copy
        p.new_slot = copy.deepcopy(sslot)
        if p.new_slot.events:
            p.notes.append(f"{len(p.new_slot.events)} sound or effect cue(s) of {source_mod.name}'s slot "
                           "are left out: their names are that mod's")
            p.new_slot.events = []
    mod_name = Path(mod.data).parent.name
    want = f"mods/{mod_name}/data/animations/ported/{_tag(source_mod.name)}/{animpack._tail_of(sslot.path)}"
    if p.old_path and animpack._key(p.old_path) == animpack._key(sslot.path):
        hit = animpack.resolve_slot(packs.anims, p.old_path, sk.scale)
        if hit is not None and packs.anims.read_entry(hit) == p.data:
            p.errors.append(f"{p.skeleton}'s {p.action} is that animation already, byte for byte")
            return p
    return _finish(p, packs, sk_entry, sk, want, loose_anim, keep_rebuildable)


# ---------------------------------------------------------------------------
# writing one

def apply(p: SlotPlan) -> dict:
    """Write ``p``: the bytes appended to ``pack.dat`` (unless reused), the
    skeleton's entry written with its slot pointed at them, and the loose
    copy and ``descr_skeleton.txt`` line. One job in the transfer log; Undo
    truncates ``pack.dat`` back and puts the rest back from the backup."""
    from . import config
    from .logutil import file_op, log

    if not p.ok:
        raise SlotError("cannot save: " + ("; ".join(p.errors) or "nothing planned"))
    running = animpack.game_running()
    if running:
        raise SlotError(f"{', '.join(running)} is running and holds the packs open; close the game first")
    data = Path(p.mod.data)
    packs = _own(data)
    if animpack._stamp(packs.dir) != p.stamp:
        raise SlotError("the mod's packs changed since this was planned; plan it again")
    need = len(p.data) + 2 * (packs.skels.dat_path.stat().st_size + packs.anims.path.stat().st_size) \
        + animpack.SPACE_MARGIN
    if shutil.disk_usage(packs.dir).free < need:
        raise SlotError(f"it needs {need / 1e6:.0f} MB free on that drive")
    rel_dir = packs.dir.relative_to(data).as_posix()
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, list] = {"backed_up": [], "created": [], "appended": []}

    def keep(rel: str) -> Path:
        target = data / rel
        b = backup_root / "data" / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, b)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {b}")
        else:
            manifest["created"].append(rel)
        return target

    for n in (["pack.idx"] if not p.reuse else []) + ["skeletons.idx", "skeletons.dat"]:
        keep(f"{rel_dir}/{n}")
    old_pack_idx = packs.anims.path.read_bytes()
    try:
        if not p.reuse:
            c = animpack.PackedAnimation(p.data)
            entry = animpack.PackEntry(p.new_path, 0, len(p.data), p.scale, c.frames, c.rot_bones, c.pos_bones)
            rec = animpack._append(packs.anims, [(entry, p.data)], f"{rel_dir}/pack.dat")
            manifest["appended"].append(rec)
            file_op("APPEND", packs.anims.dat_path, f"+{rec['added']} bytes ({p.new_path})")
        sk_entry = packs.skels.first(p.skeleton)
        animpack.replace_entry(packs.skels, sk_entry, p.skeleton_bytes)
        file_op("WRITE", packs.skels.dat_path, f"{p.skeleton}'s {p.action} -> {p.new_path}")
    except BaseException:
        for r in manifest["appended"]:
            animpack._put_back(r, packs.anims.dat_path, packs.anims.path, old_pack_idx)
        for n in ("skeletons.idx", "skeletons.dat"):
            shutil.copy2(backup_root / "data" / rel_dir / n, packs.dir / n)
        raise
    files = [f"{rel_dir}/skeletons.dat"]
    if p.loose:
        rel, blob = p.loose
        target = keep(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        file_op("WRITE", target, f"{len(blob)} bytes (kept rebuildable)")
        files.append(rel)
    if p.text_edit:
        rel, text = p.text_edit
        target = keep(rel)
        target.write_bytes(text.encode("latin-1"))
        file_op("WRITE", target, f"{len(text)} chars")
        files.append(rel)
    mod = p.mod
    what = "edited" if p.kind == "edit" else f"from {p.source}"
    summary = f"{p.skeleton}'s {p.action} in {mod.name}: {what}, as {p.new_path}"
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "animation into pack",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": f"{p.skeleton} / {p.action}", "resolved_type": p.new_path,
        "options": {"kind": p.kind, "slot": p.slot, "old_path": p.old_path, "source": p.source},
        "applied": True, "undone": False, "note": "", "summary": summary,
        "warnings": list(p.notes), "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SLOT   %s, id=%s", summary, tid)
    return {"id": tid, "summary": summary, "new_path": p.new_path, "files": files,
            "notes": list(p.notes)}


# ---------------------------------------------------------------------------
# a skeleton ported alone

@dataclass
class SkeletonPort:
    port: Optional[animpack.PortPlan] = None
    loose: Optional[animloose.Rebuild] = None
    entry: str = ""                      # the model entry pointed at it
    entry_skeleton: str = ""             # the name that entry had
    modeldb_text: str = ""
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def dest_name(self) -> str:
        rows = self.port.skeletons if self.port is not None else []
        return rows[0].dest_name if rows else ""

    def payload(self) -> dict:
        return {"port": self.port.payload() if self.port is not None else None,
                "dest_name": self.dest_name,
                "loose": self.loose.payload() if self.loose is not None else None,
                "entry": self.entry, "entry_skeleton": self.entry_skeleton,
                "notes": list(self.notes), "errors": list(self.errors),
                "ok": not self.errors and self.port is not None and self.port.ok}


def plan_skeleton(mod, source_mod, name: str, entry: str = "", entry_skeleton: str = "",
                  keep_rebuildable: bool = True) -> SkeletonPort:
    """``name`` and every animation its slots name, from ``source_mod`` into
    ``mod``'s own packs, as a transfer would bring it; and, when ``entry`` is
    given, that model entry's ``entry_skeleton`` (its body or weapon skeleton
    of that name) pointed at the one the port lands as."""
    out = SkeletonPort()
    out.port = animpack.plan_port(source_mod.data, mod.data, [name], _tag(source_mod.name))
    out.errors += out.port.errors
    out.notes += out.port.notes
    if out.errors:
        return out
    row = out.port.skeletons[0]
    if row.action == "reuse":
        out.notes.append(f"{mod.name} has {row.dest_name} already, byte for byte: nothing to bring")
    elif row.action == "reuse_as":
        out.notes.append(f"{mod.name} has these bytes already, as {row.dest_name}")
    elif row.action == "rename":
        out.notes.append(f"{mod.name}'s pack has another skeleton called {row.name}, so this one "
                         f"comes in as {row.dest_name}"
                         + (f", and {entry} is pointed at it" if entry else
                            "; nothing plays it until a model entry asks for it"))
    if keep_rebuildable and row.appends:
        out.loose = animloose.for_port(out.port, source_mod.data)
        out.notes += out.loose.notes
    if entry:
        e = mod.modeldb.by_name().get(entry.lower())
        if e is None:
            out.errors.append(f"no model entry {entry!r}")
            return out
        old = entry_skeleton or (e.skeletons() or [""])[0]
        if old.lower() not in {x.lower() for x in e.skeletons() + e.weapon_skeletons()}:
            out.errors.append(f"{e.name} names no skeleton {old!r}")
            return out
        out.entry, out.entry_skeleton = e.name, old
        if old == row.dest_name:
            out.notes.append(f"{e.name} asks for {old} already")
        else:
            # the whole file from its parse with the one entry's text changed,
            # as the model editor writes it (Phase 15)
            db = mod.modeldb
            original = list(db.entries)
            import copy
            changed = copy.copy(e)
            changed.raw = modeldb.rename_skeletons(e.raw, {old: row.dest_name}, pad=e.first_entry_pad)
            try:
                db.entries = [changed if x is e else x for x in original]
                out.modeldb_text = db.to_text()
            finally:
                db.entries = original
    return out


def apply_skeleton(sp: SkeletonPort, mod, source_mod) -> dict:
    """Write a :class:`SkeletonPort` as one job: the port (Phase 81's append),
    the rebuildable copy (Phase 84) and the model entry pointed at it."""
    from . import config
    from .logutil import file_op, log

    if sp.errors or sp.port is None or not sp.port.ok:
        raise SlotError("cannot port: " + "; ".join(sp.errors or ["nothing planned"]))
    if not any(s.appends for s in sp.port.skeletons) and not sp.modeldb_text:
        raise SlotError("nothing to write: " + "; ".join(sp.notes))
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest = animpack.apply_port(sp.port, backup_root) if any(
        s.appends for s in sp.port.skeletons) else {"backed_up": [], "created": [], "appended": []}
    for r in manifest["appended"]:
        file_op("APPEND", data / r["rel"], f"+{r['added']} bytes (skeleton port)")

    def keep(rel: str) -> Path:
        target = data / rel
        b = backup_root / "data" / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, b)
            manifest["backed_up"].append(rel)
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    if sp.loose is not None:
        loose = animloose.build(data, [(s.dest_name, s.name) for s in sp.port.skeletons if s.appends],
                                source_mod.data, sp.port.tag)
        for f in loose.files:
            if (data / f.rel).exists():
                continue
            keep(f.rel).write_bytes(f.data)
            file_op("WRITE", data / f.rel, f"{f.size} bytes ({f.kind}, kept rebuildable)")
        if loose.blocks and (data / loose.text_rel).is_file():
            old = (data / loose.text_rel).read_bytes().decode("latin-1")
            keep(loose.text_rel).write_bytes(animloose.append_blocks(
                old, loose.blocks, f"brought from {source_mod.name} by Unit Transfer ({tid})").encode("latin-1"))
    if sp.modeldb_text:
        rel = Path(mod.modeldb_path).relative_to(data).as_posix()
        keep(rel).write_text(sp.modeldb_text, encoding=modeldb.ENCODING)
        file_op("WRITE", data / rel, f"{sp.entry}: {sp.entry_skeleton} -> {sp.dest_name}")
    summary = (f"skeleton {sp.port.skeletons[0].name} from {source_mod.name} into {mod.name}"
               + (f" as {sp.dest_name}" if sp.dest_name != sp.port.skeletons[0].name else "")
               + (f"; {sp.entry} plays it" if sp.modeldb_text else ""))
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "skeleton port",
        "source": source_mod.name, "source_root": str(source_mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": sp.port.skeletons[0].name, "resolved_type": sp.dest_name,
        "options": {"tag": sp.port.tag, "renames": sp.port.renames, "entry": sp.entry},
        "applied": True, "undone": False, "note": "", "summary": summary,
        "warnings": list(sp.notes), "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("PORT   %s, id=%s", summary, tid)
    return {"id": tid, "summary": summary, "dest_name": sp.dest_name, "notes": list(sp.notes)}
