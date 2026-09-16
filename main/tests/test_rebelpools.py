"""Rebels right in place - the province and the rebel faction, both ways (35).

    python -m tests.test_rebelpools

One little mod with the two files the join is over: a ``descr_rebel_factions.txt``
carrying every shape the real ones have - tabs between the keyword and the value,
a block per non-``peasant_revolt`` category, a ``chance 0`` block, a block no
province names and a block naming a unit the EDU does not have - and a
``descr_regions.txt`` in the awkward form, with and without the ``legion:`` line.

**The suite is about the reverse direction and what it must not call a fault.**
Three blocks that no province names are correct on every real mod, because the
engine spawns them by category; a fourth is a real orphan. ``chance 0`` is an
assignment that does nothing and is legal - Reforged sets it on every block its
provinces name - so it is a warning that fires and never a refusal.

Section 6 is the phase's other half and the defect it led with: a region record
is written back to the ``descr_regions.txt`` the CAMPAIGN reads, not always the
base one, and the stale ``map.rwm`` that goes with it is that campaign's.

Section 8 plans against every installed mod for real and never applies.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, config, rebelpools as rp
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little mod ----------------------------------------------------------

# Tabs between keyword and value, CRLF, one block per engine category, a silent
# block, an orphan and a dead unit reference - every shape measured on the two
# installed mods plus the two states they do not have.
REBELS = (
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    "; the rebels\r\n"
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    "\r\n"
    "rebel_type\t\tNorth_Rebels\r\n"
    "category\t\tpeasant_revolt\r\n"
    "chance\t\t\t4\r\n"
    "description\t\tNorth_Rebels\r\n"
    "unit\t\t\tPeasant Spearmen\r\n"
    "unit\t\t\tTown Militia\r\n"
    "\r\n"
    "rebel_type\t\tSouth_Rebels\r\n"
    "category\t\tpeasant_revolt\r\n"
    "chance\t\t\t0\r\n"
    "description\t\tSouth_Rebels\r\n"
    "unit\t\t\tPeasant Spearmen\r\n"
    "\r\n"
    "rebel_type\t\tLost_Rebels\r\n"
    "category\t\tpeasant_revolt\r\n"
    "chance\t\t\t7\r\n"
    "description\t\tLost_Rebels\r\n"
    "unit\t\t\tNo Such Unit\r\n"
    "\r\n"
    "rebel_type\t\tbrigands\r\n"
    "category\t\tbrigands\r\n"
    "chance\t\t\t50\r\n"
    "description\t\tbrigands\r\n"
    "unit\t\t\tBrigands\r\n"
    "\r\n"
    "rebel_type\t\tpirates\r\n"
    "category\t\tpirates\r\n"
    "chance\t\t\t50\r\n"
    "description\t\tpirates\r\n"
    "unit\t\t\tPirates\r\n"
    "\r\n"
    "rebel_type\t\tgladiator_uprising\r\n"
    "category\t\tgladiator_revolt\r\n"
    "chance\t\t\t100\r\n"
    "description\t\tgladiator_uprising\r\n"
    "unit\t\t\tGladiators\r\n"
)

# Four provinces. Two in the legion form, two not - which is the shape Phase 40
# had to teach the parser - and one naming a rebel type nothing declares.
REGIONS = (
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    "\r\n"
    "Alpha_Province\r\n"
    "\tlegion:\tFirst\r\n"
    "\tAlphaton\r\n"
    "\tnorthmen\r\n"
    "\tNorth_Rebels\r\n"
    "\t10 20 30\r\n"
    "\tgold\r\n"
    "\t2\r\n"
    "\treligions { catholic 50 orthodox 50 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Beta_Province\r\n"
    "\tBetaton\r\n"
    "\tnorthmen\r\n"
    "\tNorth_Rebels\r\n"
    "\t40 50 60\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 50 orthodox 50 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Gamma_Province\r\n"
    "\tGammaton\r\n"
    "\tnorthmen\r\n"
    "\tSouth_Rebels\r\n"
    "\t70 80 90\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 50 orthodox 50 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Delta_Province\r\n"
    "\tDeltaton\r\n"
    "\tnorthmen\r\n"
    "\tGhost_Rebels\r\n"
    "\t11 22 33\r\n"
    "\tnone\r\n"
    "\t2\r\n"
    "\treligions { catholic 50 orthodox 50 islam 0 heretic 0 }\r\n"
)


def little_mod(rebels=True):
    root = Path(_tmp.mkdtemp(prefix="ut_reb_"))
    data = root / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    kb.write_text(data / campmap.REGIONS_REL, REGIONS, campmap.ENCODING)
    if rebels:
        kb.write_text(data / rp.REBELS_REL, REBELS, campmap.ENCODING)
    return Mod(root)


class FakeMap:
    """Just enough :class:`campmap.CampaignMap` for the join - the file and a home.

    The real one decodes ten TGA layers and the little mod has none. What the
    reverse list actually reads is ``cm.regions`` and ``cm.home``/``cm.base``
    for :func:`campmap.rel_of`, so those three are what this carries - which is
    also the proof the join needs no layer, and the reason the route asks for a
    map and never requires one.
    """

    def __init__(self, mod, home=None):
        self.mod = mod
        self.base = Path(mod.data) / campmap.BASE_REL
        self.home = home
        path = (home / "descr_regions.txt") if home is not None else None
        if path is not None and path.is_file():
            self.regions = campmap.parse_regions(
                kb.read_text(path, campmap.ENCODING))
            self.regions.path = path
        else:
            self.regions = campmap.read_regions(mod)


# every write in sections 7 and 9 goes into a scratch config, never the real one
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"


# ---- 1: the two files are read as they stand ---------------------------------

print("\n1. the little mod, read")

mod = little_mod()
cm = FakeMap(mod)

rf = rp.read_rebels(mod)
check(f"  descr_rebel_factions.txt: {len(rf.records)} blocks",
      len(rf.records) == 6)
check("  a block's unit lines are its repeats, tabs and spaces kept",
      [r.value for r in rf.get("North_Rebels").repeats]
      == ["Peasant Spearmen", "Town Militia"])
check("  a mod with no such file reads as empty rather than raising",
      len(rp.read_rebels(little_mod(rebels=False)).records) == 0)

used = rp.assignments(cm.regions)
check(f"  the reverse join: {len(used)} distinct values over 4 provinces",
      used == {"North_Rebels": ["Alpha_Province", "Beta_Province"],
               "South_Rebels": ["Gamma_Province"],
               "Ghost_Rebels": ["Delta_Province"]})
check("  and it reads the value off a record with a legion: line and one "
      "without, which is the same record in two shapes",
      used["North_Rebels"] == ["Alpha_Province", "Beta_Province"])


# ---- 2: the view, and the three states a row can be in -----------------------

print("\n2. the view")

v = rp.view(mod, cm)
rows = {r["name"]: r for r in v["rebels"]}
check(f"  {v['declared']} declared, {v['named']} named by a province, "
      f"{v['orphans']} orphan", (v["declared"], v["named"], v["orphans"])
      == (6, 2, 1))
check("  Lost_Rebels is the orphan: declared, region-driven and named by "
      "nothing", rows["Lost_Rebels"]["orphan"] and not rows["Lost_Rebels"]["count"])
check("  the three category blocks are NOT orphans, though no province names "
      "them either - the engine spawns them by category",
      all(rows[n]["by_category"] and not rows[n]["orphan"] and not rows[n]["count"]
          for n in ("brigands", "pirates", "gladiator_uprising")))
check("  South_Rebels is silent - chance 0, so its one province spawns nothing",
      rows["South_Rebels"]["silent"] and v["silent_regions"] == 1)
check("  North_Rebels is neither: chance 4, two provinces, two units",
      not rows["North_Rebels"]["silent"] and not rows["North_Rebels"]["orphan"]
      and rows["North_Rebels"]["count"] == 2
      and rows["North_Rebels"]["unit_count"] == 2)
check("  Ghost_Rebels is dangling - named by a province, declared nowhere",
      v["dangling"] == [{"name": "Ghost_Rebels",
                         "provinces": ["Delta_Province"], "count": 1}])
check("  and it is NOT in the rebel rows, because the rows are the declared "
      "file and a dangling value has no block to describe",
      "Ghost_Rebels" not in rows)
check("  no province is left without a value here", v["blank"] == [])
check("  the file named is the one the regions were read from",
      v["file"] == campmap.REGIONS_REL)


# ---- 3: the units, and the one join that can fail ----------------------------

print("\n3. what a rebel faction can field")

check("  with no EDU to read, a unit is neither known nor unknown - None, "
      "which is not the same answer as 'not in this mod'",
      all(u["known"] is None for u in rows["Lost_Rebels"]["units"]))
check("  and nothing is reported dead on a mod whose roster cannot be read",
      not any(r["dead_units"] for r in v["rebels"]))


class FakeEdu:
    def __init__(self, types):
        self.units = [type("U", (), {"type": t})() for t in types]


class ModWithEdu:
    """The little mod with a roster bolted on, so the EDU join has a true case."""

    def __init__(self, base, types):
        self._base = base
        self.edu = FakeEdu(types)

    def __getattr__(self, k):
        return getattr(self._base, k)


withedu = ModWithEdu(mod, ["Peasant Spearmen", "Town Militia", "Brigands",
                           "Pirates", "Gladiators"])
v3 = rp.view(withedu, FakeMap(withedu))
rows3 = {r["name"]: r for r in v3["rebels"]}
check("  with a roster, North_Rebels' two units are both in it",
      rows3["North_Rebels"]["dead_units"] == []
      and all(u["known"] for u in rows3["North_Rebels"]["units"]))
check("  and Lost_Rebels' one unit is named as not in the EDU",
      rows3["Lost_Rebels"]["dead_units"] == ["No Such Unit"])


# ---- 4: the move ------------------------------------------------------------

print("\n4. moving provinces onto a rebel faction")

p = rp.plan(mod, cm, {"rebel": "South_Rebels",
                      "regions": ["Alpha_Province", "Beta_Province"]})
check(f"  two provinces move: {p.changes}",
      p.changes == ["Alpha_Province: North_Rebels -> South_Rebels",
                    "Beta_Province: North_Rebels -> South_Rebels"])
check("  and the changes come back in the order they were picked, not the "
      "order they were spliced", p.changes[0].startswith("Alpha"))
after = campmap.parse_regions(p.text)
check("  the new file says so",
      [after.by_name(n).rebels for n in ("Alpha_Province", "Beta_Province")]
      == ["South_Rebels", "South_Rebels"])
check("  it is exactly two lines different and the file is the same length",
      len(after.lines) == len(cm.regions.lines)
      and sum(1 for a, b in zip(cm.regions.lines, after.lines) if a != b) == 2)
check("  every other province is untouched",
      [after.by_name(n).rebels for n in ("Gamma_Province", "Delta_Province")]
      == ["South_Rebels", "Ghost_Rebels"])
check("  the chance-0 target is a WARNING and not a refusal, because it is "
      "what a mod does to turn province rebels off",
      not p.errors and any("chance 0" in w for w in p.warnings))

p4 = rp.plan(mod, cm, {"rebel": "North_Rebels", "regions": ["Gamma_Province"]})
check("  a target with a real chance warns about nothing",
      not p4.warnings and not p4.errors)
p4b = rp.plan(mod, cm, {"rebel": "pirates", "regions": ["Gamma_Province"]})
check("  a category block warns that the engine does not reach it this way",
      any("by category" in w for w in p4b.warnings) and not p4b.errors)


# ---- 5: what it refuses -----------------------------------------------------

print("\n5. the refusals")

for body, want, why in (
        ({"rebel": "", "regions": ["Alpha_Province"]},
         "no rebel faction named", "no faction"),
        ({"rebel": "North_Rebels", "regions": []},
         "no provinces picked", "no provinces"),
        ({"rebel": "Ghost_Rebels", "regions": ["Alpha_Province"]},
         "is not a rebel faction", "a value nothing declares"),
        ({"rebel": "North_Rebels", "regions": ["Nowhere_Province"]},
         "no such province", "a province that is not on this map"),
        ({"rebel": "North_Rebels", "regions": ["Alpha_Province"]},
         "nothing to change", "a province that already names it")):
    q = rp.plan(mod, cm, body)
    check(f"  {why}: {(q.errors or ['(none)'])[0][:52]}",
          any(want in e for e in q.errors))
check("  the dangling value is refused as a TARGET even though a province "
      "already names it - which is the point, it is not a faction",
      any("is not a rebel faction" in e for e in
          rp.plan(mod, cm, {"rebel": "Ghost_Rebels",
                            "regions": ["Alpha_Province"]}).errors))


# ---- 6: the campaign's own copy, which is the defect this phase led with -----

print("\n6. which descr_regions.txt is written (22c, and the region save "
      "was not following it)")

camp_mod = little_mod()
home = Path(camp_mod.data) / "world/maps/campaign/custom/Own_Campaign"
home.mkdir(parents=True)
own = REGIONS.replace("North_Rebels", "South_Rebels")
kb.write_text(home / "descr_regions.txt", own, campmap.ENCODING)
base_cm, own_cm = FakeMap(camp_mod), FakeMap(camp_mod, home)

check("  the two files really differ, or this section proves nothing",
      base_cm.regions.by_name("Alpha_Province").rebels == "North_Rebels"
      and own_cm.regions.by_name("Alpha_Province").rebels == "South_Rebels")

pb = rp.plan(camp_mod, base_cm, {"rebel": "Lost_Rebels",
                                 "regions": ["Alpha_Province"]})
po = rp.plan(camp_mod, own_cm, {"rebel": "Lost_Rebels",
                                "regions": ["Alpha_Province"]})
check(f"  planned on the base map it writes {pb.rel}",
      pb.rel == campmap.REGIONS_REL)
check("  planned on the campaign it writes its own copy",
      po.rel == "world/maps/campaign/custom/Own_Campaign/descr_regions.txt")
check("  and the change it reports is against THAT file's value",
      po.changes == ["Alpha_Province: South_Rebels -> Lost_Rebels"]
      and pb.changes == ["Alpha_Province: North_Rebels -> Lost_Rebels"])

# the same rule, on the region save this phase corrected
rpl = campmap.plan_region(camp_mod, {"region": "Alpha_Province",
                                     "edits": {"rebels": "Lost_Rebels"}}, own_cm)
check("  campmap.plan_region takes the same map and names the same file",
      campmap.regions_rel(rpl)
      == "world/maps/campaign/custom/Own_Campaign/descr_regions.txt")
rpl_base = campmap.plan_region(camp_mod, {"region": "Alpha_Province",
                                          "edits": {"rebels": "Lost_Rebels"}})
check("  and passed no map at all it is the base file, so every caller that "
      "never had a campaign to give is unchanged",
      campmap.regions_rel(rpl_base) == campmap.REGIONS_REL)

# the stale compiled map, which is the other half of the same defect
(Path(camp_mod.data) / campmap.RWM_REL).write_bytes(b"base")
(home / "map.rwm").write_bytes(b"own")
check("  a write to the base file makes the base map.rwm stale",
      campmap.stale_rwm(camp_mod, campmap.REGIONS_REL)
      == [campmap.RWM_REL])
check("  a write to the campaign's copy makes THAT campaign's map.rwm stale "
      "and leaves the base one alone",
      campmap.stale_rwm(camp_mod, po.rel)
      == ["world/maps/campaign/custom/Own_Campaign/map.rwm"])


# ---- 7: applied, and read back off disk -------------------------------------

print("\n7. the save")

live = little_mod()
live_cm = FakeMap(live)
p7 = rp.plan(live, live_cm, {"rebel": "South_Rebels",
                             "regions": ["Alpha_Province", "Beta_Province"]})
res = rp.apply(p7)
check(f"  one log entry, id {str(res.get('id'))[:12]}…", bool(res.get("id")))
man = res["record"]["manifest"]
check("  descr_regions.txt was backed up before it was written",
      campmap.REGIONS_REL in man["backed_up"])
back = campmap.read_regions(live)
check("  read off disk: both provinces now name South_Rebels",
      [back.by_name(n).rebels for n in ("Alpha_Province", "Beta_Province")]
      == ["South_Rebels", "South_Rebels"])
check("  and the reverse list agrees with the file it just wrote",
      rp.assignments(back)["South_Rebels"]
      == ["Alpha_Province", "Beta_Province", "Gamma_Province"])
try:
    rp.apply(rp.plan(live, live_cm, {"rebel": "", "regions": []}))
    check("  a plan with errors refuses to apply", False)
except ValueError as exc:
    check(f"  a plan with errors refuses to apply: {str(exc)[:38]}…",
          "cannot apply" in str(exc))


# ---- 8: every installed mod, planned and never applied ----------------------

print("\n8. the installed mods")

mods = _realmod.installed()
if not mods:
    print("  SKIPPED - no installed mod")
else:
    for root in mods:
        real = Mod(root)
        try:
            rcm = campmap.CampaignMap(real)
        except Exception as exc:                      # noqa: BLE001
            print(f"  -- {real.name}: no map ({str(exc)[:40]})")
            continue
        rv = rp.view(real, rcm)
        print(f"  -- {real.name}")
        check(f"     {rv['regions']} provinces, {rv['declared']} rebel "
              f"factions, {rv['named']} of them named",
              rv["regions"] > 0 and rv["declared"] > 0)
        check(f"     nothing dangles - every value a province names is "
              f"declared ({len(rv['dangling'])})", not rv["dangling"])
        cats = [r for r in rv["rebels"] if r["by_category"]]
        check(f"     exactly one block per engine category, and no province "
              f"is meant to name them ({len(cats)})",
              len(cats) == 3
              and sorted(c["category"] for c in cats) == sorted(rp.BY_CATEGORY))
        check("     and not one of them is counted as an orphan",
              not any(c["orphan"] for c in cats))
        dead = [(r["name"], r["dead_units"]) for r in rv["rebels"]
                if r["dead_units"]]
        check(f"     every unit line names a unit the EDU has ({len(dead)} "
              f"that do not)", not dead)
        # the phase's finding, said as a check rather than as a claim
        silent = [r for r in rv["rebels"] if r["silent"] and r["count"]]
        print(f"       chance 0 on {len(silent)} named block(s), covering "
              f"{rv['silent_regions']} of {rv['regions']} provinces")
        orph = [r["name"] for r in rv["rebels"] if r["orphan"]]
        print(f"       orphans: {orph or 'none'}")

        # a plan against the real file, never applied
        first = rcm.regions.records[0]
        target = next((r["name"] for r in rv["rebels"]
                       if not r["by_category"] and r["name"] != first.rebels), "")
        if target:
            q = rp.plan(real, rcm, {"rebel": target, "regions": [first.name]})
            done = campmap.parse_regions(q.text) if q.text else None
            check(f"     one province planned onto {target}: one line different"
                  f" and the length unchanged",
                  done is not None
                  and len(done.lines) == len(rcm.regions.lines)
                  and sum(1 for a, b in zip(rcm.regions.lines, done.lines)
                          if a != b) == 1)
            check("     and every other record is byte-identical",
                  done is not None
                  and all(done.by_name(r.name).rebels == r.rebels
                          for r in rcm.regions.records if r.name != first.name))


# ---- 9: the two routes ------------------------------------------------------

print("\n9. GET /api/map/rebels and POST /api/map/rebel_plan|_apply")

import json                                                       # noqa: E402
import shutil                                                     # noqa: E402
import threading                                                  # noqa: E402
import urllib.error                                               # noqa: E402
import urllib.request                                             # noqa: E402

from unittransfer.server import Handler, Registry, _Server         # noqa: E402

med2 = Path(_tmp.mkdtemp(prefix="ut_reb_med2_"))
staged = little_mod()
shutil.copytree(staged.root, med2 / "mods" / "Tiny")
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
    d = get("/api/map/rebels?mod=Tiny")
    check(f"  GET answers with {len(d['rebels'])} rebel faction(s) and "
          f"{len(d['dangling'])} dangling value(s)",
          len(d["rebels"]) == 6 and len(d["dangling"]) == 1)
    check("  a mod with no map at all still answers, because the join is two "
          "text files and the layers decide nothing in it",
          d["regions"] == 4 and d["file"] == campmap.REGIONS_REL)

    r = post("/api/map/rebel_plan",
             {"mod": "Tiny", "rebel": "South_Rebels",
              "regions": ["Alpha_Province"]})
    check("  POST _plan answers with the changes and writes nothing",
          r["plan"]["changes"] == ["Alpha_Province: North_Rebels -> South_Rebels"]
          and campmap.read_regions(Mod(med2 / "mods" / "Tiny"))
          .by_name("Alpha_Province").rebels == "North_Rebels")
    check("  and carries the chance-0 warning through to the browser",
          any("chance 0" in w for w in r["plan"]["warnings"]))

    r = post("/api/map/rebel_apply",
             {"mod": "Tiny", "rebel": "South_Rebels",
              "regions": ["Alpha_Province"]})
    check("  POST _apply writes it and answers with the log id",
          bool(r.get("id")) and r.get("rebel") == "South_Rebels")
    check("  read off disk, the province moved",
          campmap.read_regions(Mod(med2 / "mods" / "Tiny"))
          .by_name("Alpha_Province").rebels == "South_Rebels")
    check("  the registry was invalidated, so the route's own answer moved "
          "with the file",
          next(x for x in get("/api/map/rebels?mod=Tiny")["rebels"]
               if x["name"] == "South_Rebels")["count"] == 2)

    r = post("/api/map/rebel_plan",
             {"mod": "Tiny", "rebel": "Ghost_Rebels",
              "regions": ["Beta_Province"]})
    check("  a value nothing declares is refused by the route too",
          "is not a rebel faction" in (r.get("error") or ""))
    try:
        get("/api/map/rebels?mod=Nope")
        check("  an unknown mod is refused", False)
    except urllib.error.HTTPError as exc:
        check(f"  an unknown mod is refused with {exc.code}", exc.code == 404)
finally:
    httpd.shutdown()


print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
