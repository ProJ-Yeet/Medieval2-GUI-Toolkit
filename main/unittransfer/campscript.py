"""96f: a campaign's ``campaign_script.txt``, piece by piece.

The Oogway campaign editor's *Campaign script...* (in its Events window): the
script listed as its pieces - each monitor, loop, ``if`` block, counter and
command at the top level - and any taken out, one, the picked ones or all, the
frame staying. Its source is no longer public; this is built from that
behaviour, on this toolkit's raw text editor (:mod:`unittransfer.rawtext`), so
a save is byte-exact outside the lines taken out, refused when the file
changed since it was read, backed up, and undone from the Log.

**A piece** is one statement between ``script`` and ``end_script`` at depth 0,
with the comment lines directly above it (no blank between). Depth goes by the
words that open and close a block - ``monitor_event``, ``monitor_conditions``,
``while`` and ``if`` against ``end_monitor``, ``end_while`` and ``end_if`` -
never by indent: Divide and Conquer's 38,726-line script indents its insides
and leaves an ``and`` at column 0 inside a block. ``script``, ``end_script``
and ``wait_monitors`` are the frame and are not offered: without
``wait_monitors`` every monitor ends the moment the script reaches the end.

A file whose blocks do not close says so, and its pieces after the fault are
not offered, since where they end is a guess.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from . import campstrat
from . import i18n as _i18n
from . import rawtext

NAME = "campaign_script.txt"
OPEN = {"monitor_event", "monitor_conditions", "while", "if"}
CLOSE = {"end_monitor", "end_while", "end_if"}
FRAME = {"script", "end_script", "wait_monitors"}
#: the first line of a piece, as long as the list shows it
HEAD = 140


def rel_for(campaign: str = "") -> str:
    """The script's path under ``data/`` for one campaign."""
    return "/".join([campstrat.CAMPAIGN_DIR_REL,
                     campstrat.campaign_rel(campaign or campstrat.DEFAULT_CAMPAIGN), NAME])


def _word(line: str) -> str:
    code = line.split(";", 1)[0].strip()
    return code.split()[0].lower() if code.split() else ""


def split(text: str) -> Tuple[List[Dict], List[str]]:
    """The top-level pieces of a script's text (``\\n`` lines), and any fault."""
    lines = text.split("\n")
    warnings: List[str] = []
    begin = next((i for i, ln in enumerate(lines) if _word(ln) == "script"), -1) + 1
    pieces: List[Dict] = []
    depth, cur = 0, None
    lead = -1                           # first line of the comments above, or -1
    for i in range(begin, len(lines)):
        line = lines[i]
        word = _word(line)
        bare = line.strip()
        if depth == 0 and cur is None:
            if not bare:
                lead = -1
                continue
            if bare.startswith(";"):
                if lead < 0:
                    lead = i
                continue
            if word == "end_script":
                break
            start = lead if lead >= 0 else i
            lead = -1
            cur = {"kind": word, "head": bare[:HEAD], "start": start, "at": i,
                   "frame": word in FRAME}
        if word in OPEN:
            depth += 1
        elif word in CLOSE:
            depth -= 1
            if depth < 0:
                warnings.append(_i18n.msg(
                    "eng.campscript.close_without_open",
                    "line {line}: {word} closes a block that was never opened, so the pieces after it are not offered",
                    line=i + 1, word=word))
                return pieces, warnings
        if depth == 0 and cur is not None:
            cur["end"] = i
            cur["lines"] = i - cur["start"] + 1
            cur["n"] = len(pieces)
            if cur["start"] < cur["at"]:
                cur["comment"] = lines[cur["start"]].strip().lstrip(";").strip()[:HEAD]
            pieces.append(cur)
            cur = None
    if cur is not None or depth > 0:
        warnings.append(_i18n.msg(
            "eng.campscript.never_closed",
            "line {line}: a {word} block is never closed, so it and what follows are not offered",
            line=(cur or {}).get("at", 0) + 1, word=(cur or {}).get("kind", "")))
    return pieces, warnings


def view(mod, campaign: str = "") -> Dict:
    """The script as the page lists it, with the signature a save is held to."""
    rel = rel_for(campaign)
    out: Dict = {"campaign": campaign or campstrat.DEFAULT_CAMPAIGN, "rel": rel,
                 "have": False, "pieces": [], "warnings": [], "readonly": "",
                 "campaigns": campstrat.campaign_paths(mod)}
    try:
        got = rawtext.read(mod, rel)
    except (rawtext.RawError, OSError) as e:
        out["problem"] = str(e)
        return out
    out.update(have=True, sig=got["sig"], lines=got["lines"], readonly=got["readonly"])
    if got["readonly"]:
        return out
    out["pieces"], out["warnings"] = split(got["text"])
    return out


def without(text: str, pieces: List[Dict], drop: List[int]) -> str:
    """The text with those pieces taken out, and a blank line each left behind."""
    lines = text.split("\n")
    gone = set()
    for p in pieces:
        if p["n"] in drop and not p["frame"]:
            gone.update(range(p["start"], p["end"] + 1))
            nxt = p["end"] + 1
            if nxt < len(lines) and not lines[nxt].strip() \
                    and (p["start"] == 0 or not lines[p["start"] - 1].strip()):
                gone.add(nxt)
    return "\n".join(ln for i, ln in enumerate(lines) if i not in gone)


def plan(mod, body: dict) -> "rawtext.RawPlan":
    """Taking ``body["drop"]`` (piece numbers) out of the campaign's script."""
    rel = rel_for(str(body.get("campaign") or ""))
    got = rawtext.read(mod, rel)
    pieces, _ = split(got["text"])
    drop = {int(n) for n in (body.get("drop") or [])}
    text = without(got["text"], pieces, sorted(drop))
    p = rawtext.plan(mod, {"rel": rel, "sig": body.get("sig"), "text": text})
    taken = [x for x in pieces if x["n"] in drop and not x["frame"]]
    if taken and not p.errors:
        p.changes.insert(0, _i18n.msg(
            "eng.campscript.took_out", "took out {n} piece(s) of {name}: {heads}",
            n=len(taken), name=NAME, heads="; ".join(x["head"][:60] for x in taken[:6])))
    return p


def apply(p: "rawtext.RawPlan") -> Dict:
    return rawtext.apply(p)
