"""The sound scripts: ``data/descr_sounds_*.txt`` (Phase 47b).

Thirty-one files in ``data/`` on both installed mods, and
``world/maps/base/descr_sounds_music_types.txt`` beside them. They decide how
every sound the game plays is played - a sword on flesh, a footstep in mud, the
music of a province, a click on a button - and nothing here opened them.

They are not the export banks of :mod:`unittransfer.soundbanks`. Measured on both
installed mods, 2026-09-21 (52,091 lines, 4,239 events, 980 of them named), a
script is five kinds of line:

``DEFAULT: 3d mindist 8 volume 0 ...``
    the attributes every event after it starts from, until the next one.
``BANK: weapon_hit``
    the start of a section the engine asks for by name.
``source export_descr_sounds_units_voice.txt``
    the export bank that fills this section (the six of 47a, and the voice bank).
``grid_cell_size 40``, ``river_max_dist_apart 250 ; comment``
    a setting: a key and numbers.
``unit Ents:sec, Harad Mumakil:sec``, ``hit building, flesh``, ``season summer``,
``terrain mud, swamp``, ``looped``, ``arrived``
    a **selector**: the events under it play when its condition holds. About
    forty keywords, and a bank nests them as deep as five.

and ``event [NAME] attrs`` … ``end`` blocks, a folder line and samples inside,
as in the banks. An event at the top of a file has a NAME the engine plays it by
(``event Rocket_Launcher_Fire mindist 15 priority 240 ...``); under a selector it
has none.

**What is read, and how far it is trusted.** Every line is kept verbatim and
every edit is a splice, so ``parse_text(t).to_text() == t``. Selectors nest by
indentation, and indentation here is a habit rather than a rule - ``looped``
sits a tab shallower than the event it wraps - so the tree built from it is for
showing where an event is, never for cutting. That is why a selector's extent is
never copied or removed: the edits are all to lines whose extent is certain
(one line, or ``event`` to ``end``).

**The arguments are typed off the files, not off a guess.** An attribute is a
number key (``volume -10``), a flag (``3d``, ``streamed``, ``looped``,
``ducking``) or ``pref`` and a word, and :data:`NUM_KEYS` and :data:`FLAGS` are
every one the two mods write. A selector's values are checked against every
value that keyword takes anywhere in the mod's scripts, and ``factions`` in
``descr_sounds_accents.txt`` against the mod's factions.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import config, keyblock as kb, soundbanks as sb
from .logutil import file_op, log

ENCODING = "latin-1"
MUSIC_TYPES_REL = "world/maps/base/descr_sounds_music_types.txt"

#: every attribute key the scripts write with a number after it, measured
NUM_KEYS = frozenset("""volume mindist maxdist lod priority probability minpitch
    maxpitch distancepriority fadeout fadein randomdelay probradius rndvolume
    delay effect_level dry_level wet_level pan ignore_pause""".split())
#: and every one written on its own
FLAGS = frozenset("1d 2d 3d streamed looped ducking".split())
#: the one key that takes a word
WORD_KEYS = frozenset(["pref"])

NUM = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")

#: the files a screen groups them under, by the name after descr_sounds_
GROUPS = [
    ("Battle", ["units", "units_ambient", "units_anims", "units_celebrate",
                "units_charge", "units_collide", "units_confirm", "units_fight",
                "units_fire", "units_idle", "units_march", "units_reform",
                "units_retreat", "units_run", "units_taunt", "units_voice",
                "weapons", "engine", "battle_events", "prebattle"]),
    ("Campaign map", ["stratmap", "stratmap_voice", "events", "structures"]),
    ("Music", ["music", "music_types"]),
    ("Everything else", ["accents", "advice", "narration", "enviro", "generic",
                         "interface"]),
]


class ScriptError(ValueError):
    pass


def _code(line: str) -> str:
    """The line without its comment, stripped."""
    return line.split(";", 1)[0].strip()


@dataclass
class Event:
    at: int
    end: int
    attrs: str                 # everything after `event`, comment left out
    name: str = ""
    body: List[int] = field(default_factory=list)

    def lines(self, src: List[str]) -> List[str]:
        return [src[i].strip() for i in self.body]


@dataclass
class Item:
    """A one-line thing a block holds: a DEFAULT:, a setting or a source."""
    at: int
    kind: str                  # default | setting | source | bank
    key: str
    value: str


@dataclass
class Node:
    kw: str
    value: str
    head: int
    depth: int
    indent: int = 0
    kind: str = "selector"     # file | bank | selector | named
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.kind == "file":
            return "File settings"
        if self.kind == "bank":
            return f"BANK: {self.value}"
        if self.kind == "named":
            return f"event {self.value}"
        return f"{self.kw} {self.value}".strip()

    def path(self) -> List[str]:
        out, n = [], self
        while n is not None and n.kind != "file":
            out.append(n.label)
            n = n.parent
        return out[::-1]


@dataclass
class Script:
    rel: str
    lines: List[str]
    root: Node = None
    nodes: List[Node] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        return "".join(self.lines)

    def event_at(self, at: int) -> Optional[Event]:
        for e in self.events:
            if e.at == at:
                return e
        return None

    def node_at(self, head: int) -> Optional[Node]:
        for n in self.nodes:
            if n.head == head and n.kind != "file":
                return n
        return None

    def item_at(self, at: int) -> Optional[Item]:
        for n in self.nodes:
            for it in n.items:
                if it.at == at:
                    return it
        return None

    def named(self) -> Dict[str, Event]:
        return {e.name: e for e in self.events if e.name}


def _event_name(rest: str) -> str:
    first = rest.split()[0] if rest.split() else ""
    low = first.lower()
    if not first or NUM.match(first) or low in NUM_KEYS or low in FLAGS or low in WORD_KEYS:
        return ""
    return first


def _width(line: str) -> int:
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())


def parse_text(rel: str, text: str) -> Script:
    lines = text.splitlines(keepends=True)
    sc = Script(rel=rel, lines=lines)
    root = Node(kw="", value="", head=-1, depth=0, kind="file")
    sc.root = root
    sc.nodes.append(root)
    bank: Optional[Node] = None
    stack: List[Node] = []
    ev: Optional[Event] = None

    def holder() -> Node:
        return stack[-1] if stack else bank or root

    for i, raw in enumerate(lines):
        s = _code(raw)
        if not s:
            continue
        low = s.lower()
        if ev is not None:
            if sb._is_end(low):
                ev.end = i + 1
                if low != "end":
                    sc.warnings.append(f"line {i + 1}: read {s!r} as 'end'")
                ev = None
            else:
                ev.body.append(i)
            continue
        words = s.split()
        key, rest = words[0], s[len(words[0]):].strip()
        lk = key.lower()
        if lk == "event":
            ev = Event(at=i, end=len(lines), attrs=rest, name=_event_name(rest))
            sc.events.append(ev)
            if ev.name and not stack:
                parent = bank or root
                n = Node(kw="event", value=ev.name, head=i,
                         depth=parent.depth + (0 if parent is root else 1),
                         kind="named", parent=parent if parent is not root else None)
                n.events.append(ev)
                (parent.children if parent is not root else []).append(n)
                sc.nodes.append(n)
            else:
                holder().events.append(ev)
            continue
        if sb._is_end(low):
            sc.warnings.append(f"line {i + 1}: 'end' with no open 'event'")
            continue
        if lk == "default:":
            # a DEFAULT: starts a new stretch of the file; it is the file's
            stack, bank = [], None
            root.items.append(Item(at=i, kind="default", key="DEFAULT:", value=rest))
            continue
        if lk == "bank:":
            stack = []
            bank = Node(kw="BANK:", value=rest, head=i, depth=0, kind="bank")
            sc.nodes.append(bank)
            continue
        if lk == "source":
            root.items.append(Item(at=i, kind="source", key=key, value=rest))
            continue
        if len(words) > 1 and all(NUM.match(w) for w in words[1:]):
            # a setting belongs to the deepest selector that sits left of it;
            # it closes nothing, so it does not touch the stack
            w = _width(raw)
            host = next((n for n in reversed(stack) if n.indent < w), None)
            (host or bank or root).items.append(
                Item(at=i, kind="setting", key=key, value=rest))
            continue
        # a selector: nests under the last one that sits deeper-left than it
        w = _width(raw)
        while stack and stack[-1].indent >= w:
            stack.pop()
        parent = stack[-1] if stack else bank
        n = Node(kw=key, value=rest, head=i, indent=w,
                 depth=(parent.depth + 1) if parent is not None else 0,
                 parent=parent)
        if parent is not None:
            parent.children.append(n)
        sc.nodes.append(n)
        stack.append(n)
    return sc


# ---------------------------------------------------------------------------
# which files a mod has


def files(mod) -> List[dict]:
    data = Path(mod.data)
    have = sorted(p.name[len("descr_sounds_"):-4] for p in data.glob("descr_sounds_*.txt"))
    if (data / MUSIC_TYPES_REL).exists():
        have.append("music_types")
    out, placed = [], set()
    for group, ids in GROUPS:
        for f in ids:
            if f in have:
                out.append(_file_entry(f, group))
                placed.add(f)
    for f in have:
        if f not in placed:
            out.append(_file_entry(f, "Everything else"))
    return out


def _file_entry(f: str, group: str) -> dict:
    return {"id": f, "group": group, "rel": rel_of(f),
            "label": f.replace("_", " ").capitalize(),
            "read_only": f == "music_types"}


def rel_of(f: str) -> str:
    if not re.match(r"^[a-z0-9_]+$", f or ""):
        raise ScriptError(f"no sound script called {f!r}")
    return MUSIC_TYPES_REL if f == "music_types" else f"descr_sounds_{f}.txt"


def read(mod, f: str) -> Script:
    p = Path(mod.data) / rel_of(f)
    if not p.exists():
        raise ScriptError(f"{getattr(mod, 'name', '?')} has no data/{rel_of(f)}")
    return parse_text(rel_of(f), kb.read_text(p, ENCODING))


# ---------------------------------------------------------------------------
# the vocabulary, off the mod's own files


def vocabulary(mod) -> dict:
    """Every value each selector takes, and each number key's range, in this mod."""
    values: Dict[str, set] = {}
    ranges: Dict[str, List[float]] = {}
    prefs: set = set()
    for f in files(mod):
        try:
            sc = read(mod, f["id"])
        except (ScriptError, OSError):
            continue
        for n in sc.nodes:
            if n.kind == "selector":
                values.setdefault(n.kw.lower(), set()).update(_values(n.value))
        heads = [e.attrs for e in sc.events] + [it.value for n in sc.nodes
                                                for it in n.items if it.kind == "default"]
        for a in heads:
            for k, v in _pairs(a)[0]:
                if k in NUM_KEYS and v is not None:
                    r = ranges.setdefault(k, [float(v), float(v)])
                    r[0], r[1] = min(r[0], float(v)), max(r[1], float(v))
                elif k in WORD_KEYS and v:
                    prefs.add(v.upper())
    return {"values": values, "ranges": ranges, "prefs": prefs}


def _values(value: str) -> List[str]:
    """``a, b, c`` and ``a b c`` are both lists here (``type general admiral``)."""
    return [v for v in re.split(r"[,\s]+", value) if v]


def _pairs(attrs: str):
    """``(pairs, problems)`` for an attribute string, name first if it has one."""
    toks = attrs.split()
    out, bad, i = [], [], 0
    if toks and _event_name(attrs):
        i = 1
    while i < len(toks):
        t, low = toks[i], toks[i].lower()
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if low in NUM_KEYS:
            if nxt is None or not NUM.match(nxt):
                bad.append(f"{t} needs a number after it")
                out.append((low, None))
                i += 1
            else:
                out.append((low, nxt))
                i += 2
        elif low in WORD_KEYS:
            if nxt is None or NUM.match(nxt):
                bad.append(f"{t} needs a word after it (SFX, SPEECH ...)")
                i += 1
            else:
                out.append((low, nxt))
                i += 2
        elif low in FLAGS:
            out.append((low, ""))
            i += 1
        else:
            out.append((low, "?"))
            i += 1
    return out, bad


# ---------------------------------------------------------------------------
# plan / apply


@dataclass
class ScriptPlan:
    mod: object
    file: str
    text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        out = [f"{rel_of(self.file)} in {getattr(self.mod, 'name', '?')}"]
        out += ["  " + c for c in self.changes]
        out += ["  ! " + w for w in self.warnings]
        out += ["  ERROR: " + e for e in self.errors]
        return "\n".join(out)

    def payload(self) -> dict:
        return {"ok": not self.errors and bool(self.text), "file": self.file,
                "changes": self.changes, "warnings": self.warnings,
                "errors": self.errors, "summary": self.summary()}


def _check_attrs(p: ScriptPlan, where: str, attrs: str, vocab: dict) -> None:
    pairs, bad = _pairs(attrs)
    for b in bad:
        p.errors.append(f"{where}: {b}")
    odd = [k for k, v in pairs if v == "?"]
    if odd:
        p.warnings.append(f"{where}: {kb.and_list(odd)} "
                          f"{'is' if len(odd) == 1 else 'are'} not an attribute any "
                          f"sound script here writes")
    for k, v in pairs:
        if k in WORD_KEYS and v and vocab["prefs"] and v.upper() not in vocab["prefs"]:
            p.warnings.append(f"{where}: pref {v} is not one this mod uses "
                              f"({kb.and_list(sorted(vocab['prefs']))})")


def _mod_factions(mod) -> set:
    try:
        from . import factions as fac_mod
        return {x.lower() for x in fac_mod.faction_slots(mod)}
    except Exception:          # the check is a courtesy; no list, no check
        return set()


def _check_selector(p: ScriptPlan, sc: Script, n: Node, value: str,
                    vocab: dict, mod) -> None:
    where = " / ".join(n.path())
    kw = n.kw.lower()
    vals = _values(value)
    if kw == "factions" and sc.rel == "descr_sounds_accents.txt":
        known = _mod_factions(mod)
        odd = [v for v in vals if known and v not in known]
        if odd:
            p.warnings.append(f"{where}: {kb.and_list(odd)} "
                              f"{'is not a faction' if len(odd) == 1 else 'are not factions'} "
                              f"in this mod")
        for other in sc.nodes:
            if other is n or other.kw.lower() != "factions":
                continue
            twice = sorted(set(vals) & set(_values(other.value)))
            if twice:
                acc = other.parent.label if other.parent else "another accent"
                p.warnings.append(f"{where}: {kb.and_list(twice)} "
                                  f"{'is' if len(twice) == 1 else 'are'} also under "
                                  f"{acc}, and a faction speaks with one accent")
        return
    seen = vocab["values"].get(kw, set())
    odd = [v for v in vals if seen and v not in seen]
    if odd:
        p.warnings.append(f"{where}: {kb.and_list(odd)} "
                          f"{'is' if len(odd) == 1 else 'are'} not a {n.kw} "
                          f"any sound script in this mod names")


def plan(mod, body: dict) -> ScriptPlan:
    """``{file, ops}``: event, default, setting, rename, duplicate, remove.

    Same contract as :func:`soundbanks.plan`: an op names its line by index and
    by text and is refused if they disagree, and ops run bottom-up.
    """
    f = str(body.get("file") or "")
    p = ScriptPlan(mod=mod, file=f if re.match(r"^[a-z0-9_]+$", f) else "units")
    try:
        rel = rel_of(f)
    except ScriptError as e:
        p.errors.append(str(e))
        return p
    if f == "music_types":
        p.errors.append("descr_sounds_music_types.txt is written from the campaign "
                        "map, a province at a time; it is shown here, not edited")
        return p
    path = Path(mod.data) / rel
    if not path.exists():
        p.errors.append(f"{getattr(mod, 'name', '?')} has no data/{rel}")
        return p
    original = kb.read_text(path, ENCODING)
    text = original
    vocab = None
    ops = [o for o in (body.get("ops") or []) if isinstance(o, dict)]
    ops.sort(key=lambda o: -int(o.get("at", -1)))
    for o in ops:
        kind = str(o.get("op") or "")
        at = int(o.get("at", -1))
        want = str(o.get("head") or "").strip()
        sc = parse_text(rel, text)
        if not 0 <= at < len(sc.lines) or sc.lines[at].strip() != want:
            p.errors.append(f"line {at + 1}: the file changed since it was read "
                            f"(expected {want!r}); reload and try again")
            continue
        if vocab is None:
            vocab = vocabulary(mod)
        try:
            if kind == "event":
                e = sc.event_at(at)
                if e is None:
                    p.errors.append(f"line {at + 1} is not an event")
                    continue
                owner = next((n for n in sc.nodes if e in n.events), sc.root)
                where = " / ".join(owner.path() or [f"line {at + 1}"])
                attrs = " ".join(str(o.get("attrs") or "").split())
                if e.name:
                    # the name is the block's; Rename is the one place it changes
                    attrs = (e.name + " " + attrs).strip()
                lines = [str(x) for x in (o.get("lines") or [])]
                n_err = len(p.errors)
                sb._check_event(p, where, "", lines, False, set())
                _check_attrs(p, where, attrs, vocab)
                if len(p.errors) > n_err:
                    continue
                new = sb.edit_event(sc, at, attrs, lines)
                if new != text:
                    what = []
                    if attrs != e.attrs:
                        what.append(f"attributes {e.attrs or '(none)'} -> {attrs or '(none)'}")
                    if [x.strip() for x in lines if x.strip()] != e.lines(sc.lines):
                        what.append(f"{len(e.body)} line(s) -> "
                                    f"{len([x for x in lines if x.strip()])}")
                    p.changes.append(f"{where}: " + ", ".join(what))
                    text = new
                continue
            if kind in ("default", "setting"):
                it = sc.item_at(at)
                if it is None or it.kind != kind:
                    p.errors.append(f"line {at + 1} is not a {kind} line")
                    continue
                value = " ".join(str(o.get("value") or "").split())
                where = f"{it.key} on line {at + 1}"
                if kind == "setting":
                    if not value or not all(NUM.match(v) for v in value.split()):
                        p.errors.append(f"{where}: a setting's value is a number")
                        continue
                else:
                    n_err = len(p.errors)
                    _check_attrs(p, where, value, vocab)
                    if len(p.errors) > n_err:
                        continue
                if value == it.value:
                    continue
                lines = list(sc.lines)
                lines[at] = sb._with_value(lines[at], value)
                text = "".join(lines)
                p.changes.append(f"{where}: {it.value} -> {value}")
                continue
            n = sc.node_at(at)
            if n is None:
                p.errors.append(f"line {at + 1} is not a block")
                continue
            where = " / ".join(n.path())
            value = " ".join(str(o.get("value") or "").split())
            if kind == "rename":
                if n.kind == "bank":
                    p.errors.append(f"{where}: the engine asks for a bank by its name, "
                                    f"so it is not renamed here")
                    continue
                if n.kind == "named":
                    if not sb.NAME_RE.match(value):
                        p.errors.append(f"{where}: an event name is letters, digits "
                                        f"and underscores")
                        continue
                    if value in sc.named() and value != n.value:
                        p.errors.append(f"{where}: there is already an event {value}")
                        continue
                    e = n.events[0]
                    rest = e.attrs[len(e.name):].strip()
                    lines = list(sc.lines)
                    lines[at] = sb._with_value(lines[at], (value + " " + rest).strip())
                    text = "".join(lines)
                    p.changes.append(f"{where}: renamed to event {value}")
                    p.warnings.append(f"whatever played {n.value} - the engine or a "
                                      f"script - plays nothing now")
                    continue
                # an accent with no factions is common (DaC has five); any
                # other selector emptied becomes a different one
                if not value and n.value and n.kw.lower() != "factions":
                    p.errors.append(f"{where}: a {n.kw} with nothing after it is "
                                    f"another selector; remove it in Raw text if meant")
                    continue
                if value == n.value:
                    continue
                _check_selector(p, sc, n, value, vocab, mod)
                lines = list(sc.lines)
                lines[at] = sb._with_value(lines[at], value)
                text = "".join(lines)
                p.changes.append(f"{where}: now {n.kw} {value}")
                continue
            if n.kind != "named":
                p.errors.append(f"{where}: only a named event can be copied or "
                                f"removed here; a selector's extent is set by "
                                f"indentation this file does not keep to")
                continue
            e = n.events[0]
            if kind == "remove":
                text = "".join(sc.lines[:e.at] + sc.lines[e.end:])
                p.changes.append(f"{where}: removed ({e.end - e.at} lines)")
                p.warnings.append(f"whatever plays {n.value} - the engine or a "
                                  f"script - plays nothing now")
                continue
            if kind == "duplicate":
                if not sb.NAME_RE.match(value):
                    p.errors.append(f"{where}: an event name is letters, digits and "
                                    f"underscores")
                    continue
                if value in sc.named():
                    p.errors.append(f"{where}: there is already an event {value}")
                    continue
                block = sc.lines[e.at:e.end]
                rest = e.attrs[len(e.name):].strip()
                block[0] = sb._with_value(block[0], (value + " " + rest).strip())
                before = sc.lines[:e.end]
                eol = sb._eol(sc.lines[e.at]) or "\r\n"
                if before and not sb._eol(before[-1]):
                    before = before[:-1] + [before[-1] + eol]
                text = "".join(before + block + sc.lines[e.end:])
                p.changes.append(f"event {value}: a copy of {where} "
                                 f"({e.end - e.at} lines)")
                p.warnings.append(f"event {value} plays when something asks for it "
                                  f"by name; nothing here does")
                continue
            p.errors.append(f"unknown operation {kind!r}")
        except (sb.SoundBankError, ScriptError) as exc:
            p.errors.append(str(exc))
    if p.errors:
        return p
    if parse_text(rel, text).to_text() != text:
        p.errors.append("the result does not read back the same; nothing written")
        return p
    p.text = "" if text == original else text
    return p


def apply(p: ScriptPlan) -> Dict:
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    rel = rel_of(p.file)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    target = Path(mod.data) / rel
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
        "mode": "soundscripts",
        "action": p.file,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": rel, "resolved_type": rel,
        "options": {"file": p.file},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SOUNDSCRIPT %s in %s - %d change(s), id=%s", p.file, mod.name,
             len(p.changes), tid)
    return rec


# ---------------------------------------------------------------------------
# payload


def overview(mod, f: str) -> dict:
    """One script for the screen, in the shape the Sound banks screen draws."""
    sc = read(mod, f)
    vocab = vocabulary(mod)
    index = {id(n): k for k, n in enumerate(sc.nodes)}
    nodes = []
    for n in sc.nodes:
        nodes.append({
            "kw": n.kw, "value": n.value, "label": n.label, "depth": n.depth,
            "kind": n.kind, "head": n.head, "line": n.head + 1,
            "head_text": sc.lines[n.head].strip() if n.head >= 0 else "",
            "vnv": False,
            "parent": index[id(n.parent)] if n.parent is not None else None,
            "lines": (n.events[0].end - n.head) if n.kind == "named" else 1,
            "can_copy": n.kind == "named", "can_remove": n.kind == "named",
            "can_rename": n.kind in ("named", "selector"),
            "events": [{"at": e.at, "line": e.at + 1, "name": e.name,
                        "attrs": e.attrs[len(e.name):].strip() if e.name else e.attrs,
                        "head_text": sc.lines[e.at].strip(),
                        "lines": e.lines(sc.lines)} for e in n.events],
            "items": [{"at": it.at, "line": it.at + 1, "kind": it.kind,
                       "key": it.key, "value": it.value,
                       "head_text": sc.lines[it.at].strip()} for it in n.items],
        })
    ro = f == "music_types"
    return {
        "mod": mod.name, "file": f, "label": rel_of(f), "rel": rel_of(f),
        "about": ("Written from the campaign map, a province at a time: shown "
                  "here so the family is in one place." if ro else
                  "DEFAULT: lines set what every event after them starts from; "
                  "an event's own attributes override them. Selectors (unit, "
                  "hit, season, terrain ...) say when the events under them play."),
        "exists": True, "read_only": ro, "bank": "", "named": False,
        "nodes": nodes, "events": len(sc.events), "line_count": len(sc.lines),
        "warnings": sc.warnings[:30], "packed": sb.PACKED_NOTE,
        "files": files(mod),
        "vocab": {"num": sorted(NUM_KEYS), "flags": sorted(FLAGS),
                  "prefs": sorted(vocab["prefs"]),
                  "ranges": {k: v for k, v in vocab["ranges"].items()}},
    }
