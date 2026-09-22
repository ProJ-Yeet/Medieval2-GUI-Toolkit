"""What the two crash guides name and nothing else here checked (Phase 54b).

`Reference/TWCenter/GUIDE - Crashes and how to fix them.pdf` and `Crash to
Desktop - TWC Wiki.pdf` list about forty causes. Most were already somebody's
rule - the map's, the EDB's, the modeldb's, a file editor's - and Health is now
the door to those. These are the ones that belonged to no module: each reads
files that two or three other modules own, and none of those was the obvious
home. So they live together here, on :mod:`unittransfer.mapcheck`'s shape - a
``@rule`` with a code, a label, a severity and a source - and Health runs them.

**Every rule was measured on both installed mods before it was written**, on
Phase 12's ruling that a count from a wiki is not a fact about a mod
(2026-09-22, DaC and ROCSS):

* an undeclared ``ai_label``: only ``papal_faction``, in both of DaC's
  campaigns, and DaC plays - so that label is the engine's own and is exempt.
  ROCSS ships no ``descr_campaign_ai_db.xml`` at all, and a mod without one
  uses the game's, so the rule does not run there.
* ``historic_event`` with no text: **the guide says case-sensitive and the mod
  says otherwise** - 631 of DaC's 633 events differ from their key only by
  case, and it plays. Matched case-blind, two are left on DaC's main campaign
  and four on Shattered Alliances (one of them is called ``crash_game``). DaC
  ships them and plays, so a warning, not the guide's CTD.
* an antitrait whose excluded cultures differ from its trait's: none in 6
  pairs on DaC, none in 323 on ROCSS. A crash rule should find nothing on a
  shipping mod, and this is one - so it ships as the guide states it.
* absolute paths in the banner, projectile and standard files: none on either.
* runs of three or more spaces on a modeldb line: none on either (DaC has one
  line with two).

**One was refused**, and is in :data:`REFUSED` so the next reader of the guide
finds the answer: "a faction a building's later level names and an earlier one
omits crashes the game". DaC has 24 such levels in 14 lines and ROCSS 6 in 4,
and both play.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

from . import keyblock as kb

GUIDE = "GUIDE - Crashes and how to fix them"
WIKI = "Crash to Desktop (TWC Wiki)"


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    file: str = ""
    line: int = 0
    what: str = ""
    #: when it bites, in health.WHEN's terms
    when: str = "campaign"
    #: the record the owning screen opens, when there is one
    name: str = ""


@dataclass
class Rule:
    code: str
    label: str
    severity: str
    source: str
    when: str
    #: the mode that owns the file, for Health's Open
    mode: str
    fn: Callable = None


RULES: List[Rule] = []


def rule(code: str, label: str, severity: str, source: str, when: str, mode: str):
    def wrap(fn):
        RULES.append(Rule(code, label, severity, source, when, mode, fn))
        return fn
    return wrap


def _read(p: Path) -> str:
    try:
        return kb.read_text(p, "latin-1")
    except (OSError, UnicodeError):
        return ""


def _code(line: str) -> str:
    return line.split(";", 1)[0]


# ---------------------------------------------------------------------------


AI_DB_REL = "descr_campaign_ai_db.xml"
#: labels the engine knows without a declaration - measured, see the docstring
AI_LABELS_BUILTIN = frozenset({"papal_faction"})


@rule("ai.label_unknown", "A faction's ai_label the AI file does not declare", "fatal",
      f"{GUIDE}: an ai_label not in descr_campaign_ai_db.xml crashes that faction's turn",
      "play", "rawtext")
def _ai_label(mod) -> List[Finding]:
    from . import renames
    db = Path(mod.data) / AI_DB_REL
    if not db.is_file():
        return []                   # the game's own file is used, and declares its own
    declared = {n.lower() for n in re.findall(r'<faction_ai_label\s+name="([^"]+)"', _read(db))}
    out = []
    for camp in renames.campaign_dirs(mod):
        strat = camp / "descr_strat.txt"
        rel = strat.relative_to(Path(mod.data)).as_posix()
        faction = ""
        for i, line in enumerate(_read(strat).splitlines()):
            words = _code(line).split()
            if len(words) >= 2 and words[0] == "faction":
                faction = words[1].rstrip(",")
            if len(words) >= 2 and words[0] == "ai_label":
                label = words[1]
                if label.lower() in declared or label.lower() in AI_LABELS_BUILTIN:
                    continue
                out.append(Finding(
                    "ai.label_unknown", "fatal",
                    f"{camp.name}: {faction or 'a faction'} has ai_label {label}, and "
                    f"{AI_DB_REL} declares no <faction_ai_label name=\"{label}\">. The guide: "
                    f"the game crashes during that faction's turn.",
                    file=rel, line=i + 1, what=f"{camp.name}|{faction}|{label}",
                    when="play", name=faction))
    return out


_EVENT = re.compile(r"\bhistoric_event\s+([A-Za-z0-9_]+)")


@rule("event.no_text", "A historic_event with no text to show", "warn",
      f"{GUIDE}: an event not listed in historic_events.txt crashes the turn it fires. "
      "Measured case-blind: DaC plays with 631 events keyed in another case",
      "play", "rawtext")
def _event_text(mod) -> List[Finding]:
    from . import campevents, renames
    keys = {k.upper() for k in campevents.event_text_pairs(mod)}
    if not keys:
        return []                   # no text file at all: the game's own is used
    out = []
    for camp in renames.campaign_dirs(mod):
        script = camp / "campaign_script.txt"
        if not script.is_file():
            continue
        rel = script.relative_to(Path(mod.data)).as_posix()
        seen = set()
        text = _read(script)
        # One pass over the whole script: ROCSS has eight campaigns of scripts
        # that run to tens of thousands of lines, and splitting each into lines
        # first cost four seconds. A match after a `;` on its line is a comment.
        for m in _EVENT.finditer(text):
            start = text.rfind("\n", 0, m.start()) + 1
            if ";" in text[start:m.start()] or m.group(1).lower() in seen:
                continue
            ev = m.group(1)
            seen.add(ev.lower())
            if f"{ev.upper()}_TITLE" in keys or f"{ev.upper()}_BODY" in keys:
                continue
            i = text.count("\n", 0, m.start())   # only for a finding: it is O(n)
            out.append(Finding(
                "event.no_text", "warn",
                f"{camp.name}: the script fires historic_event {ev}, and "
                f"text/historic_events.txt has neither {{{ev.upper()}_TITLE}} nor "
                f"{{{ev.upper()}_BODY}}. The guide says this crashes the turn it fires on; "
                f"some shipping mods carry one on a path that never runs.",
                file=rel, line=i + 1, what=f"{camp.name}|{ev.lower()}", when="play"))
    return out


@rule("trait.antitrait_cultures", "An antitrait excluded for different cultures", "fatal",
      f"{GUIDE}: a culture that has a trait excluded but not its antitrait crashes when "
      "a general swaps one for the other", "play", "traits")
def _antitrait(mod) -> List[Finding]:
    from . import traits
    path = Path(mod.edct_path)
    if not path.exists():
        return []
    tf = traits.parse_file(path)
    by = {t.name: t for t in tf.traits}
    out, done = [], set()
    for t in tf.traits:
        mine = {c.lower() for c in t.exclude_cultures}
        for a in t.anti_traits:
            other = by.get(a)
            if other is None or frozenset((t.name, a)) in done:
                continue
            done.add(frozenset((t.name, a)))
            theirs = {c.lower() for c in other.exclude_cultures}
            if mine == theirs:
                continue
            diff = sorted(mine ^ theirs)
            out.append(Finding(
                "trait.antitrait_cultures", "fatal",
                f"{t.name} and its antitrait {a} exclude different cultures "
                f"({', '.join(diff)}). The guide: a general of that culture crashes the "
                f"game when one trait replaces the other. Exclude the same cultures on both.",
                file=path.name, line=t.start + 1, what=f"{t.name}|{a}", when="play",
                name=t.name))
    return out


PATH_FILES = ("descr_banners_new.xml", "descr_projectile.txt", "descr_projectile_new.txt",
              "descr_standards.txt")
_ABS = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s\"<>,]*")


@rule("path.absolute", "An absolute path in a battle file", "warn",
      f"{GUIDE}: absolute paths in the banner, projectile and standard files crash "
      "the battle once the mod folder is renamed or moved", "battle", "rawtext")
def _absolute(mod) -> List[Finding]:
    out = []
    for rel in PATH_FILES:
        p = Path(mod.data) / rel
        if not p.is_file():
            continue
        for i, line in enumerate(_read(p).splitlines()):
            for m in _ABS.finditer(_code(line) if rel.endswith(".txt") else line):
                out.append(Finding(
                    "path.absolute", "warn",
                    f"{rel} names {m.group(0)}, a path on one particular disk. It works "
                    f"until the mod folder is renamed or moved, and then the battle "
                    f"that needs it crashes. Write it relative to data/.",
                    file=rel, line=i + 1, what=f"{rel}|{m.group(0).lower()}",
                    when="battle", name=rel))
    return out


MODELDB_REL = "unit_models/battle_models.modeldb"


@rule("modeldb.spaces", "A run of spaces in the battle models file", "warn",
      f"{GUIDE}: 'multiple spaces instead of one or two' in battle_models.modeldb "
      "crashes the battle that loads the model", "battle", "bmdb")
def _modeldb_spaces(mod) -> List[Finding]:
    p = Path(mod.data) / MODELDB_REL
    if not p.is_file():
        return []
    out = []
    for i, raw in enumerate(p.read_bytes().split(b"\n")):
        if b"   " in raw.rstrip():
            text = raw.decode("latin-1").strip()
            out.append(Finding(
                "modeldb.spaces", "warn",
                f"line {i + 1} has three or more spaces in a row: {text[:80]}. The guide "
                f"says the game crashes loading a battle with that model. A path with "
                f"spaces in it is the one legitimate case.",
                file=MODELDB_REL, line=i + 1, what=f"{text[:120]}", when="battle"))
            if len(out) >= 50:
                break
    return out


#: Stated by a guide, measured, and not a rule. Kept so the next reader of the
#: guide finds the answer instead of the question.
REFUSED: Tuple[dict, ...] = (
    {"claim": "A faction that a building's later level names but an earlier level "
              "omits crashes the game at the first turn or in the building browser",
     "source": WIKI,
     "measured": "DaC has 24 such levels in 14 building lines and ROCSS 6 in 4, "
                 "and both play (2026-09-22)"},
    {"claim": "An event name is matched case-sensitively against historic_events.txt",
     "source": GUIDE,
     "measured": "631 of DaC's 633 script events differ from their text key only by "
                 "case, and DaC plays; event.no_text matches case-blind"},
)


def run(mod) -> Tuple[List[Tuple[Rule, Finding]], List[dict]]:
    """Every rule. A rule that raises is reported, never lost with the others."""
    found, failed = [], []
    for r in RULES:
        try:
            found += [(r, f) for f in r.fn(mod)]
        except Exception as e:                          # noqa: BLE001
            failed.append({"code": r.code, "error": f"{type(e).__name__}: {e}"})
    return found, failed
