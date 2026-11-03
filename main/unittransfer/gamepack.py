r"""The base game's ``packs/*.pack``, read without unpacking them (Phase 98f).

A mod that leans on the base game ships only what it changed; the engine finds
the rest in ``packs/data_0.pack`` to ``data_4.pack`` (plus ``localized.pack``
and ``voices.pack``), 3.9 GB that most players never unpack. This module is the
one place those files are read. The rest of the toolkit asks :func:`lookup`
for a file a mod names and is told where it is: the mod's own ``data/``, the
game's loose ``data/`` (an install somebody unpacked), or a pack. Nothing is
ever written into the game or the mod; a file a caller needs as a path is read
out into the toolkit's cache folder, once.

These are not the battle animation packs (``pack.idx`` / ``pack.dat``), which
:mod:`unittransfer.animpack` reads.

The container
-------------
Little endian::

    char[4]  magic          PACK
    uint16   0
    uint16   version        3 on every pack of this install
    uint32   file count     n
    uint32   index size     bytes of the entry records below
    uint32   block count    b
    uint32   0
    uint32   record offset  n - 1 of them, from the first record; the first is 0
    uint32   block size     b of them, each block's bytes in the pack
    records, one a file:
      uint32 offset         where the file's first block starts in the pack
      uint32 first block    its index into the block sizes
      uint32 size           the file's own size
      uint32 packed size    the sum of its blocks
      char[] name + NUL     ``data/...``, lower case, padded to 4 bytes

then the blocks, file after file. A file is cut into 64 KB pieces and each is
packed on its own with LZO1X; a block whose packed size equals its own size was
stored as it is. All 37,168 files of the seven packs read out at the size their
record gives (``tests/test_gamepack.py`` keeps a sample of that).
"""
from __future__ import annotations

import hashlib
import logging
import os
import struct
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import i18n as _i18n

log = logging.getLogger(__name__)

BLOCK = 0x10000
MAGIC = b"PACK"


class PackError(ValueError):
    """A pack this reader cannot read, or a block that does not decode."""


# ---------------------------------------------------------------------------
# LZO1X, decompression only

def lzo1x_decompress(src: bytes, out_len: int) -> bytes:
    """One LZO1X stream, decoded to exactly ``out_len`` bytes.

    The format is a run of instructions, each either "copy these literal bytes"
    or "copy this many bytes from that far back in the output". The four match
    kinds (M1 to M4) differ only in how they spell the distance and length.
    Raises :class:`PackError` on a stream that runs off either end.
    """
    out = bytearray()
    ip = 0
    n = len(src)

    def match(dist: int, length: int) -> None:
        start = len(out) - dist
        if start < 0:
            raise PackError(_i18n.msg("eng.gamepack.lzo_match_before_start", "an LZO match reaches before the start of the block"))
        if dist >= length:
            out.extend(out[start:start + length])
        else:
            # overlapping: the bytes being copied are still being written
            chunk = out[start:]
            whole, rest = divmod(length, dist)
            out.extend(chunk * whole + chunk[:rest])

    def run_length(t: int, base: int) -> int:
        nonlocal ip
        while src[ip] == 0:
            t += 255
            ip += 1
        t += base + src[ip]
        ip += 1
        return t

    try:
        t = src[ip]
        state = "loop"
        if t > 17:
            ip += 1
            t -= 17
            out.extend(src[ip:ip + t])
            ip += t
            state = "first" if t >= 4 else "trail_done"
        while True:
            if state == "loop":
                t = src[ip]
                ip += 1
                if t < 16:
                    if t == 0:
                        t = run_length(0, 15)
                    out.extend(src[ip:ip + t + 3])
                    ip += t + 3
                    state = "first"
                    continue
                state = "match"
            elif state == "first":
                # straight after a literal run of four or more: a short M1
                # match is three bytes at a longer distance
                t = src[ip]
                ip += 1
                if t >= 16:
                    state = "match"
                else:
                    match(1 + 0x800 + (t >> 2) + (src[ip] << 2), 3)
                    ip += 1
                    state = "done"
                    continue
            elif state == "trail_done":
                t = src[ip]
                ip += 1
                state = "match"
            if state == "match":
                if t >= 64:
                    dist = 1 + ((t >> 2) & 7) + (src[ip] << 3)
                    ip += 1
                    match(dist, (t >> 5) + 1)
                elif t >= 32:
                    t &= 31
                    if t == 0:
                        t = run_length(0, 31)
                    dist = 1 + ((src[ip] | (src[ip + 1] << 8)) >> 2)
                    ip += 2
                    match(dist, t + 2)
                elif t >= 16:
                    dist = (t & 8) << 11
                    t &= 7
                    if t == 0:
                        t = run_length(0, 7)
                    dist += (src[ip] | (src[ip + 1] << 8)) >> 2
                    ip += 2
                    if dist == 0:
                        break                     # the end-of-stream marker
                    match(dist + 0x4000, t + 2)
                else:
                    match(1 + (t >> 2) + (src[ip] << 2), 2)
                    ip += 1
                state = "done"
            if state == "done":
                # the low two bits of the byte two back: 0-3 literals follow
                t = src[ip - 2] & 3
                if t == 0:
                    state = "loop"
                    continue
                out.extend(src[ip:ip + t])
                ip += t
                state = "trail_done"
    except IndexError:
        raise PackError(_i18n.msg("eng.gamepack.lzo_block_cut_short", "an LZO block ends in the middle of an instruction")) from None
    if len(out) != out_len:
        raise PackError(_i18n.msg("eng.gamepack.lzo_wrong_size", "an LZO block decoded to {got} bytes, not {want}", got=len(out), want=out_len))
    return bytes(out)


# ---------------------------------------------------------------------------
# one pack

class GamePack:
    """One ``.pack`` file's index, and the files read out of it by name."""

    def __init__(self, path: Path):
        self.path = Path(path)
        st = self.path.stat()
        self.stamp = (st.st_size, st.st_mtime_ns)
        self.entries: Dict[str, Tuple[int, int, int, int]] = {}
        with open(self.path, "rb") as f:
            head = f.read(24)
            if len(head) < 24 or head[:4] != MAGIC:
                raise PackError(_i18n.msg("eng.gamepack.not_a_pack", "{name} is not a PACK file", name=self.path.name))
            _z, _version, count, index_size, nblocks, _zero = struct.unpack_from("<HHIIII", head, 4)
            starts = (0,) + struct.unpack(f"<{max(count - 1, 0)}I", f.read(4 * max(count - 1, 0)))
            self.blocks = struct.unpack(f"<{nblocks}I", f.read(4 * nblocks))
            index = f.read(index_size)
        for at in starts[:count]:
            offset, first, size, packed = struct.unpack_from("<4I", index, at)
            end = index.index(b"\0", at + 16)
            name = index[at + 16:end].decode("latin-1").replace("\\", "/").lower()
            self.entries.setdefault(name, (offset, first, size, packed))

    def __contains__(self, name: str) -> bool:
        return name.lower() in self.entries

    def size_of(self, name: str) -> int:
        return self.entries[name.lower()][2]

    def read(self, name: str) -> bytes:
        """The file called ``name`` (``data/...``), whole."""
        offset, first, size, _packed = self.entries[name.lower()]
        out = bytearray()
        with open(self.path, "rb") as f:
            f.seek(offset)
            left, i = size, first
            while left > 0:
                want = min(BLOCK, left)
                raw = f.read(self.blocks[i])
                out += raw if len(raw) == want else lzo1x_decompress(raw, want)
                left -= want
                i += 1
        return bytes(out)


# ---------------------------------------------------------------------------
# a game's packs, and the one lookup

_LOCK = threading.Lock()
_PACKS: Dict[str, Tuple[tuple, List[GamePack]]] = {}


def pack_paths(root: Path) -> List[Path]:
    """``<root>/packs/*.pack``, ``data_0`` to ``data_4`` first, by name."""
    folder = Path(root) / "packs"
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir() if p.suffix.lower() == ".pack" and p.is_file()]
    return sorted(found, key=lambda p: (not p.name.lower().startswith("data_"), p.name.lower()))


def packs(root) -> List[GamePack]:
    """Every pack under ``root``, indexed once and kept while none changes.

    Indexing all seven of the base game's packs reads about 3 MB of tables and
    takes 0.13 s, so the index is held in memory and not written to disk.
    """
    if not root:
        return []
    paths = pack_paths(Path(root))
    try:
        stamp = tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
    except OSError:
        return []
    key = str(Path(root)).lower()
    with _LOCK:
        hit = _PACKS.get(key)
        if hit and hit[0] == stamp:
            return hit[1]
        out = []
        for p in paths:
            try:
                out.append(GamePack(p))
            except (OSError, PackError, struct.error, ValueError) as e:
                log.warning("pack %s not read: %s", p, e)
        _PACKS[key] = (stamp, out)
        return out


def game_root_of(mod=None) -> Optional[Path]:
    """The base game a mod reads its missing files from.

    The game folder two above ``mods/<name>`` when it has ``packs/`` or a loose
    ``data/``, else the install the settings name (or the registry finds).
    """
    if mod is not None:
        root = Path(getattr(mod, "root", "") or "")
        up = root.parent.parent if root.parent.name.lower() == "mods" else None
        if up is not None and ((up / "packs").is_dir() or (up / "data").is_dir()):
            return up
    from . import config
    saved = config.get_med2_root()
    return Path(saved) if saved and Path(saved).is_dir() else None


def _key(rel: str, prefix: str = "data/") -> str:
    rel = (rel or "").replace("\\", "/").strip().lstrip("/").lower()
    if rel.startswith("data/"):
        rel = rel[5:]
    return prefix + rel


def find_in_packs(rel: str, root, prefix: str = "data/") -> Optional[GamePack]:
    """The pack holding ``data/<rel>``, the first in :func:`pack_paths` order.

    ``prefix`` is how the packs under ``root`` name a data file: ``data/`` in
    the base game's, ``mods/<campaign>/data/`` in a Kingdoms campaign's own.
    """
    key = _key(rel, prefix)
    for pack in packs(root):
        if key in pack.entries:
            return pack
    return None


def read_bytes(rel: str, root) -> Optional[bytes]:
    """``data/<rel>`` out of the game's packs, or None when no pack has it."""
    pack = find_in_packs(rel, root)
    return pack.read(_key(rel)) if pack else None


def extract(rel: str, root, prefix: str = "data/") -> Optional[Path]:
    """``data/<rel>`` read out of its pack into the cache, and its path there.

    Keyed by the pack's size and mtime and the name, so a patched pack is read
    again and an unchanged one never twice. The file keeps its own name, since
    some readers go by the extension.
    """
    pack = find_in_packs(rel, root, prefix)
    if pack is None:
        return None
    from . import config
    key = _key(rel, prefix)
    tag = hashlib.sha1(f"{pack.path}|{pack.stamp}|{key}".encode("utf-8")).hexdigest()[:16]
    out = config.cache_dir("gamepack") / tag / key.rsplit("/", 1)[-1]
    if out.is_file() and out.stat().st_size == pack.size_of(key):
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + f".{os.getpid()}.part")
    tmp.write_bytes(pack.read(key))
    os.replace(tmp, out)
    return out


#: Where a file was found, as :func:`lookup` reports it. ``modpack`` is the
#: mod's OWN file kept in its own ``packs/`` - a Kingdoms campaign keeps every
#: file there - and is the mod's, not the base game's.
MOD, MODPACK, GAME, PACK = "mod", "modpack", "game", "pack"
#: the two that come from the base game rather than from the mod
BASE = (GAME, PACK)


def own_prefix(mod) -> str:
    """How ``mod``'s own packs name its data files, or ``""`` if it has none.

    A Kingdoms campaign (``mods/americas``) ships ``packs/data_0.pack`` and
    names every file in it ``mods/americas/data/...``, which is where the game
    lays it over the base game's.
    """
    root = Path(getattr(mod, "root", "") or "")
    if not (root / "packs").is_dir():
        return ""
    if root.parent.name.lower() == "mods":
        return f"mods/{root.name.lower()}/data/"
    # the game itself, opened read only as the base game: its packs name its
    # files as plain data/...
    return "data/" if (root / "mods").is_dir() else ""


def own_packed(rel: str, mod, as_path: bool = True) -> Tuple[Optional[Path], bool]:
    """``data/<rel>`` out of the mod's own packs: (path or None, found)."""
    prefix = own_prefix(mod)
    if not prefix or find_in_packs(rel, mod.root, prefix) is None:
        return None, False
    return (extract(rel, mod.root, prefix) if as_path else None), True


def lookup(rel: str, mod=None, root=None, *, as_path: bool = True) -> Tuple[Optional[Path], str]:
    """Find ``data/<rel>`` the way the game does: the mod, the game, the packs.

    Returns ``(path, where)``: ``where`` is ``"mod"`` for the mod's own
    ``data/``, ``"modpack"`` for the mod's own ``packs/`` (a Kingdoms
    campaign), ``"game"`` for the base game's loose ``data/`` (an install that
    was unpacked), ``"pack"`` for a file inside ``packs/`` (read out into the
    cache when ``as_path``; ``path`` is None otherwise), and ``(None, "")`` when
    none of them has it.
    """
    clean = (rel or "").replace("\\", "/").strip().lstrip("/")
    if clean.lower().startswith("data/"):
        clean = clean[5:]
    if not clean or ".." in clean.split("/") or ":" in clean:
        return None, ""                   # a path that leaves data/ is never followed
    if mod is not None:
        own = Path(mod.data) / clean
        if own.is_file():
            return own, MOD
        path, found = own_packed(clean, mod, as_path)
        if found:
            return path, MODPACK
    root = Path(root) if root else game_root_of(mod)
    if root is None:
        return None, ""
    loose = root / "data" / clean
    if loose.is_file():
        return loose, GAME
    if find_in_packs(clean, root) is None:
        return None, ""
    return (extract(clean, root) if as_path else None), PACK


def exists(rel: str, mod=None, root=None) -> str:
    """Where ``data/<rel>`` would be found (``mod``/``game``/``pack``), or ``""``."""
    return lookup(rel, mod, root, as_path=False)[1]
