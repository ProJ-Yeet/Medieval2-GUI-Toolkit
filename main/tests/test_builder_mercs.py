"""Phase 107: a mercenary design's unit put into chosen pools of descr_mercenaries.txt.

One save of the campaign's file through mercpools: a pool without a line for the
unit gets one, a pool with exactly one has its five numbers changed and its gates
kept, every other line stays byte for byte, a repeat changes nothing, and Undo
puts the file back. A design without the Mercenary subtype never reads the file.
Written before the implementation.
"""
import shutil
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from unittransfer import builder_contract as contract, config, edu, unit_sheets as sheets
from tests.test_builder_apply import TEXT, FakeDb
from tests.test_builder_calculator import design

MERCS = (";RATE_H a note the file keeps\n"
         "pool pool_a\n"
         "\tregions Region_A Region_B\n"
         "\tunit Guard,\t\texp 0 cost 400 replenish 0.1 - 0.2 max 2 initial 1 religions { catholic }\n"
         "\tunit Other,\t\texp 1 cost 300 replenish 0.1 - 0.3 max 3 initial 1\n"
         "\n"
         "pool pool_b\n"
         "\tregions Region_C\n"
         "\tunit Other,\t\texp 1 cost 300 replenish 0.1 - 0.3 max 3 initial 1 ; a comment\n"
         "\n"
         "pool pool_c\n"
         "\tregions Region_D\n"
         "\tunit Guard,\t\texp 0 cost 400 replenish 0.1 - 0.2 max 2 initial 1\n"
         "\tunit Guard,\t\texp 2 cost 600 replenish 0.1 - 0.2 max 2 initial 1 events { gunpowder_discovered }\n")


def merc(**inputs):
    base = dict(trait_mercenary=True, merc_pools='pool_a, pool_b', merc_experience=2, merc_cost=700,
                merc_replenish_min=0.15, merc_replenish_max=0.25, merc_maximum=4, merc_initial=2)
    base.update(inputs)
    return design(**base)


class MercPoolTests(unittest.TestCase):
    def setUp(self):
        from unittransfer import builder_designer
        self.service = builder_designer.service
        self.root = Path(__file__).resolve().parents[1] / '.tmp' / ('mercs_' + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.mod = SimpleNamespace(name='TestMod', root=self.root / 'mod', data=self.root / 'mod/data',
                                   edu=edu.parse_text(TEXT), m2ex=False, eop_dirs=[],
                                   modeldb=FakeDb({'guard', 'rider'}),
                                   projectile_def=lambda n: None, mount_def=lambda n: None)
        camp = self.mod.data / 'world/maps/campaign/imperial_campaign'
        camp.mkdir(parents=True)
        (camp / 'descr_strat.txt').write_text('campaign imperial_campaign\n')
        self.file = camp / 'descr_mercenaries.txt'
        self.file.write_bytes(MERCS.encode('latin-1'))
        cfg = self.root / 'config'
        for name, value in (('CONFIG_DIR', cfg), ('BACKUP_DIR', cfg / 'backups'),
                            ('LOG_PATH', cfg / 'transfers.json')):
            p = patch.object(config, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(sheets.config, 'CONFIG_DIR', cfg)
        p.start()
        self.addCleanup(p.stop)

    def call(self, action, **body):
        return self.service(self.mod, action, dict({'unit': 'Guard'}, **body))

    def lines(self):
        return self.file.read_bytes().decode('latin-1').splitlines()

    def test_a_design_without_the_mercenary_subtype_never_reads_the_file(self):
        with patch('unittransfer.mercpools.read', side_effect=AssertionError('read')):
            r = self.call('merc_plan', design=merc(trait_mercenary=False))
        self.assertFalse(r['ok'])
        self.assertIn('Mercenary subtype', r['errors'][0])
        self.assertEqual(self.file.read_bytes(), MERCS.encode('latin-1'))

    def test_load_lists_pools_and_where_the_unit_already_is(self):
        r = self.call('merc_load')
        self.assertEqual(r['campaign'], 'imperial_campaign')
        self.assertEqual(r['campaigns'], ['imperial_campaign'])
        self.assertEqual([(p['name'], p['regions'], p['has_unit']) for p in r['pools']],
                         [('pool_a', 2, 1), ('pool_b', 1, 0), ('pool_c', 1, 2)])

    def test_plan_edits_an_existing_line_and_adds_a_missing_one_without_writing(self):
        r = self.call('merc_plan', design=merc())
        self.assertTrue(r['ok'], r['errors'])
        self.assertEqual(self.file.read_bytes(), MERCS.encode('latin-1'))
        self.assertTrue(any(c.startswith('pool_a: Guard exp 0 -> 2') for c in r['changes']), r['changes'])
        self.assertTrue(any(c.startswith('pool_b: + Guard') for c in r['changes']), r['changes'])

    def test_apply_keeps_gates_and_every_other_line_and_undo_restores_bytes(self):
        r = self.call('merc_apply', design=merc())
        self.assertTrue(r['applied'])
        got = self.lines()
        self.assertIn('\tunit Guard,\t\texp 2 cost 700 replenish 0.15 - 0.25 max 4 initial 2 religions { catholic }', got)
        self.assertEqual(got[0], ';RATE_H a note the file keeps')
        self.assertIn('\tunit Other,\t\texp 1 cost 300 replenish 0.1 - 0.3 max 3 initial 1 ; a comment', got)
        b = got.index('pool pool_b')
        self.assertTrue(got[b + 3].startswith('\tunit Guard,'), got[b:b + 5])
        self.assertEqual([l for l in got if l.startswith('\tunit Guard')].count(
            '\tunit Guard,\t\texp 2 cost 700 replenish 0.15 - 0.25 max 4 initial 2'), 1)
        # A repeat finds nothing to change and writes nothing.
        again = self.call('merc_apply', design=merc())
        self.assertFalse(again['ok'])
        self.assertNotIn('applied', again)
        from unittransfer import transfer
        transfer.undo(r['id'])
        self.assertEqual(self.file.read_bytes(), MERCS.encode('latin-1'))

    def test_a_pool_with_two_lines_for_the_unit_is_refused_by_name(self):
        r = self.call('merc_plan', design=merc(merc_pools=['pool_c']))
        self.assertFalse(r['ok'])
        self.assertIn('pool_c', r['errors'][0])

    def test_bad_settings_are_refused_before_anything_is_planned(self):
        for inputs in ({'merc_pools': ''}, {'merc_initial': 5}, {'merc_cost': -1},
                       {'merc_replenish_min': 0.5}, {'merc_experience': 12}, {'merc_maximum': 1.5}):
            r = self.call('merc_plan', design=merc(**inputs))
            self.assertFalse(r['ok'], inputs)
        r = self.call('merc_plan', design=merc(merc_pools=['nowhere']))
        self.assertFalse(r['ok'])
        self.assertIn('nowhere', r['errors'][0])

    def test_armour_and_weapon_levels_stay_in_the_design(self):
        self.call('merc_apply', design=merc(merc_armour=2, merc_weapon_lvl=1))
        text = self.file.read_bytes().decode('latin-1')
        self.assertNotIn('armour', text)
        self.assertNotIn('weapon', text)

    def test_a_unit_the_mod_does_not_have_is_refused(self):
        with self.assertRaises(contract.ContractError):
            self.call('merc_plan', design=merc(), unit='Nobody')


if __name__ == '__main__':
    unittest.main()
