"""A raw text editor for the files the toolkit reads (Phase 21, D11).

Every editor here is a parser with a form on top, and every one of them is
honest about the edges of its model: the Code View shows one record as the file
stores it, the campaign screens splice only the lines their plan names, and a
line a parser does not recognise is kept and reported rather than dropped. What
none of them can do is let somebody fix the line the parser does not model -
and the mod that does something this toolkit has never seen is not a rare case,
it is every mod eventually. So this is **the escape hatch**: pick a file, edit
its text, save.

**It is still a save like every other save here.** The one rule this phase was
given is the one thing the module is built around: a raw write goes through the
backup set and the log, so the Log's Undo reverses it exactly as it reverses a
paint stroke or a faction clone. An editor that writes straight to disk is the
one thing in this toolkit that could lose somebody's mod.

Three other things a textarea would get wrong and this does not:

* **The bytes come back as they went in.** A file is decoded with the codec its
  own first bytes name - a UTF-16 byte-order mark for the ``text/`` files, UTF-8
  when that is what the bytes are, Latin-1 for the rest, which is what every
  parser here reads - and :func:`read` refuses to offer a file for editing if
  decoding and re-encoding it does not reproduce it byte for byte.
* **The line endings stay the file's.** A browser's text box turns every line
  ending into ``\\n``, and a game file is not obliged to be consistent: Third
  Age Reforged's ``descr_projectile.txt`` is 3,353 CRLF lines and five lone LFs.
  :func:`splice` diffs the edit against the original lines and gives every line
  that was not touched its own ending back, so a save is byte-exact outside the
  lines it changed - the same promise every splice in the campaign editor makes.
  A line rewritten in place keeps its own ending too; only a line that is new
  takes the file's commoner one.
* **Somebody else's write is not overwritten.** :func:`read` hands out a
  signature of the bytes, and a save whose signature no longer matches the disk
  is refused. This is a local app, but the file may be open in Notepad++ too,
  and "the last save wins" is how a morning's work disappears.

**It says what the toolkit makes of the result, and never refuses on it.**
Where the file has a reader here - ``descr_strat.txt``, ``descr_regions.txt``,
``descr_win_conditions.txt``, the roster, the EDU - :func:`plan` reads the file
before and after and reports anything the reader now objects to that it did not
before. A warning, not a refusal: the whole point of an escape hatch is that it
opens when the parser is the one that is wrong.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

#: What a file must end in to be offered. `.modeldb` is deliberately not here:
#: its strings are length-prefixed and counted, so a hand edit that changes a
#: path's length breaks every record after it - that file has its own editor.
TEXT_SUFFIXES = (".txt", ".xml")

#: Bigger than this is listed and not opened. A browser text box holding the
#: 9.5 MB ``descr_skeleton.txt`` Divide and Conquer ships is a tab that stops
#: responding; the largest file any screen here edits (DaC's EDB) is 1.7 MB.
MAX_BYTES = 4 * 1024 * 1024

#: How much of the change a plan spells out. The count is always whole.
PREVIEW_HUNKS = 40


class RawError(Exception):
    pass


# ---------------------------------------------------------------------------
# which files


#: Where the toolkit reads text files from, as (group label, folder under data/,
#: recurse). The campaign folders are added per campaign by :func:`files`.
ROOTS: Tuple[Tuple[str, str, bool], ...] = (
    ("Mod files", "", False),
    ("Map", "world/maps/base", False),
    ("Text", "text", False),
)
CAMPAIGN_ROOT = "world/maps/campaign"

#: Where :data:`modfiles.KNOWN`'s first module is not the screen a person means:
#: it lists the roster under Buildings (which reads it for cultures) and the EDU
#: under Unit Transfer (which reads it to move units), and the page offers one
#: link per file, so it should be the one that edits the file.
PREFER: Dict[str, Tuple[str, str]] = {
    "descr_sm_factions.txt": ("factions", "Factions"),
    "export_descr_unit.txt": ("edit", "Unit Editor"),
}


def _screen_for(rel: str) -> Tuple[str, str]:
    """``(mode, label)`` of the screen that edits this file properly, or blanks.

    Read off :data:`modfiles.KNOWN` - the Home page's list of every file a
    module reads - so a module that starts reading a file is offered here
    without a second list to keep in step. A campaign file is matched by its
    name, because KNOWN spells only imperial_campaign's path.
    """
    from . import modfiles
    name = rel.rsplit("/", 1)[-1].lower()
    if name in PREFER and "/" not in rel:
        return PREFER[name]
    in_camp = rel.lower().startswith(CAMPAIGN_ROOT + "/")
    for k in modfiles.KNOWN:
        if k.folder:
            continue
        krel = k.rel.lower()
        # a campaign folder may carry its own copy of a base map file (B1's
        # finding), and the map screen reads that copy for that campaign
        if krel == rel.lower() or (in_camp and "campmap" in k.modules
                                   and krel.rsplit("/", 1)[-1] == name):
            mode = k.modules[0]
            # a text/ file is the Strings screen's, whoever else reads it -
            # except the campaign's menu text, which 18a put on the map
            if rel.lower().startswith("text/") and mode != "campmap":
                break
            return mode, modfiles.MODULES.get(mode, mode)
    if rel.lower().startswith("text/"):
        return "strings", modfiles.MODULES["strings"]
    return "", ""


def _allowed(rel: str) -> bool:
    """Is ``rel`` one of the files :func:`files` would list? Checked again on
    every read and save, because the path arrives from the page."""
    rel = rel.replace("\\", "/")
    if not rel or rel.startswith("/") or ".." in rel.split("/") or ":" in rel:
        return False
    if not rel.lower().endswith(TEXT_SUFFIXES):
        return False
    folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
    if folder.lower().startswith(CAMPAIGN_ROOT + "/"):
        return True
    return any(folder.lower() == root.lower() for _, root, _ in ROOTS)


def files(mod) -> Dict:
    """Every text file the toolkit reads, grouped, lightest first.

    Stat'ed, never opened: this is the picker, and a picker that read a dozen
    megabytes to draw itself would be the slowest screen in the toolkit.
    """
    from . import campstrat
    data = Path(mod.data)
    groups: List[Dict] = []

    def add(label: str, folder: Path, recurse: bool = False) -> None:
        if not folder.is_dir():
            return
        rows = []
        walk = folder.rglob("*") if recurse else folder.iterdir()
        for p in sorted(walk, key=lambda x: x.as_posix().lower()):
            if not p.is_file() or not p.name.lower().endswith(TEXT_SUFFIXES):
                continue
            rel = p.relative_to(data).as_posix()
            size = p.stat().st_size
            mode, screen = _screen_for(rel)
            rows.append({"rel": rel, "name": rel[len(folder.relative_to(data).as_posix()) + 1:]
                         if folder != data else rel,
                         "size": size, "mode": mode, "screen": screen,
                         "too_big": size > MAX_BYTES})
        if rows:
            groups.append({"label": label, "files": rows})

    try:
        camps = campstrat.campaign_paths(mod)
    except OSError:
        camps = []
    for camp in camps:
        add(f"Campaign: {camp}",
            data / campstrat.CAMPAIGN_DIR_REL / campstrat.campaign_rel(camp))
    for label, root, recurse in ROOTS:
        add(label, data / root if root else data, recurse)
    return {"mod": getattr(mod, "name", ""), "groups": groups,
            "max_bytes": MAX_BYTES,
            "count": sum(len(g["files"]) for g in groups)}


# ---------------------------------------------------------------------------
# the bytes, both ways


@dataclass
class Codec:
    name: str                      # what Python calls it
    bom: bytes = b""
    label: str = ""                # what the page says


def sniff(raw: bytes) -> Codec:
    """The codec a file's own bytes ask for. See the module docstring."""
    if raw[:2] == b"\xff\xfe":
        return Codec("utf-16-le", b"\xff\xfe", "UTF-16 LE")
    if raw[:2] == b"\xfe\xff":
        return Codec("utf-16-be", b"\xfe\xff", "UTF-16 BE")
    if raw[:3] == b"\xef\xbb\xbf":
        return Codec("utf-8", b"\xef\xbb\xbf", "UTF-8 with BOM")
    if any(b > 0x7F for b in raw):
        try:
            raw.decode("utf-8")
            return Codec("utf-8", b"", "UTF-8")
        except UnicodeDecodeError:
            pass
    return Codec("latin-1", b"", "Latin-1")


def decode(raw: bytes, codec: Codec) -> str:
    return raw[len(codec.bom):].decode(codec.name)


def encode(text: str, codec: Codec) -> bytes:
    return codec.bom + text.encode(codec.name)


def signature(raw: bytes) -> str:
    return hashlib.sha1(raw).hexdigest()


#: A line ending, any of the three - the same three `keyblock.to_newline` folds
#: into one, which is what the browser's text box does as well.
_EOL = re.compile(r"(\r\n|\n|\r)")


def split_eol(text: str) -> Tuple[List[str], List[str]]:
    """``(contents, endings)``: line ``i`` is ``contents[i] + endings[i]``.

    The last content is whatever follows the last ending - ``""`` when the file
    ends on a newline - and its ending is ``""``. Splitting ``text`` with every
    ending folded to ``\\n`` gives exactly ``contents``, which is the view the
    page edits.
    """
    parts = _EOL.split(text)
    return parts[0::2], parts[1::2] + [""]


def splice(original: str, edited: str) -> Tuple[str, List[Tuple[str, int, int, int, int]]]:
    """``edited`` (``\\n`` line endings, from the page) with the original's own
    endings put back on every line it did not change.

    Returns the new text and the diff's opcodes over the two line lists. The
    common head and tail are peeled off before :class:`difflib.SequenceMatcher`
    sees anything, so a one-line edit in a 60,000-line EDB costs a comparison of
    one line, not a quadratic search.
    """
    old, ends = split_eol(original)
    new = edited.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    nl = "\n" if original.count("\n") - original.count("\r\n") > original.count("\r\n") \
        else "\r\n"
    head = 0
    while head < len(old) and head < len(new) and old[head] == new[head]:
        head += 1
    tail = 0
    while (tail < len(old) - head and tail < len(new) - head
           and old[-1 - tail] == new[-1 - tail]):
        tail += 1
    ops: List[Tuple[str, int, int, int, int]] = []
    if head:
        ops.append(("equal", 0, head, 0, head))
    mid = difflib.SequenceMatcher(None, old[head:len(old) - tail],
                                  new[head:len(new) - tail], autojunk=False)
    for tag, i1, i2, j1, j2 in mid.get_opcodes():
        ops.append((tag, i1 + head, i2 + head, j1 + head, j2 + head))
    if tail:
        ops.append(("equal", len(old) - tail, len(old), len(new) - tail, len(new)))

    out: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            out.extend(zip(old[i1:i2], ends[i1:i2]))
            continue
        # A line rewritten in place keeps the ending it had - the lone LF in a
        # CRLF file is the file's, not ours to normalise - and only a line that
        # is genuinely new takes the file's norm.
        for k, line in enumerate(new[j1:j2]):
            out.append((line, ends[i1 + k] if i1 + k < i2 else nl))
    # every line but the last ends in something; the last ends in nothing,
    # because by construction it is whatever followed the final line ending
    text = "".join(c + (e or nl) for c, e in out[:-1]) + (out[-1][0] if out else "")
    return text, ops


def hunks(original: str, edited_lf: str, ops) -> Tuple[List[Dict], Dict[str, int]]:
    """The change as the confirmation shows it: line numbers in the NEW file,
    the old lines and the new ones. Capped at :data:`PREVIEW_HUNKS`; the counts
    beside them never are."""
    old, _ = split_eol(original)
    new = edited_lf.split("\n")
    out: List[Dict] = []
    counts = {"changed": 0, "added": 0, "removed": 0}
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        a, b = i2 - i1, j2 - j1
        counts["changed"] += min(a, b)
        counts["added"] += max(0, b - a)
        counts["removed"] += max(0, a - b)
        if len(out) < PREVIEW_HUNKS:
            out.append({"at": j1 + 1, "was": old[i1:min(i2, i1 + 8)],
                        "now": new[j1:min(j2, j1 + 8)],
                        "more": max(0, max(a, b) - 8)})
    return out, counts


# ---------------------------------------------------------------------------
# what the toolkit makes of it


def _strat(text: str) -> List[str]:
    from . import campstrat
    return [f"{kind}: {msg}" for _, kind, msg in campstrat.parse_strat(text).problems]


def _regions(text: str) -> List[str]:
    from . import campmap
    return [f"{r.name}: {p}" for r in campmap.parse_regions(text).records
            for p in r.problems]


def _wins(text: str) -> List[str]:
    from . import winconds
    return [msg for _, msg in winconds.parse_wins(text).problems]


def _roster(text: str) -> List[str]:
    from . import factions
    rf = factions.parse_text(text)
    return [f"{len(rf.records)} factions"] + [
        f"{r.name}: {w}" for r in rf.records for w in r.warnings]


def _edu(text: str) -> List[str]:
    from . import edu
    return [f"{len(edu.parse_text(text).units)} units"]


#: file name -> a reader that returns what it objects to (or, for the two
#: record files, how many records it sees - a count that moved is worth saying)
READERS: Dict[str, Tuple[str, Callable[[str], List[str]]]] = {
    "descr_strat.txt": ("The campaign screens", _strat),
    "descr_regions.txt": ("The campaign map", _regions),
    "descr_win_conditions.txt": ("The Winning tab", _wins),
    "descr_sm_factions.txt": ("The Factions screen", _roster),
    "export_descr_unit.txt": ("The unit screens", _edu),
}


def _reader_notes(rel: str, before: str, after: str) -> List[str]:
    hit = READERS.get(rel.rsplit("/", 1)[-1].lower())
    if not hit:
        return []
    who, read = hit
    try:
        was = read(before)
    except Exception as e:                       # it refused the file already
        was = [f"refused: {e}"]
    try:
        now = read(after)
    except Exception as e:
        return [f"{who} will not read the new file: {e}"]
    gone = list(was)
    fresh = []
    for msg in now:                              # a multiset difference, in order
        if msg in gone:
            gone.remove(msg)
        else:
            fresh.append(msg)
    out = [f"{who} now reports: {m}" for m in fresh[:12]]
    if len(fresh) > 12:
        out.append(f"…and {len(fresh) - 12} more")
    return out


# ---------------------------------------------------------------------------
# read, plan, apply


def _path(mod, rel: str) -> Path:
    rel = str(rel or "").replace("\\", "/").strip()
    if not _allowed(rel):
        raise RawError(f"{rel or 'that'} is not a text file this editor opens")
    path = Path(mod.data) / rel
    if not path.is_file():
        raise RawError(f"{getattr(mod, 'name', '?')} has no data/{rel}")
    return path


def read(mod, rel: str) -> Dict:
    """One file as the page edits it: ``\\n`` endings, and what to put back."""
    path = _path(mod, rel)
    raw = path.read_bytes()
    mode, screen = _screen_for(rel)
    out = {"rel": rel, "size": len(raw), "sig": signature(raw), "mode": mode,
           "screen": screen, "text": "", "encoding": "", "newline": "",
           "mixed": False, "lines": 0, "readonly": ""}
    if len(raw) > MAX_BYTES:
        out["readonly"] = (f"{len(raw) / 1048576:.1f} MB is more than a browser text "
                           f"box holds comfortably ({MAX_BYTES // 1048576} MB is the "
                           "limit here)")
        return out
    codec = sniff(raw)
    out["encoding"] = codec.label
    try:
        text = decode(raw, codec)
    except UnicodeDecodeError as e:
        out["readonly"] = f"the bytes are not valid {codec.label}: {e}"
        return out
    if encode(text, codec) != raw:
        out["readonly"] = (f"read as {codec.label} and written back, this file would "
                           "not be the same bytes - so it is shown and not saved")
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    out["newline"] = "LF" if lf > crlf else "CRLF"
    out["mixed"] = sum(1 for n in (crlf, lf, cr) if n) > 1
    out["text"] = text.replace("\r\n", "\n").replace("\r", "\n")
    out["lines"] = out["text"].count("\n") + 1
    return out


@dataclass
class RawPlan:
    mod: object = None
    rel: str = ""
    path: Optional[Path] = None
    data: bytes = b""              # the whole new file, encoded; b"" = nothing
    before: int = 0
    changes: List[str] = field(default_factory=list)
    hunks: List[Dict] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        c = self.counts
        return (f"raw edit of {self.rel} in {getattr(self.mod, 'name', '?')}: "
                f"{c.get('changed', 0)} changed, {c.get('added', 0)} added, "
                f"{c.get('removed', 0)} removed")

    def payload(self) -> Dict:
        return {"rel": self.rel, "changes": list(self.changes),
                "hunks": list(self.hunks), "counts": dict(self.counts),
                "warnings": list(self.warnings), "errors": list(self.errors),
                "notes": list(self.notes), "bytes": len(self.data),
                "before": self.before, "ok": not self.errors and bool(self.data)}


def plan(mod, body: dict) -> RawPlan:
    """What a save would write, without writing it."""
    rel = str(body.get("rel") or "").replace("\\", "/").strip()
    p = RawPlan(mod=mod, rel=rel)
    try:
        p.path = _path(mod, rel)
    except RawError as e:
        p.errors.append(str(e))
        return p
    raw = p.path.read_bytes()
    p.before = len(raw)
    if str(body.get("sig") or "") != signature(raw):
        p.errors.append(f"data/{rel} changed on disk after it was opened here - "
                        "reload it first, or this save would undo that change")
        return p
    if len(raw) > MAX_BYTES:
        p.errors.append(f"data/{rel} is too large to edit here")
        return p
    codec = sniff(raw)
    try:
        original = decode(raw, codec)
    except UnicodeDecodeError as e:
        p.errors.append(f"data/{rel} is not valid {codec.label}: {e}")
        return p
    if encode(original, codec) != raw:
        p.errors.append(f"data/{rel} does not survive a read and a write unchanged, "
                        "so this editor will not save it")
        return p
    edited = str(body.get("text") if body.get("text") is not None else "")
    edited = edited.replace("\r\n", "\n").replace("\r", "\n")
    text, ops = splice(original, edited)
    try:
        data = encode(text, codec)
    except UnicodeEncodeError as e:
        line = text.count("\n", 0, e.start) + 1
        p.errors.append(f"line {line}: {text[e.start:e.end]!r} cannot be written as "
                        f"{codec.label}, the encoding this file is in")
        return p
    if data == raw:
        p.errors.append("nothing to change")
        return p
    p.data = data
    p.hunks, p.counts = hunks(original, edited, ops)
    c = p.counts
    p.changes.append(f"data/{rel}: {c['changed']} line(s) changed, "
                     f"{c['added']} added, {c['removed']} removed")
    p.warnings.extend(_reader_notes(rel, original, text))
    if rel.lower().startswith("text/") and rel.lower().endswith(".txt"):
        p.notes.append("The .strings.bin beside it is recompiled from the new text, "
                       "because that is the file the game reads.")
    mode, screen = _screen_for(rel)
    if screen:
        p.notes.append(f"{screen} edits this file record by record, and will show "
                       "the change the next time it is opened.")
    return p


def apply(p: RawPlan) -> Dict:
    """Write a planned save, with the same backups and undo as any other job."""
    from . import cleaner, config
    from .logutil import file_op, log

    if p.errors:
        raise ValueError("cannot apply: " + "; ".join(p.errors))
    if not p.data or p.path is None:
        raise ValueError("nothing to change")
    mod = p.mod
    data = Path(mod.data)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": []}

    def keep(rel: str) -> Path:
        target = data / rel
        bpath = backup_root / "data" / rel
        bpath.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, bpath)
            manifest["backed_up"].append(rel)
            file_op("BACKUP", target, f"-> {bpath}")
        else:
            manifest["created"].append(rel)
        return target

    target = keep(p.rel)
    target.write_bytes(p.data)
    file_op("WRITE", target, f"{len(p.data)} bytes (raw)")
    out: Dict = {"id": tid, "rel": p.rel, "bytes": len(p.data)}
    if p.rel.lower().startswith("text/") and p.rel.lower().endswith(".txt"):
        # backed up first: an undo that restored the .txt and left the new .bin
        # would put the text back and leave the game reading the edit
        keep(p.rel + ".strings.bin")
        out["strings_bin"] = cleaner.refresh_strings_bin(
            mod.root, "data/" + p.rel + ".strings.bin")
    rec = {
        "id": tid,
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "rawtext",
        "action": "edit",
        "source": mod.name, "source_root": str(mod.root),
        "dest": mod.name, "dest_root": str(mod.root),
        "unit_type": p.rel, "resolved_type": p.rel,
        "options": {"counts": dict(p.counts)},
        "applied": True, "undone": False, "note": "",
        "summary": p.summary(), "warnings": list(p.warnings),
        "manifest": manifest, "backup_root": str(backup_root),
    }
    config.append_log(rec)
    log.info("RAW    %s in %s - %s, id=%s", p.rel, mod.name, p.counts, tid)
    out["record"] = rec
    return out
