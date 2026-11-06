"""Discover add-ons, read their settings and stage installations or removals.

Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor.
"""
from __future__ import annotations

import io
import json
import zipfile
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import i18n as _i18n, scriptwords, scriptfiles
from . import scriptcompat as SC, scriptbuilder as SB


@dataclass
class Setting:
    var: str
    kind: str
    default: object
    label: str
    help: str = ''
    choices: list = field(default_factory=list)
    signed: bool = False
    pick: str = ''


@dataclass
class Addon:
    key: str
    title: str
    summary: str
    game: str = 'both'
    settings: list = field(default_factory=list)
    integration: object = None
    path: object = None
    own: bool = False
    recipe: object = None
    prefix: str = ''

    @property
    def filename(self):
        return self.path.name if self.path else self.key+'.nut'

    def text(self):
        path = self.path or Path(__file__).parent / 'data' / 'addons' / self.filename
        if not path.is_file():
            raise ValueError(_i18n.msg('eng.scriptaddons.no_nut_script','no .nut script in {name}',name=path))
        return path.read_bytes().decode('utf-8',errors='replace')


def S(var,kind,default,label,**kw):
    return Setting(var,kind,default,label,kw.pop('help'),**kw)


ADDONS = [
    Addon('recruit_order','Recruitment Order','sort the available recruits by cost',settings=[S('RO_ENABLED','bool',True,'enable recruit sorting',help='sort available recruits by their recruitment cost when the recruitment panel opens'),
        S('RO_ORDER','choice','dearest','cost ordering',help='choose whether expensive or cheap units appear first in the recruitment list',choices=[('dearest','highest cost first'),('cheapest','lowest cost first')]), S('RO_ONE_PANEL','bool',True,'combine recruit panels',help='show available recruits together in one recruitment panel')],prefix='[ORDER]'),
    Addon('upkeep_x2','Upkeep x 2 (no huge armies)','multiply unit upkeep while keeping the original costs',settings=[S('FACTOR','float',2.0,'upkeep multiplier',help='multiply each unit upkeep cost by this factor; removing the add-on restores the recorded costs')],integration=scriptfiles.upkeep),
    Addon('one_recruit_grid','One Recruitment Grid (Medieval II)','use one recruitment list','medieval2',integration=scriptfiles.onegrid),
]


# Literal spans, rather than entire declarations, are replaced when a setting changes.
DECL = re.compile(r'^\ufeff?(?:(?:local|const)[ \t]+)?([A-Z][A-Z0-9_]*)[ \t]*(?:<-|=)[ \t]*',re.M)
STRING = r'"(?:\\.|[^"\\])*"'


def declarations(text):
    for m in DECL.finditer(text):
        start = m.end()
        pos = start
        depth, quoted, escaped = 0, False, False
        while pos < len(text):
            ch = text[pos]
            if quoted:
                if escaped: escaped = False
                elif ch == '\\': escaped = True
                elif ch == '"': quoted = False
            else:
                if ch == '"': quoted = True
                elif text[pos:pos+2] == '//':
                    if depth == 0: break
                    newline = text.find('\n',pos)
                    pos = len(text) if newline < 0 else newline
                    continue
                elif ch in '[{': depth += 1
                elif ch in ']}':
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
                elif depth == 0 and (ch in ';\r\n' or text[pos:pos+2] == '//'):
                    break
            pos += 1
        end = pos
        while end > start and text[end-1].isspace(): end -= 1
        yield m[1],start,end,text[start:end]


def unquote(text):
    try: return json.loads(text)
    except ValueError: return text.strip('"').replace('\\"','"').replace('\\\\','\\')


def code_literal(text):
    return re.sub(STRING+r'|//[^\r\n]*',lambda m: '' if m[0].startswith('//') else m[0],text)


def literal(text,kind):
    text = code_literal(text)
    if kind == 'bool': return text.strip() == 'true'
    if kind in ('int','float'):
        try: return int(text) if kind == 'int' else float(text)
        except ValueError: return 0 if kind == 'int' else 0.0
    if kind in ('text','choice'): return unquote(text.strip())
    if kind == 'list': return [unquote(m[0]) for m in re.finditer(STRING,text)]
    if kind == 'set': return re.findall(r'\b([A-Za-z_]\w*)\s*(?:=|<-)\s*true\b',text)
    return None


def read_values(addon,text):
    kinds = {s.var:s.kind for s in addon.settings}
    return {var:literal(raw,kinds[var]) for var,a,b,raw in declarations(text) if var in kinds}


def metadata(text):
    return re.findall(r'^\ufeff?[ \t]*//[ \t]*@(\w+)[ \t]*(.*?)[ \t\r]*$',text,re.M)


def discover():
    result = []
    builtin = {a.key for a in ADDONS}
    for path in SC.library().iterdir():
        if not path.is_file() or path.suffix.lower() != '.nut' or path.stat().st_size > 1048576 or path.stem.casefold() in builtin: continue
        text = path.read_bytes().decode('utf-8',errors='replace')
        tags = metadata(text)
        info = {k:v for k,v in tags if k not in ('label','pick')}
        comments = [m[1].strip() for m in re.finditer(r'^\s*//\s*([^@\r\n].*)$', '\n'.join(text.splitlines()[:30]),re.M)
                    if re.search('[A-Za-z]',m[1])]
        fallback = next((s.split(' - ')[0] for s in comments if ' - ' in s),path.stem.replace('_',' ').title())
        title = info.get('title') or fallback
        summary = info.get('summary') or next(iter(comments),_i18n.msg('eng.scriptaddons.script_summary','an add-on script ({name})',name=path.name))
        game = info.get('game','both')
        if game not in ('rome','medieval2','both'): game = 'both'
        allowed = [s.strip() for s in info.get('settings','').split(',') if s.strip()]
        signed = {s.strip() for s in info.get('signed','').split(',')}
        labels, picks = {}, {}
        for tag,value in tags:
            var,sep,tail = value.partition(' ')
            if tag == 'label': labels[var] = tail
            if tag == 'pick' and tail in ('chains','units','factions'): picks[var] = tail
        settings, seen = [], set()
        for var,start,end,raw in declarations(text):
            if var in seen or (allowed and var not in allowed): continue
            raw = code_literal(raw)
            kind = None
            if raw in ('true','false'): kind = 'bool'
            elif re.fullmatch(r'-?\d+',raw): kind = 'int'
            elif re.fullmatch(STRING,raw): kind = 'text'
            elif raw.startswith('[') and re.fullmatch(r'\[\s*(?:'+STRING+r'\s*,?\s*)*\]',raw): kind = 'list'
            elif raw.startswith('{') and re.fullmatch(r'\{\s*(?:[A-Za-z_]\w*\s*(?:=|<-)\s*true\s*,?\s*)*\}',raw): kind = 'set'
            if kind is None: continue
            seen.add(var)
            line_end = text.find('\n',end)
            after = text[end:line_end if line_end >= 0 else len(text)]
            help_text = after.partition('//')[2].strip()
            if not help_text:
                previous = text[:start].splitlines()[:-1]
                adjoining = []
                for line in reversed(previous):
                    match = re.match(r'^\s*//\s*(.*)',line)
                    if not match or match[1].startswith('@') or not re.search('[A-Za-z]',match[1]): break
                    adjoining.insert(0,match[1])
                help_text = ' '.join(adjoining)
            settings.append(Setting(var,kind,literal(raw,kind),labels.get(var,var.replace('_',' ').capitalize()),help_text,signed=var in signed,pick=picks.get(var,'')))
        prefix = next((literal(raw,'text') for var,a,b,raw in declarations(text)
                       if var == 'PREFIX' and re.fullmatch(STRING,raw)), '['+path.stem.upper()+']')
        recipe = SB.recipe_in(text)
        if recipe is not None:
            fields = {p:(b,n,k) for p,b,n,k,lab,value in SB.fields_of(recipe)}
            variables = {var:p for p,var in SB.setting_variables(recipe).items()}
            for setting in settings:
                if setting.var == 'MB_ON':
                    setting.help = _i18n.msg('eng.scriptaddons.module_enabled_help','run this campaign rule when its event occurs; turning it off keeps the module installed')
                elif setting.var == 'MB_ONCE':
                    setting.help = _i18n.msg('eng.scriptaddons.module_once_help','stop this rule after its first successful execution in the campaign')
                elif setting.var in variables and variables[setting.var] in fields:
                    field_path = variables[setting.var]
                    block, field_name, kind = fields[field_path]
                    category = 'cond' if field_path.startswith('ifs.') else 'act'
                    setting.help = scriptwords.word('field_help',f'{category}.{block.key}.{field_name}',SB.field_help(block,field_name,kind))
        result.append(Addon(path.stem,title,summary,game,settings,path=path,own=True,recipe=recipe,prefix=prefix))
    return sorted(result,key=lambda a:a.title.casefold())


def all_addons():
    return ADDONS + discover()


def target(addon,mod):
    if addon.integration:
        try: return Path(addon.integration.mark_path(mod))
        except ValueError: return Path(mod.data)/'export_descr_unit.txt'
    return SC.destination(mod,addon.filename)


def older(addon,mod):
    movable,conflicts = [],[]
    folder = SC.existing(mod.root,'script')
    if not folder.is_dir(): return movable,conflicts
    threshold = min(2,len(addon.settings))
    variables = {s.var for s in addon.settings}
    for path in folder.rglob('*'):
        if not path.is_file() or path.suffix.lower() != '.nut' or any(p.casefold() == 'modules' for p in path.relative_to(folder).parts[:-1]): continue
        try: text = path.read_bytes().decode('utf-8',errors='replace')
        except OSError: continue
        related = bool(addon.prefix and addon.prefix in text) or len(variables.intersection(v for v,a,b,r in declarations(text))) >= threshold
        if related:
            (movable if path.name.casefold() == addon.filename.casefold() else conflicts).append(path)
    return movable,conflicts


def row(addon,mod):
    installed, values, error = False, {}, ''
    try:
        if addon.integration:
            found = addon.integration.installed(mod)
            installed = found is not None
            values = found if installed else {s.var:s.default for s in addon.settings}
        else:
            path = target(addon,mod)
            if not path.is_file(): path = next(iter(older(addon,mod)[0]),path)
            installed = path.is_file()
            values = read_values(addon,path.read_bytes().decode('utf-8',errors='replace')) if installed else {s.var:s.default for s in addon.settings}
            if not installed: addon.text()
    except (OSError,ValueError) as e:
        installed, error = False,str(e)
        try: values = read_values(addon,addon.text())
        except (OSError,ValueError): values = {s.var:s.default for s in addon.settings}
    w = scriptwords.word
    return dict(key=addon.key,title=w('addon',addon.key,addon.title),summary=w('addon_help',addon.key,addon.summary),files=bool(addon.integration),
                own=addon.own,installed=installed,values=values,error=error,
                settings=[dict(var=s.var,kind=s.kind,label=w('setting',addon.key+'.'+s.var,s.label),help=w('setting_help',addon.key+'.'+s.var,s.help),
                               choices=[[v,w('choice',addon.key+'.'+s.var+'.'+str(v),lab)] for v,lab in s.choices]) for s in addon.settings])


def validate(addon,mod,values):
    errors = []
    names = SC.names(mod)
    for s in addon.settings:
        if s.var not in values: continue
        v = values[s.var]
        def bad(text): errors.append(_i18n.msg('eng.scriptaddons.setting_error', '{label}: {detail}', label=s.label, detail=text))
        if s.kind == 'int':
            if type(v) is not int or (not s.signed and v < 0): bad(_i18n.msg('eng.scriptaddons.whole_number', 'use a whole number') if s.signed else _i18n.msg('eng.scriptaddons.nonnegative_integer', 'use a whole number of zero or more'))
        elif s.kind == 'float':
            if type(v) not in (int,float) or not v >= 0: bad(_i18n.msg('eng.scriptaddons.use_a_number_of_zero_or_more', 'use a number of zero or more'))
        elif s.kind == 'choice' and v not in dict(s.choices): bad(_i18n.msg('eng.scriptaddons.choose_one_of_the_offered_values', 'choose one of the offered values'))
        elif s.kind in ('set','list'):
            if not isinstance(v,list) or any(not isinstance(x,str) for x in v): bad(_i18n.msg('eng.scriptaddons.use_a_list_of_names', 'use a list of names'))
            else:
                if s.kind == 'set' and any(not re.fullmatch(r'[A-Za-z_]\w*',x) for x in v): bad(_i18n.msg('eng.scriptaddons.names_must_start_with_a_letter_or_underscore_and_contain_letters_digits_or_underscores', 'names must start with a letter or underscore and contain letters, digits or underscores'))
                available = {x.casefold() for x in names.get(s.pick,[])}
                if s.pick in ('chains','units') and available:
                    wrong = [x for x in v if x.casefold() not in available]
                    if wrong: bad(_i18n.msg('eng.scriptaddons.unknown_names', 'not in {file}: {names}', file='export_descr_buildings.txt' if s.pick == 'chains' else 'export_descr_unit.txt', names=', '.join(wrong)))
    if errors: raise ValueError(_i18n.msg('eng.scriptaddons.validation_errors','{errors}',errors='; '.join(errors)))


def render(addon,text,values):
    settings = {s.var:s for s in addon.settings}
    spans = {var:(a,b,raw) for var,a,b,raw in declarations(text)}
    edits = []
    for var,value in values.items():
        if var not in settings: continue
        s = settings[var]
        if var not in spans:
            raise ValueError(_i18n.msg('eng.scriptaddons.no_var_line','the script has no declaration for {var}',var=var))
        a,b,raw = spans[var]
        normalized = bool(value) if s.kind == 'bool' else value
        if normalized == literal(raw,s.kind): continue
        if s.kind == 'bool': replacement = 'true' if value else 'false'
        elif s.kind == 'float': replacement = str(float(value))
        elif s.kind == 'int': replacement = str(int(value))
        elif s.kind in ('text','choice'): replacement = json.dumps(str(value),ensure_ascii=False)
        elif s.kind == 'list': replacement = '['+', '.join(json.dumps(x,ensure_ascii=False) for x in value)+']'
        elif s.kind == 'set':
            indentation = re.search(r'\n([ \t]+)\w',raw)
            if indentation:
                nl = '\r\n' if '\r\n' in raw else '\n'
                replacement = '{'+nl+''.join(indentation[1]+x+' = true,'+nl for x in value)+'}'
            else: replacement = '{ '+', '.join(x+' = true' for x in value)+' }'
        edits.append((a,b,replacement))
    for a,b,replacement in sorted(edits,reverse=True): text = text[:a]+replacement+text[b:]
    text = re.sub(r'(\blocal\s+CE_GAME\s*=\s*)"auto"',r'\1"medieval2"',text)
    return text


TEST_MARKER = "// @put_in_by CE_Test - the editor's test mod (Add-ons > Scripts in the game takes it out)"


def plan(addon,mod,action,values,marker=False):
    p = SC.Plan(mod)
    values = values or {}
    if addon.integration:
        if action == 'remove': addon.integration.plan_remove(p)
        else: addon.integration.plan_install(p,**{k.lower():v for k,v in values.items()})
        return p
    dest = target(addon,mod)
    movable,conflicts = older(addon,mod)
    if action == 'remove':
        p.delete(dest,_i18n.msg('eng.scriptaddons.removed', 'the {title} add-on taken out', title=addon.title))
        for old in movable: p.delete(old,_i18n.msg('eng.scriptaddons.older_removed', 'an older copy of the {title} add-on taken out', title=addon.title))
    else:
        validate(addon,mod,values)
        if conflicts:
            raise ValueError(_i18n.msg('eng.scriptaddons.duplicate_code', '{title} code is already in {paths}; it would run twice. Remove the pasted code before installing this add-on.', title=addon.title, paths=', '.join(str(x.relative_to(mod.root)) for x in conflicts)))
        source = addon.text()
        if addon.recipe is not None:
            current = read_values(addon,source)
            current.update(values)
            source = SB.generate(addon.recipe,mod)
            text = render(addon,source,current)
        else:
            text = render(addon,source,values)
        if marker and TEST_MARKER not in text:
            nl = '\r\n' if '\r\n' in text else '\n'
            text = text.rstrip('\r\n') + nl + TEST_MARKER + nl
        p.binary(dest,text.encode('utf-8'))
        for old in movable:
            p.delete(old,_i18n.msg('eng.scriptaddons.older_moved', 'an older copy of {title} outside script/modules - it would run twice; the add-on is in {path} now', title=addon.title, path=p.display(dest)))
        if addon.recipe is not None: SB.stage_messages(p,addon.recipe,values)
        if dest.is_file():
            p.note(None,_i18n.msg('eng.scriptaddons.updated','updated {name}: {where}',name=addon.title,where=p.display(dest)))
        else:
            p.note(None,_i18n.msg('eng.scriptaddons.put_in','put in {name}: {where}',name=addon.title,where=p.display(dest)))
    return p


def import_addon(name, raw):
    """Store a supplied native script in the user library, preserving settings."""
    builtin = {a.key for a in ADDONS}
    if Path(name).stem.casefold() in builtin:
        raise ValueError(_i18n.msg('eng.scriptaddons.built_in','{name} is built in',name=name))
    if name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                member = next((m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith('.nut')),None)
                if member is None:
                    raise ValueError(_i18n.msg('eng.scriptaddons.no_nut_script','no .nut script in {name}',name=name))
                if member.file_size > 1048576:
                    raise ValueError(_i18n.msg('eng.scriptaddons.over_1_mb','{name} is over 1 MB - not a script',name=member.filename))
                name = member.filename.replace('\\','/').rsplit('/',1)[-1]
                raw = archive.read(member)
        except zipfile.BadZipFile:
            raise ValueError(_i18n.msg('eng.scriptaddons.an_add_on_is_a_squirrel','an add-on is a Squirrel script (.nut) or a zip with one - REX and M2EX load those')) from None
    if not name.lower().endswith('.nut'):
        raise ValueError(_i18n.msg('eng.scriptaddons.an_add_on_is_a_squirrel','an add-on is a Squirrel script (.nut) or a zip with one - REX and M2EX load those'))
    if len(raw) > 1048576:
        raise ValueError(_i18n.msg('eng.scriptaddons.over_1_mb','{name} is over 1 MB - not a script',name=name))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name in ('.','..'):
        raise ValueError(_i18n.msg('eng.scriptaddons.bad_script_name',"{name}: a script's name is letters, digits, _ - and . only",name=name))
    if Path(name).stem.casefold() in builtin:
        raise ValueError(_i18n.msg('eng.scriptaddons.built_in_already','{name} is built in already (it is in the list)',name=name))
    path = SC.library() / name
    old = next((a for a in discover() if a.path.name.casefold() == name.casefold()),None)
    text = raw.decode('utf-8-sig',errors='replace')
    notes = []
    if old:
        path = old.path
        # Only carry settings declared by both versions. A changed literal kind
        # cannot safely inherit the previous value.
        incoming_settings = []
        for var,a,b,value in declarations(text):
            setting = next((s for s in old.settings if s.var == var),None)
            if setting is not None:
                incoming_settings.append(Setting(var,setting.kind,literal(value,setting.kind),var))
        incoming = Addon(path.stem,path.stem,'',settings=incoming_settings)
        values = read_values(old,old.text())
        try:
            text = render(incoming,text,values)
        except (ValueError,TypeError) as error:
            notes.append(_i18n.msg('eng.scriptaddons.settings_not_kept',"{name}: its settings could not be kept ({why}) - put in with this version's defaults",name=name,why=str(error)))
    path.write_text(text,encoding='utf-8')
    notes.append(_i18n.msg('eng.scriptaddons.updated','updated {name}: {where}',name=name,where=path) if old else _i18n.msg('eng.scriptaddons.put_in','put in {name}: {where}',name=name,where=path))
    return dict(key=path.stem, notes=notes)
