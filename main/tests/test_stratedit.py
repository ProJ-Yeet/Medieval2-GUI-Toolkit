"""``descr_strat.txt``, write - Phase 16h's exit criteria, measured.

16b promised that the settlement writer would change the lines it means to
change and nothing else. This is where that is proved rather than argued, and
it is proved the expensive way: **every settlement of every installed campaign
is re-rendered with no edits at all and must come back byte for byte**, and
then again with its own building list handed back to it. 316 blocks across
vanilla's two campaigns and Third Age Reforged, comments, tabs and the modder's
own blank lines included.

The exit criteria, in the order they are checked:

    a settlement's owner, tier and buildings change on both test mods
    the file outside the edited block is byte-identical
    the whole file still reads, and reads to the same shape
    the capital rule holds: first settlement in the block
    the save backs up, and the log's undo puts the file back byte-exact

Five parts, the last two of which need a real game install:

    1  the block renderer, on text written here
    2  the move: what travels with a block, and where it lands
    3  the rules: what is fatal, what is a warning, and what is not checked
    4  every real campaign: 316 blocks re-rendered, and real plans over a sample
    5  the two routes, a real save and its undo, on a throwaway mod

    python -m tests.test_stratedit
"""
import json
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, mapquery, stratedit
from unittransfer.keyblock import read_text
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


def _lines(text):
    """A serialised file back as the list of lines it was joined from."""
    body = text[:-len(CR)] if text.endswith(CR) else text
    return body.split(CR)


def _only_block_changed(before, after, sf, node):
    """Nothing outside ``node``'s own lines moved, byte for byte.

    The exit criterion of this whole sub-phase, checked here rather than eyed:
    the head up to the block is identical, and the tail after it is identical,
    however many lines the block itself grew or lost in between.
    """
    b, a = _lines(before), _lines(after)
    if a[:node.start] != b[:node.start]:
        return False
    tail = len(b) - (node.end + 1)
    return a[len(a) - tail:] == b[node.end + 1:] if tail else True


# ---- 1) the block renderer, on text written here -----------------------------
print("\n1) an edit is one line, and the rest of the block is untouched")

SAMPLE = joined(
    "campaign imperial_campaign",
    "playable",
    "\tengland",
    "\tfrance",
    "end",
    "unlockable",
    "end",
    "nonplayable",
    "end",
    "",
    ";##### England #####",
    "faction\tengland, balanced smith",
    "\tai_label\tcatholic",
    "\tdenari\t10000",
    "",
    "\tsettlement",
    "\t{",
    "\t\tlevel large_town\t; the biggest in 1080",
    "\t\tregion London_Province",
    "",
    "\t\tyear_founded 0",
    "\t\tpopulation 3800",
    "\t\tplan_set default_set",
    "\t\tfaction_creator england",
    "\t\tbuilding",
    "\t\t{",
    "\t\t\ttype core_building wooden_wall",
    "\t\t}",
    "\t\tbuilding",
    "\t\t{",
    "\t\t\ttype barracks town_guard\t; retrained here",
    "\t\t}",
    "\t\tbuilding",
    "\t\t{",
    "\t\t\ttype market corn_exchange",
    "\t\t}",
    "\t}",
    "",
    "\tsettlement castle",
    "\t{",
    "\t\tlevel town",
    "\t\tregion Nottingham_Province",
    "\t\tpopulation 3000",
    "\t}",
    "",
    "\tcharacter\tWilliam, named character, male, leader, age 30, x 100, y 100",
    "",
    "faction\tfrance, balanced caesar",
    "\tdenari\t8000",
    "",
    "\tsettlement",
    "\t{",
    "\t\tlevel city",
    "\t\tregion Paris_Province",
    "\t\tpopulation 5000",
    "\t}",
    "",
    "faction_standings\tengland, 0.5 france",
    "region Test_Province",
    "\tfarming_level 4",
    "script",
    "campaign_script.txt",
)

sf = campstrat.parse_strat(SAMPLE)
london = stratedit.find_settlement(sf, "London_Province")
notts = stratedit.find_settlement(sf, "Nottingham_Province")
paris = stratedit.find_settlement(sf, "Paris_Province")
check("the three settlements are found by the province they name",
      london is not None and notts is not None and paris is not None)

base = sf.lines[london.start:london.end + 1]
check("a render with no edits at all is the block it was given",
      stratedit.render_block(sf, london) == base)

got = stratedit.render_block(sf, london, {"population": "9000"})
check("one field edited rewrites one line and leaves the other 20 alone",
      sum(1 for a, b in zip(base, got) if a != b) == 1
      and len(got) == len(base)
      and "\t\tpopulation 9000" in got)

got = stratedit.render_block(sf, london, {"level": "city"})
check("a rewritten line keeps its indent and its trailing comment",
      "\t\tlevel city\t; the biggest in 1080" in got)

got = stratedit.render_block(sf, london, {"population": "3800"})
check("a field set to the value it already has is not rewritten at all",
      got == base)

got = stratedit.render_block(sf, london, {"settlement_type": "castle"})
check("the header is the kind, and only the header changes",
      got[0] == "\tsettlement castle" and got[1:] == base[1:])

got = stratedit.render_block(sf, notts, {"plan_set": "osgiliath_east_a"})
check("a field the block does not have yet is inserted, indented like its "
      "neighbours",
      "\t\tplan_set osgiliath_east_a" in got and len(got) == 7
      and got[-1] == "\t}")

got = stratedit.render_block(sf, notts, {"year_founded": "1050"})
at = [i for i, ln in enumerate(got) if "year_founded" in ln][0]
check("an added field lands where the file would have written it, not at the "
      "bottom",
      at < [i for i, ln in enumerate(got) if "population" in ln][0])

blds = [(b.name, str(b.get("level"))) for b in sf.children_of(london, "building")]
check("the buildings read as (line, level) in the order the block writes them",
      blds == [("core_building", "wooden_wall"), ("barracks", "town_guard"),
               ("market", "corn_exchange")])

got = stratedit.render_block(sf, london, {}, blds)
check("handing the building list straight back changes nothing",
      got == base)

got = stratedit.render_block(sf, london, {}, blds[:1] + blds[2:])
check("a building removed is its own four lines and nothing else",
      len(got) == len(base) - 4 and "town_guard" not in "".join(got)
      and "wooden_wall" in "".join(got) and "corn_exchange" in "".join(got))

got = stratedit.render_block(sf, london, {},
                             blds + [("hinterland_roads", "roads")])
check("a building added takes the shape of the ones above it",
      got[len(base) - 1:len(base) + 3]
      == ["\t\tbuilding", "\t\t{", "\t\t\ttype hinterland_roads roads", "\t\t}"])

got = stratedit.render_block(sf, london, {},
                             [blds[0], ("barracks", "militia_barracks"), blds[2]])
check("a building whose level changes rewrites its type line and keeps its "
      "comment",
      "\t\t\ttype barracks militia_barracks\t; retrained here" in got
      and len(got) == len(base))

got = stratedit.render_block(sf, notts, {}, [("core_castle_building", "castle")])
check("a settlement with no buildings takes its first one before the closing "
      "brace",
      got[-1] == "\t}" and got[-2] == "\t\t}"
      and "\t\t\ttype core_castle_building castle" in got)

# ---- 2) the move -------------------------------------------------------------
print("\n2) what travels with a block, and where it lands")

eng = sf.faction("england")
fr = sf.faction("france")
check("a faction's settlements come back in the order the file writes them",
      [str(n.get("region")) for n in stratedit.settlements_of(sf, eng)]
      == ["London_Province", "Nottingham_Province"])
check("the capital is the first settlement in the block",
      stratedit.capital_of(sf, eng) == "London_Province"
      and stratedit.capital_of(sf, fr) == "Paris_Province")

span = stratedit.detach_span(sf, london, eng)
check("a block takes the blank line after it with it, and nothing more",
      span == (london.start, london.end + 1)
      and sf.lines[span[1]] == ""
      and sf.lines[span[1] + 1].strip().startswith("settlement"))

check("`first` lands in front of the faction's first settlement",
      stratedit.insert_at(sf, fr, "first") == paris.start)
check("`last` lands after the last one, blank line included",
      stratedit.insert_at(sf, eng, "last")
      == stratedit.detach_span(sf, notts, eng)[1] + 1)
check("a faction holding nothing takes it in front of its first character",
      stratedit.insert_at(sf, eng, "first", skip=london)
      == notts.start)

moved = stratedit.move_lines(list(sf.lines), span, paris.start)
check("a move keeps every line in the file, and the same number of them",
      sorted(moved) == sorted(sf.lines) and len(moved) == len(sf.lines))
after = campstrat.parse_strat(CR.join(moved) + CR)
check("the moved block is inside the faction it was moved into, and it is "
      "that faction's capital now",
      stratedit.capital_of(after, after.faction("france")) == "London_Province"
      and stratedit.capital_of(after, after.faction("england"))
      == "Nottingham_Province")
check("the counts are what they were: one block moved, nothing was made or lost",
      after.counts() == sf.counts())

# ---- 3) the rules ------------------------------------------------------------
print("\n3) what is fatal, what is a warning, and what is not checked at all")


class _FakeEdb:
    def __init__(self, buildings):
        self.buildings = buildings


class _FakeLine:
    def __init__(self, name, blocks):
        self.name, self.blocks = name, blocks


class _FakeBlock:
    def __init__(self, name, settlement="", **scalars):
        self.name, self.settlement, self.scalars = name, settlement, scalars


class _FakeMod:
    def __init__(self, edb):
        self.edb = edb


class _FakeFacts:
    def __init__(self, mod):
        self.mod, self.skipped = mod, []


EDB = _FakeEdb([
    _FakeLine("core_building", [
        _FakeBlock("wooden_wall", "city", settlement_min="town"),
        _FakeBlock("stone_wall", "city", settlement_min="large_town")]),
    _FakeLine("bank", [
        _FakeBlock("merchant_vault", "city", settlement_min="large_city")]),
])

voc = stratedit.Vocabulary(_FakeFacts(_FakeMod(EDB)), sf)
check("the vocabulary knows what the EDB declares",
      voc.have_edb and voc.levels["stone_wall"].declared
      and voc.levels["stone_wall"].settlement_min == "large_town")
check("and what only the campaign file names, marked as not declared",
      not voc.levels["corn_exchange"].declared
      and voc.levels["corn_exchange"].line == "market")
check("plan sets and creators are what the campaign itself writes, in order",
      voc.plan_sets == ["default_set"] and voc.creators == ["england"])

fatal = lambda f: [x["code"] for x in f if x["fatal"]]
warn = lambda f: [x["code"] for x in f if not x["fatal"]]

f = stratedit.check_settlement(voc, "city", "metropolis", 100, 0, [])
check("a level off the ladder is fatal", fatal(f) == ["settlement.level"])
f = stratedit.check_settlement(voc, "city", "town", "lots", 0, [])
check("a population that is not a number is fatal",
      fatal(f) == ["settlement.population"])
f = stratedit.check_settlement(voc, "city", "town", -5, 0, [])
check("a negative population is fatal", fatal(f) == ["settlement.population"])
f = stratedit.check_settlement(voc, "hamlet", "town", 100, 0, [])
check("a settlement kind the engine does not read is fatal",
      fatal(f) == ["settlement.type"])
f = stratedit.check_settlement(voc, "city", "town", 100, 0,
                               [("core_building", "nosuch_wall")])
check("with an EDB on disk, a level it does not declare is fatal",
      fatal(f) == ["building.unknown"])

f = stratedit.check_settlement(voc, "castle", "village", 100, 0,
                               [("bank", "merchant_vault")])
check("a city building in a castle, three rungs under its settlement_min, is "
      "two warnings and no refusal - Third Age Reforged ships 248 and 432 of "
      "them and runs",
      not fatal(f) and sorted(warn(f)) == ["building.min", "building.pin"])
f = stratedit.check_settlement(voc, "city", "huge_city", 100, 0,
                               [("core_building", "wooden_wall"),
                                ("core_building", "stone_wall")])
check("two levels of one line is a warning, because TAR ships four of those too",
      not fatal(f) and warn(f) == ["building.repeat"])
f = stratedit.check_settlement(voc, "city", "town", 100, 0,
                               [("bank", "wooden_wall")])
check("a type line naming the wrong tree still finds the building, and says so",
      not fatal(f) and warn(f) == ["building.line"])

blind = stratedit.Vocabulary(_FakeFacts(_FakeMod(_FakeEdb([]))), sf)
f = blind.levels["corn_exchange"]
check("with no EDB on disk the vocabulary is the campaign file's own words",
      not blind.have_edb and not f.declared and f.line == "market")
f = stratedit.check_settlement(blind, "castle", "village", 100, 0,
                               [("bank", "merchant_vault"),
                                ("nothing", "made_up_level")])
check("and then no building rule runs at all: a rule with no evidence reports "
      "nothing", f == [])

# ---- 4) every real campaign --------------------------------------------------
print("\n4) every installed campaign: every block re-rendered, and real plans")

roots = []
game = _realmod.MODS.parent
if (game / "data").is_dir():
    roots.append(game)
roots += _realmod.installed()
roots = [r for r in roots if (r / "data" / campstrat.CAMPAIGN_DIR_REL).is_dir()]

if not roots:
    print(f"  SKIPPED - nothing with {campstrat.CAMPAIGN_DIR_REL} under "
          f"{_realmod.MODS}")
else:
    total = 0
    for root in roots:
        mod = Mod(root)
        for name in campstrat.campaigns(mod):
            f = campstrat.read_strat(mod, name)
            raw = read_text(f.path, campstrat.ENCODING)
            blocks = f.of_kind("settlement")
            total += len(blocks)
            bad = [n for n in blocks
                   if stratedit.render_block(f, n) != f.lines[n.start:n.end + 1]]
            check(f"{root.name}/{name}: {len(blocks)} blocks re-render byte for "
                  f"byte with no edits", not bad)
            bad = [n for n in blocks
                   if stratedit.render_block(
                       f, n, {}, [(b.name or "", str(b.get("level") or ""))
                                  for b in f.children_of(n, "building")])
                   != f.lines[n.start:n.end + 1]]
            check(f"{root.name}/{name}: and with their own building lists "
                  f"handed back", not bad)
            check(f"{root.name}/{name}: the file still round-trips",
                  f.serialise() == raw)

            held = [(str(x.get("name") or x.name), stratedit.capital_of(f, x))
                    for x in f.of_kind("faction")]
            landed = [(n, c) for n, c in held if c]
            check(f"{root.name}/{name}: {len(landed)} of "
                  f"{len(held)} factions hold a province, and each one's "
                  f"capital is the first settlement in its block",
                  all(stratedit.settlements_of(f, f.faction(n))[0].get("region")
                      == c for n, c in landed))
            if root == game and name == "imperial_campaign":
                print("    (vanilla: the nineteen the capital rule was read off)")
                caps = {n: c for n, c in landed if n != "slave"}
                check("England opens in London, France in Paris, the Holy Roman "
                      "Empire in Frankfurt and Byzantium in Constantinople",
                      caps.get("england") == "London_Province"
                      and caps.get("france") == "Paris_Province"
                      and caps.get("hre") == "Frankfurt_Province"
                      and caps.get("byzantium") == "Constantinople_Province")
                check("all nineteen landed factions have theirs first",
                      len(caps) == 19)
    print(f"  {total} settlement blocks re-rendered in all")

    # ---- real plans, on a sample of each campaign ---------------------------
    print("\n   real plans: a field, the buildings, and the owner")
    for root in roots:
        mod = Mod(root)
        try:
            cm = campmap.CampaignMap(mod)
        except campmap.MapError as exc:
            print(f"  {root.name}: SKIPPED - {exc}")
            continue
        for name in campstrat.campaigns(mod)[:1]:
            facts = mapquery.Facts(mod, cm, name)
            f = campstrat.read_strat(mod, name)
            before = f.serialise()
            blocks = f.of_kind("settlement")
            # first, last and middle: a capital, a tail and something ordinary
            picks = [blocks[0], blocks[len(blocks) // 2], blocks[-1]]
            others = [str(x.get("name") or x.name) for x in f.of_kind("faction")]
            t0 = time.time()
            for node in picks:
                region = str(node.get("region") or "")
                owner = stratedit.faction_of(f, node)
                held = str(owner.get("name") or owner.name)
                dest = next(x for x in others if x != held)
                blds = [(b.name or "", str(b.get("level") or ""))
                        for b in f.children_of(node, "building")]

                p = stratedit.plan_settlement(mod, facts, {
                    "region": region, "campaign": name,
                    "edits": {"level": "city", "population": "1234"}})
                check(f"{root.name}/{name} {region}: level and population save, "
                      f"and only this block changes",
                      not p.errors and p.text
                      and _only_block_changed(before, p.text, f, node))

                p2 = stratedit.plan_settlement(mod, facts, {
                    "region": region, "campaign": name,
                    "buildings": [{"line": l, "level": v} for l, v in blds[:-1]]
                    if len(blds) > 1 else [{"line": "core_building",
                                            "level": "wooden_pallisade"}]})
                check(f"{root.name}/{name} {region}: the building list saves",
                      not p2.errors and p2.text)

                p3 = stratedit.plan_settlement(mod, facts, {
                    "region": region, "campaign": name,
                    "owner": dest, "place": "first"})
                back = campstrat.parse_strat(p3.text) if p3.text else None
                check(f"{root.name}/{name} {region}: given to {dest} as its "
                      f"capital, and the file still reads to the same shape",
                      not p3.errors and back is not None
                      and back.serialise() == p3.text
                      and back.counts() == f.counts()
                      and stratedit.capital_of(
                          back, back.faction(dest)).lower() == region.lower())
                check(f"{root.name}/{name} {region}: and the move says whose "
                      f"capital changed",
                      any("capital" in c for c in p3.capitals))
            print(f"   {root.name}/{name}: 9 plans in "
                  f"{(time.time() - t0) * 1000:.0f} ms")


# ---- 5) the two routes, a real save and its undo -----------------------------
print("\n5) /api/map/settlement and /api/map/settlement_plan|_apply")

if not roots:
    print("  SKIPPED - no campaign to serve")
else:
    src = roots[0]
    camp = campstrat.campaigns(Mod(src))[0]
    cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"

    med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "StratMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file():
            shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
    camp_dir = data / campstrat.CAMPAIGN_DIR_REL / camp
    camp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "data" / campstrat.CAMPAIGN_DIR_REL / camp
                 / campstrat.STRAT_NAME, camp_dir / campstrat.STRAT_NAME)
    edb = src / "data" / "export_descr_buildings.txt"
    if edb.is_file():
        shutil.copy2(edb, data / "export_descr_buildings.txt")
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} - {camp} copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def status(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=300) as r:
                return r.status, ""
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8")).get("error", "")
            except Exception:                          # noqa: BLE001
                return e.code, ""

    strat_path = camp_dir / campstrat.STRAT_NAME
    was = strat_path.read_bytes()
    live = campstrat.parse_strat(read_text(strat_path, campstrat.ENCODING))
    block = live.of_kind("settlement")[0]
    region = str(block.get("region") or "")
    owner = stratedit.faction_of(live, block)
    held = str(owner.get("name") or owner.name)
    dest = next(str(x.get("name") or x.name) for x in live.of_kind("faction")
                if str(x.get("name") or x.name) != held)

    try:
        d = get(f"/api/map/settlement?mod=StratMod&region={region}")
        check(f"/api/map/settlement answers for {region}: {len(d['buildings'])} "
              f"buildings, held by {d['owner']}, "
              f"{'its capital' if d['is_capital'] else 'not the capital'}",
              d["region"] == region and d["owner"] == held
              and isinstance(d["vocab"]["ladder"], list))
        check("the vocabulary carries the ladder, the factions and the plan sets "
              "the campaign itself uses",
              len(d["vocab"]["ladder"]) == 6
              and d["vocab"]["factions"] and d["vocab"]["plan_sets"])
        check("a province with no settlement is a 404 that says why",
              status("/api/map/settlement?mod=StratMod&region=Nowhere_Province")[0]
              == 404)

        body = {"mod": "StratMod", "region": region, "campaign": camp,
                "edits": {"population": "4321"}}
        plan = post("/api/map/settlement_plan", body)
        check("a plan says what would change and writes nothing",
              plan["plan"]["ok"] and plan["plan"]["changes"]
              and strat_path.read_bytes() == was)

        bad = post("/api/map/settlement_plan", dict(
            body, edits={"level": "metropolis"}))
        check("a level off the ladder is refused at the plan, with the six named",
              not bad["plan"]["ok"] and "village" in bad["error"])

        move = post("/api/map/settlement_plan", dict(
            body, owner=dest, place="first"))
        check(f"giving {region} to {dest} as its capital says whose capital "
              f"moved, on both sides",
              move["plan"]["ok"] and move["plan"]["moved"]
              and move["plan"]["capitals"])

        res = post("/api/map/settlement_apply", dict(body, owner=dest,
                                                     place="first"))
        check("the save answers with a log record that can undo it",
              not res.get("error") and res["record"]["manifest"]["backed_up"]
              and res["record"]["mode"] == "campmap"
              and res["record"]["action"] == "settlement")
        now = campstrat.parse_strat(read_text(strat_path, campstrat.ENCODING))
        check("the file on disk still reads, and to the same shape",
              now.counts() == live.counts()
              and now.serialise() == read_text(strat_path, campstrat.ENCODING))
        check(f"{region} is inside {dest}'s block now, and is its capital",
              stratedit.capital_of(now, now.faction(dest)).lower()
              == region.lower())

        again = get(f"/api/map/settlement?mod=StratMod&region={region}")
        check("and the panel is told so on the next read, so the cache went "
              "with the write",
              again["owner"] == dest and again["is_capital"])

        post("/api/undo", {"id": res["record"]["id"]})
        check("undo puts descr_strat.txt back byte-exact",
              strat_path.read_bytes() == was)
    finally:
        httpd.shutdown()
        shutil.rmtree(med2, ignore_errors=True)
        shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
