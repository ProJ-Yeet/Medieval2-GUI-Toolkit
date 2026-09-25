"""Phase 87e. A new campaign on the real world under a box.

Mylae's New Map Editor ends in a bundle of layers somebody still has to make
into a campaign. This ends in a campaign that loads: 26b's new campaign
(:mod:`unittransfer.mapnew`), with the map made from the real world instead of
an island from nothing.

**The land and the sea** are the real ground's: a tile is land when the
elevation under its centre is above sea level (Terrarium, 27's source), and
where asked the real coastline (25) and OSM's lakes and seas (87c) make their
water side sea too. Land in specks smaller than a size is made sea; it would be
a province nobody can hold.

**The provinces** come from the settlements picked on the world picker (a
search result, a historic site, a click), each grown over the land from its
city a tile at a time, all at once, so every land tile a city can walk to is
its province and each is one piece. Land no city reaches (an island with no
settlement on it) joins the province nearest across the water, as islands do
in the shipped maps. With no settlements picked, the cities are spread evenly,
as on 26b's island. A settlement on a sea tile moves to the nearest land; one
next to another is left out, and both are said.

**The rest** is every generator's, at this map's own scale: the heights true
to ``max_land_height`` and the sea floor in the blue, ground types from the
heights by 27's bands (sea shallow along the coast, deep beyond), climates as
asked (one, from the ground types, or the Köppen zones), and rivers from OSM
drawn the way the engine can build them. A port stands on the coastal land
tile nearest each coastal city, where the dock rule finds water. The box is
written beside the map as ``bbox_coords.txt``, so the Real world and Generate
tabs line up on the new campaign at once.
"""
from __future__ import annotations

import math
import re
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageFilter

from . import campmap, campstrat, mapgen, mapvocab, namekeys, osmmap
from .mapnew import (SEA_HEIGHT, SEA_REGION, NewMapError, NewMapPlan, Province, _CARD,
                     _check_size, _finish, _grow, _hand_out, _int, _names_free, _seed_tiles,
                     _setup, _terrain, corner_view, region_colours)

#: Land in a piece smaller than this many tiles is made sea.
MIN_ISLAND = 4
#: How far (tiles) a settlement on the sea is moved to find land.
MOVE_REACH = 6


def _key(name: str) -> str:
    """A name the engine can carry: ASCII letters, digits and underscores."""
    import unicodedata
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"[^A-Za-z0-9_]", "", s)
    return s or "Place"


def _pieces(land: bytearray, w: int, h: int) -> List[List[int]]:
    """The four-connected pieces of land, each a list of tiles."""
    seen = bytearray(len(land))
    out = []
    for start, v in enumerate(land):
        if not v or seen[start]:
            continue
        seen[start] = 1
        piece, todo = [], [start]
        while todo:
            i = todo.pop()
            piece.append(i)
            x = i % w
            for j, ok in ((i - w, i >= w), (i + w, i < w * (h - 1)),
                          (i - 1, x > 0), (i + 1, x < w - 1)):
                if ok and land[j] and not seen[j]:
                    seen[j] = 1
                    todo.append(j)
        out.append(piece)
    return out


def _nearest_land(land: bytearray, w: int, h: int, x: int, y: int,
                  reach: int) -> Optional[Tuple[int, int]]:
    """The nearest land tile with land on a cardinal side (a city needs one),
    stepping outwards up to ``reach`` tiles."""
    best = None
    for r in range(0, reach + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or not land[ny * w + nx]:
                    continue
                if not any(0 <= nx + a < w and 0 <= ny + b < h and land[(ny + b) * w + nx + a]
                           for a, b in _CARD):
                    continue
                d = dx * dx + dy * dy
                if best is None or d < best[0]:
                    best = (d, nx, ny)
        if best is not None:
            return best[1], best[2]
    return None


def _join_islands(land: bytearray, owner: List[int], w: int, h: int) -> int:
    """Land no city reached given to the province nearest across the water:
    one breadth-first walk over every tile from every owned one. Returns how
    many tiles were joined."""
    lab = list(owner)
    q = deque(i for i, o in enumerate(owner) if o >= 0)
    while q:
        i = q.popleft()
        x = i % w
        for j, ok in ((i - w, i >= w), (i + w, i < w * (h - 1)),
                      (i - 1, x > 0), (i + 1, x < w - 1)):
            if ok and lab[j] < 0:
                lab[j] = lab[i]
                q.append(j)
    joined = 0
    for i, v in enumerate(land):
        if v and owner[i] < 0:
            owner[i] = lab[i]
            joined += 1
    return joined


def _port(land: bytearray, owner: List[int], w: int, h: int, k: int,
          seat: Tuple[int, int], taken: set) -> Optional[Tuple[int, int]]:
    """Province ``k``'s port: a land tile of its own with sea on a cardinal
    side and nobody else's land on any, nearest its city."""
    sx, sy = seat
    best = None
    for i, o in enumerate(owner):
        if o != k:
            continue
        x, y = i % w, i // w
        if (x, y) == seat or (x, y) in taken:
            continue
        sea_side = mine = False
        other = False
        for a, b in _CARD:
            nx, ny = x + a, y + b
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            j = ny * w + nx
            if not land[j]:
                sea_side = True
            elif owner[j] == k and (nx, ny) != seat:
                mine = True
            elif owner[j] != k:
                other = True
        if sea_side and mine and not other:
            d = abs(x - sx) + abs(y - sy)
            if best is None or d < best[0]:
                best = (d, x, y)
    return (best[1], best[2]) if best else None


def _terrain_heights(text: str) -> Tuple[float, float]:
    top = re.search(r"max_land_height\s+(-?[\d.]+)", text)
    deep = re.search(r"min_sea_height\s+(-?[\d.]+)", text)
    return (float(top.group(1)) if top else 7511.272,
            float(deep.group(1)) if deep else -3122.256)


def plan(mod, body: dict) -> NewMapPlan:
    """``body``: 26b's (source, name, title, blurb, factions, climate) and
    ``box`` (the world picker's), ``width`` (the height follows the box's shape
    unless given, when the box is given the map's shape), ``settlements``
    (``[{name, lat, lon, faction?, port?}]``), ``provinces`` (how many cities
    to spread when none is picked), ``coast``, ``water`` (kinds), ``min_island``,
    ``climates`` (``one``, ``ground`` or ``koppen``), ``rivers`` (``none`` or a
    detail level)."""
    p = NewMapPlan()
    try:
        box = osmmap.parse_bbox(body.get("box") or {})
        w = _int(body, "width", 200)
        h = _int(body, "height", 0)
        if h:
            box = osmmap.fit(box, w, h, "width")
        else:
            w, h = osmmap.size_for(box, width=w)
        n_auto = _int(body, "provinces", 0)
        min_island = max(0, _int(body, "min_island", MIN_ISLAND))
    except (NewMapError, osmmap.OsmError, ValueError) as exc:
        p.errors.append(str(exc))
        return p
    p.width, p.height = w, h
    _check_size(mod, p, w, h)
    picks = [s for s in (body.get("settlements") or []) if isinstance(s, dict)]
    n = len(picks) or n_auto
    if not n:
        p.errors.append("pick the settlements on the world map (search, a historic "
                        "site or a click), or say how many to spread")
        return p
    got = _setup(mod, body, p, n)
    if got is None:
        return p
    cp, picked, climate = got
    proj = osmmap.Projection(box, w, h)
    try:
        imgs, seats, notes = _make(mod, p, box, proj, w, h, picks, n_auto, min_island, body,
                                   climate)
    except (mapgen.GenError, osmmap.OsmError, NewMapError) as exc:
        p.errors.append(str(exc))
        return p
    if p.errors:
        return p

    leaf = campstrat.campaign_leaf(cp.name)
    token = "".join(ch for ch in leaf if ch.isalnum() or ch == "_") or "New"
    colours = region_colours(len(seats))
    # a real city's name is often one the mod already has (Palermo, Roma): the
    # names file is shared by every campaign, so a taken key takes the campaign's
    # name in front; the name the player sees is the city's either way
    have = {x.lower() for x in namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL)}
    keys, used = [], set()
    for i, s in enumerate(seats):
        base = _key(s["name"]) if s.get("name") else f"{token}_{i + 1}"
        if base.lower() in have or f"{base}_province".lower() in have:
            base = f"{token}_{base}"
        k, m = base, 2
        while k.lower() in used or k.lower() in have or f"{k}_province" in have:
            k, m = f"{base}_{m}", m + 1
        used.add(k.lower())
        keys.append((f"{k}_Province", k))
    if not _names_free(mod, p, keys):
        return p
    known = {f.lower(): f for f in picked}
    for i, ((name, town), s) in enumerate(zip(keys, seats)):
        shown = s.get("name") or f"{leaf} {i + 1}"
        fac = known.get(str(s.get("faction") or "").lower(), "slave")
        p.provinces.append(Province(name, town, shown, colours[i], s["seat"], fac,
                                    s.get("port")))
    _hand_out(p, picked, w, h)
    # the regions layer wants the colours, so it is drawn now the names are known
    imgs["regions"] = _regions(imgs.pop("_owner"), imgs.pop("_land"), w, h, colours,
                               [s["seat"] for s in seats], [s.get("port") for s in seats])
    _finish(mod, p, cp, imgs, picked, w, h)
    # after _finish, which says "a W x H map of its own"
    home = cp.folder
    p.data[f"{home}/{osmmap.BBOX_FILE}"] = osmmap.bbox_text(box, w, h).encode("utf-8")
    p.changes[0] = (f"{home}: a {w}x{h} map of the real world under N {box.north:.3f} "
                    f"S {box.south:.3f} W {box.west:.3f} E {box.east:.3f}"
                    + (f", turned {box.rotation:.1f}°" if box.rotated else "")
                    + " - all ten layers, descr_terrain.txt, descr_regions.txt and "
                      "bbox_coords.txt")
    p.changes[1:1] = notes
    return p


def _make(mod, p: NewMapPlan, box, proj, w: int, h: int, picks: Sequence[dict],
          n_auto: int, min_island: int, body: dict, climate: dict):
    """The map's layers but the regions, its cities, and what was done."""
    notes: List[str] = []
    cols, rows = 2 * w + 1, 2 * h + 1
    metres = mapgen.elevation(box, cols, rows)
    centre = metres.transform((w, h), Image.AFFINE, (2, 0, 0.5, 0, 2, 0.5), Image.NEAREST)
    land = bytearray(1 if v > 0 else 0 for v in array_of(centre))
    notes.append(f"land and sea from the real ground: {sum(land):,} of {w * h:,} tiles "
                 f"above sea level")
    if body.get("coast"):
        ways = osmmap.coastline(box)
        c = osmmap.analyse(ways, proj, bytes(w * h))
        if c.leaks or not ways:
            p.warnings.append("the real coastline has a gap over this box (or none), "
                              "so the land is the elevation's alone")
        else:
            n = 0
            for i, v in enumerate(c.water):
                if v and land[i]:
                    land[i] = 0
                    n += 1
            notes.append(f"the real coastline's water side made sea: {n:,} tile(s)")
    kinds = [k for k in (body.get("water") or []) if k in osmmap.WATER_KINDS]
    if kinds:
        wt = osmmap.water_tiles(osmmap.water(box, kinds), proj, bytes(w * h),
                                float(body.get("water_min", osmmap.WATER_MIN_TILES)))
        for x, y in wt.to_sea:
            land[y * w + x] = 0
        notes.append(f"OSM's {', '.join(kinds)} made sea: {len(wt.to_sea):,} tile(s), "
                     f"{wt.holes} island(s) kept dry")
    specks = [pc for pc in _pieces(land, w, h) if len(pc) < min_island]
    for pc in specks:
        for i in pc:
            land[i] = 0
    if specks:
        notes.append(f"{len(specks)} speck(s) of land under {min_island} tiles made sea")
    if sum(land) < 5:
        raise NewMapError("there is next to no land under this box; move it over some")

    # the cities
    seats: List[dict] = []
    taken = set()
    for s in picks:
        try:
            lat, lon = float(s["lat"]), float(s["lon"])
        except (KeyError, TypeError, ValueError):
            p.warnings.append(f"{s.get('name') or 'a settlement'} has no latitude and "
                              "longitude, and is left out")
            continue
        fx, fy = proj.to_tile(lat, lon)
        x, y = int(round(fx)), int(round(fy))
        name = str(s.get("name") or "").strip()
        if not (0 <= x < w and 0 <= y < h):
            p.warnings.append(f"{name or 'a settlement'} is off the map, and is left out")
            continue
        at = _nearest_land(land, w, h, x, y, MOVE_REACH)
        if at is None:
            p.warnings.append(f"{name or 'a settlement'} is at sea, with no land within "
                              f"{MOVE_REACH} tiles, and is left out")
            continue
        if at != (x, y):
            p.warnings.append(f"{name or 'a settlement'} stood on the sea at {x},{y}; it "
                              f"is moved to the nearest land, {at[0]},{at[1]}")
        if any(abs(at[0] - a) + abs(at[1] - b) <= 1 for a, b in taken):
            p.warnings.append(f"{name or 'a settlement'} is next to another city, and "
                              "is left out (a city needs its own tiles round it)")
            continue
        taken.add(at)
        seats.append({"name": name, "seat": at, "faction": s.get("faction"),
                      "want_port": s.get("port", True) is not False})
    if picks and not seats:
        raise NewMapError("none of the settlements picked stands on this map's land")
    if not picks:
        for i in _seed_tiles(land, w, h, n_auto):
            seats.append({"name": "", "seat": (i % w, i // w), "faction": None,
                          "want_port": True})
    if len(seats) > 199:
        raise NewMapError(f"{len(seats)} settlements is more than a map can hold (199)")
    owner = _grow(land, w, h, [y * w + x for x, y in (s["seat"] for s in seats)])
    joined = _join_islands(land, owner, w, h)
    if joined:
        notes.append(f"{joined:,} tile(s) of land no city walks to (islands) joined to "
                     f"the province nearest across the water")
    ports = 0
    for k, s in enumerate(seats):
        if s["want_port"]:
            s["port"] = _port(land, owner, w, h, k, s["seat"], taken)
            if s["port"]:
                taken.add(s["port"])
                ports += 1
    notes.append(f"{len(seats)} province(s) grown from their cities over the land, "
                 f"{ports} with a port on the coast")

    # the corners
    land_c = corner_view(Image.frombytes("L", (w, h), bytes(255 if v else 0 for v in land)))
    top, deep = _terrain_heights(_terrain(mod, w, h))
    grey = ImageChops.lighter(metres.point(lambda v: v * 255.0 / max(top, 1.0) + 0.5).convert("L"),
                              Image.new("L", (cols, rows), 1))
    depth = ImageChops.lighter(metres.point(lambda v: 255.0 - 255.0 * v / min(deep, -1.0) + 0.5)
                               .convert("L"), Image.new("L", (cols, rows), 1))
    zero = Image.new("L", (cols, rows), 0)
    heights = Image.merge("RGB", (zero, zero, depth))
    heights.paste(Image.merge("RGB", (grey, grey, grey)), mask=land_c)
    peak = max((v for v, m in zip(array_of(metres), land_c.tobytes()) if m), default=0.0)
    if peak > top:
        p.warnings.append(f"the highest ground, {peak:,.0f} m, is above this mod's "
                          f"max_land_height ({top:,.0f} m) and is cut off at white")
    g = mapvocab.ground
    ground = Image.new("RGB", (cols, rows), g("sea_deep")["rgb"])
    ground.paste(g("sea_shallow")["rgb"], mask=land_c.filter(ImageFilter.MaxFilter(9)))
    table = [(0, 0, 0)] * 256
    lo = 0
    for code, band_top in mapgen.GROUND_BANDS:
        for v in range(lo, band_top + 1):
            table[v] = g(code)["rgb"]
        lo = band_top + 1
    typed = Image.merge("RGB", tuple(grey.point([table[v][c] for v in range(256)])
                                     for c in range(3)))
    ground.paste(typed, mask=land_c)
    # nothing a city or a port cannot stand on under one (27's bands never make
    # impassable land or dense forest, but the rule is the validator's)
    bad = set(mapvocab.BLOCKING_GROUND) | {"forest_dense"}
    gp = ground.load()
    for s in seats:
        for tile in (s["seat"], s.get("port")):
            if tile is None:
                continue
            x, y = tile
            for cy in range(2 * y, 2 * y + 3):
                for cx in range(2 * x, 2 * x + 3):
                    here = mapvocab.ground_at(gp[cx, cy])
                    if here is None or here["code"] in bad:
                        gp[cx, cy] = g("fertility_medium")["rgb"]

    climates = _climates(mod, p, box, proj, w, h, ground, climate, str(body.get("climates") or "one"),
                         notes)
    features = Image.new("RGB", (w, h), tuple(mapvocab.feature("none")["rgb"]))
    detail = str(body.get("rivers") or "none")
    if detail != "none":
        if detail not in mapgen.RIVER_DETAIL:
            raise mapgen.GenError(f"rivers is none or one of {', '.join(mapgen.RIVER_DETAIL)}")
        blocked = {s["seat"] for s in seats} | {s["port"] for s in seats if s.get("port")}
        sea = bytes(0 if v else 1 for v in land)
        net = mapgen.Rivers(w, h, sea, blocked)
        drawn, tiles, cliffs, volc, short = mapgen.draw_features(
            features.load(), mapgen._osm_features(box, detail), proj, w, h, sea, blocked, net)
        notes.append(f"{drawn} river(s) from OSM, {tiles:,} tiles, a source each, cut at "
                     f"every city; {cliffs} cliff tile(s), {volc} volcano(es)")
    water = Image.new("RGB", (256, 256), (0, 0, 0))
    water.paste((40, 90, 170), mask=Image.frombytes("L", (w, h), bytes(0 if v else 255 for v in land))
                .resize((256, 256), Image.NEAREST))
    imgs = {"heights": heights, "ground_types": ground, "climates": climates,
            "fog": Image.new("RGB", (cols, rows), (255, 255, 255)), "features": features,
            "trade_routes": Image.new("RGB", (w, h), (0, 0, 0)),
            "roughness": Image.new("RGB", (2 * w, 2 * h), (0, 0, 0)),
            "water_surface": water, "_owner": owner, "_land": land}
    return imgs, seats, notes


def _climates(mod, p, box, proj, w, h, ground, climate, how, notes) -> Image.Image:
    cols, rows = 2 * w + 1, 2 * h + 1
    base = Image.new("RGB", (cols, rows), tuple(climate["rgb"]))
    have = {c["code"]: c for c in mapvocab.climates(mod) if c.get("rgb")}
    if how == "one":
        notes.append(f"one climate, {climate['code']}")
        return base
    if how == "ground":
        n = 0
        for gcode, ccode in mapgen.CLIMATE_OF.items():
            c = have.get(ccode)
            if c is None:
                continue
            mask = mapgen._equal(ground, mapvocab.ground(gcode)["rgb"])
            base.paste(tuple(c["rgb"]), mask=mask)
            n += 1
        notes.append(f"climates from the ground types ({n} of this mod's climates), "
                     f"{climate['code']} elsewhere")
        return base
    if how == "koppen":
        from . import mapreal
        env = box.envelope()
        sw, sh = mapreal._merc_size(env, cols, rows, over=1.5)
        st = mapreal.settings()
        if st["koppen_file"]:
            codes = mapreal.koppen_from_file(st["koppen_file"], env, sw, sh)
        elif st["koppen_wms"]:
            codes = mapreal.classify(mapreal.wms(st["koppen_wms"], env, sw, sh, "Köppen"),
                                     [(i + 1, rgb) for i, (_, rgb, _) in enumerate(mapreal.KOPPEN)])
        else:
            raise mapgen.GenError("Köppen climates need the Köppen-Geiger map's file (or a "
                                  "WMS) in Settings, Real-world map")
        at = mapreal._to_corners(codes, env, proj, cols, rows)
        n = 0
        for i, (code, _, clim) in enumerate(mapreal.KOPPEN):
            c = have.get(clim)
            if c is not None:
                base.paste(tuple(c["rgb"]), mask=at.point(lambda v, k=i + 1: 255 if v == k else 0))
                n += 1
        notes.append(f"climates from the Köppen-Geiger zones, {climate['code']} where "
                     f"there is no zone or no climate for it")
        return base
    raise mapgen.GenError("climates is one, ground or koppen")


def _regions(owner: List[int], land: bytearray, w: int, h: int, colours, seats, ports) -> Image.Image:
    reg = bytearray(bytes(SEA_REGION) * (w * h))
    for i, o in enumerate(owner):
        if o >= 0 and land[i]:
            reg[3 * i:3 * i + 3] = bytes(colours[o])
    for x, y in seats:
        i = y * w + x
        reg[3 * i:3 * i + 3] = bytes(mapvocab.SETTLEMENT_RGB)
    for at in ports:
        if at:
            i = at[1] * w + at[0]
            reg[3 * i:3 * i + 3] = bytes(mapvocab.PORT_RGB)
    return Image.frombytes("RGB", (w, h), bytes(reg))


def array_of(img: Image.Image):
    from array import array
    return array("f", img.tobytes())
