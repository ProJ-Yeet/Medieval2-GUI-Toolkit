"""Which strat model stands for each thing on the campaign map - Phase 97d.

The 3D view of the campaign map draws each character as its strat model and
each settlement as its culture's model for its level. Three files say which:

* ``descr_character.txt`` - per character type, per faction, a list of
  ``strat_model`` names. The first is the default; vanilla's named character
  lists the heir's second and the leader's third, and a mod adds custom ones
  after them.
* ``descr_model_strat.txt`` - each of those names as a mesh, a scale, and a
  texture per faction (:mod:`unittransfer.stratmap` reads it).
* ``descr_cultures.txt`` - per culture, a model per settlement level, and one
  each for a fort and a watchtower (:mod:`unittransfer.settlemodel`'s lines).

This module joins them into one table and reads no mesh: the browser asks
for each distinct mesh once, through the routes the Strat models tab already
uses, and draws it on every tile that names it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from . import settlemodel, stratmap


def characters(mod) -> Dict[str, Dict[str, List[str]]]:
    """``type -> faction -> [strat model names, in file order]``, lower case.

    A ``faction`` line names one or more factions, comma separated, and every
    ``strat_model`` after it belongs to all of them until the next ``faction``
    or ``type`` line.
    """
    text = stratmap._strip_comments(stratmap._read(mod.data / "descr_character.txt"))
    out: Dict[str, Dict[str, List[str]]] = {}
    typ, facs = "", []
    for line in text.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        key = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        if key == "type":
            typ, facs = rest.lower(), []
        elif key == "faction" and typ:
            facs = [f.strip().lower() for f in rest.split(",") if f.strip()]
        elif key == "strat_model" and typ and facs and rest:
            name = rest.split()[0].strip().lower()
            for f in facs:
                out.setdefault(typ, {}).setdefault(f, []).append(name)
    return out


def _scale(entry) -> float:
    """The ``scale`` line of a strat model block, 1 when it has none."""
    for line in stratmap._strip_comments(entry.raw).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() == "scale":
            try:
                return float(parts[1].rstrip(","))
            except ValueError:
                return 1.0
    return 1.0


def _textures(mod, entry, folders: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """``faction -> texture`` from the block's ``texture <faction>, <path>`` lines.

    Each path as the file really is on disk: the block writes ``.tga`` and a
    packed mod ships ``.tga.dds``. The game's order is :func:`cas.texture_path`'s,
    ``<name>.dds`` first and the name as written second, case ignored - but
    looked up in one listing per folder, kept in ``folders``, because asking
    ``texture_path`` lists and stats the folder every time, and DaC's 530
    texture lines against its 780-file textures folder took 42 seconds that
    way. A texture the mod does not ship is left out, and the figure wears
    the sheet its mesh names instead.
    """
    data = Path(mod.data)
    out: Dict[str, str] = {}
    for line in stratmap._strip_comments(entry.raw).splitlines():
        parts = line.split(None, 1)
        if len(parts) < 2 or parts[0].lower() not in ("texture", "texture_no_move"):
            continue
        fields = [f.strip() for f in parts[1].split(",")]
        if len(fields) < 2 or not fields[0] or not fields[1]:
            continue
        rel = stratmap.norm(fields[1])
        folder, _, name = rel.rpartition("/")
        if folder not in folders:
            try:
                folders[folder] = {p.name.lower(): p.name for p in (data / folder).iterdir()}
            except OSError:
                folders[folder] = {}
        have = folders[folder]
        for cand in (name.lower() + ".dds", name.lower()):
            if cand in have:
                out.setdefault(fields[0].lower(),
                               f"{folder}/{have[cand]}" if folder else have[cand])
                break
    return out


def _rel(value: str) -> str:
    """A culture line's model as a path under ``data/``."""
    rel = value.replace("\\", "/").strip().lstrip("/")
    return rel[5:] if rel.lower().startswith("data/") else rel


def scene(mod) -> dict:
    """The whole table the 3D map needs, in one answer.

    ``models`` holds only the strat model names some character uses, each with
    the mesh on disk it draws (the first one the block names that is there,
    never its shadow), its scale and its textures by faction. A name with no
    block or no mesh on disk is left out, and the browser draws nothing for a
    character that names it - the flat map's icon is still there to say where
    it stands.
    """
    chars = characters(mod)
    used = {n for per in chars.values() for names in per.values() for n in names}
    entries = stratmap.strat_file(mod).by_name()
    models = {}
    folders: Dict[str, Dict[str, str]] = {}
    for name in sorted(used):
        e = entries.get(name)
        if e is None:
            continue
        meshes = e.viewable(mod.data)
        if not meshes:
            continue
        models[name] = {"mesh": meshes[0], "scale": _scale(e), "textures": _textures(mod, e, folders)}

    cultures: Dict[str, Dict[str, str]] = {}
    try:
        cf, _ = settlemodel._read_cultures(mod)
    except settlemodel.ModelError:
        cf = None
    for cul in (cf.cultures if cf else []):
        rows = {}
        for lvl in cul.levels:
            model, _plan = settlemodel._model_of(lvl.values.get("normal", ""))
            if model and settlemodel._exists(mod, model):
                rows[lvl.name.lower()] = _rel(model)
        for key in ("fort", "watchtower"):
            if key in cul.values:
                model, _plan = settlemodel._model_of(cul.values[key])
                if model and settlemodel._exists(mod, model):
                    rows[key] = _rel(model)
        cultures[cul.name.lower()] = rows

    try:
        faction_culture = {k.lower(): (v or "").lower() for k, v in mod.faction_cultures.items()}
    except Exception:                                  # noqa: BLE001 - a mod file
        faction_culture = {}                           # that will not read leaves
    return {"characters": chars, "models": models,     # every faction cultureless
            "cultures": cultures, "faction_culture": faction_culture}
