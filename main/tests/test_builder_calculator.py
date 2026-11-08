"""Phase 103 synthetic arithmetic and shared sheet boundary regressions."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from unittransfer import builder_contract as contract, edu, sheet_ops, unit_sheets


def design(**inputs):
    return {'schema':contract.SCHEMA, 'version':1,
            'profile':{'id':'combat-reforged', 'revision':contract.SOURCE_REVISION},
            'inputs':{'unit_category':'Martial Nobility', 'quality':'Average',
                      'category':'infantry', **inputs},
            'presets':{}, 'overrides':{'inputs':{}, 'native':{}}, 'metadata':{}}


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        from unittransfer import builder_calculator
        self.calc = builder_calculator

    def test_upstream_grade_goldens(self):
        # Read test_equipment_grade.cjs, never run its scripts. Hand transcribed.
        expected = {'artisan':[16,10,12,7,1150,220], 'high':[15,9,11,6,1075,210],
                    'common':[14,8,10,5,1000,200], 'munition':[13,7,9,4,800,170],
                    'poor':[13,7,9,4,1000,220]}
        for grade, golden in expected.items():
            with self.subTest(grade=grade):
                d = design(equipment_grade=grade, pri_base_atk=12, sec_base_atk=6,
                           armour=10, arm_agi=0, offhand='legacy', shield_type='heater',
                           shield=5, shield_material='reinforced',
                           cost_construct=1000, cost_upkeep=200)
                n = self.calc.calculate(d)['native']
                self.assertEqual([n[k] for k in ('attack','sec_attack','armor','shield',
                                                 'recruit_cost','upkeep')], golden)
                self.assertEqual(n['defense'], 6)

    def test_core_clamps_defending_slot_and_offhand(self):
        d = design(pri_weapon_type='missile', pri_base_atk=4, sec_category='sword_cut',
                   sec_base_atk=6, pri_handling=19, sec_handling=1,
                   arm_agi=0, offhand='buckler')
        r = self.calc.calculate(d)
        self.assertEqual(r['metadata']['defending_slot'], 'sec')
        self.assertEqual(r['native']['defense'], 9)
        d['inputs'].update(sec_twohand=True)
        self.assertEqual(self.calc.calculate(d)['native']['defense'], 7)
        self.assertEqual(self.calc.calculate(d)['native']['shield'], 0)
        d = design(pri_category='greatsword', pri_handling=-3, arm_agi=-3,
                   proficiency_def=-2, core_defense_skill=4, trait_aggressive=True)
        d['inputs']['unit_category'] = 'Emergency Levies'
        self.assertEqual(self.calc.calculate(d)['native']['defense'], 3)

    def test_barding_and_layers_count_once(self):
        d = design(armour_base='mail_med', armour_weight='medium',
                   armour_layer1='gambeson', armour_layer2='mail_voiders',
                   armour_layer3='reinforcing', horse_barding='plate',
                   equipment_grade='artisan')
        self.assertEqual(self.calc.calculate(d)['native']['armor'], 10)
        d['inputs']['category'] = 'cavalry'
        self.assertEqual(self.calc.calculate(d)['native']['armor'], 18)
        d['inputs']['armour'] = 0
        self.assertEqual(self.calc.calculate(d)['native']['armor'], 8)
        d['inputs']['horse_type'] = 'camel'
        self.assertEqual(self.calc.calculate(d)['native']['armor'], 0)

    def test_rounding_hybrid_and_override_order(self):
        d = design(pri_weapon_type='missile', pri_base_atk=2, pri_ammo=41,
                   trait_hybrid=True, cost_construct=50, cost_upkeep=5,
                   equipment_grade='high')
        r = self.calc.calculate(d)
        self.assertEqual(r['native']['recruit_cost'], 72)  # round(66.5)=67, then 72
        self.assertEqual(r['native']['ammo'], 20)
        d['overrides']['inputs']['cost_construct'] = 100
        d['overrides']['native'].update(recruit_cost=0, attack=0, attributes=[])
        n = self.calc.calculate(d)['native']
        self.assertEqual([n[k] for k in ('recruit_cost','attack','attributes')], [0,0,[]])
        self.assertEqual(self.calc.js_round(-1.5), -1)

    def test_quality_training_terrain_and_formation(self):
        d = design(pri_preset='self_bow', quality_dummy='dormant',
                   **{'class':'missile'},
                   terrain_specialty='sand', unit_tag_desert_raider=True,
                   hide_forest_override=False, armour_weight='light')
        d['inputs']['quality'] = 'Exceptional'
        r = self.calc.calculate(d)
        self.assertEqual(r['native']['training'], 'highly_trained')
        self.assertEqual(r['metadata']['melee_quality'], 'Average')
        self.assertEqual(r['native']['sand'], 2)
        self.assertNotIn('hide_forest', r['native']['attributes'])
        self.assertEqual(r['native']['close_side'], 1.2)
        d['inputs'].update(bible_formation_auto=False, f_cs=2.75, f_ranks=7)
        self.assertEqual(self.calc.calculate(d)['native']['close_side'], 2.75)
        self.assertEqual(self.calc.calculate(d)['native']['ranks'], 7)

    def test_native_profile_does_not_apply_balance(self):
        d = design(pri_base_atk=200)
        d['profile'] = {'id':'native', 'revision':'1'}
        d['overrides']['native'] = {'attack':3}
        self.assertEqual(self.calc.calculate(d)['native'], {'attack':3})

    def test_guards_skill_and_attack_goldens(self):
        # Emergency Levies have -1 Attack; ranged Average lowers melee quality.
        for weapon_type, attack, secondary in (('melee', 4, 4), ('missile', 5, 2)):
            with self.subTest(weapon_type=weapon_type):
                d = design(unit_category='Emergency Levies', core_defense_skill=4,
                           proficiency_def=0, arm_agi=0, pri_handling=0,
                           sec_handling=0, offhand='empty', pri_base_atk=6,
                           sec_base_atk=6, pri_weapon_type=weapon_type)
                before = self.calc.calculate(d)['native']
                self.assertEqual(before['defense'], 4)
                d['inputs']['trait_guards'] = True
                r = self.calc.calculate(d)
                self.assertEqual(r['native']['defense'], 6)
                self.assertEqual(r['native']['attack'], attack)
                self.assertEqual(r['native']['sec_attack'], secondary)
                self.assertEqual(r['native']['attack']-before['attack'],
                                 -int(weapon_type == 'melee'))
                self.assertEqual(r['native']['sec_attack']-before['sec_attack'], -1)
                self.assertEqual(r['explanations']['defense']['terms']['guards'], 2)

    def test_guards_morale_and_discipline_goldens(self):
        for discipline, reckless, expected_discipline, morale in (
                ('disciplined', False, 'disciplined', 12),
                ('normal', False, 'normal', 10),
                ('low', False, 'low', 9),
                ('impetuous', False, 'impetuous', 10),
                ('disciplined', True, 'impetuous', 10)):
            with self.subTest(discipline=discipline, reckless=reckless):
                d = design(pri_base_atk=6, morale_baseline=10,
                           discipline_baseline=discipline, trait_reckless=reckless)
                before = self.calc.calculate(d)['native']
                d['inputs']['trait_guards'] = True
                n = self.calc.calculate(d)['native']
                self.assertEqual(n['discipline'], expected_discipline)
                self.assertEqual(n['discipline'], before['discipline'])
                self.assertEqual(n['morale'], morale)
                self.assertEqual(n['morale']-before['morale'],
                                 int(expected_discipline == 'disciplined'))

    def test_invalid_selections(self):
        for inputs in ({'quality':'Standard'}, {'equipment_grade':'magic'},
                       {'armour_base':'missing'}, {'pri_preset':'missing'},
                       {'armour_base':[]}, {'armour_sound':{}},
                       {'offhand':'missing'}, {'armour':-1}, {'pri_base_atk':True},
                       {'pri_base_atk':1.5}, {'trait_hybrid':True},
                       {'trait_engineer':True},
                       {'trait_aggressive':'false'}, {'weapon_upgrade_level':-1}):
            with self.subTest(inputs=inputs), self.assertRaises(contract.ContractError):
                self.calc.calculate(design(**inputs))

    def test_preset_snapshot_inputs_then_final_pins(self):
        d = design(pri_preset='arming_sword')
        d['presets'] = {'pri':{'arming_sword':{'atk':17,'handling':3}}}
        self.assertEqual(self.calc.calculate(d)['native']['attack'], 19)
        d['overrides']['inputs']['pri_base_atk'] = 0
        self.assertEqual(self.calc.calculate(d)['native']['attack'], 2)
        d['overrides']['native']['attack'] = 0
        self.assertEqual(self.calc.calculate(d)['native']['attack'], 0)

    def test_repeat_nonmutation_no_writes_and_native_projection(self):
        d = design(pri_attr='ap, sp, hook_drag, spear_bonus_2, spear_bonus_4',
                   extra_attrs='hardy, stalwart, desert_raider',
                   unit_custom_attrs='fixture', weapon_upgrade_level=2)
        before = copy.deepcopy(d)
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')), \
                patch.object(Path, 'open', side_effect=AssertionError('unexpected path access')), \
                patch('os.open', side_effect=AssertionError('unexpected OS access')):
            r = self.calc.calculate(d)
            self.assertEqual(r, self.calc.calculate(json.loads(json.dumps(d))))
        self.assertEqual(d, before)
        self.assertEqual(r['native']['pri_attributes'], ['ap','spear_bonus_4'])
        self.assertIn('sp', r['metadata']['omitted']['pri_attributes'])
        self.assertNotIn('heat', r['native'])
        self.assertTrue(set(r['native']) <= set(sheet_ops.FIELDS))
        text = ('type Fixture\ncategory infantry\nclass heavy\nsoldier fixture, 60, 0, 1\n'
                'stat_pri 1, 1, no, 0, 0, melee, simple, piercing, sword, 40, 1\n'
                'stat_pri_attr no\n')
        unit = edu.parse_text(text).units[0]
        fields, _ = sheet_ops.field_changes(unit, {k:r['native'][k]
                                                   for k in ('attack','pri_attributes')})
        parsed = edu.parse_text('type Fixture\n' + '\n'.join(k+' '+v for k,v in fields.items()))
        self.assertEqual(sheet_ops.value_of(unit_sheets.fields_of(parsed.units[0]), sheet_ops.FIELDS['attack']),
                         r['native']['attack'])
        self.assertNotIn('sp', fields['stat_pri_attr'].split(', '))
        self.assertIn('attack', r['explanations'])
        self.assertEqual(r['explanations']['attack']['result'], r['native']['attack'])

    def test_engine_rules_literal_read_only_and_sources(self):
        root = Path(__file__).parent/'fixtures/builder_eop'
        vanilla = self.calc.load_engine_rules(root)
        self.assertEqual(vanilla['weapon_upgrade_attack']['value'], 3)
        self.assertEqual(vanilla['armour_upgrade_armour']['value'], 2)
        with patch.object(Path, 'write_text', side_effect=AssertionError('write')):
            rules = self.calc.load_engine_rules(root, profile='eop')
            self.assertEqual(rules['weapon_upgrade_attack']['value'], 1)
            self.assertEqual(rules['armour_upgrade_armour']['value'], 1)
            self.assertEqual(rules['notes'][0], {'id':'builder.upgrade_card_note',
                                                'params':{'weapon':1,'armour':1}})
            self.assertEqual(rules['weapon_upgrade_attack']['source'],
                             'eopData/eopScripts/luaPluginScript.lua:4')
            r = self.calc.calculate(design(weapon_upgrade_level=2, armour_upgrade_level=3),
                                    engine_rules=rules)
            self.assertEqual(r['metadata']['upgrade_preview']['attack'], r['native']['attack']+2)
            self.assertEqual(r['metadata']['upgrade_preview']['armor'], r['native']['armor']+3)
        with patch.object(Path, 'read_text', return_value='M2TWEOP.setWeaponBonusModifier(1 + 2)\n'
                          'M2TWEOP.setArmourUpgradeModifier(value)\n'):
            fallback = self.calc.load_engine_rules(root, profile='eop')
            self.assertEqual(fallback['weapon_upgrade_attack']['value'], 3)
            self.assertEqual(fallback['armour_upgrade_armour']['value'], 2)
        m2ex = self.calc.load_engine_rules(profile='M2EX')
        self.assertTrue(m2ex['weapon_upgrade_attack']['verified'])
        self.assertEqual(m2ex['weapon_upgrade_attack']['value'], 3)

    def test_m2ex_caps_fixtures_and_independent_sources(self):
        root = Path(__file__).parent/'fixtures/builder_m2ex'
        for name, weapon, armour, weapon_line, armour_line in (
                ('both', 5, 4, 2, 3), ('one', 7, 2, 1, None),
                ('none', 3, 2, None, None), ('negative', 0, 0, 1, 2)):
            with self.subTest(name=name), \
                    patch.object(Path, 'write_text', side_effect=AssertionError('write')):
                rules = self.calc.load_engine_rules(root/name, profile='M2EX')
                for key, value, line in (
                        ('weapon_upgrade_attack', weapon, weapon_line),
                        ('armour_upgrade_armour', armour, armour_line)):
                    entry = rules[key]
                    self.assertEqual(entry['value'], value)
                    self.assertTrue(entry['verified'])
                    self.assertEqual(entry['source'], 'data/descr_caps_ex.txt:'+str(line)
                                     if line else 'engine_default')
                    if name == 'negative':
                        self.assertEqual(entry['status'], 'clamped_config')
                self.assertEqual(rules['notes'][1]['id'], 'builder.m2ex_missile_unverified')
        missing = self.calc.load_engine_rules(root/'missing', profile='M2EX')
        self.assertEqual(missing['weapon_upgrade_attack']['value'], 3)
        self.assertEqual(missing['armour_upgrade_armour']['value'], 2)
        self.assertEqual(missing['weapon_upgrade_attack']['source'], 'engine_default')

    def test_m2ex_mod_flag_selects_caps_without_eop_or_parent_fallback(self):
        root = Path(__file__).parent/'fixtures/builder_m2ex/both'
        mod = SimpleNamespace(root=root, m2ex=True)
        rules = self.calc.load_engine_rules(mod)
        self.assertEqual(rules['profile'], 'M2EX')
        self.assertEqual(rules['weapon_upgrade_attack']['value'], 5)
        mod.m2ex = False
        vanilla = self.calc.load_engine_rules(mod)
        self.assertEqual(vanilla['profile'], 'vanilla')
        self.assertEqual(vanilla['weapon_upgrade_attack']['value'], 3)
        self.assertEqual(self.calc.load_engine_rules(root/'data', profile='M2EX')
                         ['weapon_upgrade_attack']['value'], 3)

    def test_vanilla_and_m2ex_weapon_upgrades_are_melee_only(self):
        root = Path(__file__).parent/'fixtures/builder_m2ex/both'
        for profile, bonus in (('vanilla', 3), ('M2EX', 5), ('eop', 3)):
            rules = self.calc.load_engine_rules(root, profile=profile)
            for weapon_type in ('melee', 'missile', 'thrown', 'siege_missile'):
                with self.subTest(profile=profile, weapon_type=weapon_type):
                    d = design(pri_weapon_type=weapon_type, weapon_upgrade_level=2,
                               armour_upgrade_level=3)
                    r = self.calc.calculate(d, engine_rules=rules)
                    applied = bonus if weapon_type == 'melee' or profile == 'eop' else 0
                    self.assertEqual(r['metadata']['upgrade_preview']['attack'],
                                     r['native']['attack']+2*applied)
                    self.assertEqual(r['metadata']['upgrade_preview']['armor'],
                                     r['native']['armor']+3*rules['armour_upgrade_armour']['value'])
        d = design(pri_preset='self_bow', weapon_upgrade_level=2, **{'class':'missile'})
        r = self.calc.calculate(d)
        self.assertEqual(r['metadata']['upgrade_preview']['attack'], r['native']['attack'])

    def test_secondary_none_and_ranged_category(self):
        r = self.calc.calculate(design(pri_category='bow', pri_preset='self_bow',
                                       **{'class':'missile'},
                                       sec_category='none', sec_preset='none'))
        self.assertNotIn('sec_attack', r['native'])
        self.assertEqual(r['metadata']['defending_slot'], 'pri')

    def test_heat_terrain_and_formation_contributions(self):
        d = design(category='cavalry', pri_category='lance', pri_base_atk=3,
                   horse_origin='iberian', horse_barding='plate', armour=10,
                   arm_heat=3, climate_heat=-2, quality='Superior')
        r = self.calc.calculate(d)
        self.assertEqual(r['native']['attack'], 7)  # 3 + training2 + quality3 - style1
        self.assertEqual(r['native']['sand'], -2)
        self.assertEqual(r['native']['close_side'], 1.5)
        self.assertEqual(r['explanations']['heat']['result'], 3)
        self.assertEqual(sum(r['explanations']['armor']['terms'].values()), r['native']['armor'])

    def test_ambiguous_eop_calls_and_long_strings_use_defaults(self):
        lua = ('local s = [=[M2TWEOP.setWeaponBonusModifier(99)]=]\n'
               'M2TWEOP.setWeaponBonusModifier(1)\n'
               'M2TWEOP.setWeaponBonusModifier(2)\n'
               'M2TWEOP.setArmourUpgradeModifier(-1)\n')
        with patch.object(Path, 'read_text', return_value=lua):
            r = self.calc.load_engine_rules('fixture', profile='eop')
        self.assertEqual(r['weapon_upgrade_attack']['value'], 3)
        self.assertEqual(r['armour_upgrade_armour']['value'], 2)
        self.assertEqual(r['weapon_upgrade_attack']['status'], 'ambiguous_script')

    def test_quality_goldens_from_upstream_audit(self):
        # Final r2 skill values, not older negative quality/handling baselines.
        for mounted in (False, True):
            for i, quality in enumerate(('Exceptional','Outstanding','Superior','Average','Inferior')):
                with self.subTest(mounted=mounted, quality=quality):
                    d = design(unit_category='Urban Militia', quality=quality,
                               category='cavalry' if mounted else 'infantry',
                               cav_style='charger', pri_base_atk=10, pri_base_charge=4,
                               pri_delay=80, pri_handling=0, sec_base_atk=6,
                               sec_delay=60, sec_handling=1, arm_agi=0, arm_heat=0,
                               mount_heat=0, armour=4)
                    r = self.calc.calculate(d)
                    self.assertEqual(r['native']['attack'], ([17,15,13,11,7] if mounted else [13,12,11,10,8])[i])
                    self.assertEqual(r['native']['sec_attack'], r['native']['attack']-4)
                    self.assertEqual(r['native']['defense'], [6,5,5,4,4][i])
                    self.assertEqual(r['native']['attack_delay'], [50,60,70,80,100][i])
                    self.assertEqual(r['explanations']['heat']['result'], [-3,-2,-1,0,1][i])
                    self.assertEqual(r['native']['charge'], 4)

    def test_ranged_hybrid_and_culture_goldens(self):
        d = design(unit_category='Urban Militia', quality='Exceptional',
                   **{'class':'missile'}, pri_weapon_type='missile', pri_base_atk=10,
                   pri_delay=80, pri_sound='bow', pri_missile='arrow', pri_range=100,
                   pri_ammo=40, sec_base_atk=6, sec_handling=1, sec_delay=60, arm_agi=0)
        keys = ('attack','range','sec_attack','sec_delay','defense')
        self.assertEqual([self.calc.calculate(d)['native'][k] for k in keys], [12,130,6,60,5])
        d['inputs']['trait_hybrid'] = True
        self.assertEqual([self.calc.calculate(d)['native'][k] for k in keys], [12,130,9,30,7])
        d['inputs']['trait_hybrid'] = False
        for culture, attack, distance in [('mongolian',13,140),('anatolian',12,140),('welsh',13,130)]:
            d['inputs']['bow_culture'] = culture
            r = self.calc.calculate(d)
            self.assertEqual([r['native'][k] for k in ('attack','range')], [attack,distance])

    def test_safe_fields_and_optouts_survive_all_final_pins(self):
        d = design(extra_attrs='hide_forest, hardy', hide_forest_override=False)
        d['overrides']['native'].update(pri_attributes=['sp','fire','spear_bonus_2','ap'])
        r = self.calc.calculate(d)
        self.assertEqual(r['native']['pri_attributes'], ['fire','ap'])
        self.assertNotIn('hide_forest', r['native']['attributes'])
        for level, weapon, armor in [(1,3,2),(2,6,4)]:
            d['inputs'].update(weapon_upgrade_level=level, armour_upgrade_level=level)
            r = self.calc.calculate(d)
            self.assertEqual(r['metadata']['upgrade_preview'],
                             {'attack':r['native']['attack']+weapon,'armor':r['native']['armor']+armor})

    def test_role_eligibility_and_compound_formation(self):
        for inputs in ({'category':'cavalry','pri_preset':'great_sword'},
                       {'pri_preset':'mounted_heavy_recurve_bow'},
                       {'category':'cavalry','offhand':'legacy','shield_type':'pavise'}):
            with self.subTest(inputs=inputs), self.assertRaises(contract.ContractError):
                self.calc.calculate(design(**inputs))
        r = self.calc.calculate(design(pri_category='pike', f_types='square, phalanx'))
        self.assertNotIn('formation', r['native'])
        self.assertEqual(r['metadata']['engine_shaped']['formation_types'], ['square','phalanx'])
        r = self.calc.calculate(design(f_types='square, wedge'))
        self.assertEqual(r['metadata']['engine_shaped']['formation_types'], ['square','wedge'])

    def test_explanations_and_selected_snapshot_validation(self):
        d = design(pri_preset='arming_sword', sec_preset='mace', offhand='medium',
                   armour_preset='full_plate', equipment_grade='high')
        r = self.calc.calculate(d)
        self.assertEqual(set(r['native'])-set(r['explanations']), set())
        for key in ('attack','armor','defense','shield','range','heat'):
            self.assertEqual(sum(r['explanations'][key]['terms'].values()),
                             r['explanations'][key]['result'])
        bad = copy.deepcopy(d)
        bad['presets'] = {'pri':{'arming_sword':{'atk':True}}}
        with self.assertRaises(contract.ContractError): self.calc.calculate(bad)
        bad = copy.deepcopy(d)
        bad['inputs']['pri_handling'] = 0.5
        with self.assertRaises(contract.ContractError): self.calc.calculate(bad)
        for family, identity, fields in [
                ('pri','arming_sword',{'name':{}}),
                ('breed','western_europe',{'terrain_med':[1,2]}),
                ('archetypes','Martial Nobility',{'attrs':[{}]})]:
            bad = copy.deepcopy(d)
            bad['presets'] = {family:{identity:fields}}
            if family == 'breed':
                bad['inputs'].update(category='cavalry', sec_preset='none')
            with self.subTest(family=family), self.assertRaises(contract.ContractError):
                self.calc.calculate(bad)

    def test_royal_grade_twohand_suppression_and_no_created_equipment(self):
        d = design(pri_category='greatsword', equipment_grade='poor', offhand='large')
        d['inputs']['unit_category'] = 'Royal Retinue'
        r = self.calc.calculate(d)
        self.assertEqual(r['native']['attack'], 16)
        self.assertEqual(r['native']['shield'], 0)
        self.assertEqual(r['metadata']['equipment_grade'], 'artisan')
        self.assertEqual(self.calc.calculate(design(armour=0, equipment_grade='artisan',
                                                  offhand='empty'))['native']['armor'], 0)


if __name__ == '__main__':
    unittest.main()
