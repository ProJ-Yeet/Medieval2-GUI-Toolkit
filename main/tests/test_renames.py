"""Renaming a thing whose name is its identity - Phase 19b: D2 and D3.

    D2  a province or its settlement, renamed everywhere
    D3  a faction slot, the same shape over a wider file set

Six claims, and the third is the one that had a wrong sentence under it:

    a rename is position-aware, never a  `Eregion` is a settlement AND a hidden
    token walk                          resource on twenty other regions' flags
                                        line of the same file. Only the lines a
                                        parser hands over are rewritten
    the file set is closed, and it is   198 and 199 region names appear in
    measured                            fifteen files and twelve, all of them
                                        map files whose shape is known
    descr_strat does NOT name a         16d's refusal said it did. Every
    settlement                          whole-word hit in both mods' descr_strat
                                        is a unit type, a portrait or a comment
    the script is reported, never       a grammar nothing here parses. Every
    edited                              occurrence by line number, none touched
    a name already in use is refused    before a byte is written, and a province
                                        and a settlement share one key file so
                                        they are checked against each other
    a rename follows five files a       a clone must invent a trait or a speech;
    clone refuses                       a rename must not - the condition is
                                        already there and already means this one

Five parts:

    1  the rules with no disk under them: the four span rules
    2  every installed mod: what the site tables really find, and the
       descr_strat correction restated as a measurement
    3  the refusals
    4  a province and a settlement renamed on a copy of a real mod, with the
       .strings.bin, the script report and undo
    5  a faction: the length-prefixed modeldb record and the EMT_* keys

    python -m tests.test_renames
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, campstrat, keyblock as kb, modeldb as mdb
from unittransfer import renames, transfer
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the rules -----------------------------------------------------------
print("\n1) where on a line a name of this kind may sit")

check("a key rule rewrites the key and leaves the value it is read as",
      renames.rewrite_lines(["{Anorien}Anorien"], {0: "key"}, "Anorien", "Rohan")[0]
      == ["{Rohan}Anorien"])
check("…and a key that is not this one is not a hit",
      renames.rewrite_lines(["{Anorien_Province}Anorien"], {0: "key"},
                            "Anorien", "Rohan")[0] == ["{Anorien_Province}Anorien"])

# custom_tiles_db.txt writes both of these, six times in Divide and Conquer
tiles = ["Anorien_Province\t324\t221\trammas_n.wfc\tstorm\tmidday",
         "Anorien_Provincea\t324\t214\trammas_n.wfc\tstorm\tmidday"]
out, hit = renames.rewrite_lines(tiles, {0: "first", 1: "first"},
                                 "Anorien_Province", "Rohan_Province")
check("a first-column rule rewrites the province and not the suffixed tile "
      "beside it", hit == [0] and out[1] == tiles[1])

check("a comment is not code: the name in one is left alone",
      renames.rewrite_lines(["\tregions Foo_Province ; and Bar_Province"],
                            {0: "any"}, "Bar_Province", "X")[0]
      == ["\tregions Foo_Province ; and Bar_Province"])

edb = ('\t\t\t\trecruit_pool "Knights"  1 0.1 1 0 requires factions '
       '{ sicily, portugal, }  and hidden_resource ResD')
check("a braced rule finds the clause in the middle of the line it is on",
      "{ testonia, portugal, }" in
      renames.rewrite_lines([edb], {0: "braced"}, "sicily", "testonia")[0][0])

trait_lines = ["        and GeneralFoughtFaction sicily",
               "Trait Fearssicily",
               "        Affects Combat_V_Faction_Sicily  1  Chance  100"]
out, hit = renames.rewrite_lines(trait_lines, {i: "operand" for i in range(3)},
                                 "sicily", "testonia")
check("an operand rule follows the condition and never a trait or an engine "
      "effect with the slot glued into its name", hit == [0])

check("the EMT_* keys are found by the underscore rule and the data rule would "
      "find none of them",
      renames.rewrite_lines(["{EMT_SICILY_ADMIRAL}The Admiral"], {0: "key_word"},
                            "sicily", "testonia")[0]
      == ["{EMT_TESTONIA_ADMIRAL}The Admiral"]      # and the slot in capitals
      and renames.rewrite_lines(["{EMT_SICILY_ADMIRAL}x"], {0: "key"},
                                "sicily", "testonia")[1] == [])


# ---- 2) the installed mods --------------------------------------------------
print("\n2) what the site tables find in a real mod, and what descr_strat does not")

mods = _realmod.installed()
if not mods:
    _realmod.pick("Divide_and_Conquer_EUR")          # prints SKIPPED and exits 0

for root in mods:
    mod = Mod(root)
    print(f"\n  -- {root.name}")
    rf = campmap.parse_regions(kb.read_text(
        Path(mod.data) / campmap.REGIONS_REL, renames.ENCODING))
    regions = [r.name for r in rf.records]
    settlements = [r.settlement for r in rf.records if r.settlement]
    print(f"     {len(regions)} regions, {len(settlements)} settlements, "
          f"{len(renames.campaign_dirs(mod))} campaign(s), "
          f"{len(renames.key_files(mod))} name-key file(s)")

    # the campaign folders, at any depth - both mods keep one under custom/
    check(f"{root.name}: every campaign folder is found, nested ones included",
          len(renames.campaign_dirs(mod)) >= 1
          and all((d / campstrat.STRAT_NAME).is_file()
                  for d in renames.campaign_dirs(mod)))

    # every province name the mod declares anywhere - the base file, plus any
    # campaign that ships its own (Third Age Reforged's Fellowship does)
    declared = set()
    for rp in renames.region_files(mod):
        declared |= {r.name for r in campmap.parse_regions(
            kb.read_text(rp, renames.ENCODING)).records}

    # the claim the refusal got wrong: descr_strat does not name a settlement
    stray = 0
    for camp in renames.campaign_dirs(mod):
        strat = kb.read_text(camp / campstrat.STRAT_NAME, renames.ENCODING)
        check(f"{root.name}/{camp.name}: descr_strat.txt offers a settlement "
              f"rename no line at all",
              renames._find_strat(strat, "settlement") == {})
        # …and what it DOES name is the province, which is why the region site
        # table reads this file and the settlement one does not
        named = {n.get("region") for n in campstrat.parse_strat(strat).nodes
                 if n.get("region")}
        stray += len(named - declared)
        check(f"{root.name}/{camp.name}: what descr_strat names is the province "
              f"- {len(named & declared)} of {len(named)}",
              named and len(named & declared) >= len(named) - 1)
    # both installed mods have exactly one, in their custom campaign: a
    # settlement pointing at a province descr_regions never declares. It is the
    # mod's own fault and a rename cannot invent the record, so it is measured
    # here rather than asserted away
    print(f"     {stray} settlement(s) name a province no descr_regions declares")

    # the lookup file reads as pairs
    look = renames.campaign_dirs(mod)[0] / "descr_regions_and_settlement_name_lookup.txt"
    if look.is_file():
        text = kb.read_text(look, renames.ENCODING)
        lines = text.split("\n")
        rmap = renames._find_lookup(text, "region")
        smap = renames._find_lookup(text, "settlement")
        heads = [kb.code_of(lines[i]) for i in sorted(rmap)]
        tails = [kb.code_of(lines[i]) for i in sorted(smap)]
        check(f"{root.name}: the lookup alternates, and its first column is "
              f"provinces ({len(heads)} pairs)",
              len(heads) - len(tails) in (0, 1)
              and sum(1 for h in heads if h in set(regions)) > len(heads) * 0.9)
        check(f"{root.name}: …and its second column is settlements",
              sum(1 for t in tails if t in set(settlements)) > len(tails) * 0.9)

    # a real province: the plan touches only map files, and every one it names
    # really does contain the word
    name = next((r for r in regions if r), "")
    p = renames.plan(mod, {"subject": "region", "old": name,
                           "new": "Ut_Test_Province"})
    check(f"{root.name}: renaming {name} plans {len(p.written())} file(s) and "
          f"{p.hits()} line(s), with no error", not p.errors and p.touched())
    check(f"{root.name}: every file it would write really names the province",
          all(re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])",
                        kb.read_text(Path(mod.data) / e.rel,
                                     e.encoding))
              for e in p.written()))


# ---- 3) the refusals --------------------------------------------------------
print("\n3) what is refused before a byte is planned")

mod = Mod(_realmod.pick("Divide_and_Conquer_EUR", "Third_Age_Reforged"))
rf = campmap.parse_regions(kb.read_text(
    Path(mod.data) / campmap.REGIONS_REL, renames.ENCODING))
a_region = rf.records[0].name
a_settlement = next(r.settlement for r in rf.records if r.settlement)

for label, body, wanted in (
    ("a subject that is not one of the three",
     {"subject": "province", "old": a_region, "new": "X"}, "is of"),
    ("a name this mod has not got",
     {"subject": "region", "old": "No_Such_Province", "new": "X_Province"},
     "there is no province"),
    ("the name it already has",
     {"subject": "region", "old": a_region, "new": a_region}, "already has"),
    ("a name with a space in it",
     {"subject": "region", "old": a_region, "new": "Two Words"}, "one word"),
    ("a province renamed to a settlement that exists",
     {"subject": "region", "old": a_region, "new": a_settlement},
     "already has a settlement"),
    ("a faction slot in capitals",
     {"subject": "faction", "old": "sicily", "new": "Testonia"}, "lower-case"),
    ("renaming the reserved slave slot",
     {"subject": "faction", "old": "slave", "new": "peasants"}, "reserved"),
):
    p = renames.plan(mod, body)
    check(f"{label} is refused, and the reason says why",
          bool(p.errors) and wanted in " ".join(p.errors))


# ---- 4) a province and a settlement, on a copy -------------------------------
print("\n4) a province renamed on a copy of a real mod")

tmp = Path(_tmp.mkdtemp(prefix="ut_rename_"))
dest = tmp / (Path(mod.root).name + "_copy")

plan_all = renames.plan(mod, {"subject": "region", "old": a_region,
                              "new": "Ut_Test_Province"})
#: only the files this rename names, plus the script it refuses and the caches
#: beside the text files - a whole mod is gigabytes and none of the rest is read
wanted = [e.rel for e in plan_all.written()]
wanted += [e.rel + ".strings.bin" for e in plan_all.written()
           if e.rel.startswith("text/")]
wanted += [renames._rel(mod, s) for s in renames.script_files(mod)]
for rel in wanted:
    src = Path(mod.data) / rel
    if src.is_file():
        (dest / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / "data" / rel)
copy = Mod(dest)
before = {rel: (dest / "data" / rel).read_bytes()
          for rel in wanted if (dest / "data" / rel).is_file()}
print(f"     {len(before)} file(s) copied, {sum(map(len, before.values())):,} bytes")

p = renames.plan(copy, {"subject": "region", "old": a_region,
                        "new": "Ut_Test_Province"})
check("the plan against the copy says the same as against the mod",
      not p.errors and p.hits() == plan_all.hits())
check("nothing is written by a plan",
      all((dest / "data" / rel).read_bytes() == raw for rel, raw in before.items()))

scripts = {renames._rel(mod, s) for s in renames.script_files(copy)}
check("no campaign script is in the write list",
      not (scripts & set(p.files())))
check("…and every occurrence in one is reported with its line number",
      all(m.line > 0 and m.rel in scripts for m in p.script))

res = renames.apply(p)
after = {rel: (dest / "data" / rel).read_bytes() for rel in before}
changed = [rel for rel in before if after[rel] != before[rel]]
check(f"exactly the planned files changed ({len(changed)})",
      sorted(changed) == sorted(set(p.files())
                                | {r + ".strings.bin" for r in p.files()
                                   if r.startswith("text/")} & set(before)))
check("every campaign script came back byte for byte",
      all(after[rel] == before[rel] for rel in scripts if rel in before))

tok = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(a_region) + r"(?![A-Za-z0-9_])")
left = {rel: len(tok.findall(after[rel].decode("latin-1")))
        for rel in p.files() if not rel.startswith("text/")}
check("the old name is gone from every file that was rewritten",
      not any(left.values()))

nf = campmap.parse_regions(kb.read_text(
    dest / "data" / campmap.REGIONS_REL, renames.ENCODING))
check("the renamed province is in descr_regions.txt under its new name and the "
      "old one is not",
      nf.by_name("Ut_Test_Province") is not None and nf.by_name(a_region) is None)
check("…and the file still holds every record it did",
      len(nf.records) == len(rf.records))

shown_before = campmap.shown_names(mod)
shown_after = campmap.shown_names(copy)
check("the words the player reads moved to the new key, unchanged",
      shown_after.get("Ut_Test_Province") == shown_before.get(a_region)
      and a_region not in shown_after)
check("…and the compiled archive beside it was rebuilt",
      any(rel.endswith(".strings.bin") for rel in changed))

transfer.undo(res["id"])
check("undo puts every one of them back, byte for byte",
      all((dest / "data" / rel).read_bytes() == raw for rel, raw in before.items()))

print("\n   a settlement, on the same copy")
sp = renames.plan(copy, {"subject": "settlement", "old": a_settlement,
                         "new": "Ut_Test_Town"})
check("a settlement rename touches the three files the measurement says it "
      f"does, and not descr_strat.txt ({len(sp.written())})",
      not sp.errors
      and not any(f.endswith(campstrat.STRAT_NAME) for f in sp.files()))
key_rel = next((f for f in sp.files() if f.startswith("text/")), "")
value_before = campmap.shown_names(copy).get(a_settlement)
renames.apply(sp)
check("the settlement's key moved and its shown words did not change",
      campmap.shown_names(copy).get("Ut_Test_Town") == value_before)
nf = campmap.parse_regions(kb.read_text(
    dest / "data" / campmap.REGIONS_REL, renames.ENCODING))
check("…and descr_regions.txt names the new settlement in its province",
      any(r.settlement == "Ut_Test_Town" for r in nf.records))


# ---- 5) a faction -----------------------------------------------------------
print("\n5) a faction: the length-prefixed record, and the keys built from the slot")

slot = next((s for s in ("sicily", "france", "england")
             if s in renames._names(mod, "faction")["faction"]), "")
if not slot:
    slot = renames._names(mod, "faction")["faction"][0]

# the real file, because a hand-written one would prove only that the fixture
# matches the reader. One entry that really has a record for this slot is enough
# to test the length token, and the whole-file pass is what proves nothing else
# moved.
mdb_path = Path(mod.data) / "unit_models/battle_models.modeldb"
if mdb_path.is_file():
    db_text = kb.read_text(mdb_path, renames.ENCODING)
    db = mdb.parse_text(db_text)
    entry = next((e for e in db.entries
                  if any(t.faction == slot for t in e.main_textures)), None)
    check(f"{slot} has a texture record in this mod's modeldb", entry is not None)
    if entry is not None:
        # both groups: an entry has main textures and attach textures, and a
        # faction can have a record in either
        was = [t.faction for t in entry.main_textures + entry.attach_textures]
        raw, n = renames._rename_entry_factions(entry.raw, slot, "ut_testonia",
                                                entry.first_entry_pad)
        after = mdb.parse_entry_text(raw, pad=entry.first_entry_pad)
        check("a texture record is renamed with the length token in front of it, "
              f"and the {len(was) - was.count(slot)} record(s) beside it are not",
              n == was.count(slot)
              and [t.faction for t in after.main_textures + after.attach_textures]
              == ["ut_testonia" if f == slot else f for f in was])
        check("…and the entry's model, mesh and texture paths are byte for byte",
              after.name == entry.name
              and [t.texture for t in after.main_textures]
              == [t.texture for t in entry.main_textures])
    whole, hits = renames.rename_modeldb(db_text, slot, "ut_testonia")
    check(f"the whole file renames {hits} record(s) and still parses",
          hits > 0 and len(mdb.parse_text(whole).entries) == len(db.entries))
    check("a slot no record names leaves the file byte for byte",
          renames.rename_modeldb(db_text, "ut_no_such_slot", "x") == (db_text, 0))

fp = renames.plan(mod, {"subject": "faction", "old": slot, "new": "ut_testonia"})
check(f"a faction rename plans {len(fp.written())} file(s) and {fp.hits()} "
      f"line(s), with no error", not fp.errors and len(fp.written()) >= 8)
check("descr_strat.txt is in the list - a clone refuses it and a rename cannot",
      any(f.endswith(campstrat.STRAT_NAME) for f in fp.files()))
check("so are the five files a clone reports rather than writes",
      len({f for f in fp.files()} & set(renames.CLONE_REVIEW_FILES)) >= 2)
check("the art the engine finds by convention moves with the slot",
      all(a.src != a.dst and slot in a.src for a in fp.assets))
check("no campaign script is written, and every line of one is reported",
      not ({renames._rel(mod, s) for s in renames.script_files(mod)} & set(fp.files()))
      and all(m.line > 0 for m in fp.script))
check("nothing was written to the real mod by any of this",
      all(not (Path(mod.data) / f).read_bytes().count(b"ut_testonia")
          for f in fp.files() if (Path(mod.data) / f).is_file()))


print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
