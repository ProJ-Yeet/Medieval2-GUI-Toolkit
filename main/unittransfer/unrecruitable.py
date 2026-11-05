"""Find EDU units absent from building pools, accounting for mercenaries."""
from __future__ import annotations


_MERCS_NAME = "descr_mercenaries.txt"


def _mercenary_units(path) -> set[str]:
    """Read unit names from one mercenary file without loading map tooling."""
    try:
        text = path.read_text(encoding="latin-1")
    except OSError:
        return set()
    units: set[str] = set()
    in_pool = False
    for raw in text.splitlines():
        code = raw.split(";", 1)[0].strip()
        word, _, rest = code.partition(" ")
        if word.casefold() == "pool":
            in_pool = True
        elif in_pool and word.casefold() == "unit":
            name = rest.casefold().split("exp", 1)[0].strip().rstrip(",").strip()
            if name:
                units.add(name)
    return units


def _mercenary_types(mod) -> tuple[set[str], int]:
    """Return type names listed by every campaign's mercenary file."""
    types: set[str] = set()
    files = 0
    for path in mod.data.rglob(_MERCS_NAME):
        if not path.is_file():
            continue
        files += 1
        types.update(_mercenary_units(path))
    return types, files


def scan(mod) -> dict:
    """Return main-EDU types absent from building pools, grouped by availability.

    The EDB parser already understands comments, quoted multi-word unit types,
    and both ordinary and faction-specific capability blocks.  Walking its
    parsed capabilities keeps this check aligned with the buildings editor.
    """
    unit_types = sorted({u.type for u in mod.edu.main_units if u.type}, key=str.lower)
    recruited = set()
    pools = 0
    for building in mod.edb.buildings:
        for level in building.blocks:
            for capability in level.capabilities + level.faction_capabilities:
                pool = capability.pool()
                if pool is not None and pool.unit:
                    recruited.add(pool.unit.casefold())
                    pools += 1
    mercenaries, mercenary_files = _mercenary_types(mod)
    absent = [unit_type for unit_type in unit_types if unit_type.casefold() not in recruited]
    return {
        "units": [{"type": unit_type} for unit_type in absent
                  if unit_type.casefold() not in mercenaries],
        "mercenary_units": [{"type": unit_type} for unit_type in absent
                            if unit_type.casefold() in mercenaries],
        "unit_count": len(unit_types),
        "pools_scanned": pools,
        "mercenary_files_scanned": mercenary_files,
    }
