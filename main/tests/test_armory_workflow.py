"""Saved-output discovery and safe data-relative folder choices; no game needed."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from unittransfer import armunit
from unittransfer.server import Handler


class ExportWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.model = SimpleNamespace(groups=[SimpleNamespace(sheets='main')], vertices=3, triangles=1)
        self.reader = patch('unittransfer.mesh.read_mesh', return_value=self.model)
        self.reader.start()
        self.addCleanup(self.reader.stop)

    def files(self, stem, attachment=False):
        for suffix in ['.mesh', '.texture', '_normal.texture'] + (['_attach.texture', '_attach_normal.texture'] if attachment else []):
            (self.folder / (stem + suffix)).write_bytes(b'fixture')

    def test_older_export_is_found_and_its_filename_is_restored(self):
        self.files('previous')
        result = armunit.existing_export(str(self.folder), 'new_default_name')
        self.assertTrue(result['found'])
        self.assertEqual(result['stem'], 'previous')
        self.assertEqual(result['vertices'], 3)

    def test_partial_export_does_not_unlock_installation(self):
        self.files('previous')
        (self.folder / 'previous_normal.texture').unlink()
        self.assertFalse(armunit.existing_export(str(self.folder), 'previous')['found'])

    def test_attachment_files_are_required_for_attachment_uvs(self):
        self.files('previous')
        self.model.groups[0].sheets = 'both'
        self.assertFalse(armunit.existing_export(str(self.folder), 'previous')['found'])
        self.files('previous', attachment=True)
        self.assertTrue(armunit.existing_export(str(self.folder), 'previous')['found'])

    def test_multiple_exports_are_not_chosen_arbitrarily(self):
        self.files('first'); self.files('second')
        result = armunit.existing_export(str(self.folder), 'unknown')
        self.assertFalse(result['found'])
        self.assertEqual(result['candidates'], ['first', 'second'])

    def test_route_checks_files_without_requiring_a_mod(self):
        self.files('previous')
        handler = SimpleNamespace(_json=lambda result: result, _err=lambda code, error: (code, error))
        result = Handler._armory_get(handler, '/api/armory/export_exists', {'folder':[str(self.folder)], 'stem':['previous']})
        self.assertTrue(result['found'])

    def test_folder_choices_are_relative_to_data_and_cannot_escape(self):
        data = self.folder / 'data'
        inside = data / 'unit_models' / 'guard'
        inside.mkdir(parents=True)
        self.assertEqual(armunit.data_folder(data, str(inside)), 'unit_models/guard')
        with self.assertRaises(armunit.InstallError):
            armunit.data_folder(data, str(self.folder / 'outside'))

    def test_folder_browser_starts_at_mod_data_and_returns_relative_path(self):
        data = self.folder / 'data'
        chosen = data / 'unit_models' / 'guard'
        chosen.mkdir(parents=True)
        handler = SimpleNamespace(path='/api/armory/install/folder',
            _read_body=lambda: {'mod': 'Example'},
            registry=SimpleNamespace(get=lambda name: SimpleNamespace(data=data)),
            _json=lambda result: result, _err=lambda code, error: (code, error))
        with patch('unittransfer.folder_dialog.browse_for_folder', return_value=str(chosen)) as picker:
            result = Handler.do_POST(handler)
        self.assertEqual(result['path'], 'unit_models/guard')
        self.assertEqual(picker.call_args.kwargs['initial_dir'], str(data))

    def test_modern_picker_sets_initial_folder_without_showing_a_real_dialog(self):
        import ctypes
        from unittransfer import folder_dialog as fd
        def create_dialog(_cls, _outer, _context, _iid, output):
            ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(1)
            return 0
        def create_item(_path, _bind, _iid, output):
            ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.c_void_p(2)
            return 0
        def call(_obj, index, _restype, *args):
            return fd._CANCELLED if index == 3 else 0
        with patch.object(fd._ole32, 'CoCreateInstance', side_effect=create_dialog), \
             patch.object(fd._shell32, 'SHCreateItemFromParsingName', side_effect=create_item) as item, \
             patch.object(fd, '_vcall', side_effect=call) as calls, patch.object(fd, '_Owner') as owner:
            owner.return_value.__enter__.return_value = 0
            self.assertIsNone(fd._pick_folder_modern('Choose folder', str(self.folder)))
        self.assertEqual(item.call_args.args[0], str(self.folder))
        self.assertTrue(any(row.args[1] == 12 for row in calls.call_args_list))


if __name__ == '__main__':
    unittest.main()
