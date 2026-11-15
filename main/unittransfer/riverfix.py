"""Rivers on ``map_features.tga``, repaired.

**From Mylae's M2TW Editor** (github.com/Machiavello-1441/m2tw-editor, used with
the author's permission): his river Auto-Fix, ``src/components/map/rivers/``
(``riverRepair.js`` and the files it calls, 2026-10-14/15). The steps and their
order are his, written again over a ``W x H`` grid of tiles:

    1  join a river tile that touches the rest only at a corner, through a
       tile of no feature, never closing a loop (``riverDiagonals.js``)
    2  thin a solid block of river to one tile wide, removing only a tile whose
       neighbours stay joined without it (``riverThin.js``)
    3  open every loop: drop a whole fork-to-rejoin arm where there is one,
       else one tile whose removal splits nothing, else the cheapest cut that
       keeps the longest course (``riverCycles.js``, ``riverLoopCorridor.js``,
       ``riverLoopFallback.js``)
    4  clear a river tile that touches no other, corners included
    5  give a course with no source one, at an end tile away from the sea
       (``riverSources.js``)
    6  put back a ford a step removed, on the nearest plain tile of the same
       course (``riverFinalCleanup.js``)

The ends of a course, its sources and its fords are never removed by step 2 or
by the first two tries of step 3 (his protect the ends and the fords; the
source is kept here too, so the block it sits in is thinned around it rather
than through it), and in the last try a source costs a thousand tiles and a ford
ten thousand, so the water's ends stay where the map author put them.

**Where this is narrower than his.** His runs over a freshly imported river
layer and rewrites it freely; this runs over a mod's map, so it changes only
what the validator reports. A fragment of two tiles is left alone (his minimum
is three; no rule here says two is wrong), a source already on a course is
never moved (his relocates one that is not at an end), and impure blues are not
normalised, since the layer's colours are checked by their own rule.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import mapvocab

NONE, RIVER, SOURCE, FORD = 0, 1, 2, 3
#: what a cut costs per tile of each kind: a ford or a source is kept at almost
#: any price (his weights)
_COST = {RIVER: 1, SOURCE: 1001, FORD: 10001}


def _rgb(code: str) -> Tuple[int, int, int]:
    return tuple(mapvocab.feature(code)["rgb"])


class Grid:
    """The river tiles of one features layer, four-connected."""

    def __init__(self, rgb: bytes, width: int, height: int):
        self.w, self.h = width, height
        kinds = {_rgb("river"): RIVER, _rgb("river_source"): SOURCE,
                 _rgb("river_crossing"): FORD}
        self.none = _rgb("none")
        self.mask = bytearray(width * height)
        self.blank = bytearray(width * height)     # a tile of no feature at all
        for n in range(width * height):
            px = (rgb[3 * n], rgb[3 * n + 1], rgb[3 * n + 2])
            self.mask[n] = kinds.get(px, NONE)
            self.blank[n] = px == self.none

    def nb(self, n: int) -> List[int]:
        w, m, out = self.w, self.mask, []
        x = n % w
        if n >= w and m[n - w]:
            out.append(n - w)
        if x < w - 1 and m[n + 1]:
            out.append(n + 1)
        if n + w < len(m) and m[n + w]:
            out.append(n + w)
        if x and m[n - 1]:
            out.append(n - 1)
        return out

    def components(self) -> Tuple[List[int], List[List[int]]]:
        labels = [-1] * len(self.mask)
        comps: List[List[int]] = []
        for n in range(len(self.mask)):
            if not self.mask[n] or labels[n] != -1:
                continue
            nodes, cid = [n], len(comps)
            labels[n] = cid
            j = 0
            while j < len(nodes):
                for q in self.nb(nodes[j]):
                    if labels[q] == -1:
                        labels[q] = cid
                        nodes.append(q)
                j += 1
            comps.append(nodes)
        return labels, comps

    def squares(self, n: int) -> int:
        """How many solid 2x2 blocks of river this tile is a corner of."""
        w, h, m = self.w, self.h, self.mask
        x, y, k = n % w, n // w, 0
        for yy in (y - 1, y):
            for xx in (x - 1, x):
                if xx < 0 or yy < 0 or xx + 1 >= w or yy + 1 >= h:
                    continue
                a = yy * w + xx
                if m[a] and m[a + 1] and m[a + w] and m[a + w + 1]:
                    k += 1
        return k


# -- 1 -------------------------------------------------------------------------

def join_diagonals(g: Grid) -> int:
    labels, comps = g.components()
    parent = list(range(len(comps)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    joined = 0
    for n in range(len(g.mask)):
        if not g.mask[n]:
            continue
        for dx in (-1, 1):
            x, other = n % g.w + dx, n + g.w + dx
            if x < 0 or x >= g.w or other >= len(g.mask) or not g.mask[other]:
                continue
            if root(labels[n]) == root(labels[other]):
                continue
            if g.nb(n) and g.nb(other):
                continue        # only a tile river.diagonal reports: no side neighbour
            for cand in (n + dx, n + g.w):
                if g.mask[cand] or not g.blank[cand]:
                    continue
                roots = [root(labels[p]) for p in g.nb(cand)]
                if len(set(roots)) != len(roots):
                    continue    # would close a loop
                keep = root(labels[n])
                for r in roots:
                    parent[r] = keep
                g.mask[cand] = RIVER
                labels[cand] = keep
                joined += 1
                break
    return joined


# -- 2 -------------------------------------------------------------------------

def _simple(g: Grid, n: int) -> bool:
    """Do this tile's neighbours stay joined inside its 3x3 ring without it?"""
    targets = g.nb(n)
    if len(targets) < 2:
        return False
    x, y = n % g.w, n // g.w
    seen, queue = {targets[0]}, [targets[0]]
    j = 0
    while j < len(queue):
        for q in g.nb(queue[j]):
            if q == n or q in seen or abs(q % g.w - x) > 1 or abs(q // g.w - y) > 1:
                continue
            seen.add(q)
            queue.append(q)
        j += 1
    return all(t in seen for t in targets)


def thin_blocks(g: Grid, keep: bytearray, clear: Callable[[int], None]) -> int:
    queued = bytearray(len(g.mask))
    queue: List[int] = []

    def push(n):
        if g.mask[n] and not keep[n] and not queued[n] and g.squares(n):
            queued[n] = 1
            queue.append(n)

    for n in range(len(g.mask)):
        push(n)
    removed, j = 0, 0
    while j < len(queue):
        n = queue[j]
        j += 1
        queued[n] = 0
        if not g.mask[n] or keep[n] or not g.squares(n) or not _simple(g, n):
            continue
        clear(n)
        removed += 1
        x, y = n % g.w, n // g.w
        for yy in range(max(0, y - 1), min(g.h - 1, y + 1) + 1):
            for xx in range(max(0, x - 1), min(g.w - 1, x + 1) + 1):
                push(yy * g.w + xx)
    return removed


# -- 3 -------------------------------------------------------------------------

def _cycle(g: Grid, nodes: Sequence[int]) -> Optional[List[int]]:
    seen: Set[int] = set()
    active: Set[int] = set()
    parent: Dict[int, int] = {}
    for start in nodes:
        if not g.mask[start] or start in seen:
            continue
        stack = [(start, g.nb(start), 0)]
        seen.add(start)
        active.add(start)
        parent[start] = -1
        while stack:
            n, adj, i = stack[-1]
            if i == len(adj):
                active.discard(n)
                stack.pop()
                continue
            stack[-1] = (n, adj, i + 1)
            q = adj[i]
            if q == parent[n]:
                continue
            if q not in seen:
                seen.add(q)
                active.add(q)
                parent[q] = n
                stack.append((q, g.nb(q), 0))
            elif q in active:
                chain, m = [n], n
                while m != q and parent[m] != -1:
                    m = parent[m]
                    chain.append(m)
                if m == q:
                    return chain
    return None


def _corridor(g: Grid, cycle: List[int], keep: bytearray) -> Optional[List[int]]:
    """The cheapest run of plain two-neighbour tiles on the loop."""
    if not any(len(g.nb(n)) != 2 for n in cycle):
        for n in cycle:
            if not keep[n]:
                return [n]
        return None
    best, seen, L = None, set(), len(cycle)
    for i, start in enumerate(cycle):
        if start in seen or len(g.nb(start)) != 2:
            continue
        run = [start]
        seen.add(start)
        for step in (-1, 1):
            k = (i + step) % L
            while cycle[k] not in seen and len(g.nb(cycle[k])) == 2:
                run.append(cycle[k])
                seen.add(cycle[k])
                k = (k + step) % L
        cost = sum(_COST[g.mask[n]] for n in run)
        if best is None or cost < best[0]:
            best = (cost, run)
    return best[1] if best else None


def _splits_nothing(g: Grid, n: int) -> bool:
    adj = g.nb(n)
    if len(adj) < 2:
        return False
    left, seen, queue = set(adj[1:]), {n, adj[0]}, [adj[0]]
    j = 0
    while j < len(queue) and left:
        for q in g.nb(queue[j]):
            if q not in seen:
                seen.add(q)
                queue.append(q)
                left.discard(q)
        j += 1
    return not left


def _cheapest_cut(g: Grid, cycle: List[int]) -> Optional[List[int]]:
    best = None
    for cut in cycle:
        seen, parts = {cut}, []
        for s in g.nb(cut):
            if s in seen:
                continue
            nodes = [s]
            seen.add(s)
            j = 0
            while j < len(nodes):
                for q in g.nb(nodes[j]):
                    if q not in seen:
                        seen.add(q)
                        nodes.append(q)
                j += 1
            parts.append(nodes)
        parts.sort(key=len, reverse=True)
        gone = [cut] + [n for p in parts[1:] for n in p]
        cost = sum(_COST[g.mask[n]] for n in gone)
        if best is None or cost < best[0]:
            best = (cost, gone)
    return best[1] if best else None


def open_loops(g: Grid, comps: List[List[int]], keep: bytearray,
               clear: Callable[[int], None]) -> int:
    removed = 0
    for nodes in comps:
        while True:
            cycle = _cycle(g, nodes)
            if not cycle:
                break
            run = _corridor(g, cycle, keep)
            if run:
                for n in run:
                    clear(n)
                removed += len(run)
                continue
            cands = sorted((n for n in cycle if not keep[n]), key=lambda n: len(g.nb(n)))
            n = next((c for c in cands if _splits_nothing(g, c)), None)
            if n is not None:
                clear(n)
                removed += 1
                continue
            gone = _cheapest_cut(g, cycle)
            if not gone:
                break
            for n in gone:
                clear(n)
            removed += len(gone)
    return removed


# -- 5, 6 ----------------------------------------------------------------------

def add_sources(g: Grid, sea: Optional[bytes]) -> int:
    """A source for every course that has none, at an end away from the sea."""
    def by_sea(n):
        if not sea:
            return False
        x, y = n % g.w, n // g.w
        return any(0 <= x + dx < g.w and 0 <= y + dy < g.h and sea[(y + dy) * g.w + x + dx]
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def edge(n):
        x, y = n % g.w, n // g.w
        return x in (0, g.w - 1) or y in (0, g.h - 1)

    added = 0
    for nodes in g.components()[1]:
        if any(g.mask[n] == SOURCE for n in nodes):
            continue
        ends = [n for n in nodes if len(g.nb(n)) == 1 and g.mask[n] == RIVER]
        if len(ends) < 2:
            continue
        mouths = [n for n in ends if by_sea(n) or edge(n)]
        inland = [n for n in ends if n not in mouths]
        if inland:
            head = inland[0]
        else:
            # every end is at the sea or the edge: the one furthest from the first mouth
            m = mouths[0]
            head = max(ends, key=lambda n: (n % g.w - m % g.w) ** 2 + (n // g.w - m // g.w) ** 2)
        g.mask[head] = SOURCE
        added += 1
    return added


def restore_fords(g: Grid, fords: Sequence[int]) -> Tuple[int, int]:
    labels, comps = g.components()
    moved = lost = 0
    for old in fords:
        if g.mask[old] == FORD:
            continue
        cid = labels[old]
        if cid < 0:
            cid = next((labels[q] for q in g.nb(old) if labels[q] >= 0), -1)
        cands = [] if cid < 0 else [n for n in comps[cid]
                                     if g.mask[n] == RIVER and len(g.nb(n)) == 2]
        if not cands:
            lost += 1
            continue
        ox, oy = old % g.w, old // g.w
        t = min(cands, key=lambda n: abs(n % g.w - ox) + abs(n // g.w - oy))
        g.mask[t] = FORD
        moved += 1
    return moved, lost


def _touches(g: Grid, n: int) -> bool:
    """Any river in the eight tiles around? (river.isolated's own test.)"""
    x, y = n % g.w, n // g.w
    return any(0 <= x + dx < g.w and 0 <= y + dy < g.h and g.mask[(y + dy) * g.w + x + dx]
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


# -- the whole repair ----------------------------------------------------------

def repair(rgb: bytes, width: int, height: int,
           sea: Optional[bytes] = None) -> Tuple[bytes, Dict[str, int]]:
    """``(new RGB bytes, counts)`` for a features layer's ``W x H`` RGB bytes.

    ``sea`` is the map's sea mask, one byte per tile, or None. Only river tiles
    change: a tile cleared becomes no feature, a tile added becomes river, a
    source or a ford. Every other colour on the layer is left as it was.
    """
    g = Grid(rgb, width, height)
    out = bytearray(rgb)
    joined = join_diagonals(g)
    fords = [n for n in range(len(g.mask)) if g.mask[n] == FORD]
    keep = bytearray(len(g.mask))
    for n in range(len(g.mask)):
        if g.mask[n] and (len(g.nb(n)) <= 1 or g.mask[n] in (FORD, SOURCE)):
            keep[n] = 1
    def clear(n):
        g.mask[n] = NONE

    thinned = thin_blocks(g, keep, clear)
    _, comps = g.components()
    opened = open_loops(g, comps, keep, clear)
    lone = 0
    for n in range(len(g.mask)):
        if g.mask[n] and not _touches(g, n):
            g.mask[n] = NONE
            lone += 1
    sources = add_sources(g, sea)
    moved, lost = restore_fords(g, fords)

    colour = {NONE: g.none, RIVER: _rgb("river"), SOURCE: _rgb("river_source"),
              FORD: _rgb("river_crossing")}
    before = Grid(rgb, width, height).mask
    for n in range(len(g.mask)):
        if g.mask[n] != before[n]:
            out[3 * n:3 * n + 3] = bytes(colour[g.mask[n]])
    return bytes(out), {"joined": joined, "thinned": thinned, "opened": opened,
                        "lone": lone, "sources": sources, "fords_moved": moved,
                        "fords_lost": lost}
