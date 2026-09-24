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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

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


class NewMapError(ValueError):
    """The form will not do."""


# ---------------------------------------------------------------------------
# the map itself


@dataclass
class Island:
    """The map as tiles: which are land, who owns them, where the cities are."""

    width: int
    height: int
    land: np.ndarray                  # bool, (H, W)
    owner: np.ndarray                 # int, (H, W), -1 for sea
    seats: List[Tuple[int, int]]      # image (x, y) of each province's city
    rise: np.ndarray                  # float 0..1 on the corner grid, 0 at the coast


def _ellipse(w: int, h: int, share: float) -> np.ndarray:
    ys, xs = np.mgrid[0:h, 0:w]
    rx0, ry0 = w / 2 - 3, h / 2 - 3
    s = min(1.0, math.sqrt(share * w * h / (math.pi * rx0 * ry0)))
    rx, ry = rx0 * s, ry0 * s
    cx, cy = (w - 1) / 2, (h - 1) / 2
    return ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0


def _kmeans(points: np.ndarray, k: int, rounds: int = 12) -> np.ndarray:
    """Seeds spread over ``points``: farthest-point start, then k-means."""
    centre = points.mean(axis=0)
    seeds = [points[np.argmin(((points - centre) ** 2).sum(1))]]
    far = ((points - seeds[0]) ** 2).sum(1)
    for _ in range(1, k):
        seeds.append(points[int(np.argmax(far))])
        far = np.minimum(far, ((points - seeds[-1]) ** 2).sum(1))
    seeds = np.array(seeds, dtype=float)
    from scipy.spatial import cKDTree
    for _ in range(rounds):
        lab = cKDTree(seeds).query(points)[1]
        for i in range(k):
            mine = points[lab == i]
            if len(mine):
                seeds[i] = mine.mean(axis=0)
    return seeds


def _tidy(owner: np.ndarray, k: int) -> np.ndarray:
    """Every province one piece: a stray fragment goes to the neighbour it
    touches most, which is 16e's rule that a province in two pieces is two."""
    from scipy import ndimage
    four = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    for _ in range(4):
        moved = False
        for i in range(k):
            parts, n = ndimage.label(owner == i, structure=four)
            if n <= 1:
                continue
            sizes = ndimage.sum(np.ones_like(parts), parts, range(1, n + 1))
            keep = int(np.argmax(sizes)) + 1
            for j in range(1, n + 1):
                if j == keep:
                    continue
                frag = parts == j
                ring = ndimage.binary_dilation(frag, structure=four) & ~frag
                around = owner[ring]
                around = around[(around >= 0) & (around != i)]
                if len(around):
                    owner[frag] = np.bincount(around).argmax()
                    moved = True
        if not moved:
            break
    return owner


def island(w: int, h: int, provinces: int, share: float) -> Island:
    """The shape: land, provinces, a city each, and how high the land climbs."""
    from scipy import ndimage
    land = _ellipse(w, h, share)
    pts = np.argwhere(land)[:, ::-1].astype(float)        # (x, y)
    if len(pts) < provinces * MIN_TILES:
        raise NewMapError(
            f"{len(pts)} tiles of land is not room for {provinces} province(s) "
            f"of {MIN_TILES} tiles each - make the map or the land share bigger, "
            f"or ask for fewer provinces")
    from scipy.spatial import cKDTree
    seeds = _kmeans(pts, provinces)
    owner = np.full((h, w), -1, dtype=int)
    ix = pts.astype(int)
    owner[ix[:, 1], ix[:, 0]] = cKDTree(seeds).query(pts)[1]
    owner = _tidy(owner, provinces)
    seats = []
    for i in range(provinces):
        cells = np.argwhere(owner == i)                    # (y, x)
        if not len(cells):
            raise NewMapError("a province came out with no land at all; ask "
                              "for fewer provinces")
        cy, cx = cells.mean(axis=0)
        best = None
        for y, x in sorted(cells.tolist(),
                           key=lambda t: (t[0] - cy) ** 2 + (t[1] - cx) ** 2):
            if all(0 <= y + dy < h and 0 <= x + dx < w and owner[y + dy, x + dx] == i
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
                best = (x, y)
                break
        if best is None:
            raise NewMapError("a province is too thin for a city to stand in; "
                              "ask for fewer provinces")
        seats.append(best)
    # how far each corner of the 2W+1 grid is from the sea, 0..1
    corners = np.zeros((2 * h + 1, 2 * w + 1), dtype=bool)
    tx = np.clip((np.arange(2 * w + 1) - 1) // 2, 0, w - 1)
    ty = np.clip((np.arange(2 * h + 1) - 1) // 2, 0, h - 1)
    corners[:, :] = land[ty[:, None], tx[None, :]]
    dist = ndimage.distance_transform_edt(corners)
    rise = dist / max(float(dist.max()), 1.0)
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


def _corner_view(tiles: np.ndarray) -> np.ndarray:
    """A tile array spread onto the 2W+1 grid by the brush's own partition."""
    h, w = tiles.shape[:2]
    tx = np.clip((np.arange(2 * w + 1) - 1) // 2, 0, w - 1)
    ty = np.clip((np.arange(2 * h + 1) - 1) // 2, 0, h - 1)
    return tiles[ty[:, None], tx[None, :]]


def layers(isl: Island, colours: Sequence[Tuple[int, int, int]],
           climate: Tuple[int, int, int]) -> Dict[str, Image.Image]:
    """Every layer, as RGB images, by layer code."""
    from scipy import ndimage
    w, h = isl.width, isl.height
    reg = np.zeros((h, w, 3), dtype=np.uint8)
    reg[:, :] = SEA_REGION
    for i, rgb in enumerate(colours):
        reg[isl.owner == i] = rgb
    for x, y in isl.seats:
        reg[y, x] = mapvocab.SETTLEMENT_RGB
    out = {"regions": Image.fromarray(reg, "RGB")}

    land_c = _corner_view(isl.land)
    hv = np.zeros((2 * h + 1, 2 * w + 1, 3), dtype=np.uint8)
    hv[:, :] = SEA_HEIGHT
    grey = np.clip(np.round(8 + 72 * isl.rise), 1, 255).astype(np.uint8)
    for c in range(3):
        hv[..., c] = np.where(land_c, grey, hv[..., c])
    out["heights"] = Image.fromarray(hv, "RGB")

    g = mapvocab.ground
    gt = np.zeros_like(hv)
    near = ndimage.binary_dilation(land_c, iterations=4)
    gt[:, :] = g("sea_deep")["rgb"]
    gt[near & ~land_c] = g("sea_shallow")["rgb"]
    gt[land_c] = g("fertility_medium")["rgb"]
    gt[land_c & (isl.rise > 0.6)] = g("hills")["rgb"]
    out["ground_types"] = Image.fromarray(gt, "RGB")

    out["climates"] = Image.new("RGB", (2 * w + 1, 2 * h + 1), climate)
    out["fog"] = Image.new("RGB", (2 * w + 1, 2 * h + 1), (255, 255, 255))
    out["features"] = Image.new("RGB", (w, h), (0, 0, 0))
    out["trade_routes"] = Image.new("RGB", (w, h), (0, 0, 0))
    out["roughness"] = Image.new("RGB", (2 * w, 2 * h), (0, 0, 0))
    ws = Image.fromarray(np.where(isl.land, 0, 255).astype(np.uint8), "L") \
        .resize((256, 256), Image.NEAREST)
    water = np.zeros((256, 256, 3), dtype=np.uint8)
    water[np.array(ws) > 0] = (40, 90, 170)
    out["water_surface"] = Image.fromarray(water, "RGB")
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
                               "seat": list(p.seat)} for p in self.provinces],
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
    land, climate, factions: [...]}``."""
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
    side_max = 2048 if getattr(mod, "m2ex", False) else MAX_SIDE
    if not (MIN_SIDE <= w <= side_max and MIN_SIDE <= h <= side_max):
        p.errors.append(f"a map is {MIN_SIDE} to {side_max} tiles a side"
                        + ("" if side_max > MAX_SIDE else
                           " on the stock engine; M2EX goes further"))
    if not 0.1 <= share <= 0.85:
        p.errors.append("the land share is between 0.1 and 0.85 of the map")
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
        return p

    cp = campnew.plan(mod, {k: body.get(k) for k in ("source", "name", "title", "blurb")})
    p.cp = cp
    if cp.errors:
        p.errors += cp.errors
        return p
    p.warnings += [x for x in cp.warnings if "map layer" not in x]
    skip = {f.lower() for f in REWRITTEN + NOT_COPIED} | {
        f.lower() for f in campmap.ALL_FILES if f.lower() != "map_fe.tga"} | {
        Path(campmap.RWM_REL).name.lower()}
    cp.copies = [(s, r) for s, r in cp.copies if Path(r).name.lower() not in skip]
    cp.texts = {r: t for r, t in cp.texts.items() if Path(r).name.lower() not in skip}

    try:
        isl = island(w, h, n, share)
    except NewMapError as exc:
        p.errors.append(str(exc))
        return p
    leaf = campstrat.campaign_leaf(cp.name)
    token = "".join(ch for ch in leaf if ch.isalnum() or ch == "_") or "New"
    colours = region_colours(n)
    have = {k.lower() for k in namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL)}
    for i in range(n):
        name, town = f"{token}_{i + 1}_Province", f"{token}_{i + 1}"
        if name.lower() in have or town.lower() in have:
            p.errors.append(f"{name} or {town} is already a name in "
                            f"{campmap.REGION_NAMES_REL}; pick another campaign "
                            f"name")
            return p
        p.provinces.append(Province(name, town, f"{leaf} {i + 1}", colours[i],
                                    isl.seats[i], "slave"))
    # the leader of each faction is its own province's; the first is nearest the
    # middle, so the player starts where the map is
    order = sorted(range(n), key=lambda i: (isl.seats[i][0] - w / 2) ** 2
                   + (isl.seats[i][1] - h / 2) ** 2)
    for j, i in enumerate(order[:len(picked)]):
        p.provinces[i].faction = picked[j]
    for i in order[len(picked):]:
        p.provinces[i].faction = "slave"

    home = cp.folder
    for code, img in layers(isl, colours, climate["rgb"]).items():
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
        leaf, src_strat, p.provinces, leaders, h, picked).encode(ENCODING)
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
    return p


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
