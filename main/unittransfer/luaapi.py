"""The ``toolkit`` table a Lua script sees, and one script run (Phases 122-123).

A script reads the mod through functions (``toolkit.units()``,
``toolkit.unit(name)``, ``toolkit.models()``...) and changes it through
``toolkit.edit_*`` / ``toolkit.delete_*`` / ``toolkit.clone_*``. It never
writes a file: every change is the plan the editor screens make
(:func:`unittransfer.edit.plan_edit`, :func:`unittransfer.edit.plan_bmdb`),
written by their own :func:`unittransfer.edit.apply_edit`, so every rule
those screens keep holds for a script too.

**One run, one Log record.** Plans are whole-file text, so each change has to
see the ones before it: a run applies its changes one by one as the script
makes them (the reads after a change see it), then folds the records those
applies wrote into ONE record (:func:`_fold`) whose manifest holds, per file,
the state from before the run. The Log's Undo, in the app or
``lua_cli.py undo``, takes the whole run back. A change the editors refuse,
or any error in the script, undoes what the run had already applied and
writes nothing.

**A preview is a run taken back.** Without ``apply`` the run does all of the
above, compares every touched file with its state before the run, and undoes
the record, so the report shows exactly what an applied run would change. The
mod is touched while that happens; when it ends every file is byte-identical
to before (checked) and the Log holds nothing from it.

**The API is declared once** (:data:`API`): the Lua table, ``lua_cli.py api``
and the annotation file are all made from that list.
"""
from __future__ import annotations

import difflib
import hashlib
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import config, edu as edu_mod, edit, luarun, transfer
from .logutil import log
from .mod import Mod
from . import i18n as _i18n

# ---------------------------------------------------------------------------
# the API, declared once


@dataclass
class Fn:
    name: str
    params: List[tuple]          # (name, LuaLS type, doc)
    returns: str                 # LuaLS type, "" for none
    doc: str
    kind: str = "read"           # read | edit


_ARCHIVE = "the archive: `expanded`, `expanded.txt` or `text/expanded.txt.strings.bin`"
_CAMPAIGN = "a campaign folder (default imperial_campaign)"
_TRIGGER_FILE = "`traits` (export_descr_character_traits.txt) or `ancillaries` (export_descr_ancillaries.txt)"

API: List[Fn] = [
    Fn("units", [], "toolkit.Unit[]",
       "Every unit in the mod, in file order (the EDU, then M2TWEOP unit files)."),
    Fn("unit", [("type", "string", "the unit's `type` line")], "toolkit.Unit?",
       "One unit by its `type`, or nil."),
    Fn("models", [], "toolkit.Model[]", "Every battle_models.modeldb entry, in file order."),
    Fn("model", [("name", "string", "the entry name, any case")], "toolkit.Model?",
       "One modeldb entry by name, or nil."),
    Fn("mounts", [], "table<string, string>", "Each mount in descr_mount.txt and the model it uses."),
    Fn("factions", [], "{slot: string, name: string, culture: string}[]",
       "Every faction slot in descr_sm_factions.txt, in file order, with its shown name "
       "(text/expanded.txt) and culture."),
    Fn("buildings", [], "toolkit.Building[]",
       "Every building line in export_descr_buildings.txt, in file order."),
    Fn("building", [("name", "string", "the building line's name")], "toolkit.Building?",
       "One building line, or nil."),
    Fn("edit_unit",
       [("type", "string", "the unit's `type` line"),
        ("fields", "table<string, string|number|string[]|false>",
         "EDU field -> new value (a list is joined with \", \"); false removes the field. "
         "A repeated field is addressed as `officer#2`."),
        ("options", "{rename?: string, dictionary?: string, name?: string, descr?: string, "
         "descr_short?: string}?",
         "rename the unit (every file naming it follows), change its dictionary key, "
         "or its shown name and descriptions")],
       "", "Change one unit's EDU block (and its text entry).", "edit"),
    Fn("clone_unit",
       [("source", "string", "the unit to copy"), ("type", "string", "the new unit's `type`"),
        ("options", "{dictionary?: string, name?: string}?",
         "its dictionary key (default: the type in lower case, `_` for anything else) "
         "and its shown name (default: the type)")],
       "", "A new unit copied from an existing one in the same mod (the Transfer screen's "
           "copy-with-a-new-name, from the mod into itself): its block, its text, its models.", "edit"),
    Fn("delete_unit",
       [("type", "string", "the unit's `type` line"),
        ("options", "{keep_text?: boolean, remove_models?: boolean, keep_refs?: boolean}?",
         "keep its export_units entry; also remove battle models only it uses; "
         "leave the recruitment and army lines that name it")],
       "", "Delete one unit, and by default every line elsewhere that names it.", "edit"),
    Fn("edit_model",
       [("name", "string", "the entry name"),
        ("changes", "{raw?: string, rename?: string, texture?: string, normal?: string, "
         "sprite?: string, attach_texture?: string, attach_normal?: string}",
         "the whole entry as text, a new name (units follow), or a texture path for every faction")],
       "", "Change one modeldb entry.", "edit"),
    Fn("clone_model",
       [("source", "string", "the entry to copy"), ("name", "string", "the new entry's name")],
       "", "Add a modeldb entry copied from an existing one.", "edit"),
    Fn("mercenaries", [("campaign", "string?", "a campaign folder (default imperial_campaign)")],
       "toolkit.MercPool[]", "Every mercenary pool of a campaign's descr_mercenaries.txt, in file order."),
    Fn("edit_merc_unit",
       [("pool", "string", "the pool's name"), ("place", "integer", "the unit line's place in it, from 1"),
        ("edits", "table<string, any>",
         "exp, cost, replenish {a, b}, max, initial, start_year, end_year, religions, events, factions, "
         "crusading; false takes an option off (crusading = false clears the flag)"),
        ("campaign", "string?", "default imperial_campaign")],
       "", "Change one unit line of a mercenary pool.", "edit"),
    Fn("add_merc_unit",
       [("pool", "string", "the pool's name"),
        ("values", "table<string, any>", "name, exp, cost, replenish {a, b}, max, initial, and any option"),
        ("campaign", "string?", "default imperial_campaign")],
       "", "Add a unit line at the end of a mercenary pool.", "edit"),
    Fn("delete_merc_unit",
       [("pool", "string", "the pool's name"), ("place", "integer", "the unit line's place, from 1"),
        ("campaign", "string?", "default imperial_campaign")],
       "", "Take one unit line out of a mercenary pool. The lines after it move up one place.", "edit"),
    Fn("traits", [], "toolkit.Trait[]", "Every trait in export_descr_character_traits.txt, in file order."),
    Fn("trait", [("name", "string", "the trait's name")], "toolkit.Trait?", "One trait, or nil."),
    Fn("edit_trait",
       [("name", "string", "the trait"),
        ("changes", "{characters?: string[], hidden?: boolean, exclude_cultures?: string[], "
         "no_going_back_level?: string, anti_traits?: string[], "
         "levels?: table<integer, toolkit.LevelEdit>}",
         "what to change; `levels` is keyed by the level's place from 1, and levels not named stay as "
         "they are (a level's `effects`, when given, replace its effect lines)")],
       "", "Change one trait's header or its levels. Levels are not added or taken out here.", "edit"),
    Fn("ancillaries", [], "toolkit.Ancillary[]", "Every ancillary in export_descr_ancillaries.txt, in file order."),
    Fn("ancillary", [("name", "string", "the ancillary's name")], "toolkit.Ancillary?",
       "One ancillary, or nil."),
    Fn("edit_ancillary",
       [("name", "string", "the ancillary"),
        ("changes", "{type?: string, transferable?: string|integer, image?: string, unique?: boolean, "
         "excluded_ancillaries?: string[], exclude_cultures?: string[], description?: string, "
         "effects_description?: string, effects?: {attribute: string, amount: string|integer}[]}",
         "what to change; `effects`, when given, replace its effect lines")],
       "", "Change one ancillary.", "edit"),
    Fn("edit_building",
       [("line", "string", "the building line"), ("level", "string", "the level in it"),
        ("changes", "{settlement?: string, requires?: string, scalars?: table<string, string|number>, "
         "upgrades?: string[], capabilities?: toolkit.CapabilityOp[], "
         "faction_capabilities?: toolkit.CapabilityOp[]}",
         "what to change; capabilities not listed stay as they are")],
       "", "Change one building level: its header, its values, its upgrades or its capability lines. "
           "Line numbers change after an edit, so read the building again before the next one.", "edit"),
    Fn("strings", [("file", "string", _ARCHIVE)], "{tag: string, value: string}[]",
       "Every entry of one data/text .strings.bin archive, in file order. An archive addressed by "
       "position (battle, shared, strat, tooltips) has empty tags."),
    Fn("string", [("file", "string", _ARCHIVE),
                  ("tag", "string|integer", "the entry's tag, or its place from 1 in an archive with no tags")],
       "string?", "One entry's text, or nil."),
    Fn("edit_strings",
       [("file", "string", _ARCHIVE),
        ("changes", "table<string|integer, string|false>",
         "tag -> new text; a tag the archive does not have is added, false takes the entry out. "
         "An archive with no tags is keyed by place from 1 and only takes new text")],
       "", "Change entries of one .strings.bin archive: the Strings screen's save.", "edit"),
    Fn("settlements", [("campaign", "string?", _CAMPAIGN)], "toolkit.Settlement[]",
       "Every settlement in a campaign's descr_strat.txt, in file order."),
    Fn("edit_settlement",
       [("region", "string", "the region the settlement stands in"),
        ("changes", "toolkit.SettlementEdit", "what to change; what is not named stays as it is"),
        ("campaign", "string?", _CAMPAIGN)],
       "", "Change one settlement of descr_strat.txt: its values, its buildings, or the faction "
           "that holds it.", "edit"),
    Fn("strat_objects", [("campaign", "string?", _CAMPAIGN)], "toolkit.StratObject[]",
       "Every fort, watchtower and resource in a campaign's descr_strat.txt, in file order."),
    Fn("edit_strat_object",
       [("kind", "string", "fort, watchtower or resource"), ("x", "integer", "the tile it is on now"),
        ("y", "integer", ""),
        ("changes", "{x?: integer, y?: integer, type?: string, culture?: string, name?: string, "
         "region?: string, delete?: boolean}",
         "new values; `region` files a fort or watchtower under another section; delete = true "
         "takes it out"),
        ("campaign", "string?", _CAMPAIGN)],
       "", "Change, move or delete one fort, watchtower or resource, found by its tile.", "edit"),
    Fn("add_strat_object",
       [("kind", "string", "fort, watchtower or resource"),
        ("values", "{x: integer, y: integer, type?: string, culture?: string, name?: string, "
         "region?: string}", "a resource's `name` is its kind (timber, iron...)"),
        ("campaign", "string?", _CAMPAIGN)],
       "", "Add a fort, watchtower or resource to descr_strat.txt.", "edit"),
    Fn("clone_faction",
       [("source", "string", "the faction to copy"), ("new", "string", "the new faction's name"),
        ("options", "{label?: string, art?: boolean}?",
         "its shown name; art = false copies no pictures")],
       "", "A new faction copied from an existing one: the Factions screen's clone, in every file "
           "it touches.", "edit"),
    Fn("triggers", [("file", "string", _TRIGGER_FILE)], "toolkit.Trigger[]",
       "Every trigger of the traits or the ancillaries file, in file order."),
    Fn("edit_trigger",
       [("file", "string", _TRIGGER_FILE), ("name", "string", "the trigger"),
        ("changes", "{name?: string, when_to_test?: string, conditions?: toolkit.Condition[], "
         "effects?: {keyword?: string, args?: string[]}[], raw?: string}",
         "`conditions`, when given, are all of them; `effects` change the existing effect lines in "
         "order; `raw` is the whole block as text and wins over the rest")],
       "", "Change one trigger.", "edit"),
    Fn("add_trigger",
       [("file", "string", _TRIGGER_FILE),
        ("trigger", "{name: string, when_to_test: string, conditions?: toolkit.Condition[], "
         "effects?: {keyword: string, args: string[]}[]}", "the new trigger")],
       "", "Add a trigger at the end of the file.", "edit"),
    Fn("delete_trigger", [("file", "string", _TRIGGER_FILE), ("name", "string", "the trigger")],
       "", "Take one trigger out.", "edit"),
    Fn("recruits", [], "toolkit.Recruit[]",
       "Every recruit_pool line of export_descr_buildings.txt: the recruitment sheet's rows."),
    Fn("edit_recruit",
       [("line", "integer", "the row's line in the EDB, from recruits()"),
        ("changes", "{initial?: number, per_turn?: number, maximum?: number, experience?: integer}",
         "the numbers to change")],
       "", "Change the numbers of one recruit_pool line: the recruitment sheet's Apply.", "edit"),
]

CLASSES = {
    "toolkit.Unit": [
        ("type", "string"), ("dictionary", "string"), ("name", "string", "shown name, from export_units"),
        ("category", "string"), ("class", "string"), ("kind", "string", "category refined by weapon"),
        ("ownership", "string[]"), ("era0", "string[]"), ("era1", "string[]"), ("era2", "string[]"),
        ("soldier", "string", "battle model"), ("officers", "string[]"), ("mount", "string"),
        ("ship", "string"), ("engine", "string"), ("animal", "string"),
        ("armour_models", "string[]"), ("attributes", "string[]"), ("mercenary", "boolean"),
        ("stat_pri", "string[]"), ("stat_sec", "string[]"), ("projectiles", "string[]"),
        ("fields", "table<string, string>", "every field line as text, `officer#2` for repeats"),
        ("field_order", "string[]", "the field names in file order"),
        ("eop", "boolean", "in an M2TWEOP unit file"), ("file", "string", "the file it is in"),
        ("raw", "string", "the block as the file has it"),
    ],
    "toolkit.Model": [
        ("name", "string"), ("scale", "number"),
        ("lods", "{mesh: string, distance: integer}[]"),
        ("textures", "{faction: string, texture: string, normal: string, sprite: string}[]"),
        ("attachments", "{faction: string, texture: string, normal: string, sprite: string}[]"),
        ("animations", "{mount: string, primary: string, secondary: string, "
                       "primary_weapons: string[], secondary_weapons: string[]}[]"),
        ("raw", "string"),
    ],
    "toolkit.Building": [
        ("name", "string"), ("convert_to", "string"), ("religion", "string"),
        ("levels", "string[]", "the level names in upgrade order"),
        ("blocks", "toolkit.Level[]", "each level's block"),
    ],
    "toolkit.Level": [
        ("name", "string"), ("settlement", "string", "city, castle or empty for both"),
        ("requires", "string"), ("scalars", "table<string, string>", "cost, construction..."),
        ("upgrades", "string[]"),
        ("capabilities", "toolkit.Capability[]"), ("faction_capabilities", "toolkit.Capability[]"),
        ("recruits", "{unit: string, initial: string, per_turn: string, maximum: string, "
                     "experience: string, requires: string}[]"),
    ],
    "toolkit.Capability": [
        ("keyword", "string"), ("args", "string"), ("requires", "string"),
        ("line", "integer", "its line in the EDB, which names it in a CapabilityOp"),
    ],
    "toolkit.MercPool": [
        ("name", "string"), ("regions", "string[]"),
        ("units", "toolkit.MercUnit[]", "its unit lines, in file order"),
    ],
    "toolkit.MercUnit": [
        ("place", "integer", "its place in the pool, from 1"), ("name", "string"),
        ("exp", "integer"), ("cost", "integer"), ("replenish", "number[]"), ("max", "integer"),
        ("initial", "integer"), ("start_year", "integer?"), ("end_year", "integer?"),
        ("religions", "string[]?"), ("events", "string[]?"), ("factions", "string[]?"),
        ("crusading", "boolean"), ("fault", "string", "why the line could not be read, if it could not"),
    ],
    "toolkit.Trait": [
        ("name", "string"), ("characters", "string[]"), ("hidden", "boolean"),
        ("exclude_cultures", "string[]"), ("no_going_back_level", "string"), ("anti_traits", "string[]"),
        ("levels", "toolkit.TraitLevel[]"),
    ],
    "toolkit.TraitLevel": [
        ("name", "string"), ("threshold", "string"), ("description", "string"),
        ("effects_description", "string"), ("gain_message", "string"), ("lose_message", "string"),
        ("epithet", "string"), ("effects", "{attribute: string, amount: string}[]"),
    ],
    "toolkit.LevelEdit": [
        ("threshold", "string|integer?"), ("description", "string?"), ("effects_description", "string?"),
        ("gain_message", "string?"), ("lose_message", "string?"), ("epithet", "string?"),
        ("effects", "{attribute: string, amount: string|integer}[]?", "the level's effect lines, all of them"),
    ],
    "toolkit.Ancillary": [
        ("name", "string"), ("type", "string"), ("transferable", "string"), ("image", "string"),
        ("unique", "boolean"), ("excluded_ancillaries", "string[]"), ("exclude_cultures", "string[]"),
        ("description", "string"), ("effects_description", "string"),
        ("effects", "{attribute: string, amount: string}[]"),
    ],
    "toolkit.Settlement": [
        ("region", "string"), ("faction", "string", "the faction block it sits in"),
        ("kind", "string", "city or castle"), ("level", "string"), ("population", "integer?"),
        ("year_founded", "integer?"), ("plan_set", "string"), ("faction_creator", "string"),
        ("buildings", "{line: string, level: string}[]"),
    ],
    "toolkit.SettlementEdit": [
        ("kind", "string?", "city or castle"), ("level", "string?"), ("population", "integer?"),
        ("year_founded", "integer?"), ("plan_set", "string?"), ("faction_creator", "string?"),
        ("buildings", "{line: string, level: string}[]?", "the whole list, in order"),
        ("owner", "string?", "move the settlement into another faction's block"),
        ("place", "string?", "first or last in that block (first makes it the capital)"),
        ("raw", "string?", "the whole block as text; wins over the values"),
    ],
    "toolkit.StratObject": [
        ("kind", "string", "fort, watchtower or resource"), ("line", "integer", "its line in the file"),
        ("x", "integer"), ("y", "integer"), ("type", "string"), ("culture", "string"),
        ("name", "string", "a resource's kind"),
    ],
    "toolkit.Trigger": [
        ("name", "string"), ("when_to_test", "string"), ("conditions", "toolkit.Condition[]"),
        ("effects", "{keyword: string, args: string[]}[]"), ("raw", "string"),
    ],
    "toolkit.Condition": [
        ("term", "string"), ("args", "string[]"), ("joiner", "string", "and / or; empty on the first"),
        ("negated", "boolean"),
    ],
    "toolkit.Recruit": [
        ("line", "integer"), ("unit", "string"), ("building", "string"), ("level", "string"),
        ("settlement", "string"), ("section", "string", "capability or faction_capability"),
        ("requires", "string"), ("initial", "number"), ("per_turn", "number"), ("maximum", "number"),
        ("experience", "integer"),
    ],
    "toolkit.CapabilityOp": [
        ("line", "integer?", "an existing line (from a read); leave out for a new one"),
        ("keyword", "string?"), ("args", "string?"), ("requires", "string?"),
        ("delete", "boolean?", "take the line out"),
    ],
}


def api_text() -> str:
    """The API as plain text, for ``lua_cli.py api``."""
    out = []
    for f in API:
        sig = ", ".join(p[0] for p in f.params)
        out.append(f"toolkit.{f.name}({sig})" + (f" -> {f.returns}" if f.returns else ""))
        out.append(f"    {f.doc}")
        for p in f.params:
            out.append(f"    {p[0]}: {p[2]}")
    for cls, flds in CLASSES.items():
        out.append(f"\n{cls}:")
        for fl in flds:
            out.append(f"    .{fl[0]}: {fl[1]}" + (f"  ({fl[2]})" if len(fl) > 2 else ""))
    return "\n".join(out)


def annotations() -> str:
    """A LuaLS annotation file for the API, so VS Code (or any editor running
    the Lua language server) completes and checks ``toolkit`` and ``args``."""
    out = ["---@meta",
           "-- The Medieval II GUI Toolkit's Lua API (lua_cli.py). Made by",
           "-- `python lua_cli.py annotations <folder>`; do not edit by hand.", ""]
    for cls, flds in CLASSES.items():
        out.append(f"---@class {cls}")
        for fl in flds:
            out.append(f"---@field {fl[0]} {fl[1]}" + (f" {fl[2]}" if len(fl) > 2 else ""))
        out.append("")
    out += ["---@class toolkit.Mod", "---@field name string the mod's folder name",
            "---@field root string the mod's folder", "",
            "---The mod the script runs against. Reads see every edit made before them;",
            "---edits are previewed unless the run has --apply.",
            "---@class toolkit", "---@field mod toolkit.Mod", "toolkit = {}", ""]
    for f in API:
        out.append(f"---{f.doc}")
        for p in f.params:
            out.append(f"---@param {p[0]} {p[1]} {p[2]}")
        if f.returns:
            out.append(f"---@return {f.returns}")
        args = ", ".join(p[0] for p in f.params)
        out += [f"function toolkit.{f.name}({args}) end", ""]
    out += ["---Values given on the command line with --set key=value.",
            "---@type table<string, string>", "args = {}", ""]
    return "\n".join(out)


def write_annotations(folder: Path) -> List[Path]:
    """``toolkit.lua`` and a ``.luarc.json`` that points the language server
    at it (Lua 5.4, the sandbox's library), in ``folder``."""
    import json
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stub = folder / "toolkit.lua"
    stub.write_text(annotations(), encoding="utf-8")
    rc = folder / ".luarc.json"
    cfg = json.loads(rc.read_text(encoding="utf-8")) if rc.is_file() else {}
    cfg["runtime.version"] = "Lua 5.4"
    cfg["runtime.builtin"] = {**cfg.get("runtime.builtin", {}),
                              "io": "disable", "os": "disable", "debug": "disable",
                              "package": "disable"}
    libs = list(cfg.get("workspace.library", []))
    if "toolkit.lua" not in libs:
        libs.append("toolkit.lua")
    cfg["workspace.library"] = libs
    rc.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return [stub, rc]


# ---------------------------------------------------------------------------
# reads


def _rel(mod: Mod, path: str) -> str:
    try:
        return Path(path).resolve().relative_to(Path(mod.root).resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def unit_view(mod: Mod, u) -> dict:
    loc = mod.loc.get(u.dictionary)
    pairs = edu_mod.block_fields(u.raw)
    return {
        "type": u.type, "dictionary": u.dictionary, "name": loc.name if loc else "",
        "category": u.category, "class": u.class_type, "kind": u.kind(),
        "ownership": list(u.ownership), "era0": list(u.era0), "era1": list(u.era1),
        "era2": list(u.era2), "soldier": u.soldier_model, "officers": list(u.officers),
        "mount": u.mount, "ship": u.ship, "engine": u.engine, "animal": u.animal,
        "armour_models": list(u.armour_ug_models), "attributes": list(u.attributes),
        "mercenary": bool(u.mercenary_unit), "stat_pri": list(u.stat_pri),
        "stat_sec": list(u.stat_sec), "projectiles": u.projectiles(),
        "fields": {k: v for k, v in pairs}, "field_order": [k for k, _ in pairs],
        "eop": bool(u.is_eop),
        "file": _rel(mod, u.eop_file) if u.is_eop else "data/export_descr_unit.txt",
        "raw": u.raw,
    }


def _tex(t) -> dict:
    return {"faction": t.faction, "texture": t.texture, "normal": t.normal, "sprite": t.sprite}


def model_view(e) -> dict:
    return {
        "name": e.name, "scale": e.scale,
        "lods": [{"mesh": m, "distance": d} for m, d in e.lods],
        "textures": [_tex(t) for t in e.main_textures],
        "attachments": [_tex(t) for t in e.attach_textures],
        "animations": [{"mount": a.mount_type, "primary": a.primary_skeleton,
                        "secondary": a.secondary_skeleton,
                        "primary_weapons": list(a.pri_weapons),
                        "secondary_weapons": list(a.sec_weapons)} for a in e.animations],
        "raw": e.raw,
    }


def trait_view(t) -> dict:
    d = t.as_dict()
    return {"name": d["name"], "characters": d["characters"], "hidden": d["hidden"],
            "exclude_cultures": d["exclude_cultures"], "no_going_back_level": d["no_going_back_level"],
            "anti_traits": d["anti_traits"],
            "levels": [{k: v for k, v in lv.items() if k not in ("start", "end")}
                       | {"effects": [{"attribute": e["attribute"], "amount": e["amount"]}
                                      for e in lv["effects"]]} for lv in d["levels"]]}


def ancillary_view(a) -> dict:
    d = a.as_dict()
    return {k: v for k, v in d.items() if k not in ("start", "end")} | {
        "effects": [{"attribute": e["attribute"], "amount": e["amount"]} for e in d["effects"]]}


def _cap(c) -> dict:
    return {"keyword": c.keyword, "args": c.args, "requires": c.requires, "line": c.line}


def building_view(b) -> dict:
    return {
        "name": b.name, "convert_to": b.convert_to, "religion": b.religion,
        "levels": list(b.levels),
        "blocks": [{
            "name": k.name, "settlement": k.settlement, "requires": k.requires,
            "scalars": dict(k.scalars), "upgrades": list(k.upgrades),
            "capabilities": [_cap(c) for c in k.capabilities],
            "faction_capabilities": [_cap(c) for c in k.faction_capabilities],
            "recruits": [{"unit": p.unit, "initial": p.initial, "per_turn": p.per_turn,
                          "maximum": p.maximum, "experience": p.experience,
                          "requires": p.requires} for p in k.recruits],
        } for k in b.blocks],
    }


# ---------------------------------------------------------------------------
# a run


class Refused(Exception):
    """An edit the editors refuse: the script stops and nothing is written."""


@dataclass
class FileChange:
    rel: str
    status: str                  # changed | created | deleted
    diff: str = ""
    added: int = 0
    removed: int = 0


@dataclass
class Report:
    script: str
    mod: str
    applied: bool = False
    ok: bool = False
    error: str = ""
    error_kind: str = ""
    printed: List[str] = field(default_factory=list)
    edits: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files: List[FileChange] = field(default_factory=list)
    log_id: str = ""
    seconds: float = 0.0


def _text_value(v) -> str:
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, bool):
        raise Refused(_i18n.msg("eng.luaapi.a_field_value_is_text_a", "a field value is text, a number or a list; false removes the field"))
    if isinstance(v, float) and v == int(v):
        v = int(v)
    return str(v)


class Run:
    """One script against one mod."""

    def __init__(self, mod: Mod, *, script_name: str = "script.lua"):
        self.mod = mod
        self.script_name = script_name
        self.records: List[dict] = []
        self.edits: List[str] = []
        self.warnings: List[str] = []
        self.refused: List[str] = []

    # -- reads ---------------------------------------------------------------
    def _units(self):
        return [unit_view(self.mod, u) for u in self.mod.edu.units]

    def _unit(self, t):
        u = self.mod.edu.by_type().get(str(t))
        return unit_view(self.mod, u) if u else None

    def _models(self):
        return [model_view(e) for e in self.mod.modeldb.entries]

    def _model(self, name):
        n = str(name).lower()
        e = next((e for e in self.mod.modeldb.entries if e.name.lower() == n), None)
        return model_view(e) if e else None

    def _mounts(self):
        return {str(k): str(v) for k, v in (self.mod.mounts or {}).items()}

    def _factions(self):
        from . import factions
        names, cultures = self.mod.faction_names or {}, self.mod.faction_cultures or {}
        return [{"slot": s, "name": str(names.get(s, "")), "culture": str(cultures.get(s, ""))}
                for s in factions.faction_slots(self.mod)]

    def _edb(self):
        if not Path(self.mod.edb_path).is_file():
            return None
        return self.mod.edb

    def _buildings(self):
        edb = self._edb()
        return [building_view(b) for b in edb.buildings] if edb else []

    def _building(self, name):
        edb = self._edb()
        b = edb.get(str(name)) if edb else None
        return building_view(b) if b else None

    # -- edits ---------------------------------------------------------------
    def _modeldb_stamp(self):
        out = []
        paths = [self.mod.modeldb_path]
        try:
            from . import modeltext
            paths.append(modeltext.text_path(self.mod))
        except Exception:  # noqa: BLE001 - a mod without text models
            pass
        for p in paths:
            try:
                st = Path(p).stat()
                out.append((str(p), st.st_size, st.st_mtime_ns))
            except OSError:
                out.append((str(p), -1, -1))
        return out

    def _apply(self, plan, what: str, applier: Callable = None) -> None:
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        # an apply forgets every cached read; the parsed modeldb is most of the
        # cost of the next edit (0.9 s on DaC's 1,678 entries), so when its file
        # was not written it is handed back
        cached, stamp = self.mod.__dict__.get("modeldb"), self._modeldb_stamp()
        rec = (applier or edit.apply_edit)(plan)
        if cached is not None and "modeldb" not in self.mod.__dict__ and self._modeldb_stamp() == stamp:
            self.mod.__dict__["modeldb"] = cached
        self.records.append(rec)
        self.edits.append(what)
        self.warnings += [f"{what}: {w}" for w in plan.warnings]

    def edit_unit(self, t, fields=None, options=None) -> None:
        t, fields, options = str(t), fields or {}, options or {}
        if t not in self.mod.edu.by_type():
            raise Refused(_i18n.msg("eng.luaapi.no_unit_in", "no unit '{t}' in {name}", t=t, name=self.mod.name))
        overrides, removes = {}, []
        for k, v in fields.items():
            if v is False:
                removes.append(str(k))
            else:
                overrides[str(k)] = _text_value(v)
        unknown = set(options) - {"rename", "dictionary", "name", "descr", "descr_short"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_unit_unknown_option_s", "edit_unit: unknown option(s) {unknown}", unknown=', '.join(sorted(unknown))))
        loc = None
        if any(k in options for k in ("name", "descr", "descr_short")):
            u = self.mod.edu.by_type()[t]
            cur = self.mod.loc.get(u.dictionary)
            loc = {"name": options.get("name", cur.name if cur else ""),
                   "descr": options.get("descr", (cur.descr or "") if cur else ""),
                   "descr_short": options.get("descr_short", (cur.descr_short or "") if cur else "")}
        req = edit.EditRequest(unit=t, new_type=str(options.get("rename", "")).strip(),
                               new_dictionary=str(options.get("dictionary", "")).strip(),
                               field_overrides=overrides, remove_fields=removes, loc=loc)
        self._apply(edit.plan_edit(self.mod, req), f"edit unit '{t}'")

    def clone_unit(self, src, new_type, options=None) -> None:
        import re
        src, new_type, options = str(src), str(new_type).strip(), options or {}
        units = self.mod.edu.by_type()
        if src not in units:
            raise Refused(_i18n.msg("eng.luaapi.no_unit_in_2", "no unit '{src}' in {name}", src=src, name=self.mod.name))
        if not new_type:
            raise Refused(_i18n.msg("eng.luaapi.clone_unit_needs_the_new_units", "clone_unit needs the new unit's type"))
        if new_type in units:
            raise Refused(_i18n.msg("eng.luaapi.a_unit_called_already_exists_in", "a unit called '{new_type}' already exists in {name}", new_type=new_type, name=self.mod.name))
        unknown = set(options) - {"dictionary", "name"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.clone_unit_unknown_option_s", "clone_unit: unknown option(s) {unknown}", unknown=', '.join(sorted(unknown))))
        dictionary = str(options.get("dictionary") or re.sub(r"[^a-z0-9_]+", "_", new_type.lower()).strip("_"))
        if any(u.dictionary == dictionary for u in units.values()):
            raise Refused(_i18n.msg("eng.luaapi.the_dictionary_key_is_already_a", "the dictionary key '{dictionary}' is already a unit's in {name}", dictionary=dictionary, name=self.mod.name))
        opts = transfer.TransferOptions(on_conflict="rename", new_type=new_type, new_dictionary=dictionary,
                                        new_name=str(options.get("name") or new_type),
                                        bring_animations=False, keep_rebuildable=False)
        plan = transfer.plan_transfer(self.mod, src, self.mod, opts)
        what = f"clone unit '{src}' as '{new_type}'"
        why = list(plan.errors) + [x for x in (plan.base_error, plan.option_error) if x]
        if why or plan.skipped:
            raise Refused(f"{what}: {'; '.join(why) or 'the transfer would skip it'}")
        self._apply(plan, what, transfer.apply_transfer)

    def delete_unit(self, t, options=None) -> None:
        t, options = str(t), options or {}
        if t not in self.mod.edu.by_type():
            raise Refused(_i18n.msg("eng.luaapi.no_unit_in", "no unit '{t}' in {name}", t=t, name=self.mod.name))
        ops = edit.DeleteOptions(remove_loc=not options.get("keep_text", False),
                                 remove_models=bool(options.get("remove_models", False)),
                                 remove_assets=False, remove_icons=False,
                                 remove_refs=not options.get("keep_refs", False))
        req = edit.EditRequest(unit=t, delete=True, delete_options=ops)
        self._apply(edit.plan_edit(self.mod, req), f"delete unit '{t}'")

    def edit_model(self, name, changes=None) -> None:
        name, changes = str(name).lower(), changes or {}
        if self._model(name) is None:
            raise Refused(_i18n.msg("eng.luaapi.no_modeldb_entry_in", "no modeldb entry '{name}' in {name2}", name=name, name2=self.mod.name))
        kinds = {"texture", "normal", "sprite", "attach_texture", "attach_normal"}
        unknown = set(changes) - kinds - {"raw", "rename"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_model_unknown_change_s", "edit_model: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        me = edit.ModelEdit(entry=name, new_name=str(changes.get("rename", "")).strip().lower(),
                            raw_entry=str(changes.get("raw", "")),
                            defaults=edit._clean_paths({k: v for k, v in changes.items() if k in kinds}))
        self._apply(edit.plan_bmdb(self.mod, edit.EditRequest(unit="", model_edits=[me])),
                    f"edit model '{name}'")

    def clone_model(self, src, name) -> None:
        src, name = str(src).lower(), str(name).strip().lower()
        if self._model(src) is None:
            raise Refused(_i18n.msg("eng.luaapi.no_modeldb_entry_in_2", "no modeldb entry '{src}' in {name}", src=src, name=self.mod.name))
        nm = edit.NewModel(name=name, clone_from=src)
        self._apply(edit.plan_bmdb(self.mod, edit.EditRequest(unit="", new_models=[nm])),
                    f"clone model '{src}' as '{name}'")

    # -- mercenary pools ------------------------------------------------------
    @staticmethod
    def _campaign(c) -> str:
        from . import campstrat
        return str(c or campstrat.DEFAULT_CAMPAIGN)

    def _mercenaries(self, campaign=None):
        from . import mercpools
        try:
            ov = mercpools.overview(self.mod, self._campaign(campaign))
        except mercpools.MercError as e:
            raise Refused(e.message)
        return [{"name": p["name"], "regions": p["regions"],
                 "units": [dict({k: v for k, v in u.items() if k != "line"}, place=i)
                           for i, u in enumerate(p["units"], 1)]} for p in ov["pools"]]

    @staticmethod
    def _merc_values(d, *, editing: bool) -> dict:
        out = {}
        for k, v in (d or {}).items():
            k = str(k)
            if v is False and k != "crusading":
                if not editing:
                    continue
                v = None
            out[k] = v
        return out

    def _merc(self, body: dict, what: str) -> None:
        from . import mercpools
        plan = mercpools.plan(self.mod, body)
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        if not plan.text:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._apply(plan, what, lambda p: mercpools.apply(p)["record"])

    @staticmethod
    def _place(place) -> int:
        try:
            i = int(place)
        except (TypeError, ValueError):
            raise Refused(_i18n.msg("eng.luaapi.a_mercenary_unit_line_is_named", "a mercenary unit line is named by its place in the pool, from 1"))
        if i < 1:
            raise Refused(_i18n.msg("eng.luaapi.a_mercenary_unit_lines_place_counts", "a mercenary unit line's place counts from 1"))
        return i - 1

    def edit_merc_unit(self, pool, place, edits=None, campaign=None) -> None:
        c = self._campaign(campaign)
        self._merc({"campaign": c, "action": "unit_edit", "pool": str(pool), "unit": self._place(place),
                    "edits": self._merc_values(edits, editing=True)},
                   f"edit mercenary '{pool}' #{place} ({c})")

    def add_merc_unit(self, pool, values=None, campaign=None) -> None:
        c = self._campaign(campaign)
        self._merc({"campaign": c, "action": "unit_add", "pool": str(pool),
                    "values": self._merc_values(values, editing=False)},
                   f"add mercenary '{(values or {}).get('name', '')}' to '{pool}' ({c})")

    def delete_merc_unit(self, pool, place, campaign=None) -> None:
        c = self._campaign(campaign)
        self._merc({"campaign": c, "action": "unit_delete", "pool": str(pool), "unit": self._place(place)},
                   f"delete mercenary '{pool}' #{place} ({c})")

    # -- traits ---------------------------------------------------------------
    def _trait_file(self):
        from . import traits
        path = Path(self.mod.edct_path)
        return traits.parse_file(path) if path.is_file() else None

    def _traits(self):
        tf = self._trait_file()
        return [trait_view(t) for t in tf.traits] if tf else []

    def _trait(self, name):
        tf = self._trait_file()
        t = tf.get(str(name)) if tf else None
        return trait_view(t) if t else None

    def edit_trait(self, name, changes=None) -> None:
        from . import traits
        name, changes = str(name), dict(changes or {})
        tf = self._trait_file()
        if tf is None:
            raise Refused(_i18n.msg("eng.luaapi.has_no", "{name} has no {name2}", name=self.mod.name, name2=Path(self.mod.edct_path).name))
        t = tf.get(name)
        if t is None:
            raise Refused(_i18n.msg("eng.luaapi.no_trait_in", "no trait '{name}' in {name2}", name=name, name2=self.mod.name))
        head = {"characters", "hidden", "exclude_cultures", "no_going_back_level", "anti_traits"}
        unknown = set(changes) - head - {"levels"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_trait_unknown_change_s", "edit_trait: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        edits = {k: changes[k] for k in head if k in changes}
        for k in ("no_going_back_level",):
            if k in edits:
                edits[k] = _text_value(edits[k])
        if "levels" in changes:
            lv = changes["levels"] or {}
            if isinstance(lv, list):  # a Lua array: places 1..n
                lv = {i: x for i, x in enumerate(lv, 1)}
            wanted = [{} for _ in t.levels]
            fields = {"threshold", "description", "effects_description", "gain_message",
                      "lose_message", "epithet", "effects"}
            for k, w in lv.items():
                try:
                    i = int(k)
                except (TypeError, ValueError):
                    raise Refused(_i18n.msg("eng.luaapi.edit_trait_levels_are_keyed_by", "edit_trait: levels are keyed by their place, from 1"))
                if not 1 <= i <= len(t.levels):
                    raise Refused(_i18n.msg("eng.luaapi.trait_has_level_s_not_a", "trait '{name}' has {levels_n} level(s), not a level {i}", name=name, levels_n=len(t.levels), i=i))
                bad = set(w or {}) - fields
                if bad:
                    raise Refused(_i18n.msg("eng.luaapi.edit_trait_unknown_level_field_s", "edit_trait: unknown level field(s) {bad}", bad=', '.join(sorted(bad))))
                w = dict(w or {})
                for f in fields - {"effects"}:
                    if f in w:
                        w[f] = _text_value(w[f])
                if "effects" in w:
                    w["effects"] = [{"attribute": str(e.get("attribute", "")),
                                     "amount": _text_value(e.get("amount", ""))} for e in (w["effects"] or [])]
                wanted[i - 1] = w
            edits["levels"] = wanted
        plan = traits.plan(self.mod, {"trait": name, "action": "edit", "edits": edits})
        what = f"edit trait '{name}'"
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        if not getattr(plan, "text", ""):
            self.edits.append(f"{what} (nothing to change)")
            return
        self._apply(plan, what, lambda p: traits.apply(p)["record"])

    # -- ancillaries ----------------------------------------------------------
    def _anc_file(self):
        from . import ancillaries
        path = Path(self.mod.eda_path)
        return ancillaries.parse_file(path) if path.is_file() else None

    def _ancillaries(self):
        af = self._anc_file()
        return [ancillary_view(a) for a in af.ancillaries] if af else []

    def _ancillary(self, name):
        af = self._anc_file()
        a = af.get(str(name)) if af else None
        return ancillary_view(a) if a else None

    def edit_ancillary(self, name, changes=None) -> None:
        from . import ancillaries
        name, changes = str(name), dict(changes or {})
        af = self._anc_file()
        if af is None:
            raise Refused(_i18n.msg("eng.luaapi.has_no", "{name} has no {name2}", name=self.mod.name, name2=Path(self.mod.eda_path).name))
        if af.get(name) is None:
            raise Refused(_i18n.msg("eng.luaapi.no_ancillary_in", "no ancillary '{name}' in {name2}", name=name, name2=self.mod.name))
        fields = {"type", "transferable", "image", "unique", "excluded_ancillaries", "exclude_cultures",
                  "description", "effects_description", "effects"}
        unknown = set(changes) - fields
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_ancillary_unknown_change_s", "edit_ancillary: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        edits = dict(changes)
        for k in ("type", "transferable", "image", "description", "effects_description"):
            if k in edits:
                edits[k] = _text_value(edits[k])
        if "effects" in edits:
            edits["effects"] = [{"attribute": str(e.get("attribute", "")),
                                 "amount": _text_value(e.get("amount", ""))} for e in (edits["effects"] or [])]
        plan = ancillaries.plan(self.mod, {"ancillary": name, "action": "edit", "edits": edits})
        what = f"edit ancillary '{name}'"
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        if not plan.text:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._apply(plan, what, lambda p: ancillaries.apply(p)["record"])

    def edit_building(self, line, level, changes=None) -> None:
        line, level, changes = str(line), str(level), dict(changes or {})
        edb = self._edb()
        if edb is None:
            raise Refused(_i18n.msg("eng.luaapi.has_no_data_export_descr_buildings", "{name} has no data/export_descr_buildings.txt", name=self.mod.name))
        bl = edb.get(line)
        if bl is None:
            raise Refused(_i18n.msg("eng.luaapi.no_building_line_in", "no building line '{line}' in {name}", line=line, name=self.mod.name))
        if bl.level(level) is None:
            raise Refused(_i18n.msg("eng.luaapi.building_line_has_no_level", "building line '{line}' has no level '{level}'", line=line, level=level))
        known = {"settlement", "requires", "scalars", "upgrades", "capabilities", "faction_capabilities"}
        unknown = set(changes) - known
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_building_unknown_change_s", "edit_building: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        lv = {"name": level}
        for k in ("settlement", "requires"):
            if k in changes:
                lv[k] = str(changes[k])
        if "scalars" in changes:
            lv["scalars"] = {str(k): _text_value(v) for k, v in (changes["scalars"] or {}).items()}
        if "upgrades" in changes:
            lv["upgrades"] = [str(u) for u in (changes["upgrades"] or [])]
        for k in ("capabilities", "faction_capabilities"):
            if k in changes:
                ops = []
                for op in changes[k] or []:
                    if not isinstance(op, dict):
                        raise Refused(_i18n.msg("eng.luaapi.edit_building_each_of_is_a", "edit_building: each of {k} is a table", k=k))
                    o = {"keyword": str(op.get("keyword", "")), "args": str(op.get("args", "")),
                         "requires": str(op.get("requires", "")), "delete": bool(op.get("delete", False))}
                    if op.get("line") is not None:
                        cur = next((c for c in (bl.level(level).faction_capabilities if k.startswith("faction")
                                                else bl.level(level).capabilities)
                                    if c.line == int(op["line"])), None)
                        if cur is None:
                            raise Refused(_i18n.msg("eng.luaapi.no_capability_on_line", "{line}/{level}: no {kind} on line {line2} (read the building again after an edit)", line=line, level=level, kind="faction_capability" if k.startswith("faction") else "capability", line2=op['line']))
                        o["line"] = cur.line
                        for f in ("keyword", "args", "requires"):  # unchanged unless given
                            if f not in op:
                                o[f] = getattr(cur, f)
                    else:
                        o["line"] = None
                    ops.append(o)
                lv[k] = ops
        from . import buildings
        plan = buildings.plan_edit(self.mod, {"line": line, "levels": [lv]})
        if plan.errors:
            raise Refused(_i18n.msg("eng.luaapi.edit_building", "edit building '{line}/{level}': {errors}", line=line, level=level, errors='; '.join(plan.errors)))
        if not plan.edb_text and not plan.loc_text:
            self.edits.append(f"edit building '{line}/{level}' (nothing to change)")
            return
        self._apply(plan, f"edit building '{line}/{level}'", buildings.apply_edit)

    def _write(self, plan, what: str, applier: Callable) -> None:
        """An editor whose apply returns ``{record}``, and whose write the
        mod's cached reads do not see: the caches go."""
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        self._apply(plan, what, lambda p: applier(p)["record"])
        self.mod.drop_caches()

    # -- strings --------------------------------------------------------------
    def _archive(self, file):
        from . import strings
        name = str(file or "").replace("\\", "/").strip("/")
        name = name[len("text/"):] if name.startswith("text/") else name
        if not name.endswith(".strings.bin"):
            name += ".strings.bin" if name.endswith(".txt") else ".txt.strings.bin"
        try:
            return strings.resolve(self.mod, name)
        except strings.StringsError as e:
            raise Refused(str(e))

    def _strings(self, file):
        from . import stringsbin
        sb = stringsbin.read(self._archive(file))
        return [{"tag": sb.tags[i] if sb.tagged else "", "value": v} for i, v in enumerate(sb.values)]

    def _string(self, file, tag):
        from . import stringsbin
        sb = stringsbin.read(self._archive(file))
        if isinstance(tag, (int, float)) and not isinstance(tag, bool):
            i = int(tag) - 1
        else:
            i = sb.index_of(str(tag)) if sb.tagged else -1
        return sb.values[i] if 0 <= i < len(sb) else None

    def edit_strings(self, file, changes=None) -> None:
        from . import strings, stringsbin
        path = self._archive(file)
        sb = stringsbin.read(path)
        ch = changes or {}
        if isinstance(ch, list):  # a Lua array: places 1..n
            ch = {i: v for i, v in enumerate(ch, 1)}
        body = {"file": strings.rel_of(self.mod, path), "edits": [], "adds": [], "removes": []}
        for k, v in ch.items():
            pos = -1
            if not sb.tagged:
                try:
                    pos = int(k) - 1
                except (TypeError, ValueError):
                    raise Refused(_i18n.msg("eng.luaapi.untagged_by_place", "{name} has no tags: its entries are named by their place, from 1", name=path.name))
            else:
                pos = sb.index_of(str(k))
            if v is False:
                body["removes"].append(f"#{pos}" if not sb.tagged else str(k))
            elif pos >= 0 or not sb.tagged:  # a place outside the archive: the plan refuses it
                body["edits"].append({"pos": pos, "value": _text_value(v)})
            else:
                body["adds"].append({"tag": str(k), "value": _text_value(v)})
        plan = strings.plan(self.mod, body)
        what = f"edit strings '{path.name}'"
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        if not plan.data:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._apply(plan, what, strings.apply)
        self.mod.drop_caches()

    # -- the campaign: settlements and strat objects ---------------------------
    def _facts(self, campaign):
        from . import campmap, mapquery
        c = self._campaign(campaign)
        try:
            if getattr(self, "_cm", None) is None:
                self._cm = campmap.CampaignMap(self.mod)
            return mapquery.Facts(self.mod, campmap.campaign_map(self.mod, c, self._cm), c)
        except (campmap.MapError, OSError) as e:
            raise Refused(str(e))

    def _strat(self, campaign):
        from . import campstrat, campmap
        try:
            return campstrat.read_strat(self.mod, self._campaign(campaign))
        except (OSError, ValueError, campmap.MapError) as e:
            raise Refused(str(e))

    @staticmethod
    def _int_or_none(v):
        from .stratedit import is_int
        return int(str(v)) if v is not None and is_int(v) else None

    def _settlements(self, campaign=None):
        from . import stratedit
        sf = self._strat(campaign)
        out = []
        for n in sf.of_kind("settlement"):
            fac = stratedit.faction_of(sf, n)
            out.append({
                "region": str(n.get("region") or ""),
                "faction": str(fac.get("name") or fac.name) if fac else "",
                "kind": str(n.get("settlement_type") or "city"), "level": str(n.get("level") or ""),
                "population": self._int_or_none(n.get("population")),
                "year_founded": self._int_or_none(n.get("year_founded")),
                "plan_set": str(n.get("plan_set") or ""),
                "faction_creator": str(n.get("faction_creator") or ""),
                "buildings": [{"line": b.name or "", "level": str(b.get("level") or "")}
                              for b in sf.children_of(n, "building")]})
        return out

    def edit_settlement(self, region, changes=None, campaign=None) -> None:
        from . import stratedit
        region, ch = str(region), dict(changes or {})
        known = {"kind", "level", "population", "year_founded", "plan_set", "faction_creator",
                 "buildings", "owner", "place", "raw"}
        unknown = set(ch) - known
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_settlement_unknown", "edit_settlement: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        edits = {k: _text_value(ch[k]) for k in stratedit.FIELDS if k in ch}
        if "kind" in ch:
            edits["settlement_type"] = str(ch["kind"])
        body = {"campaign": self._campaign(campaign), "region": region, "edits": edits,
                "owner": str(ch.get("owner") or ""), "place": str(ch.get("place") or ""),
                "raw_block": str(ch.get("raw") or "")}
        if "buildings" in ch:
            body["buildings"] = [{"line": str(b.get("line", "")), "level": str(b.get("level", ""))}
                                 for b in (ch["buildings"] or [])]
        plan = stratedit.plan_settlement(self.mod, self._facts(campaign), body)
        what = f"edit settlement '{region}' ({body['campaign']})"
        if not plan.errors and not plan.text:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._write(plan, what, stratedit.apply_settlement)

    def _strat_objects(self, campaign=None):
        from . import stratobj
        sf = self._strat(campaign)
        out = []
        for n in stratobj.objects(sf):
            s = stratobj.read_spec(n)
            out.append({"kind": s.kind, "line": n.start + 1, "x": self._int_or_none(s.x),
                        "y": self._int_or_none(s.y), "type": s.type, "culture": s.culture,
                        "name": s.name})
        return out

    def _object(self, body: dict, campaign, what: str) -> None:
        from . import stratobj
        body = dict(body, campaign=self._campaign(campaign))
        plan = stratobj.plan(self.mod, self._facts(campaign), body)
        if not plan.errors and not plan.text:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._write(plan, what, stratobj.apply)

    _OBJ_FIELDS = {"x", "y", "type", "culture", "name", "region"}

    def edit_strat_object(self, kind, x, y, changes=None, campaign=None) -> None:
        kind, ch = str(kind).lower(), dict(changes or {})
        unknown = set(ch) - self._OBJ_FIELDS - {"delete"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_strat_object_unknown", "edit_strat_object: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        at = [int(x), int(y)]
        if ch.get("delete"):
            body = {"kind": kind, "action": "delete", "at": at}
            what = f"delete {kind} at {at[0]},{at[1]}"
        else:
            body = {"kind": kind, "action": "edit", "at": at,
                    **{k: (_text_value(v) if k in ("type", "culture", "name", "region") else v)
                       for k, v in ch.items()}}
            what = f"edit {kind} at {at[0]},{at[1]}"
        self._object(body, campaign, what)

    def add_strat_object(self, kind, values=None, campaign=None) -> None:
        kind, v = str(kind).lower(), dict(values or {})
        unknown = set(v) - self._OBJ_FIELDS
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.add_strat_object_unknown", "add_strat_object: unknown value(s) {unknown}", unknown=', '.join(sorted(unknown))))
        self._object({"kind": kind, "action": "add", **v}, campaign,
                     f"add {kind} at {v.get('x')},{v.get('y')}")

    # -- faction clones -------------------------------------------------------
    def clone_faction(self, source, new, options=None) -> None:
        from . import factionclone
        opts = dict(options or {})
        unknown = set(opts) - {"label", "art"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.clone_faction_unknown", "clone_faction: unknown option(s) {unknown}", unknown=', '.join(sorted(unknown))))
        body = {"source": str(source), "new": str(new), "label": str(opts.get("label") or ""),
                "art": opts.get("art", True) is not False}
        plan = factionclone.plan(self.mod, body)
        what = f"clone faction '{source}' as '{new}'"
        if not plan.errors and not plan.touched():
            self.edits.append(f"{what} (nothing to change)")
            return
        self._write(plan, what, factionclone.apply)

    # -- triggers -------------------------------------------------------------
    def _trigger_owner(self, file):
        """(the editor module, its file's path, the request key) for a
        trigger file named ``traits`` or ``ancillaries``."""
        from . import ancillaries, traits
        f = str(file or "").lower()
        if f in ("traits", "trait", "character_traits"):
            return traits, Path(self.mod.edct_path), "trait"
        if f in ("ancillaries", "ancillary"):
            return ancillaries, Path(self.mod.eda_path), "ancillary"
        raise Refused(_i18n.msg("eng.luaapi.trigger_file", "a trigger file is `traits` or `ancillaries`, not '{file}'", file=file))

    def _triggers(self, file):
        from . import triggers
        _, path, _ = self._trigger_owner(file)
        if not path.is_file():
            return []
        tf = triggers.parse_file(path)
        return [{"name": t.name, "when_to_test": t.when_to_test,
                 "conditions": [{"term": c.term, "args": list(c.args), "joiner": c.joiner,
                                 "negated": c.negated} for c in t.conditions],
                 "effects": [{"keyword": e.keyword, "args": list(e.args)} for e in t.effects],
                 "raw": tf.block_text(t)} for t in tf.triggers]

    def _trigger_save(self, file, req: dict, what: str) -> None:
        """A trigger edit through the traits or ancillaries editor's own save:
        both own the trigger section of their file, and a save names one of the
        file's definitions, which it leaves as it is."""
        module, path, key = self._trigger_owner(file)
        if not path.is_file():
            raise Refused(_i18n.msg("eng.luaapi.has_no", "{name} has no {name2}", name=self.mod.name, name2=path.name))
        tf = module.parse_file(path)
        first = (tf.traits if key == "trait" else tf.ancillaries)
        if not first:
            raise Refused(_i18n.msg("eng.luaapi.trigger_file_empty", "{name2} defines no trait or ancillary, so the toolkit cannot write its triggers", name2=path.name))
        plan = module.plan(self.mod, {key: first[0].name, "action": "edit", "edits": {},
                                      "triggers": req, "write_loc": False})
        if plan.errors:
            raise Refused(f"{what}: {'; '.join(plan.errors)}")
        if not plan.text:
            self.edits.append(f"{what} (nothing to change)")
            return
        self._apply(plan, what, lambda p: module.apply(p)["record"])

    @staticmethod
    def _trigger_shape(t: dict) -> dict:
        out = {}
        for k in ("name", "when_to_test"):
            if k in t:
                out[k] = _text_value(t[k])
        if "conditions" in t:
            out["conditions"] = [{"term": str(c.get("term", "")),
                                  "args": [_text_value(a) for a in (c.get("args") or [])],
                                  "joiner": str(c.get("joiner", "")), "negated": bool(c.get("negated"))}
                                 for c in (t["conditions"] or [])]
        if "effects" in t:
            out["effects"] = [{k: (str(e[k]) if k == "keyword" else [_text_value(a) for a in (e[k] or [])])
                               for k in ("keyword", "args") if k in e} for e in (t["effects"] or [])]
        return out

    def edit_trigger(self, file, name, changes=None) -> None:
        name, ch = str(name), dict(changes or {})
        unknown = set(ch) - {"name", "when_to_test", "conditions", "effects", "raw"}
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_trigger_unknown", "edit_trigger: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        e = {"name": name}
        if ch.get("raw"):
            e["raw_block"] = str(ch["raw"])
        else:
            e["trigger"] = self._trigger_shape(ch)
        self._trigger_save(file, {"edits": [e]}, f"edit trigger '{name}'")

    def add_trigger(self, file, trigger=None) -> None:
        t = self._trigger_shape(dict(trigger or {}))
        self._trigger_save(file, {"adds": [{"trigger": t}]}, f"add trigger '{t.get('name', '')}'")

    def delete_trigger(self, file, name) -> None:
        from . import triggers
        name = str(name)
        _, path, _ = self._trigger_owner(file)
        if path.is_file() and triggers.parse_file(path).get(name) is None:
            raise Refused(_i18n.msg("eng.luaapi.no_trigger", "no trigger '{name}' in {name2}", name=name, name2=path.name))
        self._trigger_save(file, {"removes": [name]}, f"delete trigger '{name}'")

    # -- the recruitment sheet ------------------------------------------------
    def _recruits(self):
        from . import edb_balance
        if self._edb() is None:
            return []
        from .sheet_ops import number

        def num(v):
            try:
                n = number(v)
            except Exception:  # noqa: BLE001 - a pool line the EDB writes oddly
                return v
            return int(n) if n.is_integer() else n
        rows = edb_balance.recruitments(edb_balance.fresh_edb(self.mod))
        return [{k: (num(r[k]) if k in ("initial", "per_turn", "maximum", "experience") else r[k])
                 for k in ("line", "unit", "building", "level", "settlement", "section",
                           "requires", "initial", "per_turn", "maximum", "experience")}
                for r in rows]

    def edit_recruit(self, line, changes=None) -> None:
        from . import edb_balance, sheet_recruit, unit_sheets
        ch = dict(changes or {})
        rid = str(int(line))
        what = f"edit recruit_pool line {rid}"
        if self._edb() is None:
            raise Refused(_i18n.msg("eng.luaapi.has_no_data_export_descr_buildings", "{name} has no data/export_descr_buildings.txt", name=self.mod.name))
        row = next((r for r in edb_balance.recruitments(edb_balance.fresh_edb(self.mod)) if r["id"] == rid), None)
        if row is None:
            raise Refused(_i18n.msg("eng.luaapi.no_recruit_line", "line {line} of the EDB is not a recruit_pool line (read recruits() again after an edit)", line=rid))
        unknown = set(ch) - set(sheet_recruit.NUMBERS)
        if unknown:
            raise Refused(_i18n.msg("eng.luaapi.edit_recruit_unknown", "edit_recruit: unknown change(s) {unknown}", unknown=', '.join(sorted(unknown))))
        try:
            fields = {k: sheet_recruit.value(k, v) for k, v in ch.items() if v != row[k]}
            if not fields:
                self.edits.append(f"{what} (nothing to change)")
                return
            project = {"recruit_draft": {rid: {"unit": row["unit"], "building": row["building"],
                                              "level": row["level"], "fields": fields}}}
            token = sheet_recruit.plan(self.mod, project)["plan_token"]

            class _Plan:  # what _apply reads off a plan
                errors, warnings = [], []
            self._apply(_Plan(), what, lambda _p: sheet_recruit.apply(self.mod, project, token))
        except unit_sheets.SheetError as e:
            raise Refused(f"{what}: {e}")
        self.mod.drop_caches()

    # -- the Lua side --------------------------------------------------------
    def table(self, session: luarun.Session):
        """The ``toolkit`` table: every API function, each converting its
        arguments from Lua and its result to frozen Lua data."""
        impl: Dict[str, Callable] = {
            "units": self._units, "unit": self._unit, "models": self._models,
            "model": self._model, "mounts": self._mounts, "factions": self._factions,
            "buildings": self._buildings, "building": self._building,
            "edit_unit": self.edit_unit, "clone_unit": self.clone_unit,
            "delete_unit": self.delete_unit,
            "edit_model": self.edit_model, "clone_model": self.clone_model,
            "edit_building": self.edit_building, "mercenaries": self._mercenaries,
            "edit_merc_unit": self.edit_merc_unit, "add_merc_unit": self.add_merc_unit,
            "delete_merc_unit": self.delete_merc_unit,
            "traits": self._traits, "trait": self._trait, "edit_trait": self.edit_trait,
            "ancillaries": self._ancillaries, "ancillary": self._ancillary,
            "edit_ancillary": self.edit_ancillary,
            "strings": self._strings, "string": self._string, "edit_strings": self.edit_strings,
            "settlements": self._settlements, "edit_settlement": self.edit_settlement,
            "strat_objects": self._strat_objects, "edit_strat_object": self.edit_strat_object,
            "add_strat_object": self.add_strat_object, "clone_faction": self.clone_faction,
            "triggers": self._triggers, "edit_trigger": self.edit_trigger,
            "add_trigger": self.add_trigger, "delete_trigger": self.delete_trigger,
            "recruits": self._recruits, "edit_recruit": self.edit_recruit,
        }

        def wrap(fn):
            def call(*args):
                try:
                    out = fn(*[session.from_lua(a) for a in args])
                except Refused as e:
                    self.refused.append(str(e))
                    raise RuntimeError(str(e)) from None
                except (KeyError, ValueError) as e:
                    raise RuntimeError(str(e).strip("'\"")) from None
                return None if out is None else session.to_lua(out)
            return call

        t = {f.name: wrap(impl[f.name]) for f in API}
        t["mod"] = {"name": self.mod.name, "root": str(self.mod.root)}
        return session.to_lua(t)


# ---------------------------------------------------------------------------
# folding the run's records into one


def _sha(p: Path) -> Optional[str]:
    try:
        return hashlib.sha1(p.read_bytes()).hexdigest()
    except OSError:
        return None


def _fold(mod: Mod, records: List[dict], script_name: str, edits: List[str],
          warnings: List[str]) -> dict:
    """One Log record for every apply in a run. Per file, the first record
    that touched it says what it was before the run: its backup, or "did not
    exist". The record's backups are copied under one new backup folder, the
    run's own records leave the Log and their folders go."""
    tid = config.new_transfer_id()
    root = config.backup_root_for(tid)
    man: Dict[str, list] = {"backed_up": [], "created": [], "deleted": [],
                            "ext_backed_up": [], "ext_created": []}
    seen_rel, seen_abs = set(), set()
    for rec in records:
        m, br = rec.get("manifest") or {}, Path(rec.get("backup_root") or "")
        # kept_existing (a transfer's "already there, left alone") restores nothing
        extra = set(m) - set(man) - {"kept_existing"}
        if extra:
            raise RuntimeError(_i18n.msg("eng.luaapi.cannot_fold_a_record_with", "cannot fold a record with {extra}", extra=', '.join(sorted(extra))))
        for rel in m.get("backed_up", []):
            if rel in seen_rel:
                continue
            seen_rel.add(rel)
            src, dst = br / "data" / rel, root / "data" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            man["backed_up"].append(rel)
        for rel in m.get("created", []):
            if rel not in seen_rel:
                seen_rel.add(rel)
                man["created"].append(rel)
        for rel in m.get("deleted", []):
            if rel not in man["deleted"]:
                man["deleted"].append(rel)
        for e in m.get("ext_backed_up", []):
            key = str(Path(e["path"]).resolve()).lower()
            if key in seen_abs:
                continue
            seen_abs.add(key)
            dst = root / "ext" / f"{len(man['ext_backed_up']):03d}_{Path(e['path']).name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(e["backup"], dst)
            man["ext_backed_up"].append({"path": e["path"], "backup": str(dst)})
        for p in m.get("ext_created", []):
            key = str(Path(p).resolve()).lower()
            if key not in seen_abs:
                seen_abs.add(key)
                man["ext_created"].append(p)
    summary = "\n".join([f"Lua script {script_name} in {mod.name}"]
                        + [f"  {e}" for e in edits] + [f"  ! {w}" for w in warnings])
    folded = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "lua", "action": "script",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": "", "resolved_type": "", "options": {"script": script_name},
        "applied": True, "undone": False, "note": "",
        "summary": summary,
        "warnings": list(warnings), "manifest": man, "backup_root": str(root),
    }
    ids = {r["id"] for r in records}
    entries = [e for e in config.load_log() if e.get("id") not in ids]
    entries.append(folded)
    config.save_log(entries)
    for r in records:
        shutil.rmtree(r.get("backup_root") or "", ignore_errors=True)
    return folded


def _changes(mod: Mod, rec: dict) -> List[FileChange]:
    """Each file the folded record covers, before (its backup) against now."""
    man, root, data = rec["manifest"], Path(rec["backup_root"]), Path(mod.data)
    pairs = []  # (label, before path or None, now path)
    for rel in man["backed_up"]:
        pairs.append((f"data/{rel}", root / "data" / rel, data / rel))
    for rel in man["created"]:
        pairs.append((f"data/{rel}", None, data / rel))
    for e in man["ext_backed_up"]:
        pairs.append((_rel(mod, e["path"]), Path(e["backup"]), Path(e["path"])))
    for p in man["ext_created"]:
        pairs.append((_rel(mod, p), None, Path(p)))
    out = []
    for label, before, now in pairs:
        if before is not None and now.is_file() and _sha(before) == _sha(now):
            continue
        status = "created" if before is None else ("changed" if now.is_file() else "deleted")
        fc = FileChange(label, status)
        a = _lines(before) if before is not None else []
        b = _lines(now) if now.is_file() else []
        if a is None or b is None:
            fc.diff = "(binary file)"
        else:
            d = list(difflib.unified_diff(a, b, f"a/{label}", f"b/{label}", lineterm="", n=2))
            fc.diff = "\n".join(d)
            fc.added = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
            fc.removed = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
        out.append(fc)
    return out


def _lines(p: Path) -> Optional[List[str]]:
    if p.name.lower().endswith(".strings.bin"):  # its entries, as the .txt beside it writes them
        from . import stringsbin
        try:
            sb = stringsbin.read(p)
        except (OSError, stringsbin.StringsBinError):
            return None
        return [stringsbin.record_text(t, v) if sb.tagged else f"#{i + 1} {v}"
                for i, (t, v) in enumerate(zip(sb.tags if sb.tagged else [""] * len(sb), sb.values))]
    data = p.read_bytes()
    if b"\0" in data[:4096] and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return None
    for enc in ("utf-16", "utf-8") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8", "latin-1"):
        try:
            return data.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return None


def _drop(rec_ids) -> None:
    ids = set(rec_ids)
    config.save_log([e for e in config.load_log() if e.get("id") not in ids])


def _take_back(records: List[dict]) -> None:
    """Undo a run's applies, newest first, and leave nothing in the Log."""
    for r in reversed(records):
        try:
            transfer.undo(r["id"])
        except Exception as e:  # noqa: BLE001 - keep putting back the rest
            log.warning("LUA    could not undo %s: %s", r.get("id"), e)
    _drop([r["id"] for r in records])
    for r in records:
        shutil.rmtree(r.get("backup_root") or "", ignore_errors=True)


def run(mod: Mod, script: Path, *, apply: bool = False, args: Optional[Dict[str, str]] = None,
        time_limit: float = luarun.TIME_LIMIT, on_print: Optional[Callable[[str], None]] = None) -> Report:
    """Run ``script`` against ``mod``: a preview, or with ``apply`` a write
    that leaves one Log record."""
    script = Path(script)
    rep = Report(script=script.name, mod=mod.name, applied=False)
    started = time.monotonic()
    r = Run(mod, script_name=script.name)
    try:
        session = luarun.Session(script.parent, time_limit=time_limit, on_print=on_print)
    except luarun.ScriptError as e:
        rep.error, rep.error_kind = e.message, e.kind
        return rep
    session.set_global("toolkit", r.table(session))
    session.set_global("args", session.to_lua({str(k): str(v) for k, v in (args or {}).items()}))
    try:
        res = session.run(script.read_text(encoding="utf-8-sig"), script.name)
        rep.printed = res.printed
    except luarun.ScriptError as e:
        rep.printed = list(session.printed)
        rep.error, rep.error_kind = e.message, e.kind
        if e.kind == "error" and any(x in e.message for x in r.refused):
            rep.error_kind = "refused"
        _take_back(r.records)
        rep.edits, rep.warnings = r.edits, r.warnings
        rep.seconds = time.monotonic() - started
        return rep
    rep.edits, rep.warnings = r.edits, r.warnings
    rep.ok = True
    if r.records:
        folded = _fold(mod, r.records, script.name, r.edits, r.warnings)
        rep.files = _changes(mod, folded)
        if apply:
            rep.applied, rep.log_id = True, folded["id"]
        else:
            transfer.undo(folded["id"])
            left = _not_put_back(mod, folded)
            _drop([folded["id"]])
            if left:  # keep the backups: they are the only copy of those files now
                rep.warnings.append(_i18n.msg("eng.luaapi.the_preview_could_not_put_back", "the preview could not put back {left}; their backups are in {backup_root}", left=', '.join(left), backup_root=folded['backup_root']))
            else:
                shutil.rmtree(folded["backup_root"], ignore_errors=True)
        mod.drop_caches()
    rep.seconds = time.monotonic() - started
    return rep


def _not_put_back(mod: Mod, rec: dict) -> List[str]:
    """After a preview's undo: every file the run touched must be its backup's
    bytes again, and every file it created gone."""
    man, root, data = rec["manifest"], Path(rec["backup_root"]), Path(mod.data)
    bad = [f"data/{rel}" for rel in man["backed_up"]
           if _sha(root / "data" / rel) != _sha(data / rel)]
    bad += [f"data/{rel}" for rel in man["created"] if (data / rel).exists()]
    bad += [e["path"] for e in man["ext_backed_up"] if _sha(Path(e["backup"])) != _sha(Path(e["path"]))]
    bad += [p for p in man["ext_created"] if Path(p).exists()]
    return bad


def undo(log_id: str) -> dict:
    """The Log's Undo, for a run's record (or any record)."""
    return transfer.undo(log_id)


# ---------------------------------------------------------------------------
# the app's Lua tab (Phase 125): scripts kept in config/lua_scripts, a run's
# report as JSON. The same run as the CLI's.

#: one run at a time from the app: two runs on one mod would undo each other's files
_APP_LOCK = __import__("threading").Lock()


def scripts_dir() -> Path:
    return Path(config.CONFIG_DIR) / "lua_scripts"


def _script_name(name: str) -> str:
    import re
    stem = re.sub(r"[^\w.-]+", "_", Path(str(name or "")).stem).strip("._") or "script"
    return stem + ".lua"


def script_list() -> dict:
    """The saved scripts, the shipped examples and the API, for the tab."""
    mine = sorted(scripts_dir().glob("*.lua")) if scripts_dir().is_dir() else []
    ex_dir = Path(config.PROJECT_ROOT) / "docs" / "lua_examples"
    examples = sorted(ex_dir.glob("*.lua")) if ex_dir.is_dir() else []
    return {
        "available": luarun.available(),
        "scripts": [{"name": p.name, "text": p.read_text(encoding="utf-8-sig")} for p in mine],
        "examples": [{"name": p.name, "text": p.read_text(encoding="utf-8-sig")} for p in examples],
        "api": [{"name": f.name, "params": [p[0] for p in f.params], "returns": f.returns,
                 "doc": f.doc, "kind": f.kind} for f in API],
    }


def save_script(name: str, text: str) -> Path:
    d = scripts_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / _script_name(name)
    p.write_text(str(text or ""), encoding="utf-8")
    return p


def app_run(mod: Mod, name: str, text: str, *, apply: bool = False,
            args: Optional[Dict[str, str]] = None) -> dict:
    """Save the script, run it (a preview, or written with ``apply``) and give
    the report as JSON."""
    path = save_script(name, text)
    if not _APP_LOCK.acquire(blocking=False):
        return {"ok": False, "error_kind": "busy",
                "error": _i18n.msg("eng.luaapi.a_run_is_going", "another script is running; wait for it to end")}
    try:
        rep = run(mod, path, apply=apply, args={str(k): str(v) for k, v in (args or {}).items()})
    finally:
        _APP_LOCK.release()
    return {"name": path.name, "ok": rep.ok, "applied": rep.applied, "error": rep.error,
            "error_kind": rep.error_kind, "printed": rep.printed, "edits": rep.edits,
            "warnings": rep.warnings, "log_id": rep.log_id, "seconds": round(rep.seconds, 2),
            "files": [{"rel": f.rel, "status": f.status, "added": f.added, "removed": f.removed,
                       "diff": f.diff} for f in rep.files]}
