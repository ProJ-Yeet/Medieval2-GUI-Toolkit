"""``descr_walls.txt`` - a settlement's walls, gates and towers in battle (Phase 68).

The roadmap's row called this "wall definitions per culture and level". It is
per level only: one ``wall`` block for each of the levels 0 to 4 an EDB
building gives with ``wall_level N``, and no culture anywhere in it. Each
level has its ``wall``, its ``gateway`` (and the gate types it may carry), its
``tower`` with one firing level per ``tower_level`` an EDB building gives, and
from level 1 or 2 up a ``gatehouse``. Above them, the seven ``gates``.

**Read as the brace tree it is**, the way Phase 63 reads
``descr_offmap_models.txt``: a block's name is the last code line before its
``{``. Values are edited by keyword on their own line, keeping its indent,
its column and its comment; a gateway's gate types are rows of one word each;
a firing level is copied or removed whole. Lines keep their own ending, so a
save changes only the lines it names.

**Measured on both installed mods before any rule was written** (ROCSS 501
lines, DaC 513; both TATW-derived, both five levels and the same seven gates):

* Every gate a gateway names is declared, every ``stat`` has its eleven
  fields and names a projectile ``descr_projectile.txt`` declares, every
  ``shot_sfx`` is an ``event`` in ``descr_sounds_generic.txt``, and every
  firing level has its four ``fire_rate`` sizes. All warnings when they fail.
* **The EDB against this file**: every ``wall_level`` the EDB gives (0 to 4
  on both) has a ``wall`` block, and a building that gives ``wall_level W``
  and ``tower_level T`` together always finds wall W's tower with at least T
  firing levels (DaC's walls 1 to 4 pair with ``tower_level 2``; its tower
  at wall 1 has two). A miss is a warning.
* The file's own comment lists the tower sounds as ``arrow_tower`` and
  ``ballista_tower``; both mods fire a ``cannon_tower`` from walls 3 and 4 and
  play. It is taken as a third.
* ROCSS has three ``shot_gfx`` lines with no value, on the gatehouse arrow
  levels: a note, since the mod plays.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import keyblock as kb

REL = "descr_walls.txt"
ENCODING = "latin-1"
#: the parts of a wall level, in the order the file writes them
PARTS = ("wall", "gateway", "tower", "gatehouse")
FIRING = ("level", "missile_level", "oil_level")
SIZES = ("small", "normal", "large", "huge")
#: the file's own list, and `cannon_tower`, which both installed mods fire
SOUNDS = ("none", "knife", "sword", "spear", "axe", "mace", "club", "arrow_tower",
          "ballista_tower", "cannon_tower")
ONE_NUMBER = ("full_health", "height", "pursuit_lockout_radius", "blocked_lockout_radius",
              "control_area_radius", "manned", "fire_angle", "level")
_NUM = re.compile(r"-?\d+(\.\d*)?|-?\.\d+")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STAT_FIELDS = 11
#: the numeric fields of a `stat` line, as descr_unit.txt writes them
STAT_NUMBERS = (0, 1, 3, 4, 9, 10)


class WallError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    """``line`` is 0-based; the finding's is 1-based."""
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


@dataclass
class Node:
    """One braced block: the line naming it, its rows, its parent."""
    head: List[str]
    line: int
    close: int = -1
    parent: int = -1
    #: (line index, tokens) of every code line inside that is not a brace or a
    #: child block's name
    rows: List[Tuple[int, List[str]]] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return self.head[0].lower() if self.head else ""

    def row(self, key: str) -> Optional[Tuple[int, List[str]]]:
        return next(((i, t) for i, t in self.rows if t and t[0].lower() == key), None)

    def value(self, key: str) -> str:
        r = self.row(key)
        return " ".join(r[1][1:]) if r else ""


@dataclass
class Doc:
    text: str
    lines: List[str]              # split on "\n", each keeping its own "\r"
    nodes: List[Node]
    errors: List[Tuple[int, str]] = field(default_factory=list)

    def kids(self, i: int, kind: str = "") -> List[Tuple[int, Node]]:
        return [(j, n) for j, n in enumerate(self.nodes)
                if n.parent == i and (not kind or n.kind == kind)]


def _code(line: str) -> str:
    return kb.code_of(line.rstrip("\r"))


def parse(text: str) -> Doc:
    lines = text.split("\n")
    nodes: List[Node] = []
    stack: List[int] = []
    errors: List[Tuple[int, str]] = []
    last: Optional[Tuple[int, List[str]]] = None
    for i, line in enumerate(lines):
        c = _code(line)
        if not c:
            continue
        opens, closes = c.count("{"), c.count("}")
        word = c.replace("{", " ").replace("}", " ").split()
        if word and opens:
            # `name {` on one line
            last = (i, word)
            if stack:
                nodes[stack[-1]].rows.append(last)
        if opens:
            if last is not None and stack and nodes[stack[-1]].rows \
                    and nodes[stack[-1]].rows[-1][0] == last[0]:
                nodes[stack[-1]].rows.pop()          # it was this block's name
            head = last if last is not None else (i, [])
            nodes.append(Node(head[1], head[0], parent=stack[-1] if stack else -1))
            stack.append(len(nodes) - 1)
            last = None
        if closes:
            for _ in range(closes):
                if not stack:
                    errors.append((i, f"line {i + 1}: a }} that closes nothing"))
                    break
                nodes[stack.pop()].close = i
            last = None
            continue
        if opens:
            continue
        last = (i, c.split())
        if stack:
            nodes[stack[-1]].rows.append(last)
    for j in stack:
        errors.append((nodes[j].line, f"the block {' '.join(nodes[j].head) or '(unnamed)'} "
                                      f"opened on line {nodes[j].line + 1} is never closed"))
    return Doc(text, lines, nodes, errors)


# ---------------------------------------------------------------------------
# the model the page draws


def _row_view(doc: Doc, n: Node) -> List[Dict]:
    return [{"line": i + 1, "key": t[0], "value": " ".join(t[1:])} for i, t in n.rows if t]


def gates(doc: Doc) -> List[Dict]:
    out = []
    for i, top in enumerate(doc.nodes):
        if top.parent < 0 and top.kind == "gates":
            for j, g in doc.kids(i, "gate"):
                out.append({"id": j, "name": g.head[1] if len(g.head) > 1 else "",
                            "line": g.line + 1, "rows": _row_view(doc, g)})
    return out


def walls(doc: Doc) -> List[Dict]:
    """Each top-level ``wall``: its level, its siege-tower size, its parts, and
    each tower's and gatehouse's firing levels."""
    out = []
    for i, top in enumerate(doc.nodes):
        if top.parent >= 0 or top.kind != "wall":
            continue
        parts = []
        for j, p in doc.kids(i):
            if p.kind not in PARTS:
                continue
            firing = [{"id": k, "kind": f.kind, "line": f.line + 1, "rows": _row_view(doc, f)}
                      for k, f in doc.kids(j) if f.kind in FIRING]
            gate_rows = [{"line": r + 1, "gate": t[0]} for r, t in p.rows
                         if p.kind == "gateway" and len(t) == 1
                         and t[0].lower() != "projectile_impacts_all_hit_gate"]
            parts.append({"id": j, "kind": p.kind, "line": p.line + 1,
                          "rows": [r for r in _row_view(doc, p)
                                   if not any(g["line"] == r["line"] for g in gate_rows)],
                          "gates": gate_rows, "firing": firing})
        lv = top.value("level")
        out.append({"id": i, "level": int(lv) if kb.is_int(lv) else None, "line": top.line + 1,
                    "rows": _row_view(doc, top), "parts": parts})
    return out


# ---------------------------------------------------------------------------
# what the file is held against


def _names(path: Path, pattern: str) -> Optional[Set[str]]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="latin-1", errors="replace")
    except OSError:
        return None
    return {m.lower() for m in re.findall(pattern, text, re.M)}


class Refs:
    """What the checks hold the walls against; ``None`` skips that rule."""

    def __init__(self, projectiles=None, events=None, sets=None, sets_unread=None,
                 edb_pairs=None):
        self.projectiles: Optional[Set[str]] = projectiles
        self.events: Optional[Set[str]] = events
        self.sets: Optional[Set[str]] = sets
        self.sets_unread: List[str] = sets_unread or []
        #: {(wall_level or None, tower_level or None): [building, ...]}
        self.edb_pairs: Optional[Dict[Tuple[Optional[int], Optional[int]], List[str]]] = edb_pairs

    @classmethod
    def of(cls, mod) -> "Refs":
        from . import effects, projectiles
        data = Path(mod.data)
        sets = projectiles.effect_sets(data)
        return cls(_names(data / "descr_projectile.txt", r"^[ \t]*projectile[ \t]+(\S+)"),
                   _names(data / "descr_sounds_generic.txt", r"^[ \t]*event[ \t]+(\S+)"),
                   sets, effects.effect_files(data).unread, edb_pairs(data))


_BUILDING = re.compile(r"^\s*building\s+(\S+)", re.M)


def edb_pairs(data: Path) -> Optional[Dict[Tuple[Optional[int], Optional[int]], List[str]]]:
    """Every ``(wall_level, tower_level)`` one EDB capability block gives
    together, with the buildings that give it."""
    path = Path(data) / "export_descr_buildings.txt"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="latin-1", errors="replace")
    except OSError:
        return None
    text = "\n".join(line.split(";", 1)[0] for line in text.splitlines())
    out: Dict[Tuple[Optional[int], Optional[int]], List[str]] = {}
    marks = [(m.start(), m.group(1)) for m in _BUILDING.finditer(text)]
    for m in re.finditer(r"\bcapability\s*\{", text):
        # counted, not matched lazily: a recruit line's `requires factions
        # { jerusalem, }` closes a brace inside the block (ROCSS, every wall)
        depth, j = 1, m.end()
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        block = text[m.end():j]
        w = re.search(r"\bwall_level\s+(\d+)", block)
        t = re.search(r"\btower_level\s+(\d+)", block)
        if not (w or t):
            continue
        owner = next((name for at, name in reversed(marks) if at < m.start()), "?")
        key = (int(w.group(1)) if w else None, int(t.group(1)) if t else None)
        if owner not in out.setdefault(key, []):
            out[key].append(owner)
    return out


# ---------------------------------------------------------------------------
# checking


def _check_stat(value: str, owner: str, key: str, line: int, refs: Refs,
                out: List[Dict]) -> None:
    f = [x.strip() for x in value.split(",")]
    if len(f) != STAT_FIELDS:
        out.append(finding("stat", "fatal", f"{owner}: its stat line has {len(f)} fields, not "
                           f"the {STAT_FIELDS} descr_unit.txt writes", key, line))
        return
    for k in STAT_NUMBERS:
        if not _NUM.fullmatch(f[k]):
            out.append(finding("stat", "fatal", f"{owner}: stat field {k + 1} is {f[k]!r}, not a "
                               "number", key, line))
            return
    if refs.projectiles is not None and f[2].lower() not in refs.projectiles:
        out.append(finding("projectile", "warn", f"{owner}: fires {f[2]}, which descr_projectile.txt "
                           "does not declare", key, line))
    if f[8].lower() not in SOUNDS:
        out.append(finding("sound", "note", f"{owner}: sound type {f[8]} is not one of "
                           f"{', '.join(SOUNDS)}", key, line))


def _check_firing(doc: Doc, f: Node, owner: str, key: str, refs: Refs, out: List[Dict]) -> None:
    sizes = []
    for i, t in f.rows:
        k = t[0].lower()
        v = " ".join(t[1:])
        if k == "stat":
            _check_stat(v, owner, key, i, refs, out)
        elif k == "fire_rate":
            if len(t) != 4 or not all(_NUM.fullmatch(x) for x in t[2:]):
                out.append(finding("fire_rate", "fatal", f"{owner}: fire_rate {v} is a unit size "
                                   "and two numbers", key, i))
            else:
                sizes.append(t[1].lower())
        elif k == "shot_sfx":
            if v and refs.events is not None and v.lower() not in refs.events:
                out.append(finding("sfx", "warn", f"{owner}: shot_sfx {v} is not an event in "
                                   "descr_sounds_generic.txt", key, i))
        elif k == "shot_gfx":
            if not v:
                out.append(finding("gfx", "note", f"{owner}: shot_gfx has no value", key, i))
            elif refs.sets is not None and v.lower() not in refs.sets:
                sev = "note" if refs.sets_unread else "warn"
                out.append(finding("gfx", sev, f"{owner}: shot_gfx {v} is in none of the effect "
                                   "files that can be read"
                                   + (" (the base game's packed ones may have it)" if refs.sets_unread else ""),
                                   key, i))
        elif k in ("fire_angle",) and not (len(t) == 2 and _NUM.fullmatch(t[1])):
            out.append(finding("number", "fatal", f"{owner}: {k} {v!r} is not a number", key, i))
    gone = [s for s in SIZES if s not in sizes]
    if gone:
        out.append(finding("fire_rate", "warn", f"{owner}: no fire_rate for {', '.join(gone)} "
                           "units", key, f.line))


def check(doc: Doc, refs: Optional[Refs] = None) -> List[Dict]:
    refs = refs or Refs()
    out = [finding("braces", "fatal", msg, "file", line) for line, msg in doc.errors]
    declared = {g["name"].lower() for g in gates(doc)}
    for g in gates(doc):
        for r in g["rows"]:
            k = r["key"].lower()
            if k in ONE_NUMBER and not _NUM.fullmatch(r["value"]):
                out.append(finding("number", "fatal", f"gate {g['name']}: {k} {r['value']!r} is not "
                                   "a number", "gates", r["line"] - 1))
    if not declared and not doc.errors:
        out.append(finding("gates", "warn", "no gates block, so no gateway has a gate", "file", 0))
    levels: Dict[int, int] = {}
    towers: Dict[int, int] = {}
    for w in walls(doc):
        key = f"wall/{w['id']}"
        node = doc.nodes[w["id"]]
        lv = w["level"]
        owner = f"wall level {lv}" if lv is not None else f"the wall on line {w['line']}"
        if lv is None:
            out.append(finding("level", "fatal", f"line {w['line']}: a wall with no level", key,
                               node.line))
        elif lv in levels:
            out.append(finding("level", "warn", f"wall level {lv} is written twice (lines "
                               f"{levels[lv]} and {w['line']}); the game uses one of them",
                               key, node.line))
        else:
            levels[lv] = w["line"]
        have = {p["kind"] for p in w["parts"]}
        for need in ("wall", "gateway", "tower"):
            if need not in have:
                out.append(finding("part", "warn", f"{owner} has no {need}", key, node.line))
        for p in w["parts"]:
            pn = doc.nodes[p["id"]]
            where = f"{owner}, {p['kind']}"
            for i, t in pn.rows:
                k = t[0].lower()
                if k in ONE_NUMBER and not (len(t) == 2 and _NUM.fullmatch(t[1])):
                    out.append(finding("number", "fatal", f"{where}: {k} {' '.join(t[1:])!r} is "
                                       "not a number", key, i))
            for g in p["gates"]:
                if g["gate"].lower() not in declared:
                    out.append(finding("gate", "warn", f"{where}: gate type {g['gate']} is not "
                                       "declared in the gates block", key, g["line"] - 1))
            if p["kind"] == "gateway" and not p["gates"] and declared:
                out.append(finding("gate", "warn", f"{where}: names no gate type", key, pn.line))
            for n, f in enumerate(p["firing"], 1):
                _check_firing(doc, doc.nodes[f["id"]], f"{where}, firing level {n}", key, refs, out)
            if p["kind"] == "tower" and lv is not None:
                towers[lv] = len(p["firing"])
    if levels and sorted(levels) != list(range(len(levels))):
        out.append(finding("levels", "warn", f"the wall levels are {sorted(levels)}, not 0 to "
                           f"{len(levels) - 1} in a run", "file", 0))
    for (wl, tl), who in sorted((refs.edb_pairs or {}).items(), key=lambda kv: str(kv[0])):
        names = ", ".join(who[:3]) + ("..." if len(who) > 3 else "")
        if wl is not None and wl not in levels:
            out.append(finding("edb_wall", "warn", f"the EDB gives wall_level {wl} ({names}), and "
                               "no wall block has that level", "file", 0))
            continue
        if tl:
            have = towers.get(wl) if wl is not None else max(towers.values(), default=0)
            if have is not None and have < tl:
                at = f"wall {wl}'s tower has {have}" if wl is not None else \
                    f"no tower has more than {have}"
                out.append(finding("edb_tower", "warn", f"the EDB gives tower_level {tl} ({names}), "
                                   f"and {at} firing level(s)",
                                   f"wall/{next((w['id'] for w in walls(doc) if w['level'] == wl), '')}"
                                   if wl is not None else "file", 0))
    return out


# ---------------------------------------------------------------------------
# reading a mod


def _read(mod) -> str:
    path = Path(mod.data) / REL
    if not path.is_file():
        raise WallError(f"this mod has no {REL}")
    return kb.read_text(path, ENCODING)


def overview(mod) -> Dict:
    out: Dict = {"file": REL, "gates": [], "walls": [], "findings": [], "sizes": SIZES,
                 "sounds": SOUNDS}
    try:
        text = _read(mod)
    except WallError as e:
        out["error"] = e.message
        return out
    doc = parse(text)
    refs = Refs.of(mod)
    out["gates"] = gates(doc)
    out["walls"] = walls(doc)
    pairs = refs.edb_pairs or {}
    for w in out["walls"]:
        w["edb"] = sorted({b for (wl, _tl), who in pairs.items() if wl == w["level"] for b in who})
        w["tower_levels"] = sorted({tl for (wl, tl) in pairs if wl == w["level"] and tl})
    out["sig"] = _sig(text)
    out["findings"] = check(doc, refs)
    return out


# ---------------------------------------------------------------------------
# editing


@dataclass
class WallPlan:
    mod: object = None
    text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": [REL] if self.text else [], "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.text)}


def _eol(line: str) -> str:
    return "\r" if line.endswith("\r") else ""


def _where(doc: Doc, i: int) -> str:
    """What a change line calls the block line ``i`` is in."""
    n = next((x for x in sorted(doc.nodes, key=lambda x: -x.line)
              if x.line <= i <= x.close), None)
    names = []
    while n is not None:
        names.append(" ".join(n.head[:2]))
        if n.kind == "wall" and n.parent < 0 and n.value("level"):
            names[-1] = f"wall {n.value('level')}"
        n = doc.nodes[n.parent] if n.parent >= 0 else None
    return " / ".join(reversed(names)) or f"line {i + 1}"


def _valid(key: str, value: str, refs: Refs) -> str:
    k = key.lower()
    if re.search(r"[{};]", value):
        return f"{key}: braces and ; cannot go in a value"
    if k in ONE_NUMBER:
        return "" if _NUM.fullmatch(value) else f"{key} is a number, not {value!r}"
    if k == "stat":
        f = [x.strip() for x in value.split(",")]
        if len(f) != STAT_FIELDS:
            return f"a stat line has {STAT_FIELDS} fields, and this has {len(f)}"
        bad = [k2 + 1 for k2 in STAT_NUMBERS if not _NUM.fullmatch(f[k2])]
        return f"stat field {bad[0]} is a number" if bad else ""
    if k == "fire_rate":
        t = value.split()
        ok = len(t) == 3 and t[0].lower() in SIZES and all(_NUM.fullmatch(x) for x in t[1:])
        return "" if ok else f"fire_rate is a unit size ({', '.join(SIZES)}) and two numbers"
    if k in ("slot_yaw", "slot_pitch"):
        t = value.split()
        return "" if len(t) == 2 and all(_NUM.fullmatch(x) for x in t) else f"{key} is two numbers"
    return ""


def plan(mod, body: dict) -> WallPlan:
    """``values``: ``{line (1-based): value}`` for a ``keyword value`` line;
    ``add_gate``: ``[{gateway: its line, gate}]``; ``remove``: ``[line]`` - a
    gateway's gate row, or a firing level's first line to take the block;
    ``copy_firing``: ``[line]`` - a firing level copied under itself; ``sig``."""
    p = WallPlan(mod=mod)
    try:
        text = _read(mod)
    except WallError as e:
        p.errors.append(e.message)
        return p
    if str(body.get("sig") or "") != _sig(text):
        p.errors.append(f"{REL} changed on disk after it was opened here - reload it")
        return p
    doc = parse(text)
    if doc.errors:
        p.errors.append(f"{REL} has a brace out of place ({doc.errors[0][1]}), so nothing here "
                        "can be sure where an edit lands - fix it in Raw text first")
        return p
    refs = Refs.of(mod)
    lines = doc.lines
    rows = {i: t for n in doc.nodes for i, t in n.rows if t}
    heads = {n.line: (j, n) for j, n in enumerate(doc.nodes)}
    declared = {g["name"].lower() for g in gates(doc)}
    rewrites: Dict[int, str] = {}
    drops: Set[int] = set()
    inserts: Dict[int, List[str]] = {}
    for key, v in (body.get("values") or {}).items():
        try:
            i = int(key) - 1
        except (TypeError, ValueError):
            i = -1
        t = rows.get(i)
        if not t or len(t) < 2 and t[0].lower() not in ("shot_gfx",):
            p.errors.append(f"line {key} is not a keyword and its value")
            continue
        v = " ".join(str(v).split())
        bad = _valid(t[0], v, refs)
        if bad:
            p.errors.append(f"line {key}: {bad}")
            continue
        old = " ".join(t[1:])
        if v == old:
            continue
        body_line = lines[i].rstrip("\r")
        rewrites[i] = kb.sub_value(body_line, t[0], v) + _eol(lines[i])
        p.changes.append(f"{_where(doc, i)}: {t[0]} {old or '(blank)'} -> {v}")
        if t[0].lower() == "stat" and refs.projectiles is not None:
            proj = v.split(",")[2].strip()
            if proj.lower() not in refs.projectiles:
                p.warnings.append(f"{proj} is not a projectile descr_projectile.txt declares")
    for spec in body.get("add_gate") or []:
        at = int(spec.get("gateway") or 0) - 1
        gate = str(spec.get("gate") or "").strip()
        hit = heads.get(at)
        if hit is None or hit[1].kind != "gateway":
            p.errors.append("a gate type is added to a gateway")
            continue
        n = hit[1]
        if gate.lower() not in declared:
            p.errors.append(f"{gate!r} is not a gate the gates block declares")
            continue
        have = [(i, t) for i, t in n.rows if len(t) == 1 and t[0].lower() in declared]
        if any(t[0].lower() == gate.lower() for _i, t in have):
            p.errors.append(f"that gateway already carries {gate}")
            continue
        after = have[-1][0] if have else (n.rows[-1][0] if n.rows else n.line + 1)
        like = lines[after]
        inserts.setdefault(after, []).append(kb.indent_of(like.rstrip("\r")) + gate + _eol(like))
        p.changes.append(f"+ {_where(doc, n.line)}: gate type {gate}")
    for key in body.get("remove") or []:
        i = int(key) - 1
        if i in heads and heads[i][1].kind in FIRING:
            n = heads[i][1]
            sibs = [x for x in doc.nodes if x.parent == n.parent and x.kind in FIRING]
            if len(sibs) < 2:
                p.errors.append("a tower keeps at least one firing level")
                continue
            drops |= set(range(n.line, n.close + 1))
            p.changes.append(f"- {_where(doc, n.line)}")
            continue
        t = rows.get(i)
        par = next((n for n in doc.nodes if any(r == i for r, _t in n.rows)), None)
        if t and par is not None and par.kind == "gateway" and len(t) == 1 \
                and t[0].lower() in declared:
            drops.add(i)
            p.changes.append(f"- {_where(doc, i)}: gate type {t[0]}")
            continue
        p.errors.append(f"line {key} is not a gate type or a firing level")
    for key in body.get("copy_firing") or []:
        i = int(key) - 1
        if i not in heads or heads[i][1].kind not in FIRING:
            p.errors.append(f"line {key} is not a firing level")
            continue
        n = heads[i][1]
        inserts.setdefault(n.close, []).extend(lines[n.line:n.close + 1])
        p.changes.append(f"+ {_where(doc, n.line)}, copied under itself")
    if p.errors:
        return p
    out: List[str] = []
    for i, ln in enumerate(lines):
        if i not in drops:
            out.append(rewrites.get(i, ln))
        out += inserts.get(i, [])
    new = "\n".join(out)
    if new == text:
        p.errors.append("nothing to change")
        return p
    p.text = new
    was = {f["message"] for f in check(doc, refs)}
    p.warnings += [f["message"] for f in check(parse(new), refs)
                   if f["severity"] != "note" and f["message"] not in was]
    return p


def apply(p: WallPlan) -> Dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    target = Path(mod.data) / REL
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "walls", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": REL, "resolved_type": REL,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": {"backed_up": [REL], "created": []}, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("WALLS %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
