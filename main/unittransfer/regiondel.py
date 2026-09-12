"""Phase 24, G1. Deleting a province, and giving its land to a neighbour.

Geomod's manual: "click the name of the region, then click Delete, and all work
on that region including itself will be gone. The area of the former region will
automatically be allocated to an existing region, usually an adjacent one." Two
pages later it admits what that leaves behind - "resources, forts and characters
will remain" - and that admission is the whole reason this module is not a port.
A province's name is its identity and eight other files point at it; a delete
that removed the record and the pixels and stopped there would leave a campaign
naming a province the engine cannot find, which is the crash 19b was written to
avoid from the other direction.

**A delete is a rename to nothing.** So it walks 19b's site list rather than a
new one: :data:`unittransfer.renames.REGION_SITES` is the measured set of every
file a province is named in - fifteen in Divide and Conquer and twelve in Third
Age Reforged - and each site here is the same file found the same way, edited by
removal instead of by substitution. The one site a rename refuses to follow is
refused here for the same reason and in the same words: the campaign script is a
grammar nothing parses, so every line of it naming the province is listed and
none of it is written.

**The land goes whole to one neighbour it touches.** Geomod says "usually an
adjacent one" and does not say which; this offers every neighbour, ordered by
how much border it shares, and defaults to the longest. Splitting the area
between several neighbours is what a tile-by-tile nearest search would do and it
cannot be made safe: 16e's own rule is that a province in two pieces is two
provinces as far as an army is concerned, and a piece handed to the nearest
neighbour is not provably joined to it. One adjacent heir is, because the two
areas are each contiguous and they share an edge.

**The settlement goes with the land, and the port may not.** A province has one
settlement, so the deleted province's black pixel becomes ground the moment its
tiles become the heir's: the heir has a seat of its own, and a second settlement
pixel is not a second city but the ``marker.extra`` finding, where one of the
two is ignored. The white port pixel is the same rule with a different answer -
the heir inherits the coastline, so a port it does not otherwise have is kept
and a second one is removed. Both are said out loud in the plan rather than done
quietly.

**What is reported and not moved, and why that is the honest answer.** The
resources, forts, watchtowers and characters Geomod leaves dangling are placed
by tile, not by province, and the tiles do not move: they keep their coordinates
and change owner. Nothing about them is orphaned by a delete - what changes is
whose province they stand in, so the plan counts them and says whose. The one
exception is the ``region <name>`` section of ``descr_strat.txt``, which files
forts and watchtowers under a province name rather than under a tile. That one
IS a dangling reference, and it is moved into the heir's section or renamed to
it.

**A delete renumbers, and a rename does not.** Region IDs are first-appearance
order in a row-major scan of ``map_regions.tga``, so taking a province out moves
every region the scan reaches after it down by one - the mirror of the warning
16e gives when a province is created, and the same sentence, because it is the
same fact read backwards.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image

from . import (campaint, campfiles, campmap, campstrat, mapquery, renames,
               stratedit, stratobj, winconds)
from . import keyblock as kb
from .campmap import ENCODING, CampaignMap, MapError
from .maptga import encode
from .mapvocab import key

#: the one layer a delete paints
CODE = "regions"
REGIONS_TGA = campmap.LAYER_BY_CODE[CODE]["file"]
REGIONS_NAME = campaint.REGIONS_NAME
MERCS_NAME = campfiles.MERCS_NAME
WINS_NAME = winconds.REL_NAME
#: The three campaign files a delete reaches that a creation does not. The
#: other four are :func:`unittransfer.campaint.map_campaigns`' own, resolved
#: there to whichever copy each campaign reads.
TILES_NAME = "custom_tiles_db.txt"

#: What the deleted province's port pixel does. The default is worked out from
#: the heir rather than picked: see the module docstring.
PORT_CHOICES = ("keep", "remove")

#: The node kinds a province's tiles can have standing on them, in the order the
#: plan reports them. All four are placed by tile and none moves. A settlement
#: is not among them and cannot be: a settlement block carries ``region <name>``
#: and no coordinates at all, which is why it is the one thing a delete removes
#: rather than counts.
STANDING = ("character", "fort", "watchtower", "resource")


# ---------------------------------------------------------------------------
# reading: who can inherit, and what stands on the land


def record_of(cm: CampaignMap, name: str):
    """The record being deleted, or a refusal naming the file it is not in."""
    rec = cm.regions.by_name(name)
    if rec is None:
        raise MapError(f"{campmap.rel_of(cm, REGIONS_NAME)} has no region "
                       f"called {name}")
    return rec


def heirs(cm: CampaignMap, name: str) -> List[dict]:
    """Every declared province sharing an edge with this one, longest first.

    :func:`unittransfer.campaint.neighbours` is the rule and this is one more
    caller of it: four-connected, markers and sea skipped, which is the same
    touching rule 16e refuses a new province for failing. A province with no
    entry here is one nothing borders, and there is nobody to give its land to.
    """
    rec = record_of(cm, name)
    out: List[dict] = []
    for other, edges in campaint.neighbours(cm, rec.rgb_key).items():
        r = cm.regions.by_name(other)
        reg = cm.index.by_key.get(r.rgb_key) if r is not None else None
        out.append({"name": other, "edges": edges,
                    "tiles": reg.pixels if reg is not None else 0,
                    "port": bool(reg is not None and reg.port),
                    "settlement": r.settlement if r is not None else ""})
    out.sort(key=lambda h: (-h["edges"], h["name"].lower()))
    return out


def _mask(cm: CampaignMap, rgb_key: int) -> Optional[Image.Image]:
    """A one-byte-per-tile mask of the province's own colour, or None.

    Off the index's label image rather than off the pixels: the labels are
    already built, already exact and already one byte a tile, so the repaint
    below is two calls into Pillow's C instead of a walk over a quarter of a
    million tiles in Python.
    """
    labels = [i for i, c in enumerate(cm.index.colours) if key(c) == rgb_key]
    if not labels:
        return None
    table = [0] * 256
    for i in labels:
        table[i] = 255
    img = Image.frombytes("L", (cm.index.width, cm.index.height), cm.index.labels)
    return img.point(table, "L")


def campaigns_reading(mod, cm: CampaignMap) -> List[dict]:
    """Every campaign whose ``map_regions.tga`` is the file this map reads.

    22c's ruling applied to a delete: a campaign is judged on its own copies, so
    a delete off a campaign's own regions layer reaches that campaign and a
    delete off the base map reaches every campaign that has no copy of its own.
    The rows are :func:`unittransfer.campaint.map_campaigns`' - the same files a
    new province has to reach, each one the copy THAT campaign reads - with the
    three a delete needs and a creation does not added to each.
    """
    data = Path(mod.data)
    want = campmap.rel_of(cm, REGIONS_TGA)
    out: List[dict] = []
    for c in campaint.map_campaigns(mod):
        home = f"{campstrat.CAMPAIGN_DIR_REL}/{c['campaign']}"
        own = f"{home}/{REGIONS_TGA}"
        mine = own if (data / own).is_file() else f"{campmap.BASE_REL}/{REGIONS_TGA}"
        if mine != want:
            continue
        row = dict(c)
        row["home"] = home
        row["wins"] = f"{home}/{WINS_NAME}"
        row["mercs"] = f"{home}/{MERCS_NAME}"
        row["tiles_db"] = f"{home}/{TILES_NAME}"
        out.append(row)
    return out


def standing_on(mod, cm: CampaignMap, camps: Sequence[dict], rgb_key: int
                ) -> List[dict]:
    """What each campaign puts on this province's tiles, counted by kind.

    Geomod's caveat measured rather than repeated. None of these is orphaned by
    a delete - a fort at 212,88 is at 212,88 afterwards - so each row says what
    stands there and the plan says whose province it becomes. The exception is
    the settlement, which is the province's own and goes with it.
    """
    mask = _mask(cm, rgb_key)
    if mask is None:
        return []
    w, h = cm.index.width, cm.index.height
    inside = mask.tobytes()

    def ours(gx: int, gy: int) -> bool:
        x, y = cm.image_xy(gx, gy)
        return 0 <= x < w and 0 <= y < h and bool(inside[y * w + x])

    out: List[dict] = []
    for c in camps:
        try:
            sf = campstrat.parse_strat(kb.read_text(
                Path(mod.data) / c["strat"], ENCODING))
        except (OSError, ValueError):
            continue
        counts: Dict[str, int] = {}
        for node in sf.nodes:
            if node.kind not in STANDING:
                continue
            gx, gy = node.fields.get("x"), node.fields.get("y")
            if gx is None or gy is None or not ours(int(gx), int(gy)):
                continue
            counts[node.kind] = counts.get(node.kind, 0) + 1
        if counts:
            out.append({"campaign": c["campaign"],
                        "counts": {k: counts[k] for k in STANDING if k in counts}})
    return out


# ---------------------------------------------------------------------------
# the plan


@dataclass
class DeletePlan:
    """Everything one delete would write, worked out without touching the disk."""

    mod: object = None
    cm: Optional[CampaignMap] = None
    campaign: str = ""
    name: str = ""
    settlement: str = ""
    shown: str = ""
    heir: str = ""
    tiles: int = 0
    port: str = ""
    #: data-relative path -> the whole file as it would be written
    data: Dict[str, bytes] = field(default_factory=dict)
    texts: Dict[str, str] = field(default_factory=dict)
    deletes: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: what the province's tiles carry, per campaign
    standing: List[dict] = field(default_factory=list)
    #: every line of every campaign script naming it, reported and never written
    script: List[renames.Mention] = field(default_factory=list)
    #: every other file naming it, counted per file
    review: List[dict] = field(default_factory=list)

    @property
    def files(self) -> List[str]:
        return sorted(set(self.data) | set(self.texts))

    def summary(self) -> str:
        head = (f"delete {self.name} from {getattr(self.mod, 'name', '?')}"
                + (f", its land to {self.heir}" if self.heir else ""))
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {
            "name": self.name, "settlement": self.settlement,
            "shown": self.shown, "heir": self.heir, "tiles": self.tiles,
            "port": self.port, "campaign": self.campaign,
            "files": self.files, "deletes": list(self.deletes),
            "changes": list(self.changes), "warnings": list(self.warnings),
            "errors": list(self.errors), "standing": list(self.standing),
            "script": [{"rel": m.rel, "line": m.line, "text": m.text}
                       for m in self.script],
            "review": list(self.review),
            "ok": not self.errors and bool(self.data or self.texts),
        }


def plan(mod, cm: CampaignMap, campaign: str, body: dict) -> DeletePlan:
    """Work out one delete. ``body`` is ``{name, heir, port}``.

    Every byte is built here and nothing is written, which is the ruling
    :func:`unittransfer.campaint.plan_paint` and
    :func:`unittransfer.campmap.plan_region` both make: a layer that will not
    re-encode has to fail before the backup is taken rather than half way
    through writing the eleventh of fourteen files.
    """
    p = DeletePlan(mod=mod, cm=cm,
                   campaign=campaign or campstrat.DEFAULT_CAMPAIGN,
                   name=str(body.get("name") or "").strip())
    if not p.name:
        p.errors.append("no province was named")
        return p
    try:
        rec = record_of(cm, p.name)
    except MapError as exc:
        p.errors.append(str(exc))
        return p
    p.settlement = rec.settlement
    p.shown = campmap.shown_names(mod).get(p.name.lower(), "")
    if len(cm.regions.records) <= 1:
        p.errors.append(f"{p.name} is the only region "
                        f"{campmap.rel_of(cm, REGIONS_NAME)} declares, and a map "
                        f"with no region at all will not load")
        return p

    reg = cm.index.by_key.get(rec.rgb_key)
    p.tiles = reg.pixels if reg is not None else 0
    camps = campaigns_reading(mod, cm)
    _plan_pixels(p, rec, reg, body)
    if p.errors:
        return p
    p.standing = standing_on(mod, cm, camps, rec.rgb_key)
    _plan_records(p, camps)
    _plan_campaigns(p, camps)
    _plan_mentions(p)
    _plan_renumber(p, reg)
    if not p.data and not p.texts and not p.errors:
        p.errors.append(f"nothing in {getattr(mod, 'name', '?')} would change, "
                        f"which means {p.name} is not written down anywhere this "
                        f"knows how to read")
    return p


def _plan_pixels(p: DeletePlan, rec, reg, body: dict) -> None:
    """The regions layer with the province's tiles given to its heir.

    A record with no pixels at all skips this entirely and takes no heir: that
    is the state :func:`unittransfer.campaint._emptied` refuses a save for
    creating, and deleting the record is exactly the fix for it.
    """
    cm = p.cm
    want = str(body.get("heir") or "").strip()
    cands = heirs(cm, p.name)
    names = {h["name"].lower(): h for h in cands}
    if reg is None or not reg.pixels:
        p.warnings.append(
            f"no tile of {campmap.rel_of(cm, REGIONS_TGA)} is painted "
            f"{rec.rgb[0]} {rec.rgb[1]} {rec.rgb[2]}, so {p.name} is a record "
            f"with no land and there is nothing to give away")
        return
    if not cands:
        p.errors.append(
            f"{p.name} shares an edge with no declared region, so there is "
            f"nobody to give its {reg.pixels:,} tile(s) to. A province whose "
            f"only neighbour is the ocean has to be painted over by hand.")
        return
    if not want:
        want = cands[0]["name"]
    if want.lower() not in names:
        p.errors.append(
            f"{want} does not share an edge with {p.name}, so its land cannot "
            f"go there without leaving {want} in two pieces. The provinces that "
            f"do touch it are " + ", ".join(h["name"] for h in cands[:6])
            + ("…" if len(cands) > 6 else ""))
        return
    heir = names[want.lower()]
    p.heir = heir["name"]
    hrec = cm.regions.by_name(p.heir)
    hrgb = tuple(hrec.rgb)

    mask = _mask(cm, rec.rgb_key)
    img = cm.layer(CODE).convert("RGB")
    img.paste(hrgb, mask=mask)
    if reg.settlement is not None:
        img.putpixel(tuple(reg.settlement), hrgb)
    p.port = str(body.get("port") or "").strip().lower()
    if reg.port is not None:
        if p.port not in PORT_CHOICES:
            p.port = "remove" if heir["port"] else "keep"
        if p.port == "remove":
            img.putpixel(tuple(reg.port), hrgb)
    else:
        p.port = ""

    info = cm.info(CODE)
    try:
        raw = encode(img, info)
    except Exception as exc:                                    # noqa: BLE001
        p.errors.append(f"{REGIONS_TGA} could not be re-encoded: {exc}")
        return
    rel = campmap.rel_of(cm, REGIONS_TGA)
    p.data[rel] = raw
    p.changes.append(f"{rel}: {reg.pixels:,} tile(s) of {p.name} become "
                     f"{p.heir}'s")
    if reg.settlement is not None:
        p.changes.append(
            f"{rel}: the settlement pixel at "
            f"{reg.settlement[0]},{reg.settlement[1]} becomes ground - "
            f"{p.heir} has {hrec.settlement} and a province has one seat")
    if reg.port is not None:
        p.changes.append(
            f"{rel}: the port pixel at {reg.port[0]},{reg.port[1]} "
            + (f"stays, and becomes {p.heir}'s harbour"
               if p.port == "keep" else
               f"becomes ground - {p.heir} already has a port and only one of "
               f"two is ever used"))
    if p.port == "keep" and heir["port"]:
        p.warnings.append(
            f"{p.heir} already has a port of its own, so keeping this one "
            f"leaves two port pixels in one province and the engine uses one "
            f"of them. Check reports that as a second port.")

    # 16e's own contiguity rule, read the other way round. The heir's land plus
    # a piece that does not touch it is a province in two pieces, and the engine
    # numbers it as one.
    apart = _detached(cm, rec.rgb_key, hrec.rgb_key)
    if apart:
        p.warnings.append(
            f"{apart:,} of {p.name}'s tile(s) do not touch {p.heir} at all, so "
            f"{p.heir} would be painted in more than one piece. The engine "
            f"treats it as one region, and an army cannot walk between the "
            f"pieces.")


def _detached(cm: CampaignMap, gone: int, heir: int) -> int:
    """Tiles of ``gone`` in no piece that reaches ``heir``, four-connected.

    The flood is over the two colours together, which is the shape the map will
    be in after the paste: a piece of the deleted province that no path of its
    own tiles joins to the heir is a piece the heir will hold and not be able to
    walk to.
    """
    w, h = cm.index.width, cm.index.height
    labels = cm.index.labels
    ours = {i for i, c in enumerate(cm.index.colours) if key(c) == gone}
    theirs = {i for i, c in enumerate(cm.index.colours) if key(c) == heir}
    if not ours or not theirs:
        return 0
    mine = [i for i in range(w * h) if labels[i] in ours]
    stack = [i for i in range(w * h) if labels[i] in theirs]
    seen = set(stack)
    keep = set(mine)
    while stack:
        i = stack.pop()
        x = i % w
        for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1),
                      (i - w, i >= w), (i + w, i + w < w * h)):
            if not ok or j in seen:
                continue
            if j in keep or labels[j] in theirs:
                seen.add(j)
                stack.append(j)
    return sum(1 for i in mine if i not in seen)


def _plan_records(p: DeletePlan, camps: Sequence[dict]) -> None:
    """The record out of every ``descr_regions.txt`` these campaigns read."""
    data = Path(p.mod.data)
    rels = [campmap.rel_of(p.cm, REGIONS_NAME)]
    rels += [c["regions"] for c in camps if c["regions"] not in rels]
    for rel in rels:
        path = data / rel
        if not path.is_file():
            continue
        rf = campmap.parse_regions(kb.read_text(path, ENCODING))
        rec = rf.by_name(p.name)
        if rec is None:
            continue
        p.texts[rel] = campmap.replace_record(rf, rec, "")
        p.changes.append(f"{rel}: the record for {p.name} "
                         f"(lines {rec.span[0] + 1}-{rec.span[1] + 1}) removed")


def _plan_campaigns(p: DeletePlan, camps: Sequence[dict]) -> None:
    """Every campaign-side file that names the province, one campaign at a time.

    The order is 19b's site order, and each one is that site's own removal: the
    settlement block out of the start position, the province out of the two
    win-condition lists, out of its mercenary pool, out of its music type, out
    of the lookup pair and out of the custom battle tiles. A file two campaigns
    read is planned once, which is what ``p.texts`` being keyed on the path is
    for.
    """
    if not camps:
        p.warnings.append(
            f"no campaign in {getattr(p.mod, 'name', '?')} reads this map, so "
            f"there is no start position, no win condition and no music type "
            f"naming {p.name} to follow")
        return
    for c in camps:
        _plan_strat(p, c)
        _plan_wins(p, c)
        _plan_mercs(p, c)
        _plan_music(p, c)
        _plan_lookup(p, c)
        _plan_tiles_db(p, c)
        if c["rwm"] and c["rwm"] not in p.deletes:
            p.deletes.append(c["rwm"])
            p.changes.append(f"{c['rwm']}: deleted, or {c['campaign']} loads "
                             f"the old compiled map")
    rwm = campmap.RWM_REL
    if (Path(p.mod.data) / rwm).is_file() and rwm not in p.deletes:
        p.deletes.append(rwm)
        p.changes.append(f"{rwm}: deleted, the way every save of this map "
                         f"deletes it")


def _text_of(p: DeletePlan, rel: str) -> str:
    """This file as the plan has it so far, or as it is on disk."""
    if rel in p.texts:
        return p.texts[rel]
    return kb.read_text(Path(p.mod.data) / rel, ENCODING)


def _plan_strat(p: DeletePlan, c: dict) -> None:
    """The settlement block, and the fort-and-tower section that names it.

    Two edits in one pass over the file, because both are spans and applying
    one would move the other. The settlement takes the blank line that follows
    it, which is :func:`unittransfer.stratedit.detach_span`'s rule and the same
    one a move uses, so the block above and the block below keep the rhythm the
    file was written in.
    """
    rel = c["strat"]
    path = Path(p.mod.data) / rel
    if not path.is_file():
        p.warnings.append(f"{c['campaign']} has no {campstrat.STRAT_NAME}")
        return
    try:
        sf = campstrat.parse_strat(_text_of(p, rel))
    except (OSError, ValueError) as exc:
        p.errors.append(f"{rel} could not be read ({exc})")
        return
    lines = list(sf.lines)
    drop: List[Tuple[int, int]] = []
    inserts: Dict[int, List[str]] = {}

    node = stratedit.find_settlement(sf, p.name)
    if node is not None:
        faction = stratedit.faction_of(sf, node)
        if faction is None:
            p.errors.append(f"{rel}: {p.name}'s settlement block is not inside "
                            f"any faction block, which is a defect to fix "
                            f"rather than a block to delete")
            return
        span = stratedit.detach_span(sf, node, faction)
        drop.append(span)
        held = stratedit.settlements_of(sf, faction)
        p.changes.append(f"{rel}: {faction.name}'s settlement in {p.name} "
                         f"(lines {span[0] + 1}-{span[1] + 1}) removed")
        if len(held) == 1:
            p.warnings.append(
                f"{p.name} is the only settlement {faction.name} holds in "
                f"{c['campaign']}, so it starts the campaign holding nothing. "
                f"That is legal - it is the shape a horde faction is - but it "
                f"is very rarely what somebody meant.")
        elif held and held[0] is node:
            p.warnings.append(
                f"{p.name} is {faction.name}'s capital in {c['campaign']} - the "
                f"first settlement in the block - so "
                f"{held[1].get('region') or '(the next one)'} becomes the "
                f"capital instead.")
    else:
        p.warnings.append(f"{rel}: no faction starts holding {p.name}, so there "
                          f"is no settlement block to remove")

    section = next((n for n in sf.of_kind("region")
                    if str(n.get("name") or "").strip().lower()
                    == p.name.lower()), None)
    if section is not None:
        _plan_section(p, sf, section, rel, lines, drop, inserts)

    if not drop and not inserts and lines == sf.lines:
        return
    out: List[str] = []
    gone = {i for a, b in drop for i in range(a, b + 1)}
    for i, line in enumerate(lines):
        out += inserts.get(i, [])
        if i not in gone:
            out.append(line)
    out += inserts.get(len(lines), [])
    text = stratedit.serialise(sf, out)
    _guard_strat(p, sf, text, rel)
    p.texts[rel] = text


def _plan_section(p: DeletePlan, sf, section, rel: str, lines: List[str],
                  drop: List[Tuple[int, int]], inserts: Dict[int, List[str]]
                  ) -> None:
    """The ``region <name>`` section: moved into the heir's, or renamed to it.

    This is the one thing a delete really does orphan, and it is the one thing
    Geomod's caveat names that is not placed by tile: a fort is filed under a
    province here, and the province is going. The heir keeps the forts, because
    the tiles they stand on are the heir's now.
    """
    kept = [sf.nodes[i] for i in section.children
            if sf.nodes[i].kind in stratobj.SECTIONED]
    if not p.heir:
        drop.append((section.start, stratobj.content_end(sf, section)))
        if kept:
            p.warnings.append(
                f"{rel}: the `region {p.name}` section and its {len(kept)} fort "
                f"or watchtower line(s) go with it, because there is no heir to "
                f"move them to")
        return
    into = next((n for n in sf.of_kind("region")
                 if str(n.get("name") or "").strip().lower()
                 == p.heir.lower()), None)
    if into is None:
        at = section.field_lines.get("name", section.start)
        lines[at] = kb.keep_comment(
            lines[at], kb.indent_of(kb.code_of(lines[at])) + f"region {p.heir}")
        p.changes.append(f"{rel}: the `region {p.name}` section becomes "
                         f"`region {p.heir}`, with its {len(kept)} fort and "
                         f"watchtower line(s)")
        return
    body = [lines[n.start] for n in kept]
    drop.append((section.start, stratobj.content_end(sf, section)))
    if body:
        inserts.setdefault(stratobj.content_end(sf, into) + 1, []).extend(body)
    p.changes.append(
        f"{rel}: the `region {p.name}` section removed"
        + (f", its {len(body)} fort and watchtower line(s) moved into "
           f"`region {p.heir}`" if body else ""))


def _guard_strat(p: DeletePlan, before, text: str, rel: str) -> None:
    """What the edit did that it was never asked to do. 16h's guard, one delete on.

    :func:`unittransfer.stratedit._guard` refuses any change to the set of
    provinces held, which is exactly what a delete is for, so its counts are
    taken here with the two kinds this edit does change allowed to move and
    every other kind held to its number.
    """
    try:
        after = campstrat.parse_strat(text)
    except (OSError, ValueError) as exc:
        p.errors.append(f"{rel}: the edited file no longer reads ({exc})")
        return
    was, now = before.counts(), after.counts()
    moved = ("settlement", "building", "unit", "character", "character_record",
             "relative", "fort", "watchtower", "region")
    for kind in sorted(set(was) | set(now)):
        if kind in moved:
            continue
        if was.get(kind, 0) != now.get(kind, 0):
            p.errors.append(f"{rel}: this would leave {now.get(kind, 0)} "
                            f"{kind} record(s) where the file has "
                            f"{was.get(kind, 0)}, and a delete removes one "
                            f"settlement")
    if before.rosters != after.rosters:
        p.errors.append(f"{rel}: this would change the playable, unlockable or "
                        f"nonplayable lists, which no delete does")
    if before.globals != after.globals:
        p.errors.append(f"{rel}: this would change the campaign's own header "
                        f"values")
    a, _ = stratedit.blocks_by_region(before)
    b, _ = stratedit.blocks_by_region(after)
    lost = sorted(set(a) - set(b))
    if lost != [p.name.lower()] and lost != []:
        p.errors.append(f"{rel}: this would leave the campaign holding a "
                        f"different set of provinces (lost "
                        + ", ".join(lost[:4]) + ")")
        return
    changed = [k for k in b if a.get(k) != b[k]]
    if changed:
        p.errors.append(f"{rel}: this would rewrite {len(changed)} settlement "
                        f"block(s) nobody asked it to, starting with "
                        f"{changed[0]}")
    for kind in ("fort", "watchtower"):
        if was.get(kind, 0) != now.get(kind, 0):
            p.warnings.append(
                f"{rel}: {was.get(kind, 0) - now.get(kind, 0)} {kind}(s) go "
                f"with the section, because there was no heir to file them "
                f"under")


def _plan_wins(p: DeletePlan, c: dict) -> None:
    """The province out of every ``hold_regions`` list, long campaign and short.

    Two things this does not recompute, because a delete is not a rewrite of the
    record. **The ``short_campaign`` prefix is read off the line it is on** and
    put back: it is a switch and whichever line carries it owns the rest of the
    short campaign, so working out where it "should" go from the slots would
    move it. And **a long ``hold_regions`` left naming nobody loses its line**
    while the short one keeps it: 45 of the 74 real short campaigns write
    ``short_campaign hold_regions`` with nothing after it, and not one long
    campaign writes a bare ``hold_regions``.
    """
    rel = c["wins"]
    path = Path(p.mod.data) / rel
    if not path.is_file():
        return
    wf = winconds.parse_wins(_text_of(p, rel))
    lines = list(wf.lines)
    low = p.name.lower()
    hits = 0
    gone: set = set()
    for rec in wf.records:
        for slot in ("hold", "short_hold"):
            at = rec.lines.get(slot, -1)
            if at < 0:
                continue
            was = [str(x) for x in rec.get(slot)]
            got = [x for x in was if x.lower() != low]
            if len(got) == len(was):
                continue
            hits += 1
            short = kb.code_of(lines[at]).lower().startswith("short_campaign")
            if not got and not short:
                gone.add(at)
            else:
                body = winconds.slot_line(slot, got, short_head=short)
                lines[at] = stratedit.rewrite_line(lines[at], body)
            if not got:
                p.warnings.append(
                    f"{rel}: {rec.faction}'s "
                    + ("short campaign " if slot == "short_hold" else "")
                    + "win condition now names no province to hold, so the "
                      "only way it can win is on the other terms in its record")
    if hits:
        wf.lines = [ln for i, ln in enumerate(lines) if i not in gone]
        p.texts[rel] = wf.serialise()
        p.changes.append(f"{rel}: {p.name} taken out of {hits} hold_regions "
                         f"line(s)")


def _plan_mercs(p: DeletePlan, c: dict) -> None:
    """The province out of its mercenary pool, through 18a's own writer."""
    rel = c["mercs"]
    path = Path(p.mod.data) / rel
    if not path.is_file():
        return
    text = _text_of(p, rel)
    mf = campfiles.parse_mercs(text)
    low = p.name.lower()
    mine = [q.name for q in mf.pools
            if any(r.lower() == low for r in q.regions)]
    if not mine:
        return
    out = campfiles.move_region(mf, p.name, "")
    if out == text:
        return
    p.texts[rel] = out
    p.changes.append(f"{rel}: {p.name} taken out of the pool "
                     + (", ".join(mine[:-1]) + " and " if len(mine) > 1 else "")
                     + mine[-1])
    # every pool it was in, not only the one `pool_of` would name: the file says
    # a province may be in one pool and nothing in the format enforces it, and a
    # pool left selling nowhere sells nothing at all
    after = {q.name: q.regions for q in campfiles.parse_mercs(out).pools}
    for name in mine:
        if not after.get(name):
            p.warnings.append(f"{rel}: the pool {name} now sells in no province "
                              f"at all, so nothing in it is ever recruitable")


def _plan_music(p: DeletePlan, c: dict) -> None:
    """The province off its music type's ``regions`` line."""
    rel = c["music"]
    path = Path(p.mod.data) / rel
    if not path.is_file():
        return
    text = _text_of(p, rel)
    types = mapquery.parse_music_types(text)
    mine = next((t for t, rs in types.items()
                 if any(r.lower() == p.name.lower() for r in rs)), "")
    if not mine:
        return
    out = mapquery.drop_music_region(text, p.name)
    if out == text:
        return
    p.texts[rel] = out
    p.changes.append(f"{rel}: {p.name} taken out of the music type {mine}")


def _plan_lookup(p: DeletePlan, c: dict) -> None:
    """The pair out of ``descr_regions_and_settlement_name_lookup.txt``.

    The province on one line and its settlement on the next, which is
    :func:`unittransfer.renames._find_lookup`'s reading of the file: the
    alternation is over code lines only, so a comment between the two halves of
    a pair does not break it and is not removed with it.
    """
    rel = c["lookup"]
    if not rel:
        return
    path = Path(p.mod.data) / rel
    if not path.is_file():
        return
    text = _text_of(p, rel)
    lines, newline, trailing = campmap._split_lines(text)
    low = p.name.lower()
    seen = 0
    at = -1
    for i, line in enumerate(lines):
        code = kb.code_of(line)
        if not code:
            continue
        if seen % 2 == 0 and code.strip().lower() == low:
            at = i
            break
        seen += 1
    if at < 0:
        return
    mate = next((j for j in range(at + 1, len(lines)) if kb.code_of(lines[j])), -1)
    gone = [at] + ([mate] if mate >= 0 else [])
    out = [ln for i, ln in enumerate(lines) if i not in set(gone)]
    p.texts[rel] = newline.join(out) + (newline if trailing else "")
    p.changes.append(f"{rel}: the {p.name} / {p.settlement or '?'} pair removed")
    if mate < 0:
        p.warnings.append(f"{rel}: {p.name} was the last line in the file and "
                          f"had no settlement under it, which is a pair the "
                          f"engine would have read short anyway")


def _plan_tiles_db(p: DeletePlan, c: dict) -> None:
    """Custom battle tiles whose first column is this province."""
    rel = c["tiles_db"]
    path = Path(p.mod.data) / rel
    if not path.is_file():
        return
    text = _text_of(p, rel)
    lines, newline, trailing = campmap._split_lines(text)
    low = p.name.lower()
    gone = {i for i, line in enumerate(lines)
            if kb.code_of(line).split(None, 1)[:1] == [p.name]
            or kb.code_of(line).split(None, 1)[:1] == [low]}
    if not gone:
        return
    out = [ln for i, ln in enumerate(lines) if i not in gone]
    p.texts[rel] = newline.join(out) + (newline if trailing else "")
    p.changes.append(f"{rel}: {len(gone)} custom battle tile row(s) removed")


def _plan_mentions(p: DeletePlan) -> None:
    """Every line naming the province that this will not write. 19b's scan.

    The two words the player reads are in that list and are deliberately left
    where they are: an unused ``{key}`` is not a dangling reference, and the
    engine only ever complains about one it cannot find. Removing it would mean
    recompiling the ``.strings.bin`` beside it for no gain at all.
    """
    p.script, p.review = renames.mentions(
        p.mod, p.name, set(p.texts) | set(p.data))
    if p.script:
        p.warnings.append(
            f"{len(p.script)} line(s) of the campaign script name {p.name}, and "
            f"the script is reported and never written - it is a grammar "
            f"nothing here parses. Each one is listed with its line number.")
    keys = [r for r in p.review
            if r["rel"].startswith("text/") and r["rel"].endswith(".txt")]
    if keys:
        p.warnings.append(
            "the two words the player reads are left where they are, in "
            + ", ".join(r["rel"] for r in keys[:3])
            + ". A key nothing reads is not an error; the engine only names one "
              "it cannot find.")


def _plan_renumber(p: DeletePlan, reg) -> None:
    """16e's renumbering warning, read backwards."""
    if reg is None or reg.region_id < 0:
        return
    after = sum(1 for r in p.cm.index.regions if r.region_id > reg.region_id)
    if not after:
        return
    p.warnings.append(
        f"{p.name} is region ID {reg.region_id}, and the {after} region(s) the "
        f"engine scans after it each move down by one. A region ID is the scan "
        f"order of {REGIONS_TGA} rather than anything written down, so no file "
        f"needs editing - but a script that names a region by number now names "
        f"a different one.")


# ---------------------------------------------------------------------------
# the save


def apply(p: DeletePlan) -> dict:
    """Write the delete, with the same backups and undo as any other job.

    One backup set and one log entry for all of it, which is the ruling
    :func:`unittransfer.campaint.apply_paint` makes and for a stronger reason
    here: an undo that put the pixels back and left the record deleted would
    leave the map painted a colour nothing declares, which is the hole 16e
    refuses to let anybody paint into.
    """
    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data and not p.texts:
        raise ValueError("nothing would change")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [],
                                      "deleted": []}

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

    for rel, raw in sorted(p.data.items()):
        target = keep(rel)
        target.write_bytes(raw)
        file_op("WRITE", target, f"{len(raw)} bytes")
    for rel, text in sorted(p.texts.items()):
        target = keep(rel)
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    for rel in p.deletes:
        path = Path(mod.data) / rel
        if path.exists():
            keep(rel)
            path.unlink()
            manifest["deleted"].append(rel)
            file_op("DELETE", path,
                    "stale compiled map - the game would load it instead")

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campmap", "action": "region_delete",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {"heir": p.heir, "port": p.port, "campaign": p.campaign},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("DELETE %s - region %s%s, %d file(s), id=%s", mod.name, p.name,
             f" -> {p.heir}" if p.heir else "",
             len(p.data) + len(p.texts), tid)
    if p.cm is not None:
        p.cm.invalidate(CODE)
    return {"id": tid, "name": p.name, "heir": p.heir,
            "files": p.files, "record": rec}


# ---------------------------------------------------------------------------
# the panel


def view(mod, cm: CampaignMap, campaign: str, name: str) -> dict:
    """What the delete panel shows before anything is chosen. Never raises.

    The heirs, what stands on the land, and which files would be reached. The
    plan is what says exactly; this is what makes the question askable.
    """
    out: dict = {"name": name, "campaign": campaign, "ok": False, "error": "",
                 "heirs": [], "standing": [], "campaigns": [], "tiles": 0,
                 "settlement": "", "shown": "", "port": False}
    try:
        rec = record_of(cm, name)
        reg = cm.index.by_key.get(rec.rgb_key)
        camps = campaigns_reading(mod, cm)
        out.update({
            "ok": True,
            "settlement": rec.settlement,
            "shown": campmap.shown_names(mod).get(name.lower(), ""),
            "rgb": list(rec.rgb),
            "file": campmap.rel_of(cm, REGIONS_NAME),
            "layer": campmap.rel_of(cm, REGIONS_TGA),
            "tiles": reg.pixels if reg is not None else 0,
            "region_id": reg.region_id if reg is not None else -1,
            "port": bool(reg is not None and reg.port),
            "heirs": heirs(cm, name),
            "standing": standing_on(mod, cm, camps, rec.rgb_key),
            "campaigns": [c["campaign"] for c in camps],
            "regions": len(cm.regions.records),
        })
    except (MapError, OSError, ValueError) as exc:                # noqa: BLE001
        out["error"] = str(exc)
    return out
