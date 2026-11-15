"""The diplomacy section of descr_strat.txt, checked.

**From Mylae's M2TW Editor** (github.com/Machiavello-1441/m2tw-editor, used with
the author's permission). His ``validateCampaignDiplomacy.js``,
``diplomacyRelationRules.js`` and ``clientStateRules.js`` (2026-11-15) hold the
rules; they are written again here over :mod:`campstrat`'s reading of the file,
so the validator can report them with a line to jump to.

What is his, and what is changed:

    taken     a name no faction answers to; a faction toward itself; a pair both
              allied and at war; a standing outside -1..1; one standing given
              twice with two values; a subject with more than one overlord, or
              both a client and a protectorate; a subject whose overlord is a
              subject itself (his cycle check, which a chain always reaches
              first); a subject at war with its overlord
    changed   his "not declared in this campaign" is asked of
              descr_sm_factions.txt: a faction the campaign does not list is
              still one the game knows, and only a name it does not know is lost
    changed   protectorate_of and client_of are M2EX's. On a mod not marked as
              M2EX the line is refused outright; on one that is, client_of with
              ``client_status_enable`` off in descr_ex.txt only makes the two
              allies, which is said
    left out  his "missing reverse declaration": the game writes allied_to and
              at_war_with to both sides of the pair, so one line is the whole
              relation and the second line he asks for changes nothing

Every check is read-only. Each issue is ``(code, severity, line, what, message)``
with ``line`` 1-based; :mod:`mapcheck` turns them into findings.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import i18n as _i18n

#: what the stock game reads on a faction_relationships line
STOCK = ("allied_to", "at_war_with")
#: what M2EX adds: the first faction is the subject, the rest its overlord
SUBJECT = ("protectorate_of", "client_of")
#: the relations that leave the two factions allied
FRIENDLY = ("allied_to",) + SUBJECT


@dataclass
class Issue:
    code: str
    severity: str
    line: int
    what: str
    message: str


def clients_enabled(mod) -> bool:
    """Is ``client_status_enable true`` in the mod's descr_ex.txt? Off when absent."""
    path = Path(getattr(mod, "data", "")) / "descr_ex.txt"
    try:
        text = path.read_text(encoding="latin-1")
    except OSError:
        return False
    for raw in text.splitlines():
        words = raw.split(";", 1)[0].split()
        if len(words) >= 2 and words[0].lower() == "client_status_enable":
            return words[1].lower() == "true"
    return False


def _rows(strat, kind: str):
    """Every line of ``kind`` that read, as ``(node, faction)``."""
    for n in strat.of_kind(kind):
        who = n.get("faction")
        if who:
            yield n, str(who)


def check(strat, known: Optional[Set[str]], m2ex: bool,
          clients_on: bool) -> List[Issue]:
    """Every diplomacy issue in ``strat``.

    ``known`` is every faction name descr_sm_factions.txt declares, lower case,
    or None when it could not be read (the name check is then skipped).
    """
    out: List[Issue] = []

    def add(code, severity, node, what, message):
        out.append(Issue(code, severity, node.start + 1, what, message))

    def name_ok(node, kind, name):
        if known is not None and name.lower() not in known:
            add("strat.diplomacy_faction", "warn", node, f"{kind}|{node.name}|{name}",
                _i18n.msg("eng.diplocheck.unknown_faction",
                          "`{name}` on this {kind} line is not a faction descr_sm_factions.txt declares, so the game skips it and logs a script error.",
                          name=name, kind=kind))

    # -- standings -------------------------------------------------------------
    given: Dict[Tuple[str, str], Tuple[float, int]] = {}
    for n, who in _rows(strat, "faction_standings"):
        name_ok(n, "faction_standings", who)
        for target, value in n.get("pairs") or ():
            name_ok(n, "faction_standings", target)
            if target.lower() == who.lower():
                add("strat.diplomacy_contradiction", "warn", n, f"standing-self|{who}",
                    _i18n.msg("eng.diplocheck.standing_self",
                              "{f} is given a standing toward itself, which the game skips.",
                              f=who))
                continue
            if not -1.0 <= value <= 1.0:
                add("strat.standing_range", "warn", n, f"{who}|{target}",
                    _i18n.msg("eng.diplocheck.standing_range",
                              "{f}'s standing toward {t} is {v}; a standing runs from -1 to 1.",
                              f=who, t=target, v=f"{value:g}"))
            key = (who.lower(), target.lower())
            if key in given and given[key][0] != value:
                add("strat.diplomacy_contradiction", "note", n, f"standing-twice|{who}|{target}",
                    _i18n.msg("eng.diplocheck.standing_twice",
                              "{f}'s standing toward {t} is set to {v1} on line {l1} and to {v2} here; the later one wins.",
                              f=who, t=target, v1=f"{given[key][0]:g}", l1=given[key][1],
                              v2=f"{value:g}"))
            given[key] = (value, n.start + 1)

    # -- relationships ---------------------------------------------------------
    stance: Dict[frozenset, List[Tuple[str, int, str, str]]] = {}
    overlords: Dict[str, Dict[str, Set[str]]] = {}    # subject -> relation -> overlords
    shown: Dict[str, str] = {}                         # lower -> as written
    for n, who in _rows(strat, "faction_relationships"):
        how = str(n.get("relation") or "")
        name_ok(n, "faction_relationships", who)
        if how not in STOCK + SUBJECT:
            add("strat.diplomacy_word", "fatal", n, f"{who}|{how}",
                _i18n.msg("eng.diplocheck.unknown_relation",
                          "`{how}` is not a relation the game reads. It reads allied_to and at_war_with, and on M2EX protectorate_of and client_of.",
                          how=how))
            continue
        if how in SUBJECT and not m2ex:
            add("strat.diplomacy_word", "fatal", n, f"{who}|{how}",
                _i18n.msg("eng.diplocheck.subject_needs_m2ex",
                          "{how} is read only by M2EX, and this mod is not marked as running on it. The stock game cannot read this line.",
                          how=how))
            continue
        if how == "client_of" and not clients_on:
            add("strat.diplomacy_word", "warn", n, f"{who}|client_off",
                _i18n.msg("eng.diplocheck.client_off",
                          "client_of needs `client_status_enable true` in descr_ex.txt. Without it {f} and its overlord only start as allies.",
                          f=who))
        for target in n.get("toward") or ():
            name_ok(n, "faction_relationships", target)
            if target.lower() == who.lower():
                add("strat.diplomacy_contradiction", "warn", n, f"self|{who}|{how}",
                    _i18n.msg("eng.diplocheck.relation_self",
                              "{f} is {how} itself, which the game skips.", f=who, how=how))
                continue
            shown.setdefault(who.lower(), who)
            shown.setdefault(target.lower(), target)
            stance.setdefault(frozenset((who.lower(), target.lower())), []).append(
                (how, n.start + 1, who, target))
            if how in SUBJECT:
                overlords.setdefault(who.lower(), {}).setdefault(how, set()).add(target.lower())

    for rows in stance.values():
        war = [r for r in rows if r[0] == "at_war_with"]
        friendly = [r for r in rows if r[0] in FRIENDLY]
        if not war or not friendly:
            continue
        first = min(war[0], friendly[0], key=lambda r: r[1])
        last = max(rows, key=lambda r: r[1])
        other = war[0] if first is friendly[0] else friendly[0]
        a, b = sorted((rows[0][2], rows[0][3]))
        out.append(Issue(
            "strat.diplomacy_contradiction", "warn", last[1], f"war-and-peace|{a}|{b}",
            _i18n.msg("eng.diplocheck.war_and_alliance",
                      "{a} and {b} are declared {r1} on line {l1} and {r2} on line {l2}; the later line wins, so {last} holds.",
                      a=a, b=b, r1=first[0], l1=first[1], r2=other[0], l2=other[1],
                      last=last[0])))

    # -- subjects (M2EX) -------------------------------------------------------
    first_line = {}
    for n, who in _rows(strat, "faction_relationships"):
        if n.get("relation") in SUBJECT:
            first_line.setdefault(who.lower(), n.start + 1)
    for subject, by_how in sorted(overlords.items()):
        line = first_line.get(subject, 0)
        lords = set().union(*by_how.values())
        if len(lords) > 1 or len(by_how) > 1:
            out.append(Issue(
                "strat.subject_chain", "warn", line, f"overlords|{subject}",
                _i18n.msg("eng.diplocheck.many_overlords",
                          "{s} is declared a subject more than once ({rows}); a faction can be the client or the protectorate of one overlord only.",
                          s=shown.get(subject, subject),
                          rows=", ".join(f"{how} {shown.get(o, o)}"
                                         for how in sorted(by_how)
                                         for o in sorted(by_how[how])))))
        for lord in sorted(lords):
            if lord in overlords:
                out.append(Issue(
                    "strat.subject_chain", "warn", line, f"nested|{subject}|{lord}",
                    _i18n.msg("eng.diplocheck.nested_subject",
                              "{s}'s overlord {o} is itself a subject, and M2EX does not allow a subject of a subject.",
                              s=shown.get(subject, subject), o=shown.get(lord, lord))))
            if any(r[0] == "at_war_with" for r in stance.get(frozenset((subject, lord)), ())):
                out.append(Issue(
                    "strat.subject_chain", "warn", line, f"war|{subject}|{lord}",
                    _i18n.msg("eng.diplocheck.subject_at_war",
                              "{s} is a subject of {o} and also at war with it.",
                              s=shown.get(subject, subject), o=shown.get(lord, lord))))
    return out
