"""Buildings mode: parse, edit and write data/export_descr_buildings.txt.

The EDB is the biggest hand-maintained file in a mod (Divide and Conquer's is
17.5k lines) and it is full of things a re-emitting parser destroys - trailing
``;ok old_pool=…`` comments on recruit_pool lines, mixed tabs and spaces, comma
separated ``levels`` lists. So the load-bearing checks here are:

  * every installed mod round-trips byte-for-byte through the parser
  * every level named in a ``levels`` line has a block, and vice versa
  * an edit is a SPLICE: only the lines that changed change, and re-saving an
    untouched level writes nothing at all
  * capabilities compare by meaning, not by text - re-sending
    ``1 0.135 3 0`` with different spacing is not an edit
  * apply writes the file, logs a backup manifest, and undo restores it exactly
  * a building rename rewrites text/export_buildings.txt with all three keys

    python -m tests.test_buildings
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import buildings, config, localization
from unittransfer.mod import Mod
from unittransfer.transfer import undo

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
#: Every mod installed on this machine - the parser must cope with all of them.
CANDIDATES = ("Divide_and_Conquer_EUR", "Third_Age_6", "third_age_3")
#: The one edits are applied to (copied into a temp folder first, never in place).
EDIT_MOD = "Divide_and_Conquer_EUR"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

installed = [m for m in CANDIDATES if (MODS / m / "data").is_dir()]
if not installed:
    print(f"none of {CANDIDATES} is installed under {MODS} - nothing to test")
    sys.exit(0)

# ---- 1) parse every installed mod ------------------------------------------
print("\n1) parsing every installed EDB")
for name in installed:
    mod = Mod(MODS / name)
    if not mod.edb_path.exists():
        print(f"  [skip] {name} has no EDB")
        continue
    raw = mod.edb_path.read_text(encoding=buildings.ENCODING)
    edb = buildings.parse_text(raw)
    check(f"{name}: round-trips byte-for-byte", edb.to_text() == raw)
    check(f"{name}: found building lines", len(edb.buildings) > 0)
    check(f"{name}: no parse warnings", not edb.warnings)
    declared_ok = all(lv in [b.name for b in bl.blocks]
                      for bl in edb.buildings for lv in bl.levels)
    blocks_ok = all(b.name in bl.levels for bl in edb.buildings for b in bl.blocks)
    check(f"{name}: every declared level has a block, and vice versa",
          declared_ok and blocks_ok)
    pools = [p for bl in edb.buildings for b in bl.blocks for p in b.recruits]
    check(f"{name}: recruit pools parsed ({len(pools)})", len(pools) > 0)
    check(f"{name}: every pool has a unit and four numbers",
          all(p.unit and p.initial and p.per_turn and p.maximum and p.experience != ""
              for p in pools))
    # spans must nest: a capability block sits inside its level
    spans_ok = all(b.start < b.cap_span[0] <= b.cap_span[1] < b.end
                   for bl in edb.buildings for b in bl.blocks if b.cap_span != (0, 0))
    check(f"{name}: capability blocks sit inside their level", spans_ok)

# ---- 2) a copy to edit ------------------------------------------------------
print(f"\n2) editing a copy of {EDIT_MOD}")
src_root = MODS / EDIT_MOD
work = Path(_tmp.mkdtemp(prefix="ut_edb_")) / EDIT_MOD
(work / "data" / "text").mkdir(parents=True)
shutil.copy2(src_root / "data" / buildings.EDB_REL, work / "data" / buildings.EDB_REL)
for rel in (buildings.LOC_REL, "export_descr_unit.txt", "text/export_units.txt",
            # the ownership check needs to know which factions and cultures exist,
            # and the fix needs the battle models it would add textures to
            "descr_sm_factions.txt", "descr_cultures.txt", "text/expanded.txt",
            "unit_models/battle_models.modeldb"):
    src = src_root / "data" / rel
    if src.exists():
        (work / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, work / "data" / rel)

# A mod's cultures are its data/ui/<culture>/buildings folders, and the copy
# above brings no art across - recreate the folders (empty) so the per-culture
# name keys have the same culture list to work against as the real mod.
for c in buildings.cultures_of(Mod(src_root)):
    (work / "data" / "ui" / c / "buildings").mkdir(parents=True, exist_ok=True)

mod = Mod(work)
original = mod.edb_path.read_text(encoding=buildings.ENCODING)
edb = mod.edb

# pick a level that has recruit pools AND at least one plain capability, so the
# edit below can touch a pool, a scalar and a non-pool capability in one go
pairs = [(bl, b) for bl in edb.buildings for b in bl.blocks if b.recruits]
line, target = next(((bl, b) for bl, b in pairs
                     if len(b.capabilities) > len(b.recruits)), pairs[0])
print(f"  using {line.name} / {target.name} "
      f"({len(target.recruits)} pools, {len(target.capabilities)} capabilities)")

# ---- 3) re-saving an untouched level changes nothing -------------------------
print("\n3) a no-op save")


def level_payload(blk, **over):
    """What the page sends for one level: everything, unchanged unless overridden."""
    caps = [{"line": c.line, "keyword": c.keyword,
             # deliberately re-spaced, the way the browser rebuilds a pool line
             "args": " ".join(c.args.split()), "requires": c.requires, "delete": False}
            for c in blk.capabilities]
    out = {"name": blk.name, "settlement": blk.settlement, "requires": blk.requires,
           "scalars": dict(blk.scalars), "upgrades": list(blk.upgrades),
           "capabilities": caps}
    out.update(over)
    return out


plan = buildings.plan_edit(mod, {"line": line.name, "levels": [level_payload(target)]})
check("re-sending a level unchanged is not a change", not plan.changes)
check("…and rewrites nothing", not plan.edb_text and not plan.loc_text)
check("…even though the pool numbers were re-spaced",
      any("  " in c.args for c in target.recruits and target.capabilities))

# ---- 4) a real edit is a surgical splice ------------------------------------
print("\n4) a real edit")
pool_cap = next(c for c in target.capabilities if c.is_recruit)
pool = pool_cap.pool()
pool.per_turn, pool.maximum = "0.9", "7"
plain = next((c for c in target.capabilities if not c.is_recruit), None)
caps = [{"line": c.line, "keyword": c.keyword, "args": c.args,
         "requires": c.requires, "delete": False} for c in target.capabilities]
for c in caps:
    if c["line"] == pool_cap.line:
        c["args"] = pool.to_args()
if plain is not None:
    caps = [c for c in caps if c["line"] != plain.line] + \
           [{"line": plain.line, "keyword": plain.keyword, "args": plain.args,
             "requires": plain.requires, "delete": True}]
caps.append({"line": None, "keyword": "recruit_pool",
             "args": '"Peasant Militia"  1  0.5  2  0', "requires": "", "delete": False})

new_cost = str(int(target.scalars.get("cost", "100")) + 111)
payload = {"line": line.name,
           "levels": [level_payload(target, scalars={**target.scalars, "cost": new_cost},
                                    capabilities=caps)]}
plan = buildings.plan_edit(mod, payload)
check("the plan has exactly the four intended changes", len(plan.changes) == 4)
check("no errors or warnings", not plan.errors and not plan.warnings)
check("the EDB would be rewritten", bool(plan.edb_text))

old_lines = original.splitlines()
new_lines = plan.edb_text.splitlines()
# one capability added, one removed - so the file grows by one line only when
# there was no plain capability to delete
check("the file grows by the added line and shrinks by the removed one",
      len(new_lines) == len(old_lines) + 1 - (1 if plain is not None else 0))
# the added line shifts everything under it, so compare the untouched HEAD only
head = min(pool_cap.line, plain.line if plain else pool_cap.line)
check("nothing above the edited block moved",
      old_lines[:head] == new_lines[:head])
check("the pool line kept its trailing comment",
      pool_cap.comment == "" or pool_cap.comment in plan.edb_text)

reparsed = buildings.parse_text(plan.edb_text)
rblk = reparsed.get(line.name).level(target.name)
check("the result still parses", not reparsed.warnings)
check("cost was written", rblk.scalars.get("cost") == new_cost)
rpool = next((p for p in rblk.recruits if p.unit == pool.unit), None)
check("the pool's new rate is there", rpool and rpool.per_turn == "0.9" and rpool.maximum == "7")
check("the new unit was added",
      any(p.unit == "Peasant Militia" for p in rblk.recruits))
if plain is not None:
    check("the deleted capability is gone",
          not any(c.keyword == plain.keyword and c.args == plain.args
                  for c in rblk.capabilities))

# ---- 5) apply + undo --------------------------------------------------------
print("\n5) apply, then undo")
rec = buildings.apply_edit(plan)
after = mod.edb_path.read_text(encoding=buildings.ENCODING)
check("the file on disk changed", after != original)
check("the file on disk is the planned text", after == plan.edb_text)
check("a backup was recorded", buildings.EDB_REL in rec["manifest"]["backed_up"])
check("the backup file exists",
      (Path(rec["backup_root"]) / "data" / buildings.EDB_REL).exists())
check("the log entry says it was a buildings edit", rec["mode"] == "buildings")

undo(rec["id"])
check("undo restores the EDB byte-for-byte",
      mod.edb_path.read_text(encoding=buildings.ENCODING) == original)

# ---- 6) renaming a building writes all three localisation keys --------------
print("\n6) renaming a building")
mod = Mod(work)                      # fresh, the undo above changed the file
if mod.building_loc_path.exists():
    loc_before = mod.building_loc_path.read_text(encoding=localization.ENCODING)
    plan = buildings.plan_edit(mod, {"line": line.name, "levels": [
        level_payload(target, loc={"name": "Test Barracks of Testing",
                                   "descr": "A long description.",
                                   "descr_short": "A short one."})]})
    check("the rename is a change", any("Test Barracks" in c for c in plan.changes))
    check("the localisation file would be rewritten", bool(plan.loc_text))
    check("the EDB is NOT touched by a rename alone", not plan.edb_text)
    parsed = localization.parse_text(plan.loc_text, descr_suffix="_desc")
    entry = parsed.get(target.name)
    check("name written", entry and entry.name == "Test Barracks of Testing")
    check("description written", entry and entry.descr == "A long description.")
    check("short description written", entry and entry.descr_short == "A short one.")
    rec = buildings.apply_edit(plan)
    check("the localisation file was backed up",
          buildings.LOC_REL in rec["manifest"]["backed_up"])
    undo(rec["id"])
    check("undo restores the localisation file",
          mod.building_loc_path.read_text(encoding=localization.ENCODING) == loc_before)
else:
    print("  [skip] this mod has no text/export_buildings.txt")

# ---- 6b) per-culture names ---------------------------------------------------
# A level is named once for everyone ({stables}) and again for each culture
# ({stables_northern_european}). Mods that use the per-culture keys leave the
# shared one as a placeholder equal to its own key, and reading only that key is
# what made every building in DaC show its code name instead of its name.
print("\n6b) per-culture names")
mod = Mod(work)
if mod.building_loc_path.exists() and mod.cultures:
    culture = mod.cultures[0]
    recs = buildings._loc_all(mod, target.name)
    check("every culture has a slot, plus the shared key",
          set(recs) == set([""] + list(mod.cultures)))
    check("each slot names the key it writes",
          recs[culture]["key"] == target.name + "_" + culture and recs[""]["key"] == target.name)
    check("a key equal to its own name is not a name",
          buildings._placeholder("stables", "stables")
          and not buildings._placeholder("stables", "Stables"))

    loc_before = mod.building_loc_path.read_text(encoding=localization.ENCODING)
    other = mod.cultures[-1]
    plan = buildings.plan_edit(mod, {"line": line.name, "levels": [
        level_payload(target, loc_cultures={culture: {
            "name": "Culture Barracks", "descr": "Only for one culture.",
            "descr_short": "One culture."}})]})
    check("a per-culture rename is a change",
          any("Culture Barracks" in c for c in plan.changes))
    parsed = localization.parse_text(plan.loc_text, descr_suffix="_desc")
    entry = parsed.get(target.name + "_" + culture)
    check("it lands on the culture's own key", entry and entry.name == "Culture Barracks")
    check("the shared key is left alone",
          (parsed.get(target.name) or localization.LocEntry()).name
          == (mod.building_loc.get(target.name) or localization.LocEntry()).name)
    if other != culture:
        was = mod.building_loc.get(target.name + "_" + other)
        now = parsed.get(target.name + "_" + other)
        check("another culture's key is left alone",
              (was is None and now is None)
              or (was and now and was.name == now.name))

    # the name a level SHOWS falls through the same way the game reads it
    best = buildings._best_loc(mod, target.name, culture)
    check("the label prefers the culture being looked at, when it has one",
          best["culture"] == culture if recs[culture]["present"]
          and not buildings._placeholder(recs[culture]["key"], recs[culture]["name"])
          else True)
    check("_label never returns an empty string",
          bool(buildings._label(mod, target.name, "", culture)))
    check("planning alone wrote nothing",
          mod.building_loc_path.read_text(encoding=localization.ENCODING) == loc_before)
else:
    print("  [skip] this mod has no building localisation or no culture folders")

# ---- 7) the payloads the UI reads ------------------------------------------
print("\n7) UI payloads")
mod = Mod(work)
ov = buildings.overview(mod)
check("overview lists every line", len(ov["lines"]) == len(mod.edb.buildings))
check("overview carries the capability vocabulary", len(ov["capabilities"]) > 20)
check("every line has a settlement kind",
      all(l["settlement"] in ("city", "castle", "both") for l in ov["lines"]))
d = buildings.detail(mod, line.name)
check("detail has one entry per level", len(d["levels"]) == len(line.blocks))
check("detail carries every culture's text, so the editor never re-asks",
      all(set(lv["loc_all"]) == set([""] + list(mod.cultures)) for lv in d["levels"]))
check("detail says which culture each label came from",
      all(lv["loc_culture"] in lv["loc_all"] for lv in d["levels"]))
check("detail resolves the units its pools name",
      all(u.get("type") for u in d["units"].values()))
check("detail is JSON-serialisable", bool(json.dumps(d)))
try:
    buildings.detail(mod, "no such building line")
    check("an unknown line raises", False)
except KeyError:
    check("an unknown line raises", True)

# ---- 7b) the recruitment limit ----------------------------------------------
# M2TW's recruitment panel holds RECRUIT_LIMIT units per building; past it the
# panel overflows and the game can crash on opening the settlement. The check
# reports two numbers, and the difference between them is the whole point:
# `always` is what a faction gets with no condition at all, `most` assumes every
# other condition holds at once.
print("\n7b) the recruitment limit")
fc = mod.faction_cultures
check("the limit is carried to the UI", ov["recruit_limit"] == buildings.RECRUIT_LIMIT)
check("every level reports its pressure",
      all("recruit_pressure" in lv for lv in d["levels"]))
check("a reported faction is over the limit on one number or the other",
      all(r["most"] > r["limit"] or r["always"] > r["limit"]
          for lv in d["levels"] for r in lv["recruit_pressure"]))
check("`always` is never more than `most`",
      all(r["always"] <= r["most"]
          for lv in d["levels"] for r in lv["recruit_pressure"]))

# an unconditional pool counts towards both numbers; a gated one only towards `most`
check("a clause naming only factions is not 'gated'",
      not buildings._is_gated("factions { england, }")
      and buildings._is_gated("factions { england, } and hidden_resource X"))
check("no factions clause means every faction",
      buildings._pool_factions("", fc) == set(fc))
check("`all` means every faction too",
      buildings._pool_factions("factions { all, }", fc) == set(fc))
if fc:
    one = sorted(fc)[0]
    culture = fc[one]
    check("a culture expands to the factions in it",
          buildings._pool_factions("factions { %s, }" % culture, fc)
          == {f for f, c in fc.items() if c == culture})
    check("a named faction expands to itself",
          buildings._pool_factions("factions { %s, }" % one, fc) == {one})

# the same check runs at save time, against the payload rather than the file
over = next(((bl, blk) for bl in edb.buildings for blk in bl.blocks
             if buildings.recruitment_pressure(blk, fc)), (None, None))
if over[0] is not None:
    p = buildings.plan_edit(mod, {"line": over[0].name,
                                  "levels": [level_payload(over[1])]})
    check("saving a level that is over the limit warns about it",
          any("recruitment panel" in w or "limit" in w for w in p.warnings))
    check("…and the warning does not stop the save",
          not p.errors)
else:
    print("  [skip] no level in this mod is over the limit")

# ---- 8) requires clauses, as structure -------------------------------------
print("\n8) requires clauses")
CLAUSES = [
    "factions { gondor, northern_european, } and hidden_resource unlocked",
    "factions { portugal, }  and region_religion catholic 75 and not hidden_resource GondorEast",
    "not event_counter civil_war 1 and region_religion nomadic 15",
    "factions { sicily, } and building_present_min_level masons_lodge north_lodge"
    " or building_present_min_level masons_lodge south_lodge",
    "resource silk",
    "woe_unlock_siege.",                    # malformed, and in a real mod
    "",
]
for clause in CLAUSES:
    conds = buildings.parse_clause(clause)
    back = buildings.clause_text(conds)
    check(f"round-trips: {clause[:44] or '(empty)'!r}",
          " ".join(back.split()) == " ".join(clause.split()))
check("`not` is parsed off the term, not into it",
      buildings.parse_clause("not hidden_resource x")[0].negate)
check("a malformed term is kept verbatim as raw",
      buildings.parse_clause("woe_unlock_siege.")[0].kind == "raw")
check("a keyword with the wrong argument count stays raw",
      buildings.parse_clause("event_counter only_one_arg")[0].kind == "raw")
check("an `and` inside a faction list can't split the clause",
      len(buildings.parse_clause("factions { and, or, } and resource silk")) == 2)

# every clause in every installed mod
for name in installed:
    m2 = Mod(MODS / name)
    if not m2.edb_path.exists():
        continue
    clauses = []
    for bl in m2.edb.buildings:
        for b in bl.blocks:
            clauses.append(b.requires)
            clauses += [c.requires for c in b.capabilities + b.faction_capabilities]
    bad = [c for c in clauses if c
           and " ".join(buildings.clause_text(buildings.parse_clause(c)).split())
           != " ".join(c.split())]
    check(f"{name}: {len(clauses)} clauses, {len(bad)} not byte-identical",
          len(bad) < len(clauses) / 100)
    # Every difference must be the parser TIDYING, never losing: emitting again
    # is a fixed point, and the same factions come back out.
    unstable = [c for c in bad
                if buildings.clause_text(buildings.parse_clause(
                    buildings.clause_text(buildings.parse_clause(c))))
                != buildings.clause_text(buildings.parse_clause(c))]
    check(f"{name}: every tidied clause is a fixed point", not unstable)
    lossy = [c for c in bad
             if set(buildings.clause_factions(c))
             != set(buildings.clause_factions(
                 buildings.clause_text(buildings.parse_clause(c))))]
    check(f"{name}: no faction is lost by tidying", not lossy)

# ---- 9) structured edits go through plan_edit -------------------------------
print("\n9) editing a clause structurally")
mod = Mod(work)
edb = mod.edb
line2 = next(bl for bl in edb.buildings if any(b.recruits for b in bl.blocks))
blk2 = next(b for b in line2.blocks if b.recruits)
conds = [{"join": "", "negate": False, "kind": "factions",
          "values": ["england", "venice"], "values_raw": ""},
         {"join": "and", "negate": True, "kind": "hidden_resource",
          "values": ["nowhere"]}]
plan = buildings.plan_edit(mod, {"line": line2.name, "levels": [
    {"name": blk2.name, "conditions": conds, "scalars": dict(blk2.scalars),
     "upgrades": list(blk2.upgrades), "settlement": blk2.settlement}]})
check("a structured clause is written as text",
      "factions { england, venice, } and not hidden_resource nowhere"
      in "\n".join(plan.changes))
reparsed = buildings.parse_text(plan.edb_text).get(line2.name).level(blk2.name)
check("…and reads back the same", buildings.clause_factions(reparsed.requires)
      == ["england", "venice"])
check("sending the SAME clause as text is not a change",
      not buildings.plan_edit(mod, {"line": line2.name, "levels": [
          {"name": blk2.name, "requires": blk2.requires}]}).changes)

# ---- 10) ownership: the check and the fix -----------------------------------
print("\n10) unit ownership")
pool = blk2.recruits[0]
unit = next((u for u in mod.edu.units if u.type.lower() == pool.unit.lower()), None)
if unit is None:
    print("  [skip] the first pool names a unit this mod's EDU doesn't have")
else:
    outsider = next(f for f in mod.faction_cultures
                    if f not in unit.ownership and f != "slave")
    rows = buildings.ownership_report(mod, [{"unit": unit.type,
                                             "factions": [outsider]}])
    check("a faction the unit doesn't belong to is reported",
          rows[0]["missing_ownership"] == [outsider])
    check("one it does belong to is not",
          not buildings.ownership_report(
              mod, [{"unit": unit.type, "factions": [unit.ownership[0]]}]
          )[0]["missing_ownership"])
    check("an unknown unit is flagged rather than silently ignored",
          not buildings.ownership_report(mod, [{"unit": "no such unit",
                                                "factions": ["england"]}])[0]["known"])
    culture = next((c for c in set(mod.faction_cultures.values())), "")
    check("a culture expands to its factions",
          set(buildings._expand_factions(mod, [culture]))
          == {f for f, c in mod.faction_cultures.items()
              if c == culture and f != "slave"})
    check("`all` expands to every faction",
          len(buildings._expand_factions(mod, ["all"]))
          == len([f for f in mod.faction_cultures if f != "slave"]))

    # the fix, through a real plan
    caps = [{"line": c.line, "keyword": c.keyword, "args": c.args,
             "requires": c.requires, "delete": False} for c in blk2.capabilities]
    for c in caps:
        if c["keyword"] == "recruit_pool" and pool.unit in c["args"]:
            c["conditions"] = [{"join": "", "negate": False, "kind": "factions",
                                "values": [outsider]}]
    body = {"line": line2.name, "fix_ownership": True, "levels": [
        {"name": blk2.name, "scalars": dict(blk2.scalars),
         "upgrades": list(blk2.upgrades), "settlement": blk2.settlement,
         "requires": blk2.requires, "capabilities": caps}]}
    plan = buildings.plan_edit(mod, body)
    check("the plan says it will extend ownership",
          any("ownership +=" in c for c in plan.changes))
    check("the EDU would be rewritten", bool(plan.edu_text))
    before_edu = mod.edu_path.read_bytes()
    rec = buildings.apply_edit(plan)
    after = Mod(work)
    fixed = next(u for u in after.edu.units if u.type == unit.type)
    check("the faction is now in the unit's ownership", outsider in fixed.ownership)
    check("its existing ownership is untouched",
          all(f in fixed.ownership for f in unit.ownership))
    check("the EDU was backed up",
          "export_descr_unit.txt" in rec["manifest"]["backed_up"])
    undo(rec["id"])
    check("undo restores the EDU byte-for-byte",
          mod.edu_path.read_bytes() == before_edu)

    # and the opt-out
    plan = buildings.plan_edit(mod, dict(body, fix_ownership=False))
    check("without fix_ownership the EDU is left alone", not plan.edu_text)

# ---- 11) building art, and the any-culture sweep ----------------------------
# A mod draws each level for the cultures that build it and no others: DaC's
# `ancestral_dun` exists only under northern_european. The building browser is
# showing ONE culture on purpose and gets a placeholder for the rest, but the
# unit editor's Recruitment tab is showing pools from every line in the mod and
# has no culture to be right about - so it asks for the sweep (`&any=1`).
print("\n11) building icons: the any-culture fallback")

art = Path(_tmp.mkdtemp(prefix="ut_art_"))


class _ArtMod:
    """Just enough of a Mod for find_icon: where data/ lives, and its cultures."""
    def __init__(self, root):
        self.data = root / "data"
        self.cultures = ["northern_european", "mesoamerican"]


am = _ArtMod(art)
for culture, level in (("northern_european", "ancestral_dun"),
                       ("northern_european", "shared_level"),
                       ("mesoamerican", "shared_level")):
    d = am.data / "ui" / culture / "buildings"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{buildings.icon_stem(culture, level)}.tga").write_bytes(b"\0" * 64)

hit, src = buildings.find_icon(am, "mesoamerican", "ancestral_dun", "small", None)
check("without the sweep, a level this culture has no art for is a placeholder",
      hit is None and src == "")
hit, src = buildings.find_icon(am, "mesoamerican", "ancestral_dun", "small", None,
                               any_culture=True)
check("with it, the one culture that draws the level supplies the art",
      hit is not None and src == "mod"
      and hit.name.lower() == "#northern_european_ancestral_dun.tga")
hit, src = buildings.find_icon(am, "mesoamerican", "shared_level", "small", None,
                               any_culture=True)
check("the culture's OWN art still wins when it has any",
      hit is not None and hit.name.lower() == "#mesoamerican_shared_level.tga")
hit, src = buildings.find_icon(am, "mesoamerican", "no_such_level", "small", None,
                               any_culture=True)
check("a level no culture draws is still a placeholder", hit is None and src == "")

shutil.rmtree(art, ignore_errors=True)


# ---------------------------------------------------------------------------
print("\n12) Phase 44: the tree's rules, one fixture each")

# Written out by hand rather than through `new_tree_text`, which always chains
# every level into the next - it cannot produce the faults these rules are for.
TREE_HEAD = "building %s\n{\n%s    levels %s\n"


def edb_of(*blocks: str) -> "buildings.EdbFile":
    return buildings.parse_text("".join(blocks))


def block(name, levels, convert_to="", requires="factions { greek, }",
          upgrades=None, cost="600", construction="2", extra_req=""):
    """One `building … { … }` block, with exactly the shape a rule wants.

    The nesting is the file's own and is not optional: the level blocks live
    inside a brace of their OWN after the `levels` line, not at the top level of
    the building. A fixture that got that wrong parsed as a line with no levels
    at all, which is how this helper was first written and what four of the
    rules below appeared to fail on.
    """
    up = upgrades if upgrades is not None else {
        levels[i]: [levels[i + 1]] for i in range(len(levels) - 1)}
    out = [f"building {name}\n{{\n"]
    if convert_to:
        out.append(f"    convert_to {convert_to}\n")
    out.append(f"    levels {' '.join(levels)}\n    {{\n")
    for lv in levels:
        req = requires + (" " + extra_req if extra_req else "")
        out.append(f"        {lv} city requires {req}\n        {{\n")
        out.append("            capability\n            {\n            }\n")
        out.append(f"            construction {construction}\n")
        out.append(f"            cost {cost}\n")
        out.append("            upgrades\n            {\n")
        for u in up.get(lv, []):
            out.append(f"                {u}\n")
        out.append("            }\n        }\n")
    out.append("    }\n}\n")
    return "".join(out)


def codes(edb, line=""):
    return [f["code"] for f in buildings.tree_check(edb, line)["findings"]]


# -- the five that resolve or do not -----------------------------------------
e = edb_of(block("forge", ["a", "b"]), block("forge", ["c", "d"]))
check("a building name used twice is fatal", codes(e).count("tree.name_twice") == 1)
check("  and it is the SECOND block that is reported, not the first",
      buildings.tree_check(e)["findings"][0]["line"] > 1)

e = edb_of("building empty\n{\n    levels\n}\n")
check("a line with no levels is fatal", "tree.no_levels" in codes(e))

e = edb_of(block("forge", ["a", "b"], upgrades={"a": ["ghost"]}))
check("an upgrades entry naming nothing is fatal", "tree.upgrade_unknown" in codes(e))

e = edb_of(block("forge", ["a", "b"], upgrades={"a": ["b requires event_counter x 1"]}))
check("  and a clause on that entry is NOT a finding (upgrade_name is used)",
      "tree.upgrade_unknown" not in codes(e))

e = edb_of(block("forge", ["a", "b"], convert_to="nowhere"))
check("a convert_to naming nothing is fatal", "tree.convert_unknown" in codes(e))
e = edb_of(block("forge", ["a", "b"], convert_to="other"), block("other", ["c"]))
check("  and one that resolves is not", "tree.convert_unknown" not in codes(e))

e = edb_of(block("forge", ["a", "b"], extra_req="and building_present_min_level nope a"))
check("a building_present_min_level naming no LINE is fatal",
      "tree.min_level_unknown" in codes(e))
e = edb_of(block("forge", ["a", "b"], extra_req="and building_present_min_level other zz"),
           block("other", ["c"]))
check("  …and one naming no LEVEL on a real line is too",
      "tree.min_level_unknown" in codes(e))
e = edb_of(block("forge", ["a", "b"], extra_req="and building_present_min_level other c"),
           block("other", ["c"]))
check("  …and one that resolves both halves is not",
      "tree.min_level_unknown" not in codes(e))

# -- the reshaped one --------------------------------------------------------
e = edb_of(block("alts", ["a", "b", "c"], upgrades={}))
check("a line of ALTERNATIVES reports nothing - 'reachable' means nothing on it",
      "tree.second_entry" not in codes(e))
e = edb_of(block("chain", ["a", "b", "c"], upgrades={"a": ["b"]}))
check("a chain with a second way in is a note, not an error",
      codes(e) == ["tree.second_entry"]
      and buildings.tree_check(e)["findings"][0]["severity"] == "note")

# -- the three measured ones -------------------------------------------------
e = edb_of(block("forge", ["a"], cost="0"))
check("cost 0 is a warning", "tree.free_level" in codes(e))
e = edb_of(block("forge", ["a"], construction="0"))
check("construction 0 is a warning", "tree.instant_level" in codes(e))
e = edb_of(block("forge", ["a"], requires="hidden_resource gold"))
check("a level with no factions clause is a warning", "tree.no_factions" in codes(e))

# -- the shape of the answer -------------------------------------------------
t = buildings.tree_check(edb_of(block("forge", ["a", "b"])))
check("a clean file reports nothing", not t["findings"])
check("  and still lists its rules, so a silent validator is not a missing one",
      len(t["rules"]) == len(buildings.EDB_RULES) == 9)
check("  and the three refusals travel with it", len(t["refused"]) == 3)
check("every rule has a source", all(r["source"] for r in t["rules"]))
check("every severity is one mapcheck knows",
      {r["severity"] for r in t["rules"]} <= {"fatal", "warn", "note"})

e = edb_of(block("forge", ["a"], cost="0", construction="0"),
           block("other", ["c"], convert_to="nope"))
check("`line` narrows the findings to one building",
      {f["building"] for f in buildings.tree_check(e, "forge")["findings"]} == {"forge"})
check("findings are ordered fatal, then warn, then note",
      [f["severity"] for f in buildings.tree_check(e)["findings"]]
      == sorted([f["severity"] for f in buildings.tree_check(e)["findings"]],
                key=lambda s: {"fatal": 0, "warn": 1, "note": 2}[s]))

# -- against the real files, which is what decided three of the rules ---------
print("\n12b) the same rules over every installed EDB")
for _root in _realmod.installed():
    _p = Path(_root) / "data" / "export_descr_buildings.txt"
    if not _p.exists():
        print(f"  -- {_root.name}: no EDB")
        continue
    _t = buildings.tree_check(buildings.parse_file(_p))
    _c = _t["counts"]
    print(f"  -- {_root.name}: {_c['fatal']} fatal, {_c['warn']} warn, "
          f"{_c['note']} note")
    check(f"    {_root.name}: a shipping mod has no FATAL tree finding",
          _c["fatal"] == 0)

# ---------------------------------------------------------------------------
print("\n13) Phase 51: the list's order is the file's order")


def cap_ops(blk, order=None):
    caps = blk.capabilities
    order = order if order is not None else range(len(caps))
    return [{"line": caps[k].line, "keyword": caps[k].keyword,
             "args": " ".join(caps[k].args.split()), "requires": caps[k].requires,
             "delete": False} for k in order]


# a level with at least three capability lines, on the real mod
_lvl = next((bl, b) for bl in edb.buildings for b in bl.blocks if len(b.capabilities) >= 3)
_line, _blk = _lvl
o, c = _blk.cap_span
before = original.splitlines(keepends=True)
n = len(_blk.capabilities)
swapped = [1, 0] + list(range(2, n))
plan = buildings.plan_edit(mod, {"line": _line.name,
                                 "levels": [level_payload(_blk, capabilities=cap_ops(_blk, swapped))]})
after = plan.edb_text.splitlines(keepends=True)
check("swapping the first two capabilities is a change", bool(plan.edb_text))
check("  the file keeps its length", len(after) == len(before))
check("  nothing outside the capability block moved",
      after[:o + 1] == before[:o + 1] and after[c:] == before[c:])
check("  the block's inside is the same lines, byte for byte, reordered",
      sorted(after[o + 1:c]) == sorted(before[o + 1:c]))
_a, _b = _blk.capabilities[0].line, _blk.capabilities[1].line
check("  the second line now comes first",
      after.index(before[_b], o) < after.index(before[_a], o))
check("  and the plan says the order changed",
      any("order changed" in x for x in plan.changes))

# the file's own order with a new row at the END keeps the old append path
ops = cap_ops(_blk) + [{"line": None, "keyword": "law_bonus", "args": "bonus 1",
                        "requires": "", "delete": False}]
plan = buildings.plan_edit(mod, {"line": _line.name,
                                 "levels": [level_payload(_blk, capabilities=ops)]})
after = plan.edb_text.splitlines(keepends=True)
check("a new row at the end goes in above the closing brace, as before",
      after[c].strip() == "law_bonus bonus 1" and after[c + 1] == before[c])
check("  and every existing line is untouched", after[o + 1:c] == before[o + 1:c])
check("  and it is not reported as a reorder",
      not any("order changed" in x for x in plan.changes))

# a new row inserted after the first line lands there
ops = cap_ops(_blk)
ops.insert(1, {"line": None, "keyword": "law_bonus", "args": "bonus 1",
               "requires": "", "delete": False})
plan = buildings.plan_edit(mod, {"line": _line.name,
                                 "levels": [level_payload(_blk, capabilities=ops)]})
after = plan.edb_text.splitlines(keepends=True)
_first = after.index(before[_blk.capabilities[0].line], o)
check("a row inserted below the first lands directly under it",
      after[_first + 1].strip() == "law_bonus bonus 1")
check("  and the rest follow in the file's order, byte for byte",
      after[_first + 2:c + 1] == before[_first + 1:c])

# comments ride with the line under them; the closing remark stays at the bottom
fx = ("building forge\n{\n    levels a\n    {\n        a city requires factions { greek, }\n"
      "        {\n            capability\n            {\n"
      "                ;; the Gondor pools\n"
      "                recruit_pool \"Gondor Spearmen\"  1  0.1  2  0  ; kept\n"
      "                law_bonus bonus 1\n"
      "                ;; end of list\n"
      "            }\n            cost 1\n            construction 1\n        }\n    }\n}\n")
fe = buildings.parse_text(fx)
fb = fe.buildings[0].blocks[0]
notes, warn = [], []
ed = buildings._plan_capabilities(fe, fb, [
    {"line": fb.capabilities[1].line, "keyword": "law_bonus", "args": "bonus 1",
     "requires": "", "delete": False},
    {"line": fb.capabilities[0].line, "keyword": "recruit_pool",
     "args": fb.capabilities[0].args, "requires": "", "delete": False}],
    notes, warn, faction=False)
out = buildings.splice(fe.lines, ed).splitlines()
_i = out.index("                ;; the Gondor pools")
check("a comment above a moved line moves with it",
      out[_i + 1].startswith("                recruit_pool") and out[_i - 1].strip() == "law_bonus bonus 1")
check("  the moved line keeps its trailing comment byte for byte",
      out[_i + 1] == "                recruit_pool \"Gondor Spearmen\"  1  0.1  2  0  ; kept")
check("  the closing remark stays at the bottom",
      out[out.index("                ;; end of list") + 1].strip() == "}")
check("  and nothing was warned about", not warn)

# ---------------------------------------------------------------------------
print("\n13b) Phase 51: every gate at once, run in node against the page's own code")

import subprocess
import tempfile

GATE_HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ctx = {console, state: {}, document: {}, window: {}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = job.cases.map(k => {
  const g = ctx.bldGateEval(k.conds, job.regions[k.set]);
  return g ? {pass: g.pass.map(r => r.region), assumed: g.assumed.length} : null;
});
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""

_node = shutil.which("node")
if not _node:
    print("  -- node is not on PATH, so the gate evaluation is not run")
else:
    from unittransfer import edbvocab

    def reg(name, hidden=(), res=(), fac="f1"):
        return {"region": name, "name": name, "settlement": name, "faction": fac,
                "hidden_resources": list(hidden), "resources": list(res)}

    synth = [reg("A", hidden=["x", "z"]), reg("B", hidden=["y"]), reg("C", hidden=["x"])]
    cases, want = [], []

    def case(clause, expect, set_="synth"):
        cases.append({"set": set_, "conds": buildings.clause_payload(clause)})
        want.append(expect)

    case("hidden_resource x and hidden_resource y", [])
    case("hidden_resource x and hidden_resource z", ["A"])
    case("hidden_resource x or hidden_resource y", ["A", "B", "C"])
    case("not hidden_resource x", ["B"])
    # (x or y) and z, left to right; precedence would give x or (y and z) = A, C
    case("hidden_resource x or hidden_resource y and hidden_resource z", ["A"])
    case("factions { f9, } and hidden_resource x", ["A", "C"])
    case("factions { f9, }", None)

    # the real mods: every clause that is only `and`s and positive resource
    # terms has an answer a plain set intersection gives, so check the page's
    # evaluator against that on every such clause in each installed EDB
    real_regions = {}
    for _root in _realmod.installed():
        _m = Mod(_root)
        if not _m.edb_path.exists():
            continue
        _v = edbvocab.build(_m)
        real_regions[_root.name] = _v["regions"]
        if _root.name == "Divide_and_Conquer_EUR":
            # trade resources are placed by descr_strat.txt, not descr_regions:
            # DaC puts chocolate in two provinces and the regions file in none.
            # (ROCSS needs M2EX to read its 449 regions, which this throwaway
            # config does not mark, so its map - and this join - is skipped here.)
            _choc = [r["region"] for r in _v["regions"]
                     if "chocolate" in [x.lower() for x in r["resources"]]]
            check("a trade resource placed by descr_strat.txt is in its province's row "
                  f"(chocolate: {len(_choc)})", len(_choc) >= 1)
        _edb = buildings.parse_file(_m.edb_path)
        seen = set()
        for _bl in _edb.buildings:
            for _b in _bl.blocks:
                for _c in _b.capabilities + _b.faction_capabilities:
                    if not _c.requires or _c.requires in seen:
                        continue
                    conds = buildings.clause_payload(_c.requires)
                    rterms = [k for k in conds if k["kind"] in ("hidden_resource", "resource")]
                    if not rterms or any(k["join"] == "or" or k["negate"] for k in rterms) \
                            or any(k["join"] == "or" for k in conds):
                        continue
                    seen.add(_c.requires)
                    ok_regions = []
                    for r in _v["regions"]:
                        have = {x.lower() for x in r["hidden_resources"] + r["resources"]}
                        if all(k["values"][0].lower() in have for k in rterms):
                            ok_regions.append(r["region"])
                    cases.append({"set": _root.name, "conds": conds})
                    want.append(ok_regions)

    job = {"regions": dict(synth=synth, **real_regions), "cases": cases}
    with tempfile.TemporaryDirectory(prefix="ut_gate_") as tmp:
        t = Path(tmp)
        (t / "h.js").write_text(GATE_HARNESS, encoding="utf-8")
        (t / "job.json").write_text(json.dumps(job), encoding="utf-8")
        r = subprocess.run([_node, str(t / "h.js"), str(ROOT / "web" / "js" / "buildings.js"),
                            str(t / "job.json"), str(t / "out.json")],
                           capture_output=True, text=True)
        check("the harness runs", r.returncode == 0)
        got = json.loads((t / "out.json").read_text(encoding="utf-8")) if not r.returncode else []
        if r.returncode:
            print(r.stderr[-600:])

    labels = ["x and y overlap nowhere, and says so",
              "x and z is the one region carrying both",
              "x or y is any region with either",
              "not x is the regions without it",
              "left to right: (x or y) and z, not x or (y and z)",
              "a factions term does not narrow, it is assumed",
              "a clause with no resource term has no summary"]
    for i, lab in enumerate(labels):
        g = got[i] if i < len(got) else "missing"
        exp = want[i]
        check(lab, (g is None) if exp is None else (g is not None and sorted(g["pass"]) == sorted(exp)))
    check("  and the factions term is reported as assumed",
          len(got) > 5 and got[5] and got[5]["assumed"] == 1)
    real = list(zip(got[len(labels):], want[len(labels):]))
    bad = [w for g, w in real if not g or sorted(g["pass"]) != sorted(w)]
    empty = sum(1 for g, w in real if g and not g["pass"])
    print(f"  -- {len(real)} real clauses with resource gates, {empty} that no region passes")
    check("every real and-only resource clause matches a plain intersection", real and not bad)

# ---------------------------------------------------------------------------
print("\n14) Phase 45: the hidden_resources line")
from unittransfer import edbvocab                                     # noqa: E402

_reg = src_root / "data" / edbvocab.REGIONS_REL
(work / "data" / edbvocab.REGIONS_REL).parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(_reg, work / "data" / edbvocab.REGIONS_REL)
mod = Mod(work)
before = mod.edb_path.read_text(encoding=buildings.ENCODING)
blines = before.splitlines(keepends=True)
hl = mod.edb.hidden_resources_line
names0 = list(mod.edb.hidden_resources)

plan = buildings.plan_hidden(mod, {"add": ["tk_probe_resource"]})
after = plan.edb_text.splitlines(keepends=True)
check("adding a name rewrites the one line and nothing else",
      not plan.errors and len(after) == len(blines)
      and [i for i, (a, b) in enumerate(zip(blines, after)) if a != b] == [hl])
check("  the name goes on the end, the rest in their order",
      after[hl].split(";")[0].split()[1:] == names0 + ["tk_probe_resource"])
check("  and the line keeps its own gap after the keyword",
      after[hl].startswith(blines[hl][:len(blines[hl]) - len(blines[hl].lstrip())]
                           + "hidden_resources" + re.match(r"hidden_resources(\s+)",
                                                            blines[hl].lstrip()).group(1)))
check("  the count is stated against the ceiling, and not enforced",
      plan.impact["count_after"] == len(names0) + 1 and "63 or 64" in plan.impact["ceiling_note"])
rec = buildings.apply_edit(plan)
mod = Mod(work)
check("apply writes it", "tk_probe_resource" in mod.edb.hidden_resources)
undo(rec["id"])
check("and Undo puts the file back byte for byte",
      mod.edb_path.read_text(encoding=buildings.ENCODING) == before)

mod = Mod(work)
used = max(buildings.hidden_usage(mod), key=lambda x: x["clauses"])
imp = buildings.hidden_impact(mod, used["name"])
raw = sum(1 for i, l in enumerate(blines) if i != hl and re.search(
    r"\bhidden_resource\s+" + re.escape(used["name"]) + r"\b", buildings._code(l), re.I))
check(f"a removal names every clause that gates on it ({used['name']}: {len(imp['clauses'])})",
      len(imp["clauses"]) == raw == used["clauses"])
check(f"  and every province that carries it ({len(imp['provinces'])})",
      len(imp["provinces"]) == used["provinces"] > 0)
plan = buildings.plan_hidden(mod, {"remove": [used["name"]]})
check("removing a name still in use is refused until acknowledged",
      plan.errors and not plan.edb_text and "acknowledge" in plan.errors[0])
plan = buildings.plan_hidden(mod, {"remove": [used["name"]],
                                   "acknowledged": [used["name"].upper()]})
after = plan.edb_text.splitlines(keepends=True)
check("  and once acknowledged, it comes off the line and nothing else changes",
      not plan.errors and used["name"] not in after[hl].split()
      and [i for i, (a, b) in enumerate(zip(blines, after)) if a != b] == [hl])

p2 = buildings.plan_hidden(mod, {"add": [names0[0].lower()]})
check("a name already on the line is refused, whatever its case", bool(p2.errors))
p2 = buildings.plan_hidden(mod, {"add": ["two words"]})
check("a name the line cannot hold is refused", bool(p2.errors))
p2 = buildings.plan_hidden(mod, {"remove": ["not_a_resource_here"]})
check("removing a name that is not there is refused", bool(p2.errors))

check("the line's comment and its own separators survive a rewrite",
      buildings._hidden_line("\thidden_resources a\tb ; keep\n", ["a", "b", "c"])
      == "\thidden_resources a\tb\tc ; keep\n")
fx = buildings.parse_text("; header\r\nbuilding forge\r\n{\r\n    levels a\r\n    {\r\n    }\r\n}\r\n")


class _M:
    edb = fx
    data = work / "data"


p3 = buildings.plan_hidden(_M(), {"add": ["iron_hills"]})
check("an EDB with no line gets one, above the first building",
      p3.edb_text.startswith("; header\r\nhidden_resources iron_hills\r\n\r\nbuilding forge"))

shutil.rmtree(work.parent, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
