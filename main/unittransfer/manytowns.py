"""Many towns at once, each with a garrison - Phase 96e4.

From the other campaign editor's checklist: give one faction a village in
several provinces in one go, and stand an army in each, bought up to a cost.
Two writers already exist for the two halves, and this only chains them:

* :func:`stratedit.plan_new_settlement` puts one village last in the owner's
  faction block and reads the file back to prove it touched nothing else;
* :func:`stratchar.new_character` writes a character block in the shape of the
  faction's own, inserted where :func:`stratchar.insert_at` says.

Each province is applied to the text the last one left, in memory, and the
whole file is written once by :func:`stratedit.apply_settlement`: one backup,
one entry in the Log, one Undo for the lot. A province the village writer
refuses (it already has a settlement, or is not declared) is skipped and named,
and the rest go ahead.

THE GARRISON. descr_strat.txt has no garrison of its own (see 96d): what holds
a town is the army of whoever stands on its tile. So each town gets a general
of the owner's, named from the owner's own pool in descr_names.txt and never a
name the file already uses, standing on the settlement, leading regiments the
owner may recruit, bought from the dearest down while the total stays within
the cost asked for, no unit more than twice. Bodyguards, ships, siege engines
and mercenaries are not a garrison and are not bought.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from . import campstrat, stratchar, stratedit
from . import i18n as _i18n

#: The most regiments a garrison is bought, whatever the cost allows.
MAX_UNITS = 12
#: How many of one unit a garrison takes before it moves on to the next.
EACH = 2

_COST = re.compile(r"^\s*stat_cost\s+([^;\r\n]*)", re.M)


def unit_cost(unit) -> int:
    """A unit's recruitment price: ``stat_cost``'s second number, or 0."""
    raw = getattr(unit, "raw", "") or ""
    if isinstance(raw, (list, tuple)):
        raw = "\n".join(raw)
    m = _COST.search(str(raw))
    if not m:
        return 0
    parts = [p.strip() for p in m.group(1).split(",")]
    try:
        return int(parts[1])
    except (IndexError, ValueError):
        return 0


def garrison_units(mod, owner: str) -> List[Tuple[str, int]]:
    """``[(unit, cost)]`` the owner may field as a garrison, dearest first."""
    out = []
    low = owner.lower()
    for u in getattr(mod.edu, "units", None) or []:
        attrs = set(getattr(u, "attributes", None) or [])
        own = {o.lower() for o in (getattr(u, "ownership", None) or [])}
        if low not in own or "general_unit" in attrs or "mercenary_unit" in attrs:
            continue
        if getattr(u, "ship", None) or (u.category or "").lower() in ("ship", "siege", "handler"):
            continue
        cost = unit_cost(u)
        if cost > 0:
            out.append((u.type, cost))
    out.sort(key=lambda t: (-t[1], t[0]))
    return out


def buy(units: List[Tuple[str, int]], limit: int) -> List[str]:
    """The regiments a garrison gets for ``limit``: dearest first among those
    costing no more than a quarter of it, each at most :data:`EACH` times, at
    most :data:`MAX_UNITS`, never past the limit.

    The quarter is what makes it a garrison. Dearest-first over everything
    spent DaC's 1500 on one regiment of knights; held to a quarter it buys
    four to six of the best the money stretches to, and a limit too small for
    any of those still buys the cheapest the faction has."""
    if not units:
        return []
    cap = max(limit / 4, min(c for _n, c in units))
    got: List[str] = []
    left = limit
    for name, cost in units:
        if cost > cap:
            continue
        for _ in range(EACH):
            if len(got) >= MAX_UNITS or cost > left:
                break
            got.append(name)
            left -= cost
    return got


def _free_names(sf, voc, owner: str) -> List[str]:
    """The owner's pool names no character or record in the file already has."""
    used = {str(n.name).strip().lower() for n in sf.nodes
            if n.kind in ("character", "character_record")}
    return [n for n in (voc.pool.get(owner) or []) if n.lower() not in used]


def plan_towns(mod, facts, body: dict) -> stratedit.StratPlan:
    """``body``: ``{campaign, owner, creator, towns: [{region, x, y}], cost}``.

    ``x``, ``y`` are the settlement's tile in game coordinates, which is where
    the garrison's general stands; ``cost`` 0 or absent means villages only.
    """
    from .campmap import MapError
    campaign = str(body.get("campaign") or "") or facts.campaign
    owner = str(body.get("owner") or "").strip()
    towns = [t for t in (body.get("towns") or []) if str(t.get("region") or "").strip()]
    p = stratedit.StratPlan(mod=mod, campaign=campaign,
                            region=_i18n.msg("eng.manytowns.towns", "{n} towns", n=len(towns)))
    if not owner:
        p.errors.append(_i18n.msg("eng.stratedit.a_new_settlement_needs_a_faction", "a new settlement needs a faction to hold it"))
        return p
    if not towns:
        p.errors.append(_i18n.msg("eng.manytowns.pick_at_least_one_province", "pick at least one province with no settlement"))
        return p
    try:
        cost = max(0, int(body.get("cost") or 0))
    except (TypeError, ValueError):
        p.errors.append(_i18n.msg("eng.manytowns.the_cost_limit_is_a_whole", "the cost limit is a whole number"))
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = sf.path
    if sf.faction(owner) is None:
        p.errors.append(_i18n.msg("eng.manytowns.has_no_faction_block", "{owner} has no faction block in this campaign", owner=owner))
        return p
    creator = str(body.get("creator") or owner).strip()
    declared = stratedit._declared(facts)
    start = sf

    army: List[str] = []
    names: List[str] = []
    if cost:
        army = buy(garrison_units(mod, owner), cost)
        if not army:
            p.warnings.append(_i18n.msg("eng.manytowns.nothing_the_owner_recruits_costs", "nothing {owner} recruits costs {cost} or less, so the towns get no garrison", owner=owner, cost=cost))
        voc = stratchar.Vocabulary(facts, sf)
        names = _free_names(sf, voc, owner)
        if army and not voc.have_pool:
            p.warnings.append(_i18n.msg("eng.manytowns.no_name_pool", "descr_names.txt is not on disk, so the generals cannot be named from {owner}'s pool and the towns get no garrison", owner=owner))
            army = []

    made = gens = 0
    for t in towns:
        region = str(t["region"]).strip()
        if declared and region.lower() not in declared:
            p.warnings.append(_i18n.msg("eng.stratedit.is_not_a_province_in_this", "{region} is not a province in this map's descr_regions.txt", region=region))
            continue
        text, errs = stratedit.plan_new_settlement(sf, region, owner, creator)
        if errs:
            p.warnings.append(f"{region}: " + "; ".join(errs))
            continue
        sf = campstrat.parse_strat(text)
        made += 1
        p.changes.append(f"+ a {stratedit.NEW_LEVEL} in {region}, held by {owner}")
        if not army:
            continue
        if not names:
            p.warnings.append(_i18n.msg("eng.manytowns.out_of_names", "{owner}'s name pool has no unused name left, so {region} gets no garrison", owner=owner, region=region))
            continue
        try:
            x, y = int(t.get("x")), int(t.get("y"))
        except (TypeError, ValueError):
            p.warnings.append(_i18n.msg("eng.manytowns.no_tile", "{region} came with no tile, so it gets no garrison", region=region))
            continue
        name = names.pop(0)
        spec = stratchar.Spec(name=name, type="general", gender="male", age=30,
                              x=x, y=y,
                              army=[stratchar.Army(unit=u) for u in army])
        faction = sf.faction(owner)
        at = stratchar.insert_at(sf, faction)
        lines = list(sf.lines)
        lines[at:at] = stratchar.new_character(sf, faction, spec)
        sf = campstrat.parse_strat(stratedit.serialise(sf, lines))
        gens += 1
        p.changes.append(_i18n.msg("eng.manytowns.garrison", "  {name} holds it with {n} regiments", name=name, n=len(army)))

    if not made:
        p.errors.append(_i18n.msg("eng.manytowns.no_town_could_be_added", "no town could be added: {why}", why="; ".join(p.warnings) or "nothing to do"))
        return p
    # the lot read back as a whole: exactly the towns and the generals added,
    # and nothing else in the file counted differently
    was, now = start.counts(), sf.counts()
    for kind_ in sorted(set(was) | set(now)):
        want = was.get(kind_, 0) + {"settlement": made, "character": gens}.get(kind_, 0)
        if kind_ in ("unit", "army", "building"):
            continue                                   # the garrisons' own lines
        if now.get(kind_, 0) != want:
            p.errors.append(_i18n.msg("eng.stratedit.adding_one_settlement_would_leave_record", "adding one settlement would leave {now} {kind_} record(s) where there should be {want}", now=now.get(kind_, 0), kind_=kind_, want=want))
    if start.rosters != sf.rosters or start.globals != sf.globals:
        p.errors.append(_i18n.msg("eng.stratedit.adding_a_settlement_would_change_the", "adding a settlement would change the campaign's header, which it has no business touching"))
    if not p.errors:
        p.text = stratedit.serialise(sf, sf.lines)
        p.capitals = stratedit._capital_notes(start, sf, p, owner)
    return p
