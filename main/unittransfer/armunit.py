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
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import animkit, animpack, animslot, edit, edu, campstrat, stratchar
from . import i18n as _i18n
from .transfer import TransferOptions, apply_transfer, plan_transfer

#: The roles, in the order the menu offers them.
ROLES = ("heavy_infantry", "spear", "pike", "archer", "crossbow", "javelin", "cavalry")
#: What a template sets on a new unit.
TEMPLATE_FIELDS = ("class", "formation", "attributes", "mount")
#: Bones only an archer's skeleton has. A bow or sling weighted to them on a
#: melee skeleton is weighted to nothing the game knows, and the bow breaks.
BOW_BONES = ("bone_bowoffset", "bone_bowstring", "bone_sling")


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


def card_units(mod) -> List[dict]:
    """Every unit as the card maker's unit picker lists it: its soldier model,
    its armour upgrade models, and (2026-11-24) what it is drawn beside: its
    mount's descr_mount.txt model and its descr_engines.txt engine."""
    return [{"type": u.type, "category": u.category, "class": u.class_type,
             "soldier": u.soldier_model, "factions": list(u.ownership),
             "ug": list(u.armour_ug_models or []),
             "mount": (mod.mount_model(u.mount) or "") if u.mount else "",
             "engine": u.engine or ""}
            for u in mod.edu.units]


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
                  "weapons": list(sig[0][3]) + list(sig[0][4]), "fields": fields,
                  "members": [{"type": u.type, "soldier": u.soldier_model.lower()} for u, _s in rows]}
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


def existing_export(folder: str, stem: str) -> dict:
    from . import mesh
    d = Path(folder or "")
    if not folder.strip() or not d.is_dir():
        return {"found": False, "candidates": []}
    candidates = sorted(p.stem for p in d.glob("*.mesh"))
    if not (d / f"{stem}.mesh").is_file() and len(candidates) == 1:
        stem = candidates[0]
    files = baked_files(folder, stem) if (d / f"{stem}.mesh").is_file() else {}
    if not files:
        return {"found": False, "candidates": candidates}
    model = mesh.read_mesh(Path(files["mesh_src"]), layout=True)
    required = ["texture_src", "normal_src"]
    if any(g.sheets in ("attach", "both") for g in model.groups):
        required += ["attach_texture_src", "attach_normal_src"]
    missing = [k for k in required if k not in files]
    if missing:
        return {"found": False, "candidates": candidates, "missing": missing}
    return {"found": True, "stem": stem, "folder": str(d),
            "files": [Path(f).name for f in files.values()], "vertices": model.vertices,
            "triangles": model.triangles, "groups": len(model.groups), "existing": True}


def data_folder(data: Path, chosen: str) -> str:
    """A folder chosen by the picker as a path relative to this mod's data."""
    try:
        return Path(chosen).resolve().relative_to(data.resolve()).as_posix()
    except ValueError:
        raise InstallError(_i18n.msg("eng.armunit.outside_data", "choose a folder inside this mod's data folder")) from None


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
          "assign_to": assign, "replace": bool(req.get("replace"))}
    nm.update(baked_files(req.get("bake_folder") or "", req.get("stem") or ""))
    if req.get("skeletons"):
        nm["skeletons"] = dict(req["skeletons"])
    return nm


def weighted_bones(mesh_path) -> set:
    """The bones a baked ``.mesh`` weights any vertex to, lower case."""
    from . import mesh
    try:
        m = mesh.read_mesh(mesh_path)
    except (mesh.MeshError, OSError):
        return set()
    out, ids, w = set(), m.bone_ids, m.weights
    for v in range(len(w) // 2):
        for wi, bi in ((0, 2), (1, 1)):          # the weights pair with bytes 2 and 1
            if w[v * 2 + wi] > 0 and v * 4 + bi < len(ids) and ids[v * 4 + bi] < len(m.bones):
                out.add(m.bones[ids[v * 4 + bi]].lower())
    return out


def _clone_of(mod, req: dict, templates: Dict[str, dict], choice: str) -> str:
    """The entry a new entry would be cloned from, as :func:`_new_model` and
    the plan pick it."""
    c = (req.get("clone_from") or "").strip().lower()
    t = templates.get(req.get("template") or "")
    if not c and t:
        c = t["clone_from"]
    if not c and choice != "skip" and req.get("unit") in mod.edu.by_type():
        c = mod.edu.by_type()[req["unit"]].soldier_model.lower()
    return c


def _bow_fix(mod, req: dict, templates: Dict[str, dict], choice: str) -> Tuple[dict, str]:
    """A model weighted to a bow's bones cloned from an entry whose skeletons
    have none (a melee mesh made an archer) takes the skeletons of an entry
    that has them: the archer template's when it does, else the first soldier
    entry of the mod's that does. Returns the request and what was done."""
    try:
        files = baked_files(req.get("bake_folder") or "", req.get("stem") or "")
    except InstallError:
        return req, ""
    bow = weighted_bones(files["mesh_src"]) & set(BOW_BONES)
    if not bow:
        return req, ""
    packs, _whose = animpack.packs_for(mod.data)
    if packs is None or packs.skels is None:
        return req, ""
    seen: Dict[str, set] = {}

    def bones(name):
        if name.lower() not in seen:
            sk = packs.skeleton(name) if packs.skels.first(name) is not None else None
            seen[name.lower()] = {b.name.lower() for b in sk.bones} if sk else set()
        return seen[name.lower()]

    def fits(entry):
        e = mod.modeldb.by_name().get((entry or "").lower())
        return e is not None and any(bow <= bones(s) for s in e.skeletons())

    clone = _clone_of(mod, req, templates, choice)
    if not clone or fits(clone):
        return req, ""
    names = [templates["archer"]["clone_from"]] if "archer" in templates else []
    names += [u.soldier_model for u in mod.edu.units if u.soldier_model]
    pick = next((n.lower() for n in names if fits(n)), "")
    if not pick:
        return req, _i18n.msg("eng.armunit.bow_no_skeleton",
                              "the model is weighted to {bones}, and no soldier entry of this mod plays a skeleton with them: the bow will not animate",
                              bones=", ".join(sorted(bow)))
    return dict(req, clone_from=pick), _i18n.msg(
        "eng.armunit.bow_skeleton",
        "the model is weighted to {bones}, which {clone}'s skeletons have not got: it takes {pick}'s skeletons, an archer's, so the bow animates",
        bones=", ".join(sorted(bow)), clone=clone, pick=pick)


def _scale_steps(mod, req: dict, clone: str) -> Tuple[List[dict], Dict[str, str]]:
    """The body scale (``scale``, x y z, and ``scale_tag``): each skeleton the
    clone plays, scaled whole into ``<skeleton>_<tag>`` unless the mod's pack
    has that already. Returns the kit steps and the renaming for the entry."""
    sc = req.get("scale")
    if not sc:
        return [], {}
    try:
        nums = [float(v) for v in sc]
    except (TypeError, ValueError):
        nums = []
    if len(nums) != 3 or not all(v > 0 for v in nums):
        raise InstallError(_i18n.msg("eng.armunit.scale_numbers", "the body scale is three numbers above 0"))
    tag = re.sub(r"[^A-Za-z0-9_-]", "", str(req.get("scale_tag") or "")) \
        or "x" + "_".join(f"{v:g}" for v in dict.fromkeys(nums)).replace(".", "p")
    e = mod.modeldb.by_name().get(clone)
    if e is None:
        return [], {}
    try:
        packs = animslot._own(mod.data)
    except (animslot.SlotError, animpack.PackError) as exc:
        raise InstallError(str(exc)) from None
    steps, names = [], {}
    for s in dict.fromkeys(e.skeletons()):
        name = f"{s}_{tag}"[:63]
        if packs.skels.first(name) is None:
            steps.append({"kind": "skeleton", "scale": nums,
                          "plan": animkit.plan_kit(mod, s, name, [], scale=nums)})
        names[s.lower()] = name
    return steps, names


def _unit_request(mod, unit_type: str, req: dict, templates: Dict[str, dict],
                  fields: Optional[dict] = None) -> "edit.EditRequest":
    """The edit that makes ``unit_type`` wear the model: a new entry from the
    bake, or with ``entry`` one the mod already has; and with ``card_src`` /
    ``info_src`` a picture copied in as its cards, under its dictionary name."""
    d = {"unit": unit_type, "field_overrides": dict(fields or {}),
         "card_src": req.get("card_src") or "", "info_src": req.get("info_src") or ""}
    assign = req.get("assign_to") or "soldier"
    if not re.fullmatch(r"soldier|officer(?:#[1-9][0-9]*)?|armour_ug_models#[1-9][0-9]*", assign):
        raise InstallError(_i18n.msg("eng.armunit.invalid_slot", "choose a soldier, officer or armour tier slot"))
    u = mod.edu.by_type()[unit_type]
    name = req.get("entry") or (req.get("name") or "").strip().lower()
    block = u.raw
    if assign == "soldier" and u.armour_ug_models and u.armour_ug_models[0].lower() == u.soldier_model.lower():
        block = edu.set_model_slot(block, "armour_ug_models#1", name)
    if req.get("entry"):
        block = edu.set_model_slot(block, assign, name)
        if assign.startswith("armour_ug_models#"):
            block = edu.sync_armour_levels(block)
    else:
        d["new_models"] = [_new_model(req, templates, assign)]
    if block != u.raw:
        d["raw_block"] = block
    return edit.request_from_dict(d)


def character_targets(mod) -> list:
    """Campaign characters eligible for an optional battle model assignment."""
    out = []
    for campaign in campstrat.campaigns(mod):
        sf = campstrat.read_strat(mod, campaign)
        factions = []
        for faction in sf.of_kind("faction"):
            people = [{"name": n.name, "line": n.start + 1, "rank": str(n.get("rank") or "")}
                      for n in stratchar.characters_of(sf, faction)
                      if n.get("type") == "named character"]
            factions.append({"name": faction.name, "characters": people})
        out.append({"campaign": campaign, "factions": factions})
    return out


def _character_plan(mod, req, facts_of):
    target = req.get("character_target")
    if not isinstance(target, dict) or not facts_of or not all(
            target.get(k) for k in ("campaign", "faction", "character", "kind")):
        raise InstallError(_i18n.msg("eng.armunit.choose_character", "choose a campaign, faction and character"))
    sf = campstrat.read_strat(mod, target["campaign"])
    node = stratchar.find_character(sf, target["faction"], target["character"], int(target.get("line") or 0))
    kind = target["kind"]
    if (node is None or node.name != target["character"]
            or (target.get("line") and node.start + 1 != int(target["line"]))
            or node.get("type") != "named character" or kind not in ("general", "leader", "heir")
            or (kind in ("leader", "heir") and node.get("rank") != kind)):
        raise InstallError(_i18n.msg("eng.armunit.character_changed", "the selected character or rank changed; choose the target again"))
    name = (req.get("entry") or req.get("name") or "").strip().lower()
    return stratchar.plan_character(mod, facts_of(target["campaign"]), {
        "campaign": target["campaign"], "faction": target["faction"], "character": node.name,
        "line": node.start + 1, "action": "edit", "edits": {"battle_model": name}})


def plan_install(mod, req: dict, facts_of=None) -> dict:
    planned = _plan_install(mod, req)
    if req.get("character_target"):
        planned["steps"].append({"kind": "character", "plan": _character_plan(mod, req, facts_of)})
    return planned


def _plan_install(mod, req: dict) -> dict:
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
    note, kits = "", []
    if not entry:
        # a bow on a melee skeleton, and the body scale: the entry's skeletons
        req, note = _bow_fix(mod, req, templates, choice)
        kits, names = _scale_steps(mod, req, _clone_of(mod, req, templates, choice))
        if names:
            req = dict(req, skeletons=names)
    planned = _plan_steps(mod, req, choice, templates, entry)
    planned["req"] = req
    if note:
        warn = getattr(planned["steps"][-1]["plan"], "warnings", None)
        if isinstance(warn, list):
            warn.insert(0, note)
    planned["steps"] = kits + planned["steps"]
    return planned


def _plan_steps(mod, req: dict, choice: str, templates: Dict[str, dict], entry: str) -> dict:
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


def apply_install(mod_of, mod_name: str, req: dict, invalidate=None, facts_of=None) -> dict:
    """Write the chosen way, each step through its own door; a new unit's
    edit is planned again on the unit the duplicate made."""
    mod = mod_of(mod_name)
    planned = plan_install(mod, req, facts_of=facts_of)
    shown = payload(planned)
    if not shown["ok"]:
        raise InstallError("; ".join(e for st in shown["steps"] for e in st["errors"]))
    records = []
    # the scaled skeletons first, each planned again after the one before it
    # (they append to the same packs), then the steps as planned
    for st in [s for s in planned["steps"] if s["kind"] == "skeleton"]:
        kp = animkit.plan_kit(mod, st["plan"].base, st["plan"].name, [], scale=st["scale"])
        if not kp.ok:
            raise InstallError("; ".join(kp.payload()["errors"]))
        records.append(animkit.apply_kit(kp))
    planned["steps"] = [s for s in planned["steps"] if s["kind"] != "skeleton"]
    req = planned.get("req", req)
    def character_step():
        if req.get("character_target"):
            cp = _character_plan(mod_of(mod_name), req, facts_of)
            records.append(stratchar.apply_character(cp)["record"])
            if invalidate:
                invalidate(mod_name)

    if planned["choice"] in ("skip", "add"):
        records.append(edit.apply_edit(planned["steps"][0]["plan"]))
        if invalidate:
            invalidate(mod_name)
        character_step()
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
    character_step()
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
