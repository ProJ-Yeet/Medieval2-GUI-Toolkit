"""Give the engine's messages catalogue IDs (Phase 88b).

    python dev/checks/i18n_extract_py.py [modules...] [--dry]

A message the engine raises or reports keeps its English text for the log,
``server.log`` and ``transfer_cli.py``, and now carries an ID and its
parameters: the literal becomes ``_i18n.msg("eng.<module>.<words>",
"<English with {names}>", name=expr, ...)``, and the English goes into
``web/i18n/en.json`` under that ID. :func:`unittransfer.i18n.msg` fills the
template exactly as the f-string did (``{x}`` is ``format(x, '')``, ``{x!r}``
is passed as ``repr(x)``, a format spec is kept), so the English is the same
string; every rewritten module is parsed again, and the suites that check a
message's words run on the result.

What counts as a message, by where the string stands:

* the first argument of ``raise X(...)``;
* an argument of a call named like a report - ``finding``, ``Finding``,
  ``fail``, ``refuse``, ``warn``, ``note``, ``problem``, ``issue``, and any
  ``...Error`` or ``...Exception`` - but never ``log.*`` or ``logging.*``,
  which stay English;
* the argument of ``.append`` on a list named like a report (``notes``,
  ``errors``, ``warnings``, ``problems``, ``findings``, ``issues``,
  ``messages``, ``reasons``, ``refused``, ``skipped``, ``hints``);
* the value of a report key in a dict literal (``error``, ``message``,
  ``why``, ``note``, ``detail``, ``hint``, ``summary``, ``reason``,
  ``warning``).

and only when it reads as words (two or more, with a space). A string built
with ``+``, ``%`` or ``.format`` is not rewritten and is listed.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n_extract as jx  # noqa: E402

ROOT = jx.ROOT
PKG = ROOT / "unittransfer"
WORD = re.compile(r"[^\W\d_]{2,}")

CALL = re.compile(r"(^|_)(finding|fail|refuse|reject|warn|note|problem|issue)s?$|Finding$|Error$|"
                  r"Exception$|^Problem$|^Issue$|^Refus", re.I)
LISTS = re.compile(r"(^|_)(notes?|errors?|warnings?|warns|problems?|findings?|issues?|messages?|"
                   r"reasons?|refus\w*|skip\w*|hints?|why)$", re.I)
KEYS = {"error", "message", "why", "note", "detail", "hint", "summary", "reason", "warning"}
LOGGERS = {"log", "logger", "logging", "_log", "LOG"}
SKIP_MODULES = {"i18n.py", "__init__.py"}


def _name(func: ast.AST) -> Tuple[str, str]:
    """(callee's last name, the name it is an attribute of)."""
    if isinstance(func, ast.Name):
        return func.id, ""
    if isinstance(func, ast.Attribute):
        base = func.value
        bn = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        return func.attr, bn
    return "", ""


def text_of(n: ast.AST) -> Optional[str]:
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)
    return None


def prose(t: str) -> bool:
    return len(WORD.findall(t)) >= 2 and " " in t.strip()


def candidates(tree: ast.AST) -> Tuple[List[ast.AST], List[ast.AST]]:
    """String nodes to rewrite, and message places holding a built string."""
    found, built = [], []
    seen = set()

    def take(n):
        if n is None or id(n) in seen:
            return
        t = text_of(n)
        if t is not None:
            if prose(t):
                seen.add(id(n))
                found.append(n)
        elif isinstance(n, (ast.BinOp, ast.Call)) and _built_prose(n):
            seen.add(id(n))
            built.append(n)

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
            take(node.exc.args[0])
        elif isinstance(node, ast.Call):
            nm, base = _name(node.func)
            if base in LOGGERS or nm in ("print", "format", "join"):
                continue
            if nm == "append" and isinstance(node.func, ast.Attribute) and node.args:
                tgt = node.func.value
                tn = tgt.id if isinstance(tgt, ast.Name) else (tgt.attr if isinstance(tgt, ast.Attribute) else "")
                if LISTS.search(tn):
                    take(node.args[0])
                continue
            if CALL.search(nm):
                for a in node.args:
                    take(a)
                for kw in node.keywords:
                    if kw.arg in ("message", "msg", "why", "detail", "hint", "reason", "note", "text"):
                        take(kw.value)
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value in KEYS:
                    take(v)
    # a message inside another one's expression goes with the outer one
    spans = [(n.lineno, n.col_offset, n.end_lineno, n.end_col_offset) for n in found]

    def inside(n):
        a = (n.lineno, n.col_offset)
        b = (n.end_lineno, n.end_col_offset)
        return any((s[0], s[1]) <= a and b <= (s[2], s[3]) and s != (*a, *b) for s in spans)
    return [n for n in found if not inside(n)], built


def _built_prose(n: ast.AST) -> bool:
    for c in ast.walk(n):
        t = text_of(c)
        if t and prose(t):
            return True
    return False


_STOP = {"self", "str", "repr", "len", "int", "float", "join", "format", "name", "get", "strip",
         "lower", "upper", "items", "keys", "values", "path", "Path"}


def param_name(n: ast.AST) -> str:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    if isinstance(n, ast.Call):
        fn, _b = _name(n.func)
        if fn == "len" and n.args:
            inner = param_name(n.args[0])
            return (inner + "_n") if inner != "x" else "n"
        if fn in ("str", "repr", "int", "float", "round", "abs", "sorted", "list", "tuple", "set") and n.args:
            return param_name(n.args[0])
        if isinstance(n.func, ast.Attribute) and fn in ("join", "format"):
            return param_name(n.args[0]) if n.args else "x"
        if isinstance(n.func, ast.Attribute):
            return param_name(n.func.value) if fn in _STOP else fn
        return fn or "x"
    if isinstance(n, ast.Subscript):
        s = n.slice
        if isinstance(s, ast.Constant) and isinstance(s.value, str) and re.fullmatch(r"[A-Za-z_]\w*", s.value):
            return s.value
        return param_name(n.value)
    return "x"


def _clean(name: str) -> str:
    name = re.sub(r"\W", "", name).lstrip("_") or "x"
    if name[0].isdigit():
        name = "n" + name
    if name in ("mid", "template", "self"):
        name = name + "_"
    return name


class Rewriter:
    def __init__(self, src: str, mod: str):
        self.src, self.mod = src, mod
        self.lines = src.splitlines(keepends=True)
        self.starts = [0]
        for ln in self.lines:
            self.starts.append(self.starts[-1] + len(ln))

    def off(self, line: int, col: int) -> int:
        """AST (line, UTF-8 byte column) to an index in ``src``."""
        text = self.lines[line - 1]
        return self.starts[line - 1] + len(text.encode("utf-8")[:col].decode("utf-8", "replace"))

    def seg(self, n: ast.AST) -> str:
        return self.src[self.off(n.lineno, n.col_offset):self.off(n.end_lineno, n.end_col_offset)]

    def build(self, n: ast.AST) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
        """``(template, [(name, expr source)])``, or None when it cannot be
        done safely (a format spec with a field in it)."""
        if isinstance(n, ast.Constant):
            return n.value, []
        parts, params, used = [], [], set()
        const = "".join(v.value for v in n.values if isinstance(v, ast.Constant))
        for v in n.values:
            if isinstance(v, ast.Constant):
                parts.append(v.value)
                continue
            assert isinstance(v, ast.FormattedValue)
            spec = ""
            if v.format_spec is not None:
                if any(not isinstance(x, ast.Constant) for x in v.format_spec.values):
                    return None
                spec = "".join(x.value for x in v.format_spec.values)
            expr = self.seg(v.value)
            if "\n" in expr:
                expr = f"({expr})"              # a call's parentheses hold the lines
            if v.conversion == ord("r"):
                expr = f"repr({expr})"
            elif v.conversion == ord("a"):
                expr = f"ascii({expr})"
            elif v.conversion == ord("s"):
                expr = f"str({expr})"
            base = _clean(param_name(v.value))
            nm, i = base, 2
            while nm in used or ("{" + nm) in const:
                nm = f"{base}{i}"
                i += 1
            used.add(nm)
            params.append((nm, expr))
            parts.append("{" + nm + (":" + spec if spec else "") + "}")
        return "".join(parts), params


def run(paths: List[Path], dry: bool) -> int:
    cat = jx.load_cat()
    meta = cat.pop("_meta", None)
    by_text = {(k.rsplit(".", 1)[0], v): k for k, v in cat.items() if isinstance(v, str) and k.startswith("eng.")}
    total, skipped, built_all, changed = 0, 0, [], {}
    for p in paths:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
        found, built = candidates(tree)
        built_all += [(p.name, b.lineno) for b in built]
        if not found:
            continue
        rw = Rewriter(src, p.stem)
        edits = []
        ns = f"eng.{p.stem}"
        for n in found:
            b = rw.build(n)
            if b is None:
                skipped += 1
                continue
            template, params = b
            key = (ns, template)
            if key in by_text:
                mid = by_text[key]
            else:
                base = f"{ns}.{jx.slug(template)}"
                mid, i = base, 2
                while mid in cat and cat[mid] != template:
                    mid = f"{base}_{i}"
                    i += 1
                cat[mid] = template
                by_text[key] = mid
            args = [json.dumps(mid), json.dumps(template, ensure_ascii=False)]
            args += [f"{nm}={ex}" for nm, ex in params]
            new = "_i18n.msg(" + ", ".join(args) + ")"
            edits.append((rw.off(n.lineno, n.col_offset), rw.off(n.end_lineno, n.end_col_offset), new))
            total += 1
        edits.sort(reverse=True)
        out = src
        for a, b, t in edits:
            out = out[:a] + t + out[b:]
        out = add_import(out)
        try:
            ast.parse(out)
        except SyntaxError as e:
            print("SYNTAX", p.name, e)
            return 1
        changed[p] = out
    print(f"{len(paths)} modules, {total} messages in {len(changed)} of them; "
          f"{skipped} skipped (a format spec with a field in it); {len(built_all)} built with + or % "
          "and left in English")
    if dry:
        return 0
    for p, out in changed.items():
        p.write_text(out, encoding="utf-8")
    cat["_meta"] = meta or {"lang": "en", "status": "source"}
    jx.save_cat(cat)
    return 0


def add_import(src: str) -> str:
    if re.search(r"^from \. import i18n as _i18n$", src, re.M):
        return src
    tree = ast.parse(src)
    last = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = node
        elif last is not None:
            break
    lines = src.splitlines(keepends=True)
    at = last.end_lineno if last is not None else 0
    if last is None:
        # after the docstring and `from __future__`
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant):
                at = node.end_lineno
                continue
            break
    lines.insert(at, "from . import i18n as _i18n\n")
    return "".join(lines)


def main(argv):
    names = [a for a in argv if not a.startswith("--")]
    paths = ([PKG / (Path(n).stem + ".py") for n in names] if names else
             sorted(p for p in PKG.glob("*.py") if p.name not in SKIP_MODULES))
    return run(paths, "--dry" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
