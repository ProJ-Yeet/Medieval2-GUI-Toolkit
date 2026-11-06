"""A faction's family tree in a campaign's descr_strat.txt, and the pictures that go with it.

The tree is read from the faction's block: the people standing on the map, the
people only on record (the dead, the married-in), and the `relative` lines that
say who is whose father, wife and child. An edit is planned first as a whole,
the complete new text of the file with nothing written, and then applied as one
logged job that Undo can reverse. A named character can be given a portrait of
his own (three small TGA pictures made from one), and a culture's pool of
portraits can be grown, a number at a time, for every age at once.

Written independently from a description of the behaviour (2026-11-06); the
feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import io
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campstrat, config, factions
from . import i18n as _i18n
from .logutil import file_op, log
from .stratchar import PARENT_YEARS

AGES = ("young", "old")
GROUPS = ("generals", "civilians", "rogues", "merchants", "priests", "princesses")

_MAP_KINDS = ("named character", "princess", "family")
_DEFAULT_SIZE = (69, 96)
_NOBODY = "nobody"


class FamilyError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# paths and small helpers


def strat_rel(campaign: str) -> str:
    return f"{campstrat.CAMPAIGN_DIR_REL}/{campstrat.campaign_rel(campaign)}/{campstrat.STRAT_NAME}"


def culture_of(mod, faction: str) -> str:
    try:
        return str(factions.faction_cultures(mod).get(str(faction).lower(), "") or "").lower()
    except Exception:
        return ""


def _low(s) -> str:
    return str(s or "").strip().lower()


def _whole(v) -> Optional[int]:
    s = str(v if v is not None else "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def _load(mod, campaign: str, faction: str):
    try:
        sf = campstrat.read_strat(mod, campaign)
    except OSError as e:
        raise FamilyError(str(e))
    fac = sf.faction(faction)
    if fac is None:
        raise FamilyError(_i18n.msg("eng.stratfamily.no_faction", "{faction} has no block in this campaign's descr_strat.txt", faction=faction))
    return sf, fac


def _map_people(sf, fac) -> List[dict]:
    out = []
    for n in sf.descendants_of(fac, "character"):
        kind = str(n.get("type") or "")
        if kind not in _MAP_KINDS:
            continue
        sex = "female" if kind == "princess" else str(n.get("gender") or "male")
        age = n.get("age")
        out.append({"name": n.name, "source": "map", "kind": kind, "sex": sex,
                    "age": "" if age is None else str(age),
                    "rank": str(n.get("rank") or ""), "portrait": str(n.get("portrait") or ""),
                    "line": n.start + 1})
    return out


def _record_person(n) -> dict:
    p = {"name": n.name, "source": "record", "kind": "record",
         "sex": str(n.get("gender") or "male"),
         "age": "" if n.get("age") is None else str(n.get("age")),
         "rank": str(n.get("leadership") or ""), "line": n.start + 1}
    if n.get("dead") is not None:
        p["dead"] = str(n.get("dead"))
    return p


def _family_of(names: List[str], line: int) -> dict:
    return {"father": names[0], "wife": names[1] if len(names) > 1 else _NOBODY,
            "children": list(names[2:]), "line": line}


# ---------------------------------------------------------------------------
# what the game would trip on


def problems(people, tree) -> List[dict]:
    known = {_low(p.get("name")): p for p in people}
    out: List[dict] = []

    def say(kind, name, message):
        out.append({"kind": kind, "name": name, "message": message})

    first_father: Dict[str, str] = {}
    for fam in tree:
        father, wife = fam.get("father", ""), fam.get("wife", "")
        kids = list(fam.get("children") or [])
        for who in [father, wife] + kids:
            if _low(who) in ("", _NOBODY) or _low(who) in known:
                continue
            say("unknown", who, _i18n.msg("eng.stratfamily.unknown", "{name} is in a relative line but is no character and no record of this faction", name=who))
        w = known.get(_low(wife))
        if w is not None and _low(wife) != _NOBODY and _low(w.get("sex")) != "female":
            say("wife-male", wife, _i18n.msg("eng.stratfamily.wife_male", "{name} is a wife in {father}'s line but is male", name=wife, father=father))
        f = known.get(_low(father))
        if f is not None and _low(f.get("sex")) == "female":
            say("father-female", father, _i18n.msg("eng.stratfamily.father_female", "{name} heads a relative line but is female; the line is the father's", name=father))
        for kid in kids:
            k = _low(kid)
            if not k or k == _NOBODY:
                continue
            if k in first_father and _low(first_father[k]) != _low(father):
                say("two-families", kid, _i18n.msg("eng.stratfamily.two_families", "{name} is a child of both {a} and {b}", name=kid, a=first_father[k], b=father))
            else:
                first_father.setdefault(k, father)

    # whole-tree rules
    below: Dict[str, List[str]] = {}
    for fam in tree:
        kids = [c for c in fam.get("children") or [] if _low(c) not in ("", _NOBODY)]
        for parent in (fam.get("father"), fam.get("wife")):
            if _low(parent) not in ("", _NOBODY):
                below.setdefault(_low(parent), []).extend(_low(c) for c in kids)
    shown: Dict[str, str] = {}
    for fam in tree:
        for who in [fam.get("father"), fam.get("wife")] + list(fam.get("children") or []):
            if _low(who) not in ("", _NOBODY):
                shown.setdefault(_low(who), who)
    for key in [_low(f.get("father")) for f in tree]:
        if key in ("", _NOBODY) or key not in shown:
            continue
        seen, todo = set(), list(below.get(key, []))
        back = False
        while todo:
            cur = todo.pop()
            if cur == key:
                back = True
                break
            if cur not in seen:
                seen.add(cur)
                todo.extend(below.get(cur, []))
        if back:
            name = shown.pop(key)
            say("ancestor", name, _i18n.msg("eng.stratfamily.own_ancestor", "{name} is their own ancestor: follow the children down from {name} and {name} comes back", name=name))

    for fam in tree:
        f = known.get(_low(fam.get("father")))
        fa = _whole(f.get("age")) if f is not None and f.get("dead") is None else None
        if fa is None:
            continue
        for kid in fam.get("children") or []:
            c = known.get(_low(kid))
            ka = _whole(c.get("age")) if c is not None and c.get("dead") is None else None
            if ka is not None and fa - ka < PARENT_YEARS:
                say("years", fam.get("father"), _i18n.msg("eng.stratfamily.years", "{father} is {fa} and {kid} is {ka}, which is {x} years; a living father should be at least {years} years older", father=fam.get("father"), fa=fa, kid=kid, ka=ka, x=fa - ka, years=PARENT_YEARS))

    where: Dict[str, int] = {}
    for i, fam in enumerate(tree):
        where.setdefault(_low(fam.get("father")), i)
    for i, fam in enumerate(tree):
        for kid in fam.get("children") or []:
            j = where.get(_low(kid))
            if j is not None and j < i:
                say("order", fam.get("father"), _i18n.msg("eng.stratfamily.order", "{father}'s line stands below the line of his child {kid}; vanilla writes a father's line above his children's", father=fam.get("father"), kid=kid))
                break
    return out


# ---------------------------------------------------------------------------
# reading


def read(mod, campaign: str, faction: str) -> dict:
    sf, fac = _load(mod, campaign, faction)
    people = _map_people(sf, fac)
    people += [_record_person(n) for n in sf.descendants_of(fac, "character_record")]
    tree = [_family_of(n.get("names"), n.start + 1)
            for n in sf.descendants_of(fac, "relative") if n.get("names")]
    return {"faction": faction, "campaign": campaign, "people": people, "tree": tree,
            "findings": problems(people, tree)}


# ---------------------------------------------------------------------------
# line shapes


def relative_line(father, wife, kids, like: Optional[str] = None) -> str:
    head = "relative\t\t"
    if like:
        m = re.match(r"\s*relative\s+", like, re.I)
        if m:
            head = m.group(0)
    names = [str(father), str(wife or _NOBODY)] + [str(k) for k in kids] + ["end"]
    return head + ", ".join(names)


def record_line(name, sex, age, dead, like: Optional[str] = None) -> str:
    sex = "female" if _low(sex) == "female" else "male"
    life = "dead 0" if dead else "alive"
    if not like:
        return f"character_record\t{name}, {sex}, age {int(age)}, {life}, never_a_leader"
    code = like.split(";", 1)[0].rstrip()
    m = re.match(r"\s*character_record\s+", code, re.I)
    head = m.group(0) if m else "character_record\t"
    parts = [s.strip() for s in code[len(head):].split(",")]
    out = [str(name)]
    for seg in parts[1:]:
        s = seg.lower()
        if s in ("male", "female"):
            out.append(sex)
        elif re.fullmatch(r"age\s+\S+", s):
            out.append(f"age {int(age)}")
        elif s == "alive" or re.fullmatch(r"dead(\s+\S+)?", s):
            out.append(life)
        elif s in campstrat.LEADERSHIP:
            out.append("never_a_leader")
        else:
            out.append(seg)
    return head + ", ".join(out)


# ---------------------------------------------------------------------------
# planning


class _Work:
    """The faction's lines while an edit list is applied to them."""

    def __init__(self, sf, fac):
        self.sf = sf
        self.lines = list(sf.lines)
        self.tags: List[Optional[dict]] = [None] * len(self.lines)
        self.end = fac.end + 1            # one past the faction block
        self.map_people = _map_people(sf, fac)
        self.record_like = None
        for n in sf.descendants_of(fac, "character_record"):
            self.tags[n.start] = {"t": "rec", "p": _record_person(n)}
            if self.record_like is None:
                self.record_like = sf.lines[n.start]
        for n in sf.descendants_of(fac, "relative"):
            if n.get("names"):
                self.tags[n.start] = {"t": "rel", **_family_of(n.get("names"), 0)}

    def at(self, kind: str) -> List[int]:
        return [i for i, t in enumerate(self.tags) if t and t["t"] == kind]

    def put(self, at: int, text: str, tag: dict) -> None:
        self.lines.insert(at, text)
        self.tags.insert(at, tag)
        if at <= self.end:
            self.end += 1

    def drop(self, at: int) -> None:
        del self.lines[at]
        del self.tags[at]
        if at < self.end:
            self.end -= 1

    def persons(self) -> Dict[str, dict]:
        out = {_low(p["name"]): p for p in self.map_people}
        for i in self.at("rec"):
            out[_low(self.tags[i]["p"]["name"])] = self.tags[i]["p"]
        return out

    def families(self) -> List[dict]:
        return [self.tags[i] for i in self.at("rel")]


def _op_record(w: _Work, op: dict, errors: list, changes: list) -> None:
    name = str(op.get("name") or "")
    if not re.fullmatch(r"[^\s,;]+", name):
        errors.append(_i18n.msg("eng.stratfamily.bad_name", "a name is one word with no comma: {name}", name=name))
        return
    if _low(name) in w.persons():
        errors.append(_i18n.msg("eng.stratfamily.taken", "{name} is already a person of this faction", name=name))
        return
    sex = "female" if op.get("sex") == "female" else "male"
    try:
        age = int(op.get("age") or 30) or 30
    except (TypeError, ValueError):
        age = 30
    dead = bool(op.get("dead"))
    recs, rels = w.at("rec"), w.at("rel")
    at = recs[-1] + 1 if recs else rels[0] if rels else w.end
    person = {"name": name, "source": "record", "kind": "record", "sex": sex,
              "age": str(age), "rank": "never_a_leader", "line": 0}
    if dead:
        person["dead"] = "0"
    w.put(at, record_line(name, sex, age, dead, w.record_like), {"t": "rec", "p": person})
    changes.append(_i18n.msg("eng.stratfamily.added_record", "+ {name}, {sex}, age {age}, off the map", name=name, sex=sex, age=age))


def _op_family(w: _Work, op: dict, errors: list, changes: list) -> None:
    father = str(op.get("father") or "").strip()
    if not father:
        return
    wife = str(op.get("wife") or "").strip() or _NOBODY
    kids = [str(c).strip() for c in (op.get("children") or []) if str(c).strip()]
    persons = w.persons()
    bad = False
    for who in [father, wife] + kids:
        if _low(who) != _NOBODY and _low(who) not in persons:
            errors.append(_i18n.msg("eng.stratfamily.no_such", "{name} is no character or record of this faction", name=who))
            bad = True
    if bad:
        return
    rels = w.at("rel")
    mine = next((i for i in rels if _low(w.tags[i]["father"]) == _low(father)), None)
    tag = {"t": "rel", "father": father, "wife": wife, "children": kids, "line": 0}
    if mine is not None:
        old = w.lines[mine]
        text = relative_line(father, wife, kids, like=old)
        if ";" in old:
            text += "\t;" + old.split(";", 1)[1]
        w.lines[mine], w.tags[mine] = text, tag
    else:
        like = w.lines[rels[0]] if rels else None
        kidset = {_low(k) for k in kids}
        above = next((i for i in rels if _low(w.tags[i]["father"]) in kidset), None)
        at = above if above is not None else rels[-1] + 1 if rels else w.end
        w.put(at, relative_line(father, wife, kids, like=like), tag)
    changes.append(_i18n.msg("eng.stratfamily.set_family", "~ {father}: wife {wife}, children {kids}", father=father, wife=wife, kids=", ".join(kids) or "-"))


def plan(mod, campaign: str, faction: str, ops) -> dict:
    sf, fac = _load(mod, campaign, faction)
    w = _Work(sf, fac)
    errors: List[str] = []
    changes: list = []
    for op in ops or []:
        kind = op.get("op") if isinstance(op, dict) else None
        if kind == "record":
            _op_record(w, op, errors, changes)
        elif kind == "family":
            _op_family(w, op, errors, changes)
        elif kind == "drop_family":
            gone = [i for i in w.at("rel") if _low(w.tags[i]["father"]) == _low(op.get("father"))]
            for i in reversed(gone):
                w.drop(i)
            if gone:
                changes.append(_i18n.msg("eng.stratfamily.dropped_family", "- {father}'s relative line", father=op.get("father")))
        elif kind == "drop_record":
            gone = [i for i in w.at("rec") if _low(w.tags[i]["p"]["name"]) == _low(op.get("name"))]
            for i in reversed(gone):
                w.drop(i)
            if gone:
                changes.append(_i18n.msg("eng.stratfamily.dropped_record", "- {name}, off the map", name=op.get("name")))
    people = w.map_people + [w.tags[i]["p"] for i in w.at("rec")]
    text = ""
    if not errors:
        text = sf.newline.join(w.lines) + (sf.newline if sf.trailing_newline else "")
    return {"text": text, "changes": changes, "errors": errors,
            "warnings": [f["message"] for f in problems(people, w.families())],
            "ok": not errors and bool(changes)}


# ---------------------------------------------------------------------------
# writing


def _job(mod, files: Dict[str, bytes], action: str, unit: str, summary, who: str) -> dict:
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    for rel, raw in files.items():
        target = data / rel
        if target.exists():
            copy = backup_root / "data" / rel
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, copy)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {copy}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".new")
        tmp.write_bytes(raw)
        tmp.replace(target)
        file_op("WRITE", target, f"{len(raw)} bytes")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "campmap",
           "action": action, "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": unit,
           "resolved_type": unit, "options": {}, "applied": True, "undone": False,
           "note": "", "summary": summary, "warnings": [], "manifest": manifest,
           "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("FAMILY %s %s in %s, id=%s", action, who, mod.name, tid)
    return rec


def apply(mod, campaign: str, faction: str, ops) -> dict:
    p = plan(mod, campaign, faction, ops)
    if p["errors"]:
        raise FamilyError("; ".join(p["errors"]))
    if not p["changes"]:
        raise FamilyError(_i18n.msg("eng.stratfamily.nothing", "nothing to change"))
    return _job(mod, {strat_rel(campaign): p["text"].encode(campstrat.ENCODING)},
                "family", faction, "\n".join(p["changes"]), faction)


# ---------------------------------------------------------------------------
# portraits


def portrait_folder(faction: str, name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", f"{faction}_{name}").strip("_")


def _size_of(path: Path) -> Optional[Tuple[int, int]]:
    from PIL import Image
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def portrait_size(mod, culture: str) -> Tuple[int, int]:
    data = Path(mod.data)
    own = sorted((data / "ui" / "custom_portraits").glob("*/portrait_young.tga"))
    generals = sorted((data / "ui" / culture / "portraits" / "portraits" / "young" / "generals").glob("*.tga")) if culture else []
    for path in own + generals:
        got = _size_of(path)
        if got:
            return got
    return _DEFAULT_SIZE


def _character(sf, fac, name: str):
    for n in sf.descendants_of(fac, "character"):
        if str(n.get("type") or "") in _MAP_KINDS and _low(n.name) == _low(name):
            return n
    raise FamilyError(_i18n.msg("eng.stratfamily.not_on_map", "{name} is not on the map; off the map the game shows the family picture", name=name))


def plan_portrait(mod, campaign: str, faction: str, name: str) -> dict:
    sf, fac = _load(mod, campaign, faction)
    n = _character(sf, fac, name)
    own = str(n.get("portrait") or "")
    return {"name": n.name, "folder": own or portrait_folder(faction, n.name),
            "line": n.start, "has_line": bool(own),
            "size": list(portrait_size(mod, culture_of(mod, faction)))}


def _fit(raw: bytes, size: Tuple[int, int]):
    """The picture scaled to cover `size` and cropped, faces kept in."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        im = im.convert("RGBA")
    except Exception:
        raise FamilyError(_i18n.msg("eng.stratfamily.not_a_picture", "that file is not a picture this can read (PNG, JPG, TGA, BMP)"))
    w, h = size
    scale = max(w / im.width, h / im.height)
    nw, nh = max(w, round(im.width * scale)), max(h, round(im.height * scale))
    resample = getattr(Image, "Resampling", Image).LANCZOS
    im = im.resize((nw, nh), resample)
    left, top = (nw - w) // 2, int((nh - h) * 0.35)
    return im.crop((left, top, left + w, top + h))


def _tga(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "TGA")
    return buf.getvalue()


def _grey(im):
    from PIL import Image
    g = im.convert("L")
    return Image.merge("RGBA", (g, g, g, im.getchannel("A")))


def set_portrait(mod, campaign: str, faction: str, name: str, raw: bytes) -> dict:
    sf, fac = _load(mod, campaign, faction)
    n = _character(sf, fac, name)
    own = str(n.get("portrait") or "")
    folder = own or portrait_folder(faction, n.name)
    pic = _fit(raw, portrait_size(mod, culture_of(mod, faction)))
    base = f"ui/custom_portraits/{folder}"
    files = {f"{base}/portrait_young.tga": _tga(pic), f"{base}/portrait_old.tga": _tga(pic),
             f"{base}/portrait_dead.tga": _tga(_grey(pic))}
    if not own:
        code, sep, comment = sf.lines[n.start].partition(";")
        lines = list(sf.lines)
        lines[n.start] = code.rstrip() + f", portrait {folder}" + (("\t;" + comment) if sep else "")
        text = sf.newline.join(lines) + (sf.newline if sf.trailing_newline else "")
        files[strat_rel(campaign)] = text.encode(campstrat.ENCODING)
    summary = _i18n.msg("eng.stratfamily.portrait_summary", "{name}: a portrait of his own in {folder}", name=n.name, folder=base)
    return _job(mod, files, "portrait", n.name, summary, n.name)


# ---------------------------------------------------------------------------
# the portrait library


def _pool(mod, culture: str) -> Path:
    return Path(mod.data) / "ui" / culture / "portraits" / "portraits"


def library(mod, culture: str) -> dict:
    pool = _pool(mod, culture)
    groups: Dict[str, Dict[str, int]] = {}
    for age in ("young", "old", "dead"):
        folder = pool / age
        if not folder.is_dir():
            continue
        for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
            groups.setdefault(sub.name, {})[age] = len(list(sub.glob("*.tga")))
        if age == "dead":
            loose = len(list(folder.glob("*.tga")))
            if loose:
                slot = groups.setdefault("generals", {})
                slot["dead"] = slot.get("dead", 0) + loose
    return {"culture": culture, "groups": groups, "size": list(portrait_size(mod, culture))}


def add_to_library(mod, culture: str, group: str, raws) -> dict:
    if group not in GROUPS:
        raise FamilyError(_i18n.msg("eng.stratfamily.bad_group", "no portrait group called {g}", g=group))
    if not raws:
        raise FamilyError(_i18n.msg("eng.stratfamily.no_pictures", "pick at least one picture"))
    size = portrait_size(mod, culture)
    pics = [_fit(r, size) for r in raws]
    pool = _pool(mod, culture)
    dead = pool / "dead" if group == "generals" else pool / "dead" / group
    folders = {"young": pool / "young" / group, "old": pool / "old" / group, "dead": dead}
    top = -1
    for folder in folders.values():
        if folder.is_dir():
            for f in folder.glob("*.tga"):
                if f.stem.isdigit():
                    top = max(top, int(f.stem))
    base = f"ui/{culture}/portraits/portraits"
    files: Dict[str, bytes] = {}
    for i, pic in enumerate(pics):
        num = f"{top + 1 + i:03d}.tga"
        files[f"{base}/young/{group}/{num}"] = _tga(pic)
        files[f"{base}/old/{group}/{num}"] = _tga(pic)
        deadrel = f"{base}/dead/{num}" if group == "generals" else f"{base}/dead/{group}/{num}"
        files[deadrel] = _tga(_grey(pic))
    summary = _i18n.msg("eng.stratfamily.library_summary", "{n} new portraits for {culture}, {group}", n=len(pics), culture=culture, group=group)
    return _job(mod, files, "portraits", f"{culture}/{group}", summary, f"{culture}/{group}")
