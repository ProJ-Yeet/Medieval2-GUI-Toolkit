"""``descr_strat.txt``, write: settlements and buildings.

16b read the file as lines plus an index over them and promised that 16h to 16j
would write into it without disturbing a byte they did not mean to change. This
is the first of the three, and it owns one record: the settlement block, which
is a province's level, its size, the plan its streets are drawn from, who built
it, what is standing in it, and - by where the block sits - who starts holding
it and whether it is that faction's capital.

**Three rulings carry in from 16g, and all three are load-bearing here.**

*One fact table, read by everything.* :func:`settlement_detail` builds its whole
form out of :class:`~unittransfer.mapquery.Facts`, which has already joined
every province to its owner, its buildings and the ``export_descr_buildings.txt``
line each building belongs to. Nothing here opens ``descr_strat.txt`` to draw a
picker. The write half is the deliberate exception and is stated where it is
made: :func:`plan_settlement` re-reads the file, because a writer that writes
out of a cache is how somebody else's edit disappears.

*A rule with no evidence reports nothing.* The stock game keeps its EDB and its
settlement plans inside the packed data, so on vanilla there is no list of
building levels and no list of plan sets to check a value against. The pickers
then offer what the campaign file itself already writes - 315 ``default_set``
and one ``osgiliath_east_a`` across the three campaigns measured - and the
compatibility rules do not run at all rather than reporting everything as
unknown.

*Python owns the bytes.* The browser posts the words somebody typed and the
list of buildings they are looking at. It never posts a line number, a splice or
a file.

**What the file actually says, measured rather than assumed.**

The settlement ladder is one ladder and both kinds of settlement climb it.
``level`` on a ``settlement castle`` is written with the same six city words -
vanilla has 14 castles at ``level village`` and 21 at ``level town`` - and the
castle's own tier is the level of its ``core_castle_building``, not the word on
the ``level`` line. A picker that offered ``motte_and_bailey`` here would be
offering a word the engine does not read in this place.

**The first settlement in a faction block is that faction's capital.** Nineteen
of vanilla's nineteen landed factions have theirs first and nothing before it:
London, Paris, Frankfurt, Leon, Venice, Palermo, Milan, Edinburgh,
Constantinople, Novgorod, Cordoba, Iconium, Cairo, Arhus, Lisbon, Cracow,
Budapest, Rome, Tenochtitlan. So changing the owner of a capital moves the
capital, and that is said in the plan rather than discovered in game.

**The EDB's settlement rules gate building, not starting.** Third Age Reforged
ships 432 of its 1,518 starting buildings below the ``settlement_min`` its own
EDB declares for them, and 248 in the wrong kind of settlement altogether - 27
merchant vaults, 25 conservatoriums and 24 docklands standing in castles - and
the mod loads and plays. So ``settlement_min``, ``settlement_max`` and the
``city``/``castle`` pin are reported here as warnings with the number beside
them, never as a refusal. Four of its settlements carry two or three levels of
one building line at once, so that is a warning too. What *is* fatal is a
``type`` line naming a level the EDB does not declare at all, and only when
there is an EDB on disk to say so.

**Every edit is a line rewrite.** A field edit rewrites the one line the field
came from and keeps its indent and its trailing comment. A building added is
four lines inserted in the shape of the building above it; a building removed is
its own span deleted. An owner change is one slice of lines moved from between
two lines to between two others, which is what 16b's spans exist for. Nothing
else in the file is touched, and the suite checks that by re-rendering every
settlement of every installed campaign with no edits at all and demanding the
file back byte for byte.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campstrat
from .campstrat import Node, StratFile

#: The settlement ladder, smallest first. One ladder, both kinds - see the
#: module docstring. The same six words as
#: :data:`unittransfer.buildings.SETTLEMENT_LEVELS`, held separately because
#: that one is the EDB's vocabulary for ``settlement_min`` and this one is the
#: campaign file's for ``level``; nothing says they must stay the same.
LADDER = ("village", "town", "large_town", "city", "large_city", "huge_city")

#: What the header line may say. ``settlement`` alone is a city.
SETTLEMENT_TYPES = ("city", "castle")

#: The castle tier each rung shows as in game, for the label beside the picker.
#: Not vocabulary - nothing is ever written from this - but a castle modder
#: thinks in these words and the ladder does not use them.
CASTLE_TIER = {"village": "(no keep)", "town": "motte and bailey",
               "large_town": "wooden castle", "city": "castle",
               "large_city": "fortress", "huge_city": "citadel"}

#: The settlement's own scalar fields, in the order the file writes them. The
#: header is separate and ``region`` is the identity, so neither is here.
FIELDS = ("level", "year_founded", "population", "plan_set", "faction_creator")

#: Which of those must read as a whole number.
NUMERIC = ("year_founded", "population")

_INT = re.compile(r"-?\d+")


# The helpers below this line are public because 16i reuses every one of them.
# A settlement block and a character block are different records with the same
# discipline - rewrite the line the field came from, keep its indent and its
# comment, move the span rather than rebuild it - and a second copy of that
# discipline is a second chance for one of them to drift.


def _clean(line: str) -> str:
    return line.split(";", 1)[0].strip()


def indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip("\t "))]


def comment_of(line: str) -> str:
    """The ``;`` comment on a line, with the space before it, or ``""``."""
    at = line.find(";")
    if at < 0:
        return ""
    before = line[:at]
    keep = len(before) - len(before.rstrip("\t "))
    return line[at - keep:]


def rewrite_line(line: str, body: str) -> str:
    """``body`` put back on this line with its indent and its comment kept.

    And its trailing whitespace, when there is no comment to hold the end of
    the line. 16i found that one: 215 of vanilla's 216 character lines end in a
    space, and a rewrite that quietly trimmed it would change a byte on a line
    nobody asked about.
    """
    got = comment_of(line)
    return indent_of(line) + body + (got or line[len(line.rstrip()):])


def is_int(value) -> bool:
    return bool(_INT.fullmatch(str(value).strip())) if value is not None else False


# ---------------------------------------------------------------------------
# finding things in the tree


def find_settlement(sf: StratFile, region: str) -> Optional[Node]:
    """The settlement block whose ``region`` line names ``region``."""
    low = region.strip().lower()
    for n in sf.of_kind("settlement"):
        if str(n.get("region") or "").strip().lower() == low:
            return n
    return None


def faction_of(sf: StratFile, node: Node) -> Optional[Node]:
    """The faction block ``node`` sits inside, walked up rather than guessed."""
    at = node.parent
    while at >= 0:
        p = sf.nodes[at]
        if p.kind == "faction":
            return p
        at = p.parent
    return None


def settlements_of(sf: StratFile, faction: Node) -> List[Node]:
    """That faction's settlement blocks, in the order the file writes them."""
    return sf.children_of(faction, "settlement")


def capital_of(sf: StratFile, faction: Node) -> str:
    """The region the faction's capital is in, or ``""`` when it holds nothing.

    The first settlement in the block, which is what the campaign opens with -
    see the module docstring for the nineteen that say so.
    """
    ss = settlements_of(sf, faction)
    return str(ss[0].get("region") or "") if ss else ""


def detach_span(sf: StratFile, node: Node, faction: Node) -> Tuple[int, int]:
    """The block's own lines, plus the blank ones that follow it.

    A settlement block ends on its closing brace and every real file puts a
    blank line after it. That blank is the block's separator rather than the
    next block's, so it travels with the block: taken out with it, put back in
    front of whatever the block is inserted before, and the file keeps the
    rhythm it was written in on both sides of a move.
    """
    end = node.end
    while end + 1 <= faction.end and not _clean(sf.lines[end + 1]):
        end += 1
    return node.start, end


def insert_at(sf: StratFile, faction: Node, place: str,
               skip: Optional[Node] = None) -> int:
    """Which line a block goes in front of to land ``first`` or ``last``.

    ``first`` is in front of the faction's first settlement, which is what makes
    it the capital. ``last`` is after the last one. A faction holding nothing
    yet takes it in front of its first character, and one with no characters
    either takes it at the end of its own block, which is where the file would
    have written it.
    """
    ss = [n for n in settlements_of(sf, faction) if n is not skip]
    if ss:
        return ss[0].start if place == "first" \
            else detach_span(sf, ss[-1], faction)[1] + 1
    after = [n for n in sf.children_of(faction)
             if n.kind in ("character", "character_record", "relative")]
    return after[0].start if after else faction.end + 1


# ---------------------------------------------------------------------------
# the buildings a settlement may have


@dataclass
class LevelInfo:
    """One building level as the EDB declares it, or as the map alone knows it."""

    level: str = ""
    line: str = ""
    #: ``city``, ``castle`` or ``""`` for either
    pin: str = ""
    settlement_min: str = ""
    settlement_max: str = ""
    #: false when the EDB could not be read, so nothing above it is evidence
    declared: bool = False

    def payload(self) -> dict:
        return {"level": self.level, "line": self.line, "pin": self.pin,
                "min": self.settlement_min, "max": self.settlement_max,
                "declared": self.declared}


class Vocabulary:
    """Every value a settlement form may offer, and why one of them is missing.

    Built from the fact table and the mod's EDB, and honest about the stock
    game: with no ``export_descr_buildings.txt`` on disk there is no list of
    levels to pick from and no ``settlement_min`` to check against, so
    :attr:`levels` holds only what the campaign file itself already writes and
    every one of them says ``declared: false``.
    """

    def __init__(self, facts, sf: StratFile):
        self.facts = facts
        self.sf = sf
        self.skipped: List[dict] = list(getattr(facts, "skipped", []))
        self.levels: Dict[str, LevelInfo] = {}
        self.lines: List[str] = []
        self.have_edb = False
        self._from_edb(facts)
        self._from_file(sf)
        self.factions = [str(n.get("name") or n.name) for n in sf.of_kind("faction")]
        self.rosters = {k: list(v) for k, v in sf.rosters.items()}
        self.plan_sets = self._values("plan_set")
        self.creators = self._values("faction_creator")

    def _from_edb(self, facts) -> None:
        try:
            edb = facts.mod.edb
        except Exception:                                  # noqa: BLE001
            edb = None
        if edb is None or not getattr(edb, "buildings", None):
            return
        self.have_edb = True
        for line in edb.buildings:
            self.lines.append(line.name)
            for blk in line.blocks:
                self.levels.setdefault(blk.name, LevelInfo(
                    level=blk.name, line=line.name, pin=blk.settlement,
                    settlement_min=blk.scalars.get("settlement_min", ""),
                    settlement_max=blk.scalars.get("settlement_max", ""),
                    declared=True))

    def _from_file(self, sf: StratFile) -> None:
        """Whatever the campaign file names that the EDB did not.

        On the stock game this is the whole vocabulary, and it is a real one:
        ``descr_strat.txt`` writes ``type <line> <level>``, so the line name is
        already in the campaign file and a settlement's buildings can be edited
        with no EDB anywhere on disk.
        """
        for b in sf.of_kind("building"):
            level, line = str(b.get("level") or ""), b.name or ""
            if not level:
                continue
            self.levels.setdefault(level, LevelInfo(level=level, line=line))
            if line and line not in self.lines:
                self.lines.append(line)
        self.lines.sort(key=str.lower)

    def _values(self, key: str) -> List[str]:
        """Every value the campaign file gives this field, commonest first."""
        counts: Dict[str, int] = {}
        for n in self.sf.of_kind("settlement"):
            v = str(n.get(key) or "")
            if v:
                counts[v] = counts.get(v, 0) + 1
        return [v for v, _ in sorted(counts.items(),
                                     key=lambda kv: (-kv[1], kv[0].lower()))]

    def levels_of(self, line: str) -> List[LevelInfo]:
        got = [i for i in self.levels.values() if i.line == line]
        return sorted(got, key=lambda i: (not i.declared, i.level.lower()))

    def payload(self) -> dict:
        return {
            "ladder": list(LADDER),
            "castle_tier": dict(CASTLE_TIER),
            "types": list(SETTLEMENT_TYPES),
            "have_edb": self.have_edb,
            "lines": [{"name": name,
                       "levels": [i.payload() for i in self.levels_of(name)]}
                      for name in self.lines],
            "factions": list(self.factions),
            "rosters": dict(self.rosters),
            "plan_sets": list(self.plan_sets),
            "creators": list(self.creators),
            "skipped": list(self.skipped),
        }


# ---------------------------------------------------------------------------
# what is wrong with a settlement as it stands


def finding(code: str, fatal: bool, message: str, **extra) -> dict:
    out = {"code": code, "fatal": fatal, "message": message}
    out.update(extra)
    return out


def check_settlement(voc: Vocabulary, kind: str, level: str, population,
                     year_founded, buildings: Sequence[Tuple[str, str]]
                     ) -> List[dict]:
    """Everything wrong with one settlement, fatal first.

    ``buildings`` is ``[(line, level)]`` in the order the block writes them.
    Only four things here are fatal, and each one is a value the engine's own
    vocabulary has no room for. Everything the EDB merely disapproves of is a
    warning, because Third Age Reforged disagrees with its own EDB 680 times
    and runs.
    """
    out: List[dict] = []
    if kind not in SETTLEMENT_TYPES:
        out.append(finding(
            "settlement.type", True,
            f"The header says {kind!r}. The engine reads `settlement` and "
            f"`settlement castle` and nothing else."))
    if level not in LADDER:
        out.append(finding(
            "settlement.level", True,
            f"{level or '(nothing)'} is not a settlement level. The six are "
            + ", ".join(LADDER) + ", for a castle as much as for a city."))
    for slot, value in (("population", population),
                        ("year_founded", year_founded)):
        text = "" if value is None else str(value).strip()
        if not is_int(text):
            out.append(finding(
                f"settlement.{slot}", True,
                f"{slot.replace('_', ' ')} is {text or '(nothing)'}, which is "
                f"not a whole number."))
        elif slot == "population" and int(text) < 0:
            out.append(finding(
                "settlement.population", True,
                "A settlement cannot start with a negative population."))

    seen: Dict[str, int] = {}
    at = LADDER.index(level) if level in LADDER else -1
    for line, lvl in buildings:
        info = voc.levels.get(lvl)
        if voc.have_edb and (info is None or not info.declared):
            out.append(finding(
                "building.unknown", True,
                f"{lvl or '(nothing)'} is not a building level "
                f"export_descr_buildings.txt declares, so the campaign has "
                f"nothing to put there.", level=lvl, line=line))
            continue
        if info is None:
            continue
        if info.declared and line and info.line and line != info.line:
            out.append(finding(
                "building.line", False,
                f"{lvl} is a level of {info.line} and this line says {line}. "
                f"The engine goes by the level; the line name beside it is "
                f"only read as far as finding the building.",
                level=lvl, line=line))
        key = (info.line or line).lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            out.append(finding(
                "building.repeat", False,
                f"Two levels of {info.line or line} stand in this settlement at "
                f"once. Third Age Reforged ships four settlements like it, so "
                f"it is not fatal, but only one of them is the building.",
                level=lvl, line=info.line or line))
        if not info.declared:
            continue
        if info.pin and kind and info.pin != kind:
            out.append(finding(
                "building.pin", False,
                f"{lvl} is declared for a {info.pin} and this is a {kind}. It "
                f"stands and works; nobody can build it back if it falls.",
                level=lvl, line=info.line))
        lo = info.settlement_min
        if lo in LADDER and at >= 0 and at < LADDER.index(lo):
            out.append(finding(
                "building.min", False,
                f"{lvl} wants a {lo.replace('_', ' ')} and this is a "
                f"{level.replace('_', ' ')}. The campaign may start with it "
                f"anyway; nobody can build it back.",
                level=lvl, line=info.line))
        hi = info.settlement_max
        if hi in LADDER and at >= 0 and at > LADDER.index(hi):
            out.append(finding(
                "building.max", False,
                f"{lvl} is declared up to a {hi.replace('_', ' ')} and this is "
                f"a {level.replace('_', ' ')}.",
                level=lvl, line=info.line))
    out.sort(key=lambda f: not f["fatal"])
    return out


# ---------------------------------------------------------------------------
# the form


def settlement_detail(facts, region: str) -> dict:
    """One settlement, everything the panel shows, in one call.

    Read out of the fact table rather than off the disk, which is 16g's rule
    and the reason a panel that opens on a province costs nothing: the join is
    already done and cached, and every picker below is a walk over what it
    holds.
    """
    from .campmap import MapError

    sf = getattr(facts, "strat", None)
    if sf is None:
        raise MapError(f"{facts.strat_rel} could not be read, so this map has "
                       f"no campaign to edit")
    node = find_settlement(sf, region)
    rf = facts.by_name.get(region.strip().lower())
    if node is None:
        raise MapError(
            f"no settlement in {facts.campaign}'s descr_strat.txt stands in "
            f"{region!r}"
            + (". The province is declared and nobody starts holding it, which "
               "is legal: it opens as unclaimed wilderness."
               if rf is not None else "."))
    faction = faction_of(sf, node)
    voc = Vocabulary(facts, sf)
    kind = str(node.get("settlement_type") or "city")
    level = str(node.get("level") or "")
    buildings = [(b.name or "", str(b.get("level") or ""))
                 for b in sf.children_of(node, "building")]
    owner = str(faction.get("name") or faction.name) if faction else ""
    capital = capital_of(sf, faction) if faction else ""
    region_name = str(node.get("region") or "")

    return {
        "region": region_name,
        "campaign": facts.campaign,
        "file": facts.strat_rel,
        "shown": rf.shown if rf else "",
        "settlement": rf.settlement if rf else "",
        "shown_settlement": rf.shown_settlement if rf else "",
        "settlement_type": kind,
        "level": level,
        "castle_tier": CASTLE_TIER.get(level, "") if kind == "castle" else "",
        "population": node.get("population"),
        "year_founded": node.get("year_founded"),
        "plan_set": str(node.get("plan_set") or ""),
        "faction_creator": str(node.get("faction_creator") or ""),
        "owner": owner,
        "owner_label": facts.faction_label(owner) if owner else "",
        "capital": capital,
        "is_capital": bool(capital)
        and capital.lower() == region_name.lower(),
        "lines": [node.start + 1, node.end + 1],
        "text": sf.newline.join(sf.lines[node.start:node.end + 1]),
        "buildings": [
            {"line": line, "level": lvl,
             "info": (voc.levels.get(lvl)
                      or LevelInfo(level=lvl, line=line)).payload()}
            for line, lvl in buildings],
        "findings": check_settlement(voc, kind, level, node.get("population"),
                                     node.get("year_founded"), buildings),
        "problems": list(node.problems),
        "vocab": voc.payload(),
        "factions": _faction_rows(sf, facts),
    }


def _faction_rows(sf: StratFile, facts) -> List[dict]:
    """Every faction the settlement could be given to, with what it holds now.

    The roster it is in comes with it, because a faction in none of the three
    lists is one the campaign never loads, and handing it a province is handing
    the province to nobody.
    """
    roster_of: Dict[str, str] = {}
    for name, members in sf.rosters.items():
        for f in members:
            roster_of.setdefault(f.lower(), name)
    out = []
    for n in sf.of_kind("faction"):
        name = str(n.get("name") or n.name)
        ss = settlements_of(sf, n)
        out.append({
            "name": name,
            "label": facts.faction_label(name),
            "roster": roster_of.get(name.lower(), ""),
            "settlements": len(ss),
            "capital": str(ss[0].get("region") or "") if ss else "",
            "line": n.start + 1,
        })
    return out


# ---------------------------------------------------------------------------
# the block, rewritten a line at a time


def assemble(base: List[str], rewrites: Dict[int, str], drop: set,
              inserts: Dict[int, List[str]]) -> List[str]:
    """``base`` with those three edits applied, in one pass and in order."""
    out: List[str] = []
    for i, line in enumerate(base):
        out += inserts.get(i, [])
        if i in drop:
            continue
        out.append(rewrites.get(i, line))
    return out + inserts.get(len(base), [])


def _field_home(node: Node, base: List[str], key: str) -> Tuple[int, str]:
    """Where a field that is not in the block yet goes, and what it is indented by.

    In front of the next field the file would have written after it, so a
    ``population`` added to a block that has ``plan_set`` lands above it rather
    than at the bottom. A block with none of them at all takes it under the
    ``region`` line, which every settlement has.
    """
    order = list(FIELDS)
    later = order[order.index(key) + 1:] if key in order else []
    for nxt in later:
        at = node.field_lines.get(nxt)
        if at is not None:
            local = at - node.start
            return local, indent_of(base[local])
    homes = [node.field_lines.get(k) for k in ("region",) + FIELDS]
    last = max((a for a in homes if a is not None), default=None)
    if last is not None:
        local = last - node.start
        return local + 1, indent_of(base[local])
    return max(1, len(base) - 1), "\t"


def _building_block(indent: str, inner: str, line: str, level: str) -> List[str]:
    return [f"{indent}building", f"{indent}{{",
            f"{inner}type {line} {level}".rstrip(), f"{indent}}}"]


def render_block(sf: StratFile, node: Node, edits: Optional[dict] = None,
                 buildings: Optional[Sequence[Tuple[str, str]]] = None
                 ) -> List[str]:
    """The settlement's lines as they would be written, and no others.

    A field whose value is not changing is not rewritten at all, which is not
    an optimisation: it is the only way a block whose modder lined its values up
    with tabs comes back with the tabs still in it. The same goes for a building
    that keeps its level, so editing the fourth of six leaves the other five
    exactly as they were, comments included.
    """
    edits = dict(edits or {})
    base = list(sf.lines[node.start:node.end + 1])
    rewrites: Dict[int, str] = {}
    drop: set = set()
    inserts: Dict[int, List[str]] = {}

    kind = str(edits.get("settlement_type")
               or node.get("settlement_type") or "city").strip()
    if kind != str(node.get("settlement_type") or "city"):
        rewrites[0] = rewrite_line(
            base[0], "settlement" if kind == "city" else f"settlement {kind}")

    for key in FIELDS:
        if key not in edits:
            continue
        want = str(edits[key]).strip()
        have = "" if node.get(key) is None else str(node.get(key)).strip()
        if want == have:
            continue
        at = node.field_lines.get(key)
        if at is not None:
            local = at - node.start
            rewrites[local] = rewrite_line(base[local], f"{key} {want}".rstrip())
        elif want:
            local, indent = _field_home(node, base, key)
            inserts.setdefault(local, []).append(f"{indent}{key} {want}")

    if buildings is not None:
        old = sf.children_of(node, "building")
        if old:
            indent = indent_of(base[old[0].start - node.start])
        else:
            # Nothing to copy the shape from, so the block's own fields say how
            # deep a line inside it sits. The opening brace is no use for this:
            # every real file writes it one level out from what it opens.
            home = next((node.field_lines[k] for k in ("region",) + FIELDS
                         if k in node.field_lines), None)
            indent = indent_of(base[home - node.start]) if home is not None \
                else indent_of(base[-1]) + "\t"
        first_type = next((b.field_lines["type"] for b in old
                           if "type" in b.field_lines), None)
        inner = indent_of(sf.lines[first_type]) if first_type is not None \
            else indent + "\t"
        want = list(buildings)
        for i, (line, level) in enumerate(want[:len(old)]):
            b = old[i]
            if (b.name or "", str(b.get("level") or "")) == (line, level):
                continue
            at = b.field_lines.get("type")
            if at is None:                       # a block with no readable type
                drop |= set(range(b.start - node.start, b.end - node.start + 1))
                inserts.setdefault(b.start - node.start, []).extend(
                    _building_block(indent, inner, line, level))
                continue
            local = at - node.start
            rewrites[local] = rewrite_line(base[local], f"type {line} {level}".rstrip())
        for b in old[len(want):]:
            drop |= set(range(b.start - node.start, b.end - node.start + 1))
        if len(want) > len(old):
            home = (old[-1].end - node.start + 1) if old else len(base) - 1
            extra: List[str] = []
            for line, level in want[len(old):]:
                extra += _building_block(indent, inner, line, level)
            inserts.setdefault(home, []).extend(extra)

    return assemble(base, rewrites, drop, inserts)


def split_block(text: str) -> List[str]:
    """Hand-typed block text as lines, whatever the box put in it for newlines."""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


# ---------------------------------------------------------------------------
# moving the block between faction blocks


def move_lines(lines: List[str], span: Tuple[int, int], at: int) -> List[str]:
    """``lines`` with ``span`` lifted out and put back in front of ``at``.

    ``at`` is a line number in the list as it stands now, which is why it is
    shifted by the length of the slice when the slice came out from above it.
    Nothing is copied and nothing is re-indented: the block that arrives is the
    block that left.
    """
    start, end = span
    payload = lines[start:end + 1]
    rest = lines[:start] + lines[end + 1:]
    landing = at if at <= start else at - len(payload)
    landing = max(0, min(landing, len(rest)))
    return rest[:landing] + payload + rest[landing:]


# ---------------------------------------------------------------------------
# the plan


@dataclass
class StratPlan:
    """One settlement's save, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    region: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the settlement's new lines, for the preview
    block: str = ""
    #: what moved, said in one line, or ``""`` when the block stayed put
    moved: str = ""
    #: the faction the settlement now belongs to, set only when it changed
    owner_to: str = ""
    #: what the capital of each faction involved becomes
    capitals: List[str] = field(default_factory=list)
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"edit settlement {self.region} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"region": self.region, "campaign": self.campaign,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "findings": list(self.findings),
                "block": self.block, "moved": self.moved,
                "owner_to": self.owner_to,
                "capitals": list(self.capitals),
                "ok": not self.errors and bool(self.text)}


def serialise(sf: StratFile, lines: List[str]) -> str:
    """A new set of lines in the file's own newline and trailing-newline shape."""
    return (sf.newline.join(lines)
            + (sf.newline if sf.trailing_newline else ""))


def blocks_by_region(sf: StratFile) -> Tuple[Dict[str, str], List[str]]:
    """Every settlement's own text, keyed by the province it stands in.

    The guard below compares two of these. It is the whole byte-exactness claim
    turned into something the writer can check on itself before it writes,
    rather than something only the suite finds out about afterwards.

    A block with no ``region`` line at all has no key and cannot have one: it is
    a defect 16f reports, this writer will not touch it, and numbering it by
    where it happens to sit would make a move look like a rewrite. Those come
    back as a second list, compared as a set of texts rather than by name. No
    installed campaign has one - 316 blocks, all named - and the list is here so
    that the first mod that does gets an honest answer rather than a confident
    wrong one.
    """
    named: Dict[str, str] = {}
    nameless: List[str] = []
    for n in sf.of_kind("settlement"):
        text = "\n".join(sf.lines[n.start:n.end + 1])
        key = str(n.get("region") or "").strip().lower()
        if key:
            named[key] = text
        else:
            nameless.append(text)
    return named, sorted(nameless)


def _guard(before: StratFile, after: StratFile, region: str) -> List[str]:
    """What the edit did that it was never asked to do.

    Cheap, and it catches the two mistakes this kind of writer actually makes:
    a brace miscounted, so a settlement swallows the one below it, and a move
    that lands inside another block. Both show up here as a count that changed
    or a settlement whose text is not what it was, and both are refused before
    anything reaches the disk.
    """
    out: List[str] = []
    was, now = before.counts(), after.counts()
    for kind in sorted(set(was) | set(now)):
        if kind == "building":                 # the one this phase may change
            continue
        if was.get(kind, 0) != now.get(kind, 0):
            out.append(f"this would leave {now.get(kind, 0)} {kind} record(s) "
                       f"where the file has {was.get(kind, 0)}, and 16h edits "
                       f"one settlement")
    if before.rosters != after.rosters:
        out.append("this would change the playable, unlockable or nonplayable "
                   "lists, which no settlement edit does")
    if before.globals != after.globals:
        out.append("this would change the campaign's own header values")

    (a, a_odd), (b, b_odd) = blocks_by_region(before), blocks_by_region(after)
    if set(a) != set(b):
        gone = sorted(set(a) - set(b))
        got = sorted(set(b) - set(a))
        out.append("this would leave the campaign holding a different set of "
                   "provinces"
                   + (f" (lost {', '.join(gone[:4])})" if gone else "")
                   + (f" (gained {', '.join(got[:4])})" if got else ""))
        return out
    if a_odd != b_odd:
        out.append(f"this would rewrite one of the {len(a_odd)} settlement "
                   f"block(s) that name no province at all, which is a defect "
                   f"to fix rather than a block to edit")
        return out
    low = region.strip().lower()
    changed = [k for k in a if k != low and a[k] != b[k]]
    if changed:
        out.append(f"this would rewrite {len(changed)} settlement block(s) "
                   f"nobody asked it to, starting with {changed[0]}")
    return out


def _describe(before: dict, after: dict) -> List[str]:
    """What changed, said the way somebody would say it out loud."""
    out: List[str] = []
    if before["kind"] != after["kind"]:
        out.append(f"kind: {before['kind']} -> {after['kind']}")
    if before["level"] != after["level"]:
        tier = (f" ({CASTLE_TIER.get(after['level'], '')})"
                if after["kind"] == "castle" else "")
        out.append(f"level: {before['level'] or '(none)'} -> "
                   f"{after['level'] or '(none)'}{tier}")
    for slot in ("year_founded", "population", "plan_set", "faction_creator"):
        if before[slot] != after[slot]:
            out.append(f"{slot.replace('_', ' ')}: {before[slot] or '(none)'}"
                       f" -> {after[slot] or '(none)'}")
    was = [f"{line} {level}" for line, level in before["buildings"]]
    now = [f"{line} {level}" for line, level in after["buildings"]]
    if was != now:
        gone = [b for b in was if b not in now]
        got = [b for b in now if b not in was]
        if got:
            out.append("buildings added: " + ", ".join(got))
        if gone:
            out.append("buildings removed: " + ", ".join(gone))
        if not got and not gone:
            out.append(f"buildings reordered ({len(now)} of them)")
    return out


#: What a settlement whose ``region`` line stopped naming its province is
#: told. The line is the settlement's identity and four other files point at
#: it, so the edit is refused rather than left to be found at campaign start.
_LOST_REGION = (
    "after this edit nothing in the file stands in {region} any more. A "
    "settlement's `region` line is its identity: descr_regions.txt, the "
    "campaign script and the win conditions all name it")


def _snapshot(sf: StratFile, node: Node) -> dict:
    return {
        "kind": str(node.get("settlement_type") or "city"),
        "level": str(node.get("level") or ""),
        "year_founded": node.get("year_founded"),
        "population": node.get("population"),
        "plan_set": str(node.get("plan_set") or ""),
        "faction_creator": str(node.get("faction_creator") or ""),
        "buildings": [(b.name or "", str(b.get("level") or ""))
                      for b in sf.children_of(node, "building")],
    }


def plan_settlement(mod, facts, body: dict) -> StratPlan:
    """Work out the whole new ``descr_strat.txt`` for one settlement's save.

    ``body`` is ``{region, edits, buildings, owner, place, raw_block}``.
    ``edits`` are the form's boxes, ``buildings`` is the whole list in the order
    the panel shows it, ``owner`` and ``place`` are where the block should end
    up, and ``raw_block`` is text somebody hand-edited in the Code View, which
    wins over ``edits`` and ``buildings`` and reaches disk verbatim, the ruling
    every other editor in this toolkit makes.

    **The file is re-read here rather than taken from ``facts``.** The fact
    table is a cache, and a writer that writes out of a cache writes over
    whatever changed on disk since it was filled. ``facts`` is still used for
    the one thing it is: the vocabulary the findings are measured against.

    Nothing is written. What comes back is the whole file as it would be, the
    block as it would read, and the reasons it would be refused.
    """
    from .campmap import MapError

    campaign = str(body.get("campaign") or "") or facts.campaign
    p = StratPlan(mod=mod, campaign=campaign,
                  region=str(body.get("region") or "").strip())
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = sf.path

    node = find_settlement(sf, p.region)
    if node is None:
        p.errors.append(f"no settlement in {campaign}'s descr_strat.txt stands "
                        f"in {p.region!r}")
        return p
    faction = faction_of(sf, node)
    if faction is None:
        p.errors.append(f"the settlement in {p.region} is not inside any "
                        f"faction block, so there is nobody to save it for")
        return p
    source = str(faction.get("name") or faction.name)
    before = _snapshot(sf, node)

    # -- 1) the block itself
    raw = str(body.get("raw_block") or "")
    if raw.strip():
        block = split_block(raw)
        head = _clean(block[0]) if block else ""
        if not head.lower().startswith("settlement"):
            p.errors.append(
                "a settlement block opens with the word `settlement`, on its "
                f"own or followed by `castle`. This one opens with {head!r}")
            return p
        depth = sum(_clean(ln).count("{") - _clean(ln).count("}") for ln in block)
        if depth:
            p.errors.append(
                f"the braces in this block do not balance ({depth:+d}), so "
                f"everything below it would be read as part of it")
            return p
    else:
        want = body.get("buildings")
        buildings = None if want is None else [
            (str(b.get("line") or "").strip(), str(b.get("level") or "").strip())
            for b in want]
        block = render_block(sf, node, body.get("edits") or {}, buildings)

    lines = sf.lines[:node.start] + block + sf.lines[node.end + 1:]

    # -- 2) where the block sits
    owner = str(body.get("owner") or "").strip()
    place = str(body.get("place") or "").strip().lower()
    place = place if place in ("first", "last") else ""
    if owner or place:
        # The tree is rebuilt here rather than patched, and that is deliberate:
        # a move needs spans that agree with the lines it is moving, and the
        # block above may have changed how many lines there are and where every
        # brace after it sits. A parse costs a fifth of a second on the largest
        # campaign installed; a stale span costs somebody their campaign. When
        # nothing moves this parse is skipped, because step 3 does it anyway.
        mid = campstrat.parse_strat(serialise(sf, lines))
        node2 = find_settlement(mid, p.region)
        if node2 is None:
            p.errors.append(_LOST_REGION.format(region=p.region))
            return p
        dest_name = owner or source
        dest = mid.faction(dest_name)
        if dest is None:
            p.errors.append(
                f"{dest_name} has no faction block in {campaign}'s "
                f"descr_strat.txt, so it cannot be given a province. Creating "
                f"a faction is 16j; cloning one that already works is what the "
                f"Factions screen does today")
            return p
        src2 = faction_of(mid, node2)
        same = src2 is not None and dest.start == src2.start
        if not place:
            place = "" if same else "last"
        if place:
            held = mid.children_of(dest, "settlement")
            at = insert_at(mid, dest, place, skip=node2 if same else None)
            span = detach_span(mid, node2, src2) if src2 is not None \
                else (node2.start, node2.end)
            if span[0] <= at <= span[1] + 1:
                at = span[1] + 1                  # already where it is going
            lines = move_lines(mid.lines, span, at)
            if not same:
                p.moved = f"{source} -> {dest_name}"
                p.owner_to = dest_name
            elif place == "first":
                p.moved = f"moved to the front of {dest_name}'s block"
            elif held and held[0] is node2:
                p.moved = f"no longer {source}'s first settlement"

    # -- 3) read back exactly what would be written, and check that
    text = serialise(sf, lines)
    done = campstrat.parse_strat(text)
    node3 = find_settlement(done, p.region)
    if node3 is None:
        p.errors.append(_LOST_REGION.format(region=p.region))
        return p
    p.errors += _guard(sf, done, p.region)
    if p.errors:
        return p

    voc = Vocabulary(facts, done)
    after = _snapshot(done, node3)
    p.block = "\n".join(done.lines[node3.start:node3.end + 1])
    p.findings = check_settlement(voc, after["kind"], after["level"],
                                  after["population"], after["year_founded"],
                                  after["buildings"])
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(before, after)
    if p.moved:
        p.changes.append(f"owner: {p.moved}")
    p.warnings += _owner_warnings(sf, done, p, source)
    p.capitals = _capital_notes(sf, done, p, source)

    p.text = "" if text == sf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _owner_warnings(before: StratFile, after: StratFile, p: StratPlan,
                    source: str) -> List[str]:
    """The two things a move does that nobody asked it to do.

    A faction stripped of its last province is not an error, because a mod may
    well want one that starts with nothing and emerges by script, but it is
    never worth finding out about in game. And ``faction_creator`` is what
    decides whose architecture a settlement is built in, so a city that changes
    hands goes on looking like its old owner's until that is changed too.
    """
    out: List[str] = []
    if not p.owner_to:
        return out
    old, new = before.faction(source), after.faction(source)
    if old is not None and new is not None \
            and settlements_of(before, old) and not settlements_of(after, new):
        out.append(f"{source} is left holding no settlement at all, so the "
                   f"campaign opens with it already destroyed unless a script "
                   f"gives it one.")
    node = find_settlement(after, p.region)
    creator = str(node.get("faction_creator") or "") if node is not None else ""
    if creator and creator.lower() == source.lower():
        out.append(f"faction_creator is still {creator}, which is what decides "
                   f"the settlement's own architecture. It changes hands and "
                   f"goes on looking {creator}.")
    return out


def _capital_notes(before: StratFile, after: StratFile, p: StratPlan,
                   source: str) -> List[str]:
    """Which faction's capital this save moves, said before it is saved.

    Only the factions the edit touches are looked at, and only when the answer
    changed. A note per faction per save, rather than a table of every capital
    on the map saying the same thing every time.
    """
    out: List[str] = []
    names = {source}
    node = find_settlement(after, p.region)
    if node is not None:
        f = faction_of(after, node)
        if f is not None:
            names.add(str(f.get("name") or f.name))
    for name in sorted(names):
        old_f, new_f = before.faction(name), after.faction(name)
        if old_f is None or new_f is None:
            continue
        was, now = capital_of(before, old_f), capital_of(after, new_f)
        if was != now:
            out.append(f"{name}'s capital: {was or '(none)'} -> "
                       f"{now or '(none)'}")
    return out


# ---------------------------------------------------------------------------
# the save


def apply_settlement(p: StratPlan) -> dict:
    """Write a planned save, with the same backups and undo as any other job.

    The old ``descr_strat.txt`` goes to ``config/backups/<id>/data/…`` and the
    manifest goes in the transfer log, so the Log's Undo puts it back
    byte-exact.

    **``map.rwm`` is not deleted here, and that is a decision rather than an
    oversight.** The region editor deletes it because it writes
    ``descr_regions.txt``, which is one of the files the compiled map is built
    out of; the campaign file is not. ``descr_strat.txt`` is read fresh every
    time a campaign starts, which is why a mod's own author can move an army
    and see it moved without waiting for the map to rebuild. Deleting the
    binary here would cost a recompile on the next load and change nothing.
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
        "action": "settlement",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.region, "resolved_type": p.region,
        "options": {"campaign": p.campaign, "moved": p.moved},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(),
        "warnings": list(p.warnings) + list(p.capitals),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SETTLE %s in %s/%s - %d change(s), id=%s",
             p.region, mod.name, p.campaign, len(p.changes), tid)
    return {"id": tid, "region": p.region, "campaign": p.campaign,
            "record": rec}
