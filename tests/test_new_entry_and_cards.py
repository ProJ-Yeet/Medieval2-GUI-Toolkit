"""New bmdb entries with attachment skins, appended armour tiers, and card reuse.

Works on a throwaway copy of Third_Age_Reforged's data files, the same way
``test_edit.py`` does, so the real mods are never touched. Covers the three
things the editor could not do before:

  * a new entry gets its OWN attachment texture / normal map, rather than only
    being able to hand the attachment the main texture
  * ``assign_to`` a slot past the end of ``armour_ug_models`` appends a tier,
    and ``armour_ug_levels`` grows with it so the tier has a level to trigger it
  * a card import source may be a path inside the mod (the editor's "use one of
    these" list), not just an absolute path off disk - and the folder the file
    already lives in is not copied onto itself
"""
import os
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, edu, edit, modeldb
from unittransfer.mod import Mod

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR = MODS / "Third_Age_Reforged"

ok = []
def check(label, cond):
    ok.append(bool(cond)); print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


if not (TATR / "data/export_descr_unit.txt").is_file():
    print("Third_Age_Reforged is not installed - skipping")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"


def fresh_mod() -> Path:
    root = Path(_tmp.mkdtemp(prefix="ut_new_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    for rel in ("export_descr_unit.txt", "text/export_units.txt",
                "unit_models/battle_models.modeldb", "descr_mount.txt"):
        src = TATR / "data" / rel
        if src.exists():
            shutil.copy2(src, data / rel)
    return root


root = fresh_mod()
mod = Mod(root)
entries = mod.modeldb.by_name()

# ---------------------------------------------------------------------------
print("\n1) armour_ug_levels is the levels list, not a guess")
b = ("type\ttest_unit\ndictionary\ttest_unit\n"
     "soldier\tsome_model, 60, 0, 1.2\n"
     "armour_ug_models\tsome_model\narmour_ug_levels\t0\n")
appended = edu.set_model_slot(b, "armour_ug_models#2", "some_model_ug2")
check("a slot past the end appends rather than replacing",
      dict(edu.block_fields(appended))["armour_ug_models"] == "some_model, some_model_ug2")
check("the tier alone leaves the levels short",
      dict(edu.block_fields(appended))["armour_ug_levels"] == "0")
levelled = edu.sync_armour_levels(appended)
check("sync gives the new tier a level, one past the highest",
      dict(edu.block_fields(levelled))["armour_ug_levels"] == "0, 1")
check("a list that is already long enough is left alone",
      edu.sync_armour_levels(levelled) == levelled)
check("a block with no armour_ug_levels line is left alone",
      edu.sync_armour_levels("type\tx\narmour_ug_models\ta, b\n")
      == "type\tx\narmour_ug_models\ta, b\n")

# ---------------------------------------------------------------------------
print("\n2) a new entry with its own attachment skin, appended as a tier")
# a unit whose soldier entry HAS an attachment texture group - that second group
# is the whole point of this case, so a unit without one proves nothing
UNIT = None
for u in mod.edu.units:
    e = entries.get((u.soldier_model or "").lower())
    if e and e.lods and e.main_textures and e.attach_textures and u.dictionary:
        UNIT = u.type
        break
if UNIT is None:
    print("  no unit with an attachment texture group - skipping section 2")
else:
    unit = mod.edu.by_type()[UNIT]
    soldier = unit.soldier_model.lower()
    clone = entries[soldier]
    tiers_before = len(unit.armour_ug_models)
    print(f"  unit={UNIT!r} soldier={soldier!r} tiers={tiers_before}")

    imports = Path(_tmp.mkdtemp(prefix="ut_imp_"))
    mesh_src = imports / "tier2.mesh"; mesh_src.write_bytes(b"MESHDATA")
    tex_src = imports / "tier2.texture"; tex_src.write_bytes(b"TEXDATA")
    att_src = imports / "tier2_att.texture"; att_src.write_bytes(b"ATTDATA")
    att_n_src = imports / "tier2_att_norm.texture"; att_n_src.write_bytes(b"ATTNORM")

    new_name = "ut_test_tier_two"
    slot = f"armour_ug_models#{tiers_before + 1}"
    req = edit.request_from_dict({
        "unit": UNIT,
        "new_models": [{
            "name": new_name, "clone_from": soldier,
            "dest_dir": "unit_models/_ut_new",
            "mesh_src": str(mesh_src), "texture_src": str(tex_src),
            "attach_texture_src": str(att_src), "attach_normal_src": str(att_n_src),
            "mesh_all_lods": True, "assign_to": slot,
        }],
    })
    plan = edit.plan_edit(mod, req)
    check("plan has no errors", not plan.errors)
    check("all four files queued for copy", len(plan.copies) == 4)
    edit.apply_edit(plan)

    mod = Mod(root)
    e_new = mod.modeldb.by_name().get(new_name)
    check("new entry present", e_new is not None)
    check("modeldb round-trips byte-exact",
          mod.modeldb.to_text() ==
          (mod.data / "unit_models/battle_models.modeldb").read_text(encoding=modeldb.ENCODING))
    att = {s["kind"]: s["value"] for s in modeldb.path_slots(e_new) if s["group"] == "attach"}
    main = {s["kind"]: s["value"] for s in modeldb.path_slots(e_new) if s["group"] == "main"}
    check("the attachment texture is the imported one, not the main one",
          att.get("texture") == "unit_models/_ut_new/tier2_att.texture")
    check("the attachment normal map is its own too",
          att.get("normal") == "unit_models/_ut_new/tier2_att_norm.texture")
    check("the main texture is still the main one",
          main.get("texture") == "unit_models/_ut_new/tier2.texture")
    check("attachment files copied in",
          (mod.data / "unit_models/_ut_new/tier2_att.texture").read_bytes() == b"ATTDATA")

    u2 = mod.edu.by_type()[UNIT]
    check("the tier was APPENDED, not written over one the unit had",
          len(u2.armour_ug_models) == tiers_before + 1
          and u2.armour_ug_models[-1].lower() == new_name)
    if tiers_before:
        check("the tiers it already had are untouched",
              [m.lower() for m in u2.armour_ug_models[:tiers_before]]
              == [m.lower() for m in unit.armour_ug_models])
    lv = dict(edu.block_fields(u2.raw)).get("armour_ug_levels")
    if lv is not None:
        levels = [x.strip() for x in lv.split(",") if x.strip()]
        check("every tier has a level to trigger it",
              len(levels) >= len(u2.armour_ug_models))
        check("the levels still ascend",
              levels == sorted(levels, key=lambda x: int(x) if x.lstrip("-").isdigit() else 0))

    # an attachment given no file of its own, with apply_to_attach, follows the main
    req = edit.request_from_dict({
        "unit": UNIT,
        "new_models": [{
            "name": "ut_test_tier_three", "clone_from": soldier,
            "dest_dir": "unit_models/_ut_new",
            "texture_src": str(tex_src), "apply_to_attach": True, "assign_to": "",
        }],
    })
    plan = edit.plan_edit(mod, req)
    check("fallback plan has no errors", not plan.errors)
    raw = dict((n, r) for n, r, _p in plan.new_entries)["ut_test_tier_three"]
    slots = modeldb.path_slots_raw(raw, pad=entries[soldier].first_entry_pad)
    att2 = {s["kind"]: s["value"] for s in slots if s["group"] == "attach"}
    check("with no attachment file of its own it follows the main texture",
          att2.get("texture") == "unit_models/_ut_new/tier2.texture")
    check("and no sprite is ever written into an attachment record",
          att2.get("sprite", "") in ("", "0"))

# ---------------------------------------------------------------------------
print("\n3) a card the mod already has, spread to every faction")
mod = Mod(root)
unit3 = next(u for u in mod.edu.units if u.dictionary and len(u.ownership) >= 2)
own = [f.lower() for f in unit3.ownership if f.lower() != "slave"] or \
      [f.lower() for f in unit3.ownership]
here = mod.data / "ui/units" / own[0] / f"#{unit3.dictionary}.tga"
here.parent.mkdir(parents=True, exist_ok=True)
here.write_bytes(b"THE ONE GOOD CARD")
rel = f"ui/units/{own[0]}/#{unit3.dictionary}.tga"

req = edit.request_from_dict({"unit": unit3.type, "card_src": rel})
plan = edit.plan_edit(mod, req)
check("a mod-relative card source resolves", not plan.errors)
dests = [r for _s, r in plan.icon_copies]
check("it fans out to the other owning factions",
      len(dests) >= len(own) - 1 + 1)     # the others, plus the merc fallback
check("the folder it already lives in is not copied onto itself", rel not in dests)
check("every destination is named for the dictionary",
      all(d.endswith(f"#{unit3.dictionary}.tga") for d in dests))

req = edit.request_from_dict({"unit": unit3.type, "card_src": "ui/units/../../../etc/passwd"})
plan = edit.plan_edit(mod, req)
check("a relative source cannot climb out of the mod",
      any("not found" in e for e in plan.errors))

req = edit.request_from_dict({"unit": unit3.type, "card_src": "ui/units/nope/#nothing.tga"})
plan = edit.plan_edit(mod, req)
check("a source that is not there is an error, not a traceback",
      any("not found" in e for e in plan.errors))

# ---------------------------------------------------------------------------
print("\n4) only the folders that were ticked")
# not own[0]: that is the folder the source file itself lives in, and section 3
# already covers a folder not being copied onto itself
pick = [f for f in own if f != own[0]][:2]
req = edit.request_from_dict({"unit": unit3.type, "card_src": rel, "card_folders": pick})
plan = edit.plan_edit(mod, req)
dests = [r for _s, r in plan.icon_copies]
check("a subset writes those folders and no others",
      not plan.errors and len(dests) == len(pick)
      and all(r.split("/")[2] in pick for r in dests))
check("the merc fallback is not slipped back in",
      not any(r.startswith("ui/units/mercs/") for r in dests))

other = [f for f in own if f != own[0]][:1]
req = edit.request_from_dict({"unit": unit3.type, "card_src": rel, "card_folders": other})
plan = edit.plan_edit(mod, req)
check("the folders left out keep what they had",
      [r for _s, r in plan.icon_copies]
      == [f"ui/units/{other[0]}/#{unit3.dictionary}.tga"])

req = edit.request_from_dict({"unit": unit3.type, "card_src": rel,
                              "card_folders": ["../../../etc", "good_faction", ""]})
check("a folder name that is path-shaped is dropped before it becomes a path",
      req.card_folders == ["good_faction"])

req = edit.request_from_dict({"unit": unit3.type, "card_src": rel,
                              "card_folders": ["not_an_owner"]})
plan = edit.plan_edit(mod, req)
check("a folder outside ownership is written, but said out loud",
      [r for _s, r in plan.icon_copies]
      == [f"ui/units/not_an_owner/#{unit3.dictionary}.tga"]
      and any("ownership" in w for w in plan.warnings))

# ---------------------------------------------------------------------------
print("\n5) a file this tool writes carries the time it wrote it")
# A mod's files come out of one archive sharing a timestamp to the second, and
# shutil.copy2 carries the source's timestamps onto the copy - so an icon
# replaced by another of the same mod landed with the very mtime it already had,
# and every mtime-keyed cache downstream went on serving the old picture. That
# is the whole of "I replaced the card and the tool still shows the old one".
src_card = mod.data / rel
twin = mod.data / f"ui/units/{own[-1]}/#{unit3.dictionary}.tga"
twin.parent.mkdir(parents=True, exist_ok=True)
twin.write_bytes(b"A DIFFERENT PICTURE")
st = src_card.stat()
os.utime(twin, ns=(st.st_atime_ns, st.st_mtime_ns))
check("the two start on one mtime, which is the trap",
      twin.stat().st_mtime_ns == src_card.stat().st_mtime_ns)
req = edit.request_from_dict({"unit": unit3.type, "card_src": rel,
                              "card_folders": [own[-1]]})
plan = edit.plan_edit(mod, req)
edit.apply_edit(plan)
check("the copy landed", twin.read_bytes() == src_card.read_bytes())
check("and its mtime moved, so an mtime-keyed cache notices",
      twin.stat().st_mtime_ns != src_card.stat().st_mtime_ns)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
