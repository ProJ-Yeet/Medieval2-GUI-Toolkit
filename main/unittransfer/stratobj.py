"""``descr_strat.txt``, write: forts and watchtowers.

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

**The map is the base map.** Like 16i's character check, the tile's province
is read off ``world/maps/base``. A campaign that ships its own
``map_regions.tga`` (vanilla's prologue does; nothing installed here does) is
judged against the base one, and that is said rather than hidden.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campstrat, stratedit
from .campstrat import Node, StratFile
from .stratedit import comment_of, finding, indent_of, is_int, serialise

#: The two things this module places. 22b adds the resource.
KINDS = ("fort", "watchtower")

ACTIONS = ("edit", "add", "delete", "move")

#: The lines a new section is opened with, before its first object. Every one of
#: DaC's 241 sections writes both at 0.
SECTION_FIELDS = ("farming_level 0", "famine_threat 0")

CULTURES_REL = "descr_cultures.txt"
#: ``settlements/<culture folder>/ambient_settlements/<fort type>/``
AMBIENT = "ambient_settlements"

_OBJ = re.compile(r"^(?P<word>fort|watchtower)(?P<gap>[\t ]+)(?P<x>-?\d+)"
                  r"(?P<sep>[\t ]+)(?P<y>-?\d+)(?P<rest>.*)$", re.I)


# ---------------------------------------------------------------------------
# one record


@dataclass
class Spec:
    """One fort or watchtower, as the form holds it."""

    kind: str = "fort"
    x: object = None
    y: object = None
    type: str = ""
    culture: str = ""

    def payload(self) -> dict:
        return {"kind": self.kind, "x": self.x, "y": self.y,
                "type": self.type, "culture": self.culture}

    def xy(self) -> Optional[Tuple[int, int]]:
        if is_int(self.x) and is_int(self.y):
            return int(str(self.x)), int(str(self.y))
        return None


def read_spec(node: Node) -> Spec:
    return Spec(kind=node.kind, x=node.get("x"), y=node.get("y"),
                type=str(node.get("type") or ""),
                culture=str(node.get("culture") or ""))


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
    return s


def section_of(sf: StratFile, node: Node) -> Optional[Node]:
    """The ``region`` section a record is written in, or None."""
    parent = sf.nodes[node.parent] if node.parent >= 0 else None
    return parent if parent is not None and parent.kind == "region" else None


def objects(sf: StratFile) -> List[Node]:
    return [n for n in sf.nodes if n.kind in KINDS]


# ---------------------------------------------------------------------------
# the line


@dataclass
class Shape:
    """How this file writes the line, so a new one reads like its neighbours.

    The gap after the keyword is the one thing that varies: DaC writes
    ``fort \\t326 142`` on 145 of its 206 forts and ``watchtower 307 161`` on
    all 594 towers. Nothing is indented.
    """

    indent: str = ""
    gap: Dict[str, str] = field(default_factory=dict)


def shape_of(sf: StratFile) -> Shape:
    out = Shape()
    gaps: Dict[str, Counter] = {k: Counter() for k in KINDS}
    indents: Counter = Counter()
    for n in objects(sf):
        line = sf.lines[n.start]
        m = _OBJ.match(line.lstrip("\t "))
        if m:
            gaps[n.kind][m.group("gap")] += 1
            indents[indent_of(line)] += 1
    out.indent = indents.most_common(1)[0][0] if indents else ""
    for k in KINDS:
        out.gap[k] = gaps[k].most_common(1)[0][0] if gaps[k] else " "
    return out


def _tail(spec: Spec) -> str:
    if spec.kind != "fort" or not (spec.type or spec.culture):
        return ""
    return (f" {spec.type}" if spec.type else "") + \
        (f" culture {spec.culture}" if spec.culture else "")


def new_line(spec: Spec, shape: Shape) -> str:
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


# ---------------------------------------------------------------------------
# the vocabulary and the map


class Vocabulary:
    """What a fort may be called and what it may stand on, measured."""

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

    def payload(self) -> dict:
        return {"cultures": self.cultures, "fort_types": self.fort_types(),
                "have_folders": self.folders is not None,
                "provinces": self.provinces}


# ---------------------------------------------------------------------------
# the checks


def _placed_well(sf: StratFile, voc: Vocabulary) -> Tuple[int, int]:
    """How many of the file's own records stand in the province they are filed
    under, out of how many are filed under one - the number a mismatch warning
    carries, counted on the file being edited rather than quoted from DaC."""
    good = total = 0
    for n in objects(sf):
        sec = section_of(sf, n)
        xy = read_spec(n).xy()
        if sec is None or xy is None:
            continue
        total += 1
        good += voc.province_at(*xy).lower() == sec.name.lower()
    return good, total


def check_object(voc: Vocabulary, spec: Spec, sf: StratFile,
                 section: str = "", me: Optional[Node] = None,
                 tiles: Optional[Counter] = None,
                 placed: Optional[Tuple[int, int]] = None) -> List[dict]:
    """Everything wrong with one fort or watchtower, fatal first.

    ``tiles`` (how many records stand on each tile) and ``placed``
    (:func:`_placed_well`) may be passed in already counted: the panel checks
    all 800 of DaC's at once, and counting both again per record is 800 walks
    of the file.
    """
    out: List[dict] = []
    what = spec.kind
    if spec.kind not in KINDS:
        return [finding("obj.kind", True, f"{spec.kind!r} is not one of "
                        + ", ".join(KINDS) + ".")]
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
        else:
            out += _tile_findings(voc, spec, sf, section, me, gx, gy,
                                  tiles, placed)
    if spec.kind == "fort":
        out += _fort_findings(voc, spec, sf)
    out.sort(key=lambda f: not f["fatal"])
    return out


def _tile_findings(voc: Vocabulary, spec: Spec, sf: StratFile, section: str,
                   me: Optional[Node], gx: int, gy: int,
                   tiles: Optional[Counter] = None,
                   placed: Optional[Tuple[int, int]] = None) -> List[dict]:
    out: List[dict] = []
    what = spec.kind
    here = voc.province_at(gx, gy)
    if section and here.lower() != section.lower():
        good, total = placed or _placed_well(sf, voc)
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
    busy = tiles is None or tiles.get((gx, gy), 0) > (1 if me is not None else 0)
    others = [n for n in objects(sf) if n is not me
              and read_spec(n).xy() == (gx, gy)] if busy else []
    if others:
        o = others[0]
        out.append(finding(
            "obj.shared", False,
            f"{gx},{gy} already has a {o.kind} on it (line {o.start + 1}). No "
            f"two of the 800 measured share a tile.", x=gx, y=gy,
            line=o.start + 1))
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
    """One fort's or watchtower's save, worked out without touching the disk."""

    mod: object = None
    campaign: str = ""
    kind: str = ""
    action: str = "edit"
    #: the section it ends up filed under
    region: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    findings: List[dict] = field(default_factory=list)
    text: str = ""
    #: the record's line as it would be written, and the new section when one
    #: is opened for it
    block: str = ""
    line: int = 0
    opened: str = ""
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
                "ok": not self.errors and bool(self.text)}


def _bag(sf: StratFile) -> Counter:
    return Counter((n.kind, sf.lines[n.start],
                    (section_of(sf, n).name.lower() if section_of(sf, n) else ""))
                   for n in objects(sf))


def _section_fields(sf: StratFile) -> List[Tuple[str, dict]]:
    return [(n.name.lower(), {k: v for k, v in n.fields.items() if k != "name"})
            for n in sf.of_kind("region")]


def _guard(before: StratFile, after: StratFile, p: ObjPlan,
           was: Tuple, now: Tuple) -> List[str]:
    """What the splice did that it was never asked to do.

    The same test 16h and 16i put on themselves: every count but the one this
    save changes, the rosters, the header, every settlement's text, every
    character's, every section's own fields, and the bag of the other forts and
    watchtowers - each of those must come back exactly as it was.
    """
    out: List[str] = []
    b, a = before.counts(), after.counts()
    step = {"edit": 0, "move": 0, "add": 1, "delete": -1}[p.action]
    for kind in sorted(set(a) | set(b)):
        want = b.get(kind, 0) + (step if kind == p.kind else 0) \
            + (1 if kind == "region" and p.opened else 0)
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
    if p.opened:                   # it was not there before, so all of it is new
        secs_a = [s for s in secs_a if s[0] != p.opened.lower()]
    if secs_b != secs_a:
        out.append("this would change a region section's own lines")
    bag_b, bag_a = _bag(before), _bag(after)
    if was:
        bag_b[was] -= 1
    if now:
        bag_a[now] -= 1
    if +bag_b != +bag_a:
        out.append("this would rewrite a fort or watchtower nobody asked it to")
    return out


def plan(mod, facts, body: dict) -> ObjPlan:
    """Work out the whole new ``descr_strat.txt`` for one save.

    ``body`` is ``{kind, action, line, at, x, y, type, culture, region}``.
    ``line`` (1-based) and ``at`` (the tile it had) are the record the panel was
    looking at; ``region`` is the section to file it under, which a new record
    takes from its tile when it is not given and a moved one keeps.
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
    voc = Vocabulary(mod, sf, getattr(facts, "cm", None))

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
            return p

    was_sec = section_of(sf, node) if node is not None else None
    want = str(body.get("region") or "").strip()
    xy = spec.xy()
    if action == "add" and not want and xy is not None:
        want = voc.province_at(*xy)
    if action == "edit" and want and was_sec is not None \
            and want.lower() != was_sec.name.lower():
        action = p.action = "move"
    if action == "move" and not want and xy is not None:
        want = voc.province_at(*xy)
    if action in ("add", "move"):
        if not want:
            p.errors.append(
                f"there is no declared province under "
                f"{spec.x},{spec.y}, so there is no region section to file "
                f"this {kind} under. Pick a tile inside a province")
            return p
        if voc.provinces and want.lower() not in {r.lower() for r in voc.provinces} \
                and want.lower() not in sections(sf):
            p.errors.append(f"{want} is not a province this map declares")
            return p
        if action == "move" and was_sec is not None \
                and want.lower() == was_sec.name.lower():
            action = p.action = "edit"
    p.region = (want if action in ("add", "move")
                else (was_sec.name if was_sec is not None else ""))

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
    now_node = None
    if action != "delete":
        now_node = next((n for n in done.of_kind(kind)
                         if done.lines[n.start] == text_line
                         and (section_of(done, n).name.lower()
                              if section_of(done, n) else "") == p.region.lower()),
                        None)
        if now_node is None:
            p.errors.append(f"after this save the new line cannot be found in "
                            f"{p.region or 'the file'}")
            return p
    key = lambda f, n: (n.kind, f.lines[n.start],          # noqa: E731
                        section_of(f, n).name.lower() if section_of(f, n) else "")
    p.errors += _guard(sf, done, p,
                       key(sf, node) if node is not None else (),
                       key(done, now_node) if now_node is not None else ())
    if p.errors:
        return p

    if now_node is not None:
        p.line = now_node.start + 1
        p.block = done.lines[now_node.start]
        if p.opened:
            sec = section_of(done, now_node)
            p.block = "\n".join(done.lines[sec.start:content_end(done, sec) + 1])
        p.findings = check_object(voc, spec, done, p.region, now_node)
    p.errors += [f["message"] for f in p.findings if f["fatal"]]
    p.warnings += [f["message"] for f in p.findings if not f["fatal"]]
    p.changes = _describe(p, before, spec, was_sec)

    p.text = "" if text == sf.serialise() else text
    if not p.text and not p.errors:
        p.errors.append("nothing to change")
    return p


def _describe(p: ObjPlan, before: Optional[Spec], after: Spec,
              was_sec: Optional[Node]) -> List[str]:
    out: List[str] = []
    what = f"{after.kind}" + (f" ({after.type})" if after.type else "")
    if p.action == "add":
        out.append(f"a new {what} at {after.x},{after.y} in {p.region}")
        if p.opened:
            out.append(f"{p.region} has no region section yet, so one is opened "
                       f"for it: " + ", ".join(SECTION_FIELDS))
        return out
    if p.action == "delete":
        out.append(f"the {before.kind} at {before.x},{before.y} is taken out of "
                   f"{was_sec.name if was_sec is not None else 'the file'}")
        return out
    if (before.x, before.y) != (after.x, after.y):
        out.append(f"tile: {before.x},{before.y} -> {after.x},{after.y}")
    for slot in ("type", "culture"):
        a, b = getattr(before, slot), getattr(after, slot)
        if a != b:
            out.append(f"{slot}: {a or '(none)'} -> {b or '(none)'}")
    if p.action == "move":
        out.append(f"filed under: {was_sec.name if was_sec is not None else '(nothing)'}"
                   f" -> {p.region}")
        if p.opened:
            out.append(f"{p.region} has no region section yet, so one is opened")
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
        "action": "fortification",
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
    log.info("FORT   %s %s in %s/%s (%s), id=%s", p.action, p.kind, mod.name,
             p.campaign, p.region, tid)
    return {"id": tid, "kind": p.kind, "region": p.region,
            "campaign": p.campaign, "line": p.line, "record": rec}


# ---------------------------------------------------------------------------
# the panel


def view(facts) -> dict:
    """Every fort and watchtower in the campaign, with what is wrong with each.

    Out of the fact table's own parse, which is 16g's rule for a read: the
    file was read once when the table was filled. 800 rows on DaC is about
    120 KB, and the panel filters them by province itself.
    """
    from .campmap import MapError

    sf = getattr(facts, "strat", None)
    if sf is None:
        raise MapError(f"{facts.strat_rel} could not be read, so this campaign "
                       f"has no forts to show")
    voc = Vocabulary(facts.mod, sf, getattr(facts, "cm", None))
    tiles = Counter(read_spec(n).xy() for n in objects(sf))
    placed = _placed_well(sf, voc)
    rows = []
    for n in objects(sf):
        spec = read_spec(n)
        sec = section_of(sf, n)
        xy = spec.xy()
        rows.append({
            "kind": n.kind, "x": spec.x, "y": spec.y,
            "type": spec.type, "culture": spec.culture,
            "region": sec.name if sec is not None else "",
            "province": voc.province_at(*xy) if xy else "",
            "line": n.start + 1, "text": sf.lines[n.start],
            "problems": list(n.problems),
            "findings": check_object(voc, spec, sf,
                                     sec.name if sec is not None else "", n,
                                     tiles, placed),
        })
    good, total = placed
    return {"campaign": facts.campaign, "file": facts.strat_rel,
            "rows": rows,
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS},
            "sections": len(sf.of_kind("region")),
            "placed_well": [good, total],
            "vocab": voc.payload()}
