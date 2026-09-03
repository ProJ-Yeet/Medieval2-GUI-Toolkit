"""Faction skin coverage - 🛡 Fix ownership and 🌐 All factions.

A modeldb entry carries one texture record per faction and the game reads the
record for the faction whose army is on the field, so an entry with no record for
a faction that fields a unit drawn with it is a unit that does not show up right
for that faction. Nothing in either file says the two lists have to agree, which
is why it goes unnoticed.

Built on a mod this file writes from scratch. Covers:

  * which factions an entry *should* have, read off the units: every model slot
    counts (`soldier`, `officer`, `armour_ug_models`), `slave` counts, and an
    ownership token the faction roster does not define does NOT - it is reported
    instead, because a culture name written into the modeldb is a skin no faction
    reads;
  * `mode="all"`, which takes the answer from the roster instead;
  * the write: records are only ever ADDED, a new one is a clone of an existing
    record (same texture paths), the group counts are bumped to match, and the
    entry re-parses;
  * an entry with no texture record at all is left alone - there is nothing to
    clone from - and one already covered is not touched;
  * undo restores the modeldb byte-exact.

    python -m tests.test_ownership
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import bmdb, config, edit, modeldb
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


ROSTER = "\n".join([
    "faction\t\tengland",
    "culture\t\tnorthern_european",
    "",
    "faction\t\tfrance",
    "culture\t\tnorthern_european",
    "",
    "faction\t\tspain",
    "culture\t\tsouthern_european",
    "",
    "faction\t\tslave",
    "culture\t\tsouthern_european",
    "",
]) + "\n"

EDU = "\n".join([
    # england + france, drawn with `shared` (soldier) and `shared_ug` (upgrade)
    "type\t\talpha unit",
    "dictionary\talpha",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tshared, 60, 0, 1.2",
    "armour_ug_models\tshared_ug",
    "ownership\tengland, france",
    "",
    # spain only, same soldier entry - so `shared` needs three factions in all
    "type\t\tbeta unit",
    "dictionary\tbeta",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tshared, 60, 0, 1.2",
    "officer\t\tofficer_model",
    "ownership\tspain",
    "",
    # a rebel unit: `slave` is a real texture record and its entry is missing one
    "type\t\tgamma unit",
    "dictionary\tgamma",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\trebel_model, 60, 0, 1.2",
    "ownership\tslave",
    "",
    # ownership naming something the roster does not define - reported, never written
    "type\t\tdelta unit",
    "dictionary\tdelta",
    "category\tinfantry",
    "class\t\tlight",
    "soldier\t\tculture_model, 60, 0, 1.2",
    "ownership\tnorthern_european, england",
    "",
]) + "\n"


def _s(v: str) -> str:
    """A string as the file stores it: ``<length> <that many characters>``."""
    return f"{len(v)} {v}"


#: The vanilla ``blank`` sentinel a modeldb opens with - the name, then 39
#: reserved ints. Present on purpose: a file WITHOUT one makes the game pad its
#: first real entry with eight extra int pairs (``ModelEntry.first_entry_pad``),
#: and a fixture that tripped over that would be testing the reader, not this.
BLANK = "5 blank " + " ".join(["0"] * 39) + "\n"


def entry_text(name, factions, texture="unit_models/x/textures/x.texture"):
    """One modeldb entry: one LOD, one texture group and one attachment group.

    Hand-written in the file's own format rather than serialised, because there
    is no serialiser - entries are kept verbatim - and because the whole point of
    the code under test is that it keeps every ``<length>`` right when it adds a
    record. A fixture built by the writer could not catch the writer being wrong.
    """
    mesh = "unit_models/x/x_lod0.mesh"
    lines = [_s(name), "1.0", "1", f"{_s(mesh)} 121", str(len(factions))]
    for f in factions:                       # faction, texture, normal, sprite
        lines.append(f"{_s(f)} {_s(texture)} 0 0")
    lines.append(str(len(factions)))         # the attachment group, same shape
    for f in factions:
        lines.append(f"{_s(f)} {_s(texture)} 0 0")
    lines += ["1",                           # one animation set
              f"{_s('MTW2_Spear')} {_s('MTW2_Spear_Primary')} "
              f"{_s('MTW2_Spear_Secondary')} 0 0",
              "-1", "0 0 0 0 0 0"]           # torch index, then its six floats
    return "\n".join(lines) + "\n"


ENTRIES = [
    # short of `spain` (beta unit's ownership) - the headline case
    ("shared", ["england", "france"]),
    # short of `france` - an armour upgrade tier is drawn on the field too
    ("shared_ug", ["england"]),
    # an officer model is drawn on the field too, and this one has only england
    ("officer_model", ["england"]),
    # a rebel entry with no slave record
    ("rebel_model", ["england"]),
    # already covered: nothing should touch it
    ("culture_model", ["england"]),
    # nothing is drawn with it - "units" mode has nothing to say, "all" does
    ("orphan_model", ["england"]),
]

#: The file's own header: the archive magic, then eight ints of which the sixth
#: is the entry count. Written by hand rather than through ``ModelDb.to_text`` so
#: the fixture is a FILE this suite controls, the way a mod's is.
MODELDB = (f"{len(modeldb.ARCHIVE_MAGIC)} {modeldb.ARCHIVE_MAGIC} "
           f"3 0 0 0 0 {len(ENTRIES) + 1} 0 0\n"     # +1 for the blank sentinel
           + BLANK + "".join(entry_text(n, f) for n, f in ENTRIES))


def fresh_mod() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ut_own_"))
    data = root / "data"
    (data / "unit_models").mkdir(parents=True)
    (data / "export_descr_unit.txt").write_text(EDU, encoding="latin-1")
    (data / "descr_sm_factions.txt").write_text(ROSTER, encoding="latin-1")
    (data / "unit_models" / "battle_models.modeldb").write_text(
        MODELDB, encoding=modeldb.ENCODING)
    return root


cfg = Path(tempfile.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = fresh_mod()
mod = Mod(root)
before_db = (root / "data/unit_models/battle_models.modeldb").read_bytes()

print("\n== which factions the units ask for ==")
want = bmdb.unit_factions(mod)
check("a soldier entry collects every owner of every unit that names it",
      sorted(want["shared"]) == ["england", "france", "spain"])
check("an armour upgrade tier counts - it is drawn on the field",
      sorted(want["shared_ug"]) == ["england", "france"])
check("so does an officer", sorted(want["officer_model"]) == ["spain"])
check("slave counts: it is the generic rebel skin, not a placeholder",
      want["rebel_model"] == ["slave"])
check("an ownership token the roster does not define is not asked for",
      want["culture_model"] == ["england"])
check("an entry no unit names asks for nothing",
      "orphan_model" not in want)
check("…and that token is reported instead, with who names it",
      bmdb.unknown_ownership(mod) == {"northern_european": ["delta unit"]})

print("\n== the audit, mode=units ==")
a = bmdb.ownership_audit(mod, "units")
rows = {r["entry"]: r for r in a["rows"]}
check("only the entries that are short are listed",
      sorted(rows) == ["officer_model", "rebel_model", "shared", "shared_ug"])
check("each row names exactly what it is missing",
      rows["shared"]["missing"] == ["spain"]
      and rows["shared_ug"]["missing"] == ["france"]
      and rows["rebel_model"]["missing"] == ["slave"])
check("an entry that already has what its units need is counted, not listed",
      a["covered"] == 1)
check("an entry no unit is drawn with is counted apart", a["no_unit"] == 1)
check("the totals add up", a["added_records"] == 4 and a["row_count"] == 4)
check("it says how much bigger the modeldb gets", a["bytes"] > 0)
check("a row says which units are drawn with the entry",
      rows["shared"]["used_by"] == ["alpha unit", "beta unit"])

print("\n== the audit, mode=all ==")
b = bmdb.ownership_audit(mod, "all")
brows = {r["entry"]: r for r in b["rows"]}
check("every entry short of ANY roster faction is listed", b["row_count"] == 6)
check("including the one no unit uses", "orphan_model" in brows)
check("the missing list is the roster minus what the entry has",
      brows["shared"]["missing"] == ["spain", "slave"])
check("it is a much bigger write than mode=units",
      b["added_records"] > a["added_records"] and b["bytes"] > a["bytes"])
check("the roster is reported so the dialog can name it",
      b["slots"] == ["england", "france", "spain", "slave"])

print("\n== the edits it hands the planner ==")
edits = {e["entry"]: e["factions"] for e in bmdb.ownership_edits(mod, "units")}
check("existing factions come first, in the entry's own order",
      edits["shared"][:2] == ["england", "france"])
check("…and the missing ones are appended", edits["shared"] == ["england", "france", "spain"])
check("nothing is ever dropped, so the write can only append",
      all(set(bmdb.ownership_edits(mod, m)[0]["factions"]) >= {"england"}
          for m in ("units", "all")))
check("`only` narrows it to the entries asked for",
      [e["entry"] for e in bmdb.ownership_edits(mod, "units", ["shared"])] == ["shared"])
check("an unknown entry name in `only` is simply not found",
      bmdb.ownership_edits(mod, "units", ["nosuch"]) == [])

print("\n== writing it ==")
plan = edit.plan_bmdb(mod, edit.bmdb_request_from_dict(
    {"model_edits": bmdb.ownership_edits(mod, "units")}))
check("no errors", not plan.errors)
check("the plan says which entries gained which skins",
      any("shared" in c and "spain" in c for c in plan.changes))
rec = edit.apply_edit(plan)

mod.drop_caches()
after = mod.modeldb.by_name()
check("the entry now has the record",
      [t.faction for t in after["shared"].main_textures]
      == ["england", "france", "spain"])
check("the attachment group got it too - both groups or neither",
      [t.faction for t in after["shared"].attach_textures]
      == ["england", "france", "spain"])
check("the new record is a clone: same texture path as the ones beside it",
      len({t.texture for t in after["shared"].main_textures}) == 1)
check("an armour tier and an officer are fixed the same way",
      [t.faction for t in after["shared_ug"].main_textures] == ["england", "france"]
      and [t.faction for t in after["officer_model"].main_textures] == ["england", "spain"])
check("a rebel entry gets its slave record",
      [t.faction for t in after["rebel_model"].main_textures] == ["england", "slave"])
check("the entry that was already covered is untouched",
      [t.faction for t in after["culture_model"].main_textures] == ["england"])
check("so is the one no unit is drawn with",
      [t.faction for t in after["orphan_model"].main_textures] == ["england"])
check("the file still holds every entry", len(after) == len(ENTRIES))
check("the length prefixes are still right - the file re-parses from disk",
      modeldb.parse_file(mod.modeldb_path).by_name()["shared"].main_textures[2].faction
      == "spain")

print("\n== a second run has nothing left to do ==")
mod.drop_caches()
again = bmdb.ownership_audit(mod, "units")
check("mode=units is finished", again["row_count"] == 0)
check("…and says every entry is covered or unused",
      again["covered"] + again["no_unit"] == len(ENTRIES))

print("\n== undo ==")
undo(rec["id"])
check("battle_models.modeldb is byte-exact again",
      (root / "data/unit_models/battle_models.modeldb").read_bytes() == before_db)

print("\n== a mod with no faction roster ==")
bare = Path(tempfile.mkdtemp(prefix="ut_own_bare_"))
(bare / "data" / "unit_models").mkdir(parents=True)
(bare / "data/export_descr_unit.txt").write_text(EDU, encoding="latin-1")
(bare / "data/unit_models/battle_models.modeldb").write_text(
    MODELDB, encoding=modeldb.ENCODING)
bmod = Mod(bare)
noroster = bmdb.ownership_audit(bmod, "all")
check("says it has no roster rather than guessing",
      noroster["has_roster"] is False and noroster["slot_count"] == 0)
check("mode=all adds nothing without one", noroster["row_count"] == 0)
check("and reports no unknown tokens, since it cannot tell",
      noroster["unknown_ownership"] == [])

print(f"\n{sum(ok)}/{len(ok)} checks - {'ALL PASSED' if all(ok) else 'FAILURES ABOVE'}")
sys.exit(0 if all(ok) else 1)
