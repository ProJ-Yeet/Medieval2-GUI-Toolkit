"""A transfer into a mod that ships only ``export_units.txt.strings.bin``, and a
transfer that fails halfway.

Run:  python -m tests.test_transfer_rollback

From a user's log (v2.4.9): every transfer into a mod with no
``text/export_units.txt`` died on reading it, AFTER the EDU block was written,
so each try left one more unit in the EDU with nothing behind it. What has to
hold:

* the text is rebuilt from the ``.strings.bin``, so the transfer goes through
  and the ``.txt`` it writes keeps every entry the archive had;
* a transfer that raises partway puts back every file it wrote, byte for byte,
  and creates nothing, and its error says so.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import localization, stringsbin, transfer       # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def unit(t, d):
    return (f"type             {t}\ndictionary       {d}\ncategory         infantry\n"
            "class            heavy\nvoice_type       Heavy\nsoldier          none, 20, 0, 1\n"
            "attributes       sea_faring\nownership        egypt\n")


LOC = ("¬ test\n{Ghulams}Ghulams\n{Ghulams_descr}Heavy slave soldiers.\n"
       "{Ghulams_descr_short}Slave soldiers.\n")
OLD = "¬ test\n{Old_Guard}Old Guard\n{Old_Guard_descr}Long\n{Old_Guard_descr_short}Short\n"


#: a battle-models file holding only the blank entry every one starts with
MODELDB = "22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n"


def mod_at(root: Path, edu: str, loc: str, as_bin: bool) -> Mod:
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir()
    (data / "unit_models" / "battle_models.modeldb").write_text(MODELDB, encoding="latin-1")
    (data / "export_descr_unit.txt").write_text(edu, encoding="latin-1")
    txt = data / "text" / "export_units.txt"
    if as_bin:
        stringsbin.write(stringsbin.bin_path_for(txt), stringsbin.compile_txt(loc))
    else:
        txt.write_text(loc, encoding="utf-16")
    return Mod(root)


def apply(src, dst):
    plan = transfer.plan_transfer(src, "Ghulams", dst, transfer.TransferOptions())
    return transfer.apply_transfer(plan)


tmp = Path(_tmp.mkdtemp(prefix="ut_rollback_"))
src = mod_at(tmp / "Src", unit("Ghulams", "Ghulams"), LOC, as_bin=False)

print("\n1) a destination with only the compiled archive")
dst = mod_at(tmp / "Dst", unit("Old Guard", "Old_Guard"), OLD, as_bin=True)
txt = dst.export_units_path
try:
    apply(src, dst)
    went = True
except Exception as e:                                           # noqa: BLE001
    print("   ", e)
    went = False
check("the transfer goes through", went)
check("  and writes the .txt", txt.exists())
loc = localization.parse_file(txt) if txt.exists() else None
check("  which has the new unit's text",
      loc is not None and loc.get("Ghulams") is not None and loc.get("Ghulams").name == "Ghulams")
check("  and keeps the archive's own entries",
      loc is not None and loc.get("Old_Guard") is not None
      and loc.get("Old_Guard").descr_short == "Short")
check("  read back as UTF-16", txt.exists() and txt.read_bytes()[:2] == b"\xff\xfe")

print("\n2) a transfer that fails after the EDU is written")
dst2 = mod_at(tmp / "Dst2", unit("Old Guard", "Old_Guard"), OLD, as_bin=True)
edu_before = dst2.edu_path.read_bytes()
real = localization.upsert_record


def boom(*a, **k):
    raise OSError("disk went away")


localization.upsert_record = boom
try:
    apply(src, dst2)
    err = ""
except Exception as e:                                           # noqa: BLE001
    err = str(e)
finally:
    localization.upsert_record = real
check("it raises", bool(err))
check("  saying the files were put back", "put back" in err and "disk went away" in err)
check("  the EDU is byte for byte as it was", dst2.edu_path.read_bytes() == edu_before)
check("  and no .txt was left behind", not dst2.export_units_path.exists())
check("  nor the archive touched", stringsbin.bin_path_for(dst2.export_units_path).exists())

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
