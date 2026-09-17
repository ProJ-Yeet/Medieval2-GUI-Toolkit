"""The engine's ceilings on ``export_descr_unit.txt`` - Phase 39.

The toolkit writes every field of a unit and checked no value of any of them:
the unit editor would save an HP of 40 or 400 men without a word. This is the
check, and every number in it has a Medieval II source beside it.

**The write-up's list was Rome: Total War's.** Phase 39 was scoped off
TWCenter's *List of Hardcoded Limits*, and that thread is headed "RTW" - its
faction limit is 21 and its hidden resources mention Rome and the Marian
reforms. Taken as written, its "men per unit: max 60" reported **300 of
Divide and Conquer's units and 113 of Third Age Reforged's**, on two mods that
play. So every limit here comes from a Medieval II document in the archive
instead, and the RTW ones with no Medieval II source are **not checked**:

    source                                          limit
    A Beginner's Guide to the Export_Descr_Unit     500 units in the file
      (M2TW, the archive's EDU guide)               4 to 100 men
                                                    attack capped at 63
                                                    up to three officers
                                                    up to three mount effects
                                                    two formations, one of square
                                                      or horde and one of
                                                      shield_wall, phalanx,
                                                      schiltrom or wedge
    M2TW Ultimate Docudemons 5.3, Character         stat_health 0 to 15, both
      Attributes                                      values

    not checked (RTW only): charge 63, armour and defence 63, shield 31,
    turns to build 244, 100 units a faction, 31 men in a bodyguard

**A ceiling shows and never blocks**, the same rule the map's baseline
follows: a mod over one is somebody else's mod with somebody else's bug in it.
**M2EX lifts the unit count and nothing else here** - the 500 is a table size
in the executable and :mod:`unittransfer.modflags` already drops that kind of
finding on a marked mod; a stat capped at 63 is a field width, and no flag here
claims to change one.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from . import edu as edu_mod

GUIDE = "A Beginner's Guide to the Export_Descr_Unit (M2TW)"
DOCUDEMONS = "M2TW Ultimate Docudemons 5.3, Character Attributes"

MAX_UNITS = 500
MEN_MIN, MEN_MAX = 4, 100
MAX_ATTACK = 63
MAX_HEALTH = 15
MAX_OFFICERS = 3
MAX_MOUNT_EFFECTS = 3
MAX_FORMATIONS = 2
#: of two formations, one is a base shape and the other what it switches into
FORMATION_BASE = ("square", "horde")
FORMATION_SPECIAL = ("shield_wall", "phalanx", "schiltrom", "wedge")

_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def finding(kind: str, name: str, message: str, source: str, **extra) -> Dict:
    return dict({"kind": kind, "name": name, "message": message, "fatal": False,
                 "source": source}, **extra)


def _fields(raw: str) -> Dict[str, List[List[str]]]:
    """``{key: [values of each line with that key]}`` - officer is on many lines."""
    out: Dict[str, List[List[str]]] = {}
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        key, vals = edu_mod._split_fields(line)
        if key:
            out.setdefault(key, []).append(vals)
    return out


def _num(v: str) -> Optional[float]:
    v = (v or "").strip()
    return float(v) if _NUMBER.match(v) else None


def unit_findings(raw: str, name: str = "") -> List[Dict]:
    """Every ceiling one unit block is past."""
    f = _fields(raw)
    name = name or ((f.get("type") or [[""]])[0] or [""])[0]
    out: List[Dict] = []

    def add(field: str, message: str, source: str, value=None, limit=None) -> None:
        out.append(finding("unit-ceiling", name, message, source,
                           field=field, value=value, limit=limit))

    soldier = (f.get("soldier") or [[]])[0]
    men = _num(soldier[1]) if len(soldier) > 1 else None
    if men is not None and men > MEN_MAX:
        add("soldier", f"{men:g} men, over the engine's {MEN_MAX}", GUIDE, men, MEN_MAX)
    elif men is not None and men < MEN_MIN:
        add("soldier", f"{men:g} men, under the engine's {MEN_MIN}", GUIDE, men, MEN_MIN)

    for field, label in (("stat_pri", "primary"), ("stat_sec", "secondary")):
        vals = (f.get(field) or [[]])[0]
        attack = _num(vals[0]) if vals else None
        if attack is not None and attack > MAX_ATTACK:
            add(field, f"{label} attack {attack:g}, over the cap of {MAX_ATTACK} - "
                       f"it fights as {MAX_ATTACK}", GUIDE, attack, MAX_ATTACK)

    health = (f.get("stat_health") or [[]])[0]
    for i, label in ((0, "hit points"), (1, "second hit points (the mount's, and "
                                          "auto-resolve's)")):
        v = _num(health[i]) if len(health) > i else None
        if v is not None and v > MAX_HEALTH:
            add("stat_health", f"{label} {v:g}, over the range's {MAX_HEALTH}",
                DOCUDEMONS, v, MAX_HEALTH)

    officers = len(f.get("officer", []))
    if officers > MAX_OFFICERS:
        add("officer", f"{officers} officer lines, and a unit may have three",
            GUIDE, officers, MAX_OFFICERS)
    effects = [v for vals in f.get("mount_effect", []) for v in vals if v.strip()]
    if len(effects) > MAX_MOUNT_EFFECTS:
        add("mount_effect", f"{len(effects)} mount effects, and a unit may have three",
            GUIDE, len(effects), MAX_MOUNT_EFFECTS)

    form = (f.get("formation") or [[]])[0]
    shapes = [v.strip() for v in form if v.strip() and not _NUMBER.match(v.strip())]
    if len(shapes) > MAX_FORMATIONS:
        add("formation", f"{len(shapes)} formations, and a unit may have two",
            GUIDE, len(shapes), MAX_FORMATIONS)
    elif len(shapes) == 2:
        base = [s for s in shapes if s in FORMATION_BASE]
        special = [s for s in shapes if s in FORMATION_SPECIAL]
        if len(base) != 1 or len(special) != 1:
            add("formation", f"formations `{shapes[0]}` and `{shapes[1]}`: of two, one "
                             "has to be square or horde and the other shield_wall, "
                             "phalanx, schiltrom or wedge", GUIDE)
    return out


def mod_findings(units) -> List[Dict]:
    """The file's own ceiling. M2EX lifts it."""
    main = [u for u in units if not getattr(u, "is_eop", False)]
    if len(main) <= MAX_UNITS:
        return []
    return [finding("too-many-units", "export_descr_unit.txt",
                    f"{len(main)} units in the file, over the engine's {MAX_UNITS}",
                    GUIDE, value=len(main), limit=MAX_UNITS)]


def report(mod) -> Dict:
    """Every ceiling finding in one mod, with the ones M2EX lifts dropped."""
    from . import modflags
    units = list(mod.edu.units)
    per_unit = {}
    for u in units:
        got = unit_findings(u.raw, u.type)
        if got:
            per_unit[u.type] = got
    whole = mod_findings(units)
    kept = modflags.uncapped(whole, mod)
    return {"mod": getattr(mod, "name", ""), "m2ex": modflags.is_m2ex(mod),
            "units": len(units), "roster": kept, "lifted": len(whole) - len(kept),
            "per_unit": per_unit,
            "count": len(kept) + sum(len(v) for v in per_unit.values())}
