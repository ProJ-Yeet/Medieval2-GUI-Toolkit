"""Native unit-sheet projects: stable identities, classifications and adapters.

Game text is owned by edu/buildings/edit. This module stores only sheet metadata,
rule inputs, saved views and staged edits under config; refresh never writes a mod.
"""
from __future__ import annotations
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import threading
from . import config, edu
from . import i18n as _i18n

SCHEMA = 'm2-unit-sheets'
VERSION = 1
ANNOTATIONS = ('Unit Race', 'Tier', 'Main Faction', 'AOR')
RULE_KEYS = {'replenish': ('Tier',), 'experience': ('Unit Race','Category','BarracksTier'),
             'pool': ('Unit Race','Category','BarracksTier')}
_LOCK = threading.RLock()


class SheetError(ValueError):
    pass


def fail(reason):
    raise SheetError(_i18n.msg('eng.sheets.invalid_input','Invalid sheet data: {reason}',reason=reason))


def mod_key(mod):
    return hashlib.sha256(str(Path(mod.data).resolve()).casefold().encode()).hexdigest()[:24]


def project_path(mod):
    return Path(config.CONFIG_DIR)/'unit_sheets'/(mod_key(mod)+'.json')


def default_rule_schema(kind):
    keys = RULE_KEYS[kind]
    names = list(keys)
    if kind != 'replenish':
        names.extend(('T0', 'T1', 'T2', 'T3', 'T4'))
    return [{'name':name, 'type':'text' if name in keys else 'number', 'key':name in keys}
            for name in names]


def empty_project():
    return {'schema':SCHEMA,'version':VERSION,'units':{},'known':[], 'signatures':{},
            'rules':{k:[] for k in RULE_KEYS},'groups':{},'views':{},'recipes':{},'draft':{},
            'comparison':{'ultra_size':2.5,'defense_weight':0.8},
            'rule_schema':{kind:default_rule_schema(kind) for kind in RULE_KEYS}}


def revision(project):
    return hashlib.sha256(json.dumps(project,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def validate_project(project):
    if not isinstance(project,dict) or project.get('schema')!=SCHEMA or project.get('version')!=VERSION:
        fail(_i18n.msg('eng.sheets.unsupported_project_schema_or_version','unsupported project schema or version'))
    for field in ('units','rules','views','recipes','draft','comparison'):
        if not isinstance(project.get(field),dict):fail(_i18n.msg('eng.sheets.expected_an_object_for_value1','expected an object for {value1}',value1=field))
    if not isinstance(project.get('known'),list) or not all(isinstance(x,str) for x in project['known']):fail(_i18n.msg('eng.sheets.invalid_unit_identity_list','invalid unit identity list'))
    for uid,row in project['units'].items():
        if not isinstance(uid,str) or not uid.strip() or not isinstance(row,dict):fail(_i18n.msg('eng.sheets.invalid_unit_identity','invalid unit identity'))
        if not isinstance(row.get('annotations',{}),dict) or not isinstance(row.get('extra',{}),dict):fail(_i18n.msg('eng.sheets.invalid_annotations','invalid annotations'))
    validate_groups(project)
    from . import sheet_ops
    sheet_ops.prepare_rules(project)
    if 'balance_profile' in project:
        if not isinstance(project['balance_profile'],dict):fail(_i18n.msg('eng.sheets.invalid_balance_profile','Balance profile must be an object'))
        from . import edb_balance
        edb_balance.profile_of(project)
    if not isinstance(project.get('balance_overrides',[]),list):fail(_i18n.msg('eng.sheets.invalid_balance_overrides','Balance overrides must be a list'))
    for rule in project.get('balance_overrides',[]):
        if not isinstance(rule,dict) or rule.get('stage') not in RULE_KEYS or not any(rule.get(k) for k in ('unit','building','level')) or 'value' not in rule:
            fail(_i18n.msg('eng.sheets.invalid_balance_override','Each override requires a stage, selector and value'))
    return project


def validate_groups(project):
    # Older projects acquire an empty collection without changing their members.
    groups = project.setdefault('groups', {})
    if not isinstance(groups, dict):
        fail(_i18n.msg('eng.sheets.invalid_groups', 'Invalid comparison groups'))
    for name, members in groups.items():
        if (not isinstance(name, str) or not name.strip() or name != name.strip()
                or len(name) > 120 or any(c in name for c in '\r\n')
                or not isinstance(members, list)
                or not all(isinstance(uid, str) and uid.strip() for uid in members)
                or len(members) != len(set(members))):
            fail(_i18n.msg('eng.sheets.invalid_groups', 'Invalid comparison groups'))


def change_group(mod, project, body):
    from . import sheet_ops
    p = copy.deepcopy(project)
    groups = p['groups']
    name = body.get('name')
    operation = body.get('operation')
    if not isinstance(name, str) or not name.strip():
        fail(_i18n.msg('eng.sheets.invalid_groups', 'Invalid comparison groups'))
    if operation == 'create':
        if name in groups:
            fail(_i18n.msg('eng.sheets.group_exists', 'A comparison group with that name already exists'))
        groups[name] = []
    else:
        if name not in groups:
            fail(_i18n.msg('eng.sheets.group_unknown', 'Choose an existing comparison group'))
        if operation == 'delete':
            del groups[name]
        elif operation == 'rename':
            new_name = body.get('new_name')
            if not isinstance(new_name, str) or new_name in groups:
                fail(_i18n.msg('eng.sheets.group_exists', 'A comparison group with that name already exists'))
            groups[new_name] = groups.pop(name)
        elif operation in ('add', 'remove'):
            ids = body.get('ids')
            rows, _ = sheet_ops.records(mod, project)
            matching = {row['id'] for row in rows if sheet_ops.matches(row, body.get('where'))}
            # Only the explicit matching unit snapshot can change membership.
            if (body.get('view') == 'recruitment' or sheet_ops.rule_kind(body.get('view'))
                    or not isinstance(ids, list) or not ids
                    or not all(isinstance(uid, str) and uid in matching for uid in ids)
                    or len(ids) != len(set(ids))):
                fail(_i18n.msg('eng.sheets.group_selection', 'Select matching live units before changing group membership'))
            if operation == 'add':
                groups[name] = list(dict.fromkeys(groups[name] + ids))
            else:
                groups[name] = [uid for uid in groups[name] if uid not in ids]
        else:
            fail(_i18n.msg('eng.sheets.invalid_groups', 'Invalid comparison groups'))
    validate_groups(p)
    return p


def load_project(mod, persist_migration=True):
    with _LOCK:
        p=project_path(mod)
        if not p.exists():return empty_project()
        try:
            original = json.loads(p.read_text(encoding='utf-8'))
            migrated = validate_project(copy.deepcopy(original))
            if migrated != original and persist_migration:
                config._write_json(p, migrated)
            return migrated
        except (OSError,json.JSONDecodeError) as e:fail(str(e))


def save_project(mod,project,expected=None):
    validate_project(project)
    with _LOCK:
        stored = load_project(mod)
        from . import sheet_ops
        # Old recipes remain inspectable; only newly saved instructions can fail.
        sheet_ops.validate_recipes(project, stored)
        if expected is not None and revision(stored)!=expected:
            fail(_i18n.msg('eng.sheets.the_sheet_project_changed_in_another_window_reload_before_saving','the sheet project changed in another window; reload before saving'))
        config._write_json(project_path(mod),project)
    return revision(project)


def fields_of(unit):
    return {k.lower():v.strip() for k,v in edu.block_fields(unit.raw)}


def unit_signature(unit):
    fields=fields_of(unit)
    for key in ('type','dictionary','info_pic_dir','card_pic_dir'):fields.pop(key,None)
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()


def live_units(mod):
    rows={}
    for unit in mod.edu.units:
        uid=unit.type
        if uid in rows:fail(_i18n.msg('eng.sheets.duplicate_live_unit_id_value1','duplicate live unit ID: {value1}',value1=uid))
        rows[uid]=unit
    return rows


def refresh(mod,project):
    """Return a refreshed project and classification queue; retain removed notes."""
    p=copy.deepcopy(validate_project(project));live=live_units(mod)
    previous=set(p.get('known',[]));now=set(live)
    added=sorted(now-previous);removed=sorted(previous-now)
    signatures={uid:unit_signature(u) for uid,u in live.items()}
    old=p.get('signatures',{})
    suggestions=[]
    for before in removed:
        matches=[uid for uid in added if old.get(before) and signatures[uid]==old[before]]
        if len(matches)==1 and sum(signatures[matches[0]]==old.get(x) for x in removed)==1:
            suggestions.append({'from':before,'to':matches[0]})
    p['known']=sorted(now);p['signatures']=signatures
    queue=[];rows=[]
    for uid,u in live.items():
        meta=p['units'].get(uid,{});a=meta.get('annotations',{})
        missing=[k for k in ('Unit Race','Tier') if not str(a.get(k,'')).strip()]
        if missing:queue.append({'id':uid,'missing':missing})
        rows.append({'id':uid,'Name':uid,'Category':meta.get('category_override') or u.category,
                     'live_category':u.category,'class':u.class_type,'ownership':list(u.ownership),
                     'model':u.soldier_model,'mount':u.mount,'projectile':u.projectile,
                     'attributes':list(u.attributes),'fields':fields_of(u),
                     **{key:str(a.get(key,'')) for key in ANNOTATIONS},
                     'extra':meta.get('extra',{}),'needs_classification':bool(missing)})
    return p,{'rows':rows,'added':added,'removed':removed,'rename_candidates':suggestions,
              'missing_classifications':queue,'retained_absent':sorted(set(p['units'])-now)}


def rename_annotations(project,live,old,new):
    p=copy.deepcopy(project)
    if old in live or new not in live or old not in p['units'] or new in p['units']:
        fail(_i18n.msg('eng.sheets.rename_must_map_an_absent_annotated_id_onto_an_unannotated','rename must map an absent annotated ID onto an unannotated live ID'))
    p['units'][new]=p['units'].pop(old)
    return p


def _csv(text):
    try:
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
        headers=reader.fieldnames or []
        if not headers or len(headers)!=len(set(headers)):fail(_i18n.msg('eng.sheets.missing_or_duplicate_csv_headers','missing or duplicate CSV headers'))
        rows=list(reader)
        if any(None in row for row in rows):fail(_i18n.msg('eng.sheets.csv_row_has_more_values_than_its_headers','CSV row has more values than its headers'))
        return headers,rows
    except csv.Error as e:fail(str(e))


def import_reference(project,text,kind='csv',mapping=None):
    """Import metadata without substituting snapshot stats for current game data."""
    p=copy.deepcopy(project);mapping=mapping or {}
    if kind=='csv':headers,rows=_csv(text)
    elif kind=='edu_json':
        try:data=json.loads(text)
        except ValueError as e:fail(str(e))
        if not isinstance(data,dict) or not data or not all(isinstance(x,dict) for x in data.values()):fail(_i18n.msg('eng.sheets.expected_fynn_keyed_edu_objects','expected Fynn keyed EDU objects'))
        rows=[]
        for uid,values in data.items():
            if values.get('Type',uid)!=uid:fail(_i18n.msg('eng.sheets.json_key_and_type_disagree_value1','JSON key and Type disagree: {value1}',value1=uid))
            rows.append(dict(values,Name=uid))
        headers=sorted({k for row in rows for k in row})
    else:fail(_i18n.msg('eng.sheets.unsupported_unit_import_format','unsupported unit import format'))
    id_col=mapping.get('Name','Name' if 'Name' in headers else 'type' if 'type' in headers else 'Type')
    if id_col not in headers:fail(_i18n.msg('eng.sheets.map_the_unit_id_column_explicitly','map the unit ID column explicitly'))
    seen=set();imported=[]
    for row in rows:
        uid=str(row.get(id_col) or '').strip()
        if not uid:continue
        if uid in seen:fail(_i18n.msg('eng.sheets.duplicate_imported_unit_id_value1','duplicate imported unit ID: {value1}',value1=uid))
        seen.add(uid)
        meta=p['units'].setdefault(uid,{'annotations':{},'extra':{}})
        for key in ANNOTATIONS:
            column=mapping.get(key,key)
            if column in row and row[column] is not None:meta.setdefault('annotations',{})[key]=str(row[column]).strip()
        for key,value in row.items():
            if key!=id_col and key not in ANNOTATIONS and key not in mapping.values():
                meta.setdefault('extra',{})[key]=value
        imported.append(uid)
    if not imported:fail(_i18n.msg('eng.sheets.no_unit_records_found','no unit records found'))
    # Preserve existing known IDs so importing a subset does not mark others deleted.
    p['known']=sorted(set(p['known'])|set(imported))
    return p,{'imported':len(imported),'ids':imported}


def validate_rules(kind,rows):
    if kind not in RULE_KEYS or not isinstance(rows,list):fail(_i18n.msg('eng.sheets.invalid_rule_table','invalid rule table'))
    seen=set()
    for row in rows:
        if not isinstance(row,dict):fail(_i18n.msg('eng.sheets.rule_row_must_be_an_object','rule row must be an object'))
        key=tuple(str(row.get(k,'')).strip() for k in RULE_KEYS[kind])
        if not all(key) or key in seen:fail(_i18n.msg('eng.sheets.missing_or_duplicate_rule_key_value1','missing or duplicate rule key: {value1}',value1=repr(key)))
        seen.add(key)
    return rows


def import_rules(project,text,kind):
    headers,rows=_csv(text)
    required=set(RULE_KEYS.get(kind,()))
    if not required or not required<=set(headers):fail(_i18n.msg('eng.sheets.rule_table_headers_do_not_match_its_type','rule table headers do not match its type'))
    rows=[{k:(v or '').strip() for k,v in row.items()} for row in rows if any(row.values())]
    from . import sheet_ops
    p=copy.deepcopy(project);p['rules'][kind]=rows
    p.setdefault('rule_schema', {}).pop(kind, None)
    sheet_ops.prepare_rules(p)
    for row in rows:
        for column in p['rule_schema'][kind]:
            sheet_ops.rule_value(column, row.get(column['name'], ''))
    return p


def import_edb_json(text):
    """Normalize Fynn recruitment snapshots for comparison, never as a live parser."""
    try:data=json.loads(text)
    except ValueError as e:fail(str(e))
    if not isinstance(data,dict):fail(_i18n.msg('eng.sheets.expected_keyed_edb_json','expected keyed EDB JSON'))
    rows=[]
    for building,chain in data.items():
        if not isinstance(chain,dict) or not isinstance(chain.get('Levels'),list):fail(_i18n.msg('eng.sheets.invalid_edb_building_snapshot','invalid EDB building snapshot'))
        for level in chain['Levels']:
            if not isinstance(level,dict) or not level.get('Name'):fail(_i18n.msg('eng.sheets.invalid_edb_level_snapshot','invalid EDB level snapshot'))
            for cap in level.get('Capabilities',[]):
                if not isinstance(cap,dict):fail(_i18n.msg('eng.sheets.invalid_edb_capability','Invalid EDB capability snapshot'))
                if cap.get('Type')=='recruit_pool':
                    rows.append({'building':building,'level':level['Name'],'unit':cap.get('Unit',''),
                      'initial':cap.get('InitialPoolString',cap.get('InitialPool')),
                      'per_turn':cap.get('ReplenishmentRateString',cap.get('ReplenishmentRate')),
                      'maximum':cap.get('MaximumPoolString',cap.get('MaximumPool')),
                      'experience':cap.get('StartingExperience'),'requires':cap.get('Condition','')})
    return rows


def export_reference(mod,project):
    _,snapshot=refresh(mod,project)
    headers=['Name',*ANNOTATIONS,'Category']
    extras=sorted({k for row in snapshot['rows'] for k in row['extra'] if k not in headers})
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=headers+extras);writer.writeheader()
    for row in snapshot['rows']:
        values={k:row.get(k,'') for k in headers};values.update({k:row['extra'].get(k,'') for k in extras})
        writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in values.items()})
    return out.getvalue()


def source_token(mod):
    return hashlib.sha256(''.join(u.type+'\0'+u.raw+'\0'+getattr(u,'eop_file','') for u in mod.edu.units).encode()).hexdigest()


def service(mod,action,body=None):
    """Sheet API. Everything here writes project config only, never game data."""
    from . import sheet_ops
    body=body or {}
    with _LOCK:
        dry_run = body.get('dry_run') is True and action in ('operate', 'paste')
        p=load_project(mod, persist_migration=not dry_run);before=revision(p)
        original_project = copy.deepcopy(p)
        if action not in ('load','query','export'):
            if body.get('revision')!=before:fail(_i18n.msg('eng.sheets.the_sheet_project_changed_reload_before_editing','the sheet project changed; reload before editing'))
            if body.get('source_token')!=source_token(mod):fail(_i18n.msg('eng.sheets.game_data_changed_refresh_before_editing','game data changed; refresh before editing'))
        report={}
        recipe = None
        if action == 'operate' and 'recipe_name' in body:
            name = body['recipe_name']
            if not isinstance(name, str) or name not in p['recipes']:
                fail(_i18n.msg('sheets.invalid_recipe', 'Invalid recipe operation, column or value'))
            recipe = p['recipes'][name]
            sheet_ops.validate_recipes(dict(p, recipes={name:recipe}))
            target = recipe.get('target') or {}
            if 'profile' not in target:
                view = target.get('view', body.get('view'))
                if view == 'rules':
                    view = 'rules:' + target['rule_table']
                if view != body.get('view'):
                    fail(_i18n.msg('sheets.invalid_recipe_target', 'Unknown recipe view, rule table or balance profile'))
                body = dict(body, **{key:recipe.get(key) for key in ('column','operation','value','other')})
        profile_recipe = recipe is not None and 'profile' in (recipe.get('target') or {})
        rule_kind = sheet_ops.rule_kind(body.get('view'))
        if action in ('operate', 'paste') and not profile_recipe:
            if body.get('view') == 'recruitment':
                fail(_i18n.msg('eng.sheets.this_column_is_read_only', 'this column is read-only'))
            target_rows = (sheet_ops.rule_records(p, rule_kind)[0] if rule_kind
                           else sheet_ops.records(mod, p)[0])
            if action == 'operate':
                target_ids = sheet_ops.operation_targets(target_rows, body.get('ids'),
                    body.get('mode', 'selected'), body.get('where'))
            elif isinstance(body.get('cells'), list) and body['cells']:
                # A pasted rectangle can repeat IDs across columns, but not escape its filter.
                ids = list(dict.fromkeys(cell.get('id') for cell in body['cells']
                                        if isinstance(cell, dict) and isinstance(cell.get('id'), str)))
                sheet_ops.operation_targets(target_rows, ids, where=body.get('where'))
        if action in ('native_preview','native_apply'):
            from . import sheet_native
            if action=='native_preview':return sheet_native.preview(mod,p)
            record=sheet_native.apply(mod,p,body.get('plan_token'))
            p['draft']={};p['draft_sources']={}
            try:save_project(mod,p,before)
            except OSError:
                return {'record':record,'warning':_i18n.msg('eng.sheets.applied_project_unsaved','Unit edits were applied and logged, but their project drafts could not be cleared. Reload and discard the stale drafts.')}
            return {'record':record}
        if action=='balance_apply':
            from . import edb_balance
            return {'record':edb_balance.apply_preview(mod,p,body.get('stages'),body.get('plan_token'))}
        if action in ('balance_preview','balance_export'):
            from . import edb_balance
            result=edb_balance.preview(mod,p,body.get('stages'))
            if action=='balance_preview':
                # Full audit logs belong in the export, not a multi-megabyte DOM.
                compact={k:v for k,v in result.items() if k not in ('text','exports','logs')}
                compact['logs']={stage:{'counts':logs['counts'],'all':logs['all'][:100],
                    'issues':logs['issues'][:100],'total':len(logs['all']),
                    'truncated':len(logs['all'])>100 or len(logs['issues'])>100}
                    for stage,logs in result['logs'].items()}
                return compact
            import base64,zipfile
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr('export_descr_buildings_new.txt',result['text'].encode('latin-1'))
                if body.get('intermediate'):
                    for stage,suffix in [('replenish','r'),('experience','exp')]:
                        if stage in result['exports']:bundle.writestr('export_descr_buildings_'+suffix+'.txt',result['exports'][stage].encode('latin-1'))
                bundle.writestr('building_structure_log.json',json.dumps(result['structure'],indent=2))
                bundle.writestr('profile.json',json.dumps(result['profile'],indent=2))
                for stage,logs in result['logs'].items():
                    for kind,entries in [('all',logs['all']),('skip_error',logs['issues'])]:
                        bundle.writestr('logs/'+stage+'_'+kind+'.json',json.dumps(entries,indent=2,ensure_ascii=False))
            return {'name':'EDB_balance_export.zip','mime':'application/zip','encoding':'base64',
                    'text':base64.b64encode(archive.getvalue()).decode('ascii')}
        if action=='import':
            kind=body.get('kind','csv');text=body.get('text','')
            if len(text)>20*1024*1024:fail(_i18n.msg('eng.sheets.import_is_larger_than_20_mb','import is larger than 20 MB'))
            if kind in RULE_KEYS:p=import_rules(p,text,kind)
            elif kind=='project':
                try:p=validate_project(json.loads(text))
                except json.JSONDecodeError as e:fail(str(e))
            elif kind=='edb_json':
                report={'snapshot_recruits':len(import_edb_json(text))}
            else:p,report=import_reference(p,text,kind,body.get('mapping'))
        elif action == 'group':
            p = change_group(mod, p, body)
        elif action == 'rule_structure':
            if rule_kind is None:
                fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
            p = sheet_ops.rule_structure(p, rule_kind, body)
        elif action == 'operate' and profile_recipe:
            p, changes = sheet_ops.stage_profile_recipe(p, recipe)
            report = {'changes':changes}
        elif action == 'operate' and rule_kind:
            p, changes = sheet_ops.stage_rule_operation(p, rule_kind, target_ids,
                body.get('column'), body.get('operation', 'set'), body.get('value'))
            report = {'changes':changes}
        elif action == 'paste' and rule_kind:
            p, changes = sheet_ops.stage_rule_cells(p, rule_kind, body.get('cells'))
            report = {'changes':changes}
        elif action=='operate':
            p,changes=sheet_ops.stage_operation(mod,p,target_ids,str(body.get('column','')),
                                               body.get('operation','set'),body.get('value'),body.get('other'))
            report={'changes':changes}
        elif action=='paste':
            p,changes=sheet_ops.stage_cells(mod,p,body.get('cells'));report={'changes':changes}
        elif action=='save':
            p=validate_project(body.get('project'))
        elif action=='rename':p=rename_annotations(p,live_units(mod),str(body.get('old','')),str(body.get('new','')))
        elif action=='export':
            kind=body.get('kind','project')
            if kind=='reference':return {'name':'EDU_Reference.csv','text':export_reference(mod,p),'mime':'text/csv'}
            if kind in RULE_KEYS:
                rows=p['rules'][kind]
                headers=['id', *[column['name'] for column in p['rule_schema'][kind]]]
                out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=headers);writer.writeheader();writer.writerows(rows)
                return {'name':kind+'.csv','text':out.getvalue(),'mime':'text/csv'}
            return {'name':'unit_sheets_project.json','text':json.dumps(p,indent=2,ensure_ascii=False),'mime':'application/json'}
        elif action not in ('load','query'):fail(_i18n.msg('eng.sheets.unknown_sheet_action','unknown sheet action'))
        if action == 'save' or action == 'import' and body.get('kind') == 'project':
            # Project replacement cannot bypass typed rule-cell validation.
            for kind in RULE_KEYS:
                old_rows = {row['id']:row for row in original_project['rules'][kind]}
                for row in p['rules'][kind]:
                    for column in p['rule_schema'][kind]:
                        name = column['name']
                        if row.get(name, '') != old_rows.get(row['id'], {}).get(name, ''):
                            sheet_ops.rule_value(column, row.get(name, ''))
        for uid in set(p['units']) | set(original_project['units']):
            sheet_ops.remember_classification(p, original_project, uid)
        p,snapshot=refresh(mod,p)
        rows,_=sheet_ops.records(mod,p)
        comparison_group = sheet_ops.compare_group(mod, p, body.get('comparison_group'), rows)
        stale_drafts=[r['id'] for r in rows if r.get('stale_draft')]
        if revision(p)!=before and not dry_run:save_project(mod,p,before)
        if body.get('view')=='recruitment':
            from . import edb_balance
            native = {row['id']: row for row in rows}
            edb = edb_balance.fresh_edb(mod)
            policy = edb_balance.profile_of(p)['branch_policy']
            structures = {chain.name: edb_balance.graph(chain, policy) for chain in edb.buildings}
            building_types = {chain.name: chain.extras.get('classification') or None
                              for chain in edb.buildings}
            rows = edb_balance.recruitments(edb)
            for row in rows:
                source = native.get(row['unit'], {})
                for key in sheet_ops.RECRUIT_CONTEXT:
                    row[key] = source.get(key, False if key in ('changed', 'needs_classification') else None)
                structure = structures[row['building']]
                # Classification is optional EDB data, never inferred from the chain name.
                row['building_type'] = building_types[row['building']]
                # Graph errors must not silently assign an unknown level tier zero.
                depth = None if structure['errors'] else structure['depths'].get(row['level'])
                row['building_depth'] = depth
                row['building_tier'] = min(depth + 1, 5) if depth is not None else None
                row['invalid_columns'] = []
                for key in sheet_ops.RECRUIT_NUMBERS:
                    try:
                        value = sheet_ops.number(row[key])
                        if value < 0 or key == 'experience' and not value.is_integer():
                            row['invalid_columns'].append(key)
                        else:
                            row[key] = value
                    except SheetError:
                        # Preserve bad source tokens for inspection and invalid filters.
                        row['invalid_columns'].append(key)
        if rule_kind:
            rows, info, frozen, issues = sheet_ops.rule_records(p, rule_kind)
            report.update(filter_info=info, frozen_columns=frozen, rule_issues=issues,
                          columns=[column['name'] for column in p['rule_schema'][rule_kind]],
                          field_info={column['name']:{'type':column['type'], 'view':body['view']}
                                      for column in p['rule_schema'][rule_kind]})
        table=sheet_ops.query(rows,body.get('where'),body.get('sort'),body.get('offset',0),body.get('limit',100))
        if action in ('operate', 'paste'):
            report['target_count'] = len({change['id'] for change in report['changes']})
        if dry_run:
            # Return the persisted state so a cancelled preview needs no undo.
            p = original_project
        from . import edb_balance
        # Share server defaults without persisting them as project overrides.
        return {'project':p,'revision':revision(p),'source_token':source_token(mod),'stale_drafts':stale_drafts,
                'balance_effective':edb_balance.profile_of(p),
                'invalid_recipes':sheet_ops.invalid_recipes(p),
                'comparison_group':comparison_group,
                'table':table,'refresh':{k:v for k,v in snapshot.items() if k!='rows'},
                'filter_info':sheet_ops.filter_info(rows, body.get('view') == 'recruitment'),
                'columns':list(sheet_ops.FIELDS),'field_info':{k:{'type':v[2],'view':v[3]} for k,v in sheet_ops.FIELDS.items()},
                'extra_columns':sorted({k for row in rows for k in row if k.startswith('extra:')}),**report}
