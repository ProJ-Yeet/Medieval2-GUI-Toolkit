"""Each faction keeps its own skin and its own unit cards across a transfer.

Reported: musketeers brought over from a Kingdoms campaign arrived with
England's textures and England's cards on both England and France. A unit the
game draws differently per faction has one texture record per faction in its
battle_models.modeldb entry and, often, one card per faction folder
(``ui/units/<faction>/#<dict>.tga``, ``ui/unit_info/<faction>/<dict>_info.tga``).
The transfer must carry each faction's own over, not the first one it finds.

The base game's Arquebusiers (a card and a skin per faction, read out of the
packs) into a temp copy of a real mod's database files, then Undo, which must
leave every file byte for byte as it was.

    python -m tests.test_transfer_faction_skins
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, gamepack, modeldb  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


GAME = _realmod.game()
if not (GAME / "packs").is_dir():
    print("  [skip] needs a packed base game install")
    sys.exit(0)
dest_mods = _realmod.installed()
if not dest_mods:
    print("  [skip] needs one real mod for the destination's files")
    sys.exit(0)

from unittransfer.transfer import TransferOptions, apply_transfer, plan_transfer, undo  # noqa: E402

tmp = Path(_tmp.mkdtemp(prefix="ut_facskins_"))
cfg = tmp / "cfg"
cfg.mkdir()
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

DB = ("export_descr_unit.txt", "text/export_units.txt", "text/expanded.txt",
      "unit_models/battle_models.modeldb",
      "descr_sm_factions.txt")
real = dest_mods[0]
root = tmp / "Dest"
for rel in DB:
    (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(real / "data" / rel, root / "data" / rel)


def snapshot():
    return {p.relative_to(root).as_posix(): hashlib.sha1(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


src = Mod(GAME)
dst = Mod(root)
UNIT = "Arquebusiers"
unit = src.edu.by_type()[UNIT]
both = [f for f in ("england", "france") if f in dst.faction_cultures]
check(f"the destination has both factions ({both})", len(both) == 2)
own = src.own_card_factions(unit)
check("the source has a card of its own for each", all(f in own for f in both)
      and md5(src.find_unit_card(unit, "england")) != md5(src.find_unit_card(unit, "france")))

before = snapshot()
print(f"\n1) {UNIT}: the plan")
plan = plan_transfer(src, UNIT, dst, TransferOptions())
cards = {rel: md5(p) for p, rel in plan.icon_files}
for f in both:
    rel = f"ui/units/{f}/#{unit.dictionary.lower()}.tga"
    got = next((h for r, h in cards.items() if r.lower() == rel), None)
    check(f"  {f}'s card is {f}'s own", got == md5(src.find_unit_card(unit, f)))
    info = src.find_unit_info(unit, f)
    irel = f"ui/unit_info/{f}/{unit.dictionary.lower()}_info.tga"
    got = next((h for r, h in cards.items() if r.lower() == irel), None)
    check(f"  {f}'s info card is {f}'s own", info is not None and got == md5(info))

print("\n2) applied")
rec = apply_transfer(plan)
db = modeldb.parse_file(root / "data" / "unit_models" / "battle_models.modeldb")
name = plan.add_entries[0][0]
entry = db.get(name)
srcent = src.modeldb.get(unit.soldier_model)
for f in both:
    mine = next((t for t in entry.main_textures if t.faction == f), None)
    theirs = next(t for t in srcent.main_textures if t.faction == f)
    srcfile, _w = gamepack.lookup(theirs.texture, src)
    landed = root / "data" / mine.texture if mine else None
    check(f"  {f}'s skin record names a file holding {f}'s texture",
          landed is not None and landed.is_file() and md5(landed) == md5(srcfile))
    card = root / "data" / "ui" / "units" / f / f"#{unit.dictionary.lower()}.tga"
    check(f"  {f}'s card on disk is {f}'s own",
          card.is_file() and md5(card) == md5(src.find_unit_card(unit, f)))
    info = root / "data" / "ui" / "unit_info" / f / f"{unit.dictionary.lower()}_info.tga"
    check(f"  {f}'s info card on disk is {f}'s own",
          info.is_file() and md5(info) == md5(src.find_unit_info(unit, f)))

print("\n3) undone")
undo(rec["id"])
check("every file is byte for byte as it was", snapshot() == before)

print("\n4) the faction prompt's rows, and a faction written under another")
from unittransfer import edu as edu_mod  # noqa: E402
dst = Mod(root)
plan = plan_transfer(src, UNIT, dst, TransferOptions())
rows = {r["src"]: r for r in plan.faction_rows}
check("a row per source faction, owners and skins", set(unit.ownership) <= set(rows))
check("  each with both in-game names", rows["england"]["src_name"] and rows["england"]["dest_name"])
names_differ = [f for f, r in rows.items() if "name_differs" in r["flags"]]
check(f"  england is flagged: the same code is another faction there ({names_differ})",
      dst.faction_names.get("england", "").lower() == "england" or "england" in names_differ)
missing = [f for f, r in rows.items() if not r["dest"]]
check("  a faction the destination lacks lands nowhere, flagged",
      all("missing" in rows[f]["flags"] or "dropped" in rows[f]["flags"] for f in missing))
pick = {"england": "", "france": "england"}
plan = plan_transfer(src, UNIT, dst, TransferOptions(faction_map=pick))
rows = {r["src"]: r for r in plan.faction_rows}
check("a pick wins over the code match", rows["france"]["dest"] == "england"
      and rows["france"]["how"] == "picked" and "dropped" in rows["england"]["flags"])
before = snapshot()
rec = apply_transfer(plan)
db = modeldb.parse_file(root / "data" / "unit_models" / "battle_models.modeldb")
entry = db.get(plan.add_entries[0][0])
recs = {t.faction: t for t in entry.main_textures}
fr_src = next(t for t in srcent.main_textures if t.faction == "france")
check("  the modeldb: france's skin is written as england's record, nothing else as england",
      [t.faction for t in entry.main_textures].count("england") == 1
      and md5(root / "data" / recs["england"].texture) == md5(gamepack.lookup(fr_src.texture, src)[0]))
facs_ok = set(dst.faction_cultures) | {"merc", "default"}
check("  no record for a faction the destination lacks",
      all(t.faction in facs_ok for t in entry.main_textures))
newu = Mod(root).edu.by_type()[plan.resolved_type]
check(f"  the EDU: ownership {newu.ownership} has england once and no france",
      newu.ownership.count("england") == 1 and "france" not in newu.ownership
      and all(o in dst.faction_cultures for o in newu.ownership))
card = root / "data" / "ui" / "units" / "england" / f"#{unit.dictionary.lower()}.tga"
check("  england's card is france's", card.is_file()
      and md5(card) == md5(src.find_unit_card(unit, "france")))
undo(rec["id"])
check("  undone byte for byte", snapshot() == before)

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
