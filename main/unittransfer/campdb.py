"""``descr_campaign_db.xml`` - the campaign-wide constants.

Phase 38. Every number the engine reads once for the whole campaign: how many
units a settlement recruits a turn, how ransom and piety behave, what an
autoresolved siege costs, and **whether a fort outlives its garrison**, which is
the half of a permanent stone fort 22a could not reach - :mod:`stratobj` places
a fort and cannot make it stay.

**A form generated from the file, not 281 fields typed here.** The file types
itself. Every value is one attribute and the attribute's *name* is its type::

    <settlement>
       <destroy_empty_forts bool="false"/>
       <fort_devastation_distance uint="5"/>
       <sack_money_modifier float="0.2"/>   <!-- a note the mod wrote -->
    </settlement>

so a tag we never typed - and the two installed mods do not agree on 25 of
them - still comes out as a box that refuses the wrong kind of value. What this
module adds on top is :data:`VOCAB`: the handful of tags the archive actually
explains, with the document that explains them, and nothing guessed.

**What the file actually is, counted on both installed mods.** 18 sections,
the same 18 in the same order; 256 and 303 lines; ``uint``, ``int``, ``float``,
``bool`` and ``string`` and nothing else; no tag with two attributes, no tag
twice under one parent, no element text. Divide and Conquer writes
``float = "1.0"`` with spaces round the ``=`` on nineteen lines and puts a
comment after most of its later tags; Reforged ends its lines in CRLF.

**Why ElementTree is not the parser.** It would read every one of those files
and write none of them back: the comments, the spaces round the ``=``, the tab
before a comment and the line endings would all be its own on the way out. So
the scan is line by line and a save is a splice of the characters between two
quotes, the same ruling :mod:`campfiles` made for the faction movies.
ElementTree is still here, as the gate: a save whose text it cannot parse is
refused, because the engine's reader is stricter than ours.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb

REL = "descr_campaign_db.xml"
#: plain 8-bit text; both real copies are ASCII
ENCODING = "latin-1"

#: the five value attributes, and the only five either installed mod uses
TYPES = ("bool", "uint", "int", "float", "string")

_LEAF = re.compile(
    r'^(?P<pre>\s*<(?P<tag>[A-Za-z_][\w.-]*)\s+(?P<type>[A-Za-z_]+)\s*=\s*")'
    r'(?P<value>[^"]*)'
    r'(?P<post>"\s*/>)(?P<tail>.*)$')
_OPEN = re.compile(r"^\s*<(?P<tag>[A-Za-z_][\w.-]*)\s*>\s*(?P<tail>.*)$")
_CLOSE = re.compile(r"^\s*</(?P<tag>[A-Za-z_][\w.-]*)\s*>\s*(?P<tail>.*)$")
_COMMENT = re.compile(r"<!--(.*?)-->", re.S)

_VALID = {
    "bool": re.compile(r"^(true|false)$"),
    "uint": re.compile(r"^\d+$"),
    "int": re.compile(r"^-?\d+$"),
    "float": re.compile(r"^-?(\d+(\.\d*)?|\.\d+)$"),
}

#: The settlement ladders the ``*_city_level`` and ``*_castle_level`` strings
#: name. ``moot_and_bailey`` is how both installed mods and the archive's copy
#: of the Britannia file spell it; the EDB spells the building
#: ``motte_and_bailey``, so both are taken rather than one being called wrong.
CITY_LEVELS = ("village", "town", "large_town", "city", "large_city", "huge_city")
CASTLE_LEVELS = ("moot_and_bailey", "motte_and_bailey", "wooden_castle",
                 "castle", "fortress", "citadel")

_FORTS = "Everything you need to know about permanent stone and or buildable forts.pdf"
_PIETY = "[Tutorial] How piety works and how to activate the alternative piety mode.pdf"
_RANSOM = "[Tutorial] Prisoner Treatment.pdf"

#: What the archive says a tag does. ``default`` is only set where a document
#: prints the line whole, and is what "add it" writes.
VOCAB: Dict[str, Dict] = {
    "can_build_forts": {
        "section": "settlement", "type": "bool", "default": "true", "source": _FORTS,
        "doc": "Whether a general can build a fort in the field. false in both "
               "installed mods."},
    "destroy_empty_forts": {
        "section": "settlement", "type": "bool", "default": "false", "source": _FORTS,
        "doc": "false keeps a fort standing once its army walks out - the switch "
               "that makes a fort placed in descr_strat permanent."},
    "fort_fortification_level": {
        "section": "settlement", "type": "string", "default": "3", "source": _FORTS,
        "doc": "Which model a newly BUILT fort gets. Forts placed in descr_strat "
               "keep their own, so built ones can be wood and placed ones stone."},
    "alternative_religious_unrest": {
        "section": "settlement", "type": "bool", "default": "true", "source": _PIETY,
        "doc": "Kingdoms' Britannia piety mode: a governor's piety LOWERS unrest "
               "from a foreign religion instead of raising it. Generals only - "
               "priests are unchanged. The three alt_rel_ values are its tuning."},
    "alt_rel_allied_modifier": {
        "section": "settlement", "type": "float", "default": "0.5", "source": _PIETY,
        "doc": "Alternative piety mode: allied religion cumulative total modifier."},
    "alt_rel_gov_modifier_base": {
        "section": "settlement", "type": "float", "default": "2.0", "source": _PIETY,
        "doc": "Alternative piety mode: governor's piety, base modifier."},
    "alt_rel_gov_coefficient": {
        "section": "settlement", "type": "float", "default": "-0.2", "source": _PIETY,
        "doc": "Alternative piety mode: governor's piety, coefficient."},
    "captor_release_chance_base": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as captor: base chance to release prisoners. Applies to captains "
               "and generals with no chivalry."},
    "captor_release_chance_chiv_mod": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as captor: added release chance per point of chivalry."},
    "captor_ransom_chance_base": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as captor: base chance to offer a ransom. -100 is never."},
    "captor_ransom_chance_chiv_mod": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as captor: added ransom chance per point of chivalry."},
    "captive_ransom_chance_base": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as the side that lost: base chance to accept and pay a ransom. "
               "-100 is never, which leaves the captor to execute."},
    "captive_ransom_chance_chiv_mod": {
        "section": "ransom", "type": "float", "source": _RANSOM,
        "doc": "AI as the side that lost: added chance to pay per point of chivalry."},
    "captive_ransom_for_slave": {
        "section": "ransom", "type": "bool", "source": _RANSOM,
        "doc": "Whether the AI pays to get back prisoners who would be sold as slaves."},
}


class CampDbError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class Tag:
    """One ``<name type="value"/>`` line."""

    section: str
    name: str
    type: str
    value: str
    line: int                    # 0-based index into :attr:`DbFile.lines`
    note: str = ""               # the comment on the same line, if any

    @property
    def key(self) -> str:
        return f"{self.section}/{self.name}"


@dataclass
class Section:
    name: str
    open_line: int
    close_line: int = -1
    #: tags and stand-alone comments in file order: ("tag", Tag) | ("note", str)
    items: List[Tuple[str, object]] = field(default_factory=list)

    @property
    def tags(self) -> List[Tag]:
        return [t for k, t in self.items if k == "tag"]


@dataclass
class DbFile:
    lines: List[str]
    newline: str = "\n"
    trailing_newline: bool = True
    root: str = ""
    sections: List[Section] = field(default_factory=list)
    #: lines the scan could not place, as (index, text) - kept, and reported
    unread: List[Tuple[int, str]] = field(default_factory=list)

    def text(self) -> str:
        out = self.newline.join(self.lines)
        return out + self.newline if self.trailing_newline and self.lines else out

    def section(self, name: str) -> Optional[Section]:
        return next((s for s in self.sections if s.name == name), None)

    def tags(self) -> List[Tag]:
        return [t for s in self.sections for t in s.tags]

    def get(self, key: str) -> Optional[Tag]:
        sec, _, name = key.partition("/")
        s = self.section(sec)
        return next((t for t in s.tags if t.name == name), None) if s else None


def _notes(text: str) -> str:
    return " ".join(m.strip() for m in _COMMENT.findall(text)).strip()


def parse_text(text: str) -> DbFile:
    """Scan the file line by line. ``parse_text(t).text() == t`` always."""
    newline = "\r\n" if "\r\n" in text else "\n"
    body = text[:-len(newline)] if text.endswith(newline) else text
    db = DbFile(lines=body.split(newline) if text else [], newline=newline,
                trailing_newline=text.endswith(newline))
    depth: List[str] = []
    cur: Optional[Section] = None
    in_comment = False
    for i, raw in enumerate(db.lines):
        s = raw.strip()
        if in_comment:
            if "-->" in s:
                in_comment = False
            continue
        if not s or s.startswith("<?"):
            continue
        if s.startswith("<!--"):
            if "-->" not in s:
                in_comment = True
                continue
            if cur is not None and depth == [db.root, cur.name]:
                cur.items.append(("note", _notes(s)))
            continue
        m = _LEAF.match(raw)
        if m and cur is not None and depth == [db.root, cur.name]:
            cur.items.append(("tag", Tag(section=cur.name, name=m["tag"],
                                         type=m["type"], value=m["value"], line=i,
                                         note=_notes(m["tail"]))))
            continue
        m = _OPEN.match(raw)
        if m and (not m["tail"].strip() or m["tail"].strip().startswith("<!--")):
            depth.append(m["tag"])
            if len(depth) == 1:
                db.root = m["tag"]
            elif len(depth) == 2:
                cur = Section(name=m["tag"], open_line=i)
                db.sections.append(cur)
            continue
        m = _CLOSE.match(raw)
        if m and depth and depth[-1] == m["tag"]:
            depth.pop()
            if cur is not None and len(depth) == 1:
                cur.close_line = i
                cur = None
            continue
        db.unread.append((i, raw))
    return db


def path_for(mod) -> Path:
    return Path(mod.data) / REL


def read(mod) -> Tuple[DbFile, str]:
    p = path_for(mod)
    if not p.is_file():
        raise CampDbError(f"{mod.name} has no data/{REL}")
    text = kb.read_text(p, ENCODING)
    return parse_text(text), text


# ---------------------------------------------------------------------------
# checks


def check_value(type_: str, value: str, name: str = "") -> Tuple[Optional[str], Optional[str]]:
    """``(error, warning)`` for one value of one type."""
    if type_ not in TYPES:
        return None, f"`{type_}` is not one of the five value types this file uses"
    if type_ == "string":
        if any(c in value for c in '"<>&'):
            return "a string value cannot hold \" < > or &", None
        if name.endswith("_city_level") and value not in CITY_LEVELS:
            return None, f"`{value}` is not a city level ({', '.join(CITY_LEVELS)})"
        if name.endswith("_castle_level") and value not in CASTLE_LEVELS:
            return None, f"`{value}` is not a castle level ({', '.join(CASTLE_LEVELS)})"
        return None, None
    if not _VALID[type_].match(value):
        want = {"bool": "true or false", "uint": "a whole number, 0 or more",
                "int": "a whole number", "float": "a number"}[type_]
        return f"`{value}` is not {want}", None
    return None, None


def finding(code: str, fatal: bool, message: str, **extra) -> Dict:
    return dict({"code": code, "fatal": fatal, "message": message}, **extra)


def check_file(db: DbFile) -> List[Dict]:
    out: List[Dict] = []
    if db.root != "root":
        out.append(finding("root", True, f"the document element is `<{db.root}>`, "
                           "and the engine reads `<root>`"))
    for i, raw in db.unread:
        out.append(finding("unread", False, f"line {i + 1} is not a tag this screen "
                           f"can edit and is kept as it is: {raw.strip()[:80]}",
                           line=i + 1))
    for s in db.sections:
        if s.close_line < 0:
            out.append(finding("unclosed", True, f"<{s.name}> is never closed",
                               section=s.name))
        seen: Dict[str, int] = {}
        for t in s.tags:
            if t.name in seen:
                out.append(finding("duplicate", False,
                                   f"{t.key} is written twice (lines {seen[t.name] + 1} "
                                   f"and {t.line + 1}) - one of them is ignored",
                                   key=t.key))
            seen.setdefault(t.name, t.line)
            err, warn = check_value(t.type, t.value, t.name)
            if err or warn:
                out.append(finding("value", bool(err), f"{t.key}: {err or warn}",
                                   key=t.key))
    alt = db.get("settlement/alternative_religious_unrest")
    tuned = [t.name for t in db.tags() if t.name.startswith("alt_rel_")]
    if tuned and (alt is None or alt.value != "true"):
        out.append(finding("alt_piety", False,
                           f"{len(tuned)} alt_rel_ value(s) are set and "
                           "alternative_religious_unrest is "
                           f"{'missing' if alt is None else 'off'}, so none of them "
                           "is read", key="settlement/alternative_religious_unrest"))
    return out


# ---------------------------------------------------------------------------
# the screen


def overview(mod) -> Dict:
    db, _ = read(mod)
    return {
        "file": REL,
        "root": db.root,
        "sections": [{
            "name": s.name,
            "items": [
                {"kind": "tag", "key": t.key, "name": t.name, "type": t.type,
                 "value": t.value, "note": t.note, "line": t.line + 1,
                 "vocab": VOCAB.get(t.name)} if k == "tag"
                else {"kind": "note", "text": t}
                for k, t in s.items],
        } for s in db.sections],
        # documented tags this copy does not write, and where they would go
        "missing": [dict(v, name=n) for n, v in VOCAB.items()
                    if "default" in v and db.section(v["section"]) is not None
                    and db.get(f"{v['section']}/{n}") is None],
        "findings": check_file(db),
        "types": list(TYPES),
        "count": len(db.tags()),
    }


# ---------------------------------------------------------------------------
# the save


def set_value(db: DbFile, tag: Tag, value: str) -> None:
    m = _LEAF.match(db.lines[tag.line])
    db.lines[tag.line] = m["pre"] + value + m["post"] + m["tail"]


def add_tag(db: DbFile, section: str, name: str, type_: str, value: str) -> None:
    s = db.section(section)
    if s is None or s.close_line < 0:
        raise CampDbError(f"there is no <{section}> section to add {name} to")
    last = s.tags[-1] if s.tags else None
    indent = re.match(r"\s*", db.lines[last.line]).group(0) if last else (
        re.match(r"\s*", db.lines[s.open_line]).group(0) + "   ")
    db.lines.insert(s.close_line, f'{indent}<{name} {type_}="{value}"/>')


@dataclass
class CampDbPlan:
    mod: object = None
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    text: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"campaign constants in {getattr(self.mod, 'name', '?')} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "ok": not self.errors and bool(self.text)}


def plan(mod, body: dict) -> CampDbPlan:
    """The whole new file, without touching the disk.

    ``body`` is ``{values: {"section/tag": "value"}, add: ["tag", ...]}``. An
    ``add`` names a :data:`VOCAB` tag with a documented default; the value it
    is written with can be given in ``values`` under its key like any other.
    """
    p = CampDbPlan(mod=mod)
    try:
        db, original = read(mod)
    except CampDbError as e:
        p.errors.append(e.message)
        return p
    p.path = path_for(mod)
    values = {str(k): str(v).strip() for k, v in dict(body.get("values") or {}).items()}

    for key, value in values.items():
        t = db.get(key)
        if t is None:
            continue                       # an add, or checked just below
        if value == t.value:
            continue
        err, warn = check_value(t.type, value, t.name)
        if err:
            p.errors.append(f"{key}: {err}")
            continue
        if warn:
            p.warnings.append(f"{key}: {warn}")
        set_value(db, t, value)
        p.changes.append(f"{key}: {t.value} -> {value}")

    for name in [str(n) for n in (body.get("add") or [])]:
        v = VOCAB.get(name)
        if v is None or "default" not in v:
            p.errors.append(f"{name} is not a tag this screen knows how to add")
            continue
        key = f"{v['section']}/{name}"
        if db.get(key) is not None:
            p.errors.append(f"{key} is already in the file")
            continue
        value = values.get(key, v["default"])
        err, warn = check_value(v["type"], value, name)
        if err:
            p.errors.append(f"{key}: {err}")
            continue
        if warn:
            p.warnings.append(f"{key}: {warn}")
        try:
            add_tag(db, v["section"], name, v["type"], value)
        except CampDbError as e:
            p.errors.append(e.message)
            continue
        db = parse_text(db.text())         # line numbers moved
        p.changes.append(f"+ {key} = {value}")

    unknown = [k for k in values if db.get(k) is None]
    if unknown:
        p.errors.append(f"not in the file: {', '.join(unknown[:5])}")
    if p.errors:
        return p

    text = db.text()
    try:
        ET.fromstring(text.encode(ENCODING))
    except ET.ParseError as e:
        p.errors.append(f"the result would not be well-formed XML ({e})")
        return p
    p.text = "" if text == original else text
    if not p.text:
        p.errors.append("nothing to change")
    return p


def apply(p: CampDbPlan) -> Dict:
    """Write a planned save with a backup and an undo, like every other editor."""
    import shutil
    import time

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    target = Path(mod.data) / REL
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    manifest["backed_up"].append(REL)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campdb",
        "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": REL, "resolved_type": REL,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPDB %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
