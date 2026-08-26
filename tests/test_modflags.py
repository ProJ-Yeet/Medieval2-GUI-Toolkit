"""The M2EX mark: what it turns off, and — more importantly — what it does not.

M2EX replaces the engine's hardcoded tables, so a mod that runs on it is over
several of the ceilings the toolkit checks against by design. The mark exists
because nothing in a mod's ``data/`` says which engine it runs on, and reporting
those ceilings anyway turned every check on such a mod into a page of findings
that were all deliberate.

The risk in a feature like this is that it becomes a mute button. So the gate
here is two-sided:

  * the ceiling findings go — and go for the right mod, since the mark is stored
    per mod root and two mods must not share it;
  * **every other finding stays.** A missing text key, a header line in the wrong
    order, an antitrait naming a trait the file does not define: none of those
    are things M2EX makes legal, and a mark that silenced them would be worse
    than no mark at all.

Needs no game install.

    python -m tests.test_modflags
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import (config, factions, flatrecord as fr, modflags,
                          traits, ancillaries)

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


cfg = Path(tempfile.mkdtemp(prefix="tk-flags-"))
config.CONFIG_DIR = cfg
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"


class FakeMod:
    """Just a root and a name — the mark is stored by path and reads nothing."""

    def __init__(self, root, name):
        self.root = Path(root)
        self.name = name

    @property
    def m2ex(self):
        return modflags.is_m2ex(self)


one = FakeMod(cfg / "ModOne", "ModOne")
two = FakeMod(cfg / "ModTwo", "ModTwo")

print("the mark itself")
check("a mod starts unmarked", not one.m2ex)
modflags.set_m2ex(one, True)
check("marking it sticks", one.m2ex)
check("and it is per mod — the other one is untouched", not two.m2ex)
check("the same folder spelled the other way is the same mod",
      modflags.is_m2ex(FakeMod(str(cfg / "ModOne").replace("\\", "/"), "again")))
modflags.set_m2ex(one, False)
check("unmarking it sticks too", not one.m2ex)


print("\nover the faction cap")
# 33 faction records: two past the vanilla 31
over = "".join(f"faction f{i}\n    culture northern_european\n    religion catholic\n\n"
               for i in range(33))
found = factions.check_file(fr.parse_records(factions.SHAPE, over), None)
caps = [f for f in found if f["kind"] == "too-many-factions"]
check("the check still fires for an ordinary mod", len(caps) == 1)
check("...naming the first faction past the end", caps[0]["name"] == "f31")
modflags.set_m2ex(one, True)
left = modflags.uncapped(found, one)
check("marked M2EX, the ceiling finding goes",
      not any(f["kind"] == "too-many-factions" for f in left))
check("and NOTHING else does", len(left) == len(found) - len(caps))
check("unmarked, the finding is back", len(modflags.uncapped(found, two)) == len(found))


print("\nthe other four ceilings, and the findings that are not ceilings")
TRAIT = (
    "Trait Overloaded\n"
    "    Characters family\n"
    "    AntiTraits " + ", ".join(f"Ghost{i}" for i in range(25)) + "\n"
    + "".join(
        f"\n    Level Over_{n}\n"
        f"        Description Over_{n}_desc\n"
        f"        EffectsDescription Over_{n}_ed\n"
        f"        Threshold {n}\n" for n in range(1, 12))
)
t_found = traits.check(traits.parse_block(TRAIT + "\n"), set())
kinds = {f["kind"] for f in t_found}
check("a trait over both of its ceilings reports both",
      {"too-many-levels", "too-many-antitraits"} <= kinds)
check("...and the antitraits it names that the file has not got, which is not a ceiling",
      "unknown-antitrait" in kinds)
t_left = {f["kind"] for f in modflags.uncapped(t_found, one)}
check("marked M2EX, both ceilings go",
      not ({"too-many-levels", "too-many-antitraits"} & t_left))
check("and the unknown antitrait stays — M2EX does not make that legal",
      "unknown-antitrait" in t_left)

ANC = (
    "Ancillary Overloaded\n"
    "    Type item\n"
    "    Transferable 2\n"                       # not 0 or 1: not a ceiling
    "    Image over.tga\n"
    "    Description over_desc\n"
    "    EffectsDescription over_ed\n"
    "    ExcludedAncillaries a, b, c, d, e\n"
    + "".join(f"    Effect Command {n}\n" for n in range(1, 11))
)
a_found = ancillaries.check(ancillaries.parse_block(ANC + "\n"))
a_kinds = {f["kind"] for f in a_found}
check("an ancillary over both of its ceilings reports both",
      {"too-many-excluded", "too-many-effects"} <= a_kinds)
a_left = {f["kind"] for f in modflags.uncapped(a_found, one)}
check("marked M2EX, both go",
      not ({"too-many-excluded", "too-many-effects"} & a_left))
check("and `Transferable 2` still stands — that is a wrong value, not a ceiling",
      "bad-transferable" in a_left)

check("every kind in the list is one a module actually raises",
      modflags.CAP_FINDINGS >= {"too-many-factions", "too-many-levels",
                                "too-many-antitraits", "too-many-excluded",
                                "too-many-effects"})

shutil.rmtree(cfg, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
