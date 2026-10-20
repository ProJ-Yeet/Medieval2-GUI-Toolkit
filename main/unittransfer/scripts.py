"""The Scripts screen: ready-made add-ons and the no-code Module builder (96e1).

The work is the Pfadfinder-Adam campaign editor's (``scriptbuilder``,
``scriptaddons``, ``scriptdocs``, ``scriptfiles``, ported with its author's
permission); this module is only what the page asks for, in one shape.

**Where scripts run.** M2EX runs every ``.nut`` of the game's
``script/modules`` folder (its ``script/main.nut`` requires them all), for
whatever mod is started, and the original Medieval II runs none. So a script
add-on or a module is offered on any mod, and the page says plainly when the mod
is not marked as running on M2EX: the script would then do nothing. The two
file add-ons (Upkeep x N, One Recruitment Grid) change the mod's own files and
need no engine.

Labels come through :mod:`scriptwords` so the page reads in the toolkit's
language; the scripts themselves are written in English, as the engines read
them.
"""
from __future__ import annotations

from typing import Dict, List

from . import modflags, scriptaddons as AD, scriptbuilder as SB, scriptcompat as SC
from . import i18n as _i18n


def _w(kind: str, key: str, default: str) -> str:
    from . import scriptwords
    return scriptwords.word(kind, key, default)


def _fields(part) -> List[Dict]:
    return [{"name": n, "kind": k, "label": _w("field", f"{part.key}.{n}", lab) if lab else "", "default": d}
            for n, k, lab, d in part.fields]


def vocab() -> Dict:
    """What the builder offers, in the page's words."""
    return {
        "events": [{"key": e.key, "label": _w("event", e.key, e.label), "help": _w("event_help", e.key, e.help),
                    "subjects": list(e.subjects)} for e in SB.EVENTS],
        "conditions": [{"key": p.key, "label": _w("cond", p.key, p.label), "help": _w("cond_help", p.key, p.help),
                        "needs": list(p.needs), "fields": _fields(p)} for p in SB.CONDITIONS],
        "actions": [{"key": p.key, "label": _w("act", p.key, p.label), "help": _w("act_help", p.key, p.help),
                     "needs": list(p.needs), "fields": _fields(p)} for p in SB.ACTIONS],
        "who": [[k, _w("who", k, v)] for k, v in SB.WHO_IS],
        "to": [[k, _w("to", k, v)] for k, v in SB.TO],
        "ops": [[k, _w("op", k, v)] for k, v in SB.TURN_OPS],
        "stances": [[k, _w("stance", k, v)] for k, v in SB.STANCES],
        "match": [[k, _w("match", k, v)] for k, v in SB.MATCH],
        "each": [[k, _w("each", k, v)] for k, v in SB.EACH],
        "each_of": [[k, _w("each_of", k, v)] for k, v in SB.EACH_OF],
        "examples": [{"title": r["title"], "label": _w("example", r["title"], r["title"])} for r in SB.EXAMPLES],
    }


def _addon_row(mod, a) -> Dict:
    try:
        have = AD.installed(mod, a)
    except Exception as e:  # noqa: BLE001 - one add-on that will not read is shown as that
        have, err = None, str(e)
    else:
        err = ""
    try:
        values = have if have is not None else AD.read_settings(a, a.template())
    except Exception:  # noqa: BLE001
        values = {}
    return {"key": a.key, "title": _w("addon", a.key, a.title), "summary": _w("addon_help", a.key, a.summary),
            "files": AD.is_files(a), "own": a.own, "installed": have is not None, "values": values, "error": err,
            "settings": [{"var": s.var, "kind": s.kind, "label": _w("setting", f"{a.key}.{s.var}", s.label),
                          "help": _w("setting_help", f"{a.key}.{s.var}", s.help),
                          "choices": [[v, _w("choice", f"{a.key}.{s.var}.{v}", lab)] for v, lab in s.choices]}
                         for s in a.settings]}


def overview(mod) -> Dict:
    m2ex = modflags.is_m2ex(mod)
    addons = [a for a in AD.library() if a.fits("medieval2")]
    mine = []
    try:
        for a, r in SB.my_modules():
            mine.append({"key": a.key, "title": a.title, "recipe": r})
    except Exception:  # noqa: BLE001
        pass
    target = ""
    try:
        target = AD.target(mod, next(a for a in addons if not AD.is_files(a)))
    except (StopIteration, Exception):  # noqa: BLE001
        target = ""
    return {"mod": mod.name, "m2ex": m2ex, "target": target,
            "runs": AD.loads_modules(SC.game_of(mod.data)) or AD.loads_modules(str(mod.root)),
            "addons": [_addon_row(mod, a) for a in addons], "mine": mine, "vocab": vocab()}


def _addon(key):
    a = next((x for x in AD.library() if x.key == key), None)
    if a is None:
        raise ValueError(_i18n.msg("eng.scripts.no_addon", "no add-on called {key}", key=key))
    return a


def plan_addon(mod, key: str, action: str, values: Dict) -> SC.Plan:
    a = _addon(key)
    plan = SC.Plan(mod)
    if action == "remove":
        AD.plan_remove(plan, a, mod)
    else:
        AD.plan_install(plan, a, dict(values or {}), mod)
    return plan


def preview(mod, recipe: Dict) -> Dict:
    """The recipe read back in plain words, what is wrong with it, and its script."""
    probs = SB.problems(recipe, mod)
    return {"words": SB.plain_words(recipe), "problems": probs,
            "script": SB.script(recipe) if not probs else "", "settings": SB.settable(recipe)}


def save_module(recipe: Dict) -> Dict:
    a = SB.save(recipe)
    return {"key": a.key, "title": a.title}


def example(mod, title: str) -> Dict:
    return SB.fit_to_mod(SB.example(title), mod)


def new_recipe(title: str = "") -> Dict:
    return SB.new_recipe(title or _i18n.msg("eng.scripts.my_module", "My module"))
