"""Phase 72, D13. A horde start for a faction that holds nothing yet.

16j-2 makes a faction with the donor's AI, label, purse and diplomacy and
**nothing else** - no settlement, no character, no coordinate - and says so,
because two factions cannot start in the same city. That is the shape vanilla's
Mongols and Timurids already are. This is the other half: the toolkit filling
in the start rather than the modder, in one plan and one Undo.

**There are two ways a faction with no city enters a campaign, and both are
measured on the game's own files.**

* **On the map from turn one** (``start``). The faction's people are written
  into its ``descr_strat.txt`` block: a leader, an heir and more named
  characters, each at the head of an army on a free tile of one province, with
  the family line that makes the first two father and son. This is what
  Demir's ``buildStartingFactionStrat`` does, and it is the only one of the two
  a player can pick in the campaign menu.
* **Out of nowhere, later** (``emerge``). Vanilla's Mongol block is four lines -
  ``ai_label``, ``dead_until_resurrected``, ``denari``, ``denari_kings_purse`` -
  with no people at all; ``descr_sm_factions.txt`` heads it ``faction mongols,
  spawned_on_event`` in ROCSS, which kept vanilla's roster; and the invasion is
  an ``event emergent_faction mongols`` with four ``region`` lines, which the
  engine answers by raising a horde out of the faction's ``horde_*`` keys.
  Vanilla fires that event from its campaign script's ``add_events``, and the
  game's own header documents it as a ``descr_events.txt`` category, so a dated
  block in that file is the same event with no script: 19b's refusal to write
  ``campaign_script.txt`` stands untouched.

**Both modes write the horde keys** when the faction lacks them, because a
faction that holds no settlement is a horde or it is nothing: the seven keys
and a ``horde_unit`` roster, the faction's own when it has them, else the first
complete horde in the same file (ROCSS's Mongols in ROCSS), else vanilla's.
``factions.check_file`` then judges the result exactly as the Factions screen
would, which is where "part of a horde" and "a horde unit the EDU does not
declare" already live.

**A horde start fills an empty faction, and it refuses anything else.** A
faction that holds a settlement is not a horde, and one that already has people
has a leader this would duplicate; the Settlement and People panels move those,
and the refusal names them. It is 16j-2's delete rule turned round.

**Where the armies stand is the snap's own grid** (D10,
:meth:`unittransfer.stratobj.Vocabulary.snap`): not sea, not impassable land,
not a settlement or port pixel, not a fort or a watchtower, and not under any
character already in the file - inside the chosen province, nearest its
settlement first, and two tiles apart where the province has the room. Every
character written is then held against :func:`stratchar.check_character`, so a
tile the map says is wrong is reported the same way it would be in the People
panel.

**The names come out of the faction's own pool**, never invented: first names
on their own while they last, and in a campaign that writes surnames (ROCSS's
``Francesco Dandolo``) the leader and the heir share one. The four starter
traits vanilla gives a new leader (``Factionleader``, ``Factionheir``,
``LoyaltyStarter``, ``ReligionStarter``) are written only when the mod's trait
file declares them: DaC declares one of the four, and a trait the file does not
declare is the fatal finding :func:`stratchar.check_character` already has.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campevents, campmap, campstrat, factions, mapsnap, stratchar
from . import keyblock as kb
from .stratcamp import last_content
from .stratchar import Army, Spec
from .stratedit import is_int, serialise

#: The two shapes a horde start takes - see the module docstring.
MODES = ("start", "emerge")

#: The descr_strat flag that makes a faction start dead and wait for its event.
FLAG = "dead_until_resurrected"

#: The descr_sm_factions head modifier vanilla's two invaders carry.
MODIFIER = "spawned_on_event"

#: The descr_events category that raises it.
EVENT_KIND = "emergent_faction"

#: How many people one start may write. Demir's form clamps to 2-20; one is
#: allowed here because a lone leader is a legal faction, and the heir and the
#: family line are simply left out.
MAX_PEOPLE = 20

#: A stack holds twenty regiments, the general's bodyguard among them.
STACK = 20

#: Tiles between two armies of the start, where the province has the room.
#: Vanilla's scripted Mongol waves stand two to four apart.
SPACING = 2

#: The ages written, which keep the leader sixteen years or more older than the
#: heir (stratchar.PARENT_YEARS) so the family line is not a finding.
LEADER_AGE, HEIR_AGE, WIFE_AGE, OTHER_AGE = 48, 24, 44, 30

#: The traits vanilla starts a leader, an heir and everybody else on. Written
#: only when export_descr_character_traits.txt declares them.
STARTERS: Dict[str, Tuple[str, ...]] = {
    "leader": ("Factionleader", "LoyaltyStarter", "ReligionStarter"),
    "heir": ("Factionheir", "LoyaltyStarter", "ReligionStarter"),
    "": ("LoyaltyStarter", "ReligionStarter"),
}

#: Vanilla's horde, for a mod with no complete horde anywhere to copy. The
#: vanilla values the game shipped; ROCSS's Mongols differ (70, -6, 10, 250, 6,
#: 90, 0) and a file that has a horde is copied from rather than this.
FALLBACK_HORDE: Dict[str, str] = {
    "horde_min_units": "20",
    "horde_max_units": "30",
    "horde_max_units_reduction_every_horde": "10",
    "horde_unit_per_settlement_population": "250",
    "horde_min_named_characters": "2",
    "horde_max_percent_army_stack": "80",
    "horde_disband_percent_on_settlement_capture": "0",
}

#: When an emergent faction appears, as descr_events writes a date: a year
#: offset from the campaign start, or a pair the game picks between.
DEFAULT_DATE = "10 20"

_GAP = {"character_record": re.compile(r"^([\t ]*)character_record([\t ]+)"),
        "relative": re.compile(r"^([\t ]*)relative([\t ]+)")}




# ---------------------------------------------------------------------------
# what the faction has, and what the mod offers it


def _names(mod, faction: str) -> Dict[str, List[str]]:
    """The faction's pool, section by section; empty lists when there is none."""
    from . import minorfiles
    out: Dict[str, List[str]] = {"characters": [], "surnames": [], "women": []}
    path = Path(mod.data) / minorfiles.NAMES_REL
    if not path.is_file():
        return out
    try:
        nf = minorfiles.parse_names(path.read_text(campstrat.ENCODING))
    except Exception:                                  # noqa: BLE001
        return out
    for f in nf.factions:
        if f.name.lower() != faction.lower():
            continue
        for key in out:
            sec = f.section(key)
            out[key] = [e.value for e in sec.entries] if sec else []
    return out


def _sm(mod):
    """``descr_sm_factions.txt`` as records and as text, or ``(None, "")``."""
    path = factions.path_for(mod)
    if not path.is_file():
        return None, ""
    text = kb.read_text(path, factions.ENCODING)
    return factions.parse_text(text), text


def _record(rf, slot: str):
    if rf is None:
        return None
    return next((r for r in rf.records
                 if factions.slot_of(r.name) == slot.lower()), None)


def _horde(rec) -> Tuple[Dict[str, str], List[str]]:
    if rec is None:
        return {}, []
    keys = {k: str(rec.get(k)) for k in factions.HORDE_KEYS
            if rec.get(k) not in (None, "")}
    return keys, [r.value for r in rec.repeats]


def default_horde(rf, slot: str) -> Tuple[Dict[str, str], List[str], str]:
    """The horde a start writes when the form sends none, and whose it is.

    The faction's own when it is complete; else the first complete horde in
    the same file, because a mod's own numbers suit its own map; else
    vanilla's. The roster is only ever the faction's own - another faction's
    horde units are not this one's to recruit.
    """
    own = _record(rf, slot)
    keys, units = _horde(own)
    if len(keys) == len(factions.HORDE_KEYS):
        return keys, units, slot
    for rec in (rf.records if rf is not None else []):
        k, _ = _horde(rec)
        if len(k) == len(factions.HORDE_KEYS):
            return k, units, factions.slot_of(rec.name)
    return dict(FALLBACK_HORDE), units, "vanilla"


def owned_units(mod, faction: str) -> List[dict]:
    """Every unit the EDU lets this faction own, bodyguards marked."""
    try:
        units = getattr(mod.edu, "units", None) or []
    except Exception:                                  # noqa: BLE001
        return []
    low = faction.lower()
    out = []
    for u in units:
        own = [o.lower() for o in (u.ownership or [])]
        if low in own or "all" in own:
            out.append({"name": u.type, "category": u.category,
                        "general": "general_unit" in (u.attributes or [])})
    return out


def land_units(owned: Sequence[dict]) -> List[str]:
    """The regiments a horde may march with: not a bodyguard, not a ship."""
    return [u["name"] for u in owned
            if not u["general"] and u.get("category") != "ship"]


def default_army(owned: Sequence[dict], roster: Sequence[str]) -> List[str]:
    """A bodyguard the faction owns, then its horde roster, one of each."""
    guard = next((u["name"] for u in owned
                  if u["general"] and u.get("category") != "ship"), "")
    out = [guard] if guard else []
    for u in roster:
        if u and u not in out:
            out.append(u)
    return out[:STACK]


# ---------------------------------------------------------------------------
# who, and where


def pick_names(pool: Dict[str, List[str]], taken: set, count: int,
               given: Sequence[str] = ()) -> List[str]:
    """``count`` names nobody in the file already has, the given ones first.

    First names on their own while they last; with surnames in the pool the
    leader and the heir share the first free one and everybody after them
    takes a first name and a surname of their own. A name is never repeated,
    because a ``relative`` line addresses people by name and nothing else.
    """
    out: List[str] = []
    seen = {t.lower() for t in taken}

    def take(name: str) -> bool:
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
            return True
        return False

    for g in given:
        if len(out) < count and str(g).strip():
            take(str(g).strip())
    firsts = list(pool.get("characters") or [])
    surnames = list(pool.get("surnames") or [])
    if surnames:
        family = next((s for s in surnames
                       if not any(t.lower().endswith(" " + s.lower()) for t in seen)),
                      surnames[0])
        for first in firsts:
            if len(out) >= min(count, 2):
                break
            take(f"{first} {family}")
        rest = [s for s in surnames if s != family] + [family]
        for k in range(len(rest) * max(len(firsts), 1)):
            if len(out) >= count or not firsts:
                return out
            # round the surnames, so the ones outside the family are not kin
            take(f"{firsts[(k // len(rest) + len(out)) % len(firsts)]} "
                 f"{rest[k % len(rest)]}")
    for first in firsts:
        if len(out) >= count:
            break
        take(first)
    return out


def _grid(ov):
    """D10's grid: sea, ground, impassable colour, labels, province names."""
    return ov._grid()                   # the snap's own - one copy of the rule


def free_tiles(cm, sf, province: str, count: int,
               ov=None) -> Tuple[List[Tuple[int, int]], str]:
    """``count`` game tiles in ``province`` an army may start on, and a note.

    Nearest the province's settlement (else its anchor) first, then outward;
    :data:`SPACING` apart where there is room and packed closer where there is
    not. Short of ``count`` is returned as it is, with the note saying so.
    """
    from . import stratobj
    if cm is None:
        return [], "this campaign has no map to place anybody on"
    if ov is None:
        ov = stratobj.Vocabulary(getattr(cm, "mod", None), sf, cm)
    grid = _grid(ov)
    if not grid:
        return [], "the map would not index, so no tile can be judged"
    sea, ground, imp, labels, names = grid
    want = province.strip().lower()
    region = next((r for r in cm.index.regions
                   if r.name and r.name.lower() == want), None)
    if region is None:
        return [], f"{province or '(nothing)'} is not a province on this map"
    t = cm.terrain
    w, h = t.width, t.height
    held = set()
    for n in sf.of_kind("character"):
        if is_int(n.get("x")) and is_int(n.get("y")):
            held.add((int(str(n.get("x"))), int(str(n.get("y")))))
    for xy, nodes in stratobj.standing(sf).items():
        if any(n.kind in ("fort", "watchtower") for n in nodes):
            held.add(xy)
    centre = region.settlement or region.anchor

    def ok(ix: int, iy: int) -> bool:
        i = iy * w + ix
        if sea[i] or (ground and ground[i * 3:i * 3 + 3] == imp):
            return False
        if (names[labels[i]] or "").lower() != want:
            return False
        if (ix, iy) in ov.markers:
            return False
        return cm.game_xy(ix, iy) not in held

    got: List[Tuple[int, int]] = []
    for gap in (SPACING, 1):
        for dx, dy in mapsnap.offsets():
            if len(got) >= count:
                break
            ix, iy = centre[0] + dx, centre[1] + dy
            if not (0 <= ix < w and 0 <= iy < h) or not ok(ix, iy):
                continue
            g = cm.game_xy(ix, iy)
            if g in got or any(mapsnap.distance(g, o) < gap for o in got):
                continue
            got.append(g)
        if len(got) >= count:
            break
    note = ""
    if len(got) < count:
        note = (f"{province} has {len(got)} free land tile"
                f"{'' if len(got) == 1 else 's'} within {mapsnap.RADIUS} of its "
                f"settlement, and {count} were asked for")
    return got, note


# ---------------------------------------------------------------------------
# the lines


def _gap(sf, kind: str) -> Tuple[str, str]:
    for n in sf.of_kind(kind):
        m = _GAP[kind].match(sf.lines[n.start])
        if m:
            return m.group(1), m.group(2)
    return "", "\t"


def record_line(sf, name: str, age: int) -> str:
    """``character_record <name>, female, age N, alive, never_a_leader``."""
    indent, gap = _gap(sf, "character_record")
    return (f"{indent}character_record{gap}{name}, female, age {age}, alive, "
            f"never_a_leader")


def relative_line(sf, names: Sequence[str]) -> str:
    indent, gap = _gap(sf, "relative")
    return f"{indent}relative{gap}" + ", ".join(list(names) + ["end"])


def _starters(voc, rank: str) -> Tuple[List[Tuple[str, int]], List[str]]:
    want = STARTERS.get(rank, STARTERS[""])
    if not voc.have_edct:
        return [], list(want)
    have = [(t, 1) for t in want if t in voc.traits]
    return have, [t for t in want if t not in voc.traits]


def _head_with_modifier(line: str, slot: str) -> str:
    """``faction x`` -> ``faction x, spawned_on_event``, keeping gap and comment."""
    code, sep, comment = line.partition(";")
    m = re.match(r"^(\s*faction\s+)(.*?)(\s*)$", code)
    if not m:
        return line
    return (m.group(1) + f"{slot}, {MODIFIER}" + m.group(3)
            + (sep + comment if sep else ""))


# ---------------------------------------------------------------------------
# the plan


@dataclass
class HordePlan:
    """One horde start, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    faction: str = ""
    mode: str = "start"
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: ``rel -> new text`` for every file the start writes
    texts: Dict[str, str] = field(default_factory=dict)
    #: ``rel -> the lines added or rewritten``, for the preview
    blocks: Dict[str, str] = field(default_factory=dict)
    people: List[dict] = field(default_factory=list)
    #: what was used when the form sent nothing, so the form can show it
    used: dict = field(default_factory=dict)

    def summary(self) -> str:
        head = (f"horde start ({self.mode}) for {self.faction} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"faction": self.faction, "mode": self.mode,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "files": sorted(self.texts),
                "blocks": dict(self.blocks), "people": list(self.people),
                "used": dict(self.used),
                "ok": not self.errors and bool(self.texts)}


def _int(value, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _rel(mod, path: Path) -> str:
    return str(Path(path).relative_to(Path(mod.data))).replace("\\", "/")


def plan(mod, facts, body: dict) -> HordePlan:
    """Work out every file a horde start writes.

    ``body`` is ``{faction, mode, province, count, names, wife, army, exp,
    horde, horde_units, date, regions, movie, family}``, every one of them
    optional but the faction: what is not sent is what :func:`view` would have
    offered, and ``used`` says what that was.

    The campaign file is re-read here rather than taken from ``facts``, for the
    reason 16h gives: the fact table is a cache, and a writer that writes out of
    a cache writes over whatever changed under it.
    """
    campaign = str(body.get("campaign") or "") or facts.campaign
    p = HordePlan(mod=mod, campaign=campaign,
                  faction=str(body.get("faction") or "").strip(),
                  mode=str(body.get("mode") or "start").strip().lower())
    if p.mode not in MODES:
        p.errors.append(f"a horde start is {kb.and_list(list(MODES))}, not "
                        f"{p.mode!r}")
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, campmap.MapError) as exc:
        p.errors.append(str(exc))
        return p
    node = sf.faction(p.faction)
    if node is None:
        p.errors.append(f"{p.faction or '(nothing)'} has no faction block in "
                        f"{campaign}'s descr_strat.txt. New faction, in the "
                        f"Campaign panel, makes one")
        return p
    p.faction = node.name
    places = sf.children_of(node, "settlement")
    people = stratchar.characters_of(sf, node)
    if places or people:
        held = []
        if places:
            held.append(f"{len(places)} settlement{'' if len(places) == 1 else 's'}")
        if people:
            held.append(f"{len(people)} character{'' if len(people) == 1 else 's'}")
        p.errors.append(
            f"{p.faction} already holds {' and '.join(held)}. A horde start "
            f"fills a faction that holds nothing - the Settlement and People "
            f"panels move what it has")
        return p

    rf, sm_text = _sm(mod)
    rec = _record(rf, p.faction)
    keys, roster, source = default_horde(rf, p.faction)
    sent = body.get("horde")
    if isinstance(sent, dict):
        keys = {k: str(sent[k]).strip() for k in factions.HORDE_KEYS
                if str(sent.get(k, "")).strip() != ""} or keys
    if body.get("horde_units") is not None:
        roster = [str(u).strip() for u in body["horde_units"] if str(u).strip()]
    owned = owned_units(mod, p.faction)
    if not roster:
        roster = land_units(owned)[:9]
    p.used.update(horde=dict(keys), horde_units=list(roster),
                  horde_from=source)
    if p.mode == "emerge" and not roster:
        # the engine raises an emergent faction out of its horde_unit lines and
        # nothing else, so an empty roster is an event that raises nobody
        p.errors.append(f"{p.faction} has no horde_unit roster and owns no unit "
                        f"the EDU names, so its event would raise an empty "
                        f"horde - name the units it arrives with")
        return p

    voc = stratchar.Vocabulary(facts, sf) if p.mode == "start" else None
    if p.mode == "start":
        lines = _plan_start(p, sf, node, facts, body, keys, roster, owned, voc)
    else:
        lines = _plan_emerge(p, sf, node, body)
    if p.errors:
        return p

    text = serialise(sf, lines)
    if text != sf.serialise():
        p.texts[_rel(mod, sf.path)] = text
    done = campstrat.parse_strat(text)
    p.errors += _guard(sf, done, p)
    if p.errors:
        return p
    if p.mode == "start":
        cm = campmap.map_of(facts, campaign)
        said: Dict[Tuple[str, str], dict] = {}
        for person in p.people:
            spec = person.pop("_spec")
            for f in (stratchar.check_character(voc, spec, cm)
                      + stratchar.check_pool(voc, p.faction, spec.name)):
                # every army is the same army, so one finding about it is said
                # once and names everybody it is true of
                key = (f.get("code", ""), f["message"])
                if key in said:
                    said[key]["who"] += ", " + spec.name
                else:
                    said[key] = dict(f, who=spec.name)
                    p.findings.append(said[key])
        for f in p.findings:
            if f["who"].count(",") + 1 == len(p.people) > 1:
                f["who"] = f"all {len(p.people)}"
        p.findings += stratchar.check_faction(done, done.faction(p.faction), voc)

    _plan_sm(p, rf, rec, sm_text, keys, roster)
    if p.errors:
        return p
    for f in p.findings:
        into = p.errors if f["fatal"] else p.warnings
        if f["message"] not in into:
            into.append(f["message"])
    if not p.texts and not p.errors:
        p.errors.append("nothing to change")
    return p


def _plan_start(p: HordePlan, sf, node, facts, body, keys, roster,
                owned, voc) -> List[str]:
    """The faction's people, inserted where its last line of content ends."""
    mod = p.mod
    minimum = _int(keys.get("horde_min_named_characters"), 0)
    count = _int(body.get("count"), max(3, minimum))
    if not 1 <= count <= MAX_PEOPLE:
        p.errors.append(f"a horde start writes 1 to {MAX_PEOPLE} people, "
                        f"not {body.get('count')}")
        return sf.lines
    if minimum and count < minimum:
        p.warnings.append(
            f"horde_min_named_characters is {minimum} and this start writes "
            f"{count}; the engine tops a horde up to its minimum from the pool")
    province = str(body.get("province") or "").strip()
    cm = campmap.map_of(facts, p.campaign)
    given = body.get("positions")
    if given:
        try:
            tiles = [(int(a), int(b)) for a, b in given][:count]
        except (TypeError, ValueError):
            p.errors.append("positions are pairs of whole numbers")
            return sf.lines
        note = ""
    else:
        if not province:
            p.errors.append("choose the province the horde starts in")
            return sf.lines
        tiles, note = free_tiles(cm, sf, province, count)
    if len(tiles) < count:
        p.errors.append(note or f"{len(tiles)} tiles for {count} people")
        return sf.lines

    pool = _names(mod, p.faction)
    taken = {n.name for n in sf.of_kind("character")}
    taken |= {n.name for n in sf.of_kind("character_record")}
    names = pick_names(pool, taken, count, body.get("names") or ())
    if len(names) < count:
        p.errors.append(
            f"{p.faction}'s pool in descr_names.txt gives {len(names)} unused "
            f"name{'' if len(names) == 1 else 's'} for {count} people - add "
            f"names to the pool, or type them in")
        return sf.lines
    family = count >= 2 and body.get("family", True) is not False
    wife = str(body.get("wife") or "").strip()
    if family and not wife:
        used = {n.lower() for n in taken} | {n.lower() for n in names}
        wife = next((w for w in pool.get("women") or []
                     if w.lower() not in used), "")
    if family and not wife:
        family = False
        p.warnings.append(f"{p.faction}'s pool has no unused woman's name, so "
                          f"the leader and the heir are written with no family "
                          f"line")

    army_sent = body.get("army")
    if army_sent:
        units = [str(a.get("unit") if isinstance(a, dict) else a).strip()
                 for a in army_sent]
        units = [u for u in units if u]
    else:
        units = default_army(owned, roster)
    if not units:
        p.errors.append("an army needs at least one regiment, and this faction "
                        "owns no unit the EDU names and has no horde roster")
        return sf.lines
    if len(units) > STACK:
        p.errors.append(f"an army holds {STACK} regiments and this one lists "
                        f"{len(units)}")
        return sf.lines
    exp = _int(body.get("exp"), 0)
    p.used.update(count=count, province=province, names=list(names),
                  wife=wife if family else "", army=list(units), exp=exp,
                  positions=[list(t) for t in tiles], family=family)

    dropped: set = set()
    block: List[str] = [""]
    for i, (name, (x, y)) in enumerate(zip(names, tiles)):
        rank = "leader" if i == 0 else "heir" if i == 1 else ""
        traits, missing = _starters(voc, rank)
        dropped.update(missing)
        age = LEADER_AGE if i == 0 else HEIR_AGE if i == 1 else OTHER_AGE + i
        spec = Spec(name=name, type="named character", gender="male",
                    rank=rank, age=age, x=x, y=y, traits=traits,
                    army=[Army(unit=u, exp=exp) for u in units])
        block += stratchar.new_character(sf, node, spec)
        p.people.append({"name": name, "rank": rank, "age": age, "x": x,
                         "y": y, "_spec": spec})
    if family:
        block.append(record_line(sf, wife, WIFE_AGE))
        block.append(relative_line(sf, [names[0], wife, names[1]]))
    elif block[-1] == "":
        block.pop()
    if dropped:
        p.warnings.append(
            ("export_descr_character_traits.txt does not declare "
             + kb.and_list(sorted(dropped)) + ", so " +
             ("it is" if len(dropped) == 1 else "they are") + " left off")
            if voc.have_edct else
            "export_descr_character_traits.txt is not on disk, so no starter "
            "trait is written - the leader and heir traits are the mod's to add")

    at = last_content(sf, node) + 1
    rel = _rel(p.mod, sf.path)
    p.blocks[rel] = "\n".join(block).strip("\n")
    p.changes.append(f"{count} named character{'' if count == 1 else 's'} for "
                     f"{p.faction} in {province or 'the given tiles'}, each "
                     f"leading {len(units)} regiment{'' if len(units) == 1 else 's'}")
    p.changes += [f"  {q['name']}{' (' + q['rank'] + ')' if q['rank'] else ''}, "
                  f"age {q['age']}, at {q['x']},{q['y']}" for q in p.people]
    if family:
        p.changes.append(f"{wife} as the leader's wife, and {names[1]} their son")
    if node.get(FLAG):
        p.changes.append(f"- {FLAG}, which would keep these people off the map")
        drop = node.field_lines.get(FLAG)
        out = sf.lines[:at] + block + sf.lines[at:]
        return out[:drop] + out[drop + 1:] if drop is not None else out
    return sf.lines[:at] + block + sf.lines[at:]


def _plan_emerge(p: HordePlan, sf, node, body) -> List[str]:
    """The flag in descr_strat, and the event in descr_events."""
    date = str(body.get("date") or DEFAULT_DATE).strip()
    regions = [str(r).strip() for r in (body.get("regions") or [])
               if str(r).strip()]
    province = str(body.get("province") or "").strip()
    if not regions and province:
        regions = [province]
    if not regions:
        p.errors.append("choose at least one province for the horde to appear "
                        "in - vanilla's Mongols name four")
        return sf.lines
    movie = str(body.get("movie") or "").strip()
    p.used.update(date=date, regions=list(regions), movie=movie)

    edits = {"category": EVENT_KIND, "dates": [date], "regions": regions}
    if movie:
        edits["movie"] = movie
    ev = campevents.plan(p.mod, {"what": "events", "campaign": p.campaign,
                                 "action": "add", "name": p.faction,
                                 "edits": edits})
    p.errors += ev.errors
    if p.errors:
        return sf.lines
    p.findings += [dict(f, who="descr_events.txt") for f in ev.findings
                   if (f.get("name") or "").lower() == p.faction.lower()]
    p.warnings += [w for w in ev.warnings if w not in p.warnings
                   and not any(w == f["message"] for f in ev.findings)]
    if ev.text and ev.path is not None:
        rel = _rel(p.mod, ev.path)
        p.texts[rel] = ev.text
        p.blocks[rel] = ev.block
        p.changes.append(f"+ event {EVENT_KIND} {p.faction}, date {date}, in "
                         + kb.and_list(regions))

    if node.get(FLAG):
        return sf.lines
    after = node.field_lines.get("ai_label")
    at = (after + 1) if after is not None else node.start + 1
    indent = re.match(r"^([\t ]*)", sf.lines[after if after is not None
                                             else node.start]).group(1)
    p.changes.append(f"+ {FLAG} in {p.faction}'s campaign block, so it waits "
                     f"for its event")
    p.blocks.setdefault(_rel(p.mod, sf.path), indent + FLAG)
    return sf.lines[:at] + [indent + FLAG] + sf.lines[at:]


def _plan_sm(p: HordePlan, rf, rec, original: str, keys, roster) -> None:
    """The horde keys and roster, and the emerge mode's head modifier."""
    if rf is None:
        p.warnings.append(f"{factions.REL} is not on disk, so the horde keys "
                          f"cannot be written - the engine has no horde to "
                          f"raise for {p.faction}")
        return
    if rec is None:
        p.errors.append(f"{p.faction} has no record in {factions.REL}. The "
                        f"Factions screen's clone makes one")
        return
    base = rf.block_text(rec)
    have, units = _horde(rec)
    edits: Dict[str, object] = {}
    for k in factions.HORDE_KEYS:
        if keys.get(k) not in (None, "") and have.get(k) != keys[k]:
            edits[k] = keys[k]
    if roster and roster != units:
        edits["units"] = list(roster)
    try:
        block = factions.render_block(base, edits) if edits else base
    except factions.FactionError as e:
        p.errors.append(e.message)
        return
    if p.mode == "emerge" and factions.modifier_of(rec.name) != MODIFIER:
        if factions.modifier_of(rec.name):
            p.warnings.append(
                f"{p.faction}'s head line already carries "
                f"`{factions.modifier_of(rec.name)}`, so `{MODIFIER}` is not "
                f"added beside it")
        else:
            head, nl, rest = block.partition("\n")
            block = _head_with_modifier(head, factions.slot_of(rec.name)) + nl + rest
    if block == base:
        return
    text = rf.replace(rec.start, rec.end, block)
    if text == original:
        return
    p.texts[factions.REL] = text
    p.blocks[factions.REL] = block.strip("\r\n")
    p.changes += [f"{factions.REL}: {c}" for c in kb.diff(base, block)]
    after = factions.parse_text(text)
    now = _record(after, p.faction)
    if now is None:
        p.errors.append(f"after this save {factions.REL} has no {p.faction}")
        return
    # the Factions screen's own findings, which that screen shows as warnings:
    # a horde missing a key loads, and fights with the engine's defaults
    p.findings += [dict(f, code=f.get("kind", ""), fatal=False, who=factions.REL)
                   for f in factions.check_file(after, p.mod)
                   if factions.slot_of(f.get("name") or "") == p.faction.lower()]


def _guard(before, after, p: HordePlan) -> List[str]:
    """What the splice did that it was never asked to do.

    Every other faction's block has to come back byte for byte, and this one
    has to have gained exactly the people, the record and the family line it
    was given - or the flag and nothing else.
    """
    out: List[str] = []
    for node in before.of_kind("faction"):
        if node.name.lower() == p.faction.lower():
            continue
        was = before.lines[node.start:node.end + 1]
        twin = after.faction(node.name)
        now = after.lines[twin.start:twin.end + 1] if twin is not None else None
        if was != now:
            out.append(f"this would change {node.name}'s block, and a horde "
                       f"start writes {p.faction}'s")
    if before.rosters != after.rosters or before.globals != after.globals:
        out.append("this would change the campaign's header or its rosters")
    mine = after.faction(p.faction)
    if mine is None:
        return out + [f"after this save there is no {p.faction} block"]
    got = len(stratchar.characters_of(after, mine))
    want = len(p.people) if p.mode == "start" else 0
    if got != want:
        out.append(f"this would leave {p.faction} with {got} characters, and "
                   f"it was given {want}")
    if p.mode == "emerge" and not mine.get(FLAG):
        out.append(f"{p.faction} does not read as {FLAG} after this save")
    return out


# ---------------------------------------------------------------------------
# the save


def apply(p: HordePlan) -> dict:
    """Write every file of the start, with one backup and one Undo."""
    import shutil
    import time

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.texts:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    encodings = {factions.REL: factions.ENCODING}
    for rel, text in sorted(p.texts.items()):
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
        kb.write_text(target, text, encodings.get(rel, campstrat.ENCODING))
        file_op("WRITE", target, f"{len(text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        "action": "horde",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.faction, "resolved_type": p.faction,
        "options": {"campaign": p.campaign, "faction": p.faction,
                    "what": p.mode, "files": sorted(p.texts)},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("HORDE %s %s in %s/%s - %d file(s), id=%s", p.mode, p.faction,
             mod.name, p.campaign, len(p.texts), tid)
    return {"id": tid, "faction": p.faction, "campaign": p.campaign,
            "files": sorted(p.texts), "record": rec}


# ---------------------------------------------------------------------------
# the form


def view(mod, facts, faction: str) -> dict:
    """What the form opens on: the faction's state and every picker it needs.

    The defaults are a dry plan of each mode, so what the form shows before a
    single box is touched is exactly what a save would write.
    """
    sf = getattr(facts, "strat", None)
    if sf is None:
        raise campmap.MapError(f"{facts.strat_rel} could not be read")
    node = sf.faction(faction)
    if node is None:
        raise campmap.MapError(f"no faction called {faction!r} in "
                               f"{facts.campaign}'s descr_strat.txt")
    rf, _ = _sm(mod)
    rec = _record(rf, faction)
    keys, roster = _horde(rec)
    cm = campmap.map_of(facts)
    provinces: List[str] = []
    if cm is not None:
        try:
            provinces = sorted((r.name for r in cm.index.regions if r.name),
                               key=str.lower)
        except campmap.MapError:
            provinces = []
    owners = {}
    for s in sf.of_kind("settlement"):
        region = str(s.get("region") or "")
        f = stratchar.faction_of(sf, s)
        if region and f is not None:
            owners[region.lower()] = f.name
    # a province held by rebels, or by nobody, is the natural place for a horde
    first = next((pv for pv in provinces
                  if owners.get(pv.lower(), "slave") == "slave"),
                 provinces[0] if provinces else "")
    bf, _ = campevents.read_events(mod, facts.campaign)
    events = [{"kind": b.kind, "name": b.name, "line": b.head_line + 1,
               "dates": b.all("date"), "regions": b.all("region")}
              for b in bf.blocks
              if b.kind == EVENT_KIND and b.name.lower() == faction.lower()]
    pool = _names(mod, faction)
    dry = {m: plan(mod, facts, {"faction": faction, "mode": m,
                                "province": first,
                                "campaign": facts.campaign}).payload()
           for m in MODES}
    places = sf.children_of(node, "settlement")
    people = stratchar.characters_of(sf, node)
    return {
        "faction": node.name,
        "label": facts.faction_label(node.name),
        "campaign": facts.campaign,
        "empty": not places and not people,
        "holds": {"settlements": len(places), "characters": len(people)},
        "dead_until_resurrected": bool(node.get(FLAG)),
        "spawned_on_event": (factions.modifier_of(rec.name) == MODIFIER
                             if rec is not None else False),
        "has_sm": rec is not None,
        "horde": keys, "horde_units": roster,
        "complete_horde": len(keys) == len(factions.HORDE_KEYS),
        "events": events,
        "pool": {k: len(v) for k, v in pool.items()},
        "provinces": provinces,
        "owners": owners,
        "province": first,
        "units": owned_units(mod, faction),
        "horde_keys": list(factions.HORDE_KEYS),
        "modes": list(MODES),
        "limits": {"people": MAX_PEOPLE, "stack": STACK},
        "defaults": dry,
    }
