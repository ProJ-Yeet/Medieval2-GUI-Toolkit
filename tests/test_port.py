"""Porting a trait or an ancillary out of one mod and into another.

The gate here is not "does the block arrive" - it is **does all three of it
arrive, and does nothing else move**. A trait or an ancillary is a definition
block, the triggers that grant it, and its text keys, in two files; a port that
brings one or two of them produces a mod that either does nothing new or crashes
the character screen the first time somebody has the record.

So what each part is here to catch:

  * the definition lands **above the trigger section**, where the engine is still
    reading definitions, and byte-for-byte as the source mod wrote it - indent,
    inline comments and all;
  * the triggers that name it come with it, appended at the END of the trigger
    section, which is the only position that cannot change what already fires;
  * the text keys land in the destination's own text file with the SOURCE's
    wording, not the tag;
  * the destination file still round-trips: nothing outside the spliced ranges
    was rewritten;
  * a name the destination already has is **skipped and said so**, not silently
    doubled - and `overwrite` is what changes that;
  * what the record names and the destination has not got (a culture, an
    antitrait, an ancillary picture) is REPORTED rather than rewritten, because
    guessing a substitution turns a port into a different record;
  * the whole job is one backup set, so 🕑 Log → Undo puts both files back.

Needs no game install: the two mods are built in a temp folder. When real mods
ARE installed it also plans a port between two of them, which is the check that
finds the formats this never thought of.

    python -m tests.test_port
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _realmod
from unittransfer import (ancillaries, config, keyblock as kb, portrecords as pr,
                          traits, transfer, triggers)
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# --------------------------------------------------------------------------
# two scratch mods. The source's files carry everything a real one does - a
# comment banner, tab alignment, an inline comment inside the block being
# ported - because keeping those is most of what "byte for byte" means here.

SRC_EDCT = (
    ";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;\r\n"
    ";== TRAIT DATA ==\r\n"
    "\r\n"
    "Trait Homesick\r\n"
    "    Characters family\r\n"
    "    ExcludeCultures middle_eastern\r\n"
    "    AntiTraits Wanderer\r\n"
    "\r\n"
    "    Level Homesick_1\r\n"
    "        Description Homesick_1_desc\t\t; the words the player reads\r\n"
    "        EffectsDescription Homesick_1_effects_desc\r\n"
    "        Threshold 2\r\n"
    "\r\n"
    "        Effect Loyalty -1\r\n"
    "\r\n"
    "Trait Wanderer\r\n"
    "    Characters family\r\n"
    "\r\n"
    "    Level Wanderer_1\r\n"
    "        Description Wanderer_1_desc\r\n"
    "        EffectsDescription Wanderer_1_effects_desc\r\n"
    "        Threshold 1\r\n"
    "\r\n"
    ";== TRIGGER DATA ==\r\n"
    "\r\n"
    "Trigger homesick_gain\r\n"
    "    WhenToTest CharacterTurnEnd\r\n"
    "\r\n"
    "    Condition IsGeneral\r\n"
    "\r\n"
    "    Affects Homesick  1  Chance  40\r\n"
    "\r\n"
    "Trigger both_at_once\r\n"
    "    WhenToTest CharacterTurnEnd\r\n"
    "\r\n"
    "    Affects Homesick  1  Chance  5\r\n"
    "    Affects Wanderer  1  Chance  5\r\n"
)

DEST_EDCT = (
    ";== TRAIT DATA ==\r\n"
    "\r\n"
    "Trait Steady\r\n"
    "    Characters family\r\n"
    "\r\n"
    "    Level Steady_1\r\n"
    "        Description Steady_1_desc\r\n"
    "        EffectsDescription Steady_1_effects_desc\r\n"
    "        Threshold 1\r\n"
    "\r\n"
    ";== TRIGGER DATA ==\r\n"
    "\r\n"
    "Trigger steady_gain\r\n"
    "    WhenToTest CharacterTurnEnd\r\n"
    "\r\n"
    "    Affects Steady  1  Chance  10\r\n"
)

SRC_EDA = (
    ";== ANCILLARY DATA ==\r\n"
    "\r\n"
    "Ancillary lucky_charm\r\n"
    "    Type item\r\n"
    "    Transferable 1\r\n"
    "    Image lucky_charm.tga\r\n"
    "    Description lucky_charm_desc\r\n"
    "    EffectsDescription lucky_charm_effects_desc\r\n"
    "    ExcludedAncillaries cursed_ring\r\n"
    "    Effect Command 1\r\n"
    "\r\n"
    ";== TRIGGER DATA ==\r\n"
    "\r\n"
    "Trigger charm_found\r\n"
    "    WhenToTest CharacterTurnEnd\r\n"
    "\r\n"
    "    AcquireAncillary lucky_charm  chance  5\r\n"
)

DEST_EDA = (
    ";== ANCILLARY DATA ==\r\n"
    "\r\n"
    "Ancillary plain_ring\r\n"
    "    Type item\r\n"
    "    Transferable 1\r\n"
    "    Image plain_ring.tga\r\n"
    "    Description plain_ring_desc\r\n"
    "    EffectsDescription plain_ring_effects_desc\r\n"
    "\r\n"
    ";== TRIGGER DATA ==\r\n"
)

EDU = "type peasant\n dictionary peasant\n soldier x, 1, 0, 1\n"


def build(root: Path, edct: str, eda: str, vnv: dict, anc_loc: dict) -> Mod:
    (root / "data" / "text").mkdir(parents=True)
    kb.write_text(root / "data" / "export_descr_character_traits.txt", edct,
                  traits.ENCODING)
    kb.write_text(root / "data" / "export_descr_ancillaries.txt", eda,
                  ancillaries.ENCODING)
    (root / "data" / "export_descr_unit.txt").write_text(EDU, encoding="latin-1")
    for rel, pairs in (("text/export_VnVs.txt", vnv),
                       ("text/export_ancillaries.txt", anc_loc)):
        body = "﻿¬ test\r\n" + "".join(
            f"{{{k}}}{v}\r\n" for k, v in pairs.items())
        kb.write_text(root / "data" / rel, body, "utf-16")
    return Mod(root)


work = Path(tempfile.mkdtemp(prefix="tk-port-"))
src = build(work / "SourceMod", SRC_EDCT, SRC_EDA,
            {"Homesick_1": "Homesick", "Homesick_1_desc": "He pines for home.",
             "Homesick_1_effects_desc": "-1 Loyalty",
             "Wanderer_1": "Wanderer", "Wanderer_1_desc": "Never still.",
             "Wanderer_1_effects_desc": "No effect"},
            {"lucky_charm": "Lucky Charm", "lucky_charm_desc": "A worn coin.",
             "lucky_charm_effects_desc": "+1 Command"})
dst = build(work / "DestMod", DEST_EDCT, DEST_EDA,
            {"Steady_1": "Steady", "Steady_1_desc": "Unshakeable.",
             "Steady_1_effects_desc": "No effect"},
            {"plain_ring": "Plain Ring", "plain_ring_desc": "Just a ring.",
             "plain_ring_effects_desc": "No effect"})

# config, backups and the transfer log go in the temp folder, never the real ones
cfg = Path(tempfile.mkdtemp(prefix="tk-port-cfg-"))
config.CONFIG_DIR = cfg
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config.BACKUP_DIR = cfg / "backups"


print("what the picker opens on")
ov = pr.overview(src, dst, "traits")
check("every trait in the source is offered",
      [r["name"] for r in ov["records"]] == ["Homesick", "Wanderer"])
check("with its shown name, not just its code name",
      ov["records"][0]["label"] == "Homesick (Homesick)")
check("and how many triggers give it over there",
      ov["records"][0]["triggers"] == 2)      # homesick_gain and both_at_once
check("and how many text keys it needs", ov["records"][0]["keys"] == 3)
check("nothing here is in the destination yet", ov["already"] == 0)


print("\na trait, its triggers and its text keys, in one plan")
p = pr.plan(src, dst, "traits", ["Homesick"])
check("the plan holds together", not p.errors)
check("the block is written", any(c.startswith("+ Homesick") for c in p.changes))
check("both triggers that name it come with it",
      sorted(p.rows[0]["triggers"]) == ["both_at_once", "homesick_gain"])
check("its three text keys are written with the SOURCE's wording, not the tag",
      p.loc_writes == {"Homesick_1": "Homesick",
                       "Homesick_1_desc": "He pines for home.",
                       "Homesick_1_effects_desc": "-1 Loyalty"})
check("what it names and this mod has not got is REPORTED, not rewritten",
      any("AntiTraits" in w and "Wanderer" in w for w in p.warnings))
check("...and so is a trigger that also feeds something else",
      any("both_at_once" in w and "Wanderer" in w for w in p.warnings))

res = pr.apply(p)
after = kb.read_text(Path(dst.edct_path), traits.ENCODING)
tf = traits.parse_text(after)
check("the trait is in the destination now", tf.get("Homesick") is not None)
check("its block arrived byte for byte, inline comment and all",
      tf.block_text(tf.get("Homesick"))
      == traits.parse_text(SRC_EDCT).block_text(traits.parse_text(SRC_EDCT).get("Homesick")))
check("it landed ABOVE the trigger section, where definitions are still read",
      tf.get("Homesick").start < tf.trigger_start)
gtf = triggers.parse_text(after)
check("both triggers are there", {t.name for t in gtf.triggers}
      == {"steady_gain", "homesick_gain", "both_at_once"})
check("appended at the end, so nothing that already fired moved",
      [t.name for t in gtf.triggers][-2:] == ["homesick_gain", "both_at_once"])
check("the destination's own trait was left alone", tf.get("Steady") is not None)
check("the file still round-trips byte for byte", tf.text() == after)
names = traits.loc(dst)
check("the text keys landed with their words",
      names.get("Homesick_1_desc") == "He pines for home.")
check("and the destination's own text was not touched",
      names.get("Steady_1_desc") == "Unshakeable.")


print("\na name the destination already has")
p2 = pr.plan(src, dst, "traits", ["Homesick"])
check("is skipped, not doubled", p2.skipped == ["Homesick"])
check("and says why", any("already has" in w for w in p2.warnings))
check("nothing would be written", not p2.payload()["ok"])
p3 = pr.plan(src, dst, "traits", ["Homesick"], overwrite=True)
check("`overwrite` is what changes that",
      any(c.startswith("~ Homesick") for c in p3.changes))
check("...and it does not double the triggers either - they are already there",
      not p3.rows[0]["triggers"])


print("\nundo puts both files back")
before_edct = kb.read_text(Path(dst.edct_path), traits.ENCODING)
before_vnv = dict(traits.loc(dst))
p4 = pr.plan(src, dst, "traits", ["Wanderer"])
rec = pr.apply(p4)
check("the second trait landed",
      traits.parse_text(kb.read_text(Path(dst.edct_path), traits.ENCODING))
      .get("Wanderer") is not None)
transfer.undo(rec["record"]["id"])
check("the EDCT is back byte for byte",
      kb.read_text(Path(dst.edct_path), traits.ENCODING) == before_edct)
check("and so is the text file", traits.loc(dst) == before_vnv)


print("\nan ancillary is the same job with one word changed")
pa = pr.plan(src, dst, "ancillaries", ["lucky_charm"])
check("the plan holds together", not pa.errors)
check("its trigger comes with it", pa.rows[0]["triggers"] == ["charm_found"])
check("its text keys carry the source's words",
      pa.loc_writes.get("lucky_charm_desc") == "A worn coin.")
check("a picture the destination has not got is reported, not copied",
      any("lucky_charm.tga" in w for w in pa.warnings))
check("...and so is an ExcludedAncillaries name it has not got",
      any("ExcludedAncillaries" in w and "cursed_ring" in w for w in pa.warnings))
pr.apply(pa)
eda = kb.read_text(Path(dst.eda_path), ancillaries.ENCODING)
af = ancillaries.parse_text(eda)
check("the ancillary is in the destination", af.get("lucky_charm") is not None)
check("above the trigger section", af.get("lucky_charm").start < af.trigger_start)
check("the EDA still round-trips", af.text() == eda)
check("its trigger arrived",
      triggers.parse_text(eda).get("charm_found") is not None)
check("the destination's own ancillary was left alone",
      af.get("plain_ring") is not None)


print("\nwhat it refuses")
same = pr.plan(src, src, "traits", ["Homesick"])
check("porting a mod into itself", any("same mod" in e for e in same.errors))
none = pr.plan(src, dst, "traits", [])
check("porting nothing", any("at least one" in e for e in none.errors))
missing = pr.plan(src, dst, "traits", ["NotAThing"])
check("a name the source has not got",
      any("NotAThing" in e for e in missing.errors))
try:
    pr.plan(src, dst, "buildings", ["x"])
    check("a kind it does not port", False)
except pr.PortError as e:
    check("a kind it does not port", "buildings" in str(e))


print("\nthe real mods")
mods = _realmod.installed()
if len(mods) < 2:
    print("  (fewer than two mods installed - nothing to sweep)")
else:
    a, b = Mod(mods[0]), Mod(mods[1])
    for kind_id in ("traits", "ancillaries"):
        try:
            real = pr.overview(a, b, kind_id)
        except pr.PortError as e:
            print(f"  ({kind_id}: {e})")
            continue
        check(f"{a.name} -> {b.name}: {real['count']} {real['noun']}(s) offered",
              real["count"] > 0 and not real.get("error"))
        fresh = next((r for r in real["records"]
                      if not r["exists"] and r["triggers"] and r["keys"]), None)
        if fresh is None:
            continue
        rp = pr.plan(a, b, kind_id, [fresh["name"]])
        check(f"...and porting `{fresh['name']}` plans without an error",
              not rp.errors and bool(rp.text))
        check("...its block is spliced in and the file still round-trips",
              rp.kind.module.parse_text(rp.text).text() == rp.text)
        check("...and it brought its text keys",
              bool(rp.loc_writes))

shutil.rmtree(work, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
