"""Armory Studio's import unit menu (Phase 95k).

A baked model (95i, 95j) goes into a mod one of three ways, every one through
the doors the rest of the toolkit writes by, so each shows in My Changes and
comes back out with Undo:

* **Skip** - a new modeldb entry for this model only, in a folder of the
  user's choosing (:func:`edit.plan_bmdb`);
* **Add to a unit** - the same entry, made that unit's soldier model
  (:func:`edit.plan_edit` with ``assign_to: soldier``);
* **New unit** - a chosen unit duplicated in the mod (the same-mod transfer
  the unit list's *new unit from this one* is), then the entry made its soldier
  model, with a **role template** on top if one was picked.

An entry is always a clone of one the mod has (:class:`edit.NewModel`): the
mesh and the sheets are this model's, the skeletons, weapons, sprites and
faction records the clone's. **Role templates** (:func:`role_templates`) are
measured on the mod itself: for each role, the units that play it, the
animation set their soldier entries share most, and the EDU class, formation,
attributes (and for cavalry, mount) they share most. Picking one clones its
most typical entry, so the skeletons and weapons are the role's, and sets
those fields on a new unit.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import edit, edu
from . import i18n as _i18n
from .transfer import TransferOptions, apply_transfer, plan_transfer

#: The roles, in the order the menu offers them.
ROLES = ("heavy_infantry", "spear", "pike", "archer", "crossbow", "javelin", "cavalry")
#: What a template sets on a new unit.
TEMPLATE_FIELDS = ("class", "formation", "attributes", "mount")


class InstallError(ValueError):
    """The model cannot go into the mod this way, said as a sentence."""


def _skeleton(mod, model: str) -> Tuple[str, Optional[tuple]]:
    e = mod.modeldb.by_name().get((model or "").lower())
    if e is None or not e.animations:
        return "", None
    a = e.animations[0]
    sig = tuple((x.mount_type or "", x.primary_skeleton or "", x.secondary_skeleton or "",
                 tuple(x.pri_weapons), tuple(x.sec_weapons)) for x in e.animations)
    return (a.primary_skeleton or "").lower(), sig


def role_of(unit, skeleton: str) -> str:
    """The role a unit plays, by its EDU category and class and its soldier's
    primary skeleton; "" for one the menu does not offer (siege, ships...)."""
    cat, cls = (unit.category or "").lower(), (unit.class_type or "").lower()
    if cat == "cavalry":
        return "" if any(w in skeleton for w in ("bow", "javelin", "gun")) else "cavalry"
    if cat != "infantry":
        return ""
    if "crossbow" in skeleton:
        return "crossbow"
    if "javelin" in skeleton:
        return "javelin"
    if "bow" in skeleton:
        return "archer"
    if "pike" in skeleton:
        return "pike"
    if cls == "spearmen" or "spear" in skeleton:
        return "spear"
    if cls == "heavy":
        return "heavy_infantry"
    return ""


def _field(unit, key: str) -> str:
    for k, v in edu.block_fields(unit.raw):
        if k.lower() == key:
            return v.strip()
    return ""


def role_templates(mod) -> Dict[str, dict]:
    """Each role as this mod plays it: how many units, the entry to clone (the
    most typical soldier entry), and the EDU fields most of them share."""
    found: Dict[str, list] = {r: [] for r in ROLES}
    for u in mod.edu.units:
        skel, sig = _skeleton(mod, u.soldier_model)
        if sig is None:
            continue
        r = role_of(u, skel)
        if r:
            found[r].append((u, sig))
    out = {}
    for r in ROLES:
        rows = found[r]
        if not rows:
            continue
        sig, _n = Counter(s for _u, s in rows).most_common(1)[0]
        typical = [u for u, s in rows if s == sig]
        fields = {}
        for key in TEMPLATE_FIELDS:
            if key == "mount" and r != "cavalry":
                continue
            vals = Counter(v for v in (_field(u, key) for u, _s in rows) if v)
            if vals:
                fields[key] = vals.most_common(1)[0][0]
        example = typical[0]
        out[r] = {"role": r, "units": len(rows), "example": example.type,
                  "clone_from": example.soldier_model.lower(),
                  "skeletons": [x for x in (sig[0][1], sig[0][2]) if x],
                  "weapons": list(sig[0][3]) + list(sig[0][4]), "fields": fields}
    return out


# ---------------------------------------------------------------------------
# the plan


def baked_files(folder: str, stem: str) -> Dict[str, str]:
    """The files a bake wrote, by the slot each fills."""
    d = Path(folder or "")
    names = {"mesh_src": f"{stem}.mesh", "texture_src": f"{stem}.texture",
             "normal_src": f"{stem}_normal.texture", "attach_texture_src": f"{stem}_attach.texture",
             "attach_normal_src": f"{stem}_attach_normal.texture"}
    out = {k: str(d / v) for k, v in names.items() if (d / v).is_file()}
    if "mesh_src" not in out:
        raise InstallError(_i18n.msg("eng.armunit.no_bake", "bake the model first: {folder} holds no {stem}.mesh", folder=str(d), stem=stem))
    return out


def _new_model(req: dict, templates: Dict[str, dict], assign: str = "") -> dict:
    name = (req.get("name") or "").strip().lower()
    clone = (req.get("clone_from") or "").strip().lower()
    t = templates.get(req.get("template") or "")
    if t and not clone:
        clone = t["clone_from"]
    if not clone:
        raise InstallError(_i18n.msg("eng.armunit.no_clone", "choose an entry to take the skeletons from, or a role template"))
    folder = (req.get("folder") or "").strip().strip("/\\") or f"unit_models/_units/armory/{name}"
    nm = {"name": name, "clone_from": clone, "dest_dir": folder, "mesh_all_lods": True,
          "assign_to": assign}
    nm.update(baked_files(req.get("bake_folder") or "", req.get("stem") or ""))
    return nm


def _unit_request(mod, unit_type: str, req: dict, templates: Dict[str, dict],
                  fields: Optional[dict] = None) -> "edit.EditRequest":
    """The edit that makes ``unit_type`` wear the model: a new entry from the
    bake, or with ``entry`` one the mod already has; and with ``card_src`` /
    ``info_src`` a picture copied in as its cards, under its dictionary name."""
    d = {"unit": unit_type, "field_overrides": dict(fields or {}),
         "card_src": req.get("card_src") or "", "info_src": req.get("info_src") or ""}
    if req.get("entry"):
        u = mod.edu.by_type()[unit_type]
        d["raw_block"] = edu.set_model_slot(u.raw, "soldier", req["entry"])
    else:
        d["new_models"] = [_new_model(req, templates, "soldier")]
    return edit.request_from_dict(d)


def plan_install(mod, req: dict) -> dict:
    """What the chosen way would write, planned and not written.

    ``req``: ``choice`` (skip, add, new), ``name`` (the entry), ``folder``
    (under ``data/``), ``bake_folder`` and ``stem`` (the bake's files),
    ``clone_from`` or ``template``, ``unit`` (add, new) and ``new_type``,
    ``new_name`` (new). A new unit is planned as its two steps: the duplicate,
    then the edit, which is planned on the unit it is duplicated from, since
    the new one does not exist until the first step is written.
    """
    choice = req.get("choice") or "skip"
    templates = role_templates(mod)
    entry = (req.get("entry") or "").strip().lower()
    if entry:
        # an entry the mod has (a folder's import): it needs a unit to wear it
        if entry not in mod.modeldb.by_name():
            raise InstallError(_i18n.msg("eng.armunit.no_entry", "{mod} has no model entry {entry}", mod=mod.name, entry=entry))
        if choice == "skip":
            raise InstallError(_i18n.msg("eng.armunit.entry_needs_unit", "choose a unit to wear {entry}, or a new one", entry=entry))
        req = dict(req, entry=entry, clone_from=req.get("clone_from") or entry)
    if choice == "skip":
        er = edit.bmdb_request_from_dict({"new_models": [_new_model(req, templates)]})
        return {"choice": choice, "steps": [{"kind": "bmdb", "plan": edit.plan_bmdb(mod, er)}]}
    unit = req.get("unit") or ""
    if unit not in mod.edu.by_type():
        raise InstallError(_i18n.msg("eng.armunit.no_unit", "choose a unit of {mod}", mod=mod.name))
    if choice == "add":
        if not req.get("clone_from") and not req.get("template"):
            req = dict(req, clone_from=mod.edu.by_type()[unit].soldier_model)
        er = _unit_request(mod, unit, req, templates)
        return {"choice": choice, "steps": [{"kind": "edit", "plan": edit.plan_edit(mod, er)}]}
    new_type = (req.get("new_type") or "").strip()
    if not new_type:
        raise InstallError(_i18n.msg("eng.armunit.no_new_type", "give the new unit a type name"))
    if new_type in mod.edu.by_type():
        raise InstallError(_i18n.msg("eng.armunit.type_taken", "{mod} already has a unit {type}", mod=mod.name, type=new_type))
    if not req.get("clone_from") and not req.get("template"):
        req = dict(req, clone_from=mod.edu.by_type()[unit].soldier_model)
    # the copy speaks with the voice of the unit it copies
    opts = TransferOptions(on_conflict="rename", new_type=new_type,
                           new_name=(req.get("new_name") or "").strip() or None,
                           sound_mode="unit", sound_donor=unit)
    dup = plan_transfer(mod, unit, mod, opts)
    t = templates.get(req.get("template") or "")
    er = _unit_request(mod, unit, req, templates, t["fields"] if t else None)
    return {"choice": choice, "new_type": new_type,
            "steps": [{"kind": "transfer", "plan": dup}, {"kind": "edit", "plan": edit.plan_edit(mod, er), "on": unit}]}


def apply_install(mod_of, mod_name: str, req: dict, invalidate=None) -> dict:
    """Write the chosen way, each step through its own door; a new unit's
    edit is planned again on the unit the duplicate made."""
    mod = mod_of(mod_name)
    planned = plan_install(mod, req)
    shown = payload(planned)
    if not shown["ok"]:
        raise InstallError("; ".join(e for st in shown["steps"] for e in st["errors"]))
    records = []
    if planned["choice"] in ("skip", "add"):
        records.append(edit.apply_edit(planned["steps"][0]["plan"]))
        if invalidate:
            invalidate(mod_name)
        return {"records": records}
    records.append(apply_transfer(planned["steps"][0]["plan"]))
    if invalidate:
        invalidate(mod_name)
    mod = mod_of(mod_name)
    new_type = planned["new_type"]
    templates = role_templates(mod)
    if not req.get("clone_from") and not req.get("template"):
        req = dict(req, clone_from=mod.edu.by_type()[req["unit"]].soldier_model)
    if req.get("entry"):
        req = dict(req, entry=req["entry"].strip().lower())
    t = templates.get(req.get("template") or "")
    er = _unit_request(mod, new_type, req, templates, t["fields"] if t else None)
    plan = edit.plan_edit(mod, er)
    if plan.errors:
        raise InstallError("; ".join(str(e) for e in plan.errors))
    records.append(edit.apply_edit(plan))
    if invalidate:
        invalidate(mod_name)
    return {"records": records, "new_type": new_type}


def payload(planned: dict) -> dict:
    """A plan as the page shows it: each step's lines, warnings and errors."""
    steps = []
    for st in planned["steps"]:
        plan = st["plan"]
        errors = [str(e) for e in getattr(plan, "errors", []) or []]
        for attr in ("base_error", "option_error"):
            if getattr(plan, attr, None):
                errors.append(str(getattr(plan, attr)))
        steps.append({"kind": st["kind"], "on": st.get("on", ""),
                      "lines": [ln.strip() for ln in plan.summary().splitlines() if ln.strip()],
                      "warnings": [str(w) for w in getattr(plan, "warnings", []) or []],
                      "errors": errors})
    return {"choice": planned["choice"], "new_type": planned.get("new_type", ""), "steps": steps,
            "ok": not any(s["errors"] for s in steps)}
