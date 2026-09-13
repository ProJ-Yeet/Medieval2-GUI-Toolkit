"""Parser for data/text/export_units.txt (M2TW unit localisation).

UTF-16 LE (BOM ff fe). Records are separated by a line ``¬-----`` (the ``¬``
character, U+00AC, also begins comment lines). Each unit contributes three keys:

    {<dict>}<Localized Name>
    {<dict>_descr}
    <long description - on the FOLLOWING line(s)>
    {<dict>_descr_short}
    <short description - on the FOLLOWING line(s)>

IMPORTANT: a key's value is whatever follows on the same line PLUS every
subsequent line up to the next ``{key}`` or ``¬`` line. In practice the name sits
on the key line while the descriptions sit on the lines after it, so reading only
the key line yields an empty description.

``data/text/export_buildings.txt`` is the same format with a different suffix -
``_desc`` / ``_desc_short`` rather than ``_descr`` / ``_descr_short`` - so every
entry point here takes a ``descr_suffix``. The two never collide: a key ending in
``_descr`` does not end in ``_desc``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ENCODING = "utf-16"          # Python picks LE/BE from the BOM on read
SEPARATOR = "¬-----"    # ¬-----
NOT = "¬"               # ¬

_ENTRY_RE = re.compile(r"^\{([^}]*)\}(.*)$")


@dataclass
class LocEntry:
    name: str = ""
    descr: Optional[str] = None
    descr_short: Optional[str] = None


@dataclass
class Localization:
    entries: Dict[str, LocEntry] = field(default_factory=dict)
    _lines: List[str] = field(default_factory=list)   # original lines (no line endings)
    _newline: str = "\r\n"

    def get(self, dictionary: str) -> Optional[LocEntry]:
        return self.entries.get(dictionary)

    def record_text(self, dictionary: str) -> str:
        """Build a fresh 3-line record block for a dictionary key."""
        e = self.entries.get(dictionary)
        if e is None:
            return ""
        nl = self._newline
        out = SEPARATOR + nl
        out += "{" + dictionary + "}" + (e.name or "") + nl
        out += "{" + dictionary + "_descr}" + (e.descr or "") + nl
        out += "{" + dictionary + "_descr_short}" + (e.descr_short or "") + nl
        return out


def parse_text(text: str, descr_suffix: str = "_descr") -> Localization:
    # normalise: detect newline style, split on \n keeping content
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split("\n")
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in lines]

    entries: Dict[str, LocEntry] = {}
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].strip("﻿").strip()
        if not line or line.startswith(NOT):
            i += 1
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2)
        # gather continuation lines: everything until the next key or ¬ line
        j = i + 1
        cont: List[str] = []
        while j < n:
            s = lines[j].strip("﻿").strip()
            if s.startswith("{") or s.startswith(NOT):
                break
            cont.append(lines[j])
            j += 1
        while cont and not cont[-1].strip():        # drop trailing blank lines
            cont.pop()
        full = value + ("\n" + "\n".join(cont) if cont else "")
        full = full.strip() if not value.strip() else full

        short_suffix = descr_suffix + "_short"
        if key.endswith(short_suffix):
            entries.setdefault(key[: -len(short_suffix)], LocEntry()).descr_short = full
        elif key.endswith(descr_suffix):
            entries.setdefault(key[: -len(descr_suffix)], LocEntry()).descr = full
        else:
            entries.setdefault(key, LocEntry()).name = full
        i = j
    return Localization(entries=entries, _lines=lines, _newline=newline)


def read_file(path: str | Path) -> Tuple[str, str]:
    """``(text, encoding)`` - the file, and what it turned out to be.

    The game reads these as UTF-16 with a BOM and nothing else, but a person who
    opens one in Notepad and saves it gets UTF-8, and a mod ships like that. The
    file is then unreadable to the game AND, until this, to us: ``ENCODING`` on
    a file with no BOM raises out of the codec, and :attr:`Mod.loc` is warmed
    inside the registry lock on the way into ``/api/units``, so one mis-saved
    file took the whole unit list down and the transfer composer with it.

    The encoding comes back because a save has to write the file the way it was
    found. Rewriting a mis-saved file as UTF-16 would be a repair nobody asked
    for, made in passing, on a file the caller is editing one line of.
    """
    p = Path(path)
    with p.open("rb") as fh:
        head = fh.read(3)
    # Off the mark rather than by trying codecs in turn, because the mark is
    # what decides how it is written BACK: `utf-8-sig` reads a file with no BOM
    # perfectly well and then puts one in on the way out, which is a byte the
    # mod author did not have.
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        order = ("utf-16",)
    elif head == b"\xef\xbb\xbf":
        order = ("utf-8-sig",)
    else:
        order = ("utf-8",)
    for enc in order:
        try:
            return p.read_text(encoding=enc), enc
        except UnicodeError:
            break
    return p.read_text(encoding="latin-1"), "latin-1"   # decodes any byte


def save_encoding(text: str, read_as: str) -> str:
    """What to actually write with, given what the file was read as.

    Almost always what it was read as - see :func:`read_file`. The exception is
    a file that was 8-bit and an edit that puts a character in it 8 bits cannot
    hold, where writing it back as found is not "as found", it is a crash on
    save. UTF-16 is what the game wanted from that file anyway.
    """
    if read_as == ENCODING:
        return ENCODING
    try:
        text.encode(read_as)
    except UnicodeEncodeError:
        return ENCODING
    return read_as


def encoding_warning(path: str | Path, read_as: str, save_as: str) -> str:
    """What to tell a person whose loc file is not UTF-16. ``""`` if it is.

    Said on a SAVE rather than on the read, because the read happens on every
    page load and this is only news when the file is about to be written.
    """
    if read_as == ENCODING:
        return ""
    name = Path(path).name
    said = (f"{name} is {read_as}, not UTF-16 with a BOM, and the game reads "
            f"only UTF-16 here - so none of this file's text reaches it. ")
    return said + (
        "Written back as it was found rather than converted in passing."
        if save_as == read_as else
        f"The new text has characters {read_as} cannot hold, so it is saved as "
        f"UTF-16, which is what the game wanted from it anyway.")


def parse_file(path: str | Path, descr_suffix: str = "_descr") -> Localization:
    return parse_text(read_file(path)[0], descr_suffix)


def upsert_record(text: str, key: str, name: str, descr: str = "",
                  descr_short: str = "", descr_suffix: str = "_descr") -> str:
    """Replace the {key}/{key_descr}/{key_descr_short} lines in ``text`` in place,
    or append a fresh record block if the key is not present.
    """
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split("\n")
    trimmed = [ln[:-1] if ln.endswith("\r") else ln for ln in lines]

    # Replace each key's FULL span (its line + continuation lines); replacing only
    # the key line would strand the previous description underneath it.
    short_suffix = descr_suffix + "_short"
    blocks = [("{" + key + "}", _emit(key, name, inline=True)),
              ("{" + key + descr_suffix + "}", _emit(key + descr_suffix, descr)),
              ("{" + key + short_suffix + "}", _emit(key + short_suffix, descr_short))]
    found = False
    for marker, new_lines in blocks:
        span = _key_span(trimmed, marker)
        if span is None:
            continue
        start, end = span
        trimmed[start:end] = new_lines
        found = True
    if found:
        return nl.join(trimmed)

    # append a fresh record
    if not text.endswith("\n"):
        text += nl
    out = [SEPARATOR]
    for marker, new_lines in blocks:
        out.extend(new_lines)
    return text + nl.join(out) + nl


def remove_record(text: str, key: str, descr_suffix: str = "_descr") -> str:
    """Delete a unit's three keys (and the record separator above them).

    Used when a unit is deleted, or when its ``dictionary`` is renamed and the
    old record would otherwise be left orphaned in export_units.txt.
    """
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split("\n")
    trimmed = [ln[:-1] if ln.endswith("\r") else ln for ln in lines]
    spans = []
    for marker in ("{" + key + "}", "{" + key + descr_suffix + "}",
                   "{" + key + descr_suffix + "_short}"):
        span = _key_span(trimmed, marker)
        if span:
            spans.append(span)
    if not spans:
        return text
    start = min(s for s, _ in spans)
    end = max(e for _, e in spans)
    # swallow a separator line sitting directly above the record
    while start > 0 and trimmed[start - 1].strip().startswith(SEPARATOR):
        start -= 1
    del trimmed[start:end]
    return nl.join(trimmed)


def _emit(key: str, value: Optional[str], inline: bool = False) -> List[str]:
    """Lines for one keyed entry.

    The name goes on the key line; descriptions go on the following line(s),
    matching how M2TW's own export_units.txt is laid out.
    """
    val = (value or "").strip("\r\n")
    if inline:
        return ["{" + key + "}" + val.replace("\n", " ")]
    if not val:
        return ["{" + key + "}"]
    return ["{" + key + "}"] + val.split("\n")


def _key_span(lines: List[str], marker: str):
    """(start, end) covering ``marker``'s line and its continuation lines."""
    for i, ln in enumerate(lines):
        if ln.strip("﻿").strip().startswith(marker):
            j = i + 1
            while j < len(lines):
                s = lines[j].strip("﻿").strip()
                if s.startswith("{") or s.startswith(NOT):
                    break
                j += 1
            return i, j
    return None
