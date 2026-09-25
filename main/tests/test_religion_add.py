"""Phase 60: add a religion - every region, the pip, and sums that stay 100.

    python -m tests.test_religion_add

1. largest_remainder: whole numbers in proportion that add up exactly.
2. Every region's religions line, on both installed mods' real descr_regions.txt:
   an add gives every line `name 0` and changes no sum; a starting share is
   taken from the other religions so the line is still 100; a region whose
   line does not add up to 100 cannot be given a share; a remove gives the
   share back; add-then-remove is the file byte for byte.
3. The whole add through the Minor Files plan, on a temp mod built from
   ROCSS's religion files: the list, the block, the lookup, the shown name,
   every region, the pip copied from islam's - one save and one Undo.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import campmap  # noqa: E402
from unittransfer import keyblock as kb  # noqa: E402
from unittransfer import minorfiles as mf  # noqa: E402
from unittransfer import transfer  # noqa: E402
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
REG = "world/maps/base/descr_regions.txt"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


# ---- 1) the arithmetic -----------------------------------------------------------------
print("\n1) largest_remainder")
lr = mf.largest_remainder
check("90 over 0/10/80/5/5/0 is 0/9/72/5/4/0: the two tied halves go first-listed first",
      lr([0, 10, 80, 5, 5, 0], 90) == [0, 9, 72, 5, 4, 0])
check("the parts always add up to the total", all(sum(lr(w, t)) == t for w in
      ([1, 1, 1], [7, 0, 93], [33, 33, 34], [0, 0, 1]) for t in (1, 17, 99, 100)))
check("all weights zero share it out evenly", lr([0, 0, 0], 7) == [3, 2, 2])

# ---- 2) the regions ------------------------------------------------------------------------
print("\n2) every region's religions line")
for name in ("ROCSS", "Divide_and_Conquer_EUR"):
    path = MODS / name / "data" / REG
    if not path.is_file():
        continue
    text = kb.read_text(path, mf.ENCODING)
    before = campmap.parse_regions(text)
    recs = [r for r in before.records if r.religions_line >= 0]
    sums = {r.name: r.religion_total for r in recs}
    plain, st = mf.edit_region_religions(text, add="zoroastrian")
    after = campmap.parse_regions(plain)
    check(f"{name}: every one of {st['lines']} lines gains zoroastrian 0, and no sum moves",
          all(r.religions.get("zoroastrian") == 0 for r in after.records if r.religions_line >= 0
              and r.religions) and all(r.religion_total == sums[r.name]
                                        for r in after.records if r.name in sums))
    first = next(r for r in recs if r.religion_total == 100)
    seeded, st = mf.edit_region_religions(text, add="zoroastrian", seeds={first.name: 25})
    got = campmap.parse_regions(seeded).by_name(first.name)
    check(f"{name}: {first.name} given 25% takes it from the rest and still adds up to 100 "
          f"({got.religions})", got.religions["zoroastrian"] == 25 and got.religion_total == 100)
    bad = next((r for r in recs if r.religion_total != 100), None)
    if bad is not None:
        _, st = mf.edit_region_religions(text, add="zoroastrian", seeds={bad.name: 10})
        check(f"{name}: {bad.name}, which adds up to {bad.religion_total}, cannot be given a share",
              st["unseedable"] == [bad.name])
    back, _ = mf.edit_region_religions(seeded, remove="zoroastrian")
    check(f"{name}: taking it out gives the share back, every line 100 again where it was",
          all(r.religion_total == sums[r.name] for r in campmap.parse_regions(back).records
              if r.name in sums))
    undone, _ = mf.edit_region_religions(plain, remove="zoroastrian")
    check(f"{name}: add then remove, with no share, is the file byte for byte", undone == text)

# ---- 3) the whole add ------------------------------------------------------------------------
REAL = MODS / "ROCSS" / "data"
if not (REAL / mf.RELIGIONS_REL).is_file():
    print("\nROCSS is not installed - the whole add is SKIPPED")
else:
    print("\n3) the whole add, on a temp mod built from ROCSS's files")
    root = Path(_tmp.mkdtemp(prefix="ut_religion_")) / "RelMod"
    data = root / "data"
    for rel in (mf.RELIGIONS_REL, mf.RELIGIONS_LOOKUP_REL, mf.RELIGIONS_LOC_REL,
                mf.RELIGIONS_LOC_REL + ".strings.bin", REG, "ui/pips/pip_islam.tga"):
        if (REAL / rel).is_file():
            (data / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, data / rel)

    class TinyMod:
        name = "RelMod"
        def __init__(self):
            self.root, self.data = root, data
    mod = TinyMod()
    snap = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    rf = campmap.parse_regions(kb.read_text(data / REG, mf.ENCODING))
    where = next(r.name for r in rf.records if r.religion_total == 100)
    body = {"tab": "religions", "action": "add", "name": "zoroastrian",
            "edits": {"name": "zoroastrian", "pip_path": "ui/pips/pip_zoroastrian.tga"},
            "loc": {"zoroastrian": "Zoroastrian"}, "pip_from": "islam",
            "seeds": [{"region": where, "share": 30}]}
    p = mf.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.touched())
    check("it writes the list and block, the lookup and every region",
          p.text and mf.RELIGIONS_LOOKUP_REL in p.extra and REG in p.extra)
    check("and copies islam's pip to where the new block points",
          p.copies == [("ui/pips/pip_islam.tga", "ui/pips/pip_zoroastrian.tga")])
    wrong = mf.plan(mod, dict(body, seeds=[{"region": "Atlantis", "share": 30}]))
    check("a region that is not on the map is refused, by name", any("Atlantis" in e for e in wrong.errors))
    over = mf.plan(mod, dict(body, seeds=[{"region": where, "share": 130}]))
    check("a share over 100 is refused", over.errors)
    res = mf.apply(p)
    got = campmap.parse_regions(kb.read_text(data / REG, mf.ENCODING)).by_name(where)
    check(f"written: {where} starts 30% zoroastrian and adds up to 100",
          got.religions.get("zoroastrian") == 30 and got.religion_total == 100)
    check("the pip is there", (data / "ui/pips/pip_zoroastrian.tga").read_bytes()
          == (data / "ui/pips/pip_islam.tga").read_bytes())
    check("the lookup and the list both carry it",
          "zoroastrian" in kb.read_text(data / mf.RELIGIONS_LOOKUP_REL, mf.ENCODING)
          and "religion zoroastrian" in kb.read_text(data / mf.RELIGIONS_REL, mf.ENCODING))
    transfer.undo(res["id"])
    now = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    check("one undo puts every file back and takes the pip away", now == snap)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
