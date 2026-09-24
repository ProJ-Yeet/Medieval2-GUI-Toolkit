"""Phase 76: building lines brought in from another mod.

    python -m tests.test_edbimport

A small hand-written source EDB with Divide and Conquer's factions, cultures,
religions, resources and units, into a copy of ROCSS's buildings, then every
real line of Divide and Conquer planned into that copy.

1. The list: every source line, and which the destination has by name.
2. One line planned: a faction both have stays, one whose culture the
   destination has is mapped onto it, one with neither is left out; a pool for
   a unit the destination lacks is left out and named; a capability for nobody,
   for a missing resource or religion, is left out; a missing hidden resource
   is added; a convert_to to nowhere is dropped; nothing is written.
3. The text keys: the three per level, a missing one filled, a faction's own
   wording carried under its new name, a longer level name never mistaken for
   one. The cards: the source's own, and a borrowed one only where none is.
4. Refusals: a level needing a line not brought (and fine once it is), a line
   name the destination has (and swapped in place with Replace), a level name
   another line owns, a line nobody could build.
5. A mapping chosen by hand.
6. Applied and undone, byte for byte.
7. Every real Divide and Conquer line planned into ROCSS: none writes a faction
   ROCSS lacks, and every refusal is one of the refusals above.
8. The routes.
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import _tmp  # noqa: E402
from unittransfer import buildings as B, config, edbimport as E, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


roc, dac = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
NAMES = ("descr_sm_factions.txt", "descr_cultures.txt", "descr_religions.txt",
         "descr_sm_resources.txt", "export_descr_unit.txt")
if not all((m / "data" / n).is_file() for m in (roc, dac) for n in NAMES + (B.EDB_REL,)):
    print("SKIPPED - needs ROCSS and Divide and Conquer installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

med2 = Path(_tmp.mkdtemp(prefix="ut_edbimp_"))
into, frm = med2 / "mods" / "TreeInto" / "data", med2 / "mods" / "TreeFrom" / "data"
for d, real in ((into, roc), (frm, dac)):
    (d / "text").mkdir(parents=True)
    for n in NAMES:
        shutil.copy2(real / "data" / n, d / n)
shutil.copy2(roc / "data" / B.EDB_REL, into / B.EDB_REL)
shutil.copy2(roc / "data" / B.LOC_REL, into / B.LOC_REL)
D, S = Mod(into.parent), Mod(frm.parent)

# ---- the names, picked off the two real mods rather than assumed ----
dfac, sfac = B.faction_cultures(D), B.faction_cultures(S)
SHARED = next(f for f in sorted(sfac) if f in dfac)
MAPPED = next(f for f in sorted(sfac) if f not in dfac and sfac[f] in set(dfac.values()))
DROPPED = next((f for f in sorted(sfac) if f not in dfac
                and sfac[f] not in set(dfac.values())), "")
CUL = sfac[MAPPED]
KNOWN = D.edu.units[0].type
TAKEN = D.edb.buildings[0].blocks[0].name
print(f"  shared {SHARED}, mapped {MAPPED} -> {CUL}, dropped {DROPPED or '(none)'}, "
      f"known unit {KNOWN!r}, a level ROCSS has: {TAKEN}")
if not DROPPED:
    print("SKIPPED - the two mods no longer have a faction of a culture ROCSS lacks")
    sys.exit(0)
DROP_CUL = sfac[DROPPED]
BORROW_TO = sorted(set(dfac.values()) - {CUL})[0]

EDB = f"""hidden_resources river_76

building smithy_76
{{
	convert_to castle_smithy_76
	levels forge_76 big_forge_76
	{{
		forge_76 city requires factions {{ {SHARED}, {MAPPED}, {DROPPED}, }}
		{{
			capability
			{{
				recruit_pool "{KNOWN}"  1  0.5  2  0  requires factions {{ {SHARED}, {MAPPED}, }}
				recruit_pool "Nobody Has These Axemen"  1  0.5  2  0  requires factions {{ {SHARED}, }}
				weapon_simple 1  requires factions {{ {DROPPED}, }}
				trade_base_income_bonus 1  requires resource no_such_resource_76
				religion no_such_religion_76 1
				armour 1  requires factions {{ {SHARED}, }} and hidden_resource deep_mine_76
			}}
			material wooden
			construction 2
			cost 400
			settlement_min town
			upgrades
			{{
				big_forge_76
			}}
		}}
		big_forge_76 city requires factions {{ {SHARED}, {MAPPED}, }}
		{{
			capability
			{{
				recruit_pool "{KNOWN}"  2  0.7  3  0  requires factions {{ {MAPPED}, }}
			}}
			material stone
			construction 3
			cost 900
			settlement_min large_town
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}

building market_76
{{
	levels stall_76
	{{
		stall_76 city requires factions {{ {SHARED}, }}
		{{
			capability
			{{
			}}
			material wooden
			construction 1
			cost 200
			settlement_min village
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}

building hall_76
{{
	levels hall_one_76
	{{
		hall_one_76 city requires factions {{ {SHARED}, }} and building_present_min_level market_76 stall_76
		{{
			capability
			{{
			}}
			material wooden
			construction 1
			cost 200
			settlement_min village
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}

building barracks
{{
	levels drill_76
	{{
		drill_76 city requires factions {{ {SHARED}, }}
		{{
			capability
			{{
			}}
			material wooden
			construction 1
			cost 200
			settlement_min village
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}

building clash_76
{{
	levels {TAKEN}
	{{
		{TAKEN} city requires factions {{ {SHARED}, }}
		{{
			capability
			{{
			}}
			material wooden
			construction 1
			cost 200
			settlement_min village
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}

building nobody_76
{{
	levels only_76
	{{
		only_76 city requires factions {{ {DROPPED}, }}
		{{
			capability
			{{
			}}
			material wooden
			construction 1
			cost 200
			settlement_min village
			upgrades
			{{
			}}
		}}
	}}
	plugins
	{{
	}}
}}
"""
(frm / B.EDB_REL).write_text(EDB, encoding=B.ENCODING)
TEXT = "\ufeff" + "\n".join([
    "{forge_76}Forge", "{forge_76_desc}A forge.", "{forge_76_desc_short}Forge.",
    f"{{forge_76_{MAPPED}}}Their Forge", f"{{forge_76_{MAPPED}_desc}}Their forge.",
    "{forge_76_house}Not a variant",
    "{big_forge_76}Big Forge", "{big_forge_76_desc}A big forge.",
    "{smithy_76_name}Smithy",
    "{stall_76}Stall", "{stall_76_desc}.", "{stall_76_desc_short}.",
    "{hall_one_76}Hall", "{hall_one_76_desc}.", "{hall_one_76_desc_short}.",
    "{drill_76}Drill", "{drill_76_desc}.", "{drill_76_desc_short}.",
]) + "\n"
(frm / B.LOC_REL).write_text(TEXT, encoding="utf-16-le")
# the cards: the shared culture's own pair, and the dropped culture's for borrowing
dcul = dfac[SHARED]
for c, stem in ((dcul, "forge_76"), (DROP_CUL, "forge_76")):
    b = frm / "ui" / c / "buildings"
    b.mkdir(parents=True, exist_ok=True)
    (b / f"#{c}_{stem}.tga").write_bytes(b"")                 # a packer's stub
    (b / f"#{c}_{stem}.tga.dds").write_bytes(b"DDS " + c.encode())
for c in sorted(set(dfac.values())):
    (into / "ui" / c / "buildings").mkdir(parents=True, exist_ok=True)
D, S = Mod(into.parent), Mod(frm.parent)


def snapshot():
    return {p.relative_to(into).as_posix(): p.read_bytes()
            for p in into.rglob("*") if p.is_file()}


print("1) the list")
rows = {r["name"]: r for r in E.sources(S, D)}
check("every source line is listed", set(rows) >= {"smithy_76", "hall_76", "barracks"})
check("barracks is said to be in the destination too, smithy_76 is not",
      rows["barracks"]["in_dest"] and not rows["smithy_76"]["in_dest"])
check("with its shown name", rows["smithy_76"]["label"] == "Smithy")
t = E.targets(D)
check("the destination's factions and cultures are there to map onto",
      any(f["name"] == SHARED for f in t["factions"]) and CUL in t["cultures"])

print("\n2) one line planned")
before = snapshot()
p = E.plan(D, S, {"lines": ["smithy_76"]})
d = p.payload()
check(f"it plans ({'; '.join(p.errors)})", d["ok"])
check("and a plan writes nothing", snapshot() == before)
names = {n["name"]: n for n in d["names"]}
check(f"{MAPPED} maps onto its own culture {CUL} by default",
      names.get(MAPPED, {}).get("to") == CUL)
check(f"{DROPPED} is left out by default, its culture {DROP_CUL} being ROCSS-less",
      names.get(DROPPED, {}).get("to") == "")
check(f"{SHARED} is not asked about at all", SHARED not in names)
after = B.parse_text(p.edb_text)
sm = after.get("smithy_76")
forge = sm.level("forge_76")
check("the forge's own clause names the shared faction and the culture",
      B.clause_factions(forge.requires) == [SHARED, CUL])
pools = [x.unit for x in forge.recruits]
check("the pool for a known unit stays", pools == [KNOWN])
check("the unknown unit is named, once", d["units_left"] == [
      {"unit": "Nobody Has These Axemen", "pools": 1}])
kw = [c.keyword for c in forge.capabilities]
check("a capability for nobody, for a missing resource and for a missing "
      "religion are left out; the hidden-resource one stays",
      kw == ["recruit_pool", "armour"], )
check("and counted by reason", sum(d["caps_left"].values()) == 3)
check("the missing hidden resource is added to the list",
      d["hidden_added"] == ["deep_mine_76"] and "deep_mine_76" in after.hidden_resources
      and len(after.hidden_resources) == len(D.edb.hidden_resources) + 1)
check("the convert_to to a line nowhere is dropped, with a warning",
      not sm.convert_to and any("castle_smithy_76" in w for w in d["warnings"]))
big = sm.level("big_forge_76")
check("the second level's lone pool is kept for the mapped culture",
      [x.unit for x in big.recruits] == [KNOWN]
      and B.clause_factions(big.capabilities[0].requires) == [CUL])
old = D.edb.lines
new = after.lines
diff = [i for i, (a, b) in enumerate(zip(old, new))
        if a != b and not (i == len(old) - 1 and b == a + "\n")]
check("everything above the new line is as it was, but the one hidden_resources "
      "line (and a last line given the line ending it lacked)",
      diff == [D.edb.hidden_resources_line])

print("\n3) text and cards")
pairs = dict(__import__("unittransfer.stringsbin", fromlist=["x"]).from_txt(p.loc_text))
check("the three keys of each level", all(k in pairs for k in (
    "forge_76", "forge_76_desc", "forge_76_desc_short", "big_forge_76",
    "big_forge_76_desc", "big_forge_76_desc_short")))
check("the one the source lacks is written blank, with a warning",
      pairs["big_forge_76_desc_short"] == ""
      and any("text key" in w for w in d["warnings"]))
check(f"{MAPPED}'s own wording arrives as the {CUL} wording",
      pairs.get(f"forge_76_{CUL}") == "Their Forge"
      and pairs.get(f"forge_76_{CUL}_desc") == "Their forge.")
check("a key that only looks like a variant is not carried",
      "forge_76_house" not in pairs and f"forge_76_{MAPPED}" not in pairs)
check("the line's heading comes too", pairs.get("smithy_76_name") == "Smithy")
check("every key the destination had is still there",
      set(dict(__import__("unittransfer.stringsbin", fromlist=["x"]).from_txt(
          (into / B.LOC_REL).read_text(encoding="utf-16")))) <= set(pairs))
pics = set(d["pictures"])
check(f"the {dcul} card comes, as its .tga.dds; the empty stub stays behind",
      f"ui/{dcul}/buildings/#{dcul}_forge_76.tga.dds" in pics
      and f"ui/{dcul}/buildings/#{dcul}_forge_76.tga" not in pics)
p2 = E.plan(D, S, {"lines": ["smithy_76"], "map": {DROPPED: BORROW_TO}})
check(f"mapped onto {BORROW_TO}, the {DROP_CUL} card is borrowed for it",
      f"ui/{BORROW_TO}/buildings/#{BORROW_TO}_forge_76.tga.dds" in p2.payload()["pictures"])
own = into / "ui" / BORROW_TO / "buildings" / f"#{BORROW_TO}_forge_76.tga"
own.write_bytes(b"theirs")
p3 = E.plan(D, S, {"lines": ["smithy_76"], "map": {DROPPED: BORROW_TO}})
check("...but not over a card the destination already draws",
      not any(r.startswith(f"ui/{BORROW_TO}/") for r in p3.payload()["pictures"])
      and p3.pictures_kept == 1)
own.unlink()
before = snapshot()

print("\n4) refusals")
r = E.plan(D, S, {"lines": ["hall_76"]})
check("a level needing a line not brought is refused, naming the line",
      any("add the 'market_76' line to the import" in e for e in r.errors))
check("and with it brought, it plans", not E.plan(D, S, {"lines": ["hall_76", "market_76"]}).errors)
r = E.plan(D, S, {"lines": ["barracks"]})
check("a line name the destination has is refused without Replace",
      any("tick Replace" in e for e in r.errors))
r = E.plan(D, S, {"lines": ["barracks"], "replace": True})
check("with Replace it plans", not r.errors)
if not r.errors:
    a = B.parse_text(r.edb_text)
    check("and is swapped in place, where the old one began",
          a.get("barracks").start == D.edb.get("barracks").start
          and [b.name for b in a.get("barracks").blocks] == ["drill_76"])
r = E.plan(D, S, {"lines": ["clash_76"]})
check(f"a level name another line owns ({TAKEN}) is refused",
      any(f"already has a level called {TAKEN!r}" in e for e in r.errors))
r = E.plan(D, S, {"lines": ["nobody_76"]})
check("a line nobody could build is refused, naming who to map",
      any("could build any level" in e and DROPPED in e for e in r.errors))
check("an unknown line is refused", E.plan(D, S, {"lines": ["no_such_line"]}).errors)
check("so is nothing at all", E.plan(D, S, {"lines": []}).errors)

print("\n5) a mapping chosen by hand")
r = E.plan(D, S, {"lines": ["smithy_76"], "map": {DROPPED: SHARED, MAPPED: ""}})
a = B.parse_text(r.edb_text).get("smithy_76")
f = a.level("forge_76")
check(f"{DROPPED} onto {SHARED}: its capability comes back, now for {SHARED}",
      any(c.keyword == "weapon_simple" and B.clause_factions(c.requires) == [SHARED]
          for c in f.capabilities))
check(f"{MAPPED} left out: the clause names {SHARED} once",
      B.clause_factions(f.requires) == [SHARED])
check("and the pool only it had is left out as a capability for nobody",
      not a.level("big_forge_76").capabilities)
r = E.plan(D, S, {"lines": ["smithy_76"], "map": {MAPPED: "not_a_faction_here"}})
check("a mapping onto a name the destination lacks is read as left out",
      next(n for n in r.names if n["name"] == MAPPED)["to"] == "")

print("\n6) applied, and undone")
p = E.plan(D, S, {"lines": ["smithy_76", "hall_76", "market_76"]})
res = E.apply(p)
now = Mod(into.parent)
check("the three lines are in the EDB",
      all(now.edb.get(n) for n in ("smithy_76", "hall_76", "market_76")))
check("the card is on disk", (into / f"ui/{dcul}/buildings/#{dcul}_forge_76.tga.dds")
      .read_bytes() == b"DDS " + dcul.encode())
check("the text reads back with the new keys",
      now.building_loc.get("forge_76") is not None)
check("one log record", res["record"]["action"] == "building-import"
      and res["record"]["manifest"]["created"])
transfer.undo(res["id"])
check("one Undo puts every file back byte for byte", snapshot() == before)

print("\n7) every real Divide and Conquer line into ROCSS")
R = Mod(dac)
refusals = {"to the import": 0, "already has a level": 0, "a religion": 0,
            "could build": 0, "requires": 0}
fine = total = 0
stray = []
known = E._Vocab(D)
for bl in R.edb.buildings:
    total += 1
    q = E.plan(D, R, {"lines": [bl.name], "replace": True, "pictures": False})
    if q.errors:
        e = q.errors[0]
        for k in refusals:
            if k in e:
                refusals[k] += 1
                break
        else:
            stray.append(e)
        continue
    fine += 1
    got = B.parse_text(q.edb_text).get(bl.name)
    for b in got.blocks:
        for clause in [b.requires] + [c.requires for c in b.capabilities + b.faction_capabilities]:
            bad = [v for v in B.clause_factions(clause) if not known.knows(v)]
            if bad:
                stray.append(f"{bl.name}/{b.name} names {bad}")
print(f"    {fine}/{total} plan alone; refused: {refusals}")
check("at least half of Divide and Conquer's lines plan on their own", fine * 2 >= total)
check("no planned line names a faction or culture ROCSS lacks, and every "
      "refusal is one of the kinds above", not stray)
for s_ in stray[:5]:
    print("     ", s_)

print("\n8) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, b):
    req = urllib.request.Request(BASE + path, data=json.dumps(b).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


g = get("/api/edbimport/lines?mod=TreeInto&from=TreeFrom")
check("GET /api/edbimport/lines lists the lines and the names to map onto",
      any(x["name"] == "smithy_76" for x in g.get("lines", []))
      and g.get("targets", {}).get("cultures"))
rb = {"mod": "TreeInto", "from": "TreeFrom", "lines": ["smithy_76"],
      "clear_strings_bin": False}
pl = post("/api/edbimport/plan", rb)
check("POST plan works it out and writes nothing",
      pl.get("plan", {}).get("ok") and snapshot() == before)
res = post("/api/edbimport/apply", rb)
check("POST apply writes it", res.get("id") and not res.get("error")
      and "smithy_76" in (into / B.EDB_REL).read_text(encoding=B.ENCODING))
transfer.undo(res["id"])
check("and the Undo takes it back", snapshot() == before)
bad = post("/api/edbimport/plan", dict(rb, **{"from": "TreeInto"}))
check("the same mod as its own source is refused", bool(bad.get("error")))
bad = post("/api/edbimport/plan", dict(rb, lines=["hall_76"]))
check("a refusal comes back as an error with the plan", bool(bad.get("error"))
      and bad.get("plan", {}).get("errors"))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
