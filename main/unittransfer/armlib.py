"""Armory Studio's asset library (Phase 95l).

Models kept for later: a model entry of any installed mod, or a model file on
disk, each with a name and notes of the user's own beside its code name, in
custom collections and categories of the user's own. It lives in
``config/armory/library.json`` and holds no art, only where each model is.

By default the library sorts itself four ways, worked out from each entry's
mod (:func:`facets`): the **unit class** and **unit type** (EDU class and
category) of the units that wear it, the **factions** it has a skin for or
that own those units, and their **tier** (the toolkit's own tier mark on a
unit, as the Units view sets it).

Two items are the same when they are the same entry of the same mod or the
same file, or when their model files are byte for byte the same (the hash the
assets panel already takes, 95e): a model copied into a second mod is caught.
"""
from __future__ import annotations

import json
from typing import Dict, List

from . import armory
from . import i18n as _i18n

def _path():
    # read through armory so a test that moves ARMORY_DIR moves this too
    return armory.ARMORY_DIR / "library.json"


def load() -> dict:
    try:
        lib = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lib = {}
    lib.setdefault("items", [])
    lib.setdefault("collections", [])
    lib.setdefault("categories", [])
    return lib


def save(lib: dict) -> None:
    armory.ARMORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(lib, indent=1), encoding="utf-8")
    tmp.replace(_path())


def item_key(item: dict) -> str:
    """The same key the page gives an asset (``armAssetKey``); an item that
    is one object of a model (2026-11-24, ``part``) adds that object's group."""
    part = item.get("part")
    key = armory.asset_key(item)
    return key + "#" + str(part.get("group")) if isinstance(part, dict) else key


def add(lib: dict, item: dict) -> dict:
    """``item`` added, or a sentence saying which item it already is.

    Returns ``{"item": ...}`` or ``{"same": <the existing item>, "why": ...}``.
    """
    key = item_key(item)
    for old in lib["items"]:
        if item_key(old) == key:
            return {"same": old, "why": "same"}
        # one object is never the same art as a whole model, or as another object
        if item.get("file_hash") and old.get("file_hash") == item.get("file_hash") and not item.get("part") and not old.get("part"):
            return {"same": old, "why": "art"}
    top = max([0] + [int(x.get("id") or 0) for x in lib["items"]])
    new = {k: item.get(k) for k in ("kind", "mod", "entry", "path", "unit", "file_hash") if item.get(k)}
    part = item.get("part")
    if isinstance(part, dict):
        new["part"] = {"group": int(part.get("group") or 0), "name": str(part.get("name") or ""), "mesh": str(part.get("mesh") or "")}
    new.update(id=top + 1, name=item.get("name") or item.get("entry") or (item.get("path") or "").replace("\\", "/").split("/")[-1],
               notes=item.get("notes") or "", collections=list(item.get("collections") or []),
               categories=list(item.get("categories") or []))
    lib["items"].append(new)
    return {"item": new}


def facets(lib: dict, mod_of) -> Dict[int, dict]:
    """Each entry item's default categories, from its mod."""
    out: Dict[int, dict] = {}
    by_mod: Dict[str, dict] = {}
    for it in lib.get("items") or []:
        f = {"class": [], "type": [], "faction": [], "tier": []}
        out[it.get("id")] = f
        if it.get("kind") != "entry":
            continue
        name = it.get("mod") or ""
        if name not in by_mod:
            try:
                by_mod[name] = _mod_index(mod_of(name))
            except Exception:          # a mod since removed: no categories
                by_mod[name] = {}
        idx = by_mod[name]
        hit = idx.get((it.get("entry") or "").lower())
        if hit:
            for k in f:
                f[k] = sorted(hit[k])
    return out


def _mod_index(mod) -> Dict[str, dict]:
    """``{entry: {class, type, faction, tier}}`` for every entry of a mod."""
    idx: Dict[str, dict] = {}

    def slot(name: str) -> dict:
        return idx.setdefault(name.lower(), {"class": set(), "type": set(), "faction": set(), "tier": set()})

    for e in mod.modeldb.entries:
        s = slot(e.name)
        for fac in e.factions():
            if fac and fac.lower() != "merc":
                s["faction"].add(fac.lower())
    for u in mod.edu.units:
        models = [u.soldier_model] + list(u.officers or []) + list(u.armour_ug_models or [])
        for m in models:
            if not m:
                continue
            s = slot(m)
            if u.class_type:
                s["class"].add(u.class_type.lower())
            if u.category:
                s["type"].add(u.category.lower())
            for fac in u.ownership or []:
                s["faction"].add(fac.lower())
            if u.tier:
                s["tier"].add(str(u.tier))
    return idx


def check_lib(lib: dict) -> dict:
    """A library from the page, kept to the shape it is saved in."""
    if not isinstance(lib, dict) or not isinstance(lib.get("items"), list):
        raise armory.ArmoryError(_i18n.msg("eng.armlib.not_a_library", "that is not an asset library"))
    for k in ("collections", "categories"):
        if not isinstance(lib.get(k), list):
            lib[k] = []
    return lib


def view(mod_of) -> dict:
    lib = load()
    return {"library": lib, "facets": {str(k): v for k, v in facets(lib, mod_of).items()}}
