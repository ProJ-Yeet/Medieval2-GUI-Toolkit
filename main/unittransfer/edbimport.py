"""A building tree brought in from another mod (Phase 76).

Unit Transfer's own shape at EDB scale: pick one or more building lines in
another installed mod and bring each across whole - the ``building … { … }``
block with its levels, their ``text/export_buildings.txt`` keys, and the
building cards - with a report of what the destination lacks, in one plan and
one Undo. The buildings screen already edits a line in place and writes a new
one from a form (:func:`unittransfer.buildings.plan_new_tree`); this is the
third way a line arrives.

**What the game refuses, and what this does about each.** A building block is
full of names, and a name the destination does not know stops the game at the
loading screen rather than quietly doing nothing. Every one of these was
checked against the destination and each has its own answer:

* a faction or culture in a ``factions { … }`` list: **mapped**. A name the
  destination also has stays; any other is mapped onto one of the
  destination's factions or cultures, or left out of the list. The default is
  the source faction's own culture when the destination has a culture of that
  name, else left out. The two installed mods share almost nothing here -
  3,654 list entries in Divide and Conquer's EDB name something ROCSS lacks.
* a unit in a ``recruit_pool``: **that pool is left out**, and the unit is
  listed. Bringing the unit is Unit Transfer's job; transfer it and plan again,
  and the pool comes across.
* a ``hidden_resource``: **the name is added** to the destination's
  ``hidden_resources`` line. That keeps the clause meaning exactly what it
  meant: no region carries the name yet, so it gates as it did in a campaign
  that never placed it.
* a trade ``resource``, a ``building_present`` or
  ``building_present_min_level`` naming a line or level the destination lacks,
  a religion it lacks: a capability that asks for one is left out; a level
  that asks for one cannot be, so the plan refuses and says which line to add
  to the import.
* ``convert_to`` naming a line the destination lacks: the line is dropped with
  a warning; the building then simply does not convert.

**Not checked: a faction whose levels have a hole.** The game notices a faction
that may build level 3 of a line but not level 2, says so in its log and loads
anyway; Divide and Conquer ships 118 of them. It is not a refusal, so mapping
factions is not held to it.

**A line whose name the destination already has** is refused unless the
request says ``replace``, and is then swapped in place. A level name is the
EDB's one global namespace - text keys, cards and settlement plans all use it
- so a level already used by some other line refuses the plan either way.
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

from . import buildings as B
from . import config, edbvocab, localization, stringsbin
from .logutil import counted, file_op, fingerprint, log

#: The three pictures a level has per culture, and the one a line has, under
#: ``data/ui/<culture>/``. The game looks for exactly these names.
LEVEL_PICTURES = ("buildings/#{c}_{n}.tga", "buildings/#{c}_{n}_constructed.tga",
                  "buildings/construction/#{c}_{n}.tga")
LINE_PICTURES = ("buildings/#{c}_{n}.tga",)

#: The most hidden resources the game's own table holds.
HIDDEN_MAX = 64

_BUILDING_TERMS = ("building_present", "building_present_min_level")


@dataclass
class TreePlan:
    dst: object = None
    source: str = ""
    lines: List[str] = field(default_factory=list)
    replace: bool = False
    edb_text: str = ""
    loc_text: str = ""
    loc_encoding: str = localization.ENCODING
    #: ``(file in the source, data-relative path in the destination)``
    pictures: List[Tuple[Path, str]] = field(default_factory=list)
    pictures_kept: int = 0
    pictures_same: int = 0
    #: the names the destination lacks, and where each one goes
    names: List[dict] = field(default_factory=list)
    units_left: Dict[str, int] = field(default_factory=dict)
    hidden_added: List[str] = field(default_factory=list)
    caps_left: Dict[str, int] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {"source": self.source, "lines": list(self.lines),
                "replace": self.replace, "names": self.names,
                "units_left": [{"unit": u, "pools": n} for u, n in
                               sorted(self.units_left.items(), key=lambda x: x[0].lower())],
                "hidden_added": list(self.hidden_added),
                "caps_left": dict(self.caps_left),
                "pictures": [rel for _, rel in self.pictures],
                "pictures_kept": self.pictures_kept,
                "pictures_same": self.pictures_same,
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.edb_text)}


# ---------------------------------------------------------------------------
# what each side has


class _Vocab:
    """The destination's names, lower-cased for matching."""

    def __init__(self, mod):
        self.fac = {k.lower(): v.lower() for k, v in B.faction_cultures(mod).items()}
        self.cul = {c.lower() for c in edbvocab.cultures(mod)} | set(self.fac.values())
        self.units = {u.type.strip().lower() for u in mod.edu.units}
        self.res = {r.lower() for r in edbvocab.resources(mod)}
        self.rel = {r.lower() for r in edbvocab.religions(mod)}
        self.hidden = list(mod.edb.hidden_resources)

    def knows(self, name: str) -> bool:
        n = name.lower()
        return n == "all" or n in self.fac or n in self.cul


def targets(dst) -> dict:
    """What a name the destination lacks can be mapped onto: its factions, each
    with its culture, and its cultures."""
    fac = B.faction_cultures(dst)
    return {"factions": [{"name": k, "culture": v} for k, v in sorted(fac.items())],
            "cultures": sorted(set(edbvocab.cultures(dst)) | set(fac.values()))}


def sources(src, dst) -> List[dict]:
    """Every building line of ``src``, and whether ``dst`` has one by that name."""
    have = {bl.name for bl in dst.edb.buildings}
    loc = src.building_loc
    out = []
    for bl in src.edb.buildings:
        rec = loc.get(bl.name + "_name")
        out.append({"name": bl.name, "levels": [b.name for b in bl.blocks],
                    "settlement": bl.settlement,
                    "label": (rec.name or "") if rec else "",
                    "units": len({p.unit for b in bl.blocks for p in b.recruits}),
                    "in_dest": bl.name in have})
    return out


# ---------------------------------------------------------------------------
# the requires clauses


def _mapping(src, vocab: _Vocab, names: List[str], asked: Dict[str, str]) -> Dict[str, str]:
    """source name -> destination name ('' = left out), for every name ``dst`` lacks."""
    src_fac = {k.lower(): v.lower() for k, v in B.faction_cultures(src).items()}
    out: Dict[str, str] = {}
    for n in names:
        key = n.lower()
        if key in asked:
            to = str(asked[key] or "").strip()
            out[key] = to if (not to or vocab.knows(to)) else ""
            continue
        culture = src_fac.get(key, "")
        out[key] = culture if culture and culture in vocab.cul else ""
    return out


class _Clause:
    """One clause rewritten for the destination, and what stood in its way."""

    def __init__(self, text: str):
        self.text = text
        self.missing: List[Tuple[str, str]] = []     # (what, name)
        self.hidden: List[str] = []
        self.never = False                           # can no longer be true
        self.changed = False


def _rewrite_clause(clause: str, vocab: _Vocab, mapping: Dict[str, str],
                    lines: Dict[str, Set[str]]) -> _Clause:
    out = _Clause(clause)
    terms = B.parse_clause(clause)
    only_and = all(t.join in ("", "and") for t in terms)
    for t in terms:
        if t.kind == "factions":
            new: List[str] = []
            for v in t.values:
                if vocab.knows(v):
                    to = v
                else:
                    to = mapping.get(v.lower(), "")
                    out.changed = True
                if to and to.lower() not in {x.lower() for x in new}:
                    new.append(to)
            t.values = new
            if not new and not t.negate and only_and:
                out.never = True
        elif t.kind == "hidden_resource":
            if t.values[0] not in vocab.hidden:
                out.hidden.append(t.values[0])
        elif t.kind == "resource":
            if t.values[0].lower() not in vocab.res:
                out.missing.append(("resource", t.values[0]))
        elif t.kind == "region_religion":
            if t.values[0].lower() not in vocab.rel:
                out.missing.append(("religion", t.values[0]))
        elif t.kind in _BUILDING_TERMS:
            have = lines.get(t.values[0])
            if have is None:
                out.missing.append(("building", t.values[0]))
            elif t.kind == "building_present_min_level" and t.values[1] not in have:
                out.missing.append(("level", f"{t.values[0]} {t.values[1]}"))
    if out.changed:
        out.text = B.clause_text(terms)
    return out


def _swap_clause(raw: str, old: str, new: str) -> str:
    """``raw`` with its clause replaced, the rest of the line as it was, or ``''``
    when the clause is not in the line as parsed - the caller then writes the
    whole line afresh rather than let an unmapped name through."""
    at = raw.rfind(old)
    if not old or at < 0:
        return ""
    return raw[:at] + new + raw[at + len(old):]


# ---------------------------------------------------------------------------
# one line's block, rewritten


def _line_block(p: TreePlan, src_edb: B.EdbFile, bl: B.BuildingLine, vocab: _Vocab,
                mapping: Dict[str, str], lines: Dict[str, Set[str]],
                used: Dict[str, int]) -> List[str]:
    headers = {b.header: b for b in bl.blocks}
    caps: Dict[int, B.Capability] = {}
    for b in bl.blocks:
        for c in b.capabilities + b.faction_capabilities:
            caps[c.line] = c
    first_level = min((b.start for b in bl.blocks), default=bl.end)
    nobody: List[str] = []
    out: List[str] = []
    for i in range(bl.start, bl.end):
        raw = src_edb.lines[i]
        code = B._code(raw)
        word = code.split(None, 1)[0] if code else ""
        if i < first_level and word == "convert_to":
            target = code.split()[1] if len(code.split()) > 1 else ""
            if target and target not in lines:
                p.warnings.append(f"{bl.name}: converts to {target!r}, which "
                                  f"{p.dst.name} has no line for, so that line is "
                                  f"dropped and the building does not convert")
                continue
        if i < first_level and word == "religion":
            rel = code.split()[1] if len(code.split()) > 1 else ""
            if rel and rel.lower() not in vocab.rel:
                p.errors.append(f"{bl.name} is a temple of {rel!r}, a religion "
                                f"{p.dst.name} does not have - add the religion first")
        blk = headers.get(i)
        if blk is not None:
            c = _rewrite_clause(blk.requires, vocab, mapping, lines)
            for what, name in c.missing:
                p.errors.append(
                    f"{bl.name}/{blk.name} requires {what} {name!r}, which "
                    f"{p.dst.name} does not have"
                    + (f" - add the {name.split()[0]!r} line to the import"
                       if what in ("building", "level") else ""))
            _note_hidden(p, c)
            if c.never:
                nobody.append(blk.name)
            if c.changed:
                raw = (_swap_clause(raw, blk.requires, c.text)
                       or B._rewrite_header(blk, src_edb.lines, blk.settlement, c.text))
            out.append(raw)
            continue
        cap = caps.get(i)
        if cap is not None:
            why = ""
            if cap.is_recruit:
                pool = cap.pool()
                if pool and pool.unit.strip().lower() not in vocab.units:
                    p.units_left[pool.unit] = p.units_left.get(pool.unit, 0) + 1
                    continue
            elif cap.keyword == "religion":
                rel = (cap.args.split() or [""])[0]
                if rel and rel.lower() not in vocab.rel:
                    why = "a religion the destination lacks"
            c = _rewrite_clause(cap.requires, vocab, mapping, lines)
            if c.missing:
                why = why or f"a {c.missing[0][0]} the destination lacks"
            elif c.never:
                why = why or "no faction left to have it"
            if why:
                p.caps_left[why] = p.caps_left.get(why, 0) + 1
                continue
            _note_hidden(p, c)
            if c.changed:
                raw = (_swap_clause(raw, cap.requires, c.text)
                       or B.Capability(keyword=cap.keyword, args=cap.args,
                                       requires=c.text, indent=cap.indent,
                                       comment=cap.comment).text())
            out.append(raw)
            continue
        out.append(raw)
    if nobody and len(nobody) == len(bl.blocks):
        left = sorted(n for n, k in used.items() if k)
        p.errors.append(f"no faction of {p.dst.name} could build any level of "
                        f"{bl.name} - map at least one of "
                        f"{', '.join(left) or 'its factions'} onto a faction or culture")
    elif nobody:
        p.warnings.append(f"{bl.name}: no faction could build "
                          f"{', '.join(nobody)} once the names are mapped")
    return out


def _note_hidden(p: TreePlan, c: _Clause) -> None:
    for h in c.hidden:
        if h not in p.hidden_added:
            p.hidden_added.append(h)


# ---------------------------------------------------------------------------
# text and pictures


def _pairs(mod) -> Dict[str, str]:
    """``{key: value}`` of a mod's building text, from the ``.txt`` or its cache."""
    path = mod.data / B.LOC_REL
    if path.is_file():
        text, _ = localization.read_file(path)
        return dict(stringsbin.from_txt(text))
    return stringsbin.load_pairs(stringsbin.bin_path_for(path))


def _text(p: TreePlan, src, spans: Dict[str, List[str]], mapping: Dict[str, str],
          vocab: _Vocab, who_names: Set[str]) -> None:
    """The level keys, and each faction's or culture's own wording of them.

    The game reads ``{L}``, ``{L_desc}`` and ``{L_desc_short}`` for every level
    and stops on one that is missing, then ``{L_<faction>…}`` and
    ``{L_<culture>…}`` where a mod words a level its own way for one people.
    Those carry across under the name they are mapped to. ``who_names`` is every
    faction and culture of the source, so ``town_guard_house`` is never read as
    ``town_guard`` worded for someone called ``house``.
    """
    path = p.dst.data / B.LOC_REL
    if not path.is_file():
        p.errors.append(f"{p.dst.name} has no data/{B.LOC_REL}, so the levels "
                        "would have no names, and a level with no text key stops "
                        "the game. Nothing written.")
        return
    have = _pairs(src)
    lower = {k.lower(): k for k in have}
    writes: Dict[str, str] = {}
    filled = 0
    for line, levels in spans.items():
        if line + "_name" in have:
            writes[line + "_name"] = have[line + "_name"]
        for lv in levels:
            for suffix in ("", "_desc", "_desc_short"):
                key = lv + suffix
                if key in have:
                    writes[key] = have[key]
                else:
                    writes[key] = lv.replace("_", " ").title() if not suffix else ""
                    filled += 1
            # the per-faction and per-culture variants, carried to their new name
            head = (lv + "_").lower()
            for low, key in lower.items():
                if not low.startswith(head):
                    continue
                rest = key[len(lv) + 1:]
                who, tail = rest, ""
                for suffix in ("_desc_short", "_desc"):
                    if rest.lower().endswith(suffix):
                        who, tail = rest[:-len(suffix)], suffix
                        break
                if who.lower() not in who_names:
                    continue
                to = who if vocab.knows(who) else mapping.get(who.lower(), "")
                if not to:
                    continue
                new = f"{lv}_{to}{tail}"
                if new not in writes or to == who:
                    writes[new] = have[key]
    if filled:
        p.warnings.append(f"{filled} text key(s) the source does not have were "
                          "written with the level's code name or left blank - the "
                          "game stops on a level with a key missing")
    text, enc = localization.read_file(path)
    p.loc_text = stringsbin.upsert_txt(text, writes)
    p.loc_encoding = enc
    p.changes.append(f"{len(writes)} text key(s) in {B.LOC_REL}")


def _pictures(p: TreePlan, src, spans: Dict[str, List[str]], mapping: Dict[str, str],
              src_fac: Dict[str, str]) -> None:
    """The building cards for each destination culture, from the source's art.

    A culture both mods have takes the source's own picture, over what the
    destination has. A culture only the destination has borrows the picture of
    the source culture mapped onto it, and only where the destination has none.
    """
    dst_cultures = B.cultures_of(p.dst)
    borrow: Dict[str, List[str]] = {}
    fac = {k.lower(): v.lower() for k, v in B.faction_cultures(p.dst).items()}
    for name, to in mapping.items():
        if not to:
            continue
        to_cul = fac.get(to.lower(), to.lower())
        from_cul = src_fac.get(name, name)
        borrow.setdefault(to_cul, [])
        if from_cul not in borrow[to_cul]:
            borrow[to_cul].append(from_cul)
    src_ui = src.data / "ui"
    seen: Dict[Path, Dict[str, Tuple[Path, int]]] = {}
    for culture in dst_cultures:
        own = (src_ui / culture / "buildings").is_dir()
        for line, levels in spans.items():
            for name, shapes in [(line, LINE_PICTURES)] + [(lv, LEVEL_PICTURES) for lv in levels]:
                for shape in shapes:
                    rel = "ui/" + culture + "/" + shape.format(c=culture, n=name)
                    found = None
                    exact = False
                    if own:
                        found = _art(src_ui / culture / shape.format(c=culture, n=name), seen)
                        exact = bool(found)
                    if not found:
                        for other in borrow.get(culture.lower(), []):
                            found = _art(src_ui / other / shape.format(c=other, n=name), seen)
                            if found:
                                break
                    if not found:
                        continue
                    target = p.dst.data / rel
                    there = [t for t in (target, target.with_name(target.name + ".dds"))
                             if t.is_file()]
                    if there and not exact:
                        p.pictures_kept += 1
                        continue
                    for f in found:
                        # the twin keeps its .dds after the destination's name
                        dest = rel + (".dds" if f.name.lower().endswith(".tga.dds") else "")
                        t = p.dst.data / dest
                        if t.is_file() and t.read_bytes() == f.read_bytes():
                            p.pictures_same += 1
                            continue
                        p.pictures.append((f, dest))


def _art(path: Path, seen: Dict[Path, Dict[str, Tuple[Path, int]]]) -> List[Path]:
    """The picture at ``path`` and its ``.tga.dds`` twin, whichever are there.

    ``seen`` holds each folder's listing for the one plan: a culture's
    buildings folder is 300 to 600 files, asked about once per picture, and
    listing it every time was seven seconds of a DaC line into ROCSS.
    """
    folder = path.parent
    names = seen.get(folder)
    if names is None:
        names = {}
        try:
            with os.scandir(folder) as it:
                for e in it:
                    if e.is_file():
                        names[e.name.lower()] = (Path(e.path), e.stat().st_size)
        except OSError:
            pass
        seen[folder] = names
    out = []
    for n in (path.name, path.name + ".dds"):
        hit = names.get(n.lower())
        if hit is not None and hit[1]:
            out.append(hit[0])
    return out


# ---------------------------------------------------------------------------
# the plan


def plan(dst, src, body: dict) -> TreePlan:
    """Work out bringing ``body['lines']`` from ``src`` into ``dst``.

    ``body``: ``{lines: [...], replace: bool, map: {name: dest name or ''},
    pictures: bool}``. Nothing is written.
    """
    want = [str(x).strip() for x in (body.get("lines") or []) if str(x).strip()]
    want = list(dict.fromkeys(want))
    p = TreePlan(dst=dst, source=src.name, lines=want, replace=bool(body.get("replace")))
    if not want:
        p.errors.append("pick at least one building line to bring")
        return p
    if not src.edb_path.is_file():
        p.errors.append(f"{src.name} has no data/{B.EDB_REL}")
        return p
    if not dst.edb_path.is_file():
        p.errors.append(f"{dst.name} has no data/{B.EDB_REL}")
        return p
    src_edb, dst_edb = src.edb, dst.edb
    picked = []
    for name in want:
        bl = src_edb.get(name)
        if bl is None:
            p.errors.append(f"{src.name} has no building line called {name!r}")
        else:
            picked.append(bl)
    if p.errors:
        return p

    # ---- names: lines, levels ----
    replaced = {bl.name for bl in picked if dst_edb.get(bl.name) is not None}
    if replaced and not p.replace:
        for n in sorted(replaced):
            p.errors.append(f"{dst.name} already has a line called {n!r} - tick "
                            "Replace to swap it for this one")
        return p
    taken = {lv: owner for lv, (owner, _) in
             ((k, (v[0].name, v[1])) for k, v in dst_edb.by_level().items())
             if owner not in replaced}
    for bl in picked:
        for b in bl.blocks:
            if b.name in taken:
                p.errors.append(f"{bl.name}/{b.name}: {dst.name} already has a level "
                                f"called {b.name!r}, in its {taken[b.name]!r} line: a "
                                "level name is its text key and its card, so two "
                                "lines cannot share one")
    if p.errors:
        return p
    lines: Dict[str, Set[str]] = {bl.name: {b.name for b in bl.blocks}
                                  for bl in dst_edb.buildings if bl.name not in replaced}
    for bl in picked:
        lines[bl.name] = {b.name for b in bl.blocks}

    # ---- factions and cultures ----
    vocab = _Vocab(dst)
    used: Dict[str, int] = {}
    shown: Dict[str, str] = {}
    for bl in picked:
        for b in bl.blocks:
            for clause in [b.requires] + [c.requires for c in b.capabilities
                                          + b.faction_capabilities]:
                for v in B.clause_factions(clause):
                    if not vocab.knows(v):
                        used[v.lower()] = used.get(v.lower(), 0) + 1
                        shown.setdefault(v.lower(), v)
    asked = {str(k).lower(): v for k, v in (body.get("map") or {}).items()}
    mapping = _mapping(src, vocab, list(used), asked)
    src_fac = {k.lower(): v.lower() for k, v in B.faction_cultures(src).items()}
    src_cul = {c.lower() for c in edbvocab.cultures(src)}
    for key in sorted(used):
        p.names.append({"name": shown[key], "uses": used[key],
                        "kind": ("faction" if key in src_fac else
                                 "culture" if key in src_cul else "unknown"),
                        "culture": src_fac.get(key, ""), "to": mapping[key],
                        "chosen": key in asked})

    # ---- the blocks ----
    blocks: Dict[str, List[str]] = {}
    for bl in picked:
        blocks[bl.name] = _line_block(p, src_edb, bl, vocab, mapping, lines, used)
    if p.errors:
        return p

    # ---- the destination's EDB, spliced ----
    text_lines = list(dst_edb.lines)
    for bl in sorted((dst_edb.get(n) for n in replaced), key=lambda x: -x.start):
        text_lines[bl.start:bl.end] = blocks[bl.name]
    tail: List[str] = []
    for bl in picked:
        if bl.name not in replaced:
            tail += ["\n"] + blocks[bl.name]
    if tail:
        if text_lines and not text_lines[-1].endswith("\n"):
            text_lines[-1] += "\n"
        text_lines += tail
    if p.hidden_added:
        names = list(dst_edb.hidden_resources) + p.hidden_added
        at = dst_edb.hidden_resources_line
        if at >= 0:
            # the line may have moved if a replaced line sat above it - it never
            # does, hidden_resources is the first thing in the file
            text_lines[at] = B._hidden_line(text_lines[at], names)
        else:
            text_lines.insert(0, "hidden_resources " + " ".join(names) + "\n")
        p.changes.append(f"hidden_resources: {', '.join(p.hidden_added)} added, "
                         "so the clauses that name them read as they did")
        if len(names) > HIDDEN_MAX:
            p.warnings.append(f"{len(names)} hidden resources. " + B.HIDDEN_CEILING_NOTE)
    text = "".join(text_lines)
    after = B.parse_text(text)
    for bl in picked:
        got = after.get(bl.name)
        if got is None or len(got.blocks) != len(bl.blocks):
            p.errors.append(f"{bl.name} would come out as an EDB this tool can no "
                            "longer read - refusing to write it")
        # the whole point of the mapping, checked on what would be written
        for b in (got.blocks if got else []):
            for clause in [b.requires] + [c.requires for c in b.capabilities
                                          + b.faction_capabilities]:
                stray = [v for v in B.clause_factions(clause) if not vocab.knows(v)]
                if stray:
                    p.errors.append(f"{bl.name}/{b.name} would still name "
                                    f"{', '.join(stray)}, which {dst.name} does not have")
    if len(after.warnings) > len(dst_edb.warnings):
        p.errors.append("the EDB would read with new warnings: "
                        + "; ".join(after.warnings[len(dst_edb.warnings):][:3]))
    if p.errors:
        return p

    # ---- what the game would refuse ----
    before = {(f["code"], f["message"]) for f in B.tree_check(dst_edb)["findings"]
              if f["severity"] == "fatal"}
    for f in B.tree_check(after)["findings"]:
        if f["severity"] == "fatal" and (f["code"], f["message"]) not in before:
            p.errors.append(f["message"])
    if p.errors:
        return p
    for bl in picked:
        if bl.name.startswith("core_"):
            p.warnings.append(f"{bl.name} is the settlement's own chain: its top "
                              "level has to match each culture's largest settlement "
                              "in descr_cultures.txt, or the game will not load")

    p.edb_text = text
    for bl in picked:
        verb = "replaces the line of that name" if bl.name in replaced else "new line"
        p.changes.append(f"{bl.name}: {verb}, {len(bl.blocks)} level"
                         f"{'' if len(bl.blocks) == 1 else 's'} "
                         f"({', '.join(b.name for b in bl.blocks)})")
    if p.units_left:
        n = sum(p.units_left.values())
        p.warnings.append(f"{n} recruit pool(s) left out: {len(p.units_left)} unit(s) "
                          f"{dst.name} does not have. Transfer them first and plan "
                          "again to keep the pools.")
    for why, n in sorted(p.caps_left.items()):
        p.warnings.append(f"{n} capability line(s) left out: {why}")
    spans = {bl.name: [b.name for b in bl.blocks] for bl in picked}
    _text(p, src, spans, mapping, vocab, set(src_fac) | src_cul)
    if body.get("pictures", True) and not p.errors:
        _pictures(p, src, spans, mapping, src_fac)
        if p.pictures:
            p.changes.append(f"{len(p.pictures)} building card file(s)")
        if p.pictures_kept:
            p.warnings.append(f"{p.pictures_kept} card(s) the destination already "
                              "draws for a culture the source does not have were kept")
    return p


# ---------------------------------------------------------------------------
# writing it


def apply(p: TreePlan) -> dict:
    """Write the EDB, the text and the cards: one backup, one Undo."""
    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.edb_text:
        raise ValueError("nothing to change")
    mod = p.dst
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    fingerprint(mod)

    def keep(rel: str) -> Path:
        target = Path(mod.data) / rel
        if target.exists():
            bpath = backup_root / "data" / rel
            bpath.parent.mkdir(parents=True, exist_ok=True)
            if not bpath.exists():
                shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    target = keep(B.EDB_REL)
    target.write_text(p.edb_text, encoding=B.ENCODING)
    file_op("WRITE", target, f"{', '.join(p.lines)} from {p.source}")
    if p.loc_text:
        target = keep(B.LOC_REL)
        target.write_text(p.loc_text, encoding=p.loc_encoding)
        file_op("WRITE", target, f"{p.loc_encoding}, {len(p.loc_text)} chars")
    for src_file, rel in p.pictures:
        target = keep(rel)
        shutil.copy2(src_file, target)
        file_op("WRITE", target, f"from {p.source}")
    summary = "\n".join([f"building line(s) {', '.join(p.lines)} from {p.source} "
                         f"into {mod.name}"] + [f"  {c}" for c in p.changes])
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "buildings", "action": "building-import",
        "source": p.source, "source_root": "",
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": ", ".join(p.lines), "resolved_type": ", ".join(p.lines),
        "options": {"replace": p.replace},
        "applied": True, "undone": False, "note": "",
        "summary": summary, "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    counted(manifest)
    log.info("BUILD IMPORT %s from %s into %s (%d file(s)), id=%s",
             ", ".join(p.lines), p.source, mod.name,
             len(manifest["backed_up"]) + len(manifest["created"]), tid)
    mod.drop_caches()
    return {"id": tid, "record": rec, "lines": list(p.lines)}
