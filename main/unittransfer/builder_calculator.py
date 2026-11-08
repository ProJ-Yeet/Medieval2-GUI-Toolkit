"""Pure Phase 103 calculator. No service registration, staging or mod writes.

Combat Reforged rules by lupinemaverick, based on MUG Unit Builder v1.5 /
MUG Unit Creation Guide, developed for King Siegfried. User reported permission.
Pinned literal tables and provenance: builder_rules.json and docs/BUILDER_RULES.md.
Error strings and explanation keys are internal codes for future localized UI.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re

from . import builder_contract as contract, vocab

_DATA = json.loads(Path(__file__).with_name('builder_rules.json').read_text(encoding='utf-8'))
assert _DATA['revision'] == contract.SOURCE_REVISION
_TABLES = _DATA['tables']
_ENGINE_DEFAULTS = _DATA['engine_profiles']['vanilla']
_ENGINE_CALLS = {'setWeaponBonusModifier':'weapon_upgrade_attack',
                 'setArmourUpgradeModifier':'armour_upgrade_armour'}
_SCRIPT = 'eopData/eopScripts/luaPluginScript.lua'
_CAPS = 'data/descr_caps_ex.txt'
_CAPS_KEYS = {'weapon_upgrade_points':'weapon_upgrade_attack',
              'armour_upgrade_points':'armour_upgrade_armour'}
_LUA_SKIP = re.compile(r'--\[(=*)\[[\s\S]*?(?:\]\1\]|\Z)|--[^\n]*|'
                       r'\[(=*)\[[\s\S]*?(?:\]\2\]|\Z)|'
                       r'"(?:\\.|[^"\\])*(?:"|\Z)|\'(?:\\.|[^\'\\])*(?:\'|\Z)')
_SUBTYPES = ('guards','hybrid','aggressive','reckless','fanatic','bloc','raider',
             'mounted','engineer','mercenary','garrison','command')


def js_round(value):
    """JavaScript Math.round tie direction, including negative halves."""
    return math.floor(value + 0.5)


def load_engine_rules(mod_root=None, *, profile='vanilla'):
    """Read mod-local M2EX integers or literal EOP settings. Never execute Lua.

    This is an observed script setting, not a claim that a branch ran in game.
    Multiple calls or nonliteral arguments are ambiguous, so retain defaults.
    A mod entry's m2ex flag selects M2EX; paths use the explicit profile.
    """
    if hasattr(mod_root, 'm2ex'):
        if mod_root.m2ex:
            profile = 'M2EX'
        mod_root = mod_root.root
    if profile not in ('vanilla', 'eop', 'M2EX'):
        raise contract.ContractError('engine_profile')
    result = {'profile':profile}

    def finish():
        result['notes'] = [{'id':'builder.upgrade_card_note', 'params':{
            'weapon':result['weapon_upgrade_attack']['value'],
            'armour':result['armour_upgrade_armour']['value']}}]
        if profile == 'M2EX':
            result['notes'].append({'id':'builder.m2ex_missile_unverified', 'params':{}})
        return result
    for key, entry in _DATA['engine_profiles'][profile].items():
        result[key] = copy.deepcopy(entry)
    if profile == 'vanilla' or mod_root is None:
        return finish()
    if profile == 'M2EX':
        # M2EX reads these keys from descr_caps_ex.txt.
        try:
            text = (Path(mod_root)/_CAPS).read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            return finish()
        for line, raw in enumerate(text.splitlines(), 1):
            match = re.fullmatch(r'\s*(weapon_upgrade_points|armour_upgrade_points)\s+'
                                 r'([+-]?[0-9]+)\s*', raw.split(';', 1)[0])
            if match:
                value = int(match[2])
                result[_CAPS_KEYS[match[1]]] = {
                    'value':max(0, value), 'source':_CAPS+':'+str(line),
                    'verified':True, 'status':'clamped_config' if value < 0 else 'literal_config'}
        return finish()
    try:
        text = (Path(mod_root)/_SCRIPT).read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError):
        return finish()
    # Preserve offsets/newlines for exact source locations. Quotes and comments
    # cannot masquerade as a function call. No expression evaluation is used.
    clean = _LUA_SKIP.sub(lambda m:re.sub(r'[^\n]', ' ', m.group()), text)
    for call, key in _ENGINE_CALLS.items():
        matches = list(re.finditer(r'(?<![\w.:])M2TWEOP\s*\.\s*'+call+r'\s*\(([^)]*)\)', clean))
        if not matches:
            continue
        arg = matches[0].group(1).strip()
        if len(matches) != 1 or not re.fullmatch(r'[+]?[0-9]+', arg):
            result[key]['status'] = 'ambiguous_script'
            continue
        value = int(arg)
        if value > 1000:
            result[key]['status'] = 'out_of_range_script'
            continue
        line = clean.count('\n', 0, matches[0].start()) + 1
        result[key] = {'value':value, 'source':_SCRIPT+':'+str(line),
                       'verified':True, 'status':'literal_script'}
    return finish()


def _number(value, key, *, minimum=None, integer=False):
    if type(value) not in (int, float, str) or value == '':
        raise contract.ContractError('input_number:'+key)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise contract.ContractError('input_number:'+key) from error
    if (not math.isfinite(number) or abs(number) > 1_000_000
            or (integer and not number.is_integer())
            or (minimum is not None and number < minimum)):
        raise contract.ContractError('input_range:'+key)
    return int(number) if integer else number


def calculate(design, *, engine_rules=None):
    """Return shared typed native columns, contribution explanations and metadata.

    Native pins run last through the 102 boundary. Engine upgrade previews stay
    metadata so staging a base EDU stat cannot apply an upgrade twice. Unknown
    input/preset metadata never becomes a stat or directive. No filesystem access
    occurs here; pass read-only engine rules explicitly when a mod is selected.
    """
    packet = contract.validate_design(design)
    inputs = contract.effective_inputs(packet)
    rules = copy.deepcopy(engine_rules if engine_rules is not None else load_engine_rules())
    contract._json(rules)
    if not isinstance(rules, dict) or rules.get('profile') not in ('vanilla','eop','M2EX'):
        raise contract.ContractError('engine_rules')
    for key in _ENGINE_DEFAULTS:
        entry = rules.get(key)
        if (not isinstance(entry, dict) or not isinstance(entry.get('source'), str)
                or type(entry.get('value')) is not int):
            raise contract.ContractError('engine_rules')
        _number(entry.get('value'), key, minimum=0, integer=True)
    explanations = {}
    metadata = {'engine_rules':rules}
    native = {}

    def record(key, terms, value, *, native_field=True):
        explanations[key] = {'terms':terms, 'result':value}
        if native_field:
            native[key] = value
        return value

    def num(key, default=0, *, minimum=None, integer=False):
        value = inputs.get(key, default)
        if value is None:
            raise contract.ContractError('input_number:'+key)
        if value == '':
            value = default
        return _number(value, key, minimum=minimum, integer=integer)

    def boolean(key, default=False):
        value = inputs.get(key, default)
        if type(value) is not bool:
            raise contract.ContractError('input_boolean:'+key)
        return value

    def choice(key, allowed, default):
        value = inputs.get(key, default)
        if not isinstance(value, str) or value not in allowed:
            raise contract.ContractError('input_choice:'+key)
        return value

    def table(family, key):
        if not isinstance(key, str):
            raise contract.ContractError('preset_id:'+family)
        custom = packet['presets'].get(family, {})
        if not isinstance(custom, dict):
            raise contract.ContractError('preset_family:'+family)
        original = _TABLES[family].get(key)
        patch = custom.get(key, {})
        if (original is None and key not in custom) or not isinstance(patch, dict):
            raise contract.ContractError('preset_id:'+family)
        return dict(copy.deepcopy(original or {}), **patch)

    def pn(preset, key, default=0, *, minimum=None, integer=False):
        return _number(preset.get(key, default), 'preset.'+key, minimum=minimum, integer=integer)

    def tags(value):
        if isinstance(value, str):
            return [x.strip() for x in value.split(',') if x.strip()]
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            return list(value)
        raise contract.ContractError('input_tags')

    def text(value, key):
        if not isinstance(value, str) or any(c in value for c in '\r\n;'):
            raise contract.ContractError('input_text:'+key)
        return value

    if packet['profile']['id'] == 'combat-reforged':
        flags = {key:boolean('trait_'+key) for key in _SUBTYPES}
        category = choice('category', ('infantry','cavalry','siege','ship','handler','non_combatant'), 'infantry')
        cls = choice('class', ('heavy','light','spear','spearmen','missile','skirmish'), 'heavy')
        mounted = category == 'cavalry'
        archetype = choice('unit_category', _TABLES['archetypes'], 'Martial Nobility')
        base = table('archetypes', archetype)
        quality = choice('quality', _TABLES['foot_quality'], 'Average')
        grade_id = choice('equipment_grade', _TABLES['grades'], 'common')
        if archetype == 'Royal Retinue':
            grade_id = 'artisan'
        grade = table('grades', grade_id)
        grade_stat = pn(grade, 'stat', integer=True)
        if flags['mounted'] and mounted:
            raise contract.ContractError('mounted_eligibility')
        if flags['engineer'] and category != 'siege':
            raise contract.ContractError('engineer_eligibility')
        if flags['garrison'] and inputs.get('project_profile') == 'SSR':
            raise contract.ContractError('garrison_eligibility')

        weapons = {}
        for slot in ('pri','sec'):
            preset_id = inputs.get(slot+'_preset', '')
            if not isinstance(preset_id, str):
                raise contract.ContractError('weapon_preset')
            preset = table(slot, preset_id) if preset_id else {}
            role = 'cav' if mounted else cls if cls in ('missile','skirmish') else 'inf'
            roles = preset.get('roles', [])
            if not isinstance(roles, list) or not all(isinstance(x,str) for x in roles):
                raise contract.ContractError('preset_roles')
            if preset_id and not (role in roles or 'any' in roles
                    or slot == 'pri' and role == 'skirmish' and 'missile' in roles
                    or slot == 'sec' and role in ('missile','skirmish') and 'inf' in roles):
                raise contract.ContractError('weapon_role_eligibility:'+slot)
            cat_id = inputs.get(slot+'_category', preset.get('weapon_category', ''))
            if not isinstance(cat_id, str):
                raise contract.ContractError('weapon_category')
            cat = table('weapon_categories', cat_id) if cat_id and cat_id not in ('bow','crossbow','firearm','thrown','none') else {}
            defaults = dict(cat, **preset)
            # A selected category supplies only category defaults. A selected
            # weapon preset retains its individual charge, delay and projectile.
            for field, attr, fallback in [('base_atk','atk',0),('base_charge','charge',0),
                                          ('delay','delay',0),('handling','handling',0),
                                          ('heat','heat',0),('range','range',0),('ammo','ammo',0)]:
                default = defaults.get(attr+'_mounted', defaults.get(attr, fallback)) if mounted else defaults.get(attr, fallback)
                if default is None:
                    default = fallback
                weapons.setdefault(slot, {})[field] = num(slot+'_'+field, default,
                    integer=field in ('base_atk','base_charge','handling'),
                    minimum=None if field in ('base_atk','handling','heat') else 0)
            w = weapons[slot]
            w['category'] = cat_id
            w['type'] = choice(slot+'_weapon_type', ('melee','missile','thrown','siege_missile'), preset.get('wtype','melee'))
            w['twohand'] = boolean(slot+'_twohand', defaults.get('twohand', False))
            w['attr'] = tags(inputs.get(slot+'_attr', defaults.get('attr','')))
            w['sound'] = text(inputs.get(slot+'_sound', preset.get('sound','sword')), slot+'_sound')
            w['missile'] = text(inputs.get(slot+'_missile', preset.get('missile','no')), slot+'_missile')
            w['name'] = text(inputs.get(slot+'_weapon', preset.get('name','')), slot+'_weapon')
            w['present'] = slot == 'pri' or (inputs.get('sec_base_atk', preset.get('atk')) not in (None, '')) or bool(cat_id and cat_id != 'none')
            if slot == 'sec' and inputs.get('sec_base_atk') == '':
                w['present'] = False
        pri, sec = weapons['pri'], weapons['sec']
        if flags['hybrid'] and pri['type'] != 'missile':
            raise contract.ContractError('hybrid_eligibility')
        ranged = pri['type'] != 'melee'
        qindex = list(_TABLES['foot_quality']).index(quality)
        melee_quality = quality
        if ranged and not flags['hybrid'] and quality != 'Inferior':
            melee_quality = ('Superior' if quality in ('Exceptional','Outstanding') else 'Average') if cls == 'skirmish' or pri['type'] == 'thrown' else ('Inferior' if quality == 'Average' else 'Average')
        melee = table('mounted_quality' if mounted else 'foot_quality', melee_quality)
        bow = pri['sound'] == 'bow' or pri['missile'] == 'arrow'
        thrown = pri['type'] == 'thrown'
        ranged_atk = -1 if quality == 'Inferior' else ([3,2,1,0,0] if thrown else [2,1,0,0,0] if bow else [0]*5)[qindex]
        ranged_range = -10 if quality == 'Inferior' else ([15,10,5,0,0] if thrown else [30,20,10,0,0])[qindex]
        culture = choice('bow_culture', ('','anatolian','mongolian','welsh'), '')
        style_id = choice('cav_style', ('lancer','charger','brawler'), 'lancer')
        style = dict(atk=0,charge=0,defense=0,heat=0,morale=0)
        if mounted:
            if ranged: style.update(heat=-2)
            elif style_id == 'lancer': style.update(atk=-1,charge=2,defense=0,heat=-1)
            elif style_id == 'brawler': style.update(atk=1,charge=-2,defense=1,heat=1,morale=2)
            else: style.update(morale=1)

        weight = choice('armour_weight', ('light','medium','heavy'), 'medium')
        armor_id = inputs.get('armour_base', inputs.get('armour_preset','unarmored'))
        armor = table('armour', armor_id)
        arrangement = _TABLES['loadouts'].get(inputs.get('armour_preset',''), [armor_id])
        if 'armour_base' not in inputs and 'armour_preset' in inputs:
            armor_id = arrangement[0]
            armor = table('armour', armor_id)
        armor_terms = {'base':pn(armor,'arm',minimum=0,integer=True)}
        armor_heat, armor_agi = pn(armor,'heat'), max(0,pn(armor,'agi'))
        sound = armor.get('sound','flesh')
        active_layers = []
        for i in range(1, {'light':1,'medium':2,'heavy':3}[weight]+1):
            layer_id = inputs.get('armour_layer'+str(i), arrangement[i] if i < len(arrangement) else 'none')
            layer = table('layers', layer_id)
            active_layers.append(layer_id)
            armor_terms['layer'+str(i)] = pn(layer,'arm',minimum=0,integer=True)
            armor_heat += pn(layer,'heat')
            armor_agi += max(0,pn(layer,'agi'))
            if layer_id in ('mail_haubergon','mail_voiders','coat_of_plates','reinforcing'): sound = 'metal'
            elif sound == 'flesh' and layer_id in ('gambeson','arming_doublet','leather'): sound = 'leather'
        worn = num('armour', sum(armor_terms.values()), minimum=0, integer=True)
        armor_terms['input_override'] = worn - sum(armor_terms.values())
        sound = text(inputs.get('armour_sound', sound), 'armour_sound')
        sound = {'padded':'leather','chain':'metal','plate':'metal'}.get(sound, sound)
        if sound not in ('flesh','leather','metal'):
            raise contract.ContractError('armour_sound')

        offhand_id = choice('offhand', (*_TABLES['offhands'], 'legacy'), 'empty')
        shield_id = choice('shield_type', _TABLES['shield_type'], 'none')
        shield_type = table('shield_type', shield_id)
        material = table('shield_mat', choice('shield_material', _TABLES['shield_mat'], 'wooden'))
        if mounted and offhand_id == 'legacy' and shield_id == 'pavise':
            raise contract.ContractError('pavise_eligibility')

        def offhand(w):
            if w['twohand']:
                return {'shield':0,'defense':0,'applicable':False}
            if offhand_id == 'legacy':
                skill = 0 if shield_id == 'none' else pn(shield_type,'def')+pn(material,'def')
                return {'shield':num('shield', pn(shield_type,'base')+pn(material,'bonus') if shield_id != 'none' else 0, minimum=0, integer=True),
                        'defense':min(1,max(0,skill)), 'applicable':True}
            p = table('offhands', offhand_id)
            return {'shield':num('offhand_shield',pn(p,'shield'),minimum=0,integer=True),
                    'defense':max(-1 if offhand_id == 'large' else 0,num('offhand_def',pn(p,'def'),integer=True)),
                    'applicable':True}

        defending = 'sec' if ranged and sec['present'] else 'pri'
        offhands = {slot:offhand(w) for slot,w in weapons.items()}
        record('category', {'selection':category}, category)
        record('class', {'selection':cls}, 'spearmen' if cls == 'spear' else cls)
        for slot, w in weapons.items():
            if not w['present']:
                continue
            terms = {'weapon':w['base_atk'], 'archetype_training':pn(base,'atk_tr',integer=True),
                     'quality':pn(melee,'atk',integer=True) if w['type'] == 'melee' else ranged_atk,
                     'subtype':int(flags['aggressive'])-int(flags['guards']) if w['type'] == 'melee' else 0,
                     'cavalry_style':style['atk'] if w['type'] == 'melee' else 0,
                     'kite':-1 if mounted and offhand_id == 'legacy' and shield_id == 'kite' and offhands[slot]['applicable'] and w['type'] == 'melee' else 0,
                     'skirmish':1 if w['type'] != 'melee' and cls == 'skirmish' else 0,
                     'culture':1 if w['type'] != 'melee' and bow and culture in ('mongolian','welsh') else 0,
                     'equipment_grade':grade_stat}
            attack = sum(terms.values())
            # The shared sheet boundary refuses negative attack. Report the
            # invalid design rather than silently clamping an upstream value.
            if attack < 0:
                raise contract.ContractError('negative_attack:'+slot)
            record('attack' if slot == 'pri' else 'sec_attack', terms, attack)
            lance = w['category'] == 'lance' or 'lance' in w['name'].lower()
            charge_terms = {'weapon':w['base_charge'], 'cavalry_style':style['charge'] if lance and w['type'] == 'melee' else 0}
            record('charge' if slot == 'pri' else 'sec_charge', charge_terms, sum(charge_terms.values()))
            delay = max(0,w['delay']+pn(melee,'delay')) if w['type'] == 'melee' else w['delay']
            record('attack_delay' if slot == 'pri' else 'sec_delay', {'base':w['delay'],'quality':pn(melee,'delay') if w['type']=='melee' else 0,'floor':0}, delay)
            record(slot+'_attributes', {'selection':w['attr']}, w['attr'])
        skill_terms = {'core':max(0,num('core_defense_skill',4,integer=True)),
                       'archetype_training':max(0,pn(base,'def_tr',integer=True)),
                       'soldier_quality':max(0,num('proficiency_def',pn(melee,'def'),integer=True)),
                       'armor':max(0,num('arm_agi',armor_agi,integer=True)),
                       'weapon_handling':max(0,weapons[defending]['handling']),
                       'offhand':offhands[defending]['defense'], 'aggressive':-int(flags['aggressive']),
                       'guards':2*int(flags['guards']), 'cavalry_style':style['defense']}
        record('defense', skill_terms, max(0,sum(skill_terms.values())))
        held = offhands[defending]['shield']
        record('shield', {'held':held,'grade':grade_stat if held > 0 else 0,'floor':0}, max(0,held+grade_stat) if held > 0 else 0)
        horse = table('horse', choice('horse_type', _TABLES['horse'], 'stallion'))
        breed = table('breed', choice('horse_origin', _TABLES['breed'], 'western_europe'))
        bard = table('barding', choice('horse_barding', _TABLES['barding'], 'none'))
        horse_only = mounted and inputs.get('horse_type','stallion') not in ('camel','elephant')
        bard_armor = pn(bard,'armour',minimum=0,integer=True) if horse_only else 0
        back = pn(shield_type,'armourBonus',integer=True) if offhand_id == 'legacy' and any(w['present'] and not w['twohand'] for w in weapons.values()) else 0
        graded_worn = max(0,worn+back+grade_stat) if worn > 0 else worn+back
        record('armor', dict(armor_terms, back_strapped=back, equipment_grade=graded_worn-worn-back, horse_barding=bard_armor), graded_worn+bard_armor)
        range_terms = {'base':pri['range'], 'quality':ranged_range if ranged else 0,
                       'culture':10 if ranged and bow and culture in ('anatolian','mongolian') else 0}
        range_value = sum(range_terms.values())
        if ranged and cls == 'skirmish':
            range_terms['skirmish_adjustment'] = math.floor(range_value*0.6)-range_value
        record('range', range_terms, sum(range_terms.values()))
        record('missile', {'selection':pri['missile']}, pri['missile'])
        record('ammo', {'base':pri['ammo'],'hybrid_divisor':2 if flags['hybrid'] else 1}, math.floor(pri['ammo']/2) if flags['hybrid'] else pri['ammo'])
        training = choice('training_override', ('','untrained','trained','highly_trained'), '') or ('highly_trained' if quality in ('Exceptional','Outstanding') else 'untrained' if quality == 'Inferior' else 'trained')
        if flags['hybrid']: training = 'highly_trained'
        discipline = choice('discipline_baseline', ('','low','normal','disciplined','impetuous'), '') or base['discipline']
        if flags['reckless']: discipline = 'impetuous'
        record('training', {'quality':quality,'hybrid':flags['hybrid'],'override':inputs.get('training_override','')}, training)
        record('discipline', {'baseline':base['discipline'],'reckless':flags['reckless'],'override':inputs.get('discipline_baseline','')}, discipline)
        morale_terms = {'baseline':num('morale_baseline',pn(base,'morale'),minimum=0,integer=True),
                        'quality':[3,2,1,0,-1][qindex], 'fanatic':int(flags['fanatic'])}
        preliminary_morale = max(0,min(30,sum(morale_terms.values())))
        morale_terms.update(first_clamp=preliminary_morale-sum(morale_terms.values()),
                            training=1 if training == 'highly_trained' else -1 if training == 'untrained' else 0,
                            discipline=1 if discipline == 'disciplined' else -1 if discipline == 'low' else 0,
                            guards=int(flags['guards'] and discipline == 'disciplined'),
                            role=int(mounted)+(-3 if cls == 'missile' else -1 if cls == 'skirmish' else 0), cavalry_style=style['morale'])
        record('morale', morale_terms, max(0,min(30,sum(morale_terms.values()))))
        size = num('soldier_count', base['size_cav'] if mounted else 100 if pri['category']=='pike' else 80 if cls in ('spear','spearmen') else base['size_inf'],minimum=1,integer=True)
        if archetype == 'Royal Retinue': size = num('soldier_count',base['size_cav'] if mounted else base['size_inf'],minimum=1,integer=True)
        record('unit_size', {'archetype':archetype,'override':inputs.get('soldier_count',''),'pike':pri['category']=='pike'}, size)
        heat_terms = {'armor':num('arm_heat',armor_heat),'primary':pri['heat'],
                      'secondary':sec['heat'] if sec['present'] else 0,
                      'mount':num('mount_heat',pn(horse,'heat')+pn(breed,'heat')+pn(bard,'heat')) if mounted else 0,
                      'archetype':pn(base,'heat'), 'quality':pn(melee,'heat'),
                      'cavalry_style':style['heat'], 'climate':num('climate_heat'),
                      'shield':pn(shield_type,'heat')+pn(material,'heat') if offhand_id == 'legacy' and shield_id != 'none' and any(w['present'] and not w['twohand'] for w in weapons.values()) else 0}
        record('heat', heat_terms, sum(heat_terms.values()), native_field=False)
        origin = choice('origin', _TABLES['terrain'], 'Western European')
        ground = breed.get('terrain_'+('med' if weight=='medium' else weight)) if mounted else table('terrain',origin).get(weight)
        if not isinstance(ground,list) or len(ground) != 4:
            raise contract.ContractError('terrain_shape')
        ground = [_number(x,'terrain',integer=True) for x in ground]
        pike = pri['category'] == 'pike' or 'long_pike' in pri['attr']
        specialty = choice('terrain_specialty', ('','scrub','sand','forest','snow'), '')
        attrs = tags(base.get('attrs',[])) + tags(inputs.get('extra_attrs',''))
        for tag in ('mercenary','command'):
            if flags[tag]: attrs.append('mercenary_unit' if tag == 'mercenary' else 'command')
        if boolean('can_sap'): attrs.append('can_sap')
        if mounted and archetype in ('Royal Retinue','Martial Nobility'): attrs.append('knight')
        hide = inputs.get('hide_forest_override')
        if hide is not None and type(hide) is not bool:
            raise contract.ContractError('hide_forest_override')
        if hide is True or hide is None and category == 'infantry': attrs.append('hide_forest')
        if hide is False: attrs = [x for x in attrs if x != 'hide_forest']
        for i,key in enumerate(('scrub','sand','forest','snow')):
            terms = {'origin_weight':ground[i], 'weapon':(-1 if key=='scrub' and pike else -2 if key=='forest' and pike else -1 if key=='forest' and pri['twohand'] else 0) if not mounted else 0,
                     'specialty':int(specialty == key), 'terrain_choice':2 if key in ('sand','forest') and (boolean('unit_tag_'+('desert_raider' if key=='sand' else 'forest_ambusher')) or ('desert_raider' if key=='sand' else 'forest_ambusher') in attrs) else 0}
            record(key, terms, sum(terms.values()))
        attrs = [x for x in attrs if x not in ('desert_raider','forest_ambusher')]
        record('attributes', {'selection':list(dict.fromkeys(attrs))}, list(dict.fromkeys(attrs)))
        if boolean('bible_formation_auto', True):
            if mounted:
                if thrown: formation = [2,4.4,3,4.4]
                elif not ranged and cls == 'heavy' and style_id != 'brawler': formation = [1.5,4.4,2.5,6]
                else: formation = [2,4.4,3,6]
            else:
                if pike: formation = [1.2,1.2,2.4,2.4]
                elif thrown: formation = [1.4,1.2,2.8,1.4]
                elif ranged and (pri['sound']=='crossbow' or pri['missile']=='bolt'): formation = [1.4]*4
                elif ranged: formation = [1.4,1.4,2.8,2] if cls=='skirmish' else [1.2,1.2,2.4,2.4]
                elif cls in ('spear','spearmen'): formation = [1.2,1.2,2.4,2.4] if quality=='Inferior' else [1,1,2,2]
                else: formation = [1.4,1.2,2.8,2.4] if quality=='Inferior' else [1.2,1,2.4,2]
                for i,value in enumerate(formation):
                    if cls == 'light': value += 0.2 if i < 2 else 0.4
                    if pri['twohand'] and not pike and i in (0,2): value += 0.2
                    formation[i] = js_round(value*100)/100
        else: formation = [num(k,v,minimum=0) for k,v in zip(('f_cs','f_cf','f_ls','f_lf'),(1.2,1,2.4,2))]
        for key,value in zip(('close_side','close_front','loose_side','loose_front'),formation): record(key, {'automatic':inputs.get('bible_formation_auto',True),'selection':value}, value)
        record('ranks', {'selection':num('f_ranks',4,minimum=1,integer=True)}, num('f_ranks',4,minimum=1,integer=True))
        formation_types = tags(inputs.get('f_types','square'))
        if not formation_types or any(x not in (*vocab.FORMATION_MAIN, *vocab.FORMATION_SPECIAL) for x in formation_types):
            raise contract.ContractError('formation_types')
        record('formation', {'selection':formation_types}, ', '.join(formation_types),
               native_field=len(formation_types) == 1)
        qcost = [3,2,1,0,-1][qindex]
        recruit = num('cost_construct',500+200*qcost+int(mounted)*300+worn*40,minimum=0,integer=True)
        upkeep = num('cost_upkeep',120+40*qcost+int(mounted)*80+worn*8,minimum=0,integer=True)
        custom = num('cost_custom',recruit+upkeep*2,minimum=0,integer=True)
        hybrid_cost = js_round(recruit*1.33) if flags['hybrid'] else recruit
        record('recruit_cost', {'pre_grade':recruit,'hybrid_rounded':hybrid_cost,'grade_multiplier':1+pn(grade,'recruit')}, js_round(hybrid_cost*(1+pn(grade,'recruit'))))
        record('upkeep', {'pre_grade':upkeep,'grade_multiplier':1+pn(grade,'upkeep')}, js_round(upkeep*(1+pn(grade,'upkeep'))))
        for key,source,default in [('custom_cost','cost_custom',custom),('recruit_turns','cost_turns',1),('weapon_upgrade_cost','cost_wpn',50),('armor_upgrade_cost','cost_arm',50)]: record(key, {'input':source,'default':default},num(source,default,minimum=0,integer=True))
        metadata.update(defending_slot=defending, melee_quality=melee_quality,
                        equipment_grade=grade_id, armor_loadout={'base':armor_id,'layers':active_layers},
                        secondary_defense={'defense':max(0,sum(skill_terms.values())-skill_terms['weapon_handling']-skill_terms['offhand']+max(0,sec['handling'])+offhands['sec']['defense']), 'shield':max(0,offhands['sec']['shield']+grade_stat) if offhands['sec']['shield']>0 else 0} if sec['present'] else {},
                        engine_shaped={'heat':explanations['heat']['result'],'armour_sound':sound,
                                       'lock_morale':flags['fanatic'],'formation_types':formation_types},
                        design_only={'subtypes':[x for x in ('bloc','raider','mounted','engineer','garrison') if flags[x]], 'unit_custom_attrs':tags(inputs.get('unit_custom_attrs','')), 'projectile_accuracy':[-0.2,-0.1,-0.05,0,0.1][qindex] if ranged else None})
    result = contract.output_values(packet, native)
    metadata.update(result['metadata'])
    result['metadata'] = metadata
    # Final pins and omitted proposals must be visible in the contribution trace.
    for key,value in result['native'].items():
        explanation = explanations.setdefault(key, {'terms':{},'result':value})
        if key in packet['overrides']['native']:
            explanation['before_pin'] = explanation['result']
            explanation['native_pin'] = value
        if key in metadata['omitted']:
            explanation['omitted'] = metadata['omitted'][key]
        explanation['result'] = value
    levels = {'attack':num('weapon_upgrade_level',0,minimum=0,integer=True),
              'armor':num('armour_upgrade_level',0,minimum=0,integer=True)}
    weapon_type = pri['type'] if packet['profile']['id'] == 'combat-reforged' else inputs.get('pri_weapon_type', 'melee')
    if rules['profile'] in ('vanilla', 'M2EX') and weapon_type != 'melee':
        levels['attack'] = 0
    metadata['upgrade_preview'] = {key:result['native'][key]+levels[key]*rules[rule]['value']
        for key,rule in [('attack','weapon_upgrade_attack'),('armor','armour_upgrade_armour')] if key in result['native']}
    result['explanations'] = explanations
    return result
