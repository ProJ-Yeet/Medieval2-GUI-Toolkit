"""Phase 19a. The text that names a record somebody just created.

Two gaps, D4 and D5, and one sentence covers both: **a record was written and
the words the player reads for it were not.** The validator already reports the
first of them against our own output - 16e's wizard creates a province, 16f's
``loc.missing`` rule then says the player will read its code name on the
campaign map, and until now there was nothing in the toolkit that could write
the line that fixes it.

**D4 - the province and its settlement.**
``data/text/imperial_campaign_regions_and_settlement_names.txt`` is a
``{key}value`` file keyed by the region's own name and its settlement's own
name. :func:`unittransfer.campmap.shown_names` has parsed it for the region
panel since 16f and nothing has ever written it. Measured on both installed
mods: UTF-16LE with a BOM, CRLF, 400 keys in Divide and Conquer and 398 in
Third Age Reforged, and **every region and every settlement in both is in it** -
so a mod that is missing one is a mod something built, which is the case this
closes.

**D5 - the pool a character's name has to come from.** ``descr_names.txt``
lists, per faction, the names the engine may generate and localise. 16i writes
characters and takes the name as free text, and
:func:`unittransfer.stratchar.check_pool` already says when that name is in no
pool. This is the write behind that finding.

**And D5 is two files, not one.** Every one of Divide and Conquer's 3,583 pool
names and 2,572 of Third Age Reforged's 2,573 has a key in
``data/text/names.txt``; the single exception is the word ``surnames``, which is
a section heading our parser was reading as a name (see below). A pool entry
with no key there shows the raw token in game, so the pool line and the text key
are one job with one backup set and one undo - the ruling
:func:`unittransfer.minorfiles.plan` already makes for a religion, which is
worthless written one file at a time.

**The fourth section this file has, that nothing here knew about.** Third Age
Reforged's ``dolguldur`` writes a ``surnames`` heading, and
:data:`unittransfer.minorfiles.NAME_SECTIONS` listed only three, so the heading
and the one name under it were both read as characters. Two references settle it
independently - Demir's ``parseDescrNamePools`` accepts
``characters | surnames | women | settlements``, and TWMapReader's
``TwDataReader`` tests for ``surnames`` by name - so 19a adds it there rather
than working around it here. A writer that did not know would have appended a
new name underneath a heading that is not the one it meant.

**A name is one word in both campaigns.** All 305 of Divide and Conquer's
characters and all 246 of Third Age Reforged's have a one-word name, and every
one of those words is in a pool. The two-part form the references model - the
last word is a surname and the rest is the first name, joined with underscores -
is therefore supported on the arbiter's word rather than on a measurement, and
is what :func:`name_parts` does.

**Neither file is this module's to parse.** ``descr_names.txt`` belongs to
:mod:`unittransfer.minorfiles` and 16j-2 refused a second copy of it; the two
``{key}value`` files belong to :mod:`unittransfer.stringsbin`. What is here is
the *write* and the rules around it, and every read goes through the module that
already owns the format.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from . import campmap, cleaner, config, keyblock as kb, minorfiles, stringsbin
from .logutil import file_op, log

#: the campaign files are plain 8-bit text; both text files are UTF-16
ENCODING = "latin-1"
LOC_ENCODING = "utf-16"

#: D4's file - the words on the campaign map, keyed by the region's code name
REGION_NAMES_REL = campmap.REGION_NAMES_REL

#: D5's two - the pool itself, and the text keys its entries are read through
POOL_REL = minorfiles.NAMES_REL
POOL_LOC_REL = "text/names.txt"

#: which section a first name goes in. ``surnames`` takes the other half.
POOL_SECTIONS = {"male": "characters", "female": "women"}

WHAT = ("region_names", "name_pool")


class NameKeyError(ValueError):
    """The request names a record, a faction or a file this mod has not got."""


# ---------------------------------------------------------------------------
# the two {key}value files


def bin_rel(rel: str) -> str:
    """``text/names.txt`` -> ``data/text/names.txt.strings.bin``.

    Relative to the mod *root*, because that is what
    :func:`unittransfer.cleaner.refresh_strings_bin` takes.
    """
    return f"data/{rel}.strings.bin"


def loc_state(mod, rel: str) -> Dict:
    """Which of the two forms of one localisation file this mod actually has.

    A released mod very often ships the compiled archive and no ``.txt`` at all,
    and that is not a broken mod - it is the normal one. Both roads are written;
    only "neither" is a refusal, and it names both files rather than one.
    """
    txt = Path(mod.data) / rel
    return {"rel": rel, "txt": txt.exists(),
            "bin": stringsbin.bin_path_for(txt).exists(),
            "file": rel if txt.exists() else rel + ".strings.bin"}


def loc_pairs(mod, rel: str) -> Dict[str, str]:
    """``{key: value}`` from the ``.txt`` if there is one, else the archive."""
    return minorfiles._loc(mod, rel)


def clean_value(value: str, what: str) -> str:
    """One line of a ``{key}value`` file, or the reason it is not one.

    The file is one key a line and a brace is its delimiter, so a value with a
    line break or a brace in it does not round trip - it comes back as a
    different key, or as two.
    """
    text = str(value or "").strip()
    if not text:
        raise NameKeyError(
            f"a {what} the player reads cannot be blank - with no line at all "
            f"the game shows the code name, which is at least a word")
    if "\n" in text or "\r" in text:
        raise NameKeyError(f"a {what} is one line; this one has a line break in it")
    if "{" in text or "}" in text:
        raise NameKeyError(
            f"a {what} cannot contain {{ or }} - they are what separates a key "
            f"from its text in this file")
    return text


def _write_loc(mod, rel: str, writes: Dict[str, str], keep,
               warnings: List[str]) -> Dict:
    """Put these keys in one localisation file, whichever form the mod has.

    The ``.txt`` road also backs up and recompiles the ``.strings.bin`` beside
    it, and that is not tidiness: the game reads the archive, so an undo that
    restored the text and left the cache would put the file back and leave the
    game still showing the new words.

    ``keep`` is the caller's own backup closure, so this write joins whatever
    backup set it was called from rather than opening a second one.
    """
    txt = Path(mod.data) / rel
    if txt.exists():
        target = keep(rel)
        keep(rel + ".strings.bin")
        kb.write_text(target,
                      stringsbin.upsert_txt(kb.read_text(target, LOC_ENCODING),
                                            writes),
                      LOC_ENCODING)
        file_op("WRITE", target, f"{len(writes)} text key(s)")
        res = cleaner.refresh_strings_bin(mod.root, bin_rel(rel))
        if not res.get("rebuilt"):
            warnings.append(
                f"{Path(rel).name}.strings.bin could not be recompiled "
                f"({res.get('rebuild_error') or 'no reason given'}), so it was "
                f"deleted instead and the game rebuilds it on the next launch")
        return {"file": rel, "written": len(writes), "strings_bin": res}
    rel_bin = rel + ".strings.bin"
    target = keep(rel_bin)
    sb = stringsbin.read(target)
    for tag, value in writes.items():
        sb.set(tag, value)
    stringsbin.write(target, sb)
    file_op("WRITE", target, f"{len(writes)} text key(s)")
    return {"file": rel_bin, "written": len(writes), "compiled": True}


# ---------------------------------------------------------------------------
# D4 - what the campaign map calls a province and its settlement


def region_names(mod, region: str) -> Dict:
    """The two keys one province is read through, and what each says today.

    The settlement half is absent on the short wasteland form, which has no
    settlement at all - the panel asks one question fewer rather than offering a
    box for a key nothing would ever look up.
    """
    rf = campmap.read_regions(mod)
    rec = rf.by_name(region)
    if rec is None:
        raise NameKeyError(f"no region called {region!r} in descr_regions.txt")
    pairs = loc_pairs(mod, REGION_NAMES_REL)
    state = loc_state(mod, REGION_NAMES_REL)
    out = {**state, "region": rec.name, "have": state["txt"] or state["bin"],
           "keys": len(pairs), "rows": []}
    for slot, value in (("region", rec.name), ("settlement", rec.settlement)):
        if not value:
            continue
        out["rows"].append({"slot": slot, "key": value,
                            "value": pairs.get(value, ""),
                            "set": value in pairs})
    if not out["have"]:
        out["problem"] = (
            f"{getattr(mod, 'name', '?')} has neither {REGION_NAMES_REL} nor the "
            f"compiled archive beside it, so there is nothing to write into and "
            f"nothing that could be missing from it")
    return out


def region_writes(mod, region: str, edits: Dict) -> Tuple[Dict[str, str], List[str]]:
    """``({key: text}, [keys that are new])`` for one province's two boxes.

    Only what actually differs: a box somebody opened and did not change is not
    a write, and writing it anyway would put a file in the backup set and a line
    in the log for nothing.
    """
    got = region_names(mod, region)
    if not got["have"]:
        raise NameKeyError(got["problem"])
    writes: Dict[str, str] = {}
    new: List[str] = []
    for row in got["rows"]:
        if row["slot"] not in edits:
            continue
        want = clean_value(edits[row["slot"]],
                           "region name" if row["slot"] == "region"
                           else "settlement name")
        if want == row["value"]:
            continue
        writes[row["key"]] = want
        if not row["set"]:
            new.append(row["key"])
    return writes, new


# ---------------------------------------------------------------------------
# D5 - the pool a character's name has to be in


def name_parts(name: str) -> Tuple[str, str]:
    """``"Baldwin"`` -> ``("Baldwin", "")``; ``"Jean de Brienne"`` -> the two halves.

    The references' rule, not a measured one: every character in both installed
    campaigns has a one-word name. Demir's ``ensureCharacterNameInFaction`` takes
    the last word as the surname and joins the rest as the first name, and a pool
    entry is one word, so the join is by underscore - which is exactly the token
    both ``descr_names.txt`` and ``text/names.txt`` are keyed by.

    **The split is on spaces and never on underscores.** An underscore is what a
    space *inside* one part becomes: Divide and Conquer's pool holds
    ``The_Dark_Lord`` as one entry and its ``descr_strat`` writes it as one word,
    so a rule that split on underscores would go looking for a first name called
    ``The_Dark`` and a surname called ``Lord``, and find neither.
    """
    words = str(name or "").split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return "_".join(words[:-1]), words[-1]


def read_pool(mod) -> Tuple[minorfiles.NameFile, str]:
    """``descr_names.txt`` through the module that owns it, plus its own text."""
    path = Path(mod.data) / POOL_REL
    if not path.is_file():
        raise NameKeyError(
            f"{getattr(mod, 'name', '?')} has no {POOL_REL}, so there is no pool "
            f"to add a name to. The stock game keeps it inside its packed data")
    text = kb.read_text(path, ENCODING)
    return minorfiles.parse_names(text), text


def pool_view(mod, faction: str, name: str = "", gender: str = "male") -> Dict:
    """What the character form shows beside the Name box.

    Says which of the three sections each half of the name would go in, whether
    it is already there, and whether the text key it is read through exists -
    the second of those being the half nothing in the toolkit could see before.
    """
    out: Dict = {"faction": faction, "file": POOL_REL, "have": False,
                 "loc": loc_state(mod, POOL_LOC_REL), "parts": []}
    try:
        nf, _ = read_pool(mod)
    except NameKeyError as exc:
        out["problem"] = str(exc)
        return out
    out["have"] = True
    fac = nf.get(faction)
    if fac is None:
        out["problem"] = (f"{POOL_REL} has no `faction: {faction}` block, so this "
                          f"faction can generate no names at all")
        return out
    out["sections"] = {s.name: len(s.entries) for s in fac.sections}
    first, surname = name_parts(name)
    pairs = loc_pairs(mod, POOL_LOC_REL) if (first or surname) else {}
    out["keys"] = len(pairs)
    for part, section in ((first, POOL_SECTIONS.get(str(gender).lower(), "characters")),
                          (surname, "surnames")):
        if not part:
            continue
        sec = fac.section(section)
        out["parts"].append({
            "part": part, "section": section,
            "in_pool": bool(sec and any(e.value == part for e in sec.entries)),
            "has_section": sec is not None,
            "shown": pairs.get(part, ""),
            "has_key": part in pairs,
        })
    return out


def _add_to_section(nf: minorfiles.NameFile, fac: minorfiles.NameFaction,
                    section: str, part: str) -> str:
    """One name into one section of one faction, as the whole file's new text.

    Written through :func:`unittransfer.minorfiles.render_names` on the faction's
    own block and spliced back, rather than by editing lines here: that function
    is index-aligned with the names already on disk, so 800 untouched lines stay
    byte for byte where they were.
    """
    base = nf.block_text(fac)
    sec = fac.section(section)
    if sec is None:
        # a heading this faction has not got. Written in the indentation the
        # faction's own sections use - one level for a heading and two for a
        # name, which is what all three installed files do on 43,158 of 43,161
        # lines - rather than in one decided here.
        indent = (kb.indent_of(nf.lines[fac.sections[0].start])
                  if fac.sections else "\t")
        inner = (kb.indent_of(nf.lines[fac.sections[0].entries[0].line])
                 if fac.sections and fac.sections[0].entries else indent + "\t")
        block = base.rstrip("\r\n").split(nf.newline)
        block += [indent + section, inner + part]
        return nf.replace(fac.start, fac.end, nf.newline.join(block))
    wanted = [e.value for e in sec.entries] + [part]
    return nf.replace(fac.start, fac.end,
                      minorfiles.render_names(base, {"sections": {section: wanted}}))


# ---------------------------------------------------------------------------
# plan -> apply


@dataclass
class NamePlan:
    """One save, worked out without touching the disk."""

    mod: object = None
    what: str = ""
    name: str = ""                       # the region, or the character's name
    faction: str = ""                    # D5 only
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: ``{rel: whole new text}`` for the 8-bit files this save rewrites
    text: Dict[str, str] = field(default_factory=dict)
    #: ``{rel: {key: value}}`` for the ``{key}value`` files it writes into
    loc_writes: Dict[str, Dict[str, str]] = field(default_factory=dict)
    loc_new: List[str] = field(default_factory=list)

    def touched(self) -> bool:
        return bool(self.text or any(self.loc_writes.values()))

    def files(self) -> List[str]:
        return sorted(set(self.text)
                      | {rel for rel, w in self.loc_writes.items() if w})

    def summary(self) -> str:
        subject = self.name or self.faction
        head = (f"{self.what} for {subject} in {getattr(self.mod, 'name', '?')} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"what": self.what, "name": self.name, "faction": self.faction,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "loc_new": list(self.loc_new),
                "files": self.files(),
                "ok": not self.errors and self.touched()}


def plan(mod, body: dict) -> NamePlan:
    """Work out one save. ``body`` is ``{what, region|faction, name, gender, edits}``."""
    p = NamePlan(mod=mod, what=str(body.get("what") or "").strip())
    if p.what not in WHAT:
        p.errors.append(f"a save is about {kb.and_list(list(WHAT))}, not {p.what!r}")
        return p
    try:
        if p.what == "region_names":
            _plan_region(p, body)
        else:
            _plan_pool(p, body)
    except (NameKeyError, minorfiles.MinorError, campmap.MapError, OSError) as exc:
        p.errors.append(getattr(exc, "message", None) or str(exc))
        return p
    if not p.touched() and not p.errors:
        p.errors.append("nothing to change")
    return p


def _plan_region(p: NamePlan, body: dict) -> None:
    p.name = str(body.get("region") or "").strip()
    writes, new = region_writes(p.mod, p.name, dict(body.get("edits") or {}))
    if not writes:
        return
    p.loc_writes[REGION_NAMES_REL] = writes
    p.loc_new += new
    for key, value in writes.items():
        p.changes.append(f"{'+ ' if key in new else ''}{key}: {value}")
    if not loc_state(p.mod, REGION_NAMES_REL)["txt"]:
        p.warnings.append(f"this mod ships only {Path(REGION_NAMES_REL).name}"
                          f".strings.bin, so the keys go straight into the "
                          f"compiled archive")


def _plan_pool(p: NamePlan, body: dict) -> None:
    """One character's name into the faction's pool, and into ``names.txt``.

    Both halves of the write are optional on their own: a name already in the
    pool may still have no text key, and that is exactly the state that shows
    the raw token in game rather than the name.
    """
    p.faction = str(body.get("faction") or "").strip()
    p.name = str(body.get("name") or "").strip()
    gender = str(body.get("gender") or "male").lower()
    if not p.name:
        raise NameKeyError("a name is needed before it can be put in a pool")
    nf, original = read_pool(p.mod)
    if nf.get(p.faction) is None:
        raise NameKeyError(
            f"{POOL_REL} has no `faction: {p.faction}` block. Adding one is the "
            f"Minor Files names tab, or the Factions screen's clone, both of "
            f"which write a whole pool rather than one line of one")
    have = loc_pairs(p.mod, POOL_LOC_REL)
    shown = dict(body.get("edits") or {})
    text = original
    loc: Dict[str, str] = {}
    first, surname = name_parts(p.name)
    for part, section in ((first, POOL_SECTIONS.get(gender, "characters")),
                          (surname, "surnames")):
        if not part:
            continue
        # re-read after the first half's splice, so the second one is spliced
        # against the file as the first left it rather than as it was on disk
        nf = minorfiles.parse_names(text)
        fac = nf.get(p.faction)
        sec = fac.section(section)
        if sec is None or not any(e.value == part for e in sec.entries):
            text = _add_to_section(nf, fac, section, part)
            if sec is None:
                p.changes.append(f"+ a `{section}` heading for {p.faction}")
            p.changes.append(f"+ {part} in {p.faction}'s `{section}` list")
        elif part in have:
            p.warnings.append(f"{part} is already in {p.faction}'s `{section}` "
                              f"list and already has a text key")
        else:
            p.warnings.append(f"{part} is already in {p.faction}'s `{section}` "
                              f"list; what is missing is its text key")
        want = clean_value(shown.get(part) or have.get(part)
                           or part.replace("_", " "), "name")
        if part not in have:
            loc[part] = want
            p.loc_new.append(part)
            p.changes.append(f"+ {part}: {want} in {POOL_LOC_REL}")
        elif want != have[part]:
            loc[part] = want
            p.changes.append(f"{part}: {have[part]} -> {want} in {POOL_LOC_REL}")
    if text != original:
        p.text[POOL_REL] = text
    got = loc_state(p.mod, POOL_LOC_REL)
    if not got["txt"] and not got["bin"]:
        if loc:
            p.warnings.append(
                f"this mod has neither {POOL_LOC_REL} nor the archive beside it, "
                f"so nothing here could give {p.name} a localised name - the game "
                f"shows the token instead")
        loc = {}
    elif loc and not got["txt"]:
        p.warnings.append(f"this mod ships only {Path(POOL_LOC_REL).name}"
                          f".strings.bin, so the keys go straight into the "
                          f"compiled archive")
    if loc:
        p.loc_writes[POOL_LOC_REL] = loc


def apply(p: NamePlan) -> Dict:
    """Write a planned save, with the same backups and undo as any other job.

    One backup set for both of D5's files, because a pool line with no text key
    behind it is the fault this closes rather than half of a fix - the same
    ruling :func:`unittransfer.minorfiles.apply` makes over a religion's four.
    """
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.touched():
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [], "deleted": []}
    out: Dict = {"id": tid, "what": p.what, "files": []}

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

    for rel, text in p.text.items():
        target = keep(rel)
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
        out["files"].append(rel)
    for rel, writes in p.loc_writes.items():
        if not writes:
            continue
        out["files"].append(_write_loc(mod, rel, writes, keep, p.warnings)["file"])

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "namekeys",
        "action": p.what,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name or p.faction, "resolved_type": p.what,
        "options": {"faction": p.faction},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("NAMEKEY %s %s in %s - %d change(s), id=%s",
             p.what, p.name or p.faction, mod.name, len(p.changes), tid)
    out["record"] = rec
    return out
