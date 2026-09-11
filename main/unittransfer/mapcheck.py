"""The validator: everything that stops a campaign map loading. Phase 16f.

16a to 16e read the map, drew it, made one region editable and let a brush
change the pixels. This is the part that says whether what came out of all that
will start. It is the union of four reference tools' rule sets - Demir's
editor, Mylae's eight checks, TWMapReader's twenty-three and Geomod's debugger
- with the duplicates folded together and every rule carrying the source that
says it is a rule at all.

**A rule with no evidence reports nothing.** This is the load-bearing decision
of the phase and it is the one a validator gets wrong. The game's own ``data/``
is packed: ``descr_climates.txt`` is not on disk, ``descr_sm_resources.txt`` is
not on disk, and the region and settlement name file is not on disk. A checker
that reads "no climate is declared" as "every climate colour is undeclared"
reports 11 faults, 55,755 tiles and 112 missing name keys against a map that
ships with the game and works. So every rule that needs a vocabulary asks for
it first, and a missing one puts a line in :attr:`Report.skipped` saying which
file would have to exist - never a finding. Absence of the evidence is not the
finding.

**A finding is identified by what it is about, not by where it is written.**
:attr:`Finding.key` is a hash of the rule, the file and the thing - a region's
name, a tile's coordinates, a resource's name and position - so it survives
every edit that shifts a line number. That is what makes the baseline work:
:func:`take_baseline` stamps the keys a mod already had when it was untouched,
and from then on those findings are still shown and still counted but they no
longer block a save. A mod is somebody else's work with somebody else's bugs in
it, and a tool that refuses to save until the user has fixed 40 faults they did
not create is a tool nobody uses twice.

**Every fatal here is a crash somebody has had.** The three severities are
``fatal`` (the map will not load, or loads and crashes), ``warn`` (wrong, and
the game runs) and ``note`` (worth knowing, not wrong). Only ``fatal`` blocks,
and only when it is not in the baseline.

Three auto-fixes, and they are Geomod's debugger's three::

    heights_black       ambiguous (0,0,0) altitudes on land -> (1,1,1)
    resource_duplicate  the second of two identical resource lines, deleted
    resource_position   a resource that is off the grid or in the sea, deleted

Vanilla is the measurement for the first one, and it is a better example than
the one this phase was scoped with. ``map_heights.tga`` has 55 tiles painted
pure black on land that ``map_ground_types.tga`` calls land, and
:func:`mapvocab.is_sea_height` has to read black as sea because that is what the
engine does. Two of those 55 have a port standing on them - Nottingham's, and
**Ragusa's**, which is the port bug Geomod's manual names its debugger action
after. The fix is the one Geomod makes: black is ambiguous, ``(1,1,1)`` is not,
and the picture is identical.

Everything a fix writes goes through one backup set and one log entry, so the
Log's Undo puts it back byte-exact - the same route :func:`campaint.apply_paint`
takes, for the same reason.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from PIL import Image

from . import campmap, campstrat, mapvocab
from .campaint import block
from .campmap import (ENCODING, LAYER_BY_CODE, RWM_REL,
                      CampaignMap, MapError, Rgb, key)
from .maptga import encode
from .mapvocab import PORT_RGB, SETTLEMENT_RGB

#: How many findings one rule may list individually before the rest are folded
#: into a single row with a count. Each listed finding carries a tile or a line,
#: which is what the jump button needs; a folded row carries the first one.
ROW_MAX = 60

#: The three severities, worst first. Only ``fatal`` blocks a save, and only
#: when the untouched mod did not already have it.
SEVERITIES = ("fatal", "warn", "note")

#: The three features that make up a river network on ``map_features.tga``. A
#: cliff or a land bridge is not part of it.
#:
#: :mod:`unittransfer.mapvocab` owns the tuple as of 20a, because the map
#: screen's river overlay draws exactly the tiles these rules walk, and a second
#: list of what a river is made of is how a picture and its validator come to
#: disagree. Kept re-exported under this name: the rules below read better for
#: it, and it was already the name in use here.
RIVER_CODES = mapvocab.RIVER_CODES


# ---------------------------------------------------------------------------
# a finding


@dataclass
class Finding:
    """One thing that is wrong, and enough to go and look at it.

    ``what`` is the identity the fingerprint is built from and it never
    contains a line number: a region's name, a tile's coordinates, a resource's
    name and position. Adding a line to a file must not turn every finding
    below it into a new one, or the baseline would be worthless after the first
    edit.
    """

    code: str
    severity: str
    message: str
    #: relative to the mod's ``data/``, so the UI can name the file
    file: str = ""
    #: 1-based, or 0 for a finding that is about pixels rather than text
    line: int = 0
    #: image coordinates of the tile to jump to, or ``None``
    tile: Optional[Tuple[int, int]] = None
    what: str = ""
    #: the auto-fix that would clear this, or ``""``
    fix: str = ""
    #: how many identical faults this row stands for, when a rule folded them
    count: int = 1
    #: filled in by :func:`run` from the mod's stamped baseline
    baseline: bool = False

    @property
    def key(self) -> str:
        raw = f"{self.code}|{self.file}|{self.what}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def payload(self, cm: Optional[CampaignMap] = None) -> dict:
        out = {"code": self.code, "severity": self.severity,
               "message": self.message, "file": self.file, "line": self.line,
               "tile": list(self.tile) if self.tile else None,
               "game": None, "fix": self.fix, "count": self.count,
               "baseline": self.baseline, "key": self.key}
        if self.tile and cm is not None:
            out["game"] = list(cm.game_xy(*self.tile))
        return out


@dataclass
class Rule:
    """One rule, and who says it is one.

    ``source`` is not decoration. Every rule here came from a tool, a manual or
    a measurement, and a validator whose rules have no provenance is a list of
    somebody's opinions that nobody can argue with later.
    """

    code: str
    label: str
    #: what a finding of this rule usually is. A rule may still raise the
    #: severity of one finding - a stray altitude is a warning until a port is
    #: standing on it.
    severity: str
    source: str
    fn: Callable[["Check"], Iterable[Finding]] = None  # type: ignore[assignment]


RULES: List[Rule] = []


def rule(code: str, label: str, severity: str, source: str):
    def wrap(fn):
        RULES.append(Rule(code, label, severity, source, fn))
        return fn
    return wrap


RULE_BY_CODE: Dict[str, Rule] = {}


# ---------------------------------------------------------------------------
# the context every rule reads


def _triples(img: Image.Image) -> bytes:
    return img.convert("RGB").tobytes()


def _at(data: bytes, width: int, x: int, y: int) -> Rgb:
    i = (y * width + x) * 3
    return data[i], data[i + 1], data[i + 2]


def _find(data: bytes, width: int, rgb: Rgb, limit: int = 0
          ) -> List[Tuple[int, int]]:
    """Every tile carrying ``rgb``, in image coordinates.

    ``bytes.find`` in a loop rather than a scan over every pixel: the hits are
    what costs, not the misses, and on a 510x487 map the difference between the
    two is the difference between the whole run fitting in a second and not.
    The offset has to land on a pixel boundary - a colour's three bytes can
    match across two pixels - so a hit at an unaligned offset is stepped over
    rather than reported.
    """
    want = bytes(rgb)
    out: List[Tuple[int, int]] = []
    at = data.find(want)
    while at >= 0:
        if at % 3 == 0:
            px = at // 3
            out.append((px % width, px // width))
            if limit and len(out) >= limit:
                return out
            at = data.find(want, at + 3)
        else:
            at = data.find(want, at + 1)
    return out


def _colours(img: Image.Image, cap: int = 1 << 16) -> List[Tuple[int, Rgb]]:
    """``[(count, rgb)]`` for every distinct colour, or ``[]`` past ``cap``."""
    got = img.convert("RGB").getcolors(cap)
    return list(got or [])


class Check:
    """Everything the rules read, gathered once and shared by all of them.

    A layer is decoded through :class:`~unittransfer.campmap.CampaignMap`, which
    the caller may already be holding with unsaved paint in it - and that is
    deliberate. The validator has to be able to answer "would this save load?"
    about the map on the screen, not about the one still on disk.

    Anything that cannot be read is recorded in :attr:`skipped` and the rules
    that needed it yield nothing. A rule that cannot run is not a rule that
    passed, and the report says which is which.
    """

    def __init__(self, mod, cm: CampaignMap, campaign: str = ""):
        self.mod = mod
        self.cm = cm
        self.width = cm.terrain.width
        self.height = cm.terrain.height
        self.skipped: List[dict] = []
        self._px: Dict[str, Optional[bytes]] = {}
        self._rivers: Optional[Set[Tuple[int, int]]] = None

        # `campaign_rel` and not the raw word: 20b's browser is the first
        # thing that lets a campaign name come off the page, and the label
        # two lines down is what a backup is filed under.
        self.campaign = campstrat.campaign_rel(campaign)
        self.strat: Optional[campstrat.StratFile] = None
        self.strat_rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{self.campaign}/"
                          f"{campstrat.STRAT_NAME}")
        try:
            self.strat = campstrat.read_strat(mod, self.campaign)
        except (OSError, ValueError) as exc:
            self.skip("descr_strat.txt", f"{self.strat_rel} could not be read "
                                         f"({exc}), so nothing in the campaign "
                                         f"itself is checked")

        # Both of these are allowed to come back empty, and an empty one turns
        # its rules off rather than making everything a fault. See the module
        # docstring: the game's own data is packed, and neither file is on disk.
        self.vocab = campmap.region_vocab(mod)
        self.names = campmap.shown_names(mod)

    # -- the pieces ----------------------------------------------------------

    def skip(self, what: str, why: str) -> None:
        self.skipped.append({"what": what, "why": why})

    def px(self, code: str) -> Optional[bytes]:
        """One layer at one pixel per tile, as raw RGB bytes, or ``None``.

        ``None`` means the layer is missing or the wrong shape, and the reason
        is already in :attr:`skipped` by the time it is returned.
        """
        if code not in self._px:
            try:
                self.cm.require_grid(code)
                self._px[code] = _triples(self.cm.tiles(code))
            except (MapError, OSError) as exc:
                self._px[code] = None
                self.skip(LAYER_BY_CODE[code]["file"], str(exc))
        return self._px[code]

    @property
    def index(self) -> Optional[campmap.RegionIndex]:
        try:
            return self.cm.index
        except MapError as exc:
            self.skip("map_regions.tga", str(exc))
            return None

    @property
    def sea(self) -> Optional[bytes]:
        try:
            return self.cm.sea
        except MapError as exc:
            self.skip("the sea mask", str(exc))
            return None

    @property
    def rivers(self) -> Set[Tuple[int, int]]:
        """Every tile that is part of a river, by the three feature colours."""
        if self._rivers is None:
            data = self.px("features")
            out: Set[Tuple[int, int]] = set()
            if data:
                for code in RIVER_CODES:
                    f = mapvocab.feature(code)
                    if f:
                        out.update(_find(data, self.width, f["rgb"]))
            self._rivers = out
        return self._rivers

    def is_sea(self, x: int, y: int) -> bool:
        sea = self.sea
        return bool(sea and sea[y * self.width + x])

    def in_grid(self, x: int, y: int) -> bool:
        return self.cm.terrain.in_bounds(x, y)

    def rel(self, name: str) -> str:
        """The file a finding about ``name`` names: the copy this map read.

        A campaign that ships its own ``map_heights.tga`` is judged on it, so a
        finding about its heights names that file and a fix writes it, rather
        than world/maps/base's, which the campaign never reads.
        """
        return campmap.rel_of(self.cm, name)


# ---------------------------------------------------------------------------
# 1) the layers themselves


@rule("layer.size", "Layer shapes", "fatal",
      "The arbiter's size table; every reference tool checks it first")
def _r_layer_size(ck: Check) -> Iterable[Finding]:
    """A layer whose size does not follow from ``descr_terrain.txt``.

    The classic map crash, and the one worth catching before anything else:
    every rule below reads two layers against each other by tile index, so a
    layer one pixel out is not a finding, it is an ``IndexError`` in some rule
    that had nothing to do with it.
    """
    for line in ck.cm.check_layers():
        name = line.split(":", 1)[0]
        yield Finding("layer.size", "fatal", line,
                      file=ck.rel(name) if name.endswith(".tga") else "",
                      what=line)


@rule("layer.colour_cap", "Region colour cap", "fatal",
      "The arbiter: 200 colours in map_regions.tga, markers included")
def _r_colour_cap(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if idx is None:
        return
    used = len(idx.by_key)
    if used > mapvocab.MAX_REGION_COLOURS:
        yield Finding(
            "layer.colour_cap", "fatal",
            f"map_regions.tga has {used} distinct colours and the engine's cap "
            f"is {mapvocab.MAX_REGION_COLOURS}, the two marker colours "
            f"included. Everything past the cap is a province the game never "
            f"sees.",
            file=ck.rel("map_regions.tga"), what="cap")


# ---------------------------------------------------------------------------
# 2) descr_regions.txt against the pixels


@rule("region.duplicate_colour", "Duplicate region colours", "fatal",
      "Mylae's check 2; Demir refuses the same colour twice on a save")
def _r_duplicate_colour(ck: Check) -> Iterable[Finding]:
    """Two records with one colour. The second province owns no tiles at all.

    Not "the map has two regions painted the same" - the map cannot tell them
    apart, so there is one region on it and one record pointing at somebody
    else's land.
    """
    seen: Dict[int, campmap.RegionRecord] = {}
    for rec in ck.cm.regions.records:
        first = seen.get(rec.rgb_key)
        if first is None:
            seen[rec.rgb_key] = rec
            continue
        yield Finding(
            "region.duplicate_colour", "fatal",
            f"{rec.name} is declared rgb({rec.rgb[0]}, {rec.rgb[1]}, "
            f"{rec.rgb[2]}), which {first.name} already has. The map cannot "
            f"tell them apart, so one of the two owns every tile and the other "
            f"owns none.",
            file=ck.rel("descr_regions.txt"), line=rec.rgb_line + 1, what=f"{rec.name}|{first.name}")


@rule("region.reserved_colour", "Reserved colours", "fatal",
      "The marker colours: black is a settlement, white is a port")
def _r_reserved_colour(ck: Check) -> Iterable[Finding]:
    for rec in ck.cm.regions.records:
        for rgb, what in ((SETTLEMENT_RGB, "the settlement marker"),
                          (PORT_RGB, "the port marker")):
            if rec.rgb == rgb:
                yield Finding(
                    "region.reserved_colour", "fatal",
                    f"{rec.name} claims rgb({rgb[0]}, {rgb[1]}, {rgb[2]}), "
                    f"which is {what} rather than a province colour. The "
                    f"region scan skips it, so the province does not exist.",
                    file=ck.rel("descr_regions.txt"), line=rec.rgb_line + 1, what=rec.name)


@rule("region.no_pixels", "Regions with no tiles", "fatal",
      "Mylae's check 3; the arbiter calls it a load crash")
def _r_no_pixels(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if idx is None:
        return
    for rec in idx.empty_records:
        yield Finding(
            "region.no_pixels", "fatal",
            f"{rec.name} is declared rgb({rec.rgb[0]}, {rec.rgb[1]}, "
            f"{rec.rgb[2]}) and not one pixel of map_regions.tga is that "
            f"colour. A region with no tiles is legal to write and fatal to "
            f"play.",
            file=ck.rel("descr_regions.txt"), line=rec.rgb_line + 1, what=rec.name)


@rule("region.undeclared", "Provinces nobody declared", "fatal",
      "TWMapReader's unmapped-colour pass, with 16c's sea heuristic")
def _r_undeclared(ck: Check) -> Iterable[Finding]:
    """A colour on the map that no record claims, and that is not the ocean.

    The heuristic is 16c's and the measurements say it decides nothing on a
    knife edge: vanilla's four undeclared colours are 100% sea, DaC's ocean is
    99.94% and DaC's one undeclared province is 0%. Half is the line, with
    three orders of magnitude of daylight either side of it.
    """
    idx = ck.index
    if idx is None:
        return
    sea = campmap.sea_pixels(ck.cm)
    for r in idx.regions:
        if r.record is not None or not r.pixels:
            continue
        wet = sea.get(key(r.rgb), 0)
        if wet * 2 >= r.pixels:
            continue
        yield Finding(
            "region.undeclared", "fatal",
            f"{r.pixels:,} tiles are painted rgb({r.rgb[0]}, {r.rgb[1]}, "
            f"{r.rgb[2]}) and descr_regions.txt declares no region with that "
            f"colour. None of it is sea, so it is land the game has no "
            f"province for.",
            file=ck.rel("map_regions.tga"), tile=r.anchor,
            what=f"{r.rgb[0]},{r.rgb[1]},{r.rgb[2]}")


@rule("region.record", "Region record fields", "warn",
      "16d's check_record: the religion total is the arbiter's load crash")
def _r_record_fields(ck: Check) -> Iterable[Finding]:
    """Everything 16d already says about one record, as findings.

    The rules live in :func:`campmap.check_record` because the region panel
    enforces them as somebody types, and running a second copy of them here is
    how the two would come to disagree. This is the same call the panel makes.
    """
    for rec in ck.cm.regions.records:
        for f in campmap.check_record(rec, ck.vocab):
            yield Finding("region.record", "fatal" if f["fatal"] else "warn",
                          f"{rec.name}: {f['message']}",
                          file=ck.rel("descr_regions.txt"), line=f["line"],
                          what=f"{rec.name}|{f['field']}|{f['message'][:60]}")


@rule("region.wasteland_last", "A settlement-less region must be last", "warn",
      "The arbiter: a record with no settlement has to be the final entry")
def _r_wasteland_last(ck: Check) -> Iterable[Finding]:
    recs = ck.cm.regions.records
    for i, rec in enumerate(recs):
        if rec.wasteland and i != len(recs) - 1:
            yield Finding(
                "region.wasteland_last", "warn",
                f"{rec.name} has no settlement line, and the arbiter says such "
                f"a record must be the last one in the file. It is entry "
                f"{i + 1} of {len(recs)}.",
                file=ck.rel("descr_regions.txt"), line=rec.span[0] + 1, what=rec.name)


# ---------------------------------------------------------------------------
# 3) the markers


@rule("marker.no_settlement", "Regions with no settlement pixel", "fatal",
      "Gigantus: every province needs exactly one black pixel")
def _r_no_settlement(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if idx is None:
        return
    for r in idx.regions:
        if r.record is None or not r.pixels or r.settlement:
            continue
        yield Finding(
            "marker.no_settlement", "fatal",
            f"{r.name} owns {r.pixels:,} tiles and has no settlement pixel on "
            f"any of them. The engine has nowhere to put the city.",
            file=ck.rel("map_regions.tga"), tile=r.anchor, what=r.name)


@rule("marker.extra", "More than one marker in a region", "fatal",
      "Mylae's check 5; Gigantus's cardinal rule decides which region owns one")
def _r_extra_markers(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if idx is None:
        return
    for at in idx.extra_settlements[:ROW_MAX]:
        owner = _marker_owner(idx, at, "settlement")
        yield Finding(
            "marker.extra", "fatal",
            f"a second settlement pixel at {at[0]},{at[1]}"
            + (f", in {owner}" if owner else "")
            + ". A region gets one city, and the engine takes the first it "
              "scans and leaves the other standing in nothing.",
            file=ck.rel("map_regions.tga"), tile=at,
            what=f"settlement|{at[0]},{at[1]}")
    for at in idx.extra_ports[:ROW_MAX]:
        owner = _marker_owner(idx, at, "port")
        yield Finding(
            "marker.extra", "warn",
            f"a second port pixel at {at[0]},{at[1]}"
            + (f", for {owner}" if owner else "")
            + ". Only one of them will ever be a port.",
            file=ck.rel("map_regions.tga"), tile=at,
            what=f"port|{at[0]},{at[1]}")


def _marker_owner(idx: campmap.RegionIndex, at: Tuple[int, int],
                  kind: str) -> str:
    """Which region already has the marker this one is a second of."""
    for r in idx.regions:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if (at[0] + dx, at[1] + dy) == (r.settlement if kind == "settlement"
                                            else r.port):
                return r.name
    return ""


@rule("marker.orphan", "Markers standing in no region", "fatal",
      "16a found DaC's, at image (339,65), inside a colour nobody declares")
def _r_orphan_markers(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if idx is None:
        return
    for at in idx.orphan_settlements[:ROW_MAX]:
        yield Finding(
            "marker.orphan", "fatal",
            f"The settlement pixel at {at[0]},{at[1]} has no region on any "
            f"cardinal side, so no province owns it. Usually a city painted on "
            f"the map and never written into descr_regions.txt.",
            file=ck.rel("map_regions.tga"), tile=at,
            what=f"settlement|{at[0]},{at[1]}")
    # A port with no sea at all beside it is also undecidable - the dock rule
    # needs water on one side - but "nobody owns it" is the vaguer half of that
    # and `port.inland` says the sharper half. Reported once, by the rule that
    # names the actual fault.
    for at in idx.undecided_ports[:ROW_MAX]:
        if not _has_sea_beside(ck, at):
            continue
        yield Finding(
            "marker.orphan", "warn",
            f"The port pixel at {at[0]},{at[1]} touches no single region the "
            f"cardinal rule can give it to, so which province gets the port is "
            f"whatever the engine decides.",
            file=ck.rel("map_regions.tga"), tile=at,
            what=f"port|{at[0]},{at[1]}")


def _has_sea_beside(cm: CampaignMap, sea: bytes, at: Tuple[int, int]) -> bool:
    x, y = at
    w, h = cm.terrain.width, cm.terrain.height
    return any(0 <= x + dx < w and 0 <= y + dy < h
               and sea[(y + dy) * w + x + dx]
               for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))


#: What the four marker rules are about, in the order they are reported. The
#: file each names is the layer the fault is IN, which is where somebody has to
#: go and paint to clear it - not ``map_regions.tga``, where the marker is.
MARKER_LAYER = {
    "marker.ground": "map_ground_types.tga",
    "marker.feature": "map_features.tga",
    "marker.sea": "map_heights.tga",
    "port.inland": "map_regions.tga",
}


def marker_faults(cm: CampaignMap, at: Sequence[int], kind: str,
                  ground: Optional[bytes] = None, feats: Optional[bytes] = None,
                  sea: Optional[bytes] = None) -> List[dict]:
    """What is wrong with the tile a settlement or a port is standing on.

    **The one copy of these four rules.** The paint tool's new-province wizard
    asks the same question about a marker it is about to place that the
    validator asks about every marker already on the map, and 16f's brief was
    explicit that those must not become two rule sets that drift apart. So the
    predicate lives here, the wizard calls it through
    :func:`campaint._marker_problems`, and the four rules below are this
    function filtered by code.

    Each entry is ``{code, fatal, tail}``: the tail is the clause after "X's
    settlement pixel at 4,5", so a caller can put its own subject in front of
    it. The layer bytes may be passed in already fetched - a rule that scans two
    hundred markers must not copy a 745 KB layer two hundred times.
    """
    x, y = int(at[0]), int(at[1])
    w = cm.terrain.width
    i = y * w + x
    out: List[dict] = []
    try:
        ground = _triples(cm.tiles("ground_types")) if ground is None else ground
        feats = _triples(cm.tiles("features")) if feats is None else feats
        sea = cm.sea if sea is None else sea
    except MapError as exc:
        return [{"code": "layer.size", "fatal": False, "tail": str(exc)}]

    # A port is the exception to the ground rule: it stands on the coast with
    # its dock in the water. Only impassable land is a crash under one. Sea
    # ground under a port is still worth saying - 142 of the 142 port pixels on
    # the two shipped maps measured are on land ground, so it is an anomaly -
    # but DaC ships five of them and runs, so it is not a fatal.
    g = mapvocab.ground_at(_at(ground, w, x, y))
    if g is not None:
        if g["code"] in (mapvocab.BLOCKING_GROUND if kind == "settlement"
                         else ("impassable_land",)):
            out.append({"code": "marker.ground", "fatal": True,
                        "tail": f"is standing on {g['name']}, which nothing can "
                                f"stand on."})
        elif kind == "port" and g["code"] in mapvocab.SEA_GROUND:
            out.append({"code": "marker.ground", "fatal": False,
                        "tail": f"is standing on {g['name']}. A port pixel goes "
                                f"on the coastal land tile, not in the water: "
                                f"every one of the 142 on the maps measured is "
                                f"on land ground."})

    f = mapvocab.feature_at(_at(feats, w, x, y))
    if f is not None and f["code"] in mapvocab.FATAL_UNDER_SETTLEMENT:
        out.append({"code": "marker.feature", "fatal": True,
                    "tail": f"is on a {f['name'].lower()} in map_features.tga. "
                            f"The engine crashes to the menu on that one."})

    if sea[i]:
        black = _at(_triples(cm.tiles("heights")), w, x, y) == (0, 0, 0)
        out.append({
            "code": "marker.sea", "fatal": True, "ambiguous": black,
            "tail": "is on a tile the engine reads as sea"
                    + (". Its altitude is pure black, which map_heights.tga "
                       "cannot tell from sea level. Geomod's fix applies: black "
                       "becomes (1,1,1), and the picture does not change."
                       if black else ".")})

    if kind == "port" and not _has_sea_beside(cm, sea, (x, y)):
        out.append({"code": "port.inland", "fatal": True,
                    "tail": "has no sea tile on any of its four sides, so "
                            "nothing can ever dock there and no province can be "
                            "given the port."})
    return out


def _marker_rule(ck: Check, code: str) -> Iterable[Finding]:
    """One of the four marker rules: :func:`marker_faults`, filtered by code."""
    idx = ck.index
    ground, feats, sea = ck.px("ground_types"), ck.px("features"), ck.sea
    if idx is None or ground is None or feats is None or sea is None:
        return
    for r in idx.regions:
        for at, kind in ((r.settlement, "settlement"), (r.port, "port")):
            if at is None:
                continue
            for f in marker_faults(ck.cm, at, kind, ground, feats, sea):
                if f["code"] != code:
                    continue
                yield Finding(
                    code, "fatal" if f["fatal"] else "warn",
                    f"{r.name or 'An undeclared region'}'s {kind} pixel at "
                    f"{at[0]},{at[1]} {f['tail']}",
                    file=ck.rel(MARKER_LAYER[code]) if code in MARKER_LAYER
                    else "", tile=at,
                    fix="heights_black" if f.get("ambiguous") else "",
                    what=f"{kind}|{at[0]},{at[1]}")


@rule("marker.ground", "A marker on ground nothing can stand on", "fatal",
      "The TWCenter index: a settlement on sea or impassable land is the "
      "back-to-menu crash")
def _r_marker_ground(ck: Check) -> Iterable[Finding]:
    return _marker_rule(ck, "marker.ground")


@rule("marker.feature", "A marker on a river or a volcano", "fatal",
      "The arbiter's four fatal features under a settlement")
def _r_marker_feature(ck: Check) -> Iterable[Finding]:
    return _marker_rule(ck, "marker.feature")


@rule("marker.sea", "A marker on a sea tile", "fatal",
      "The height rule (TWMapReader): a tile is sea by its altitude, not by "
      "its ground type")
def _r_marker_sea(ck: Check) -> Iterable[Finding]:
    """A settlement or port on a tile the engine calls sea.

    Worth having as well as the ground-type rule, because the two read different
    layers and disagree exactly where it matters. Vanilla's two hits are both
    ports on perfectly good land ground standing on a pure-black altitude -
    Nottingham's and Ragusa's - and only this rule sees them.
    ``heights_black`` is the fix.
    """
    return _marker_rule(ck, "marker.sea")


@rule("port.inland", "Ports with no sea beside them", "fatal",
      "Mylae's check 6; a port with nothing to sail out of is a dead province")
def _r_port_inland(ck: Check) -> Iterable[Finding]:
    """A white pixel with no water beside it.

    Every port pixel on the layer, not only the ones a region owns, and that is
    the whole reason this rule exists separately from :func:`_r_orphan_markers`:
    the dock rule needs sea on one side to decide an owner at all, so an inland
    port is by construction a port nobody owns - and "nobody owns it" is the
    symptom while "there is no water" is the fault.
    """
    idx, sea = ck.index, ck.sea
    if idx is None or sea is None:
        return
    owner = {r.port: r.name for r in idx.regions if r.port}
    for x, y in idx.ports[:ROW_MAX]:
        if _has_sea_beside(ck.cm, sea, (x, y)):
            continue
        who = owner.get((x, y)) or "an undeclared region"
        yield Finding(
            "port.inland", "fatal",
            f"The port pixel at {x},{y} ({who}) has no sea tile on any of its "
            f"four sides, so nothing can ever dock there and no province can be "
            f"given the port.",
            file=MARKER_LAYER["port.inland"], tile=(x, y), what=f"{x},{y}")


# ---------------------------------------------------------------------------
# 4) colours no table names


def _unknown_colours(ck: Check, code: str, namer, label: str, rule_code: str,
                     severity: str) -> Iterable[Finding]:
    data = ck.px(code)
    if data is None:
        return
    img = ck.cm.tiles(code)
    got = _colours(img)
    if not got:
        ck.skip(LAYER_BY_CODE[code]["file"],
                "more than 65,536 distinct colours, which is a picture rather "
                "than a layer of values - not censused")
        return
    for count, rgb in sorted(got, key=lambda c: -c[0]):
        if namer(rgb) is not None:
            continue
        where = _find(data, ck.width, rgb, limit=1)
        yield Finding(
            rule_code, severity,
            f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]}) is on {count:,} tile"
            f"{'' if count == 1 else 's'} of "
            f"{LAYER_BY_CODE[code]['file']} and {label}. The engine reads it as "
            f"whatever it happens to fall nearest to, which is not a decision "
            f"anybody made.",
            file=ck.rel(LAYER_BY_CODE[code]['file']),
            tile=where[0] if where else None, count=count,
            what=f"{rgb[0]},{rgb[1]},{rgb[2]}")


@rule("feature.unknown", "Feature colours nothing names", "fatal",
      "16a found DaC's stray (1,1,1); the table is the arbiter's seven")
def _r_feature_colours(ck: Check) -> Iterable[Finding]:
    """A colour in ``map_features.tga`` that is none of the seven features.

    The headline finding of this phase. DaC ships a single ``(1,1,1)`` pixel
    here, one value away from the black that means "no feature", and no tool
    before this one says so - Geomod rounds to the nearest known colour, which
    is precisely how a pixel like that survives for years.
    """
    return _unknown_colours(ck, "features", mapvocab.feature_at,
                            "no feature in the table is that colour",
                            "feature.unknown", "fatal")


@rule("ground.unknown", "Ground colours nothing names", "fatal",
      "The sixteen ground types; Mylae's table and every mod's "
      "descr_aerial_map_ground_types.txt agree on them")
def _r_ground_colours(ck: Check) -> Iterable[Finding]:
    return _unknown_colours(ck, "ground_types", mapvocab.ground_at,
                            "no ground type is that colour",
                            "ground.unknown", "fatal")


@rule("climate.unknown", "Climate colours nothing declares", "fatal",
      "Descr_climates.txt, which every mod renames - so it is read, never "
      "hardcoded")
def _r_climate_colours(ck: Check) -> Iterable[Finding]:
    """Climate colours are the mod's own, so an absent file turns this off.

    This is the rule the "no evidence, no finding" ruling was written for. The
    game's ``descr_climates.txt`` is inside a ``.pack``; reading its absence as
    "all 11 colours are undeclared" would report the stock map as broken in
    55,755 tiles.
    """
    declared = mapvocab.climate_index(ck.mod)
    if not declared:
        ck.skip("descr_climates.txt",
                "no climate is declared on disk, so no colour in "
                "map_climates.tga can be called undeclared. Every mod renames "
                "its climates, so this table is never assumed.")
        return
    return _unknown_colours(ck, "climates", lambda rgb: declared.get(key(rgb)),
                            "descr_climates.txt declares no climate with it",
                            "climate.unknown", "fatal")


# ---------------------------------------------------------------------------
# 5) rivers


@rule("river.diagonal", "Rivers joined only at a corner", "warn",
      "TWMapReader: the river mesh is built along cardinal steps")
def _r_river_diagonal(ck: Check) -> Iterable[Finding]:
    """A river tile whose only neighbour is diagonal.

    The engine walks a river cardinally. A tile that touches the rest of the
    network only at a corner is a river that stops there and starts again, and
    what the player sees is a gap. Vanilla has none of these; that zero is the
    baseline the rule was checked against.
    """
    riv = ck.rivers
    if not riv:
        return
    card = ((0, -1), (0, 1), (-1, 0), (1, 0))
    diag = ((-1, -1), (1, -1), (-1, 1), (1, 1))
    n = 0
    for x, y in sorted(riv):
        if any((x + dx, y + dy) in riv for dx, dy in card):
            continue
        if not any((x + dx, y + dy) in riv for dx, dy in diag):
            continue                       # an isolated tile, the rule below
        n += 1
        if n > ROW_MAX:
            continue
        yield Finding(
            "river.diagonal", "warn",
            f"The river tile at {x},{y} touches the rest of the river only at "
            f"a corner. The engine steps a river north, south, east and west, "
            f"so the water stops here and starts again on the far side.",
            file=ck.rel("map_features.tga"), tile=(x, y), what=f"{x},{y}")


@rule("river.isolated", "A river tile on its own", "warn",
      "Mylae's check 7; vanilla ships exactly one, at image (175,14)")
def _r_river_isolated(ck: Check) -> Iterable[Finding]:
    riv = ck.rivers
    if not riv:
        return
    around = ((0, -1), (0, 1), (-1, 0), (1, 0),
              (-1, -1), (1, -1), (-1, 1), (1, 1))
    for x, y in sorted(riv):
        if any((x + dx, y + dy) in riv for dx, dy in around):
            continue
        yield Finding(
            "river.isolated", "warn",
            f"The river tile at {x},{y} touches no other river tile at all. "
            f"One tile of water with no course through it.",
            file=ck.rel("map_features.tga"), tile=(x, y), what=f"{x},{y}")


@rule("river.rejoin", "A river that splits and rejoins", "warn",
      "TWMapReader: the river mesh is a tree, and a loop has no mouth")
def _r_river_rejoin(ck: Check) -> Iterable[Finding]:
    """A cycle in the river network, found as the edge that closes it.

    Not "a tile with three neighbours" - vanilla has 26 of those and every one
    is an ordinary tributary joining the trunk. A rejoin is a *loop*: follow the
    water and come back to where you started. That is one union-find pass over
    the four-connected river graph, and the edge that finds both ends already
    joined is the edge that closes the loop. Vanilla has none.
    """
    riv = ck.rivers
    if not riv:
        return
    parent: Dict[Tuple[int, int], Tuple[int, int]] = {p: p for p in riv}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    n = 0
    for p in sorted(riv):
        for dx, dy in ((1, 0), (0, 1)):
            q = (p[0] + dx, p[1] + dy)
            if q not in riv:
                continue
            ra, rb = find(p), find(q)
            if ra != rb:
                parent[ra] = rb
                continue
            n += 1
            if n > ROW_MAX:
                continue
            yield Finding(
                "river.rejoin", "warn",
                f"The river closes a loop at {p[0]},{p[1]}: the water leaves "
                f"here and comes back to the same tile. A river the engine can "
                f"build is a tree, and a loop has no mouth.",
                file=ck.rel("map_features.tga"), tile=p,
                what=f"{p[0]},{p[1]}|{q[0]},{q[1]}")


# ---------------------------------------------------------------------------
# 6) heights - the ambiguous altitude, and Geomod's fix for it


def _ambiguous_tiles(ck: Check) -> List[Tuple[int, int]]:
    """Land tiles whose altitude pixel is pure black.

    ``is_sea_height`` reads black as sea because the engine does, and the
    ground-type layer is the independent witness that says the tile is land.
    Where the two disagree the altitude is the one that is wrong, because a
    coastline painted in a tool that wrote 0 for "no data" is how they get
    there in the first place.
    """
    heights, ground = ck.px("heights"), ck.px("ground_types")
    if heights is None or ground is None:
        return []
    out = []
    for at in _find(heights, ck.width, (0, 0, 0)):
        g = mapvocab.ground_at(_at(ground, ck.width, *at))
        if g is not None and g["code"] not in mapvocab.SEA_GROUND:
            out.append(at)
    return out


@rule("height.ambiguous", "Ambiguous altitudes", "warn",
      "Geomod's debugger action, and vanilla's Ragusa port is one of them")
def _r_height_black(ck: Check) -> Iterable[Finding]:
    """Pure black on ``map_heights.tga`` where the ground says land.

    Black is the one altitude the engine cannot read: ``is_sea_height`` calls a
    pixel sea if it is not greyscale **or** if it is black, so ``(0,0,0)`` is
    both a valid grey and the sea case. A tile like that is land in every layer
    but the one the engine believes.

    Vanilla has 55, and two of them have a port standing on them - which is
    what the ``marker.sea`` rule reports as fatal, and what this one offers to
    fix. Geomod's action is the fix: ``(1,1,1)``, one step off black, land
    beyond argument, and no visible change to the picture.
    """
    tiles = _ambiguous_tiles(ck)
    if not tiles:
        return
    for i, at in enumerate(tiles):
        if i >= ROW_MAX:
            break
        yield Finding(
            "height.ambiguous", "warn",
            f"The tile at {at[0]},{at[1]} is land in map_ground_types.tga and "
            f"pure black in map_heights.tga, which the engine reads as sea.",
            file=ck.rel("map_heights.tga"), tile=at, fix="heights_black",
            what=f"{at[0]},{at[1]}")
    if len(tiles) > ROW_MAX:
        yield Finding(
            "height.ambiguous", "warn",
            f"Another {len(tiles) - ROW_MAX:,} tiles carry the same pure-black "
            f"altitude on land.",
            file=ck.rel("map_heights.tga"), tile=tiles[ROW_MAX],
            fix="heights_black", count=len(tiles) - ROW_MAX, what="rest")


# ---------------------------------------------------------------------------
# 7) descr_strat.txt


@rule("strat.parse", "Lines descr_strat.txt does not read as anything", "warn",
      "16b: DaC has nine, and every one is a real defect in the mod")
def _r_strat_parse(ck: Check) -> Iterable[Finding]:
    if ck.strat is None:
        return
    for i, (line, kind, message) in enumerate(ck.strat.problems):
        if i >= ROW_MAX:
            break
        yield Finding("strat.parse", "warn", message,
                      file=ck.strat_rel, line=line + 1,
                      what=f"{kind}|{message[:70]}")


@rule("strat.faction_after_diplomacy", "A faction block after the diplomacy "
      "section", "fatal",
      "The file's own order: every faction block precedes faction_standings")
def _r_faction_order(ck: Check) -> Iterable[Finding]:
    if ck.strat is None:
        return
    dip = [n for n in ck.strat.nodes
           if n.kind in ("faction_standings", "faction_relationships")]
    if not dip:
        return
    first = min(n.start for n in dip)
    for n in ck.strat.of_kind("faction"):
        if n.start <= first:
            continue
        yield Finding(
            "strat.faction_after_diplomacy", "fatal",
            f"The faction block for {n.name} starts on line {n.start + 1}, "
            f"after the diplomacy section opens on line {first + 1}. The "
            f"engine has stopped reading faction blocks by then, so this "
            f"faction has no settlements, no characters and no army.",
            file=ck.strat_rel, line=n.start + 1, what=n.name)


def _resource_rows(ck: Check) -> List[Tuple[campstrat.Node, int, int]]:
    """``(node, x, image_y)`` for every resource line that has coordinates."""
    if ck.strat is None:
        return []
    out = []
    for n in ck.strat.of_kind("resource"):
        x, y = n.get("x"), n.get("y")
        if isinstance(x, int) and isinstance(y, int):
            out.append((n, x, ck.cm.terrain.image_y(y)))
    return out


def duplicate_message(name: str, x: int, gy: int, line: int) -> str:
    """The one wording of a resource written twice on a tile, which
    :mod:`stratobj` also says of a save that would make one."""
    return (f"a second `{name}` at {x},{gy}; line {line} already puts one "
            f"there. The engine takes one and the other is a line nobody will "
            f"ever find.")


@rule("strat.resource_duplicate", "The same resource twice on one tile", "warn",
      "Geomod's debugger action: duplicate resources")
def _r_resource_duplicate(ck: Check) -> Iterable[Finding]:
    seen: Dict[Tuple[str, int, int], campstrat.Node] = {}
    for n, x, iy in _resource_rows(ck):
        k = (n.name.lower(), x, iy)
        first = seen.get(k)
        if first is None:
            seen[k] = n
            continue
        yield Finding(
            "strat.resource_duplicate", "warn",
            duplicate_message(n.name, x, ck.cm.terrain.game_y(iy),
                              first.start + 1),
            file=ck.strat_rel, line=n.start + 1, tile=(x, iy),
            fix="resource_duplicate", what=f"{n.name.lower()}|{x},{iy}|dup")


def position_faults(cm: CampaignMap, x: int, gy: int,
                    sea: Optional[bytes] = None) -> List[dict]:
    """What is wrong with the tile a resource, an event or a disaster is on.

    **The one copy of Geomod's two position checks.** The validator asks it of
    every resource and every 18b position in the file; :mod:`stratobj` asks it
    of the one resource a save is about to write. Off the grid is fatal and sea
    is a warning. Each entry is ``{code, fatal, tail, near}``: the tail is the
    clause after "`timber` is", and ``near`` is D10's answer for a sea tile -
    the nearest land, in game coordinates - or None when there is none within
    :data:`mapsnap.RADIUS`.
    """
    from . import mapsnap
    w, h = cm.terrain.width, cm.terrain.height
    iy = cm.terrain.image_y(gy)
    if not (0 <= x < w and 0 <= iy < h):
        return [{"code": "off", "fatal": True, "near": None,
                 "tail": f"at {x},{gy}, which is off a {w}x{h} map altogether."}]
    try:
        sea = cm.sea if sea is None else sea
    except MapError:
        return []
    if not sea[iy * w + x]:
        return []
    at = mapsnap.nearest(w, h, x, iy, lambda tx, ty: not sea[ty * w + tx])
    near = cm.game_xy(*at) if at is not None else None
    return [{"code": "sea", "fatal": False, "near": near,
             "tail": f"at {x},{gy}, on a tile the engine reads as sea."}]


def _land_clause(f: dict, start: Tuple[int, int]) -> str:
    """D10's clause for a sea finding: where the nearest land is."""
    from . import mapsnap
    if f["code"] != "sea":
        return ""
    return mapsnap.sentence(f["near"], start, noun="land")


@rule("strat.resource_position", "A resource off the map or in the sea", "warn",
      "Geomod's debugger action: invalid positions")
def _r_resource_position(ck: Check) -> Iterable[Finding]:
    """A resource nobody can ever trade.

    Vanilla has one - a ``timber`` at game 199,57 sitting on a sea tile - which
    is exactly the sort of finding the baseline exists for: it is real, it is
    somebody else's, and refusing to save a mod until it is gone would be
    absurd. :func:`position_faults` decides; this reports.
    """
    sea = ck.sea
    for n, x, iy in _resource_rows(ck):
        gy = ck.cm.terrain.game_y(iy)
        for f in position_faults(ck.cm, x, gy, sea):
            off = f["code"] == "off"
            yield Finding(
                "strat.resource_position", "fatal" if f["fatal"] else "warn",
                f"`{n.name}` is {f['tail']}"
                + ("" if off else " Nothing on land can reach it.")
                + _land_clause(f, (x, gy)),
                file=ck.strat_rel, line=n.start + 1,
                tile=None if off else (x, iy), fix="resource_position",
                what=f"{n.name.lower()}|{x},{gy}|{f['code']}")


@rule("strat.settlement_region", "A settlement in a region nobody declares",
      "fatal", "Descr_regions.txt is the region vocabulary for the campaign")
def _r_settlement_region(ck: Check) -> Iterable[Finding]:
    if ck.strat is None:
        return
    known = {r.name.lower() for r in ck.cm.regions.records}
    for n in ck.strat.of_kind("settlement"):
        reg = str(n.get("region") or "")
        if not reg:
            yield Finding(
                "strat.settlement_region", "fatal",
                f"The settlement block opening on line {n.start + 1} names no "
                f"region at all.",
                file=ck.strat_rel, line=n.start + 1, what=f"line|{n.start}")
        elif reg.lower() not in known:
            yield Finding(
                "strat.settlement_region", "fatal",
                f"a settlement is placed in `{reg}`, and descr_regions.txt "
                f"declares no region with that name.",
                file=ck.strat_rel, line=n.field_lines.get("region", n.start) + 1,
                what=reg)


@rule("strat.region_unowned", "A region no settlement block claims", "note",
      "Vanilla ships one - Durazzo_Province - so it is a note, not a fault")
def _r_region_unowned(ck: Check) -> Iterable[Finding]:
    if ck.strat is None:
        return
    owned = {str(n.get("region") or "").lower()
             for n in ck.strat.of_kind("settlement")}
    for rec in ck.cm.regions.records:
        if rec.wasteland or rec.name.lower() in owned:
            continue
        yield Finding(
            "strat.region_unowned", "note",
            f"{rec.name} is declared with a settlement ({rec.settlement}) and "
            f"no faction's settlement block in {ck.campaign} claims it, so "
            f"nobody starts there.",
            file=ck.strat_rel, what=rec.name)


@rule("strat.port_building", "A port building where there is no port pixel",
      "fatal", "Mylae's check 8; the building has nowhere to be built")
def _r_port_building(ck: Check) -> Iterable[Finding]:
    idx = ck.index
    if ck.strat is None or idx is None:
        return
    with_pixel = {r.name.lower() for r in idx.regions if r.port and r.record}
    for n in ck.strat.of_kind("settlement"):
        reg = str(n.get("region") or "")
        if not reg or reg.lower() in with_pixel:
            continue
        ports = [b for b in ck.strat.children_of(n, "building")
                 if "port" in (b.name or "").lower()]
        if not ports:
            continue
        yield Finding(
            "strat.port_building", "fatal",
            f"{reg} starts with a `{ports[0].name}` and map_regions.tga has no "
            f"white port pixel anywhere in it. The building has nowhere to "
            f"stand.",
            file=ck.strat_rel, line=ports[0].start + 1, what=reg)


# ---------------------------------------------------------------------------
# 8) localisation


@rule("loc.missing", "Names the player never sees", "warn",
      "The region and settlement name file; absent means unchecked, never "
      "missing")
def _r_localisation(ck: Check) -> Iterable[Finding]:
    """Region and settlement keys with no line in the names file.

    Off entirely when the file is not on disk. Vanilla keeps it inside a
    ``.pack``, so the choice here is between reporting 224 missing keys against
    the stock game and saying "there is nothing to check against" - and only one
    of those is true.
    """
    if not ck.names:
        ck.skip(campmap.REGION_NAMES_REL,
                "The region and settlement name file is not on disk, so no "
                "name can be called missing from it. Most mods ship it; the "
                "stock game keeps it inside a .pack.")
        return
    n = 0
    for rec in ck.cm.regions.records:
        for value, what in ((rec.name, "region"),
                            (rec.settlement, "settlement")):
            if not value or value in ck.names:
                continue
            n += 1
            if n > ROW_MAX:
                continue
            yield Finding(
                "loc.missing", "warn",
                f"The {what} `{value}` has no line in "
                f"{Path(campmap.REGION_NAMES_REL).name}, so the player reads "
                f"the code name on the campaign map.",
                file=campmap.REGION_NAMES_REL,
                line=(rec.name_line if what == "region"
                      else rec.settlement_line) + 1,
                what=f"{what}|{value}")


# ---------------------------------------------------------------------------
# 18b) the two files that put something on a tile without a character on it


def _event_blocks(ck: "Check") -> List[Tuple[str, str, object]]:
    """``(file, label, block)`` for every block in the two 18b files.

    Both files are read here rather than in :class:`Check`'s constructor,
    because both are optional and neither is read by any other rule: a mod with
    no ``descr_disasters.txt`` is the normal case - both installed mods ship an
    empty one - and a rule that cannot run has to be silent rather than absent.
    """
    from . import campevents
    out: List[Tuple[str, str, object]] = []
    try:
        bf, _ = campevents.read_events(ck.mod, ck.campaign)
        rel = f"{campstrat.CAMPAIGN_DIR_REL}/{ck.campaign}/{campevents.EVENTS_NAME}"
        out += [(rel, b.name or b.kind, b) for b in bf.blocks]
    except (campevents.CampEventError, OSError, ValueError):
        pass
    try:
        df, _ = campevents.read_disasters(ck.mod)
        out += [(campevents.DISASTERS_REL, b.kind, b) for b in df.blocks]
    except (campevents.CampEventError, OSError, ValueError):
        pass
    return out


@rule("event.position", "An event or disaster placed off the map or in the sea",
      "warn", "descr_events.txt's own header: a volcano fires at the position "
              "specified, a plague in the settlements at them")
def _r_event_position(ck: Check) -> Iterable[Finding]:
    """The rule 18b was told to teach this validator.

    The resource rule's shape exactly - off the grid is fatal, sea is a warning
    - because it is the same fault about the same kind of number, and a second
    wording for it would only make the two harder to compare. What is different
    is that these two files are optional and usually empty, so this yields
    nothing at all far more often than it yields anything.
    """
    sea = ck.sea
    for rel, label, b in _event_blocks(ck):
        for p in b.positions:
            for f in position_faults(ck.cm, p.x, p.y, sea):
                off = f["code"] == "off"
                yield Finding(
                    "event.position", "fatal" if f["fatal"] else "warn",
                    f"`{label}` is placed {f['tail']}"
                    + ("" if off else " A settlement event there reaches nobody.")
                    + _land_clause(f, (p.x, p.y)),
                    file=rel, line=p.line + 1,
                    tile=None if off else (p.x, ck.cm.terrain.image_y(p.y)),
                    what=f"{label.lower()}|{p.x},{p.y}|{f['code']}")


# ---------------------------------------------------------------------------
# running the lot


@dataclass
class Report:
    """One run of every rule over one map."""

    mod: str = ""
    campaign: str = ""
    findings: List[Finding] = field(default_factory=list)
    #: rules that could not run, and the file that would let them
    skipped: List[dict] = field(default_factory=list)
    #: rules that raised. A broken rule is a finding about the tool, not a
    #: reason to lose the other twenty-four.
    failed: List[dict] = field(default_factory=list)
    ms: int = 0
    baseline_at: str = ""
    baseline_keys: int = 0

    def counts(self) -> Dict[str, int]:
        out = {s: 0 for s in SEVERITIES}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out

    @property
    def blocking(self) -> List[Finding]:
        """The fatals this user is responsible for: not in the baseline."""
        return [f for f in self.findings
                if f.severity == "fatal" and not f.baseline]

    def payload(self, cm: Optional[CampaignMap] = None) -> dict:
        return {
            "mod": self.mod, "campaign": self.campaign, "ms": self.ms,
            "findings": [f.payload(cm) for f in self.findings],
            "counts": self.counts(),
            "blocking": len(self.blocking),
            "skipped": list(self.skipped), "failed": list(self.failed),
            "baseline_at": self.baseline_at,
            "baseline_keys": self.baseline_keys,
            "rules": [{"code": r.code, "label": r.label,
                       "severity": r.severity, "source": r.source}
                      for r in RULES],
            "fixes": [dict(f, code=c) for c, f in FIXES.items()],
        }


def run(mod, cm: Optional[CampaignMap] = None, campaign: str = "",
        use_baseline: bool = True) -> Report:
    """Every rule, over one map, in one pass.

    ``cm`` is passed in rather than made here so that the validator can be run
    against the map **as it is on the screen**, unsaved strokes and all. That is
    the whole point of it existing beside a paint tool: "would what I am about
    to save load?" is a different question from "does what is on disk load?".

    Nothing raises. A rule that throws is recorded in :attr:`Report.failed` with
    its code, because losing twenty-four working rules to one broken one is the
    failure mode that makes a validator untrustworthy.
    """
    t0 = time.perf_counter()
    cm = cm or CampaignMap(mod)
    ck = Check(mod, cm, campaign)
    out = Report(mod=getattr(mod, "name", ""), campaign=ck.campaign)

    for r in RULES:
        try:
            got = list(r.fn(ck) or ())
        except Exception as exc:                       # noqa: BLE001
            out.failed.append({"code": r.code, "error": f"{type(exc).__name__}: {exc}"})
            continue
        out.findings.extend(got)

    out.skipped = ck.skipped
    order = {s: i for i, s in enumerate(SEVERITIES)}
    out.findings.sort(key=lambda f: (order.get(f.severity, 9), f.code,
                                     f.file, f.line, f.tile or (0, 0)))

    if use_baseline:
        base = read_baseline(mod)
        stamped = set(base.get("keys") or ())
        for f in out.findings:
            f.baseline = f.key in stamped
        out.baseline_at = base.get("taken", "")
        out.baseline_keys = len(stamped)
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out


# ---------------------------------------------------------------------------
# the baseline
#
# What was already wrong before this user touched anything. Stored in the cache
# folder rather than in the mod: it is derived data about somebody else's files,
# and config.cache_dir() is where derived data goes (a mod folder can be inside
# OneDrive, and this must never be a file that syncs).


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)) or "mod"


def baseline_path(mod) -> Path:
    from . import config
    return config.cache_dir("mapcheck") / f"{_slug(getattr(mod, 'name', ''))}.json"


def read_baseline(mod) -> dict:
    try:
        return json.loads(baseline_path(mod).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def take_baseline(mod, report: Optional[Report] = None) -> dict:
    """Stamp what is wrong now as "not this user's problem".

    Every finding goes in, not only the fatals, so that a warning already in the
    mod reads as an inherited one afterwards too. The stamp is keys and a date;
    it holds no message, because the wording of a rule may improve and the
    baseline must not go stale when it does.
    """
    rep = report or run(mod, use_baseline=False)
    out = {"mod": getattr(mod, "name", ""), "taken": time.strftime("%Y-%m-%d %H:%M:%S"),
           "keys": sorted({f.key for f in rep.findings})}
    p = baseline_path(mod)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def clear_baseline(mod) -> bool:
    try:
        baseline_path(mod).unlink()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# the auto-fixes
#
# Geomod's three debugger actions, and nothing invented beside them. Each one is
# derived from the findings of exactly one rule, so a fix can never act on
# something the report did not show the user first.

FIXES: Dict[str, dict] = {
    "heights_black": {
        "label": "Set ambiguous altitudes to (1,1,1)",
        "rule": "height.ambiguous",
        "file": "map_heights.tga",
        "what": "Every pure-black altitude pixel on a tile the ground layer "
                "calls land becomes (1,1,1). That is one step off black, land "
                "beyond argument, and no visible change to the map.",
    },
    "resource_duplicate": {
        "label": "Delete duplicate resource lines",
        "rule": "strat.resource_duplicate",
        "file": "",
        "what": "The second and later of two identical `resource` lines are "
                "removed. The first one, which is the one the engine uses, "
                "stays exactly where it is.",
    },
    "resource_position": {
        "label": "Delete resources that are off the map or in the sea",
        "rule": "strat.resource_position",
        "file": "",
        "what": "A resource nothing on land can reach is removed. There is no "
                "position to move it to that would not be a guess.",
    },
}


@dataclass
class FixPlan:
    """What one round of auto-fixes would write, worked out without writing."""

    mod: object = None
    codes: List[str] = field(default_factory=list)
    #: rel path -> the whole file as it would go to disk
    data: Dict[str, bytes] = field(default_factory=dict)
    text: Dict[str, str] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: the findings this plan would clear, for the answer and the log
    cleared: List[Finding] = field(default_factory=list)

    def summary(self) -> str:
        head = (f"fix {getattr(self.mod, 'name', '?')}'s campaign map "
                f"({len(self.codes)} fix(es), {len(self.cleared)} finding(s))")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"codes": list(self.codes), "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "cleared": len(self.cleared),
                "files": sorted(list(self.data) + list(self.text)),
                "ok": not self.errors and bool(self.data or self.text)}


def plan_fix(mod, codes: Sequence[str], cm: Optional[CampaignMap] = None,
             campaign: str = "", keys: Optional[Sequence[str]] = None
             ) -> FixPlan:
    """What the chosen fixes would write.

    The rules are re-run here rather than trusting a report the browser sent
    back: a fix acts on the map as it is at the moment of the fix, and a stale
    finding list is how a tool ends up deleting the wrong line. ``keys`` narrows
    it to particular findings; without it, a fix takes every finding its rule
    produces.
    """
    cm = cm or CampaignMap(mod)
    p = FixPlan(mod=mod, codes=[c for c in codes if c in FIXES])
    unknown = [str(c) for c in codes if c not in FIXES]
    if unknown:
        p.errors.append("no such fix: " + ", ".join(unknown)
                        + ". The fixes are " + ", ".join(sorted(FIXES)) + ".")
        return p
    if not p.codes:
        p.errors.append("no fix was chosen")
        return p
    ck = Check(mod, cm, campaign)
    want = set(keys) if keys else None

    found: Dict[str, List[Finding]] = {}
    for code in p.codes:
        r = RULE_BY_CODE[FIXES[code]["rule"]]
        try:
            got = [f for f in (r.fn(ck) or ()) if f.fix == code]
        except Exception as exc:                       # noqa: BLE001
            p.errors.append(f"{r.code} could not be re-checked: {exc}")
            continue
        if want is not None:
            got = [f for f in got if f.key in want]
        found[code] = got
        p.cleared.extend(got)
    if p.errors:
        return p
    if not p.cleared:
        p.errors.append("nothing left to fix - the findings are already gone")
        return p

    if "heights_black" in found and found["heights_black"]:
        _plan_heights(ck, p)
    drop = sorted({f.line - 1 for code in ("resource_duplicate",
                                           "resource_position")
                   for f in found.get(code, ()) if f.line > 0})
    if drop:
        _plan_strat(ck, p, drop)
    if not p.data and not p.text and not p.errors:
        p.errors.append("nothing left to fix - the findings are already gone")
    return p


def _plan_heights(ck: Check, p: FixPlan) -> None:
    """Rewrite every pure-black land pixel of ``map_heights.tga``.

    The whole tile's block, not the sampled pixel alone. ``map_heights.tga`` is
    a ``2W+1`` layer whose pixels are the *corners* the terrain mesh is
    interpolated across, so leaving three black corners around one corrected
    centre would leave the tile at sea level anyway. :func:`campaint.block` is
    the same partition the brush paints through, which is what keeps the two
    from disagreeing about which pixels a tile owns.
    """
    tiles = _ambiguous_tiles(ck)
    if not tiles:
        return
    cm = ck.cm
    try:
        img = cm.layer("heights").convert("RGB")
        info = cm.info("heights")
    except MapError as exc:
        p.errors.append(f"map_heights.tga could not be read: {exc}")
        return
    px = img.load()
    rule = LAYER_BY_CODE["heights"]["size"]
    moved = 0
    for tx, ty in tiles:
        x0, y0, x1, y1 = block(rule, tx, ty)
        for y in range(y0, min(y1 + 1, img.height)):
            for x in range(x0, min(x1 + 1, img.width)):
                if px[x, y] == (0, 0, 0):
                    px[x, y] = (1, 1, 1)
                    moved += 1
    if not moved:
        return
    try:
        p.data[ck.rel("map_heights.tga")] = encode(img, info)
    except Exception as exc:                           # noqa: BLE001
        p.errors.append(f"map_heights.tga could not be re-encoded: {exc}")
        return
    p.changes.append(f"map_heights.tga: {moved:,} pixel(s) over {len(tiles):,} "
                     f"tile(s) from (0,0,0) to (1,1,1)")


def _plan_strat(ck: Check, p: FixPlan, drop: Sequence[int]) -> None:
    """Delete whole lines from ``descr_strat.txt``, bottom up.

    Bottom up because every index above a deleted line would otherwise be one
    out, which is the bug every "delete these rows" routine is born with. The
    rest of the file is untouched: this is 16b's model, lines plus an index, and
    a deletion is a slice rather than a re-serialisation.
    """
    if ck.strat is None:
        p.errors.append("descr_strat.txt could not be read, so nothing in it "
                        "can be fixed")
        return
    lines = list(ck.strat.lines)
    gone = []
    for i in sorted(set(drop), reverse=True):
        if 0 <= i < len(lines):
            gone.append(lines[i].strip())
            del lines[i]
    if not gone:
        return
    sf = ck.strat
    p.text[ck.strat_rel] = (sf.newline.join(lines)
                            + (sf.newline if sf.trailing_newline else ""))
    p.changes.append(f"{campstrat.STRAT_NAME}: {len(gone)} line(s) deleted "
                     + ", ".join(f"`{g}`" for g in gone[:4])
                     + ("…" if len(gone) > 4 else ""))


def apply_fix(p: FixPlan) -> dict:
    """Write the fixes, with the backups and the log entry every job gets.

    Same route as :func:`campaint.apply_paint`, deliberately: one backup set,
    one log record, ``map.rwm`` deleted when a layer moved, and therefore one
    Undo in the Log that puts every fixed file back byte for byte. "Every
    auto-fix is undoable" is this function and nothing else.
    """
    import shutil

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data and not p.text:
        raise ValueError("nothing to fix")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [], "deleted": []}

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

    for rel, data in p.data.items():
        target = keep(rel)
        target.write_bytes(data)
        file_op("WRITE", target, f"{len(data)} bytes")
    for rel, text in p.text.items():
        target = keep(rel)
        write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")

    # Only a layer changing invalidates the compiled map; a descr_strat.txt edit
    # does not. It is deleted whenever one did, for the same reason a paint save
    # deletes it: the game reads the binary in preference to the text. The one
    # beside the layer that changed - a campaign that ships its own heights
    # ships its own map.rwm, and that is the one it would load.
    for rw in sorted({str(Path(rel).parent.as_posix() + "/" + Path(RWM_REL).name)
                      for rel in p.data}):
        rwm = Path(mod.data) / rw
        if rwm.exists():
            keep(rw)
            rwm.unlink()
            manifest["deleted"].append(rw)
            file_op("DELETE", rwm, "stale compiled map - the game would load it "
                                   "instead")

    what = ", ".join(FIXES[c]["label"] for c in p.codes)
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "mapfix",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": what, "resolved_type": what,
        "options": {"fixes": list(p.codes)}, "applied": True, "undone": False,
        "note": "", "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("MAPFIX %s - %s, %d finding(s), id=%s", mod.name, what,
             len(p.cleared), tid)
    return {"id": tid, "codes": list(p.codes), "cleared": len(p.cleared),
            "files": sorted(list(p.data) + list(p.text)), "record": rec}


RULE_BY_CODE = {r.code: r for r in RULES}
