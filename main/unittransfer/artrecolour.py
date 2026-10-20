"""Recolour a faction's pictures from the colours they are painted in to new ones (96e6).

A cloned faction keeps its donor's colours in every picture it copied: the unit
cards, the battle textures, the symbols. This moves the parts painted in one
pair of colours (a faction's primary and secondary in descr_sm_factions.txt)
to another pair, the light and shade kept.

The finding and the painting are the Pfadfinder-Adam (formerly
MasterOogwayHomebrew) RTW / M2TW Campaign Editor's ``recolour.py``, taken
verbatim with its author's permission (from ``RE_RGB`` to ``recolour``). How a
part is found: a pixel is a colour part when it is coloured and its hue is near
the source colour; where the same picture exists in other factions' colours
(the same unit card or texture), only the pixels that differ between them
count, so faces, metal and leather stay. The new colour takes the target's
hue, its saturation and brightness moved by the ratio between the two colours,
so a dark fold of a red cloak becomes a dark fold of a blue one.

What is this toolkit's: which pictures are the faction's (its unit-card and
unit-info folders, the battle textures its modeldb records name, its symbols),
the plan that shows a few before and after, and the write. A texture other
factions also wear is not painted over: the faction gets its own copy,
``<name>_<faction>.texture``, and its records in battle_models.modeldb point
at it. Backups and a log record, so Undo works.
"""
from __future__ import annotations

import base64
import colorsys
import io
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, modeldb
from . import i18n as _i18n
from .logutil import file_op, log

RE_RGB = re.compile(r"red\s+(\d+)\s*,\s*green\s+(\d+)\s*,\s*blue\s+(\d+)", re.I)
SAT_MIN = 0.28          # below: grey, white, skin - not a faction colour
SAT_REL = 0.5           # a part must be at least this share as saturated as the source colour
VAL_MIN = 0.10          # below: shadow
HUE_GAP = 0.10          # how far (of the colour wheel, 0..0.5) a pixel's hue may lie from the source colour
DIFF = 40               # a pixel that differs from the other factions' copy by more counts as a colour part
DIFF_MOST = 0.45        # over this share of differing pixels the copies are different pictures: hue alone



def hsv(rgb):
    return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])


def coloured(rgb):
    """Whether a colour has a hue to look for (not white, grey or black)."""
    h, s, v = hsv(rgb)
    return s >= SAT_MIN and v >= VAL_MIN


def _hue_dist_lut(h0):
    """A lookup table: Pillow hue (0..255) -> distance to h0 on the wheel, 0..128."""
    c = int(round(h0 * 255))
    return [min(abs(h - c), 256 - abs(h - c)) for h in range(256)]


def _near(a, b):
    """Whether two colours have hues near each other (both coloured)."""
    if not a or not b or not coloured(a) or not coloured(b):
        return False
    d = abs(hsv(a)[0] - hsv(b)[0]) % 1.0
    return min(d, 1 - d) <= HUE_GAP * 1.5



def _plain(rgb):
    """A colour with no hue to look for: 'dark' (black, near black), 'light' (white, near white), 'grey', or None."""
    if not rgb or coloured(rgb):
        return None
    v = hsv(rgb)[2]
    return "dark" if v < 0.35 else "light" if v > 0.7 else "grey"


def _like(a, b):
    """Whether two faction colours look alike (near hues, or both black / both white / both grey)."""
    pa = _plain(a)
    return _near(a, b) or (pa is not None and pa == _plain(b))


def _plain_mask(S, V, kind):
    """Where a pixel could be painted in a colour of that kind: dark and dull, light and dull, or mid grey."""
    from PIL import ImageChops
    dull = S.point(lambda s: 255 if s < 0.30 * 255 else 0)
    if kind == "dark":
        val = V.point(lambda v: 255 if v < 0.42 * 255 else 0)
    elif kind == "light":
        val = V.point(lambda v: 255 if v > 0.58 * 255 else 0)
    else:
        val = V.point(lambda v: 255 if 0.25 * 255 < v < 0.8 * 255 else 0)
    return ImageChops.multiply(dull, val)


def masks(im, source, others=(), plain=True):
    """[mask of the primary's parts, mask of the secondary's parts] ('L' images, 255 = recolour) of a picture.
    source = (primary, secondary); a source colour without a hue gives an empty mask. others: [(the same picture in
    another faction's colours, that faction's (primary, secondary))] - a pixel counts only where it differs from
    every other copy whose faction does not wear a colour like it (Denmark's red says nothing about England's red)."""
    from PIL import ImageChops
    rgb = im.convert("RGB")
    H, S, V = rgb.convert("HSV").split()
    lit = V.point(lambda v: 255 if v >= VAL_MIN * 255 else 0)
    diffs = []
    # how far a pixel must differ: DIFF in the light, less in the shade (a dark green and a dark blue fold are
    # near in numbers though plainly other colours - the shaded half of a cloak stayed in the old colour)
    need = V.point(lambda v: max(12, min(DIFF, int(v * 0.4))))
    for o, cols in others:
        if o is None or o.size != im.size:
            continue
        d = ImageChops.difference(rgb, o.convert("RGB")).split()
        d = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2])
        d = ImageChops.subtract(d, need).point(lambda x: 255 if x > 0 else 0)
        diffs.append((d, cols or ()))
    gap = int(HUE_GAP * 255)
    dists = [H.point(_hue_dist_lut(hsv(c)[0])) if c and coloured(c) else None for c in source]
    out = []
    for k, d in enumerate(dists):
        if d is None:
            out.append(_plain_part(im.size, S, V, source[k], diffs if plain else []))
            continue
        smin = max(SAT_MIN, hsv(source[k])[1] * SAT_REL) * 255     # a dull brown is not a bright red
        hue = ImageChops.multiply(lit, d.point(lambda x: 255 if x <= gap else 0))
        m = ImageChops.multiply(hue, S.point(lambda s: 255 if s >= smin else 0))
        # a ruddy face is not a red coat: with no copies to compare (a texture only this faction wears) every skin
        # and hair tone is kept; with copies only the paler skin (an orange-red caparison is the faction's)
        informative = any(not any(_like(source[k], c) for c in cols) for _, cols in diffs)
        skin = None if _skin_colour(source[k]) else _skin(H, S, V, broad=not informative)
        use = [dd for dd, cols in diffs if not any(_like(source[k], c) for c in cols)]
        proven = None                            # differs from every such copy: the faction's colour
        if use:
            proven = use[0]
            for dd in use[1:]:
                proven = ImageChops.multiply(proven, dd)
            if not 0 < proven.histogram()[255] / float(im.size[0] * im.size[1]) <= DIFF_MOST:
                proven = None                    # the copies are other pictures: they prove nothing
        if skin is not None and proven is not None:
            # a face is the same in every copy; what differs in all of them is cloth in the faction's colour, also
            # where its shade is skin-like (a red hood's brown folds stayed red in a black recolour: speckles)
            skin = ImageChops.subtract(skin, proven)
        if skin is not None:
            m = ImageChops.subtract(m, skin)
        # any coloured pixel of the hue - taken only where the other factions' copies show it is the faction's
        # colour (an artist often paints a duller green than the faction's colour says: the cloak came out in patches)
        loose = ImageChops.multiply(hue, S.point(lambda s: 255 if s >= SAT_MIN * 255 else 0))
        if skin is not None:
            loose = ImageChops.subtract(loose, skin)       # faces and hands stay (they differ by the man)
        other = dists[1 - k] if len(dists) > 1 else None
        closer = None
        if other is not None:                    # near both: the nearer one takes it (the primary on a tie)
            closer = ImageChops.subtract(d, other) if k == 0 else ImageChops.subtract(d, other, 1, -1)
            closer = closer.point(lambda x: 255 if x == 0 else 0)
            m = ImageChops.multiply(m, closer)
            loose = ImageChops.multiply(loose, closer)
        same = None
        strict = m
        if use:
            diff = proven if proven is not None else use[0]
            if proven is None:
                for dd in use[1:]:
                    diff = ImageChops.multiply(diff, dd)
            share = diff.histogram()[255] / float(im.size[0] * im.size[1])
            if 0 < share <= DIFF_MOST:
                # differs from most copies (two in three): one other faction whose cloak happens to be of a like
                # shade in places must not leave patches of the old colour
                if len(use) >= 3:
                    many = None
                    for dd in use:
                        one = dd.point(lambda x: 1 if x else 0)
                        many = one if many is None else ImageChops.add(many, one)
                    need = (2 * len(use) + 2) // 3
                    diff = many.point(lambda v: 255 if v >= need else 0)
                m = ImageChops.multiply(loose, diff)
                strict = loose
            # what is the same as in a faction that does not wear this colour is never the faction's colour (a
            # bronze star, a wooden pole, a face) - kept even when most of the picture differs
            # (by most of them: one other faction with a like part by chance must not keep a speck of the old colour)
            votes = None
            for dd in use:
                one = dd.point(lambda x: 0 if x else 1)
                votes = one if votes is None else ImageChops.add(votes, one)
            need = max(1, (len(use) + 1) // 2)
            same = votes.point(lambda v: 255 if v >= need else 0)
            m = ImageChops.subtract(m, same)
            # a cloak another faction happens to wear in a like shade in places would come out in patches: what the
            # comparison kept spreads over the rest of its own colour next to it (never into what most copies share)
            m = _spread(m, ImageChops.subtract(strict, same))
        g = _grow(m, H, S, V, d, gap, closer)
        if skin is not None:
            g = ImageChops.subtract(g, skin)        # the rim grown in never takes a face either
        out.append(ImageChops.subtract(g, same) if same is not None else g)
    if len(out) > 1:                             # grown into each other: the primary keeps its own
        from PIL import ImageChops as _C
        out[1] = _C.subtract(out[1], out[0])
    return out


def _skin_colour(rgb):
    """Whether a faction colour is itself of a skin tone (orange, brown) - then skin cannot be told apart by hue."""
    if not rgb or not coloured(rgb):
        return False
    h, sat, v = hsv(rgb)
    return 0.02 <= h <= 0.11 and sat < 0.75


def _skin(H, S, V, broad=True):
    """Pixels of a skin tone: orange-brown hue, not strongly coloured. broad: hair and the shaded skin too."""
    from PIL import ImageChops
    smax, vmin = (0.62, 0.12) if broad else (0.5, 0.3)
    h = H.point(lambda x: 255 if 0.02 * 255 <= x <= 0.11 * 255 else 0)
    return ImageChops.multiply(ImageChops.multiply(h, S.point(lambda x: 255 if x < smax * 255 else 0)),
                               V.point(lambda x: 255 if x > vmin * 255 else 0))


def _spread(m, inside, rounds=8):
    """m grown step by step over the pixels of 'inside' that touch it (a flood bounded to some pixels a round)."""
    from PIL import ImageChops, ImageFilter
    if not m.getbbox():
        return m
    for _ in range(rounds):
        nxt = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), inside))
        if nxt.histogram()[255] == m.histogram()[255]:
            break
        m = nxt
    return m


def _plain_part(size, S, V, colour, diffs):
    """The parts in a black / white / grey faction colour. No hue tells them apart from iron, cloth or a face, so
    they are found only where the same picture of other factions exists: dull pixels of that lightness that differ
    from every copy whose faction does not wear such a colour too, and not the same as in most of them. Without
    such copies (or when the copies are other pictures) nothing is taken - a black outline is not a black coat."""
    from PIL import Image, ImageChops
    kind = _plain(colour)
    use = [dd for dd, cols in diffs if not any(_like(colour, c) for c in cols)]
    if not kind or not use:
        return Image.new("L", size, 0)
    diff = use[0]
    for dd in use[1:]:
        diff = ImageChops.multiply(diff, dd)
    share = diff.histogram()[255] / float(size[0] * size[1])
    if not 0 < share <= DIFF_MOST:
        return Image.new("L", size, 0)
    from PIL import ImageFilter
    could = _plain_mask(S, V, kind)
    m = ImageChops.multiply(could, diff)
    # specks taken away (a dark shadow pixel that happens to differ is not a black coat), then the parts grown
    # over the rest of the same plain colour next to them (a black field found in pieces is filled)
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    for _ in range(3):
        m = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), could))
    return m


def _grow(m, H, S, V, dist, gap, closer=None, rounds=2):
    """The edges a strict test leaves (a dull or dark rim of a red stripe, a pixel blended with its neighbour)
    taken in: neighbours of the found parts that are somewhat coloured and of a hue somewhat near, twice."""
    from PIL import ImageChops, ImageFilter
    if not m.getbbox():
        return m
    loose = ImageChops.multiply(S.point(lambda s: 255 if s >= SAT_MIN * 0.5 * 255 else 0),
                                V.point(lambda v: 255 if v >= VAL_MIN * 0.6 * 255 else 0))
    loose = ImageChops.multiply(loose, dist.point(lambda x: 255 if x <= gap * 1.5 else 0))
    # past the strict hue gap only a rim is taken - dull or dark pixels; a bright clean colour of its own (the gold
    # of a wreath next to red) stays (a tester's emblem: its gold wolf and laurel turned red)
    rim = ImageChops.lighter(S.point(lambda s: 255 if s < 0.55 * 255 else 0),
                             V.point(lambda v: 255 if v < 0.55 * 255 else 0))
    loose = ImageChops.multiply(loose, ImageChops.lighter(dist.point(lambda x: 255 if x <= gap else 0), rim))
    if closer is not None:                       # never into the other colour's parts (a gold lion on red)
        loose = ImageChops.multiply(loose, closer)
    for _ in range(rounds):
        m = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), loose))
    return m


def _shift(im, src, dst):
    """The whole picture moved from colour src to colour dst (hue set, saturation and brightness scaled)."""
    from PIL import Image
    H, S, V = im.convert("RGB").convert("HSV").split()
    sh, ss, sv = hsv(src)
    th, ts, tv = hsv(dst)
    ks = ts / max(ss, 0.05)
    kv = tv / max(sv, 0.05)
    H = Image.new("L", im.size, int(round(th * 255)) % 256)
    S = S.point(lambda s: min(255, int(s * ks)))
    V = V.point(lambda v: min(255, int(v * kv)))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


PLAIN_LIGHT = {"dark": 0.22, "light": 0.77}      # the lightness the games' artists give a black / a white part


def _to_plain(im, mask, dst, src=None):
    """A part made black / white / grey (dst has no hue) the way the games' own textures do it: no hue, the part's
    average light set to the artists' black (0.22) or white (0.77) - grey: dst's own - and every fold kept (each pixel
    as far from the average as it was). A flat black (lightness scaled to near 0) lost every fold: black shields and
    hoods like holes in battle. A white part as lit as its source colour (a flat card) is as light as dst itself (the
    artists' 0.77 made a flat white card grey)."""
    from PIL import Image, ImageStat
    H, S, V = im.convert("RGB").convert("HSV").split()
    kind = _plain(dst)
    goal = PLAIN_LIGHT.get(kind, hsv(dst)[2]) * 255.0
    ref = max(ImageStat.Stat(V, mask).mean[0], 12.0)
    if kind == "light" and src:
        lit = min(1.0, ref / max(hsv(src)[2] * 255.0, 12.0))     # how lit the part is against its own colour
        goal = max(goal, hsv(dst)[2] * 255.0 * lit)
    S = Image.new("L", im.size, 0)
    if kind == "dark":       # measured against the HRE's own copies: the light scaled down is nearest the artists' black
        k = goal / ref
        V = V.point(lambda v: max(8, min(255, int(v * k))))
    else:                    # against Poland's: the folds kept as they were (moved up) is nearest their white
        add = goal - ref
        V = V.point(lambda v: max(8, min(255, int(v + add))))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


def _shift_plain(im, mask, dst):
    """A black / white / grey part moved to colour dst: dst's hue and saturation, its brightness set by the pixel's
    light against the part's average light (the folds kept; a black coat does not stay black when made red)."""
    from PIL import Image, ImageStat
    H, S, V = im.convert("RGB").convert("HSV").split()
    th, ts, tv = hsv(dst)
    ref = max(ImageStat.Stat(V, mask).mean[0], 12.0)
    H = Image.new("L", im.size, int(round(th * 255)) % 256)
    S = Image.new("L", im.size, int(round(ts * 255)))
    k = tv * 255.0 / ref
    V = V.point(lambda v: min(255, int(v * k)))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


def recolour(im, source, target, others=(), edits=None, plain=True):
    """(new picture, share of pixels changed): im with the parts in the source colours (primary, secondary) in the
    target colours, alpha kept. edits: the hand touch-ups {'p': mask, 's': mask, 'keep': mask} ('L', the picture's
    size) - painted as the new primary / secondary, or kept as they were. plain: black / white / grey faction colours
    are looked for too (only when the other copies are the same drawing - unit cards and textures, not symbols)."""
    from PIL import ImageChops
    ms = masks(im, source, others, plain)
    if edits:
        keep = edits.get("keep")
        for k, key in ((0, "p"), (1, "s")):
            e = edits.get(key)
            if e is not None:
                ms[k] = ImageChops.lighter(ms[k], e)
                ms[1 - k] = ImageChops.subtract(ms[1 - k], e)
            if keep is not None:
                ms[k] = ImageChops.subtract(ms[k], keep)
    rgb = im.convert("RGB")
    out = rgb.copy()
    n = 0
    for m, src, dst in zip(ms, source, target):
        if not dst or not m.getbbox():
            continue
        if _plain(dst):
            if _plain(src) == _plain(dst):
                continue                         # white to white: the artist's own white stays as it is
            part = _to_plain(rgb, m, dst, src)
        elif _plain(src):
            part = _shift_plain(rgb, m, dst)
        else:
            part = _shift(rgb, src or dst, dst)
        out.paste(part, (0, 0), m)
        n += m.histogram()[255]
    if im.mode in ("RGBA", "LA", "P"):
        a = im.convert("RGBA").split()[3]
        out = out.convert("RGBA")
        out.putalpha(a)
    return out, n / float(im.size[0] * im.size[1])



# ---------------------------------------------------------------------------
# this toolkit's side: which pictures, a plan, the write


class RecolourError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


#: at most this many pictures of the faction are compared against, per picture
OTHERS_MAX = 6


def faction_colours(mod) -> Dict[str, Tuple[Optional[Tuple[int, int, int]], Optional[Tuple[int, int, int]]]]:
    """``{slot: (primary, secondary)}`` from descr_sm_factions.txt."""
    from . import factions as fa
    out = {}
    try:
        rf = fa.parse_file(fa.path_for(mod))
    except OSError:
        return out
    for r in rf.records:
        out[fa.slot_of(r.name)] = (fa.parse_colour(r.get("primary_colour")),
                                   fa.parse_colour(r.get("secondary_colour")))
    return out


def _read(path: Path):
    from .bannermaker import read_picture
    return read_picture(path)


def _write(path: Path, im) -> bytes:
    """The bytes of ``im`` in ``path``'s own format."""
    from . import armbake, sprites
    suf = path.suffix.lower()
    if suf == ".texture":
        return sprites.dds_to_texture(armbake.dds_with_mipmaps(im))
    if suf == ".dds":
        return armbake.dds_with_mipmaps(im)
    buf = io.BytesIO()
    im.save(buf, "PNG" if suf == ".png" else "TGA")
    return buf.getvalue()


def targets(mod, slot: str) -> List[Dict]:
    """Every picture of the faction: ``{rel, kind, others: [(rel, faction)], shared: [faction]}``."""
    data = Path(mod.data)
    cols = faction_colours(mod)
    out: List[Dict] = []
    for folder, kind in (("ui/units", "card"), ("ui/unit_info", "info")):
        base = data / folder
        mine = base / slot
        if not mine.is_dir():
            continue
        others = [d for d in base.iterdir() if d.is_dir() and d.name.lower() != slot.lower()
                  and d.name.lower() in cols]
        for f in sorted(mine.iterdir()):
            if f.suffix.lower() not in (".tga", ".dds", ".png"):
                continue
            same = [(f"{folder}/{d.name}/{f.name}", d.name) for d in others if (d / f.name).is_file()]
            out.append({"rel": f"{folder}/{slot}/{f.name}", "kind": kind,
                        "others": same[:OTHERS_MAX], "shared": [], "entries": []})
    seen: Dict[str, Dict] = {}
    try:
        entries = mod.modeldb.entries
    except Exception:  # noqa: BLE001 - a mod whose modeldb will not read has no textures to give
        entries = []
    for e in entries:
        recs = {t.faction.lower(): t.texture.replace("\\", "/") for t in e.main_textures if t.texture}
        mine_tex = recs.get(slot.lower())
        if not mine_tex:
            continue
        rel = mine_tex[5:] if mine_tex.lower().startswith("data/") else mine_tex
        row = seen.get(rel.lower())
        if row is None:
            row = seen[rel.lower()] = {"rel": rel, "kind": "texture", "others": [], "shared": [], "entries": []}
            out.append(row)
        row["entries"].append(e.name)
        for f, t in recs.items():
            if f == slot.lower():
                continue
            t = t[5:] if t.lower().startswith("data/") else t
            if t.lower() == rel.lower():
                if f not in row["shared"]:
                    row["shared"].append(f)
            elif len(row["others"]) < OTHERS_MAX and f in cols and (t, f) not in row["others"]:
                row["others"].append((t, f))
    for rel in (f"ui/faction_symbols/{slot}.tga", f"menu/symbols/fe_symbols_80/{slot}.tga",
                f"loading_screen/symbols/symbol128_{slot}.tga"):
        if (data / rel).is_file():
            out.append({"rel": rel, "kind": "symbol", "others": [], "shared": [], "entries": []})
    return [t for t in out if (data / t["rel"]).is_file()]


def _colours(body: dict, mod, key: str):
    cols = faction_colours(mod)
    def one(v):
        if not v:
            return None
        v = str(v).strip().lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
            raise RecolourError(_i18n.msg("eng.artrecolour.bad_colour", "{c} is not a colour like #c81e1e", c=v))
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    got = body.get(key)
    if isinstance(got, str) and got in cols:
        return cols[got]
    if isinstance(got, (list, tuple)):
        p, s = (list(got) + [None, None])[:2]
        return one(p), one(s)
    raise RecolourError(_i18n.msg("eng.artrecolour.no_colours", "say which colours the pictures are in now and which they should take"))


def _one(mod, row: Dict, source, target, cols):
    data = Path(mod.data)
    im = _read(data / row["rel"])
    others = []
    for rel, f in row["others"]:
        try:
            others.append((_read(data / rel), cols.get(f)))
        except Exception:  # noqa: BLE001 - a copy that will not read is simply not compared against
            continue
    return recolour(im, source, target, others, plain=row["kind"] != "symbol")


def _png(im, side=128) -> str:
    im = im.copy()
    im.thumbnail((side, side))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def plan(mod, body: dict) -> Dict:
    """Which pictures would change, and a few of them before and after."""
    slot = str(body.get("faction") or "").strip()
    rows = targets(mod, slot)
    if not rows:
        raise RecolourError(_i18n.msg("eng.artrecolour.nothing", "{faction} has no pictures of its own in this mod to recolour", faction=slot))
    source, target = _colours(body, mod, "source"), _colours(body, mod, "target")
    cols = faction_colours(mod)
    samples = []
    picks = [r for r in rows if r["kind"] == "card"][:3] + [r for r in rows if r["kind"] == "texture"][:2] \
        + [r for r in rows if r["kind"] == "symbol"][:1]
    for r in picks:
        try:
            new, share = _one(mod, r, source, target, cols)
        except Exception as e:  # noqa: BLE001 - one sample that will not read is shown as that
            samples.append({"rel": r["rel"], "error": str(e)})
            continue
        samples.append({"rel": r["rel"], "kind": r["kind"], "share": round(share, 3),
                        "old": _png(_read(Path(mod.data) / r["rel"])), "new": _png(new)})
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    space = _new_space(mod, rows)
    return {"faction": slot, "counts": counts, "samples": samples,
            "shared": sum(1 for r in rows if r["shared"]),
            "new_bytes": space, "free_bytes": _free(mod),
            "source": [list(c) if c else None for c in source],
            "target": [list(c) if c else None for c in target]}


def _new_space(mod, rows) -> int:
    """About how many bytes the faction's own copies of shared textures take."""
    data = Path(mod.data)
    total = 0
    for r in rows:
        if r["shared"]:
            try:
                total += (data / r["rel"]).stat().st_size
            except OSError:
                pass
    return total


def _free(mod) -> int:
    try:
        return shutil.disk_usage(Path(mod.data)).free
    except OSError:
        return 0


def _own_name(rel: str, slot: str) -> str:
    p = Path(rel)
    return (p.parent / f"{p.stem}_{slot}{p.suffix}").as_posix()


def apply(mod, body: dict) -> Dict:
    """Recolour every picture of the faction, each backed up first."""
    slot = str(body.get("faction") or "").strip()
    rows = targets(mod, slot)
    source, target = _colours(body, mod, "source"), _colours(body, mod, "target")
    cols = faction_colours(mod)
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        t = data / rel
        if t.exists():
            b = backup_root / "data" / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(t, b)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", t, f"-> {b}")
        else:
            manifest["created"].append(rel)
        t.parent.mkdir(parents=True, exist_ok=True)
        return t

    need, free = _new_space(mod, rows), _free(mod)
    if free and need * 2 + 50_000_000 > free:      # the copies, their backups' headroom, and a margin
        raise RecolourError(_i18n.msg("eng.artrecolour.no_space", "the faction's own copies of the textures it shares need about {need} MB and the drive has {free} MB free; free some space first", need=f"{need / 1e6:.0f}", free=f"{free / 1e6:.0f}"))
    repoint: Dict[str, str] = {}
    changed = skipped = 0
    for r in rows:
        try:
            new, share = _one(mod, r, source, target, cols)
        except Exception:  # noqa: BLE001 - a picture that will not read is left as it is
            skipped += 1
            continue
        if share <= 0:
            continue
        rel = r["rel"]
        if r["shared"]:
            rel = _own_name(rel, slot)
            repoint[r["rel"].lower()] = rel
        dest = keep(rel)
        raw = _write(dest, new)
        tmp = dest.with_name(dest.name + ".new")
        tmp.write_bytes(raw)
        tmp.replace(dest)
        file_op("WRITE", dest, "recoloured")
        changed += 1
    if repoint:
        db = mod.modeldb
        text_entries = []
        for e in db.entries:
            raw = e.raw
            idx = {}
            for s in modeldb.path_slots_raw(raw, pad=e.first_entry_pad):
                if s["kind"] == "texture" and s["faction"].lower() == slot.lower():
                    v = s["value"].replace("\\", "/")
                    v2 = v[5:] if v.lower().startswith("data/") else v
                    if v2.lower() in repoint:
                        idx[s["i"]] = repoint[v2.lower()]
            text_entries.append(modeldb.rewrite_paths_indexed(raw, idx, pad=e.first_entry_pad) if idx else raw)
        olds = [e.raw for e in db.entries]
        try:
            for e, raw in zip(db.entries, text_entries):
                e.raw = raw
            text = db.to_text()
        finally:
            for e, raw in zip(db.entries, olds):
                e.raw = raw
        target_db = keep("unit_models/battle_models.modeldb")
        target_db.write_text(text, encoding=modeldb.ENCODING)   # as apply_transfer writes it
        file_op("WRITE", target_db, f"{len(repoint)} texture(s) of {slot} pointed at its own copies")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "factions",
           "action": "recolour", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": slot, "resolved_type": slot,
           "options": {}, "applied": True, "undone": False, "note": "",
           "summary": _i18n.msg("eng.artrecolour.summary", "{faction}'s pictures recoloured: {n} changed, {own} made its own", faction=slot, n=changed, own=len(repoint)),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    mod.__dict__.pop("modeldb", None)
    log.info("RECOLOUR %s in %s: %d changed, %d own copies, %d skipped, id=%s",
             slot, mod.name, changed, len(repoint), skipped, tid)
    return dict(rec, changed=changed, own=len(repoint), skipped=skipped)
