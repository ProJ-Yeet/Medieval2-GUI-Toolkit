"""``descr_strat.txt``, read: the whole campaign as a tree of lines.

The file the entire campaign is defined in. Which faction owns which city, who
its general is, what regiments he is standing with, who his father was, who his
faction is at war with, where every fort and watchtower stands. 13,153 lines of
it in DaC, and 16h to 16j all write into it, so the one thing 16b has to get
right is that reading it and writing it back changes nothing.

**The model is lines plus an index over them, never objects plus a serialiser.**
Every node here carries the line it started on, the line it ends on and the line
each of its fields came from; :meth:`StratFile.serialise` joins
:attr:`StratFile.lines` and hands back the bytes that were read. An edit rewrites
the one line it means to change and leaves the tabs, the banner comments and the
commented-out unit on line 1965 exactly where they were. Demir's tool re-parses
the whole file after every edit - eight to ten times to save one faction detail -
and the reason it can afford to is that it throws the formatting away.

The shape of the file, in the order it appears:

    campaign <name>
    playable / unlockable / nonplayable … end     the three rosters
    start_date, end_date, timescale, and the campaign flags
    resource <name>, <x>, <y>                     1,131 of them in DaC
    faction <name>, <ai personality>              31 blocks, each holding
        ai_label / denari / denari_kings_purse
        settlement [castle] { level, region, … building { type … } }
        character … / traits … / ancillaries … / army / unit …
        character_record …                        the off-map family
        relative …                                the family tree
    faction_standings …                           the diplomacy section, which
    faction_relationships …                       every faction block precedes
    region <name> / farming_level / famine_threat / fort … / watchtower …
    script / campaign_script.txt

Three things decide where a block ends, and all three are needed:

**Brace depth, counted on the line with its comment stripped.** A `region` line
at depth 0 opens the regions section; the same word at depth 1 is a settlement's
own field. Mylae's ``factionBlockOps.js`` has this rule and counts braces on the
raw line instead, so a commented-out brace shifts its depth.

**Terminators.** A faction block runs to the next `faction` header or to the
first of `faction_standings`, `faction_relationships`, a depth-0 `region` or
`script`. A character runs to the next thing that can only start something else.

**Nothing else.** Blank lines and comments belong to whatever block they fall
in and are never a boundary, because a mod's own banner comment sits between two
factions as often as inside one.

**Nothing here raises.** DaC's file has nine lines that do not parse, and every
one of them is a real mod defect rather than a gap in the format::

    3747   … portrait Magor,            a trailing comma, so an empty field
    5376   character Sauron, …          no age at all, on the faction leader
    8464   settlement tyuiop            a settlement type that does not exist
    9703   … named character, general   two type words where one is allowed
    9983   exp 0 rmour 0 weapon_lvl 1   "armour" misspelled
    10438  … named character, general   the second one
    10581  exp 1 armour 1 weapon_lv     truncated, no value
    10947  exp 0 rmour 0 weapon_lvl 1   and two more of the misspelling
    10948  exp 0 rmour 0 weapon_lvl 1

Vanilla's two campaigns have none of these; a parser that refused any of DaC's
nine would refuse DaC. So a node that cannot read a field keeps the field empty,
records the reason in :attr:`Node.problems` and stays in the tree with its line
span intact, which is also what lets 16f report all nine by line number instead
of leaving them invisible.
"""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

#: Plain 8-bit game data, as everywhere else
ENCODING = "latin-1"

CAMPAIGN_DIR_REL = "world/maps/campaign"
STRAT_NAME = "descr_strat.txt"
#: the campaign every mod has, and the one the toolkit means by "the campaign"
DEFAULT_CAMPAIGN = "imperial_campaign"

#: the three faction lists at the top, in the order the file writes them
ROSTERS = ("playable", "unlockable", "nonplayable")

#: single-word flags on the campaign header
CAMPAIGN_FLAGS = (
    "marian_reforms_disabled", "rebelling_characters_active",
    "gladiator_uprising_disabled", "night_battles_enabled",
    "show_date_as_turns", "disable_all_ai_battle_participation",
)

#: ``keyword value`` globals on the campaign header
CAMPAIGN_VALUES = ("start_date", "end_date", "timescale", "brigand_spawn_value",
                   "pirate_spawn_value", "free_upkeep_forts")

#: Single-word flags inside a faction block. All three are measured, not
#: guessed: ``dead_until_resurrected`` appears three times in DaC and twice in
#: vanilla, ``re_emergent`` once in DaC, and ``undiscovered`` once in vanilla,
#: on the Aztecs, who do not exist until somebody sails far enough west.
FACTION_FLAGS = ("dead_until_resurrected", "re_emergent", "undiscovered")

#: what a character may be. Anything else on that line is a defect, not a kind.
CHARACTER_TYPES = ("named character", "general", "admiral", "spy", "merchant",
                   "diplomat", "priest", "assassin", "princess", "heretic",
                   "witch", "inquisitor")

#: The last field of a ``character_record``, and where each word was found.
#: ``never_a_leader`` is all vanilla writes - 61 in the imperial campaign and 4
#: in the prologue - and 16i found ``current_heir`` on three of Third Age
#: Reforged's, which the first four words here did not cover, so those three
#: records came back with no leadership at all. The pairs are kept whole rather
#: than reduced to a rule, because a word the engine does not know is a defect
#: worth reporting rather than a pattern to match loosely.
LEADERSHIP = ("past_leader", "never_a_leader", "current_leader", "current_heir",
              "leader", "heir")

#: a depth-0 keyword that closes whatever faction block is open
_FACTION_TERMINATORS = ("faction_standings", "faction_relationships",
                        "action_relationships", "script")


def _clean(line: str) -> str:
    """The line without its comment or its surrounding space.

    The engine's comment character is ``;`` and it runs to end of line. Braces
    inside a comment are not braces, which is why depth is counted on this and
    never on the raw line.
    """
    return line.split(";", 1)[0].strip()


@dataclass
class Node:
    """One thing in the file, and every line it is made of.

    A one-line record (a resource, a fort, a unit) has ``start == end``. A block
    (a faction, a settlement, a character with its army) spans its lines
    inclusive, comments and blank lines included, so that moving or deleting one
    is a slice rather than a reconstruction.
    """

    kind: str
    name: str = ""
    start: int = 0
    end: int = 0
    parent: int = -1
    children: List[int] = field(default_factory=list)
    fields: Dict[str, object] = field(default_factory=dict)
    #: field name to the index of the line it was read from
    field_lines: Dict[str, int] = field(default_factory=dict)
    problems: List[str] = field(default_factory=list)

    def get(self, key: str, default=None):
        return self.fields.get(key, default)

    @property
    def span(self) -> Tuple[int, int]:
        return self.start, self.end


@dataclass
class StratFile:
    """``descr_strat.txt`` as its own lines, plus a tree and an index."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    nodes: List[Node] = field(default_factory=list)
    roots: List[int] = field(default_factory=list)
    #: campaign-header globals, and the line each came from
    campaign: str = ""
    globals: Dict[str, object] = field(default_factory=dict)
    global_lines: Dict[str, int] = field(default_factory=dict)
    rosters: Dict[str, List[str]] = field(default_factory=dict)
    roster_lines: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    path: Optional[Path] = None
    #: every node's start line. Nodes are opened as their first line is read, so
    #: this is already sorted and both lookups below can bisect it.
    _starts: List[int] = field(default_factory=list)

    # -- the file ------------------------------------------------------------

    def serialise(self) -> str:
        """The file, exactly as it would go back to disk."""
        return (self.newline.join(self.lines)
                + (self.newline if self.trailing_newline else ""))

    # -- the index -----------------------------------------------------------

    def node_at(self, line: int) -> Optional[Node]:
        """The innermost node containing ``line``, without scanning the file.

        Nodes come out of the parse in document order and nest properly, so the
        last node starting at or before ``line`` either contains it or is a
        closed sibling of something that does. Binary search, then walk up the
        parents: no lookup here is ever O(lines), which is the whole point of
        keeping an index rather than re-reading.
        """
        if not self._starts:
            return None
        at = bisect_right(self._starts, line) - 1
        while at >= 0:
            node = self.nodes[at]
            if node.start <= line <= node.end:
                return node
            parent = node.parent
            while parent >= 0:
                p = self.nodes[parent]
                if p.start <= line <= p.end:
                    return p
                parent = p.parent
            at -= 1
        return None

    def index_of(self, node: Node) -> int:
        """Where ``node`` sits in :attr:`nodes`, by bisect rather than by scan."""
        at = bisect_right(self._starts, node.start) - 1
        while at >= 0 and self.nodes[at].start == node.start:
            if self.nodes[at] is node:
                return at
            at -= 1
        return -1

    def of_kind(self, kind: str) -> List[Node]:
        return [n for n in self.nodes if n.kind == kind]

    def children_of(self, node: Node, kind: str = "") -> List[Node]:
        out = [self.nodes[i] for i in node.children]
        return [n for n in out if n.kind == kind] if kind else out

    def descendants_of(self, node: Node, kind: str = "") -> List[Node]:
        """Everything under ``node``, as a slice rather than a search.

        A node is opened as its first line is read, so a block and everything
        inside it are contiguous in :attr:`nodes`. "Every unit in this faction"
        is therefore one bisect and a slice of a few hundred entries, not a walk
        over six thousand.
        """
        first = self.index_of(node)
        if first < 0:
            return []
        last = bisect_right(self._starts, node.end)
        out = self.nodes[first + 1:last]
        return [n for n in out if n.kind == kind] if kind else out

    def faction(self, name: str) -> Optional[Node]:
        low = name.lower()
        return next((n for n in self.nodes
                     if n.kind == "faction" and n.name.lower() == low), None)

    def counts(self) -> Dict[str, int]:
        """How many of each kind, for a status line or a test."""
        out: Dict[str, int] = {}
        for n in self.nodes:
            out[n.kind] = out.get(n.kind, 0) + 1
        return out

    @property
    def problems(self) -> List[Tuple[int, str, str]]:
        """``(line, kind, message)`` for everything that did not parse cleanly."""
        return [(n.start, n.kind, p) for n in self.nodes for p in n.problems]


# ---------------------------------------------------------------------------
# the parse


class _Parser:
    """One pass over the lines, holding the stack of blocks that are open."""

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.out = StratFile(lines=lines)
        self.stack: List[int] = []
        self.depth = 0

    # -- the stack -----------------------------------------------------------

    def open(self, kind: str, at: int, name: str = "") -> int:
        node = Node(kind=kind, name=name, start=at, end=at)
        idx = len(self.out.nodes)
        self.out.nodes.append(node)
        if self.stack:
            node.parent = self.stack[-1]
            self.out.nodes[node.parent].children.append(idx)
        else:
            self.out.roots.append(idx)
        self.stack.append(idx)
        return idx

    def record(self, kind: str, at: int, name: str = "") -> Node:
        """A one-line node under whatever is open."""
        idx = self.open(kind, at, name)
        self.stack.pop()
        return self.out.nodes[idx]

    def close(self, at: int, *kinds: str) -> None:
        """Close the innermost open blocks of these kinds, ending at ``at``."""
        while self.stack and self.out.nodes[self.stack[-1]].kind in kinds:
            self.out.nodes[self.stack.pop()].end = at

    def close_all(self, at: int) -> None:
        while self.stack:
            self.out.nodes[self.stack.pop()].end = at

    @property
    def top(self) -> Optional[Node]:
        return self.out.nodes[self.stack[-1]] if self.stack else None

    def open_of(self, kind: str) -> Optional[Node]:
        for i in reversed(self.stack):
            if self.out.nodes[i].kind == kind:
                return self.out.nodes[i]
        return None


def parse_strat(text: str) -> StratFile:
    """Read the whole file in one pass. Never raises.

    The one-pass rule is not a performance boast, it is the model: a second pass
    would need somewhere to put what the first one learned, and that somewhere
    is exactly the structure this returns.
    """
    from .triggers import split_lines
    lines, newline, trailing = split_lines(text)
    p = _Parser(lines)
    p.out.newline, p.out.trailing_newline = newline, trailing

    roster: Optional[str] = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = _clean(raw)
        if not s:
            i += 1
            continue

        # the three faction lists are the only place `end` means anything
        if roster is not None:
            if s.lower() == "end":
                start, _ = p.out.roster_lines[roster]
                p.out.roster_lines[roster] = (start, i)
                roster = None
            elif s.lower() not in ROSTERS:
                p.out.rosters[roster].append(s.split()[0])
            i += 1
            continue
        if s.lower() in ROSTERS:
            roster = s.lower()
            p.out.rosters.setdefault(roster, [])
            p.out.roster_lines[roster] = (i, i)
            i += 1
            continue

        word = s.split()[0]

        if p.depth == 0:
            _line_at_depth_zero(p, i, s, word)
        else:
            _line_inside_braces(p, i, s, word)

        p.depth += s.count("{") - s.count("}")
        if p.depth < 0:                       # a stray closing brace
            p.depth = 0
        i += 1

    p.close_all(len(lines) - 1)
    _index(p.out)
    return p.out


def _line_at_depth_zero(p: _Parser, i: int, s: str, word: str) -> None:
    out = p.out

    # a settlement's opening brace is read here, because depth only rises after
    # the line that raised it
    if s.strip("{} \t") == "":
        return

    if word == "campaign" and not out.campaign:
        out.campaign = s.split(None, 1)[1].strip() if " " in s or "\t" in s else ""
        out.global_lines["campaign"] = i
        return

    if word in CAMPAIGN_FLAGS:
        out.globals[word] = True
        out.global_lines[word] = i
        return
    if word in CAMPAIGN_VALUES:
        out.globals[word] = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
        out.global_lines[word] = i
        return

    if word == "resource":
        _resource(p, i, s)
        return

    if word == "faction":
        p.close(i - 1, "unit", "army", "character", "settlement", "faction")
        _faction(p, i, s)
        return

    if word in _FACTION_TERMINATORS or (word == "region" and len(s.split()) > 1):
        p.close(i - 1, "unit", "army", "character", "settlement", "faction", "region")

    if word == "faction_standings":
        _standings(p, i, s)
        return
    if word in ("faction_relationships", "action_relationships"):
        _relationships(p, i, s)
        return
    if word == "region":
        _region(p, i, s)
        return
    if word in ("farming_level", "famine_threat"):
        region = p.open_of("region")
        if region is None:
            p.record(word, i).problems.append(f"{word} with no region above it")
            return
        value = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
        region.fields[word] = int(value) if re.fullmatch(r"-?\d+", value) else value
        region.field_lines[word] = i
        region.end = max(region.end, i)
        return
    if word == "script":
        node = p.record("script", i)
        node.fields["file"] = ""
        return

    # a bare filename under `script`, and anything else we do not know
    prev = out.nodes[-1] if out.nodes else None
    if prev is not None and prev.kind == "script" and not prev.fields.get("file"):
        prev.fields["file"] = s
        prev.field_lines["file"] = i
        prev.end = i
        return

    _inside_faction(p, i, s, word)


def _line_inside_braces(p: _Parser, i: int, s: str, word: str) -> None:
    """A line inside a ``{ … }``: a settlement's fields, or a building block."""
    node = p.top
    if node is None:
        return
    if word == "building" and node.kind == "settlement":
        p.open("building", i)
        return
    if s == "{":
        return
    if s.startswith("}"):
        # the innermost brace block closes here
        if node.kind == "building":
            node.end = i
            p.stack.pop()
        elif node.kind == "settlement":
            node.end = i
            p.stack.pop()
        return

    if node.kind == "building":
        if word == "type":
            rest = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
            node.fields["type"] = rest
            node.field_lines["type"] = i
            node.name = rest.split()[0] if rest else ""
            bits = rest.split()
            if len(bits) > 1:
                node.fields["level"] = bits[1]
            node.end = i
        return

    if node.kind == "settlement":
        _settlement_field(node, i, s, word)


def _settlement_field(node: Node, i: int, s: str, word: str) -> None:
    if word in ("level", "region", "plan_set", "faction_creator", "population",
                "year_founded", "creator_faction"):
        value = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
        node.fields[word] = int(value) if word in ("population", "year_founded") \
            and re.fullmatch(r"-?\d+", value) else value
        node.field_lines[word] = i
        if word == "region":
            node.name = value
        node.end = i


# ---------------------------------------------------------------------------
# the records, one function each


_RESOURCE = re.compile(r"^resource\s+([\w-]+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)", re.I)


def _resource(p: _Parser, i: int, s: str) -> None:
    node = p.record("resource", i)
    m = _RESOURCE.match(s)
    if not m:
        node.problems.append(f"resource line does not read as `resource <name>, <x>, <y>`: {s!r}")
        return
    node.name = m.group(1)
    node.fields.update(name=m.group(1), x=int(m.group(2)), y=int(m.group(3)))
    for k in ("name", "x", "y"):
        node.field_lines[k] = i


def _faction(p: _Parser, i: int, s: str) -> None:
    """``faction <name>, <ai personality>`` opens a block that runs to the next.

    The tail is two words in every real file - ``balanced smith``,
    ``trader caesar`` - and they are the AI's personality and its named
    template. It is kept whole as well as split, because nothing here has a
    source that says which word is which and inventing one would be worse than
    handing the UI the text the file actually holds.
    """
    body = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
    name, _, tail = body.partition(",")
    idx = p.open("faction", i, name.strip())
    node = p.out.nodes[idx]
    node.fields["name"] = name.strip()
    node.fields["ai"] = tail.strip()
    node.fields["ai_words"] = tail.split()
    node.field_lines["name"] = node.field_lines["ai"] = i
    if not name.strip():
        node.problems.append("faction line has no name")


def _inside_faction(p: _Parser, i: int, s: str, word: str) -> None:
    """Everything that lives in a faction block and is not braced."""
    faction = p.open_of("faction")

    if word in FACTION_FLAGS and faction is not None:
        faction.fields[word] = True
        faction.field_lines[word] = i
        faction.end = i
        return
    if word in ("ai_label", "denari", "denari_kings_purse") and faction is not None:
        value = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
        faction.fields[word] = int(value) if re.fullmatch(r"-?\d+", value) else value
        faction.field_lines[word] = i
        faction.end = i
        return

    if word == "settlement":
        p.close(i - 1, "unit", "army", "character")
        _settlement(p, i, s)
        return
    if word == "character":
        p.close(i - 1, "unit", "army", "character")
        _character(p, i, s)
        return
    if word == "character_record":
        p.close(i - 1, "unit", "army", "character")
        _character_record(p, i, s)
        return
    if word == "relative":
        p.close(i - 1, "unit", "army", "character")
        _relative(p, i, s)
        return
    if word in ("traits", "ancillaries"):
        _character_list(p, i, s, word)
        return
    if word == "army":
        p.close(i - 1, "unit", "army")
        p.open("army", i)
        return
    if word == "unit":
        _unit(p, i, s)
        return
    if word in ("fort", "watchtower"):
        _fortification(p, i, s, word)
        return

    node = p.top
    if node is not None:
        node.problems.append(f"line {i + 1} not recognised inside {node.kind}: {s!r}")


def _settlement(p: _Parser, i: int, s: str) -> None:
    """``settlement`` or ``settlement castle``, then a braced block.

    DaC writes ``settlement tyuiop`` on line 8464 - a settlement type that does
    not exist, left behind by whoever was testing. It is kept, with the word it
    actually wrote, because a validator that says "line 8464 says tyuiop" is
    useful and a parser that silently reads it as a city is not.
    """
    bits = s.split()
    kind = bits[1] if len(bits) > 1 else "city"
    idx = p.open("settlement", i)
    node = p.out.nodes[idx]
    node.fields["settlement_type"] = kind
    node.field_lines["settlement_type"] = i
    if len(bits) > 2 or kind not in ("city", "castle"):
        node.problems.append(
            f"settlement header says {kind!r}; the engine knows `settlement` and "
            f"`settlement castle`")


_CHARACTER = re.compile(
    r"^character\s+(?:sub_faction\s+(?P<sub>\w+)\s*,\s*)?"
    r"(?P<name>[^,]+?)\s*,\s*(?P<rest>.*)$", re.I)
_AGE = re.compile(r"\bage\s+(-?\d+)", re.I)
_X = re.compile(r"\bx\s+(-?\d+)", re.I)
_Y = re.compile(r"\by\s+(-?\d+)", re.I)
_TAIL_KEYS = ("portrait", "label", "battle_model", "hero_ability", "direction",
              "shadowing", "shadowed_by")


def _character(p: _Parser, i: int, s: str) -> None:
    """``character [sub_faction f,] <name>, <type>, <sex>, [rank,] age N, x N, y N, …``

    Read by looking for what is there rather than by position, because the
    positions are not reliable: DaC writes ``named character, general`` on two
    lines (two type words where one is allowed) and leaves a trailing comma on
    line 3747. Both parse here, both are reported.
    """
    idx = p.open("character", i)
    node = p.out.nodes[idx]
    m = _CHARACTER.match(s)
    if not m:
        node.problems.append(f"character line has no name: {s!r}")
        return
    node.name = m.group("name").strip()
    node.fields["name"] = node.name
    node.field_lines["name"] = i
    if m.group("sub"):
        node.fields["sub_faction"] = m.group("sub")

    rest = m.group("rest")
    segments = [seg.strip() for seg in rest.split(",")]
    types = [seg for seg in segments if seg.lower() in CHARACTER_TYPES]
    node.fields["type"] = types[0] if types else ""
    if len(types) > 1:
        node.problems.append(f"character is {' and '.join(types)}; only the first counts")
    elif not types:
        node.problems.append("character has no type (named character, general, spy, …)")

    for token in ("male", "female"):
        if token in (seg.lower() for seg in segments):
            node.fields["gender"] = token
    for token in ("leader", "heir"):
        if token in (seg.lower() for seg in segments):
            node.fields["rank"] = token

    for key, rx in (("age", _AGE), ("x", _X), ("y", _Y)):
        hit = rx.search(rest)
        if hit:
            node.fields[key] = int(hit.group(1))
            node.field_lines[key] = i
        else:
            node.problems.append(f"character has no {key}")

    for seg in segments:
        bits = seg.split(None, 1)
        if len(bits) == 2 and bits[0].lower() in _TAIL_KEYS:
            node.fields[bits[0].lower()] = bits[1].strip()
            node.field_lines[bits[0].lower()] = i
        elif len(bits) == 1 and bits[0].lower() in _TAIL_KEYS:
            node.problems.append(f"{bits[0]} has no value")
    if segments and not segments[-1]:
        node.problems.append("trailing comma leaves an empty field")


def _character_list(p: _Parser, i: int, s: str, word: str) -> None:
    """``traits Name 1, Other 2, …`` and ``ancillaries a, b, c``."""
    node = p.open_of("character")
    if node is None:
        p.record(word, i).problems.append(f"{word} line with no character above it")
        return
    body = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
    items = [t.strip() for t in body.split(",") if t.strip()]
    if word == "ancillaries":
        node.fields["ancillaries"] = items
    else:
        traits: Dict[str, int] = {}
        for item in items:
            bits = item.rsplit(None, 1)
            if len(bits) == 2 and re.fullmatch(r"-?\d+", bits[1]):
                traits[bits[0]] = int(bits[1])
            else:
                node.problems.append(f"trait {item!r} has no level")
        node.fields["traits"] = traits
    node.field_lines[word] = i
    node.end = i


_UNIT = re.compile(r"^unit\s+(?P<name>.+?)\s+exp\s+(?P<exp>-?\d+)\s+"
                   r"(?P<armour_key>\w+)\s+(?P<armour>-?\d+)\s+"
                   r"(?P<weapon_key>\w+)(?:\s+(?P<weapon>-?\d+))?\s*$", re.I)


def _unit(p: _Parser, i: int, s: str) -> None:
    """``unit <name> exp N armour N weapon_lvl N``, spelled loosely.

    The three keywords are matched as words rather than as literals, so DaC's
    ``exp 0 rmour 0 weapon_lvl 1`` (three lines) and ``exp 1 armour 1 weapon_lv``
    (one, truncated) both give up their unit name and their numbers and then say
    what is wrong with them. The alternative is losing four regiments out of an
    army because somebody's finger slipped.
    """
    node = p.record("unit", i)
    m = _UNIT.match(s)
    if not m:
        node.problems.append(f"unit line does not read as "
                             f"`unit <name> exp N armour N weapon_lvl N`: {s!r}")
        node.name = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
        node.fields["name"] = node.name
        return
    node.name = m.group("name").strip()
    node.fields.update(name=node.name, exp=int(m.group("exp")),
                       armour=int(m.group("armour")))
    if m.group("armour_key").lower() != "armour":
        node.problems.append(f"{m.group('armour_key')!r} should be `armour`")
    if m.group("weapon_key").lower() != "weapon_lvl":
        node.problems.append(f"{m.group('weapon_key')!r} should be `weapon_lvl`")
    if m.group("weapon") is None:
        node.problems.append("weapon level has no value")
    else:
        node.fields["weapon_lvl"] = int(m.group("weapon"))
    for k in node.fields:
        node.field_lines[k] = i


_RECORD = re.compile(r"^character_record\s+(?P<name>[^,]+?)\s*,\s*(?P<rest>.*)$", re.I)


def _character_record(p: _Parser, i: int, s: str) -> None:
    """``character_record <name>, <sex>, age N, <dead N|alive>, <leadership>``.

    The off-map half of the family tree: the dead, the married-in and the
    never-seen, which the game needs in order to draw a family at all.
    """
    node = p.record("character_record", i)
    m = _RECORD.match(s)
    if not m:
        node.problems.append(f"character_record has no name: {s!r}")
        return
    node.name = m.group("name").strip()
    node.fields["name"] = node.name
    segments = [seg.strip() for seg in m.group("rest").split(",")]
    for seg in segments:
        low = seg.lower()
        if low in ("male", "female"):
            node.fields["gender"] = low
        elif low.startswith("age "):
            node.fields["age"] = int(low.split()[1]) if low.split()[1:2] and \
                re.fullmatch(r"-?\d+", low.split()[1]) else 0
        elif low == "alive":
            node.fields["dead"] = None
        elif low.startswith("dead"):
            bits = low.split()
            node.fields["dead"] = int(bits[1]) if len(bits) > 1 and \
                re.fullmatch(r"-?\d+", bits[1]) else 0
        elif low in LEADERSHIP:
            node.fields["leadership"] = low
    for k in node.fields:
        node.field_lines[k] = i


def _relative(p: _Parser, i: int, s: str) -> None:
    """``relative <father>, <mother>, <child>, …, end`` - one family line.

    The names are positional and the list is terminated by the word ``end``,
    which is not a name and is dropped. 16i's sixteen-year and oldest-first
    constraints read this; 16b only has to hand them the names in order.
    """
    node = p.record("relative", i)
    body = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
    names = [t.strip() for t in re.split(r"[,\t]+", body) if t.strip()]
    if names and names[-1].lower() == "end":
        names.pop()
    else:
        node.problems.append("relative line does not end with `end`")
    node.fields["names"] = names
    node.field_lines["names"] = i
    node.name = names[0] if names else ""
    if len(names) < 2:
        node.problems.append("a relative line names fewer than two people")


_STANDING = re.compile(r"^faction_standings\s+(?P<who>\w+)\s*,\s*"
                       r"(?P<value>-?[\d.]+)\s+(?P<toward>.+)$", re.I)


def _standings(p: _Parser, i: int, s: str) -> None:
    node = p.record("faction_standings", i)
    m = _STANDING.match(s)
    if not m:
        node.problems.append(f"faction_standings does not read as "
                             f"`faction_standings <faction>, <value> <faction…>`: {s!r}")
        return
    node.name = m.group("who")
    node.fields.update(faction=m.group("who"), value=float(m.group("value")),
                       toward=[t.strip() for t in re.split(r"[,\s]+", m.group("toward"))
                               if t.strip()])
    for k in ("faction", "value", "toward"):
        node.field_lines[k] = i


_RELATIONSHIP = re.compile(r"^(?:faction|action)_relationships\s+(?P<who>\w+)\s*,\s*"
                           r"(?P<how>\w+)\s+(?P<toward>.+)$", re.I)


def _relationships(p: _Parser, i: int, s: str) -> None:
    node = p.record("faction_relationships", i)
    m = _RELATIONSHIP.match(s)
    if not m:
        node.problems.append(f"faction_relationships does not read as "
                             f"`faction_relationships <faction>, <how> <faction…>`: {s!r}")
        return
    node.name = m.group("who")
    node.fields.update(faction=m.group("who"), relation=m.group("how").lower(),
                       toward=[t.strip() for t in re.split(r"[,\s]+", m.group("toward"))
                               if t.strip()])
    for k in ("faction", "relation", "toward"):
        node.field_lines[k] = i


def _region(p: _Parser, i: int, s: str) -> None:
    """A depth-0 ``region <name>``: the section holding forts and watchtowers.

    Not to be confused with the ``region`` line inside a settlement block, which
    is that settlement's province. Brace depth is the only thing that tells them
    apart, and it is why depth is tracked at all.
    """
    name = s.split(None, 1)[1].strip() if len(s.split()) > 1 else ""
    idx = p.open("region", i, name)
    node = p.out.nodes[idx]
    node.fields["name"] = name
    node.field_lines["name"] = i


_FORT = re.compile(r"^fort\s+(?P<x>-?\d+)\s+(?P<y>-?\d+)"
                   r"(?:\s+(?P<type>\S+))?(?:\s+culture\s+(?P<culture>\S+))?\s*$", re.I)
_TOWER = re.compile(r"^watchtower\s+(?P<x>-?\d+)\s+(?P<y>-?\d+)\s*$", re.I)


def _fortification(p: _Parser, i: int, s: str, word: str) -> None:
    """``watchtower x y``, and ``fort x y`` in both forms.

    Vanilla writes a fort as ``fort <x> <y>`` and has none in either of its two
    campaigns; DaC writes all 105 of its own as
    ``fort <x> <y> <type> culture <culture>``. Both are the same record with the
    last two fields optional, which is the honest reading. Mylae's parser hunts
    the type with ``/(\\S+_fort\\S*)/`` instead, so a fort type not ending in
    ``_fort`` comes back blank.
    """
    node = p.record(word, i)
    m = (_FORT if word == "fort" else _TOWER).match(s)
    if not m:
        node.problems.append(f"{word} line does not read as `{word} <x> <y>"
                             + (" [<type> culture <culture>]`" if word == "fort" else "`")
                             + f": {s!r}")
        return
    node.fields.update(x=int(m.group("x")), y=int(m.group("y")))
    if word == "fort":
        node.fields["type"] = m.group("type") or ""
        node.fields["culture"] = m.group("culture") or ""
        node.name = node.fields["type"]
    for k in node.fields:
        node.field_lines[k] = i
    region = p.open_of("region")
    if region is not None:
        node.fields["region"] = region.name
        region.end = max(region.end, i)


def _index(out: StratFile) -> None:
    """The interval index: every node's start line, in one list.

    No sort is needed and none is done. A node is appended the moment its first
    line is read, so :attr:`StratFile.nodes` comes out of the parse already in
    document order, which is what makes both lookups a bisect.
    """
    out._starts = [n.start for n in out.nodes]


# ---------------------------------------------------------------------------
# the files on disk


def campaigns(mod) -> List[str]:
    """Every campaign folder that really has a ``descr_strat.txt`` in it."""
    base = mod.data / CAMPAIGN_DIR_REL
    if not base.is_dir():
        return []
    return sorted(d.name for d in base.iterdir()
                  if d.is_dir() and (d / STRAT_NAME).is_file())


def strat_path(mod, campaign: str = DEFAULT_CAMPAIGN) -> Path:
    return mod.data / CAMPAIGN_DIR_REL / campaign / STRAT_NAME


def read_strat(mod, campaign: str = DEFAULT_CAMPAIGN) -> StratFile:
    """Read one campaign's ``descr_strat.txt``. Raises only if it is unreadable."""
    from .keyblock import read_text
    path = strat_path(mod, campaign)
    out = parse_strat(read_text(path, ENCODING))
    out.path = path
    return out
