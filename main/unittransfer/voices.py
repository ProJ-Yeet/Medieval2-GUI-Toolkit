"""Hear a unit's voices by accent, and give it a name call of your own (96e5).

Taken in part from the Pfadfinder-Adam (formerly MasterOogwayHomebrew) RTW /
M2TW Campaign Editor's ``sounds.py`` (the SND.PACK reader, the wav check and the
way a name call is written), with its author's permission, and built on this
toolkit's own voice-bank parser, :mod:`unittransfer.sounds`.

**Where a sound is.** The voice bank names files under ``data/sounds/...``. The
game plays a loose file first, else the record of that name in its packs:
``data/sounds/Voice1.idx`` + ``.dat`` and the rest, the mod's own before the
game's. A pack's ``.idx`` is ``SND.PACK``, a version, a count, then per sound
six u32 (offset into the ``.dat``, size, rate, bits, channels, kind: 1 wav,
2 IMA ADPCM wav, 13 mp3), the name, a zero byte and three more bytes. The
``.dat`` holds whole wav or mp3 files, so a record's bytes play as they are.

**A name call of your own.** The wav goes in as a loose file under a name no
pack has, the unit gets a ``Unit_Select`` entry of its own for that accent and
class (taken out of a line it shared, or added after the block's last entry,
written the way the file writes its others), and the compiled
``data/sounds/events.dat`` / ``.idx`` are removed so the game builds them from
the text again. Every file is backed up first and the job goes in the log, so
Undo takes it back.
"""
from __future__ import annotations

import os
import re
import shutil
import struct
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, sounds
from . import i18n as _i18n
from .logutil import file_op, log

PACKS = ("Voice1", "Voice2", "Voice3", "SFX", "Music")
VOICE_FOLDER = "data/sounds/Voice/Human/Localized/Battle_Map"
KINDS = {1: "wav", 2: "wav", 13: "mp3"}


class VoiceError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Sound:
    __slots__ = ("name", "dat", "offset", "size", "kind")

    def __init__(self, name, dat, offset, size, kind):
        self.name, self.dat, self.offset, self.size, self.kind = name, dat, offset, size, kind

    def read(self) -> bytes:
        with open(self.dat, "rb") as f:
            f.seek(self.offset)
            return f.read(self.size)


_cache: Dict[str, Tuple[float, List[Sound]]] = {}
_lock = threading.Lock()


def _ci(folder: Path, name: str) -> Optional[Path]:
    """``folder/name`` whatever its case, or None."""
    p = folder / name
    if p.exists():
        return p
    low = name.lower()
    try:
        return next((folder / n for n in os.listdir(folder) if n.lower() == low), None)
    except OSError:
        return None


def read_pack(idx: Path) -> List[Sound]:
    stamp = idx.stat().st_mtime
    key = str(idx)
    with _lock:
        got = _cache.get(key)
        if got and got[0] == stamp:
            return got[1]
    b = idx.read_bytes()
    if b[:8] != b"SND.PACK":
        raise ValueError(_i18n.msg("eng.voices.not_a_pack", "{name} is not a sound pack", name=idx.name))
    _ver, n = struct.unpack_from("<2I", b, 8)
    dat = _ci(idx.parent, idx.stem + ".dat") or idx.with_suffix(".dat")
    pos, out = 24, []
    for _ in range(n):
        off, size, _rate, _bits, _ch, kind = struct.unpack_from("<6I", b, pos)
        pos += 24
        end = b.index(b"\0", pos)
        out.append(Sound(b[pos:end].decode("latin-1"), str(dat), off, size, kind))
        pos = end + 4
    with _lock:
        _cache[key] = (stamp, out)
    return out


def _game_data(mod) -> Optional[Path]:
    from . import gamepack
    root = gamepack.game_root_of(mod)
    return root / "data" if root and (root / "data").is_dir() else None


def sound_dirs(mod) -> List[Path]:
    out: List[Path] = []
    for data in (Path(mod.data), _game_data(mod)):
        d = _ci(data, "sounds") if data else None
        if d and d.is_dir() and d not in out:
            out.append(d)
    return out


def pack_index(mod) -> Dict[str, Sound]:
    """``{lower 'data/sounds/...': Sound}`` of every pack the mod plays, its own winning."""
    out: Dict[str, Sound] = {}
    for d in reversed(sound_dirs(mod)):
        names = [n for n in os.listdir(d) if n.lower().endswith(".idx") and n.lower() != "events.idx"]
        stock = {p.lower() for p in PACKS}
        order = [p for p in PACKS] + sorted(n[:-4] for n in names if n[:-4].lower() not in stock)
        for p in order:
            idx = _ci(d, p + ".idx")
            if not idx:
                continue
            try:
                for s in read_pack(idx):
                    out[s.name.lower().replace("\\", "/")] = s
            except (OSError, ValueError, struct.error):
                continue
    return out


def loose_path(mod, rel: str) -> Optional[Path]:
    rel = rel.replace("\\", "/")
    sub = rel[5:] if rel.lower().startswith("data/") else rel
    for data in (Path(mod.data), _game_data(mod)):
        if not data:
            continue
        cur: Optional[Path] = data
        for part in sub.split("/"):
            cur = _ci(cur, part) if cur else None
        if cur and cur.is_file():
            return cur
    return None


def sound_bytes(mod, rel: str, index: Optional[Dict] = None) -> Optional[bytes]:
    """A loose file wins, as it does in the game; else the pack's record."""
    p = loose_path(mod, rel)
    try:
        if p:
            return p.read_bytes()
        s = (index if index is not None else pack_index(mod)).get(rel.lower().replace("\\", "/"))
        return s.read() if s else None
    except OSError:
        return None


def wav_info(data: bytes) -> Optional[Tuple[int, int, int, int]]:
    """``(format, channels, rate, bits)`` of a wav, or None."""
    if len(data) < 36 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if cid == b"fmt " and size >= 16:
            fmt, ch, rate = struct.unpack_from("<HHI", data, pos + 8)
            bits = struct.unpack_from("<H", data, pos + 22)[0]
            return fmt, ch, rate, bits
        pos += 8 + size + (size & 1)
    return None


def content_type(data: bytes) -> str:
    return "audio/wav" if data[:4] == b"RIFF" else "audio/mpeg"


# ---------------------------------------------------------------------------
# what a unit says


def _files(lines: List[str]) -> List[List[str]]:
    """The files of each ``event`` block in these lines, folder joined on."""
    events: List[List[str]] = []
    folder, cur = "", None
    for line in lines:
        code = line.split(";", 1)[0].strip()
        low = code.lower()
        if not code:
            continue
        if low == "event" or low.startswith("event "):
            cur, folder = [], ""
            continue
        if low == "end":
            if cur is not None:
                events.append(cur)
            cur = None
            continue
        if cur is None:
            continue
        if low.startswith("folder "):
            folder = code.split(None, 1)[1].strip().replace("\\", "/")
            continue
        if low.endswith((".wav", ".mp3")):
            cur.append(f"{folder}/{code}" if folder else code)
    return events


def unit_view(mod, unit_type: str, pick: str = "") -> Dict:
    """The unit's name call in every accent the bank gives it one, and its
    accent's class-wide orders, each file marked found or not."""
    unit = next((u for u in mod.edu.units if u.type == unit_type), None)
    if unit is None:
        raise VoiceError(_i18n.msg("eng.voices.no_unit", "no unit {unit} in this mod", unit=unit_type))
    path = Path(mod.data) / sounds.EDS_REL
    if not path.is_file():
        raise VoiceError(_i18n.msg("eng.voices.no_bank", "this mod has no {rel}", rel=sounds.EDS_REL))
    bank = sounds.parse_file(path)
    index = pack_index(mod)
    accent, vclass = sounds.unit_voice_fields(unit)

    def mark(rels: List[str]) -> List[Dict]:
        return [{"rel": r, "found": bool(loose_path(mod, r) or r.lower() in index)} for r in rels]

    calls = []
    for e in bank.unit_entries():
        if unit_type in e.names:
            ev = _files(bank.lines[e.start:e.end])
            calls.append({"accent": e.accent, "class": e.voice_class, "shared": len(e.names) > 1,
                          "files": mark([f for x in ev for f in x])})
    heard = pick or accent or (calls[0]["accent"] if calls else "")
    cls = vclass or (calls[0]["class"] if calls else "")
    orders = []
    for v in bank.vocals:
        if v.vocal == sounds.UNIT_SELECT or v.accent != heard or (cls and v.voice_class != cls):
            continue
        ev = _files(bank.lines[v.start:v.end])
        if ev:
            orders.append({"vocal": v.vocal, "accent": v.accent, "class": v.voice_class,
                           "files": mark(ev[0][:6])})
        if len(orders) >= 40:
            break
    return {"unit": unit_type, "accent": accent, "class": vclass, "heard": heard, "heard_class": cls,
            "accents": bank.accents(), "classes": bank.classes(),
            "pairs": [list(p) for p in bank.class_pairs()],
            "calls": calls, "orders": orders, "packs": bool(index)}


# ---------------------------------------------------------------------------
# a name call of the user's own


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "unit"


def _new_name(mod, prefix: str, index: Dict, taken: set) -> str:
    k = 1
    while True:
        name = f"{prefix}_{k}.wav"
        rel = f"{VOICE_FOLDER}/{name}"
        if rel.lower() not in index and name.lower() not in taken and not loose_path(mod, rel):
            return name
        k += 1


def _indent(line: str) -> str:
    return re.match(r"[ \t]*", line).group(0)


def plan_name_call(mod, unit_type: str, accent: str, vclass: str,
                   wavs: List[Tuple[str, bytes]]) -> Dict:
    """What a name call of one's own would write, without writing it."""
    path = Path(mod.data) / sounds.EDS_REL
    if not path.is_file():
        raise VoiceError(_i18n.msg("eng.voices.no_bank", "this mod has no {rel}", rel=sounds.EDS_REL))
    if not wavs:
        raise VoiceError(_i18n.msg("eng.voices.no_wav", "pick at least one .wav file"))
    bank = sounds.parse_file(path)
    block = bank.unit_select(accent, vclass)
    if block is None:
        raise VoiceError(_i18n.msg("eng.voices.no_block", "the voice bank has no Unit_Select names for {accent}, class {vclass}; pick another accent or class", accent=accent, vclass=vclass))
    tmpl = next((e for e in block.entries if e.kind == "unit"), None) if block.entries else None
    if tmpl is None:
        tmpl = next((e for e in bank.unit_entries() if e.accent == accent and e.voice_class == vclass), None)
    if tmpl is None:
        raise VoiceError(_i18n.msg("eng.voices.no_template", "no unit in {accent}, class {vclass} has a name call to copy the layout of", accent=accent, vclass=vclass))
    lines = bank.lines
    t = lines[tmpl.start:tmpl.end]
    ev_i = next(i for i, ln in enumerate(t) if ln.strip().lower().startswith("event"))
    folder_ln = next((ln for ln in t if ln.strip().lower().startswith("folder")), None)
    file_ln = next((ln for ln in t if ln.strip().lower().endswith((".wav", ".mp3"))), None)
    end_ln = next(ln for ln in reversed(t) if ln.strip().lower() == "end")
    nl = "\r\n" if t[0].endswith("\r\n") else "\n"
    head_ind, ev_ind = _indent(t[0]), _indent(t[ev_i])
    folder_ind = _indent(folder_ln) if folder_ln else ev_ind + "\t"
    file_ind = _indent(file_ln) if file_ln else ev_ind + "\t"

    index = pack_index(mod)
    prefix = f"{_slug(accent).title()}_{vclass}_name_{_slug(unit_type)}_custom"
    names, warnings, taken = [], [], set()
    for label, data in wavs:
        info = wav_info(data)
        if info is None:
            raise VoiceError(_i18n.msg("eng.voices.not_wav", "{label} is not a .wav file; the game's voices are wav, so save it as wav first", label=label))
        name = _new_name(mod, prefix, index, taken)
        taken.add(name.lower())
        fmt, ch, rate, bits = info
        if fmt == 1 and (ch, rate, bits) != (1, 22050, 16):
            warnings.append(_i18n.msg("eng.voices.odd_format", "{label} is {rate} Hz, {bits}-bit, {ch} channel(s); the game's own voices are 22050 Hz, 16-bit, mono, so it may sound off in the game", label=label, rate=rate, bits=bits, ch=ch))
        names.append((name, data))
    new = [f"{head_ind}unit {unit_type}{nl}", f"{ev_ind}event{nl}",
           f"{folder_ind}folder {VOICE_FOLDER}{nl}"]
    new += [f"{file_ind}{n}{nl}" for n, _ in names]
    new.append(f"{_indent(end_ln)}end{nl}")

    out = list(lines)
    old = next((e for e in block.entries if e.kind == "unit" and unit_type in e.names), None)
    if old is None:
        old = next((e for e in bank.unit_entries() if e.accent == accent and e.voice_class == vclass
                    and unit_type in e.names), None)
    changes = []
    if old is not None and len(old.names) == 1:
        out[old.start:old.end] = new
        changes.append(_i18n.msg("eng.voices.replaced", "{accent}, class {vclass}: the name call of {unit} now plays {files}", accent=accent, vclass=vclass, unit=unit_type, files=", ".join(n for n, _ in names)))
    else:
        at = block.end
        if old is not None:
            rest = [n for n in old.names if n != unit_type]
            head = lines[old.start]
            word = re.match(r"([ \t]*unit)\s", head).group(1)
            sep = ", " if ", " in head else ","
            out[old.start] = f"{word} {sep.join(rest)}{nl}"
            at = old.end
            changes.append(_i18n.msg("eng.voices.split", "{accent}, class {vclass}: {unit} taken out of the line it shared with {others}", accent=accent, vclass=vclass, unit=unit_type, others=", ".join(rest[:3])))
        out[at:at] = new
        changes.append(_i18n.msg("eng.voices.added", "{accent}, class {vclass}: {unit} gets its own name call, {files}", accent=accent, vclass=vclass, unit=unit_type, files=", ".join(n for n, _ in names)))
    sdir = _ci(Path(mod.data), "sounds")
    compiled = [p for p in ((_ci(sdir, "events.dat"), _ci(sdir, "events.idx")) if sdir else ()) if p]
    return {"unit": unit_type, "accent": accent, "class": vclass,
            "text": "".join(out), "files": names, "changes": changes, "warnings": warnings,
            "compiled": [str(p) for p in compiled]}


def apply_name_call(mod, p: Dict) -> Dict:
    """Write a planned name call: backups and a log record, so Undo takes it back."""
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}
    data = Path(mod.data)

    def keep(rel: str) -> Path:
        target = data / rel
        if target.exists():
            b = backup_root / "data" / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, b)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {b}")
        else:
            manifest["created"].append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    folder_rel = VOICE_FOLDER[5:]
    for name, raw in p["files"]:
        target = keep(f"{folder_rel}/{name}")
        target.write_bytes(raw)
        file_op("WRITE", target, f"{len(raw)} bytes")
    target = keep(sounds.EDS_REL)
    target.write_text(p["text"], encoding=sounds.ENCODING)   # as sounds.apply_sounds writes it
    file_op("WRITE", target, "name call")
    for c in p["compiled"]:
        rel = os.path.relpath(c, data).replace("\\", "/")
        keep(rel)
        os.remove(c)
        file_op("DELETE", Path(c), "the game builds it again from the sound texts")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "sounds",
           "action": "name call", "source": mod.name, "source_root": str(mod.root),
           "dest": mod.name, "dest_root": str(mod.root), "unit_type": p["unit"],
           "resolved_type": p["unit"], "options": {}, "applied": True, "undone": False,
           "note": "", "summary": "\n".join(p["changes"]), "warnings": list(p["warnings"]),
           "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("VOICE  name call for %s in %s, id=%s", p["unit"], mod.name, tid)
    mod.__dict__.pop("sounds", None)
    return rec
