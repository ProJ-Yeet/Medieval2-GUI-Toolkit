"""Phase 37a, T7. What the campaign script spawns, and where it puts it.

**Reading a script is not writing one, and that is the whole reason this can
exist.** 19b refused to edit ``campaign_script.txt`` because its grammar is
nothing this toolkit models, and 24 kept the refusal; :mod:`renames` still lists
every line it would have had to touch and writes none of them. That ruling is
untouched here. This reads coordinates out of the script and never puts one
back, so the refusal stands and the screen still gains the one thing the script
holds that nothing else can see: **where the campaign puts armies that
``descr_strat.txt`` knows nothing about.**

**How much that is, measured.** The markers layer has shown seven kinds since
18b, all of them out of ``descr_strat.txt`` and the two event files. Beside
them:

======================================  ======  =========================
campaign                                spawns  from
======================================  ======  =========================
Divide and Conquer, imperial_campaign    1,324  1,317 armies, 7 characters
Divide and Conquer, Shattered_Alliances  1,131  1,129 armies, 2 characters
Third Age Reforged, Fellowship              98  64 armies, 34 characters
======================================  ======  =========================

DaC's imperial campaign has **1,317 scripted armies** against the 305 characters
its ``descr_strat.txt`` places. Four fifths of what that campaign puts on the
map has been invisible on this screen.

**Every single one carries a coordinate.** 2,510 ``spawn_army`` blocks across
the three campaigns and not one without an ``x``/``y`` on its ``character``
line, so this is a complete reading rather than a sample. That is worth knowing
because it is what makes the export trustworthy: there is no silent remainder.

**The y is the game's, and the flip is the map's.** A script writes the same
coordinates ``descr_strat.txt`` does - counting up from the bottom - so
:meth:`CampaignMap.image_xy` is what turns one into a pixel, exactly as
:func:`unittransfer.campstrat.markers` leaves that flip to the caller. Doing it
twice in two places is how a marker ends up mirrored, which is 17d's rule and is
followed here: **the rows this returns are in the file's own coordinates.**

**The reading is validated against the one thing that can check it.** Resolved
through :meth:`unittransfer.stratobj.Vocabulary.province_at`, **1,322 of DaC's
1,324 imperial spawns land in a named province, and both misses are admirals** -
which is correct, because an admiral is a fleet and belongs at sea. The same on
Shattered Alliances: 1,127 of 1,131, the four misses all admirals. A reading
that agreed with the map 99.8% of the time by accident is not a thing that
happens.

**And on the third campaign it does not, which is the finding.** Third Age
Reforged's Fellowship campaign puts **45 of its 98 spawns on sea tiles with a
land character on them** - 20 named characters, 16 witches, 9 generals - by its
own ``map_heights.tga``. Its ``descr_strat.txt`` does the same thing with 72 of
its 150 characters. That is reported as a count and a list of lines, never as a
verdict: it is somebody else's campaign and the reason is not established here.
The baseline rule this project keeps says a tool that blocks on another mod's
state is one nobody opens twice, so :func:`view` counts it and moves on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import campmap, campstrat

#: The two names a campaign folder gives its script, which is
#: :data:`unittransfer.renames.SCRIPT_NAMES` - imported rather than copied,
#: because "which files are the script" must have exactly one answer.
from .renames import SCRIPT_NAMES

#: ``x 167, y 356`` as every one of these files writes it, comma optional.
XY = re.compile(r"\bx\s+(-?\d+)\s*,?\s*y\s+(-?\d+)", re.I)

#: The block a scripted army is: ``spawn_army`` … ``end``, with a ``faction``
#: line, one ``character`` line carrying the coordinate, and a ``unit`` line per
#: regiment. Measured on all three campaigns: one character per block, always.
ARMY_HEAD = "spawn_army"

#: …and the one-liner, which carries its own coordinate and no units.
CHARACTER_HEAD = "spawn_character"

#: A character type that belongs on water. An admiral is a fleet, so an admiral
#: at sea is right and a general at sea is not. Measured: the only type that
#: ever appears at sea in a campaign that plays.
AFLOAT = ("admiral",)


@dataclass
class Spawn:
    """One thing the script puts on the map, in the file's own coordinates."""

    kind: str = "army"                  # "army" or "character"
    faction: str = ""
    name: str = ""
    type: str = ""                      # named character, general, spy, admiral…
    x: int = 0
    y: int = 0
    units: List[str] = field(default_factory=list)
    line: int = 0                       # 1-based, of the block head
    char_line: int = 0                  # 1-based, of the line carrying x/y
    rel: str = ""                       # the script, relative to data/
    #: filled in by :func:`resolve` and empty until then
    province: str = ""
    at_sea: bool = False
    off_map: bool = False
    #: the tile carries a colour no ``descr_regions.txt`` record declares. A
    #: third state, and a real one: two of DaC's Shattered Alliances spawns
    #: stand on the ocean's own colour while ``map_heights.tga`` calls the tile
    #: land, so they are neither in a province nor at sea. Without this they
    #: would vanish into "did not resolve" and look like a fault in the reader.
    undeclared: bool = False

    def payload(self) -> dict:
        return {"kind": self.kind, "faction": self.faction, "name": self.name,
                "type": self.type, "x": self.x, "y": self.y,
                "units": list(self.units), "unit_count": len(self.units),
                "line": self.line, "char_line": self.char_line, "rel": self.rel,
                "province": self.province, "at_sea": self.at_sea,
                "off_map": self.off_map, "undeclared": self.undeclared,
                "afloat_ok": self.type.lower() in AFLOAT}


def script_paths(mod, campaign: str = "") -> List[Path]:
    """The script files this campaign has, in :data:`SCRIPT_NAMES` order.

    A campaign keeps its script in its own folder, so which one is read follows
    the campaign the screen is on rather than a constant - the same rule every
    other per-campaign read here follows.
    """
    home = (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
            / campstrat.campaign_rel(campaign or campstrat.DEFAULT_CAMPAIGN))
    return [home / n for n in SCRIPT_NAMES if (home / n).is_file()]


def _fields(body: str) -> List[str]:
    return [p.strip() for p in body.split(",")]


def _head(line: str) -> str:
    bare = line.strip()
    return bare.split()[0].lower() if bare.split() else ""


#: A ``unit`` line inside a ``spawn_army``, which is NOT the comma-separated
#: shape the ``character`` line beside it uses.
#:
#: Measured across both installed mods: **4,253 unit lines, not one of them
#: carrying a comma, and every single one carrying ``exp``, ``armour`` and
#: ``weapon_lvl``.** So the name runs from the keyword to the first attribute
#: and the tabs inside it are whitespace - ``unit\t\tClan Heralds\t\t\texp 3
#: armour 0 weapon_lvl 0`` is one unit called "Clan Heralds". Splitting this on
#: commas the way the ``character`` line beside it is split gives a unit whose
#: name has "exp 3 armour 0 weapon_lvl 0" on the end, which is a name no EDU has.
#:
#: ``soldiers`` is in the list because **six of DaC's 3,822 lines carry it** -
#: ``unit Moria Balrog soldiers 1 exp 9 armour 3 weapon_lvl 2`` - and stopping
#: only at ``exp`` made those six "Moria Balrog soldiers 1", which is exactly
#: the six dead references the EDU join then reported. With it, the join is
#: clean on every one of DaC's 3,822.
_ATTRS = ("soldiers", "exp", "armour", "weapon_lvl")
_UNIT = re.compile(r"^unit\s+(.*?)(?:\s+(?:%s)\b.*)?$" % "|".join(_ATTRS),
                   re.I | re.S)


def _unit_name(line: str) -> str:
    m = _UNIT.match(line.strip())
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def scan_text(text: str, rel: str = "") -> List[Spawn]:
    """Every spawn in one script, read as blocks rather than as lines.

    A ``spawn_army`` is read to its ``end`` so that the units belong to the army
    that spawns them; a ``character`` line outside such a block is not a spawn
    at all (``descr_strat.txt`` shares the keyword and this is not that file),
    so only the one inside the block is taken.
    """
    out: List[Spawn] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        bare = raw.strip()
        if bare.startswith(";"):
            i += 1
            continue
        head = _head(raw)

        if head == ARMY_HEAD:
            sp = Spawn(kind="army", line=i + 1, rel=rel)
            j = i + 1
            while j < len(lines):
                b = lines[j].strip()
                if b.startswith(";"):
                    j += 1
                    continue
                low = _head(lines[j])
                if low == "end" or low == ARMY_HEAD:
                    break
                if low == "faction":
                    parts = b.split(None, 1)
                    sp.faction = _fields(parts[1])[0] if len(parts) > 1 else ""
                elif low == "character":
                    parts = b.split(None, 1)
                    f = _fields(parts[1]) if len(parts) > 1 else []
                    sp.name = f[0] if f else ""
                    sp.type = f[1] if len(f) > 1 else ""
                    m = XY.search(b)
                    if m:
                        sp.x, sp.y = int(m.group(1)), int(m.group(2))
                        sp.char_line = j + 1
                elif low == "unit":
                    sp.units.append(_unit_name(b))
                j += 1
            out.append(sp)
            i = j
            continue

        if head == CHARACTER_HEAD:
            parts = bare.split(None, 1)
            f = _fields(parts[1]) if len(parts) > 1 else []
            sp = Spawn(kind="character", line=i + 1, char_line=i + 1, rel=rel,
                       faction=f[0] if f else "",
                       name=f[1] if len(f) > 1 else "",
                       type=f[2] if len(f) > 2 else "")
            m = XY.search(bare)
            if m:
                sp.x, sp.y = int(m.group(1)), int(m.group(2))
            out.append(sp)
        i += 1
    return out


def scan(mod, campaign: str = "") -> List[Spawn]:
    """Every spawn in every script this campaign has."""
    out: List[Spawn] = []
    data = Path(mod.data)
    for path in script_paths(mod, campaign):
        try:
            text = path.read_text(encoding=campmap.ENCODING, errors="ignore")
        except OSError:
            continue
        out += scan_text(text, path.relative_to(data).as_posix())
    return out


def resolve(rows: List[Spawn], cm: Optional[campmap.CampaignMap]) -> List[Spawn]:
    """Fill in the province, the sea flag and the off-map flag, in place.

    The coordinates stay as the file wrote them. What this adds is what the map
    says about each one, through the same two calls every other reader of a
    game coordinate uses - :meth:`CampaignMap.image_xy` and
    :meth:`unittransfer.stratobj.Vocabulary.province_at` - so a spawn and a fort
    at the same tile can never disagree about which province they are in.
    """
    if cm is None:
        return rows
    from . import stratobj
    try:
        sf = campstrat.read_strat(cm.mod, getattr(cm, "campaign", "")
                                  or campstrat.DEFAULT_CAMPAIGN)
        voc = stratobj.Vocabulary(cm.mod, sf, cm)
    except Exception:                                           # noqa: BLE001
        voc = None
    idx = cm.index
    w, h = idx.width, idx.height
    for sp in rows:
        # A spawn whose character line carries no x/y has no place at all, and
        # resolving it would resolve the (0,0) its fields default to - which on
        # every real map is the bottom-left corner, usually ocean. It would then
        # be counted as a spawn at sea, which is a fault invented out of a
        # missing field. It stays unresolved and `no_coordinate` counts it.
        if not sp.char_line:
            continue
        ix, iy = cm.image_xy(sp.x, sp.y)
        if not (0 <= ix < w and 0 <= iy < h):
            sp.off_map = True
            continue
        sp.at_sea = bool(cm.sea[iy * w + ix])
        if voc is not None:
            sp.province = voc.province_at(sp.x, sp.y)
        else:
            reg = idx.at(ix, iy)
            sp.province = reg.name if reg is not None else ""
        if not sp.province and not sp.at_sea:
            reg = idx.at(ix, iy)
            sp.undeclared = reg is not None and reg.record is None
    return rows


def positions(mod, campaign: str = "", cm=None) -> List[Dict]:
    """The marker-layer rows, in the shape 17d's layer already draws.

    The same keys :func:`unittransfer.campstrat.markers` and
    :func:`unittransfer.campevents.positions` return, so the layer gains a
    category rather than a second overlay - which is 18b's ruling, made for the
    reason that two overlays each knowing half of what stands on a tile is how a
    tooltip ends up telling you half the truth.
    """
    rows = resolve(scan(mod, campaign), cm)
    out: List[Dict] = []
    for sp in rows:
        if not sp.char_line:
            continue                    # no coordinate: nothing to draw
        out.append({"kind": "spawn", "name": sp.name or sp.faction,
                    "type": sp.type or sp.kind, "faction": sp.faction,
                    "x": sp.x, "y": sp.y, "line": sp.char_line,
                    "rel": sp.rel, "units": len(sp.units),
                    "at_sea": sp.at_sea, "province": sp.province})
    return out


def dead_units(mod, rows: List[Spawn]) -> List[str]:
    """Unit names in these spawns that this mod's EDU does not declare.

    Reported, never refused, and counted rather than listed per row - 32c's
    baseline rule, which this mod is the reason for. Measured: **DaC's 3,822
    unit lines are clean, every one**, which is what validates the parse; Third
    Age Reforged's Fellowship script names 247 units of 431 that its own EDU
    does not have, the commonest being "Mordor Orcs Super" 40 times against a
    roster that has "Mordor Orcs". A mod whose roster cannot be read gets an
    empty list rather than 431 false findings.
    """
    try:
        known = {u.type.lower() for u in mod.edu.units}
    except (OSError, AttributeError, ValueError):
        return []
    if not known:
        return []
    return sorted({u for sp in rows for u in sp.units
                   if u and u.lower() not in known})


def view(mod, cm=None, campaign: str = "") -> dict:
    """The panel's whole answer: the rows, the counts and what looks wrong."""
    rows = resolve(scan(mod, campaign), cm)
    by_faction: Dict[str, int] = {}
    for sp in rows:
        if sp.faction:
            by_faction[sp.faction] = by_faction.get(sp.faction, 0) + 1
    # An admiral at sea is a fleet. Anything else at sea is worth saying, and
    # saying is all it is: it is somebody else's campaign and the reason is not
    # established here.
    afloat = [sp for sp in rows if sp.at_sea and sp.type.lower() in AFLOAT]
    aground = [sp for sp in rows if sp.at_sea and sp.type.lower() not in AFLOAT]
    return {
        "mod": getattr(mod, "name", ""),
        "campaign": campaign,
        "files": sorted({sp.rel for sp in rows}),
        "rows": [sp.payload() for sp in rows],
        "armies": len([s for s in rows if s.kind == "army"]),
        "characters": len([s for s in rows if s.kind == "character"]),
        "units": sum(len(s.units) for s in rows),
        "placed": len([s for s in rows if s.char_line]),
        "no_coordinate": len([s for s in rows if not s.char_line]),
        "in_province": len([s for s in rows if s.province]),
        "off_map": len([s for s in rows if s.off_map]),
        "undeclared": len([s for s in rows if s.undeclared]),
        "at_sea": len(afloat) + len(aground),
        "at_sea_afloat": len(afloat),
        "at_sea_aground": len(aground),
        "factions": by_faction,
        "dead_units": dead_units(mod, rows),
        "read_only": True,
    }


#: The columns the export writes, in order. Chosen so the file is useful in a
#: spreadsheet and readable in a terminal, and so that every row can be taken
#: back to the line it came from.
COLUMNS = ("file", "line", "kind", "faction", "name", "type", "x", "y",
           "units", "province", "at_sea", "undeclared")


def _csv_cell(value) -> str:
    s = "" if value is None else str(value)
    if any(c in s for c in ',"\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def export_text(rows: List[Spawn]) -> str:
    """The spawns as CSV, one row each, with the line they came from.

    **A list wants a list format.** The map screen's only export until now is
    16g's per-faction TGA, which is right for a picture and useless for two and
    a half thousand rows; this is the other kind. It is also the honest shape
    for a read-only scan: a file somebody can sort, filter and paste into a bug
    report, produced without the script being touched.
    """
    out = [",".join(COLUMNS)]
    for sp in rows:
        out.append(",".join(_csv_cell(v) for v in (
            sp.rel, sp.char_line or sp.line, sp.kind, sp.faction, sp.name,
            sp.type, sp.x, sp.y, len(sp.units), sp.province,
            "yes" if sp.at_sea else "",
            "yes" if sp.undeclared else "")))
    return "\n".join(out) + "\n"


def export(mod, cm=None, campaign: str = "") -> dict:
    """Write the CSV into the cache folder and say where it went."""
    from . import config
    rows = resolve(scan(mod, campaign), cm)
    text = export_text(rows)
    folder = Path(config.cache_dir()) / "spawns"
    folder.mkdir(parents=True, exist_ok=True)
    stem = (campaign or campstrat.DEFAULT_CAMPAIGN).replace("/", "_")
    path = folder / f"{getattr(mod, 'name', 'mod')}-{stem}-spawns.csv"
    path.write_text(text, encoding="utf-8")
    return {"file": path.name, "folder": str(folder), "rows": len(rows),
            "bytes": len(text.encode("utf-8"))}
