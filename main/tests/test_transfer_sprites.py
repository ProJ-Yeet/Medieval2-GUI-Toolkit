"""A copied sprite never lands on a different sprite the destination already has.

Reported 2026-09-28: an imported Uruk-hai Crossbow's base armour level showed
the destination's old sprite at the far LOD, while its upgrades (new names)
looked right. A sprite is named after its model, so a model whose name the
destination already uses brings a sprite whose path it already uses too, and
the relocating modes only ever moved files under unit_models/.

Uses Third Age Reforged's Uruk-Hai Crossbow and a TEMP destination (the three
DB files of DaC, plus a different sprite planted at Reforged's sprite path) and
a TEMP config dir, so neither the real mods nor the project config are touched.

Run:  python -m tests.test_transfer_sprites
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer.transfer import (TransferOptions, plan_transfer,  # noqa: E402
                                   apply_transfer, undo)

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR = MODS / "Third_Age_Reforged"
DAC = MODS / "Divide_and_Conquer_EUR"
UNIT = "Uruk-Hai Crossbow"
SPR = "unit_sprites/france_Uruk_Crossbow_sprite.spr"
NEW = "unit_sprites/france_Uruk_Crossbow_thir_sprite.spr"
# a different sprite (two sheets, not three) to plant at SPR in the destination
OTHER = "france_Heavy_uruk_sword_sprite"

results = []


def check(label, cond):
    results.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return cond


def make_dest(plant: str = "other") -> Path:
    """DaC's three DB files, and a sprite at SPR: a different one, or the source's own."""
    tmp = Path(_tmp.mkdtemp(prefix="ut_sprdest_"))
    data = tmp / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    (data / "unit_sprites").mkdir(parents=True)
    for rel in ("export_descr_unit.txt", "text/export_units.txt",
                "unit_models/battle_models.modeldb"):
        shutil.copy2(DAC / "data" / rel, data / rel)
    if plant == "other":
        folder = DAC / "data" / "unit_sprites"
        for f in folder.glob(OTHER + "*"):
            shutil.copy2(f, data / "unit_sprites" / f.name.replace(OTHER, "france_Uruk_Crossbow_sprite"))
    elif plant == "same":
        for f in (TATR / "data" / "unit_sprites").glob("france_Uruk_Crossbow_sprite*"):
            shutil.copy2(f, data / "unit_sprites" / f.name)
    return tmp


def snapshot(folder: Path):
    return {f.name: f.read_bytes() for f in sorted(folder.glob("france_Uruk_Crossbow*"))}


def sprite_paths(mod: Mod, model: str):
    e = mod.modeldb.get(model)
    return {t.sprite for t in e.main_textures} if e else set()


def main():
    cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"
    src = Mod(TATR)
    made = []
    try:
        print("\n=== A: default mode, a different sprite at the path ===")
        root = make_dest("other"); made.append(root)
        planted = snapshot(root / "data" / "unit_sprites")
        plan = plan_transfer(src, UNIT, Mod(root), TransferOptions())
        check("plan renames the colliding sprite", plan.sprite_renames.get(SPR) == NEW)
        rels = {r for _a, r in plan.asset_files}
        check("its three sheets travel under the new name",
              all(f"unit_sprites/france_Uruk_Crossbow_thir_sprite_00{i}.texture" in rels
                  for i in range(3)))
        check("nothing is copied onto the old path",
              not any(r.startswith("unit_sprites/france_Uruk_Crossbow_sprite") for r in rels))
        check("the plan says so", any("sprite(s) renamed" in str(w) for w in plan.warnings))
        check("the summary says so", "SPRITE RENAMED" in plan.summary())
        rec = apply_transfer(plan)
        dest = Mod(root)
        model = plan.model_renames.get("uruk_crossbow", "uruk_crossbow")
        check(f"the added entry '{model}' points at the new sprite",
              sprite_paths(dest, model) == {NEW})
        after = snapshot(root / "data" / "unit_sprites")
        check("the destination's own sprite is untouched",
              all(after.get(k) == v for k, v in planted.items()))
        check("the new sprite is the source's, byte for byte",
              after.get("france_Uruk_Crossbow_thir_sprite.spr")
              == (TATR / "data" / SPR).read_bytes()
              and all(after.get(f"france_Uruk_Crossbow_thir_sprite_00{i}.texture")
                      == (TATR / "data" / f"unit_sprites/france_Uruk_Crossbow_sprite_00{i}.texture").read_bytes()
                      for i in range(3)))
        again = plan_transfer(src, UNIT, Mod(root), TransferOptions(on_conflict="rename",
                                                                    new_type="Uruk Again",
                                                                    new_dictionary="uruk_again"))
        check("a second transfer reuses the entry (the rename reads back)",
              any(a.source_name == "uruk_crossbow" and a.action == "reuse_identical"
                  for a in again.model_actions))
        undo(rec["id"])
        check("undo takes the renamed sprite away",
              snapshot(root / "data" / "unit_sprites") == planted)

        print("\n=== B: keep the destination's files, same collision ===")
        root = make_dest("other"); made.append(root)
        plan = plan_transfer(src, UNIT, Mod(root), TransferOptions(asset_conflict="use_existing"))
        check("renamed there too", plan.sprite_renames.get(SPR) == NEW)

        print("\n=== C: overwrite, same collision ===")
        plan = plan_transfer(src, UNIT, Mod(root), TransferOptions(asset_conflict="overwrite"))
        check("overwrite leaves the path alone", not plan.sprite_renames
              and any(r == SPR for _a, r in plan.asset_files))

        print("\n=== D: the same sprite already there ===")
        root = make_dest("same"); made.append(root)
        plan = plan_transfer(src, UNIT, Mod(root), TransferOptions())
        check("an identical sprite is reused, not renamed", not plan.sprite_renames)

        print("\n=== E: nothing at the path ===")
        root = make_dest("none"); made.append(root)
        plan = plan_transfer(src, UNIT, Mod(root), TransferOptions())
        check("no collision, no rename", not plan.sprite_renames)
    finally:
        for d in made + [cfg]:
            shutil.rmtree(d, ignore_errors=True)

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
