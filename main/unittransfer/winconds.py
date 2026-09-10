"""``descr_win_conditions.txt``: what a faction has to do to win.

The last file 16j owes. A campaign is not finished when its map, its
settlements, its people and its diplomacy are written - somebody still has to be
able to win it, and the file that says how is the one file in the campaign
folder nothing in the toolkit could edit. 16g reads it already, to answer "which
factions is this province in the win conditions of"; this writes it.

**It is lines plus an index over them, the model
:mod:`unittransfer.campstrat` uses on ``descr_strat.txt``**, and for the same
reason: an edit rewrites the one line it means to change and leaves the mod's own
comments where they are - vanilla's file has 21 of them, including a
``;take_regions 35`` somebody left commented out mid-record.

**The format has no braces and no keyword to open a record.** A line that is a
bare word and is not one of the four condition words *is* the next faction. That
is 16g's reading and it is what the parse here uses, so the two agree by
construction rather than by luck.

**``short_campaign`` is a switch, not a line.** It prefixes the first line of the
short campaign's conditions and everything after it on that line and below
belongs to the short campaign until the next faction opens. All four installed
files write it exactly that way: **every one of the 74 records that has a short
campaign carries the switch on its ``hold_regions`` line**, so that is what is
written back.

**Measured over the four installed files, and each one shaped something here:**

* **The layout is the most regular in the whole game.** 492 value-bearing lines
  and not one of them is indented; every keyword is followed by a single space;
  every file is CRLF. So the only shape worth reading off a line is whether the
  line is there at all.
* **``hold_regions`` with nothing after it is a real line, and it is the common
  case.** 45 of those 74 short campaigns ask for no particular province, only a
  count - the line is there to carry the ``short_campaign`` switch and nothing
  else. A parser that required a region list would have refused 45 records, and
  a writer that dropped the empty line would have folded every one of those
  short campaigns into the long one.
* **Two of vanilla's 22 factions have no win record at all** - the Mongols and
  the Timurids, which are also the two with no settlement in
  ``descr_strat.txt``. A faction that
  arrives by script is not expected to win, so a missing record is a warning
  with that number on it and never a refusal.
* **A win condition may name a faction that is not in this campaign.** Vanilla's
  ``outlive`` lines name 17 factions and all 17 have blocks, but the engine reads
  the word rather than looking it up, so this reports an unknown one and does
  not refuse it.

**What is fatal is what the map has no room for**: a region the mod's own
``descr_regions.txt`` does not declare, and a count that is not a whole number.
A province held by nobody, a short campaign harder than the long one, a faction
asked to outlive itself: those are all things a real file could mean, so they
warn.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import campstrat
from .stratedit import assemble, finding, is_int, rewrite_line

ENCODING = campstrat.ENCODING
REL_NAME = "descr_win_conditions.txt"

#: The four words that are conditions rather than the name of a faction.
WORDS = ("hold_regions", "take_regions", "outlive", "short_campaign")

#: The six slots a record has, long campaign then short, in the order the file
#: writes them. ``short_campaign`` is a switch and not a slot - see the module
#: docstring.
SLOTS = ("hold", "take", "outlive", "short_hold", "short_take", "short_outlive")

#: Which keyword each slot is written with.
KEYWORD = {"hold": "hold_regions", "take": "take_regions", "outlive": "outlive",
           "short_hold": "hold_regions", "short_take": "take_regions",
           "short_outlive": "outlive"}

#: Which slots hold a list of words and which hold one number.
LISTS = ("hold", "outlive", "short_hold", "short_outlive")
COUNTS = ("take", "short_take")

#: The separator every one of the 492 real value lines uses.
SEP = " "

ACTIONS = ("edit", "add", "delete")

#: The newline a preview's lines are joined with. What goes to disk
#: is joined with the file's own, which every installed one writes
#: as CRLF.
NL = "\n"


def _clean(line: str) -> str:
    return line.split(";", 1)[0].strip()


# ---------------------------------------------------------------------------
# the file


@dataclass
class WinRecord:
    """One faction's win conditions, and every line they are made of."""

    faction: str = ""
    start: int = 0
    end: int = 0
    #: slot name to its value: a list of words, or an int
    values: Dict[str, object] = field(default_factory=dict)
    #: slot name to the line it was read from
    lines: Dict[str, int] = field(default_factory=dict)
    #: the line ``short_campaign`` is written on, or -1
    short_at: int = -1
    problems: List[str] = field(default_factory=list)

    def get(self, slot: str):
        return self.values.get(slot, 0 if slot in COUNTS else [])

    def payload(self) -> dict:
        return {"faction": self.faction, "line": self.start + 1,
                "lines": [self.start + 1, self.end + 1],
                **{s: self.get(s) for s in SLOTS},
                "problems": list(self.problems)}


@dataclass
class WinFile:
    """``descr_win_conditions.txt`` as its own lines, plus the records in them."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = False
    records: List[WinRecord] = field(default_factory=list)
    path: Optional[Path] = None

    def serialise(self) -> str:
        return (self.newline.join(self.lines)
                + (self.newline if self.trailing_newline else ""))

    def find(self, faction: str) -> Optional[WinRecord]:
        low = faction.lower()
        return next((r for r in self.records if r.faction.lower() == low), None)

    @property
    def problems(self) -> List[Tuple[int, str]]:
        return [(r.start, p) for r in self.records for p in r.problems]


def parse_wins(text: str) -> WinFile:
    """Read the whole file in one pass. Never raises.

    The same model as :func:`~unittransfer.campstrat.parse_strat` and the same
    reading of the format as :func:`~unittransfer.mapquery.parse_win_conditions`,
    with the line each value came from kept so that an edit can rewrite it.
    """
    from .triggers import split_lines

    lines, newline, trailing = split_lines(text)
    out = WinFile(lines=lines, newline=newline, trailing_newline=trailing)
    short = False
    for i, raw in enumerate(lines):
        s = _clean(raw)
        if not s:
            continue
        word, _, rest = s.partition(" ")
        low = word.lower()
        at_short = False
        if low == "short_campaign":
            short = at_short = True
            s = rest.strip()
            if not s:
                if out.records:
                    out.records[-1].short_at = i
                    out.records[-1].end = i
                continue
            word, _, rest = s.partition(" ")
            low = word.lower()
        if low not in WORDS:
            if len(s.split()) == 1:
                out.records.append(WinRecord(faction=s, start=i, end=i))
                short = False
            elif out.records:
                out.records[-1].problems.append(
                    f"line {i + 1} is neither a faction nor one of "
                    + ", ".join(WORDS) + f": {s!r}")
            continue
        if not out.records:
            continue
        rec = out.records[-1]
        rec.end = i
        if at_short:
            rec.short_at = i
        slot = ({"hold_regions": "hold", "take_regions": "take",
                 "outlive": "outlive"}[low])
        if short:
            slot = "short_" + slot
        if slot in COUNTS:
            got = rest.strip()
            rec.values[slot] = int(got) if re.fullmatch(r"\d+", got) else got
        else:
            rec.values[slot] = rest.split()
        rec.lines[slot] = i
    return out


def path_for(mod, campaign: str = campstrat.DEFAULT_CAMPAIGN) -> Path:
    return (mod.data / campstrat.CAMPAIGN_DIR_REL
            / campstrat.campaign_rel(campaign) / REL_NAME)


def read_wins(mod, campaign: str = campstrat.DEFAULT_CAMPAIGN) -> WinFile:
    """One campaign's ``descr_win_conditions.txt``. Raises if it is unreadable."""
    from .keyblock import read_text

    p = path_for(mod, campaign)
    out = parse_wins(read_text(p, ENCODING))
    out.path = p
    return out


# ---------------------------------------------------------------------------
# what is wrong with a record


class Vocabulary:
    """The provinces this map has and the factions this campaign runs.

    Both come from the fact table, which has already read
    ``descr_regions.txt`` and ``descr_strat.txt``; nothing here opens a file.
    """

    def __init__(self, facts):
        # `by_name` is keyed lower case for lookup; the province's own spelling
        # is on the record, and that is what a picker has to show and what an
        # edit has to write - `descr_regions.txt` writes London_Province
        by_name = getattr(facts, "by_name", {}) or {}
        self.regions = sorted(getattr(rf, "name", key) for key, rf
                              in by_name.items())
        self.region_lower = {r.lower() for r in self.regions}
        self.labels = {}
        for name in self.regions:
            rf = by_name.get(name.lower())
            self.labels[name] = (facts.label_of(rf) if rf is not None
                                 and hasattr(facts, "label_of") else name)
        sf = getattr(facts, "strat", None)
        self.factions = [n.name for n in sf.of_kind("faction")] if sf else []
        self.faction_lower = {f.lower() for f in self.factions}

    def payload(self) -> dict:
        return {"regions": list(self.regions), "labels": dict(self.labels),
                "factions": list(self.factions), "slots": list(SLOTS),
                "lists": list(LISTS), "counts": list(COUNTS)}


def check_record(voc: Vocabulary, faction: str,
                 values: Dict[str, object]) -> List[dict]:
    """Everything wrong with one faction's win conditions."""
    out: List[dict] = []
    if faction and voc.factions and faction.lower() not in voc.faction_lower:
        out.append(finding("win.faction", True,
                           f"{faction} has no faction block in this campaign, "
                           f"so nothing can win with it"))
    for slot in ("hold", "short_hold"):
        for region in values.get(slot) or []:
            if voc.regions and region.lower() not in voc.region_lower:
                out.append(finding("win.region", True,
                                   f"{region} is not a province this map "
                                   f"declares, and the "
                                   f"{'short' if slot.startswith('short') else 'long'}"
                                   f" campaign asks for it to be held"))
    for slot in COUNTS:
        got = values.get(slot)
        if got in (None, "", 0):
            continue
        if not is_int(got):
            out.append(finding("win.count", True,
                               f"{KEYWORD[slot]} says {got!r}, and it is a "
                               f"number of provinces"))
        elif voc.regions and int(got) > len(voc.regions):
            out.append(finding("win.too_many", False,
                               f"{KEYWORD[slot]} asks for {got} provinces and "
                               f"this map has {len(voc.regions)}, so the "
                               f"campaign cannot be won"))
    long_take = values.get("take") or 0
    short_take = values.get("short_take") or 0
    if is_int(long_take) and is_int(short_take) \
            and int(short_take) > int(long_take) > 0:
        out.append(finding("win.short_harder", False,
                           f"the short campaign asks for {short_take} provinces "
                           f"and the long one for {long_take}, so the short one "
                           f"is the harder of the two"))
    for slot in ("outlive", "short_outlive"):
        for who in values.get(slot) or []:
            if who.lower() == faction.lower():
                out.append(finding("win.outlive_self", False,
                                   f"{faction} is asked to outlive itself"))
            elif voc.factions and who.lower() not in voc.faction_lower:
                out.append(finding("win.outlive_unknown", False,
                                   f"{faction} is asked to outlive {who}, which "
                                   f"has no faction block in this campaign. The "
                                   f"engine reads the word rather than looking "
                                   f"it up, so this is a condition that can "
                                   f"never fail"))
    if not (values.get("hold") or values.get("take")):
        out.append(finding("win.nothing", False,
                           f"{faction}'s long campaign asks for no province and "
                           f"no count, so it is won at turn one"))
    return out


def check_file(voc: Vocabulary, wf: WinFile) -> List[dict]:
    """Everything wrong with the file as a whole."""
    out: List[dict] = []
    seen: Dict[str, int] = {}
    for rec in wf.records:
        low = rec.faction.lower()
        if low in seen:
            out.append(finding("win.twice", False,
                               f"{rec.faction} has a second record on line "
                               f"{rec.start + 1}; the engine reads the first"))
        seen[low] = rec.start
    missing = [f for f in voc.factions if f.lower() not in seen]
    if missing:
        out.append(finding("win.missing", False,
                           "no win condition for " + ", ".join(missing)
                           + ". Vanilla leaves two of its 22 factions out for "
                             "the same reason - the Mongols and the Timurids "
                             "arrive by script and are not expected to win"))
    return out


# ---------------------------------------------------------------------------
# rendering


def slot_line(slot: str, value, short_head: bool = False) -> str:
    """One condition line, in the shape all 492 real ones are written in."""
    head = ("short_campaign " if short_head else "") + KEYWORD[slot]
    if slot in COUNTS:
        return f"{head}{SEP}{value}"
    got = " ".join(str(x) for x in (value or []))
    return f"{head}{SEP}{got}" if got else head


#: The slots of each campaign, in the order the file writes them.
LONG = ("hold", "take", "outlive")
SHORT = ("short_hold", "short_take", "short_outlive")


def _said(values: Dict[str, object], slot: str) -> bool:
    return values.get(slot) not in (None, "", 0, [])


def render_record(faction: str, values: Dict[str, object]) -> List[str]:
    """A whole new record, long campaign then short.

    **A short campaign always opens on ``hold_regions``, even with nothing after
    it.** That is not a guess: all 74 real records with a short campaign write
    ``short_campaign hold_regions`` as its first line, and 45 of them have no
    province to name there. ``short_campaign`` is a switch and something has to
    carry it, so a record that opened its short campaign on ``take_regions``
    would be the only one of its kind in any installed file.
    """
    out = [faction]
    for slot in LONG:
        if _said(values, slot):
            out.append(slot_line(slot, values[slot]))
    if any(_said(values, slot) for slot in SHORT):
        out.append(slot_line("short_hold", values.get("short_hold"),
                             short_head=True))
        for slot in ("short_take", "short_outlive"):
            if _said(values, slot):
                out.append(slot_line(slot, values[slot]))
    return out


def record_span(wf: WinFile, rec: WinRecord) -> Tuple[int, int]:
    """A record's lines, and the blank run that separates it from the next.

    Every one of the four files puts a blank line between records - 75 of 75
    gaps - so a record that goes out takes its own separator with it, the way a
    faction block does in :mod:`unittransfer.stratcamp`.
    """
    last = rec.end
    while (last + 1 < len(wf.lines)
           and not _clean(wf.lines[last + 1])):
        last += 1
    return rec.start, last


# ---------------------------------------------------------------------------
# the plan


@dataclass
class WinPlan:
    """One faction's win conditions, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    faction: str = ""
    action: str = "edit"
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the record's new lines, for the preview
    block: str = ""
    #: ``[(first, last, lines written)]``, the runs of the file it may touch
    spans: List[Tuple[int, int, int]] = field(default_factory=list)
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} win conditions for {self.faction} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign} "
                f"({len(self.changes)} change(s))")
        return NL.join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"faction": self.faction, "action": self.action,
                "campaign": self.campaign, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "findings": list(self.findings), "block": self.block,
                "spans": [[a + 1, b + 1] for a, b, _n in self.spans],
                "ok": not self.errors and bool(self.text)}


def values_from_body(body: dict, base: Optional[Dict[str, object]] = None
                     ) -> Dict[str, object]:
    """The six slots off the wire, with anything not sent left as it was.

    A slot the form did not send is a slot nobody edited. Filling one in from a
    default here is how a panel that shows five fields quietly blanks the sixth
    - :mod:`unittransfer.stratcamp` makes the same ruling about a faction's
    scalars.
    """
    out: Dict[str, object] = dict(base or {})
    want = body.get("values")
    if not isinstance(want, dict):
        return out
    for slot in SLOTS:
        if slot not in want:
            continue
        got = want[slot]
        if slot in COUNTS:
            out[slot] = str(got).strip()
        elif isinstance(got, str):
            out[slot] = got.split()
        else:
            out[slot] = [str(x).strip() for x in (got or []) if str(x).strip()]
    return out


def _describe(before: Dict[str, object], after: Dict[str, object]) -> List[str]:
    """What changed, said the way somebody would say it out loud."""
    out: List[str] = []
    for slot in SLOTS:
        a, b = before.get(slot), after.get(slot)
        if slot in COUNTS:
            a, b = str(a or 0), str(b or 0)
            if a != b:
                out.append(f"{slot.replace('_', ' ')}: {a} -> {b}")
            continue
        was, now = list(a or []), list(b or [])
        if was == now:
            continue
        got = [x for x in now if x not in was]
        lost = [x for x in was if x not in now]
        if got:
            out.append(f"{slot.replace('_', ' ')}: added " + ", ".join(got))
        if lost:
            out.append(f"{slot.replace('_', ' ')}: removed " + ", ".join(lost))
        if not got and not lost:
            out.append(f"{slot.replace('_', ' ')}: reordered")
    return out


def _edit_splice(wf: WinFile, p: WinPlan, rec: WinRecord,
                 values: Dict[str, object]):
    """A record edited in place: rewrite what is there, add what is new, drop
    what is gone.

    The one thing that is not a line rewrite is ``short_campaign`` moving. It
    prefixes whichever short line comes first, so a record whose short campaign
    loses its ``hold_regions`` has to hand the switch to the line below it or
    the whole short campaign quietly becomes part of the long one.
    """
    rewrites: Dict[int, str] = {}
    drop: set = set()
    inserts: Dict[int, List[str]] = {}
    spans: List[Tuple[int, int, int]] = []

    # Which short lines this edit leaves behind, and therefore which of them
    # carries the switch. It has to be worked out from what will be written
    # rather than from what is said: a short campaign whose `hold_regions` is
    # empty still writes that line - 45 of the 74 real ones do - so the switch
    # stays on it, and computing the head off the first *stated* slot moved it
    # onto `take_regions` and left two `short_campaign` words in one record.
    any_short = any(_said(values, x) for x in SHORT)
    kept_short = [x for x in SHORT
                  if _said(values, x) or (x == "short_hold" and any_short)]
    head_slot = kept_short[0] if kept_short else ""
    for slot in SLOTS:
        at = rec.lines.get(slot)
        keeps = slot in LONG and _said(values, slot) or slot in kept_short
        head = slot == head_slot
        if at is None:
            if not keeps:
                continue
            # a slot the record never had: written under the last line it does.
            # Two new slots can land on one line - a record that gains a whole
            # short campaign gains three - so the runs these declare are
            # collected once at the end rather than one per line, or the same
            # insert point would be declared twice and counted twice.
            where = _insert_at(wf, rec, slot)
            inserts.setdefault(where, []).append(
                slot_line(slot, values.get(slot), short_head=bool(head)))
            continue
        if not keeps:
            drop.add(at)
            spans.append((at, at, 0))
            continue
        body = slot_line(slot, values.get(slot), short_head=bool(head))
        line = rewrite_line(wf.lines[at], body)
        if line != wf.lines[at]:
            rewrites[at] = line
            spans.append((at, at, 1))
    spans += [(at, at - 1, len(got)) for at, got in inserts.items()]
    p.spans = spans
    lines = assemble(wf.lines, rewrites, drop, inserts)
    p.block = NL.join(render_record(rec.faction, values))
    return lines


def _insert_at(wf: WinFile, rec: WinRecord, slot: str) -> int:
    """Where a line for a slot the record does not have goes.

    In the file's own order: after the last line of a slot that comes before it,
    and failing that on the line under the faction's name.
    """
    order = list(SLOTS)
    above = [rec.lines[s] for s in order[:order.index(slot)] if s in rec.lines]
    return (max(above) if above else rec.start) + 1


def _add_splice(wf: WinFile, p: WinPlan, values: Dict[str, object]):
    """A whole new record, at the bottom, separated the way the others are."""
    lines = render_record(p.faction, values)
    at = len(wf.lines)
    if wf.records:
        _, last = record_span(wf, wf.records[-1])
        at = last + 1
    gap = [""] if at and _clean(wf.lines[at - 1]) else []
    p.spans = [(at, at - 1, len(gap) + len(lines))]
    p.block = NL.join(lines)
    return assemble(wf.lines, {}, set(), {at: gap + lines})


def _delete_splice(wf: WinFile, p: WinPlan, rec: WinRecord):
    """A record and its own blank separator, taken out."""
    first, last = record_span(wf, rec)
    p.spans = [(first, last, 0)]
    p.block = ""
    return assemble(wf.lines, {}, set(range(first, last + 1)), {})


def _touched(before: WinFile, after: WinFile,
             spans: Sequence[Tuple[int, int, int]]) -> List[str]:
    """Every line this save changed that it never said it would.

    :func:`unittransfer.stratcamp._touched` on a smaller file, and the same
    walk: between one declared run and the next, every line has to be identical
    and in the same place, and below the last run both files have to match to
    the end.
    """
    out: List[str] = []
    b, a = before.lines, after.lines
    bi = ai = 0
    for lo, hi, kept in sorted(spans):
        if lo < bi:
            out.append(f"this save declares two runs that overlap at line "
                       f"{lo + 1}")
            return out
        for step in range(lo - bi):
            if b[bi + step] != a[ai + step]:
                out.append(f"this would rewrite line {bi + step + 1}, which "
                           f"this save never asked about: "
                           f"{b[bi + step].strip()[:60]!r}")
                return out
        ai += lo - bi
        bi, ai = hi + 1, ai + kept
    if b[bi:] != a[ai:]:
        out.append("this would rewrite the file below everything it asked "
                   "about")
    return out


def _guard(before: WinFile, after: WinFile, action: str, faction: str,
           spans: Sequence[Tuple[int, int, int]]) -> List[str]:
    """What the splice did that it was never asked to do."""
    out: List[str] = []
    step = {"edit": 0, "add": 1, "delete": -1}[action]
    if len(after.records) != len(before.records) + step:
        out.append(f"this would leave {len(after.records)} win conditions where "
                   f"the file has {len(before.records)}, and an {action} "
                   f"changes it by {step:+d}")
        return out
    low = faction.lower()
    was = {r.faction: r.values for r in before.records if r.faction.lower() != low}
    now = {r.faction: r.values for r in after.records if r.faction.lower() != low}
    if was != now:
        odd = sorted(set(was) ^ set(now)) or [k for k in was if was[k] != now.get(k)]
        out.append("this would rewrite the win conditions of "
                   + ", ".join(odd[:3]) + ", which nobody asked it to")
    out += _touched(before, after, spans)
    return out


def plan_win(mod, facts, body: dict) -> WinPlan:
    """Work out the whole new ``descr_win_conditions.txt`` for one save.

    ``body`` is ``{campaign, faction, action, values}`` and ``action`` is one of
    :data:`ACTIONS`.

    **The file is re-read here rather than taken from ``facts``**, for the
    reason 16h states where it does the same: the fact table is a cache, and a
    writer that writes out of a cache writes over whatever changed under it.
    """
    from .campmap import MapError

    campaign = str(body.get("campaign") or "") or facts.campaign
    action = str(body.get("action") or "edit").lower()
    p = WinPlan(mod=mod, campaign=campaign, action=action,
                faction=str(body.get("faction") or "").strip())
    if action not in ACTIONS:
        p.errors.append(f"no such action {action!r}. The three are "
                        + ", ".join(ACTIONS))
        return p
    try:
        wf = read_wins(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = wf.path
    voc = Vocabulary(facts)

    rec = wf.find(p.faction)
    if action != "add" and rec is None:
        p.errors.append(f"{p.faction or '(nothing)'} has no win condition in "
                        f"{campaign}'s {REL_NAME}. Adding one is the same panel "
                        f"with a different button")
        return p
    if action == "add" and rec is not None:
        p.errors.append(f"{p.faction} already has a win condition on line "
                        f"{rec.start + 1}")
        return p

    before = dict(rec.values) if rec is not None else {}
    if action == "delete":
        after: Dict[str, object] = {}
        lines = _delete_splice(wf, p, rec)
    else:
        after = values_from_body(body, before)
        p.findings = check_record(voc, p.faction, after)
        lines = (_add_splice(wf, p, after) if action == "add"
                 else _edit_splice(wf, p, rec, after))
    if p.errors:
        return p

    text = (wf.newline.join(lines)
            + (wf.newline if wf.trailing_newline else ""))
    done = parse_wins(text)
    p.errors += _guard(wf, done, action, p.faction, p.spans)
    if p.errors:
        return p
    p.findings += check_file(voc, done)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(before, after)
    if action == "add":
        p.changes.insert(0, f"a win condition for {p.faction}")
    elif action == "delete":
        p.changes = [f"{p.faction} is taken out of {REL_NAME}"]
    p.spans = [(a + 1, b + 1, n) for a, b, n in p.spans]
    p.text = "" if text == wf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


# ---------------------------------------------------------------------------
# the save


def apply_win(p: WinPlan) -> dict:
    """Write a planned save, with the same backups and undo as any other job."""
    import shutil
    import time

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    rel = f"{campstrat.CAMPAIGN_DIR_REL}/{p.campaign}/{REL_NAME}"
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [],
                                      "deleted": []}

    target = Path(mod.data) / rel
    bpath = backup_root / "data" / rel
    bpath.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, bpath)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", target, f"-> {bpath}")
    else:
        manifest["created"].append(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        "action": "win_conditions",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.faction, "resolved_type": p.faction,
        "options": {"campaign": p.campaign, "faction": p.faction,
                    "what": p.action},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("WIN %s %s in %s/%s - %d change(s), id=%s",
             p.action, p.faction, mod.name, p.campaign, len(p.changes), tid)
    return {"id": tid, "faction": p.faction, "campaign": p.campaign,
            "record": rec}


# ---------------------------------------------------------------------------
# the form


def win_detail(facts) -> dict:
    """Every faction's win conditions, everything the panel shows, in one call.

    Read off the disk rather than out of the fact table, unlike every other
    detail route in the campaign map: ``facts`` carries the *parsed conditions*
    (16g put them there to answer "which factions is this province in the win
    conditions of") but not the file's own lines, and this panel edits lines.
    """
    from .campmap import MapError

    mod = getattr(facts, "mod", None)
    if mod is None:
        raise MapError("no mod to read win conditions from")
    rel = f"{campstrat.CAMPAIGN_DIR_REL}/{facts.campaign}/{REL_NAME}"
    try:
        wf = read_wins(mod, facts.campaign)
    except OSError as exc:
        raise MapError(f"{rel} could not be read ({exc}). The stock game ships "
                       f"it on disk and so do both installed mods, so a "
                       f"campaign without one is a campaign nobody can win")
    voc = Vocabulary(facts)
    return {
        "campaign": facts.campaign,
        "file": rel,
        "records": [{**r.payload(),
                     "findings": check_record(voc, r.faction, r.values)}
                    for r in wf.records],
        "findings": check_file(voc, wf),
        "vocab": voc.payload(),
    }
