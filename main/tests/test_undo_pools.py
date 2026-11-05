"""Two things a unit's other lines need beyond the delete itself.

Run:  python -m tests.test_undo_pools

Kirsi's Bigger Map pooled five units its unit file had lost, which the stock
engine refuses. test_delete_refs covers the Unit Editor's delete; this covers:

* a delete on files with Windows line ends writes them back with those line
  ends, never "\\r\\r\\n" (write_refs used write_text, which doubles them);
* undoing a transfer whose unit was pooled by hand afterwards takes those pool
  lines out too, and the record says how many (needs the base game's
  crusades campaign installed; skipped without it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config, edit                               # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402
from unittransfer.transfer import undo                              # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


EDU = ("type             Spearmen\ndictionary       Spearmen\ncategory         infantry\n"
       "soldier          spearmen, 40, 0, 1\n\n"
       "type             Greek Firethrower\ndictionary       Greek_Firethrower\ncategory         infantry\n"
       "soldier          greek_firethrower, 16, 0, 1\n\n")
EDB = ("building barracks\n{\n    levels town_watch\n    {\n        town_watch city requires factions { england, }\n"
       "        {\n            capability\n            {\n"
       '                recruit_pool "Spearmen"  1  0.7  6  0  requires factions { england, }\n'
       '                recruit_pool "Greek Firethrower"  1  0.7  6  0  requires factions { byzantium, }\n'
       "            }\n        }\n    }\n}\n")
MERC = ("pool Thrace\n\tregions Constantinople_Province\n"
        "\tunit Spearmen,\t\texp 0 cost 300 replenish 0.1 - 0.2 max 2 initial 1\n"
        "\tunit Greek Firethrower\t\texp 0 cost 1280 replenish 0.02 - 0.06 max 2 initial 1\n"
        "end\n")
BMDB = "22 serialization::archive 3 0 0 0 0 0 0 0\n"

real = config.get_med2_root()       # before the config folder is swapped out
config.CONFIG_DIR = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
tmp = Path(_tmp.mkdtemp(prefix="ut_undopools_"))
data = tmp / "M" / "data"
merc_rel = "world/maps/base/descr_mercenaries.txt"
(data / "world" / "maps" / "base").mkdir(parents=True)
(data / "unit_models").mkdir(parents=True)
for rel, text in (("export_descr_unit.txt", EDU), ("export_descr_buildings.txt", EDB),
                  (merc_rel, MERC), ("unit_models/battle_models.modeldb", BMDB)):
    (data / rel).write_bytes(text.replace("\n", "\r\n").encode("latin-1"))


def plan_delete():
    return edit.plan_edit(Mod(tmp / "M"), edit.request_from_dict({
        "unit": "Greek Firethrower", "delete": True,
        "delete_options": {"remove_loc": False, "remove_models": False,
                           "remove_assets": False, "remove_icons": False}}))


print("\n1) a delete keeps Windows line ends")
rec = edit.apply_edit(plan_delete())
check("written without the lines",
      "Greek Firethrower" not in (data / "export_descr_buildings.txt").read_text("latin-1")
      and "Greek Firethrower" not in (data / merc_rel).read_text("latin-1"))
check("  keeping their Windows line ends, never doubling the \\r",
      b"\r\r" not in (data / "export_descr_buildings.txt").read_bytes()
      and b"\r\r" not in (data / merc_rel).read_bytes()
      and b"\r\n" in (data / merc_rel).read_bytes())
undo(rec["id"])
check("undo puts both files back byte for byte",
      (data / "export_descr_buildings.txt").read_bytes() == EDB.replace("\n", "\r\n").encode("latin-1")
      and (data / merc_rel).read_bytes() == MERC.replace("\n", "\r\n").encode("latin-1"))

print("\n2) only a unit transfer's undo looks at the pools")
from unittransfer import transfer                                   # noqa: E402
edb_p = data / "export_descr_buildings.txt"
ghost = '                recruit_pool "Ghost Unit"  1  0.7  6  0  requires factions { england, }\r\n'
t = edb_p.read_bytes().decode("latin-1")
i = t.index('                recruit_pool "Spearmen"')
edb_p.write_bytes((t[:i] + ghost + t[i:]).encode("latin-1"))
rec = {"resolved_type": "Ghost Unit", "dest_root": str(tmp / "M"), "backup_root": str(tmp / "bk"),
       "options": {}}
check("an undo of anything else (a banner, a building) leaves them alone",
      transfer._drop_orphan_pools(rec) == 0 and "Ghost Unit" in edb_p.read_text("latin-1"))
rec["options"] = {"bring_animations": True}
check("a transfer's undo takes out the line naming its vanished unit",
      transfer._drop_orphan_pools(rec) == 1 and "Ghost Unit" not in edb_p.read_text("latin-1"))

crus = Path(real or "") / "mods" / "crusades"
if (crus / "packs").is_dir():
    print("\n3) undoing a transfer whose unit was pooled afterwards")
    from unittransfer.transfer import plan_transfer, apply_transfer, TransferOptions  # noqa: E402
    edit.apply_edit(plan_delete())            # the mod without it, as kirsi was
    plan = plan_transfer(Mod(crus), "Greek Firethrower", Mod(tmp / "M"),
                         TransferOptions(bring_animations=False))
    rec = apply_transfer(plan)
    # pooled by hand after the transfer, as a user does in the buildings and
    # mercenary editors
    for rel, line in (("export_descr_buildings.txt",
                       '                recruit_pool "Greek Firethrower"  1  0.7  6  0  requires factions { byzantium, }\r\n'),
                      (merc_rel, "\tunit Greek Firethrower\t\texp 0 cost 1280 replenish 0.02 - 0.06 max 2 initial 1\r\n")):
        p = data / rel
        t = p.read_bytes().decode("latin-1")
        anchor = '                recruit_pool "Spearmen"' if rel.endswith("buildings.txt") else "\tunit Spearmen,"
        i = t.index(anchor)
        p.write_bytes((t[:i] + line + t[i:]).encode("latin-1"))
    out = undo(rec["id"])
    check("the unit is gone and so are the two lines that pooled it",
          "Greek Firethrower" not in (data / "export_descr_buildings.txt").read_text("latin-1")
          and "Greek Firethrower" not in (data / merc_rel).read_text("latin-1"))
    check("  Spearmen's lines stay",
          'recruit_pool "Spearmen"' in (data / "export_descr_buildings.txt").read_text("latin-1")
          and "unit Spearmen," in (data / merc_rel).read_text("latin-1"))
    check("  and the record says how many", out.get("refs_dropped") == 2)
else:
    print("\n3) skipped: the base game's crusades campaign is not installed")

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
