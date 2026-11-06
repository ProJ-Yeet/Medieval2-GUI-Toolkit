"""Bringing a whole faction over from another installed mod.

The new faction is first made as a clone of a "frame" faction of this mod (one
of the same culture where there is one), so every file the game needs already
names it. The faction being brought then has its own data laid over the clone's
edits before anything is written: its record's colours, religion, culture and
symbol files, its texts, its name lists, the textures of its campaign-map
figures, its pictures, and the ownership of the units both mods have alike.
The units only the other mod has are brought afterwards by Unit Transfer, one
log entry each, once the slot exists. Planning touches no disk; applying
writes through the clone's own writer, so one Undo takes the faction out again.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import factionclone as fc
from . import factions as fac
from . import gamepack
from . import i18n as _i18n
from . import keyblock as kb
from . import minorfiles
from . import stringsbin

FILE_KEYS = ("symbol", "rebel_symbol", "loading_logo", "intro_movie",
             "victory_movie", "defeat_movie", "death_movie")
PLAIN_KEYS = ("primary_colour", "secondary_colour")
NAMES_TXT = "text/names.txt"
LOC_ENCODING = "utf-16"
SECTIONS = ("characters", "surnames", "women", "settlements")

_EXPANDED = "text/expanded.txt"
_EDU = "export_descr_unit.txt"
_NAMES = "descr_names.txt"
_STRAT_MODELS = "descr_model_strat.txt"
_STAND_IN = "zz_bring_"


@dataclass
class BringPlan:
    mod: object = None
    src_mod: object = None
    faction: str = ""
    frame: str = ""
    clone: Optional[fc.ClonePlan] = None
    shared: List[str] = field(default_factory=list)
    bring: List[str] = field(default_factory=list)
    laid: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def new(self) -> str:
        return (self.clone.new if self.clone else "") or ""

    def payload(self) -> Dict:
        out = (self.clone.payload() if self.clone
               else {"files": [], "assets": [], "ok": False})
        clone_ok = bool(out.get("ok"))
        for key, own in (("errors", self.errors), ("warnings", self.warnings),
                         ("notes", self.notes)):
            out[key] = list(own) + list(out.get(key) or [])
        out.update({
            "bring": True, "faction": self.faction, "frame": self.frame,
            "from_mod": getattr(self.src_mod, "name", ""),
            "shared": list(self.shared), "units": list(self.bring),
            "laid": list(self.laid),
            "ok": clone_ok and not self.errors,
        })
        return out


# ---------------------------------------------------------------------------
# reading


def _read(mod, rel: str, encoding: str) -> Optional[str]:
    """A file as the game would find it for ``mod``, or None."""
    try:
        path, _ = gamepack.lookup(rel, mod)
        if path is None:
            return None
        return kb.read_text(Path(path), encoding)
    except (OSError, UnicodeError, ValueError):
        return None


def _roster(mod) -> Optional[object]:
    text = _read(mod, fac.REL, fac.ENCODING)
    return None if text is None else fac.parse_text(text)


def _find(rf, slot: str):
    if rf is None:
        return None
    return rf.get(slot) or next(
        (r for r in rf.records if fac.slot_of(r.name) == slot), None)


def _texts(mod) -> Dict[str, str]:
    text = _read(mod, _EXPANDED, LOC_ENCODING)
    if text is not None:
        return dict(stringsbin.from_txt(text))
    try:
        return dict(fac.loc(mod))
    except Exception:
        return {}


def _clean_rel(value: str) -> str:
    rel = (value or "").replace("\\", "/").strip().lstrip("/")
    return rel[5:] if rel.lower().startswith("data/") else rel


def factions_of(mod) -> List[Dict]:
    rf = _roster(mod)
    if rf is None:
        return []
    texts = _texts(mod)
    rows = []
    for rec in rf.records:
        slot = fac.slot_of(rec.name)
        if not slot or slot == "slave":
            continue
        rows.append({"slot": slot, "culture": rec.get("culture") or "",
                     "label": texts.get(slot.upper()) or slot})
    return rows


def frame_for(mod, culture: str, prefer: str = "") -> str:
    rf = _roster(mod)
    if rf is None:
        return ""
    cands = [(fac.slot_of(r.name), r) for r in rf.records
             if fac.slot_of(r.name) not in fac.HOMELESS_BARRED_SLOTS
             and not r.get("special_faction_type")]
    if prefer and any(s == prefer for s, _ in cands):
        return prefer
    return next((s for s, r in cands if culture and r.get("culture") == culture),
                cands[0][0] if cands else "")


def own_units(src_mod, faction: str) -> List[str]:
    return [u.type for u in src_mod.edu.units
            if faction in [o.strip().lower() for o in u.ownership]]


# ---------------------------------------------------------------------------
# the clone's file edits, read and written back


def _edit_for(p: BringPlan, rel: str):
    return next((e for e in p.clone.edits if e.rel == rel), None)


def _working(p: BringPlan, rel: str, encoding: str) -> Optional[str]:
    """The text the clone will write for ``rel``, or this mod's file when the
    clone left it alone; None when there is neither."""
    e = _edit_for(p, rel)
    if e is not None and e.text:
        return e.text
    return _read(p.mod, rel, encoding)


def _store(p: BringPlan, rel: str, label: str, text: str, encoding: str) -> None:
    e = _edit_for(p, rel)
    if e is None:
        p.clone.edits.append(fc.FileEdit(rel, label, text=text, encoding=encoding))
        return
    e.text, e.skipped = text, ""
    if e.encoding != encoding:
        e.encoding = encoding


def _schedule(p: BringPlan, rel: str) -> bool:
    """Copy ``rel`` from the source mod when the clone does not already."""
    if any(a.dst == rel and a.root for a in p.clone.assets):
        return True
    try:
        path, _ = gamepack.lookup(rel, p.src_mod)
    except (OSError, ValueError):
        return False
    if path is None:
        return False
    path = Path(path)
    try:
        src, root = path.relative_to(Path(p.src_mod.data)).as_posix(), str(p.src_mod.data)
    except ValueError:
        src, root = path.name, str(path.parent)
    p.clone.assets.append(fc.AssetCopy(src, rel, False, 1, path.stat().st_size, root=root))
    return True


# ---------------------------------------------------------------------------
# the parts


def _lay_record(p: BringPlan, srcrec) -> None:
    text = _working(p, fac.REL, fac.ENCODING)
    if text is None:
        return
    rf = fac.parse_text(text)
    rec = _find(rf, p.new)
    here = _roster(p.mod)
    if rec is None:
        return
    new, faction, frame = p.new, p.faction, p.frame
    edits: Dict[str, str] = {}
    copies: List[str] = []

    culture = srcrec.get("culture")
    if culture and culture != rec.get("culture"):
        if here is not None and any(r.get("culture") == culture for r in here.records):
            edits["culture"] = culture
        else:
            p.warnings.append(_i18n.msg(
                "eng.factionbring.culture_missing",
                "{faction}'s culture {culture} is not in this mod, so {new} keeps {frame}'s ({theirs}).",
                faction=faction, culture=culture, new=new, frame=frame,
                theirs=rec.get("culture") or "?"))
    religion = srcrec.get("religion")
    if religion and religion != rec.get("religion"):
        known = {r.get("religion") for r in (here.records if here else [])}
        rtext = _read(p.mod, "descr_religions.txt", fac.ENCODING)
        if rtext is not None:
            known.update(minorfiles.parse_religions(rtext).listed)
        if religion in known:
            edits["religion"] = religion
        else:
            p.warnings.append(_i18n.msg(
                "eng.factionbring.religion_missing",
                "{faction}'s religion {religion} is not in this mod, so {new} keeps {frame}'s.",
                faction=faction, religion=religion, new=new, frame=frame))
    for key in PLAIN_KEYS:
        value = srcrec.get(key)
        if value and value != rec.get(key):
            edits[key] = value
    for key in FILE_KEYS:
        value = srcrec.get(key)
        if not value or value == rec.get(key):
            continue
        rel = _clean_rel(value)
        if gamepack.exists(rel, p.mod):
            edits[key] = value
        elif gamepack.lookup(rel, p.src_mod)[0] is not None:
            copies.append(rel)
            edits[key] = value
    if not edits:
        return
    try:
        block = fac.render_block(rf.block_text(rec), edits)
    except fac.FactionError:
        return
    for rel in copies:
        _schedule(p, rel)
    _store(p, fac.REL, "Faction roster", rf.replace(rec.start, rec.end, block),
           fac.ENCODING)
    p.laid.append(_i18n.msg(
        "eng.factionbring.laid_record", "{rel}: {keys} - {faction}'s own",
        rel=fac.REL, keys=", ".join(edits), faction=faction))


def _lay_text(p: BringPlan, label: str) -> None:
    text = _working(p, _EXPANDED, LOC_ENCODING)
    theirs = _read(p.src_mod, _EXPANDED, LOC_ENCODING)
    if text is None or theirs is None:
        return
    src_texts = dict(stringsbin.from_txt(theirs))
    tok = re.compile(fc._key_tok(p.new.upper()))
    writes: Dict[str, str] = {}
    for tag, _ in stringsbin.from_txt(text):
        if not tok.search(tag):
            continue
        value = src_texts.get(tok.sub(lambda m: p.faction.upper(), tag), "")
        if not value.strip() or (label and tag == p.new.upper()):
            continue
        writes[tag] = value
    if not writes:
        return
    _store(p, _EXPANDED, "Faction name and event text",
           stringsbin.upsert_txt(text, writes), LOC_ENCODING)
    p.laid.append(_i18n.msg(
        "eng.factionbring.laid_text", "text/expanded.txt: {n} text(s) of {faction}'s",
        n=len(writes), faction=p.faction))


_HEAD = re.compile(r"^\s*faction\s*:\s*(\S+)", re.I)


def _section(lines: List[str], slot: str) -> Optional[Tuple[int, int]]:
    """``[start, end)`` of a ``faction: slot`` section, trailing blanks off."""
    heads = [(i, m.group(1).lower()) for i, ln in enumerate(lines)
             for m in [_HEAD.match(ln)] if m]
    for n, (i, name) in enumerate(heads):
        if name == slot:
            end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return i, end
    return None


def _lay_names(p: BringPlan) -> None:
    text = _working(p, _NAMES, fac.ENCODING)
    theirs = _read(p.src_mod, _NAMES, fac.ENCODING)
    if text is None or theirs is None:
        return
    nl = kb.newline_of(text)
    mine = kb.to_newline(text, "\n").split("\n")
    other = kb.to_newline(theirs, "\n").split("\n")
    at, got = _section(mine, p.new), _section(other, p.faction)
    if got is None:
        p.warnings.append(_i18n.msg(
            "eng.factionbring.no_names",
            "{faction} has no name lists in {mod}, so {new} keeps {frame}'s.",
            faction=p.faction, mod=p.src_mod.name, new=p.new, frame=p.frame))
        return
    if at is None:
        return
    body = [re.sub(r"(?i)faction\s*:\s*\S+", "faction: " + p.new, other[got[0]], count=1)]
    body += other[got[0] + 1:got[1]]
    mine[at[0]:at[1]] = body
    _store(p, _NAMES, "Character names", kb.to_newline("\n".join(mine), nl),
           fac.ENCODING)

    names: List[str] = []
    for line in body[1:]:
        code = line.split(";", 1)[0].strip()
        if code and code.lower() not in SECTIONS and " " not in code and "\t" not in code \
                and code not in names:
            names.append(code)
    mytxt = _read(p.mod, NAMES_TXT, LOC_ENCODING)
    theirtxt = _read(p.src_mod, NAMES_TXT, LOC_ENCODING)
    have = {k.lower() for k, _ in stringsbin.from_txt(mytxt or "")}
    src_has = {k.lower(): (k, v) for k, v in stringsbin.from_txt(theirtxt or "")}
    adds: Dict[str, str] = {}
    neither: List[str] = []
    for name in names:
        low = name.lower()
        if low in have:
            continue
        if low in src_has:
            key, value = src_has[low]
            adds[key] = value
        else:
            neither.append(name)
    if adds:
        base = _working(p, NAMES_TXT, LOC_ENCODING)
        _store(p, NAMES_TXT, "Character name text",
               stringsbin.upsert_txt(base if base is not None else "\r\n", adds),
               LOC_ENCODING)
    if neither:
        p.warnings.append(_i18n.msg(
            "eng.factionbring.names_no_text",
            "{n} of {faction}'s names have a text in neither mod and will show as their raw token: {names}",
            n=len(neither), faction=p.faction, names=", ".join(sorted(neither)[:12])))
    p.laid.append(_i18n.msg(
        "eng.factionbring.laid_names",
        "descr_names.txt: {faction}'s name lists ({n} name(s), {t} new text(s))",
        faction=p.faction, n=len(names), t=len(adds)))


_TYPE_LINE = re.compile(r"^\s*type\s+(\S.*?)\s*$")


def _figure_textures(lines: List[str], slot: str) -> Dict[str, Tuple[int, str]]:
    """``{figure type: (line index, path)}`` for the ``texture <slot>, path`` lines."""
    rx = re.compile(r"^\s*texture\s+" + re.escape(slot) + r"\s*,\s*(\S+)", re.I)
    found, cur = {}, None
    for i, ln in enumerate(lines):
        code = ln.split(";", 1)[0]
        m = _TYPE_LINE.match(code)
        if m:
            cur = m.group(1)
            continue
        m = rx.match(code)
        if m and cur is not None and cur not in found:
            found[cur] = (i, m.group(1))
    return found


def _lay_figures(p: BringPlan) -> None:
    text = _working(p, _STRAT_MODELS, fac.ENCODING)
    theirs = _read(p.src_mod, _STRAT_MODELS, fac.ENCODING)
    if text is None or theirs is None:
        return
    nl = kb.newline_of(text)
    mine = kb.to_newline(text, "\n").split("\n")
    ours = _figure_textures(mine, p.new)
    brought = _figure_textures(kb.to_newline(theirs, "\n").split("\n"), p.faction)
    done = 0
    for figure, (i, path) in ours.items():
        want = brought.get(figure)
        if want is None or want[1] == path:
            continue
        rel = _clean_rel(want[1])
        if not gamepack.exists(rel, p.mod) and not _schedule(p, rel):
            continue
        mine[i] = re.sub(r"^(\s*texture\s+" + re.escape(p.new) + r"\s*,\s*)\S+",
                         lambda m: m.group(1) + want[1], mine[i], count=1, flags=re.I)
        done += 1
    if not done:
        return
    _store(p, _STRAT_MODELS, "Campaign map models",
           kb.to_newline("\n".join(mine), nl), fac.ENCODING)
    p.laid.append(_i18n.msg(
        "eng.factionbring.laid_figures",
        "descr_model_strat.txt: {n} campaign-map figure(s) in {faction}'s textures",
        n=done, faction=p.faction))


def _lay_art(p: BringPlan, src_rf) -> None:
    slots = sorted({fac.slot_of(r.name) for r in src_rf.records})
    mine = Path(p.mod.data)
    pat = re.compile(re.escape(_STAND_IN + p.faction), re.I)

    def named(m):
        return p.new.upper() if m.group(0).isupper() else p.new

    items: List[fc.AssetCopy] = []
    for hit in fc._asset_hits(p.src_mod, p.faction, _STAND_IN + p.faction, slots):
        dst = pat.sub(named, hit.dst)
        if (mine / dst).exists():
            continue
        items.append(fc.AssetCopy(hit.src, dst, hit.is_dir, hit.files, hit.bytes,
                                  root=str(p.src_mod.data)))
    if items:
        dsts = [a.dst for a in items]
        p.clone.assets = [
            a for a in p.clone.assets
            if a.root or not any(a.dst == d or a.dst.startswith(d + "/") for d in dsts)]
        p.clone.assets.extend(items)
        p.laid.append(_i18n.msg(
            "eng.factionbring.laid_art",
            "{n} art item(s) of {faction}'s, {files} file(s), in place of {frame}'s",
            n=len(items), faction=p.faction, files=sum(a.files for a in items),
            frame=p.frame))
    left = [a.dst for a in p.clone.assets if not a.root]
    if left:
        p.notes.append(_i18n.msg(
            "eng.factionbring.frame_art_left",
            "{n} picture(s) {faction} has none of in {mod} are {frame}'s, as a clone's would be: {list}",
            n=len(left), faction=p.faction, mod=p.mod.name, frame=p.frame,
            list=", ".join(left[:8])))


def _signature(raw: str) -> List[Tuple[str, ...]]:
    sig = []
    for line in raw.splitlines():
        code = line.split(";", 1)[0].replace(",", " , ").split()
        if code and code[0] != "ownership":
            sig.append(tuple(code))
    return sig


def _split_units(p: BringPlan, owned: List[str]) -> None:
    try:
        here = p.mod.edu.by_type()
        theirs = p.src_mod.edu.by_type()
    except Exception:
        here, theirs = {}, {}
    for name in owned:
        mine, src = here.get(name), theirs.get(name)
        if mine is not None and src is not None \
                and _signature(mine.raw) == _signature(src.raw):
            p.shared.append(name)
        else:
            p.bring.append(name)


_OWN = re.compile(r"^(\s*ownership\s+)([^;]*?)(\s*(?:;.*)?)$")


def _set_ownership(text: str, new: str, shared: List[str], drop: bool) -> str:
    nl = kb.newline_of(text)
    lines = kb.to_newline(text, "\n").split("\n")
    cur = None
    for i, ln in enumerate(lines):
        m = _TYPE_LINE.match(ln.split(";", 1)[0])
        if m:
            cur = m.group(1)
            continue
        m = _OWN.match(ln)
        if not m or cur is None:
            continue
        owners = [o.strip() for o in m.group(2).split(",") if o.strip()]
        if cur in shared:
            if new not in owners:
                owners.append(new)
        elif drop and new in owners:
            owners.remove(new)
        else:
            continue
        lines[i] = m.group(1) + ", ".join(owners) + m.group(3)
    return kb.to_newline("\n".join(lines), nl)


def _lay_units(p: BringPlan, want_units: bool, frame_units: bool) -> None:
    new, faction, frame = p.new, p.faction, p.frame
    if not want_units:
        p.notes.append(_i18n.msg(
            "eng.factionbring.units_left",
            "Its units were not asked for: {new} fields {frame}'s units, as a clone would.",
            new=new, frame=frame))
        return
    owned = own_units(p.src_mod, faction)
    if not owned:
        p.warnings.append(_i18n.msg(
            "eng.factionbring.no_units",
            "No unit in {mod} names {faction} in its ownership, so {new} keeps {frame}'s units.",
            mod=p.src_mod.name, faction=faction, new=new, frame=frame))
        return
    _split_units(p, owned)
    text = _working(p, _EDU, fac.ENCODING)
    if text is not None:
        _store(p, _EDU, "Unit roster ownership",
               _set_ownership(text, new, p.shared, not frame_units), fac.ENCODING)
    if not frame_units:
        p.laid.append(_i18n.msg(
            "eng.factionbring.laid_units",
            "export_descr_unit.txt: {new} owns {shared} unit(s) this mod has just as {faction} has them, and none of {frame}'s",
            new=new, shared=len(p.shared), faction=faction, frame=frame))
    if p.bring:
        p.notes.append(_i18n.msg(
            "eng.factionbring.units_follow",
            "{n} unit(s) of {faction}'s come by Unit Transfer once {new} is written, each its own entry in the Log: {list}",
            n=len(p.bring), faction=faction, new=new, list=", ".join(p.bring)))


# ---------------------------------------------------------------------------
# plan and apply


def plan(mod, src_mod, body: dict) -> BringPlan:
    given = str(body.get("faction") or "").strip().lower()
    new = str(body.get("new") or "").strip().lower()
    p = BringPlan(mod=mod, src_mod=src_mod, faction=given)
    src_rf = _roster(src_mod)
    srcrec = _find(src_rf, given) if given else None
    if srcrec is None:
        p.clone = fc.ClonePlan(mod=mod, new=new)
        p.errors.append(_i18n.msg(
            "eng.factionbring.not_in_source", "{faction} is not a faction in {mod}",
            faction=given or "?", mod=getattr(src_mod, "name", "") or "?"))
        return p
    p.faction = fac.slot_of(srcrec.name)
    p.frame = frame_for(mod, srcrec.get("culture") or "",
                        str(body.get("source") or "").strip().lower())
    label = str(body.get("label") or "").strip() or _texts(src_mod).get(p.faction.upper()) \
        or p.faction
    want_art = bool(body.get("art", True))
    p.clone = fc.plan(mod, {"source": p.frame, "new": new, "label": label,
                            "titles": body.get("titles"), "art": want_art,
                            "rename": False})
    if p.clone.errors:
        return p

    _lay_record(p, srcrec)
    _lay_text(p, label)
    _lay_names(p)
    _lay_figures(p)
    if want_art:
        _lay_art(p, src_rf)
    _lay_units(p, bool(body.get("units", True)), bool(body.get("frame_units", False)))
    p.notes.append(_i18n.msg(
        "eng.factionbring.not_brought",
        "Not brought from {mod}: {faction}'s towns, armies and family (give {new} a place in descr_strat.txt), scripts and events naming it, traits only it has, and its shield pictures on the logo sheets ({frame}'s stand in).",
        mod=src_mod.name, faction=p.faction, new=p.new, frame=p.frame))
    return p


def apply(p: BringPlan, reload: Callable[[], object]) -> Dict:
    from . import cleaner, config, transfer

    if p.errors:
        raise ValueError(_i18n.msg("eng.factionclone.cannot_apply",
                                   "cannot apply: {why}", why="; ".join(p.errors)))
    out = fc.apply(p.clone)
    new, src_mod = p.new, p.src_mod
    record = out.get("record") or {}
    record.setdefault("options", {})["brought_from"] = f"{src_mod.name}:{p.faction}"
    try:
        config.update_log(record.get("id") or out["id"], options=record["options"])
    except Exception:
        pass

    done: List[Dict] = []
    failed: List[Dict] = []
    for unit in p.bring:
        try:
            dest = reload()
            known = src_mod.edu.by_type().get(unit)
            opts = transfer.TransferOptions(
                set_recruitment=True, field_overrides={"ownership": new},
                new_type=f"{unit} ({new})",
                new_dictionary=f"{known.dictionary}_{new}" if known else None)
            tp = transfer.plan_transfer(src_mod, unit, dest, opts)
            if tp.skipped:
                failed.append({"unit": unit, "error": "skipped"})
                continue
            res = transfer.apply_transfer(tp)
            done.append({"unit": unit, "as": tp.resolved_type, "id": res.get("id")})
        except Exception as e:
            failed.append({"unit": unit, "error": str(e)})
    if done:
        out["strings_bin"] = cleaner.refresh_strings_bin(
            Path(reload().root), cleaner.STRINGS_BIN_REL)
    out.update({"faction": new, "from_mod": src_mod.name, "brought": p.faction,
                "units": done, "units_failed": failed, "shared": list(p.shared)})
    return out
