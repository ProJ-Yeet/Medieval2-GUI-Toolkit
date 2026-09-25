"""Phase 56 (M12): several factions at once, and the faction files as a zip.

    python -m tests.test_factionbulk

1. The two text options, on their own: a title set outright (or added when the
   donor has none), and the donor's shown name swapped as a whole word.
2. The zip: every faction file and the asked-for art, laid out under data/.
3. A batch, on a real mod's faction files: the zip of ROCSS unpacked into a
   temp folder is the mod, so nothing real is written. Three factions from one
   donor plan one on top of the other, a slot asked for twice is refused, the
   write is one record, and undoing it puts every byte back.
"""
import io
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import factionclone as fc  # noqa: E402
from unittransfer import factions as fa  # noqa: E402
from unittransfer import keyblock as kb  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer import config  # noqa: E402

# Every save and undo here goes to a config of its own, never the real undo log
# and backups: a suite run beside others would race them on transfers.json. It
# starts from a copy of the real settings, so the game root and the M2EX marks
# read the same, and nothing is written back to them.
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


# ---- 1) the text options -------------------------------------------------------
print("\n1) titles and the shown name, in expanded.txt")
T = ("{ENGLAND}\tMordor\n{EMT_ENGLAND_SPY}\tMordor Scout\n"
     "{EMT_ENGLAND_FACTION_HEIR_TITLE}\tHeir\n{ENGLAND_UNIT}Mordorim of Mordor\n")
out, n = fc.clone_expanded(T, "england", "rhun", "Rhûn", rename=True,
                           titles={"leader": "Khan", "heir": "Prince", "adjective": "x"})
new = {l.split("}")[0][1:]: l.split("}", 1)[1].strip() for l in out.splitlines()
       if l.startswith("{") and "RHUN" in l}
check("the shown name is the one given", new.get("RHUN") == "Rhûn")
check("the donor's name becomes the new one where it stands as a word",
      new.get("EMT_RHUN_SPY") == "Rhûn Scout")
check("and only as a word: Mordorim stays Mordorim", new.get("RHUN_UNIT") == "Mordorim of Rhûn")
check("a title the donor has is set to the one asked for", new.get("EMT_RHUN_FACTION_HEIR_TITLE") == "Prince")
check("a title the donor lacks is added", new.get("EMT_RHUN_FACTION_LEADER_TITLE") == "Khan")
check("a key that is not one of the five is ignored", not any("ADJ" in k for k in new))
plain, _ = fc.clone_expanded(T, "england", "rhun", "Rhûn")
check("without rename the donor's text is copied as it was (the old behaviour)",
      "{EMT_RHUN_SPY}\tMordor Scout" in plain)

# ---- 2) and 3) on a real mod's faction files --------------------------------------
REAL = MODS / "ROCSS"
if not (REAL / "data" / fa.REL).is_file():
    print("\nROCSS is not installed - the real half is SKIPPED")
else:
    print("\n2) the faction files of ROCSS, as a zip")
    real = Mod(REAL)
    roster = fa.parse_file(fa.path_for(real))
    slots = [fa.slot_of(r.name) for r in roster.records]
    donor = next(s for s in slots if s not in ("slave", "papal_states"))
    files = fc.export_files(real, [donor])
    blob, rels = fc.export_zip(real, [donor])
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = z.namelist()
    check(f"{len(rels)} files, every one under data/ as the game lays it out",
          names == ["data/" + r for r in rels] and rels == files)
    check("the roster, the EDU, the EDB and the compiled text are all in it",
          {"data/descr_sm_factions.txt", "data/export_descr_unit.txt",
           "data/export_descr_buildings.txt", "data/text/expanded.txt.strings.bin"} <= set(names))
    art = [r for r in rels if r.split("/")[0] in fc.ART_ROOTS]
    check(f"and the art of `{donor}`, found the way the clone finds it ({len(art)} files)",
          art and all(donor in r.lower() for r in art))
    check("asked for no art, it carries none",
          not [r for r in fc.export_files(real) if r.split("/")[0] in fc.ART_ROOTS])

    print(f"\n3) three factions from `{donor}` in one batch, on that zip unpacked")
    root = Path(_tmp.mkdtemp(prefix="ut_factionbulk_")) / "BulkMod"
    z.extractall(root)
    mod = Mod(root)
    before = {p.relative_to(root).as_posix(): p.read_bytes()
              for p in root.rglob("*") if p.is_file()}
    rows = [{"new": "bulk_one", "label": "First Realm", "titles": {"leader": "High King"}},
            {"new": "bulk_two", "label": "Second Realm"},
            {"new": "bulk_three"}]
    body = {"source": donor, "rows": rows, "art": True, "rename": True}
    capped = fc.plan_many(mod, body)
    free = fa.FACTION_LIMIT - len(roster.records)
    check(f"the engine's {fa.FACTION_LIMIT}-slot ceiling is held across the batch: "
          f"{free} free, so row {free + 1} on is refused",
          free < 3 and any(f"row {free + 1}" in e and "faction slots" in e for e in capped.errors)
          or free >= 3 and not capped.errors)

    class Unlimited(Mod):
        """The same folder, marked M2EX: the ceiling is lifted."""
        m2ex = True
    mod = Unlimited(root)
    bp = fc.plan_many(mod, body)
    pay = bp.payload()
    check(f"the batch plans clean ({len(pay['files'])} files, {pay['asset_files']} art files)",
          pay["ok"] and not bp.errors)
    ros = fa.parse_text(bp.final[fa.REL][0])
    check("each row planned on top of the last: the final roster has all three",
          {"bulk_one", "bulk_two", "bulk_three"} <= {fa.slot_of(r.name) for r in ros.records})
    twice = fc.plan_many(mod, dict(body, rows=rows + [{"new": "bulk_two"}]))
    check("a slot asked for twice is refused, naming the row",
          any("row 4" in e and "already a faction" in e for e in twice.errors))
    check("and a refused batch is not ok to write", not twice.payload()["ok"])
    empty = fc.plan_many(mod, {"source": donor, "rows": []})
    check("an empty batch is refused", empty.errors)

    res = fc.apply_many(bp)
    check("the write is one record, naming all three", res["factions"] == ["bulk_one", "bulk_two", "bulk_three"])
    after_ros = fa.parse_file(fa.path_for(Mod(root)))
    check("the written roster re-parses with all three",
          {"bulk_one", "bulk_two", "bulk_three"} <= {fa.slot_of(r.name) for r in after_ros.records})
    exp = kb.read_text(root / "data" / "text" / "expanded.txt", "utf-16")
    check("the first carries its shown name and the leader title asked for",
          "{BULK_ONE}\tFirst Realm" in exp.replace("\r", "") or "{BULK_ONE}First Realm" in exp
          or any(l.startswith("{BULK_ONE}") and l.endswith("First Realm") for l in exp.splitlines()))
    check("the leader title is set", any(l.startswith("{EMT_BULK_ONE_FACTION_LEADER_TITLE}")
                                         and l.rstrip().endswith("High King") for l in exp.splitlines()))
    check("the third, given no shown name, keeps the donor's text as it was",
          any(l.startswith("{BULK_THREE}") for l in exp.splitlines()))
    made_art = [p for p in (root / "data").rglob("*") if p.is_file() and "bulk_two" in p.name.lower()]
    check(f"each faction got its own copy of the art ({len(made_art)} files for bulk_two)",
          bool(made_art) == bool(art))

    transfer.undo(res["id"])
    after = {p.relative_to(root).as_posix(): p.read_bytes()
             for p in root.rglob("*") if p.is_file()}
    check("one undo restores every file byte for byte",
          all(after.get(k) == v for k, v in before.items()))
    left = sorted(set(after) - set(before))
    check(f"and leaves no copied art behind ({len(left)} extra)", not left)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
