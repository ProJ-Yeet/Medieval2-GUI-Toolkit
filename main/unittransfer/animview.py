r"""Every animation a model has, for the Models viewer, straight from the packs (Phase 80).

Phase 55's viewer played what ``descr_skeleton.txt`` names and the mod ships
loose, which for DaC was 1 753 of 15 661 and for most mods nothing. The game
plays the packs, so the viewer does too now:

* **the skeletons** come from the model's modeldb entry, one set per mount
  type (``none``, ``horse``, ``camel``...), each a primary and a secondary
  skeleton and the weapon skeletons of each;
* **the actions** are the filled slots of each skeleton **in
  ``skeletons.dat``**, named by Phase 78's table and grouped by family, with
  the frame count, duration, distance and speed of each out of its
  ``pack.dat`` entry, and the slot's impact frame, turn limits and sound
  events;
* **the keys** are read straight out of ``pack.dat`` and given the packed
  skeleton's bones (:func:`read`). A loose file at the same path is still
  preferred, as the game may prefer it too (Phase 82's question 6).

A mod with no pack of its own plays vanilla's, as the game does, and the view
says so. A skeleton the packs have not got falls back to Phase 55's chain,
``descr_skeleton.txt`` and loose files only.

80b adds the unit as the game assembles it:

* **the weapon skeletons** (:func:`add_weapons`). A weapon skeleton is two or
  three bones rooted at a hand (``bone_Rhand``, ``bone_weapon01``), its root's
  pivot where that hand is in the T-pose. Its action for the body's slot, or
  its ``default`` when that slot is empty, is resampled onto the body's keys
  and its bones hung under the body's hand, so a mesh weighted to
  ``bone_weapon01`` (1 066 of ROCSS's 1 800 soldier meshes) moves its weapon
  with the arm instead of with the pelvis;
* **the mount** (:func:`mounts_for`): the mounts a rider's units ride, out of
  the EDU and ``descr_mount.txt``, each with its model and ``rider_offset``,
  where the rider sits relative to the mount's root bone;
* **a ``.cas`` model** (:func:`cas_view`), played by the skeleton its
  ``descr_model_strat.txt`` entry names;
* **the same action in another mod** (:func:`compare`), for the side-by-side
  view a port is checked with.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import animpack, casanim, skelslots

#: An event's type, as descr_skeleton.txt's event files use them.
EVENT_TYPES = {1: "sound", 2: "sound bank", 3: "shockwave", 4: "voice", 5: "ambient"}

#: The last slot, ``default``, filled in every skeleton: what a weapon plays
#: when its slot for the body's action is empty.
DEFAULT_SLOT = animpack.SKELETON_SLOTS - 1


def packs_for(data_dir) -> Tuple[Optional[animpack.Packs], str]:
    """The packs a mod plays: its own, or vanilla's when it ships none.
    ``("", None)`` when neither can be found."""
    own = animpack.for_data(data_dir)
    if own is not None and own.skels is not None:
        return own, "mod"
    data = Path(data_dir)
    # <game>/mods/<mod>/data -> <game>/data
    if data.parent.parent.name.lower() == "mods":
        van = animpack.for_data(data.parent.parent.parent / "data")
        if van is not None and van.skels is not None:
            return van, "vanilla"
    return None, ""


def _summary(packs: animpack.Packs, fid, entry: animpack.PackEntry) -> dict:
    """The index record's counts and the entry's eight summary floats, which
    are its last 40 bytes but the mask."""
    fid.seek(entry.offset + entry.size - 40)
    s = struct.unpack("<8f", fid.read(32))
    return {"frames": entry.frames, "duration": round(s[0], 3), "distance": round(s[1], 3),
            "speed": round(s[5], 3)}


def _truly_loose(p: Path) -> bool:
    """A loose ``.cas``, not an unpacked pack entry left under a ``.cas`` name
    (DaC has 11 568 of those, byte for byte what the pack holds, so reading
    the pack is the same and needs no unpacked skeleton). Five bytes and the
    size tell them apart."""
    try:
        size = p.stat().st_size
        with open(p, "rb") as f:
            head = f.read(5)
    except OSError:
        return False
    if len(head) < 5:
        return False
    nf, nq, npb = struct.unpack("<HHB", head)
    return not (nf and nq and size == animpack.anim_size(nf, nq, npb))


def _deg(v: int) -> float:
    return round(v * 180.0 / 32768, 1)


def skeleton_view(data_dir, name: str, packs: Optional[animpack.Packs],
                  loose: Optional[dict] = None) -> dict:
    """One skeleton's actions, a row per filled slot."""
    sk = packs.skeleton(name) if packs is not None else None
    if sk is None:
        return {"skeleton": name, "packed": False}
    root = Path(data_dir)
    loose = casanim.loose_index(root) if loose is None else loose
    rows = []
    with open(packs.anims.dat_path, "rb") as fid:
        for i, s in sk.filled():
            label = skelslots.label(i)
            first = (skelslots.names(i) or ("",))[0]
            row = {"slot": i, "action": label, "family": skelslots.family(first) if first else "other",
                   "path": s.path, "file": s.path.replace("\\", "/").rsplit("/", 1)[-1],
                   "impact_frame": s.impact_frame, "turn": [_deg(s.min_turn), _deg(s.max_turn)],
                   "events": [{"type": EVENT_TYPES.get(e.type, str(e.type)), "name": e.name,
                               "start": e.start, "end": e.end} for e in s.events]}
            entry = packs.anims.first(s.path) if packs.anims is not None else None
            if entry is not None:
                row.update(_summary(packs, fid, entry))
            hit, _how = casanim.find(root, s.path, loose)
            if hit is not None and _truly_loose(hit):
                row["rel"] = hit.relative_to(root).as_posix()
            row["playable"] = entry is not None or "rel" in row
            rows.append(row)
    return {"skeleton": name, "packed": True, "bones": len(sk.bones),
            "speeds": [round(v, 3) for v in sk.speeds], "actions": rows,
            "playable": sum(1 for r in rows if r["playable"])}


def entry_view(data_dir, entry) -> dict:
    """What the viewer's picker offers for a modeldb entry: its skeleton sets,
    and each skeleton's actions once."""
    sets = [{"mount": a.mount_type, "primary": a.primary_skeleton,
             "secondary": a.secondary_skeleton,
             "primary_weapons": list(a.pri_weapons), "secondary_weapons": list(a.sec_weapons)}
            for a in entry.animations]
    return sets_view(data_dir, sets)


def sets_view(data_dir, sets: List[dict]) -> dict:
    """The picker for any list of skeleton sets: each skeleton's actions once,
    the weapon skeletons' included."""
    packs, whose = packs_for(data_dir)
    names: List[str] = []
    for st in sets:
        for n in [st.get("primary"), st.get("secondary")] + list(st.get("primary_weapons") or []) \
                + list(st.get("secondary_weapons") or []):
            if n and n.lower() not in {x.lower() for x in names}:
                names.append(n)
    loose = casanim.loose_index(data_dir) if Path(data_dir).is_dir() else {}
    skels = {n.lower(): skeleton_view(data_dir, n, packs, loose) for n in names}
    # a skeleton the packs have not got: Phase 55's chain, loose files only
    missing = [n for n in names if not skels[n.lower()]["packed"]]
    if missing:
        old = {s["skeleton"].lower(): s for s in casanim.actions_view(data_dir, missing)["skeletons"]}
        for n in missing:
            o = old.get(n.lower(), {})
            skels[n.lower()].update(text_only=True, found=o.get("found", False),
                                    actions=[{"action": x["action"], "file": x["file"],
                                              "rel": x["rel"], "playable": bool(x["rel"]),
                                              "family": skelslots.family(x["action"])}
                                             for x in o.get("actions", [])])
    return {"packs": whose, "sets": sets, "skeletons": skels,
            "families": [{"id": f, "label": label} for f, label, _rx in skelslots.FAMILIES]}


def read(data_dir, skeleton: str, path: str = "", rel: str = "",
         weapons: Sequence[str] = (), slot: Optional[int] = None) -> casanim.Animation:
    """One action's keys: the loose file ``rel`` under ``data/`` when given,
    else the pack entry ``path`` with its packed skeleton's bones; with the
    ``weapons`` skeletons' bones added for ``slot`` (:func:`add_weapons`)."""
    root = Path(data_dir)
    if rel:
        anim = casanim.read_anim(root / rel, skeleton, root)
    else:
        packs, _whose = packs_for(root)
        if packs is None or packs.anims is None:
            raise casanim.AnimError("this mod has no animation pack, and vanilla's was not found")
        sk = packs.skeleton(skeleton)
        if sk is None:
            raise casanim.AnimError(f"the skeleton pack has no {skeleton!r}")
        data = packs.animation_bytes(path)
        if data is None:
            raise casanim.AnimError(f"pack.idx has no {path!r}")
        anim = casanim.read_packed_bytes(data, path, sk.bone_table(), skeleton)
    anim.weapons = add_weapons(root, anim, weapons, slot) if weapons else []
    return anim


# ---------------------------------------------------------------------------
# 80b: the weapon skeletons


def weapon_slot(ws: animpack.PackedSkeleton, slot: Optional[int]) -> Optional[int]:
    """Which of a weapon skeleton's slots plays with the body's ``slot``: the
    same slot when it is filled, else ``default``, else its first filled one.
    (Read off the files, not proven in game: a weapon skeleton fills a handful
    of slots, ``default`` always, and the bow's its draw, hold and release.)"""
    if slot is not None and 0 <= slot < len(ws.slots) and ws.slots[slot] is not None:
        return slot
    if ws.slots[DEFAULT_SLOT] is not None:
        return DEFAULT_SLOT
    filled = ws.filled()
    return filled[0][0] if filled else None


def add_weapons(data_dir, anim: casanim.Animation, weapons: Sequence[str],
                slot: Optional[int]) -> List[dict]:
    """Hang each weapon skeleton's bones under the body's, keyed on the body's
    key times, and say what was done with each.

    A weapon skeleton's first bone is a hand (or the torso, an elbow) and is
    not added: the body already has it, and its place is the body's. Every
    bone after it is added under that bone of the body, keyed from the weapon
    action, looped where the weapon action is shorter (a ``default`` is often
    one frame). A bone the body already has is left to the body, so a second
    weapon skeleton naming ``bone_weapon01`` does not fight the first."""
    packs, _whose = packs_for(data_dir)
    if packs is None or packs.anims is None:
        return [{"skeleton": w, "error": "no skeleton pack"} for w in weapons if w]
    report: List[dict] = []
    have = {t.name.lower(): i for i, t in enumerate(anim.tracks)}
    times = list(anim.key_times) or [0.0]
    for w in weapons:
        if not w:
            continue
        ws = packs.skeleton(w)
        if ws is None:
            report.append({"skeleton": w, "error": "not in the skeleton pack"})
            continue
        at = weapon_slot(ws, slot)
        if at is None:
            report.append({"skeleton": w, "error": "fills no slot"})
            continue
        path = ws.slots[at].path
        data = packs.animation_bytes(path)
        if data is None:
            report.append({"skeleton": w, "error": f"pack.idx has no {path!r}"})
            continue
        try:
            wa = casanim.read_packed_bytes(data, path, ws.bone_table(), w)
        except casanim.AnimError as exc:
            report.append({"skeleton": w, "error": str(exc)})
            continue
        # wa.tracks: 0 the Scene Root, 1 the weapon skeleton's root, then its bones
        if len(wa.tracks) < 3:
            report.append({"skeleton": w, "error": "has no bone past its root"})
            continue
        root = wa.tracks[1].name
        if root.lower() not in have:
            report.append({"skeleton": w, "error": f"hangs off {root}, which the body has not got"})
            continue
        into = {1: have[root.lower()]}
        samples = [casanim.sample(wa, t) for t in times]
        added = []
        for i in range(2, len(wa.tracks)):
            t = wa.tracks[i]
            if t.name.lower() in have:
                into[i] = have[t.name.lower()]
                continue
            tr = casanim.Track(t.name, into.get(t.parent, into[1]), t.pivot)
            for smp in samples:
                tr.rot.extend(smp[i]["rot"])
                tr.pos.extend(p - q for p, q in zip(smp[i]["pos"], t.pivot))
            into[i] = len(anim.tracks)
            have[t.name.lower()] = len(anim.tracks)
            anim.tracks.append(tr)
            added.append(t.name)
        report.append({"skeleton": w, "slot": at, "action": skelslots.label(at),
                       "path": path, "hangs_off": root, "bones": added})
    return report


# ---------------------------------------------------------------------------
# 80b: the mount


_NUM = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def rider_offset(raw: str) -> Optional[List[float]]:
    """The first ``rider_offset x, y, z`` of a descr_mount.txt block (an
    elephant lists one per rider, and the first is the driver's)."""
    for line in raw.splitlines():
        line = line.split(";", 1)[0].strip()
        if line.lower().startswith("rider_offset"):
            nums = _NUM.findall(line[len("rider_offset"):])
            if len(nums) >= 3:
                return [float(x) for x in nums[:3]]
    return None


def mounts_for(mod, entry) -> dict:
    """The mounts a rider entry can be shown on: first those its own units ride
    (EDU ``soldier`` this entry, ``mount`` that type), then every other mount
    of the class its skeleton sets are for. Each with its modeldb entry, its
    skeleton and its ``rider_offset``."""
    riders = [a for a in entry.animations if (a.mount_type or "none").lower() != "none"]
    if not riders:
        return {"mounts": [], "classes": []}
    classes = {a.mount_type.lower() for a in riders}
    me = entry.name.lower()
    ridden = {}
    for u in mod.edu.units:
        if (u.soldier_model or "").lower() == me and u.mount:
            ridden.setdefault(u.mount.lower(), []).append(u.type)
    db = mod.modeldb.by_name()
    rows = []
    for m in mod.mount_file.mounts:
        units = ridden.get(m.type.lower(), [])
        if not units and (m.mount_class or "").lower() not in classes:
            continue
        model = db.get((m.model or "").lower())
        if model is None:
            continue
        off = rider_offset(m.raw)
        skel = next((a.primary_skeleton for a in model.animations if a.primary_skeleton), "")
        rows.append({"type": m.type, "class": m.mount_class, "entry": model.name,
                     "skeleton": skel, "offset": off or [0.0, 0.0, 0.0],
                     "offset_given": off is not None, "units": units})
    rows.sort(key=lambda r: (not r["units"], r["type"].lower()))
    return {"mounts": rows, "classes": sorted(classes)}


# ---------------------------------------------------------------------------
# 80b: a .cas model


def _norm(p: str) -> str:
    p = p.replace("\\", "/").lower().lstrip("/")
    return p[5:] if p.startswith("data/") else p


def cas_view(mod, rel: str) -> dict:
    """The picker for a strat ``.cas``: the skeleton each descr_model_strat.txt
    entry that draws it names, one set each. With none, every ``strat_``
    skeleton in the pack is offered, and the view says it is a guess."""
    key = _norm(rel)
    sets, seen = [], set()
    try:
        entries = mod.strat_models.entries
    except Exception:           # a mod with no descr_model_strat.txt, or one that will not parse
        entries = []
    for e in entries:
        if e.skeleton and e.skeleton.lower() not in seen and any(_norm(p) == key for p in e.models):
            seen.add(e.skeleton.lower())
            sets.append({"mount": "none", "primary": e.skeleton, "secondary": "",
                         "primary_weapons": [], "secondary_weapons": [], "entry": e.name})
    guessed = False
    if not sets:
        packs, _whose = packs_for(mod.data)
        names = [n for n in (packs.skeleton_names() if packs else []) if n.lower().startswith("strat_")]
        sets = [{"mount": "none", "primary": n, "secondary": "", "primary_weapons": [],
                 "secondary_weapons": [], "entry": ""} for n in names]
        guessed = bool(sets)
    out = sets_view(mod.data, sets)
    out["guessed"] = guessed
    return out


# ---------------------------------------------------------------------------
# 80b: side by side


def compare(here_dir, there_dir, skeleton: str, slot: int) -> dict:
    """The same skeleton's ``slot`` in another mod: whether it has that
    skeleton and that slot, the path it plays there, and whether the two
    animations and the two skeletons' bones are the same bytes."""
    pa, _w = packs_for(here_dir)
    pb, whose = packs_for(there_dir)
    a = pa.skeleton(skeleton) if pa else None
    b = pb.skeleton(skeleton) if pb else None
    out = {"skeleton": skeleton, "slot": slot, "action": skelslots.label(slot),
           "packs": whose, "has_skeleton": b is not None}
    if b is None:
        return out
    out["same_bones"] = a is not None and [x.to_bytes() for x in a.bones] == [x.to_bytes() for x in b.bones]
    sa = a.slots[slot] if a is not None and 0 <= slot < len(a.slots) else None
    sb = b.slots[slot] if 0 <= slot < len(b.slots) else None
    out["has_slot"] = sb is not None
    if sb is None:
        return out
    out["path"] = sb.path
    out["same_path"] = sa is not None and sa.path.lower() == sb.path.lower()
    da = pa.animation_bytes(sa.path) if sa is not None and pa.anims is not None else None
    db = pb.animation_bytes(sb.path) if pb.anims is not None else None
    out["playable"] = db is not None
    out["same_bytes"] = da is not None and da == db
    entry = pb.anims.first(sb.path) if pb.anims is not None else None
    if entry is not None:
        with open(pb.anims.dat_path, "rb") as fid:
            out.update(_summary(pb, fid, entry))
    return out
