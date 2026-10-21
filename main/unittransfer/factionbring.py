"""96f: a whole faction brought from another mod.

The Oogway campaign editor's *New faction > From another mod* (its
``factionbring.py``, Pfadfinder-Adam/RTW-M2TW-Campaign-Editor, taken with the
author's leave), laid on this toolkit's own clone rather than the editor's.

**How.** The new faction is first made the way *Add a faction* makes one: a
clone of a faction of THIS mod (:mod:`unittransfer.factionclone`), its
*frame*. The frame is what puts a line for the new slot in every file that
lists factions, written the way this mod writes them, so nothing here has to
know how fourteen files spell a faction. Then what is the brought faction's own
is laid over the clone's files before a byte is written:

* its record in ``descr_sm_factions.txt``: culture (when this mod has it),
  religion (likewise), colours, its 3D symbol, loading logo and movies, the
  files they name brought over where this mod lacks them;
* its shown name and every ``EMT_*`` text of its slot in ``expanded.txt``;
* its name lists in ``descr_names.txt``, and every name's text this mod's
  ``names.txt`` lacks (a name with no text shows its raw token in game);
* its campaign-map figures' textures in ``descr_model_strat.txt``, for each
  figure type this mod has too;
* its art: every picture under ``ui``, ``menu`` and ``banners`` carrying its
  slot, in place of the frame's copy at the same path;
* its own units: one this mod has with the very same lines is shared (the new
  faction joins its ownership), any other is brought by Unit Transfer, owned by
  the new faction, with its models, cards, sounds and recruitment.

The frame's own units are taken back out of the new faction's ownership, so it
fields the brought faction's army and not the frame's, unless the frame's are
asked for or the brought faction owns nothing of its own.

**What does not come**, and the plan says so: its towns, armies and family
(``descr_strat.txt`` is never cloned, see ``factionclone.STRAT_NOTE``), scripts
and events naming it, traits only it has, a culture or religion this mod lacks,
and its shield pictures on the logo sheets (the frame's, made the new faction's
own, stand in).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import factionclone as fc
from . import factions as fac
from . import gamepack
from . import keyblock as kb
from . import stringsbin
from . import i18n as _i18n

#: the record's lines that name a file of its own, brought with the file
FILE_KEYS: Tuple[str, ...] = ("symbol", "rebel_symbol", "loading_logo", "intro_movie",
                              "victory_movie", "defeat_movie", "death_movie")

#: the record's lines that are simply the brought faction's
PLAIN_KEYS: Tuple[str, ...] = ("primary_colour", "secondary_colour")

NAMES_TXT = "text/names.txt"
LOC_ENCODING = "utf-16"
SECTIONS = ("characters", "surnames", "women", "settlements")


# ---------------------------------------------------------------------------
# reading the other mod
#
# A mod may ship a file loose or only in its packs (a Kingdoms campaign), and a
# file it never changed is the base game's: the game's own lookup finds all of
# them, so the other mod is read through it.


def _read(mod, rel: str, encoding: str) -> Optional[str]:
    path, _where = gamepack.lookup(rel, mod)
    if path is None or not Path(path).is_file():
        return None
    try:
        return kb.to_newline(kb.read_text(Path(path), encoding), "\n")
    except (OSError, UnicodeError):
        return None


def _roster(mod) -> Optional[fac.fr.RecordFile]:
    text = _read(mod, fac.REL, fac.ENCODING)
    return fac.parse_text(text) if text is not None else None


def factions_of(mod) -> List[Dict]:
    """``[{slot, culture, label}]`` of a mod, the rebels left out - what the
    dialog offers to bring."""
    rf = _roster(mod)
    if rf is None:
        return []
    names = {}
    exp = _read(mod, "text/expanded.txt", LOC_ENCODING)
    if exp:
        names = dict(stringsbin.from_txt(exp))
    out = []
    for r in rf.records:
        slot = fac.slot_of(r.name)
        if slot == "slave":
            continue
        out.append({"slot": slot, "culture": r.get("culture") or "",
                    "label": names.get(slot.upper(), "") or slot})
    return out


def frame_for(mod, culture: str, prefer: str = "") -> str:
    """The faction of this mod the new one is made on: ``prefer`` when it is
    here, else the first of the same culture, else the first faction. Never
    the rebels or the papacy, whose records carry a special type a new faction
    must not inherit."""
    rf = _roster(mod)
    if rf is None:
        return ""
    have = [(fac.slot_of(r.name), r.get("culture") or "") for r in rf.records
            if fac.slot_of(r.name) not in fac.HOMELESS_BARRED_SLOTS
            and not (r.get("special_faction_type") or "").strip()]
    if prefer and any(s == prefer for s, _ in have):
        return prefer
    return next((s for s, c in have if c == culture), have[0][0] if have else "")


def own_units(src, faction: str) -> List[str]:
    """The other mod's units whose ``ownership`` names the faction itself."""
    return [u.type for u in src.edu.units
            if faction in [o.strip().lower() for o in u.ownership]]


def _sans_ownership(raw: str) -> List[List[str]]:
    """An EDU block's lines as words, comments, blanks and ``ownership`` left
    out: two units alike in this are the same unit."""
    out = []
    for line in raw.splitlines():
        code = kb.code_of(line).strip()
        if not code or code.split()[0] == "ownership":
            continue
        out.append(code.replace(",", " , ").split())
    return out


# ---------------------------------------------------------------------------
# the plan


@dataclass
class BringPlan:
    """A clone of the frame with the brought faction laid over it, and the
    units still to come by Unit Transfer once the slot exists."""
    mod: object = None
    src_mod: object = None
    faction: str = ""              # its slot in the other mod
    frame: str = ""                # the faction of this mod it is made on
    clone: Optional[fc.ClonePlan] = None
    shared: List[str] = field(default_factory=list)
    bring: List[str] = field(default_factory=list)
    laid: List[str] = field(default_factory=list)       # what was laid over, one line each
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def new(self) -> str:
        return self.clone.new if self.clone else ""

    def payload(self) -> Dict:
        p = self.clone.payload() if self.clone else {"files": [], "assets": [], "ok": False}
        p = dict(p)
        p["errors"] = list(self.errors) + list(p.get("errors") or [])
        p["warnings"] = list(self.warnings) + list(p.get("warnings") or [])
        p["notes"] = list(self.notes) + list(p.get("notes") or [])
        p.update({"bring": True, "faction": self.faction, "frame": self.frame,
                  "from_mod": getattr(self.src_mod, "name", ""),
                  "shared": list(self.shared), "units": list(self.bring),
                  "laid": list(self.laid),
                  "ok": bool(p.get("ok")) and not self.errors})
        return p


def _edit(p: BringPlan, rel: str, label: str = "", encoding: str = fac.ENCODING,
          make: bool = False) -> Optional[fc.FileEdit]:
    """The clone's edit of ``rel``, given the file's text when the clone left it
    alone; a new edit when ``make`` and the clone has none."""
    for e in p.clone.edits:
        if e.rel == rel:
            if not e.text and not e.data:
                path = Path(p.mod.data) / rel
                if not path.is_file():
                    return None
                e.text = kb.read_text(path, e.encoding)
                e.skipped = ""
            return e
    if not make:
        return None
    path, _where = gamepack.lookup(rel, p.mod)
    text = kb.read_text(Path(path), encoding) if path is not None and Path(path).is_file() else ""
    e = fc.FileEdit(rel, label or Path(rel).name, text=text, encoding=encoding)
    p.clone.edits.append(e)
    return e


def _flat(e: fc.FileEdit) -> Tuple[str, str]:
    return kb.to_newline(e.text, "\n"), kb.newline_of(e.text)


def _put(e: fc.FileEdit, text: str, nl: str, n: int = 1) -> None:
    e.text = kb.to_newline(text, nl)
    e.count += n
    e.skipped = ""


def plan(mod, src_mod, body: dict) -> BringPlan:
    """Work out the whole bring without touching the disk.

    ``body``: ``{faction, new, label?, source? (the frame), titles?, art?,
    units?, frame_units?}``."""
    faction = str(body.get("faction") or "").strip().lower()
    p = BringPlan(mod=mod, src_mod=src_mod, faction=faction)
    srf = _roster(src_mod)
    srec = None
    if srf is not None:
        srec = srf.get(faction) or next(
            (r for r in srf.records if fac.slot_of(r.name) == faction), None)
    if srec is None:
        p.errors.append(_i18n.msg("eng.factionbring.not_in_source",
                                  "{faction} is not a faction in {mod}",
                                  faction=faction or "?", mod=getattr(src_mod, "name", "?")))
        p.clone = fc.ClonePlan(mod=mod, new=str(body.get("new") or ""))
        return p
    culture = (srec.get("culture") or "").strip()
    p.frame = frame_for(mod, culture, str(body.get("source") or "").strip().lower())
    src_names = {r["slot"]: r["label"] for r in factions_of(src_mod)}
    label = str(body.get("label") or "").strip() or src_names.get(faction, "")
    want_art = bool(body.get("art", True))
    p.clone = fc.plan(mod, {"source": p.frame, "new": body.get("new"), "label": label,
                            "titles": body.get("titles"), "art": want_art, "rename": False})
    if p.clone.errors:
        return p
    new = p.clone.new

    _lay_record(p, srec, culture)
    _lay_text(p, label)
    _lay_names(p)
    _lay_figures(p)
    if want_art:
        _lay_art(p)
    if body.get("units", True):
        _lay_units(p, bool(body.get("frame_units")))
    else:
        p.notes.append(_i18n.msg("eng.factionbring.units_left",
                                 "Its units were not asked for: {new} fields {frame}'s units, as a clone would.",
                                 new=new, frame=p.frame))
    p.notes.append(_i18n.msg(
        "eng.factionbring.not_brought",
        "Not brought from {mod}: {faction}'s towns, armies and family (give {new} a place in descr_strat.txt), scripts and events naming it, traits only it has, and its shield pictures on the logo sheets ({frame}'s stand in).",
        mod=getattr(src_mod, "name", "?"), faction=faction, new=new, frame=p.frame))
    return p


def _lay_record(p: BringPlan, srec, culture: str) -> None:
    """Culture, religion, colours and the record's own files, the brought
    faction's where this mod can take them."""
    new = p.new
    e = _edit(p, fac.REL)
    if e is None:
        return
    text, nl = _flat(e)
    rf = fac.parse_text(text)
    rec = rf.get(new) or next((r for r in rf.records if fac.slot_of(r.name) == new), None)
    if rec is None:
        return
    here = {fac.slot_of(r.name): r for r in rf.records}
    cultures = {(r.get("culture") or "").strip() for r in here.values()}
    edits: Dict[str, str] = {}
    if culture and culture != rec.get("culture"):
        if culture in cultures:
            edits["culture"] = culture
        else:
            p.warnings.append(_i18n.msg(
                "eng.factionbring.culture_missing",
                "{faction}'s culture {culture} is not in this mod, so {new} keeps {frame}'s ({theirs}).",
                faction=p.faction, culture=culture, new=new, frame=p.frame,
                theirs=rec.get("culture") or "?"))
    religion = (srec.get("religion") or "").strip()
    if religion and religion != rec.get("religion"):
        known = {(r.get("religion") or "").strip() for r in here.values()}
        rt = _read(p.mod, "descr_religions.txt", fac.ENCODING)
        if rt:
            from . import minorfiles
            known |= set(minorfiles.parse_religions(rt).listed)
        if religion in known:
            edits["religion"] = religion
        else:
            p.warnings.append(_i18n.msg(
                "eng.factionbring.religion_missing",
                "{faction}'s religion {religion} is not in this mod, so {new} keeps {frame}'s.",
                faction=p.faction, religion=religion, new=new, frame=p.frame))
    for key in PLAIN_KEYS:
        v = (srec.get(key) or "").strip()
        if v and v != rec.get(key):
            edits[key] = v
    for key in FILE_KEYS:
        v = (srec.get(key) or "").strip()
        if not v or v == rec.get(key):
            continue
        rel = v.replace("\\", "/")
        rel = rel[5:] if rel.lower().startswith("data/") else rel
        if gamepack.exists(rel, p.mod):
            edits[key] = v
            continue
        got, _where = gamepack.lookup(rel, p.src_mod)
        if got is None:
            continue                         # neither mod has it: the frame's line stays
        _bring_file(p, Path(got), rel)
        edits[key] = v
    if not edits:
        return
    block = fac.render_block(rf.block_text(rec), edits)
    _put(e, rf.replace(rec.start, rec.end, block), nl, len(edits))
    p.laid.append(_i18n.msg("eng.factionbring.laid_record",
                            "{rel}: {keys} - {faction}'s own",
                            rel=fac.REL, keys=", ".join(edits), faction=p.faction))


def _bring_file(p: BringPlan, path: Path, rel: str) -> None:
    """One file of the other mod, to the same place under this mod's data/."""
    root = str(path)[:-len(rel)].rstrip("/\\") if str(path).replace("\\", "/").endswith(rel) else ""
    if not root:                             # read out of a pack into the cache: copy it by itself
        root, rel_src = str(path.parent), path.name
    else:
        rel_src = rel
    if any(a.dst == rel for a in p.clone.assets):
        return
    p.clone.assets.append(fc.AssetCopy(rel_src, rel, False, 1, path.stat().st_size, root=root))


def _lay_text(p: BringPlan, label: str) -> None:
    """Every text key of the new slot the clone wrote, given the brought
    faction's value of the same key where its mod has one."""
    theirs = _read(p.src_mod, "text/expanded.txt", LOC_ENCODING)
    e = _edit(p, "text/expanded.txt")
    if not theirs or e is None:
        return
    pairs = dict(stringsbin.from_txt(theirs))
    up_s, up_n = p.faction.upper(), p.new.upper()
    tok = re.compile(fc._key_tok(up_n))
    mine = [t for t, _ in stringsbin.from_txt(e.text) if tok.search(t)]
    writes = {}
    for tag in mine:
        if tag == up_n and label:
            continue                         # the shown name: the one given wins
        src_tag = tok.sub(up_s, tag)
        if src_tag in pairs and pairs[src_tag].strip():
            writes[tag] = pairs[src_tag]
    if not writes:
        return
    text, nl = _flat(e)
    _put(e, stringsbin.upsert_txt(text, writes), nl, 0)
    p.laid.append(_i18n.msg("eng.factionbring.laid_text",
                            "text/expanded.txt: {n} text(s) of {faction}'s",
                            n=len(writes), faction=p.faction))


def _name_sections(lines: List[str]) -> List[Tuple[int, str]]:
    """``[(line, faction)]`` of every ``faction:`` head."""
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*faction:\s*([A-Za-z0-9_]+)", kb.code_of(line))
        if m:
            out.append((i, m.group(1).lower()))
    return out


def _lay_names(p: BringPlan) -> None:
    """The new faction's name lists (the frame's, cloned) made the brought
    faction's, and every name's text ``names.txt`` lacks."""
    theirs = _read(p.src_mod, "descr_names.txt", fac.ENCODING)
    e = _edit(p, "descr_names.txt")
    if not theirs or e is None:
        return
    slines = theirs.split("\n")
    sh = _name_sections(slines)
    k = next((k for k, (_, f) in enumerate(sh) if f == p.faction), None)
    if k is None:
        p.warnings.append(_i18n.msg("eng.factionbring.no_names",
                                    "{faction} has no name lists in {mod}, so {new} keeps {frame}'s.",
                                    faction=p.faction, mod=getattr(p.src_mod, "name", "?"),
                                    new=p.new, frame=p.frame))
        return
    s = sh[k][0]
    end = sh[k + 1][0] if k + 1 < len(sh) else len(slines)
    body = slines[s + 1:end]
    while body and not body[-1].strip():
        body.pop()
    head = re.sub(r"(faction:\s*)[A-Za-z0-9_]+", lambda m: m.group(1) + p.new, slines[s], count=1)
    text, nl = _flat(e)
    lines = text.split("\n")
    th = _name_sections(lines)
    j = next((j for j, (_, f) in enumerate(th) if f == p.new), None)
    if j is None:
        return
    a = th[j][0]
    b = th[j + 1][0] if j + 1 < len(th) else len(lines)
    tail = []
    while b > a + 1 and not lines[b - 1].strip():
        b -= 1
        tail.append("")
    lines[a:b] = [head] + body
    _put(e, "\n".join(lines), nl)
    names = {kb.code_of(x).strip() for x in body}
    names = {n for n in names if n and n not in SECTIONS and " " not in n}
    have_t = _read(p.mod, NAMES_TXT, LOC_ENCODING) or ""
    have = {t.upper() for t, _ in stringsbin.from_txt(have_t)}
    src_t = _read(p.src_mod, NAMES_TXT, LOC_ENCODING) or ""
    src = {t.upper(): v for t, v in stringsbin.from_txt(src_t)}
    add = {n: src[n.upper()] for n in sorted(names) if n.upper() not in have and n.upper() in src}
    if add:
        ne = _edit(p, NAMES_TXT, "Character name text", LOC_ENCODING, make=True)
        if ne is not None:
            t, tnl = (_flat(ne) if ne.text else ("", "\r\n"))
            _put(ne, stringsbin.upsert_txt(t, add), tnl, len(add))
    missing = sorted(n for n in names if n.upper() not in have and n not in add)
    if missing:
        p.warnings.append(_i18n.msg("eng.factionbring.names_no_text",
                                    "{n} of {faction}'s names have a text in neither mod and will show as their raw token: {names}",
                                    n=len(missing), faction=p.faction, names=", ".join(missing[:12])))
    p.laid.append(_i18n.msg("eng.factionbring.laid_names",
                            "descr_names.txt: {faction}'s name lists ({n} name(s), {t} new text(s))",
                            faction=p.faction, n=len(names), t=len(add)))


def _lay_figures(p: BringPlan) -> None:
    """``descr_model_strat.txt``: each figure type this mod has too, its
    ``texture <new>`` line given the brought faction's texture, the picture
    copied in where this mod lacks it."""
    theirs = _read(p.src_mod, "descr_model_strat.txt", fac.ENCODING)
    e = _edit(p, "descr_model_strat.txt")
    if not theirs or e is None:
        return
    tex: Dict[str, str] = {}
    cur = None
    for line in theirs.split("\n"):
        t = kb.code_of(line).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
        elif len(t) >= 3 and t[0] == "texture" and t[1] == p.faction and cur:
            tex[cur] = t[2]
    text, nl = _flat(e)
    lines = text.split("\n")
    n, cur = 0, None
    pat = re.compile(r"^(\s*texture\s+" + re.escape(p.new) + r"\s*,\s*)(\S+)(.*)$")
    for i, line in enumerate(lines):
        t = kb.code_of(line).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
            continue
        m = pat.match(line)
        if not m or cur not in tex or m.group(2) == tex[cur]:
            continue
        rel = tex[cur].replace("\\", "/")
        rel = rel[5:] if rel.lower().startswith("data/") else rel
        if not gamepack.exists(rel, p.mod):
            got, _where = gamepack.lookup(rel, p.src_mod)
            if got is None:
                continue
            _bring_file(p, Path(got), rel)
        lines[i] = m.group(1) + tex[cur] + m.group(3)
        n += 1
    if n:
        _put(e, "\n".join(lines), nl, 0)
        p.laid.append(_i18n.msg("eng.factionbring.laid_figures",
                                "descr_model_strat.txt: {n} campaign-map figure(s) in {faction}'s textures",
                                n=n, faction=p.faction))


def _lay_art(p: BringPlan) -> None:
    """The brought faction's pictures where the frame's copies were going."""
    srf = _roster(p.src_mod)
    slots = sorted({fac.slot_of(r.name) for r in srf.records}) if srf else []
    # The finder skips a destination its mod already has, and its mod here is
    # the OTHER one, where the new slot's name may well be taken (aragon brought
    # as aragon): so it is asked for a name nobody ships, put right after.
    stand_in = "zz_bring_" + p.faction
    hits = fc._asset_hits(p.src_mod, p.faction, stand_in, slots)
    data = Path(p.mod.data)
    for a in hits:
        a.dst = a.dst.replace(stand_in.upper(), p.new.upper()).replace(stand_in, p.new)
    hits = [a for a in hits if not (data / a.dst).exists()]
    if not hits:
        return
    root = str(Path(p.src_mod.data))
    dsts = {a.dst for a in hits}
    # a whole folder of the brought faction's replaces the frame's whole folder,
    # and a single picture the frame's at the same path
    p.clone.assets = [a for a in p.clone.assets
                      if a.root or (a.dst not in dsts
                                    and not any(a.dst.startswith(d + "/") for d in dsts))]
    for a in hits:
        a.root = root
        p.clone.assets.append(a)
    p.laid.append(_i18n.msg("eng.factionbring.laid_art",
                            "{n} art item(s) of {faction}'s, {files} file(s), in place of {frame}'s",
                            n=len(hits), faction=p.faction, files=sum(a.files for a in hits),
                            frame=p.frame))
    # the places the frame filled and the brought faction does not keep the
    # frame's picture, which is said rather than found in game
    left = [a.dst for a in p.clone.assets if not a.root]
    if left:
        p.notes.append(_i18n.msg("eng.factionbring.frame_art_left",
                                 "{n} picture(s) {faction} has none of in {mod} are {frame}'s, as a clone's would be: {list}",
                                 n=len(left), faction=p.faction, mod=getattr(p.src_mod, "name", "?"),
                                 frame=p.frame, list=", ".join(left[:8])))


def _lay_units(p: BringPlan, frame_units: bool) -> None:
    """Which of the brought faction's units this mod already has, alike line
    for line, and which must come by Unit Transfer; the frame's units out of the
    new faction's ownership unless they are asked for."""
    want = own_units(p.src_mod, p.faction)
    src_by = p.src_mod.edu.by_type()
    here_by = p.mod.edu.by_type()
    for u in want:
        mine = here_by.get(u)
        if mine is not None and _sans_ownership(mine.raw) == _sans_ownership(src_by[u].raw):
            p.shared.append(u)
        else:
            p.bring.append(u)
    if not want:
        p.warnings.append(_i18n.msg("eng.factionbring.no_units",
                                    "No unit in {mod} names {faction} in its ownership, so {new} keeps {frame}'s units.",
                                    mod=getattr(p.src_mod, "name", "?"), faction=p.faction,
                                    new=p.new, frame=p.frame))
        frame_units = True
    e = _edit(p, "export_descr_unit.txt")
    if e is None:
        return
    text, nl = _flat(e)
    keep = set(p.shared)
    out, cur, n = [], None, 0
    tok = re.compile(fc._tok(p.new))
    for line in text.split("\n"):
        code = kb.code_of(line)
        t = code.split()
        if t[:1] == ["type"]:
            cur = code.strip()[4:].strip()
        elif t[:1] == ["ownership"]:
            has = bool(tok.search(code))
            if cur in keep and not has:
                line = code.rstrip() + ", " + p.new + line[len(code):]
                n += 1
            elif has and cur not in keep and not frame_units:
                parts = [x.strip() for x in code.strip()[len("ownership"):].split(",")]
                parts = [x for x in parts if x and x != p.new]
                lead = re.match(r"^(\s*ownership\s+)", code).group(1)
                line = lead + ", ".join(parts) + line[len(code):]
                n += 1
        out.append(line)
    if n:
        _put(e, "\n".join(out), nl, 0)
    if not frame_units:
        p.laid.append(_i18n.msg("eng.factionbring.laid_units",
                                "export_descr_unit.txt: {new} owns {shared} unit(s) this mod has just as {faction} has them, and none of {frame}'s",
                                new=p.new, shared=len(p.shared), faction=p.faction, frame=p.frame))
    if p.bring:
        p.notes.append(_i18n.msg("eng.factionbring.units_follow",
                                 "{n} unit(s) of {faction}'s come by Unit Transfer once {new} is written, each its own entry in the Log: {list}",
                                 n=len(p.bring), faction=p.faction, new=p.new, list=", ".join(p.bring)))


# ---------------------------------------------------------------------------
# apply


def apply(p: BringPlan, reload: Callable[[], object]) -> Dict:
    """Write the faction, then bring its units one by one.

    ``reload`` hands back this mod freshly read: every unit is planned against
    the mod as the one before it left it, the way a batch transfer does."""
    from . import transfer as tr
    if p.errors:
        raise ValueError(_i18n.msg("eng.factionclone.cannot_apply", "cannot apply: {why}",
                                   why="; ".join(p.errors)))
    out = fc.apply(p.clone)
    rec = out.get("record") or {}
    rec_opts = rec.setdefault("options", {})
    rec_opts["brought_from"] = f"{getattr(p.src_mod, 'name', '?')}:{p.faction}"
    try:
        from . import config
        config.update_log(rec.get("id", ""), options=rec_opts)
    except Exception:
        pass
    units, failed = [], []
    for u in p.bring:
        dest = reload()
        unit = p.src_mod.edu.by_type().get(u)
        opts = tr.TransferOptions(
            set_recruitment=True,
            field_overrides={"ownership": p.new},
            new_type=f"{u} ({p.new})",
            new_dictionary=f"{unit.dictionary}_{p.new}" if unit else None)
        try:
            tp = tr.plan_transfer(p.src_mod, u, dest, opts)
            if tp.skipped:
                failed.append({"unit": u, "error": "skipped"})
                continue
            got = tr.apply_transfer(tp)
            units.append({"unit": u, "as": tp.resolved_type, "id": got.get("id", "")})
        except Exception as e:             # one unit's trouble never loses the rest
            failed.append({"unit": u, "error": str(e)})
    if units:
        from . import cleaner
        out["strings_bin"] = cleaner.refresh_strings_bin(Path(reload().root), cleaner.STRINGS_BIN_REL)
    out.update({"faction": p.new, "from_mod": getattr(p.src_mod, "name", ""),
                "brought": p.faction, "units": units, "units_failed": failed,
                "shared": list(p.shared)})
    return out
