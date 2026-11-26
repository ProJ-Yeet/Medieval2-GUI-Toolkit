"""The Armory scale controls reuse the existing loose and packed writers."""
import unittest
from unittest.mock import Mock
from unittransfer.server import Handler


class AnimationRouteTests(unittest.TestCase):
    def test_pack_scale_uses_existing_pack_handlers(self):
        handler = object.__new__(Handler)
        handler._anim_pack = Mock(return_value={"ok": True})
        body = dict(mod="fixture", target="pack", skeleton="human", slot=2,
                    edits={"scale": [2, 2, 2]}, name="walk_scaled")
        for action, packed in (("preview", "pack_preview"), ("save_plan", "pack_plan"), ("save_apply", "pack_apply")):
            self.assertEqual(handler._anim_edit(action, body), {"ok": True})
            handler._anim_pack.assert_called_with(packed, body)

    def test_a_unit_animates_from_its_soldier_line(self):
        # 2026-11-26: Falas Lords pulled from its armour_ug_models entry
        # (falas_lords, on a bow skeleton) moves as its soldier line does
        # (orc_key_host_upg0, a swordsman), the one entry the engine animates
        from types import SimpleNamespace as NS
        from unittransfer import animview
        mod = NS(edu=NS(units=[NS(type="Falas Lords", soldier_model="Orc_Key_Host_Upg0"),
                               NS(type="Other", soldier_model="")]))
        self.assertEqual(animview.soldier_of(mod, "falas lords"), "orc_key_host_upg0")
        self.assertIsNone(animview.soldier_of(mod, "Other"))
        self.assertIsNone(animview.soldier_of(mod, "Nobody"))
        self.assertIsNone(animview.soldier_of(mod, ""))


if __name__ == '__main__':
    unittest.main()
