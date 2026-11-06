"""Read engine facts and validate expert command identifiers.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from . import scriptcompat as SC, i18n as _i18n

EXPORTS = dict(characterRecord='character', targetFaction='target', targetSettlement='settlement', faction='faction', settlement='settlement', target_settlement='settlement',
               character_record='character', character='character', nc_character_record='character',
               target_faction='target', unit='unit', player_unit='unit')
FLOW = set('if if_not while while_fast while_yield monitor_event monitor_conditions else else_if end_if end_while end_monitor terminate_monitor script end_script terminate_script goto label set_label break return wait campaign_wait wait_monitors'.split())
FILES = dict(console='console_commands.txt', commands='docudemon_commands.txt', conditions='docudemon_conditions.txt', events='docudemon_events.txt')


def _signature(text):
    depth = 0
    for i, ch in enumerate(text):
        if ch in '[<(': depth += 1
        if ch in ']>)': depth = max(0, depth - 1)
        if ch == ':' and depth == 0: return text[:i].strip()
    return text.strip()


def parse_document(text, category):
    records = {}
    if category == 'console':
        heading, availability = '', ''
        for line in text.splitlines():
            s = line.strip()
            if s.startswith('Availability:'):
                availability = s.partition(':')[2].strip()
            elif s.startswith('Usage:'):
                usage = _signature(s.partition(':')[2].strip())
                name = usage.split()[0] if usage else heading
                if name and name not in records:
                    records[name] = [name, usage[len(name):].strip(), usage, availability, [], True]
            elif s and not s.startswith(('Description:', '-')):
                heading = s
        return records
    fields = 'Identifier|Parameters|Description|Sample use|Class|Implemented|Trigger requirements|Battle or Strat|Event|Exports'
    for chunk in re.split(r'-{10,}', text):
        values, last = {}, None
        for line in chunk.splitlines():
            m = re.match(r'^\s*(' + fields + r')\s*:\s*(.*)$', line)
            if m:
                last = m[1]
                values[last] = m[2].strip()
            elif last and line.strip():
                values[last] += ' ' + line.strip()
        name = values.get('Event' if category == 'events' else 'Identifier', '')
        if not name or name in records: continue
        params = values.get('Parameters', '')
        if category == 'conditions' and params.lower() == 'none': params = ''
        needs = values.get('Exports' if category == 'events' else 'Trigger requirements', '')
        needs = [s.strip() for s in needs.split(',') if s.strip() and s.strip().lower() != 'none']
        records[name] = [name, params, values.get('Sample use', ''), values.get('Battle or Strat', values.get('Class', '')), needs,
                         values.get('Implemented', '').strip().lower() != 'no']
    return records


def catalogue(mod=None, game='both'):
    try:
        with gzip.open(Path(__file__).parent / 'data' / 'engine_catalogue.json.gz', 'rt', encoding='ascii') as f:
            bundled = json.load(f)
    except (OSError, ValueError):
        bundled = {}
    engines = {e: {k: {r[0]: list(r) for r in bundled.get(e, {}).get(k, [])} for k in FILES} for e in ('rex', 'm2ex')}
    if mod is not None:
        for kind, filename in FILES.items():
            for root in (SC.game_root(mod), Path(mod.root)):
                path = SC.existing(root, 'documentation', filename)
                try:
                    new = parse_document(path.read_text(encoding='utf-8', errors='replace'), kind)
                except OSError:
                    continue
                for name, row in new.items(): engines['m2ex'][kind].setdefault(name, row)
                break
    if game in ('rome', 'medieval2'):
        return engines['rex' if game == 'rome' else 'm2ex']
    shared = {}
    for kind in FILES:
        shared[kind] = {}
        for name, m in engines['m2ex'][kind].items():
            r = engines['rex'][kind].get(name)
            if r is None: continue
            row = list(m)
            if r[1] and r[1] != m[1]: row[1] += '   (REX: ' + r[1] + ')'
            row[2] = m[2] or r[2]
            row[5] = m[5] and r[5]
            if kind == 'events': row[4] = [x for x in m[4] if x in r[4]]
            shared[kind][name] = row
    return shared


def subjects(exports):
    return {EXPORTS[x] for x in exports if x in EXPORTS}


def check_line(line, category, facts, event_exports, game):
    line = line.strip()
    if not line: return _i18n.msg('eng.scriptdocs.enter_an_engine_line_or_choose_one', 'enter an engine line or choose one')
    words = line.split()
    if category == 'conditions' and words[0] == 'not': words = words[1:]
    if not words: return _i18n.msg('eng.scriptdocs.enter_a_condition_after_not', 'enter a condition after not')
    name = words[0]
    rows = facts[category]
    if not rows: return ''
    if category == 'commands' and (name in FLOW or any(line.startswith(k + ' ') for k in rows if ' ' in k)):
        return _i18n.msg('eng.scriptdocs.campaign_script_flow_belongs_in_the_module_rule_not_an_individual_command', 'campaign_script flow belongs in the module rule, not an individual command')
    if name not in rows:
        similar = next((k for k in rows if k.lower() == name.lower()), None)
        if similar: return _i18n.msg('eng.scriptdocs.use_the_exact_spelling_similar', 'use the exact spelling {similar}', similar=similar)
        engine = {'rome': 'REX', 'medieval2': 'M2EX', 'both': 'REX and M2EX'}.get(game, game)
        return _i18n.msg('eng.scriptdocs.name_is_not_a_known_category_identifier_for_engine', '{name} is not a known {category} identifier for {engine}', name=name, category=category, engine=engine)
    row = rows[name]
    if not row[5]: return _i18n.msg('eng.scriptdocs.name_is_marked_as_not_implemented', '{name} is marked as not implemented', name=name)
    context = row[3].lower()
    availability = {x.strip() for x in context.split(',')}
    if category == 'console' and 'campaign' not in availability:
        return _i18n.msg('eng.scriptdocs.name_is_unavailable_on_the_campaign_map', '{name} is unavailable on the campaign map', name=name)
    if category == 'conditions':
        if 'battle' in context and not any(x in context for x in ('strat', 'campaign', 'both')):
            return _i18n.msg('eng.scriptdocs.name_is_only_available_in_battles', '{name} is only available in battles', name=name)
        missing = [x for x in row[4] if x not in event_exports]
        if missing: return _i18n.msg('eng.scriptdocs.name_needs_event_data_missing', '{name} needs event data: {missing}', name=name, missing=', '.join(missing))
    return ''
