"""``descr_lbc_db.txt`` and ``descr_offmap_models.txt`` - who walks a faction's
streets, and what its fleets and settlements look like off the map (Phase 63).

Both were read by three modules as places a faction is named (the clone copies
a faction's block in each, the audit counts them, a rename follows them) and
parsed by none. This reads, checks and edits them.

**``descr_lbc_db.txt``**, the settlement populace: a ``faction`` line, then a
``model <name> <share>`` line per kind of townsfolk::

    faction venice
    model roman_peasant           40
    model roman_female_peasant   60

**``descr_offmap_models.txt``** is three braced sections, and they nest
differently: ``navy`` holds a block per ``faction`` with a ``large``,
``medium`` and ``small`` row (a model path and two numbers), while
``settlement`` and ``port`` hold a block per ``culture``, a block per
``level`` inside that, and one row (a path and two numbers) inside that. So
the reader is a tree of braced blocks - each named by the line before its
``{`` - rather than a shape per section.

**Measured on both installed mods.** 30 populace blocks each; every one's
shares add up to exactly 100; the nine model names are all the base game's
peasants, which live in its packed modeldb, so a name is not checked against a
mod's own. The off-map models point at ``data/models_off_map/...`` and
``data/models_building/...`` files the base game also packs, so a missing path
is not a finding either. DaC's populace file has no block for ``gundabad`` or
``scripts`` and still has one for ``ents``, which is no faction; DaC's navy has
no block for several of its factions. Both kinds of mismatch are notes: nothing
says what the engine does about either, and DaC plays.

The checks, then: a share that is not a whole number (fatal), shares that do
not add up to 100 (warning), a faction written twice in one list (warning), a
row's two numbers that are not numbers (fatal), and the roster mismatches
(notes). Saves are line splices, so a file keeps its tabs, comments and line
endings; an off-map edit carries the signature of the copy it was made
against, and a file changed since is refused.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb

LBC_REL = "descr_lbc_db.txt"
OFFMAP_REL = "descr_offmap_models.txt"
ENCODING = "latin-1"
_NUM = re.compile(r"-?\d+(\.\d+)?")


class SiteError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _code(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _tok_sub(line: str, index: int, value: str) -> str:
    """The ``index``-th token of a line's code replaced, everything around it -
    tabs, spacing, a comment - kept."""
    code_end = line.find(";") if ";" in line else len(line)
    spans = [m.span() for m in re.finditer(r"\S+", line[:code_end])]
    s, e = spans[index]
    return line[:s] + value + line[e:]


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# the populace


@dataclass
class Populace:
    faction: str
    line: int                                   # the `faction` line
    #: (line index, model, share)
    models: List[Tuple[int, str, str]] = field(default_factory=list)

    @property
    def end(self) -> int:
        return self.models[-1][0] if self.models else self.line


def parse_lbc(text: str) -> Tuple[List[str], List[Populace]]:
    lines = text.split("\n")
    out: List[Populace] = []
    for i, line in enumerate(lines):
        w = _code(line).split()
        if not w:
            continue
        if w[0].lower() == "faction" and len(w) > 1:
            out.append(Populace(w[1], i))
        elif w[0].lower() == "model" and out and len(w) >= 3:
            out[-1].models.append((i, w[1], w[-1]))
    return lines, out


# ---------------------------------------------------------------------------
# the off-map models


@dataclass
class OffNode:
    """One braced block: the line that names it (``faction ireland``,
    ``culture southern_european``, ``level village``), its rows, its parent."""
    head: List[str]
    line: int
    close: int = -1
    parent: int = -1
    #: (line index, tokens) of each line inside that is neither a brace nor a
    #: block's own name
    rows: List[Tuple[int, List[str]]] = field(default_factory=list)


def parse_offmap(text: str) -> Tuple[List[str], List[OffNode]]:
    """Every block in file order; a block's name is the last code line before
    its ``{``, which all three installed files put on a line of its own."""
    lines = text.split("\n")
    nodes: List[OffNode] = []
    stack: List[int] = []
    last: Optional[Tuple[int, List[str]]] = None
    for i, line in enumerate(lines):
        c = _code(line)
        if not c:
            continue
        if c == "{":
            if last is not None and stack and nodes[stack[-1]].rows \
                    and nodes[stack[-1]].rows[-1][0] == last[0]:
                nodes[stack[-1]].rows.pop()          # it was this block's name
            head = last if last is not None else (i, [])
            nodes.append(OffNode(head[1], head[0], parent=stack[-1] if stack else -1))
            stack.append(len(nodes) - 1)
            last = None
            continue
        if c == "}":
            if stack:
                nodes[stack.pop()].close = i
            last = None
            continue
        last = (i, c.split())
        if stack:
            nodes[stack[-1]].rows.append(last)
    return lines, nodes


def offmap_path(nodes: List[OffNode], n: OffNode) -> str:
    """``navy/faction ireland`` - the names down to ``n``."""
    parts = []
    cur: Optional[OffNode] = n
    while cur is not None:
        parts.append(" ".join(cur.head[:2]))
        cur = nodes[cur.parent] if cur.parent >= 0 else None
    return "/".join(reversed(parts))


def _depth(nodes: List[OffNode], n: OffNode) -> int:
    d = 0
    while n.parent >= 0:
        d += 1
        n = nodes[n.parent]
    return d


def _children(nodes: List[OffNode], i: int) -> List[OffNode]:
    return [n for n in nodes if n.parent == i]


# ---------------------------------------------------------------------------
# reading, checking


def _roster(mod) -> List[str]:
    from . import factions as fa
    path = fa.path_for(mod)
    if not path.is_file():
        return []
    return [fa.slot_of(r.name) for r in fa.parse_file(path).records]


def _read(mod, rel: str) -> str:
    path = Path(mod.data) / rel
    if not path.is_file():
        raise SiteError(f"this mod has no {rel}")
    return kb.read_text(path, ENCODING)


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


def check_lbc(pops: List[Populace], roster: List[str]) -> List[Dict]:
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for p in pops:
        if p.faction in seen:
            out.append(finding("duplicate", "warn", f"{p.faction} has two populace blocks "
                               f"(lines {seen[p.faction] + 1} and {p.line + 1})",
                               f"lbc/{p.faction}", p.line))
        seen.setdefault(p.faction, p.line)
        bad = False
        for i, m, s in p.models:
            if not re.fullmatch(r"\d+", s):
                bad = True
                out.append(finding("share", "fatal", f"{p.faction}: {m}'s share {s!r} is not "
                                   f"a whole number", f"lbc/{p.faction}", i))
        total = sum(int(s) for _i, _m, s in p.models if re.fullmatch(r"\d+", s))
        if p.models and not bad and total != 100:
            out.append(finding("sum", "warn", f"{p.faction}'s townsfolk add up to {total}, "
                               f"not 100 (both installed mods' do, every one)",
                               f"lbc/{p.faction}", p.line))
    if roster:
        for f in roster:
            if f not in seen:
                out.append(finding("absent", "note", f"{f} is in the roster and has no "
                                   f"populace block", f"lbc/{f}", 0))
        for f, at in seen.items():
            if f not in roster:
                out.append(finding("stale", "note", f"{f} has a populace block and is not a "
                                   f"faction in the roster", f"lbc/{f}", at))
    return out


def check_offmap(nodes: List[OffNode], roster: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for ti, top in enumerate(nodes):
        if top.parent >= 0:
            continue
        name = " ".join(top.head)
        facs = [n for n in _children(nodes, ti) if n.head[:1] == ["faction"] and len(n.head) > 1]
        seen: Dict[str, int] = {}
        for n in facs:
            f = n.head[1]
            if f in seen:
                out.append(finding("duplicate", "warn", f"{name}: {f} is written twice (lines "
                                   f"{seen[f] + 1} and {n.line + 1})", f"offmap/{name}/{f}", n.line))
            seen.setdefault(f, n.line)
        if facs and roster:
            for f in roster:
                if f not in seen:
                    out.append(finding("absent", "note", f"{name}: {f} is in the roster and has "
                                       f"no block here", f"offmap/{name}/{f}", top.line))
            for f, at in seen.items():
                if f not in roster:
                    out.append(finding("stale", "note", f"{name}: {f} has a block and is not a "
                                       f"faction in the roster", f"offmap/{name}/{f}", at))
    for n in nodes:
        for i, toks in n.rows:
            if toks[:1] == ["faction"] and len(toks) > 1:
                # DaC's own file: `faction egypt` with no `{` under it, and so
                # 117 opening braces to 118 closing - its `}` closes the navy
                # section, and every faction after it is read outside the navy
                out.append(finding("unopened", "warn",
                                   f"line {i + 1}: faction {toks[1]} has no opening brace, so "
                                   f"its closing one ends the enclosing block early and "
                                   f"everything after it is read outside it",
                                   f"offmap/{offmap_path(nodes, n)}", i))
                continue
            for v in (toks[-2:] if len(toks) >= 3 else []):
                if not _NUM.fullmatch(v):
                    out.append(finding("number", "fatal", f"line {i + 1}: {v!r} is not a number",
                                       f"offmap/{offmap_path(nodes, n)}", i))
    return out


def overview(mod) -> Dict:
    roster = _roster(mod)
    out: Dict = {"roster": roster, "lbc": None, "offmap": None, "findings": []}
    try:
        _lines, pops = parse_lbc(_read(mod, LBC_REL).replace("\r\n", "\n"))
        out["lbc"] = [{"faction": p.faction, "line": p.line + 1,
                       "models": [{"model": m, "share": s} for _i, m, s in p.models]}
                      for p in pops]
        out["findings"] += check_lbc(pops, roster)
    except SiteError as e:
        out["lbc_error"] = e.message
    try:
        text = _read(mod, OFFMAP_REL)
        _lines, nodes = parse_offmap(text.replace("\r\n", "\n"))
        out["offmap"] = [{"path": offmap_path(nodes, n), "depth": _depth(nodes, n),
                          "head": n.head, "line": n.line + 1, "kind": (n.head or [""])[0],
                          "rows": [{"line": i, "tokens": t} for i, t in n.rows]}
                         for n in nodes]
        out["offmap_sig"] = _sig(text)
        out["findings"] += check_offmap(nodes, roster)
    except SiteError as e:
        out["offmap_error"] = e.message
    return out


# ---------------------------------------------------------------------------
# the save


@dataclass
class SitePlan:
    mod: object = None
    texts: Dict[str, str] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": sorted(self.texts), "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.texts)}


def _splice(lines: List[str], rewrites: Dict[int, str], drops: set,
            inserts: Dict[int, List[str]]) -> List[str]:
    out: List[str] = []
    for i, ln in enumerate(lines):
        if i not in drops:
            out.append(rewrites.get(i, ln))
        out += inserts.get(i, [])
    return out


def _plan_lbc(p: SitePlan, mod, lbc: Dict, roster: List[str]) -> None:
    try:
        text = _read(mod, LBC_REL)
    except SiteError as e:
        p.errors.append(e.message)
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    lines, pops = parse_lbc(text.replace("\r\n", "\n"))
    by = {x.faction: x for x in pops}
    rewrites: Dict[int, str] = {}
    drops: set = set()
    inserts: Dict[int, List[str]] = {}
    tail: List[str] = []
    sample = next((lines[x.models[0][0]] for x in pops if x.models), "model x\t0")
    for fac, rows in lbc.items():
        cur = by.get(fac)
        if rows is None:
            if cur is None:
                p.errors.append(f"{fac} has no populace block to take out")
                continue
            end = cur.end + 1
            while end < len(lines) and not lines[end].strip():
                end += 1
            drops |= set(range(cur.line, end))
            p.changes.append(f"- {fac}'s populace")
            continue
        rows = [(str(m).strip(), str(s).strip()) for m, s in rows]
        bad = False
        for m, s in rows:
            if not m or re.search(r"\s", m):
                p.errors.append(f"{fac}: {m!r} is not a model name")
                bad = True
            if not re.fullmatch(r"\d+", s):
                p.errors.append(f"{fac}: a share is a whole number, not {s!r}")
                bad = True
        if bad:
            continue
        made = lambda m, s, base=sample: _tok_sub(_tok_sub(base, 1, m), 2, s)
        if cur is None:
            if roster and fac not in roster:
                p.warnings.append(f"{fac} is not a faction in the roster")
            tail += ["", f"faction {fac}"] + [made(m, s) for m, s in rows]
            p.changes.append(f"+ {fac}'s populace ({len(rows)} model(s))")
            continue
        if [(m, s) for _i, m, s in cur.models] == rows:
            continue
        idxs = [i for i, _m, _s in cur.models]
        for k, (m, s) in enumerate(rows):
            if k < len(idxs):
                ln = lines[idxs[k]]
                ln = _tok_sub(ln, 1, m)
                ln = _tok_sub(ln, len(re.findall(r"\S+", ln.split(";")[0])) - 1, s)
                rewrites[idxs[k]] = ln
            else:
                inserts.setdefault(cur.end, []).append(
                    made(m, s, lines[idxs[-1]]) if idxs else made(m, s))
        drops |= set(idxs[len(rows):])
        p.changes.append(f"{fac}: " + ", ".join(f"{m} {s}" for m, s in rows))
    if p.errors:
        return
    out = _splice(lines, rewrites, drops, inserts)
    if tail:
        while out and not out[-1].strip():
            out.pop()
        out += tail + [""]
    new_text = nl.join(out)
    if new_text == text:
        return
    p.texts[LBC_REL] = new_text
    was = {f["message"] for f in check_lbc(pops, roster)}
    _, after = parse_lbc(new_text.replace("\r\n", "\n"))
    p.warnings += [f["message"] for f in check_lbc(after, roster)
                   if f["severity"] != "note" and f["message"] not in was]


def _plan_offmap(p: SitePlan, mod, off: Dict, sig: str, roster: List[str]) -> None:
    try:
        text = _read(mod, OFFMAP_REL)
    except SiteError as e:
        p.errors.append(e.message)
        return
    if sig != _sig(text):
        p.errors.append(f"{OFFMAP_REL} changed on disk after it was opened here - reload it")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    lines, nodes = parse_offmap(text.replace("\r\n", "\n"))
    rows = {i: (n, t) for n in nodes for i, t in n.rows}
    rewrites: Dict[int, str] = {}
    drops: set = set()
    inserts: Dict[int, List[str]] = {}
    for key, vals in (off.get("rows") or {}).items():
        i = int(key)
        if i not in rows:
            p.errors.append(f"line {i + 1} is not a row of {OFFMAP_REL}")
            continue
        n, toks = rows[i]
        vals = [str(v).strip() for v in vals]
        if len(vals) != len(toks) or any(not v or re.search(r"\s", v) for v in vals):
            p.errors.append(f"line {i + 1} takes {len(toks)} values, none of them blank")
            continue
        if len(vals) >= 3 and any(not _NUM.fullmatch(v) for v in vals[-2:]):
            p.errors.append(f"line {i + 1}: the last two values are numbers")
            continue
        ln = lines[i]
        for k, v in enumerate(vals):
            if v != toks[k]:
                ln = _tok_sub(ln, k, v)
        if ln != lines[i]:
            rewrites[i] = ln
            p.changes.append(f"{offmap_path(nodes, n)}: {' '.join(vals)}")
    tops = {" ".join(n.head): (i, n) for i, n in enumerate(nodes) if n.parent < 0}
    for spec in off.get("add") or []:
        sec, fac, like = (str(spec.get(k) or "").strip() for k in ("section", "faction", "like"))
        ti, top = tops.get(sec, (-1, None))
        kids = _children(nodes, ti) if top is not None else []
        src = next((x for x in kids if x.head[:2] == ["faction", like]), None)
        if src is None:
            p.errors.append(f"{sec or 'that section'} has no faction {like} to copy")
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", fac):
            p.errors.append(f"{fac!r} is not a faction slot")
            continue
        if any(x.head[:2] == ["faction", fac] for x in kids):
            p.errors.append(f"{sec} already has {fac}")
            continue
        if roster and fac not in roster:
            p.warnings.append(f"{fac} is not a faction in the roster")
        block = lines[src.line:src.close + 1]
        block[0] = _tok_sub(block[0], 1, fac)
        inserts.setdefault(top.close - 1, []).extend(block)
        p.changes.append(f"+ {sec}: {fac}, copied from {like}")
    for spec in off.get("remove") or []:
        sec, fac = (str(spec.get(k) or "").strip() for k in ("section", "faction"))
        ti, top = tops.get(sec, (-1, None))
        hit = next((x for x in (_children(nodes, ti) if top is not None else [])
                    if x.head[:2] == ["faction", fac]), None)
        if hit is None:
            p.errors.append(f"{sec or 'that section'} has no block for {fac}")
            continue
        drops |= set(range(hit.line, hit.close + 1))
        p.changes.append(f"- {sec}: {fac}")
    if p.errors:
        return
    new_text = nl.join(_splice(lines, rewrites, drops, inserts))
    if new_text != text:
        p.texts[OFFMAP_REL] = new_text


def plan(mod, body: dict) -> SitePlan:
    """``body["lbc"]``: ``{faction: [[model, share], ...]}`` replacing that
    faction's list (a faction the file lacks is added at the end, ``null``
    removes one). ``body["offmap"]``: ``{rows: {line: [tokens]}, add:
    [{section, faction, like}], remove: [{section, faction}]}``, with
    ``body["offmap_sig"]`` the signature the page read the file under."""
    p = SitePlan(mod=mod)
    roster = _roster(mod)
    if body.get("lbc"):
        _plan_lbc(p, mod, dict(body["lbc"]), roster)
    if body.get("offmap") and not p.errors:
        _plan_offmap(p, mod, dict(body["offmap"]), str(body.get("offmap_sig") or ""), roster)
    if not p.texts and not p.errors:
        p.errors.append("nothing to change")
    return p


def apply(p: SitePlan) -> Dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.texts:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    for rel, text in sorted(p.texts.items()):
        target = Path(mod.data) / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, bpath)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", target, f"-> {bpath}")
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "factionsites", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": ", ".join(sorted(p.texts)), "resolved_type": ", ".join(sorted(p.texts)),
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SITES  %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
