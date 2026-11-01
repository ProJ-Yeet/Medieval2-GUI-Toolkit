"""96f: a faction's culture change, previewed before it is saved.

Run:  python -m tests.test_culturechange

One small mod in a temp folder: ``england`` (northern_european) and ``milan``
(southern_european). Its EDB gates a barracks and a pool by culture, by faction,
with ``not`` and with ``or``; its campaign gives england a town with two
buildings. England is previewed as southern_european. What has to hold:

* **a clause reads cultures and factions alike**, left to right, ``not`` and
  ``or`` included, and a clause with no ``factions { }`` is open to everyone;
* **the units**: gained and lost by the pools' clauses and the levels' own, a
  unit named by faction or by everyone is neither, and a gained unit whose EDU
  ownership leaves the faction out is said so;
* **the buildings in its towns**: the level the new culture cannot build is
  listed, the one open to everyone is not;
* **nothing is written**, and no change, an unknown faction or no EDB say so.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import culturechange as cc                       # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


NL = chr(13) + chr(10)


def crlf(text: str) -> str:
    return NL.join(text.strip("\n").split("\n")) + NL


def record(slot, culture):
    return f"""
faction						{slot}
culture						{culture}
religion					catholic
symbol						models_strat/symbol_{slot}.CAS
rebel_symbol				models_strat/symbol_rebels.CAS
primary_colour				red 200, green 10, blue 10
secondary_colour			red 130, green 20, blue 30
loading_logo				loading_screen/symbols/symbol128_{slot}.tga
standard_index				6
logo_index					FACTION_LOGO_{slot.upper()}
small_logo_index			SMALL_FACTION_LOGO_{slot.upper()}
triumph_value				5
custom_battle_availability	yes
can_sap						yes
prefers_naval_invasions		no
can_have_princess			yes
has_family_tree				yes
"""


def unit(name, own):
    return f"""
type             {name}
dictionary       {name.replace(' ', '_')}
category         infantry
class            light
soldier          militia, 40, 0, 1
ownership        {own}
"""


EDB = """
hidden_resources river

building barracks
{
    levels town_watch town_guard
    {
        town_watch city requires factions { northern_european, southern_european, }
        {
            capability
            {
                recruit_pool "Peasants"  1   0.5   2  0  requires factions { southern_european, }
                recruit_pool "Spear Militia"  1   0.5   2  0  requires factions { northern_european, }
                recruit_pool "Town Militia"  1   0.5   2  0
                recruit_pool "English Archers"  1   0.5   2  0  requires factions { england, }
                recruit_pool "Italian Crossbows"  1   0.5   2  0  requires factions { milan, } or factions { southern_european, }
                recruit_pool "Not Southern"  1   0.5   2  0  requires not factions { southern_european, }
            }
            construction 2
            cost 400
            upgrades
            {
                town_guard
            }
        }
        town_guard city requires factions { northern_european, }
        {
            capability
            {
                recruit_pool "Huscarls"  1   0.5   2  0
            }
            construction 2
            cost 600
            upgrades
            {
            }
        }
    }
}

building market
{
    levels corn_exchange
    {
        corn_exchange city requires factions { all, }
        {
            capability
            {
            }
            construction 2
            cost 600
            upgrades
            {
            }
        }
    }
}
"""

STRAT = """
campaign		imperial_campaign
playable
	england
	milan
end
unlockable
end
nonplayable
end

start_date	1080 summer
end_date	1530 winter
timescale	2.00

faction	england, comfortable caderyn
ai_label		catholic
denari	2000
denari_kings_purse	2000
settlement
{
	level town
	region London
	year_founded 0
	population 1500
	plan_set default_set
	faction_creator england
	building
	{
		type barracks town_guard
	}
	building
	{
		type market corn_exchange
	}
}

faction	milan, comfortable caderyn
ai_label		catholic
denari	2000
settlement
{
	level town
	region Milan
	year_founded 0
	population 1500
	plan_set default_set
	faction_creator milan
	building
	{
		type barracks town_watch
	}
}
"""

FILES = {
    "descr_sm_factions.txt": record("england", "northern_european")
    + record("milan", "southern_european"),
    "export_descr_unit.txt": unit("Peasants", "england, milan")
    + unit("Spear Militia", "england") + unit("Town Militia", "england, milan")
    + unit("English Archers", "england") + unit("Italian Crossbows", "milan")
    + unit("Not Southern", "england") + unit("Huscarls", "england"),
    "export_descr_buildings.txt": EDB,
    "world/maps/campaign/imperial_campaign/descr_strat.txt": STRAT,
}


def build(root: Path, files) -> Mod:
    for rel, body in files.items():
        path = root / "data" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        kb.write_text(path, crlf(body), "utf-8")
    return Mod(root)


tmp = Path(_tmp.mkdtemp(prefix="ut_culture_"))
mod = build(tmp / "Here", FILES)
print(f"=== {tmp} ===")
before = {p.relative_to(mod.root).as_posix(): p.read_bytes()
          for p in Path(mod.root).rglob("*") if p.is_file()}

print("\n1) a clause, cultures and factions alike")
fc = {"england": "northern_european", "milan": "southern_european", "sicily": "southern_european"}
check("a culture means every faction of it",
      cc.admitted("factions { southern_european, }", fc) == {"milan", "sicily"})
check("a faction and a culture together",
      cc.admitted("factions { england, sicily, }", fc) == {"england", "sicily"})
check("all is everyone", cc.admitted("factions { all, }", fc) == set(fc))
check("no factions term is everyone", cc.admitted("hidden_resource river", fc) == set(fc))
check("not takes the culture out", cc.admitted("not factions { southern_european, }", fc) == {"england"})
check("or joins, and meets",
      cc.admitted("factions { england, } or factions { milan, }", fc) == {"england", "milan"}
      and cc.admitted("factions { all, } and not factions { milan, }", fc) == {"england", "sicily"})

print("\n2) england as southern_european")
p = cc.preview(mod, "england", "southern_european")
gained = {r["unit"]: r for r in p["gained"]}
lost = {r["unit"]: r for r in p["lost"]}
check("it reads the EDB and knows the old culture",
      p["has_edb"] and p["old"] == "northern_european" and not p["same"])
check("gains the southern pools: Peasants and Italian Crossbows",
      set(gained) == {"Peasants", "Italian Crossbows"})
check("loses the northern pool, the not-southern one and what its lost level trained",
      set(lost) == {"Spear Militia", "Not Southern", "Huscarls"})
check("a unit named by faction or by everyone is neither",
      not {"English Archers", "Town Militia"} & (set(gained) | set(lost)))
check("each row says the level it is trained at",
      gained["Peasants"]["levels"] == ["town_watch"] and lost["Huscarls"]["levels"] == ["town_guard"])
check("a gained unit its ownership leaves out is said so",
      gained["Italian Crossbows"]["owned"] is False and gained["Peasants"]["owned"] is True)
towns = [(b["region"], b["level"]) for b in p["buildings"]]
check("the town's barracks level the new culture cannot build is listed",
      towns == [("London", "town_guard")])
check("  with its line and its campaign",
      p["buildings"][0]["line"] == "barracks" and p["buildings"][0]["campaign"] == "imperial_campaign")

print("\n3) nothing to say")
check("the same culture is no change", cc.preview(mod, "england", "Northern_European")["same"])
check("an unknown faction gives nothing back",
      cc.preview(mod, "france", "southern_european")["gained"] == [])
back = cc.preview(mod, "milan", "northern_european")
check("milan the other way loses Peasants but keeps the crossbows its own name holds",
      {r["unit"] for r in back["lost"]} == {"Peasants"})
check("  and gains the northern pools, the northern level's among them",
      {r["unit"] for r in back["gained"]} == {"Spear Militia", "Not Southern", "Huscarls"})
(Path(mod.root) / "data" / "export_descr_buildings.txt").rename(
    Path(mod.root) / "data" / "edb.off")
bare = cc.preview(Mod(mod.root), "england", "southern_european")
check("no EDB says so rather than guessing", bare["has_edb"] is False and bare["gained"] == [])
(Path(mod.root) / "data" / "edb.off").rename(
    Path(mod.root) / "data" / "export_descr_buildings.txt")

after = {p.relative_to(mod.root).as_posix(): p.read_bytes()
         for p in Path(mod.root).rglob("*") if p.is_file()}
check("nothing was written", before == after)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
