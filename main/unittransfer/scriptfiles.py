"""The two add-ons that change the mod's own files instead of putting a script in (96e1, round two).

The Pfadfinder-Adam (formerly MasterOogwayHomebrew) campaign editor's
``upkeep.py`` and ``onegrid.py``, taken with its author's permission and
rewritten onto this toolkit's text handling and :class:`scriptcompat.Plan`.
Neither needs an engine; both keep what was there in a small note beside the
file, so Take it out puts back exactly the old values.

* **Upkeep x N**: every unit's upkeep (``stat_cost``'s third number in
  export_descr_unit.txt) multiplied. A unit whose upkeep the modder changed
  after it went in is left as it is on Take it out, and named.
* **One Recruitment Grid**: ``<recruitment_sort_simple>`` in
  descr_campaign_db.xml set to true, so a town's recruitment panel is one grid
  read row by row, as in Rome. A mod with no copy of the file gets the game's
  own, and loses it again on Take it out.
"""
from __future__ import annotations

import json
import os
import re
import types
from pathlib import Path

from . import i18n as _i18n

RE_COST = re.compile(r"^(\s*stat_cost\b\s*)([^;\r\n]*)(.*)$", re.S)
RE_TYPE = re.compile(r"^\s*type\s+(.+?)\s*(;.*)?$")


def _text(plan, path) -> str:
    raw = plan.stored(path)
    if raw is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_file", "this mod has no {name}", name=os.path.basename(path)))
    return raw.decode("latin-1")


# ---------------------------------------------------------------------------
# Upkeep x N

_UPKEEP_MARK = "toolkit_upkeep.json"


def _up_mark(mod):
    return os.path.join(mod.data, _UPKEEP_MARK)


def _up_record(mod):
    try:
        with open(_up_mark(mod), encoding="utf-8") as fh:
            return json.load(fh).get("units", {})
    except (OSError, ValueError):
        return {}


def _up_lines(lines):
    out, unit = [], None
    for i, t in enumerate(lines):
        m = RE_TYPE.match(t)
        if m:
            unit = m.group(1).strip()
            continue
        m = RE_COST.match(t)
        if m and unit:
            out.append((i, unit, m))
    return out


def _with_upkeep(m, value):
    parts = m.group(2).split(",")
    if len(parts) < 3:
        return None
    old = parts[2]
    parts[2] = old[:len(old) - len(old.lstrip())] + str(value) + old[len(old.rstrip()):]
    return m.group(1) + ",".join(parts) + m.group(3)


def _upkeep_of(m):
    try:
        return int(float(m.group(2).split(",")[2]))
    except (IndexError, ValueError):
        return None


def _up_installed(mod):
    if not os.path.isfile(_up_mark(mod)):
        return None
    try:
        with open(_up_mark(mod), encoding="utf-8") as fh:
            return {"FACTOR": str(json.load(fh).get("factor", 2.0))}
    except (OSError, ValueError):
        return {"FACTOR": "2.0"}


def _up_install(plan, factor="2.0"):
    factor = float(factor)
    if factor <= 0:
        raise ValueError(_i18n.msg("eng.scriptfiles.factor", "the upkeep is multiplied by a number above 0"))
    mod = plan.mod
    rec = _up_record(mod)
    path = str(mod.edu_path)
    text = _text(plan, path)
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    units, changed = {}, 0
    for i, unit, m in _up_lines(lines):
        now = _upkeep_of(m)
        if now is None:
            continue
        was = rec.get(unit)
        base = was[0] if was and was[1] == now else now
        new = int(round(base * factor))
        units[unit] = [base, new]
        if new != now:
            lines[i] = _with_upkeep(m, new)
            changed += 1
    if not units:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_cost", "no stat_cost line found in export_descr_unit.txt"))
    plan.binary(path, nl.join(lines).encode("latin-1"))
    plan.binary(_up_mark(mod), (json.dumps({"factor": factor, "units": units}, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_done", "upkeep x {f}: {n} unit(s) changed, the old numbers kept in {mark}", f=f"{factor:g}", n=changed, mark=_UPKEEP_MARK))


def _up_remove(plan):
    mod = plan.mod
    rec = _up_record(mod)
    if not rec:
        raise ValueError(_i18n.msg("eng.scriptfiles.upkeep_not_in", "Upkeep x N is not in this mod"))
    path = str(mod.edu_path)
    text = _text(plan, path)
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    left = []
    for i, unit, m in _up_lines(lines):
        was, now = rec.get(unit), _upkeep_of(m)
        if not was or now is None:
            continue
        if now == was[1]:
            if was[0] != now:
                lines[i] = _with_upkeep(m, was[0])
        else:
            left.append(unit)
    plan.binary(path, nl.join(lines).encode("latin-1"))
    plan.delete(_up_mark(mod), "Upkeep x N")
    plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_back", "upkeep back to the old numbers"))
    if left:
        plan.note(None, _i18n.msg("eng.scriptfiles.upkeep_left", "left as it is now (changed after the add-on went in): {units}", units=", ".join(left[:20])))


upkeep = types.SimpleNamespace(mark_path=_up_mark, installed=_up_installed,
                               plan_install=lambda plan, factor="2.0", **_k: _up_install(plan, factor),
                               plan_remove=_up_remove)


# ---------------------------------------------------------------------------
# One Recruitment Grid

_GRID_MARK = "toolkit_onegrid.json"
_KEY = "recruitment/recruitment_sort_simple"


def _grid_mark(mod):
    return os.path.join(mod.data, _GRID_MARK)


def _grid_installed(mod):
    return {} if os.path.isfile(_grid_mark(mod)) else None


def _campdb(plan):
    """(the file's text, its path, whether the mod had its own copy)."""
    from . import campdb, vanilla
    path = os.path.join(plan.mod.data, campdb.REL)
    raw = plan.stored(path)
    if raw is not None:
        return raw.decode(campdb.ENCODING), path, True
    text = vanilla.text(campdb.REL, plan.mod)
    if text is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_campdb", "this mod and its game have no {name}", name=campdb.REL))
    return text, path, False


def _set(text: str, value: str) -> str:
    from . import campdb
    db = campdb.parse_text(text)
    tag = db.get(_KEY)
    if tag is None:
        raise ValueError(_i18n.msg("eng.scriptfiles.no_rule", "{name} has no <recruitment_sort_simple> line", name=campdb.REL))
    campdb.set_value(db, tag, value)
    return db.text()


def _grid_install(plan, **_k):
    from . import campdb
    if _grid_installed(plan.mod) is not None:
        raise ValueError(_i18n.msg("eng.scriptfiles.grid_in", "One Recruitment Grid is in this mod already"))
    text, path, own = _campdb(plan)
    was = campdb.parse_text(text).get(_KEY)
    plan.binary(_grid_mark(plan.mod), (json.dumps({"was": was.value if was else "false", "own_file": own}, indent=1) + "\n").encode("utf-8"))
    plan.binary(path, _set(text, "true").encode(campdb.ENCODING))
    plan.note(None, _i18n.msg("eng.scriptfiles.grid_done", "descr_campaign_db.xml: recruitment_sort_simple set to true"))


def _grid_remove(plan):
    from . import campdb
    try:
        with open(_grid_mark(plan.mod), encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        raise ValueError(_i18n.msg("eng.scriptfiles.grid_not_in", "One Recruitment Grid is not in this mod")) from None
    text, path, own = _campdb(plan)
    plan.delete(_grid_mark(plan.mod), "One Recruitment Grid")
    if own and not rec.get("own_file", True):
        plan.delete(path, _i18n.msg("eng.scriptfiles.grid_copy", "the copy One Recruitment Grid put in"))
        return
    plan.binary(path, _set(text, str(rec.get("was", "false"))).encode(campdb.ENCODING))


onegrid = types.SimpleNamespace(mark_path=_grid_mark, installed=_grid_installed,
                                plan_install=_grid_install, plan_remove=_grid_remove)
