"""96f: community translations in the config folder.

Run:  python -m tests.test_i18n_community

A temporary config folder with two files in ``translations/``: ``de.json``
correcting one German string, and ``xx.json``, a language the toolkit does not
ship, naming itself in its ``_meta``. What has to hold:

* **a file over a shipped language** wins string by string, the rest and the
  shipped ``_meta`` staying, and the row says ``community``;
* **a new language** is offered, named by its file, status ``community``, and
  its catalogue is the file's words;
* **English is never overlaid**, and a broken file is ignored;
* **the translator's file** has every English ID, the language's words where
  it has them, English where not.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config, i18n                              # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
folder = cfg / "translations"
folder.mkdir()
shipped_de = i18n.catalogue("de")
some = next(k for k in shipped_de if k != "_meta" and isinstance(shipped_de[k], str))
other = next(k for k in shipped_de if k not in ("_meta", some) and isinstance(shipped_de[k], str))
(folder / "de.json").write_text(json.dumps({some: "MEINE WORTE"}), encoding="utf-8")
(folder / "xx.json").write_text(json.dumps({"_meta": {"name": "Testish", "native": "Tëstish"},
                                            "common.save": "Sæve"}), encoding="utf-8")
(folder / "en.json").write_text(json.dumps({"common.save": "NOPE"}), encoding="utf-8")
(folder / "yy.json").write_text("{ not json", encoding="utf-8")

print("\n1) over a shipped language")
de = i18n.catalogue("de")
check("the file's string wins", de[some] == "MEINE WORTE")
check("the rest stays", de[other] == shipped_de[other] and de.get("_meta") == shipped_de.get("_meta"))
rows = {r["tag"]: r for r in i18n.available()}
check("the row says community", rows["de"].get("community") is True and rows["fr"].get("community") is False)

print("\n2) a new language")
check("offered, named by its file", rows.get("xx", {}).get("native") == "Tëstish"
      and rows["xx"]["status"] == "community")
check("its catalogue is the file's words", i18n.catalogue("xx").get("common.save") == "Sæve")
check("picked when saved", i18n.pick("xx") == "xx")

print("\n3) what is not laid over")
check("English never", i18n.catalogue("en").get("common.save") != "NOPE" and "en" not in
      [r["tag"] for r in i18n.available() if r.get("status") == "community"])
check("a broken file is not offered", "yy" not in rows)

print("\n4) the translator's file")
w = i18n.words_to_translate("de")
en = i18n.catalogue("en")
check("every English ID", set(en) - {"_meta"} == set(w) - {"_meta"})
check("the language's words where it has them", w[other] == shipped_de[other] and w[some] == "MEINE WORTE")
new = i18n.words_to_translate("xx")
check("English where it has none", new["common.cancel"] == en["common.cancel"]
      and new["common.save"] == "Sæve")

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
