"""A faction's battle banners painted new: colours, a pattern and a symbol (96e6).

Taken from the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW / M2TW
Campaign Editor's ``banners_m2.py`` and ``banners.py``, with its author's
permission, and fitted to this toolkit's readers and its plan / apply.

**The white template.** Medieval II has no white banner: every faction sheet
(``banners/textures/faction_banner_<faction>.texture``, 1024 x 512) carries its
heraldry. But every faction shares one sheet layout, and the banner meshes of
``descr_banners_new.xml`` lay their cloth on the same places of every sheet. So
the template is taken from the mod's own sheets: per pixel, each sheet's light
against its own neighbourhood (the colour out, the folds and stitching kept),
and the median over all of them - each faction's heraldry is somewhere else, so
it vanishes, while what they share stays. Pixels alike in nearly every sheet
(the wood, the finials, the trim) are not cloth and keep their colour. The
cloth is what one banner mesh alone shows of the sheet, less those. The small
pennants' other three looks (a quarter across, half down) are found where the
sheets' see-through shape repeats the first, and painted as copies of it; the
cavalry banner's slit, a line no mesh shows, is filled so the symbol has no seam.

**Painting.** The cloth dyed in one colour or a pattern of two or three, its
folds kept; the symbol (any picture with a clear ground) laid on each banner in
its upper middle, shaded by the cloth; the see-through parts the template's.

**Where it goes.** A sheet only this faction uses is written over; a sheet it
shares becomes its own ``faction_banner_<slot>.texture`` and its rows in
``descr_banners_new.xml`` point at it. Backups and a log record, so Undo works.
"""
from __future__ import annotations

import base64
import io
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, gamepack
from . import i18n as _i18n
from .logutil import file_op, log

XML_REL = "descr_banners_new.xml"
BLOCK = 48
SAME_WITHIN = 18
SAME_SHARE = 0.70
WHITE = 210
NOT_FACTIONS = ("ally", "enemy", "test_", "_trans")
MIN_PANEL = 0.004
VARIANT_SHIFTS = ((0.25, 0.0), (0.0, 0.5), (0.25, 0.5))
SHAPE_ALIKE = 0.90
SLIT_CLOSE = 9
SLIT_LONG = 32

#: name -> (how many colours, which colour a point (u, v) of a banner takes)
PATTERNS = {
    "plain": (1, lambda u, v: 0),
    "two stripes, upright": (2, lambda u, v: int(u * 2)),
    "three stripes, upright": (3, lambda u, v: int(u * 3)),
    "two stripes, across": (2, lambda u, v: int(v * 2)),
    "three stripes, across": (3, lambda u, v: int(v * 3)),
    "halves, slanting /": (2, lambda u, v: 0 if u + v < 1 else 1),
    "halves, slanting \\": (2, lambda u, v: 0 if u > v else 1),
    "three bands, slanting": (3, lambda u, v: min(2, int((u + v) * 1.5))),
    "quarters": (2, lambda u, v: (u >= 0.5) ^ (v >= 0.5)),
    "a cross": (2, lambda u, v: 1 if abs(u - 0.5) < 0.1 or abs(v - 0.4) < 0.08 else 0),
    "a slanting cross": (2, lambda u, v: 1 if abs(u - v) < 0.1 or abs(u + v - 1) < 0.1 else 0),
    "a border": (2, lambda u, v: 1 if min(u, 1 - u, v, 1 - v) < 0.1 else 0),
    "a stripe in the middle, upright": (2, lambda u, v: 1 if abs(u - 0.5) < 0.17 else 0),
    "a stripe in the middle, across": (2, lambda u, v: 1 if abs(v - 0.5) < 0.12 else 0),
}

_cache: Dict = {}
_lock = threading.Lock()


class BannerError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# reading


def _xml(mod) -> str:
    p, _ = gamepack.lookup(XML_REL, mod)
    return p.read_text(encoding="latin-1") if p else ""


def _clean_ref(ref: str) -> str:
    ref = ref.replace("\\", "/")
    return ref[5:] if ref.lower().startswith("data/") else ref


def faction_sheet(name: str) -> bool:
    low = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return low.startswith("faction_banner_") and not any(k in low for k in NOT_FACTIONS)


def read_picture(path: Path):
    """A .texture (a DDS with the game's header), .dds, .tga or .png, as RGBA."""
    from PIL import Image
    from . import sprites
    raw = Path(path).read_bytes()
    if Path(path).suffix.lower() == ".texture":
        raw = sprites.texture_to_dds(raw)
    im = Image.open(io.BytesIO(raw))
    im.load()
    return im.convert("RGBA")


def sheet_refs(text: str) -> List[str]:
    seen, out = set(), []
    for ref in re.findall(r'DiffuseMap="([^"]+)"', text):
        if faction_sheet(ref) and ref.lower() not in seen:
            seen.add(ref.lower())
            out.append(_clean_ref(ref))
    return out


def mesh_refs(mod, text: str) -> List[Tuple[str, Path]]:
    out: List[Tuple[str, Path]] = []
    for m in re.finditer(r"<Banner\b([^>]*)>(.*?)</Banner>", text, re.S):
        if not any(faction_sheet(r) for r in re.findall(r'DiffuseMap="([^"]+)"', m.group(2))):
            continue
        for kind, ref in re.findall(r'(Main|Mini|General|Building)Mesh="([^"]+)"', m.group(1)):
            p, _ = gamepack.lookup(_clean_ref(ref), mod)
            if p and all(p != q for _, q in out):
                out.append((kind, p))
    return out


# ---------------------------------------------------------------------------
# the white template


class Sheet:
    def __init__(self, blank, shade, cloth, panels, count, copies=()):
        self.blank, self.shade, self.cloth, self.panels, self.count = blank, shade, cloth, panels, count
        self.copies = list(copies)

    @property
    def size(self):
        return self.blank.size


def _light(im):
    """'L': the sheet's light against its own neighbourhood, 128 = as light as
    the cloth round it. The neighbourhood is averaged over the opaque pixels
    only, so cloth beside a see-through gap is not read as glaring (the
    editor's average counted the gap as black)."""
    from PIL import Image, ImageChops, ImageMath
    lum = im.convert("L")
    w, h = lum.size
    solid = im.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    small = (max(1, w // BLOCK), max(1, h // BLOCK))
    lit = ImageChops.multiply(lum, solid).resize(small, Image.BOX).resize((w, h), Image.BILINEAR)
    cover = solid.resize(small, Image.BOX).resize((w, h), Image.BILINEAR)
    return ImageMath.lambda_eval(
        lambda e: e["convert"](e["a"] * 128 * e["max"](e["c"], 1) / e["max"](e["b"] * 255, 8 * 255) , "L"),
        a=lum, b=lit, c=cover)


def _median(bands):
    from PIL import Image
    if len(bands) == 1:
        return bands[0].copy()
    try:
        import numpy as np
        stack = np.stack([np.asarray(b, dtype=np.uint8) for b in bands])
        return Image.fromarray(np.sort(stack, axis=0)[len(bands) // 2])
    except ImportError:
        mid = len(bands) // 2
        data = bytes(sorted(t)[mid] for t in zip(*(b.tobytes() for b in bands)))
        return Image.frombytes("L", bands[0].size, data)


def _mesh_mask(path: Path, size):
    from PIL import Image, ImageDraw
    from . import mesh
    w, h = size
    m = Image.new("L", size, 0)
    try:
        mf = mesh.read_mesh(path)
    except Exception:  # noqa: BLE001 - a mesh that will not read shows no cloth
        return m
    uv = mf.uvs
    if not uv:
        return m
    dr = ImageDraw.Draw(m)
    # mesh.read_mesh doubles u (the unit convention of a main sheet and an
    # attachment sheet side by side); a banner lays its u over ONE sheet
    for g in mf.groups:
        t = g.indices
        for i in range(0, len(t) - 2, 3):
            dr.polygon([(uv[2 * k] * 0.5 * w, uv[2 * k + 1] * h) for k in t[i:i + 3]], fill=255)
    return m


def _union(masks, size):
    from PIL import Image, ImageChops
    out = Image.new("L", size, 0)
    for m in masks:
        out = ImageChops.lighter(out, m)
    return out


def _clean(mask):
    from PIL import ImageFilter
    m = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    return m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))


def panels_of(cloth):
    from PIL import Image
    w, h = cloth.size
    k = 8
    sw, sh = max(1, w // k), max(1, h // k)
    small = cloth.resize((sw, sh), Image.BOX).point(lambda v: 1 if v >= 96 else 0)
    px = list(small.tobytes())
    seen = [False] * len(px)
    out = []
    for start in range(len(px)):
        if not px[start] or seen[start]:
            continue
        stack, n = [start], 0
        seen[start] = True
        x0, y0, x1, y1 = sw, sh, 0, 0
        while stack:
            i = stack.pop()
            n += 1
            x, y = i % sw, i // sw
            x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
            for j in (i - 1 if x else -1, i + 1 if x + 1 < sw else -1, i - sw, i + sw):
                if 0 <= j < len(px) and px[j] and not seen[j]:
                    seen[j] = True
                    stack.append(j)
        if n >= MIN_PANEL * sw * sh:
            out.append((n, (x0 * k, y0 * k, min(w, (x1 + 1) * k), min(h, (y1 + 1) * k))))
    return [b for _, b in sorted(out, key=lambda t: -t[0])]


def own_cloth(masks, same, size):
    from PIL import Image, ImageChops
    if not masks:
        return Image.new("L", size, 0), []
    count = Image.new("L", size, 0)
    for m in masks:
        count = ImageChops.add(count, m.point(lambda v: 1 if v > 128 else 0))
    single = count.point(lambda v: 255 if v == 1 else 0)
    keep = ImageChops.subtract(single, same)
    owns, panels = [], []
    for m in masks:
        own = _clean(ImageChops.multiply(m, keep))
        boxes = panels_of(own)
        if not boxes:
            continue
        box = Image.new("L", size, 0)
        box.paste(255, boxes[0])
        owns.append(ImageChops.multiply(own, box))
        if boxes[0] not in panels:
            panels.append(boxes[0])
    return _union(owns, size), panels


def _pieces(mask):
    w, _h = mask.size
    px = mask.tobytes()
    seen = bytearray(len(px))
    out = []
    for start in range(len(px)):
        if px[start] < 128 or seen[start]:
            continue
        seen[start] = 1
        stack, pts = [start], []
        while stack:
            i = stack.pop()
            x, y = i % w, i // w
            pts.append((x, y))
            for j in (i - 1 if x else -1, i + 1 if x + 1 < w else -1, i - w, i + w):
                if 0 <= j < len(px) and px[j] >= 128 and not seen[j]:
                    seen[j] = 1
                    stack.append(j)
        out.append(pts)
    return out


def fill_slits(cloth, panels):
    from PIL import ImageChops, ImageFilter, ImageOps
    out = cloth.copy()
    m = SLIT_CLOSE
    for box in panels:
        part = ImageOps.expand(cloth.crop(box).point(lambda v: 255 if v > 128 else 0), border=m, fill=0)
        closed = part.filter(ImageFilter.MaxFilter(SLIT_CLOSE)).filter(ImageFilter.MinFilter(SLIT_CLOSE))
        added = ImageChops.subtract(closed, part).crop((m, m, m + box[2] - box[0], m + box[3] - box[1]))
        for pts in _pieces(added):
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            long_, short = sorted((max(xs) - min(xs) + 1, max(ys) - min(ys) + 1), reverse=True)
            if long_ >= SLIT_LONG and long_ >= 6 * short:
                for x, y in pts:
                    out.putpixel((box[0] + x, box[1] + y), 255)
    return out


def variant_copies(panels, cloth, alpha, small_meshes):
    from PIL import ImageChops
    w, h = cloth.size
    solid = alpha.point(lambda v: 255 if v > 128 else 0)
    taken = cloth.point(lambda v: 255 if v > 128 else 0)
    out = []
    for i, (x0, y0, x1, y1) in enumerate(panels):
        if not any(m.crop((x0, y0, x1, y1)).getbbox() for m in small_meshes):
            continue
        src = solid.crop((x0, y0, x1, y1))
        for fx, fy in VARIANT_SHIFTS:
            dx, dy = int(round(fx * w)), int(round(fy * h))
            box = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
            if box[2] > w or box[3] > h:
                continue
            if taken.crop(box).histogram()[255] > 0.02 * (x1 - x0) * (y1 - y0):
                continue
            diff = ImageChops.difference(src, solid.crop(box)).histogram()[255]
            if diff <= (1 - SHAPE_ALIKE) * (x1 - x0) * (y1 - y0):
                out.append((i, dx, dy))
    return out


def make_sheet(pictures, mesh_paths=(), mini_paths=()) -> Sheet:
    from PIL import Image, ImageChops
    pics = [p.convert("RGBA") for p in pictures]
    pics = [p for p in pics if p.size == pics[0].size]
    size = pics[0].size
    shade = _median([_light(p) for p in pics]).point(lambda v: min(255, v * WHITE // 128))
    bands = [_median([p.getchannel(c) for p in pics]) for c in range(4)]
    med = Image.merge("RGBA", bands)
    need = max(1, round(SAME_SHARE * len(pics)))
    count = Image.new("L", size, 0)
    rgb = med.convert("RGB")
    for p in pics:
        d = ImageChops.difference(p.convert("RGB"), rgb).split()
        far = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2])
        count = ImageChops.add(count, far.point(lambda v: 1 if v < SAME_WITHIN else 0))
    same = count.point(lambda v: 255 if v >= need else 0) if len(pics) > 2 else Image.new("L", size, 0)
    all_masks = [(p, _mesh_mask(p, size)) for p in mesh_paths]
    masks = [m for _p, m in all_masks if m.getbbox()]
    cloth, panels = own_cloth(masks, same, size)
    copies = []
    if not panels:
        cloth = _clean(ImageChops.subtract(bands[3].point(lambda v: 255 if v > 128 else 0), same))
        panels = panels_of(cloth)
    else:
        cloth = fill_slits(cloth, panels)
        small = [m for p, m in all_masks if p in mini_paths]
        copies = variant_copies(panels, cloth, bands[3], small)
        for i, dx, dy in copies:
            x0, y0, x1, y1 = panels[i]
            moved = cloth.crop((x0, y0, x1, y1))
            cloth.paste(ImageChops.lighter(cloth.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy)), moved),
                        (x0 + dx, y0 + dy))
    white = Image.merge("RGBA", (shade, shade, shade, bands[3]))
    blank = Image.composite(white, med, cloth)
    return Sheet(blank, shade, cloth, panels, len(pics), copies)


def template(mod) -> Optional[Sheet]:
    """The mod's white template, kept while its sheets and meshes are unchanged."""
    text = _xml(mod)
    paths = [p for p in (gamepack.lookup(r, mod)[0] for r in sheet_refs(text)) if p]
    if not paths:
        return None
    refs = mesh_refs(mod, text)
    ms = [p for _, p in refs]
    key = (str(getattr(mod, "root", "")), tuple((str(p), p.stat().st_mtime) for p in paths + ms))
    with _lock:
        if _cache.get("key") == key:
            return _cache["sheet"]
    pics = []
    for p in paths:
        try:
            pics.append(read_picture(p))
        except Exception:  # noqa: BLE001 - a sheet that will not read is left out of the median
            pass
    sheet = make_sheet(pics, ms, [p for k, p in refs if k == "Mini"]) if pics else None
    with _lock:
        _cache.clear()
        _cache.update(key=key, sheet=sheet)
    return sheet


# ---------------------------------------------------------------------------
# painting


def _all_cloth(cloth, box, step=4):
    x0, y0, x1, y1 = box
    pts = [(x, y) for x in range(x0, x1, step) for y in range(y0, y1, step)]
    if not pts:
        return True
    w, h = cloth.size
    inside = sum(1 for x, y in pts if 0 <= x < w and 0 <= y < h and cloth.getpixel((x, y)) > 128)
    return inside >= 0.97 * len(pts)


def _square_in_cloth(cloth, panel, centre, most, k=4):
    from PIL import Image
    x0, y0, x1, y1 = panel
    sw, sh = max(1, (x1 - x0) // k), max(1, (y1 - y0) // k)
    small = cloth.crop(panel).resize((sw, sh), Image.BOX)
    on = [[small.getpixel((x, y)) >= 200 for x in range(sw)] for y in range(sh)]
    size = [[0] * sw for _ in range(sh)]
    best = 0
    for y in range(sh):
        for x in range(sw):
            if on[y][x]:
                size[y][x] = 1 if not x or not y else 1 + min(size[y - 1][x], size[y][x - 1], size[y - 1][x - 1])
                best = max(best, size[y][x])
    if not best:
        return None
    n = min(best, max(1, most // k))
    pick = None
    for y in range(sh):
        for x in range(sw):
            if size[y][x] >= n:
                mx = x0 + (x - n + 1 + n / 2.0) * k
                my = y0 + (y - n + 1 + n / 2.0) * k
                d = (mx - centre[0]) ** 2 + (my - centre[1]) ** 2
                if pick is None or d < pick[0]:
                    pick = (d, mx, my)
    side = int(n * k * 0.85)
    _, mx, my = pick
    return (int(mx - side / 2), int(my - side / 2), int(mx - side / 2) + side, int(my - side / 2) + side)


def symbol_boxes(sheet: Sheet):
    out = []
    for x0, y0, x1, y1 in sheet.panels:
        bw, bh = x1 - x0, y1 - y0
        side = min(int(bw * 0.6), int(bh * 0.5))
        cx, cy = (x0 + x1) // 2, y0 + int(bh * 0.42)
        box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
        if not _all_cloth(sheet.cloth, box):
            box = _square_in_cloth(sheet.cloth, (x0, y0, x1, y1), (cx, cy), side) or box
        out.append(box)
    return out


def put_symbol(out, light, symbol, boxes, strength=1.0):
    from PIL import Image, ImageChops, ImageStat
    from .emblem import footprint
    sym = symbol.convert("RGBA")
    fb = footprint(sym)
    if fb:
        sym = sym.crop((fb[0], fb[1], fb[0] + fb[2], fb[1] + fb[3]))
    for bx0, by0, bx1, by1 in boxes:
        bw, bh = bx1 - bx0, by1 - by0
        if bw < 2 or bh < 2:
            continue
        k = min(bw / sym.size[0], bh / sym.size[1])
        s = sym.resize((max(1, round(sym.size[0] * k)), max(1, round(sym.size[1] * k))), Image.LANCZOS)
        at = (bx0 + (bw - s.size[0]) // 2, by0 + (bh - s.size[1]) // 2)
        under = light.crop((at[0], at[1], at[0] + s.size[0], at[1] + s.size[1]))
        base = max(1.0, ImageStat.Stat(under).mean[0])
        shade = under.point(lambda v: min(255, int(255 * min(1.6, max(0.4, v / base)) / 1.6)))
        r, g, b, a = s.split()
        lit = [ImageChops.multiply(c, shade).point(lambda v: min(255, int(v * 1.6))) for c in (r, g, b)]
        if strength < 1:
            a = a.point(lambda v: int(v * strength))
        s = Image.merge("RGBA", lit + [a])
        layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        layer.paste(s, at)
        out.alpha_composite(layer)
    return out


def _colour_layer(sheet: Sheet, colours, pattern):
    from PIL import Image
    n, which = PATTERNS.get(pattern, PATTERNS["plain"])
    layer = Image.new("RGB", sheet.size, tuple(colours[0][:3]))
    if n == 1:
        return layer
    for x0, y0, x1, y1 in sheet.panels:
        bw, bh = max(1, (x1 - x0) // 4), max(1, (y1 - y0) // 4)
        small = Image.new("RGB", (bw, bh))
        sp = small.load()
        for y in range(bh):
            for x in range(bw):
                i = min(int(which(x / bw, min(0.999, y / bh))), len(colours) - 1)
                sp[x, y] = tuple(colours[i][:3])
        layer.paste(small.resize((x1 - x0, y1 - y0), Image.NEAREST), (x0, y0))
    return layer


def paint(sheet: Sheet, colours, symbol=None, pattern="plain"):
    from PIL import Image, ImageChops
    col = _colour_layer(sheet, colours, pattern)
    shade = Image.merge("RGB", (sheet.shade,) * 3)
    dyed = ImageChops.multiply(col, shade).point(lambda v: min(255, v * 255 // WHITE))
    out = sheet.blank.copy()
    out.paste(dyed, (0, 0), sheet.cloth)
    if symbol is not None:
        put_symbol(out, sheet.shade, symbol, symbol_boxes(sheet))
    for i, dx, dy in sheet.copies:
        x0, y0, x1, y1 = sheet.panels[i]
        out.paste(out.crop((x0, y0, x1, y1)), (x0 + dx, y0 + dy), sheet.cloth.crop((x0, y0, x1, y1)))
    out.putalpha(sheet.blank.getchannel("A"))
    return out


# ---------------------------------------------------------------------------
# plan and apply


def _hex(c: str) -> Tuple[int, int, int]:
    c = (c or "").strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        raise BannerError(_i18n.msg("eng.bannermaker.bad_colour", "{c} is not a colour like #c81e1e", c=c or "''"))
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _symbol(b64: str):
    if not b64:
        return None
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(base64.b64decode(b64)))
        im.load()
        return im.convert("RGBA")
    except (OSError, ValueError, SyntaxError):
        raise BannerError(_i18n.msg("eng.bannermaker.bad_symbol", "the symbol is not a picture this can read")) from None


def _faction_rows(text: str, slot: str) -> List[re.Match]:
    return [m for m in re.finditer(r'<Texture\b[^>]*\bFaction="([^"]+)"[^>]*>', text)
            if m.group(1).lower() == slot.lower()]


def target_of(text: str, slot: str) -> Tuple[str, bool]:
    """(the sheet this faction's banners use, whether another faction uses it too)."""
    mine = [re.search(r'DiffuseMap="([^"]+)"', m.group(0)) for m in _faction_rows(text, slot)]
    refs = [x.group(1) for x in mine if x and faction_sheet(x.group(1))]
    if not refs:
        return "", False
    ref = refs[0]
    others = [m for m in re.finditer(r'<Texture\b[^>]*\bFaction="([^"]+)"[^>]*DiffuseMap="([^"]+)"', text)
              if m.group(2).lower() == ref.lower() and m.group(1).lower() != slot.lower()]
    return ref, bool(others)


def _settings(body: dict):
    pattern = body.get("pattern")
    if isinstance(pattern, int) or str(pattern or "").isdigit():
        names = list(PATTERNS)            # the page sends a pattern by its number
        pattern = names[int(pattern)] if int(pattern) < len(names) else str(pattern)
    pattern = str(pattern or "plain")
    if pattern not in PATTERNS:
        raise BannerError(_i18n.msg("eng.bannermaker.bad_pattern", "no pattern called {p}", p=pattern))
    colours = [_hex(c) for c in (body.get("colours") or [])][:3]
    if not colours:
        raise BannerError(_i18n.msg("eng.bannermaker.no_colour", "pick at least one colour"))
    while len(colours) < PATTERNS[pattern][0]:
        colours.append(colours[-1])
    return colours, pattern, _symbol(str(body.get("symbol") or ""))


def plan(mod, body: dict) -> Dict:
    """The painted sheet, previewed, and where it would be written. Writes nothing."""
    slot = str(body.get("faction") or "").strip()
    sheet = template(mod)
    if sheet is None:
        raise BannerError(_i18n.msg("eng.bannermaker.no_sheets", "this mod names no faction banner sheets in {rel}, so there is no template to paint", rel=XML_REL))
    colours, pattern, symbol = _settings(body)
    out = paint(sheet, colours, symbol, pattern)
    text = _xml(mod)
    ref, shared = target_of(text, slot)
    new_ref = f"banners\\textures\\faction_banner_{slot}.texture" if (shared or not ref) else ref
    small = out.copy()
    small.thumbnail((768, 384))
    buf = io.BytesIO()
    small.save(buf, "PNG")
    tpl = sheet.blank.copy()
    tpl.thumbnail((384, 192))
    tbuf = io.BytesIO()
    tpl.save(tbuf, "PNG")
    return {"faction": slot, "sheets": sheet.count, "panels": len(sheet.panels), "copies": len(sheet.copies),
            "preview": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
            "template": "data:image/png;base64," + base64.b64encode(tbuf.getvalue()).decode("ascii"),
            "target": _clean_ref(new_ref), "was": _clean_ref(ref), "shared": shared,
            "patterns": list(PATTERNS)}


def apply(mod, body: dict) -> Dict:
    from . import armbake, sprites
    p = plan(mod, body)
    sheet = template(mod)
    colours, pattern, symbol = _settings(body)
    out = paint(sheet, colours, symbol, pattern)
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = data / rel
        if target.exists():
            b = backup_root / "data" / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, b)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {b}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    target = keep(p["target"])
    raw = sprites.dds_to_texture(armbake.dds_with_mipmaps(out))
    tmp = target.with_name(target.name + ".new")
    tmp.write_bytes(raw)
    tmp.replace(target)
    file_op("WRITE", target, f"{len(raw)} bytes")
    if p["target"].lower() != p["was"].lower():
        text = _xml(mod)
        old = p["was"].replace("/", "\\")
        new = p["target"].replace("/", "\\")
        rows = _faction_rows(text, p["faction"])
        for m in reversed(rows):
            row = m.group(0)
            fixed = re.sub(r'(DiffuseMap=")([^"]+)(")',
                           lambda g: g.group(1) + (new if _clean_ref(g.group(2)).lower() == p["was"].lower() or not old else g.group(2)) + g.group(3),
                           row)
            text = text[:m.start()] + fixed + text[m.end():]
        xml = keep(XML_REL)
        xml.write_bytes(text.encode("latin-1"))
        file_op("WRITE", xml, "banner rows point at the faction's own sheet")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "factions",
           "action": "banners", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": p["faction"],
           "resolved_type": p["faction"], "options": {}, "applied": True, "undone": False, "note": "",
           "summary": _i18n.msg("eng.bannermaker.summary", "new battle banners for {faction} in {rel}", faction=p["faction"], rel=p["target"]),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("BANNER %s in %s -> %s, id=%s", p["faction"], mod.name, p["target"], tid)
    return rec
