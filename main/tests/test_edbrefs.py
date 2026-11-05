"""Every ``requires`` clause in the EDB checked against what the mod declares.

`edbvocab` already knows every faction, culture, religion, trade resource and
hidden resource the mod declares, and the clause editor offers only those. A
clause that was typed by hand, or that came in with a building from another mod,
was never checked against the lists: the building just never becomes buildable
and the game says nothing. Mylae's editor checks every clause on export
(``buildingRequirementValidation.js``); this is the same sweep as tree rules.

What each part is here to catch:

  * **a name nothing declares is said, once**, with how many clauses name it
    and where the first one is - level requires, capability lines and the
    clauses `upgrades` entries carry.
  * **the engine reads these names case-blind**, so ``River`` against a
    declared ``river`` is not a finding.
  * **`all`, a culture or a faction** may stand in a `factions { }` list.
  * **a list the mod does not have is not checked**: with no
    ``descr_religions.txt`` nothing is said about religions, rather than every
    religion being called unknown.
  * **without a mod, the tree check runs as before** (the EDB import calls it
    that way).

    python -m tests.test_edbrefs
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import buildings as B
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


EDB = """hidden_resources river coast

building zz_forge
{
    levels zz_1 zz_2
    {
        zz_1 city requires factions { england, northern_european, saxonz, } and hidden_resource rivr
        {
            capability
            {
                recruit_pool "Peasants"  1  0.5  2  0  requires factions { saxonz, } and resource silvr
            }
            material wooden
            construction 2
            cost 600
            settlement_min village
            upgrades
            {
                zz_2 requires hidden_resource River and not region_religion catholc 50
            }
        }
        zz_2 city requires factions { all, } and resource silver and region_religion catholic 50
        {
            capability
            {
            }
            material wooden
            construction 2
            cost 600
            settlement_min village
            upgrades
            {
            }
        }
    }
    plugins
    {
    }
}
"""

edb = B.parse_text(EDB)
REFS = {"factions": {"england"}, "cultures": {"northern_european"},
        "religions": {"catholic", "orthodox"}, "resources": {"silver", "iron"}}

print("1) a name nothing declares")
got = B.tree_check(edb, refs=REFS)["findings"]
refs = {f["what"]: f for f in got if f["code"].startswith("ref.")}
check("the faction nobody declares is said", "faction|saxonz" in refs)
check("once, counting both clauses that name it", refs.get("faction|saxonz", {}).get("count") == 2)
check("and pointing at the first of them",
      refs.get("faction|saxonz", {}).get("line") == EDB.splitlines().index(
          "        zz_1 city requires factions { england, northern_european, saxonz, } and hidden_resource rivr") + 1)
check("a misspelt hidden resource", "hidden_resource|rivr" in refs)
check("a misspelt trade resource on a capability line", "resource|silvr" in refs)
check("a misspelt religion in an upgrades entry's clause", "religion|catholc" in refs)
check("and nothing else", set(refs) == {"faction|saxonz", "hidden_resource|rivr",
                                        "resource|silvr", "religion|catholc"})
check("a hidden resource is read case-blind (River is river)", "hidden_resource|river" not in refs)
check("all of them are warnings", {f["severity"] for f in refs.values()} == {"warn"})
check("the rules are listed even when they find nothing",
      {"ref.faction", "ref.hidden_resource", "ref.resource", "ref.religion"}
      <= {r["code"] for r in B.tree_check(B.parse_text(EDB.replace("rivr", "river")), refs=REFS)["rules"]})

print("\n2) what is not checked")
plain = B.tree_check(edb)["findings"]
check("without a mod or lists the tree check says nothing about references",
      not any(f["code"].startswith("ref.") for f in plain))
part = B.tree_check(edb, refs=dict(REFS, religions=None))["findings"]
check("a list the mod does not have is not checked",
      not any(f["code"] == "ref.religion" for f in part)
      and any(f["code"] == "ref.resource" for f in part))

print("\n3) read out of a mod")
root = Path(_tmp.mkdtemp(prefix="ut_refs_")) / "M"
(root / "data").mkdir(parents=True)
(root / "data" / B.EDB_REL).parent.mkdir(parents=True, exist_ok=True)
(root / "data" / B.EDB_REL).write_text(EDB, encoding="latin-1")
(root / "data" / "descr_sm_factions.txt").write_text(
    "faction\tengland\nculture\tnorthern_european\n", encoding="latin-1")
mod = Mod(root)
r = B.requires_refs(mod)
check("the factions come from descr_sm_factions.txt", "england" in (r["factions"] or set()))
check("and the cultures factions claim", "northern_european" in (r["cultures"] or set()))
check("a mod with no descr_religions.txt has no religion list", r["religions"] is None)
res = B.checks(mod)["tree"]["findings"]
check("the building screen's check runs them", any(f["what"] == "faction|saxonz" for f in res))
check("and leaves out what the mod cannot say", not any(f["code"] == "ref.religion" for f in res))
shutil.rmtree(root.parent, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
