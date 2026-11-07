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


if __name__ == '__main__':
    unittest.main()
