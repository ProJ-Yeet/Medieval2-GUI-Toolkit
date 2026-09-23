"""``descr_settlement_mechanics.xml`` - how a settlement grows, obeys and pays.

Phase 59, the rest of *Mines and hidden resources* (Phase 45 took the hidden
resources). The file is two lists:

* **factor modifiers** - one ``<factor name="...">`` per engine factor, the
  ``SPF_`` ones behind population growth, ``SOF_`` behind public order and
  ``SIF_`` behind income (``SIF_MINING`` is the mines). Each has a
  ``pip_modifier`` and may add a ``city_modifier``, a ``castle_modifier`` and a
  ``pip_min``/``pip_max`` clamp;
* **population levels** - ``<level name="village" base upgrade min max/>`` for
  the six city levels and five castle ones.

**Measured on both installed mods** (DaC 186 lines, ROCSS 193): 42 live
factors each, no factor twice, and DaC keeps one more commented out - so the
scan skips comments, and anything inside one is the mod's note, not data.
Every level's ``upgrade`` is at most its ``max`` and equals the next level's
``base``. DaC also shows what is NOT a rule: its ``large_city`` has
``upgrade`` 4000 below its ``base`` 16000, and the mod plays.

So the checks are the ones that follow from the numbers alone: a value that
is not a number; ``pip_min`` above ``pip_max``; ``min`` above ``max``; an
``upgrade`` above ``max``, which is a threshold the capped population never
reaches, so the settlement never grows past that level; and, as a note only,
an ``upgrade`` that is not the next level's ``base``.

Like :mod:`campdb`, the file is scanned as text and a save is a splice of the
characters between two quotes, so its comments, spacing and line endings are
its own on the way out; ElementTree is only the gate a save must pass.
"""
from __future__ import annotations

import re
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb

REL = "descr_settlement_mechanics.xml"
ENCODING = "latin-1"

#: what a factor may carry, in the order both mods write them
CHILDREN = ("pip_modifier", "city_modifier", "castle_modifier", "pip_min", "pip_max")
#: the two ladders, bottom to top - the names both mods and the engine use
CITY = ("village", "town", "large_town", "city", "large_city", "huge_city")
CASTLE = ("moot_and_bailey", "wooden_castle", "castle", "fortress", "citadel")
LEVEL_ATTRS = ("base", "upgrade", "min", "max")
#: what each factor family is behind, for the screen
FAMILIES = {"SPF": "Population growth", "SOF": "Public order", "SIF": "Income"}

_NUM = re.compile(r"^-?(\d+(\.\d*)?|\.\d+)$")
_INT = re.compile(r"^\d+$")


class SettleError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class Value:
    key: str                      # "factor/SIF_MINING/pip_modifier", "level/town/base"
    value: str
    start: int                    # the value's characters in the text
    end: int
    line: int


@dataclass
class Factor:
    name: str
    line: int
    values: Dict[str, Value] = field(default_factory=dict)
    #: where the next child line would go, and how it is indented
    insert_at: int = 0
    indent: str = "\t\t\t"


@dataclass
class Level:
    name: str
    line: int
    values: Dict[str, Value] = field(default_factory=dict)


@dataclass
class MechFile:
    text: str
    factors: List[Factor] = field(default_factory=list)
    levels: List[Level] = field(default_factory=list)

    def value(self, key: str) -> Optional[Value]:
        kind, name, attr = (key.split("/") + ["", "", ""])[:3]
        pool = self.factors if kind == "factor" else self.levels if kind == "level" else []
        for x in pool:
            if x.name == name:
                return x.values.get(attr)
        return None

    def factor(self, name: str) -> Optional[Factor]:
        return next((f for f in self.factors if f.name == name), None)


def _line_of(text: str, at: int) -> int:
    return text.count("\n", 0, at)


def parse_text(text: str) -> MechFile:
    """Every live factor and level, with where each value sits."""
    # comments blanked to spaces, so offsets stay the text's own
    live = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    out = MechFile(text=text)
    for m in re.finditer(r'<factor\s+name\s*=\s*"([^"]*)"\s*>(.*?)</factor\s*>', live, re.S):
        f = Factor(name=m.group(1), line=_line_of(text, m.start()))
        body_at = m.start(2)
        last_end = None
        for c in re.finditer(r'<(\w+)\s+value\s*=\s*"([^"]*)"\s*/>', m.group(2)):
            s = body_at + c.start(2)
            f.values[c.group(1)] = Value(f"factor/{f.name}/{c.group(1)}", c.group(2), s,
                                         s + len(c.group(2)), _line_of(text, s))
            last_end = body_at + c.end()
            ls = text.rfind("\n", 0, body_at + c.start()) + 1
            f.indent = re.match(r"[ \t]*", text[ls:]).group(0)
        # a new child goes on its own line after the last one
        f.insert_at = (text.find("\n", last_end) if last_end is not None
                       else text.find("\n", m.start()))
        out.factors.append(f)
    for m in re.finditer(r'<level\s+([^>]*?)/>', live):
        attrs = {a.group(1): a for a in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', m.group(1))}
        if "name" not in attrs:
            continue
        lv = Level(name=attrs["name"].group(2), line=_line_of(text, m.start()))
        base = m.start(1)
        for k, a in attrs.items():
            if k == "name":
                continue
            s = base + a.start(2)
            lv.values[k] = Value(f"level/{lv.name}/{k}", a.group(2), s, s + len(a.group(2)),
                                 _line_of(text, s))
        out.levels.append(lv)
    return out


def path_for(mod) -> Path:
    return Path(mod.data) / REL


def read(mod) -> Tuple[MechFile, str]:
    path = path_for(mod)
    if not path.is_file():
        raise SettleError(f"this mod has no {REL} - the game uses its own, packed")
    text = kb.read_text(path, ENCODING)
    return parse_text(text), text


# ---------------------------------------------------------------------------
# checks


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


def check_value(key: str, value: str) -> str:
    """Why ``value`` cannot go in ``key``, or ""."""
    v = value.strip()
    if key.startswith("level/"):
        return "" if _INT.match(v) else f"{v!r} is not a whole number of people"
    return "" if _NUM.match(v) else f"{v!r} is not a number"


def check_file(mf: MechFile) -> List[Dict]:
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for f in mf.factors:
        if f.name in seen:
            out.append(finding("duplicate", "warn", f"{f.name} is written twice (lines "
                               f"{seen[f.name] + 1} and {f.line + 1}) - one of them is ignored",
                               f"factor/{f.name}", f.line))
        seen.setdefault(f.name, f.line)
        for v in f.values.values():
            why = check_value(v.key, v.value)
            if why:
                out.append(finding("value", "fatal", f"{v.key}: {why}", v.key, v.line))
        lo, hi = f.values.get("pip_min"), f.values.get("pip_max")
        if lo and hi and not check_value(lo.key, lo.value) and not check_value(hi.key, hi.value) \
                and float(lo.value) > float(hi.value):
            out.append(finding("pip_range", "warn", f"{f.name}: pip_min {lo.value} is above "
                               f"pip_max {hi.value}", hi.key, hi.line))
    by = {lv.name: lv for lv in mf.levels}
    for ladder in (CITY, CASTLE):
        for i, name in enumerate(ladder):
            lv = by.get(name)
            if lv is None:
                continue
            nums = {k: int(v.value) for k, v in lv.values.items() if not check_value(v.key, v.value)}
            for v in lv.values.values():
                why = check_value(v.key, v.value)
                if why:
                    out.append(finding("value", "fatal", f"{v.key}: {why}", v.key, v.line))
            if "min" in nums and "max" in nums and nums["min"] > nums["max"]:
                out.append(finding("min_max", "warn", f"{name}: min {nums['min']} is above "
                                   f"max {nums['max']}", f"level/{name}/min", lv.line))
            if "upgrade" in nums and "max" in nums and nums["upgrade"] > nums["max"]:
                out.append(finding("upgrade_max", "warn",
                                   f"{name}: upgrade {nums['upgrade']} is above max "
                                   f"{nums['max']}, which the population never passes - a "
                                   f"{name} never grows into the next level",
                                   f"level/{name}/upgrade", lv.line))
            nxt = by.get(ladder[i + 1]) if i + 1 < len(ladder) else None
            if nxt and "upgrade" in nums:
                nb = nxt.values.get("base")
                if nb and not check_value(nb.key, nb.value) and int(nb.value) != nums["upgrade"]:
                    out.append(finding("chain", "note",
                                       f"{name}: upgrade {nums['upgrade']} is not "
                                       f"{nxt.name}'s base {nb.value} (both installed mods "
                                       f"keep them equal)", f"level/{name}/upgrade", lv.line))
    return out


def overview(mod) -> Dict:
    mf, _ = read(mod)
    fams: Dict[str, List[dict]] = {}
    for f in mf.factors:
        fam = f.name.split("_", 1)[0]
        fams.setdefault(fam, []).append({
            "name": f.name, "line": f.line + 1,
            "values": {k: f.values[k].value for k in CHILDREN if k in f.values}})
    return {
        "file": REL,
        "families": [{"id": k, "label": FAMILIES.get(k, k), "factors": v}
                     for k, v in sorted(fams.items(), key=lambda kv: list(FAMILIES).index(kv[0])
                                        if kv[0] in FAMILIES else 9)],
        "levels": [{"ladder": ladder_name, "levels": [
            {"name": n, "line": by.line + 1,
             "values": {k: by.values[k].value for k in LEVEL_ATTRS if k in by.values}}
            for n in ladder for by in [next((l for l in mf.levels if l.name == n), None)] if by]}
            for ladder_name, ladder in (("city", CITY), ("castle", CASTLE))],
        "children": list(CHILDREN),
        "findings": check_file(mf),
    }


# ---------------------------------------------------------------------------
# the save


@dataclass
class SettlePlan:
    mod: object = None
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    text: str = ""

    def summary(self) -> str:
        head = (f"settlement mechanics in {getattr(self.mod, 'name', '?')} "
                f"({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "ok": not self.errors and bool(self.text)}


def plan(mod, body: dict) -> SettlePlan:
    """``body["values"]``: ``{key: value}``. A factor child the factor lacks is
    added on its own line; an existing factor child given ``""`` is taken out.
    A level's attributes can be changed, not added or taken out."""
    p = SettlePlan(mod=mod)
    try:
        mf, original = read(mod)
    except SettleError as e:
        p.errors.append(e.message)
        return p
    values = {str(k): str(v).strip() for k, v in dict(body.get("values") or {}).items()}
    splices: List[Tuple[int, int, str]] = []
    for key, value in sorted(values.items()):
        v = mf.value(key)
        kind, name, attr = (key.split("/") + ["", "", ""])[:3]
        if v is not None:
            if value == v.value:
                continue
            if value == "" and kind == "factor" and attr != "pip_modifier":
                ls = original.rfind("\n", 0, v.start) + 1
                le = original.find("\n", v.end)
                splices.append((ls, le + 1 if le >= 0 else len(original), ""))
                p.changes.append(f"- {key} (was {v.value})")
                continue
            why = check_value(key, value)
            if why:
                p.errors.append(f"{key}: {why}")
                continue
            splices.append((v.start, v.end, value))
            p.changes.append(f"{key}: {v.value} -> {value}")
            continue
        f = mf.factor(name) if kind == "factor" else None
        if f is None or attr not in CHILDREN:
            p.errors.append(f"{key} is not in the file, and not something this screen adds")
            continue
        if value == "":
            continue
        why = check_value(key, value)
        if why:
            p.errors.append(f"{key}: {why}")
            continue
        nl = "\r\n" if "\r\n" in original else "\n"
        at = f.insert_at if f.insert_at >= 0 else len(original)
        # the line break we insert after sits before the \r of a CRLF, so step past it
        if nl == "\r\n" and at > 0 and original[at - 1] == "\r":
            at -= 1
        splices.append((at, at, f'{nl}{f.indent}<{attr} value="{value}"/>'))
        p.changes.append(f"+ {key} = {value}")
    if p.errors:
        return p
    text = original
    for s, e, new in sorted(splices, key=lambda x: (x[0], x[1]), reverse=True):
        text = text[:s] + new + text[e:]
    try:
        ET.fromstring(text.encode(ENCODING))
    except ET.ParseError as e:
        p.errors.append(f"the result would not be well-formed XML ({e})")
        return p
    for f in check_file(parse_text(text)):
        if f["severity"] == "warn" and f not in check_file(mf):
            p.warnings.append(f["message"])
    if text == original:
        p.errors.append("nothing to change")
        return p
    p.text = text
    return p


def apply(p: SettlePlan) -> Dict:
    """Write a planned save with a backup and an undo, like every other editor."""
    from . import config
    from .logutil import file_op, log

    if p.errors or not p.text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    target = path_for(mod)
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "settlemech", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": REL, "resolved_type": REL,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": {"backed_up": [REL], "created": []}, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SETTLE %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
