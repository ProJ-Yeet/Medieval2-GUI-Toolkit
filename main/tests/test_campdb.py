"""``descr_campaign_db.xml`` - Phase 38.

Four claims under test:

    the file comes back         parse_text(t).text() == t on every installed
                                mod, CRLF and the spaces round `=` included
    the form types itself       every tag's box comes off its own attribute,
                                and a value of the wrong kind is refused
    a save is a splice          one value edited rewrites the characters
                                between two quotes and nothing else
    an add is documented        only a tag the archive prints can be added,
                                and it lands inside its section

Four parts:

    1  a file written here: parse, notes, checks
    2  plan: values, refusals, adds
    3  every installed mod: round trip, no findings
    4  plan and apply against a copy of a real mod

    python -m tests.test_campdb
"""
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import campdb
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


SAMPLE = """<?xml version="1.0"?>
<root>
   <recruitment>
      <recruitment_slots uint="1"/>
      <deplenish_offset float="-0.2"/>
   </recruitment>
   <settlement>
      <!-- FORTS -->
      <destroy_empty_forts bool="false"/>
      <can_build_forts bool = "false"/><!--can a general build one -->
      <siege_gear_required_for_city_level string="town"/>
      <min_turn_keep_rebel_garrison int="45"/>
   </settlement>
</root>
"""


class FakeMod:
    def __init__(self, root: Path):
        self.root = root
        self.data = root / "data"
        self.name = root.name


print("1  a file written here")
db = campdb.parse_text(SAMPLE)
check("it comes back byte for byte", db.text() == SAMPLE)
check("CRLF comes back too",
      campdb.parse_text(SAMPLE.replace("\n", "\r\n")).text() == SAMPLE.replace("\n", "\r\n"))
check("…and a file with no final newline",
      campdb.parse_text(SAMPLE.rstrip("\n")).text() == SAMPLE.rstrip("\n"))
check("root and two sections", db.root == "root"
      and [s.name for s in db.sections] == ["recruitment", "settlement"])
check("six tags, each typed off its own attribute",
      [(t.name, t.type) for t in db.tags()] == [
          ("recruitment_slots", "uint"), ("deplenish_offset", "float"),
          ("destroy_empty_forts", "bool"), ("can_build_forts", "bool"),
          ("siege_gear_required_for_city_level", "string"),
          ("min_turn_keep_rebel_garrison", "int")])
check("spaces round `=` are read", db.get("settlement/can_build_forts").value == "false")
check("an inline comment is the tag's note",
      db.get("settlement/can_build_forts").note == "can a general build one")
check("a stand-alone comment is kept in order as a heading",
      db.section("settlement").items[0] == ("note", "FORTS"))
check("a clean file has no findings", campdb.check_file(db) == [])

bad = campdb.parse_text(SAMPLE.replace('uint="1"', 'uint="-1"')
                        .replace('string="town"', 'string="metropolis"')
                        .replace("   </recruitment>",
                                 '      <deplenish_offset float="0.1"/>\n   </recruitment>'))
codes = sorted((f["code"], f["fatal"]) for f in campdb.check_file(bad))
check("a uint below zero is fatal, an unknown city level a warning, a repeat a warning",
      codes == [("duplicate", False), ("value", False), ("value", True)])
odd = campdb.parse_text(SAMPLE.replace("   <settlement>", "   <x a='1'>stray</x>\n   <settlement>"))
check("a line the scan cannot place is kept and reported, not dropped",
      odd.text().count("stray") == 1
      and [f["code"] for f in campdb.check_file(odd)] == ["unread"])
alt = campdb.parse_text(SAMPLE.replace("   </settlement>",
                                       '      <alt_rel_gov_coefficient float="-0.2"/>\n   </settlement>'))
check("alt_rel_ values with the mode off are reported",
      [f["code"] for f in campdb.check_file(alt)] == ["alt_piety"])

for t, v, good in [("bool", "true", True), ("bool", "True", False), ("uint", "0", True),
                   ("uint", "-3", False), ("int", "-3", True), ("int", "1.0", True),
                   ("float", "-0.25", True), ("float", "2", True), ("float", "1e3", False),
                   ("string", "a<b", False)]:
    err, _, _ = campdb.check_value(t, v)
    check(f"{t} {v!r} is {'taken' if good else 'refused'}", (err is None) == good)

# Blank space inside the quotes is not the wrong KIND of value, and saying it
# was ("`true ` is not true or false") is no help in front of a box that reads
# true. Named, as a warning, with the trimmed value in the sentence.
for v, side in [("true ", "after it"), (" true", "in front of it"),
                (" true ", "on both sides of it")]:
    err, warn, _ = campdb.check_value("bool", v)
    check(f"bool {v!r} is blank space, not the wrong kind",
          err is None and warn and f"blank space {side}" in warn and "`true`" in warn)
check("…and a value that is wrong once trimmed is still refused, spaces and all",
      campdb.check_value("bool", "yes ")[0] == "`yes ` is not true or false")

# A whole number spelled as a decimal is that whole number. A note, so Health
# leaves it out of the default list; a fraction that is not zero is still wrong.
for t, v, n in [("int", "100.0", "100"), ("uint", "100.0", "100"), ("int", "-5.000", "-5")]:
    err, warn, note = campdb.check_value(t, v)
    check(f"{t} {v!r} is {n}, as a note and not a fault",
          err is None and warn is None and note and f"is {n} written as a decimal" in note)
check("…but a fraction that is not zero is still refused",
      campdb.check_value("int", "100.5")[0] and campdb.check_value("uint", "-3.0")[0])
check("…and a float is unchanged by any of it", campdb.check_value("float", "1.0") == (None, None, None))

spaced = campdb.parse_text(SAMPLE.replace('bool="false"', 'bool="false "')
                           .replace('int="45"', 'int="45.0"'))
sf = campdb.check_file(spaced)
check("both reach check_file, one a warning and one a note",
      [(f["code"], f["fatal"], f.get("severity")) for f in sf]
      == [("value", False, None), ("value", False, "note")])


print("\n2  plan")
tmp = Path(_tmp.mkdtemp(prefix="ut_campdb_"))
fake = FakeMod(tmp / "Fake")
(fake.data).mkdir(parents=True)
(fake.data / campdb.REL).write_bytes(SAMPLE.encode("latin-1"))

p = campdb.plan(fake, {"values": {"settlement/can_build_forts": "true",
                                  "recruitment/deplenish_offset": "-0.5"}})
check("two values plan cleanly", p.payload()["ok"] and len(p.changes) == 2)
check("…and only the characters between the quotes change",
      p.text == SAMPLE.replace('bool = "false"/><!--', 'bool = "true"/><!--')
                      .replace('"-0.2"', '"-0.5"'))
check("an unchanged value is not a change",
      campdb.plan(fake, {"values": {"recruitment/recruitment_slots": "1"}}).errors
      == ["nothing to change"])
r = campdb.plan(fake, {"values": {"recruitment/recruitment_slots": "two"}})
check("a value of the wrong kind is refused", r.errors and not r.text)
check("a key the file does not have is refused",
      campdb.plan(fake, {"values": {"settlement/nope": "1"}}).errors)
check("an unknown city level plans, with a warning",
      campdb.plan(fake, {"values": {"settlement/siege_gear_required_for_city_level":
                                    "metropolis"}}).warnings)

a = campdb.plan(fake, {"add": ["alternative_religious_unrest", "alt_rel_allied_modifier"],
                       "values": {"settlement/alt_rel_allied_modifier": "0.75"}})
check("two documented tags add", a.payload()["ok"] and len(a.changes) == 2)
after = campdb.parse_text(a.text)
check("…inside <settlement>, at its end, in the order asked",
      [t.name for t in after.section("settlement").tags][-2:]
      == ["alternative_religious_unrest", "alt_rel_allied_modifier"])
check("…with the default, or the value given",
      after.get("settlement/alternative_religious_unrest").value == "true"
      and after.get("settlement/alt_rel_allied_modifier").value == "0.75")
check("…indented like the tag above them",
      a.text.count('\n      <alt_rel_allied_modifier float="0.75"/>\n   </settlement>') == 1)
check("…and the result is still XML", ET.fromstring(a.text) is not None)
check("a tag the archive gives no default for cannot be added",
      campdb.plan(fake, {"add": ["captor_ransom_chance_base"]}).errors)
check("a tag already written cannot be added twice",
      campdb.plan(fake, {"add": ["can_build_forts"]}).errors)
nosec = fake.data / campdb.REL
nosec.write_bytes(SAMPLE.replace("settlement>", "towns>").encode("latin-1"))
check("a documented tag whose section the file lacks is refused",
      any("no <settlement> section" in e
          for e in campdb.plan(fake, {"add": ["can_build_forts"]}).errors))
nosec.write_bytes(SAMPLE.encode("latin-1"))

ov = campdb.overview(fake)
check("the overview offers the documented tags the file lacks and none it has",
      sorted(m["name"] for m in ov["missing"]) == sorted(
          ["alternative_religious_unrest", "alt_rel_allied_modifier",
           "alt_rel_gov_modifier_base", "alt_rel_gov_coefficient", "fort_fortification_level"]))
check("…and carries the archive's word on the tags it knows",
      next(i for s in ov["sections"] for i in s["items"]
           if i.get("name") == "destroy_empty_forts")["vocab"]["source"].startswith("Everything"))


print("\n3  every installed mod")
mods = _realmod.installed()
for root in mods:
    f = root / "data" / campdb.REL
    if not f.is_file():
        continue
    text = campdb.kb.read_text(f, campdb.ENCODING)
    rdb = campdb.parse_text(text)
    check(f"{root.name}: round trip", rdb.text() == text)
    check(f"{root.name}: 18 sections, nothing unread",
          len(rdb.sections) == 18 and not rdb.unread)
    check(f"{root.name}: every tag is one of the five types",
          all(t.type in campdb.TYPES for t in rdb.tags()))
    check(f"{root.name}: no fatal findings",
          not [x for x in campdb.check_file(rdb) if x["fatal"]])


print("\n4  plan and apply on a copy of a real mod")
src = _realmod.pick("Third_Age_Reforged", need=campdb.REL)
dest = tmp / src.name
(dest / "data").mkdir(parents=True)
shutil.copy2(src / "data" / campdb.REL, dest / "data" / campdb.REL)
mod = Mod(dest)
before = (dest / "data" / campdb.REL).read_bytes()
cur = campdb.read(mod)[0].get("settlement/destroy_empty_forts").value
flip = "true" if cur == "false" else "false"
pl = campdb.plan(mod, {"values": {"settlement/destroy_empty_forts": flip}})
check("a real fort switch plans", pl.payload()["ok"])
res = campdb.apply(pl)
now = (dest / "data" / campdb.REL).read_bytes()
check("…writes one line's worth of difference",
      len(now) == len(before) + len(flip) - len(cur)
      and now.count(b"\r\n") == before.count(b"\r\n"))
check("…and backs the old file up byte for byte",
      (Path(res["record"]["backup_root"]) / "data" / campdb.REL).read_bytes() == before)
check("…under its own mode in the log", res["record"]["mode"] == "campdb")

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
