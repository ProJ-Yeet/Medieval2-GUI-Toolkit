"""A battle-model entry's animations, changed from the Unit Editor's model card.

    python -m tests.test_animentry

Nothing installed is needed: a two-entry modeldb is written to a temp mod.

1. the entry payload carries its animation records, and the unit / entry
   payload the skeleton names the mod already uses
2. a changed primary skeleton and mount type land in the entry and nowhere
   else: the weapon skeletons, the other entry and every other byte stay
3. an unknown skeleton is a warning, an unknown mount type or a missing
   primary skeleton an error, and a changed record count is refused
4. apply writes it and Undo puts the file back byte for byte
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import config, edit, modeldb  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def s(x):
    return f"{len(x)} {x}"


def entry_text(name, skel):
    return (f"{s(name)}\n1 1\n{s('unit_models/' + name + '.mesh')} 6400\n1\n{s('england')}\n"
            f"{s('unit_models/t.texture')}\n{s('unit_models/t_norm.texture')}\n{s('unit_sprites/x_sprite.spr')}\n"
            f"1\n{s('england')}\n{s('unit_models/a.texture')}\n{s('unit_models/a_norm.texture')} 0\n"
            f"1\n{s('none')}\n{s(skel)} {s(skel)}\n"
            f"1\n{s(skel + '_Primary')}\n1\n{s(skel + '_Primary')}\n"
            f"16 -0.09 0 0 -0.35 0.8 0.6\n")


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = Path(_tmp.mkdtemp(prefix="ut_animentry_"))
data = root / "data"
(data / "unit_models").mkdir(parents=True)
(data / "text").mkdir(parents=True)
(data / "unit_models/battle_models.modeldb").write_bytes((
    "22 serialization::archive 3 0 0 0 0 3 0 0\n5 blank " + " ".join(["0"] * 39) + "\n"
    + entry_text("elf", "MTW2_Swordsman") + entry_text("dwarf", "MTW2_Spearman")).encode("latin-1"))
(data / "export_descr_unit.txt").write_text(
    "type             Elf Swords\ndictionary       elf_swords\ncategory         infantry\n"
    "class            light\nvoice_type       Light\nsoldier          elf, 40, 0, 1\n"
    "ownership        england\n", encoding="latin-1")
(data / "text/export_units.txt").write_text("", encoding="utf-16")
DB = data / "unit_models/battle_models.modeldb"
before = DB.read_bytes()

try:
    mod = Mod(root)
    print("1) what the editor is given")
    e = mod.modeldb.by_name()["elf"]
    p = edit.model_payload(e, ["soldier"], [], mod=mod)
    check("the entry's records: mount type, primary and secondary skeleton",
          p["animations"] == [{"mount_type": "none", "primary": "MTW2_Swordsman",
                               "secondary": "MTW2_Swordsman"}])
    check("the mod's skeleton names, for the suggestions",
          {"MTW2_Swordsman", "MTW2_Spearman"} <= set(sorted(mod.modeldb.all_skeletons())))

    def plan(anims):
        req = edit.bmdb_request_from_dict({"model_edits": [{"entry": "elf", "animations": anims}]})
        return edit.plan_bmdb(Mod(root), req)

    print("2) a record changed")
    pl = plan([{"mount_type": "horse", "primary": "MTW2_Spearman", "secondary": ""}])
    check("no error, and the change is listed", not pl.errors and any("animation #1" in c for c in pl.changes))
    new = modeldb.parse_entry(pl.entry_updates["elf"])
    a = new.animations[0]
    check("mount type, primary and secondary written",
          (a.mount_type, a.primary_skeleton, a.secondary_skeleton) == ("horse", "mtw2_spearman", ""))
    check("the weapon skeletons are left alone",
          a.pri_weapons == ["MTW2_Swordsman_Primary"] and a.sec_weapons == ["MTW2_Swordsman_Primary"])
    check("only the edited entry changes", set(pl.entry_updates) == {"elf"})
    check("a known skeleton is not warned about", not any("MTW2_Spearman".lower() in w.lower() for w in pl.warnings))
    check("the same names again (case aside) are no change at all",
          not plan([{"mount_type": "none", "primary": "mtw2_swordsman", "secondary": "MTW2_SWORDSMAN"}]).entry_updates)

    print("3) what is refused or warned about")
    pw = plan([{"mount_type": "none", "primary": "no_such_skeleton", "secondary": ""}])
    check("an unknown skeleton is a warning, not an error",
          not pw.errors and any("no_such_skeleton" in w for w in pw.warnings))
    check("an unknown mount type is an error", bool(plan([{"mount_type": "dragon", "primary": "MTW2_Spearman"}]).errors))
    check("an empty primary skeleton is an error", bool(plan([{"mount_type": "none", "primary": ""}]).errors))
    check("a different number of records is refused",
          bool(plan([{"mount_type": "none", "primary": "MTW2_Spearman"}] * 2).errors))

    print("4) written, and undone")
    pl = plan([{"mount_type": "horse", "primary": "MTW2_Spearman", "secondary": ""}])
    res = edit.apply_edit(pl)
    after = Mod(root).modeldb.by_name()
    check("the file now says horse / mtw2_spearman",
          after["elf"].animations[0].mount_type == "horse"
          and after["elf"].animations[0].primary_skeleton.lower() == "mtw2_spearman")
    check("the other entry is untouched", after["dwarf"].raw == Mod(root).modeldb.by_name()["dwarf"].raw
          and after["dwarf"].animations[0].primary_skeleton == "MTW2_Spearman")
    from unittransfer.transfer import undo
    undo(res["record"]["id"] if "record" in res else res["id"])
    check("Undo puts the modeldb back byte for byte", DB.read_bytes() == before)
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
