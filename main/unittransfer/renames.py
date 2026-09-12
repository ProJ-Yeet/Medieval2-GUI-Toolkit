"""Phase 19b. Renaming a thing whose name IS its identity.

Three subjects and one engine: a **region**, a **settlement** and a **faction**
are each named by a bare token that other files point at, so renaming one in the
file that declares it and nowhere else is the one edit that is worse than no edit
at all. 16d refuses all three today, in three places, with the reason spelled
out; this is the answer to that refusal, and the refusal was right about the
problem.

**Everything here is position-aware, and that is not caution - it is measured.**
The obvious implementation is :mod:`unittransfer.unitrefs`' - walk the whole mod
and rewrite the token wherever it stands alone - and over these three namespaces
it would corrupt real mods:

* Divide and Conquer's region ``Eregion_Province`` has the settlement
  ``Eregion``, and ``Eregion`` is **also a hidden resource** on the flags line of
  twenty other regions in the same file. A token walk over ``descr_regions.txt``
  renaming that settlement would rewrite all twenty.
* ``Dunland`` is a settlement, a sound folder (``data/sounds/Voice/Dunland``),
  the first word of eleven unit types, a ``custom_location``, a climate comment,
  and in Third Age Reforged a faction slot as well. Settlement names matched in
  **60 files** across the two installed mods and most of those hits are
  coincidences.
* A faction slot is worse still: ``united`` and ``scripts`` are Divide and
  Conquer's, and one of its files names a slot 93,437 times.

So a rename asks each *file* which of its *lines* may hold a name of this kind -
through the module that already owns that file, wherever one exists - and
rewrites the token only on those lines. Everywhere else in the mod is
**reported and never touched**.

**Region names, by contrast, are a clean namespace, and that is measured too.**
All 198 of Divide and Conquer's and all 199 of Third Age Reforged's appear in
fifteen files and twelve respectively, and every one of those is a campaign or
base map file whose shape is known. That is what makes D2 doable at all: the
hard half of a region rename is not finding the references, it is knowing that
the list is closed.

**What the two installed mods actually say a settlement's name is worth.** The
refusal 16d wrote - and the one the region panel still showed - says
``descr_strat.txt`` points at a settlement name. **It does not.** A settlement
block in ``descr_strat.txt`` carries ``region <province>`` and no settlement name
at all; every one of the 578 and 147 whole-word hits in the two mods'
``descr_strat.txt`` is a unit type, a portrait, a character label or a comment.
A settlement is named in exactly three places - its province's record in
``descr_regions.txt``, the lookup file's pairs, and the ``{key}`` it is read
through - plus the campaign script, which is reported. The refusal was
overstating its case, the way 19a found ``NAME_SECTIONS`` doing, and it is
corrected in the same commit as this module.

**``campaign_script.txt`` is reported, never edited**, and that is the same
ruling 15g made about ``descr_strat.txt`` and 16f makes about a vocabulary that
is not on disk. The script is a grammar nothing here parses; a rename that
silently left it pointing at a dead name would be worse than no rename. Every
occurrence is listed with its line number and its line, and the plan says so
before anything is written.

**A rename does not renumber anything.** Region IDs are first-appearance order in
a row-major scan of ``map_regions.tga``, which is why D1 (recolouring) is
expensive - but a rename touches no pixel and moves no record, so every ID, every
``IsRegionOneOf`` operand and every ``map.rwm`` cache stays exactly as it was.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import (campfiles, campmap, campstrat, cleaner, config, factionclone,
               factions as fac, keyblock as kb, modeldb as mdb, stringsbin,
               winconds)
from .logutil import file_op, log

ENCODING = "latin-1"
LOC_ENCODING = "utf-16"

SUBJECTS = ("region", "settlement", "faction")

#: What each subject is called in a sentence the user reads.
NOUN = {"region": "province", "settlement": "settlement", "faction": "faction"}

#: A province or a settlement is a word the map files spell as it is written. A
#: faction slot is stricter still - see :data:`unittransfer.factionclone.SLOT_RE`.
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

#: The script grammars this refuses to edit, under any campaign folder.
SCRIPT_NAMES = ("campaign_script.txt", "custom_script.txt")

#: How many occurrences of one file are listed before the count stands in for
#: the rest. The script's own list is not capped by this - the plan's promise is
#: that every line of it is reported.
MENTION_LIMIT = 12

#: Where a mod keeps art the engine finds from the faction's own name.
ART_ROOTS = factionclone.ART_ROOTS


class RenameError(ValueError):
    """The request names something this mod has not got, or asks for a name it
    already has."""


# ---------------------------------------------------------------------------
# finding the files
#
# `campstrat.campaigns` lists the campaign folders directly under
# `world/maps/campaign`, which is right for a screen that offers a campaign to
# open and wrong here: Divide and Conquer keeps Shattered_Alliances under
# `custom/` and Third Age Reforged keeps Fellowship_Campaign there, and both are
# whole campaigns with their own descr_strat, win conditions, mercenaries and
# script. A rename that skipped them would leave the mod's second campaign
# pointing at a name that no longer exists.
#
# 20b moved the walk itself into `campstrat`, which owns the file, and found
# that "right for a screen that offers a campaign to open" was wrong too - the
# screen was offering one campaign of two. This is now that one list, as paths.


def campaign_dirs(mod) -> List[Path]:
    """Every folder under ``world/maps/campaign`` holding a ``descr_strat.txt``.

    At any depth, which is the difference from
    :func:`unittransfer.campstrat.campaigns`;
    :func:`unittransfer.campstrat.campaign_paths` is the same list as names and
    is what this reads.
    """
    base = Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
    return [base / rel for rel in campstrat.campaign_paths(mod)]


def region_files(mod) -> List[Path]:
    """Every ``descr_regions.txt``: the base one, and any campaign's own copy.

    Third Age Reforged's Fellowship campaign ships its own with all 199 regions
    in it, so "the regions file" is a list rather than a path.
    """
    data = Path(mod.data)
    out = [data / campmap.REGIONS_REL]
    out += [d / "descr_regions.txt" for d in campaign_dirs(mod)]
    return [p for p in out if p.is_file()]


def base_and_campaign(mod, name: str) -> List[Path]:
    """``world/maps/base/<name>`` plus every campaign folder's own copy."""
    data = Path(mod.data)
    out = [data / campmap.BASE_REL / name]
    out += [d / name for d in campaign_dirs(mod)]
    return [p for p in out if p.is_file()]


def key_files(mod) -> List[Path]:
    """Every ``text/*_regions_and_settlement_names.txt`` this mod ships.

    Globbed rather than named per campaign: Divide and Conquer has one each for
    ``imperial_campaign`` and ``shattered_alliances`` and Third Age Reforged has
    one serving two campaigns. Either way each keys a province and a settlement
    by their own code names, so a rename that missed one would leave that
    campaign's map showing the old word.
    """
    text = Path(mod.data) / "text"
    return sorted(text.glob("*_regions_and_settlement_names.txt")) if text.is_dir() else []


def script_files(mod) -> List[Path]:
    """The campaign scripts, which are reported and never written."""
    out: List[Path] = []
    for d in campaign_dirs(mod):
        out += [d / n for n in SCRIPT_NAMES]
    return [p for p in out if p.is_file()]


def _rel(mod, path: Path) -> str:
    data = Path(mod.data)
    return path.relative_to(data).as_posix() if path.is_relative_to(data) else path.name


# ---------------------------------------------------------------------------
# rewriting one line
#
# Four rules, and they are about WHERE on a line a name of this kind may sit.
# Only a token equal to the old name is ever rewritten, so a rule that is
# generous about the line is still safe - what a rule must be exact about is
# which lines it is applied to, and that is what the finders below decide.


def _code_end(line: str) -> int:
    """Where the code part of a line stops. ``;`` opens a comment anywhere."""
    at = line.find(";")
    return len(line) if at < 0 else at


def _token_spans(text: str, old: str, start: int = 0, stop: int = -1
                 ) -> List[Tuple[int, int]]:
    """Every whole-token occurrence of ``old`` in ``text[start:stop]``.

    The boundary is :mod:`unittransfer.unitrefs`' - a name is never found inside
    a longer identifier, so renaming ``Anorien_Province`` leaves
    ``Anorien_Provincea`` (which Divide and Conquer's ``custom_tiles_db.txt``
    really does write, six times) exactly where it was.
    """
    stop = len(text) if stop < 0 else stop
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])")
    return [(m.start(), m.end()) for m in pat.finditer(text, start, stop)]


def _spans_any(line: str, old: str) -> List[Tuple[int, int]]:
    """Anywhere in the line's code, and never in its comment."""
    return _token_spans(line, old, 0, _code_end(line))


def _spans_first(line: str, old: str) -> List[Tuple[int, int]]:
    """The first whitespace-delimited token only.

    ``custom_tiles_db.txt`` is a table whose first column is a province and whose
    later columns are coordinates, a ``.wfc`` file, a weather word and a time of
    day. None of those could equal a province name, but reading only the column
    that is one costs nothing and says what the file is.
    """
    code = line[:_code_end(line)]
    head = code.strip()
    if not head:
        return []
    at = len(code) - len(code.lstrip())
    word = head.split(None, 1)[0]
    return [(at, at + len(word))] if word == old else []


_KEY_LINE = re.compile(r"^([ \t]*)\{([^}]*)\}")


def _spans_key(line: str, old: str) -> List[Tuple[int, int]]:
    """The ``{key}`` of a ``{key}value`` line, and never its value.

    ``{Anorien}Anorien`` is a real line - the code name and the shown word are
    very often the same - so a rule that rewrote the whole line would change what
    the player reads as a side effect of renaming the record.
    """
    m = _KEY_LINE.match(line)
    if not m or m.group(2).strip() != old:
        return []
    at = m.start(2) + (len(m.group(2)) - len(m.group(2).lstrip()))
    return [(at, at + len(old))]


def _spans_key_word(line: str, old: str) -> List[Tuple[int, int]]:
    """The slot inside an UPPER CASE text key, where ``_`` separates words.

    ``{EMT_SICILY_ADMIRAL}`` is the slot joined to other words with underscores,
    so this is the one place the data-file token rule is the wrong one - it is
    :func:`unittransfer.factionclone._key_tok`'s instead, and using the other
    would find the bare ``{SICILY}`` and none of the thirty ``EMT_`` keys.
    """
    m = _KEY_LINE.match(line)
    if not m:
        return []
    pat = re.compile(factionclone._key_tok(old.upper()))
    return [(m.start(2) + h.start(), m.start(2) + h.end())
            for h in pat.finditer(m.group(2))]


#: ``requires factions { sicily, }``, ``FactionStanding factions { … }``,
#: ``exclude_factions { … }`` - the one clause shape three files share, and the
#: reason the keyword cannot be read off the front of the line: in
#: ``export_descr_buildings.txt`` the line opens with ``recruit_pool`` and the
#: clause is most of the way along it. One installed mod writes 12,295 of these.
_BRACED = re.compile(r"(?<![A-Za-z0-9_])(?:exclude_factions|factions)\s*\{([^}]*)\}")

#: What opens a line whose tail is a *condition operand*: ``Condition FactionType
#: sicily``, ``and GeneralFoughtFaction sicily``, ``relationship Hates sicily``.
#: A clone cannot follow these - :mod:`unittransfer.factionclone` says so at
#: length, because adding a faction to a boolean means rewriting its logic - but
#: a **rename** can and must: the condition still means the same faction, which
#: is now called something else.
_OPERAND_HEADS = ("condition", "and", "or", "not", "relationship")


def _spans_braced(line: str, old: str) -> List[Tuple[int, int]]:
    """Inside a ``factions { … }`` clause, wherever on the line it sits."""
    stop = _code_end(line)
    out: List[Tuple[int, int]] = []
    for m in _BRACED.finditer(line, 0, stop):
        out += _token_spans(line, old, m.start(1), min(m.end(1), stop))
    return out


def _spans_operand(line: str, old: str) -> List[Tuple[int, int]]:
    """The tail of a condition line, and nothing else in the file.

    ``export_descr_character_traits.txt`` also names a faction inside a trait's
    own name (``Trait Fearssicily``) and inside an engine effect
    (``Combat_V_Faction_Sicily``); neither is a token by the rule above - one has
    a letter before it and the other an underscore - so neither is found, which
    is what makes reading only the operand lines a belt as well as braces.
    """
    code = line[:_code_end(line)]
    head = code.split(None, 1)[0].lower() if code.split() else ""
    return _spans_any(line, old) if head in _OPERAND_HEADS else []


def _spans_all(line: str, old: str) -> List[Tuple[int, int]]:
    """Anywhere at all, comment or not - for the XML files, where ``;`` is data."""
    return _token_spans(line, old)


RULES: Dict[str, Callable[[str, str], List[Tuple[int, int]]]] = {
    "any": _spans_any, "first": _spans_first, "all": _spans_all,
    "braced": _spans_braced, "operand": _spans_operand,
    "key": _spans_key, "key_word": _spans_key_word}

#: How the new name is spelled where a rule found the old one. Only one rule
#: needs this and it is not decoration: ``text/expanded.txt`` writes the slot in
#: UPPER CASE inside every key, so writing the slot back as typed would give the
#: faction thirty keys the engine looks up in capitals and does not find.
RULE_CASE: Dict[str, Callable[[str], str]] = {"key_word": str.upper}


def rewrite_lines(lines: List[str], where: Dict[int, str], old: str, new: str
                  ) -> Tuple[List[str], List[int]]:
    """Rewrite ``old`` -> ``new`` on the lines ``where`` allows, and say which.

    ``where`` is ``{line index: rule}``. The replacement per line runs
    back-to-front so an earlier span's offsets stay valid, which matters because
    one ``regions`` line can name the same province more than once in a file
    somebody has hand-edited.
    """
    out = list(lines)
    touched: List[int] = []
    for i, rule in sorted(where.items()):
        if not 0 <= i < len(out):
            continue
        spans = RULES[rule](out[i], old)
        if not spans:
            continue
        line, word = out[i], RULE_CASE.get(rule, str)(new)
        for start, end in reversed(spans):
            line = line[:start] + word + line[end:]
        out[i] = line
        touched.append(i)
    return out, touched


# ---------------------------------------------------------------------------
# which lines of which file
#
# One finder per file shape. Each takes the file's text and the subject and
# returns `{line index: rule}` - and every one that has an owner module asks that
# module rather than parsing the file a second time, which is the ruling 16j-2
# made and 19a followed.


def _find_regions(text: str, subject: str) -> Dict[int, str]:
    """``descr_regions.txt``, through :func:`unittransfer.campmap.parse_regions`.

    The settlement field is the reason this file cannot be walked as tokens: a
    hidden resource named after a settlement sits on the flags line of the same
    record, and the flags line is not in this map.
    """
    rf = campmap.parse_regions(text)
    fields = {"region": ("name_line", "legion_line"),
              "settlement": ("settlement_line",),
              "faction": ("faction_line",)}[subject]
    out: Dict[int, str] = {}
    for rec in rf.records:
        for name in fields:
            at = getattr(rec, name, -1)
            if at >= 0:
                out[at] = "any"
    return out


def _find_strat(text: str, subject: str) -> Dict[int, str]:
    """``descr_strat.txt``, through :func:`unittransfer.campstrat.parse_strat`.

    A settlement gets nothing, and that is the measurement rather than an
    omission: a settlement block names its province and never itself.
    """
    if subject == "settlement":
        return {}
    sf = campstrat.parse_strat(text)
    out: Dict[int, str] = {}
    if subject == "region":
        for node in sf.nodes:
            # `region <province>` inside a settlement block, and the depth-0
            # `region <name>` section that holds forts and watchtowers
            for key in ("region", "name" if node.kind == "region" else ""):
                at = node.field_lines.get(key, -1) if key else -1
                if at >= 0:
                    out[at] = "any"
        return out
    for start, end in sf.roster_lines.values():          # playable / unlockable / …
        for at in range(start, end + 1):
            out[at] = "any"
    for node in sf.nodes:
        # `faction x, balanced smith`, a settlement's `faction_creator`, and both
        # sides of every standings and relationships line
        for key in ("faction", "faction_creator", "creator_faction", "toward"):
            at = node.field_lines.get(key, -1)
            if at >= 0:
                out[at] = "any"
        if node.kind == "faction" or (node.kind == "character"
                                      and node.fields.get("sub_faction")):
            out[node.start] = "any"
    return out


def _find_wins(text: str, subject: str) -> Dict[int, str]:
    """``descr_win_conditions.txt``, through :func:`unittransfer.winconds.parse_wins`.

    A record's head line is the faction; ``hold_regions`` and its short-campaign
    twin are the province lists; ``outlive`` names other factions. ``take_regions``
    is a count and holds no name, which is why it is not here.
    """
    wf = winconds.parse_wins(text)
    slots = {"region": ("hold", "short_hold"),
             "faction": ("outlive", "short_outlive"),
             "settlement": ()}[subject]
    out: Dict[int, str] = {}
    for rec in wf.records:
        if subject == "faction":
            out[rec.start] = "any"
        for slot in slots:
            at = rec.lines.get(slot, -1)
            if at >= 0:
                out[at] = "any"
    return out


def _find_mercs(text: str, subject: str) -> Dict[int, str]:
    """``descr_mercenaries.txt``, through :func:`unittransfer.campfiles.parse_mercs`.

    Only the ``regions`` lines. A pool is very often named after a province it
    sells in - Divide and Conquer has ``pool Dunland`` beside the province
    ``Dunland_Province`` - and a pool name is its own namespace, so renaming the
    province must leave the pool's name alone.
    """
    if subject != "region":
        return {}
    mf = campfiles.parse_mercs(text)
    return {at: "any" for at in mf.regions_line.values() if at >= 0}


def _find_lookup(text: str, subject: str) -> Dict[int, str]:
    """``descr_regions_and_settlement_name_lookup.txt``: pairs, one to a line.

    Nothing owns this file and it needs nothing owned - it is the simplest in the
    game: a province on one line and its settlement on the next, 177 pairs in
    Divide and Conquer and 191 in Third Age Reforged. Blank lines and comments do
    not count towards the alternation, so the pairing is over code lines only.
    """
    if subject == "faction":
        return {}
    want = 0 if subject == "region" else 1
    out: Dict[int, str] = {}
    seen = 0
    for i, line in enumerate(text.split("\n")):
        if not kb.code_of(line):
            continue
        if seen % 2 == want:
            out[i] = "any"
        seen += 1
    return out


def _find_music(text: str, subject: str) -> Dict[int, str]:
    """``descr_sounds_music_types.txt``: the ``regions`` and ``factions`` lists.

    Nobody owns it either. A ``music_type`` block's body is one keyword to a line
    and the two keywords that hold names are the two this looks for.
    """
    kw = {"region": "regions", "faction": "factions"}.get(subject, "")
    if not kw:
        return {}
    return {i: "any" for i, line in enumerate(text.split("\n"))
            if kb.code_of(line).split(None, 1)[:1] == [kw]}


def _find_tiles(text: str, subject: str) -> Dict[int, str]:
    """``custom_tiles_db.txt``: a table whose first column is a province."""
    if subject != "region":
        return {}
    return {i: "first" for i, line in enumerate(text.split("\n")) if kb.code_of(line)}


def _find_keys(text: str, subject: str) -> Dict[int, str]:
    """A ``{key}value`` file: the key, and never the value it is read as."""
    if subject == "faction":
        return {}
    return {i: "key" for i, line in enumerate(text.split("\n")) if _KEY_LINE.match(line)}


def _find_expanded(text: str, subject: str) -> Dict[int, str]:
    """``text/expanded.txt``: the slot inside the shown-name and ``EMT_*`` keys."""
    if subject != "faction":
        return {}
    return {i: "key_word" for i, line in enumerate(text.split("\n"))
            if _KEY_LINE.match(line)}


def _find_roster(text: str, subject: str) -> Dict[int, str]:
    """``descr_sm_factions.txt``: the record head, which is the slot itself."""
    return {rec.start: "any" for rec in fac.parse_text(text).records}


def _find_braced(text: str, subject: str) -> Dict[int, str]:
    """Every line carrying a ``factions { … }`` clause, wherever on it."""
    if subject != "faction":
        return {}
    return {i: "braced" for i, line in enumerate(text.split("\n"))
            if _BRACED.search(line, 0, _code_end(line))}


def _find_operand(text: str, subject: str) -> Dict[int, str]:
    """Every condition line, whose tail may name a faction."""
    if subject != "faction":
        return {}
    out: Dict[int, str] = {}
    for i, line in enumerate(text.split("\n")):
        code = kb.code_of(line)
        if code and code.split(None, 1)[0].lower() in _OPERAND_HEADS:
            out[i] = "operand"
    return out


def _find_xml(text: str, subject: str) -> Dict[int, str]:
    """An XML file where the only slot-shaped token is a slot.

    ``<Faction>sicily</Faction>`` and ``target_faction="sicily"`` are the two
    shapes, in ``descr_sounds_db.xml`` and ``descr_campaign_ai_db.xml``. Nothing
    else in either file is a bare lower-case word standing alone, so the whole
    line is offered and the token rule does the rest - and ``;`` is not a comment
    in XML, which is why this cannot use the rule every other file here uses.
    """
    if subject != "faction":
        return {}
    return {i: "all" for i, _ in enumerate(text.split("\n"))}


def _find_keyword(*words: str) -> Callable[[str, str], Dict[int, str]]:
    """A finder for any file whose names sit on lines a fixed keyword opens.

    ``ownership england, france``, ``requires factions { sicily, }``,
    ``texture sicily, models_strat/…``, ``faction: sicily`` - eight of the twelve
    files :mod:`unittransfer.factionclone` clones into are this shape, and what
    tells a name from a path or a number is which keyword opened the line.
    """
    heads = tuple(w.lower() for w in words)

    def find(text: str, subject: str) -> Dict[int, str]:
        out: Dict[int, str] = {}
        for i, line in enumerate(text.split("\n")):
            code = kb.code_of(line)
            if code and code.split(None, 1)[0].lower().rstrip(":") in heads:
                out[i] = "any"
        return out
    return find


# ---------------------------------------------------------------------------
# the site tables


@dataclass(frozen=True)
class Site:
    """One file a rename rewrites, and how it finds the name in it."""
    paths: Callable[[object], List[Path]]
    label: str
    find: Callable[[str, str], Dict[int, str]]
    encoding: str = ENCODING
    note: str = ""


def _one(rel: str) -> Callable[[object], List[Path]]:
    return lambda mod: [p for p in [Path(mod.data) / rel] if p.is_file()]


def _each_campaign(name: str) -> Callable[[object], List[Path]]:
    return lambda mod: [p for p in (d / name for d in campaign_dirs(mod)) if p.is_file()]


#: Where a **province** is named. Fifteen files in Divide and Conquer and twelve
#: in Third Age Reforged, and this is all of them bar the script.
REGION_SITES: Tuple[Site, ...] = (
    Site(region_files, "Region records", _find_regions,
         note="the record's own head, and any `legion:` line naming it"),
    Site(_each_campaign(campstrat.STRAT_NAME), "Campaign start position", _find_strat,
         note="every settlement's `region` line, and the forts-and-towers section"),
    Site(_each_campaign(winconds.REL_NAME), "Win conditions", _find_wins,
         note="the provinces a faction has to hold, long campaign and short"),
    Site(_each_campaign(campfiles.MERCS_NAME), "Mercenary pools", _find_mercs,
         note="the `regions` line of every pool this province is in"),
    Site(_each_campaign("descr_regions_and_settlement_name_lookup.txt"),
         "Region and settlement lookup", _find_lookup,
         note="the province half of the pair"),
    Site(lambda mod: base_and_campaign(mod, "descr_sounds_music_types.txt"),
         "Campaign music", _find_music,
         note="which music type plays over this province"),
    Site(_each_campaign("custom_tiles_db.txt"), "Custom battle tiles", _find_tiles,
         note="the first column, which is the province a tile belongs to"),
    Site(key_files, "The words the player reads", _find_keys, encoding=LOC_ENCODING,
         note="the {key} the campaign map reads the province through"),
)

#: Where a **settlement** is named. Three files, measured - see the docstring.
SETTLEMENT_SITES: Tuple[Site, ...] = (
    Site(region_files, "Region records", _find_regions,
         note="the settlement line of its own province's record"),
    Site(_each_campaign("descr_regions_and_settlement_name_lookup.txt"),
         "Region and settlement lookup", _find_lookup,
         note="the settlement half of the pair"),
    Site(key_files, "The words the player reads", _find_keys, encoding=LOC_ENCODING,
         note="the {key} the campaign map reads the settlement through"),
)

#: Where a **faction slot** is named: the twelve files
#: :mod:`unittransfer.factionclone` clones into, plus the five a clone had no
#: reason to touch and a rename cannot skip - the campaign start position (which
#: a clone deliberately leaves alone because there is nothing to copy, and which
#: a rename must follow because the block is already there), the province records
#: that name a creator, the win conditions, the campaign music and the guilds.
FACTION_SITES: Tuple[Site, ...] = (
    Site(_one(fac.REL), "Faction roster", _find_roster, note="the slot itself"),
    Site(_one("export_descr_unit.txt"), "Unit roster ownership",
         _find_keyword("ownership"), note="every unit this faction may recruit"),
    Site(_one("export_descr_buildings.txt"), "Recruitment and construction",
         _find_braced,
         note="every `requires factions { … }` that lets it build or recruit"),
    Site(_one("descr_faction_standing.txt"), "Diplomatic standing", _find_braced,
         note="the standing rules it is named in, on either side"),
    Site(_one("descr_missions.txt"), "Missions", _find_braced,
         note="the missions offered to it"),
    Site(_one("descr_character.txt"), "Agents and generals", _find_keyword("faction"),
         note="which character types it may field"),
    Site(_one("descr_sounds_accents.txt"), "Voice accent", _find_keyword("factions"),
         note="the accent its characters speak with"),
    Site(_one("descr_model_strat.txt"), "Campaign map models", _find_keyword("texture"),
         note="the strat-map art for each agent type"),
    Site(_one("descr_names.txt"), "Character names", _find_keyword("faction"),
         note="the name pool its characters are drawn from"),
    Site(_one("descr_lbc_db.txt"), "Settlement populace", _find_keyword("faction"),
         note="the civilian models that walk its streets"),
    Site(_one("descr_offmap_models.txt"), "Off-map navy models", _find_keyword("faction"),
         note="the ships shown at the edge of the map"),
    Site(_one("export_descr_guilds.txt"), "Guilds", _find_operand,
         note="the `FactionType` condition on each guild it may build"),
    Site(_one("export_descr_character_traits.txt"), "Character traits", _find_operand,
         note="every condition naming it - and never a trait or an engine effect "
              "with the slot glued into its name, which is not a token"),
    Site(_one("export_descr_ancillaries.txt"), "Ancillaries", _find_operand,
         note="every `FactionType` operand naming it"),
    Site(_one("export_descr_sounds_prebattle.txt"), "Prebattle speeches", _find_operand,
         note="every `relationship … <faction>` line naming it"),
    Site(_one("descr_sounds_music.txt"), "Faction music", _find_keyword("faction", "factions"),
         note="the theme that plays for it"),
    Site(_one("descr_sounds_db.xml"), "Sound database", _find_xml,
         note="its <Faction> element"),
    Site(_one("descr_campaign_ai_db.xml"), "Campaign AI", _find_xml,
         note="every `target_faction` this AI has an opinion about"),
    Site(region_files, "Region records", _find_regions,
         note="every province that names it as its creator"),
    Site(_each_campaign(campstrat.STRAT_NAME), "Campaign start position", _find_strat,
         note="its roster line, its own block, every settlement it created and "
              "both sides of every standing and relationship line"),
    Site(_each_campaign(winconds.REL_NAME), "Win conditions", _find_wins,
         note="its own record, and every `outlive` line naming it"),
    Site(lambda mod: base_and_campaign(mod, "descr_sounds_music_types.txt"),
         "Campaign music", _find_music, note="which music type plays for it"),
    Site(_one("text/expanded.txt"), "Faction name and event text", _find_expanded,
         encoding=LOC_ENCODING,
         note="the shown name and the ~30 EMT_* keys built from the slot"),
)

SITES: Dict[str, Tuple[Site, ...]] = {
    "region": REGION_SITES, "settlement": SETTLEMENT_SITES, "faction": FACTION_SITES}

#: **A rename follows five files a clone refuses**, and the difference is worth
#: saying out loud because it looks like an inconsistency and is not.
#: :data:`unittransfer.factionclone.REVIEW_FILES` are the files where naming the
#: donor is a *judgement*: adding a clone to ``and FactionType sicily`` means
#: rewriting a boolean's logic, and giving it a trait or a prebattle speech means
#: inventing one. None of that applies here. A rename does not add a faction to
#: anything - the condition, the trait and the speech already exist and already
#: mean this faction, which is now called something else. So traits, ancillaries,
#: prebattle speeches, missions and guilds are **sites**, not review, and the
#: only thing left that a rename refuses to follow is the campaign script.
CLONE_REVIEW_FILES: Tuple[str, ...] = factionclone.REVIEW_FILES


# ---------------------------------------------------------------------------
# the parts of a rename that are not lines


def rename_modeldb(text: str, old: str, new: str) -> Tuple[str, int]:
    """``battle_models.modeldb``: every texture record naming the old slot.

    A texture record's faction is a length-prefixed string, so the count in front
    of it has to change with it - which is the part of this file nobody can
    maintain by hand and the reason this is not a search and replace. Per ENTRY,
    for :func:`unittransfer.factionclone.clone_modeldb`'s reason: the span reader
    reads one entry and finds no texture groups in a whole file.
    """
    db = mdb.parse_text(text)
    done = 0
    for e in db.entries:
        raw, hits = _rename_entry_factions(e.raw, old, new, e.first_entry_pad)
        if hits:
            e.raw = raw
            done += hits
    return (db.to_text() if done else text), done


def _rename_entry_factions(raw: str, old: str, new: str, pad: bool) -> Tuple[str, int]:
    """One entry's texture records, back to front so offsets stay valid."""
    groups = mdb._texture_group_spans(raw, pad=pad)
    edits = [(rec["start"], rec["fac_end"]) for g in groups for rec in g["records"]
             if rec["fac"] == old]
    out = raw
    for start, end in sorted(edits, reverse=True):
        out = out[:start] + f"{len(new)} {new}" + out[end:]
    return out, len(edits)


@dataclass
class AssetMove:
    """One art file or folder whose name carries the faction's."""
    src: str
    dst: str
    is_dir: bool = False
    files: int = 0


def art_moves(mod, old: str, new: str) -> List[AssetMove]:
    """The art the engine finds BY CONVENTION, under its new name.

    ``symbol24_sicily_roll.tga``, ``faction_banner_sicily``, ``ui/units/sicily/``
    - nothing points at any of these, the engine builds the path out of the slot,
    so a renamed faction whose art kept the old name has none. Found by globbing
    for the slot as a token under the art roots, which is
    :func:`unittransfer.factionclone._asset_hits`' rule and is right for the same
    reason: a hardcoded list would be wrong for every mod that ships a folder
    vanilla does not.
    """
    data = Path(mod.data)
    tok = re.compile(factionclone._tok(old))
    out: List[AssetMove] = []
    seen: set = set()
    for root in ART_ROOTS:
        base = data / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not tok.search(p.name):
                continue
            # a file inside an already-matched folder moves with the folder
            rel = p.relative_to(data).as_posix()
            if any(rel.startswith(s + "/") for s in seen):
                continue
            seen.add(rel)
            dst = p.with_name(tok.sub(new, p.name)).relative_to(data).as_posix()
            out.append(AssetMove(src=rel, dst=dst, is_dir=p.is_dir(),
                                 files=sum(1 for f in p.rglob("*") if f.is_file())
                                 if p.is_dir() else 1))
    return out


# ---------------------------------------------------------------------------
# what a rename would do


@dataclass
class FileEdit:
    """One file this rename rewrites, and its whole new text."""
    rel: str
    label: str
    text: str = ""
    encoding: str = ENCODING
    count: int = 0
    note: str = ""
    #: the 1-based lines that changed, for the plan's own report
    lines: List[int] = field(default_factory=list)


@dataclass
class Mention:
    """One place the name is written that this rename will NOT touch."""
    rel: str
    line: int
    text: str


@dataclass
class RenamePlan:
    """One rename, worked out without touching the disk."""

    mod: object = None
    subject: str = ""
    old: str = ""
    new: str = ""
    edits: List[FileEdit] = field(default_factory=list)
    assets: List[AssetMove] = field(default_factory=list)
    #: every occurrence in a campaign script, in full - the plan's own promise
    script: List[Mention] = field(default_factory=list)
    #: the files whose mention is a judgement: `{rel, hits, lines}`
    review: List[Dict] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def written(self) -> List[FileEdit]:
        return [e for e in self.edits if e.text]

    def touched(self) -> bool:
        return bool(self.written() or self.assets)

    def hits(self) -> int:
        return sum(e.count for e in self.written())

    def files(self) -> List[str]:
        return [e.rel for e in self.written()]

    def summary(self) -> str:
        head = (f"rename {NOUN[self.subject]} {self.old} -> {self.new} in "
                f"{getattr(self.mod, 'name', '?')} ({self.hits()} line(s) in "
                f"{len(self.written())} file(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {
            "subject": self.subject, "old": self.old, "new": self.new,
            "files": [{"rel": e.rel, "label": e.label, "count": e.count,
                       "note": e.note, "lines": e.lines[:MENTION_LIMIT]}
                      for e in self.written()],
            "hits": self.hits(),
            "assets": [{"src": a.src, "dst": a.dst, "dir": a.is_dir,
                        "files": a.files} for a in self.assets],
            "script": [{"rel": m.rel, "line": m.line, "text": m.text}
                       for m in self.script],
            "review": list(self.review),
            "changes": list(self.changes), "warnings": list(self.warnings),
            "errors": list(self.errors), "notes": list(self.notes),
            "ok": not self.errors and self.touched(),
        }


def _names(mod, subject: str) -> Dict[str, List[str]]:
    """Every name this mod already uses, so a collision is refused before a write.

    A province and a settlement are checked against **each other** as well as
    against their own kind, because the two share one ``{key}value`` file: a
    province renamed to a settlement's name would take over that settlement's
    line on the campaign map, which is a rename that looks like it worked.
    """
    out = {"region": [], "settlement": [], "faction": []}
    for path in region_files(mod):
        rf = campmap.parse_regions(kb.read_text(path, ENCODING))
        for rec in rf.records:
            out["region"].append(rec.name)
            if rec.settlement:
                out["settlement"].append(rec.settlement)
    path = Path(mod.data) / fac.REL
    if path.is_file():
        out["faction"] = [fac.slot_of(r.name)
                          for r in fac.parse_text(kb.read_text(path, ENCODING)).records]
    return out


def _validate(p: RenamePlan, known: Dict[str, List[str]]) -> None:
    """Everything that can be wrong before a byte is planned."""
    kind = NOUN[p.subject]
    mine = {n.lower() for n in known[p.subject]}
    if p.old.lower() not in mine:
        p.errors.append(f"there is no {kind} called {p.old!r} in "
                        f"{getattr(p.mod, 'name', '?')}")
        return
    if not p.new:
        p.errors.append(f"a rename needs the new name")
        return
    if p.new == p.old:
        p.errors.append(f"{p.new} is the name it already has")
        return
    if p.subject == "faction":
        if not factionclone.SLOT_RE.match(p.new):
            p.errors.append(
                f"{p.new!r} is not a faction slot - the engine reads a slot as a "
                f"lower-case word of letters, digits and underscores, and every "
                f"file that names one spells it that way")
            return
        if p.new in factionclone.RESERVED or p.old in factionclone.RESERVED:
            p.errors.append(
                f"{kb.and_list(list(factionclone.RESERVED))} are reserved - the "
                f"engine means something specific by each of them, so neither "
                f"end of a rename may be one")
            return
    elif not NAME_RE.match(p.new):
        p.errors.append(
            f"{p.new!r} is not a name these files can hold - a {kind} is one "
            f"word of letters, digits, underscores and hyphens, starting with a "
            f"letter, because that is what every file naming one writes")
        return
    clash = ("region", "settlement") if p.subject in ("region", "settlement") \
        else ("faction",)
    for other in clash:
        if p.new.lower() in {n.lower() for n in known[other]}:
            p.errors.append(
                f"this mod already has a {NOUN[other]} called {p.new} - and a "
                f"province and its settlement are keyed in one file, so a second "
                f"{p.new} would take over the first one's line on the campaign map"
                if other != p.subject else
                f"this mod already has a {NOUN[other]} called {p.new}")
            return


def _read(path: Path, encoding: str) -> str:
    return kb.read_text(path, encoding)


def _plan_sites(p: RenamePlan) -> None:
    """Every file the rename rewrites, in the order the plan reports it."""
    done: set = set()
    for site in SITES[p.subject]:
        for path in site.paths(p.mod):
            rel = _rel(p.mod, path)
            if rel in done:
                continue
            done.add(rel)
            try:
                text = _read(path, site.encoding)
            except (OSError, UnicodeError) as exc:
                p.warnings.append(f"{rel} could not be read ({exc}), so nothing "
                                  f"in it was renamed")
                continue
            lines, newline, trailing = campmap._split_lines(text)
            try:
                where = site.find(text, p.subject)
            except Exception as exc:                     # a file we cannot parse
                p.warnings.append(f"{rel} did not parse ({exc}), so nothing in "
                                  f"it was renamed - open it in Code View")
                continue
            out, touched = rewrite_lines(lines, where, p.old, p.new)
            if not touched:
                continue
            body = newline.join(out) + (newline if trailing else "")
            p.edits.append(FileEdit(rel=rel, label=site.label, text=body,
                                    encoding=site.encoding, count=len(touched),
                                    note=site.note,
                                    lines=[i + 1 for i in touched]))
            p.changes.append(f"{rel}: {len(touched)} line(s) - {site.note}")


def _plan_modeldb(p: RenamePlan) -> None:
    """The one file in the set that is length-prefixed rather than lines."""
    path = Path(p.mod.data) / "unit_models/battle_models.modeldb"
    if not path.is_file():
        return
    text = _read(path, ENCODING)
    try:
        out, hits = rename_modeldb(text, p.old, p.new)
    except Exception as exc:
        p.warnings.append(
            f"battle_models.modeldb did not read ({exc}), so the faction's "
            f"texture records still name {p.old} and its units will show no skin "
            f"for it - the BMDB screen reports the same fault in detail")
        return
    if hits:
        p.edits.append(FileEdit(rel="unit_models/battle_models.modeldb",
                                label="Battle model skins", text=out, count=hits,
                                note="a texture record per model, and the "
                                     "length in front of each one"))
        p.changes.append(f"unit_models/battle_models.modeldb: {hits} texture "
                         f"record(s), each with its length token")


def _scan_mentions(p: RenamePlan) -> None:
    """What names the old name and is NOT rewritten: the scripts, and the rest.

    **The scripts are listed line by line**, which is the plan's own promise, and
    they are the reason this exists at all.

    Everything else is counted per file rather than listed, because the counts
    are the honest shape of it: renaming Divide and Conquer's ``Dunland`` finds
    the word in sixty files and in most of them it is a unit type, a sound folder
    or a comment. A list of four thousand lines is not a report and would make
    the two lines that matter unfindable. The file set is
    :func:`unittransfer.unitrefs.scan_paths`' - the mod's own definition files,
    every campaign file and every Lua script, which is the set this project
    already decided could name a thing.
    """
    p.script, p.review = mentions(p.mod, p.old, {e.rel for e in p.edits})


def mentions(mod, name: str, written: Optional[set] = None
             ) -> Tuple[List[Mention], List[dict]]:
    """``(script lines, other files)`` naming ``name`` and not being written.

    Split out of :func:`_scan_mentions` in 24 so that G1's delete reports the
    same thing the same way. A delete is a rename to nothing and it refuses to
    follow the script for exactly the reason a rename does, so the two share the
    scan rather than each having one that can drift.
    """
    from . import unitrefs

    written = set(written or ())
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
    script: List[Mention] = []
    review: List[dict] = []
    scripts = set()
    for path in script_files(mod):
        rel = _rel(mod, path)
        scripts.add(rel)
        for i, line in enumerate(_read(path, ENCODING).split("\n")):
            if pat.search(line):
                script.append(Mention(rel=rel, line=i + 1, text=line.strip()[:200]))
    # A whole-mod walk reads tens of megabytes - Divide and Conquer's
    # export_descr_buildings.txt alone is six - so the substring is looked for in
    # the raw bytes first and the great majority of files never get decoded. That
    # is the difference between a preview that appears and one that is waited for.
    needle = name.encode(ENCODING, "replace")
    for path in unitrefs.scan_paths(mod):
        rel = _rel(mod, path)
        if rel in written or rel in scripts:
            continue
        try:
            if needle not in path.read_bytes():
                continue
        except OSError:
            continue
        lines = [i + 1 for i, line in enumerate(_read(path, ENCODING).split("\n"))
                 if pat.search(line)]
        if not lines:
            continue
        review.append({"rel": rel, "hits": len(lines),
                       "lines": lines[:MENTION_LIMIT]})
    return script, review


def plan(mod, body: dict) -> RenamePlan:
    """Work out one rename. ``body`` is ``{subject, old, new}``."""
    p = RenamePlan(mod=mod, subject=str(body.get("subject") or "").strip(),
                   old=str(body.get("old") or "").strip(),
                   new=str(body.get("new") or "").strip())
    if p.subject not in SUBJECTS:
        p.errors.append(f"a rename is of {kb.and_list(list(SUBJECTS))}, "
                        f"not {p.subject!r}")
        return p
    try:
        _validate(p, _names(mod, p.subject))
        if p.errors:
            return p
        _plan_sites(p)
        if p.subject == "faction":
            _plan_modeldb(p)
            p.assets = art_moves(mod, p.old, p.new)
            for a in p.assets:
                p.changes.append(f"{a.src} -> {a.dst}"
                                 + (f" ({a.files} file(s))" if a.is_dir else ""))
        _scan_mentions(p)
    except (RenameError, campmap.MapError, OSError) as exc:
        p.errors.append(getattr(exc, "message", None) or str(exc))
        return p
    _notes(p)
    if not p.touched() and not p.errors:
        p.errors.append(
            f"nothing in {getattr(mod, 'name', '?')} names the {NOUN[p.subject]} "
            f"{p.old} in a place a rename knows how to follow")
    return p


def _notes(p: RenamePlan) -> None:
    """What the user has to be told before they press the button."""
    if p.script:
        files = sorted({m.rel for m in p.script})
        p.warnings.append(
            f"{len(p.script)} line(s) in {kb.and_list(files)} name {p.old} and "
            f"NONE of them is rewritten. A campaign script is a grammar nothing "
            f"here parses, and a wrong edit to one is a campaign that fails to "
            f"start - every line is listed above so it can be changed by hand")
    if p.review:
        p.notes.append(
            f"{sum(x['hits'] for x in p.review)} more line(s) across "
            f"{len(p.review)} file(s) write the word {p.old} and are left alone. "
            f"In a real mod most of those are something else with the same name - "
            f"a unit type, a sound folder, a comment beside a numeric ID - so they "
            f"are counted here for you to look at rather than rewritten")
    if p.subject == "region":
        p.notes.append(
            "Region IDs are unchanged. They are first-appearance order in a scan "
            "of map_regions.tga, and a rename moves no record and repaints no "
            "pixel, so every `IsRegionOneOf` operand still means what it did")
    if p.subject == "settlement":
        p.notes.append(
            "descr_strat.txt is not in this list and does not need to be: a "
            "settlement block names its province, never itself. Measured over "
            "both installed mods")
    if p.subject == "faction" and not p.assets:
        p.warnings.append(
            f"no art under {kb.and_list(list(ART_ROOTS))} is named after {p.old}, "
            f"so either this mod keeps its faction art somewhere else or the "
            f"faction has none - check the Factions screen's pictures tab")


# ---------------------------------------------------------------------------
# writing it


def apply(p: RenamePlan) -> Dict:
    """Write a planned rename, with the same backups and undo as any other job.

    **One backup set for all of it**, which is 18a's rule and the only defensible
    reading here: a rename half applied is a mod that will not load, so an undo
    that put back some of the files would be worse than one that put back none.

    An art folder **moves**: the source is backed up file by file and then
    deleted, and the destination is recorded as created, so
    :func:`unittransfer.transfer.undo` restores the one and removes the other.
    """
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.touched():
        raise ValueError("nothing to change")
    mod = p.mod
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        """Back a file up before it is written, or record that it is new - the
        two halves of what undo needs to put this mod back."""
        target = data / rel
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

    written: List[str] = []
    for edit in p.written():
        target = keep(edit.rel)
        kb.write_text(target, edit.text, edit.encoding)
        file_op("WRITE", target, f"{edit.count} line(s) renamed")
        written.append(edit.rel)
        # the {key}value files are compiled: the game reads the .bin, not the .txt
        if edit.rel.startswith("text/") and edit.rel.endswith(".txt"):
            keep(edit.rel + ".strings.bin")
            res = cleaner.refresh_strings_bin(mod.root, "data/" + edit.rel + ".strings.bin")
            if not res.get("rebuilt"):
                p.warnings.append(
                    f"{Path(edit.rel).name}.strings.bin could not be recompiled "
                    f"({res.get('rebuild_error') or 'no reason given'}), so it "
                    f"was deleted instead and the game rebuilds it on launch")

    moved = 0
    for a in p.assets:
        src, dst = data / a.src, data / a.dst
        if not src.exists() or dst.exists():
            continue
        pairs = ([(f, dst / f.relative_to(src)) for f in sorted(src.rglob("*"))
                  if f.is_file()] if a.is_dir else [(src, dst)])
        for one, other in pairs:
            rel = one.relative_to(data).as_posix()
            keep(rel)                                   # its bytes, for the undo
            other.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(one, other)
            manifest["created"].append(other.relative_to(data).as_posix())
            one.unlink()
            moved += 1
        file_op("MOVE", dst, f"<- {src} ({len(pairs)} file(s))")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "renames",
        "action": f"rename {p.subject}",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.new, "resolved_type": p.new,
        "options": {"subject": p.subject, "old": p.old},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("RENAME %s %s -> %s in %s - %d file(s), %d line(s), %d art file(s), id=%s",
             p.subject, p.old, p.new, mod.name, len(written), p.hits(), moved, tid)
    return {"id": tid, "subject": p.subject, "old": p.old, "new": p.new,
            "files": written, "hits": p.hits(), "asset_files": moved,
            "script": len(p.script), "notes": list(p.notes),
            "warnings": list(p.warnings), "record": rec}
