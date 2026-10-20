"""The game's own ``system.log.txt`` in plain words (96e2).

Taken from the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW / M2TW
Campaign Editor's ``gamelog.py`` and ``report.py``, with its author's
permission, and fitted to this toolkit: the result is data for the Health
screen rather than a block of text, and every explanation is a catalogue
string.

Health checks the mod's files against the crashes we know. This reads what the
game itself said on its last run: the crash first (the engine's own line after
a fatal one, else the Script Error just before it), then every error and
warning, grouped so a hundred lines that say the same thing of a hundred units
are one row, the most frequent first. A Script Error names a file and a line;
that line is shown as the mod has it now, since it may have been fixed since.

Read only - nothing is written. The log lines explained were seen in real logs.

**Where the log is.** The game writes it where the ``[log] to =`` line of the
``.cfg`` it started with says, relative to the game folder; failing that, in the
mod's folder or the game's, or a ``logs`` folder under either. The newest one
the mod could have written is read.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import i18n as _i18n

RE_LINE = re.compile(r"^\d\d:\d\d:\d\d(?:\.\d+)?\s+\[([^\]]+)\]\s+\[(fatal|error|warning|warn)\]\s*(.*)$", re.I)
RE_ANY = re.compile(r"^\d\d:\d\d:\d\d(?:\.\d+)?\s+\[")
RE_SCRIPT = re.compile(r"(Script Error|Trigger parsing warning) in (.+?), at line (\d+), column (\d+)", re.I)
RE_LOG_TO = re.compile(r"^\s*to\s*=\s*(.+?)\s*$", re.I | re.M)

#: a log bigger than this is read from its newest part
CAP = 40 * 1024 * 1024


#: (pattern, plain words) - the pattern's groups fill {a}, {b}, {c}
KNOWN: List[Tuple[str, object]] = [
    (r"year_founded", lambda *g: _i18n.msg("eng.gamelog.known_1", "A town's founding year (descr_strat.txt, year_founded) is later than the campaign's start year, and the game stops here. Set it to the start year or earlier.")),
    (r"Character '(.+?)' is placed on an invalid tile", lambda *g: _i18n.msg("eng.gamelog.known_2", "{a} stands on a tile no one may stand on (the sea, a river, mountains, dense forest, off the map), so the game leaves him out. Move him on the campaign map.", a=g[0])),
    (r"unit\((.+?)\) does not match up to the ownership for faction\((.+?)\)", lambda *g: _i18n.msg("eng.gamelog.known_3", "A building lets {b} recruit {a}, but the unit's ownership in export_descr_unit.txt does not name {b}, so the game drops that recruit line. Give {b} the unit in the Unit Editor, or take {b} off the line in Buildings.", a=g[0], b=g[1])),
    (r"invalid tile\((\d+), (\d+)\) for the settlement of (.+?)\.", lambda *g: _i18n.msg("eng.gamelog.known_4", "The town {c} sits on tile {a}, {b}, which nothing can reach (water, a blocked tile or off the map). Armies cannot get to it. Move it on the campaign map, or check the map's size.", a=g[0], b=g[1], c=g[2])),
    (r"Target building level not allowed: (.+?), (\w+) -> (\w+)", lambda *g: _i18n.msg("eng.gamelog.known_5", "When a {b} of {a} turns into a {c} (a city made a castle or back), its buildings change by their chains' convert_to lines, here into a level {a} may not build. Check those levels' requires lines in Buildings, or the convert_to lines.", a=g[0], b=g[1], c=g[2])),
    (r"FactionType: faction not found", lambda *g: _i18n.msg("eng.gamelog.known_6", "A file or a script names a faction this mod does not have. The vanilla prologue scripts do this too (harmless there); otherwise look for a removed or renamed faction in the scripts and descr_strat.txt.")),
    (r"open: (.+?) is missing", lambda *g: _i18n.msg("eng.gamelog.known_7", "The game looked for {a} and did not find it. Often harmless (it falls back to something else); a missing picture shows blank or as a default one.", a=g[0])),
    (r"Cannot find the portrait path: (.+?),", lambda *g: _i18n.msg("eng.gamelog.known_8", "No portrait pictures in {a}, so the game uses the culture's default ones.", a=g[0])),
    (r"Unresolved sprite definition\((.+?)\)", lambda *g: _i18n.msg("eng.gamelog.known_9", "An interface picture {a} is not on its sprite page, so the game draws another in its place (often a faction logo missing for a new faction).", a=g[0])),
    (r"Game selection invalid - is the path '(.*?)' ok", lambda *g: _i18n.msg("eng.gamelog.known_10", "The engine could not tell which game or mod to run: the path it read ({a}) makes no sense, either letters it reads wrong on the way to the game, or the game started away from its own folder. Start the mod with its .bat from the mod's folder.", a=g[0])),
    (r"skeleton\.cpp\(\d+\): adata != 0", lambda *g: _i18n.msg("eng.gamelog.known_11", "A battle skeleton names an animation the game cannot find, in no animation pack and no loose .cas file, so the game stops while it loads the animations, before the menu. Units brought from another mod are the usual cause: copy the missing .cas from that mod, or bring the unit again.")),
    (r"Condition eval: (\w+) needs a (\w+)", lambda *g: _i18n.msg("eng.gamelog.known_12", "A script condition {a} asks about a {b}, but the event it runs on gives none, so the game takes it as false and the trigger never fires. Not a crash.", a=g[0], b=g[1])),
    (r"encountered an unspecified error", lambda *g: _i18n.msg("eng.gamelog.known_13", "The game crashed. The lines just before this one in the log name what it was doing.")),
    (r"DATA: src.(.+?)\((\d+)\)", lambda *g: _i18n.msg("eng.gamelog.known_14", "The game's own check failed in its code ({a}, line {b}) while reading data; the lines before it say what it was reading.", a=g[0], b=g[1])),
    (r"does not exist|not found|unknown", lambda *g: _i18n.msg("eng.gamelog.known_15", "The game met a name it does not know.")),
]
_GENERIC = {13, 14, 15}


def parse(text: str) -> List[Dict]:
    """Every error and warning line: ``{level, area, msg, why, file, line, col}``,
    a Script Error's reason (the untimed lines after it) in ``why``."""
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = RE_LINE.match(line)
        if not m:
            continue
        area, level, msg = m.group(1), m.group(2).lower(), m.group(3).strip()
        e = {"level": {"fatal": "fatal", "error": "error"}.get(level, "warning"), "area": area,
             "msg": msg, "why": "", "file": None, "line": None, "col": None}
        s = RE_SCRIPT.search(msg)
        if s:
            e["file"], e["line"], e["col"] = s.group(2).replace("\\", "/"), int(s.group(3)), int(s.group(4))
            why = []
            for k in range(i + 1, min(i + 6, len(lines))):
                if RE_ANY.match(lines[k]) or not lines[k].strip():
                    break
                why.append(lines[k].strip())
            e["why"] = " ".join(why)
        out.append(e)
    return out


def _known(text: str) -> Tuple[int, Optional[re.Match], object]:
    for n, (pattern, words) in enumerate(KNOWN, 1):
        m = re.search(pattern, text, re.I)
        if m:
            return n, m, words
    return 0, None, None


def explain(text: str, generic: bool = False) -> str:
    """Plain words for a log message, or ''. ``generic``: the group's lines name
    different things, so the names become X, Y and the rows below name them."""
    n, m, words = _known(text)
    if not m:
        return ""
    if generic and m.groups():
        return words(*"XYZW"[:len(m.groups())])
    return words(*m.groups())


def _key(e: Dict) -> Tuple:
    """Entries that say the same thing of different lines or names count as one."""
    s = re.sub(r"\([^)]*\)", "()", e["why"] or e["msg"])
    s = re.sub(r"'[^']*'", "''", s)
    s = re.sub(r"\d+", "N", s)
    return (e["level"], e["file"], s[:120])


ORDER = {"fatal": 0, "error": 1, "warning": 2}


def summary(entries: List[Dict]) -> List[List]:
    """``[entry, count, [(line, reason or the line's own message)]]`` grouped: a
    crash first, then errors, the most frequent first."""
    groups: Dict[Tuple, List] = {}
    for e in entries:
        g = groups.setdefault(_key(e), [e, 0, []])
        g[1] += 1
        if len(g[2]) < 6:
            g[2].append((e["line"], e["why"] or e["msg"]))
    return sorted(groups.values(), key=lambda g: (ORDER[g[0]["level"]], -g[1]))


def mod_line(game, rel: Optional[str], line: Optional[int]) -> Optional[str]:
    """Line ``line`` of the file the log names (relative to the game folder)."""
    if not game or not rel or not line:
        return None
    path = os.path.join(str(game), *rel.split("/"))
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="latin-1") as fh:
            for n, t in enumerate(fh, 1):
                if n == line:
                    return t.rstrip("\r\n")
    except OSError:
        return None
    return None


RE_FATAL = re.compile(r"\[fatal\]|encountered an unspecified error", re.I)
RE_STOP = re.compile(r"ASSERT FAILED|encountered an unspecified error", re.I)
RE_CLOSED = re.compile(r"sprites_close\(\)|libs called display_close", re.I)
RE_CODE = re.compile(r"(?:ASSERT FAILED|ERROR|DATA):\s*src[\\/](\S+?)\((\d+)\)(?::\s*(.*))?", re.I)
RE_PATH = re.compile(r"((?:data/)?[\w\-./\\]+\.(?:txt|tga|dds|texture|cas|mesh|xml|lnt|db|modeldb|spr))", re.I)


def fatal_events(lines: List[str]) -> List[Tuple[int, str, str]]:
    """``(index, the fatal line, its detail)`` - the engine writes what went wrong
    on the lines after a fatal one, before its call stack."""
    out = []
    for i, line in enumerate(lines):
        if not RE_FATAL.search(line):
            continue
        detail = []
        for t in lines[i + 1:i + 6]:
            if not t.strip():
                continue
            if t.lstrip().startswith("at ") or RE_ANY.match(t):
                break
            detail.append(t.strip())
        out.append((i, line.strip(), " ".join(detail)))
    return out


def _words(line: str, detail: str) -> Tuple[str, bool]:
    """A known line's plain words, else the engine's own detail, else its code.
    The bool is True when only the code was there to go on."""
    for text in (detail, line):
        if not text:
            continue
        n, m, _ = _known(text)
        if m and n not in _GENERIC:
            return explain(text), False
    if detail:
        return _i18n.msg("eng.gamelog.the_game_says", "the game says: {detail}", detail=detail[:220]), False
    m = RE_CODE.search(line)
    if m:
        return _i18n.msg("eng.gamelog.check_failed", "the game's own check {file} line {line} failed{x}",
                         file=m.group(1).replace("\\", "/"), line=m.group(2),
                         x=": " + m.group(3) if m.group(3) else ""), True
    return "", False


def verdict(text: str, game=None) -> Optional[Dict]:
    """The crash doctor's word on the last run: ``{stopped, headline, lines,
    serious, file, line, now}``, or None for a log with nothing to say. A stop is
    an ASSERT FAILED or an unspecified error; a fatal line the game went on after
    is serious, not the stop."""
    lines = text.splitlines()
    events = fatal_events(lines)
    stops = [e for e in events if RE_STOP.search(e[1])]
    serious: List[str] = []
    for i, line, detail in events:
        if stops and i == stops[-1][0]:
            continue
        w = _words(line, detail)[0]
        if w and w not in serious:
            serious.append(w)
    closed = any(RE_CLOSED.search(t) for t in lines[-60:])
    if not stops:
        if not events and not closed:
            return None
        head = (_i18n.msg("eng.gamelog.no_crash_closed", "No crash: the game was closed in the usual way.")
                if closed else _i18n.msg("eng.gamelog.no_crash", "No crash in the game's log."))
        return {"stopped": False, "headline": head, "lines": [], "serious": serious[:5],
                "file": None, "line": None, "now": None}
    at, first, detail = stops[-1]
    why, only_code = _words(first, detail)
    rel = line_no = None
    paths = RE_PATH.findall(detail or "")
    if paths:
        rel = paths[0].replace("\\", "/")
    before = [t for t in lines[max(0, at - 30):at] if t.strip()]
    for e in reversed(parse("\n".join(before))):          # a Script Error just before it
        if e["file"]:
            if rel is None:
                rel, line_no = e["file"], e["line"]
            if not why or only_code:
                why = f"{e['file']} line {e['line']}: {(e['why'] or e['msg'])[:200]}"
            break
    head = _i18n.msg("eng.gamelog.stopped", "The game stopped: {why}",
                     why=why or _i18n.msg("eng.gamelog.no_cause", "the log names no cause; the lines before the stop are shown below"))
    return {"stopped": True, "headline": head, "lines": before[-8:] + [first] + ([detail] if detail else []),
            "serious": serious[:5], "file": rel, "line": line_no,
            "now": mod_line(game, rel, line_no) if rel and line_no else None}


# ---------------------------------------------------------------------------
# where the log is


def _root(mod) -> Path:
    """The mod folder from a Mod or a path (a Path's own ``.root`` is its drive)."""
    return Path(mod) if isinstance(mod, (str, Path)) else Path(mod.root)


def _game_of(mod) -> Optional[Path]:
    root = _root(mod)
    if root.parent.name.lower() == "mods":
        return root.parent.parent
    from . import config
    saved = config.get_med2_root()
    return Path(saved) if saved else None


def candidates(mod) -> List[Path]:
    """Every system.log.txt this mod's game could have written, the mod's first."""
    root = _root(mod)
    game = _game_of(mod)
    out: List[Path] = []
    for cfg in sorted(root.glob("*.cfg")) if root.is_dir() else []:
        try:
            text = cfg.read_text(encoding="latin-1", errors="replace")
        except OSError:
            continue
        for to in RE_LOG_TO.findall(text):
            to = to.strip().strip('"')
            for base in ([game] if game else []) + [root]:
                out.append(Path(base) / to)
    for folder in [root] + ([game] if game else []):
        out += [folder / "system.log.txt", folder / "logs" / "system.log.txt"]
    seen, uniq = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def find(mod) -> Optional[Path]:
    """The newest log the mod could have written."""
    have = [p for p in candidates(mod) if p.is_file()]
    return max(have, key=lambda p: p.stat().st_mtime) if have else None


def read(mod, path=None, limit: int = 60) -> Dict:
    """Health's Game log panel: the verdict, the counts and the groups."""
    p = Path(path) if path else find(mod)
    game = _game_of(mod)
    if p is None or not p.is_file():
        return {"found": False, "looked": [str(x) for x in candidates(mod)][:8],
                "howto": _i18n.msg("eng.gamelog.howto", "The game writes system.log.txt only while its log is on; M2EX keeps it on. For the original game, put these lines under [log] in the .cfg the mod starts with, start the game again and do what went wrong:\n[log]\nto = logs/system.log.txt\nlevel = * error")}
    size = p.stat().st_size
    with open(p, "rb") as fh:
        if size > CAP:
            fh.seek(size - CAP)
        data = fh.read()
    text = data.decode("utf-8", "replace")
    entries = parse(text)
    groups = summary(entries)
    out = []
    for e, n, seen in groups[:limit]:
        generic = len({w for _, w in seen}) > 1
        out.append({"level": e["level"], "area": e["area"], "file": e["file"], "msg": e["msg"][:300],
                    "count": n, "plain": explain(e["why"] or e["msg"], generic=generic),
                    "seen": [{"line": ln, "why": (w or "")[:240],
                              "now": (mod_line(game, e["file"], ln) or "")[:240] if e["file"] else ""}
                             for ln, w in seen]})
    errors = sum(1 for e in entries if e["level"] != "warning")
    return {"found": True, "path": str(p), "size": size, "cut": size > CAP,
            "age": int(max(0, time.time() - p.stat().st_mtime)),
            "verdict": verdict(text, game),
            "errors": errors, "warnings": len(entries) - errors,
            "groups": out, "more": max(0, len(groups) - limit)}
