"""The six export sound banks beside the unit voice bank (Phase 47a).

``data/export_descr_sounds_*.txt`` is seven files. One of them,
``_units_voice``, is :mod:`unittransfer.sounds` and keys on units. The other six
are the same indented tree of header lines over ``event`` … ``end`` blocks, and
nothing here opened them:

=====================  =================================================  ======
file                   headers, outermost first                           DaC
=====================  =================================================  ======
``_soldier_voice``     ``accent`` > ``class`` > ``vocal``                 16,144
``_stratmap_voice``    ``accent`` > ``type`` > ``vocal``                  16,155
``_units_battle_…``    ``accent`` > ``notification``                       7,328
``_prebattle``         ``accent`` > ``element`` > a selector               8,400
``_advice``            ``text``                                            3,980
``_narration``         none: ``event <NAME>`` at the top                       3
=====================  =================================================  ======

Measured on both installed mods, 2026-09-21, and three things in that table
are why this is its own parser rather than :func:`sounds.parse_text` with more
keywords:

- **Indentation says nothing.** ``_prebattle`` mixes tabs and runs of spaces in
  one block, and a ``pri 9`` line sits deeper than the ``VnV`` it belongs to. So
  a header's depth comes from its KEYWORD, per file, never from its indent.
- **``VnV`` is not a level.** In ``_prebattle`` it is a line of its own that
  qualifies the ``trait`` or ``pri`` line under it (``VnV`` / ``trait Anger``),
  so it is carried as the first line of the block it qualifies.
- **An ``event`` line has attributes** in two files (``mindist 0.75 priority 120
  volume -10 probability .4`` in ``_soldier_voice``, ``delay 0 pref SFX`` in
  ``_stratmap_voice``), and in ``_narration`` what follows ``event`` is the
  event's NAME. A sample line can carry them too (``willhelm.wav probability
  .001``), so a body line is kept as text, not split into a path.

Everything is a splice, as in :mod:`sounds`: the file is its verbatim lines, a
block is a line range, and nothing outside the range an edit names is
rewritten, so ``parse_text(t).to_text() == t`` for every file on every mod.
"""
from __future__ import annotations

import difflib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import config, keyblock as kb
from .logutil import file_op, log

ENCODING = "latin-1"

#: id -> the file, what it is, and its header keywords by depth. A keyword not
#: in its file's list is kept verbatim and reported, never guessed at.
FILES: Dict[str, dict] = {
    "soldier_voice": {
        "rel": "export_descr_sounds_soldier_voice.txt",
        "label": "Soldier voices",
        "about": "What soldiers grunt, scream and shout in battle, per accent "
                 "and voice class. The unit's EDU accent and voice_type pick "
                 "the block.",
        "levels": [["accent"], ["class"], ["vocal"]],
    },
    "stratmap_voice": {
        "rel": "export_descr_sounds_stratmap_voice.txt",
        "label": "Strat map voices",
        "about": "What a general, admiral or agent says on the campaign map "
                 "when it is selected, moved or sent to do something.",
        "levels": [["accent"], ["type"], ["vocal"]],
    },
    "battle_events": {
        "rel": "export_descr_sounds_units_battle_events.txt",
        "label": "Battle events",
        "about": "The announcer's lines in battle: an allied general killed, "
                 "the enemy routing. The number after a notification is which "
                 "of its variants this is.",
        "levels": [["accent"], ["notification"]],
    },
    "prebattle": {
        "rel": "export_descr_sounds_prebattle.txt",
        "label": "Pre-battle speech",
        "about": "The general's speech before a battle, built from elements. "
                 "An element's lines are picked by the enemy faction, a trait, "
                 "the ground or the situation. VnV marks a line chosen by the "
                 "general's traits (vices and virtues).",
        "levels": [["accent"], ["element"],
                   ["relationship", "trait", "condition", "situation", "pri"]],
        "prefix": ["vnv"],
    },
    "advice": {
        "rel": "export_descr_sounds_advice.txt",
        "label": "Advice",
        "about": "The advisor's spoken lines, one per advice text key.",
        "levels": [["text"]],
    },
    "narration": {
        "rel": "export_descr_sounds_narration.txt",
        "label": "Narration",
        "about": "Named narration events, spoken by a script or a historic "
                 "battle. The name after event is what the script plays.",
        "levels": [],
        "named": True,
    },
}

#: Where the samples are. The sound files a bank names are not loose files in
#: most installs: M2TW ships them packed, so a name cannot be checked here.
PACKED_NOTE = ("Sample names point into the game's packed sounds "
               "(data/sounds/*.idx and *.dat) unless the mod ships the file "
               "loose, so the toolkit does not check that a name exists.")

NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class SoundBankError(ValueError):
    pass


@dataclass
class Event:
    at: int                        # index of the `event` line
    end: int                       # exclusive: one past the `end` line
    attrs: str                     # what follows `event`, stripped
    body: List[int] = field(default_factory=list)   # indices of folder/sample lines

    def lines(self, src: List[str]) -> List[str]:
        return [src[i].strip() for i in self.body]


@dataclass
class Node:
    kw: str                        # the keyword as written (`accent`, `vocal`, `event`)
    value: str
    depth: int
    head: int                      # index of the keyword line
    start: int                     # == head, or the `VnV` line above it
    end: int                       # exclusive, trailing blanks/comments left out
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)

    @property
    def label(self) -> str:
        return (f"{self.kw} {self.value}".strip() if self.start == self.head
                else f"VnV {self.kw} {self.value}".strip())

    def path(self) -> List[str]:
        out, n = [], self
        while n is not None:
            out.append(n.label)
            n = n.parent
        return out[::-1]


@dataclass
class Bank:
    file: str
    lines: List[str]
    bank: str = ""                 # the name after `BANK:`
    nodes: List[Node] = field(default_factory=list)   # every node, file order
    roots: List[Node] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        return "".join(self.lines)

    def node_at(self, head: int) -> Optional[Node]:
        for n in self.nodes:
            if n.head == head:
                return n
        return None

    def event_at(self, at: int) -> Optional[Event]:
        for e in self.events:
            if e.at == at:
                return e
        return None


def _is_end(low: str) -> bool:
    # sounds.py tolerates `endd`; the same typo would sink this parser too
    return low == "end" or (low.startswith("end") and low.rstrip("d") == "en")


def parse_text(file: str, text: str) -> Bank:
    spec = FILES[file]
    levels = {k: d for d, ks in enumerate(spec["levels"]) for k in ks}
    prefix = set(spec.get("prefix", ()))
    named = bool(spec.get("named"))
    lines = text.splitlines(keepends=True)
    b = Bank(file=file, lines=lines)
    stack: List[Node] = []
    pending: Optional[int] = None          # a `VnV` line waiting for its header
    ev: Optional[Event] = None

    def trimmed(node: Node, at: int) -> int:
        cut = at
        floor = max([node.head + 1] + [e.end for e in node.events]
                    + [c.end for c in node.children])
        while cut > floor:
            s = lines[cut - 1].strip()
            if s and not s.startswith(";"):
                break
            cut -= 1
        return cut

    def close_to(depth: int, at: int) -> None:
        while stack and stack[-1].depth >= depth:
            n = stack.pop()
            n.end = trimmed(n, at)

    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        low = s.lower()
        if ev is not None:
            if _is_end(low):
                ev.end = i + 1
                if low != "end":
                    b.warnings.append(f"line {i + 1}: read {s!r} as 'end'")
                ev = None
            else:
                ev.body.append(i)
            continue
        word = s.split(None, 1)
        key = word[0].lower()
        rest = word[1].strip() if len(word) > 1 else ""
        if key == "bank:":
            b.bank = rest
            continue
        if key == "event":
            ev = Event(at=i, end=len(lines), attrs=rest)
            b.events.append(ev)
            if pending is not None:
                b.warnings.append(f"line {pending + 1}: a VnV line with no "
                                  f"header under it")
                pending = None
            if named and not stack:
                n = Node(kw=word[0], value=rest, depth=0, head=i, start=i,
                         end=len(lines))
                n.events.append(ev)
                b.nodes.append(n)
                b.roots.append(n)
            elif stack:
                stack[-1].events.append(ev)
            else:
                b.warnings.append(f"line {i + 1}: an event with no header above it")
            continue
        if _is_end(low):
            b.warnings.append(f"line {i + 1}: 'end' with no open 'event'")
            continue
        if key in prefix:
            pending = i
            continue
        depth = levels.get(key)
        if depth is None:
            b.warnings.append(f"line {i + 1}: {word[0]!r} is not a header this "
                              f"file uses; kept as it is")
            continue
        # a VnV line waiting above this header is this block's, not the tail
        # of the one before it
        close_to(depth, pending if pending is not None else i)
        n = Node(kw=word[0], value=rest, depth=depth, head=i,
                 start=pending if pending is not None else i, end=len(lines))
        pending = None
        if stack:
            n.parent = stack[-1]
            stack[-1].children.append(n)
        else:
            b.roots.append(n)
        b.nodes.append(n)
        stack.append(n)
    if named:
        # a named event node ends where its event does, so the next one's
        # header is not swallowed; they never nest
        for n in b.nodes:
            n.end = n.events[0].end if n.events else n.head + 1
    close_to(-1, len(lines))
    return b


def rel_of(file: str) -> str:
    if file not in FILES:
        raise SoundBankError(f"no sound bank called {file!r}")
    return FILES[file]["rel"]


def path_of(mod, file: str) -> Path:
    return Path(mod.data) / rel_of(file)


def read(mod, file: str) -> Bank:
    p = path_of(mod, file)
    if not p.exists():
        return Bank(file=file, lines=[])
    return parse_text(file, kb.read_text(p, ENCODING))


# ---------------------------------------------------------------------------
# edits: every one a splice against the running text


def _eol(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


_REST = re.compile(r"^(\s*\S+)(\s*)([^;]*?)(\s*)(;.*)?$")


def _with_value(line: str, value: str) -> str:
    """The keyword line with its value replaced; indent, keyword and EOL kept.

    47b: and a trailing ``; comment`` kept, with the space before it -
    ``river_max_dist_apart 250	; maximum distance ...`` in the sound scripts.
    """
    eol = _eol(line)
    m = _REST.match(line[:len(line) - len(eol)])
    head, gap, _old, pad, comment = m.groups()
    if not value:
        return f"{head}{pad if comment else ''}{comment or ''}{eol}"
    return f"{head}{gap or ' '}{value}{pad or (' ' if comment else '')}{comment or ''}{eol}"


def edit_event(b: Bank, at: int, attrs: str, body: List[str]) -> str:
    """One event's attributes and its folder and sample lines, re-spliced.

    Lines that did not change keep their bytes; a new folder line takes the
    indent of the event's first folder line and a new sample the indent of its
    first sample, so a block keeps whatever mix of tabs and spaces it had.
    """
    e = b.event_at(at)
    if e is None:
        raise SoundBankError(f"line {at + 1} is not an event")
    src = b.lines
    old_head = src[at]
    if attrs.strip() != e.attrs:
        head = _with_value(old_head, attrs.strip())
    else:
        head = old_head
    eol = _eol(old_head) or "\r\n"
    old = [src[i] for i in e.body]
    old_s = [x.strip() for x in old]
    new_s = [x.strip() for x in body if x.strip()]

    def ind_for(kind_folder: bool) -> str:
        for x in old:
            if x.strip().lower().startswith("folder ") == kind_folder:
                return _indent(x)
        return _indent(old[0]) if old else _indent(old_head) + "\t"

    out: List[str] = []
    sm = difflib.SequenceMatcher(a=old_s, b=new_s, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += old[i1:i2]
        else:
            for x in new_s[j1:j2]:
                out.append(ind_for(x.lower().startswith("folder ")) + x + eol)
    first, last = e.body[0] if e.body else at + 1, (e.body[-1] + 1) if e.body else at + 1
    # body lines are contiguous except for blanks and comments between them,
    # which a rewrite keeps where the first changed line was
    between = [src[i] for i in range(first, last) if i not in set(e.body)]
    if out == old:
        new_body = src[first:last]
    else:
        new_body = between + out
    return "".join(src[:at] + [head] + src[at + 1:first] + new_body + src[last:])


def _siblings(b: Bank, n: Node) -> List[Node]:
    return n.parent.children if n.parent is not None else b.roots


def duplicate(b: Bank, head: int, value: str) -> str:
    """A copy of one block, straight after it, under a new value."""
    n = b.node_at(head)
    if n is None:
        raise SoundBankError(f"line {head + 1} is not a header")
    block = b.lines[n.start:n.end]
    k = n.head - n.start
    block[k] = _with_value(block[k], value)
    before = b.lines[:n.end]
    if before and not _eol(before[-1]):
        # the file's last line had no newline: it gets one, and the copy ends
        # without, so the file still does
        before = before[:-1] + [before[-1] + (_eol(b.lines[n.head]) or "\r\n")]
    return "".join(before + block + b.lines[n.end:])


def rename(b: Bank, head: int, value: str) -> str:
    n = b.node_at(head)
    if n is None:
        raise SoundBankError(f"line {head + 1} is not a header")
    lines = list(b.lines)
    lines[head] = _with_value(lines[head], value)
    return "".join(lines)


def remove(b: Bank, head: int) -> str:
    n = b.node_at(head)
    if n is None:
        raise SoundBankError(f"line {head + 1} is not a header")
    return "".join(b.lines[:n.start] + b.lines[n.end:])


# ---------------------------------------------------------------------------
# plan / apply


@dataclass
class SoundBankPlan:
    mod: object
    file: str
    text: str = ""                 # "" = unchanged
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        out = [f"{FILES[self.file]['label']} in {getattr(self.mod, 'name', '?')}"]
        out += ["  " + c for c in self.changes]
        out += ["  ! " + w for w in self.warnings]
        out += ["  ERROR: " + e for e in self.errors]
        return "\n".join(out)

    def payload(self) -> dict:
        return {"ok": not self.errors and bool(self.text), "file": self.file,
                "changes": self.changes, "warnings": self.warnings,
                "errors": self.errors, "summary": self.summary()}


def _value_problem(file: str, n: Node, value: str) -> str:
    if not value:
        return "a name is needed"
    if n.kw.lower() == "event" and not NAME_RE.match(value):
        return (f"{value!r}: an event name is letters, digits and underscores, "
                f"because a script plays it by that name")
    if "\n" in value or ";" in value:
        return f"{value!r}: one line, and no ';' (that starts a comment)"
    return ""


def _check_event(p: SoundBankPlan, where: str, attrs: str, body: List[str],
                 named: bool, known: set) -> None:
    lines = [x.strip() for x in body if x.strip()]
    if any(x.lower() == "end" or x.lower().startswith("event") for x in lines):
        p.errors.append(f"{where}: a line of 'end' or 'event' inside an event "
                        f"would close it early")
        return
    if not lines:
        p.errors.append(f"{where}: an event needs at least a folder and one sample")
        return
    if not lines[0].lower().startswith("folder "):
        p.errors.append(f"{where}: the first line has to be a folder, or the "
                        f"engine does not know where the first sample is")
    if all(x.lower().startswith("folder ") for x in lines):
        p.warnings.append(f"{where}: no samples, so the event plays nothing")
    if named:
        if not NAME_RE.match(attrs.strip()):
            p.errors.append(f"{where}: an event name is letters, digits and "
                            f"underscores")
        return
    toks = attrs.split()
    keys = toks[0::2]
    if len(toks) % 2:
        p.warnings.append(f"{where}: event attributes come in pairs "
                          f"(priority 120 volume -10); {attrs!r} has an odd one")
    odd = [k for k in keys if k.lower() not in known]
    if odd:
        p.warnings.append(f"{where}: {kb.and_list(odd)} "
                          f"{'is' if len(odd) == 1 else 'are'} not used by any "
                          f"event in this mod's sound banks")


def _known_attrs(mod) -> set:
    out = set()
    for f, spec in FILES.items():
        if spec.get("named"):
            continue
        b = read(mod, f)
        for e in b.events:
            out.update(t.lower() for t in e.attrs.split()[0::2])
    return out


def plan(mod, body: dict) -> SoundBankPlan:
    """``{file, ops: [{op, at, head, ...}]}`` against the file as it is now.

    Each op names a line by index AND by its text, and is refused if the two no
    longer agree, so a save planned against a file that changed since it was
    read cannot land on the wrong block. Ops run from the bottom of the file
    up: a splice moves only the lines after it, so the lines of every op still
    to run stay where they were read.
    """
    file = str(body.get("file") or "")
    if file not in FILES:
        p = SoundBankPlan(mod=mod, file=next(iter(FILES)))
        p.errors.append(f"no sound bank called {file!r}")
        return p
    p = SoundBankPlan(mod=mod, file=file)
    path = path_of(mod, file)
    if not path.exists():
        p.errors.append(f"{getattr(mod, 'name', '?')} has no data/{rel_of(file)}")
        return p
    original = kb.read_text(path, ENCODING)
    text = original
    named = bool(FILES[file].get("named"))
    known = None
    ops = [o for o in (body.get("ops") or []) if isinstance(o, dict)]
    ops.sort(key=lambda o: -int(o.get("at", -1)))
    for o in ops:
        kind = str(o.get("op") or "")
        at = int(o.get("at", -1))
        want = str(o.get("head") or "").strip()
        b = parse_text(file, text)
        if not 0 <= at < len(b.lines) or b.lines[at].strip() != want:
            p.errors.append(f"line {at + 1}: the file changed since it was read "
                            f"(expected {want!r}); reload and try again")
            continue
        try:
            if kind == "event":
                e = b.event_at(at)
                n = next((x for x in b.nodes if e in x.events), None)
                where = " / ".join(n.path()) if n else f"line {at + 1}"
                if known is None:
                    known = _known_attrs(mod)
                attrs = str(o.get("attrs") or "")
                lines = [str(x) for x in (o.get("lines") or [])]
                _check_event(p, where, attrs, lines, named, known)
                if p.errors:
                    continue
                new = edit_event(b, at, attrs, lines)
                if new != text:
                    old_n = len(e.body)
                    new_n = len([x for x in lines if x.strip()])
                    what = []
                    if attrs.strip() != e.attrs:
                        what.append(f"{'name' if named else 'attributes'} "
                                    f"{e.attrs or '(none)'} -> {attrs.strip() or '(none)'}")
                    if [x.strip() for x in lines if x.strip()] != e.lines(b.lines):
                        what.append(f"{old_n} line(s) -> {new_n}")
                    p.changes.append(f"{where}: " + ", ".join(what))
                    text = new
                continue
            n = b.node_at(at)
            if n is None:
                p.errors.append(f"line {at + 1} is not a header")
                continue
            where = " / ".join(n.path())
            if kind == "remove":
                text = remove(b, at)
                p.changes.append(f"{where}: removed "
                                 f"({n.end - n.start} lines)")
                if n.depth == 0 and file != "narration":
                    p.warnings.append(
                        f"{where}: every unit or character with this "
                        f"{n.kw} loses these sounds, and the game does not "
                        f"say so")
                continue
            value = " ".join(str(o.get("value") or "").split())
            bad = _value_problem(file, n, value)
            if bad:
                p.errors.append(f"{where}: {bad}")
                continue
            if kind == "duplicate" and value == n.value:
                p.errors.append(f"{where}: a copy needs a name of its own")
                continue
            if any(s is not n and s.kw.lower() == n.kw.lower() and s.value == value
                   and (s.start == s.head) == (n.start == n.head)
                   for s in _siblings(b, n)):
                p.errors.append(f"{where}: there is already a {n.kw} {value} "
                                f"beside it, and the game reads the first one")
                continue
            if kind == "duplicate":
                text = duplicate(b, at, value)
                p.changes.append(f"{n.kw} {value}: a copy of {where} "
                                 f"({n.end - n.start} lines)")
                if n.kw.lower() == "accent":
                    p.warnings.append(
                        f"nothing speaks with accent {value} until something "
                        f"names it (a unit's EDU accent, for one); this save "
                        f"does not point anything at it")
            elif kind == "rename":
                if value == n.value:
                    continue
                text = rename(b, at, value)
                p.changes.append(f"{where}: renamed to {n.kw} {value}")
                if n.depth == 0 or named:
                    p.warnings.append(
                        f"whatever named {n.kw} {n.value} still does, and "
                        f"finds nothing now")
            else:
                p.errors.append(f"unknown operation {kind!r}")
        except SoundBankError as exc:
            p.errors.append(str(exc))
    if p.errors:
        return p
    if parse_text(file, text).to_text() != text:
        p.errors.append("the result does not read back the same; nothing written")
        return p
    p.text = "" if text == original else text
    return p


def apply(p: SoundBankPlan) -> Dict:
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    rel = rel_of(p.file)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    target = path_of(mod, p.file)
    bpath = backup_root / "data" / rel
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    manifest["backed_up"].append(rel)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} chars")
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "soundbanks",
        "action": p.file,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": FILES[p.file]["label"],
        "resolved_type": FILES[p.file]["label"],
        "options": {"file": p.file},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SOUNDBANK %s in %s - %d change(s), id=%s", p.file, mod.name,
             len(p.changes), tid)
    return rec


# ---------------------------------------------------------------------------
# payload


def files(mod) -> List[dict]:
    out = []
    for f, spec in FILES.items():
        p = path_of(mod, f)
        out.append({"id": f, "label": spec["label"], "rel": spec["rel"],
                    "exists": p.exists()})
    return out


def overview(mod, file: str) -> dict:
    """One bank for the screen: its blocks in file order, events inline."""
    if file not in FILES:
        raise SoundBankError(f"no sound bank called {file!r}")
    spec = FILES[file]
    b = read(mod, file)
    index = {id(n): k for k, n in enumerate(b.nodes)}
    nodes = []
    for n in b.nodes:
        nodes.append({
            "kw": n.kw, "value": n.value, "label": n.label, "depth": n.depth,
            "head": n.head, "line": n.head + 1, "head_text": b.lines[n.head].strip(),
            "vnv": n.start != n.head,
            "parent": index[id(n.parent)] if n.parent is not None else None,
            "lines": n.end - n.start,
            "events": [{"at": e.at, "line": e.at + 1, "attrs": e.attrs,
                        "head_text": b.lines[e.at].strip(),
                        "lines": e.lines(b.lines)} for e in n.events],
        })
    return {
        "mod": mod.name, "file": file, "label": spec["label"],
        "rel": spec["rel"], "about": spec["about"],
        "exists": path_of(mod, file).exists(),
        "bank": b.bank, "named": bool(spec.get("named")),
        "levels": spec["levels"], "nodes": nodes,
        "events": len(b.events), "line_count": len(b.lines),
        "warnings": b.warnings[:30], "packed": PACKED_NOTE,
        "files": files(mod),
    }
