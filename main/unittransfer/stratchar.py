"""``descr_strat.txt``, write: characters, armies and the family tree.

16h wrote the half of a faction block that is places. This is the half that is
people: the general standing outside Nottingham with five regiments behind him,
the princess, the spy, the dead grandfather the game needs in order to draw a
family tree at all, and the ``relative`` line that says who was whose child.

It is built on 16h rather than beside it. :mod:`unittransfer.stratedit` owns the
discipline both records share - rewrite the line a field came from and keep its
indent and its comment, move a span rather than rebuild it, splice and then read
the whole file back to check what would be written - and every one of those
helpers is imported here rather than written again.

**What the file says, measured on all three installed campaigns.**

*A character block already ends on the blank line after it.* 16b closes a
character at the next thing that can only start something else, so its span runs
to the line before that: 216 of vanilla's 216 and 245 of Third Age Reforged's
246 end on a blank line, the one exception being the last character in a faction
block. A settlement needed :func:`~unittransfer.stratedit.detach_span` to pick
its separator up; a character carries its own, and moving one is therefore a
straight slice of ``[start, end]``.

*Nothing inside a faction block is indented.* Not the ``character`` line, not
``traits``, not one of the 1,678 ``unit`` lines measured. The comma separator on
a character line is ``", "`` on all 1,178 of vanilla's and all 1,422 of Third
Age Reforged's; on a ``traits`` line it is ``" , "`` on 388 of 389 and 513 of
513. The character line usually carries a trailing space - 215 of 216, 244 of
246 - which is why a new one is written in the shape of the line above it rather
than in a shape decided here.

**The bodyguard-first rule is vanilla's habit, not the engine's rule.** This was
going to be a refusal. Third Age Reforged has 213 characters with an army and
**only 14 of them hold a unit the EDU marks ``general_unit`` anywhere at all**,
never mind first; 199 lead armies with no bodyguard in them. The mod loads and
plays. Vanilla puts a bodyguard first on every general it has. So the rule is
reported as a warning with that number attached, and only when there is an
``export_descr_unit.txt`` on disk to say which units are bodyguards - which the
stock game, whose EDU is inside the packed data, does not have.

**And the attribute is what is read, never the name.** That mod calls 19 units
Bodyguard and gives ``general_unit`` to 6 of them: its Gondor, Arnor, Dunedain,
Lindon and Mithril Bodyguards are all ordinary regiments as far as the engine is
concerned. A check that went by the word would clear every one of those and
report nothing, which is worse than a check that does not run.

**The two family constraints are real and real files break them.** A living
parent should be at least sixteen years older than a child: vanilla breaks it
once (Egypt's Al-Zahir at 60 with Al-Mustansir at 45) and Third Age Reforged
once. Children should be listed oldest first: vanilla breaks it twice, on
Philip's four and Heinrich's three. Both are therefore warnings. Ages are only
comparable between the living - a dead ancestor's ``age`` is the age they died
at, not the age they would be now - so a ``dead`` record is left out of the
comparison rather than reported for it.

**Every faction with named characters has exactly one leader**, on all three
campaigns, and the exceptions hold none at all: the rebels in both of vanilla's
and Third Age Reforged's, and the prologue's Saxons. An heir is optional - seven
of Third Age Reforged's factions have a leader and no heir. Five of its factions
name two different characters the same thing, which matters because a
``relative`` line addresses people by name and nothing else.

**What is fatal is what the engine's own vocabulary has no room for**, which is
16h's ruling carried into a fourth phase: a character type that is not one of
the twelve, an age or a coordinate that is not a whole number, a tile off the
map, and a unit, trait or ancillary the mod's own file does not declare - that
last only when the file is on disk to say so. Everything else is a warning with
the count that made it one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campstrat, stratedit
from .campstrat import CHARACTER_TYPES, LEADERSHIP, Node, StratFile
from .stratedit import (assemble, comment_of, faction_of, finding, indent_of,
                        is_int, move_lines, rewrite_line, serialise,
                        split_block)

#: The two ranks a character line may carry. Neither is required and only one
#: of each may exist in a faction.
RANKS = ("leader", "heir")

#: ``keyword value`` fields on the tail of a character line, in the order the
#: files write them. Every one is optional.
TAIL = ("portrait", "label", "battle_model", "hero_ability", "direction",
        "shadowing", "shadowed_by")

#: The character line's own fields, which are positional rather than keyed.
HEAD = ("name", "type", "gender", "rank", "age", "x", "y")

#: How many years older than a child a living parent should be. Geomod's manual
#: and every family in the shipped campaigns bar two agree on sixteen.
PARENT_YEARS = 16

#: What a ``character_record`` is, keyword by keyword. Held apart from the live
#: character because they are different records with different fields, however
#: alike they read.
RECORD_FIELDS = ("name", "gender", "age", "dead", "leadership")

#: The comma separator the campaign files write on a character line, used only
#: when there is no sibling line to copy it from.
SEP = ", "

#: The same, on a ``traits`` line.
TRAIT_SEP = " , "

_NUM = re.compile(r"-?\d+")


def _clean(line: str) -> str:
    return line.split(";", 1)[0].strip()


# ---------------------------------------------------------------------------
# finding people in the tree


def characters_of(sf: StratFile, faction: Node) -> List[Node]:
    """That faction's characters, in the order the file writes them."""
    return sf.children_of(faction, "character")


def records_of(sf: StratFile, faction: Node) -> List[Node]:
    return sf.children_of(faction, "character_record")


def relatives_of(sf: StratFile, faction: Node) -> List[Node]:
    return sf.children_of(faction, "relative")


def find_character(sf: StratFile, faction: str, name: str,
                   line: int = 0) -> Optional[Node]:
    """One character, by the faction that holds them and their name.

    ``line`` is the 1-based line the panel was looking at and it wins when it is
    given, because five of Third Age Reforged's factions name two different
    characters the same thing and a name alone cannot tell those two apart. The
    name is what the family tree addresses people by, so it is still the key
    everywhere else; this is the one place that has somewhere better to look.
    """
    fac = sf.faction(faction) if faction else None
    pool = characters_of(sf, fac) if fac is not None else sf.of_kind("character")
    if line:
        hit = next((n for n in pool if n.start + 1 == line), None)
        if hit is not None:
            return hit
    low = name.strip().lower()
    return next((n for n in pool if n.name.strip().lower() == low), None)


def find_record(sf: StratFile, faction: str, name: str,
                line: int = 0) -> Optional[Node]:
    fac = sf.faction(faction) if faction else None
    pool = (records_of(sf, fac) if fac is not None
            else sf.of_kind("character_record"))
    if line:
        hit = next((n for n in pool if n.start + 1 == line), None)
        if hit is not None:
            return hit
    low = name.strip().lower()
    return next((n for n in pool if n.name.strip().lower() == low), None)


def leader_of(sf: StratFile, faction: Node) -> str:
    """The faction's leader, or ``""``. One per faction on all three campaigns."""
    for n in characters_of(sf, faction):
        if str(n.get("rank") or "") == "leader":
            return n.name
    return ""


def heir_of(sf: StratFile, faction: Node) -> str:
    for n in characters_of(sf, faction):
        if str(n.get("rank") or "") == "heir":
            return n.name
    return ""


def insert_at(sf: StratFile, faction: Node, skip: Optional[Node] = None) -> int:
    """Where a new character goes: after the last one this faction already has.

    The roadmap's rule, and it is a rule rather than a preference - a character
    inserted at the head of the list lands in front of the settlements, where
    the parser and the engine are both still reading places. A faction with no
    character yet takes one after its last settlement, and one with no
    settlement either takes one at the end of its own block, which is where the
    file would have written it.
    """
    chars = [n for n in characters_of(sf, faction) if n is not skip]
    if chars:
        return chars[-1].end + 1
    places = stratedit.settlements_of(sf, faction)
    if places:
        return stratedit.detach_span(sf, places[-1], faction)[1] + 1
    after = [n for n in sf.children_of(faction)
             if n.kind in ("character_record", "relative")]
    return after[0].start if after else faction.end + 1


# ---------------------------------------------------------------------------
# what a form may offer


class Vocabulary:
    """Every value a character form may offer, and why one of them is missing.

    Four of the six sources are files the stock game keeps inside its packed
    data - the EDU, the trait file, the ancillary file and the name pool - so on
    vanilla this is mostly empty and says so, and the rules that needed each one
    do not run. That is 16f's ruling, and this is the fourth phase to apply it.
    """

    def __init__(self, facts, sf: StratFile):
        self.facts = facts
        self.sf = sf
        self.skipped: List[dict] = list(getattr(facts, "skipped", []))
        self.units: Dict[str, dict] = {}
        self.bodyguards: set = set()
        self.have_edu = False
        self.traits: Dict[str, int] = {}
        self.have_edct = False
        self.ancillaries: set = set()
        self.have_eda = False
        self.pool: Dict[str, List[str]] = {}
        #: the fourth section 19a taught the parser about - see
        #: :data:`unittransfer.minorfiles.NAME_SECTIONS`. Kept apart from
        #: :attr:`pool` because a surname is the *second* half of a name and
        #: never a character on its own.
        self.surnames: Dict[str, List[str]] = {}
        self.have_pool = False
        #: ``text/names.txt`` - what the player reads for one pool token
        self.name_keys: Dict[str, str] = {}
        self.have_name_keys = False
        self._read_edu()
        self._read_traits()
        self._read_ancillaries()
        self._read_pool()
        self._from_file(sf)
        self.factions = [str(n.get("name") or n.name) for n in sf.of_kind("faction")]

    def skip(self, what: str, why: str) -> None:
        self.skipped.append({"what": what, "why": why})

    def _read_edu(self) -> None:
        """Which units exist, and which of them the engine treats as a bodyguard.

        ``general_unit`` is the attribute that makes a unit a general's
        bodyguard. Third Age Reforged declares 28 of them and puts one in only
        14 of its 213 starting armies, which is the measurement that turned the
        bodyguard rule from a refusal into a warning.
        """
        try:
            edu = self.facts.mod.edu
        except Exception as exc:                           # noqa: BLE001
            self.skip("export_descr_unit.txt",
                      f"The unit list could not be read ({exc}), so an army's "
                      f"regiments are whatever the campaign file already names.")
            return
        units = getattr(edu, "units", None) or []
        if not units:
            self.skip("export_descr_unit.txt",
                      "The stock game keeps export_descr_unit.txt inside its "
                      "packed data rather than on disk, so an army's regiments "
                      "are the names the campaign file itself writes and no "
                      "unit can be checked against a roster.")
            return
        self.have_edu = True
        for u in units:
            attrs = getattr(u, "attributes", None) or []
            self.units[u.type] = {"name": u.type, "category": u.category,
                                  "class": u.class_type,
                                  "general": "general_unit" in attrs}
            if "general_unit" in attrs:
                self.bodyguards.add(u.type)

    def _read_traits(self) -> None:
        from . import traits as traits_mod
        path = Path(getattr(self.facts.mod, "edct_path", ""))
        if not path.is_file():
            self.skip("export_descr_character_traits.txt",
                      "Not on disk, so a trait on a character is whatever the "
                      "campaign file names and its level cannot be checked.")
            return
        try:
            tf = traits_mod.parse_file(path)
        except Exception as exc:                           # noqa: BLE001
            self.skip("export_descr_character_traits.txt",
                      f"The trait file could not be read ({exc}).")
            return
        self.have_edct = True
        for t in tf.traits:
            self.traits[t.name] = len(t.levels)

    def _read_ancillaries(self) -> None:
        from . import ancillaries as anc_mod
        path = Path(getattr(self.facts.mod, "eda_path", ""))
        if not path.is_file():
            self.skip("export_descr_ancillaries.txt",
                      "Not on disk, so an ancillary on a character is whatever "
                      "the campaign file names.")
            return
        try:
            af = anc_mod.parse_file(path)
        except Exception as exc:                           # noqa: BLE001
            self.skip("export_descr_ancillaries.txt",
                      f"The ancillary file could not be read ({exc}).")
            return
        self.have_eda = True
        self.ancillaries = {a.name for a in af.ancillaries}

    def _read_pool(self) -> None:
        """``descr_names.txt``: the names each faction may generate.

        Every one of Third Age Reforged's 325 characters and records is in it.
        ``descr_names_lookup.txt`` is deliberately not read: 547 of that mod's
        pool names are absent from the lookup and 176 lookup names are absent
        from the pool, so it is not the authority on anything and writing to it
        would be inventing a rule.
        """
        from . import minorfiles
        path = Path(self.facts.mod.data) / minorfiles.NAMES_REL
        if not path.is_file():
            self.skip(minorfiles.NAMES_REL,
                      "Not on disk, so nothing here knows which names a "
                      "faction may use.")
            return
        try:
            nf = minorfiles.parse_names(path.read_text(campstrat.ENCODING))
        except Exception as exc:                           # noqa: BLE001
            self.skip(minorfiles.NAMES_REL, f"Could not be read ({exc}).")
            return
        self.have_pool = True
        for f in nf.factions:
            got: List[str] = []
            for s in f.sections:
                if s.name in ("characters", "women"):
                    got += [e.value for e in s.entries]
            self.pool[f.name] = got
            sec = f.section("surnames")
            self.surnames[f.name] = [e.value for e in sec.entries] if sec else []

        # 19a. A pool entry is a token, and the words the player reads for it
        # are in text/names.txt - 3,583 of Divide and Conquer's 3,583 pool names
        # have a key there and 2,572 of Third Age Reforged's 2,573. A name in
        # the pool with no key is the other half of the same fault, and it was
        # the half nothing here could see.
        from . import namekeys
        state = namekeys.loc_state(self.facts.mod, namekeys.POOL_LOC_REL)
        if not (state["txt"] or state["bin"]):
            self.skip(namekeys.POOL_LOC_REL,
                      "Neither the file nor the archive beside it is on disk, "
                      "so no pool name can be called untranslated.")
            return
        self.name_keys = namekeys.loc_pairs(self.facts.mod, namekeys.POOL_LOC_REL)
        self.have_name_keys = bool(self.name_keys)

    def _from_file(self, sf: StratFile) -> None:
        """What the campaign file itself writes, for the fields nothing declares.

        ``hero_ability`` has no list anywhere on disk - Third Age Reforged's 45
        of them are named in ``descr_strat.txt`` and nowhere else - so the
        picker offers what is already in use. The same goes for portraits and
        labels, and for units when there is no EDU.
        """
        self.abilities: List[str] = []
        self.portraits: List[str] = []
        self.labels: List[str] = []
        self.file_units: List[str] = []
        for c in sf.of_kind("character"):
            for slot, into in (("hero_ability", self.abilities),
                               ("portrait", self.portraits),
                               ("label", self.labels)):
                v = str(c.get(slot) or "")
                if v and v not in into:
                    into.append(v)
        for u in sf.of_kind("unit"):
            if u.name and u.name not in self.units:
                self.file_units.append(u.name)
        for lst in (self.abilities, self.portraits, self.labels):
            lst.sort(key=str.lower)
        self.file_units = sorted(set(self.file_units), key=str.lower)

    def unit_names(self) -> List[str]:
        """Every unit that may be put in an army, the roster first."""
        return sorted(self.units, key=str.lower) or list(self.file_units)

    def payload(self) -> dict:
        return {
            "types": list(CHARACTER_TYPES),
            "ranks": list(RANKS),
            "leadership": list(LEADERSHIP),
            "tail": list(TAIL),
            "have_edu": self.have_edu,
            "have_edct": self.have_edct,
            "have_eda": self.have_eda,
            "have_pool": self.have_pool,
            "units": [{"name": n, "general": n in self.bodyguards}
                      for n in self.unit_names()],
            "bodyguards": sorted(self.bodyguards, key=str.lower),
            "traits": [{"name": n, "levels": v}
                       for n, v in sorted(self.traits.items(),
                                          key=lambda kv: kv[0].lower())],
            "ancillaries": sorted(self.ancillaries, key=str.lower),
            "abilities": list(self.abilities),
            "portraits": list(self.portraits),
            "labels": list(self.labels),
            "factions": list(self.factions),
            "pool": {k: len(v) for k, v in self.pool.items()},
            "surnames": {k: len(v) for k, v in self.surnames.items() if v},
            "have_name_keys": self.have_name_keys,
            "skipped": list(self.skipped),
        }


# ---------------------------------------------------------------------------
# one character, as values rather than as lines


@dataclass
class Army:
    """One regiment: what it is and the three numbers after it."""

    unit: str = ""
    exp: int = 0
    armour: int = 0
    weapon_lvl: int = 0

    def payload(self) -> dict:
        return {"unit": self.unit, "exp": self.exp, "armour": self.armour,
                "weapon_lvl": self.weapon_lvl}


@dataclass
class Spec:
    """A character as a form holds them, with no line in sight.

    The checks read this rather than a :class:`~unittransfer.campstrat.Node`, so
    every rule can be run over values typed into a box before any of them have
    been written down, and tested on values written in a test file.
    """

    name: str = ""
    type: str = ""
    gender: str = ""
    rank: str = ""
    age: object = None
    x: object = None
    y: object = None
    sub_faction: str = ""
    tail: Dict[str, str] = field(default_factory=dict)
    traits: List[Tuple[str, int]] = field(default_factory=list)
    ancillaries: List[str] = field(default_factory=list)
    army: List[Army] = field(default_factory=list)

    def payload(self) -> dict:
        return {"name": self.name, "type": self.type, "gender": self.gender,
                "rank": self.rank, "age": self.age, "x": self.x, "y": self.y,
                "sub_faction": self.sub_faction, "tail": dict(self.tail),
                "traits": [{"name": n, "level": v} for n, v in self.traits],
                "ancillaries": list(self.ancillaries),
                "army": [a.payload() for a in self.army]}


def read_spec(sf: StratFile, node: Node) -> Spec:
    """The character block as values, exactly as the panel will show it."""
    army = next(iter(sf.children_of(node, "army")), None)
    return Spec(
        name=node.name,
        type=str(node.get("type") or ""),
        gender=str(node.get("gender") or ""),
        rank=str(node.get("rank") or ""),
        age=node.get("age"), x=node.get("x"), y=node.get("y"),
        sub_faction=str(node.get("sub_faction") or ""),
        tail={k: str(node.get(k)) for k in TAIL if node.get(k)},
        traits=list((node.get("traits") or {}).items()),
        ancillaries=list(node.get("ancillaries") or []),
        army=[Army(unit=u.name, exp=int(u.get("exp") or 0),
                   armour=int(u.get("armour") or 0),
                   weapon_lvl=int(u.get("weapon_lvl") or 0))
              for u in (sf.children_of(army, "unit") if army is not None else [])])


def spec_from_body(body: dict, base: Optional[Spec] = None) -> Spec:
    """What the browser posted, folded onto what is already there.

    A key the panel did not send is left as it was, so a form that only edits
    the army does not have to send the traits back to keep them.
    """
    out = Spec(**{k: v for k, v in vars(base).items()}) if base else Spec()
    if base:
        out.tail = dict(base.tail)
        out.traits = list(base.traits)
        out.ancillaries = list(base.ancillaries)
        out.army = [Army(**vars(a)) for a in base.army]
    edits = body.get("edits")
    if isinstance(edits, dict):
        for slot in HEAD + ("sub_faction",):
            if slot in edits:
                setattr(out, slot, str(edits[slot]).strip()
                        if slot not in ("age", "x", "y") else edits[slot])
        for slot in TAIL:
            if slot in edits:
                value = str(edits[slot] or "").strip()
                if value:
                    out.tail[slot] = value
                else:
                    out.tail.pop(slot, None)
    if body.get("traits") is not None:
        out.traits = [(str(t.get("name") or "").strip(), t.get("level"))
                      for t in body["traits"]]
    if body.get("ancillaries") is not None:
        out.ancillaries = [str(a).strip() for a in body["ancillaries"] if str(a).strip()]
    if body.get("army") is not None:
        out.army = [Army(unit=str(a.get("unit") or "").strip(),
                         exp=a.get("exp", 0), armour=a.get("armour", 0),
                         weapon_lvl=a.get("weapon_lvl", 0))
                    for a in body["army"]]
    return out


# ---------------------------------------------------------------------------
# what is wrong with one character


def check_character(voc: Vocabulary, spec: Spec, cm=None) -> List[dict]:
    """Everything wrong with one character, fatal first.

    Fatal is only what the engine's own vocabulary has no room for, which is
    16h's ruling in its fourth phase. A bodyguard that is not first is a habit
    Third Age Reforged breaks 199 times and runs, so it is a warning with that
    number on it.
    """
    out: List[dict] = []
    if not spec.name:
        out.append(finding("char.name", True,
                           "A character with no name cannot be given traits, "
                           "put in a family or found by a script."))
    if spec.type not in CHARACTER_TYPES:
        out.append(finding(
            "char.type", True,
            f"{spec.type or '(nothing)'} is not a character type. The twelve "
            f"are " + ", ".join(CHARACTER_TYPES) + "."))
    for slot in ("age", "x", "y"):
        value = getattr(spec, slot)
        if not is_int(value):
            out.append(finding(
                f"char.{slot}", True,
                f"{slot} is {value if value not in (None, '') else '(nothing)'}, "
                f"which is not a whole number."))
    if is_int(spec.age) and int(str(spec.age)) < 0:
        out.append(finding("char.age", True,
                           "A character cannot start at a negative age."))
    if cm is not None and is_int(spec.x) and is_int(spec.y):
        gx, gy = int(str(spec.x)), int(str(spec.y))
        ix, iy = cm.image_xy(gx, gy)
        if not cm.terrain.in_bounds(ix, iy):
            out.append(finding(
                "char.offmap", True,
                f"{gx},{gy} is off the {cm.terrain.width}x"
                f"{cm.terrain.height} tile grid, so there is nowhere on the "
                f"map for this character to stand.", x=gx, y=gy))
        else:
            sea = cm.sea[iy * cm.terrain.width + ix]
            if spec.type == "admiral" and not sea:
                out.append(finding(
                    "char.aground", False,
                    f"An admiral stands on his ship, and {gx},{gy} is land.",
                    x=gx, y=gy))
            elif spec.type and spec.type != "admiral" and sea:
                out.append(finding(
                    "char.adrift", False,
                    f"{gx},{gy} is sea, and only an admiral starts there.",
                    x=gx, y=gy))
    if spec.gender not in ("male", "female"):
        out.append(finding(
            "char.gender", False,
            "No sex on the line. Every character in all three campaigns "
            "measured writes male or female, and it is what decides which "
            "model is drawn."))
    elif spec.type == "princess" and spec.gender != "female":
        out.append(finding("char.gender", False,
                           "A princess is written female in every campaign "
                           "measured."))
    if spec.rank and spec.rank not in RANKS:
        out.append(finding("char.rank", False,
                           f"{spec.rank!r} is not a rank. A character line "
                           f"carries leader, heir or neither."))

    for name, level in spec.traits:
        if not name:
            continue
        if voc.have_edct and name not in voc.traits:
            out.append(finding(
                "char.trait_unknown", True,
                f"{name} is not a trait export_descr_character_traits.txt "
                f"declares.", trait=name))
            continue
        if not is_int(level):
            out.append(finding("char.trait_level", True,
                               f"{name} has no level on it.", trait=name))
            continue
        top = voc.traits.get(name, 0)
        if voc.have_edct and top and int(str(level)) > top:
            out.append(finding(
                "char.trait_level", True,
                f"{name} is given level {level} and it has {top}.", trait=name))
    for anc in spec.ancillaries:
        if voc.have_eda and anc not in voc.ancillaries:
            out.append(finding(
                "char.anc_unknown", True,
                f"{anc} is not an ancillary export_descr_ancillaries.txt "
                f"declares.", ancillary=anc))

    out += _check_army(voc, spec)
    out.sort(key=lambda f: not f["fatal"])
    return out


def _check_army(voc: Vocabulary, spec: Spec) -> List[dict]:
    """The regiments, and the bodyguard rule that turned out not to be one."""
    out: List[dict] = []
    for a in spec.army:
        if not a.unit:
            out.append(finding("army.blank", True,
                               "A regiment with no unit name on it."))
            continue
        if voc.have_edu and a.unit not in voc.units:
            out.append(finding(
                "army.unknown", True,
                f"{a.unit} is not a unit export_descr_unit.txt declares, so "
                f"the campaign has nothing to put in this army.", unit=a.unit))
        for slot, value in (("exp", a.exp), ("armour", a.armour),
                            ("weapon_lvl", a.weapon_lvl)):
            if not is_int(value):
                out.append(finding(
                    "army.number", True,
                    f"{a.unit}'s {slot} is {value!r}, which is not a whole "
                    f"number.", unit=a.unit))
    if not spec.army or not voc.have_edu:
        return out
    if spec.type not in ("named character", "general"):
        return out
    if spec.army[0].unit in voc.bodyguards:
        return out
    held = [a.unit for a in spec.army if a.unit in voc.bodyguards]
    out.append(finding(
        "army.bodyguard", False,
        (f"{spec.army[0].unit} leads this army and the EDU does not give it "
         f"`general_unit`. "
         if not held else
         f"The `general_unit` in this army is {held[0]}, and "
         f"{spec.army[0].unit} is in front of it. ")
        + "Vanilla puts a bodyguard first on every general it has; Third Age "
          "Reforged has 213 armies and only 14 with a `general_unit` in them "
          "at all, and it plays. So this is a habit worth keeping rather than "
          "a rule. The attribute is what is read, not the name: that mod calls "
          "19 units Bodyguard and marks 6 of them.",
        unit=spec.army[0].unit))
    return out


def check_faction(sf: StratFile, faction: Node, voc: Vocabulary) -> List[dict]:
    """The rules that are about a faction rather than about one character.

    Every one of these is a warning. Each is broken by a shipped campaign
    somewhere, and the number that says so is in the message.
    """
    out: List[dict] = []
    name = str(faction.get("name") or faction.name)
    chars = characters_of(sf, faction)
    named = [c for c in chars if c.get("type") == "named character"]
    leaders = [c.name for c in chars if c.get("rank") == "leader"]
    heirs = [c.name for c in chars if c.get("rank") == "heir"]
    if len(leaders) > 1:
        out.append(finding(
            "faction.leaders", False,
            f"{name} has {len(leaders)} characters flagged leader "
            f"({', '.join(leaders[:4])}). Every faction on all three campaigns "
            f"measured has exactly one or none."))
    elif not leaders and named:
        out.append(finding(
            "faction.leaders", False,
            f"{name} has {len(named)} named characters and none of them is "
            f"the leader. The rebels are the only faction in any campaign "
            f"measured that does this."))
    if len(heirs) > 1:
        out.append(finding(
            "faction.heirs", False,
            f"{name} has {len(heirs)} characters flagged heir "
            f"({', '.join(heirs[:4])}). An heir is optional, and seven of "
            f"Third Age Reforged's factions have none, but there is only ever "
            f"one."))

    seen: Dict[str, int] = {}
    for c in chars:
        key = c.name.strip().lower()
        seen[key] = seen.get(key, 0) + 1
    dup = sorted(k for k, v in seen.items() if v > 1 and k)
    if dup:
        out.append(finding(
            "faction.duplicate", False,
            f"{name} names two characters {', '.join(dup[:3])}. A relative "
            f"line addresses people by name and nothing else, so a family "
            f"holding one of these is ambiguous. Five of Third Age Reforged's "
            f"factions do it."))
    out += _check_family(sf, faction, name)
    return out


def _check_family(sf: StratFile, faction: Node, name: str) -> List[dict]:
    """The two family constraints, over the living only.

    A dead ancestor's ``age`` is the age they died at rather than the age they
    would be now, so comparing one against a living child says nothing. Both
    rules are warnings: vanilla breaks the sixteen-year one once and the
    oldest-first one twice.
    """
    out: List[dict] = []
    chars = characters_of(sf, faction)
    records = records_of(sf, faction)
    known = {c.name.strip().lower() for c in chars if c.name}
    known |= {r.name.strip().lower() for r in records if r.name}
    living: Dict[str, int] = {}
    for c in chars:
        if is_int(c.get("age")):
            living[c.name.strip().lower()] = int(str(c.get("age")))
    for r in records:
        if r.get("dead") is None and is_int(r.get("age")):
            living.setdefault(r.name.strip().lower(), int(str(r.get("age"))))

    for rel in relatives_of(sf, faction):
        names = list(rel.get("names") or [])
        missing = [n for n in names if n.strip().lower() not in known]
        if missing:
            out.append(finding(
                "family.unknown", False,
                f"{name}'s family line on line {rel.start + 1} names "
                f"{', '.join(missing[:3])}, who is not a character or a "
                f"character_record in this faction.", line=rel.start + 1))
        if len(names) < 3:
            continue
        father, kids = names[0], names[2:]
        fa = living.get(father.strip().lower())
        for kid in kids:
            ka = living.get(kid.strip().lower())
            if fa is not None and ka is not None and fa - ka < PARENT_YEARS:
                out.append(finding(
                    "family.years", False,
                    f"{father} is {fa} and {kid} is {ka}, which is "
                    f"{fa - ka} years. A living parent should be at least "
                    f"{PARENT_YEARS} years older; vanilla breaks it once, on "
                    f"Egypt's Al-Zahir.", line=rel.start + 1))
        ages = [living[k.strip().lower()] for k in kids
                if k.strip().lower() in living]
        if ages and ages != sorted(ages, reverse=True):
            out.append(finding(
                "family.order", False,
                f"{father}'s children are listed {', '.join(str(a) for a in ages)} "
                f"and the game reads them oldest first. Vanilla breaks this "
                f"twice, on Philip's four and Heinrich's three.",
                line=rel.start + 1))
    return out


def check_pool(voc: Vocabulary, faction: str, name: str) -> List[dict]:
    """Whether the faction may generate this name, when anything says so.

    All 325 of Third Age Reforged's characters and records are in its pool, so
    a name that is not is worth saying out loud. The stock game keeps
    ``descr_names.txt`` inside its packed data, and then this reports nothing.

    **19a split the name in two before asking.** A ``descr_strat`` name is one
    or more parts, the last of which is a surname out of the ``surnames``
    section, and the finding now names the half that is missing rather than the
    whole name - which on a two-part name was the wrong thing to go looking for
    in a list of first names. Every character in both installed campaigns has a
    one-word name, so on those the two readings agree and this one also has a
    section to point at. The finding it produces is what 19a's Add to pool
    button writes.
    """
    if not voc.have_pool or not name:
        return []
    from .namekeys import name_parts
    pool = voc.pool.get(faction) or []
    first, surname = name_parts(name)
    out: List[dict] = []
    for part, have, where in ((first, pool, "characters/women"),
                              (surname, voc.surnames.get(faction) or [], "surnames")):
        if not part:
            continue
        if part not in have:
            other = [f for f, names in (voc.surnames if where == "surnames"
                                        else voc.pool).items() if part in names]
            out.append(finding(
                "char.pool", False,
                f"{part} is not in {faction}'s `{where}` section of descr_names.txt"
                + (f" - it is in {', '.join(other[:2])}'s. " if other else ". ")
                + "Every one of Third Age Reforged's 325 characters is in its own "
                  "faction's pool, and a name that is not may come out untranslated.",
                name=name, part=part))
        elif voc.have_name_keys and part not in voc.name_keys:
            out.append(finding(
                "char.name_key", False,
                f"{part} is in the pool but has no key in text/names.txt, so the "
                f"player reads the token rather than a name. Every one of Divide "
                f"and Conquer's 3,583 pool names has one.",
                name=name, part=part))
    return out


# ---------------------------------------------------------------------------
# the shape a line is written in


@dataclass
class Shape:
    """The whitespace and separators this file writes people with.

    Taken off the file rather than decided here, because the three campaigns
    measured do not agree: vanilla puts a trailing space on 215 of its 216
    character lines and the prologue on 9 of 17, and the padding between a
    unit's name and its numbers runs from two tabs to five. So a new line is
    written in the shape of the nearest line of the same kind, and the values
    below are only what is used when there is no such line anywhere.
    """

    gap: str = "\t"
    sep: str = SEP
    trail: str = " "
    trait_gap: str = " "
    trait_sep: str = TRAIT_SEP
    anc_gap: str = " "
    anc_sep: str = TRAIT_SEP
    army_gap: str = ""
    unit_gap: str = "\t\t"
    unit_pad: str = "\t\t\t\t"
    indent: str = ""
    #: the padding each named unit is already written with, so a regiment added
    #: to an army lines its numbers up with every other copy of that regiment
    #: in the file rather than with whichever one happened to be read first
    pads: Dict[str, str] = field(default_factory=dict)


_CHAR_GAP = re.compile(r"^(?P<i>[\t ]*)character(?P<gap>[\t ]+)", re.I)
_KEY_GAP = re.compile(r"^[\t ]*(?:traits|ancillaries)(?P<gap>[\t ]+)", re.I)
_SEP = re.compile(r",(?P<gap>[\t ]*)")
_TRAIT_SEP = re.compile(r"(?P<gap>[\t ]*,[\t ]*)")
_UNIT_SHAPE = re.compile(
    r"^(?P<i>[\t ]*)unit(?P<gap>[\t ]+)(?P<name>.+?)(?P<pad>[\t ]+)exp\b", re.I)


def _trailing(line: str) -> str:
    return line[len(line.rstrip()):]


def shape_of(sf: StratFile, faction: Optional[Node] = None,
             node: Optional[Node] = None) -> Shape:
    """How to write a character here: this one's own shape, then a neighbour's.

    Looked for in the order somebody would look: the character being edited,
    then any other character in the same faction, then the first one anywhere
    in the file. A campaign with no character at all - vanilla has two factions
    like that, the Mongols and the Timurids - falls through to the defaults,
    which are what the other 216 lines write.
    """
    out = Shape()
    pool: List[Node] = []
    if node is not None:
        pool.append(node)
    if faction is not None:
        pool += [n for n in characters_of(sf, faction) if n is not node]
    pool += [n for n in sf.of_kind("character") if n not in pool]

    for n in pool:
        line = sf.lines[n.start]
        m = _CHAR_GAP.match(line)
        if not m:
            continue
        out.indent, out.gap = m.group("i"), m.group("gap")
        seps = [s.group("gap") for s in _SEP.finditer(line)]
        if seps:
            out.sep = "," + max(set(seps), key=seps.count)
        out.trail = _trailing(line)
        break

    for n in pool:
        for slot, gap, sep in (("traits", "trait_gap", "trait_sep"),
                               ("ancillaries", "anc_gap", "anc_sep")):
            at = n.field_lines.get(slot)
            if at is None or getattr(out, gap + "_seen", False):
                continue
            line = sf.lines[at]
            m = _KEY_GAP.match(line)
            if not m:
                continue
            setattr(out, gap, m.group("gap"))
            body = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            hits = [h.group("gap") for h in _TRAIT_SEP.finditer(body)]
            if hits:
                setattr(out, sep, max(set(hits), key=hits.count))
            setattr(out, gap + "_seen", True)

    # The padding between a regiment's name and its numbers runs from two tabs
    # to five across one file, so it is taken from the nearest army rather than
    # from the first one anywhere: this character's own, then the faction's,
    # then whatever the file opens with.
    near: List[Node] = []
    if node is not None:
        near += sf.descendants_of(node, "unit")
    if faction is not None:
        near += sf.descendants_of(faction, "unit")
    for u in near + sf.of_kind("unit"):
        m = _UNIT_SHAPE.match(sf.lines[u.start])
        if m:
            out.unit_gap, out.unit_pad = m.group("gap"), m.group("pad")
            break
    for u in sf.of_kind("unit"):
        m = _UNIT_SHAPE.match(sf.lines[u.start])
        if m:
            out.pads.setdefault(m.group("name").strip(), m.group("pad"))
    return out


# ---------------------------------------------------------------------------
# the lines themselves


def character_line(spec: Spec, shape: Shape) -> str:
    """``character <name>, <type>, <sex>, [rank,] age N, x N, y N, …``

    Written by looking at what the spec has rather than by filling in a
    template, which is the same reason 16b reads it that way: the rank, the sex
    and all seven tail fields are optional and a blank field left in place is
    the trailing comma DaC has on line 3747.
    """
    parts = [spec.name.strip(), spec.type]
    if spec.gender:
        parts.append(spec.gender)
    if spec.rank:
        parts.append(spec.rank)
    parts += [f"age {spec.age}", f"x {spec.x}", f"y {spec.y}"]
    for key in TAIL:
        value = str(spec.tail.get(key) or "").strip()
        if value:
            parts.append(f"{key} {value}")
    head = f"{shape.indent}character{shape.gap}"
    if spec.sub_faction:
        head += f"sub_faction {spec.sub_faction}{shape.sep}"
    return head + shape.sep.join(parts)


def traits_line(traits: Sequence[Tuple[str, object]], shape: Shape) -> str:
    return (f"{shape.indent}traits{shape.trait_gap}"
            + shape.trait_sep.join(f"{n} {v}" for n, v in traits if n))


def ancillaries_line(names: Sequence[str], shape: Shape) -> str:
    return (f"{shape.indent}ancillaries{shape.anc_gap}"
            + shape.anc_sep.join(n for n in names if n))


def unit_line(a: Army, shape: Shape) -> str:
    """``unit <name> exp N armour N weapon_lvl N``, padded like its own kind.

    The tabs between the name and the numbers are decoration the engine never
    reads, and they are still worth getting right: a file where one added
    regiment does not line up with the twenty others of the same unit reads as
    a file something has been at.
    """
    pad = shape.pads.get(a.unit, shape.unit_pad)
    return (f"{shape.indent}unit{shape.unit_gap}{a.unit}{pad}"
            f"exp {a.exp} armour {a.armour} weapon_lvl {a.weapon_lvl}")


def _army_span(sf: StratFile, army: Node) -> Tuple[int, int]:
    """The ``army`` line and its regiments, and not the blank line after them.

    Read off the units rather than off ``army.end``, which is the line before
    whatever closed the character and is therefore usually the blank line that
    separates two people. Deleting an army must not take that with it.
    """
    units = sf.children_of(army, "unit")
    return army.start, (units[-1].end if units else army.start)


def render_character(sf: StratFile, node: Node, spec: Spec) -> List[str]:
    """The character's lines as they would be written, and no others.

    Every line whose values did not change is left exactly as it was, which is
    what keeps the file's own tabs, its trailing spaces and the comment somebody
    left on a regiment. A no-op render of all 316 characters on the installed
    campaigns comes back byte for byte, and the suite checks it.
    """
    base = list(sf.lines[node.start:node.end + 1])
    shape = shape_of(sf, faction_of(sf, node), node)
    cur = read_spec(sf, node)
    rewrites: Dict[int, str] = {}
    drop: set = set()
    inserts: Dict[int, List[str]] = {}

    head_changed = any(getattr(cur, s) != getattr(spec, s)
                       for s in HEAD + ("sub_faction",)) or cur.tail != spec.tail
    if head_changed:
        rewrites[0] = rewrite_line(base[0], character_line(spec, shape))

    home = 1                                  # where an added line would go
    for slot, values, build in (
            ("traits", spec.traits, lambda: traits_line(spec.traits, shape)),
            ("ancillaries", spec.ancillaries,
             lambda: ancillaries_line(spec.ancillaries, shape))):
        at = node.field_lines.get(slot)
        was = cur.traits if slot == "traits" else cur.ancillaries
        local = at - node.start if at is not None else None
        if local is not None:
            home = max(home, local + 1)
        if list(was) == list(values):
            continue
        if values and local is not None:
            rewrites[local] = rewrite_line(base[local], build())
        elif values:
            inserts.setdefault(home, []).append(build())
            home += 1
        elif local is not None:
            drop.add(local)

    army = next(iter(sf.children_of(node, "army")), None)
    if army is not None:
        home = max(home, _army_span(sf, army)[1] - node.start + 1)
    if cur.army != spec.army:
        _render_army(sf, node, base, army, spec, shape, home,
                     rewrites, drop, inserts)
    return assemble(base, rewrites, drop, inserts)


def _render_army(sf: StratFile, node: Node, base: List[str],
                 army: Optional[Node], spec: Spec, shape: Shape, home: int,
                 rewrites: Dict[int, str], drop: set,
                 inserts: Dict[int, List[str]]) -> None:
    """The regiments, diffed by position the way 16h diffs buildings.

    A regiment that keeps its unit and its three numbers is not rewritten, so
    editing the fourth of five leaves the other four exactly as they were.
    """
    old = sf.children_of(army, "unit") if army is not None else []
    want = list(spec.army)
    if not want:
        if army is not None:
            start, end = _army_span(sf, army)
            drop |= set(range(start - node.start, end - node.start + 1))
        return
    if army is None:
        inserts.setdefault(home, []).extend(
            [f"{shape.indent}army{shape.army_gap}"]
            + [unit_line(a, shape) for a in want])
        return
    for i, a in enumerate(want[:len(old)]):
        u = old[i]
        was = Army(unit=u.name, exp=int(u.get("exp") or 0),
                   armour=int(u.get("armour") or 0),
                   weapon_lvl=int(u.get("weapon_lvl") or 0))
        if was == a:
            continue
        rewrites[u.start - node.start] = rewrite_line(
            base[u.start - node.start], unit_line(a, shape))
    for u in old[len(want):]:
        drop |= set(range(u.start - node.start, u.end - node.start + 1))
    if len(want) > len(old):
        at = ((old[-1].end if old else army.start) - node.start) + 1
        inserts.setdefault(at, []).extend(
            unit_line(a, shape) for a in want[len(old):])


def new_character(sf: StratFile, faction: Node, spec: Spec) -> List[str]:
    """A whole new character block, written in the shape of the ones beside it.

    The blank line at the end is the block's own separator - 216 of vanilla's
    216 character spans end on one - so it is written here rather than left for
    whatever the block lands in front of.
    """
    shape = shape_of(sf, faction)
    out = [character_line(spec, shape) + shape.trail]
    if spec.traits:
        out.append(traits_line(spec.traits, shape) + shape.trail)
    if spec.ancillaries:
        out.append(ancillaries_line(spec.ancillaries, shape))
    if spec.army:
        out.append(f"{shape.indent}army{shape.army_gap}")
        out += [unit_line(a, shape) for a in spec.army]
    out.append("")
    return out


# ---------------------------------------------------------------------------
# the plan


#: The records this phase does not touch. A count that moves on any of them is
#: a splice that went somewhere it was not asked to go.
UNTOUCHED = ("faction", "settlement", "building", "region", "fort",
             "watchtower", "resource", "faction_standings",
             "faction_relationships", "character_record", "relative")

ACTIONS = ("edit", "add", "delete", "move")


@dataclass
class CharPlan:
    """One character's save, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    faction: str = ""
    name: str = ""
    action: str = "edit"
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the character's new lines, for the preview
    block: str = ""
    #: ``"england -> france"`` when the character changes hands, else ``""``
    moved: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} character {self.name} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign} "
                f"({self.faction}, {len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"faction": self.faction, "name": self.name,
                "action": self.action, "campaign": self.campaign,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "findings": list(self.findings),
                "block": self.block, "moved": self.moved,
                "ok": not self.errors and bool(self.text)}


def _char_texts(sf: StratFile) -> Dict[str, int]:
    """Every character block's own text, counted.

    Counted rather than keyed, because a name is not unique: five of Third Age
    Reforged's factions have two characters with one name. The guard below asks
    whether the bag of blocks changed by exactly the one this save is about,
    which needs no key at all.
    """
    out: Dict[str, int] = {}
    for n in sf.of_kind("character"):
        text = "\n".join(sf.lines[n.start:n.end + 1])
        out[text] = out.get(text, 0) + 1
    return out


def _guard(before: StratFile, after: StratFile, action: str,
           was: str, now: str) -> List[str]:
    """What the splice did that it was never asked to do.

    The bag of character blocks is compared with the one block this save is
    about taken out of each side. Whatever is left has to match exactly: an
    edit that swallowed the person below it, a move that landed inside somebody
    else's block and a delete that took the blank line off the next character
    all show up here as a block that is not in both bags.
    """
    out: List[str] = []
    b, a = before.counts(), after.counts()
    for kind in UNTOUCHED:
        if b.get(kind, 0) != a.get(kind, 0):
            out.append(f"this would leave {a.get(kind, 0)} {kind} record(s) "
                       f"where the file has {b.get(kind, 0)}, and 16i edits "
                       f"one character")
    step = {"edit": 0, "move": 0, "add": 1, "delete": -1}[action]
    if a.get("character", 0) != b.get("character", 0) + step:
        out.append(f"this would leave {a.get('character', 0)} characters where "
                   f"the file has {b.get('character', 0)}")
        return out
    if before.rosters != after.rosters:
        out.append("this would change the playable, unlockable or nonplayable "
                   "lists, which no character edit does")
    if before.globals != after.globals:
        out.append("this would change the campaign's own header values")
    places_b, odd_b = stratedit.blocks_by_region(before)
    places_a, odd_a = stratedit.blocks_by_region(after)
    if places_b != places_a or odd_b != odd_a:
        out.append("this would rewrite a settlement block, and 16i writes "
                   "people")
    if out:
        return out

    bag_b, bag_a = _char_texts(before), _char_texts(after)
    for bag, text in ((bag_b, was), (bag_a, now)):
        if text and bag.get(text):
            bag[text] -= 1
            if not bag[text]:
                del bag[text]
    if bag_b != bag_a:
        gone = [t for t in bag_b if bag_b[t] != bag_a.get(t, 0)]
        who = gone[0].splitlines()[0].strip()[:60] if gone else ""
        out.append("this would rewrite a character block nobody asked it to"
                   + (f", starting with `{who}`" if who else ""))
    return out


def _describe(before: Optional[Spec], after: Optional[Spec]) -> List[str]:
    """What changed, said the way somebody would say it out loud."""
    out: List[str] = []
    if before is None or after is None:
        return out
    for slot in HEAD + ("sub_faction",):
        a, b = getattr(before, slot), getattr(after, slot)
        if a != b:
            out.append(f"{slot.replace('_', ' ')}: {a if a not in (None, '') else '(none)'}"
                       f" -> {b if b not in (None, '') else '(none)'}")
    for key in TAIL:
        a, b = before.tail.get(key, ""), after.tail.get(key, "")
        if a != b:
            out.append(f"{key}: {a or '(none)'} -> {b or '(none)'}")
    if before.traits != after.traits:
        was = {n: v for n, v in before.traits}
        now = {n: v for n, v in after.traits}
        for n in sorted(set(was) | set(now)):
            if was.get(n) != now.get(n):
                out.append(f"trait {n}: {was.get(n, '(none)')} -> "
                           f"{now.get(n, '(none)')}")
    if before.ancillaries != after.ancillaries:
        gone = [a for a in before.ancillaries if a not in after.ancillaries]
        got = [a for a in after.ancillaries if a not in before.ancillaries]
        if got:
            out.append("ancillaries added: " + ", ".join(got))
        if gone:
            out.append("ancillaries removed: " + ", ".join(gone))
    if before.army != after.army:
        was = [a.unit for a in before.army]
        now = [a.unit for a in after.army]
        gone = [u for u in was if u not in now]
        got = [u for u in now if u not in was]
        if got:
            out.append("regiments added: " + ", ".join(got))
        if gone:
            out.append("regiments removed: " + ", ".join(gone))
        if not got and not gone:
            out.append(f"army rewritten ({len(now)} regiments)")
    return out


def plan_character(mod, facts, body: dict) -> CharPlan:
    """Work out the whole new ``descr_strat.txt`` for one character's save.

    ``body`` is ``{faction, character, line, action, edits, traits,
    ancillaries, army, owner, raw_block}``. ``action`` is one of edit, add,
    delete and move; ``line`` is the 1-based line the panel was looking at,
    which is what tells two characters of one name apart.

    **The file is re-read here rather than taken from ``facts``**, for the
    reason 16h states where it does the same: the fact table is a cache, and a
    writer that writes out of a cache writes over whatever changed under it.
    ``facts`` is the vocabulary the findings are measured against, and the map
    the coordinates are checked against.
    """
    from .campmap import MapError

    campaign = str(body.get("campaign") or "") or facts.campaign
    action = str(body.get("action") or "edit").lower()
    p = CharPlan(mod=mod, campaign=campaign, action=action,
                 faction=str(body.get("faction") or "").strip(),
                 name=str(body.get("character") or "").strip())
    if action not in ACTIONS:
        p.errors.append(f"no such action {action!r}. The four are "
                        + ", ".join(ACTIONS))
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = sf.path

    faction = sf.faction(p.faction)
    if faction is None:
        p.errors.append(
            f"{p.faction or '(nothing)'} has no faction block in {campaign}'s "
            f"descr_strat.txt. Creating a faction is 16j; cloning one that "
            f"already works is what the Factions screen does today")
        return p

    node = None
    before: Optional[Spec] = None
    was_text = ""
    if action != "add":
        node = find_character(sf, p.faction, p.name,
                              int(body.get("line") or 0))
        if node is None:
            p.errors.append(f"{p.faction} has no character called {p.name!r} "
                            f"in {campaign}'s descr_strat.txt")
            return p
        before = read_spec(sf, node)
        p.name = node.name
        was_text = "\n".join(sf.lines[node.start:node.end + 1])

    spec = spec_from_body(body, before)
    lines, dest = _splice(sf, p, faction, node, spec, body)
    if p.errors:
        return p

    text = serialise(sf, lines)
    done = campstrat.parse_strat(text)
    now_node = (None if action == "delete"
                else find_character(done, dest, spec.name))
    now_text = ("" if now_node is None
                else "\n".join(done.lines[now_node.start:now_node.end + 1]))
    if action != "delete" and now_node is None:
        p.errors.append(f"after this save nothing in {dest}'s block is called "
                        f"{spec.name!r}")
        return p
    p.errors += _guard(sf, done, action, was_text, now_text)
    if p.errors:
        return p

    voc = Vocabulary(facts, done)
    p.block = now_text
    if action != "delete":
        p.findings = check_character(voc, spec, getattr(facts, "cm", None))
        p.findings += check_pool(voc, dest, spec.name)
    p.findings += check_faction(done, done.faction(dest), voc)
    if action == "move" or (before is not None and dest != p.faction):
        p.findings += check_faction(done, done.faction(p.faction), voc)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(before, spec if action != "delete" else None)
    if action == "add":
        p.changes.insert(0, f"a new {spec.type or 'character'} called "
                            f"{spec.name} in {dest}")
    elif action == "delete":
        p.changes.insert(0, f"{p.name} is taken out of {p.faction}")
    if p.moved:
        p.changes.append(f"faction: {p.moved}")

    p.text = "" if text == sf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _splice(sf: StratFile, p: CharPlan, faction: Node, node: Optional[Node],
            spec: Spec, body: dict) -> Tuple[List[str], str]:
    """The new lines, and which faction the character ends up in.

    Four shapes, and each is the smallest edit that does the job: a rewrite of
    the block's own lines, an insert after the faction's last character, a
    delete of the span, and a slice moved from one faction's list to another's.
    """
    action = p.action
    raw = str(body.get("raw_block") or "")

    if action == "delete":
        return sf.lines[:node.start] + sf.lines[node.end + 1:], p.faction

    if raw.strip():
        block = split_block(raw)
        head = _clean(block[0]) if block else ""
        if not head.lower().startswith("character"):
            p.errors.append(
                "a character block opens with the word `character`. This one "
                f"opens with {head!r}")
            return sf.lines, p.faction
    elif action == "add":
        block = new_character(sf, faction, spec)
    else:
        block = render_character(sf, node, spec)

    if action == "add":
        at = insert_at(sf, faction)
        return sf.lines[:at] + block + sf.lines[at:], p.faction

    if action == "edit":
        return (sf.lines[:node.start] + block + sf.lines[node.end + 1:],
                p.faction)

    # move: the block leaves one faction's list and joins another's
    dest_name = str(body.get("owner") or "").strip() or p.faction
    dest = sf.faction(dest_name)
    if dest is None:
        p.errors.append(
            f"{dest_name} has no faction block in {p.campaign}'s "
            f"descr_strat.txt, so nobody there can be given a character")
        return sf.lines, p.faction
    if dest.start == faction.start:
        p.errors.append(f"{p.name} is already in {dest_name}")
        return sf.lines, p.faction
    lines = sf.lines[:node.start] + block + sf.lines[node.end + 1:]
    mid = campstrat.parse_strat(serialise(sf, lines))
    moved = find_character(mid, p.faction, spec.name)
    target = mid.faction(dest_name)
    if moved is None or target is None:
        p.errors.append("the edited block could not be found again to move it")
        return sf.lines, p.faction
    at = insert_at(mid, target)
    p.moved = f"{p.faction} -> {dest_name}"
    return move_lines(mid.lines, (moved.start, moved.end), at), dest_name


# ---------------------------------------------------------------------------
# the save


def apply_character(p: CharPlan) -> dict:
    """Write a planned save, with the same backups and undo as any other job.

    The same shape as :func:`~unittransfer.stratedit.apply_settlement`, and
    ``map.rwm`` is left alone here for the same reason: it is compiled from the
    map layers and ``descr_regions.txt``, and the campaign file is read fresh at
    every campaign start.
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
    rel = f"{campstrat.CAMPAIGN_DIR_REL}/{p.campaign}/{campstrat.STRAT_NAME}"
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [],
                                      "deleted": []}

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
    write_text(target, p.text, campstrat.ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        "action": "character",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {"campaign": p.campaign, "faction": p.faction,
                    "what": p.action, "moved": p.moved},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CHARACTER %s %s in %s/%s - %d change(s), id=%s",
             p.action, p.name, mod.name, p.campaign, len(p.changes), tid)
    return {"id": tid, "name": p.name, "faction": p.faction,
            "campaign": p.campaign, "record": rec}


# ---------------------------------------------------------------------------
# the form


def faction_detail(facts, faction: str) -> dict:
    """One faction's people, everything the panel shows, in one call.

    Read out of the fact table's own :class:`~unittransfer.campstrat.StratFile`
    rather than off the disk, which is 16g's rule and what makes opening a
    faction free: the parse is already done and cached.
    """
    from .campmap import MapError

    sf = getattr(facts, "strat", None)
    if sf is None:
        raise MapError(f"{facts.strat_rel} could not be read, so this map has "
                       f"no campaign to edit")
    node = sf.faction(faction)
    if node is None:
        raise MapError(f"no faction called {faction!r} in "
                       f"{facts.campaign}'s descr_strat.txt")
    voc = Vocabulary(facts, sf)
    cm = getattr(facts, "cm", None)
    people = []
    for c in characters_of(sf, node):
        spec = read_spec(sf, c)
        people.append({
            "name": c.name, "line": c.start + 1,
            "lines": [c.start + 1, c.end + 1],
            "type": spec.type, "gender": spec.gender, "rank": spec.rank,
            "age": spec.age, "x": spec.x, "y": spec.y,
            "sub_faction": spec.sub_faction,
            "army": len(spec.army),
            "traits": len(spec.traits),
            "ancillaries": len(spec.ancillaries),
            "spec": spec.payload(),
            "findings": check_character(voc, spec, cm)
            + check_pool(voc, faction, c.name),
            "problems": list(c.problems),
        })
    return {
        "faction": faction,
        "label": facts.faction_label(faction),
        "campaign": facts.campaign,
        "file": facts.strat_rel,
        "leader": leader_of(sf, node),
        "heir": heir_of(sf, node),
        "characters": people,
        "records": [{"name": r.name, "line": r.start + 1,
                     "gender": str(r.get("gender") or ""),
                     "age": r.get("age"), "dead": r.get("dead"),
                     "leadership": str(r.get("leadership") or ""),
                     "text": sf.lines[r.start]}
                    for r in records_of(sf, node)],
        "relatives": [{"names": list(r.get("names") or []),
                       "line": r.start + 1}
                      for r in relatives_of(sf, node)],
        "findings": check_faction(sf, node, voc),
        "vocab": voc.payload(),
    }
