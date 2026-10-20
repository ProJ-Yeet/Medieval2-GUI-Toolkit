"""A faction's family tree, edited as a tree; portraits of one's own; the portrait library (96e3).

From the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW / M2TW Campaign
Editor's ``family.py`` and ``portraits.py``, with its author's permission:
the record line written in the file's own form, the portrait folders and the
way a portrait of one's own is named. The tree itself is drawn by the page.

**What descr_strat.txt says.** A faction block holds its people on the map
(``character Denethor, named character, male, leader, age 50, ...``), the
people off the map (``character_record Ecthelion, male, age 98, dead 0,
past_leader``) and one ``relative`` line per father: ``relative Denethor,
Finduilas, Boromir, Faramir, end`` - the father, his wife (or ``nobody``), then
the children. The game draws the family tree from those lines alone.

**Edits** are a list of operations, planned together and written as one job:
``family`` sets one father's line (his wife and children, in order), adding it
when he has none; ``record`` adds a person off the map; ``drop_family`` and
``drop_record`` take one out. New records go after the faction's last record
(else before its first relative line), new lines after its last relative
line, each written like the lines already there.

**Portraits.** On Medieval II a named character may carry ``portrait
<folder>``: the game shows ``ui/custom_portraits/<folder>/portrait_young.tga``,
``_old`` and ``_dead`` for him instead of one from his culture's pool. One
picture makes all three at the size the mod's other portraits use. The pool is
``ui/<culture>/portraits/portraits/<young|old|dead>/<group>/NNN.tga``, the same
number the same man at every age, so a new portrait goes in at the next free
number of every age folder of its group at once.
"""
from __future__ import annotations

import io
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import campstrat, config
from . import i18n as _i18n
from .logutil import file_op, log

AGES = ("young", "old")
GROUPS = ("generals", "civilians", "rogues", "merchants", "priests", "princesses")


class FamilyError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _faction(sf, faction: str):
    node = sf.faction(faction)
    if node is None:
        raise FamilyError(_i18n.msg("eng.stratfamily.no_faction", "{faction} has no block in this campaign's descr_strat.txt", faction=faction))
    return node


def read(mod, campaign: str, faction: str) -> Dict:
    sf = campstrat.read_strat(mod, campaign)
    node = _faction(sf, faction)
    people = []
    for c in sf.descendants_of(node, "character"):
        if (c.get("type") or "") not in ("named character", "princess", "family"):
            continue
        people.append({"name": c.name, "source": "map", "kind": c.get("type") or "",
                       "sex": c.get("gender") or ("female" if c.get("type") == "princess" else "male"),
                       "age": c.get("age"), "rank": c.get("rank") or "",
                       "portrait": c.get("portrait") or "", "line": c.start + 1})
    for r in sf.descendants_of(node, "character_record"):
        people.append({"name": r.name, "source": "record", "kind": "record",
                       "sex": r.get("gender") or "male", "age": r.get("age"),
                       "dead": r.get("dead"), "rank": r.get("leadership") or "",
                       "line": r.start + 1})
    tree = []
    for rel in sf.descendants_of(node, "relative"):
        names = list(rel.get("names") or [])
        if names:
            tree.append({"father": names[0], "wife": names[1] if len(names) > 1 else "nobody",
                         "children": names[2:], "line": rel.start + 1})
    return {"faction": faction, "campaign": campaign, "people": people, "tree": tree,
            "findings": problems(people, tree)}


def problems(people: List[Dict], tree: List[Dict]) -> List[Dict]:
    """What the game would trip on: a name in a line nobody is called; a child in
    two families; a wife who is a man, a father who is a woman."""
    by = {p["name"].lower(): p for p in people}
    out = []
    seen: Dict[str, str] = {}
    for fam in tree:
        for role, name in [("father", fam["father"]), ("wife", fam["wife"])] + [("child", c) for c in fam["children"]]:
            if not name or name.lower() == "nobody":
                continue
            p = by.get(name.lower())
            if p is None:
                out.append({"kind": "unknown", "name": name, "message": _i18n.msg("eng.stratfamily.unknown", "{name} is in a relative line but is no character and no record of this faction", name=name)})
                continue
            if role == "wife" and p["sex"] != "female":
                out.append({"kind": "wife-male", "name": name, "message": _i18n.msg("eng.stratfamily.wife_male", "{name} is a wife in {father}'s line but is male", name=name, father=fam["father"])})
            if role == "father" and p["sex"] == "female":
                out.append({"kind": "father-female", "name": name, "message": _i18n.msg("eng.stratfamily.father_female", "{name} heads a relative line but is female; the line is the father's", name=name)})
            if role == "child":
                k = name.lower()
                if k in seen and seen[k] != fam["father"]:
                    out.append({"kind": "two-families", "name": name, "message": _i18n.msg("eng.stratfamily.two_families", "{name} is a child of both {a} and {b}", name=name, a=seen[k], b=fam["father"])})
                seen[k] = fam["father"]
    return out


# ---------------------------------------------------------------------------
# lines in the file's own form


def relative_line(father: str, wife: str, kids: List[str], like: Optional[str] = None) -> str:
    head = re.match(r"\s*relative\s*", like).group(0) if like else "relative\t\t"
    return head + ", ".join([father, wife or "nobody"] + list(kids) + ["end"])


def record_line(name: str, sex: str, age: int, dead: bool, like: Optional[str] = None) -> str:
    """A character_record line, another record as the pattern (the editor's
    record_line): its head, its other words kept, sex, age and alive/dead set."""
    if like:
        code = like.split(";", 1)[0].rstrip()
        head = re.match(r"\s*character_record\s*", code).group(0)
        parts = [p.strip() for p in code[len(head):].split(",")]
        rest = []
        for p in parts[1:]:
            if p in ("male", "female"):
                p = sex
            elif p.startswith("age"):
                p = f"age {int(age)}"
            elif p.split()[:1] in (["alive"], ["dead"]):
                p = "dead 0" if dead else "alive"
            elif p in ("past_leader", "never_a_leader", "leader"):
                p = "never_a_leader"
            rest.append(p)
        return f"{head}{name}, " + ", ".join(rest)
    return f"character_record\t{name}, {sex}, age {int(age)}, {'dead 0' if dead else 'alive'}, never_a_leader"


def plan(mod, campaign: str, faction: str, ops: List[Dict]) -> Dict:
    """The whole new descr_strat.txt for these family edits, without writing it."""
    sf = campstrat.read_strat(mod, campaign)
    node = _faction(sf, faction)
    lines = list(sf.lines)
    have = read(mod, campaign, faction)
    names = {p["name"].lower() for p in have["people"]}
    rels = {r.name.lower(): r for r in sf.descendants_of(node, "relative") if r.name}
    recs = {r.name.lower(): r for r in sf.descendants_of(node, "character_record") if r.name}
    rel_like = lines[next(iter(rels.values())).start] if rels else None
    rec_like = lines[next(iter(recs.values())).start] if recs else None
    last_rec = max((r.start for r in recs.values()), default=None)
    first_rel = min((r.start for r in rels.values()), default=None)
    last_rel = max((r.start for r in rels.values()), default=None)
    # where things go, as (line index to insert before, order) - applied bottom up
    inserts: List[Tuple[int, int, str]] = []
    replace: Dict[int, Optional[str]] = {}
    changes, errors = [], []
    end = node.end
    rec_at = (last_rec + 1) if last_rec is not None else (first_rel if first_rel is not None else end)
    rel_at = (last_rel + 1) if last_rel is not None else end
    tree = {f["father"].lower(): dict(f) for f in have["tree"]}
    people = list(have["people"])
    for n, op in enumerate(ops or []):
        kind = op.get("op")
        if kind == "record":
            name = str(op.get("name") or "").strip()
            if not re.fullmatch(r"[^\s,;]+", name):
                errors.append(_i18n.msg("eng.stratfamily.bad_name", "a name is one word with no comma: {name}", name=name or "''"))
                continue
            if name.lower() in names:
                errors.append(_i18n.msg("eng.stratfamily.taken", "{name} is already a person of this faction", name=name))
                continue
            sex = "female" if op.get("sex") == "female" else "male"
            age = int(op.get("age") or 30)
            inserts.append((rec_at, n, record_line(name, sex, age, bool(op.get("dead")), rec_like)))
            names.add(name.lower())
            people.append({"name": name, "source": "record", "sex": sex, "age": age})
            changes.append(_i18n.msg("eng.stratfamily.added_record", "+ {name}, {sex}, age {age}, off the map", name=name, sex=sex, age=age))
        elif kind == "family":
            father = str(op.get("father") or "").strip()
            wife = str(op.get("wife") or "").strip() or "nobody"
            kids = [str(k).strip() for k in (op.get("children") or []) if str(k).strip()]
            for who in [father, wife] + kids:
                if who.lower() != "nobody" and who.lower() not in names:
                    errors.append(_i18n.msg("eng.stratfamily.no_such", "{name} is no character or record of this faction", name=who))
            old = rels.get(father.lower())
            if old is not None:
                replace[old.start] = relative_line(father, wife, kids, sf.lines[old.start])
            else:
                inserts.append((rel_at, n, relative_line(father, wife, kids, rel_like)))
            tree[father.lower()] = {"father": father, "wife": wife, "children": kids}
            changes.append(_i18n.msg("eng.stratfamily.set_family", "~ {father}: wife {wife}, children {kids}", father=father, wife=wife, kids=", ".join(kids) or "-"))
        elif kind == "drop_family":
            old = rels.get(str(op.get("father") or "").lower())
            if old is not None:
                replace[old.start] = None
                tree.pop(old.name.lower(), None)
                changes.append(_i18n.msg("eng.stratfamily.dropped_family", "- {father}'s relative line", father=old.name))
        elif kind == "drop_record":
            old = recs.get(str(op.get("name") or "").lower())
            if old is not None:
                replace[old.start] = None
                names.discard(old.name.lower())
                people = [p for p in people if p["name"].lower() != old.name.lower()]
                changes.append(_i18n.msg("eng.stratfamily.dropped_record", "- {name}, off the map", name=old.name))
    for i, new in replace.items():
        if new is None:
            lines[i] = None
        else:
            comment = sf.lines[i].split(";", 1)[1] if ";" in sf.lines[i] else ""
            lines[i] = new + (("\t;" + comment) if comment else "")
    for at, _n, text in sorted(inserts, key=lambda t: (-t[0], -t[1])):
        lines.insert(at, text)
    out = [x for x in lines if x is not None]
    text = sf.newline.join(out) + (sf.newline if sf.trailing_newline and out else "")
    warns = [f["message"] for f in problems(people, list(tree.values()))]
    return {"text": "" if errors else text, "changes": changes, "errors": errors, "warnings": warns,
            "ok": not errors and bool(changes)}


def _write(mod, rels_bytes: Dict[str, bytes], action: str, who: str, summary: str) -> Dict:
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    data = Path(mod.data)
    for rel, raw in rels_bytes.items():
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
        tmp = target.with_name(target.name + ".new")
        tmp.write_bytes(raw)
        tmp.replace(target)
        file_op("WRITE", target, action)
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "campmap",
           "action": action, "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": who, "resolved_type": who,
           "options": {}, "applied": True, "undone": False, "note": "", "summary": summary,
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("FAMILY %s %s in %s, id=%s", action, who, mod.name, tid)
    return rec


def strat_rel(campaign: str) -> str:
    return f"{campstrat.CAMPAIGN_DIR_REL}/{campaign}/{campstrat.STRAT_NAME}"


def apply(mod, campaign: str, faction: str, ops: List[Dict]) -> Dict:
    p = plan(mod, campaign, faction, ops)
    if p["errors"]:
        raise FamilyError("; ".join(p["errors"]))
    if not p["changes"]:
        raise FamilyError(_i18n.msg("eng.stratfamily.nothing", "nothing to change"))
    return _write(mod, {strat_rel(campaign): p["text"].encode(campstrat.ENCODING)}, "family", faction,
                  "\n".join(p["changes"]))


# ---------------------------------------------------------------------------
# portraits


def culture_of(mod, faction: str) -> str:
    from . import factions as fa
    try:
        return fa.faction_cultures(mod).get(faction, "")
    except Exception:  # noqa: BLE001
        return ""


def _picture(raw: bytes):
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        return im.convert("RGBA")
    except (OSError, ValueError, SyntaxError):
        raise FamilyError(_i18n.msg("eng.stratfamily.not_a_picture", "that file is not a picture this can read (PNG, JPG, TGA, BMP)")) from None


def _tga(im, size) -> bytes:
    from PIL import Image, ImageOps
    out = ImageOps.fit(im, tuple(size), Image.LANCZOS, centering=(0.5, 0.35))
    buf = io.BytesIO()
    out.save(buf, "TGA")
    return buf.getvalue()


def portrait_size(mod, culture: str) -> Tuple[int, int]:
    from PIL import Image
    data = Path(mod.data)
    for d in sorted((data / "ui" / "custom_portraits").glob("*/portrait_young.tga"))[:1]:
        with Image.open(d) as im:
            return im.size
    folder = data / "ui" / culture / "portraits" / "portraits" / "young" / "generals"
    for f in sorted(folder.glob("*.tga"))[:1]:
        with Image.open(f) as im:
            return im.size
    return (69, 96)


def portrait_folder(faction: str, name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", f"{faction}_{name}").strip("_")


def plan_portrait(mod, campaign: str, faction: str, name: str) -> Dict:
    sf = campstrat.read_strat(mod, campaign)
    node = _faction(sf, faction)
    ch = next((c for c in sf.descendants_of(node, "character") if c.name.lower() == name.lower()), None)
    if ch is None:
        raise FamilyError(_i18n.msg("eng.stratfamily.not_on_map", "{name} is not on the map; off the map the game shows the family picture", name=name))
    folder = ch.get("portrait") or portrait_folder(faction, ch.name)
    return {"name": ch.name, "folder": folder, "line": ch.start, "has_line": bool(ch.get("portrait")),
            "size": list(portrait_size(mod, culture_of(mod, faction)))}


def set_portrait(mod, campaign: str, faction: str, name: str, raw: bytes) -> Dict:
    """His own portrait at every age from one picture, and ``portrait <folder>``
    on his line when it has none."""
    p = plan_portrait(mod, campaign, faction, name)
    im = _picture(raw)
    base = f"ui/custom_portraits/{p['folder']}"
    files = {f"{base}/portrait_{a}.tga": _tga(im, p["size"]) for a in AGES}
    from PIL import ImageOps
    files[f"{base}/portrait_dead.tga"] = _tga(ImageOps.grayscale(im).convert("RGBA"), p["size"])
    if not p["has_line"]:
        sf = campstrat.read_strat(mod, campaign)
        lines = list(sf.lines)
        code, sep, comment = lines[p["line"]].partition(";")
        lines[p["line"]] = code.rstrip() + f", portrait {p['folder']}" + (("\t;" + comment) if sep else "")
        text = sf.newline.join(lines) + (sf.newline if sf.trailing_newline else "")
        files[strat_rel(campaign)] = text.encode(campstrat.ENCODING)
    return _write(mod, files, "portrait", p["name"],
                  _i18n.msg("eng.stratfamily.portrait_summary", "{name}: a portrait of his own in {folder}", name=p["name"], folder=base))


def library(mod, culture: str) -> Dict:
    """``{group: {age: count}}`` of the culture's pool, the mod's own folders."""
    root = Path(mod.data) / "ui" / culture / "portraits" / "portraits"
    out: Dict[str, Dict[str, int]] = {}
    for age in ("young", "old", "dead"):
        d = root / age
        if not d.is_dir():
            continue
        for g in sorted(x for x in d.iterdir() if x.is_dir()):
            out.setdefault(g.name, {})[age] = len(list(g.glob("*.tga")))
        if age == "dead":
            loose = len(list(d.glob("*.tga")))
            if loose:
                out.setdefault("generals", {})["dead"] = loose
    return {"culture": culture, "groups": out, "size": list(portrait_size(mod, culture))}


def add_to_library(mod, culture: str, group: str, raws: List[bytes]) -> Dict:
    """New portraits for a group: each at the next free number of every age
    folder of the group at once (young, old, and dead for generals), so the same
    number stays the same man."""
    if group not in GROUPS:
        raise FamilyError(_i18n.msg("eng.stratfamily.bad_group", "no portrait group called {g}", g=group))
    if not raws:
        raise FamilyError(_i18n.msg("eng.stratfamily.no_pictures", "pick at least one picture"))
    root = Path(mod.data) / "ui" / culture / "portraits" / "portraits"
    folders = [root / "young" / group, root / "old" / group]
    folders.append(root / "dead" if group == "generals" else root / "dead" / group)
    taken = set()
    for f in folders:
        taken |= {int(x.stem) for x in f.glob("*.tga") if x.stem.isdigit()}
    size = portrait_size(mod, culture)
    files: Dict[str, bytes] = {}
    nxt = max(taken, default=-1) + 1
    from PIL import ImageOps
    for raw in raws:
        im = _picture(raw)
        for f in folders:
            pic = ImageOps.grayscale(im).convert("RGBA") if f.name == "dead" or f.parent.name == "dead" else im
            rel = (f / f"{nxt:03d}.tga").relative_to(Path(mod.data)).as_posix()
            files[rel] = _tga(pic, size)
        nxt += 1
    return _write(mod, files, "portraits", f"{culture}/{group}",
                  _i18n.msg("eng.stratfamily.library_summary", "{n} new portraits for {culture}, {group}", n=len(raws), culture=culture, group=group))
