"""The diplomacy section of descr_strat.txt, checked (:mod:`unittransfer.diplocheck`).

The rules are Mylae's (``validateCampaignDiplomacy.js``,
``diplomacyRelationRules.js``, ``clientStateRules.js``). Two halves: one broken
line per rule over a small campaign, then every installed campaign, where the
stock game's own file must come back clean.

    python -m tests.test_diplocheck
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campstrat, diplocheck, factions as facfile
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


HEAD = """campaign imperial_campaign
playable
\tengland
\tfrance
end
nonplayable
\tslave
end
faction england, balanced smith
\tdenari 1000
faction france, balanced smith
\tdenari 1000
faction slave, comfort caesar
\tdenari 1000
"""
KNOWN = {"england", "france", "scotland", "milan", "slave"}


def run(lines, known=KNOWN, m2ex=False, clients=False):
    sf = campstrat.parse_strat(HEAD + "\n".join(lines) + "\n")
    return diplocheck.check(sf, known, m2ex, clients)


def codes(got):
    return sorted({(i.code, i.severity) for i in got})


print("\n1) a clean diplomacy section reports nothing")
clean = ["faction_standings england, 0.5 france, scotland",
         "faction_standings france, -0.25 england",
         "faction_relationships england, at_war_with scotland",
         "faction_relationships france, allied_to milan"]
check(f"nothing found, got {codes(run(clean))}", not run(clean))
check("one at_war_with line is the whole relation: no second line asked for",
      not run(["faction_relationships england, at_war_with france"]))
check("the same standing given twice with one value is not reported",
      not run(["faction_standings england, 0.5 france",
               "faction_standings england, 0.5 france"]))

print("\n2) one break per rule")
got = run(["faction_standings england, 0.5 frnace"])
check("a misspelt faction is strat.diplomacy_faction",
      codes(got) == [("strat.diplomacy_faction", "warn")] and "frnace" in got[0].message)
check("the name check is skipped when the factions file could not be read",
      not run(["faction_standings england, 0.5 frnace"], known=None))
check("a standing toward itself is a contradiction",
      codes(run(["faction_standings england, 0.5 england"]))
      == [("strat.diplomacy_contradiction", "warn")])
check("a relation toward itself is a contradiction",
      codes(run(["faction_relationships france, allied_to france"]))
      == [("strat.diplomacy_contradiction", "warn")])
got = run(["faction_standings england, 1.5 france"])
check("a standing of 1.5 is strat.standing_range",
      codes(got) == [("strat.standing_range", "warn")] and "1.5" in got[0].message)
got = run(["faction_standings england, 0.5 france",
           "faction_standings england, -0.5 france"])
check("one standing given two values is a note naming the first line",
      codes(got) == [("strat.diplomacy_contradiction", "note")]
      and got[0].line == HEAD.count("\n") + 2 and "-0.5" in got[0].message)
got = run(["faction_relationships england, allied_to france",
           "faction_relationships france, at_war_with england"])
check("allied on one line and at war on another names the winner",
      codes(got) == [("strat.diplomacy_contradiction", "warn")]
      and "at_war_with holds" in got[0].message)
check("a word the game has no relation for is fatal",
      codes(run(["faction_relationships england, friends_with france"]))
      == [("strat.diplomacy_word", "fatal")])

print("\n3) M2EX's subjects")
sub = ["faction_relationships scotland, protectorate_of england"]
check("protectorate_of on a mod not marked M2EX is fatal",
      codes(run(sub)) == [("strat.diplomacy_word", "fatal")])
check("protectorate_of on an M2EX mod is clean", not run(sub, m2ex=True))
cl = ["faction_relationships scotland, client_of england"]
check("client_of with client_status_enable off is a warning",
      codes(run(cl, m2ex=True)) == [("strat.diplomacy_word", "warn")])
check("client_of with it on is clean", not run(cl, m2ex=True, clients=True))
got = run(["faction_relationships scotland, protectorate_of england, france"],
          m2ex=True)
check("two overlords is strat.subject_chain",
      codes(got) == [("strat.subject_chain", "warn")])
got = run(["faction_relationships scotland, protectorate_of england",
           "faction_relationships scotland, client_of england"], m2ex=True, clients=True)
check("a client and a protectorate at once is strat.subject_chain",
      codes(got) == [("strat.subject_chain", "warn")])
got = run(["faction_relationships scotland, protectorate_of england",
           "faction_relationships milan, protectorate_of scotland"], m2ex=True)
check("a subject's subject is strat.subject_chain and names the middle one",
      codes(got) == [("strat.subject_chain", "warn")] and "scotland" in got[0].message)
got = run(["faction_relationships scotland, protectorate_of england",
           "faction_relationships england, protectorate_of scotland"], m2ex=True)
check("a cycle is reported as a chain", any(i.code == "strat.subject_chain" for i in got))
got = run(["faction_relationships scotland, protectorate_of england",
           "faction_relationships england, at_war_with scotland"], m2ex=True)
check("a subject at war with its overlord is reported twice over: the "
      "contradiction and the chain",
      codes(got) == [("strat.diplomacy_contradiction", "warn"),
                     ("strat.subject_chain", "warn")])

print("\n4) descr_ex.txt's client_status_enable")
tmp = _tmp.mkdtemp("ut_diplo_")
data = Path(tmp) / "mods" / "m" / "data"
data.mkdir(parents=True)
mod = Mod(data.parent)
check("absent file: off", not diplocheck.clients_enabled(mod))
(data / "descr_ex.txt").write_text("; x\nclient_status_enable false\n", encoding="latin-1")
check("false: off", not diplocheck.clients_enabled(mod))
(data / "descr_ex.txt").write_text("client_status_enable\ttrue ; on\n", encoding="latin-1")
check("true: on", diplocheck.clients_enabled(mod))

print("\n5) the stock game's campaigns and every installed mod")
game = _realmod.MODS.parent
roots = ([game] if (game / "data" / campstrat.CAMPAIGN_DIR_REL).is_dir() else []) + [
    r for r in _realmod.installed()
    if (r / "data" / campstrat.CAMPAIGN_DIR_REL).is_dir()]
if not roots:
    print("  SKIPPED - no game or mod with a campaign installed")
for root in roots:
    mod = Mod(root)
    try:
        rf = facfile.parse_file(facfile.path_for(mod))
        known = {r.name.split(",")[0].strip().lower() for r in rf.records} or None
    except (OSError, ValueError):
        known = None
    for camp in campstrat.campaigns(mod):
        try:
            sf = campstrat.read_strat(mod, camp)
        except (OSError, ValueError):
            continue
        got = diplocheck.check(sf, known, False, False)
        tally = {}
        for i in got:
            tally[i.code] = tally.get(i.code, 0) + 1
        print(f"     {mod.name}/{camp}: {tally or 'clean'}")
        for i in got[:4]:
            print(f"        line {i.line}: {i.message}")
        if root == game:
            check(f"the stock game's {camp} is clean", not got)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
