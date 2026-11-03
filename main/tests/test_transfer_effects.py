"""A missile unit's projectile effects, carried across on request and on M2EX.

Run:  python -m tests.test_transfer_effects

A made-up install: the base game's data/ lists two effect files in its
descr_effects.txt and ships one of them; the source mod declares the sets its
arrow fires; the destination leaves every effect file to the base game. What
has to hold:

* a destination not marked M2EX still blanks the sets by default, and says so;
* with *Bring the effects anyway* the sets come across, with a warning that
  names the plain engine's limit;
* a file the destination left to the base game is written from the base's own
  copy first, so the base's sets are kept above the new one;
* a file the destination's manifest does not load is added to it, the manifest
  started from the base's;
* the projectile's lines point at the real sets, and Undo takes it all back.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import effects, projectiles, transfer         # noqa: E402
from unittransfer.mod import Mod                                 # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


MODELDB = "22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n"
UNIT = ("type             Fire Archers\ndictionary       Fire_Archers\ncategory         infantry\n"
        "class            missile\nvoice_type       Light\nsoldier          none, 20, 0, 1\n"
        "stat_pri         5, 2, fire_arrow, 120, 30, missile, archery, piercing, none, 25, 1\n"
        "ownership        egypt\n")
PROJ = ("projectile fire_arrow\n\neffect                     fire_trail_set\n"
        "end_effect                 fire_burst_set\ndamage      0\nvelocity    30 50\n")


def set_text(name, effect):
    return f"effect_set {name}\n{{\n\tlod 1000\n\t{{\n\t\t{effect}\n\t}}\n}}\n\n"


def effect_text(name):
    return f"effect {name}\n{{\n\ttype ribbon\n\t{{\n\t}}\n}}\n\n"


game = Path(_tmp.mkdtemp(prefix="ut_fx_")) / "Game"
(game / "data").mkdir(parents=True)
(game / "data" / "descr_effects.txt").write_text(
    "descr_trails.txt\ndescr_bursts.txt\n", encoding="latin-1")
BASE_TRAILS = set_text("base_trail_set", "base_trail") + effect_text("base_trail")
(game / "data" / "descr_trails.txt").write_text(BASE_TRAILS, encoding="latin-1")
(game / "data" / "descr_bursts.txt").write_text(set_text("base_burst_set", "base_burst")
                                               + effect_text("base_burst"), encoding="latin-1")


def mod(name, files):
    data = game / "mods" / name / "data"
    (data / "unit_models").mkdir(parents=True)
    (data / "unit_models" / "battle_models.modeldb").write_text(MODELDB, encoding="latin-1")
    (data / "text").mkdir()
    (data / "text" / "export_units.txt").write_text(
        "{Fire_Archers}Fire Archers\n{Fire_Archers_descr}d\n{Fire_Archers_descr_short}s\n", encoding="utf-16")
    for rel, text in files.items():
        (data / rel).write_text(text, encoding="latin-1")
    return Mod(data.parent)


src = mod("Src", {
    "export_descr_unit.txt": UNIT,
    "descr_projectile.txt": PROJ,
    # the source loads a third file the base game does not list
    "descr_effects.txt": "descr_trails.txt\ndescr_bursts.txt\ndescr_fire.txt\n",
    "descr_trails.txt": BASE_TRAILS + set_text("fire_trail_set", "fire_trail") + effect_text("fire_trail"),
    "descr_fire.txt": set_text("fire_burst_set", "fire_burst") + effect_text("fire_burst"),
})


def fresh(name):
    return mod(name, {"export_descr_unit.txt": "type             Spearmen\ndictionary       Spearmen\n"
                                               "category         infantry\nclass            spearmen\n"
                                               "voice_type       Light\nownership        egypt\n",
                      "descr_projectile.txt": ""})


print("\n1) a plain destination, by default")
dst = fresh("Plain")
plan = transfer.plan_transfer(src, "Fire Archers", dst, transfer.TransferOptions())
check("no effect is brought", not plan.effect_blocks)
check("  both lines blanked", plan.projectile_effects_blanked == 2)
check("  and it says so", any("NOT imported" in w for w in plan.warnings))

print("\n2) the same, with Bring the effects anyway")
plan = transfer.plan_transfer(src, "Fire Archers", dst, transfer.TransferOptions(import_effects=True))
added = {n.lower() for n, a, _ in plan.effect_actions if a == "add"}
check("both sets come across", added == {"fire_trail_set", "fire_burst_set"})
check("  none blanked", plan.projectile_effects_blanked == 0)
check("  with the plain engine's warning", any("PLAIN ENGINE" in w for w in plan.warnings))
check("the trails file is seeded from the base game's copy",
      plan.effect_seeds.get("descr_trails.txt", "").replace("\\", "/").endswith("Game/data/descr_trails.txt"))
check("the fire file is added to the manifest, the manifest seeded from the base's",
      plan.effect_manifest_adds == ["descr_fire.txt"] and "descr_effects.txt" in plan.effect_seeds)
check("the bursts file is not touched", "descr_bursts.txt" not in plan.effect_seeds)

rec = transfer.apply_transfer(plan)
after = Mod(dst.root)
trails = (dst.data / "descr_trails.txt").read_text(encoding="latin-1")
check("the destination's trails file keeps the base's set, above the new one",
      trails.startswith(BASE_TRAILS.rstrip("\n")) and "fire_trail_set" in trails)
manifest = effects._listed(dst.data / "descr_effects.txt")
check("its manifest is the base's with the fire file added",
      manifest == ["descr_trails.txt", "descr_bursts.txt", "descr_fire.txt"])
check("it declares every set now, the base's too",
      {"fire_trail_set", "fire_burst_set", "base_trail_set", "base_burst_set"} <= set(after.effect_sets))
written = projectiles.parse_file(dst.data / "descr_projectile.txt").get("fire_arrow")
check("the projectile names the real sets",
      written is not None and written.effects.get("effect") == "fire_trail_set"
      and written.effects.get("end_effect") == "fire_burst_set")

transfer.undo(rec["id"])
check("Undo takes the three files away again",
      not any((dst.data / f).exists() for f in ("descr_trails.txt", "descr_fire.txt", "descr_effects.txt")))

print("\n3) an M2EX destination brings them without being asked")
m2 = fresh("Ex")
from unittransfer import modflags                                 # noqa: E402
modflags.set_m2ex(m2, True)
m2 = Mod(m2.root)
plan = transfer.plan_transfer(src, "Fire Archers", m2, transfer.TransferOptions())
check("both sets come across", {n.lower() for n, a, _ in plan.effect_actions if a == "add"}
      == {"fire_trail_set", "fire_burst_set"})
check("  with the M2EX note, not the plain engine's",
      any("EFFECTS IMPORTED" in w for w in plan.warnings) and not any("PLAIN ENGINE" in w for w in plan.warnings))
modflags.set_m2ex(m2, False)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
