"""96f: what a faction's culture change costs it, said before it is saved.

The Oogway campaign editor's *Culture* pick on New / Edit faction, whose Preview
"says which units it gains or loses and which buildings in its towns the new
culture cannot build". Its source is no longer public, so this is built from
that behaviour, on this toolkit's own readers.

**Why a culture moves units at all.** The EDU's ``ownership`` names factions,
so it does not change. What changes is the EDB: a level's ``requires`` and a
``recruit_pool``'s both say ``factions { northern_european, }`` as often as
they name a faction, and a culture there means every faction of it. So the
faction's culture is swapped in the slot -> culture map and every clause is read
twice, once each way:

* a unit is **recruitable** when some level the faction may build has a pool
  for it that admits the faction (its other conditions - a resource, an event -
  are the same either way and are not weighed);
* a unit gained whose EDU ``ownership`` does not name the faction is said so,
  because the game trains nothing a unit's ownership leaves out;
* a **building in its towns** (every campaign's ``descr_strat.txt``) is one
  the faction could build before and cannot after. It stands at the start, but
  nobody can build it again.

Read only: nothing here writes, the faction editor's own save does.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from . import buildings as bld
from . import campstrat
from . import factions as fac
from . import stratedit

#: How many levels a unit row names as where it is recruited.
LEVELS_SHOWN = 3


def admitted(clause: str, fc: Dict[str, str]) -> Set[str]:
    """Which factions a ``requires`` clause lets in, cultures expanded.

    Only its ``factions { }`` terms are weighed, left to right with their own
    ``and`` / ``or`` and ``not``, the way the game reads a clause; a clause
    with none is open to everyone.
    """
    every = set(fc)
    cultures = set(fc.values())
    out: Optional[Set[str]] = None
    for c in bld.parse_clause(clause):
        if c.kind != "factions":
            continue
        named: Set[str] = set()
        for tok in c.values:
            low = tok.strip().lower()
            if low == "all":
                named = set(every)
                break
            if low in cultures:
                named |= {f for f, cu in fc.items() if cu == low}
            else:
                named.add(low)
        if c.negate:
            named = every - named
        if out is None:
            out = named
        elif c.join == "or":
            out |= named
        else:
            out &= named
    return set(every) if out is None else out


def recruitable(edb, slot: str, fc: Dict[str, str]) -> Dict[str, List[str]]:
    """unit type (lower-cased) -> the levels that train it for ``slot``."""
    out: Dict[str, List[str]] = {}
    for line in edb.buildings:
        for blk in line.blocks:
            if slot not in admitted(blk.requires, fc):
                continue
            for pool in blk.recruits:
                if slot in admitted(pool.requires, fc):
                    out.setdefault(pool.unit.lower(), []).append(blk.name)
    return out


def _unit_rows(mod, slot: str, types: Dict[str, List[str]]) -> List[dict]:
    by_type = {}
    try:
        by_type = {u.type.lower(): u for u in mod.edu.units}
    except (OSError, AttributeError, ValueError):
        pass
    rows = []
    for low, levels in types.items():
        u = by_type.get(low)
        shown = ""
        if u is not None:
            entry = mod.loc.get(u.dictionary)
            shown = entry.name.strip() if entry and entry.name else ""
        rows.append({
            "unit": u.type if u is not None else low,
            "label": shown,
            "known": u is not None,
            "owned": u is not None and slot in {o.lower() for o in u.ownership},
            "levels": levels[:LEVELS_SHOWN], "more": max(0, len(levels) - LEVELS_SHOWN),
        })
    rows.sort(key=lambda r: (r["label"] or r["unit"]).lower())
    return rows


def _town_buildings(mod, slot: str, edb, before, after) -> List[dict]:
    """Each building in the faction's towns it can build now and could not after."""
    levels = edb.by_level()
    out: List[dict] = []
    for camp in campstrat.campaign_paths(mod):
        try:
            sf = campstrat.read_strat(mod, camp)
        except (OSError, ValueError):
            continue
        node = sf.faction(slot)
        if node is None:
            continue
        for town in stratedit.settlements_of(sf, node):
            region = str(town.get("region") or "")
            for b in sf.children_of(town, "building"):
                level = str(b.get("level") or "")
                hit = levels.get(level)
                if hit is None:
                    continue
                line, blk = hit
                if slot in admitted(blk.requires, before) \
                        and slot not in admitted(blk.requires, after):
                    out.append({"campaign": camp, "region": region,
                                "line": line.name, "level": level})
    return out


def preview(mod, faction: str, culture: str) -> dict:
    """What ``faction`` gains and loses if its culture becomes ``culture``."""
    slot = fac.slot_of(faction).lower()
    new = (culture or "").strip().strip(",").lower()
    before = fac.faction_cultures(mod)
    old = before.get(slot, "")
    out = {"faction": slot, "old": old, "culture": new, "same": new == old,
           "has_edb": False, "gained": [], "lost": [], "buildings": []}
    if not slot or slot not in before or out["same"] or not new:
        return out
    if not mod.edb_path.exists():
        return out
    edb = mod.edb
    out["has_edb"] = True
    after = dict(before)
    after[slot] = new
    had = recruitable(edb, slot, before)
    gets = recruitable(edb, slot, after)
    out["gained"] = _unit_rows(mod, slot, {k: v for k, v in gets.items() if k not in had})
    out["lost"] = _unit_rows(mod, slot, {k: v for k, v in had.items() if k not in gets})
    out["buildings"] = _town_buildings(mod, slot, edb, before, after)
    return out
