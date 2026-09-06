"""Find UI prose that breaks the toolkit's two writing rules.

The rules: a note in the UI is a lead line plus points through ``docPoints()``,
never prose strung together on dashes; and every sentence starts with a capital.
A dash is fine in a short appositive and fine anywhere in code, so this only
flags the ones doing a full stop's job.

The third rule has no judgement in it at all: the em dash is not used in this
project, anywhere. The whole tree was swept to plain hyphens in 2.1.11, so one
that reappears was typed by something that was not looking rather than chosen,
and it is reported wherever it is - comment, string or doc - not just in UI text.

    python tools/prose_check.py            # a summary and the worst offenders
    python tools/prose_check.py --all      # every hit
    python tools/prose_check.py --file web/js/home.js

It is a heuristic, not a linter: it reads text out of string literals and cannot
know for certain where a sentence ends. Treat the output as a work list, and read
each hit in context before rewriting it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: How long the text after a dash has to be before it stops being an appositive
#: and starts being a clause the dash is holding together.
CLAUSE_CHARS = 55

DASH = re.compile(r"\s[-–]\s")
#: The em dash itself. Not a style opinion and not scoped to UI strings:
#: the character is not written in this project at all, so any one at all is
#: a hit, in whatever kind of line it turns up in.
ANY_EM = re.compile("\u2014")
#: A line of code rather than prose: no point flagging a dash inside a regex, a
#: path or an identifier.
CODE_ISH = re.compile(r"^(//|/\*|\*|rem\s|#)")


#: An inline style, not a sentence. ``'flex:0 0 88px'`` and
#: ``'margin-left:auto;display:flex'`` have spaces and letters like prose does,
#: and they were being stitched onto the title next to them and then reported
#: for opening in lower case - which they are supposed to do.
CSS_DECL = re.compile(r"^[a-z-]+\s*:\s*[^;]+(?:;\s*[a-z-]+\s*:\s*[^;]+)*;?$")

#: `+( … )+` - a value spliced into the middle of a sentence. See :func:`_fold`.
INTERP = re.compile(r"\+\s*\([^()]*\)\s*\+")

#: A value spliced into a sentence: JavaScript writes `${x}`, Python writes
#: `{x}`. Both are a value at render time, and neither is prose - the code
#: inside one was being measured as if it were. `{len(tiles) - ROW_MAX:,}` was
#: reported as a clause-joining dash, and `{getattr(m, 'name', '?')}` as two
#: lower-case sentences, in a module where every message is an f-string.
HOLE = re.compile(r"\$?\{[^{}]*\}")

#: A line that opens a string literal, with Python's optional f/r/b prefix
#: captured so :func:`_fold` can drop it. Python concatenates adjacent literals
#: with nothing between them, which is the same continuation the `+` rule above
#: handles in JavaScript.
ADJACENT = re.compile(r"""^([frbFRB]{0,2})['"`]""")


def _literals(line: str):
    """``[(text, glued)]`` for the quoted runs that look like visible text.

    ``glued`` says the literal continues the one before it: joined by ``+``, or
    by ``+ something +`` where the something is a value being interpolated into
    the middle of a sentence (``'on a '+esc(cat)+' unit the engine…'``). Both
    are halves of one sentence.

    Anything else between them - a ``?``, a ``:``, a comma, markup - means they
    are separate strings that only happen to share a line, and joining those
    invents sentences nobody wrote. The two branches of a ternary were being
    read as one, which is where "the replaced unit - pick one first the base
    unit - pick one" came from.
    """
    out = []
    end = 0
    # `(?:[^'\\\n]|\\.)` rather than `[^'\n]`: an apostrophe inside a
    # single-quoted string is written \' , and stopping at it chopped
    # "the source unit\'s own skeletons come across" into pieces that were then
    # reported for opening in lower case.
    for m in re.finditer(
            r"""(?:'((?:[^'\\\n]|\\.){12,})'"""
            r"""|"((?:[^"\\\n]|\\.){12,})\""""
            r"""|`((?:[^`\\\n]|\\.){12,})`)""", line):
        s = next(g for g in m.groups() if g is not None)
        sep, end = line[end:m.start()], m.end()
        # visible text has spaces and letters; skip selectors, urls, formats
        if " " not in s or not re.search(r"[A-Za-z]{3}", s):
            continue
        if s.startswith(("#", ".", "/", "http")) or "://" in s:
            continue
        if CSS_DECL.match(s.strip()):
            continue
        # joined by `+`; by `+ value +`; or by `+ (expression) +`, which is how a
        # choice is dropped into the middle of a sentence:
        #   '…animates like '+(rep?'the replaced unit':'the base unit')+' instead…'
        # The parentheses are what tell that apart from a bare ternary PICKING
        # between two whole strings, where the separator is just `:`.
        glued = re.fullmatch(r"[\s+]*|\+[^'\"`?:,]*\+|\+\s*\([^()]*\)\s*\+",
                             sep) is not None
        out.append((s, bool(out) and glued))
    return out


def _groups(line: str):
    """The logical strings on one line - ``+``-glued literals joined into one."""
    groups = []
    for s, glued in _literals(line):
        if glued and groups:
            groups[-1] += " " + s
        else:
            groups.append(s)
    return groups


def _fold(text: str):
    """``(first line number, source)`` with ``+`` continuations merged.

    The stitching this module's docstring promises only worked when the ``+``
    was left at the END of a line. This codebase overwhelmingly writes it at the
    START of the continuation instead::

        help:'The weapon’s attack factor - how much damage a blow does. '
          +'A higher number is stored but behaves as 63.'

    and every one of those continuations was being flushed as a string of its
    own and then reported for opening in lower case. 37 of guided.js's 37 hits
    were that, and nothing else. Folding the physical lines into logical ones
    before any literal is read fixes the measurement at the source, rather than
    asking 90 sentences to be rewritten around a quirk of the reader.

    **Python joins its continuations with nothing at all**, which is the same
    construct without the ``+``::

        f"the tile at {x},{y} is land in map_ground_types.tga and "
        f"pure black in map_heights.tga, which the engine reads as sea."

    So a line that STARTS with a quote, directly under one that ENDS with a
    quote, is the rest of the sentence above it. The end-with-a-quote half is
    what keeps this out of JavaScript, where the same shape is a list and the
    line above ends on a comma: 49 of mapcheck.py's 49 hits were this, and the
    two rules together leave it at 4.
    """
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if out and (s.startswith("+") or out[-1][1].rstrip().endswith("+")):
            out[-1] = (out[-1][0], out[-1][1] + " " + s)
            continue
        m = ADJACENT.match(s)
        if m and out and out[-1][1].rstrip().endswith(("'", '"', "`")):
            # the `f` prefix goes with the join, or the separator between the
            # two literals reads as code rather than as a plus
            out[-1] = (out[-1][0], out[-1][1] + " + " + s[m.end(1):])
            continue
        out.append((i, line))
    # A choice dropped into the middle of a sentence is one value, not two
    # strings: in `'animates like '+(rep?'the replaced unit':'the base unit')+'
    # instead…'` the branches are words in a slot, and reading them as literals
    # of their own split the sentence around them into lower-case fragments.
    return [(i, INTERP.sub(" + ", line)) for i, line in out]


def ui_strings(text: str):
    """(line number, string) per LOGICAL string of visible text.

    A long note is written as several literals joined with ``+`` across several
    source lines, and each continuation naturally starts mid-sentence in lower
    case. Reading them line by line reported 589 "lower-case sentence starts",
    almost all of which were the second half of a sentence that began correctly
    on the line above. So the fragments of one expression are stitched back
    together before anything is measured - :func:`_fold` across lines, and
    :func:`_groups` within one - and nothing else is: two literals that merely
    share a line stay two strings.
    """
    for i, line in _fold(text):
        if CODE_ISH.match(line.strip()):
            continue
        for s in _groups(line):
            yield i, s


def clause_dashes(s: str):
    """Dashes with a long stretch of text after them - a full stop's work.

    The holes come out FIRST, not just out of the tail being measured. A hole
    is code, and code has arithmetic in it: ``{len(tiles) - ROW_MAX:,}`` was
    being read as a dash holding two clauses together in a sentence whose only
    dash is inside an expression the reader never sees.
    """
    s = HOLE.sub(" ", s)
    out = []
    for m in DASH.finditer(s):
        after = s[m.end():]
        plain = re.sub(r"<[^>]*>", "", after).strip()
        if len(plain) >= CLAUSE_CHARS:
            out.append(plain[:70])
    return out


def lower_starts(s: str):
    """SENTENCES that open in lower case, ignoring code and template holes.

    A label is not a sentence: "mercs only", "per turn" and "pool" are exactly
    right in lower case, and flagging them buries the real hits. A run of text
    counts as a sentence when it ends in a full stop or is long enough to be
    prose - which is the same line the eye draws.
    """
    plain = re.sub(r"<[^>]*>", " ", s)
    plain = HOLE.sub("", plain).strip()
    if not plain:
        return []
    sentence_ish = plain.endswith((".", "!", "?")) or len(plain) >= 60
    if not sentence_ish:
        return []
    # A LIST is not a sentence either, for the same reason a label is not: the
    # `syn:` lines name a record's value slots in the order the file writes them
    # ("attack, charge, projectile, range, ammo, …") and every one of those
    # words is an EDU term that is lower case by definition. Long enough to look
    # like prose, punctuated like an inventory.
    if plain.count(",") >= 2 and not re.search(r"[.!?]", plain):
        return []
    # The opening of the string, and only that. Scanning after every full stop was
    # tried and abandoned: a sentence may legitimately open with a code identifier
    # ("`no` means a melee weapon", "`spear` also carries a penalty"), an EDU
    # keyword is lower case by definition, and there is no way to tell those from
    # a real slip without reading the line - which is what the work list is for.
    if s.lstrip().startswith("<"):
        return []                      # opens inside markup: <code>keyword</code>
    # Opens on a value, not a word: "${n} pool(s) added…" reads "3 pool(s)
    # added…" on screen. Stripping the hole and then judging the first letter
    # asks a sentence that starts with a number to start with a capital. A bare
    # `{` is the same thing in Python: "{rec.name} owns 16 tiles…" renders as
    # "Aland owns 16 tiles…" and is capitalised by whatever the value is.
    if s.lstrip().startswith(("${", "{")):
        return []
    if not re.match(r"[a-z]{3,}\b", plain) or plain.startswith(("px", "em", "rem")):
        return []
    return [plain[:60]]


#: Text that is a sentence BECAUSE OF WHERE IT IS, however short it is.
#:
#: 17g: every one of the burger menu's fifteen hints started in lower case, and
#: this tool did not say so - `lower_starts` asks a run of text to look like
#: prose first (a full stop, or sixty characters) so that "mercs only" and "per
#: turn" are left alone, and "your mods, and what each one is ready for" is
#: forty-one characters with no full stop. The label was right and the test was
#: right; what was missing is that some text is a sentence by DECLARATION. A
#: `hint:` under a module name, a `help:` under a box and the two lines the nav
#: brand carries are all whole phrases shown to somebody as prose, so they are
#: measured as prose at any length. The value has to contain a space to be
#: one: `note: 'count'` is a severity mapped to a CSS class in two modules,
#: and a single token is never a sentence.
NAMED_PROSE = re.compile(r"""\b(?:hint|help|tip)\s*:\s*['"`]([^'"`]*\s[^'"`]*)['"`]""")
#: The same thing in the page itself: the nav's brand subtitle and the hint
#: under a nav item are written as markup rather than as a field.
NAMED_HTML = re.compile(r"""class="(?:hint|s)"\s*>([^<>{]{4,})<""")


def named_prose(text: str):
    """``(line, string)`` for text that is prose wherever it appears."""
    for i, line in enumerate(text.splitlines(), 1):
        if CODE_ISH.match(line.strip()):
            continue
        for m in NAMED_PROSE.finditer(line):
            yield i, m.group(1)
        for m in NAMED_HTML.finditer(line):
            yield i, m.group(1).strip()


def named_lower(s: str):
    """A declared sentence that opens in lower case. No length test, by design.

    The three guards that are about reading rather than about length still
    apply: markup, a value spliced in at render time, and a first word that is
    not a word at all.
    """
    if s.lstrip().startswith(("<", "${", "{")):
        return []
    plain = HOLE.sub("", re.sub(r"<[^>]*>", " ", s)).strip()
    if not re.match(r"[a-z]{3,}\b", plain):
        return []
    return [plain[:60]]


def scan(paths):
    hits = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        # Whole file, not just its UI strings: a banned character in a comment is
        # as much of a slip as one on screen, and cheaper to catch here than in
        # a review.
        for m in ANY_EM.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(("em", p, line,
                         text[max(0, m.start() - 30):m.start() + 30].replace("\n", " ")))
        said = set()
        for line, s in ui_strings(text):
            for bad in clause_dashes(s):
                hits.append(("dash", p, line, bad))
            for bad in lower_starts(s):
                hits.append(("case", p, line, bad))
                said.add((line, bad))
        # A long hint is caught by both rules and is one fault, so the second
        # one only reports what the first did not.
        for line, s in named_prose(text):
            for bad in named_lower(s):
                if (line, bad) not in said:
                    hits.append(("case", p, line, bad))
    return hits


def main(argv):
    show_all = "--all" in argv
    if "--file" in argv:
        paths = [ROOT / argv[argv.index("--file") + 1]]
    else:
        paths = sorted((ROOT / "web" / "js").glob("*.js")) + [ROOT / "web" / "index.html"]

    hits = scan(paths)
    per_file = {}
    for kind, p, line, text in hits:
        per_file.setdefault(p.name, []).append((kind, line, text))

    dashes = sum(1 for h in hits if h[0] == "dash")
    cases = sum(1 for h in hits if h[0] == "case")
    ems = sum(1 for h in hits if h[0] == "em")
    print(f"{len(hits)} hits in {len(per_file)} files - "
          f"{dashes} clause-joining dashes, {cases} lower-case sentence starts, "
          f"{ems} em dashes\n")
    for name in sorted(per_file, key=lambda n: -len(per_file[n])):
        rows = per_file[name]
        print(f"  {len(rows):3}  {name}")
        if show_all:
            for kind, line, text in rows:
                print(f"        {kind} {name}:{line}  {text}")
    if not show_all:
        print("\n  --all to list every hit, --file <path> for one file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
