"""Missing card coverage uses synthetic mods only."""
import shutil
from copy import copy
import struct
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from unittransfer import edit
from unittransfer.mod import Mod


class CardCoverageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / '.tmp' / ('cards_' + uuid.uuid4().hex)
        self.root.mkdir(mode=0o777, parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.modroot = self.root / 'mod'
        self.game = self.root / 'game'
        self.write('export_descr_unit.txt', 'type Spearmen\ndictionary spearmen\nownership england, france, spain\n')
        self.write('descr_sm_factions.txt', '\n'.join(
            f'faction {f}\nculture {c}\n' for f, c in
            [('england', 'north'), ('france', 'north'), ('spain', 'south'), ('denmark', 'north')]))
        self.write('export_descr_buildings.txt', '''building barracks
{
 levels wooden
 {
 wooden city
 {
  capability
  {
   recruit_pool "Spearmen" 1 0.5 2 0 requires factions { france, denmark, }
  }
 }
 }
}
''')
        self.write('ui/units/england/#spearmen.tga', 'card')
        self.write('ui/units/france/#spearmen.tga', 'base card', game=True)
        self.write('ui/unit_info/england/spearmen_info.tga', 'info')
        self.mod = Mod(self.modroot)
        self.unit = self.mod.edu.units[0]
        p = patch('unittransfer.gamepack.game_root_of', return_value=self.game)
        p.start()
        self.addCleanup(p.stop)

    def write(self, rel, text, game=False):
        p = (self.game if game else self.modroot) / 'data' / rel
        p.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def report(self):
        return edit.icon_coverage(self.mod, self.unit)

    def test_owners_recruiters_and_base_game(self):
        r = self.report()
        self.assertEqual([x['faction'] for x in r['card']], ['denmark', 'spain'])
        self.assertEqual([x['faction'] for x in r['info']], ['denmark', 'france', 'spain'])
        reasons = {x['faction']: x['reasons'] for x in r['info']}
        self.assertEqual(reasons['denmark'], ['recruitment'])
        self.assertEqual(reasons['france'], ['ownership', 'recruitment'])
        self.assertEqual(reasons['spain'], ['ownership'])
        self.assertTrue(all(x['fallback'] == '' for x in r['card']))

    def test_all_folder_is_not_a_fallback(self):
        self.write('ui/units/all/#spearmen.tga', 'shared', game=True)
        self.assertTrue(all(not r['fallback'] for r in self.report()['card']))

    def test_non_eop_mercenary_checks_only_shared_picture(self):
        self.unit.mercenary_unit = True
        r = self.report()
        self.assertEqual(len(r['card']), 1)
        self.assertEqual(r['card'][0]['faction'], 'mercs')
        self.assertEqual(r['card'][0]['severity'], 'warning')
        self.assertEqual(r['info'][0]['faction'], 'merc')
        self.write('ui/units/mercs/#spearmen.tga', 'merc')
        self.write('ui/unit_info/merc/spearmen_info.tga', 'info')
        self.assertEqual(self.report(), {'card': [], 'info': []})

    def eop(self, script=''):
        p = self.modroot / 'eopData/eopScripts/luaPluginScript.lua'
        p.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
        p.write_text(script, encoding='utf-8')
        self.mod.drop_caches()

    def test_eop_mercenary_real_fallback_is_note(self):
        self.eop('-- handleUnitCards(false) is only a comment')
        self.unit.mercenary_unit = True
        self.write('ui/units/mercs/#spearmen.tga', 'merc')
        self.write('ui/unit_info/merc/spearmen_info.tga', 'info')
        self.assertTrue(all(r['severity'] == 'note' for r in self.report()['info']))
        rows = self.report()['card']
        self.assertEqual([r['faction'] for r in rows], ['denmark', 'spain'])
        self.assertTrue(all(r['severity'] == 'note' for r in rows))
        self.assertTrue(all(r['fallback'] == 'ui/units/mercs/#spearmen.tga' for r in rows))

    def test_eop_explicit_false_uses_shared_only(self):
        self.eop('M2TWEOP.handleUnitCards ( false )')
        self.unit.mercenary_unit = True
        self.assertEqual([r['faction'] for r in self.report()['card']], ['mercs'])

    def test_pinned_picture_covers_all_factions(self):
        self.unit.card_pic_dir = 'custom'
        self.unit.info_pic_dir = 'custom_info'
        self.write('ui/units/custom/#spearmen.tga', 'custom')
        self.write('ui/unit_info/custom_info/spearmen_info.tga', 'custom')
        self.assertEqual(self.report(), {'card': [], 'info': []})

    def test_generic_picture_is_warning(self):
        self.assertTrue(all(r['severity'] == 'warning' and not r['fallback']
                            for rows in self.report().values() for r in rows))

    def test_edb_scanned_once_and_invalidated_after_write(self):
        from unittransfer import buildings
        original = buildings.clause_factions
        with patch.object(buildings, 'clause_factions', wraps=original) as scan:
            self.report()
            other = copy(self.unit)
            other.type = 'Other Unit'
            edit.icon_coverage(self.mod, other)
            self.report()
            self.assertEqual(scan.call_count, 1)
            edit._invalidate(self.mod)
            self.report()
            self.assertEqual(scan.call_count, 2)

    def test_missing_pinned_picture_checks_factions(self):
        self.unit.card_pic_dir = 'missing'
        self.assertEqual([r['faction'] for r in self.report()['card']], ['denmark', 'spain'])

    def test_folder_index_once_per_request(self):
        with patch.object(self.mod, '_dir_index', wraps=self.mod._dir_index) as index:
            self.report()
            paths = [call.args[0] for call in index.call_args_list]
            self.assertEqual(len(paths), len(set(paths)))

    def test_eop_default_and_text_examples_do_not_disable(self):
        for script in ['', '--[[ handleUnitCards(false) ]]',
                       'local example = "handleUnitCards(false)"',
                       'local example = [=[handleUnitCards(false)]=]']:
            with self.subTest(script=script):
                self.eop(script)
                self.assertTrue(self.mod.faction_unit_cards)
        self.eop('handleUnitCards(false)')
        self.assertFalse(self.mod.faction_unit_cards)
        self.eop('handleUnitCards(true)')
        self.assertTrue(self.mod.faction_unit_cards)

    def test_culture_and_all_ownership(self):
        self.unit.ownership = ['north']
        self.assertEqual([x['faction'] for x in self.report()['card']], ['denmark'])
        self.unit.ownership = ['all']
        self.assertEqual([x['faction'] for x in self.report()['card']], ['denmark', 'spain'])

    def test_no_missing(self):
        for f in ['england', 'france', 'spain', 'denmark']:
            self.write(f'ui/units/{f}/#spearmen.tga', 'card')
            self.write(f'ui/unit_info/{f}/spearmen_info.tga', 'info')
        self.assertEqual(self.report(), {'card': [], 'info': []})

    def test_base_pack_picture_without_extraction(self):
        key = b'data/ui/units/spain/#spearmen.tga\0'
        size = (16 + len(key) + 3) // 4 * 4
        record = struct.pack('<4I', 28 + size, 0, 3, 3) + key
        record += b'\0' * (size - len(record))
        packs = self.game / 'packs'
        packs.mkdir(mode=0o777, parents=True)
        (packs / 'data_0.pack').write_bytes(
            b'PACK' + struct.pack('<HHIIII', 0, 3, 1, size, 1, 0)
            + struct.pack('<I', 3) + record + b'ART')
        with patch('unittransfer.gamepack.extract', side_effect=AssertionError('must not extract')):
            self.assertEqual([x['faction'] for x in self.report()['card']], ['denmark'])

    def test_missing_edb_keeps_ownership_coverage(self):
        (self.mod.data / 'export_descr_buildings.txt').unlink()
        self.assertEqual([x['faction'] for x in self.report()['card']], ['spain'])


if __name__ == '__main__':
    unittest.main()
