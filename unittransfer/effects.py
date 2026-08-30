"""Reader for the effect files a projectile's ``effect`` / ``end_*`` lines name.

A projectile in ``descr_projectile.txt`` does not carry its own visuals. It names
effect-SETS::

    projectile elite_arrow
        effect          small_arrow_trail_set
        end_effect      arrow_impact_ground_set

and each set is declared in one of the four effect files, where it is a list of
effect names and nothing else::

    effect_set small_arrow_trail_set
    {
        lod 1000
        {
            small_arrow_trail
        }
    }

    effect small_arrow_trail
    {
        type ribbon
        {
            texture  models_effects/textures/slingshot_trail.texture
        }
    }

So an effect-set is two levels deep: the set names effects, and the effects name
the ``.CAS`` models and textures that actually draw. Carrying one across means
carrying the set block, every effect block it lists, and the files those name —
which is what this module finds and :mod:`unittransfer.transfer` emits.

**Which file a block goes back into matters.** The engine loads the four files
for different jobs: a trail set read out of ``descr_arrow_trail_effects.txt`` is
a trail, and the same text in ``descr_effect_impacts.txt`` is not. So every block
here remembers the data-relative file it was read from, and a transfer writes it
back into the file of the same name in the destination.

Blocks are kept verbatim. Nothing here rewrites one — a name collision is
resolved by *not* importing (the destination already declares a set by that name,
so a projectile pointing at it is pointing at something real), which means there
is no renaming to do and no reason to re-emit text nobody edited.

Two things real files do that the shape above does not show:

  * **A set may be declared once per graphics-detail band**, as
    ``effect_set < 3 4 > fiery_arrow_set``. That is one set with several bodies,
    not several sets, and the name is the last token. All of its variants have to
    travel together or the set exists only at some detail settings.
  * **Braces do not always balance.** Divide and Conquer's impacts file leaves an
    ``effect`` block open, and a reader that trusted the depth count swallowed the
    next two sets whole. So a block ends at the next header OR when the depth
    closes it, whichever comes first — the same rule
    :mod:`unittransfer.projectiles` uses on its own blocks.

``;`` starts a comment, and a comment may hold a brace, so the depth count reads
past it first. A header and its ``{`` may be separated by blank lines — the stock
files do it both ways.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from . import keyblock as kb

ENCODING = "latin-1"

#: The files that declare ``effect_set`` / ``effect`` blocks. The same four
#: :func:`unittransfer.projectiles.effect_sets` scans for names, and in the same
#: order, so the two never disagree about whether a mod defines a set.
FILES = (
    "descr_effect_impacts.txt",
    "descr_arrow_trail_effects.txt",
    "descr_arrow_trail_custom_effects.txt",
    "descr_artillery_effects.txt",
)

#: The two block kinds. A set lists effects; an effect draws something.
SET, EFFECT = "effect_set", "effect"

#: Keys inside an ``effect`` block whose value is a data-relative file. These are
#: the only three the stock files use, and a mod's are the same keys.
ASSET_KEYS = ("model", "debris_model", "texture")

#: ``effect_set < 3 4 > fiery_arrow_set`` — the optional ``< … >`` is the range of
#: graphics-detail levels this body is for, and the NAME is what follows it.
_HEAD_RE = re.compile(r"^\s*(effect_set|effect)\s+(?:<[^>]*>\s*)?(\S+)\s*$",
                      re.IGNORECASE)


def _code(line: str) -> str:
    """The line with its ``;`` comment removed — a brace in a comment is not code."""
    return line.split(";", 1)[0]


def _head(line: str):
    """``(kind, name)`` if this line opens a block, else ``None``.

    The name has to be the whole rest of the line: ``effect_set foo`` opens one,
    ``effect_set_count 4`` does not, and neither does a line that merely starts
    with the word inside a longer statement.
    """
    m = _HEAD_RE.match(_code(line))
    if not m:
        return None
    return m.group(1).lower(), m.group(2)


@dataclass
class Block:
    """One ``effect_set`` or ``effect``, verbatim, and where it came from."""
    kind: str = ""
    name: str = ""
    raw: str = ""              # header line through the closing brace, verbatim
    rel: str = ""              # data-relative file it was read from

    def members(self) -> List[str]:
        """The effect names an ``effect_set`` lists.

        Inside the set's ``lod`` sub-block each member is a line of its own with
        nothing else on it, which is what separates a member from one of the
        set's own settings: ``play_time 20`` and ``lod 1000`` carry a value, a
        member does not. Empty for an ``effect`` block, which lists nothing.
        """
        if self.kind != SET:
            return []
        out: List[str] = []
        seen: Set[str] = set()
        for line in self.raw.splitlines()[1:]:
            body = _code(line).strip()
            if not body or body in ("{", "}"):
                continue
            if len(body.split()) != 1:
                continue                   # a setting (`play_time 20`), not a member
            if body.lower() not in seen:
                seen.add(body.lower())
                out.append(body)
        return out

    def assets(self) -> List[str]:
        """Data-relative paths this block's ``model`` / ``texture`` lines name."""
        out: List[str] = []
        for line in self.raw.splitlines():
            parts = _code(line).strip().split(None, 1)
            if len(parts) != 2 or parts[0].lower() not in ASSET_KEYS:
                continue
            rel = parts[1].split(",", 1)[0].strip().replace("\\", "/")
            if rel.lower().startswith("data/"):
                rel = rel[5:]
            if rel and rel not in out:
                out.append(rel)
        return out


def parse_text(text: str, rel: str = "") -> List[Block]:
    """Every block in one effect file, in the order it is written."""
    lines = text.splitlines(keepends=True)
    out: List[Block] = []
    i = 0
    while i < len(lines):
        head = _head(lines[i])
        if head is None:
            i += 1
            continue
        kind, name = head
        # Find the opening brace. Anything other than blank lines before it means
        # this header has no body — malformed, and not ours to repair: skip it.
        j, opened = i + 1, False
        while j < len(lines):
            code = _code(lines[j])
            if "{" in code:
                opened = True
                break
            if code.strip():
                break                      # a statement or the next block
            j += 1
        if not opened:
            i += 1
            continue
        depth = 0
        while j < len(lines):
            # A header here ends the block whatever the depth says. Depth alone is
            # not trustworthy: a mod that leaves a brace open would otherwise take
            # every block after it with it (see the module docstring).
            if depth > 0 and _head(lines[j]) is not None:
                break
            code = _code(lines[j])
            depth += code.count("{") - code.count("}")
            j += 1
            if depth <= 0:
                break
        out.append(Block(kind=kind, name=name, raw="".join(lines[i:j]), rel=rel))
        i = j
    return out


def parse_file(path, rel: str = "") -> List[Block]:
    p = Path(path)
    if not p.exists():
        return []
    # Read without letting the platform decide what a line ending is, for the
    # reason descr_projectile.txt is read that way: a block goes back out exactly
    # as it came in, and a file mixing CRLF with lone LF must not grow.
    return parse_text(kb.read_text(p, ENCODING), rel or p.name)


@dataclass
class EffectIndex:
    """Every block a mod's four effect files declare, by name.

    Names are matched case-insensitively — the engine does, and a mod that writes
    ``Default_Arrow_Trail_Set`` in one file and the lower-case spelling in another
    means one set, not two.

    A set maps to a LIST because of the ``< 3 4 >`` detail-band form: one name can
    have three bodies, and all of them are the set. An effect maps to one block —
    nothing in the stock files declares an effect twice, and if a mod does, the
    first declaration is the one the engine keeps.
    """
    sets: Dict[str, List[Block]] = field(default_factory=dict)
    effects: Dict[str, Block] = field(default_factory=dict)

    def set_of(self, name: str) -> List[Block]:
        """Every body declared for this set name (empty if the mod has none)."""
        return self.sets.get((name or "").lower()) or []

    def effect_of(self, name: str) -> Optional[Block]:
        return self.effects.get((name or "").lower())


def index(data_dir) -> EffectIndex:
    """Read a mod's four effect files into one index.

    Set bodies accumulate in file order; for an effect the first declaration wins.
    """
    idx = EffectIndex()
    for fn in FILES:
        for b in parse_file(Path(data_dir) / fn, fn):
            if b.kind == SET:
                idx.sets.setdefault(b.name.lower(), []).append(b)
            else:
                idx.effects.setdefault(b.name.lower(), b)
    return idx


def resolve(idx: EffectIndex, names: Iterable[str],
            have_sets: Iterable[str] = (), have_effects: Iterable[str] = ()):
    """What it takes to bring ``names`` (effect-set names) into another mod.

    Returns ``(blocks, missing)``:

      * ``blocks`` — the set blocks and the effect blocks they list, in the order
        they must be written, skipping anything the destination already declares
        (``have_sets`` / ``have_effects``). A set is emitted before the effects it
        names, so a file read top to bottom introduces the set first, the way the
        stock files do. A set declared once per detail band contributes all of its
        bodies: half of them would leave the set undefined at the other settings.
      * ``missing`` — the names the SOURCE does not declare either. Those are the
        ones a transfer still has to point at the placeholder: the source mod is
        inheriting them from vanilla, and vanilla's copy is not ours to copy.
    """
    have_sets = {s.lower() for s in have_sets}
    have_effects = {e.lower() for e in have_effects}
    blocks: List[Block] = []
    missing: List[str] = []
    taken: Set[str] = set()
    for name in names:
        low = (name or "").lower()
        if not low or low in taken:
            continue
        taken.add(low)
        if low in have_sets:
            # The destination declares this set itself. Its body is the one the
            # engine will use, so importing the source's members underneath it
            # would add blocks nothing reaches.
            continue
        bodies = idx.set_of(low)
        if not bodies:
            missing.append(name)
            continue
        blocks.extend(bodies)
        for member in (m for b in bodies for m in b.members()):
            mlow = member.lower()
            if mlow in taken or mlow in have_effects:
                continue
            taken.add(mlow)
            eb = idx.effect_of(mlow)
            if eb is not None:
                blocks.append(eb)
            # An effect the source does not declare either is vanilla's, like the
            # set case above. It is NOT reported as missing: the set itself came
            # across, so the projectile points at something real, and the engine
            # falls back to its own copy of the member — which is what the source
            # mod was relying on too.
    return blocks, missing
