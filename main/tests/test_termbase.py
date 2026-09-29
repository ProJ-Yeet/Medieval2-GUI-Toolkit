"""Phase 88c: the termbase, and the checker that holds a translation to it.

    python -m tests.test_termbase

1. The termbase: every term has a rendering, a stem and a source in every
   language of Phase 88, the stem is inside the rendering, and a source that
   does not fit the term's rule says why.
2. The checker, on catalogues made here: it passes a faithful translation and
   fails each thing it is for - a lost placeholder, a lost tag, a rule-1 token
   translated, a term left unrendered, a plural with the wrong categories.
3. The pseudo-locales, made as the page makes them, pass the structural checks
   over the whole of en.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dev" / "checks"))

import i18n_termbase as tb  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


T = tb.load()
EN = json.loads((tb.I18N / "en.json").read_text(encoding="utf-8"))
LOCALES = [r["tag"] for r in json.loads((tb.I18N / "locales.json").read_text(encoding="utf-8"))["locales"]
           if r["tag"] != "en"]

# ---- 1) the termbase --------------------------------------------------------------------
print("1) the termbase")
check("it lists every language of Phase 88", tb.languages(T) == LOCALES and len(LOCALES) == 16)
problems = tb.completeness(T)
check(f"{len(T['terms'])} terms, each with a rendering, stem and source in all {len(LOCALES)} languages",
      not problems)
for p in problems[:8]:
    print("     " + p)
rules = {t["rule"] for t in T["terms"]}
check("every term is under rule 2, 3 or 4", rules == {2, 3, 4})
unsourced = [(t["id"], lang) for t in T["terms"] for lang in LOCALES
             if not t["tr"].get(lang, {}).get("src")]
check("nothing is unsourced", not unsourced)
check("no term id is listed twice", len({t["id"] for t in T["terms"]}) == len(T["terms"]))
check("a translated language's plural categories are CLDR's (Polish has four, Arabic six)",
      tb.CLDR["pl"] == ("one", "few", "many", "other") and len(tb.CLDR["ar"]) == 6
      and tb.CLDR["ja"] == ("other",) and set(tb.CLDR) == set(LOCALES) | {"en"})

# ---- 2) the checker ---------------------------------------------------------------------
print("\n2) the checker")
en = {
    "_meta": {"lang": "en", "status": "source"},
    "t.read": "Read {path}, the <code>descr_strat.txt</code> of this mod",
    "t.faction": "Add a faction to the campaign",
    "t.save": "Save",
    "t.files": {"one": "{count} file was skipped", "other": "{count} files were skipped"},
    "t.tag": "Open <b>this</b> one",
}
mini = {
    "_meta": {"languages": ["de"]},
    "keep": ["EDU"],
    "terms": [
        {"id": "faction", "rule": 2, "en": "faction", "forms": ["faction", "factions"], "gloss": "g",
         "tr": {"de": {"t": "Fraktion", "stem": "fraktion", "src": "game", "conf": "high"}}},
        {"id": "campaign", "rule": 2, "en": "campaign", "forms": ["campaign"], "gloss": "g",
         "tr": {"de": {"t": "Kampagne", "stem": "kampagne", "src": "game", "conf": "high"}}},
        {"id": "save", "rule": 4, "en": "save", "forms": ["save"], "gloss": "g",
         "tr": {"de": {"t": "Speichern", "stem": "speicher", "src": "ms", "conf": "high"}}},
    ],
}
good = {
    "t.read": "{path} lesen, die <code>descr_strat.txt</code> dieser Mod",
    "t.faction": "Eine Fraktion zur Kampagne hinzufügen",
    "t.save": "Speichern",
    "t.files": {"one": "{count} Datei wurde übersprungen", "other": "{count} Dateien wurden übersprungen"},
    "t.tag": "Dieses <b>eine</b> öffnen",
}
check("a faithful German catalogue passes", tb.check_catalogue(en, good, mini, "de") == [])


def with_(**kw):
    c = json.loads(json.dumps(good))
    c.update(kw)
    return c


def fails(cat, needle):
    return any(needle in p for p in tb.check_catalogue(en, cat, mini, "de"))


check("a missing ID is reported", fails({k: v for k, v in good.items() if k != "t.save"}, "t.save: missing"))
check("an extra ID is reported", fails(with_(**{"t.zzz": "x"}), "not an ID in en.json"))
check("a lost placeholder is reported", fails(with_(**{"t.read": "lesen, die <code>descr_strat.txt</code>"}),
                                              "placeholders"))
check("a placeholder renamed is reported", fails(with_(**{"t.read": "{pfad} <code>descr_strat.txt</code>"}),
                                                 "placeholders"))
check("a lost HTML tag is reported", fails(with_(**{"t.tag": "Dieses eine öffnen"}), "HTML tags"))
check("a rule-1 name translated is reported",
      fails(with_(**{"t.read": "{path} lesen, die <code>strat_beschreibung.txt</code>"}), "rule 1"))
check("a term left unrendered is reported",
      fails(with_(**{"t.faction": "Eine Nation zur Kampagne hinzufügen"}), "term faction"))
check("an exemption on the record lets one sentence be worded around a term",
      tb.check_catalogue(en, with_(**{"t.faction": "Eine Nation zur Kampagne hinzufügen",
                                      "_exempt": {"t.faction": ["faction"]}}), mini, "de") == [])
check("a rule-4 word alone must be the platform's word", fails(with_(**{"t.save": "Sichern"}), "term save"))
check("but a rule-4 word inside a sentence is worded freely",
      not tb.check_catalogue({"t.x": "Save the file before you close it"},
                             {"t.x": "Sichern Sie die Datei vor dem Schließen"}, mini, "de"))
check("a plural with the wrong categories is reported",
      fails(with_(**{"t.files": {"one": "{count} Datei", "few": "x", "other": "{count} Dateien"}}), "plural forms"))
check("a plural's singular may leave out {count}",
      not tb.check_catalogue(en, with_(**{"t.files": {"one": "eine Datei wurde übersprungen",
                                                      "other": "{count} Dateien wurden übersprungen"}}),
                             mini, "de"))
check("a plural that brings a name English does not have is reported",
      fails(with_(**{"t.files": {"one": "{count} {x}", "other": "{count} Dateien"}}), "placeholders"))
en2 = {"t.p": {"one": "{count} file ({why})", "other": "{count} files"}}
check("a plural form may leave a name out, as English's own forms do",
      not tb.check_catalogue(en2, {"t.p": {"one": "{count} Datei ({why})", "other": "{count} Dateien"}},
                             mini, "de"))
check("but a name no form uses is reported",
      any("no form uses" in p for p in tb.check_catalogue(
          en2, {"t.p": {"one": "{count} Datei", "other": "{count} Dateien"}}, mini, "de")))
check("a string that became a plural is reported", fails(with_(**{"t.save": {"one": "a", "other": "b"}}),
                                                         "English is a string"))
check("the tokens a translation must carry verbatim are found (code, file names, snake_case, keep list)",
      tb.rule1_tokens("Edit <code>foo bar</code> in export_descr_unit.txt via recruit_pool for EDU",
                      ["EDU"]) == ["foo bar", "export_descr_unit.txt", "recruit_pool", "EDU"])
check("a {placeholder} inside <code> is not a token",
      tb.rule1_tokens("Write <code>{file}</code> now", []) == [])

# ---- 3) the pseudo-locales ---------------------------------------------------------------
print("\n3) the pseudo-locales")
for kind in ("en-XA", "ar-XB"):
    cat = tb.pseudo_catalogue(EN, kind)
    p = tb.check_catalogue(EN, cat, T, "en", pseudo=True)
    check(f"{kind} passes over all {len(cat)} strings (placeholders, plural shape, tags)", not p)
    for line in p[:5]:
        print("     " + line)

print(f"\n{sum(ok)} of {len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
