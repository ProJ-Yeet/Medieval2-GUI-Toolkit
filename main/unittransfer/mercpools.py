"""``descr_mercenaries.txt`` - the pools, every gate on every unit line, and the writes.

Phase 32a. The file was read by one parser before this, and the rule is still
one parser; what that parser kept was a pool's name, its regions and its unit
*names*, and every gate on a unit line went on the floor. This module is that
parser now, whole, and :func:`unittransfer.mapquery.parse_mercenaries` and
18a's G3 writer in :mod:`unittransfer.campfiles` are thin calls into it. Two
readers of a unit line is how the gates got dropped the first time.

**A unit line, as the file's own header documents it**::

    unit Raider Warband,\\t\\texp 0 cost 270 replenish 0.25 - 0.35 max 4 initial 3 religions { catholic } crusading

The name is everything in front of ``exp``. Not a word count: a name is one to
four words and both installed mods write a comma after it, with a run of tabs
to line the columns up. Then five fixed fields - ``exp``, ``cost``,
``replenish lo - hi``, ``max``, ``initial`` - and any of the optionals in any
order: ``start_year N``, ``end_year N``, ``religions { }``, ``events { }``,
``crusading``, and ``factions { }``, which the header does not document and
Third Age Reforged's Fellowship campaign writes on 41 of its 51 lines.

**Counted on all three campaign files on this machine**, 363 unit lines: every
one has the five fixed fields in that order, no option word appears that is not
one of the six above, and no line is anything but ``pool``, ``regions``,
``unit``, a comment or blank. DaC ends without a newline; all three are CRLF.
The optional words seen: ``religions`` 317, ``events`` 105, ``factions`` 41,
``crusading`` 28, ``start_year`` 2, ``end_year`` none. An option word this
module does not know is kept on the line and reported, never dropped.

**Writing is a splice, one field at a time.** A value is replaced between its
own character positions, an option that is added goes on the end of the code
part, one that is removed takes the whitespace in front of it with it, and the
tab columns, the comment after a line and DaC's ``;RATE_H`` notes at the top of
the file are never touched. ``parse_text(t).text() == t`` on every file, and
every plan re-reads its own output and refuses a save in which any record it
did not name has changed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb
from .triggers import split_lines

MERCS_NAME = "descr_mercenaries.txt"
ENCODING = "latin-1"

#: the fields every unit line carries, in the order it carries them
FIXED = ("exp", "cost", "replenish", "max", "initial")
#: a key followed by one whole number
NUMBERS = ("exp", "cost", "max", "initial", "start_year", "end_year")
#: a key followed by ``{ a b c }``
LISTS = ("religions", "events", "factions")
#: a key standing on its own
FLAGS = ("crusading",)
OPTIONAL = ("start_year", "end_year", "religions", "events", "factions", "crusading")
FIELDS = FIXED + OPTIONAL

_HEAD = re.compile(r"^(?P<head>\s*unit\s+)(?P<name>.*?)(?P<sep>[\s,]*)(?=\bexp\b)",
                   re.I)
_TOKEN = re.compile(r"\{[^}]*\}?|[^\s{}]+")
_INT = re.compile(r"^-?\d+$")
_NUM = re.compile(r"^-?(\d+(\.\d*)?|\.\d+)$")
_WORD = re.compile(r"^[^\s{};]+$")


class MercError(kb.BlockError):
    """An edit the file cannot take, or a name the file does not have."""


@dataclass
class MercUnit:
    """One ``unit`` line, with where each of its values sits on the line."""

    name: str
    line: int
    exp: Optional[int] = None
    cost: Optional[int] = None
    replenish: Optional[Tuple[float, float]] = None
    max: Optional[int] = None
    initial: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    religions: Optional[List[str]] = None
    events: Optional[List[str]] = None
    factions: Optional[List[str]] = None
    crusading: bool = False
    #: option words this module does not know, kept on the line
    extra: List[str] = field(default_factory=list)
    #: what could not be read, "" when the line is whole
    fault: str = ""
    #: field -> (key start, value start, value end) on the raw line
    spans: Dict[str, Tuple[int, int, int]] = field(default_factory=dict)
    name_span: Tuple[int, int] = (0, 0)

    def record(self) -> Dict:
        """The line's values, and only its values - what a comparison sees."""
        return {"name": self.name, "exp": self.exp, "cost": self.cost,
                "replenish": list(self.replenish) if self.replenish else None,
                "max": self.max, "initial": self.initial,
                "start_year": self.start_year, "end_year": self.end_year,
                "religions": self.religions, "events": self.events,
                "factions": self.factions, "crusading": self.crusading,
                "extra": list(self.extra), "fault": self.fault}

    def payload(self) -> Dict:
        return dict(self.record(), line=self.line + 1)


@dataclass
class MercPool:
    name: str
    line: int
    regions: List[str] = field(default_factory=list)
    #: every ``regions`` line the pool has, in order - one on every real file
    regions_lines: List[int] = field(default_factory=list)
    units: List[MercUnit] = field(default_factory=list)
    #: the last ``regions`` or ``unit`` line of the block
    end: int = 0

    @property
    def unit_names(self) -> List[str]:
        return [u.name for u in self.units]


@dataclass
class MercFile:
    """The file held as lines, with the pools read off them."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    pools: List[MercPool] = field(default_factory=list)
    #: pool name -> 0-based line of its first ``regions`` line, -1 when none
    regions_line: Dict[str, int] = field(default_factory=dict)
    #: pool name -> 0-based line of its ``pool`` line
    pool_line: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def text(self) -> str:
        return _join(self.lines, self.newline, self.trailing_newline)

    def pool(self, name: str) -> Optional[MercPool]:
        return next((p for p in self.pools if p.name == name), None)

    def pool_of(self, region: str) -> str:
        low = region.lower()
        for p in self.pools:
            if any(r.lower() == low for r in p.regions):
                return p.name
        return ""


def _join(lines: List[str], newline: str, trailing: bool) -> str:
    out = newline.join(lines)
    return out + newline if trailing and lines else out


def _code_len(raw: str) -> int:
    """Where the code part of a raw line ends - at ``;``, trailing space kept."""
    at = raw.find(";")
    return len(raw) if at < 0 else at


# ---------------------------------------------------------------------------
# reading


def parse_unit(raw: str, line: int = 0) -> MercUnit:
    """One ``unit`` line. Never raises: what cannot be read goes in ``fault``."""
    code = raw[:_code_len(raw)]
    m = _HEAD.match(code)
    if not m:
        rest = code.strip()[4:].strip().rstrip(",").strip()
        start = code.find(rest) if rest else len(code)
        return MercUnit(name=rest, line=line, fault="no `exp` on the line",
                        name_span=(start, start + len(rest)))
    u = MercUnit(name=m["name"].strip(), line=line,
                 name_span=(m.start("name"), m.start("name") + len(m["name"].rstrip())))
    toks = [(t.group(0), t.start(), t.end()) for t in _TOKEN.finditer(code, m.end())]
    i = 0

    def fault(msg: str) -> None:
        if not u.fault:
            u.fault = msg

    while i < len(toks):
        word, ks, ke = toks[i]
        key = word.lower()
        if key in NUMBERS:
            if i + 1 >= len(toks) or not _INT.match(toks[i + 1][0]):
                fault(f"`{word}` is not followed by a whole number")
                i += 1
                continue
            val, vs, ve = toks[i + 1]
            setattr(u, key, int(val))
            u.spans[key] = (ks, vs, ve)
            i += 2
        elif key == "replenish":
            # `lo - hi` is three tokens on every real line; `lo-hi` is one
            nxt = [t for t in toks[i + 1:i + 4]]
            lo = hi = None
            if len(nxt) >= 3 and nxt[1][0] == "-" and _NUM.match(nxt[0][0]) \
                    and _NUM.match(nxt[2][0]):
                lo, hi, vs, ve, used = nxt[0][0], nxt[2][0], nxt[0][1], nxt[2][2], 3
            elif nxt and re.match(r"^-?[\d.]+-[\d.]+$", nxt[0][0]):
                lo, hi = nxt[0][0].rsplit("-", 1)
                vs, ve, used = nxt[0][1], nxt[0][2], 1
            if lo is None or not _NUM.match(lo) or not _NUM.match(hi):
                fault("`replenish` is not followed by `low - high`")
                i += 1
                continue
            u.replenish = (float(lo), float(hi))
            u.spans[key] = (ks, vs, ve)
            i += 1 + used
        elif key in LISTS:
            if i + 1 >= len(toks) or not toks[i + 1][0].startswith("{"):
                fault(f"`{word}` is not followed by `{{ ... }}`")
                i += 1
                continue
            val, vs, ve = toks[i + 1]
            if not val.endswith("}"):
                fault(f"`{word} {{` is never closed")
            setattr(u, key, val.strip("{}").split())
            u.spans[key] = (ks, vs, ve)
            i += 2
        elif key in FLAGS:
            u.crusading = True
            u.spans[key] = (ks, ks, ke)
            i += 1
        else:
            u.extra.append(word)
            fault(f"`{word}` is not a word this file's format has")
            i += 1
    missing = [f for f in FIXED if f not in u.spans]
    if missing:
        fault("missing " + ", ".join(missing))
    return u


def parse_text(text: str) -> MercFile:
    """The whole file. Never raises."""
    lines, newline, trailing = split_lines(text)
    mf = MercFile(lines=lines, newline=newline, trailing_newline=trailing)
    cur: Optional[MercPool] = None
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        word, _, rest = code.partition(" ")
        low = word.lower()
        if low == "pool":
            cur = MercPool(name=rest.strip(), line=i, end=i)
            if cur.name in mf.pool_line:
                mf.warnings.append(f"line {i + 1}: a second pool called "
                                   f"{cur.name}; edits go to the first")
            mf.pools.append(cur)
            mf.pool_line.setdefault(cur.name, i)
            mf.regions_line.setdefault(cur.name, -1)
        elif cur is None:
            mf.warnings.append(f"line {i + 1}: `{word}` before any pool")
        elif low == "regions":
            cur.regions.extend(rest.split())
            cur.regions_lines.append(i)
            cur.end = i
            if mf.regions_line.get(cur.name, -1) >= 0:
                if mf.pool(cur.name) is cur:
                    mf.warnings.append(f"line {i + 1}: a second `regions` line for "
                                       f"pool {cur.name}; the first one is edited")
            elif mf.pool(cur.name) is cur:
                mf.regions_line[cur.name] = i
        elif low == "unit":
            cur.units.append(parse_unit(raw, i))
            cur.end = i
        else:
            mf.warnings.append(f"line {i + 1}: `{word}` is not pool, regions or unit")
    return mf


def path_for(mod, campaign: str) -> Path:
    from . import campstrat
    return (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
            / campstrat.campaign_rel(campaign) / MERCS_NAME)


def read(mod, campaign: str) -> Tuple[MercFile, str]:
    path = path_for(mod, campaign)
    if not path.is_file():
        raise MercError(f"{campaign} has no {MERCS_NAME}, so no province in it "
                        "has a mercenary pool")
    text = kb.read_text(path, ENCODING)
    return parse_text(text), text


# ---------------------------------------------------------------------------
# one unit line


def _fmt_num(v) -> str:
    return str(v).strip()


def _fmt_list(items: List[str]) -> str:
    return "{ " + " ".join(items) + " }" if items else "{ }"


def check_edit(key: str, value) -> Tuple[str, str]:
    """``(canonical text, "")`` or ``("", error)`` for one field's new value.

    ``None`` means "take the option off", and only an optional can be taken off.
    """
    if key not in FIELDS and key != "name":
        return "", f"`{key}` is not a field of a unit line"
    if value is None:
        if key in FIXED or key == "name":
            return "", f"`{key}` is on every unit line and cannot be taken off"
        return "", ""
    if key == "name":
        v = " ".join(str(value).split()).rstrip(",").strip()
        if not v or ";" in v or re.search(r"\bexp\b", v, re.I):
            return "", f"`{value}` cannot be a unit name here"
        return v, ""
    if key in NUMBERS:
        v = _fmt_num(value)
        if not _INT.match(v):
            return "", f"{key} has to be a whole number, not `{value}`"
        if int(v) < 0:
            return "", f"{key} cannot be below zero"
        if key == "exp" and int(v) > 9:
            return "", "exp runs from 0 to 9"
        return v, ""
    if key == "replenish":
        try:
            lo, hi = [_fmt_num(x) for x in value]
        except (TypeError, ValueError):
            return "", "replenish is two numbers, low and high"
        if not (_NUM.match(lo) and _NUM.match(hi)):
            return "", f"replenish has to be two numbers, not `{lo} - {hi}`"
        if float(lo) < 0 or float(hi) < 0:
            return "", "a replenish rate cannot be below zero"
        return f"{lo} - {hi}", ""
    if key in LISTS:
        items = value.split() if isinstance(value, str) else [str(x) for x in value]
        bad = [x for x in items if not _WORD.match(x)]
        if bad:
            return "", f"`{bad[0]}` cannot go in a {key} list"
        return _fmt_list(items), ""
    return ("crusading" if value else ""), ""


def set_field(raw: str, key: str, value) -> str:
    """``raw`` with one field set, added or taken off. Nothing else moves."""
    text, err = check_edit(key, value)
    if err:
        raise MercError(err)
    u = parse_unit(raw)
    if key == "name":
        s, e = u.name_span
        return raw[:s] + text + raw[e:]
    have = key in u.spans
    if key in FLAGS:
        value = bool(value)
        if value == have:
            return raw
        if not value:
            return _cut(raw, u.spans[key])
        return _append(raw, key)
    if value is None:
        return _cut(raw, u.spans[key]) if have else raw
    if have:
        # the same value written another way - `0.10` for `0.1` - is not an
        # edit, and rewriting it would be a change nobody asked for
        if _value_of(u, key) == _value_of(parse_unit(f"unit x exp 0 {key} {text}"
                                                     if key not in FIXED[:1] else
                                                     f"unit x exp {text}"), key):
            return raw
        _, vs, ve = u.spans[key]
        return raw[:vs] + text + raw[ve:]
    if key in FIXED:
        raise MercError(f"this line has no `{key}` to set, and a fixed field is "
                        "not added out of its order")
    return _append(raw, f"{key} {text}")


def _value_of(u: MercUnit, key: str):
    return u.record().get(key)


def _cut(raw: str, span: Tuple[int, int, int]) -> str:
    ks, _, ve = span
    start = ks
    while start > 0 and raw[start - 1] in " \t":
        start -= 1
    return raw[:start] + raw[ve:]


def _append(raw: str, words: str) -> str:
    code_end = _code_len(raw)
    code = raw[:code_end]
    body = code.rstrip()
    return body + " " + words + raw[len(body):]


def unit_line(template: Optional[str], values: Dict) -> str:
    """A new unit line, laid out like ``template`` - its indent and the gap after
    the name - or with one tab and a comma when the file has no unit to copy."""
    indent, sep = "\t", ",\t\t"
    if template:
        m = _HEAD.match(template[:_code_len(template)])
        if m:
            indent = m["head"][:len(m["head"]) - len(m["head"].lstrip())]
            sep = m["sep"] or " "
    name, err = check_edit("name", values.get("name"))
    if err:
        raise MercError(err)
    parts = []
    for key in FIXED:
        if values.get(key) is None:
            raise MercError(f"a new unit line needs `{key}`")
        text, err = check_edit(key, values[key])
        if err:
            raise MercError(err)
        parts.append(f"{key} {text}")
    raw = f"{indent}unit {name}{sep}" + " ".join(parts)
    for key in OPTIONAL:
        if values.get(key) not in (None, False):
            raw = set_field(raw, key, values[key])
    return raw


# ---------------------------------------------------------------------------
# the file's edits. Each returns the whole new text.


def _result(mf: MercFile, sp: kb.Splice) -> str:
    return _join(sp.result(), mf.newline, mf.trailing_newline)


def _need_pool(mf: MercFile, name: str) -> MercPool:
    p = mf.pool(name)
    if p is None:
        raise MercError(f"there is no pool called {name!r} in {MERCS_NAME}")
    return p


def _need_unit(p: MercPool, index) -> MercUnit:
    try:
        i = int(index)
    except (TypeError, ValueError):
        raise MercError(f"pick a unit of pool {p.name} by its place in the pool")
    if not 0 <= i < len(p.units):
        raise MercError(f"pool {p.name} has {len(p.units)} unit line(s), not a "
                        f"number {i + 1}")
    return p.units[i]


def edit_unit(mf: MercFile, pool: str, index, edits: Dict) -> str:
    u = _need_unit(_need_pool(mf, pool), index)
    raw = mf.lines[u.line]
    for key, value in edits.items():
        raw = set_field(raw, key, value)
    sp = kb.Splice(mf.lines)
    sp.replace(u.line, raw)
    return _result(mf, sp)


def add_unit(mf: MercFile, pool: str, values: Dict) -> str:
    p = _need_pool(mf, pool)
    template = mf.lines[p.units[-1].line] if p.units else next(
        (mf.lines[u.line] for q in mf.pools for u in q.units), None)
    sp = kb.Splice(mf.lines)
    sp.after(p.end, [unit_line(template, values)])
    return _result(mf, sp)


def delete_unit(mf: MercFile, pool: str, index) -> str:
    u = _need_unit(_need_pool(mf, pool), index)
    sp = kb.Splice(mf.lines)
    sp.drop(u.line)
    return _result(mf, sp)


def set_regions(line: str, names: List[str]) -> str:
    """Rewrite a ``regions`` line's list, keeping its indent, gap and comment.

    Not :func:`unittransfer.keyblock.sub_tokens`, which walks the tokens already
    on the line and substitutes into them: that is right for the fixed-width
    columns it was written for and wrong here, because a shorter list would
    leave every province past its end still on the line. This one owns the whole
    tail of the line, which is what a variable-length list needs.
    """
    code = line.partition(";")[0]
    indent = kb.indent_of(code)
    rest = code[len(indent) + len("regions"):]
    gap = rest[:len(rest) - len(rest.lstrip())] or " "
    return kb.keep_comment(line, indent + "regions" + gap + " ".join(names))


def move_region(mf: MercFile, region: str, pool: str) -> str:
    """The whole file with ``region`` taken out of every pool and put in ``pool``.

    An empty ``pool`` takes the province out of all of them, which is a real
    state: 45 of Divide and Conquer's provinces are in no pool and sell nothing.
    The word is spliced into the existing ``regions`` line rather than the line
    being rewritten, so the tab columns the file is laid out in survive.
    """
    low = region.lower()
    if pool and pool not in mf.regions_line:
        raise MercError(f"there is no pool called {pool!r} in {MERCS_NAME}")
    sp = kb.Splice(list(mf.lines))
    touched = False
    for p in mf.pools:
        at = mf.regions_line.get(p.name, -1)
        if at < 0 or mf.pool(p.name) is not p:
            continue
        here = [r for r in p.regions if r.lower() == low]
        want = p.name == pool
        if bool(here) == want:
            continue
        kept = [r for r in p.regions if r.lower() != low]
        if want:
            kept.append(region)
        if kept:
            sp.replace(at, set_regions(mf.lines[at], kept))
        else:
            # `regions` with nothing after it is not a line any real file
            # writes, so the pool loses the line rather than keeping an empty one
            sp.drop(at)
        touched = True
    if pool and mf.regions_line.get(pool, -1) < 0:
        # a pool with no regions line at all: give it one, under its `pool` line
        at = mf.pool_line[pool]
        indent = kb.indent_of(mf.lines[at + 1]) if at + 1 < len(mf.lines) else "\t"
        sp.after(at, [f"{indent or chr(9)}regions {region}"])
        touched = True
    if not touched:
        return mf.text()
    return _result(mf, sp)


def add_pool(mf: MercFile, name: str, regions: Optional[List[str]] = None) -> str:
    """A new pool at the end of the file, laid out like the first pool in it."""
    name = str(name or "").strip()
    if not name or not _WORD.match(name):
        raise MercError(f"`{name}` cannot be a pool name - one word, no braces")
    if mf.pool(name) is not None:
        raise MercError(f"there is already a pool called {name}")
    regions = [r for r in (regions or []) if r]
    taken = [(r, mf.pool_of(r)) for r in regions if mf.pool_of(r)]
    if taken:
        raise MercError(f"{taken[0][0]} is already in pool {taken[0][1]} - move it "
                        "rather than put it in two")
    indent = "\t"
    first = next((p for p in mf.pools if p.regions_lines), None)
    if first is not None:
        indent = kb.indent_of(mf.lines[first.regions_lines[0]]) or "\t"
    block = [f"pool {name}"] + ([f"{indent}regions " + " ".join(regions)]
                                if regions else [])
    lines = list(mf.lines)
    while lines and not lines[-1].strip():
        lines.pop()
    tail = mf.lines[len(lines):]
    lines += [""] + block
    # keep however the file ended: DaC has no final newline, the others do
    return _join(lines + tail, mf.newline, mf.trailing_newline)


def delete_pool(mf: MercFile, name: str) -> str:
    """The pool's block out - its lines through its last unit, and one blank
    line that separated it, so the gap between the pools either side stays one."""
    p = _need_pool(mf, name)
    sp = kb.Splice(mf.lines)
    for i in range(p.line, p.end + 1):
        sp.drop(i)
    after = p.end + 1
    before = p.line - 1
    if after < len(mf.lines) and not mf.lines[after].strip():
        sp.drop(after)
    elif before >= 0 and not mf.lines[before].strip():
        sp.drop(before)
    return _result(mf, sp)


# ---------------------------------------------------------------------------
# the view


def overview(mod, campaign: str) -> Dict:
    """Every pool with every unit line whole, and what could not be read."""
    mf, _ = read(mod, campaign)
    faults = [{"pool": p.name, "unit": u.name, "line": u.line + 1,
               "message": u.fault}
              for p in mf.pools for u in p.units if u.fault]
    return {
        "campaign": campaign, "file": MERCS_NAME,
        "pools": [{"name": p.name, "line": p.line + 1, "regions": list(p.regions),
                   "units": [u.payload() for u in p.units]} for p in mf.pools],
        "faults": faults, "warnings": list(mf.warnings),
        "counts": {"pools": len(mf.pools),
                   "regions": sum(len(p.regions) for p in mf.pools),
                   "units": sum(len(p.units) for p in mf.pools),
                   "distinct_units": len({u.name for p in mf.pools for u in p.units})},
    }


# ---------------------------------------------------------------------------
# the save


ACTIONS = ("unit_edit", "unit_add", "unit_delete", "pool_add", "pool_delete",
           "region_move")


@dataclass
class MercPlan:
    mod: object = None
    campaign: str = ""
    action: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    text: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} in {self.campaign}/{MERCS_NAME} of "
                f"{getattr(self.mod, 'name', '?')} ({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"action": self.action, "campaign": self.campaign,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "ok": not self.errors and bool(self.text)}


def _records(mf: MercFile) -> Dict[Tuple[str, int], Dict]:
    return {(p.name, i): u.record() for p in mf.pools for i, u in enumerate(p.units)}


def _say(u: Dict) -> str:
    r = u.get("replenish") or ["?", "?"]
    return (f"{u['name']} (exp {u['exp']}, cost {u['cost']}, replenish "
            f"{r[0]} - {r[1]}, max {u['max']}, initial {u['initial']})")


def plan(mod, body: dict) -> MercPlan:
    """One save, worked out without touching the disk.

    ``body`` is ``{campaign, action, pool, unit, edits, values, region, name,
    regions}``: ``unit`` is a unit's place in its pool, ``edits`` the fields of
    an existing line (``null`` takes an option off), ``values`` a new line whole.
    """
    from . import campstrat
    p = MercPlan(mod=mod, campaign=str(body.get("campaign") or campstrat.DEFAULT_CAMPAIGN),
                 action=str(body.get("action") or ""))
    if p.action not in ACTIONS:
        p.errors.append(f"a mercenary save is one of {kb.and_list(list(ACTIONS))}, "
                        f"not {p.action!r}")
        return p
    try:
        mf, original = read(mod, p.campaign)
    except MercError as e:
        p.errors.append(e.message)
        return p
    p.path = path_for(mod, p.campaign)
    pool = str(body.get("pool") or "").strip()
    before = _records(mf)
    try:
        if p.action == "unit_edit":
            q = _need_pool(mf, pool)
            u = _need_unit(q, body.get("unit"))
            edits = dict(body.get("edits") or {})
            text = edit_unit(mf, pool, body.get("unit"), edits)
            was = u.record()
            now = parse_unit(split_lines(text)[0][u.line]).record()
            for k in edits:
                if was.get(k) != now.get(k):
                    p.changes.append(f"{pool}: {u.name} {k} {_show(was.get(k))} -> "
                                     f"{_show(now.get(k))}")
            expect = {(pool, int(body.get("unit"))): now}
        elif p.action == "unit_add":
            values = dict(body.get("values") or {})
            text = add_unit(mf, pool, values)
            q = _need_pool(mf, pool)
            new = parse_text(text).pool(pool).units[-1].record()
            p.changes.append(f"{pool}: + {_say(new)}")
            expect = {(pool, len(q.units)): new}
        elif p.action == "unit_delete":
            q = _need_pool(mf, pool)
            u = _need_unit(q, body.get("unit"))
            text = delete_unit(mf, pool, body.get("unit"))
            p.changes.append(f"{pool}: - {_say(u.record())}")
            # everything after it in the pool moves up one place
            i = int(body.get("unit"))
            expect = {(pool, j): None for j in range(i, len(q.units))}
            expect.update({(pool, j - 1): q.units[j].record()
                           for j in range(i + 1, len(q.units))})
        elif p.action == "pool_add":
            name = str(body.get("name") or pool).strip()
            regions = [str(r) for r in (body.get("regions") or [])]
            text = add_pool(mf, name, regions)
            p.changes.append(f"+ pool {name}" + (f" over {len(regions)} province(s)"
                                                   if regions else ", in no province yet"))
            expect = {}
        elif p.action == "pool_delete":
            q = _need_pool(mf, pool)
            text = delete_pool(mf, pool)
            p.changes.append(f"- pool {pool}: {len(q.units)} unit line(s), "
                             f"{len(q.regions)} province(s)")
            if q.regions:
                p.warnings.append(f"{len(q.regions)} province(s) are left in no pool, "
                                  "so no mercenary is recruitable there")
            expect = {(pool, j): None for j in range(len(q.units))}
        else:
            region = str(body.get("region") or "").strip()
            if not region:
                raise MercError("moving a province between pools needs the province")
            was = mf.pool_of(region)
            text = move_region(mf, region, pool)
            p.changes.append(f"{region}: mercenary pool {was or '(none)'} -> "
                             f"{pool or '(none)'}")
            if not pool:
                p.warnings.append(f"{region} is now in no pool, so no mercenary is "
                                  "recruitable there")
            expect = {}
    except MercError as e:
        p.errors.append(e.message)
        return p

    after = parse_text(text)
    got = _records(after)
    stray = [k for k in set(before) | set(got)
             if k not in expect and before.get(k) != got.get(k)]
    wrong = [k for k, v in expect.items() if got.get(k) != v]
    if stray or wrong:
        k = (stray or wrong)[0]
        p.errors.append(f"refused: the save would change {k[0]} unit {k[1] + 1} "
                        "as well as what it names")
        return p
    names = [q.name for q in mf.pools]
    if p.action == "pool_add":
        names.append(str(body.get("name") or pool).strip())
    elif p.action == "pool_delete":
        names.remove(pool)
    if [q.name for q in after.pools] != names:
        p.errors.append("refused: the save would change which pools the file has")
        return p
    for (qn, i), rec in expect.items():
        if rec is None:
            continue
        if rec["fault"]:
            p.errors.append(f"{qn}: {rec['name']} would not read back - {rec['fault']}")
        if rec["max"] is not None and rec["initial"] is not None                 and rec["initial"] > rec["max"]:
            p.warnings.append(f"{qn}: {rec['name']} starts with {rec['initial']} and "
                              f"its pool holds at most {rec['max']}")
        rep = rec["replenish"]
        if rep and rep[0] > rep[1]:
            p.warnings.append(f"{qn}: {rec['name']} replenishes from {rep[0]} to a "
                              f"lower {rep[1]}")
        if rec["crusading"] and not rec["religions"]:
            p.warnings.append(f"{qn}: {rec['name']} is `crusading` with no religions, "
                              "and the file's header says it needs one")
    if p.errors:
        return p
    p.text = "" if text == original else text
    if not p.text:
        p.errors.append("nothing to change")
    return p


def _show(v) -> str:
    if v is None:
        return "(none)"
    if isinstance(v, list):
        return "{ " + " ".join(str(x) for x in v) + " }"
    return str(v)


def apply(p: MercPlan) -> Dict:
    """Write a planned save with a backup and an undo, like every other editor."""
    import shutil
    import time

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    rel = str(p.path.relative_to(Path(mod.data))).replace("\\", "/")
    bpath = backup_root / "data" / rel
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p.path, bpath)
    file_op("BACKUP", p.path, f"-> {bpath}")
    kb.write_text(p.path, p.text, ENCODING)
    file_op("WRITE", p.path, f"{len(p.text)} bytes")
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "mercpools",
        "action": p.action,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.campaign, "resolved_type": MERCS_NAME,
        "options": {"campaign": p.campaign},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": {"backed_up": [rel], "created": []},
        "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("MERCS %s in %s/%s - %d change(s), id=%s", p.action, mod.name,
             p.campaign, len(p.changes), tid)
    return {"id": tid, "record": rec}


# ---------------------------------------------------------------------------
# 32b - the join: who can hire what, and where
#
# A unit line carries up to five gates and none of them names a province: the
# province side is only ever "which pool". So the question a person asks - can
# this faction hire this unit here, and if not, why - is a join over five other
# files, and every one of them is read here and nowhere in the page.
#
#   gate on the line          resolved against
#   the unit's name           the mod's EDU
#   religions { }             the faction's religion in descr_sm_factions.txt
#   factions { }              the faction itself (undocumented; Fellowship)
#   crusading                 nothing on disk - it is a state of an army
#   events { }                descr_events.txt, and what the campaign's scripts set
#   start_year / end_year     the campaign's own start_date and end_date


#: a gate's verdict. `no` is never, `later` is not from turn one, `unknown` is
#: a name nothing we can read sets, `info` is a gate that depends on a faction
#: when none is picked
GATE_STATES = ("ok", "no", "later", "unknown", "info")

_SET_EVENT = re.compile(
    r"^[ \t]*(?:set_event_counter|inc_event_counter|historic_event|declare_counter)"
    r"[ \t]+(\S+)", re.M | re.I)


def _year(value) -> Optional[int]:
    m = re.match(r"\s*(-?\d+)", str(value or ""))
    return int(m.group(1)) if m else None


def campaign_years(mod, campaign: str) -> Dict:
    """``{start, end, timescale}`` off the campaign's descr_strat.txt, or Nones."""
    from . import campstrat
    try:
        s = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError):
        return {"start": None, "end": None, "timescale": None}
    g = s.globals or {}
    try:
        ts = float(str(g.get("timescale") or "").split()[0])
    except (ValueError, IndexError):
        ts = None
    return {"start": _year(g.get("start_date")), "end": _year(g.get("end_date")),
            "timescale": ts}


def event_sources(mod, campaign: str) -> Dict[str, Dict]:
    """``{event lower: {name, how, where}}`` - what can ever fire a named event.

    Two sources, both in the campaign's own folder: an ``event`` block in
    descr_events.txt (``how: "events"``), and a ``set_event_counter`` /
    ``historic_event`` line in a script there (``how: "script"``, with the file
    and line). DaC's ``ND_BOH`` is the second kind - its descr_events.txt never
    mentions it and its campaign script sets it four times.
    """
    from . import campevents, campstrat
    out: Dict[str, Dict] = {}
    try:
        bf, _ = campevents.read_events(mod, campaign)
        for b in bf.blocks:
            if b.name:
                out.setdefault(b.name.lower(), {
                    "name": b.name, "how": "events",
                    "where": f"{campevents.EVENTS_NAME} line {b.head_line + 1}"})
    except (campevents.CampEventError, OSError, ValueError, AttributeError):
        pass
    folder = (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
              / campstrat.campaign_rel(campaign))
    try:
        scripts = sorted(p for p in folder.glob("*.txt")
                         if "script" in p.name.lower() and p.is_file())
    except OSError:
        scripts = []
    for path in scripts:
        try:
            text = kb.read_text(path, ENCODING)
        except OSError:
            continue
        # a running count: DaC's script is 10 MB and recounting from the top
        # for every match was four seconds
        line, at = 1, 0
        for m in _SET_EVENT.finditer(text):
            line += text.count(chr(10), at, m.start())
            at = m.start()
            name = m.group(1)
            out.setdefault(name.lower(), {
                "name": name, "how": "script", "where": f"{path.name} line {line}"})
    return out


def faction_rows(mod, campaign: str) -> List[Dict]:
    """Every faction the campaign places, with its religion and shown name."""
    from . import campstrat, factions as facfile
    try:
        rosters = campstrat.read_strat(mod, campaign).rosters
    except (OSError, ValueError):
        rosters = {}
    religion: Dict[str, str] = {}
    try:
        rf = facfile.parse_file(facfile.path_for(mod))
        # `faction egypt, spawned_on_event` - the name is the word before the comma
        religion = {r.name.split(",")[0].strip(): r.get("religion").strip(",")
                    for r in rf.records}
    except (OSError, ValueError, AttributeError):
        pass
    try:
        names = facfile.loc(mod)
    except (OSError, ValueError):
        names = {}
    out = []
    for status in ("playable", "unlockable", "nonplayable"):
        for name in rosters.get(status, []):
            out.append({"name": name, "status": status,
                        "religion": religion.get(name, ""),
                        "label": facfile.label(name, names)})
    if not out:
        out = [{"name": n, "status": "", "religion": r,
                "label": facfile.label(n, names)} for n, r in religion.items()]
    return out


def gates(u: MercUnit, faction: Optional[Dict], years: Dict,
          events: Dict[str, Dict], edu_types: Optional[set]) -> Tuple[str, List[Dict]]:
    """``(verdict, [gate])`` for one unit line and, optionally, one faction.

    The verdict is ``no`` if any gate is ``no``; else ``later`` if any gate
    waits on something; else ``unknown`` if an event cannot be traced; else
    ``yes``. With no faction picked the two faction gates are ``info`` and do
    not decide it, so the verdict is what is true for everybody.
    """
    out: List[Dict] = []

    def add(gate: str, state: str, say: str) -> None:
        out.append({"gate": gate, "state": state, "say": say})

    if edu_types is not None:
        if u.name in edu_types:
            add("unit", "ok", "a unit type in this mod's EDU")
        else:
            add("unit", "no", f"no unit called `{u.name}` in this mod's EDU, so "
                              "the engine has nothing to raise")
    rel = faction.get("religion") if faction else ""
    if u.religions is not None:
        if not u.religions:
            add("religions", "ok", "an empty list - every religion")
        elif faction is None:
            add("religions", "info", "only to a faction of " + ", ".join(u.religions))
        elif rel in u.religions:
            add("religions", "ok", f"{faction['name']} is {rel}")
        else:
            add("religions", "no", f"{faction['name']} is {rel or 'of no religion'}, "
                                   "and the line sells to " + ", ".join(u.religions))
    if u.factions is not None:
        named = [f.lower() for f in u.factions]
        if faction is None:
            add("factions", "info", "only to " + ", ".join(u.factions))
        elif "all" in named or faction["name"].lower() in named:
            add("factions", "ok", f"names {faction['name']}")
        else:
            add("factions", "no", "names only " + ", ".join(u.factions))
    if u.crusading:
        add("crusading", "later", "only to an army on a crusade or a jihad")
    for ev in u.events or []:
        src = events.get(ev.lower())
        if src is None:
            add("events", "unknown", f"after `{ev}`, which nothing in this campaign's "
                                     "descr_events.txt or scripts sets - a script "
                                     "elsewhere may")
        else:
            add("events", "later", f"after `{ev}` ({src['where']})")
    start, end = years.get("start"), years.get("end")
    if u.start_year:
        if end is not None and u.start_year > end:
            add("start_year", "no", f"from {u.start_year}, after the campaign ends "
                                    f"in {end}")
        elif start is not None and u.start_year > start:
            add("start_year", "later", f"from {u.start_year}; the campaign starts "
                                       f"in {start}")
        else:
            add("start_year", "ok", f"from {u.start_year}")
    if u.end_year:
        if start is not None and u.end_year < start:
            add("end_year", "no", f"until {u.end_year}, before the campaign starts "
                                  f"in {start}")
        elif end is not None and u.end_year < end:
            add("end_year", "later", f"only until {u.end_year}")
        else:
            add("end_year", "ok", f"until {u.end_year}")
    states = {g["state"] for g in out}
    verdict = ("no" if "no" in states else "later" if "later" in states
               else "unknown" if "unknown" in states else "yes")
    return verdict, out


def hire_view(mod, campaign: str, faction: str = "") -> Dict:
    """Both directions at once, for one campaign and, optionally, one faction.

    ``pools`` is the province direction - the page knows which pool a province
    is in from ``regions`` - and ``units`` the mercenary direction: every pool
    that sells a unit, its price and pool size there, and the provinces.
    """
    mf, _ = read(mod, campaign)
    years = campaign_years(mod, campaign)
    events = event_sources(mod, campaign)
    facs = faction_rows(mod, campaign)
    picked = next((f for f in facs if f["name"] == faction), None) if faction else None
    try:
        edu_types: Optional[set] = {x.type for x in mod.edu.units}
    except (OSError, AttributeError, ValueError):
        edu_types = None
    pools, index = [], {}
    for p in mf.pools:
        rows = []
        for i, u in enumerate(p.units):
            verdict, gs = gates(u, picked, years, events, edu_types)
            rows.append(dict(u.payload(), index=i, hire=verdict, gates=gs))
            entry = index.setdefault(u.name, {
                "name": u.name,
                "known": None if edu_types is None else u.name in edu_types,
                "offers": [], "provinces": 0})
            entry["offers"].append({"pool": p.name, "index": i, "cost": u.cost,
                                    "max": u.max, "initial": u.initial,
                                    "replenish": list(u.replenish or ()),
                                    "hire": verdict, "regions": list(p.regions)})
            entry["provinces"] += len(p.regions)
        pools.append({"name": p.name, "line": p.line + 1,
                      "regions": list(p.regions), "units": rows})
    units = sorted(index.values(), key=lambda e: e["name"].lower())
    for e in units:
        e["prices"] = sorted({o["cost"] for o in e["offers"] if o["cost"] is not None})
    where: Dict[str, List[str]] = {}
    for p in mf.pools:
        for r in p.regions:
            where.setdefault(r.lower(), []).append(p.name)
    return {
        "campaign": campaign, "file": MERCS_NAME, "faction": picked,
        "factions": facs, "years": years, "pools": pools, "units": units,
        "in_two": {k: v for k, v in where.items() if len(v) > 1},
        "unknown_units": [e["name"] for e in units if e["known"] is False],
        # what the add box offers: the names the unit gate will accept
        "edu_types": sorted(edu_types, key=str.lower) if edu_types else [],
        "counts": {"pools": len(mf.pools), "units": len(units),
                   "lines": sum(len(p.units) for p in mf.pools),
                   "regions": len(where)},
        "warnings": list(mf.warnings),
    }
