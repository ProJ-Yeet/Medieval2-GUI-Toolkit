"""96f: a faction's names for the pickers, first names and surnames apart.

Run:  python -m tests.test_namepool

One small mod with ``descr_names.txt`` and ``text/names.txt``: ``england`` has
all three lists, ``milan`` no surnames. What has to hold:

* **each list as [token, shown]**, the shown words from names.txt and empty
  where a token has none;
* **a faction with no surnames** gives an empty list, not a missing key;
* **a faction the file lacks, or no file**, says so and offers nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer import namekeys                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


NL = chr(13) + chr(10)
NAMES = """faction: england

	characters
		Edward
		Henry
	surnames
		Plantagenet
		de_Clare
	women
		Matilda

faction: milan

	characters
		Ottone
	women
		Bianca
"""
TEXT = """{Edward}Edward
{Henry}Henry
{Plantagenet}Plantagenet
{de_Clare}de Clare
{Matilda}Matilda
{Ottone}Ottone
"""

tmp = Path(_tmp.mkdtemp(prefix="ut_namepool_"))
data = tmp / "Here" / "data"
(data / "text").mkdir(parents=True)
kb.write_text(data / "descr_names.txt", NL.join(NAMES.split("\n")), "utf-8")
kb.write_text(data / "text" / "names.txt", NL.join(TEXT.split("\n")), "utf-16")
mod = Mod(tmp / "Here")

print("\n1) england")
p = namekeys.faction_pool(mod, "england")
check("read", p["have"] and "problem" not in p)
check("first names with their shown words",
      p["characters"] == [["Edward", "Edward"], ["Henry", "Henry"]])
check("surnames, a spaced one shown with its space",
      p["surnames"] == [["Plantagenet", "Plantagenet"], ["de_Clare", "de Clare"]])
check("women apart", p["women"] == [["Matilda", "Matilda"]])

print("\n2) milan, and what is not there")
m = namekeys.faction_pool(mod, "milan")
check("no surnames is an empty list", m["have"] and m["surnames"] == [])
check("a token with no text is shown empty", m["women"] == [["Bianca", ""]])
x = namekeys.faction_pool(mod, "france")
check("a faction the file lacks says so", not x["have"] and "france" in x["problem"])
(data / "descr_names.txt").unlink()
y = namekeys.faction_pool(Mod(tmp / "Here"), "england")
check("no descr_names.txt says so", not y["have"] and y["problem"] and y["characters"] == [])

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
