"""The UI's source as it reads in English (Phase 88b).

Since 88b a module's text is in ``web/i18n/en.json`` and the code says
``tt('id')``. A test that holds a module to its words (a label, a heading, a
line of help) reads it through :func:`read`, which puts each call's English
back where it stood:

* ``${tt('id',{a:expr})}`` in a template  ->  the English, ``{a}`` as ``${expr}``
* ``tt('id')`` elsewhere                  ->  ``'English'``
* ``tt('id',{a:expr})`` elsewhere         ->  ```English ${expr}```
* ``ttN('id', n, {...})``                 ->  the form for ``n``, chosen when it runs
* ``tt(on ? 'a' : 'b', {...})``           ->  ``(on ? English a : English b)`` (88c)

and index.html without its ``data-i18n`` attributes. So a check written
against the source before 88 reads the same after it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "web" / "i18n" / "en.json"
_CAT: Dict[str, object] = {}
_CALL = re.compile(r"(?<![\w$.])(tt|ttA|ttN)\('([a-z0-9_.]+)'")


def cat() -> Dict[str, object]:
    if not _CAT:
        _CAT.update(json.loads(EN.read_text(encoding="utf-8")))
    return _CAT


def _close(src: str, i: int, open_c: str, close_c: str) -> int:
    """Index of the bracket closing the one at ``i``, strings and templates skipped."""
    depth, j, n = 0, i, len(src)
    while j < n:
        c = src[j]
        if c in "'\"`":
            j = _skip_str(src, j)
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _skip_str(src: str, i: int) -> int:
    q, j = src[i], i + 1
    while j < len(src):
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if q == "`" and src.startswith("${", j):
            j = _close(src, j + 1, "{", "}") + 1
            continue
        if c == q:
            return j + 1
        j += 1
    return j


def _params(body: str) -> Dict[str, str]:
    """``{a:expr,b}`` as ``{"a": "expr", "b": "b"}``."""
    inner = body.strip()[1:-1]
    out, depth, cur, j = {}, 0, [], 0
    parts = []
    while j < len(inner):
        c = inner[j]
        if c in "'\"`":
            k = _skip_str(inner, j)
            cur.append(inner[j:k])
            j = k
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        j += 1
    if "".join(cur).strip():
        parts.append("".join(cur))
    for p in parts:
        k, sep, v = p.partition(":")
        out[k.strip()] = (v if sep else k).strip()
    return out


def _english(mid: str) -> str:
    v = cat().get(mid, mid)
    return v if isinstance(v, str) else v.get("other", mid)


def _tpl_safe(text: str) -> str:
    """English as a template literal's raw text: it means the same string."""
    return text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def _fill_tpl(text: str, params: Dict[str, str]) -> str:
    text = _tpl_safe(text)
    return re.sub(r"\{([A-Za-z_]\w*)\}", lambda m: "${" + params[m.group(1)] + "}"
                  if m.group(1) in params else m.group(0), text)


_ANY_CALL = re.compile(r"(?<![\w$.])(tt|ttA|ttN)\(")
_ID = re.compile(r"'([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)'")


def _split(body: str) -> List[str]:
    """A call's arguments, split at its top-level commas."""
    parts, cur, depth, j = [], [], 0, 0
    while j < len(body):
        c = body[j]
        if c in "'\"`":
            k = _skip_str(body, j)
            cur.append(body[j:k])
            j = k
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        j += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def _expr(mid: str, params: Dict[str, str], n_expr: str = "") -> str:
    """The English of ``mid`` as a JavaScript expression. A plural chooses its
    form when it runs, as ttN does, the count read once."""
    v = cat().get(mid, mid)
    if isinstance(v, str) or not n_expr:
        text = _english(mid)
        if params:
            return "`" + _fill_tpl(text, params) + "`"
        return "'" + text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"
    p = dict(params, count="__c")
    one = "`" + _fill_tpl(v.get("one", v.get("other", "")), p) + "`"
    other = "`" + _fill_tpl(v.get("other", ""), p) + "`"
    pick = f"__c===1?{one}:{other}"
    if "zero" in v:
        pick = f"__c===0?`{_fill_tpl(v['zero'], p)}`:" + pick
    return f"((__c)=>{pick})({n_expr})"


def english(src: str, only=None) -> str:
    """``src`` with each call's English put back; ``only``, a set of IDs,
    limits it to those."""
    out: List[str] = []
    pos = 0
    for m in _ANY_CALL.finditer(src):
        if m.start() < pos:
            continue
        open_at = m.end() - 1
        end = _close(src, open_at, "(", ")")
        if end < 0:
            continue
        args = _split(src[open_at + 1:end])
        if not args:
            continue
        ids = _ID.findall(args[0])
        if not ids or (only is not None and not set(ids) & set(only)):
            continue
        plural = m.group(1) == "ttN"
        n_expr = args[1] if plural and len(args) > 1 else ""
        pidx = 2 if plural else 1
        params = _params(args[pidx]) if len(args) > pidx and args[pidx].startswith("{") else {}
        simple = args[0] == f"'{ids[0]}'"
        in_tpl = src[max(0, m.start() - 2):m.start()] == "${" and src[end + 1:end + 2] == "}"
        if simple and not plural:
            en = _english(ids[0])
            if in_tpl:
                out.append(src[pos:m.start() - 2])
                out.append(_fill_tpl(en, params))
                pos = end + 2
                continue
            out.append(src[pos:m.start()])
            out.append(_expr(ids[0], params))
            pos = end + 1
            continue
        # a plural, or an ID chosen when it runs: tt(on ? 'a.shown' : 'a.hidden', {...})
        expr = _ID.sub(lambda i: _expr(i.group(1), params, n_expr), args[0])
        out.append(src[pos:m.start()])
        out.append(f"({expr})")
        pos = end + 1
    out.append(src[pos:])
    return "".join(out)


_DATA = re.compile(r' data-i18n(?:-[\w-]+)?="[^"]*"')


def read(path) -> str:
    """A web file as it read in English before 88: ``tt()`` inlined, and
    index.html without its ``data-i18n`` marks."""
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    if p.suffix == ".html":
        src = re.sub(r'<span data-i18n="[^"]*">(.*?)</span>', r"", src, flags=re.S)
        src = _DATA.sub("", src)
    return english(src)


_COPIES = {}


def english_copy(path) -> Path:
    """A copy of a web file as :func:`read` gives it, for a harness that hands
    Node a path: the module runs without i18n.js, its English in place."""
    p = Path(path)
    if p not in _COPIES:
        if "dir" not in _COPIES:
            import atexit
            import shutil
            import tempfile
            _COPIES["dir"] = Path(tempfile.mkdtemp(prefix="ut_webtext_"))   # one per run: suites run six at once
            atexit.register(shutil.rmtree, _COPIES["dir"], True)
        out = _COPIES["dir"] / p.name
        out.write_text(read(p), encoding="utf-8")
        _COPIES[p] = out
    return _COPIES[p]
