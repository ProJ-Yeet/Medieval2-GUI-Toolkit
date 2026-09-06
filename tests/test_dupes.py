"""Entries battle_models.modeldb lists more than once (unittransfer.dupes).

The game reads the FIRST block with a name and walks past every later one, so a
second block is a model the mod cannot reach and nothing anywhere says so. This
suite covers both ways out of that and the guard rails around them:

  * the audit finds every duplicated name, keyed by block index rather than by
    name, and says which later block is a byte-copy of the first and which is a
    different model (and what is different about it)
  * the first block of a name is refused for both actions, because it is the one
    the game reads and everything in the mod resolves to it
  * remove drops exactly that block, the header's entry count follows, and the
    file still parses
  * rename gives the block a name of its own: the model survives byte-for-byte
    under the new name and the entry the game reads is untouched
  * the refusals: a name already in the file, a name with a space, an index that
    is not a duplicate at all, the same block twice in one request
  * undo puts the file back byte-exact

It runs on a throwaway copy of a real mod's text files, with one duplicate of
its own making appended so the fixture is the same whichever mod is installed.
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp
from unittransfer import config, dupes, modeldb
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []
def check(label, cond):
    ok.append(bool(cond)); print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


SRC = _realmod.pick("Third_Age_Reforged", "Divide_and_Conquer_EUR",
                    need="unit_models/battle_models.modeldb")
print(f"measuring against {SRC.name}")


def fresh_mod() -> Path:
    """A copy of the mod's text files - nothing here reads an asset."""
    root = Path(_tmp.mkdtemp(prefix="ut_dupes_"))
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir(parents=True)
    for rel in ("export_descr_unit.txt", "text/export_units.txt",
                "unit_models/battle_models.modeldb", "descr_mount.txt",
                "descr_character.txt"):
        src = SRC / "data" / rel
        if src.exists():
            shutil.copy2(src, data / rel)
    return root


def plant(path: Path, name: str, new_scale: float) -> None:
    """Append a second block for ``name``, with its scale changed.

    The fixture has to be a *different* model rather than a copy, because the
    interesting half of this feature is the block that is worth keeping. The
    scale is the smallest thing that makes two blocks differ and it does not
    have to point at a file that exists.
    """
    db = modeldb.parse_file(path)
    src = db.by_name()[name]
    raw = src.raw
    # the scale is the first float after the length-prefixed name
    head = f"{len(name)} {name}"
    at = raw.index(head) + len(head)
    rest = raw[at:]
    lead = len(rest) - len(rest.lstrip())
    tok = rest[lead:].split(None, 1)[0]
    raw = raw[:at] + rest[:lead] + str(new_scale) + rest[lead + len(tok):]
    db.entries.append(modeldb.parse_entry_text(raw))
    db.entries[-1].raw = raw
    db.write(path)


cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

root = fresh_mod()
dbpath = root / "data/unit_models/battle_models.modeldb"
PLANTED = modeldb.parse_file(dbpath).entries[0].name
plant(dbpath, PLANTED, 1.75)
mod = Mod(root)
before = dbpath.read_bytes()

print("\n== the audit ==")
a = dupes.audit(mod)
rows = {r["name"]: r for r in a["rows"]}
check(f"{a['entry_count']} entries, {a['duplicated']} duplicated name(s), "
      f"{a['extra_blocks']} block(s) the game never reads", a["extra_blocks"] >= 1)
check(f"the planted duplicate of '{PLANTED}' is found", PLANTED in rows)
row = rows[PLANTED]
check("both of its blocks are listed, first one first",
      len(row["blocks"]) == 2 and row["blocks"][0]["first"]
      and not row["blocks"][1]["first"])
check("the later block is indexed after the first",
      row["blocks"][1]["index"] > row["blocks"][0]["index"])
check("it is reported as a different model, not a copy",
      not row["blocks"][1]["identical"] and not row["identical"])
check("and the difference is named: " + "; ".join(row["blocks"][1]["differs"]),
      any("scale" in d for d in row["blocks"][1]["differs"]))
check(f"a free name is suggested for it ({row['blocks'][1]['suggested']})",
      row["blocks"][1]["suggested"] not in {e.name for e in mod.modeldb.entries})
check("every row really does have more than one block",
      all(r["copies"] > 1 and len(r["blocks"]) == r["copies"] for r in a["rows"]))
check("every block's line number rises with its index",
      all(b1["line"] <= b2["line"] for r in a["rows"]
          for b1, b2 in zip(r["blocks"], r["blocks"][1:])))
check("the extra bytes counted are the later blocks only",
      a["extra_bytes"] == sum(b["bytes"] for r in a["rows"]
                              for b in r["blocks"] if not b["first"]))

print("\n== the first block of a name is never touched ==")
first_i = row["blocks"][0]["index"]
later_i = row["blocks"][1]["index"]
p = dupes.plan(mod, dupes.request_from_dict(
    {"actions": [{"index": first_i, "action": "remove"}]}))
check("removing the block the game reads is refused, and says why",
      p.errors and "FIRST block" in p.errors[0])
p = dupes.plan(mod, dupes.request_from_dict(
    {"actions": [{"index": first_i, "action": "rename", "new_name": "whatever_x"}]}))
check("renaming it is refused too", bool(p.errors))

print("\n== the refusals ==")
taken = mod.modeldb.entries[1].name
cases = [
    ("a name already in the file",
     {"index": later_i, "action": "rename", "new_name": taken}, "already exists"),
    ("a name with a space in it",
     {"index": later_i, "action": "rename", "new_name": "two words"}, "cannot contain spaces"),
    ("a rename with no new name",
     {"index": later_i, "action": "rename", "new_name": ""}, "needs a new name"),
    ("an index that is not in the file",
     {"index": 99999, "action": "remove"}, "no entry block"),
]
for label, act, phrase in cases:
    pp = dupes.plan(mod, dupes.request_from_dict({"actions": [act]}))
    check(f"{label} is refused: {phrase}",
          any(phrase in e for e in pp.errors) and not pp.text)
solo = next(i for i, e in enumerate(mod.modeldb.entries)
            if sum(1 for x in mod.modeldb.entries if x.name == e.name) == 1)
pp = dupes.plan(mod, dupes.request_from_dict({"actions": [{"index": solo, "action": "remove"}]}))
check("an entry that is only in the file once is refused",
      any("only in the file once" in e for e in pp.errors))
pp = dupes.plan(mod, dupes.request_from_dict(
    {"actions": [{"index": later_i, "action": "remove"},
                 {"index": later_i, "action": "rename", "new_name": "x_y_z"}]}))
check("the same block twice in one request is refused",
      any("in the request twice" in e for e in pp.errors))
pp = dupes.plan(mod, dupes.request_from_dict({"actions": []}))
check("an empty request is refused rather than writing the file unchanged",
      any("nothing is ticked" in e for e in pp.errors))

print("\n== rename: the block becomes a model the mod can reach ==")
new_name = row["blocks"][1]["suggested"]
was_later = mod.modeldb.entries[later_i]
was_first = mod.modeldb.entries[first_i]
p = dupes.plan(mod, dupes.request_from_dict(
    {"actions": [{"index": later_i, "action": "rename", "new_name": new_name}]}))
check("the plan is clean and says what it renames",
      not p.errors and len(p.renames) == 1 and not p.removes
      and any(new_name in c for c in p.changes))
check("and warns that nothing names the new entry yet",
      any("nothing in the mod names it yet" in w for w in p.warnings))
rec = dupes.apply(p)
after = modeldb.parse_text(dbpath.read_text(encoding=modeldb.ENCODING))
names = [e.name for e in after.entries]
check("the file still parses, with the same number of entries",
      len(after.entries) == len(mod.modeldb.entries))
check(f"'{new_name}' is now a name of its own, exactly once",
      names.count(new_name) == 1)
check(f"'{PLANTED}' is no longer duplicated", names.count(PLANTED) == 1)
renamed = after.by_name()[new_name]
check("the renamed block is the model that was unreachable, unchanged apart from its name",
      renamed.content_equals(was_later))
check("the entry the game reads is untouched",
      after.by_name()[PLANTED].content_equals(was_first))
check("the header's entry count is unchanged by a rename",
      after.header_ints[5] == modeldb.parse_text(
          before.decode(modeldb.ENCODING)).header_ints[5])
check("a second audit finds nothing left to do for that name",
      PLANTED not in {r["name"] for r in dupes.find(Mod(root))})

print("\n== undo ==")
undo(rec["id"])
check("undo puts battle_models.modeldb back byte-exact", dbpath.read_bytes() == before)

print("\n== remove: the block goes and the count follows ==")
mod = Mod(root)
p = dupes.plan(mod, dupes.request_from_dict(
    {"actions": [{"index": later_i, "action": "remove"}]}))
check("the plan is clean and says the file shrinks",
      not p.errors and len(p.removes) == 1 and any("->" in c for c in p.changes))
check("and warns that this one is not a copy, so a model goes with it",
      any("not a copy" in w for w in p.warnings))
n_before = len(mod.modeldb.entries)
head_before = mod.modeldb.header_ints[5]
rec = dupes.apply(p)
after = modeldb.parse_text(dbpath.read_text(encoding=modeldb.ENCODING))
check("one block fewer, and the file still parses", len(after.entries) == n_before - 1)
check("the header's entry count came down with it",
      after.header_ints[5] == head_before - 1)
check(f"'{PLANTED}' is left in the file exactly once",
      [e.name for e in after.entries].count(PLANTED) == 1)
check("and it is the block the game was already reading",
      after.by_name()[PLANTED].content_equals(was_first))
undo(rec["id"])
check("undo puts it back byte-exact", dbpath.read_bytes() == before)

print("\n== an identical copy is reported as one ==")
root2 = fresh_mod()
db2 = root2 / "data/unit_models/battle_models.modeldb"
d2 = modeldb.parse_file(db2)
name2 = d2.entries[0].name
d2.entries.append(d2.entries[0])          # a byte-for-byte second block
d2.write(db2)
mod2 = Mod(root2)
r2 = {r["name"]: r for r in dupes.find(mod2)}[name2]
check("a byte-identical second block is called identical, not different",
      r2["identical"] and r2["blocks"][1]["identical"] and not r2["blocks"][1]["differs"])
i2 = r2["blocks"][1]["index"]
p2 = dupes.plan(mod2, dupes.request_from_dict({"actions": [{"index": i2, "action": "remove"}]}))
check("removing it warns about nothing, because nothing is lost",
      not p2.errors and not any("not a copy" in w for w in p2.warnings))
p3 = dupes.plan(mod2, dupes.request_from_dict(
    {"actions": [{"index": i2, "action": "rename", "new_name": name2 + "_copy"}]}))
check("renaming it says plainly that this makes a second name for the same model",
      any("second name for the same model" in w for w in p3.warnings))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
