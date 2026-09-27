"""A JavaScript lexer just deep enough to find every string a person reads.

Phase 88 (every major language). The UI is ~50k lines of plain scripts, and
nearly all of its text is inside string and template literals, most of those
HTML. This finds them: every ``'...'``, ``"..."`` and ```...``` literal, with a
template's static parts and its ``${...}`` expressions (lexed again, so a
literal inside an expression is found too), skipping comments and regular
expressions. It is not a parser: it knows only what it takes to tell a string
from a regex from a comment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

#: after one of these, a ``/`` starts a regular expression, not a division
_REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")
_REGEX_WORDS = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
                "throw", "case", "do", "else", "yield", "await"}


@dataclass
class Lit:
    """One literal. ``start``/``end`` span the quotes or backticks.

    ``parts`` is the static text: one string for a quoted literal (its raw
    source, escapes as written), and for a template the text between its
    expressions, with ``exprs`` the ``(start, end)`` of each ``${...}`` body."""
    kind: str                      # "'", '"' or '`'
    start: int
    end: int
    parts: List[str] = field(default_factory=list)
    exprs: List[Tuple[int, int]] = field(default_factory=list)
    depth: int = 0                 # how many templates it is nested in


class LexError(ValueError):
    pass


def lex(src: str) -> List[Lit]:
    out: List[Lit] = []
    _scan(src, 0, len(src), out, 0, top=True)
    out.sort(key=lambda l: l.start)
    return out


def _scan(src: str, i: int, stop: int, out: List[Lit], depth: int, top: bool = False,
          brace_end: bool = False) -> int:
    """Lex ``src[i:stop]``. With ``brace_end``, stop at the ``}`` that closes a
    template expression and return its index."""
    n = stop
    prev = ""            # the last significant token, for the regex decision
    braces = 0
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise LexError(f"unclosed comment at {i}")
            i = j + 2
            continue
        if c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    raise LexError(f"newline in a string at {i}")
                j += 1
            out.append(Lit(c, i, j + 1, [src[i + 1:j]], [], depth))
            i = j + 1
            prev = "str"
            continue
        if c == "`":
            i = _template(src, i, n, out, depth)
            prev = "str"
            continue
        if c == "/":
            if prev in _REGEX_WORDS or prev == "" or (len(prev) == 1 and prev in _REGEX_AFTER):
                i = _regex(src, i, n)
                prev = "re"
                continue
            i += 1
            prev = "/"
            continue
        if c == "{":
            braces += 1
        elif c == "}":
            if brace_end and braces == 0:
                return i
            braces -= 1
        if c.isalnum() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            prev = src[i:j]
            i = j
            continue
        if c == "." and prev and prev[0].isdigit():
            i += 1
            continue
        prev = c if c not in ")]" else "id"   # `a) / b` and `a] / b` divide
        i += 1
    if brace_end:
        raise LexError("unclosed ${ in a template")
    return i


def _template(src: str, i: int, n: int, out: List[Lit], depth: int) -> int:
    lit = Lit("`", i, i, [], [], depth)
    out.append(lit)
    j = i + 1
    buf_start = j
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            lit.parts.append(src[buf_start:j])
            lit.end = j + 1
            return j + 1
        if src.startswith("${", j):
            lit.parts.append(src[buf_start:j])
            e0 = j + 2
            e1 = _scan(src, e0, n, out, depth + 1, brace_end=True)
            lit.exprs.append((e0, e1))
            j = e1 + 1
            buf_start = j
            continue
        j += 1
    raise LexError(f"unclosed template at {i}")


def _regex(src: str, i: int, n: int) -> int:
    j = i + 1
    in_class = False
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            raise LexError(f"newline in a regex at {i}")
        if in_class:
            if c == "]":
                in_class = False
        elif c == "[":
            in_class = True
        elif c == "/":
            j += 1
            while j < n and src[j].isalpha():
                j += 1
            return j
        j += 1
    raise LexError(f"unclosed regex at {i}")
