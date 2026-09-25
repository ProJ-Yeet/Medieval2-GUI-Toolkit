"""Phase 67: descr_area_effects.xml.

    python -m tests.test_areaeffects

1. Both installed mods, as measured: each has one projectile naming an area
   effect the file never declares (ROCSS's ae_fearcommand_arrow, DaC's
   ae_poison_javelin), the one warning in each; CA's ae_medium_fire named
   where an effect set goes a note in both; ROCSS's nahptha_fire_set a note
   because ROCSS leaves the file that declares it to the base game, DaC's not
   a finding because DaC ships it; `horizontal` not a finding.
2. The rules on a fixture: a set member that is no area effect, a projectile
   type that is no projectile, a colour past 255, alpha and force ranges
   upside down, a number that is not one, a name twice, an unknown type, an
   effect set a mod that ships every effect file lacks (with the near miss it
   probably meant), a tag closed out of order.
3. Saves on a temp copy of DaC's file: a value changed, an area effect copied
   under a new name, a set member added with its own delay and one removed, a
   field added; the rest of the file byte for byte; bad values refused; one
   Undo.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import areaeffects as ae  # noqa: E402
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
for path, name, ghost, n in ((ROC, "ROCSS", "ae_fearcommand_arrow", 55),
                             (DAC, "DaC", "ae_poison_javelin", 41)):
    if not (path / "data" / ae.REL).is_file():
        continue
    ov = ae.overview(Mod(path))
    fs = ov["findings"]
    warn = [f for f in fs if f["severity"] != "note"]
    check(f"{name}: {n} area effects in six types", len(ov["effects"]) == n
          and {e["type"] for e in ov["effects"]} == set(ae.TYPES))
    check(f"{name}: the one warning is the projectile naming {ghost}",
          len(warn) == 1 and warn[0]["code"] == "undeclared" and ghost in warn[0]["message"])
    check(f"{name}: ae_medium_fire named as an effect set is a note",
          any(f["code"] == "set_is_effect" and "ae_medium_fire" in f["message"] for f in fs))
    check(f"{name}: no `direction` finding (horizontal is one of them)", not any(f["code"] == "direction" for f in fs))
    used = {e["name"]: e for e in ov["effects"]}
    check(f"{name}: ae_holy_inspiration is named by the holy cart in descr_engines.txt",
          any(u["file"] == "descr_engines.txt" for u in used["ae_holy_inspiration"]["used"]))
    check(f"{name}: a set's members are counted as uses (ae_greek_fire_burn is in a set)",
          used["ae_greek_fire_burn"]["in_sets"])
    naph = [f for f in fs if "nahptha_fire_set" in f["message"]]
    if name == "ROCSS":
        check("ROCSS: nahptha_fire_set is a note, since ROCSS leaves descr_burning_building.txt to the base game",
              "descr_burning_building.txt" in ov["absent_effect_files"]
              and [f["code"] for f in naph] == ["set_absent"])
    else:
        check("DaC: nahptha_fire_set is no finding, since DaC ships the file that declares it", not naph)

print("\n2) the rules")
XML = """<?xml version="1.0"?>
<root>
   <area_effects>
      <area_effect>
         <name>ae_one</name>
         <type>nausea</type>
         <ground_effect>smok_set</ground_effect>
         <radius>ten</radius>
         <banner_colour><red>300</red><green>0</green><blue>0</blue></banner_colour>
         <banner_colour_alpha_min>160</banner_colour_alpha_min>
         <banner_colour_alpha_max>32</banner_colour_alpha_max>
      </area_effect>
      <area_effect>
         <name>AE_ONE</name>
         <type>lightning</type>
      </area_effect>
      <area_effect>
         <name>ae_split</name>
         <type>projectile</type>
         <projectile_type>no_such_shot</projectile_type>
         <explosion_force_min>3</explosion_force_min>
         <explosion_force_max>1</explosion_force_max>
         <preserve_momentum>maybe</preserve_momentum>
         <direction>sideways</direction>
      </area_effect>
      <area_effect>
         <name>aeset_x</name>
         <type>area_effect_set</type>
         <effect delay="0.2">ae_one</effect>
         <effect delay="soon">ae_missing</effect>
      </area_effect>
   </area_effects>
</root>
"""
refs = ae.Refs(uses={"ae_gone": [{"file": "descr_projectile.txt", "who": "gone_arrow", "line": 3,
                                  "name": "ae_gone"}]},
               projectiles={"arrow"}, sets={"smoke_set"}, absent=[])
fs = ae.check(ae.parse(XML), refs)
got = codes(fs)
check("a projectile naming an area effect the file lacks is a warning, naming the projectile",
      any(f["code"] == "undeclared" and "gone_arrow" in f["message"] for f in fs))
check("a set member that is no area effect is a warning; a delay that is no number fatal",
      ("member", "warn") in got and ("number", "fatal") in got)
check("a projectile type that is no projectile, and preserve_momentum not true or false, are warnings",
      ("projectile", "warn") in got and ("bool", "warn") in got)
check("a colour past 255, and alpha and force ranges upside down, are warnings",
      ("colour", "warn") in got and sum(1 for f in fs if f["code"] == "range") == 2)
check("a name twice and an unknown type are warnings", ("duplicate", "warn") in got and ("type", "warn") in got)
check("an unknown direction is a note", ("direction", "note") in got)
check("with every effect file shipped, a missing effect set is a warning naming the near miss",
      any(f["code"] == "set_missing" and f["severity"] == "warn" and "smoke_set" in f["message"] for f in fs))
refs.absent = ["descr_surface_fire.txt"]
check("...and a note while the mod leaves an effect file to the base game",
      ("set_absent", "note") in codes(ae.check(ae.parse(XML), refs)))
got = codes(ae.check(ae.parse("<root><area_effects><a></b></a></area_effects></root>")))
check("a tag closed out of order is fatal", ("xml", "fatal") in got)

print("\n3) saves, on a temp copy of DaC's file")
if not (DAC / "data" / ae.REL).is_file():
    print("  -- DaC is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_aef_")) / "AefMod"
    (root / "data").mkdir(parents=True)
    for rel in (ae.REL, "descr_projectile.txt"):
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    mod = Mod(root)
    before = (root / "data" / ae.REL).read_bytes()
    ov = ae.overview(mod)
    by = {e["name"]: e for e in ov["effects"]}
    cow, gset = by["ae_cow_carcass"], by["aeset_greek_fire"]
    radius = next(f for f in cow["fields"] if f["tag"] == "radius")
    red = next(f for f in cow["fields"] if f["path"] == "banner_colour/red")
    fire = by["ae_greek_fire_displacement"]
    lack = next(t for t in ae.TYPES["fire"] if t not in {f["tag"] for f in fire["fields"]})
    last = gset["members"][-1]
    body = {"sig": ov["sig"], "values": {str(radius["id"]): "12.5", str(red["id"]): "40"},
            "copy": [{"like": cow["id"], "name": "ae_poison_javelin"},
                     {"like": last["id"], "value": "ae_greek_fire_fear", "attrs": {"delay": "2.5"}}],
            "remove": [gset["members"][0]["id"]],
            "add_field": [{"parent": fire["id"], "tag": lack, "value": "1"}]}
    p = ae.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.text)
    res = ae.apply(p)
    ov2 = ae.overview(Mod(root))
    by2 = {e["name"]: e for e in ov2["effects"]}
    names = [e["name"] for e in ov2["effects"]]
    check("the radius and the red changed",
          next(f for f in by2["ae_cow_carcass"]["fields"] if f["tag"] == "radius")["value"] == "12.5"
          and next(f for f in by2["ae_cow_carcass"]["fields"] if f["path"] == "banner_colour/red")["value"] == "40")
    check("the copy is right after the cow, and declaring ae_poison_javelin clears DaC's one warning",
          names[names.index("ae_cow_carcass") + 1] == "ae_poison_javelin"
          and not any(f["code"] == "undeclared" for f in ov2["findings"]))
    m2 = by2["aeset_greek_fire"]["members"]
    check("the set lost its first member and gained ae_greek_fire_fear after 2.5 s, last",
          len(m2) == len(gset["members"]) and m2[-1]["name"] == "ae_greek_fire_fear" and m2[-1]["delay"] == "2.5"
          and m2[0]["id"] != gset["members"][0]["id"])
    check(f"ae_greek_fire_displacement gained its {lack}",
          any(f["tag"] == lack and f["value"] == "1" for f in by2["ae_greek_fire_displacement"]["fields"]))
    after = (root / "data" / ae.REL).read_bytes()
    head = before[:before.index(b"<name>ae_cow_carcass</name>")]
    check("everything above the first edit is byte for byte what it was", after.startswith(head))
    check("the tail of the file is byte for byte what it was", after.endswith(before[-300:]))
    stale = ae.plan(mod, dict(body, sig="0" * 16))
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    for label, bad in (("a colour past 255", {"values": {str(red["id"]): "400"}}),
                       ("a type that is not one of the six", {"values": {
                           str(next(f for f in by2["ae_cow_carcass"]["fields"] if f["tag"] == "type")["id"]): "lightning"}}),
                       ("a copy under a name already taken", {"copy": [{"like": cow["id"], "name": "AE_HIVE"}]}),
                       ("a field the type does not take", {"add_field": [
                           {"parent": by2["ae_cow_carcass"]["id"], "tag": "kill_damage", "value": "3"}]})):
        check(f"{label} is refused", ae.plan(mod, dict(bad, sig=ov2["sig"])).errors)
    gone = ae.plan(mod, {"sig": ov2["sig"], "remove": [by2["ae_poison_javelin"]["id"]]})
    check("removing an area effect a projectile names is allowed, and warned about",
          not gone.errors and any("ae_poison_javelin" in w for w in gone.warnings))
    transfer.undo(res["id"])
    check("one undo puts the file back byte for byte", (root / "data" / ae.REL).read_bytes() == before)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
