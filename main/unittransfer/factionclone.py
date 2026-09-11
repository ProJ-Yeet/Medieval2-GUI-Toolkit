"""Adding a faction by cloning one that already works.

:mod:`unittransfer.factions` edits the roster and says, at length, why it will
not create a slot: a faction lives in nine files at once and one that exists
only in ``descr_sm_factions.txt`` is a mod that will not load. That refusal was
right about the *problem* and wrong about the *conclusion* - the answer is not
to refuse, it is to do all the files. This module does twelve of them, and
names the three it will not touch rather than leaving them to be discovered.

**It clones rather than invents,** which is the whole reason it can be safe.
TWCenter's own step-by-step for this job (``Reference/TWCenter/Creating a world
- adding a new faction/adding_cloned_faction_steps.txt``) never writes a value
from scratch: every step is "find where the old faction is named and name the
new one too, with the same value". So there is no question of what colour, what
banner, what strat model or what unit roster the new faction gets - it gets the
donor's, everywhere, and the modder changes what they want afterwards in the
editors this toolkit already has. A clone that is a perfect copy under a new
name is a mod that loads, and a mod that loads is something you can then edit.

**What the donor's name is doing in each file is different every time**, which
is why this is a cloner per shape and not one search-and-replace:

* ``descr_sm_factions.txt`` - a whole record to copy and re-head.
* ``descr_names.txt`` - an indented ``faction: x`` section to copy.
* ``descr_lbc_db.txt`` - a ``faction x`` paragraph to copy.
* ``descr_offmap_models.txt`` - a braced ``faction x { … }`` block to copy.
* ``descr_character.txt`` and ``descr_sounds_accents.txt`` - a **shared list**:
  ``faction venice, sicily, milan`` names every faction that uses the block
  under it, so the clone joins the lists the donor is in rather than being given
  blocks of its own.
* ``export_descr_buildings.txt`` and ``descr_faction_standing.txt`` - the same
  idea inside braces, ``requires factions { sicily, }``. The EDB one is not
  optional: those clauses are what let a faction build and recruit at all, and
  one installed mod has 424 of them naming a single faction. The standing file
  spells its list **two ways** and which one a mod uses is the mod's own habit,
  so both are matched - see :func:`clone_braced_list`.
* ``descr_model_strat.txt`` - one ``texture <faction>, <path>`` line per faction
  per agent model, so each of the donor's is duplicated.
* ``export_descr_unit.txt`` - ``ownership`` lines, appended to, which is what
  gives the clone the donor's entire unit roster.
* ``battle_models.modeldb`` - texture records, which are length-prefixed and
  counted, so :func:`unittransfer.modeldb.add_texture_factions` does it: it
  already clones a donor record and fixes the group's count, and it is the same
  call the model card's faction checklist makes.
* ``text/expanded.txt`` - the shown name and the ~30 ``EMT_*`` keys, which are
  the donor's text with the donor's slot swapped out of the key.

**The art is found, not listed.** Every faction file in a real mod carries the
slot in its own name - ``symbol24_sicily_roll.tga``, ``faction_banner_sicily``,
``captain_card_sicily``, ``ui/units/sicily/`` - so the copier globs for the
donor's name as a *token* under the art roots and copies each hit to the same
path with the name swapped. A hardcoded list would have been wrong for every
mod that ships a folder vanilla does not, and mods do that constantly.

**Where the donor's name is a decision, it is reported, not cloned.** A trait
named after the faction, an ancillary's ``and FactionType sicily`` operand, a
prebattle speech - none of those is a list to join, and appending to them would
either invent a trait the engine has never heard of or silently rewrite a
boolean. :data:`REVIEW_FILES` is that list and :func:`review_mentions` counts
the hits, so the plan can say which other places name the donor instead of
letting them be discovered in a crash log.

**What it does not do, and says so.** ``descr_strat.txt`` is not cloned. A
faction's campaign entry is a region, a settlement, a starting army, a family
tree and map coordinates - the one part of this job with no correct answer to
copy, since two factions cannot start in the same settlement. The tutorial
treats it as its own step for the same reason. The clone is written, the mod
loads for custom battles, and the plan says in as many words that the campaign
needs a ``descr_strat`` entry before the faction will play. Same ruling as the
missing-picture one in :mod:`unittransfer.factions`: report the gap, do not
invent a value nobody can check.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import factions as fac
from . import flatrecord as fr
from . import keyblock as kb
from . import modeldb as mdb

ENCODING = fr.ENCODING

#: A faction slot is a bare word in every file that names one. Anything else in
#: a mod's own naming (a hyphen, a space) the engine would not read back.
SLOT_RE = re.compile(r"^[a-z][a-z0-9_]*$")

#: Reserved because the engine means something specific by them.
RESERVED: Tuple[str, ...] = ("slave", "merc", "mercs", "all")

CloneError = fr.RecordError


# ---------------------------------------------------------------------------
# the text files, one cloner each
#
# Every one takes the file's whole text plus the two slot names and hands back
# the new text and a count of what it touched. None of them ever writes a value
# the donor did not already have.


def _tok(name: str) -> str:
    """The donor's slot as a regex, bounded so ``sicily`` never matches
    ``sicily_clone`` - the single mistake that would corrupt every file here.

    Underscore counts as part of a word: in a data file a slot is a whole token,
    and ``sicily`` and ``sicily_clone`` are two different factions.
    """
    return r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"


def _key_tok(name: str) -> str:
    """The same, for a text KEY, where underscore separates words rather than
    belonging to one.

    ``{EMT_SICILY_ADMIRAL}`` is the slot ``sicily`` inside a key built by joining
    words with underscores, so here ``_`` is a boundary and only a letter or
    digit either side means "this is a longer word, leave it alone". Using the
    data-file boundary here finds the bare ``{SICILY}`` and none of the thirty
    ``EMT_`` keys, which is a faction whose every event message is missing.
    """
    return r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])"


def clone_roster(text: str, src: str, new: str) -> Tuple[str, int]:
    """``descr_sm_factions.txt``: the donor's record again, under the new head.

    Inserted straight after the donor so the file stays readable and a diff
    shows the pair together. The head keeps only the slot - a modifier like
    ``spawned_on_event`` is the donor's own campaign wiring and cloning it would
    hand the new faction an event it has no entry in.
    """
    rf = fac.parse_text(text)
    rec = rf.get(src) or next(
        (r for r in rf.records if fac.slot_of(r.name) == src), None)
    if rec is None:
        raise CloneError(f"{src} is not a faction in descr_sm_factions.txt")
    block = rf.block_text(rec)
    lines = block.split("\n")
    lines[0] = kb.sub_head(lines[0], "faction", new)
    return rf.replace(rec.end, rec.end, "\n".join(lines)), 1


def clone_paragraph(text: str, src: str, new: str, kw: str = "faction") -> Tuple[str, int]:
    """``descr_lbc_db.txt``: ``faction x`` and the indented run under it.

    The paragraph ends at the next line that starts the same keyword, or at the
    end of the file - blank lines are inside it, not terminators, because the
    real file separates its paragraphs with exactly one.
    """
    head = re.compile(r"^[ \t]*" + re.escape(kw) + r"[ \t]+" + _tok(src) + r"[ \t]*(;.*)?$",
                      re.M | re.I)
    # NOT `\b` after the keyword: `descr_names.txt` heads its sections with
    # `faction:`, and `\b` after a colon demands a word character next, so it
    # never matched the space that is really there - the paragraph then ran to
    # the end of the file and cloned 10,000 lines of every other faction's names.
    nxt = re.compile(r"^[ \t]*" + re.escape(kw) + r"(?![A-Za-z0-9_])", re.M | re.I)
    m = head.search(text)
    if not m:
        return text, 0
    after = nxt.search(text, m.end())
    end = after.start() if after else len(text)
    body = text[m.start():end].rstrip("\r\n")
    clone = re.sub(_tok(src), new, body, count=1, flags=re.I)
    nl = kb.newline_of(text)
    return text[:end] + clone + nl + nl + text[end:], 1


def clone_braced(text: str, src: str, new: str) -> Tuple[str, int]:
    """``descr_offmap_models.txt``: every ``faction x { … }`` block, duplicated.

    The donor may have one per section (a navy block, and whatever else a mod
    has added), so all of them are cloned, each just after its own original.
    Brace counting rather than indentation: the file nests.
    """
    pat = re.compile(r"^([ \t]*)faction[ \t]+" + _tok(src) + r"[ \t]*(;[^\n]*)?$",
                     re.M | re.I)
    out, done, pos = [], 0, 0
    for m in pat.finditer(text):
        brace = text.find("{", m.end())
        if brace < 0:
            continue
        depth, i = 0, brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            continue                       # unbalanced: leave the file alone
        end = i + 1
        block = text[m.start():end]
        clone = re.sub(_tok(src), new, block, count=1, flags=re.I)
        nl = kb.newline_of(text)
        out.append(text[pos:end] + nl + nl + clone)
        pos, done = end, done + 1
    out.append(text[pos:])
    return "".join(out), done


def clone_list_lines(text: str, src: str, new: str, kw: str) -> Tuple[str, int]:
    """A keyword whose value is a comma list of factions - append the clone.

    ``descr_character.txt``'s ``faction venice, sicily, milan`` and the EDU's
    ``ownership`` are the same shape and the same rule: the block underneath is
    shared by everyone named on the line, so the clone joins the line rather
    than getting a block of its own. A line that already names the clone is left
    alone, which is what makes a re-run safe.
    """
    pat = re.compile(r"^([ \t]*" + re.escape(kw) + r"[ \t]+)([^\n;]*)(;[^\n]*)?$",
                     re.M | re.I)
    done = 0

    def fix(m):
        nonlocal done
        head, value, comment = m.group(1), m.group(2), m.group(3) or ""
        names = [t.strip() for t in value.split(",")]
        low = {n.lower() for n in names if n}
        if src not in low or new in low:
            return m.group(0)
        done += 1
        # The file's own spacing after a comma, so the line still reads like its
        # neighbours. A line with only ONE faction on it has no comma to copy the
        # style from, and every real file writes `a, b` rather than `a,b` - so
        # the tight form is used only when the line itself demonstrates it.
        sep = "," if ("," in value and ", " not in value) else ", "
        return head + value.rstrip() + sep + new + comment

    return pat.sub(fix, text), done


def clone_braced_list(text: str, src: str, new: str,
                      kw=("factions",)) -> Tuple[str, int]:
    """A brace-delimited faction list - join it, the way a comma list is joined.

    ``export_descr_buildings.txt`` is the one that matters: every recruitment and
    construction line is gated by ``requires factions { sicily, }``, so a clone
    that does not join those clauses is a faction that can build nothing and
    recruit nobody - which is most of what a faction *is*. 424 clauses in one
    installed mod name a single faction.

    ``descr_faction_standing.txt``'s ``exclude_factions { … }`` is the same
    shape and gets the same treatment, including where the list is an exclusion:
    the clone is supposed to behave exactly like the donor, so it belongs
    wherever the donor is named, on whichever side of the rule that puts it.

    The file's own trailing comma is kept - ``{ sicily, }`` becomes
    ``{ sicily, x, }`` and ``{ sicily }`` becomes ``{ sicily, x }`` - because
    both spellings are in the real files and neither is ours to normalise.

    ``kw`` is a *set* of keywords, because ``descr_faction_standing.txt`` uses
    both ``factions { … }`` and ``exclude_factions { … }`` and which one it
    prefers is per mod: Third Age Reforged writes 96 of the first and 20 of the
    second, Divide and Conquer writes 164 of the first and none of the second.
    Handling only ``exclude_factions`` would have cloned nothing at all in one
    of the two installed mods. The lookbehind keeps them apart - inside
    ``exclude_factions`` the bare ``factions`` is preceded by ``_`` and does not
    match - so the alternation needs no ordering.
    """
    names = (kw,) if isinstance(kw, str) else tuple(kw)
    pat = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(k) for k in names)
                     + r")([ \t]*\{)([^{}]*)(\})", re.I)
    done = 0

    def fix(m):
        nonlocal done
        body = m.group(3)
        listed = {t.strip().lower() for t in body.split(",") if t.strip()}
        if src not in listed or new in listed:
            return m.group(0)
        done += 1
        stripped = body.rstrip()
        gap = body[len(stripped):]              # the space before the brace
        add = (" " + new + ",") if stripped.endswith(",") else (", " + new)
        return m.group(1) + m.group(2) + stripped + add + (gap or " ") + m.group(4)

    return pat.sub(fix, text), done


def clone_texture_lines(text: str, src: str, new: str) -> Tuple[str, int]:
    """``descr_model_strat.txt``: ``texture <faction>, <path>``, duplicated.

    One line per faction per agent model, and the clone gets the donor's path -
    the same art, which is exactly what a clone should look like until somebody
    paints it something else.
    """
    pat = re.compile(r"^([ \t]*texture[ \t]+)" + _tok(src) + r"([ \t]*,[^\n]*)$",
                     re.M | re.I)
    done = 0
    have = re.compile(r"^[ \t]*texture[ \t]+" + _tok(new) + r"[ \t]*,", re.M | re.I)

    def fix(m):
        nonlocal done
        done += 1
        nl = kb.newline_of(text)
        return m.group(0) + nl + m.group(1) + new + m.group(2)

    if have.search(text):
        return text, 0                     # already cloned once; do not double it
    return pat.sub(fix, text), done


def clone_names(text: str, src: str, new: str) -> Tuple[str, int]:
    """``descr_names.txt``: the donor's ``faction: x`` section, copied whole.

    The section is indented under its head and runs to the next ``faction:``,
    carrying the ``characters`` / ``surnames`` / ``women`` sub-lists with it.
    The tutorial says to paste it into an empty file and check it before putting
    it back; doing it by span means there is nothing to check.
    """
    return clone_paragraph(text, src, new, kw="faction:")


def clone_expanded(text: str, src: str, new: str, label: str = "") -> Tuple[str, int]:
    """``text/expanded.txt``: the shown name and every ``EMT_*`` key.

    A faction's text keys are its slot in UPPER CASE inside a brace - ``{SICILY}``,
    ``{EMT_SICILY_SPY}``, ``{EMT_VICTORY_SICILY}`` - so the donor's whole family
    is found by the slot appearing as a token inside the key, wherever in the key
    it sits (the ``VICTORY_SICILY`` ones put it last). The *value* is copied
    unchanged, so the clone reads as the donor everywhere, EXCEPT the bare
    ``{NEW}`` key when a ``label`` is given: that one is the faction's shown name
    and it is the one thing worth being asked at creation, since a roster with
    two factions both called "Gondor" is unusable the moment it loads. The other
    thirty keys stay the donor's until they are edited - ``{EMT_X_SPY}`` is a
    sentence, not a name, and guessing at thirty of them from one word would put
    text in the game nobody wrote.
    """
    up_s, up_n = src.upper(), new.upper()
    shown = str(label or "").strip()
    key = re.compile(r"^([ \t]*\{)([A-Z0-9_]*" + re.escape(up_s) + r"[A-Z0-9_]*)(\}[^\n]*)$",
                     re.M)
    tok = re.compile(_key_tok(up_s))
    seen, adds = set(), []
    for m in key.finditer(text):
        name = m.group(2)
        if not tok.search(name):
            continue                       # SICILY inside a longer word, not the slot
        made = tok.sub(up_n, name)
        if made == name or made in seen:
            continue
        seen.add(made)
        tail = m.group(3)
        if shown and made == up_n:
            # the shown name, and only it: keep the file's own separator between
            # the key and its value so the column still lines up
            gap = re.match(r"\}([ \t]*)", tail)
            tail = "}" + (gap.group(1) if gap else "\t") + shown
        adds.append(m.group(1) + made + tail)
    if not adds:
        return text, 0
    # anything already there is the file's, not ours to duplicate
    present = set(re.findall(r"^[ \t]*\{([A-Z0-9_]+)\}", text, re.M))
    adds = [a for a in adds if re.search(r"\{([A-Z0-9_]+)\}", a).group(1) not in present]
    if not adds:
        return text, 0
    nl = kb.newline_of(text)
    return text.rstrip("\r\n") + nl + nl + nl.join(adds) + nl, len(adds)


def clone_modeldb(text: str, src: str, new: str) -> Tuple[str, int]:
    """``battle_models.modeldb``: a texture record for the clone in every entry
    the donor has one in.

    Per ENTRY, because :func:`unittransfer.modeldb.add_texture_factions` reads
    ONE entry's raw text - handed the whole file it finds no texture groups and
    silently changes nothing, which is a clone with no skins and no error to say
    so. With the donor as ``prefer`` the clone inherits the donor's texture,
    normal and sprite paths rather than whichever record happened to be first,
    and that function rewrites each group's length-prefixed count, which is the
    part of this file nobody can maintain by hand.

    Only entries the donor really has a record in are touched: a model it does
    not use has nothing worth copying, and giving the clone a skin there would
    be inventing one. ``to_text`` re-emits the header byte-for-byte while the
    entry count is unchanged, and adding a texture record never changes it.
    """
    db = mdb.parse_text(text)
    done = 0
    for e in db.entries:
        if not any(t.faction.lower() == src for t in e.main_textures):
            continue
        raw = mdb.add_texture_factions(e.raw, [new], prefer=src,
                                       pad=e.first_entry_pad)
        if raw != e.raw:
            e.raw = raw
            done += 1
    return (db.to_text() if done else text), done


# ---------------------------------------------------------------------------
# what gets cloned, in the order the plan reports it


@dataclass(frozen=True)
class Job:
    rel: str
    label: str
    how: str                       # which cloner above
    #: the keyword(s) the cloner looks for. A tuple where one file spells the
    #: same list two ways - see `clone_braced_list`.
    kw: object = ""
    required: bool = False
    encoding: str = ENCODING
    note: str = ""


JOBS: Tuple[Job, ...] = (
    Job(fac.REL, "Faction roster", "roster", required=True,
        note="the new slot itself: culture, religion, colours, banners"),
    Job("text/expanded.txt", "Faction name and event text", "expanded",
        encoding="utf-16",
        note="the shown name and the ~30 EMT_* keys that go with it"),
    Job("export_descr_unit.txt", "Unit roster ownership", "list", kw="ownership",
        note="every unit the donor may recruit, the clone may recruit"),
    Job("unit_models/battle_models.modeldb", "Battle model skins", "modeldb",
        note="a texture record per model, cloned from the donor's"),
    Job("export_descr_buildings.txt", "Recruitment and construction", "braced_list",
        kw=("factions",),
        note="every `requires factions { … }` that lets the donor build or recruit"),
    Job("descr_character.txt", "Agents and generals", "list", kw="faction",
        note="which character types the faction may field"),
    Job("descr_sounds_accents.txt", "Voice accent", "list", kw="factions",
        note="the accent its characters speak with"),
    Job("descr_faction_standing.txt", "Diplomatic standing", "braced_list",
        kw=("factions", "exclude_factions"),
        note="the standing rules the donor is named in, on either side"),
    Job("descr_model_strat.txt", "Campaign map models", "texture",
        note="the strat-map art for each agent type"),
    Job("descr_names.txt", "Character names", "names",
        note="the name pool its characters are drawn from"),
    Job("descr_lbc_db.txt", "Settlement populace", "paragraph", kw="faction",
        note="the civilian models that walk its streets"),
    Job("descr_offmap_models.txt", "Off-map navy models", "braced",
        note="the ships shown at the edge of the map"),
)

#: Where a mod keeps art the engine finds BY CONVENTION - from the faction's own
#: name, with nothing pointing at it: ``ui/units/<faction>/``, ``symbol24_<faction>``,
#: ``faction_banner_<faction>``, ``captain_card_<faction>``. That art has to be
#: copied and renamed or the clone has none.
#:
#: Deliberately NOT here: ``models_strat/textures``, ``models_building/textures``
#: and ``loading_screen``. Those are named by a *line* - ``texture sicily,
#: models_strat/textures/spy_gondor.tga``, the roster's ``loading_logo`` - and
#: the clone's own copies of those lines already point at the donor's file, which
#: is what the tutorial has them do. Copying and renaming them would leave a
#: duplicate that nothing in the mod refers to.
ART_ROOTS: Tuple[str, ...] = ("ui", "menu", "banners")

#: Files whose faction mentions are NOT a list to join, so they are reported
#: rather than cloned. Each names the donor in a way that needs a decision:
#:
#: * ``export_descr_character_traits.txt`` - traits named *after* the faction
#:   (``Trait Fearssicily``) and engine effect names (``Combat_V_Faction_Sicily``).
#:   Cloning would mean inventing whole new traits and an effect the engine has
#:   never heard of.
#: * ``export_descr_ancillaries.txt`` - ``and FactionType sicily`` is one operand
#:   of a boolean condition. Adding the clone means rewriting the expression's
#:   logic, not appending to a list, and getting that wrong silently changes
#:   which characters an ancillary can reach.
#: * ``export_descr_sounds_prebattle.txt`` / ``descr_missions.txt`` /
#:   ``descr_sounds_music.txt`` - per-faction blocks whose contents are a
#:   judgement (which speech, which mission, which theme).
#:
#: The Traits and Ancillaries editors already open all of these, which is where
#: the decision belongs.
REVIEW_FILES: Tuple[str, ...] = (
    "export_descr_character_traits.txt", "export_descr_ancillaries.txt",
    "export_descr_sounds_prebattle.txt", "descr_missions.txt",
    "descr_sounds_music.txt", "descr_win_conditions.txt", "descr_banners.txt")

#: the campaign file this deliberately leaves alone, and why
STRAT_REL = "world/maps/campaign/imperial_campaign/descr_strat.txt"
STRAT_NOTE = (
    "The campaign start position is NOT cloned. A faction's descr_strat entry is "
    "a region, a settlement, a starting army, a family tree and map coordinates - "
    "and two factions cannot begin in the same settlement, so there is nothing "
    "here that can be copied and still be right. The clone will load, appear in "
    "custom battles and own its units; give it a settlement in descr_strat.txt "
    "before expecting it in the campaign.")


# ---------------------------------------------------------------------------
# the plan


@dataclass
class AssetCopy:
    src: str                       # relative to data/
    dst: str
    is_dir: bool = False
    files: int = 0
    bytes: int = 0


@dataclass
class FileEdit:
    rel: str
    label: str
    text: str = ""                 # the whole new file; "" means unchanged
    encoding: str = ENCODING
    count: int = 0
    note: str = ""
    skipped: str = ""              # why it did nothing, when it did nothing


@dataclass
class ClonePlan:
    mod: object = None
    source: str = ""
    new: str = ""
    #: ``clone`` makes a new slot; ``repair`` (21, D6, :mod:`factionaudit`)
    #: copies only the missing records into a slot that already exists. Same
    #: cloners, same write, same undo - only the log line and its wording differ.
    action: str = "clone"
    edits: List[FileEdit] = field(default_factory=list)
    assets: List[AssetCopy] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    review: List[Dict] = field(default_factory=list)

    def written(self) -> List[FileEdit]:
        return [e for e in self.edits if e.text]

    def touched(self) -> bool:
        return bool(self.written() or self.assets)

    def summary(self) -> str:
        what = (f"repair faction {self.new} from {self.source}"
                if self.action == "repair"
                else f"clone faction {self.source} -> {self.new}")
        head = (f"{what} in {getattr(self.mod, 'name', '?')} "
                f"({len(self.written())} file(s), {len(self.assets)} art item(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {
            "action": self.action, "source": self.source, "new": self.new,
            "files": [{"rel": e.rel, "label": e.label, "count": e.count,
                       "note": e.note, "skipped": e.skipped, "written": bool(e.text)}
                      for e in self.edits],
            "assets": [{"src": a.src, "dst": a.dst, "dir": a.is_dir,
                        "files": a.files, "bytes": a.bytes} for a in self.assets],
            "asset_files": sum(a.files for a in self.assets),
            "asset_bytes": sum(a.bytes for a in self.assets),
            "changes": list(self.changes), "warnings": list(self.warnings),
            "errors": list(self.errors), "notes": list(self.notes),
            "review": list(self.review),
            "ok": not self.errors and self.touched(),
        }


def _validate(mod, src: str, new: str, p: ClonePlan) -> Optional[fr.RecordFile]:
    """Everything that can be wrong before a byte is planned."""
    path = fac.path_for(mod)
    if not path.is_file():
        p.errors.append(f"{getattr(mod, 'name', '?')} has no {fac.REL}")
        return None
    rf = fac.parse_file(path)
    slots = {fac.slot_of(r.name) for r in rf.records}
    if src not in slots:
        p.errors.append(f"{src} is not a faction in this mod")
    if not new:
        p.errors.append("the new faction needs a name")
    elif not SLOT_RE.match(new):
        p.errors.append(
            f"`{new}` cannot be a faction slot - it has to start with a letter and "
            "hold only lower-case letters, digits and underscores, because every "
            "file that names a faction reads it as one bare word")
    elif new in slots:
        p.errors.append(f"{new} is already a faction in this mod")
    elif new in RESERVED:
        p.errors.append(f"`{new}` is reserved - the engine means something specific by it")
    if new and new == src:
        p.errors.append("the clone needs a different name from the faction it copies")
    # the cap is the engine's, and an M2EX mod has replaced the table it came from
    limit = 0 if getattr(mod, "m2ex", False) else fac.FACTION_LIMIT
    if limit and len(rf.records) >= limit:
        p.errors.append(
            f"this mod already has {len(rf.records)} of the engine's {limit} faction "
            "slots - one has to go before another can be added")
    elif limit and len(rf.records) + 1 == limit:
        p.warnings.append(f"this uses the last of the engine's {limit} faction slots")
    return rf


def _asset_hits(mod, src: str, new: str, slots=()) -> List[AssetCopy]:
    """Every file and folder under the art roots whose name carries the donor's
    slot, paired with where its copy goes.

    A folder is taken whole and its contents are not walked again, so
    ``ui/units/sicily`` is one item rather than fifty-eight. Found rather than
    listed: see the module docstring.

    In a *filename* underscore is the separator, not part of the word -
    ``symbol24_sicily_grey.tga`` is the slot ``sicily`` - so this uses the key
    boundary, not the data-file one. Which then raises the problem the data
    files do not have: ``sicily`` also sits inside ``symbol24_sicily_clone.tga``,
    art that belongs to a *different* faction. So the winner is the LONGEST slot
    in the roster that the name carries, and the file is only taken when that
    winner is the donor. Without it, cloning `sicily` in a mod that also has
    `sicily_clone` quietly copies the other faction's banners too.
    """
    data = Path(mod.data)
    tok = re.compile(_key_tok(src), re.I)
    rivals = sorted((s for s in slots if s != src and tok.search(s)),
                    key=len, reverse=True)
    rival_res = [(s, re.compile(_key_tok(s), re.I)) for s in rivals]
    out: List[AssetCopy] = []
    for root in ART_ROOTS:
        base = data / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            name = path.name
            if not tok.search(name):
                continue
            # a longer slot matching the same name owns this file, not the donor
            if any(len(s) > len(src) and rx.search(name) for s, rx in rival_res):
                continue
            rel = path.relative_to(data).as_posix()
            # inside a folder already being copied whole - it comes along
            if any(rel.startswith(a.src + "/") for a in out):
                continue
            # `SICILY_KING_EVENT.tga` should become `GONDOR_SOUTH_KING_EVENT.tga`,
            # not `gondor_south_KING_EVENT.tga` - a mod that shouts its filenames
            # keeps shouting them
            def swap(m, _new=new):
                hit = m.group(0)
                return _new.upper() if hit.isupper() else _new
            dst = (path.parent.relative_to(data) / tok.sub(swap, name)).as_posix()
            if (data / dst).exists():
                continue                   # the mod already ships it; never overwrite
            if path.is_dir():
                files = [f for f in path.rglob("*") if f.is_file()]
                out.append(AssetCopy(rel, dst, True, len(files),
                                     sum(f.stat().st_size for f in files)))
            elif path.is_file():
                out.append(AssetCopy(rel, dst, False, 1, path.stat().st_size))
    return out


#: {(data folder, donor): [{"rel", "hits"}]} - the review scan reads a dozen
#: multi-megabyte files, and the dialog re-plans on every keystroke.
_MENTIONS: Dict[Tuple[str, str], List[Dict]] = {}


def review_mentions(mod, src: str) -> List[Dict]:
    """Which of :data:`REVIEW_FILES` name the donor, and how often.

    Reported so the gap is visible rather than silent: the clone will load and
    play without these, but it will not inherit the donor's traits, ancillary
    conditions or prebattle speeches, and only a person can say what it should
    have instead.
    """
    data = Path(mod.data)
    key = (str(data), src)
    if key in _MENTIONS:
        return _MENTIONS[key]
    tok = re.compile(_tok(src), re.I)
    out: List[Dict] = []
    for rel in REVIEW_FILES:
        path = data / rel
        if not path.is_file():
            continue
        try:
            hits = len(tok.findall(kb.read_text(path, ENCODING)))
        except (OSError, UnicodeError):
            continue
        if hits:
            out.append({"rel": rel, "hits": hits})
    _MENTIONS[key] = out
    return out


def clone_file(data: Path, job: Job, src: str, new: str, label: str = "") -> FileEdit:
    """One job's cloner run over one file: the new text, or why there is none.

    Shared by the clone and by 21's repair (:mod:`unittransfer.factionaudit`),
    which runs the same cloner for a slot that already exists and is missing
    only this file's record. Never raises; an unreadable file comes back with
    ``skipped`` saying so.
    """
    path = data / job.rel
    if not path.is_file():
        return FileEdit(job.rel, job.label, note=job.note,
                        skipped="this mod has no such file")
    try:
        original = kb.read_text(path, job.encoding)
        # Every cloner below anchors on `$`, and in a CRLF file `$` sits
        # AFTER the carriage return - so `[ \t]*$` never reaches the end of
        # a line and the paragraph, braced and names cloners all match
        # nothing, while the list and texture ones match but eat the `\r`
        # and leave the file with mixed endings. Measured, not guessed: the
        # real game files are CRLF and three of the cloners silently did
        # nothing until this was put in. So the cloners see `\n` throughout
        # and the file gets its own ending back at the end.
        # The modeldb is exempt: its strings are length-prefixed and it is
        # rebuilt by its own writer, so nothing here should touch its bytes.
        flat = job.how != "modeldb"
        newline = kb.newline_of(original)
        before = kb.to_newline(original, "\n") if flat else original
        if job.how == "roster":
            after, n = clone_roster(before, src, new)
        elif job.how == "expanded":
            after, n = clone_expanded(before, src, new, label)
        elif job.how == "list":
            after, n = clone_list_lines(before, src, new, job.kw)
        elif job.how == "braced_list":
            after, n = clone_braced_list(before, src, new, job.kw)
        elif job.how == "texture":
            after, n = clone_texture_lines(before, src, new)
        elif job.how == "names":
            after, n = clone_names(before, src, new)
        elif job.how == "paragraph":
            after, n = clone_paragraph(before, src, new, job.kw)
        elif job.how == "braced":
            after, n = clone_braced(before, src, new)
        elif job.how == "modeldb":
            after, n = clone_modeldb(before, src, new)
        else:                                     # unreachable
            after, n = before, 0
    except (fr.RecordError, ValueError, OSError, UnicodeError) as e:
        return FileEdit(job.rel, job.label, note=job.note,
                        skipped=f"could not be read: {e}")
    edit = FileEdit(job.rel, job.label, encoding=job.encoding, note=job.note,
                    count=n)
    if n and after != before:
        edit.text = kb.to_newline(after, newline) if flat else after
    else:
        edit.skipped = f"{src} is not named in it"
    return edit


def plan(mod, body: dict) -> ClonePlan:
    """Work out every file and every copy, without touching the disk."""
    src = str(body.get("source") or "").strip().lower()
    new = str(body.get("new") or body.get("faction") or "").strip().lower()
    p = ClonePlan(mod=mod, source=src, new=new)
    rf = _validate(mod, src, new, p)
    if rf is None or p.errors:
        return p
    slots = sorted({fac.slot_of(r.name) for r in rf.records})

    label = str(body.get("label") or "").strip()
    # Art is the one part a modder may genuinely not want copied - they may be
    # drawing their own. The twelve FILES are all or nothing: a roster naming a
    # slot the EDU and the modeldb have never heard of is not a faction, it is a
    # crash, so there is no per-file opt-out here to get wrong.
    want_art = bool(body.get("art", True))
    data = Path(mod.data)

    for job in JOBS:
        edit = clone_file(data, job, src, new, label)
        p.edits.append(edit)
        if edit.skipped and job.required and not edit.count:
            if not (data / job.rel).is_file():
                p.errors.append(f"{getattr(mod, 'name', '?')} has no {job.rel}")
            elif edit.skipped.startswith("could not be read"):
                p.errors.append(f"{job.rel}: {edit.skipped}")
        if edit.text:
            p.changes.append(f"{job.label} ({Path(job.rel).name}) - {edit.count} "
                             + ("entry" if edit.count == 1 else "entries"))

    if want_art:
        p.assets = _asset_hits(mod, src, new, slots)
        if p.assets:
            n = sum(a.files for a in p.assets)
            p.changes.append(f"{len(p.assets)} art item(s), {n} file(s), copied "
                             f"from {src}'s and renamed")
        else:
            p.warnings.append(
                f"no art was found carrying `{src}` in its name - the clone will "
                "fall back to whatever the engine shows for a faction with no "
                "symbol, banner or unit cards of its own")

    # The files themselves are in `review`, so the note explains rather than
    # re-lists them: the dialog draws both, and saying it twice reads as noise.
    p.review = review_mentions(mod, src)
    if p.review:
        p.notes.append(
            f"Some files name {src} in a way that is a decision rather than a "
            "list, and those are left for you. A trait named after the faction, "
            "an ancillary's `FactionType` condition and a prebattle speech "
            "cannot be cloned by appending to them - the Traits and Ancillaries "
            "editors open all three.")
    p.notes.append(STRAT_NOTE)
    if not (data / STRAT_REL).is_file():
        p.notes.append("This mod has no descr_strat.txt where one is expected "
                       f"({STRAT_REL}), so nothing here was checked against it.")
    if not p.touched() and not p.errors:
        p.errors.append(f"nothing in this mod names `{src}`, so there is nothing to clone")
    return p


# ---------------------------------------------------------------------------
# apply


def apply(p: ClonePlan) -> Dict:
    """Write a planned clone, with the same backups and undo as any other job."""
    import time

    from . import cleaner, config, stringsbin
    from .logutil import file_op, log

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
        file_op("WRITE", target, f"{len(edit.text)} bytes")
        written.append(edit.rel)
        # expanded.txt is compiled: the game reads the .bin, not the .txt
        if edit.rel.endswith(".txt") and edit.rel.startswith("text/"):
            keep(edit.rel + ".strings.bin")
            cleaner.refresh_strings_bin(mod.root, "data/" + edit.rel + ".strings.bin")

    # Copied art goes into the manifest ONE FILE AT A TIME, never as a folder.
    # `transfer.undo` removes a created path with `Path.unlink()`, which raises
    # on a directory and is swallowed - so a folder listed here would survive the
    # undo and leave the clone's unit cards behind after the faction itself was
    # taken back out. Listing the files means undo removes every one of them.
    # (The now-empty folders stay, which undo does everywhere else too.)
    copied_files = 0
    for a in p.assets:
        src_path, dst_path = data / a.src, data / a.dst
        if not src_path.exists() or dst_path.exists():
            continue
        pairs = ([(f, dst_path / f.relative_to(src_path)) for f in sorted(src_path.rglob("*"))
                  if f.is_file()] if a.is_dir else [(src_path, dst_path)])
        for src_file, dst_file in pairs:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            manifest["created"].append(dst_file.relative_to(data).as_posix())
            copied_files += 1
        file_op("COPY", dst_path, f"<- {src_path} ({len(pairs)} file(s))")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "factions",
        "action": p.action,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.new, "resolved_type": p.new,
        "options": ({"template": p.source} if p.action == "repair"
                    else {"cloned_from": p.source}),
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("FACTION %s %s -> %s in %s - %d file(s), %d art file(s), id=%s",
             p.action, p.source, p.new, mod.name, len(written), copied_files, tid)
    return {"id": tid, "faction": p.new, "source": p.source,
            "files": written, "asset_files": copied_files,
            "notes": list(p.notes), "record": rec}
