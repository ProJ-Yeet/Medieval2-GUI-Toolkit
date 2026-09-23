"""``descr_animals.txt``, ``descr_standards.txt`` and ``export_descr_advice.txt``
- three small files a mod ships and nothing here edited (Phase 64).

**``descr_animals.txt``** is a record per animal: a ``type`` line, then
``class``, ``model``, ``radius``, an optional ``x_radius``, ``height`` and
``mass``. A unit's ``animal`` line in the EDU names a ``type``, and the
``model`` names a battle model::

    type        wardog
    class       wardog
    model       mount_heavy_horse_marka
    radius      0.75

**``descr_standards.txt``** is how the campaign map draws a banner: the army
and navy flag models with a scale each, six ``banner_*`` rectangles (four
numbers from 0 to 1, left, top, right, bottom, and for the crusade and jihad a
texture after them), and the symbol sheets, under ``factions`` and then
``rebels_factions``.

**``export_descr_advice.txt``** is the advisor: ``AdviceThread`` blocks, each a
``GameArea`` and one or more ``Item`` records (priority, repeats, the title
and text keys from ``text/export_advice.txt``, an optional ``On_display``
script), then ``Trigger`` blocks in the trait-file grammar whose effect line
is ``AdviceThread <name> <score>``. Mods use it for one thing more than the
advisor: ROCSS's only thread launches its background script, the usual way a
campaign script is started.

**Measured on both installed mods before any rule was written.**

* ROCSS declares one animal, ``wardog``, and its EDU's ``Princess`` carries
  ``animal wardogs`` - a name the file does not declare. A warning, not a
  fatal: ROCSS plays, and a princess seldom stands in a battle line.
* DaC declares ``pig`` and ``wardog`` with models (``pig``, ``wardogs``) its
  battle modeldb does not have - and no unit of DaC's has an ``animal`` line,
  so those are notes. A model missing for an animal a unit uses is a warning.
* Both files' own header lists ``wardog`` and ``pig`` as the classes, and
  both mods use only those.
* DaC's ``standard_index`` runs to 30 over 31 factions with seven faction
  sheets. The guides' "four symbols a sheet" would make that a defect, and
  DaC plays, so the sheets are shown and never counted against the index.
* Every symbol sheet in both standards files is on disk, ROCSS's as the
  ``.tga.dds`` it keeps beside a zero-byte ``.tga``, so either counts. DaC's
  two flag models are not loose; the base game packs them.
* DaC's advice file is its six-line header and no thread; ROCSS's thread's
  two text keys are both in its ``export_advice.txt``.

A missing path is a note wherever it can only be the base game's packed file.
Saves are line splices: each file keeps its tabs, comments, line endings and,
for DaC's animals, the missing final newline. Every edit carries the
signature of the copy it was read from, and a file changed since is refused.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb

ANIMALS_REL = "descr_animals.txt"
STANDARDS_REL = "descr_standards.txt"
ADVICE_REL = "export_descr_advice.txt"
ADVICE_TEXT_REL = "text/export_advice.txt"
RELS = (ANIMALS_REL, STANDARDS_REL, ADVICE_REL)
ENCODING = "latin-1"

ANIMAL_KEYS = ("class", "model", "radius", "x_radius", "height", "mass")
ANIMAL_REQUIRED = ("class", "model", "radius", "height", "mass")
ANIMAL_NUMBERS = ("radius", "x_radius", "height", "mass")
#: what the file's own header says the classes are, and all either mod uses
ANIMAL_CLASSES = ("wardog", "pig")

#: the six rectangles on the standard's texture, in the order both mods write them
BANNER_RECTS = ("banner_star", "banner_button", "banner_flag", "banner_sail",
                "banner_crusade", "banner_jihad")
SYMBOL_SECTIONS = ("factions", "rebels_factions")

ADVICE_INTS = ("Verbosity", "Priority", "Threshold", "MaxRepeats", "RepeatInterval")

_NUM = re.compile(r"-?\d+(\.\d*)?|-?\.\d+")


class SideError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _code(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def _tok_sub(line: str, index: int, value: str) -> str:
    """The ``index``-th token of a line's code replaced, everything else kept."""
    code_end = line.find(";") if ";" in line else len(line)
    spans = [m.span() for m in re.finditer(r"\S+", line[:code_end])]
    s, e = spans[index]
    return line[:s] + value + line[e:]


def _rest_sub(line: str, value: str) -> str:
    """Everything after the line's first token replaced - a value that may
    hold spaces (an advice field) - keeping the indent, the gap after the key
    and any comment."""
    code_end = line.find(";") if ";" in line else len(line)
    m = re.match(r"(\s*\S+\s+)(.*?)(\s*)$", line[:code_end])
    if not m:
        key = re.match(r"\s*\S+", line[:code_end]).group(0)
        return key + " " + value + line[code_end:]
    return m.group(1) + value + m.group(3) + line[code_end:]


def _fields_sub(line: str, values: List[str]) -> str:
    """A ``banner_*`` line's comma-separated fields replaced one by one, the
    spacing around each comma kept (``0,       0.67969, 0.19141``)."""
    code_end = line.find(";") if ";" in line else len(line)
    key = re.match(r"\s*\S+", line)
    start = key.end() if key else 0
    spans = []
    for m in re.finditer(r"[^,]+", line[start:code_end]):
        inner = re.search(r"\S(.*\S)?", m.group(0))
        if inner:
            spans.append((start + m.start() + inner.start(), start + m.start() + inner.end()))
    out = line
    for (s, e), v in sorted(zip(spans, values), reverse=True):
        out = out[:s] + v + out[e:]
    return out


def _is_num(v: str) -> bool:
    return bool(_NUM.fullmatch(v))


def _on_disk(data: Path, rel: str) -> bool:
    """``rel`` under ``data/`` - written with or without the ``data/`` the
    standards file puts on its models, and as the ``.dds`` ROCSS keeps beside
    a zero-byte ``.tga``."""
    rel = rel.replace("\\", "/").strip()
    if rel.lower().startswith("data/"):
        rel = rel[5:]
    p = data / rel
    return (p.is_file() and p.stat().st_size > 0) or Path(str(p) + ".dds").is_file()


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


def _read(mod, rel: str) -> str:
    path = Path(mod.data) / rel
    if not path.is_file():
        raise SideError(f"this mod has no {rel}")
    return kb.read_text(path, ENCODING)


# ---------------------------------------------------------------------------
# descr_animals.txt


@dataclass
class Animal:
    name: str
    line: int                                   # the `type` line
    #: key -> (line index, value)
    fields: Dict[str, Tuple[int, str]] = field(default_factory=dict)
    #: (line index, key) of lines this reader does not know
    other: List[Tuple[int, str]] = field(default_factory=list)

    @property
    def end(self) -> int:
        idx = [i for i, _v in self.fields.values()] + [i for i, _k in self.other]
        return max(idx) if idx else self.line


def parse_animals(text: str) -> Tuple[List[str], List[Animal]]:
    lines = text.split("\n")
    out: List[Animal] = []
    for i, line in enumerate(lines):
        w = _code(line).split()
        if not w:
            continue
        k = w[0].lower()
        if k == "type":
            out.append(Animal(" ".join(w[1:]), i))
        elif out:
            if k in ANIMAL_KEYS:
                out[-1].fields[k] = (i, " ".join(w[1:]))
            else:
                out[-1].other.append((i, w[0]))
    return lines, out


def _edu_animals(mod) -> Dict[str, List[str]]:
    """``animal`` name (lower-case) -> the units whose EDU line names it."""
    out: Dict[str, List[str]] = {}
    try:
        units = mod.edu.units
    except Exception:
        return out
    for u in units:
        if u.animal:
            out.setdefault(u.animal.strip().lower(), []).append(u.type)
    return out


def _model_names(mod) -> Optional[set]:
    try:
        return {e.name.lower() for e in mod.modeldb.entries}
    except Exception:
        return None


def check_animals(animals: List[Animal], models: Optional[set],
                  uses: Dict[str, List[str]]) -> List[Dict]:
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for a in animals:
        key = f"animals/{a.name}"
        low = a.name.lower()
        if not a.name:
            out.append(finding("name", "fatal", f"line {a.line + 1}: a `type` line with no name",
                               key, a.line))
        if low in seen:
            out.append(finding("duplicate", "warn", f"{a.name} is declared twice (lines "
                               f"{seen[low] + 1} and {a.line + 1})", key, a.line))
        seen.setdefault(low, a.line)
        for k in ANIMAL_REQUIRED:
            if k not in a.fields:
                out.append(finding("missing", "warn", f"{a.name} has no `{k}` line", key, a.line))
        for i, k in a.other:
            out.append(finding("key", "warn", f"line {i + 1}: {a.name} has a `{k}` line, which "
                               f"is not one of the file's keys ({', '.join(ANIMAL_KEYS)})", key, i))
        for k in ANIMAL_NUMBERS:
            if k in a.fields and not _is_num(a.fields[k][1]):
                i, v = a.fields[k]
                out.append(finding("number", "fatal", f"{a.name}: {k} {v!r} is not a number",
                                   key, i))
        if "class" in a.fields and a.fields["class"][1].lower() not in ANIMAL_CLASSES:
            i, v = a.fields["class"]
            out.append(finding("class", "warn", f"{a.name}: class {v!r} is not one the file's "
                               f"header lists ({', '.join(ANIMAL_CLASSES)})", key, i))
        if models is not None and "model" in a.fields:
            i, v = a.fields["model"]
            if v.lower() not in models:
                users = uses.get(low, [])
                if users:
                    out.append(finding("model", "warn", f"{a.name}'s model {v} is not in the "
                                       f"battle modeldb, and {len(users)} unit(s) bring this "
                                       f"animal to battle ({', '.join(users[:3])})", key, i))
                else:
                    out.append(finding("model", "note", f"{a.name}'s model {v} is not in the "
                                       f"battle modeldb; no unit uses this animal", key, i))
    for name, units in uses.items():
        if name not in seen:
            have = ", ".join(a.name for a in animals) or "nothing"
            out.append(finding("undeclared", "warn",
                               f"{', '.join(units[:3])}{' and more' if len(units) > 3 else ''} "
                               f"carr{'ies' if len(units) == 1 else 'y'} `animal {name}`, and "
                               f"this file does not declare it (it declares {have})",
                               f"animals/{name}", 0))
    return out


# ---------------------------------------------------------------------------
# descr_standards.txt


@dataclass
class StdLine:
    line: int
    key: str
    kind: str              # "scale" | "file" | "rect" | "section" | "symbols" | "other"
    values: List[str]
    section: str = ""      # a `symbols` line's section


def parse_standards(text: str) -> Tuple[List[str], List[StdLine]]:
    lines = text.split("\n")
    out: List[StdLine] = []
    section = ""
    for i, line in enumerate(lines):
        c = _code(line)
        if not c:
            continue
        w = c.split()
        k = w[0].lower()
        if k == "file_scale":
            out.append(StdLine(i, w[0], "scale", w[1:]))
        elif k.startswith("file_"):
            out.append(StdLine(i, w[0], "file", w[1:]))
        elif k.startswith("banner_"):
            rest = c[len(w[0]):]
            out.append(StdLine(i, w[0], "rect", [v.strip() for v in rest.split(",") if v.strip()]))
        elif k in SYMBOL_SECTIONS and len(w) == 1:
            section = k
            out.append(StdLine(i, w[0], "section", []))
        elif k == "symbols":
            out.append(StdLine(i, w[0], "symbols", w[1:], section))
        else:
            out.append(StdLine(i, w[0], "other", w[1:]))
    return lines, out


def check_standards(rows: List[StdLine], data: Path) -> List[Dict]:
    out: List[Dict] = []
    rects = set()
    for r in rows:
        key = f"standards/{r.line}"
        if r.kind == "scale":
            v = r.values[0] if r.values else ""
            if not _is_num(v[:-1] if v.lower().endswith("f") else v):
                out.append(finding("number", "fatal", f"line {r.line + 1}: file_scale {v!r} is "
                                   f"not a number", key, r.line))
        elif r.kind == "file":
            if len(r.values) != 1:
                out.append(finding("spaces", "warn", f"line {r.line + 1}: {r.key} is "
                                   f"{' '.join(r.values) or 'empty'} - one path, and the "
                                   f"file's own comment says it can't have spaces", key, r.line))
            elif not _on_disk(data, r.values[0]):
                out.append(finding("path", "note", f"line {r.line + 1}: {r.values[0]} is not "
                                   f"in the mod; the base game's packs may hold it", key, r.line))
        elif r.kind == "rect":
            rects.add(r.key.lower())
            nums = r.values[:4]
            if len(nums) < 4 or not all(_is_num(v) for v in nums):
                out.append(finding("rect", "fatal", f"line {r.line + 1}: {r.key} is four "
                                   f"numbers, left, top, right, bottom - not "
                                   f"{', '.join(r.values) or 'nothing'}", key, r.line))
                continue
            x0, y0, x1, y1 = (float(v) for v in nums)
            if any(v < 0 or v > 1 for v in (x0, y0, x1, y1)):
                out.append(finding("range", "warn", f"line {r.line + 1}: {r.key} reaches "
                                   f"outside the texture (every number is 0 to 1)", key, r.line))
            if x0 >= x1 or y0 >= y1:
                out.append(finding("empty", "warn", f"line {r.line + 1}: {r.key}'s right or "
                                   f"bottom edge is not past its left or top, so it covers "
                                   f"nothing", key, r.line))
        elif r.kind == "symbols":
            if not r.section:
                out.append(finding("section", "warn", f"line {r.line + 1}: a symbol sheet before "
                                   f"any `factions` line", key, r.line))
            if r.values and not _on_disk(data, r.values[0]):
                out.append(finding("path", "note", f"line {r.line + 1}: {r.values[0]} is not in "
                                   f"the mod; the base game's packs may hold it", key, r.line))
    for k in BANNER_RECTS:
        if rows and k not in rects:
            out.append(finding("absent", "note", f"no {k} rectangle; both installed mods "
                               f"have all six", f"standards/{k}", 0))
    if rows and not any(r.kind == "symbols" and r.section == "factions" for r in rows):
        out.append(finding("sheets", "warn", "no symbol sheet under `factions`, so no faction "
                           "has a symbol to put on its standard", "standards/factions", 0))
    return out


# ---------------------------------------------------------------------------
# export_descr_advice.txt


@dataclass
class AdviceItem:
    name: str
    line: int
    #: (line index, key, value) in file order
    fields: List[Tuple[int, str, str]] = field(default_factory=list)


@dataclass
class Thread:
    name: str
    line: int
    area: str = ""
    area_line: int = -1
    items: List[AdviceItem] = field(default_factory=list)
    end: int = 0           # the last line that is part of it


def parse_advice(text: str):
    """``(lines, threads, trigger file)``. The threads are everything above the
    first ``Trigger``; the triggers are read by :mod:`triggers`, whose grammar
    they are, and an ``AdviceThread`` line inside one is its effect."""
    from . import triggers as tg
    lines = text.split("\n")
    threads: List[Thread] = []
    for i, line in enumerate(lines):
        w = _code(line).split()
        if not w:
            continue
        if w[0] == "Trigger":
            break
        if threads:
            threads[-1].end = i
        if w[0] == "AdviceThread":
            threads.append(Thread(" ".join(w[1:2]), i, end=i))
        elif not threads:
            continue
        elif w[0] == "GameArea":
            threads[-1].area, threads[-1].area_line = " ".join(w[1:]), i
        elif w[0] == "Item":
            threads[-1].items.append(AdviceItem(" ".join(w[1:2]), i))
        elif threads[-1].items:
            threads[-1].items[-1].fields.append((i, w[0], " ".join(w[1:])))
    tf = tg.parse_text(text)
    return lines, threads, tf


def _advice_keys(data: Path) -> Optional[set]:
    from . import stringsbin
    txt = data / ADVICE_TEXT_REL
    if txt.is_file():
        try:
            body = kb.read_text(txt, "utf-16")
            return {m.group(1).lower() for m in
                    re.finditer(r"^[ \t]*\{([^}\r\n]+)\}", body, re.M)}
        except (OSError, UnicodeError):
            pass
    pairs = stringsbin.load_pairs(stringsbin.bin_path_for(txt))
    return {k.lower() for k in pairs} if pairs else None


def check_advice(threads: List[Thread], tf, data: Path) -> List[Dict]:
    from . import triggers as tg
    out: List[Dict] = []
    keys = _advice_keys(data)
    names: Dict[str, int] = {}
    for t in threads:
        k = f"advice/{t.name}"
        if t.name in names:
            out.append(finding("duplicate", "warn", f"thread {t.name} is declared twice (lines "
                               f"{names[t.name] + 1} and {t.line + 1})", k, t.line))
        names.setdefault(t.name, t.line)
        if not t.area:
            out.append(finding("area", "warn", f"thread {t.name} has no GameArea", k, t.line))
        if not t.items:
            out.append(finding("items", "warn", f"thread {t.name} has no Item", k, t.line))
        for it in t.items:
            for i, key, val in it.fields:
                if key in ADVICE_INTS and not re.fullmatch(r"-?\d+", val):
                    out.append(finding("number", "fatal", f"{it.name}: {key} {val!r} is not a "
                                       f"whole number", k, i))
                elif key in ("Title", "Text") and keys is not None and val.lower() not in keys:
                    out.append(finding("text", "warn", f"{it.name}: {key} {val} is not a key in "
                                       f"{ADVICE_TEXT_REL}, so the advisor shows the raw key",
                                       k, i))
                elif key == "On_display" and val and not _on_disk(data, val):
                    out.append(finding("script", "note", f"{it.name}: On_display {val} is not "
                                       f"in the mod; the base game's packs may hold it", k, i))
    fired = set()
    trig_seen: Dict[str, int] = {}
    for trig in tf.triggers:
        k = f"advice/trigger/{trig.name}"
        if trig.name in trig_seen:
            out.append(finding("duplicate", "warn", f"trigger {trig.name} is written twice "
                               f"(lines {trig_seen[trig.name] + 1} and {trig.start + 1})",
                               k, trig.start))
        trig_seen.setdefault(trig.name, trig.start)
        effs = [e for e in trig.effects if e.keyword == "AdviceThread"]
        if not effs:
            out.append(finding("effect", "note", f"trigger {trig.name} fires no AdviceThread",
                               k, trig.start))
        for e in effs:
            nm = e.args[0] if e.args else ""
            fired.add(nm)
            if nm not in names:
                out.append(finding("thread", "warn", f"trigger {trig.name} fires thread "
                                   f"{nm or '(none)'}, which this file does not declare",
                                   k, e.line))
            if len(e.args) > 1 and not re.fullmatch(r"-?\d+", e.args[1]):
                out.append(finding("number", "fatal", f"trigger {trig.name}: the thread's "
                                   f"score {e.args[1]!r} is not a whole number", k, e.line))
        for c in tg.check(trig):
            sev = "note" if c["kind"] == "unknown-condition" else "warn"
            out.append(finding(c["kind"], sev, f"trigger {trig.name}: {c['message']}",
                               k, max(c["line"] - 1, 0)))
    for t in threads:
        if t.name not in fired:
            out.append(finding("unfired", "note", f"no trigger fires thread {t.name}",
                               f"advice/{t.name}", t.line))
    return out


# ---------------------------------------------------------------------------
# the overview


def overview(mod) -> Dict:
    data = Path(mod.data)
    out: Dict = {"animals": None, "standards": None, "advice": None, "findings": [],
                 "sigs": {}}
    try:
        text = _read(mod, ANIMALS_REL)
        _l, animals = parse_animals(text.replace("\r\n", "\n"))
        uses = _edu_animals(mod)
        models = _model_names(mod)
        out["animals"] = [{"name": a.name, "line": a.line + 1,
                           "fields": {k: {"line": i, "value": v} for k, (i, v) in a.fields.items()},
                           "units": uses.get(a.name.lower(), []),
                           "model_known": None if models is None or "model" not in a.fields
                           else a.fields["model"][1].lower() in models}
                          for a in animals]
        out["sigs"][ANIMALS_REL] = _sig(text)
        out["findings"] += check_animals(animals, models, uses)
    except SideError as e:
        out["animals_error"] = e.message
    try:
        text = _read(mod, STANDARDS_REL)
        _l, rows = parse_standards(text.replace("\r\n", "\n"))
        out["standards"] = [{"line": r.line, "key": r.key, "kind": r.kind, "values": r.values,
                             "section": r.section,
                             "on_disk": _on_disk(data, r.values[0])
                             if r.kind in ("file", "symbols") and r.values else None}
                            for r in rows]
        out["sigs"][STANDARDS_REL] = _sig(text)
        out["standard_indexes"] = _standard_indexes(mod)
        out["findings"] += check_standards(rows, data)
    except SideError as e:
        out["standards_error"] = e.message
    try:
        text = _read(mod, ADVICE_REL)
        _l, threads, tf = parse_advice(text.replace("\r\n", "\n"))
        out["advice"] = {
            "threads": [{"name": t.name, "line": t.line + 1, "area": t.area,
                         "items": [{"name": it.name, "line": it.line + 1,
                                    "fields": [{"line": i, "key": k, "value": v}
                                               for i, k, v in it.fields]}
                                   for it in t.items]} for t in threads],
            "triggers": [{"name": g.name, "line": g.start + 1, "event": g.when_to_test,
                          "conditions": [c.raw.strip() for c in g.conditions],
                          "fires": [{"line": e.line, "thread": (e.args or [""])[0],
                                     "score": (e.args[1:2] or [""])[0]}
                                    for e in g.effects if e.keyword == "AdviceThread"]}
                         for g in tf.triggers]}
        out["sigs"][ADVICE_REL] = _sig(text)
        out["findings"] += check_advice(threads, tf, data)
    except SideError as e:
        out["advice_error"] = e.message
    return out


def _standard_indexes(mod) -> Dict:
    """What the roster asks of the symbol sheets - shown, never checked (see
    the module docstring on DaC's index 30)."""
    from . import factions as fa
    try:
        path = fa.path_for(mod)
        recs = fa.parse_file(path).records if path.is_file() else []
    except Exception:
        return {}
    got = [r.get("standard_index") for r in recs]
    nums = [int(v) for v in got if v and re.fullmatch(r"\d+", v.strip())]
    return {"factions": len(recs), "max": max(nums) if nums else None}


# ---------------------------------------------------------------------------
# the save


@dataclass
class SidePlan:
    mod: object = None
    texts: Dict[str, str] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": sorted(self.texts), "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.texts)}


def _splice(lines: List[str], rewrites: Dict[int, str], drops: set,
            inserts: Dict[int, List[str]]) -> List[str]:
    out: List[str] = []
    for i, ln in enumerate(lines):
        if i not in drops:
            out.append(rewrites.get(i, ln))
        out += inserts.get(i, [])
    return out


def _open(p: SidePlan, mod, rel: str, sig: str) -> Optional[Tuple[str, str]]:
    try:
        text = _read(mod, rel)
    except SideError as e:
        p.errors.append(e.message)
        return None
    if sig != _sig(text):
        p.errors.append(f"{rel} changed on disk after it was opened here - reload it")
        return None
    return text, ("\r\n" if "\r\n" in text else "\n")


def _finish(p: SidePlan, rel: str, text: str, nl: str, out: List[str], check) -> None:
    new_text = nl.join(out)
    if new_text == text:
        return
    p.texts[rel] = new_text
    was = {f["message"] for f in check(text)}
    p.warnings += [f["message"] for f in check(new_text)
                   if f["severity"] != "note" and f["message"] not in was]


def _plan_animals(p: SidePlan, mod, body: Dict, sig: str) -> None:
    got = _open(p, mod, ANIMALS_REL, sig)
    if not got:
        return
    text, nl = got
    lines, animals = parse_animals(text.replace("\r\n", "\n"))
    by = {a.name: a for a in animals}
    rewrites: Dict[int, str] = {}
    drops: set = set()
    inserts: Dict[int, List[str]] = {}
    for name, vals in (body.get("edit") or {}).items():
        a = by.get(name)
        if a is None:
            p.errors.append(f"no animal is called {name}")
            continue
        for k, v in vals.items():
            v = str(v).strip()
            if k not in ANIMAL_KEYS:
                p.errors.append(f"{k} is not one of an animal's keys")
                continue
            if not v:
                if k in ANIMAL_REQUIRED:
                    p.errors.append(f"{name}: {k} cannot be blank")
                elif k in a.fields:
                    drops.add(a.fields[k][0])
                    p.changes.append(f"{name}: - {k}")
                continue
            if re.search(r"\s", v):
                p.errors.append(f"{name}: {k} is one word, not {v!r}")
                continue
            if k in ANIMAL_NUMBERS and not _is_num(v):
                p.errors.append(f"{name}: {k} is a number, not {v!r}")
                continue
            if k in a.fields:
                i, cur = a.fields[k]
                if v != cur:
                    rewrites[i] = _tok_sub(lines[i], 1, v)
                    p.changes.append(f"{name}: {k} {cur} -> {v}")
            else:
                base = lines[(a.fields.get("radius") or (a.line, ""))[0]]
                new = _tok_sub(_tok_sub(base, 0, k), 1, v)
                # x_radius goes where the header puts it, after radius
                after = a.fields["radius"][0] if k == "x_radius" and "radius" in a.fields else a.end
                inserts.setdefault(after, []).append(new)
                p.changes.append(f"{name}: + {k} {v}")
    tail: List[str] = []
    for spec in body.get("add") or []:
        name, like = str(spec.get("name") or "").strip(), str(spec.get("like") or "").strip()
        src = by.get(like)
        if src is None:
            p.errors.append(f"there is no animal {like} to copy")
            continue
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            p.errors.append(f"{name!r} is not an animal name (letters, digits, underscore)")
            continue
        if any(a.name.lower() == name.lower() for a in animals):
            p.errors.append(f"{name} is already declared")
            continue
        block = lines[src.line:src.end + 1]
        block[0] = _tok_sub(block[0], 1, name)
        tail += [""] + block
        p.changes.append(f"+ {name}, copied from {like}")
    for name in body.get("remove") or []:
        a = by.get(name)
        if a is None:
            p.errors.append(f"no animal is called {name}")
            continue
        end = a.end + 1
        while end < len(lines) and not lines[end].strip():
            end += 1
        drops |= set(range(a.line, end))
        p.changes.append(f"- {name}")
    if p.errors:
        return
    out = _splice(lines, rewrites, drops, inserts)
    if tail or drops:
        # the file's own last line kept: DaC's ends on `mass 10.0` with no
        # newline, and taking its last animal out must not give it one
        ended = lines[-1] == ""
        while out and not out[-1].strip():
            out.pop()
        out += tail + ([""] if ended else [])
    uses, models = _edu_animals(mod), _model_names(mod)
    _finish(p, ANIMALS_REL, text, nl, out,
            lambda t: check_animals(parse_animals(t.replace("\r\n", "\n"))[1], models, uses))


def _plan_standards(p: SidePlan, mod, body: Dict, sig: str) -> None:
    got = _open(p, mod, STANDARDS_REL, sig)
    if not got:
        return
    text, nl = got
    lines, rows = parse_standards(text.replace("\r\n", "\n"))
    by = {r.line: r for r in rows}
    rewrites: Dict[int, str] = {}
    drops: set = set()
    inserts: Dict[int, List[str]] = {}
    for key, vals in (body.get("lines") or {}).items():
        r = by.get(int(key))
        if r is None or r.kind in ("section", "other"):
            p.errors.append(f"line {int(key) + 1} is not a line this screen edits")
            continue
        vals = [str(v).strip() for v in vals]
        if len(vals) != len(r.values) or any(not v for v in vals):
            p.errors.append(f"line {r.line + 1} takes {len(r.values)} value(s), none blank")
            continue
        if r.kind in ("file", "symbols") and re.search(r"\s", vals[0]):
            p.errors.append(f"line {r.line + 1}: a path cannot have spaces")
            continue
        if r.kind == "scale" and not _is_num(vals[0].rstrip("fF")):
            p.errors.append(f"line {r.line + 1}: file_scale is a number")
            continue
        if r.kind == "rect" and not all(_is_num(v) for v in vals[:4]):
            p.errors.append(f"line {r.line + 1}: the first four values are numbers")
            continue
        if vals == r.values:
            continue
        rewrites[r.line] = (_fields_sub(lines[r.line], vals) if r.kind == "rect"
                            else _tok_sub(lines[r.line], 1, vals[0]))
        p.changes.append(f"{r.key} (line {r.line + 1}): {', '.join(vals)}")
    for spec in body.get("symbols_add") or []:
        sec, path = str(spec.get("section") or ""), str(spec.get("path") or "").strip()
        sheets = [r for r in rows if r.kind == "symbols" and r.section == sec]
        head = next((r for r in rows if r.kind == "section" and r.key.lower() == sec), None)
        if head is None:
            p.errors.append(f"this file has no `{sec}` line")
            continue
        if not path or re.search(r"\s", path):
            p.errors.append("a symbol sheet is one path with no spaces")
            continue
        base = lines[sheets[-1].line] if sheets else "symbols\t\t\t\tx"
        inserts.setdefault(sheets[-1].line if sheets else head.line, []).append(
            _tok_sub(base, 1, path))
        p.changes.append(f"+ {sec}: {path}")
        if not _on_disk(Path(mod.data), path):
            p.warnings.append(f"{path} is not in the mod")
    for key in body.get("symbols_remove") or []:
        r = by.get(int(key))
        if r is None or r.kind != "symbols":
            p.errors.append(f"line {int(key) + 1} is not a symbol sheet")
            continue
        drops.add(r.line)
        p.changes.append(f"- {r.section}: {r.values[0] if r.values else ''}")
        if r.section == "factions":
            p.warnings.append("taking a faction sheet out moves every sheet after it, and "
                              "every standard_index that pointed past it")
    if p.errors:
        return
    data = Path(mod.data)
    _finish(p, STANDARDS_REL, text, nl, _splice(lines, rewrites, drops, inserts),
            lambda t: check_standards(parse_standards(t.replace("\r\n", "\n"))[1], data))


def _plan_advice(p: SidePlan, mod, body: Dict, sig: str) -> None:
    got = _open(p, mod, ADVICE_REL, sig)
    if not got:
        return
    text, nl = got
    lines, threads, tf = parse_advice(text.replace("\r\n", "\n"))
    fields = {i: (it, k, v) for t in threads for it in t.items for i, k, v in it.fields}
    areas = {t.area_line: t for t in threads if t.area_line >= 0}
    fires = {e.line: (g, e) for g in tf.triggers for e in g.effects if e.keyword == "AdviceThread"}
    rewrites: Dict[int, str] = {}
    drops: set = set()
    for key, val in (body.get("fields") or {}).items():
        i, val = int(key), str(val).strip()
        if i in fields:
            it, k, cur = fields[i]
            if k in ADVICE_INTS and not re.fullmatch(r"-?\d+", val):
                p.errors.append(f"{it.name}: {k} is a whole number")
                continue
            if k in ("Title", "Text", "On_display") and (not val or re.search(r"\s", val)):
                p.errors.append(f"{it.name}: {k} is one word")
                continue
            if not cur:
                p.errors.append(f"{it.name}: {k} takes no value")
                continue
            if val != cur:
                rewrites[i] = _rest_sub(lines[i], val)
                p.changes.append(f"{it.name}: {k} {cur} -> {val}")
        elif i in areas:
            if not val or re.search(r"\s", val):
                p.errors.append("GameArea is one word")
                continue
            if val != areas[i].area:
                rewrites[i] = _rest_sub(lines[i], val)
                p.changes.append(f"{areas[i].name}: GameArea {val}")
        elif i in fires:
            g, e = fires[i]
            if not re.fullmatch(r"-?\d+", val) or len(e.args) < 2:
                p.errors.append(f"trigger {g.name}: the score is a whole number")
                continue
            if val != e.args[1]:
                rewrites[i] = _tok_sub(lines[i], 2, val)
                p.changes.append(f"trigger {g.name}: {e.args[0]} scores {val}")
        else:
            p.errors.append(f"line {i + 1} is not a value this screen edits")
    for name in body.get("remove") or []:
        t = next((x for x in threads if x.name == name), None)
        if t is None:
            p.errors.append(f"no thread is called {name}")
            continue
        last = t.line
        for i in range(t.line, t.end + 1):
            if _code(lines[i]):
                last = i
        drops |= set(range(t.line, last + 1))
        gone = 0
        for g in tf.triggers:
            effs = [e for e in g.effects if e.keyword == "AdviceThread"]
            mine = [e for e in effs if (e.args or [""])[0] == name]
            if mine and len(mine) == len(effs):
                end = g.end
                while end < len(lines) and not lines[end].strip():
                    end += 1
                drops |= set(range(g.start, end))
                gone += 1
            else:
                drops |= {e.line for e in mine}
        p.changes.append(f"- thread {name}" + (f", and the {gone} trigger(s) that only fired it"
                                               if gone else ""))
    if p.errors:
        return
    data = Path(mod.data)

    def check(t: str):
        _l, th, f = parse_advice(t.replace("\r\n", "\n"))
        return check_advice(th, f, data)
    _finish(p, ADVICE_REL, text, nl, _splice(lines, rewrites, drops, {}), check)


def plan(mod, body: dict) -> SidePlan:
    """``body["animals"]``: ``{edit: {name: {key: value}}, add: [{name, like}],
    remove: [name]}``. ``body["standards"]``: ``{lines: {line: [values]},
    symbols_add: [{section, path}], symbols_remove: [line]}``.
    ``body["advice"]``: ``{fields: {line: value}, remove: [thread]}``.
    ``body["sigs"]``: the signature each file was read under."""
    p = SidePlan(mod=mod)
    sigs = dict(body.get("sigs") or {})
    if body.get("animals"):
        _plan_animals(p, mod, dict(body["animals"]), str(sigs.get(ANIMALS_REL) or ""))
    if body.get("standards") and not p.errors:
        _plan_standards(p, mod, dict(body["standards"]), str(sigs.get(STANDARDS_REL) or ""))
    if body.get("advice") and not p.errors:
        _plan_advice(p, mod, dict(body["advice"]), str(sigs.get(ADVICE_REL) or ""))
    if not p.texts and not p.errors:
        p.errors.append("nothing to change")
    return p


def apply(p: SidePlan) -> Dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.texts:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    for rel, text in sorted(p.texts.items()):
        target = Path(mod.data) / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, bpath)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", target, f"-> {bpath}")
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "sidefiles", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": ", ".join(sorted(p.texts)), "resolved_type": ", ".join(sorted(p.texts)),
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SIDE   %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
