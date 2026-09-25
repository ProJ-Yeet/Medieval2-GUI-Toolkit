"""Phase 26b. A new campaign on a map made from nothing.

The TWCenter tutorial "Creating a World - Basic mapping from scratch" is the
recipe, and this is it done in one plan: every layer a map needs at the size
``descr_terrain.txt`` gives it, a ``descr_regions.txt`` that declares every
colour on ``map_regions.tga``, a ``descr_strat.txt`` that owns every province,
and the names the game shows for all of them. What the tutorial does by hand in
GIMP - an outline, a flood fill, a pixel per city - is done here to a shape
nobody drew, because the point is a map that **loads**, which is the one thing
a blank canvas does not do. The shape is then painted with the brush, the Real
world tab and the layer generators like any other map.

**It is a campaign, not a base map.** The engine reads a campaign's map from its
own folder before the base (:data:`campmap.ALL_FILES`), so the new map goes in
the new campaign's folder with its own ``descr_terrain.txt`` and
``descr_regions.txt``, and ``world/maps/base`` and every campaign reading it
are not touched. That is Reforged's ``world_a`` and Phase 73's shape.

**It starts as a copy.** :func:`campnew.plan` copies a campaign that works for
everything a map does not decide - the menu pictures, the faction movies, the
description keys - and the files that name provinces are then written fresh:
the strat, the script, the events, the mercenaries and the win conditions.

**The map.** One island in open sea, an ellipse over the share of the map asked
for, cut into provinces around evenly spread seeds (k-means over the land
tiles). Each province has one settlement pixel with its own province on all
four sides. The land rises away from the coast, so the first battle is not on
a table top: fertile ground, hills on the high middle, shallow sea along the
coast and deep sea beyond. One climate, chosen from the mod's own.

**Who holds what.** Each faction picked gets one province and a leader standing
in its settlement with the bodyguard the EDU gives it; every other province is
the rebels'. Leader names come from the faction's own pool in ``names.txt``.
"""
from __future__ import annotations

import colorsys
import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageFilter

from . import campfiles, campmap, campnew, campstrat, factions, hordestart, mapvocab
from . import namekeys
from .campmap import BASE_REL
from .maptga import TgaInfo, encode, read

ENCODING = campstrat.ENCODING

#: The sea's region colour and height, from the tutorial.
SEA_REGION = (41, 140, 233)
SEA_HEIGHT = (0, 0, 253)
#: Provinces smaller than this are not worth a settlement: a city needs its
#: tile and four neighbours, and room round them for an army to stand.
MIN_TILES = 16
#: The smallest map that is a map; the stock engine's largest.
MIN_SIDE, MAX_SIDE = 24, 510

#: Files of the copied campaign that name provinces, and so are written fresh
#: or not at all.
REWRITTEN = ("descr_strat.txt", "campaign_script.txt", "descr_events.txt",
             "descr_mercenaries.txt", "descr_win_conditions.txt")
NOT_COPIED = ("custom_tiles_db.txt", "descr_regions_and_settlement_name_lookup.txt")

#: The four sides a tile touches.
_CARD = ((0, -1), (0, 1), (-1, 0), (1, 0))


class NewMapError(ValueError):
    """The form will not do."""


# ---------------------------------------------------------------------------
# the map itself
#
# Plain Python and Pillow, like the rest of the toolkit: the release carries an
# embedded Python with Pillow in it and nothing else. Provinces are grown out
# of their seeds a tile at a time, all at once, which is linear in the land and
# gives every province in one piece by construction.


@dataclass
class Island:
    """The map as tiles: which are land, who owns them, where the cities are.

    Every grid is a flat list, row after row: ``land[y * width + x]``.
    """

    width: int
    height: int
    land: bytearray                   # 1 on land
    owner: List[int]                  # the province, -1 for sea
    seats: List[Tuple[int, int]]      # image (x, y) of each province's city
    rise: List[float]                 # 0..1 a tile, 0 at the coast

    def share(self) -> float:
        return sum(self.land) / float(self.width * self.height)


def _ellipse(w: int, h: int, share: float) -> bytearray:
    rx0, ry0 = w / 2 - 3, h / 2 - 3
    s = min(1.0, math.sqrt(share * w * h / (math.pi * rx0 * ry0)))
    rx, ry = rx0 * s, ry0 * s
    cx, cy = (w - 1) / 2, (h - 1) / 2
    out = bytearray(w * h)
    for y in range(h):
        dy = ((y - cy) / ry) ** 2
        if dy > 1:
            continue
        half = rx * math.sqrt(1 - dy)
        lo, hi = max(0, math.ceil(cx - half)), min(w, math.floor(cx + half) + 1)
        out[y * w + lo:y * w + hi] = b"\x01" * (hi - lo)
    return out


def _grow(land: bytearray, w: int, h: int, seeds: Sequence[int]) -> List[int]:
    """Every land tile given to the seed that reaches it first, stepping one
    tile at a time from all the seeds at once. -1 for sea."""
    owner = [-1] * (w * h)
    q: deque = deque()
    for k, s in enumerate(seeds):
        if owner[s] < 0:
            owner[s] = k
            q.append(s)
    while q:
        i = q.popleft()
        lab = owner[i]
        x = i % w
        for j, ok in ((i - w, i >= w), (i + w, i < w * (h - 1)),
                      (i - 1, x > 0), (i + 1, x < w - 1)):
            if ok and land[j] and owner[j] < 0:
                owner[j] = lab
                q.append(j)
    return owner


def _seed_tiles(land: bytearray, w: int, h: int, k: int) -> List[int]:
    """``k`` land tiles on an even staggered grid, the spacing found by halving,
    then moved a few times to the middle of what they grow into."""
    total = sum(land)
    cx, cy = (w - 1) / 2, (h - 1) / 2

    def grid(step: float) -> List[int]:
        out, row = [], 0
        y = step / 2
        while y < h:
            x = step / 2 + (step / 2 if row % 2 else 0)
            while x < w:
                i = int(y) * w + int(x)
                if land[i]:
                    out.append(i)
                x += step
            y += step * 0.866
            row += 1
        return out

    lo, hi = 1.0, float(max(w, h))
    best = grid(lo)
    for _ in range(30):
        mid = (lo + hi) / 2
        got = grid(mid)
        if len(got) >= k:
            lo, best = mid, got
        else:
            hi = mid
    best.sort(key=lambda i: (i % w - cx) ** 2 + (i // w - cy) ** 2)
    seeds = best[:k]
    if len(seeds) < k:                                    # a tiny island
        spare = [i for i, v in enumerate(land) if v and i not in set(seeds)]
        seeds += spare[:k - len(seeds)]
    for _ in range(3 if total < 400000 else 1):
        owner = _grow(land, w, h, seeds)
        sx, sy, n = [0.0] * k, [0.0] * k, [0] * k
        for i, o in enumerate(owner):
            if o >= 0:
                sx[o] += i % w
                sy[o] += i // w
                n[o] += 1
        moved = []
        taken = set()
        for o in range(k):
            if not n[o]:
                moved.append(seeds[o])
                continue
            t = int(round(sy[o] / n[o])) * w + int(round(sx[o] / n[o]))
            if not land[t] or owner[t] != o or t in taken:
                t = seeds[o]
            taken.add(t)
            moved.append(t)
        seeds = moved
    return seeds


def _steps(land: bytearray, w: int, h: int) -> List[int]:
    """How many tiles each land tile is from the sea (four-connected)."""
    out = [0 if v else -1 for v in land]
    q: deque = deque(i for i, v in enumerate(land) if not v)
    far = [0] * (w * h)
    seen = bytearray(0 if v else 1 for v in land)
    while q:
        i = q.popleft()
        x = i % w
        for j, ok in ((i - w, i >= w), (i + w, i < w * (h - 1)),
                      (i - 1, x > 0), (i + 1, x < w - 1)):
            if ok and not seen[j]:
                seen[j] = 1
                far[j] = far[i] + 1
                q.append(j)
    for i, v in enumerate(land):
        if v:
            out[i] = far[i]
    return out


def island(w: int, h: int, provinces: int, share: float) -> Island:
    """The shape: land, provinces, a city each, and how high the land climbs."""
    land = _ellipse(w, h, share)
    total = sum(land)
    if total < provinces * MIN_TILES:
        raise NewMapError(
            f"{total} tiles of land is not room for {provinces} province(s) "
            f"of {MIN_TILES} tiles each - make the map or the land share bigger, "
            f"or ask for fewer provinces")
    owner = _grow(land, w, h, _seed_tiles(land, w, h, provinces))
    cells: Dict[int, List[int]] = {}
    for j, o in enumerate(owner):
        if o >= 0:
            cells.setdefault(o, []).append(j)
    seats = []
    for i in range(provinces):
        mine = cells.get(i)
        if not mine or len(mine) < 5:
            raise NewMapError("a province came out too small for a city; ask "
                              "for fewer provinces or more land")
        cx = sum(j % w for j in mine) / len(mine)
        cy = sum(j // w for j in mine) / len(mine)
        best = None
        for j in sorted(mine, key=lambda t: (t % w - cx) ** 2 + (t // w - cy) ** 2):
            x, y = j % w, j // w
            if all(0 <= x + dx < w and 0 <= y + dy < h
                   and owner[(y + dy) * w + x + dx] == i for dx, dy in _CARD):
                best = (x, y)
                break
        if best is None:
            raise NewMapError("a province is too thin for a city to stand in; "
                              "ask for fewer provinces")
        seats.append(best)
    steps = _steps(land, w, h)
    top = max(steps) or 1
    rise = [s / top if s > 0 else 0.0 for s in steps]
    return Island(w, h, land, owner, seats, rise)


def region_colours(n: int) -> List[Tuple[int, int, int]]:
    """``n`` colours no marker, no sea and no other province is near."""
    out: List[Tuple[int, int, int]] = []
    taken = {SEA_REGION, mapvocab.SETTLEMENT_RGB, mapvocab.PORT_RGB}
    hue = 0.13
    while len(out) < n:
        hue = (hue + 0.618033988749895) % 1.0
        for sat, val in ((0.62, 0.86), (0.48, 0.72), (0.75, 0.62)):
            rgb = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(hue, sat, val))
            near_sea = all(abs(a - b) <= 12 for a, b in zip(rgb, SEA_REGION))
            if rgb not in taken and not near_sea:
                out.append(rgb)
                taken.add(rgb)
                break
    return out


def corner_view(tiles: Image.Image) -> Image.Image:
    """A tile-sized picture spread onto the 2W+1 grid by the brush's own
    partition: corner ``c`` is tile ``(c - 1) // 2``, and corner 0 goes with
    tile 0."""
    w, h = tiles.size
    big = tiles.resize((2 * w, 2 * h), Image.NEAREST)
    out = Image.new(tiles.mode, (2 * w + 1, 2 * h + 1))
    out.paste(big, (1, 1))
    out.paste(big.crop((0, 0, 1, 2 * h)), (0, 1))
    out.paste(out.crop((0, 1, 2 * w + 1, 2)), (0, 0))
    return out


def layers(isl: Island, colours: Sequence[Tuple[int, int, int]],
           climate: Tuple[int, int, int]) -> Dict[str, Image.Image]:
    """Every layer, as RGB images, by layer code."""
    w, h = isl.width, isl.height
    reg = bytearray(bytes(SEA_REGION) * (w * h))
    for i, o in enumerate(isl.owner):
        if o >= 0:
            reg[3 * i:3 * i + 3] = bytes(colours[o])
    for x, y in isl.seats:
        i = y * w + x
        reg[3 * i:3 * i + 3] = bytes(mapvocab.SETTLEMENT_RGB)
    out = {"regions": Image.frombytes("RGB", (w, h), bytes(reg))}

    cw, ch = 2 * w + 1, 2 * h + 1
    land = corner_view(Image.frombytes("L", (w, h), bytes(255 if v else 0 for v in isl.land)))
    grey = corner_view(Image.frombytes("L", (w, h), bytes(
        min(255, max(1, int(round(8 + 72 * r)))) for r in isl.rise)))
    heights = Image.new("RGB", (cw, ch), SEA_HEIGHT)
    heights.paste(Image.merge("RGB", (grey, grey, grey)), mask=land)
    out["heights"] = heights

    g = mapvocab.ground
    ground = Image.new("RGB", (cw, ch), g("sea_deep")["rgb"])
    coast = land.filter(ImageFilter.MaxFilter(9))          # four corners out
    ground.paste(g("sea_shallow")["rgb"], mask=coast)
    ground.paste(g("fertility_medium")["rgb"], mask=land)
    high = grey.point(lambda v: 255 if v > 8 + 72 * 0.6 else 0)
    ground.paste(g("hills")["rgb"], mask=ImageChops.multiply(high, land))
    out["ground_types"] = ground

    out["climates"] = Image.new("RGB", (cw, ch), climate)
    out["fog"] = Image.new("RGB", (cw, ch), (255, 255, 255))
    out["features"] = Image.new("RGB", (w, h), (0, 0, 0))
    out["trade_routes"] = Image.new("RGB", (w, h), (0, 0, 0))
    out["roughness"] = Image.new("RGB", (2 * w, 2 * h), (0, 0, 0))
    sea = Image.frombytes("L", (w, h), bytes(0 if v else 255 for v in isl.land)) \
        .resize((256, 256), Image.NEAREST)
    water = Image.new("RGB", (256, 256), (0, 0, 0))
    water.paste((40, 90, 170), mask=sea)
    out["water_surface"] = water
    return out


def _tga(mod, code: str, img: Image.Image) -> bytes:
    """``img`` in the shape the mod's own copy of the layer is written in."""
    name = campmap.LAYER_BY_CODE[code]["file"]
    path = Path(mod.data) / BASE_REL / name
    depth, itype, desc = 24, 2, 0x20
    if path.is_file():
        try:
            _, have = read(path)
            depth, itype, desc = have.depth, have.image_type, have.descriptor
        except Exception:                                  # noqa: BLE001
            pass
    info = TgaInfo(image_type=itype, width=img.width, height=img.height,
                   depth=depth, descriptor=desc)
    return encode(img.convert(info.mode), info)


# ---------------------------------------------------------------------------
# the text


def _terrain(mod, w: int, h: int) -> str:
    """The base's ``descr_terrain.txt`` with the new dimensions, else the
    tutorial's."""
    import re
    path = Path(mod.data) / campmap.TERRAIN_REL
    text = path.read_bytes().decode(ENCODING) if path.is_file() else (
        "dimensions\n{\n\twidth  0\n\theight  0\n}\nheights\n{\n"
        "\tmin_sea_height  -3122.256\n\tmax_land_height  7511.272\n}\n"
        "roughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n"
        "\tmultiplier  0.500\n}\nlattitude\n{\n\tmin  22.000\n\tmax  56.000\n}\n")
    text = re.sub(r"(\bwidth\s+)\d+", lambda m: f"{m.group(1)}{w}", text, count=1)
    return re.sub(r"(\bheight\s+)\d+", lambda m: f"{m.group(1)}{h}", text, count=1)


def _template_record(mod) -> Tuple[str, str]:
    """``(rebels, religions line)`` of the base map's first province, so the new
    records name a rebel type and religions this mod actually has."""
    path = Path(mod.data) / campmap.REGIONS_REL
    if path.is_file():
        rf = campmap.parse_regions(path.read_bytes().decode(ENCODING))
        for rec in rf.records:
            if rec.rebels and rec.religions_line >= 0:
                line = rf.lines[rec.religions_line].strip()
                return rec.rebels, line
    return "Bandit_Rebels", "religions { catholic 100 }"


@dataclass
class Province:
    name: str
    town: str
    shown: str
    rgb: Tuple[int, int, int]
    seat: Tuple[int, int]                 # image
    faction: str
    port: Optional[Tuple[int, int]] = None   # image; 87e places one on the coast


def _regions_text(provs: Sequence[Province], rebels: str, religions: str) -> str:
    rows = []
    for p in provs:
        rows += [p.name, f"\t{p.town}", f"\t{p.faction}", f"\t{rebels}",
                 f"\t{p.rgb[0]} {p.rgb[1]} {p.rgb[2]}", "\tnone", "\t5", "\t4",
                 f"\t{religions}", ""]
    return "\r\n".join(rows)


def _strat_text(leaf: str, source_strat: str, provs: Sequence[Province],
                leaders: Dict[str, Tuple[str, List[str]]], h: int,
                playable: Sequence[str]) -> str:
    """The whole ``descr_strat.txt``: the tutorial's shape, the source's dates."""
    import re
    keep = []
    for word in ("start_date", "end_date", "timescale", "brigand_spawn_value",
                 "pirate_spawn_value"):
        m = re.search(rf"^[ \t]*{word}\b[^\r\n;]*", source_strat, re.M)
        if m:
            keep.append(m.group(0).strip())
    heads = dict(re.findall(r"^[ \t]*faction[ \t]+(\w+)[ \t]*,[ \t]*([^\r\n;]*)",
                            source_strat, re.M))
    labels = {}
    for m in re.finditer(r"^[ \t]*faction[ \t]+(\w+)[^\n]*\n[ \t]*ai_label[ \t]+(\w+)",
                         source_strat, re.M):
        labels[m.group(1)] = m.group(2)
    out = [f"campaign\t\t{leaf}", "playable"] + [f"\t{f}" for f in playable] + [
        "end", "unlockable", "end", "nonplayable", "\tslave", "end", ""]
    out += keep + [""]
    owners = list(playable) + ["slave"]
    for f in owners:
        mine = [p for p in provs if p.faction == f]
        out.append(f"faction\t{f}, {heads.get(f, 'balanced smith').strip()}")
        out.append(f"ai_label\t\t{labels.get(f, 'default')}")
        out.append(f"denari\t{10000 if f != 'slave' else 5000}")
        for p in mine:
            out += ["settlement", "{", "\tlevel town", f"\tregion {p.name}", "",
                    "\tyear_founded 0", "\tpopulation 1500",
                    "\tplan_set default_set", f"\tfaction_creator {f}", "}"]
        if f in leaders and mine:
            name, army = leaders[f]
            x, y = mine[0].seat
            out.append(f"character\t{name}, named character, male, leader, "
                       f"age 30, x {x}, y {h - 1 - y}")
            out.append("army")
            out += [f"unit\t\t{u}\t\t\t\texp 1 armour 0 weapon_lvl 0" for u in army]
        out.append("")
    out += ["script", "campaign_script.txt", ""]
    return "\r\n".join(out)


SCRIPT = "script\r\n\trestrict_strat_radar false\r\n\r\nend_script\r\n"


# ---------------------------------------------------------------------------
# the plan


@dataclass
class NewMapPlan:
    """A new campaign on a new map, worked out without writing."""

    cp: Optional[campnew.CampaignPlan] = None
    width: int = 0
    height: int = 0
    provinces: List[Province] = field(default_factory=list)
    data: Dict[str, bytes] = field(default_factory=dict)
    loc: Dict[str, str] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def mod(self):
        return self.cp.mod if self.cp else None

    def summary(self) -> str:
        head = (f"new campaign {self.cp.name if self.cp else '?'} on a new "
                f"{self.width}x{self.height} map, {len(self.provinces)} provinces")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        cp = self.cp
        return {"name": cp.name if cp else "", "folder": cp.folder if cp else "",
                "source": cp.source if cp else "",
                "width": self.width, "height": self.height,
                "provinces": [{"name": p.name, "town": p.town, "shown": p.shown,
                               "faction": p.faction, "rgb": list(p.rgb),
                               "seat": list(p.seat),
                               "port": list(p.port) if p.port else None}
                              for p in self.provinces],
                "files": sorted(set(self.data) | {r for _, r in (cp.copies if cp else [])}),
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.data)}


def _int(body: dict, key: str, default: int) -> int:
    try:
        return int(body.get(key) if body.get(key) not in (None, "") else default)
    except (TypeError, ValueError):
        raise NewMapError(f"{key} has to be a whole number, not {body.get(key)!r}")


def plan(mod, body: dict) -> NewMapPlan:
    """``body``: ``{source, name, title, blurb, width, height, provinces,
    land, climate, factions: [...]}``. With ``shape: real`` the map is the real
    world under a box instead (87e, :mod:`unittransfer.mapnewreal`)."""
    if str(body.get("shape") or "") == "real":
        from . import mapnewreal
        return mapnewreal.plan(mod, body)
    p = NewMapPlan()
    try:
        w = _int(body, "width", 160)
        h = _int(body, "height", 120)
        n = _int(body, "provinces", 8)
        share = float(body.get("land") or 0.55)
    except (NewMapError, ValueError) as exc:
        p.errors.append(str(exc))
        return p
    p.width, p.height = w, h
    _check_size(mod, p, w, h)
    if not 0.1 <= share <= 0.85:
        p.errors.append("the land share is between 0.1 and 0.85 of the map")
    got = _setup(mod, body, p, n)
    if got is None:
        return p
    cp, picked, climate = got
    try:
        isl = island(w, h, n, share)
    except NewMapError as exc:
        p.errors.append(str(exc))
        return p
    leaf = campstrat.campaign_leaf(cp.name)
    token = "".join(ch for ch in leaf if ch.isalnum() or ch == "_") or "New"
    colours = region_colours(n)
    keys = [(f"{token}_{i + 1}_Province", f"{token}_{i + 1}") for i in range(n)]
    if not _names_free(mod, p, keys):
        return p
    for i, (name, town) in enumerate(keys):
        p.provinces.append(Province(name, town, f"{leaf} {i + 1}", colours[i],
                                    isl.seats[i], "slave"))
    _hand_out(p, picked, w, h)
    _finish(mod, p, cp, layers(isl, colours, climate["rgb"]), picked, w, h)
    return p


def _check_size(mod, p: NewMapPlan, w: int, h: int) -> None:
    side_max = 2048 if getattr(mod, "m2ex", False) else MAX_SIDE
    if not (MIN_SIDE <= w <= side_max and MIN_SIDE <= h <= side_max):
        p.errors.append(f"a map is {MIN_SIDE} to {side_max} tiles a side"
                        + ("" if side_max > MAX_SIDE else
                           " on the stock engine; M2EX goes further"))


def _setup(mod, body: dict, p: NewMapPlan, n: int):
    """The checks every new map shares, then the campaign copied. Returns
    ``(campaign plan, factions picked, climate)``, or None with ``p.errors``."""
    if not 1 <= n <= 199:
        p.errors.append("a map has 1 to 199 provinces")
    slots = [s.lower() for s in factions.faction_slots(mod)]
    picked = [str(f).strip() for f in (body.get("factions") or []) if str(f).strip()]
    bad = [f for f in picked if f.lower() not in slots or f.lower() == "slave"]
    if bad:
        p.errors.append("not a faction of this mod: " + ", ".join(bad))
    if not picked:
        p.errors.append("pick at least one faction to play")
    if len(picked) > n:
        p.errors.append(f"{len(picked)} factions need {len(picked)} provinces at "
                        f"least, one each")
    clim = [c for c in mapvocab.climates(mod) if c.get("rgb")]
    want = str(body.get("climate") or "").strip()
    climate = next((c for c in clim if c["code"] == want), None) or (
        clim[0] if clim else None)
    if climate is None:
        p.errors.append("this mod declares no climates in descr_climates.txt, so "
                        "there is nothing to paint the map with")
    if p.errors:
        return None

    cp = campnew.plan(mod, {k: body.get(k) for k in ("source", "name", "title", "blurb")})
    p.cp = cp
    if cp.errors:
        p.errors += cp.errors
        return None
    p.warnings += [x for x in cp.warnings if "map layer" not in x]
    skip = {f.lower() for f in REWRITTEN + NOT_COPIED} | {
        f.lower() for f in campmap.ALL_FILES if f.lower() != "map_fe.tga"} | {
        Path(campmap.RWM_REL).name.lower()}
    cp.copies = [(s, r) for s, r in cp.copies if Path(r).name.lower() not in skip]
    cp.texts = {r: t for r, t in cp.texts.items() if Path(r).name.lower() not in skip}
    return cp, picked, climate


def _names_free(mod, p: NewMapPlan, keys: Sequence[Tuple[str, str]]) -> bool:
    """Refuse a province or town key the shared names file already has."""
    have = {k.lower() for k in namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL)}
    for name, town in keys:
        if name.lower() in have or town.lower() in have:
            p.errors.append(f"{name} or {town} is already a name in "
                            f"{campmap.REGION_NAMES_REL}; pick another campaign "
                            f"name")
            return False
    return True


def _hand_out(p: NewMapPlan, picked: Sequence[str], w: int, h: int) -> None:
    """Each faction picked that holds nothing yet takes the free province
    nearest the middle, so the player starts where the map is; every province
    nobody holds is the rebels'."""
    held = {pr.faction for pr in p.provinces if pr.faction != "slave"}
    order = sorted(range(len(p.provinces)),
                   key=lambda i: (p.provinces[i].seat[0] - w / 2) ** 2
                   + (p.provinces[i].seat[1] - h / 2) ** 2)
    free = [i for i in order if p.provinces[i].faction == "slave"]
    for f, i in zip([f for f in picked if f not in held], free):
        p.provinces[i].faction = f


def _finish(mod, p: NewMapPlan, cp, imgs: Dict[str, Image.Image],
            picked: Sequence[str], w: int, h: int) -> None:
    """Every file of the new campaign: the layers, its terrain and regions, the
    strat with a leader each, the script, the blanks, and the names."""
    n = len(p.provinces)
    home = cp.folder
    for code, img in imgs.items():
        p.data[f"{home}/{campmap.LAYER_BY_CODE[code]['file']}"] = _tga(mod, code, img)
    p.data[f"{home}/descr_terrain.txt"] = _terrain(mod, w, h).encode(ENCODING)
    rebels, religions = _template_record(mod)
    p.data[f"{home}/descr_regions.txt"] = _regions_text(
        p.provinces, rebels, religions).encode(ENCODING)

    leaders: Dict[str, Tuple[str, List[str]]] = {}
    taken: set = set()
    for f in picked:
        names = hordestart.pick_names(hordestart._names(mod, f), taken, 1)
        name = names[0] if names else f"{f.title()} Leader"
        taken.add(name)
        army = hordestart.default_army(hordestart.owned_units(mod, f), [])
        if not army:
            p.warnings.append(f"the EDU gives {f} no bodyguard unit, so its "
                              f"leader starts with no army")
        leaders[f] = (name, army[:1])
    src_strat = ""
    src = campmap.campaign_home(mod, cp.source) / campstrat.STRAT_NAME
    if src.is_file():
        src_strat = src.read_bytes().decode(ENCODING)
    p.data[f"{home}/{campstrat.STRAT_NAME}"] = _strat_text(
        campstrat.campaign_leaf(cp.name), src_strat, p.provinces, leaders, h,
        picked).encode(ENCODING)
    p.data[f"{home}/campaign_script.txt"] = SCRIPT.encode(ENCODING)
    for blank in ("descr_events.txt", "descr_mercenaries.txt",
                  "descr_win_conditions.txt"):
        p.data[f"{home}/{blank}"] = b""
    for pr in p.provinces:
        p.loc[pr.name] = pr.shown
        p.loc[pr.town] = f"{pr.shown} town"

    p.changes.append(f"{home}: a {w}x{h} map of its own - all ten layers, "
                     f"descr_terrain.txt and descr_regions.txt")
    held = ", ".join(f"{pr.faction}: {pr.name}" for pr in p.provinces
                     if pr.faction != "slave")
    p.changes.append(f"{n} province(s), {len(picked)} held ({held}), the rest "
                     f"the rebels'")
    p.changes.append(f"{home}/{campstrat.STRAT_NAME}: written new, one leader "
                     f"per faction in its settlement")
    p.changes.append(f"{campmap.REGION_NAMES_REL}: {len(p.loc)} name(s) added")
    p.changes.append(f"copied from {cp.source}: {len(cp.copies)} file(s) that name "
                     f"no province (pictures, movies)")
    p.warnings.append(
        "descr_sounds_music_types.txt in world/maps/base is shared with every "
        "other campaign and names no music for these provinces; they play the "
        "default until a music type lists them")


# ---------------------------------------------------------------------------
# the save


def apply(p: NewMapPlan) -> dict:
    """Write the campaign, its map and its names, with one Undo."""
    import shutil

    from . import config
    from .logutil import file_op, log

    if p.errors or p.cp is None:
        raise ValueError("cannot apply: " + "; ".join(p.errors or ["no plan"]))
    cp, mod = p.cp, p.cp.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    warnings: List[str] = []

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

    for src, rel in cp.copies:
        shutil.copy2(src, keep(rel))
    for rel, text in sorted(cp.texts.items()):
        keep(rel).write_bytes(text.encode(ENCODING))
    for rel, blob in sorted(p.data.items()):
        keep(rel).write_bytes(blob)
        file_op("WRITE", Path(mod.data) / rel, f"{len(blob)} bytes")
    if cp.loc_writes:
        campfiles.write_descriptions(mod, cp.loc_writes, cp.loc_new, keep, file_op)
    namekeys._write_loc(mod, campmap.REGION_NAMES_REL, p.loc, keep, warnings)

    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campfiles", "action": "campaign_new_map",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": cp.name, "resolved_type": cp.name,
        "options": {"source": cp.source, "size": [p.width, p.height],
                    "provinces": len(p.provinces)},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings) + warnings,
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("NEWMAP %s - %s %dx%d, %d province(s), id=%s", mod.name, cp.name,
             p.width, p.height, len(p.provinces), tid)
    return {"id": tid, "name": cp.name, "folder": cp.folder,
            "files": len(cp.copies) + len(cp.texts) + len(p.data), "record": rec}


def view(mod) -> dict:
    """What the form offers: campaigns to copy, factions, climates."""
    return {"sources": campnew.sources(mod),
            "factions": [s for s in factions.faction_slots(mod) if s.lower() != "slave"],
            "climates": [{"code": c["code"], "name": c["name"], "rgb": list(c["rgb"])}
                         for c in mapvocab.climates(mod) if c.get("rgb")],
            "limits": {"min": MIN_SIDE,
                       "max": 2048 if getattr(mod, "m2ex", False) else MAX_SIDE}}
