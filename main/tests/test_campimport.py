"""Phase 73, M7: a campaign imported from another mod.

    python -m tests.test_campimport

ROCSS's imperial campaign (a historical map of 449 provinces) into a copy of
Divide and Conquer (Middle-earth), the hardest pair installed: almost no unit,
building, trait, religion or rebel type in common, and seven factions with no
slot of their name. The source is a copy of what the import reads; the
destination a copy of the files it checks against and writes.

1. The view lists the source's campaigns.
2. The plan: every faction on a distinct declared slot; every regiment,
   building, trait, ancillary, resource, religion, rebel type and creator the
   written files name is one the destination has; religions total 100; the
   header is the new name; a planned import writes nothing.
3. Choices: a substituted unit, a chosen slot, a chosen religion are what is
   written; two factions on one slot, a slot the mod lacks, a folder already
   there and the same mod twice are refused.
4. Applied: the campaign reads back with its own map, names in the pool, the
   menu title; the destination's base map is untouched; one Undo restores
   every file byte for byte and takes the folder away.
5. The routes: GET /api/campimport and POST /api/campimport/plan|apply.
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import (campfiles, campimport as ci, campmap, campstrat,  # noqa: E402
                          config, minorfiles, modflags, namekeys, transfer)
from unittransfer.keyblock import read_text  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
CAMP = "imperial_campaign"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


roc, dac = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
if not ((roc / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP).is_dir()
        and (dac / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP).is_dir()):
    print("SKIPPED - needs both ROCSS and Divide_and_Conquer_EUR installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

DATA_FILES = ("export_descr_unit.txt", "export_descr_buildings.txt",
              "export_descr_character_traits.txt", "export_descr_ancillaries.txt",
              "descr_names.txt", "descr_sm_factions.txt", "descr_religions.txt",
              "descr_rebel_factions.txt", "descr_sm_resources.txt", "descr_cultures.txt",
              "descr_campaign_ai_db.xml", "descr_hero_abilities.xml", "descr_climates.txt")
TEXTS = ("names.txt", "imperial_campaign_regions_and_settlement_names.txt",
         "historic_events.txt", "campaign_descriptions.txt")


def copy_files(src: Path, data: Path, rels) -> None:
    for rel in rels:
        for suffix in ("", ".strings.bin"):
            f = src / "data" / (rel + suffix)
            if f.is_file():
                (data / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, data / (rel + suffix))


def copy_source(src: Path, med2: Path, name: str) -> Path:
    """What an import reads: the campaign folder, the base map, the text."""
    from unittransfer import projectzip
    data = med2 / "mods" / name / "data"
    home = src / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
    for p in home.rglob("*"):
        if p.is_file() and not projectzip.side_file(p.name) \
                and p.name.lower() != campmap.RWM_NAME:
            out = data / campstrat.CAMPAIGN_DIR_REL / CAMP / p.relative_to(home)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)
    base = data / campmap.BASE_REL
    base.mkdir(parents=True, exist_ok=True)
    for n in campmap.ALL_FILES:
        if (src / "data" / campmap.BASE_REL / n).is_file():
            shutil.copy2(src / "data" / campmap.BASE_REL / n, base / n)
    copy_files(src, data, ["descr_sm_factions.txt"] + [f"text/{t}" for t in TEXTS])
    if (src / "data" / ci.PORTRAITS_REL).is_dir():
        shutil.copytree(src / "data" / ci.PORTRAITS_REL, data / ci.PORTRAITS_REL)
    return data.parent


def copy_dest(src: Path, med2: Path, name: str) -> Path:
    """What an import checks against and writes: the data files, the text,
    the base map and the mod's own campaign."""
    data = med2 / "mods" / name / "data"
    copy_files(src, data, list(DATA_FILES) + [f"text/{t}" for t in TEXTS]
               + [f"{campmap.BASE_REL}/{n}" for n in ("descr_regions.txt", "descr_terrain.txt",
                                                       "map_regions.tga")]
               + [f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{campstrat.STRAT_NAME}"])
    return data.parent


def snapshot(mod):
    return {p.relative_to(mod.data).as_posix(): p.read_bytes()
            for p in Path(mod.data).rglob("*") if p.is_file()}


med2 = Path(_tmp.mkdtemp(prefix="ut_cimp_"))
S = Mod(copy_source(roc, med2, "ImportFrom"))
D = Mod(copy_dest(dac, med2, "ImportInto"))
modflags.set_m2ex(D, True)          # ROCSS's 449 provinces, read as M2EX
NAME = "Imported_ROCSS"

print("1) the view")
v = ci.view(S, D)
check("the source's imperial campaign is offered",
      any(r["campaign"] == CAMP for r in v["campaigns"]))

print("\n2) the plan")
before = snapshot(D)
p = ci.plan(S, D, {"campaign": CAMP, "name": NAME, "title": "Europe, Imported"})
check(f"it plans with no error ({'; '.join(p.errors)[:200]})", not p.errors and p.payload()["ok"])
check("and a plan writes nothing", snapshot(D) == before)
slots = {s["slot"].lower() for s in p.slots}
held = [f for f in p.factions if not f["only_creator"]]
check(f"every one of the {len(held)} factions is on a slot {D.name} declares",
      held and all(f["slot"].lower() in slots for f in held))
check("and no two share one", len({f["slot"].lower() for f in held}) == len(held))
strat_rel = f"{campstrat.CAMPAIGN_DIR_REL}/{NAME}/{campstrat.STRAT_NAME}"
regions_rel = f"{campstrat.CAMPAIGN_DIR_REL}/{NAME}/descr_regions.txt"
sf = campstrat.parse_strat(p.texts[strat_rel])
d = ci.Destination(D, sf)
check("the header names the new campaign", sf.campaign.lower() == NAME.lower()
      or sf.lines[next(i for i, l in enumerate(sf.lines) if l.strip()
                       and not l.strip().startswith(";"))].split()[-1] == NAME)
check("every faction block is a declared slot",
      all(n.name.lower() in slots for n in sf.of_kind("faction")))
units = [u.name for u in sf.of_kind("unit")]
check(f"all {len(units)} regiments written are units {D.name} has",
      units and all(u.lower() in d.units for u in units))
empty = [c.name for c in sf.of_kind("character") for a in sf.children_of(c, "army")
         if not sf.children_of(a, "unit")]
said = next((w for w in p.warnings if "no regiment left" in w), "")
check(f"every army keeps a regiment but the {len(empty)} the plan names",
      all(n in said for n in empty[:8]) and (bool(said) == bool(empty)))
blds = sf.of_kind("building")
check(f"all {len(blds)} buildings are levels {D.name}'s EDB declares on their own line",
      all((d.levels.get(str(b.get("level")).lower()) or "").lower() == b.name.lower()
          for b in blds))
traits = [t for c in sf.of_kind("character") for t in (c.get("traits") or {})]
check(f"all {len(traits)} traits are ones {D.name} has",
      all(t.lower() in d.traits for t in traits))
check("and no trait is above its top level",
      all(lv <= (d.traits[t.lower()][1] or lv) for c in sf.of_kind("character")
          for t, lv in (c.get("traits") or {}).items()))
ancs = [a for c in sf.of_kind("character") for a in (c.get("ancillaries") or [])]
check(f"all {len(ancs)} ancillaries are ones {D.name} has",
      all(a.lower() in d.ancillaries for a in ancs))
check("every resource on the map is a trade resource it has",
      all(r.name.lower() in d.trade for r in sf.of_kind("resource")))
rf = campmap.parse_regions(p.texts[regions_rel])
rels = {r.lower() for r in d.religions}
check("every province's religions are its own and total 100",
      all(r.religion_total == 100 and all(n.lower() in rels for n in r.religions)
          for r in rf.records if r.religions))
rebs = {r.lower() for r in d.rebels}
check("every rebel type is one it declares",
      all(r.rebels.lower() in rebs for r in rf.records if r.rebels))
check("every creator faction is one of its slots",
      all(r.faction.lower() in slots for r in rf.records if r.faction))
check("every hidden resource is one it declares",
      all(x.lower() in d.hidden or x.lower() in d.trade
          for r in rf.records for x in r.resources))
check("the map comes with it: every layer and descr_terrain.txt",
      {Path(rel).name for _, rel in p.copies} >= set(ci.MAP_FILES) - {"descr_regions.txt"})
check("the side copies are left behind and named",
      not any(" " in Path(rel).name for _, rel in p.copies))

print("\n3) choices and refusals")
some = next(u for u in p.units if u["how"] == "left out")
lith = next(f for f in held if f["how"] == "free")
other = next(s["slot"] for s in p.slots
             if s["slot"].lower() not in {f["slot"].lower() for f in held})
rel_missing = p.religions[0]["religion"] if p.religions else ""
body = {"campaign": CAMP, "name": NAME, "units": {some["unit"]: p.unit_names[0]},
        "factions": {lith["source"]: other},
        "religions": {rel_missing: d.religions[-1]} if rel_missing else {}}
q = ci.plan(S, D, body)
check("a chosen unit stands in for the missing one",
      next(u for u in q.units if u["unit"] == some["unit"])["to"] == p.unit_names[0]
      and p.unit_names[0] in {u.name for u in campstrat.parse_strat(
          q.texts[strat_rel]).of_kind("unit")})
check(f"{lith['source']} plays as the slot picked for it",
      next(f for f in q.factions if f["source"] == lith["source"])["slot"] == other)
if rel_missing:
    check(f"{rel_missing} goes where it was sent",
          next(r for r in q.religions if r["religion"] == rel_missing)["to"] == d.religions[-1])
a, b = held[0]["source"], held[1]["source"]
r = ci.plan(S, D, {"campaign": CAMP, "name": NAME, "factions": {a: held[1]["slot"],
                                                               b: held[1]["slot"]}})
check("two factions on one slot are refused", any("share a slot" in e for e in r.errors))
r = ci.plan(S, D, {"campaign": CAMP, "name": NAME, "factions": {a: "no_such_slot"}})
check("a slot the mod lacks is refused", any("declares" in e for e in r.errors))
r = ci.plan(S, D, {"campaign": CAMP, "name": CAMP})
check("a folder that is already there is refused", any("already there" in e for e in r.errors))
r = ci.plan(S, S, {"campaign": CAMP, "name": NAME})
check("the same mod twice is refused", bool(r.errors))
r = ci.plan(S, D, {"campaign": CAMP, "name": "9lives"})
check("a folder name that is not a bare word is refused", bool(r.errors))

print("\n4) applied, and undone")
res = ci.apply(p)
D = Mod(D.root)
home = Path(D.data) / campstrat.CAMPAIGN_DIR_REL / NAME
check("the campaign folder is there", (home / campstrat.STRAT_NAME).is_file())
check("and the menu lists it", NAME in campstrat.campaigns(D))
back = campstrat.read_strat(D, NAME)
check("it reads back as written", back.serialise() == p.texts[strat_rel])
cm = campmap.campaign_map(D, NAME)
check("it reads its own map", cm.home is not None
      and len(cm.regions.records) == len(rf.records))
after = snapshot(D)
check("the destination's base map is untouched",
      all(after[k] == before[k] for k in before if k.startswith(campmap.BASE_REL)))
check("and so is its own campaign",
      after[f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{campstrat.STRAT_NAME}"]
      == before[f"{campstrat.CAMPAIGN_DIR_REL}/{CAMP}/{campstrat.STRAT_NAME}"])
nf = minorfiles.parse_names(read_text(Path(D.data) / namekeys.POOL_REL, namekeys.ENCODING))
missing = []
for n in back.of_kind("faction"):
    fac = nf.get(n.name)
    pool = {e.value for s in (fac.sections if fac else []) for e in s.entries}
    for c in back.descendants_of(n, "character"):
        first, sur = namekeys.name_parts(c.name)
        missing += [x for x in (first, sur) if x and x not in pool]
check(f"every character's name is in its slot's pool ({len(missing)} not)", not missing)
pairs = campfiles.descr_pairs(D)
check("the menu title is written", pairs.get(campfiles.descr_token(NAME) + "_TITLE")
      == "Europe, Imported")
keys = namekeys.loc_pairs(D, campmap.REGION_NAMES_REL)
check("every province of the map has its name key",
      all(r.name in keys for r in rf.records if r.name))
transfer.undo(res["id"])
check("one Undo puts every file back byte for byte", snapshot(D) == before)
check("and the folder holds nothing", not any(p_.is_file() for p_ in home.rglob("*"))
      if home.exists() else True)

print("\n5) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))


g = get("/api/campimport?mod=ImportInto&from=ImportFrom")
check("GET /api/campimport lists the source's campaigns",
      any(c["campaign"] == CAMP for c in g.get("campaigns", [])))
body = {"mod": "ImportInto", "from": "ImportFrom", "campaign": CAMP, "name": NAME}
pl = post("/api/campimport/plan", body)
if not pl.get("plan", {}).get("ok"):
    print("   ", pl.get("error"), (pl.get("plan") or {}).get("errors"))
check("POST plan works it out and writes nothing",
      pl.get("plan", {}).get("ok") and snapshot(D) == before)
res = post("/api/campimport/apply", body)
check("POST apply writes it", res.get("id") and not res.get("error")
      and (home / campstrat.STRAT_NAME).is_file())
transfer.undo(res["id"])
check("and the Undo takes it back", snapshot(D) == before)
bad = post("/api/campimport/plan", dict(body, **{"from": "ImportInto"}))
check("the same mod twice is refused over the route too", bool(bad.get("error")))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
