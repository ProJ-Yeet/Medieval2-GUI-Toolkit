"""A new entry whose clone has no attachment records still gets its attach sheet.

The Armory bakes a model over a main and an attachment sheet and installs it as
a clone of an existing entry, for that entry's skeletons. Every horse in the
mods we test against has main textures only, so the clone had nowhere to put
the attachment sheet: the files were copied, nothing pointed at them, and half
the horse was drawn with the wrong texture. Tested in game: a horse given
attachment records the way a unit's are written draws both sheets.

  1) ``modeldb.add_attach_records`` on an entry's own text
  2) the new-entry cloner, planned (never written) against a real mod
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import config, edit, modeldb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def lp(s):
    return f"{len(s)} {s}"


TEX = "unit_models/_units/x/textures/x_attach.texture"
NRM = "unit_models/_units/x/textures/x_attach_normal.texture"

# ---------------------------------------------------------------------------
print("\n1) attachment records added to an entry that has none")
main_recs = []
for fac, spr in (("venice", "unit_sprites/a.spr"), ("slave", "unit_sprites/b.spr")):
    main_recs += [lp(fac), lp("unit_models/_units/x/textures/x.texture"),
                  lp("unit_models/_units/x/textures/x_normal.texture"), lp(spr)]
raw = "\n".join(["", lp("x"), "1 1", lp("unit_models/_units/x/x.mesh") + " 15000", "2"]
                + main_recs + ["0", "1", lp("horse"), lp("fs_horse_marka") + " 0",
                               "0 0 -1 0 0 0 0 0 0"])
before = modeldb.parse_entry_text(raw)
check("the sample entry reads, with no attachment records", before.main_textures and not before.attach_textures)

out = modeldb.add_attach_records(raw, TEX, NRM)
e = modeldb.parse_entry_text(out)
check("one attachment record per main faction, in the same order",
      [t.faction for t in e.attach_textures] == [t.faction for t in e.main_textures])
check("each points at the attachment texture and normal map",
      all(t.texture == TEX and t.normal == NRM for t in e.attach_textures))
check("written the way a unit's are: no sprite, the bare 0",
      f"{lp(NRM)} 0\n" in out and all(not t.sprite for t in e.attach_textures))
check("the main records and the animations are untouched",
      [vars(t) for t in e.main_textures] == [vars(t) for t in before.main_textures]
      and e.animations == before.animations)
check("an entry that already has attachment records is left alone",
      modeldb.add_attach_records(out, TEX, NRM) == out)

# ---------------------------------------------------------------------------
print("\n2) the cloner gives a new entry the records its clone lacks")
mods = _realmod.mods(required=False)
mod_root = next((p for p in [mods / "Divide_and_Conquer_EUR"] + _realmod.installed()
                 if (Path(p) / "data/unit_models/battle_models.modeldb").is_file()), None)
if mod_root is None:
    print("  no mod with a battle_models.modeldb installed - skipping section 2")
else:
    cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"
    mod = Mod(Path(mod_root))
    clone = next((x for x in mod.modeldb.entries
                  if x.lods and x.main_textures and not x.attach_textures), None)
    if clone is None:
        print(f"  {mod.name} has no entry without attachment records - skipping section 2")
    else:
        print(f"  mod={mod.name!r} clone={clone.name!r}")
        imports = Path(_tmp.mkdtemp(prefix="ut_imp_"))
        files = {}
        for k, n in (("mesh_src", "m.mesh"), ("texture_src", "m.texture"),
                     ("normal_src", "m_normal.texture"), ("attach_texture_src", "m_attach.texture"),
                     ("attach_normal_src", "m_attach_normal.texture")):
            (imports / n).write_bytes(b"DATA")
            files[k] = str(imports / n)
        req = edit.request_from_dict({"new_models": [dict(
            name="ut_attach_clone", clone_from=clone.name, dest_dir="unit_models/_ut_attach",
            mesh_all_lods=True, **files)]})
        plan = edit.plan_bmdb(mod, req)
        check("plan has no errors", not plan.errors)
        raws = [r for n, r, _p in plan.new_entries if n == "ut_attach_clone"]
        check("the new entry is planned", len(raws) == 1)
        if raws:
            e = modeldb.parse_entry_text(raws[0], pad=clone.first_entry_pad)
            check("it has one attachment record per main faction",
                  len(e.attach_textures) == len(e.main_textures) > 0)
            check("they point at the copied attachment files",
                  all(t.texture == "unit_models/_ut_attach/textures/m_attach.texture"
                      and t.normal == "unit_models/_ut_attach/textures/m_attach_normal.texture"
                      for t in e.attach_textures))
        check("no warning that nothing points at the attachment sheet",
              not any("attachment" in w and "nothing points" in w for w in plan.warnings))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
