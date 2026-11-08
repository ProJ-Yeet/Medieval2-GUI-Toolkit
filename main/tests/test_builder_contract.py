"""Phase 102 contracts only. All projects and EDU rows are synthetic."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from unittransfer import edu, sheet_ops, unit_sheets as sheets


class BuilderContractTests(unittest.TestCase):
    def setUp(self):
        from unittransfer import builder_contract
        self.contract = builder_contract
        self.design = {
            'schema':'m2-unit-design', 'version':1,
            'profile':{'id':'combat-reforged', 'revision':builder_contract.SOURCE_REVISION},
            'inputs':{'category':'infantry', 'pri_twohand':False,
                      'hide_forest_override':False},
            'presets':{}, 'overrides':{'inputs':{}, 'native':{}},
            'metadata':{'unknown':{'keep':[0, False, None]}},
        }

    def test_version_profile_and_json_are_explicit(self):
        c = self.contract
        before = copy.deepcopy(self.design)
        self.assertEqual(c.validate_design(self.design), before)
        self.assertEqual(self.design, before)
        for field, value in [('version',2), ('version',True), ('schema','combat-reforged-builder'),
                             ('profile',None), ('profile',{'id':'SSR','revision':'1'}),
                             ('profile',{'id':'combat-reforged','revision':'latest'}),
                             ('inputs',[]), ('presets',[]), ('metadata',{'bad':float('nan')}),
                             ('metadata',{1:'key'}), ('unexpected','value')]:
            with self.subTest(field=field, value=value), self.assertRaises(c.ContractError):
                c.validate_design(dict(self.design, **{field:value}))
        native = dict(self.design, profile={'id':'native', 'revision':'1'})
        self.assertEqual(c.validate_design(native)['profile']['id'], 'native')

    def test_input_and_output_overrides_are_separate_and_persistent(self):
        c = self.contract
        self.design['overrides'] = {'inputs':{'pri_twohand':True}, 'native':{'attack':0}}
        before = copy.deepcopy(self.design)
        self.assertTrue(c.effective_inputs(self.design)['pri_twohand'])
        for value in (13, 19):
            result = c.output_values(self.design, {'attack':value, 'shield':0})
            self.assertEqual(result['native'], {'attack':0, 'shield':0})
        self.assertEqual(self.design, before)
        self.assertEqual(json.loads(json.dumps(self.design)), before)
        for overrides in ({}, {'inputs':{}, 'native':{'attack':None}},
                          {'inputs':{}, 'native':{'attack':True}},
                          {'inputs':{}, 'native':{'replenish':3}}):
            with self.subTest(overrides=overrides), self.assertRaises(c.ContractError):
                c.validate_design(dict(self.design, overrides=overrides))

    def test_custom_and_unknown_attributes_never_become_native(self):
        c = self.contract
        result = c.output_values(self.design, {
            'attributes':['hardy','stalwart','lock_morale','desert_raider','unknown_unit'],
            'pri_attributes':['ap','hook_drag','hook','rend_9','stagger','sp','unknown_weapon'],
            'sec_attributes':['long_pike','batter_7','AP'],
        })
        self.assertEqual(result['native'], {'attributes':['hardy'],
                         'pri_attributes':['ap'], 'sec_attributes':['long_pike']})
        self.assertEqual(result['metadata']['omitted']['pri_attributes'],
                         ['hook_drag','hook','rend_9','stagger','sp','unknown_weapon'])
        self.assertEqual(result['metadata']['omitted']['sec_attributes'], ['batter_7','AP'])
        self.assertEqual(self.design['metadata']['unknown']['keep'], [0, False, None])
        with self.assertRaises(c.ContractError):
            c.output_values(self.design, {'mount_speed':4})

    def test_shared_sheet_identity_classifications_staging_and_no_writes(self):
        c = self.contract
        text = ('type Fixture Guard\ncategory infantry\nclass heavy\n'
                'soldier fixture_model, 47, 0, 1\n'
                'stat_pri 13, 7, no, 0, 0, melee, simple, piercing, sword, 29, 1\n'
                'attributes hardy, fixture_legacy\n; fixture comment\n')
        mod = SimpleNamespace(edu=edu.parse_text(text))
        project = sheets.empty_project()
        project['units']['Fixture Guard'] = {'annotations':{'Tier':'T2','Unit Race':'Fixture'},
                                            'extra':{'source column':'keep'}}
        before = copy.deepcopy(project)
        with patch.object(Path, 'write_text', side_effect=AssertionError('disk write')):
            attached = c.attach_design(mod, project, 'Fixture Guard', self.design)
            self.assertEqual(attached['draft'], {})
            values = c.output_values(self.design, {'attack':0})['native']
            staged, changes = sheet_ops.stage_cells(mod, attached, [
                {'id':'Fixture Guard','column':key,'value':value} for key,value in values.items()])
            fields, removals = sheet_ops.field_changes(mod.edu.units[0], staged['draft']['Fixture Guard'])
        self.assertEqual(fields, {'stat_pri':'0, 7, no, 0, 0, melee, simple, piercing, sword, 29, 1'})
        self.assertEqual(removals, [])
        self.assertEqual(changes[0]['id'], 'Fixture Guard')
        self.assertEqual(attached['units']['Fixture Guard']['annotations'], before['units']['Fixture Guard']['annotations'])
        self.assertEqual(attached['units']['Fixture Guard']['extra'], {'source column':'keep'})
        self.assertEqual(sheets.validate_project(json.loads(json.dumps(staged))), staged)
        self.assertEqual(project, before)
        self.assertEqual(mod.edu.units[0].raw, text)
        for uid in ('fixture guard', 'Fixture Guard ', 'translated name'):
            with self.subTest(uid=uid), self.assertRaises(c.ContractError):
                c.attach_design(mod, project, uid, self.design)
        attached['units']['Fixture Guard']['builder_design']['metadata']['unknown']['keep'].append(5)
        self.assertEqual(self.design['metadata']['unknown']['keep'], [0, False, None])

    def test_native_output_types_and_shared_field_mapping(self):
        c = self.contract
        self.assertEqual(c.native_mapping(), {key:list(value) for key,value in sheet_ops.FIELDS.items()})
        for value in (None, True, -1, float('inf'), 'bad'):
            with self.subTest(value=value), self.assertRaises(c.ContractError):
                c.output_values(self.design, {'attack':value})
        self.assertEqual(c.output_values(self.design, {'attributes':[]})['native'], {'attributes':[]})
        self.assertEqual(c.output_values(self.design, {})['native'], {})

    def test_reviewed_samples_and_golden_packets(self):
        c = self.contract
        root = Path(__file__).parent / 'fixtures' / 'builder_contract.json'
        fixture = json.loads(root.read_text(encoding='utf-8'))
        self.assertEqual(fixture['source_revision'], c.SOURCE_REVISION)
        self.assertEqual({x['case'] for x in fixture['cases']},
                         {'infantry','missile_defending_secondary','cavalry_barding',
                          'twohand_offhand','grade_override','hiding_opt_out'})
        for case in fixture['cases']:
            with self.subTest(case=case['case']):
                design = c.validate_design(case['design'])
                self.assertEqual(c.output_values(design, case['calculated']), case['expected'])
        audit = json.loads((Path(__file__).parents[1] / 'docs/upstream/SSR_BUILDER_AUDIT.json').read_text())
        self.assertEqual(audit['source_revision'], c.SOURCE_REVISION)
        self.assertEqual(set(audit['features']), {'archetypes','subtypes','weapons','armor',
                         'offhands','mounts','grades','attributes','formulas','projects','exporters'})
        for feature in audit['features'].values():
            self.assertTrue(feature['sources'])
            self.assertTrue(feature['destination'])
            self.assertIn(feature['compatibility'], ('profile_only','shared','metadata_only','mixed'))
        self.assertTrue(audit['open_questions'])


if __name__ == '__main__':
    unittest.main()
