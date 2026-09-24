"""A settlement model brought in and put on a culture's level (Phase 74).

Three halves of this were already here: the map screen lists and draws every
strat ``.cas`` (:func:`unittransfer.cas.list_models`), the Cultures screen edits
a level's model path as text (:func:`unittransfer.minorfiles.render_culture`),
and B3 puts any one file under ``data/`` (:mod:`unittransfer.fileswap`). What
nothing did was the one step joining them: **pick a model in another mod, or on
disk, copy it with the textures it names, and write it onto a culture's level**,
in one plan and one Undo.

**A model is never one file.** A ``.cas`` names its textures the way 3ds-max saw
them, relative to its own folder (``textures\\NE_stone_castle.tga``), so the
textures go to the same place relative to wherever the model lands, found by
the same rule the viewer uses (:func:`unittransfer.cas.texture_path`: case
forgiven, a ``.tga`` also sought as ``.dds`` and ``.tga.dds``, an empty packer
stub never taken over the real file beside it). A texture neither side has is
said, not invented.

**Nothing already there is written over.** A model or a texture already at its
path with the same bytes is used as it is; with other bytes it belongs to some
other model, so the whole set goes into a folder of its own
(``models_strat/residences/<mod>/``) and the plan says so. Settlement models
share one ``textures`` folder in both installed mods, which is why this is the
common case rather than the rare one.

**What the level says is the model and nothing else.** A level's ``normal`` line
is a model and a settlement plan together (``…dwarf_t1_village.CAS,
settlement_eastern_level_1``); the plan names the battle map's layout, which is
the destination's and stays. The tail lines that hold a model - ``fort``,
``fort_wall``, ``fishing_village`` and ``watchtower`` - can be the target too,
in the same shape.
"""
from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from . import cas, minorfiles
from . import keyblock as kb

RESIDENCES = f"{cas.STRAT_MODELS}/residences"
#: the culture lines outside the settlement ladder that name a model
TAIL_MODELS = ("fort", "fort_wall", "fishing_village", "watchtower")
TARGETS = minorfiles.CULTURE_LEVELS + TAIL_MODELS
#: the most one model with its textures may weigh
MAX_BYTES = 64 * 1024 * 1024
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class ModelError(ValueError):
    pass


def _cultures_path(mod) -> Path:
    return Path(mod.data) / minorfiles.CULTURES_REL


def _read_cultures(mod):
    path = _cultures_path(mod)
    if not path.is_file():
        raise ModelError(f"{getattr(mod, 'name', '?')} has no {minorfiles.CULTURES_REL} "
                         f"on disk, so there is no culture to put a model on")
    text = kb.read_text(path, minorfiles.ENCODING)
    return minorfiles.parse_cultures(text), text


def _model_of(value: str) -> Tuple[str, str]:
    """``(model, plan)`` of a ``normal`` or tail value; plan is ``""`` alone."""
    return minorfiles.split_pair(value)


def _exists(mod, path_value: str) -> bool:
    """Whether the model a culture line names is on disk (``data/...`` or not)."""
    rel = path_value.replace("\\", "/").strip().lstrip("/")
    if rel.lower().startswith("data/"):
        rel = rel[5:]
    return bool(rel) and (Path(mod.data) / rel).is_file()


# ---------------------------------------------------------------------------
# the lists


def sources(mod) -> List[dict]:
    """The settlement models a mod ships: everything under ``residences``."""
    data = Path(mod.data)
    return [m for m in cas.list_models(data)
            if m["rel"].lower().startswith(RESIDENCES.lower() + "/")]


def view(mod) -> dict:
    """Every culture's model lines, each with whether its model is on disk."""
    try:
        cf, _ = _read_cultures(mod)
    except ModelError as exc:
        return {"mod": getattr(mod, "name", ""), "error": str(exc), "cultures": []}
    out = []
    for cul in cf.cultures:
        rows = []
        for lvl in cul.levels:
            model, plan = _model_of(lvl.values.get("normal", ""))
            rows.append({"target": lvl.name, "model": model, "plan": plan,
                         "on_disk": _exists(mod, model)})
        for key in TAIL_MODELS:
            if key in cul.values:
                model, plan = _model_of(cul.values[key])
                rows.append({"target": key, "model": model, "plan": plan,
                             "on_disk": _exists(mod, model), "tail": True})
        out.append({"culture": cul.name, "targets": rows})
    return {"mod": getattr(mod, "name", ""), "cultures": out,
            "file": minorfiles.CULTURES_REL}


# ---------------------------------------------------------------------------
# the plan


@dataclass
class ModelPlan:
    dst: object = None
    source: str = ""                 # a mod's name, or "disk"
    model: str = ""                  # its path in the source, or its file name
    culture: str = ""
    target: str = ""
    rel: str = ""                    # where the model lands, under data/
    was: str = ""                    # what the line said before
    #: ``(bytes, data-relative path)`` for every file written
    writes: List[Tuple[bytes, str]] = field(default_factory=list)
    same: List[str] = field(default_factory=list)
    textures: List[dict] = field(default_factory=list)
    text: str = ""                   # descr_cultures.txt's new text
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def payload(self) -> dict:
        return {"source": self.source, "model": self.model, "culture": self.culture,
                "target": self.target, "rel": self.rel, "was": self.was,
                "files": [rel for _, rel in self.writes], "same": list(self.same),
                "bytes": sum(len(b) for b, _ in self.writes),
                "textures": self.textures, "changes": list(self.changes),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "ok": not self.errors and bool(self.text)}


def _from_mod(p: ModelPlan, src, rel: str) -> Tuple[bytes, Path, Dict[str, Tuple[bytes, str]]]:
    """The model's bytes, where it is, and each texture it names that is found:
    ``{texture as written: (bytes, path relative to the model's folder)}``."""
    from . import fileswap
    try:
        path = fileswap.resolve(src, rel)
    except fileswap.SwapError as exc:
        raise ModelError(str(exc)) from None
    if not path.is_file() or path.suffix.lower() != ".cas":
        raise ModelError(f"{getattr(src, 'name', '?')} has no model at data/{rel}")
    raw = path.read_bytes()
    scene = _scene(raw, path.name)
    found: Dict[str, Tuple[bytes, str]] = {}
    for tex in _textures(scene):
        hit = cas.texture_path(path, tex)
        if hit is not None and hit.stat().st_size > 0:
            found[tex] = (hit.read_bytes(), hit.relative_to(path.parent).as_posix())
            # the packer's empty stub under the name the model writes, beside
            # its <name>.tga.dds: carried too, since it is what the source has
            named = path.parent / tex.replace("\\", "/").lstrip("/")
            stub = None
            if named.parent.is_dir():
                stub = next((q for q in named.parent.iterdir()
                             if q.name.lower() == named.name.lower()), None)
            if stub is not None and stub != hit and stub.stat().st_size == 0:
                found[tex + "|stub"] = (b"", stub.relative_to(path.parent).as_posix())
    return raw, path, found


def _from_disk(files: List[dict]) -> Tuple[bytes, str, Dict[str, Tuple[bytes, str]]]:
    """The one ``.cas`` among uploaded files and the textures it names, matched
    by name the way :func:`unittransfer.cas.texture_path` matches them."""
    import base64
    got: Dict[str, bytes] = {}
    for f in files or []:
        name = Path(str(f.get("name") or "")).name
        try:
            got[name] = base64.b64decode(str(f.get("data") or ""), validate=True)
        except ValueError:
            raise ModelError(f"{name or 'a file'} did not arrive whole") from None
    models = [n for n in got if n.lower().endswith(".cas")]
    if len(models) != 1:
        raise ModelError("pick one .cas model, with the textures it names beside it"
                         if not models else "pick one .cas at a time")
    name = models[0]
    scene = _scene(got[name], name)
    lower = {n.lower(): n for n in got}
    found: Dict[str, Tuple[bytes, str]] = {}
    for tex in _textures(scene):
        rel = tex.replace("\\", "/").lstrip("/")
        folder, _, leaf = rel.rpartition("/")
        stem = leaf.rsplit(".", 1)[0]
        for want in (leaf, leaf + ".dds", stem + ".dds"):   # cas.texture_path's order
            hit = lower.get(want.lower())
            if hit and got[hit]:
                found[tex] = (got[hit], (folder + "/" if folder else "") + hit)
                break
    return got[name], name, found


def _scene(raw: bytes, name: str):
    try:
        return cas.read_cas_bytes(raw, name)
    except cas.CasError as exc:
        raise ModelError(f"{name} does not read as a .cas model ({exc})") from None


def _textures(scene) -> List[str]:
    out: List[str] = []
    for m in scene.materials:
        if m.texture and m.texture not in out:
            out.append(m.texture)
    return out


def plan(dst, src, body: dict) -> ModelPlan:
    """Work out one model onto one culture line. ``body``: ``{from, model,
    files: [{name, data}], culture, target, folder}``; ``files`` is a model
    from disk and ``from`` is then ``"disk"``."""
    p = ModelPlan(dst=dst, source=str(body.get("from") or "").strip(),
                  model=str(body.get("model") or "").strip(),
                  culture=str(body.get("culture") or "").strip(),
                  target=str(body.get("target") or "").strip())
    try:
        cf, text = _read_cultures(dst)
        if p.target not in TARGETS:
            raise ModelError(f"{p.target or 'nothing'} is not a line of a culture "
                             f"that names a model")
        cul = cf.get(p.culture)
        if cul is None:
            raise ModelError(f"{dst.name} has no culture called {p.culture!r}")
        if p.source == "disk":
            raw, name, found = _from_disk(body.get("files") or [])
            p.model = name
            home = RESIDENCES
        else:
            if src is None:
                raise ModelError("pick the mod the model comes from, or a model on disk")
            raw, path, found = _from_mod(p, src, p.model)
            name = path.name
            home = path.parent.relative_to(Path(src.data)).as_posix()
        scene = _scene(raw, name)
    except ModelError as exc:
        p.errors.append(str(exc))
        return p

    wanted = _textures(scene)
    missing = [t for t in wanted if t not in found]
    for t in wanted:
        p.textures.append({"texture": t, "found": t in found,
                           "file": found[t][1] if t in found else ""})
    if missing:
        p.warnings.append(
            f"{name} names {len(missing)} texture(s) that "
            f"{'the files picked do' if p.source == 'disk' else p.source + ' does'} "
            f"not have: {', '.join(missing[:6])}. The model comes without "
            f"{'it' if len(missing) == 1 else 'them'} and draws untextured "
            f"unless {dst.name} already has {'it' if len(missing) == 1 else 'them'} "
            f"beside it.")

    # where it lands: its own folder, else one of its own, else refused
    folder = str(body.get("folder") or "").replace("\\", "/").strip().strip("/")
    if folder.lower().startswith("data/"):
        folder = folder[5:]
    tries = [folder] if folder else [home, f"{RESIDENCES}/"
                                     f"{_SAFE.sub('_', p.source or 'imported')}"]
    total = len(raw) + sum(len(b) for b, _ in found.values())
    if total > MAX_BYTES:
        p.errors.append(f"{total / 1048576:.0f} MB is more than the "
                        f"{MAX_BYTES // 1048576} MB one model with its textures may be")
        return p
    for place in tries:
        files = [(raw, f"{place}/{name}")] + [(b, f"{place}/{r}") for b, r in found.values()]
        clash = [rel for b, rel in files if (Path(dst.data) / rel).is_file()
                 and (Path(dst.data) / rel).read_bytes() != b]
        if not clash:
            break
    else:
        p.errors.append(f"{', '.join(clash[:4])} {'is' if len(clash) == 1 else 'are'} "
                        f"already in {dst.name} with other bytes, and a model is never "
                        f"copied over another. Give it a folder of its own.")
        return p
    try:
        from . import fileswap
        for _, rel in files:
            fileswap.resolve(dst, rel)
    except fileswap.SwapError as exc:
        p.errors.append(str(exc))
        return p
    if place != tries[0]:
        p.warnings.append(f"{tries[0]} already holds a file of the same name with other "
                          f"bytes (settlement models share one textures folder), so "
                          f"this one goes into {place} with its own")
    p.rel = f"{place}/{name}"
    for b, rel in files:
        target = Path(dst.data) / rel
        if target.is_file():
            p.same.append(rel)
        else:
            p.writes.append((b, rel))

    # the culture line
    value = "data/" + p.rel
    block = cf.block_text(cul)
    try:
        if p.target in TAIL_MODELS:
            old = cul.values.get(p.target)
            if old is None:
                raise ModelError(f"{p.culture} has no `{p.target}` line")
            model, plan_ = _model_of(old)
            gap = old.partition(",")[2]
            gap = gap[: len(gap) - len(gap.lstrip())] or "\t\t"
            new = f"{value},{gap}{plan_}" if "," in old else value
            p.was = model
            edits = {p.target: new}
        else:
            lvl = cul.level(p.target)
            if lvl is None:
                raise ModelError(f"{p.culture} has no `{p.target}` settlement level")
            p.was = lvl.model
            edits = {"levels": {p.target: {"model": value}}}
        if p.was.replace("\\", "/").lower() == value.lower():
            raise ModelError(f"{p.culture}'s {p.target} already names {value}")
        new_block = minorfiles.render_culture(block, edits)
    except (ModelError, minorfiles.MinorError) as exc:
        p.errors.append(getattr(exc, "message", None) or str(exc))
        return p
    p.text = minorfiles.replace_culture(cf, cul, new_block)
    again = minorfiles.parse_cultures(p.text)
    got = again.get(p.culture)
    now = (_model_of(got.values.get(p.target, ""))[0] if p.target in TAIL_MODELS
           else got.level(p.target).model) if got else ""
    if now != value or len(again.cultures) != len(cf.cultures):
        p.errors.append(f"{minorfiles.CULTURES_REL} did not read back as written")
        return p

    p.changes.append(f"{minorfiles.CULTURES_REL}: {p.culture} {p.target}: "
                     f"{p.was or '(none)'} -> {value}")
    if p.writes:
        p.changes.append(f"{len(p.writes)} file(s) from {p.source}: "
                         + ", ".join(rel for _, rel in p.writes[:6])
                         + (" ..." if len(p.writes) > 6 else ""))
    if p.same:
        p.changes.append(f"{len(p.same)} already there with the same bytes, used as "
                         f"they are")
    def same(v: str) -> bool:
        return v.replace("\\", "/").lower() == p.was.replace("\\", "/").lower()
    users = [f"{c.name} {lv.name}" for c in cf.cultures for lv in c.levels
             if same(lv.model) and not (c.name == p.culture and lv.name == p.target)]
    users += [f"{c.name} {k}" for c in cf.cultures for k in TAIL_MODELS
              if k in c.values and same(_model_of(c.values[k])[0])
              and not (c.name == p.culture and k == p.target)]
    if p.was and not users:
        p.warnings.append(f"no other line names {p.was} any more; it stays on disk "
                          f"and Undo puts it back on this line")
    return p


# ---------------------------------------------------------------------------
# the save


def apply(p: ModelPlan) -> dict:
    """Write the model, its textures and the culture line: one backup, one Undo."""
    from . import config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.text:
        raise ValueError("nothing to change")
    mod = p.dst
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

    for raw, rel in p.writes:
        target = keep(rel)
        target.write_bytes(raw)
        file_op("WRITE", target, f"{len(raw)} bytes from {p.source}")
    target = keep(minorfiles.CULTURES_REL)
    kb.write_text(target, p.text, minorfiles.ENCODING)
    file_op("WRITE", target, f"{p.culture} {p.target} -> {p.rel}")
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "minor", "action": "settlement_model",
        "source": p.source, "source_root": "",
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": f"{p.culture} {p.target}", "resolved_type": p.rel,
        "options": {"model": p.model, "culture": p.culture, "target": p.target},
        "applied": True, "undone": False, "note": "",
        "summary": "\n".join([f"settlement model {p.model} onto {p.culture} "
                              f"{p.target} in {mod.name}"]
                             + [f"  {c}" for c in p.changes]),
        "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("SETTLEMENT MODEL %s -> %s %s in %s (%d file(s)), id=%s", p.model,
             p.culture, p.target, mod.name, len(p.writes), tid)
    return {"id": tid, "rel": p.rel, "files": [rel for _, rel in p.writes],
            "record": rec}
