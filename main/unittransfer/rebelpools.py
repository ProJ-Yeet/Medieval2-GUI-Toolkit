"""Phase 35. Rebels right in place - the province and the rebel faction, both ways.

**A join and a screen, not a format.** Every file this needs was already read.
``descr_rebel_factions.txt`` is :data:`unittransfer.minorfiles.REBELS` and has
been since Phase 11 - a flat record with a ``category``, a ``chance``, a
``description`` and a repeating ``unit`` line - the region record is
:func:`unittransfer.campmap.parse_regions`' and its ``rebels`` slot has been
editable since 16d, and the map has been colourable by that slot since
:func:`unittransfer.mapquery.info_rebels`. What was missing is one direction:
**take a rebel faction and see its provinces.** Nothing anywhere did that.

**Three of the four things the scoping called missing already existed**, and
finding that out is most of what this phase is. Seeing what a rebel faction can
field is the Minor Files screen's rebel form, which lists the ``unit`` lines and
resolves each one against the EDU - it even prints ``✗ not a unit in this mod``.
Changing the assignment from the province end is the ``rebels`` box on the
province panel. Lighting a rebel faction's provinces is
:func:`unittransfer.mapquery.info_rebels` and the group filter that already
comes with a ``_by_value`` colouring. So what is built here is the reverse list,
and the one operation that end has and the province end does not: **assigning
many provinces at once.**

**So this is not a rebel faction editor.** That record belongs to the Minor
Files screen and works there; what this edits is the *assignment*, which lives
in a different file. The two screens link to each other and neither grows the
other's fields - 32c's ruling about the mercenary pool, made again here for the
same reason.

**The tutorial's complaint is not a rule, and the measurement is why.** The
archive has Errabundi's *Rebels Right in Place*, whose grievance is Bulgarian
rebels spawning in Serbia. Measured on both installed mods, **not one province
names a rebel faction that is not declared** - DaC's 200 records name 38 of its
42 blocks, Reforged's 199 name 27 of its 30 - and **not one of the 248 ``unit``
lines across the two mods names a unit the EDU does not have**, in any case.
There is nothing here for a validator to find. A wrong assignment is a *valid*
assignment somebody did not mean, and no rule can tell the two apart, which is
exactly what the write-up says: it is invisible unless you colour the whole map
and look. **So this phase ships no ``mapcheck`` rule and no repair.** It is a
legibility phase, and saying so is more honest than inventing a rule that would
fire on a correct file.

**What the measurement did turn up is the number that decides whether an
assignment does anything, and it is in the other file.** ``chance`` is the
per-block likelihood, and:

  * **Third Age Reforged sets ``chance 0`` on every one of the 27 blocks its
    provinces name.** All 199 of its provinces point at a zero-chance rebel
    faction. Province-driven rebel spawning is switched off across that whole
    mod, deliberately and uniformly - only ``brigands``, ``pirates`` and
    ``gladiator_uprising`` are non-zero, and no province names those.
  * **Divide and Conquer spreads it**: 2 on 29 blocks, 4 on 7, 6 on one, 10 on
    one, and ``No_Rebels`` at 0 on the 9 provinces that are meant to have none.

So ``chance 0`` is an idiom - "no rebels here" - and a rule that flagged it
would fire 199 times on one mod and 9 on the other and be wrong every time.
That is the baseline rule this project already keeps. What it earns instead is a
**note**: the panel says the chance beside every faction, because picking a
block for a province without knowing its chance is the one way to make this edit
and have it do nothing. That is the real "rebels right in place" failure, and it
is more defensible than the tutorial's.

**The three blocks no province ever names are not orphans.** Each mod declares
exactly one block per non-``peasant_revolt`` category - ``gladiator_uprising``
is ``gladiator_revolt``, ``brigands`` is ``brigands``, ``pirates`` is
``pirates`` - and the engine spawns those by category rather than off a region
record. :data:`BY_CATEGORY` is that rule, and without it the reverse list would
call three correct blocks dead on every mod. What is left over after the
exemption is a real orphan, and there are **two on DaC** - ``Ent_Rebels`` and
``Saralainn_Rebels``, declared with units and named by no province, so nothing
in them can ever spawn - and **none on Reforged**, which names both.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import campmap, minorfiles

#: ``descr_rebel_factions.txt``, relative to ``data/``.
REBELS_REL = "descr_rebel_factions.txt"

#: The category a block has to carry to be one a province can name.
#:
#: The engine's other three - ``gladiator_revolt``, ``brigands``, ``pirates`` -
#: are spawned by category rather than off a ``descr_regions.txt`` record, and
#: both installed mods declare exactly one block of each, named after the
#: category itself. A reverse list that did not know this would report three
#: correct blocks as unused on every mod there is.
BY_REGION = "peasant_revolt"

#: The three that are not, kept as the measured set rather than derived, because
#: what makes them special is the engine's behaviour and not their spelling.
BY_CATEGORY = ("gladiator_revolt", "brigands", "pirates")


def read_rebels(mod) -> minorfiles.RecordFile:
    """``descr_rebel_factions.txt``, parsed - or an empty file if it has none.

    A mod without the file is not an error here. It means every province's
    ``rebels`` value is dangling, which is what the reverse list will say.
    """
    from .keyblock import read_text
    path = Path(mod.data) / REBELS_REL
    try:
        text = read_text(path, campmap.ENCODING)
    except OSError:
        return minorfiles.parse_rebels("")
    out = minorfiles.parse_rebels(text)
    out.path = path
    return out


def _regions_of(mod, cm: Optional[campmap.CampaignMap]):
    """The ``descr_regions.txt`` to read, with or without a map to read it from.

    **The join needs no layer**, and a mod whose map will not decode must still
    get its reverse list: the whole of this is two text files under ``data/``
    and not one of them is a TGA. So a map is taken when there is one - it is
    what knows the campaign ships its own copy - and its absence falls back to
    the base file rather than being an error. That is 30's ruling, made here for
    the same reason the climate panel makes it.
    """
    return cm.regions if cm is not None else campmap.read_regions(mod)


def _rel_of(cm: Optional[campmap.CampaignMap]) -> str:
    """The data-relative path of the file :func:`_regions_of` answered with."""
    if cm is None:
        return campmap.REGIONS_REL
    return campmap.rel_of(cm, Path(campmap.REGIONS_REL).name)


def assignments(rf: campmap.RegionsFile) -> Dict[str, List[str]]:
    """``{rebel faction: [province, …]}`` - the direction nothing else had.

    Keyed by the value exactly as the record writes it, because that is what
    has to match a block's name for the engine to find one; the comparison a
    person would make by eye is done in :func:`_rows` and reported, never
    silently applied.
    """
    out: Dict[str, List[str]] = {}
    for rec in rf.records:
        if rec.rebels:
            out.setdefault(rec.rebels, []).append(rec.name)
    return out


def _units(rec, edu_types: Optional[set]) -> List[dict]:
    """A block's ``unit`` lines, each said to be in this mod's EDU or not.

    ``edu_types`` of ``None`` is "the roster could not be read", which is not
    the same answer as "the unit is not there" - a mod that ships a map and no
    roster must not have all 151 of its rebel units called dead. Both installed
    mods came back clean, so the unknown flag has no true case on this machine
    and is here for the mod that does.
    """
    out: List[dict] = []
    for rep in rec.repeats:
        value = rep.value.strip()
        out.append({"type": value, "line": rep.line,
                    "known": None if edu_types is None else value in edu_types})
    return out


def _edu_types(mod) -> Optional[set]:
    """Every unit type this mod's EDU declares, or ``None`` if it cannot be read."""
    try:
        return {u.type for u in mod.edu.units}
    except (OSError, AttributeError, ValueError):
        return None


def _rows(rf: minorfiles.RecordFile, used: Dict[str, List[str]],
          shown: Dict[str, str], edu_types: Optional[set]) -> List[dict]:
    """One row per declared rebel faction, with its provinces hung off it."""
    out: List[dict] = []
    for rec in rf.records:
        cat = rec.get("category")
        provinces = used.get(rec.name, [])
        by_category = cat in BY_CATEGORY
        chance = (rec.get("chance") or "").strip()
        units = _units(rec, edu_types)
        out.append({
            "name": rec.name,
            "category": cat,
            "chance": chance,
            "description": rec.get("description"),
            #: the shown name out of text/rebel_faction_descr.txt, keyed by the
            #: record's own `description` - minorfiles' ruling, not a new one
            "shown": shown.get(rec.get("description"), ""),
            "units": units,
            "unit_count": len(units),
            "dead_units": [u["type"] for u in units if u["known"] is False],
            "provinces": provinces,
            "count": len(provinces),
            #: spawned by category, so a province never names it and an empty
            #: province list is correct rather than a fault
            "by_category": by_category,
            #: declared, region-driven, and named by nothing - its units cannot
            #: spawn at all
            "orphan": not provinces and not by_category,
            #: the assignment is real and does nothing, which is legal and is
            #: what 27 of Reforged's 30 blocks say
            "silent": chance == "0",
            "line": rec.start + 1,
        })
    return out


def view(mod, cm: Optional[campmap.CampaignMap] = None) -> dict:
    """The whole join, both ways, for one mod and one campaign's map.

    ``cm`` decides which ``descr_regions.txt`` is read, the same way every
    other judgement on this screen does: a campaign that ships its own copy is
    read from that copy. ``descr_rebel_factions.txt`` is not a map file and has
    no per-campaign copy, so it is the mod's one and only.
    """
    regions = _regions_of(mod, cm)
    rebels = read_rebels(mod)
    used = assignments(regions)
    try:
        shown = minorfiles.rebel_loc(mod)
    except (OSError, ValueError):
        shown = {}
    rows = _rows(rebels, used, shown, _edu_types(mod))
    declared = {r.name for r in rebels.records}
    dangling = [{"name": n, "provinces": p, "count": len(p)}
                for n, p in sorted(used.items()) if n not in declared]
    blank = [r.name for r in regions.records if not r.rebels]
    return {
        "mod": getattr(mod, "name", ""),
        "file": _rel_of(cm),
        "rebels_file": REBELS_REL,
        "rebels": rows,
        "dangling": dangling,
        "blank": blank,
        "regions": len(regions.records),
        "declared": len(rows),
        "named": len([r for r in rows if r["count"]]),
        "orphans": len([r for r in rows if r["orphan"]]),
        "silent_regions": sum(r["count"] for r in rows if r["silent"]),
        "categories": list(minorfiles.REBEL_CATEGORIES),
    }


@dataclass
class RebelPlan:
    """Moving a set of provinces onto one rebel faction, worked out on paper."""

    mod: object = None
    rebel: str = ""
    regions: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    path: Optional[Path] = None
    rel: str = ""

    def summary(self) -> str:
        head = (f"{len(self.changes)} province(s) -> rebel faction "
                f"{self.rebel} in {getattr(self.mod, 'name', '?')}")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"rebel": self.rebel, "regions": list(self.regions),
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "rel": self.rel,
                "ok": not self.errors and bool(self.text)}


def plan(mod, cm: Optional[campmap.CampaignMap], body: dict) -> RebelPlan:
    """Work out the whole new ``descr_regions.txt`` for one bulk assignment.

    ``body`` is ``{mod, campaign, rebel, regions}``. Nothing is written.

    **The records are spliced back to front**, because every span is an index
    into the lines this is editing and replacing an early record moves every
    later one. Going backwards means each span is still true when it is used,
    which is the same reason :mod:`unittransfer.regiondel` works the way it
    does, and it is why this does not simply call :func:`campmap.plan_region`
    in a loop - that re-reads the file from disk each time and would write the
    first province's change over the second's.
    """
    p = RebelPlan(mod=mod, rebel=str(body.get("rebel") or "").strip())
    want = [str(n).strip() for n in (body.get("regions") or []) if str(n).strip()]
    p.regions = want
    rf = _regions_of(mod, cm)
    p.path = rf.path
    p.rel = _rel_of(cm)

    if not p.rebel:
        p.errors.append("no rebel faction named")
    if not want:
        p.errors.append("no provinces picked")
    if p.errors:
        return p

    rebels = read_rebels(mod)
    rec = rebels.get(p.rebel)
    if rec is None:
        p.errors.append(
            f"{p.rebel} is not a rebel faction descr_rebel_factions.txt "
            "declares. The engine reads this value off the region record and "
            "looks it up there by name, so a province naming a block that is "
            "not in the file gets no rebels at all. Add it on the Minor Files "
            "screen first")
        return p

    # the two facts a person needs BEFORE the write, not after it. Neither one
    # refuses: both are real states in the installed mods and both are legal.
    if (rec.get("chance") or "").strip() == "0":
        p.warnings.append(
            f"{p.rebel} has `chance 0`, so these provinces will spawn no "
            "rebels at all. That is a real setting rather than a mistake - "
            "Reforged sets it on all 27 of the blocks its provinces name, and "
            "DaC uses it for No_Rebels - but it is the whole of what this edit "
            "will do")
    if rec.get("category") in BY_CATEGORY:
        p.warnings.append(
            f"{p.rebel} is a `{rec.get('category')}` block, which the engine "
            "spawns by category rather than off a region record. Naming it "
            "here is not how it is meant to be reached")

    missing = [n for n in want if rf.by_name(n) is None]
    if missing:
        p.errors.append("no such province in " + p.rel + ": "
                        + ", ".join(missing[:6])
                        + (f" (+{len(missing) - 6} more)" if len(missing) > 6 else ""))
        return p

    # back to front, so every span is still true when it is used
    picked = [rf.by_name(n) for n in want]
    picked.sort(key=lambda r: r.span[0], reverse=True)
    text = rf.serialise()
    cursor = rf
    for target in picked:
        if target.rebels == p.rebel:
            continue
        base = campmap.record_text(cursor, target)
        block = campmap.render_block(base, {"rebels": p.rebel})
        text = campmap.replace_record(cursor, target, block)
        cursor = campmap.parse_regions(text)
        p.changes.append(
            f"{target.name}: {target.rebels or '(none)'} -> {p.rebel}")

    p.changes.reverse()          # back into the order the person picked them
    p.text = "" if text == rf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append(
            "nothing to change - every province picked already names "
            + p.rebel)
    return p


def apply(p: RebelPlan) -> dict:
    """Write a planned assignment, with the same backups and undo as any save.

    The file written is the one the plan read, and the stale ``map.rwm`` set is
    :func:`unittransfer.campmap.stale_rwm`'s - both of which is to say this goes
    through the same two answers the region save was corrected to use in this
    phase, rather than keeping a second opinion about where a region record
    lives.
    """
    import shutil
    import time

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [], "deleted": []}

    def keep(rel: str) -> Path:
        target = Path(mod.data) / rel
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

    target = keep(p.rel)
    write_text(target, p.text, campmap.ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    for srel in campmap.stale_rwm(mod, p.rel):
        rwm = Path(mod.data) / srel
        keep(srel)
        rwm.unlink()
        manifest["deleted"].append(srel)
        file_op("DELETE", rwm, "stale compiled map - the game would load it instead")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        "action": "rebels",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.rebel, "resolved_type": p.rebel,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("REBELS %s in %s - %d province(s), id=%s",
             p.rebel, mod.name, len(p.changes), tid)
    return {"id": tid, "rebel": p.rebel, "record": rec}
