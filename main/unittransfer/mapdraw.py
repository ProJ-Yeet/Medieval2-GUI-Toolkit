"""A finished picture drawn from the campaign map (96f, "Draw from the map").

:mod:`mapfe` composes the map's raw layers for tracing: nearest neighbour,
province colours as keys, nothing a player should see. This module draws the
picture a player does see - the front-end map, ``map_FE.tga`` - from the same
files, so a mod with a new or changed map has one without painting it:

* **relief**: the land coloured by height (lowland green, upland tan, the
  peaks pale) and shaded from the north-west by the slope, sea in two blues
  by depth;
* **rivers** from ``map_features.tga``;
* **no signs**: no settlements, ports, names or borders;
* and, when a faction is named, **its starting land** (every region whose
  settlement it holds in ``descr_strat.txt``) as one solid patch in its
  primary colour, with a line round the outside only - dark round a bright
  colour, light round a dark one - and no borders inside.

The grid is laid into the picture's own shape the way :func:`mapfe.frame`
lays it (around the map, centred), so a picture drawn at the size of the one
the mod ships drops straight over it.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

from . import campmap, campstrat, mapfe, mapvocab
from . import i18n as _i18n

#: the default size when the campaign ships no front-end picture: two pixels a
#: tile, held to this many a side
DEFAULT_MAX = 1024

SEA_DEEP = (34, 62, 96)
SEA_SHALLOW = (64, 104, 140)
RIVER = (70, 112, 150)

#: land by height, 0..1 of the land's own range: (at, rgb)
_RAMP = ((0.00, (96, 122, 70)), (0.25, (126, 140, 84)), (0.50, (160, 146, 98)),
         (0.75, (138, 116, 88)), (0.92, (190, 182, 170)), (1.00, (236, 234, 228)))


def _ramp(t: np.ndarray) -> np.ndarray:
    at = np.array([a for a, _ in _RAMP])
    cols = np.array([c for _, c in _RAMP], dtype=float)
    return np.stack([np.interp(t, at, cols[:, k]) for k in range(3)], axis=-1)


def owned_regions(mod, campaign: str, faction: str) -> List[str]:
    """The regions whose settlement ``faction`` holds at the campaign's start."""
    sf = campstrat.read_strat(mod, campaign)
    return [n.get("region") or n.name for n in sf.nodes
            if n.kind == "settlement" and campstrat._faction_of(sf, n) == faction
            and (n.get("region") or n.name)]


def relief(cm: "campmap.CampaignMap") -> Tuple[np.ndarray, np.ndarray]:
    """``(rgb, land)`` at one pixel a tile: the shaded relief with rivers, and
    the land mask."""
    w, h = cm.terrain.width, cm.terrain.height
    heights = np.asarray(cm.centres("heights").convert("RGB"), dtype=float)
    sea = np.frombuffer(cm.sea, dtype=np.uint8).reshape(h, w).astype(bool)
    land = ~sea
    z = heights[..., 0]
    lz = z[land] if land.any() else np.array([0.0, 1.0])
    lo, hi = float(lz.min()), float(max(lz.max(), lz.min() + 1))
    t = np.clip((z - lo) / (hi - lo), 0, 1)
    rgb = _ramp(t)
    # shading: the slope towards the light, from the north-west
    # over the heights evened out a tile each way: the raw ones are noisy
    zs = np.pad(z, 1, mode="edge")
    zs = sum(zs[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)) / 9.0
    gy, gx = np.gradient(zs)
    shade = np.clip(1.0 + (-gx - gy) * 0.03, 0.65, 1.3)
    rgb = rgb * shade[..., None]
    # sea: shallow beside the land, deep away from it
    near = np.asarray(Image.fromarray((land * 255).astype(np.uint8))
                      .filter(ImageFilter.MaxFilter(5)), dtype=bool)
    rgb[sea] = SEA_DEEP
    rgb[sea & near] = SEA_SHALLOW
    try:
        feat = np.asarray(campmap.tile_view(cm, "features").convert("RGB"))
        river = np.zeros((h, w), dtype=bool)
        for code in mapvocab.RIVER_CODES:
            f = mapvocab.feature(code)
            if f:
                river |= np.all(feat == np.array(f["rgb"]), axis=-1)
        rgb[river & land] = RIVER
    except (campmap.MapError, OSError, ValueError):
        pass
    return np.clip(rgb, 0, 255).astype(np.uint8), land


def land_mask(cm: "campmap.CampaignMap", regions: Sequence[str]) -> np.ndarray:
    """One bool a tile: inside one of ``regions``."""
    idx = cm.index
    want = {r.lower() for r in regions}
    keep = np.zeros(len(idx.colours), dtype=bool)
    for k, rgb in enumerate(idx.colours):
        reg = idx.by_key.get(mapvocab.key(rgb))
        if reg is not None and reg.name.lower() in want:
            keep[k] = True
    # bytes up to 256 colours, a 16-bit array past it (RegionIndex.labels)
    raw = idx.labels
    labels = (np.frombuffer(raw, dtype=np.uint8) if isinstance(raw, (bytes, bytearray))
              else np.asarray(raw, dtype=np.int64)).reshape(idx.height, idx.width)
    return keep[labels]


def _hex(colour: str) -> Tuple[int, int, int]:
    c = (colour or "").strip().lstrip("#")
    if len(c) != 6:
        return (180, 40, 40)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def draw(mod, campaign: str, faction: str = "", colour: str = "",
         size: Optional[Tuple[int, int]] = None) -> Image.Image:
    """The picture, at ``size`` (the shipped front-end picture's when not
    given). ``faction``'s starting land is laid over it in ``colour``."""
    cm = campmap.campaign_map(mod, campaign)
    grid = (cm.terrain.width, cm.terrain.height)
    if size is None:
        pic = mapfe.picture(mapfe.fe_map(mod, campaign, cm))
        if pic is not None:
            size = (pic.width, pic.height)
        else:
            k = min(2.0, DEFAULT_MAX / max(grid))
            size = (max(1, round(grid[0] * k)), max(1, round(grid[1] * k)))
    w, h = size
    if not (0 < w <= mapfe.MAX_SIDE and 0 < h <= mapfe.MAX_SIDE):
        raise mapfe.FeError(_i18n.msg("eng.mapfe.x_is_not_a_size_this", "{w}x{h} is not a size this can compose - it is 1 to {MAX_SIDE} a side", w=w, h=h, MAX_SIDE=mapfe.MAX_SIDE))
    fr = mapfe.frame(grid, size)

    rgb, land = relief(cm)
    # the grid laid into the picture's shape, sea round the short edge
    pad = Image.new("RGB", (round(fr.w), round(fr.h)), SEA_DEEP)
    ox, oy = round(-fr.x), round(-fr.y)
    pad.paste(Image.fromarray(rgb), (ox, oy))
    out = pad.resize((w, h), Image.BICUBIC)

    if faction:
        mask = land_mask(cm, owned_regions(mod, campaign, faction))
        mpad = Image.new("L", pad.size, 0)
        mpad.paste(Image.fromarray((mask * 255).astype(np.uint8)), (ox, oy))
        m = mpad.resize((w, h), Image.BILINEAR).point(lambda v: 255 if v >= 128 else 0)
        col = _hex(colour)
        patch = Image.new("RGB", (w, h), col)
        out = Image.composite(Image.blend(out, patch, 0.72), out, m)
        # the outside line only: the mask grown, less the mask
        thick = max(3, (min(w, h) // 256) * 2 + 1)
        ring = Image.fromarray(np.asarray(m.filter(ImageFilter.MaxFilter(thick)), dtype=np.int16)
                               .__sub__(np.asarray(m, dtype=np.int16)).clip(0, 255).astype(np.uint8))
        bright = (col[0] * 299 + col[1] * 587 + col[2] * 114) / 1000 > 128
        line = Image.new("RGB", (w, h), (24, 20, 16) if bright else (240, 236, 222))
        out = Image.composite(line, out, ring)
    return out


def png(img: Image.Image) -> bytes:
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def view(mod, campaign: str, faction: str = "") -> Dict:
    """What the page shows beside the picture: its size, the regions the
    faction starts with, and where it would be written."""
    cm = campmap.campaign_map(mod, campaign)
    fe = mapfe.view(mod, campaign, cm)
    regions = owned_regions(mod, campaign, faction) if faction else []
    return {"campaign": campaign, "file": fe.get("file"), "rel": fe.get("rel"),
            "present": fe.get("present"), "native": fe.get("native"),
            "regions": regions}


def rel_for(campaign: str, faction: str) -> str:
    """Where the faction-select screen looks for this faction's map: the
    campaign's own ``map_<faction>.tga``, before it falls back to the base
    ``map_FE.tga``."""
    return f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.campaign_rel(campaign)}/map_{faction}.tga"


def apply(mod, campaign: str, faction: str, colour: str) -> Dict:
    """Write the faction's select-screen map, backed up first; one Undo."""
    import shutil
    import time
    from pathlib import Path
    from . import config
    from .logutil import file_op, log
    if not faction:
        raise mapfe.FeError(_i18n.msg("eng.mapdraw.no_faction", "a faction is needed to draw its map"))
    img = draw(mod, campaign, faction, colour)
    rel = rel_for(campaign, faction)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    target = Path(mod.data) / rel
    if target.exists():
        b = backup_root / "data" / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, b)
        manifest["backed_up"].append(rel)
        file_op("BACKUP", target, f"-> {b}")
    else:
        manifest["created"].append(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".new")
    img.convert("RGBA").save(tmp, "TGA")
    tmp.replace(target)
    file_op("WRITE", target, f"{img.width}x{img.height}, drawn from the map")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "factions",
           "action": "map-drawn", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": faction, "resolved_type": faction,
           "options": {}, "applied": True, "undone": False, "note": "",
           "summary": _i18n.msg("eng.mapdraw.summary", "{faction}'s select-screen map drawn from the campaign map: {rel}", faction=faction, rel=rel),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("MAPDRAW %s in %s -> %s, id=%s", faction, mod.name, rel, tid)
    return rec
