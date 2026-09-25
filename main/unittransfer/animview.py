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
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Optional, Tuple

from . import animpack, casanim, skelslots

#: An event's type, as descr_skeleton.txt's event files use them.
EVENT_TYPES = {1: "sound", 2: "sound bank", 3: "shockwave", 4: "voice", 5: "ambient"}


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
    packs, whose = packs_for(data_dir)
    sets, names = [], []
    for a in entry.animations:
        sets.append({"mount": a.mount_type, "primary": a.primary_skeleton,
                     "secondary": a.secondary_skeleton,
                     "primary_weapons": list(a.pri_weapons), "secondary_weapons": list(a.sec_weapons)})
        for n in a.skeletons() + a.weapon_skeletons():
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


def read(data_dir, skeleton: str, path: str = "", rel: str = "") -> casanim.Animation:
    """One action's keys: the loose file ``rel`` under ``data/`` when given,
    else the pack entry ``path`` with its packed skeleton's bones."""
    root = Path(data_dir)
    if rel:
        return casanim.read_anim(root / rel, skeleton, root)
    packs, _whose = packs_for(root)
    if packs is None or packs.anims is None:
        raise casanim.AnimError("this mod has no animation pack, and vanilla's was not found")
    sk = packs.skeleton(skeleton)
    if sk is None:
        raise casanim.AnimError(f"the skeleton pack has no {skeleton!r}")
    data = packs.animation_bytes(path)
    if data is None:
        raise casanim.AnimError(f"pack.idx has no {path!r}")
    return casanim.read_packed_bytes(data, path, sk.bone_table(), skeleton)
