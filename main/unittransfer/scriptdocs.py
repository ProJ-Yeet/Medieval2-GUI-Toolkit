"""(96e1) The Pfadfinder-Adam campaign editor's ``enginedocs.py``, taken with its author's
permission; see :mod:`scriptcompat`.

What REX (Rome) and M2EX (Medieval II) offer a script: every console command, campaign-script command, condition
and event, read from the documentation the engines write themselves (the console command dump_docudemon writes
<game>/documentation/console_commands.txt and docudemon_commands / _conditions / _events.txt).

The editor carries the facts of both engines' builds of 2026-10-03 (docs/reference/engine_catalogue.json.gz):
names, parameters, a sample line, where each works, what a condition needs and what an event brings. Not the
descriptions - they are the engines' (and the original games') own words: those are read from the game's own
documentation folder when the engine has written it there, and shown beside the facts.

A module script reaches all of it through the engines' API: game.runConsoleCommand(verb, rest),
game.runScriptCommand(token, rest) (one campaign-script command through the engine's own parser - not the scope ones,
if / while / monitor_event) and game.evaluateCondition(line) (a condition line checked against the event that fired).
Engine events are what events.on(name, fn) takes; their payload carries what the event 'exports'."""

import gzip
import json
import os
import re

KINDS = ("console", "commands", "conditions", "events")
FILES = {"console": "console_commands.txt", "commands": "docudemon_commands.txt",
         "conditions": "docudemon_conditions.txt", "events": "docudemon_events.txt"}
KIND_WORDS = {"console": "console commands", "commands": "campaign-script commands", "conditions": "conditions",
              "events": "events"}
ENGINES = ("rex", "m2ex")
ENGINE_OF_GAME = {"rome": "rex", "medieval2": "m2ex"}
ENGINE_WORDS = {"rex": "REX (Rome)", "m2ex": "M2EX (Medieval II)"}
CATALOGUE_FILE = "engine_catalogue.json.gz"
DUMP_HOW = ("The engine writes its own descriptions: start the game with REX / M2EX, open the console (the ~ key) "
            "and type dump_docudemon - it makes a 'documentation' folder in the game's folder, which the editor "
            "then reads.")


class Entry:
    """One command / condition / event. params: the parameters in the engine's words; sample: a line as written;
    where: campaign, battle or both (console: its availability); needs: what a condition needs from the event
    (trigger requirements) or what an event brings (exports); works: False when the engine marks it not implemented;
    desc: the engine's description, '' when the game has no documentation folder."""
    __slots__ = ("kind", "name", "params", "sample", "where", "needs", "works", "desc", "engines")

    def __init__(self, kind, name, params="", sample="", where="", needs=(), works=True, desc="", engines=()):
        self.kind, self.name, self.params, self.sample, self.where = kind, name, params, sample, where
        self.needs, self.works, self.desc, self.engines = list(needs), works, desc, list(engines)

    def facts(self):
        return [self.name, self.params, self.sample, self.where, self.needs, self.works]

    def runnable(self):
        """Can a module run / test it: a console command for the campaign, a campaign-script command that is one line
        (not 'if ... end_if', 'monitor_event ... end_monitor'), anything the engine has implemented."""
        if not self.works:
            return False
        if self.kind == "console":
            return "campaign" in self.where.replace("campaign_ed", "")
        if self.kind == "commands":
            return " " not in self.name and self.name not in SCOPE_COMMANDS
        if self.kind == "conditions":
            return self.where.lower() != "battle"
        return True

    def line(self):
        """What to put in the box when it is picked: its sample, else its name."""
        return (self.sample or "").strip() or self.name


# the flow of a campaign_script.txt (blocks, jumps, waits) - one line of it alone means nothing in a module, and
# runScriptCommand refuses the block openers
SCOPE_COMMANDS = {"if", "if_not", "while", "while_fast", "while_yield", "monitor_event", "monitor_conditions", "else",
                  "else_if", "end_if", "end_while", "end_monitor", "terminate_monitor", "script", "end_script",
                  "terminate_script", "goto", "label", "set_label", "break", "return", "wait", "campaign_wait",
                  "wait_monitors"}


# ---------------------------------------------------------------------------
# Reading the engines' own files
# ---------------------------------------------------------------------------
RE_CONSOLE = re.compile(r"^([a-z_0-9]+)[ \t]*\n[ \t]+Availability:[ \t]*([^\n]*)\n[ \t]+Usage:[ \t]*([^\n]*)", re.M)
RE_FIELD = re.compile(r"^([A-Z][A-Za-z ]*?):[ \t]*(.*)$")


def parse(kind, text):
    """[Entry] of one of the engine's files."""
    text = text.replace("\r", "")
    if kind == "console":
        out = []
        for m in RE_CONSOLE.finditer(text):
            name, where, usage = m.group(1), m.group(2).strip(), m.group(3).strip()
            sig, desc = _split_usage(usage)
            params = sig[len(name):].strip() if sig.startswith(name) else sig
            out.append(Entry(kind, name, params, sig, where, (), True, desc.strip()))
        return out
    out = []
    for block in re.split(r"\n-{10,}[ \t]*\n", text):
        f, last = {}, None
        for line in block.split("\n"):
            m = RE_FIELD.match(line)
            if m and m.group(1) in ("Identifier", "Parameters", "Description", "Sample use", "Class", "Implemented",
                                    "Trigger requirements", "Battle or Strat", "Event", "Exports"):
                last = m.group(1)
                f[last] = m.group(2).strip()
            elif last and line.strip():
                f[last] = (f[last] + " " + line.strip()).strip()
        name = f.get("Identifier", "").strip()
        if not name:
            continue
        works = f.get("Implemented", "Yes").strip().lower() != "no"
        if kind == "events":
            needs = [x.strip() for x in f.get("Exports", "").split(",") if x.strip() and x.strip() != "none"]
            out.append(Entry(kind, name, "", "", "", needs, works, f.get("Event", "")))
        elif kind == "conditions":
            needs = [x.strip() for x in f.get("Trigger requirements", "").split(",") if x.strip()]
            params = f.get("Parameters", "")
            out.append(Entry(kind, name, "" if params.lower() == "none" else params, f.get("Sample use", ""),
                             f.get("Battle or Strat", ""), needs, works, f.get("Description", "")))
        else:
            out.append(Entry(kind, name, f.get("Parameters", ""), f.get("Sample use", ""), "", (), works,
                             f.get("Description", "")))
    return out


def _split_usage(usage):
    """'add_money <opt:faction_type> <amount> : adds ...' -> (the line's form, the words after it): the first ':'
    outside <> and [] that a space follows ends the form ('<opt:level>: gives ...' too)."""
    depth = 0
    for i, ch in enumerate(usage):
        if ch in "<[":
            depth += 1
        elif ch in ">]":
            depth = max(0, depth - 1)
        elif ch == ":" and depth == 0 and (i + 1 == len(usage) or usage[i + 1] == " "):
            return usage[:i].strip(), usage[i + 1:].strip()
    return usage.strip(), ""


def read_dir(folder):
    """{kind: {name: Entry}} of a documentation folder, or None when it holds none of the files."""
    if not folder or not os.path.isdir(folder):
        return None
    low = {n.lower(): n for n in os.listdir(folder)}
    out, found = {}, False
    for kind, fname in FILES.items():
        out[kind] = {}
        if fname not in low:
            continue
        found = True
        with open(os.path.join(folder, low[fname]), "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        for e in parse(kind, text):
            out[kind].setdefault(e.name, e)
    return out if found else None


def facts(rex_dir, m2ex_dir):
    """The catalogue the editor carries: {'made': ..., 'rex': {kind: [facts]}, 'm2ex': ...} - no descriptions."""
    out = {"made": "facts of REX's and M2EX's own documentation (dump_docudemon), builds of 2026-10-04; the "
                   "descriptions are read from the game's documentation folder"}
    for engine, folder in (("rex", rex_dir), ("m2ex", m2ex_dir)):
        docs = read_dir(folder) or {}
        out[engine] = {kind: [e.facts() for e in docs.get(kind, {}).values()] for kind in KINDS}
    return out


def write_catalogue(rex_dir, m2ex_dir, path):
    data = json.dumps(facts(rex_dir, m2ex_dir), ensure_ascii=True, separators=(",", ":")).encode("ascii")
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as fh:   # the same bytes each run
        fh.write(data)
    return path


# ---------------------------------------------------------------------------
# What the editor offers
# ---------------------------------------------------------------------------
_BUILTIN = {}
_GAME_DOCS = {}


def builtin():
    """{engine: {kind: {name: Entry}}} of the catalogue the editor carries (empty when the file is missing)."""
    if "data" not in _BUILTIN:
        from .scriptcompat import reference_dir
        p = os.path.join(reference_dir(), CATALOGUE_FILE)
        data = {}
        try:
            with gzip.open(p, "rb") as fh:
                data = json.loads(fh.read().decode("ascii"))
        except (OSError, ValueError):
            data = {}
        out = {}
        for engine in ENGINES:
            out[engine] = {}
            for kind in KINDS:
                out[engine][kind] = {r[0]: Entry(kind, *r, engines=[engine]) for r in data.get(engine, {}).get(kind, [])}
        _BUILTIN["data"] = out
    return _BUILTIN["data"]


def doc_dir(mod):
    """The game's documentation folder the engine wrote (dump_docudemon), or None."""
    if mod is None:
        return None
    try:
        from .scriptcompat import game_of
        game = game_of(mod.data)
    except Exception:
        return None
    for d in (os.path.join(game, "documentation"), os.path.join(os.path.dirname(os.path.abspath(mod.data)),
                                                                "documentation")) if game else ():
        if os.path.isdir(d):
            return d
    return None


def game_docs(mod):
    """{kind: {name: Entry}} the loaded game's engine wrote, with its descriptions; None when it wrote none."""
    d = doc_dir(mod)
    if not d:
        return None
    try:
        stamp = tuple(os.path.getmtime(os.path.join(d, n)) for n in sorted(os.listdir(d)))
    except OSError:
        stamp = None
    got = _GAME_DOCS.get(d)
    if got is None or got[0] != stamp:
        got = _GAME_DOCS[d] = (stamp, read_dir(d))
    return got[1]


_CAT = {}


def catalogue(game="both", mod=None):
    """The catalogue below, kept while the game's documentation stays the same."""
    have = game_docs(mod)
    key = (game, id(have), doc_dir(mod) if have else None, _engine_of(mod))
    if key not in _CAT:
        _CAT.clear() if len(_CAT) > 12 else None
        _CAT[key] = _catalogue(game, mod, have, key[3])
    return _CAT[key]


def _engine_of(mod):
    if mod is None:
        return None
    try:
        from .scriptcompat import game_kind
        return ENGINE_OF_GAME.get(game_kind(mod))
    except Exception:
        return None


def _catalogue(game, mod, have, mine):
    """{kind: {name: Entry}} a module made for game ('both', 'rome', 'medieval2') may use: one engine's, or for both
    games what BOTH engines have (the parameters of M2EX's where they differ, REX's beside them). The loaded game's
    own documentation adds the descriptions, and whatever its engine has that the carried catalogue lacks (a newer
    build) when the module is for that game."""
    b = builtin()
    if have and mine:                                    # the engine on this PC is newer than the editor's list?
        merged = {k: dict(b[mine][k]) for k in KINDS}
        for k in KINDS:
            for n, e in have[k].items():
                if n not in merged[k]:
                    merged[k][n] = Entry(k, n, e.params, e.sample, e.where, e.needs, e.works, "", [mine])
        b = dict(b, **{mine: merged})
    out = {}
    for kind in KINDS:
        if game == "both":
            rex, m2 = b["rex"][kind], b["m2ex"][kind]
            names = [n for n in m2 if n in rex]
            got = {}
            for n in names:
                e, r = m2[n], rex[n]
                params = e.params if e.params == r.params or not r.params else "%s   (REX: %s)" % (e.params, r.params)
                needs = e.needs if kind == "conditions" else [x for x in e.needs if x in r.needs]
                got[n] = Entry(kind, n, params, e.sample or r.sample, e.where, needs, e.works and r.works, "",
                               ["rex", "m2ex"])
        else:
            src = b[ENGINE_OF_GAME.get(game, "m2ex")][kind]
            got = {n: Entry(kind, n, e.params, e.sample, e.where, e.needs, e.works, "", e.engines or [])
                   for n, e in src.items()}
        if have:
            for n, e in got.items():
                if n in have[kind]:
                    e.desc = have[kind][n].desc
        out[kind] = got
    return out


def search(entries, words):
    """The entries (sorted by name) whose name, parameters, sample or description hold every word."""
    ws = [w for w in (words or "").lower().split() if w]
    out = []
    for e in sorted(entries, key=lambda e: e.name.lower()):
        hay = " ".join((e.name, e.params, e.sample, e.desc, " ".join(e.needs))).lower()
        if all(w in hay for w in ws):
            out.append(e)
    return out


# what an event's export means for the Module builder's subjects
# (a region_id alone is no town: it is where a battle was or a character stands)
EXPORT_SUBJECT = {"faction": "faction", "settlement": "settlement", "target_settlement": "settlement",
                  "character_record": "character", "character": "character",
                  "nc_character_record": "character", "target_faction": "target", "unit": "unit",
                  "player_unit": "unit"}


def subjects_of(event):
    """The Module builder subjects an engine event brings (in the builder's order)."""
    got = {EXPORT_SUBJECT[x] for x in event.needs if x in EXPORT_SUBJECT}
    return tuple(s for s in ("faction", "settlement", "character", "target", "unit") if s in got)


def missing(condition, event):
    """What a condition needs from the event (its trigger requirements) that the event does not bring - [] when it
    fits, or when the event is not known."""
    if event is None:
        return []
    return [x for x in condition.needs if x not in event.needs]


def first_word(line):
    """The command / condition name a line starts with ('not' skipped)."""
    words = (line or "").split()
    if words and words[0] == "not":
        words = words[1:]
    return words[0] if words else ""


# ---------------------------------------------------------------------------
# The parameters of a line, as fields
# ---------------------------------------------------------------------------
class Param:
    """One parameter: its words, what fills it ('factions', 'towns', 'regions', 'units', 'characters', 'traits',
    'ancillaries', 'levels', 'chains', 'logic', 'choice' with choices, 'number', 'text') and whether it may be left
    out."""
    __slots__ = ("label", "kind", "optional", "choices")

    def __init__(self, label, kind="text", optional=False, choices=()):
        self.label, self.kind, self.optional, self.choices = label, kind, optional, list(choices)


# the words of a parameter -> what fills it (the first that fits)
PARAM_KINDS = (("logic token", "logic"), ("logic_token", "logic"), ("character type", "text"),
               ("character_type", "text"), ("trait", "traits"), ("ancillar", "ancillaries"),
               ("settlement/character", "towns|characters"), ("counter", "text"),
               ("faction", "factions"), ("settlement", "towns"), ("town", "towns"), ("city", "towns"),
               ("region", "regions"), ("unit", "units"), ("character", "characters"), ("general", "characters"),
               ("chain", "chains"), ("building", "levels"), ("amount", "number"), ("number", "number"),
               ("level", "number"), ("value", "number"), ("turn", "number"), ("percent", "number"),
               ("count", "number"), ("how_many", "number"), ("money", "number"), ("year", "number"))
LOGIC = ["<", "<=", "=", ">=", ">", "!="]
NOT_CHOICES = {"exp/armour/weapon"}             # three numbers, not one of three words
PLACEHOLDER = ("_name", "_id", "_type")         # event_message_name | all: a name or the word all


def _param(text, optional=False):
    t = text.strip().strip(",").strip()
    if t.lower().startswith("opt:"):
        t, optional = t[4:].strip(), True
    if "(optional" in t.lower() or "optional" == t.lower().split(" ")[0]:
        optional = True
    t = re.sub(r"\s*\([^)]*\)", "", t).strip()
    low = t.lower()
    alts = [a.strip() for a in re.split(r"[/|]", t)]
    if len(alts) > 1 and all(re.fullmatch(r"[a-z]+(_[a-z]+)*", a) and not a.endswith(PLACEHOLDER) for a in alts) and \
            t not in NOT_CHOICES and \
            not any(k in low for k, _ in PARAM_KINDS[:18]):
        return Param(t, "choice", optional, alts)
    kind = next((v for k, v in PARAM_KINDS if k in low), "text")
    return Param(t, kind, optional)


def params_of(entry):
    """[Param] of a command / condition, read from its parameters in the engine's words: console '<a> <opt:b>
    [<c>]', the campaign script's 'faction, character' (or 'region_name|region_id value unit_name'). Events have
    none."""
    text = (entry.params or "").split("   (REX:")[0].strip()
    if not text or text.lower() in ("none", "-"):
        return []
    if entry.kind == "console" or "<" in text:
        out = []
        for m in re.finditer(r"\[\s*<([^>]*)>\s*\]|<([^>]*)>|\[([^\]]*)\]", text):
            if m.group(1) is not None:
                out.append(_param(m.group(1), True))
            elif m.group(2) is not None:
                out.append(_param(m.group(2)))
            else:
                out.append(_param(m.group(3), True))
        return out
    text = re.sub(r"\([^)]*\)", lambda m: " (optional)" if "optional" in m.group().lower() else "", text)
    parts = [p for p in text.split(",") if p.strip()]
    if len(parts) == 1 and " " in parts[0].strip() and all("_" in w or "|" in w for w in parts[0].split()
                                                           if w not in ("value",)):
        parts = parts[0].split()
    return [_param(p) for p in parts]


def split_line(line):
    """The words of a line, "quoted words" kept together (quotes dropped), commas between words dropped."""
    out, cur, quote = [], "", False
    for ch in line or "":
        if ch == '"':
            quote = not quote
            continue
        if not quote and (ch.isspace() or ch == ","):
            if cur:
                out.append(cur)
                cur = ""
            continue
        cur += ch
    if cur:
        out.append(cur)
    return out


def compose(entry, values, negate=False):
    """The line of an entry with these parameter values (in order; empty ones at the end left out): console values
    with spaces in quotes, campaign-script lines parted as its sample parts them (', ' or a space)."""
    vals = [str(v).strip() for v in values]
    while vals and not vals[-1]:
        vals.pop()
    sample = entry.sample or ""
    comma = entry.kind == "commands" and re.match(r"^\S+\s+[^,]+,\s", sample) is not None
    if entry.kind == "console":                  # a name of several words in quotes ({general}, {town} may be)
        vals = ['"%s"' % v if (" " in v or v in ("{general}", "{town}")) and not v.startswith('"') else v
                for v in vals]
    body = (", " if comma else " ").join(v for v in vals if v)
    line = entry.name + (" " + body if body else "")
    return ("not " + line) if negate and entry.kind == "conditions" else line
