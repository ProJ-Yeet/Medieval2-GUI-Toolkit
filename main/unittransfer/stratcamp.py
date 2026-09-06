"""``descr_strat.txt``, write: the campaign's own settings, and its factions.

16h wrote the settlements and 16i wrote the people. What is left at depth zero
is the campaign itself: the header it opens with, the three lists that say who
can be played, the diplomacy section every faction block has to precede, and the
handful of scalars a faction block carries before its first settlement - and
then the faction block itself, made and unmade.

**Seven things can be saved and they are seven shapes of one edit.** ``globals``
rewrites the header's own lines, ``rosters`` rewrites the three lists,
``standings`` and ``relationships`` rewrite one faction's row of a matrix, and
``faction`` rewrites a faction block's own scalars: those five are 16j-1 and
none of them writes a line that was not already there. ``create`` and ``delete``
are 16j-2 and make and unmake a whole campaign entry - the block, its place in a
roster, and every diplomacy line on both sides of it. Every one goes through the
same mill 16h and 16i built: splice, re-parse, check the tree that comes out,
guard it against the tree that went in, then back up, log and let the Log undo
it. Eleven helpers come from :mod:`unittransfer.stratedit` and none of them is
copied here.

**A new faction is the donor's, everywhere except its campaign.**
:mod:`unittransfer.factionclone` does the twelve files a faction slot lives in
and says in as many words why ``descr_strat.txt`` is not one of them: a
campaign entry is a settlement, an army and a family tree, and two factions
cannot start in the same city. That ruling stands. What is cloned here is the
donor's AI, its label, its purse and its diplomacy in both directions; what is
not cloned is a settlement, a character or a coordinate, and the plan says so
rather than leaving it to be found at turn one. Deleting refuses while the
faction still holds anything and names what it holds - 16h moves a settlement
and 16i moves a character.

**Four rulings carry in and all four are load-bearing.** *One fact table, read
by everything* - the form is built from :class:`~unittransfer.mapquery.Facts`
and :func:`plan_campaign` re-reads the file from disk, because a writer that
writes out of a cache writes over whatever changed under it. *A rule with no
evidence reports nothing* - the stock game keeps ``descr_sm_factions.txt``
inside its packed data, so on vanilla there is no list of faction slots to check
a roster against and that check does not run. *Python owns the bytes.* *And the
plan reads back what it would write.*

**What the three campaigns actually say, counted rather than assumed.**

*The standing value is sticky and a standings line is a list of pairs.* This is
the one that had a bug under it. The grammar is
``faction_standings <who>, <value> <faction>[, <value> <faction>]…`` and a
target with no number in front of it takes the last number stated. Vanilla never
repeats the value - 46 lines of 46 - so a reader that took the first number and
called the rest targets was right there by accident. Third Age Reforged repeats
it on nearly all of its 204::

    faction_standings   sicily,     1.00    denmark, 1.00   milan
    faction_standings   denmark,    1.00    sicily, milan

Read the old way, Sicily held an opinion of a faction called ``1.00`` and its
opinion of Milan was gone. :mod:`unittransfer.campstrat` now reads the pairs,
and this module is what surfaces them.

*A faction's diplomacy lines are contiguous, in all three campaigns.* 46
standings lines over 17 factions, 204 over 28, 74 relationships over 54, and
**not one faction's lines are interrupted by another's**. So a row edit is a
rewrite of one contiguous run and never a rebuild of the section, and no real
file writes a cell twice for the checks to have to choose between.

*The separator is per keyword and the three campaigns agree on every one of
them.* ``campaign`` takes two tabs; ``start_date``, ``end_date`` and
``timescale`` take one; ``brigand_spawn_value``, ``pirate_spawn_value`` and
``free_upkeep_forts`` take a single space; a roster entry is indented one tab
(56 of 56); ``faction_standings`` is followed by a tab (250 of 250) and
``faction_relationships`` by a space and a tab (74 of 74). An existing line is
still rewritten in its own shape rather than in this one - that is what
:func:`~unittransfer.stratedit.rewrite_line` is for - and these are only what a
keyword the file has never written gets.

*One word in the header is not a word the engine reads.* Third Age Reforged
writes ``marian_reforms_activated`` where ``marian_reforms_disabled`` would go.
It is not in the engine's vocabulary, it does nothing, and until 16j the parser
had nowhere to record it - the campaign header is the only region of the file
where an unrecognised line has no open block to hang a problem on, so it was
dropped without a word and the file would not have survived an edit. It is read
now, and reported here as the dead line it is.

**Nothing here refuses a value the engine would accept.** A start date after an
end date, a timescale of zero, a faction in two rosters at once, a standing
outside -1 to 1, a faction with an opinion of itself: all warn. What is fatal is
what the engine's own vocabulary has no room for - a season that is not
``summer`` or ``winter``, a year or a spawn value that is not a whole number, a
relationship word that is not one of the two, and a faction named anywhere here
that has no faction block in the file.

**And the one ordering rule 16j owns.** Every faction block precedes
``faction_standings``; the file's own shape says so, and
:mod:`unittransfer.mapcheck` has reported it since 16f as
``strat.faction_after_diplomacy``. This is the phase that can put one in the
wrong place, so :func:`check_order` asks the question of the file that has not
been written yet, which is the only place it can stop the mistake rather than
report it. The insert point is worked out to satisfy the rule and then the rule
is checked anyway.

**The guard is a walk, not a diff.** Every run a save declares carries a third
number - how many lines go back in where those came out - and the two files are
read side by side. Between one declared run and the next every line has to be
identical and in the same relative place, and below the last run the rest of
both files has to match to the end. It started as a diff and stopped being one
when a whole-faction save turned out to touch the roster on line 4 and the
diplomacy section on line 10,800, leaving ``difflib`` no small middle to trim to
and four seconds to find that out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campstrat, stratedit
from .campstrat import Node, StratFile
from .stratedit import (assemble, finding, indent_of, is_int, rewrite_line,
                        serialise)

#: The two seasons a date line may name.
SEASONS = ("summer", "winter")

#: The header's ``keyword value`` globals, in the order the file writes them.
VALUES = campstrat.CAMPAIGN_VALUES

#: Which of those must read as a whole number. ``timescale`` is a decimal - the
#: three campaigns write 2.00, 2.00 and 0.25 - and the two dates are a year and
#: a season, so neither of those is a plain number either.
INTEGER_VALUES = ("brigand_spawn_value", "pirate_spawn_value",
                  "free_upkeep_forts")

#: The header's single-word flags.
FLAGS = campstrat.CAMPAIGN_FLAGS

#: The one header word no engine reads. Third Age Reforged writes it; see the
#: module docstring.
DEAD_FLAGS = ("marian_reforms_activated",)

#: The three faction lists, in the order the file writes them.
ROSTERS = campstrat.ROSTERS

#: What a ``faction_relationships`` line may say. Both are measured: vanilla and
#: the prologue write only ``at_war_with`` (25 lines), Third Age Reforged writes
#: both (49). A third word is refused because the engine has no third.
RELATIONS = ("at_war_with", "allied_to")

#: A faction block's own scalars.
FACTION_VALUES = ("ai_label", "denari", "denari_kings_purse")
FACTION_NUMERIC = ("denari", "denari_kings_purse")

#: A faction block's single-word flags.
FACTION_FLAGS = campstrat.FACTION_FLAGS

#: What a keyword the file has never written gets when it is inserted. Measured
#: over the three campaigns; every one of them agrees on every entry.
SEPARATOR = {"campaign": "\t\t", "start_date": "\t", "end_date": "\t",
             "timescale": "\t", "brigand_spawn_value": " ",
             "pirate_spawn_value": " ", "free_upkeep_forts": " "}
ROSTER_INDENT = "\t"
STANDING_HEAD = "faction_standings\t"
RELATION_HEAD = "faction_relationships \t"

#: The seven things a save can be about. The first five rewrite lines that are
#: already there (16j-1); the last two make and unmake a faction's whole
#: campaign entry (16j-2).
WHAT = ("globals", "rosters", "standings", "relationships", "faction",
        "create", "delete")

#: The newline a preview's lines are joined with. The preview is text for a
#: browser to show, never bytes for the file - what goes to disk is joined with
#: :attr:`~unittransfer.campstrat.StratFile.newline`, which is the file's own.
NL = "\n"

_YEAR = re.compile(r"-?\d+$")
_DECIMAL = re.compile(r"-?\d+(?:\.\d+)?$")


# ---------------------------------------------------------------------------
# finding things in the tree


def header_end(sf: StratFile) -> int:
    """The line the campaign header stops at.

    Everything at depth zero before the first node of any kind. The header is
    the only region of the file with no block in it, so its end is where the
    first one starts - or the end of the file, which is what a campaign with
    nothing in it would give.
    """
    return min([n.start for n in sf.nodes] or [len(sf.lines)])


def header_words(sf: StratFile) -> List[Tuple[int, str]]:
    """``(line, first word)`` for every line of the header that says anything.

    Roster entries included; the caller knows where the three lists are.
    """
    out: List[Tuple[int, str]] = []
    for i in range(header_end(sf)):
        s = sf.lines[i].split(";", 1)[0].strip()
        if s:
            out.append((i, s.split()[0]))
    return out


def diplomacy_start(sf: StratFile) -> int:
    """Where the diplomacy section opens, or ``-1`` when there is none.

    The prologue has five relationships and no standings at all, so this is the
    first line of either kind rather than the first ``faction_standings``.
    """
    at = [n.start for n in sf.nodes
          if n.kind in ("faction_standings", "faction_relationships")]
    return min(at) if at else -1


def rows_of(sf: StratFile, kind: str, faction: str) -> List[Node]:
    """One faction's lines of a diplomacy matrix, in the order they are written."""
    low = faction.lower()
    return [n for n in sf.of_kind(kind) if n.name.lower() == low]


def row_span(rows: Sequence[Node]) -> Tuple[int, int]:
    """The run a row occupies. See the module docstring for why it is contiguous."""
    return (rows[0].start, rows[-1].end) if rows else (-1, -1)


def standings_of(sf: StratFile, faction: str) -> Dict[str, float]:
    """What one faction thinks of everybody it has an opinion about.

    A later cell wins over an earlier one, which is the engine's own reading of
    a repeated target and never happens in a real file: no faction in any of the
    three campaigns names the same target twice.
    """
    out: Dict[str, float] = {}
    for n in rows_of(sf, "faction_standings", faction):
        for who, value in n.get("pairs") or []:
            out[who] = value
    return out


def relations_of(sf: StratFile, faction: str) -> Dict[str, str]:
    """Which factions this one is at war with, and which it is allied to."""
    out: Dict[str, str] = {}
    for n in rows_of(sf, "faction_relationships", faction):
        for who in n.get("toward") or []:
            out[who] = str(n.get("relation") or "")
    return out


def faction_scalars(sf: StratFile, node: Node) -> Dict[str, object]:
    """A faction block's own fields, without its settlements or its people."""
    out: Dict[str, object] = {"name": node.name,
                              "ai": str(node.get("ai") or "")}
    for key in FACTION_VALUES:
        out[key] = node.get(key, "")
    for key in FACTION_FLAGS:
        out[key] = bool(node.get(key))
    return out


# ---------------------------------------------------------------------------
# what the pickers may offer


class Vocabulary:
    """What this mod's own files say a faction is, and nothing this one invents.

    Two lists, and they are not the same list. :attr:`blocks` is every faction
    with a block in ``descr_strat.txt`` - the only ones that can be given money,
    an opinion or a place in a roster. :attr:`slots` is every faction
    ``descr_sm_factions.txt`` declares, which is what says a roster entry names
    a faction the game knows at all. On the stock game that second file lives
    inside the packed data, so :attr:`slots` is empty, :attr:`slots_known` is
    false and the check that needs it does not run.
    """

    def __init__(self, facts, sf: StratFile):
        blocks = sf.of_kind("faction")
        self.blocks = [n.name for n in blocks]
        self.lower = {n.lower() for n in self.blocks}
        self.slots = sorted(getattr(facts, "faction_cultures", {}) or {})
        self.slots_known = bool(self.slots)
        self.slot_lower = {s.lower() for s in self.slots}
        label = getattr(facts, "faction_label", None)
        self.labels = {n: (label(n) if label else n) for n in self.blocks}
        self.ai_labels = sorted({str(n.get("ai_label") or "") for n in blocks
                                 if n.get("ai_label")})
        self.ai = sorted({str(n.get("ai") or "") for n in blocks if n.get("ai")})

    def is_faction(self, name: str) -> bool:
        return str(name).lower() in self.lower

    def payload(self) -> dict:
        return {"factions": list(self.blocks), "labels": dict(self.labels),
                "slots": list(self.slots), "slots_known": self.slots_known,
                "ai_labels": list(self.ai_labels), "ai": list(self.ai),
                "relations": list(RELATIONS), "seasons": list(SEASONS),
                "flags": list(FLAGS), "dead_flags": list(DEAD_FLAGS),
                "rosters": list(ROSTERS), "values": list(VALUES),
                "integer_values": list(INTEGER_VALUES),
                "faction_values": list(FACTION_VALUES),
                "faction_flags": list(FACTION_FLAGS)}


# ---------------------------------------------------------------------------
# what is wrong with the campaign as it stands


def split_date(value) -> Tuple[str, str]:
    """``"1080 summer"`` as its year and its season, whatever it actually says."""
    bits = str(value or "").split()
    return (bits[0] if bits else "", bits[1] if len(bits) > 1 else "")


def check_globals(values: Dict[str, object], flags: Sequence[str]) -> List[dict]:
    """Everything wrong with the campaign header."""
    out: List[dict] = []
    years: Dict[str, int] = {}
    for key in ("start_date", "end_date"):
        if key not in values:
            continue
        year, season = split_date(values[key])
        if not _YEAR.match(year):
            out.append(finding("camp.date", True,
                               f"{key} says {year or '(nothing)'!r}, and a "
                               f"campaign year is a whole number"))
        else:
            years[key] = int(year)
        if season and season.lower() not in SEASONS:
            out.append(finding("camp.season", True,
                               f"{key} says {season!r}; the engine's two "
                               f"seasons are " + " and ".join(SEASONS)))
        elif not season:
            out.append(finding("camp.season", False,
                               f"{key} names a year and no season. All three "
                               f"installed campaigns write both"))
    if len(years) == 2 and years["end_date"] <= years["start_date"]:
        out.append(finding("camp.date_order", False,
                           f"the campaign ends in {years['end_date']} and "
                           f"starts in {years['start_date']}, so it has no "
                           f"turns in it"))
    if "timescale" in values:
        got = str(values["timescale"]).strip()
        if not _DECIMAL.match(got):
            out.append(finding("camp.timescale", True,
                               f"timescale says {got or '(nothing)'!r}, and it "
                               f"is a number of years per turn"))
        elif float(got) <= 0:
            out.append(finding("camp.timescale_zero", False,
                               f"a timescale of {got} means a turn advances the "
                               f"calendar by nothing"))
    for key in INTEGER_VALUES:
        if key not in values:
            continue
        if not is_int(values[key]):
            out.append(finding("camp.number", True,
                               f"{key} says {values[key]!r}, and it is a whole "
                               f"number"))
        elif int(str(values[key]).strip()) < 0:
            out.append(finding("camp.negative", False,
                               f"{key} is {values[key]}, and no installed "
                               f"campaign writes a spawn value below zero"))
    for name in flags:
        if name in DEAD_FLAGS:
            out.append(finding("camp.dead_flag", False,
                               f"{name} is not a word the engine reads - the "
                               f"one it reads is marian_reforms_disabled - so "
                               f"this line does nothing. Third Age Reforged "
                               f"ships it too"))
        elif name not in FLAGS:
            out.append(finding("camp.flag", True,
                               f"{name} is not one of the campaign header's "
                               f"flags: " + ", ".join(FLAGS)))
    return out


def check_rosters(voc: Vocabulary,
                  rosters: Dict[str, Sequence[str]]) -> List[dict]:
    """Everything wrong with the three lists.

    The check against ``descr_sm_factions.txt`` does not run when that file is
    not on disk, which on the stock game it never is.
    """
    out: List[dict] = []
    seen: Dict[str, str] = {}
    for name in ROSTERS:
        for who in rosters.get(name, []):
            low = who.lower()
            if low in seen:
                out.append(finding("camp.roster_twice", False,
                                   f"{who} is in both the {seen[low]} and the "
                                   f"{name} list, and the engine reads the "
                                   f"first one it meets"))
            seen[low] = name
            if not voc.is_faction(who):
                out.append(finding("camp.roster_unknown", True,
                                   f"the {name} list names {who}, which has no "
                                   f"faction block in this campaign"))
            elif voc.slots_known and low not in voc.slot_lower:
                out.append(finding("camp.roster_slot", True,
                                   f"the {name} list names {who}, which "
                                   f"descr_sm_factions.txt does not declare"))
    for who in voc.blocks:
        if who.lower() not in seen:
            out.append(finding("camp.block_unlisted", True,
                               f"{who} has a faction block and is in none of "
                               f"the three lists, so nothing tells the engine "
                               f"it exists"))
    if not rosters.get("playable"):
        out.append(finding("camp.no_playable", False,
                           "no faction is playable, so the campaign cannot be "
                           "started from the menu"))
    return out


def check_standings(voc: Vocabulary, faction: str,
                    cells: Dict[str, object]) -> List[dict]:
    """Everything wrong with one faction's row of the standings matrix."""
    out: List[dict] = []
    if faction and not voc.is_faction(faction):
        out.append(finding("camp.standing_who", True,
                           f"{faction} has no faction block in this campaign, "
                           f"so it has nothing to hold an opinion with"))
    for who, value in cells.items():
        if not voc.is_faction(who):
            out.append(finding("camp.standing_toward", True,
                               f"{faction} is given an opinion of {who}, which "
                               f"has no faction block in this campaign"))
        if who.lower() == faction.lower():
            out.append(finding("camp.standing_self", False,
                               f"{faction} is given an opinion of itself"))
        try:
            got = float(value)
        except (TypeError, ValueError):
            out.append(finding("camp.standing_value", True,
                               f"the standing toward {who} says {value!r}, and "
                               f"a standing is a number"))
            continue
        if not -1.0 <= got <= 1.0:
            out.append(finding("camp.standing_range", False,
                               f"the standing toward {who} is {got}. Every one "
                               f"of the 250 in the three installed campaigns is "
                               f"between -1 and 1"))
    return out


def check_relations(voc: Vocabulary, faction: str,
                    cells: Dict[str, str]) -> List[dict]:
    """Everything wrong with one faction's row of the relationships matrix."""
    out: List[dict] = []
    if faction and not voc.is_faction(faction):
        out.append(finding("camp.relation_who", True,
                           f"{faction} has no faction block in this campaign, "
                           f"so it has nothing to be at war with"))
    for who, how in cells.items():
        if not voc.is_faction(who):
            out.append(finding("camp.relation_toward", True,
                               f"{faction} is put in a relationship with {who}, "
                               f"which has no faction block in this campaign"))
        if str(how).lower() not in RELATIONS:
            out.append(finding("camp.relation_word", True,
                               f"{how!r} is not a relationship the engine "
                               f"reads. The two are " + " and ".join(RELATIONS)))
        if who.lower() == faction.lower():
            out.append(finding("camp.relation_self", False,
                               f"{faction} is put in a relationship with itself"))
    return out


def check_faction(scalars: Dict[str, object]) -> List[dict]:
    """Everything wrong with a faction block's own scalars."""
    out: List[dict] = []
    for key in FACTION_NUMERIC:
        got = scalars.get(key, "")
        if got in ("", None):
            continue
        if not is_int(got):
            out.append(finding("camp.faction_number", True,
                               f"{key} says {got!r}, and it is a whole number "
                               f"of florins"))
        elif int(str(got).strip()) < 0:
            out.append(finding("camp.faction_negative", False,
                               f"{key} is {got}, so the faction starts in debt"))
    if not str(scalars.get("ai") or "").strip():
        out.append(finding("camp.faction_ai", False,
                           f"{scalars.get('name')} names no AI personality. "
                           f"Every faction in the three installed campaigns "
                           f"writes two words there"))
    return out


def check_order(sf: StratFile) -> List[dict]:
    """The one ordering rule this phase owns.

    Every faction block precedes ``faction_standings``. This is
    :mod:`unittransfer.mapcheck`'s ``strat.faction_after_diplomacy`` asked of a
    file that has not been written yet, which is the only place it can stop the
    mistake rather than report it.
    """
    at = diplomacy_start(sf)
    if at < 0:
        return []
    return [finding("camp.faction_after_diplomacy", True,
                    f"{n.name}'s faction block starts on line {n.start + 1}, "
                    f"after the diplomacy section opens on line {at + 1}. The "
                    f"engine reads the factions first and would not see it")
            for n in sf.of_kind("faction") if n.start > at]


# ---------------------------------------------------------------------------
# rendering, in the shape of the lines already there


def _head_of(line: str) -> str:
    """``"faction_standings\\t"`` taken off a line that already exists."""
    m = re.match(r"\s*\S+\s*", line.split(";", 1)[0])
    return m.group(0) if m else ""


#: one target on a diplomacy line: the comma before it, an optional restated
#: value, the space after that value, and the faction's name
_PIECE = re.compile(r"(?P<sep>,\s*)?(?P<value>-?\d+(?:\.\d+)?)?(?P<pad>\s*)"
                    r"(?P<name>\w+)")


@dataclass
class RowShape:
    """How one diplomacy line is laid out, so a rewrite of it is the same line.

    16i's ruling, on a different record: **a new record is written in the shape
    of the one beside it**, because the three campaigns do not agree on their
    own whitespace and nothing here has a source that says which of them is
    right. A standings line carries four pieces of shape and every one of them
    varies in a real file - vanilla pads ``hre,`` with three tabs and ``england,``
    with two, Third Age Reforged writes ``1.00`` where vanilla writes ``0.2``,
    restates the value in front of most targets and leaves a tab hanging off the
    end of the line. Read as shape, all of that survives a rewrite; guessed at,
    none of it does.
    """

    head: str = ""
    pad: str = ""
    value: str = ""
    gap: str = ""
    #: ``(separator, restated value or "", pad after it)`` per target
    pieces: List[Tuple[str, str, str]] = field(default_factory=list)
    tail: str = ""

    def render(self, faction: str, value: str, names: Sequence[str]) -> str:
        out = f"{self.head}{faction},{self.pad}{value}{self.gap}"
        for at, name in enumerate(names):
            if at < len(self.pieces):
                sep, restated, pad = self.pieces[at]
            else:
                sep, restated, pad = (", " if at else ""), "", ""
            out += sep + (value + pad if restated else "") + name
        return out + self.tail


def read_row_shape(line: str, kind: str) -> RowShape:
    """One diplomacy line taken apart into the shape it is written in."""
    word = "value" if kind == "faction_standings" else "relation"
    pattern = (r"^(?P<head>\s*\S+\s*)(?P<who>\w+),(?P<pad>\s*)"
               + (r"(?P<value>-?\d+(?:\.\d+)?)" if word == "value"
                  else r"(?P<value>\w+)")
               + r"(?P<gap>\s*)(?P<rest>.*)$")
    m = re.match(pattern, line)
    if not m:
        return RowShape(head=_head_of(line), pad="\t\t", gap="\t")
    shape = RowShape(head=m.group("head"), pad=m.group("pad"),
                     value=m.group("value"), gap=m.group("gap"))
    rest, at = m.group("rest"), 0
    for piece in _PIECE.finditer(rest):
        shape.pieces.append((piece.group("sep") or "",
                             piece.group("value") or "",
                             piece.group("pad") or ""))
        at = piece.end()
    shape.tail = rest[at:]
    return shape


def row_shapes(sf: StratFile, kind: str, faction: str) -> List[RowShape]:
    """The shape of every line a faction's row is written on today."""
    return [read_row_shape(sf.lines[n.start], kind)
            for n in rows_of(sf, kind, faction)]


def _shape_at(shapes: Sequence[RowShape], at: int, kind: str) -> RowShape:
    """The shape for the ``at``-th line of a row, when the row grew.

    The last shape read is reused rather than a default invented, which is what
    makes a row that gains a value line look like the ones above it.
    """
    if shapes:
        return shapes[min(at, len(shapes) - 1)]
    return (RowShape(head=STANDING_HEAD, pad="\t\t", gap="\t")
            if kind == "faction_standings"
            else RowShape(head=RELATION_HEAD, pad=" ", gap=" \t"))


def _number(value, like: str = "") -> str:
    """A standing written the way the line it is replacing writes one.

    Vanilla writes ``-0.2`` and ``-1.0``, Third Age Reforged writes ``1.00``.
    The decimals are taken from the value already on the line, so a row keeps
    its own convention and 0.30000000000000004 never reaches the file.
    """
    places = len(like.partition(".")[2]) if "." in like else 1
    try:
        return f"{float(value):.{places}f}"
    except (TypeError, ValueError):
        return str(value)


def value_line(sf: StratFile, key: str, value: object) -> str:
    """One ``keyword value`` header line, in its own shape when it has one."""
    at = sf.global_lines.get(key)
    body = f"{key}{SEPARATOR.get(key, ' ')}{value}"
    return rewrite_line(sf.lines[at], body) if at is not None else body


def roster_block(sf: StratFile, name: str,
                 members: Sequence[str]) -> List[str]:
    """One of the three lists, keeping the indent its own entries use.

    All 56 roster entries in the three installed campaigns are indented one tab,
    so that is the fallback; a mod that indents differently keeps its own.
    """
    start, end = sf.roster_lines.get(name, (-1, -1))
    indent = ROSTER_INDENT
    if start >= 0:
        for i in range(start + 1, end):
            if sf.lines[i].split(";", 1)[0].strip():
                indent = indent_of(sf.lines[i]) or ROSTER_INDENT
                break
    head = rewrite_line(sf.lines[start], name) if start >= 0 else name
    tail = rewrite_line(sf.lines[end], "end") if end > start else "end"
    return [head] + [indent + who for who in members] + [tail]


def standings_rows(sf: StratFile, faction: str, cells: Dict[str, object],
                   under: str = "") -> List[str]:
    """One faction's standings, written over the lines it already occupies.

    **The lines the row is on are its shape too, not just their whitespace.**
    Grouping the cells by value and writing one line each looked right and is
    wrong: vanilla puts Egypt's two -0.6 opinions on separate lines, Third Age
    Reforged gives the Aztecs twelve lines all reading -1.00, and a renderer
    that merged them rewrote 13 rows nobody had touched. So each existing line
    keeps the targets it still has at the value it still has, in the order it
    has them, and only what is genuinely new is appended - grouped by value,
    in the shape of the last line of the row.
    """
    if not cells:
        return []
    #: 16j-2 renders a new faction's first row off the donor's shapes, which is
    #: what makes a cloned faction's diplomacy look like the file it lands in
    shown = under or faction
    want: Dict[str, float] = {}
    for who, value in cells.items():
        try:
            want[who] = float(value)
        except (TypeError, ValueError):
            return []      # not a number: the checks report it, nothing is written
    out: List[Optional[str]] = []
    shapes: List[RowShape] = []
    for node in rows_of(sf, "faction_standings", faction):
        shape = read_row_shape(sf.lines[node.start], "faction_standings")
        shapes.append(shape)
        value = float(node.get("value") or 0.0)
        kept = [who for who, _ in (node.get("pairs") or [])
                if want.get(who) == value]
        for who in kept:
            del want[who]
        # a line that keeps nothing leaves its slot open rather than closing up,
        # so that a cell moved to another value lands where it was written
        # instead of at the bottom of the row
        out.append(shape.render(shown, _number(value, shape.value), kept)
                   if kept else None)
    left: Dict[float, List[str]] = {}
    for who in want:
        left.setdefault(want[who], []).append(who)
    free = [at for at, line in enumerate(out) if line is None]
    for value in sorted(left, reverse=True):
        at = free.pop(0) if free else len(out)
        shape = _shape_at(shapes, at, "faction_standings")
        line = shape.render(shown, _number(value, shape.value), left[value])
        if at < len(out):
            out[at] = line
        else:
            out.append(line)
    return [line for line in out if line is not None]


def relation_rows(sf: StratFile, faction: str, cells: Dict[str, str],
                  under: str = "") -> List[str]:
    """One faction's relationships, written over the lines it already occupies.

    Same rule as the standings above, and the same reason: Third Age Reforged
    writes Denmark's ``allied_to`` line above its ``at_war_with`` one and 18
    other factions the same way, so a fixed order over
    :data:`RELATIONS` rewrote every one of them. The file's own order wins; a
    word the row has never used is appended in :data:`RELATIONS` order.
    """
    if not cells:
        return []
    shown = under or faction
    want = {w: str(h).lower() for w, h in cells.items()}
    out: List[str] = []
    shapes: List[RowShape] = []
    for node in rows_of(sf, "faction_relationships", faction):
        shape = read_row_shape(sf.lines[node.start], "faction_relationships")
        shapes.append(shape)
        how = str(node.get("relation") or "").lower()
        kept = [who for who in (node.get("toward") or []) if want.get(who) == how]
        for who in kept:
            del want[who]
        if kept:
            out.append(shape.render(shown, how, kept))
    for how in RELATIONS:
        names = [w for w, h in want.items() if h == how]
        if names:
            out.append(_shape_at(shapes, len(shapes),
                                 "faction_relationships").render(
                                     shown, how, names))
    return out


def faction_rewrites(sf: StratFile, node: Node,
                     scalars: Dict[str, object]) -> Dict[int, str]:
    """The rewrites one faction block's scalars need, keyed by line.

    Only lines that already exist are rewritten. A scalar the block does not
    have is not invented here: adding one is a line insert, which is the second
    half of 16j, and a faction with no ``denari`` line is a faction the engine
    gives nothing to rather than a defect to be fixed behind somebody's back.
    """
    out: Dict[int, str] = {}
    at = node.field_lines.get("ai")
    ai = str(scalars.get("ai") or "").strip()
    if at is not None and "ai" in scalars             and ai != str(node.get("ai") or "").strip():
        # `faction	england, balanced smith` keeps its tab. Every faction header
        # in the three campaigns writes one and a space would be a changed byte
        # on a line whose only edit is two words further along
        body = sf.lines[at].split(";", 1)[0].strip()
        rest = body[len("faction"):]
        sep = rest[:len(rest) - len(rest.lstrip())] or " "
        out[at] = rewrite_line(sf.lines[at],
                               f"faction{sep}{node.name}, {ai}")
    for key in FACTION_VALUES:
        at = node.field_lines.get(key)
        # a key the form did not send is a key nobody edited. Filling one in
        # from a default here is how a panel that shows three fields quietly
        # blanks the fourth
        if at is None or key not in scalars:
            continue
        got = str(scalars.get(key, "")).strip()
        if got == str(node.get(key, "")).strip():
            continue
        body = sf.lines[at].split(";", 1)[0].strip()
        rest = body[len(key):]
        sep = rest[:len(rest) - len(rest.lstrip())] or " "
        out[at] = rewrite_line(sf.lines[at], f"{key}{sep}{got}")
    return out


# ---------------------------------------------------------------------------
# 16j-2: a faction's campaign entry, created and removed


def last_content(sf: StratFile, node: Node) -> int:
    """The last line of a block that actually says something.

    A faction block runs to the line before the next thing that can only start
    something else, so the **last** one in the file swallows the banner comment
    above the diplomacy section - 2,979 to 4,355 in vanilla, where 4,353 is
    ``; >>>> start of diplomacy section <<<<``. Inserting "after the last
    faction block" would therefore put a new faction under that banner and, by
    the file's own order, after the diplomacy section. This is where the last
    faction really stops.
    """
    for i in range(node.end, node.start - 1, -1):
        if sf.lines[i].split(";", 1)[0].strip():
            return i
    return node.start


def block_span(sf: StratFile, node: Node) -> Tuple[int, int]:
    """A faction block's lines, and the blank run that separates it from the one
    above.

    Symmetric with :func:`_create_splice`, which writes that run: a block that
    goes out has to take its own separator with it or the file gains two blank
    lines every time one is removed and put back. The walk upwards stops at the
    first line that says something, so the header, the resource list and the
    faction above are all safe from it.
    """
    first = node.start
    while (first - 1 >= 0
           and not sf.lines[first - 1].split(";", 1)[0].strip()):
        first -= 1
    return first, last_content(sf, node)


def block_gap(sf: StratFile) -> int:
    """How many blank lines sit between two faction blocks in this file.

    Measured on the file being written rather than decided here: vanilla puts
    two between all 22 of its blocks and Third Age Reforged puts one between 26
    of its 29. The commonest gap wins, and one is the floor - a new block that
    opened on the line the last one ended on would still parse and would still
    be wrong to look at.
    """
    gaps: Dict[int, int] = {}
    for node in sf.of_kind("faction")[1:]:
        n = 0
        while (node.start - n - 1 >= 0
               and not sf.lines[node.start - n - 1].split(";", 1)[0].strip()):
            n += 1
        gaps[n] = gaps.get(n, 0) + 1
    return max(gaps, key=lambda k: (gaps[k], -k)) if gaps else 1


def new_faction_block(sf: StratFile, donor: Node, name: str,
                      scalars: Dict[str, object],
                      flags: Sequence[str]) -> List[str]:
    """A new faction's block, written in the shape of the donor's own lines.

    16i's ruling on a third record: **a new record is written in the shape of
    the one beside it**. The header keeps the donor's tab, each scalar keeps the
    separator the donor's own line uses, and the flags go under ``ai_label``
    where all five real ones sit.

    **Nothing of the donor's campaign is copied - not a settlement, not a
    character, not a coordinate.** That is
    :mod:`unittransfer.factionclone`'s ruling about ``descr_strat.txt``, and it
    is right for the same reason here: two factions cannot start in the same
    settlement, so there is no value to clone. The block that comes out is a
    faction with a treasury and nothing else, and the plan says so - 16h hands
    it a settlement and 16i hands it people, and until one of them does it is
    the same shape vanilla's Mongols and Timurids already are.
    """
    head = sf.lines[donor.start]
    body = head.split(";", 1)[0].strip()
    rest = body[len("faction"):]
    sep = rest[:len(rest) - len(rest.lstrip())] or "\t"
    ai = str(scalars.get("ai") or donor.get("ai") or "").strip()
    out = [rewrite_line(head, f"faction{sep}{name}, {ai}")]
    for key in FACTION_VALUES:
        at = donor.field_lines.get(key)
        got = scalars.get(key, donor.get(key, ""))
        if at is None:
            if got not in ("", None):
                out.append(f"{key}	{got}")
        else:
            line = sf.lines[at].split(";", 1)[0].strip()
            tail = line[len(key):]
            gap = tail[:len(tail) - len(tail.lstrip())] or "	"
            out.append(rewrite_line(sf.lines[at], f"{key}{gap}{got}"))
        if key == "ai_label":
            out += [str(f) for f in flags]      # where all five real ones sit
    return out


def check_new_name(voc: Vocabulary, name: str) -> List[dict]:
    """Whether this is a name a faction can have, and does not already have."""
    out: List[dict] = []
    if not name:
        out.append(finding("camp.new_blank", True,
                           "a new faction needs a name, and it is the slot the "
                           "rest of the mod points at rather than the one shown "
                           "in game"))
        return out
    if not re.fullmatch(r"[a-z0-9_]+", name):
        out.append(finding("camp.new_shape", True,
                           f"{name!r} is not a faction slot. Every one of the "
                           f"90 in the three installed mods is lower case "
                           f"letters, digits and underscores"))
    if voc.is_faction(name):
        out.append(finding("camp.new_taken", True,
                           f"{name} already has a faction block in this "
                           f"campaign"))
    elif voc.slots_known and name.lower() not in voc.slot_lower:
        out.append(finding("camp.new_slot", True,
                           f"descr_sm_factions.txt does not declare {name}. A "
                           f"faction that exists only in descr_strat.txt is a "
                           f"mod that will not load - the Factions screen "
                           f"clones the other twelve files first"))
    return out


def check_created(sf: StratFile, node: Node) -> List[dict]:
    """What is still missing from a faction that has just been made.

    All warnings, and deliberately so: **vanilla ships two factions with no
    settlement of their own** - the Mongols and the Timurids, both
    ``dead_until_resurrected`` - so a block with nothing in it is a shape the
    engine already reads rather than a defect. What it will not do is appear on
    the map, and that is worth saying out loud rather than leaving to be found
    at turn one.
    """
    out: List[dict] = []
    if not sf.children_of(node, "settlement"):
        out.append(finding("camp.new_homeless", False,
                           f"{node.name} holds no settlement, so it will not "
                           f"appear on the map. The settlement panel changes an "
                           f"owner, which is how it gets one. Vanilla's Mongols "
                           f"and Timurids are the same shape and appear by "
                           f"script"))
    if not sf.descendants_of(node, "character"):
        out.append(finding("camp.new_leaderless", False,
                           f"{node.name} has nobody in it, so it has no faction "
                           f"leader. The people panel adds one"))
    if not standings_of(sf, node.name) and not relations_of(sf, node.name):
        out.append(finding("camp.new_neutral", False,
                           f"{node.name} is written into no line of the "
                           f"diplomacy section, so it starts neutral toward "
                           f"everybody - the rebels included, which every other "
                           f"faction in the three installed campaigns is at war "
                           f"with"))
    return out


def check_holdings(sf: StratFile, node: Node) -> List[dict]:
    """What a faction still holds, and why that stops it being deleted."""
    towns = sf.children_of(node, "settlement")
    people = sf.descendants_of(node, "character")
    if not towns and not people:
        return []
    what = []
    if towns:
        what.append(f"{len(towns)} settlement(s) - "
                    + ", ".join(t.name for t in towns[:4])
                    + (", …" if len(towns) > 4 else ""))
    if people:
        what.append(f"{len(people)} character(s)")
    return [finding("camp.delete_holds", True,
                    f"{node.name} still holds " + " and ".join(what)
                    + ". Deleting the block would take them with it, so move "
                      "them first: the settlement panel changes an owner and "
                      "the people panel moves a character")]


def _create_splice(sf: StratFile, p: CampPlan, body: dict):
    """A whole new faction: its block, its place in a roster, and its diplomacy.

    Four edits in one save, and the order they are worked out in is the order
    they sit in the file, so the line numbers the earlier ones use are still
    the numbers the file has.
    """
    name = p.faction
    donor = sf.faction(str(body.get("donor") or "").strip())
    if donor is None:
        p.errors.append(
            f"{body.get('donor') or '(nothing)'} has no faction block to clone "
            f"from. A new faction is written in the shape of one that already "
            f"works, which is what makes it safe")
        return sf.lines
    roster = str(body.get("roster") or "playable").lower()
    if roster not in ROSTERS:
        p.errors.append(f"{roster!r} is not one of the three lists: "
                        + ", ".join(ROSTERS))
        return sf.lines

    inserts: Dict[int, List[str]] = {}
    drop: set = set()
    rewrites: Dict[int, str] = {}
    spans: List[Tuple[int, int, int]] = []

    # the block, after the last faction really stops - which is not where its
    # span ends, because the last block in the file swallows the banner comment
    # above the diplomacy section
    facs = sf.of_kind("faction")
    at = last_content(sf, facs[-1]) + 1
    block = ([""] * block_gap(sf)
             + new_faction_block(sf, donor, name, dict(body.get("scalars") or {}),
                                 [str(f) for f in (body.get("flags") or [])]))
    inserts[at] = block

    # its place in one of the three lists
    start, end = sf.roster_lines.get(roster, (-1, -1))
    if start < 0:
        p.errors.append(f"this campaign has no {roster} list to put "
                        f"{name} in")
        return sf.lines
    members = list(sf.rosters.get(roster, [])) + [name]
    drop |= set(range(start, end + 1))
    inserts[start] = roster_block(sf, roster, members)
    spans.append((start, end, 0))          # filled in from `inserts` below

    # and the opinions the donor is on both sides of
    if body.get("diplomacy", True):
        for kind, read, render in (
                ("faction_standings", standings_of, standings_rows),
                ("faction_relationships", relations_of, relation_rows)):
            mine = read(sf, donor.name)
            mine.pop(name, None)
            rows = rows_of(sf, kind, donor.name)
            if mine and rows:
                # at the end of the section, not under the donor: the line after
                # the donor's last row is the line another faction's row starts
                # on, and two inserts keyed on it would be one insert
                inserts.setdefault(_section_end(sf, kind), []).extend(
                    render(sf, donor.name, mine, under=name))
            for other in sf.of_kind("faction"):
                if other.name in (donor.name, name):
                    continue
                cells = read(sf, other.name)
                if donor.name not in cells:
                    continue
                cells[name] = cells[donor.name]
                theirs = rows_of(sf, kind, other.name)
                a, b = row_span(theirs)
                drop |= set(range(a, b + 1))
                inserts[a] = render(sf, other.name, cells)
                spans.append((a, b, 0))
    # every run that only inserts, declared once from the dict. Two inserts
    # keyed on one line are one insert, and a run declared twice counts its
    # lines twice - which the walk in `_touched` sees as the file shifting
    replaced = {lo for lo, _hi, _n in spans}
    spans = [(lo, hi, len(inserts[lo]) if lo in inserts else n)
             for lo, hi, n in spans]
    spans += [(at, at - 1, len(got)) for at, got in inserts.items()
              if at not in replaced]
    p.spans = spans
    p.block = NL.join(block).strip(NL)
    return assemble(sf.lines, rewrites, drop, inserts)


def _delete_splice(sf: StratFile, p: CampPlan, node: Node):
    """A faction's whole campaign entry taken out, in the four places it is in."""
    name = node.name
    p.errors += [f["message"] for f in check_holdings(sf, node)]
    if p.errors:
        return sf.lines
    first, last = block_span(sf, node)
    drop: set = set(range(first, last + 1))
    inserts: Dict[int, List[str]] = {}
    spans: List[Tuple[int, int, int]] = [(first, last, 0)]

    for roster in ROSTERS:
        if name not in sf.rosters.get(roster, []):
            continue
        start, end = sf.roster_lines[roster]
        members = [w for w in sf.rosters[roster] if w != name]
        drop |= set(range(start, end + 1))
        inserts[start] = roster_block(sf, roster, members)
        spans.append((start, end, len(inserts[start])))

    for kind, read, render in (("faction_standings", standings_of, standings_rows),
                               ("faction_relationships", relations_of,
                                relation_rows)):
        for other in sf.of_kind("faction"):
            cells = read(sf, other.name)
            if other.name != name and name not in cells:
                continue
            rows = rows_of(sf, kind, other.name)
            if not rows:
                continue
            a, b = row_span(rows)
            drop |= set(range(a, b + 1))
            if other.name == name:
                spans.append((a, b, 0))        # its own row goes entirely
                continue
            cells.pop(name, None)
            lines = render(sf, other.name, cells)
            if lines:
                inserts[a] = lines
            spans.append((a, b, len(lines)))
    p.spans = spans
    p.block = ""
    return assemble(sf.lines, {}, drop, inserts)


# ---------------------------------------------------------------------------
# the plan


#: Every kind of record in the file. A save names the one kind it is allowed to
#: change the number of, and the guard holds every other kind to its count.
KINDS = ("faction", "settlement", "building", "character", "character_record",
         "relative", "army", "unit", "region", "fort", "watchtower",
         "resource", "faction_standings", "faction_relationships", "script")

#: Which kind each save is allowed to add or remove lines of. Three of the five
#: may not change the shape of the tree at all.
OWNS = {"globals": {}, "rosters": {}, "faction": {},
        "standings": {"faction_standings": None},
        "relationships": {"faction_relationships": None},
        # a new faction is one block, a place in a roster and however many
        # diplomacy lines its opinions need, so those three counts are the ones
        # allowed to move and every other kind is held to the number it had
        "create": {"faction": 1, "faction_standings": None,
                   "faction_relationships": None},
        "delete": {"faction": -1, "faction_standings": None,
                   "faction_relationships": None}}


@dataclass
class CampPlan:
    """One save of the campaign's own settings, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    what: str = "globals"
    faction: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the lines this save would put in, for the preview
    block: str = ""
    #: ``[(first, last, lines written)]`` for every run of the file this save
    #: may touch. 0-based and inclusive while the plan is being worked out, then
    #: 1-based for the payload. The third number is how many lines go back in
    #: where those came out, which is what lets :func:`_touched` walk the two
    #: files instead of diffing them.
    spans: List[Tuple[int, int, int]] = field(default_factory=list)
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.what} in {getattr(self.mod, 'name', '?')}/"
                f"{self.campaign}"
                + (f" ({self.faction})" if self.faction else "")
                + f", {len(self.changes)} change(s)")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"what": self.what, "faction": self.faction,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "block": self.block,
                "spans": [[a, b] for a, b, _n in self.spans],
                "ok": not self.errors and bool(self.text)}


def _flag_lines(sf: StratFile, want: Sequence[str], have: Dict[str, int],
                after: int) -> Tuple[set, Dict[int, List[str]]]:
    """Which flag lines to drop and which to insert, for the header or a block.

    A flag is a line or it is nothing - there is no ``= no`` form - so turning
    one off deletes its line and turning one on inserts a line, in the shape of
    a flag line that is already there when there is one to copy.
    """
    keep = {f.lower() for f in want}
    drop = {at for name, at in have.items() if name.lower() not in keep}
    add = [f for f in want if f.lower() not in {h.lower() for h in have}]
    inserts: Dict[int, List[str]] = {}
    if add:
        model = sf.lines[min(have.values())] if have else ""
        indent = indent_of(model) if model else ""
        inserts[after] = [indent + f for f in add]
    return drop, inserts


def diff_runs(before: Sequence[str],
              after: Sequence[str]) -> List[Tuple[str, int, int, int, int]]:
    """The opcodes between two sets of lines, without diffing the whole file.

    Used for the preview only - :func:`_touched` does the guarding and does not
    need a diff at all. The identical head and tail are trimmed first and only
    the middle goes to :class:`difflib.SequenceMatcher`, which on a header edit
    is three lines rather than eleven thousand.
    """
    from difflib import SequenceMatcher

    n = min(len(before), len(after))
    pre = 0
    while pre < n and before[pre] == after[pre]:
        pre += 1
    suf = 0
    while suf < n - pre and before[len(before) - 1 - suf] == after[len(after) - 1 - suf]:
        suf += 1
    b, a = before[pre:len(before) - suf], after[pre:len(after) - suf]
    if not b and not a:
        return []
    sm = SequenceMatcher(None, b, a, autojunk=False)
    return [(tag, i1 + pre, i2 + pre, j1 + pre, j2 + pre)
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def _touched(before: StratFile, after: StratFile,
             spans: Sequence[Tuple[int, int, int]]) -> List[str]:
    """Every line this save changed that it never said it would.

    The strongest guard the seven edits here can carry, and the reason it is
    affordable: all seven are region-local and each one declares not just the
    run of the file it replaces but **how many lines it puts back**. That third
    number is what turns the check from a diff into a walk. The two files are
    read side by side; between one declared run and the next, every line has to
    be identical *and in the same relative place*, and after the last run the
    rest of both files has to match to the end. A splice that landed a line
    short, ate the blank line under a roster or rewrote the faction below the
    one asked about shows up here by line number.

    A diff would answer the same question, and did until Third Age Reforged's
    11,063 lines took four seconds over it - a new faction touches the roster on
    line 4 and the diplomacy section on line 10,800, so there is no small middle
    to trim to. This is linear and exact, and it does not have to guess which of
    several equivalent placements of a blank line the edit meant.
    """
    out: List[str] = []
    b, a = before.lines, after.lines
    bi = ai = 0
    for lo, hi, kept in sorted(spans):
        if lo < bi:
            out.append(f"this save declares two runs that overlap at line "
                       f"{lo + 1}, so what it would write there is not decided")
            return out
        for step in range(lo - bi):
            if b[bi + step] != a[ai + step]:
                out.append(f"this would rewrite line {bi + step + 1} of the "
                           f"file, which this save never asked about: "
                           f"{b[bi + step].strip()[:60]!r}")
                return out
        ai += lo - bi
        bi = hi + 1
        ai += kept
    if b[bi:] != a[ai:]:
        at = next((i for i, (x, y) in enumerate(zip(b[bi:], a[ai:])) if x != y),
                  min(len(b) - bi, len(a) - ai))
        line = b[bi + at] if bi + at < len(b) else ""
        out.append(f"this would rewrite line {bi + at + 1} of the file, which "
                   f"is below everything this save asked about: "
                   f"{line.strip()[:60]!r}")
    return out


def _guard(before: StratFile, after: StratFile, what: str,
           spans: Sequence[Tuple[int, int]]) -> List[str]:
    """What the splice did that it was never asked to do."""
    out: List[str] = []
    owns = OWNS[what]
    b, a = before.counts(), after.counts()
    for kind in KINDS:
        was, now = b.get(kind, 0), a.get(kind, 0)
        if kind not in owns:
            if was != now:
                out.append(f"this would leave {now} {kind} record(s) where the "
                           f"file has {was}, and a {what} save does not touch "
                           f"them")
        elif owns[kind] is not None and now != was + owns[kind]:
            out.append(f"this would leave {now} {kind} record(s) where the file "
                       f"has {was}, and a {what} save changes it by "
                       f"{owns[kind]:+d}")
    if what not in ("rosters", "create", "delete")             and before.rosters != after.rosters:
        out.append("this would change the playable, unlockable or nonplayable "
                   "lists, which a " + what + " save does not")
    if what != "globals" and before.globals != after.globals:
        out.append("this would change the campaign's own header values, which "
                   "a " + what + " save does not")
    places_b, odd_b = stratedit.blocks_by_region(before)
    places_a, odd_a = stratedit.blocks_by_region(after)
    if places_b != places_a or odd_b != odd_a:
        out.append("this would move or rewrite a settlement block, and 16j "
                   "writes the campaign's settings")
    out += _touched(before, after, spans)
    out += [f["message"] for f in check_order(after)]
    return out


def _section_end(sf: StratFile, kind: str) -> int:
    """Where a new line of a diplomacy section goes when the section has none.

    After the last line of its own kind if there is one; else at the top of the
    diplomacy section, which is where the prologue's five relationships sit with
    no standings above them; else immediately before the regions, which is the
    next thing in the file's own order.
    """
    same = sf.of_kind(kind)
    if same:
        return same[-1].end + 1
    at = diplomacy_start(sf)
    if at >= 0:
        return at
    regions = sf.of_kind("region") + sf.of_kind("script")
    return min([n.start for n in regions] or [len(sf.lines)])


def _globals_splice(sf: StratFile, p: CampPlan, body: dict):
    """The header's own lines: rewrite what moved, insert what is new, drop what went."""
    want = dict(body.get("values") or {})
    flags = [str(f) for f in (body.get("flags") or [])]
    rewrites: Dict[int, str] = {}
    drop: set = set()
    inserts: Dict[int, List[str]] = {}
    spans: List[Tuple[int, int, int]] = []

    tail = max([sf.global_lines[k] for k in VALUES if k in sf.global_lines]
               + [sf.global_lines.get("campaign", -1)]) + 1
    for key in VALUES:
        at = sf.global_lines.get(key)
        got = "" if want.get(key) is None else str(want[key]).strip()
        if at is None:
            if key in want and got:
                inserts.setdefault(tail, []).append(f"{key}{SEPARATOR[key]}{got}")
                spans.append((tail, tail - 1, len(inserts[tail])))
            continue
        if key not in want:
            continue
        if not got:
            drop.add(at)
            spans.append((at, at, 0))
        elif got != str(sf.globals.get(key, "")).strip():
            rewrites[at] = value_line(sf, key, got)
            spans.append((at, at, 1))

    known = FLAGS
    have = {k: sf.global_lines[k] for k in known
            if k in sf.globals and k in sf.global_lines}
    at_end = max(list(have.values()) + [tail - 1]) + 1
    gone, added = _flag_lines(sf, flags, have, at_end)
    drop |= gone
    for k, v in added.items():
        inserts.setdefault(k, []).extend(v)
        spans.append((k, k - 1, len(inserts[k])))
    spans += [(at, at, 0) for at in gone]

    p.spans = spans
    return assemble(sf.lines, rewrites, drop, inserts)


def _roster_splice(sf: StratFile, p: CampPlan, body: dict):
    """The three lists, each replaced where it stands."""
    want = body.get("rosters") or {}
    drop: set = set()
    inserts: Dict[int, List[str]] = {}
    spans: List[Tuple[int, int, int]] = []
    for name in ROSTERS:
        if name not in want:
            continue
        start, end = sf.roster_lines.get(name, (-1, -1))
        if start < 0:
            p.errors.append(f"this campaign has no {name} list to rewrite, and "
                            f"adding one is the second half of 16j")
            continue
        members = [str(w).strip() for w in want[name] if str(w).strip()]
        block = roster_block(sf, name, members)
        if block == sf.lines[start:end + 1]:
            continue
        drop |= set(range(start, end + 1))
        inserts[start] = block
        spans.append((start, end, len(block)))
    p.spans = spans
    return assemble(sf.lines, {}, drop, inserts)


def _row_splice(sf: StratFile, p: CampPlan, kind: str,
                rows: List[str]) -> List[str]:
    """One faction's diplomacy row, put where its row already is."""
    have = rows_of(sf, kind, p.faction)
    start, end = row_span(have)
    if start < 0:
        at = _section_end(sf, kind)
        p.spans = [(at, at - 1, len(rows))]
        return assemble(sf.lines, {}, set(), {at: rows} if rows else {})
    p.spans = [(start, end, len(rows))]
    if rows == sf.lines[start:end + 1]:
        return list(sf.lines)
    return assemble(sf.lines, {}, set(range(start, end + 1)),
                    {start: rows} if rows else {})


def _faction_splice(sf: StratFile, p: CampPlan, node: Node, body: dict):
    """A faction block's own scalars and flags, and nothing below them."""
    scalars = dict(body.get("scalars") or {})
    scalars.setdefault("name", node.name)
    rewrites = faction_rewrites(sf, node, scalars)
    have = {k: node.field_lines[k] for k in FACTION_FLAGS
            if node.get(k) and k in node.field_lines}
    # after `ai_label`, which is where all five real flags in the installed
    # campaigns sit - vanilla's Aztecs, its Mongols and its Timurids all write
    # the flag between `ai_label` and `denari`. Falling back to after the last
    # scalar when a block has no `ai_label` to sit under
    own = [at for k, at in node.field_lines.items()
           if k in FACTION_VALUES or k in FACTION_FLAGS] + [node.start]
    at_end = node.field_lines.get("ai_label")
    gone, added = _flag_lines(sf, [str(f) for f in (body.get("flags") or [])],
                              have, (at_end + 1 if at_end is not None
                                     else max(own) + 1))
    spans = [(at, at, 1 if at in rewrites else 0)
             for at in set(rewrites) | gone]
    spans += [(k, k - 1, len(v)) for k, v in added.items()]
    p.spans = spans
    return assemble(sf.lines, rewrites, gone, added)


def _describe(before: dict, after: dict) -> List[str]:
    """What changed, said the way somebody would say it out loud."""
    out: List[str] = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a == b:
            continue
        if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
            was, now = list(a or []), list(b or [])
            got = [x for x in now if x not in was]
            lost = [x for x in was if x not in now]
            if got:
                out.append(f"{key}: added " + ", ".join(str(x) for x in got))
            if lost:
                out.append(f"{key}: removed " + ", ".join(str(x) for x in lost))
            if not got and not lost:
                out.append(f"{key}: reordered")
        else:
            out.append(f"{key}: {a if a not in (None, '') else '(none)'} -> "
                       f"{b if b not in (None, '') else '(none)'}")
    return out


def _cells(raw: dict) -> Dict[str, object]:
    """A standings row off the wire, with anything that is not a number kept.

    A cell that will not read as a number is passed to the checks as it stands
    rather than dropped here, because ``camp.standing_value`` saying what was
    typed is more use than a row that quietly lost a faction.
    """
    out: Dict[str, object] = {}
    for who, value in raw.items():
        try:
            out[str(who)] = float(str(value).strip())
        except (TypeError, ValueError):
            out[str(who)] = value
    return out


def _cells_text(cells: Dict[str, object]) -> List[str]:
    return [f"{k} {v}" for k, v in sorted(cells.items(), key=lambda kv: kv[0])]


def _changed_lines(before: StratFile, after: StratFile) -> List[str]:
    """The lines this save would put in, for the preview under the form."""
    return [line for _t, _i1, _i2, j1, j2 in diff_runs(before.lines, after.lines)
            for line in after.lines[j1:j2]]


def plan_campaign(mod, facts, body: dict) -> CampPlan:
    """Work out the whole new ``descr_strat.txt`` for one campaign-settings save.

    ``body`` is ``{campaign, what, faction, values, flags, rosters, standings,
    relationships, scalars}`` and ``what`` is one of :data:`WHAT`.

    **The file is re-read here rather than taken from ``facts``**, for the
    reason 16h states where it does the same: the fact table is a cache, and a
    writer that writes out of a cache writes over whatever changed under it.
    ``facts`` is the vocabulary the findings are measured against - which
    factions this mod declares, and what they are called.
    """
    from .campmap import MapError

    campaign = str(body.get("campaign") or "") or facts.campaign
    what = str(body.get("what") or "globals").lower()
    p = CampPlan(mod=mod, campaign=campaign, what=what,
                 faction=str(body.get("faction") or "").strip())
    if what not in WHAT:
        p.errors.append(f"no such save {what!r}. The five are "
                        + ", ".join(WHAT))
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = sf.path
    voc = Vocabulary(facts, sf)

    node: Optional[Node] = None
    if what in ("faction", "standings", "relationships", "delete"):
        node = sf.faction(p.faction)
        if node is None:
            p.errors.append(
                (p.faction or "(nothing)") + " has no faction block in "
                + campaign + "'s descr_strat.txt. Creating one is the second "
                "half of 16j; cloning one that already works is what the "
                "Factions screen does today")
            return p
        p.faction = node.name
    elif what == "create":
        p.faction = str(body.get("faction") or "").strip().lower()

    before: dict = {}
    after: dict = {}
    if what == "globals":
        before = {**{k: str(sf.globals.get(k, "")) for k in VALUES},
                  "flags": [k for k in FLAGS
                            if sf.globals.get(k)]}
        want = {k: str(v).strip()
                for k, v in (body.get("values") or {}).items()}
        after = {**{k: want.get(k, before[k]) for k in VALUES},
                 "flags": [str(f) for f in (body.get("flags") or [])]}
        lines = _globals_splice(sf, p, body)
        p.findings = check_globals({k: v for k, v in after.items()
                                    if k in VALUES and v != ""},
                                   after["flags"])
    elif what == "rosters":
        before = {k: list(sf.rosters.get(k, [])) for k in ROSTERS}
        want = body.get("rosters") or {}
        after = {k: [str(w).strip() for w in want.get(k, before[k])
                     if str(w).strip()] for k in ROSTERS}
        lines = _roster_splice(sf, p, {"rosters": after})
        p.findings = check_rosters(voc, after)
    elif what == "standings":
        cells = _cells(body.get("standings") or {})
        before = {"standings": _cells_text(standings_of(sf, p.faction))}
        after = {"standings": _cells_text(cells)}
        p.findings = check_standings(voc, p.faction, cells)
        lines = _row_splice(sf, p, "faction_standings",
                            standings_rows(sf, p.faction, cells))
    elif what == "relationships":
        cells = {str(k): str(v).lower()
                 for k, v in (body.get("relationships") or {}).items()
                 if str(v).strip()}
        before = {"relationships": _cells_text(relations_of(sf, p.faction))}
        after = {"relationships": _cells_text(cells)}
        p.findings = check_relations(voc, p.faction, cells)
        lines = _row_splice(sf, p, "faction_relationships",
                            relation_rows(sf, p.faction, cells))
    elif what == "faction":
        before = faction_scalars(sf, node)
        want = dict(body.get("scalars") or {})
        after = {**before, **{k: want[k] for k in want if k in before}}
        before["flags"] = [k for k in FACTION_FLAGS if node.get(k)]
        after["flags"] = [str(f) for f in (body.get("flags") or [])]
        p.findings = check_faction(after)
        lines = _faction_splice(sf, p, node, body)
    elif what == "create":
        p.findings = check_new_name(voc, p.faction)
        p.errors += [f["message"] for f in p.findings if f["fatal"]]
        if p.errors:
            return p
        lines = _create_splice(sf, p, body)
        after = {"faction": p.faction,
                 "cloned from": str(body.get("donor") or "").strip(),
                 "roster": str(body.get("roster") or "playable").lower(),
                 "diplomacy": ("the donor's, both ways"
                               if body.get("diplomacy", True) else "none")}
    else:
        before = {"faction": node.name,
                  "roster": next((r for r in ROSTERS
                                  if node.name in sf.rosters.get(r, [])), ""),
                  "standings": _cells_text(standings_of(sf, node.name)),
                  "relationships": _cells_text(relations_of(sf, node.name))}
        after = {"faction": "(gone)", "roster": "", "standings": [],
                 "relationships": []}
        lines = _delete_splice(sf, p, node)
    if p.errors:
        return p

    text = serialise(sf, lines)
    done = campstrat.parse_strat(text)
    p.errors += _guard(sf, done, what, p.spans)
    if p.errors:
        return p

    if what == "create":
        made = done.faction(p.faction)
        if made is None:
            p.errors.append(f"after this save there is no faction block called "
                            f"{p.faction!r}, which is the one thing it was for")
            return p
        p.findings += check_created(done, made)
    else:
        p.block = NL.join(_changed_lines(sf, done))
    p.findings += check_order(done)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(before, after)
    p.spans = [(a + 1, b + 1, n) for a, b, n in p.spans]
    p.text = "" if text == sf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


# ---------------------------------------------------------------------------
# the save


def apply_campaign(p: CampPlan) -> dict:
    """Write a planned save, with the same backups and undo as any other job.

    The same shape as :func:`~unittransfer.stratchar.apply_character`, and
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
        "action": "campaign",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.what, "resolved_type": p.faction or p.what,
        "options": {"campaign": p.campaign, "what": p.what,
                    "faction": p.faction},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPAIGN %s %s in %s/%s - %d change(s), id=%s",
             p.what, p.faction or "-", mod.name, p.campaign,
             len(p.changes), tid)
    return {"id": tid, "what": p.what, "faction": p.faction,
            "campaign": p.campaign, "record": rec}


# ---------------------------------------------------------------------------
# the form


def campaign_detail(facts) -> dict:
    """Everything the Campaign panel shows, in one call.

    Read out of the fact table's own :class:`~unittransfer.campstrat.StratFile`
    rather than off the disk, which is 16g's rule and what makes opening the
    panel free: the parse is already done and cached. The write half is the
    deliberate exception and says so where it is made.

    The diplomacy matrix is handed over whole - every faction's row, both ways -
    because a grid with a hole in it cannot tell "no opinion" from "not loaded",
    and because the asymmetry is the interesting part: vanilla writes England's
    -0.2 of France and France's -0.2 of England as two separate lines, and
    nothing in the engine makes the second follow from the first.
    """
    from .campmap import MapError

    sf = getattr(facts, "strat", None)
    if sf is None:
        raise MapError(f"{facts.strat_rel} could not be read, so this map has "
                       f"no campaign to edit")
    voc = Vocabulary(facts, sf)
    flags = [k for k in FLAGS if sf.globals.get(k)]
    rosters = {k: list(sf.rosters.get(k, [])) for k in ROSTERS}
    factions = []
    for node in sf.of_kind("faction"):
        scalars = faction_scalars(sf, node)
        factions.append({
            **scalars,
            "label": voc.labels.get(node.name, node.name),
            "line": node.start + 1,
            "flags": [k for k in FACTION_FLAGS if node.get(k)],
            "settlements": len(sf.children_of(node, "settlement")),
            "characters": len(sf.descendants_of(node, "character")),
            "roster": next((k for k in ROSTERS
                            if node.name in rosters.get(k, [])), ""),
            "standings": {w: v for w, v in standings_of(sf, node.name).items()},
            "relationships": relations_of(sf, node.name),
            "rows": {kind: [n.start + 1 for n in rows_of(sf, kind, node.name)]
                     for kind in ("faction_standings",
                                  "faction_relationships")},
            "findings": check_faction(scalars),
            "problems": list(node.problems),
        })
    return {
        "campaign": facts.campaign,
        "file": facts.strat_rel,
        "name": sf.campaign,
        "values": {k: str(sf.globals.get(k, "")) for k in VALUES},
        "value_lines": {k: sf.global_lines[k] + 1 for k in VALUES
                        if k in sf.global_lines},
        "flags": flags,
        "rosters": rosters,
        "roster_lines": {k: [a + 1, b + 1]
                         for k, (a, b) in sf.roster_lines.items()},
        "diplomacy_line": diplomacy_start(sf) + 1,
        "factions": factions,
        "findings": (check_globals({k: v for k, v in
                                    ((k, str(sf.globals.get(k, "")))
                                     for k in VALUES) if v != ""}, flags)
                     + check_rosters(voc, rosters)
                     + check_order(sf)),
        "vocab": voc.payload(),
    }
