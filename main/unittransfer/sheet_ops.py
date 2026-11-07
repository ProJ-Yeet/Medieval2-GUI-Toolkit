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
            n=float(text)
            return int(n) if kind=='int' and n.is_integer() else n if math.isfinite(n) else None
        except ValueError:return None
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
        row['invalid_columns']=[column for column,definition in FIELDS.items()
            if definition[2] in ('int','number') and definition[0] in fields
            and (row[column] is None or definition[2]=='int' and not float(row[column]).is_integer())]
        row['Category override']=project['units'].get(uid,{}).get('category_override','')
        row['Category']=row['Category override'] or row.get('category')
        row['changed']=bool(draft)
        row['stale_draft']=stale
        a,d,shield=row.get('armor'),row.get('defense'),row.get('shield')
        row['defense_total']=a+d+shield if None not in (a,d,shield) else None
        size=row.get('unit_size');row['ultra_size']=size*number(project['comparison'].get('ultra_size',2.5)) if size is not None else None
        atk=row.get('attack');weight=number(project['comparison'].get('defense_weight',.8))
        denom=atk+a+weight*d+shield if None not in (atk,a,d,shield) else None
        for name,col in [('cost_efficiency','recruit_cost'),('upkeep_efficiency','upkeep')]:
            row[name]=row[col]/denom if row.get(col) is not None and denom not in (None,0) else None
        for k,v in source['extra'].items():row['extra:'+k]=v
        rows.append(row)
    extras={key for row in rows for key in row if key.startswith('extra:')}
    for row in rows:
        for key in extras:row.setdefault(key,None)
    return rows,snapshot


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
    if op=='missing':return value is None
    if op=='blank':return value is None or value=='' or value==[]
    if op=='invalid':
        if 'invalid_columns' in row:return key in row['invalid_columns']
        if key in FIELDS and FIELDS[key][2] in ('int','number'):
            return value is None
        return value is None
    if op in ('gt','ge','lt','le'):
        if value is None or value=='':return False
        a,b=number(value),number(want)
        return {'gt':a>b,'ge':a>=b,'lt':a<b,'le':a<=b}[op]
    if isinstance(value,list):hit=str(want).casefold() in {str(x).casefold() for x in value}
    else:hit=str(want if want is not None else '').casefold() in str(value if value is not None else '').casefold()
    if op in ('contains','not_contains'):return hit if op=='contains' else not hit
    if op in ('eq','ne'):
        same=value==want if isinstance(value,(int,float,bool)) else str(value or '').casefold()==str(want or '').casefold()
        if isinstance(value,(int,float)) and isinstance(want,str):
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
    if any(uid not in live for uid in ids):sheets.fail(_i18n.msg('eng.sheets.selected_units_changed_refresh_before_editing','selected units changed; refresh before editing'))
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
        changes.append({'id':uid,'column':column,'before':before[uid].get(column),'after':value})
    for uid in {c['id'] for c in cells}:
        field_changes(units[uid],p['draft'].get(uid,{}))
    return p,changes
