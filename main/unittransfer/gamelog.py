"""Reads Medieval II's own system.log.txt (what the game said on its last run)
and turns it into data for the Health screen's "Game log" panel: a crash
verdict, every error and warning grouped so a repeated complaint is one row,
a plain-English explanation where the cause is known, and, for a Script Error,
the line of the mod's file as it is now and where in the toolkit it is fixed.
It only reads; it writes nothing.

Written independently from a description of the behaviour (2026-11-06); the
feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import i18n as _i18n

# A log bigger than this is read from its newest bytes.
CAP = 40 * 1024 * 1024
ORDER = {"fatal": 0, "error": 1, "warning": 2}

_TIMED = re.compile(r"^\s*\d\d:\d\d:\d\d(?:\.\d+)?\s+\[")
_ENTRY = re.compile(r"^\s*\d\d:\d\d:\d\d(?:\.\d+)?\s+\[([^\]]*)\]\s+\[([^\]]*)\]\s*(.*)$")
_SCRIPT = re.compile(
    r"(?:Script Error|Trigger parsing warning) in (.+?), at line (\d+), column (\d+)")
_CODE_PLACE = re.compile(
    r"(?:ASSERT FAILED|ERROR|DATA):\s*src[\\/]([^\s(]+)\((\d+)\)(?::\s*(.*))?")
_PATHISH = re.compile(
    r"[\w\-./\\]+\.(?:txt|tga|dds|texture|cas|mesh|xml|lnt|db|modeldb|spr)\b", re.I)
_CLOSED = ("sprites_close()", "libs called display_close")

# (pattern, generic, message builder). The first match wins.
# Captures fill {a}, {b}, {c} in order.
_SITUATIONS = [
    (r"Script Error in (.+?), at line (\d+), column (\d+)", False, lambda **p: _i18n.msg("eng.gamelog.known_script_error", 'The game could not read line {b} of {a} (at character {c}): a word or a number there is not what the game expects. The line is shown below as the file has it now.', **p)),
    (r"unknown attribute '([^']*)'", False, lambda **p: _i18n.msg("eng.gamelog.known_unknown_attribute", "A unit's attributes line has a word the game does not know: {a}. Check its spelling in the Unit Editor's Attributes, or take it out.", **p)),
    (r"year_founded", False, lambda **p: _i18n.msg("eng.gamelog.known_1", "A town's founding year (descr_strat.txt, year_founded) is later than the campaign's start year, and the game stops here. Set it to the start year or earlier.", **p)),
    (r"Character '([^']*)' is placed on an invalid tile", False, lambda **p: _i18n.msg("eng.gamelog.known_2", '{a} stands on a tile no one may stand on (the sea, a river, mountains, dense forest, off the map), so the game leaves him out. Move him on the campaign map.', **p)),
    (r"unit\(([^)]*)\) does not match up to the ownership for faction\(([^)]*)\)", False, lambda **p: _i18n.msg("eng.gamelog.known_3", "A building lets {b} recruit {a}, but the unit's ownership in export_descr_unit.txt does not name {b}, so the game drops that recruit line. Give {b} the unit in the Unit Editor, or take {b} off the line in Buildings.", **p)),
    (r"invalid tile\((\d+), (\d+)\) for the settlement of (.+?)\.", False, lambda **p: _i18n.msg("eng.gamelog.known_4", "The town {c} sits on tile {a}, {b}, which nothing can reach (water, a blocked tile or off the map). Armies cannot get to it. Move it on the campaign map, or check the map's size.", **p)),
    (r"Target building level not allowed: ([^,]*), (\w+) -> (\w+)", False, lambda **p: _i18n.msg("eng.gamelog.known_5", "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines.", **p)),
    (r"FactionType: faction not found", False, lambda **p: _i18n.msg("eng.gamelog.known_6", 'A file or a script names a faction this mod does not have. The vanilla prologue scripts do this too (harmless there); otherwise look for a removed or renamed faction in the scripts and descr_strat.txt.', **p)),
    (r"open: (.+?) is missing", False, lambda **p: _i18n.msg("eng.gamelog.known_7", 'The game looked for {a} and did not find it. Often harmless (it falls back to something else); a missing picture shows blank or as a default one.', **p)),
    (r"Cannot find the portrait path: ([^,]*),", False, lambda **p: _i18n.msg("eng.gamelog.known_8", "No portrait pictures in {a}, so the game uses the culture's default ones.", **p)),
    (r"Unresolved sprite definition\(([^)]*)\)", False, lambda **p: _i18n.msg("eng.gamelog.known_9", 'An interface picture {a} is not on its sprite page, so the game draws another in its place (often a faction logo missing for a new faction).', **p)),
    (r"Game selection invalid - is the path '([^']*)' ok", False, lambda **p: _i18n.msg("eng.gamelog.known_10", "The engine could not tell which game or mod to run: the path it read ({a}) makes no sense, either letters it reads wrong on the way to the game, or the game started away from its own folder. Start the mod with its .bat from the mod's folder.", **p)),
    (r"skeleton\.cpp\(\d+\): adata != 0", False, lambda **p: _i18n.msg("eng.gamelog.known_11", 'A battle skeleton names an animation the game cannot find, in no animation pack and no loose .cas file, so the game stops while it loads the animations, before the menu. Units brought from another mod are the usual cause: copy the missing .cas from that mod, or bring the unit again.', **p)),
    (r"Condition eval: (\w+) needs a (\w+)", False, lambda **p: _i18n.msg("eng.gamelog.known_12", 'A script condition {a} asks about a {b}, but the event it runs on gives none, so the game takes it as false and the trigger never fires. Not a crash.', **p)),
    (r"encountered an unspecified error", True, lambda **p: _i18n.msg("eng.gamelog.known_13", 'The game crashed. The lines just before this one in the log name what it was doing.', **p)),
    (r"DATA: src.([^(\s]+)\((\d+)\)", True, lambda **p: _i18n.msg("eng.gamelog.known_14", "The game's own check failed in its code ({a}, line {b}) while reading data; the lines before it say what it was reading.", **p)),
    (r"does not exist|not found|unknown", True, lambda **p: _i18n.msg("eng.gamelog.known_15", 'The game met a name it does not know.', **p)),
]
_SITUATIONS = [(re.compile(p, re.I), g, t) for p, g, t in _SITUATIONS]
_LETTERS = "XYZW"


def _situation(text: str):
    for sit in _SITUATIONS:
        m = sit[0].search(text)
        if m:
            return sit, m
    return None


def _timed(line: str) -> bool:
    return bool(_TIMED.match(line))


def parse(text: str) -> List[dict]:
    lines = text.splitlines()
    out = []
    for i, raw in enumerate(lines):
        m = _ENTRY.match(raw)
        if not m:
            continue
        area, level, msg = m.group(1), m.group(2).strip().lower(), m.group(3).strip()
        if level == "warn":
            level = "warning"
        if level not in ORDER:
            continue
        e = {"level": level, "area": area, "msg": msg, "why": "",
             "file": None, "line": None, "col": None}
        s = _SCRIPT.search(msg)
        if s:
            e["file"] = s.group(1).replace("\\", "/")
            e["line"], e["col"] = int(s.group(2)), int(s.group(3))
            extra = []
            for nxt in lines[i + 1:i + 6]:
                if not nxt.strip() or _timed(nxt):
                    break
                extra.append(nxt.strip())
            e["why"] = " ".join(extra)
        out.append(e)
    return out


def explain(text: str, generic: bool = False):
    found = _situation(text)
    if not found:
        return ""
    (_rx, _gen, say), m = found
    parts = [g or "" for g in m.groups()]
    if generic and parts:
        parts = list(_LETTERS[:len(parts)])
    return say(**dict(zip("abc", parts)))


def _names(text: str) -> str:
    found = _situation(text)
    if not found:
        return ""
    return " \u00b7 ".join(g for g in found[1].groups() if g)


def _squash(t: str) -> str:
    t = re.sub(r"\([^)]*\)", "()", t)
    t = re.sub(r"'[^']*'", "''", t)
    t = re.sub(r"\d+", "N", t)
    return t[:120]


def summary(entries: List[dict]) -> list:
    groups: Dict[tuple, list] = {}
    for e in entries:
        said = e["why"] or e["msg"]
        key = (e["level"], e["file"], _squash(said))
        g = groups.get(key)
        if g is None:
            g = groups[key] = [e, 0, []]
        g[1] += 1
        if len(g[2]) < 6:
            g[2].append((e["line"], said))
    return sorted(groups.values(), key=lambda g: (ORDER[g[0]["level"]], -g[1]))


def mod_line(game, rel, line) -> Optional[str]:
    if not game or not rel or not line:
        return None
    try:
        p = Path(game) / rel
        if not p.is_file():
            return None
        with open(p, "r", encoding="latin-1", newline="") as f:
            for n, raw in enumerate(f, 1):
                if n == line:
                    return raw.rstrip("\r\n")
    except OSError:
        pass
    return None


def fix_target(game, rel, line) -> Optional[dict]:
    if not game or not rel:
        return None
    p = Path(game) / rel
    base = os.path.basename(rel).lower()
    if line and p.is_file() and base in ("export_descr_unit.txt", "export_descr_buildings.txt"):
        unit = base == "export_descr_unit.txt"
        rx = re.compile(r"^\s*type\s+(.*)$" if unit else r"^\s*building\s+(\S+)")
        try:
            rows = p.read_text(encoding="latin-1").splitlines()[:line]
        except OSError:
            rows = []
        for row in reversed(rows):
            m = rx.match(row)
            if m:
                return {"kind": "unit" if unit else "building", "name": m.group(1).strip()}
    return {"kind": "file", "name": rel}


def fatal_events(lines: List[str]) -> list:
    out = []
    for i, raw in enumerate(lines):
        low = raw.lower()
        if "[fatal]" not in low and "encountered an unspecified error" not in low:
            continue
        detail = []
        for nxt in lines[i + 1:i + 6]:
            if not nxt.strip():
                continue
            if nxt.lstrip().startswith("at ") or _timed(nxt):
                break
            detail.append(nxt.strip())
        out.append((i, raw.strip(), " ".join(detail)))
    return out


def _plain(line: str, detail: str):
    """Plain words for a fatal event, and whether only the code place was known."""
    for t in (detail, line):
        found = _situation(t) if t else None
        if found and not found[0][1]:
            return explain(t), False
    if detail:
        return _i18n.msg("eng.gamelog.the_game_says", 'the game says: {detail}', detail=detail[:220]), False
    m = _CODE_PLACE.search(line)
    if m:
        extra = ": " + m.group(3).strip() if m.group(3) and m.group(3).strip() else ""
        return _i18n.msg("eng.gamelog.check_failed", "the game's own check {file} line {line} failed{x}",
                         file=m.group(1).replace("\\", "/"), line=m.group(2), x=extra), True
    return "", False


def _is_stop(line: str) -> bool:
    return "ASSERT FAILED" in line or "encountered an unspecified error" in line.lower()


def verdict(text: str, game=None) -> Optional[dict]:
    lines = text.splitlines()
    events = fatal_events(lines)
    stops = [e for e in events if _is_stop(e[1])]
    last = stops[-1] if stops else None

    serious = []
    for e in events:
        if e is last:
            continue
        words = _plain(e[1], e[2])[0]
        if words and words not in serious:
            serious.append(words)
    serious = serious[:5]

    if last is None:
        closed = any(any(c in ln for c in _CLOSED) for ln in lines[-60:])
        if not events and not closed:
            return None
        head = (_i18n.msg("eng.gamelog.no_crash_closed", 'No crash: the game was closed in the usual way.') if closed
                else _i18n.msg("eng.gamelog.no_crash", "No crash in the game's log."))
        return {"stopped": False, "headline": head, "lines": [], "serious": serious,
                "file": None, "line": None, "now": None}

    idx, stop_line, detail = last
    why, only_code = _plain(stop_line, detail)
    m = _PATHISH.search(detail)
    file = m.group(0).replace("\\", "/") if m else None
    line_no = None
    recent = lines[max(0, idx - 30):idx]
    before = [ln for ln in recent if ln.strip()]
    entries = [e for e in parse("\n".join(recent)) if e["file"]]
    if file is None and entries:
        e = entries[-1]
        file, line_no = e["file"], e["line"]
        if not why or only_code:
            why = "%s line %s: %s" % (file, line_no, (e["why"] or e["msg"])[:200])
    col = None
    for e in entries:
        if e["file"] == file and e["line"] == line_no:
            col = e["col"]
    shown = why or _i18n.msg("eng.gamelog.no_cause", 'the log names no cause; the lines before the stop are shown below')
    return {
        "stopped": True,
        "headline": _i18n.msg("eng.gamelog.stopped", 'The game stopped: {why}', why=shown),
        "why": why,
        "lines": before[-8:] + [stop_line] + ([detail] if detail else []),
        "serious": serious,
        "file": file, "line": line_no, "col": col,
        "now": mod_line(game, file, line_no) if file and line_no else None,
        "fix": fix_target(game, file, line_no) if file else None,
    }


# ---- finding the log -------------------------------------------------------

def _dirs(mod) -> Tuple[Path, Optional[Path]]:
    """The mod's folder and the game folder it sits in (or the saved one)."""
    root = Path(mod if isinstance(mod, (str, os.PathLike)) else mod.root)
    if root.parent.name.lower() == "mods":
        return root, root.parent.parent
    from . import config
    saved = config.get_med2_root()
    return root, (Path(saved) if saved else None)


def candidates(mod) -> List[Path]:
    root, game = _dirs(mod)
    found: List[Path] = []
    for cfg in sorted(root.glob("*.cfg"), key=lambda p: p.name):
        try:
            rows = cfg.read_text(encoding="latin-1").splitlines()
        except OSError:
            continue
        for row in rows:
            m = re.match(r"\s*to\s*=\s*(.*?)\s*$", row, re.I)
            if not m:
                continue
            val = m.group(1).strip().strip('"')
            if not val:
                continue
            if game:
                found.append(game / val)
            found.append(root / val)
    for base in (root, game):
        if base:
            found += [base / "system.log.txt", base / "logs" / "system.log.txt"]
    out, seen = [], set()
    for p in found:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def find(mod) -> Optional[Path]:
    best, best_t = None, -1.0
    for p in candidates(mod):
        try:
            if p.is_file() and p.stat().st_mtime > best_t:
                best, best_t = p, p.stat().st_mtime
        except OSError:
            pass
    return best


def _group(g: list, game) -> dict:
    e, count, seen = g
    text = seen[0][1] if seen else (e["why"] or e["msg"])
    varied = len({w for _, w in seen}) > 1
    file = e["file"]
    return {
        "level": e["level"], "area": e["area"], "file": file, "msg": e["msg"][:300],
        "count": count,
        "plain": explain(text, generic=varied),
        "plain_first": explain(text) if varied else "",
        "names": list(dict.fromkeys(n for n in (_names(w) for _, w in seen) if n))[:6],
        "known": _situation(text) is not None,
        "fix": fix_target(game, file, seen[0][0]) if file and seen else None,
        "seen": [{"line": ln, "why": w[:240],
                  "now": (mod_line(game, file, ln) or "")[:240] if file else ""}
                 for ln, w in seen],
    }


def read(mod, path=None, limit: int = 60) -> dict:
    _root, game = _dirs(mod)
    p = Path(path) if path else find(mod)
    if p is None or not p.is_file():
        return {"found": False,
                "looked": [str(c) for c in candidates(mod)[:8]],
                "howto": _i18n.msg("eng.gamelog.howto", 'The game writes system.log.txt only while its log is on; M2EX keeps it on. For the original game, put these lines under [log] in the .cfg the mod starts with, start the game again and do what went wrong:\n[log]\nto = logs/system.log.txt\nlevel = * error')}
    st = p.stat()
    size = st.st_size
    with open(p, "rb") as f:
        if size > CAP:
            f.seek(size - CAP)
        raw = f.read(CAP)
    text = raw.decode("utf-8", errors="replace")
    entries = parse(text)
    groups = summary(entries)
    return {
        "found": True, "path": str(p), "size": size, "cut": size > CAP,
        "age": max(0, int(time.time() - st.st_mtime)),
        "verdict": verdict(text, game),
        "errors": sum(1 for e in entries if e["level"] != "warning"),
        "warnings": sum(1 for e in entries if e["level"] == "warning"),
        "groups": [_group(g, game) for g in groups[:limit]],
        "more": max(0, len(groups) - limit),
    }
