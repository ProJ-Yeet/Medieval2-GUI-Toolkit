"""Is this faction complete? (Phase 21, D6.)

A faction is a slot named in a dozen files, and every one of them is somebody's
screen here already: the roster is Factions, the units are the Unit Editor, the
campaign entry is the map's faction tab. What nobody had was the one question a
modder asks while standing on that faction - *which of those files still has
never heard of it?* - answered in one place, with the fix offered beside each
answer. This module is the answer; ``web/js/facaudit.js`` draws it on 17f's
faction screen.

**It reads the mod once for every faction at once.** :class:`Census` makes one
pass over each file and counts every slot it names, so the audit of one faction
and the audit of all thirty cost the same - which is what lets the faction
picker carry a gap count on every row, and what the template suggestion needs,
since "the most complete faction of the same culture" is a question about all
of them.

**Gap or note is measured, not copied.** Demir's audit (``factionDependencyAudit``)
blocks on the off-map navy models and calls the voice accent optional. Measured
on the two installed mods, that is backwards for the files that matter here:

* every one of the 61 factions in Divide and Conquer and Third Age Reforged has
  a voice accent, a ``descr_character.txt`` entry, a ``descr_names.txt``
  section, strat-map textures and an ``{SLOT}`` text key, and every one but a
  script dummy owns units and is named by the EDB - those are **gaps**;
* Third Age Reforged ships three factions with no off-map navy block, three
  with no settlement populace, and twenty with no diplomatic standing rule at
  all, and both mods load - so those are **notes**, shown and not counted. A
  check that calls a working mod broken is one nobody believes twice (the
  baseline rule, Locked decisions).

The same measurement dropped a check Demir does not have and this module
nearly did: "an owned unit whose battle model has no skin for the faction".
Third Age Reforged has seven to seventeen of those *per faction* and plays, so
it would have been thirty lines of noise on every screen.

**The campaign half is per campaign, and absence is ordinary.** Fellowship
Campaign leaves fourteen of Third Age Reforged's thirty factions out entirely,
so "not in this campaign" is a note. What is a gap is the pairing the engine
reads: every faction that *has* a ``descr_strat.txt`` block in a campaign has a
win-conditions record there, in all four campaigns installed, without one
exception.

**The repair is the clone, pointed at a slot that already exists.**
:mod:`unittransfer.factionclone` knows how to put a faction into each of these
files by copying a donor's record - and "copy the missing record from a
faction that has one" is exactly that operation with the new slot already in
the roster. So :func:`repair_plan` runs the same cloner per gap
(:func:`factionclone.clone_file`) and :func:`factionclone.apply` writes it: one
backup set, one log entry, one undo. The two campaign gaps are not copies -
two factions cannot start in the same settlement - so they are links to the two
tabs that make them (New faction and Winning), the way the clone's own plan
has always pointed at them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import factionclone as fc
from . import factions as fac
from . import flatrecord as fr
from . import keyblock as kb

ENCODING = fc.ENCODING


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    rel: str                       # under data/; a campaign check says which file
    level: str                     # "gap" is counted; "note" is shown and not
    #: what fixes it: "clone" (a factionclone job over `rel`), "strat" / "wins"
    #: (a tab on the campaign screen), "addfaction" (the clone itself), or ""
    fix: str = ""
    why: str = ""


STRAT_NAME = "descr_strat.txt"
WINS_NAME = "descr_win_conditions.txt"

CHECKS: Tuple[Check, ...] = (
    Check("roster", "Faction roster", fac.REL, "gap", "addfaction",
          "the slot itself - every other file points at it"),
    Check("text", "Shown name and event text", "text/expanded.txt", "gap", "clone",
          "without the {SLOT} key the game shows the code name; without the "
          "EMT_ keys its event messages show raw keys"),
    Check("names", "Character names", "descr_names.txt", "gap", "clone",
          "the pool every character it spawns is named from"),
    Check("characters", "Agents and generals", "descr_character.txt", "gap", "clone",
          "which character types it may field - a named character first of all"),
    Check("units", "Units it may recruit", "export_descr_unit.txt", "gap", "clone",
          "an ownership line naming it is what lets it have an army"),
    Check("generals", "A bodyguard unit", "export_descr_unit.txt", "note", "",
          "a general_unit it owns, which a named character leads"),
    Check("buildings", "Recruitment and construction", "export_descr_buildings.txt",
          "gap", "clone",
          "every `requires factions { ... }` that lets it build or recruit"),
    Check("accent", "Voice accent", "descr_sounds_accents.txt", "gap", "clone",
          "the accent its characters speak with on the campaign map"),
    Check("strat_models", "Campaign map models", "descr_model_strat.txt", "gap", "clone",
          "the strat-map texture for each agent model"),
    Check("skins", "Battle model skins", "unit_models/battle_models.modeldb", "note",
          "clone", "a texture record in the models its units use"),
    Check("populace", "Settlement populace", "descr_lbc_db.txt", "note", "clone",
          "the civilians that walk its streets"),
    Check("navy", "Off-map navy models", "descr_offmap_models.txt", "note", "clone",
          "the ships shown at the edge of the map"),
    Check("standing", "Diplomatic standing", "descr_faction_standing.txt", "note",
          "clone", "the standing rules that name it, on either side"),
    Check("campaign", "Campaign start", STRAT_NAME, "note", "strat",
          "a block in this campaign's descr_strat.txt"),
    Check("wins", "Win conditions", WINS_NAME, "gap", "wins",
          "a faction with a campaign block needs a record here"),
)
BY_ID: Dict[str, Check] = {c.id: c for c in CHECKS}

#: which factionclone job repairs each "clone" check - looked up by file, so the
#: two lists cannot disagree about where a record lives
JOB_BY_REL: Dict[str, fc.Job] = {j.rel: j for j in fc.JOBS}

#: The engine's own factions. `slave` is in every file by design; it is never
#: offered as a template for somebody else, because a rebel's records (177
#: diplomatic rules in DaC, 889 units) are nothing a real faction should copy.
NEVER_TEMPLATE = ("slave",)


def _tok_set(value: str) -> List[str]:
    """``"venice, sicily,  milan ; note"`` -> ``["venice", "sicily", "milan"]``."""
    return [t.strip().lower() for t in value.split(";", 1)[0].split(",") if t.strip()]


def _read(data: Path, rel: str, encoding: str = ENCODING) -> Optional[str]:
    path = data / rel
    if not path.is_file():
        return None
    try:
        return kb.to_newline(kb.read_text(path, encoding), "\n")
    except (OSError, UnicodeError):
        return None


# ---------------------------------------------------------------------------
# the census: one pass per file, every slot at once


class Census:
    """How often every file names every faction, read once.

    Each attribute is ``None`` when its file is not on disk - "a rule with no
    evidence reports nothing" (Locked decisions) - and otherwise a dict keyed by
    the lower-case slot. Nothing here is parsed twice: the EDU and the modeldb
    are the mod's own cached parses.
    """

    def __init__(self, mod, campaign: str = ""):
        from . import campstrat
        self.mod = mod
        data = Path(mod.data)
        self.campaign = campaign or campstrat.DEFAULT_CAMPAIGN

        # -- the roster --------------------------------------------------
        self.slots: List[str] = []
        self.cultures: Dict[str, str] = {}
        self.roster_error = ""
        path = fac.path_for(mod)
        if path.is_file():
            try:
                rf = fac.parse_file(path)
                for r in rf.records:
                    slot = fac.slot_of(r.name).lower()
                    if slot and slot not in self.cultures:
                        self.slots.append(slot)
                        self.cultures[slot] = r.get("culture").strip(",").lower()
            except (fr.RecordError, OSError, UnicodeError) as e:
                self.roster_error = str(e)
        else:
            self.roster_error = (f"{getattr(mod, 'name', '?')} keeps no loose "
                                 f"{fac.REL} - it is inside the game's .pack "
                                 "archives until the mod is unpacked")

        self._text(data)
        self._name_pools(data)
        self._characters(data)
        self._units()
        self.edb = self._braced(_read(data, "export_descr_buildings.txt"), ("factions",))
        self._accents(data)
        self._strat_models(data)
        self._skins()
        self.populace = self._heads(_read(data, "descr_lbc_db.txt"), "faction")
        self.navy = self._heads(_read(data, "descr_offmap_models.txt"), "faction")
        self.standing = self._braced(_read(data, "descr_faction_standing.txt"),
                                     ("factions", "exclude_factions"))
        self._campaigns()

    # -- one reader per shape -------------------------------------------------

    def _text(self, data: Path) -> None:
        """``{SLOT}`` and the ``EMT_`` family, from the .txt or else the .bin."""
        from . import stringsbin
        self.text_source = ""
        self.text_keys: Optional[Dict[str, str]] = None
        txt = data / "text" / "expanded.txt"
        if txt.is_file():
            try:
                body = kb.read_text(txt, "utf-16")
            except (OSError, UnicodeError):
                body = None
            if body is not None:
                self.text_source = "txt"
                self.text_keys = {m.group(1).upper(): m.group(2).strip()
                                  for m in re.finditer(
                                      r"^[ \t]*\{([A-Za-z0-9_]+)\}([^\r\n]*)", body, re.M)}
                return
        pairs = stringsbin.load_pairs(stringsbin.bin_path_for(txt))
        if pairs:
            self.text_source = "bin"
            self.text_keys = {k.upper(): v for k, v in pairs.items()}

    def event_keys(self, slot: str) -> int:
        """How many ``EMT_*`` / ``*_SLOT_*`` keys carry the slot as a word."""
        if not self.text_keys:
            return 0
        up = slot.upper()
        tok = re.compile(r"(?<![A-Za-z0-9])" + re.escape(up) + r"(?![A-Za-z0-9])")
        return sum(1 for k in self.text_keys if k != up and tok.search(k))

    def _name_pools(self, data: Path) -> None:
        """``faction: x`` sections, with how many names of each kind."""
        text = _read(data, "descr_names.txt")
        self.pools: Optional[Dict[str, Dict[str, int]]] = None
        if text is None:
            return
        self.pools = {}
        cur, sub = "", ""
        for line in text.split("\n"):
            code = kb.code_of(line)
            if not code:
                continue
            m = re.match(r"faction\s*:\s*([A-Za-z0-9_]+)", code, re.I)
            if m:
                cur, sub = m.group(1).lower(), ""
                self.pools.setdefault(cur, {"characters": 0, "surnames": 0, "women": 0})
                continue
            word = code.lower()
            if word in ("characters", "surnames", "women"):
                sub = word
            elif cur and sub:
                self.pools[cur][sub] += 1

    def _characters(self, data: Path) -> None:
        """Which ``type`` sections of descr_character.txt list each faction."""
        text = _read(data, "descr_character.txt")
        self.char_types: List[str] = []
        self.chars: Optional[Dict[str, Set[str]]] = None
        if text is None:
            return
        self.chars = {}
        cur = ""
        for line in text.split("\n"):
            code = kb.code_of(line)
            m = re.match(r"type\s+(.+)$", code, re.I)
            if m:
                cur = " ".join(m.group(1).split()).lower()
                if cur not in self.char_types:
                    self.char_types.append(cur)
                continue
            m = re.match(r"faction\s+(.+)$", code, re.I)
            if m and cur:
                for slot in _tok_set(m.group(1)):
                    self.chars.setdefault(slot, set()).add(cur)

    def _units(self) -> None:
        self.units: Optional[Dict[str, int]] = None
        self.generals: Optional[Dict[str, int]] = None
        try:
            units = self.mod.edu.units
        except Exception:                          # the EDU refuses: no evidence
            return
        self.units, self.generals = {}, {}
        for u in units:
            general = (u.category or "").lower() != "ship" and any(
                a.lower() == "general_unit" for a in u.attributes)
            for o in {o.strip().lower() for o in u.ownership if o.strip()}:
                self.units[o] = self.units.get(o, 0) + 1
                if general:
                    self.generals[o] = self.generals.get(o, 0) + 1

    @staticmethod
    def _braced(text: Optional[str], kws) -> Optional[Dict[str, int]]:
        """``factions { a, b, }`` clauses - the pattern :func:`clone_braced_list`
        joins, so the count and the repair agree about what a clause is."""
        if text is None:
            return None
        out: Dict[str, int] = {}
        pat = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(k) for k in kws)
                         + r")[ \t]*\{([^{}]*)\}", re.I)
        for m in pat.finditer(text):
            for slot in {t.strip().lower() for t in m.group(2).split(",") if t.strip()}:
                out[slot] = out.get(slot, 0) + 1
        return out

    def _accents(self, data: Path) -> None:
        text = _read(data, "descr_sounds_accents.txt")
        self.accents: Optional[Dict[str, str]] = None
        if text is None:
            return
        self.accents = {}
        cur = ""
        for line in text.split("\n"):
            code = kb.code_of(line)
            m = re.match(r"accent\s+(\S+)", code, re.I)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"factions\b(.*)$", code, re.I)
            if m:
                for slot in _tok_set(m.group(1)):
                    self.accents.setdefault(slot, cur)

    def _strat_models(self, data: Path) -> None:
        text = _read(data, "descr_model_strat.txt")
        self.strat_models: Optional[Dict[str, int]] = None
        if text is None:
            return
        self.strat_models = {}
        for m in re.finditer(r"^[ \t]*texture[ \t]+([A-Za-z0-9_]+)[ \t]*,", text,
                             re.M | re.I):
            slot = m.group(1).lower()
            self.strat_models[slot] = self.strat_models.get(slot, 0) + 1

    def _skins(self) -> None:
        self.skins: Optional[Dict[str, int]] = None
        if not Path(self.mod.data, "unit_models/battle_models.modeldb").is_file():
            return
        try:
            db = self.mod.modeldb
        except Exception:
            return
        self.skins = {}
        for e in db.entries:
            for slot in {t.faction.lower() for t in e.main_textures}:
                self.skins[slot] = self.skins.get(slot, 0) + 1

    @staticmethod
    def _heads(text: Optional[str], kw: str) -> Optional[Set[str]]:
        """``faction x`` heads - descr_lbc_db's paragraphs, the off-map blocks."""
        if text is None:
            return None
        return {m.group(1).lower() for m in re.finditer(
            r"^[ \t]*" + re.escape(kw) + r"[ \t]+([A-Za-z0-9_]+)", text, re.M | re.I)}

    def _campaigns(self) -> None:
        """Every campaign's faction blocks, and this campaign's win records."""
        from . import campstrat, winconds
        self.campaigns: List[str] = []
        try:
            self.campaigns = campstrat.campaign_paths(self.mod)
        except OSError:
            pass
        #: campaign -> slot -> (settlements, characters, has a leader)
        self.strat: Dict[str, Dict[str, Tuple[int, int, bool]]] = {}
        self.strat_errors: Dict[str, str] = {}
        for camp in self.campaigns:
            try:
                sf = campstrat.read_strat(self.mod, camp)
            except Exception as e:                 # a campaign that will not read
                self.strat_errors[camp] = str(e)
                continue
            blocks = {}
            for node in sf.of_kind("faction"):
                people = sf.descendants_of(node, "character")
                blocks[node.name.lower()] = (
                    len(sf.descendants_of(node, "settlement")), len(people),
                    any(c.get("rank") == "leader" for c in people))
            self.strat[camp] = blocks
        self.wins: Optional[Set[str]] = None
        if self.campaign in self.strat:
            try:
                wf = winconds.read_wins(self.mod, self.campaign)
                self.wins = {r.faction.lower() for r in wf.records}
            except Exception:
                self.wins = None

    # -- the whole list of slots worth auditing ------------------------------

    def all_slots(self) -> List[str]:
        """The roster, then anything this campaign has a block for and the
        roster does not - the one state the roster check exists to name."""
        out = list(self.slots)
        for slot in (self.strat.get(self.campaign) or {}):
            if slot not in self.cultures:
                out.append(slot)
        return out


# ---------------------------------------------------------------------------
# one faction, row by row


def _row(chk: Check, state: str, detail: str, count: int = 0) -> Dict:
    return {"id": chk.id, "label": chk.label, "rel": chk.rel, "level": chk.level,
            "state": state, "detail": detail, "count": count, "fix": chk.fix,
            "why": chk.why}


def _plural(n: int, one: str, many: str = "") -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _verb(n: int) -> str:
    return " names" if n == 1 else " name"


def evaluate(c: Census, slot: str) -> List[Dict]:
    """Every check for one faction: ``ok``, ``missing`` or ``unknown``.

    ``unknown`` is the evidence rule: the file is not on disk, so nothing was
    checked and nothing is claimed. Whether a ``missing`` row is counted is its
    check's ``level``, never this function's.
    """
    slot = slot.lower()
    out: List[Dict] = []
    up = slot.upper()
    nofile = lambda chk: _row(chk, "unknown", f"this mod has no loose {chk.rel}, "
                                              "so nothing was checked")

    chk = BY_ID["roster"]
    if c.roster_error and not c.slots:
        out.append(_row(chk, "unknown", c.roster_error))
    elif slot in c.cultures:
        out.append(_row(chk, "ok", f"culture {c.cultures[slot] or '(none)'}", 1))
    else:
        out.append(_row(chk, "missing",
                        f"{slot} has a campaign block and no {fac.REL} record, so "
                        "the game has no faction by that name", 0))

    chk = BY_ID["text"]
    if c.text_keys is None:
        out.append(nofile(chk))
    else:
        shown = c.text_keys.get(up)
        emt = c.event_keys(slot)
        where = "" if c.text_source == "txt" else " (read from the compiled .strings.bin)"
        if shown is None:
            out.append(_row(chk, "missing", f"no {{{up}}} key, so the game shows "
                            f"`{slot}`; {_plural(emt, 'event key')}{where}", emt))
        elif not emt:
            out.append(_row(chk, "missing", f"“{shown}”, and no EMT_ keys - its "
                            f"event messages show the raw key{where}", 0))
        else:
            out.append(_row(chk, "ok", f"“{shown}” and {_plural(emt, 'event key')}"
                            + where, emt + 1))

    chk = BY_ID["names"]
    if c.pools is None:
        out.append(nofile(chk))
    elif slot in c.pools:
        p = c.pools[slot]
        out.append(_row(chk, "ok", f"{p['characters']} men's names, "
                        f"{_plural(p['surnames'], 'surname')}, "
                        f"{p['women']} women's", sum(p.values())))
    else:
        out.append(_row(chk, "missing", "no `faction:` section", 0))

    chk = BY_ID["characters"]
    if c.chars is None:
        out.append(nofile(chk))
    else:
        mine = c.chars.get(slot, set())
        named = "named character"
        total = len(c.char_types)
        if not mine:
            out.append(_row(chk, "missing", f"in none of the {total} character types", 0))
        elif named in c.char_types and named not in mine:
            out.append(_row(chk, "missing", f"in {len(mine)} of {total} types, but "
                            "not `named character` - it can have no general",
                            len(mine)))
        else:
            gone = [t for t in c.char_types if t not in mine]
            out.append(_row(chk, "ok", f"in {len(mine)} of {total} types"
                            + (f"; not {', '.join(gone[:4])}"
                               + ("…" if len(gone) > 4 else "") if gone else ""),
                            len(mine)))

    chk = BY_ID["units"]
    if c.units is None:
        out.append(nofile(chk))
    else:
        n = c.units.get(slot, 0)
        out.append(_row(chk, "ok" if n else "missing",
                        _plural(n, "unit") + _verb(n) + " it in `ownership`" if n
                        else "no unit names it in `ownership`", n))
    chk = BY_ID["generals"]
    if c.generals is None:
        out.append(nofile(chk))
    else:
        n = c.generals.get(slot, 0)
        out.append(_row(chk, "ok" if n else "missing",
                        _plural(n, "general_unit") + " it owns" if n
                        else "it owns no general_unit - the Unit Editor gives one", n))

    for cid, counts, noun in (("buildings", c.edb, "clause"),
                              ("strat_models", c.strat_models, "texture line"),
                              ("skins", c.skins, "model"),
                              ("standing", c.standing, "rule")):
        chk = BY_ID[cid]
        if counts is None:
            out.append(nofile(chk))
            continue
        n = counts.get(slot, 0)
        out.append(_row(chk, "ok" if n else "missing",
                        f"{_plural(n, noun)}{_verb(n)} it" if n else "nothing names it", n))

    chk = BY_ID["accent"]
    if c.accents is None:
        out.append(nofile(chk))
    elif slot in c.accents:
        out.append(_row(chk, "ok", f"speaks {c.accents[slot]}", 1))
    else:
        out.append(_row(chk, "missing", "in no accent's `factions` line", 0))

    for cid, heads in (("populace", c.populace), ("navy", c.navy)):
        chk = BY_ID[cid]
        if heads is None:
            out.append(nofile(chk))
        else:
            out.append(_row(chk, "ok" if slot in heads else "missing",
                            "a block of its own" if slot in heads else "no block",
                            int(slot in heads)))

    # -- the campaign half ---------------------------------------------------
    camp = c.campaign
    chk = BY_ID["campaign"]
    others = [k for k, blocks in c.strat.items() if k != camp and slot in blocks]
    elsewhere = (f"; also in {', '.join(others)}" if others else "")
    block = (c.strat.get(camp) or {}).get(slot)
    if camp not in c.strat:
        why = c.strat_errors.get(camp) or f"this mod has no {camp}/{STRAT_NAME}"
        out.append(_row(chk, "unknown", why))
    elif block is None:
        out.append(_row(chk, "missing", f"not in {camp}"
                        + (f"; in {', '.join(others)}" if others else "")
                        + (" - it is in no campaign at all" if not others else ""), 0))
    else:
        settle, people, leader = block
        out.append(_row(chk, "ok", f"{_plural(settle, 'settlement')}, "
                        f"{_plural(people, 'character')}"
                        + (", a leader" if leader else "") + elsewhere, 1))

    chk = BY_ID["wins"]
    if block is None:
        # no block, nothing to win - the pairing is the rule, not the file
        out.append(_row(chk, "ok" if camp in c.strat else "unknown",
                        "not needed - it has no block in this campaign"
                        if camp in c.strat else "no campaign to check against", 0))
    elif c.wins is None:
        out.append(_row(chk, "unknown", f"{camp} has no readable {WINS_NAME}"))
    elif slot in c.wins:
        out.append(_row(chk, "ok", "a record of its own", 1))
    else:
        out.append(_row(chk, "missing", "it has a campaign block and no record", 0))
    return out


def tally(rows: List[Dict]) -> Tuple[int, int]:
    """(gaps, notes) - a missing row counts as its check's level says."""
    gaps = sum(1 for r in rows if r["state"] == "missing" and r["level"] == "gap")
    notes = sum(1 for r in rows if r["state"] == "missing" and r["level"] == "note")
    return gaps, notes


def suggest_template(c: Census, slot: str, rows: Dict[str, List[Dict]]) -> str:
    """The faction a repair should copy from.

    The one that has the most of what this faction lacks, then the same culture
    (a Gondor clone should take Gondor's names, not Mordor's), then the fewest
    gaps of its own. Never itself, never a slot outside the roster (there would
    be nothing to copy from), and never ``slave``.
    """
    lack = {r["id"] for r in rows.get(slot, []) if r["state"] == "missing"
            and r["fix"] == "clone"}
    culture = c.cultures.get(slot, "")
    best, key = "", None
    for other in c.slots:
        if other == slot or other in NEVER_TEMPLATE:
            continue
        theirs = rows.get(other) or []
        has = sum(1 for r in theirs if r["id"] in lack and r["state"] == "ok")
        k = (-has, 0 if culture and c.cultures.get(other) == culture else 1,
             tally(theirs)[0], other)
        if key is None or k < key:
            best, key = other, k
    return best


def audit(mod, campaign: str = "") -> Dict:
    """Every faction in the mod, every check, and a template for each."""
    c = Census(mod, campaign)
    slots = c.all_slots()
    rows = {s: evaluate(c, s) for s in slots}
    out = []
    for s in slots:
        gaps, notes = tally(rows[s])
        out.append({
            "slot": s, "label": fac.label(s, c.text_keys or {}),
            "culture": c.cultures.get(s, ""), "in_roster": s in c.cultures,
            "gaps": gaps, "notes": notes,
            "template": suggest_template(c, s, rows) if s in c.cultures else "",
            "rows": rows[s]})
    return {"mod": getattr(mod, "name", ""), "campaign": c.campaign,
            "campaigns": list(c.campaigns), "error": c.roster_error if not slots else "",
            "checks": [{"id": k.id, "label": k.label, "rel": k.rel, "level": k.level,
                        "fix": k.fix, "why": k.why} for k in CHECKS],
            "factions": out}


# ---------------------------------------------------------------------------
# the repair


def repair_plan(mod, body: dict) -> fc.ClonePlan:
    """Copy the records ``faction`` is missing out of ``template``.

    ``checks`` names which rows to repair; empty means every repairable GAP the
    faction has and the template does not - never a note (see below). Each is one factionclone job run
    with the template as donor, so what is written is byte for byte what adding
    a faction would have written there - and nothing is written for a row the
    faction already has, which is what keeps the paragraph and block cloners
    from giving it a second section.
    """
    faction = str(body.get("faction") or "").strip().lower()
    template = str(body.get("template") or "").strip().lower()
    want = [str(x) for x in (body.get("checks") or [])]
    p = fc.ClonePlan(mod=mod, source=template, new=faction, action="repair")
    c = Census(mod, str(body.get("campaign") or ""))
    if faction not in c.cultures:
        p.errors.append(f"{faction or 'the faction'} is not in {fac.REL} - add it "
                        "with ＋ Add a faction, which writes every file at once")
        return p
    if not template or template not in c.cultures:
        p.errors.append(f"{template or 'a template'} is not a faction in this mod")
        return p
    if template == faction:
        p.errors.append("a faction cannot be repaired from itself")
        return p
    mine = {r["id"]: r for r in evaluate(c, faction)}
    theirs = {r["id"]: r for r in evaluate(c, template)}
    if not want:
        # every GAP, and no note: a note is a file working mods go without, and
        # "copy what is missing" should not quietly add 1,614 skin records to a
        # modeldb because Divide and Conquer's papal_states has none. A note is
        # still one click away on its own row.
        want = [k for k, r in mine.items() if r["fix"] == "clone"
                and r["level"] == "gap" and r["state"] == "missing"
                and theirs[k]["state"] == "ok"]
    data = Path(mod.data)
    for cid in want:
        chk = BY_ID.get(cid)
        if chk is None:
            p.errors.append(f"there is no check called {cid}")
            continue
        if chk.fix != "clone":
            p.errors.append(f"{chk.label} is not repaired by copying - "
                            + ("the campaign screen's New faction tab makes it"
                               if chk.fix == "strat" else
                               "the campaign screen's Winning tab adds it"
                               if chk.fix == "wins" else "nothing copies it"))
            continue
        if mine[cid]["state"] == "ok":
            p.notes.append(f"{chk.label}: {faction} already has it")
            continue
        if mine[cid]["state"] == "unknown":
            p.warnings.append(f"{chk.label}: {mine[cid]['detail']}")
            continue
        if theirs[cid]["state"] != "ok":
            p.warnings.append(f"{chk.label}: {template} has none either, so there is "
                              "nothing to copy")
            continue
        job = JOB_BY_REL[chk.rel]
        # the shown name is the one value not copied: two factions both called
        # "Gondor" is a roster nobody can read, so the slot stands in until the
        # faction form's name box is filled - the same placeholder factions.py
        # writes for a missing key
        edit = fc.clone_file(data, job, template, faction,
                             label=faction if cid == "text" else "")
        if not edit.text:
            p.warnings.append(f"{chk.label}: {edit.skipped or 'nothing to copy'}")
            continue
        p.edits.append(edit)
        p.changes.append(f"{chk.label} ({Path(job.rel).name}) - "
                         f"{_plural(edit.count, 'entry', 'entries')} copied from "
                         f"{template}")
        if cid == "units":
            p.warnings.append(
                f"{faction} joins every ownership line {template} is on - "
                f"{_plural(edit.count, 'unit')}. That is {template}'s whole "
                "roster; the Unit Editor takes any of them back out.")
        if cid == "buildings":
            p.warnings.append(
                f"{faction} joins {_plural(edit.count, 'requires factions clause')}"
                f" - it builds and recruits wherever {template} does.")
    if not p.errors and not p.written():
        p.errors.append(f"nothing to repair: {faction} is missing nothing "
                        f"{template} can give it")
    return p
