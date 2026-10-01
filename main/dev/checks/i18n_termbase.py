"""The termbase, and the checker that holds a translation to it (Phase 88c).

    python dev/checks/i18n_termbase.py              # the termbase's own completeness, all languages
    python dev/checks/i18n_termbase.py --pseudo     # the two pseudo-locales against en.json
    python dev/checks/i18n_termbase.py de           # web/i18n/de.json against en.json and the termbase

``web/i18n/termbase.json`` holds every technical term once, under the rule that
decides where its rendering comes from (see ROADMAP.md, Phase 88):

* **rule 1, never translated**: file names, file-format keywords, script
  commands, code names, product names. No entry per term: what is inside a
  ``<code>`` in English, any ``name.ext`` file name, any ``snake_case`` name and
  the tokens under ``keep`` are read as written, so a translation must carry each
  of them verbatim.
* **rule 2, the game's own term**, **rule 3, the modding community's term**,
  **rule 4, the platform's standard term**: an entry with the English forms it is
  matched by, a gloss that says what it means here, and per language ``t`` (the
  rendering), ``stem`` (a lower-case piece present in every form of it a sentence
  may use, so a case ending does not fail the check; ``|`` between stems where a
  plural changes the vowel, ``stadt|städt``, the first inside ``t``), ``src`` (where it comes
  from: ``game``, ``community``, ``loan``, ``ms``) and ``conf`` (how sure the
  drafter was). A rendering with no source is *unsourced*, and reported.

What a translated catalogue is held to, string by string:

1. the same IDs as English (none missing, none extra), and the same shape (a
   plain string stays a plain string, a plural stays a plural);
2. the same ``{placeholders}``; a plural form may leave a name out (a singular
   can say "one file", and English's own forms differ at times), but uses none
   English does not, and every name English uses is in some form;
3. a plural entry has exactly the CLDR categories of its language;
4. the same HTML tags (a translation must not lose or invent markup);
5. every rule-1 token of the English is in the translation verbatim;
6. every rule-2 and rule-3 term the English uses is rendered (its stem is in the
   translation), and a string that is nothing but a rule-4 term uses the
   platform's word for it. A catalogue's ``_exempt`` map, ``{id: [term ids]}``,
   lets one sentence be worded around a term, on the record.

The pseudo-locales are made in the page from English; here they are made the same
way and held to checks 1, 2 and 4 only (letters are accented, so the words of the
termbase are not there to find).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "web" / "i18n"
TERMBASE = I18N / "termbase.json"

#: where each rule's renderings may come from
SOURCES = {2: {"game"}, 3: {"community", "loan"}, 4: {"ms"}}
ALL_SOURCES = set().union(*SOURCES.values())
CONF = {"high", "medium", "low"}

#: CLDR plural categories (cardinal), the ones a catalogue entry must hold
CLDR = {
    "en": ("one", "other"), "de": ("one", "other"), "hu": ("one", "other"), "tr": ("one", "other"),
    "fr": ("one", "many", "other"), "es": ("one", "many", "other"), "it": ("one", "many", "other"),
    "pt-BR": ("one", "many", "other"), "pl": ("one", "few", "many", "other"),
    "cs": ("one", "few", "many", "other"), "ru": ("one", "few", "many", "other"),
    "uk": ("one", "few", "many", "other"), "zh-Hans": ("other",), "zh-Hant": ("other",),
    "ja": ("other",), "ko": ("other",), "ar": ("zero", "one", "two", "few", "many", "other"),
}

FIELD = re.compile(r"\{([A-Za-z_]\w*)(?::([^{}]*))?\}")
TAG = re.compile(r"<(/?[a-zA-Z][a-zA-Z0-9-]*)(?:\s[^<>]*)?/?>")
CODE = re.compile(r"<code>(.*?)</code>", re.S)
FILE_NAME = re.compile(
    r"\b[\w\-]+\.(?:txt|tga|dds|cas|dat|bin|lua|xml|json|zip|sd|rwm|exe|bat|py|db|dll|ini|cfg|csv|png|"
    r"jpg|texture|wav|mp3|bik|skeleton|pack|bmp|modeldb|evt|spr|tsv)\b", re.I)
SNAKE = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")
ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-f]+|[a-z]+);", re.I)
#: an accent stands in for the letter in en-XA
_ACCENT = "áƀçðéƒĝĥîĵķļɱñöþǫŕšţûṽŵẋýž"


def load(path: Path = TERMBASE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def languages(tb: dict) -> List[str]:
    return [t for t in tb["_meta"]["languages"]]


# ---------------------------------------------------------------------------
# the termbase itself

def completeness(tb: dict) -> List[str]:
    """Every term has a rendering, a stem and a source in every language."""
    out: List[str] = []
    langs = languages(tb)
    seen: Set[str] = set()
    for term in tb["terms"]:
        tid = term["id"]
        if tid in seen:
            out.append(f"{tid}: listed twice")
        seen.add(tid)
        rule = term.get("rule")
        if rule not in SOURCES:
            out.append(f"{tid}: rule {rule!r} is not 2, 3 or 4")
            continue
        if not term.get("forms") or not term.get("gloss"):
            out.append(f"{tid}: needs its English forms and a gloss")
        for lang in langs:
            r = (term.get("tr") or {}).get(lang)
            if not r:
                out.append(f"{tid}: no rendering in {lang}")
                continue
            t, stem, src = r.get("t", ""), r.get("stem", ""), r.get("src", "")
            if not t.strip():
                out.append(f"{tid}/{lang}: empty rendering")
            if not stem or stem.split("|")[0] not in t.lower():
                out.append(f"{tid}/{lang}: stem {stem!r} is not inside {t!r}")
            if not src:
                out.append(f"{tid}/{lang}: unsourced")
            elif src not in ALL_SOURCES:
                out.append(f"{tid}/{lang}: source {src!r} is not one of {sorted(ALL_SOURCES)}")
            elif src not in SOURCES[rule] and not (r.get("note") or "").strip():
                out.append(f"{tid}/{lang}: source {src!r} does not fit rule {rule}, and no note says why")
            if r.get("conf") not in CONF:
                out.append(f"{tid}/{lang}: no confidence mark")
    return out


# ---------------------------------------------------------------------------
# reading a catalogue string

def forms_of(v) -> Dict[str, str]:
    return {"": v} if isinstance(v, str) else dict(v)


def placeholders(s: str) -> Set[str]:
    return {m.group(1) for m in FIELD.finditer(s)}


def tags(s: str) -> List[str]:
    return sorted(t.lower() for t in TAG.findall(s))


def visible(s: str) -> str:
    """What a person reads of a string: tags, entities and placeholders out."""
    s = TAG.sub(" ", s)
    s = ENTITY.sub(" ", s)
    return FIELD.sub(" ", s)


def rule1_tokens(en: str, keep: Iterable[str]) -> List[str]:
    """The tokens of an English string that a translation carries verbatim."""
    out: List[str] = []
    for m in CODE.finditer(en):
        c = ENTITY.sub(lambda e: {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&quot;": '"'}.get(e.group(0).lower(), e.group(0)),
                       m.group(1))
        c = FIELD.sub("", c).strip()
        if c and not FIELD.search(m.group(1)) and len(c) > 1:
            out.append(c)
    plain = CODE.sub(" ", en)
    vis = visible(plain)
    out.extend(m.group(0) for m in FILE_NAME.finditer(vis))
    # a snake_case name inside a file name is that file name, found above
    out.extend(m.group(0) for m in SNAKE.finditer(FILE_NAME.sub(" ", vis)))
    for k in keep:
        if re.search(r"(?<![\w])" + re.escape(k) + r"(?![\w])", vis):
            out.append(k)
    seen, res = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res


def _word_rx(forms: Iterable[str]) -> "re.Pattern[str]":
    alts = sorted({f for f in forms if f}, key=len, reverse=True)
    return re.compile(r"(?<![\w])(?:" + "|".join(re.escape(a) for a in alts) + r")(?![\w])", re.I)


def compile_terms(tb: dict) -> List[dict]:
    out = []
    for term in tb["terms"]:
        out.append(dict(term, _rx=_word_rx(term["forms"]),
                        _whole={f.lower() for f in term["forms"]}))
    return out


def terms_in(en: str, cterms: List[dict]) -> List[dict]:
    """The terms an English string uses. A rule-4 term counts only when the
    string is that word and nothing else (a button or a tab), since a generic
    word inside a sentence is reworded freely in every language."""
    vis = visible(CODE.sub(" ", en))
    plain = re.sub(r"[^\w ]+", " ", vis).strip().lower()
    hit = []
    for t in cterms:
        if t["rule"] == 4:
            if plain in t["_whole"]:
                hit.append(t)
        elif t["_rx"].search(vis):
            hit.append(t)
    return hit


# ---------------------------------------------------------------------------
# a catalogue against English

def check_catalogue(en: dict, cat: dict, tb: Optional[dict], tag: str, pseudo: bool = False) -> List[str]:
    """Problems of ``cat`` (a locale's ``{id: string | {category: string}}``).
    ``tb`` None checks structure only."""
    out: List[str] = []
    en = {k: v for k, v in en.items() if k != "_meta"}
    exempt = cat.get("_exempt") or {}
    cat = {k: v for k, v in cat.items() if k not in ("_meta", "_exempt")}
    for k in cat:
        if k not in en:
            out.append(f"{k}: not an ID in en.json")
    cterms = compile_terms(tb) if (tb and not pseudo) else []
    keep = tb.get("keep", []) if tb else []
    cats = CLDR.get(tag)
    for k, src in en.items():
        if k not in cat:
            out.append(f"{k}: missing")
            continue
        tr = cat[k]
        if isinstance(src, str) != isinstance(tr, str):
            out.append(f"{k}: English is {'a string' if isinstance(src, str) else 'a plural'} "
                       f"and the translation is not")
            continue
        sf, tf = forms_of(src), forms_of(tr)
        if not isinstance(src, str) and not pseudo and cats:
            if set(tf) != set(cats):
                out.append(f"{k}: plural forms {sorted(tf)} but {tag} needs {sorted(cats)}")
        if not isinstance(src, str):
            want = set.union(*(placeholders(x) for x in sf.values())) - {"count"}
        else:
            want = placeholders(src)
        for cat_name, txt in tf.items():
            if not isinstance(txt, str):
                out.append(f"{k}: {cat_name or 'the string'} is not text")
                continue
            got = placeholders(txt)
            if isinstance(src, str):
                if got != want:
                    out.append(f"{k}: placeholders {sorted(got)} but English has {sorted(want)}")
            elif (got - {"count"}) - want:
                out.append(f"{k}/{cat_name}: placeholders {sorted(got)} but English has {sorted(want)}")
        if not isinstance(src, str):
            # a form may leave a name out (English's singular can say why where its plural
            # does not), but every name English uses is used by some form
            have = set().union(*(placeholders(x) for x in tf.values() if isinstance(x, str)))
            if want - have:
                out.append(f"{k}: no form uses {sorted(want - have)}")
        base = src if isinstance(src, str) else src.get("other", "")
        for cat_name, txt in tf.items():
            if isinstance(txt, str) and tags(txt) != tags(base if isinstance(src, str) else base):
                out.append(f"{k}/{cat_name}".rstrip("/") + ": HTML tags differ from English")
                break
        if pseudo or not tb:
            continue
        joined = " ".join(x for x in tf.values() if isinstance(x, str))
        joined_l = joined.lower()
        for tok in rule1_tokens(base, keep):
            if tok not in joined:
                out.append(f"{k}: rule 1: {tok!r} must appear as written")
        skip = set(exempt.get(k, []))
        for t in terms_in(base, cterms):
            if t["id"] in skip:
                continue
            r = (t.get("tr") or {}).get(tag)
            if not r:
                out.append(f"{k}: term {t['id']} has no rendering in {tag}")
            elif not any(s in joined_l for s in r["stem"].lower().split("|")):
                out.append(f"{k}: term {t['id']} ({t['en']}) should read {r['t']!r}")
    return out


# ---------------------------------------------------------------------------
# the pseudo-locales, as the page makes them (i18n.js: i18nPseudo)

_ACC = dict(zip("abcdefghijklmnopqrstuvwxyz", _ACCENT))
_ACC.update({c.upper(): a.upper() for c, a in zip("abcdefghijklmnopqrstuvwxyz", "áƀçðéƒĝĥîĵķļɱñöþǫŕšţûṽŵẋýž")})
_SKIP = re.compile(r"(<[^>]*>|&(?:#\d+|#x[0-9a-f]+|[a-z]+);|\{[A-Za-z_]\w*(?::[^{}]*)?\})", re.I)


def pseudo_string(s: str, kind: str) -> str:
    parts = _SKIP.split(s)
    if kind == "ar-XB":
        return "".join(p if i % 2 or not re.search(r"\S", p) else "‮" + p + "‬"
                       for i, p in enumerate(parts))
    letters = 0
    out = []
    for i, p in enumerate(parts):
        if i % 2:
            out.append(p)
            continue
        buf = []
        for c in p:
            if c.isascii() and c.isalpha():
                letters += 1
                buf.append(_ACC.get(c, c))
            else:
                buf.append(c)
        out.append("".join(buf))
    pad = -(-letters * 35 // 100)
    body = "".join(out)
    return "[" + body + (" " + "·" * pad if pad else "") + "]" if letters else body


def pseudo_catalogue(en: dict, kind: str) -> dict:
    out = {}
    for k, v in en.items():
        if k == "_meta":
            continue
        out[k] = pseudo_string(v, kind) if isinstance(v, str) else {c: pseudo_string(x, kind) for c, x in v.items()}
    return out


def main(argv: List[str]) -> int:
    tb = load()
    en = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    problems: List[str] = []
    if "--pseudo" in argv:
        for kind in ("en-XA", "ar-XB"):
            p = check_catalogue(en, pseudo_catalogue(en, kind), tb, "en", pseudo=True)
            print(f"{kind}: {len(p)} problems")
            problems += p
    tags_ = [a for a in argv if not a.startswith("--")]
    if not tags_ and "--pseudo" not in argv:
        problems = completeness(tb)
        print(f"termbase: {len(tb['terms'])} terms, {len(languages(tb))} languages, {len(problems)} problems")
    for tag in tags_:
        cat = json.loads((I18N / f"{tag}.json").read_text(encoding="utf-8"))
        p = check_catalogue(en, cat, tb, tag)
        print(f"{tag}: {len(p)} problems")
        problems += p
    for line in problems[:40]:
        print("  ", line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
