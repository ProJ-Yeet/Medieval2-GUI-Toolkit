"""Focused checks for the full-mod unused-unit text scan.

    python -m tests.test_unusedunits
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittransfer import unusedunits


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "data"
        data.mkdir()
        (data / "export_descr_unit.txt").write_text("type lone\ntype voiced\ntype used\ntype git_only\ntype localized\n")
        (data / "export_descr_sounds_units_voice.txt").write_text("voiced\n")
        (data / "text").mkdir()
        (data / "text" / "export_units.txt").write_text("{localized} Localized name\n")
        (root / "script.lua").write_text("spawn_unit('used')\n")
        (root / ".git").mkdir()
        (root / ".git" / "note").write_text("git_only\n")
        (root / "asset.mesh").write_bytes(b"\0used\0")
        mod = SimpleNamespace(root=root, edu=SimpleNamespace(main_units=[
            SimpleNamespace(type="lone"), SimpleNamespace(type="voiced"),
            SimpleNamespace(type="used"), SimpleNamespace(type="git_only"),
            SimpleNamespace(type="localized")]))
        optional = {x["type"]: x for x in unusedunits.scan(mod)["units"]}
        strict = {x["type"]: x for x in unusedunits.scan(mod, False)["units"]}
        assert optional["lone"]["unused"]
        assert optional["voiced"]["unused"]
        assert not optional["used"]["unused"]
        assert optional["git_only"]["unused"]
        assert optional["localized"]["unused"]
        assert not strict["voiced"]["unused"]
        assert optional["used"]["files"] == ["data/export_descr_unit.txt", "script.lua"]
        print("[OK] unused-unit scan recognises scripts, optional sound registrations and binary files")


if __name__ == "__main__":
    main()
