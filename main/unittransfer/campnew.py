"""Phase 24, M15. Making a new campaign out of one that is already there.

Every file inside a campaign folder now has a writer in this toolkit - 16h the
settlements, 16i the characters, 16j-1 and 16j-2 the factions and the diplomacy,
:mod:`unittransfer.winconds` the victory terms, 18a the descriptions, the movies
and the mercenary pools, 18b the events - and there has never been a way to make
the folder they all live in. That is the whole of this item: the folder-level
operation, and the plan that says what a new campaign inherits and what it has
to be given.

**A new campaign is a copy of one that works.** Not a template and not a
skeleton: the engine reads fourteen or more files out of that folder and a
missing one is a load failure with nothing on screen to explain it, so the only
honest starting point is a campaign the mod already runs. What this adds on top
of the copy is the three things a copy alone gets wrong.

**One: the compiled map does not travel.** ``map.rwm`` is the engine's binary
cache of the whole map and it is rebuilt from the text and the layers on first
load. Copied, it would be the source campaign's map, and the new campaign would
load that in preference to its own files - the same trap every save in
:mod:`unittransfer.campaint` deletes it to avoid.

**Two: the header says which campaign this is.** ``descr_strat.txt`` opens on
``campaign <name>``, and a copy that keeps the source's opens claiming to be the
source. It is set to the new folder's own name here. The two are allowed to
disagree - Divide and Conquer's ``custom/Shattered_Alliances`` says
``campaign imperial_campaign`` and runs - so this is a choice rather than a
rule, and it is the one that leaves the copy self-consistent.

**Three: the menu has to be told what to call it.** The description keys are
built from the campaign's folder name (18a), so a copy inherits none of them and
the new-game menu shows raw keys: the title, the blurb and every faction's pair
are copied across under the new token, with the title and the blurb overridable
because those two are the whole point of making a second campaign.

**Where the folder goes is not cosmetic.** The engine's new-game menu reads the
folders **directly** under ``world/maps/campaign``, which is
:func:`unittransfer.campstrat.campaigns`' own measured rule; a campaign nested
one deeper is a campaign this toolkit can open and the menu cannot. Both
installed mods keep one there, so nesting is offered and it is warned about.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from . import campfiles, campmap, campstrat
from . import keyblock as kb

ENCODING = campstrat.ENCODING
LOC_ENCODING = campfiles.LOC_ENCODING

#: A folder name the engine and every path in this toolkit can carry. The same
#: shape :data:`unittransfer.renames.NAME_RE` holds a province to, because a
#: campaign name is read the same way: a bare token, no spaces, no dots.
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

#: What is never copied. The compiled map is the engine's own cache of the text
#: and the layers, and the new campaign has to build its own.
SKIP = (campmap.RWM_REL.rsplit("/", 1)[-1],)

#: The one line in the copy that is rewritten, and the word it opens on.
HEADER = "campaign"


class CampaignError(ValueError):
    """The name will not do, or the source is not a campaign that can be copied."""


# ---------------------------------------------------------------------------
# reading


def sources(mod) -> List[dict]:
    """Every campaign that could be copied, with what copying it would cost.

    Cheap on purpose - a folder walk and the description keys, no
    ``descr_strat.txt`` parsed. :func:`unittransfer.campfiles.browse` is what
    says how big a campaign is in factions and settlements; this says how big it
    is in bytes, which is the question a copy asks.
    """
    pairs = campfiles.descr_pairs(mod)
    #: 20b's rule again: the front-end picture is not a layer of its own
    layer_names = {ly["file"].lower() for ly in campmap.LAYERS
                   if ly["code"] != "fe"}
    out: List[dict] = []
    for rel in campstrat.campaign_paths(mod):
        home = campfiles.campaign_dir(mod, rel)
        files = [f for f in sorted(home.rglob("*")) if f.is_file()]
        kept = [f for f in files if f.name.lower() not in
                {s.lower() for s in SKIP}]
        out.append({
            "campaign": rel,
            "leaf": campstrat.campaign_leaf(rel),
            "nested": "/" in rel,
            "folder": f"{campstrat.CAMPAIGN_DIR_REL}/{rel}",
            "title": pairs.get(campfiles.descr_key(rel, "", "TITLE"), ""),
            "files": len(kept),
            "bytes": sum(f.stat().st_size for f in kept),
            "layers": sorted(f.name for f in files
                             if f.name.lower() in layer_names),
            "keys": sum(1 for k in pairs
                        if k.startswith(campfiles.descr_token(rel) + "_")),
        })
    return out


def _resolve(mod, name: str) -> Tuple[str, Path]:
    """The new campaign's relative name and folder, or a refusal saying why."""
    rel = str(name or "").replace("\\", "/").strip("/")
    if not rel:
        raise CampaignError("a new campaign needs a name")
    parts = [p for p in rel.split("/") if p]
    for part in parts:
        if not NAME_RE.match(part):
            raise CampaignError(
                f"{part!r} will not do as a folder name - a campaign is a bare "
                f"word: a letter first, then letters, digits, underscores or "
                f"hyphens, and no spaces or dots")
    try:
        rel = campstrat.campaign_rel("/".join(parts))
    except ValueError as exc:
        raise CampaignError(str(exc)) from None
    home = Path(mod.data) / campstrat.CAMPAIGN_DIR_REL / rel
    if home.exists():
        raise CampaignError(
            f"{campstrat.CAMPAIGN_DIR_REL}/{rel} is already there, and this "
            f"makes a campaign rather than writing over one")
    return rel, home


# ---------------------------------------------------------------------------
# the plan


@dataclass
class CampaignPlan:
    """One new campaign, worked out without touching the disk."""

    mod: object = None
    source: str = ""
    name: str = ""
    folder: str = ""
    #: ``(source path, data-relative destination)`` for every file copied as is
    copies: List[Tuple[Path, str]] = field(default_factory=list)
    #: data-relative path -> whole new text, for the files a copy has to change
    texts: Dict[str, str] = field(default_factory=dict)
    #: the description keys, and which of them the file does not have yet
    loc_writes: Dict[str, str] = field(default_factory=dict)
    loc_new: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def files(self) -> int:
        return len(self.copies) + len(self.texts)

    @property
    def bytes(self) -> int:
        return (sum(p.stat().st_size for p, _ in self.copies)
                + sum(len(t) for t in self.texts.values()))

    def summary(self) -> str:
        head = (f"new campaign {self.name} in "
                f"{getattr(self.mod, 'name', '?')}, copied from {self.source} "
                f"({self.files} file(s), {self.bytes:,} bytes)")
        return "\n".join([head] + [f"  {c}" for c in self.changes])

    def payload(self) -> dict:
        return {"source": self.source, "name": self.name, "folder": self.folder,
                "files": self.files, "bytes": self.bytes,
                "copies": [rel for _, rel in self.copies],
                "texts": sorted(self.texts), "skipped": list(self.skipped),
                "keys": sorted(self.loc_writes), "new_keys": list(self.loc_new),
                "changes": list(self.changes), "warnings": list(self.warnings),
                "errors": list(self.errors),
                "ok": not self.errors and bool(self.copies or self.texts)}


def plan(mod, body: dict) -> CampaignPlan:
    """Work out one new campaign. ``body`` is ``{source, name, title, blurb}``.

    ``title`` and ``blurb`` are what the new-game menu will show. Left empty
    they are inherited from the source, which is a real answer for a fork
    somebody is about to edit and a poor one for a campaign they mean to keep -
    so an inherited title is a warning rather than a refusal.
    """
    p = CampaignPlan(mod=mod, source=str(body.get("source") or "").strip())
    try:
        p.name, home = _resolve(mod, body.get("name"))
    except CampaignError as exc:
        p.errors.append(str(exc))
        return p
    p.folder = f"{campstrat.CAMPAIGN_DIR_REL}/{p.name}"
    if not p.source:
        p.errors.append("a new campaign is copied from one that already works, "
                        "so pick the one to copy")
        return p
    try:
        src = campfiles.campaign_dir(mod, p.source)
    except ValueError as exc:
        p.errors.append(str(exc))
        return p
    if not (src / campstrat.STRAT_NAME).is_file():
        p.errors.append(f"{p.source} has no {campstrat.STRAT_NAME}, so it is "
                        f"not a campaign there is anything to copy")
        return p
    if p.name.lower() == p.source.lower():
        p.errors.append("the new campaign and the one it is copied from are the "
                        "same folder")
        return p

    _plan_files(p, src)
    if p.errors:
        return p
    _plan_header(p, src)
    _plan_keys(p, body)
    if "/" in p.name:
        p.warnings.append(
            f"{p.name} is nested, and the engine's own new-game menu reads the "
            f"folders directly under {campstrat.CAMPAIGN_DIR_REL} - so this "
            f"campaign will open on this screen and not in the game. Both "
            f"installed mods keep one there, which is why it is offered.")
    return p


def _plan_files(p: CampaignPlan, src: Path) -> None:
    """Every file in the source folder, and the two kinds that are not copied."""
    data = Path(p.mod.data)
    skip = {s.lower() for s in SKIP}
    # 20b's rule: map_FE.tga is the menu picture and every campaign has its own,
    # so counting it would say "ships a map layer of its own" about all six
    # campaigns installed here and mean nothing by it
    layer_names = {ly["file"].lower() for ly in campmap.LAYERS
                   if ly["code"] != "fe"}
    layers: List[str] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        under = path.relative_to(src).as_posix()
        if path.name.lower() in skip:
            p.skipped.append(under)
            continue
        p.copies.append((path, f"{p.folder}/{under}"))
        if path.name.lower() in layer_names:
            layers.append(path.name)
    if not p.copies:
        p.errors.append(f"{p.source}'s folder has no files in it at all")
        return
    p.changes.append(f"{p.folder}: {len(p.copies)} file(s), "
                     f"{sum(q.stat().st_size for q, _ in p.copies):,} bytes, "
                     f"copied from {p.source}")
    if p.skipped:
        p.changes.append(f"{p.folder}: {', '.join(p.skipped)} left behind - the "
                         f"engine rebuilds the compiled map from the text and "
                         f"the layers, and a copied one would be the old map")
    if layers:
        p.warnings.append(
            f"{p.source} ships {len(layers)} map layer(s) of its own "
            f"({', '.join(sorted(layers))}), so the copy gets a copy of them "
            f"too and the two campaigns are then two maps to keep in step. The "
            f"map screen draws whichever one the campaign you have open reads.")
    elif not (data / campmap.REGIONS_REL).is_file():
        p.warnings.append(
            f"{campmap.REGIONS_REL} is not on disk and {p.source} ships no map "
            f"of its own, so there is no region list for this campaign to read")


def _plan_header(p: CampaignPlan, src: Path) -> None:
    """``campaign <name>``, set to the new folder's own name.

    The first code line of the file, and the only line of any copied file this
    changes. A source whose header already disagrees with its own folder - which
    Divide and Conquer's nested campaign does - is still set to the new folder's
    name, and what it used to say is in the change line.
    """
    rel = f"{p.folder}/{campstrat.STRAT_NAME}"
    text = kb.read_text(src / campstrat.STRAT_NAME, ENCODING)
    lines, newline, trailing = campmap._split_lines(text)
    leaf = campstrat.campaign_leaf(p.name)
    for i, raw in enumerate(lines):
        code = kb.code_of(raw)
        if not code:
            continue
        word, _, rest = code.partition(" ")
        if word.lower() != HEADER:
            p.warnings.append(
                f"{p.source}'s {campstrat.STRAT_NAME} does not open on "
                f"`{HEADER} <name>` but on {code.split()[0]!r}, so the copy is "
                f"taken exactly as it is and names itself whatever the source "
                f"did")
            return
        was = rest.strip()
        if was == leaf:
            return
        lines[i] = kb.keep_comment(raw, kb.indent_of(code) + f"{HEADER} {leaf}")
        p.texts[rel] = newline.join(lines) + (newline if trailing else "")
        p.copies = [(q, r) for q, r in p.copies if r != rel]
        p.changes.append(f"{rel}: `{HEADER} {was}` -> `{HEADER} {leaf}`, so the "
                         f"copy does not claim to be the campaign it came from")
        return
    p.errors.append(f"{p.source}'s {campstrat.STRAT_NAME} has no code in it at "
                    f"all")


def _plan_keys(p: CampaignPlan, body: dict) -> None:
    """The new-game menu's title, blurb and every faction pair, under the new key.

    18a's rule: the key is the campaign's own folder name upper-cased, so the
    copy inherits nothing by being a copy and every key has to be written. The
    faction pairs are taken across as they stand - the factions are the same
    factions - and the campaign's own two are overridable, because a second
    campaign with the first one's name on the menu is the one mistake this
    cannot let somebody make quietly.
    """
    have = campfiles.descr_pairs(p.mod)
    src_head = campfiles.descr_token(p.source) + "_"
    new_head = campfiles.descr_token(p.name) + "_"
    for key, value in have.items():
        if key.startswith(src_head):
            p.loc_writes[new_head + key[len(src_head):]] = value
    for kind, field_name in (("TITLE", "title"), ("DESCR", "blurb")):
        given = str(body.get(field_name) or "").strip()
        if given:
            p.loc_writes[new_head + kind] = given
    title = p.loc_writes.get(new_head + "TITLE", "")
    if not title:
        p.warnings.append(
            f"nothing names {p.name} on the new-game menu, so the engine shows "
            f"the key {new_head}TITLE. {campfiles.DESCR_REL} is where that "
            f"lives and the Descriptions panel writes it."
            + ("" if campfiles.descr_path(p.mod).exists()
               else " This mod ships only the compiled archive, which is "
                    "where the key would go."))
    elif not str(body.get("title") or "").strip():
        p.warnings.append(
            f"{p.name} inherits {p.source}'s title, {title!r}, so two campaigns "
            f"read the same on the menu until one of them is renamed")
    p.loc_new = [k for k in p.loc_writes if k not in have]
    if p.loc_writes:
        p.changes.append(f"{campfiles.DESCR_REL}: {len(p.loc_writes)} key(s) "
                         f"under {new_head}, {len(p.loc_new)} of them new")


# ---------------------------------------------------------------------------
# the save


def apply(p: CampaignPlan) -> dict:
    """Write the new campaign, with the same backups and undo as any other job.

    Nothing here is overwritten - the folder did not exist a moment ago - so the
    backup set is empty and the manifest is all ``created``, which is what an
    undo of this needs: every file it made, to take away again.
    """
    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.copies and not p.texts:
        raise ValueError("there is nothing to copy")
    mod = p.mod
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

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

    for src, rel in p.copies:
        target = keep(rel)
        shutil.copy2(src, target)
    file_op("WRITE", Path(mod.data) / p.folder,
            f"{len(p.copies)} file(s) copied from {p.source}")
    for rel, text in sorted(p.texts.items()):
        target = keep(rel)
        kb.write_text(target, text, ENCODING)
        file_op("WRITE", target, f"{len(text)} bytes")
    out: dict = {"id": tid, "name": p.name, "folder": p.folder,
                 "files": p.files}
    if p.loc_writes:
        out["loc"] = campfiles.write_descriptions(
            mod, p.loc_writes, p.loc_new, keep, file_op)

    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "campfiles", "action": "campaign_new",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.name, "resolved_type": p.name,
        "options": {"source": p.source},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("CAMPAIGN %s - new %s from %s, %d file(s), id=%s", mod.name,
             p.name, p.source, p.files, tid)
    out["record"] = rec
    return out


# ---------------------------------------------------------------------------
# the panel


def view(mod) -> dict:
    """What the New campaign panel shows before anything is picked."""
    return {
        "mod": getattr(mod, "name", ""),
        "dir": campstrat.CAMPAIGN_DIR_REL,
        "default": campstrat.DEFAULT_CAMPAIGN,
        "menu": campstrat.campaigns(mod),
        "sources": sources(mod),
        "descriptions": campfiles.DESCR_REL,
        "have_descriptions": campfiles.descr_path(mod).exists(),
        "skipped": list(SKIP),
    }
