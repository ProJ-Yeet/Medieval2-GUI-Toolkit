"""A campaign brought out of one mod and into another (Phase 73, M7).

The reference tool's ``campaignImporter.jsx``: take a whole campaign folder out
of one mod and make it a campaign of another, resolving what the destination
does not have. This is Unit Transfer's problem at campaign scale, and
:mod:`unittransfer.transfer`'s discipline is the model: **a plan that names
every missing faction, unit, building, trait, resource, religion and rebel type
before anything is written**, then one backup and one Undo.

**It arrives as a new campaign, carrying its own map.** Phase 24's
:mod:`unittransfer.campnew` makes a campaign folder out of one the mod already
runs; this makes it out of one another mod runs. The engine reads a campaign's
map from its own folder first (:data:`unittransfer.campmap.ALL_FILES`, the ten
layers and the two text files, measured on Reforged's Fellowship campaign, which
ships all twelve), so the source's base map goes *into* the new folder beside
the source campaign's own files. The destination's ``world/maps/base`` and every
campaign already reading it are not touched. ``map.rwm`` is left behind, as
every copy here leaves it, and so are the modder's side copies Phase 71 names
(:func:`unittransfer.projectzip.side_file`): ROCSS's campaign carries 22 of them.

**A campaign is played by the destination's factions.** A faction slot is a line
in ``descr_sm_factions.txt`` and the files a clone writes (Phase 16's thirteen),
so the campaign cannot bring its own; each faction it names is **mapped onto a
slot the destination declares**: the same slot when there is one, else a free
slot of the same culture, else any free one, and every mapping can be changed.
Two of the campaign's factions can never share a slot. The name, colours, units
and buildings the player then sees are the destination's for that slot, which
is what the plan says in as many words.

**What the destination lacks is resolved, never guessed silently:**

* a regiment the EDU lacks is **substituted** by a unit chosen per type, or left
  out; a character whose army is left empty gets a bodyguard its new faction
  owns, so no general stands on the map with nobody behind him. Unit Transfer is
  how to bring the missing ones themselves, first.
* a building level the EDB lacks, a trade resource ``descr_sm_resources.txt``
  lacks, a fort whose culture ``descr_cultures.txt`` lacks, a trait, an
  ancillary, a hero ability, a battle model the modeldb lacks: **left out and
  counted**, because each is a campaign that does not start. A trait above the
  destination's top level is capped at it.
* an ``ai_label`` the AI file does not declare (a crash on that faction's turn,
  :mod:`unittransfer.crashrules`) becomes the one the slot has in the
  destination's own campaign.
* a religion or a rebel type the destination lacks is **mapped** onto one it
  has; religion shares mapped together are added, so every line still totals
  100, and each of the destination's religions a line lacks is written at 0, as
  Phase 60 writes them. A hidden resource neither the EDB nor the resource file
  declares is left out of its region.
* a character's name the slot's pool lacks is **added** to the pool, with its
  text key from the source's ``names.txt``; a custom portrait the destination
  lacks is copied from the source; the region and settlement names, the
  historic events' text and the menu's title and blurbs are copied as keys the
  destination does not have yet. A key it has with other words keeps them.

**Faction names in the other campaign files follow the mapping.** Structurally
in ``descr_strat.txt``, ``descr_regions.txt``, ``descr_win_conditions.txt`` and
``descr_faction_movies.xml``; as whole words in ``descr_events.txt`` and
``campaign_script.txt``, except a word that is also a province, a settlement or
a character there, which is left and counted. The victory pictures named after a
slot (``vc_``, ``vcs_``, ``leader_pic_``) are renamed with it.
"""
from __future__ import annotations

import re
import shutil
import time
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional, Tuple

from . import campfiles, campmap, campnew, campstrat
from . import keyblock as kb

#: every 8-bit file here is read and written byte for byte: only ASCII tokens
#: are ever replaced, so latin-1 round-trips a UTF-8 XML file untouched too
ENCODING = campstrat.ENCODING
#: the files a campaign reads its map from, first in its own folder
MAP_FILES = campmap.ALL_FILES
REGIONS_NAME = Path(campmap.REGIONS_REL).name
WIN_NAME = "descr_win_conditions.txt"
MOVIES_NAME = "descr_faction_movies.xml"
MERCS_NAME = "descr_mercenaries.txt"
SCRIPT_NAME = "campaign_script.txt"
#: pictures named after a faction slot, renamed with the mapping
SLOT_PICTURE = re.compile(r"^(vc|vcs|leader_pic)_(.+)(\.tga)$", re.I)
PORTRAITS_REL = "ui/custom_portraits"
#: how many names a count is followed by in a change line
SHOW = 8
REBEL_SLOT = "slave"
_WORD = r"[A-Za-z0-9_]"


def _code(line: str) -> str:
    return line.split(";", 1)[0]


@lru_cache(maxsize=16)
def _token_rx(words: Tuple[str, ...]):
    """One compiled pattern per mapping: a campaign script is 300 000 lines."""
    return re.compile(r"(?<!" + _WORD + r")(" + "|".join(re.escape(k) for k in words)
                      + r")(?!" + _WORD + r")", re.I)


def _swap_tokens(text: str, mapping: Dict[str, str]) -> Tuple[str, int]:
    """Every whole-word occurrence of a key replaced by its value, case-blind,
    in one pass, so a swap of two slots does not undo itself."""
    if not mapping:
        return text, 0
    low = {k.lower(): v for k, v in mapping.items()}
    rx = _token_rx(tuple(sorted(low, key=len, reverse=True)))
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return low[m.group(1).lower()]
    return rx.sub(sub, text), n


def _swap_code(line: str, mapping: Dict[str, str]) -> Tuple[str, int]:
    """:func:`_swap_tokens` on the part of a line before its comment."""
    code, sep, rest = line.partition(";")
    new, n = _swap_tokens(code, mapping)
    return new + sep + rest, n


def _shown(names: Iterable[str], limit: int = SHOW) -> str:
    names = list(names)
    head = ", ".join(names[:limit])
    return head + (f" and {len(names) - limit} more" if len(names) > limit else "")


def _counted(c: Counter, limit: int = SHOW) -> str:
    items = sorted(c.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    return _shown([f"{k} x{v}" if v > 1 else k for k, v in items], limit)


# ---------------------------------------------------------------------------
# what the destination has


class Destination:
    """Every list the import checks the campaign against, read once.

    A file the destination does not have on disk gives an empty list, and an
    empty list means *no check*, never *everything is missing*: the stock game
    keeps most of these inside its packed data (16f's ruling).
    """

    def __init__(self, mod, sf):
        from . import edbvocab, heroabilities, stratchar
        self.mod = mod
        self.chars = stratchar.Vocabulary(SimpleNamespace(mod=mod, skipped=[]), sf)
        self.units = {n.lower(): n for n in self.chars.units}
        self.traits = {n.lower(): (n, lv) for n, lv in self.chars.traits.items()}
        self.ancillaries = {n.lower(): n for n in self.chars.ancillaries}
        self.abilities = {a.lower() for a in heroabilities.declared(mod)}
        rv = campmap.region_vocab(mod)
        self.slots = list(rv["factions"])
        self.labels = dict(rv["faction_labels"])
        self.religions = list(rv["religions"])
        self.rebels = list(rv["rebels"])
        self.trade = {r.lower() for r in rv["trade_resources"]}
        self.hidden = {r.lower() for r in rv["hidden_resources"]}
        try:
            self.cultures = {c.lower() for c in edbvocab.cultures(mod)}
        except Exception:                                  # noqa: BLE001
            self.cultures = set()
        self.slot_culture = dict(getattr(mod, "faction_cultures", {}) or {})
        self.levels: Dict[str, str] = {}
        try:
            edb = mod.edb
            for line in getattr(edb, "buildings", None) or []:
                for blk in line.blocks:
                    self.levels.setdefault(blk.name.lower(), line.name)
        except Exception:                                  # noqa: BLE001
            pass
        self.ai_labels = self._ai_labels()
        self._models: Optional[set] = None
        self._own = self._own_campaign()

    def _ai_labels(self) -> Optional[set]:
        from .crashrules import AI_DB_REL, AI_LABELS_BUILTIN
        path = Path(self.mod.data) / AI_DB_REL
        if not path.is_file():
            return None
        text = path.read_text("utf-8", errors="replace")
        return ({n.lower() for n in re.findall(
            r'<faction_ai_label\s+name="([^"]+)"', text)} | set(AI_LABELS_BUILTIN))

    def _own_campaign(self) -> Dict[str, dict]:
        """``{slot: {ai_label, guard}}`` out of the destination's own campaign:
        the label and the bodyguard each slot already starts with there."""
        out: Dict[str, dict] = {}
        try:
            sf = campstrat.read_strat(self.mod, campstrat.DEFAULT_CAMPAIGN)
        except Exception:                                  # noqa: BLE001
            return out
        for node in sf.of_kind("faction"):
            got = {"ai_label": str(node.get("ai_label") or ""), "guard": ""}
            for army in sf.descendants_of(node, "army"):
                first = next(iter(sf.children_of(army, "unit")), None)
                if first is not None and first.name.lower() in self.units:
                    got["guard"] = self.units[first.name.lower()]
                    break
            out[node.name.lower()] = got
        return out

    def models(self) -> Optional[set]:
        """Battle model names, read only when a character asks for one."""
        if self._models is None:
            path = Path(getattr(self.mod, "modeldb_path", "") or "")
            if not path.is_file():
                self._models = set()
            else:
                try:
                    self._models = {n.lower() for n in self.mod.modeldb.by_name}
                except Exception:                          # noqa: BLE001
                    self._models = set()
        return self._models or None

    def guard_for(self, slot: str) -> str:
        """A bodyguard for a general whose own regiments were all left out:
        the one the slot starts with in the destination's campaign, else the
        first general's unit the EDU lets the slot own."""
        from . import hordestart
        got = self._own.get(slot.lower(), {}).get("guard", "")
        if got:
            return got
        owned = hordestart.owned_units(self.mod, slot)
        return next((u["name"] for u in owned
                     if u["general"] and u.get("category") != "ship"), "")

    def label_for(self, slot: str) -> str:
        return self._own.get(slot.lower(), {}).get("ai_label", "")


# ---------------------------------------------------------------------------
# the plan


@dataclass
class ImportPlan:
    """One campaign brought across, worked out without touching the disk."""

    src: object = None
    dst: object = None
    campaign: str = ""
    name: str = ""
    folder: str = ""
    #: ``(source path, data-relative destination)`` for every file copied as is
    copies: List[Tuple[Path, str]] = field(default_factory=list)
    #: data-relative path -> whole new text, for the files the import rewrites
    texts: Dict[str, str] = field(default_factory=dict)
    #: ``{rel: {key: value}}`` for the text files keys are added to
    loc: Dict[str, Dict[str, str]] = field(default_factory=dict)
    descr: Dict[str, str] = field(default_factory=dict)
    descr_new: List[str] = field(default_factory=list)
    factions: List[dict] = field(default_factory=list)
    units: List[dict] = field(default_factory=list)
    religions: List[dict] = field(default_factory=list)
    rebels: List[dict] = field(default_factory=list)
    left_out: List[Tuple[str, str]] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: the destination's lists, for the form's pickers
    slots: List[dict] = field(default_factory=list)
    unit_names: List[str] = field(default_factory=list)
    religion_names: List[str] = field(default_factory=list)
    rebel_names: List[str] = field(default_factory=list)

    @property
    def files(self) -> int:
        return len(self.copies) + len(self.texts)

    @property
    def bytes(self) -> int:
        return (sum(p.stat().st_size for p, _ in self.copies)
                + sum(len(t) for t in self.texts.values()))

    def summary(self) -> str:
        head = (f"campaign {self.campaign} of {getattr(self.src, 'name', '?')} "
                f"imported as {self.name} ({self.files} file(s), {self.bytes:,} bytes)")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"source": getattr(self.src, "name", ""), "campaign": self.campaign,
                "name": self.name, "folder": self.folder,
                "files": self.files, "bytes": self.bytes,
                "copies": [rel for _, rel in self.copies],
                "texts": sorted(self.texts),
                "keys": {rel: len(w) for rel, w in self.loc.items() if w},
                "descr_keys": len(self.descr), "descr_new": len(self.descr_new),
                "factions": self.factions, "units": self.units,
                "religions": self.religions, "rebels": self.rebels,
                "left_out": [{"rel": r, "why": w} for r, w in self.left_out],
                "slots": self.slots, "unit_names": self.unit_names,
                "religion_names": self.religion_names,
                "rebel_names": self.rebel_names,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.copies or self.texts)}


def plan(src, dst, body: dict) -> ImportPlan:
    """Work out the import. ``body``: ``{campaign, name, title, blurb,
    factions: {src slot: dst slot}, units: {src unit: dst unit or ""},
    religions: {src: dst}, rebels: {src: dst}}``."""
    p = ImportPlan(src=src, dst=dst, campaign=str(body.get("campaign") or "").strip()
                   or campstrat.DEFAULT_CAMPAIGN)
    if src is None or dst is None:
        p.errors.append("an import needs a mod to take the campaign from and one to put it in")
        return p
    if Path(src.data).resolve() == Path(dst.data).resolve():
        p.errors.append("that is the same mod - New campaign copies a campaign "
                        "within one mod")
        return p
    try:
        p.name, _home = campnew._resolve(dst, body.get("name") or campstrat.campaign_leaf(p.campaign))
    except campnew.CampaignError as exc:
        p.errors.append(str(exc))
        return p
    p.folder = f"{campstrat.CAMPAIGN_DIR_REL}/{p.name}"
    try:
        home = campfiles.campaign_dir(src, p.campaign)
    except ValueError as exc:
        p.errors.append(str(exc))
        return p
    if not (home / campstrat.STRAT_NAME).is_file():
        p.errors.append(f"{src.name} has no campaign {p.campaign} with a "
                        f"{campstrat.STRAT_NAME} in it")
        return p
    sf = campstrat.parse_strat(kb.read_text(home / campstrat.STRAT_NAME, ENCODING))
    d = Destination(dst, sf)
    p.slots = [{"slot": s, "label": d.labels.get(s, s),
                "culture": d.slot_culture.get(s, "")} for s in d.slots]
    p.unit_names = sorted(d.units.values(), key=str.lower)
    p.religion_names = list(d.religions)
    p.rebel_names = list(d.rebels)

    regions_src = home / REGIONS_NAME if (home / REGIONS_NAME).is_file() \
        else Path(src.data) / campmap.REGIONS_REL
    if not regions_src.is_file():
        p.errors.append(f"{src.name} has no {REGIONS_NAME} for this campaign, so "
                        f"there is no map to bring")
        return p
    rf = campmap.parse_regions(kb.read_text(regions_src, ENCODING))
    _plan_cap(p, rf)

    fmap = _plan_factions(p, sf, rf, d, body.get("factions") or {})
    if p.errors:
        return p
    guard_names = ({r.name.lower() for r in rf.records if r.name}
                   | {r.settlement.lower() for r in rf.records if r.settlement}
                   | {c.name.lower() for c in sf.of_kind("character") if c.name})
    renames = {s: t for s, t in fmap.items() if s.lower() != t.lower()}
    owners = _owners(sf, fmap)

    strat_text = _plan_strat(p, sf, d, fmap, owners, body)
    if p.errors:
        return p
    regions_text = _plan_regions(p, rf, d, fmap, owners, body)
    _plan_folder(p, home, d, renames, guard_names, strat_text, regions_text)
    _plan_map(p, home)
    _plan_names(p, sf, d, fmap)
    _plan_portraits(p, sf, d)
    _plan_text(p, home, fmap, body)
    _plan_climates(p, home)
    p.warnings.append(
        f"{p.name} is played by {dst.name}'s factions: each slot's own name, "
        f"colours, units and buildings, whatever the campaign called it in "
        f"{src.name}. Health checks the result once it is written.")
    return p


# ---------------------------------------------------------------------------
# factions


def _campaign_slots(sf, rf) -> Tuple[List[str], List[str]]:
    """``(factions with a block, slots named only as a creator)``, in file order."""
    held = []
    for n in sf.of_kind("faction"):
        if n.name and n.name.lower() not in {h.lower() for h in held}:
            held.append(n.name)
    for names in sf.rosters.values():
        for n in names:
            if n.lower() not in {h.lower() for h in held}:
                held.append(n)
    low = {h.lower() for h in held}
    only: List[str] = []
    for s in sf.of_kind("settlement"):
        c = str(s.get("faction_creator") or "")
        if c and c.lower() not in low and c.lower() not in {o.lower() for o in only}:
            only.append(c)
    for r in rf.records:
        c = r.faction
        if c and c.lower() not in low and c.lower() not in {o.lower() for o in only}:
            only.append(c)
    return held, only


def _plan_factions(p: ImportPlan, sf, rf, d: Destination, asked: dict) -> Dict[str, str]:
    """Each of the campaign's factions onto one of the destination's slots."""
    held, only = _campaign_slots(sf, rf)
    slots = {s.lower(): s for s in d.slots}
    src_culture = dict(getattr(p.src, "faction_cultures", {}) or {})
    asked = {str(k).lower(): str(v).strip() for k, v in asked.items() if str(v).strip()}
    fmap: Dict[str, str] = {}
    how: Dict[str, str] = {}
    if not slots:
        p.warnings.append(f"{p.dst.name} has no descr_sm_factions.txt on disk, so "
                          f"no faction can be checked and each keeps its slot")
        for s in held + only:
            fmap[s] = s
            how[s] = "unchecked"
    else:
        taken: Dict[str, str] = {}
        # asked first, then the same slot, then a free one: in file order
        for s in held:
            want = asked.get(s.lower())
            if want:
                if want.lower() not in slots:
                    p.errors.append(f"{want} is not a faction {p.dst.name} declares")
                    continue
                fmap[s], how[s] = slots[want.lower()], "chosen"
        for s in held:
            if s in fmap:
                continue
            if s.lower() in slots and s.lower() not in {v.lower() for v in fmap.values()}:
                fmap[s], how[s] = slots[s.lower()], "same"
        for s in held:
            if s in fmap:
                continue
            used = {v.lower() for v in fmap.values()}
            free = [x for x in d.slots if x.lower() not in used
                    and x.lower() != REBEL_SLOT]
            culture = src_culture.get(s, "")
            pick = next((x for x in free if culture
                         and d.slot_culture.get(x, "") == culture), "") \
                or (free[0] if free else "")
            if not pick:
                p.errors.append(f"{s} has no slot to go to: every faction "
                                f"{p.dst.name} declares is already taken by this "
                                f"campaign. Add one on the Factions screen first.")
                continue
            fmap[s], how[s] = pick, "free"
        for s, t in fmap.items():
            other = taken.get(t.lower())
            if other:
                p.errors.append(f"{other} and {s} are both mapped onto {t}, and "
                                f"two factions of one campaign cannot share a slot")
            taken[t.lower()] = s
        for s in only:
            want = asked.get(s.lower())
            if want and want.lower() in slots:
                fmap[s], how[s] = slots[want.lower()], "chosen"
            elif s.lower() in slots:
                fmap[s], how[s] = slots[s.lower()], "same"
            else:
                how[s] = "owner"           # resolved per settlement, below
    freed, recultured = [], []
    for s in held + only:
        t = fmap.get(s, "")
        row = {"source": s, "slot": t, "how": how.get(s, ""),
               "only_creator": s in only,
               "source_culture": src_culture.get(s, ""),
               "culture": d.slot_culture.get(t, "") if t else "",
               "label": d.labels.get(t, t) if t else ""}
        p.factions.append(row)
        if s in only or s.lower() == REBEL_SLOT:
            continue
        if row["how"] == "free":
            freed.append(f"{s} as {t} ({row['label']})")
        if row["source_culture"] and row["culture"] and row["source_culture"] != row["culture"]:
            recultured.append(f"{s} {row['source_culture']} -> {row['culture']}")
    if freed:
        p.warnings.append(f"{len(freed)} faction(s) {p.dst.name} has no slot of that "
                          f"name for play on a free one: {_shown(freed, 12)}. Pick "
                          f"another slot for any of them below.")
    if recultured:
        p.warnings.append(f"{len(recultured)} faction(s) change culture with their "
                          f"slot, so their settlements are built in the new "
                          f"culture's art: {_shown(recultured, 12)}")
    moved = [f"{s} -> {t}" for s, t in fmap.items() if s.lower() != t.lower()]
    if moved:
        p.changes.append(f"factions: {_shown(moved, 12)}")
    return {s: t for s, t in fmap.items()}


def _owners(sf, fmap: Dict[str, str]) -> Dict[str, str]:
    """``{region: destination slot}`` of the settlement standing in it."""
    out: Dict[str, str] = {}
    for node in sf.of_kind("faction"):
        slot = fmap.get(node.name, node.name)
        for s in sf.children_of(node, "settlement"):
            region = str(s.get("region") or "")
            if region:
                out[region.lower()] = slot
    return out


# ---------------------------------------------------------------------------
# descr_strat.txt


_UNIT = re.compile(r"^(?P<head>[\t ]*unit[\t ]+)(?P<name>.+?)(?P<tail>,?[\t ]+exp\b.*)$", re.I)
_TAIL_FIELD = r",[\t ]*{key}[\t ]+[^,;]*?(?=[\t ]*(?:,|;|$))"


def _drop_field(line: str, key: str) -> str:
    code, sep, rest = line.partition(";")
    new = re.sub(_TAIL_FIELD.format(key=re.escape(key)), "", code, count=1, flags=re.I)
    return new + sep + rest


def _list_line(line: str, keep) -> Tuple[str, bool]:
    """A ``traits`` or ``ancillaries`` line with ``keep(entry)`` applied to each
    comma-separated entry: it returns the entry to write, or None to drop it.
    ``(line, empty)`` - the separator and the spacing are the line's own."""
    code, sep, rest = line.partition(";")
    m = re.match(r"^([\t ]*\w+[\t ]+)(.*?)([\t ]*)$", code)
    if not m:
        return line, False
    head, body, trail = m.groups()
    parts = re.split(r"([\t ]*,[\t ]*)", body)
    entries = parts[0::2]
    seps = parts[1::2]
    joiner = seps[0] if seps else " , "
    kept = [k for k in (keep(e.strip()) for e in entries if e.strip()) if k]
    return head + joiner.join(kept) + trail + sep + rest, not kept


def _plan_strat(p: ImportPlan, sf, d: Destination, fmap: Dict[str, str],
                owners: Dict[str, str], body: dict) -> str:
    """The campaign file, every faction mapped and every missing thing resolved."""
    from . import stratchar
    lines = list(sf.lines)
    drop: set = set()
    after: Dict[int, List[str]] = {}
    gone: Dict[str, Counter] = {k: Counter() for k in (
        "units", "buildings", "traits", "ancillaries", "resources", "forts",
        "abilities", "models")}
    capped: Counter = Counter()
    guards: Counter = Counter()
    labels: List[str] = []
    empty_armies: List[str] = []
    swap = {s: t for s, t in fmap.items() if s.lower() != t.lower()}

    # the header: the new campaign's own name
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        if code.split()[0].lower() == campnew.HEADER:
            lines[i] = kb.keep_comment(raw, kb.indent_of(code) + f"{campnew.HEADER} "
                                       f"{campstrat.campaign_leaf(p.name)}")
        break

    # rosters and the diplomacy: lines made of faction names and keywords
    for a, b in sf.roster_lines.values():
        for i in range(a, b + 1):
            lines[i], _ = _swap_code(lines[i], swap)
    for kind in ("faction_standings", "faction_relationships"):
        for n in sf.of_kind(kind):
            for i in range(n.start, n.end + 1):
                lines[i], _ = _swap_code(lines[i], swap)

    # the units: which exist, which are substituted, which are left out
    asked = {str(k).lower(): str(v).strip() for k, v in (body.get("units") or {}).items()}
    uses: Counter = Counter()
    for u in sf.of_kind("unit"):
        uses[u.name] += 1
    unit_to: Dict[str, str] = {}
    if d.units:
        for name, count in sorted(uses.items(), key=lambda kv: kv[0].lower()):
            have = d.units.get(name.lower())
            if have:
                unit_to[name] = have
                continue
            want = asked.get(name.lower(), "")
            if want and want.lower() in d.units:
                unit_to[name] = d.units[want.lower()]
                how = "substituted"
            else:
                unit_to[name] = ""
                how = "left out"
                if want:
                    p.warnings.append(f"{want} is not a unit {p.dst.name} has, so "
                                      f"{name} is left out")
            p.units.append({"unit": name, "count": count, "to": unit_to[name], "how": how})
    for u in sf.of_kind("unit"):
        to = unit_to.get(u.name, u.name)
        if not to:
            drop.add(u.start)
            gone["units"][u.name] += 1
        elif to != u.name:
            m = _UNIT.match(lines[u.start])
            if m:
                lines[u.start] = m.group("head") + to + m.group("tail")

    shape = stratchar.shape_of(sf)
    models = None
    for node in sf.of_kind("faction"):
        slot = fmap.get(node.name, node.name)
        # the faction header, and its ai_label
        lines[node.start], _ = _swap_code(lines[node.start], swap)
        at = node.field_lines.get("ai_label")
        label = str(node.get("ai_label") or "")
        if at is not None and label and d.ai_labels is not None \
                and label.lower() not in d.ai_labels:
            new = d.label_for(slot)
            if new and new.lower() in d.ai_labels:
                lines[at] = re.sub(r"(ai_label[\t ]+)\S+", lambda m: m.group(1) + new,
                                   lines[at], count=1)
                labels.append(f"{node.name} {label} -> {new}")
            else:
                drop.add(at)
                labels.append(f"{node.name} {label} left out")
        # settlements: the creator, and each building
        for s in sf.children_of(node, "settlement"):
            at = s.field_lines.get("faction_creator")
            creator = str(s.get("faction_creator") or "")
            if at is not None and creator:
                to = fmap.get(creator) or next(
                    (t for k, t in fmap.items() if k.lower() == creator.lower()), "") or slot
                if to != creator:
                    lines[at] = re.sub(r"(faction_creator[\t ]+)\S+",
                                       lambda m: m.group(1) + to, lines[at], count=1)
            for b in sf.descendants_of(s, "building"):
                level = str(b.get("level") or "")
                chain = d.levels.get(level.lower())
                if d.levels and (chain is None or chain.lower() != (b.name or "").lower()):
                    drop.update(range(b.start, b.end + 1))
                    gone["buildings"][f"{b.name} {level}"] += 1
        # people
        for c in sf.descendants_of(node, "character"):
            _plan_character(p, sf, lines, drop, c, d, gone, capped)
            if c.get("battle_model"):
                if models is None:
                    models = d.models() or set()
                bm = str(c.get("battle_model"))
                if models and bm.lower() not in models:
                    lines[c.start] = _drop_field(lines[c.start], "battle_model")
                    gone["models"][bm] += 1
            for army in sf.children_of(c, "army"):
                units = sf.children_of(army, "unit")
                if units and all(u.start in drop for u in units):
                    guard = d.guard_for(slot)
                    if guard:
                        after.setdefault(army.start, []).append(stratchar.unit_line(
                            stratchar.Army(unit=guard, exp=0, armour=0, weapon_lvl=0),
                            shape))
                        guards[guard] += 1
                    else:
                        empty_armies.append(c.name)

    # depth 0: resources and forts
    for r in sf.of_kind("resource"):
        if d.trade and r.name.lower() not in d.trade:
            drop.add(r.start)
            gone["resources"][r.name] += 1
    for f in sf.of_kind("fort"):
        culture = str(f.get("culture") or "")
        if d.cultures and culture and culture.lower() not in d.cultures:
            drop.add(f.start)
            gone["forts"][culture] += 1

    out: List[str] = []
    for i, line in enumerate(lines):
        if i not in drop:
            out.append(line)
        out += after.get(i, [])
    text = sf.newline.join(out) + (sf.newline if sf.trailing_newline else "")

    what = {"units": "regiment(s) the EDU lacks",
            "buildings": "building(s) the EDB does not declare",
            "traits": "trait(s) the trait file lacks",
            "ancillaries": "ancillar(ies) the ancillary file lacks",
            "resources": "resource(s) descr_sm_resources.txt lacks",
            "forts": "fort(s) of a culture descr_cultures.txt lacks",
            "abilities": "hero abilit(ies) descr_hero_abilities.xml lacks",
            "models": "battle model(s) the modeldb lacks"}
    for k, c in gone.items():
        if c:
            p.changes.append(f"{campstrat.STRAT_NAME}: {sum(c.values())} "
                             f"{what[k]} left out: {_counted(c)}")
    if capped:
        p.changes.append(f"{campstrat.STRAT_NAME}: {sum(capped.values())} trait(s) "
                         f"capped at {p.dst.name}'s top level: {_counted(capped)}")
    if guards:
        p.changes.append(f"{campstrat.STRAT_NAME}: {sum(guards.values())} general(s) "
                         f"whose regiments were all left out given a bodyguard "
                         f"their new faction owns: {_counted(guards)}")
    if empty_armies:
        p.warnings.append(f"{len(empty_armies)} character(s) lead an army with no "
                          f"regiment left in it and no bodyguard their slot owns "
                          f"could be found: {_shown(empty_armies)}. Substitute a "
                          f"unit for theirs.")
    if labels:
        p.changes.append(f"{campstrat.STRAT_NAME}: ai_label the AI file lacks: "
                         f"{_shown(labels)}")
    missing = [u for u in p.units if u["how"] == "left out"]
    if missing:
        p.warnings.append(
            f"{len(missing)} unit type(s) {p.dst.name} lacks are left out of the "
            f"armies: {_shown([u['unit'] for u in missing])}. Substitute one of "
            f"{p.dst.name}'s units for each below, or bring them first with Unit "
            f"Transfer and work the import out again.")
    if not d.units:
        p.warnings.append(f"{p.dst.name} has no export_descr_unit.txt on disk, so "
                          f"no regiment could be checked")
    if not d.levels:
        p.warnings.append(f"{p.dst.name} has no export_descr_buildings.txt on "
                          f"disk, so no building could be checked")

    # read back: the result has to parse no worse than the source did
    done = campstrat.parse_strat(text)
    if len(done.problems) > len(sf.problems):
        p.errors.append(f"the rewritten {campstrat.STRAT_NAME} reads with "
                        f"{len(done.problems)} faulty line(s) where the source had "
                        f"{len(sf.problems)}; nothing was written")
    if len(done.of_kind("faction")) != len(sf.of_kind("faction")) \
            or len(done.of_kind("settlement")) != len(sf.of_kind("settlement")) \
            or len(done.of_kind("character")) != len(sf.of_kind("character")):
        p.errors.append(f"the rewritten {campstrat.STRAT_NAME} does not hold the "
                        f"same factions, settlements and characters as the source")
    names = [n.name.lower() for n in done.of_kind("faction")]
    if len(set(names)) != len(names):
        p.errors.append("two faction blocks would name the same slot")
    rel = f"{p.folder}/{campstrat.STRAT_NAME}"
    p.texts[rel] = text
    return text


def _plan_character(p: ImportPlan, sf, lines: List[str], drop: set, c, d: Destination,
                    gone: Dict[str, Counter], capped: Counter) -> None:
    """One character's traits, ancillaries, hero ability and sub-faction."""
    at = c.field_lines.get("traits")
    if at is not None and d.traits:
        def keep_trait(entry: str) -> Optional[str]:
            m = re.match(r"^(\S+)[\t ]+(-?\d+)$", entry)
            if not m:
                return entry
            name, level = m.group(1), int(m.group(2))
            have = d.traits.get(name.lower())
            if have is None:
                gone["traits"][name] += 1
                return None
            top = have[1]
            if top and level > top:
                capped[name] += 1
                return f"{have[0]} {top}"
            return entry
        new, empty = _list_line(lines[at], keep_trait)
        if empty:
            drop.add(at)
        else:
            lines[at] = new
    at = c.field_lines.get("ancillaries")
    if at is not None and d.ancillaries:
        def keep_anc(entry: str) -> Optional[str]:
            if entry.lower() in d.ancillaries:
                return entry
            gone["ancillaries"][entry] += 1
            return None
        new, empty = _list_line(lines[at], keep_anc)
        if empty:
            drop.add(at)
        else:
            lines[at] = new
    ability = str(c.get("hero_ability") or "")
    if ability and d.abilities and ability.lower() not in d.abilities:
        lines[c.start] = _drop_field(lines[c.start], "hero_ability")
        gone["abilities"][ability] += 1


# ---------------------------------------------------------------------------
# descr_regions.txt


def _plan_regions(p: ImportPlan, rf, d: Destination, fmap: Dict[str, str],
                  owners: Dict[str, str], body: dict) -> str:
    """The map's own region list: creators, rebels, resources and religions."""
    lines = list(rf.lines)
    rel_asked = {str(k).lower(): str(v).strip() for k, v in (body.get("religions") or {}).items()}
    reb_asked = {str(k).lower(): str(v).strip() for k, v in (body.get("rebels") or {}).items()}
    dest_rel = {r.lower(): r for r in d.religions}
    dest_reb = {r.lower(): r for r in d.rebels}

    used_rel: Counter = Counter()
    used_reb: Counter = Counter()
    for r in rf.records:
        for name in r.religions:
            used_rel[name] += 1
        if r.rebels:
            used_reb[r.rebels] += 1
    rel_to: Dict[str, str] = {}
    for name, count in sorted(used_rel.items(), key=lambda kv: kv[0].lower()):
        if not dest_rel or name.lower() in dest_rel:
            rel_to[name] = dest_rel.get(name.lower(), name)
            continue
        want = rel_asked.get(name.lower(), "")
        rel_to[name] = dest_rel.get(want.lower()) if want.lower() in dest_rel \
            else d.religions[0]
        p.religions.append({"religion": name, "regions": count, "to": rel_to[name],
                            "how": "chosen" if want.lower() in dest_rel else "first"})
    reb_to: Dict[str, str] = {}
    for name, count in sorted(used_reb.items(), key=lambda kv: kv[0].lower()):
        if not dest_reb or name.lower() in dest_reb:
            reb_to[name] = dest_reb.get(name.lower(), name)
            continue
        want = reb_asked.get(name.lower(), "")
        reb_to[name] = dest_reb.get(want.lower()) if want.lower() in dest_reb \
            else d.rebels[0]
        p.rebels.append({"rebels": name, "regions": count, "to": reb_to[name],
                         "how": "chosen" if want.lower() in dest_reb else "first"})

    creators = 0
    hidden: Counter = Counter()
    for r in rf.records:
        if r.faction_line >= 0 and r.faction:
            to = fmap.get(r.faction) or owners.get(r.name.lower()) or REBEL_SLOT
            if to != r.faction:
                campmap._set_line(lines, r.faction_line, to)
                creators += 1
        if r.rebels_line >= 0 and r.rebels and reb_to.get(r.rebels, r.rebels) != r.rebels:
            campmap._set_line(lines, r.rebels_line, reb_to[r.rebels])
        if r.resources_line >= 0 and (d.hidden or d.trade):
            keep = [x for x in r.resources
                    if x.lower() in d.hidden or x.lower() in d.trade]
            for x in r.resources:
                if x not in keep:
                    hidden[x] += 1
            if len(keep) != len(r.resources):
                campmap._set_line(lines, r.resources_line, ", ".join(keep) or "none")
        if r.religions_line >= 0 and r.religions:
            shares: Dict[str, int] = {}
            for name, value in r.religions.items():
                to = rel_to.get(name, name)
                shares[to] = shares.get(to, 0) + value
            for name in d.religions:
                shares.setdefault(name, 0)
            if list(shares.items()) != list(r.religions.items()):
                campmap._set_line(lines, r.religions_line, campmap._religions_text(shares))

    text = rf.newline.join(lines) + (rf.newline if rf.trailing_newline else "")
    rel = f"{p.folder}/{REGIONS_NAME}"
    p.texts[rel] = text
    if creators:
        p.changes.append(f"{REGIONS_NAME}: {creators} province(s)' creator faction mapped")
    if p.religions:
        p.changes.append(f"{REGIONS_NAME}: religion(s) {p.dst.name} lacks, mapped "
                         f"with their shares: " + _shown(
                             [f"{r['religion']} -> {r['to']}" for r in p.religions]))
    if p.rebels:
        p.changes.append(f"{REGIONS_NAME}: rebel type(s) {p.dst.name} lacks, mapped: "
                         + _shown([f"{r['rebels']} -> {r['to']}" for r in p.rebels]))
    if hidden:
        p.changes.append(f"{REGIONS_NAME}: {sum(hidden.values())} resource(s) "
                         f"{p.dst.name} declares neither as hidden nor as trade "
                         f"left out of their provinces: {_counted(hidden)}")
    done = campmap.parse_regions(text)
    bad = [r.name for r in done.records if r.religions_line >= 0 and r.religions
           and r.religion_total != 100]
    was = {r.name for r in rf.records if r.religions_line >= 0 and r.religions
           and r.religion_total != 100}
    if [b for b in bad if b not in was]:
        p.errors.append(f"the mapped religions would not total 100 in "
                        f"{_shown([b for b in bad if b not in was])}")
    if len(done.records) != len(rf.records):
        p.errors.append(f"the rewritten {REGIONS_NAME} does not hold the same provinces")
    return text


# ---------------------------------------------------------------------------
# the rest of the folder, and the map


def _plan_folder(p: ImportPlan, home: Path, d: Destination, renames: Dict[str, str],
                 guard: set, strat_text: str, regions_text: str) -> None:
    """Every file in the source campaign's folder: copied, rewritten or left out."""
    from . import projectzip
    data = Path(p.src.data)
    safe = {s: t for s, t in renames.items() if s.lower() not in guard}
    held = sorted(s for s in renames if s.lower() in guard)
    if held:
        p.warnings.append(
            f"{_shown(held)} {'is' if len(held) == 1 else 'are'} also a province, a "
            f"settlement or a character in this campaign, so the word is left as "
            f"it is in {SCRIPT_NAME} and descr_events.txt rather than guessed at")
    script_hits = 0
    for path in sorted(home.rglob("*")):
        if not path.is_file():
            continue
        under = path.relative_to(home).as_posix()
        low = path.name.lower()
        if low == campmap.RWM_NAME:
            p.left_out.append((path.relative_to(data).as_posix(),
                               "the compiled map, which the game builds again"))
            continue
        why = projectzip.side_file(path.name)
        if why:
            p.left_out.append((path.relative_to(data).as_posix(), why))
            continue
        if "/" not in under and low in (campstrat.STRAT_NAME, REGIONS_NAME):
            continue                      # written by their own planners
        target = under
        m = SLOT_PICTURE.match(path.name) if "/" not in under else None
        if m:
            slot = next((t for s, t in renames.items()
                         if s.lower() == m.group(2).lower()), "")
            if slot:
                target = f"{m.group(1)}_{slot}{m.group(3)}"
        rel = f"{p.folder}/{target}"
        if "/" in under or low not in (WIN_NAME, MOVIES_NAME, MERCS_NAME, SCRIPT_NAME,
                                        "descr_events.txt"):
            p.copies.append((path, rel))
            continue
        text = kb.read_text(path, ENCODING)
        if low == WIN_NAME:
            new = _win_conditions(text, renames)
        elif low == MOVIES_NAME:
            new = re.sub(r"(<name>\s*)([^<\s]+)(\s*</name>)", lambda m: m.group(1) + next(
                (t for s, t in renames.items() if s.lower() == m.group(2).lower()),
                m.group(2)) + m.group(3), text)
        elif low == MERCS_NAME:
            new = _mercenaries(p, text, d)
        else:
            new, n = _swap_lines(text, safe)
            if low == SCRIPT_NAME:
                script_hits = n
        if new == text:
            p.copies.append((path, rel))
        else:
            p.texts[rel] = new
    renamed = [f"{path.name}" for path, rel in p.copies
               if Path(rel).name != path.name]
    kept = [c for c in p.copies]
    p.changes.insert(0, f"{p.folder}: {len(kept) + len(p.texts)} file(s) from "
                        f"{p.src.name}'s {p.campaign}")
    if renamed:
        p.changes.append(f"{len(renamed)} victory picture(s) renamed with their slot")
    if script_hits:
        p.changes.append(f"{SCRIPT_NAME}: {script_hits} faction name(s) mapped")
    if p.left_out:
        p.changes.append(f"left behind: {len(p.left_out)} file(s) the game never reads "
                         f"under that name, and the compiled map")


def _swap_lines(text: str, mapping: Dict[str, str]) -> Tuple[str, int]:
    """:func:`_swap_code` over a whole file, comments left alone."""
    if not mapping:
        return text, 0
    lines, newline, trailing = campmap._split_lines(text)
    total = 0
    for i, line in enumerate(lines):
        lines[i], n = _swap_code(line, mapping)
        total += n
    return newline.join(lines) + (newline if trailing else ""), total


def _win_conditions(text: str, renames: Dict[str, str]) -> str:
    """A faction's own line, the one word heading its block, renamed."""
    if not renames:
        return text
    low = {s.lower(): t for s, t in renames.items()}
    lines, newline, trailing = campmap._split_lines(text)
    for i, line in enumerate(lines):
        code = _code(line).strip()
        if code and " " not in code and "\t" not in code and code.lower() in low:
            lines[i] = line.replace(code, low[code.lower()], 1)
    return newline.join(lines) + (newline if trailing else "")


_MERC_UNIT = re.compile(r"^(?P<head>[\t ]*unit[\t ]+)(?P<name>.+?)(?P<tail>,?[\t ]+exp\b.*)$", re.I)


def _mercenaries(p: ImportPlan, text: str, d: Destination) -> str:
    """Mercenary regiments the EDU lacks left out; religions mapped."""
    lines, newline, trailing = campmap._split_lines(text)
    out: List[str] = []
    gone: Counter = Counter()
    rel_to = {r["religion"].lower(): r["to"] for r in p.religions}
    for line in lines:
        m = _MERC_UNIT.match(line)
        if m and d.units and m.group("name").strip().lower() not in d.units:
            gone[m.group("name").strip()] += 1
            continue
        if rel_to and "religions" in line:
            line, _ = _swap_code(line, rel_to)
        out.append(line)
    if gone:
        p.changes.append(f"{MERCS_NAME}: {sum(gone.values())} mercenary regiment(s) "
                         f"the EDU lacks left out: {_counted(gone)}")
    return newline.join(out) + (newline if trailing else "")


def _plan_map(p: ImportPlan, home: Path) -> None:
    """The source's base map, into the new folder, for each file the campaign
    does not already ship a copy of."""
    base = Path(p.src.data) / campmap.BASE_REL
    brought = []
    for name in MAP_FILES:
        if name == REGIONS_NAME or (home / name).is_file():
            continue
        if (base / name).is_file():
            p.copies.append((base / name, f"{p.folder}/{name}"))
            brought.append(name)
    if brought:
        p.changes.append(f"{p.folder}: {len(brought)} map file(s) from {p.src.name}'s "
                         f"{campmap.BASE_REL}, so the campaign reads its own map and "
                         f"{p.dst.name}'s base map is not touched")
    missing = [n for n in MAP_FILES if n != REGIONS_NAME and not (home / n).is_file()
               and not (base / n).is_file()]
    if missing:
        p.warnings.append(f"{p.src.name} has no {_shown(missing)}, so the new campaign "
                          f"reads {p.dst.name}'s base copy of "
                          f"{'it' if len(missing) == 1 else 'them'}, which belongs "
                          f"to a different map")


def _plan_cap(p: ImportPlan, rf) -> None:
    """A map past the vanilla engine's 200 provinces, going into a mod that is
    not marked as running on M2EX: the campaign would not load there."""
    from . import mapvocab, modflags
    count = sum(1 for r in rf.records if r.name)
    if count <= mapvocab.MAX_REGION_COLOURS or modflags.is_m2ex(p.dst):
        return
    p.warnings.append(
        f"this map has {count} provinces and the unmodified engine stops at "
        f"{mapvocab.MAX_REGION_COLOURS}. {p.src.name}"
        f"{' is marked as running on M2EX' if modflags.is_m2ex(p.src) else ''}; "
        f"{p.dst.name} is not, so the campaign will not load unless it runs on "
        f"M2EX too (the flag is on its Home card)")


def _plan_climates(p: ImportPlan, home: Path) -> None:
    """Climate colours the map paints that the destination does not declare."""
    from . import mapvocab
    name = "map_climates.tga"
    src = home / name if (home / name).is_file() \
        else Path(p.src.data) / campmap.BASE_REL / name
    if not src.is_file():
        return
    try:
        declared = mapvocab.climate_index(p.dst)
    except Exception:                                  # noqa: BLE001
        return
    if not declared:
        return
    try:
        from PIL import Image
        with Image.open(src) as im:
            colours = im.convert("RGB").getcolors(1 << 16) or []
    except Exception:                                  # noqa: BLE001
        return
    odd = [c for _, c in colours if mapvocab.key(c) not in declared]
    if odd:
        p.warnings.append(
            f"map_climates.tga paints {len(odd)} colour(s) {p.dst.name}'s "
            f"descr_climates.txt does not declare ({_shown([str(c) for c in odd], 4)}), "
            f"and the map checker calls that fatal. The Climates screen adds a climate.")


# ---------------------------------------------------------------------------
# names, portraits and text


def _plan_names(p: ImportPlan, sf, d: Destination, fmap: Dict[str, str]) -> None:
    """Every character's name into its new slot's pool, with its text key."""
    from . import minorfiles, namekeys
    voc = d.chars
    if not voc.have_pool:
        return
    src_keys = namekeys.loc_pairs(p.src, namekeys.POOL_LOC_REL)
    add: Dict[str, Dict[str, List[str]]] = {}
    for node in sf.of_kind("faction"):
        slot = fmap.get(node.name, node.name)
        pool = set(voc.pool.get(slot) or [])
        surnames = set(voc.surnames.get(slot) or [])
        for c in sf.descendants_of(node):
            if c.kind not in ("character", "character_record") or not c.name:
                continue
            gender = str(c.get("gender") or "male").lower()
            first, surname = namekeys.name_parts(c.name)
            for part, section, have in (
                    (first, namekeys.POOL_SECTIONS.get(gender, "characters"), pool),
                    (surname, "surnames", surnames)):
                if part and part not in have:
                    have.add(part)
                    add.setdefault(slot, {}).setdefault(section, []).append(part)
    if not add:
        return
    path = Path(p.dst.data) / namekeys.POOL_REL
    text = kb.read_text(path, namekeys.ENCODING)
    total = 0
    for slot, sections in add.items():
        nf = minorfiles.parse_names(text)
        fac = nf.get(slot)
        if fac is None:
            p.warnings.append(f"{namekeys.POOL_REL} has no `faction: {slot}` block, "
                              f"so {sum(len(v) for v in sections.values())} name(s) "
                              f"of its characters have no pool to go in")
            continue
        text = _add_names(nf, fac, sections)
        total += sum(len(v) for v in sections.values())
    if total:
        p.texts[namekeys.POOL_REL] = text
        p.changes.append(f"{namekeys.POOL_REL}: {total} character name(s) added to "
                         f"their new faction's pool")
    have = namekeys.loc_pairs(p.dst, namekeys.POOL_LOC_REL)
    state = namekeys.loc_state(p.dst, namekeys.POOL_LOC_REL)
    if state["txt"] or state["bin"]:
        writes = {}
        for sections in add.values():
            for parts in sections.values():
                for part in parts:
                    if part not in have:
                        value = (src_keys.get(part) or part.replace("_", " ")).strip()
                        if value and "{" not in value and "}" not in value:
                            writes[part] = value
        if writes:
            p.loc.setdefault(namekeys.POOL_LOC_REL, {}).update(writes)
            p.changes.append(f"{namekeys.POOL_LOC_REL}: {len(writes)} name key(s) "
                             f"from {p.src.name}")


def _add_names(nf, fac, sections: Dict[str, List[str]]) -> str:
    """Many names into one faction's pool in one splice, as the whole file's new
    text: :func:`unittransfer.namekeys._add_to_section`'s rule, batched, since
    a campaign brings hundreds of names and each single splice re-reads a file
    of tens of thousands of lines. The sections a faction has are written
    through :func:`~unittransfer.minorfiles.render_names`, index-aligned so
    every name already there stays on its line; a section it lacks is added
    at the foot of its block in the indentation its own sections use."""
    from . import minorfiles
    base = nf.block_text(fac)
    have = {name: [e.value for e in fac.section(name).entries] + parts
            for name, parts in sections.items() if fac.section(name) is not None}
    block = minorfiles.render_names(base, {"sections": have}) if have else base
    lacking = [(name, parts) for name, parts in sections.items()
               if fac.section(name) is None]
    if lacking:
        indent = (kb.indent_of(nf.lines[fac.sections[0].start])
                  if fac.sections else "\t")
        inner = (kb.indent_of(nf.lines[fac.sections[0].entries[0].line])
                 if fac.sections and fac.sections[0].entries else indent + "\t")
        rows = block.rstrip("\r\n").split(nf.newline)
        for name, parts in lacking:
            rows += [indent + name] + [inner + x for x in parts]
        block = nf.newline.join(rows)
    return nf.replace(fac.start, fac.end, block)


def _plan_portraits(p: ImportPlan, sf, d: Destination) -> None:
    """A custom portrait the destination lacks, copied from the source."""
    want = sorted({str(c.get("portrait")) for c in sf.of_kind("character")
                   if c.get("portrait")}, key=str.lower)
    if not want:
        return
    dst_root = Path(p.dst.data) / PORTRAITS_REL
    src_root = Path(p.src.data) / PORTRAITS_REL
    copied, lacking = [], []
    for name in want:
        if (dst_root / name).is_dir():
            continue
        folder = src_root / name
        if not folder.is_dir():
            lacking.append(name)
            continue
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                p.copies.append((f, f"{PORTRAITS_REL}/{name}/"
                                    f"{f.relative_to(folder).as_posix()}"))
        copied.append(name)
    if copied:
        p.changes.append(f"{PORTRAITS_REL}: {len(copied)} portrait folder(s) from "
                         f"{p.src.name}: {_shown(copied)}")
    if lacking:
        p.warnings.append(f"{len(lacking)} portrait(s) neither mod has a folder for: "
                          f"{_shown(lacking)}")


def _plan_text(p: ImportPlan, home: Path, fmap: Dict[str, str], body: dict) -> None:
    """Region names, historic events and the menu's words, as keys the
    destination lacks. A key it has keeps its own words."""
    from . import campevents
    # the region and settlement names
    rf = campmap.parse_regions(p.texts[f"{p.folder}/{REGIONS_NAME}"])
    want = set()
    for r in rf.records:
        for v in (r.name, r.settlement, r.legion):
            if v:
                want.add(v)
    _copy_keys(p, campmap.REGION_NAMES_REL, lambda k: k in want, "region and settlement name(s)")
    # the historic events this campaign fires
    events = set()
    ev = home / campevents.EVENTS_NAME
    if ev.is_file():
        for m in re.finditer(r"^[\t ]*event[\t ]+historic[\t ]+(\S+)",
                             kb.read_text(ev, ENCODING), re.M | re.I):
            events.add(m.group(1).upper())
    script = home / SCRIPT_NAME
    if script.is_file():
        for m in re.finditer(r"\bhistoric_event[\t ]+([A-Za-z0-9_]+)",
                             kb.read_text(script, ENCODING)):
            events.add(m.group(1).upper())
    keys = {f"{e}_{k}" for e in events for k in ("TITLE", "BODY")}
    _copy_keys(p, campevents.EVENT_TEXT_REL, lambda k: k.upper() in keys,
               "historic event text(s)", blind=True)
    # the new-game menu
    have = campfiles.descr_pairs(p.dst)
    pairs = campfiles.descr_pairs(p.src)
    src_head = campfiles.descr_token(p.campaign) + "_"
    new_head = campfiles.descr_token(p.name) + "_"
    up = {s.upper(): t.upper() for s, t in fmap.items()}
    for key, value in pairs.items():
        if not key.startswith(src_head):
            continue
        rest = key[len(src_head):]
        for s, t in up.items():
            if rest.startswith(s + "_") and rest[len(s) + 1:] in ("TITLE", "DESCR"):
                rest = t + rest[len(s):]
                break
        p.descr[new_head + rest] = value
    for kind, name in (("TITLE", "title"), ("DESCR", "blurb")):
        given = str(body.get(name) or "").strip()
        if given:
            p.descr[new_head + kind] = given
    p.descr_new = [k for k in p.descr if k not in have]
    if p.descr:
        p.changes.append(f"{campfiles.DESCR_REL}: {len(p.descr)} key(s) under "
                         f"{new_head}, {len(p.descr_new)} of them new")
    if not p.descr.get(new_head + "TITLE"):
        p.warnings.append(f"nothing names {p.name} on the new-game menu, so the "
                          f"engine shows the key {new_head}TITLE")


def _copy_keys(p: ImportPlan, rel: str, wanted, what: str, blind: bool = False) -> None:
    from . import namekeys
    state = namekeys.loc_state(p.dst, rel)
    if not (state["txt"] or state["bin"]):
        return
    have = namekeys.loc_pairs(p.dst, rel)
    low = {k.upper() for k in have} if blind else set(have)
    theirs = namekeys.loc_pairs(p.src, rel)
    writes: Dict[str, str] = {}
    differ = 0
    for key, value in theirs.items():
        if not wanted(key):
            continue
        if (key.upper() if blind else key) in low:
            if have.get(key) not in (None, value):
                differ += 1
            continue
        if "{" in value or "}" in value or "\n" in value:
            continue
        writes[key] = value
    if writes:
        p.loc.setdefault(rel, {}).update(writes)
        p.changes.append(f"{rel}: {len(writes)} {what} from {p.src.name}")
    if differ:
        p.warnings.append(f"{rel}: {differ} key(s) {p.dst.name} already has with "
                          f"other words keep {p.dst.name}'s, and every campaign of "
                          f"it reads them")


# ---------------------------------------------------------------------------
# the save


def apply(p: ImportPlan) -> dict:
    """Write the campaign and every file it needed, with one backup and one Undo."""
    from . import config, namekeys
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.copies and not p.texts:
        raise ValueError("there is nothing to import")
    there = Path(p.dst.data) / p.folder
    if there.exists() and any(f.is_file() for f in there.rglob("*")):
        raise ValueError(f"{p.folder} appeared since the plan was made")
    mod = p.dst
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = Path(mod.data) / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if rel not in manifest["backed_up"]:
                shutil.copy2(target, bpath)
                manifest["backed_up"].append(rel)
                file_op("BACKUP", target, f"-> {bpath}")
        elif rel not in manifest["created"]:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    for src, rel in p.copies:
        shutil.copy2(src, keep(rel))
    file_op("WRITE", Path(mod.data) / p.folder,
            f"{len(p.copies)} file(s) copied from {p.src.name}")
    for rel, text in sorted(p.texts.items()):
        target = keep(rel)
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    warnings = list(p.warnings)
    written = []
    for rel, writes in sorted(p.loc.items()):
        if writes:
            written.append(namekeys._write_loc(mod, rel, writes, keep, warnings)["file"])
    out: dict = {"id": tid, "name": p.name, "folder": p.folder, "files": p.files,
                 "text": written}
    if p.descr:
        out["loc"] = campfiles.write_descriptions(mod, p.descr, p.descr_new, keep, file_op)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campfiles", "action": "campaign_import",
        "source": p.src.name, "source_root": str(p.src.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {"campaign": p.campaign,
                    "factions": {f["source"]: f["slot"] for f in p.factions}},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": warnings,
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPAIGN IMPORT %s/%s -> %s as %s, %d file(s), id=%s", p.src.name,
             p.campaign, mod.name, p.name, p.files, tid)
    out["record"] = rec
    return out


# ---------------------------------------------------------------------------
# the form


def view(src, dst) -> dict:
    """What the form opens on: the source's campaigns and the destination's menu."""
    return {"source": getattr(src, "name", ""), "dest": getattr(dst, "name", ""),
            "campaigns": campnew.sources(src),
            "menu": campstrat.campaigns(dst),
            "dir": campstrat.CAMPAIGN_DIR_REL}
