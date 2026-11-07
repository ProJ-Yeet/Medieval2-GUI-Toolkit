"""Read-only joins for the Models Editor's faction and character cards.

Slot position is the character level. Comments label slots; only EDCT effects
explain how a character reaches them. All edits use the existing writers.
"""
from pathlib import Path
import re

from . import characters, traits, triggers, campstrat, stratchar, factions, stratmap
from . import keyblock as kb, i18n as _i18n


def _path(mod, rel):
    path = Path(mod.data) / rel
    return mod.game_or(path) if hasattr(mod, "game_or") else path


def _doc(mod):
    path = _path(mod, characters.REL)
    return characters.parse(kb.read_text(path, "latin-1")) if path.is_file() else characters.parse("")


def levels_of(mod):
    """Character type -> integer level -> trait names, preserving EDCT order."""
    path = _path(mod, "export_descr_character_traits.txt")
    out = {}
    if not path.is_file():
        return out
    for trait in traits.parse_file(path).traits:
        kinds = ["named character" if c.lower() == "family" else c.lower()
                 for c in trait.characters]
        for level in trait.levels:
            for effect in level.effects:
                if effect.attribute.lower() != "level":
                    continue
                try:
                    n = int(effect.amount)
                except ValueError:
                    continue
                for kind in kinds:
                    if kind == "general":  # Captains do not receive traits.
                        continue
                    names = out.setdefault(kind, {}).setdefault(n, [])
                    if trait.name not in names:
                        names.append(trait.name)
    # The traits every faction's heir or leader gets go first, since a level
    # can have dozens (DaC: 22 at level 3) and the page shows the first few.
    # They are named Factionheir / Factionleader in vanilla, DaC and the
    # TWCenter levels tutorial (DaC gives them from EOP Lua, so no trigger
    # says so), or a BecomesFactionHeir / BecomesFactionLeader trigger gives them.
    first = {"factionheir", "factionleader"}
    for trig in triggers.parse_file(path).triggers:
        if trig.when_to_test in ("BecomesFactionHeir", "BecomesFactionLeader"):
            first |= {e.args[0].lower() for e in trig.effects
                      if e.keyword.lower() == "affects" and e.args}
    for by_level in out.values():
        for names in by_level.values():
            names.sort(key=lambda t: t.lower() not in first)
    return out


def strat_characters(mod, name):
    levels = levels_of(mod)
    return [dict(u, level=u["slot"], traits=levels.get(u["type"].lower(), {}).get(u["slot"], []))
            for u in characters.model_users(_doc(mod)).get((name or "").lower(), [])]


def _people(mod, faction=""):
    out = []
    for campaign in campstrat.campaign_paths(mod):
        sf = campstrat.read_strat(mod, campaign)
        for fac in sf.of_kind("faction"):
            if faction and fac.name.lower() != faction.lower():
                continue
            for node in stratchar.characters_of(sf, fac):
                if str(node.get("type") or "").lower() != "named character":
                    continue
                rank = str(node.get("rank") or "")
                model = str(node.get("battle_model") or "")
                if rank in ("leader", "heir") or model:
                    out.append({"campaign": campaign, "faction": fac.name, "name": node.name,
                                "line": node.start + 1, "rank": rank, "battle_model": model})
    return out


_CHANGE = re.compile(r"^change_battle_model\s+(\S+)\s+(leader|heir)\s+(\S+)\s*$", re.I)


def _scripts(mod, faction=""):
    out = []
    base = Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
    if not base.is_dir():
        return out
    for path in sorted(base.rglob("campaign_script.txt")):
        for i, raw in enumerate(kb.read_text(path, "latin-1").splitlines()):
            code = raw.strip()
            commented = code.startswith(";")
            if commented:
                code = code[1:].lstrip()
            code = code.partition(";")[0].rstrip()
            match = _CHANGE.fullmatch(code)
            if not match:
                continue
            fac, who, model = match.groups()
            if faction and fac.lower() != faction.lower():
                continue
            out.append({"rel": path.relative_to(mod.data).as_posix(), "line": i + 1,
                        "faction": fac, "who": who.lower(), "model": model,
                        "commented": commented})
    return out


def _battle(row, entries):
    entry = entries.get(row.value.lower())
    return {"line": row.line + 1, "value": row.value, "exists": entry is not None,
            "horse": bool(entry and any(a.mount_type.lower() == "horse" for a in entry.animations))}


def faction_models(mod, faction=""):
    """One faction's owned lines, or the descr_character faction roster."""
    doc = _doc(mod)
    roster = sorted({f for s in doc.sections for b in s.blocks for f in b.factions})
    out = {"roster": roster, "sig": characters._sig(doc.text)}
    if not faction:
        return out
    faction = next((f for f in roster if f.lower() == faction.lower()), faction)
    levels = levels_of(mod)
    entries = mod.modeldb.by_name()
    out.update(faction=faction, named=[], captain=[], agents=[], findings=[],
               characters=_people(mod, faction), scripts=_scripts(mod, faction), symbols={},
               strat_textures=[], battle_models=sorted(entries), strat_models=[])
    for sec in doc.sections:
        for block in sec.blocks:
            if faction.lower() not in [f.lower() for f in block.factions]:
                continue
            slots = [{"line": row.line + 1, "level": n, "model": row.value,
                      "comment": row.label, "traits": levels.get(sec.name.lower(), {}).get(n, [])}
                     for n, row in enumerate(r for r in block.rows if r.key == "strat_model")]
            item = {"type": sec.name, "line": block.line + 1, "factions": block.factions, "slots": slots}
            battles = [r for r in block.rows if r.key == "battle_model"]
            if battles:
                item["battle_model"] = _battle(battles[0], entries)
            if sec.name.lower() == "general":
                if slots:
                    item["strat_model"] = {"line": slots[0]["line"], "value": slots[0]["model"]}
                out["captain"].append(item)
            elif sec.name.lower() == "named character":
                out["named"].append(item)
            else:
                out["agents"].append(item)
            for slot in slots:
                if slot["level"] > 0 and not slot["traits"]:
                    out["findings"].append({"code": "level", "severity": "note", "line": slot["line"],
                        "message": _i18n.msg("eng.charmodels.unreached", "{type} level {level}: no trait of this character type gives this level", type=sec.name, level=slot["level"])})
            if sec.name.lower() in characters.FIGHTERS and battles:
                battle = item["battle_model"]
                if not battle["exists"]:
                    out["findings"].append({"code": "battle", "severity": "warn", "line": battle["line"],
                        "message": _i18n.msg("eng.charmodels.missing", "{model} is not a modeldb entry", model=battle["value"])})
                elif not battle["horse"]:
                    out["findings"].append({"code": "horse", "severity": "warn", "line": battle["line"],
                        "message": _i18n.msg("eng.charmodels.horse", "{model} has no horse animation; generals and captains use the same model on foot and mounted", model=battle["value"])})
    path = _path(mod, "descr_sm_factions.txt")
    if path.is_file():
        for record in factions.parse_file(path).records:
            if factions.slot_of(record.name).lower() == faction.lower():
                out["symbols"] = {key: record.get(key) for key in ("symbol", "rebel_symbol") if record.get(key)}
    sf = stratmap.strat_file(mod)
    out["strat_models"] = sorted({e.name for e in sf.entries})
    out["strat_textures"] = sorted({e.name for e in sf.entries if faction.lower() in [f.lower() for f in e.factions]})
    return out


def entry_characters(mod, name):
    """Every battle-model use, including inactive script lines marked as such."""
    out = []
    name = (name or "").lower()
    for sec in _doc(mod).sections:
        for block in sec.blocks:
            for row in block.rows:
                if row.key == "battle_model" and row.value.lower() == name:
                    for faction in block.factions:
                        out.append({"source": "descr_character", "type": sec.name, "faction": faction,
                                    "line": row.line + 1, "key": characters._key(sec, block),
                                    "role": "captain" if sec.name.lower() == "general" else "generals"})
    out.extend(dict(c, source="descr_strat", role=c["rank"] or "general")
               for c in _people(mod) if c["battle_model"].lower() == name)
    out.extend(dict(s, source="campaign_script", role=s["who"])
               for s in _scripts(mod) if s["model"].lower() == name)
    return out
