"""BMDB mode — the whole battle_models.modeldb, not one unit's slice of it.

Runs on a throwaway copy of Third_Age_Reforged's data files, so the real mods are
never touched. Covers:
  * the audit: what nothing references, what only a `soldier` line names, and
    which files under unit_models no entry mentions at all
  * the safety nets: an entry named in a descr_*.txt — or inline in a campaign's
    descr_strat.txt / campaign_script.txt — is never called unused, and the padded
    first entry of a sentinel-less modeldb is never removed
  * mounts no unit rides: reported, removable from descr_mount.txt, and the model
    entry they were the last referrer of comes free with them — including when a
    mount is named after a model, where the audit has two differently shaped
    mention maps in play and used to read the wrong one
  * cleanup: entries dropped, their files exported mirroring the mod's layout,
    files a surviving entry still uses left alone, and a standalone modeldb of
    exactly the removed entries that parses back
  * accepted soldier merges rewrite the EDU's soldier line and free the entry
  * mod-wide entry editing (plan_bmdb): a rename chases every unit in the EDU
  * undo restores the mod byte-exact
"""
import shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import config, edit, modeldb
from unittransfer import bmdb as bmdb_mod
from unittransfer.mod import Mod
from unittransfer.transfer import undo

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
TATR = MODS / "Third_Age_Reforged"

ok = []
def check(label, cond):
    ok.append(bool(cond)); print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def fresh_mod(with_assets=()) -> Path:
    """A copy of the mod's text files, plus any asset files the test needs."""
    root = Path(tempfile.mkdtemp(prefix="ut_bmdb_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    for rel in ("export_descr_unit.txt", "text/export_units.txt",
                "unit_models/battle_models.modeldb", "descr_mount.txt",
                "descr_character.txt"):
        src = TATR / "data" / rel
        if src.exists():
            shutil.copy2(src, data / rel)
    for rel in with_assets:
        src, dst = TATR / "data" / rel, data / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return root


cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

root = fresh_mod()
mod = Mod(root)
before_db = mod.modeldb_path.read_bytes()
before_edu = mod.edu_path.read_bytes()

print("\n== audit ==")
steps = []
a = bmdb_mod.audit(mod, progress=lambda pct, label: steps.append((pct, label)))
check(f"the audit reported {len(steps)} progress steps, each with a label",
      len(steps) > 5 and all(label for _pct, label in steps))
check("progress never goes backwards and ends at 100%",
      all(b[0] >= x[0] for x, b in zip(steps, steps[1:])) and steps[-1][0] == 100)
unused = {u["entry"] for u in a["unused"]}
check(f"{a['entry_count']} entries scanned", a["entry_count"] > 500)
check(f"{len(unused)} entries nothing references", len(unused) > 0)
check("every unused entry really is unreferenced by the EDU",
      not (unused & {m for u in mod.edu.units for m in u.model_names()}))
check("every unused entry really is unreferenced by descr_mount.txt",
      not (unused & set((mod.mounts or {}).values())))
check("descr_character.txt battle_models are never called unused",
      not (unused & set(bmdb_mod._character_models(mod))))
mentioned = {m["entry"] for m in a["mentioned"]}
check(f"{len(mentioned)} entries held back because a descr_*.txt names them",
      bool(mentioned) and not (mentioned & unused))
check(f"{len(a['merges'])} soldier-only merge candidates", len(a["merges"]) > 0)

print("\n== merge candidates ==")
for c in a["merges"][:3]:
    print(f"     {c['entry']} -> {c['into']}  (units: {', '.join(c['units'][:3])})")
entries = mod.modeldb.by_name()
check("every candidate is named ONLY by soldier lines",
      all(not any(u.type in c["units"] and (c["entry"] in [x.lower() for x in u.armour_ug_models]
                                            or c["entry"] in [x.lower() for x in u.officers])
                  for u in mod.edu.units)
          for c in a["merges"]))
check("every candidate's twin has an identical footer",
      all(bmdb_mod.footer_key(entries[c["entry"]]) == bmdb_mod.footer_key(entries[c["into"]])
          for c in a["merges"]))
check("a candidate's twin is never the entry itself",
      all(c["into"] != c["entry"] for c in a["merges"]))
check("candidates are never also on the unused list",
      not ({c["entry"] for c in a["merges"]} & unused))
# Twins suggest each other, so A->B and B->A can both look like a saving. Accept
# both and each soldier line ends up naming an entry the same cleanup deleted --
# M2TW then refuses to read the EDU at all.
sources = {c["entry"] for c in a["merges"]}
check("no candidate points at an entry that is itself merged away",
      not [c for c in a["merges"] if c["into"] in sources])
check("nor is one ever offered as an alternative target",
      not [o for c in a["merges"] for o in c["options"] if o in sources])
# Only referenced entries are offered to move onto: that is what keeps them off
# the unused list and what makes plan_cleanup refuse to delete them. An entry
# held back only because a descr_*.txt mentions it is deletable, so it is out.
users_now = bmdb_mod.entry_users(mod)
def is_referenced(n):
    s = users_now.get(n)
    return bool(s and any(s[k] for k in bmdb_mod.SLOT_KINDS))
check("every target offered is an entry something still references",
      all(is_referenced(o) for c in a["merges"] for o in c["options"]))
check("...including the default pick",
      all(is_referenced(c["into"]) for c in a["merges"]))
# "already an armour tier of the same unit" is a fact about the picked twin, so the
# audit says it for EVERY option — the UI's picker can be changed after the scan.
by_type = mod.edu.by_type()
def _own_tiers(c):
    return {x.lower() for t in c["units"] if by_type.get(t)
            for x in by_type[t].armour_ug_models}
check("each candidate flags which of its options are armour tiers of the same unit",
      all(set(c["own_options"]) <= set(c["options"]) for c in a["merges"])
      and all(set(c["own_options"]) == set(c["options"]) & _own_tiers(c)
              for c in a["merges"]))
check("the default pick's badge agrees with that list",
      all(c["own_upgrade"] == (c["into"] in c["own_options"]) for c in a["merges"]))
check("an entry only a descr_*.txt mentions is never offered as a target",
      not ({m["entry"] for m in a["mentioned"]}
           & {o for c in a["merges"] for o in c["options"]}))

print("\n== cleanup plan ==")
target = Path(tempfile.mkdtemp(prefix="ut_export_")) / "unused_assets"
picked = sorted(unused)[:20]
merge = a["merges"][0]
plan = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target), entries=picked,
    merges=[{"entry": merge["entry"], "into": merge["into"]}]))
check("no errors", not plan.errors)
check(f"{len(plan.entry_deletes)} entries queued for removal (20 picked + 1 merged)",
      len(plan.entry_deletes) == 21 and merge["entry"] in plan.entry_deletes)
check("the EDU is rewritten for the merge", bool(plan.edu_text))
check("every exported file mirrors the mod's own layout",
      all(rel.startswith("data/") for _s, rel in plan.exports))
check("a file a surviving entry still uses is never moved",
      all(f not in [r for _s, r in plan.exports] for f in plan.kept_files))

inside = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(root / "export"), entries=picked))
check("refuses an export folder inside the mod", bool(inside.errors))

# A stale scan can list an entry the mod has started using again. Removing it
# would leave a `soldier` line pointing at nothing, which stops M2TW loading the
# EDU at all -- so the plan re-checks the request instead of trusting it.
used_entry = merge["entry"]                       # named by a soldier line
stale = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target), entries=picked + [used_entry]))
check("a referenced entry asked for as unused is not removed",
      used_entry not in stale.entry_deletes)
check("...and the warning says what still names it",
      any(used_entry in w and "soldier model for" in w for w in stale.warnings))
check("...while the rest of the request still goes through",
      len(stale.entry_deletes) == len(picked))
check("...and nothing rewrites the EDU, since no merge was accepted",
      not stale.edu_text)

# Same entry, this time as an accepted merge: now it may go, because the merge
# repoints the soldier line naming it.
paired = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target), entries=picked + [used_entry],
    merges=[{"entry": used_entry, "into": merge["into"]}]))
check("the same entry IS removed when a merge repoints its soldier line",
      used_entry in paired.entry_deletes and bool(paired.edu_text))

# A merge that no longer validates must not delete through the exemption either.
bad = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target), entries=[used_entry],
    merges=[{"entry": used_entry, "into": "no_such_entry_at_all"}]))
check("a merge that fails its checks takes the entry with it",
      used_entry not in bad.entry_deletes and bool(bad.errors))

# The scan no longer offers a mutual pair, but a hand-built request still can.
mutual = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target),
    merges=[{"entry": used_entry, "into": merge["into"]},
            {"entry": merge["into"], "into": used_entry}]))
check("a mutual pair of merges is refused rather than applied",
      bool(mutual.errors) and not mutual.entry_deletes)
check("...and the error names both halves",
      any(used_entry in e and merge["into"] in e for e in mutual.errors))
into_doomed = bmdb_mod.plan_cleanup(mod, bmdb_mod.CleanupRequest(
    target=str(target), entries=picked,          # picked[0] is on the unused list
    merges=[{"entry": used_entry, "into": picked[0]}]))
check("merging into an entry the same cleanup deletes is refused",
      bool(into_doomed.errors) and used_entry not in into_doomed.entry_deletes)

print("\n== cleanup apply ==")
orig_raw = {e.name: e.raw for e in mod.modeldb.entries}   # applying reparses `mod`
rec = bmdb_mod.apply_cleanup(plan)
mod2 = Mod(root)
db2 = mod2.modeldb
check(f"modeldb went {a['entry_count']} -> {len(db2.entries)}",
      len(db2.entries) == a["entry_count"] - 21)
check("removed entries are gone", not (set(plan.entry_deletes) & set(db2.by_name())))
check("the header count follows the removal",
      db2.header_ints[5] == len(db2.entries) + (1 if db2.blank_raw else 0))
check("the file still parses to a clean round trip",
      db2.to_text() == mod2.modeldb_path.read_text(encoding=modeldb.ENCODING))

merged_unit = next(u for u in mod2.edu.units if u.type == merge["units"][0])
check(f"'{merged_unit.type}' soldier is now '{merge['into']}'",
      merged_unit.soldier_model.lower() == merge["into"])
check("nothing in the EDU names a removed entry any more",
      not ({m for u in mod2.edu.units for m in u.model_names()} & set(plan.entry_deletes)))

print("\n== the export folder ==")
exp_db = target / bmdb_mod.EXPORT_DB_NAME
check("a standalone modeldb was written next to the assets", exp_db.is_file())
parsed = modeldb.parse_file(exp_db)
check(f"it parses and holds exactly the {len(plan.entry_deletes)} removed entries",
      sorted(parsed.by_name()) == sorted(plan.entry_deletes))
check("its entries are byte-identical to the ones cut out of the mod",
      all(e.raw == orig_raw[e.name] for e in parsed.entries))
check("a README explains how to put it back", (target / bmdb_mod.README_NAME).is_file())
check("it is not called battle_models.modeldb (it would overwrite a real one)",
      not (target / "data" / "unit_models" / "battle_models.modeldb").exists())

print("\n== undo ==")
undo(rec["id"])
mod3 = Mod(root)
check("the modeldb is restored byte-exact", mod3.modeldb_path.read_bytes() == before_db)
check("export_descr_unit.txt is restored byte-exact", mod3.edu_path.read_bytes() == before_edu)
check("the export folder is left alone (it is a copy, not the original)", exp_db.is_file())

print("\n== assets really move ==")
# a fresh mod that actually has the files of one unused entry on disk (a mod's
# modeldb names plenty of files that were never shipped with it, so pick an entry
# whose files really are in the source mod)
mod_a = Mod(fresh_mod())
owners = {}
for e in mod_a.modeldb.entries:
    for f in e.mesh_files() + e.texture_files():
        owners.setdefault(f.lower(), set()).add(e.name)
au = next(u for u in bmdb_mod.audit(mod_a, scan_orphans=False)["unused"]
          if [f for f in u["files"]
              if (TATR / "data" / f).is_file() and owners[f.lower()] == {u["entry"]}])
files = [f for f in au["files"]
         if (TATR / "data" / f).is_file() and owners[f.lower()] == {au["entry"]}][:3]
root_b = fresh_mod(with_assets=files)
mod_b = Mod(root_b)
tgt_b = Path(tempfile.mkdtemp(prefix="ut_export2_")) / "out"
pb = bmdb_mod.plan_cleanup(mod_b, bmdb_mod.CleanupRequest(target=str(tgt_b), entries=[au["entry"]]))
moved = [r for _s, r in pb.exports]
check(f"'{au['entry']}': {len(moved)} of its files are on disk and queued to move", bool(moved))
rec_b = bmdb_mod.apply_cleanup(pb)
check("they are gone from the mod", all(not (mod_b.data / d).exists() for d in pb.deletes))
check("they are in the export folder under the same relative path",
      all((tgt_b / r).is_file() for r in moved))
undo(rec_b["id"])
check("undo brings them back", all((mod_b.data / d).is_file() for d in pb.deletes))

print("\n== orphan files (nothing in the modeldb mentions them) ==")
root_c = fresh_mod()
(Path(root_c) / "data/unit_models/_Junk").mkdir(parents=True)
junk = Path(root_c) / "data/unit_models/_Junk/nobody_reads_this.texture"
junk.write_bytes(b"x" * 4096)
mod_c = Mod(root_c)
ac = bmdb_mod.audit(mod_c)
rels = [o["rel"] for o in ac["orphans"]]
check("the planted file is reported as an orphan",
      "unit_models/_Junk/nobody_reads_this.texture" in rels)
check("no orphan is a file the modeldb actually names",
      not (set(r.lower() for r in rels)
           & {f.lower() for e in mod_c.modeldb.entries
              for f in e.mesh_files() + e.texture_files()}))
check("the modeldb itself is never offered as an orphan",
      not any(".modeldb" in r.lower() for r in rels))
tgt_c = Path(tempfile.mkdtemp(prefix="ut_export3_")) / "out"
pc = bmdb_mod.plan_cleanup(mod_c, bmdb_mod.CleanupRequest(
    target=str(tgt_c), orphans=["unit_models/_Junk/nobody_reads_this.texture"]))
rec_c = bmdb_mod.apply_cleanup(pc)
check("it moves into the export's unused folder, path mirrored",
      (tgt_c / bmdb_mod.UNUSED_SUBDIR / "data/unit_models/_Junk/nobody_reads_this.texture").is_file())
check("and is gone from the mod", not junk.exists())
check("the modeldb was not rewritten — no entry was touched",
      Mod(root_c).modeldb_path.read_bytes() == before_db)
undo(rec_c["id"])
check("undo restores it", junk.is_file())

print("\n== campaign references (descr_strat.txt / campaign_script.txt) ==")
# A named character on the campaign map can carry its own battle_model, written
# inline in a comma-separated line rather than on one of its own. Nothing in the
# EDU or descr_mount points at it, so without this pass it looks stone dead.
root_e = fresh_mod()
dead = [u["entry"] for u in bmdb_mod.audit(Mod(root_e), scan_orphans=False)["unused"]]
in_strat, in_script, in_comment = dead[0], dead[1], dead[2]
camp = root_e / "data/world/maps/campaign/imperial_campaign"
camp.mkdir(parents=True)
(camp / "descr_strat.txt").write_text(
    "character\tGrishnakh, general, male, age 23, x 346, y 250, "
    f"portrait Grishnak, battle_model {in_strat}, hero_ability WHIPING\n",
    encoding="latin-1")
(camp / "campaign_script.txt").write_text(
    f"    spawn_character England, agent spy, battle_model {in_script}, x 10, y 20\n"
    f"    ;spawn_character England, agent spy, battle_model {in_comment}, x 1, y 2\n",
    encoding="latin-1")
mod_e2 = Mod(root_e)
a_e = bmdb_mod.audit(mod_e2, scan_orphans=False)
unused_e = {u["entry"] for u in a_e["unused"]}
check("both campaign files are found", len(a_e["campaign_files"]) == 2)
check(f"'{in_strat}' (descr_strat.txt, inline after a comma) is no longer unused",
      in_strat not in unused_e)
check(f"'{in_script}' (campaign_script.txt) is no longer unused", in_script not in unused_e)
check(f"'{in_comment}' (only in a commented-out line) is still unused",
      in_comment in unused_e)
slots_e = bmdb_mod.entry_users(mod_e2)
# The label is the file's path inside the mod, not its parent folder: the same
# two filenames now turn up in half a dozen trees (custom campaigns, custom
# battles, an installer's alternate copies), and "imperial_campaign/descr_strat.txt"
# no longer says which of them was read.
check("the reference is attributed to the campaign file it came from",
      slots_e[in_strat]["campaign"]
      == ["file:data/world/maps/campaign/imperial_campaign/descr_strat.txt"])
pe = bmdb_mod.plan_cleanup(mod_e2, bmdb_mod.CleanupRequest(
    target=str(Path(tempfile.mkdtemp(prefix="ut_exp_"))), entries=[in_strat]))
check("asked to remove it anyway, the cleanup refuses", not pe.entry_deletes)
check("and says which campaign file still names it",
      any("descr_strat.txt" in w for w in pe.warnings))

print("\n== change_battle_model: the script command that puts the model LAST ==")
# `change_battle_model <faction> <who> <model>` swaps a character's model
# mid-campaign. It breaks both of the other patterns at once — the bare-word one
# never fires (the character before `battle_model` is `_`, not a space), and if it
# were loosened to fire it would capture the FACTION. An entry named only this way
# is invisible to every other net here, so it reads as textbook dead weight: this
# is how a mod loses the model its faction leader becomes at the climax of its own
# campaign.
check("the inline form still yields its FIRST argument",
      bmdb_mod.script_models(
          "character\tG, named character, age 22, portrait P, battle_model gandalf_white, "
          "hero_ability WHITE_GANDALF, label g2") == ["gandalf_white"])
check("the command form yields its LAST argument, not the faction",
      bmdb_mod.script_models("        change_battle_model turks leader aragorn_arnor")
      == ["aragorn_arnor"])
check("an unknown *_battle_model command is read as a command, not ignored",
      bmdb_mod.script_models("set_battle_model england general someone_new")
      == ["someone_new"])
check("both forms are picked up out of one file, in order",
      bmdb_mod.script_models("change_battle_model france leader saruman\n"
                             "  spawn, battle_model legolas, x 1\n") == ["saruman", "legolas"])

root_g = fresh_mod()
dead_g = [u["entry"] for u in bmdb_mod.audit(Mod(root_g), scan_orphans=False)["unused"]]
swapped, inline_g = dead_g[0], dead_g[1]
camp_g = root_g / "data/world/maps/campaign/imperial_campaign"
camp_g.mkdir(parents=True)
(camp_g / "campaign_script.txt").write_text(
    "monitor_event PreFactionTurnStart FactionIsLocal\n"
    "    if I_EventCounter house_of_kings_finished = 1\n"
    f"        change_battle_model turks leader {swapped}\n"
    "    end_if\n"
    "    spawn_army\n"
    f"        character\tGandalf, named character, age 22, battle_model {inline_g}, label g2\n"
    "    end\n"
    "end_monitor\n",
    encoding="latin-1")
mod_g = Mod(root_g)
a_g = bmdb_mod.audit(mod_g, scan_orphans=False)
unused_g = {u["entry"] for u in a_g["unused"]}
check(f"'{swapped}' (change_battle_model) is no longer unused", swapped not in unused_g)
check(f"'{inline_g}' (inline battle_model) is no longer unused", inline_g not in unused_g)
check("the faction name on the command is NOT mistaken for the model",
      "turks" not in {n for n, _w in bmdb_mod._campaign_models(mod_g)})
pg = bmdb_mod.plan_cleanup(mod_g, bmdb_mod.CleanupRequest(
    target=str(Path(tempfile.mkdtemp(prefix="ut_exp2_"))), entries=[swapped]))
check("asked to remove the swapped-to model anyway, the cleanup refuses",
      not pg.entry_deletes and any("campaign_script.txt" in w for w in pg.warnings))

print("\n== descr_model_strat.txt is not a reference ==")
# The "any descr_*.txt that mentions it" net is deliberately over-cautious, but
# descr_model_strat.txt only ever names STRAT-map models (data/models_strat) — a
# battle-model name matching in there is a coincidence that would pin a genuinely
# dead entry in place forever.
root_g = fresh_mod()
dead_g = [u["entry"] for u in bmdb_mod.audit(Mod(root_g), scan_orphans=False)["unused"]][0]
strat_block = (f"type {dead_g}\nskeleton strat_named_with_army\n"
               f"model_flexi data/models_strat/{dead_g}_high.cas, 15\n")
(root_g / "data/descr_model_strat.txt").write_text(strat_block, encoding="latin-1")
a_g = bmdb_mod.audit(Mod(root_g), scan_orphans=False)
check(f"'{dead_g}' named in descr_model_strat.txt is still reported as unused",
      dead_g in {u["entry"] for u in a_g["unused"]})
check("and is not held back as 'mentioned somewhere else'",
      dead_g not in {m["entry"] for m in a_g["mentioned"]})
(root_g / "data/descr_model_strat.txt").unlink()
(root_g / "data/descr_ut_other.txt").write_text(strat_block, encoding="latin-1")
a_g2 = bmdb_mod.audit(Mod(root_g), scan_orphans=False)
check("the same text in any OTHER descr_*.txt still holds it back",
      dead_g in {m["entry"] for m in a_g2["mentioned"]})

print("\n== mounts no unit rides ==")
# Removing the mount is what takes the last referrer off its model, so the entry
# only comes free as part of the same cleanup.
root_f = fresh_mod()
free_me = [u["entry"] for u in bmdb_mod.audit(Mod(root_f), scan_orphans=False)["unused"]][0]
dmp = root_f / "data/descr_mount.txt"
before_mounts = dmp.read_bytes()
dmp.write_text(dmp.read_text(encoding="latin-1") +
               f"\ntype\t\t\tut_test_mount\nclass\t\t\thorse\nmodel\t\t\t{free_me}\n"
               "radius\t\t\t1.2\nheight\t\t\t2.0\nmass\t\t\t1.0\n", encoding="latin-1")
mod_f = Mod(root_f)
a_f = bmdb_mod.audit(mod_f, scan_orphans=False)
check("the planted mount's model is no longer 'unused' — the mount references it",
      free_me not in {u["entry"] for u in a_f["unused"]})
row = next((r for r in a_f["unused_mounts"] if r["mount"] == "ut_test_mount"), None)
check("the mount is reported as ridden by nobody", row is not None)
check("and flagged as freeing its model entry", bool(row and row["frees_model"]))
ridden = next(u.mount for u in mod_f.edu.units if u.mount)
check(f"a mount a unit actually rides ('{ridden}') is not offered",
      ridden not in {r["mount"] for r in a_f["unused_mounts"]})
pf = bmdb_mod.plan_cleanup(mod_f, bmdb_mod.CleanupRequest(
    target=str(Path(tempfile.mkdtemp(prefix="ut_exp_"))), mounts=[ridden]))
check("and asked for anyway it is refused, with the riders named",
      not pf.mount_deletes and any(ridden in w for w in pf.warnings))

tgt_f = Path(tempfile.mkdtemp(prefix="ut_exp_"))
n_mounts = len(mod_f.mount_file.mounts)     # applying invalidates mod_f's cached parse
pf2 = bmdb_mod.plan_cleanup(mod_f, bmdb_mod.CleanupRequest(
    target=str(tgt_f), mounts=["ut_test_mount"], entries=[free_me]))
check("planning the removal is clean", not pf2.errors)
check("the mount block goes", pf2.mount_deletes == ["ut_test_mount"])
check("and its model entry goes with it", free_me in pf2.entry_deletes)
rec_f = bmdb_mod.apply_cleanup(pf2)
mod_f2 = Mod(root_f)
check("descr_mount.txt no longer defines it", mod_f2.mount_file.get("ut_test_mount") is None)
check("every other mount is untouched",
      len(mod_f2.mount_file.mounts) == n_mounts - 1)
check("the entry is gone from the modeldb", free_me not in mod_f2.modeldb.by_name())
check("the removed block is exported verbatim so it can be pasted back",
      (tgt_f / bmdb_mod.EXPORT_MOUNTS_NAME).is_file()
      and "ut_test_mount" in (tgt_f / bmdb_mod.EXPORT_MOUNTS_NAME).read_text(encoding="latin-1"))
undo(rec_f["id"])
check("undo restores descr_mount.txt byte-exact",
      (root_f / "data/descr_mount.txt").read_bytes() != before_mounts
      and "ut_test_mount" in (root_f / "data/descr_mount.txt").read_text(encoding="latin-1"))
check("undo restores the modeldb byte-exact",
      (root_f / "data/unit_models/battle_models.modeldb").read_bytes() == before_db)

# ---------------------------------------------------------------------------
print("\n== a mount named after a model: the two mention maps stay apart ==")
# The audit carries two "somebody still names it" maps and they are NOT
# interchangeable: `name_mentions` is keyed by modeldb ENTRY name and holds a row
# per name, `_mount_mentions` is keyed by MOUNT name and holds a bare filename.
# mount_audit used one name for both, the second assignment shadowing the first,
# so the two model-keyed lookups read the mount map. That answers for the wrong
# thing the moment a mount and an entry share a name — four of them do in DaC —
# and hands mention_file a string where it wants a row, which crashed the whole
# audit before it returned anything.
root_c = fresh_mod()
spare_c = [u["entry"] for u in bmdb_mod.audit(Mod(root_c), scan_orphans=False)["unused"]]
collide, other = spare_c[0], spare_c[1]

dmc = root_c / "data/descr_mount.txt"
dmc.write_text(
    dmc.read_text(encoding="latin-1")
    # nobody rides this one, and its MODEL is the name of the mount below
    + f"\ntype\t\t\tut_collide_rider\nclass\t\t\thorse\nmodel\t\t\t{collide}\n"
      "radius\t\t\t1.2\nheight\t\t\t2.0\nmass\t\t\t1.0\n"
    # …and this one is NAMED for that model, which is the collision
    + f"\ntype\t\t\t{collide}\nclass\t\t\thorse\nmodel\t\t\t{other}\n"
      "radius\t\t\t1.2\nheight\t\t\t2.0\nmass\t\t\t1.0\n",
    encoding="latin-1")

# Two files name it, and the two scanners disagree about which. `_descr_tokens`
# splits a path into tokens, so it sees the name in the first file; the mount
# sweep matches the whole phrase and will not match one preceded by `/`, so it
# only sees the second. Whichever filename comes back on the row therefore says
# which map the lookup went to — that is what makes this a real check and not
# just "it did not crash".
(root_c / "data/descr_ut_aaa.txt").write_text(
    f"; a path, so only the token sweep finds it\nmodels/{collide}/body.cas\n",
    encoding="latin-1")
(root_c / "data/descr_ut_bbb.txt").write_text(
    f"; the bare phrase, which both sweeps find\nmount {collide}\n",
    encoding="latin-1")

mod_c = Mod(root_c)
by_mount = bmdb_mod._mount_mentions(mod_c)
by_entry = bmdb_mod.name_mentions(mod_c)
check("the mount sweep really does hold a bare filename",
      isinstance(by_mount.get(collide), str))
check("…and the entry sweep a row", isinstance(by_entry.get(collide), dict))
check("the two disagree about the file, so the row below can say which was read",
      by_mount.get(collide) == "descr_ut_bbb.txt"
      and by_entry.get(collide, {}).get("file") == "descr_ut_aaa.txt")

a_c = bmdb_mod.audit(mod_c, scan_orphans=False)      # this is what used to crash
row_c = next((r for r in a_c["unused_mounts"] if r["mount"] == "ut_collide_rider"), None)
check("the audit gets all the way through a mount named after a model",
      row_c is not None)
check("the mount named after the model is held, not offered for removal",
      collide in {m["mount"] for m in a_c["mentioned_mounts"]}
      and collide not in {r["mount"] for r in a_c["unused_mounts"]})
check("'mentioned_in' is read from the ENTRY map, which is the one keyed by model",
      bool(row_c) and row_c["mentioned_in"] == "descr_ut_aaa.txt")

# mention_file itself takes either shape, because both maps are legitimately
# passed to it — see its docstring.
check("mention_file reads a row", bmdb_mod.mention_file(
    {"x": {"file": "descr_a.txt", "lua": False, "in_comment": False}}, "X")
    == "descr_a.txt")
check("…and a bare filename", bmdb_mod.mention_file({"x": "descr_b.txt"}, "X")
      == "descr_b.txt")
check("…and says nothing for a name neither holds",
      bmdb_mod.mention_file({"x": "descr_b.txt"}, "nobody") == "")

print("\n== mod-wide entry editing (the unit editor's engine, no unit) ==")
root_d = fresh_mod()
mod_d = Mod(root_d)
# an entry several units reference: the rename has to reach every one of them
counts = {}
for u in mod_d.edu.units:
    for m in u.model_names():
        counts.setdefault(m, []).append(u.type)
name, users = max(counts.items(), key=lambda kv: len(kv[1]))
req = edit.bmdb_request_from_dict(
    {"model_edits": [{"entry": name, "new_name": name + "_renamed"}]})
pd = edit.plan_bmdb(mod_d, req)
check("no errors", not pd.errors)
check(f"'{name}' renamed", pd.entry_renames.get(name) == name + "_renamed")
check(f"all {len(users)} units that named it are rewritten", bool(pd.edu_text))
edit.apply_edit(pd)
mod_e = Mod(root_d)
check("the entry is renamed in the modeldb", name + "_renamed" in mod_e.modeldb.by_name())
check("no unit still names the old entry",
      not any(name in u.model_names() for u in mod_e.edu.units))
check(f"all {len(users)} of them name the new one",
      sum(1 for u in mod_e.edu.units if name + "_renamed" in u.model_names()) == len(users))

print("\n== padded first entry (a modeldb with no 'blank' sentinel) ==")
# Such a file keeps its reserved int-pairs in the FIRST entry, so that entry can
# never be the one we drop — the next entry has no padding and the file would stop
# parsing. Built by hand (same shape as tests/test_modeldb_no_blank_entry.py).
P = "0 0 "
def _padded(name, tex):
    return (f"\n{len(name)} {name} \n1.0 {P}\n1 {P}"
            f"\n{len('m/' + name + '.mesh')} m/{name}.mesh 121 {P}"
            f"\n1 {P}\n4 ever \n{len(tex)} {tex} \n{len(tex)} {tex} \n0 \n0 "
            f"{P}\n1 {P}\n5 horse \n3 pri \n3 sec \n0 \n0 {P}"
            f"\n-1 0.0 0.0 0.0 0.0 0.0 0.0 {P}")
def _plain(name, tex):
    return (f"\n{len(name)} {name} \n1.0 \n1 "
            f"\n{len('m/' + name + '.mesh')} m/{name}.mesh 121 "
            f"\n1 \n4 ever \n{len(tex)} {tex} \n{len(tex)} {tex} \n0 \n0 "
            f"\n1 \n5 horse \n3 pri \n3 sec \n0 \n0 "
            f"\n-1 0.0 0.0 0.0 0.0 0.0 0.0 ")
root_f = fresh_mod()
(Path(root_f) / "data/unit_models/battle_models.modeldb").write_text(
    "22 serialization::archive 3 0 0 0 0 3 0 0"
    + _padded("pad_first", "t/a.texture") + _plain("second_e", "t/b.texture")
    + _plain("third_e", "t/c.texture"), encoding=modeldb.ENCODING)
mod_f = Mod(root_f)
first = mod_f.modeldb.entries[0]
check(f"the first entry '{first.name}' is the padded one", first.first_entry_pad)
af = bmdb_mod.audit(mod_f, scan_orphans=False)
check("it is not even offered as unused",
      first.name not in {u["entry"] for u in af["unused"]}
      and first.name in {m["entry"] for m in af["mentioned"]})
tgt_f = Path(tempfile.mkdtemp(prefix="ut_export4_")) / "out"
pf = bmdb_mod.plan_cleanup(mod_f, bmdb_mod.CleanupRequest(
    target=str(tgt_f), entries=[first.name, "second_e", "third_e"]))
check("asked for anyway, it is refused with a reason",
      pf.entry_deletes == ["second_e", "third_e"] and any("padded" in w for w in pf.warnings))
bmdb_mod.apply_cleanup(pf)
check("what is left still parses, padding intact",
      [e.name for e in Mod(root_f).modeldb.entries] == ["pad_first"])
exported = modeldb.parse_file(tgt_f / bmdb_mod.EXPORT_DB_NAME)
check("the export of a sentinel-less file gets a sentinel of its own so it reads back",
      sorted(exported.by_name()) == ["second_e", "third_e"] and bool(exported.blank_raw))

print("\n== the wider campaign net: nested, custom-battle and alternate trees ==")
# Every one of these is a real place a mod puts a file that names a battle model,
# and every one of them used to be invisible to the cleanup: the campaign folder's
# immediate children were walked and nothing else was.
root_w = fresh_mod()
dead_w = [u["entry"] for u in bmdb_mod.audit(Mod(root_w), scan_orphans=False)["unused"]]
nested, battle, activate, eop_extra = dead_w[0], dead_w[1], dead_w[2], dead_w[3]
places = {
    # a custom campaign: one folder DEEPER than the walk used to reach
    "data/world/maps/campaign/custom/Shattered_Alliances/descr_strat.txt":
        f"character\tX, general, male, age 23, x 1, y 2, battle_model {nested}, hero_ability W\n",
    # a custom battle map: a whole file kind that was never opened at all
    "data/world/maps/battle/custom/Cair_Andros/descr_battle.txt":
        f"character\tY, general, battle_model {battle}, x 3, y 4\n",
    # an installer's alternate tree — a copy now, the live mod the moment the
    # mod's own switcher runs
    "Activate/NORMAL/data/world/maps/campaign/imperial_campaign/campaign_script.txt":
        f"    spawn_character England, agent spy, battle_model {activate}, x 5, y 6\n",
    "extra/kdSkip/world/maps/campaign/imperial_campaign/campaign_script.txt":
        f"    spawn_character England, agent spy, battle_model {eop_extra}, x 7, y 8\n",
}
for rel, text in places.items():
    p = root_w / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="latin-1")
mod_w = Mod(root_w)
a_w = bmdb_mod.audit(mod_w, scan_orphans=False)
unused_w = {u["entry"] for u in a_w["unused"]}
check(f"all {len(places)} of them are found", len(a_w["campaign_files"]) == len(places))
for label, name in (("nested custom campaign", nested), ("custom battle map", battle),
                    ("an Activate/ alternate tree", activate),
                    ("an extra/ alternate tree", eop_extra)):
    check(f"'{name}' named only by {label} is no longer unused", name not in unused_w)
check("each is attributed to its own full path inside the mod",
      sorted(a_w["campaign_files"]) == sorted(places))

print("\n== the mod's OTHER battle_models.modeldb files are NOT a second opinion ==")
# A mod carries several: `battle_models.modeldb.bak`, `battle_models_og.modeldb`,
# a copy some other tool wrote out. Every one of them is a snapshot of an OLDER
# state of the live file, not an alternate database the game ever loads — so
# honouring them would hold alive every file the mod has ever used at any point
# in its history, and no cleanup could free anything again. Only the live
# `data/unit_models/battle_models.modeldb` is believed.
root_s = fresh_mod()
# the backup names a file the live database has since stopped naming — exactly
# the shape a stale `.bak` has
(root_s / "data/unit_models/from_modeldb").mkdir(parents=True, exist_ok=True)
for stale_rel in ("data/unit_models/battle_models.modeldb.bak",
                  "data/unit_models/battle_models_og.modeldb",
                  "data/unit_models/from_modeldb/battle_models_new.modeldb"):
    shutil.copy2(Mod(root_s).modeldb_path, root_s / stale_rel)
live_s = modeldb.parse_file(Mod(root_s).modeldb_path)
victim_s = next(e for e in live_s.entries if e.mesh_files())
stale_file = victim_s.mesh_files()[0].replace("\\", "/")
p_stale = root_s / "data" / stale_file
p_stale.parent.mkdir(parents=True, exist_ok=True)
p_stale.write_bytes(b"named only by the backups now")
live_s.entries = [e for e in live_s.entries if e.name != victim_s.name]
live_s.write(Mod(root_s).modeldb_path)
mod_s = Mod(root_s)
check("the live database no longer names the file",
      stale_file.lower() not in {f.replace("\\", "/").lower()
                                 for e in mod_s.modeldb.entries for f in e.mesh_files()})
a_s = bmdb_mod.audit(mod_s)
check("a file only the backup copies still name IS offered as an orphan",
      stale_file.lower() in {o["rel"].lower() for o in a_s["orphans"]})
check("and no .modeldb is ever offered for removal itself",
      not [o for o in a_s["orphans"] if ".modeldb" in o["rel"].lower()])
# …nor may a modeldb be read as text: it names thousands of files, so token-
# scanning one would make every file in the mod "mentioned somewhere"
check("a .modeldb is never collected as a text file to scan",
      not [p for p in mod_s.scanned_files["text"] if ".modeldb" in p.name.lower()])
check("so the text scan does not resurrect it either",
      stale_file.lower() not in bmdb_mod.unit_model_refs(mod_s))

print("\n== recheck: what a past cleanup took out that today's nets would keep ==")
# The morning after. A cleanup ran under the narrower nets, the mod now crashes,
# and the thing that broke it is by definition no longer IN the mod — so only the
# cleanup's own log entry remembers it. This is the pass that reads that back.
root_r = fresh_mod()
mod_r0 = Mod(root_r)
needed = root_r / "data/unit_models/_units/needed_after_all_lod0.mesh"
needed.parent.mkdir(parents=True, exist_ok=True)
needed.write_bytes(b"the mesh a script needs")
junk_r = root_r / "data/unit_models/_units/really_is_junk_lod0.mesh"
junk_r.write_bytes(b"nothing names this")
tgt_r = Path(tempfile.mkdtemp(prefix="ut_export5_")) / "out"
pr = bmdb_mod.plan_cleanup(mod_r0, bmdb_mod.CleanupRequest(
    target=str(tgt_r),
    orphans=["unit_models/_units/needed_after_all_lod0.mesh",
             "unit_models/_units/really_is_junk_lod0.mesh"]))
rec_r = bmdb_mod.apply_cleanup(pr)
check("both files are out of the mod", not needed.is_file() and not junk_r.is_file())

# …and only NOW does a script that names one of them turn up (the same shape as a
# reference the older build could not see).
script_r = root_r / "eopData/eopScripts/spawn.lua"
script_r.parent.mkdir(parents=True, exist_ok=True)
script_r.write_text(
    'M2TWEOP.setModel(unit, "unit_models/_units/needed_after_all_lod0.mesh")\n',
    encoding="latin-1")
mod_r = Mod(root_r)
rr = bmdb_mod.recheck(mod_r)
flagged = {x["name"] for x in rr["rows"]}
check("the cleanup is found in the log", len(rr["runs"]) == 1 and rr["runs"][0]["hits"] == 1)
check("the file the script names is flagged",
      "unit_models/_units/needed_after_all_lod0.mesh" in flagged)
check("the file nothing names is not",
      "unit_models/_units/really_is_junk_lod0.mesh" not in flagged)
row_r = rr["rows"][0]
check("it says why", any("spawn.lua" in w for w in row_r["why"]))
check("and that a copy still exists to put it back from",
      row_r["revertable"] and row_r["source"] in ("backup", "export"))

back = bmdb_mod.revert_recheck(mod_r, [{"kind": "file", "run": row_r["run"],
                                        "name": row_r["name"]}])
check("reverting puts the file back, byte-exact",
      needed.is_file() and needed.read_bytes() == b"the mesh a script needs")
check("it is reported as restored and nothing failed",
      back["restored"] == [row_r["name"]] and not back["failed"])
check("the file that really was junk is still gone", not junk_r.is_file())
rr2 = bmdb_mod.recheck(Mod(root_r))
check("a second recheck is clean — a file that is back is not a finding", not rr2["rows"])
undo(back["id"])
check("the revert is itself undoable", not needed.is_file())

print("\n== recheck: an entry, and a run whose copies are all gone ==")
root_x = fresh_mod()
mod_x0 = Mod(root_x)
doomed_x = [u["entry"] for u in bmdb_mod.audit(mod_x0, scan_orphans=False)["unused"]][0]
tgt_x = Path(tempfile.mkdtemp(prefix="ut_export6_")) / "out"
px = bmdb_mod.plan_cleanup(mod_x0, bmdb_mod.CleanupRequest(
    target=str(tgt_x), entries=[doomed_x]))
rec_x = bmdb_mod.apply_cleanup(px)
check("the entry is out of the modeldb",
      doomed_x not in {e.name for e in Mod(root_x).modeldb.entries})
check("the run wrote down which entries it removed, so a later recheck can ask",
      bmdb_mod.removed_entries(rec_x) == [doomed_x])
# something starts naming it again
(root_x / "data/descr_campaign_ai_db.txt").write_text(
    f"; the AI picks {doomed_x} for its bodyguard\n", encoding="latin-1")
rx = bmdb_mod.recheck(Mod(root_x))
check("the entry is flagged", [r["name"] for r in rx["rows"]] == [doomed_x])
backx = bmdb_mod.revert_recheck(Mod(root_x), [{"kind": "entry", "run": rec_x["id"],
                                               "name": doomed_x}])
check("reverting puts the entry back into the live modeldb",
      doomed_x in {e.name for e in Mod(root_x).modeldb.entries} and not backx["failed"])
check("and what is left still parses", len(Mod(root_x).modeldb.entries) > 1)

# a run whose backup AND export folder have both since been deleted: still
# reported (the log remembers), but honestly marked as unrecoverable
shutil.rmtree(rec_x["backup_root"], ignore_errors=True)
shutil.rmtree(tgt_x, ignore_errors=True)
root_y = fresh_mod()
mod_y0 = Mod(root_y)
gone_y = root_y / "data/unit_models/_units/gone_forever_lod0.mesh"
gone_y.parent.mkdir(parents=True, exist_ok=True)
gone_y.write_bytes(b"x")
tgt_y = Path(tempfile.mkdtemp(prefix="ut_export7_")) / "out"
py_ = bmdb_mod.plan_cleanup(mod_y0, bmdb_mod.CleanupRequest(
    target=str(tgt_y), orphans=["unit_models/_units/gone_forever_lod0.mesh"]))
rec_y = bmdb_mod.apply_cleanup(py_)
(root_y / "eopData").mkdir(parents=True, exist_ok=True)
(root_y / "eopData/x.lua").write_text(
    'setModel("unit_models/_units/gone_forever_lod0.mesh")\n', encoding="latin-1")
shutil.rmtree(rec_y["backup_root"], ignore_errors=True)
shutil.rmtree(tgt_y, ignore_errors=True)
ry = bmdb_mod.recheck(Mod(root_y))
check("a run with no surviving copies is still reported", len(ry["rows"]) == 1)
check("but the row says plainly that it cannot be put back",
      not ry["rows"][0]["revertable"] and ry["revertable"] == 0)
check("and the run row says both copies are gone",
      not ry["runs"][0]["backup_here"] and not ry["runs"][0]["export_here"])
fail_y = bmdb_mod.revert_recheck(Mod(root_y), [{"kind": "file", "run": ry["rows"][0]["run"],
                                                "name": ry["rows"][0]["name"]}])
check("asked to revert it anyway, it fails with a reason rather than pretending",
      not fail_y["restored"] and any("no copy left" in f for f in fail_y["failed"]))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
