"""Explicit, previewed sheet interchange. OOXML uses only the standard library.

See docs/SHEET_INTERCHANGE.md for mappings, blank semantics and formula limits.
No archive is extracted and no spreadsheet code, links or macros are executed.
"""
from __future__ import annotations
import ast
import base64
import copy
import csv
import io
import json
import math
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from . import i18n as _i18n, sheet_ops as ops, unit_sheets as sheets

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
VIEWS = ('classification', 'base', 'attributes', 'soft', *('rules:'+k for k in sheets.RULE_KEYS))
MAX_BYTES = 20 * 1024 * 1024
MAX_CELLS = 250000


def refuse(code):
    sheets.fail(_i18n.msg('sheets.interchange_invalid', 'Invalid interchange data: {code}', code=code))


def column_name(index):
    name = ''
    while index >= 0:
        index, rem = divmod(index, 26)
        name = chr(65+rem) + name
        index -= 1
    return name


def coordinates(address):
    m = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', address)
    if not m:
        refuse('cell_address')
    col = 0
    for char in m[1]:
        col = col*26+ord(char)-64
    row = int(m[2])
    if col > 16384 or row > 1048576:
        refuse('cell_address')
    return row, col-1


def xml(blob):
    if b'<!DOCTYPE' in blob.upper() or b'<!ENTITY' in blob.upper():
        refuse('xml_declaration')
    return ET.fromstring(blob)


def _xlsx(text):
    blob = base64.b64decode(text, validate=True)
    if len(blob) > MAX_BYTES:
        refuse('file_size')
    tables = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if (len(z.infolist()) > 10000 or sum(x.file_size for x in z.infolist()) > 80*1024*1024
                or len(z.namelist()) != len(set(z.namelist()))):
            refuse('archive_size')
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(t.text or '' for t in e.iter('{'+NS+'}t'))
                      for e in xml(z.read('xl/sharedStrings.xml'))]
        relationships = {e.get('Id'):e for e in xml(z.read('xl/_rels/workbook.xml.rels'))}
        book = xml(z.read('xl/workbook.xml'))
        count = 0
        for element in book.findall('{'+NS+'}sheets/{'+NS+'}sheet'):
            relation = relationships.get(element.get('{'+REL+'}id'))
            if relation is None or not relation.get('Type','').endswith('/worksheet'):
                continue
            if relation.get('TargetMode') == 'External':
                refuse('external_worksheet')
            path = relation.get('Target','')
            path = posixpath.normpath(path.lstrip('/') if path.startswith('/') else 'xl/'+path)
            if not path.startswith('xl/'):
                refuse('worksheet_path')
            cells = {}
            # Iteration clears empty/formatted cells immediately. dimension is never read.
            sheet_xml = z.read(path)
            if b'<!DOCTYPE' in sheet_xml.upper() or b'<!ENTITY' in sheet_xml.upper():
                refuse('xml_declaration')
            for _, cell in ET.iterparse(io.BytesIO(sheet_xml), events=('end',)):
                if cell.tag != '{'+NS+'}c':
                    if cell.tag == '{'+NS+'}row':
                        cell.clear()
                    continue
                value = cell.find('{'+NS+'}v')
                formula = cell.find('{'+NS+'}f')
                inline = cell.find('{'+NS+'}is')
                if value is None and formula is None and inline is None:
                    cell.clear()
                    continue
                address = cell.get('r','')
                coordinates(address)
                if address in cells:
                    refuse('duplicate_cell')
                kind = cell.get('t')
                raw = value.text if value is not None else None
                if kind == 's':
                    raw = shared[int(raw)]
                elif inline is not None:
                    raw = ''.join(t.text or '' for t in inline.iter('{'+NS+'}t'))
                elif raw is not None and kind not in ('str','e','d'):
                    raw = float(raw)
                    if not math.isfinite(raw):
                        refuse('nonfinite_cell')
                    if raw.is_integer():
                        raw = int(raw)
                    if kind == 'b':
                        raw = bool(raw)
                if formula is None and raw in (None,''):
                    cell.clear()
                    continue
                entry = {'value':raw}
                if formula is not None:
                    entry['formula'] = formula.text or ''
                    entry['formula_type'] = formula.get('t','normal')
                    entry['cache'] = raw
                cells[address] = entry
                count += 1
                if count > MAX_CELLS:
                    refuse('cell_count')
                cell.clear()
            tables.append({'name':element.get('name'), 'cells':cells})
    if not tables or len({t['name'] for t in tables}) != len(tables):
        refuse('worksheet_names')
    return tables


def read_tables(fmt, text):
    if not isinstance(text, str) or len(text) > MAX_BYTES*4//3+4:
        refuse('file_size')
    try:
        if fmt == 'xlsx':
            return _xlsx(text)
        if fmt == 'csv':
            cells = {}
            for r,row in enumerate(csv.reader(io.StringIO(text.lstrip('\ufeff')),strict=True),1):
                if r>1048576 or len(row)>16384:refuse('cell_count')
                for c,value in enumerate(row):
                    if value!='':cells[column_name(c)+str(r)]={'value':value}
                if len(cells)>MAX_CELLS:refuse('cell_count')
            return [{'name':'CSV', 'cells':cells}]
        if fmt == 'edu_json':
            data = json.loads(text)
            if not isinstance(data,dict) or not data or not all(isinstance(v,dict) for v in data.values()):
                refuse('fynn_shape')
            headers = ['Name', *sorted({k for v in data.values() for k in v if k != 'Name'})]
            cells = {column_name(c)+'1':{'value':h} for c,h in enumerate(headers)}
            for r,(uid,row) in enumerate(data.items(),2):
                if row.get('Type',uid) != uid or row.get('Name',uid) != uid:
                    refuse('fynn_identity')
                for c,h in enumerate(headers):
                    if h == 'Name' or h in row:
                        cells[column_name(c)+str(r)] = {'value':uid if h=='Name' else row[h]}
            if len(cells) > MAX_CELLS:
                refuse('cell_count')
            return [{'name':'Fynn EDU', 'cells':cells}]
        refuse('format')
    except (ValueError, KeyError, IndexError, TypeError, zipfile.BadZipFile, ET.ParseError, csv.Error, RuntimeError, OSError) as error:
        if isinstance(error, sheets.SheetError):
            raise
        refuse('file_structure')


def row_values(table):
    rows = {}
    for address,cell in table['cells'].items():
        r,c = coordinates(address)
        rows.setdefault(r,{})[c] = cell
    return rows


def inspect(body):
    result = []
    for table in read_tables(body.get('format'),body.get('text')):
        rows = row_values(table)
        sample = []
        for r,values in sorted(rows.items())[:12]:
            sample.append({'number':r, 'values':[values.get(c,{}).get('value','') for c in range(max(values)+1)]})
        result.append({'name':table['name'], 'rows':sample, 'populated_rows':len(rows)})
    return {'sheets':result, 'views':list(VIEWS)}


def calculate(table):
    """Bounded numeric arithmetic and same-sheet A1 references, never eval()."""
    cells = table['cells']
    memo, active, issues, supported = {}, set(), [], set()

    class FormulaError(Exception):
        pass

    def value(address):
        if address in memo:
            return memo[address]
        if address in active or len(active)>64:
            raise FormulaError('cyclic_formula')
        cell = cells.get(address,{})
        if 'formula' not in cell:
            raw = cell.get('value')
            if type(raw) in (int,float) and math.isfinite(raw):
                return raw
            if isinstance(raw,str) and raw.strip():
                try:
                    n = float(raw)
                    if math.isfinite(n):
                        return n
                except ValueError:
                    pass
            raise FormulaError('missing_input')
        active.add(address)
        try:
            if cell.get('formula_type','normal') != 'normal' or len(cell['formula'])>1024:
                raise FormulaError('unsupported_formula')
            formula = cell['formula'].lstrip('=')
            # Strip only A1 dollar anchors. Other dollar signs stay invalid syntax.
            formula = re.sub(r'\$?([A-Z]{1,3})\$?([1-9][0-9]*)',r'\1\2',formula)
            try:
                tree = ast.parse(formula,mode='eval')
            except (SyntaxError,ValueError):
                raise FormulaError('unsupported_formula')
            if len(list(ast.walk(tree)))>64:
                raise FormulaError('unsupported_formula')

            def node(n):
                if isinstance(n,ast.Expression):
                    return node(n.body)
                if isinstance(n,ast.Constant) and type(n.value) in (int,float):
                    return n.value
                if isinstance(n,ast.Name) and re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}',n.id):
                    coordinates(n.id)
                    return value(n.id)
                if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
                    return node(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
                if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
                    a,b = node(n.left),node(n.right)
                    if isinstance(n.op,ast.Add):return a+b
                    if isinstance(n.op,ast.Sub):return a-b
                    if isinstance(n.op,ast.Mult):return a*b
                    if b==0:raise FormulaError('division_by_zero')
                    return a/b
                raise FormulaError('unsupported_formula')
            result = node(tree)
            if not math.isfinite(result):
                raise FormulaError('nonfinite_formula')
            supported.add(address)
            memo[address] = result
            return result
        finally:
            active.remove(address)

    for address,cell in cells.items():
        if 'formula' not in cell:
            continue
        def issue(code):
            issues.append({'sheet':table['name'],'cell':address,'name':cell['formula'],'code':code})
        try:
            result = value(address)
            cache = cell.get('cache')
            if cache is not None and (type(cache) not in (int,float) or not math.isclose(result,cache,rel_tol=1e-10,abs_tol=1e-10)):
                issue('stale_cache')
        except (FormulaError,OverflowError,RecursionError) as error:
            result = None
            issue(str(error) if isinstance(error,FormulaError) else 'nonfinite_formula')
        if cell.get('cache') is None:
            issue('missing_cache')
        cell['value'] = result
        cell['supported'] = address in supported
    return issues


def resolve_mapping(plan, headers):
    mapping = plan.get('mapping')
    if not isinstance(mapping,dict) or not mapping:
        refuse('explicit_mapping_required')
    result = {}
    for target,source in mapping.items():
        if not isinstance(target,str) or not target.strip():
            refuse('mapping_target')
        multiple = isinstance(source,list)
        if multiple and (target not in ops.FIELDS or ops.FIELDS[target][2]!='list' or not source):
            refuse('mapping_column')
        indices = []
        for item in source if multiple else [source]:
            if isinstance(item,str):
                if headers.count(item) != 1:
                    refuse('ambiguous_header')
                item = headers.index(item)
            if (type(item) is not int or not 0<=item<len(headers) or item in mapped_columns(result)
                    or item in indices):
                refuse('mapping_column')
            indices.append(item)
        result[target] = indices if multiple else indices[0]
    return result


def mapped_columns(mapping):
    return {i for value in mapping.values() for i in (value if isinstance(value,list) else [value])}


def label(headers,index):
    text = str(headers[index])
    if text and headers.count(headers[index])==1:return text
    result = (text or 'Column')+' ['+column_name(index)+']'
    while result in [str(h) for h in headers]:
        result += ' ['+column_name(index)+']'
    return result


def token(mod,project,body):
    return sheets.revision({'project':sheets.revision(project),'source':sheets.source_token(mod),
        **{k:body.get(k) for k in ('format','text','plans')}})


def prepare(mod,project,body):
    tables = {t['name']:t for t in read_tables(body.get('format'),body.get('text'))}
    plans = body.get('plans')
    if not isinstance(plans,list) or not plans or len(plans)>32:
        refuse('explicit_mapping_required')
    p = copy.deepcopy(project)
    cells, changes, ignored, issues, identities, fields = [], [], [], [], set(), set()
    targets, selected_sheets, selected_views = set(),set(),set()
    live = sheets.live_units(mod)
    layouts = p.setdefault('interchange',{})
    for plan in plans:
        if not isinstance(plan,dict):refuse('mapping_plan')
        name,view,header_row = plan.get('sheet'),plan.get('view'),plan.get('header_row')
        if (name not in tables or view not in VIEWS or type(header_row) is not int
                or header_row<1 or name in selected_sheets or view in selected_views):
            refuse('mapping_plan')
        selected_sheets.add(name);selected_views.add(view)
        table = tables[name]
        issues.extend(calculate(table))
        rows = row_values(table)
        if header_row not in rows:refuse('header_row')
        width = max(rows[header_row])+1
        headers = [rows[header_row].get(c,{}).get('value','') for c in range(width)]
        if any(isinstance(h,(dict,list)) for h in headers):refuse('headers')
        mapping = resolve_mapping(plan,headers)
        kind = ops.rule_kind(view)
        required = sheets.RULE_KEYS[kind] if kind else ('id',)
        if not set(required)<=set(mapping):refuse('identity_mapping')
        if not kind and any(k not in ops.FIELDS and k not in ops.META and k!='id' for k in mapping):
            refuse('mapping_target')
        if kind and any(k in ops.RULE_RESERVED-{'id'} for k in mapping):refuse('mapping_target')
        row_ids = {}
        seen = set()
        rule_rows = p['rules'][kind] if kind else []
        existing = {tuple(str(row.get(k,'')).strip() for k in required):row for row in rule_rows}
        if kind and len(existing)!=len(rule_rows):refuse('duplicate_rule_key')
        schema = {c['name']:c for c in p['rule_schema'][kind]} if kind else {}
        for r,values in sorted(rows.items()):
            if r<=header_row:continue
            if max(values)>=width and any(c>=width and v.get('value') not in (None,'') for c,v in values.items()):
                refuse('row_width')
            def get(target):
                source = mapping[target]
                if not isinstance(source,list):return values.get(source,{}).get('value','')
                items = [values.get(c,{}).get('value','') for c in source]
                if not any(v not in (None,'') for v in items):return ''
                result = []
                for item in items:
                    if item in (None,'','no','[]'):continue
                    if not isinstance(item,str):refuse('list_value')
                    result.append(item)
                return result
            key = tuple(str(get(k) if get(k) is not None else '').strip() for k in required)
            if not all(key) or not kind and key[0] not in live:
                ignored.append({'sheet':name,'row':r,'id':key,'code':'unmatched_identity'})
                continue
            if key in seen:refuse('duplicate_identity')
            seen.add(key)
            if kind:
                dest = existing.get(key)
                if dest is None:
                    dest = {'id':'rule-'+sheets.revision({'kind':kind,'key':key})[:32]}
                    rule_rows.append(dest)
                uid = dest['id']
            else:
                uid = key[0]
            identities.add(uid);row_ids[str(r)] = uid
            for target,c in mapping.items():
                indices = c if isinstance(c,list) else [c]
                for index in indices:
                    if 'formula' in values.get(index,{}):
                        refuse('formula_must_be_derived:'+name+'!'+column_name(index)+str(r))
                if target=='id':continue
                if (uid,target) in targets:refuse('duplicate_target')
                targets.add((uid,target));fields.add(target)
                value = get(target)
                if kind:
                    if target not in schema:
                        definition = {'name':target,'type':'text' if target in required else 'number','key':target in required}
                        p['rule_schema'][kind].append(definition);schema[target]=definition
                    value = ops.rule_value(schema[target],value)
                    changes.append({'id':uid,'column':target,'before':dest.get(target,''),'after':value})
                    dest[target]=value
                else:
                    # Empty native cells mean unchanged. Lists clear only with explicit [].
                    if value in (None,'') and target in ops.FIELDS:
                        continue
                    if target in ops.FIELDS and ops.FIELDS[target][2]=='list' and isinstance(value,str) and value.startswith('['):
                        try:value=json.loads(value)
                        except ValueError:refuse('list_value')
                        if not isinstance(value,list):refuse('list_value')
                    cells.append({'id':uid,'column':target,'value':value})
            extra = (p.setdefault('interchange_rule_extras',{}).setdefault(kind,{}).setdefault(uid,{})
                     if kind else p['units'].setdefault(uid,{'annotations':{},'extra':{}}).setdefault('extra',{}))
            for c in range(width):
                if c not in mapped_columns(mapping):
                    extra[label(headers,c)] = values.get(c,{}).get('value','')
        if not seen and not kind:refuse('no_valid_units')
        if kind:
            sheets.validate_rules(kind,rule_rows)
        layouts[view] = {'table':table,'header_row':header_row,'mapping':mapping,'headers':headers,'rows':row_ids}
    if cells:
        # Chunking does not weaken atomicity: only this private copy is changed.
        for start in range(0,len(cells),10000):
            p,native_changes = ops.stage_cells(mod,p,cells[start:start+10000],allow_clear=True)
            changes.extend(native_changes)
    sheets.validate_project(p)
    report = {'ids':sorted(identities),'fields':sorted(fields),'changes':changes,'ignored':ignored,
              'formula_issues':issues,'preview_token':token(mod,project,body)}
    return p,report


def display(value):
    return json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else '' if value is None else value


def updated_table(saved, live, strict=True):
    table = copy.deepcopy(saved['table'])
    for r,uid in saved['rows'].items():
        if uid not in live:refuse('removed_identity')
        for target,c in saved['mapping'].items():
            value = live[uid].get(target)
            if isinstance(c,list):
                items = value if isinstance(value,list) else []
                if strict and len(items)>len(c):refuse('list_exceeds_imported_columns:'+target)
                for i,col in enumerate(c):
                    raw = items[i] if i<len(items) else '[]' if i==0 and value==[] else ''
                    table['cells'][column_name(col)+r] = {'value':raw}
            else:
                table['cells'][column_name(c)+r] = {'value':display(value)}
    return table


def derived_records(rows,project,rule=None):
    """Re-evaluate imported derived cells against staged native values by ID."""
    live = {r['id']:r for r in rows}
    if rule:
        extras = project.get('interchange_rule_extras',{}).get(rule,{})
        names = {k for values in extras.values() for k in values}
        for uid,row in live.items():
            row.update({'extra:'+key:extras.get(uid,{}).get(key,'') for key in names})
    for uid,row in live.items():
        for column,value in project['draft'].get(uid,{}).items():
            if value==[]:row[column]=[]
    for view,saved in project.get('interchange',{}).items():
        if rule and view!='rules:'+rule or not rule and view.startswith('rules:'):continue
        # Removed units retain project metadata but never become active records.
        present = dict(saved, rows={r:uid for r,uid in saved['rows'].items() if uid in live})
        table = updated_table(present,live,strict=False)
        issues = calculate(table)
        for r,uid in present['rows'].items():
            for c in range(len(saved['headers'])):
                entry = table['cells'].get(column_name(c)+r,{})
                if 'formula' in entry:
                    key = 'extra:'+label(saved['headers'],c)
                    live[uid][key] = entry.get('value')
                    if key not in live[uid].setdefault('derived_columns',[]):live[uid]['derived_columns'].append(key)
                    if not entry.get('supported'):live[uid]['invalid_columns'].append(key)
            live[uid].setdefault('formula_issues',[]).extend(x for x in issues if coordinates(x['cell'])[0]==int(r))


def export_table(mod,project,view,layout):
    if view not in VIEWS:refuse('view')
    kind = ops.rule_kind(view)
    aliases = {}
    if kind:
        rows,_,_,_ = ops.rule_records(project,kind)
        headers = ['id', *[c['name'] for c in project['rule_schema'][kind]]]
        extras = project.get('interchange_rule_extras',{}).get(kind,{})
        names = sorted({k for values in extras.values() for k in values if k not in headers})
        for row in rows:row.update({k:row.get('extra:'+k,extras.get(row['id'],{}).get(k,'')) for k in names})
        headers.extend(names)
    else:
        rows,_ = ops.records(mod,project)
        headers = ['id', *(sorted(ops.META) if view=='classification' else
                    [k for k,v in ops.FIELDS.items() if v[3]==view])]
        if view=='base':headers.extend(ops.DERIVED_COLUMNS)
        extras = sorted({k for row in rows for k in row if k.startswith('extra:')})
        for key in extras:
            target = key[6:]
            while target in headers:target='extra:'+target
            aliases[key]=target
            headers.append(target)
    live = {r['id']:r for r in rows}
    if layout=='imported':
        saved = project.get('interchange',{}).get(view)
        if not saved:refuse('no_imported_layout')
        return updated_table(saved,live)
    if layout not in (None,'canonical'):refuse('layout')
    for row in rows:
        values = {source:row.get(source) for source in aliases}
        row.update({target:values[source] for source,target in aliases.items()})
    cells = {column_name(c)+'1':{'value':h} for c,h in enumerate(headers)}
    for r,row in enumerate(rows,2):
        for c,h in enumerate(headers):
            value = row.get(h)
            if project['draft'].get(row['id'],{}).get(h) == []:
                value = []
            cells[column_name(c)+str(r)] = {'value':display(value)}
    return {'name':'CSV' if kind else view,'cells':cells,
            'formula_issues':[issue for row in rows for issue in row.get('formula_issues',[])]}


def write_xlsx(table,mode):
    ET.register_namespace('',NS)
    root = ET.Element('{'+NS+'}worksheet')
    data = ET.SubElement(root,'{'+NS+'}sheetData')
    for r,values in sorted(row_values(table).items()):
        row = ET.SubElement(data,'{'+NS+'}row',r=str(r))
        for c,entry in sorted(values.items()):
            cell = ET.SubElement(row,'{'+NS+'}c',r=column_name(c)+str(r))
            raw = entry.get('value')
            if mode=='supported' and entry.get('supported'):
                ET.SubElement(cell,'{'+NS+'}f').text=entry['formula'].lstrip('=')
                if raw is not None:ET.SubElement(cell,'{'+NS+'}v').text=str(raw)
            elif isinstance(raw,bool):
                cell.set('t','b')
                ET.SubElement(cell,'{'+NS+'}v').text='1' if raw else '0'
            elif type(raw) in (int,float):
                ET.SubElement(cell,'{'+NS+'}v').text=str(raw)
            else:
                cell.set('t','inlineStr')
                text = ET.SubElement(ET.SubElement(cell,'{'+NS+'}is'),'{'+NS+'}t')
                text.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                text.text=str(display(raw))
    book=ET.Element('{'+NS+'}workbook')
    ET.SubElement(ET.SubElement(book,'{'+NS+'}sheets'),'{'+NS+'}sheet',
                  name=table['name'],sheetId='1',attrib={'{'+REL+'}id':'rId1'})
    ET.SubElement(book,'{'+NS+'}calcPr',calcMode='auto')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="'+REL+'/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="'+REL+'/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',ET.tostring(book,encoding='utf-8',xml_declaration=True))
        z.writestr('xl/worksheets/sheet1.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))
    return base64.b64encode(out.getvalue()).decode('ascii')


def export(mod,project,body):
    fmt,mode = body.get('format'),body.get('formulas')
    if fmt not in ('csv','xlsx') or mode not in ('values','supported'):
        refuse('explicit_export_mode')
    if mode=='supported' and body.get('layout')!='imported':refuse('formula_layout_required')
    table = export_table(mod,project,body.get('view'),body.get('layout'))
    issues = table.get('formula_issues',[]) + calculate(table)
    name = body['view'].replace(':','_')+'.'+fmt
    if fmt=='xlsx':
        return {'name':name,'text':write_xlsx(table,mode),'encoding':'base64',
                'mime':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','formula_issues':issues}
    if mode!='values':refuse('csv_values_only')
    out=io.StringIO(newline='');writer=csv.writer(out)
    rows = row_values(table)
    width = max((max(v)+1 for v in rows.values()),default=0)
    previous = 0
    for r,values in sorted(rows.items()):
        for _ in range(r-previous-1):writer.writerow([])
        writer.writerow([display(values.get(c,{}).get('value')) for c in range(width)])
        previous = r
    return {'name':name,'text':out.getvalue(),'mime':'text/csv','formula_issues':issues}
