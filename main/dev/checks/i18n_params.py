"""Every tt / ttA / ttN call passes each {placeholder} its string names (Phase 88c).

    python dev/checks/i18n_params.py            # problems, file:line

A name the call does not pass is drawn as written, ``{name}`` on the screen, so a
sentence made whole by 88c that lost a parameter on the way shows at once. Read
from the source: the ID (or the IDs of a ``cond ? 'a' : 'b'`` choice) and the keys
of the object literal after it. A call whose parameters are not a literal (a
variable, a spread) is not judged. A string that shows braces as text (the
``{z}/{x}/{y}`` of a tile address) is listed in ``LITERAL_BRACES``; a call kept
for another reason says so with ``// i18n-ok: <why>``.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jslex  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "web" / "js"
CALL = re.compile(r"(?<![\w$.])(tt[AN]?)\(")
FIELD = re.compile(r"\{([A-Za-z_]\w*)(?::[^{}]*)?\}")
ID = re.compile(r"'([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)'")
WAIVER = "i18n-ok:"
#: strings whose braces are text a person reads (i18n.js leaves a name nobody
#: passes as written): a tile address's {z}/{x}/{y}, a lookup key's {key}
LITERAL_BRACES = {
    "settings.map_tiles_and_are_filled_in",            # ({z}, {x} and {y} are filled in)
    "settings.openhistoricalmap_a_backdrop_style_is_the",  # {date} in the style address
    "settings.land_cover_esa_worldcover_as_a",         # {bbox}, {width}, {height} in the address
    "campevents.labels_are_looked_up_in_as",           # the key shapes {NAME_TITLE}, {NAME_BODY}
    "renameui.lead_in_settlement",                     # the {key} a name is looked up through
    "eng.strings.this_archives_entries_have_no_tags",  # the {tag}text form of an entry
    "eng.strings.a_tag_has_no_spaces_or",
    "eng.stringsbin.an_entry_starts_with_its_tag",
}


def _close(src: str, i: int, skip) -> int:
    """Index of the bracket that closes the one opened just before ``i``."""
    depth = 0
    while i < len(src):
        j = skip.get(i)
        if j:
            i = j
            continue
        c = src[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return i
            depth -= 1
        i += 1
    return len(src)


def _top_split(src: str, a: int, b: int, skip) -> List[Tuple[int, int]]:
    """``src[a:b]`` split at its top-level commas."""
    parts, depth, s, i = [], 0, a, a
    while i < b:
        j = skip.get(i)
        if j:
            i = j
            continue
        c = src[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append((s, i))
            s = i + 1
        i += 1
    parts.append((s, b))
    return parts


def _keys(src: str, a: int, b: int, skip) -> Optional[Set[str]]:
    """The keys of the object literal ``src[a:b]``, or None when it is not one."""
    t = src[a:b].strip()
    if not (t.startswith("{") and t.endswith("}")):
        return None
    a = src.index("{", a) + 1
    b = src.rindex("}", a - 1, b)
    keys: Set[str] = set()
    for s, e in _top_split(src, a, b, skip):
        part = src[s:e].strip()
        if not part:
            continue
        if part.startswith("..."):
            return None
        m = re.match(r"""(?:'([^']*)'|"([^"]*)"|([A-Za-z_$][\w$]*))\s*(:|$)""", part)
        if not m:
            return None
        keys.add(m.group(1) or m.group(2) or m.group(3))
    return keys


def check_file(path: Path, cat: dict) -> List[str]:
    src = path.read_text(encoding="utf-8")
    skip = {l.start: l.end for l in jslex.lex(src) if l.depth == 0}
    out = []
    for m in CALL.finditer(src):
        if m.start() in skip:
            continue
        end = _close(src, m.end(), skip)
        args = _top_split(src, m.end(), end, skip)
        ids = ID.findall(src[args[0][0]:args[0][1]])
        if not ids:
            continue
        plural = m.group(1) == "ttN"
        pidx = 2 if plural else 1
        if len(args) > pidx:
            keys = _keys(src, args[pidx][0], args[pidx][1], skip)
            if keys is None:
                continue
        else:
            keys = set()
        if plural:
            keys.add("count")
        line = src.count("\n", 0, m.start()) + 1
        lines = src.split("\n")
        if any(WAIVER in lines[k] for k in (line - 1, line - 2) if k >= 0):
            continue
        every = set()
        for i in ids:
            for x in ([cat.get(i)] if isinstance(cat.get(i), str) else (cat.get(i) or {}).values()):
                every |= {f.group(1) for f in FIELD.finditer(x)}
        if len(ids) > 1 and keys - every - {"count"}:
            out.append(f"{path.name}:{line} {' / '.join(ids)} are passed {sorted(keys - every - {'count'})}"
                       f" and neither uses it")
        for i in ids:
            v = cat.get(i)
            if v is None or i in LITERAL_BRACES:
                continue
            names = set()
            for x in ([v] if isinstance(v, str) else v.values()):
                names |= {f.group(1) for f in FIELD.finditer(x)}
            lost = names - keys
            if lost:
                out.append(f"{path.name}:{line} {i} needs {sorted(lost)}")
            # a name passed and never used is text that no longer shows
            unused = keys - names - {"count"}
            if unused and len(ids) == 1:
                out.append(f"{path.name}:{line} {i} is passed {sorted(unused)} and uses none of it")
    return out


def check_engine() -> List[str]:
    """The same for the engine: each ``_i18n.msg`` / ``msgN`` passes every name its
    template uses (``count`` is msgN's own), and uses every name it is passed."""
    import ast
    out: List[str] = []
    for p in sorted((ROOT / "unittransfer").glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("msg", "msgN") and isinstance(n.func.value, ast.Name)
                    and n.func.value.id == "_i18n"):
                continue
            tpl_args = n.args[1:2] if n.func.attr == "msg" else n.args[2:4]
            if not tpl_args or not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in tpl_args):
                continue
            if any(kw.arg is None for kw in n.keywords):
                continue                                   # **params: not judged
            if isinstance(n.args[0], ast.Constant) and n.args[0].value in LITERAL_BRACES:
                continue
            keys = {kw.arg for kw in n.keywords} | ({"count"} if n.func.attr == "msgN" else set())
            names = set().union(*({f.group(1) for f in FIELD.finditer(a.value)} for a in tpl_args))
            if names - keys:
                out.append(f"{p.name}:{n.lineno} needs {sorted(names - keys)}")
            if keys - names - {"count"}:
                out.append(f"{p.name}:{n.lineno} is passed {sorted(keys - names - {'count'})} and uses none of it")
    return out


def check_tree() -> List[str]:
    cat = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8"))
    out: List[str] = []
    for p in sorted(JS.glob("*.js")):
        if p.name != "i18n.js":
            out.extend(check_file(p, cat))
    return out


if __name__ == "__main__":
    problems = check_tree() + check_engine()
    for p in problems:
        print(p)
    print(f"{len(problems)} calls that do not pass a name their string uses")
    sys.exit(1 if problems else 0)
