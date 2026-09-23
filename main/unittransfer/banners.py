"""``descr_banners_new.xml`` - the banners a unit carries in battle (Phase 65).

Every *add a faction* tutorial names this file, three modules read it (the
EDU's banner pickers from :mod:`vocab`, the absolute-path rule in
:mod:`crashrules`, the faction zip) and nothing edited it, so the faction
audit had a row-shaped hole where it should be. This reads, checks and edits
it, and :mod:`factionclone` now writes a new faction into it.

**The shape.** ``<Settings>`` holds the look of every banner (scale, the
routing and out-of-control colours, the wave). Then three lists of named
banners, which are the three names an EDU unit's ``banner`` lines use:
``<FactionBanners>`` (``banner faction main_spear``), ``<UnitSpecificBanners>``
(``banner unit Hospitaller``) and ``<HolyBanners>`` (``banner holy crusade``).
A faction banner names four meshes and holds a ``<Texture>`` per faction; the
other two hold ``<MeshAndTexture>`` rows, a mesh per faction as well. Last,
``<RoyalBanner>``, one row per faction.

**Read as text, not by an XML library.** DaC's copy is not well-formed: its
``</Banners>`` is on line 391, and after it come thirteen lines of an older,
longer copy of the royal banner that was saved over and never cut off. An XML
parser refuses the file; the game plays it, so it plainly stops at the root's
close. So does this reader - it tokenises tags by hand, keeps every offset,
and edits by splicing attribute values and whole lines, so the file keeps its
tabs, its comments and its line endings.

**Measured on both installed mods before any rule was written.**

* The four ``main_*`` faction banners carry a texture for every faction in
  both rosters. The rule that matters is sharper than "every faction in every
  banner": **a faction that owns a unit carrying banner X has a texture in X**.
  On both mods that is true without one exception (the keyword ``all`` in an
  ownership line is not a faction and is left out), so it is a warning.
* The same rule for the holy banners fails 15 times on DaC - factions that own
  units with ``banner holy crusade`` and have no crusade texture - and DaC
  plays, because a faction that never crusades never raises one. A note, one
  per banner.
* DaC's royal banner leaves out ``scripts``, ``teutonic_order`` and
  ``norway``: a note.
* A texture row for a name that is no faction is a note, one per name, except
  the multiplayer placeholders: the file's own comment names ``Ally0-2`` and
  ``Enemy0-3``, and both mods also carry ``Ally3-5``, ``Enemy4-6`` and a
  ``Rebels`` row in every main banner. None of those is reported.
* Paths: DaC names 62 files it does not ship (the base game packs them), so a
  missing path is not a finding. Two kinds are: ROCSS's
  ``faction_banner_antioch_trans.texture.texture`` (an extension written
  twice) and ``Faction_banner_thospitaller_trans.texture`` beside a
  ``faction_banner_hospitaller_trans.texture`` it plainly meant - a missing
  file one or two letters from a file in the same folder. Neither rule fires
  anywhere else on either mod.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import keyblock as kb

REL = "descr_banners_new.xml"
ENCODING = "latin-1"
ROOT_TAG = "Banners"

#: section -> the EDU `banner` kind that names its banners
SECTIONS = {"FactionBanners": "faction", "UnitSpecificBanners": "unit",
            "HolyBanners": "holy"}
ROW_TAGS = ("Texture", "MeshAndTexture")
PATH_ATTRS = ("MainMesh", "MiniMesh", "GeneralMesh", "BuildingMesh", "Mesh",
              "DiffuseMap", "TranslucencyMap")
#: the placeholders the file's own comment reserves for multiplayer (it names
#: Ally0-2 and Enemy0-3; both installed mods also ship Ally3-5, Enemy4-6 and a
#: `Rebels` row in every main banner)
MULTIPLAYER = re.compile(r"(ally\d+|enemy\d+|rebels)", re.I)
COLOUR_TAGS = ("RoutingColour", "OutOfControlColour", "NauseaColour")

_TAG = re.compile(r"<!--.*?-->|<(/?)([A-Za-z_][\w.-]*)((?:\s+[\w:.-]+\s*=\s*\"[^\"]*\")*)\s*(/?)>",
                  re.S)
_ATTR = re.compile(r"([\w:.-]+)\s*=\s*\"([^\"]*)\"")
_NUM = re.compile(r"-?\d+(\.\d*)?|-?\.\d+")
_BAN = re.compile(r"^[ \t]*banner[ \t]+(faction|unit|holy)[ \t]+([^\s;]+)", re.M | re.I)


class BannerError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _sig(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


@dataclass
class Elem:
    id: int
    tag: str
    start: int                      # offset of `<`
    open_end: int                   # offset after the opening tag's `>`
    line: int                       # 0-based line of `<`
    parent: int = -1
    #: name -> (value, (start, end) of the value inside the quotes)
    attrs: Dict[str, Tuple[str, Tuple[int, int]]] = field(default_factory=dict)
    end: int = -1                   # offset after the element's last `>`
    children: List[int] = field(default_factory=list)

    def get(self, name: str) -> str:
        return self.attrs.get(name, ("", (0, 0)))[0]


@dataclass
class Doc:
    text: str
    elems: List[Elem]
    root_end: int                   # offset after `</Banners>`, or -1
    errors: List[Tuple[int, str]] = field(default_factory=list)   # (line, message)

    def line_of(self, off: int) -> int:
        return self.text.count("\n", 0, off)

    def kids(self, e: Elem, tag: str = "") -> List[Elem]:
        return [self.elems[i] for i in e.children if not tag or self.elems[i].tag == tag]

    def find(self, tag: str, under: Optional[Elem] = None) -> List[Elem]:
        if under is None:
            return [e for e in self.elems if e.tag == tag]
        out, stack = [], list(under.children)
        while stack:
            e = self.elems[stack.pop(0)]
            if e.tag == tag:
                out.append(e)
            stack[0:0] = e.children
        return out

    def trailing(self) -> str:
        return self.text[self.root_end:] if self.root_end >= 0 else ""


def parse(text: str) -> Doc:
    """Every element up to the root's close, with offsets. Never raises: a
    tag closed out of order or a root never closed is an error on the doc."""
    elems: List[Elem] = []
    stack: List[int] = []
    errors: List[Tuple[int, str]] = []
    root_end = -1
    for m in _TAG.finditer(text):
        if m.group(0).startswith("<!--"):
            continue
        close, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3) or "", m.group(4)
        line = text.count("\n", 0, m.start())
        if close:
            if not stack or elems[stack[-1]].tag != tag:
                errors.append((line, f"line {line + 1}: </{tag}> closes nothing open"
                               + (f" (the open one is <{elems[stack[-1]].tag}>)" if stack else "")))
                continue
            elems[stack.pop()].end = m.end()
            if not stack:
                root_end = m.end()
                break
            continue
        e = Elem(len(elems), tag, m.start(), m.end(), line,
                 parent=stack[-1] if stack else -1)
        base = m.start(3)
        for a in _ATTR.finditer(attrs):
            e.attrs[a.group(1)] = (a.group(2), (base + a.start(2), base + a.end(2)))
        if stack:
            elems[stack[-1]].children.append(e.id)
        elif elems:
            errors.append((line, f"line {line + 1}: <{tag}> stands outside <{ROOT_TAG}>"))
        elems.append(e)
        if selfclose:
            e.end = m.end()
        else:
            stack.append(e.id)
    if stack:
        errors.append((elems[stack[0]].line, f"<{elems[stack[-1]].tag}> is never closed"))
    if elems and elems[0].tag != ROOT_TAG:
        errors.append((0, f"the root is <{elems[0].tag}>, not <{ROOT_TAG}>"))
    return Doc(text, elems, root_end, errors)


# ---------------------------------------------------------------------------
# the model the page draws


def banners(doc: Doc) -> List[Dict]:
    """Every named banner in the three lists, and the royal banner, with its
    rows. ``section`` is the list it is in."""
    out: List[Dict] = []
    if not doc.elems:
        return out
    root = doc.elems[0]
    for sec in doc.kids(root):
        if sec.tag in SECTIONS:
            items = doc.kids(sec, "Banner")
        elif sec.tag == "RoyalBanner":
            items = [sec]
        else:
            continue
        for b in items:
            rows = [r for tag in ROW_TAGS for r in doc.find(tag, b)]
            rows.sort(key=lambda r: r.start)
            out.append({"id": b.id, "section": sec.tag, "name": b.get("Name") or sec.tag,
                        "line": b.line + 1,
                        "attrs": {k: v for k, (v, _s) in b.attrs.items()},
                        "rows": [{"id": r.id, "tag": r.tag, "line": r.line + 1,
                                  "faction": r.get("Faction"),
                                  "attrs": {k: v for k, (v, _s) in r.attrs.items()}}
                                 for r in rows]})
    return out


def settings(doc: Doc) -> List[Dict]:
    """Every element under ``<Settings>`` that has attributes: the numbers."""
    if not doc.elems:
        return []
    root = doc.elems[0]
    sec = next(iter(doc.kids(root, "Settings")), None)
    if sec is None:
        return []
    out = []
    stack = list(sec.children)
    while stack:
        e = doc.elems[stack.pop(0)]
        if e.attrs:
            path = []
            cur = e
            while cur.id != sec.id:
                path.append(cur.tag)
                cur = doc.elems[cur.parent]
            out.append({"id": e.id, "tag": e.tag, "path": "/".join(reversed(path)),
                        "line": e.line + 1, "attrs": {k: v for k, (v, _s) in e.attrs.items()}})
        stack[0:0] = e.children
    return out


# ---------------------------------------------------------------------------
# checking


def finding(code: str, severity: str, message: str, key: str, line: int) -> Dict:
    return {"code": code, "severity": severity, "fatal": severity == "fatal",
            "message": message, "key": key, "line": line + 1}


def _roster(mod) -> List[str]:
    from . import factions as fa
    try:
        path = fa.path_for(mod)
        return [fa.slot_of(r.name).lower() for r in fa.parse_file(path).records] \
            if path.is_file() else []
    except Exception:
        return []


def _edu_banners(mod) -> List[Tuple[str, str, str, List[str]]]:
    """``(unit, kind, banner, owners)`` for every ``banner`` line in the EDU."""
    out = []
    try:
        units = mod.edu.units
    except Exception:
        return out
    for u in units:
        for kind, name in _BAN.findall(u.raw or ""):
            out.append((u.type, kind.lower(), name,
                        [o.strip().lower() for o in u.ownership if o.strip()]))
    return out


def _lev(a: str, b: str, cap: int = 3) -> int:
    if abs(len(a) - len(b)) >= cap:
        return cap
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) >= cap:
            return cap
        prev = cur
    return prev[-1]


def _path_file(data: Path, value: str) -> Path:
    rel = value.replace("\\", "/").strip()
    if rel.lower().startswith("data/"):
        rel = rel[5:]
    return data / rel


def _path_findings(doc: Doc, data: Optional[Path]) -> List[Dict]:
    out: List[Dict] = []
    seen = set()
    listing: Dict[Path, List[str]] = {}
    for e in doc.elems:
        for a in PATH_ATTRS:
            v = e.get(a)
            if not v or v.lower() in seen:
                continue
            seen.add(v.lower())
            name = v.replace("\\", "/").rsplit("/", 1)[-1]
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext and name.lower().endswith(f".{ext}.{ext}"):
                out.append(finding("extension", "warn", f"{v} has its extension twice, so "
                                   f"the game looks for a file nobody made", f"path/{v}", e.line))
                continue
            if data is None:
                continue
            p = _path_file(data, v)
            if p.is_file() or not p.parent.is_dir():
                continue
            if p.parent not in listing:
                listing[p.parent] = [f.name for f in p.parent.iterdir() if f.is_file()]
            near = [n for n in listing[p.parent] if _lev(n.lower(), name.lower()) <= 2]
            if near:
                out.append(finding("typo", "warn", f"{v} is not in the mod, and "
                                   f"{near[0]} is, in the same folder - probably what was "
                                   f"meant", f"path/{v}", e.line))
    return out


def check(doc: Doc, roster: List[str], edu: List[Tuple[str, str, str, List[str]]],
          data: Optional[Path] = None) -> List[Dict]:
    out: List[Dict] = []
    for line, msg in doc.errors:
        out.append(finding("xml", "fatal", msg, "file", line))
    tail = doc.trailing()
    if tail.strip():
        at = doc.line_of(doc.root_end)
        n = tail.strip("\r\n").count("\n") + 1
        out.append(finding("trailing", "warn", f"{n} line(s) after </{ROOT_TAG}> (from line "
                           f"{at + 1}) that the game never reads - a copy saved over a longer "
                           f"one; an edit there changes nothing", "file", at))
    bans = banners(doc)
    by_kind: Dict[Tuple[str, str], Dict] = {}
    #: rows for a name that is no faction, gathered so it is one note a name
    stale: Dict[str, List[Tuple[str, int]]] = {}
    for b in bans:
        key = f"banner/{b['id']}"
        seen: Dict[str, int] = {}
        for r in b["rows"]:
            f = r["faction"].lower()
            if not f:
                out.append(finding("faction", "fatal", f"line {r['line']}: a <{r['tag']}> with "
                                   f"no Faction", key, r["line"] - 1))
                continue
            if f in seen:
                out.append(finding("duplicate", "warn", f"{b['name']}: {r['faction']} has two "
                                   f"rows (lines {seen[f]} and {r['line']})", key, r["line"] - 1))
            seen.setdefault(f, r["line"])
            if roster and f not in roster and not MULTIPLAYER.fullmatch(f):
                stale.setdefault(r["faction"], []).append((b["name"], r["line"] - 1))
        b["_have"] = set(seen)
        if b["section"] in SECTIONS:
            by_kind[(SECTIONS[b["section"]], b["name"].lower())] = b
        elif roster:
            gone = [f for f in roster if f not in seen]
            if gone:
                out.append(finding("royal", "note", f"the royal banner has no row for "
                                   f"{', '.join(gone)}", key, b["line"] - 1))
    for name, where in stale.items():
        out.append(finding("stale", "note", f"{name} has {len(where)} row(s) ({', '.join(sorted({w for w, _l in where})[:4])}"
                           f"{'...' if len({w for w, _l in where}) > 4 else ''}) and is not a faction in the roster",
                           f"faction/{name}", where[0][1]))
    holes: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    for unit, kind, name, owners in edu:
        b = by_kind.get((kind, name.lower()))
        if b is None:
            if bans:
                holes.setdefault(("undeclared", kind, name), {}).setdefault("", []).append(unit)
            continue
        for f in owners:
            if f != "all" and f not in b["_have"]:
                holes.setdefault((kind, b["name"], b["id"]), {}).setdefault(f, []).append(unit)
    for key, facs in holes.items():
        if key[0] == "undeclared":
            units = facs[""]
            out.append(finding("undeclared", "warn", f"{len(units)} unit(s) carry `banner {key[1]} "
                               f"{key[2]}` ({', '.join(units[:3])}), and no <{_section_of(key[1])}> "
                               f"banner is called that", f"edu/{key[2]}", 0))
            continue
        kind, name, bid = key
        line = doc.elems[bid].line
        if kind == "holy":
            out.append(finding("holy", "note", f"{name}: {len(facs)} faction(s) own units carrying "
                               f"it and have no row ({', '.join(sorted(facs)[:6])}"
                               f"{'...' if len(facs) > 6 else ''}) - it shows only on a crusade or "
                               f"jihad, which some factions never join", f"banner/{bid}", line))
            continue
        for f, units in sorted(facs.items()):
            out.append(finding("coverage", "warn", f"{name}: {f} owns {len(units)} unit(s) "
                               f"carrying it ({', '.join(units[:3])}) and has no row here, so "
                               f"they have no banner of theirs", f"banner/{bid}", line))
    for s in settings(doc):
        for k, v in s["attrs"].items():
            if not _NUM.fullmatch(v.strip()):
                out.append(finding("number", "fatal", f"{s['path']}: {k}={v!r} is not a number",
                                   f"setting/{s['id']}", s["line"] - 1))
            elif s["tag"] in COLOUR_TAGS and not 0 <= float(v) <= 255:
                out.append(finding("colour", "warn", f"{s['path']}: {k}={v} is outside 0-255",
                                   f"setting/{s['id']}", s["line"] - 1))
    for b in bans:
        for k in ("EffectOffsetX", "EffectOffsetY", "EffectOffsetZ"):
            v = b["attrs"].get(k)
            if v is not None and not _NUM.fullmatch(v.strip()):
                out.append(finding("number", "fatal", f"{b['name']}: {k}={v!r} is not a number",
                                   f"banner/{b['id']}", b["line"] - 1))
        b.pop("_have", None)
    out += _path_findings(doc, data)
    return out


def _section_of(kind: str) -> str:
    return next(s for s, k in SECTIONS.items() if k == kind)


# ---------------------------------------------------------------------------
# reading a mod


def _read(mod) -> str:
    path = Path(mod.data) / REL
    if not path.is_file():
        raise BannerError(f"this mod has no {REL}")
    return kb.read_text(path, ENCODING)


def overview(mod) -> Dict:
    out: Dict = {"file": REL, "banners": [], "settings": [], "findings": [], "roster": []}
    try:
        text = _read(mod)
    except BannerError as e:
        out["error"] = e.message
        return out
    doc = parse(text)
    roster = _roster(mod)
    edu = _edu_banners(mod)
    out["roster"] = roster
    out["banners"] = banners(doc)
    uses: Dict[Tuple[str, str], int] = {}
    for _u, kind, name, _o in edu:
        uses[(kind, name.lower())] = uses.get((kind, name.lower()), 0) + 1
    for b in out["banners"]:
        b["units"] = uses.get((SECTIONS.get(b["section"], ""), b["name"].lower()), 0)
    out["settings"] = settings(doc)
    out["trailing_lines"] = doc.trailing().strip("\r\n").count("\n") + 1 \
        if doc.trailing().strip() else 0
    out["sig"] = _sig(text)
    out["findings"] = check(doc, roster, edu, Path(mod.data))
    return out


def coverage(text: str) -> Dict[str, int]:
    """slot -> how many ``<FactionBanners>`` banners give it a texture. The
    faction audit's row: every faction in both installed mods has all of its
    faction banners, so a slot with none is a gap."""
    doc = parse(text)
    out: Dict[str, int] = {}
    for b in banners(doc):
        if b["section"] != "FactionBanners":
            continue
        for f in {r["faction"].lower() for r in b["rows"] if r["faction"]}:
            out[f] = out.get(f, 0) + 1
    return out


# ---------------------------------------------------------------------------
# editing


def _line_span(text: str, e: Elem) -> Tuple[int, int]:
    """The whole line(s) an element stands on, newline included - or just the
    element when something else shares its line."""
    s = text.rfind("\n", 0, e.start) + 1
    nl = text.find("\n", e.end)
    t = len(text) if nl < 0 else nl + 1
    if text[s:e.start].strip() or text[e.end:t].strip():
        return e.start, e.end
    return s, t


def row_copy(doc: Doc, row: Elem, faction: str,
             paths: Optional[Dict[str, str]] = None) -> str:
    """A row's own line(s) with its Faction, and optionally its paths, changed -
    what is inserted after it."""
    s, t = _line_span(doc.text, row)
    chunk = doc.text[s:t]
    edits = [(row.attrs["Faction"][1], faction)] if "Faction" in row.attrs else []
    for a, v in (paths or {}).items():
        if a in row.attrs:
            edits.append((row.attrs[a][1], v))
    for (vs, ve), v in sorted(edits, reverse=True):
        chunk = chunk[:vs - s] + v + chunk[ve - s:]
    if s == row.start:                       # shares a line: keep it on one
        chunk = " " + chunk
    return chunk


def styled(donor: str, new: str) -> str:
    """The new slot written the way the donor's row writes its faction:
    ``England`` makes ``Rhun``, ``england`` makes ``rhun``."""
    return new[:1].upper() + new[1:] if donor[:1].isupper() else new


def clone_rows(text: str, src: str, new: str, swap=None) -> Tuple[str, int]:
    """Every row naming ``src`` copied under it for ``new`` - the faction
    clone's job for this file. ``swap(path)`` returns the path the copy should
    name instead, or None to keep the donor's."""
    doc = parse(text)
    if doc.root_end < 0 and doc.errors:
        raise ValueError(doc.errors[0][1])
    have = {(doc.elems[r.parent].id if r.parent >= 0 else -1)
            for r in doc.elems if r.tag in ROW_TAGS and r.get("Faction").lower() == new.lower()}
    ins: List[Tuple[int, str]] = []
    for r in doc.elems:
        if r.tag not in ROW_TAGS or r.get("Faction").lower() != src.lower():
            continue
        if r.parent in have:
            continue
        paths = {}
        if swap:
            for a in PATH_ATTRS:
                v = r.get(a)
                w = swap(v) if v else None
                if w and w != v:
                    paths[a] = w
        s, t = _line_span(text, r)
        ins.append((t, row_copy(doc, r, styled(r.get("Faction"), new), paths)))
    for at, chunk in sorted(ins, reverse=True):
        text = text[:at] + chunk + text[at:]
    return text, len(ins)


NUMERIC_ATTRS = ("Scale", "MinSizeDistance", "PastMinDistanceScale", "DebugSizes", "R", "G",
                 "B", "Overbrighten", "BouncingAmplitude", "BoundingFrequency", "Time",
                 "Distance", "WindSpeed", "Amplitude", "Speed", "FrequencyX", "FrequencyY",
                 "Width", "Height", "OffsetX", "OffsetY", "EffectOffsetX", "EffectOffsetY",
                 "EffectOffsetZ")


@dataclass
class BannerPlan:
    mod: object = None
    text: str = ""
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> Dict:
        return {"files": [REL] if self.text else [], "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.text)}


def plan(mod, body: dict) -> BannerPlan:
    """``attrs``: ``{element id: {attribute: value}}``; ``add_rows``:
    ``[{like: row id, faction}]`` (a copy of that row, under it);
    ``remove_rows``: ``[row id]``; ``trim``: cut what follows the root's
    close; ``sig``: the signature the page read the file under."""
    p = BannerPlan(mod=mod)
    try:
        text = _read(mod)
    except BannerError as e:
        p.errors.append(e.message)
        return p
    if str(body.get("sig") or "") != _sig(text):
        p.errors.append(f"{REL} changed on disk after it was opened here - reload it")
        return p
    doc = parse(text)
    if doc.root_end < 0:
        p.errors.append(f"{REL} does not close its <{ROOT_TAG}>, so nothing here can be sure "
                        "where an edit lands - fix it in Raw text first")
        return p
    roster = _roster(mod)
    by = {e.id: e for e in doc.elems}
    splices: List[Tuple[int, int, str]] = []
    for key, vals in (body.get("attrs") or {}).items():
        e = by.get(int(key))
        if e is None:
            p.errors.append(f"element {key} is not in the file")
            continue
        for a, v in vals.items():
            v = str(v).strip()
            if a not in e.attrs:
                p.errors.append(f"<{e.tag}> on line {e.line + 1} has no {a}")
                continue
            if re.search(r"[\"<>&]", v):
                p.errors.append(f"{a}: quotes, <, > and & cannot go in a value")
                continue
            if a in NUMERIC_ATTRS and not _NUM.fullmatch(v):
                p.errors.append(f"{e.tag} {a} is a number, not {v!r}")
                continue
            if a == "Faction" and not v:
                p.errors.append("a row's Faction cannot be blank")
                continue
            cur, span = e.attrs[a]
            if v != cur:
                splices.append((span[0], span[1], v))
                p.changes.append(f"{e.get('Name') or e.get('Faction') or e.tag} "
                                 f"(line {e.line + 1}): {a} {cur} -> {v}")
    for spec in body.get("add_rows") or []:
        r = by.get(int(spec.get("like", -1)))
        fac = str(spec.get("faction") or "").strip()
        if r is None or r.tag not in ROW_TAGS:
            p.errors.append("a new row is copied from a row of the same banner")
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", fac):
            p.errors.append(f"{fac!r} is not a faction slot")
            continue
        sibs = [x for x in doc.elems if x.parent == r.parent and x.tag in ROW_TAGS]
        if any(x.get("Faction").lower() == fac.lower() for x in sibs):
            p.errors.append(f"that banner already has a row for {fac}")
            continue
        if roster and fac.lower() not in roster and not MULTIPLAYER.fullmatch(fac):
            p.warnings.append(f"{fac} is not a faction in the roster")
        _s, t = _line_span(text, r)
        splices.append((t, t, row_copy(doc, r, fac)))
        p.changes.append(f"+ {fac}, a row copied from {r.get('Faction')} (line {r.line + 1})")
    for key in body.get("remove_rows") or []:
        r = by.get(int(key))
        if r is None or r.tag not in ROW_TAGS:
            p.errors.append(f"element {key} is not a texture row")
            continue
        s, t = _line_span(text, r)
        splices.append((s, t, ""))
        p.changes.append(f"- {r.get('Faction')}'s row (line {r.line + 1})")
    if body.get("trim"):
        tail = doc.trailing()
        if tail.strip():
            nl = "\r\n" if "\r\n" in text else "\n"
            splices.append((doc.root_end, len(text), nl if tail.endswith(("\n",)) else ""))
            p.changes.append(f"- the {tail.strip(chr(13) + chr(10)).count(chr(10)) + 1} line(s) "
                             f"after </{ROOT_TAG}>")
    if p.errors:
        return p
    spans = sorted(splices, key=lambda x: (x[0], x[1]))
    for (a0, a1, _), (b0, b1, _) in zip(spans, spans[1:]):
        if b0 < a1:
            p.errors.append("two edits touch the same place - save one, then the other")
            return p
    new = text
    for s, t, v in sorted(splices, key=lambda x: (x[0], x[1]), reverse=True):
        new = new[:s] + v + new[t:]
    if new == text:
        p.errors.append("nothing to change")
        return p
    p.text = new
    edu, data = _edu_banners(mod), Path(mod.data)
    was = {f["message"] for f in check(doc, roster, edu, data)}
    p.warnings += [f["message"] for f in check(parse(new), roster, edu, data)
                   if f["severity"] != "note" and f["message"] not in was]
    return p


def apply(p: BannerPlan) -> Dict:
    from . import config
    from .logutil import file_op, log
    if p.errors or not p.text:
        raise ValueError("cannot apply: " + ("; ".join(p.errors) or "nothing to change"))
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    target = Path(mod.data) / REL
    bpath = backup_root / "data" / REL
    bpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, bpath)
    file_op("BACKUP", target, f"-> {bpath}")
    kb.write_text(target, p.text, ENCODING)
    file_op("WRITE", target, f"{len(p.text)} bytes")
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "banners", "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": REL, "resolved_type": REL,
        "options": {}, "applied": True, "undone": False, "note": "",
        "summary": "\n".join(p.changes), "warnings": list(p.warnings),
        "manifest": {"backed_up": [REL], "created": []}, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("BANNER %d change(s) in %s, id=%s", len(p.changes), mod.name, tid)
    return {"id": tid, "record": rec}
