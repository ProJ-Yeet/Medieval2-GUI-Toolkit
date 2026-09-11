"""``descr_strat.txt``, write: forts, watchtowers and trade resources.

16b read them - 105 forts and 295 watchtowers in DaC's imperial campaign, 101
and 299 in its Shattered Alliances, each with its line - and nothing wrote a
single one. ``stratchar.UNTOUCHED`` names both as records a character save may
not change, which was the guard working correctly around a feature that did not
exist. This is that feature: add one, move one, change one, delete one, and
the four are the same request with a different ``action``, because in the file
they are the same edit - one line, rewritten, inserted or taken out.

It follows 16h and 16i exactly, and imports their helpers rather than writing
them again: the file is re-read for every plan rather than taken from the fact
table, the new text is parsed back and checked against the old before anything
is offered, and the save is one backup and one entry the Log can undo.

**What the file says, measured on both installed mods rather than assumed.**

*They live in the region sections, not in the factions.* All 800 of DaC's are
written inside the ``region <name>`` sections after the diplomacy, none inside
a faction block, and every one of those 241 sections also carries
``farming_level 0`` and ``famine_threat 0``. Twelve of the imperial campaign's
sections hold nothing else: a section is the province's own record, and it
stays when its last fort goes. Third Age Reforged writes no forts, no
watchtowers and no section at all, and neither of vanilla's campaigns does, so
the first one placed there opens a new section - in the shape DaC writes, which
is also the shape Demir's editor writes.

*A section names the province the object stands in - usually.* 393 of the
imperial campaign's 400 stand in the province their section names, and the
seven that do not are all in ``Erebor_Province``, a section naming a province
the map does not declare. Shattered Alliances reads the same map and manages
352 of 400. So a new fort is filed under the province under its tile, a moved
one stays where it is filed unless it is asked to move, and a mismatch is a
warning with the file's own count on it.

*A fort type is a folder.* Every one of the 206 fort lines on DaC's two
campaigns names a folder under some culture's
``settlements/*/ambient_settlements`` - but not the culture it is written
with: ``cerin_amroth_fort culture middle_eastern`` is drawn out of the
``mesoamerican`` folder. So the type is checked against every culture's
folders, the culture against ``descr_cultures.txt``, and neither against the
other. Vanilla's short form, ``fort <x> <y>``, has neither, and is legal.

*Nothing stands on a settlement, and nothing shares a tile.* None of the 800
is on a settlement or a port pixel and no two are on one tile; 51 forts have a
general standing on them, which is a garrison, not a fault. A watchtower on the
sea (one) or on impassable land (four, Shattered Alliances) is in a mod that
loads, so both are warnings. What is fatal is what has no room in the engine's
own vocabulary: a coordinate that is not a whole number, a tile off the map,
and a culture ``descr_cultures.txt`` does not declare when it is on disk.

**Resources, 22b.** The same four actions over one more kind of line,
``resource <name>, <x>, <y>``, measured on all four installed campaigns (2,813
lines) before a rule was written:

*They are written at the top, not in a section.* Every one sits between the
campaign header and the first faction. Where a new one goes inside that run is
read off how the file groups its own: Third Age Reforged's imperial campaign
heads each group with the province's name as a comment (``;Talsir_Province``,
90 of them) and 410 of its 413 stand in the province their heading names, so a
new one joins its province's group and a province with none gets a heading of
its own - the section rule again. DaC's and the Fellowship campaign's keep
each name together (25 names, 25 runs), so a new one follows the last of its
name. With no resource at all it goes under a banner that says "resource",
else in front of the first faction's banner.

*What the engine is given.* A name ``descr_sm_resources.txt`` does not declare
is fatal, as a culture is; all 2,813 name one it does. Off the map is fatal and
sea a warning - :func:`mapcheck.position_faults`, the validator's own copy -
and so is a second one of the same name on one tile, which DaC's imperial
campaign writes 63 times. Impassable land (9, 7, 4 and 4) and a tile in no
province are warnings carrying the file's own count. **A resource may stand on
a settlement or port pixel**: the province that owns the marker owns it, which
is 16g's rule, and DaC does it once in each campaign. No resource of the 2,813
shares a tile with a fort or a watchtower, so either on the other's is said.

**D10, the snap.** Each finding about the tile - sea, impassable, a marker, a
shared tile - ends on the nearest tile that has none of them, from
:mod:`mapsnap`'s search, and carries it as ``near`` so the panel can offer to
move there. It looks inside the province the record is filed under first.

**The map is the one the campaign reads.** :func:`campmap.campaign_map`: a
campaign folder's own ``map_regions.tga``, ``map_heights.tga`` and the rest win
over the base ones, file by file, as they do in the engine. Third Age
Reforged's Fellowship campaign ships the whole set; nothing else installed
ships one that decides anything here.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campmap, campstrat, mapsnap, stratedit
from .campstrat import Node, StratFile
from .stratedit import comment_of, finding, indent_of, is_int, serialise

#: What this module places.
KINDS = ("fort", "watchtower", "resource")

#: The two that are written inside a ``region`` section.
SECTIONED = ("fort", "watchtower")

ACTIONS = ("edit", "add", "delete", "move")

#: The lines a new section is opened with, before its first object. Every one of
#: DaC's 241 sections writes both at 0.
SECTION_FIELDS = ("farming_level 0", "famine_threat 0")

CULTURES_REL = "descr_cultures.txt"
#: ``settlements/<culture folder>/ambient_settlements/<fort type>/``
AMBIENT = "ambient_settlements"

_OBJ = re.compile(r"^(?P<word>fort|watchtower)(?P<gap>[\t ]+)(?P<x>-?\d+)"
                  r"(?P<sep>[\t ]+)(?P<y>-?\d+)(?P<rest>.*)$", re.I)
#: the parser's own ``resource`` pattern, with every gap kept
_RES = re.compile(r"^(?P<word>resource)(?P<gap>[\t ]+)(?P<name>[\w-]+)"
                  r"(?P<c1>[\t ]*,[\t ]*)(?P<x>-?\d+)(?P<c2>[\t ]*,[\t ]*)"
                  r"(?P<y>-?\d+)(?P<rest>.*)$", re.I)

#: Every resource line on the four installed campaigns, for the one finding
#: that has no count on the file being edited to quote.
MEASURED_RESOURCES = 2813


# ---------------------------------------------------------------------------
# one record


@dataclass
class Spec:
    """One fort, watchtower or resource, as the form holds it."""

    kind: str = "fort"
    x: object = None
    y: object = None
    type: str = ""
    culture: str = ""
    #: a resource's name - ``timber``, ``iron`` - and nothing else's
    name: str = ""

    def payload(self) -> dict:
        return {"kind": self.kind, "x": self.x, "y": self.y,
                "type": self.type, "culture": self.culture, "name": self.name}

    def xy(self) -> Optional[Tuple[int, int]]:
        if is_int(self.x) and is_int(self.y):
            return int(str(self.x)), int(str(self.y))
        return None


def read_spec(node: Node) -> Spec:
    return Spec(kind=node.kind, x=node.get("x"), y=node.get("y"),
                type=str(node.get("type") or ""),
                culture=str(node.get("culture") or ""),
                name=node.name if node.kind == "resource" else "")


def spec_from_body(body: dict, base: Optional[Spec] = None) -> Spec:
    """The form's boxes over the record they came from, or over nothing."""
    s = Spec(**(base.payload() if base else {}))
    s.kind = str(body.get("kind") or s.kind).strip().lower()
    for key in ("x", "y"):
        if key in body and body[key] not in (None, ""):
            v = str(body[key]).strip()
            s.__dict__[key] = int(v) if is_int(v) else v
    if s.kind == "fort":
        for key in ("type", "culture"):
            if key in body:
                s.__dict__[key] = str(body[key] or "").strip()
    else:
        s.type = s.culture = ""
    if s.kind == "resource":
        if "name" in body:
            s.name = str(body["name"] or "").strip()
    else:
        s.name = ""
    return s


def section_of(sf: StratFile, node: Node) -> Optional[Node]:
    """The ``region`` section a record is written in, or None."""
    parent = sf.nodes[node.parent] if node.parent >= 0 else None
    return parent if parent is not None and parent.kind == "region" else None


def objects(sf: StratFile, kinds: Tuple[str, ...] = KINDS) -> List[Node]:
    return [n for n in sf.nodes if n.kind in kinds]


# ---------------------------------------------------------------------------
# the line


@dataclass
class Shape:
    """How this file writes the line, so a new one reads like its neighbours.

    The gap after the keyword is the one thing that varies: DaC writes
    ``fort \\t326 142`` on 145 of its 206 forts and ``watchtower 307 161`` on
    all 594 towers. Nothing is indented. A resource has three gaps and the
    commonest set is kept whole: DaC's ``resource\tdogs,\t\t264,\t431`` on 964
    of 1,131, Reforged's ``resource\ttimber,\t296,\t331`` on all 413 of its
    imperial campaign's.
    """

    indent: str = ""
    gap: Dict[str, str] = field(default_factory=dict)
    #: a resource's: after the keyword, after the name, after x
    res: Tuple[str, str, str] = ("\t", ",\t", ",\t")


def shape_of(sf: StratFile) -> Shape:
    out = Shape()
    gaps: Dict[str, Counter] = {k: Counter() for k in SECTIONED}
    indents: Counter = Counter()
    res: Counter = Counter()
    for n in objects(sf):
        line = sf.lines[n.start]
        if n.kind == "resource":
            m = _RES.match(line.lstrip("\t "))
            if m:
                res[(m.group("gap"), m.group("c1"), m.group("c2"))] += 1
            continue
        m = _OBJ.match(line.lstrip("\t "))
        if m:
            gaps[n.kind][m.group("gap")] += 1
            indents[indent_of(line)] += 1
    out.indent = indents.most_common(1)[0][0] if indents else ""
    for k in SECTIONED:
        out.gap[k] = gaps[k].most_common(1)[0][0] if gaps[k] else " "
    if res:
        out.res = res.most_common(1)[0][0]
    return out


def _tail(spec: Spec) -> str:
    if spec.kind != "fort" or not (spec.type or spec.culture):
        return ""
    return (f" {spec.type}" if spec.type else "") + \
        (f" culture {spec.culture}" if spec.culture else "")


def new_line(spec: Spec, shape: Shape) -> str:
    if spec.kind == "resource":
        g, c1, c2 = shape.res
        return f"resource{g}{spec.name}{c1}{spec.x}{c2}{spec.y}"
    return (f"{shape.indent}{spec.kind}{shape.gap.get(spec.kind, ' ')}"
            f"{spec.x} {spec.y}{_tail(spec)}")


def render_line(line: str, before: Spec, spec: Spec) -> str:
    """``line`` rewritten to say ``spec``, keeping everything else it had.

    Its indent, the gap after the keyword, the gap between the numbers, the
    comment and the trailing space all stay. The type and culture keep their
    own spacing when neither changed - a move of a fort is two numbers.
    """
    com = comment_of(line)
    code = line[:len(line) - len(com)] if com else line
    if spec.kind == "resource":
        m = _RES.match(code.lstrip("\t "))
        if not m:
            return new_line(spec, Shape())
        body = (f"{m.group('word')}{m.group('gap')}{spec.name}{m.group('c1')}"
                f"{spec.x}{m.group('c2')}{spec.y}{m.group('rest').rstrip()}")
        return stratedit.rewrite_line(line, body)
    m = _OBJ.match(code.lstrip("\t "))
    if not m:
        return new_line(spec, Shape(indent=indent_of(line)))
    rest = m.group("rest").rstrip("\t ")
    same = (before.type, before.culture) == (spec.type, spec.culture)
    body = (f"{m.group('word')}{m.group('gap')}{spec.x}{m.group('sep')}{spec.y}"
            f"{rest if same else _tail(spec)}")
    return stratedit.rewrite_line(line, body)


# ---------------------------------------------------------------------------
# where a record goes


def sections(sf: StratFile) -> Dict[str, List[Node]]:
    """Every ``region`` section, by lower-case name, in file order.

    A list, because a name can appear twice: DaC writes ``Celebrant_Province``
    and ``South_Ithilien_Province`` twice each, in both campaigns. A new record
    goes into the first.
    """
    out: Dict[str, List[Node]] = {}
    for n in sf.of_kind("region"):
        out.setdefault(n.name.lower(), []).append(n)
    return out


def content_end(sf: StratFile, section: Node) -> int:
    """The section's last line that says something.

    Not :attr:`Node.end`: the parser closes a section on the line before the
    next thing, so the last one's span runs over the blank lines and the
    ``;#### Scripts ####`` banner in front of ``script``.
    """
    last = section.start
    for ln in section.field_lines.values():
        last = max(last, ln)
    for ci in section.children:
        last = max(last, sf.nodes[ci].end)
    return last


def insert_point(sf: StratFile, section: Node, kind: str) -> int:
    """After the section's last record of this kind, else after its last line.

    DaC's sections list their watchtowers and then their forts, and a new one
    joins its own kind rather than landing between a fort and its neighbour.
    """
    same = [sf.nodes[ci].end for ci in section.children
            if sf.nodes[ci].kind == kind]
    return (max(same) if same else content_end(sf, section)) + 1


def new_section(sf: StratFile, region: str, line: str) -> Tuple[int, List[str]]:
    """Where a new section goes, and its lines.

    After the last section when there is one, with the blank line every one of
    DaC's is separated by. When there is none, where the file says the sections
    go: both of Third Age Reforged's campaigns end on the banner
    ``; >>>> start of regions section <<<<``, a blank line and ``script``, so the
    section goes under that banner. With no such banner it goes in front of the
    run of comments and blank lines that heads ``script`` - DaC's is
    ``;#### Scripts ####`` - so a banner stays on the thing it is a banner for.
    """
    body = [f"region {region}", *SECTION_FIELDS, line]
    have = sf.of_kind("region")
    if have:
        return content_end(sf, have[-1]) + 1, [""] + body
    lines = sf.lines
    script = next((n for n in sf.of_kind("script")), None)
    end = script.start if script is not None else len(lines)
    blank = end
    while blank > 0 and not lines[blank - 1].strip():
        blank -= 1
    top = blank
    while top > 0 and lines[top - 1].lstrip().startswith(";"):
        top -= 1
    if any("region" in ln.lower() for ln in lines[top:blank]):
        at = blank + 1 if blank < end else blank
        return at, ([] if blank < end else [""]) + body + [""]
    at = top
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    return at, [""] + body


@dataclass
class Layout:
    """How a file groups its resources, read off the file rather than assumed.

    ``by`` is ``"province"`` when the run carries comment headings that name
    declared provinces - Reforged's ``;Talsir_Province`` - ``"name"`` when every
    name's lines are together, as DaC's are, and ``""`` for neither.
    """

    by: str = ""
    #: what a heading is written as in front of the name: ``";"``
    prefix: str = ";"
    #: lower-case province -> the line its heading is on
    heads: Dict[str, int] = field(default_factory=dict)
    #: a resource's line -> the province its heading names
    under: Dict[int, str] = field(default_factory=dict)


def layout_of(sf: StratFile, provinces: List[str]) -> Layout:
    out = Layout()
    res = sf.of_kind("resource")
    if not res:
        return out
    known = {p.lower(): p for p in provinces}
    lo = res[0].start
    while lo > 0 and (not sf.lines[lo - 1].strip()
                      or sf.lines[lo - 1].lstrip().startswith(";")):
        lo -= 1
    at = {n.start for n in res}
    prefixes: Counter = Counter()
    head = ""
    for i in range(lo, res[-1].start + 1):
        line = sf.lines[i].strip()
        if line.startswith(";"):
            word = line.lstrip(";").strip()
            if word.lower() in known:
                head = word
                out.heads[word.lower()] = i
                prefixes[line[:line.index(word)]] += 1
        elif i in at and head:
            out.under[i] = head
    names = [n.name.lower() for n in res]
    runs = 1 + sum(1 for a, b in zip(names, names[1:]) if a != b)
    if out.heads:
        out.by = "province"
        out.prefix = prefixes.most_common(1)[0][0]
    elif runs == len(set(names)):
        out.by = "name"
    return out


def resource_home(sf: StratFile, lay: Layout, name: str, province: str,
                  line: str) -> Tuple[int, List[str], str]:
    """Where a new resource line goes, the lines to put there, and the heading
    it opens (``""`` for none)."""
    res = sf.of_kind("resource")
    low = province.lower()
    if lay.by == "province" and low:
        if low in lay.heads:
            mine = [i for i, p in lay.under.items() if p.lower() == low]
            return (max(mine) if mine else lay.heads[low]) + 1, [line], ""
        return res[-1].start + 1, ["", f"{lay.prefix}{province}", line], province
    if lay.by == "name":
        same = [n.start for n in res if n.name.lower() == name.lower()]
        if same:
            return max(same) + 1, [line], ""
    if res:
        return res[-1].start + 1, [line], ""
    # none at all: under a banner that says so, else in front of the first
    # faction's own banner, the way a section goes in front of the scripts'
    lines = sf.lines
    first = next((n for n in sf.nodes if n.kind == "faction"), None)
    end = first.start if first is not None else len(lines)
    top = end
    while top > 0 and (not lines[top - 1].strip()
                       or lines[top - 1].lstrip().startswith(";")):
        top -= 1
    for i in range(top, end):
        if lines[i].lstrip().startswith(";") and "resource" in lines[i].lower():
            return i + 1, [line], ""
    return top, ["", line], ""


def filed_under(sf: StratFile, node: Node, lay: Optional[Layout]) -> str:
    """The section a fort is written in, or the heading a resource is under."""
    if node.kind == "resource":
        return lay.under.get(node.start, "") if lay is not None else ""
    sec = section_of(sf, node)
    return sec.name if sec is not None else ""


# ---------------------------------------------------------------------------
# the vocabulary and the map


class Vocabulary:
    """What a fort or a resource may be called and what it may stand on."""

    def __init__(self, mod, sf: StratFile, cm=None):
        self.mod = mod
        self.cm = cm
        data = Path(mod.data) if mod is not None else None
        #: None when descr_cultures.txt is not on disk, so nothing is checked
        self.cultures: Optional[List[str]] = None
        path = data / CULTURES_REL if data is not None else None
        if path is not None and path.is_file():
            from .keyblock import read_text
            text = read_text(path, "latin-1")
            self.cultures = re.findall(r"^\s*culture\s+(\S+)", text, re.M)
        #: fort type folder -> the culture folders it is under; None with none
        self.folders: Optional[Dict[str, List[str]]] = None
        base = data / "settlements" if data is not None else None
        if base is not None and base.is_dir():
            found: Dict[str, List[str]] = {}
            for c in sorted(base.iterdir()):
                amb = c / AMBIENT
                if amb.is_dir():
                    for t in sorted(amb.iterdir()):
                        if t.is_dir():
                            found.setdefault(t.name.lower(), []).append(c.name)
            self.folders = found or None
        #: what the file itself writes, (type, culture) -> count
        self.pairs: Counter = Counter(
            (str(n.get("type") or ""), str(n.get("culture") or ""))
            for n in sf.of_kind("fort"))
        #: the resource names descr_sm_resources.txt declares; None when it is
        #: not on disk, so nothing is checked against a list we do not have
        from . import minorfiles
        self.resources: Optional[List[str]] = (
            minorfiles.resource_names(mod) or None) if mod is not None else None
        #: what the file writes, name -> count
        self.res_names: Counter = Counter(n.name for n in sf.of_kind("resource")
                                          if n.name)
        self.provinces: List[str] = []
        self._ground = self._feats = None
        #: settlement and port pixels, image coords -> (province, "settlement")
        self.markers: Dict[Tuple[int, int], Tuple[str, str]] = {}
        if cm is not None:
            try:
                idx = cm.index
                self.provinces = sorted(r.name for r in idx.regions if r.name)
                for r in idx.regions:
                    if r.settlement:
                        self.markers[tuple(r.settlement)] = (r.name, "settlement")
                    if r.port:
                        self.markers[tuple(r.port)] = (r.name, "port")
            except Exception:                     # a map that will not index
                self.cm = None
        self.layout = layout_of(sf, self.provinces)

    # -- the tile -------------------------------------------------------------

    def in_bounds(self, gx: int, gy: int) -> Optional[bool]:
        if self.cm is None:
            return None
        ix, iy = self.cm.image_xy(gx, gy)
        return self.cm.terrain.in_bounds(ix, iy)

    def province_at(self, gx: int, gy: int) -> str:
        """The declared province under a tile in the file's coordinates.

        A settlement or port pixel names the province that owns it, which is
        16g's rule for a resource standing on a marker, taken as it is.
        """
        if self.cm is None or not self.in_bounds(gx, gy):
            return ""
        ix, iy = self.cm.image_xy(gx, gy)
        r = self.cm.index.at(ix, iy)
        if r is not None and r.name:
            return r.name
        return self.markers.get((ix, iy), ("", ""))[0]

    def ground(self, gx: int, gy: int) -> Optional[dict]:
        from . import mapcheck, mapvocab
        from .campmap import MapError
        if self.cm is None:
            return None
        if self._ground is None:
            try:
                self._ground = mapcheck._triples(self.cm.tiles("ground_types"))
            except MapError:
                self._ground = b""
        if not self._ground:
            return None
        ix, iy = self.cm.image_xy(gx, gy)
        return mapvocab.ground_at(
            mapcheck._at(self._ground, self.cm.terrain.width, ix, iy))

    def sea(self, gx: int, gy: int) -> Optional[bool]:
        """Whether the engine reads the tile as sea; None when it cannot say."""
        from .campmap import MapError
        if self.cm is None:
            return None
        ix, iy = self.cm.image_xy(gx, gy)
        try:
            return bool(self.cm.sea[iy * self.cm.terrain.width + ix])
        except MapError:
            return None

    def marker(self, gx: int, gy: int) -> str:
        """``"Nottingham_Province's settlement"`` for a marker pixel, else ``""``."""
        if self.cm is None:
            return ""
        name, kind = self.markers.get(self.cm.image_xy(gx, gy), ("", ""))
        return f"{name}'s {kind}" if kind else ""

    # -- the pickers ----------------------------------------------------------

    def fort_types(self) -> List[dict]:
        """What the type box offers: the file's own, then the folders.

        A folder is offered only when "fort" is in its name and "fortified" is
        not: ``ambient_settlements`` also holds the farms, hamlets and fortified
        houses the battle map scatters, and DaC's 93 folders are mostly those.
        """
        seen: Dict[str, dict] = {}
        for (t, c), n in self.pairs.most_common():
            if t and t.lower() not in seen:
                seen[t.lower()] = {"name": t, "culture": c, "uses": n,
                                   "folder": bool(self.folders
                                                  and t.lower() in self.folders)}
        for name in sorted(self.folders or {}):
            if "fort" in name and "fortified" not in name and name not in seen:
                seen[name] = {"name": name, "culture": "", "uses": 0,
                              "folder": True}
        return list(seen.values())

    def resource_names(self) -> List[dict]:
        """What the name box offers: the declared list, the file's own counts.

        With ``descr_sm_resources.txt`` packed, the names the file already
        writes and the 28 every installed mod ships, and nothing is checked.
        """
        from .minorfiles import KNOWN_RESOURCES
        names = self.resources or sorted(set(KNOWN_RESOURCES) | set(self.res_names))
        return [{"name": n, "uses": self.res_names.get(n, 0)} for n in names]

    def payload(self) -> dict:
        return {"cultures": self.cultures, "fort_types": self.fort_types(),
                "have_folders": self.folders is not None,
                "provinces": self.provinces,
                "resources": self.resource_names(),
                "have_resources": self.resources is not None,
                "grouped_by": self.layout.by}

    # -- D10 ------------------------------------------------------------------

    def _grid(self):
        """The four things the snap asks of every tile, as flat bytes.

        A search can ask 6,561 tiles, and 1,531 records on DaC's imperial
        campaign can each start one, so it reads the sea mask, the ground
        layer and the region labels directly rather than going through a
        method call per tile.
        """
        if getattr(self, "_grid_", None) is None:
            from . import mapvocab
            from .campmap import MapError
            try:
                sea = self.cm.sea
                idx = self.cm.index
            except MapError:
                self._grid_ = ()
                return self._grid_
            self.ground(0, 0)                     # fills self._ground
            imp = mapvocab.ground("impassable_land")["rgb"]
            names = [(r.name if r is not None and r.name else "")
                     for r in (idx.by_key.get(campmap.key(c)) for c in idx.colours)]
            self._grid_ = (sea, self._ground or b"", bytes(imp), idx.labels, names)
        return self._grid_

    def snap(self, kind: str, gx: int, gy: int, taken: Dict[Tuple[int, int], set],
             name: str = "", home: str = "") -> Optional[Tuple[Tuple[int, int], str]]:
        """The nearest tile none of this kind's tile findings would be about.

        Not sea, not impassable land, in a province, with nothing of the
        other class on it and nothing of its own kind (for a resource, of its
        own name); a fort or a watchtower is also kept off the settlement and
        port pixels, which a resource is allowed on. Inside ``home`` - the
        province it is filed under - when any tile there within the radius
        will do, and anywhere otherwise. ``((gx, gy), province)`` or None.
        """
        if self.cm is None or not self._grid():
            return None
        sea, ground, imp, labels, names = self._grid()
        t = self.cm.terrain
        w, h = t.width, t.height
        start = self.cm.image_xy(gx, gy)
        own = "res:" + name.lower()

        def ok(ix: int, iy: int, want: str) -> bool:
            i = iy * w + ix
            if (ix, iy) == start or sea[i] or \
                    (ground and ground[i * 3:i * 3 + 3] == imp):
                return False
            here = names[labels[i]] or self.markers.get((ix, iy), ("", ""))[0]
            if not here or (want and here.lower() != want):
                return False
            there = taken.get((ix, t.game_y(iy)))
            if kind == "resource":
                return not there or not (there & {"fort", "watchtower", own})
            return not there and (ix, iy) not in self.markers

        for want in ([home.lower(), ""] if home else [""]):
            at = mapsnap.nearest(w, h, start[0], start[1],
                                 lambda a, b: ok(a, b, want))
            if at is not None:
                g = self.cm.game_xy(*at)
                return g, self.province_at(*g)
        return None


def standing(sf: StratFile) -> Dict[Tuple[int, int], List[Node]]:
    """Every record on each tile, in file order."""
    out: Dict[Tuple[int, int], List[Node]] = {}
    for n in objects(sf):
        xy = read_spec(n).xy()
        if xy is not None:
            out.setdefault(xy, []).append(n)
    return out


def taken_tiles(at: Dict[Tuple[int, int], List[Node]], leave: Optional[Node] = None
                ) -> Dict[Tuple[int, int], set]:
    """What stands on each tile - ``{"fort"}``, ``{"resource", "res:timber"}`` -
    with ``leave`` taken off the tile it is leaving."""
    out: Dict[Tuple[int, int], set] = {}
    for xy, nodes in at.items():
        got = out.setdefault(xy, set())
        for n in nodes:
            if n is leave:
                continue
            got.add(n.kind)
            if n.kind == "resource":
                got.add("res:" + n.name.lower())
    return out


# ---------------------------------------------------------------------------
# the checks


def _placed_well(sf: StratFile, voc: Vocabulary) -> Tuple[int, int]:
    """How many of the file's own records stand in the province they are filed
    under, out of how many are filed under one - the number a mismatch warning
    carries, counted on the file being edited rather than quoted from DaC."""
    good = total = 0
    for n in objects(sf, SECTIONED):
        sec = section_of(sf, n)
        xy = read_spec(n).xy()
        if sec is None or xy is None:
            continue
        total += 1
        good += voc.province_at(*xy).lower() == sec.name.lower()
    return good, total


@dataclass
class Census:
    """What the file being edited already does, counted once.

    Every warning quotes a number, and the number is this file's where it can
    be: the panel checks all 2,178 of DaC's records at once, and walking the
    file again per record to count them would be 2,178 walks.
    """

    #: every record on each tile
    at: Dict[Tuple[int, int], List[Node]] = field(default_factory=dict)
    #: what stands on each tile, the way :meth:`Vocabulary.snap` asks
    tiles: Dict[Tuple[int, int], set] = field(default_factory=dict)
    #: how this file groups its resources - this file's, not the one the
    #: vocabulary was read with, since a plan checks the file it made
    layout: Layout = field(default_factory=Layout)
    #: forts and watchtowers standing in the province of their section
    placed: Tuple[int, int] = (0, 0)
    #: resources standing in the province their heading names
    headed: Tuple[int, int] = (0, 0)
    resources: int = 0
    #: resources on sea, on impassable land, and in no province
    sea: set = field(default_factory=set)
    rough: set = field(default_factory=set)
    lost: set = field(default_factory=set)


def census(sf: StratFile, voc: Vocabulary) -> Census:
    at = standing(sf)
    out = Census(at=at, tiles=taken_tiles(at), placed=_placed_well(sf, voc),
                 layout=layout_of(sf, voc.provinces))
    good = total = 0
    for n in sf.of_kind("resource"):
        xy = read_spec(n).xy()
        out.resources += 1
        if xy is None or voc.cm is None or not voc.in_bounds(*xy):
            continue
        here = voc.province_at(*xy)
        if voc.sea(*xy):
            out.sea.add(n.start)
        else:
            g = voc.ground(*xy)
            if g is not None and g["code"] == "impassable_land":
                out.rough.add(n.start)
            if not here:
                out.lost.add(n.start)
        head = out.layout.under.get(n.start, "")
        if head:
            total += 1
            good += here.lower() == head.lower()
    out.headed = (good, total)
    return out


#: the findings about the tile itself, which the snap answers
SNAPPED = ("obj.sea", "obj.ground", "obj.marker", "obj.shared", "obj.mixed",
           "res.sea", "res.ground", "res.province", "res.duplicate")


def _others(total: int, n: int, what: str, me: Optional[Node],
            mine: set) -> str:
    """``This campaign has 8 others like it, of 1,130.``"""
    if me is not None:
        total -= 1
        n -= me.start in mine
    return (f" This campaign has {'no other' if not n else f'{n:,} other'}"
            f"{'s' if n > 1 else ''} like it, of {total:,} {what}.")


def check_object(voc: Vocabulary, spec: Spec, sf: StratFile,
                 section: str = "", me: Optional[Node] = None,
                 cen: Optional[Census] = None, saving: bool = False) -> List[dict]:
    """Everything wrong with one fort, watchtower or resource, fatal first.

    ``saving`` is a plan's check of the record it is writing. A duplicate
    resource is then said whichever of the two comes first in the file; read
    off the file, only the second of a pair is, as the validator says it, so
    DaC's 63 are 63 findings and not 126.

    ``section`` is where it is filed: a fort's region section, a resource's
    province heading. ``cen`` may be passed in already counted. A finding
    about the tile ends on D10's nearest tile that would do, and carries it as
    ``near``.
    """
    out: List[dict] = []
    what = spec.kind
    if spec.kind not in KINDS:
        return [finding("obj.kind", True, f"{spec.kind!r} is not one of "
                        + ", ".join(KINDS) + ".")]
    cen = cen if cen is not None else census(sf, voc)
    if spec.kind == "resource":
        out += _name_findings(voc, spec)
    for slot in ("x", "y"):
        v = getattr(spec, slot)
        if not is_int(v):
            out.append(finding(f"obj.{slot}", True,
                               f"{slot} is {v if v not in (None, '') else '(nothing)'}"
                               f", which is not a whole number."))
    xy = spec.xy()
    if xy is not None and voc.cm is not None:
        gx, gy = xy
        if not voc.in_bounds(gx, gy):
            out.append(finding(
                "obj.offmap", True,
                f"{gx},{gy} is off the {voc.cm.terrain.width}x"
                f"{voc.cm.terrain.height} tile grid, so there is nowhere for "
                f"this {what} to stand.", x=gx, y=gy))
            _snap(voc, spec, sf, me, cen, "", out[-1])
        else:
            tile = (_resource_tile(voc, spec, sf, section, me, gx, gy, cen,
                                   saving)
                    if spec.kind == "resource" else
                    _tile_findings(voc, spec, sf, section, me, gx, gy, cen))
            first = next((f for f in tile if f["code"] in SNAPPED), None)
            if first is not None:
                _snap(voc, spec, sf, me, cen,
                      section or voc.province_at(gx, gy), first)
            out += tile
    if spec.kind == "fort":
        out += _fort_findings(voc, spec, sf)
    out.sort(key=lambda f: not f["fatal"])
    return out


def _snap(voc: Vocabulary, spec: Spec, sf: StratFile, me: Optional[Node],
          cen: Census, home: str, f: dict) -> None:
    """D10: put the nearest tile that would do on ``f``, and say it."""
    taken = cen.tiles
    was = read_spec(me).xy() if me is not None else None
    if was is not None and was in cen.at:
        # the tile it is leaving is free of it, and of nothing else
        taken = dict(taken)
        taken[was] = taken_tiles({was: cen.at[was]}, me)[was]
    x, y = int(str(spec.x)), int(str(spec.y))
    got = voc.snap(spec.kind, x, y, taken, spec.name, home)
    off = f["code"] == "obj.offmap"
    if got is None:
        f["message"] += mapsnap.sentence(None, (x, y))
        return
    at, where = got
    f["near"] = [at[0], at[1]]
    if off:                # how far from a tile that is not there says nothing
        f["message"] += (f" The nearest tile on the map that would do is "
                         f"{at[0]},{at[1]}" + (f", in {where}" if where else "")
                         + ".")
        return
    f["message"] += mapsnap.sentence(
        at, (x, y), where if not home or where.lower() != home.lower() else "")


def _name_findings(voc: Vocabulary, spec: Spec) -> List[dict]:
    from .minorfiles import RESOURCES
    if not spec.name:
        return [finding("res.name", True,
                        "A resource line names the resource first, and this "
                        "one names nothing.")]
    if voc.resources is not None and spec.name not in voc.resources:
        low = [r for r in voc.resources if r.lower() == spec.name.lower()]
        return [finding(
            "res.name", True,
            f"{spec.name} is not a resource {RESOURCES.rel} declares"
            + (f" - it writes {low[0]}" if low else "") + f". The "
            f"{len(voc.resources)} it does are " + ", ".join(voc.resources)
            + ". All 2,813 resource lines on the four campaigns measured name "
            "one of their own mod's.")]
    return []


def _resource_tile(voc: Vocabulary, spec: Spec, sf: StratFile, heading: str,
                   me: Optional[Node], gx: int, gy: int,
                   cen: Census, saving: bool = False) -> List[dict]:
    from . import mapcheck
    out: List[dict] = []
    name = spec.name or "resource"
    here = voc.province_at(gx, gy)
    total = cen.resources
    if heading and here and here.lower() != heading.lower():
        good, t = cen.headed
        if me is not None and me.start in cen.layout.under:
            t -= 1
            good -= voc.province_at(*read_spec(me).xy()).lower() == \
                cen.layout.under[me.start].lower()
        out.append(finding(
            "res.heading", False,
            f"{gx},{gy} is in {here}, and this {name} is listed under the "
            f"{cen.layout.prefix}{heading} heading. {good} of the {t} in this "
            f"campaign stand in the province their heading names.",
            x=gx, y=gy, province=here))
    for f in mapcheck.position_faults(voc.cm, gx, gy):
        if f["code"] == "sea":
            out.append(finding(
                "res.sea", False,
                f"This {name} is {f['tail']} Nothing on land can reach it."
                + _others(total, len(cen.sea), "resources", me, cen.sea),
                x=gx, y=gy))
    if not any(f["code"] == "res.sea" for f in out):
        g = voc.ground(gx, gy)
        if g is not None and g["code"] == "impassable_land":
            out.append(finding(
                "res.ground", False,
                f"{gx},{gy} is {g['name']}, which no army can walk onto."
                + _others(total, len(cen.rough), "resources", me, cen.rough),
                x=gx, y=gy))
        if not here:
            out.append(finding(
                "res.province", False,
                f"{gx},{gy} is in no declared province, so no settlement owns "
                f"this {name} and nobody trades it."
                + _others(total, len(cen.lost), "resources", me, cen.lost),
                x=gx, y=gy))
    twin = next((n for n in cen.at.get((gx, gy), []) if n is not me
                 and n.kind == "resource" and n.name.lower() == name.lower()
                 and (saving or me is None or n.start < me.start)), None)
    if twin is not None:
        out.append(finding(
            "res.duplicate", False,
            mapcheck.duplicate_message(twin.name, gx, gy, twin.start + 1),
            x=gx, y=gy, line=twin.start + 1))
    out += _mixed(sf, me, gx, gy, cen, SECTIONED)
    return out


def _mixed(sf: StratFile, me: Optional[Node], gx: int, gy: int, cen: Census,
           kinds: Tuple[str, ...]) -> List[dict]:
    """A resource on a fort's tile, or a fort on a resource's."""
    o = next((n for n in cen.at.get((gx, gy), []) if n is not me
              and n.kind in kinds), None)
    if o is None:
        return []
    return [finding(
        "obj.mixed", False,
        f"{gx},{gy} already has a {o.name if o.kind == 'resource' else o.kind}"
        f" on it (line {o.start + 1}). None of the {MEASURED_RESOURCES:,} "
        f"resources on the four campaigns measured shares a tile with a fort "
        f"or a watchtower.", x=gx, y=gy, line=o.start + 1)]


def _tile_findings(voc: Vocabulary, spec: Spec, sf: StratFile, section: str,
                   me: Optional[Node], gx: int, gy: int,
                   cen: Census) -> List[dict]:
    out: List[dict] = []
    what = spec.kind
    here = voc.province_at(gx, gy)
    if section and here.lower() != section.lower():
        good, total = cen.placed
        if me is not None and section_of(sf, me) is not None:
            total -= 1               # the record being judged is not its own evidence
        out.append(finding(
            "obj.section", False,
            (f"{gx},{gy} is in {here}" if here else f"{gx},{gy} is in no "
             f"declared province") + f", and this {what} is filed under "
            f"{section}. {good} of the {total} in this campaign stand in the "
            f"province they are filed under.", x=gx, y=gy, province=here))
    if voc.sea(gx, gy) is True:
        out.append(finding(
            "obj.sea", False,
            f"{gx},{gy} is sea. A {what} is built on land: one watchtower of "
            f"the 800 on DaC's two campaigns is on the sea, and no fort.",
            x=gx, y=gy))
    else:
        g = voc.ground(gx, gy)
        if g is not None and g["code"] == "impassable_land":
            out.append(finding(
                "obj.ground", False,
                f"{gx},{gy} is {g['name']}, which no army can walk onto. Four "
                f"of DaC's watchtowers stand on it and no fort does.",
                x=gx, y=gy))
    mark = voc.marker(gx, gy)
    if mark:
        out.append(finding(
            "obj.marker", False,
            f"{gx},{gy} is {mark} pixel. None of the 800 forts and watchtowers "
            f"measured stands on a settlement or a port.", x=gx, y=gy))
    others = [n for n in cen.at.get((gx, gy), []) if n is not me
              and n.kind in SECTIONED]
    if others:
        o = others[0]
        out.append(finding(
            "obj.shared", False,
            f"{gx},{gy} already has a {o.kind} on it (line {o.start + 1}). No "
            f"two of the 800 measured share a tile.", x=gx, y=gy,
            line=o.start + 1))
    out += _mixed(sf, me, gx, gy, cen, ("resource",))
    return out


def _fort_findings(voc: Vocabulary, spec: Spec, sf: StratFile) -> List[dict]:
    out: List[dict] = []
    if bool(spec.type) != bool(spec.culture):
        out.append(finding(
            "fort.half", False,
            "A fort writes both a type and a culture, or neither: DaC's 206 "
            "write both and vanilla's short form writes neither. This one has "
            + ("a type and no culture." if spec.type else
               "a culture and no type.")))
    if spec.culture and voc.cultures is not None \
            and spec.culture not in voc.cultures:
        out.append(finding(
            "fort.culture", True,
            f"{spec.culture} is not a culture {CULTURES_REL} declares. The "
            f"{len(voc.cultures)} are " + ", ".join(voc.cultures) + "."))
    if spec.type and voc.folders is not None \
            and spec.type.lower() not in voc.folders:
        named = sum(n for (t, _), n in voc.pairs.items() if t)
        found = sum(n for (t, _), n in voc.pairs.items()
                    if t and t.lower() in voc.folders)
        out.append(finding(
            "fort.type", False,
            f"There is no {spec.type} folder under any culture's "
            f"settlements/*/{AMBIENT}, which is where the fort's battle map is "
            f"drawn from. {found} of the {named} fort lines in this campaign "
            f"that name a type name one of those folders."))
    return out


# ---------------------------------------------------------------------------
# finding one again


def find_object(sf: StratFile, kind: str, line: int = 0,
                at: Optional[Tuple[int, int]] = None) -> Optional[Node]:
    """The record the panel was looking at.

    ``line`` is 1-based and ``at`` is the tile it had. A record is the one on
    that line when it is still of that kind and on that tile; otherwise the one
    of that kind on that tile anywhere in the file, since no two of the 800
    measured share one. Anything else is somebody else's edit, and the plan
    says so rather than rewriting whatever has moved onto the line.
    """
    if 0 < line <= len(sf.lines):
        n = sf.node_at(line - 1)
        if n is not None and n.kind == kind and n.start == line - 1 \
                and (at is None or read_spec(n).xy() == tuple(at)):
            return n
    if at is None:
        return None
    hits = [n for n in sf.of_kind(kind) if read_spec(n).xy() == tuple(at)]
    return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------------------
# the plan


@dataclass
class ObjPlan:
    """One fort's, watchtower's or resource's save, worked out without
    touching the disk."""

    mod: object = None
    campaign: str = ""
    kind: str = ""
    action: str = "edit"
    #: the section it ends up filed under, or the heading a resource is under
    region: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    text: str = ""
    #: the record's line as it would be written, and the new section or
    #: heading when one is opened for it
    block: str = ""
    line: int = 0
    opened: str = ""
    #: D10: the nearest tile that would do, when a finding is about the tile
    near: Optional[List[int]] = None
    path: Optional[Path] = None

    def summary(self) -> str:
        head = (f"{self.action} {self.kind} in {self.region or '?'} in "
                f"{getattr(self.mod, 'name', '?')}/{self.campaign}")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"kind": self.kind, "action": self.action,
                "campaign": self.campaign, "region": self.region,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "findings": list(self.findings),
                "block": self.block, "line": self.line, "opened": self.opened,
                "near": self.near, "ok": not self.errors and bool(self.text)}


def _bag(sf: StratFile, lay: Layout) -> Counter:
    return Counter((n.kind, sf.lines[n.start], filed_under(sf, n, lay).lower())
                   for n in objects(sf))


def _section_fields(sf: StratFile) -> List[Tuple[str, dict]]:
    return [(n.name.lower(), {k: v for k, v in n.fields.items() if k != "name"})
            for n in sf.of_kind("region")]


def _guard(before: StratFile, after: StratFile, p: ObjPlan,
           was: Tuple, now: Tuple, lays: Tuple[Layout, Layout]) -> List[str]:
    """What the splice did that it was never asked to do.

    The same test 16h and 16i put on themselves: every count but the one this
    save changes, the rosters, the header, every settlement's text, every
    character's, every section's own fields, and the bag of the other forts,
    watchtowers and resources, each with where it is filed - each of those must
    come back exactly as it was.
    """
    out: List[str] = []
    b, a = before.counts(), after.counts()
    step = {"edit": 0, "move": 0, "add": 1, "delete": -1}[p.action]
    section = p.kind in SECTIONED and bool(p.opened)
    for kind in sorted(set(a) | set(b)):
        want = b.get(kind, 0) + (step if kind == p.kind else 0) \
            + (1 if kind == "region" and section else 0)
        if a.get(kind, 0) != want:
            out.append(f"this would leave {a.get(kind, 0)} {kind} record(s) "
                       f"where there should be {want}")
    if out:
        return out
    if before.rosters != after.rosters or before.globals != after.globals:
        out.append("this would change the campaign's rosters or its header")
    if stratedit.blocks_by_region(before) != stratedit.blocks_by_region(after):
        out.append("this would rewrite a settlement block")
    from .stratchar import _char_texts
    if _char_texts(before) != _char_texts(after):
        out.append("this would rewrite a character block")
    secs_b, secs_a = _section_fields(before), _section_fields(after)
    if section:                    # it was not there before, so all of it is new
        secs_a = [s for s in secs_a if s[0] != p.opened.lower()]
    if secs_b != secs_a:
        out.append("this would change a region section's own lines")
    bag_b, bag_a = _bag(before, lays[0]), _bag(after, lays[1])
    if was:
        bag_b[was] -= 1
    if now:
        bag_a[now] -= 1
    if +bag_b != +bag_a:
        out.append("this would rewrite or refile a fort, watchtower or "
                   "resource nobody asked it to")
    return out


def plan(mod, facts, body: dict) -> ObjPlan:
    """Work out the whole new ``descr_strat.txt`` for one save.

    ``body`` is ``{kind, action, line, at, x, y, type, culture, name, region}``.
    ``line`` (1-based) and ``at`` (the tile it had) are the record the panel was
    looking at; ``region`` is the section to file a fort under, or the heading
    to list a resource under, which a new record takes from its tile when it is
    not given and a moved one keeps.
    """
    from .campmap import MapError

    campaign = str(body.get("campaign") or "") or facts.campaign
    action = str(body.get("action") or "edit").lower()
    kind = str(body.get("kind") or "").strip().lower()
    p = ObjPlan(mod=mod, campaign=campaign, kind=kind, action=action)
    if action not in ACTIONS:
        p.errors.append(f"no such action {action!r}. The four are "
                        + ", ".join(ACTIONS))
        return p
    if kind not in KINDS:
        p.errors.append(f"{kind or '(nothing)'} is not one of "
                        + ", ".join(KINDS))
        return p
    try:
        sf = campstrat.read_strat(mod, campaign)
    except (OSError, ValueError, MapError) as exc:
        p.errors.append(str(exc))
        return p
    p.path = sf.path
    voc = Vocabulary(mod, sf, campmap.map_of(facts, campaign))
    lay = voc.layout
    sectioned = kind in SECTIONED
    # a resource is filed under a heading only in a file that heads its groups
    headed = not sectioned and lay.by == "province"

    node, before = None, None
    if action != "add":
        at = body.get("at")
        at = (tuple(int(v) for v in at) if isinstance(at, (list, tuple))
              and len(at) == 2 and all(is_int(v) for v in at) else None)
        node = find_object(sf, kind, int(body.get("line") or 0), at)
        if node is None:
            p.errors.append(
                f"there is no {kind} "
                + (f"at {at[0]},{at[1]} " if at else "")
                + f"in {campaign}'s descr_strat.txt any more. Something else "
                  f"changed the file; read it again")
            return p
        before = read_spec(node)
    spec = spec_from_body(body, before)
    spec.kind = kind
    if action != "delete":
        # a tile that is not a whole number or not on the map has no province,
        # and "no province under it" would be the wrong thing to say
        bad = [f for f in check_object(voc, spec, sf, "", node)
               if f["code"] in ("obj.x", "obj.y", "obj.offmap")]
        if bad:
            p.errors += [f["message"] for f in bad]
            p.near = next((f["near"] for f in bad if f.get("near")), None)
            return p

    was = filed_under(sf, node, lay) if node is not None else ""
    want = str(body.get("region") or "").strip() if (sectioned or headed) else ""
    xy = spec.xy()
    if action == "add" and not want and xy is not None and (sectioned or headed):
        want = voc.province_at(*xy)
    if action == "edit" and want and was and want.lower() != was.lower():
        action = p.action = "move"
    if action == "move" and not want and xy is not None and (sectioned or headed):
        want = voc.province_at(*xy)
    if action == "move" and not (sectioned or headed):
        action = p.action = "edit"            # a resource with nowhere else to go
    if action in ("add", "move"):
        if not want and sectioned:
            p.errors.append(
                f"there is no declared province under "
                f"{spec.x},{spec.y}, so there is no region section to file "
                f"this {kind} under. Pick a tile inside a province")
            return p
        if not want and action == "move":
            action = p.action = "edit"
        elif want and voc.provinces \
                and want.lower() not in {r.lower() for r in voc.provinces} \
                and want.lower() not in sections(sf):
            p.errors.append(f"{want} is not a province this map declares")
            return p
        if action == "move" and was and want.lower() == was.lower():
            action = p.action = "edit"
    p.region = want if action in ("add", "move") else was

    # -- the splice
    lines = list(sf.lines)
    if action == "delete":
        del lines[node.start]
        text_line = ""
    else:
        text_line = (render_line(sf.lines[node.start], before, spec)
                     if node is not None else new_line(spec, shape_of(sf)))
        if action == "edit":
            lines[node.start] = text_line
        else:
            if not sectioned:
                at_, block, p.opened = resource_home(sf, lay, spec.name,
                                                     p.region, text_line)
            else:
                hold = sections(sf).get(p.region.lower())
                if hold:
                    at_ = insert_point(sf, hold[0], kind)
                    block = [text_line]
                else:
                    at_, block = new_section(sf, p.region, text_line)
                    p.opened = p.region
            if node is not None:                    # a move: out, then in
                if at_ > node.start:
                    at_ -= 1
                del lines[node.start]
            lines[at_:at_] = block

    text = serialise(sf, lines)
    done = campstrat.parse_strat(text)
    lay_done = layout_of(done, voc.provinces)
    now_node = None
    if action != "delete":
        now_node = next((n for n in done.of_kind(kind)
                         if done.lines[n.start] == text_line
                         and filed_under(done, n, lay_done).lower()
                         == p.region.lower()), None)
        if now_node is None:
            p.errors.append(f"after this save the new line cannot be found in "
                            f"{p.region or 'the file'}")
            return p
    key = lambda f, n, ly: (n.kind, f.lines[n.start],          # noqa: E731
                            filed_under(f, n, ly).lower())
    p.errors += _guard(sf, done, p,
                       key(sf, node, lay) if node is not None else (),
                       key(done, now_node, lay_done) if now_node is not None else (),
                       (lay, lay_done))
    if p.errors:
        return p

    if now_node is not None:
        p.line = now_node.start + 1
        p.block = done.lines[now_node.start]
        if p.opened and sectioned:
            sec = section_of(done, now_node)
            p.block = "\n".join(done.lines[sec.start:content_end(done, sec) + 1])
        elif p.opened:
            p.block = "\n".join(done.lines[now_node.start - 1:now_node.start + 1])
        p.findings = check_object(voc, spec, done, p.region, now_node,
                                  saving=True)
        p.near = next((f["near"] for f in p.findings if f.get("near")), None)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(p, before, spec, was, lay.prefix)

    p.text = "" if text == sf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _describe(p: ObjPlan, before: Optional[Spec], after: Spec,
              was: str, prefix: str = ";") -> List[str]:
    out: List[str] = []
    res = after.kind == "resource"
    what = (f"{after.kind}" + (f" ({after.type})" if after.type else "")
            if not res else f"{after.name or 'resource'}")
    where = (f" under the {prefix}{p.region} heading" if res and p.region
             else f" in {p.region}" if p.region else "")
    if p.action == "add":
        out.append(f"a new {what} at {after.x},{after.y}{where}")
        if p.opened and res:
            out.append(f"no group of resources has a {prefix}{p.region} heading "
                       f"yet, so one is opened for it")
        elif p.opened:
            out.append(f"{p.region} has no region section yet, so one is opened "
                       f"for it: " + ", ".join(SECTION_FIELDS))
        return out
    if p.action == "delete":
        gone = before.name if res else before.kind
        out.append(f"the {gone} at {before.x},{before.y} is taken out of "
                   + (f"{was}" if was and not res else
                      f"the {prefix}{was} group" if was else "the file"))
        return out
    if (before.x, before.y) != (after.x, after.y):
        out.append(f"tile: {before.x},{before.y} -> {after.x},{after.y}")
    for slot in ("type", "culture", "name"):
        a, b = getattr(before, slot), getattr(after, slot)
        if a != b:
            out.append(f"{slot}: {a or '(none)'} -> {b or '(none)'}")
    if p.action == "move":
        out.append(("listed under: " if res else "filed under: ")
                   + f"{was or '(nothing)'} -> {p.region}")
        if p.opened:
            out.append(f"{p.region} has no " + ("heading" if res else
                                                "region section")
                       + " yet, so one is opened")
    return out


# ---------------------------------------------------------------------------
# the save


def apply(p: ObjPlan) -> dict:
    """Write a planned save: one backup, one Log entry, one Undo.

    ``map.rwm`` is left alone for 16h's reason: it is compiled from the layers
    and ``descr_regions.txt``, and the campaign file is read fresh at every
    campaign start.
    """
    import shutil
    import time

    from . import config
    from .keyblock import write_text
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.mod
    rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.campaign_rel(p.campaign)}/"
           f"{campstrat.STRAT_NAME}")
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [],
                                      "deleted": []}
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
    write_text(target, p.text, campstrat.ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap",
        # a resource is its own entry, so the Log can say which it was
        "action": "resource" if p.kind == "resource" else "fortification",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": f"{p.kind} in {p.region}" if p.region else p.kind,
        "resolved_type": f"{p.kind} in {p.region}" if p.region else p.kind,
        "options": {"campaign": p.campaign, "kind": p.kind, "what": p.action,
                    "region": p.region, "opened": p.opened},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("OBJECT %s %s in %s/%s (%s), id=%s", p.action, p.kind, mod.name,
             p.campaign, p.region, tid)
    return {"id": tid, "kind": p.kind, "region": p.region,
            "campaign": p.campaign, "line": p.line, "record": rec}


# ---------------------------------------------------------------------------
# the panel


def view(facts) -> dict:
    """Every fort, watchtower and resource in the campaign, with what is wrong
    with each.

    Out of the fact table's own parse, which is 16g's rule for a read: the
    file was read once when the table was filled. DaC's imperial campaign is
    1,531 rows, and the panel filters them by province itself.
    """
    from .campmap import MapError

    sf = getattr(facts, "strat", None)
    if sf is None:
        raise MapError(f"{facts.strat_rel} could not be read, so this campaign "
                       f"has nothing to show")
    voc = Vocabulary(facts.mod, sf, campmap.map_of(facts))
    cen = census(sf, voc)
    rows = []
    for n in objects(sf):
        spec = read_spec(n)
        home = filed_under(sf, n, cen.layout)
        xy = spec.xy()
        rows.append({
            "kind": n.kind, "x": spec.x, "y": spec.y,
            "type": spec.type, "culture": spec.culture, "name": spec.name,
            "region": home,
            "province": voc.province_at(*xy) if xy else "",
            "line": n.start + 1, "text": sf.lines[n.start],
            "problems": list(n.problems),
            "findings": check_object(voc, spec, sf, home, n, cen),
        })
    good, total = cen.placed
    return {"campaign": facts.campaign, "file": facts.strat_rel,
            "rows": rows,
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS},
            "sections": len(sf.of_kind("region")),
            "placed_well": [good, total],
            "headed_well": list(cen.headed),
            "own_map": bool(voc.cm is not None
                            and getattr(voc.cm, "home", None) is not None),
            "vocab": voc.payload()}
