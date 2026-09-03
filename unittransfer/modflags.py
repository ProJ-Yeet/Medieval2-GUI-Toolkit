"""Per-mod flags. Today there is one: whether the mod runs on **M2EX**.

M2EX is a *separate* thing from M2TWEOP, and the toolkit already had a per-mod
setting for that one (:mod:`unittransfer.eop`, which is about where a mod's extra
unit files live). This is not that. M2EX replaces the engine's own hardcoded
tables, so the ceilings the vanilla executable has simply are not there: the
31-faction cap, the 500-unit cap, the caps on a trait's levels and an ancillary's
effects, the 32 recruitment slots a building may offer. A mod built for it sits
over several of them by design.

Which is why this is a flag and not a guess. The toolkit cannot detect M2EX from
a mod's files - nothing in ``data/`` says so - and reporting the caps anyway
turned every check on such a mod into a page of findings that were all
deliberate. So the person who knows says so once, on the Home screen or in
Settings, and from then on:

  * the cap findings are dropped rather than shown (:func:`uncapped`), and
  * the 500-unit transfer warning is suppressed, the same way ticking it off on
    the warning itself already did.

Nothing else changes. A cap finding is *only* the "you are over the engine's
number" one - every other check on the same record (a missing text key, a
line in the wrong order, a name nothing defines) still runs, because none of
those are things M2EX makes legal.

Stored the way the EOP folders are: a table in ``config/settings.json`` keyed by
the mod's resolved root path, so it survives the mod being renamed in the picker
and cannot be confused with another mod of the same name somewhere else.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from . import config

#: The finding kinds that are engine ceilings, and nothing else. Each one is a
#: count against a number baked into the vanilla executable - the number M2EX
#: replaces - so these are exactly the findings that stop being true on a mod
#: that runs on it.
CAP_FINDINGS = frozenset({
    "too-many-factions",        # descr_sm_factions.txt: vanilla loads 31
    "too-many-levels",          # one trait: 9 levels
    "too-many-antitraits",      # one trait: 20 antitraits
    "too-many-excluded",        # one ancillary: 3 ExcludedAncillaries
    "too-many-effects",         # one ancillary: 8 Effect lines
    "recruit-limit",            # one building: 32 recruitment slots
    "recruit-limit-always",
})

#: settings.json key for the table below
_SETTING = "m2ex"


def _root_of(mod) -> "Path | str":
    """The mod folder, whether the caller had a :class:`~unittransfer.mod.Mod` or a
    plain path.

    ``getattr(mod, "root", mod)`` is what this used to be, and on a ``Path`` it is
    a trap: ``Path.root`` is the path's own ANCHOR - ``'\'`` on Windows - not a
    folder anyone means. Every mod handed in as a path therefore keyed to the
    drive root of the process's working directory instead of itself, so
    ``/api/mods`` (which reads the flag straight off the discovered path) reported
    every mod's mark as whatever one shared bogus row said. Ticking a mod on the
    Home card still looked right - that response is answered from a ``Mod``, which
    has a real ``.root`` - and the tick then vanished the next time the mod list
    was fetched.
    """
    if isinstance(mod, (str, Path)):
        return mod
    return getattr(mod, "root", None) or mod


def _key(root) -> str:
    """The settings-table key for a mod root - resolved, slashed and folded.

    The same normalisation :func:`unittransfer.eop._key` uses, and for the same
    reason: the browser hands back a path with whatever separators and casing the
    OS dialog produced, and two spellings of one folder must not become two rows.
    """
    p = Path(root)
    try:
        return str(p.resolve()).replace("\\", "/").casefold()
    except OSError:
        return str(p).replace("\\", "/").casefold()


def is_m2ex(mod) -> bool:
    """Has this mod been marked as running on M2EX?"""
    root = _root_of(mod)
    table = config.load_settings().get(_SETTING) or {}
    return bool(table.get(_key(root)))


def set_m2ex(mod, on: bool) -> bool:
    """Mark (or unmark) this mod. Returns what it is now."""
    root = _root_of(mod)
    settings = config.load_settings()
    table = dict(settings.get(_SETTING) or {})
    if on:
        table[_key(root)] = True
    else:
        table.pop(_key(root), None)
    config.save_settings(**{_SETTING: table})
    return bool(on)


def marked_roots() -> List[str]:
    """Every mod root currently marked, for the Settings panel's list."""
    return sorted((config.load_settings().get(_SETTING) or {}).keys())


def uncapped(findings: Iterable[Dict], mod) -> List[Dict]:
    """``findings`` with the engine-ceiling ones dropped when ``mod`` is M2EX.

    Called where a module hands its findings out with the mod in hand - its
    overview, its detail pane and its plan - rather than inside the ``check``
    functions themselves, which are pure and take a parsed file rather than a
    mod. One seam, one list of kinds, and every editor gets the same answer.
    """
    rows = list(findings)
    if not rows or not getattr(mod, "m2ex", False):
        return rows
    return [f for f in rows if f.get("kind") not in CAP_FINDINGS]
