r"""Kitbash a skeleton: a new one made from a base, slots taken from others, slots cleared.

A skeleton in the packs is a set of up to 687 action slots (stand, walk, each
attack...). This makes a **new** skeleton in the mod's own packs, a copy of a
``base`` skeleton under a name of its own, and changes slots in it:

* **a slot taken from another skeleton**: any skeleton, in this mod or another
  (its own packs, or vanilla's when it ships none), and from any of its slots,
  so a source's ``stand_a_idle`` can be this skeleton's ``walk``;
* **a slot cleared**: the action is left empty, as skeletons leave the ones they
  do not play. ``default`` cannot be cleared: the engine needs it.

Nothing that exists changes: units play the new skeleton once a model entry
names it. The whole kit is one job in the transfer log and one Undo.

How a slot's animation is carried across
----------------------------------------
When the source skeleton has this skeleton's bones (the same names, in the
same order, for the bones the animation turns) and no bone map is given, the
packed bytes are used as they are, as :func:`animslot.plan_bring` does.
Otherwise the animation is read onto the source's bones, each track renamed by
the change's ``bone_map`` (source bone -> this skeleton's bone, any case), and
put on this skeleton by name: a bone no track reaches holds its bind pose, and
the plan says which. That is "forced to match": a renamed bone, a second
weapon bone, a creature whose bones are called something else.

The slot's settings (impact frame, turn limits, sound cues) are the base's for
that slot when the base fills it, held inside the new frame count; else the
source slot's, its cues left out when it comes from another mod, whose cue
names are that mod's.

Kept rebuildable as a port is (:mod:`unittransfer.animloose`): a loose ``.cas``
for each animation it plays that has no file yet, and a ``type`` block in
``descr_skeleton.txt``, so a modder who deletes the packs to have the game
rebuild them keeps the kit.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import animloose, animpack, animslot, casanim, skelslots
from . import i18n as _i18n

DEFAULT_SLOT = animslot.DEFAULT_SLOT
_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,63}$")


class KitError(ValueError):
    pass


@dataclass
class Change:
    """One slot of the new skeleton: cleared, or taken from ``skeleton``'s
    ``source_slot`` in mod ``source`` ("" for this mod, -1 for the same slot)."""
    slot: int
    clear: bool = False
    source: str = ""
    skeleton: str = ""
    source_slot: int = -1
    bone_map: Dict[str, str] = field(default_factory=dict)
    #: 128g: the slot's impact frame and turn limits (degrees), when set
    impact_frame: Optional[int] = None
    turn: Optional[Tuple[float, float]] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Change":
        try:
            slot = int(d.get("slot"))
            ss = d.get("source_slot")
            ss = int(ss) if ss not in (None, "") else -1
        except (TypeError, ValueError):
            raise KitError(_i18n.msg("eng.animkit.a_change_needs_a_slot_number", "a change needs a slot number")) from None
        bm = d.get("bone_map") if isinstance(d.get("bone_map"), dict) else {}
        try:
            imp = d.get("impact_frame")
            imp = int(imp) if imp not in (None, "") else None
            turn = d.get("turn")
            turn = (float(turn[0]), float(turn[1])) if isinstance(turn, (list, tuple)) and len(turn) == 2 else None
        except (TypeError, ValueError):
            raise KitError(_i18n.msg("eng.animkit.timing_numbers", "the impact frame and turn limits are numbers")) from None
        return cls(slot=slot, clear=bool(d.get("clear")), source=str(d.get("source") or ""),
                   skeleton=str(d.get("skeleton") or ""), source_slot=ss,
                   bone_map={str(k): str(v) for k, v in bm.items() if k and v},
                   impact_frame=imp, turn=turn)


@dataclass
class KitRow:
    slot: int
    action: str = ""
    clear: bool = False
    source: str = ""
    new_path: str = ""
    reuse: bool = False
    data: bytes = b""
    scale: float = 1.0
    loose_anim: Optional[casanim.Animation] = None
    #: the source's slot, and whether it is another mod's
    src_slot: Optional[animpack.Slot] = None
    foreign: bool = False
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {"slot": self.slot, "action": self.action, "clear": self.clear,
                "source": self.source, "new_path": self.new_path, "reuse": self.reuse,
                "frames": animpack.PackedAnimation(self.data).frames if self.data else 0,
                "notes": list(self.notes), "errors": list(self.errors)}


@dataclass
class KitPlan:
    mod: object = None
    base: str = ""
    name: str = ""
    rows: List[KitRow] = field(default_factory=list)
    skeleton_bytes: bytes = b""
    stamp: tuple = ()
    keep_rebuildable: bool = True
    #: 128g: ``name`` is a skeleton there already, changed in place
    extend: bool = False
    #: 128g: a model entry pointed at the skeleton
    entry: str = ""
    entry_skeleton: str = ""
    modeldb_text: str = ""
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not any(r.errors for r in self.rows) and bool(self.skeleton_bytes)

    @property
    def appends(self) -> List[KitRow]:
        return [r for r in self.rows if r.data and not r.reuse]

    def payload(self) -> dict:
        return {"base": self.base, "name": self.name, "rows": [r.payload() for r in self.rows],
                "extend": self.extend, "entry": self.entry, "entry_skeleton": self.entry_skeleton,
                "appends": len(self.appends), "bytes": sum(len(r.data) for r in self.appends),
                "notes": list(self.notes),
                "errors": list(self.errors) + [f"{r.action or r.slot}: {e}" for r in self.rows for e in r.errors],
                "ok": self.ok}


def _label(slot: int) -> str:
    return skelslots.label(slot) if 0 <= slot < animpack.SKELETON_SLOTS else str(slot)


def _source_packs(mod, source_mod) -> Tuple[animpack.Packs, str]:
    if source_mod is None or source_mod is mod:
        return animslot._own(mod.data), ""
    src, whose = animpack.packs_for(source_mod.data)
    if src is None or src.anims is None or src.skels is None:
        raise KitError(_i18n.msg("eng.animkit.has_no_animation_packs", "{name} has no animation packs, and vanilla's were not found", name=source_mod.name))
    return src, whose


def carry(mod, packs: animpack.Packs, base: animpack.PackedSkeleton, slot: int,
          change: Change, source_mod=None) -> KitRow:
    """One change's animation as this skeleton would play it in ``slot``:
    the bytes, their index scale, and what was not carried."""
    row = KitRow(slot=slot, action=_label(slot))
    sslot_i = change.source_slot if change.source_slot >= 0 else slot
    try:
        src, whose = _source_packs(mod, source_mod)
        sname = change.skeleton or base_name_of(base)
        _se, ssk = animslot._skeleton(src, sname)
        sslot = ssk.slots[sslot_i] if 0 <= sslot_i < len(ssk.slots) else None
        who = source_mod.name if source_mod is not None and source_mod is not mod else mod.name
        if sslot is None:
            raise KitError(_i18n.msg("eng.animkit.leaves_empty", "{skeleton} in {mod} leaves {action} empty", skeleton=_se.name, mod=who, action=_label(sslot_i)))
        e = animpack.resolve_slot(src.anims, sslot.path, ssk.scale)
        if e is None:
            raise KitError(_i18n.msg("eng.animkit.pack_idx_has_no", "{mod}'s pack.idx has no {path}", mod=who, path=repr(sslot.path)))
        raw = src.anims.read_entry(e)
        row.source = f"{who}: {_se.name} / {_label(sslot_i)}" + (" (vanilla's packs)" if whose == "vanilla" else "")
        nq = e.rot_bones or len(ssk.bones)
        if not change.bone_map and animslot._same_bones(ssk, base, nq):
            row.data, row.scale = raw, e.scale
            row.loose_anim = animloose.to_cas(raw, base.bone_table(), e.scale, sslot.path, bone_scale=base.scale)
        else:
            anim = animloose.to_cas(raw, ssk.bone_table(), e.scale, sslot.path, bone_scale=ssk.scale)
            if change.bone_map:
                have = {b.name.lower() for b in ssk.bones}
                want = {b.name.lower() for b in base.bones}
                bad = [k for k in change.bone_map if k.lower() not in have]
                bad += [v for v in change.bone_map.values() if v.lower() not in want]
                if bad:
                    raise KitError(_i18n.msg("eng.animkit.bone_map_names_bones_that_are_not",
                                             "the bone map names bones the skeletons do not have: {names}",
                                             names=", ".join(bad[:6])))
                renamed = {k.lower(): v for k, v in change.bone_map.items()}
                for t in anim.tracks[1:]:
                    if t.name.lower() in renamed:
                        t.name = renamed[t.name.lower()]
            moved, missing = animslot.onto(anim, base, animslot._rot_bones(packs, base, slot))
            shift = animslot.root_shift(anim, base)
            if shift:
                row.notes.append(shift)
            if missing:
                row.notes.append(_i18n.msg("eng.animkit.carried_bone_by_bone",
                                           "carried bone by bone; {n} bone(s) it does not reach hold their bind pose: {names}",
                                           n=len(missing), names=", ".join(missing[:6]) + ("..." if len(missing) > 6 else "")))
            else:
                row.notes.append(_i18n.msg("eng.animkit.carried_bone_by_bone_all", "carried bone by bone, every bone reached"))
            row.data, row.scale = animslot.pack_for(packs, base, slot, moved), base.scale or 1.0
            row.loose_anim = animslot.on_frames(moved)
        row.src_slot = sslot
        row.foreign = source_mod is not None and source_mod is not mod
    except (KitError, animslot.SlotError, animpack.PackError, casanim.AnimError,
            animloose.LooseError, ValueError, TypeError) as exc:
        row.errors.append(str(exc))
    return row


def base_name_of(sk: animpack.PackedSkeleton) -> str:
    return getattr(sk, "_kit_name", "")


def _base(packs: animpack.Packs, name: str) -> animpack.PackedSkeleton:
    e, sk = animslot._skeleton(packs, name)
    sk._kit_name = e.name                    # type: ignore[attr-defined]
    return sk


def _turn(deg: float) -> int:
    """Degrees as a slot stores a turn limit: int16, times pi/32768 radians."""
    return max(-32768, min(32767, int(round(float(deg) * 32768.0 / 180.0))))


def plan_kit(mod, base: str, name: str, changes: List[Change], sources: Optional[Dict[str, object]] = None,
             keep_rebuildable: bool = True, extend: bool = False, entry: str = "",
             entry_skeleton: str = "") -> KitPlan:
    """The new skeleton ``name``: ``base`` with ``changes`` made, in order.
    With ``extend`` (128g), ``name`` is a skeleton of the mod's own pack
    already, a kit made earlier, and the changes are made to it in place:
    ``base`` is ignored. With ``entry``, that model entry's
    ``entry_skeleton`` (its first body skeleton when not given) is pointed at
    ``name``, as a port does. ``sources`` maps a change's ``source`` mod name
    to its mod. Writes nothing."""
    if extend:
        base = name
    p = KitPlan(mod=mod, base=base, name=name, keep_rebuildable=keep_rebuildable, extend=extend)
    sources = sources or {}
    try:
        packs = animslot._own(mod.data)
        sk = _base(packs, base)
        p.base = base_name_of(sk)
        if extend:
            p.name = name = p.base
    except (animslot.SlotError, animpack.PackError) as e:
        p.errors.append(str(e))
        return p
    if extend:
        if len(packs.skels.find(name)) > 1:
            p.notes.append(_i18n.msg("eng.animslot.the_skeleton_pack_lists_more_than", "the skeleton pack lists {name} more than once; the first copy, the one the game plays, is the one changed", name=name))
    elif not _NAME.match(name or ""):
        p.errors.append(_i18n.msg("eng.animkit.name_the_skeleton", "{name}: name the new skeleton with letters, digits, _ and -", name=repr(name)))
    elif packs.skels.first(name) is not None or name.lower() in casanim.skeleton_types(mod.data):
        p.errors.append(_i18n.msg("eng.animkit.already_a_skeleton", "{name} is a skeleton in this mod already: pick a new name", name=name))
    if not changes:
        p.errors.append(_i18n.msg("eng.animkit.no_changes", "no slot is changed: the copy would be the base itself"))
    if p.errors:
        return p
    original = _base(packs, base)            # the base as it is, for bone counts
    mod_name = Path(mod.data).parent.name
    taken = set(packs.anims._names())
    index = animpack.content_index(packs, "anims")
    seen: Dict[Tuple[bytes, float], str] = {}
    done_slots = set()
    for ch in changes:
        if not 0 <= ch.slot < animpack.SKELETON_SLOTS:
            p.errors.append(_i18n.msg("eng.animkit.no_slot", "there is no slot {slot}", slot=ch.slot))
            continue
        if ch.slot in done_slots:
            p.notes.append(_i18n.msg("eng.animkit.slot_twice", "{action} is changed twice; the last change wins", action=_label(ch.slot)))
            p.rows = [r for r in p.rows if r.slot != ch.slot]
        done_slots.add(ch.slot)
        if ch.clear:
            row = KitRow(slot=ch.slot, action=_label(ch.slot), clear=True)
            if ch.slot == DEFAULT_SLOT:
                row.errors.append(_i18n.msg("eng.animkit.default_stays", "default cannot be cleared: the engine plays it whenever a slot is empty"))
            elif original.slots[ch.slot] is None:
                row.notes.append(_i18n.msg("eng.animkit.already_empty", "{base} leaves it empty already", base=p.base))
            p.rows.append(row)
            continue
        src_mod = sources.get(ch.source) if ch.source else None
        if ch.source and src_mod is None:
            p.rows.append(KitRow(slot=ch.slot, action=_label(ch.slot),
                                 errors=[_i18n.msg("eng.animkit.no_mod", "no mod {name}", name=repr(ch.source))]))
            continue
        if not ch.skeleton:
            ch.skeleton = p.base
        row = carry(mod, packs, original, ch.slot, ch, src_mod)
        if row.data:
            hit = index.find(row.data) if index is not None else None
            if hit is not None and hit.scale == row.scale:
                row.reuse, row.new_path = True, hit.name
            elif (row.data, row.scale) in seen:
                row.reuse, row.new_path = True, seen[(row.data, row.scale)]
            else:
                tail = animpack._tail_of(row.src_slot.path)
                row.new_path = animpack._unique(
                    f"mods/{mod_name}/data/animations/kit/{animslot._tag(name)}/{tail}", taken)
                taken = set(taken) | {animpack._key(row.new_path)}
                seen[(row.data, row.scale)] = row.new_path
        p.rows.append(row)
    if p.errors or any(r.errors for r in p.rows):
        return p
    # the new skeleton: the base's bytes, the slots changed
    sk = _base(packs, base)
    for row in p.rows:
        if row.clear:
            sk.slots[row.slot] = None
            continue
        nf = animpack.PackedAnimation(row.data).frames
        cur = original.slots[row.slot]
        if cur is not None:
            new = animslot._retime(cur, 0, 1.0, nf)
        else:
            new = animslot._retime(row.src_slot, 0, 1.0, nf)
            if row.foreign and new.events:
                row.notes.append(_i18n.msg("eng.animkit.cues_left_out", "{n} sound or effect cue(s) of the source slot are left out: their names are the other mod's", n=len(new.events)))
                new.events = []
        new.path = row.new_path
        ch = next(c for c in reversed(changes) if c.slot == row.slot)
        if ch.impact_frame is not None:
            if not 0 <= ch.impact_frame < nf:
                row.errors.append(_i18n.msg("eng.animkit.impact_outside", "an impact frame of {n} is outside the animation's frames, 0 to {last}", n=ch.impact_frame, last=nf - 1))
            new.impact_frame = ch.impact_frame
        if ch.turn is not None:
            lo, hi = ch.turn
            if not -180 <= lo <= hi <= 180:
                row.errors.append(_i18n.msg("eng.animkit.turn_outside", "turn limits {lo:g} to {hi:g}: give the least first, both inside -180 to 180 degrees", lo=lo, hi=hi))
            new.min_turn, new.max_turn = _turn(lo), _turn(hi)
        sk.slots[row.slot] = new
    if any(r.errors for r in p.rows):
        return p
    if sk.slots[DEFAULT_SLOT] is None:
        p.errors.append(_i18n.msg("eng.animkit.default_stays", "default cannot be cleared: the engine plays it whenever a slot is empty"))
        return p
    p.skeleton_bytes = sk.to_bytes()
    if extend and p.skeleton_bytes == packs.skels.read_entry(packs.skels.first(name)) and not p.appends:
        p.errors.append(_i18n.msg("eng.animkit.extend_no_change", "{name} plays all of this already: nothing would change", name=name))
        return p
    p.stamp = animpack._stamp(packs.dir)
    if entry:
        p.entry, p.entry_skeleton, p.modeldb_text, notes, errors = animslot.point_entry(
            mod, entry, entry_skeleton, name)
        p.notes += notes
        p.errors += errors
    elif not extend:
        p.notes.append(_i18n.msg("eng.animkit.nothing_plays_it", "nothing plays {name} until a model entry names it", name=name))
    return p


def preview(mod, base: str, change: Change, sources: Optional[Dict[str, object]] = None) -> casanim.Animation:
    """What one change would put in its slot, read back as the viewer plays a
    pack entry: the bytes the game would get, on the base's bones."""
    packs = animslot._own(mod.data)
    sk = _base(packs, base)
    if change.clear:
        raise KitError(_i18n.msg("eng.animkit.cleared_nothing_to_play", "a cleared slot has nothing to play"))
    if not change.skeleton:
        change.skeleton = base_name_of(sk)
    src = (sources or {}).get(change.source) if change.source else None
    if change.source and src is None:
        raise KitError(_i18n.msg("eng.animkit.no_mod", "no mod {name}", name=repr(change.source)))
    row = carry(mod, packs, sk, change.slot, change, src)
    if row.errors:
        raise KitError("; ".join(row.errors))
    if row.scale != (sk.scale or 1.0) and row.scale:
        return casanim.read_packed_bytes(row.data, row.action, sk.bone_table(), base_name_of(sk),
                                         rescale=(sk.scale or 1.0) / row.scale)
    return casanim.read_packed_bytes(row.data, row.action, sk.bone_table(), base_name_of(sk))


def kit_names(mod) -> List[str]:
    """The skeletons kitbashed in ``mod`` (the transfer log's kits, not
    undone) that its own pack still holds, to add to (128g)."""
    from . import config
    try:
        packs = animslot._own(mod.data)
    except (animslot.SlotError, animpack.PackError):
        return []
    out: List[str] = []
    for rec in config.load_log():
        if rec.get("action") != "skeleton kit" or rec.get("undone") or not rec.get("applied"):
            continue
        if str(rec.get("dest_root") or "") != str(mod.root):
            continue
        name = str(rec.get("resolved_type") or "")
        e = packs.skels.first(name) if name else None
        if e is not None and e.name not in out:
            out.append(e.name)
    return out


def apply_kit(p: KitPlan) -> dict:
    """Write ``p``: its animations appended to ``pack.dat``, the new skeleton
    appended to ``skeletons.dat``, and the rebuildable copy. One job in the
    transfer log; Undo cuts both packs back and takes the files out again."""
    from . import config
    from .logutil import file_op, log

    if not p.ok:
        raise KitError(_i18n.msg("eng.animkit.cannot_write", "cannot write the kit: {why}",
                                 why="; ".join(p.payload()["errors"]) or "nothing planned"))
    running = animpack.game_running()
    if running:
        raise KitError(_i18n.msg("eng.animkit.game_running", "{running} is running and holds the packs open; close the game first", running=", ".join(running)))
    data = Path(p.mod.data)
    packs = animslot._own(data)
    if animpack._stamp(packs.dir) != p.stamp:
        raise KitError(_i18n.msg("eng.animkit.packs_changed", "the mod's packs changed since this was planned; plan it again"))
    need = sum(len(r.data) for r in p.appends) + len(p.skeleton_bytes) + animpack.SPACE_MARGIN
    if shutil.disk_usage(packs.dir).free < need:
        raise KitError(_i18n.msg("eng.animkit.disk", "it needs {x:.0f} MB free on that drive", x=need / 1e6))
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
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    jobs = []
    if p.appends:
        blobs = []
        for r in p.appends:
            c = animpack.PackedAnimation(r.data)
            blobs.append((animpack.PackEntry(r.new_path, 0, len(r.data), r.scale, c.frames,
                                             c.rot_bones, c.pos_bones), r.data))
        jobs.append((packs.anims, "pack", blobs))
    if not p.extend:
        jobs.append((packs.skels, "skeletons", [(animpack.PackEntry(p.name, 0, len(p.skeleton_bytes)),
                                                 p.skeleton_bytes)]))
    for idx, stem, _b in jobs:
        keep(f"{rel_dir}/{stem}.idx")
    if p.extend:
        # the skeleton's entry written again in place (a second copy under
        # its name would never play), so its pair is backed up whole
        keep(f"{rel_dir}/skeletons.idx")
        keep(f"{rel_dir}/skeletons.dat")
    done = []
    try:
        for idx, stem, blobs in jobs:
            old = idx.path.read_bytes()
            rec = animpack._append(idx, blobs, f"{rel_dir}/{stem}.dat")
            manifest["appended"].append(rec)
            done.append((idx, old))
            file_op("APPEND", idx.dat_path, f"+{rec['added']} bytes (skeleton kit {p.name})")
        if p.extend:
            animpack.replace_entry(packs.skels, packs.skels.first(p.name), p.skeleton_bytes)
            file_op("WRITE", packs.skels.dat_path, f"skeleton kit {p.name}, added to")
    except BaseException:
        for (idx, old), rec in zip(reversed(done), reversed(manifest["appended"])):
            animpack._put_back(rec, idx.dat_path, idx.path, old)
        if p.extend:
            for n in ("skeletons.idx", "skeletons.dat"):
                shutil.copy2(backup_root / "data" / rel_dir / n, packs.dir / n)
        raise
    files: List[str] = []
    notes = list(p.notes) + [n for r in p.rows for n in r.notes]
    if p.keep_rebuildable:
        built = animloose.build(data, [(p.name, p.base)], data, f"kit_{animslot._tag(p.name)}", again=p.extend)
        notes += built.notes + built.errors
        for f in built.files:
            if (data / f.rel).exists():
                continue
            keep(f.rel).write_bytes(f.data)
            file_op("WRITE", data / f.rel, f"{f.size} bytes ({f.kind}, kept rebuildable)")
            files.append(f.rel)
        if built.blocks and (data / built.text_rel).is_file():
            old = (data / built.text_rel).read_bytes().decode("latin-1")
            why = f"skeleton kit {p.name} from {p.base} by Unit Transfer ({tid})"
            new = (animloose.replace_block(old, p.name, built.blocks[p.name], why) if p.extend
                   else animloose.append_blocks(old, built.blocks, why))
            keep(built.text_rel).write_bytes(new.encode("latin-1"))
            files.append(built.text_rel)
    if p.modeldb_text:
        rel = animslot.write_modeldb(p.mod, keep, p.modeldb_text)
        file_op("WRITE", data / rel, f"{p.entry}: {p.entry_skeleton} -> {p.name}")
        files.append(rel)
    mod = p.mod
    taken = sum(1 for r in p.rows if not r.clear)
    cleared = sum(1 for r in p.rows if r.clear)
    summary = (f"skeleton {p.name} in {mod.name}: {p.base} with {taken} slot(s) taken and {cleared} cleared"
               if not p.extend else
               f"skeleton kit {p.name} in {mod.name}: {taken} slot(s) changed and {cleared} cleared")
    if p.modeldb_text:
        summary += f"; {p.entry} plays it"
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "skeleton kit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.base, "resolved_type": p.name,
        "options": {"rows": [r.payload() for r in p.rows], "extend": p.extend, "entry": p.entry},
        "applied": True, "undone": False, "note": "", "summary": summary,
        "warnings": notes, "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("KIT    %s, id=%s", summary, tid)
    return {"id": tid, "summary": summary, "name": p.name, "files": files, "notes": notes}
