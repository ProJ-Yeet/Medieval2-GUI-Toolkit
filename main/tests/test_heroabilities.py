"""Phase 66: descr_hero_abilities.xml.

    python -m tests.test_heroabilities

1. Both installed mods, as measured: ROCSS's sprite given twice the one
   warning, its unused abilities' missing labels and its effect oddities
   notes; DaC's 32 abilities with one note; every ability a character names
   declared, and who names each one counted.
2. The rules on a fixture: a character naming an undeclared ability, a name
   twice, an unknown effect and target, a number that is not one, a label,
   sprite and sound the mod lacks (warning when the ability is given, note
   when not), a tag closed out of order.
3. Saves on a temp copy of DaC's file: a value changed, an ability copied
   under a new name, an effect copied into another ability, a field removed
   and, in a second save, added back; the rest of the file byte for byte; a stale signature and a
   bad value refused; each save one Undo.
4. The people panel: the picker offers the declared abilities, and a
   character naming one the file lacks is a warning.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import heroabilities as ha  # noqa: E402
from unittransfer import leafxml as lx  # noqa: E402
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
if (ROC / "data" / ha.REL).is_file():
    ov = ha.overview(Mod(ROC))
    bad = sorted(f["code"] for f in ov["findings"] if f["severity"] != "note")
    check("ROCSS: seven abilities", len(ov["abilities"]) == 7)
    check("ROCSS: The_Heart_of_the_Lion's second <selected_sprite> is the one warning", bad == ["twice"]
          and "The_Heart_of_the_Lion" in next(f for f in ov["findings"] if f["code"] == "twice")["message"])
    notes = sorted(f["code"] for f in ov["findings"] if f["severity"] == "note")
    check("ROCSS: two unused abilities' labels, a stray permanent and a negative kill chance are notes",
          notes == ["effect_field", "kill_chance", "label", "label"])
    check("ROCSS: the banana bomb's projectile effect is known, and its projectile exists",
          not any(f["code"] in ("effect", "projectile") for f in ov["findings"]))
    used = {a["name"]: a["used_count"] for a in ov["abilities"]}
    check("ROCSS: Byzantine_Politics is given three times, Light_of_the_Faith never",
          used["Byzantine_Politics"] == 3 and used["Light_of_the_Faith"] == 0)
    check("ROCSS ships no battle.sd, so no sprite is called missing", not ov["have"]["battle_sd"]
          and not any(f["code"] == "sprite" for f in ov["findings"]))
if (DAC / "data" / ha.REL).is_file():
    ov = ha.overview(Mod(DAC))
    check("DaC: 32 abilities, 1,187 lines", len(ov["abilities"]) == 32
          and (DAC / "data" / ha.REL).read_text(encoding="latin-1").count("\n") + 1 == 1187)
    check("DaC: one note (NUMENOR's army_morale is given permanent) and nothing else",
          [(f["code"], f["severity"]) for f in ov["findings"]] == [("effect_field", "note")])
    check("DaC: every character's ability is declared", not any(f["code"] == "undeclared" for f in ov["findings"]))
    check("DaC: battle.sd read, and all its button sprites are in it",
          ov["have"]["battle_sd"] and not any(f["code"] == "sprite" for f in ov["findings"]))
    check("DaC: the tooltip text is read back for a label",
          any(v for v in ov["labels"].values()))

print("\n2) the rules")
XML = """<?xml version="1.0"?>
<root>
  <hero_abilities>
    <hero_ability>
      <name>Given</name>
      <duration>x</duration>
      <activations>0</activations>
      <normal_tooltip_label>EMT_NOPE</normal_tooltip_label>
      <normal_sprite>NO_SPRITE</normal_sprite>
      <sound_effect>no_sound</sound_effect>
      <hero_ability_effects>
        <hero_ability_effect>
          <name>army_morale</name>
          <target>everyone</target>
          <morale_modifier>5</morale_modifier>
        </hero_ability_effect>
        <hero_ability_effect>
          <name>make_it_rain</name>
        </hero_ability_effect>
        <hero_ability_effect>
          <name>unit_infighting</name>
          <target>enemy_armies</target>
          <percentage_chance>150</percentage_chance>
          <min_effect_time>30</min_effect_time>
          <max_effect_time>10</max_effect_time>
        </hero_ability_effect>
      </hero_ability_effects>
    </hero_ability>
    <hero_ability>
      <name>given</name>
      <normal_tooltip_label>EMT_NOPE</normal_tooltip_label>
      <hero_ability_effects></hero_ability_effects>
    </hero_ability>
    <hero_ability>
      <name>Unused</name>
      <normal_tooltip_label>EMT_NOPE</normal_tooltip_label>
      <hero_ability_effects>
        <hero_ability_effect><name>lock_morale</name><target>own_army</target><morale_level>firm</morale_level></hero_ability_effect>
      </hero_ability_effects>
    </hero_ability>
  </hero_abilities>
</root>
"""
refs = ha.Refs(uses={"given": [{"file": "world/maps/campaign/imperial_campaign/descr_strat.txt", "line": 9,
                                "who": "Bob", "name": "Given"}],
                     "ghost": [{"file": "world/maps/campaign/imperial_campaign/descr_strat.txt", "line": 12,
                                "who": "Tim", "name": "Ghost"}]},
               text_keys={"EMT_YES"}, sprites=b"\x05yes_sprite", sounds={"a_sound"}, projectiles=set())
fs = ha.check(ha.parse(XML), refs)
got = codes(fs)
check("a character naming an ability the file lacks is a warning", ("undeclared", "warn") in got
      and any("Ghost" in f["message"] and "Tim" in f["message"] for f in fs if f["code"] == "undeclared"))
check("a name declared twice (in any case) is a warning", ("duplicate", "warn") in got)
check("a duration that is not a number is fatal, activations of 0 a warning",
      ("number", "fatal") in got and ("activations", "warn") in got)
check("on an ability a character has: a missing label, sprite and sound are warnings",
      {("label", "warn"), ("sprite", "warn"), ("sound", "warn")} <= got)
check("on an ability nobody has: the missing label is a note",
      any(f["code"] == "label" and f["severity"] == "note" and "Unused" in f["message"] for f in fs))
check("an unknown target and an unknown effect are warnings",
      ("target", "warn") in got and ("effect", "warn") in got)
check("a chance past 100 and a min above its max are warnings", ("percent", "warn") in got and ("range", "warn") in got)
check("an ability with no effects is a warning", ("no_effects", "warn") in got)
got = codes(ha.check(ha.parse("<root><hero_abilities><a></b></a></hero_abilities></root>")))
check("a tag closed out of order is fatal", ("xml", "fatal") in got)

print("\n3) saves, on a temp copy of DaC's file")
if not (DAC / "data" / ha.REL).is_file():
    print("  -- DaC is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_hab_")) / "HabMod"
    (root / "data").mkdir(parents=True)
    shutil.copy2(DAC / "data" / ha.REL, root / "data" / ha.REL)
    strat = "world/maps/campaign/imperial_campaign/descr_strat.txt"
    (root / "data" / strat).parent.mkdir(parents=True)
    shutil.copy2(DAC / "data" / strat, root / "data" / strat)
    mod = Mod(root)
    before = (root / "data" / ha.REL).read_bytes()
    ov = ha.overview(mod)
    by = {a["name"]: a for a in ov["abilities"]}
    iron, captain = by["IRON_FIST"], by["CAPTAIN"]
    dur = next(f for f in iron["fields"] if f["tag"] == "duration")
    cool = next((f for f in iron["fields"] if f["tag"] == "cooldown"), None)
    body = {"sig": ov["sig"], "values": {str(dur["id"]): "45"},
            "copy": [{"like": iron["id"], "name": "IRON_FIST_II"},
                     {"like": iron["effects"][0]["id"], "into": captain["effects_id"]}],
            "add_field": [] if cool else [{"parent": iron["id"], "tag": "cooldown", "value": "90"}],
            "remove": [cool["id"]] if cool else []}
    p = ha.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.text)
    res = ha.apply(p)
    ov2 = ha.overview(Mod(root))
    by2 = {a["name"]: a for a in ov2["abilities"]}
    names = [a["name"] for a in ov2["abilities"]]
    check("the duration changed", next(f for f in by2["IRON_FIST"]["fields"] if f["tag"] == "duration")["value"] == "45")
    check("the copy sits right after IRON_FIST, with IRON_FIST's effects",
          names[names.index("IRON_FIST") + 1] == "IRON_FIST_II"
          and [e["name"] for e in by2["IRON_FIST_II"]["effects"]] == [e["name"] for e in iron["effects"]])
    check("CAPTAIN gained IRON_FIST's first effect, last",
          len(by2["CAPTAIN"]["effects"]) == len(captain["effects"]) + 1
          and by2["CAPTAIN"]["effects"][-1]["name"] == iron["effects"][0]["name"])
    check("the cooldown " + ("went" if cool else "arrived"),
          any(f["tag"] == "cooldown" for f in by2["IRON_FIST"]["fields"]) != bool(cool))
    check("the saved file is still clean (no new finding above a note)",
          not [f for f in ov2["findings"] if f["severity"] != "note"])
    after = (root / "data" / ha.REL).read_bytes()
    head = before[:before.index(b"<name>IRON_FIST</name>")]
    check("everything above the first edit is byte for byte what it was", after.startswith(head))
    check("the tail of the file is byte for byte what it was", after.endswith(before[-400:]))
    stale = ha.plan(mod, dict(body, sig="0" * 16))
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    tgt = next(f for f in by2["IRON_FIST"]["effects"][0]["fields"] if f["tag"] == "target")
    bad = ha.plan(mod, {"sig": ov2["sig"], "values": {str(tgt["id"]): "everyone"}})
    check("a target that is not one of the three is refused", bad.errors)
    dup = ha.plan(mod, {"sig": ov2["sig"], "copy": [{"like": by2["CAPTAIN"]["id"], "name": "iron_fist"}]})
    check("a copy under a name already taken is refused", any("already" in e for e in dup.errors))
    gone = ha.plan(mod, {"sig": ov2["sig"], "remove": [by2["CAPTAIN"]["id"]]})
    check("removing an ability characters use is allowed, and warned about",
          not gone.errors and any("CAPTAIN" in w and "declares no ability" in w for w in gone.warnings))
    if cool:
        again = ha.plan(mod, {"sig": ov2["sig"], "add_field": [
            {"parent": by2["IRON_FIST"]["id"], "tag": "cooldown", "value": "75"}]})
        res2 = ha.apply(again)
        f3 = ha.overview(Mod(root))["abilities"]
        i3 = next(a for a in f3 if a["name"] == "IRON_FIST")
        box = next(ln for ln, t in enumerate((root / "data" / ha.REL).read_text(encoding="latin-1").splitlines(), 1)
                   if "<hero_ability_effects>" in t and ln > i3["line"])
        check("a second save gives it back a cooldown of 75, after its last field and above its effects",
              i3["fields"][-1]["tag"] == "cooldown" and i3["fields"][-1]["value"] == "75"
              and i3["fields"][-1]["line"] == box - 1)
        transfer.undo(res2["id"])
    transfer.undo(res["id"])
    check("undo puts the file back byte for byte", (root / "data" / ha.REL).read_bytes() == before)

print("\n4) the people panel")
if (ROC / "data" / ha.REL).is_file():
    from unittransfer import stratchar as sc

    class _Facts:
        mod = Mod(ROC)
        skipped = []

    voc = sc.Vocabulary.__new__(sc.Vocabulary)
    voc.facts = _Facts()
    voc.abilities, voc.portraits, voc.labels, voc.units, voc.file_units = [], [], [], {}, []

    class _SF:
        def of_kind(self, kind):
            return []

    voc._from_file(_SF())
    check("the picker offers what the file declares", {"Light_of_the_Faith", "Super_Banana_Bomb"} <= set(voc.abilities))
    for name, warn in (("Byzantine_Politics", False), ("byzantine_politics", False), ("Not_An_Ability", True)):
        spec = sc.Spec(name="X", type="named character", gender="male", age="30", x="1", y="1",
                    tail={"hero_ability": name})
        voc.have_edct = voc.have_eda = False
        fs = [f for f in sc.check_character(voc, spec) if f["code"] == "char.ability"]
        check(f"{name}: " + ("a warning" if warn else "declared, no finding"), bool(fs) == warn
              and all(not f["fatal"] for f in fs))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
