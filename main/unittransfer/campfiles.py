"""The campaign folder's three small files: descriptions, movies and mercenaries.

Phase 18a. Three of the four items it closes are campaign facts, and putting
them in one module is not tidiness - it is that all three are answers to "what
does this campaign say about this faction, or this province", and each one on
its own is fifty lines of code and a screen nobody would open twice.

**M5 - what the campaign calls itself.** ``data/text/campaign_descriptions.txt``,
the title and the blurb the new-game menu shows, per campaign and per faction.
The keys are built rather than listed::

    {IMPERIAL_CAMPAIGN_TITLE}Grand Campaign
    {IMPERIAL_CAMPAIGN_SICILY_TITLE}Gondor
    {IMPERIAL_CAMPAIGN_SICILY_DESCR}King Eldacar\\n\\n\\n\\nGondor, the mighty …

- the campaign token is its folder name, upper-cased: ``imperial_campaign`` ->
  ``IMPERIAL_CAMPAIGN``, ``Fellowship_Campaign`` -> ``FELLOWSHIP_CAMPAIGN``
- the faction token is the faction's own name, upper-cased

Measured across both installed mods, every one of the 230 keys in the two files
fits that pattern and the only two suffixes are ``_TITLE`` and ``_DESCR``.
``REFERENCE_GAPS.md`` also promises "victory text" here; there is none in this
file in either mod, and the campaign's victory terms are ``descr_win_conditions``
which 16j-2 already writes.

**M6 - ``descr_faction_movies.xml``.** The roadmap calls it a ``.txt``; it is
XML, and it is in the campaign folder rather than under ``data/``. Both installed
mods have one - Third Age Reforged declares one faction, Divide and Conquer ships
the empty shell - and neither has a trailing newline, which is the whole reason
this is a line splice and not a serialiser: the reference tool's
``serializeFactionMovies`` rebuilds the file from its own model and would rewrite
both of them on the first save of either.

**G3 - the region's mercenary pool.** ``descr_mercenaries.txt`` groups provinces
into pools and sells a different roster in each. 16b read it -
:func:`unittransfer.mapquery.parse_mercenaries` is the one parser and is used
here rather than copied - and the UI has been deferred ever since. What was
missing was the write, and the write is one word moved from one ``regions`` line
to another. Measured: 57 pools over 193 provinces in Divide and Conquer and 27
over 148 in Third Age Reforged, and **not one province is in two pools**, which
is what lets the picker be a single choice rather than a set of tick boxes.

**One rule governs all three.** These files are hand-aligned, comment-banked and
in one case not even newline-terminated, so every edit is a splice against the
file as read and ``parse_*(t).text() == t`` is the gate on each one, exactly as
in every editor since Phase 8.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campstrat, keyblock as kb, mapquery, stringsbin
from .triggers import split_lines

#: the campaign files are plain 8-bit text; the localisation file is UTF-16
ENCODING = "latin-1"
LOC_ENCODING = "utf-16"

CAMPAIGN_DIR_REL = campstrat.CAMPAIGN_DIR_REL
DEFAULT_CAMPAIGN = campstrat.DEFAULT_CAMPAIGN

#: M6, in the campaign folder
MOVIES_NAME = "descr_faction_movies.xml"

#: G3, in the campaign folder. The name comes from the module that reads it.
MERCS_NAME = mapquery.MERCS_NAME

#: M5, under ``data/``
DESCR_REL = "text/campaign_descriptions.txt"
DESCR_BIN_REL = "data/" + DESCR_REL + ".strings.bin"

#: the two suffixes the description file uses, and nothing else in either mod
DESCR_KINDS = ("TITLE", "DESCR")

#: the movie slots one ``<faction>`` block can carry, in the order real files
#: write them. ``intro`` is absent from Third Age Reforged's only block, so a
#: slot that is not there is a line to add rather than a line to blank.
MOVIE_SLOTS = ("intro", "victory", "defeat", "death")

#: movie paths in that file are relative to this folder
FMV_REL = "fmv"


class CampFileError(kb.BlockError):
    """The file is not there, or an edit would write one the engine cannot read."""


def campaign_dir(mod, campaign: str = DEFAULT_CAMPAIGN) -> Path:
    return Path(mod.data) / CAMPAIGN_DIR_REL / campaign


def campaigns(mod) -> List[str]:
    """Every campaign folder with a ``descr_strat.txt`` - campstrat's own list."""
    return campstrat.campaigns(mod)


# ---------------------------------------------------------------------------
# M5 - campaign_descriptions.txt


def descr_token(campaign: str) -> str:
    """``imperial_campaign`` -> ``IMPERIAL_CAMPAIGN``. The whole key rule."""
    return campaign.strip().upper()


def descr_key(campaign: str, faction: str, kind: str) -> str:
    """The key one box writes. ``faction`` empty means the campaign's own title."""
    head = descr_token(campaign)
    if not faction:
        return f"{head}_{kind}"
    return f"{head}_{faction.strip().upper()}_{kind}"


def descr_path(mod) -> Path:
    return Path(mod.data) / DESCR_REL


def descr_pairs(mod) -> Dict[str, str]:
    """Every key in the description file, read from the ``.txt`` or the ``.bin``.

    The ``.txt`` first and the compiled archive as the fallback, because a
    released mod very often ships only the archive - the same two roads
    :func:`unittransfer.modfiles.campaign_title` already takes.
    """
    txt = descr_path(mod)
    if txt.exists():
        try:
            return dict(stringsbin.from_txt(
                txt.read_text(encoding=stringsbin.TXT_ENCODING)))
        except (OSError, UnicodeError):
            pass
    return stringsbin.load_pairs(stringsbin.bin_path_for(txt))


def descr_view(mod, campaign: str = DEFAULT_CAMPAIGN) -> Dict:
    """The description screen: the campaign's own title, then one row a faction.

    A faction with neither key is still a row. It is the case the screen exists
    for - a faction added to a campaign and never given a name on the menu shows
    as its code name in game, and there is nothing on disk to grep for.
    """
    pairs = descr_pairs(mod)
    have = descr_path(mod).exists()
    rows = []
    for name in campaign_factions(mod, campaign):
        row = {"faction": name}
        for kind in DESCR_KINDS:
            key = descr_key(campaign, name, kind)
            row[kind.lower()] = pairs.get(key, "")
            row[kind.lower() + "_key"] = key
            row[kind.lower() + "_set"] = key in pairs
        rows.append(row)
    title_key = descr_key(campaign, "", "TITLE")
    return {
        "campaign": campaign,
        "file": DESCR_REL if have else DESCR_REL + ".strings.bin",
        "have_txt": have,
        "title": pairs.get(title_key, ""),
        "title_key": title_key,
        "title_set": title_key in pairs,
        "rows": rows,
        "keys": len(pairs),
    }


def campaign_factions(mod, campaign: str = DEFAULT_CAMPAIGN) -> List[str]:
    """Every faction with a block in that campaign's ``descr_strat.txt``.

    The campaign's own list rather than the mod's, because a description key is
    only ever read for a faction that campaign actually starts.
    """
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError):
        return []
    seen: List[str] = []
    for node in sf.of_kind("faction"):
        if node.name and node.name not in seen:
            seen.append(node.name)
    return seen


# ---------------------------------------------------------------------------
# M6 - descr_faction_movies.xml


_TAG = re.compile(r"<\s*(/?)\s*([A-Za-z_][\w-]*)\s*>")
_VALUE = re.compile(r"<\s*([A-Za-z_][\w-]*)\s*>(.*?)<\s*/\s*\1\s*>")


@dataclass
class MovieRecord:
    """One ``<faction>`` block: its name and the movie slots it fills."""

    faction: str = ""
    values: Dict[str, str] = field(default_factory=dict)
    lines: Dict[str, int] = field(default_factory=dict)
    name_line: int = -1
    start: int = 0
    end: int = 0

    def get(self, slot: str) -> str:
        return self.values.get(slot, "")

    def as_dict(self) -> Dict:
        d = {"faction": self.faction, "lines": [self.start + 1, self.end]}
        for slot in MOVIE_SLOTS:
            d[slot] = self.get(slot)
            d[slot + "_set"] = slot in self.lines
        return d


@dataclass
class MovieFile:
    """The whole XML, held as its own lines with the blocks indexed into it."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    records: List[MovieRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    #: 0-based line of ``</faction_movies>``, where a new block is inserted
    close_line: int = -1

    def text(self) -> str:
        out = self.newline.join(self.lines)
        return out + self.newline if self.trailing_newline and self.lines else out

    def get(self, faction: str) -> Optional[MovieRecord]:
        low = faction.lower()
        return next((r for r in self.records if r.faction.lower() == low), None)

    def block_text(self, rec: MovieRecord) -> str:
        return self.newline.join(self.lines[rec.start:rec.end])


def parse_movies(text: str) -> MovieFile:
    """Read the file. Never raises: an unknown tag is a warning, never a loss.

    A hand-rolled line scan rather than an XML parser, for the reason every
    other reader here is one: ``ElementTree`` would give back a tree with no
    line numbers and no indentation, and the file would come back from the
    first save reformatted.
    """
    lines, newline, trailing = split_lines(text)
    mf = MovieFile(lines=lines, newline=newline, trailing_newline=trailing)
    cur: Optional[MovieRecord] = None
    for i, raw in enumerate(lines):
        code = raw.strip()
        if not code:
            continue
        if _TAG.match(code) and _TAG.match(code).group(2) == "faction_movies":
            if _TAG.match(code).group(1):
                mf.close_line = i
            continue
        opened = _TAG.match(code)
        if opened and opened.group(2) == "faction":
            if opened.group(1):              # </faction>
                if cur is not None:
                    cur.end = i + 1
                    cur = None
                continue
            cur = MovieRecord(start=i, end=i + 1)
            mf.records.append(cur)
            continue
        if cur is None:
            continue
        cur.end = i + 1
        m = _VALUE.match(code)
        if m is None:
            mf.warnings.append(f"line {i + 1}: `{code[:40]}` is not a "
                               "<slot>value</slot> line")
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "name":
            cur.faction = value
            cur.name_line = i
            continue
        if tag not in MOVIE_SLOTS:
            mf.warnings.append(
                f"line {i + 1}: <{tag}> is not one of "
                + kb.and_list(list(MOVIE_SLOTS)))
            continue
        if tag in cur.lines:
            mf.warnings.append(f"line {i + 1}: a second <{tag}> for "
                               f"{cur.faction or '(unnamed)'}")
        cur.values[tag] = value
        cur.lines[tag] = i
    for rec in mf.records:
        if not rec.faction:
            mf.warnings.append(f"line {rec.start + 1}: this <faction> block has "
                               "no <name>")
    if mf.close_line < 0:
        mf.warnings.append("this file has no closing </faction_movies>")
    return mf


def movies_path(mod, campaign: str = DEFAULT_CAMPAIGN) -> Path:
    return campaign_dir(mod, campaign) / MOVIES_NAME


def read_movies(mod, campaign: str = DEFAULT_CAMPAIGN) -> Tuple[MovieFile, str]:
    path = movies_path(mod, campaign)
    if not path.exists():
        raise CampFileError(f"{campaign} has no {MOVIES_NAME}")
    text = kb.read_text(path, ENCODING)
    return parse_movies(text), text


def _indent_pair(mf: MovieFile, rec: MovieRecord) -> Tuple[str, str]:
    """``(block indent, slot indent)``, copied off the file rather than chosen."""
    outer = kb.indent_of(mf.lines[rec.start])
    inner = next((kb.indent_of(mf.lines[i]) for i in sorted(rec.lines.values())),
                 kb.indent_of(mf.lines[rec.name_line])
                 if rec.name_line >= 0 else outer + "\t")
    return outer, inner


def render_movies(mf: MovieFile, rec: MovieRecord, edits: Dict) -> str:
    """The whole file with one faction's slots rewritten, line by line.

    A slot the block does not have is a line inserted in :data:`MOVIE_SLOTS`
    order; a slot cleared to nothing has its line removed, because
    ``<victory></victory>`` is a path of zero characters and not "no movie".
    """
    sp = kb.Splice(list(mf.lines))
    outer, inner = _indent_pair(mf, rec)
    added: List[Tuple[int, str]] = []
    for slot in MOVIE_SLOTS:
        if slot not in edits:
            continue
        value = str(edits[slot] or "").strip()
        at = rec.lines.get(slot)
        if at is not None:
            if not value:
                sp.drop(at)
            elif value != rec.get(slot):
                sp.replace(at, f"{inner}<{slot}>{value}</{slot}>")
            continue
        if value:
            added.append((MOVIE_SLOTS.index(slot), f"{inner}<{slot}>{value}</{slot}>"))
    if "faction" in edits:
        name = str(edits["faction"] or "").strip()
        if not name:
            raise CampFileError("a <faction> block needs a <name>", rec.start + 1)
        if name != rec.faction and rec.name_line >= 0:
            sp.replace(rec.name_line, f"{inner}<name>{name}</name>")
    if added:
        # after the last slot line that already exists and sorts before it, so
        # the block stays in the order every real file writes
        for order, row in sorted(added):
            before = [rec.lines[s] for s in MOVIE_SLOTS[:order] if s in rec.lines]
            anchor = max(before) if before else (
                rec.name_line if rec.name_line >= 0 else rec.start)
            sp.after(anchor, [row])
    out = sp.result()
    text = mf.newline.join(out)
    return text + mf.newline if mf.trailing_newline and out else text


def new_movie_block(faction: str, edits: Dict, outer: str = "\t",
                    inner: str = "\t\t") -> List[str]:
    """A whole ``<faction>`` block, in the order the real files write it."""
    name = str(faction or "").strip()
    if not name:
        raise CampFileError("a new <faction> block needs a name")
    rows = [f"{outer}<faction>", f"{inner}<name>{name}</name>"]
    for slot in MOVIE_SLOTS:
        value = str(edits.get(slot) or "").strip()
        if value:
            rows.append(f"{inner}<{slot}>{value}</{slot}>")
    rows.append(f"{outer}</faction>")
    return rows


def insert_movie_block(mf: MovieFile, rows: List[str]) -> str:
    """A new block goes immediately above ``</faction_movies>``."""
    if mf.close_line < 0:
        raise CampFileError("this file has no closing </faction_movies> to put a "
                            "faction in front of")
    lines = list(mf.lines)
    lines[mf.close_line:mf.close_line] = rows
    out = mf.newline.join(lines)
    return out + mf.newline if mf.trailing_newline and lines else out


def remove_movie_block(mf: MovieFile, rec: MovieRecord) -> str:
    lines = list(mf.lines)
    del lines[rec.start:rec.end]
    out = mf.newline.join(lines)
    return out + mf.newline if mf.trailing_newline and lines else out


def check_movies(mf: MovieFile, mod=None, campaign: str = DEFAULT_CAMPAIGN,
                 factions: Optional[List[str]] = None) -> List[Dict]:
    """What is wrong with the movie file, when there is evidence for saying so.

    The ``.bik`` check runs only when the mod ships a ``data/fmv`` folder. Every
    stock movie lives inside the game's packed data, which the toolkit cannot
    read, so "not on disk here" is not "missing" - the same ruling
    :mod:`unittransfer.minorfiles` makes about a settlement card.
    """
    out: List[Dict] = []

    def add(code: str, fatal: bool, message: str, **extra) -> None:
        out.append(dict({"code": code, "fatal": fatal, "message": message}, **extra))

    seen: Dict[str, int] = {}
    for rec in mf.records:
        if not rec.faction:
            add("no_name", True, "a <faction> block with no <name> names no faction",
                line=rec.start + 1)
            continue
        low = rec.faction.lower()
        if low in seen:
            add("duplicate", False,
                f"`{rec.faction}` has a second <faction> block; the engine reads "
                f"the first (line {seen[low] + 1})",
                faction=rec.faction, line=rec.start + 1)
        else:
            seen[low] = rec.start
        if factions is not None and rec.faction not in factions:
            add("unknown_faction", False,
                f"`{rec.faction}` has no faction block in {campaign}'s "
                "descr_strat.txt, so these movies are never played",
                faction=rec.faction, line=rec.start + 1)
        if not rec.values:
            add("no_movies", False,
                f"`{rec.faction}` names no movie at all - the block does nothing",
                faction=rec.faction, line=rec.start + 1)

    fmv = Path(mod.data) / FMV_REL if mod is not None else None
    if fmv is None or not fmv.is_dir():
        return out
    for rec in mf.records:
        for slot, value in rec.values.items():
            if not value:
                continue
            if not (fmv / value).exists():
                add("no_file", False,
                    f"`{rec.faction}`'s {slot} movie is `{value}`, and there is "
                    f"no data/{FMV_REL}/{value}",
                    faction=rec.faction, line=rec.lines.get(slot, rec.start) + 1)
    return out


def movies_view(mod, campaign: str = DEFAULT_CAMPAIGN) -> Dict:
    """The movie screen: one row a faction, whether it has a block or not."""
    try:
        mf, _ = read_movies(mod, campaign)
    except CampFileError as e:
        return {"campaign": campaign, "file": MOVIES_NAME, "have": False,
                "problem": e.message, "rows": [], "findings": [], "warnings": []}
    names = campaign_factions(mod, campaign)
    rows = []
    for name in names:
        rec = mf.get(name)
        rows.append(rec.as_dict() if rec is not None
                    else {"faction": name, "lines": [],
                          **{s: "" for s in MOVIE_SLOTS},
                          **{s + "_set": False for s in MOVIE_SLOTS}})
    extra = [r.as_dict() for r in mf.records
             if r.faction and r.faction not in names]
    return {
        "campaign": campaign, "file": MOVIES_NAME, "have": True,
        "problem": "", "slots": list(MOVIE_SLOTS), "fmv": FMV_REL,
        "rows": rows + extra,
        "declared": len(mf.records),
        "findings": check_movies(mf, mod, campaign, names),
        "warnings": list(mf.warnings),
    }


# ---------------------------------------------------------------------------
# G3 - descr_mercenaries.txt, the province's pool


def mercs_path(mod, campaign: str = DEFAULT_CAMPAIGN) -> Path:
    return campaign_dir(mod, campaign) / MERCS_NAME


def set_regions(line: str, names: List[str]) -> str:
    """Rewrite a ``regions`` line's list, keeping its indent, gap and comment.

    Not :func:`unittransfer.keyblock.sub_tokens`, which walks the tokens already
    on the line and substitutes into them: that is right for the fixed-width
    columns it was written for and wrong here, because a shorter list would
    leave every province past its end still on the line. This one owns the whole
    tail of the line, which is what a variable-length list needs.
    """
    code = line.partition(";")[0]
    indent = kb.indent_of(code)
    rest = code[len(indent) + len("regions"):]
    gap = rest[:len(rest) - len(rest.lstrip())] or " "
    return kb.keep_comment(line, indent + "regions" + gap + " ".join(names))


@dataclass
class MercFile:
    """``descr_mercenaries.txt`` held as lines, with each pool's regions line."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    pools: List[mapquery.MercPool] = field(default_factory=list)
    #: pool name -> 0-based line of its `regions` line, or -1 when it has none
    regions_line: Dict[str, int] = field(default_factory=dict)
    #: pool name -> 0-based line of its `pool` line
    pool_line: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def text(self) -> str:
        out = self.newline.join(self.lines)
        return out + self.newline if self.trailing_newline and self.lines else out

    def pool_of(self, region: str) -> str:
        low = region.lower()
        for p in self.pools:
            if any(r.lower() == low for r in p.regions):
                return p.name
        return ""


def parse_mercs(text: str) -> MercFile:
    """The pools, and where each one's ``regions`` line is.

    The pools themselves come from :func:`unittransfer.mapquery.parse_mercenaries`
    - one parser for this file, as the locked decision says - and what is added
    here is the line index a write needs.
    """
    lines, newline, trailing = split_lines(text)
    mf = MercFile(lines=lines, newline=newline, trailing_newline=trailing,
                  pools=mapquery.parse_mercenaries(text))
    cur = ""
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        word, _, _ = code.partition(" ")
        low = word.lower()
        if low == "pool":
            cur = code[len(word):].strip()
            mf.pool_line.setdefault(cur, i)
            mf.regions_line.setdefault(cur, -1)
        elif low == "regions" and cur:
            if mf.regions_line.get(cur, -1) >= 0:
                mf.warnings.append(f"line {i + 1}: a second `regions` line for "
                                   f"pool {cur}; the first one is edited")
            else:
                mf.regions_line[cur] = i
    return mf


def read_mercs(mod, campaign: str = DEFAULT_CAMPAIGN) -> Tuple[MercFile, str]:
    path = mercs_path(mod, campaign)
    if not path.exists():
        raise CampFileError(f"{campaign} has no {MERCS_NAME}, so no province in "
                            "it has a mercenary pool")
    text = kb.read_text(path, ENCODING)
    return parse_mercs(text), text


def move_region(mf: MercFile, region: str, pool: str) -> str:
    """The whole file with ``region`` taken out of every pool and put in ``pool``.

    An empty ``pool`` takes the province out of all of them, which is a real
    state: 45 of Divide and Conquer's provinces are in no pool and sell nothing.
    The word is spliced into the existing ``regions`` line rather than the line
    being rewritten, so the tab columns the file is laid out in survive.
    """
    low = region.lower()
    if pool and pool not in mf.regions_line:
        raise CampFileError(f"there is no pool called {pool!r} in {MERCS_NAME}")
    sp = kb.Splice(list(mf.lines))
    touched = False
    for p in mf.pools:
        at = mf.regions_line.get(p.name, -1)
        if at < 0:
            continue
        here = [r for r in p.regions if r.lower() == low]
        want = p.name == pool
        if bool(here) == want:
            continue
        kept = [r for r in p.regions if r.lower() != low]
        if want:
            kept.append(region)
        if kept:
            sp.replace(at, set_regions(mf.lines[at], kept))
        else:
            # `regions` with nothing after it is not a line any real file
            # writes, so the pool loses the line rather than keeping an empty one
            sp.drop(at)
        touched = True
    if pool and mf.regions_line.get(pool, -1) < 0:
        # a pool with no regions line at all: give it one, under its `pool` line
        at = mf.pool_line[pool]
        indent = kb.indent_of(mf.lines[at + 1]) if at + 1 < len(mf.lines) else "\t"
        sp.after(at, [f"{indent or chr(9)}regions {region}"])
        touched = True
    if not touched:
        return mf.text()
    out = sp.result()
    text = mf.newline.join(out)
    return text + mf.newline if mf.trailing_newline and out else text


def mercs_view(mod, campaign: str = DEFAULT_CAMPAIGN,
               region: str = "") -> Dict:
    """What the region panel's picker needs: the pools, and which one this is in."""
    try:
        mf, _ = read_mercs(mod, campaign)
    except CampFileError as e:
        return {"campaign": campaign, "file": MERCS_NAME, "have": False,
                "problem": e.message, "pools": [], "pool": "", "units": []}
    pools = [{"name": p.name, "regions": len(p.regions), "units": list(p.units)}
             for p in mf.pools]
    here = mf.pool_of(region) if region else ""
    units = next((list(p.units) for p in mf.pools if p.name == here), [])
    return {"campaign": campaign, "file": MERCS_NAME, "have": True, "problem": "",
            "pools": pools, "pool": here, "units": units,
            "warnings": list(mf.warnings)}


def check_mercs(mf: MercFile, regions: Optional[List[str]] = None) -> List[Dict]:
    """Findings over the whole file. ``regions`` is descr_regions.txt's list.

    A rule with no evidence reports nothing: with no region list the province
    checks do not run at all, rather than reporting every pool as naming
    provinces that do not exist.
    """
    out: List[Dict] = []

    def add(code: str, fatal: bool, message: str, **extra) -> None:
        out.append(dict({"code": code, "fatal": fatal, "message": message}, **extra))

    seen: Dict[str, str] = {}
    for p in mf.pools:
        if mf.regions_line.get(p.name, -1) < 0:
            add("no_regions", False,
                f"pool `{p.name}` names no regions, so nothing draws on it",
                pool=p.name, line=mf.pool_line.get(p.name, 0) + 1)
        if not p.units:
            add("no_units", False,
                f"pool `{p.name}` sells nothing",
                pool=p.name, line=mf.pool_line.get(p.name, 0) + 1)
        for r in p.regions:
            low = r.lower()
            if low in seen:
                add("two_pools", False,
                    f"`{r}` is in pool `{seen[low]}` and pool `{p.name}`",
                    pool=p.name, region=r,
                    line=mf.regions_line.get(p.name, 0) + 1)
            else:
                seen[low] = p.name
            if regions is not None and not any(x.lower() == low for x in regions):
                add("unknown_region", False,
                    f"pool `{p.name}` names `{r}`, which is not a region in "
                    "descr_regions.txt",
                    pool=p.name, region=r,
                    line=mf.regions_line.get(p.name, 0) + 1)
    if regions is not None:
        for r in regions:
            if r.lower() not in seen:
                add("no_pool", False,
                    f"`{r}` is in no mercenary pool, so no mercenary is ever "
                    "recruitable there",
                    region=r, line=0)
    return out


# ---------------------------------------------------------------------------
# the save - one plan and one apply over all three files


#: what a save can be about
WHAT = ("descriptions", "movies", "mercenaries")


@dataclass
class CampFilePlan:
    """One save, worked out without touching the disk."""

    mod: object = None
    what: str = ""
    campaign: str = DEFAULT_CAMPAIGN
    action: str = "edit"                 # 'edit' | 'add' | 'delete'
    name: str = ""                       # the faction or the region
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    #: the campaign-folder file as it would be written, and where
    text: str = ""
    path: Optional[Path] = None
    #: ``{tag: text}`` this save would write into campaign_descriptions
    loc_writes: Dict[str, str] = field(default_factory=dict)
    loc_new: List[str] = field(default_factory=list)

    def summary(self) -> str:
        head = (f"{self.action} {self.what} for {self.name or self.campaign} in "
                f"{getattr(self.mod, 'name', '?')} ({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"what": self.what, "action": self.action, "name": self.name,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings),
                "loc_writes": dict(self.loc_writes), "loc_new": list(self.loc_new),
                "ok": not self.errors and bool(self.text or self.loc_writes)}


def plan(mod, body: dict) -> CampFilePlan:
    """Work out one save. ``body`` is ``{what, campaign, action, name, edits}``."""
    p = CampFilePlan(mod=mod, what=str(body.get("what") or "").strip(),
                     campaign=str(body.get("campaign") or DEFAULT_CAMPAIGN),
                     action=str(body.get("action") or "edit"),
                     name=str(body.get("name") or "").strip())
    if p.what not in WHAT:
        p.errors.append(f"a save is about {kb.and_list(list(WHAT))}, not "
                        f"{p.what!r}")
        return p
    try:
        if p.what == "descriptions":
            _plan_descriptions(p, dict(body.get("edits") or {}))
        elif p.what == "movies":
            _plan_movies(p, dict(body.get("edits") or {}))
        else:
            _plan_mercenaries(p, dict(body.get("edits") or {}))
    except CampFileError as e:
        p.errors.append(e.message)
        return p
    if not p.text and not p.loc_writes and not p.errors:
        p.errors.append("nothing to change")
    return p


def _plan_descriptions(p: CampFilePlan, edits: Dict) -> None:
    """The keys one description save would write.

    The campaign's own title is written when ``name`` is empty, and a faction's
    title and blurb when it is not. A key the file has not got is created rather
    than refused: a faction with no description shows its code name on the menu,
    which is the fault the screen exists to fix.
    """
    have = descr_pairs(p.mod)
    for kind in DESCR_KINDS:
        field_name = kind.lower()
        if field_name not in edits:
            continue
        value = str(edits[field_name] or "")
        key = descr_key(p.campaign, p.name, kind)
        if have.get(key, None) == value:
            continue
        if key not in have:
            p.loc_new.append(key)
        p.loc_writes[key] = value
        shown = value.replace("\\n", " ").strip()
        p.changes.append(f"{key}: {shown[:60] or '(blank)'}")
    if not descr_path(p.mod).exists():
        bin_path = stringsbin.bin_path_for(descr_path(p.mod))
        if not bin_path.exists():
            raise CampFileError(
                f"{getattr(p.mod, 'name', '?')} has neither {DESCR_REL} nor the "
                "compiled archive beside it, so there is nothing to write into")
        p.warnings.append(
            f"this mod ships only {bin_path.name}, so the keys go straight into "
            "the compiled archive")


def _plan_movies(p: CampFilePlan, edits: Dict) -> None:
    mf, original = read_movies(p.mod, p.campaign)
    names = campaign_factions(p.mod, p.campaign)
    rec = mf.get(p.name)
    if p.action == "add":
        if rec is not None:
            p.errors.append(f"{p.name} already has a <faction> block")
            return
        if not p.name:
            p.errors.append("a new <faction> block needs a faction")
            return
        outer, inner = ("\t", "\t\t")
        if mf.records:
            outer, inner = _indent_pair(mf, mf.records[0])
        text = insert_movie_block(mf, new_movie_block(p.name, edits, outer, inner))
        p.changes.append(f"+ <faction>{p.name}</faction>")
    elif rec is None:
        p.errors.append(f"{p.name} has no <faction> block in {MOVIES_NAME}")
        return
    elif p.action == "delete":
        text = remove_movie_block(mf, rec)
        p.changes.append(f"- <faction>{p.name}</faction>")
    else:
        text = render_movies(mf, rec, edits)
        for slot in MOVIE_SLOTS:
            if slot not in edits:
                continue
            was, now = rec.get(slot), str(edits[slot] or "").strip()
            if was != now:
                p.changes.append(f"{p.name} {slot}: {was or '(none)'} -> "
                                 f"{now or '(none)'}")
    p.path = movies_path(p.mod, p.campaign)
    p.text = "" if text == original else text
    after = parse_movies(text)
    p.findings = check_movies(after, p.mod, p.campaign, names)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings
                   if not f["fatal"] and f.get("faction") == p.name]


def _plan_mercenaries(p: CampFilePlan, edits: Dict) -> None:
    """Move one province between pools. ``name`` is the region."""
    mf, original = read_mercs(p.mod, p.campaign)
    if not p.name:
        raise CampFileError("moving a mercenary pool needs a region")
    pool = str(edits.get("pool") or "").strip()
    before = mf.pool_of(p.name)
    if pool == before:
        return
    text = move_region(mf, p.name, pool)
    p.path = mercs_path(p.mod, p.campaign)
    p.text = "" if text == original else text
    p.changes.append(f"{p.name}: mercenary pool {before or '(none)'} -> "
                     f"{pool or '(none)'}")
    if not pool:
        p.warnings.append(
            f"{p.name} is now in no pool, so no mercenary is recruitable there")
    p.findings = check_mercs(parse_mercs(text))


def apply(p: CampFilePlan) -> Dict:
    """Write a planned save, with the same backups and undo as any other job."""
    import shutil
    import time

    from . import cleaner, config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text and not p.loc_writes:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    out: Dict = {"id": tid, "what": p.what, "name": p.name}

    def keep(rel: str) -> Path:
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
        return target

    if p.text and p.path is not None:
        rel = str(p.path.relative_to(Path(mod.data))).replace("\\", "/")
        target = keep(rel)
        kb.write_text(target, p.text, ENCODING)
        file_op("WRITE", target, f"{len(p.text)} bytes")
    if p.loc_writes:
        out["loc"] = _write_descriptions(p, keep, cleaner, file_op)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campfiles",
        "action": p.action,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name or p.campaign, "resolved_type": p.what,
        "options": {"campaign": p.campaign, "what": p.what},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPFILE %s %s %s in %s - %d change(s), id=%s",
             p.action, p.what, p.name or p.campaign, mod.name,
             len(p.changes), tid)
    out["record"] = rec
    return out


def _write_descriptions(p: CampFilePlan, keep, cleaner, file_op) -> Dict:
    """The keys, into the ``.txt`` if there is one and the ``.bin`` if not.

    The same two roads :func:`unittransfer.traits._write_loc` takes, and for the
    same reason: a mod that ships only the compiled archive is not a broken mod,
    it is most released ones.
    """
    txt = descr_path(p.mod)
    if txt.exists():
        target = keep(DESCR_REL)
        # the compiled cache is rewritten below, so back it up too - an undo
        # that restored the .txt and left the .bin would put the file back and
        # leave the game still reading the new text
        keep(DESCR_REL + ".strings.bin")
        kb.write_text(target,
                      stringsbin.upsert_txt(kb.read_text(target, LOC_ENCODING),
                                            p.loc_writes),
                      LOC_ENCODING)
        file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
        res = cleaner.refresh_strings_bin(p.mod.root, DESCR_BIN_REL)
        return {"file": DESCR_REL, "written": len(p.loc_writes),
                "new": len(p.loc_new), "strings_bin": res}
    rel = DESCR_REL + ".strings.bin"
    target = keep(rel)
    sb = stringsbin.read(target)
    for tag, value in p.loc_writes.items():
        sb.set(tag, value)
    stringsbin.write(target, sb)
    file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
    return {"file": rel, "written": len(p.loc_writes), "new": len(p.loc_new),
            "compiled": True}
