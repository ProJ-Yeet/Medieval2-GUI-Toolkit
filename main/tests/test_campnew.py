"""Making a new campaign out of one that is already there (24, M15).

    python -m tests.test_campnew

One little mod written here with a campaign folder that has the shape a real one
has: a ``descr_strat.txt`` that opens on ``campaign <name>``, four files beside
it, a subfolder, a stale ``map.rwm`` that must not travel, and a description file
whose keys are built from the campaign's own folder name.

What the suite is about is the three things a plain folder copy gets wrong - the
compiled map, the header, and the menu keys - and then the two answers to "where
does it go": directly under ``world/maps/campaign``, which is what the engine's
new-game menu reads, or nested, which this toolkit can open and the menu cannot.
Then every installed mod, where a copy is planned for real and never applied.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campfiles, campnew, campstrat, config, stringsbin
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little mod ----------------------------------------------------------

STRAT = """; the grand campaign
campaign imperial_campaign
playable
\tengland
end
unlockable
end
nonplayable
\tslave
end

start_date 1080 summer
end_date 1530 winter

faction\tengland, balanced smith
\tdenari\t10000
"""

WINS = "england\nhold_regions Alpha\ntake_regions 1\n"
MERCS = "pool Northern\n\tregions Alpha\n"
SCRIPT = "script\n\nend_script\n"
MOVIES = '<faction_movies>\n</faction_movies>'

DESCR = {
    "IMPERIAL_CAMPAIGN_TITLE": "The Grand Campaign",
    "IMPERIAL_CAMPAIGN_DESCR": "Everything, everywhere.",
    "IMPERIAL_CAMPAIGN_ENGLAND_TITLE": "England",
    "IMPERIAL_CAMPAIGN_ENGLAND_DESCR": "A wet island.",
    "SOMETHING_ELSE_TITLE": "Not a campaign key at all",
}


def tiny_mod(root: Path) -> Mod:
    camp = (root / "data" / campstrat.CAMPAIGN_DIR_REL
            / campstrat.DEFAULT_CAMPAIGN)
    camp.mkdir(parents=True, exist_ok=True)
    (camp / campstrat.STRAT_NAME).write_text(STRAT, encoding="latin-1")
    (camp / "descr_win_conditions.txt").write_text(WINS, encoding="latin-1")
    (camp / "descr_mercenaries.txt").write_text(MERCS, encoding="latin-1")
    (camp / "campaign_script.txt").write_text(SCRIPT, encoding="latin-1")
    (camp / "descr_faction_movies.xml").write_text(MOVIES, encoding="latin-1")
    (camp / "map.rwm").write_bytes(b"the compiled map, which must not travel")
    (camp / "fmv").mkdir(exist_ok=True)
    (camp / "fmv" / "intro.bik").write_bytes(b"movie")

    text = root / "data" / "text"
    text.mkdir(parents=True, exist_ok=True)
    (text / "campaign_descriptions.txt").write_text(
        "﻿" + "".join(f"{{{k}}}{v}\r\n" for k, v in DESCR.items()),
        encoding="utf-16")
    return Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"

med2 = Path(_tmp.mkdtemp(prefix="ut_campnew_"))
mod = tiny_mod(med2 / "mods" / "Tiny")
print("  one campaign, six files, a subfolder and a stale map.rwm")


# ---- 1) what can be copied ---------------------------------------------------
print("\n1) the sources, and what a copy would cost")

v = campnew.view(mod)
check(f"     the engine's menu reads the folders directly under "
      f"{v['dir']}: {v['menu']}", v["menu"] == [campstrat.DEFAULT_CAMPAIGN])
src = v["sources"][0]
check(f"     {src['campaign']}: {src['files']} file(s), {src['bytes']:,} bytes, "
      f"{src['keys']} description key(s), titled {src['title']!r}",
      src["files"] == 6 and src["keys"] == 4
      and src["title"] == "The Grand Campaign")
check("     map.rwm is not counted, because a copy will not take it",
      src["files"] == len(list((Path(mod.data) / src["folder"]).rglob("*"))) - 2)


# ---- 2) the refusals ---------------------------------------------------------
print("\n2) what a new campaign will not be called")

for name, why in (("", "a new campaign needs a name"),
                  ("My Campaign", "will not do as a folder name"),
                  ("2nd_try", "will not do as a folder name"),
                  ("../escape", "will not do as a folder name"),
                  (campstrat.DEFAULT_CAMPAIGN, "is already there")):
    p = campnew.plan(mod, {"source": campstrat.DEFAULT_CAMPAIGN, "name": name})
    check(f"     {name!r}: {why}", p.errors and why in p.errors[0])

p = campnew.plan(mod, {"source": "no_such_campaign", "name": "Fresh"})
check("     a source that is not a campaign is refused by name",
      p.errors and campstrat.STRAT_NAME in p.errors[0])
p = campnew.plan(mod, {"source": "", "name": "Fresh"})
check("     and so is no source at all, because a new campaign is a copy of one "
      "that works", p.errors and "copied from one that already works" in p.errors[0])


# ---- 3) the plan -------------------------------------------------------------
print("\n3) the three things a folder copy gets wrong")

p = campnew.plan(mod, {"source": campstrat.DEFAULT_CAMPAIGN, "name": "Fresh_Start",
                       "title": "A Fresh Start", "blurb": "Smaller, and new."})
check(f"     no errors, {p.files} file(s) planned", not p.errors and p.files == 6)
said = "\n".join(p.changes)
check("     map.rwm is left behind, and the change line says why",
      p.skipped == ["map.rwm"] and "compiled map" in said)
check("     the subfolder travels with the rest",
      any(rel.endswith("fmv/intro.bik") for _, rel in p.copies))
check("     the header stops claiming to be the campaign it came from",
      "`campaign imperial_campaign` -> `campaign Fresh_Start`" in said)
rel = f"{campstrat.CAMPAIGN_DIR_REL}/Fresh_Start/{campstrat.STRAT_NAME}"
check("     and that is the only line of the file that changed, comment and all",
      rel in p.texts
      and p.texts[rel].splitlines()[0] == "; the grand campaign"
      and p.texts[rel].count("\n") == STRAT.count("\n"))
check("     the strat is planned as a text rather than copied, so it is written "
      "once", not any(r == rel for _, r in p.copies))

keys = p.loc_writes
check(f"     all four of the source's description keys come across under the "
      f"new token, and the key that is not a campaign's does not: {sorted(keys)}",
      sorted(keys) == ["FRESH_START_DESCR", "FRESH_START_ENGLAND_DESCR",
                       "FRESH_START_ENGLAND_TITLE", "FRESH_START_TITLE"])
check("     the faction pair is inherited as it stands - it is the same faction",
      keys["FRESH_START_ENGLAND_TITLE"] == "England"
      and keys["FRESH_START_ENGLAND_DESCR"] == "A wet island.")
check("     the campaign's own two are what was typed, not what was inherited",
      keys["FRESH_START_TITLE"] == "A Fresh Start"
      and keys["FRESH_START_DESCR"] == "Smaller, and new.")
check("     every one of them is new to the file", len(p.loc_new) == 4)

q = campnew.plan(mod, {"source": campstrat.DEFAULT_CAMPAIGN, "name": "Copycat"})
check("     a copy with no title of its own inherits one, and is told that two "
      "campaigns now read the same on the menu",
      q.loc_writes["COPYCAT_TITLE"] == "The Grand Campaign"
      and any("read the same on the menu" in w for w in q.warnings))

n = campnew.plan(mod, {"source": campstrat.DEFAULT_CAMPAIGN,
                       "name": "custom/Nested", "title": "Nested"})
check("     a nested campaign is offered and warned about: this screen opens it "
      "and the engine's menu does not",
      not n.errors and n.name == "custom/Nested"
      and any("new-game menu reads the folders directly" in w
              for w in n.warnings))
check("     and its keys are built from the folder's own name, not the path it "
      "is reached through", "NESTED_TITLE" in n.loc_writes)


# ---- 4) the save -------------------------------------------------------------
print("\n4) applied, and read back off disk")

res = campnew.apply(p)
home = Path(mod.data) / campstrat.CAMPAIGN_DIR_REL / "Fresh_Start"
check(f"     one log entry, {res['files']} file(s) written",
      bool(res["id"]) and res["files"] == 6)
man = res["record"]["manifest"]
check(f"     the six campaign files are all `created`, because the folder was "
      f"not there a moment ago, and the only thing backed up is the description "
      f"file the keys go into: {man['backed_up']}",
      len([r for r in man["created"] if "/Fresh_Start/" in r]) == 6
      and all(r.startswith("text/campaign_descriptions.txt")
              for r in man["backed_up"]))
check("     the new campaign is on the engine's menu list",
      campstrat.campaigns(mod) == ["Fresh_Start", campstrat.DEFAULT_CAMPAIGN])
check("     its start position parses and opens on its own name",
      campstrat.read_strat(mod, "Fresh_Start").campaign == "Fresh_Start")
check("     the source is untouched",
      campstrat.read_strat(mod, campstrat.DEFAULT_CAMPAIGN).campaign
      == campstrat.DEFAULT_CAMPAIGN)
check("     map.rwm did not travel", not (home / "map.rwm").exists()
      and (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
           / campstrat.DEFAULT_CAMPAIGN / "map.rwm").exists())
check("     the subfolder and its file came across byte for byte",
      (home / "fmv" / "intro.bik").read_bytes() == b"movie")
check("     the other four files came across unchanged",
      (home / "descr_win_conditions.txt").read_text("latin-1") == WINS
      and (home / "descr_mercenaries.txt").read_text("latin-1") == MERCS
      and (home / "campaign_script.txt").read_text("latin-1") == SCRIPT
      and (home / "descr_faction_movies.xml").read_text("latin-1") == MOVIES)

pairs = campfiles.descr_pairs(mod)
check("     the menu now names the new campaign, and still names the old one",
      pairs.get("FRESH_START_TITLE") == "A Fresh Start"
      and pairs.get("IMPERIAL_CAMPAIGN_TITLE") == "The Grand Campaign"
      and pairs.get("SOMETHING_ELSE_TITLE") == "Not a campaign key at all")
check("     and the browser reads the new campaign as a campaign of its own",
      next(r for r in campfiles.browse(mod)["campaigns"]
           if r["campaign"] == "Fresh_Start")["title"] == "A Fresh Start")
check("     a second copy under the same name is refused rather than merged",
      campnew.plan(mod, {"source": campstrat.DEFAULT_CAMPAIGN,
                         "name": "Fresh_Start"}).errors)


# ---- 5) the routes -----------------------------------------------------------
print("\n5) the three routes the panel uses")

import json
import threading
import urllib.request

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    d = get("/api/campnew?mod=Tiny")
    check(f"     GET /api/campnew offers both campaigns to copy and says which "
          f"of them the engine's menu lists: {d['menu']}",
          len(d["sources"]) == 2 and d["menu"] == ["Fresh_Start",
                                                   campstrat.DEFAULT_CAMPAIGN]
          and d["have_descriptions"])

    r = post("/api/campnew/plan", {"mod": "Tiny", "source": "Fresh_Start",
                                   "name": "Third_Go", "title": "Third go"})
    check(f"     POST /api/campnew/plan works it out and writes nothing: "
          f"{r['plan']['files']} file(s)",
          r["plan"]["ok"] and r["plan"]["files"] == 6
          and campstrat.campaigns(mod) == ["Fresh_Start",
                                           campstrat.DEFAULT_CAMPAIGN])
    bad = post("/api/campnew/plan", {"mod": "Tiny", "source": "Fresh_Start",
                                     "name": "Third Go"})
    check("     a name the engine could not read comes back as the reason",
          bad.get("error") and "folder name" in bad["error"])

    r = post("/api/campnew/apply", {"mod": "Tiny", "source": "Fresh_Start",
                                    "name": "Third_Go", "title": "Third go"})
    check("     POST /api/campnew/apply writes it and answers with the log id",
          r.get("id") and r.get("name") == "Third_Go")
    check("     and the third campaign is on the menu, copied from the second",
          campstrat.campaigns(mod) == ["Fresh_Start", "Third_Go",
                                       campstrat.DEFAULT_CAMPAIGN]
          and campstrat.read_strat(mod, "Third_Go").campaign == "Third_Go"
          and campfiles.descr_pairs(mod)["THIRD_GO_TITLE"] == "Third go")
    r = post("/api/campnew/apply", {"mod": "Tiny", "source": "Fresh_Start",
                                    "name": "Third_Go"})
    check("     a second copy under a name that is now taken is a refusal, not "
          "a merge", bool(r.get("error")))
finally:
    httpd.shutdown()


# ---- 6) every installed mod --------------------------------------------------
print("\n6) a real mod, planned and not applied")

import time

seen = False
for root in _realmod.installed():
    rmod = Mod(root)
    camps = campstrat.campaign_paths(rmod)
    if not camps:
        continue
    seen = True
    for source in camps:
        t0 = time.perf_counter()
        rp = campnew.plan(rmod, {"source": source, "name": "Toolkit_Test",
                                 "title": "Toolkit test"})
        ms = int((time.perf_counter() - t0) * 1000)
        check(f"     {rmod.name}/{source}: {rp.files} file(s), "
              f"{rp.bytes / 1e6:.1f} MB, {len(rp.loc_writes)} menu key(s), "
              f"{len(rp.warnings)} warning(s), {ms} ms",
              not rp.errors and rp.files > 1 and rp.name == "Toolkit_Test")
        check(f"     {rmod.name}/{source}: the header is rewritten and the "
              f"campaign still parses",
              all(campstrat.parse_strat(t).campaign == "Toolkit_Test"
                  for rel, t in rp.texts.items()
                  if rel.endswith(campstrat.STRAT_NAME))
              or not any(rel.endswith(campstrat.STRAT_NAME)
                         for rel in rp.texts))
        check(f"     {rmod.name}/{source}: nothing it would write is inside the "
              f"campaign it is copying",
              not any(f"/{source}/" in rel or rel.endswith(f"/{source}")
                      for _, rel in rp.copies))

if not seen:
    print("  SKIPPED - no installed mod has a campaign")

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
