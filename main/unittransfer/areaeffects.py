"""``descr_area_effects.xml`` - what a shot does where it lands (Phase 67).

The roadmap's row called this file "interdict, excommunication and the rest".
It is not: those are campaign mechanics and live nowhere near it. **An area
effect is a battle thing**, named by a projectile's ``area_effect`` line in
``descr_projectile.txt`` (and by a holy cart's in ``descr_engines.txt``): the
cow carcass that sickens a unit, the Greek fire that burns on the ground, the
explosion that throws men, the grapeshot that splits into more shots, the
holy aura that lifts morale. The file's own comment says the types are the
names in the engine's ``AREA_EFFECT_STRINGS``.

**Six types, measured on both installed mods** (ROCSS 55 effects, DaC 41;
DaC's 555 lines hold 34 tags, the same 34 as ROCSS):

* ``nausea`` - radius, duration, a banner colour and its alpha range, a
  morale hit and its cap, and a ground and a wall effect set;
* ``holy`` - radius, duration, a morale lift and its cap, a banner colour;
* ``fire`` - radius, height, delay, duration, an effect set, ``fiery``;
* ``explosion`` - impulse, effective and kill radius with a force or damage
  each, ``fiery``, an effect set;
* ``projectile`` - ``projectile_type`` (a projectile) fired
  ``projectile_number`` times with a force range, a ``direction`` and a
  ``scatter_angle``;
* ``area_effect_set`` - ``<effect delay="0.2">ae_greek_fire</effect>`` rows:
  other area effects, each after a delay. **An ``<effect>`` here names an area
  effect; anywhere else it names an effect set** (``descr_effects.txt``'s
  list of files). The rules keep the two apart.

What the measurement found, and what became a rule:

* Each mod has one projectile whose ``area_effect`` is declared nowhere:
  ROCSS's ``ae_fearcommand_arrow``, DaC's ``ae_poison_javelin``. The warning
  that matters.
* Both mods' explosion ``ae_nahptha_shot`` names ``ae_medium_fire`` as its
  effect set, and that is an area effect, not a set: CA's own line, carried by
  both, so a note. DaC's ``ae_naphtha_fire`` names ``nahptha_fire_set``, which
  DaC declares in ``descr_burning_building.txt`` - one of the 14 files the
  manifest lists that the toolkit's effect index read none of until it was
  taught the manifest (:mod:`effects`). ROCSS does not ship that file, so the
  base game's is read, and on this install the base game's files are packed:
  a set not found is a note while a listed file cannot be read, and a warning
  once every one can.
* The file's own comment gives four directions (forward, backward, up,
  down); ``horizontal`` is written 11 times across the two mods, grapeshot
  and multishot among them, so it is a fifth and not a finding. Anything
  else is a note.
* No duplicate names, no unknown type, no colour past 255, no projectile type
  that is not a projectile, in either mod. Many effects are named by nothing
  a mod ships (20 in ROCSS, 15 in DaC): the page shows who uses each one, and
  that is not a finding.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import leafxml as lx

REL = "descr_area_effects.xml"
ROOT_TAG = "root"
LIST_TAG = "area_effects"
ITEM_TAG = "area_effect"
SET_TYPE = "area_effect_set"

#: type -> its fields after `name` and `type`, the union of both installed mods
TYPES: Dict[str, Tuple[str, ...]] = {
    "nausea": ("radius", "duration", "banner_colour", "banner_colour_alpha_min",
               "banner_colour_alpha_max", "morale_effect", "morale_max", "ground_effect",
               "floating_effect"),
    "holy": ("radius", "duration", "morale_effect", "morale_max", "banner_colour"),
    "fire": ("radius", "height", "delay", "duration", "effect", "fiery"),
    "explosion": ("impulse_radius", "impulse_force", "effective_radius", "effective_damage",
                  "kill_radius", "kill_damage", "fiery", "effect"),
    "projectile": ("projectile_type", "projectile_number", "explosion_force_min",
                   "explosion_force_max", "preserve_momentum", "direction", "scatter_angle",
                   "effect", "banner_colour"),
    SET_TYPE: ("effect",),
}
NUMBERS = ("radius", "duration", "height", "delay", "morale_effect", "morale_max",
           "impulse_radius", "impulse_force", "effective_radius", "effective_damage",
           "kill_radius", "kill_damage", "fiery", "explosion_force_min", "explosion_force_max",
           "scatter_angle", "projectile_number", "banner_colour_alpha_min",
           "banner_colour_alpha_max", "red", "green", "blue")
COLOURS = ("red", "green", "blue", "banner_colour_alpha_min", "banner_colour_alpha_max")
#: the four the file's own comment gives, and `horizontal`, which both mods
#: write on shots they fire
DIRECTIONS = ("forward", "backward", "up", "down", "horizontal")
#: the fields that name an effect set in the effect files
SET_REFS = ("effect", "ground_effect", "floating_effect")
NAME = re.compile(r"[^\s,;<>&]+")
_REF = re.compile(r"^[ \t]*area_effect[ \t]+([^\s;]+)", re.M | re.I)

finding = lx.finding


def parse(text: str) -> lx.Doc:
    return lx.parse(text, ROOT_TAG)


def _items(doc: lx.Doc) -> List[lx.Node]:
    return [n for n in doc.find(ITEM_TAG) if n.parent >= 0 and doc.nodes[n.parent].tag == LIST_TAG]


def area_effects(doc: lx.Doc) -> List[Dict]:
    """Every area effect, its type and its fields; a set's members are the
    ``members`` list, ``{id, name, delay, line}``."""
    out = []
    for a in _items(doc):
        typ = doc.field(a, "type")
        fields = [f for f in lx.leaves(doc, a) if not (typ == SET_TYPE and f["tag"] == "effect")]
        members = [{"id": e.id, "name": doc.value(e), "delay": e.get("delay"), "line": e.line + 1}
                   for e in doc.kids(a, "effect")] if typ == SET_TYPE else []
        out.append({"id": a.id, "name": doc.field(a, "name"), "type": typ, "line": a.line + 1,
                    "fields": fields, "members": members})
    return out


# ---------------------------------------------------------------------------
# who names an area effect, and what it names


def uses(data: Path) -> Dict[str, List[Dict]]:
    """``lower name -> [{file, who, line}]``: every projectile and engine that
    names an area effect."""
    out: Dict[str, List[Dict]] = {}
    for rel, head in (("descr_projectile.txt", "projectile"), ("descr_engines.txt", "type")):
        p = data / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="latin-1")
        except OSError:
            continue
        who = ""
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split(";", 1)[0]
            m = re.match(rf"^[ \t]*{head}[ \t]+(\S+)", code)
            if m:
                who = m.group(1)
                continue
            m = _REF.match(code)
            if m:
                out.setdefault(m.group(1).lower(), []).append(
                    {"file": rel, "who": who, "line": i, "name": m.group(1)})
    return out


def _projectiles(data: Path) -> Optional[Set[str]]:
    p = data / "descr_projectile.txt"
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="latin-1")
    except OSError:
        return None
    return {m.lower() for m in re.findall(r"^[ \t]*projectile[ \t]+(\S+)", text, re.M)}


def effect_sets(data: Path) -> Tuple[Set[str], List[str]]:
    """Every ``effect_set`` the engine loads for the mod, and the listed files
    nothing here can read (the mod does not ship them and the base game's copy
    is packed). The one file list :mod:`effects` keeps for every reader."""
    from . import effects as fx
    from . import projectiles
    return projectiles.effect_sets(data), fx.effect_files(data).unread


class Refs:
    """What the checks hold an effect against; ``None`` skips that rule."""

    def __init__(self, uses=None, projectiles=None, sets=None, absent=None):
        #: `absent` is the listed effect files nothing here can read: not in
        #: the mod, and the base game's copy packed
        self.uses: Dict[str, List[Dict]] = uses or {}
        self.projectiles: Optional[Set[str]] = projectiles
        self.sets: Optional[Set[str]] = sets
        self.absent: List[str] = absent or []

    @classmethod
    def of(cls, mod) -> "Refs":
        data = Path(mod.data)
        sets, absent = effect_sets(data)
        return cls(uses(data), _projectiles(data), sets, absent)


# ---------------------------------------------------------------------------
# checking


def check(doc: lx.Doc, refs: Optional[Refs] = None) -> List[Dict]:
    refs = refs or Refs()
    out = lx.xml_findings(doc)
    items = _items(doc)
    if not items and not doc.errors:
        out.append(finding("empty", "warn", f"no <{ITEM_TAG}> under <{LIST_TAG}>", "file", 0))
    names: Dict[str, int] = {}
    for a in items:
        n = doc.field(a, "name")
        if n and n.lower() not in names:
            names[n.lower()] = a.line + 1
    seen: Set[str] = set()
    set_notes: Dict[str, List[Tuple[str, int, str]]] = {}
    for a in items:
        key = f"effect/{a.id}"
        name = doc.field(a, "name")
        owner = name or f"the area effect on line {a.line + 1}"
        typ = doc.field(a, "type")
        if not name:
            out.append(finding("name", "fatal", f"line {a.line + 1}: an area effect with no "
                               "<name>, so nothing can name it", key, a.line))
        elif name.lower() in seen:
            out.append(finding("duplicate", "warn", f"{name} is declared twice (lines "
                               f"{names[name.lower()]} and {a.line + 1})", key, a.line))
        if name:
            seen.add(name.lower())
        if not typ:
            out.append(finding("type", "warn", f"{owner} has no <type>", key, a.line))
        elif typ not in TYPES:
            out.append(finding("type", "warn", f"{owner}: type {typ} is not one of "
                               f"{', '.join(TYPES)}", key, a.line))
        vals: Dict[str, float] = {}
        for f in lx.leaves(doc, a):
            node = doc.nodes[f["id"]]
            v = f["value"]
            if f["tag"] in NUMBERS:
                if not lx.NUM.fullmatch(v):
                    out.append(finding("number", "fatal", f"{owner}: <{f['path']}> is "
                                       f"{v or '(blank)'}, not a number", key, node.line))
                    continue
                vals[f["path"]] = float(v)
                if f["tag"] in COLOURS and not 0 <= float(v) <= 255:
                    out.append(finding("colour", "warn", f"{owner}: {f['path']} {v} is outside "
                                       "0-255", key, node.line))
            elif f["tag"] == "preserve_momentum" and v not in ("true", "false"):
                out.append(finding("bool", "warn", f"{owner}: preserve_momentum is "
                                   f"{v or '(blank)'}, not true or false", key, node.line))
            elif f["tag"] == "direction" and v not in DIRECTIONS:
                out.append(finding("direction", "note", f"{owner}: direction {v or '(blank)'} "
                                   f"is not one of {', '.join(DIRECTIONS)}", key, node.line))
            elif f["tag"] == "projectile_type" and refs.projectiles is not None \
                    and v.lower() not in refs.projectiles:
                out.append(finding("projectile", "warn", f"{owner}: projectile_type {v} is not "
                                   "a projectile descr_projectile.txt declares", key, node.line))
            elif f["tag"] in SET_REFS and typ != SET_TYPE and v and refs.sets is not None \
                    and v.lower() not in refs.sets:
                set_notes.setdefault(v, []).append((owner, node.line, key))
        for lo, hi in (("banner_colour_alpha_min", "banner_colour_alpha_max"),
                       ("explosion_force_min", "explosion_force_max")):
            if lo in vals and hi in vals and vals[lo] > vals[hi]:
                out.append(finding("range", "warn", f"{owner}: {lo} {vals[lo]:g} is above "
                                   f"{hi} {vals[hi]:g}", key, a.line))
        if typ == SET_TYPE:
            members = doc.kids(a, "effect")
            if not members:
                out.append(finding("set", "warn", f"{owner} is a set with no <effect> in it, so "
                                   "it does nothing", key, a.line))
            for e in members:
                m, d = doc.value(e), e.get("delay")
                if m.lower() not in names:
                    out.append(finding("member", "warn", f"{owner}: its member {m or '(blank)'} "
                                       f"(line {e.line + 1}) is not an area effect in this file",
                                       key, e.line))
                elif m.lower() == (name or "").lower():
                    out.append(finding("member", "warn", f"{owner} lists itself (line "
                                       f"{e.line + 1})", key, e.line))
                if d and not lx.NUM.fullmatch(d):
                    out.append(finding("number", "fatal", f"{owner}: delay {d!r} on line "
                                       f"{e.line + 1} is not a number", key, e.line))
    for v, where in set_notes.items():
        owner, line, key = where[0]
        who = ", ".join(sorted({w for w, _l, _k in where})[:4])
        if v.lower() in names:
            out.append(finding("set_is_effect", "note", f"{who}: effect {v} is an area effect, "
                               "where an effect set from the effect files goes", key, line))
        elif refs.absent:
            out.append(finding("set_absent", "note", f"{who}: effect set {v} is in none of the "
                               f"effect files that can be read; {len(refs.absent)} of the "
                               "files descr_effects.txt lists are the base game's and packed, "
                               "and one of those may have it", key, line))
        else:
            near = sorted(s for s in refs.sets if lx.lev(s, v.lower()) <= 2)
            out.append(finding("set_missing", "warn", f"{who}: effect set {v} is in none of the "
                               "effect files descr_effects.txt lists"
                               + (f" - {near[0]} is, and is probably what was meant" if near else ""),
                               key, line))
    for low, where in refs.uses.items():
        if low in names:
            continue
        first = where[0]
        whos = ", ".join(sorted({w["who"] for w in where if w["who"]})[:4])
        out.append(finding("undeclared", "warn", f"{first['file']}: {whos or 'line ' + str(first['line'])} "
                           f"name{'s' if len(where) == 1 else ''} area_effect {first['name']}, and "
                           f"{REL} declares no area effect called that", f"use/{first['name']}", 0))
    return out


# ---------------------------------------------------------------------------
# reading a mod


def overview(mod) -> Dict:
    out: Dict = {"file": REL, "effects": [], "findings": [], "types": TYPES,
                 "directions": DIRECTIONS}
    try:
        text = lx.read(mod, REL)
    except lx.LeafError as e:
        out["error"] = e.message
        return out
    doc = parse(text)
    refs = Refs.of(mod)
    out["effects"] = area_effects(doc)
    in_sets: Dict[str, List[str]] = {}
    for e in out["effects"]:
        for m in e["members"]:
            in_sets.setdefault(m["name"].lower(), []).append(e["name"])
    for e in out["effects"]:
        low = e["name"].lower()
        e["used"] = refs.uses.get(low, [])[:50]
        e["in_sets"] = sorted(set(in_sets.get(low, [])))
    out["absent_effect_files"] = refs.absent
    out["sig"] = lx.sig(text)
    out["findings"] = check(doc, refs)
    return out


# ---------------------------------------------------------------------------
# editing


def _type_of(doc: lx.Doc, n: lx.Node) -> str:
    cur = n
    while cur.parent >= 0 and cur.tag != ITEM_TAG:
        cur = doc.nodes[cur.parent]
    return doc.field(cur, "type") if cur.tag == ITEM_TAG else ""


def _check_value(doc: lx.Doc, n: lx.Node, v: str) -> str:
    if n.tag == "name":
        return "" if NAME.fullmatch(v) else \
            f"{v!r} cannot be an area effect's name: one word, with no comma"
    if n.tag == "type":
        return "" if v in TYPES else f"type is one of {', '.join(TYPES)}"
    if n.tag in NUMBERS:
        if not lx.NUM.fullmatch(v):
            return f"{n.tag} is a number, not {v!r}"
        if n.tag in COLOURS and not 0 <= float(v) <= 255:
            return f"{n.tag} is 0 to 255"
        return ""
    if n.tag == "preserve_momentum" and v not in ("true", "false"):
        return "preserve_momentum is true or false"
    if n.tag in ("projectile_type", "direction") + SET_REFS and not NAME.fullmatch(v):
        return f"{n.tag} is one word, not {v!r}"
    return ""


def _removable(doc: lx.Doc, n: lx.Node) -> str:
    if n.tag == ITEM_TAG:
        return ""
    if n.tag in ("name", "type"):
        return f"<{n.tag}> is what the record is; remove the record instead"
    if n.tag in ("red", "green", "blue"):
        return "a colour keeps its three parts; remove banner_colour instead"
    return ""


def _fields_of(doc: lx.Doc, par: lx.Node) -> Tuple[str, ...]:
    if par.tag != ITEM_TAG:
        return ()
    typ = doc.field(par, "type")
    return tuple(f for f in TYPES.get(typ, ()) if f != "banner_colour") \
        if typ != SET_TYPE else ()


def _name_ok(doc: lx.Doc, like: lx.Node, name: str) -> str:
    if like.tag != ITEM_TAG:
        return "a set's member is copied as it is; change it after"
    if not NAME.fullmatch(name):
        return f"{name!r} cannot be an area effect's name: one word, with no comma"
    if any(e["name"].lower() == name.lower() for e in area_effects(doc)):
        return f"there is already an area effect called {name}"
    return ""


def plan(mod, body: dict) -> lx.Plan:
    """The body is :mod:`leafxml`'s: ``values`` (a set member's name is its
    value), ``attrs`` (a member's ``delay``), ``copy`` (an area effect with a
    new ``name``, or a set member ``into`` its set), ``remove``,
    ``add_field``; and ``sig``."""
    p = lx.Plan(REL, "areaeffects", mod=mod)
    try:
        text = lx.read(mod, REL)
    except lx.LeafError as e:
        p.errors.append(e.message)
        return p
    if str(body.get("sig") or "") != lx.sig(text):
        p.errors.append(f"{REL} changed on disk after it was opened here - reload it")
        return p
    doc = parse(text)
    if doc.root_end < 0:
        p.errors.append(f"{REL} does not close its <{ROOT_TAG}>, so nothing here can be sure "
                        "where an edit lands - fix it in Raw text first")
        return p
    by = {str(n.id): n for n in doc.nodes}
    for spec in body.get("copy") or []:
        like = by.get(str(spec.get("like")))
        if like is None:
            continue
        if like.tag == ITEM_TAG and not str(spec.get("name") or "").strip():
            p.errors.append("a copied area effect needs a name of its own")
        if like.tag == "effect" and _type_of(doc, like) != SET_TYPE:
            p.errors.append("only a set's member is copied on its own")
    if p.errors:
        return p
    new = lx.plan_edits(p, text, doc, body, _check_value, (ITEM_TAG, "effect"),
                        _removable, _fields_of, _name_ok)
    if not new:
        return p
    p.text = new
    refs = Refs.of(mod)
    was = {f["message"] for f in check(doc, refs)}
    p.warnings += [f["message"] for f in check(parse(new), refs)
                   if f["severity"] != "note" and f["message"] not in was]
    return p


apply = lx.apply
