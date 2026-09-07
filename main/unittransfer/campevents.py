"""The two files that say what happens on its own: events and disasters.

Phase 18b, closing M3 and M4. Two files, one module, for the reason 18a gave
for putting three in one: they are the same sentence with a different subject.
A ``descr_events.txt`` block is "on this date, this happens, here"; a
``descr_disasters.txt`` block is "every so many years, this happens, somewhere
that looks like this". Both are a head line, a run of ``keyword value`` lines
under it, and - the thing that makes this a map phase - repeatable
``position x, y`` lines.

**M3 - ``descr_events.txt``**, in the campaign folder beside ``descr_strat.txt``::

    event   historic    first_windmill
    date    50

    event   earthquake  earthquake_in_aleppo
    date    58
    position    257, 73

The label is the join to two other things, and both of them are checks here:
it is looked up in ``text/historic_events.txt`` as ``{NAME_TITLE}`` and
``{NAME_BODY}`` - measured, 1,796 keys in Divide and Conquer and 582 in Third
Age Reforged, and **every one of them ends in one of those two words** - and it
is the file name of the event picture in each ``data/ui/<culture>/eventspic``
folder, which is a campaign CTD when it is missing.

**M4 - ``descr_disasters.txt``**, under ``world/maps/base`` rather than in the
campaign folder::

    event       earthquake
    frequency   20
    winter      false
    summer      false
    warning     false
    climate     rocky_desert
    min_scale   2
    max_scale   5

**Neither installed mod ships a word of either file**, which is why this one is
measured against the game's own unpacked copies rather than against a mod:
``descr_disasters.txt`` is 0 bytes in both mods and in Third Age Reforged's
Fellowship campaign, and its ``descr_events.txt`` is a Geomod comment banner
with nothing under it. The game's own two files are the arbiter here, and
``descr_disasters.txt`` carries its own format documentation in its header.

**What measuring corrected in the reference tool.** ``campaignEventsParser.jsx``
and ``disastersParser.jsx`` are 90-line readers with a serialiser each, and all
four of these are faults their own files would show:

* **both serialisers rebuild the file from a model**, so the first save of
  either drops every comment in it. The game's own ``descr_events.txt`` is 6,194
  bytes of which the whole top half is commented-out test cases and the format
  documentation quoted above, and it has **no trailing newline**. Every edit
  here is a splice, and ``parse_*(t).text() == t`` is the gate.
* **their event parser holds one ``date``**, ``current.date = …``, so the last
  ``date`` line wins. Third Age Reforged's Fellowship campaign writes four of
  them for one event (``date 7 8`` then three ``date … turns …`` lines); three
  would be lost.
* **their event categories are the disaster list.** The game's own header names
  ``counter``, ``historic``, ``volcano``, ``plague`` and ``emergent_faction``,
  and its own live lines also use ``earthquake``. Theirs has neither ``counter``
  nor ``emergent_faction`` - and ``emergent_faction`` is how a faction enters a
  campaign at all.
* **their disaster serialiser writes every key.** Vanilla's ``plague`` block has
  no ``warning`` line; theirs would add one on the first save of any block in
  the file, because it defaults the value rather than remembering the line was
  absent. A slot that is not there is a line to add, not a line to blank - 18a's
  ruling about a movie slot, and the same ruling here.

**And one rule that would have fired on the game's own file.** Vanilla's
``storm`` and ``horde`` both write ``region the sea``, which is not a region in
``descr_regions.txt`` and never will be. So :data:`SEA_REGION` is a declared
value here, and the unknown-region rule does not report it. That is the "a rule
with no evidence reports nothing" decision applied to a value rather than to a
missing file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campmap, campstrat, keyblock as kb, mapvocab, stringsbin
from .triggers import split_lines

#: both files are plain 8-bit text; the localisation beside them is UTF-16
ENCODING = "latin-1"

CAMPAIGN_DIR_REL = campstrat.CAMPAIGN_DIR_REL
DEFAULT_CAMPAIGN = campstrat.DEFAULT_CAMPAIGN

#: M3, in the campaign folder beside descr_strat.txt
EVENTS_NAME = "descr_events.txt"

#: M4, under world/maps/base with the layers - **not** in the campaign folder.
#: Third Age Reforged also keeps an empty one inside a campaign folder; the game
#: reads the one here, and an empty file beside a campaign is reported rather
#: than edited.
DISASTERS_NAME = "descr_disasters.txt"
DISASTERS_REL = f"{campmap.BASE_REL}/{DISASTERS_NAME}"

#: where an event's title and body text live, and how its keys are spelled
EVENT_TEXT_REL = "text/historic_events.txt"
EVENT_TEXT_KINDS = ("TITLE", "BODY")

#: an event picture is `<name>.tga` in every one of these, and a missing one is
#: a campaign CTD (the TWCenter tutorial's own warning). The folders are found
#: on disk rather than listed, because a mod's cultures are its own.
EVENTSPIC_GLOB = "ui/*/eventspic"

#: What an ``event`` line's category may be. The first five are the game's own
#: header in ``descr_events.txt``; ``earthquake`` is not in that list and is used
#: four times by the file the list is written in, so it is one too.
EVENT_CATEGORIES = ("counter", "historic", "volcano", "plague",
                    "emergent_faction", "earthquake")

#: The categories whose whole effect is a place - the header says a volcano
#: fires "at the position specified" and a plague "in settlements at the
#: specified positions", so one of these with no position does nothing.
EVENT_PLACED = ("volcano", "plague", "earthquake")

#: The keyword lines an event block may carry, in the order the game's own file
#: writes them. ``date`` is required; the rest are optional and repeatable
#: except ``movie``.
EVENT_KEYS = ("date", "position", "region", "movie")
EVENT_REPEATED = ("date", "position", "region")

#: The eight disaster types, in the order vanilla's own file declares them.
DISASTER_TYPES = ("earthquake", "volcano", "flood", "storm", "horde",
                  "dustbowl", "locusts", "plague")

#: The keyword lines a disaster block carries, in vanilla's own order.
DISASTER_KEYS = ("frequency", "winter", "summer", "warning", "climate",
                 "region", "position", "min_scale", "max_scale")
DISASTER_FLAGS = ("winter", "summer", "warning")
DISASTER_NUMBERS = ("frequency", "min_scale", "max_scale")
DISASTER_REPEATED = ("climate", "region", "position")

#: A ``region`` line that is not a region. Vanilla's ``storm`` and ``horde``
#: both write it, and both are disasters that happen at sea.
SEA_REGION = "the sea"

#: ``257, 73`` - and the comma is optional, because nothing in the engine's own
#: files depends on it and a hand-typed one will go in without it.
_POS = re.compile(r"^(-?\d+)\s*,?\s+(-?\d+)$")


class CampEventError(kb.BlockError):
    """The file is not there, or an edit would write one the engine misreads."""


# ---------------------------------------------------------------------------
# what both files are made of


@dataclass
class Position:
    """One ``position x, y`` line, in the coordinates the file writes."""

    x: int
    y: int
    #: 0-based line in the file
    line: int = -1

    def text(self) -> str:
        return f"{self.x}, {self.y}"

    def as_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "line": self.line + 1}


def parse_position(value: str) -> Optional[Tuple[int, int]]:
    m = _POS.match(value.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


@dataclass
class Block:
    """One ``event …`` head line and the keyword lines under it.

    Shared by both files because both files are this: the head line differs -
    an event names a category and a label, a disaster names only a type - and
    everything below it is the same run of ``keyword value``.
    """

    #: the ``event`` line's second token: a category, or a disaster's type
    kind: str = ""
    #: the third token, which only an event has
    name: str = ""
    head_line: int = -1
    #: keyword -> the 0-based lines carrying it, in file order
    lines: Dict[str, List[int]] = field(default_factory=dict)
    #: keyword -> the values on those lines, in the same order
    values: Dict[str, List[str]] = field(default_factory=dict)
    positions: List[Position] = field(default_factory=list)
    #: first line of the block, and one past its last
    start: int = 0
    end: int = 0

    def first(self, key: str) -> str:
        got = self.values.get(key) or []
        return got[0] if got else ""

    def has(self, key: str) -> bool:
        return bool(self.lines.get(key))

    def all(self, key: str) -> List[str]:
        return list(self.values.get(key) or [])

    def line_of(self, key: str) -> int:
        got = self.lines.get(key) or []
        return got[0] if got else self.head_line


@dataclass
class BlockFile:
    """A whole file, held as its own lines with the blocks indexed into it."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    blocks: List[Block] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    #: which file this is, for the messages: 'events' or 'disasters'
    what: str = "events"

    def text(self) -> str:
        out = self.newline.join(self.lines)
        return out + self.newline if self.trailing_newline and self.lines else out

    def block_text(self, b: Block) -> str:
        return self.newline.join(self.lines[b.start:b.end])

    def by_name(self, name: str) -> Optional[Block]:
        low = (name or "").lower()
        return next((b for b in self.blocks
                     if (b.name or b.kind).lower() == low), None)


def _parse(text: str, what: str, keys: Sequence[str], named: bool) -> BlockFile:
    """Both readers. ``named`` is whether the head line carries a third token.

    Never raises. A keyword the file has that this module does not know is a
    warning and is left exactly where it is, because a file carrying a
    directive we have not heard of is far likelier than a file that is wrong.
    """
    lines, newline, trailing = split_lines(text)
    bf = BlockFile(lines=lines, newline=newline, trailing_newline=trailing,
                   what=what)
    cur: Optional[Block] = None
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        # `event\t\tearthquake` - the gap between a keyword and its value is a
        # tab as often as a space, so this splits on whitespace rather than
        # partitioning on " ", which would take the whole line as the keyword
        parts = code.split()
        word = parts[0].lower()
        rest = code[len(parts[0]):].strip()
        if word == "event":
            if cur is not None:
                cur.end = i
            cur = Block(head_line=i, start=i, end=i + 1)
            if named:
                cur.kind = parts[1] if len(parts) > 1 else ""
                cur.name = parts[2] if len(parts) > 2 else ""
                if len(parts) > 3:
                    bf.warnings.append(
                        f"line {i + 1}: `event` takes a category and a label; "
                        f"{' '.join(parts[3:])[:30]} is a third value")
            else:
                cur.kind = rest
            bf.blocks.append(cur)
            continue
        if cur is None:
            bf.warnings.append(
                f"line {i + 1}: `{code[:30]}` is before the first `event` line, "
                "so nothing reads it")
            continue
        cur.end = i + 1
        if word not in keys:
            bf.warnings.append(
                f"line {i + 1}: `{parts[0]}` is not one of "
                + kb.and_list(list(keys)))
            continue
        cur.lines.setdefault(word, []).append(i)
        cur.values.setdefault(word, []).append(rest)
        if word == "position":
            xy = parse_position(rest)
            if xy is None:
                bf.warnings.append(
                    f"line {i + 1}: `{rest[:30]}` is not an `x, y` position")
            else:
                cur.positions.append(Position(xy[0], xy[1], i))
    if cur is not None and cur.end < cur.start + 1:
        cur.end = cur.start + 1
    return bf


def parse_events(text: str) -> BlockFile:
    """``descr_events.txt``. ``parse_events(t).text() == t`` for any ``t``."""
    return _parse(text, "events", EVENT_KEYS, named=True)


def parse_disasters(text: str) -> BlockFile:
    """``descr_disasters.txt``. Round-trips byte for byte, same as above."""
    return _parse(text, "disasters", DISASTER_KEYS, named=False)


# ---------------------------------------------------------------------------
# where they are


def events_path(mod, campaign: str = DEFAULT_CAMPAIGN) -> Path:
    return Path(mod.data) / CAMPAIGN_DIR_REL / campaign / EVENTS_NAME


def disasters_path(mod) -> Path:
    return Path(mod.data) / DISASTERS_REL


def read_events(mod, campaign: str = DEFAULT_CAMPAIGN) -> Tuple[BlockFile, str]:
    path = events_path(mod, campaign)
    if not path.exists():
        raise CampEventError(f"{campaign} has no {EVENTS_NAME}, so it fires no "
                             "historical events")
    text = kb.read_text(path, ENCODING)
    return parse_events(text), text


def read_disasters(mod) -> Tuple[BlockFile, str]:
    path = disasters_path(mod)
    if not path.exists():
        raise CampEventError(f"this mod has no {DISASTERS_REL}, so no natural "
                             "disaster ever happens on its map")
    text = kb.read_text(path, ENCODING)
    return parse_disasters(text), text


# ---------------------------------------------------------------------------
# writing one block back


def _key_prefix(bf: BlockFile, b: Block, keyword: str) -> str:
    """``"position\\t"`` - the indent, keyword and gap a new line should copy.

    Off a line of the same keyword when the block has one, off any other keyword
    line when it does not, and off nothing at all only for a block that is one
    line long. These files are laid out in tab columns and a new line landing in
    a different one is the first thing anybody notices about a save.
    """
    have = bf.lines[b.lines[keyword][0]] if b.has(keyword) else ""
    if have:
        return kb.head_prefix(have, kb.code_of(have).split()[0])
    for key in b.lines:
        line = bf.lines[b.lines[key][0]]
        indent = kb.indent_of(line)
        return kb.pad_to_column(keyword, indent,
                                kb.value_column(line, kb.code_of(line).split()[0]))
    return kb.indent_of(bf.lines[b.head_line]) + keyword + "\t"


def _edit_repeated(sp: kb.Splice, bf: BlockFile, b: Block, keyword: str,
                   wanted: List[str], anchor_after: Sequence[str]) -> List[str]:
    """Make a repeatable keyword's lines say exactly ``wanted``, in that order.

    Reusing the lines that are there rather than dropping and re-adding them,
    so a block whose four positions had one number changed comes back with three
    lines untouched and one spliced. New lines go after the last existing line
    of the same keyword, and when there is none, after the last line of whatever
    keyword precedes it in the file's own order.
    """
    at = list(b.lines.get(keyword) or [])
    was = b.all(keyword)
    prefix = _key_prefix(bf, b, keyword)
    for i, value in enumerate(wanted[:len(at)]):
        if value != was[i]:
            sp.replace(at[i], kb.keep_comment(bf.lines[at[i]], prefix + value))
    for i in range(len(wanted), len(at)):
        sp.drop(at[i])
    extra = wanted[len(at):]
    if extra:
        after = at[-1] if at else _anchor(b, anchor_after)
        sp.after(after, [prefix + v for v in extra])
    return _list_changes(keyword, was, wanted)


def _list_changes(keyword: str, was: List[str], wanted: List[str]) -> List[str]:
    """What a confirmation dialog should say about a repeatable keyword.

    Said as what went and what came rather than as which line became which. The
    splice above reuses the lines it can, so dropping one climate out of three
    rewrites the second line and deletes the third - which is the right thing to
    write to disk and exactly the wrong thing to read in a dialog, where it
    would say a climate was renamed to one already in the list and then removed.
    """
    left = list(was)
    added: List[str] = []
    for v in wanted:
        if v in left:
            left.remove(v)
        else:
            added.append(v)
    if len(left) == 1 and len(added) == 1:
        # one out and one in is a value being changed, and reading it as a
        # removal and an addition is how `frequency 20 -> 25` becomes two lines
        # of dialog that look like two edits
        return [f"{keyword} {left[0]} -> {added[0]}"]
    out = [f"- {keyword} {v}" for v in left] + [f"+ {keyword} {v}" for v in added]
    if not out and was != wanted:
        out.append(f"{keyword}: reordered")
    return out


def _anchor(b: Block, before: Sequence[str]) -> int:
    """The line a new keyword's first line goes after: the last line of the last
    keyword that sorts before it, or the head line."""
    at = [max(b.lines[k]) for k in before if b.has(k)]
    return max(at) if at else b.head_line


def render_event(bf: BlockFile, b: Block, edits: Dict) -> Tuple[str, List[str]]:
    """The whole file with one event rewritten. Returns the text and what moved.

    Only the keys ``edits`` actually carries are touched, which is what lets one
    screen save the dates without having an opinion about the movie.
    """
    sp = kb.Splice(list(bf.lines))
    changes: List[str] = []
    kind = str(edits.get("category", b.kind) or "").strip()
    name = str(edits.get("name", b.name) or "").strip()
    if not kind:
        raise CampEventError("an `event` line needs a category", b.head_line + 1)
    if not name:
        raise CampEventError("an `event` line needs a label", b.head_line + 1)
    if kind != b.kind or name != b.name:
        sp.replace(b.head_line,
                   kb.sub_tokens(bf.lines[b.head_line], "event", [kind, name]))
        if kind != b.kind:
            changes.append(f"category {b.kind} -> {kind}")
        if name != b.name:
            changes.append(f"label {b.name} -> {name}")
    if "dates" in edits:
        wanted = [str(d).strip() for d in edits["dates"] if str(d).strip()]
        if not wanted:
            raise CampEventError(
                "an event with no `date` line never fires - the tutorial's own "
                "warning, and the file agrees: every live block has one",
                b.head_line + 1)
        changes += _edit_repeated(sp, bf, b, "date", wanted, ())
    if "positions" in edits:
        changes += _edit_repeated(sp, bf, b, "position",
                                  _position_texts(edits["positions"]), ("date",))
    if "regions" in edits:
        wanted = [str(r).strip() for r in edits["regions"] if str(r).strip()]
        changes += _edit_repeated(sp, bf, b, "region", wanted,
                                  ("date", "position"))
    if "movie" in edits:
        changes += _edit_repeated(
            sp, bf, b, "movie",
            [str(edits["movie"]).strip()] if str(edits["movie"] or "").strip() else [],
            ("date", "position", "region"))
    return _joined(bf, sp.result()), changes


def render_disaster(bf: BlockFile, b: Block, edits: Dict) -> Tuple[str, List[str]]:
    """The whole file with one disaster rewritten, line by line.

    A scalar cleared to nothing loses its line rather than being written empty,
    for the reason vanilla's own ``plague`` block gives: it has no ``warning``
    line at all, and ``warning`` with nothing after it is not a line any real
    file writes.
    """
    sp = kb.Splice(list(bf.lines))
    changes: List[str] = []
    kind = str(edits.get("type", b.kind) or "").strip()
    if not kind:
        raise CampEventError("an `event` line needs a disaster type", b.head_line + 1)
    if kind != b.kind:
        sp.replace(b.head_line,
                   kb.sub_tokens(bf.lines[b.head_line], "event", [kind]))
        changes.append(f"{b.kind} -> {kind}")
    for key in DISASTER_KEYS:
        if key in DISASTER_REPEATED or key not in edits:
            continue
        value = str(edits[key] if edits[key] is not None else "").strip()
        if key in DISASTER_FLAGS and isinstance(edits[key], bool):
            value = "true" if edits[key] else "false"
        changes += _edit_repeated(sp, bf, b, key, [value] if value else [],
                                  DISASTER_KEYS[:DISASTER_KEYS.index(key)])
    for key, field_name in (("climate", "climates"), ("region", "regions")):
        if field_name not in edits:
            continue
        wanted = [str(v).strip() for v in edits[field_name] if str(v).strip()]
        changes += _edit_repeated(sp, bf, b, key, wanted,
                                  DISASTER_KEYS[:DISASTER_KEYS.index(key)])
    if "positions" in edits:
        changes += _edit_repeated(sp, bf, b, "position",
                                  _position_texts(edits["positions"]),
                                  DISASTER_KEYS[:DISASTER_KEYS.index("position")])
    return _joined(bf, sp.result()), changes


def _position_texts(raw) -> List[str]:
    """``[[10, 20], "30, 40"]`` -> ``["10, 20", "30, 40"]``, refusing the rest."""
    out: List[str] = []
    for item in raw or ():
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                out.append(f"{int(item[0])}, {int(item[1])}")
            except (TypeError, ValueError):
                raise CampEventError(
                    f"`{item}` is not a pair of whole numbers") from None
            continue
        if isinstance(item, dict):
            try:
                out.append(f"{int(item['x'])}, {int(item['y'])}")
            except (KeyError, TypeError, ValueError):
                raise CampEventError(f"`{item}` is not an x and a y") from None
            continue
        xy = parse_position(str(item))
        if xy is None:
            raise CampEventError(f"`{item}` is not an `x, y` position")
        out.append(f"{xy[0]}, {xy[1]}")
    return out


def _joined(bf: BlockFile, lines: List[str]) -> str:
    out = bf.newline.join(lines)
    return out + bf.newline if bf.trailing_newline and lines else out


def new_event_lines(kind: str, name: str, edits: Dict, prefix: str = "") -> List[str]:
    """A whole event block, in the order the game's own file writes it."""
    kind, name = str(kind or "").strip(), str(name or "").strip()
    if not kind:
        raise CampEventError("a new event needs a category")
    if not name:
        raise CampEventError("a new event needs a label")
    dates = [str(d).strip() for d in (edits.get("dates") or []) if str(d).strip()]
    if not dates:
        raise CampEventError("a new event needs at least one `date` line, or it "
                             "never fires")
    pad = prefix or "\t"
    rows = [f"event{pad}{kind}{pad}{name}"]
    rows += [f"date{pad}{d}" for d in dates]
    rows += [f"position{pad}{p}" for p in _position_texts(edits.get("positions"))]
    rows += [f"region{pad}{r}" for r in (edits.get("regions") or []) if str(r).strip()]
    if str(edits.get("movie") or "").strip():
        rows.append(f"movie{pad}{str(edits['movie']).strip()}")
    return rows


#: The column ``descr_disasters.txt`` lines its values up in. Vanilla's own file
#: is one column at tab width 4 - ``event`` and ``winter`` reach it in two tabs,
#: ``frequency`` and ``min_scale`` in one - so a new block is padded to a column
#: rather than given a fixed gap, which is what would push the short keywords
#: four characters past everything around them.
DISASTER_COLUMN = 12


def new_disaster_lines(kind: str, edits: Dict,
                       column: int = DISASTER_COLUMN) -> List[str]:
    """A whole disaster block, in vanilla's own key order and its own column.

    Every key vanilla writes is written, because a disaster with no
    ``frequency`` or no ``min_scale`` is not a shorter block, it is one the
    engine has to guess at.
    """
    kind = str(kind or "").strip()
    if not kind:
        raise CampEventError("a new disaster needs a type")
    def row(key: str, value) -> str:
        return kb.pad_to_column(key, "", column) + str(value)

    rows = [row("event", kind)]
    for key in ("frequency", "winter", "summer", "warning"):
        value = edits.get(key)
        if key in DISASTER_FLAGS:
            value = "true" if kb.truthy(value) and value != "false" else "false"
        else:
            value = str(value if value not in (None, "") else 20).strip()
        rows.append(row(key, value))
    for key, field_name in (("climate", "climates"), ("region", "regions")):
        rows += [row(key, str(v).strip())
                 for v in (edits.get(field_name) or []) if str(v).strip()]
    rows += [row("position", p) for p in _position_texts(edits.get("positions"))]
    for key, default in (("min_scale", 2), ("max_scale", 5)):
        value = edits.get(key)
        rows.append(row(key, value if value not in (None, "") else default))
    return rows


def insert_block(bf: BlockFile, rows: List[str]) -> str:
    """A new block goes at the end, with a blank line before it.

    Both files separate their blocks with one blank line and neither has any
    kind of closing directive, so the end of the file is where a block goes and
    there is nothing to insert in front of.
    """
    lines = list(bf.lines)
    if lines and lines[-1].strip():
        # `.strip()`, not `code_of`: the game's own descr_events.txt ends on a
        # commented `;position 190, 80` with no trailing newline, and a block
        # appended straight onto that line would be inside the comment
        lines.append("")
    return _joined(bf, lines + rows)


def remove_block(bf: BlockFile, b: Block) -> str:
    """Take one block out, and the blank line that separated it from the next.

    The line above is left alone: it is very often a ``; ---- CORE GAME EVENT
    ----`` banner belonging to the block below, and guessing that a comment
    belongs to the block under it is how a delete eats a comment nobody asked
    it to.
    """
    lines = list(bf.lines)
    start, end = b.start, b.end
    if end < len(lines) and not lines[end].strip():
        end += 1                       # the one blank line under it, and no more
    elif end >= len(lines) and start > 0 and not lines[start - 1].strip():
        # the last block in the file has no blank line under it, so the one
        # above it is its separator - without this, adding a block and deleting
        # it again leaves the file one blank line longer than it started
        start -= 1
    del lines[start:end]
    return _joined(bf, lines)


# ---------------------------------------------------------------------------
# what is wrong with them


def _finding(out: List[Dict], code: str, fatal: bool, message: str, **extra) -> None:
    out.append(dict({"code": code, "fatal": fatal, "message": message}, **extra))


def event_text_pairs(mod) -> Dict[str, str]:
    """Every key in ``historic_events.txt``, from the ``.txt`` or the ``.bin``.

    The two roads :func:`unittransfer.campfiles.descr_pairs` takes, and for the
    same reason: a released mod very often ships only the compiled archive.
    """
    txt = Path(mod.data) / EVENT_TEXT_REL
    if txt.exists():
        try:
            return dict(stringsbin.from_txt(
                txt.read_text(encoding=stringsbin.TXT_ENCODING)))
        except (OSError, UnicodeError):
            pass
    try:
        return stringsbin.load_pairs(stringsbin.bin_path_for(txt))
    except (OSError, ValueError):
        return {}


def eventspic_dirs(mod) -> List[Path]:
    """Every ``data/ui/<culture>/eventspic`` folder this mod actually ships.

    Found rather than listed. Neither installed mod ships one - the stock
    pictures are inside a ``.pack`` nothing here reads - so on those two the
    picture rule does not run at all, which is the point.
    """
    try:
        return sorted(p for p in Path(mod.data).glob(EVENTSPIC_GLOB) if p.is_dir())
    except OSError:
        return []


def check_events(bf: BlockFile, mod=None, campaign: str = DEFAULT_CAMPAIGN,
                 factions: Optional[List[str]] = None,
                 regions: Optional[List[str]] = None,
                 size: Optional[Tuple[int, int]] = None) -> List[Dict]:
    """What is wrong with the event file, when there is evidence for saying so.

    ``factions``, ``regions`` and ``size`` are each allowed to be ``None`` and
    each turns its own rules off when it is. The text and picture rules ask the
    mod for themselves and go quiet the same way.
    """
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for b in bf.blocks:
        where = {"name": b.name, "line": b.head_line + 1}
        if not b.name:
            _finding(out, "no_label", True,
                     "an `event` line with no label names no event, and nothing "
                     "in historic_events.txt can be found for it", **where)
        if b.kind and b.kind not in EVENT_CATEGORIES:
            _finding(out, "unknown_category", False,
                     f"`{b.kind}` is not a category the engine documents; the "
                     f"file's own header names {kb.and_list(list(EVENT_CATEGORIES[:5]))}",
                     **where)
        low = (b.name or "").lower()
        if low and low in seen:
            _finding(out, "duplicate", False,
                     f"`{b.name}` has a second block; both fire, and both read "
                     f"the same text (the first is line {seen[low] + 1})", **where)
        elif low:
            seen[low] = b.head_line
        if not b.has("date"):
            _finding(out, "no_date", True,
                     f"`{b.name or b.kind}` has no `date` line, so it never "
                     "fires", **where)
        for i, value in enumerate(b.all("date")):
            parts = value.split()
            nums = [p for p in parts if kb.is_int(p)]
            line = b.lines["date"][i] + 1
            if not nums:
                _finding(out, "bad_date", True,
                         f"`{b.name}`'s date is `{value}`, and a date is a year "
                         "offset or a pair of them",
                         name=b.name, line=line)
            elif all(int(n) in (0, 1) for n in nums[:2]):
                _finding(out, "date_zero", False,
                         f"`{b.name}` is dated {value}; an event on turn 0 or 1 "
                         "does not appear in a campaign, only in an "
                         "`add_events` block in a script",
                         name=b.name, line=line)
        if b.kind in EVENT_PLACED and not b.has("position") and not b.has("region"):
            _finding(out, "no_position", False,
                     f"a `{b.kind}` event happens at a position, and `{b.name}` "
                     "names none, so nothing happens", **where)
        if b.kind == "emergent_faction" and factions is not None and b.name:
            if b.name not in factions:
                _finding(out, "unknown_faction", False,
                         f"`{b.name}` has no block in {campaign}'s "
                         "descr_strat.txt, so there is no faction to emerge",
                         **where)
        out += _position_findings(b, regions, size)
    if mod is not None:
        out += _event_text_findings(bf, mod)
        out += _event_picture_findings(bf, mod)
    return out


def _position_findings(b: Block, regions: Optional[List[str]],
                       size: Optional[Tuple[int, int]]) -> List[Dict]:
    """The two things about a coordinate that can be decided from the file.

    Off the map is decided here because ``descr_terrain.txt`` says how big the
    map is and that is a two-line read; whether a tile is sea needs the layers
    decoded and belongs to :mod:`unittransfer.mapcheck`, which already holds
    them for every other rule.
    """
    out: List[Dict] = []
    who = b.name or b.kind
    for p in b.positions:
        if size is not None and not (0 <= p.x < size[0] and 0 <= p.y < size[1]):
            _finding(out, "position_off", True,
                     f"`{who}` is placed at {p.x},{p.y}, which is off a "
                     f"{size[0]}x{size[1]} map altogether",
                     name=b.name, line=p.line + 1, position=[p.x, p.y])
    for i, value in enumerate(b.all("region")):
        if regions is None or value.lower() == SEA_REGION:
            continue
        if not any(r.lower() == value.lower() for r in regions):
            _finding(out, "unknown_region", False,
                     f"`{who}` names region `{value}`, which is not in "
                     f"descr_regions.txt (`{SEA_REGION}` is the one value that "
                     "is not a region and is still valid)",
                     name=b.name, line=b.lines["region"][i] + 1, region=value)
    return out


def _event_text_findings(bf: BlockFile, mod) -> List[Dict]:
    """A label with no title or body. Silent when neither text file is there."""
    pairs = event_text_pairs(mod)
    if not pairs:
        return []
    out: List[Dict] = []
    for b in bf.blocks:
        if not b.name or b.kind == "counter":
            continue                    # a counter shows no message at all
        missing = [k for k in EVENT_TEXT_KINDS
                   if f"{b.name.upper()}_{k}" not in pairs]
        if missing:
            _finding(out, "no_text", False,
                     f"`{b.name}` has no "
                     + kb.and_list([f"{{{b.name.upper()}_{k}}}" for k in missing])
                     + f" in {EVENT_TEXT_REL}, so the message it shows is blank",
                     name=b.name, line=b.head_line + 1)
    return out


def _event_picture_findings(bf: BlockFile, mod) -> List[Dict]:
    """A label with no event picture. Silent when the mod ships no such folder.

    The tutorial's own warning is that this is a campaign CTD rather than a
    blank picture, which is why it is fatal in the folders that exist - and why
    it says nothing at all about the folders that do not.
    """
    dirs = eventspic_dirs(mod)
    if not dirs:
        return []
    out: List[Dict] = []
    for b in bf.blocks:
        if not b.name or b.kind == "counter":
            continue
        absent = [d for d in dirs if not (d / f"{b.name}.tga").exists()]
        if not absent:
            continue
        rel = [str(d.relative_to(Path(mod.data))).replace("\\", "/") for d in absent]
        _finding(out, "no_picture", True,
                 f"`{b.name}` has no picture in "
                 + kb.and_list(rel[:3])
                 + (f" and {len(rel) - 3} more" if len(rel) > 3 else "")
                 + " - a missing event picture crashes the campaign when the "
                   "event fires",
                 name=b.name, line=b.head_line + 1)
    return out


def check_disasters(bf: BlockFile, mod=None,
                    regions: Optional[List[str]] = None,
                    climates: Optional[List[str]] = None,
                    size: Optional[Tuple[int, int]] = None) -> List[Dict]:
    """What is wrong with the disaster file, on the same evidence rule."""
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for b in bf.blocks:
        where = {"name": b.kind, "line": b.head_line + 1}
        if not b.kind:
            _finding(out, "no_type", True,
                     "an `event` line with no type is not a disaster", **where)
            continue
        if b.kind not in DISASTER_TYPES:
            _finding(out, "unknown_type", False,
                     f"`{b.kind}` is not one of the eight the engine has; the "
                     f"file the engine ships declares "
                     f"{kb.and_list(list(DISASTER_TYPES))}", **where)
        low = b.kind.lower()
        if low in seen:
            _finding(out, "duplicate", False,
                     f"`{b.kind}` has a second block (the first is line "
                     f"{seen[low] + 1}); the engine has one setting per "
                     "disaster, so one of the two is never read", **where)
        else:
            seen[low] = b.head_line
        for key in DISASTER_NUMBERS:
            value = b.first(key)
            if b.has(key) and not kb.is_int(value):
                _finding(out, "bad_number", True,
                         f"`{b.kind}`'s {key} is `{value}`, and it is a whole "
                         "number", name=b.kind, line=b.line_of(key) + 1)
        for key in DISASTER_FLAGS:
            value = b.first(key).lower()
            if b.has(key) and value not in ("true", "false"):
                _finding(out, "bad_flag", False,
                         f"`{b.kind}`'s {key} is `{b.first(key)}`, and the "
                         "engine reads `true` or `false`",
                         name=b.kind, line=b.line_of(key) + 1)
        if not b.has("frequency"):
            _finding(out, "no_frequency", False,
                     f"`{b.kind}` has no `frequency`, so how often it happens "
                     "is whatever the engine defaults to", **where)
        lo, hi = b.first("min_scale"), b.first("max_scale")
        if kb.is_int(lo) and kb.is_int(hi) and int(lo) > int(hi):
            _finding(out, "scale_order", True,
                     f"`{b.kind}` has min_scale {lo} above max_scale {hi}, so "
                     "there is no size it can be",
                     name=b.kind, line=b.line_of("min_scale") + 1)
        if climates is not None:
            for i, value in enumerate(b.all("climate")):
                if not any(c.lower() == value.lower() for c in climates):
                    _finding(out, "unknown_climate", False,
                             f"`{b.kind}` names climate `{value}`, which "
                             "descr_climates.txt does not declare, so no tile "
                             "ever matches it",
                             name=b.kind, line=b.lines["climate"][i] + 1,
                             climate=value)
        out += _position_findings(b, regions, size)
    return out


# ---------------------------------------------------------------------------
# the screens


def _map_size(mod) -> Optional[Tuple[int, int]]:
    """``(width, height)`` off ``descr_terrain.txt``, or ``None``.

    A two-line read rather than a map load: this is only ever used to say
    whether a coordinate is on the grid, and decoding ten TGA layers to answer
    that would make opening the panel cost what opening the map costs.
    """
    try:
        t = campmap.read_terrain(mod)
    except Exception:                                  # noqa: BLE001 - a mod file
        return None                                    # that will not read is not
    return (t.width, t.height) if t and t.width and t.height else None


def _region_names(mod) -> Optional[List[str]]:
    try:
        return [r.name for r in campmap.read_regions(mod).records if r.name]
    except Exception:                                  # noqa: BLE001
        return None


def _climate_names(mod) -> Optional[List[str]]:
    try:
        names = [c["code"] for c in mapvocab.climates(mod)]
    except Exception:                                  # noqa: BLE001
        return None
    return names or None


def _campaign_factions(mod, campaign: str) -> Optional[List[str]]:
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError):
        return None
    seen: List[str] = []
    for node in sf.of_kind("faction"):
        if node.name and node.name not in seen:
            seen.append(node.name)
    return seen or None


def _block_payload(bf: BlockFile, b: Block, named: bool) -> Dict:
    out = {
        "lines": [b.start + 1, b.end],
        "head_line": b.head_line + 1,
        "positions": [p.as_dict() for p in b.positions],
        "regions": b.all("region"),
        "text": bf.block_text(b),
    }
    if named:
        out.update({"name": b.name, "category": b.kind,
                    "dates": b.all("date"), "movie": b.first("movie")})
    else:
        out.update({"type": b.kind, "climates": b.all("climate")})
        for key in DISASTER_KEYS:
            if key in DISASTER_REPEATED:
                continue
            out[key] = b.first(key)
            out[key + "_set"] = b.has(key)
    return out


def events_view(mod, campaign: str = DEFAULT_CAMPAIGN) -> Dict:
    """The events screen: every block, with what is wrong with each."""
    try:
        bf, _ = read_events(mod, campaign)
    except CampEventError as e:
        return {"campaign": campaign, "file": EVENTS_NAME, "have": False,
                "problem": e.message, "rows": [], "findings": [],
                "warnings": [], "categories": list(EVENT_CATEGORIES)}
    size = _map_size(mod)
    return {
        "campaign": campaign, "have": True, "problem": "",
        "file": f"{CAMPAIGN_DIR_REL}/{campaign}/{EVENTS_NAME}",
        "categories": list(EVENT_CATEGORIES),
        "placed": list(EVENT_PLACED),
        "size": list(size) if size else None,
        "text_file": EVENT_TEXT_REL,
        "eventspic": [str(d.relative_to(Path(mod.data))).replace("\\", "/")
                      for d in eventspic_dirs(mod)],
        "rows": [_block_payload(bf, b, True) for b in bf.blocks],
        "findings": check_events(bf, mod, campaign,
                                 _campaign_factions(mod, campaign),
                                 _region_names(mod), size),
        "warnings": list(bf.warnings),
    }


def disasters_view(mod) -> Dict:
    """The disasters screen. Not per campaign - the file is under the map."""
    try:
        bf, _ = read_disasters(mod)
    except CampEventError as e:
        return {"file": DISASTERS_REL, "have": False, "problem": e.message,
                "rows": [], "findings": [], "warnings": [],
                "types": list(DISASTER_TYPES)}
    size = _map_size(mod)
    climates = _climate_names(mod)
    return {
        "file": DISASTERS_REL, "have": True, "problem": "",
        "types": list(DISASTER_TYPES),
        "keys": list(DISASTER_KEYS),
        "flags": list(DISASTER_FLAGS),
        "sea_region": SEA_REGION,
        "size": list(size) if size else None,
        "climates": climates or [],
        "declared": len(bf.blocks),
        "rows": [_block_payload(bf, b, False) for b in bf.blocks],
        "findings": check_disasters(bf, mod, _region_names(mod), climates, size),
        "warnings": list(bf.warnings),
    }


def positions(mod, campaign: str = DEFAULT_CAMPAIGN) -> List[Dict]:
    """Every coordinate either file puts on the map, for 17d's marker layer.

    Coordinates are left exactly as the files write them, which is
    :func:`unittransfer.mapquery.marker_view`'s own rule: the flip to image
    coordinates belongs to whatever is holding the map's height, and doing it
    twice in two places is how a marker ends up mirrored.
    """
    out: List[Dict] = []
    try:
        bf, _ = read_events(mod, campaign)
    except (CampEventError, OSError):
        bf = None
    if bf is not None:
        for b in bf.blocks:
            for p in b.positions:
                out.append({"kind": "event", "name": b.name or b.kind,
                            "type": b.kind, "faction": "", "x": p.x, "y": p.y,
                            "line": p.line + 1,
                            "date": b.first("date")})
    try:
        df, _ = read_disasters(mod)
    except (CampEventError, OSError):
        df = None
    if df is not None:
        for b in df.blocks:
            for p in b.positions:
                out.append({"kind": "disaster", "name": b.kind, "type": b.kind,
                            "faction": "", "x": p.x, "y": p.y,
                            "line": p.line + 1,
                            "frequency": b.first("frequency")})
    return out


# ---------------------------------------------------------------------------
# the save - one plan and one apply over both files


#: what a save can be about
WHAT = ("events", "disasters")


@dataclass
class CampEventPlan:
    """One save, worked out without touching the disk."""

    mod: object = None
    what: str = ""
    campaign: str = DEFAULT_CAMPAIGN
    action: str = "edit"                 # 'edit' | 'add' | 'delete'
    name: str = ""                       # the event's label, or the disaster type
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    block: str = ""
    text: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} {self.what[:-1]} {self.name} in "
                f"{getattr(self.mod, 'name', '?')} ({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"what": self.what, "action": self.action, "name": self.name,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "block": self.block,
                "ok": not self.errors and bool(self.text)}


def plan(mod, body: dict) -> CampEventPlan:
    """Work out one save. ``body`` is ``{what, campaign, action, name, edits}``."""
    p = CampEventPlan(mod=mod, what=str(body.get("what") or "").strip(),
                      campaign=str(body.get("campaign") or DEFAULT_CAMPAIGN),
                      action=str(body.get("action") or "edit"),
                      name=str(body.get("name") or "").strip())
    if p.what not in WHAT:
        p.errors.append(f"a save is about {kb.and_list(list(WHAT))}, not "
                        f"{p.what!r}")
        return p
    try:
        if p.what == "events":
            _plan_events(p, dict(body.get("edits") or {}))
        else:
            _plan_disasters(p, dict(body.get("edits") or {}))
    except CampEventError as e:
        p.errors.append(e.message)
        return p
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _plan_events(p: CampEventPlan, edits: Dict) -> None:
    bf, original = read_events(p.mod, p.campaign)
    b = bf.by_name(p.name)
    if p.action == "add":
        if b is not None:
            p.errors.append(f"`{p.name}` already has a block at line "
                            f"{b.head_line + 1}")
            return
        rows = new_event_lines(str(edits.get("category") or "historic"), p.name,
                               edits, _pad(bf))
        text = insert_block(bf, rows)
        p.block = bf.newline.join(rows)
        p.changes.append(f"+ event {edits.get('category') or 'historic'} {p.name}")
    elif b is None:
        p.errors.append(f"`{p.name}` has no block in {EVENTS_NAME}")
        return
    elif p.action == "delete":
        text = remove_block(bf, b)
        p.block = bf.block_text(b)
        p.changes.append(f"- event {b.kind} {b.name}")
    else:
        text, p.changes = render_event(bf, b, edits)
    p.path = events_path(p.mod, p.campaign)
    p.text = "" if text == original else text
    after = parse_events(text)
    size = _map_size(p.mod)
    p.findings = check_events(after, p.mod, p.campaign,
                              _campaign_factions(p.mod, p.campaign),
                              _region_names(p.mod), size)
    _carry(p, after)


def _plan_disasters(p: CampEventPlan, edits: Dict) -> None:
    bf, original = read_disasters(p.mod)
    b = bf.by_name(p.name)
    if p.action == "add":
        if b is not None:
            p.errors.append(f"`{p.name}` already has a block at line "
                            f"{b.head_line + 1}")
            return
        rows = new_disaster_lines(p.name, edits, _column(bf))
        text = insert_block(bf, rows)
        p.block = bf.newline.join(rows)
        p.changes.append(f"+ event {p.name}")
    elif b is None:
        p.errors.append(f"`{p.name}` has no block in {DISASTERS_NAME}")
        return
    elif p.action == "delete":
        text = remove_block(bf, b)
        p.block = bf.block_text(b)
        p.changes.append(f"- event {b.kind}")
    else:
        text, p.changes = render_disaster(bf, b, edits)
    p.path = disasters_path(p.mod)
    p.text = "" if text == original else text
    after = parse_disasters(text)
    p.findings = check_disasters(after, p.mod, _region_names(p.mod),
                                 _climate_names(p.mod), _map_size(p.mod))
    _carry(p, after)


def _pad(bf: BlockFile) -> str:
    """The gap a new event block puts between a keyword and its value.

    A gap and not a column, because ``descr_events.txt`` is not in columns: the
    game's own file writes ``date\\t50`` (column 8) and ``position\\t257, 73``
    (column 12) three lines apart. One tab after every keyword is what it does,
    so one tab is what a new block copies - taken off the file's own first
    ``event`` line so a mod that indents differently keeps its own shape.
    """
    for b in bf.blocks:
        m = re.match(r"event(\s+)", kb.code_of(bf.lines[b.head_line]))
        if m:
            return m.group(1)
    return "\t"


def _column(bf: BlockFile) -> int:
    """The column ``descr_disasters.txt`` lines its values up in.

    Off the file's own first keyword line, because unlike the event file this
    one really is one column - see :data:`DISASTER_COLUMN`.
    """
    for b in bf.blocks:
        for key in DISASTER_KEYS:
            if b.has(key):
                line = bf.lines[b.lines[key][0]]
                return kb.value_column(line, kb.code_of(line).split()[0])
    return DISASTER_COLUMN


def _carry(p: CampEventPlan, after: BlockFile) -> None:
    """Findings become errors when fatal, and warnings when they are this block's.

    The same split 18a's movie save makes, and for the same reason: a mod is
    somebody else's work with somebody else's faults in it, so a finding about
    another block must not refuse this save.
    """
    low = p.name.lower()
    p.errors += [f["message"] for f in p.findings
                 if f["fatal"] and (f.get("name") or "").lower() == low]
    p.warnings += [f["message"] for f in p.findings
                   if not f["fatal"] and (f.get("name") or "").lower() == low]
    p.warnings += list(after.warnings)


def apply(p: CampEventPlan) -> Dict:
    """Write a planned save, with the same backups and undo as any other job."""
    import shutil
    import time

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text or p.path is None:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    rel = str(p.path.relative_to(Path(mod.data))).replace("\\", "/")
    bpath = backup_root / "data" / rel
    bpath.parent.mkdir(parents=True, exist_ok=True)
    if p.path.exists():
        shutil.copy2(p.path, bpath)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", p.path, f"-> {bpath}")
    else:
        manifest["created"].append(rel)
    p.path.parent.mkdir(parents=True, exist_ok=True)
    kb.write_text(p.path, p.text, ENCODING)
    file_op("WRITE", p.path, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campevents",
        "action": p.action,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.what,
        "options": {"campaign": p.campaign, "what": p.what},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPEVENT %s %s %s in %s - %d change(s), id=%s",
             p.action, p.what, p.name, mod.name, len(p.changes), tid)
    return {"id": tid, "what": p.what, "name": p.name, "record": rec}
