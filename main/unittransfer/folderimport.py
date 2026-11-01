"""A Blender export's models brought into a mod, then a unit and its cards.

The Models Editor's folder view (:mod:`meshfolder`) reads an export - one
folder per model, holding ``<name>.mesh``, a ``textures/`` folder and
sometimes ``<name>_bmdb.txt`` - to look at. This writes those models into a
mod, through :func:`edit.plan_bmdb` like every other new entry, so the whole
import is one record in My Changes and one Undo:

* **with a** ``_bmdb.txt`` the entry goes in as written: its skeletons, its
  factions, its sprites. The paths in it are where the mod keeps the files
  (``unit_models/_units/reaper/textures/...``), so each file the folder holds
  is copied to exactly that path. A file the mod already has byte for byte is
  left alone; one that differs is overwritten, backed up first;
* **without one** there is nothing to take the skeletons from, so the person
  picks an entry of the mod to clone (:class:`edit.NewModel`), and the mesh and
  the sheets the folder view would draw it in go into a folder under
  ``unit_models/_units/``.

A model whose name the mod already has is shown as a clash, and per model the
person picks what happens: replace the mod's entry (a ``_bmdb.txt`` only),
take a new name, or skip it.

Afterwards each entry can be made a unit's soldier or the model of a new unit
(:func:`armunit.plan_install` with ``entry``), and given a card and an info
card. The game finds a card by the unit's dictionary name and nothing else
(:mod:`cards`), so whatever picture is picked is copied in under that name:
:func:`card_pictures` offers the pictures in the folder whose names come
closest to the model's and the unit's, but any file will do.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import edit, gamepack, loosemesh, meshfolder, modeldb
from . import i18n as _i18n


class FolderImportError(ValueError):
    """The folder cannot be imported as asked, said as a sentence."""


#: where a model with no ``_bmdb.txt`` goes, under ``data/``
DEFAULT_DIR = "unit_models/_units/{name}"
#: what a card can be saved as
PICTURE_SUFFIXES = (".tga", ".png", ".dds", ".jpg", ".jpeg", ".bmp")
#: a name an entry can take: what the game reads as one token
_NAME_BAD = re.compile(r"[^a-z0-9_\-]+")


def entry_name(stem: str) -> str:
    return _NAME_BAD.sub("_", (stem or "").strip().lower()).strip("_")


def _digest(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _file_state(mod, rel: str, src: Optional[Path]) -> str:
    """``new``, ``same`` or ``differs`` for a file the folder has, against the
    mod's own; ``in_mod`` or ``missing`` for one it has not."""
    target = mod.data / rel
    if src is None:
        if target.is_file():
            return "in_mod"
        found, _where = gamepack.lookup(rel, mod, as_path=False)
        return "in_mod" if _where else "missing"
    if not target.is_file():
        return "new"
    try:
        same = target.stat().st_size == src.stat().st_size and _digest(target) == _digest(src)
    except OSError:
        same = False
    return "same" if same else "differs"


def _normal_of(fs: meshfolder.FolderSource, sheet: Path) -> Optional[Path]:
    """The normal map saved beside a sheet: ``a.texture`` -> ``a_norm.texture``."""
    base = meshfolder._base(sheet.name).lower()
    best = None
    for p in fs.files:
        if p.parent != sheet.parent or p.suffix.lower() not in meshfolder._SHEET_ORDER:
            continue
        b = meshfolder._base(p.name)
        if b.lower() == base or not b.lower().startswith(base) or not meshfolder._is_normal(b):
            continue
        if b.lower()[len(base):].strip("_-") not in ("n", "nm", "nrm", "norm", "normal", "bump"):
            continue
        if best is None or (meshfolder._SHEET_ORDER.index(p.suffix.lower())
                            < meshfolder._SHEET_ORDER.index(best.suffix.lower())):
            best = p
    return best


def _bmdb_model(mod, fs, src: Path, e, bmdb_name: str, known_facs: set) -> dict:
    heads = fs._heads([src.parent / "textures", src.parent])
    files, seen = [], set()
    for rel in e.mesh_files() + e.texture_files():
        clean = rel.replace("\\", "/").strip()
        if clean.lower().startswith("data/"):
            clean = clean[5:]
        if clean.lower() in seen:
            continue
        seen.add(clean.lower())
        here = fs.locate(clean, heads)
        p = fs.root / here if here else None
        # found by its file name: a copy keeps the name the entry gives it
        if p is not None and p.name.lower() != clean.rsplit("/", 1)[-1].lower():
            p = None
        files.append({"rel": clean, "src": str(p) if p else "",
                      "state": _file_state(mod, clean, p)})
    facs = e.factions()
    return {"bmdb": bmdb_name, "files": files,
            "lods": len(e.lods), "factions": len(facs),
            "unknown_factions": [f for f in facs if known_facs and f.lower() not in known_facs],
            "skeletons": list(dict.fromkeys(s for s in e.skeletons() if s)),
            "missing_skeletons": [s for s in dict.fromkeys(e.skeletons())
                                  if s and s not in mod.modeldb.all_skeletons()]}


def _sheet_model(mod, fs, src: Path, name: str) -> dict:
    """A model with no ``_bmdb.txt``: its mesh and the sheets the viewer draws it in."""
    skins = fs._guess(src)
    main = fs.root / skins[0]["rel"] if skins else None
    att = fs.root / skins[0]["attach"] if skins and skins[0].get("attach") else None
    dest = DEFAULT_DIR.format(name=name)
    tex = f"{dest}/textures"
    slots = {"mesh_src": src, "texture_src": main,
             "normal_src": _normal_of(fs, main) if main else None,
             "attach_texture_src": att,
             "attach_normal_src": _normal_of(fs, att) if att else None}
    files = []
    for slot, p in slots.items():
        if p is None:
            continue
        rel = f"{dest if slot == 'mesh_src' else tex}/{p.name}"
        files.append({"slot": slot, "rel": rel, "src": str(p), "state": _file_state(mod, rel, p)})
    cas = sorted(p.stem for p in src.parent.glob("*.cas")) if src.parent.is_dir() else []
    return {"bmdb": "", "files": files, "dest_dir": dest, "cas": cas}


def scan(mod, path: str, fresh: bool = False) -> dict:
    """Every model the folder holds, as it would go into ``mod``."""
    fs = meshfolder.open_folder(path, fresh=fresh)
    entries = mod.modeldb.by_name()
    known_facs = {f.lower() for f in (mod.faction_names or {})}
    if known_facs:
        known_facs |= {"merc", "slave"}       # a skin for mercenaries and rebels
    models = []
    for p in fs.files:
        if p.suffix.lower() != ".mesh":
            continue
        rel = fs.rel(p)
        e, bmdb_name = fs._bmdb_entry(p)
        name = e.name.lower() if e is not None else entry_name(loosemesh._stem(p.name))
        row = {"id": rel, "mesh": p.name, "folder": Path(rel).parent.as_posix(),
               "name": name, "clash": name in entries}
        row.update(_bmdb_model(mod, fs, p, e, bmdb_name, known_facs) if e is not None
                   else _sheet_model(mod, fs, p, name))
        models.append(row)
    models.sort(key=lambda m: m["id"].lower())
    # two exports often carry one _bmdb.txt between them (a unit and its
    # upgrade), so a name can be the folder's twice; each such model, and each
    # the mod has already, is offered a free name, its mesh's if that is one
    count: Dict[str, int] = {}
    for m in models:
        count[m["name"]] = count.get(m["name"], 0) + 1
    taken = set(entries) | set(count)
    keeps = {}                              # name -> the model that keeps it
    for m in models:
        if count[m["name"]] > 1 and (m["name"] not in keeps
                                     or entry_name(loosemesh._stem(m["mesh"])) == m["name"]):
            keeps[m["name"]] = m["id"]
    for m in models:
        m["dup"] = count[m["name"]] > 1
        if m["clash"] or (m["dup"] and keeps[m["name"]] != m["id"]):
            want = entry_name(loosemesh._stem(m["mesh"]))
            n = 2
            while want in taken:
                want = f"{entry_name(loosemesh._stem(m['mesh']))}_{n}"
                n += 1
            taken.add(want)
            m["suggest"] = want
    return {"root": str(fs.root), "mod": mod.name, "models": models,
            "notes": list(fs.notes), "truncated": fs.truncated}


# ---------------------------------------------------------------------------
# the plan

def _picked(scanned: dict, req: dict) -> List[tuple]:
    by_id = {m["id"]: m for m in scanned["models"]}
    out = []
    for r in req.get("models") or []:
        m = by_id.get(str(r.get("id") or ""))
        if m is None:
            raise FolderImportError(_i18n.msg("eng.folderimport.no_such_model", "{id} is not in the folder any more: read it again", id=r.get("id")))
        if (r.get("action") or "new") != "skip":
            out.append((m, r))
    return out


def plan_import(mod, req: dict) -> dict:
    """What importing the picked models would write, planned and not written.

    ``req``: ``path`` (the folder) and ``models``, each ``{id, action, name,
    clone_from, dest_dir}``: ``action`` is ``new`` (the default), ``replace``
    (the mod's entry of that name; a ``_bmdb.txt`` only), ``rename`` (``name``
    is the new one) or ``skip``.
    """
    fs = meshfolder.open_folder(req.get("path") or "")
    scanned = scan(mod, str(fs.root))
    picked = _picked(scanned, req)
    if not picked:
        raise FolderImportError(_i18n.msg("eng.folderimport.nothing_picked", "tick at least one model to import"))
    new_models, warnings, names = [], [], []
    copied: Dict[str, str] = {}             # rel -> source, across the batch
    for m, r in picked:
        action = r.get("action") or "new"
        name = entry_name(r.get("name") or m["name"]) if action == "rename" else m["name"]
        names.append(name)
        files = {}
        for f in m["files"]:
            if not f["src"]:
                if f["state"] == "missing":
                    warnings.append(_i18n.msg("eng.folderimport.file_nowhere", "'{name}' names {rel}, which is neither in the folder nor in the mod", name=name, rel=f["rel"]))
                continue
            if f["state"] == "same":
                continue
            have = copied.get(f["rel"].lower())
            if have is not None:
                if have != f["src"] and _digest(Path(have)) != _digest(Path(f["src"])):
                    warnings.append(_i18n.msg("eng.folderimport.two_sources", "two models put a different {rel}: the first one's is kept", rel=f["rel"]))
                continue
            copied[f["rel"].lower()] = f["src"]
            files[f["rel"]] = f["src"]
        if m["bmdb"]:
            e, _n = fs._bmdb_entry(fs.root / m["id"])
            if e is None:
                raise FolderImportError(_i18n.msg("eng.folderimport.bmdb_unreadable", "{bmdb} could not be read", bmdb=m["bmdb"]))
            if m.get("unknown_factions"):
                warnings.append(_i18n.msg("eng.folderimport.unknown_factions", "'{name}' has skins for factions {mod} does not have: {factions}", name=name, mod=mod.name, factions=", ".join(m["unknown_factions"][:8])))
            new_models.append({"name": name, "raw_entry": e.raw, "files": files,
                               "replace": action == "replace"})
            continue
        if action == "replace":
            raise FolderImportError(_i18n.msg("eng.folderimport.replace_needs_bmdb", "'{name}' has no _bmdb.txt, so it cannot replace the mod's entry: give it a new name", name=name))
        clone = (r.get("clone_from") or "").strip().lower()
        if not clone:
            raise FolderImportError(_i18n.msg("eng.folderimport.pick_a_clone", "'{name}' has no _bmdb.txt: pick an entry of the mod to take its skeletons and factions from", name=name))
        dest = (r.get("dest_dir") or "").strip().strip("/\\") or DEFAULT_DIR.format(name=name)
        nm = {"name": name, "clone_from": clone, "dest_dir": dest, "mesh_all_lods": True}
        for f in m["files"]:
            nm[f["slot"]] = f["src"]
        new_models.append(nm)
    plan = edit.plan_bmdb(mod, edit.bmdb_request_from_dict({"new_models": new_models}))
    plan.warnings[:0] = warnings
    return {"plan": plan, "names": names}


def payload(planned: dict) -> dict:
    plan = planned["plan"]
    errors = [str(e) for e in plan.errors]
    return {"names": planned["names"],
            "lines": [ln.strip() for ln in plan.summary().splitlines() if ln.strip()],
            "warnings": [str(w) for w in plan.warnings], "errors": errors, "ok": not errors}


def apply_import(mod, req: dict) -> dict:
    planned = plan_import(mod, req)
    if planned["plan"].errors:
        raise FolderImportError("; ".join(str(e) for e in planned["plan"].errors))
    record = edit.apply_edit(planned["plan"])
    return {"record": record, "names": planned["names"]}


# ---------------------------------------------------------------------------
# unit cards

def _key(name: str) -> str:
    s = name.lower()
    for suf in PICTURE_SUFFIXES:
        while s.endswith(suf):
            s = s[:-len(suf)]
    s = s.lstrip("#")
    s = re.sub(r"_(info|result)$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _kind(rel: str) -> str:
    low = rel.lower()
    return "info" if "unit_info/" in low or re.search(r"_info(\.|_|$)", Path(low).name) else "card"


def card_pictures(path: str, names: List[str]) -> List[dict]:
    """Every picture in the folder that could be a card, closest to ``names`` first.

    A model's own sheets (anything in a ``textures/`` folder) and normal maps
    are not cards. ``score`` is how near the file's name is to the nearest of
    ``names`` (the entry, the unit's type and dictionary), 1.0 the same.
    """
    fs = meshfolder.open_folder(path)
    keys = [k for k in dict.fromkeys(_key(n) for n in names if n) if k]
    out = []
    base = len(fs.root.parts)
    for dirpath, dirs, files in os.walk(fs.root):
        depth = len(Path(dirpath).parts) - base
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.lower() != "textures") \
            if depth < meshfolder.MAX_DEPTH else []
        for n in sorted(files):
            p = Path(dirpath) / n
            if p.suffix.lower() not in PICTURE_SUFFIXES or meshfolder._is_normal(meshfolder._base(n)):
                continue
            try:
                # a card tool can leave the .tga empty beside the .tga.dds it wrote
                if p.stat().st_size == 0:
                    continue
            except OSError:
                continue
            rel = fs.rel(p)
            k = _key(n)
            score = max((1.0 if k == w else difflib.SequenceMatcher(None, k, w).ratio()
                         for w in keys), default=0.0)
            out.append({"rel": rel, "path": str(p), "kind": _kind(rel), "score": round(score, 3)})
        if len(out) > 5000:
            break
    out.sort(key=lambda c: (-c["score"], c["rel"].lower()))
    return out


def picture_path(root: str, rel: str) -> Optional[Path]:
    """A picture inside a folder already opened, for the page to show; ``None``
    for anything else, so the icon route serves nothing it was not shown."""
    key = str(Path(root).resolve()).lower()
    fs = meshfolder._OPEN.get(key)
    if fs is None or not rel:
        return None
    p = (fs.root / rel).resolve()
    try:
        p.relative_to(fs.root)
    except ValueError:
        return None
    return p if p.is_file() and p.suffix.lower() in PICTURE_SUFFIXES else None
