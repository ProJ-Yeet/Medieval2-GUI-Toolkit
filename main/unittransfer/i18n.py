"""The interface language (Phase 88).

Two languages are never confused here. The *interface language* is the
toolkit's own buttons, headings and messages; the *mod's language* is whatever
its ``data/text`` files hold. This module is only the first: choosing an
interface language never changes a byte written to a mod.

What it does:

* **Catalogues.** ``web/i18n/<tag>.json`` per locale, flat ``{id: text}``;
  ``en.json`` is the source and the fallback. :func:`catalogue_js` hands the
  page English and the chosen locale in one script, loaded before any module,
  so a string is there the moment a script asks for it.
* **Which language.** The one saved in Settings (``ui_lang``), else the first
  entry of the browser's ``Accept-Language`` that has a catalogue, else
  English. The two pseudo-locales, ``en-XA`` and ``ar-XB``, are made in the
  page from English and are only ever chosen by hand.
* **The engine speaks message IDs.** :func:`msg` builds a message as English
  text, which is what the log, ``server.log`` and ``transfer_cli.py`` see, and
  remembers its ID and parameters. :func:`annotate` then marks, in a reply to
  the page, which strings are such messages, so the page shows the
  catalogue's text for them, or the English when there is none.
"""
from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
I18N_DIR = WEB_DIR / "i18n"
SOURCE = "en"

_FIELD = re.compile(r"\{([A-Za-z_]\w*)(?::([^{}]*))?\}")


# ---------------------------------------------------------------------------
# the locales

def locales() -> dict:
    """``web/i18n/locales.json``: every locale known, and the pseudo ones."""
    return json.loads((I18N_DIR / "locales.json").read_text(encoding="utf-8"))


def available() -> List[dict]:
    """The locales Settings offers: those with a catalogue, then the pseudo
    ones. Each row carries its status (source, draft, reviewed, test)."""
    meta = locales()
    out = []
    for row in meta["locales"]:
        p = I18N_DIR / f"{row['tag']}.json"
        if not p.is_file():
            continue
        r = dict(row)
        try:
            own = json.loads(p.read_text(encoding="utf-8")).get("_meta") or {}
            r["status"] = own.get("status", r.get("status"))
        except (OSError, ValueError):
            continue
        out.append(r)
    out.extend(dict(r) for r in meta.get("pseudo", []))
    return out


def _match(tag: str, tags: List[str]) -> Optional[str]:
    """``tag`` against the offered ones: exact, then by language (``pt`` finds
    ``pt-BR``, ``zh-CN`` finds ``zh-Hans``, ``zh-TW`` ``zh-Hant``)."""
    low = {t.lower(): t for t in tags}
    t = tag.strip().lower()
    if not t:
        return None
    if t in low:
        return low[t]
    script = {"zh-cn": "zh-hans", "zh-sg": "zh-hans", "zh-tw": "zh-hant", "zh-hk": "zh-hant",
              "zh-mo": "zh-hant", "zh": "zh-hans"}.get(t)
    if script and script in low:
        return low[script]
    base = t.split("-")[0]
    for k, v in low.items():
        if k.split("-")[0] == base:
            return v
    return None


def pick(saved: str = "", accept_language: str = "") -> str:
    """The interface language: the saved one if it is offered, else the first
    of ``Accept-Language`` that is (never a pseudo-locale), else English."""
    rows = available()
    tags = [r["tag"] for r in rows]
    if saved:
        hit = _match(saved, tags)
        if hit:
            return hit
    real = [r["tag"] for r in rows if r.get("status") != "test"]
    for part in (accept_language or "").split(","):
        hit = _match(part.split(";")[0], real)
        if hit:
            return hit
    return SOURCE


def catalogue(tag: str) -> Dict[str, Any]:
    p = I18N_DIR / f"{tag}.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def catalogue_js(tag: str) -> str:
    """The script the page loads before any module: English, the chosen
    locale's catalogue (or none for English and the pseudo ones), and the
    offered list."""
    rows = available()
    row = next((r for r in rows if r["tag"] == tag), None) or {"tag": SOURCE, "dir": "ltr"}
    boot = {"lang": row["tag"], "dir": row.get("dir", "ltr"), "status": row.get("status", ""),
            "base": row.get("base", ""), "en": catalogue(SOURCE),
            "cat": catalogue(row["tag"]) if row["tag"] != SOURCE and not row.get("base") else {},
            "offered": rows}
    body = json.dumps(boot, ensure_ascii=False, separators=(",", ":"))
    # `</script>` cannot occur in JSON's output unescaped in a way that
    # matters here (this is a separate file), but a U+2028 would end a line
    # in older engines: escape both line separators
    body = body.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"window.I18N_BOOT={body};\n"


# ---------------------------------------------------------------------------
# the engine's messages

class Msg(str):
    """English text that knows its catalogue ID and parameters. It *is* the
    English string, so every caller that logs, compares or concatenates it
    goes on working unchanged."""

    def __new__(cls, text: str, mid: str = "", params: Optional[Dict[str, Any]] = None):
        s = super().__new__(cls, text)
        s.id, s.params = mid, dict(params or {})
        return s

    def __reduce__(self):
        # copy, deepcopy and pickle make it again with its ID
        return (Msg, (str(self), self.id, self.params))


#: Recently made messages by their English text. A reply is built from str(e)
#: and list copies, which drop the subclass, so the reply is matched on text.
_RECENT: "OrderedDict[str, Tuple[str, Dict[str, Any]]]" = OrderedDict()
_RECENT_MAX = 4096
_LOCK = threading.Lock()


def _plain(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return str(v)
    return str(v)


def fill(template: str, params: Dict[str, Any]) -> str:
    """``template`` with ``{name}`` and ``{name:spec}`` filled from ``params``
    exactly as an f-string formats them (``format(v, spec)``, so an enum or
    anything with its own ``__format__`` reads the same). A name not in
    ``params`` stays as written."""
    def one(m):
        name, spec = m.group(1), m.group(2)
        if name not in params:
            return m.group(0)
        return format(params[name], spec or "")
    return _FIELD.sub(one, template)


def msg(mid: str, template: str, **params: Any) -> Msg:
    """A message for the screen: English ``template`` filled from ``params``,
    remembered under ``mid`` so the page can show it in its own language.

    ``template`` is en.json's text for ``mid``; the catalogue checker holds the
    two to each other."""
    text = fill(template, params)
    plain = {k: _plain(v) for k, v in params.items()}
    with _LOCK:
        _RECENT[text] = (mid, plain)
        _RECENT.move_to_end(text)
        while len(_RECENT) > _RECENT_MAX:
            _RECENT.popitem(last=False)
    return Msg(text, mid, plain)


def msgN(mid: str, n: Any, one: str, other: str, **params: Any) -> Msg:
    """A message with a count in it: English ``one`` when ``n`` is 1, else
    ``other``, and the page picks the plural form its own language needs
    (``Intl.PluralRules``) from the catalogue's entry, ``{"one": ..., "other":
    ...}``, using ``{count}``, which is ``n``. English is the string an
    f-string with an ``'s' if n != 1`` made, so the log is unchanged."""
    params["count"] = n
    return msg(mid, one if n == 1 else other, **params)


def lookup(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    if isinstance(text, Msg):
        return text.id, text.params
    with _LOCK:
        return _RECENT.get(text)


def annotate(obj: Any) -> Optional[Dict[str, list]]:
    """``{text: [id, params]}`` for every string in ``obj`` that is a message
    made by :func:`msg`, or None when there are none. Only walked when a
    message has been made at all."""
    if not _RECENT:
        return None
    found: Dict[str, list] = {}

    def walk(v, depth=0):
        if depth > 12:
            return
        if isinstance(v, str):
            if len(v) > 3 and v not in found:
                hit = lookup(v)
                if hit:
                    found[v] = [hit[0], hit[1]]
        elif isinstance(v, dict):
            for x in v.values():
                walk(x, depth + 1)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x, depth + 1)
    walk(obj)
    return found or None
