"""Phase 116: the recruitment sheet made editable.

A recruitment row is one ``recruit_pool`` line of export_descr_buildings.txt,
and its ID is that line's number. Its four numbers (initial, per turn, maximum,
experience) can be staged from a cell, a pasted rectangle or a CSV/XLSX import.
A staged row is kept in the sheet project under ``recruit_draft`` with the unit,
building and level it was staged against, so a row whose line now holds
something else is reported stale instead of being written to the wrong pool.
Nothing touches the EDB until the review's Apply, which rewrites only those
number tokens and goes through the EDB's own atomic writer with its backup and
Log Undo, as the balance pipeline does.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re

from . import buildings, edb_balance, sheet_ops, unit_sheets as sheets
from . import i18n as _i18n

NUMBERS = sheet_ops.RECRUIT_NUMBERS
_IDENTITY = ('unit', 'building', 'level')


def drafts(project):
    return project.get('recruit_draft') or {}


def validate(project):
    """The shape of ``recruit_draft``; the numbers are checked when staged."""
    value = project.get('recruit_draft', {})
    if not isinstance(value, dict):
        sheets.fail(_i18n.msg('eng.sheets.invalid_recruit_draft', 'Invalid staged recruitment edits'))
    for rid, row in value.items():
        if (not isinstance(rid, str) or not rid.isdigit() or not isinstance(row, dict)
                or any(not isinstance(row.get(k), str) for k in _IDENTITY)
                or not isinstance(row.get('fields'), dict) or not row['fields']
                or any(k not in NUMBERS for k in row['fields'])):
            sheets.fail(_i18n.msg('eng.sheets.invalid_recruit_draft', 'Invalid staged recruitment edits'))


def value(column, raw):
    """One staged number, as the EDB will hold it."""
    n = sheet_ops.number(raw)
    if n < 0 or column == 'experience' and not n.is_integer():
        sheets.fail(_i18n.msg('eng.sheets.invalid_recruit_value',
                              '{column} has to be zero or more, and experience a whole number', column=column))
    return int(n) if n.is_integer() else n


def _live(mod):
    return {row['id']: row for row in edb_balance.recruitments(edb_balance.fresh_edb(mod))}


def _same(a, b):
    return all(a.get(k) == b.get(k) for k in _IDENTITY)


def stage(mod, project, cells, live=None):
    """``(project copy, changes)`` with these cells staged; refuses as a whole."""
    import copy
    if not isinstance(cells, list) or not cells or len(cells) > 10000:
        sheets.fail(_i18n.msg('eng.sheets.paste_must_contain_1_10000_cells', 'paste must contain 1-10000 cells'))
    live = _live(mod) if live is None else live
    p = copy.deepcopy(project)
    staged = p.setdefault('recruit_draft', {})
    changes = []
    for cell in cells:
        rid, column = cell.get('id') if isinstance(cell, dict) else None, cell.get('column') if isinstance(cell, dict) else None
        if rid not in live:
            sheets.fail(_i18n.msg('eng.sheets.unknown_recruit_row', 'No recruitment line {row} in the EDB', row=rid))
        if column not in NUMBERS:
            sheets.fail(_i18n.msg('eng.sheets.this_column_is_read_only', 'this column is read-only'))
        row = live[rid]
        held = staged.get(rid)
        if held and not _same(held, row):
            sheets.fail(_i18n.msg('eng.sheets.stale_draft_edit', 'Discard stale unit drafts before editing those units again'))
        after = value(column, cell.get('value'))
        try:
            source = sheet_ops.number(row.get(column))
        except sheets.SheetError:
            source = None
        before = held['fields'].get(column) if held and column in held['fields'] else source
        if isinstance(before, float) and before.is_integer():
            before = int(before)
        held = staged.setdefault(rid, {**{k: row[k] for k in _IDENTITY}, 'fields': {}})
        if source is not None and source == after:
            held['fields'].pop(column, None)
        else:
            held['fields'][column] = after
        if not held['fields']:
            del staged[rid]
        try:
            same = sheet_ops.number(before) == after
        except sheets.SheetError:
            same = False
        if not same:
            changes.append({'id': rid, 'column': column, 'before': before, 'after': after})
    if not staged:
        p.pop('recruit_draft', None)
    return p, changes


def overlay(rows, project):
    """Show staged numbers on the live rows, and mark a row whose line moved."""
    held = drafts(project)
    for row in rows:
        draft = held.get(row['id'])
        if not draft:
            continue
        if not _same(draft, row):
            row['stale_draft'] = True
            continue
        for column, number in draft['fields'].items():
            row[column] = number
            if column in row.get('invalid_columns', []):
                row['invalid_columns'].remove(column)
        row['changed'] = True
    return rows


def stale(rows, project):
    """Staged rows whose line is gone or now holds another pool."""
    live = {row['id']: row for row in rows}
    return sorted((rid for rid, draft in drafts(project).items()
                   if rid not in live or not _same(draft, live[rid])), key=int)


def plan(mod, project):
    """The EDB text with every staged number written, worked out without writing."""
    path = getattr(mod, 'edb_path', None)
    edb = edb_balance.fresh_edb(mod)
    original = edb.to_text()
    lines = list(edb.lines)
    live = {row['id']: row for row in edb_balance.recruitments(edb)}
    changes = []
    for rid, draft in sorted(drafts(project).items(), key=lambda item: int(item[0])):
        row = live.get(rid)
        if row is None or not _same(draft, row):
            sheets.fail(_i18n.msg('eng.sheets.recruit_draft_stale',
                                  'Line {row} of the EDB no longer holds {unit} at {building} {level}: discard the staged recruitment edits and stage them again',
                                  row=rid, unit=draft['unit'], building=draft['building'], level=draft['level']))
        index = int(rid) - 1
        raw = lines[index]
        match = edb_balance.TOKENS.match(raw)
        if match is None:
            sheets.fail(_i18n.msg('eng.sheets.recruit_line_malformed', 'Line {row} of the EDB is not a whole recruit_pool line', row=rid))
        spans = list(re.finditer(r'\S+', match.group('nums')))
        for column, number in sorted(draft['fields'].items(), key=lambda kv: -NUMBERS.index(kv[0])):
            token = spans[NUMBERS.index(column)]
            start, end = match.start('nums') + token.start(), match.start('nums') + token.end()
            text = str(number) if isinstance(number, int) else format(number, '.12g')
            changes.append({'id': rid, 'unit': row['unit'], 'building': row['building'], 'level': row['level'],
                            'column': column, 'before': raw[start:end], 'after': text})
            raw = raw[:start] + text + raw[end:]
        lines[index] = raw
    text = ''.join(lines)
    if text == original:
        sheets.fail(_i18n.msg('eng.sheets.no_recruit_changes', 'There are no staged recruitment changes to apply'))
    source = hashlib.sha256(original.encode(buildings.ENCODING)).hexdigest()
    token = hashlib.sha256(json.dumps({'project': sheets.revision(project), 'edb': source},
                                      sort_keys=True).encode()).hexdigest()
    diff = list(difflib.unified_diff(original.splitlines(), text.splitlines(), lineterm='', n=0,
                                     fromfile=buildings.EDB_REL, tofile=buildings.EDB_REL))
    return {'plan_token': token, 'changes': changes, 'rows': len(drafts(project)), 'source_token': source,
            'diff': '\n'.join(diff[:500]), 'truncated': len(diff) > 500, 'text': text, 'path': path}


def preview(mod, project):
    result = plan(mod, project)
    return {k: v for k, v in result.items() if k not in ('text', 'path')}


def apply(mod, project, token):
    from .mod import Mod
    fresh = Mod(mod.root)
    result = plan(fresh, project)
    if not token or token != result['plan_token']:
        sheets.fail(_i18n.msg('eng.sheets.recruit_preview_changed', 'The recruitment preview changed; review it again before applying'))
    path = fresh.edb_path
    if not path.is_file():
        sheets.fail(_i18n.msg('eng.sheets.extract_the_edb_into_the_mod_before_applying_balance_changes',
                              'Extract the EDB into the mod before applying balance changes'))
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != result['source_token']:
        sheets.fail(_i18n.msg('eng.sheets.the_edb_changed_after_preview', 'The EDB changed after preview'))
    notes = [f"{c['unit']} at {c['building']}/{c['level']} line {c['id']}: {c['column']} {c['before']} -> {c['after']}"
             for c in result['changes']]
    edit = buildings.BuildingPlan(mod=fresh, line='Recruitment sheet edits', edb_text=result['text'],
                                  changes=notes, atomic_edb=True)
    try:
        return buildings.apply_edit(edit)
    except Exception:
        if path.read_bytes() != original:
            buildings._atomic_edb_write(path, original)
            from . import changesets
            changesets.refresh(fresh.root, [buildings.EDB_REL])
        raise
