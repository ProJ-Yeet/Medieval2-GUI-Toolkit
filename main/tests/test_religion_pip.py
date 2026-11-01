"""96f: a religion from nothing - its pip drawn here, not copied.

    python -m tests.test_religion_pip

1. draw_pip: the size asked, a clear corner, a coloured disc, a refused colour.
2. pip_size: the size most of a mod's pips are, 16 when it has none.
3. The whole add through the Minor Files plan, on a temp mod built from Divide
   and Conquer's religion files: the pip drawn at DaC's own size where the new
   block points, one save and one Undo; a pip already there is kept.
"""
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config  # noqa: E402
from unittransfer import minorfiles as mf  # noqa: E402
from unittransfer import transfer  # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


print("\n1) draw_pip")
im = Image.open(io.BytesIO(mf.draw_pip("elvish", "#3060c0", 16)))
check("16x16 RGBA", im.size == (16, 16) and im.mode == "RGBA")
check("the corner is clear", im.getpixel((0, 0))[3] == 0)
px = im.getpixel((3, 8))
check(f"the disc is the colour picked ({px})", px[3] == 255 and px[2] > px[0])
check("32 when asked", Image.open(io.BytesIO(mf.draw_pip("x", "a08040", 32))).size == (32, 32))
try:
    mf.draw_pip("x", "blue")
    check("a colour not #rrggbb is refused", False)
except mf.MinorError as e:
    check("a colour not #rrggbb is refused, by name", "blue" in e.message)


class TinyMod:
    name = "RelMod"

    def __init__(self, root):
        self.root, self.data = root, root / "data"


print("\n2) pip_size")
empty = TinyMod(Path(_tmp.mkdtemp(prefix="ut_religion_")) / "Empty")
check("16 with no pips", mf.pip_size(empty) == 16)

REAL = _realmod.mods() / "Divide_and_Conquer_EUR" / "data"
if not (REAL / mf.RELIGIONS_REL).is_file():
    print("\nDivide and Conquer is not installed - the whole add is SKIPPED")
else:
    print("\n3) the whole add, on a temp mod built from DaC's files")
    root = Path(_tmp.mkdtemp(prefix="ut_religion_")) / "RelMod"
    data = root / "data"
    for rel in (mf.RELIGIONS_REL, mf.RELIGIONS_LOOKUP_REL, mf.RELIGIONS_LOC_REL,
                mf.RELIGIONS_LOC_REL + ".strings.bin"):
        if (REAL / rel).is_file():
            (data / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, data / rel)
    shutil.copytree(REAL / "ui" / "pips", data / "ui" / "pips")
    mod = TinyMod(root)
    check(f"DaC's pips are mostly 16 ({mf.pip_size(mod)})", mf.pip_size(mod) == 16)
    snap = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    body = {"tab": "religions", "action": "add", "name": "valar",
            "edits": {"name": "valar", "pip_path": "ui/pips/pip_valar.tga"},
            "loc": {"valar": "Valar"}, "pip_draw": "#d0c060", "regions": False}
    p = mf.plan(mod, body)
    check(f"the plan is clean ({p.errors})", not p.errors and p.touched())
    check("one pip drawn, none copied", [d for d, _ in p.drawn] == ["ui/pips/pip_valar.tga"]
          and not p.copies)
    bad = mf.plan(mod, dict(body, pip_draw="nope"))
    check("a bad colour stops the plan", bad.errors)
    res = mf.apply(p)
    with Image.open(data / "ui/pips/pip_valar.tga") as got:   # closed, or Windows keeps it from Undo
        size = got.size
    check(f"written at 16x16 ({size})", size == (16, 16))
    check("the block points at it", "pip_valar.tga" in (data / mf.RELIGIONS_REL).read_text(encoding="latin-1"))
    transfer.undo(res["id"])
    now = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    check("one undo puts every file back and takes the pip away", now == snap)
    kept = mf.plan(mod, dict(body, edits={"name": "valar", "pip_path": "ui/pips/pip_elvish.tga"}))
    check("a pip already there is kept, and said", not kept.drawn
          and any("pip_elvish" in w for w in kept.warnings))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
