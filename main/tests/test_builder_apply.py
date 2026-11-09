"""Phase 106: a design staged onto an existing unit or a new unit from a donor.

Staging writes nothing. What it returns goes through the Unit Editor's own edit
planner (an existing unit) or the New unit transfer planner (a new unit), so the
backup, My Changes and Undo are theirs. Written before the implementation.
"""
import shutil
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from unittransfer import edu, unit_sheets as sheets, builder_contract as contract
from tests.test_builder_calculator import design

TEXT = """type Guard
dictionary guard
category infantry
class heavy
soldier guard, 60, 0, 1
stat_pri 5, 2, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_sec 0, 0, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_pri_armour 1, 2, 3, metal
stat_mental 5, normal, trained
stat_cost 1, 100, 50, 10, 10, 200, 1, 1
formation 1, 1, 2, 2, 4, square
stat_ground 0, 0, 0, 0
ownership england
; keep this comment

type Rider
dictionary rider
category cavalry
class heavy
soldier rider, 30, 0, 1
mount ghost horse
stat_pri 7, 6, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_sec 0, 0, no, 0, 0, melee, simple, piercing, sword, 25, 1
stat_pri_armour 3, 2, 3, metal
stat_mental 5, normal, trained
stat_cost 1, 300, 80, 10, 10, 200, 1, 1
formation 1, 1, 2, 2, 4, square
stat_ground 0, 0, 0, 0
ownership england
"""


class FakeDb:
    def __init__(self, names):
        self.names = set(names)

    def get(self, name):
        return object() if name.lower() in self.names else None


class StageTests(unittest.TestCase):
    def setUp(self):
        from unittransfer import builder_designer
        self.service = builder_designer.service
        self.root = Path(__file__).resolve().parents[1] / '.tmp' / ('apply_' + uuid.uuid4().hex)
        self.root.mkdir(mode=0o777, parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.mod = SimpleNamespace(root=self.root / 'mod', data=self.root / 'mod/data',
                                   edu=edu.parse_text(TEXT), m2ex=False, eop_dirs=[],
                                   modeldb=FakeDb({'guard', 'rider'}),
                                   projectile_def=lambda n: object() if n == 'arrow' else None,
                                   mount_def=lambda n: None)
        self.mod.data.mkdir(mode=0o777, parents=True)
        self.file = self.mod.data / 'export_descr_unit.txt'
        self.file.write_text(TEXT)
        p = patch.object(sheets.config, 'CONFIG_DIR', self.root / 'config')
        p.start()
        self.addCleanup(p.stop)

    def stage(self, **body):
        return self.service(self.mod, 'stage', body)

    def test_existing_unit_takes_only_the_chosen_fields(self):
        d = design(pri_preset='great_sword')
        native = self.service(self.mod, 'preview', {'design': d, 'unit': 'Guard'})['native']
        r = self.stage(design=d, unit='Guard', fields=['attack'])
        self.assertEqual(r['mode'], 'edit')
        self.assertEqual(r['target'], 'Guard')
        self.assertEqual(list(r['field_overrides']), ['stat_pri'])
        members = [x.strip() for x in r['field_overrides']['stat_pri'].split(',')]
        self.assertEqual(int(members[0]), native['attack'])
        # Every other member of the tuple is the unit's own, untouched.
        self.assertEqual(members[1:], ['2', 'no', '0', '0', 'melee', 'simple', 'piercing', 'sword', '25', '1'])
        self.assertEqual(r['remove_fields'], [])
        self.assertEqual(r['changes'], [{'column': 'attack', 'before': 5, 'after': native['attack']}])
        self.assertEqual(r['profile'], d['profile']['id'])
        self.assertEqual(r['missing'], [])
        self.assertEqual(self.file.read_text(), TEXT)
        self.assertFalse(sheets.project_path(self.mod).exists())

    def test_an_unchosen_or_unknown_field_is_refused(self):
        d = design()
        for fields in ([], ['no_such_column'], 'attack', [3]):
            with self.assertRaises(contract.ContractError):
                self.stage(design=d, unit='Guard', fields=fields)

    def test_target_is_exactly_one_of_unit_and_donor(self):
        d = design()
        for body in ({}, {'unit': 'Guard', 'donor': 'Guard'}, {'donor': 'Nobody'}, {'unit': 'Nobody'}):
            with self.assertRaises(contract.ContractError):
                self.stage(design=d, fields=['attack'], **body)

    def test_new_unit_is_staged_against_its_donor(self):
        d = design(pri_preset='horseman_sword', category='cavalry')
        r = self.stage(design=d, donor='Rider', fields=['attack', 'armor'])
        self.assertEqual(r['mode'], 'new')
        self.assertEqual(r['target'], 'Rider')
        self.assertEqual(sorted(r['field_overrides']), ['stat_pri', 'stat_pri_armour'])
        self.assertEqual(r['field_overrides']['stat_pri'].split(',')[1].strip(), '6')
        self.assertEqual(self.file.read_text(), TEXT)

    def test_missing_prerequisites_are_listed_before_writing(self):
        d = design(pri_preset='self_bow', **{'class': 'missile'})
        with patch('unittransfer.builder_calculator.calculate',
                   return_value={'native': {'missile': 'fire_arrow', 'category': 'cavalry'},
                                 'explanations': {}, 'metadata': {}}):
            r = self.stage(design=d, unit='Guard', fields=['missile', 'category'])
        kinds = {(m['kind'], m.get('name', '')) for m in r['missing']}
        self.assertIn(('projectile', 'fire_arrow'), kinds)
        self.assertIn(('mount', ''), kinds)            # a cavalry unit with no mount
        self.mod.modeldb = FakeDb(set())
        r = self.stage(design=design(), unit='Guard', fields=['attack'])
        self.assertIn({'kind': 'model', 'name': 'guard'}, r['missing'])
        r = self.stage(design=design(), donor='Rider', fields=['attack'])
        self.assertIn({'kind': 'mount', 'name': 'ghost horse'}, r['missing'])

    def test_a_new_unit_cannot_take_a_removal(self):
        with patch('unittransfer.builder_calculator.calculate',
                   return_value={'native': {'attributes': []}, 'explanations': {}, 'metadata': {}}):
            r = self.stage(design=design(), donor='Rider', fields=['attributes'])
            self.assertIn({'kind': 'removal', 'name': 'attributes'}, r['missing'])
            r = self.stage(design=design(), unit='Guard', fields=['attributes'])
            self.assertEqual(r['remove_fields'], ['attributes'])
            self.assertEqual(r['missing'], [])

    def test_the_profile_is_the_designs_own_choice(self):
        d = design()
        d['profile'] = {'id': 'guess', 'revision': '1'}
        with self.assertRaises(contract.ContractError):
            self.stage(design=d, unit='Guard', fields=['attack'])


class RealApplyTests(unittest.TestCase):
    """Through the normal planners on a throwaway copy of an installed mod."""

    @classmethod
    def setUpClass(cls):
        from tests import _realmod, _tmp
        from unittransfer import config
        source = None
        for root in sorted(_realmod.mods().glob('*')):
            if (root / 'data/export_descr_unit.txt').is_file() and \
               (root / 'data/unit_models/battle_models.modeldb').is_file():
                source = root
                break
        if source is None:
            raise unittest.SkipTest('no installed mod with an unpacked EDU and modeldb')
        cls.root = Path(_tmp.mkdtemp(prefix='ut_bdapply_'))
        data = cls.root / 'data'
        for rel in ('export_descr_unit.txt', 'text/export_units.txt',
                    'unit_models/battle_models.modeldb', 'descr_mount.txt',
                    'descr_projectile.txt'):
            if (source / 'data' / rel).exists():
                (data / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / 'data' / rel, data / rel)
        cfg = Path(_tmp.mkdtemp(prefix='ut_bdcfg_'))
        cls.saved = (config.CONFIG_DIR, config.BACKUP_DIR, config.SETTINGS_PATH, config.LOG_PATH)
        config.CONFIG_DIR = cfg
        config.BACKUP_DIR = cfg / 'backups'
        config.SETTINGS_PATH = cfg / 'settings.json'
        config.LOG_PATH = cfg / 'transfers.json'

    @classmethod
    def tearDownClass(cls):
        from unittransfer import config
        (config.CONFIG_DIR, config.BACKUP_DIR, config.SETTINGS_PATH, config.LOG_PATH) = cls.saved
        shutil.rmtree(cls.root, ignore_errors=True)

    def pick(self, mod):
        entries = mod.modeldb.by_name()
        for u in mod.edu.units:
            if (u.category or '').lower() == 'infantry' and not u.mount and \
               (u.soldier_model or '').lower() in entries and not u.is_eop and u.dictionary:
                return u.type
        self.skipTest('no plain infantry unit to design on')

    def test_existing_and_new_unit_apply_and_undo_byte_exact(self):
        from unittransfer import builder_designer, edit, config
        from unittransfer.mod import Mod
        from unittransfer.transfer import TransferOptions, plan_transfer, apply_transfer, undo
        files = [p for p in (self.root / 'data').rglob('*') if p.is_file()]
        before = {p: p.read_bytes() for p in files}
        mod = Mod(self.root)
        uid = self.pick(mod)
        d = design(pri_preset='great_sword')
        native = builder_designer.service(mod, 'preview', {'design': d, 'unit': uid})['native']
        old = mod.edu.by_type()[uid]
        others = [u.raw for u in mod.edu.units if u.type != uid]

        r = builder_designer.service(mod, 'stage', {'design': d, 'unit': uid, 'fields': ['attack', 'morale']})
        self.assertEqual(r['missing'], [])
        plan = edit.plan_edit(mod, edit.request_from_dict(
            {'unit': uid, 'field_overrides': r['field_overrides'], 'remove_fields': r['remove_fields']}))
        self.assertFalse(plan.errors)
        edit.apply_edit(plan)
        mod = Mod(self.root)
        new = mod.edu.by_type()[uid]
        self.assertEqual(int(new.stat_pri[0]), native['attack'])
        self.assertEqual(new.stat_pri[1:], old.stat_pri[1:])
        self.assertEqual(sheets.fields_of(new)['stat_pri_armour'], sheets.fields_of(old)['stat_pri_armour'])
        self.assertEqual([u.raw for u in mod.edu.units if u.type != uid], others)

        r = builder_designer.service(mod, 'stage', {'design': d, 'donor': uid, 'fields': ['armor']})
        self.assertEqual(r['mode'], 'new')
        opts = TransferOptions(on_conflict='rename', new_type=uid + ' designed',
                               new_dictionary=(old.dictionary or 'unit') + '_designed',
                               new_name=uid + ' designed', asset_conflict='use_existing',
                               icon_conflict='use_existing', engine_conflict='use_existing',
                               field_overrides=r['field_overrides'])
        plan = plan_transfer(mod, uid, mod, opts)
        self.assertFalse(plan.errors, plan.errors)
        apply_transfer(plan)
        mod = Mod(self.root)
        made = mod.edu.by_type()[uid + ' designed']
        self.assertEqual(int(sheets.fields_of(made)['stat_pri_armour'].split(',')[0]), native['armor'])

        for rec in reversed(config.load_log()):
            if rec.get('applied') and not rec.get('undone'):
                undo(rec['id'])
        for p, blob in before.items():
            self.assertEqual(p.read_bytes(), blob, p)


class BuilderUiTests(unittest.TestCase):
    """The designer's Node VM tests, so the suite runner covers them too."""

    def test_designer_ui_scripts(self):
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        main = Path(__file__).resolve().parents[1]
        for name in ('test_builder_apply_ui.js', 'test_builder_designer_ui.js', 'test_builder_projects_ui.js'):
            out = subprocess.run([node, str(main / 'tests' / name)], cwd=main, capture_output=True,
                                 text=True, timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertEqual(out.returncode, 0, name + '\n' + out.stdout + out.stderr)


if __name__ == '__main__':
    unittest.main()
