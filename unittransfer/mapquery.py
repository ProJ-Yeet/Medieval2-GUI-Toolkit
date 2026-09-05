"""Asking the campaign map questions about itself. Phase 16g.

16a to 16f read the map, drew it, made a region editable, let a brush change
the pixels and said whether the result would load. This is the part that
answers "which provinces are these?" - TWMapReader's filter engine, its three
themes, Geomod's information maps, and a TGA of any of them on disk.

**One fact table, read by everything.** A filter, a theme, an information map
and an export are four views of the same handful of sentences about a province,
so they are gathered once into :class:`Facts` and nothing below it opens a
file. That is the ruling :class:`unittransfer.mapcheck.Check` makes and it is
here for the same reason: "has a port", "starts with a wall" and "is in the
Mordor mercenary pool" are three questions about one province, and three
readers of ``descr_strat.txt`` would be three chances to disagree.

**A rule with no evidence reports nothing.** 16f's ruling, carried straight
over. A filter whose vocabulary the mod does not ship is *off, with the file
that would turn it on named* - never an empty result, which reads as "none of
your provinces have this" and is a different and false sentence. The game's own
``data/`` is packed and ships neither ``descr_mercenaries.txt`` nor
``descr_win_conditions.txt`` on disk, so on vanilla several of the filters are
off and say which file would run them.

**The browser decides nothing.** Python works out which regions match and what
colour each one takes; the browser recolours the region layer it is already
holding through that table. There is no second copy of a rule on the far side
to drift, which is the division the paint tool, the region form and the
validator all already make. The table is keyed by the region's **map colour**
rather than by its name, because the label image is what the browser has.

**A theme and an information map are the same object.** Both are a grouping of
regions plus a palette, so both are a :class:`Colouring`; one function builds
the payload, one writes the TGA, one draws it. What separates them is only
where the grouping comes from - a theme is a fact about who owns a province,
an information map is a fact about what is in it.

Two measurements worth writing down. Building the whole fact table is one pass
over ``descr_strat.txt`` plus the region index that is already cached, and
every filter, theme and information map after that is a dictionary lookup per
region. And an exported TGA is written through
:func:`unittransfer.maptga.encode` in the shape of the mod's own
``map_regions.tga``, so what comes out is a file the tools that made the map
can open.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image

from . import campmap, campstrat, factions as factionfile, minorfiles
from .campmap import BASE_REL, ENCODING, CampaignMap, MapError, Rgb, key
from .maptga import encode
from .mapvocab import PORT_RGB, SETTLEMENT_RGB

#: Music types live beside the layers rather than beside the campaign, because
#: which music a province plays is a fact about the map and not about one
#: campaign on it.
MUSIC_REL = f"{BASE_REL}/descr_sounds_music_types.txt"
MERCS_NAME = "descr_mercenaries.txt"
WIN_NAME = "descr_win_conditions.txt"

#: What a province in no group is painted: dark, and not black, so "this region
#: is in no group" and "this pixel is not a region at all" stay apart on the
#: exported file as well as on the screen.
NO_GROUP: Rgb = (32, 34, 38)
#: Sea, and everything else on the region layer that is not a province.
BACKDROP: Rgb = (10, 12, 16)
#: The line drawn between two groups on a theme. Dark rather than black so it
#: still reads over the darkest faction colour a mod might declare.
BORDER: Rgb = (18, 18, 22)

#: How many provinces one query lists individually before the rest are counted.
#: Every listed one carries the tile the map jumps to; the fold carries one.
LIST_MAX = 400


# ---------------------------------------------------------------------------
# the three files nothing else in the toolkit reads yet
#
# All three are small, all three are line-oriented, and none of them is written
# here - 16g reads. So each is a plain function returning plain records rather
# than a LineFile with spans: there is nothing yet to splice.


def _text(path: Path) -> str:
    from .keyblock import read_text
    try:
        return read_text(path, ENCODING)
    except OSError:
        return ""


def _bare(line: str) -> str:
    """The line without its comment or its surrounding space."""
    return line.split(";", 1)[0].strip()


def parse_music_types(text: str) -> Dict[str, List[str]]:
    """``{music type: [region, ...]}`` out of ``descr_sounds_music_types.txt``.

    A block is ``music_type <name>`` followed by any number of ``regions`` and
    ``factions`` lines; the regions lines wrap, so they accumulate rather than
    replace. The factions lines are read past deliberately: this module colours
    provinces, and which factions share a music type is not a fact about one.
    """
    out: Dict[str, List[str]] = {}
    current = ""
    for raw in text.splitlines():
        s = _bare(raw)
        if not s:
            continue
        word, _, rest = s.partition(" ")
        low = word.lower()
        if low == "music_type":
            current = rest.strip()
            out.setdefault(current, [])
        elif low == "regions" and current:
            out[current].extend(rest.split())
    return out


@dataclass
class MercPool:
    """One ``pool`` block: where it applies and what it sells."""

    name: str = ""
    regions: List[str] = field(default_factory=list)
    units: List[str] = field(default_factory=list)


def parse_mercenaries(text: str) -> List[MercPool]:
    """``descr_mercenaries.txt`` as pools.

    A unit line is ``unit <name> exp N cost N ...`` and the name is everything
    in front of ``exp``. It is taken that way rather than by word count because
    a mercenary's name is one to four words and real files write a trailing
    comma after it: Third Age Reforged ships ``unit dhow,`` and ``unit Gondor
    Osgiliath Archers,`` in the same file.
    """
    out: List[MercPool] = []
    for raw in text.splitlines():
        s = _bare(raw)
        if not s:
            continue
        word, _, rest = s.partition(" ")
        low = word.lower()
        if low == "pool":
            out.append(MercPool(name=rest.strip()))
        elif not out:
            continue
        elif low == "regions":
            out[-1].regions.extend(rest.split())
        elif low == "unit":
            name = re.split(r"\bexp\b", rest, 1)[0].strip().rstrip(",").strip()
            if name:
                out[-1].units.append(name)
    return out


@dataclass
class WinCondition:
    """One faction's victory terms, long campaign and short.

    ``take`` is a count of provinces and ``hold`` is a list of them, which is
    why only ``hold`` can colour a map. The rest is carried because the panel
    says what the whole condition is when it names a province in it.
    """

    faction: str = ""
    hold: List[str] = field(default_factory=list)
    take: int = 0
    outlive: List[str] = field(default_factory=list)
    short_hold: List[str] = field(default_factory=list)
    short_take: int = 0
    short_outlive: List[str] = field(default_factory=list)

    def mentions(self, region: str) -> List[str]:
        low = region.lower()
        out = []
        if any(r.lower() == low for r in self.hold):
            out.append("long campaign")
        if any(r.lower() == low for r in self.short_hold):
            out.append("short campaign")
        return out


_WIN_WORDS = ("hold_regions", "take_regions", "outlive", "short_campaign")


def parse_win_conditions(text: str) -> List[WinCondition]:
    """``descr_win_conditions.txt`` as one record per faction.

    The file has no braces and no faction keyword: a line that is a bare word
    and not one of the four condition words opens the next faction. A
    ``short_campaign`` switches everything after it, on that line and on the
    lines below it, into the short campaign until the next faction opens.
    """
    out: List[WinCondition] = []
    short = False
    for raw in text.splitlines():
        s = _bare(raw)
        if not s:
            continue
        word, _, rest = s.partition(" ")
        low = word.lower()
        if low == "short_campaign":
            short = True
            s = rest.strip()
            if not s:
                continue
            word, _, rest = s.partition(" ")
            low = word.lower()
        if low not in _WIN_WORDS:
            if len(s.split()) == 1:
                out.append(WinCondition(faction=s))
                short = False
            continue
        if not out:
            continue
        w = out[-1]
        if low == "hold_regions":
            (w.short_hold if short else w.hold).extend(rest.split())
        elif low == "take_regions":
            n = int(rest.strip()) if re.fullmatch(r"\d+", rest.strip()) else 0
            if short:
                w.short_take = n
            else:
                w.take = n
        elif low == "outlive":
            (w.short_outlive if short else w.outlive).extend(rest.split())
    return out


# ---------------------------------------------------------------------------
# one province, everything anything here needs to know about it


@dataclass
class RegionFacts:
    """One province, joined from the four places that describe it.

    Nothing here is computed twice and nothing here reads a file. The four
    sources are ``descr_regions.txt`` (the record), ``map_regions.tga`` (the
    pixels), ``descr_strat.txt`` (who starts holding it and what is standing in
    it) and the three small files above.
    """

    name: str = ""
    shown: str = ""
    rgb: Rgb = (0, 0, 0)
    #: the order the engine numbers regions in, or -1 for a record with no
    #: pixels on the map at all
    region_id: int = -1
    pixels: int = 0
    #: a tile inside the province, for the map to jump to
    anchor: Tuple[int, int] = (0, 0)

    # -- descr_regions.txt
    settlement: str = ""
    shown_settlement: str = ""
    creator: str = ""
    rebels: str = ""
    hidden_resources: List[str] = field(default_factory=list)
    triumph: int = 0
    farming: int = 0
    religions: Dict[str, int] = field(default_factory=dict)
    wasteland: bool = False

    # -- the pixels
    has_settlement_pixel: bool = False
    has_port_pixel: bool = False

    # -- descr_strat.txt
    owner: str = ""
    culture: str = ""
    settlement_type: str = ""
    level: str = ""
    population: int = 0
    plan_set: str = ""
    settlement_creator: str = ""
    year_founded: int = 0
    #: every ``type <line> <level>`` in the settlement block, level names
    buildings: List[str] = field(default_factory=list)
    #: the ``export_descr_buildings.txt`` line each of those levels belongs to
    building_lines: List[str] = field(default_factory=list)
    wall: str = ""
    port_building: str = ""
    trade_resources: List[str] = field(default_factory=list)
    #: line in descr_strat.txt the settlement block opens at, 1-based, or 0
    strat_line: int = 0

    # -- the three small files
    music_type: str = ""
    merc_pools: List[str] = field(default_factory=list)
    win_for: List[str] = field(default_factory=list)

    @property
    def rgb_key(self) -> int:
        return key(self.rgb)

    @property
    def religion_majority(self) -> str:
        """The religion with the largest share, or ``""`` on a tie or none.

        A tie is deliberately not broken. Two religions at 50 each is a real
        state a real region is in, and picking the alphabetically first would
        put a province on a majority map under a colour that is an artefact of
        this function rather than a fact about the mod.
        """
        if not self.religions:
            return ""
        best = max(self.religions.values())
        top = [r for r, v in self.religions.items() if v == best]
        return top[0] if len(top) == 1 and best > 0 else ""

    def payload(self) -> dict:
        return {
            "name": self.name, "shown": self.shown, "rgb": list(self.rgb),
            "key": self.rgb_key, "id": self.region_id, "pixels": self.pixels,
            "tile": list(self.anchor),
            "settlement": self.settlement, "shown_settlement": self.shown_settlement,
            "owner": self.owner, "culture": self.culture,
            "level": self.level, "settlement_type": self.settlement_type,
            "population": self.population, "religion": self.religion_majority,
            "port": self.has_port_pixel, "line": self.strat_line,
        }


# ---------------------------------------------------------------------------
# the fact table


class Facts:
    """Everything every filter, theme and information map reads, gathered once.

    Built from a :class:`~unittransfer.campmap.CampaignMap` the caller may
    already be holding with unsaved paint in it, exactly like the validator, so
    a query answers about the map on the screen rather than the one on disk.

    Anything that will not read is recorded in :attr:`skipped` and the filters
    that needed it are turned off by name. A filter that cannot run is not a
    filter that matched nothing.
    """

    def __init__(self, mod, cm: CampaignMap, campaign: str = ""):
        self.mod = mod
        self.cm = cm
        self.campaign = campaign or campstrat.DEFAULT_CAMPAIGN
        self.skipped: List[dict] = []
        self.regions: List[RegionFacts] = []
        self.by_name: Dict[str, RegionFacts] = {}
        self.ms = 0
        t0 = time.perf_counter()

        self.strat_rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{self.campaign}/"
                          f"{campstrat.STRAT_NAME}")
        self.strat: Optional[campstrat.StratFile] = None
        try:
            self.strat = campstrat.read_strat(mod, self.campaign)
        except (OSError, ValueError) as exc:
            self.skip(campstrat.STRAT_NAME,
                      f"{self.strat_rel} could not be read ({exc}), so nothing "
                      f"the campaign itself says about a province is known")

        self.names = campmap.shown_names(mod)
        self.faction_cultures: Dict[str, str] = {}
        self.faction_labels: Dict[str, str] = {}
        self.faction_colours: Dict[str, Rgb] = {}
        self._read_factions()
        self._read_buildings()
        self._read_small_files()
        self._build()
        self.ms = int((time.perf_counter() - t0) * 1000)

    # -- gathering -----------------------------------------------------------

    def skip(self, what: str, why: str) -> None:
        self.skipped.append({"what": what, "why": why})

    def _read_factions(self) -> None:
        """``descr_sm_factions.txt``: which culture a faction is, and its colour.

        The file that made 16f's ruling necessary is this one. The stock game
        does not ship it on disk - it is inside the packed data - and
        :attr:`Mod.faction_cultures` answers that with an empty dict rather
        than an error, so a reader that does not check would offer a culture
        filter with nothing in it and a culture map that is uniformly blank.
        Absent evidence is a skip, and the skip names the file.
        """
        try:
            self.faction_cultures = dict(self.mod.faction_cultures)
        except Exception as exc:                       # noqa: BLE001
            self.faction_cultures = {}
            self.skip("descr_sm_factions.txt",
                      f"The faction list could not be read ({exc}), so no "
                      f"province has a culture or a faction colour.")
            return
        if not self.faction_cultures:
            self.skip("descr_sm_factions.txt",
                      "The stock game keeps descr_sm_factions.txt inside its "
                      "packed data rather than on disk, so no province has a "
                      "culture and no faction has a colour of its own.")
            return
        for name in self.faction_cultures:
            try:
                self.faction_labels[name] = self.mod.faction_label(name)
            except Exception:                          # noqa: BLE001
                self.faction_labels[name] = name
        try:
            rf = factionfile.parse_file(factionfile.path_for(self.mod))
            for rec in rf.records:
                rgb = factionfile.parse_colour(rec.get("primary_colour") or "")
                if rgb:
                    self.faction_colours[rec.name] = rgb
        except Exception:                              # noqa: BLE001
            pass

    def _read_buildings(self) -> None:
        """``{level name: the export_descr_buildings.txt line it belongs to}``.

        This is what turns "has ``huge_stone_wall``" into "has a level of
        ``core_building``", which is the difference between TWMapReader's
        building filter and its building-tree filter.

        The fallback is better than it looks and it is why the building-tree
        filter still runs on the stock game. ``descr_strat.txt`` writes
        ``type <line> <level>`` - the line name is already in the campaign file
        - so a mod with no readable EDB gets its trees from the map's own words
        and only loses the trees no settlement has built.
        """
        self.building_line_of: Dict[str, str] = {}
        self.building_levels: List[str] = []
        self.building_trees: List[str] = []
        try:
            edb = self.mod.edb
        except Exception as exc:                       # noqa: BLE001
            self.skip("export_descr_buildings.txt",
                      f"The building list could not be read ({exc}), so a "
                      f"building tree is only as good as the word "
                      f"descr_strat.txt writes in front of the level.")
            return
        if not edb.buildings:
            self.skip("export_descr_buildings.txt",
                      "The stock game keeps export_descr_buildings.txt inside "
                      "its packed data rather than on disk, so a building tree "
                      "is the word descr_strat.txt writes in front of the level "
                      "rather than the line the EDB declares.")
        for line in edb.buildings:
            self.building_trees.append(line.name)
            for lvl in line.levels:
                self.building_line_of[lvl] = line.name
                self.building_levels.append(lvl)

    def _read_small_files(self) -> None:
        camp = self.mod.data / campstrat.CAMPAIGN_DIR_REL / self.campaign

        self.music: Dict[str, List[str]] = {}
        txt = _text(self.mod.data / MUSIC_REL)
        if txt:
            self.music = parse_music_types(txt)
        else:
            self.skip("descr_sounds_music_types.txt",
                      f"{MUSIC_REL} is not on disk, so no province has a music "
                      f"type to filter on")

        self.pools: List[MercPool] = []
        txt = _text(camp / MERCS_NAME)
        if txt:
            self.pools = parse_mercenaries(txt)
        else:
            self.skip(MERCS_NAME,
                      f"{campstrat.CAMPAIGN_DIR_REL}/{self.campaign}/"
                      f"{MERCS_NAME} is not on disk, so no province has a "
                      f"mercenary pool to filter on")

        self.wins: List[WinCondition] = []
        txt = _text(camp / WIN_NAME)
        if txt:
            self.wins = parse_win_conditions(txt)
        else:
            self.skip(WIN_NAME,
                      f"{campstrat.CAMPAIGN_DIR_REL}/{self.campaign}/"
                      f"{WIN_NAME} is not on disk, so no province is in "
                      f"anybody's win conditions")

        self.religion_names: List[str] = []
        try:
            self.religion_names = list(minorfiles.religion_names(self.mod))
        except Exception:                              # noqa: BLE001
            pass

    # -- the join ------------------------------------------------------------

    def _build(self) -> None:
        """One :class:`RegionFacts` per record in ``descr_regions.txt``.

        The record is the spine rather than the pixels, and that is the right
        way round: a province with a record and no pixels is a fault the
        validator already reports, and it still has a name, a creator and a
        religion breakdown worth querying. A colour on the map with no record
        has nothing to say and nothing to be filtered by.
        """
        try:
            index = self.cm.index
        except MapError as exc:
            index = None
            self.skip("map_regions.tga",
                      f"{exc}, so nothing here knows where a province is")

        for rec in self.cm.regions.records:
            rf = RegionFacts(
                name=rec.name, shown=self.names.get(rec.name, ""),
                rgb=rec.rgb, settlement=rec.settlement,
                shown_settlement=self.names.get(rec.settlement, ""),
                creator=rec.faction, rebels=rec.rebels,
                hidden_resources=list(rec.resources), triumph=rec.triumph,
                farming=rec.farming, religions=dict(rec.religions),
                wasteland=rec.wasteland)
            if index is not None:
                r = index.by_key.get(rec.rgb_key)
                if r is not None:
                    rf.region_id = r.region_id
                    rf.pixels = r.pixels
                    rf.anchor = r.anchor
                    rf.has_settlement_pixel = r.settlement is not None
                    rf.has_port_pixel = r.port is not None
            self.regions.append(rf)
            self.by_name[rec.name.lower()] = rf

        self._join_strat()
        self._join_small_files()

    def _join_strat(self) -> None:
        if self.strat is None:
            return
        for node in self.strat.of_kind("settlement"):
            region = str(node.get("region") or "")
            rf = self.by_name.get(region.lower())
            if rf is None:
                continue                               # 16f reports this one
            owner = self._faction_of(node)
            rf.owner = owner
            rf.culture = self.faction_cultures.get(owner, "")
            rf.settlement_type = str(node.get("settlement_type") or "city")
            rf.level = str(node.get("level") or "")
            pop = node.get("population")
            rf.population = int(pop) if isinstance(pop, int) else 0
            rf.plan_set = str(node.get("plan_set") or "")
            rf.settlement_creator = str(node.get("faction_creator") or "")
            yf = node.get("year_founded")
            rf.year_founded = int(yf) if isinstance(yf, int) else 0
            rf.strat_line = node.start + 1
            for b in self.strat.children_of(node, "building"):
                level = str(b.get("level") or "")
                line = b.name or ""
                if level:
                    rf.buildings.append(level)
                    rf.building_lines.append(
                        self.building_line_of.get(level, line))
                    if line == "core_building" or line == "core_castle_building":
                        rf.wall = level
                    if "port" in line.lower():
                        rf.port_building = level

        self._join_resources()

    def _faction_of(self, node: campstrat.Node) -> str:
        """Which faction block a settlement is inside.

        Walked up the parent chain rather than matched by position, because a
        settlement is inside its faction block and nothing else in the file
        nests a settlement.
        """
        at = node.parent
        while at >= 0:
            p = self.strat.nodes[at]
            if p.kind == "faction":
                return str(p.get("name") or p.name or "")
            at = p.parent
        return ""

    def _join_resources(self) -> None:
        """Every ``resource <name>, x, y`` put in the province it stands in.

        The coordinates are the ones ``descr_strat.txt`` writes, which are game
        coordinates with y counted from the bottom, so they go through the map's
        own transform rather than through a second copy of it here. A resource
        off the grid or in a colour no record claims is skipped: 16f is what
        reports those, and reporting them again from a query panel would be a
        second voice saying the same thing.
        """
        try:
            index = self.cm.index
        except MapError:
            return
        # A resource is allowed to stand on a settlement or a port pixel, and
        # several mods put one right beside the city it feeds. The index does
        # not answer for a marker tile - a marker has no region colour of its
        # own - so the region that owns the marker answers instead.
        on_marker: Dict[Tuple[int, int], str] = {}
        for r in index.regions:
            if r.record and r.settlement:
                on_marker[r.settlement] = r.record.name
            if r.record and r.port:
                on_marker[r.port] = r.record.name

        for node in self.strat.of_kind("resource"):
            name = str(node.get("name") or "")
            gx, gy = node.get("x"), node.get("y")
            if not name or not isinstance(gx, int) or not isinstance(gy, int):
                continue
            x, y = self.cm.image_xy(gx, gy)
            if not self.cm.terrain.in_bounds(x, y):
                continue
            r = index.at(x, y)
            where = (r.record.name if r is not None and r.record
                     else on_marker.get((x, y), ""))
            rf = self.by_name.get(where.lower()) if where else None
            if rf is not None:
                rf.trade_resources.append(name)

    def _join_small_files(self) -> None:
        for music, regions in self.music.items():
            for name in regions:
                rf = self.by_name.get(name.lower())
                if rf is not None:
                    rf.music_type = music
        for pool in self.pools:
            for name in pool.regions:
                rf = self.by_name.get(name.lower())
                if rf is not None:
                    rf.merc_pools.append(pool.name)
        for w in self.wins:
            for name in set(w.hold) | set(w.short_hold):
                rf = self.by_name.get(name.lower())
                if rf is not None and w.faction not in rf.win_for:
                    rf.win_for.append(w.faction)

    # -- what a filter asks it -----------------------------------------------

    def faction_label(self, name: str) -> str:
        """``"Gondor (sicily)"``, or the slot when the mod names it nothing.

        :meth:`Mod.faction_label` already puts the slot in the brackets, so
        this does not add a second pair. It exists so a filter, a legend and an
        exported file name all say the faction the same way.
        """
        return self.faction_labels.get(name) or name

    def label_of(self, rf: RegionFacts) -> str:
        return f"{rf.shown} ({rf.name})" if rf.shown else rf.name

    def values_of(self, get: Callable[[RegionFacts], Iterable[str]]
                  ) -> List[Tuple[str, int]]:
        """``[(value, how many provinces have it)]``, commonest first.

        A filter's vocabulary is what is *on this map*, not what the mod could
        declare. Offering ``mercenary_pool = Gondor7`` on a map where no
        province is in it is offering a query whose answer is known to be empty
        before it is asked.
        """
        counts: Dict[str, int] = {}
        for rf in self.regions:
            # a province with two vineyards in it is one province with
            # vineyards, and the count beside a filter's value is what its
            # answer will be
            for v in {v for v in get(rf) if v}:
                counts[v] = counts.get(v, 0) + 1
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))


# ---------------------------------------------------------------------------
# the filters
#
# One object per question TWMapReader can ask a map, plus the two the exit
# criteria name. Every one of them carries where it came from, the same way a
# validator rule does, because a filter with no provenance is a query somebody
# invented and nobody can argue with later.


@dataclass
class Filter:
    """One question, and everything the panel needs to offer it."""

    code: str
    label: str
    group: str
    #: ``choice`` picks one value, ``bool`` is on or off, ``range`` is two
    #: numbers, ``text`` is a substring of the name, ``share`` is a value and a
    #: percentage together.
    kind: str
    source: str
    #: the file that would have to be on disk for this filter to have anything
    #: to offer. Named in the "off" sentence rather than guessed at.
    needs: str = ""
    note: str = ""
    unit: str = ""
    values: Optional[Callable[["Facts"], List[Tuple[str, int]]]] = None
    labeller: Optional[Callable[["Facts", str], str]] = None
    test: Callable[["Facts", RegionFacts, dict], bool] = None  # type: ignore[assignment]
    why: Optional[Callable[["Facts", RegionFacts, dict], str]] = None

    def options(self, facts: "Facts") -> List[dict]:
        if not self.values:
            return []
        return [{"value": v, "label": (self.labeller(facts, v)
                                       if self.labeller else v), "count": n}
                for v, n in self.values(facts)]

    def off(self, facts: "Facts", options: List[dict]) -> str:
        """Why this filter cannot be asked, or ``""``.

        16f's ruling, and the whole reason this method exists: a filter with
        nothing to offer is turned off *with the file that would turn it on*.
        An empty result set would read as "no province has one", which is a
        different sentence and, on a mod whose data is packed, a false one.
        """
        if self.kind in ("bool", "range", "text"):
            return ""
        if options:
            return ""
        if self.needs:
            for s in facts.skipped:
                if s["what"] == self.needs:
                    return s["why"]
            return (f"{self.needs} is on disk and names no province on this "
                    f"map, so there is nothing to pick")
        return "no province on this map has one"

    def payload(self, facts: "Facts") -> dict:
        options = self.options(facts)
        return {"code": self.code, "label": self.label, "group": self.group,
                "kind": self.kind, "source": self.source, "note": self.note,
                "unit": self.unit, "values": options,
                "off": self.off(facts, options)}


FILTERS: List[Filter] = []
FILTER_BY_CODE: Dict[str, Filter] = {}


def _filter(f: Filter) -> Filter:
    FILTERS.append(f)
    FILTER_BY_CODE[f.code] = f
    return f


def _value(rule: dict) -> str:
    return str(rule.get("value") or "")


def _same(a: str, b: str) -> bool:
    return a.lower() == b.lower() if a and b else False


def _has(values: Iterable[str], want: str) -> bool:
    low = want.lower()
    return any(v.lower() == low for v in values)


def _num(rule: dict, slot: str, default: Optional[int] = None) -> Optional[int]:
    raw = rule.get(slot)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


# -- who holds it ------------------------------------------------------------

_filter(Filter(
    code="owner", label="Starting owner", group="Who holds it", kind="choice",
    source="TWMapReader's starting-regions filter; the faction block a "
           "settlement is written inside in descr_strat.txt",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: [r.owner]),
    labeller=lambda f, v: f.faction_label(v),
    test=lambda f, r, q: _same(r.owner, _value(q)),
    why=lambda f, r, q: f"starts held by {f.faction_label(r.owner)}"))

_filter(Filter(
    code="culture", label="Culture", group="Who holds it", kind="choice",
    source="TWMapReader's culture filter; the culture of the faction that "
           "starts holding the province",
    needs="descr_sm_factions.txt",
    values=lambda f: f.values_of(lambda r: [r.culture]),
    test=lambda f, r, q: _same(r.culture, _value(q)),
    why=lambda f, r, q: f"{f.faction_label(r.owner)} is {r.culture}"))

_filter(Filter(
    code="creator", label="Region creator", group="Who holds it", kind="choice",
    source="TWMapReader's creator filter; the faction line in the "
           "descr_regions.txt record",
    needs="descr_regions.txt",
    values=lambda f: f.values_of(lambda r: [r.creator]),
    labeller=lambda f, v: f.faction_label(v),
    note="The faction named in the region's own record, which is not always "
         "the one holding it at the start.",
    test=lambda f, r, q: _same(r.creator, _value(q)),
    why=lambda f, r, q: f"descr_regions.txt names {r.creator} as its creator"))

_filter(Filter(
    code="settlement_creator", label="Settlement creator", group="Who holds it",
    kind="choice",
    source="descr_strat.txt's faction_creator, which decides the settlement's "
           "architecture rather than its owner",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: [r.settlement_creator]),
    labeller=lambda f, v: f.faction_label(v),
    test=lambda f, r, q: _same(r.settlement_creator, _value(q)),
    why=lambda f, r, q: f"faction_creator {r.settlement_creator}"))

_filter(Filter(
    code="rebels", label="Rebel tribe", group="Who holds it", kind="choice",
    source="TWMapReader's rebel-tribe filter; the fourth line of the "
           "descr_regions.txt record, against descr_rebel_factions.txt",
    needs="descr_regions.txt",
    values=lambda f: f.values_of(lambda r: [r.rebels]),
    test=lambda f, r, q: _same(r.rebels, _value(q)),
    why=lambda f, r, q: f"rebels are {r.rebels}"))

_filter(Filter(
    code="win_condition", label="In win conditions of", group="Who holds it",
    kind="choice",
    source="TWMapReader's win-conditions filter; hold_regions in "
           "descr_win_conditions.txt, long campaign and short",
    needs=WIN_NAME,
    values=lambda f: f.values_of(lambda r: r.win_for),
    labeller=lambda f, v: f.faction_label(v),
    note="Only hold_regions can colour a map. take_regions is a count of "
         "provinces rather than a list of them.",
    test=lambda f, r, q: _has(r.win_for, _value(q)),
    why=lambda f, r, q: _win_why(f, r, _value(q))))


def _win_why(facts: "Facts", rf: RegionFacts, faction: str) -> str:
    for w in facts.wins:
        if _same(w.faction, faction):
            where = w.mentions(rf.name)
            return (f"{facts.faction_label(faction)} must hold it to win "
                    f"({', '.join(where)})" if where else
                    f"named in {facts.faction_label(faction)}'s win conditions")
    return "named in a win condition"


# -- what is in it -----------------------------------------------------------

_filter(Filter(
    code="hidden_resource", label="Hidden resource", group="What is in it",
    kind="choice",
    source="TWMapReader's hidden-resource filter; the resource line of the "
           "descr_regions.txt record, against export_descr_buildings.txt",
    needs="descr_regions.txt",
    values=lambda f: f.values_of(lambda r: r.hidden_resources),
    test=lambda f, r, q: _has(r.hidden_resources, _value(q)),
    why=lambda f, r, q: f"hidden resource {_value(q)}"))

_filter(Filter(
    code="trade_resource", label="Trade resource", group="What is in it",
    kind="choice",
    source="TWMapReader's trade-resource filter; every resource line in "
           "descr_strat.txt, placed in the province its tile falls in",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: r.trade_resources),
    note="A resource belongs to the province the tile it stands on belongs "
         "to, by the same index the map itself is drawn from.",
    test=lambda f, r, q: _has(r.trade_resources, _value(q)),
    why=lambda f, r, q: _count_why(r.trade_resources, _value(q))))


def _count_why(values: List[str], want: str) -> str:
    n = sum(1 for v in values if _same(v, want))
    return f"{n} x {want}" if n > 1 else want


_filter(Filter(
    code="religion_majority", label="Religion majority", group="What is in it",
    kind="choice",
    source="The religions block of the descr_regions.txt record; the largest "
           "share, with a tie left uncoloured",
    needs="descr_regions.txt",
    values=lambda f: f.values_of(lambda r: [r.religion_majority]),
    note="A province split evenly between two religions has no majority and "
         "matches none of them, which is the state it is really in.",
    test=lambda f, r, q: _same(r.religion_majority, _value(q)),
    why=lambda f, r, q: (f"{r.religion_majority} "
                         f"{r.religions.get(r.religion_majority, 0)}%")))

_filter(Filter(
    code="religion_share", label="Religion at least", group="What is in it",
    kind="share", unit="%",
    source="The religions block of the descr_regions.txt record, read as a "
           "threshold rather than as a winner",
    needs="descr_regions.txt",
    values=lambda f: f.values_of(lambda r: list(r.religions)),
    test=lambda f, r, q: (r.religions.get(_value(q), 0)
                          >= (_num(q, "min", 50) or 0)),
    why=lambda f, r, q: f"{_value(q)} {r.religions.get(_value(q), 0)}%"))

_filter(Filter(
    code="farming", label="Farming level", group="What is in it", kind="range",
    source="Geomod's agriculture map; the farming line of the "
           "descr_regions.txt record",
    test=lambda f, r, q: _in_range(r.farming, q),
    why=lambda f, r, q: f"farming {r.farming}"))

_filter(Filter(
    code="triumph", label="Triumph value", group="What is in it", kind="range",
    source="The triumph line of the descr_regions.txt record",
    test=lambda f, r, q: _in_range(r.triumph, q),
    why=lambda f, r, q: f"triumph {r.triumph}"))

_filter(Filter(
    code="music_type", label="Music type", group="What is in it", kind="choice",
    source="TWMapReader's music-type filter; the regions lines of "
           "descr_sounds_music_types.txt",
    needs="descr_sounds_music_types.txt",
    values=lambda f: f.values_of(lambda r: [r.music_type]),
    test=lambda f, r, q: _same(r.music_type, _value(q)),
    why=lambda f, r, q: f"music type {r.music_type}"))

_filter(Filter(
    code="mercenary_pool", label="Mercenary pool", group="What is in it",
    kind="choice",
    source="TWMapReader's mercenary-pool filter; the regions line of each "
           "pool block in descr_mercenaries.txt",
    needs=MERCS_NAME,
    values=lambda f: f.values_of(lambda r: r.merc_pools),
    note="A province can be in more than one pool, and several mods rely on "
         "that. All of them are matched.",
    test=lambda f, r, q: _has(r.merc_pools, _value(q)),
    why=lambda f, r, q: f"in the {_value(q)} pool"))


def _in_range(value: int, rule: dict) -> bool:
    lo, hi = _num(rule, "min"), _num(rule, "max")
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


# -- the settlement ----------------------------------------------------------

_filter(Filter(
    code="has_port", label="Has a port", group="The settlement", kind="bool",
    source="TWMapReader's has-port filter; the white port pixel in "
           "map_regions.tga, by the same cardinal-ownership rule the index uses",
    note="The pixel, not the building. A province with a port building and no "
         "port pixel is a fatal the validator reports.",
    test=lambda f, r, q: r.has_port_pixel,
    why=lambda f, r, q: "has a port pixel"))

_filter(Filter(
    code="wall", label="Starting wall", group="The settlement", kind="choice",
    source="TWMapReader's starting-wall filter; the core_building level in "
           "the settlement block",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: [r.wall]),
    test=lambda f, r, q: _same(r.wall, _value(q)),
    why=lambda f, r, q: f"starts with {r.wall}"))

_filter(Filter(
    code="settlement_kind", label="City or castle", group="The settlement",
    kind="choice",
    source="The settlement header in descr_strat.txt: `settlement` or "
           "`settlement castle`",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: [r.settlement_type]),
    test=lambda f, r, q: _same(r.settlement_type, _value(q)),
    why=lambda f, r, q: r.settlement_type))

_filter(Filter(
    code="level", label="Settlement level", group="The settlement",
    kind="choice",
    source="The level line of the settlement block in descr_strat.txt",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: [r.level]),
    test=lambda f, r, q: _same(r.level, _value(q)),
    why=lambda f, r, q: r.level))

_filter(Filter(
    code="population", label="Population", group="The settlement", kind="range",
    source="The population line of the settlement block in descr_strat.txt",
    test=lambda f, r, q: _in_range(r.population, q),
    why=lambda f, r, q: f"{r.population:,} people"))

_filter(Filter(
    code="building", label="Building", group="The settlement", kind="choice",
    source="TWMapReader's building filter; every building block in the "
           "settlement, by the level it is at",
    needs=campstrat.STRAT_NAME,
    values=lambda f: f.values_of(lambda r: r.buildings),
    test=lambda f, r, q: _has(r.buildings, _value(q)),
    why=lambda f, r, q: f"has {_value(q)}"))

_filter(Filter(
    code="building_tree", label="Building tree", group="The settlement",
    kind="choice",
    source="TWMapReader's building-tree filter; the export_descr_buildings.txt "
           "line a settlement's building belongs to, at any level",
    needs=campstrat.STRAT_NAME,
    note="Any level of the chain counts. This is what separates `has a wall of "
         "some kind` from `has a huge stone wall`.",
    values=lambda f: f.values_of(lambda r: r.building_lines),
    test=lambda f, r, q: _has(r.building_lines, _value(q)),
    why=lambda f, r, q: _tree_why(r, _value(q))))


def _tree_why(rf: RegionFacts, tree: str) -> str:
    low = tree.lower()
    at = [lvl for lvl, line in zip(rf.buildings, rf.building_lines)
          if line.lower() == low]
    return f"{tree} at {', '.join(at)}" if at else f"has {tree}"


# -- the province itself -----------------------------------------------------

_filter(Filter(
    code="name", label="Name contains", group="The province", kind="text",
    source="The region and settlement name file, and the code names both sides "
           "of it",
    note="Matches the code name and the name the player reads, so a province "
         "can be found by either.",
    test=lambda f, r, q: _name_hit(r, _value(q)),
    why=lambda f, r, q: f.label_of(r)))


def _name_hit(rf: RegionFacts, want: str) -> bool:
    low = want.strip().lower()
    if not low:
        return False
    return any(low in (v or "").lower() for v in
               (rf.name, rf.shown, rf.settlement, rf.shown_settlement))


_filter(Filter(
    code="pixels", label="Size in tiles", group="The province", kind="range",
    unit="tiles",
    source="The region index; how many tiles of map_regions.tga carry this "
           "province's colour",
    test=lambda f, r, q: _in_range(r.pixels, q),
    why=lambda f, r, q: f"{r.pixels:,} tiles"))

_filter(Filter(
    code="unsettled", label="No settlement pixel", group="The province",
    kind="bool",
    source="The region index; a province with no green settlement pixel in it",
    note="A playable province needs one. This is the query behind the "
         "validator's own settlement rules.",
    test=lambda f, r, q: not r.has_settlement_pixel,
    why=lambda f, r, q: "no settlement pixel in it"))


# ---------------------------------------------------------------------------
# running a query


#: What a matched province is painted. One colour rather than a palette,
#: because a query has one answer: this province is in the set or it is not.
HIGHLIGHT: Rgb = (255, 208, 74)


@dataclass
class QueryResult:
    """One run of one set of rules over one map."""

    rules: List[dict] = field(default_factory=list)
    match: str = "all"
    matched: List[RegionFacts] = field(default_factory=list)
    why: Dict[str, List[str]] = field(default_factory=dict)
    #: rules that could not be asked, and why. Never a silent no-match.
    off: List[dict] = field(default_factory=list)
    ms: int = 0

    @property
    def tiles(self) -> int:
        return sum(r.pixels for r in self.matched)

    def payload(self, facts: "Facts") -> dict:
        listed = self.matched[:LIST_MAX]
        matched = {r.name for r in self.matched}
        return {
            "count": len(self.matched), "tiles": self.tiles,
            "of": len(facts.regions), "match": self.match,
            "rules": list(self.rules), "off": list(self.off), "ms": self.ms,
            "listed": len(listed), "folded": len(self.matched) - len(listed),
            "regions": [dict(r.payload(), why=self.why.get(r.name, []))
                        for r in listed],
            # Every mapped province is in the table, not only the matched ones.
            # A highlight that paints the answer and leaves the rest of the map
            # as it was is a thousand gold tiles on a map of four hundred
            # thousand, which nobody can see; dimming what did not match is
            # what makes the answer readable. It is also what
            # :func:`render_query` writes, so the screen and the exported file
            # are the same picture rather than nearly the same one.
            "colours": {str(r.rgb_key): list(HIGHLIGHT if hit else NO_GROUP)
                        for r, hit in ((r, r.name in matched) for r in facts.regions)
                        if r.region_id >= 0},
        }


def run_query(facts: "Facts", rules: Sequence[dict], match: str = "all"
              ) -> QueryResult:
    """Every rule over every province, in one pass.

    ``match`` is ``all`` or ``any``. A rule the mod has no evidence for is
    dropped into :attr:`QueryResult.off` and takes no part in either: under
    ``all`` it would match nothing and empty the result, and under ``any`` it
    would quietly widen it. Neither is an honest answer to a question that
    could not be asked, so it is not asked and the panel says so.
    """
    t0 = time.perf_counter()
    out = QueryResult(rules=[dict(r) for r in rules],
                      match="any" if str(match).lower() == "any" else "all")

    live: List[Tuple[Filter, dict]] = []
    for raw in rules:
        code = str(raw.get("code") or "")
        f = FILTER_BY_CODE.get(code)
        if f is None:
            out.off.append({"code": code, "why": f"no filter called {code!r}"})
            continue
        why = f.off(facts, f.options(facts))
        if why:
            out.off.append({"code": code, "label": f.label, "why": why})
            continue
        if f.kind == "choice" and not _value(raw):
            out.off.append({"code": code, "label": f.label,
                            "why": "nothing is picked in it yet"})
            continue
        if f.kind == "text" and not str(raw.get("value") or "").strip():
            out.off.append({"code": code, "label": f.label,
                            "why": "nothing is typed in it yet"})
            continue
        live.append((f, dict(raw)))

    for rf in facts.regions:
        hits: List[str] = []
        good = out.match == "all"
        for f, raw in live:
            try:
                hit = bool(f.test(facts, rf, raw))
            except Exception:                          # noqa: BLE001 - a filter
                hit = False                            # that throws is a filter
            if bool(raw.get("negate")):                # that did not match
                hit = not hit
            if hit:
                note = ""
                if f.why and not raw.get("negate"):
                    try:
                        note = f.why(facts, rf, raw)
                    except Exception:                  # noqa: BLE001
                        note = ""
                hits.append(f"{f.label}: {note}" if note
                            else (f"not {f.label}" if raw.get("negate")
                                  else f.label))
            if out.match == "all":
                good = good and hit
                if not good:
                    break
            else:
                good = good or hit
        if live and good:
            out.matched.append(rf)
            out.why[rf.name] = hits
    if not live:
        out.matched = []
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out


# ---------------------------------------------------------------------------
# a colouring: a theme, or one of Geomod's information maps
#
# The two are the same object. A theme groups provinces by who holds them; an
# information map groups them by what is in them. Everything after the grouping
# - the palette, the payload, the TGA, the legend - is shared, which is why
# there is one class here rather than two that would drift.


@dataclass
class Group:
    """One band of a colouring, and every province in it."""

    key: str
    label: str
    rgb: Rgb
    regions: List[str] = field(default_factory=list)
    pixels: int = 0

    def payload(self) -> dict:
        return {"key": self.key, "label": self.label, "rgb": list(self.rgb),
                "regions": len(self.regions), "pixels": self.pixels,
                "names": self.regions[:40]}


@dataclass
class Colouring:
    """A grouping of provinces plus the colour each group takes."""

    code: str
    label: str
    group: str
    #: ``category`` is a set of names with no order, ``scale`` is a magnitude
    #: with bands that read low to high. The legend draws them differently and
    #: nothing else cares.
    kind: str = "category"
    source: str = ""
    note: str = ""
    #: whether a border between groups is worth drawing. True for the three
    #: themes, where the interesting thing is the shape of the blocs.
    borders: bool = False
    groups: List[Group] = field(default_factory=list)
    #: region code name, lower case, to an index into :attr:`groups`
    of_region: Dict[str, int] = field(default_factory=dict)
    #: values whose declared colour was too close to something already on the
    #: map to tell apart, and which are drawn in the fallback palette instead.
    #: ``{"value", "declared", "clash"}``, and the panel says so.
    substituted: List[dict] = field(default_factory=list)
    off: str = ""

    def rgb_of(self, rf: RegionFacts) -> Optional[Rgb]:
        at = self.of_region.get(rf.name.lower())
        return self.groups[at].rgb if at is not None else None

    def payload(self, facts: "Facts") -> dict:
        table: Dict[str, List[int]] = {}
        for rf in facts.regions:
            if rf.region_id < 0:
                continue
            rgb = self.rgb_of(rf)
            table[str(rf.rgb_key)] = list(rgb if rgb else NO_GROUP)
        return {"code": self.code, "label": self.label, "group": self.group,
                "kind": self.kind, "source": self.source, "note": self.note,
                "borders": self.borders, "off": self.off,
                "substituted": list(self.substituted),
                "groups": [g.payload() for g in self.groups],
                "ungrouped": sum(1 for rf in facts.regions
                                 if rf.region_id >= 0 and not self.rgb_of(rf)),
                "colours": table}


# -- palettes ----------------------------------------------------------------

#: The golden angle, in turns. Stepping the hue by it gives colours that stay
#: apart at any count, which a fixed list of twelve does not: a mod with 31
#: factions would run out and start repeating, and two factions sharing a
#: colour on a faction map is the one thing that map may not do.
_GOLDEN = 0.6180339887498949


def _hsv(h: float, s: float, v: float) -> Rgb:
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t),
               (p, q, v), (t, p, v), (v, p, q))[i]
    return (int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5))


def palette(n: int) -> List[Rgb]:
    """``n`` colours that stay apart, in a fixed order.

    Saturation and value alternate slightly as well as the hue, because hue
    alone puts two of anything above twenty within a few degrees of each other
    and the eye reads those as the same colour on a province the size of a
    thumbnail.
    """
    out: List[Rgb] = []
    for i in range(max(n, 0)):
        h = (0.09 + i * _GOLDEN) % 1.0
        s = 0.55 + 0.18 * (i % 3)
        v = 0.95 - 0.16 * (i % 2)
        out.append(_hsv(h, min(s, 1.0), v))
    return out


#: The three stops every magnitude map is drawn along. Viridis's ends and
#: middle: deep purple, teal, yellow. Three rather than two because a two-stop
#: ramp between a dark colour and a light one puts its whole low half within a
#: few units of the sea behind the map, and the first version of this measured
#: exactly that - Third Age Reforged uses farming levels 0 to 2 and the picture
#: came out as one dark blue field with the coastline invisible. It is also the
#: ramp that survives being looked at by somebody who cannot tell red from
#: green, which a red-to-green one is not.
_RAMP: Tuple[Rgb, Rgb, Rgb] = ((68, 1, 84), (33, 145, 140), (253, 231, 37))


def ramp(t: float) -> Rgb:
    """A colour along the ramp, ``t`` from 0 (lowest band) to 1 (highest)."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    half = 0 if t < 0.5 else 1
    u = t * 2 - half
    a, b = _RAMP[half], _RAMP[half + 1]
    return tuple(int(x + (y - x) * u + 0.5)                # type: ignore[return-value]
                 for x, y in zip(a, b))


# -- building one ------------------------------------------------------------


#: How far apart two colours have to be, as a straight RGB distance, before two
#: provinces can be told apart at map size. Measured against a real mod rather
#: than picked: Third Age Reforged is a Middle-earth mod with a deliberately
#: dark faction palette, and inside it ``france`` is 7 from ``moors``,
#: ``spain`` is 8 from ``portugal`` and ``england`` is ``0 0 0``, which is
#: exactly the settlement marker. Sixteen is the value at which those pairs are
#: caught and the mod's own reds, greens and blues all survive.
COLOUR_GAP = 16.0

#: Colours a group may never be given, because something else on the map is
#: already using them and the picture has to stay readable: the two marker
#: pixels, the sea behind the provinces, an ungrouped province and the border.
RESERVED: Tuple[Rgb, ...] = (SETTLEMENT_RGB, PORT_RGB, BACKDROP, NO_GROUP,
                             BORDER)

_RESERVED_NAMES = ("the settlement marker", "the port marker", "the sea",
                   "an ungrouped province", "the border line")


def _distance(a: Rgb, b: Rgb) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _clash(rgb: Rgb, taken: Sequence[Tuple[Rgb, str]],
           gap: float = COLOUR_GAP) -> str:
    """What ``rgb`` is too close to already, or ``""``."""
    for other, name in taken:
        if _distance(rgb, other) < gap:
            return name
    return ""


def assign_colours(order: Sequence[str], declared: Dict[str, Rgb]
                   ) -> Tuple[List[Rgb], List[dict]]:
    """A colour per value, using each one's own wherever it can be told apart.

    A faction map should read the way the campaign's own does, so a faction
    keeps the colour ``descr_sm_factions.txt`` gives it. It cannot keep one
    that something else on the map is already using, though, and this is not a
    hypothetical: Third Age Reforged declares ``england`` as ``0 0 0``, which
    is exactly the settlement marker's colour, and ``france`` as ``37 37 37``,
    which at map size is the border line.

    So a declared colour is used unless it is within :data:`COLOUR_GAP` of one
    of the five reserved colours or of a colour already placed, and the values
    are walked biggest bloc first so the province that takes up most of the map
    is the one that keeps its own colour. What was swapped and what it clashed
    with is returned rather than hidden: a legend that quietly recolours a
    faction is lying about the mod in a quieter way.
    """
    spare = palette(len(order) + len(RESERVED))
    taken: List[Tuple[Rgb, str]] = list(zip(RESERVED, _RESERVED_NAMES))
    out: List[Rgb] = []
    swapped: List[dict] = []
    at = 0
    for v in order:
        want = declared.get(v)
        if want:
            why = _clash(want, taken)
            if not why:
                out.append(want)
                taken.append((want, v))
                continue
            swapped.append({"value": v, "declared": list(want), "clash": why})
        while at < len(spare) and _clash(spare[at], taken, COLOUR_GAP):
            at += 1
        rgb = spare[at] if at < len(spare) else (200, 200, 200)
        at += 1
        out.append(rgb)
        taken.append((rgb, v))
    return out, swapped


def _by_value(facts: "Facts", code: str, label: str, group: str,
              source: str, get: Callable[[RegionFacts], str],
              colours: Optional[Dict[str, Rgb]] = None,
              labeller: Optional[Callable[[str], str]] = None,
              note: str = "", borders: bool = False,
              needs: str = "") -> Colouring:
    """A category colouring: one group per distinct value.

    Ordered by how many provinces are in each, commonest first, so the palette
    puts its clearest colours on the blocs that take up the most of the map.
    """
    col = Colouring(code=code, label=label, group=group, kind="category",
                    source=source, note=note, borders=borders)
    counts: Dict[str, int] = {}
    for rf in facts.regions:
        v = get(rf)
        if v:
            counts[v] = counts.get(v, 0) + 1
    if not counts:
        col.off = _no_evidence(facts, needs, label)
        return col
    order = sorted(counts, key=lambda v: (-counts[v], v.lower()))
    chosen, swapped = assign_colours(order, colours or {})
    col.substituted = swapped
    for i, v in enumerate(order):
        col.groups.append(Group(key=v, label=labeller(v) if labeller else v,
                                rgb=chosen[i]))
    at = {v: i for i, v in enumerate(order)}
    for rf in facts.regions:
        v = get(rf)
        if v in at:
            col.of_region[rf.name.lower()] = at[v]
            g = col.groups[at[v]]
            g.regions.append(rf.name)
            g.pixels += rf.pixels
    return col


def _by_band(facts: "Facts", code: str, label: str, group: str, source: str,
             get: Callable[[RegionFacts], Optional[int]],
             bands: Sequence[Tuple[str, int, int]], note: str = "",
             needs: str = "") -> Colouring:
    """A magnitude colouring: fixed bands, low to high, along the ramp."""
    col = Colouring(code=code, label=label, group=group, kind="scale",
                    source=source, note=note)
    n = max(len(bands) - 1, 1)
    for i, (name, _lo, _hi) in enumerate(bands):
        col.groups.append(Group(key=name, label=name, rgb=ramp(i / n)))
    any_value = False
    for rf in facts.regions:
        v = get(rf)
        if v is None:
            continue
        any_value = True
        for i, (_name, lo, hi) in enumerate(bands):
            if lo <= v <= hi:
                col.of_region[rf.name.lower()] = i
                col.groups[i].regions.append(rf.name)
                col.groups[i].pixels += rf.pixels
                break
    if not any_value:
        col.off = _no_evidence(facts, needs, label)
    return col


def _no_evidence(facts: "Facts", needs: str, label: str) -> str:
    for s in facts.skipped:
        if needs and s["what"] == needs:
            return s["why"]
    return (f"Nothing on this map has a value for {label.lower()}, so there "
            f"is nothing to colour.")


# -- the fixed list ----------------------------------------------------------

#: Geomod's population bands, which are the settlement levels' own thresholds
#: rather than a range split into six. A map whose bands are arbitrary tells
#: you about the bands.
POPULATION_BANDS: Tuple[Tuple[str, int, int], ...] = (
    ("under 800", 0, 799), ("800 to 1,999", 800, 1999),
    ("2,000 to 5,999", 2000, 5999), ("6,000 to 11,999", 6000, 11999),
    ("12,000 to 23,999", 12000, 23999), ("24,000 and over", 24000, 1 << 30))

FARMING_BANDS: Tuple[Tuple[str, int, int], ...] = tuple(
    (f"level {n}", n, n) for n in range(6))

SHARE_BANDS: Tuple[Tuple[str, int, int], ...] = (
    ("none", 0, 0), ("1 to 24%", 1, 24), ("25 to 49%", 25, 49),
    ("50 to 74%", 50, 74), ("75 to 99%", 75, 99), ("all of it", 100, 100))


def theme_faction(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "faction", "Factions", "Themes",
        "TWMapReader's faction theme; the faction block each settlement is "
        "written inside, coloured with that faction's own primary_colour",
        lambda r: r.owner, colours=facts.faction_colours,
        labeller=facts.faction_label, borders=True,
        needs=campstrat.STRAT_NAME,
        note="Each faction takes the colour descr_sm_factions.txt gives it, so "
             "the map reads the way the campaign's own does. A faction with no "
             "colour declared falls back to the palette.")


def theme_religion(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "religion", "Religion majority", "Themes",
        "TWMapReader's religion theme; the largest share in the region's "
        "religions block",
        lambda r: r.religion_majority, borders=True, needs="descr_regions.txt",
        note="A province split evenly has no majority and stays uncoloured, "
             "which is the state it is really in.")


def theme_culture(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "culture", "Cultures", "Themes",
        "TWMapReader's culture theme; the culture of the faction holding the "
        "province at the start",
        lambda r: r.culture, borders=True, needs="descr_sm_factions.txt")


def info_agriculture(facts: "Facts") -> Colouring:
    return _by_band(
        facts, "agriculture", "Agriculture", "Information maps",
        "Geomod's agriculture map; the farming line of the descr_regions.txt "
        "record",
        lambda r: r.farming, FARMING_BANDS, needs="descr_regions.txt")


def info_population(facts: "Facts") -> Colouring:
    return _by_band(
        facts, "population", "Population", "Information maps",
        "Geomod's population map; the population line of the settlement block",
        lambda r: r.population or None, POPULATION_BANDS,
        needs=campstrat.STRAT_NAME)


def info_creators(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "creators", "Creators", "Information maps",
        "Geomod's creators map; the faction line of the descr_regions.txt "
        "record",
        lambda r: r.creator, colours=facts.faction_colours,
        labeller=facts.faction_label, needs="descr_regions.txt")


def info_factions(facts: "Facts") -> Colouring:
    col = theme_faction(facts)
    col.code, col.group, col.borders = "factions", "Information maps", False
    col.source = ("Geomod's factions map; the same grouping as the faction "
                  "theme, exported rather than drawn over the layers")
    return col


def info_mercenaries(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "mercenaries", "Mercenary pools", "Information maps",
        "Geomod's mercenary pool map; the regions line of each pool block in "
        "descr_mercenaries.txt",
        lambda r: r.merc_pools[0] if r.merc_pools else "", needs=MERCS_NAME,
        note="A province in more than one pool is coloured by the first pool "
             "in the file that names it. The filter matches all of them; a "
             "map has one colour per tile and has to pick.")


def info_rebels(facts: "Facts") -> Colouring:
    return _by_value(
        facts, "rebels", "Rebel pools", "Information maps",
        "Geomod's rebel pool map; the rebel line of the descr_regions.txt "
        "record",
        lambda r: r.rebels, needs="descr_regions.txt")


#: The fixed colourings, in the order the panel lists them.
COLOURINGS: Tuple[Tuple[str, Callable[["Facts"], Colouring]], ...] = (
    ("faction", theme_faction),
    ("religion", theme_religion),
    ("culture", theme_culture),
    ("agriculture", info_agriculture),
    ("creators", info_creators),
    ("factions", info_factions),
    ("mercenaries", info_mercenaries),
    ("rebels", info_rebels),
    ("population", info_population),
)


# -- the per-value ones ------------------------------------------------------
#
# Geomod writes one map per hidden resource, one per religion and one per trade
# resource, and a mod can have forty of each. They are built on request from
# the code rather than listed as forty functions.


def _one_resource(facts: "Facts", code: str, value: str, label: str,
                  source: str, get: Callable[[RegionFacts], List[str]]
                  ) -> Colouring:
    """A province either has this resource or it does not, so two groups.

    Two colours rather than a ramp of counts: Geomod's per-resource maps are
    presence maps, and a province with two vineyards is not twice as much of a
    vineyard region. The count is in the legend instead.
    """
    col = Colouring(code=code, label=label, group="Information maps",
                    kind="category", source=source)
    low = value.lower()
    hit = Group(key=value, label=value, rgb=(232, 196, 88))
    miss = Group(key="", label="none", rgb=NO_GROUP)
    col.groups = [hit, miss]
    for rf in facts.regions:
        n = sum(1 for v in get(rf) if v.lower() == low)
        at = 0 if n else 1
        col.of_region[rf.name.lower()] = at
        col.groups[at].regions.append(rf.name)
        col.groups[at].pixels += rf.pixels
    if not hit.regions:
        col.off = f"no province on this map has {value}"
    return col


def _one_religion(facts: "Facts", value: str) -> Colouring:
    return _by_band(
        facts, f"religion:{value}", f"Religion: {value}", "Information maps",
        "Geomod's per-religion maps; that religion's share of the region's "
        "religions block",
        lambda r: r.religions.get(value, 0), SHARE_BANDS,
        needs="descr_regions.txt")


def colouring(facts: "Facts", code: str) -> Colouring:
    """One theme or information map by code, built on demand.

    Raises :class:`~unittransfer.campmap.MapError` for a code nothing declares,
    which the route turns into a 404 rather than an empty picture.
    """
    for name, fn in COLOURINGS:
        if name == code:
            return fn(facts)
    head, _, value = code.partition(":")
    if value:
        if head == "hidden":
            return _one_resource(
                facts, code, value, f"Hidden resource: {value}",
                "Geomod's per-hidden-resource maps; the resource line of the "
                "descr_regions.txt record",
                lambda r: r.hidden_resources)
        if head == "trade":
            return _one_resource(
                facts, code, value, f"Trade resource: {value}",
                "Geomod's per-trade-resource maps; every resource line in "
                "descr_strat.txt, placed in the province it stands in",
                lambda r: r.trade_resources)
        if head == "religion":
            return _one_religion(facts, value)
    raise MapError(f"no theme or information map called {code!r}")


def catalogue(facts: "Facts") -> List[dict]:
    """Every colouring this map can be given, without building any of them.

    The per-value ones are listed from what is actually on the map rather than
    from what the mod declares, for the same reason a filter's vocabulary is:
    offering "one map per hidden resource" for a resource no province has is
    offering a picture that is known to be blank.
    """
    out: List[dict] = []
    for name, fn in COLOURINGS:
        col = fn(facts)
        out.append({"code": col.code, "label": col.label, "group": col.group,
                    "kind": col.kind, "note": col.note, "source": col.source,
                    "borders": col.borders, "off": col.off,
                    "groups": len(col.groups)})
    for kind, label, get in (
            ("hidden", "Hidden resource", lambda r: r.hidden_resources),
            ("trade", "Trade resource", lambda r: r.trade_resources),
            ("religion", "Religion", lambda r: list(r.religions))):
        for value, n in facts.values_of(get):
            out.append({"code": f"{kind}:{value}", "label": f"{label}: {value}",
                        "group": "Information maps", "kind": "category",
                        "note": "", "source": "", "borders": False, "off": "",
                        "groups": 2, "regions": n})
    return out


# ---------------------------------------------------------------------------
# drawing one, in Python, at map size
#
# The screen does not use this - the browser recolours the region layer it is
# already holding, through the same table - but an export does, and so would
# anything that ever wanted a picture without a browser. Both sides read the
# one `Colouring`, so the file on disk and the picture on screen cannot
# disagree about which province is which colour.


#: A marker tile keeps its own colour on an exported map - a black settlement
#: pixel and a white port pixel, exactly as on ``map_regions.tga``. Geomod's
#: information maps do the same, and it is what makes the picture recognisable
#: as this map rather than as an abstract blob chart.
_MARKERS: Dict[int, Rgb] = {key(SETTLEMENT_RGB): SETTLEMENT_RGB,
                            key(PORT_RGB): PORT_RGB}

def _label_colours(facts: "Facts", of_region: Callable[[RegionFacts],
                                                       Optional[Rgb]]
                   ) -> Tuple[List[Rgb], List[int]]:
    """``(one colour per label, one group id per label)``.

    The group id is what a border is worked out from: two tiles are on a border
    when their group ids differ, which is not the same as their colours
    differing (two provinces of one faction share a colour and must not have a
    line drawn between them).
    """
    index = facts.cm.index
    by_name = {rf.name.lower(): rf for rf in facts.regions}
    colours: List[Rgb] = []
    groups: List[int] = []
    seen: Dict[Tuple[int, int, int], int] = {}
    for c in index.colours:
        k = key(c)
        if k in _MARKERS:
            colours.append(_MARKERS[k])
            groups.append(-1)
            continue
        reg = index.by_key.get(k)
        rf = by_name.get(reg.record.name.lower()) if reg and reg.record else None
        rgb = of_region(rf) if rf else None
        if rf is None:
            colours.append(BACKDROP)
            groups.append(-1)
        elif rgb is None:
            colours.append(NO_GROUP)
            groups.append(-2)
        else:
            colours.append(rgb)
            groups.append(seen.setdefault(rgb, len(seen)))
    return colours, groups


def render(facts: "Facts", col: Colouring, borders: Optional[bool] = None
           ) -> Image.Image:
    """One colouring as an image the size of ``map_regions.tga``.

    The label image is already one byte per tile, so this is a palette swap
    rather than a pass over pixels: the labels go in as a P-mode image, the
    group colours go in as its palette, and Pillow does the conversion. The
    only per-tile loop is the border pass, and it only runs for a theme.
    """
    index = facts.cm.index
    colours, groups = _label_colours(facts, col.rgb_of)
    img = Image.frombytes("P", (index.width, index.height), index.labels)
    flat: List[int] = []
    for c in colours:
        flat.extend(c)
    flat.extend([0, 0, 0] * (256 - len(colours)))
    img.putpalette(flat[:768])
    out = img.convert("RGB")
    if borders if borders is not None else col.borders:
        _draw_borders(out, index, groups)
    return out


def _draw_borders(img: Image.Image, index, groups: List[int]) -> None:
    """A line where two different groups meet.

    Four-connected and drawn on the left-hand tile of each pair, the same rule
    and the same direction as :func:`unittransfer.campmap._adjacency`, so a
    border on this picture is a border that index would report. A tile in no
    group takes no line: an uncoloured province is not a political frontier, it
    is a province the mod says nothing about.
    """
    w, h, labels = index.width, index.height, index.labels
    px = img.load()
    edge: List[Tuple[int, int]] = []
    for y in range(h):
        row = y * w
        for x in range(w):
            g = groups[labels[row + x]]
            if g < 0:
                continue
            if x + 1 < w and groups[labels[row + x + 1]] not in (g, -1):
                edge.append((x, y))
                continue
            if y + 1 < h and groups[labels[row + w + x]] not in (g, -1):
                edge.append((x, y))
    for x, y in edge:
        px[x, y] = BORDER


def render_query(facts: "Facts", result: QueryResult) -> Image.Image:
    """The matched provinces in one colour, the rest of the map behind them."""
    hit = {rf.name.lower() for rf in result.matched}
    col = Colouring(code="query", label="Query", group="Query")
    col.groups = [Group(key="match", label="matches", rgb=HIGHLIGHT)]
    col.of_region = {name: 0 for name in hit}
    return render(facts, col, borders=False)


# ---------------------------------------------------------------------------
# writing it out


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_") or "map"


def export_dir(mod, sub: str = "") -> Path:
    """Where an export lands: the cache, never the mod.

    Same reasoning as the validator's baseline. This is derived data about
    somebody else's files, a mod folder can be inside OneDrive, and a tool that
    drops forty TGAs into ``data/world/maps/base`` has changed a mod nobody
    asked it to change.
    """
    from . import config
    out = config.cache_dir("mapexport") / _slug(getattr(mod, "name", "mod"))
    if sub:
        out = out / _slug(sub)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_tga(facts: "Facts", img: Image.Image, path: Path) -> int:
    """The picture, in the shape of the mod's own ``map_regions.tga``.

    The header is that layer's rather than a fresh one, so what comes out is
    the size, the origin and the depth the tools that made the map expect. A
    24-bit uncompressed file would open too; matching is free and means an
    exported map can be dropped straight back into a workflow.
    """
    info = facts.cm.info("regions")
    data = encode(img, info)
    path.write_bytes(data)
    return len(data)


@dataclass
class Export:
    """What one export wrote."""

    folder: str = ""
    files: List[dict] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    ms: int = 0

    def payload(self) -> dict:
        return {"folder": self.folder, "files": self.files,
                "skipped": self.skipped, "count": len(self.files),
                "bytes": sum(f["bytes"] for f in self.files), "ms": self.ms}


def export_colouring(facts: "Facts", code: str) -> Export:
    """One theme or information map, as one TGA."""
    t0 = time.perf_counter()
    col = colouring(facts, code)
    out = Export()
    if col.off:
        out.skipped.append({"what": col.label, "why": col.off})
        out.ms = int((time.perf_counter() - t0) * 1000)
        return out
    folder = export_dir(facts.mod)
    path = folder / f"map_{_slug(code)}.tga"
    n = _write_tga(facts, render(facts, col), path)
    out.folder = str(folder)
    out.files.append({"name": path.name, "bytes": n, "label": col.label,
                      "groups": len(col.groups),
                      "regions": len(col.of_region)})
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out


def export_query(facts: "Facts", result: QueryResult) -> Export:
    """The matched set, as one TGA."""
    t0 = time.perf_counter()
    out = Export()
    if not result.matched:
        out.skipped.append({"what": "the query",
                            "why": "nothing matched, so there is nothing to draw"})
        return out
    folder = export_dir(facts.mod)
    path = folder / "map_query.tga"
    n = _write_tga(facts, render_query(facts, result), path)
    out.folder = str(folder)
    out.files.append({"name": path.name, "bytes": n, "label": "Query",
                      "groups": 1, "regions": len(result.matched)})
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out


def export_factions(facts: "Facts") -> Export:
    """One TGA per faction, plus the map they are all on.

    Geomod's batch export, and the reason it is a batch rather than a loop the
    user drives: a faction map is read against the other faction maps - who
    borders whom, who is boxed in - and forty separate exports taken over forty
    minutes are forty pictures of forty slightly different working copies.
    They are written from one fact table, in one call, so they are all of the
    same map.
    """
    t0 = time.perf_counter()
    out = Export()
    col = info_factions(facts)
    if col.off:
        out.skipped.append({"what": "faction maps", "why": col.off})
        out.ms = int((time.perf_counter() - t0) * 1000)
        return out
    folder = export_dir(facts.mod, "factions")
    out.folder = str(folder)

    path = folder / "map_all_factions.tga"
    n = _write_tga(facts, render(facts, col), path)
    out.files.append({"name": path.name, "bytes": n, "label": "Every faction",
                      "groups": len(col.groups), "regions": len(col.of_region)})

    for g in col.groups:
        one = Colouring(code=f"faction:{g.key}", label=g.label, group="Factions")
        one.groups = [Group(key=g.key, label=g.label, rgb=g.rgb)]
        one.of_region = {name.lower(): 0 for name in g.regions}
        path = folder / f"map_faction_{_slug(g.key)}.tga"
        n = _write_tga(facts, render(facts, one), path)
        out.files.append({"name": path.name, "bytes": n, "label": g.label,
                          "groups": 1, "regions": len(g.regions)})
    out.ms = int((time.perf_counter() - t0) * 1000)
    return out


# ---------------------------------------------------------------------------
# what the panel asks for once, when it opens


def vocab(facts: "Facts") -> dict:
    """Every filter, every colouring and every value either can take.

    One call, because all of it comes out of one fact table and a panel that
    fetched fifteen vocabularies separately would be fifteen chances to show
    half a screen. The filters that cannot be asked are in the list with the
    reason on them rather than missing from it, so nobody has to wonder whether
    the tool forgot mercenary pools or the mod did.
    """
    return {
        "mod": getattr(facts.mod, "name", ""), "campaign": facts.campaign,
        "regions": len(facts.regions),
        "mapped": sum(1 for r in facts.regions if r.region_id >= 0),
        "tiles": facts.cm.terrain.tiles,
        "filters": [f.payload(facts) for f in FILTERS],
        "colourings": catalogue(facts),
        "skipped": list(facts.skipped),
        "highlight": list(HIGHLIGHT),
        "no_group": list(NO_GROUP),
        "border": list(BORDER),
        "ms": facts.ms,
    }


# ---------------------------------------------------------------------------
# the markers layer (17d)

#: Where a mod keeps a trade resource's picture, and the name it gives it. Both
#: real mods follow it: Third Age Reforged ships six of these and lets the game
#: fall back to its own art for the rest, which is why a missing one is normal
#: and is answered with an empty string rather than a fault.
RESOURCE_ART = "ui/resources/resource_{name}.tga"


def _resource_art(mod, name: str) -> str:
    """The mod's own picture for one resource, as a path under ``data/``.

    ``''`` when the mod ships none - which is the ordinary case, because the
    stock game's copy is inside a ``.pack`` archive that nothing here reads. The
    browser draws its own glyph then, rather than a broken image.
    """
    rel = RESOURCE_ART.format(name=re.sub(r"[^A-Za-z0-9_.-]", "", name or ""))
    try:
        return rel if (Path(mod.data) / rel).is_file() else ""
    except OSError:
        return ""


def marker_view(facts: "Facts") -> dict:
    """Everything in ``descr_strat.txt`` that stands on a tile, drawable.

    17d. :func:`campstrat.markers` does the reading and knows nothing about
    factions or art; this joins the two things a picture needs and nothing more
    - what each faction is called and what colour it flies, which the fact table
    already holds, and which resources this mod ships a picture for.

    Coordinates are left exactly as the file writes them. The flip to image
    coordinates belongs to whatever is holding the map's height, and doing it
    twice in two places is how a marker ends up mirrored.
    """
    out: dict = {"mod": getattr(facts.mod, "name", ""), "campaign": facts.campaign,
                 "items": [], "counts": {}, "factions": {}, "art": {},
                 "skipped": [s for s in facts.skipped
                             if campstrat.STRAT_NAME in str(s)]}
    if facts.strat is None:
        return out
    items = campstrat.markers(facts.strat)
    out["items"] = items
    counts: Dict[str, int] = {}
    for it in items:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    out["counts"] = counts
    seen = {it["faction"] for it in items if it["faction"]}
    for code in sorted(seen):
        rgb = facts.faction_colours.get(code)
        out["factions"][code] = {
            "label": facts.faction_labels.get(code) or code,
            "colour": list(rgb) if rgb else None,
        }
    for name in sorted({it["name"] for it in items if it["kind"] == "resource"}):
        art = _resource_art(facts.mod, name)
        if art:
            out["art"][name] = art
    return out
