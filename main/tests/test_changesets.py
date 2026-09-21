"""Phase 52: change sets - your edits recorded, and ported onto the next version.

    python -m tests.test_changesets

1. Recording: a real save (the raw text editor's) through the real write path
   puts the file's original in the set as its baseline and the result as mine,
   outside the mod folder; a second save keeps the first original; a mod
   outside <Medieval II>/mods records nothing; Undo tells the set.
2. The change list, record by record: an EDU unit by type, an EDB building by
   name, a text key by key, and the split joins back to the file exactly.
3. The three-way line merge: disjoint edits merge, overlapping ones do not, the
   same edit on both sides is not a conflict.
4. A port onto the same mod after a simulated update overwrote it, with every
   outcome: clean, already, merged, conflict, gone, a removal, an addition,
   and a dangling recruit pool.
5. Applying it: the picked records and only those, byte for byte elsewhere, a
   log entry Undo reverses, and the baseline moved to the version ported onto.
6. Export and import as one file, and a port from the imported set onto a
   second folder.
7. Phase 53, switching in place: a set off puts the originals back, a new save
   with every set off starts another, a switch between two is one job and one
   Undo, it is refused rather than guessed when the disk has moved, and a
   switch's own writes are never recorded as an edit.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import changesets, config, rawtext
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


tmp = Path(_tmp.mkdtemp(prefix="ut_cs_"))
cfg = tmp / "config"
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
med2 = tmp / "med2"
config.save_settings(med2_root=str(med2))

CR = "\r\n"
EDU = CR.join([
    "; the units", "",
    "type             Gondor Spearmen", "dictionary       Gondor_Spearmen",
    "soldier          gondor_spear, 40, 0, 1", "stat_pri         7, 4, no, 0, 0", "",
    "type             Gondor Archers", "dictionary       Gondor_Archers",
    "soldier          gondor_archer, 40, 0, 1", "stat_pri         9, 3, arrow, 120, 30", "",
    "type             Rohan Riders", "dictionary       Rohan_Riders",
    "soldier          rohan_rider, 30, 0, 1", "stat_pri         8, 5, no, 0, 0", "",
]) + CR
EDB = CR.join([
    "hidden_resources rohan gondor", "",
    "building barracks", "{", "    levels muster", "    {",
    "        muster city requires factions { gondor, }", "        {",
    "            capability", "            {",
    '                recruit_pool "Gondor Spearmen"  1  0.1  2  0',
    "            }", "            cost 400", "        }", "    }", "}", "",
    "building range", "{", "    levels butts", "    {",
    "        butts city requires factions { gondor, }", "        {",
    "            capability", "            {",
    '                recruit_pool "Gondor Archers"  1  0.1  2  0',
    "            }", "            cost 300", "        }", "    }", "}", "",
]) + CR


def make_mod(name, edu=EDU, edb=EDB):
    d = med2 / "mods" / name / "data"
    (d / "text").mkdir(parents=True, exist_ok=True)
    (d / "export_descr_unit.txt").write_bytes(edu.encode("latin-1"))
    (d / "export_descr_buildings.txt").write_bytes(edb.encode("latin-1"))
    (d / "text" / "export_units.txt").write_bytes(
        b"\xff\xfe" + ("{Gondor_Spearmen}Spearmen of Gondor" + CR
                       + "{Gondor_Archers}Archers of Gondor" + CR).encode("utf-16-le"))
    return Mod(med2 / "mods" / name)


def save(mod, rel, text):
    """A save through the raw text editor - a real writer, the real hook."""
    raw = (mod.data / rel).read_bytes()
    p = rawtext.plan(mod, {"rel": rel, "sig": rawtext.signature(raw), "text": text})
    assert not p.errors, p.errors
    return rawtext.apply(p)


def text_of(mod, rel):
    raw = (mod.data / rel).read_bytes()
    return rawtext.decode(raw, rawtext.sniff(raw))


# ---------------------------------------------------------------------------
print("\n1) recording, from inside the write path")
mod = make_mod("AGO")
orig_edu = (mod.data / "export_descr_unit.txt").read_bytes()
orig_edb = (mod.data / "export_descr_buildings.txt").read_bytes()

e1 = EDU.replace("stat_pri         7, 4, no, 0, 0", "stat_pri         9, 4, no, 0, 0")
save(mod, "export_descr_unit.txt", e1.replace(CR, "\n"))
sd = changesets.set_dir("AGO")
check("the set lives under config/, not in the mod folder",
      sd.is_dir() and cfg in sd.parents and not str(sd).startswith(str(med2)))
check("the baseline is the file as it was before the first save",
      (sd / "base" / "export_descr_unit.txt").read_bytes() == orig_edu)
check("mine is the file as saved",
      (sd / "mine" / "export_descr_unit.txt").read_bytes()
      == (mod.data / "export_descr_unit.txt").read_bytes())
e2 = e1.replace("stat_pri         8, 5, no, 0, 0", "stat_pri         8, 6, no, 0, 0")
save(mod, "export_descr_unit.txt", e2.replace(CR, "\n"))
check("a second save keeps the FIRST original as the baseline",
      (sd / "base" / "export_descr_unit.txt").read_bytes() == orig_edu)

other = tmp / "elsewhere" / "Loose" / "data"
other.mkdir(parents=True)
(other / "export_descr_unit.txt").write_bytes(orig_edu)
save(Mod(other.parent), "export_descr_unit.txt", EDU.replace("Rohan", "Dale").replace(CR, "\n"))
check("a mod outside <Medieval II>/mods records nothing",
      not changesets.set_dir("Loose").exists())

# the EDB: a pool added to barracks, the range building edited, a new building
b1 = EDB.replace('                recruit_pool "Gondor Spearmen"  1  0.1  2  0',
                 '                recruit_pool "Gondor Spearmen"  1  0.1  2  0' + CR
                 + '                recruit_pool "Rohan Riders"  1  0.1  2  0')
b1 = b1.replace("            cost 300", "            cost 250")
b1 = b1 + CR.join(["building stables", "{", "    levels stall", "    {",
                   "        stall city requires factions { rohan, }", "        {",
                   "            capability", "            {",
                   '                recruit_pool "Rohan Riders"  1  0.2  3  0',
                   "            }", "            cost 500", "        }", "    }", "}", ""]) + CR
r = save(mod, "export_descr_buildings.txt", b1.replace(CR, "\n"))
undo(r["id"])
check("Undo puts the file back, and the set's mine follows it",
      (sd / "mine" / "export_descr_buildings.txt").read_bytes() == orig_edb)
save(mod, "export_descr_buildings.txt", b1.replace(CR, "\n"))
t1 = text_of(mod, "text/export_units.txt").replace("Archers of Gondor", "Bowmen of Gondor")
save(mod, "text/export_units.txt", t1.replace(CR, "\n"))

# ---------------------------------------------------------------------------
print("\n2) the change list, record by record")
s = changesets.summary(mod)
files = {f["rel"]: f for f in s["files"]}
check("three files tracked", set(files) == {"export_descr_unit.txt",
      "export_descr_buildings.txt", "text/export_units.txt"})
edu_recs = {(r["key"], r["kind"]) for r in files["export_descr_unit.txt"]["records"]}
check("the EDU is two units edited, by type",
      edu_recs == {("Gondor Spearmen", "edited"), ("Rohan Riders", "edited")})
edb_recs = {(r["key"], r["kind"]) for r in files["export_descr_buildings.txt"]["records"]}
check("the EDB is two buildings edited and one added, by name",
      edb_recs == {("barracks", "edited"), ("range", "edited"), ("stables", "added")})
check("the text file is one key edited",
      [(r["key"], r["kind"]) for r in files["text/export_units.txt"]["records"]]
      == [("Gondor_Archers", "edited")])
check("and the disk still says what was saved", all(f["disk"] == "same" for f in s["files"]))
for rel in files:
    t = text_of(mod, rel)
    if "".join(changesets.split(rel, t).values()) != t:
        check(f"{rel} splits and joins back exactly", False)
check("every file splits into records and joins back exactly", True)

# ---------------------------------------------------------------------------
print("\n3) the three-way line merge")
base = "a\nb\nc\nd\ne\n"
check("edits to different lines merge",
      changesets.merge3(base, "A\nb\nc\nd\ne\n", "a\nb\nc\nd\nE\n") == "A\nb\nc\nd\nE\n")
check("edits to the same line do not",
      changesets.merge3(base, "a\nB\nc\nd\ne\n", "a\nX\nc\nd\ne\n") is None)
check("the same edit on both sides is not a conflict",
      changesets.merge3(base, "a\nB\nc\nd\ne\n", "a\nB\nc\nd\ne\n") == "a\nB\nc\nd\ne\n")
check("edits to neighbouring lines conflict, as git's do",
      changesets.merge3(base, "a\nB\nc\nd\ne\n", "a\nb\nC\nd\ne\n") is None)
check("two inserts at the same point conflict",
      changesets.merge3(base, "a\nx\nb\nc\nd\ne\n", "a\ny\nb\nc\nd\ne\n") is None)

# ---------------------------------------------------------------------------
print("\n4) the update lands: a port onto the same mod")
# AGO 2.0 overwrites the files. Upstream: Gondor Spearmen's stat_pri untouched
# but its soldier line changed (merges with ours); Rohan Riders removed (ours
# was edited: gone); barracks rewritten in the same line ours touched
# (conflict); range untouched (clean); text untouched (clean).
new_edu = (EDU.replace("dictionary       Gondor_Spearmen",
                       "dictionary       Gondor_Spearmen" + CR + "officer          gondor_captain")
           .replace(CR.join(["type             Rohan Riders", "dictionary       Rohan_Riders",
                             "soldier          rohan_rider, 30, 0, 1",
                             "stat_pri         8, 5, no, 0, 0", ""]) + CR, ""))
new_edb = EDB.replace('recruit_pool "Gondor Spearmen"  1  0.1  2  0',
                      'recruit_pool "Gondor Spearmen"  2  0.2  4  0')
(mod.data / "export_descr_unit.txt").write_bytes(new_edu.encode("latin-1"))
(mod.data / "export_descr_buildings.txt").write_bytes(new_edb.encode("latin-1"))
(mod.data / "text" / "export_units.txt").write_bytes(
    (sd / "base" / "text" / "export_units.txt").read_bytes())
s = changesets.summary(mod)
check("the summary sees the disk moved under the set",
      {f["rel"]: f["disk"] for f in s["files"]}["export_descr_unit.txt"] == "changed")

port = changesets.plan_port("AGO", mod)
got = {(i.rel.split("/")[-1], i.key): i for i in port.items}
out = lambda rel, key: got[(rel, key)].outcome if (rel, key) in got else None  # noqa: E731
check("Gondor Spearmen: both sides changed different lines, so it merges",
      out("export_descr_unit.txt", "Gondor Spearmen") == "merged")
check("  and the merge carries both: our stat_pri and their officer line",
      "9, 4, no" in got[("export_descr_unit.txt", "Gondor Spearmen")].merged
      and "gondor_captain" in got[("export_descr_unit.txt", "Gondor Spearmen")].merged)
check("Rohan Riders: ours edited, theirs removed, so it is gone",
      out("export_descr_unit.txt", "Rohan Riders") == "gone")
check("barracks: a pool added directly under the one upstream re-tuned, so it conflicts",
      out("export_descr_buildings.txt", "barracks") == "conflict")
check("range: untouched upstream, so it applies clean",
      out("export_descr_buildings.txt", "range") == "clean")
check("stables: ours alone, so it is a clean addition",
      out("export_descr_buildings.txt", "stables") == "clean"
      and got[("export_descr_buildings.txt", "stables")].kind == "added")
check("stables recruits Rohan Riders, which the new EDU dropped: dangling",
      got[("export_descr_buildings.txt", "stables")].dangling == ["Rohan Riders"])
check("the text key applies clean", out("export_units.txt", "Gondor_Archers") == "clean")
check("conflicts and gone are not ticked by default, clean and merged are",
      {i.outcome: i.default for i in port.items} ==
      {"merged": True, "gone": False, "conflict": False, "clean": True})

# ---------------------------------------------------------------------------
print("\n5) applying it")
edb_before = (mod.data / "export_descr_buildings.txt").read_bytes()
picks = {i.id: "mine" for i in port.items if i.default}
res = changesets.apply_port(port, picks)
edu_now = text_of(mod, "export_descr_unit.txt")
edb_now = text_of(mod, "export_descr_buildings.txt")
check("the merge is written", "9, 4, no" in edu_now and "gondor_captain" in edu_now)
check("a gone record is not brought back unticked", "Rohan Riders" not in edu_now)
check("the conflict keeps theirs", 'recruit_pool "Gondor Spearmen"  2  0.2  4  0' in edb_now)
check("the clean edit and the addition are in", "cost 250" in edb_now and "building stables" in edb_now)
check("the new building goes where it sits in ours, after range",
      edb_now.index("building range") < edb_now.index("building stables"))
check("everything outside the picked records is theirs, byte for byte",
      edb_now.startswith(new_edb.split("building range")[0]))
check("the text key is ported", "Bowmen of Gondor" in text_of(mod, "text/export_units.txt"))
check("the UTF-16 file keeps its BOM",
      (mod.data / "text" / "export_units.txt").read_bytes()[:2] == b"\xff\xfe")
check("the port is one log entry", any(e.get("id") == res["id"] and e.get("mode") == "changeset"
                                       for e in config.load_log()))
check("the set's baseline is now the version ported onto",
      (sd / "base" / "export_descr_buildings.txt").read_bytes() == edb_before)
check("  so porting again finds nothing new to do",
      all(i.outcome in ("already", "conflict", "gone")
          for i in changesets.plan_port("AGO", mod).items))
undo(res["id"])
check("Undo takes the port back",
      (mod.data / "export_descr_buildings.txt").read_bytes() == edb_before)
check("  and puts the set back too: the baseline is the ORIGINAL again, so the "
      "edits are still there to port",
      (sd / "base" / "export_descr_buildings.txt").read_bytes() == orig_edb
      and any(i.key == "stables" for i in changesets.plan_port("AGO", mod).items))

# ---------------------------------------------------------------------------
print("\n6) one file out, one file in")
blob = changesets.export_bytes("AGO")
name = changesets.import_bytes(blob, "AGO from a friend")
check("the export imports under a name of its own",
      name == "AGO from a friend" and changesets.load(name)["imported"])
ago2 = make_mod("AGO_2", edu=new_edu, edb=new_edb)
p2 = changesets.plan_port(name, ago2)
check("an imported set ports onto another folder",
      any(i.key == "stables" and i.outcome == "clean" for i in p2.items))
r2 = changesets.apply_port(p2, {i.id: "mine" for i in p2.items if i.key == "stables"})
check("  and writes only the picked record there",
      "building stables" in text_of(ago2, "export_descr_buildings.txt")
      and "cost 250" not in text_of(ago2, "export_descr_buildings.txt"))
check("  and the folder it wrote to starts a set of its own, baselined on its own files",
      (changesets.set_dir("AGO_2") / "base" / "export_descr_buildings.txt").read_bytes()
      == new_edb.encode("latin-1"))
try:
    changesets._safe_rel("../../evil.txt")
    check("a path out of data/ in an imported set is refused", False)
except changesets.ChangeSetError:
    check("a path out of data/ in an imported set is refused", True)

# ---------------------------------------------------------------------------
print("\n7) Phase 53: sets switched in place")
eur = make_mod("EUR")
eur_edu0 = (eur.data / "export_descr_unit.txt").read_bytes()
eur_edb0 = (eur.data / "export_descr_buildings.txt").read_bytes()
save(eur, "export_descr_unit.txt",
     EDU.replace("stat_pri         7, 4, no, 0, 0", "stat_pri         9, 4, no, 0, 0").replace(CR, "\n"))
save(eur, "export_descr_buildings.txt",
     EDB.replace("            cost 300", "            cost 250").replace(CR, "\n"))
mine_a = (eur.data / "export_descr_unit.txt").read_bytes()
check("the first save starts the mod's first set, and it is on",
      changesets.active_of("EUR") == "EUR")

sw = changesets.plan_switch(eur, None)
check("switching it off is clean: every record goes back to the original",
      not sw.blocked and sw.off == "EUR" and sw.on is None)
r_off = changesets.apply_switch(sw)
check("  and the mod's files are the originals again, byte for byte",
      (eur.data / "export_descr_unit.txt").read_bytes() == eur_edu0
      and (eur.data / "export_descr_buildings.txt").read_bytes() == eur_edb0)
check("  the set is off, and still holds both its copies",
      changesets.active_of("EUR") is None
      and (changesets.set_dir("EUR") / "mine" / "export_descr_unit.txt").read_bytes() == mine_a)
check("  the switch's own writes were not recorded as an edit",
      not changesets.set_dir("EUR (2)").exists())

save(eur, "export_descr_unit.txt",
     EDU.replace("stat_pri         8, 5, no, 0, 0", "stat_pri         8, 7, no, 0, 0").replace(CR, "\n"))
mine_b = (eur.data / "export_descr_unit.txt").read_bytes()
check("with every set off, the next save starts a new one",
      changesets.active_of("EUR") == "EUR (2)")
check("  whose original is the mod as it shipped",
      (changesets.set_dir("EUR (2)") / "base" / "export_descr_unit.txt").read_bytes() == eur_edu0)
s7 = changesets.summary(eur)
check("the summary lists both versions and says which is on",
      {(v["name"], v["active"]) for v in s7["versions"]} == {("EUR", False), ("EUR (2)", True)})

sw = changesets.plan_switch(eur, "EUR")
check("switching to the first set takes the second out and puts the first in",
      not sw.blocked and sw.off == "EUR (2)" and sw.on == "EUR")
r_sw = changesets.apply_switch(sw)
check("  the files are the first set's version",
      (eur.data / "export_descr_unit.txt").read_bytes() == mine_a
      and b"cost 250" in (eur.data / "export_descr_buildings.txt").read_bytes())
check("  one set on at a time",
      changesets.active_of("EUR") == "EUR"
      and not changesets.load("EUR (2)")["active"])
check("  and the second set kept its version to come back to",
      (changesets.set_dir("EUR (2)") / "mine" / "export_descr_unit.txt").read_bytes() == mine_b)
check("the switch is one log entry",
      any(e.get("id") == r_sw["id"] and e.get("action") == "switch" for e in config.load_log()))

undo(r_sw["id"])
check("Undo takes the switch back: the second set's version is on disk again",
      (eur.data / "export_descr_unit.txt").read_bytes() == mine_b)
check("  and the sets are as they were: the second on, the first off",
      changesets.active_of("EUR") == "EUR (2)" and not changesets.load("EUR")["active"])

# the disk moves under the active set (an update touching the same line):
# a switch must refuse rather than guess
drift = (eur.data / "export_descr_unit.txt").read_bytes().replace(b"8, 7, no", b"8, 9, no")
(eur.data / "export_descr_unit.txt").write_bytes(drift)
sw = changesets.plan_switch(eur, "EUR")
check("a switch that would conflict is refused, and names the record",
      any(b["key"] == "Rohan Riders" and b["step"] == "out" for b in sw.blocked))
try:
    changesets.apply_switch(sw)
    check("  and cannot be applied anyway", False)
except changesets.ChangeSetError:
    check("  and cannot be applied anyway", True)
(eur.data / "export_descr_unit.txt").write_bytes(mine_b)

try:
    changesets.plan_switch(eur, "AGO")
    check("a set of another mod cannot be switched on here", False)
except changesets.ChangeSetError:
    check("a set of another mod cannot be switched on here", True)

new_name = changesets.rename("EUR (2)", "EUR with slower Rohan")
check("a set can be renamed, and stays on",
      changesets.active_of("EUR") == new_name == "EUR with slower Rohan")
save(eur, "export_descr_buildings.txt",
     text_of(eur, "export_descr_buildings.txt").replace("cost 400", "cost 450").replace(CR, "\n"))
check("  and records into its new name",
      (changesets.set_dir(new_name) / "mine" / "export_descr_buildings.txt").is_file())

shutil.rmtree(tmp, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
