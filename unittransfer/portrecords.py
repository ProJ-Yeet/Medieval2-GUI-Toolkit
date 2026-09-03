"""Copy a trait or an ancillary out of one mod and into another.

Every other editor in the toolkit works on one mod. This is the one that reads
two, and it exists because "port the retinue from that mod" is the job people
were doing by hand: find the block in the other mod's file, paste it in, then
remember that a trait is never only its block.

A trait or an ancillary is **three things in two files**, and a port that brings
one of them is worse than no port at all:

  * **the definition block** - the ``Trait`` / ``Ancillary`` lines at the top of
    the file. Pasted alone, the record exists and nothing ever grants it.
  * **the triggers that give it** - hundreds of lines below, past
    ``;== TRIGGER DATA ==`` in the same file, keyed by ``Affects <trait>`` or
    ``AcquireAncillary <name>``. Left behind, the record is unreachable; brought
    without the definition, the trigger is the "Trait not recognized" error.
  * **its text keys** - in ``text/export_VnVs.txt`` for a trait,
    ``text/export_ancillaries.txt`` for an ancillary. Left behind, the character
    screen crashes the first time anyone has it. This is not a cosmetic third:
    it is the half that turns a working port into a save-game-ending one.

So all three move together, in one job, with one backup set and one undo - the
same contract every other write in the toolkit makes.

What this deliberately does NOT do
----------------------------------
**It does not rewrite what the block refers to.** A ported trait keeps its
``Characters``, its ``ExcludeCultures`` and its ``AntiTraits``; a ported
ancillary keeps its ``Image`` and its ``ExcludedAncillaries``; the triggers keep
every condition they had. Those name cultures, religions, other traits and
picture files that the destination mod may not have - and guessing a
substitution is how a port silently becomes a different trait. Instead every one
of them is CHECKED against the destination and reported before the write, so the
list of what will not work is in front of you while it is still a preview.

**It does not copy pictures.** An ancillary's ``Image`` is a ``.tga`` under
``data/ui/ancillaries``; the port says when the destination has not got it, and
the Images tool is what puts one there.

The two record types are one module because they are one format. The EDA is the
EDCT with the level ladder taken out - same header keywords, same trigger
language underneath, same "its name is a key in a text file" - which is already
why :mod:`unittransfer.triggers` serves both. :data:`KINDS` is the whole of the
difference between them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from . import ancillaries, keyblock as kb, traits, triggers
from .logutil import log


class PortError(ValueError):
    """The port cannot be planned - a missing file, or a record that is not there."""


@dataclass(frozen=True)
class Kind:
    """Everything that differs between porting a trait and porting an ancillary."""
    id: str
    noun: str
    module: object
    #: the ``Mod`` property naming the file this record lives in
    path_attr: str
    #: the trigger effect keyword that names one of these records
    keyword: str
    #: where the shown text lives, relative to ``data/``, and its compiled cache
    loc_rel: str
    loc_bin_rel: str
    #: the attribute on the parsed file holding the records, in file order
    records_attr: str


KINDS: Dict[str, Kind] = {
    "traits": Kind(id="traits", noun="trait", module=traits, path_attr="edct_path",
                   keyword="Affects", loc_rel=traits.VNV_REL,
                   loc_bin_rel=traits.VNV_BIN_REL, records_attr="traits"),
    "ancillaries": Kind(id="ancillaries", noun="ancillary", module=ancillaries,
                        path_attr="eda_path", keyword="AcquireAncillary",
                        loc_rel=ancillaries.LOC_REL,
                        loc_bin_rel=ancillaries.LOC_BIN_REL,
                        records_attr="ancillaries"),
}


def kind(kind_id: str) -> Kind:
    k = KINDS.get(str(kind_id or "").strip())
    if k is None:
        raise PortError(f"{kind_id!r} is not something this can port")
    return k


# ---------------------------------------------------------------------------
# reading the two mods


def _path(mod, k: Kind) -> Path:
    return Path(getattr(mod, k.path_attr))


def _read(mod, k: Kind):
    """The mod's whole file, parsed both ways: as records and as triggers.

    Both halves come out of ONE read of ONE file. They are two views of the same
    bytes - :mod:`unittransfer.traits` reads the top of it and
    :mod:`unittransfer.triggers` the bottom - and reading the file twice is how
    they would end up disagreeing about it.
    """
    path = _path(mod, k)
    if not path.exists():
        raise PortError(f"{getattr(mod, 'name', '?')} has no {path.name}")
    text = kb.read_text(path, k.module.ENCODING)
    return text, k.module.parse_text(text), triggers.parse_text(text)


def _records(parsed, k: Kind) -> list:
    return getattr(parsed, k.records_attr)


def givers(tf: triggers.TriggerFile, keyword: str, name: str) -> List[triggers.Trigger]:
    """Every trigger in a file that names ``name`` through ``keyword``.

    Not :func:`triggers.orphaned_by`, which asks the narrower question a DELETE
    needs ("does this trigger serve ONLY that record"). A port wants every
    trigger that feeds the record, including one that feeds two - it is copied
    whole, and what it does for the other record is said in the warnings rather
    than edited out. Editing a trigger down on the way through would produce a
    trigger the source mod does not have and nobody asked for.
    """
    out = []
    for trig in tf.triggers:
        if any(e.keyword == keyword and e.args and e.args[0] == name
               for e in trig.effects):
            out.append(trig)
    return out


def overview(source, dest, kind_id: str) -> Dict:
    """Every record the source mod has, and what the destination makes of it."""
    k = kind(kind_id)
    _text, parsed, tf = _read(source, k)
    here = set()
    dest_error = ""
    try:
        _dtext, dparsed, _dtf = _read(dest, k)
        here = set(dparsed.by_name())
    except PortError as e:
        dest_error = str(e)
    names = k.module.loc(source)
    rows = []
    for rec in _records(parsed, k):
        rows.append({
            "name": rec.name,
            "label": k.module.label(rec, names),
            "triggers": len(givers(tf, k.keyword, rec.name)),
            "keys": len(k.module.text_tags(rec)),
            "exists": rec.name in here,
        })
    return {
        "kind": k.id, "noun": k.noun,
        "source": getattr(source, "name", ""), "dest": getattr(dest, "name", ""),
        "file": _path(source, k).name,
        "records": rows,
        "count": len(rows),
        "already": sum(1 for r in rows if r["exists"]),
        "dest_error": dest_error,
    }


# ---------------------------------------------------------------------------
# the plan


@dataclass
class PortPlan:
    source: object = None
    dest: object = None
    kind: Optional[Kind] = None
    names: List[str] = field(default_factory=list)
    with_triggers: bool = True
    overwrite: bool = False
    #: the destination file as it would be written - empty when nothing changes
    text: str = ""
    #: ``{tag: text}`` this port would write into the destination's text file
    loc_writes: Dict[str, str] = field(default_factory=dict)
    loc_new: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    #: per record: what came, and what the destination has not got
    rows: List[Dict] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    def summary(self) -> str:
        head = (f"port {len(self.rows)} {self.kind.noun if self.kind else 'record'}(s) "
                f"from {getattr(self.source, 'name', '?')} into "
                f"{getattr(self.dest, 'name', '?')}")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> Dict:
        return {"kind": self.kind.id if self.kind else "",
                "source": getattr(self.source, "name", ""),
                "dest": getattr(self.dest, "name", ""),
                "names": list(self.names), "rows": list(self.rows),
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors), "skipped": list(self.skipped),
                "loc_writes": dict(self.loc_writes), "loc_new": list(self.loc_new),
                "ok": not self.errors and bool(self.text or self.loc_writes)}


def plan(source, dest, kind_id: str, names: Sequence[str],
         with_triggers: bool = True, overwrite: bool = False) -> PortPlan:
    """Work out the whole write, against both mods, without touching either.

    Nothing is decided per record in isolation: each one is spliced into the text
    the last one produced, so two records that both land above the trigger
    section do not compute their insertion point against the same stale line
    numbers.
    """
    k = kind(kind_id)
    p = PortPlan(source=source, dest=dest, kind=k, names=[str(n) for n in names],
                 with_triggers=bool(with_triggers), overwrite=bool(overwrite))
    if source is dest or getattr(source, "name", 1) == getattr(dest, "name", 2):
        p.errors.append("the source and the destination are the same mod")
        return p
    if not p.names:
        p.errors.append(f"pick at least one {k.noun} to port")
        return p
    try:
        _stext, sparsed, stf = _read(source, k)
        text, _dparsed, _dtf = _read(dest, k)
    except PortError as e:
        p.errors.append(str(e))
        return p

    original = text
    known = _dest_vocab(dest)
    for name in p.names:
        rec = sparsed.get(name)
        if rec is None:
            p.errors.append(f"{name} is not {_a(k.noun)} in {source.name}")
            return p
        text = _port_one(p, k, text, sparsed, stf, rec, known)
    p.text = "" if text == original else text
    _plan_loc(p, k, sparsed)
    if not p.text and not p.loc_writes and not p.errors:
        p.warnings.append("nothing to change")
    return p


def _a(noun: str) -> str:
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun


def _port_one(p: PortPlan, k: Kind, text: str, sparsed, stf, rec, known) -> str:
    """One record, its triggers and its findings, spliced into ``text``."""
    parsed = k.module.parse_text(text)
    block = sparsed.block_text(rec)
    here = parsed.get(rec.name)
    row: Dict = {"name": rec.name, "triggers": [], "keys": [], "missing": []}

    if here is not None and not p.overwrite:
        p.skipped.append(rec.name)
        p.warnings.append(
            f"{p.dest.name} already has {_a(k.noun)} called `{rec.name}` - it was "
            "left alone. Tick “replace what is already there” to overwrite it")
        return text
    if here is not None:
        text = k.module.replace_block(parsed, here, block)
        p.changes.append(f"~ {rec.name} replaced ({len(block.splitlines())} lines)")
    else:
        text = _insert(parsed, block)
        p.changes.append(f"+ {rec.name} ({len(block.splitlines())} lines)")

    if p.with_triggers:
        text = _port_triggers(p, k, text, stf, rec.name, row)
    row["missing"] = _missing_in_dest(k, rec, known, p.dest)
    for note in row["missing"]:
        p.warnings.append(f"{rec.name}: {note}")
    row["keys"] = list(k.module.text_tags(rec))
    p.rows.append(row)
    return text


def _insert(parsed, block: str) -> str:
    """``block`` under the last definition, above the trigger section.

    Never at the end of the file: the engine stops reading definitions at the
    first ``Trigger``, so a block written below one is a block it has already
    stopped looking for. The same rule :func:`traits._insert_trait` writes by,
    over whichever of the two files this is.
    """
    lines = list(parsed.lines)
    recs = getattr(parsed, "traits", None)
    if recs is None:
        recs = getattr(parsed, "ancillaries", [])
    at = (recs[-1].end if recs
          else (parsed.trigger_start if parsed.trigger_start >= 0 else len(lines)))
    body = [ln[:-1] if ln.endswith("\r") else ln for ln in block.split("\n")]
    lines[at:at] = [""] + body
    out = parsed.newline.join(lines)
    return out + parsed.newline if parsed.trailing_newline and lines else out


def _port_triggers(p: PortPlan, k: Kind, text: str, stf, name: str, row: Dict) -> str:
    """The triggers that give this record, copied whole and appended.

    Appended, never inserted: the engine reads triggers in order, and the end is
    the only position that cannot change when an existing trigger fires. A
    trigger whose NAME the destination already uses is skipped with a warning
    rather than renamed - a trigger name is what the destination's own file
    already refers to, and quietly writing a second one under a new name would
    make the record fire twice.
    """
    for trig in givers(stf, k.keyword, name):
        dtf = triggers.parse_text(text)
        if dtf.get(trig.name) is not None:
            p.warnings.append(
                f"{name}: {p.dest.name} already has a trigger called "
                f"`{trig.name}`, so it was not copied - check that the one it "
                "has still does what this record needs")
            continue
        text = triggers.append_block(dtf, stf.block_text(trig))
        row["triggers"].append(trig.name)
        p.changes.append(f"+ trigger {trig.name}")
        others = sorted({e.args[0] for e in trig.effects
                         if e.keyword == k.keyword and e.args and e.args[0] != name})
        if others:
            p.warnings.append(
                f"{name}: trigger `{trig.name}` also gives {kb.and_list(others)} - "
                f"port {'those' if len(others) > 1 else 'that'} too, or the "
                "trigger names something this mod has not got")
    if not row["triggers"] and p.with_triggers:
        p.warnings.append(f"{name}: no trigger in {p.source.name} gives it, so "
                          "nothing in the destination will either")
    return text


def _dest_vocab(dest) -> Dict[str, set]:
    """What the destination mod HAS, for the "will this work over there" checks.

    Every lookup is wrapped: a mod with no cultures file is a mod this cannot
    check, which is not the same as a mod where every culture is missing. An
    empty set here means "not checked" and the caller reports nothing.
    """
    from . import minorfiles
    out: Dict[str, set] = {"cultures": set(), "religions": set(), "traits": set(),
                           "ancillaries": set()}
    try:
        out["cultures"] = set(minorfiles.culture_names(dest))
    except (OSError, AttributeError, ValueError):
        pass
    try:
        out["religions"] = set(minorfiles.religion_names(dest))
    except (OSError, AttributeError, ValueError):
        pass
    for key, k in (("traits", KINDS["traits"]), ("ancillaries", KINDS["ancillaries"])):
        try:
            out[key] = set(_read(dest, k)[1].by_name())
        except (PortError, OSError, ValueError):
            pass
    return out


def _missing_in_dest(k: Kind, rec, known: Dict[str, set], dest) -> List[str]:
    """What this record names that the destination has not got.

    Reported, never rewritten - see the module docstring. Each line is something
    that will not work over there and that a person has to decide about.
    """
    out: List[str] = []

    def gone(kind_name: str, wanted, label: str) -> None:
        have = known.get(kind_name) or set()
        if not have:
            return                      # could not be checked; not "all missing"
        missing = [w for w in wanted if w and w not in have]
        if missing:
            out.append(f"{label} {kb.and_list(sorted(set(missing)))} - "
                       f"not in {getattr(dest, 'name', 'the destination')}")

    gone("cultures", getattr(rec, "exclude_cultures", []) or [],
         "its ExcludeCultures line names")
    if k.id == "traits":
        gone("traits", rec.anti_traits, "its AntiTraits line names")
    else:
        gone("ancillaries", rec.excluded_ancillaries,
             "its ExcludedAncillaries line names")
        image = (rec.get("Image") or "").strip()
        if image and ancillaries.image_path(dest, image) is None:
            out.append(f"its picture `{image}` is not in "
                       f"{getattr(dest, 'name', 'the destination')} - the port "
                       "does not copy art, so add it with the Images tool")
    return out


def _plan_loc(p: PortPlan, k: Kind, sparsed) -> None:
    """The text keys this port owes the destination, and where they come from.

    A key the destination already has is left alone unless the port is
    overwriting: two mods using one tag for different words is ordinary, and
    silently retyping the destination's own wording is not what "port this
    trait" asked for.
    """
    from . import stringsbin
    txt = Path(p.dest.data) / k.loc_rel
    have = k.module.loc(p.dest)
    theirs = k.module.loc(p.source)
    if not txt.exists() and not stringsbin.bin_path_for(txt).exists():
        p.warnings.append(
            f"{p.dest.name} has no {Path(k.loc_rel).name}, so no text key could be "
            f"written - every ported {k.noun} will show its tags in game")
        return
    for row in p.rows:
        for tag in row["keys"]:
            words = (theirs.get(tag) or "").strip()
            if tag not in have:
                p.loc_writes[tag] = words or tag
                p.loc_new.append(tag)
                if not words:
                    p.warnings.append(
                        f"{row['name']}: `{tag}` has no wording in {p.source.name} "
                        "either, so it is created with the tag as placeholder text")
            elif p.overwrite and words and words != have[tag]:
                p.loc_writes[tag] = words
    if p.loc_new:
        p.changes.append(f"+ {len(p.loc_new)} text key(s) in {Path(k.loc_rel).name}")
    reworded = len(p.loc_writes) - len(p.loc_new)
    if reworded:
        p.changes.append(f"~ {reworded} text(s) rewritten in {Path(k.loc_rel).name}")


# ---------------------------------------------------------------------------
# writing


def apply(p: PortPlan) -> Dict:
    """Write a planned port, with the same backups and undo as any other job.

    Both files go into one job's backup folder and one manifest, because they
    fail together: a definition written without its text keys is a crash the
    first time anyone gets the record, and an undo that put back one of the two
    would leave exactly that.
    """
    import shutil
    import time

    from . import cleaner, config, stringsbin
    from .logutil import file_op

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text and not p.loc_writes:
        raise ValueError("nothing to change")
    k = p.kind
    dest = p.dest
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    out: Dict = {"id": tid, "kind": k.id, "names": list(p.names)}

    def keep(rel: str) -> Path:
        target = Path(dest.data) / rel
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

    if p.text:
        target = keep(_path(dest, k).name)
        kb.write_text(target, p.text, k.module.ENCODING)
        file_op("WRITE", target, f"{len(p.text)} bytes")
    if p.loc_writes:
        txt = Path(dest.data) / k.loc_rel
        if txt.exists():
            target = keep(k.loc_rel)
            # the compiled cache is rewritten below, so it is backed up too - an
            # undo that restored the .txt and left the .bin would put the file
            # back and leave the game still reading the ported text
            keep(k.loc_rel + ".strings.bin")
            kb.write_text(target,
                          stringsbin.upsert_txt(kb.read_text(target, "utf-16"),
                                                p.loc_writes),
                          "utf-16")
            file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
            res = cleaner.refresh_strings_bin(dest.root, k.loc_bin_rel)
            out["loc"] = {"file": k.loc_rel, "written": len(p.loc_writes),
                          "new": len(p.loc_new), "strings_bin": res}
        else:
            rel = k.loc_rel + ".strings.bin"
            target = keep(rel)
            sb = stringsbin.read(target)
            for tag, value in p.loc_writes.items():
                sb.set(tag, value)
            stringsbin.write(target, sb)
            file_op("WRITE", target, f"{len(p.loc_writes)} text key(s)")
            out["loc"] = {"file": rel, "written": len(p.loc_writes),
                          "new": len(p.loc_new), "compiled": True}

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": k.id,
        "action": "port",
        "source": p.source.name, "source_root": str(p.source.root),
        "dest": dest.name, "dest_root": str(dest.root),
        "unit_type": ", ".join(p.names[:4]),
        "resolved_type": ", ".join(p.names[:4]),
        "options": {"with_triggers": p.with_triggers, "overwrite": p.overwrite},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("PORT   %d %s(s) %s -> %s, %d text key(s), id=%s", len(p.rows), k.noun,
             p.source.name, dest.name, len(p.loc_writes), tid)
    out["record"] = rec
    return out
