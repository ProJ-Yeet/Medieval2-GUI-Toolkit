"""The names a new record needs - Phase 19a: D4 and D5.

    D4  text/imperial_campaign_regions_and_settlement_names.txt
                                     what the campaign map calls a province
    D5  descr_names.txt + text/names.txt
                                     the pool a character's name comes out of,
                                     and the words the player reads for it

Five claims, and the third is the one that had a bug under it:

    a key is written, not invented   the province and its settlement are keyed
                                     by their own code names, and every region
                                     and settlement in both installed mods has
                                     a line - so a missing one is ours
    the .bin is the file that counts  the game reads the compiled archive, so a
                                     write that left it stale would show the old
                                     words and look like the tool did nothing
    descr_names has FOUR sections    `surnames` was missing from NAME_SECTIONS,
                                     and Third Age Reforged uses it: the heading
                                     and the name under it were both being read
                                     as characters. Demir and TWMapReader both
                                     say the word out loud
    a pool line alone is half a fix  3,583 of Divide and Conquer's 3,583 pool
                                     names have a key in text/names.txt, so both
                                     files are one job and one undo
    a name splits on spaces, never   the pool holds `The_Dark_Lord` as one entry
    on underscores                   and descr_strat writes it as one word

Five parts:

    1  the rules with no disk under them: name_parts and clean_value
    2  the fourth section, and what it changes about a real file
    3  every installed mod: what is keyed and what is not
    4  D4 against a copy of a real mod, .bin and undo included
    5  D5 against a copy: two files, one backup set

    python -m tests.test_namekeys
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campmap, keyblock as kb, minorfiles, namekeys, stringsbin
from unittransfer import transfer
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the rules -----------------------------------------------------------
print("\n1) how a name splits, and what a {key}value line may hold")

check("one word is a first name and no surname",
      namekeys.name_parts("Baldwin") == ("Baldwin", ""))
check("an underscored token stays ONE part - the pool holds it that way",
      namekeys.name_parts("The_Dark_Lord") == ("The_Dark_Lord", ""))
check("two words are a first name and a surname",
      namekeys.name_parts("Baldwin Brienne") == ("Baldwin", "Brienne"))
check("three: the last is the surname and the rest joins with an underscore, "
      "which is the token the two files are keyed by",
      namekeys.name_parts("Jean de Brienne") == ("Jean_de", "Brienne"))
check("nothing at all is two empty halves rather than a crash",
      namekeys.name_parts("   ") == ("", ""))

for bad, why in (("", "a blank name"), ("Two\nLines", "a line break"),
                 ("Cur{ly}", "a brace, which is what separates key from text")):
    try:
        namekeys.clean_value(bad, "name")
        check(f"{why} is refused", False)
    except namekeys.NameKeyError as exc:
        check(f"{why} is refused: {str(exc)[:52]}…", True)
check("and an ordinary name with spaces and accents in it is fine",
      namekeys.clean_value("  Annúnlond  ", "name") == "Annúnlond")


# ---- 2) the fourth section --------------------------------------------------
print("\n2) descr_names.txt has four sections, not three")

check("NAME_SECTIONS names all four", set(minorfiles.NAME_SECTIONS)
      == {"settlements", "characters", "surnames", "women"})

FOUR = ("faction: orcs\n"
        "\n"
        "\tcharacters\n\t\tGorbag\n\t\tShagrat\n"
        "\n"
        "\tsurnames\n\t\tChan\n"
        "\n"
        "\twomen\n\t\tShelob\n")
nf = minorfiles.parse_names(FOUR)
fac = nf.factions[0]
check("a surnames heading is a heading, not a character called `surnames`",
      [(s.name, [e.value for e in s.entries]) for s in fac.sections]
      == [("characters", ["Gorbag", "Shagrat"]), ("surnames", ["Chan"]),
          ("women", ["Shelob"])])
check("and the file still comes back byte for byte", nf.text() == FOUR)

added = minorfiles.render_names(FOUR.rstrip("\n"),
                               {"sections": {"characters":
                                             ["Gorbag", "Shagrat", "Muzgash"]}})
check("a name appended to `characters` lands under that heading, not under the "
      "one after it",
      added.split("\n")[:6] == FOUR.split("\n")[:5] + ["\t\tMuzgash"])
check("…and every other line of the block is untouched",
      [ln for ln in added.split("\n") if ln.strip() != "Muzgash"]
      == FOUR.rstrip("\n").split("\n"))

fresh = minorfiles.new_names({"name": "elves",
                              "sections": {"characters": ["Elrond"],
                                           "surnames": ["Peredhil"]}})
check("a faction written from scratch can carry a surnames list",
      minorfiles.parse_names(fresh + "\n").factions[0].section("surnames")
      is not None)


# ---- 3) every installed mod -------------------------------------------------
print("\n3) every installed mod: what has a name and what has a token")

mods = _realmod.installed()
if not mods:
    print("  (no mod installed - nothing to measure)")
for root in mods:
    mod = Mod(root)
    print(f"\n  -- {root.name}")
    state = namekeys.loc_state(mod, namekeys.REGION_NAMES_REL)
    if not (state["txt"] or state["bin"]):
        print("     no region-name file and no archive - the stock game's is "
              "inside a .pack")
    else:
        pairs = namekeys.loc_pairs(mod, namekeys.REGION_NAMES_REL)
        try:
            rf = campmap.read_regions(mod)
        except campmap.MapError:
            rf = None
        if rf is not None:
            want = {r.name for r in rf.records} | {r.settlement for r in rf.records
                                                   if r.settlement}
            missing = sorted(want - set(pairs))
            check(f"{len(pairs)} keys cover all {len(want)} region and "
                  f"settlement names" + (f" - missing {missing[:3]}" if missing
                                         else ""),
                  not missing)
            one = next(iter(rf.records))
            got = namekeys.region_names(mod, one.name)
            check(f"the panel's view of `{one.name}` names both keys and says "
                  f"whether each is set",
                  got["have"] and [r["slot"] for r in got["rows"]]
                  == (["region", "settlement"] if one.settlement else ["region"]))

    pool_path = Path(mod.data) / namekeys.POOL_REL
    if not pool_path.is_file():
        print("     no descr_names.txt - the stock game's is packed too")
        continue
    nf = minorfiles.parse_names(kb.read_text(pool_path, namekeys.ENCODING))
    check(f"descr_names.txt: {len(nf.factions)} factions, and the whole file "
          f"comes back byte for byte",
          nf.text() == kb.read_text(pool_path, namekeys.ENCODING))
    tokens = set()
    for f in nf.factions:
        for s in f.sections:
            if s.name in ("characters", "women", "surnames"):
                tokens |= {e.value for e in s.entries}
    keys = namekeys.loc_pairs(mod, namekeys.POOL_LOC_REL)
    if not keys:
        print("     no text/names.txt and no archive, so nothing can be called "
              "untranslated")
        continue
    absent = sorted(tokens - set(keys))
    check(f"{len(tokens)} pool names and {len(keys)} text keys: "
          f"{len(tokens) - len(absent)} of them are localised"
          + (f", {absent[:3]} are not" if absent else ""),
          len(absent) * 200 < len(tokens))     # a handful, never a whole file
    fac = next(f for f in nf.factions if f.section("characters")
               and f.section("characters").entries)
    who = fac.section("characters").entries[0].value
    view = namekeys.pool_view(mod, fac.name, who, "male")
    check(f"pool_view finds `{who}` already in {fac.name}'s characters list",
          view["have"] and view["parts"]
          and view["parts"][0]["in_pool"] and view["parts"][0]["section"]
          == "characters")
    view = namekeys.pool_view(mod, fac.name, "Nobodyexpectsthis", "female")
    check("…and puts a woman's name nobody has in the `women` list",
          view["parts"][0]["section"] == "women"
          and not view["parts"][0]["in_pool"])


# ---- 4) D4 against a copy ---------------------------------------------------
print("\n4) a region-name save against a copy of a real mod")

src = _realmod.pick("Third_Age_Reforged",
                    need=campmap.REGION_NAMES_REL)
tmp = Path(_tmp.mkdtemp(prefix="ut_namekeys_"))
dest = tmp / src.name
(dest / "data" / "text").mkdir(parents=True)
(dest / "data" / campmap.BASE_REL).mkdir(parents=True)
shutil.copy2(src / "data" / campmap.REGIONS_REL,
             dest / "data" / campmap.REGIONS_REL)
for rel in (campmap.REGION_NAMES_REL, campmap.REGION_NAMES_REL + ".strings.bin"):
    if (src / "data" / rel).exists():
        shutil.copy2(src / "data" / rel, dest / "data" / rel)
mod = Mod(dest)
rf = campmap.read_regions(mod)
region = rf.records[0]

txt_before = (dest / "data" / campmap.REGION_NAMES_REL).read_bytes()
p = namekeys.plan(mod, {"what": "region_names", "region": region.name,
                        "edits": {"region": "Testshire"}})
check("a save plans one key and names the file it goes in",
      p.payload()["ok"] and p.files() == [campmap.REGION_NAMES_REL]
      and p.loc_writes[campmap.REGION_NAMES_REL] == {region.name: "Testshire"})
check("nothing is written by a plan",
      (dest / "data" / campmap.REGION_NAMES_REL).read_bytes() == txt_before)

same = namekeys.plan(mod, {"what": "region_names", "region": region.name,
                           "edits": {"region": namekeys.loc_pairs(
                               mod, campmap.REGION_NAMES_REL)[region.name]}})
check("retyping the name that is already there is not a write",
      not same.payload()["ok"] and same.errors == ["nothing to change"])

blank = namekeys.plan(mod, {"what": "region_names", "region": region.name,
                            "edits": {"region": "  "}})
check(f"a blank name is refused with the reason: {blank.errors[0][:46]}…",
      blank.errors and "cannot be blank" in blank.errors[0])
nowhere = namekeys.plan(mod, {"what": "region_names", "region": "Nowhere",
                              "edits": {"region": "X"}})
check(f"a region the file has not got is refused: {nowhere.errors[0][:44]}…",
      nowhere.errors and "no region called" in nowhere.errors[0])

res = namekeys.apply(p)
check("the .txt is written",
      (dest / "data" / campmap.REGION_NAMES_REL).read_bytes() != txt_before)
check("only the one line changed",
      sum(1 for a, b in zip(
          txt_before.decode("utf-16").splitlines(),
          (dest / "data" / campmap.REGION_NAMES_REL)
          .read_bytes().decode("utf-16").splitlines()) if a != b) == 1)
check("the panel reads the new name back",
      campmap.shown_names(mod)[region.name] == "Testshire")
compiled = stringsbin.load_pairs(
    dest / "data" / (campmap.REGION_NAMES_REL + ".strings.bin"))
check("…and so does the compiled archive, which is the one the game reads",
      compiled[region.name] == "Testshire")
check("both files are in the one backup set",
      sorted(res["record"]["manifest"]["backed_up"])
      == sorted([campmap.REGION_NAMES_REL,
                 campmap.REGION_NAMES_REL + ".strings.bin"]))
check("the log records it as a namekeys job",
      res["record"]["mode"] == "namekeys"
      and res["record"]["action"] == "region_names")
transfer.undo(res["id"])
check("undo puts the .txt back byte for byte",
      (dest / "data" / campmap.REGION_NAMES_REL).read_bytes() == txt_before)

# a key the file has NOT got - the wizard's own output, and the case 16f reports
new_key = namekeys.plan(mod, {"what": "region_names", "region": region.name,
                              "edits": {"settlement": "Brand New"}})
was = namekeys.loc_pairs(mod, campmap.REGION_NAMES_REL)
if region.settlement in was:
    print(f"     ({region.settlement} already has a key, so `new` is a change)")
check("a settlement name is written under the settlement's own key",
      new_key.payload()["ok"]
      and list(new_key.loc_writes[campmap.REGION_NAMES_REL])
      == [region.settlement])


# ---- 5) D5 against a copy ---------------------------------------------------
print("\n5) a name-pool save against a copy: two files, one backup set")

psrc = _realmod.pick("Third_Age_Reforged", need="descr_names.txt")
pdest = tmp / (psrc.name + "_pool")
(pdest / "data" / "text").mkdir(parents=True)
shutil.copy2(psrc / "data" / namekeys.POOL_REL, pdest / "data" / namekeys.POOL_REL)
for rel in (namekeys.POOL_LOC_REL, namekeys.POOL_LOC_REL + ".strings.bin"):
    if (psrc / "data" / rel).exists():
        shutil.copy2(psrc / "data" / rel, pdest / "data" / rel)
pmod = Mod(pdest)
pool_before = (pdest / "data" / namekeys.POOL_REL).read_bytes()
names_before = (pdest / "data" / namekeys.POOL_LOC_REL).read_bytes()
faction = minorfiles.parse_names(
    kb.read_text(pdest / "data" / namekeys.POOL_REL, namekeys.ENCODING)
).factions[0].name

pp = namekeys.plan(pmod, {"what": "name_pool", "faction": faction,
                          "name": "Testarossa", "gender": "male"})
check("a pool save plans both files at once",
      pp.payload()["ok"]
      and pp.files() == sorted([namekeys.POOL_REL, namekeys.POOL_LOC_REL]))
check("nothing is written by a plan",
      (pdest / "data" / namekeys.POOL_REL).read_bytes() == pool_before)

no_fac = namekeys.plan(pmod, {"what": "name_pool", "faction": "no_such_faction",
                              "name": "Testarossa"})
check(f"a faction with no block is refused, and says where to add one: "
      f"{no_fac.errors[0][:44]}…",
      no_fac.errors and "has no `faction:" in no_fac.errors[0])
no_name = namekeys.plan(pmod, {"what": "name_pool", "faction": faction,
                               "name": ""})
check("a save with no name at all is refused",
      no_name.errors and "a name is needed" in no_name.errors[0])

pres = namekeys.apply(pp)
after = minorfiles.parse_names(
    kb.read_text(pdest / "data" / namekeys.POOL_REL, namekeys.ENCODING))
sec = after.get(faction).section("characters")
check("the name is the last entry of that faction's characters list",
      sec.entries[-1].value == "Testarossa")
before_nf = minorfiles.parse_names(pool_before.decode(namekeys.ENCODING)
                                   .replace("\r\n", "\n"))
check("exactly one line was added and no other line changed",
      len(after.lines) == len(before_nf.lines) + 1)
keys = namekeys.loc_pairs(pmod, namekeys.POOL_LOC_REL)
check("…and it has a text key, so the player reads a name and not the token",
      keys["Testarossa"] == "Testarossa")
compiled = stringsbin.load_pairs(
    pdest / "data" / (namekeys.POOL_LOC_REL + ".strings.bin"))
check("the compiled archive the game reads has it too",
      compiled.get("Testarossa") == "Testarossa")
check("three files in one backup set: the pool, the text and its archive",
      sorted(pres["record"]["manifest"]["backed_up"])
      == sorted([namekeys.POOL_REL, namekeys.POOL_LOC_REL,
                 namekeys.POOL_LOC_REL + ".strings.bin"]))
transfer.undo(pres["id"])
check("one undo puts both files back byte for byte",
      (pdest / "data" / namekeys.POOL_REL).read_bytes() == pool_before
      and (pdest / "data" / namekeys.POOL_LOC_REL).read_bytes() == names_before)

# a woman's name goes in the other list, and a two-part name in two lists
wp = namekeys.plan(pmod, {"what": "name_pool", "faction": faction,
                          "name": "Testella", "gender": "female",
                          "edits": {"Testella": "Testella the Fair"}})
namekeys.apply(wp)
after = minorfiles.parse_names(
    kb.read_text(pdest / "data" / namekeys.POOL_REL, namekeys.ENCODING))
check("a female character's name goes in `women`, not in `characters`",
      after.get(faction).section("women").entries[-1].value == "Testella"
      and all(e.value != "Testella"
              for e in after.get(faction).section("characters").entries))
check("…and the typed display name is what the text key says",
      namekeys.loc_pairs(pmod, namekeys.POOL_LOC_REL)["Testella"]
      == "Testella the Fair")

two = namekeys.plan(pmod, {"what": "name_pool", "faction": faction,
                           "name": "Testo Rossi", "gender": "male"})
namekeys.apply(two)
after = minorfiles.parse_names(
    kb.read_text(pdest / "data" / namekeys.POOL_REL, namekeys.ENCODING))
sur = after.get(faction).section("surnames")
check("a two-part name writes the first half and the surname to their own lists",
      after.get(faction).section("characters").entries[-1].value == "Testo"
      and sur is not None and sur.entries[-1].value == "Rossi")
check("…and both halves are keyed in text/names.txt",
      set(namekeys.loc_pairs(pmod, namekeys.POOL_LOC_REL))
      >= {"Testo", "Rossi"})

again = namekeys.plan(pmod, {"what": "name_pool", "faction": faction,
                             "name": "Testo Rossi", "gender": "male"})
check("adding the same name twice is refused as nothing to change, with the "
      "reason on both halves",
      again.errors == ["nothing to change"] and len(again.warnings) == 2)


print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
