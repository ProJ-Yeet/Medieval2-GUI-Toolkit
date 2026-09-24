"""Phase 72, D13. A horde start for a faction that holds nothing.

16j-2 makes a faction with no settlement and no character, and says in as many
words that it is the shape vanilla's Mongols and Timurids already are: a
``dead_until_resurrected`` block that appears by script. This is the other
half, the script. **Two files, one plan, one Undo**:

* ``descr_strat.txt`` - the block gets ``dead_until_resurrected`` when it does
  not already have it, through 16j's own faction save
  (:func:`unittransfer.stratcamp.plan_campaign`, ``what: faction``), so the
  guard that walks the two files is the one every other flag edit passes. A
  faction that still holds a settlement or a person is not given the flag -
  what the script then spawns is reinforcements, and the plan says so.
* ``campaign_script.txt`` - one monitor that fires on the rebels' turn once
  ``I_TurnNumber`` reaches the turn asked for, spawns each army with
  ``spawn_army`` and terminates itself.

**This is the first thing in the toolkit that writes the campaign script, and
19b's refusal still stands.** That refusal is about *rewriting* the script: a
rename would have to find every line that names a thing in a grammar nothing
here parses, and one it missed is a dead name. None of that applies to adding a
block. The block is written whole, between two marker comments
(:data:`OPEN` and :data:`CLOSE`), in front of the script's last
``wait_monitors``, and **no line of the script outside the markers is ever
changed** - the guard compares the head and the tail line for line and refuses
the save if either moved. The markers are what make it editable and removable
again: this module reads back only what it wrote. A script whose shape it
cannot place a block in (no ``script`` first, no ``wait_monitors`` before its
``end_script``, a marker left open) is refused with the reason, never guessed
at.

**What is checked is what the engine would fall over on**, through the
readers that already check the same values in ``descr_strat.txt``:
:func:`unittransfer.stratchar.check_character` for each army's general, his
tile and his regiments; :func:`~unittransfer.stratchar.check_pool` for a named
character's name; :class:`unittransfer.stratobj.Vocabulary` for impassable
ground and a settlement pixel. A spawned army reads back through
:func:`unittransfer.spawns.scan_text`, the 37a reader, so the markers layer
draws it the moment it is saved and a block this module cannot read back is a
block it does not write.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campmap, campstrat, spawns, stratcamp, stratchar
from .keyblock import newline_of, read_text, write_text
from .stratedit import finding, is_int

ENCODING = "latin-1"

#: The script this writes when the campaign has none: the first name
#: :data:`unittransfer.renames.SCRIPT_NAMES` looks for, which is the one the
#: engine runs for a campaign folder by itself.
DEFAULT_SCRIPT = spawns.SCRIPT_NAMES[0]

#: The two comment lines a block is written between, and read back by.
OPEN = ";;; horde start: {faction} - written by the toolkit's Horde start tab, which reads this block back"
CLOSE = ";;; end horde start: {faction}"
_OPEN = re.compile(r"^\s*;;;\s*horde start:\s*([A-Za-z0-9_]+)", re.I)
_CLOSE = re.compile(r"^\s*;;;\s*end horde start:\s*([A-Za-z0-9_]+)", re.I)
_TURN = re.compile(r"\bI_TurnNumber\s*(?:>=|=)\s*(\d+)", re.I)

#: The three character types ``spawn_army`` is given in the scripts measured:
#: 2,510 blocks over the three installed campaigns (37a).
TYPES = ("named character", "general", "admiral")

#: A stack holds twenty regiments, the general's bodyguard among them.
STACK = 20

#: The flag a faction with nothing on the map needs to outlive turn one.
DEAD = "dead_until_resurrected"


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode(ENCODING, "replace")).hexdigest()[:16]


def _code(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _head(line: str) -> str:
    bare = _code(line)
    return bare.split()[0].lower() if bare else ""


# ---------------------------------------------------------------------------
# the script's shape


def script_path(mod, campaign: str) -> Tuple[Path, bool]:
    """The script a block goes into, and whether it is already on disk."""
    have = spawns.script_paths(mod, campaign)
    if have:
        return have[0], True
    home = (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
            / campstrat.campaign_rel(campaign))
    return home / DEFAULT_SCRIPT, False


@dataclass
class Shape:
    """Where a block can go in one script, and the blocks already there."""

    lines: List[str] = field(default_factory=list)
    #: the line a new block goes in front of - the last ``wait_monitors``
    insert: int = -1
    #: faction -> (first line, last line) of each marked block, 0-based
    blocks: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    error: str = ""


def shape_of(text: str) -> Shape:
    """Read where a block may go, and refuse a script it cannot be sure of."""
    sh = Shape(lines=text.split("\n"))
    lines = sh.lines
    code = [(i, _head(ln)) for i, ln in enumerate(lines) if _code(ln)]
    if not code or code[0][1] != "script":
        sh.error = ("the script does not open with `script`, so this is not a "
                    "shape anything here can add a monitor to")
        return sh
    ends = [i for i, h in code if h == "end_script"]
    if not ends:
        sh.error = "the script has no `end_script`, so there is no end to put a monitor before"
        return sh
    waits = [i for i, h in code if h == "wait_monitors" and i < ends[-1]]
    if not waits:
        sh.error = ("the script has no `wait_monitors` before its `end_script`, "
                    "so no monitor in it would ever fire")
        return sh
    sh.insert = waits[-1]
    open_at: Dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = _OPEN.match(ln)
        if m:
            f = m.group(1).lower()
            if f in open_at or f in sh.blocks:
                sh.error = f"line {i + 1}: a second horde start for {f}"
                return sh
            open_at[f] = i
            continue
        m = _CLOSE.match(ln)
        if m:
            f = m.group(1).lower()
            if f not in open_at:
                sh.error = f"line {i + 1}: a horde start for {f} is closed and was never opened"
                return sh
            sh.blocks[f] = (open_at.pop(f), i)
    if open_at:
        f, i = next(iter(open_at.items()))
        sh.error = (f"line {i + 1}: the horde start for {f} is never closed, so "
                    f"nothing here can tell where it ends - put its end marker "
                    f"back in Raw text first")
        return sh
    for f, (a, b) in sh.blocks.items():
        if a <= sh.insert <= b:
            sh.error = f"the script's last `wait_monitors` is inside the horde start for {f}"
    return sh


# ---------------------------------------------------------------------------
# a horde, as values


@dataclass
class Army:
    name: str = ""
    type: str = "named character"
    age: object = 30
    x: object = None
    y: object = None
    units: List[stratchar.Army] = field(default_factory=list)

    def payload(self) -> dict:
        return {"name": self.name, "type": self.type, "age": self.age,
                "x": self.x, "y": self.y,
                "units": [u.payload() for u in self.units]}


def armies_from_body(raw) -> List[Army]:
    out: List[Army] = []
    for a in raw or []:
        out.append(Army(
            name=" ".join(str(a.get("name") or "").split()),
            type=str(a.get("type") or "named character").strip().lower(),
            age=a.get("age", 30), x=a.get("x"), y=a.get("y"),
            units=[stratchar.Army(unit=" ".join(str(u.get("unit") or "").split()),
                                  exp=u.get("exp", 0), armour=u.get("armour", 0),
                                  weapon_lvl=u.get("weapon_lvl", 0))
                   for u in (a.get("units") or [])]))
    return out


def read_block(lines: List[str], span: Tuple[int, int]) -> dict:
    """A block this module wrote, as the form holds it."""
    text = "\n".join(ln.rstrip("\r") for ln in lines[span[0]:span[1] + 1])
    m = _TURN.search(text)
    armies = []
    for sp in spawns.scan_text(text):
        if sp.kind != "army":
            continue
        age = re.search(r"\bage\s+(\d+)", text.split("\n")[sp.char_line - 1]) \
            if sp.char_line else None
        # the three numbers after each unit, which 37a's reader does not keep
        body = text.split("\n")[sp.line:]
        nums = []
        for ln in body:
            if _head(ln) == "end":
                break
            if _head(ln) == "unit":
                got = {k: int(v) for k, v in re.findall(
                    r"\b(exp|armour|weapon_lvl)\s+(-?\d+)", ln)}
                nums.append(got)
        armies.append({"name": sp.name, "type": sp.type,
                       "age": int(age.group(1)) if age else 30,
                       "x": sp.x, "y": sp.y,
                       "units": [{"unit": u, "exp": n.get("exp", 0),
                                  "armour": n.get("armour", 0),
                                  "weapon_lvl": n.get("weapon_lvl", 0)}
                                 for u, n in zip(sp.units, nums)]})
    return {"turn": int(m.group(1)) if m else 0, "armies": armies,
            "line": span[0] + 1, "end": span[1] + 1}


def render_block(faction: str, turn: int, armies: List[Army], nl: str) -> List[str]:
    """The block, written in the shape 37a measured on every real spawn: tabs
    between keyword and value, a comma-separated ``character`` line carrying
    the coordinate, and a ``unit`` line per regiment with its three numbers."""
    eol = "\r" if nl == "\r\n" else ""
    out = [OPEN.format(faction=faction),
           "monitor_event FactionTurnStart FactionType slave",
           f"\tand I_TurnNumber = {turn}",
           ""]
    for a in armies:
        tail = ", family" if a.type == "named character" else ""
        out += ["\tspawn_army",
                f"\t\tfaction\t{faction}",
                f"\t\tcharacter\t{a.name}, {a.type}, age {int(str(a.age))}, "
                f"x {int(str(a.x))}, y {int(str(a.y))}{tail}"]
        for u in a.units:
            out.append(f"\t\tunit\t\t{u.unit}\t\texp {int(str(u.exp))} "
                       f"armour {int(str(u.armour))} weapon_lvl {int(str(u.weapon_lvl))}")
        out += ["\tend", ""]
    out += ["\tterminate_monitor", "end_monitor", CLOSE.format(faction=faction)]
    return [ln + eol for ln in out]


# ---------------------------------------------------------------------------
# the checks


def _faction_state(sf, name: str) -> dict:
    node = sf.faction(name)
    if node is None:
        return {}
    return {"name": node.name,
            "settlements": len(sf.children_of(node, "settlement")),
            "characters": len(sf.descendants_of(node, "character")),
            "flags": [k for k in campstrat.FACTION_FLAGS if node.get(k)]}


def _horde_keys(mod) -> Dict[str, dict]:
    """``descr_sm_factions.txt``: which factions carry horde settings."""
    from . import factions as fac
    try:
        rf = fac.parse_file(fac.path_for(mod))
    except (OSError, ValueError):
        return {}
    return {r.name.lower(): {"keys": len([k for k in fac.HORDE_KEYS if k in r.lines]),
                             "units": len(r.repeats)}
            for r in rf.records}


def check_armies(facts, sf, faction: str, turn, armies: List[Army]) -> List[dict]:
    """Everything wrong with a horde before it is written, fatal first."""
    from . import stratobj
    out: List[dict] = []
    if not is_int(turn) or int(str(turn)) < 0:
        out.append(finding("horde.turn", True,
                           f"the turn is {turn!r}; it is a whole number from 0, "
                           f"which is how I_TurnNumber counts the first turn"))
    if not armies:
        out.append(finding("horde.empty", True, "a horde needs at least one army"))
        return out
    cm = campmap.map_of(facts)
    cvoc = stratchar.Vocabulary(facts, sf)
    try:
        ovoc = stratobj.Vocabulary(facts.mod, sf, cm)
    except Exception:                                           # noqa: BLE001
        ovoc = None
    owners: Dict[str, List[str]] = {}
    try:
        owners = {u.type: [o.lower() for o in u.ownership] for u in facts.mod.edu.units}
    except Exception:                                           # noqa: BLE001
        owners = {}
    seen: Dict[Tuple[int, int], int] = {}
    placed = {}
    for c in sf.of_kind("character"):
        if is_int(c.get("x")) and is_int(c.get("y")):
            placed.setdefault((int(str(c.get("x"))), int(str(c.get("y")))), c.name)
    for n, a in enumerate(armies, 1):
        who = f"army {n}" + (f" ({a.name})" if a.name else "")
        if a.type not in TYPES:
            out.append(finding("horde.type", True,
                               f"{who}: {a.type or '(nothing)'} does not lead a "
                               f"spawned army; the three are " + ", ".join(TYPES)))
            continue
        if not a.units:
            out.append(finding("horde.no_units", True,
                               f"{who} has no regiment, so there is no army to spawn"))
        if len(a.units) > STACK:
            out.append(finding("horde.stack", True,
                               f"{who} has {len(a.units)} regiments and a stack "
                               f"holds {STACK}"))
        if "," in a.name or ";" in a.name:
            out.append(finding("horde.name", True,
                               f"{who}: a name cannot carry a comma or a ;, since "
                               f"the character line is split on commas"))
        for u in a.units:
            if "," in u.unit or ";" in u.unit:
                out.append(finding("horde.unit", True,
                                   f"{who}: {u.unit!r} cannot be a unit name"))
            if is_int(u.exp) and not 0 <= int(str(u.exp)) <= 9:
                out.append(finding("horde.exp", True,
                                   f"{who}: {u.unit} is given experience "
                                   f"{u.exp}, and it runs 0 to 9"))
            own = owners.get(u.unit)
            if own and faction.lower() not in own and "all" not in own:
                out.append(finding(
                    "horde.owner", False,
                    f"{who}: {u.unit}'s ownership line does not name {faction}, "
                    f"so the battle map may have no model to draw it with"))
        spec = stratchar.Spec(name=a.name, type=a.type, gender="male", age=a.age,
                              x=a.x, y=a.y, army=list(a.units))
        for f in stratchar.check_character(cvoc, spec, cm):
            if f["code"] == "char.gender":
                continue
            out.append(dict(f, message=f"{who}: {f['message']}"))
        if a.type == "named character":
            out += [dict(f, message=f"{who}: {f['message']}")
                    for f in stratchar.check_pool(cvoc, faction, a.name)]
        if not (is_int(a.x) and is_int(a.y)):
            continue
        xy = (int(str(a.x)), int(str(a.y)))
        if xy in seen:
            out.append(finding("horde.shared", False,
                               f"{who} is spawned on {xy[0]},{xy[1]} with army "
                               f"{seen[xy]}; the engine moves one of them", x=xy[0], y=xy[1]))
        seen.setdefault(xy, n)
        if xy in placed:
            out.append(finding("horde.occupied", False,
                               f"{who}: {placed[xy]} starts on {xy[0]},{xy[1]} in "
                               f"descr_strat.txt", x=xy[0], y=xy[1]))
        if ovoc is not None and ovoc.cm is not None and ovoc.in_bounds(*xy):
            g = ovoc.ground(*xy) if ovoc.sea(*xy) is False else None
            if g is not None and g["code"] == "impassable_land":
                out.append(finding("horde.ground", True,
                                   f"{who}: {xy[0]},{xy[1]} is {g['name']}, which "
                                   f"no army can stand on", x=xy[0], y=xy[1]))
            mark = ovoc.marker(*xy)
            if mark:
                out.append(finding("horde.marker", False,
                                   f"{who}: {xy[0]},{xy[1]} is {mark} pixel; a "
                                   f"spawned army belongs beside a settlement, "
                                   f"not on it", x=xy[0], y=xy[1]))
    if not any(a.type == "named character" for a in armies):
        out.append(finding("horde.leaderless", False,
                           "no army is led by a named character, so nobody joins "
                           "the family tree the faction's leader comes from"))
    out.sort(key=lambda f: not f["fatal"])
    return out


# ---------------------------------------------------------------------------
# what the tab shows


def detail(facts) -> dict:
    """Every faction the campaign has, which of them could start as a horde,
    and the starts this module has already written."""
    mod = facts.mod
    campaign = facts.campaign
    sf = campstrat.read_strat(mod, campaign)
    path, exists = script_path(mod, campaign)
    text = read_text(path, ENCODING) if exists else ""
    sh = shape_of(text) if exists else Shape()
    starts = {f: read_block(sh.lines, span) for f, span in sh.blocks.items()}
    horde = _horde_keys(mod)
    scripted: Dict[str, int] = {}
    for sp in spawns.scan_text(text) if text else []:
        if sp.faction:
            scripted[sp.faction.lower()] = scripted.get(sp.faction.lower(), 0) + 1
    rows = []
    for node in sf.of_kind("faction"):
        st = _faction_state(sf, node.name)
        low = node.name.lower()
        mine = len(starts.get(low, {}).get("armies", []))
        rows.append({**st, "start": starts.get(low),
                     "scripted": scripted.get(low, 0) - mine,
                     "horde_keys": horde.get(low, {}).get("keys", 0),
                     "horde_units": horde.get(low, {}).get("units", 0),
                     "homeless": not st["settlements"] and not st["characters"]})
    cvoc = stratchar.Vocabulary(facts, sf)
    rel = path.relative_to(Path(mod.data)).as_posix()
    return {"campaign": campaign, "script": rel, "exists": exists,
            "sig": _sig(text), "error": sh.error if exists else "",
            "factions": rows,
            "types": list(TYPES), "stack": STACK,
            "units": [{"name": n, "general": n in cvoc.bodyguards}
                      for n in cvoc.unit_names()],
            "pool": dict(cvoc.pool)}


# ---------------------------------------------------------------------------
# the save


@dataclass
class HordePlan:
    mod: object = None
    campaign: str = ""
    faction: str = ""
    action: str = "write"
    script_rel: str = ""
    script_text: str = ""
    script_new: bool = False
    strat: Optional[object] = None           # a stratcamp.CampPlan, or None
    block: str = ""
    findings: List[dict] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def files(self) -> List[str]:
        out = [self.script_rel] if self.script_text else []
        if self.strat is not None:
            out.append(f"{campstrat.CAMPAIGN_DIR_REL}/{self.campaign}/"
                       f"{campstrat.STRAT_NAME}")
        return out

    def payload(self) -> dict:
        return {"faction": self.faction, "action": self.action,
                "files": self.files(), "block": self.block,
                "findings": list(self.findings), "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "new_script": self.script_new,
                "ok": not self.errors and bool(self.script_text)}


ACTIONS = ("write", "remove")


def plan(mod, facts, body: dict) -> HordePlan:
    """``{campaign, faction, action, turn, armies, flag, sig}``.

    ``action`` is ``write`` (a new start, or the faction's own marked block
    replaced where it stands) or ``remove`` (the marked block taken out, and
    nothing else). ``flag`` - on unless it is sent false - gives the faction
    ``dead_until_resurrected`` when it holds nothing and lacks it.
    """
    campaign = str(body.get("campaign") or "") or facts.campaign
    campaign = campstrat.campaign_rel(campaign)
    p = HordePlan(mod=mod, campaign=campaign,
                  faction=str(body.get("faction") or "").strip(),
                  action=str(body.get("action") or "write").lower())
    if p.action not in ACTIONS:
        p.errors.append(f"no such action {p.action!r}; the two are " + ", ".join(ACTIONS))
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError) as exc:
        p.errors.append(str(exc))
        return p
    st = _faction_state(sf, p.faction)
    if not st:
        p.errors.append(f"{p.faction or '(nothing)'} has no faction block in "
                        f"{campaign}'s descr_strat.txt. New faction, on the tab "
                        f"beside this one, writes one")
        return p
    p.faction = st["name"]
    low = p.faction.lower()

    path, exists = script_path(mod, campaign)
    p.script_rel = path.relative_to(Path(mod.data)).as_posix()
    text = read_text(path, ENCODING) if exists else ""
    if body.get("sig") and str(body["sig"]) != _sig(text):
        p.errors.append(f"{p.script_rel} changed on disk after it was opened here - reload it")
        return p
    if exists:
        sh = shape_of(text)
        if sh.error:
            p.errors.append(f"{p.script_rel}: {sh.error}")
            return p
        nl = newline_of(text)
    else:
        nl = "\r\n"
        sh = Shape(lines=["script\r", "\r", "wait_monitors\r", "end_script\r", ""])
        sh.insert = 2
        p.script_new = True
    lines = sh.lines
    had = sh.blocks.get(low)

    if p.action == "remove":
        if had is None:
            p.errors.append(f"{p.script_rel} has no horde start for {p.faction} "
                            f"written by this tab; nothing else in the script is "
                            f"ever taken out")
            return p
        a, b = had
        # the blank line this tab put in front of the block goes with it
        if a > 0 and not lines[a - 1].strip():
            a -= 1
        new_lines = lines[:a] + lines[b + 1:]
        was = read_block(lines, had)
        p.changes.append(f"- the horde start for {p.faction}: "
                         f"{len(was['armies'])} army(ies) on turn {was['turn']}")
        p.warnings.append(f"{p.faction} keeps its flags in descr_strat.txt; the "
                          f"Each faction tab takes {DEAD} off")
        p.script_text = "\n".join(new_lines)
        p.errors += _guard(lines, new_lines, (a, b + 1), 0)
        return p

    turn = body.get("turn", 0)
    armies = armies_from_body(body.get("armies"))
    p.findings = check_armies(facts, sf, p.faction, turn, armies)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    if p.errors:
        return p

    block = render_block(p.faction, int(str(turn)), armies, nl)
    eol = "\r" if nl == "\r\n" else ""
    if had is not None:
        a, b = had
        new_lines = lines[:a] + block + lines[b + 1:]
        span = (a, b + 1)
        p.changes.append(f"the horde start for {p.faction} is rewritten where it stands")
    else:
        at = sh.insert
        lead = [] if at > 0 and not lines[at - 1].strip() else [eol]
        add = lead + block + [eol]
        new_lines = lines[:at] + add + lines[at:]
        span = (at, at)
        block = add
        p.changes.append(f"+ a horde start for {p.faction}, in front of the "
                         f"script's last wait_monitors (line {at + 1})")
    p.changes.append(f"turn {int(str(turn))}: " + "; ".join(
        f"{a.name or '?'} ({a.type}) at {a.x},{a.y} with {len(a.units)} regiment(s)"
        for a in armies))
    p.errors += _guard(lines, new_lines, span, len(block))
    if p.errors:
        return p
    p.script_text = "\n".join(new_lines)
    p.block = "\n".join(ln.rstrip("\r") for ln in render_block(p.faction, int(str(turn)), armies, "\n"))

    # it must read back: as 37a's spawns, and as this module's own block
    back = [s for s in spawns.scan_text(p.script_text) if s.faction == p.faction]
    was_n = len([s for s in spawns.scan_text(text) if s.faction == p.faction]) if text else 0
    mine_was = len(read_block(lines, had)["armies"]) if had else 0
    if len(back) != was_n - mine_was + len(armies):
        p.errors.append("the block does not read back as the armies it was "
                        "written from, so it is not written")
        return p

    if st["settlements"] or st["characters"]:
        p.warnings.append(
            f"{p.faction} still holds {st['settlements']} settlement(s) and "
            f"{st['characters']} character(s), so this is not a horde start but "
            f"reinforcements, and {DEAD} is not added")
    elif DEAD not in st["flags"] and body.get("flag", True):
        cp = stratcamp.plan_campaign(mod, facts, {
            "campaign": campaign, "what": "faction", "faction": p.faction,
            "scalars": {}, "flags": st["flags"] + [DEAD]})
        if cp.errors:
            p.errors += [f"descr_strat.txt: {e}" for e in cp.errors]
            return p
        p.strat = cp
        p.changes.append(f"descr_strat.txt: {p.faction} gets {DEAD}, so it is "
                         f"not dead at turn one for holding nothing")
    elif DEAD not in st["flags"]:
        p.warnings.append(f"{p.faction} holds nothing and has no {DEAD}; the "
                          f"engine counts it destroyed before the script spawns it")
    if p.script_new:
        p.changes.append(f"{p.script_rel} is new: `script`, this block, "
                         f"`wait_monitors`, `end_script`")
    return p


def _guard(before: List[str], after: List[str], span: Tuple[int, int],
           put: int) -> List[str]:
    """Every line outside the block is the line that was there.

    ``span`` is the run of ``before`` replaced (``[a, b)``) and ``put`` how many
    lines went in; the head must be ``before[:a]`` and the tail ``before[b:]``.
    """
    a, b = span
    if after[:a] != before[:a] or after[a + put:] != before[b:] \
            or len(after) != len(before) - (b - a) + put:
        return ["the save would touch a line of the script outside the horde "
                "start, so it is not written"]
    return []


def apply(p: HordePlan) -> dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.script_text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [], "deleted": []}
    writes = [(p.script_rel, p.script_text, ENCODING)]
    if p.strat is not None:
        writes.append((f"{campstrat.CAMPAIGN_DIR_REL}/{p.campaign}/{campstrat.STRAT_NAME}",
                       p.strat.text, campstrat.ENCODING))
    for rel, _t, _e in writes:
        target = Path(mod.data) / rel
        if target.exists():
            bpath = backup_root / "data" / rel
            bpath.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
    for rel, text, enc in writes:
        target = Path(mod.data) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, text, enc)
        file_op("WRITE", target, f"{len(text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "horde",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.faction, "resolved_type": p.faction,
        "options": {"campaign": p.campaign, "faction": p.faction, "what": p.action},
        "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("HORDE %s %s in %s/%s, id=%s", p.action, p.faction, mod.name,
             p.campaign, tid)
    return {"id": tid, "faction": p.faction, "campaign": p.campaign, "record": rec}
