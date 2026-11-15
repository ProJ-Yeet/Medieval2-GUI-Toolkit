"""Lua scripts over the toolkit's data: reads, preview, apply, one Undo (121-123).

    python -m tests.test_luaapi

Runs on a copy of DaC's unit, text and modeldb files (skipped without DaC),
with the toolkit's config, Log and backups in a temporary folder.

1. the read API: every unit and entry, a unit's fields, frozen tables
2. a preview changes nothing on disk and leaves nothing in the Log, and says
   what --apply would change
3. --apply: one Log record for many edits; its Undo puts every byte back
4. edits see the edits before them (a rename, then the new name)
5. an edit the editor refuses, and a script error, undo the run's edits
6. delete a unit; clone a modeldb entry, then edit the clone
7. lua_cli.py: run, --apply, undo, api, and its exit codes
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, luaapi, luarun  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


MODS = _realmod.mods(required=False)
DAC = MODS / "Divide_and_Conquer_EUR" if MODS else None
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt", "export_descr_buildings.txt", "text/export_buildings.txt", "text/expanded.txt",
       "descr_sm_factions.txt", "world/maps/campaign/imperial_campaign/descr_mercenaries.txt",
       "export_descr_character_traits.txt", "text/export_vnvs.txt", "export_descr_ancillaries.txt",
       "text/export_ancillaries.txt")
if not luarun.available() or not DAC or not (DAC / "data" / REL[0]).is_file():
    print("needs lupa and Divide_and_Conquer_EUR; skipped")
    sys.exit(0)

tmp = Path(_tmp.mkdtemp(prefix="ut_luaapi_"))
cfg = tmp / "config"
cfg.mkdir()
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"


def fresh(tag) -> Mod:
    root = tmp / tag / "mods" / "Dest"
    for rel in REL:
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    return Mod(root)


def shas(mod) -> dict:
    return {p.relative_to(mod.root).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in sorted(Path(mod.root).rglob("*")) if p.is_file()}


def script(name, text) -> Path:
    p = tmp / "scripts" / name
    p.parent.mkdir(exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


mod = fresh("a")
units = mod.edu.units
u0, u1 = units[0], units[1]
print(f"(DaC copy: {len(units)} units, {len(mod.modeldb.entries)} modeldb entries)")

print("1. reads")
s = script("read.lua", f"""
local us = toolkit.units()
local u = toolkit.unit({u0.type!r})
print(#us, #toolkit.models(), u.type, u.fields.category, #u.field_order > 5, u.eop)
print(toolkit.unit("no such unit") == nil, toolkit.mod.name)
local ok, e = pcall(function() u.category = "x" end)
print(ok, toolkit.model(u.soldier) ~= nil)
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("counts and fields", rep.printed and rep.printed[0] ==
      f"{len(units)}\t{len(mod.modeldb.entries)}\t{u0.type}\t{u0.category}\ttrue\tfalse")
check("a missing unit is nil; mod name", rep.printed[1] == "true\tDest")
check("a write is refused; its soldier entry is found", rep.printed[2] == "false\ttrue")
check("reading leaves no Log record", config.load_log() == [])

print("2. preview")
before = shas(mod)
edit_two = script("two.lua", f"""
local a = toolkit.unit({u0.type!r})
toolkit.edit_unit(a.type, {{ ["stat_pri_armour"] = "9, 9, 9, metal" }})
toolkit.edit_unit({u1.type!r}, {{ ["stat_mental"] = "13, disciplined, trained" }})
print(toolkit.unit(a.type).fields.stat_pri_armour)
""")
rep = luaapi.run(mod, edit_two)
check(f"preview ok ({rep.error})", rep.ok and not rep.applied)
check("the second read sees the first edit", rep.printed == ["9, 9, 9, metal"])
check("one file would change", [f.rel for f in rep.files] == ["data/export_descr_unit.txt"])
check("its diff has both edits", rep.files and "9, 9, 9, metal" in rep.files[0].diff
      and "13, disciplined, trained" in rep.files[0].diff)
check("every byte back after a preview", shas(mod) == before)
check("the Log holds nothing", config.load_log() == [])
check("no backup folder left", not any(config.BACKUP_DIR.glob("*")) if config.BACKUP_DIR.exists() else True)

print("3. apply")
rep = luaapi.run(mod, edit_two, apply=True)
log = config.load_log()
check("applied", rep.ok and rep.applied and rep.log_id)
check("one Log record, mode lua", len(log) == 1 and log[0]["mode"] == "lua" and log[0]["id"] == rep.log_id)
check("the file changed", shas(mod) != before)
check("the edit is on disk", "9, 9, 9, metal" in Mod(mod.root).edu.by_type()[u0.type].raw)
luaapi.undo(rep.log_id)
check("Undo puts every byte back", shas(mod) == before)

print("4. chained")
mod = fresh("b")
before = shas(mod)
s = script("chain.lua", f"""
toolkit.edit_unit({u0.type!r}, {{}}, {{rename = "lua renamed unit"}})
toolkit.edit_unit("lua renamed unit", {{ ["stat_cost"] = "1, 1, 1, 1, 1, 1" }})
print(toolkit.unit({u0.type!r}) == nil, toolkit.unit("lua renamed unit").fields.stat_cost)
""")
rep = luaapi.run(mod, s, apply=True)
check(f"rename then edit by the new name ({rep.error})", rep.ok and rep.printed == ["true\t1, 1, 1, 1, 1, 1"])
check("one record for both", len(config.load_log()) == 2 and config.load_log()[-1]["id"] == rep.log_id)
luaapi.undo(rep.log_id)
check("Undo puts every byte back", shas(mod) == before)

print("5. refused and failed")
n_log = len(config.load_log())
s = script("refused.lua", f"""
toolkit.edit_unit({u0.type!r}, {{ ["stat_cost"] = "2, 2, 2, 2, 2, 2" }})
toolkit.edit_unit({u1.type!r}, {{}}, {{rename = {u0.type!r}}})
""")
rep = luaapi.run(mod, s, apply=True)
check(f"refused ({rep.error_kind}: {rep.error[:70]})", not rep.ok and rep.error_kind == "refused")
check("the first edit was undone", shas(mod) == before)
check("nothing new in the Log", len(config.load_log()) == n_log)
s = script("fails.lua", f"""
toolkit.edit_unit({u0.type!r}, {{ ["stat_cost"] = "3, 3, 3, 3, 3, 3" }})
local x = nil
print(x.y)
""")
rep = luaapi.run(mod, s, apply=True)
check(f"a script error ({rep.error_kind})", not rep.ok and rep.error_kind == "error" and "fails.lua:4" in rep.error)
check("its edit was undone, nothing in the Log", shas(mod) == before and len(config.load_log()) == n_log)
s = script("nounit.lua", 'toolkit.edit_unit("no such unit", {})')
rep = luaapi.run(mod, s, apply=True)
check("a missing unit is refused", not rep.ok and rep.error_kind == "refused" and "no unit" in rep.error)

print("6. delete, clone")
victim = units[-1]
src = victim.soldier_model.lower()
s = script("del.lua", f"""
toolkit.delete_unit({victim.type!r})
print(toolkit.unit({victim.type!r}) == nil)
toolkit.clone_model({src!r}, "lua_clone_entry")
toolkit.edit_model("lua_clone_entry", {{ texture = "unit_models/_units/lua/test.texture" }})
local m = toolkit.model("lua_clone_entry")
print(m ~= nil, m and m.textures[1].texture)
""")
rep = luaapi.run(mod, s, apply=True)
check(f"runs ({rep.error})", rep.ok)
check("the unit is gone", rep.printed[:1] == ["true"])
check("the clone exists with its new texture",
      len(rep.printed) > 1 and rep.printed[1] == "true\tunit_models/_units/lua/test.texture")
check("the modeldb and the EDU changed", {"data/unit_models/battle_models.modeldb",
                                          "data/export_descr_unit.txt"} <= {f.rel for f in rep.files})
luaapi.undo(rep.log_id)
check("Undo puts every byte back", shas(mod) == before)

print("7. the CLI")
cli = [sys.executable, str(ROOT / "lua_cli.py")]
env_cfg = ("import sys; sys.argv[0]='lua_cli.py'; from unittransfer import config; from pathlib import Path; "
           f"c=Path({str(cfg)!r}); config.CONFIG_DIR=c; config.BACKUP_DIR=c/'backups'; "
           "config.SETTINGS_PATH=c/'settings.json'; config.LOG_PATH=c/'transfers.json'; "
           "import lua_cli; sys.exit(lua_cli.main(sys.argv[1:]))")


def cli_run(*a):
    return subprocess.run([sys.executable, "-c", env_cfg, *a], cwd=ROOT, capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


p = cli_run("api")
check("api lists edit_unit", p.returncode == 0 and "toolkit.edit_unit(" in p.stdout)
ann = tmp / "ann"
p = cli_run("annotations", str(ann))
stub = (ann / "toolkit.lua").read_text(encoding="utf-8") if (ann / "toolkit.lua").is_file() else ""
check("annotations written", p.returncode == 0 and (ann / ".luarc.json").is_file()
      and "---@class toolkit.Unit" in stub and "function toolkit.clone_model(source, name) end" in stub)
try:
    luarun.Session().run(stub, "toolkit.lua")
    stub_ok = True
except luarun.ScriptError as e:
    stub_ok = str(e)
check(f"the annotation file is valid Lua ({stub_ok})", stub_ok is True)
check("every API function is in it", all(f"function toolkit.{f.name}(" in stub for f in luaapi.API))
p = cli_run("run", str(edit_two), "--mod", str(mod.root))
check("a preview run exits 0 and says so", p.returncode == 0 and "preview" in p.stdout and shas(mod) == before)
p = cli_run("run", str(edit_two), "--mod", str(mod.root), "--apply")
lid = next((ln.split()[-1] for ln in p.stdout.splitlines() if "lua_cli.py undo" in ln), "")
check("--apply exits 0 with a Log id", p.returncode == 0 and lid and shas(mod) != before)
p = cli_run("undo", lid)
check("undo exits 0 and puts it back", p.returncode == 0 and shas(mod) == before)
p = cli_run("run", str(tmp / "scripts" / "refused.lua"), "--mod", str(mod.root), "--apply")
check("a refused edit exits 2", p.returncode == 2)
p = cli_run("run", str(tmp / "scripts" / "fails.lua"), "--mod", str(mod.root))
check("a script error exits 1", p.returncode == 1)
p = cli_run("run", "nope.lua", "--mod", str(mod.root))
check("a missing script exits 3", p.returncode == 3)
check("still every byte as it was", shas(mod) == before)

print("8. buildings and factions")
edb = mod.edb
bl = next(b for b in edb.buildings if any(k.recruits and "cost" in k.scalars for k in b.blocks))
blk = next(k for k in bl.blocks if k.recruits and "cost" in k.scalars)
pool = next(c for c in blk.capabilities if c.keyword == "recruit_pool")
s = script("bld.lua", f"""
local b = toolkit.building({bl.name!r})
local fs = toolkit.factions()
print(#toolkit.buildings(), b.name, #b.blocks, next(fs) ~= nil and fs[1].slot ~= "" and fs[1].culture ~= "")
local lv
for _, k in ipairs(b.blocks) do if k.name == {blk.name!r} then lv = k end end
print(lv.scalars.cost, #lv.recruits > 0)
toolkit.edit_building(b.name, lv.name, {{ scalars = {{ cost = 1234 }} }})
-- read again: the line numbers moved, and the cost is the new one
b = toolkit.building({bl.name!r})
for _, k in ipairs(b.blocks) do if k.name == {blk.name!r} then lv = k end end
local cap
for _, c in ipairs(lv.capabilities) do if c.keyword == "recruit_pool" then cap = c break end end
toolkit.edit_building(b.name, lv.name, {{ capabilities = {{
  {{ line = cap.line, delete = true }},
  {{ keyword = "recruit_pool", args = '"' .. {u0.type!r} .. '"  1  0.5  2  0', requires = "factions {{ england, }}" }},
}} }})
b = toolkit.building({bl.name!r})
for _, k in ipairs(b.blocks) do if k.name == {blk.name!r} then lv = k end end
print(lv.scalars.cost)
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check(f"buildings, the line, its levels, factions ({rep.printed[:1]})",
      rep.printed[:1] == [f"{len(edb.buildings)}\t{bl.name}\t{len(bl.blocks)}\ttrue"])
check("a level's cost and pools", len(rep.printed) > 1 and rep.printed[1] == f"{blk.scalars['cost']}\ttrue")
check("the cost edit is read back", rep.printed[-1:] == ["1234"])
d = next((f.diff for f in rep.files if f.rel == "data/export_descr_buildings.txt"), "")
check("the EDB diff: the cost, the pool out, the new pool in",
      "1234" in d and ("-" + "") in d and f'recruit_pool "{u0.type}"' in d and "factions { england, }" in d)
check("one file changed", [f.rel for f in rep.files] == ["data/export_descr_buildings.txt"])
check("the preview left every byte", shas(mod) == before)
s = script("bld_bad.lua", f'toolkit.edit_building({bl.name!r}, "no_such_level", {{ scalars = {{ cost = 1 }} }})')
rep = luaapi.run(mod, s)
check("a missing level is refused", not rep.ok and rep.error_kind == "refused")

print("9. clone a unit")
s = script("clone_unit.lua", f"""
toolkit.clone_unit({u0.type!r}, "Lua Clone Unit", {{ name = "Lua's Clone" }})
local c = toolkit.unit("Lua Clone Unit")
print(c ~= nil, c and c.dictionary, c and c.name, c and c.soldier == toolkit.unit({u0.type!r}).soldier)
toolkit.edit_unit("Lua Clone Unit", {{ ["stat_cost"] = "7, 7, 7, 7, 7, 7" }})
local ok, e = pcall(toolkit.clone_unit, {u0.type!r}, {u1.type!r})
print(ok, e)
""")
rep = luaapi.run(mod, s, apply=True)
check(f"runs ({rep.error})", rep.ok)
check("the clone, its dictionary, its shown name, its model",
      rep.printed[:1] == ["true\tlua_clone_unit\tLua's Clone\ttrue"])
check("cloning onto a taken name is refused", len(rep.printed) > 1 and rep.printed[1].startswith("false")
      and "already exists" in rep.printed[1])
log_now = config.load_log()
check("one Log record for clone and edit", log_now[-1]["id"] == rep.log_id
      and sum(1 for e in log_now if not e.get("undone") and e.get("applied")) == 1)
luaapi.undo(rep.log_id)
check("Undo puts every byte back", shas(mod) == before)

print("10. mercenary pools")
s = script("mercs.lua", f"""
local pools = toolkit.mercenaries()
local p = pools[1]
local u = p.units[1]
print(#pools > 0, #p.units > 1, u.place, type(u.cost))
toolkit.edit_merc_unit(p.name, 1, {{ cost = u.cost + 111 }})
toolkit.add_merc_unit(p.name, {{ name = {u0.type!r}, exp = 1, cost = 999, replenish = {{0.1, 0.2}}, max = 2, initial = 1 }})
local after = toolkit.mercenaries()[1]
print(after.units[1].cost == u.cost + 111, after.units[#after.units].name, #after.units == #p.units + 1)
toolkit.delete_merc_unit(p.name, #after.units)
print(#toolkit.mercenaries()[1].units == #p.units)
local ok, e = pcall(toolkit.edit_merc_unit, p.name, 0, {{ cost = 1 }})
print(ok)
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("pools, units, places from 1, numbers", rep.printed[:1] == ["true\ttrue\t1\tnumber"])
check("an edit and an add read back", len(rep.printed) > 1 and rep.printed[1] == f"true\t{u0.type}\ttrue")
check("the delete reads back", len(rep.printed) > 2 and rep.printed[2] == "true")
check("place 0 is refused", rep.printed[3:4] == ["false"])
d = next((f.diff for f in rep.files if f.rel.endswith("descr_mercenaries.txt")), "")
check("the diff is the cost line only (the add and the delete cancel)",
      [f.rel for f in rep.files] == ["data/world/maps/campaign/imperial_campaign/descr_mercenaries.txt"]
      and rep.files[0].added == 1 and rep.files[0].removed == 1)
check("the preview left every byte", shas(mod) == before)

print("11. traits")
from unittransfer import traits as _traits  # noqa: E402
tf = _traits.parse_file(mod.edct_path)
tr = next(t for t in tf.traits if len(t.levels) >= 2 and t.levels[1].effects)
s = script("traits.lua", f"""
local t = toolkit.trait({tr.name!r})
print(#toolkit.traits(), t.name, #t.levels, t.levels[2].threshold)
toolkit.edit_trait(t.name, {{ levels = {{ [2] = {{ threshold = 77, effects = {{
  {{ attribute = "Command", amount = 3 }}, {{ attribute = "Chivalry", amount = -1 }} }} }} }} }})
local after = toolkit.trait(t.name)
print(#after.levels, after.levels[2].threshold, #after.levels[2].effects, after.levels[1].threshold == t.levels[1].threshold)
local ok = pcall(toolkit.edit_trait, t.name, {{ levels = {{ [99] = {{ threshold = 1 }} }} }})
print(ok)
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("traits, levels, a threshold", rep.printed[:1] == [f"{len(tf.traits)}\t{tr.name}\t{len(tr.levels)}\t{tr.levels[1].threshold}"])
check("level 2 changed, level count and level 1 kept",
      len(rep.printed) > 1 and rep.printed[1] == f"{len(tr.levels)}\t77\t2\ttrue")
check("a level that is not there is refused", rep.printed[2:3] == ["false"])
d = next((f.diff for f in rep.files if f.rel == "data/export_descr_character_traits.txt"), "")
check("the diff: the threshold and the two effects", "77" in d and "Command" in d and "Chivalry" in d)
check("the preview left every byte", shas(mod) == before)

print("12. ancillaries")
from unittransfer import ancillaries as _anc  # noqa: E402
af = _anc.parse_file(mod.eda_path)
an = next(a for a in af.ancillaries if a.effects)
s = script("anc.lua", f"""
local a = toolkit.ancillary({an.name!r})
print(#toolkit.ancillaries(), a.name, #a.effects > 0)
toolkit.edit_ancillary(a.name, {{ effects = {{ {{ attribute = "Command", amount = 2 }} }} }})
local after = toolkit.ancillary(a.name)
print(#after.effects, after.effects[1].attribute, after.effects[1].amount)
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("ancillaries and one with effects", rep.printed[:1] == [f"{len(af.ancillaries)}\t{an.name}\ttrue"])
check("its effects replaced", rep.printed[1:2] == ["1\tCommand\t2"])
check("one file changed", [f.rel for f in rep.files] == ["data/export_descr_ancillaries.txt"])
check("the preview left every byte", shas(mod) == before)

print("13. the examples in docs/lua_examples, previewed")
ex = ROOT / "docs" / "lua_examples"
inf = next(u for u in units if u.category == "infantry" and u.ownership)
rep = luaapi.run(mod, ex / "raise_morale.lua", args={"faction": inf.ownership[0], "by": "2"})
check(f"raise_morale ({rep.error}{rep.printed[-1:] if rep.printed else ''})",
      rep.ok and rep.files and "get +2 morale" in rep.printed[-1])
rep = luaapi.run(mod, ex / "units_without_names.lua")
check(f"units_without_names ({rep.error})", rep.ok and rep.printed and "units have no shown name" in rep.printed[-1]
      and not rep.files)
rep = luaapi.run(mod, ex / "clone_entry.lua", args={"from": src, "name": "lua_example_clone"})
check(f"clone_entry ({rep.error})", rep.ok and rep.printed and rep.printed[-1].startswith("lua_example_clone:"))
check("previews left every byte and an empty Log", shas(mod) == before
      and not any(e.get("mode") == "lua" and not e.get("undone") for e in config.load_log()))

print("14. strings: a .strings.bin read, edited, added to, taken from")
for rel in ("text/event_titles.txt.strings.bin", "text/battle.txt.strings.bin"):
    shutil.copy2(DAC / "data" / rel, Path(mod.data) / rel)
from unittransfer import stringsbin as _sbin  # noqa: E402
sb = _sbin.read(Path(mod.data) / "text/event_titles.txt.strings.bin")
t1, t2, t3 = sb.tags[:3]
before = shas(mod)
s = script("strings.lua", f"""
local s = toolkit.strings("event_titles")
print(#s, s[1].tag, toolkit.string("event_titles.txt", {t2!r}) == s[2].value)
toolkit.edit_strings("event_titles", {{ [{t1!r}] = "Changed by Lua", LUA_NEW_TAG = "new one", [{t3!r}] = false }})
print(toolkit.string("event_titles", {t1!r}), toolkit.string("event_titles", "LUA_NEW_TAG"),
      toolkit.string("event_titles", {t3!r}) == nil)
toolkit.edit_strings("battle", {{ [3] = "third" }})
print(toolkit.strings("battle")[3].tag == "", toolkit.string("battle", 3))
print(pcall(toolkit.edit_strings, "battle", {{ x = "no tags here" }}))
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("entries, a tag, a lookup", rep.printed[:1] == [f"{len(sb)}\t{t1}\ttrue"])
check("an edit, an add and a removal read back", rep.printed[1:2] == ["Changed by Lua\tnew one\ttrue"])
check("an untagged archive by place", rep.printed[2:3] == ["true\tthird"])
check("an untagged archive refuses a tag", rep.printed[3:4] and rep.printed[3].startswith("false"))
d = next((f.diff for f in rep.files if f.rel.endswith("event_titles.txt.strings.bin")), "")
check("the preview diff shows entries, not '(binary file)'",
      "+{LUA_NEW_TAG}new one" in d and f"-{{{t3}}}" in d)
check("the preview left every byte", shas(mod) == before)

print("15. the campaign: settlements and strat objects")
shutil.copytree(DAC / "data/world/maps/base", Path(mod.data) / "world/maps/base")
for p in (DAC / "data/world/maps/campaign/imperial_campaign").glob("*.txt"):
    shutil.copy2(p, Path(mod.data) / "world/maps/campaign/imperial_campaign" / p.name)
from unittransfer import campstrat as _cs, stratobj as _so  # noqa: E402
sf = _cs.read_strat(mod, "imperial_campaign")
st = sf.of_kind("settlement")[0]
region, pop = str(st.get("region")), int(str(st.get("population")))
res = next(n for n in _so.objects(sf) if n.kind == "resource")
rx, ry = _so.read_spec(res).xy()
before = shas(mod)
s = script("camp.lua", f"""
local st = toolkit.settlements()
print(#st, st[1].region, st[1].population, #st[1].buildings > 0)
toolkit.edit_settlement(st[1].region, {{ population = st[1].population + 500 }})
print(toolkit.settlements()[1].population)
toolkit.edit_strat_object("resource", {rx}, {ry}, {{ name = "iron" }})
local moved
for _, o in ipairs(toolkit.strat_objects()) do
  if o.x == {rx} and o.y == {ry} and o.kind == "resource" then moved = o.name end
end
print(moved)
print(pcall(toolkit.add_strat_object, "resource", {{ x = -5, y = 3, name = "iron" }}))
print(pcall(toolkit.edit_settlement, "no_such_region", {{ population = 1 }}))
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("settlements read", rep.printed[:1] == [f"{len(sf.of_kind('settlement'))}\t{region}\t{pop}\ttrue"])
check("a population edit reads back", rep.printed[1:2] == [str(pop + 500)])
check("a resource edit reads back", rep.printed[2:3] == ["iron"])
check("a tile off the map is refused", rep.printed[3:4] and rep.printed[3].startswith("false"))
check("a region with no settlement is refused", rep.printed[4:5] and rep.printed[4].startswith("false"))
check("one file, two lines", [f.rel for f in rep.files] ==
      ["data/world/maps/campaign/imperial_campaign/descr_strat.txt"] and rep.files[0].added == 2)
check("the preview left every byte", shas(mod) == before)

print("16. faction clones")
s = script("clone_faction.lua", """
local f = toolkit.factions()
print(pcall(toolkit.clone_faction, f[1].slot, "luaclone"))
print(pcall(toolkit.clone_faction, f[1].slot, "luaclone", { colour = "red" }))
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("DaC's 31 slots: the editor's own refusal reaches the script",
      rep.printed[:1] and rep.printed[0].startswith("false") and "slot" in rep.printed[0])
check("an unknown option is refused", rep.printed[1:2] and "colour" in rep.printed[1])

print("17. triggers")
from unittransfer import triggers as _trg  # noqa: E402
tg = _trg.parse_file(mod.edct_path)
anc0 = _anc.parse_file(mod.eda_path).ancillaries[0].name
before = shas(mod)
s = script("trig.lua", f"""
local t = toolkit.triggers("traits")
print(#t, t[1].name, t[1].when_to_test, #t[1].conditions == {len(tg.triggers[0].conditions)})
toolkit.edit_trigger("traits", t[1].name, {{ when_to_test = "CharacterTurnStart" }})
toolkit.add_trigger("ancillaries", {{ name = "lua_test_trigger", when_to_test = "CharacterTurnEnd",
  conditions = {{ {{ term = "IsGeneral" }} }},
  effects = {{ {{ keyword = "AcquireAncillary", args = {{ {anc0!r}, "chance", 5 }} }} }} }})
toolkit.delete_trigger("traits", t[2].name)
local after = toolkit.triggers("traits")
print(#after, after[1].when_to_test)
local a = toolkit.triggers("ancillaries")
print(a[#a].name, a[#a].effects[1].args[1])
print(pcall(toolkit.delete_trigger, "traits", "no_such_trigger"), pcall(toolkit.triggers, "units"))
""")
rep = luaapi.run(mod, s)
check(f"runs ({rep.error})", rep.ok)
check("triggers read", rep.printed[:1] == [f"{len(tg.triggers)}\t{tg.triggers[0].name}\t{tg.triggers[0].when_to_test}\ttrue"])
check("an edit and a delete read back", rep.printed[1:2] == [f"{len(tg.triggers) - 1}\tCharacterTurnStart"])
check("an added trigger reads back", rep.printed[2:3] == [f"lua_test_trigger\t{anc0}"])
check("a missing trigger and a wrong file are refused",
      rep.printed[3:4] and rep.printed[3].startswith("false") and "\tfalse\t" in rep.printed[3])
check("two files changed", sorted(f.rel for f in rep.files) ==
      ["data/export_descr_ancillaries.txt", "data/export_descr_character_traits.txt"])
check("the preview left every byte", shas(mod) == before)

print("18. the recruitment sheet's rows")
s = script("recruit.lua", """
local r = toolkit.recruits()
local x = r[1]
print(#r > 0, type(x.line), x.unit ~= "")
toolkit.edit_recruit(x.line, { maximum = x.maximum + 1, experience = 2 })
local y = toolkit.recruits()[1]
print(y.maximum == x.maximum + 1, y.experience, y.unit == x.unit)
print(pcall(toolkit.edit_recruit, x.line, { experience = 1.5 }))
print(pcall(toolkit.edit_recruit, 1, { maximum = 1 }))
""")
rep = luaapi.run(mod, s, apply=True)
check(f"runs ({rep.error})", rep.ok)
check("rows read", rep.printed[:1] == ["true\tnumber\ttrue"])
check(f"an edit reads back {rep.printed[1:2]}", rep.printed[1:2] == ["true\t2\ttrue"])
check("experience must be whole; line 1 is no recruit_pool",
      rep.printed[2:3] and rep.printed[2].startswith("false") and rep.printed[3:4] and rep.printed[3].startswith("false"))
check("applied as one record", rep.log_id and [f.rel for f in rep.files] == ["data/export_descr_buildings.txt"])
luaapi.undo(rep.log_id)
check("its Undo puts every byte back", shas(mod) == before)

print("19. the app's Lua tab: saved scripts, a run as JSON")
lst = luaapi.script_list()
check("the runtime, the examples and the API are listed",
      lst["available"] and {"raise_morale.lua", "clone_entry.lua"} <= {x["name"] for x in lst["examples"]}
      and any(f["name"] == "edit_recruit" for f in lst["api"]))
out = luaapi.app_run(mod, "../../evil name", f"print(args.n)\ntoolkit.edit_unit({u0.type!r}, {{ soldier = toolkit.unit({u0.type!r}).soldier }})",
                     args={"n": "7"})
check("the name stays inside config/lua_scripts", out["name"] == "evil_name.lua"
      and (luaapi.scripts_dir() / "evil_name.lua").is_file())
check(f"a preview as JSON ({out['error']})", out["ok"] and not out["applied"] and out["printed"] == ["7"])
check("it is listed as saved", [x["name"] for x in luaapi.script_list()["scripts"]] == ["evil_name.lua"])
out = luaapi.app_run(mod, "bad", "error('stop here')")
check("a script error comes back with its line", not out["ok"] and "bad.lua:1" in out["error"])
check("the previews left every byte", shas(mod) == before)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
