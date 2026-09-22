"""One door to every check (Phase 54, M17).

The toolkit has more validators than any of the reference tools and, until
this, no single place that ran them: the map rules live on the map screen, the
faction audit on the faction screen, the EDB rules on the buildings screen and
the file checkers inside each file's editor. Somebody whose mod crashes had to
know all of that before they could ask "what is wrong with it".

This module asks every one of them and hands back one list, in one shape. It
owns no rule. Each **source** is an adapter from one validator's own answer to
a :class:`Finding`, and the screen that owns a finding is still the place to
fix it - every finding says which screen that is.

**Only the fast ones run.** Measured cold on the two installed mods on
2026-09-22: the map rules 0.9s and 2.8s, the faction audit about 1.2s, the EDB
checks 0.2s. The four cleanup audits cost 7s to 95s each (cards on ROCSS is the
95) and are about a tidy mod rather than one that starts, so they are listed
in :data:`SLOW` as a door into their own screens and never run from here.

**A source that throws is a failed source**, reported with its error, never an
empty one and never the whole answer. That is `mapcheck.run`'s rule for its own
rules, one level up: losing the faction audit to a broken trait file would be
the failure that makes a dashboard untrustworthy.

**Severity.** The map and EDB rules already say `fatal`/`warn`/`note`. Several
file checkers say `fatal` as a bool, and three (traits, ancillaries, factions)
say nothing at all - but their sentences do: "more than 8 crashes the game",
"the game stops loading the file here". :func:`severity_of` reads that, so a
checker that learns a new crash is ranked by the sentence it already writes,
with no second table here to forget to update.

**When** is the column the two crash guides add. Nobody arrives saying "my
EDB has a fatal"; they arrive saying "it crashes loading the campaign". Each
source says when its findings usually bite, and a sentence that names a panel
or a battle moves its finding there.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

SEVERITIES = ("fatal", "warn", "note")

#: When a finding bites, in the order somebody playing meets them.
WHEN = (
    ("launch", "Starting the game", "Read before the main menu: the unit, trait, "
     "ancillary and faction files. A fault here is a crash or a black screen at start."),
    ("campaign", "Loading a campaign", "The map, the settlements, the buildings and "
     "who starts where. A fault here crashes the campaign on its loading screen."),
    ("panel", "Opening a panel", "Only when a particular scroll, detail screen or "
     "building browser is opened."),
    ("battle", "In battle", "When a battle loads the models and the units in it."),
    ("play", "During play", "Later: an AI turn, an event firing, a character "
     "gaining a trait."),
)
WHEN_IDS = tuple(w[0] for w in WHEN)

# A checker's own sentence, read for how bad it is. Kept to phrases the checkers
# actually write (see tests/test_health.py, which holds these to real messages).
_FATAL_WORDS = re.compile(
    r"crash|stops loading|will not load|won't load|does not load|stops recognising|"
    r"refuses to load|can(?:no|')t be read|cannot start|black screen|ctd\b",
    re.I)
_PANEL_WORDS = re.compile(r"detail screen|scroll|panel|building browser|"
                          r"when (?:it is )?opened|opening", re.I)
_BATTLE_WORDS = re.compile(r"\bbattle\b", re.I)


def severity_of(raw: dict, default: str = "warn") -> str:
    """``fatal``/``warn``/``note`` for one checker's finding.

    An explicit ``severity`` wins; then ``fatal: True``; then the sentence."""
    sev = str(raw.get("severity") or "").lower()
    if sev in SEVERITIES:
        return sev
    if raw.get("fatal") is True:
        return "fatal"
    if _FATAL_WORDS.search(str(raw.get("message") or "")):
        return "fatal"
    return default


def when_of(message: str, default: str) -> str:
    if _PANEL_WORDS.search(message or ""):
        return "panel"
    if _BATTLE_WORDS.search(message or ""):
        return "battle"
    return default


@dataclass
class Finding:
    """One thing wrong, whichever validator found it.

    ``what`` is the identity and, as in :class:`mapcheck.Finding`, never holds a
    line number. ``open`` is where the page goes to show it: a mode, and the
    record in that mode when there is one."""

    source: str
    code: str
    severity: str
    message: str
    file: str = ""
    line: int = 0
    what: str = ""
    when: str = "campaign"
    count: int = 1
    #: already there when the mod's baseline was taken (map rules only)
    baseline: bool = False
    open: Dict[str, str] = field(default_factory=dict)


@dataclass
class Source:
    id: str
    label: str
    #: the mode the page opens for this source's findings
    mode: str
    file: str
    when: str
    run: Callable[..., List[Finding]]
    #: needs the campaign map, so off where the map screen is off
    needs_map: bool = False


SOURCES: List[Source] = []


def source(id: str, label: str, mode: str, file: str, when: str, needs_map: bool = False):
    def wrap(fn):
        SOURCES.append(Source(id, label, mode, file, when, fn, needs_map))
        return fn
    return wrap


def _plain(rows: Iterable[dict], src: str, file: str, when: str, mode: str,
           name_key: str, code_prefix: str) -> List[Finding]:
    """The file checkers' shape: ``{kind|code, <name>, line?, message, fatal?}``."""
    out = []
    for r in rows:
        msg = str(r.get("message") or "")
        name = str(r.get(name_key) or r.get("name") or "")
        code = str(r.get("code") or r.get("kind") or "finding")
        out.append(Finding(
            source=src, code=f"{code_prefix}.{code}", severity=severity_of(r),
            message=(f"{name}: {msg}" if name and name not in msg else msg),
            file=file, line=int(r.get("line") or 0),
            what=f"{name}|{code}", when=when_of(msg, when),
            open={"mode": mode, "name": name}))
    return out


# ---------------------------------------------------------------------------
# the sources


@source("map", "Campaign map rules", "campmap", "world/maps", "campaign", needs_map=True)
def _map(mod, ctx) -> List[Finding]:
    from . import mapcheck
    cm = ctx["map_for"](ctx.get("campaign") or "")
    rep = mapcheck.run(mod, cm, ctx.get("campaign") or "")
    out = []
    for f in rep.findings:
        out.append(Finding(
            source="map", code=f.code, severity=f.severity, message=f.message,
            file=f.file, line=f.line, what=f.what, count=f.count,
            baseline=f.baseline, when=when_of(f.message, "campaign"),
            open={"mode": "campmap", "key": f.key}))
    for r in rep.failed:
        out.append(Finding(
            source="map", code=str(r.get("code") or "rule"), severity="warn",
            message=f"this rule could not run: {r.get('error') or r}",
            what=f"failed|{r.get('code')}", when="campaign",
            open={"mode": "campmap"}))
    return out


@source("factions_audit", "Is every faction complete", "factions",
        "descr_sm_factions.txt and five more", "campaign")
def _faction_audit(mod, ctx) -> List[Finding]:
    from . import factionaudit
    rep = factionaudit.audit(mod, ctx.get("campaign") or "")
    out = []
    if rep.get("error"):
        out.append(Finding("factions_audit", "audit.roster", "fatal", rep["error"],
                           file="descr_sm_factions.txt", what="roster",
                           when="launch", open={"mode": "factions"}))
    for fac in rep.get("factions") or []:
        for row in fac.get("rows") or []:
            if row.get("state") != "missing":
                continue
            sev = "warn" if row.get("level") == "gap" else "note"
            out.append(Finding(
                source="factions_audit", code=f"audit.{row.get('id')}", severity=sev,
                message=f"{fac.get('label') or fac.get('slot')}: {row.get('label')} - "
                        f"{row.get('detail') or 'missing'}",
                file=str(row.get("rel") or ""), what=f"{fac.get('slot')}|{row.get('id')}",
                when="campaign", open={"mode": "factions", "name": str(fac.get("slot") or "")}))
    return out


@source("edb", "Buildings: the tree and recruitment", "buildings",
        "export_descr_buildings.txt", "campaign")
def _edb(mod, ctx) -> List[Finding]:
    from . import buildings
    rep = buildings.checks(mod)
    out = []
    for f in (rep.get("tree") or {}).get("findings") or []:
        out.append(Finding(
            source="edb", code=f["code"], severity=f["severity"], message=f["message"],
            file=buildings.EDB_REL, line=int(f.get("line") or 0), what=f.get("what", ""),
            count=int(f.get("count") or 1), when=when_of(f["message"], "campaign"),
            open={"mode": "buildings", "name": f.get("building", "")}))
    # The recruitment checks are the unit editor's half: a unit that stops being
    # trainable up a chain, or trained twice by one level. Worth knowing, never a
    # crash, so notes - and folded to one per building line, because DaC has
    # 2 151 of them unit by unit and a door that opens on two thousand notes is
    # a door nobody reads past. The building's own Checks panel lists each one.
    # The city/castle comparison is a tool, not a finding, and is left out.
    for ln in rep.get("lines") or []:
        for key, code, says in (
                ("gaps", "recruit.gap", "not trained at every level above the one that first trains them"),
                ("dupes", "recruit.twice", "trained twice by one level")):
            units = sorted({str(x.get("unit") or "") for x in (ln.get(key) or [])})
            if not units:
                continue
            shown = ", ".join(units[:4]) + (f" and {len(units) - 4} more" if len(units) > 4 else "")
            out.append(Finding(
                source="edb", code=code, severity="note", count=len(units),
                message=f"{ln['line']}: {len(units)} unit{'s' if len(units) != 1 else ''} "
                        f"{says} ({shown})",
                file=buildings.EDB_REL, what=f"{ln['line']}|{code}",
                when="play", open={"mode": "buildings", "name": ln["line"]}))
    return out


@source("edu", "Units: the engine's ceilings", "edit", "export_descr_unit.txt", "launch")
def _edu(mod, ctx) -> List[Finding]:
    from . import educeil, modflags
    rows = modflags.uncapped(educeil.mod_findings(mod.edu.units), mod)
    return _plain(rows, "edu", "export_descr_unit.txt", "launch", "edit", "name", "edu")


@source("traits", "Traits", "traits", "export_descr_character_traits.txt", "launch")
def _traits(mod, ctx) -> List[Finding]:
    from . import traits, triggers, modflags
    path = Path(mod.edct_path)
    if not path.exists():
        return []
    rows = modflags.uncapped(traits.check_file(traits.parse_file(path),
                                               triggers.parse_file(path)), mod)
    return _plain(rows, "traits", path.name, "launch", "traits", "trait", "trait")


@source("ancillaries", "Ancillaries", "ancillaries", "export_descr_ancillaries.txt", "launch")
def _ancillaries(mod, ctx) -> List[Finding]:
    from . import ancillaries, triggers, modflags
    path = Path(mod.eda_path)
    if not path.exists():
        return []
    rows = modflags.uncapped(ancillaries.check_file(ancillaries.parse_file(path),
                                                    triggers.parse_file(path), mod), mod)
    return _plain(rows, "ancillaries", path.name, "launch", "ancillaries",
                  "ancillary", "anc")


@source("factions", "Factions", "factions", "descr_sm_factions.txt", "launch")
def _factions(mod, ctx) -> List[Finding]:
    from . import factions, modflags
    path = factions.path_for(mod)
    if not path.is_file():
        return []
    rows = modflags.uncapped(factions.check_file(factions.parse_file(path), mod), mod)
    return _plain(rows, "factions", factions.REL, "launch", "factions", "name", "faction")


@source("guilds", "Guilds", "guilds", "export_descr_guilds.txt", "play")
def _guilds(mod, ctx) -> List[Finding]:
    from . import guilds
    if not guilds.path_for(mod).exists():
        return []
    gf, text = guilds.read(mod)
    rows = guilds.check_file(gf, guilds.trigger_file(text), guilds.building_names(mod))
    return _plain(rows, "guilds", guilds.GUILDS_REL, "play", "guilds", "guild", "guild")


@source("campdb", "Campaign constants", "campdb", "descr_campaign_db.xml", "campaign")
def _campdb(mod, ctx) -> List[Finding]:
    from . import campdb
    if not campdb.path_for(mod).exists():
        return []
    db, _ = campdb.read(mod)
    # "key" is what a campdb finding calls its tag ("agents/assassinate_chance_max"),
    # and it is what the screen's cdbOpen takes - `name` would come back empty and
    # the row would land on the screen with nothing picked.
    return _plain(campdb.check_file(db), "campdb", campdb.REL, "campaign", "campdb",
                  "key", "campdb")


@source("minor", "Rebels, religions, resources, cultures, names", "minor",
        "five campaign files", "campaign")
def _minor(mod, ctx) -> List[Finding]:
    from . import minorfiles
    out = []
    for t in minorfiles.TABS:
        if not minorfiles.path_for(mod, t.id).is_file():
            continue
        parsed, _ = minorfiles.read_any(mod, t.id)
        rows = minorfiles.check_any(mod, t.id, parsed)
        mode = "cultures" if t.id == "cultures" else "minor"
        for f in _plain(rows, "minor", t.rel, "campaign", mode, "name", t.id):
            if mode == "minor":
                f.open["tab"] = t.id
            out.append(f)
    return out


@source("crash", "What the crash guides name", "rawtext", "five files", "play")
def _crash(mod, ctx) -> List[Finding]:
    """Phase 54b's rules: the guides' causes that belonged to no module."""
    from . import crashrules
    found, failed = crashrules.run(mod)
    out = []
    for r, f in found:
        open_ = {"mode": r.mode}
        if r.mode == "rawtext":
            open_.update(rel=f.file, line=str(f.line))
        elif f.name:
            open_["name"] = f.name
        out.append(Finding(
            source="crash", code=f.code, severity=f.severity, message=f.message,
            file=f.file, line=f.line, what=f.what, when=f.when, open=open_))
    for x in failed:
        out.append(Finding(
            source="crash", code=x["code"], severity="warn",
            message=f"this rule could not run: {x['error']}",
            what=f"failed|{x['code']}", when="play", open={"mode": "rawtext"}))
    return out


#: The cleanup audits: listed, never run here (see the module docstring).
SLOW = (
    {"id": "bmdb", "label": "Battle models no unit uses, and files nothing names",
     "mode": "bmdb", "cost": "10 to 30 seconds"},
    {"id": "dupes", "label": "Battle models entered twice (the game reads the first)",
     "mode": "bmdb", "cost": "7 to 20 seconds"},
    {"id": "stratmap", "label": "Strat map models nothing draws",
     "mode": "stratmap", "cost": "7 to 16 seconds"},
    {"id": "cards", "label": "Unit cards for units that are gone, and copies",
     "mode": "cards", "cost": "25 to 95 seconds"},
)


def _refused() -> List[dict]:
    from . import crashrules
    return [dict(x) for x in crashrules.REFUSED]


# ---------------------------------------------------------------------------
# the run


def run(mod, map_for: Optional[Callable] = None, campaign: str = "",
        only: Iterable[str] = ()) -> dict:
    """Every fast source over one mod. ``map_for(campaign)`` gives the map, and
    without it the map source is skipped (the build has the map screen off)."""
    ctx = {"map_for": map_for, "campaign": campaign}
    want = set(only or ())
    findings: List[Finding] = []
    sources = []
    t_all = time.perf_counter()
    for s in SOURCES:
        if want and s.id not in want:
            continue
        row = {"id": s.id, "label": s.label, "mode": s.mode, "file": s.file,
               "when": s.when, "state": "ok", "error": "", "ms": 0,
               "counts": {k: 0 for k in SEVERITIES}}
        if s.needs_map and map_for is None:
            row["state"] = "off"
            sources.append(row)
            continue
        t = time.perf_counter()
        try:
            got = s.run(mod, ctx)
        except Exception as e:                      # noqa: BLE001 - the point
            row["state"] = "failed"
            row["error"] = f"{type(e).__name__}: {e}"
            got = []
        row["ms"] = int((time.perf_counter() - t) * 1000)
        for f in got:
            if f.severity not in SEVERITIES:
                f.severity = "warn"
            if f.when not in WHEN_IDS:
                f.when = s.when
            row["counts"][f.severity] += 1
        findings += got
        sources.append(row)
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings.sort(key=lambda f: (order[f.severity], f.baseline, WHEN_IDS.index(f.when),
                                 f.source, f.message))
    return {
        "mod": getattr(mod, "name", ""), "campaign": campaign,
        "ms": int((time.perf_counter() - t_all) * 1000),
        "findings": [asdict(f) for f in findings],
        "counts": {k: sum(1 for f in findings if f.severity == k) for k in SEVERITIES},
        "sources": sources,
        "slow": [dict(x) for x in SLOW],
        # what the crash guides claim and measuring refused, so it is findable
        "refused": _refused(),
        "when": [{"id": w[0], "label": w[1], "help": w[2]} for w in WHEN],
    }
