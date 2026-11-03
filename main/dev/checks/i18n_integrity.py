"""Check literal syntax that a linguistic review must not change.

Run ``python dev/checks/i18n_integrity.py pl``. Work catalogues are supported.
This checks integrity, not whether a translation conveys the English meaning.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n_todo as todo
import i18n_termbase as termbase

TAG = re.compile(r"<(?:/?[A-Za-z][\w:-]*\b|/?\{[A-Za-z_]\w*\})[^>]*>")
CODE = re.compile(r"<code>(.*?)</code>", re.S)
BACKTICK = re.compile(r"`[^`]+`")
GLOB = re.compile(r"\*\.[\w*]+")
UI_ATTRIBUTE = re.compile(r'\b(title|placeholder|aria-label|alt)="[^"]*"')
# Whole messages that were accidentally extracted from code rather than UI.
INTERNAL = re.compile(
    r'(?:(?:data-[\w-]+|aria-label)="[^"]*"(?: (?:data-[\w-]+|aria-label)="[^"]*")*'
    r'|list="[^"]*"|class="val" data-val|on(?:click|change|input)="[^"]*"'
    r'|\[data-cap="[^"]*"\]\s*|(?:factor|level)/\{name\}/\{x\})'
)


def problems(source: str, translated: str) -> list[str]:
    checks = [
        (termbase.FIELD, "placeholder occurrences"),
        (CODE, "literal code contents"),
        (BACKTICK, "inline code"),
        (GLOB, "file-picker filter patterns"),
    ]
    out = [label for pattern, label in checks
           if Counter(pattern.findall(source)) != Counter(pattern.findall(translated))]
    # Native tooltip/accessibility text is prose; every other attribute remains
    # literal. Quote boundaries and attribute names must still match exactly.
    markup = lambda text: Counter(UI_ATTRIBUTE.sub(lambda m: m[1] + '=""', tag)
                                  for tag in TAG.findall(text))
    if markup(source) != markup(translated):
        out.append("literal HTML tags/attributes")
    if INTERNAL.fullmatch(source) and translated != source:
        out.append("internal syntax")
    title = re.fullmatch(r'(disabled |on(?:click|change|input)="[^"]*" )?title="([\s\S]*)"', source)
    if title:
        value = re.fullmatch(r'(disabled |on(?:click|change|input)="[^"]*" )?title="([\s\S]*)"', translated)
        if not value or value[1] != title[1]:
            out.append("title attribute syntax")
    if re.fullmatch(r"[A-Za-z]+", source) and re.search(r"[a-z][A-Z]", source) and translated != source:
        out.append("literal keyword or product name")
    return out


def check(english: dict, catalogue: dict) -> list[str]:
    out = []
    for key, source in english.items():
        if key not in catalogue:
            out.append(f"{key}: missing")
            continue
        for form, translated in termbase.forms_of(catalogue[key]).items():
            original = source if isinstance(source, str) else source.get(form, source["other"])
            out.extend(f"{key}{('/' + form) if form else ''}: {p}"
                       for p in problems(original, translated))
    return out


def main(tag: str) -> int:
    out = check(todo.english(), todo._read(todo.target(tag)))
    print(f"{tag}: {len(out)} integrity problems (not a linguistic certification)")
    for problem in out:
        print("  " + problem)
    return int(bool(out))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1]))
