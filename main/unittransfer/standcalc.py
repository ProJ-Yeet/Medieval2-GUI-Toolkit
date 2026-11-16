"""Every faction's starting standings, worked out from who they are.

**From Mylae's M2TW Editor** (github.com/Machiavello-1441/m2tw-editor, used with
the author's permission): ``diplomacyStandings.js`` and its panel
``DiplomacyStandingUpdater.jsx`` (2026-11-15). For each ordered pair of
factions, in hundredths:

    same religion +15, different -15
    same culture  +10, different -10
    allied        +20
    at war        -50

summed and kept between -1 and 1, either from zero (``recalculate``) or on top
of what the file already says (``add``). A faction whose religion or culture is
not known gets no points for it, never a guess. The numbers are his choice, not
the game's, so they are defaults the panel lets the user change.

What is changed from his:

    * a protectorate_of or client_of line counts as allied, since the game
      starts the two factions allied
    * the rebels (``slave``) are left out on both sides and their existing
      standings are kept: their opinions are not a diplomacy anyone plays
    * a pair that comes out at 0 and had no cell is not written, since 0 is
      what the game starts an unwritten pair at; his writes every pair
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

#: his weights, in hundredths
WEIGHTS = {"religion": 15, "culture": 10, "ally": 20, "war": -50}
MODES = ("recalculate", "add")
FRIENDLY = ("allied_to", "protectorate_of", "client_of")
REBELS = "slave"


def faction_meta(mod) -> Dict[str, Tuple[str, str]]:
    """``{faction: (religion, culture)}`` from descr_sm_factions.txt, lower case.

    Empty when the file cannot be read (the stock game's is packed): every
    religion and culture point is then skipped rather than guessed.
    """
    from . import factions as facfile
    try:
        rf = facfile.parse_file(facfile.path_for(mod))
    except (OSError, ValueError):
        return {}
    out = {}
    for r in rf.records:
        name = r.name.split(",")[0].strip().lower()
        rel = str(r.get("religion") or "").strip(", ").lower()
        cul = str(r.get("culture") or "").strip(", ").lower()
        out[name] = (rel, cul)
    return out


def relations(strat) -> Dict[frozenset, set]:
    """Each unordered pair's stated relations, from faction_relationships."""
    out: Dict[frozenset, set] = {}
    for n in strat.of_kind("faction_relationships"):
        who, how = str(n.get("faction") or ""), str(n.get("relation") or "")
        for t in n.get("toward") or ():
            if t.lower() != who.lower():
                out.setdefault(frozenset((who.lower(), t.lower())), set()).add(how)
    return out


def compute(factions: Iterable[str], meta: Dict[str, Tuple[str, str]],
            rel: Dict[frozenset, set], existing: Dict[str, Dict[str, float]],
            mode: str = "recalculate", weights: Optional[Dict[str, int]] = None
            ) -> Dict[str, Dict[str, float]]:
    """``{faction: {target: standing}}`` for every ordered pair but the rebels.

    ``existing`` is each faction's current cells; its cells toward the rebels
    or toward a faction not in ``factions`` are kept as they are.
    """
    w = dict(WEIGHTS, **(weights or {}))
    names = [f for f in dict.fromkeys(factions) if f and f.lower() != REBELS]
    out: Dict[str, Dict[str, float]] = {}
    for f in names:
        mine = existing.get(f, {})
        cells = {t: v for t, v in mine.items()
                 if t.lower() not in {n.lower() for n in names} or t.lower() == f.lower()}
        rf, cf = meta.get(f.lower(), ("", ""))
        for t in names:
            if t == f:
                continue
            rt, ct = meta.get(t.lower(), ("", ""))
            pts = 0
            if rf and rt:
                pts += w["religion"] if rf == rt else -w["religion"]
            if cf and ct:
                pts += w["culture"] if cf == ct else -w["culture"]
            stated = rel.get(frozenset((f.lower(), t.lower())), set())
            if stated & set(FRIENDLY):
                pts += w["ally"]
            if "at_war_with" in stated:
                pts += w["war"]
            base = mine.get(t, 0.0) if mode == "add" else 0.0
            value = round(max(-1.0, min(1.0, base + pts / 100)), 2)
            if value == 0 and t not in mine:
                continue
            cells[t] = value
        out[f] = cells
    return out
