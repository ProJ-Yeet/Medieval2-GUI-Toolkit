"""Many towns at once, each with a garrison, and the wizard's two numbers -
Phase 96e4.

`unittransfer/manytowns.py` chains the one-village writer and the character
writer over several provinces in memory and hands back one file to write. It
is run here against DaC's own campaign with three provinces' settlements taken
out in memory (DaC has none spare), so what is checked is the real file's
shape. Nothing is written to the mod.

    python -m tests.test_manytowns
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _realmod, _webtext  # noqa: E402
from unittransfer import campaint, campmap, campstrat, manytowns, mapquery, stratedit  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n== 1) what a garrison buys ==")
units = [("Knights", 2000), ("Spears", 300), ("Archers", 250), ("Militia", 120), ("Peasants", 60)]
got = manytowns.buy(units, 1500)
check(f"held to a quarter of the money, dearest first: {got}",
      got and got[0] == "Spears" and "Knights" not in got)
check("never past the limit", sum(dict(units)[u] for u in got) <= 1500)
check(f"each unit at most {manytowns.EACH} times", max(got.count(u) for u in got) <= manytowns.EACH)
check("a limit too small for a quarter still buys the cheapest", manytowns.buy(units, 100) == ["Peasants"])
check("and no money buys nothing", manytowns.buy(units, 0) == [])
check("at most twelve regiments", len(manytowns.buy([("A", 1)] * 40, 10 ** 6)) <= manytowns.MAX_UNITS)
check("the price is stat_cost's second number",
      manytowns.unit_cost(type("U", (), {"raw": "type x\nstat_cost 1, 470, 140, 70\n"})()) == 470)

print("\n== 2) the wizard's triumph and farming ==")
check("left empty, they are Geomod's usual", campaint._whole({}, "triumph") == campaint.NEW_REGION_DEFAULTS["triumph"]
      and campaint._whole({"farming": ""}, "farming") == campaint.NEW_REGION_DEFAULTS["farming"])
check("a number is taken", campaint._whole({"farming": "2"}, "farming") == 2)
for bad in ("x", "-1", "2.5"):
    try:
        campaint._whole({"triumph": bad}, "triumph")
        check(f"{bad!r} is refused", False)
    except campmap.MapError as exc:
        check(f"{bad!r} is refused by name: {str(exc)[:40]}…", "triumph" in str(exc))
js = _webtext.read(ROOT / "web" / "js" / "campaint.js")
check("the form asks for both", "box('triumph'" in js and "box('farming'" in js)

print("\n== 3) on DaC's campaign, three provinces emptied in memory ==")
dac = next((r for r in _realmod.installed() if r.name == "Divide_and_Conquer_EUR"), None)
if dac is None:
    print("  -- DaC is not installed")
else:
    mod = Mod(dac)
    cm = campmap.CampaignMap(mod)
    facts = mapquery.Facts(mod, cm, campstrat.DEFAULT_CAMPAIGN)
    sf = campstrat.read_strat(mod, campstrat.DEFAULT_CAMPAIGN)
    gone = []
    for rec in cm.regions.records[5:60]:
        node = stratedit.find_settlement(sf, rec.name)
        if node is None or len(gone) == 3:
            continue
        a, b = stratedit.detach_span(sf, node, stratedit.faction_of(sf, node))
        lines = list(sf.lines)
        del lines[a:b + 1]
        sf = campstrat.parse_strat(stratedit.serialise(sf, lines))
        gone.append(rec.name)
    real = campstrat.read_strat
    campstrat.read_strat = lambda m, c: sf
    try:
        towns = [{"region": n, "x": 10 + i, "y": 10} for i, n in enumerate(gone)]
        towns.append({"region": "Anorien_Province", "x": 1, "y": 1})
        p = manytowns.plan_towns(mod, facts, {"owner": "sicily", "towns": towns, "cost": 1500})
        bare = manytowns.plan_towns(mod, facts, {"owner": "sicily", "towns": towns[:1], "cost": 0})
    finally:
        campstrat.read_strat = real
    done = campstrat.parse_strat(p.text) if p.text else None
    check(f"it plans: {p.errors}", not p.errors and done is not None)
    if done is not None:
        check("three villages added, the one already held skipped and named",
              len(done.of_kind("settlement")) == len(sf.of_kind("settlement")) + 3
              and any("Anorien_Province" in w for w in p.warnings))
        check("three generals, one standing in each",
              len(done.of_kind("character")) == len(sf.of_kind("character")) + 3)
        for n in gone:
            node = stratedit.find_settlement(done, n)
            home = stratedit.faction_of(done, node)
            check(f"  {n} is Gondor's", str(home.get("name") or home.name) == "sicily")
        names = re.findall(r"^\s*([^\n]*?) holds it with (\d+) regiments", "\n".join(p.changes), re.M)
        pool = set()
        try:
            from unittransfer import stratchar
            pool = set(stratchar.Vocabulary(facts, sf).pool.get("sicily") or [])
        except Exception:                                  # noqa: BLE001
            pass
        check(f"each general named from Gondor's own pool: {[n for n, _ in names]}",
              len(names) == 3 and (not pool or all(n in pool for n, _ in names)))
        check("and no name the file already used",
              all(sum(1 for c in done.of_kind("character") if c.name == n) == 1 for n, _ in names))
        check("each garrison as bought", all(int(k) == len(manytowns.buy(
            manytowns.garrison_units(mod, "sicily"), 1500)) for _n, k in names))
        check("every other block is the text it was",
              all(stratedit.blocks_by_region(done)[0].get(k) == v
                  for k, v in stratedit.blocks_by_region(sf)[0].items()))
    check("with no cost limit, villages and nobody in them",
          not bare.errors and not any(c.startswith("  ") for c in bare.changes))

print("\n== 4) the panel and the route ==")
se = _webtext.read(ROOT / "web" / "js" / "stratedit.js")
check("the settlement editor offers it, held or not", se.count("${csTownsHtml()}") == 2)
check("one plan, one confirm, one write, through the settlement route",
      "action: 'towns'" in se and "csAction(" in se)
srv = _webtext.read(ROOT / "unittransfer" / "server.py")
check("the route dispatches it", 'what == "towns"' in srv and "manytowns.plan_towns(" in srv)

print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
