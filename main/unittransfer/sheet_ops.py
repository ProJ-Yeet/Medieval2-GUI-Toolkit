"""Typed sheet columns, safe filtering and transactional staged operations."""
from __future__ import annotations
from . import i18n as _i18n
import ast
import copy
from functools import cmp_to_key
import math
from . import unit_sheets as sheets

# id -> (EDU field, tuple member or None, type, view). Metadata stays outside EDU.
FIELDS={
 'category':('category',None,'text','base'),'class':('class',None,'text','base'),
 'unit_size':('soldier',1,'int','base'),'movement':('move_speed_mod',None,'number','base'),
 'attack':('stat_pri',0,'int','base'),'charge':('stat_pri',1,'int','base'),
 'missile':('stat_pri',2,'text','base'),'range':('stat_pri',3,'number','base'),
 'ammo':('stat_pri',4,'number','base'),'attack_delay':('stat_pri',9,'number','base'),
 'sec_attack':('stat_sec',0,'int','base'),'sec_charge':('stat_sec',1,'int','base'),
 'sec_delay':('stat_sec',9,'number','base'),
 'armor':('stat_pri_armour',0,'int','base'),'defense':('stat_pri_armour',1,'int','base'),
 'shield':('stat_pri_armour',2,'int','base'),'morale':('stat_mental',0,'int','base'),
 'discipline':('stat_mental',1,'text','base'),'training':('stat_mental',2,'text','base'),
 'recruit_turns':('stat_cost',0,'int','base'),'recruit_cost':('stat_cost',1,'int','base'),
 'upkeep':('stat_cost',2,'int','base'),'weapon_upgrade_cost':('stat_cost',3,'int','base'),
 'armor_upgrade_cost':('stat_cost',4,'int','base'),'custom_cost':('stat_cost',5,'int','base'),
 'custom_limit':('stat_cost',6,'int','base'),'custom_stacking':('stat_cost',7,'int','base'),
 'attributes':('attributes',None,'list','attributes'),'pri_attributes':('stat_pri_attr',None,'list','attributes'),
 'sec_attributes':('stat_sec_attr',None,'list','attributes'),
 'close_side':('formation',0,'number','soft'),'close_front':('formation',1,'number','soft'),
 'loose_side':('formation',2,'number','soft'),'loose_front':('formation',3,'number','soft'),
 'ranks':('formation',4,'int','soft'),'formation':('formation',5,'text','soft'),
 'scrub':('stat_ground',0,'int','soft'),'sand':('stat_ground',1,'int','soft'),
 'forest':('stat_ground',2,'int','soft'),'snow':('stat_ground',3,'int','soft'),
 'mount_effect':('mount_effect',None,'list','soft'),
 'recruit_priority':('recruit_priority_offset',None,'number','soft')}
META={'Unit Race','Tier','Main Faction','AOR','Category override'}
CONTEXT={'id','Name','ownership','model','mount','projectile','needs_classification','changed',
         'defense_total','ultra_size','cost_efficiency','upkeep_efficiency'}


def number(value):
    try:
        n=float(value)
        if not math.isfinite(n):raise ValueError()
        return n
    except (ValueError,TypeError):sheets.fail(_i18n.msg('eng.sheets.expected_a_finite_number','expected a finite number'))


def value_of(fields,definition):
    key,index,kind,_=definition
    text=fields.get(key)
    if text is None:return None
    if index is not None:
        parts=text.split(',')
        if index>=len(parts):return None
        text=parts[index].strip()
    if kind=='list':return [x.strip() for x in text.split(',') if x.strip() and x.strip()!='no']
    if kind in ('int','number'):
        try:
            n = float(text)
            if math.isfinite(n):
                return int(n) if kind == 'int' and n.is_integer() else n
        except ValueError:
            pass
        # Keep malformed source text visible and distinct from an absent member.
        return text
    return text


def typed(column,value):
    if column in META:
        if isinstance(value,(dict,list)) or '\n' in str(value):sheets.fail(_i18n.msg('eng.sheets.expected_a_single_text_value','expected a single text value'))
        return str(value).strip()
    if column not in FIELDS:sheets.fail(_i18n.msg('eng.sheets.this_column_is_read_only_or_unknown_value1','this column is read-only or unknown: {value1}',value1=column))
    kind=FIELDS[column][2]
    if kind in ('int','number'):
        n=number(value)
        if kind=='int' and not n.is_integer():sheets.fail(_i18n.msg('eng.sheets.this_column_requires_a_whole_number','this column requires a whole number'))
        if n<0 and column not in {'morale','scrub','sand','forest','snow','recruit_priority'}:sheets.fail(_i18n.msg('eng.sheets.negative_value_is_not_allowed_in_value1','negative value is not allowed in {value1}',value1=column))
        return int(n) if kind=='int' else n
    if kind=='list':
        if not isinstance(value,list) and not str(value).strip():sheets.fail(_i18n.msg('eng.sheets.explicit_list_clear','Use Clear to remove a list; an empty edit is not a replacement'))
        values=value if isinstance(value,list) else str(value).split(',')
        if any(any(c in str(x) for c in '\r\n;') for x in values):sheets.fail(_i18n.msg('eng.sheets.invalid_list_item','invalid list item'))
        return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip() and str(x).strip()!='no'))
    text=str(value).strip()
    if any(c in text for c in '\r\n;,'):sheets.fail(_i18n.msg('eng.sheets.invalid_text_value','invalid text value'))
    if column=='category' and text not in {'infantry','cavalry','siege','ship','handler','non_combatant'}:sheets.fail(_i18n.msg('eng.sheets.unknown_edu_category','unknown EDU category'))
    if not text:sheets.fail(_i18n.msg('eng.sheets.use_an_explicit_clear_operation_instead_of_empty_text','use an explicit clear operation instead of empty text'))
    return text


def field_changes(unit,columns):
    """Convert typed staged cells to existing EDU field edits, retaining other slots."""
    fields=sheets.fields_of(unit);changed={};removals=[]
    for column,value in columns.items():
        if column not in FIELDS:sheets.fail(_i18n.msg('eng.sheets.unknown_staged_column_value1','unknown staged column: {value1}',value1=column))
        key,index,kind,_=FIELDS[column]
        if value is None:
            if index is not None:sheets.fail(_i18n.msg('eng.sheets.cannot_clear_an_individual_required_tuple_member_value1','cannot clear an individual required tuple member: {value1}',value1=column))
            removals.append(key);continue
        value=typed(column,value)
        if key=='attributes' and value==[]:
            removals.append(key);continue
        text=(', '.join(value) or 'no') if kind=='list' else str(value)
        if isinstance(value,float) and value.is_integer():text=str(int(value))
        if index is None:changed[key]=text;continue
        parts=(changed.get(key,fields.get(key,''))).split(',')
        if index>=len(parts):sheets.fail(_i18n.msg('eng.sheets.the_original_field_has_no_requested_tuple_member_value1','the original field has no requested tuple member: {value1}',value1=column))
        old=parts[index];lead=old[:len(old)-len(old.lstrip())];tail=old[len(old.rstrip()):]
        parts[index]=lead+text+tail;changed[key]=','.join(parts)
    return changed,removals


WEAPON_MEMBERS = {
    'pri_weapon_type': ('stat_pri', 5), 'pri_tech_type': ('stat_pri', 6),
    'sec_weapon_type': ('stat_sec', 5), 'sec_tech_type': ('stat_sec', 6),
}
RECRUIT_NUMBERS = ('initial', 'per_turn', 'maximum', 'experience')
RECRUIT_CONTEXT = (*sheets.ANNOTATIONS, 'Category override', 'Category', 'class',
                   'ownership', 'model', 'mount', 'projectile', 'changed',
                   'needs_classification', 'groups', *WEAPON_MEMBERS)


def classification_state(project, uid):
    meta = project.get('units', {}).get(uid, {})
    return {**{key: str(meta.get('annotations', {}).get(key, ''))
               for key in sheets.ANNOTATIONS},
            'Category override': meta.get('category_override', '')}


def remember_classification(project, before, uid):
    # A baseline lets changed include config edits and become false on reversion.
    if classification_state(project, uid) != classification_state(before, uid):
        project.setdefault('classification_sources', {}).setdefault(
            uid, copy.deepcopy(before.get('classification_sources', {}).get(
                uid, classification_state(before, uid))))


def filter_info(rows, recruitment=False):
    """Publish the row contract even when the current source contains no rows."""
    kinds = {key: 'text' for key in ('id', *RECRUIT_CONTEXT)}
    kinds.update(ownership='list', groups='list', changed='bool', needs_classification='bool')
    if recruitment:
        kinds.update({key: 'text' for key in
                      ('unit', 'building', 'building_type', 'level', 'settlement', 'section', 'requires')})
        kinds.update({key: 'number' for key in
                      (*RECRUIT_NUMBERS, 'line', 'building_depth', 'building_tier')})
    else:
        kinds.update({key: 'text' for key in ('Name', 'live_category')})
        kinds.update({key: 'number' if definition[2] == 'int' else definition[2]
                      for key, definition in FIELDS.items()})
        kinds.update({key: 'number' for key in
                      ('defense_total', 'ultra_size', 'cost_efficiency', 'upkeep_efficiency')})
        for row in rows:
            for key, value in row.items():
                if key.startswith('extra:'):
                    if isinstance(value, bool):
                        kinds[key] = 'bool'
                    elif isinstance(value, (int, float)):
                        kinds[key] = 'number'
                    elif isinstance(value, list):
                        kinds[key] = 'list'
                    elif value is not None or key not in kinds:
                        kinds[key] = 'text'
    return {key: {'type': kind, 'kind': column_kind(key),
                  'readonly': recruitment or key not in FIELDS and key not in META}
            for key, kind in kinds.items()}


def invalid_native(column, value):
    if value is None:
        return False
    try:
        typed(column, value)
        return False
    except sheets.SheetError:
        return True


def valid_number(row, column):
    # Derived arithmetic must never consume malformed or forbidden source values.
    return row.get(column) if column not in row['invalid_columns'] else None


def records(mod,project):
    _,snapshot=sheets.refresh(mod,project)
    units=sheets.live_units(mod);rows=[]
    for source in snapshot['rows']:
        uid=source['id'];fields=source['fields'];draft=project['draft'].get(uid,{})
        expected=project.get('draft_sources',{}).get(uid)
        stale=bool(draft and expected and expected!=sheets.revision({'raw':units[uid].raw}))
        if draft and not stale:
            changes,removals=field_changes(units[uid],draft)
            fields=dict(fields);fields.update(changes)
            for key in removals:fields.pop(key,None)
        row={k:v for k,v in source.items() if k not in ('fields','extra','attributes','class')}
        row.update({column:value_of(fields,definition) for column,definition in FIELDS.items()})
        row['invalid_columns'] = [column for column in FIELDS
                                  if invalid_native(column, row[column])]
        for column, (key, index) in WEAPON_MEMBERS.items():
            row[column] = value_of(fields, (key, index, 'text', 'base'))
        # Use the same pri-then-sec projectile policy as EDU, against staged fields.
        projectiles = [value_of(fields, (key, 2, 'text', 'base'))
                       for key in ('stat_pri', 'stat_sec')]
        row['projectile'] = next((value for value in projectiles
                                  if value and value.lower() != 'no'), '')
        row['Category override']=project['units'].get(uid,{}).get('category_override','')
        row['Category']=row['Category override'] or row.get('category')
        baseline = project.get('classification_sources', {}).get(uid)
        row['changed'] = bool(draft) or (baseline is not None and
                                       baseline != classification_state(project, uid))
        row['groups'] = [name for name, members in project.get('groups', {}).items() if uid in members]
        row['stale_draft']=stale
        a, d, shield = (valid_number(row, key) for key in ('armor', 'defense', 'shield'))
        row['defense_total']=a+d+shield if None not in (a,d,shield) else None
        size=valid_number(row, 'unit_size');row['ultra_size']=size*number(project['comparison'].get('ultra_size',2.5)) if size is not None else None
        atk=valid_number(row, 'attack');weight=number(project['comparison'].get('defense_weight',.8))
        denom=atk+a+weight*d+shield if None not in (atk,a,d,shield) else None
        for name,col in [('cost_efficiency','recruit_cost'),('upkeep_efficiency','upkeep')]:
            row[name]=row[col]/denom if valid_number(row, col) is not None and denom not in (None,0) else None
        for k,v in source['extra'].items():row['extra:'+k]=v
        rows.append(row)
    extras={key for row in rows for key in row if key.startswith('extra:')}
    for row in rows:
        for key in extras:row.setdefault(key,None)
    return rows,snapshot


DERIVED_COLUMNS = ('defense_total', 'ultra_size', 'cost_efficiency', 'upkeep_efficiency')


def column_kind(column):
    if column in FIELDS:
        return 'native'
    if column in META or column in ('id', 'Name', 'Category', 'groups') or column.startswith('extra:'):
        return 'annotation'
    return 'derived'


def compare_group(mod, project, name, rows=None):
    """Compare the complete saved group, independent of grid filtering and paging."""
    if not name or name not in project.get('groups', {}):
        return None
    if rows is None:
        rows, _ = records(mod, project)
    by_id = {row['id']: row for row in rows}
    columns = [key for key, definition in FIELDS.items() if definition[3] == 'base']
    columns.extend(DERIVED_COLUMNS)
    members = []
    for uid in project['groups'][name]:
        source = by_id.get(uid)
        members.append({**{column: source.get(column) if source else None for column in columns},
                        'id':uid, 'missing':source is None, 'difference':{}})
    statistics = {}
    for column in columns:
        numeric = column in DERIVED_COLUMNS or FIELDS[column][2] in ('int', 'number')
        if not numeric:
            continue
        # Missing and invalid source values have no vote in the group average.
        values = [member[column] for member in members
                  if not member['missing'] and column not in by_id[member['id']]['invalid_columns']
                  and isinstance(member[column], (int, float)) and math.isfinite(member[column])]
        average = sum(values) / len(values) if values else None
        statistics[column] = {'min':min(values) if values else None,
                              'max':max(values) if values else None,
                              'average':average, 'count':len(values)}
        for member in members:
            value = member[column]
            valid = (not member['missing'] and column not in by_id[member['id']]['invalid_columns']
                     and isinstance(value, (int, float)) and math.isfinite(value))
            member['difference'][column] = value - average if valid and average is not None else None
    return {'name':name, 'columns':columns, 'members':members, 'statistics':statistics,
            'column_kinds':{column:column_kind(column) for column in columns}}


def matches(row,expr,depth=0):
    if not expr:return True
    if depth>8 or not isinstance(expr,dict):sheets.fail(_i18n.msg('eng.sheets.filter_nesting_is_invalid_or_too_deep','filter nesting is invalid or too deep'))
    if 'all' in expr or 'any' in expr:
        key='all' if 'all' in expr else 'any';children=expr[key]
        if not isinstance(children,list) or len(children)>64:sheets.fail(_i18n.msg('eng.sheets.invalid_filter_group','invalid filter group'))
        values=[matches(row,x,depth+1) for x in children]
        return all(values) if key=='all' else any(values)
    if 'not' in expr:return not matches(row,expr['not'],depth+1)
    key=expr.get('column');op=expr.get('op','eq');want=expr.get('value');value=row.get(key)
    if key not in row:sheets.fail(_i18n.msg('eng.sheets.unknown_filter_column_value1','unknown filter column: {value1}',value1=str(key)))
    if op=='missing':return value is None and key not in row.get('invalid_columns', [])
    if op=='blank':return value is None or value=='' or value==[]
    if op=='invalid':
        if 'invalid_columns' in row:return key in row['invalid_columns']
        if key in FIELDS and FIELDS[key][2] in ('int','number'):
            return value is None
        return value is None
    if op in ('gt','ge','lt','le'):
        if value is None or value=='':return False
        if key in row.get('invalid_columns', []):
            return False
        a,b=number(value),number(want)
        return {'gt':a>b,'ge':a>=b,'lt':a<b,'le':a<=b}[op]
    if isinstance(value,list):hit=str(want).casefold() in {str(x).casefold() for x in value}
    else:hit=str(want if want is not None else '').casefold() in str(value if value is not None else '').casefold()
    if op in ('contains','not_contains'):return hit if op=='contains' else not hit
    if op in ('eq','ne'):
        same=value==want if isinstance(value,(int,float,bool)) else str(value or '').casefold()==str(want or '').casefold()
        if isinstance(value, bool):
            if isinstance(want, str):
                normalized = want.strip().lower()
                same = normalized in ('true', 'false') and value == (normalized == 'true')
            else:
                same = isinstance(want, bool) and value == want
        elif isinstance(value,(int,float)) and isinstance(want,str):
            try:same=number(value)==number(want)
            except sheets.SheetError:same=False
        return same if op=='eq' else not same
    sheets.fail(_i18n.msg('eng.sheets.unknown_filter_operator','unknown filter operator'))


def query(rows,where=None,sort=None,offset=0,limit=100):
    matched=[row for row in rows if matches(row,where)]
    sort=sort or [{'column':'id','desc':False}]
    if len(sort)>8:sheets.fail(_i18n.msg('eng.sheets.at_most_eight_sort_columns','at most eight sort columns'))
    for spec in sort:
        if rows and spec.get('column') not in rows[0]:sheets.fail(_i18n.msg('eng.sheets.unknown_sort_column','unknown sort column'))
    def compare(a,b):
        for spec in sort:
            x,y=a.get(spec['column']),b.get(spec['column'])
            if x is None or y is None:
                c=0 if x is y else 1 if x is None else -1
            else:
                if not isinstance(x,(int,float)) or not isinstance(y,(int,float)):x,y=str(x).casefold(),str(y).casefold()
                c=(x>y)-(x<y)
                if spec.get('desc'):c=-c
            if c:return c
        return (a['id']>b['id'])-(a['id']<b['id'])
    matched.sort(key=cmp_to_key(compare));offset=max(0,int(offset));limit=max(1,min(300,int(limit)))
    return {'rows':matched[offset:offset+limit],'total':len(matched),'matched_ids':[r['id'] for r in matched], 'offset':offset,'limit':limit}


def expression(text,row):
    """Small numeric expression language: column names, + - * / and constants."""
    try:tree=ast.parse(str(text),mode='eval')
    except (SyntaxError,ValueError):sheets.fail(_i18n.msg('eng.sheets.invalid_arithmetic_expression','invalid arithmetic expression'))
    if len(list(ast.walk(tree)))>64:sheets.fail(_i18n.msg('eng.sheets.expression_is_too_long','expression is too long'))
    def walk(n):
        if isinstance(n,ast.Expression):return walk(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):return number(n.value)
        if isinstance(n,ast.Name) and n.id in row:return number(row[n.id])
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return walk(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if b==0:sheets.fail(_i18n.msg('eng.sheets.division_by_zero','division by zero'))
            return a/b
        sheets.fail(_i18n.msg('eng.sheets.only_numeric_columns_constants_and_are_supported','only numeric columns, constants and + - * / are supported'))
    return number(walk(tree))


def stage_operation(mod,project,ids,column,operation,value=None,other=None):
    """One all-or-nothing operation; save config only after the caller reviews it."""
    if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)):sheets.fail(_i18n.msg('eng.sheets.select_distinct_unit_ids_first','select distinct unit IDs first'))
    p=copy.deepcopy(project);rows,_=records(mod,p);live={r['id']:r for r in rows}
    if any(not isinstance(uid, str) or uid not in live for uid in ids):sheets.fail(_i18n.msg('eng.sheets.selected_units_changed_refresh_before_editing','selected units changed; refresh before editing'))
    if any(live[uid].get('stale_draft') for uid in ids):sheets.fail(_i18n.msg('eng.sheets.stale_draft_edit','Discard stale unit drafts before editing those units again'))
    if column not in META and column not in FIELDS:sheets.fail(_i18n.msg('eng.sheets.this_column_is_read_only','this column is read-only'))
    units=sheets.live_units(mod);changes=[]
    for uid in ids:
        old=live[uid].get(column);new=value
        if operation=='clear':new='' if column in META else [] if FIELDS[column][2]=='list' else None
        elif operation in ('add','subtract','multiply','divide','percent','min','max','round'):
            a,b=number(old),number(value)
            if operation=='divide' and b==0:sheets.fail(_i18n.msg('eng.sheets.division_by_zero','division by zero'))
            if operation=='add':new=a+b
            elif operation=='subtract':new=a-b
            elif operation=='multiply':new=a*b
            elif operation=='divide':new=a/b
            elif operation=='percent':new=a*(1+b/100)
            elif operation=='min':new=max(a,b)
            elif operation=='max':new=min(a,b)
            else:
                if not b.is_integer() or not -6<=b<=6:sheets.fail(_i18n.msg('eng.sheets.rounding_digits_must_be_between_6_and_6','rounding digits must be between -6 and 6'))
                new=round(a,int(b))
        elif operation=='expression':new=expression(value,live[uid])
        elif operation=='copy':
            if value not in live[uid]:sheets.fail(_i18n.msg('eng.sheets.unknown_source_column','unknown source column'))
            new=live[uid][value]
        elif operation=='replace':
            new=[str(x).replace(str(value),str(other or '')) for x in old] if isinstance(old,list) else str(old or '').replace(str(value),str(other or ''))
        elif operation in ('append','remove','deduplicate'):
            values=old if isinstance(old,list) else [s.strip() for s in str(old or '').split(',') if s.strip()]
            target=typed(column,value or [])
            if not isinstance(target,list):sheets.fail(_i18n.msg('eng.sheets.list_operation_requires_an_attribute_column','list operation requires an attribute column'))
            new=list(dict.fromkeys(values+(target if operation=='append' else [])))
            if operation=='remove':new=[v for v in new if v not in target]
        elif operation!='set':sheets.fail(_i18n.msg('eng.sheets.unknown_edit_operation','unknown edit operation'))
        if new is None and operation!='clear':sheets.fail(_i18n.msg('eng.sheets.explicit_clear_required','Missing values cannot be copied or set; use Clear explicitly'))
        if new is not None:new=typed(column,new)
        if column in META:
            meta=p['units'].setdefault(uid,{'annotations':{},'extra':{}})
            if column=='Category override':meta['category_override']=new
            else:meta.setdefault('annotations',{})[column]=new
        else:
            p['draft'].setdefault(uid,{})[column]=new
            p.setdefault('draft_sources',{}).setdefault(uid,sheets.revision({'raw':units[uid].raw}))
            field_changes(units[uid],p['draft'][uid])
        remember_classification(p, project, uid)
        changes.append({'id':uid,'column':column,'before':old,'after':new})
    return p,changes


def stage_cells(mod,project,cells):
    if not isinstance(cells,list) or not cells or len(cells)>10000:sheets.fail(_i18n.msg('eng.sheets.paste_must_contain_1_10000_cells','paste must contain 1-10000 cells'))
    p=copy.deepcopy(project);units=sheets.live_units(mod);rows,_=records(mod,p);before={r['id']:r for r in rows};changes=[]
    for cell in cells:
        uid,column=cell.get('id'),cell.get('column')
        if uid not in units:sheets.fail(_i18n.msg('eng.sheets.unknown_unit_in_pasted_cells','unknown unit in pasted cells'))
        if before[uid].get('stale_draft'):sheets.fail(_i18n.msg('eng.sheets.stale_draft_edit','Discard stale unit drafts before editing those units again'))
        value=typed(column,cell.get('value'))
        if column in META:
            meta=p['units'].setdefault(uid,{'annotations':{},'extra':{}})
            if column=='Category override':meta['category_override']=value
            else:meta.setdefault('annotations',{})[column]=value
        else:
            p['draft'].setdefault(uid,{})[column]=value
            p.setdefault('draft_sources',{}).setdefault(uid,sheets.revision({'raw':units[uid].raw}))
        remember_classification(p, project, uid)
        changes.append({'id':uid,'column':column,'before':before[uid].get(column),'after':value})
    for uid in {c['id'] for c in cells}:
        field_changes(units[uid],p['draft'].get(uid,{}))
    return p,changes


RULE_RESERVED = {'id', 'invalid_columns', 'changed'}


def prepare_rules(project):
    """Migrate identities deterministically so old revisions remain reproducible."""
    import uuid
    schemas = project.setdefault('rule_schema', {})
    if not isinstance(schemas, dict):
        sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
    for kind, keys in sheets.RULE_KEYS.items():
        rows = project['rules'].setdefault(kind, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
        if kind not in schemas:
            names = list(dict.fromkeys([*keys, *(k for row in rows for k in row if k != 'id')]))
            if kind != 'replenish':
                names.extend(k for k in ('T0', 'T1', 'T2', 'T3', 'T4') if k not in names)
            schemas[kind] = [{'name':name, 'type':'text' if name in keys else 'number',
                              'key':name in keys} for name in names]
        schema = schemas[kind]
        if not isinstance(schema, list):
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
        names = set()
        for column in schema:
            if (not isinstance(column, dict) or not isinstance(column.get('name'), str)
                    or not column['name'].strip() or column['name'] in names | RULE_RESERVED
                    or column.get('type') not in ('text', 'number')
                    or not isinstance(column.get('key'), bool)
                    or column['type'] != ('text' if column['key'] else 'number')):
                sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
            names.add(column['name'])
        # Preserve endpoint columns supplied by old projects and import adapters.
        for row in rows:
            for name in row:
                if name in names or name == 'id':
                    continue
                if name in RULE_RESERVED:
                    sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
                schema.append({'name':name, 'type':'text' if name in keys else 'number',
                               'key':name in keys})
                names.add(name)
        seen = set()
        for index, row in enumerate(rows):
            if set(row) - names - {'id'}:
                sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
            if 'id' not in row:
                seed = kind + ':' + str(index) + ':' + sheets.revision(row)
                row['id'] = 'rule-' + uuid.uuid5(uuid.NAMESPACE_URL, seed).hex
            if not isinstance(row['id'], str) or not row['id'] or row['id'] in seen:
                sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
            seen.add(row['id'])
    return project


def rule_kind(view):
    if isinstance(view, str) and view.startswith('rules:'):
        kind = view[6:]
        if kind not in sheets.RULE_KEYS:
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
        return kind
    return None


def rule_value(column, value):
    # Clearing a rule cell is distinct from entering explicit zero.
    if value is None or isinstance(value, str) and not value.strip():
        return ''
    if column['type'] == 'number':
        if isinstance(value, bool):
            sheets.fail(_i18n.msg('eng.sheets.expected_a_finite_number', 'expected a finite number'))
        return number(value)
    if isinstance(value, (dict, list, bool)) or any(c in str(value) for c in '\r\n'):
        sheets.fail(_i18n.msg('eng.sheets.expected_a_single_text_value', 'expected a single text value'))
    return str(value).strip()


def rule_records(project, kind):
    schema = project['rule_schema'][kind]
    columns = {column['name']:column for column in schema}
    rows = []
    groups = {}
    issues = []
    keys = [column['name'] for column in schema if column['key']]
    for source in project['rules'][kind]:
        row = {'id':source['id'], 'invalid_columns':[]}
        for name, column in columns.items():
            try:
                row[name] = rule_value(column, source.get(name, ''))
            except sheets.SheetError:
                row[name] = source.get(name)
                row['invalid_columns'].append(name)
                issues.append({'code':'invalid_rule_value', 'ids':[row['id']],
                    'message':_i18n.msg('sheets.rule_invalid_value', 'Invalid rule value: {column} ({id})',
                                        column=name, id=row['id'])})
        key = tuple(str(row.get(name, '')).strip() for name in keys)
        if not keys or not all(key):
            issues.append({'code':'missing_rule_key', 'ids':[row['id']],
                'message':_i18n.msg('sheets.rule_missing_key', 'Incomplete rule key: {id}', id=row['id'])})
        else:
            groups.setdefault(key, []).append(row)
        rows.append(row)
    for key, members in groups.items():
        values = {repr(tuple(row[name] for name in columns if name not in keys)) for row in members}
        if len(members) > 1:
            code = 'conflicting_duplicate_rule_key' if len(values) > 1 else 'duplicate_rule_key'
            message = (_i18n.msg('sheets.rule_conflicting_key', 'Conflicting duplicate rule key: {key}',
                                 key=', '.join(key)) if len(values) > 1 else
                       _i18n.msg('sheets.rule_duplicate_key', 'Duplicate rule key: {key}', key=', '.join(key)))
            issues.append({'code':code, 'ids':[row['id'] for row in members], 'message':message})
    info = {'id':{'type':'text', 'readonly':True}}
    info.update({name:{'type':column['type'], 'readonly':False} for name,column in columns.items()})
    return rows, info, ['id', *keys], issues


def stage_rule_cells(project, kind, cells):
    if not isinstance(cells, list):
        sheets.fail(_i18n.msg('eng.sheets.invalid_rule_table', 'invalid rule table'))
    p = copy.deepcopy(project)
    columns = {column['name']:column for column in p['rule_schema'][kind]}
    rows = {row['id']:row for row in p['rules'][kind]}
    changes = []
    for cell in cells:
        if not isinstance(cell, dict):
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
        uid, name = cell.get('id'), cell.get('column')
        if not isinstance(uid, str) or not isinstance(name, str) or uid not in rows or name not in columns:
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
        value = rule_value(columns[name], cell.get('value'))
        changes.append({'id':uid, 'column':name, 'before':rows[uid].get(name, ''), 'after':value})
        rows[uid][name] = value
    return p, changes


def stage_rule_operation(project, kind, ids, column, operation, value=None):
    rows, _, _, _ = rule_records(project, kind)
    live = {row['id']:row for row in rows}
    if not isinstance(ids, list) or not ids or any(not isinstance(uid, str) or uid not in live for uid in ids):
        sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
    cells = []
    for uid in ids:
        new = value
        if operation == 'clear':
            new = ''
        elif operation == 'copy':
            if not isinstance(value, str) or value not in live[uid] or value in RULE_RESERVED:
                sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
            new = live[uid][value]
        elif operation != 'set':
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_operation', 'Unsupported rule operation'))
        cells.append({'id':uid, 'column':column, 'value':new})
    return stage_rule_cells(project, kind, cells)


def rule_structure(project, kind, body):
    import uuid
    p = copy.deepcopy(project)
    schema = p['rule_schema'][kind]
    rows = p['rules'][kind]
    operation = body.get('operation')
    name = str(body.get('column', '')).strip()
    columns = {column['name']:column for column in schema}
    if operation == 'add_row':
        rows.append({'id':'rule-' + uuid.uuid4().hex, **{name:'' for name in columns}})
    elif operation == 'remove_rows':
        ids = body.get('ids')
        if not isinstance(ids, list) or any(not isinstance(uid, str) or uid not in {row['id'] for row in rows} for uid in ids):
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
        p['rules'][kind] = [row for row in rows if row['id'] not in ids]
    elif operation in ('add_column', 'rename_column', 'remove_column'):
        target = str(body.get('name', '')).strip() if operation == 'rename_column' else name
        if operation != 'remove_column' and (not target or target in columns or target in RULE_RESERVED
                                                or any(c in target for c in '\r\n')):
            sheets.fail(_i18n.msg('eng.sheets.invalid_rule_column', 'Column name is blank, reserved or already exists'))
        if operation == 'add_column':
            key = body.get('key', False) is True
            schema.append({'name':name, 'type':'text' if key else 'number', 'key':key})
            for row in rows:
                row[name] = ''
        else:
            if name not in columns:
                sheets.fail(_i18n.msg('eng.sheets.invalid_rule_target', 'Unknown rule row or column'))
            if operation == 'rename_column':
                columns[name]['name'] = target
                for row in rows:
                    row[target] = row.pop(name, '')
            else:
                schema.remove(columns[name])
                for row in rows:
                    row.pop(name, None)
    else:
        sheets.fail(_i18n.msg('eng.sheets.invalid_rule_operation', 'Unsupported rule operation'))
    return p
