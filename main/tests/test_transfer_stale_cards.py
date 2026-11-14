"""A renamed transfer never lands on a dictionary whose cards are still on disk.

Run:  python -m tests.test_transfer_stale_cards

From a user's report (R-20261113-21FF9B, v2.4.12): Musketeers brought from one
mod into another that already had a Musketeers came in as ``Musketeers_copy_2``.
The destination still held ``#Musketeers_copy_2.tga`` cards for France and the
mercenaries from an earlier unit that was gone, all of them England's picture.
The new name was free in the EDU and the text, so it was taken; the icon rule
kept the destination's files; and France showed England's card in game. What
has to hold:

* a dictionary the tool picks for a rename skips any name that still has a unit
  card or an info card in the destination, so nothing stale is reused;
* every faction then gets its own card from the source, France included.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def unit(t, d, owners):
    return (f"type             {t}\ndictionary       {d}\ncategory         infantry\n"
            "class            missile\nvoice_type       Light\nsoldier          none, 20, 0, 1\n"
            f"attributes       sea_faring\nownership        {owners}\n")


MODELDB = "22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n"


def mod_at(root: Path, edu: str, loc: str) -> Path:
    data = root / "data"
    (data / "text").mkdir(parents=True)
    (data / "unit_models").mkdir()
    (data / "unit_models" / "battle_models.modeldb").write_text(MODELDB, encoding="latin-1")
    (data / "export_descr_unit.txt").write_text(edu, encoding="latin-1")
    (data / "text" / "export_units.txt").write_text(loc, encoding="utf-16")
    return root


def put(root: Path, rel: str, raw: bytes):
    p = root / "data" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(raw)


tmp = Path(_tmp.mkdtemp(prefix="ut_stalecards_"))
LOC = "¬ t\n{Musketeers}Musketeers\n{Musketeers_descr}Long\n{Musketeers_descr_short}Short\n"

src_root = mod_at(tmp / "Src", unit("Musketeers", "Musketeers", "england, france"), LOC)
for fac in ("england", "france"):
    put(src_root, f"ui/units/{fac}/#Musketeers.tga", f"card {fac}".encode())
    put(src_root, f"ui/unit_info/{fac}/Musketeers_info.tga", f"info {fac}".encode())

dst_root = mod_at(tmp / "Dst", unit("Musketeers", "Musketeers", "england, france"), LOC)
# what an earlier unit, long gone from the EDU and the text, left behind
for rel in ("ui/units/france/#Musketeers_copy.tga", "ui/units/mercs/#Musketeers_copy.tga",
            "ui/unit_info/france/Musketeers_copy_info.tga"):
    put(dst_root, rel, b"card england")

print("\n1) the planned name")
plan = transfer.plan_transfer(Mod(src_root), "Musketeers", Mod(dst_root),
                              transfer.TransferOptions(on_conflict="rename"))
check("the unit is renamed", plan.resolved_type != "Musketeers")
check("its dictionary is not the one the stale cards are under",
      plan.resolved_dict.lower() != "musketeers_copy")
check("  and no icon of the new unit already exists in the destination",
      not [c for c in plan.asset_conflicts if c.kind == "icon"])

print("\n2) the cards written")
transfer.apply_transfer(plan)
d = plan.resolved_dict
for fac in ("england", "france"):
    card = dst_root / "data" / f"ui/units/{fac}/#{d}.tga"
    check(f"{fac} wears its own card", card.exists() and card.read_bytes() == f"card {fac}".encode())
check("the stale cards are left where they were",
      (dst_root / "data/ui/units/france/#Musketeers_copy.tga").read_bytes() == b"card england")

print("\n3) a dictionary the user typed is theirs to keep")
plan2 = transfer.plan_transfer(Mod(src_root), "Musketeers", Mod(dst_root),
                               transfer.TransferOptions(on_conflict="rename",
                                                        new_dictionary="Musketeers_copy"))
check("it is used as asked, the stale cards reported as conflicts",
      plan2.resolved_dict == "Musketeers_copy"
      and any(c.kind == "icon" for c in plan2.asset_conflicts))

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
