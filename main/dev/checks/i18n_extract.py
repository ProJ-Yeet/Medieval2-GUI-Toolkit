"""Move the interface's strings into web/i18n/en.json (Phase 88b).

    python dev/checks/i18n_extract.py [files...] [--dry] [--no-verify]

With no files, every module under web/js (not i18n.js) and index.html.

Each item :mod:`i18n_scan` finds becomes a catalogue entry with a stable,
namespaced ID (``<module>.<words>``, ``common.<words>`` for a string several
modules share, ``app.<words>`` for index.html), and its place in the code a
call:

* a run of text in markup  ->  ``${tt('id',{name:expr})}`` in the literal
  (a quoted literal holding markup becomes a template literal to take it);
* an attribute value       ->  ``${ttA('id')}``;
* a prose literal          ->  ``tt('id')``, or ``tt('id',{...})`` for a
  template;
* index.html               ->  ``data-i18n="id"`` on the element, or
  ``data-i18n-title`` and friends for an attribute; the English stays in the
  page.

Each ``${...}`` in a run becomes a named parameter (``{count}``, ``{name}``),
named after its expression.

**Verified, not trusted.** Every rewritten literal is evaluated twice in Node,
the old and the new, with each of its expressions replaced by a marker and the
real ``web/js/i18n.js`` loaded on the new catalogue: the two must be the same
string, or the file is not written. Then ``node --check`` on every file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jslex  # noqa: E402
import i18n_scan as scan  # noqa: E402

ROOT = scan.ROOT
WEB = scan.WEB
EN = WEB / "i18n" / "en.json"


# ---------------------------------------------------------------------------
# JS text

_ESC = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def cook(raw: str) -> str:
    """A literal's raw text as the string it makes."""
    out, i, n = [], 0, len(raw)
    while i < n:
        c = raw[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        d = raw[i + 1] if i + 1 < n else ""
        if d in _ESC and not (d == "0" and i + 2 < n and raw[i + 2].isdigit()):
            out.append(_ESC[d]); i += 2
        elif d == "x":
            out.append(chr(int(raw[i + 2:i + 4], 16))); i += 4
        elif d == "u" and raw[i + 2:i + 3] == "{":
            j = raw.index("}", i)
            out.append(chr(int(raw[i + 3:j], 16))); i = j + 1
        elif d == "u":
            out.append(chr(int(raw[i + 2:i + 6], 16))); i += 6
        elif d == "\r" and raw[i + 2:i + 3] == "\n":
            i += 3
        elif d in "\n\r  ":
            i += 2
        else:
            out.append(d); i += 2
    return "".join(out)


def quoted_to_template(raw: str) -> str:
    """A quoted literal's raw text as a template literal's raw text."""
    out, i, n = [], 0, len(raw)
    while i < n:
        c = raw[i]
        if c == "\\":
            pair = raw[i:i + 2]
            out.append(pair[1] if pair in ("\\'", '\\"') else pair)
            i += 2
            continue
        if c == "`":
            out.append("\\`")
        elif c == "$" and raw[i + 1:i + 2] == "{":
            out.append("\\$")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def top_level_comma(expr: str) -> bool:
    depth, q = 0, None
    i = 0
    while i < len(expr):
        c = expr[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            return True
        i += 1
    return False


_STOP = {"esc", "q1", "String", "Number", "Math", "round", "floor", "ceil", "toFixed",
         "toLocaleString", "join", "map", "filter", "trim", "toLowerCase", "toUpperCase",
         "replace", "slice", "substr", "substring", "this", "state", "fmt", "abs", "max", "min",
         "parseInt", "parseFloat", "JSON", "stringify", "length", "size", "fmtNum", "keys",
         "values", "entries", "Object", "Array", "from", "encodeURIComponent", "escAttr",
         "attr", "html", "d", "s", "e", "r", "x", "i", "j", "k", "n", "v", "o", "a", "b", "c",
         "m", "p", "q", "u", "t", "g", "h", "l", "w", "y", "z"}


def param_name(expr: str) -> str:
    e = expr.strip()
    while True:
        m = re.fullmatch(r"(?:esc|q1|String|Number|escAttr|fmtNum)\((.*)\)", e, re.S)
        if not m or top_level_comma(m.group(1)):
            break
        e = m.group(1).strip()
    if re.fullmatch(r"[\w$.]+(\(\))?", e):
        parts = [p for p in e.replace("()", "").split(".") if p]
        if parts and parts[-1] in ("length", "size") and len(parts) > 1:
            base = re.sub(r"\W", "", parts[-2])
            return (base + "_n") if base else "n"
        for p in reversed(parts):
            p = re.sub(r"\W", "", p)
            if p and p not in _STOP and re.fullmatch(r"[A-Za-z_]\w*", p):
                return p
    m = re.search(r"\.(length|size)\s*$", e)
    if m:
        return "n"
    ids = [x for x in re.findall(r"[A-Za-z_]\w*", re.sub(r"(['\"`]).*?\1", "", e))
           if x not in _STOP]
    if len(ids) == 1:
        return ids[0]
    return "x"


def slug(text: str) -> str:
    t = re.sub(r"<[^>]*>", " ", text)
    t = re.sub(r"\{[A-Za-z_]\w*\}", " ", t)
    t = re.sub(r"&[#\w]+;", " ", t)
    t = t.replace("'", "").replace("’", "")
    words = re.findall(r"[a-z0-9]+", t.lower())
    s = "_".join(words[:6])[:48].strip("_")
    return s or "x"


# ---------------------------------------------------------------------------
# what is extracted

@dataclass
class Run:
    kind: str                    # html | attr | prose
    s: int                       # in joined coordinates (prose: whole literal)
    e: int
    en: str = ""                 # the English, with {name}
    params: List[Tuple[str, int]] = field(default_factory=list)   # (name, expr index)
    id: str = ""


@dataclass
class LitEdit:
    lit: jslex.Lit
    joined: str
    runs: List[Run]
    ns: str

    @property
    def start(self):
        return self.lit.start

    @property
    def end(self):
        return self.lit.end


_PH = re.compile(r"\x00(\d+)\x00")
_STYLE = re.compile(r"<(style|script|pre|textarea)\b[^>]*>.*?</\1\s*>", re.S | re.I)
#: in HTML a line break and the indent after it draw as one space (outside
#: <pre> and <textarea>, which are masked): the catalogue holds the one space
_FOLD = re.compile(r"[ \t]*\n\s*")


def joined_of(lit: jslex.Lit) -> str:
    if lit.kind != "`":
        return lit.parts[0]
    out = []
    for k, part in enumerate(lit.parts):
        out.append(part)
        if k < len(lit.exprs):
            out.append(f"\x00{k}\x00")
    return "".join(out)


def _single_ok(read: str) -> bool:
    """A run of one token is text when it is a word, not a code name."""
    w = read.strip()
    if " " in w or "\n" in w:
        return True
    return bool(re.fullmatch(r"[^\W\d_]+(-[^\W\d_]+)?[.,:;!?…]?", w))


def runs_of(lit: jslex.Lit, joined: str, classes) -> List[Run]:
    if lit.kind == "`" and lit.start > 0:
        pass
    has_markup = scan.TAG.search(joined) and re.search(r"<[a-zA-Z/]", joined)
    out: List[Run] = []
    if has_markup:
        # a masked element is a wall at each end and blank between, so the
        # sentence before it and the one after it are each still found
        masked = _STYLE.sub(lambda m: "<hr>" + " " * (len(m.group(0)) - 8) + "<hr>", joined)
        # an HTML comment is a note to the next reader, never on screen (88d)
        masked = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), masked, flags=re.S)
        for s, e, kind in scan._runs(masked):
            s, e = scan._strip_edges(masked, s, e)
            frag = masked[s:e]
            if not frag or "\x01" in frag:
                continue
            read = scan._read(frag)
            no_code = scan._read(re.sub(r"<code>.*?</code>", " ", frag, flags=re.S))
            if not scan.WORD.search(read) or not scan.WORD.search(no_code):
                continue
            if not _single_ok(read):
                continue
            out.append(Run(kind, s, e))
        # a tooltip inside a tag the sentence around it holds goes with the
        # sentence: one entry, the markup and its title together
        spans = [(r.s, r.e) for r in out if r.kind == "html"]
        return [r for r in out if r.kind != "attr" or not any(a <= r.s and r.e <= b for a, b in spans)]
    text = scan._read(joined) if lit.kind == "`" else scan._unescape(joined)
    if scan.looks_like_prose(text, classes) and not _codey(text):
        out.append(Run("prose", 0, len(joined)))
    return out


def _codey(t: str) -> bool:
    """Prose-shaped strings that are code: a font, CSS, a script, a colour."""
    t = t.strip()
    return bool(re.search(r"\d+px\b|===|=>|\btypeof\b|\bfunction\b|&&|\|\||^rgba?\(|"
                          r"^\s*[\w-]+\s*:\s*[\w#-]+\s*;|\bsans-serif\b|\bmonospace\b|"
                          # a call, onclick="edListRemove('a',{x})": a camelCase or dotted name
                          r"^(?:[A-Za-z_$]*[a-z0-9][A-Z][\w$]*|[\w$]+\.[\w$]+)\(.*\)$|"
                          r"^/[\w/-]*\?|[?&]\w+=|"                      # a URL
                          r"^(translate[XYZ]?|scale|rotate|hsla?|calc|url|matrix)\(|"
                          r"^\(\s*\w+-[\w-]+\s*:", t))                  # a media query


def fill_run(run: Run, lit: jslex.Lit, joined: str, src: str) -> None:
    frag = joined[run.s:run.e]
    names: Dict[int, str] = {}
    used = set()
    static_text = _PH.sub(" ", frag)

    def name_for(k: int) -> str:
        if k in names:
            return names[k]
        e0, e1 = lit.exprs[k]
        base = param_name(src[e0:e1])
        nm, i = base, 2
        while nm in used or ("{" + nm + "}") in static_text:
            nm = f"{base}{i}"
            i += 1
        used.add(nm)
        names[k] = nm
        run.params.append((nm, k))
        return nm

    pieces = []
    pos = 0
    for m in _PH.finditer(frag):
        pieces.append(cook(frag[pos:m.start()]))
        pieces.append("{" + name_for(int(m.group(1))) + "}")
        pos = m.end()
    pieces.append(cook(frag[pos:]))
    run.en = "".join(pieces)
    if run.kind == "html":
        run.en = _FOLD.sub(" ", run.en)


# ---------------------------------------------------------------------------
# the rewrite

def is_tagged(src: str, lit: jslex.Lit) -> bool:
    if lit.kind != "`":
        return False
    j = lit.start - 1
    while j >= 0 and src[j] in " \t":
        j -= 1
    if j < 0 or not (src[j].isalnum() or src[j] in "_$)]"):
        return False
    if src[j] in ")]":
        return True
    k = j
    while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
        k -= 1
    return src[k + 1:j + 1] not in jslex._REGEX_WORDS


def collect(src: str, rel: str, ns: str, classes) -> List[LitEdit]:
    lits = jslex.lex(src)
    skip = scan._in_t_calls(src, lits)
    edits = []
    for lit in lits:
        if lit.start in skip or is_tagged(src, lit):
            continue
        joined = joined_of(lit)
        runs = runs_of(lit, joined, classes)
        if runs and runs[0].kind == "prose" and scan._code_context(src, lit):
            continue
        if not runs:
            continue
        for r in runs:
            fill_run(r, lit, joined, src)
        edits.append(LitEdit(lit, joined, runs, ns))
    return edits


def assign_ids(all_edits: Dict[str, List[LitEdit]], existing: Dict[str, str]) -> Dict[str, str]:
    """IDs for every run, reusing an existing entry with the same text in the
    same namespace. A text with no parameters met in three namespaces or more
    goes to ``common``."""
    cat = dict(existing)
    by_text_ns = {}
    for k, v in existing.items():
        if isinstance(v, str):
            by_text_ns[(k.split(".")[0], v)] = k
    spread = defaultdict(set)
    for rel, eds in all_edits.items():
        for ed in eds:
            for r in ed.runs:
                if not r.params:
                    spread[r.en].add(ed.ns)
    common = {t for t, nss in spread.items() if len(nss) >= 3 and len(t) <= 60}
    for rel, eds in all_edits.items():
        for ed in eds:
            for r in ed.runs:
                ns = "common" if r.en in common else ed.ns
                key = (ns, r.en)
                if key in by_text_ns:
                    r.id = by_text_ns[key]
                    continue
                base = f"{ns}.{slug(r.en)}"
                rid, i = base, 2
                while rid in cat and cat[rid] != r.en:
                    rid = f"{base}_{i}"
                    i += 1
                cat[rid] = r.en
                by_text_ns[key] = rid
                r.id = rid
    return cat


class Renderer:
    def __init__(self, src: str, edits: List[LitEdit]):
        self.src = src
        self.edits = sorted(edits, key=lambda e: (e.start, -e.end))

    def render(self, a: int, b: int) -> str:
        out, pos = [], a
        i = 0
        eds = [e for e in self.edits if e.start >= a and e.end <= b]
        top, last_end = [], -1
        for e in eds:
            if e.start >= last_end:
                top.append(e)
                last_end = e.end
        for e in top:
            out.append(self.src[pos:e.start])
            out.append(self.emit(e))
            pos = e.end
        out.append(self.src[pos:b])
        return "".join(out)

    def expr(self, lit: jslex.Lit, k: int) -> str:
        e0, e1 = lit.exprs[k]
        return self.render(e0, e1)

    def call(self, fn: str, run: Run, lit: jslex.Lit) -> str:
        if not run.params:
            return f"{fn}('{run.id}')"
        items = []
        for nm, k in run.params:
            ex = self.expr(lit, k).strip()
            if ex == nm:
                items.append(nm)
            else:
                items.append(f"{nm}:({ex})" if top_level_comma(ex) else f"{nm}:{ex}")
        return f"{fn}('{run.id}',{{{','.join(items)}}})"

    def emit(self, ed: LitEdit) -> str:
        lit, joined = ed.lit, ed.joined
        if len(ed.runs) == 1 and (ed.runs[0].kind == "prose" or
                                  (ed.runs[0].kind == "html" and ed.runs[0].s == 0
                                   and ed.runs[0].e == len(joined))):
            return self.call("tt", ed.runs[0], lit)
        quoted = lit.kind != "`"
        out = ["`"]
        pos = 0

        def static(a, b):
            seg = joined[a:b]
            res, p = [], 0
            for m in _PH.finditer(seg):
                raw = seg[p:m.start()]
                res.append(quoted_to_template(raw) if quoted else raw)
                res.append("${" + self.expr(lit, int(m.group(1))) + "}")
                p = m.end()
            raw = seg[p:]
            res.append(quoted_to_template(raw) if quoted else raw)
            return "".join(res)

        for r in sorted(ed.runs, key=lambda r: r.s):
            out.append(static(pos, r.s))
            out.append("${" + self.call("ttA" if r.kind == "attr" else "tt", r, lit) + "}")
            pos = r.e
        out.append(static(pos, len(joined)))
        out.append("`")
        return "".join(out)

    def test_pair(self, ed: LitEdit) -> Tuple[str, str]:
        """The old and new literal as expressions with every ``${...}`` of the
        literal replaced by a marker string, for Node to compare."""
        lit = ed.lit
        mark = {k: json.dumps(f"\u0001{k}\u0001") for k in range(len(lit.exprs))}
        # old
        if lit.kind == "`":
            old = ["`"]
            for k, part in enumerate(lit.parts):
                old.append(part)
                if k < len(lit.exprs):
                    old.append("${" + mark[k] + "}")
            old.append("`")
            old_s = "".join(old)
        else:
            old_s = self.src[lit.start:lit.end]
        saved = self.expr
        self.expr = lambda l, k: mark[k] if l is lit else saved(l, k)
        try:
            new_s = self.emit(ed)
        finally:
            self.expr = saved
        return old_s, new_s


# ---------------------------------------------------------------------------
# index.html

def apply_html(cat: Dict[str, str], existing_by_text: Dict[str, str]) -> Tuple[str, int]:
    path = WEB / "index.html"
    html = path.read_text(encoding="utf-8")
    b0 = html.index("\n<body") + 1
    b1 = html.index("<script", b0)
    body = html[b0:b1]
    masked = re.sub(r"<!--.*?-->", lambda m: "\x01" * len(m.group(0)), body, flags=re.S)
    inserts: List[Tuple[int, str]] = []       # (offset in body, text to insert)
    wraps: List[Tuple[int, int, str]] = []
    n = 0

    def tag_before(pos: int) -> Optional[re.Match]:
        """The last tag that ends at or before ``pos``."""
        last = None
        for m in scan.TAG.finditer(masked, 0, pos):
            last = m
        return last

    def tag_around(pos: int) -> Optional[re.Match]:
        """The tag ``pos`` is inside (an attribute value's own tag)."""
        i = masked.rfind("<", 0, pos)
        return scan.TAG.match(masked, i) if i >= 0 else None

    def new_id(text: str) -> str:
        key = ("app", text)
        if key in existing_by_text:
            return existing_by_text[key]
        base = f"app.{slug(text)}"
        rid, i = base, 2
        while rid in cat and cat[rid] != text:
            rid = f"{base}_{i}"
            i += 1
        cat[rid] = text
        existing_by_text[key] = rid
        return rid

    for s, e, kind in scan._runs(masked):
        s, e = scan._strip_edges(masked, s, e)
        frag = masked[s:e]
        if not frag or "\x01" in frag or not scan.WORD.search(scan._read(frag)):
            continue
        if kind == "html" and not _single_ok(scan._read(frag)):
            continue
        text = body[s:e]
        if kind == "attr":
            # the attribute's name is just before the value
            m = re.search(r"([\w-]+)\s*=\s*[\"']$", body[:s])
            opener = tag_around(s)
            if not m or not opener:
                continue
            if f"data-i18n-{m.group(1)}=" in opener.group(0):
                continue
            rid = new_id(text)
            inserts.append((opener.start() + 1 + len(opener.group(2)), f' data-i18n-{m.group(1)}="{rid}"'))
            n += 1
            continue
        opener = tag_before(s)
        if opener and not opener.group(1) and "data-i18n=" in opener.group(0) \
                and masked[opener.end():s].strip() == "":
            continue                                   # carried already
        if opener and opener.end() <= s and not opener.group(1) and masked[opener.end():s].strip() == "":
            name = opener.group(2)
            close = re.compile(rf"</{name}\s*>", re.I).search(masked, e)
            if close and masked[e:close.start()].strip() == "" and "data-i18n=" not in opener.group(0):
                rid = new_id(text)
                inserts.append((opener.start() + 1 + len(name), f' data-i18n="{rid}"'))
                n += 1
                continue
        rid = new_id(text)
        wraps.append((s, e, rid))
        n += 1
    edits = [(p, p, t) for p, t in inserts] + [(s, e, f'<span data-i18n="{rid}">' + body[s:e] + "</span>")
                                                for s, e, rid in wraps]
    edits.sort(key=lambda x: x[0], reverse=True)
    for s, e, t in edits:
        body = body[:s] + t + body[e:]
    return html[:b0] + body + html[b1:], n


# ---------------------------------------------------------------------------
# verification

NODE_HARNESS = r"""
const fs=require('fs'),vm=require('vm');
const [,, i18nPath, catPath, pairsPath]=process.argv;
global.window={I18N_BOOT:{lang:'en',dir:'ltr',status:'source',base:'',
  en:JSON.parse(fs.readFileSync(catPath,'utf8')),cat:{},offered:[]}};
global.document={documentElement:{},querySelectorAll:()=>[]};
vm.runInThisContext(fs.readFileSync(i18nPath,'utf8'));
const pairs=JSON.parse(fs.readFileSync(pairsPath,'utf8'));
let bad=0;
const fold=s=>typeof s==='string'?s.replace(/[ \t]*\n\s*/g,' '):s;
for(const [where,a,b,html] of pairs){
  let x,y;
  try{x=vm.runInThisContext('('+a+')');}catch(e){console.log('OLD FAILS',where,e.message,a.slice(0,200));bad++;continue;}
  try{y=vm.runInThisContext('('+b+')');}catch(e){console.log('NEW FAILS',where,e.message,b.slice(0,300));bad++;continue;}
  if(html){x=fold(x);y=fold(y);}
  if(x!==y){bad++;console.log('DIFFERS',where,JSON.stringify(x).slice(0,300),'\n   vs',JSON.stringify(y).slice(0,300));}
}
console.log('checked',pairs.length,'bad',bad);
process.exit(bad?1:0);
"""


def verify(pairs: List[Tuple[str, str, str]], cat: Dict[str, str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="ut_i18n_") as d:
        dp = Path(d)
        (dp / "h.js").write_text(NODE_HARNESS, encoding="utf-8")
        (dp / "cat.json").write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
        (dp / "pairs.json").write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(dp / "h.js"), str(WEB / "js" / "i18n.js"),
                            str(dp / "cat.json"), str(dp / "pairs.json")],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout[-6000:], r.stderr[-3000:])
        return r.returncode == 0


def node_check(path: Path, text: str) -> Optional[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        return None if r.returncode == 0 else r.stderr[-1500:]
    finally:
        Path(tmp).unlink(missing_ok=True)


# ---------------------------------------------------------------------------

def load_cat() -> Dict[str, object]:
    if EN.is_file():
        return json.loads(EN.read_text(encoding="utf-8"))
    return {"_meta": {"lang": "en", "status": "source"}}


def save_cat(cat: Dict[str, object]) -> None:
    meta = cat.pop("_meta", {"lang": "en", "status": "source"})
    ordered = {"_meta": meta}
    for k in sorted(cat):
        ordered[k] = cat[k]
    EN.write_text(json.dumps(ordered, ensure_ascii=False, indent=0).replace("\n", "\n") + "\n",
                  encoding="utf-8")
    cat["_meta"] = meta


def main(argv):
    dry = "--dry" in argv
    noverify = "--no-verify" in argv
    names = [a for a in argv if not a.startswith("--")]
    do_html = not names or "index.html" in names
    files = ([WEB / "js" / (Path(n).stem + ".js") for n in names if n != "index.html"] if names else
             sorted(p for p in (WEB / "js").glob("*.js") if p.name != "i18n.js"))
    classes = scan.css_classes()
    cat = load_cat()
    meta = cat.pop("_meta", None)
    srcs, all_edits = {}, {}
    for f in files:
        src = f.read_text(encoding="utf-8")
        srcs[f] = src
        all_edits[f] = collect(src, f"js/{f.name}", f.stem, classes)
    cat = assign_ids(all_edits, {k: v for k, v in cat.items()})
    pairs, outs = [], {}
    for f, eds in all_edits.items():
        rd = Renderer(srcs[f], eds)
        for ed in eds:
            o, n = rd.test_pair(ed)
            pairs.append((f"{f.name}:{srcs[f].count(chr(10), 0, ed.start) + 1}", o, n,
                          any(r.kind == "html" for r in ed.runs)))
        outs[f] = rd.render(0, len(srcs[f]))
    runs = sum(len(ed.runs) for eds in all_edits.values() for ed in eds)
    print(f"{len(files)} files, {sum(len(e) for e in all_edits.values())} literals, {runs} runs, "
          f"{len(cat)} catalogue entries")
    ok = True
    if not noverify:
        ok = verify(pairs, cat)
    for f, text in outs.items():
        err = node_check(f, text)
        if err:
            ok = False
            print("SYNTAX", f.name, err)
    if not ok:
        print("NOT WRITTEN")
        return 1
    if dry:
        print("dry run: nothing written")
        return 0
    html_n = 0
    if do_html:
        by_text = {(k.split(".")[0], v): k for k, v in cat.items() if isinstance(v, str)}
        new_html, html_n = apply_html(cat, by_text)
        (WEB / "index.html").write_text(new_html, encoding="utf-8")
    for f, text in outs.items():
        if text != srcs[f]:
            f.write_text(text, encoding="utf-8")
    cat["_meta"] = meta or {"lang": "en", "status": "source"}
    save_cat(cat)
    print(f"written; index.html {html_n} places")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
