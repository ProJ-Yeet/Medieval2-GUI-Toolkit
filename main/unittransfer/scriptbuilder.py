"""Describe, validate and compile campaign recipes into Squirrel modules.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass

from . import i18n as _i18n, scriptwords, scriptcompat as SC, scriptdocs as SD


@dataclass
class Event:
    key: str
    engine: str
    label: str
    subjects: tuple
    help: str = ''


@dataclass
class Block:
    key: str
    label: str
    needs: tuple
    fields: tuple
    help: str = ''


EVENTS = [Event(*row) for row in [
    ('player_turn', 'FactionTurnStart', 'your faction starts its turn', ('faction',)),
    ('faction_turn', 'FactionTurnStart', 'a faction starts its turn', ('faction',)),
    ('town_turn', 'SettlementTurnStart', 'a town starts its turn', ('faction', 'settlement')),
    ('town_taken', 'GeneralCaptureSettlement', 'a general takes a town', ('faction', 'settlement', 'character', 'target')),
    ('building_done', 'BuildingCompleted', 'a building finishes', ('faction', 'settlement')),
    ('unit_trained', 'UnitTrained', 'a unit finishes training', ('faction', 'settlement', 'unit')),
    ('battle_over', 'PostBattle', 'a battle ends', ('faction', 'character')),
    ('town_riots', 'CityRiots', 'a town riots', ('faction', 'settlement')),
    ('town_rebels', 'CityRebels', 'a town rebels', ('faction', 'settlement')),
    ('town_grows', 'SettlementUpgraded', 'a town advances in size', ('faction', 'settlement')),
    ('faction_destroyed', 'FactionDestroyed', 'a faction is destroyed', ('faction',)),
    ('new_leader', 'BecomesFactionLeader', 'a character becomes leader', ('faction', 'character')),
    ('comes_of_age', 'CharacterComesOfAge', 'a character reaches adulthood', ('faction', 'character')),
    ('new_round', 'turnChanged', 'a new round begins', ()),
    ('character_died', 'characterDied', 'a character dies', ('faction', 'character')),
    ('faction_died', 'factionDied', 'a faction is about to disappear', ('faction',)),
    ('new_campaign', 'newGameLoaded', 'a fresh campaign opens', ()),
]]
for _event in EVENTS:
    _event.help = 'run the rule when ' + _event.label


def F(name, kind, default, label=''):
    return (name, kind, label or {'op':'comparison','v':'value','to':'recipient','a':'first faction','faction':'faction identifier','faction_b':'other faction identifier','anc':'ancillary identifier','text':'text'}.get(name,name), default)


CONDITIONS = [
    Block('who', 'faction control', ('faction',), (F('v','who','player'), F('names','names:factions',[],'chosen factions'))),
    Block('money', 'treasury test', ('faction',), (F('op','op','<'), F('v','signed',0,'treasury amount'))),
    Block('towns', 'town count', ('faction',), (F('op','op','<'), F('v','int',3,'number of towns'))),
    Block('turn', 'campaign turn', (), (F('op','turn_op','>='), F('v','int',10,'turn number'))),
    Block('chance', 'random chance', (), (F('v','percent',10,'chance in percent'),)),
    Block('people', 'population test', ('settlement',), (F('op','op','>'), F('v','int',24000,'population number'))),
    Block('town_is', 'selected towns', ('settlement',), (F('names','names:towns',[],'chosen towns'),)),
    Block('capital', 'capital town', ('settlement','faction'), ()),
    Block('has_chain', 'building chain present', ('settlement',), (F('v','name:chains','','building chain'),)),
    Block('old_owner', 'previous owner control', ('target',), (F('v','who','computer'), F('names','names:factions',[],'chosen factions'))),
    Block('counter', 'counter test', (), (F('name','counter','my_count','counter identifier'), F('op','op','>='), F('v','signed',1))),
    Block('game', 'engine condition', (), (F('line','cond','','condition line'),)),
]
ACTIONS = [
    Block('money', 'change treasury', (), (F('amount','signed',1000,'money change'), F('to','to','this','recipient'), F('faction','name:factions',''))),
    Block('people', 'change population', ('settlement',), (F('amount','signed',1000,'population change'),)),
    Block('people_pct', 'reduce population by percent', ('settlement',), (F('pct','percent',10,'percent removed'),)),
    Block('people_max', 'limit population', ('settlement',), (F('max','int',6000,'population ceiling'),)),
    Block('build', 'add a building', ('settlement',), (F('level','name:levels','','building level'),)),
    Block('tear_down', 'remove a building chain', ('settlement',), (F('chain','name:chains','','chain to remove'),)),
    Block('units', 'add garrison units', ('settlement',), (F('unit','name:units','','unit type'), F('count','int',1,'units to add'))),
    Block('give_town', 'transfer a town', ('settlement',), (F('to','to','rebels'), F('faction','name:factions',''))),
    Block('stance', 'set diplomatic relations', (), (F('a','to','this'), F('faction','name:factions',''), F('b','to','player','other faction'), F('faction_b','name:factions',''), F('stance','stance','war','relationship'))),
    Block('trait', 'grant a trait', ('character',), (F('trait','name:traits','','trait identifier'), F('level','int',1,'trait level'))),
    Block('ancillary', 'grant an ancillary', ('character',), (F('anc','name:ancillaries',''),)),
    Block('counter_set', 'assign a counter', (), (F('v','signed',0), F('name','counter','my_count','counter identifier'))),
    Block('counter_add', 'adjust a counter', (), (F('v','signed',1), F('name','counter','my_count','counter identifier'))),
    Block('message', 'show an event scroll', (), (F('title','text','','scroll heading'), F('body','long','','scroll text'))),
    Block('log', 'write to the game log', (), (F('text','text',''),)),
    Block('console', 'run a console command', (), (F('text','cmd:console','','command line'),)),
    Block('script', 'run a campaign command', (), (F('text','cmd:commands','','command line'),)),
]
CONDITION_HELP = {'who': 'test whether the event faction is human controlled, computer controlled or one of the chosen factions', 'money': 'compare the event faction treasury with the chosen amount', 'towns': 'compare the number of settlements owned by the event faction', 'turn': 'test the campaign turn, counting the opening turn as one', 'chance': 'roll a fresh percentage chance each time the rule is evaluated', 'people': 'compare the event town population with the chosen number', 'town_is': 'restrict the rule to the chosen campaign settlements', 'capital': 'check whether the event town is its faction capital', 'has_chain': 'check whether the event town contains any level of the chosen building chain', 'old_owner': 'test who controlled the town before its capture', 'counter': 'compare a saved engine event counter with the chosen value', 'game': 'ask the engine to evaluate a campaign-script condition with the event data'}
ACTION_HELP = dict([('money', 'add money to the chosen faction treasury, or subtract it with a negative amount'), ('people', 'add residents to the event town, or remove them with a negative amount'), ('people_pct', 'remove the chosen percentage of the event town population'), ('people_max', 'reduce the event town population only when it exceeds the chosen ceiling'), ('build', 'add the chosen building level to the event town'), ('tear_down', 'remove the chosen building chain from the event town'), ('units', 'create the chosen number of units in the event town garrison'), ('give_town', 'transfer ownership of the event town to the chosen faction'), ('stance', 'set war, peace or alliance between the two chosen factions'), ('trait', 'give the event general the chosen trait at the chosen level'), ('ancillary', 'give the event general the chosen ancillary'), ('counter_set', 'replace the saved engine event counter with the chosen value'), ('counter_add', 'add to the saved engine event counter, or subtract with a negative value'), ('message', 'show a campaign event scroll with the chosen heading and body'), ('log', 'write the chosen text to the game log when this rule runs'), ('console', 'run a console command on the campaign map'), ('script', 'run a campaign-script command using the current event data')])
for _block in CONDITIONS:
    _block.help = CONDITION_HELP[_block.key]
for _block in ACTIONS:
    _block.help = ACTION_HELP[_block.key]


def field_help(block, name, kind):
    specific = {
        ('money', 'amount'): 'money added to the recipient treasury; a negative number spends money',
        ('people', 'amount'): 'residents added to the town; a negative number removes residents',
        ('people_pct', 'pct'): 'percentage of the current town population to remove, from 1 to 100',
        ('people_max', 'max'): 'maximum population to leave in the town; smaller towns stay unchanged',
        ('units', 'count'): 'number of copies of the selected unit to place in the garrison',
        ('trait', 'level'): 'trait level to grant to the event general',
        ('message', 'title'): 'heading displayed at the top of the campaign event scroll',
        ('message', 'body'): 'message displayed inside the campaign event scroll',
        ('log', 'text'): 'line written to the game log; {faction} and {town} insert event names',
        ('counter_set', 'v'): 'new value to store in the engine event counter',
        ('counter_add', 'v'): 'amount added to the engine event counter; negative values subtract',
    }
    if (block.key, name) in specific:
        return specific[block.key, name]
    if kind in ('op', 'turn_op'):
        return 'comparison to apply to the measured value; a multiple of repeats every chosen number of turns' if kind == 'turn_op' else 'comparison between the measured value and the chosen threshold'
    if kind == 'who': return 'choose human control, computer control or an explicit list of factions'
    if kind == 'to': return 'choose which faction receives this action; a chosen faction uses its identifier below'
    if kind == 'counter': return 'engine event counter name; {faction} and {town} create separate counters for each subject'
    if kind == 'cond': return 'complete campaign-script condition accepted by the selected engine'
    if kind.startswith('cmd:'): return 'complete engine command, with its required arguments'
    if kind == 'stance': return 'diplomatic state to establish between the two selected factions'
    if kind.startswith(('name:', 'names:')):
        return {
            'factions': 'faction identifiers used when the faction selector requests an explicit choice',
            'towns': 'campaign region identifiers of the towns allowed to pass this test',
            'chains': 'building chain identifier to find in or remove from the event town',
            'levels': 'building level identifier to construct in the event town',
            'units': 'unit type identifier to create in the event town garrison',
            'traits': 'trait identifier to grant to the event general',
            'ancillaries': 'ancillary identifier to give to the event general',
        }[kind.partition(':')[2]]
    return {
        'money': 'treasury threshold in denarii for Rome or florins for Medieval II',
        'towns': 'settlement-count threshold for the event faction',
        'turn': 'campaign turn to compare, counting the opening turn as one',
        'chance': 'percentage chance that this test succeeds, from 1 to 100',
        'people': 'population threshold for the event town',
        'counter': 'threshold against which to compare the engine event counter',
    }[block.key]


WHO_IS = [('player','human controlled'), ('computer','computer controlled'), ('these','chosen factions')]
TO = [('this','the current faction'), ('old','the former owner'), ('player','the human faction'), ('rebels','the rebels'), ('named','a chosen faction')]
TURN_OPS = [('<','less than'), ('>','greater than'), ('<=','at most'), ('>=','at least'), ('==','equal to'), ('every','a multiple of')]
STANCES = [('war','at war'), ('neutral','at peace'), ('allied','allied')]
MATCH = [('all','all tests pass'), ('any','one test passes'), ('none','no test passes')]
EACH = [('', 'use the event subjects'), ('town','each town'), ('army','each army'), ('faction','each non-rebel faction')]
EACH_OF = [('this','of the current faction'), ('player','of the human faction'), ('named','of a chosen faction')]
EXPOSABLE = {'int','signed','percent','text','long'}
RESERVED = {'sack_settlement', 'raze_settlement', 'avoid_growth', 'recruit_order', 'player_diplomacy', 'upkeep_x2', 'one_recruit_grid'}


def new_recipe(title=''):
    return dict(v=1, title=title or _i18n.msg('eng.scripts.my_module','My module'), game='both', when='player_turn',
                once=False, ifs=[], dos=[], settings={}, match='all', **{'else': [], 'each': '', 'each_of': 'this', 'each_faction': ''})


def key_for(title):
    stem = re.sub('[^a-z0-9]+', '_', title.strip().lower()).strip('_')[:40] or 'my_module'
    return 'm_' + stem if stem[0].isdigit() else stem


def recipe_in(text):
    for m in re.finditer(r'^\ufeff?[ \t]*//[ \t]*@recipe[ \t]+(.*)$', text, re.M):
        try:
            obj = json.loads(m[1])
            if isinstance(obj, dict) and 'when' in obj: return obj
        except ValueError:
            pass
    return None


def _example(title, when, conditions, actions, settings, **extra):
    r = new_recipe(title)
    r.update(when=when, ifs=conditions, dos=actions, settings=settings, **extra)
    return r


EXAMPLES = [
    _example('A modest reserve', 'player_turn', [dict(k='money',op='<',v=500)], [dict(k='money',amount=250,to='this',faction='')], {'ifs.0.v':'reserve threshold','dos.0.amount':'reserve payment'}),
    _example('Crowded streets', 'town_turn', [dict(k='people',op='>',v=18000)], [dict(k='people_pct',pct=5)], {'ifs.0.v':'crowding threshold','dos.0.pct':'departure percent'}),
    _example('A new reign', 'new_leader', [], [dict(k='money',amount=400,to='this',faction=''),dict(k='log',text='A new ruler takes charge of {faction}.')], {'dos.0.amount':'accession grant'}),
    _example('Campaign milestone', 'player_turn', [dict(k='turn',op='==',v=20)], [dict(k='message',title='Twenty turns behind us',body='Consider the roads ahead.')], {'ifs.0.v':'milestone turn'}, once=True),
    _example('Quiet growth', 'town_turn', [dict(k='people',op='<',v=3000)], [dict(k='people',amount=100)], {'ifs.0.v':'small town size','dos.0.amount':'new residents'}),
    _example('Border watch', 'town_taken', [], [dict(k='units',unit='',count=1)], {'dos.0.count':'watch units'}),
    _example('Record the victories', 'battle_over', [], [dict(k='counter_add',v=1,name='victories_{faction}')], {'dos.0.v':'count increment'}),
    _example('A winter allowance', 'player_turn', [dict(k='turn',op='every',v=4)], [dict(k='money',amount=100,to='this',faction='')], {'dos.0.amount':'seasonal payment'}),
    _example('Civic works', 'town_turn', [dict(k='turn',op='==',v=12)], [dict(k='build',level='')], {'ifs.0.v':'construction turn'}),
]


def vocabulary():
    w = scriptwords.word
    result = {'events': [dict(key=e.key, label=w('event',e.key,e.label), help=w('event_help',e.key,e.help), subjects=list(e.subjects)) for e in EVENTS]}
    for key, category, blocks in [('conditions','cond',CONDITIONS), ('actions','act',ACTIONS)]:
        result[key] = [dict(key=b.key,label=w(category,b.key,b.label),help=w(category+'_help',b.key,b.help),needs=list(b.needs),
                            fields=[dict(name=n,kind=k,label=w('field',b.key+'.'+n,lab) if lab else '',default=copy.deepcopy(d),help=w('field_help',category+'.'+b.key+'.'+n,field_help(b,n,k))) for n,k,lab,d in b.fields]) for b in blocks]
    for key, category, pairs in [('who','who',WHO_IS),('to','to',TO),('ops','op',TURN_OPS),('stances','stance',STANCES),('match','match',MATCH),('each','each',EACH),('each_of','each_of',EACH_OF)]:
        result[key] = [[v,w(category,v,lab)] for v,lab in pairs]
    result['examples'] = [dict(title=r['title'],label=w('example',r['title'],r['title'])) for r in EXAMPLES]
    return result


def event_for(recipe, facts):
    name = recipe.get('when','')
    if name.startswith('ev:'):
        row = facts['events'].get(name[3:])
        return Event(name,name[3:],name[3:]+' (an engine event)',tuple(SD.subjects(row[4])) if row else ())
    return next((e for e in EVENTS if e.key == name), None)


def fields_of(recipe):
    for group in ('ifs','dos','else'):
        blocks = CONDITIONS if group == 'ifs' else ACTIONS
        for i, item in enumerate(recipe.get(group,[])):
            block = next((b for b in blocks if b.key == item['k']), None)
            if block:
                for n,k,lab,d in block.fields:
                    yield f'{group}.{i}.{n}', block, n, k, lab, item.get(n,d)


def exposed(recipe):
    return [(path,_i18n.msg('eng.scriptbuilder.exposed_label','{block} - {field}',block=b.label,field=lab) if lab else b.label)
            for path,b,n,k,lab,v in fields_of(recipe) if k in EXPOSABLE]


def validate(mod, recipe):
    problems = []
    title = recipe.get('title','').strip()
    if not title: problems.append(_i18n.msg('eng.scriptbuilder.when_give_this_module_a_title', 'WHEN: give this module a title'))
    if key_for(title) in RESERVED or title.casefold() in {'recruitment order', 'upkeep x 2 (no huge armies)', 'one recruitment grid (medieval ii)'}:
        problems.append(_i18n.msg('eng.scriptbuilder.when_this_title_belongs_to_a_built_in_add_on', 'WHEN: this title belongs to a built-in add-on'))
    facts = SD.catalogue(mod,recipe.get('game','both'))
    event = event_for(recipe,facts)
    subjects, exports = set(), []
    lifecycle = event and event.key in ('new_round','character_died','faction_died','new_campaign')
    if event is None:
        problems.append(_i18n.msg('eng.scriptbuilder.when_choose_a_recognized_event', 'WHEN: choose a recognized event'))
    else:
        row = facts['events'].get(event.engine)
        if not lifecycle and facts['events'] and (row is None or not row[5]):
            problems.append(_i18n.msg('eng.scriptbuilder.when_this_event_is_unavailable_in_the_selected_engine_s', 'WHEN: this event is unavailable in the selected engine(s)'))
        subjects = set(event.subjects) if lifecycle or row is None else SD.subjects(row[4])
        exports = row[4] if row else []
    each = recipe.get('each') or ''
    if each not in dict(EACH): problems.append(_i18n.msg('eng.scriptbuilder.for_each_choose_a_supported_iteration', 'FOR EACH: choose a supported iteration'))
    if each in ('town','army'):
        if recipe.get('each_of','this') == 'this' and 'faction' not in subjects:
            problems.append(_i18n.msg('eng.scriptbuilder.for_each_this_event_supplies_no_faction_to_iterate', 'FOR EACH: this event supplies no faction to iterate'))
        if recipe.get('each_of') == 'named' and not recipe.get('each_faction','').strip():
            problems.append(_i18n.msg('eng.scriptbuilder.for_each_pick_the_faction_to_iterate', 'FOR EACH: pick the faction to iterate'))
    subjects.update({'town': ('settlement','faction'), 'army': ('character','faction'), 'faction': ('faction',)}.get(each,()))
    if (recipe.get('match') or 'all') not in dict(MATCH): problems.append(_i18n.msg('eng.scriptbuilder.if_choose_all_any_or_none', 'IF: choose all, any or none'))
    if not recipe.get('dos'): problems.append(_i18n.msg('eng.scriptbuilder.do_add_at_least_one_action', 'DO: add at least one action'))
    if recipe.get('else') and not recipe.get('ifs'): problems.append(_i18n.msg('eng.scriptbuilder.else_add_an_if_test_so_this_branch_can_run', 'ELSE: add an IF test so this branch can run'))
    sources = SC.names(mod)
    eligible = {p for p,_ in exposed(recipe)}
    for path in recipe.get('settings',{}):
        if path not in eligible: problems.append(_i18n.msg('eng.scriptbuilder.do_exposed_setting_path_does_not_point_to_an_eligible_field', 'DO: exposed setting {path} does not point to an eligible field', path=path))
    for group in ('ifs','dos','else'):
        blocks = CONDITIONS if group == 'ifs' else ACTIONS
        side = {'ifs':'IF','dos':'DO','else':'ELSE'}[group]
        for i,item in enumerate(recipe.get(group,[]),1):
            b = next((b for b in blocks if b.key == item['k']),None)
            def bad(s):
                problems.append(_i18n.msg('eng.scriptbuilder.block_error', '{side} {index} ({block}): {detail}', side=side, index=i, block=b.label if b else item['k'], detail=s))
            if b is None:
                kind = item['k']
                bad(_i18n.msg('eng.scriptbuilder.unknown_condition','unrecognized condition {kind}',kind=kind) if group == 'ifs' else
                    _i18n.msg('eng.scriptbuilder.unknown_action','unrecognized action {kind}',kind=kind))
                continue
            for subject in b.needs:
                if subject not in subjects:
                    bad(_i18n.msg('eng.scriptbuilder.missing_subject', 'the event supplies no {subject}', subject={'settlement':'town','character':'general','target':'former owner'}.get(subject,subject)))
            for n,k,lab,default in b.fields:
                v = item.get(n,default)
                label = lab or n
                if k in ('int','signed','percent'):
                    if type(v) is not int: bad(_i18n.msg('eng.scriptbuilder.whole_number', '{label} must be a whole number', label=label))
                    elif k == 'int' and v < 0: bad(_i18n.msg('eng.scriptbuilder.nonnegative', '{label} must be zero or more', label=label))
                    elif k == 'percent' and not 1 <= v <= 100: bad(_i18n.msg('eng.scriptbuilder.percent_range', '{label} must be from 1 through 100', label=label))
                elif k in ('text','long'):
                    if k == 'text' and not v.strip(): bad(_i18n.msg('eng.scriptbuilder.text_required', '{label} needs some text', label=label))
                elif k == 'counter':
                    plain = str(v).replace('{faction}','').replace('{town}','')
                    if not v or not re.fullmatch(r'[A-Za-z0-9_]*',plain): bad(_i18n.msg('eng.scriptbuilder.counter_names_allow_letters_digits_faction_and_town', 'counter names allow letters, digits, _, {faction} and {town}',faction='{faction}',town='{town}'))
                elif k == 'cond' or k.startswith('cmd:'):
                    category = 'conditions' if k == 'cond' else k.partition(':')[2]
                    error = SD.check_line(v,category,facts,exports,recipe.get('game','both'))
                    if error: bad(error)
                elif k.startswith(('name:','names:')):
                    category = k.partition(':')[2]
                    required = True
                    if category == 'factions':
                        selector = ('b' if n == 'faction_b' else ('a' if b.key == 'stance' else 'to'))
                        required = item.get('v') == 'these' if k.startswith('names:') else item.get(selector) == 'named'
                    picks = v if k.startswith('names:') else [v] if v else []
                    if required and not picks: bad(_i18n.msg('eng.scriptbuilder.pick_required', '{label} needs at least one pick', label=label))
                    available = {x.casefold() for x in sources[category]}
                    if available:
                        wrong = [x for x in picks if x.casefold() not in available]
                        if wrong: bad(_i18n.msg('eng.scriptbuilder.unknown_names', 'not found in this mod: {names}', names=', '.join(wrong)))
                elif k == 'to' and v == 'old' and 'target' not in subjects:
                    bad(_i18n.msg('eng.scriptbuilder.the_event_supplies_no_former_owner', 'the event supplies no former owner'))
    return problems


def phrase(item, condition=False, game='both'):
    k = item.get('k','')
    definitions = CONDITIONS if condition else ACTIONS
    b = next((b for b in definitions if b.key == k),None)
    if b is None:
        return _i18n.msg('eng.scriptbuilder.unknown_block','unknown block {kind}',kind=k)
    v = {n:item.get(n,d) for n,kind,lab,d in b.fields}
    currency = _i18n.msg('eng.scriptbuilder.denarii','denarii') if game == 'rome' else _i18n.msg('eng.scriptbuilder.florins','florins')
    def destination(field='to',name='faction'):
        return {
            'this': lambda: _i18n.msg('eng.scriptbuilder.current_faction','the current faction'),
            'old': lambda: _i18n.msg('eng.scriptbuilder.former_owner','the former owner'),
            'player': lambda: _i18n.msg('eng.scriptbuilder.human_faction','the human faction'),
            'rebels': lambda: _i18n.msg('eng.scriptbuilder.rebels','the rebels'),
            'named': lambda: v.get(name) or _i18n.msg('eng.scriptbuilder.no_faction','(no faction picked)'),
        }.get(v.get(field),lambda: _i18n.msg('eng.scriptbuilder.a_faction','a faction'))()
    def picks():
        return ', '.join(v.get('names',[])) or (_i18n.msg('eng.scriptbuilder.no_town','(no town picked)') if k == 'town_is' else _i18n.msg('eng.scriptbuilder.no_faction','(no faction picked)'))
    def control():
        return {'player': lambda: _i18n.msg('eng.scriptbuilder.human_control','human controlled'), 'computer': lambda: _i18n.msg('eng.scriptbuilder.computer_control','computer controlled'), 'these':picks}.get(v['v'],lambda:v['v'])()
    if condition:
        result = {
            'who': lambda: _i18n.msg('eng.scriptbuilder.test_control','the faction is {control}',control=control()),
            'old_owner': lambda: _i18n.msg('eng.scriptbuilder.test_old_control','the former owner is {control}',control=control()),
            'money': lambda: _i18n.msg('eng.scriptbuilder.test_treasury','the treasury is {op} {amount} {currency}',op=v['op'],amount=v['v'],currency=currency),
            'towns': lambda: _i18n.msg('eng.scriptbuilder.test_towns','the town count is {op} {count}',op=v['op'],count=v['v']),
            'turn': lambda: _i18n.msg('eng.scriptbuilder.test_turn','the turn is {op} {turn}',op=v['op'],turn=v['v']),
            'chance': lambda: _i18n.msg('eng.scriptbuilder.test_chance','a {percent} percent roll succeeds',percent=v['v']),
            'people': lambda: _i18n.msg('eng.scriptbuilder.test_people','population is {op} {population}',op=v['op'],population=v['v']),
            'town_is': lambda: _i18n.msg('eng.scriptbuilder.test_selected_towns','the town is among {towns}',towns=picks()),
            'capital': lambda: _i18n.msg('eng.scriptbuilder.test_capital','the town is the capital'),
            'has_chain': lambda: _i18n.msg('eng.scriptbuilder.test_chain','the town has {chain}',chain=v['v'] or _i18n.msg('eng.scriptbuilder.no_chain','(no chain picked)')),
            'counter': lambda: _i18n.msg('eng.scriptbuilder.test_counter','counter {name} is {op} {value}',name=v['name'],op=v['op'],value=v['v']),
            'game': lambda: _i18n.msg('eng.scriptbuilder.test_engine','the engine accepts {line}',line=v['line'] or _i18n.msg('eng.scriptbuilder.no_condition','(no condition picked)')),
        }[k]()
        return _i18n.msg('eng.scriptbuilder.negated','not true that {condition}',condition=result) if item.get('not') else result
    return {
        'money': lambda: _i18n.msg('eng.scriptbuilder.action_money',"change {faction}'s treasury by {amount} {currency}",faction=destination(),amount=v['amount'],currency=currency),
        'people': lambda: _i18n.msg('eng.scriptbuilder.action_people','change population by {amount}',amount=v['amount']),
        'people_pct': lambda: _i18n.msg('eng.scriptbuilder.action_people_pct','remove {percent} percent of the population',percent=v['pct']),
        'people_max': lambda: _i18n.msg('eng.scriptbuilder.action_people_max','cap population at {maximum}',maximum=v['max']),
        'build': lambda: _i18n.msg('eng.scriptbuilder.action_build','build {level}',level=v['level'] or _i18n.msg('eng.scriptbuilder.no_level','(no level picked)')),
        'tear_down': lambda: _i18n.msg('eng.scriptbuilder.action_tear_down','remove {chain}',chain=v['chain'] or _i18n.msg('eng.scriptbuilder.no_chain','(no chain picked)')),
        'units': lambda: _i18n.msg('eng.scriptbuilder.action_units','add {count} of {unit} to the garrison',count=v['count'],unit=v['unit'] or _i18n.msg('eng.scriptbuilder.no_unit','(no unit picked)')),
        'give_town': lambda: _i18n.msg('eng.scriptbuilder.action_give_town','give the town to {faction}',faction=destination()),
        'stance': lambda: _i18n.msg('eng.scriptbuilder.action_stance','set relations between {first} and {second} to {stance}',first=destination('a'),second=destination('b','faction_b'),stance=v['stance']),
        'trait': lambda: _i18n.msg('eng.scriptbuilder.action_trait','grant {trait} at level {level}',trait=v['trait'] or _i18n.msg('eng.scriptbuilder.no_trait','(no trait picked)'),level=v['level']),
        'ancillary': lambda: _i18n.msg('eng.scriptbuilder.action_ancillary','grant {ancillary}',ancillary=v['anc'] or _i18n.msg('eng.scriptbuilder.no_ancillary','(no ancillary picked)')),
        'counter_set': lambda: _i18n.msg('eng.scriptbuilder.action_counter_set','set counter {name} to {value}',name=v['name'],value=v['v']),
        'counter_add': lambda: _i18n.msg('eng.scriptbuilder.action_counter_add','change counter {name} by {value}',name=v['name'],value=v['v']),
        'message': lambda: _i18n.msg('eng.scriptbuilder.action_message','show the scroll {title}',title=v['title'] or _i18n.msg('eng.scriptbuilder.no_heading','(no heading yet)')),
        'log': lambda: _i18n.msg('eng.scriptbuilder.action_log','log {text}',text=v['text'] or _i18n.msg('eng.scriptbuilder.no_text','(no text yet)')),
        'console': lambda: _i18n.msg('eng.scriptbuilder.action_console','run console line {line}',line=v['text'] or _i18n.msg('eng.scriptbuilder.no_command','(no command picked)')),
        'script': lambda: _i18n.msg('eng.scriptbuilder.action_script','run campaign line {line}',line=v['text'] or _i18n.msg('eng.scriptbuilder.no_command','(no command picked)')),
    }[k]()


def readback(recipe):
    event = event_for(recipe,{'events':{}})
    text = _i18n.msg('eng.scriptbuilder.when','When {event}',event=event.label if event else _i18n.msg('eng.scriptbuilder.no_event','(no event picked)'))
    each = recipe.get('each')
    if each:
        scope = scriptwords.word('each',each,dict(EACH).get(each,each))
        if each != 'faction':
            owner = recipe.get('each_of','this')
            scope = _i18n.msg('eng.scriptbuilder.iteration_owner','{scope} {owner}',scope=scope,owner=scriptwords.word('each_of',owner,dict(EACH_OF).get(owner,'')))
            if owner == 'named':
                scope = _i18n.msg('eng.scriptbuilder.iteration_named','{scope} {faction}',scope=scope,faction=recipe.get('each_faction',''))
        text = _i18n.msg('eng.scriptbuilder.for_each','{when}, for {scope}',when=text,scope=scope)
    conditions = [phrase(x,True,recipe.get('game','both')) for x in recipe.get('ifs',[])]
    match = recipe.get('match') or 'all'
    if conditions:
        if match == 'none':
            text = _i18n.msg('eng.scriptbuilder.if_none','{when}, if none of: {conditions}',when=text,conditions='; '.join(conditions))
        elif match == 'any':
            text = _i18n.msg('eng.scriptbuilder.if_any','{when}, if {conditions}',when=text,conditions=_i18n.msg('eng.scriptbuilder.or_separator',' or ').join(conditions))
        else:
            text = _i18n.msg('eng.scriptbuilder.if_all','{when}, if {conditions}',when=text,conditions=_i18n.msg('eng.scriptbuilder.and_separator',' and ').join(conditions))
    actions = '; '.join(phrase(x,False,recipe.get('game','both')) for x in recipe.get('dos',[])) or _i18n.msg('eng.scriptbuilder.no_actions','nothing yet')
    text = _i18n.msg('eng.scriptbuilder.readback_actions','{when}: {actions}',when=text,actions=actions)
    if recipe.get('else'):
        text = _i18n.msg('eng.scriptbuilder.readback_else','{rule}, otherwise: {actions}',rule=text,actions='; '.join(phrase(x,False,recipe.get('game','both')) for x in recipe['else']))
    text = _i18n.msg('eng.scriptbuilder.readback_end','{rule}.',rule=text)
    if recipe.get('once'):
        text = _i18n.msg('eng.scriptbuilder.readback_once','{rule} Only once in a campaign.',rule=text)
    if recipe.get('only_with'):
        text = _i18n.msg('eng.scriptbuilder.readback_only_with','{rule} Only in a campaign that has the faction {faction}.',rule=text,faction=recipe['only_with'])
    return text


def setting_variables(recipe):
    used = {'MB_ON','MB_ONCE'}
    result = {}
    for path,label in recipe.get('settings',{}).items():
        stem = re.sub('[^A-Z0-9]+','_',label.upper()).strip('_')[:36] or 'VALUE'
        var, i = 'MB_'+stem, 2
        while var in used:
            var = 'MB_'+stem+'_'+str(i)
            i += 1
        used.add(var)
        result[path] = var
    return result


def squirrel(value):
    if isinstance(value,dict): return '{'+', '.join('['+json.dumps(str(k))+'] = '+squirrel(v) for k,v in value.items())+'}'
    if isinstance(value,list): return '['+', '.join(squirrel(v) for v in value)+']'
    return json.dumps(value,ensure_ascii=True)


def generate(recipe, mod=None):
    key = key_for(recipe['title'])
    variables = setting_variables(recipe)
    fields = {p:(kind,value) for p,b,n,kind,lab,value in fields_of(recipe)}
    lines = ['// @title '+recipe['title'].strip().replace('\r',' ').replace('\n',' '), '// @game '+recipe.get('game','both'),
             '// @summary a campaign rule assembled with the module builder',
             '// @settings '+', '.join(['MB_ON','MB_ONCE']+list(variables.values())),
             '// @label MB_ON run this module', '// @label MB_ONCE run once per campaign',
             '// @recipe '+json.dumps(recipe,ensure_ascii=True,separators=(',',':')),
             'local MB_ON = true;', 'local MB_ONCE = '+squirrel(bool(recipe.get('once')))+';']
    signed = []
    for path,var in variables.items():
        kind,value = fields[path]
        lines += ['// @label '+var+' '+str(recipe['settings'][path]).replace('\n',' '), 'local '+var+' = '+squirrel(value)+';']
        if kind == 'signed': signed.append(var)
    lines.append('// @signed '+', '.join(signed))
    runtime_recipe = copy.deepcopy(recipe)
    runtime_recipe['townNames'] = SC.town_names(mod)
    for group in ('ifs','dos','else'):
        definitions = CONDITIONS if group == 'ifs' else ACTIONS
        for item in runtime_recipe.get(group,[]):
            b = next(b for b in definitions if b.key == item['k'])
            for n,kind,lab,d in b.fields: item.setdefault(n,copy.deepcopy(d))
            item['_words'] = phrase(item,group=='ifs',recipe.get('game','both'))
    msg = 0
    for group in ('dos','else'):
        for item in runtime_recipe.get(group,[]):
            if item['k'] == 'message':
                msg += 1
                item['_message'] = f'{key}_msg{msg}'
    event = event_for(recipe,{'events':{}})
    lines += ['local rule = '+squirrel(runtime_recipe)+';']
    for path,var in variables.items():
        group,number,field = path.split('.')
        lines.append(f'rule[{squirrel(group)}][{number}][{squirrel(field)}] = {var};')
    lines += ['local moduleKey = '+squirrel(key)+';', 'local engineEvent = '+squirrel(event.engine)+';', _RUNTIME]
    return '\n'.join(lines).rstrip()+'\n'


def preview(mod, recipe):
    problems = validate(mod,recipe)
    return dict(words=readback(recipe), problems=problems, script='' if problems else generate(recipe,mod), settings=exposed(recipe))


def save_module(recipe):
    problems = validate(None,recipe)
    if problems: raise ValueError(_i18n.msg('eng.scriptbuilder.validation_errors','{errors}',errors='; '.join(problems)))
    from . import config
    if config.CONFIG_DIR is None:
        raise ValueError(_i18n.msg('eng.scriptbuilder.the_editor_has_no_folder_of',
                                  'the editor needs its own folder to store add-ons'))
    path = SC.library() / (key_for(recipe['title'])+'.nut')
    if path.exists() and recipe_in(path.read_text(encoding='utf-8',errors='replace')) is None:
        raise ValueError(_i18n.msg('eng.scriptbuilder.not_made_with_builder','{name} belongs to another add-on; choose a different title',name=path.name))
    path.write_bytes(generate(recipe).encode('utf-8'))
    return dict(key=key_for(recipe['title']),title=recipe['title'].strip())


def example(mod,title):
    recipe = copy.deepcopy(next(r for r in EXAMPLES if r['title'] == title))
    sources = SC.names(mod)
    preferred = dict(chains=['barracks','castle_barracks','city_barracks'],traits=['GoodCommander','GoodAttacker','BattleScarred'])
    try:
        preferred['units'] = [u.type for u in mod.edu.units if u.category.lower() == 'infantry' and any(f.lower() != 'slave' for f in u.ownership)
                              and not any(s in u.type.lower() for s in ('general','bodyguard','merc'))]
    except (OSError,ValueError,AttributeError):
        pass
    for path,b,n,kind,lab,value in fields_of(recipe):
        if value or not kind.startswith(('name:','names:')): continue
        category = kind.partition(':')[2]
        if category == 'factions': continue
        available = sources[category]
        chosen = next((s for s in preferred.get(category,[]) if s in available), next(iter(available),''))
        if chosen:
            group,index,_ = path.split('.')
            recipe[group][int(index)][n] = [chosen] if kind.startswith('names:') else chosen
    return recipe


def stage_messages(plan, recipe, values):
    from . import stringsbin
    changed = copy.deepcopy(recipe)
    for path,var in setting_variables(recipe).items():
        if var in values:
            group,index,field = path.split('.')
            changed[group][int(index)][field] = values[var]
    entries = {}
    number = 0
    for group in ('dos','else'):
        for item in changed.get(group,[]):
            if item['k'] != 'message': continue
            number += 1
            ident = f"{key_for(recipe['title'])}_msg{number}"
            entries.update({ident:item.get('title',''),ident+'_body':item.get('body') or item.get('title',''),ident+'_image':'messenger'})
    if not entries: return
    path = SC.existing(plan.mod.data,'text','custom_messages.txt')
    raw = plan.stored(path)
    new = raw is None
    if new:
        game_path = SC.existing(SC.game_root(plan.mod),'data','text','custom_messages.txt')
        if game_path.absolute() != path.absolute(): raw = plan.stored(game_path)
    copied = raw is not None
    utf16 = raw.startswith(b'\xff\xfe') if raw is not None else True
    if raw is None:
        folder = SC.existing(plan.mod.data,'text')
        if folder.is_dir():
            for candidate in sorted(folder.iterdir(),key=lambda p:p.name):
                if candidate.suffix.lower() != '.txt': continue
                sample = plan.stored(candidate)
                if sample is not None:
                    utf16 = sample.startswith(b'\xff\xfe')
                    break
        text = '¬ Messages of the add-ons made with the Module builder (display_message <id>)\r\n'
    else:
        text = raw[2:].decode('utf-16le') if utf16 else raw.decode('utf-8-sig')
    text = stringsbin.upsert_txt(text,{ident:'\t'+str(value) for ident,value in entries.items()})
    nl = '\r\n' if new or '\r\n' in text else '\n'
    text = nl.join(text.replace('\r\n','\n').rstrip('\n').split('\n'))+nl
    plan.binary(path, (b'\xff\xfe'+text.encode('utf-16le')) if utf16 else text.encode('utf-8'))
    cache = SC.existing(path.parent,path.name+'.strings.bin')
    if cache.exists(): plan.delete(cache,_i18n.msg('eng.scriptbuilder.rebuild_message_cache','the game builds it again from the text'))
    if new:
        if copied:
            plan.note(None,_i18n.msg('eng.scriptbuilder.messages_made_copy',"{name} created from the game's table for module messages",name=path.name))
        else:
            plan.note(None,_i18n.msg('eng.scriptbuilder.messages_made','{name} created for module messages',name=path.name))


_RUNTIME = r'''
// All engine entry points below use ENGINE_API.md; failures stay inside this module.
local say = function(text) {
    try { println("[" + moduleKey.toupper() + "] " + text); } catch (ignored) {}
};
local get = function(obj, name, fallback = null) {
    if (obj == null) return fallback;
    try { return obj[name]; } catch (e) { return fallback; }
};
local read = function(obj, name, fallback = null) {
    if (obj == null) return fallback;
    try { return obj[name]; }
    catch (e) { say("cannot read " + name + ": " + e); return fallback; }
};
local storage = function() {
    try {
        if (!("persistent" in getroottable())) ::persistent <- {};
        if (!(moduleKey in ::persistent)) ::persistent[moduleKey] <- {};
        return ::persistent[moduleKey];
    } catch (e) { say("saved state unavailable: " + e); return null; }
};
local save = function(name, value) {
    try {
        local state = storage();
        if (state == null) return;
        state[name] <- value;
    } catch (e) { say("saved state write failed: " + e); }
};
local settlement = function(town) {
    if (town == null) return null;
    local id = read(town,"regionId");
    if (id == null) return town;
    try { return ::stratMap.region(id).settlementAt(0); }
    catch (e) { say("settlement lookup failed for region " + id + ": " + e); return town; }
};
local human = function(f) {
    local h = read(f,"isPlayerControlled"); return h == true || h == 1;
};
local factions = function() {
    local result = [], count = 0;
    try { count = ::game.factionCount(); } catch (e) { say("faction count failed: " + e); }
    for (local i = 0; i < count; i++) {
        try { result.append(::game.faction(i)); } catch (e) { say("faction " + i + " failed: " + e); }
    }
    return result;
};
local faction = function(name) {
    foreach (f in factions()) if (read(f,"name","") == name) return f;
    say("faction missing: " + name); return null;
};
local player = function() {
    try { return ::game.localFaction(); }
    catch (e) { say("local faction failed: " + e); return null; }
};
local objectCount = function(obj, name) {
    try {
        local count = obj[name];
        if (typeof count == "function") count = obj[name]();
        return count;
    } catch (e) { say(name + " failed: " + e); return 0; }
};
local towns = function(f) {
    local result = [], count = 0;
    try { count = objectCount(::stratMap,"regionCount"); }
    catch (e) { say("region enumeration failed: " + e); }
    local name = read(f,"name");
    if (name == null) return result;
    for (local i = 0; i < count; i++) {
        try {
            local town = ::stratMap.region(i).settlementAt(0);
            if (town != null && read(read(town,"owner"),"name") == name) result.append(town);
        } catch (e) { say("region " + i + " failed: " + e); }
    }
    return result;
};
local armies = function(f) {
    local result = [], count = objectCount(f,"armyCount");
    for (local i = 0; i < count; i++) {
        try {
            local army = get(f,"army") != null ? f.army(i) : f.armyAt(i);
            if (army != null) result.append(army);
        } catch (e) { say("army " + i + " failed: " + e); }
    }
    return result;
};
local commander = function(army) {
    foreach (name in ["general","leader","character"]) {
        local character = get(army,name);
        if (character != null) return character;
    }
    return null;
};
local turn = function() {
    try { return ::game.campaign().turnNumber + 1; }
    catch (e) { say("campaign turn failed: " + e); return null; }
};
local seed = 1;
try { seed = ::game.campaign().millisecondCount; } catch (e) { say("random seed failed: " + e); }
local roll = function() {
    // Module-local generator avoids changing the game's global random sequence.
    seed = (seed * 1664525 + 1013904223) & 0x7fffffff;
    return seed % 100;
};
local generalName = function(c) {
    local record = c.characterRecord;
    local name = get(c.character,"fullName",get(c.character,"name",null));
    if (name == null) name = get(record,"fullName",get(record,"name",""));
    return name;
};
local expand = function(text, c) {
    local substitutions = {
        town = read(c.settlement,"name", ""), faction = read(c.faction,"name", ""),
        owner = read(c.target,"name", ""), general = generalName(c),
        turn = turn(), people = read(c.settlement,"population", "")
    };
    foreach (key, value in substitutions) {
        local token = "{" + key + "}";
        local pos = 0;
        while ((pos = text.find(token, pos)) != null) {
            local word = value == null ? "" : value.tostring();
            text = text.slice(0,pos) + word + text.slice(pos + token.len());
            pos += word.len();
        }
    }
    return text;
};
local compare = function(a, op, b) {
    if (typeof a != "integer" && typeof a != "float") return false;
    switch (op) {
        case "<": return a < b; case ">": return a > b;
        case "<=": return a <= b; case ">=": return a >= b;
        case "==": return a == b; case "every": return b > 0 && a % b == 0;
    }
    return false;
};
local counter = function(name) {
    try { local v = ::game.eventCounter(name); return v == null ? 0 : v; }
    catch (e) { say("counter read failed for " + name + ": " + e); return get(storage(), "n_" + name, 0); }
};
local setCounter = function(name, value) {
    try { ::game.setEventCounter(name,value); }
    catch (e) { say("counter write failed for " + name + ": " + e); }
    save("n_" + name,value); say("counter " + name + " is " + value);
};
local scriptCommand = function(verb, rest) {
    try {
        local ok = ::game.runScriptCommand(verb,rest);
        say("campaign command " + verb + (ok == true ? " accepted" : " refused"));
        return ok == true;
    } catch (e) { say("campaign command " + verb + " failed: " + e); return false; }
};
local console = function(verb, rest) {
    try {
        local reply = ::game.runConsoleCommand(verb,rest);
        if (reply != false) {
            say("console " + verb + " reply: " + (reply == null ? "no reply" : reply.tostring()));
            return true;
        }
        say("console " + verb + " refused");
    } catch (e) { say("console " + verb + " failed: " + e); }
    return scriptCommand("console_command",verb + " " + rest);
};
local accepted = function(ok) {
    if (!ok) throw "engine command failed or was refused";
    return ok;
};
local commandLine = function(line, isConsole) {
    // Only split the verb: quoted arguments and spaces must remain intact.
    line = strip(line);
    local end = 0;
    while (end < line.len() && line[end] != 32 && line[end] != 9 && line[end] != 10 && line[end] != 13) end++;
    local verb = line.slice(0,end), rest = strip(line.slice(end));
    return accepted(isConsole ? console(verb,rest) : scriptCommand(verb,rest));
};
local quote = function(value) {
    if (value == null || value == "") throw "missing command recipient or name";
    local result = "\"";
    foreach (ch in value.tostring()) {
        if (ch == 34 || ch == 92) result += "\\";
        result += ch.tochar();
    }
    return result + "\"";
};
local recipient = function(selector, name, c) {
    switch (selector) {
        case "this": return c.faction; case "old": return c.target;
        case "player": return player(); case "rebels": return faction("slave");
        case "named": return faction(name);
    }
    return null;
};
local control = function(f, mode, names) {
    if (f == null) return false;
    if (mode == "player") return human(f);
    if (mode == "computer") {
        local h = read(f,"isPlayerControlled");
        return h != null && h != true && h != 1;
    }
    return names.find(read(f,"name","")) != null;
};
local treasury = function(f) {
    // Both spellings are documented; no other engine aliases are probed.
    local money = get(f,"money");
    return money == null ? read(f,"treasury") : money;
};
local hasChain = function(town, chain) {
    if (town == null) return false;
    local count = read(town,"buildingCount",0);
    for (local i = 0; i < count; i++) {
        try { if (town.building(i).chainName == chain) return true; }
        catch (e) { say("building read failed: " + e); throw e; }
    }
    return false;
};
local test = function(b,c) {
    switch (b.k) {
        case "who": return control(c.faction,b.v,b.names);
        case "old_owner": return control(c.target,b.v,b.names);
        case "money": return compare(treasury(c.faction),b.op,b.v);
        case "towns": return compare(read(c.faction,"settlementCount"),b.op,b.v);
        case "turn": return compare(turn(),b.op,b.v);
        case "chance": return roll() < b.v;
        case "people": return compare(read(c.settlement,"population"),b.op,b.v);
        case "town_is": {
            local name = read(c.settlement,"name","");
            foreach (pick in b.names) if (get(rule.townNames,pick,pick) == name) return true;
            return false;
        }
        case "capital": return c.settlement != null && read(c.faction,"capital") == c.settlement;
        case "has_chain": return hasChain(c.settlement,b.v);
        case "counter": return compare(counter(expand(b.name,c)),b.op,b.v);
        case "game":
            try { return ::game.evaluateCondition(expand(b.line,c) + "\n"); }
            catch (e) { say("condition failed: " + b._words + ": " + e); throw e; }
    }
    return false;
};
local changePopulation = function(town, desired) {
    if (town == null) { say("population target town is missing"); return; }
    local before = read(town,"population");
    // The engine itself enforces the settlement level's population minimum.
    try { town.population = desired.tointeger(); }
    catch (e) {
        say("population assignment failed: " + e);
        accepted(console("set_population",quote(read(town,"name")) + " " + desired.tointeger()));
    }
    say("population " + before + " -> " + read(town,"population"));
};
local act = function(b,c) {
    switch (b.k) {
        case "money": {
            local f = recipient(b.to,b.faction,c);
            if (f == null) { say("money recipient faction is missing"); break; }
            local before = treasury(f);
            try {
                if (get(f,"money") != null) f.money = before + b.amount;
                else f.treasury = before + b.amount;
            } catch (e) {
                say("treasury assignment failed: " + e);
                accepted(console("add_money",quote(read(f,"name")) + " " + b.amount));
            }
            say("treasury " + before + " -> " + treasury(f)); break;
        }
        case "people": changePopulation(c.settlement,read(c.settlement,"population")+b.amount); break;
        case "people_pct": changePopulation(c.settlement,read(c.settlement,"population")*(100-b.pct)/100.0); break;
        case "people_max":
            if (read(c.settlement,"population") > b.max) changePopulation(c.settlement,b.max); break;
        case "build": accepted(console("create_building",quote(read(c.settlement,"name")) + " " + quote(b.level))); break;
        case "tear_down":
            if (b.chain.find("core") == 0) say("core chain retained: " + b.chain);
            else if (!hasChain(c.settlement,b.chain)) say("chain not present: " + b.chain);
            else {
                try {
                    c.settlement.destroyBuilding(b.chain,false);
                    say("chain " + b.chain + (hasChain(c.settlement,b.chain) ? " retained" : " removed"));
                } catch (e) { say("chain demolition failed: " + b.chain + ": " + e); }
            }
            break;
        case "units": accepted(console("create_unit",quote(read(c.settlement,"name")) + " " + quote(b.unit) + " " + b.count)); break;
        case "give_town": {
            local f = recipient(b.to,b.faction,c);
            if (f == null || c.settlement == null) { say("town or receiving faction is missing"); break; }
            if (accepted(scriptCommand("give_settlement",quote(read(c.settlement,"name")) + " " + quote(read(f,"name")))))
                say("town " + read(c.settlement,"name","") + " transferred to " + read(f,"name",""));
            break;
        }
        case "stance": {
            local a = recipient(b.a,b.faction,c), z = recipient(b.b,b.faction_b,c);
            if (a == null || z == null) { say("a diplomatic faction is missing"); break; }
            accepted(console("diplomatic_stance",quote(read(a,"name")) + " " + quote(read(z,"name")) + " " + b.stance)); break;
        }
        case "trait": accepted(console("give_trait",quote(generalName(c)) + " " + quote(b.trait) + " " + b.level)); break;
        case "ancillary": accepted(console("give_ancillary",quote(generalName(c)) + " " + quote(b.anc))); break;
        case "counter_set": setCounter(expand(b.name,c),b.v); break;
        case "counter_add": { local n = expand(b.name,c); setCounter(n,counter(n)+b.v); break; }
        case "message": if (accepted(console("display_message",b._message))) say("scroll shown: " + b._message); break;
        case "log": say(expand(b.text,c)); break;
        case "console": case "script": commandLine(expand(b.text,c),b.k == "console"); break;
    }
};
local runOne = function(c) {
    local tests = get(rule,"ifs",[]), mode = get(rule,"match","all"), pass = mode != "any";
    foreach (b in tests) {
        local v = false;
        try {
            v = test(b,c);
            if (get(b,"not",false)) v = !v;
        } catch (e) { say("condition failed: " + b._words + ": " + e); v = false; }
        if (mode == "any") pass = pass || v;
        else if (mode == "none") pass = pass && !v;
        else pass = pass && v;
    }
    if (tests.len() == 0) pass = true;
    local actions = pass ? rule.dos : get(rule,"else",[]);
    if (!pass && actions.len() == 0) return false;
    say((pass ? "DO" : "ELSE") + " for " + expand("{faction} {town} {owner}",c));
    foreach (b in actions) {
        try { act(b,c); } catch (e) { say("action failed: " + b._words + ": " + e); }
    }
    return true;
};
local absentReported = false;
local receive = function(event = null) {
    if (!MB_ON || (MB_ONCE && get(storage(),"done",false))) return;
    local required = get(rule,"only_with","");
    if (required != "" && faction(required) == null) {
        if (!absentReported) { say("faction " + required + " is absent; this module does nothing in this campaign"); absentReported = true; }
        return;
    }
    local c = {faction=get(event,"faction"),settlement=get(event,"settlement",get(event,"targetSettlement")),
               character=get(event,"character"),characterRecord=get(event,"characterRecord"),
               target=get(event,"targetFaction"),unit=get(event,"unit")};
    c.settlement = settlement(c.settlement);
    if (c.characterRecord == null) c.characterRecord = get(c.character,"characterRecord");
    if (c.faction == null) c.faction = read(c.settlement,"owner");
    if (rule.when == "player_turn" && !human(c.faction)) return;
    local each = get(rule,"each",""), acted = false;
    if (each == "faction") {
        foreach (f in factions()) if (read(f,"name","") != "slave") {
            local next = clone c; next.faction = f; if (runOne(next)) acted = true;
        }
    } else if (each == "town" || each == "army") {
        local selection = get(rule,"each_of","this");
        local f = selection == "player" ? player() :
                  (selection == "named" ? faction(get(rule,"each_faction","")) : c.faction);
        if (f == null) { say("iteration faction is missing"); return; }
        // Snapshot the selected objects before actions can change ownership.
        local items = each == "town" ? towns(f) : armies(f);
        foreach (item in items) {
            local next = clone c;
            next.faction = f;
            if (each == "town") {
                next.settlement = item;
                next.faction = read(item,"owner");
            } else {
                next.character = commander(item);
                next.characterRecord = get(next.character,"characterRecord");
            }
            try { if (runOne(next)) acted = true; }
            catch (e) { say("iteration item failed: " + e); }
        }
    } else acted = runOne(c);
    if (acted && MB_ONCE) save("done",true);
};
local handler = function(e) {
    try { receive(e); } catch (error) { say("event handler failed: " + error); }
};
try { ::events.on(engineEvent,handler); }
catch (e) { say("event registration failed: " + e); }
try { ::events.on("GameReloaded",function(e) { absentReported = false; }); }
catch (e) { say("reload registration failed: " + e); }
say("module loaded");
'''
