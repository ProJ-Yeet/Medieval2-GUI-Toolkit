"""Phase 102 design contract, with no service registration, calculator or writer.

Source audit: docs/UNIT_BUILDER_CONTRACT.md. Upstream by lupinemaverick,
derived from MUG Unit Builder v1.5 / MUG Unit Creation Guide, with Combat
Reforged work for King Siegfried. User reported author permission to reuse.
No upstream code or balance tables are copied here. ContractError codes are
internal; a future UI must localize them before presenting them to users.
"""
from __future__ import annotations
import copy
import json
import math

from . import sheet_ops, unit_sheets as sheets, vocab

SCHEMA = 'm2-unit-design'
VERSION = 1
SOURCE_REVISION = 'd4ed9368d0db3da2000bc895e96f52a83b93cb67'
PROFILES = {'native':'1', 'combat-reforged':SOURCE_REVISION}
_KEYS = {'schema','version','profile','inputs','presets','overrides','metadata'}
# The game accepts fire, but refuses sp and spear_bonus_2. Existing-source
# preservation and the editor's broader suggestions stay outside this boundary.
_WEAPON_ATTR = [x for x in vocab.WEAPON_ATTR if x not in ('sp','spear_bonus_2')] + ['fire']
_LIST_VOCAB = {'attributes':(*vocab.UNIT_ATTR, *vocab.AI_ATTR),
               'pri_attributes':_WEAPON_ATTR, 'sec_attributes':_WEAPON_ATTR}


class ContractError(ValueError):
    """Internal contract rejection code, never a translated UI message."""


def _json(value, depth=0):
    if depth > 32:
        raise ContractError('json_depth')
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json(item, depth+1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json(item, depth+1)
        return
    raise ContractError('json_value')


def _native(values):
    if not isinstance(values, dict):
        raise ContractError('native_object')
    result = {}
    for key, value in values.items():
        if key not in sheet_ops.FIELDS or value is None:
            raise ContractError('native_field')
        if sheet_ops.FIELDS[key][2] == 'list' and (
                not isinstance(value, list) or not all(isinstance(x, str) for x in value)):
            raise ContractError('native_list')
        try:
            result[key] = sheet_ops.typed(key, value)
        except sheets.SheetError as error:
            raise ContractError('native_type') from error
    return result


def validate_design(design):
    """Validate a complete v1 packet without migrating or mutating its inputs.

    Unknown future data belongs in metadata. An upstream v1 project is a
    different schema and must pass through the Phase 105 adapter explicitly.
    """
    _json(design)
    if len(json.dumps(design, ensure_ascii=True)) > 1_000_000:
        raise ContractError('json_size')
    if (not isinstance(design, dict) or set(design) != _KEYS
            or design['schema'] != SCHEMA or type(design['version']) is not int
            or design['version'] != VERSION):
        raise ContractError('design_schema')
    profile = design['profile']
    if (not isinstance(profile, dict) or set(profile) != {'id','revision'}
            or not isinstance(profile['id'], str) or profile['id'] not in PROFILES
            or profile['revision'] != PROFILES[profile['id']]):
        raise ContractError('rules_profile')
    for key in ('inputs','presets','overrides','metadata'):
        if not isinstance(design[key], dict):
            raise ContractError('design_object')
    overrides = design['overrides']
    if set(overrides) != {'inputs','native'} or not isinstance(overrides['inputs'], dict):
        raise ContractError('overrides_schema')
    _native(overrides['native'])
    return copy.deepcopy(design)


def effective_inputs(design):
    """Apply explicit input pins before calculation; retain the stored baseline."""
    packet = validate_design(design)
    return dict(packet['inputs'], **packet['overrides']['inputs'])


def output_values(design, calculated):
    """Project calculated sheet columns and final overrides through shared types.

    There is no calculation here. Omitted columns mean unchanged. Zero and []
    are explicit values. Unknown/custom attribute proposals stay in metadata,
    including hook and hook_drag, with no alias conversion or runtime opt-in.
    Existing unknown native tags are still owned by the ordinary EDU patcher.
    """
    packet = validate_design(design)
    _json(calculated)
    values = _native(calculated)
    values.update(_native(packet['overrides']['native']))
    omitted = {}
    for key, allowed in _LIST_VOCAB.items():
        if key in values:
            omitted[key] = [tag for tag in values[key] if tag not in allowed]
            values[key] = [tag for tag in values[key] if tag in allowed]
            if not omitted[key]:
                del omitted[key]
    return {'native':values, 'metadata':{'omitted':omitted}}


def native_mapping():
    """The shared sheet field registry is the sole native tuple map."""
    return {key:list(value) for key,value in sheet_ops.FIELDS.items()}


def attach_design(mod, project, uid, design):
    """Return an unsaved sheet project with design metadata on an exact live ID.

    Does not stage native values or save anything. Phase 106 must use the sheet
    preview/revision/source-token checks and normal native Apply path. New units
    first require an explicit donor plan through existing unit creation tools.
    """
    packet = validate_design(design)
    if uid not in sheets.live_units(mod):
        raise ContractError('unit_identity')
    result = sheets.validate_project(copy.deepcopy(project))
    row = result['units'].setdefault(uid, {'annotations':{}, 'extra':{}})
    row['builder_design'] = packet
    return result
