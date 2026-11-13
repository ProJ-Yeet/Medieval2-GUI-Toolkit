"""Phase 107: a mercenary design's unit put into chosen pools of descr_mercenaries.txt.

The design carries the upstream builder's pool settings as inputs (``merc_pools``,
``merc_experience``, ``merc_cost``, ``merc_replenish_min``/``_max``,
``merc_maximum``, ``merc_initial``). This turns them into one save of the
campaign's mercenary file through ``mercpools``: a pool that has no line for the
unit gets one, a pool that has exactly one gets its five numbers changed and its
gates kept, and every other line, region and pool stays as it was. The write is
``mercpools.apply``, so it has the same backup and Log Undo as the map's own
mercenary panel. Repeating an apply changes nothing.

Only the Mercenary subtype puts a unit in a pool: a design without it is refused
before the file is read. The armour and weapon levels the upstream builder keeps
for M2EX (``merc_armour``, ``merc_weapon_lvl``) have no verified syntax in the
game's file, so they stay in the design and are never written.
"""
from __future__ import annotations

from . import builder_contract as contract, mercpools, unit_sheets as sheets
from . import i18n as _i18n

#: the upstream builder's own defaults for a new pool line
DEFAULTS = {'merc_experience': 0, 'merc_cost': 500, 'merc_replenish_min': 0.1,
            'merc_replenish_max': 0.2, 'merc_maximum': 2, 'merc_initial': 1}
_WHOLE = {'merc_experience': 'exp', 'merc_cost': 'cost',
          'merc_maximum': 'max', 'merc_initial': 'initial'}


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float('inf') else None


def pools_of(inputs):
    """``merc_pools`` as a list: the upstream form keeps it as comma text."""
    raw = inputs.get('merc_pools') or []
    items = raw.split(',') if isinstance(raw, str) else raw if isinstance(raw, list) else []
    seen = []
    for item in items:
        name = str(item).strip()
        if name and name not in seen:
            seen.append(name)
    return seen


def settings(design):
    """``(line values, pools, errors)`` out of a design's inputs."""
    packet = contract.validate_design(design)
    inputs = contract.effective_inputs(packet)
    if inputs.get('trait_mercenary') is not True:
        return None, [], [_i18n.msg('eng.builder.merc_not_mercenary',
                                    'This design is not a mercenary: tick the Mercenary subtype to put it in pools')]
    errors, values = [], {}
    for key, default in DEFAULTS.items():
        value = _number(inputs.get(key, default))
        if key in _WHOLE:
            if value is None or value < 0 or value != int(value):
                errors.append(_i18n.msg('eng.builder.merc_whole', '{field} has to be a whole number, zero or more',
                                        field=_WHOLE[key]))
                continue
            values[_WHOLE[key]] = int(value)
        elif value is None or value < 0:
            errors.append(_i18n.msg('eng.builder.merc_replenish',
                                    'Replenishment needs a low rate of zero or more and a high rate no lower'))
        else:
            values[key] = value
    if 'merc_replenish_min' in values and 'merc_replenish_max' in values:
        low, high = values.pop('merc_replenish_min'), values.pop('merc_replenish_max')
        if high < low:
            errors.append(_i18n.msg('eng.builder.merc_replenish',
                                    'Replenishment needs a low rate of zero or more and a high rate no lower'))
        values['replenish'] = [_fmt(low), _fmt(high)]
    if values.get('exp', 0) > 9:
        errors.append(_i18n.msg('eng.builder.merc_exp', 'Experience in a pool runs from 0 to 9'))
    if 'max' in values and 'initial' in values and values['initial'] > values['max']:
        errors.append(_i18n.msg('eng.builder.merc_initial', 'The starting number cannot be above the maximum'))
    pools = pools_of(inputs)
    if not pools:
        errors.append(_i18n.msg('eng.builder.merc_no_pools', 'Pick at least one pool'))
    return values, pools, errors


def _fmt(number):
    return str(int(number)) if number == int(number) else repr(round(number, 6))


def _same(name, unit):
    return ' '.join(name.split()).lower() == ' '.join(unit.split()).lower()


def _campaign(body):
    from . import campstrat
    return str(body.get('campaign') or campstrat.DEFAULT_CAMPAIGN)


def _unit(mod, body):
    unit = body.get('unit')
    if not isinstance(unit, str) or unit not in sheets.live_units(mod):
        raise contract.ContractError('unit_identity')
    return unit


def load(mod, body):
    """The campaigns that have a mercenary file, and one campaign's pools."""
    from . import campstrat
    unit = body.get('unit') or ''
    campaigns = [c for c in campstrat.campaign_paths(mod) if mercpools.path_for(mod, c).is_file()]
    campaign = _campaign(body)
    if campaign not in campaigns and campaigns:
        campaign = campaigns[0]
    try:
        mf, _ = mercpools.read(mod, campaign)
    except mercpools.MercError as e:
        return {'campaigns': campaigns, 'campaign': campaign, 'pools': [], 'error': str(e)}
    return {'campaigns': campaigns, 'campaign': campaign, 'pools': [
        {'name': p.name, 'regions': len(p.regions),
         'has_unit': sum(1 for u in p.units if unit and _same(u.name, unit))} for p in mf.pools]}


def plan(mod, body):
    """One save of the mercenary file, worked out without touching the disk."""
    unit = _unit(mod, body)
    p = mercpools.MercPlan(mod=mod, campaign=_campaign(body), action='builder_pools')
    values, pools, errors = settings(body.get('design'))
    if errors:
        p.errors.extend(errors)
        return p
    try:
        mf, original = mercpools.read(mod, p.campaign)
    except mercpools.MercError as e:
        p.errors.append(e.message)
        return p
    p.path = mercpools.path_for(mod, p.campaign)
    names = [q.name for q in mf.pools]
    text = original
    try:
        for name in pools:
            q = mercpools._need_pool(mf, name)
            lines = [i for i, u in enumerate(q.units) if _same(u.name, unit)]
            if len(lines) > 1:
                p.errors.append(_i18n.msg('eng.builder.merc_twice',
                                          '{pool} has {count} lines for {unit}: change them in the campaign map\'s mercenary panel',
                                          pool=name, count=len(lines), unit=unit))
                continue
            if lines:
                was = q.units[lines[0]].record()
                edits = {k: v for k, v in values.items()
                         if (was.get(k) if k != 'replenish' else [_fmt(x) for x in (was.get(k) or [])]) != v}
                if not edits:
                    continue
                text = mercpools.edit_unit(mf, name, lines[0], edits)
                now = mercpools.parse_text(text).pool(name).units[lines[0]].record()
                for k in edits:
                    p.changes.append(f"{name}: {unit} {k} {mercpools._show(was.get(k))} -> {mercpools._show(now.get(k))}")
            else:
                text = mercpools.add_unit(mf, name, dict(values, name=unit))
                new = mercpools.parse_text(text).pool(name).units[-1].record()
                p.changes.append(f"{name}: + {mercpools._say(new)}")
            mf = mercpools.parse_text(text)
    except mercpools.MercError as e:
        p.errors.append(e.message)
    if p.errors:
        return p
    after = mercpools.parse_text(text)
    if [q.name for q in after.pools] != names:
        p.errors.append(_i18n.msg('eng.mercpools.refused_the_save_would_change_which',
                                  'refused: the save would change which pools the file has'))
        return p
    # Every line that is not this unit's must read back as it was.
    others = lambda f: [(q.name, u.record()) for q in f.pools for u in q.units if not _same(u.name, unit)]
    if others(after) != others(mercpools.parse_text(original)):
        p.errors.append(_i18n.msg('eng.builder.merc_stray', 'Refused: the save would change another unit\'s line'))
        return p
    for q in after.pools:
        for u in q.units:
            if _same(u.name, unit) and u.fault:
                p.errors.append(f"{q.name}: {u.name} - {u.fault}")
    if not p.errors and text != original:
        p.text = text
    elif not p.errors:
        p.errors.append(_i18n.msg('eng.mercpools.nothing_to_change', 'nothing to change'))
    return p


def service(mod, action, body):
    if action == 'merc_load':
        return load(mod, body)
    p = plan(mod, body)
    if action == 'merc_plan':
        return p.payload()
    if action == 'merc_apply':
        if p.errors:
            return p.payload()
        done = mercpools.apply(p)
        return dict(p.payload(), id=done['id'], applied=True)
    raise contract.ContractError('designer_action')
