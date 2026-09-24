"""Phase 72, D13. A horde start for a faction that holds nothing.

16j-2 creates a faction's campaign entry with the donor's AI, label, purse and
diplomacy **and nothing else** - no settlement, no character, no coordinate -
and says so, because that is the shape vanilla's Mongols and Timurids already
are. This is the other half: the start that makes such a faction appear.

**Two starts, because the engine has two.** A faction with no settlement comes
onto the map in one of two ways, and they are different files:

* **On the map from turn one** (``map``): its generals are written into its
  ``descr_strat.txt`` block like anybody else's, each standing on a tile with an
  army behind him. That is 16i's character block, written by 16i's own
  :func:`~unittransfer.stratchar.new_character` in the shape of the lines
  around it. The faction is alive at the start, so a ``dead_until_resurrected``
  line it carries is taken off.
* **Later, on a date** (``emerge``): the faction starts dormant -
  ``dead_until_resurrected`` on its block, as vanilla's Mongols and Timurids
  write it - and an ``event emergent_faction <slot>`` block in the campaign's
  ``descr_events.txt`` brings it in. The game's own header for that file names
  the category: *"emergent_faction - triggers the emergence of the given
  faction"*. The event is written by 18b's own
  :func:`~unittransfer.campevents.new_event_lines`, with its date and the
  positions picked on the map.

**Both are a horde, and that half is shared.** The seven ``horde_*`` numbers and
the ``horde_unit`` list in ``descr_sm_factions.txt`` are what the engine builds
the horde out of and what keeps a faction with no settlement a horde rather
than a faction that has lost. Phase 11's faction editor already edits them one
box at a time; this writes all of them at once, from another horde faction in
the same mod when there is one, so nothing is invented that the mod does not
already say. :data:`factions.HORDE_KEYS` is the list, and 11's rule that they
are all or none (``part-horde``) is met by construction.

**An emergence is an event, and 18b's rules about events apply to it.** Its
label is looked up in ``text/historic_events.txt`` as ``{SLOT_TITLE}`` and
``{SLOT_BODY}`` - the guide says an event with no text crashes the turn it
fires - and it is the file name of a picture in every ``ui/<culture>/eventspic``
folder the mod ships, which is a campaign CTD when it is missing. So the plan
writes both text keys (whichever of the ``.txt`` and the ``.strings.bin`` the mod
has) and copies a picture into each folder that lacks one, from an event the
mod already has a picture for.

**What is refused.** A faction that still holds a settlement: a horde start is
the start of a faction with no home, and the settlement panel is where a home
is given or taken. And an emergence for a faction that already has people in
its block: a dormant faction's characters are the ones the event makes, and a
general written in by hand under ``dead_until_resurrected`` is one the file and
the flag disagree about.

**What is not claimed.** Nothing here has been watched in game on this
machine. What the engine does with each line is the game's own header, the
existing readers' measurements and TWCenter's tutorials; the ``position`` lines
of an ``emergent_faction`` event are written as 18b writes any event's, and
where the horde really lands is the first thing to check in game.

One plan, one backup set, one Undo, across every file it touches.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campevents, campmap, campstrat, factions, stratcamp, stratchar
from . import flatrecord as fr
from . import keyblock as kb
from .stratedit import assemble, finding, is_int, serialise

#: the two starts - see the module docstring
MODES = ("map", "emerge")

#: the flag that keeps a faction off the map until something brings it in
DORMANT = "dead_until_resurrected"

#: the event category that brings it in
EMERGENT = "emergent_faction"

#: Starting numbers for a mod with no horde faction of its own to copy. A mod
#: that has one is offered that faction's numbers instead, which is why these
#: are only ever a fallback and are shown as the tool's rather than as anybody's
#: measurement.
DEFAULT_KEYS: Dict[str, int] = {
    "horde_min_units": 10,
    "horde_max_units": 20,
    "horde_max_units_reduction_every_horde": 10,
    "horde_unit_per_settlement_population": 250,
    "horde_min_named_characters": 2,
    "horde_max_percent_army_stack": 80,
    "horde_disband_percent_on_settlement_capture": 0,
}

#: the two keys that are a share of something, so 0 to 100
PERCENT_KEYS = ("horde_max_percent_army_stack",
                "horde_disband_percent_on_settlement_capture")

#: A stack holds twenty units, the general's bodyguard among them - the engine's
#: own limit, and the one 16i's army form is built around.
STACK_LIMIT = 20

#: a general written for a map start, unless the form says otherwise
DEFAULT_AGE = 30


class HordeError(ValueError):
    """The request cannot be turned into a plan at all."""


# ---------------------------------------------------------------------------
# what the mod already says


def _sm_record(rf: fr.RecordFile, slot: str):
    low = slot.lower()
    return next((r for r in rf.records if factions.slot_of(r.name).lower() == low),
                None)


def _horde_of(rec) -> Optional[Dict]:
    """A record's horde, or None when it has none."""
    if rec is None or not any(k in rec.lines for k in factions.HORDE_KEYS):
        return None
    return {"keys": {k: rec.get(k) for k in factions.HORDE_KEYS if k in rec.lines},
            "units": [r.value for r in rec.repeats]}


def donors(rf: fr.RecordFile, skip: str = "") -> List[Dict]:
    """Every faction in ``descr_sm_factions.txt`` that is a whole horde already."""
    out = []
    for rec in rf.records:
        slot = factions.slot_of(rec.name)
        h = _horde_of(rec)
        if slot.lower() == skip.lower() or h is None:
            continue
        if len(h["keys"]) == len(factions.HORDE_KEYS) and h["units"]:
            out.append(dict(h, faction=slot))
    return out


def _edu_units(mod) -> Tuple[Optional[Dict[str, object]], str]:
    """``{type: unit}`` from the EDU, or ``(None, why)`` when it will not read."""
    try:
        units = mod.edu.units
    except Exception as exc:                               # noqa: BLE001
        return None, f"export_descr_unit.txt could not be read ({exc})"
    if not units:
        return None, ("export_descr_unit.txt is not on disk, so no unit can be "
                      "checked against a roster")
    return {u.type: u for u in units}, ""


def owned_units(units: Dict[str, object], slot: str) -> List[str]:
    """The units whose ``ownership`` names this faction, in EDU order."""
    low = slot.lower()
    return [t for t, u in units.items()
            if any(o.lower() in (low, "all") for o in (getattr(u, "ownership", None) or []))]


def _emergent_blocks(bf: Optional[campevents.BlockFile], slot: str):
    if bf is None:
        return []
    low = slot.lower()
    return [b for b in bf.blocks
            if b.kind == EMERGENT and (b.name or "").lower() == low]


def _read_events(mod, campaign: str):
    """The event file and its text, or ``(None, '')`` when the campaign has none."""
    try:
        return campevents.read_events(mod, campaign)
    except campevents.CampEventError:
        return None, ""


def _pictures(mod) -> Tuple[List[str], List[str]]:
    """The eventspic folders, and the labels every one of them has a picture for.

    Only a label with a picture in *every* folder is offered as the one to copy,
    because a copy has to come from somewhere in each folder it goes into.
    """
    dirs = campevents.eventspic_dirs(mod)
    rels = [str(d.relative_to(Path(mod.data))).replace("\\", "/") for d in dirs]
    common: Optional[set] = None
    for d in dirs:
        try:
            have = {p.stem for p in d.glob("*.tga") if p.is_file()}
        except OSError:
            have = set()
        common = have if common is None else common & have
    return rels, sorted(common or (), key=str.lower)


def _unused_names(voc: stratchar.Vocabulary, sf, slot: str) -> List[str]:
    """Pool names nobody in the campaign file is called yet, for the name boxes."""
    used = {n.name for n in sf.of_kind("character")}
    used |= {n.name for n in sf.of_kind("character_record")}
    return [n for n in (voc.pool.get(slot) or []) if n and n not in used]


def view(mod, facts, faction: str = "") -> Dict:
    """Everything the Horde start tab shows, for one faction of one campaign."""
    campaign = facts.campaign
    sf = campstrat.read_strat(mod, campaign)
    out: Dict = {"campaign": campaign, "modes": list(MODES),
                 "keys": list(factions.HORDE_KEYS), "defaults": dict(DEFAULT_KEYS),
                 "stack_limit": STACK_LIMIT, "default_age": DEFAULT_AGE,
                 "factions": [], "faction": None, "skipped": []}
    for node in sf.of_kind("faction"):
        out["factions"].append({
            "name": node.name,
            "settlements": len(sf.children_of(node, "settlement")),
            "characters": len(sf.descendants_of(node, "character")),
            "dormant": bool(node.get(DORMANT))})
    slot = faction or next((f["name"] for f in out["factions"]
                            if not f["settlements"]), "")
    node = sf.faction(slot) if slot else None
    if node is None:
        return out
    slot = node.name

    rf = factions.parse_file(factions.path_for(mod)) \
        if factions.path_for(mod).is_file() else None
    rec = _sm_record(rf, slot) if rf is not None else None
    units, why = _edu_units(mod)
    if units is None:
        out["skipped"].append({"what": "export_descr_unit.txt", "why": why})
    voc = stratchar.Vocabulary(facts, sf)
    bf, _ = _read_events(mod, campaign)
    blocks = _emergent_blocks(bf, slot)
    pic_dirs, pic_labels = _pictures(mod)
    pairs = campevents.event_text_pairs(mod)
    tag = slot.upper()
    cm = campmap.map_of(facts)
    out["faction"] = {
        "name": slot,
        "settlements": [n.name for n in sf.children_of(node, "settlement")],
        "characters": [n.name for n in sf.descendants_of(node, "character")],
        "leader": stratchar.leader_of(sf, node),
        "flags": [k for k in campstrat.FACTION_FLAGS if node.get(k)],
        "in_sm": rec is not None,
        "horde": _horde_of(rec),
        "donors": donors(rf, slot) if rf is not None else [],
        "owned": owned_units(units, slot) if units else [],
        "bodyguards": [t for t in (owned_units(units, slot) if units else [])
                       if t in voc.bodyguards],
        "units": sorted(units, key=str.lower) if units else voc.unit_names(),
        "names": _unused_names(voc, sf, slot)[:40],
        "have_pool": voc.have_pool,
        "event": ({"dates": blocks[0].all("date"),
                   "positions": [[p.x, p.y] for p in blocks[0].positions],
                   "line": blocks[0].head_line + 1} if blocks else None),
        "events_file": bf is not None,
        "text": {"title": pairs.get(f"{tag}_TITLE", ""),
                 "body": pairs.get(f"{tag}_BODY", ""),
                 "have_file": bool(pairs)},
        "eventspic": pic_dirs,
        "pictures": pic_labels,
        "has_picture": bool(pic_dirs) and slot in pic_labels,
    }
    out["size"] = ([cm.terrain.width, cm.terrain.height] if cm is not None
                   else list(campevents._map_size(mod) or []) or None)
    out["skipped"] += list(voc.skipped)
    return out


# ---------------------------------------------------------------------------
# the plan


@dataclass
class HordePlan:
    """One horde start, worked out without touching the disk."""

    mod: object = None
    campaign: str = campstrat.DEFAULT_CAMPAIGN
    faction: str = ""
    mode: str = "map"
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: data-relative path -> the whole new text, for the three latin-1 files
    texts: Dict[str, str] = field(default_factory=dict)
    #: data-relative path -> the block or lines this plan writes there, to show
    blocks: Dict[str, str] = field(default_factory=dict)
    #: ``{SLOT_TITLE}`` and ``{SLOT_BODY}``, when an emergence needs them
    loc_writes: Dict[str, str] = field(default_factory=dict)
    #: (from, to), data-relative: the event pictures copied in
    copies: List[Tuple[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        head = (f"horde start ({self.mode}) for {self.faction} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def touched(self) -> bool:
        return bool(self.texts or self.loc_writes or self.copies)

    def payload(self) -> Dict:
        return {"faction": self.faction, "mode": self.mode,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "blocks": dict(self.blocks),
                "files": sorted(set(self.texts) | {t for _f, t in self.copies}
                                | ({campevents.EVENT_TEXT_REL} if self.loc_writes
                                   else set())),
                "loc_writes": dict(self.loc_writes),
                "copies": [list(c) for c in self.copies],
                "ok": not self.errors and self.touched()}


def _rel(path: Path, mod) -> str:
    return str(Path(path).relative_to(Path(mod.data))).replace("\\", "/")


def plan(mod, facts, body: dict) -> HordePlan:
    """Work out every file one horde start writes.

    ``body`` is ``{faction, mode, keys, units, generals, dates, positions,
    title, text, picture_from}``: ``keys`` the seven numbers, ``units`` the
    ``horde_unit`` list, ``generals`` (``map``) a list of ``{name, age, x, y,
    army}``, and the rest (``emerge``) the event, its words and the event
    picture to copy.

    The campaign file is read from disk rather than out of ``facts``, which is
    16h's rule for every writer of it: the fact table is the vocabulary and the
    map, and a cache is not what a writer writes over.
    """
    p = HordePlan(mod=mod, campaign=str(body.get("campaign") or "") or facts.campaign,
                  faction=str(body.get("faction") or "").strip(),
                  mode=str(body.get("mode") or "map").strip().lower())
    if p.mode not in MODES:
        p.errors.append(f"a horde start is {kb.and_list(MODES)}, not {p.mode!r}")
        return p
    try:
        sf = campstrat.read_strat(mod, p.campaign)
    except (OSError, ValueError) as exc:
        p.errors.append(str(exc))
        return p
    node = sf.faction(p.faction) if p.faction else None
    if node is None:
        p.errors.append(f"{p.faction or '(nothing)'} has no faction block in "
                        f"{p.campaign}'s descr_strat.txt. The New faction tab "
                        f"writes one")
        return p
    p.faction = node.name
    towns = sf.children_of(node, "settlement")
    if towns:
        p.errors.append(
            f"{p.faction} holds {len(towns)} settlement(s) - "
            + ", ".join(t.name for t in towns[:4]) + (", …" if len(towns) > 4 else "")
            + ". A horde start is the start of a faction with no home; the "
              "settlement panel gives a settlement to somebody else first")
        return p
    try:
        _plan_sm(p, mod, body)
        if p.mode == "map":
            _plan_map(p, mod, facts, sf, node, body)
        else:
            _plan_emerge(p, mod, facts, sf, node, body)
    except (HordeError, fr.RecordError, kb.BlockError) as exc:
        p.errors.append(getattr(exc, "message", None) or str(exc))
        return p
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    if not p.touched() and not p.errors:
        p.errors.append("nothing to change")
    return p


# -- descr_sm_factions.txt ----------------------------------------------------


def check_keys(keys: Dict[str, object]) -> List[dict]:
    """The seven numbers: whole, not negative, and the two ranges that say so."""
    out: List[dict] = []
    for k in factions.HORDE_KEYS:
        v = keys.get(k)
        if v in (None, "") or not kb.is_int(str(v).strip()):
            out.append(finding("horde.number", True,
                               f"{k} is {v if v not in (None, '') else '(nothing)'}"
                               f", which is not a whole number.", key=k))
        elif int(str(v).strip()) < 0:
            out.append(finding("horde.number", True,
                               f"{k} is {v}, and it cannot be negative.", key=k))
    if out:
        return out
    n = {k: int(str(keys[k]).strip()) for k in factions.HORDE_KEYS}
    if n["horde_min_units"] > n["horde_max_units"]:
        out.append(finding(
            "horde.range", True,
            f"horde_min_units is {n['horde_min_units']} and horde_max_units "
            f"{n['horde_max_units']}: the least a horde has is more than the most."))
    for k in PERCENT_KEYS:
        if n[k] > 100:
            out.append(finding("horde.percent", True,
                               f"{k} is {n[k]}, and it is a share of 100.", key=k))
    return out


def _plan_sm(p: HordePlan, mod, body: dict) -> None:
    path = factions.path_for(mod)
    if not path.is_file():
        raise HordeError(f"{getattr(mod, 'name', '?')} has no {factions.REL} on "
                         f"disk, and a horde is written there")
    original = kb.read_text(path, factions.ENCODING)
    rf = factions.parse_text(original)
    rec = _sm_record(rf, p.faction)
    if rec is None:
        raise HordeError(f"{factions.REL} does not declare {p.faction}. The "
                         f"Factions screen clones the faction files first")
    keys = {k: str((body.get("keys") or {}).get(k, "")).strip()
            for k in factions.HORDE_KEYS}
    p.findings += check_keys(keys)
    wanted = [str(u).strip() for u in (body.get("units") or []) if str(u).strip()]
    if not wanted:
        p.findings.append(finding(
            "horde.units", True,
            "A horde with no `horde_unit` line has nothing to spawn - 11's own "
            "rule on this file, `horde-no-units`."))
    units, _why = _edu_units(mod)
    if units is not None:
        for u in wanted:
            if u not in units:
                p.findings.append(finding(
                    "horde.unit_unknown", True,
                    f"{u} is not a unit export_descr_unit.txt declares.", unit=u))
    seen = set()
    for u in wanted:
        if u in seen:
            p.findings.append(finding(
                "horde.unit_twice", False,
                f"{u} is listed twice. Vanilla's hordes list a unit once.", unit=u))
        seen.add(u)
    if any(f["fatal"] for f in p.findings):
        return

    base = rf.block_text(rec)
    block = factions.render_block(base, dict(keys))
    if rec.repeats:
        block = factions.render_block(block, {"units": wanted})
    else:
        block = _add_units(block, wanted)
    if block == base:
        return
    text = rf.replace(rec.start, rec.end, block)
    check = factions.parse_text(text)
    now = _sm_record(check, p.faction)
    if now is None or [r.value for r in now.repeats] != wanted \
            or any(str(now.get(k)) != keys[k] for k in factions.HORDE_KEYS):
        raise HordeError(f"After this save {factions.REL} does not read back as "
                         f"the horde it was asked to write")
    p.texts[factions.REL] = text
    p.blocks[factions.REL] = check.block_text(now)
    p.changes += [f"{factions.REL}: {c}" for c in kb.diff(base, block)]


def _add_units(block: str, wanted: Sequence[str]) -> str:
    """``horde_unit`` lines into a record that has none, under its horde numbers.

    Where every horde in the installed mods writes them: straight after the
    last ``horde_*`` number, before ``can_sap``. :func:`flatrecord.edit_repeats`
    would put a first one at the end of the record, which parses and reads as a
    stray line to anybody opening the file.
    """
    rec = factions.parse_block(block)
    lines, newline, trailing = fr.split_lines(block)
    at = max(rec.lines[k] for k in factions.HORDE_KEYS if k in rec.lines)
    culture = rec.lines.get("culture", at)
    indent = kb.indent_of(lines[at])
    column = kb.value_column(lines[culture], "culture")
    rows = [kb.pad_to_column("horde_unit", indent, column) + u for u in wanted]
    return (newline.join(lines[:at + 1] + rows + lines[at + 1:])
            + (newline if trailing else ""))


# -- descr_strat.txt ----------------------------------------------------------


class _Spans:
    """What :func:`stratcamp._faction_splice` records its runs on."""
    spans: list = []


def _flags(sf, node, want_on: bool) -> List[str]:
    """The block's own flag lines, with :data:`DORMANT` turned on or off."""
    have = [k for k in campstrat.FACTION_FLAGS if node.get(k)]
    keep = [k for k in have if k != DORMANT]
    return keep + [DORMANT] if want_on else keep


def _set_dormant(sf, node, on: bool) -> Tuple[List[str], bool]:
    """The file's lines with the flag set, and whether that changed anything."""
    if bool(node.get(DORMANT)) == on:
        return list(sf.lines), False
    lines = stratcamp._faction_splice(sf, _Spans(), node,
                                      {"flags": _flags(sf, node, on), "scalars": {}})
    return lines, True


def _others_unchanged(before, after, slot: str) -> List[str]:
    """Every other faction's block, byte for byte. The guard this writer keeps.

    16j-1's is a walk over declared runs; this plan's runs are a flag line and
    whole new blocks inside one faction, so what it may not touch is simpler to
    say: anything in anybody else's block, and anything outside a faction.
    """
    def blocks(sf):
        return {n.name.lower(): "\n".join(sf.lines[n.start:n.end + 1])
                for n in sf.of_kind("faction")}
    was, now = blocks(before), blocks(after)
    out = [f"{name}'s block changed" for name in was
           if name != slot.lower() and was[name] != now.get(name)]
    if set(was) != set(now):
        out.append("The file's faction blocks are not the same set after this save")
    return out


def _plan_map(p: HordePlan, mod, facts, sf, node, body: dict) -> None:
    raw = [g for g in (body.get("generals") or []) if isinstance(g, dict)]
    if not raw:
        raise HordeError("a start on the map needs at least one general to stand "
                         "on it")
    lines, flag_moved = _set_dormant(sf, node, False)
    cur = campstrat.parse_strat(serialise(sf, lines))
    voc = stratchar.Vocabulary(facts, cur)
    cm = campmap.map_of(facts, p.campaign)
    has_leader = bool(stratchar.leader_of(cur, cur.faction(p.faction)))
    written: List[str] = []
    names = set()
    for i, g in enumerate(raw):
        army = [stratchar.Army(unit=str(u).strip()) for u in (g.get("army") or [])
                if str(u).strip()]
        spec = stratchar.Spec(
            name=str(g.get("name") or "").strip(), type="named character",
            gender="male",
            rank="leader" if (i == 0 and not has_leader) else "",
            age=g.get("age") if g.get("age") not in (None, "") else DEFAULT_AGE,
            x=g.get("x"), y=g.get("y"), army=army)
        who = spec.name or f"general {i + 1}"
        if spec.name and spec.name in names:
            p.findings.append(finding(
                "horde.same_name", True,
                f"Two generals are called {spec.name}; a `relative` line and a "
                f"script address a character by name and nothing else."))
        names.add(spec.name)
        if not army:
            p.findings.append(finding(
                "horde.no_army", True,
                f"{who} has no army. A horde start is its armies, and a general "
                f"with none is a man standing alone on a tile."))
        elif len(army) > STACK_LIMIT:
            p.findings.append(finding(
                "horde.stack", True,
                f"{who} leads {len(army)} units and a stack holds {STACK_LIMIT}."))
        for f in stratchar.check_character(voc, spec, cm) \
                + stratchar.check_pool(voc, p.faction, spec.name):
            f = dict(f)
            f["message"] = f"{who}: {f['message']}"
            p.findings.append(f)
        if any(f["fatal"] for f in p.findings):
            continue
        faction = cur.faction(p.faction)
        block = stratchar.new_character(cur, faction, spec)
        at = stratchar.insert_at(cur, faction)
        lines = cur.lines[:at] + block + cur.lines[at:]
        cur = campstrat.parse_strat(serialise(cur, lines))
        written += block
        p.changes.append(
            f"descr_strat.txt: + {spec.name}{' (leader)' if spec.rank else ''} at "
            f"{spec.x},{spec.y} with {len(army)} unit(s)")
    if any(f["fatal"] for f in p.findings):
        return
    if flag_moved:
        p.changes.insert(0, f"descr_strat.txt: - {DORMANT} on {p.faction}, which "
                            f"starts on the map now")
    p.findings += stratchar.check_faction(cur, cur.faction(p.faction), voc)
    _strat_text(p, sf, cur, "\n".join(written))
    bf, _ = _read_events(mod, p.campaign)
    if _emergent_blocks(bf, p.faction):
        p.warnings.append(
            f"{campevents.EVENTS_NAME} also has an `event {EMERGENT} "
            f"{p.faction}`, which brings the faction in a second time on its "
            f"date. The Events panel deletes it.")


def _strat_text(p: HordePlan, before, after, shown: str) -> None:
    errs = _others_unchanged(before, after, p.faction)
    if errs:
        raise HordeError("descr_strat.txt would change outside "
                         f"{p.faction}'s block: " + "; ".join(errs))
    text = after.serialise()
    if text != before.serialise():
        rel = _rel(campstrat.strat_path(p.mod, p.campaign), p.mod)
        p.texts[rel] = text
        p.blocks[rel] = shown


# -- the emergence ------------------------------------------------------------


def _plan_emerge(p: HordePlan, mod, facts, sf, node, body: dict) -> None:
    people = sf.descendants_of(node, "character")
    if people:
        raise HordeError(
            f"{p.faction} already has {len(people)} character(s) in its block. "
            f"An emergent faction's people are the ones its event makes; to keep "
            f"these, start it on the map instead")
    lines, flag_moved = _set_dormant(sf, node, True)
    after = campstrat.parse_strat(serialise(sf, lines))
    if flag_moved:
        p.changes.append(f"descr_strat.txt: + {DORMANT} on {p.faction}, which "
                         f"starts off the map")
        _strat_text(p, sf, after, DORMANT)

    dates = [str(d).strip() for d in (body.get("dates") or []) if str(d).strip()]
    positions = campevents._position_texts(body.get("positions"))
    for d in dates:
        nums = [x for x in d.split() if kb.is_int(x)]
        if not nums or len(nums) != len(d.split()) or len(nums) > 2:
            p.findings.append(finding(
                "horde.date", True,
                f"`{d}` is not a date: a turn, or two turns it falls between."))
    if not dates:
        p.findings.append(finding("horde.date", True,
                                  "An event with no `date` line never fires."))
    if not positions:
        p.findings.append(finding(
            "horde.position", False,
            "No position, so nothing in the file says where the horde comes in."))
    _positions_on_map(p, facts, positions)

    bf, original = _read_events(mod, p.campaign)
    rel = _rel(campevents.events_path(mod, p.campaign), mod)
    edits = {"dates": dates, "positions": positions}
    if any(f["fatal"] for f in p.findings):
        return
    if bf is None:
        rows = campevents.new_event_lines(EMERGENT, p.faction, edits)
        text = "\r\n".join(rows) + "\r\n"
        p.changes.append(f"{rel}: a new file, with one event in it")
        p.blocks[rel] = "\n".join(rows)
    else:
        found = _emergent_blocks(bf, p.faction)
        if found:
            text, moved = campevents.render_event(bf, found[0], edits)
            p.changes += [f"{rel}: {c}" for c in moved]
            done = campevents.parse_events(text)
            b = _emergent_blocks(done, p.faction)[0]
            p.blocks[rel] = done.block_text(b)
        else:
            rows = campevents.new_event_lines(EMERGENT, p.faction, edits,
                                              campevents._pad(bf))
            text = campevents.insert_block(bf, rows)
            p.changes.append(f"{rel}: + event {EMERGENT} {p.faction}")
            p.blocks[rel] = "\n".join(rows)
    if bf is None or text != original:
        p.texts[rel] = text
        check = campevents.check_events(campevents.parse_events(text), None,
                                        p.campaign, None, None,
                                        campevents._map_size(mod))
        p.findings += [f for f in check
                       if (f.get("name") or "").lower() == p.faction.lower()]
    _plan_text(p, mod, body)
    _plan_picture(p, mod, body)


def _positions_on_map(p: HordePlan, facts, positions: Sequence[str]) -> None:
    """Sea is a warning here, not the character rule's; off the map is fatal."""
    cm = campmap.map_of(facts, p.campaign)
    if cm is None:
        return
    w, h = cm.terrain.width, cm.terrain.height
    for text in positions:
        gx, gy = campevents.parse_position(text)
        ix, iy = cm.image_xy(gx, gy)
        if not cm.terrain.in_bounds(ix, iy):
            p.findings.append(finding(
                "horde.offmap", True,
                f"{gx},{gy} is off the {w}x{h} tile grid.", x=gx, y=gy))
        elif cm.sea[iy * w + ix]:
            p.findings.append(finding(
                "horde.sea", False,
                f"{gx},{gy} is sea, and a horde is an army on land.", x=gx, y=gy))


def _plan_text(p: HordePlan, mod, body: dict) -> None:
    """``{SLOT_TITLE}`` and ``{SLOT_BODY}``: kept when there, written when not."""
    from .namekeys import NameKeyError, clean_value, loc_state
    state = loc_state(mod, campevents.EVENT_TEXT_REL)
    pairs = campevents.event_text_pairs(mod)
    tag = p.faction.upper()
    for kind, key, fallback in (("TITLE", "title", f"The {p.faction} arrive"),
                                ("BODY", "text", f"A horde of {p.faction} has "
                                                 f"appeared on the map.")):
        name = f"{tag}_{kind}"
        want = str(body.get(key) or "").strip()
        have = pairs.get(name, "")
        if not want and have:
            continue
        try:
            value = clean_value(want or fallback, f"event {kind.lower()}")
        except NameKeyError as exc:
            p.findings.append(finding("horde.text", True, str(exc)))
            continue
        if value == have:
            continue
        if not (state["txt"] or state["bin"]):
            p.findings.append(finding(
                "horde.no_text_file", False,
                f"This mod ships neither {campevents.EVENT_TEXT_REL} nor its "
                f".strings.bin, so the game's own is read and {{{name}}} is not "
                f"in it. The guide says an event with no text crashes the turn "
                f"it fires."))
            return
        p.loc_writes[name] = value
        p.changes.append(f"{state['file']}: {'~' if have else '+'} {{{name}}}")


def _plan_picture(p: HordePlan, mod, body: dict) -> None:
    """A ``<slot>.tga`` in every eventspic folder, copied from another event's."""
    dirs = campevents.eventspic_dirs(mod)
    if not dirs:
        return
    src = str(body.get("picture_from") or "").strip()
    need = [d for d in dirs if not (d / f"{p.faction}.tga").exists()]
    if not need:
        return
    if not src:
        p.findings.append(finding(
            "horde.picture", True,
            f"{len(need)} eventspic folder(s) have no {p.faction}.tga, and a "
            f"missing event picture crashes the campaign when the event fires. "
            f"Pick an event whose picture to copy."))
        return
    for d in need:
        frm = d / f"{src}.tga"
        if not frm.is_file():
            p.findings.append(finding(
                "horde.picture", True,
                f"{_rel(d, mod)} has no {src}.tga to copy."))
            continue
        p.copies.append((_rel(frm, mod), _rel(d / f"{p.faction}.tga", mod)))
        p.changes.append(f"{_rel(d, mod)}: + {p.faction}.tga, a copy of {src}.tga")


# ---------------------------------------------------------------------------
# the save


def apply(p: HordePlan) -> Dict:
    """Write every file the plan names, under one backup and one Undo."""
    import shutil

    from . import config
    from .logutil import file_op, log
    from .namekeys import _write_loc

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.touched():
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

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

    for rel, text in sorted(p.texts.items()):
        target = keep(rel)
        kb.write_text(target, text, campstrat.ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    for frm, to in p.copies:
        target = keep(to)
        shutil.copy2(Path(mod.data) / frm, target)
        file_op("COPY", target, f"<- {frm}")
    out: Dict = {"id": tid, "faction": p.faction, "mode": p.mode,
                 "files": sorted(set(p.texts) | {t for _f, t in p.copies})}
    warnings = list(p.warnings)
    if p.loc_writes:
        out["loc"] = _write_loc(mod, campevents.EVENT_TEXT_REL, p.loc_writes,
                                keep, warnings)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "horde_start",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.faction, "resolved_type": p.faction,
        "options": {"campaign": p.campaign, "start": p.mode},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": warnings,
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("HORDE START %s (%s) in %s/%s - %d change(s), id=%s", p.faction,
             p.mode, mod.name, p.campaign, len(p.changes), tid)
    out["record"] = rec
    return out
