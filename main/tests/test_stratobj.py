"""Phase 22a: forts and watchtowers, placed, moved, changed and taken out.

    python -m tests.test_stratobj

1. A small campaign file written here, with no map: every edit is one line, the
   short form ``fort <x> <y>`` survives every edit that does not ask for a type,
   a section is opened where the file says sections go, and nothing outside the
   planned lines moves.
2. The vocabulary: a culture ``descr_cultures.txt`` does not declare is fatal, a
   type with no battle-map folder is a warning, and neither is claimed when the
   file or the folder is not on disk.
3. Every installed campaign: each of the real lines renders back byte for byte
   through the writer with nothing changed, the panel's view carries no fatal
   finding on a mod that loads, and an edit, a delete, an add and a move each
   differ from the file only where the plan says.
4. The routes, a real save and its undo on a copy of a real campaign.
"""
import difflib
import json
import shutil
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, mapquery, stratobj
from unittransfer.keyblock import read_text, write_text
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


def lines_of(text):
    return (text[:-len(CR)] if text.endswith(CR) else text).split(CR)


def hunks(before, after):
    """``[(tag, old lines, new lines)]`` for everything that differs."""
    a, b = lines_of(before), lines_of(after)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(t, a[i1:i2], b[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes()
            if t != "equal"]


HEAD = ("campaign imperial_campaign", "playable", "\tengland", "end",
        "nonplayable", "\tslave", "end", "start_date 1080 summer",
        "faction england, balanced smith",
        "settlement", "{", "\tlevel town", "\tregion London_Province",
        "\tyear_founded 0", "\tpopulation 800", "\tplan_set default_set",
        "\tfaction_creator england", "}",
        "character\tWilliam, named character, male, leader, age 30, x 10, y 20",
        "army", "unit\t\tNE Bodyguard\t\texp 1 armour 0 weapon_lvl 0", "",
        "faction_standings england, 0.0 slave",
        "faction_relationships england, at_war_with slave", "")

SECTIONS = joined(
    *HEAD,
    "region London_Province", "farming_level 0", "famine_threat 0",
    "watchtower 11 21",
    "fort\t12 30 ; the old keep",
    "fort 13 31 stone_fort_b culture northern_european",
    "",
    "region York_Province", "farming_level 1", "famine_threat 0",
    "",
    ";;;;;;;;", "; the scripts", "",
    "script", "campaign_script.txt")

#: Third Age Reforged's ending, with no section at all
BANNERED = joined(*HEAD, ";;;;;;;;", "; >>>> start of regions section <<<<",
                  "", "script", "campaign_script.txt")

#: DaC's banner, but no sections
SCRIPTED = joined(*HEAD, ";###################", ";##### Scripts #####", "",
                  "script", "campaign_script.txt")


class Facts:
    """What a plan asks the fact table for, with no map behind it."""

    def __init__(self, mod, campaign, cm=None):
        self.mod, self.campaign, self.cm = mod, campaign, cm
        self.strat_rel = (f"{campstrat.CAMPAIGN_DIR_REL}/{campaign}/"
                          f"{campstrat.STRAT_NAME}")
        self.strat = campstrat.read_strat(mod, campaign)


tmp = Path(_tmp.mkdtemp(prefix="ut_stratobj_"))
CAMP = "imperial_campaign"


def make(text, name="ObjMod"):
    root = tmp / name
    d = root / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
    d.mkdir(parents=True, exist_ok=True)
    write_text(d / campstrat.STRAT_NAME, text, campstrat.ENCODING)
    mod = Mod(root)
    return mod, Facts(mod, CAMP)


def plan(mod, facts, **body):
    return stratobj.plan(mod, facts, dict(body, campaign=CAMP))


# ---- 1) the writer, with no map -----------------------------------------------
print("\n1) one line at a time, in a file written here")

mod, facts = make(SECTIONS)
sf = facts.strat
check("the file reads: one watchtower, two forts, two sections",
      sf.counts().get("watchtower") == 1 and sf.counts().get("fort") == 2
      and sf.counts().get("region") == 2)
short = next(n for n in sf.of_kind("fort") if n.get("x") == 12)
check("the short form reads as a fort with no type and no culture",
      short.get("type") == "" and short.get("culture") == ""
      and short.get("region") == "London_Province")

tower = sf.of_kind("watchtower")[0]
p = plan(mod, facts, kind="watchtower", action="edit", line=tower.start + 1,
         at=[11, 21], x=5, y=6)
check(f"a watchtower moved is one line rewritten: {p.changes}",
      p.payload()["ok"]
      and hunks(SECTIONS, p.text) == [("replace", ["watchtower 11 21"],
                                        ["watchtower 5 6"])])

p = plan(mod, facts, kind="fort", action="edit", line=short.start + 1,
         at=[12, 30], x=7, y=8)
check("a short-form fort moved stays short, and keeps its tab and its comment",
      hunks(SECTIONS, p.text) == [("replace", ["fort\t12 30 ; the old keep"],
                                    ["fort\t7 8 ; the old keep"])])

p = plan(mod, facts, kind="fort", action="edit", line=short.start + 1,
         at=[12, 30], type="stone_fort_a", culture="northern_european")
check("given a type, a short fort takes the long form and keeps its comment",
      hunks(SECTIONS, p.text) == [(
          "replace", ["fort\t12 30 ; the old keep"],
          ["fort\t12 30 stone_fort_a culture northern_european ; the old keep"])])

long = next(n for n in sf.of_kind("fort") if n.get("x") == 13)
p = plan(mod, facts, kind="fort", action="edit", line=long.start + 1,
         at=[13, 31], type="", culture="")
check("and a long one given neither goes back to vanilla's short form",
      hunks(SECTIONS, p.text) == [(
          "replace", ["fort 13 31 stone_fort_b culture northern_european"],
          ["fort 13 31"])])
back = campstrat.parse_strat(p.text)
check("…which reads back as a fort, in the same section",
      any(n.get("x") == 13 and n.get("region") == "London_Province"
          and n.get("type") == "" for n in back.of_kind("fort")))

p = plan(mod, facts, kind="fort", action="edit", line=long.start + 1,
         at=[13, 31], x=13, y=31)
check("a save that changes nothing is refused as nothing to change",
      p.errors == ["nothing to change"] and not p.text)

p = plan(mod, facts, kind="watchtower", action="delete", line=tower.start + 1,
         at=[11, 21])
check("a delete takes out its one line and nothing else",
      hunks(SECTIONS, p.text) == [("delete", ["watchtower 11 21"], [])])
check("…and the section keeps its own farming and famine lines",
      campstrat.parse_strat(p.text).of_kind("region")[0].get("farming_level") == 0)

p = plan(mod, facts, kind="watchtower", action="add", x=14, y=22,
         region="London_Province")
check("a new watchtower joins its own kind in the section, after the last one",
      hunks(SECTIONS, p.text) == [("insert", [], ["watchtower 14 22"])]
      and lines_of(p.text).index("watchtower 14 22")
      == lines_of(SECTIONS).index("watchtower 11 21") + 1)

p = plan(mod, facts, kind="fort", action="add", x=40, y=41,
         region="York_Province", type="stone_fort_b", culture="northern_european")
new = [ln for ln in lines_of(p.text) if "40 41 stone_fort_b" in ln]
check("a section with nothing in it takes a fort after its own last line",
      len(new) == 1 and lines_of(p.text).index(new[0])
      == lines_of(SECTIONS).index("famine_threat 0",
                                  lines_of(SECTIONS).index("region York_Province")) + 1)
check("…written with the gap after `fort` this file uses (a tab, which the "
      "first of its two forts has)", new and new[0].startswith("fort\t40 41"))

p = plan(mod, facts, kind="watchtower", action="add", x=50, y=51,
         region="Paris_Province")
got = hunks(SECTIONS, p.text)
check(f"a province with no section has one opened for it after the last one: {p.changes}",
      p.opened == "Paris_Province"
      and all(t == "insert" for t, _, _ in got)
      and sum(len(b) for _, _, b in got) == 5
      and lines_of(p.text)[lines_of(p.text).index("region York_Province") + 3:][:6]
      == ["", "region Paris_Province", "farming_level 0", "famine_threat 0",
          "watchtower 50 51", ""])
check("…before the blank line and the banner that head `script`",
      lines_of(p.text)[lines_of(p.text).index("watchtower 50 51") + 1:][:3]
      == ["", ";;;;;;;;", "; the scripts"])

p = plan(mod, facts, kind="fort", action="move", line=long.start + 1,
         at=[13, 31], region="York_Province")
got = hunks(SECTIONS, p.text)
check(f"a move files the line under another section: {p.changes}",
      p.payload()["ok"] and len(got) == 2
      and got[0] == ("delete", ["fort 13 31 stone_fort_b culture northern_european"], [])
      and got[1] == ("insert", [], ["fort 13 31 stone_fort_b culture northern_european"]))
moved = campstrat.parse_strat(p.text)
check("…and it reads back under York",
      any(n.get("x") == 13 and n.get("region") == "York_Province"
          for n in moved.of_kind("fort")))
p2 = plan(mod, facts, kind="fort", action="edit", line=long.start + 1,
          at=[13, 31], region="York_Province")
check("an edit naming a different section is the same move",
      p2.action == "move" and p2.text == p.text)

p = plan(mod, facts, kind="fort", action="edit", line=long.start + 1,
         at=[99, 99], x=1, y=1)
check("a record that is not on the tile the panel saw is refused, not guessed: "
      + "; ".join(p.errors), not p.text and "any more" in "; ".join(p.errors))
p = plan(mod, facts, kind="watchtower", action="add", x=5, y=5)
check("with no map and no region named, there is no section to file it under",
      not p.text and "no declared province" in "; ".join(p.errors))
p = plan(mod, facts, kind="watchtower", action="add", x="abc", y=5,
         region="London_Province")
check("a coordinate that is not a whole number is fatal and named",
      not p.text and "not a whole number" in "; ".join(p.errors))
p = plan(mod, facts, kind="keep", action="add", x=5, y=5)
check("a kind that is not one of the three is refused by name",
      not p.text and "not one of fort, watchtower, resource" in "; ".join(p.errors))

for label, text, want in (
        ("under Third Age Reforged's regions banner", BANNERED,
         [";;;;;;;;", "; >>>> start of regions section <<<<", "",
          "region Kent_Province", "farming_level 0", "famine_threat 0",
          "watchtower 3 4", "", "script"]),
        ("in front of DaC's scripts banner", SCRIPTED,
         ["faction_relationships england, at_war_with slave", "",
          "region Kent_Province", "farming_level 0", "famine_threat 0",
          "watchtower 3 4", "", ";###################"])):
    m2, f2 = make(text, name=f"Obj{len(text)}")
    p = stratobj.plan(m2, f2, {"campaign": CAMP, "kind": "watchtower",
                               "action": "add", "x": 3, "y": 4,
                               "region": "Kent_Province"})
    out = lines_of(p.text)
    at = out.index(want[0]) if want[0] in out else -1
    check(f"a file with no sections opens its first one {label}",
          p.payload()["ok"] and out[at:at + len(want)] == want)
    check("…and nothing else in it moves",
          all(t == "insert" for t, _, _ in hunks(text, p.text)))

# the save itself, into a config of its own
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
path = Path(mod.data) / campstrat.CAMPAIGN_DIR_REL / CAMP / campstrat.STRAT_NAME
was = path.read_bytes()
p = plan(mod, facts, kind="fort", action="add", x=60, y=61,
         region="Paris_Province")
res = stratobj.apply(p)
check("a save writes the file the plan worked out",
      read_text(path, campstrat.ENCODING) == p.text)
check("…logged as one campmap job that names what it did",
      res["record"]["mode"] == "campmap"
      and res["record"]["action"] == "fortification"
      and res["record"]["options"]["what"] == "add"
      and res["record"]["options"]["opened"] == "Paris_Province")
from unittransfer.transfer import undo                               # noqa: E402
undo(res["id"])
check("and the Log's undo puts it back byte for byte", path.read_bytes() == was)
try:
    stratobj.apply(plan(mod, facts, kind="fort", action="add", x="q", y=1,
                        region="London_Province"))
    refused = False
except ValueError:
    refused = True
check("a refused plan cannot be applied anyway", refused and path.read_bytes() == was)


# ---- 2) the vocabulary ---------------------------------------------------------
print("\n2) what a fort may be called")

data = Path(mod.data)
write_text(data / "descr_cultures.txt",
           joined("culture northern_european", "{", "}", "culture gondor", "{", "}"),
           "latin-1")
(data / "settlements" / "north_european" / "ambient_settlements"
 / "stone_fort_b").mkdir(parents=True)
(data / "settlements" / "gondor" / "ambient_settlements" / "farms").mkdir(parents=True)
voc = stratobj.Vocabulary(mod, sf)
check("the cultures are read out of descr_cultures.txt",
      voc.cultures == ["northern_european", "gondor"])
names = [t["name"] for t in voc.fort_types()]
check(f"the type box offers the file's own first, then the fort folders: {names}",
      names == ["stone_fort_b"] and "farms" not in names)
p = plan(mod, facts, kind="fort", action="add", x=70, y=71, region="York_Province",
         type="stone_fort_b", culture="klingon")
check("a culture descr_cultures.txt does not declare is fatal, with the list: "
      + "; ".join(p.errors),
      not p.payload()["ok"] and "klingon is not a culture" in "; ".join(p.errors))
p = plan(mod, facts, kind="fort", action="add", x=70, y=71, region="York_Province",
         type="nope_fort", culture="gondor")
check("a type with no battle-map folder is a warning, not a refusal",
      p.payload()["ok"] and any("no nope_fort folder" in w for w in p.warnings))
p = plan(mod, facts, kind="fort", action="add", x=70, y=71, region="York_Province",
         type="stone_fort_b", culture="")
check("a type with no culture is said, and allowed",
      p.payload()["ok"] and any("both a type and a culture" in w for w in p.warnings))
shutil.rmtree(data / "settlements")
(data / "descr_cultures.txt").unlink()
p = plan(mod, facts, kind="fort", action="add", x=70, y=71, region="York_Province",
         type="nope_fort", culture="klingon")
check("with neither file on disk, neither rule claims anything",
      p.payload()["ok"] and not [w for w in p.warnings
                                 if "culture" in w and "klingon" in w
                                 or "folder" in w])


# ---- 3) every installed campaign ------------------------------------------------
print("\n3) the real files")

roots = [m for m in _realmod.installed()
         if (m / "data" / campmap.BASE_REL / "descr_terrain.txt").exists()]
if not roots:
    print("  SKIPPED - no installed mod with a map")
for root in roots:
    rmod = Mod(root)
    try:
        cm = campmap.CampaignMap(rmod)
    except campmap.MapError as exc:
        print(f"  [skip] {root.name}: {exc}")
        continue
    for camp in campstrat.campaign_paths(rmod):
        rf = mapquery.Facts(rmod, cm, camp)
        rs = rf.strat
        if rs is None:
            continue
        objs = stratobj.objects(rs)
        same = sum(stratobj.render_line(rs.lines[n.start], stratobj.read_spec(n),
                                        stratobj.read_spec(n)) == rs.lines[n.start]
                   for n in objs)
        check(f"{root.name}/{camp}: all {len(objs)} fort, watchtower and resource lines "
              f"render back byte for byte", same == len(objs))
        t0 = time.time()
        v = stratobj.view(rf)
        ms = (time.time() - t0) * 1000
        fatal = [f for r in v["rows"] for f in r["findings"] if f["fatal"]]
        check(f"  the panel's view: {v['counts']} in {ms:.0f} ms, "
              f"{v['placed_well'][0]} of {v['placed_well'][1]} filed where they "
              f"stand, no fatal finding on a mod that loads",
              v["counts"]["fort"] == rs.counts().get("fort", 0)
              and v["counts"]["watchtower"] == rs.counts().get("watchtower", 0)
              and not fatal and ms < 5000)
        orig = rs.serialise()

        def rplan(**body):
            return stratobj.plan(rmod, rf, dict(body, campaign=camp))

        forts = [x for x in v["rows"] if x["kind"] in stratobj.SECTIONED]
        if forts:
            r = forts[0]
            p = rplan(kind=r["kind"], action="edit", line=r["line"],
                      at=[r["x"], r["y"]], x=r["x"] + 1)
            h = hunks(orig, p.text)
            check(f"  an edit rewrites line {r['line']} and no other",
                  p.payload()["ok"] and len(h) == 1 and h[0][0] == "replace"
                  and h[0][1] == [r["text"]])
            p = rplan(kind=r["kind"], action="delete", line=r["line"],
                      at=[r["x"], r["y"]])
            check("  a delete takes out that one line",
                  hunks(orig, p.text) == [("delete", [r["text"]], [])])
            other = next((x["region"] for x in forts
                          if x["region"] and x["region"] != r["region"]), "")
            if other:
                p = rplan(kind=r["kind"], action="move", line=r["line"],
                          at=[r["x"], r["y"]], region=other)
                h = hunks(orig, p.text)
                check(f"  a move to {other} is that line out and the same line in",
                      p.payload()["ok"] and [t for t, _, _ in h]
                      == ["delete", "insert"] and h[0][1] == h[1][2])
        reg = next((x for x in cm.index.regions if x.name and x.settlement), None)
        if reg is not None:
            sx, sy = reg.settlement
            gx, gy = cm.game_xy(sx, sy)
            p = rplan(kind="watchtower", action="add", x=gx + 1, y=gy)
            h = hunks(orig, p.text)
            prov = p.region
            check(f"  a watchtower placed beside {reg.name}'s settlement is filed "
                  f"under the province under it ({prov}) and only inserts",
                  p.payload()["ok"] and prov and all(t == "insert" for t, _, _ in h))
            p = rplan(kind="fort", action="add", x=gx, y=gy)
            check("  a fort on the settlement itself is said, with the count behind it",
                  any("settlement pixel" in w for w in p.warnings))


# ---- 4) the routes, a save and its undo ----------------------------------------
print("\n4) /api/map/objects and /api/map/object_plan|_apply")

if not roots:
    print("  SKIPPED - no campaign to serve")
else:
    from unittransfer.server import Handler, Registry, _Server
    src = next((m for m in roots if m.name.lower().startswith("divide")), roots[0])
    med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "ObjMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file():
            shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
    camp_dir = data / campstrat.CAMPAIGN_DIR_REL / CAMP
    camp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "data" / campstrat.CAMPAIGN_DIR_REL / CAMP
                 / campstrat.STRAT_NAME, camp_dir / campstrat.STRAT_NAME)
    if (src / "data" / "descr_cultures.txt").is_file():
        shutil.copy2(src / "data" / "descr_cultures.txt", data / "descr_cultures.txt")
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} - {CAMP} copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    strat_path = camp_dir / campstrat.STRAT_NAME
    was = strat_path.read_bytes()
    try:
        d = get("/api/map/objects?mod=ObjMod")
        check(f"/api/map/objects answers: {d['counts']}, {d['sections']} sections",
              isinstance(d["rows"], list) and "vocab" in d
              and sum(d["counts"].values()) == len(d["rows"]))
        cm = campmap.CampaignMap(Mod(med2 / "mods" / "ObjMod"))
        reg = next(x for x in cm.index.regions if x.name and x.settlement)
        gx, gy = cm.game_xy(reg.settlement[0] + 1, reg.settlement[1])
        body = {"mod": "ObjMod", "campaign": CAMP, "kind": "watchtower",
                "action": "add", "x": gx, "y": gy}
        pl = post("/api/map/object_plan", body)
        check("a plan says where it would file the tower and writes nothing",
              pl["plan"]["ok"] and pl["plan"]["region"]
              and strat_path.read_bytes() == was)
        res = post("/api/map/object_apply", body)
        check("the save answers with the line it wrote and a record to undo",
              not res.get("error") and res["line"] > 0
              and res["record"]["manifest"]["backed_up"])
        again = get("/api/map/objects?mod=ObjMod")
        check("and the next read has it, so the cache went with the write",
              any(r["x"] == gx and r["y"] == gy and r["kind"] == "watchtower"
                  for r in again["rows"]))
        marks = get("/api/map/markers?mod=ObjMod")
        check("the markers layer draws it too",
              any(i["kind"] == "watchtower" and i["x"] == gx and i["y"] == gy
                  for i in marks["items"]))
        mv = post("/api/map/object_apply", {
            "mod": "ObjMod", "campaign": CAMP, "kind": "watchtower",
            "action": "edit", "line": res["line"], "at": [gx, gy], "x": gx, "y": gy + 1})
        check("dragging it a tile is the same route with the new numbers",
              not mv.get("error"))
        post("/api/undo", {"id": mv["record"]["id"]})
        post("/api/undo", {"id": res["record"]["id"]})
        check("two undos put descr_strat.txt back byte for byte",
              strat_path.read_bytes() == was)
    finally:
        httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
