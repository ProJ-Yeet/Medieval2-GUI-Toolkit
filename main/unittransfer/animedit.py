"""Edit a battle animation and save it: M16's editor half (Phase 57a).

The reference tool's ``AnimationEditor`` edits a bone's rotation per frame as
Euler angles and scales the translation data, "useful for fitting
non-standard skeletons (e.g. dwarves)", then writes a new ``.cas``. This is
that, over :func:`unittransfer.casanim.write_anim`, which writes every one of
the 1 751 loose animation files on the installed mods back byte for byte - so
an edit changes what it says it changes and nothing else.

The edits, applied in this order whatever order they are given in::

    keys      [{bone, key, euler}]    set a bone's rotation at one key outright,
                                      the key numbered as the file has it
    trim      [first key, last key]   keep that stretch; its times start at 0
    speed     2.0                     play in half the time (times / speed)
    in_place  true                    take a cycle's travel out of the pelvis
    scale     [sx, sy, sz]            every pivot and position key, per axis
    offsets   [{bone, euler}]         turn a bone by [x, y, z] degrees at every key

Angles are degrees about the bone's own X, then Y, then Z. A bone that had no
rotation keys gets one; a bone with one key that is set at a later key is
given every key first, holding the one it had, which is what the game did
with it anyway.

**What saving does, and does not, reach.** The game plays a mod's animations
from ``data/animations/pack.dat`` (``pack.idx`` lists what is in it); DaC and
ROCSS both ship one beside their loose files. A loose file this writes reaches
the game once the pack is rebuilt - the TWCenter archive carries the tool,
``xidx.exe -caf pack.idx < anim_list.txt``. Every screen that saves says so.
"""
from __future__ import annotations

import copy
import math
import re
import shutil
import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import casanim

REPACK_NOTE = (
    "The game plays this mod's animations from animations/pack.dat. A loose "
    "file reaches the game once that pack is rebuilt - the TWCenter archive's "
    "xidx does it: xidx.exe -caf pack.idx < anim_list.txt, in data/animations.")


class EditError(ValueError):
    pass


# ---------------------------------------------------------------------------
# angles


def quat_from_euler(deg) -> Tuple[float, float, float, float]:
    """``[x, y, z]`` degrees -> ``(x, y, z, w)``: X first, then Y, then Z."""
    hx, hy, hz = (math.radians(float(v)) / 2 for v in deg)
    cx, sx = math.cos(hx), math.sin(hx)
    cy, sy = math.cos(hy), math.sin(hy)
    cz, sz = math.cos(hz), math.sin(hz)
    return (sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz)


def euler_from_quat(q) -> List[float]:
    """The inverse of :func:`quat_from_euler`, in degrees."""
    x, y, z, w = _norm(q)
    ex = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    sy = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    ey = math.asin(sy)
    ez = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return [round(math.degrees(v), 4) for v in (ex, ey, ez)]


def _norm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


# ---------------------------------------------------------------------------
# the edits


def _track(anim: casanim.Animation, name: str) -> casanim.Track:
    low = str(name or "").lower()
    for t in anim.tracks:
        if t.name.lower() == low:
            return t
    raise EditError(f"this animation has no bone called {name!r}")


def _hub(anim: casanim.Animation) -> Optional[casanim.Track]:
    return next((t for t in anim.tracks if t.parent == 0), None)


def _full(t: casanim.Track, keys: int, what: str) -> None:
    """Give a track every key, holding its last - the game's own reading."""
    width = 4 if what == "rot" else 3
    arr = getattr(t, what)
    have = len(arr) // width
    if have == keys:
        return
    if have == 0:
        last = [0.0, 0.0, 0.0, 1.0] if what == "rot" else [0.0, 0.0, 0.0]
    else:
        last = list(arr[(have - 1) * width:have * width])
    grown = array("f", arr)
    for _ in range(keys - have):
        grown.extend(last)
    setattr(t, what, grown)


def apply_edits(anim: casanim.Animation, edits: Optional[Dict]) -> casanim.Animation:
    """A copy of ``anim`` with ``edits`` done to it; ``anim`` is left alone."""
    a = copy.deepcopy(anim)
    e = edits or {}
    keys = len(a.key_times)

    for kv in e.get("keys") or []:
        t = _track(a, kv.get("bone"))
        k = int(kv.get("key", 0))
        if not 0 <= k < keys:
            raise EditError(f"key {k} is not one of this animation's 0 to {keys - 1}")
        if t.rot_keys <= k or (t.rot_keys == 1 and keys > 1):
            _full(t, keys, "rot")
        t.rot[k * 4:k * 4 + 4] = array("f", quat_from_euler(kv.get("euler") or (0, 0, 0)))

    trim = e.get("trim")
    if trim:
        lo, hi = int(trim[0]), int(trim[1])
        if not 0 <= lo < hi < keys:
            raise EditError(f"keep keys {lo} to {hi}: this animation has keys 0 to {keys - 1}")
        t0 = a.key_times[lo]
        a.key_times = array("f", [t - t0 for t in a.key_times[lo:hi + 1]])
        for t in a.tracks:
            for what, width in (("rot", 4), ("pos", 3)):
                arr = getattr(t, what)
                have = len(arr) // width
                if have > 1:
                    # a short track (the 3.02 engines) holds its last key past its end
                    _full(t, keys, what)
                    arr = getattr(t, what)
                    setattr(t, what, array("f", arr[lo * width:(hi + 1) * width]))
        keys = hi - lo + 1
        a.length = a.key_times[-1]

    speed = e.get("speed")
    if speed not in (None, "", 1, 1.0):
        sp = float(speed)
        if not 0.05 <= sp <= 20:
            raise EditError(f"a speed of {sp:g} is outside 0.05 to 20")
        a.key_times = array("f", [t / sp for t in a.key_times])
        a.length = a.length / sp

    if e.get("in_place"):
        hub = _hub(a)
        if hub is not None and hub.pos_keys > 1:
            _full(hub, keys, "pos")
            first, last = hub.pos[0:3], hub.pos[(keys - 1) * 3:keys * 3]
            end = a.key_times[-1] or 1.0
            for k in range(keys):
                f = a.key_times[k] / end
                hub.pos[k * 3] -= (last[0] - first[0]) * f
                hub.pos[k * 3 + 2] -= (last[2] - first[2]) * f

    scale = e.get("scale")
    if scale:
        sx, sy, sz = (float(v) for v in scale)
        for t in a.tracks:
            t.pivot = (t.pivot[0] * sx, t.pivot[1] * sy, t.pivot[2] * sz)
            for k in range(t.pos_keys):
                t.pos[k * 3] *= sx
                t.pos[k * 3 + 1] *= sy
                t.pos[k * 3 + 2] *= sz

    for off in e.get("offsets") or []:
        t = _track(a, off.get("bone"))
        d = quat_from_euler(off.get("euler") or (0, 0, 0))
        if t.rot_keys == 0:
            t.rot = array("f", [0.0, 0.0, 0.0, 1.0])
        for k in range(t.rot_keys):
            q = _qmul(tuple(t.rot[k * 4:k * 4 + 4]), d)
            t.rot[k * 4:k * 4 + 4] = array("f", _norm(q))

    return a


def view(anim: casanim.Animation) -> dict:
    """What the page plays and edits: :meth:`Animation.view` and, per bone,
    each rotation key as Euler degrees for the key editor."""
    out = anim.view()
    for b, t in zip(out["bones"], anim.tracks):
        b["euler"] = [euler_from_quat(t.rot[i:i + 4]) for i in range(0, len(t.rot), 4)]
    out["notes"] = list(anim.notes)
    out["keys"] = len(anim.key_times)
    return out


# ---------------------------------------------------------------------------
# saving


@dataclass
class SavePlan:
    mod: object = None
    rel: str = ""                       # the file edited
    target: str = ""                    # where it is written, relative to data/
    data: bytes = b""
    skeleton_edit: Optional[Tuple[str, str]] = None   # (rel, new text) of descr_skeleton.txt
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {"rel": self.rel, "target": self.target, "bytes": len(self.data),
                "overwrites": self.overwrites, "assigns": bool(self.skeleton_edit),
                "errors": list(self.errors), "notes": list(self.notes),
                "ok": not self.errors and bool(self.data)}

    @property
    def overwrites(self) -> bool:
        return bool(self.mod) and (Path(self.mod.data) / self.target).is_file()


_SAFE = re.compile(r"^[A-Za-z0-9_.\- /]+$")


def plan_save(mod, rel: str, edits: Optional[Dict], save_as: str = "",
              assign: Optional[Dict] = None, skeleton: str = "") -> SavePlan:
    """Work out one save: the edited file's bytes and, when ``assign`` names a
    skeleton and an action, that action's line in ``descr_skeleton.txt``
    pointed at it.

    ``skeleton`` is for an animation from the pack (an unpacked ``pack.dat``
    entry), which is read with that skeleton's bones. What is written is
    always a loose ``.cas``, so such a file is never saved over: the tree it is
    in is the pack's own format, and a packer reading it back expects that."""
    from . import factions
    p = SavePlan(mod=mod, rel=rel)
    src = factions.picture_path(mod, rel)
    if src is None or not src.is_file():
        p.errors.append(f"{rel!r} is not a file in this mod")
        return p
    try:
        anim = casanim.read_anim(src, skeleton, mod.data)
        p.data = casanim.write_anim(apply_edits(anim, edits))
    except (casanim.AnimError, EditError, ValueError, TypeError) as exc:
        p.errors.append(str(exc))
        return p
    target = (save_as or rel).strip().replace("\\", "/").lstrip("/")
    if not target.lower().endswith(".cas"):
        target += ".cas"
    if casanim.packed_counts(src.read_bytes()) is not None \
            and target.lower() == rel.strip().replace("\\", "/").lstrip("/").lower():
        p.errors.append(f"{src.name} is an animation from the pack: the save is a loose .cas, "
                        "so it goes beside it under a name of its own, not over it")
        return p
    if (not target.lower().startswith("animations/") or ".." in target
            or not _SAFE.match(target)):
        p.errors.append(f"{target!r}: an animation is saved under animations/, "
                        f"named with letters, digits, _ . - and /")
        return p
    p.target = target
    if p.overwrites and target.lower() != rel.lower():
        p.errors.append(f"{target} is already a file in this mod; pick another name "
                        f"or save over the one you opened")
    if assign and assign.get("skeleton") and assign.get("action"):
        edit = _assign(mod, str(assign["skeleton"]), str(assign["action"]), target)
        if isinstance(edit, str):
            p.errors.append(edit)
        else:
            p.skeleton_edit = edit
            p.notes.append(f"descr_skeleton.txt: {assign['skeleton']}'s "
                           f"{assign['action']} is pointed at {target}")
    p.notes.append(REPACK_NOTE)
    return p


def _assign(mod, skeleton: str, action: str, target: str):
    """``descr_skeleton.txt`` with one ``anim`` line pointed at ``target``, or a
    sentence saying why not. Only the path is replaced: the flags after it
    (``-fr``, ``-evt:``) and the file's spacing and line endings stay. The new
    path keeps whatever the old one had before ``data/`` - DaC's name another
    mod's folder for every file, and the game resolves them all the same."""
    path = Path(mod.data) / "descr_skeleton.txt"
    if not path.is_file():
        return "this mod has no descr_skeleton.txt to point at the file"
    text = path.read_bytes().decode("latin-1")
    rx_type = re.compile(r"^[ \t]*type[ \t]+(\S+)", re.M | re.I)
    starts = [(m.start(), m.group(1)) for m in rx_type.finditer(text)]
    span = None
    for i, (at, name) in enumerate(starts):
        if name.lower() == skeleton.lower():
            span = (at, starts[i + 1][0] if i + 1 < len(starts) else len(text))
            break
    if span is None:
        return f"descr_skeleton.txt has no type {skeleton}"
    block = text[span[0]:span[1]]
    rx = re.compile(r"^([ \t]*anim[ \t]+" + re.escape(action) + r"[ \t]+)(\S+)", re.M | re.I)
    m = rx.search(block)
    if m is None:
        return f"{skeleton} has no {action} line in descr_skeleton.txt"
    old = m.group(2)
    at = old.lower().find("data/")
    new_path = (old[:at] if at >= 0 else "") + "data/" + target
    block = block[:m.start(2)] + new_path + block[m.end(2):]
    return ("descr_skeleton.txt", text[:span[0]] + block + text[span[1]:])


def apply_save(p: SavePlan) -> Dict:
    """Write a planned save, backed up and undoable like every other job."""
    from . import config
    from .logutil import file_op, log

    if p.errors or not p.data:
        raise ValueError("cannot save: " + ("; ".join(p.errors) or "nothing planned"))
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
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    out_path = keep(p.target)
    out_path.write_bytes(p.data)
    file_op("WRITE", out_path, f"{len(p.data)} bytes (animation)")
    files = [p.target]
    if p.skeleton_edit:
        rel, text = p.skeleton_edit
        sk = keep(rel)
        sk.write_bytes(text.encode("latin-1"))
        file_op("WRITE", sk, f"{len(text)} bytes")
        files.append(rel)
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "models", "action": "animation",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.target, "resolved_type": p.target,
        "options": {"from": p.rel},
        "applied": True, "undone": False, "note": "",
        "summary": f"animation {p.rel} -> {p.target} in {mod.name}",
        "warnings": [], "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("ANIM   %s -> %s in %s, id=%s", p.rel, p.target, mod.name, tid)
    return {"id": tid, "files": files, "target": p.target, "notes": list(p.notes),
            "record": rec}
