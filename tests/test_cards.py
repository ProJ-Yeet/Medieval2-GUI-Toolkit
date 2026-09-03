"""Unit cards and info cards - the merc-folder consolidation.

Runs on a mod this file builds from scratch, so it needs no game install and
each case is exactly the one it names:

  * art for a dictionary no unit claims is found, and one a ``.lua`` script names
    is not (M2TWEOP can build a unit at runtime);
  * copies that are byte for byte the same are one row with nothing to decide;
    copies that DIFFER are a variant set, and consolidating one is refused until
    the caller says which picture survives;
  * consolidating writes the survivor into ``ui/units/mercs`` /
    ``ui/unit_info/merc`` and takes every other copy out - and writes nothing at
    all when the survivor is already the merc copy;
  * a unit that pins ``card_pic_dir`` is left alone, and so is a file in those
    folders that is not shaped like a card (the agent pictures);
  * the export folder keeps "for a unit that is gone" apart from "a copy we
    folded up", and undo restores the mod byte-exact.

    python -m tests.test_cards
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import cards, config
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


EDU = "\n".join([
    "type\t\talpha unit",
    "dictionary\talpha",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\talpha_model, 60, 0, 1.2",
    "ownership\tengland, france",
    "",
    "type\t\tbeta unit",
    "dictionary\tbeta",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tbeta_model, 60, 0, 1.2",
    "ownership\tengland, france",
    "",
    "type\t\tgamma unit",
    "dictionary\tgamma",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tgamma_model, 60, 0, 1.2",
    "card_pic_dir\tengland",
    "ownership\tengland, france",
    "",
    "type\t\tdelta unit",
    "dictionary\tdelta",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tdelta_model, 60, 0, 1.2",
    "ownership\tengland",
    "",
]) + "\n"

LUA = "-- built at runtime\nlocal d = 'runtime_hero'\nEOP.createUnit(d)\n"

#: rel -> bytes. Same bytes means the same picture, which is the whole test.
ART = {
    # alpha: identical in two faction folders, nothing in the merc folder yet
    "ui/units/england/#alpha.tga": b"alpha-card",
    "ui/units/france/#alpha.tga": b"alpha-card",
    "ui/unit_info/england/alpha_info.tga": b"alpha-info",
    "ui/unit_info/france/alpha_info.tga": b"alpha-info",
    # beta: genuinely DIFFERENT cards per faction, plus a third folder that
    # agrees with england - so the commonest picture is england's, two to one
    "ui/units/england/#beta.tga": b"beta-card-england",
    "ui/units/france/#beta.tga": b"beta-card-france",
    "ui/units/spain/#beta.tga": b"beta-card-england",
    # gamma: pins card_pic_dir, so its card is counted and never consolidated
    "ui/units/england/#gamma.tga": b"gamma-card",
    "ui/units/france/#gamma.tga": b"gamma-card",
    # delta: identical, and one of the copies is ALREADY the merc one - the case
    # where consolidating should write no new file at all
    "ui/units/mercs/#delta.tga": b"delta-card",
    "ui/units/england/#delta.tga": b"delta-card",
    # art for a unit that no longer exists
    "ui/units/england/#ghost.tga": b"ghost-card",
    "ui/units/france/#ghost.tga": b"ghost-card",
    "ui/unit_info/england/ghost_info.tga": b"ghost-info",
    # …and for one that only a Lua script creates
    "ui/units/england/#runtime_hero.tga": b"hero-card",
    # not a card at all: the agent pictures the game reads by their own name
    "ui/units/england/spy.tga": b"spy",
    "ui/units/england/diplomat.tga": b"diplomat",
}


def fresh_mod() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ut_cards_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "export_descr_unit.txt").write_text(EDU, encoding="latin-1")
    (data / "scripts").mkdir()
    (data / "scripts" / "hero.lua").write_text(LUA, encoding="utf-8")
    for rel, blob in ART.items():
        p = data / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
    return root


cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = fresh_mod()
mod = Mod(root)

print("\n== the audit ==")
a = cards.audit(mod)
card = next(k for k in a["kinds"] if k["kind"] == "card")
info = next(k for k in a["kinds"] if k["kind"] == "info")

check("four units are read out of the EDU", a["units"] == 4)
check("the card folder is ui/units/mercs and the info one is ui/unit_info/merc",
      (card["base"], card["merc"]) == ("ui/units", "mercs")
      and (info["base"], info["merc"]) == ("ui/unit_info", "merc"))
check("art for a dictionary no unit claims is found",
      [u["name"] for u in card["unused"]] == ["ghost"])
check("…and every folder holding it is listed",
      sorted(card["unused"][0]["folders"]) == ["england", "france"])
check("a dictionary only a .lua script names is NOT offered for removal",
      [k["name"] for k in card["lua_kept"]] == ["runtime_hero"]
      and not any(u["name"] == "runtime_hero" for u in card["unused"]))
check("identical copies are one row with nothing to decide",
      sorted(d["name"] for d in card["duplicates"]) == ["alpha", "delta"])
check("copies that differ are a variant set instead",
      [v["name"] for v in card["variants"]] == ["beta"])
check("a variant set is ordered commonest picture first",
      card["variants"][0]["options"][0]["folders"] == ["england", "spain"])
check("a unit that pins card_pic_dir is counted, not consolidated",
      [p["name"] for p in card["pinned"]] == ["gamma"]
      and not any(d["name"] == "gamma" for d in card["duplicates"]))
check("info cards are audited separately from unit cards",
      [d["name"] for d in info["duplicates"]] == ["alpha"]
      and [u["name"] for u in info["unused"]] == ["ghost"])
check("a file that is not shaped like a card is counted and left alone",
      card["stray_count"] == 2
      and sorted(Path(s["rel"]).name for s in card["strays"]) == ["diplomat.tga", "spy.tga"])
check("what consolidating saves is every copy but the one that stays",
      next(d for d in card["duplicates"] if d["name"] == "alpha")["bytes_saved"]
      == len(b"alpha-card"))

print("\n== the plan ==")
target = Path(tempfile.mkdtemp(prefix="ut_cards_out_"))
shutil.rmtree(target)
beta_england = card["variants"][0]["options"][0]["digest"]
plan = cards.plan_cleanup(mod, cards.cleanup_request_from_dict({
    "target": str(target),
    "remove": {"card": ["ghost"], "info": ["ghost"]},
    "consolidate": {"card": ["alpha", "delta"], "info": ["alpha"]},
    "choose": {"card": {"beta": beta_england}},
}))
copies = {rel for _src, rel in plan.copies}
exported = {rel for _src, rel in plan.exports}
check("no errors", not plan.errors)
check("the survivor is written into the merc folder",
      "ui/units/mercs/#alpha.tga" in copies
      and "ui/unit_info/merc/alpha_info.tga" in copies)
check("nothing is written when the survivor is already the merc copy",
      "ui/units/mercs/#delta.tga" not in copies)
check("the chosen variant becomes the merc copy",
      "ui/units/mercs/#beta.tga" in copies)
check("art for a unit that is gone lands in unused_files/",
      "unused_files/data/ui/units/england/#ghost.tga" in exported)
check("a folded-up copy lands beside the mod's own layout, not in unused_files/",
      "data/ui/units/france/#alpha.tga" in exported)
check("the merc copy that stays is never scheduled for removal",
      "ui/units/mercs/#delta.tga" not in set(plan.deletes))
check("the counts say what happened",
      plan.removed == 2 and plan.consolidated == 4)

print("\n== a request the mod disagrees with is refused, not obeyed ==")
bad = cards.plan_cleanup(mod, cards.cleanup_request_from_dict({
    "target": str(target),
    "remove": {"card": ["alpha"]},                 # alpha is a live unit
    "consolidate": {"card": ["beta", "gamma", "nosuch"]},
}))
check("art for a unit that still exists is not removed", bad.removed == 0)
check("a variant set with no choice made is left alone", bad.consolidated == 0)
check("…and each refusal says why",
      sum(1 for w in bad.warnings if "alpha" in w or "beta" in w
          or "gamma" in w or "nosuch" in w) == 4)
check("exporting into the mod itself is an error",
      cards.plan_cleanup(mod, cards.cleanup_request_from_dict(
          {"target": str(root / "out")})).errors)

print("\n== applying it ==")
rec = cards.apply_cleanup(plan)
data = root / "data"
check("the merc copy exists and is the right picture",
      (data / "ui/units/mercs/#alpha.tga").read_bytes() == b"alpha-card"
      and (data / "ui/unit_info/merc/alpha_info.tga").read_bytes() == b"alpha-info")
check("the chosen beta card is the england one",
      (data / "ui/units/mercs/#beta.tga").read_bytes() == b"beta-card-england")
check("the faction copies are gone",
      not (data / "ui/units/england/#alpha.tga").exists()
      and not (data / "ui/units/france/#alpha.tga").exists()
      and not (data / "ui/units/france/#beta.tga").exists())
check("the delta merc copy is still there, untouched",
      (data / "ui/units/mercs/#delta.tga").read_bytes() == b"delta-card"
      and not (data / "ui/units/england/#delta.tga").exists())
check("the pinned unit's cards are both still where they were",
      (data / "ui/units/england/#gamma.tga").exists()
      and (data / "ui/units/france/#gamma.tga").exists())
check("the agent pictures are untouched",
      (data / "ui/units/england/spy.tga").exists()
      and (data / "ui/units/england/diplomat.tga").exists())
check("the Lua-named card is untouched",
      (data / "ui/units/england/#runtime_hero.tga").exists())
check("the ghost art is out of the mod",
      not (data / "ui/units/england/#ghost.tga").exists()
      and not (data / "ui/unit_info/england/ghost_info.tga").exists())
check("the export folder holds both kinds, kept apart",
      (target / "unused_files/data/ui/units/england/#ghost.tga").read_bytes() == b"ghost-card"
      and (target / "data/ui/units/france/#alpha.tga").read_bytes() == b"alpha-card")
check("a README says what the folder is", (target / "README.txt").is_file())

print("\n== a second audit sees a tidy mod ==")
mod.drop_caches()
a2 = cards.audit(mod)
card2 = next(k for k in a2["kinds"] if k["kind"] == "card")
check("nothing is left to remove or consolidate",
      not card2["unused"] and not card2["duplicates"] and not card2["variants"])
check("…and the cards that stayed are counted as already merc-only",
      card2["already"] == 3)

print("\n== undo ==")
undo(rec["id"])
check("every file is back, byte for byte",
      all((data / rel).is_file() and (data / rel).read_bytes() == blob
          for rel, blob in ART.items()))
check("and the merc copies this run created are gone again",
      not (data / "ui/units/mercs/#alpha.tga").exists()
      and not (data / "ui/units/mercs/#beta.tga").exists()
      and not (data / "ui/unit_info/merc/alpha_info.tga").exists())

print("\n== a mod with no card folders at all ==")
bare = Path(tempfile.mkdtemp(prefix="ut_cards_bare_"))
(bare / "data").mkdir()
(bare / "data/export_descr_unit.txt").write_text(EDU, encoding="latin-1")
empty = cards.audit(Mod(bare))
check("says so rather than raising",
      all(k["dictionaries"] == 0 and k["unused"] == [] for k in empty["kinds"]))

print(f"\n{sum(ok)}/{len(ok)} checks - {'ALL PASSED' if all(ok) else 'FAILURES ABOVE'}")
sys.exit(0 if all(ok) else 1)
