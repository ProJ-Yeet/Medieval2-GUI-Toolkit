"""Phase 34. Declaring a climate - which is four writes, and a slot rather than
a thirteenth name.

Every file this needs is already parsed. ``descr_climates.txt`` is
:func:`unittransfer.mapvocab.climates`, ``descr_aerial_map_ground_types.txt`` is
:func:`unittransfer.mapterrain.parse`, and ``map_climates.tga`` is a layer the
brush has painted since 16c. **What was missing is the operation**, and the
archive has a tutorial for it - Bella's *How-To: Add a New Climate Zone*, 2007 -
that names exactly those files plus ``descr_climates_lookup.txt``,
``text/climates.txt`` and ``map_ground_types.tga``.

**The tutorial's own thread withdraws its central claim, and the installed mods
agree with the thread.** Two years and eighteen posts after the how-to, wilddog
writes that a climate the engine does not already know by name is not read by
``descr_geography_new.txt``, that the exe looks to be hard coded to those names,
and that the answer is to amend an existing one "including the unused1 and
unused2 names". That is not one modder's opinion, it is what is on this machine:
**all four installed mods declare exactly twelve climates, and they are the same
twelve in the same order**, ``unused1`` and ``unused2`` among them. Divide and
Conquer has a wholly custom map of 248,370 tiles and did not add a thirteenth -
it painted 18,970 of them with ``unused1`` and called it Harondor in
``text/climates.txt``.

**So the operation this offers is taking a slot over**, and appending a new name
is offered second, with the geography file named as the reason it is second.
Both are real: the strat map draws a new name perfectly well, which is why the
tutorial worked for its author, and the battle map is where it stops.

**Four writes that have to agree**, in the tutorial's own order:

  1. ``descr_climates.txt`` - the ``climates { }`` list fixes the index, and a
     ``climate <name> { }`` block carries the colour, the heat and the winter
     flag.
  2. ``descr_aerial_map_ground_types.txt`` - a texture for every ground type,
     **in both seasons**, or the tiles are Phase 30's gap.
  3. ``text/climates.txt`` - the display name, UTF-16, or the ``.strings.bin``
     when a mod ships only the compiled copy.
  4. ``descr_climates_lookup.txt`` - the same list again, when the mod has one.

**The fourth is already wrong in the wild, and it is the tutorial's fault.** Its
step 4 prints a lookup list containing ``volcanic`` while its step 3 prints a
``climates { }`` block that does not, and Third Age Reforged and Vanilla Redux
both ship exactly that: thirteen names in the lookup, twelve declared, the extra
one ``volcanic``. Divide and Conquer's twelve match;
``vanilla_kingdoms_uncompromised`` has no lookup file at all. All four states are
reported rather than tidied away.

**``map_climates.tga`` is not written here.** Painting a climate onto the map is
a stroke, the brush owns strokes, and 28b's ruling is that a control which is
not the brush does not start a paint session. What this writes is the colour the
brush can then use - and, on a take-over, the plan says how many tiles are
already painted the slot's *old* colour and will therefore fall through to the
``default`` block until they are repainted.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import mapterrain, mapvocab
from . import keyblock as kb
from .campmap import MapError
from .mapvocab import Rgb

#: Plain 8-bit game data, as everywhere else
ENCODING = mapvocab.ENCODING
#: ``data/text`` is UTF-16 with a BOM, as everywhere else
LOC_ENCODING = "utf-16"

CLIMATES_REL = mapvocab.CLIMATES_REL
NAMES_REL = mapvocab.CLIMATE_NAMES_REL
LOOKUP_REL = "descr_climates_lookup.txt"
AERIAL_REL = mapterrain.AERIAL_REL

#: The battle map's own reading of a climate, by name. The text file regenerates
#: the compiled one beside it; most released mods ship only the compiled one,
#: which is why a missing ``.txt`` is not a fault here.
GEOG_REL = "descr_geography_new.txt"
GEOG_DB_REL = "descr_geography_new.db"

#: The file's three top-level blocks that are not climates. Measured off
#: Vanilla Redux's copy, the one mod here that ships the text file: it has
#: fifteen top-level blocks and twelve of them are the twelve climates. Without
#: this the count in the warning would be three too many.
GEOG_SETTINGS: Tuple[str, ...] = ("generation", "texture_settings",
                                  "grid_settings")

#: A climate in that file is a top-level block, in one of two shapes: a bare
#: name for the four that carry a full description, and ``<name> modifies
#: <base>`` for the eight that vary one of them. Both are a block for the name.
_GEOG_BLOCK = re.compile(
    r"^(\w+)[ \t]*(?:modifies[ \t]+\w+)?[ \t]*(?:;[^\n]*)?\n\{", re.M)

#: The twelve the engine ships, in the engine's own order. Measured rather than
#: copied from the tutorial: it is what all four installed mods declare,
#: character for character, and it is what ``descr_geography_new.txt`` has a
#: block for.
VANILLA_ORDER: Tuple[str, ...] = (
    "mediterranean", "sandy_desert", "rocky_desert", "unused1", "steppe",
    "temperate_deciduous_forest", "temperate_coniferous_forest", "unused2",
    "highland", "alpine", "tropical", "semi_arid",
)

#: The two of the twelve that are spare by name. CA left them unnamed and every
#: mod here that wanted a climate of its own took one: Divide and Conquer's
#: ``unused1`` is Harondor over 18,970 tiles, Reforged's is 5,466.
SPARE: Tuple[str, ...] = ("unused1", "unused2")

#: A climate code the engine and every path here can carry - a bare token, the
#: same shape :data:`unittransfer.campnew.NAME_RE` holds a campaign to.
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

#: ``heat`` is the armour-fatigue effect. The range is the file's own header
#: comment in Divide and Conquer: "range 1-4 (zero would mean no armour effects
#: to fatigue at all)", so zero is legal and means none.
HEAT_MIN, HEAT_MAX = 0, 4

#: The block every climate falls back to, and the one a colour nobody declared
#: is drawn with. :mod:`unittransfer.mapterrain` owns the rule; this is the same
#: name so that a donor list can offer it.
DEFAULT_CLIMATE = mapterrain.DEFAULT_CLIMATE


class ClimateError(ValueError):
    """The climate cannot be declared, with the reason in the modder's words."""


# ---------------------------------------------------------------------------
# what the mod already has


def lookup_names(mod) -> Optional[List[str]]:
    """``descr_climates_lookup.txt`` as a list, or ``None`` when there is none.

    ``None`` and ``[]`` are different answers: a mod without the file has
    nothing to keep in step, and a mod with an empty one has a file saying there
    are no climates at all. Only the first is ordinary.
    """
    path = Path(mod.data) / LOOKUP_REL
    if not path.is_file():
        return None
    try:
        text = kb.read_text(path, ENCODING)
    except OSError:
        return None
    out: List[str] = []
    for line in text.splitlines():
        s = line.split(";", 1)[0].strip().lstrip("﻿")
        if s and s not in ("{", "}"):
            out.append(s)
    return out


def lookup_state(mod, codes: Sequence[str]) -> dict:
    """Whether the lookup file and the declared list say the same twelve things.

    Reported rather than repaired, and reported in both directions, because the
    two disagreements mean different things: a name in the lookup that nothing
    declares is the tutorial's own ``volcanic`` propagated - Reforged and
    Vanilla Redux both have it - and a declared climate missing from the lookup
    is a slot the engine may index differently from this file.
    """
    names = lookup_names(mod)
    out = {"file": LOOKUP_REL, "have": names is not None,
           "names": names or [], "extra": [], "missing": [], "note": ""}
    if names is None:
        out["note"] = (f"this mod has no {LOOKUP_REL}, so there is no second "
                       f"list to keep in step. Nothing is written to it.")
        return out
    have = set(codes)
    out["extra"] = [n for n in names if n not in have]
    out["missing"] = [c for c in codes if c not in names]
    bits = []
    if out["extra"]:
        bits.append(f"{LOOKUP_REL} names {len(out['extra'])} climate(s) that "
                    f"{CLIMATES_REL} does not declare: "
                    f"{', '.join(out['extra'])}. The tutorial this operation "
                    f"comes from prints exactly that mismatch in its own step 4, "
                    f"which is where it is most likely to have come from.")
    if out["missing"]:
        bits.append(f"{len(out['missing'])} declared climate(s) are not in "
                    f"{LOOKUP_REL}: {', '.join(out['missing'])}.")
    out["note"] = " ".join(bits)
    return out


def geography(mod) -> dict:
    """Which climates the battle map's own file names, when it can be read.

    ``descr_geography_new.txt`` carries one ``<climate> modifies <climate>``
    block per name and the engine compiles it into the ``.db`` beside it. Most
    released mods ship only the ``.db``, so "the names cannot be read here" is
    the ordinary state and not a fault - it is said in those words rather than
    left as an empty list, which would read as "no climate has a block".
    """
    data = Path(mod.data)
    path, db = data / GEOG_REL, data / GEOG_DB_REL
    out = {"file": GEOG_REL, "have": False, "compiled": db.is_file(),
           "names": [], "problem": ""}
    if not path.is_file():
        out["problem"] = (
            f"{GEOG_REL} is not in this mod's data folder"
            + (f", only the compiled {GEOG_DB_REL} beside it, which is not read "
               f"here. Which climates the battle map knows by name cannot be "
               f"checked against this mod." if db.is_file() else
               f" and neither is {GEOG_DB_REL}. The game keeps its own copy "
               f"inside a .pack."))
        return out
    try:
        text = kb.read_text(path, ENCODING)
    except OSError as exc:
        out["problem"] = f"{GEOG_REL} will not read: {exc}"
        return out
    out["have"] = True
    text = text.replace("\r\n", "\n")
    out["names"] = sorted({m.group(1) for m in _GEOG_BLOCK.finditer(text)}
                          - set(GEOG_SETTINGS))
    return out


def climate_tiles(cm) -> Dict[int, int]:
    """Tiles per packed colour in ``map_climates.tga``. ``{}`` if it will not read.

    The same census :func:`unittransfer.campmap.layer_legend` takes, without the
    naming and without the cap: this wants a count for a colour that may be in
    no vocabulary at all, which is exactly the colour a new climate is about to
    claim.
    """
    try:
        census = cm.tiles("climates").getcolors(1 << 20)
    except (MapError, OSError, ValueError):
        return {}
    if census is None:
        return {}
    return {mapvocab.key(rgb): n for n, rgb in census}


def slots(mod, cm=None) -> List[dict]:
    """Every declared climate as a slot, with what is and is not filled in.

    One row per climate in the engine's index order, carrying the four facts
    that decide whether it is the one to take over: whether the name is spare,
    how many tiles already carry its colour, whether the aerial file gives it a
    texture block, and whether the battle map knows the name.
    """
    cl = mapvocab.climates(mod)
    voc = mapterrain.read_vocabulary(mod)
    geo = geography(mod)
    tiles = climate_tiles(cm) if cm is not None else {}
    out: List[dict] = []
    for c in cl:
        block = voc.blocks.get(c["code"]) or {}
        rgb = c["rgb"]
        out.append({
            "code": c["code"],
            "name": c["name"],
            "label": c["name"] if c["name"] != c["code"] else "",
            "index": c["index"],
            "rgb": list(rgb) if rgb else None,
            "key": mapvocab.key(rgb) if rgb else None,
            "heat": c["heat"],
            "winter": bool(c["winter"]),
            "tiles": tiles.get(mapvocab.key(rgb), 0) if rgb else 0,
            "spare": c["code"] in SPARE,
            "vanilla": c["code"] in VANILLA_ORDER,
            "aerial": bool(block),
            "grounds": len(block),
            # None rather than False when the file is not readable: "no block"
            # and "cannot say" are answers a panel has to tell apart
            "geography": (c["code"] in geo["names"]) if geo["have"] else None,
        })
    return out


def ground_keys(voc: mapterrain.Vocabulary) -> List[str]:
    """Which ground types a new block in **this mod** has to name.

    The mod's own blocks, not a constant this module invents. Every installed
    mod is internally consistent - one key set across all of its blocks - and
    the set is not the same everywhere: three mods name sixteen ground types and
    Vanilla Redux names seventeen, the extra one ``impassable_shrouded``. A
    block written to a constant would be a line short on one mod in four.
    """
    counts: Dict[Tuple[str, ...], int] = {}
    for block in voc.blocks.values():
        if block:
            keys = tuple(sorted(block))
            counts[keys] = counts.get(keys, 0) + 1
    if not counts:
        return []
    return list(max(counts.items(), key=lambda kv: (kv[1], len(kv[0])))[0])


def donors(voc: mapterrain.Vocabulary) -> List[dict]:
    """Every aerial block a new one can be copied from, ``default`` first.

    A climate with no textures of its own is pink across every tile it is
    painted on (30), and the honest starting point is a block that already
    draws - the same rule :mod:`unittransfer.campnew` applies to a campaign.
    """
    out = [{"code": c, "grounds": len(voc.blocks[c])} for c in sorted(voc.blocks)]
    out.sort(key=lambda d: (d["code"] != DEFAULT_CLIMATE, d["code"]))
    return out


# ---------------------------------------------------------------------------
# writing descr_climates.txt


def _colour_line(rgb: Rgb) -> str:
    return f"\tcolour\t{rgb[0]} {rgb[1]} {rgb[2]}"


def _strip_head(body: str) -> str:
    """A donor body without the three lines a new climate sets for itself."""
    out: List[str] = []
    for line in body.splitlines():
        s = line.split(";", 1)[0].strip()
        if re.match(r"^(colour|heat)\b", s) or s == "winter":
            continue
        out.append(line.rstrip())
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def climate_block(code: str, rgb: Rgb, heat: int, winter: bool,
                  donor_body: str = "") -> str:
    """One ``climate <name> { … }`` block, in the file's own shape.

    ``donor_body`` is another climate's body with its ``colour``, ``heat`` and
    ``winter`` lines taken out: the strategy tree models, the battle vegetation
    and the env map are the parts a new climate has no way to invent and are
    most of what makes it look like anything, so they are inherited rather than
    left out. Without them the block is legal, the strat map draws, and the
    province has no trees.
    """
    lines = [f"climate {code}", "{", _colour_line(rgb), f"\theat\t{heat}"]
    if winter:
        lines.append("\twinter")
    body = _strip_head(donor_body)
    if body:
        lines.append("")
        lines.extend(body.splitlines())
    lines.append("}")
    return "\n".join(lines) + "\n"


def _find_block(text: str, code: str) -> Optional[Tuple[int, int, str]]:
    """``(start, end, body)`` of one ``climate <code> { … }``, or ``None``."""
    m = re.search(r"^[ \t]*climate[ \t]+" + re.escape(code)
                  + r"[ \t]*(?:;[^\n]*)?\n[ \t]*\{(.*?)^[ \t]*\}[ \t]*\n?",
                  text, re.S | re.M)
    return (m.start(), m.end(), m.group(1)) if m else None


def _list_span(text: str) -> Optional[Tuple[int, int, str]]:
    """``(start, end, body)`` of the opening ``climates { … }`` list."""
    m = re.search(r"^[ \t]*climates[ \t]*\n?[ \t]*\{(.*?)^[ \t]*\}[ \t]*\n?",
                  text, re.S | re.M)
    return (m.start(), m.end(), m.group(1)) if m else None


def write_climates(text: str, code: str, rgb: Rgb, heat: int, winter: bool,
                   donor_body: str = "") -> Tuple[str, bool]:
    """``descr_climates.txt`` with this climate declared. ``(text, appended)``.

    A slot that is already there keeps its place in the list - **the list is the
    index the engine reads, and moving a name in it renumbers every climate
    after the move**, which is 36's lesson about region colours arriving a file
    early. So a take-over rewrites the block where it stands and touches the
    list not at all; only a genuinely new name is appended, to both.
    """
    nl = kb.newline_of(text)
    flat = text.replace("\r\n", "\n")
    hit = _find_block(flat, code)
    block = climate_block(code, rgb, heat, winter, donor_body)
    if hit:
        start, end, _ = hit
        flat = flat[:start] + block + flat[end:]
        return (flat.replace("\n", nl) if nl != "\n" else flat), False

    span = _list_span(flat)
    if span is None:
        raise ClimateError(
            f"{CLIMATES_REL} has no opening 'climates {{ … }}' list, which is "
            f"the order the engine indexes climates by. This file is not in a "
            f"shape a climate can be added to safely.")
    start, end, body = span
    listed = body.rstrip("\n")
    listed = listed + ("\n" if listed else "") + f"\t{code}\n"
    flat = flat[:start] + "climates\n{" + listed + "}\n" + flat[end:]
    flat = flat.rstrip("\n") + "\n\n" + block
    return (flat.replace("\n", nl) if nl != "\n" else flat), True


# ---------------------------------------------------------------------------
# writing descr_aerial_map_ground_types.txt


def aerial_block(code: str, pairs: Dict[str, Tuple[str, str]],
                 order: Sequence[str]) -> str:
    """One aerial block, every ground type on its own line in both columns.

    Both columns always, even where they are the same file. The one-column form
    is legal and :meth:`unittransfer.mapterrain.Vocabulary.texture` reads it,
    but a block written here is a block somebody is about to edit, and two
    columns is the form that makes the winter half visible to edit.
    """
    width = max((len(g) for g in order), default=0) + 1
    lines = [f"climate {code}", "{"]
    for ground in order:
        summer, winter = pairs.get(ground, ("", ""))
        if not summer:
            continue
        lines.append(f"\t{ground.ljust(width)}\t{summer}\t{winter}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_aerial(text: str, code: str, block: str) -> Tuple[str, bool]:
    """The aerial file with this climate's block in it. ``(text, appended)``."""
    nl = kb.newline_of(text) if text else "\n"
    flat = text.replace("\r\n", "\n")
    hit = _find_block(flat, code)
    if hit:
        start, end, _ = hit
        out, appended = flat[:start] + block + flat[end:], False
    else:
        out, appended = flat.rstrip("\n") + "\n\n" + block, True
    return (out.replace("\n", nl) if nl != "\n" else out), appended


def write_lookup(text: str, code: str) -> str:
    """The lookup list with this code in it, appended and never reordered."""
    nl = kb.newline_of(text) if text else "\n"
    flat = text.replace("\r\n", "\n")
    for line in flat.splitlines():
        if line.split(";", 1)[0].strip().lstrip("﻿") == code:
            return text
    out = flat.rstrip("\n") + "\n" + code + "\n"
    return out.replace("\n", nl) if nl != "\n" else out


# ---------------------------------------------------------------------------
# the plan


@dataclass
class ClimatePlan:
    """One climate declared, worked out without touching the disk."""

    mod: object = None
    cm: object = None
    code: str = ""
    label: str = ""
    rgb: Optional[Rgb] = None
    heat: int = 0
    winter: bool = False
    donor: str = ""
    #: ``"take"`` an existing slot, or ``"add"`` a name the mod does not have
    mode: str = "take"
    #: data-relative path -> whole new text
    texts: Dict[str, str] = field(default_factory=dict)
    #: the display name, and whether ``text/climates.txt`` has the key yet
    loc_writes: Dict[str, str] = field(default_factory=dict)
    loc_new: List[str] = field(default_factory=list)
    #: whether the new block inherited any strategy models, battle vegetation
    #: or env map - false when the donor is not a declared climate
    trimmings: bool = False
    #: ground types the new aerial block names, and the ones the donor lacks
    grounds: List[str] = field(default_factory=list)
    ground_gaps: List[str] = field(default_factory=list)
    #: tiles already painted the colour being claimed, and the slot's old one
    claimed_tiles: int = 0
    orphan_tiles: int = 0
    orphan_rgb: Optional[Rgb] = None
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    lookup: dict = field(default_factory=dict)
    geog: dict = field(default_factory=dict)
    #: every declared climate, for the sentence that names what could be copied
    climates_named: List[str] = field(default_factory=list)

    def summary(self) -> str:
        head = (f"climate {self.code} "
                f"{'declared in' if self.mode == 'add' else 'taken over in'} "
                f"{getattr(self.mod, 'name', '?')} - colour "
                f"{' '.join(str(v) for v in (self.rgb or ()))}, heat {self.heat}"
                f"{', winter' if self.winter else ''}, "
                f"{len(self.grounds)} ground type(s) from {self.donor}")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {
            "code": self.code, "label": self.label, "mode": self.mode,
            "rgb": list(self.rgb) if self.rgb else None,
            "key": mapvocab.key(self.rgb) if self.rgb else None,
            "heat": self.heat, "winter": self.winter, "donor": self.donor,
            "trimmings": self.trimmings,
            "files": sorted(self.texts), "grounds": list(self.grounds),
            "ground_gaps": list(self.ground_gaps),
            "keys": sorted(self.loc_writes), "new_keys": list(self.loc_new),
            "claimed_tiles": self.claimed_tiles,
            "orphan_tiles": self.orphan_tiles,
            "orphan_rgb": list(self.orphan_rgb) if self.orphan_rgb else None,
            "changes": list(self.changes), "warnings": list(self.warnings),
            "errors": list(self.errors), "lookup": dict(self.lookup),
            "geography": dict(self.geog),
            "ok": not self.errors and bool(self.texts),
        }


def _colour_of(body: dict) -> Rgb:
    raw = body.get("colour") if body.get("colour") is not None else body.get("rgb")
    if isinstance(raw, str):
        raw = [p for p in re.split(r"[\s,]+", raw.strip()) if p]
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ClimateError(
            "a climate is declared by one colour in map_climates.tga, so it "
            "needs three numbers: red, green and blue")
    out: List[int] = []
    for v in raw:
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise ClimateError(f"{v!r} is not a colour channel - each of the "
                               f"three is a whole number from 0 to 255") from None
        if not 0 <= n <= 255:
            raise ClimateError(f"{n} is outside 0-255, which is what a TGA "
                               f"channel holds")
        out.append(n)
    return (out[0], out[1], out[2])


def plan(mod, cm, body: dict) -> ClimatePlan:
    """Work out one climate. ``body`` is
    ``{code, label, colour, heat, winter, donor}``.

    ``code`` decides the mode on its own, out of the mod's own data: a code the
    mod already declares is a **take-over** and keeps its place in the index; a
    code it does not is an **add**, and the geography warning is attached to it.
    There is no fifth field asking which of the two this is, because the answer
    is not the caller's to give.
    """
    p = ClimatePlan(mod=mod, cm=cm)
    p.code = str(body.get("code") or "").strip()
    p.label = str(body.get("label") or "").strip()
    if not p.code:
        p.errors.append("a climate needs the name the engine reads it by")
        return p
    if not NAME_RE.match(p.code):
        p.errors.append(
            f"{p.code!r} will not do as a climate name - it is a bare word the "
            f"engine reads out of four files: a letter first, then letters, "
            f"digits or underscores, and no spaces or dots")
        return p

    cl = mapvocab.climates(mod)
    by_code = {c["code"]: c for c in cl}
    existing = by_code.get(p.code)
    p.mode = "take" if existing else "add"

    try:
        p.rgb = _colour_of(body)
    except ClimateError as exc:
        p.errors.append(str(exc))
        return p
    try:
        p.heat = int(body.get("heat", existing["heat"] if existing else 2))
    except (TypeError, ValueError):
        p.errors.append("heat is a whole number, the armour-fatigue effect")
        return p
    if not HEAT_MIN <= p.heat <= HEAT_MAX:
        p.errors.append(
            f"heat {p.heat} is outside {HEAT_MIN}-{HEAT_MAX}. The range is the "
            f"file's own header comment: zero would mean no armour effects to "
            f"fatigue at all.")
    p.winter = bool(body.get("winter", existing["winter"] if existing else False))

    clash = [c for c in cl
             if c["rgb"] and tuple(c["rgb"]) == p.rgb and c["code"] != p.code]
    if clash:
        p.errors.append(
            f"{' and '.join(c['code'] for c in clash)} already "
            f"{'declare' if len(clash) > 1 else 'declares'} colour "
            f"{' '.join(str(v) for v in p.rgb)}. Two climates on one colour is "
            f"one climate: map_climates.tga has no way to tell them apart, and "
            f"the probe would name whichever the file declares first.")

    voc = mapterrain.read_vocabulary(mod)
    p.geog = geography(mod)
    p.climates_named = [c["code"] for c in cl]
    p.lookup = lookup_state(mod, p.climates_named)
    _plan_textures(p, voc, body)
    if p.errors:
        return p
    _plan_files(p, voc, existing)
    if p.errors:
        return p
    _plan_tiles(p, existing)
    _plan_warnings(p)
    return p


def _plan_textures(p: ClimatePlan, voc: mapterrain.Vocabulary,
                   body: dict) -> None:
    """The donor block, and the ground types the new one will name."""
    if not voc.present:
        p.errors.append(
            voc.problem or f"{AERIAL_REL} is not readable, and without it a "
            f"climate has no textures in either season")
        return
    p.donor = str(body.get("donor") or "").strip() or DEFAULT_CLIMATE
    src = voc.blocks.get(p.donor)
    if not src:
        have = ", ".join(sorted(voc.blocks)) or "none"
        p.errors.append(
            f"{AERIAL_REL} has no block for {p.donor!r}, so there is nothing to "
            f"copy the textures from. It has: {have}")
        return
    p.grounds = ground_keys(voc)
    if not p.grounds:
        p.errors.append(f"{AERIAL_REL} names no ground types at all")
        return
    p.ground_gaps = [g for g in p.grounds if g not in src]


def _plan_files(p: ClimatePlan, voc: mapterrain.Vocabulary,
                existing: Optional[dict]) -> None:
    """The four texts, each read and rewritten whole."""
    data = Path(p.mod.data)
    src = voc.blocks.get(p.donor) or {}
    pairs = {g: src[g] for g in p.grounds if g in src}

    # 1 - descr_climates.txt
    cpath = data / CLIMATES_REL
    if not cpath.is_file():
        p.errors.append(f"{CLIMATES_REL} is not in this mod's data folder. The "
                        f"game keeps its own copy inside a .pack, and a climate "
                        f"cannot be declared into a file that is not there.")
        return
    ctext = kb.read_text(cpath, ENCODING)
    # a take-over keeps its own strategy models and vegetation; an add inherits
    # the donor's, which is the only source for them there is - and the donor
    # may be `default`, which is a block of the AERIAL file and not a climate,
    # so there is nothing there to inherit. That is not a corner: `default` is
    # the first donor offered, so it is the likeliest thing to be asked for.
    hit = _find_block(ctext.replace("\r\n", "\n"),
                      p.code if existing else p.donor)
    donor_body = hit[2] if hit else ""
    p.trimmings = bool(_strip_head(donor_body))
    try:
        new_c, appended = write_climates(ctext, p.code, p.rgb, p.heat,
                                         p.winter, donor_body)
    except ClimateError as exc:
        p.errors.append(str(exc))
        return
    p.texts[CLIMATES_REL] = new_c
    p.changes.append(
        f"{CLIMATES_REL}: {'the climates list and a new' if appended else 'the'} "
        f"climate {p.code} block - colour "
        f"{' '.join(str(v) for v in p.rgb)}, heat {p.heat}"
        f"{', winter' if p.winter else ', no winter of its own'}")

    # 2 - descr_aerial_map_ground_types.txt
    apath = data / AERIAL_REL
    atext = kb.read_text(apath, ENCODING) if apath.is_file() else ""
    new_a, a_appended = write_aerial(atext, p.code,
                                     aerial_block(p.code, pairs, p.grounds))
    p.texts[AERIAL_REL] = new_a
    p.changes.append(
        f"{AERIAL_REL}: {'a new' if a_appended else 'the'} climate {p.code} "
        f"block, {len(pairs)} ground type(s) in both seasons, copied from "
        f"{p.donor}")

    # 4 - descr_climates_lookup.txt, when the mod has one
    if p.lookup["have"]:
        ltext = kb.read_text(data / LOOKUP_REL, ENCODING)
        new_l = write_lookup(ltext, p.code)
        if new_l != ltext:
            p.texts[LOOKUP_REL] = new_l
            p.changes.append(f"{LOOKUP_REL}: {p.code} appended")

    # 3 - the display name. Worked out last because it is the one that may go to
    # a .strings.bin instead, and that road is campfiles' rather than a text here
    if p.label:
        p.loc_writes[p.code] = p.label
        if f"{{{p.code}}}" not in _loc_body(p.mod):
            p.loc_new.append(p.code)
        p.changes.append(
            f"{NAMES_REL}: {{{p.code}}}{p.label}"
            f"{' (a new key)' if p.code in p.loc_new else ''}")


def _loc_body(mod) -> str:
    path = Path(mod.data) / NAMES_REL
    if not path.is_file():
        return ""
    try:
        return kb.read_text(path, LOC_ENCODING)
    except (OSError, UnicodeError):
        try:
            return kb.read_text(path, ENCODING)
        except OSError:
            return ""


def _plan_tiles(p: ClimatePlan, existing: Optional[dict]) -> None:
    """How many tiles the new colour already covers, and how many it strands.

    Two counts, and they answer different questions. ``claimed_tiles`` is tiles
    already painted the colour being declared: on an add that is usually zero,
    and anything else means the map was already using a colour nothing named.
    ``orphan_tiles`` is a take-over's own - the slot's *old* colour is still on
    the map and nothing declares it any more, so those tiles fall through to the
    ``default`` block until they are repainted. Divide and Conquer's ``unused1``
    is 18,970 of them.
    """
    if p.cm is None or not p.rgb:
        return
    tiles = climate_tiles(p.cm)
    if not tiles:
        return
    p.claimed_tiles = tiles.get(mapvocab.key(p.rgb), 0)
    if existing and existing["rgb"] and tuple(existing["rgb"]) != p.rgb:
        p.orphan_rgb = tuple(existing["rgb"])
        p.orphan_tiles = tiles.get(mapvocab.key(p.orphan_rgb), 0)


def _plan_warnings(p: ClimatePlan) -> None:
    """Everything true that is not a refusal - the geography file above all."""
    if p.mode == "add":
        if p.geog["have"] and p.code not in p.geog["names"]:
            p.warnings.append(
                f"{GEOG_REL} has a block for {len(p.geog['names'])} climate(s) "
                f"and {p.code} is not one of them. The strat map will draw this "
                f"climate; a battle fought in a province painted with it is the "
                f"crash the tutorial's own thread ends on, because the engine "
                f"reads the battle map's terrain by climate NAME. Taking over "
                f"{' or '.join(SPARE)} instead avoids it entirely, and that is "
                f"what every mod installed here did.")
        elif not p.geog["have"]:
            p.warnings.append(
                f"{p.geog['problem']} A climate name the battle map does not "
                f"know is a crash when a battle starts in it, so a new name is "
                f"the half of this operation that cannot be checked against "
                f"this mod. Taking over one of the twelve the engine ships - "
                f"{' or '.join(SPARE)} are spare by name - needs no such check.")
        if p.code not in VANILLA_ORDER:
            p.warnings.append(
                f"all four mods measured for this declare exactly the twelve "
                f"climates the engine ships, in the engine's order, and not one "
                f"added a thirteenth. Divide and Conquer has a wholly custom map "
                f"and took over unused1 rather than adding a name.")
    if p.ground_gaps:
        p.warnings.append(
            f"{p.donor} names no texture for {', '.join(p.ground_gaps)}, so "
            f"{p.code} will not either and those tiles fall through to the "
            f"{DEFAULT_CLIMATE} block. Where that has none either they are "
            f"drawn by nothing, which is the gap the terrain layer counts.")
    if not p.trimmings:
        others = ", ".join(c for c in (p.climates_named or []) if c != p.code)
        p.warnings.append(
            f"{p.donor} is a block of {AERIAL_REL} and not a declared climate, "
            f"so it has no strategy tree models, no battle vegetation and no "
            f"env map to copy - and there is nowhere else those lines could "
            f"come from. {p.code}'s block carries its colour, its heat and its "
            f"winter flag and nothing else: the strat map will draw the ground "
            f"underneath it and the province will have no trees on it. Copying "
            f"from a climate instead gives it all three"
            + (f" - {others} each have them." if others else "."))
    if p.orphan_tiles:
        p.warnings.append(
            f"{p.orphan_tiles:,} tile(s) are painted "
            f"{' '.join(str(v) for v in p.orphan_rgb)}, which is {p.code}'s "
            f"colour until this is saved and nobody's afterwards. They stay "
            f"where they are - this writes no pixels - and are drawn with the "
            f"{DEFAULT_CLIMATE} block until they are repainted with the brush.")
    if p.claimed_tiles and p.mode == "add":
        p.warnings.append(
            f"{p.claimed_tiles:,} tile(s) already carry "
            f"{' '.join(str(v) for v in p.rgb)}. Declaring it does not paint "
            f"them, it names them: they are this climate from the moment this "
            f"is saved.")
    if not p.claimed_tiles and not p.orphan_tiles:
        p.warnings.append(
            f"no tile carries {' '.join(str(v) for v in p.rgb)} yet. This "
            f"declares the climate and the brush paints it - map_climates.tga "
            f"is not written here.")
    if not p.label:
        p.warnings.append(
            f"no display name, so {NAMES_REL} is left alone and the climate "
            f"shows as its code name. The tutorial's own note is that nobody is "
            f"sure where the game uses it; Divide and Conquer fills it in "
            f"anyway, which is why it is offered.")
    if p.lookup["note"]:
        p.warnings.append(p.lookup["note"])


# ---------------------------------------------------------------------------
# the save


def apply(p: ClimatePlan) -> dict:
    """Write the four files, with the same backups and undo as any other job."""
    import shutil

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.texts:
        raise ValueError("there is nothing to write")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = Path(mod.data) / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    for rel, text in sorted(p.texts.items()):
        target = keep(rel)
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")

    out: dict = {"id": tid, "code": p.code, "mode": p.mode,
                 "files": sorted(p.texts)}
    if p.loc_writes:
        out["loc"] = _write_names(mod, p, keep, file_op)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "climate_new",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.code, "resolved_type": p.code,
        "options": {"donor": p.donor, "take": p.mode == "take",
                    "colour": list(p.rgb or ())},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CLIMATE %s - %s %s, colour %s, %d file(s), id=%s", mod.name,
             p.mode, p.code, p.rgb, len(p.texts), tid)
    out["record"] = rec
    return out


def _write_names(mod, p: ClimatePlan, keep, file_op) -> dict:
    """The display name, into ``text/climates.txt`` or its compiled copy.

    The same two roads :func:`unittransfer.campfiles.write_descriptions` takes,
    over a different file: a mod that ships only the ``.strings.bin`` is not a
    broken mod, it is most released ones - and here it is two of the four
    installed, neither of which has the ``.txt`` at all.
    """
    from . import cleaner, stringsbin

    txt = Path(mod.data) / NAMES_REL
    if txt.exists():
        target = keep(NAMES_REL)
        # the compiled cache is rewritten below, so back it up too - an undo
        # that restored the .txt and left the .bin would put the file back and
        # leave the game still reading the new text
        keep(NAMES_REL + ".strings.bin")
        kb.write_text(target,
                      stringsbin.upsert_txt(kb.read_text(target, LOC_ENCODING),
                                            p.loc_writes),
                      LOC_ENCODING)
        file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
        res = cleaner.refresh_strings_bin(
            mod.root, "data/" + NAMES_REL + ".strings.bin")
        return {"file": NAMES_REL, "written": len(p.loc_writes),
                "new": len(p.loc_new), "strings_bin": res}
    rel = NAMES_REL + ".strings.bin"
    target = keep(rel)
    sb = stringsbin.read(target)
    for tag, value in p.loc_writes.items():
        sb.set(tag, value)
    stringsbin.write(target, sb)
    file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
    return {"file": rel, "written": len(p.loc_writes), "new": len(p.loc_new),
            "compiled": True}


# ---------------------------------------------------------------------------
# the panel


def view(mod, cm=None) -> dict:
    """What the Climates panel shows before anything is picked. Never raises.

    Everything the form needs, built out of this mod rather than out of a table
    here: the slots with their tile counts, the donors with their ground counts,
    the two spare names, and the state of the two files that cannot be written
    blind - the lookup and the geography.
    """
    voc = mapterrain.read_vocabulary(mod)
    cl = mapvocab.climates(mod)
    rows = slots(mod, cm)
    return {
        "mod": getattr(mod, "name", ""),
        "file": CLIMATES_REL,
        "have": bool(cl),
        "problem": ("" if cl else
                    f"{CLIMATES_REL} is not in this mod's data folder, or it "
                    f"declares nothing. The game keeps its own copy inside a "
                    f".pack, so a mod that changed no climate has no file here "
                    f"and nothing on this panel can be filled in."),
        "slots": rows,
        "spare": list(SPARE),
        "free": [s["code"] for s in rows if s["spare"] and s["tiles"] == 0],
        "vanilla": list(VANILLA_ORDER),
        "aerial": voc.payload(),
        "donors": donors(voc),
        "grounds": ground_keys(voc),
        "heat": [HEAT_MIN, HEAT_MAX],
        "lookup": lookup_state(mod, [c["code"] for c in cl]),
        "geography": geography(mod),
        "names_file": NAMES_REL,
        "names_have": (Path(mod.data) / NAMES_REL).is_file(),
        "layer": "climates",
    }
