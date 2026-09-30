"""M2EX's text battle models: ``data/descr_model_battle.txt`` (Phase 92a).

An M2EX mod can read its battle models from this text file instead of
``unit_models/battle_models.modeldb``, switched on by ``model_battle_source
text`` in the mod's own ``data/descr_caps_ex.txt``. M2EX's file says the
default for mods is the ``.modeldb``, so a mod without the line, or without the
file, reads the ``.modeldb``, and the M2EX tick on its own says nothing about
it. On such a mod a transfer that wrote the ``.modeldb`` wrote models the game
never reads.

**Measured on M2EX's own files** (the base game's ``descr_model_battle.txt``,
11,250 lines and 701 models, "generated from battle_models.modelDB", CRLF,
ASCII, ``;`` comments), not guessed:

* an entry is ``type <name>`` then its lines, to a blank line:
  ``scale <float>`` (7 of 701 write it; 1 when absent),
  ``skeleton <primary>, <secondary>`` with ``skeleton_attachment_primary`` and
  ``_secondary`` lines under it (one per weapon skeleton), the same again as
  ``skeleton_horse``, ``skeleton_camel`` and ``skeleton_elephant`` for the
  other mount types, ``mesh <path>, <distance>`` per LOD,
  ``texture <faction>, <diffuse>, <normal>, <sprite>``,
  ``texture_attachments <faction>, <diffuse>, <normal>`` and
  ``torch <bone>, <six offsets>`` (677 of 701; none means no torch);
* **a mesh distance is the square root of the ``.modeldb``'s.** Tsardoms'
  ``.modeldb`` holds 953 of its 1,015 LOD distances as perfect squares (6400,
  121, 900...), and the text's are 80, 11, 30, 50, 35, 100. A ``.modeldb``
  distance that is not a square (1200, 9400) is written rounded, the one thing
  a round trip through text changes;
* the first skeleton block is written ``skeleton`` whatever its mount type, the
  rest ``skeleton_<type>``: a foot soldier with mounted variants is
  ``skeleton`` + ``skeleton_horse``..., a knight only ``skeleton``. So reading
  text back into a ``.modeldb`` has to be told the first block's type: the
  units that use the model say it (:func:`read_db`), ``horse`` for a mounted
  unit and ``none`` otherwise.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import modeldb as mdb

CAPS_REL = "descr_caps_ex.txt"
TEXT_REL = "descr_model_battle.txt"
ENCODING = "latin-1"
MOUNT_KEYS = {"skeleton_horse": "horse", "skeleton_camel": "camel",
              "skeleton_elephant": "elephant"}
_CAPS = re.compile(r"^\s*model_battle_source\s+(\S+)", re.M | re.I)


def reads_text(mod) -> bool:
    """Does this mod read ``descr_model_battle.txt``? Its own caps file decides."""
    data = getattr(mod, "data", None)
    path = Path(data if data is not None else Path(mod) / "data") / CAPS_REL
    if not path.is_file():
        return False
    text = "\n".join(ln.split(";", 1)[0] for ln in
                     path.read_text(encoding=ENCODING, errors="replace").splitlines())
    m = None
    for m in _CAPS.finditer(text):
        pass
    return bool(m and m.group(1).lower() == "text")


def text_path(mod) -> Path:
    return Path(mod.data) / TEXT_REL


def _vals(rest: str) -> List[str]:
    return [v.strip() for v in rest.split(",")]


def parse(text: str) -> List[mdb.ModelEntry]:
    """Every entry, in file order. The first skeleton block's mount type is
    ``""`` (the file does not say it; see :func:`read_db`). ``raw`` is the
    entry's own text."""
    out: List[mdb.ModelEntry] = []
    cur: Optional[mdb.ModelEntry] = None
    lines: List[str] = []

    def close():
        nonlocal cur, lines
        if cur is not None:
            cur.raw = "\n".join(lines).rstrip() + "\n"
            out.append(cur)
        cur, lines = None, []

    for line in text.splitlines():
        body = line.split(";", 1)[0].strip()
        if not body:
            if cur is not None and not line.strip():
                close()
            continue
        parts = body.split(None, 1)
        key, rest = parts[0].lower(), (parts[1].strip() if len(parts) > 1 else "")
        if key == "type":
            close()
            cur = mdb.ModelEntry(rest.lower(), 1.0, [], [], [], [], -1, [0.0] * 6)
            lines = [line]
            continue
        if cur is None:
            continue
        lines.append(line)
        v = _vals(rest)
        if key == "scale":
            cur.scale = float(v[0])
        elif key == "skeleton" or key in MOUNT_KEYS:
            cur.animations.append(mdb.Animation(
                MOUNT_KEYS.get(key, ""), v[0], v[1] if len(v) > 1 else "", [], []))
        elif key == "skeleton_attachment_primary" and cur.animations:
            cur.animations[-1].pri_weapons.append(v[0])
        elif key == "skeleton_attachment_secondary" and cur.animations:
            cur.animations[-1].sec_weapons.append(v[0])
        elif key == "mesh":
            cur.lods.append((v[0], float(v[1]) if len(v) > 1 and v[1] else 0.0))
        elif key == "texture":
            cur.main_textures.append(mdb.Texture(v[0].lower(), v[1] if len(v) > 1 else "",
                                                 v[2] if len(v) > 2 else "",
                                                 v[3] if len(v) > 3 else ""))
        elif key == "texture_attachments":
            cur.attach_textures.append(mdb.Texture(v[0].lower(), v[1] if len(v) > 1 else "",
                                                   v[2] if len(v) > 2 else "", ""))
        elif key == "torch":
            cur.torch_index = int(float(v[0]))
            cur.torch = [float(x) for x in (v[1:] + ["0"] * 6)[:6]]
    close()
    return out


def _num(x: float) -> str:
    return format(x, "g")


def _dist_to_text(d) -> str:
    """A text distance (already the root), written whole, as every one of M2EX's is."""
    return str(int(round(float(d))))


def render(e: mdb.ModelEntry) -> str:
    """One entry as text, the way M2EX writes it: tab-aligned keys, the first
    skeleton block as ``skeleton``.

    Every value is stripped: a ``.modeldb`` string is length-prefixed and can
    hold a newline (Reforged's has a ``MTW2_Mace_Primary`` with one in it), which
    a line of text cannot."""
    t = lambda v: (v or "").strip()  # noqa: E731
    e = mdb.ModelEntry(
        t(e.name), e.scale, [(t(m), d) for m, d in e.lods],
        [mdb.Texture(t(x.faction), t(x.texture), t(x.normal), t(x.sprite)) for x in e.main_textures],
        [mdb.Texture(t(x.faction), t(x.texture), t(x.normal), "") for x in e.attach_textures],
        [mdb.Animation(t(a.mount_type), t(a.primary_skeleton), t(a.secondary_skeleton),
                       [t(w) for w in a.pri_weapons], [t(w) for w in a.sec_weapons])
         for a in e.animations], e.torch_index, e.torch)
    out = [f"type\t\t\t\t{e.name}"]
    if abs(e.scale - 1.0) > 1e-9:
        out.append(f"scale\t\t\t\t{_num(e.scale)}")
    for i, a in enumerate(e.animations):
        key = "skeleton" if i == 0 else f"skeleton_{a.mount_type or 'horse'}"
        out.append(f"{key}\t\t\t{a.primary_skeleton}, {a.secondary_skeleton}".rstrip())
        out += [f"skeleton_attachment_primary\t{w}" for w in a.pri_weapons]
        out += [f"skeleton_attachment_secondary\t{w}" for w in a.sec_weapons]
    out += [f"mesh\t\t\t\t{m}, {_dist_to_text(d)}" for m, d in e.lods]
    out += [f"texture\t\t\t\t{t.faction}, {t.texture}, {t.normal}, {t.sprite}".rstrip(", ")
            for t in e.main_textures]
    out += [f"texture_attachments\t\t{t.faction}, {t.texture}, {t.normal}"
            for t in e.attach_textures]
    if e.torch_index >= 0:
        out.append("torch\t\t\t\t" + ", ".join([str(e.torch_index)] + [_num(x) for x in e.torch]))
    return "\r\n".join(out) + "\r\n"


def _s(v: str) -> str:
    return f"{len(v)} {v}" if v else "0"


def entry_raw(e: mdb.ModelEntry) -> str:
    """One entry in ``.modeldb`` form, for everything that works on raw entries
    (transfer's rename, relocation and texture records). ``e`` is in
    ``.modeldb`` distances; an unknown first mount type is ``none``."""
    b = [f" \n{_s(e.name)} \n{_num(e.scale)} {len(e.lods)} "]
    for m, d in e.lods:
        b.append(f"\n{_s(m)} {int(round(float(d)))} ")
    b.append(f"\n{len(e.main_textures)} ")
    for t in e.main_textures:
        b.append(f"\n{_s(t.faction)} \n{_s(t.texture)} \n{_s(t.normal)} {_s(t.sprite)} ")
    b.append(f"\n{len(e.attach_textures)} ")
    for t in e.attach_textures:
        b.append(f"\n{_s(t.faction)} \n{_s(t.texture)} \n{_s(t.normal)} 0 ")
    b.append(f"\n{len(e.animations)} ")
    for a in e.animations:
        b.append(f"\n{_s(a.mount_type or 'none')} \n{_s(a.primary_skeleton)} {_s(a.secondary_skeleton)} ")
        b.append(f"\n{len(a.pri_weapons)} " + "".join(f"\n{_s(w)} " for w in a.pri_weapons))
        b.append(f"\n{len(a.sec_weapons)} " + "".join(f"\n{_s(w)} " for w in a.sec_weapons))
    b.append(f"\n{e.torch_index} " + " ".join(_num(x) for x in e.torch))
    return "".join(b)


def from_modeldb(e: mdb.ModelEntry) -> mdb.ModelEntry:
    """A ``.modeldb`` entry with LOD distances as the text writes them."""
    return mdb.ModelEntry(e.name, e.scale, [(m, math.sqrt(max(float(d), 0.0))) for m, d in e.lods],
                          e.main_textures, e.attach_textures, e.animations,
                          e.torch_index, e.torch, raw="")


def first_mounts(mod) -> Dict[str, str]:
    """``{model: mount type}`` for the models a mounted unit wears: the text
    does not write the first skeleton block's type, the units do."""
    out: Dict[str, str] = {}
    try:
        units = mod.edu.units
    except Exception:
        return out
    for u in units:
        if not getattr(u, "mount", ""):
            continue
        low = u.mount.lower()
        kind = "camel" if "camel" in low else "elephant" if "elephant" in low else "horse"
        for m in [u.soldier_model] + list(getattr(u, "officers", []) or []):
            if m:
                out.setdefault(m.lower(), kind)
    return out


def read_db(mod, mounts: Optional[Callable[[], Dict[str, str]]] = None) -> mdb.ModelDb:
    """The text file as a :class:`~unittransfer.modeldb.ModelDb`, each entry
    with ``.modeldb`` distances and a ``raw`` in ``.modeldb`` form, so every
    reader of models works on it unchanged."""
    text = text_path(mod).read_text(encoding=ENCODING, errors="replace")
    firsts = (mounts or (lambda: first_mounts(mod)))()
    entries = []
    for e in parse(text):
        if e.animations and not e.animations[0].mount_type:
            only = len(e.animations) == 1
            e.animations[0].mount_type = firsts.get(e.name, "none") if only else "none"
        conv = mdb.ModelEntry(e.name, e.scale, [(m, int(round(float(d) ** 2))) for m, d in e.lods],
                              e.main_textures, e.attach_textures, e.animations,
                              e.torch_index, e.torch)
        conv.raw = entry_raw(conv)
        entries.append(conv)
    return mdb.ModelDb(header_ints=[], blank_raw="", entries=entries)


def append(text: str, entries: List[mdb.ModelEntry]) -> str:
    """The file with these entries added at the end, a blank line before each,
    in its own line endings. An entry is in ``.modeldb`` distances."""
    nl = "\r\n" if "\r\n" in text else "\n"
    blocks = [render(from_modeldb(e)).replace("\r\n", nl) for e in entries]
    body = text.rstrip("\r\n")
    return body + nl + nl + (nl).join(blocks)
