"""Parser-backed, read-only EDB balance previews with complete per-stage outcomes.

Only numeric token spans of parser-identified recruit_pool lines are replaced.
The original document, conditions, spacing, comments and bytes otherwise survive.
"""
from __future__ import annotations
from . import i18n as _i18n
from collections import Counter, deque
import hashlib
import json
import math
import re
from pathlib import Path
from . import buildings, unit_sheets as sheets

STAGES=('replenish','experience','pool')
PROFILE={'city_multiplier':.9,'cavalry_multiplier':.8,'branch_policy':'shortest',
         'fractional_pool_exception':True,'barracks_cap':5}
# Read-only compatibility rules, separate from editable profile/recipe keys.
# Per-level settlement is the user's approved exception to the legacy chain header.
PROFILE_RULES={'settlement_policy':'per_level_header','unspecified_city_multiplier':1,
               'beast_replenish_tier':'Beast','beast_cavalry_policy':'native_category',
               'malformed_beast_policy':'report','missing_endpoint_policy':'use_other_endpoint',
               'single_level_policy':'earliest','rounding_digits':6,'rounding_mode':'python_round',
               'shortest_policy':'minimum_root_distance',
               'reject_ambiguous_policy':'reject_unequal_merge_distances',
               'disconnected_policy':'root_zero_shared_chain_maximum',
               'invalid_graph_policy':'preserve_and_report'}
# This lexer locates token spans inside a line already owned by the EDB parser.
# It does not discover buildings/levels/conditions or replace the format parser.
TOKENS=re.compile(r'^\s*recruit_pool\s+(?:"[^"\r\n]*"|[^\s"]+)(?P<nums>(?:[ \t]+[^\s;]+){4})')


class RuleSkip(ValueError):pass


def finite(value):
    try:
        n=float(value)
        if not math.isfinite(n):raise ValueError()
        return n
    except (ValueError,TypeError):raise RuleSkip('invalid_number')


def graph(chain,policy='shortest'):
    """Legacy shortest-root depth, with explicit diagnostics instead of tier 0 fallbacks."""
    names=[b.name for b in chain.blocks];have=set(names)
    edges={b.name:[buildings.upgrade_name(x) for x in b.upgrades] for b in chain.blocks}
    errors=[];notes=[]
    if len(have)!=len(names):errors.append('duplicate_level')
    if set(chain.levels)!=have:errors.append('declared_level_mismatch')
    if any(x not in have for children in edges.values() for x in children):errors.append('unknown_upgrade')
    parents={n:[] for n in names}
    for parent,children in edges.items():
        for child in children:
            if child in parents:parents[child].append(parent)
    roots=[n for n in names if not parents[n]]
    indegree={n:len(parents[n]) for n in names};queue=deque(roots);order=[]
    while queue:
        node=queue.popleft();order.append(node)
        for child in edges[node]:
            if child in indegree:
                indegree[child]-=1
                if indegree[child]==0:queue.append(child)
    if len(order)!=len(names):errors.append('cycle')
    depths={r:0 for r in roots}
    for node in order:
        if parents[node]:
            options=[depths[x]+1 for x in parents[node] if x in depths]
            if options:
                depths[node]=min(options)
                if len(set(options))>1:
                    notes.append('unequal_merge:'+node)
                    if policy=='reject_ambiguous':errors.append('ambiguous_depth')
    if len(roots)>1:notes.append('multiple_roots')
    if any(len(x)>1 for x in edges.values()):notes.append('branched')
    return {'building':chain.name,'roots':roots,'edges':edges,'depths':depths,
            'max_depth':max(depths.values(),default=0),'errors':sorted(set(errors)),
            'notes':notes,'policy':policy,'disconnected_policy':'each root starts at 0; shared chain maximum'}


def recruitments(edb):
    rows=[]
    for chain in edb.buildings:
        for level in chain.blocks:
            for section,caps in [('capability',level.capabilities),('faction_capability',level.faction_capabilities)]:
                for cap in caps:
                    if cap.keyword!='recruit_pool':continue
                    pool=cap.pool()
                    rows.append({'id':str(cap.line+1),'unit':pool.unit if pool else '',
                      'building':chain.name,'level':level.name,'settlement':level.settlement or 'unspecified',
                      'section':section,'requires':cap.requires,'line':cap.line+1,
                      'initial':pool.initial if pool else None,'per_turn':pool.per_turn if pool else None,
                      'maximum':pool.maximum if pool else None,'experience':pool.experience if pool else None})
    return rows


def profile_of(project):
    p={**PROFILE,**project.get('balance_profile',{})}
    if p['branch_policy'] not in ('shortest','reject_ambiguous'):sheets.fail(_i18n.msg('eng.sheets.unknown_branch_policy','unknown branch policy'))
    for key in ('city_multiplier','cavalry_multiplier'):
        try:p[key]=finite(p[key])
        except RuleSkip:sheets.fail(_i18n.msg('eng.sheets.invalid_multiplier_value1','invalid multiplier: {value1}',value1=key))
        if p[key]<=0:sheets.fail(_i18n.msg('eng.sheets.multipliers_must_be_positive','multipliers must be positive'))
    if p['barracks_cap']!=5:sheets.fail(_i18n.msg('eng.sheets.this_compatibility_profile_caps_barracks_at_t5','this compatibility profile caps barracks at T5'))
    return p


def classification(unit,project):
    meta=project['units'].get(unit.type,{});a=meta.get('annotations',{})
    race=str(a.get('Unit Race','')).strip();tier=str(a.get('Tier','')).strip()
    category=meta.get('category_override') or sheets.fields_of(unit).get('category','')
    if not race:raise RuleSkip('missing_race')
    if not tier:raise RuleSkip('missing_tier')
    beast=race.casefold().startswith('beast')
    if beast:
        parts=race.split(maxsplit=1)
        if len(parts)!=2 or parts[0].casefold()!='beast' or not parts[1].strip():raise RuleSkip('malformed_beast')
        race=parts[1].strip();category='beast'
    return race,tier,category,beast


def lookup_index(project):
    indices={}
    for stage in STAGES:
        rows=project['rules'][stage];sheets.validate_rules(stage,rows)
        indices[stage]={tuple(str(r.get(k,'')).strip() for k in sheets.RULE_KEYS[stage]):r for r in rows}
    return indices


def overrides(project,stage,row,explain=None):
    candidates=[]
    for i,rule in enumerate(project.get('balance_overrides',[])):
        if not isinstance(rule,dict) or rule.get('stage') not in STAGES:sheets.fail(_i18n.msg('eng.sheets.invalid_balance_override','invalid balance override'))
        keys=[k for k in ('unit','building','level') if rule.get(k)]
        if not keys:sheets.fail(_i18n.msg('eng.sheets.override_must_select_a_unit_building_or_level','override must select a unit, building or level'))
        if rule['stage']==stage and all(rule[k]==row[k] for k in keys):candidates.append((len(keys),i,rule['value']))
    if explain is not None:
        explain['override_candidates']=[{'selector':{k:project['balance_overrides'][i][k]
            for k in ('unit','building','level') if project['balance_overrides'][i].get(k)},'value':v}
            for _,i,v in candidates]
    if not candidates:return None
    top=max(n for n,_,_ in candidates);values=[v for n,_,v in candidates if n==top]
    if len(values)>1:raise RuleSkip('conflicting_overrides')
    if explain is not None:
        chosen=next(i for n,i,_ in candidates if n==top)
        rule=project['balance_overrides'][chosen]
        explain.update(override=True,override_input=values[0],
                       override_selector={k:rule[k] for k in ('unit','building','level') if rule.get(k)})
    return values[0]


def explanation_inputs(row,unit,project,structure,profile):
    meta=project['units'].get(row['unit'],{})
    native_category=(meta.get('category_override') or sheets.fields_of(unit).get('category','')) if unit else None
    return {'inputs':{**row,'annotations':dict(meta.get('annotations',{})),
                      'category_override':meta.get('category_override')},
            'depth':None if structure['errors'] else structure['depths'].get(row['level']),
            'max_depth':structure['max_depth'],'graph_errors':list(structure['errors']),
            'graph_notes':list(structure['notes']),'branch_policy':profile['branch_policy'],
            'settlement':row['settlement'],'settlement_policy':PROFILE_RULES['settlement_policy'],
            'native_category':native_category,
            'city_multiplier':profile['city_multiplier'] if row['settlement']=='city' else 1,
            'cavalry_multiplier':profile['cavalry_multiplier'] if native_category=='cavalry' else 1,
            'fractional_pool_exception':profile['fractional_pool_exception'],'rounding_steps':[]}


def lookup_inputs(row,unit,project,profile,index,explain):
    """Record the candidate cell before any skip or override short-circuits lookup."""
    meta=project['units'].get(row['unit'],{});a=meta.get('annotations',{})
    race=str(a.get('Unit Race','')).strip();tier=str(a.get('Tier','')).strip()
    category=explain['native_category']
    parts=race.split(maxsplit=1)
    if len(parts)==2 and parts[0].casefold()=='beast':race=parts[1].strip();category='beast'
    depth=explain['depth'];barracks='T'+str(min(depth+1,profile['barracks_cap'])) if depth is not None else None
    key=(race,category,barracks);rule=index.get(key)
    explain.update(race=race,tier=tier,category=category,barracks_tier=barracks,rule_key=key,
                   lookup_column=tier,lookup_row_found=rule is not None,
                   lookup_value=rule.get(tier) if rule is not None else None,override=False)


def calculate(stage,row,unit,project,structure,profile,index,explain=None):
    # Mutate the entry's audit context so skipped/invalid outcomes keep known inputs.
    if explain is None:explain=explanation_inputs(row,unit,project,structure,profile)
    # An explicit override outranks classification/graph/table rules, including skips.
    if stage in ('experience','pool') and 'lookup_column' not in explain:
        lookup_inputs(row,unit,project,profile,index,explain)
    override=overrides(project,stage,row,explain)
    if override is not None:
        explain.update(override=True,override_input=override)
        value=finite(override)
    else:
        if structure['errors']:raise RuleSkip('invalid_building_graph:'+','.join(structure['errors']))
        if row['level'] not in structure['depths']:raise RuleSkip('unknown_level_depth')
        if stage in ('pool','replenish') and profile['fractional_pool_exception'] and finite(row['maximum'])<1:
            raise RuleSkip('fractional_pool_preserved')
        if unit is None:raise RuleSkip('unit_not_in_edu')
        race,tier,category,beast=classification(unit,project)
        depth=structure['depths'][row['level']];maximum=structure['max_depth']
        explain.update(race=race,tier=tier,category=category,depth=depth,max_depth=maximum)
        if stage=='replenish':
            key=('Beast' if beast else tier,);rule=index.get(key)
            explain.update(rule_key=key)
            if rule is None:raise RuleSkip('missing_replenish_tier:'+key[0])
            e=rule.get(race+'_Earliest',rule.get(race+' Earliest'));l=rule.get(race+'_Latest',rule.get(race+' Latest'))
            explain.update(endpoint_inputs={'earliest':e,'latest':l},endpoint_fallback=None)
            missing=lambda x:x is None or str(x).strip().upper() in ('','N/A','MISSING')
            if missing(e) and not missing(l):e=l;explain['endpoint_fallback']='earliest_from_latest'
            if missing(l) and not missing(e):l=e;explain['endpoint_fallback']='latest_from_earliest'
            if missing(e) or missing(l):raise RuleSkip('missing_replenish_endpoints:'+race)
            e,l=finite(e),finite(l)
            if e<=0 or l<=0:raise RuleSkip('nonpositive_replenish_interval')
            interval=e+(l-e)*depth/maximum if maximum else e
            reciprocal=round(1/interval,6)
            city=profile['city_multiplier'] if row['settlement']=='city' else 1
            # Replenishment uses the original EDU category even for Beast races;
            # only experience/pool table lookup maps that category to "beast".
            native_category=project['units'].get(unit.type,{}).get('category_override') or sheets.fields_of(unit).get('category','')
            cavalry=profile['cavalry_multiplier'] if native_category=='cavalry' else 1
            after_city=reciprocal*city;after_cavalry=after_city*cavalry
            value=round(after_cavalry,6)
            explain.update(earliest=e,latest=l,interval=interval,reciprocal=reciprocal,
                           city_multiplier=city,cavalry_multiplier=cavalry,native_category=native_category,rounding='reciprocal 6, multipliers, result 6',
                           rounding_steps=[{'operation':'reciprocal','input':1/interval,'digits':6,'output':reciprocal},
                                           {'operation':'city_multiplier','input':reciprocal,'multiplier':city,'output':after_city},
                                           {'operation':'cavalry_multiplier','input':after_city,'multiplier':cavalry,'output':after_cavalry},
                                           {'operation':'result','input':after_cavalry,'digits':6,'output':value}])
        else:
            if tier not in ('T0','T1','T2','T3','T4'):raise RuleSkip('unsupported_unit_tier:'+tier)
            barracks='T'+str(min(depth+1,profile['barracks_cap']))
            key=(race,category,barracks);rule=index.get(key)
            # Categories are supported by this project's table, not a global list.
            if index and not any(k[1]==category for k in index):raise RuleSkip('unsupported_unit_category:'+category)
            if rule is None:raise RuleSkip('missing_lookup_row:'+repr(key))
            if tier not in rule or str(rule[tier]).strip().upper() in ('','N/A','MISSING'):raise RuleSkip('missing_lookup_value:'+tier)
            value=finite(rule[tier]);explain.update(barracks_tier=barracks,rule_key=key)
    if value<0:raise RuleSkip('negative_result')
    if stage=='experience' and (not value.is_integer() or value>9):raise RuleSkip('experience_requires_integer_0_to_9')
    return value,explain


def run(mod,project,stages=None,edb=None):
    """Pure preview. All stages consume one staged document, in explicit order."""
    stages=STAGES if stages is None else stages
    if not isinstance(stages,(list,tuple)) or not stages or len(set(stages))!=len(stages) or any(s not in STAGES for s in stages):sheets.fail(_i18n.msg('eng.sheets.invalid_balance_stages','invalid balance stages'))
    profile=profile_of(project);edb=edb or mod.edb;units=sheets.live_units(mod);indices=lookup_index(project)
    structures=[graph(chain,profile['branch_policy']) for chain in edb.buildings]
    by_name={s['building']:s for s in structures}
    duplicates={k for k,v in Counter(s['building'] for s in structures).items() if v>1}
    for name in duplicates:by_name[name]['errors'].append('duplicate_building')
    lines=list(edb.lines);rows=recruitments(edb);logs={};exports={};total=0
    for stage in stages:
        entries=[]
        for original in rows:
            row=dict(original);line_index=row['line']-1;raw=lines[line_index]
            structure=by_name[row['building']];unit=units.get(row['unit'])
            explanation=explanation_inputs(row,unit,project,structure,profile)
            if stage in ('experience','pool'):lookup_inputs(row,unit,project,profile,indices[stage],explanation)
            explanation['inputs']['raw_line']=raw
            entry={**row,'stage':stage,'status':'skipped','reason':'','before':None,'after':None,'explanation':explanation}
            match=TOKENS.match(raw)
            if match is None:
                entry.update(status='invalid',reason='malformed_recruit_pool');explanation['outcome']='malformed_recruit_pool';entries.append(entry);continue
            spans=list(re.finditer(r'\S+',match.group('nums')))
            numbers=[m.group() for m in spans]
            for field,val in zip(('initial','per_turn','maximum','experience'),numbers):row[field]=val
            explanation['inputs'].update({field:row[field] for field in ('initial','per_turn','maximum','experience')})
            field={'replenish':'per_turn','experience':'experience','pool':'maximum'}[stage]
            slot={'per_turn':1,'maximum':2,'experience':3}[field];entry['before']=numbers[slot]
            try:
                # Missing original values may never be invented by RecruitPool.parse padding.
                if any(x in ('requires','{','}') for x in numbers):raise RuleSkip('malformed_recruit_pool')
                for n in numbers:finite(n)
                value,explanation=calculate(stage,row,unit,project,structure,profile,indices[stage],explanation)
                text=str(int(value)) if value.is_integer() else format(value,'.12g')
                changed=finite(numbers[slot])!=value
                if changed:
                    token=spans[slot];start=match.start('nums')+token.start();end=match.start('nums')+token.end()
                    lines[line_index]=raw[:start]+text+raw[end:];total+=1
                entry.update(status='changed' if changed else 'unchanged',after=text,explanation=explanation)
            except RuleSkip as e:
                reason=str(e);entry.update(reason=reason,after=entry['before'],status='invalid' if reason.startswith(('invalid_','negative_','nonpositive_','experience_','malformed_','conflicting_')) else 'skipped')
            explanation['outcome']=entry['reason'] or entry['status']
            entries.append(entry)
        counts=dict(Counter(e['status'] for e in entries));logs[stage]={'counts':counts,'all':entries,'issues':[e for e in entries if e['status'] in ('invalid','skipped')]}
        exports[stage]=''.join(lines)
    return {'profile':profile,'profile_rules':dict(PROFILE_RULES),'structure':structures,'logs':logs,'exports':exports,'text':''.join(lines),
            'source_token':hashlib.sha256(edb.to_text().encode('latin-1')).hexdigest(),
            'changed_fields':total,'recruitment_rows':len(rows),'stages':list(stages)}


def fresh_edb(mod):
    path=getattr(mod,'edb_path',None)
    if path is not None and Path(path).is_file():
        # read_text's universal newlines would destroy an original CRLF document.
        return buildings.parse_text(Path(path).read_bytes().decode(buildings.ENCODING))
    return mod.edb


def preview(mod,project,stages=None):
    if project.get('draft'):sheets.fail(_i18n.msg('eng.sheets.apply_or_discard_native_unit_drafts_before_balancing_the_edb','Apply or discard native unit drafts before balancing the EDB; rules use the saved game roster'))
    result=run(mod,project,stages,fresh_edb(mod))
    inputs={'project':sheets.revision(project),'edu':sheets.source_token(mod),
            'edb':result['source_token'],'stages':result['stages'],'text':result['text']}
    result['plan_token']=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    return result


def apply_preview(mod,project,stages,token):
    # Fresh Mod avoids the registry's short revalidation cache for the EDU/EOP join.
    from .mod import Mod
    fresh=Mod(mod.root);result=preview(fresh,project,stages)
    if not token or token!=result['plan_token']:sheets.fail(_i18n.msg('eng.sheets.preview_changed_refresh_and_review_the_edb_changes_before_applying','Preview changed; refresh and review the EDB changes before applying'))
    if not result['changed_fields']:sheets.fail(_i18n.msg('eng.sheets.there_are_no_edb_changes_to_apply','There are no EDB changes to apply'))
    path=fresh.edb_path
    if not path.is_file():sheets.fail(_i18n.msg('eng.sheets.extract_the_edb_into_the_mod_before_applying_balance_changes','Extract the EDB into the mod before applying balance changes'))
    original=path.read_bytes()
    if hashlib.sha256(original).hexdigest()!=result['source_token']:sheets.fail(_i18n.msg('eng.sheets.the_edb_changed_after_preview','The EDB changed after preview'))
    notes=[f"{stage}: {entry['unit']} at {entry['building']}/{entry['level']} line {entry['line']}: {entry['before']} -> {entry['after']}"
           for stage in result['stages'] for entry in result['logs'][stage]['all'] if entry['status']=='changed']
    plan=buildings.BuildingPlan(mod=fresh,line='EDB balance',edb_text=result['text'],changes=notes,atomic_edb=True)
    try:return buildings.apply_edit(plan)
    except Exception:
        # Existing log/backup machinery still owns the operation. A failed log
        # write must not leave an apparently unapplied EDB edit behind.
        if path.read_bytes()!=original:buildings._atomic_edb_write(path,original)
        raise
