"""Provide the Scripts page overview, recipe tools and add-on plans.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

from . import i18n as _i18n, modflags
from . import scriptcompat as SC, scriptbuilder as SB, scriptaddons as AD


def overview(mod) -> dict:
    try:
        addons = AD.all_addons()
    except (OSError,ValueError):
        addons = list(AD.ADDONS)
    offered = [a for a in addons if a.game in ('both','medieval2')]
    target = ''
    try:
        target = str(AD.target(next(a for a in offered if not a.integration),mod))
    except (OSError,ValueError,StopIteration):
        pass
    mine = []
    try:
        mine = [dict(key=a.key,title=a.title,recipe=a.recipe) for a in addons if a.own and a.recipe is not None]
    except (OSError,ValueError):
        pass
    return dict(mod=mod.name,m2ex=bool(modflags.is_m2ex(mod)),target=target,
                runs=SC.loader(mod.root) or SC.loader(SC.game_root(mod)),addons=[AD.row(a,mod) for a in offered],mine=mine,vocab=SB.vocabulary())


def plan_addon(mod,key: str,action: str,values: dict) -> SC.Plan:
    addon = next((a for a in AD.all_addons() if a.key == key),None)
    if addon is None:
        raise ValueError(_i18n.msg('eng.scripts.no_addon','no add-on called {key}',key=key))
    return AD.plan(addon,mod,action,values)


def preview(mod,recipe: dict) -> dict:
    return SB.preview(mod,recipe)


def save_module(recipe: dict) -> dict:
    return SB.save_module(recipe)


def example(mod,title: str) -> dict:
    return SB.example(mod,title)


def new_recipe(title: str = '') -> dict:
    return SB.new_recipe(title)


def import_addon(name: str, raw: bytes) -> dict:
    return AD.import_addon(name,raw)
