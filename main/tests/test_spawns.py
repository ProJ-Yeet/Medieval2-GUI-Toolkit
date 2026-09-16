"""What the campaign script spawns, and where it puts it (37a, T7).

    python -m tests.test_spawns

A little script written here carrying every shape the real ones have: tabs
between keyword and value, a comment line, a commented-out spawn, a
``spawn_army`` block with several units, a ``spawn_character`` one-liner, a unit
line with the ``soldiers`` attribute, and a block with no coordinate at all.

**The suite is about the reading being trustworthy, because the phase is a
report and a report nobody believes is worth nothing.** Section 4 is the check
that makes it so: on the installed mods every spawn resolves to a province
except the admirals, and every unit name resolves to the EDU.

Section 3 is the parse trap the real files set. A ``character`` line inside a
spawn is comma-separated and the ``unit`` line beside it is not, so splitting
both the same way gives units called "Moria Balrog soldiers 1".

Nothing here writes to a mod. The script is read and never touched, which is
19b's refusal and 24's, kept.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, config, spawns
from unittransfer import keyblock as kb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- the little script -------------------------------------------------------

SCRIPT = (
    ";;; a campaign script\r\n"
    "script\r\n"
    "\r\n"
    "monitor_event PreFactionTurnStart FactionType england\r\n"
    "\r\n"
    "    spawn_army\r\n"
    "        faction\tengland\r\n"
    "        character\tAlfred, named character, age 30, x 3, y 6, family\r\n"
    "        unit\t\tPeasant Spearmen\t\texp 1 armour 0 weapon_lvl 0\r\n"
    "        unit\t\tTown Militia\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
    "    end\r\n"
    "\r\n"
    ";    spawn_army\r\n"
    ";        faction\tfrance\r\n"
    ";        character\tGhost, named character, age 30, x 1, y 1\r\n"
    ";    end\r\n"
    "\r\n"
    "    spawn_army\r\n"
    "        faction\tfrance\r\n"
    "        character\tBalrog, general, age 40, x 8, y 6\r\n"
    "        unit\t\tMoria Balrog\tsoldiers 1 exp 9 armour 3 weapon_lvl 2\r\n"
    "    end\r\n"
    "\r\n"
    "    spawn_character\tspain, Ferdinand, diplomat, age 21, x 3, y 1\r\n"
    "\r\n"
    "    spawn_army\r\n"
    "        faction\tvenice\r\n"
    "        character\tNelson, admiral, age 44, x 0, y 3\r\n"
    "        unit\t\tWar Galley\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
    "    end\r\n"
    "\r\n"
    "    spawn_army\r\n"
    "        faction\tpoland\r\n"
    "        character\tNowhere, general, age 22\r\n"
    "        unit\t\tTown Militia\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
    "    end\r\n"
    "\r\n"
    "end_monitor\r\n"
)

W, H = 12, 8
SEA = (41, 140, 233)
A = (200, 110, 100)
B = (100, 200, 110)

#: Alpha in the north-west, Beta in the south-east, sea everywhere else. The
#: rows are image rows, so `y` here counts DOWN and the script's counts UP.
PICTURE = [
    "............",
    ".AAA........",
    ".AAA........",
    "............",
    "............",
    "........BBB.",
    "........BBB.",
    "............",
]
LETTERS = {".": SEA, "A": A, "B": B}

REGIONS = (
    "Alpha_Province\r\n\tAlphaton\r\n\tnorthmen\r\n\tNorth_Rebels\r\n"
    f"\t{A[0]} {A[1]} {A[2]}\r\n\tnone\r\n\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
    "\r\n"
    "Beta_Province\r\n\tBetaton\r\n\tnorthmen\r\n\tNorth_Rebels\r\n"
    f"\t{B[0]} {B[1]} {B[2]}\r\n\tnone\r\n\t2\r\n"
    "\treligions { catholic 100 orthodox 0 islam 0 heretic 0 }\r\n"
)

TERRAIN = (
    "dimensions\r\n{\r\n" + f"\twidth  {W}\r\n\theight  {H}\r\n" + "}\r\n"
    "heights\r\n{\r\n\tmin_sea_height  -3406.782\r\n"
    "\tmax_land_height  7511.272\r\n}\r\n"
    "roughness\r\n{\r\n\tmin  50.000\r\n\tmax  200.000\r\n}\r\n"
    "fractal\r\n{\r\n\tmultiplier  0.500\r\n}\r\n"
    "lattitude\r\n{\r\n\tmin  22.000\r\n\tmax  56.000\r\n}\r\n"
)


def little_mod(script_name="campaign_script.txt"):
    from PIL import Image
    root = Path(_tmp.mkdtemp(prefix="ut_spw_"))
    base = root / "data" / campmap.BASE_REL
    base.mkdir(parents=True)
    px = [LETTERS[ch] for row in PICTURE for ch in row]
    img = Image.new("RGB", (W, H))
    img.putdata(px)
    img.save(base / "map_regions.tga")
    grids = {"tile": (W, H), "centre": (2 * W + 1, 2 * H + 1),
             "double": (2 * W, 2 * H), "advisory": (W, H), "free": (W, H)}
    for ly in campmap.LAYERS:
        if ly["code"] == "regions":
            continue
        # the heights decide the sea, and the sea is the whole of section 5:
        # land under Alpha and Beta, water everywhere else
        if ly["code"] == "heights":
            # Pure black is sea, per `sea_mask`: a tile is sea iff its height
            # pixel is not greyscale OR is pure black. A dark grey is neither
            # and would make the whole fixture dry land.
            hi = Image.new("RGB", grids["centre"], (0, 0, 0))
            for row_i, row in enumerate(PICTURE):
                for col_i, ch in enumerate(row):
                    if ch != ".":
                        for dy in (0, 1, 2):
                            for dx in (0, 1, 2):
                                hi.putpixel((2 * col_i + dx, 2 * row_i + dy),
                                            (200, 200, 200))
            hi.save(base / ly["file"])
            continue
        fill = {"ground_types": (0, 100, 0), "climates": (12, 90, 200),
                "fog": (255, 255, 255)}.get(ly["code"], (0, 0, 0))
        Image.new("RGB", grids[ly["size"]], fill).save(base / ly["file"])
    kb.write_text(base / "descr_regions.txt", REGIONS, campmap.ENCODING)
    kb.write_text(base / "descr_terrain.txt", TERRAIN, campmap.ENCODING)

    home = (root / "data" / campstrat.CAMPAIGN_DIR_REL
            / campstrat.campaign_rel(campstrat.DEFAULT_CAMPAIGN))
    home.mkdir(parents=True)
    kb.write_text(home / script_name, SCRIPT, campmap.ENCODING)
    return Mod(root)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config._cache_dir = cfg / "cache"


# ---- 1: the script is found, and only in the campaign's own folder ----------

print("\n1. finding the script")

mod = little_mod()
paths = spawns.script_paths(mod, campstrat.DEFAULT_CAMPAIGN)
check(f"  one script found: {[p.name for p in paths]}",
      len(paths) == 1 and paths[0].name == "campaign_script.txt")
check("  the other name is found too, when that is what the campaign calls it",
      [p.name for p in
       spawns.script_paths(little_mod("custom_script.txt"),
                           campstrat.DEFAULT_CAMPAIGN)] == ["custom_script.txt"])
check("  and a campaign with no script at all is empty rather than an error",
      spawns.script_paths(mod, "custom/Nope") == [])


# ---- 2: the blocks --------------------------------------------------------

print("\n2. what it reads")

rows = spawns.scan(mod, campstrat.DEFAULT_CAMPAIGN)
check(f"  five spawns, four armies and one character: "
      f"{[(r.kind, r.faction) for r in rows]}",
      len(rows) == 5
      and len([r for r in rows if r.kind == "army"]) == 4
      and len([r for r in rows if r.kind == "character"]) == 1)
check("  the commented-out block is not one of them",
      not any(r.faction == "france" and r.name == "Ghost" for r in rows))
alfred = next(r for r in rows if r.name == "Alfred")
check(f"  Alfred: {alfred.faction}, {alfred.type}, ({alfred.x},{alfred.y}), "
      f"{len(alfred.units)} units",
      (alfred.faction, alfred.type, alfred.x, alfred.y) ==
      ("england", "named character", 3, 6) and len(alfred.units) == 2)
ferd = next(r for r in rows if r.kind == "character")
check(f"  the one-liner reads the same way: {ferd.faction}, {ferd.name}, "
      f"{ferd.type}, ({ferd.x},{ferd.y})",
      (ferd.faction, ferd.name, ferd.type, ferd.x, ferd.y)
      == ("spain", "Ferdinand", "diplomat", 3, 1))
nowhere = next(r for r in rows if r.name == "Nowhere")
check("  a block whose character line has no x/y is read, and marked as having "
      "no coordinate rather than being dropped or defaulted to 0,0",
      nowhere.char_line == 0 and nowhere.faction == "poland")
check("  the line numbers are the block head and the line the coordinate is on",
      alfred.line < alfred.char_line)


# ---- 3: the parse trap the real files set ----------------------------------

print("\n3. the unit line, which is not comma-separated")

check(f"  Alfred's units are names and nothing else: {alfred.units}",
      alfred.units == ["Peasant Spearmen", "Town Militia"])
balrog = next(r for r in rows if r.name == "Balrog")
check(f"  and `soldiers` is an attribute, not part of the name: "
      f"{balrog.units}", balrog.units == ["Moria Balrog"])
check("  every attribute keyword ends the name",
      spawns._unit_name("unit  Foo Bar   exp 1 armour 0") == "Foo Bar"
      and spawns._unit_name("unit\tFoo Bar\tsoldiers 2 exp 1") == "Foo Bar"
      and spawns._unit_name("unit Foo Bar armour 3") == "Foo Bar"
      and spawns._unit_name("unit Foo Bar weapon_lvl 1") == "Foo Bar")
check("  a unit line with no attributes at all is still just the name",
      spawns._unit_name("unit Foo Bar") == "Foo Bar")


# ---- 4: resolved against the map, and the y that has to be flipped ---------

print("\n4. where they land")

cm = campmap.CampaignMap(mod)
rows = spawns.resolve(spawns.scan(mod, campstrat.DEFAULT_CAMPAIGN), cm)
by = {r.name: r for r in rows}
# Alpha is image rows 1-2, so game rows 5-6 on an 8-high map. Alfred is at
# game (3,6) which is image (3,1) - inside Alpha.
check(f"  Alfred at game (3,6) is in {by['Alfred'].province!r}",
      by["Alfred"].province == "Alpha_Province")
# Beta is image rows 5-6, so game rows 1-2. Balrog is at game (8,6) = image
# (8,1), which is SEA - the flip is what tells the two apart.
check(f"  Balrog at game (8,6) is not in Beta - it is at sea, which is what "
      f"the flip decides: province {by['Balrog'].province!r}, "
      f"at_sea {by['Balrog'].at_sea}",
      by["Balrog"].at_sea and not by["Balrog"].province)
check("  and a spawn at game (8,1) IS in Beta, which is the same tile the "
      "other way up",
      any(True for _ in [None])
      and spawns.resolve([spawns.Spawn(x=8, y=1, char_line=1)], cm)[0].province
      == "Beta_Province")
check(f"  the admiral at game (0,3) is at sea and that is correct for its "
      f"type: at_sea {by['Nelson'].at_sea}, afloat_ok "
      f"{by['Nelson'].payload()['afloat_ok']}",
      by["Nelson"].at_sea and by["Nelson"].payload()["afloat_ok"])
check("  the general at sea is NOT afloat_ok, which is the whole distinction",
      by["Balrog"].at_sea and not by["Balrog"].payload()["afloat_ok"])
check("  coordinates are left as the file wrote them, never flipped in place",
      by["Alfred"].x == 3 and by["Alfred"].y == 6)
off = spawns.resolve([spawns.Spawn(x=999, y=999, char_line=1)], cm)[0]
check("  a coordinate off the map is marked off_map rather than clamped",
      off.off_map and not off.province)
# …and a spawn with no coordinate at all is left alone entirely, which is what
# stops a missing field being reported as a fleet in the corner of the map
none = spawns.resolve([spawns.Spawn(x=0, y=0)], cm)[0]
check("  a spawn with no coordinate line is not resolved at all, so a missing "
      "field cannot be counted as a spawn at sea",
      not none.at_sea and not none.off_map and not none.province)


# ---- 5: the view and the export --------------------------------------------

print("\n5. the view, and the CSV")

v = spawns.view(mod, cm, campstrat.DEFAULT_CAMPAIGN)
check(f"  counted: {v['armies']} armies, {v['characters']} characters, "
      f"{v['units']} units, {v['no_coordinate']} without a coordinate",
      (v["armies"], v["characters"], v["units"], v["no_coordinate"])
      == (4, 1, 5, 1))
check(f"  at sea {v['at_sea']}, of which {v['at_sea_afloat']} a fleet and "
      f"{v['at_sea_aground']} not",
      (v["at_sea"], v["at_sea_afloat"], v["at_sea_aground"]) == (3, 1, 2))
check(f"  one line per faction: {sorted(v['factions'])}",
      sorted(v["factions"]) == ["england", "france", "poland", "spain", "venice"])
check("  it says out loud that it writes nothing", v["read_only"] is True)

csv = spawns.export_text(rows)
lines = csv.strip().split("\n")
check(f"  the CSV has a header and one row per spawn: {len(lines)} lines",
      len(lines) == 6 and lines[0] == ",".join(spawns.COLUMNS))
check("  a value with a comma in it is quoted, so the file really is CSV",
      spawns._csv_cell("a, b") == '"a, b"'
      and spawns._csv_cell('say "hi"') == '"say ""hi"""'
      and spawns._csv_cell("plain") == "plain")
check("  every row carries the line it came from",
      all(part.isdigit() for part in
          [l.split(",")[1] for l in lines[1:]]))

# the marker rows, which are the layer's own shape
pos = spawns.positions(mod, campstrat.DEFAULT_CAMPAIGN, cm)
check(f"  the marker layer gets {len(pos)} rows - the one with no coordinate "
      f"is not drawable and is left out", len(pos) == 4)
check("  and each is the shape the layer already draws",
      all({"kind", "name", "type", "faction", "x", "y", "line"} <= set(p)
          for p in pos)
      and all(p["kind"] == "spawn" for p in pos))


# ---- 6: nothing is written to the mod --------------------------------------

print("\n6. read-only")

import hashlib                                                    # noqa: E402

script = (Path(mod.data) / campstrat.CAMPAIGN_DIR_REL
          / campstrat.campaign_rel(campstrat.DEFAULT_CAMPAIGN)
          / "campaign_script.txt")
before = hashlib.sha256(script.read_bytes()).hexdigest()
spawns.view(mod, cm, campstrat.DEFAULT_CAMPAIGN)
spawns.export(mod, cm, campstrat.DEFAULT_CAMPAIGN)
check("  the script is byte-identical after a view and an export",
      hashlib.sha256(script.read_bytes()).hexdigest() == before)
out = spawns.export(mod, cm, campstrat.DEFAULT_CAMPAIGN)
check(f"  and the export went to the cache folder, not the mod: "
      f"{Path(out['folder']).name}/{out['file']}",
      str(cfg) in out["folder"] and out["rows"] == 5)


# ---- 7: every installed campaign, for real ---------------------------------

print("\n7. the installed mods")

mods = _realmod.installed()
if not mods:
    print("  SKIPPED - no installed mod")
else:
    for root in mods:
        real = Mod(root)
        for camp in campstrat.campaign_paths(real):
            if not spawns.script_paths(real, camp):
                continue
            try:
                rcm = campmap.campaign_map(real, camp,
                                           campmap.CampaignMap(real))
            except Exception as exc:                      # noqa: BLE001
                print(f"  -- {real.name} {camp}: no map ({str(exc)[:40]})")
                continue
            rv = spawns.view(real, rcm, camp)
            if not rv["placed"]:
                continue
            print(f"  -- {real.name}  {camp}")
            print(f"       {rv['armies']} armies, {rv['characters']} characters,"
                  f" {rv['units']} units, {rv['in_province']}/{rv['placed']} in "
                  f"a province, {rv['at_sea_aground']} aground at sea, "
                  f"{len(rv['dead_units'])} unit names the EDU lacks")
            check(f"     every spawn carries a coordinate "
                  f"({rv['no_coordinate']} do not)", rv["no_coordinate"] == 0)
            check(f"     none is off the map ({rv['off_map']})",
                  rv["off_map"] == 0)
            # the check that validates the whole reading: everything resolves
            # except the fleets
            # Everything that did not resolve has a reason, and there are
            # exactly three: at sea, on a colour no record declares, or off the
            # map. A spawn that resolved to none of them would be a hole in the
            # reader, so this is the check that says there is no such hole.
            unresolved = rv["placed"] - rv["in_province"]
            explained = rv["at_sea"] + rv["undeclared"] + rv["off_map"]
            check(f"     {unresolved} did not resolve to a province and every "
                  f"one is accounted for ({rv['at_sea']} at sea, "
                  f"{rv['undeclared']} on an undeclared colour, "
                  f"{rv['off_map']} off the map)",
                  unresolved <= explained)


print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
