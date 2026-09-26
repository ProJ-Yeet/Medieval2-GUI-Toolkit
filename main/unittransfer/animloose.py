r"""Keep a ported mod rebuildable: loose ``.cas`` files and ``descr_skeleton.txt`` (Phase 84).

Phase 83 brings a unit's animations into the destination's packs and nothing
else. That is all the game needs to play them. It is not all the game needs to
**rebuild** the packs, which it does from ``descr_skeleton.txt`` and the loose
``.cas`` files that text names, and a rebuild that meets one missing file stops
loading the animations altogether. So this module writes, for what a port
appended and only for that, what a rebuild would read:

* each animation a ported skeleton plays, as a loose ``.cas`` at the path its
  slot names, when no file is there yet;
* a ``type`` block per skeleton the port added, rendered from the packed
  skeleton itself (the packs are the truth), with its combat settings taken
  from the source's own text where it has a block for that skeleton;
* an ``.evt`` file per slot that carries sound or effect cues.

When the engine rebuilds
------------------------
It loads the mod's four pack files if all four are there and each loads: the
magic, the version (a skeleton pack's includes the ``Version`` line of
``descr_skeleton.txt``) and **the same entry count in the ``.idx`` and the
``.dat`` headers**. If the mod's packs fail it tries vanilla's, and only when
those fail too does it read ``descr_skeleton.txt`` and write new packs into the
mod's ``data/animations``. The file's age plays no part, so a block appended
here never sets a rebuild off on its own: the ``Version`` line is left as it
is. (The working model for Phase 82's questions 2 and 4; the in-game kits
confirm it.)

Where a loose file goes
-----------------------
A path in an ``anim`` line is looked up under the mod's ``data/`` first and then
from the game folder. A path under this mod's own folder
(``mods/<dest>/data/animations/...``) is written where it says; any other
(``mods/Third_Age_3/data/animations/...``, which is every DaC path) is written
under the mod's ``data/`` with the whole path kept, so it is found first and
nothing is ever written outside the destination mod.

From a pack entry to a ``.cas``, and back
-----------------------------------------
A pack entry is what the engine made of a ``.cas``: each bone's rotation keys as
they were, the moving bones' positions plus their pivot times the skeleton's
scale, and the pelvis's path through the world as the "root offsets". The
loose file written here puts back the rotations, the positions less the pivot
over the scale, and the pelvis keyed along its root offsets (what an exported
walk carries); its pivots are the packed skeleton's bones over the scale, which
is what the engine builds a skeleton from when the file is the first a type
names. :func:`to_packed` is the engine's own reading of a ``.cas`` into a pack
entry, and ``tests/test_animloose.py`` holds that a file written here packs
back to the entry it came from on every installed animation.
"""
from __future__ import annotations

import math
import re
import struct
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import animpack, casanim, skelslots

#: Seconds a packed frame lasts, and the battle AI's ticks a second: every
#: installed entry's duration is (frames - 1) * 0.05, and its AI speed a tenth
#: of its speed.
FRAME_TIME = 0.05
AI_FPS = 10.0

#: The header a written file opens with, from 3ds Max's exporter: version 3.2,
#: 38, 9, 0, the length (set per file), then the scene's colours, as the
#: exported siege files carry them. Only the version and length are read back.
_HEAD = (struct.pack("<fIIIf", 3.2, 38, 9, 0, 0.0)
         + bytes.fromhex("010000000000000000000001000000000000006666660000000000000000"))

#: The engine's defaults for a line with no ``-mintd``/``-maxtd`` (10 and 179
#: degrees, as its int16 angle), ``-prob`` and ``-ld``.
MIN_TURN_DEFAULT = round(math.radians(10) * 32768 / math.pi)
MAX_TURN_DEFAULT = round(math.radians(179) * 32768 / math.pi)
PROB_DEFAULT = 50
#: ``evade_parry``: 0 blocks, 1 evades, 2 parries.
DEFENCE = {1: "-evade", 2: "-parry"}
#: An event's type number, as ``.evt`` files spell it.
EVENT_TYPES = {1: "SOUND", 2: "SOUND_BANK", 3: "SHOCKWAVE", 4: "SOUND_VOICE",
               5: "SOUND_AMBIENT", 6: "DETACH", 7: "ATTACH"}
#: The two slots the engine takes the climb's rise out of.
Y_COMPENSATED = ("climb_up", "climb_down")
DEFAULT_SLOT = animpack.SKELETON_SLOTS - 1


class LooseError(ValueError):
    pass


# ---------------------------------------------------------------------------
# one animation: pack entry -> .cas, and the engine's .cas -> pack entry

def to_cas(data: bytes, bones: List[Tuple[str, int, tuple]], scale: float,
           source: str = "", bone_scale: Optional[float] = None) -> casanim.Animation:
    """A pack entry as the loose animation the engine would pack back into it.

    ``scale`` is the entry's own (its index record's), which its positions
    are times; ``bones`` are the packed skeleton's (name, parent, position),
    positions times ``bone_scale``, the skeleton's (default ``scale``). They
    differ when a mod's pack was put together by hand: DaC's crew animations
    are packed at 0.89 and played by skeletons at 1.0, which the engine
    rescales at load, and a rebuild at the skeleton's scale does the same. The
    file keeps only the first ``nq`` bones, since the engine counts its nodes."""
    a = animpack.PackedAnimation(data, source)
    nf, nq, npb = a.frames, a.rot_bones, a.pos_bones
    if len(bones) < nq:
        raise LooseError(f"{Path(source).name or 'animation'} turns {nq} bones and its "
                         f"skeleton has {len(bones)}")
    s = scale or 1.0
    bs = (bone_scale if bone_scale is not None else scale) or 1.0
    moving = a.moving
    out = casanim.Animation(source=source, version=3.2, length=(nf - 1) * FRAME_TIME,
                            key_times=array("f", [f * FRAME_TIME for f in range(nf)]),
                            layout=(2, True), head=_HEAD, tail=None)
    out.tracks.append(casanim.Track("Scene Root", -1, (0.0, 0.0, 0.0)))
    for b in range(nq):
        name, parent, pos = bones[b]
        pivot = tuple(float(v) / bs for v in pos)
        par = parent + 1 if 0 <= parent < b else 0
        t = casanim.Track(name, par, pivot)
        for f in range(nf):
            at = (f * nq + b) * 4
            t.rot.extend(a.rotations[at:at + 4])
        if b == 0:
            src, stride, at = a.control, 3, 0
        elif b in moving:
            src, stride, at = a.positions, npb * 3, moving.index(b) * 3
        else:
            src = None
        if src is not None:
            px, py, pz = pivot
            for f in range(nf):
                x, y, z = src[f * stride + at:f * stride + at + 3]
                t.pos.extend((x / s - px, y / s - py, z / s - pz))
        out.tracks.append(t)
    return out


def cas_bytes(data: bytes, bones, scale: float, source: str = "",
              bone_scale: Optional[float] = None) -> bytes:
    return casanim.write_anim(to_cas(data, bones, scale, source, bone_scale))


def _div(a: float, b: float) -> float:
    if b:
        return a / b
    return math.nan if a == 0 or math.isnan(a) else math.copysign(math.inf, a)


def to_packed(anim: casanim.Animation, scale: float, generate_deltas: bool = True,
              y_compensate: bool = False, rescaled: bool = False) -> bytes:
    """The pack entry the engine makes of a loose animation: what a rebuild
    writes. ``generate_deltas`` is off for the ``default`` slot and for a type
    marked ``no_deltas``; ``y_compensate`` is on for the two climbs.
    ``rescaled`` works out the distance still to travel as the engine does
    when it makes an entry at a second scale out of the first, without zeroing
    an offset under a millimetre: 47 of DaC's crew entries were made so."""
    nodes = anim.tracks[1:]
    nq = len(nodes)
    nf = len(anim.key_times)
    if not nf % 2:
        nf -= 1
    if nf < 1 or not nq:
        raise LooseError(f"{Path(anim.source).name}: nothing to pack")
    root = nodes[0]
    base = root.pivot

    def tk(t, f):
        return t.pos[f * 3:f * 3 + 3]

    trans = [x for x, t in enumerate(nodes) if t.pos_keys or x == 0]
    delta_h = 0.0
    if generate_deltas and y_compensate and root.pos_keys:
        # scaled once more below, as the engine does; an entry rescaled from
        # one at scale 1 had its rise taken out at that scale
        delta_h = (tk(root, nf - 1)[1] - tk(root, 0)[1]) * (1.0 if rescaled else scale)
    ro, rk, tks = [], array("f"), array("f")
    for f in range(nf):
        interp = delta_h * f / (nf - 1) if nf > 1 else 0.0
        if root.pos_keys:
            ro.append(tuple((k + b) * scale for k, b in zip(tk(root, f), base)))
        else:
            ro.append(tuple(base))
        for t in nodes:
            rk.extend(t.rot[f * 4:f * 4 + 4] if t.rot_keys else (0.0, 0.0, 0.0, 1.0))
        for x in trans:
            t = nodes[x]
            if x == 0:
                if not t.pos_keys:
                    v = (0.0, t.pivot[1], 0.0) if generate_deltas else t.pivot
                elif generate_deltas:
                    v = (0.0, tk(t, f)[1] + t.pivot[1] - interp, 0.0)
                else:
                    v = tuple(k + b for k, b in zip(tk(t, f), t.pivot))
            else:
                v = tuple(k + b for k, b in zip(tk(t, f), t.pivot))
            tks.extend(c * scale for c in v)
    dp = tuple(e - s for e, s in zip(ro[-1], ro[0]))
    dist = math.hypot(dp[0], dp[2]) if dp[0] ** 2 + dp[2] ** 2 > 1e-6 else 0.0
    moves = array("f")
    for d in range(nf - 1):
        if generate_deltas:
            moves.extend((ro[d + 1][0] - ro[d][0], ro[d + 1][2] - ro[d][2]))
        else:
            moves.extend((0.0, 0.0))
    moves.extend((0.0, 0.0))
    dte = array("f")
    for r in ro:
        sq = r[0] ** 2 + r[2] ** 2
        travelled = math.sqrt(sq) if sq > 1e-6 or rescaled else 0.0
        dte.append(min(max(dist - travelled, 0.0), dist))
    length = (nf - 1) * FRAME_TIME
    speed = _div(dist, length)
    summary = array("f", [length, dist, *dp, speed, speed / AI_FPS, dist / nf])
    mask = sum(1 << x for x in trans)
    return (struct.pack("<HHB", nf, nq, len(trans)) + rk.tobytes() + tks.tobytes()
            + moves.tobytes() + dte.tobytes() + array("f", [c for r in ro for c in r]).tobytes()
            + summary.tobytes() + mask.to_bytes(8, "little"))


def floats_close(a: bytes, b: bytes, rel: float = 1e-4, abs_: float = 1e-5) -> bool:
    """Two pack entries the same to float precision: counts and mask exact."""
    if len(a) != len(b) or a[:5] != b[:5] or a[-8:] != b[-8:]:
        return False
    x, y = array("f", a[5:-8]), array("f", b[5:-8])
    for p, q in zip(x, y):
        if p == q or (math.isnan(p) and math.isnan(q)):
            continue
        if abs(p - q) > abs_ + rel * max(abs(p), abs(q)):
            return False
    return True


# ---------------------------------------------------------------------------
# one slot as an ``anim`` line, and its cues as an .evt file

def _num(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _degrees(tab: int) -> str:
    return _num(round(tab * 180.0 / 32768.0, 5))


def slot_flags(slot: animpack.Slot, frames: int, evt: str = "") -> List[str]:
    """The flags that make the engine rebuild ``slot`` as it is packed, in the
    order it reads them. A value at the engine's default is left out."""
    out: List[str] = []
    if slot.evade_parry in DEFENCE:
        out.append(DEFENCE[slot.evade_parry])
    if slot.probability != PROB_DEFAULT:
        out.append(f"-prob:{slot.probability}")
    if slot.delta_rot == 0:
        out.append("-fr")
    if not (tuple(slot.impact) == (0.0, 0.0, struct.unpack("<f", struct.pack("<f", 1.6))[0])
            and slot.delta_angle == 0 and slot.delta_length == 0):
        out.append("-id: " + ", ".join(_num(v) for v in slot.impact))
    if not (slot.impact_frame == frames >> 1 and slot.impact_dist == 0):
        out.append(f"-if:{slot.impact_frame}")
    if slot.min_turn != MIN_TURN_DEFAULT:
        out.append(f"-mintd:{_degrees(slot.min_turn)}")
    if slot.max_turn != MAX_TURN_DEFAULT:
        out.append(f"-maxtd:{_degrees(slot.max_turn)}")
    if tuple(round(v, 6) for v in slot.launch) != (0.0, 0.0, 1.0):
        out.append("-ld: " + ", ".join(_num(v) for v in slot.launch))
    if evt:
        out.append(f"-evt:{evt}")
    return out


def evt_text(events: List[animpack.Event]) -> str:
    lines = []
    for e in events:
        kind = EVENT_TYPES.get(e.type)
        if kind is None:
            continue
        words = ["event", kind, e.name, str(e.start), str(e.end)]
        if e.random:
            words.append("RANDOM")
        if e.looped:
            words.append("LOOPED")
        lines.append(" ".join(words))
    return "\n".join(lines) + ("\n" if lines else "")


_FLAG = re.compile(r"(?:(?<=\s)|^)-(evade|parry|prob|fr|id|if|mintd|maxtd|ld|evt)\b[:\s]*", re.I)


def read_flags(text: str) -> dict:
    """The flags of an ``anim`` line as the engine takes them (numbers only;
    ``evt`` is the path). For the tests: what :func:`slot_flags` wrote reads
    back as the slot."""
    out: dict = {}
    hits = list(_FLAG.finditer(text))
    for m, nxt in zip(hits, hits[1:] + [None]):
        k = m.group(1).lower()
        v = text[m.end():nxt.start() if nxt else len(text)].strip()
        nums = [float(x) for x in re.split(r"[,\s]+", v) if x] if k not in ("evt",) else []
        if k in ("evade", "parry"):
            out["defence"] = 1 if k == "evade" else 2
        elif k == "prob":
            out["prob"] = int(nums[0])
        elif k == "fr":
            out["fr"] = True
        elif k in ("id", "ld"):
            out[k] = tuple(nums[:3])
        elif k == "if":
            out["if"] = int(nums[0])
        elif k in ("mintd", "maxtd"):
            out[k] = int(round(math.radians(nums[0]) * 32768 / math.pi))
        elif k == "evt":
            out["evt"] = v.split()[0] if v else ""
    return out


# ---------------------------------------------------------------------------
# a type block

#: The lines of a source's type block kept for the destination's, in the order
#: the engine reads them. ``scale`` is written from the pack; ``parent``,
#: ``remove_attack_anims`` and ``reference_points`` are left out because every
#: slot is written out in full, with its impact point.
_HEADER_ORDER = ("suppress_refpoints_warning", "force_hit_positions_to_cylinder",
                 "variant_skeleton", "no_deltas")
_SCANNER = ("strike_directions", "strike_heights", "strike_distances", "in_awareness",
            "in_zone", "in_centre")


def type_header(data_dir, name: str) -> Optional[List[str]]:
    """The lines of ``name``'s block in a mod's ``descr_skeleton.txt`` before
    its first ``anim``, comments dropped, or None when it has no such block."""
    path = Path(data_dir) / "descr_skeleton.txt"
    if not path.is_file():
        return None
    want = name.lower()
    lines: Optional[List[str]] = None
    with open(path, encoding="latin-1") as fh:
        for raw in fh:
            w = raw.split(";", 1)[0].split()
            if not w:
                continue
            kw = w[0].lower()
            if lines is None:
                if kw == "type" and len(w) > 1 and w[1].lower() == want:
                    lines = []
                continue
            if kw in ("anim", "type"):
                break
            lines.append(" ".join(w))
    return lines


def _no_deltas(packs: animpack.Packs, skel: animpack.PackedSkeleton) -> bool:
    """Whether the type was built with ``no_deltas``: its pelvis keeps the
    walk's travel instead of zeroing it. Read off the first moving animation."""
    for i, s in skel.filled():
        if i == DEFAULT_SLOT:
            continue
        a = packs.animation(s.path)
        if a is None or not a.distance:
            continue
        xz = max(max(abs(a.positions[f * a.pos_bones * 3]), abs(a.positions[f * a.pos_bones * 3 + 2]))
                 for f in range(a.frames))
        return xz > 1e-6
    return False


def render_block(name: str, skel: animpack.PackedSkeleton, header: Optional[List[str]],
                 frames: Dict[str, int], evts: Dict[int, str], first: int,
                 no_deltas: bool, dest_skeletons=()) -> Tuple[str, List[str]]:
    """``(text, notes)``: one ``type`` block, every filled slot a line, the
    slot ``first`` first (the engine builds the skeleton's bones from the first
    file a type names). ``frames`` maps a lower-case path to its frame count."""
    notes: List[str] = []
    kept: Dict[str, List[str]] = {}
    for line in header or ():
        kw = line.split()[0].lower()
        if kw in _HEADER_ORDER or kw in _SCANNER or kw == "locomotion_table":
            if kw == "variant_skeleton":
                other = line.split()[1] if len(line.split()) > 1 else ""
                if other.lower() not in {d.lower() for d in dest_skeletons}:
                    notes.append(f"{name}: its variant skeleton {other} is not in the destination, "
                                 "so the line is left out")
                    continue
            kept.setdefault(kw, []).append(line)
    if header is None:
        notes.append(f"{name}: the source's descr_skeleton.txt has no block for it, so a rebuild "
                     "would give it the engine's default strike distances")
    if no_deltas and "no_deltas" not in kept:
        kept["no_deltas"] = ["no_deltas"]
    out = [f"type            {name}"]
    for kw in ("suppress_refpoints_warning",):
        out += kept.get(kw, [])
    if abs(skel.scale - 1.0) > 1e-6:
        out.append(f"scale           {_num(skel.scale)}")
    for kw in _HEADER_ORDER[1:]:
        out += kept.get(kw, [])
    for line in header or ():
        if line.split()[0].lower() in _SCANNER:
            out.append(line)
    out += kept.get("locomotion_table", [])
    out.append("")
    order = [first] + [i for i, _s in skel.filled() if i != first]
    for i in order:
        s = skel.slots[i]
        names = skelslots.names(i)
        if not names:
            notes.append(f"{name}: slot {i} has no name the engine takes, so it is not written")
            continue
        flags = slot_flags(s, frames.get(animpack._key(s.path), 0), evts.get(i, ""))
        out.append("\t\t".join(["anim", f"{names[0]:<32}", s.path] + (["\t".join(flags)] if flags else [])))
        if s.events and i not in evts:
            notes.append(f"{name}: {names[0]}'s cues could not be written")
    return "\n".join(out) + "\n", notes


# ---------------------------------------------------------------------------
# what a port writes

def loose_rel(dest_mod: str, pack_path: str) -> str:
    """Where under the destination's ``data/`` the loose file for
    ``pack_path`` goes: see *Where a loose file goes*."""
    p = pack_path.replace("\\", "/").lstrip("/")
    own = f"mods/{dest_mod}/data/".lower()
    return p[len(own):] if p.lower().startswith(own) else p


def text_path(dest_mod: str, rel: str) -> str:
    """The path an ``anim``/``-evt`` line gives a file at ``data/<rel>``."""
    return f"mods/{dest_mod}/data/{rel}"


@dataclass
class LooseFile:
    rel: str
    kind: str                 # "cas" or "evt"
    data: bytes = b""
    skeleton: str = ""

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass
class Rebuild:
    """What :func:`build` would write: the files, one block per skeleton, and
    what could not be done."""
    files: List[LooseFile] = field(default_factory=list)
    blocks: Dict[str, str] = field(default_factory=dict)
    present: int = 0           # slot files already on disk, left alone
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    text_rel: str = "descr_skeleton.txt"

    def bytes_written(self) -> int:
        return sum(f.size for f in self.files)

    def payload(self) -> dict:
        return {"files": len(self.files), "cas": sum(1 for f in self.files if f.kind == "cas"),
                "evt": sum(1 for f in self.files if f.kind == "evt"),
                "bytes": self.bytes_written(), "present": self.present,
                "skeletons": sorted(self.blocks), "notes": list(self.notes),
                "errors": list(self.errors)}


def _entry(idx: animpack.PackIndex, path: str, scale: float) -> Optional[animpack.PackEntry]:
    return animpack.resolve_slot(idx, path, scale)


def _exists(game_root: Optional[Path], data: Path, pack_path: str, rel: str) -> bool:
    if (data / rel).is_file():
        return True
    p = pack_path.replace("\\", "/")
    return game_root is not None and (game_root / p).is_file()


def _game_root(data: Path) -> Optional[Path]:
    return data.parent.parent.parent if data.parent.parent.name.lower() == "mods" else None


def build(dest_data, skeletons: List[Tuple[str, str]], source_data=None, tag: str = "ported",
          packs: Optional[animpack.Packs] = None,
          read_anim: Optional[Callable[[str, float], Optional[Tuple[bytes, float]]]] = None) -> Rebuild:
    """What keeps ``skeletons`` (``(name in the destination, name in the
    source)``) rebuildable in the mod at ``dest_data``: read from its packs as
    they are (so call it after the port is written), or from ``packs`` and
    ``read_anim(path, scale)`` (an entry's bytes and its own scale) when
    given. Nothing is written."""
    data = Path(dest_data)
    dest_mod = data.parent.name
    out = Rebuild()
    packs = packs or animpack.for_data(data)
    if packs is None or getattr(packs, "anims", None) is None or packs.skels is None:
        out.errors.append(f"{data} has no packs of its own")
        return out
    text = data / out.text_rel
    types = casanim.skeleton_types(data) if text.is_file() else {}
    if not text.is_file():
        out.errors.append("the destination has no descr_skeleton.txt of its own, so nothing is "
                          "written for a pack rebuild (a block in a new file would be all one read)")
        return out
    root = _game_root(data)
    dest_skels = [e.name for e in packs.skels.entries]

    def entry_bytes(path: str, scale: float) -> Optional[Tuple[bytes, float]]:
        if read_anim is not None:
            return read_anim(path, scale)
        e = _entry(packs.anims, path, scale)
        return (packs.anims.read_entry(e), e.scale) if e is not None else None

    written: Dict[str, LooseFile] = {}
    cues: Dict[str, str] = {}              # an .evt file's text -> its path, written once
    for dest_name, source_name in skeletons:
        if dest_name.lower() in types:
            out.notes.append(f"{dest_name}: descr_skeleton.txt already has a type of that name, "
                             "so no second block is written")
            continue
        skel = packs.skeleton(dest_name)
        if skel is None:
            out.errors.append(f"the skeleton pack has no {dest_name}")
            continue
        bones = skel.bone_table()
        frames: Dict[str, int] = {}
        ours: List[int] = []
        for i, s in skel.filled():
            k = animpack._key(s.path)
            rel = loose_rel(dest_mod, s.path)
            got = entry_bytes(s.path, skel.scale)
            if got is None:
                out.errors.append(f"{dest_name}: pack.idx has no {s.path}")
                continue
            data_b, entry_scale = got
            frames[k] = struct.unpack_from("<H", data_b, 0)[0]
            if rel.lower() in written:
                if written[rel.lower()].skeleton == dest_name:
                    ours.append(i)
                continue
            if _exists(root, data, s.path, rel):
                out.present += 1
                continue
            try:
                f = LooseFile(rel, "cas", cas_bytes(data_b, bones, entry_scale, s.path, skel.scale),
                              dest_name)
            except (LooseError, animpack.PackError) as e:
                out.errors.append(f"{dest_name}: {e}")
                continue
            written[rel.lower()] = f
            out.files.append(f)
            ours.append(i)
        evts: Dict[int, str] = {}
        for i, s in skel.filled():
            if not s.events or not skelslots.names(i):
                continue
            body = evt_text(s.events)
            if not body:
                continue
            if body not in cues:
                rel = f"animations/ported/{tag}/events/{dest_name}/{skelslots.names(i)[0]}.evt"
                out.files.append(LooseFile(rel, "evt", body.encode("latin-1"), dest_name))
                cues[body] = text_path(dest_mod, rel)
            evts[i] = cues[body]
        filled = [i for i, _s in skel.filled()]
        if not filled:
            continue
        first = DEFAULT_SLOT if DEFAULT_SLOT in ours else (ours[0] if ours else filled[0])
        if not ours:
            out.notes.append(f"{dest_name}: every file it names was already there, so a rebuild "
                             "builds its bones from one of those")
        header = type_header(source_data, source_name) if source_data is not None else None
        block, notes = render_block(dest_name, skel, header, frames, evts, first,
                                    _no_deltas(packs, skel) if header is None else False,
                                    dest_skels)
        out.blocks[dest_name] = block
        out.notes += notes
    return out


def append_blocks(text: str, blocks: Dict[str, str], why: str) -> str:
    """``descr_skeleton.txt`` with ``blocks`` added at its end, in the file's
    own line endings. The ``Version`` line is not touched."""
    crlf = text.count("\r\n")
    nl = "\r\n" if crlf and crlf >= text.count("\n") - crlf else "\n"
    body = "".join(f"{nl};; {why}{nl}" + b.replace("\n", nl) for _n, b in sorted(blocks.items()))
    if text and not text.endswith(("\n", "\r")):
        text += nl
    return text + body


def for_port(port: "animpack.PortPlan", source_data) -> Rebuild:
    """:func:`build` for a port not yet written: the ported skeletons as the
    plan made them, their animations out of the source's pack when the port
    appends them and out of the destination's otherwise."""
    dst = animpack.for_data(port.dest_dir)
    src, _whose = animpack.packs_for(source_data)
    rows = [s for s in port.skeletons if s.appends]
    if dst is None or src is None or not rows:
        return Rebuild()
    appended = {animpack._key(a.dest_path): a for a in port.anims if a.appends}
    parsed = {s.dest_name.lower(): animpack.PackedSkeleton(s.data, s.dest_name) for s in rows}

    class _View:
        """The destination's packs with the port's skeletons in them."""
        anims, skels = dst.anims, dst.skels

        def skeleton(self, name):
            return parsed.get(name.lower()) or dst.skeleton(name)

        def animation(self, path):
            a = appended.get(animpack._key(path))
            if a is not None:
                return animpack.PackedAnimation(src.anims.read_entry(a.entry), path)
            return dst.animation(path)

    def read(path: str, scale: float) -> Optional[Tuple[bytes, float]]:
        a = appended.get(animpack._key(path))
        if a is not None:
            return src.anims.read_entry(a.entry), a.entry.scale
        e = _entry(dst.anims, path, scale)
        return (dst.anims.read_entry(e), e.scale) if e is not None else None

    return build(port.dest_dir, [(s.dest_name, s.name) for s in rows], source_data, port.tag,
                 packs=_View(), read_anim=read)
