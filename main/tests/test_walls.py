"""Phase 68: descr_walls.txt.

    python -m tests.test_walls

1. Both installed mods, as measured: five wall levels and seven gates each,
   every gateway's gates declared, every tower level the EDB gives backed by
   enough firing levels, ROCSS's three empty shot_gfx lines the only finding,
   and every line read back as it was.
2. The rules on a fixture: a gate nobody declared, a stat line one field
   short, a projectile and a sound event the mod lacks, a fire_rate size
   missing, a number that is not one, a level written twice, the EDB giving a
   wall level no block has and a tower level its tower cannot fire, an
   unclosed brace.
3. Saves on a temp copy of DaC's file: a value changed keeping its column and
   comment, a gate type added and one removed, a firing level copied and one
   removed; the rest of the file byte for byte; a stale signature and bad
   values refused; one Undo.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer import walls as wl  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROC, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def codes(fs):
    return {(f["code"], f["severity"]) for f in fs}


print("\n1) the installed mods")
for path, name in ((ROC, "ROCSS"), (DAC, "DaC")):
    if not (path / "data" / wl.REL).is_file():
        continue
    ov = wl.overview(Mod(path))
    check(f"{name}: wall levels 0 to 4 and seven gates", [w["level"] for w in ov["walls"]] == [0, 1, 2, 3, 4]
          and len(ov["gates"]) == 7)
    check(f"{name}: every level has its wall, gateway and tower",
          all({"wall", "gateway", "tower"} <= {p["kind"] for p in w["parts"]} for w in ov["walls"]))
    fs = ov["findings"]
    if name == "ROCSS":
        check("ROCSS: the only findings are its three shot_gfx lines with no value, as notes",
              [(f["code"], f["severity"]) for f in fs] == [("gfx", "note")] * 3)
    else:
        check("DaC: no finding at all", not fs)
    text = (path / "data" / wl.REL).read_bytes().decode("latin-1")
    check(f"{name}: every line read back as it was", "\n".join(wl.parse(text).lines) == text)
    pairs = wl.edb_pairs(path / "data")
    check(f"{name}: the EDB's wall levels are all in the file ({sorted({k[0] for k in pairs if k[0] is not None})})",
          {k[0] for k in pairs if k[0] is not None} <= {0, 1, 2, 3, 4})
if (DAC / "data" / wl.REL).is_file():
    ov = wl.overview(Mod(DAC))
    w1 = next(w for w in ov["walls"] if w["level"] == 1)
    tower = next(p for p in w1["parts"] if p["kind"] == "tower")
    check("DaC: wall 1 is given with tower_level 2, and its tower has two firing levels",
          w1["tower_levels"] == [2] and len(tower["firing"]) == 2)

print("\n2) the rules")
FIX = """gates
{
	gate  short_wooden
	{
		full_health x
	}
}
wall
{
	level 0
	wall
	{
		full_health 250
	}
	gateway
	{
		full_health 120
		short_wooden
		iron_door
	}
	tower
	{
		full_health 120
		level
		{
			stat		12, 0, tower_arrow, 160, 100, missile, missile_mechanical, piercing, arrow_tower, 10
			shot_sfx	NO_SUCH_SOUND
			fire_rate small  4000	   3000
			fire_rate normal 3500	   3000
		}
		level
		{
			stat		12, 0, no_shot, 160, 100, missile, missile_mechanical, piercing, laser_tower, 10, 1
			fire_rate small  4000	   3000
			fire_rate normal 3500	   3000
			fire_rate large  3000	   3000
			fire_rate huge   2500	   3000
		}
	}
}
wall
{
	level 0
	wall
	{
		full_health 250
	}
}
"""
refs = wl.Refs(projectiles={"tower_arrow"}, events={"tower_arrow_firing"}, sets=set(),
               edb_pairs={(0, 3): ["tower_upgrade"], (2, None): ["big_walls"]})
fs = wl.check(wl.parse(FIX), refs)
got = codes(fs)
check("a gate the gates block does not declare is a warning", ("gate", "warn") in got)
check("a stat line one field short is fatal; a projectile the mod lacks a warning",
      ("stat", "fatal") in got and ("projectile", "warn") in got)
check("a sound event descr_sounds_generic.txt lacks is a warning, an unknown tower sound a note",
      ("sfx", "warn") in got and ("sound", "note") in got)
check("a firing level missing its large and huge fire_rate is a warning", ("fire_rate", "warn") in got)
check("a number that is not one is fatal", ("number", "fatal") in got)
check("a wall level written twice is a warning, and so is a level with no gateway or tower",
      ("level", "warn") in got and ("part", "warn") in got)
check("the EDB giving wall_level 2 is a warning when no block has it",
      any(f["code"] == "edb_wall" and "big_walls" in f["message"] for f in fs))
check("...and tower_level 3 on a wall whose tower fires two levels",
      any(f["code"] == "edb_tower" and "tower_upgrade" in f["message"] for f in fs))
check("an unclosed brace is fatal", ("braces", "fatal") in codes(wl.check(wl.parse("wall\n{\n\tlevel 0\n"))))

print("\n3) saves, on a temp copy of DaC's file")
if not (DAC / "data" / wl.REL).is_file():
    print("  -- DaC is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_walls_")) / "WallMod"
    (root / "data").mkdir(parents=True)
    for rel in (wl.REL, "descr_projectile.txt", "descr_sounds_generic.txt"):
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    mod = Mod(root)
    before = (root / "data" / wl.REL).read_bytes()
    ov = wl.overview(mod)
    w3 = next(w for w in ov["walls"] if w["level"] == 3)
    wall = next(p for p in w3["parts"] if p["kind"] == "wall")
    gateway = next(p for p in w3["parts"] if p["kind"] == "gateway")
    tower = next(p for p in w3["parts"] if p["kind"] == "tower")
    health = next(r for r in wall["rows"] if r["key"] == "full_health")
    w0 = next(w for w in ov["walls"] if w["level"] == 0)
    g0 = next(p for p in w0["parts"] if p["kind"] == "gateway")
    body = {"sig": ov["sig"], "values": {str(health["line"]): "2400"},
            "add_gate": [{"gateway": g0["line"], "gate": "medium_wooden"}],
            "remove": [gateway["gates"][-1]["line"], tower["firing"][-1]["line"]],
            "copy_firing": [tower["firing"][0]["line"]]}
    p = wl.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.text)
    res = wl.apply(p)
    ov2 = wl.overview(Mod(root))
    w3b = next(w for w in ov2["walls"] if w["level"] == 3)
    t3b = next(p for p in w3b["parts"] if p["kind"] == "tower")
    check("the health changed, and the line kept its tabs",
          next(r for r in next(p for p in w3b["parts"] if p["kind"] == "wall")["rows"]
               if r["key"] == "full_health")["value"] == "2400"
          and "\t\tfull_health 2400" in (root / "data" / wl.REL).read_text(encoding="latin-1"))
    check("wall 0's gateway carries medium_wooden too, and wall 3's lost its last gate type",
          [g["gate"] for g in next(p for p in next(w for w in ov2["walls"] if w["level"] == 0)["parts"]
                                   if p["kind"] == "gateway")["gates"]] == ["short_wooden", "medium_wooden"]
          and len(next(p for p in w3b["parts"] if p["kind"] == "gateway")["gates"]) == len(gateway["gates"]) - 1)
    check("the tower's first firing level was copied and its last removed: still three, the first twice",
          len(t3b["firing"]) == 3 and t3b["firing"][0]["rows"] == [dict(r, line=r["line"]) for r in t3b["firing"][0]["rows"]]
          and [r["value"] for r in t3b["firing"][1]["rows"]] == [r["value"] for r in t3b["firing"][0]["rows"]])
    after = (root / "data" / wl.REL).read_bytes()
    head = before[:before.index(b"; SHORT WOODEN WALLS")]
    check("everything above the first edit is byte for byte what it was", after.startswith(head))
    check("the saved file is still clean", not ov2["findings"])
    stale = wl.plan(mod, dict(body, sig="0" * 16))
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    for label, bad in (("a health that is not a number", {"values": {str(health["line"]): "lots"}}),
                       ("a stat line one field short", {"values": {
                           str(next(r for r in t3b["firing"][0]["rows"] if r["key"] == "stat")["line"]):
                               "15, 0, tower_arrow, 180, 100, missile, missile_mechanical, piercing, arrow_tower, 10"}}),
                       ("a gate type nobody declared", {"add_gate": [{"gateway": g0["line"], "gate": "iron_door"}]}),
                       ("removing the only firing level of wall 0's tower", {"remove": [
                           next(p for p in next(w for w in ov2["walls"] if w["level"] == 0)["parts"]
                                if p["kind"] == "tower")["firing"][0]["line"]]})):
        check(f"{label} is refused", wl.plan(mod, dict(bad, sig=ov2["sig"])).errors)
    transfer.undo(res["id"])
    check("one undo puts the file back byte for byte", (root / "data" / wl.REL).read_bytes() == before)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
