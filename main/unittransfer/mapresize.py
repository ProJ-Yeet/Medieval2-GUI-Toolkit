"""Phase 26a, G6. Resizing a campaign map, and moving everything that stands on it.

Geomod's manual describes this in one line - "add surface area and
automatically write the new coordinates into ``descr_strat.txt``" - and warns in
the next that shrinking needs the area emptied by hand first. Both halves are
here, and the second is a plan rather than a warning: a shrink that would push
anything off the map is refused, and the refusal names every one of them.

**A resize is four margins.** ``north``, ``south``, ``west`` and ``east``, each
a number of tiles, positive to add and negative to take away. The layers are
padded or cropped by that many tiles on each side - a pixel on a ``tile``
layer, two on a ``2W+1`` or ``2W`` one - so the corner lines of the ``2W+1``
layers stay where the tiles they belong to are, and a painted coastline does
not move by half a tile.

**Added ground is open sea.** Each layer is filled with the colour it most
often has on the tiles the engine already reads as sea: the sea's own region
colour, its depth, its ground type, its climate, its fog. That is measured per
map rather than taken from the tutorial's table, because a mod that paints its
ocean ``sea_deep`` wants ``sea_deep`` at the new edge and not the tutorial's
shallow red. Land is then painted with the brush or the Real world tab.

**What moves, and by how much.** A coordinate in the game's files counts ``y``
from the bottom, so land added to the **west** or the **south** moves every
coordinate, and land added to the north or the east moves none. What is moved:

* ``descr_strat.txt`` - resources, forts, watchtowers, and every character's
  ``x``/``y``;
* ``descr_events.txt`` and ``descr_disasters.txt`` - every ``position`` line;
* ``custom_tiles_db.txt`` - the tile column of every row;
* ``campaign_script.txt`` and ``custom_script.txt`` - every ``x N, y N`` pair
  and the tile of the fifteen commands and one condition the engine documents
  as taking a strategy-map position (:data:`SCRIPT_TILE`);
* every custom and historic battle's ``battle x, y`` and its characters.

The script is a grammar nothing here parses, and it is edited anyway, because
a campaign whose map moved and whose script did not is a campaign whose script
is wrong everywhere. The rule is narrow on purpose: only those sixteen words,
and only whole integers in their argument lists. A line the rule does not
recognise is left exactly as it was.

**Which campaigns move with the map.** The base map is read by every campaign
that does not ship its own ``descr_terrain.txt``; all of them move, and any
layer one of them ships its own copy of is resized with the base's. A campaign
that ships its own ``descr_terrain.txt`` is a separate map - Reforged's
``world_a`` - and is resized on its own, from its own folder. Battles stand on
the base map and move only with it.

**What it does not touch.** ``map_FE.tga``, the radar maps and ``disasters.tga``
are pictures with their own sizes, not layers, and are listed. ``map.rwm`` is
deleted as every other map save deletes it.
"""
from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image

from . import campmap, campstrat
from .campmap import (BASE_REL, LAYERS, RWM_REL, TERRAIN_REL, MapError,
                      parse_terrain)
from .maptga import encode, read

ENCODING = campmap.ENCODING

#: The four margins, in the order the panel and the plan say them.
SIDES = ("north", "south", "west", "east")

#: The layers a resize pads, by size rule. ``map_FE.tga`` is a picture with a
#: size of its own; ``water_surface.tga`` is resized only when it is the size of
#: the heights, which it is on Divide and Conquer and is not on Reforged (256).
_SCALE = {"tile": 1, "centre": 2, "double": 2}

#: Where a size rule's pixel for tile ``(x, y)`` is: the engine's own sample
#: point, which is also :func:`campaint.block`'s.
_SAMPLE = {"tile": lambda x, y: (x, y), "centre": lambda x, y: (2 * x + 1, 2 * y + 1),
           "double": lambda x, y: (2 * x, 2 * y)}

#: What a layer is filled with when the map has no sea to measure: the
#: tutorial's own colours ("Creating a World - Basic mapping from scratch").
_FALLBACK = {"regions": (41, 140, 233), "heights": (0, 0, 253),
             "ground_types": (196, 0, 0), "climates": (0, 114, 188),
             "features": (0, 0, 0), "fog": (255, 255, 255),
             "trade_routes": (0, 0, 0), "roughness": (0, 0, 0),
             "water_surface": (0, 0, 253)}

#: The biggest map the stock engine loads, a side; M2EX lifts it.
VANILLA_MAX = 510

#: Script commands whose arguments end in one strategy-map tile, from the
#: engine's own command documentation: ``(word, which)`` where ``which`` is
#: "last" (the final two integers) or "first" (the first two).
SCRIPT_TILE: Dict[str, str] = {
    "move_strat_camera": "last", "snap_strat_camera": "last",
    "zoom_strat_camera": "last", "point_at_strat_position": "last",
    "settlement_flash_start": "last", "settlement_flash_stop": "last",
    "reveal_tile": "last", "reposition_character": "last", "move": "last",
    "camera_look_at_position": "last", "point_at_location": "last",
    "position": "last", "i_charactertypeneartile": "last",
    "reveal_radius": "first",
}
#: ``reveal_area x1, y1, x2, y2`` - two opposite corners.
_SCRIPT_TWO = {"reveal_area"}
#: the words a condition line may open on before its condition
_LEAD = {"if", "and", "or", "not", "while", "else"}

_INT = re.compile(r"(?<![\w.])-?\d+(?![\w.])")
_XY = re.compile(r"\bx\s+(-?\d+)\s*,\s*y\s+(-?\d+)", re.I)
_RESOURCE = re.compile(r"^\s*resource\s+[\w-]+\s*,\s*(-?\d+)\s*,\s*(-?\d+)", re.I)
_FORT = re.compile(r"^\s*(?:fort|watchtower)\s+(-?\d+)\s+(-?\d+)", re.I)
_POSITION = re.compile(r"^\s*position\s+(-?\d+)\s*,?\s*(-?\d+)", re.I)
_BATTLE = re.compile(r"^\s*battle\s+(-?\d+)\s*,\s*(-?\d+)", re.I)
_TILE_ROW = re.compile(r"^\s*\S+\s+(-?\d+)\s+(-?\d+)")

Span = Tuple[int, int]

#: A line that matches none of these carries no tile, whatever its kind, and is
#: passed over without the rules being asked - most of a campaign script.
_WORDS = "|".join(sorted(set(SCRIPT_TILE) | _SCRIPT_TWO | {"console_command"}))
_TRIGGER = {
    "strat": re.compile(r"\bx\s+-?\d|^\s*(?:resource|fort|watchtower)\b", re.I),
    "events": re.compile(r"\bx\s+-?\d|^\s*position\b", re.I),
    "battle": re.compile(r"\bx\s+-?\d|^\s*battle\s+-?\d", re.I),
    "tiles": re.compile(r"^\s*[^;\s]+\s+-?\d"),
    "script": re.compile(r"\bx\s+-?\d|^\s*(?:(?:if|and|or|not|while|else)\s+)*"
                         rf"(?:{_WORDS})\b", re.I),
}


class ResizeError(ValueError):
    """The margins or the map will not do."""


# ---------------------------------------------------------------------------
# the plan


@dataclass
class ResizePlan:
    """One resize, worked out without writing anything."""

    mod: object = None
    campaign: str = ""
    home: str = BASE_REL
    margins: Dict[str, int] = field(default_factory=dict)
    old: Tuple[int, int] = (0, 0)
    new: Tuple[int, int] = (0, 0)
    campaigns: List[str] = field(default_factory=list)
    #: data-relative path -> the whole file as it would go to disk
    data: Dict[str, bytes] = field(default_factory=dict)
    #: file -> how many coordinates moved in it
    moved: Dict[str, int] = field(default_factory=dict)
    left: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: what a shrink would push off the map, file -> ``[(line, text)]``
    off: Dict[str, List[Tuple[int, str]]] = field(default_factory=dict)

    @property
    def shift(self) -> Tuple[int, int]:
        """How far a game coordinate moves: west and south, the two that count."""
        return self.margins.get("west", 0), self.margins.get("south", 0)

    def summary(self) -> str:
        head = (f"resize {getattr(self.mod, 'name', '?')}'s map in {self.home} "
                f"from {self.old[0]}x{self.old[1]} to {self.new[0]}x{self.new[1]}")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"campaign": self.campaign, "home": self.home,
                "margins": dict(self.margins), "old": list(self.old),
                "new": list(self.new), "campaigns": list(self.campaigns),
                "shift": list(self.shift), "files": sorted(self.data),
                "moved": dict(self.moved), "left": list(self.left),
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "off": {k: [list(t) for t in v[:20]] for k, v in self.off.items()},
                "off_total": sum(len(v) for v in self.off.values()),
                "ok": not self.errors and bool(self.data)}


def _margins(body: dict) -> Dict[str, int]:
    out = {}
    for side in SIDES:
        try:
            out[side] = int(body.get(side) or 0)
        except (TypeError, ValueError):
            raise ResizeError(f"the {side} margin has to be a whole number of "
                              f"tiles, not {body.get(side)!r}")
    return out


def members(mod, campaign: str = "") -> Tuple[Path, List[str]]:
    """The folder whose map is resized, and every campaign that reads it.

    ``campaign`` empty, or one that reads the base map, means the base map and
    every campaign without a ``descr_terrain.txt`` of its own. A campaign with
    its own is its own map and moves alone.
    """
    base = Path(mod.data) / BASE_REL
    terrain = Path(TERRAIN_REL).name
    every = campstrat.campaign_paths(mod)
    if campaign:
        home = campmap.campaign_home(mod, campaign)
        if (home / terrain).is_file():
            return home, [campaign]
    return base, [c for c in every
                  if not (campmap.campaign_home(mod, c) / terrain).is_file()]


def plan(mod, body: dict) -> ResizePlan:
    """Work out one resize. ``body`` is ``{campaign, north, south, west, east}``."""
    p = ResizePlan(mod=mod, campaign=str(body.get("campaign") or "").strip())
    try:
        p.margins = _margins(body)
    except ResizeError as exc:
        p.errors.append(str(exc))
        return p
    if not any(p.margins.values()):
        p.errors.append("every margin is 0, so there is nothing to resize")
        return p
    data = Path(mod.data)
    home, p.campaigns = members(mod, p.campaign)
    p.home = home.relative_to(data).as_posix()
    tpath = home / Path(TERRAIN_REL).name
    if not tpath.is_file():
        p.errors.append(f"{p.home} has no descr_terrain.txt, so there is no map "
                        f"size to change")
        return p
    ttext = tpath.read_bytes().decode(ENCODING)
    try:
        terr = parse_terrain(ttext)
    except MapError as exc:
        p.errors.append(str(exc))
        return p
    W, H = terr.width, terr.height
    m = p.margins
    nW, nH = W + m["west"] + m["east"], H + m["north"] + m["south"]
    p.old, p.new = (W, H), (nW, nH)
    if nW < 1 or nH < 1:
        p.errors.append(f"those margins leave a map {nW}x{nH}, which is no map")
        return p
    if max(nW, nH) > VANILLA_MAX and not getattr(mod, "m2ex", False):
        p.warnings.append(
            f"{nW}x{nH} is over the stock engine's {VANILLA_MAX} a side. It "
            f"loads on M2EX; mark the mod as M2EX on its Home card if it runs "
            f"on it.")

    cm = _map_for(mod, p)
    if cm is None:
        return p
    _plan_layers(p, cm, home)
    if p.errors:
        return p
    _plan_shrink(p, cm)
    _plan_terrain(p, tpath, ttext)
    _plan_coordinates(p)
    _plan_numbering(p, cm)
    for pic in ("radar_map1.tga", "radar_map2.tga", "map_FE.tga"):
        for c in p.campaigns:
            if (campmap.campaign_home(mod, c) / pic).is_file():
                p.left.append(f"{campmap.campaign_home(mod, c).relative_to(data).as_posix()}/{pic}")
    if p.left:
        p.warnings.append(
            f"{len(p.left)} picture(s) of the map - the radar maps and the "
            f"menu map - keep their own size and still show the old outline. "
            f"The game loads them as they are.")
    if p.off:
        n = sum(len(v) for v in p.off.values())
        p.errors.append(
            f"{n} thing(s) stand on the ground this would take away. Move or "
            f"delete them first - the list names the file and line of each - "
            f"and the resize will go through.")
    return p


def _map_for(mod, p: ResizePlan) -> Optional["campmap.CampaignMap"]:
    try:
        if p.home == BASE_REL:
            return campmap.CampaignMap(mod)
        return campmap.CampaignMap(mod, Path(mod.data) / p.home)
    except MapError as exc:
        p.errors.append(str(exc))
        return None


# ---------------------------------------------------------------------------
# the layers


def _layer_files(p: ResizePlan, home: Path) -> List[Tuple[dict, Path]]:
    """Every layer file this resize writes: the home's, and each member's own."""
    out: List[Tuple[dict, Path]] = []
    seen = set()
    homes = [home] + [campmap.campaign_home(p.mod, c) for c in p.campaigns]
    for h in homes:
        for ly in LAYERS:
            path = h / ly["file"]
            if ly["code"] == "fe" or not path.is_file():
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((ly, path))
    return out


def fill_colour(cm, code: str, img: Image.Image, rule: str) -> tuple:
    """The value a layer most often has on the tiles the engine reads as sea."""
    try:
        sea = cm.sea
    except MapError:
        sea = b""
    W, H = cm.terrain.width, cm.terrain.height
    px = img.load()
    at = _SAMPLE[rule]
    got: Counter = Counter()
    if sea:
        step = max(1, (W * H) // 60000)             # a sample, not every tile
        for i in range(0, W * H, step):
            if sea[i]:
                x, y = at(i % W, i // W)
                if x < img.width and y < img.height:
                    got[px[x, y]] += 1
    if got:
        return got.most_common(1)[0][0]
    rgb = _FALLBACK.get(code, (0, 0, 0))
    return rgb + (255,) * (len(img.getbands()) - 3)


def resized(img: Image.Image, margins: Dict[str, int], k: int,
            fill: tuple) -> Image.Image:
    """``img`` padded or cropped by ``k`` pixels per tile on each side."""
    w = img.width + k * (margins["west"] + margins["east"])
    h = img.height + k * (margins["north"] + margins["south"])
    out = Image.new(img.mode, (w, h), fill)
    out.paste(img, (k * margins["west"], k * margins["north"]))
    return out


def _plan_layers(p: ResizePlan, cm, home: Path) -> None:
    W, H = p.old
    data = Path(p.mod.data)
    for ly, path in _layer_files(p, home):
        rule = ly["size"]
        rel = path.relative_to(data).as_posix()
        try:
            img, info = read(path)
        except Exception as exc:                           # noqa: BLE001
            p.errors.append(f"{rel} could not be read: {exc}")
            continue
        if rule == "advisory":
            if img.size != (2 * W + 1, 2 * H + 1):
                p.left.append(rel)
                continue
            rule = "centre"
        if rule not in _SCALE:
            continue
        want = {"tile": (W, H), "centre": (2 * W + 1, 2 * H + 1),
                "double": (2 * W, 2 * H)}[rule]
        if img.size != want:
            p.errors.append(f"{rel} is {img.size[0]}x{img.size[1]} and a "
                            f"{W}x{H} map needs it {want[0]}x{want[1]}; fix "
                            f"its size before resizing")
            continue
        img = img.convert(info.mode) if img.mode != info.mode else img
        fill = fill_colour(cm, ly["code"], img, rule)
        out = resized(img, p.margins, _SCALE[rule], fill)
        new_info = replace(info, width=out.width, height=out.height)
        p.data[rel] = encode(out, new_info)
        p.changes.append(f"{rel}: {img.width}x{img.height} -> "
                         f"{out.width}x{out.height}, new ground filled "
                         f"{tuple(fill[:3])}")


def _plan_shrink(p: ResizePlan, cm) -> None:
    """Settlements, ports and provinces on the ground a shrink takes away."""
    m = p.margins
    if min(m.values()) >= 0:
        return
    W, H = p.old
    x0, x1 = max(0, -m["west"]), W - max(0, -m["east"])
    y0, y1 = max(0, -m["north"]), H - max(0, -m["south"])

    def gone(x: int, y: int) -> bool:
        return not (x0 <= x < x1 and y0 <= y < y1)

    try:
        idx = cm.index
        sea = cm.sea
    except MapError as exc:
        p.errors.append(str(exc))
        return
    rel = f"{p.home}/map_regions.tga"
    owner = {}
    for r in idx.regions:
        for at in (r.settlement, r.port):
            if at:
                owner[at] = r.name
    for kind, pts in (("settlement", idx.settlements), ("port", idx.ports)):
        for x, y in pts:
            if gone(x, y):
                who = owner.get((x, y))
                p.off.setdefault(rel, []).append(
                    (0, f"the {kind} pixel at {x},{y} (image)"
                        + (f" of {who}" if who else "")))
    lost: Counter = Counter()
    total: Counter = Counter()
    labels = idx.labels
    for i, lab in enumerate(labels):
        if sea[i]:
            continue
        total[lab] += 1
        if gone(i % W, i // W):
            lost[lab] += 1
    names = []
    for lab, n in lost.most_common():
        reg = idx.by_key.get(campmap.key(idx.colours[lab]))
        if reg is None or not reg.name:
            continue
        if n == total[lab]:
            p.off.setdefault(rel, []).append(
                (0, f"all {n} land tile(s) of {reg.name}"))
        else:
            names.append(f"{reg.name} ({n} of {total[lab]})")
    if names:
        p.warnings.append(f"{len(names)} province(s) lose land at the edge: "
                          + ", ".join(names[:8]) + ("…" if len(names) > 8 else ""))


def _plan_terrain(p: ResizePlan, tpath: Path, text: str) -> None:
    """``descr_terrain.txt``'s two numbers, and nothing else in it."""
    nW, nH = p.new
    out = text
    for word, value in (("width", nW), ("height", nH)):
        out, n = re.subn(rf"(\b{word}\s+)\d+", lambda mm, v=value: f"{mm.group(1)}{v}",
                         out, count=1)
        if not n:
            p.errors.append(f"{tpath.name} has no {word} line to change")
            return
    rel = tpath.relative_to(Path(p.mod.data)).as_posix()
    p.data[rel] = out.encode(ENCODING)
    p.changes.append(f"{rel}: dimensions {p.old[0]}x{p.old[1]} -> {nW}x{nH}")


def _plan_numbering(p: ResizePlan, cm) -> None:
    """Whether the engine's region numbers change - a sea band read first can."""
    before = {r.name: r.region_id for r in cm.index.regions if r.name}
    reg_rel = f"{p.home}/map_regions.tga"
    if reg_rel not in p.data:
        return
    try:
        from io import BytesIO
        regions = _decode(BytesIO(p.data[reg_rel]))
        heights = _decode(BytesIO(p.data[f"{p.home}/map_heights.tga"]))
        feats = _decode(BytesIO(p.data[f"{p.home}/map_features.tga"]))
    except Exception:                                      # noqa: BLE001
        return
    centres = heights.transform((p.new[0], p.new[1]), Image.AFFINE,
                                (2, 0, 0, 0, 2, 0), Image.NEAREST)
    sea = campmap.sea_mask(centres.convert("RGB"), feats.convert("RGB"))
    try:
        idx = campmap.build_index(regions, sea, cm.regions.records,
                                  cm.label_limit)
    except Exception:                                      # noqa: BLE001
        return
    after = {r.name: r.region_id for r in idx.regions if r.name}
    moved = [n for n in before if before[n] != after.get(n)]
    if moved:
        p.warnings.append(
            f"{len(moved)} region number(s) change, because the engine numbers "
            f"regions in the order a scan from the top-left first meets them. A "
            f"save made before the resize will not match the map.")


def _decode(buf) -> Image.Image:
    """A TGA from bytes, through the same reader the map uses."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tga", delete=False) as fh:
        fh.write(buf.getvalue())
        name = fh.name
    try:
        img, _ = read(Path(name))
        return img.copy()
    finally:
        Path(name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# the coordinates


def _code(line: str) -> Tuple[str, str]:
    i = line.find(";")
    return (line, "") if i < 0 else (line[:i], line[i:])


def _spans(line: str) -> List[Span]:
    """Every tile coordinate on one line, as ``[(x span), (y span), ...]``.

    Generic: the ``x N, y N`` pairs any file writes a character with. The file
    kinds add their own on top of this in :func:`_line_spans`.
    """
    code, _ = _code(line)
    out: List[Span] = []
    for mm in _XY.finditer(code):
        out += [mm.span(1), mm.span(2)]
    return out


def _script_spans(code: str) -> List[Span]:
    """The tile of one of the engine's documented tile-taking commands."""
    words = code.split()
    i = 0
    while i < len(words) and words[i].lower() in _LEAD:
        i += 1
    if i >= len(words):
        return []
    word = words[i].lower()
    start = code.lower().find(words[i].lower())
    rest_at = start + len(words[i])
    if word == "console_command" and i + 1 < len(words) \
            and words[i + 1].lower() == "move_character":
        word, which = "move_character", "last"
    elif word in _SCRIPT_TWO:
        ints = [mm.span() for mm in _INT.finditer(code, rest_at)]
        return ints[:4] if len(ints) >= 4 else []
    else:
        which = SCRIPT_TILE.get(word)
        if which is None:
            return []
    ints = [mm.span() for mm in _INT.finditer(code, rest_at)]
    if len(ints) < 2:
        return []
    return ints[-2:] if which == "last" else ints[:2]


def _line_spans(kind: str, line: str) -> List[Span]:
    if not _TRIGGER[kind].search(line):
        return []
    code, _ = _code(line)
    out = _spans(line)
    if out:
        return out
    rx = {"strat": None, "events": _POSITION, "battle": _BATTLE,
          "tiles": _TILE_ROW}.get(kind)
    if kind == "strat":
        for r in (_RESOURCE, _FORT):
            mm = r.match(code)
            if mm:
                return [mm.span(1), mm.span(2)]
        return []
    if kind == "script":
        return _script_spans(code)
    if rx is not None:
        mm = rx.match(code)
        if mm:
            return [mm.span(1), mm.span(2)]
    return []


def shift_text(text: str, kind: str, dx: int, dy: int, size: Tuple[int, int],
               ) -> Tuple[str, int, List[Tuple[int, str]]]:
    """``text`` with every coordinate its kind carries moved by ``(dx, dy)``.

    Returns the new text, how many pairs moved, and ``(line, text)`` for every
    pair that lands off a map of ``size``. Everything else on every line -
    spacing, commas, comments - is kept exactly.
    """
    nW, nH = size
    out: List[str] = []
    n = 0
    off: List[Tuple[int, str]] = []
    for no, line in enumerate(text.splitlines(keepends=True), 1):
        spans = _line_spans(kind, line)
        if len(spans) < 2 or len(spans) % 2:
            out.append(line)
            continue
        pieces = []
        last = 0
        bad = False
        for j in range(0, len(spans), 2):
            (xs, xe), (ys, ye) = spans[j], spans[j + 1]
            x, y = int(line[xs:xe]) + dx, int(line[ys:ye]) + dy
            if not (0 <= x < nW and 0 <= y < nH):
                bad = True
            pieces += [line[last:xs], str(x), line[xe:ys], str(y)]
            last = ye
            n += 1
        pieces.append(line[last:])
        if bad:
            off.append((no, line.strip()[:100]))
        out.append("".join(pieces))
    return "".join(out), n, off


def coordinate_files(mod, campaigns: Sequence[str], battles: bool
                     ) -> List[Tuple[str, Path]]:
    """``(kind, path)`` for every file a resize moves coordinates in."""
    data = Path(mod.data)
    out: List[Tuple[str, Path]] = []
    for c in campaigns:
        home = campmap.campaign_home(mod, c)
        for name, kind in ((campstrat.STRAT_NAME, "strat"),
                           ("descr_events.txt", "events"),
                           ("custom_tiles_db.txt", "tiles"),
                           ("campaign_script.txt", "script"),
                           ("custom_script.txt", "script")):
            if (home / name).is_file():
                out.append((kind, home / name))
    if battles:
        dis = data / BASE_REL / "descr_disasters.txt"
        if dis.is_file():
            out.append(("events", dis))
        for sub in ("custom", "historic"):
            root = data / "world" / "maps" / "battle" / sub
            if root.is_dir():
                out += [("battle", b) for b in sorted(root.glob("*/descr_battle.txt"))]
    return out


def _plan_coordinates(p: ResizePlan) -> None:
    dx, dy = p.shift
    data = Path(p.mod.data)
    files = coordinate_files(p.mod, p.campaigns, p.home == BASE_REL)
    shrink = min(p.margins.values()) < 0
    for kind, path in files:
        rel = path.relative_to(data).as_posix()
        raw = path.read_bytes()
        text = raw.decode(ENCODING)
        new, n, off = shift_text(text, kind, dx, dy, p.new)
        if off and shrink:
            if kind == "script":
                p.warnings.append(
                    f"{rel}: {len(off)} script line(s) name a tile the smaller "
                    f"map does not have, first line {off[0][0]}: {off[0][1]!r}. "
                    f"They are moved like every other and left for you to read.")
            else:
                p.off[rel] = off
        if not n or (dx, dy) == (0, 0):
            continue
        p.moved[rel] = n
        p.data[rel] = new.encode(ENCODING)
    if (dx, dy) == (0, 0):
        p.changes.append("no coordinate moves: nothing was added or taken away "
                         "on the west or south edge, and the game counts from "
                         "there")
    elif p.moved:
        total = sum(p.moved.values())
        p.changes.append(
            f"{total:,} coordinate(s) moved by ({dx:+d}, {dy:+d}) in "
            f"{len(p.moved)} file(s): "
            + ", ".join(f"{'/'.join(Path(r).parts[-2:])} {n:,}" for r, n in
                        sorted(p.moved.items(), key=lambda kv: -kv[1])[:6]))


# ---------------------------------------------------------------------------
# the save


def apply(p: ResizePlan) -> dict:
    """Write it, with one backup set and one Undo, and drop the compiled maps."""
    import shutil

    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data:
        raise ValueError("nothing to resize")
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

    for rel, blob in sorted(p.data.items()):
        target = keep(rel)
        target.write_bytes(blob)
        file_op("WRITE", target, f"{len(blob)} bytes")
    homes = {p.home} | {campmap.campaign_home(mod, c).relative_to(Path(mod.data))
                        .as_posix() for c in p.campaigns}
    for h in sorted(homes):
        rw = f"{h}/{Path(RWM_REL).name}"
        rwm = Path(mod.data) / rw
        if rwm.exists():
            keep(rw)
            rwm.unlink()
            manifest["deleted"].append(rw)
            file_op("DELETE", rwm, "stale compiled map - the game would load it")

    what = f"{p.old[0]}x{p.old[1]} -> {p.new[0]}x{p.new[1]}"
    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "map_resize",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": f"map resize {what}", "resolved_type": what,
        "options": {"margins": dict(p.margins), "home": p.home},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("MAPRESIZE %s - %s, %d file(s), id=%s", mod.name, what,
             len(p.data), tid)
    return {"id": tid, "old": list(p.old), "new": list(p.new),
            "files": sorted(p.data), "record": rec}
