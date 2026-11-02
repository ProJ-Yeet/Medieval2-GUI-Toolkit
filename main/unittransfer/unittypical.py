"""The usual unit of a kind in a mod (96f, a unit from nothing).

New unit always starts from a unit that works in the game. What it lacked is
the start the editor calls *Nothing*: say what the unit is - foot soldiers who
fight hand to hand, spearmen, foot that shoot, horsemen who charge, horsemen
who shoot - and begin where such units in *this* mod usually are. This module
reads every unit of the kind, takes the middle of each main number (men,
attack, charge, armour, defence, shield, morale, cost, upkeep, turns), and
names the unit that sits closest to all of those middles at once. New unit
then copies that one, so every line is in the form the mod's own units of the
kind have, and the page shows each number's middle, lowest and highest beside
it to change from there.

General's bodyguards are left out: they are a kind of their own, and one per
faction would pull every middle towards them.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

#: kind -> (category, the classes it takes)
KINDS: Dict[str, tuple] = {
    "foot_melee": ("infantry", {"heavy", "light"}),
    "foot_spear": ("infantry", {"spearmen"}),
    "foot_missile": ("infantry", {"missile", "skirmish"}),
    "horse_charge": ("cavalry", {"heavy", "light"}),
    "horse_missile": ("cavalry", {"missile"}),
}
#: the numbers compared, in the order the page lists them
STATS = ("men", "attack", "charge", "missile", "armour", "defence", "shield", "morale",
         "cost", "upkeep", "turns")

_NUM = re.compile(r"-?\d+(\.\d+)?")


def _line(raw: str, key: str) -> List[str]:
    for ln in raw.splitlines():
        bits = ln.split(None, 1)
        if bits and bits[0].lower() == key:
            return [x.strip() for x in (bits[1] if len(bits) > 1 else "").split(";")[0].split(",")]
    return []


def _n(vals: List[str], i: int) -> Optional[float]:
    if i < len(vals) and _NUM.fullmatch(vals[i].strip()):
        return float(vals[i])
    return None


def numbers(unit) -> Dict[str, Optional[float]]:
    """The main numbers of one unit, from its own EDU lines."""
    raw = unit.raw or ""
    pri, sec = _line(raw, "stat_pri"), _line(raw, "stat_sec")
    shoots = (pri[5].strip().lower() if len(pri) > 5 else "") in ("missile", "thrown") \
        and (_n(pri, 3) or 0) > 0
    melee = sec if shoots else pri
    soldier, armour = _line(raw, "soldier"), _line(raw, "stat_pri_armour")
    mental, cost = _line(raw, "stat_mental"), _line(raw, "stat_cost")
    return {"men": _n(soldier, 1), "attack": _n(melee, 0), "charge": _n(melee, 1),
            "missile": _n(pri, 0) if shoots else None,
            "armour": _n(armour, 0), "defence": _n(armour, 1), "shield": _n(armour, 2),
            "morale": _n(mental, 0), "cost": _n(cost, 1), "upkeep": _n(cost, 2), "turns": _n(cost, 0)}


def _middle(vals: List[float]) -> float:
    vals = sorted(vals)
    k = len(vals)
    return vals[k // 2] if k % 2 else (vals[k // 2 - 1] + vals[k // 2]) / 2


def of_kind(mod, kind: str) -> List:
    cat, classes = KINDS[kind]
    return [u for u in mod.edu.by_type().values()
            if (u.category or "").lower() == cat and (u.class_type or "").lower() in classes
            and "general_unit" not in [a.lower() for a in (u.attributes or [])]]


def typical(mod, kind: str) -> Dict:
    """The kind's numbers in this mod and the unit closest to their middle."""
    if kind not in KINDS:
        raise KeyError(kind)
    units = of_kind(mod, kind)
    rows = [(u, numbers(u)) for u in units]
    stats = []
    for key in STATS:
        vals = [n[key] for _, n in rows if n[key] is not None]
        if not vals:
            continue
        stats.append({"key": key, "middle": round(_middle(vals), 2), "low": min(vals), "high": max(vals),
                      "count": len(vals)})
    best, best_d = None, None
    for u, n in rows:
        d = 0.0
        for s in stats:
            v = n[s["key"]]
            span = (s["high"] - s["low"]) or 1.0
            d += abs((v if v is not None else s["middle"]) - s["middle"]) / span
        if best_d is None or d < best_d:
            best, best_d = (u, n), d
    out = {"kind": kind, "count": len(units), "stats": stats, "type": "", "name": "", "values": {}}
    if best:
        out["type"] = best[0].type
        out["values"] = {k: v for k, v in best[1].items() if v is not None}
    return out
