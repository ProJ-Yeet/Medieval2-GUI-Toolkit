r"""The 687 slots named, and ``descr_skeleton.txt`` held against the packs (Phase 78).

A packed skeleton keeps its animations in 687 slots in the engine's fixed
order, and a slot carries no name, only its position. The names are
``descr_skeleton.txt``'s (``anim stand_a_idle <path>``), and the table that
joins the two, ``data/skeleton_slots.json``, was built by aligning the text
with the packs wherever the two agree: every skeleton on vanilla, ROCSS and
DaC whose text names exactly as many animations as its pack fills
(``dev/reference/skeleton_slots.py``, which says how).

**Every one of the 687 slots has a name** since 2026-09-26. The measurement
names 462 (455 before Reforged was installed again), every slot an installed
skeleton fills but one; a few of them only as a group whose names always share
a path (``die_to_back_right_2`` and ``die_to_back_left_2`` on 91 and 93). A list
of the engine's 687 names in order, shared by the user's friend
(``dev/reference/m2_slot_names.json``), agrees with every measured slot, so it
names the rest and says which slot of a group is which. :func:`measured` says
whether a slot's name was measured or taken from that list. A group still
shows as ``a / b`` if a table without the list is ever loaded.

**The packs are the truth.** Many mods appended to their packs, so the text is
often out of step with them, and the game plays the packs. :func:`report`
says how far out, for one mod: types the text has and the pack does not,
skeletons the pack has and the text does not, and per skeleton the slots
where the two disagree.

**And the modeldb held against the pack** (Phase 79): :func:`modeldb_findings`
lists every body or weapon skeleton a modeldb entry names that the mod's own
``skeletons.idx`` has not got, which Health reports. A weapon skeleton is a
warning, not a crash: it only shows when the mesh has weight on the weapon
bones (Makanyane).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import animpack, casanim

_TABLE_PATH = Path(__file__).resolve().parent / "data" / "skeleton_slots.json"
_TABLE: Optional[Tuple[Tuple[str, ...], ...]] = None
_BY_NAME: Dict[str, Tuple[int, ...]] = {}
_MEASURED: set = set()


def _load():
    global _TABLE
    if _TABLE is None:
        doc = json.loads(_TABLE_PATH.read_text(encoding="utf-8"))
        raw = doc["slots"]
        _MEASURED.update(doc.get("measured") or [i for i, v in enumerate(raw) if v])
        table = []
        for i, v in enumerate(raw):
            names = () if v is None else (v,) if isinstance(v, str) else tuple(v)
            table.append(names)
            for n in names:
                _BY_NAME[n] = _BY_NAME.get(n, ()) + (i,)
        _TABLE = tuple(table)
    return _TABLE


def names(slot: int) -> Tuple[str, ...]:
    """The slot's name, or its group's names; empty for a slot nothing names."""
    return _load()[slot]


def label(slot: int) -> str:
    """``stand_a_idle``, ``crew_right / crew_right_to_crew_stand`` for a group,
    or ``slot 312`` for one with no name."""
    n = names(slot)
    return " / ".join(n) if n else f"slot {slot}"


def slots_of(name: str) -> Tuple[int, ...]:
    """The slot an ``anim`` name fills, or every slot of its group; empty for a
    name the table does not know."""
    _load()
    return _BY_NAME.get(name.lower(), ())


def named() -> int:
    return sum(1 for n in _load() if n)


def measured(slot: int) -> bool:
    """Whether the slot's name was measured off the installed packs (True) or
    taken from the list of the engine's names (False)."""
    _load()
    return slot in _MEASURED


# ---------------------------------------------------------------------------
# one skeleton, text against pack

@dataclass
class SlotDiff:
    """Slots where the text and the pack disagree. ``slots`` is one slot, or a
    group's; the paths are as each side writes them (``""`` for none)."""
    slots: Tuple[int, ...]
    label: str
    text: List[str]
    pack: List[str]

    @property
    def kind(self) -> str:
        if not any(self.pack):
            return "text only"
        if not any(self.text):
            return "pack only"
        return "path differs"


@dataclass
class SkeletonDiff:
    name: str
    diffs: List[SlotDiff] = field(default_factory=list)
    #: ``anim`` names the table does not know: a typo the engine skips, or a
    #: slot no installed skeleton fills
    unknown: List[str] = field(default_factory=list)
    #: ``anim`` names given twice in the block, the path of each
    repeated: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def in_step(self) -> bool:
        return not self.diffs


def compare(skel: animpack.PackedSkeleton, text: casanim.SkeletonType) -> SkeletonDiff:
    """Every slot the text names or the pack fills, held side by side."""
    out = SkeletonDiff(text.name)
    table = _load()
    by_name: Dict[str, List[str]] = {}
    for action, path in text.anims:
        by_name.setdefault(action.lower(), []).append(path)
    for n, paths in by_name.items():
        if len(paths) > 1:
            out.repeated[n] = paths
        if not slots_of(n):
            out.unknown.append(n)
    seen = set()
    for i in range(animpack.SKELETON_SLOTS):
        if i in seen:
            continue
        group = slots_of(table[i][0]) if table[i] else (i,)
        seen.update(group)
        # a name repeated in the block: the last line is taken as the one
        text_paths = sorted(animpack._key(by_name[n][-1]) for n in table[i] if n in by_name)
        pack_paths = sorted(animpack._key(skel.slots[s].path) for s in group
                            if skel.slots[s] is not None)
        if text_paths == pack_paths:
            continue
        # a group whose names all share one path: the same path on every slot is agreement
        if text_paths and set(text_paths) == set(pack_paths) and len(set(text_paths)) == 1:
            continue
        out.diffs.append(SlotDiff(tuple(group), label(i), text_paths, pack_paths))
    return out


# ---------------------------------------------------------------------------
# one mod

@dataclass
class Report:
    text: Optional[Path]
    anim_dir: Optional[Path]
    text_only: List[str] = field(default_factory=list)
    pack_only: List[str] = field(default_factory=list)
    #: types listed more than once, in the text or the pack; not compared slot
    #: by slot, since which block the game keeps is not known
    twice: List[str] = field(default_factory=list)
    skeletons: List[SkeletonDiff] = field(default_factory=list)

    @property
    def out_of_step(self) -> List[SkeletonDiff]:
        return [s for s in self.skeletons if not s.in_step]

    def counts(self) -> Dict[str, int]:
        kinds: Dict[str, int] = {"path differs": 0, "pack only": 0, "text only": 0}
        for s in self.skeletons:
            for d in s.diffs:
                kinds[d.kind] += 1
        return {"in the text": len(self.skeletons) + len(self.text_only),
                "compared": len(self.skeletons),
                "in step": len(self.skeletons) - len(self.out_of_step),
                "out of step": len(self.out_of_step),
                "text only": len(self.text_only), "pack only": len(self.pack_only),
                "listed twice": len(self.twice),
                "slots, path differs": kinds["path differs"],
                "slots, pack only": kinds["pack only"],
                "slots, text only": kinds["text only"],
                "unknown names": sum(len(s.unknown) for s in self.skeletons)}

    def as_dict(self) -> dict:
        return {
            "text": str(self.text) if self.text else None,
            "packs": str(self.anim_dir) if self.anim_dir else None,
            "counts": self.counts(),
            "text_only": self.text_only, "pack_only": self.pack_only, "twice": self.twice,
            "out_of_step": [{"skeleton": s.name,
                             "slots": [{"slots": list(d.slots), "name": d.label, "kind": d.kind,
                                        "text": d.text, "pack": d.pack} for d in s.diffs],
                             "unknown": s.unknown} for s in self.out_of_step],
        }


def report(data_dir, text_dir=None) -> Report:
    """``descr_skeleton.txt`` (from ``text_dir``, default ``data_dir``) held
    against the packs in ``data_dir/animations``. Either may be missing: a mod
    with no pack plays vanilla's, and one with no text has nothing to hold."""
    text_dir = Path(text_dir) if text_dir is not None else Path(data_dir)
    types = casanim.skeleton_types(text_dir)
    packs = animpack.for_data(data_dir)
    skels = packs.skels if packs else None
    out = Report(text_dir / "descr_skeleton.txt" if types else None,
                 packs.dir if packs else None)
    if skels is None:
        out.text_only = sorted(t.name for t in types.values())
        return out
    for key, t in sorted(types.items()):
        hits = skels.find(key)
        if not hits:
            out.text_only.append(t.name)
        elif len(hits) > 1 or t.blocks > 1:
            out.twice.append(t.name)
        else:
            out.skeletons.append(compare(packs.skeleton(hits[0].name), t))
    out.pack_only = sorted({e.name for e in skels.entries if e.name.lower() not in types},
                           key=str.lower)
    return out


# ---------------------------------------------------------------------------
# the modeldb held against the mod's own pack (Phase 79)

MODELDB_REL = "unit_models/battle_models.modeldb"


def modeldb_findings(mod) -> List[dict]:
    """Every body or weapon skeleton a modeldb entry names that the mod's own
    ``skeletons.idx`` has not got, one row per entry and skeleton. Empty for a
    mod with no pack of its own: it plays vanilla's, and its modeldb names are
    all there is to hold anything against. Measured 2026-09-25: ROCSS 3 (all
    weapon skeletons), DaC none."""
    packs = animpack.for_data(mod.data)
    if packs is None or packs.skels is None or not mod.modeldb_path.is_file():
        return []
    rows: List[dict] = []
    seen = set()
    for e in mod.modeldb.entries:
        for kind, names in (("body", e.skeletons()), ("weapon", e.weapon_skeletons())):
            for s in dict.fromkeys(names):
                if s in packs.skels or (e.name, s.lower()) in seen:
                    continue
                seen.add((e.name, s.lower()))
                if kind == "body":
                    msg = (f"'{e.name}' is animated by the skeleton '{s}', which this mod's "
                           "skeleton pack has not got. A unit drawn with this model crashes "
                           "the battle it loads in.")
                else:
                    msg = (f"'{e.name}' names '{s}' as a weapon skeleton, and this mod's "
                           "skeleton pack has not got it. That only shows if the mesh has "
                           "vertices weighted to the weapon bones (a bowstring, a flag, a "
                           "javelin): the weapon stays still.")
                rows.append({"code": f"skeleton.{kind}_not_in_pack", "name": e.name,
                             "skeleton": s, "kind": kind, "message": msg,
                             "severity": "fatal" if kind == "body" else "warn"})
    return rows


# ---------------------------------------------------------------------------
# families, so two hundred actions can be found (Phase 80)

#: The order the viewer lists them in; the first pattern a name matches wins.
FAMILIES = (
    ("stand", "Standing and idle", r"^(stand|idle|ready(?!_brace)|taunt|celebrate|selected|"
                                   r"er_stand|victory|pre_battle|general_signal)"),
    ("move", "Walking and running", r"^(walk|run(?!_attack)|shuffle|step|advance|combat_jog|"
                                    r"retreat|stealthy|hide|er_walk|er_run|jump)"),
    ("charge", "Charging", r"^charge"),
    ("attack", "Attacking", r"^(eager_attack|attack|run_attack)"),
    ("defend", "Defending", r"^eager_defend"),
    ("brace", "Braced formation", r"brace"),
    ("die", "Hit, knocked down and dying", r"^(die|knockback|knockdown|kill_mount|impact)"),
    ("crew", "Crews, carrying and siege", r"^(crew|carry|push|pull|raise_hand|siege|elephant)"),
    ("climb", "Climbing and swimming", r"^(climb|swim)"),
    ("agent", "Agents on the campaign map", r"^(build_settlement|ambush|no_mp|despoil|decimate|"
                                            r"insurrect|sabotage|assassinate|capture|spying|"
                                            r"conduct|refuse|druid)"),
    ("other", "Everything else", r""),
)
_FAMILY_RES = None


def family(name: str) -> str:
    """The family id of an ``anim`` name (``walk_to_run`` is ``move``)."""
    global _FAMILY_RES
    if _FAMILY_RES is None:
        import re
        _FAMILY_RES = [(fid, re.compile(rx)) for fid, _label, rx in FAMILIES]
    n = (name or "").lower()
    return next(fid for fid, rx in _FAMILY_RES if rx.search(n))
