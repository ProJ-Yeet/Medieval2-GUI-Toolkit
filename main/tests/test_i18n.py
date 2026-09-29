"""Phase 88a-88c: the interface language.

    python -m tests.test_i18n

1. The catalogue: en.json parses, its IDs are namespaced, and every ID the
   code asks for is in it - each tt/ttA/ttN in web/js, each data-i18n in
   index.html, each engine message - with the engine's English the same
   template en.json holds.
2. The lint: no string a person reads is left outside the catalogue, in any
   module under web/js, in index.html, or among the engine's messages (the
   extractors' own rules, so the lint and the move agree by construction).
   88c: every sentence whole - none joined with + or built of fragments, no
   plural made with an 's', no engine message built with + or % - and every
   call passing exactly the names its string uses (dev/checks/i18n_joins.py,
   i18n_params.py).
3. The engine: msg() is the English string, as an f-string would have made it,
   and remembers its ID; annotate() marks it in a reply; the language picked
   from Settings, then Accept-Language, then English, never a pseudo-locale.
4. The page's runtime, in Node with the real i18n.js: English exactly as
   en.json has it; the pseudo-locales keep tags, entities and placeholders;
   a missing ID falls back; plurals by CLDR (Polish has four forms); a
   translated engine message swapped in, English left alone.
5. Over HTTP: catalogue.js with the chosen language, en.json, and an error
   reply carrying its message's ID.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dev" / "checks"))

from tests import _tmp  # noqa: E402
from unittransfer import config, i18n  # noqa: E402
import i18n_extract as jx  # noqa: E402
import i18n_extract_py as px  # noqa: E402

WEB = ROOT / "web"
EN = WEB / "i18n" / "en.json"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the catalogue -------------------------------------------------------------------
print("1) the catalogue")
cat = json.loads(EN.read_text(encoding="utf-8"))
meta = cat.pop("_meta", {})
check(f"en.json parses: {len(cat)} strings, marked as the source", meta.get("status") == "source" and len(cat) > 5000)
check("every ID is <namespace>.<words>, lower case",
      all(re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)+", k) for k in cat))
used = {}
# an ID is asked for as tt('id'), or picked first: tt(on ? 'a.shown' : 'a.hidden'), so
# every quoted literal shaped like an ID in a module's namespace counts
namespaces = {f.stem for f in (WEB / "js").glob("*.js")} | {"common", "app", "i18n"}
for f in sorted((WEB / "js").glob("*.js")):
    src = f.read_text(encoding="utf-8")
    for m in re.finditer(r"(?<![\w$.])tt[AN]?\('([^']+)'", src):
        used.setdefault(m.group(1), f.name)
    for m in re.finditer(r"'([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)'", src):
        if m.group(1).split(".")[0] in namespaces:
            used.setdefault(m.group(1), f.name)
html = (WEB / "index.html").read_text(encoding="utf-8")
for m in re.finditer(r'data-i18n(?:-[\w-]+)?="([^"]+)"', html):
    used.setdefault(m.group(1), "index.html")
missing = sorted(k for k in used if k not in cat)
check(f"every ID the page asks for is in en.json ({len(used)} asked for)", not missing)
if missing:
    print("     missing:", missing[:10])
eng_calls = {}
for f in sorted((ROOT / "unittransfer").glob("*.py")):
    # msg(id, template) and msgN(id, n, one, other), the catalogue holding {"one", "other"}
    for k, tpl in px.catalogued(f.read_text(encoding="utf-8")).items():
        eng_calls[k] = (tpl, f.name)
check(f"every engine message's ID is in en.json ({len(eng_calls)})",
      all(k in cat for k in eng_calls))
drift = [k for k, (tpl, _f) in eng_calls.items() if cat.get(k) != tpl]
check("and its English is the template en.json holds, word for word", not drift)
if drift:
    print("     drift:", drift[:5])
unused = [k for k in cat if k not in used and k not in eng_calls]
check(f"no string in en.json that nothing asks for ({len(unused)})", not unused)
if unused:
    print("     unused:", unused[:10])

# ---- 2) the lint --------------------------------------------------------------------------
print("\n2) nothing a person reads is left outside the catalogue")
classes = jx.scan.css_classes()
left = {}
for f in sorted((WEB / "js").glob("*.js")):
    if f.name == "i18n.js":
        continue
    eds = jx.collect(f.read_text(encoding="utf-8"), f"js/{f.name}", f.stem, classes)
    n = sum(len(e.runs) for e in eds)
    if n:
        left[f.name] = [(f.read_text(encoding="utf-8").count("\n", 0, e.start) + 1, r.en[:60])
                        for e in eds for r in e.runs][:3]
check(f"web/js: every module clean ({len(list((WEB / 'js').glob('*.js')))} files)", not left)
for k, v in list(left.items())[:8]:
    print(f"     {k}: {v}")
tmp_html = Path(tempfile.mkdtemp(prefix="ut_i18n_html_"))
cat2 = dict(cat)
_new, n_html = jx.apply_html(cat2, {(k.split(".")[0], v): k for k, v in cat2.items() if isinstance(v, str)})
check("index.html: every text and tooltip carries data-i18n", n_html == 0)
shutil.rmtree(tmp_html, ignore_errors=True)
py_left = {}
for f in sorted((ROOT / "unittransfer").glob("*.py")):
    if f.name in px.SKIP_MODULES:
        continue
    import ast
    found, _built = px.candidates(ast.parse(f.read_text(encoding="utf-8")))
    if found:
        py_left[f.name] = [(n.lineno, (px.text_of(n) or "")[:50]) for n in found[:3]]
check("unittransfer: every message the engine raises or reports has an ID", not py_left)
for k, v in list(py_left.items())[:8]:
    print(f"     {k}: {v}")

# 88c: the sentences whole, the plurals by category
import i18n_joins as jn  # noqa: E402
join_sites = jn.scan_tree()
check("web/js: no sentence is joined with + and no plural is made with an 's'", not join_sites)
for st in join_sites[:6]:
    print(f"     {st.file}:{st.line} [{st.kind}] {st.text[:90]}")
import i18n_params as ip  # noqa: E402
param_gaps = ip.check_tree() + ip.check_engine()
check("every call passes each {name} its string uses, and uses each name it passes", not param_gaps)
for g in param_gaps[:6]:
    print(f"     {g}")
eng_sites = jn.scan_py()
check("unittransfer: no message is built with + or %, and no plural is a parameter", not eng_sites)
for st in eng_sites[:6]:
    print(f"     {st.file}:{st.line} [{st.kind}] {st.text[:90]}")

# ---- 3) the engine --------------------------------------------------------------------------
print("\n3) the engine's side")
x, spec, items = 3, 1.23456, ["a", "b"]
m = i18n.msg("eng.test.x", "{x} files, {spec:.2f} wide, {items!r}", x=x, spec=spec, items=repr(items))
check("msg() is the English string (the unfilled !r kept as written)", m == "3 files, 1.23 wide, {items!r}")
m = i18n.msg("eng.test.y", "{x} files, {spec:.2f} wide, {items}", x=x, spec=spec, items=repr(items))
check("and fills exactly as the f-string did", m == f"{x} files, {spec:.2f} wide, {items!r}")
check("it is a str, with its ID and parameters", isinstance(m, str) and m.id == "eng.test.y"
      and m.params["x"] == 3)
import copy  # noqa: E402
import pickle  # noqa: E402
check("copy and pickle keep the ID", copy.deepcopy(m).id == "eng.test.y" and pickle.loads(pickle.dumps(m)).id == "eng.test.y")
check("a literal { } in a message is left alone", i18n.msg("eng.test.z", "requires factions { }") == "requires factions { }")
marks = i18n.annotate({"error": str(m), "rows": [{"why": str(m)}], "name": "not a message"})
check("annotate() marks a message by its text, anywhere in the reply, and nothing else",
      marks == {str(m): ["eng.test.y", m.params]})
check("the pick: saved first", i18n.pick("en-XA", "de") == "en-XA")
check("then Accept-Language, never a pseudo-locale, then English",
      i18n.pick("", "ar-XB,en-XA;q=0.9") == "en" and i18n.pick("", "") == "en")
js = i18n.catalogue_js("en")
check("catalogue.js: English, the offered list, and nothing else for English",
      js.startswith("window.I18N_BOOT=") and '"lang":"en"' in js and '"cat":{}' in js)

# ---- 4) the page's runtime in Node --------------------------------------------------------------
print("\n4) i18n.js in Node")
if shutil.which("node"):
    harness = r"""
const fs=require('fs'),vm=require('vm');
const [,,src,lang,base,catJson]=process.argv;
const en={'a.plain':'Save','a.p':'{n} tiles in <b>{region}</b> &amp; more','a.code':'<code>descr_strat.txt</code> read',
  'a.pl':{one:'{count} file',few:'{count} files (few)',many:'{count} files (many)',other:'{count} files'},
  'a.lit':'requires factions { }','eng.t.m':'{n} units'};
global.window={I18N_BOOT:{lang,dir:lang==='ar-XB'?'rtl':'ltr',status:'',base,en,cat:JSON.parse(catJson),offered:[]}};
global.document={documentElement:{},querySelectorAll:()=>[]};
global.console={warn(){},log:console.log};
global.esc=s=>String(s);
vm.runInThisContext(fs.readFileSync(src,'utf8'));
const r={};
r.plain=tt('a.plain'); r.p=tt('a.p',{n:5,region:'Anjou'}); r.code=tt('a.code'); r.lit=tt('a.lit');
r.missing=tt('a.nope'); r.attr=ttA('a.plain');
r.pl=[1,2,5,22,1.5].map(n=>ttN('a.pl',n));
const reply={error:'4 units',_i18n:{'4 units':['eng.t.m',{n:4}]}};
r.srv=i18nFromServer(reply).error; r.dir=document.documentElement.dir; r.lang=document.documentElement.lang;
console.log(JSON.stringify(r));
"""
    hp = Path(_tmp.mkdtemp(prefix="ut_i18n_node_")) / "h.js"
    hp.write_text(harness, encoding="utf-8")

    def node(lang, base="", cat=None):
        out = subprocess.run(["node", str(hp), str(WEB / "js" / "i18n.js"), lang, base,
                              json.dumps(cat or {})], capture_output=True, text=True, encoding="utf-8")
        return json.loads(out.stdout.strip().splitlines()[-1]) if out.returncode == 0 else {"err": out.stderr}

    r = node("en")
    check("English: exactly en.json's text, filled as written",
          r.get("plain") == "Save" and r["p"] == "5 tiles in <b>Anjou</b> &amp; more" and r["lit"] == "requires factions { }")
    check("an ID with no string shows the ID (and warns once)", r["missing"] == "a.nope")
    check("a reply's English is left as it came in English", r["srv"] == "4 units" and r["lang"] == "en")
    r = node("en-XA", "en")
    check("en-XA: accented, longer, bracketed", r.get("plain", "").startswith("[Šá") and "·" in r["plain"])
    check("en-XA: tags, entities and {placeholders} untouched",
          "<b>Anjou</b>" in r["p"] and "&amp;" in r["p"] and "<code>" in r["code"])
    check("en-XA: an engine message with an English template is shown pseudo-localised",
          r["srv"].startswith("[4 ûñîţš"))
    r = node("ar-XB", "en")
    check("ar-XB: the page is right to left, the text wrapped in a right-to-left override",
          r.get("dir") == "rtl" and r["plain"] == "‮Save‬" and "<b>" in r["p"])
    r = node("pl", "", {"a.plain": "Zapisz", "a.pl": {"one": "{count} plik", "few": "{count} pliki",
                                                        "many": "{count} plików", "other": "{count} pliku"}})
    check("a real locale: its string, the English for what it lacks",
          r.get("plain") == "Zapisz" and r["code"] == "<code>descr_strat.txt</code> read")
    check("Polish plurals by CLDR: 1 plik, 2 pliki, 5 plików, 22 pliki, 1,5 pliku",
          r["pl"] == ["1 plik", "2 pliki", "5 plików", "22 pliki", "1,5 pliku"])
    check("ttA escapes a translation's quotes", node("pl", "", {"a.plain": 'l\'"x"'})["attr"] == "l&#39;&quot;x&quot;")
    check("an engine message with no translation stays English", r["srv"] == "4 units")
    r = node("pl", "", {"eng.t.m": "{n} jednostki"})
    check("and with one, it is swapped in", r.get("srv") == "4 jednostki")
else:
    print("  (node not installed: skipped)")

# ---- 5) over HTTP --------------------------------------------------------------------------------
print("\n5) over HTTP")
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8"), r.headers.get("Content-Type", "")


body, ctype = get("/i18n/catalogue.js", {"Accept-Language": "de-DE,de;q=0.9"})
check("catalogue.js: a script, English when nothing else has a catalogue",
      "javascript" in ctype and '"lang":"en"' in body)
config.save_settings(ui_lang="ar-XB")
body, _c = get("/i18n/catalogue.js")
check("the Settings choice wins, and brings its direction", '"lang":"ar-XB"' in body and '"dir":"rtl"' in body)
body, ctype = get("/i18n/en.json")
check("en.json is served, for the fallback", "json" in ctype and json.loads(body)["_meta"]["status"] == "source")
page, _c = get("/")
check("index.html loads the catalogue and i18n.js before core.js",
      page.index("i18n/catalogue.js") < page.index("js/i18n.js") < page.index("js/core.js"))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
