"""96f: Health's check for a town that starts with two guild buildings.

Run:  python -m tests.test_guildrule

A campaign with two towns: London starts with a merchants' and a swordsmiths'
guild, York with one guild and a barracks. What has to hold:

* London is found, once, naming both guild lines and the campaign;
* York is not, since one guild and any other building is a working town;
* the rule is one Health runs (it is in crashrules' RULES).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import crashrules                                 # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def town(region, lines):
    out = (f"settlement\n{{\n\tlevel town\n\tregion {region}\n\tyear_founded 0\n\tpopulation 1500\n"
           f"\tplan_set default_set\n\tfaction_creator england\n")
    for line, level in lines:
        out += f"\tbuilding\n\t{{\n\t\ttype {line} {level}\n\t}}\n"
    return out + "}\n"


STRAT = ("campaign\t\timperial_campaign\nplayable\n\tengland\nend\nunlockable\nend\nnonplayable\nend\n\n"
         "start_date\t1080 summer\nend_date\t1530 winter\ntimescale\t2.00\n\n"
         "faction\tengland, comfortable caderyn\nai_label\t\tcatholic\ndenari\t2000\n"
         + town("London", [("guild_merchants_guild", "guild_merchants_guild"),
                           ("guild_swordsmiths_guild", "guild_swordsmiths_guild")])
         + town("York", [("guild_merchants_guild", "guild_merchants_guild"),
                         ("barracks", "town_watch")]))

tmp = Path(_tmp.mkdtemp(prefix="ut_guildrule_"))
home = tmp / "M" / "data" / "world" / "maps" / "campaign" / "imperial_campaign"
home.mkdir(parents=True)
(home / "descr_strat.txt").write_text(STRAT, encoding="latin-1")
mod = Mod(tmp / "M")

found = crashrules._two_guilds(mod)
check("London is found, once", [f.name for f in found] == ["London"])
check("  naming both guild lines and the campaign",
      "guild_merchants_guild" in found[0].message and "guild_swordsmiths_guild" in found[0].message
      and "imperial_campaign" in found[0].message)
check("  at the settlement's line", found[0].line > 1 and found[0].file.endswith("descr_strat.txt"))
check("the rule is one Health runs", any(r.code == "guild.two_in_town" for r in crashrules.RULES))

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
