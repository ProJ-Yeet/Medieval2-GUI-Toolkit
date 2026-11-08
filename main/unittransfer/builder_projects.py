"""Portable draft adapter. Data only, no installed-mod or project-store writes.

Upstream v1 shape: lupinemaverick, pinned revision in builder_contract.
See docs/BUILDER_PROJECTS.md for intentionally different export semantics.
"""
from __future__ import annotations
import copy
import json
from . import builder_contract as contract, builder_calculator as calculator
from . import sheet_interchange as interchange

SCHEMA = 'm2-builder-project'
PRESETS = 'm2-builder-presets'
UPSTREAM = 'combat-reforged-builder'


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise contract.ContractError('project_duplicate')
        result[key] = value
    return result


def _presets(value):
    if not isinstance(value, dict):
        raise contract.ContractError('project_presets')
    # Unknown families/properties are inert JSON and retained for interchange.
    for family, rows in value.items():
        if not isinstance(rows, dict):
            raise contract.ContractError('project_presets')
        if family in calculator._TABLES:
            for row in rows.values():
                if not isinstance(row, list if family == 'loadouts' else dict):
                    raise contract.ContractError('project_preset_row')
    return copy.deepcopy(value)


def read(text, current=None):
    if not isinstance(text, str) or len(text) > 1_000_000:
        raise contract.ContractError('project_size')
    try:
        raw = json.loads(text.lstrip('\ufeff'), object_pairs_hook=_object)
        contract._json(raw)
    except (ValueError, RecursionError) as error:
        raise contract.ContractError('project_json') from error
    if not isinstance(raw, dict) or raw.get('schema') not in (SCHEMA, PRESETS, UPSTREAM):
        raise contract.ContractError('project_schema')
    if type(raw.get('version')) is not int or raw['version'] != 1:
        raise contract.ContractError('project_version')
    if raw['schema'] == SCHEMA:
        if set(raw) != {'schema','version','design'}:
            raise contract.ContractError('project_keys')
        packet = contract.validate_design(raw['design'])
    elif raw['schema'] == PRESETS:
        if set(raw) != {'schema','version','profile','presets'}:
            raise contract.ContractError('project_keys')
        packet = contract.validate_design(current)
        if packet['profile'] != raw['profile']:
            raise contract.ContractError('project_profile')
        for family, rows in _presets(raw['presets']).items():
            packet['presets'].setdefault(family, {}).update(rows)
    else:
        fields = raw.get('fields')
        if not isinstance(fields, dict):
            raise contract.ContractError('project_fields')
        presets = _presets(raw.get('presets', {}))
        if 'weapon_categories' in raw:
            categories = _presets({'weapon_categories':raw['weapon_categories']})
            presets.setdefault('weapon_categories', {}).update(categories['weapon_categories'])
        # Form values are explicit, including zero/false and blank numeric
        # overrides. Blank selects mean inherit, not an unknown profile choice.
        inputs = {k:v for k,v in fields.items() if v != '' or k == 'sec_base_atk'}
        if inputs.get('quality') == 'Standard':
            inputs['quality'] = 'Average'
        packet = {'schema':contract.SCHEMA,'version':1,
                  'profile':{'id':'combat-reforged','revision':contract.SOURCE_REVISION},
                  'inputs':{},'presets':presets,
                  'overrides':{'inputs':inputs,'native':{}},
                  'metadata':{'upstream':raw}}
        # Our exported extension restores native pins/metadata without asking
        # upstream to interpret them. Fields remain authoritative on reimport.
        extension = raw.get('m2_toolkit')
        if extension is not None:
            stored = contract.validate_design(extension)
            if stored['profile'] != packet['profile']:
                raise contract.ContractError('project_profile')
            packet['overrides']['native'] = stored['overrides']['native']
            packet['metadata'] = dict(stored['metadata'], upstream=raw)
    packet = contract.validate_design(packet)
    _presets(packet['presets'])
    calculator.calculate(packet)  # Validate before caller replaces any draft.
    return packet


def json_export(packet, fmt):
    packet = contract.validate_design(packet)
    _presets(packet['presets'])
    calculator.calculate(packet)
    if fmt == 'project':
        raw = {'schema':SCHEMA,'version':1,'design':packet}
    elif fmt == 'presets':
        raw = {'schema':PRESETS,'version':1,'profile':packet['profile'],'presets':packet['presets']}
    elif fmt == 'upstream':
        if packet['profile']['id'] != 'combat-reforged':
            raise contract.ContractError('project_profile')
        raw = copy.deepcopy(packet['metadata'].get('upstream', {}))
        raw.update(schema=UPSTREAM, version=1, fields=contract.effective_inputs(packet),
                   presets=packet['presets'], weapon_categories=packet['presets'].get('weapon_categories', {}))
        # Cached upstream unit is never trusted; omit a stale calculated cache.
        raw.pop('unit', None)
        extension = copy.deepcopy(packet)
        extension['metadata'].pop('upstream', None)
        raw['m2_toolkit'] = extension
    else:
        raise contract.ContractError('project_format')
    return {'name':'builder_'+fmt+'.json','mime':'application/json',
            'text':json.dumps(raw, ensure_ascii=True, indent=2, allow_nan=False)+'\n'}


def csv_export(result, uid=''):
    headers = ['id', *result['native']]
    values = [uid or 'builder_preview', *result['native'].values()]
    table = {'cells':{interchange.column_name(c)+str(r):{'value':v}
                     for r, row in enumerate((headers, values), 1)
                     for c, v in enumerate(row)}}
    return {'name':'builder.csv','mime':'text/csv','text':interchange.write_csv(table)}
