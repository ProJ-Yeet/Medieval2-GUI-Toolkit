"""Strat-map mode — descr_model_strat.txt and data/models_strat.

Runs on a mod this file builds from scratch, so it needs no game install and
measures exactly the cases it is about:

  * the audit: which declared strat models nothing references, and which files
    under ``data/models_strat`` nothing names;
  * the safety nets — a model named in another ``descr_*.txt``, one named only by
    a ``.lua`` script, and one another entry borrows the sprite of, are all kept;
  * ``models_strat/residences`` is invisible to the whole pass, which is the one
    rule a settlement mod's disk depends on;
  * ``x.tga.dds`` and ``x.dds`` are the SAME texture as the ``x.tga`` a line
    names, so neither is ever reported as unnamed and both travel with a removal
    (the bug that would otherwise delete 387 MB of live art out of one mod);
  * cleanup: the block leaves the file with every other byte of it intact
    (CRLF included), its files are exported mirroring the mod's layout, a file a
    surviving model still names is left alone, and the export folder's
    ``removed_model_strat.txt`` holds exactly the blocks that went;
  * undo restores the mod byte-exact.

    python -m tests.test_stratmap
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import config, stratmap
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CRLF = "\r\n"

# Deliberately CRLF, tab-aligned, with trailing `;` comments and one ALL-CAPS
# extension — every shape a real file has, so "the bytes come back as they went
# in" is a claim about a realistic file rather than a tidy one.
STRAT = CRLF.join([
    "; the mod's strat models",
    "ignore_registry",
    "",
    "type\t\t\tused_general\t; drawn by half the map",
    "skeleton\t\tstrat_named_with_army",
    "scale\t\t\t0.7",
    "texture\t\t\tengland, models_strat/textures/used.tga",
    "model_flexi_m\t\tmodels_strat/used.CAS, max",
    "shadow_model_flexi\tmodels_strat/shared_shadow.cas, max",
    "",
    "type\t\t\tdead_general",
    "skeleton\t\tstrat_named_with_army",
    "texture\t\t\tengland, models_strat/textures/dead.tga",
    "model_flexi_m\t\tmodels_strat/dead.CAS, max",
    "shadow_model_flexi\tmodels_strat/shared_shadow.cas, max",
    "",
    "type\t\t\tnamed_general",
    "skeleton\t\tstrat_named_with_army",
    "model_flexi_m\t\tmodels_strat/named.CAS, max",
    "",
    "type\t\t\tlua_general",
    "skeleton\t\tstrat_named_with_army",
    "model_flexi_m\t\tmodels_strat/lua.CAS, max",
    "",
    "type\t\t\tsprite_source",
    "skeleton\t\tstrat_named_with_army",
    "model_flexi_m\t\tmodels_strat/sprite_source.CAS, max",
    "",
    "type\t\t\tsprite_borrower",
    "skeleton\t\tstrat_named_with_army",
    "model_sprite\t\tsprite_source",
    "model_flexi_m\t\tmodels_strat/borrower.CAS, max",
    "",
    "type\t\t\tcommented_general",
    "skeleton\t\tstrat_named_with_army",
    "model_flexi_m\t\tmodels_strat/commented.CAS, max",
    "",
]) + CRLF

CHARACTER = CRLF.join([
    "type\t\t\tnamed character",
    "faction\t\t\tengland",
    "strat_model\t\tused_general\t; 0 (Default)",
    "; strat_model\t\tcommented_general  <- parked behind a `;` for a patch",
    "battle_model\t\tsome_battle_model",
    "",
    "type\t\t\tspy",
    "faction\t\t\tengland",
    "strat_model\t\tsprite_borrower",
    "",
]) + CRLF

#: The over-cautious net: a name here is not a use, but it IS a reason to leave
#: the model alone and say where it was seen.
NAMES = "; a name list\r\nnamed_general\r\n"

LUA = "-- spawns a hero\nlocal m = 'lua_general'\nspawnCharacter(m)\n"

FACTIONS = CRLF.join([
    "faction\t\t\tengland",
    "symbol\t\t\tmodels_strat/symbol_england.CAS",
    "rebel_symbol\t\tmodels_strat/symbol_rebels.CAS",
    "",
]) + CRLF

CULTURES = "settlement\r\n\tnormal\tdata/models_strat/residences/village.CAS,\tlevel_1\r\n"

#: rel -> the bytes to put there. The point of each one is in the comment.
ASSETS = {
    # used_general's own art, and the shadow it SHARES with dead_general
    "models_strat/used.CAS": b"used-mesh",
    "models_strat/textures/used.tga": b"used-texture",
    "models_strat/shared_shadow.cas": b"shared-shadow",
    # dead_general's own art — this is what a cleanup should take
    "models_strat/dead.CAS": b"dead-mesh",
    "models_strat/textures/dead.tga": b"dead-texture",
    # …and the compressed twin of that texture, which no line names and which
    # must travel with it rather than being left behind or called an orphan
    "models_strat/textures/dead.tga.dds": b"dead-texture-dds",
    "models_strat/named.CAS": b"named-mesh",
    "models_strat/lua.CAS": b"lua-mesh",
    "models_strat/sprite_source.CAS": b"sprite-source-mesh",
    "models_strat/borrower.CAS": b"borrower-mesh",
    "models_strat/commented.CAS": b"commented-mesh",
    # named by descr_sm_factions.txt, not by any model block
    "models_strat/symbol_england.CAS": b"england-symbol",
    "models_strat/symbol_rebels.CAS": b"rebels-symbol",
    # the compressed twin of a texture a LIVING model names: must never be
    # reported as unnamed
    "models_strat/textures/used.tga.dds": b"used-texture-dds",
    # nothing at all names these two
    "models_strat/orphan.CAS": b"orphan-mesh",
    "models_strat/textures/orphan.tga": b"orphan-texture",
    # inside the one folder the whole module is blind to
    "models_strat/residences/village.CAS": b"village",
    "models_strat/residences/textures/village.tga": b"village-texture",
    "models_strat/residences/faction_variants/england/village.CAS": b"england-village",
}


def fresh_mod() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ut_strat_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    for rel, text in (("descr_model_strat.txt", STRAT),
                      ("descr_character.txt", CHARACTER),
                      ("descr_names.txt", NAMES),
                      ("descr_sm_factions.txt", FACTIONS),
                      ("descr_cultures.txt", CULTURES)):
        with open(data / rel, "w", encoding="latin-1", newline="") as fh:
            fh.write(text)
    (data / "export_descr_unit.txt").write_text("", encoding="latin-1")
    scripts = data / "scripts"
    scripts.mkdir()
    (scripts / "heroes.lua").write_text(LUA, encoding="utf-8")
    for rel, blob in ASSETS.items():
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
before_strat = (root / "data/descr_model_strat.txt").read_bytes()

print("\n== parsing keeps every byte ==")
sf = stratmap.strat_file(mod)
check("seven type blocks read", len(sf.entries) == 7)
check("the file rebuilds byte for byte, CRLF and all",
      sf.to_text().encode("latin-1") == before_strat)
check("a block's files are read off its lines",
      sf.by_name()["dead_general"].paths()
      == ["models_strat/textures/dead.tga", "models_strat/dead.cas",
          "models_strat/shared_shadow.cas"])
check("a `texture <faction>, <path>` line yields the faction too",
      sf.by_name()["used_general"].factions == ["england"])
check("`model_sprite <other type>` is read as a cross-reference",
      sf.by_name()["sprite_borrower"].sprite_of == "sprite_source")

print("\n== the audit ==")
a = stratmap.audit(mod)
unused = {u["entry"] for u in a["unused"]}
mentioned = {m["entry"]: m for m in a["mentioned"]}
check("the model no character names is the only unused one",
      unused == {"dead_general"})
check("a `strat_model` line keeps its model out of the unused list",
      "used_general" not in unused)
check("a strat_model line parked behind a `;` is not a use, but IS a mention "
      "— over-cautious on purpose, the same rule the BMDB cleanup follows",
      "commented_general" not in unused
      and mentioned.get("commented_general", {}).get("file") == "descr_character.txt")
check("a name in another descr_*.txt keeps a model, and says which file",
      mentioned.get("named_general", {}).get("file") == "descr_names.txt")
check("a name in a .lua script keeps a model",
      mentioned.get("lua_general", {}).get("lua") is True)
check("a model another entry borrows the sprite of is used, not merely mentioned",
      "sprite_source" not in unused and "sprite_source" not in mentioned)

orphans = {o["rel"] for o in a["orphans"]}
check("a file nothing names is an orphan",
      "models_strat/orphan.CAS" in orphans
      and "models_strat/textures/orphan.tga" in orphans)
check("a .CAS named only by descr_sm_factions.txt is NOT an orphan",
      not any("symbol_" in o for o in orphans))
check("the .tga.dds beside a named .tga is NOT an orphan",
      "models_strat/textures/used.tga.dds" not in orphans)
check("a dead model's own files are not orphans — they belong to the entry",
      "models_strat/dead.CAS" not in orphans)
check("nothing under models_strat/residences is ever listed",
      not any("residences" in o for o in orphans))
check("the scanned-file list names the campaign and descr files it read",
      "descr_sm_factions.txt" in a["scanned"] and "descr_names.txt" in a["scanned"])

print("\n== texture_siblings ==")
check("a .tga stands for all three spellings",
      stratmap.texture_siblings("models_strat/textures/x.tga")
      == ["models_strat/textures/x.tga", "models_strat/textures/x.tga.dds",
          "models_strat/textures/x.dds"])
check("so does the .tga.dds",
      set(stratmap.texture_siblings("MODELS_STRAT/Textures/X.TGA.DDS"))
      == set(stratmap.texture_siblings("models_strat/textures/x.dds")))
check("a mesh has only itself",
      stratmap.texture_siblings("models_strat/x.CAS") == ["models_strat/x.cas"])

print("\n== the plan ==")
target = Path(tempfile.mkdtemp(prefix="ut_strat_out_"))
shutil.rmtree(target)                       # it must be creatable, not existing
req = stratmap.cleanup_request_from_dict({
    "target": str(target), "entries": ["dead_general"],
    "orphans": ["models_strat/orphan.CAS", "models_strat/textures/orphan.tga"]})
plan = stratmap.plan_cleanup(mod, req)
exported = {rel for _src, rel in plan.exports}
check("no errors", not plan.errors)
check("the dead model's own mesh and texture are exported",
      "data/models_strat/dead.CAS" in exported
      and "data/models_strat/textures/dead.tga" in exported)
check("its unnamed .tga.dds twin goes with them",
      "data/models_strat/textures/dead.tga.dds" in exported)
check("the shadow a living model also names is LEFT in place",
      "models_strat/shared_shadow.cas" in plan.kept_files
      and not any("shared_shadow" in r for r in exported))
check("the two orphans go to unused_files/, kept apart from the entry's own art",
      "unused_files/data/models_strat/orphan.CAS" in exported
      and plan.orphan_count == 2)

print("\n== a request that is out of date is refused, not obeyed ==")
bad = stratmap.plan_cleanup(mod, stratmap.cleanup_request_from_dict(
    {"target": str(target), "entries": ["used_general", "named_general", "nonesuch"]}))
check("a model a character still names is not removed", not bad.entry_deletes)
check("…and the plan says why, per model", len(bad.warnings) >= 3)
check("a model that is not in the file any more is skipped, not fatal",
      any("nonesuch" in w for w in bad.warnings))
check("exporting into the mod itself is an error",
      stratmap.plan_cleanup(mod, stratmap.cleanup_request_from_dict(
          {"target": str(root / "backup"), "entries": []})).errors)

print("\n== applying it ==")
rec = stratmap.apply_cleanup(plan)
after = (root / "data/descr_model_strat.txt").read_bytes()
sf2 = stratmap.parse_file(root / "data/descr_model_strat.txt")
check("the block is gone from the file", "dead_general" not in sf2.by_name())
check("every other block is still there", len(sf2.entries) == 6)
check("the file is the old one minus exactly that block",
      after == before_strat.replace(
          CRLF.join([
              "type\t\t\tdead_general",
              "skeleton\t\tstrat_named_with_army",
              "texture\t\t\tengland, models_strat/textures/dead.tga",
              "model_flexi_m\t\tmodels_strat/dead.CAS, max",
              "shadow_model_flexi\tmodels_strat/shared_shadow.cas, max",
              "", ""]).encode("latin-1"), b""))
check("the removed files are out of the mod",
      not (root / "data/models_strat/dead.CAS").exists()
      and not (root / "data/models_strat/textures/dead.tga.dds").exists())
check("the shared shadow is still in the mod",
      (root / "data/models_strat/shared_shadow.cas").exists())
check("the residences tree is untouched",
      (root / "data/models_strat/residences/village.CAS").exists()
      and (root / "data/models_strat/residences/faction_variants/england/village.CAS").exists())
check("the export folder mirrors the mod's layout",
      (target / "data/models_strat/dead.CAS").read_bytes() == b"dead-mesh")
check("orphans land one folder deeper",
      (target / "unused_files/data/models_strat/orphan.CAS").exists())
check("a README says what the folder is", (target / "README.txt").is_file())

removed = stratmap.parse_file(target / stratmap.EXPORT_FILE_NAME)
check("the export's removed_model_strat.txt parses back",
      [e.name for e in removed.entries] == ["dead_general"])
check("…and holds the block verbatim",
      removed.entries[0].raw == stratmap.parse_text(
          before_strat.decode("latin-1")).by_name()["dead_general"].raw)

print("\n== undo ==")
undo(rec["id"])
check("descr_model_strat.txt is byte-exact again",
      (root / "data/descr_model_strat.txt").read_bytes() == before_strat)
check("every removed file is back, byte for byte",
      all((root / "data" / rel).is_file()
          and (root / "data" / rel).read_bytes() == blob
          for rel, blob in ASSETS.items()))

print("\n== a mod with no descr_model_strat.txt ==")
bare = Path(tempfile.mkdtemp(prefix="ut_strat_bare_"))
(bare / "data").mkdir()
(bare / "data/export_descr_unit.txt").write_text("", encoding="latin-1")
empty = stratmap.audit(Mod(bare))
check("says so rather than raising",
      empty["has_file"] is False and empty["entry_count"] == 0
      and empty["unused"] == [])

print(f"\n{sum(ok)}/{len(ok)} checks — {'ALL PASSED' if all(ok) else 'FAILURES ABOVE'}")
sys.exit(0 if all(ok) else 1)
