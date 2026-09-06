"""``export_descr_guilds.txt`` - the guilds, and the triggers that feed them.

Phase 18a. The toolkit has validated *against* this file since Phase 12 -
:mod:`unittransfer.buildings` refuses a ``guild_`` requirement the file does not
declare, and says so with the count - and could not open it. That asymmetry, we
know a file well enough to refuse and not well enough to fix, is the whole
argument for this module.

**Two block types, one file, and the keyword is the same word.** ::

    Guild assassins_guild                 <- a definition
        building guild_assassins_guild
        levels  100 250 500

    Trigger 0010_Recruit_Assassin
        WhenToTest AgentCreated
        Condition TrainedAgentType = assassin
        Guild assassins_guild s  10       <- an effect

The trigger half is :mod:`unittransfer.triggers`, unchanged, and the definition
half is a flat record. What is new here is that the two are told apart by word
count, which is why :data:`unittransfer.triggers.DEFINITION_WORDS` exists: read
without it every guild trigger ends at its own first effect and the effects are
collected as definitions. Measured across both installed mods, ``Guild`` is 21
two-word definitions against 507 four-word effects, and every one of the 1,850
``Trait`` and ``Ancillary`` lines in the EDCT and the EDA is two words, so the
count costs the older files nothing.

**Why the whole file is not read through :mod:`unittransfer.flatrecord`.** The
roadmap asked, and the answer is that keyword collision: ``parse_records`` opens
a new record on every line whose head word is the shape's, so all 507 effect
lines would become guilds named ``assassins_guild s 10``. One *block* on its own
has no triggers in it, though, so :data:`SHAPE` is a real flatrecord shape and
the block editor, its span map and its field list are that module's and not
copied here. The file-level scan is the only new parser.

**What the file actually says, counted rather than assumed.**

*A definition has exactly two body keys.* All 21 records in both mods write
``building`` and ``levels`` and nothing else. The reference tool's parser also
reads ``SettlementMinLevel`` and ``FactionSupport``; neither appears in a single
real file, so they are carried through an edit and are not offered as form
fields anybody has to answer.

*A ``levels`` line is three ascending thresholds.* 20 of the 21 are. The one
that is not is Third Age Reforged's ``gwaith_i_mirdain_guild``, ``levels
1000000 250`` - two values and descending - which is reported and not refused,
because it is somebody else's mod and it loads today.

*The scope letter is ``s``, ``o`` or ``a``* - 272, 188 and 47 uses. The
reference tool documents only ``s`` and ``o`` and defaults to ``o``, which would
quietly rewrite all 47 of the third kind.

*``all`` and ``this`` are engine words, not guild names.* Both mods award points
to them and neither declares them, so the check that a trigger's points go
somewhere skips those two rather than reporting 47 findings about them.

And one thing found by running the check that this module exists to run: Divide
and Conquer awards guild points to ``avengers_guild`` and ``thiefs_guild`` and
**declares neither**. Those points go nowhere, which is exactly the fault the
building side could see the shadow of and never name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import flatrecord as fr
from . import keyblock as kb
from . import triggers

#: plain 8-bit text like every other campaign file
ENCODING = triggers.ENCODING

#: where it lives, under the mod's ``data/``
GUILDS_REL = "export_descr_guilds.txt"

#: the keyword that opens a definition, and the one an effect line reuses
GUILD_KW = "Guild"

#: the two body keys every real record writes, then the two the reference tool
#: reads and no installed mod has. All four round-trip; only the first two are
#: put on a form.
ORDER = ("building", "levels", "SettlementMinLevel", "FactionSupport")

#: what the form leads with, because it is what the file actually holds
FORM_KEYS = ("building", "levels")

#: the scope letter of a ``Guild <name> <scope> <points>`` effect line, measured
#: rather than taken from the reference tool, which knows only the first two
SCOPES = {"s": "this settlement", "o": "every settlement this faction owns",
          "a": "every settlement in the world"}

#: names an effect line may carry that are not guilds. Both mods use both and
#: neither declares either, so a check that treated them as guild names would
#: report 47 findings about words the engine owns.
EFFECT_KEYWORDS = ("all", "this")

#: how many thresholds a ``levels`` line carries. 20 of the 21 real records.
LEVEL_COUNT = 3

#: the prefix a guild's building tree carries in ``export_descr_buildings.txt``
BUILDING_PREFIX = "guild_"

#: one flat record - a head line and ``keyword value`` lines under it. Used for
#: ONE block at a time, never for the file: see the module docstring.
SHAPE = fr.Shape(rel=GUILDS_REL, label="Guilds", kw=GUILD_KW, noun="guild",
                 order=ORDER, required=("building", "levels"))


class GuildError(kb.BlockError):
    """The text is not a guild, or an edit would write a file the engine cannot use."""


split_lines = triggers.split_lines


# ---------------------------------------------------------------------------
# the file


@dataclass
class Guild:
    """One ``Guild <name>`` definition block."""

    name: str = ""
    values: Dict[str, str] = field(default_factory=dict)
    lines: Dict[str, int] = field(default_factory=dict)
    start: int = 0
    end: int = 0
    warnings: List[str] = field(default_factory=list)

    def get(self, key: str) -> str:
        return self.values.get(key, "")

    @property
    def building(self) -> str:
        return self.get("building")

    @property
    def levels(self) -> List[str]:
        return self.get("levels").split()

    def as_dict(self) -> Dict:
        d: Dict = {"name": self.name, "start": self.start, "end": self.end,
                   "levels_list": self.levels}
        for key in ORDER:
            d[key] = self.get(key)
        return d


@dataclass
class GuildFile:
    """The whole file: its own lines, its definitions and its trigger section."""

    lines: List[str] = field(default_factory=list)
    newline: str = "\r\n"
    trailing_newline: bool = True
    guilds: List[Guild] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    #: 0-based line of the first ``Trigger``, or -1 when the file has none
    trigger_start: int = -1

    def text(self) -> str:
        """The file exactly as it was read - what every round-trip test asserts."""
        out = self.newline.join(self.lines)
        return out + self.newline if self.trailing_newline and self.lines else out

    def get(self, name: str) -> Optional[Guild]:
        return next((g for g in self.guilds if g.name == name), None)

    def by_name(self) -> Dict[str, Guild]:
        return {g.name: g for g in self.guilds}

    def block_text(self, g: Guild) -> str:
        return self.newline.join(self.lines[g.start:g.end])


def _is_definition(words: Sequence[str]) -> bool:
    """``Guild <name>`` and nothing else. The rule the whole file turns on."""
    return (len(words) == triggers.DEFINITION_WORDS
            and words[0] == GUILD_KW)


def parse_text(text: str) -> GuildFile:
    """Read the whole file. Never raises: anything odd becomes a warning.

    Only the definition blocks are interpreted here. The trigger section is
    carried as lines and read by :func:`trigger_file`, so that one line number
    means the same thing to both halves of the editor.
    """
    lines, newline, trailing = split_lines(text)
    gf = GuildFile(lines=lines, newline=newline, trailing_newline=trailing)
    cur: Optional[Guild] = None
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        words = code.split()
        if _is_definition(words):
            cur = Guild(name=words[1], start=i, end=i + 1)
            gf.guilds.append(cur)
            continue
        if words[0] == triggers.TRIGGER_KW:
            if gf.trigger_start < 0:
                gf.trigger_start = i
            cur = None
            continue
        if cur is None:
            continue
        key = words[0]
        if key not in ORDER:
            # an effect line loose above the trigger section, or a key nobody
            # has written down. Reported, never dropped.
            cur.warnings.append(f"line {i + 1}: `{key}` is not a guild line")
        elif key in cur.lines:
            cur.warnings.append(f"line {i + 1}: a second `{key}` line")
        cur.values[key] = code[len(key):].strip()
        cur.lines[key] = i
        cur.end = i + 1

    for g in gf.guilds:
        gf.warnings.extend(f"{g.name or '(unnamed)'}: {w}" for w in g.warnings)
    return gf


def parse_file(path: str | Path) -> GuildFile:
    return parse_text(kb.read_text(Path(path), ENCODING))


def path_for(mod) -> Path:
    return Path(mod.data) / GUILDS_REL


def read(mod) -> Tuple[GuildFile, str]:
    """``(parsed, original text)``. Raises :class:`GuildError` when there is none."""
    path = path_for(mod)
    if not path.exists():
        raise GuildError(f"{getattr(mod, 'name', '?')} has no {GUILDS_REL}")
    text = kb.read_text(path, ENCODING)
    return parse_text(text), text


def trigger_file(text: str) -> triggers.TriggerFile:
    """The trigger half, read by the one parser that owns that grammar."""
    return triggers.parse_text(text)


def parse_block(text: str) -> Guild:
    """One definition block, as a Code View pane holds it."""
    gf = parse_text(text if text.endswith("\n") else text + "\n")
    if not gf.guilds:
        raise GuildError("a guild starts with a `Guild <name>` line - this text "
                         "has none", 1)
    if len(gf.guilds) > 1:
        raise GuildError(f"this text holds {len(gf.guilds)} guilds - one at a time",
                         gf.guilds[1].start + 1)
    return gf.guilds[0]


# ---------------------------------------------------------------------------
# what the effects say about the definitions


@dataclass
class Award:
    """One ``Guild <name> <scope> <points>`` line inside a trigger."""

    guild: str = ""
    scope: str = ""
    points: str = ""
    trigger: str = ""
    line: int = 0

    def as_dict(self) -> Dict:
        return {"guild": self.guild, "scope": self.scope, "points": self.points,
                "scope_label": SCOPES.get(self.scope, ""),
                "trigger": self.trigger, "line": self.line + 1}


def awards(tf: triggers.TriggerFile) -> List[Award]:
    """Every guild-point line in the file, with the trigger it belongs to."""
    out: List[Award] = []
    for t in tf.triggers:
        for e in t.effects:
            if e.keyword != GUILD_KW:
                continue
            args = list(e.args) + ["", ""]
            out.append(Award(guild=args[0], scope=args[1], points=args[2],
                             trigger=t.name, line=e.line))
    return out


def awards_by_guild(tf: triggers.TriggerFile) -> Dict[str, List[Award]]:
    out: Dict[str, List[Award]] = {}
    for a in awards(tf):
        out.setdefault(a.guild, []).append(a)
    return out


# ---------------------------------------------------------------------------
# checks


def finding(code: str, fatal: bool, message: str, **extra) -> Dict:
    d = {"code": code, "fatal": fatal, "message": message}
    d.update(extra)
    return d


def check_guild(g: Guild, buildings: Optional[set] = None) -> List[Dict]:
    """One definition, on its own terms.

    Nothing here is fatal on somebody else's mod: a baseline shows and stops
    blocking, it never hides, and every one of these loads in the game today.
    """
    out: List[Dict] = []
    if not g.name:
        out.append(finding("no_name", True, "this guild has no name"))
    if not g.building:
        out.append(finding(
            "no_building", True,
            f"{g.name or 'this guild'} names no `building` line, so nothing in "
            f"{GUILDS_REL} says which building tree it grants"))
    elif buildings is not None and g.building not in buildings:
        out.append(finding(
            "unknown_building", False,
            f"`building {g.building}` is not a building line in "
            f"export_descr_buildings.txt - the guild has nothing to build",
            value=g.building))
    elif g.building and not g.building.startswith(BUILDING_PREFIX):
        out.append(finding(
            "building_prefix", False,
            f"`building {g.building}` does not start with `{BUILDING_PREFIX}` - "
            "every guild building line in both installed mods does",
            value=g.building))

    levels = g.levels
    if not levels:
        out.append(finding(
            "no_levels", True,
            f"{g.name or 'this guild'} has no `levels` line, so no number of "
            "guild points ever completes it"))
        return out
    bad = [v for v in levels if not kb.is_int(v)]
    if bad:
        out.append(finding("levels_not_numbers", True,
                           "`levels` takes whole numbers of guild points - "
                           + kb.and_list(bad) + " is not one", value=" ".join(levels)))
        return out
    nums = [int(v) for v in levels]
    if len(nums) != LEVEL_COUNT:
        out.append(finding(
            "levels_count", False,
            f"`levels` has {len(nums)} threshold(s); 20 of the 21 guilds in the "
            f"installed mods write {LEVEL_COUNT}, one per guild tier",
            value=" ".join(levels)))
    if any(b <= a for a, b in zip(nums, nums[1:])):
        out.append(finding(
            "levels_order", False,
            "`levels` counts upward - " + " ".join(levels) + " does not, so a "
            "later tier is reached before an earlier one",
            value=" ".join(levels)))
    if any(n < 0 for n in nums):
        out.append(finding("levels_negative", False,
                           "a guild point threshold below zero is reached at once",
                           value=" ".join(levels)))
    return out


def check_file(gf: GuildFile, tf: Optional[triggers.TriggerFile] = None,
               buildings: Optional[set] = None) -> List[Dict]:
    """Every finding the whole file can have, definitions and triggers together.

    The two cross-checks are the point of reading both halves at once: points
    awarded to a guild nobody declared go nowhere, and a guild nobody awards
    points to can never be built.
    """
    out: List[Dict] = []
    seen: Dict[str, int] = {}
    for g in gf.guilds:
        for f in check_guild(g, buildings):
            out.append(dict(f, guild=g.name, line=g.start + 1))
        if g.name in seen:
            out.append(finding(
                "duplicate", False,
                f"`Guild {g.name}` is declared twice - the engine reads the "
                f"first block and ignores this one (line {seen[g.name] + 1})",
                guild=g.name, line=g.start + 1))
        else:
            seen[g.name] = g.start
    if tf is None:
        return out

    declared = set(seen)
    by_guild = awards_by_guild(tf)
    for name in sorted(by_guild):
        if name in declared or name in EFFECT_KEYWORDS:
            continue
        rows = by_guild[name]
        out.append(finding(
            "undeclared", False,
            f"{len(rows)} trigger line(s) award guild points to `{name}`, which "
            f"no `Guild {name}` block in this file declares - those points go "
            "nowhere",
            guild=name, line=rows[0].line + 1,
            triggers=sorted({r.trigger for r in rows})))
    for name in sorted(declared):
        if name in by_guild:
            continue
        g = gf.get(name)
        out.append(finding(
            "never_awarded", False,
            f"no trigger in this file awards a guild point to `{name}`, so it "
            "can never reach its first tier",
            guild=name, line=(g.start + 1) if g else 0))
    for a in awards(tf):
        if a.scope and a.scope not in SCOPES:
            out.append(finding(
                "unknown_scope", False,
                f"`Guild {a.guild} {a.scope} {a.points}` - the scope letter is "
                + kb.and_list(sorted(SCOPES)) + " in every one of the 507 real "
                "lines measured", guild=a.guild, line=a.line + 1))
        elif a.points and not kb.is_int(a.points):
            out.append(finding(
                "points_not_number", False,
                f"`Guild {a.guild} {a.scope} {a.points}` - guild points are a "
                "whole number", guild=a.guild, line=a.line + 1))
    return out


def building_names(mod) -> set:
    """Every building line in the mod's EDB, for the `building` check.

    A rule with no evidence reports nothing: when the mod keeps its EDB inside
    the packed data there is no list to check against, and the caller is handed
    ``None`` rather than an empty set that would report every guild as broken.
    """
    from . import buildings as bld
    path = Path(mod.data) / "export_descr_buildings.txt"
    if not path.exists():
        return None
    try:
        tree = bld.parse_text(kb.read_text(path, bld.ENCODING))
    except Exception:
        return None
    return {b.name for b in tree.buildings}


# ---------------------------------------------------------------------------
# the block editor - flatrecord's, because one block IS a flat record


def render_block(base: str, edits: Optional[Dict] = None) -> str:
    """``base`` with ``edits`` spliced into it, line by line.

    ``edits`` is the form's own body: ``name`` plus any of :data:`ORDER`. What
    is not named is not touched, so a form that posts every box does not
    reformat the lines nobody edited.
    """
    try:
        return fr.render_record(SHAPE, base, edits or {})
    except fr.RecordError as e:
        raise GuildError(e.message, e.line) from None


def new_block(edits: Dict) -> str:
    """A whole guild written from scratch, in the shape the real files write."""
    name = str(edits.get("name") or "").strip()
    if not name:
        raise GuildError("a new guild needs a name")
    building = str(edits.get("building") or "").strip() or (BUILDING_PREFIX + name)
    levels = kb.value_text(edits.get("levels")) or "100 250 500"
    return "\n".join([f"{GUILD_KW} {name}",
                      f"    building {building}",
                      f"    levels  {levels}"])


def block_spans(block: str) -> Dict[str, List[List[int]]]:
    """``{label: [[first, last]]}``, 1-based, for one block - Code View's map."""
    try:
        return fr.record_spans(SHAPE, block)
    except fr.RecordError as e:
        raise GuildError(e.message, e.line) from None


def block_fields(block: str) -> List[Tuple[str, str]]:
    """``[(label, value)]`` for one block, in the order its lines appear."""
    try:
        return fr.record_fields(SHAPE, block)
    except fr.RecordError as e:
        raise GuildError(e.message, e.line) from None


def replace_block(gf: GuildFile, g: Guild, block: str) -> str:
    """The whole file with one definition's lines swapped for ``block``."""
    body, _, _ = split_lines(block)
    while body and not body[-1].strip():
        body.pop()
    lines = list(gf.lines)
    lines[g.start:g.end] = body
    out = gf.newline.join(lines)
    return out + gf.newline if gf.trailing_newline and lines else out


def _banner_span(gf: GuildFile, g: Guild) -> Tuple[int, int]:
    """A block's own lines, plus the separator banner written above it.

    Every block in both installed mods sits under
    ``;------------------------------------------``, and :func:`insert_block`
    writes one for a new guild, so a delete that took only the block's own lines
    would leave a banner pointing at the next guild - and adding a guild and
    removing it again would not put the file back.

    Only a comment whose text is dashes counts. The section headers in this file
    are ``;===`` rules with words between them, and eating one of those would
    take the ``;== TRIGGER DATA STARTS HERE ==`` line off the top of the trigger
    section the first time somebody deleted the last guild.
    """
    start = g.start
    if start > 0:
        above = gf.lines[start - 1].strip()
        if above.startswith(";") and above[1:] and set(above[1:]) == {"-"}:
            start -= 1
            if start > 0 and not gf.lines[start - 1].strip():
                start -= 1
    return start, g.end


def insert_block(gf: GuildFile, block: str) -> str:
    """A new guild goes under the last one, above the trigger section.

    Never at the end of the file: the engine reads the definitions before the
    triggers that name them, and a ``Guild`` line below a ``Trigger`` is a guild
    it has already stopped looking for. This is the same ruling
    :func:`unittransfer.traits._insert_trait` makes about the EDCT.
    """
    lines = list(gf.lines)
    at = (gf.guilds[-1].end if gf.guilds
          else (gf.trigger_start if gf.trigger_start >= 0 else len(lines)))
    body = [ln[:-1] if ln.endswith("\r") else ln for ln in block.split("\n")]
    lines[at:at] = ["", ";------------------------------------------"] + body
    out = gf.newline.join(lines)
    return out + gf.newline if gf.trailing_newline and lines else out


# ---------------------------------------------------------------------------
# what the module serves


def label(g: Guild) -> str:
    """The name, with the building tree it grants in brackets."""
    return f"{g.name} ({g.building})" if g.building else g.name


def overview(mod) -> Dict:
    """Every guild in the mod, what it grants, and what feeds it."""
    gf, text = read(mod)
    tf = trigger_file(text)
    by_guild = awards_by_guild(tf)
    known = building_names(mod)
    findings = check_file(gf, tf, known)
    per_guild: Dict[str, int] = {}
    for f in findings:
        name = f.get("guild") or ""
        per_guild[name] = per_guild.get(name, 0) + 1
    rows = []
    for g in gf.guilds:
        rows.append({
            "name": g.name,
            "label": label(g),
            "building": g.building,
            "levels": g.levels,
            "awards": len(by_guild.get(g.name, [])),
            "triggers": sorted({a.trigger for a in by_guild.get(g.name, [])}),
            "findings": per_guild.get(g.name, 0),
            "lines": [g.start + 1, g.end],
        })
    undeclared = sorted(n for n in by_guild
                        if n not in gf.by_name() and n not in EFFECT_KEYWORDS)
    return {
        "mod": mod.name,
        "file": GUILDS_REL,
        "guilds": rows,
        "triggers": len(tf.triggers),
        "awards": len(awards(tf)),
        "undeclared": undeclared,
        "scopes": dict(SCOPES),
        "findings": findings,
        "warnings": list(gf.warnings),
        "buildings_known": known is not None,
    }


def detail(mod, name: str) -> Dict:
    """One guild: its block, the triggers that feed it, and its findings."""
    gf, text = read(mod)
    g = gf.get(name)
    if g is None:
        raise GuildError(f"{name!r} is not a guild in {GUILDS_REL}")
    tf = trigger_file(text)
    known = building_names(mod)
    rows = awards_by_guild(tf).get(name, [])
    out = g.as_dict()
    out.update({
        "label": label(g),
        "file": GUILDS_REL,
        "block": gf.block_text(g),
        "lines": [g.start + 1, g.end],
        "awards": [a.as_dict() for a in rows],
        "triggers": [t.as_dict() for t in tf.triggers
                     if any(e.keyword == GUILD_KW and e.args
                            and e.args[0] == name for e in t.effects)],
        "findings": [dict(f) for f in check_guild(g, known)],
        "vocab": {"buildings": sorted(known) if known else [],
                  "buildings_known": known is not None,
                  "scopes": dict(SCOPES),
                  "guilds": [x.name for x in gf.guilds]},
    })
    return out


# ---------------------------------------------------------------------------
# the save


@dataclass
class GuildPlan:
    """One save, worked out without touching the disk."""

    mod: object = None
    action: str = "edit"                 # 'edit' | 'add' | 'delete'
    name: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[Dict] = field(default_factory=list)
    #: the whole file as it would be written - empty when nothing would change
    text: str = ""
    #: the block as it would read, for the preview
    block: str = ""
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} guild {self.name} in "
                f"{getattr(self.mod, 'name', '?')} ({len(self.changes)} change(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"action": self.action, "name": self.name,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "findings": list(self.findings),
                "block": self.block, "ok": not self.errors and bool(self.text)}


def plan(mod, body: dict) -> GuildPlan:
    """Work out the whole new file for one save, without touching the disk.

    ``body`` is ``{guild, action, edits, raw_block, triggers: {...}}``.
    ``raw_block`` is text hand-edited in the Code View and it wins over
    ``edits`` and reaches disk verbatim - the ruling every editor here makes.
    """
    p = GuildPlan(mod=mod, action=str(body.get("action") or "edit"),
                  name=str(body.get("guild") or "").strip())
    try:
        gf, original = read(mod)
    except GuildError as e:
        p.errors.append(e.message)
        return p
    p.path = path_for(mod)
    try:
        text = _plan_guild(p, gf, original, body)
        text = triggers.edit_section(text, dict(body.get("triggers") or {}),
                                     p.changes, p.warnings, p.errors)
    except (GuildError, triggers.TriggerError) as e:
        p.errors.append(e.message)
        return p
    if p.errors:
        return p

    after = parse_text(text)
    g = after.get(p.name)
    if g is not None:
        p.block = after.block_text(g)
        p.findings = check_guild(g, building_names(mod))
        p.errors += [f["message"] for f in p.findings if f["fatal"]]
        p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.text = "" if text == original else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _plan_guild(p: GuildPlan, gf: GuildFile, text: str, body: dict) -> str:
    """The file with this one guild added, edited or removed."""
    if p.action == "add":
        if not p.name:
            raise GuildError("a new guild needs a name")
        if gf.get(p.name) is not None:
            p.errors.append(f"{p.name} is already a guild in this file")
            return text
        block = str(body.get("raw_block") or "").strip("\r\n") or new_block(
            dict(body.get("edits") or {}, name=p.name))
        parse_block(block + "\n")          # refuse a block that is not one
        p.changes.append(f"+ Guild {p.name}")
        return insert_block(gf, block)

    g = gf.get(p.name)
    if g is None:
        p.errors.append(f"{p.name} is not a guild in {GUILDS_REL}")
        return text

    if p.action == "delete":
        rows = awards_by_guild(trigger_file(text)).get(p.name, [])
        if rows:
            p.warnings.append(
                f"{len(rows)} trigger line(s) still award points to {p.name} - "
                "they will award them to a guild nothing declares")
        p.changes.append(f"- Guild {p.name}")
        lines = list(gf.lines)
        start, end = _banner_span(gf, g)
        del lines[start:end]
        out = gf.newline.join(lines)
        return out + gf.newline if gf.trailing_newline and lines else out

    base = gf.block_text(g)
    raw = body.get("raw_block")
    if raw is not None and str(raw).strip():
        block = str(raw).strip("\r\n")
        if parse_block(block + "\n").name != p.name:
            raise GuildError(
                f"this guild is `{p.name}` - renaming it here would orphan every "
                "trigger that awards it points and the building line it grants")
    else:
        block = render_block(base, dict(body.get("edits") or {}))
    if block == base:
        return text
    p.changes.extend(kb.diff(base, block))
    return replace_block(gf, g, block)


def apply(p: GuildPlan) -> Dict:
    """Write a planned save, with the same backups and undo as any other job.

    The old file goes to ``config/backups/<id>/data/…`` and the manifest goes in
    the transfer log, so the Log's Undo puts it back byte-exact.
    """
    import shutil
    import time

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    target = Path(mod.data) / GUILDS_REL
    bpath = backup_root / "data" / GUILDS_REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, bpath)
        manifest["backed_up"].append(GUILDS_REL)
        file_op("BACKUP", target, f"-> {bpath}")
    else:
        manifest["created"].append(GUILDS_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "guilds",
        "action": p.action,
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("GUILD  %s %s in %s - %d change(s), id=%s",
             p.action, p.name, mod.name, len(p.changes), tid)
    return {"id": tid, "guild": p.name, "record": rec}
