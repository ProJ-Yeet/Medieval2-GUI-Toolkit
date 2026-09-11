"""The nearest tile that would take it. D10, 22b.

Every placement on the map already has its "no": :func:`mapcheck.marker_faults`
for a settlement or a port pixel, :func:`stratchar.check_character` for a
character on the wrong side of the shore, :mod:`stratobj`'s tile findings for a
fort, a watchtower or a resource, and 18b's sea rule for an event. What none of
them said was where it could go instead, and a refusal with no way forward
leaves somebody clicking round the coast one tile at a time.

This is only the search. It walks outwards from the tile in rings of growing
distance and hands each tile to the caller's own predicate, so the rules stay
where they are and there is still one copy of each - the brief for D10 was a
spiral over the predicate we already have, not a second set of rules.

**Nearest is by straight-line distance**, ties broken by ring and then by a
fixed order round the ring, so the same tile always gets the same answer.
**The search gives up at :data:`RADIUS` tiles.** A tile 40 tiles from where
somebody clicked is not "nearly here"; it is a different place, and saying
"nothing within 40" is the honest answer. A search that finds nothing returns
None and the caller says the plain "no".
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, List, Optional, Tuple

#: how far out the search goes, in tiles
RADIUS = 40


@lru_cache(maxsize=4)
def offsets(radius: int = RADIUS) -> Tuple[Tuple[int, int], ...]:
    """Every ``(dx, dy)`` within ``radius``, nearest first, ``(0, 0)`` first.

    6,561 of them at the default radius, sorted once and kept.
    """
    out: List[Tuple[int, int, int, int]] = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            d2 = dx * dx + dy * dy
            if d2 <= radius * radius:
                out.append((d2, max(abs(dx), abs(dy)), dy, dx))
    out.sort()
    return tuple((dx, dy) for _, _, dy, dx in out)


def nearest(width: int, height: int, x: int, y: int,
            ok: Callable[[int, int], bool], radius: int = RADIUS
            ) -> Optional[Tuple[int, int]]:
    """The nearest tile to ``(x, y)`` that ``ok`` accepts, or None.

    Coordinates are whatever the caller works in - image or game - as long as
    ``ok`` takes the same ones; tiles off a ``width`` x ``height`` grid are
    never offered. A start off the grid is searched from the nearest tile on it.
    """
    cx = min(max(int(x), 0), width - 1)
    cy = min(max(int(y), 0), height - 1)
    for dx, dy in offsets(radius):
        tx, ty = cx + dx, cy + dy
        if 0 <= tx < width and 0 <= ty < height and ok(tx, ty):
            return tx, ty
    return None


def distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Tiles between two, the way an army counts them: the longer side."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def sentence(at: Optional[Tuple[int, int]], start: Tuple[int, int],
             where: str = "", noun: str = "tile that would do",
             radius: int = RADIUS) -> str:
    """The clause a finding ends on: where, how far, and in which province."""
    if at is None:
        return f" There is no {noun} within {radius} tiles."
    n = distance(at, start)
    return (f" The nearest {noun} is {at[0]},{at[1]}, {n} tile"
            f"{'' if n == 1 else 's'} away" + (f", in {where}" if where else "")
            + ".")
