"""Phase 61 (B2): delete a settlement, create one where none is, copy one across mods.

    python -m tests.test_settlement_b2

On two temp copies of ROCSS's map and campaign (nothing real is written):

1. Delete: the block goes, every other block and the header stay the text
   they were, a capital moves and is named, a faction left with nothing is
   warned about, and one Undo puts the file back byte for byte.
2. Create: a province nobody holds gets a village for the faction named, last
   in its block; the panel's GET says the province is missing rather than
   erroring; a province the map does not declare is refused.
3. Copy into another mod: the same province, filled with the source's level,
   population and buildings in the destination's shape; a building the
   destination does not declare is left out and named; a province with no
   settlement there needs an owner and then gets one.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import campmap, campstrat, mapquery  # noqa: E402
from unittransfer import stratedit as se  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer import config  # noqa: E402

# Every save and undo here goes to a config of its own, never the real undo log
# and backups: a suite run beside others would race them on transfers.json. It
# starts from a copy of the real settings, so the game root and the M2EX marks
# read the same, and nothing is written back to them.
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

SRC = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods/ROCSS/data")
CAMP = "imperial_campaign"
STRAT = f"world/maps/campaign/{CAMP}/descr_strat.txt"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def copy_mod(name: str) -> Path:
    root = Path(_tmp.mkdtemp(prefix="ut_b2_")) / name
    shutil.copytree(SRC / "world/maps/base", root / "data/world/maps/base")
    (root / "data" / STRAT).parent.mkdir(parents=True)
    shutil.copy2(SRC / STRAT, root / "data" / STRAT)
    for f in ("export_descr_buildings.txt", "descr_sm_factions.txt", "export_descr_unit.txt"):
        shutil.copy2(SRC / f, root / "data" / f)
    return root


def facts_of(root: Path):
    mod = Mod(root)
    return mod, mapquery.Facts(mod, campmap.CampaignMap(mod), CAMP)


if not (SRC / STRAT).is_file():
    print("ROCSS is not installed - SKIPPED")
    sys.exit(0)

a_root = copy_mod("B2A")
mod, facts = facts_of(a_root)
sf = campstrat.read_strat(mod, CAMP)
original = (a_root / "data" / STRAT).read_bytes()

# ---- 1) delete --------------------------------------------------------------------------
print("\n1) delete")
faction = next(f for f in sf.of_kind("faction") if len(se.settlements_of(sf, f)) >= 2)
fname = str(faction.get("name") or faction.name)
capital = se.settlements_of(sf, faction)[0]
region = str(capital.get("region"))
p = se.plan_delete_settlement(mod, facts, {"region": region, "campaign": CAMP})
check(f"{fname}'s capital {region} plans out clean", not p.errors and p.text)
done = campstrat.parse_strat(p.text)
check("the block is gone and every other settlement block is the text it was",
      se.find_settlement(done, region) is None
      and len(done.of_kind("settlement")) == len(sf.of_kind("settlement")) - 1)
check(f"the capital moving is named ({p.capitals})",
      any(fname in c and region in c for c in p.capitals))
check("and the province left empty is said, with vanilla's Durazzo beside it",
      any("Durazzo" in w for w in p.warnings))
lone = next((f for f in sf.of_kind("faction") if len(se.settlements_of(sf, f)) == 1), None)
if lone is not None:
    only = str(se.settlements_of(sf, lone)[0].get("region"))
    q = se.plan_delete_settlement(mod, facts, {"region": only, "campaign": CAMP})
    check(f"deleting {lone.name}'s only settlement warns it opens destroyed",
          any("holding no settlement" in w for w in q.warnings))
check("a province with no settlement cannot be deleted",
      se.plan_delete_settlement(mod, facts, {"region": "Nowhere_Province", "campaign": CAMP}).errors)
res = se.apply_settlement(p)
check("written", se.find_settlement(campstrat.read_strat(mod, CAMP), region) is None)

# ---- 2) create ------------------------------------------------------------------------------
print("\n2) create")
mod, facts = facts_of(a_root)
d = se.settlement_detail(facts, region)
check("the panel's GET says the province is missing and offers the factions",
      d.get("missing") is True and d["factions"])
c = se.plan_create_settlement(mod, facts, {"region": region, "campaign": CAMP, "owner": fname})
check("a village for the faction named plans clean", not c.errors and c.text)
made = campstrat.parse_strat(c.text)
node = se.find_settlement(made, region)
check("it lands in that faction's block, last - not taking the capital back",
      node is not None and se.faction_of(made, node).name.split(",")[0].strip() == fname
      and se.settlements_of(made, se.faction_of(made, node))[-1] is node)
check("a province the map does not declare is refused",
      se.plan_create_settlement(mod, facts, {"region": "Atlantis_Province", "campaign": CAMP,
                                             "owner": fname}).errors)
check("and a create needs an owner",
      se.plan_create_settlement(mod, facts, {"region": region, "campaign": CAMP}).errors)
transfer.undo(res["id"])
check("one undo of the delete puts the file back byte for byte",
      (a_root / "data" / STRAT).read_bytes() == original)

# ---- 3) copy into another mod ----------------------------------------------------------------
print("\n3) copy into another mod")
b_root = copy_mod("B2B")
src_mod, src_facts = facts_of(a_root)
sf_a = campstrat.read_strat(src_mod, CAMP)
busy = max(sf_a.of_kind("settlement"), key=lambda n: len(sf_a.children_of(n, "building")))
busy_region = str(busy.get("region"))
want = [(b.name, str(b.get("level"))) for b in sf_a.children_of(busy, "building")]
# the destination's copy of that settlement is stripped to nothing, and one of
# the source's buildings is taken out of the destination's EDB
dmod, dfacts = facts_of(b_root)
strip = se.plan_settlement(dmod, dfacts, {"region": busy_region, "campaign": CAMP,
                                          "edits": {"level": "village", "population": "400"},
                                          "buildings": []})
se.apply_settlement(strip)
gone_line, gone_level = want[-1]
edb = (b_root / "data/export_descr_buildings.txt").read_text(encoding="latin-1")
(b_root / "data/export_descr_buildings.txt").write_text(
    re.sub(rf"\b{re.escape(gone_level)}\b", f"zz_{gone_level}", edb), encoding="latin-1")
dmod, dfacts = facts_of(b_root)
before_b = (b_root / "data" / STRAT).read_bytes()
cp = se.plan_copy_settlement(src_mod, src_facts, dmod, dfacts,
                             {"region": busy_region, "campaign": CAMP})
check(f"{busy_region} ({len(want)} buildings) copies into the other mod clean", not cp.errors and cp.text)
got = se.find_settlement(campstrat.parse_strat(cp.text), busy_region)
got_b = [(b.name, str(b.get("level"))) for b in campstrat.parse_strat(cp.text).children_of(got, "building")]
check("its level and population come across", str(got.get("level")) == str(busy.get("level"))
      and str(got.get("population")) == str(busy.get("population")))
check(f"every building the other mod declares comes across ({len(got_b)} of {len(want)})",
      set(got_b) == set(want) - {(gone_line, gone_level)})
check("the one it does not declare is left out, and named",
      any("left out" in w and gone_level in w for w in cp.warnings))
res = se.apply_settlement(cp)
transfer.undo(res["id"])
check("the copy undoes byte for byte", (b_root / "data" / STRAT).read_bytes() == before_b)

# a province the other mod holds nothing in
del_b = se.plan_delete_settlement(dmod, dfacts, {"region": busy_region, "campaign": CAMP})
se.apply_settlement(del_b)
dmod, dfacts = facts_of(b_root)
need = se.plan_copy_settlement(src_mod, src_facts, dmod, dfacts, {"region": busy_region, "campaign": CAMP})
check("into a province the other mod holds nothing in, an owner has to be named",
      any("name the faction" in e for e in need.errors))
owner = str(se.faction_of(sf_a, busy).get("name") or se.faction_of(sf_a, busy).name)
made = se.plan_copy_settlement(src_mod, src_facts, dmod, dfacts,
                               {"region": busy_region, "campaign": CAMP, "owner": owner})
check("and with one it creates the settlement and fills it", not made.errors and made.text
      and se.find_settlement(campstrat.parse_strat(made.text), busy_region) is not None)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
