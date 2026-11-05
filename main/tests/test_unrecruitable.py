"""Focused checks for the EDU unit recruit-pool audit.

    python -m tests.test_unrecruitable
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittransfer.mod import Mod
from unittransfer import unrecruitable


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "data"
        data.mkdir()
        (data / "export_descr_unit.txt").write_text(
            "type Spearmen\n\ntype Archers\n\ntype Mercenary Only\n\ntype Never Recruited\n")
        (data / "export_descr_buildings.txt").write_text("""building barracks
{
 levels town
 {
  town city
  {
   capability
   {
    recruit_pool "Spearmen"  1  0.5  2  0
   }
   faction_capability england
   {
    recruit_pool "Archers"  1  0.5  2  0
   }
  }
 }
}
""")
        mercs = data / "world" / "maps" / "campaign" / "test"
        mercs.mkdir(parents=True)
        (mercs / "descr_mercenaries.txt").write_text(
            "pool test\nregions Test_Province\nunit Mercenary Only exp 0 cost 100\n")
        report = unrecruitable.scan(Mod(root))
        assert [row["type"] for row in report["units"]] == ["Never Recruited"]
        assert [row["type"] for row in report["mercenary_units"]] == ["Mercenary Only"]
        assert report["unit_count"] == 4
        assert report["pools_scanned"] == 2
        assert report["mercenary_files_scanned"] == 1
        print("[OK] unrecruitable-unit scan includes faction pools and mercenaries")


if __name__ == "__main__":
    main()
