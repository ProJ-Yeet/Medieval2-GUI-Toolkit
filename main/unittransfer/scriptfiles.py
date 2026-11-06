"""The two file add-ons of the Scripts screen: they change the mod's own game
files instead of installing a script, and need no scripting engine.

* ``upkeep``  - "Upkeep x N": multiplies every unit's upkeep in
  export_descr_unit.txt.
* ``onegrid`` - "One Recruitment Grid": sets the campaign constant
  ``recruitment_sort_simple`` in descr_campaign_db.xml.

Neither writes anything itself: each stages its changes into a
``scriptcompat.Plan``, and the caller runs it (every file backed up, one entry
in the Log to Undo). Each leaves a small JSON note beside the changed file so
that taking the add-on out restores exactly the old values.

Written independently from a description of the behaviour (2026-11-06); the
add-ons follow Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from . import campdb, vanilla
from . import i18n as _i18n

_UPKEEP_NOTE = "toolkit_upkeep.json"
_GRID_NOTE = "toolkit_onegrid.json"
_RULE = "recruitment/recruitment_sort_simple"

_TYPE_LINE = re.compile(r"^\s*type\s+([^;]*)", re.IGNORECASE)
_COST_LINE = re.compile(r"^(\s*stat_cost\b\s*)([^;]*)(.*)$", re.IGNORECASE)
_NUMBER = re.compile(r"^(\s*)(-?\d+(?:\.\d+)?)(\s*)$")


# ---------------------------------------------------------------------------
# small helpers


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("utf-8")


def _read_json(raw: Optional[bytes]) -> Optional[dict]:
    if raw is None:
        return None
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _disk_json(path: str) -> Optional[dict]:
    try:
        with open(path, "rb") as fh:
            return _read_json(fh.read())
    except OSError:
        return None


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _whole(x: float):
    return int(x) if float(x) == int(x) else float(x)


# ---------------------------------------------------------------------------
# upkeep


def _upkeep_mark(mod) -> str:
    return os.path.join(str(mod.data), _UPKEEP_NOTE)


def _upkeep_installed(mod) -> Optional[dict]:
    path = _upkeep_mark(mod)
    if not os.path.exists(path):
        return None
    note = _disk_json(path)
    try:
        return {"FACTOR": str(note["factor"])}
    except (TypeError, KeyError):
        return {"FACTOR": "2.0"}


def _edu_lines(plan) -> Tuple[str, List[str], str]:
    path = str(plan.mod.edu_path)
    raw = plan.stored(path)
    if raw is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_file", "this mod has no {name}",
                                   name=os.path.basename(path)))
    text = raw.decode("latin-1")
    sep = "\r\n" if "\r\n" in text else "\n"
    return path, text.split(sep), sep


def _costs(lines: List[str]):
    """Yield (line index, unit name, prefix, parts, number match, tail) for
    every stat_cost line that follows a type line and has a usable third
    number."""
    unit = None
    for i, line in enumerate(lines):
        t = _TYPE_LINE.match(line)
        if t:
            unit = t.group(1).strip()
            continue
        c = _COST_LINE.match(line)
        if c is None or unit is None:
            continue
        parts = c.group(2).split(",")
        if len(parts) < 3:
            continue
        n = _NUMBER.match(parts[2])
        if n is None:
            continue
        yield i, unit, c.group(1), parts, n, c.group(3)


def _put(lines: List[str], i: int, prefix: str, parts: List[str], n, tail: str, value) -> None:
    parts = list(parts)
    parts[2] = n.group(1) + str(value) + n.group(3)
    lines[i] = prefix + ",".join(parts) + tail


def _upkeep_install(plan, factor="2.0", **_ignored) -> None:
    f = float(factor)
    if f <= 0:
        raise ValueError(_i18n.msg("eng.scriptfiles.factor",
                                   "the upkeep is multiplied by a number above 0"))
    path, lines, sep = _edu_lines(plan)
    mark = _upkeep_mark(plan.mod)
    old = (_read_json(plan.stored(mark)) or {}).get("units")
    old = old if isinstance(old, dict) else {}
    units: Dict[str, list] = {}
    changed = 0
    for i, unit, prefix, parts, n, tail in list(_costs(lines)):
        now = float(n.group(2))
        base = now
        rec = old.get(unit)
        if isinstance(rec, list) and len(rec) == 2 and _is_num(rec[1]) and float(rec[1]) == now:
            base = float(rec[0])
        new = int(round(base * f))
        units[unit] = [_whole(base), new]
        if new != now:
            _put(lines, i, prefix, parts, n, tail, new)
            changed += 1
    if not units:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_cost",
                                   "no stat_cost line found in export_descr_unit.txt"))
    plan.binary(path, sep.join(lines).encode("latin-1"))
    plan.binary(mark, _json_bytes({"factor": f, "units": units}))
    plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_done",
                              "upkeep x {f}: {n} unit(s) changed, the old numbers kept in {mark}",
                              f="%g" % f, n=changed, mark=_UPKEEP_NOTE))


def _upkeep_remove(plan) -> None:
    mark = _upkeep_mark(plan.mod)
    units = (_read_json(plan.stored(mark)) or {}).get("units")
    if not isinstance(units, dict) or not units:
        raise ValueError(_i18n.msg("eng.scriptfiles.upkeep_not_in",
                                   "Upkeep x N is not in this mod"))
    path, lines, sep = _edu_lines(plan)
    left: List[str] = []
    for i, unit, prefix, parts, n, tail in list(_costs(lines)):
        rec = units.get(unit)
        if not (isinstance(rec, list) and len(rec) == 2 and _is_num(rec[0]) and _is_num(rec[1])):
            continue
        now = float(n.group(2))
        if now == float(rec[1]):
            if now != float(rec[0]):
                _put(lines, i, prefix, parts, n, tail, rec[0])
        elif unit not in left:
            left.append(unit)
    plan.binary(path, sep.join(lines).encode("latin-1"))
    plan.delete(mark, "Upkeep x N")
    plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_back", "upkeep back to the old numbers"))
    if left:
        plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_left",
                                  "left as it is now (changed after the add-on went in): {units}",
                                  units=", ".join(left[:20])))


upkeep = SimpleNamespace(mark_path=_upkeep_mark, installed=_upkeep_installed,
                         plan_install=_upkeep_install, plan_remove=_upkeep_remove)


# ---------------------------------------------------------------------------
# one recruitment grid


def _grid_mark(mod) -> str:
    return os.path.join(str(mod.data), _GRID_NOTE)


def _grid_installed(mod) -> Optional[dict]:
    return {} if os.path.exists(_grid_mark(mod)) else None


def _grid_source(plan) -> Tuple[str, str, bool]:
    """(the mod's own path, the XML text to work from, whether the mod has it)."""
    own = os.path.join(str(plan.mod.data), campdb.REL)
    raw = plan.stored(own)
    if raw is not None:
        return own, raw.decode(campdb.ENCODING), True
    text = vanilla.text(campdb.REL, plan.mod)
    if text is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_campdb",
                                   "this mod and its game have no {name}", name=campdb.REL))
    return own, text, False


def _grid_install(plan, **_ignored) -> None:
    mark = _grid_mark(plan.mod)
    if plan.stored(mark) is not None:
        raise ValueError(_i18n.msg("eng.scriptfiles.grid_in",
                                   "One Recruitment Grid is in this mod already"))
    own, text, had = _grid_source(plan)
    db = campdb.parse_text(text)
    tag = db.get(_RULE)
    if tag is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_rule",
                                   "{name} has no <recruitment_sort_simple> line", name=campdb.REL))
    was = str(tag.value)
    campdb.set_value(db, tag, "true")
    plan.binary(mark, _json_bytes({"was": was, "own_file": had}))
    plan.binary(own, db.text().encode(campdb.ENCODING))
    plan.note(None, _i18n.msg("eng.scriptfiles.grid_done",
                              "descr_campaign_db.xml: recruitment_sort_simple set to true"))


def _grid_remove(plan) -> None:
    mark = _grid_mark(plan.mod)
    note = _read_json(plan.stored(mark))
    if note is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.grid_not_in",
                                   "One Recruitment Grid is not in this mod"))
    plan.delete(mark, "One Recruitment Grid")
    own, text, had = _grid_source(plan)
    if had and note.get("own_file") is False:
        plan.delete(own, _i18n.msg("eng.scriptfiles.grid_copy",
                                   "the copy One Recruitment Grid put in"))
        return
    db = campdb.parse_text(text)
    tag = db.get(_RULE)
    if tag is not None:
        campdb.set_value(db, tag, str(note.get("was", "false")))
    plan.binary(own, db.text().encode(campdb.ENCODING))


onegrid = SimpleNamespace(mark_path=_grid_mark, installed=_grid_installed,
                          plan_install=_grid_install, plan_remove=_grid_remove)
