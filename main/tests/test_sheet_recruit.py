"""Phase 116: the recruitment sheet made editable and importable.

A row is one recruit_pool line of the EDB, by line number. Its four numbers are
staged in the sheet project, checked against the unit, building and level they
were staged on, previewed, and written only by Apply, through the EDB's atomic
writer with a backup and Log Undo. CSV/XLSX import and export use the sheets'
own mapping flow. Written before the implementation.
"""
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from unittransfer import config, unit_sheets as sheets
from unittransfer.mod import Mod
from unittransfer.transfer import undo
from tests import test_edb_balance as fixture

EDB, EDU = fixture.EDB, fixture.EDU
GUARD_HUT = '10'     # recruit_pool "Guard"  1   0.1  2  0  requires factions { england, } ; keep this


class RecruitSheetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / 'mods/fixture/data'
        self.data.mkdir(parents=True)
        (self.data / 'export_descr_unit.txt').write_bytes(EDU.encode('latin-1'))
        self.original = EDB.replace('keep this', 'café').replace('\n', '\r\n').encode('latin-1')
        self.edb = self.data / 'export_descr_buildings.txt'
        self.edb.write_bytes(self.original)
        self.mod = Mod(self.data.parent)
        for key, value in [('CONFIG_DIR', self.root / 'config'), ('BACKUP_DIR', self.root / 'config/backups'),
                           ('LOG_PATH', self.root / 'config/transfers.json'),
                           ('SETTINGS_PATH', self.root / 'config/settings.json')]:
            p = patch.object(config, key, value)
            p.start()
            self.addCleanup(p.stop)
        helper = fixture.BalanceTests()
        helper.setUp()
        sheets.save_project(self.mod, helper.p)

    def call(self, action, **body):
        current = sheets.service(self.mod, 'load', {'view': 'recruitment'})
        return sheets.service(self.mod, action, dict(view='recruitment', revision=current['revision'],
                                                     source_token=current['source_token'], **body))

    def rows(self):
        return {r['id']: r for r in sheets.service(self.mod, 'load', {'view': 'recruitment', 'limit': 100})['table']['rows']}

    def line(self, number):
        return self.edb.read_bytes().decode('latin-1').split('\r\n')[int(number) - 1]

    def test_only_the_four_numbers_are_editable(self):
        info = sheets.service(self.mod, 'load', {'view': 'recruitment'})['filter_info']
        for column in ('initial', 'per_turn', 'maximum', 'experience'):
            self.assertFalse(info[column]['readonly'], column)
        for column in ('unit', 'building', 'level', 'requires', 'line'):
            self.assertTrue(info[column]['readonly'], column)

    def test_a_cell_stages_in_the_project_and_the_edb_is_untouched(self):
        r = self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'per_turn', 'value': '0.25'}])
        self.assertEqual(r['changes'], [{'id': GUARD_HUT, 'column': 'per_turn', 'before': 0.1, 'after': 0.25}])
        self.assertEqual(self.edb.read_bytes(), self.original)
        row = self.rows()[GUARD_HUT]
        self.assertEqual(row['per_turn'], 0.25)
        self.assertTrue(row['changed'])
        draft = sheets.load_project(self.mod)['recruit_draft'][GUARD_HUT]
        self.assertEqual((draft['unit'], draft['building'], draft['level']), ('Guard', 'barracks', 'hut'))
        # A single cell edit from the grid is an operate set.
        self.call('operate', ids=[GUARD_HUT], column='maximum', operation='set', value='3')
        self.assertEqual(self.rows()[GUARD_HUT]['maximum'], 3)
        # Back to the EDB's own value, and the staged field goes away.
        self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'per_turn', 'value': 0.1},
                                  {'id': GUARD_HUT, 'column': 'maximum', 'value': 2}])
        self.assertNotIn('recruit_draft', sheets.load_project(self.mod))

    def test_bad_values_rows_and_columns_are_refused_whole(self):
        for cell in ({'id': GUARD_HUT, 'column': 'per_turn', 'value': -1},
                     {'id': GUARD_HUT, 'column': 'experience', 'value': 1.5},
                     {'id': GUARD_HUT, 'column': 'per_turn', 'value': 'x'},
                     {'id': GUARD_HUT, 'column': 'unit', 'value': 'Horse'},
                     {'id': '3', 'column': 'per_turn', 'value': 1}):
            with self.assertRaises(sheets.SheetError, msg=cell):
                self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'initial', 'value': 4}, cell])
        self.assertNotIn('recruit_draft', sheets.load_project(self.mod))
        with self.assertRaises(sheets.SheetError):
            self.call('operate', ids=[GUARD_HUT], column='per_turn', operation='add', value=1)

    def test_apply_writes_only_the_tokens_and_undo_restores_the_bytes(self):
        self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'per_turn', 'value': 0.25},
                                  {'id': GUARD_HUT, 'column': 'experience', 'value': 2},
                                  {'id': '23', 'column': 'maximum', 'value': 1.5}])
        preview = self.call('recruit_preview')
        self.assertEqual(len(preview['changes']), 3)
        self.assertEqual(self.edb.read_bytes(), self.original)
        done = self.call('recruit_apply', plan_token=preview['plan_token'])
        self.assertEqual(self.line(GUARD_HUT),
                         '    recruit_pool "Guard"  1   0.25  2  2  requires factions { england, } ; café')
        self.assertEqual(self.line(23), '    recruit_pool "Guard" 1 0.1 1.5 0')
        before, after = self.original.split(b'\r\n'), self.edb.read_bytes().split(b'\r\n')
        self.assertEqual([i + 1 for i, (a, b) in enumerate(zip(before, after)) if a != b], [10, 23])
        self.assertNotIn('recruit_draft', sheets.load_project(self.mod))
        undo(done['record']['id'])
        self.assertEqual(self.edb.read_bytes(), self.original)

    def test_a_stale_token_or_moved_line_never_writes(self):
        self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'per_turn', 'value': 0.25}])
        preview = self.call('recruit_preview')
        with self.assertRaises(sheets.SheetError):
            self.call('recruit_apply', plan_token='nope')
        # The EDB gains a line above, so line 14 is no longer that pool.
        self.edb.write_bytes(b'; a new first line\r\n' + self.original)
        self.mod = Mod(self.data.parent)
        loaded = sheets.service(self.mod, 'load', {'view': 'recruitment'})
        self.assertEqual(loaded['stale_drafts'], [GUARD_HUT])
        self.assertFalse(self.rows()['11'].get('changed'), 'the moved pool does not take the staged number')
        with self.assertRaises(sheets.SheetError):
            self.call('recruit_preview')
        with self.assertRaises(sheets.SheetError):
            self.call('recruit_apply', plan_token=preview['plan_token'])
        self.assertTrue(self.edb.read_bytes().endswith(self.original))

    def test_balancing_waits_for_staged_recruitment(self):
        self.call('paste', cells=[{'id': GUARD_HUT, 'column': 'per_turn', 'value': 0.25}])
        with self.assertRaises(sheets.SheetError):
            self.call('balance_preview', stages=['replenish'])

    def accept(self, **body):
        preview = self.call('interchange_preview', **body)
        return preview, self.call('interchange_import', preview_token=preview['preview_token'], **body)

    def test_csv_and_xlsx_export_edit_and_import_by_line(self):
        for fmt in ('csv', 'xlsx'):
            exported = self.call('interchange_export', format=fmt, formulas='values')
            info = self.call('interchange_inspect', format=fmt, text=exported['text'])
            headers = info['sheets'][0]['rows'][0]['values']
            self.assertEqual(headers[:4], ['id', 'unit', 'building', 'level'])
        exported = self.call('interchange_export', format='csv', formulas='values')
        table = list(csv.reader(io.StringIO(exported['text'])))
        head = table[0]
        for row in table[1:]:
            if row[0] == GUARD_HUT:
                row[head.index('per_turn')] = '0.3'
        text = '\n'.join(','.join(c if ',' not in c else '"' + c + '"' for c in row) for row in table) + '\n'
        mapping = {h: i for i, h in enumerate(head) if h in ('id', 'unit', 'building', 'level', 'initial',
                                                              'per_turn', 'maximum', 'experience')}
        body = dict(format='csv', text=text, plans=[dict(sheet='CSV', view='recruitment', header_row=1, mapping=mapping)])
        preview, done = self.accept(**body)
        self.assertEqual([(c['id'], c['column'], c['after']) for c in preview['changes']], [(GUARD_HUT, 'per_turn', 0.3)])
        self.assertEqual(sheets.load_project(self.mod)['recruit_draft'][GUARD_HUT]['fields'], {'per_turn': 0.3})
        self.assertEqual(self.edb.read_bytes(), self.original)

    def test_an_import_whose_line_holds_another_pool_is_refused(self):
        text = 'id,unit,per_turn\n14,Horse,0.3\n'
        body = dict(format='csv', text=text, plans=[dict(sheet='CSV', view='recruitment', header_row=1,
                                                         mapping={'id': 0, 'unit': 1, 'per_turn': 2})])
        with self.assertRaises(sheets.SheetError):
            self.call('interchange_preview', **body)
        body['plans'][0]['mapping'] = {'id': 0, 'requires': 1}
        with self.assertRaises(sheets.SheetError):
            self.call('interchange_preview', **body)
        self.assertNotIn('recruit_draft', sheets.load_project(self.mod))


if __name__ == '__main__':
    unittest.main()
