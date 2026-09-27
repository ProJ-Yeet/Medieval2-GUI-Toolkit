"""Find the interface text in web/js and index.html (Phase 88).

    python dev/checks/i18n_scan.py            # counts per module
    python dev/checks/i18n_scan.py --list     # every item, file:line and text
    python dev/checks/i18n_scan.py --json out.json

An *item* is one run of text a person reads:

* ``html`` - text between tags in a literal that holds markup, together with
  the inline tags and ``${...}`` expressions inside the run (a sentence with a
  ``<code>`` in it is one item, not three);
* ``attr`` - a ``title``, ``placeholder``, ``aria-label``, ``alt`` or
  ``data-tip`` value in such a literal;
* ``prose`` - a literal with no markup that reads as words.

A literal already inside ``tt(...)`` is the catalogue's and is not counted. What
is code - class lists, selectors, URLs, CSS, ids, event names, file names and
format keywords - is not an item. The rules are measured on this tree, not
general.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jslex  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"

#: tags that sit inside a sentence; any other tag ends one
INLINE = {"code", "b", "i", "em", "strong", "kbd", "span", "a", "bdi", "small", "sub", "sup",
          "u", "s", "q", "abbr", "mark", "br", "wbr", "var", "samp", "cite", "dfn"}
#: attributes whose value is read
TEXT_ATTRS = ("title", "placeholder", "aria-label", "alt", "data-tip", "data-title")

TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^<>\"'`\x00]|\"[^\"]*\"|'[^']*'|\x00\d+\x00)*)(/?)>")
ATTR = re.compile(r"(?<![\w-])(" + "|".join(re.escape(a) for a in TEXT_ATTRS) +
                  r")\s*=\s*(\"([^\"]*)\"|'([^']*)')")
ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-f]+|[a-z]+);", re.I)
WORD = re.compile(r"[^\W\d_]{2,}")
EXPR = re.compile(r"\x00(\d+)\x00")


@dataclass
class Item:
    file: str
    line: int
    kind: str          # html | attr | prose
    text: str          # static text, ${} shown as {0}, {1}...
    start: int         # source offsets of the whole run
    end: int


def css_classes() -> Set[str]:
    """Every class name the stylesheet or the scripts set, so a string made of
    them only is a class list and not two English words."""
    names: Set[str] = set()
    html = (WEB / "index.html").read_text(encoding="utf-8")
    style = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.S))
    names.update(re.findall(r"\.([a-zA-Z_][\w-]*)", style))
    for f in list(WEB.glob("js/*.js")) + [WEB / "index.html"]:
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r"class=[\"']([^\"'$]*)", s):
            names.update(m.group(1).split())
        for m in re.finditer(r"classList\.(?:add|remove|toggle|contains)\(\s*'([^']*)'", s):
            names.add(m.group(1))
    return {n for n in names if n}


_CODEISH = [
    re.compile(r"^[\w.-]*$"),                             # one token: an id, a key, a name
    re.compile(r"^[#.\[]?[\w-]+([#.:>\[\] ][\w\-=\"'()\]]*)*$"),  # a selector
    re.compile(r"^/?(api|js|i18n)/"),                     # a URL
    re.compile(r"^[\w-]+:\S"),                           # CSS or a key:value
    re.compile(r"^\s*$"),
]


def looks_like_prose(s: str, classes: Set[str]) -> bool:
    """A literal with no markup that a person reads."""
    t = ENTITY.sub(" ", s).strip()
    if not WORD.search(t):
        return False
    if re.fullmatch(r"[\w.\-/\\:*?]+\.(txt|tga|dds|cas|mesh|json|xml|bin|dat|idx|db|modeldb|"
                    r"sd|png|zip|lua|log|bat|py|js|html|wav|mp3|ogg|bik)", t, re.I):
        return False                                      # a file name
    words = t.split()
    if len(words) == 1:
        w = words[0].strip(".,:;!?…()")
        # a lone word is prose when it is written as one: Capitalised and not
        # CamelCase or ALL_CAPS or snake_case, or ending in a sentence mark
        if re.fullmatch(r"[A-Z][a-z]+(-[a-z]+)?", w) or re.search(r"[.!?…:]$", t) and WORD.search(w):
            return not re.fullmatch(r"[A-Z][a-z]+[A-Z]\w*", w)
        return False
    if all(w in classes for w in words):
        return False                                      # a class list
    if re.fullmatch(r"[\w-]+(\s+[\w-]+)*", t) and all(re.fullmatch(r"[a-z0-9_-]+", w) for w in words) \
            and any("_" in w or "-" in w for w in words):
        return False                                      # keywords, not words
    if any(p.search(t) for p in _CODEISH[2:4]):
        return False
    if re.search(r"[{};]\s*$|^\s*[.#][\w-]+\s*[{,]", t):
        return False                                      # CSS
    return True


def _runs(text: str) -> Iterable[Tuple[int, int, str]]:
    """Split markup into text runs: ``(start, end, kind)``, kind ``html`` for a
    sentence (text, inline tags and expressions) and ``attr`` for a value."""
    for m in TAG.finditer(text):
        for a in ATTR.finditer(m.group(3)):
            g = 3 if a.group(3) is not None else 4
            s0 = m.start(3) + a.start(g)
            yield s0, s0 + len(a.group(g)), "attr"
    # sentences: between block tags
    pos, run0 = 0, None
    bounds = []
    for m in TAG.finditer(text):
        name = m.group(2).lower()
        if name in INLINE:
            continue
        bounds.append((m.start(), m.end()))
    cut = 0
    for b0, b1 in bounds + [(len(text), len(text))]:
        yield cut, b0, "html"
        cut = b1


def _space(text: str, s: int, e: int) -> Tuple[int, int]:
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return s, e


def _tags_in(text: str, s: int, e: int) -> List[re.Match]:
    return [m for m in TAG.finditer(text, s, e)]


def _match_close(tags: List[re.Match], i: int) -> int:
    """Index in ``tags`` of the tag closing ``tags[i]``, or -1."""
    name, depth = tags[i].group(2).lower(), 0
    for j in range(i, len(tags)):
        m = tags[j]
        if m.group(2).lower() != name or m.group(4):
            continue
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return j
    return -1


def _strip_edges(text: str, s: int, e: int) -> Tuple[int, int]:
    """Trim a run to the sentence in it. Space goes, and at either edge so do
    an inline element holding nothing read (an icon, a count, an empty span
    filled later), a tag whose partner is outside the run, and one element
    wrapping the whole run: those are layout, and stay in the code."""
    s, e = _space(text, s, e)
    for _ in range(64):
        s0, e0 = s, e
        tags = _tags_in(text, s, e)
        if not tags:
            break
        first, last = tags[0], tags[-1]
        if first.start() == s:
            if first.group(1) or first.group(4) or first.group(2).lower() in ("br", "wbr"):
                s = first.end()                       # a stray close, or a lone tag
            else:
                j = _match_close(tags, 0)
                if j < 0:
                    s = first.end()                   # opened here, closed outside
                elif not WORD.search(_read(text[first.end():tags[j].start()])):
                    s = tags[j].end()                 # holds nothing read
                elif tags[j].end() == e:
                    s, e = first.end(), tags[j].start()   # wraps the whole run
        elif last.end() == e:
            if last.group(1):
                # a close whose open is outside the run
                opened = [k for k, m in enumerate(tags) if not m.group(1) and not m.group(4)
                          and m.group(2).lower() == last.group(2).lower()]
                if not any(_match_close(tags, k) == len(tags) - 1 for k in opened):
                    e = last.start()
                else:
                    k = next(k for k in opened if _match_close(tags, k) == len(tags) - 1)
                    if not WORD.search(_read(text[tags[k].end():last.start()])):
                        e = tags[k].start()           # a trailing element with nothing read
            elif last.group(4) or last.group(2).lower() in ("br", "wbr"):
                e = last.start()
            else:
                e = last.start()                      # opened at the end, closed outside
        s, e = _space(text, s, e)
        if (s, e) == (s0, e0):
            break
    return s, e


def _read(frag: str) -> str:
    """What a person reads of a fragment: tags and expressions out."""
    t = TAG.sub(" ", frag)
    t = EXPR.sub(" ", t)
    return ENTITY.sub(" ", t)


def scan_source(src: str, rel: str, classes: Set[str]) -> List[Item]:
    items: List[Item] = []
    lits = jslex.lex(src)
    line_of = _line_index(src)
    skip = _in_t_calls(src, lits)
    for lit in lits:
        if lit.start in skip:
            continue
        joined, offs = _join(lit)
        if TAG.search(joined) and re.search(r"<[a-zA-Z/]", joined):
            for s, e, kind in _runs(joined):
                s, e = _strip_edges(joined, s, e)
                frag = joined[s:e]
                if not frag:
                    continue
                read = _read(frag)
                if kind == "html" and not WORD.search(read):
                    continue
                if kind == "attr" and not WORD.search(read):
                    continue
                a, b = offs(s), offs(e)
                items.append(Item(rel, line_of(a), kind, _show(frag), a, b))
        elif lit.kind != "`" or not lit.exprs:
            text = "".join(lit.parts)
            if looks_like_prose(_unescape(text), classes) and not _code_context(src, lit):
                items.append(Item(rel, line_of(lit.start), "prose", text, lit.start, lit.end))
        else:
            if looks_like_prose(_read(joined), classes) and not _code_context(src, lit):
                items.append(Item(rel, line_of(lit.start), "prose", _show(joined), lit.start, lit.end))
    return items


def _unescape(s: str) -> str:
    return s.replace("\\'", "'").replace('\\"', '"').replace("\\n", "\n")


def _show(frag: str) -> str:
    return EXPR.sub(lambda m: "{" + m.group(1) + "}", frag)


def _join(lit: jslex.Lit):
    """The literal's static text with ``\\x00N\\x00`` for each expression, and a
    function from an offset in that text back to the source."""
    if lit.kind != "`":
        base = lit.start + 1
        return lit.parts[0], (lambda o: base + o)
    pieces, marks = [], []   # marks: (joined_offset, source_offset)
    src_at = lit.start + 1
    j = 0
    for k, part in enumerate(lit.parts):
        marks.append((j, src_at))
        pieces.append(part)
        j += len(part)
        if k < len(lit.exprs):
            e0, e1 = lit.exprs[k]
            ph = f"\x00{k}\x00"
            marks.append((j, e0 - 2))
            pieces.append(ph)
            j += len(ph)
            src_at = e1 + 1

    def offs(o: int) -> int:
        best = marks[0]
        for m in marks:
            if m[0] <= o:
                best = m
            else:
                break
        jo, so = best
        # inside a placeholder: snap to its source span edges
        k = next((i for i, (a, _b) in enumerate(marks) if a == jo), 0)
        is_ph = "".join(pieces)[jo:jo + 1] == "\x00"
        if is_ph:
            e = next(x for x in lit.exprs if x[0] - 2 == so)
            return so if o == jo else e[1] + 1
        return so + (o - jo)
    return "".join(pieces), offs


def _line_index(src: str):
    import bisect
    starts = [0] + [i + 1 for i, c in enumerate(src) if c == "\n"]
    return lambda o: bisect.bisect_right(starts, o)


#: calls whose string argument is code, not text
_CODE_CALLS = re.compile(
    r"(getElementById|querySelector(All)?|closest|matches|classList\.\w+|addEventListener|"
    r"removeEventListener|setAttribute|getAttribute|removeAttribute|hasAttribute|createElement|"
    r"api\.get|api\.post|fetch|startsWith|endsWith|includes|indexOf|split|join|replace|"
    r"localStorage\.\w+|dataset|getPropertyValue|setProperty|toggleAttribute|tt|ttA|ttN|console\.\w+|"
    r"new RegExp|RegExp|Error|navUrl|navGo|postMessage|dispatchEvent|CustomEvent)\s*\(\s*$")


def _code_context(src: str, lit: jslex.Lit) -> bool:
    """A literal whose place says it is code: a comparison, an object key, a
    case label, an argument to a DOM or network call."""
    before = src[max(0, lit.start - 80):lit.start]
    after = src[lit.end:lit.end + 40]
    b = before.rstrip()
    if re.search(r"(===|!==|==|!=)\s*$", before) or re.match(r"\s*(===|!==|==|!=)", after):
        return True
    if re.search(r"\bcase\s*$", before):
        return True
    if re.match(r"\s*:", after) and re.search(r"[{,]\s*$", b):
        return True                                       # an object key
    if re.match(r"\s*\]", after) and b.endswith("["):
        return True                                       # obj['key']
    if _CODE_CALLS.search(before):
        return True
    return False


def _in_t_calls(src: str, lits: List[jslex.Lit]) -> Set[int]:
    """Starts of literals that are the first argument of ``t(`` or ``tp(``."""
    out = set()
    for lit in lits:
        if re.search(r"(?<![\w$.])(tt|ttA|ttN)\(\s*$", src[max(0, lit.start - 12):lit.start]):
            out.add(lit.start)
    return out


def scan_html(classes: Set[str]) -> List[Item]:
    """index.html's body: its static text, the same rules as a template."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    b0 = html.index("\n<body") + 1
    b1 = html.index("<script", b0)
    body = html[b0:b1]
    body = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), body, flags=re.S)
    line_of = _line_index(html)
    items = []
    for s, e, kind in _runs(body):
        s, e = _strip_edges(body, s, e)
        frag = body[s:e]
        if frag and WORD.search(_read(frag)) and 'data-i18n' not in body[max(0, s - 200):s].rsplit("<", 1)[-1]:
            items.append(Item("index.html", line_of(b0 + s), kind, frag, b0 + s, b0 + e))
    return items


def scan_all() -> List[Item]:
    classes = css_classes()
    items: List[Item] = []
    for f in sorted(WEB.glob("js/*.js")):
        if f.name == "i18n.js":
            continue
        items += scan_source(f.read_text(encoding="utf-8"), f"js/{f.name}", classes)
    items += scan_html(classes)
    return items


def main(argv):
    items = scan_all()
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(
            json.dumps([asdict(i) for i in items], indent=1, ensure_ascii=False), encoding="utf-8")
    if "--list" in argv:
        for i in items:
            print(f"{i.file}:{i.line} [{i.kind}] {i.text[:140]!r}")
        return
    per = {}
    for i in items:
        per.setdefault(i.file, {"html": 0, "attr": 0, "prose": 0})[i.kind] += 1
    for f, c in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{sum(c.values()):5d}  {f:24s} html {c['html']:4d}  attr {c['attr']:4d}  prose {c['prose']:4d}")
    tot = {k: sum(c[k] for c in per.values()) for k in ("html", "attr", "prose")}
    words = sum(len(WORD.findall(_read(i.text))) for i in items)
    print(f"{len(items)} items in {len(per)} files: html {tot['html']}, attr {tot['attr']}, "
          f"prose {tot['prose']}; about {words} words")


if __name__ == "__main__":
    main(sys.argv[1:])
