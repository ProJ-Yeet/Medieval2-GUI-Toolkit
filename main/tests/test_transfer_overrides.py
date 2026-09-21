"""Regression coverage for transfer dependency planning after EDU edits."""

from types import SimpleNamespace

from unittransfer.transfer import (TransferOptions, TransferPlan, _build_unit_block,
                                   _effective_projectiles)


def test_projectile_override_replaces_source_projectile_dependency():
    unit = SimpleNamespace(stat_pri=["10", "5", "initial_arrow"],
                           stat_sec=["0", "0", "no"])
    opts = TransferOptions(field_overrides={
        "stat_pri": "10, 5, edited_arrow, 100, missile, missile",
    })

    assert _effective_projectiles(unit, opts, has_base=False) == ["edited_arrow"]


def test_base_projectile_dependency_only_comes_from_overridden_stat():
    unit = SimpleNamespace(stat_pri=["10", "5", "initial_arrow"],
                           stat_sec=["0", "0", "no"])
    opts = TransferOptions(field_overrides={
        "stat_pri": "10, 5, edited_arrow, 100, missile, missile",
    })

    assert _effective_projectiles(unit, opts, has_base=True) == ["edited_arrow"]


def test_clearing_era_ownership_removes_the_era_lines():
    raw = (
        "type             test_unit\n"
        "dictionary       test_unit\n"
        "ownership        england\n"
        "era 1            england\n"
        "era 2            france\n"
    )
    unit = SimpleNamespace(raw=raw, dictionary="test_unit")
    plan = TransferPlan(unit_type="test_unit", dictionary="test_unit", source=None,
                        dest=None, options=TransferOptions(field_overrides={
                            "era 1": "", "era 2": "   ",
                        }))

    block = _build_unit_block(plan, unit)

    assert "era 1" not in block
    assert "era 2" not in block


def test_dependency_renames_are_preserved_after_field_overrides():
    raw = (
        "type             test_unit\n"
        "dictionary       test_unit\n"
        "mount            old_mount\n"
        "stat_pri         10, 5, old_arrow, 100, missile, missile\n"
    )
    unit = SimpleNamespace(raw=raw, dictionary="test_unit")
    plan = TransferPlan(
        unit_type="test_unit", dictionary="test_unit", source=None, dest=None,
        options=TransferOptions(field_overrides={
            "mount": "edited_mount",
            "stat_pri": "10, 5, edited_arrow, 100, missile, missile",
        }),
        mount_rename=("edited_mount", "edited_mount_source"),
        projectile_renames={"edited_arrow": "edited_arrow_source"},
    )

    block = _build_unit_block(plan, unit)

    assert "mount            edited_mount_source" in block
    assert "edited_arrow_source" in block
