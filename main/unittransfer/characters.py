"""``descr_character.txt`` - what each agent is, and what it looks like (Phase 69).

Twelve ``type`` sections (named character, general, the agents, princess,
admiral, heretic, witch, inquisitor), each with its ``actions``,
``wage_base`` and ``starting_action_points``, then one block per faction: its
``dictionary``, its ``strat_model`` lines (the campaign-map model, from
``descr_model_strat.txt``; a named character has one for default, heir and
leader and may have more), and for the two that fight, a ``battle_model``
(from ``battle_models.modeldb``) and its ``battle_equip``.

Six modules read this file and none wrote it: the faction audit, the faction
clone, the rename, the BMDB and strat-model audits, and the Lua scan. **This
is the join the roadmap asked for**: the Strat models screen named a model
"used by character:spy" and could not say which faction or open it, and
nothing here led from a character to the model it draws. Now a strat model's
card lists every block that draws it, as a link, and this screen links each
of a block's models to its screen.

**Read as lines.** The file has no braces: a ``type`` line starts a section,
a ``faction`` line starts a block, and every other line is ``keyword value``.
Values are edited in place keeping the indent, the column and the comment
(``strat_model gondor_general ; 1 (Heir)`` keeps its label), a strat model
can be added after the block's last or removed, and a faction's block copied
for another faction or removed. Line endings are the file's own.

**Measured on both installed mods before any rule was written** (ROCSS 1 524
lines, 30 factions; DaC 1 707 lines, 31):

* Every ``strat_model`` is an entry of ``descr_model_strat.txt``, every
  ``battle_model`` an entry of the modeldb, every ``faction`` a slot in the
  roster. A miss is a warning.
* DaC lists ``england`` twice under ``inquisitor``: a warning, since only one
  of the two blocks can be the one read.
* Every named character block has at least three strat models (default, heir,
  leader; ROCSS three or four, DaC up to eleven), every named character and
  general block a ``battle_model``, every block at least one strat model.
  Warnings when they fail.
* Which types a faction has is not a rule: ``slave`` has no diplomat,
  princess or priest in ROCSS, heretics and witches are the rebels' alone in
  both, and ROCSS gives inquisitors to 16 factions of 30. The screen shows the
  grid of types by faction instead, and the faction audit already has its
  *Agents and generals* row.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import keyblock as kb

REL = "descr_character.txt"
ENCODING = "latin-1"
TYPES = ("named character", "general", "spy", "assassin", "diplomat", "admiral", "princess",
         "merchant", "priest", "heretic", "witch", "inquisitor")
#: the types a battle model is written for, in both installed mods
FIGHTERS = ("named character", "general")
HEAD_KEYS = ("actions", "wage_base", "starting_action_points")
BLOCK_KEYS = ("dictionary", "strat_model", "battle_model", "battle_equip")
NUMBERS = ("wage_base", "starting_action_points", "dictionary")
_SLOT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_TOKEN = re.compile(r"[^\s,;]+")


class CharError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    """``line`` is 0-based; the finding's is 1-based."""
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


@dataclass
class Row:
    line: int                 # 0-based
    key: str
    value: str
    label: str = ""           # the comment after it, e.g. `0 (Default)`


@dataclass
class Block:
    """One faction's block in a type section."""
    line: int
    end: int                  # the last line that belongs to it (0-based)
    factions: List[str]
    rows: List[Row] = field(default_factory=list)

    def values(self, key: str) -> List[str]:
        return [r.value for r in self.rows if r.key == key]

    def first(self, key: str) -> str:
        v = self.values(key)
        return v[0] if v else ""


@dataclass
class Section:
    name: str
    line: int
    end: int
    head: List[Row] = field(default_factory=list)
    blocks: List[Block] = field(default_factory=list)


@dataclass
class Doc:
    text: str
    lines: List[str]          # split on "\n", each keeping its own "\r"
    sections: List[Section]
    #: lines above the first `type`, in order - the file's own notes
    preamble: int = 0


def _split(line: str) -> Tuple[str, str, str]:
    """``(keyword, value, label)`` of one line: the comment is the label."""
    body = line.rstrip("\r")
    code, _sep, comment = body.partition(";")
    code = kb.without_bom(code).strip()
    parts = code.split(None, 1)
    return (parts[0].lower() if parts else "", parts[1].strip() if len(parts) > 1 else "",
            comment.strip())


def parse(text: str) -> Doc:
    lines = text.split("\n")
    sections: List[Section] = []
    sec: Optional[Section] = None
    blk: Optional[Block] = None
    for i, line in enumerate(lines):
        key, value, label = _split(line)
        if not key:
            continue
        if key == "type":
            sec = Section(value, i, i)
            sections.append(sec)
            blk = None
            continue
        if sec is None:
            continue
        sec.end = i
        if key == "faction":
            blk = Block(i, i, [f for f in kb.split_list(value)])
            sec.blocks.append(blk)
            continue
        row = Row(i, key, value, label)
        if blk is None:
            sec.head.append(row)
        else:
            blk.rows.append(row)
            blk.end = i
    return Doc(text, lines, sections)


# ---------------------------------------------------------------------------
# what the file is held against


class Refs:
    """What the checks hold the characters against; ``None`` skips a rule."""

    def __init__(self, roster=None, strat=None, battle=None):
        self.roster: Optional[List[str]] = roster
        self.strat: Optional[Set[str]] = strat
        self.battle: Optional[Set[str]] = battle

    @classmethod
    def of(cls, mod) -> "Refs":
        from . import factions as fa, stratmap
        try:
            path = fa.path_for(mod)
            roster = [fa.slot_of(r.name).lower() for r in fa.parse_file(path).records] \
                if path.is_file() else None
        except Exception:
            roster = None
        try:
            strat = {e.name.lower() for e in stratmap.strat_file(mod).entries} or None
        except Exception:
            strat = None
        try:
            battle = set(mod.modeldb.by_name()) or None
        except Exception:
            battle = None
        return cls(roster, strat, battle)


# ---------------------------------------------------------------------------
# the model the page draws


def _key(sec: Section, blk: Block) -> str:
    """A block's address: its faction line, since DaC has two blocks for one
    faction in one type. The page also opens ``<type>/<faction>``."""
    return f"block/{blk.line + 1}"


def view(doc: Doc) -> List[Dict]:
    out = []
    for s in doc.sections:
        out.append({
            "type": s.name, "line": s.line + 1,
            "head": [{"line": r.line + 1, "key": r.key, "value": r.value} for r in s.head],
            "blocks": [{"key": _key(s, b), "line": b.line + 1, "factions": b.factions,
                        "rows": [{"line": r.line + 1, "key": r.key, "value": r.value,
                                  "label": r.label} for r in b.rows]}
                       for b in s.blocks]})
    return out


def model_users(doc: Doc) -> Dict[str, List[Dict]]:
    """``lower strat model -> [{type, faction, key, slot, label}]``: the join
    the Strat models screen draws."""
    out: Dict[str, List[Dict]] = {}
    for s in doc.sections:
        for b in s.blocks:
            for n, r in enumerate(x for x in b.rows if x.key == "strat_model"):
                name = r.value.split()[0] if r.value else ""
                if name:
                    out.setdefault(name.lower(), []).append(
                        {"type": s.name, "faction": ", ".join(b.factions), "key": _key(s, b),
                         "slot": n, "label": r.label})
    return out


# ---------------------------------------------------------------------------
# checking


def check(doc: Doc, refs: Optional[Refs] = None) -> List[Dict]:
    refs = refs or Refs()
    out: List[Dict] = []
    if not doc.sections:
        out.append(finding("empty", "fatal", f"{REL} has no type section", "file", 0))
    seen_types: Dict[str, int] = {}
    for s in doc.sections:
        low = s.name.lower()
        if low in seen_types:
            out.append(finding("type", "warn", f"type {s.name} is written twice (lines "
                               f"{seen_types[low]} and {s.line + 1})", f"type/{s.name}", s.line))
        seen_types.setdefault(low, s.line + 1)
        if low not in TYPES:
            out.append(finding("type", "note", f"type {s.name} is not one of the "
                               f"{len(TYPES)} character types", f"type/{s.name}", s.line))
        for r in s.head:
            if r.key in NUMBERS and not kb.is_int(r.value):
                out.append(finding("number", "fatal", f"{s.name}: {r.key} {r.value!r} is not a "
                                   "whole number", f"type/{s.name}", r.line))
        if not any(r.key == "actions" for r in s.head):
            out.append(finding("actions", "warn", f"{s.name} has no actions line, so it can do "
                               "nothing", f"type/{s.name}", s.line))
        seen: Dict[str, int] = {}
        for b in s.blocks:
            key = _key(s, b)
            who = f"{s.name}, {', '.join(b.factions) or 'a block with no faction'}"
            if not b.factions:
                out.append(finding("faction", "fatal", f"{s.name}: line {b.line + 1} is a faction "
                                   "line with no faction", key, b.line))
            for f in b.factions:
                fl = f.lower()
                if fl in seen:
                    out.append(finding("duplicate", "warn", f"{s.name}: {f} has two blocks (lines "
                                       f"{seen[fl]} and {b.line + 1}); only one of them is read",
                                       key, b.line))
                seen.setdefault(fl, b.line + 1)
                if refs.roster is not None and fl not in refs.roster:
                    out.append(finding("roster", "warn", f"{who}: {f} is not a faction in "
                                       "descr_sm_factions.txt", key, b.line))
            for r in b.rows:
                if r.key in NUMBERS and not kb.is_int(r.value):
                    out.append(finding("number", "fatal", f"{who}: {r.key} {r.value!r} is not a "
                                       "whole number", key, r.line))
                elif r.key == "strat_model":
                    name = r.value.split()[0] if r.value else ""
                    if not name:
                        out.append(finding("strat", "fatal", f"{who}: a strat_model with no "
                                           "model", key, r.line))
                    elif refs.strat is not None and name.lower() not in refs.strat:
                        out.append(finding("strat", "warn", f"{who}: strat_model {name} is not "
                                           "an entry of descr_model_strat.txt", key, r.line))
                elif r.key == "battle_model":
                    if refs.battle is not None and r.value.lower() not in refs.battle:
                        out.append(finding("battle", "warn", f"{who}: battle_model {r.value} is "
                                           "not an entry of the modeldb", key, r.line))
                elif r.key not in BLOCK_KEYS:
                    out.append(finding("key", "note", f"{who}: {r.key} is not a line a block "
                                       "carries in either installed mod", key, r.line))
            models = b.values("strat_model")
            if not models:
                out.append(finding("strat", "warn", f"{who} has no strat_model, so it has nothing "
                                   "to stand on the map with", key, b.line))
            elif low == "named character" and len(models) < 3:
                out.append(finding("strat", "warn", f"{who} has {len(models)} strat model(s); a "
                                   "named character has one each for default, heir and leader",
                                   key, b.line))
            if low in FIGHTERS and not b.values("battle_model"):
                out.append(finding("battle", "warn", f"{who} has no battle_model, so it has no "
                                   "model to fight with", key, b.line))
    return out


# ---------------------------------------------------------------------------
# reading a mod


def _read(mod) -> str:
    path = Path(mod.data) / REL
    if not path.is_file():
        raise CharError(f"this mod has no {REL}")
    return kb.read_text(path, ENCODING)


def overview(mod) -> Dict:
    out: Dict = {"file": REL, "types": [], "findings": [], "roster": [], "known_types": TYPES}
    try:
        text = _read(mod)
    except CharError as e:
        out["error"] = e.message
        return out
    doc = parse(text)
    refs = Refs.of(mod)
    out["types"] = view(doc)
    out["roster"] = refs.roster or []
    out["strat_models"] = sorted(refs.strat or [])
    out["battle_models"] = sorted(refs.battle or [])
    out["sig"] = _sig(text)
    out["findings"] = check(doc, refs)
    return out


def users_of(mod, strat_model: str) -> List[Dict]:
    """The blocks that draw ``strat_model``: for the Strat models card."""
    try:
        return model_users(parse(_read(mod))).get((strat_model or "").lower(), [])
    except CharError:
        return []


# ---------------------------------------------------------------------------
# editing


@dataclass
class CharPlan:
    mod: object = None
    text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": [REL] if self.text else [], "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.text)}


def _eol(line: str) -> str:
    return "\r" if line.endswith("\r") else ""


def _valid(key: str, value: str, refs: Refs) -> Tuple[str, str]:
    """``(error, warning)`` for one value."""
    if ";" in value:
        return f"{key}: ; starts a comment, and cannot go in a value", ""
    if key in NUMBERS:
        return ("", "") if kb.is_int(value) else (f"{key} is a whole number, not {value!r}", "")
    if key == "strat_model":
        if not _TOKEN.fullmatch(value):
            return "a strat_model is one model's name", ""
        if refs.strat is not None and value.lower() not in refs.strat:
            return "", f"{value} is not an entry of descr_model_strat.txt"
    if key == "battle_model":
        if not _TOKEN.fullmatch(value):
            return "a battle_model is one entry's name", ""
        if refs.battle is not None and value.lower() not in refs.battle:
            return "", f"{value} is not an entry of the modeldb"
    if key == "actions":
        acts = kb.split_list(value)
        if not acts or any(not _SLOT.fullmatch(a) for a in acts):
            return "actions is a list of words, with commas between them", ""
    return "", ""


def plan(mod, body: dict) -> CharPlan:
    """``values``: ``{line (1-based): value}``; ``add_model``: ``[{block: its
    faction line, model}]`` (after the block's last strat_model);
    ``remove``: ``[line]`` - a strat_model line, or a block's faction line to
    take the whole block; ``copy_block``: ``[{block: its faction line,
    faction}]`` - a block copied for another faction, after the section's
    last block; ``sig``."""
    p = CharPlan(mod=mod)
    try:
        text = _read(mod)
    except CharError as e:
        p.errors.append(e.message)
        return p
    if str(body.get("sig") or "") != _sig(text):
        p.errors.append(f"{REL} changed on disk after it was opened here - reload it")
        return p
    doc = parse(text)
    refs = Refs.of(mod)
    lines = doc.lines
    rows: Dict[int, Tuple[Section, Optional[Block], Row]] = {}
    blocks: Dict[int, Tuple[Section, Block]] = {}
    for s in doc.sections:
        for r in s.head:
            rows[r.line] = (s, None, r)
        for b in s.blocks:
            blocks[b.line] = (s, b)
            for r in b.rows:
                rows[r.line] = (s, b, r)
    rewrites: Dict[int, str] = {}
    drops: Set[int] = set()
    inserts: Dict[int, List[str]] = {}

    def where(s: Section, b: Optional[Block]) -> str:
        return f"{s.name}" + (f", {', '.join(b.factions)}" if b else "")

    for key, v in (body.get("values") or {}).items():
        i = int(key) - 1
        hit = rows.get(i)
        if hit is None:
            p.errors.append(f"line {key} is not a keyword and its value")
            continue
        s, b, r = hit
        v = " ".join(str(v).split())
        if r.key == "actions":
            v = ", ".join(kb.split_list(v))
        err, warn = _valid(r.key, v, refs)
        if err:
            p.errors.append(f"{where(s, b)}: {err}")
            continue
        if warn:
            p.warnings.append(f"{where(s, b)}: {warn}")
        if v == r.value:
            continue
        body_line = lines[i].rstrip("\r")
        rewrites[i] = kb.sub_value(body_line, body_line.split()[0], v) + _eol(lines[i])
        p.changes.append(f"{where(s, b)}: {r.key} {r.value} -> {v}")
    for spec in body.get("add_model") or []:
        at = int(spec.get("block") or 0) - 1
        model = str(spec.get("model") or "").strip()
        hit = blocks.get(at)
        if hit is None:
            p.errors.append("a strat model is added to a faction's block")
            continue
        s, b = hit
        err, warn = _valid("strat_model", model, refs)
        if err:
            p.errors.append(err)
            continue
        if warn:
            p.warnings.append(f"{where(s, b)}: {warn}")
        last = max((r.line for r in b.rows if r.key == "strat_model"), default=b.line)
        like = lines[last]
        prefix = kb.head_prefix(like.rstrip("\r"), "strat_model") if last != b.line \
            else kb.indent_of(like) + "strat_model\t\t"
        n = len(b.values("strat_model"))
        inserts.setdefault(last, []).append(f"{prefix}{model} ; {n} (Custom){_eol(like)}")
        p.changes.append(f"+ {where(s, b)}: strat_model {model}, slot {n}")
    for key in body.get("remove") or []:
        i = int(key) - 1
        if i in blocks:
            s, b = blocks[i]
            if len(s.blocks) < 2:
                p.errors.append(f"{s.name} keeps at least one block")
                continue
            end = b.end
            # the blank lines after a block go with it, up to the next one
            while end + 1 < len(lines) and not lines[end + 1].strip() \
                    and end + 1 not in blocks and end + 1 < s.end:
                end += 1
            drops |= set(range(b.line, end + 1))
            p.changes.append(f"- {where(s, b)}: the whole block")
            continue
        hit = rows.get(i)
        if hit is None or hit[2].key != "strat_model" or hit[1] is None:
            p.errors.append(f"line {key} is not a strat_model or a faction's block")
            continue
        s, b, r = hit
        if len(b.values("strat_model")) < 2:
            p.errors.append(f"{where(s, b)} keeps at least one strat model")
            continue
        drops.add(i)
        p.changes.append(f"- {where(s, b)}: strat_model {r.value}")
    for spec in body.get("copy_block") or []:
        at = int(spec.get("block") or 0) - 1
        fac = str(spec.get("faction") or "").strip()
        hit = blocks.get(at)
        if hit is None:
            p.errors.append("a block is copied from a faction's block")
            continue
        s, b = hit
        if not _SLOT.fullmatch(fac):
            p.errors.append(f"{fac!r} is not a faction slot")
            continue
        if any(fac.lower() == f.lower() for x in s.blocks for f in x.factions):
            p.errors.append(f"{s.name} already has a block for {fac}")
            continue
        if refs.roster is not None and fac.lower() not in refs.roster:
            p.warnings.append(f"{fac} is not a faction in descr_sm_factions.txt")
        chunk = lines[b.line:b.end + 1]
        chunk[0] = kb.sub_value(chunk[0].rstrip("\r"), chunk[0].split()[0], fac) + _eol(chunk[0])
        last = s.blocks[-1].end
        nl_line = _eol(lines[last])
        inserts.setdefault(last, []).extend([nl_line] + chunk)
        p.changes.append(f"+ {s.name}: {fac}, a block copied from {', '.join(b.factions)}")
    if p.errors:
        return p
    out: List[str] = []
    for i, ln in enumerate(lines):
        if i not in drops:
            out.append(rewrites.get(i, ln))
        out += inserts.get(i, [])
    new = "\n".join(out)
    if new == text:
        p.errors.append("nothing to change")
        return p
    p.text = new
    was = {f["message"] for f in check(doc, refs)}
    p.warnings += [f["message"] for f in check(parse(new), refs)
                   if f["severity"] != "note" and f["message"] not in was
                   and f["message"] not in p.warnings]
    return p


def apply(p: CharPlan) -> Dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    target = Path(mod.data) / REL
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "characters", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": REL, "resolved_type": REL,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": {"backed_up": [REL], "created": []}, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CHARS  %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
