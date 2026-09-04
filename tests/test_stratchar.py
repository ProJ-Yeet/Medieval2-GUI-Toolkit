"""``descr_strat.txt``, write: people - Phase 16i's exit criteria, measured.

16h proved a settlement block could be rewritten without disturbing a byte it
did not mean to. This is the same gate on the other half of a faction block, and
it is a bigger one: **479 character blocks across vanilla's two campaigns and
Third Age Reforged are re-rendered with no edits and must come back byte for
byte**, tabs, trailing spaces and the comment somebody left on a regiment
included.

The exit criteria, in the order they are checked:

    a general with an army is added to a faction on both test mods
    every character rule passes on the result
    the file outside the edited block is byte-identical
    a move takes the block that left and puts it back unchanged
    the save backs up, and the log's undo puts the file back byte-exact

Five parts, the last two of which need a real game install:

    1  the lines: shapes taken off the file, and edits that rewrite one of them
    2  the four actions: edit, add, delete and move
    3  the rules: what is fatal, what is a warning, and what is not checked
    4  every real campaign: 479 blocks re-rendered, and real plans over a sample
    5  the two routes, a real save and its undo, on a throwaway mod

    python -m tests.test_stratchar
"""
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod
from unittransfer import campmap, campstrat, config, mapquery, stratchar
from unittransfer.keyblock import read_text
from unittransfer.mod import Mod
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


CR = "\r\n"


def joined(*lines):
    return CR.join(lines) + CR


def lines_of(text):
    body = text[:-len(CR)] if text.endswith(CR) else text
    return body.split(CR)


def only_block_changed(before, after, node):
    """Nothing outside ``node``'s own lines moved, byte for byte."""
    b, a = lines_of(before), lines_of(after)
    if a[:node.start] != b[:node.start]:
        return False
    tail = len(b) - (node.end + 1)
    return a[len(a) - tail:] == b[node.end + 1:] if tail else True


# ---- 1) the lines --------------------------------------------------------------
print("\n1) the shapes are taken off the file, and an edit rewrites one line")

SAMPLE = joined(
    "campaign imperial_campaign",
    "playable",
    "\tengland",
    "\tfrance",
    "end",
    "unlockable",
    "end",
    "nonplayable",
    "end",
    "",
    "faction\tengland, balanced smith",
    "\tdenari\t10000",
    "",
    "settlement",
    "{",
    "\tlevel large_town",
    "\tregion London_Province",
    "}",
    "",
    "character\tWilliam, named character, male, leader, age 50, x 109, y 147 ",
    "traits Factionleader 1 , GoodCommander 1 , Intelligent 2 ",
    "ancillaries mentor , sceptre",
    "army",
    "unit\t\tNE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0",
    "unit\t\tSpear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0\t; the green ones",
    "",
    "character\tRobin, general, male, age 20, x 99, y 131 ",
    "army",
    "unit\t\tPeasants\t\t\t\texp 0 armour 0 weapon_lvl 0",
    "",
    "character\tCecilia, princess, female, age 18, x 111, y 151 ",
    "",
    "character_record\t\tMatilda, \tfemale, age 49, alive, never_a_leader",
    "",
    "relative \tWilliam, \tMatilda,\t\tRobin,\tCecilia,\tend",
    "",
    "faction\tfrance, balanced caesar",
    "\tdenari\t8000",
    "",
    "character\tPhilippe, named character, male, leader, age 40, x 60, y 120 ",
    "",
    "faction_standings\tengland, 0.5 france",
    "script",
    "campaign_script.txt",
)

sf = campstrat.parse_strat(SAMPLE)
eng = sf.faction("england")
fr = sf.faction("france")
will = stratchar.find_character(sf, "england", "William")
robin = stratchar.find_character(sf, "england", "Robin")
cecilia = stratchar.find_character(sf, "england", "Cecilia")
check("the three characters are found by the faction that holds them",
      will is not None and robin is not None and cecilia is not None)
check("the leader and the heir are read off the rank on the line",
      stratchar.leader_of(sf, eng) == "William"
      and stratchar.heir_of(sf, eng) == "")

check("a character's span already ends on the blank line after it",
      sf.lines[will.end] == ""
      and sf.lines[will.end + 1].startswith("character\tRobin"))

shape = stratchar.shape_of(sf, eng, will)
check("the shape is taken off the file: a tab after `character`, `, ` between "
      "fields, a trailing space, ` , ` between traits",
      shape.gap == "\t" and shape.sep == ", " and shape.trail == " "
      and shape.trait_sep == " , " and shape.indent == "")
check("and each named unit's own padding, so a regiment lines up with its kind",
      shape.pads.get("NE Bodyguard") == "\t\t\t\t")

spec = stratchar.read_spec(sf, will)
check("a character reads as values: name, type, rank, traits, army",
      spec.name == "William" and spec.type == "named character"
      and spec.rank == "leader" and spec.age == 50
      and spec.traits == [("Factionleader", 1), ("GoodCommander", 1),
                          ("Intelligent", 2)]
      and spec.ancillaries == ["mentor", "sceptre"]
      and [a.unit for a in spec.army] == ["NE Bodyguard", "Spear Militia"])

base = sf.lines[will.start:will.end + 1]
check("a render with no edits at all is the block it was given",
      stratchar.render_character(sf, will, spec) == base)

s2 = stratchar.spec_from_body({"edits": {"age": 44}}, spec)
got = stratchar.render_character(sf, will, s2)
check("one field edited rewrites one line and leaves the other five alone",
      sum(1 for a, b in zip(base, got) if a != b) == 1 and len(got) == len(base))
check("and the rewritten line keeps the trailing space the file wrote",
      got[0].endswith("y 147 ") and "age 44" in got[0])

s3 = stratchar.spec_from_body({"edits": {"portrait": "william"}}, spec)
check("a tail field the line did not have is appended, not inserted at the front",
      stratchar.render_character(sf, will, s3)[0].endswith(
          "y 147, portrait william "))

s4 = stratchar.spec_from_body(
    {"army": [{"unit": "NE Bodyguard", "exp": 1, "armour": 0, "weapon_lvl": 0},
              {"unit": "Spear Militia", "exp": 2, "armour": 0, "weapon_lvl": 0}]},
    spec)
got = stratchar.render_character(sf, will, s4)
check("a regiment whose numbers change rewrites its line and keeps its comment",
      got[5].endswith("; the green ones") and "exp 2" in got[5]
      and got[4] == base[4] and len(got) == len(base))

s5 = stratchar.spec_from_body({"army": []}, spec)
got = stratchar.render_character(sf, will, s5)
check("an army taken away is the `army` line and its regiments, and not the "
      "blank line after them",
      got == [base[0], base[1], base[2], ""])

s6 = stratchar.spec_from_body({"traits": [], "ancillaries": []}, spec)
got = stratchar.render_character(sf, will, s6)
check("traits and ancillaries emptied delete their own lines",
      len(got) == len(base) - 2 and "traits" not in "".join(got)
      and "ancillaries" not in "".join(got))

s7 = stratchar.spec_from_body(
    {"traits": [{"name": "GoodCommander", "level": 2}]},
    stratchar.read_spec(sf, robin))
got = stratchar.render_character(sf, robin, s7)
check("a traits line a character did not have is inserted under the header",
      got[1] == "traits GoodCommander 2" and len(got) == 5)

fresh = stratchar.new_character(sf, eng, stratchar.Spec(
    name="Aldred", type="general", gender="male", age=28, x=108, y=150,
    traits=[("GoodCommander", 1)],
    army=[stratchar.Army("NE Bodyguard", 1, 0, 0)]))
check("a new character is written in the shape of the ones beside it, blank "
      "line and all",
      fresh == ["character\tAldred, general, male, age 28, x 108, y 150 ",
                "traits GoodCommander 1 ",
                "army",
                "unit\t\tNE Bodyguard\t\t\t\texp 1 armour 0 weapon_lvl 0",
                ""])

# ---- 2) the four actions -------------------------------------------------------
print("\n2) edit, add, delete and move")

check("a new character goes after the faction's last one, not at the head of "
      "the list",
      stratchar.insert_at(sf, eng) == cecilia.end + 1
      and sf.lines[stratchar.insert_at(sf, eng)].startswith("character_record"))
check("a faction with no character at all takes one after its last settlement",
      stratchar.insert_at(sf, fr) > fr.start)

moved = stratchar.move_lines(list(sf.lines), (robin.start, robin.end),
                             stratchar.insert_at(sf, fr))
check("a move keeps every line in the file, and the same number of them",
      sorted(moved) == sorted(sf.lines) and len(moved) == len(sf.lines))
after = campstrat.parse_strat(CR.join(moved) + CR)
check("the moved character is inside the faction they were moved into",
      [c.name for c in stratchar.characters_of(after, after.faction("france"))]
      == ["Philippe", "Robin"]
      and [c.name for c in stratchar.characters_of(after, after.faction("england"))]
      == ["William", "Cecilia"])
check("and the counts are what they were: one block moved, nothing made or lost",
      after.counts() == sf.counts())

# ---- 3) the rules --------------------------------------------------------------
print("\n3) what is fatal, what is a warning, and what is not checked at all")


class _Fake:
    """A mod with exactly the four files 16i reads, or none of them."""

    def __init__(self, base, edu=None, edct=None, eda=None, names=None):
        self.data = base
        self.edct_path = base / "export_descr_character_traits.txt"
        self.eda_path = base / "export_descr_ancillaries.txt"
        self._edu = edu
        for path, text in ((self.edct_path, edct), (self.eda_path, eda),
                           (base / "descr_names.txt", names)):
            if text is not None:
                path.write_text(text, encoding="latin-1")

    @property
    def edu(self):
        if self._edu is None:
            raise OSError("no export_descr_unit.txt on disk")
        return self._edu


class _Units:
    def __init__(self, units):
        self.units = units


class _Unit:
    def __init__(self, name, general=False):
        self.type = name
        self.category = "infantry"
        self.class_type = "heavy"
        self.attributes = ["general_unit"] if general else []


class _Facts:
    def __init__(self, mod):
        self.mod, self.skipped = mod, []


tmp = Path(tempfile.mkdtemp(prefix="ut_char_"))
EDCT = "Trait GoodCommander\n Level Good\n  Threshold 1\n Level Better\n  Threshold 2\n"
EDA = "Ancillary mentor\n Image mentor.tga\n"
NAMES = "faction: england\n\tcharacters\n\t\tWilliam\n\t\tAldred\n"
full = _Fake(tmp, edu=_Units([_Unit("NE Bodyguard", True), _Unit("Spear Militia"),
                             _Unit("Peasants")]),
             edct=EDCT, eda=EDA, names=NAMES)
voc = stratchar.Vocabulary(_Facts(full), sf)
check("the vocabulary reads the four files when they are on disk",
      voc.have_edu and voc.have_edct and voc.have_eda and voc.have_pool
      and voc.bodyguards == {"NE Bodyguard"} and voc.traits == {"GoodCommander": 2}
      and voc.ancillaries == {"mentor"})
check("and the hero abilities come off the campaign file, which is the only "
      "place any of them is written down",
      isinstance(voc.abilities, list))

fatal = lambda f: [x["code"] for x in f if x["fatal"]]
warn = lambda f: [x["code"] for x in f if not x["fatal"]]


def spec(**kw):
    base = dict(name="Aldred", type="general", gender="male", age=28, x=10, y=10)
    base.update(kw)
    return stratchar.Spec(**base)


check("a character type the engine does not know is fatal",
      fatal(stratchar.check_character(voc, spec(type="wizard")))
      == ["char.type"])
check("an age that is not a whole number is fatal",
      fatal(stratchar.check_character(voc, spec(age="old"))) == ["char.age"])
check("a negative age is fatal",
      fatal(stratchar.check_character(voc, spec(age=-2))) == ["char.age"])
check("a character with no name is fatal, because the family tree has no other "
      "way to point at them",
      fatal(stratchar.check_character(voc, spec(name=""))) == ["char.name"])
check("a unit the EDU does not declare is fatal",
      fatal(stratchar.check_character(voc, spec(
          army=[stratchar.Army("Space Marines", 0, 0, 0)]))) == ["army.unknown"])
check("a trait the trait file does not declare is fatal",
      fatal(stratchar.check_character(voc, spec(traits=[("Nosuch", 1)])))
      == ["char.trait_unknown"])
check("a trait level above the levels the trait has is fatal",
      fatal(stratchar.check_character(voc, spec(traits=[("GoodCommander", 5)])))
      == ["char.trait_level"])
check("an ancillary the ancillary file does not declare is fatal",
      fatal(stratchar.check_character(voc, spec(ancillaries=["nosuch"])))
      == ["char.anc_unknown"])

f = stratchar.check_character(voc, spec(
    army=[stratchar.Army("Spear Militia", 0, 0, 0),
          stratchar.Army("NE Bodyguard", 1, 0, 0)]))
check("a general whose bodyguard is not in front is a warning, because Third "
      "Age Reforged has 199 armies with no bodyguard at all and plays",
      not fatal(f) and warn(f) == ["army.bodyguard"])
check("and a general who leads with his bodyguard says nothing",
      not stratchar.check_character(voc, spec(
          army=[stratchar.Army("NE Bodyguard", 1, 0, 0)])))
check("a spy with a regiment behind him is not asked about bodyguards at all",
      not stratchar.check_character(voc, spec(
          type="spy", army=[stratchar.Army("Peasants", 0, 0, 0)])))
check("no sex on the line is a warning, not a refusal",
      warn(stratchar.check_character(voc, spec(gender=""))) == ["char.gender"])
check("a name the faction's own pool does not hold is a warning that says "
      "whose pool it is in",
      [x["code"] for x in stratchar.check_pool(voc, "england", "Boromir")]
      == ["char.pool"]
      and not stratchar.check_pool(voc, "england", "Aldred"))

blind = stratchar.Vocabulary(_Facts(_Fake(Path(tempfile.mkdtemp(prefix="ut_bl_")))), sf)
check("with none of the four files on disk the vocabulary says so, by name",
      not blind.have_edu and not blind.have_edct and not blind.have_eda
      and not blind.have_pool and len(blind.skipped) == 4)
check("and then no roster rule runs at all: a rule with no evidence reports "
      "nothing",
      not stratchar.check_character(blind, spec(
          traits=[("Nosuch", 9)], ancillaries=["nosuch"],
          army=[stratchar.Army("Space Marines", 0, 0, 0)]))
      and not stratchar.check_pool(blind, "england", "Boromir"))

fac = stratchar.check_faction(sf, eng, voc)
check("a faction with one leader and a clean family says nothing", not fac)

TWO = SAMPLE.replace("character\tRobin, general, male, age 20",
                     "character\tRobin, general, male, leader, age 20")
sf2 = campstrat.parse_strat(TWO)
check("two leaders in one faction is a warning naming both",
      [f["code"] for f in stratchar.check_faction(sf2, sf2.faction("england"), voc)]
      == ["faction.leaders"])

YOUNG = SAMPLE.replace("William, named character, male, leader, age 50",
                       "William, named character, male, leader, age 30")
sf3 = campstrat.parse_strat(YOUNG)
codes = [f["code"] for f in stratchar.check_faction(sf3, sf3.faction("england"), voc)]
check("a father ten years older than his son is a warning, because vanilla "
      "does it once", "family.years" in codes)

OLD = SAMPLE.replace("Robin,\tCecilia,\tend", "Cecilia,\tRobin,\tend")
sf4 = campstrat.parse_strat(OLD)
check("children out of oldest-first order is a warning, because vanilla does "
      "it twice",
      "family.order" in [f["code"] for f in
                         stratchar.check_faction(sf4, sf4.faction("england"), voc)])

GHOST = SAMPLE.replace("Robin,\tCecilia,\tend", "Robin,\tCecilia,\tNobody,\tend")
sf5 = campstrat.parse_strat(GHOST)
check("a family line naming somebody who is not in the faction is a warning",
      "family.unknown" in [f["code"] for f in
                           stratchar.check_faction(sf5, sf5.faction("england"), voc)])

DUP = SAMPLE.replace("character\tCecilia, princess, female",
                     "character\tRobin, princess, female")
sf6 = campstrat.parse_strat(DUP)
check("two characters of one name is a warning, because a relative line has "
      "no other way to tell them apart",
      "faction.duplicate" in [f["code"] for f in
                              stratchar.check_faction(sf6, sf6.faction("england"), voc)])

shutil.rmtree(tmp, ignore_errors=True)

# ---- 4) every real campaign ----------------------------------------------------
print("\n4) every installed campaign: every block re-rendered, and real plans")

roots = []
game = _realmod.MODS.parent
if (game / "data").is_dir():
    roots.append(game)
roots += _realmod.installed()
roots = [r for r in roots if (r / "data" / campstrat.CAMPAIGN_DIR_REL).is_dir()]

if not roots:
    print(f"  SKIPPED - nothing with {campstrat.CAMPAIGN_DIR_REL} under "
          f"{_realmod.MODS}")
else:
    total = 0
    for root in roots:
        mod = Mod(root)
        for name in campstrat.campaigns(mod):
            f = campstrat.read_strat(mod, name)
            raw = read_text(f.path, campstrat.ENCODING)
            people = f.of_kind("character")
            total += len(people)
            bad = [n for n in people
                   if stratchar.render_character(f, n, stratchar.read_spec(f, n))
                   != f.lines[n.start:n.end + 1]]
            check(f"{root.name}/{name}: {len(people)} character blocks re-render "
                  f"byte for byte with no edits", not bad)
            check(f"{root.name}/{name}: the file still round-trips",
                  f.serialise() == raw)

            ends = Counter("blank" if not f.lines[n.end].strip() else "code"
                           for n in people)
            check(f"{root.name}/{name}: {ends['blank']} of {len(people)} spans "
                  f"end on the blank line that separates them, which is what "
                  f"makes a move a straight slice", ends["blank"] >= len(people) - 1)

            held = [x for x in f.of_kind("faction")
                    if [c for c in stratchar.characters_of(f, x)
                        if c.get("type") == "named character"]]
            many = [str(x.get("name") or x.name) for x in held
                    if len([c for c in stratchar.characters_of(f, x)
                            if c.get("rank") == "leader"]) > 1]
            check(f"{root.name}/{name}: none of the {len(held)} factions with "
                  f"named characters has two leaders", not many)

    print(f"  {total} character blocks re-rendered in all")

    # ---- real plans, on a sample of each campaign ---------------------------
    print("\n   real plans: an edit, a general with an army, a move and a delete")
    for root in roots:
        mod = Mod(root)
        try:
            cm = campmap.CampaignMap(mod)
        except campmap.MapError as exc:
            print(f"  {root.name}: SKIPPED - {exc}")
            continue
        for name in campstrat.campaigns(mod)[:1]:
            facts = mapquery.Facts(mod, cm, name)
            f = campstrat.read_strat(mod, name)
            before = f.serialise()
            with_people = [x for x in f.of_kind("faction")
                           if len(stratchar.characters_of(f, x)) > 1]
            picks = [with_people[0], with_people[len(with_people) // 2]]
            t0 = time.time()
            for fac in picks:
                who = str(fac.get("name") or fac.name)
                chars = stratchar.characters_of(f, fac)
                node = chars[-1]
                spec = stratchar.read_spec(f, node)
                dest = next(str(x.get("name") or x.name)
                            for x in f.of_kind("faction")
                            if str(x.get("name") or x.name) != who)

                p = stratchar.plan_character(mod, facts, {
                    "faction": who, "character": node.name, "line": node.start + 1,
                    "campaign": name, "edits": {"age": 41}})
                check(f"{root.name}/{name} {who}/{node.name}: an age saves, and "
                      f"only this block changes",
                      not p.errors and p.text
                      and only_block_changed(before, p.text, node))

                army = [{"unit": a.unit, "exp": a.exp, "armour": a.armour,
                         "weapon_lvl": a.weapon_lvl} for a in spec.army] or [
                    {"unit": next(iter(u.name for u in f.of_kind("unit") if u.name),
                                  "Peasants"),
                     "exp": 0, "armour": 0, "weapon_lvl": 0}]
                p2 = stratchar.plan_character(mod, facts, {
                    "faction": who, "campaign": name, "action": "add",
                    "edits": {"name": "Testwright", "type": "general",
                              "gender": "male", "age": 28,
                              "x": spec.x, "y": spec.y},
                    "army": army})
                back = campstrat.parse_strat(p2.text) if p2.text else None
                added = (stratchar.find_character(back, who, "Testwright")
                         if back is not None else None)
                check(f"{root.name}/{name} {who}: a general with "
                      f"{len(army)} regiment(s) is added, after the faction's "
                      f"last character",
                      not [e for e in p2.errors] and back is not None
                      and added is not None
                      and back.serialise() == p2.text
                      and back.counts()["character"] == f.counts()["character"] + 1
                      and [c.name for c in
                           stratchar.characters_of(back, back.faction(who))][-1]
                      == "Testwright")
                check(f"{root.name}/{name} {who}: and every character rule "
                      f"passes on the result",
                      not [x for x in p2.findings if x["fatal"]])

                p3 = stratchar.plan_character(mod, facts, {
                    "faction": who, "character": node.name, "line": node.start + 1,
                    "campaign": name, "action": "move", "owner": dest})
                back = campstrat.parse_strat(p3.text) if p3.text else None
                check(f"{root.name}/{name} {who}/{node.name}: joins {dest}, and "
                      f"the block that lands is the block that left",
                      not p3.errors and back is not None
                      and back.serialise() == p3.text
                      and back.counts() == f.counts()
                      and Counter(back.lines) == Counter(f.lines)
                      and (lambda n2: n2 is not None
                           and back.lines[n2.start:n2.end + 1]
                           == f.lines[node.start:node.end + 1])(
                          stratchar.find_character(back, dest, node.name)))

                p4 = stratchar.plan_character(mod, facts, {
                    "faction": who, "character": node.name, "line": node.start + 1,
                    "campaign": name, "action": "delete"})
                back = campstrat.parse_strat(p4.text) if p4.text else None
                check(f"{root.name}/{name} {who}/{node.name}: deleted, and every "
                      f"other block is untouched",
                      not p4.errors and back is not None
                      and only_block_changed(before, p4.text, node)
                      and back.counts()["character"]
                      == f.counts()["character"] - 1)
            print(f"   {root.name}/{name}: 8 plans in "
                  f"{(time.time() - t0) * 1000:.0f} ms")

# ---- 5) the two routes, a real save and its undo -------------------------------
print("\n5) /api/map/faction and /api/map/character_plan|_apply")

if not roots:
    print("  SKIPPED - no campaign to serve")
else:
    src = roots[0]
    camp = campstrat.campaigns(Mod(src))[0]
    cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"

    med2 = Path(tempfile.mkdtemp(prefix="ut_med2_"))
    data = med2 / "mods" / "CharMod" / "data"
    (data / campmap.BASE_REL).mkdir(parents=True)
    for pth in (src / "data" / campmap.BASE_REL).iterdir():
        if pth.is_file():
            shutil.copy2(pth, data / campmap.BASE_REL / pth.name)
    camp_dir = data / campstrat.CAMPAIGN_DIR_REL / camp
    camp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "data" / campstrat.CAMPAIGN_DIR_REL / camp
                 / campstrat.STRAT_NAME, camp_dir / campstrat.STRAT_NAME)
    for extra in ("export_descr_unit.txt", "descr_names.txt",
                  "export_descr_character_traits.txt",
                  "export_descr_ancillaries.txt"):
        got = src / "data" / extra
        if got.is_file():
            shutil.copy2(got, data / extra)
    config.save_settings(med2_root=str(med2), run_full_cleaner=False)

    Handler.registry = Registry(cfg / "icons")
    httpd = _Server(("127.0.0.1", 0), Handler)
    BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"  serving {BASE} - {camp} copied from {src.name}")

    def get(path):
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(path, body):
        req = urllib.request.Request(
            BASE + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))

    def status(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=300) as r:
                return r.status, ""
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8")).get("error", "")
            except Exception:                          # noqa: BLE001
                return e.code, ""

    strat_path = camp_dir / campstrat.STRAT_NAME
    was = strat_path.read_bytes()
    live = campstrat.parse_strat(read_text(strat_path, campstrat.ENCODING))
    fac = next(x for x in live.of_kind("faction")
               if len(stratchar.characters_of(live, x)) > 1)
    who = str(fac.get("name") or fac.name)
    last = stratchar.characters_of(live, fac)[-1]

    try:
        d = get(f"/api/map/faction?mod=CharMod&faction={who}")
        check(f"/api/map/faction answers for {who}: {len(d['characters'])} "
              f"characters, leader {d['leader'] or '(none)'}, "
              f"{len(d['relatives'])} family line(s)",
              d["faction"] == who and d["characters"]
              and isinstance(d["vocab"]["types"], list))
        check("the vocabulary carries the twelve character types and whatever "
              "roster is on disk",
              len(d["vocab"]["types"]) == 12
              and isinstance(d["vocab"]["units"], list))
        check("a faction with no block is a 404 that says so",
              status("/api/map/faction?mod=CharMod&faction=atlantis")[0] == 404)

        body = {"mod": "CharMod", "campaign": camp, "faction": who,
                "character": last.name, "line": last.start + 1,
                "edits": {"age": 39}}
        plan = post("/api/map/character_plan", body)
        check("a plan says what would change and writes nothing",
              plan["plan"]["ok"] and plan["plan"]["changes"]
              and strat_path.read_bytes() == was)

        bad = post("/api/map/character_plan", dict(body, edits={"type": "wizard"}))
        check("a type the engine does not know is refused at the plan, with the "
              "twelve named",
              not bad["plan"]["ok"] and "named character" in bad["error"])

        spec = stratchar.read_spec(live, last)
        add = {"mod": "CharMod", "campaign": camp, "faction": who,
               "action": "add",
               "edits": {"name": "Testwright", "type": "general",
                         "gender": "male", "age": 28, "x": spec.x, "y": spec.y},
               "army": [{"unit": a.unit, "exp": a.exp, "armour": a.armour,
                         "weapon_lvl": a.weapon_lvl} for a in spec.army]}
        res = post("/api/map/character_apply", add)
        check("adding a general with an army answers with a log record that can "
              "undo it",
              not res.get("error") and res["record"]["manifest"]["backed_up"]
              and res["record"]["mode"] == "campmap"
              and res["record"]["action"] == "character")
        now = campstrat.parse_strat(read_text(strat_path, campstrat.ENCODING))
        check("the file on disk still reads, and holds one more character",
              now.counts()["character"] == live.counts()["character"] + 1
              and now.serialise() == read_text(strat_path, campstrat.ENCODING))
        check(f"{who} holds Testwright now, and he is last in the block",
              [c.name for c in
               stratchar.characters_of(now, now.faction(who))][-1] == "Testwright")

        again = get(f"/api/map/faction?mod=CharMod&faction={who}")
        check("and the panel is told so on the next read, so the cache went "
              "with the write",
              any(c["name"] == "Testwright" for c in again["characters"]))
        check("every rule passes on the character that was just added",
              not [x for c in again["characters"] if c["name"] == "Testwright"
                   for x in c["findings"] if x["fatal"]])

        post("/api/undo", {"id": res["record"]["id"]})
        check("undo puts descr_strat.txt back byte-exact",
              strat_path.read_bytes() == was)
    finally:
        httpd.shutdown()
        shutil.rmtree(med2, ignore_errors=True)
        shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
