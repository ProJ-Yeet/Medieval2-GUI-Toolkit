"""Find the sentences the page still builds with ``+``, and the plurals it makes with an 's' (Phase 88c).

    python dev/checks/i18n_joins.py            # counts per module
    python dev/checks/i18n_joins.py --list     # every site, file:line and the source line
    python dev/checks/i18n_joins.py FILE...    # only these modules
    python dev/checks/i18n_joins.py --py [--list]   # the engine's built messages

Two kinds of site, both of which no translation can be right for:

* ``join`` - a ``tt(...)`` / ``ttA(...)`` / ``ttN(...)`` call with a ``+`` straight
  before or after it, so the page glues a catalogue string to other text. The
  other text is a value (a path, a count), a second catalogue string, or English
  the extractor did not see. Word order differs between languages, so the
  sentence must be one string with named placeholders.
* ``plural`` - ``n === 1 ? '' : 's'`` (and the mirror image), an English plural
  made in code. The catalogue holds a form per CLDR category and the page asks
  ``ttN(id, n)``.
* ``fragment`` - a catalogue string that is half a sentence, joined inside a
  template where there is no ``+`` to see (``${tt('x.read')}${path}``): one that
  opens with a space and a lower-case word, or ends on a word and a space.

A finished tree has none of either. ``tests/test_i18n`` runs this over web/js.
A site that is not a sentence at all (a key built for the undo stack, a code name
joined to a value) is kept by a comment ``// i18n-ok: <why>`` on its line or the
line above (``# i18n-ok: <why>`` in the engine), so each exception is on the
record where it stands.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jslex  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "web" / "js"

CALL = re.compile(r"(?<![\w$.])(tt[AN]?)\(")
# an English plural made in code: a ternary that yields '' or 's' (or 'es', 'ies')
PLURAL = re.compile(
    r"""(?:[?]\s*(?:''|"")\s*:\s*(?:'s'|"s"|'es'|"es"|'ies'|"ies"|'y'|"y")"""
    r"""|[?]\s*(?:'s'|"s"|'es'|"es"|'ies'|"ies")\s*:\s*(?:''|"")"""
    # 88d: 'y' : 'ies' (entr-y), and ' is' : the catalogue's 's are' in either order
    r"""|[?]\s*(?:'y'|"y")\s*:\s*(?:'ies'|"ies")"""
    r"""|[?]\s*(?:' is'|" is"|'is'|"is")\s*:)""")
# an s glued straight onto a counted noun: `${n} file${n===1?'':'s'}` is caught above;
# this is the bare  + 's'  and  + (n===1?'':'s')  forms
PLURAL_CAT = re.compile(r"""\+\s*(?:'s'|"s")(?![\w])""")


# a conditional yielding a plural ending or agreement word inside a message's parameter
ENGINE_PLURAL = re.compile(
    r"""\bif\b[^,]*?(?:[=!]=\s*1\b|>\s*1\b)"""
    r"""|['"](?:s|es|ies|y|is|are|its|their|it does|they do|has|have)['"]""")
#: a site checked by hand and kept: not a sentence (a key, a code name), said on the line or the one above
WAIVER = "i18n-ok:"


@dataclass
class Site:
    file: str
    line: int
    kind: str      # join | plural
    text: str


def _skip_ws(src: str, i: int, step: int) -> int:
    while 0 <= i < len(src) and src[i] in " \t\r\n":
        i += step
    return i


def scan(path: Path) -> List[Site]:
    src = path.read_text(encoding="utf-8")
    inside = {l.start: l.end for l in jslex.lex(src) if l.depth == 0}
    lines = src.split("\n")

    def lit_end(i):
        return inside.get(i)

    def line_of(off):
        return src.count("\n", 0, off) + 1

    def line_text(off):
        return lines[line_of(off) - 1].strip()

    def waived(ln):
        return any(WAIVER in lines[k] for k in (ln - 1, ln - 2) if 0 <= k < len(lines))

    out: List[Site] = []
    seen = set()
    for m in CALL.finditer(src):
        s = m.start()
        # is this call itself inside a literal that is not a template expression?
        depth = 0
        i = m.end()
        n = len(src)
        while i < n:
            j = lit_end(i)
            if j:
                i = j
                continue
            c = src[i]
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        end = i + 1
        a = _skip_ws(src, end, 1)
        b = _skip_ws(src, s - 1, -1)
        after = a < n and src[a] == "+" and src[a:a + 2] not in ("++", "+=")
        before = b >= 0 and src[b] == "+" and src[b - 1:b + 1] not in ("++",) and src[b:b + 2] != "+="
        if (after or before) and line_of(s) not in seen:
            seen.add(line_of(s))
            out.append(Site(path.name, line_of(s), "join", line_text(s)))
    for m in list(PLURAL.finditer(src)) + list(PLURAL_CAT.finditer(src)):
        ln = line_of(m.start())
        if ("plural", ln) in seen:
            continue
        seen.add(("plural", ln))
        out.append(Site(path.name, ln, "plural", line_text(m.start())))
    out = [s for s in out if not waived(s.line)]
    out.sort(key=lambda s: (s.line, s.kind))
    return out


#: what may open a string that is a tag after a name (" · unique", " (no text)")
_TAG_OPEN = "·([+-–|,;/→←✓✗⚠<"


def fragment(text: str) -> bool:
    """A catalogue string that is half a sentence: it opens mid-sentence (a space, then a
    lower-case word: " after {delay}s") or stops mid-sentence (a word, then a space:
    "Could not read "). A tag after a name, a label ending in a colon, and a whole
    sentence set after another are phrases of their own."""
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.strip()
    first = t.split()[0]
    code_name = "." in first.rstrip(".,:") or "_" in first     # descr_sm_factions.txt opens a sentence
    if text[0] == " " and t[0] not in _TAG_OPEN and t[0].islower() and not code_name:
        return True
    if text[-1] == " " and (t[-1].isalnum() or t[-1] == "}"):
        return True
    return False


def scan_fragments(files=None) -> List[Site]:
    """Uses of a catalogue string that is a fragment (see :func:`fragment`)."""
    import json
    cat = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8"))
    bad = {k for k, v in cat.items() if k != "_meta" and fragment(v)}
    paths = [JS / f for f in files] if files else sorted(JS.glob("*.js"))
    out: List[Site] = []
    for p in paths:
        lines = p.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            for m in re.finditer(r"'([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)'", line):
                if m.group(1) in bad and not any(WAIVER in lines[k] for k in (i, i - 1) if k >= 0):
                    out.append(Site(p.name, i + 1, "fragment", f"{m.group(1)}: {cat[m.group(1)]!r}"))
    return out


def scan_tree(files=None) -> List[Site]:
    paths = [JS / f for f in files] if files else sorted(JS.glob("*.js"))
    res: List[Site] = []
    for p in paths:
        res.extend(scan(p))
    res.extend(scan_fragments([p.name for p in paths]))
    return res


def scan_py(files=None) -> List[Site]:
    """Engine messages built with ``+``, ``%`` or ``.format`` instead of ``_i18n.msg``."""
    import ast
    import i18n_extract_py as px
    pkg = ROOT / "unittransfer"
    paths = [pkg / f for f in files] if files else sorted(pkg.glob("*.py"))
    out: List[Site] = []
    for p in paths:
        if p.name in px.SKIP_MODULES:
            continue
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        tree = ast.parse(src)

        def waived(n):
            return any("# " + WAIVER in lines[k] for k in range(max(n.lineno - 3, 0), n.end_lineno))

        _found, built = px.candidates(tree)
        for n in built:
            if isinstance(n, ast.Call) and px._name(n.func)[0] in ("msg", "msgN"):
                continue
            if not waived(n):
                out.append(Site(p.name, n.lineno, "engine", lines[n.lineno - 1].strip()))
        # a message whose English plural is a parameter: x='s' if n == 1 else ''
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and px._name(n.func)[0] == "msg" and not waived(n):
                for kw in n.keywords:
                    seg = ast.get_source_segment(src, kw.value) or ""
                    if ENGINE_PLURAL.search(seg):
                        out.append(Site(p.name, n.lineno, "engine-plural", lines[n.lineno - 1].strip()))
                        break
    out.sort(key=lambda s: (s.file, s.line))
    return out


def main(argv):
    if "--py" in argv:
        files = [Path(a).name for a in argv if not a.startswith("--")]
        sites = scan_py(files or None)
        if "--list" in argv:
            for s in sites:
                print(f"{s.file}:{s.line} [{s.kind}] {s.text[:200]}")
        else:
            b = sum(1 for s in sites if s.kind == "engine")
            print(f"{b} engine messages built with + or %, {len(sites) - b} with a plural in a parameter, "
                  f"in {len({s.file for s in sites})} modules")
        return 0
    lst = "--list" in argv
    files = [a for a in argv if not a.startswith("--")]
    sites = scan_tree([Path(f).name for f in files] or None)
    if lst:
        for s in sites:
            print(f"{s.file}:{s.line} [{s.kind}] {s.text[:200]}")
        return 0
    kinds = ("join", "plural", "fragment")
    by = {}
    for s in sites:
        by.setdefault(s.file, [0, 0, 0])[kinds.index(s.kind)] += 1
    for f, (j, p, g) in sorted(by.items(), key=lambda kv: -sum(kv[1])):
        print(f"{j + p + g:5}  {f:24} join {j:4}  plural {p:4}  fragment {g:4}")
    print(", ".join(f"{sum(v[i] for v in by.values())} {k}s" for i, k in enumerate(kinds))
          + f" in {len(by)} modules")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
