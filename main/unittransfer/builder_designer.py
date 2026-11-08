"""Phase 104 draft service. Config writes only; no staging or Apply action."""
from __future__ import annotations
import copy
from . import builder_calculator as calculator, builder_contract as contract
from . import edu, sheet_ops, unit_sheets as sheets

# Placeholder tuple members let the shared mapper preview a detached design.
# This is a preview scaffold, never a new-unit creation template or mod write.
_PREVIEW = """type builder_preview
soldier builder_preview, 1, 0, 1
stat_pri 0, 0, no, 0, 0, melee, simple, piercing, sword, 0, 1
stat_sec 0, 0, no, 0, 0, melee, simple, piercing, sword, 0, 1
stat_pri_armour 0, 0, 0, flesh
stat_mental 0, normal, trained
stat_cost 1, 0, 0, 0, 0, 0, 1, 1
formation 1, 1, 2, 2, 4, square
stat_ground 0, 0, 0, 0
"""


def service(mod, action, body=None):
    """Preview pure calculations or save packets in the existing sheet project.

    An existing unit uses its Phase 102 attachment. builder_new_design stores
    one detached draft per mod without assigning a fictional unit identity.
    Revision and source checks use the same lock and config writer as sheets.
    """
    body = body or {}
    if action in ('import', 'export'):
        from . import builder_projects
        if action == 'import':
            return {'design':builder_projects.read(body.get('text'), body.get('design'))}
        fmt = body.get('format')
        if fmt in ('project', 'presets', 'upstream'):
            return builder_projects.json_export(body.get('design'), fmt)
        if fmt not in ('edu', 'csv'):
            raise contract.ContractError('project_format')
        result = service(mod, 'preview', body)
        if fmt == 'csv':
            return builder_projects.csv_export(result, body.get('unit', ''))
        return {'name':'builder.edu.txt','mime':'text/plain','text':result['edu']}
    if action not in ('load', 'preview', 'save'):
        raise contract.ContractError('designer_action')
    uid = body.get('unit', '')
    if not isinstance(uid, str):
        raise contract.ContractError('unit_identity')
    units = sheets.live_units(mod)
    if uid and uid not in units:
        raise contract.ContractError('unit_identity')
    if action == 'preview':
        packet = contract.validate_design(body.get('design'))
        engine = 'eop' if getattr(mod, 'eop_dirs', []) else 'vanilla'
        result = calculator.calculate(packet, engine_rules=calculator.load_engine_rules(mod, profile=engine))
        # Reuse the native mapper and EDU editor, including donor comments and
        # untouched tuple members. Detached previews explicitly use placeholders.
        raw = units[uid].raw if uid else _PREVIEW
        present = sheets.fields_of(edu.parse_text(raw).units[0])
        for key, value in edu.block_fields(_PREVIEW):
            if key != 'type' and key not in present:
                raw = edu.set_field(raw, key, value)
        unit = edu.parse_text(raw).units[0]
        changes, removals = sheet_ops.field_changes(unit, result['native'])
        result['edu'] = edu.apply_field_edits(raw, changes, removals)
        result['design'] = packet
        return result
    with sheets._LOCK:
        project = sheets.load_project(mod, persist_migration=False)
        before = sheets.revision(project)
        token = sheets.source_token(mod)
        if action == 'save':
            if body.get('revision') != before or body.get('source_token') != token:
                raise contract.ContractError('designer_stale')
            packet = contract.validate_design(body.get('design'))
            if uid:
                project = contract.attach_design(mod, project, uid, packet)
            else:
                project['builder_new_design'] = packet
            sheets.save_project(mod, project, before)
        packet = (project['units'].get(uid, {}).get('builder_design') if uid
                  else project.get('builder_new_design'))
        if packet is not None:
            packet = contract.validate_design(packet)
        result = {'design':packet, 'revision':sheets.revision(project), 'source_token':token}
        if action == 'load':
            fields = sheets.fields_of(units[uid]) if uid else {}
            result.update(tables=copy.deepcopy(calculator._TABLES),
                          defaults={'unit_category':'Martial Nobility','quality':'Average',
                                    'category':'infantry','class':'heavy','equipment_grade':'common',
                                    'pri_preset':'arming_sword','sec_preset':'none',
                                    'armour_preset':'unarmored','armour_weight':'medium',
                                    'offhand':'empty','origin':'Western European',
                                    'bible_formation_auto':True},
                          native={k:v for k,d in sheet_ops.FIELDS.items()
                                  if (v := sheet_ops.value_of(fields,d)) is not None})
        return result
