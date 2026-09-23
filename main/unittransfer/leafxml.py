"""The battle XML files whose values are element text (Phases 66 and 67).

``descr_hero_abilities.xml`` and ``descr_area_effects.xml`` are one shape: a
root, one list, and records whose every value is the text of a leaf element
(``<duration>30</duration>``), a few of them grouped (``<banner_colour>``
around a red, a green and a blue; an ability's effects). Phase 65's banner
file keeps its values in attributes, which is why its reader is its own.

**Read as text, like the banner file.** Both files carry things an XML library
either refuses or throws away: DaC's area effects have ``;;; 1 for burning
victims`` after a closing tag, and both files are full of comments that
document the fields. So this tokenises tags by hand, keeps every offset, and
edits by splicing a value or whole lines; the rest of the file comes back byte
for byte, tabs, comments and line endings included.

The editing half is one body shape for both files:

* ``values``: ``{node id: text}`` - a leaf's text;
* ``attrs``: ``{node id: {attribute: value}}`` - an area effect set's
  ``delay``;
* ``copy``: ``[{like: node id, into: container id?, name: str?}]`` - a record
  copied whole under itself, or at the end of another container, with its
  ``<name>`` changed;
* ``remove``: ``[node id]`` - a record or a field, whole lines;
* ``add_field``: ``[{parent: node id, tag, value}]`` - a leaf the record does
  not have yet, after its last value.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import keyblock as kb

ENCODING = "latin-1"

_TAG = re.compile(r"<!--.*?-->|<\?.*?\?>|<(/?)([A-Za-z_][\w.-]*)"
                  r"((?:\s+[\w:.-]+\s*=\s*\"[^\"]*\")*)\s*(/?)>", re.S)
_ATTR = re.compile(r"([\w:.-]+)\s*=\s*\"([^\"]*)\"")
NUM = re.compile(r"-?\d+(\.\d*)?|-?\.\d+")
INT = re.compile(r"-?\d+")
_TAGNAME = re.compile(r"[A-Za-z_][\w.-]*")


class LeafError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


@dataclass
class Node:
    id: int
    tag: str
    start: int                      # offset of `<`
    open_end: int                   # offset after the opening tag's `>`
    line: int                       # 0-based line of `<`
    parent: int = -1
    #: name -> (value, (start, end) of the value inside the quotes)
    attrs: Dict[str, Tuple[str, Tuple[int, int]]] = field(default_factory=dict)
    close_start: int = -1           # offset of the closing tag's `<`
    end: int = -1                   # offset after the element's last `>`
    children: List[int] = field(default_factory=list)

    def get(self, name: str) -> str:
        return self.attrs.get(name, ("", (0, 0)))[0]


@dataclass
class Doc:
    text: str
    nodes: List[Node]
    root_tag: str
    root_end: int                   # offset after the root's close, or -1
    errors: List[Tuple[int, str]] = field(default_factory=list)   # (line, message)

    def kids(self, n: Node, tag: str = "") -> List[Node]:
        return [self.nodes[i] for i in n.children if not tag or self.nodes[i].tag == tag]

    def child(self, n: Node, tag: str) -> Optional[Node]:
        return next(iter(self.kids(n, tag)), None)

    def find(self, tag: str) -> List[Node]:
        return [n for n in self.nodes if n.tag == tag]

    def span(self, n: Node) -> Tuple[int, int]:
        """Where a leaf's text is, blank space around it left out. An empty
        leaf gives an empty span right after its opening tag."""
        if n.close_start < 0 or n.children:
            return n.open_end, n.open_end
        raw = self.text[n.open_end:n.close_start]
        lead = len(raw) - len(raw.lstrip())
        s = n.open_end + lead
        return s, s + len(raw.strip())

    def value(self, n: Optional[Node]) -> str:
        if n is None:
            return ""
        s, t = self.span(n)
        return self.text[s:t]

    def field(self, n: Node, tag: str) -> str:
        return self.value(self.child(n, tag))

    def is_leaf(self, n: Node) -> bool:
        return not n.children and n.close_start >= 0

    def trailing(self) -> str:
        return self.text[self.root_end:] if self.root_end >= 0 else ""


def parse(text: str, root_tag: str) -> Doc:
    """Every element up to the root's close, with offsets. Never raises: a
    tag closed out of order or a root never closed is an error on the doc."""
    nodes: List[Node] = []
    stack: List[int] = []
    errors: List[Tuple[int, str]] = []
    root_end = -1
    for m in _TAG.finditer(text):
        if m.group(0).startswith(("<!--", "<?")):
            continue
        close, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3) or "", m.group(4)
        line = text.count("\n", 0, m.start())
        if close:
            if not stack or nodes[stack[-1]].tag != tag:
                errors.append((line, f"line {line + 1}: </{tag}> closes nothing open"
                               + (f" (the open one is <{nodes[stack[-1]].tag}>)" if stack else "")))
                continue
            n = nodes[stack.pop()]
            n.close_start, n.end = m.start(), m.end()
            if not stack:
                root_end = m.end()
                break
            continue
        n = Node(len(nodes), tag, m.start(), m.end(), line, parent=stack[-1] if stack else -1)
        base = m.start(3)
        for a in _ATTR.finditer(attrs):
            n.attrs[a.group(1)] = (a.group(2), (base + a.start(2), base + a.end(2)))
        if stack:
            nodes[stack[-1]].children.append(n.id)
        elif nodes:
            errors.append((line, f"line {line + 1}: <{tag}> stands outside <{root_tag}>"))
        nodes.append(n)
        if selfclose:
            n.end = m.end()
        else:
            stack.append(n.id)
    if stack:
        errors.append((nodes[stack[0]].line, f"<{nodes[stack[-1]].tag}> is never closed"))
    if nodes and nodes[0].tag != root_tag:
        errors.append((0, f"the root is <{nodes[0].tag}>, not <{root_tag}>"))
    return Doc(text, nodes, root_tag, root_end, errors)


def leaves(doc: Doc, n: Node, stop: Tuple[str, ...] = ()) -> List[Dict]:
    """Every leaf under a record, in file order, as ``{id, tag, path, value,
    line, attrs}``; ``path`` is ``banner_colour/red`` for a grouped one. A
    child whose tag is in ``stop`` is not walked into (an ability's effects)."""
    out: List[Dict] = []

    def walk(x: Node, path: str) -> None:
        for c in doc.kids(x):
            p = f"{path}/{c.tag}" if path else c.tag
            if c.children:
                if c.tag not in stop:
                    walk(c, p)
            else:
                out.append({"id": c.id, "tag": c.tag, "path": p, "value": doc.value(c),
                            "line": c.line + 1,
                            "attrs": {k: v for k, (v, _s) in c.attrs.items()}})
    walk(n, "")
    return out


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    """``line`` is 0-based, as a node carries it; the finding is 1-based."""
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


def xml_findings(doc: Doc) -> List[Dict]:
    out = [finding("xml", "fatal", msg, "file", line) for line, msg in doc.errors]
    tail = doc.trailing()
    if tail.strip():
        at = doc.text.count("\n", 0, doc.root_end)
        out.append(finding("trailing", "warn", f"text after </{doc.root_tag}> (from line "
                           f"{at + 1}) that the game never reads", "file", at))
    return out


def lev(a: str, b: str, cap: int = 3) -> int:
    """Edit distance, given up at ``cap``."""
    if abs(len(a) - len(b)) >= cap:
        return cap
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) >= cap:
            return cap
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# editing


def line_span(text: str, n: Node) -> Tuple[int, int]:
    """The whole line(s) an element stands on, newline included - or just the
    element when something else shares its line. A `;` comment after it, as
    DaC writes one, goes with the line."""
    end = n.end if n.end >= 0 else n.open_end
    s = text.rfind("\n", 0, n.start) + 1
    nl = text.find("\n", end)
    t = len(text) if nl < 0 else nl + 1
    after = text[end:t].strip()
    if text[s:n.start].strip() or (after and not after.startswith(";")):
        return n.start, end
    return s, t


def _indent(text: str, off: int) -> str:
    s = text.rfind("\n", 0, off) + 1
    return text[s:off] if not text[s:off].strip() else ""


def _reindent(chunk: str, old: str, new: str) -> str:
    if old == new:
        return chunk
    out = []
    for ln in chunk.splitlines(keepends=True):
        out.append(new + ln[len(old):] if ln.startswith(old) else ln)
    return "".join(out)


def copy_chunk(doc: Doc, like: Node, name: str = "", indent: Optional[str] = None,
               value: Optional[str] = None, attrs: Optional[Dict[str, str]] = None) -> str:
    """A record's own line(s), with its ``<name>`` changed and, given
    ``indent``, moved to that indentation. A leaf copied (a set's member) can
    take its ``value`` and ``attrs`` in the same go."""
    text = doc.text
    s, t = line_span(text, like)
    chunk = text[s:t]
    edits: List[Tuple[Tuple[int, int], str]] = []
    nm = doc.child(like, "name") if name else None
    if nm is not None:
        edits.append((doc.span(nm), name))
    if value is not None and doc.is_leaf(like):
        edits.append((doc.span(like), value))
    for a, v in (attrs or {}).items():
        if a in like.attrs:
            edits.append((like.attrs[a][1], v))
    for (a, b), v in sorted(edits, reverse=True):
        chunk = chunk[:a - s] + v + chunk[b - s:]
    if s == like.start:                      # shares a line: keep it on one
        return " " + chunk
    if indent is not None:
        chunk = _reindent(chunk, _indent(text, like.start), indent)
    if not chunk.endswith("\n"):
        chunk = kb.newline_of(text) + chunk
    return chunk


#: (node, new value) -> an error, or "" when the value is fine
Check = Callable[[Doc, Node, str], str]


@dataclass
class Plan:
    rel: str
    mode: str
    mod: object = None
    text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": [self.rel] if self.text else [], "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.text)}


def read(mod, rel: str) -> str:
    path = Path(mod.data) / rel
    if not path.is_file():
        raise LeafError(f"this mod has no {rel}")
    return kb.read_text(path, ENCODING)


def _label(doc: Doc, n: Node) -> str:
    """What a change line calls a node: its record's name and its own tag."""
    cur = n
    while cur.parent >= 0:
        nm = doc.child(cur, "name")
        if nm is not None and nm.id != n.id:
            return f"{doc.value(nm)} {n.tag}" if cur.id != n.id else doc.value(nm)
        cur = doc.nodes[cur.parent]
    return n.tag


def plan_edits(p: Plan, text: str, doc: Doc, body: dict, check_value: Check,
               copyable: Tuple[str, ...], removable: Callable[[Doc, Node], str],
               fields_of: Callable[[Doc, Node], Tuple[str, ...]],
               name_ok: Callable[[Doc, Node, str], str]) -> str:
    """Every edit the body asks for, as one new text, or "" with ``p.errors``.

    ``copyable`` is the tags that may be copied whole; ``removable`` says why
    a node may not go (or ""); ``fields_of`` is the tags a container may be
    given; ``name_ok`` vets a copy's new name."""
    by = {n.id: n for n in doc.nodes}
    splices: List[Tuple[int, int, str]] = []

    def node(key) -> Optional[Node]:
        try:
            return by.get(int(key))
        except (TypeError, ValueError):
            return None

    for key, v in (body.get("values") or {}).items():
        n = node(key)
        if n is None or not doc.is_leaf(n):
            p.errors.append(f"element {key} is not a value in the file")
            continue
        v = str(v).strip()
        if re.search(r"[<>&]", v):
            p.errors.append(f"{n.tag}: <, > and & cannot go in a value")
            continue
        bad = check_value(doc, n, v)
        if bad:
            p.errors.append(bad)
            continue
        cur = doc.value(n)
        if v != cur:
            a, b = doc.span(n)
            splices.append((a, b, v))
            p.changes.append(f"{_label(doc, n)} (line {n.line + 1}): {cur or '(blank)'} -> {v or '(blank)'}")
    for key, vals in (body.get("attrs") or {}).items():
        n = node(key)
        if n is None:
            p.errors.append(f"element {key} is not in the file")
            continue
        for a, v in (vals or {}).items():
            v = str(v).strip()
            if a not in n.attrs:
                p.errors.append(f"<{n.tag}> on line {n.line + 1} has no {a}")
                continue
            if re.search(r"[\"<>&]", v):
                p.errors.append(f"{a}: quotes, <, > and & cannot go in a value")
                continue
            if not NUM.fullmatch(v):
                p.errors.append(f"{n.tag} {a} is a number, not {v!r}")
                continue
            cur, span = n.attrs[a]
            if v != cur:
                splices.append((span[0], span[1], v))
                p.changes.append(f"{_label(doc, n)} (line {n.line + 1}): {a} {cur} -> {v}")
    for spec in body.get("copy") or []:
        like = node(spec.get("like"))
        if like is None or like.tag not in copyable:
            p.errors.append("only a whole record can be copied")
            continue
        name = str(spec.get("name") or "").strip()
        if name:
            bad = name_ok(doc, like, name)
            if bad:
                p.errors.append(bad)
                continue
        value = spec.get("value")
        cattrs = {str(k): str(v).strip() for k, v in (spec.get("attrs") or {}).items()}
        if value is not None:
            value = str(value).strip()
            bad = "only a single value takes a new value" if not doc.is_leaf(like) else                 ("<, > and & cannot go in a value" if re.search(r"[<>&]", value)
                 else check_value(doc, like, value))
            if bad:
                p.errors.append(bad)
                continue
        if any(k not in like.attrs or not NUM.fullmatch(v) for k, v in cattrs.items()):
            p.errors.append(f"<{like.tag}>'s attributes are numbers it already has")
            continue
        into = node(spec.get("into")) if spec.get("into") not in (None, "") else None
        if into is not None:
            kids = doc.kids(into, like.tag)
            if not kids:
                p.errors.append(f"<{like.tag}> cannot go into <{into.tag}>")
                continue
            last = kids[-1]
            _s, at = line_span(text, last)
            chunk = copy_chunk(doc, like, name, _indent(text, last.start), value, cattrs)
        else:
            _s, at = line_span(text, like)
            chunk = copy_chunk(doc, like, name, None, value, cattrs)
        splices.append((at, at, chunk))
        src = doc.field(like, "name") or doc.value(like) or like.tag
        new_name = name or (value if value is not None else "")
        p.changes.append(f"+ {new_name or src}, copied from {src} (line {like.line + 1})"
                         + (f" into {_label(doc, into)}" if into is not None else ""))
    for key in body.get("remove") or []:
        n = node(key)
        if n is None or n.parent < 0:
            p.errors.append(f"element {key} is not in the file")
            continue
        why = removable(doc, n)
        if why:
            p.errors.append(why)
            continue
        s, t = line_span(text, n)
        splices.append((s, t, ""))
        p.changes.append(f"- {_label(doc, n)} (line {n.line + 1})")
    for spec in body.get("add_field") or []:
        par = node(spec.get("parent"))
        tag = str(spec.get("tag") or "").strip()
        v = str(spec.get("value") or "").strip()
        if par is None or not par.children:
            p.errors.append("a field is added to a record that has fields")
            continue
        if not _TAGNAME.fullmatch(tag) or tag not in fields_of(doc, par):
            p.errors.append(f"<{par.tag}> takes no <{tag}> here")
            continue
        if doc.child(par, tag) is not None:
            p.errors.append(f"{_label(doc, par)} already has a <{tag}>")
            continue
        if re.search(r"[<>&]", v):
            p.errors.append(f"{tag}: <, > and & cannot go in a value")
            continue
        fake = Node(-1, tag, 0, 0, par.line, parent=par.id)
        bad = check_value(doc, fake, v)
        if bad:
            p.errors.append(bad)
            continue
        # after the record's last value, so a field goes among its own fields
        # and not after a group (an ability's effects) that ends the record
        flat = [k for k in doc.kids(par) if doc.is_leaf(k)]
        last = flat[-1] if flat else doc.kids(par)[-1]
        s, at = line_span(text, last)
        nl = kb.newline_of(text)
        if s == last.start:
            chunk = f" <{tag}>{v}</{tag}>"
            at = last.end
        else:
            chunk = f"{_indent(text, last.start)}<{tag}>{v}</{tag}>{nl}"
            if not text[s:at].endswith("\n"):
                chunk = nl + chunk
        splices.append((at, at, chunk))
        p.changes.append(f"+ {_label(doc, par)}: <{tag}>{v}</{tag}>")
    if p.errors:
        return ""
    spans = sorted(splices, key=lambda x: (x[0], x[1]))
    for (a0, a1, _), (b0, b1, _) in zip(spans, spans[1:]):
        if b0 < a1:
            p.errors.append("two edits touch the same place - save one, then the other")
            return ""
    new = text
    for s, t, v in sorted(splices, key=lambda x: (x[0], x[1]), reverse=True):
        new = new[:s] + v + new[t:]
    if new == text:
        p.errors.append("nothing to change")
        return ""
    return new


def apply(p: Plan) -> Dict:
    """Back the file up, write it, and log the one Undo."""
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    target = Path(mod.data) / p.rel
    bpath = backup_root / "data" / p.rel
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": p.mode, "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.rel, "resolved_type": p.rel,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": {"backed_up": [p.rel], "created": []}, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("%s %d change(s) in %s, id=%s", p.mode.upper(), len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
