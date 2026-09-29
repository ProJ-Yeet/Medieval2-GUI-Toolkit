"""``descr_hero_abilities.xml`` - a named character's battle ability (Phase 66).

A character line in ``descr_strat.txt`` (or a ``spawn_army`` in a campaign
script, or a ``descr_battle.txt``) ends ``hero_ability The_Heart_of_the_Lion``,
and this file says what that is: how long it lasts, how often it can be used,
its button and tooltip, its sound, and its effects on the armies in the field.
The people panel (Phase 16) wrote the name and had no list to offer - its own
comment said the names were "in descr_strat.txt and nowhere else" - so the
picker now offers what this file declares, and a character naming something
it does not declare is a warning there as well as here.

**The shape**, from the file's own documented ``Sample_Ability``: an ability
is ``name``, ``duration`` (seconds, 0 is instant), ``activations`` (default 1),
``cooldown``, three tooltip labels (``text/expanded.txt`` keys), three sprites
(``ui/battle.sd``), ``sound_effect`` (an ``event`` in
``descr_sounds_generic.txt``) and ``hero_ability_effects``. The six effects the
sample documents, each with a ``target`` (enemy_armies, own_army,
allied_armies), and a seventh measured in ROCSS: ``projectile``, whose only
field is ``projectile_name`` (the ``Super_Banana_Bomb``).

**Measured on both installed mods before any rule was written** (ROCSS 7
abilities, DaC 32; DaC's 1,187 lines hold 26 tags, ROCSS's add
``projectile_name``):

* Every ``hero_ability`` a character names, in every campaign and battle of
  both mods (99 lines in DaC's main ``descr_strat.txt`` alone), is declared.
  A name that is not is the warning that matters.
* ROCSS's ``The_Heart_of_the_Lion`` has ``<selected_sprite>`` twice: a
  warning, since only one of the two can be the button.
* Both mods give ``army_morale`` a ``permanent`` (ROCSS's Heart of the Lion,
  DaC's NUMENOR), which the sample documents only for ``army_fatigue``, and
  ROCSS has a ``kill_chance_modifier`` of -0.5, below the 0 the sample calls
  "no chance to kill": notes, since both mods play.
* ROCSS's ``Sample_Ability`` and ``Super_Banana_Bomb`` name
  ``EMT_HERO_SPECIAL_ABILITY_DEFAULT_*`` labels its ``expanded.txt`` lacks;
  neither ability is given to anyone, so a missing label is a note there and
  a warning on an ability a character carries.
* DaC ships ``ui/battle.sd`` and every one of its 84 sprite names is in it;
  ROCSS ships none (the base game's is read), so the rule only runs when the
  mod has the file. Every ``sound_effect`` in both is an ``event`` in the
  mod's own ``descr_sounds_generic.txt``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import leafxml as lx
from . import i18n as _i18n

REL = "descr_hero_abilities.xml"
ROOT_TAG = "root"
LIST_TAG = "hero_abilities"
ITEM_TAG = "hero_ability"
EFFECTS_TAG = "hero_ability_effects"
EFFECT_TAG = "hero_ability_effect"

LABELS = ("normal_tooltip_label", "selected_tooltip_label", "disabled_tooltip_label")
SPRITES = ("normal_sprite", "selected_sprite", "disabled_sprite")
ABILITY_FIELDS = ("name", "duration", "activations", "cooldown") + LABELS + SPRITES \
    + ("sound_effect",)
#: effect -> its fields after `name`, from the sample (and ROCSS for projectile)
EFFECTS: Dict[str, Tuple[str, ...]] = {
    "lock_morale": ("target", "morale_level"),
    "rally_units": ("target", "morale_level", "min_time_before_rout"),
    "army_morale": ("target", "morale_modifier"),
    "army_fatigue": ("target", "fatigue_modifier", "permanent"),
    "soldier_combat_effectiveness": ("target", "kill_chance_modifier"),
    "unit_infighting": ("target", "percentage_chance", "min_effect_time", "max_effect_time"),
    "projectile": ("projectile_name",),
}
TARGETS = ("enemy_armies", "own_army", "allied_armies")
MORALE_LEVELS = ("impetuous", "high", "firm", "shaken", "wavering")
NUMBERS = ("duration", "activations", "cooldown", "morale_modifier", "fatigue_modifier",
           "kill_chance_modifier", "percentage_chance", "min_effect_time", "max_effect_time",
           "min_time_before_rout")
#: what a hero_ability token may be on a descr_strat line
NAME = re.compile(r"[^\s,;<>&]+")
_USE = re.compile(r"hero_ability\s+([^\s,;]+)", re.I)
_CHAR = re.compile(r"character\s+([^,]+),", re.I)

finding = lx.finding


class HeroError(lx.LeafError):
    pass


def parse(text: str) -> lx.Doc:
    return lx.parse(text, ROOT_TAG)


def _items(doc: lx.Doc) -> List[lx.Node]:
    return [n for n in doc.find(ITEM_TAG) if n.parent >= 0 and doc.nodes[n.parent].tag == LIST_TAG]


def abilities(doc: lx.Doc) -> List[Dict]:
    """Every ability, with its fields and its effects, in file order."""
    out = []
    for a in _items(doc):
        box = doc.child(a, EFFECTS_TAG)
        effects = []
        for e in doc.kids(box, EFFECT_TAG) if box is not None else []:
            effects.append({"id": e.id, "name": doc.field(e, "name"), "line": e.line + 1,
                            "fields": lx.leaves(doc, e)})
        out.append({"id": a.id, "name": doc.field(a, "name"), "line": a.line + 1,
                    "fields": lx.leaves(doc, a, stop=(EFFECTS_TAG,)),
                    "effects_id": box.id if box is not None else None, "effects": effects})
    return out


def declared(mod) -> List[str]:
    """Every ability name the mod declares, as written - for the people
    panel's picker. Empty when the file is not there or cannot be read."""
    try:
        return [a["name"] for a in abilities(parse(lx.read(mod, REL))) if a["name"]]
    except (lx.LeafError, OSError):
        return []


# ---------------------------------------------------------------------------
# what the ability names, and who names the ability


def uses(data: Path) -> Dict[str, List[Dict]]:
    """``lower name -> [{file, line, who}]`` for every ``hero_ability`` a
    campaign or battle file under ``world/maps`` gives a character."""
    out: Dict[str, List[Dict]] = {}
    root = data / "world" / "maps"
    if not root.is_dir():
        return out
    for f in sorted(root.rglob("*.txt")):
        try:
            text = f.read_text(encoding="latin-1")
        except OSError:
            continue
        if "hero_ability" not in text:
            continue
        rel = f.relative_to(data).as_posix()
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split(";", 1)[0]
            for m in _USE.finditer(code):
                who = _CHAR.search(code)
                out.setdefault(m.group(1).lower(), []).append(
                    {"file": rel, "line": i, "who": who.group(1).strip() if who else "",
                     "name": m.group(1)})
    return out


def _text_keys(mod) -> Optional[Set[str]]:
    from . import namekeys
    try:
        pairs = namekeys.loc_pairs(mod, "text/expanded.txt")
    except Exception:
        return None
    return {k.upper() for k in pairs} if pairs else None


def _sprites(data: Path) -> Optional[bytes]:
    p = data / "ui" / "battle.sd"
    try:
        return p.read_bytes().lower() if p.is_file() else None
    except OSError:
        return None


def _sound_events(data: Path) -> Optional[Set[str]]:
    p = data / "descr_sounds_generic.txt"
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="latin-1")
    except OSError:
        return None
    return {m.lower() for m in re.findall(r"^[ \t]*event[ \t]+(\S+)", text, re.M)}


def _projectiles(data: Path) -> Optional[Set[str]]:
    p = data / "descr_projectile.txt"
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="latin-1")
    except OSError:
        return None
    return {m.lower() for m in re.findall(r"^[ \t]*projectile[ \t]+(\S+)", text, re.M)}


class Refs:
    """What the checks hold an ability against. ``None`` on any of them means
    the mod does not ship that file, and the rule is not run."""

    def __init__(self, uses=None, text_keys=None, sprites=None, sounds=None, projectiles=None):
        self.uses: Dict[str, List[Dict]] = uses or {}
        self.text_keys: Optional[Set[str]] = text_keys
        self.sprites: Optional[bytes] = sprites
        self.sounds: Optional[Set[str]] = sounds
        self.projectiles: Optional[Set[str]] = projectiles

    @classmethod
    def of(cls, mod) -> "Refs":
        data = Path(mod.data)
        return cls(uses(data), _text_keys(mod), _sprites(data), _sound_events(data),
                   _projectiles(data))


# ---------------------------------------------------------------------------
# checking


def _num(doc: lx.Doc, n: lx.Node, key: str, owner: str, out: List[Dict]) -> Optional[float]:
    v = doc.value(n)
    if not lx.NUM.fullmatch(v):
        out.append(finding("number", "fatal", _i18n.msg("eng.heroabilities.is_not_a_number", "{owner}: <{tag}> is {x}, not a number", owner=owner, tag=n.tag, x=v or '(blank)'), key, n.line))
        return None
    return float(v)


def check(doc: lx.Doc, refs: Optional[Refs] = None) -> List[Dict]:
    refs = refs or Refs()
    out = lx.xml_findings(doc)
    items = _items(doc)
    if not items and not doc.errors:
        out.append(finding("empty", "warn", _i18n.msg("eng.heroabilities.no_under", "no <{ITEM_TAG}> under <{LIST_TAG}>", ITEM_TAG=ITEM_TAG, LIST_TAG=LIST_TAG), "file", 0))
    seen: Dict[str, int] = {}
    for a in items:
        key = f"ability/{a.id}"
        name = doc.field(a, "name")
        used = bool(name) and name.lower() in refs.uses
        owner = name or f"the ability on line {a.line + 1}"
        if not name:
            out.append(finding("name", "fatal", _i18n.msg("eng.heroabilities.line_an_ability_with_no_so", "line {x}: an ability with no <name>, so no character can be given it", x=a.line + 1), key, a.line))
        elif name.lower() in seen:
            out.append(finding("duplicate", "warn", _i18n.msg("eng.heroabilities.is_declared_twice_lines_and", "{name} is declared twice (lines {seen} and {x})", name=name, seen=seen[name.lower()], x=a.line + 1), key, a.line))
        elif not NAME.fullmatch(name):
            out.append(finding("name", "warn", _i18n.msg("eng.heroabilities.has_a_space_or_a_comma", "{name} has a space or a comma in it, and a descr_strat.txt line cannot name it", name=repr(name)), key, a.line))
        if name:
            seen.setdefault(name.lower(), a.line + 1)
        tags: Dict[str, List[int]] = {}
        for c in doc.kids(a):
            tags.setdefault(c.tag, []).append(c.line + 1)
        for tag, lines in tags.items():
            if len(lines) > 1 and tag != EFFECTS_TAG:
                out.append(finding("twice", "warn", _i18n.msg("eng.heroabilities.has_times_lines_the_game_uses", "{owner} has <{tag}> {lines_n} times (lines {map}); the game uses one of them", owner=owner, tag=tag, lines_n=len(lines), map=', '.join(map(str, lines))), key, a.line))
            if tag not in ABILITY_FIELDS and tag != EFFECTS_TAG:
                out.append(finding("field", "note", _i18n.msg("eng.heroabilities.is_not_a_field_the_files", "{owner}: <{tag}> is not a field the file's own sample documents", owner=owner, tag=tag), key, lines[0] - 1))
        vals: Dict[str, float] = {}
        for c in doc.kids(a):
            if c.tag in NUMBERS and doc.is_leaf(c):
                v = _num(doc, c, key, owner, out)
                if v is not None:
                    vals[c.tag] = v
        if "activations" in vals and (vals["activations"] < 1
                                      or not lx.INT.fullmatch(doc.field(a, "activations"))):
            out.append(finding("activations", "warn", _i18n.msg("eng.heroabilities.activations_is_and_it_is_a", "{owner}: activations is {field}, and it is a count of one or more", owner=owner, field=doc.field(a, 'activations')), key, a.line))
        for t in ("duration", "cooldown"):
            if vals.get(t, 0) < 0:
                out.append(finding("negative", "warn", _i18n.msg("eng.heroabilities.is_below_zero", "{owner}: {t} is below zero", owner=owner, t=t), key, a.line))
        sev = "warn" if used else "note"
        why = "" if used else "; no character is given it"
        if refs.text_keys is not None:
            gone = [doc.field(a, t) for t in LABELS
                    if doc.field(a, t) and doc.field(a, t).upper() not in refs.text_keys]
            if gone:
                out.append(finding("label", sev, _i18n.msg("eng.heroabilities.tooltip_label_s_not_in_text", "{owner}: {gone_n} tooltip label(s) not in text/expanded.txt ({gone}), so the button's tooltip has no text{why}", owner=owner, gone_n=len(gone), gone=', '.join(gone), why=why), key, a.line))
        if refs.sprites is not None:
            gone = [doc.field(a, t) for t in SPRITES
                    if doc.field(a, t) and doc.field(a, t).lower().encode("latin-1") not in refs.sprites]
            if gone:
                out.append(finding("sprite", sev, _i18n.msg("eng.heroabilities.not_in_ui_battle_sd_so", "{owner}: {gone} not in ui/battle.sd, so the button has no picture{why}", owner=owner, gone=', '.join(gone), why=why), key, a.line))
        snd = doc.field(a, "sound_effect")
        if refs.sounds is not None and snd and snd.lower() not in refs.sounds:
            out.append(finding("sound", sev, _i18n.msg("eng.heroabilities.sound_effect_is_not_an_event", "{owner}: sound_effect {snd} is not an event in descr_sounds_generic.txt{why}", owner=owner, snd=snd, why=why), key, a.line))
        box = doc.child(a, EFFECTS_TAG)
        effects = doc.kids(box, EFFECT_TAG) if box is not None else []
        if not effects:
            out.append(finding("no_effects", "warn", _i18n.msg("eng.heroabilities.has_no_effects_so_using_it", "{owner} has no effects, so using it does nothing", owner=owner), key, a.line))
        for e in effects:
            _check_effect(doc, e, owner, key, refs, out)
    for low, where in refs.uses.items():
        if low in seen:
            continue
        first = where[0]
        places = ", ".join(sorted({w["file"].rsplit("/", 2)[-2] for w in where})[:3])
        # i18n-ok: x2 is an ellipsis for more places, not a plural
        out.append(finding("undeclared", "warn", _i18n.msg("eng.heroabilities.character_line_s_name_hero_ability", "{where_n} character line(s) name hero_ability {name} ({x} in {file}{x2}; {places}), and {REL} declares no ability called that", where_n=len(where), name=first['name'], x=first['who'] or 'line ' + str(first['line']), file=first['file'], x2='...' if len(where) > 1 else '', places=places, REL=REL), f"use/{first['name']}", 0))
    return out


def _check_effect(doc: lx.Doc, e: lx.Node, owner: str, key: str, refs: Refs,
                  out: List[Dict]) -> None:
    ename = doc.field(e, "name")
    where = f"{owner}, {ename or 'an effect'} (line {e.line + 1})"
    if not ename:
        out.append(finding("effect", "fatal", _i18n.msg("eng.heroabilities.an_effect_with_no", "{where}: an effect with no <name>", where=where), key, e.line))
        return
    if ename not in EFFECTS:
        out.append(finding("effect", "warn", _i18n.msg("eng.heroabilities.is_not_one_of_the_effects", "{where}: {ename} is not one of the {EFFECTS_n} effects ({EFFECTS})", where=where, ename=ename, EFFECTS_n=len(EFFECTS), EFFECTS=', '.join(EFFECTS)), key, e.line))
        return
    known = EFFECTS[ename]
    for c in doc.kids(e):
        if c.tag == "name":
            continue
        if c.tag not in known:
            out.append(finding("effect_field", "note", _i18n.msg("eng.heroabilities.is_not_one_of_s_fields", "{where}: <{tag}> is not one of {ename}'s fields ({known})", where=where, tag=c.tag, ename=ename, known=', '.join(known)), key, c.line))
            continue
        v = doc.value(c)
        if c.tag in NUMBERS:
            _num(doc, c, key, where, out)
        elif c.tag == "target" and v not in TARGETS:
            out.append(finding("target", "warn", _i18n.msg("eng.heroabilities.target_is_not", "{where}: target {x} is not {TARGETS}", where=where, x=v or '(blank)', TARGETS=', '.join(TARGETS)), key, c.line))
        elif c.tag == "morale_level" and v not in MORALE_LEVELS:
            out.append(finding("morale", "warn", _i18n.msg("eng.heroabilities.morale_level_is_not", "{where}: morale_level {x} is not {MORALE_LEVELS}", where=where, x=v or '(blank)', MORALE_LEVELS=', '.join(MORALE_LEVELS)), key, c.line))
        elif c.tag == "permanent" and v not in ("true", "false"):
            out.append(finding("bool", "warn", _i18n.msg("eng.heroabilities.permanent_is_not_true_or_false", "{where}: permanent is {x}, not true or false", where=where, x=v or '(blank)'), key, c.line))
        elif c.tag == "projectile_name" and refs.projectiles is not None \
                and v.lower() not in refs.projectiles:
            out.append(finding("projectile", "warn", _i18n.msg("eng.heroabilities.is_not_a_projectile_descr_projectile", "{where}: {v} is not a projectile descr_projectile.txt declares", where=where, v=v), key, c.line))
    if "target" in known and doc.child(e, "target") is None:
        out.append(finding("target", "warn", _i18n.msg("eng.heroabilities.no_so_it_is_not_said", "{where}: no <target>, so it is not said which army it works on", where=where), key, e.line))
    kc = doc.field(e, "kill_chance_modifier")
    if lx.NUM.fullmatch(kc) and float(kc) < 0:
        out.append(finding("kill_chance", "note", _i18n.msg("eng.heroabilities.kill_chance_modifier_is_below_0", "{where}: kill_chance_modifier {kc} is below 0, which the sample already calls no chance to kill", where=where, kc=kc), key, e.line))
    pc = doc.field(e, "percentage_chance")
    if lx.NUM.fullmatch(pc) and not 0 <= float(pc) <= 100:
        out.append(finding("percent", "warn", _i18n.msg("eng.heroabilities.percentage_chance_is_outside_0_100", "{where}: percentage_chance {pc} is outside 0-100", where=where, pc=pc), key, e.line))
    lo, hi = doc.field(e, "min_effect_time"), doc.field(e, "max_effect_time")
    if lx.NUM.fullmatch(lo) and lx.NUM.fullmatch(hi) and float(lo) > float(hi):
        out.append(finding("range", "warn", _i18n.msg("eng.heroabilities.min_effect_time_is_above_max", "{where}: min_effect_time {lo} is above max_effect_time {hi}", where=where, lo=lo, hi=hi), key, e.line))


# ---------------------------------------------------------------------------
# reading a mod


def overview(mod) -> Dict:
    out: Dict = {"file": REL, "abilities": [], "findings": [], "effects": EFFECTS,
                 "ability_fields": ABILITY_FIELDS, "targets": TARGETS,
                 "morale_levels": MORALE_LEVELS}
    try:
        text = lx.read(mod, REL)
    except lx.LeafError as e:
        out["error"] = e.message
        return out
    doc = parse(text)
    refs = Refs.of(mod)
    out["abilities"] = abilities(doc)
    #: label -> its text, or None when expanded.txt lacks it; empty when the
    #: mod has no expanded.txt to hold them against
    labels: Dict[str, Optional[str]] = {}
    tk: Dict[str, str] = {}
    if refs.text_keys is not None:
        from . import namekeys
        try:
            tk = {k.upper(): v for k, v in namekeys.loc_pairs(mod, "text/expanded.txt").items()}
        except Exception:
            tk = {}
    for a in out["abilities"]:
        a["used"] = refs.uses.get(a["name"].lower(), [])[:50]
        a["used_count"] = len(refs.uses.get(a["name"].lower(), []))
        for f in a["fields"]:
            if f["tag"] in LABELS and f["value"] and tk:
                labels[f["value"]] = tk.get(f["value"].upper())
    out["labels"] = labels
    out["have"] = {"text": refs.text_keys is not None, "battle_sd": refs.sprites is not None,
                   "sounds": refs.sounds is not None, "projectiles": refs.projectiles is not None}
    out["sig"] = lx.sig(text)
    out["findings"] = check(doc, refs)
    return out


# ---------------------------------------------------------------------------
# editing


def _check_value(doc: lx.Doc, n: lx.Node, v: str) -> str:
    par = doc.nodes[n.parent] if n.parent >= 0 else None
    in_effect = par is not None and par.tag == EFFECT_TAG
    if n.tag == "name":
        if in_effect:
            return "" if v in EFFECTS else f"{v!r} is not one of the effects ({', '.join(EFFECTS)})"
        return "" if NAME.fullmatch(v) else \
            f"{v!r} cannot be an ability's name: it needs to be one word, with no comma"
    if n.tag in NUMBERS:
        if not lx.NUM.fullmatch(v):
            return f"{n.tag} is a number, not {v!r}"
        if n.tag == "activations" and (not lx.INT.fullmatch(v) or int(v) < 1):
            return "activations is a count of one or more"
        return ""
    if n.tag == "target" and v not in TARGETS:
        return f"target is one of {', '.join(TARGETS)}"
    if n.tag == "morale_level" and v not in MORALE_LEVELS:
        return f"morale_level is one of {', '.join(MORALE_LEVELS)}"
    if n.tag == "permanent" and v not in ("true", "false"):
        return "permanent is true or false"
    if n.tag in LABELS + SPRITES + ("sound_effect", "projectile_name") and not NAME.fullmatch(v):
        return f"{n.tag} is one word, not {v!r}"
    return ""


def _removable(doc: lx.Doc, n: lx.Node) -> str:
    if n.tag in (ITEM_TAG, EFFECT_TAG):
        return ""
    if n.tag in ("name", EFFECTS_TAG):
        return f"<{n.tag}> is what the record is; remove the record instead"
    par = doc.nodes[n.parent]
    if par.tag == EFFECT_TAG and n.tag == "target":
        return "an effect needs its target"
    return "" if doc.is_leaf(n) else f"<{n.tag}> is not a field"


def _fields_of(doc: lx.Doc, par: lx.Node) -> Tuple[str, ...]:
    if par.tag == ITEM_TAG:
        return ABILITY_FIELDS
    if par.tag == EFFECT_TAG:
        return EFFECTS.get(doc.field(par, "name"), ())
    return ()


def _name_ok(doc: lx.Doc, like: lx.Node, name: str) -> str:
    if like.tag != ITEM_TAG:
        return "an effect is copied as it is; change it after"
    if not NAME.fullmatch(name):
        return f"{name!r} cannot be an ability's name: one word, with no comma"
    if any(a["name"].lower() == name.lower() for a in abilities(doc)):
        return f"there is already an ability called {name}"
    return ""


def plan(mod, body: dict) -> lx.Plan:
    """The body is :mod:`leafxml`'s: ``values``, ``copy`` (an ability copied
    with a new ``name``, or an effect copied ``into`` an ability's
    ``hero_ability_effects``), ``remove``, ``add_field``; and ``sig``."""
    p = lx.Plan(REL, "heroabilities", mod=mod)
    try:
        text = lx.read(mod, REL)
    except lx.LeafError as e:
        p.errors.append(e.message)
        return p
    if str(body.get("sig") or "") != lx.sig(text):
        p.errors.append(_i18n.msg("eng.heroabilities.changed_on_disk_after_it_was", "{REL} changed on disk after it was opened here - reload it", REL=REL))
        return p
    doc = parse(text)
    if doc.root_end < 0:
        p.errors.append(_i18n.msg("eng.heroabilities.does_not_close_its_so_nothing", "{REL} does not close its <{ROOT_TAG}>, so nothing here can be sure where an edit lands - fix it in Raw text first", REL=REL, ROOT_TAG=ROOT_TAG))
        return p
    for spec in body.get("copy") or []:
        like = next((n for n in doc.nodes if str(n.id) == str(spec.get("like"))), None)
        if like is not None and like.tag == ITEM_TAG and not str(spec.get("name") or "").strip():
            p.errors.append(_i18n.msg("eng.heroabilities.a_copied_ability_needs_a_name", "a copied ability needs a name of its own"))
    if p.errors:
        return p
    new = lx.plan_edits(p, text, doc, body, _check_value, (ITEM_TAG, EFFECT_TAG),
                        _removable, _fields_of, _name_ok)
    if not new:
        return p
    p.text = new
    refs = Refs.of(mod)
    was = {f["message"] for f in check(doc, refs)}
    p.warnings += [f["message"] for f in check(parse(new), refs)
                   if f["severity"] != "note" and f["message"] not in was]
    return p


apply = lx.apply
