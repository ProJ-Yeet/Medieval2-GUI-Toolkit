"""Everything in a mod, by category, in one report to read or share (96e2).

From the Pfadfinder-Adam (formerly MasterOogwayHomebrew) campaign editor's
idea of a mod contents report. Every screen of this toolkit shows its own part
of a mod; this puts the whole of it on one page: the factions and what each
holds at the start, the cultures and religions, the units by category and by
owner, the building chains, the regions and towns, the named characters, and
the diplomacy the campaign opens with.

Read only. A part whose file is missing or will not parse is reported as that,
with the error, and the rest of the report still comes back - the same rule
:mod:`health` keeps for a failed source.

:func:`text` writes the same report as Markdown, for a forum post or a bug
report.
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Dict, List

from . import i18n as _i18n


def _part(out: Dict, key: str, fn: Callable[[], object]) -> None:
    try:
        out[key] = fn()
    except Exception as e:  # noqa: BLE001 - a part that fails is named, never the whole report
        out.setdefault("failed", {})[key] = f"{type(e).__name__}: {e}"


def build(mod, campaign: str = "") -> Dict:
    from . import campfiles, campstrat, factions as fa, minorfiles

    out: Dict = {"mod": getattr(mod, "name", ""), "failed": {}}
    camps: List[str] = []
    _part(out, "campaigns", lambda: campfiles.campaigns(mod))
    camps = out.get("campaigns") or []
    campaign = campaign or (campstrat.DEFAULT_CAMPAIGN if campstrat.DEFAULT_CAMPAIGN in camps or not camps
                            else camps[0])
    out["campaign"] = campaign

    names: Dict[str, str] = {}
    try:
        names = fa.loc(mod)
    except Exception:  # noqa: BLE001
        names = {}

    def roster():
        rf = fa.parse_file(fa.path_for(mod))
        return [{"slot": fa.slot_of(r.name), "label": fa.label(r.name, names),
                 "culture": r.get("culture"), "religion": r.get("religion"),
                 "special": r.get("special_faction_type")} for r in rf.records]
    _part(out, "factions", roster)
    _part(out, "cultures", lambda: minorfiles.culture_names(mod))
    _part(out, "religions", lambda: minorfiles.religion_names(mod))

    def units():
        us = list(mod.edu.units)
        owners: Counter = Counter()
        for u in us:
            for o in (u.ownership or []):
                owners[o] += 1
        return {"count": len(us),
                "by_category": dict(Counter(u.category or "?" for u in us).most_common()),
                "by_class": dict(Counter(u.class_type or "?" for u in us).most_common()),
                "by_owner": dict(owners.most_common()),
                "mercenary": sum(1 for u in us if getattr(u, "mercenary_unit", False))}
    _part(out, "units", units)

    def edb():
        from . import buildings
        e = buildings.parse_file(mod.data / "export_descr_buildings.txt")
        chains = [{"name": b.name, "levels": len(b.levels)} for b in e.buildings]
        return {"chains": len(chains), "levels": sum(c["levels"] for c in chains),
                "list": chains, "hidden_resources": list(e.hidden_resources or [])}
    _part(out, "buildings", edb)

    def regions():
        from . import campmap
        rf = campmap.read_regions(mod)
        return [{"name": r.name, "settlement": r.settlement} for r in rf.records]
    _part(out, "regions", regions)

    def strat():
        sf = campstrat.read_strat(mod, campaign)
        rows = []
        for f in sf.of_kind("faction"):
            setts = sf.descendants_of(f, "settlement")
            chars = sf.descendants_of(f, "character")
            named = [c for c in chars if c.get("type") == "named character"]
            rows.append({
                "slot": f.name,
                "playable": next((k for k, v in sf.rosters.items() if f.name in v), ""),
                "treasury": f.get("denari"),
                "towns": [{"region": s.get("region") or s.name, "level": s.get("level"),
                           "population": s.get("population")} for s in setts],
                "characters": len(chars),
                "named": [{"name": c.name, "rank": c.get("rank") or "",
                           "age": c.get("age")} for c in named],
                "armies": len(sf.descendants_of(f, "army")),
                "units": len(sf.descendants_of(f, "unit")),
                "relatives": len(sf.descendants_of(f, "relative")),
            })
        rel = []
        for n in sf.of_kind("faction_relationships"):
            rel.append({"line": n.name or "", "fields": {k: v for k, v in n.fields.items()
                                                         if isinstance(v, (str, int, float, list))}})
        return {"factions": rows, "start_date": sf.globals.get("start_date"),
                "end_date": sf.globals.get("end_date"),
                "counts": sf.counts(), "relationships": rel}
    _part(out, "strat", strat)
    return out


def text(rep: Dict) -> str:
    """The report as Markdown."""
    L: List[str] = [f"# {rep.get('mod', '')}", ""]
    if rep.get("campaign"):
        L += [_i18n.msg("eng.modreport.campaign", "Campaign: {campaign}", campaign=rep["campaign"]), ""]
    facs = rep.get("factions") or []
    strat = rep.get("strat") or {}
    by_slot = {r["slot"]: r for r in strat.get("factions", [])}
    if facs:
        L += ["## " + _i18n.msg("eng.modreport.h_factions", "Factions ({n})", n=len(facs)), "",
              "| " + " | ".join([_i18n.msg("eng.modreport.c_faction", "Faction"), _i18n.msg("eng.modreport.c_culture", "Culture"),
                                 _i18n.msg("eng.modreport.c_religion", "Religion"), _i18n.msg("eng.modreport.c_status", "Status"),
                                 _i18n.msg("eng.modreport.c_towns", "Towns"), _i18n.msg("eng.modreport.c_characters", "Characters"),
                                 _i18n.msg("eng.modreport.c_armies", "Armies")]) + " |",
              "|---|---|---|---|---|---|---|"]
        for f in facs:
            s = by_slot.get(f["slot"], {})
            L.append(f"| {f['label']} | {f['culture']} | {f['religion']} | "
                     f"{s.get('playable') or f.get('special') or ''} | {len(s.get('towns', []))} | "
                     f"{s.get('characters', '')} | {s.get('armies', '')} |")
        L.append("")
    for key, head in (("cultures", _i18n.msg("eng.modreport.h_cultures", "Cultures")), ("religions", _i18n.msg("eng.modreport.h_religions", "Religions"))):
        if rep.get(key):
            L += [f"## {head} ({len(rep[key])})", "", ", ".join(rep[key]), ""]
    u = rep.get("units")
    if u:
        L += ["## " + _i18n.msg("eng.modreport.h_units", "Units ({n})", n=u["count"]), ""]
        L += ["- " + _i18n.msg("eng.modreport.by_category", "By category: {x}", x=", ".join(f"{k} {v}" for k, v in u["by_category"].items()))]
        L += ["- " + _i18n.msg("eng.modreport.by_class", "By class: {x}", x=", ".join(f"{k} {v}" for k, v in u["by_class"].items()))]
        L += ["- " + _i18n.msg("eng.modreport.by_owner", "By owner: {x}", x=", ".join(f"{k} {v}" for k, v in u["by_owner"].items())), ""]
    b = rep.get("buildings")
    if b:
        L += ["## " + _i18n.msg("eng.modreport.h_buildings", "Buildings ({chains} chains, {levels} levels)", chains=b["chains"], levels=b["levels"]), "",
              ", ".join(f"{c['name']} ({c['levels']})" for c in b["list"]), ""]
    if rep.get("regions") is not None:
        L += ["## " + _i18n.msg("eng.modreport.h_regions", "Regions ({n})", n=len(rep["regions"])), ""]
    if strat:
        L += ["## " + _i18n.msg("eng.modreport.h_towns", "Towns at the start"), ""]
        for r in strat["factions"]:
            if r["towns"]:
                L.append(f"- **{r['slot']}**: " + ", ".join(
                    f"{x['region']} ({x['level']})" for x in r["towns"]))
        L += ["", "## " + _i18n.msg("eng.modreport.h_characters", "Named characters at the start"), ""]
        for r in strat["factions"]:
            if r["named"]:
                L.append(f"- **{r['slot']}**: " + ", ".join(
                    f"{c['name']}{' (' + c['rank'] + ')' if c['rank'] else ''}" for c in r["named"]))
        L.append("")
    for k, why in (rep.get("failed") or {}).items():
        L.append("> " + _i18n.msg("eng.modreport.failed", "{part} could not be read: {why}", part=k, why=why))
    return "\n".join(L).rstrip() + "\n"
