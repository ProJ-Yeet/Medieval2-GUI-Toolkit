"""Find the sounds a unit says, and give a unit a name call of its own.

Three jobs: find a sound the way Medieval II does (a loose file first, else a
record in a SND.PACK .idx/.dat pair, the mod's packs before the game's);
describe what a unit says (its name calls per accent and the orders of its
accent, each file marked found or not); and, from uploaded .wav files, plan and
apply a name call for a unit, with backups, a log record and Undo.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
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

from . import config, gamepack, sounds
from . import i18n as _i18n
from .logutil import file_op, log

PACKS = ("Voice1", "Voice2", "Voice3", "SFX", "Music")
VOICE_FOLDER = "data/sounds/Voice/Human/Localized/Battle_Map"
KINDS = {1: "wav", 2: "wav", 13: "mp3"}
_MAGIC = b"SND.PACK"


class VoiceError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Sound:
    def __init__(self, name, dat, offset, size, kind):
        self.name, self.dat, self.offset, self.size, self.kind = name, dat, offset, size, kind

    def read(self) -> bytes:
        with open(self.dat, "rb") as fh:
            fh.seek(self.offset)
            return fh.read(self.size)


# ---------------------------------------------------------------------------
# finding files


def _ci(folder: Path, name: str) -> Optional[Path]:
    """``folder/name`` whatever the case of its letters, or None."""
    folder = Path(folder)
    exact = folder / name
    if exact.exists():
        return exact
    want = name.lower()
    try:
        for child in folder.iterdir():
            if child.name.lower() == want:
                return child
    except OSError:
        pass
    return None


_CACHE: Dict[Tuple[str, float], List[Sound]] = {}
_LOCK = threading.Lock()


def read_pack(idx: Path) -> List[Sound]:
    idx = Path(idx)
    key = (str(idx), idx.stat().st_mtime)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    raw = idx.read_bytes()
    if raw[:8] != _MAGIC:
        raise ValueError(_i18n.msg("eng.voices.not_a_pack", "{name} is not a sound pack", name=idx.name))
    count = struct.unpack_from("<I", raw, 12)[0]
    dat = _ci(idx.parent, idx.stem + ".dat") or idx.with_suffix(".dat")
    out: List[Sound] = []
    pos = 24
    for _ in range(count):
        offset, size, _rate, _bits, _ch, kind = struct.unpack_from("<6I", raw, pos)
        pos += 24
        end = raw.index(b"\0", pos)
        out.append(Sound(raw[pos:end].decode("latin-1"), str(dat), offset, size, kind))
        pos = end + 1 + 3
    with _LOCK:
        _CACHE[key] = out
    return out


def sound_dirs(mod) -> List[Path]:
    bases = [Path(mod.data)]
    game = gamepack.game_root_of(mod)
    if game is not None and (Path(game) / "data").is_dir():
        bases.append(Path(game) / "data")
    out: List[Path] = []
    for base in bases:
        found = _ci(base, "sounds")
        if found is not None and found.is_dir() and found not in out:
            out.append(found)
    return out


def pack_index(mod) -> Dict[str, Sound]:
    index: Dict[str, Sound] = {}
    for folder in reversed(sound_dirs(mod)):
        stock = [_ci(folder, stem + ".idx") for stem in PACKS]
        stock = [p for p in stock if p is not None]
        seen = {p.name.lower() for p in stock} | {"events.idx"}
        try:
            more = sorted((c for c in folder.iterdir()
                           if c.suffix.lower() == ".idx" and c.name.lower() not in seen),
                          key=lambda c: c.name)
        except OSError:
            more = []
        for idx in stock + more:
            try:
                records = read_pack(idx)
            except (OSError, ValueError, struct.error):
                continue
            for rec in records:
                index[rec.name.lower().replace("\\", "/")] = rec
    return index


def loose_path(mod, rel: str) -> Optional[Path]:
    rel = rel.replace("\\", "/")
    if rel[:5].lower() == "data/":
        rel = rel[5:]
    parts = [p for p in rel.split("/") if p]
    game = gamepack.game_root_of(mod)
    roots = [Path(mod.data)]
    if game is not None:
        roots.append(Path(game) / "data")
    for root in roots:
        cur: Optional[Path] = root
        for part in parts:
            cur = _ci(cur, part)
            if cur is None:
                break
        if cur is not None and cur.is_file():
            return cur
    return None


def sound_bytes(mod, rel: str, index=None) -> Optional[bytes]:
    try:
        loose = loose_path(mod, rel)
        if loose is not None:
            return loose.read_bytes()
        if index is None:
            index = pack_index(mod)
        rec = index.get(rel.lower().replace("\\", "/"))
        return rec.read() if rec is not None else None
    except OSError:
        return None


def wav_info(data: bytes):
    if len(data) < 36 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if cid == b"fmt " and size >= 16 and pos + 24 <= len(data):
            fmt, ch, rate, _brate, _align, bits = struct.unpack_from("<HHIIHH", data, pos + 8)
            return fmt, ch, rate, bits
        pos += 8 + size + (size & 1)
    return None


def content_type(data) -> str:
    return "audio/wav" if data[:4] == b"RIFF" else "audio/mpeg"


def _files(lines: List[str]) -> List[List[str]]:
    """The sound files of each event ... end block of some bank lines."""
    events: List[List[str]] = []
    cur: Optional[List[str]] = None
    folder = ""
    for raw in lines:
        s = raw.split(";", 1)[0].strip()
        if not s:
            continue
        low = s.lower()
        if low == "event" or low.startswith("event "):
            cur, folder = [], ""
        elif low == "end":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is None:
            continue
        elif low.startswith("folder "):
            folder = s[7:].strip().replace("\\", "/")
        elif low.endswith((".wav", ".mp3")):
            cur.append(f"{folder}/{s}" if folder else s)
    return events


# ---------------------------------------------------------------------------
# what a unit says


def _bank_path(mod) -> Path:
    return Path(mod.data) / sounds.EDS_REL


def _no_bank() -> VoiceError:
    return VoiceError(_i18n.msg("eng.voices.no_bank", "this mod has no {rel}", rel=sounds.EDS_REL))


def _flat(bank, start, end) -> List[str]:
    return [f for ev in _files(bank.lines[start:end]) for f in ev]


def unit_view(mod, unit_type: str, pick: str = "") -> dict:
    unit = next((u for u in mod.edu.units if u.type == unit_type), None)
    if unit is None:
        raise VoiceError(_i18n.msg("eng.voices.no_unit", "no unit {unit} in this mod", unit=unit_type))
    path = _bank_path(mod)
    if not path.is_file():
        raise _no_bank()
    bank = sounds.parse_file(path)
    accent, vclass = sounds.unit_voice_fields(unit)
    index = pack_index(mod)

    def mark(rels):
        return [{"rel": r, "found": loose_path(mod, r) is not None or r.lower() in index} for r in rels]

    calls = [{"accent": e.accent, "class": e.voice_class, "shared": len(e.names) > 1,
              "files": mark(_flat(bank, e.start, e.end))}
             for e in bank.unit_entries() if unit_type in e.names]
    heard = pick or accent or (calls[0]["accent"] if calls else "")
    heard_class = vclass or (calls[0]["class"] if calls else "")
    orders = []
    for v in bank.vocals:
        if len(orders) >= 40:
            break
        if v.vocal == sounds.UNIT_SELECT or v.accent != heard:
            continue
        if heard_class and v.voice_class != heard_class:
            continue
        events = _files(bank.lines[v.start:v.end])
        if events:
            orders.append({"vocal": v.vocal, "accent": v.accent, "class": v.voice_class,
                           "files": mark(events[0][:6])})
    return {"unit": unit_type, "accent": accent, "class": vclass, "calls": calls,
            "heard": heard, "heard_class": heard_class, "orders": orders,
            "accents": bank.accents(), "classes": bank.classes(),
            "pairs": [list(p) for p in bank.class_pairs()], "packs": bool(index)}


# ---------------------------------------------------------------------------
# a name call of one's own


def _slug(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "_".join(words).lower() or "unit"


def _no_template(accent, vclass) -> VoiceError:
    return VoiceError(_i18n.msg(
        "eng.voices.no_template",
        "no unit in {accent}, class {vclass} has a name call to copy the layout of",
        accent=accent, vclass=vclass))


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _layout(bank, entry, accent, vclass):
    """(unit indent, event indent, folder indent, file indent, end indent, eol)."""
    lines = bank.lines[entry.start:entry.end]
    ev = fo = fi = en = None
    for ln in lines[1:]:
        s = ln.split(";", 1)[0].strip()
        low = s.lower()
        if ev is None:
            if low == "event" or low.startswith("event "):
                ev = _indent(ln)
            continue
        if low == "end":
            en = _indent(ln)
            break
        if low.startswith("folder ") and fo is None:
            fo = _indent(ln)
        elif low.endswith((".wav", ".mp3")) and fi is None:
            fi = _indent(ln)
    if ev is None or en is None:
        raise _no_template(accent, vclass)
    first = lines[0]
    eol = "\r\n" if first.endswith("\r\n") else "\n"
    return _indent(first), ev, fo or ev + "\t", fi or ev + "\t", en, eol


def plan_name_call(mod, unit_type, accent, vclass, wavs) -> dict:
    path = _bank_path(mod)
    if not path.is_file():
        raise _no_bank()
    if not wavs:
        raise VoiceError(_i18n.msg("eng.voices.no_wav", "pick at least one .wav file"))
    bank = sounds.parse_file(path)
    block = bank.unit_select(accent, vclass)
    if block is None:
        raise VoiceError(_i18n.msg(
            "eng.voices.no_block",
            "the voice bank has no Unit_Select names for {accent}, class {vclass}; pick another accent or class",
            accent=accent, vclass=vclass))
    units_here = [e for e in block.entries if e.kind == "unit"]
    same = [e for e in bank.unit_entries() if e.accent == accent and e.voice_class == vclass]
    template = units_here[0] if units_here else (same[0] if same else None)
    if template is None:
        raise _no_template(accent, vclass)
    ind_unit, ind_ev, ind_folder, ind_file, ind_end, eol = _layout(bank, template, accent, vclass)

    infos = []
    for label, data in wavs:
        info = wav_info(data)
        if info is None:
            raise VoiceError(_i18n.msg(
                "eng.voices.not_wav",
                "{label} is not a .wav file; the game's voices are wav, so save it as wav first", label=label))
        infos.append(info)
    warnings = []
    for (label, _d), (fmt, ch, rate, bits) in zip(wavs, infos):
        if fmt == 1 and (ch, rate, bits) != (1, 22050, 16):
            warnings.append(_i18n.msg(
                "eng.voices.odd_format",
                "{label} is {rate} Hz, {bits}-bit, {ch} channel(s); the game's own voices are 22050 Hz, 16-bit, mono, so it may sound off in the game",
                label=label, rate=rate, bits=bits, ch=ch))

    index = pack_index(mod)
    base = f"{_slug(accent).title()}_{vclass}_name_{_slug(unit_type)}_custom_"
    names: List[str] = []
    k = 0
    for _ in wavs:
        while True:
            k += 1
            name = f"{base}{k}.wav"
            rel = f"{VOICE_FOLDER}/{name}"
            if rel.lower() not in index and name not in names and loose_path(mod, rel) is None:
                break
        names.append(name)

    new = [f"{ind_unit}unit {unit_type}{eol}", f"{ind_ev}event{eol}",
           f"{ind_folder}folder {VOICE_FOLDER}{eol}"]
    new += [f"{ind_file}{n}{eol}" for n in names]
    new.append(f"{ind_end}end{eol}")

    existing = next((e for e in units_here if unit_type in e.names), None) \
        or next((e for e in same if unit_type in e.names), None)
    lines = list(bank.lines)
    files = ", ".join(names)
    changes = []
    if existing is not None and existing.names == [unit_type]:
        lines[existing.start:existing.end] = new
        changes.append(_i18n.msg(
            "eng.voices.replaced", "{accent}, class {vclass}: the name call of {unit} now plays {files}",
            accent=accent, vclass=vclass, unit=unit_type, files=files))
    else:
        if existing is not None:
            others = [n for n in existing.names if n != unit_type]
            old = lines[existing.start]
            sep = ", " if ", " in old else ","
            lines[existing.start] = f"{_indent(old)}unit {sep.join(others)}{eol}"
            lines[existing.end:existing.end] = new
            changes.append(_i18n.msg(
                "eng.voices.split",
                "{accent}, class {vclass}: {unit} taken out of the line it shared with {others}",
                accent=accent, vclass=vclass, unit=unit_type, others=", ".join(others[:3])))
        else:
            at = sounds._insert_at(block, None)
            lines[at:at] = new
        changes.append(_i18n.msg(
            "eng.voices.added", "{accent}, class {vclass}: {unit} gets its own name call, {files}",
            accent=accent, vclass=vclass, unit=unit_type, files=files))

    compiled = []
    sdir = _ci(Path(mod.data), "sounds")
    if sdir is not None:
        for nm in ("events.dat", "events.idx"):
            got = _ci(sdir, nm)
            if got is not None:
                compiled.append(str(got))
    return {"unit": unit_type, "accent": accent, "class": vclass, "text": "".join(lines),
            "files": [(n, d) for n, (_l, d) in zip(names, wavs)], "changes": changes,
            "warnings": warnings, "compiled": compiled}


def apply_name_call(mod, p: dict) -> dict:
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def backup(target: Path, rel: str) -> None:
        if target.exists():
            dest = backup_root / "data" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(target, dest)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, "-> backup")
        else:
            manifest["created"].append(rel)

    for name, raw in p["files"]:
        rel = f"sounds/Voice/Human/Localized/Battle_Map/{name}"
        target = data / rel
        backup(target, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        file_op("WRITE", target, f"{len(raw)} bytes")
    target = data / sounds.EDS_REL
    backup(target, sounds.EDS_REL)
    target.write_text(p["text"], encoding=sounds.ENCODING)
    file_op("WRITE", target, "name call")
    for c in p["compiled"]:
        c = Path(c)
        rel = os.path.relpath(c, data).replace("\\", "/")
        if c.exists():
            backup(c, rel)
            c.unlink()
            file_op("DELETE", c, "the game rebuilds it from the text")

    rec = {
        "id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "sounds",
        "action": "name call", "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root), "unit_type": p["unit"],
        "resolved_type": p["unit"], "options": {}, "applied": True, "undone": False,
        "note": "", "summary": "\n".join(str(c) for c in p["changes"]),
        "warnings": list(p["warnings"]), "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("VOICE  name call for %s in %s, id=%s", p["unit"], mod.name, tid)
    mod.__dict__.pop("sounds", None)
    return rec
