"""Phase 115: synthetic header shapes only, never the user's workbook data."""
import base64
import copy
import io
import json
import unittest
import time
import zipfile
from xml.sax.saxutils import escape
from tests import test_unit_sheets as fixture, test_sheet_pipeline as pipeline_fixture
from unittransfer import unit_sheets as sheets, sheet_ops


def workbook(tables):
    """Independent minimal OOXML fixture, including a deliberately inflated range."""
    out = io.BytesIO()
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="'+ns+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(
            '<sheet name="'+escape(name)+'" sheetId="'+str(i)+'" r:id="r'+str(i)+'"/>' for i,name in enumerate(tables,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(
            '<Relationship Id="r'+str(i)+'" Target="worksheets/sheet'+str(i)+'.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>' for i in range(1,len(tables)+1))+'</Relationships>')
        for i, cells in enumerate(tables.values(),1):
            body=[]
            for address,value in cells.items():
                if isinstance(value,dict):
                    body.append('<c r="'+address+'"><f>'+escape(value['formula'])+'</f>'+(('<v>'+str(value['cache'])+'</v>') if 'cache' in value else '')+'</c>')
                else:
                    body.append('<c r="'+address+'" t="inlineStr"><is><t>'+escape(str(value))+'</t></is></c>')
            z.writestr('xl/worksheets/sheet'+str(i)+'.xml','<worksheet xmlns="'+ns+'"><dimension ref="A1:XFD1048576"/><sheetData><row>'+''.join(body)+'</row><row r="1048576"><c r="XFD1048576" s="1"/></row></sheetData></worksheet>')
        z.writestr('xl/vbaProject.bin', b'NEVER EXECUTE')
    return base64.b64encode(out.getvalue()).decode()


class InterchangeTests(unittest.TestCase):
    setUp = fixture.SheetProjectTests.setUp

    def test_gunpowder_delay_round_trip_and_native_patch(self):
        from unittransfer import edu
        native='20, 3, bullet, 45, 20, missile, missile_gunpowder, piercing, none, musket_shot_set, 25, 1'
        self.mod.edu=edu.parse_text('type Guard\ncategory infantry\nstat_pri '+native+' ; keep\n')
        for fmt in ('csv','xlsx'):
            exported=self.request('interchange_export',view='base',format=fmt,formulas='values')
            table=self.request('interchange_inspect',format=fmt,text=exported['text'])['sheets'][0]
            headers=table['rows'][0]['values']
            body=dict(format=fmt,text=exported['text'],plans=[dict(sheet=table['name'],view='base',header_row=1,
                mapping={'id':headers.index('id'),'attack_delay':headers.index('attack_delay')})])
            p=self.accept(body)['project']
            self.assertEqual(p['draft']['Guard']['attack_delay'],25)
            fields,_=sheet_ops.field_changes(self.mod.edu.units[0],p['draft']['Guard'])
            self.assertEqual(fields['stat_pri'],native)

    def test_fifty_thousand_formatted_empty_rows_are_bounded(self):
        source=base64.b64decode(workbook({'Base stats':{'A1':'type','B1':'Attack','A2':'Guard','B2':0}}))
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(source)) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
            for name in src.namelist():
                value=src.read(name)
                if name.endswith('sheet1.xml'):
                    empty=''.join('<row r="'+str(r)+'"><c r="B'+str(r)+'" s="1"/></row>' for r in range(3,50003))
                    value=value.replace(b'</sheetData>',empty.encode()+b'</sheetData>')
                dest.writestr(name,value)
        start=time.perf_counter()
        body=self.spec();body.update(format='xlsx',text=base64.b64encode(out.getvalue()).decode())
        body['plans'][0]['sheet']='Base stats'
        preview=self.request('interchange_preview',**body)
        self.assertEqual(preview['ids'],['Guard']);self.assertEqual(preview['ignored'],[])
        self.assertLess(time.perf_counter()-start,10,'formatted empty rows must not become records')

    def test_list_round_trip_preserves_duplicate_native_members(self):
        from unittransfer import edu
        self.mod.edu=edu.parse_text('type Guard\ncategory infantry\nattributes hardy, stakes, stakes ; keep\n')
        for fmt in ('csv','xlsx'):
            exported=self.request('interchange_export',view='attributes',format=fmt,formulas='values')
            table=self.request('interchange_inspect',format=fmt,text=exported['text'])['sheets'][0]
            headers=table['rows'][0]['values']
            body=dict(format=fmt,text=exported['text'],plans=[dict(sheet=table['name'],view='attributes',header_row=1,
                mapping={'id':headers.index('id'),'attributes':headers.index('attributes')})])
            p=self.accept(body)['project']
            self.assertEqual(p['draft']['Guard']['attributes'],['hardy','stakes','stakes'])
            fields,_=sheet_ops.field_changes(self.mod.edu.units[0],p['draft']['Guard'])
            self.assertEqual(fields['attributes'],'hardy, stakes, stakes')

    def request(self, action, **kw):
        current=sheets.service(self.mod,'load')
        return sheets.service(self.mod,action,dict(revision=current['revision'],source_token=current['source_token'],**kw))

    def spec(self, text='type,Attack,Note\nGuard,0,keep\n', **kw):
        return dict(format='csv',text=text,plans=[dict(sheet='CSV',view='base',header_row=1,mapping={'id':0,'attack':1})],**kw)

    def accept(self, body):
        preview=self.request('interchange_preview',**body)
        return self.request('interchange_import',**body,preview_token=preview['preview_token'])

    def test_mapping_preview_required_and_atomic_with_zero(self):
        before=self.request('load')['project'];raw=sheets.project_path(self.mod).read_bytes()
        body=self.spec()
        with self.assertRaises(sheets.SheetError):self.request('interchange_import',**body)
        preview=self.request('interchange_preview',**body)
        self.assertEqual(preview['ids'],['Guard']);self.assertEqual(preview['fields'],['attack'])
        self.assertEqual(sheets.project_path(self.mod).read_bytes(),raw)
        self.assertEqual(before,self.request('load')['project'])
        result=self.request('interchange_import',**body,preview_token=preview['preview_token'])
        self.assertEqual(result['project']['draft']['Guard']['attack'],0)
        raw=sheets.project_path(self.mod).read_bytes()
        bad=self.spec('type,Attack,Note\nGuard,8,x\nHorse,invalid,y\n')
        with self.assertRaises(sheets.SheetError):self.request('interchange_preview',**bad)
        with self.assertRaises(sheets.SheetError):self.request('interchange_import',**bad,preview_token=preview['preview_token'])
        self.assertEqual(sheets.project_path(self.mod).read_bytes(),raw)

    def test_inspect_duplicate_headings_and_reject_ambiguous_mapping(self):
        text='Sort,A,Race,Race,925\n1,Guard,Human,Elf,55\n'
        info=self.request('interchange_inspect',format='csv',text=text)
        self.assertEqual(info['sheets'][0]['rows'][0]['values'],['Sort','A','Race','Race','925'])
        body=self.spec(text);body['plans'][0]['mapping']={'id':'A','Unit Race':'Race'}
        with self.assertRaises(sheets.SheetError):self.request('interchange_preview',**body)
        body['plans'][0]['mapping']={'id':1,'Unit Race':3}
        result=self.accept(body)
        self.assertEqual(result['project']['units']['Guard']['annotations']['Unit Race'],'Elf')
        self.assertNotIn('Gondor',result['project']['units'])

    def test_current_archived_shapes_and_sparse_formatted_rows(self):
        for headings in [('Sort','A','Faction','Race','Column 3','925'),('Sort','type','Faction','Race','Tier','Campaign cost')]:
            cells={chr(65+i)+'1':v for i,v in enumerate(headings)}
            cells.update(B2='Gondor',B3='Guard',D3='Human',E3='T1',F3=0,B7='not_a_unit',B9='Horse',F9='')
            body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':1,'Unit Race':3,'Tier':4,'recruit_cost':5})])
            # This fixture's units have no stat_cost tuple: a nonblank cost is invalid.
            body['plans'][0]['mapping'].pop('recruit_cost')
            p=self.request('interchange_preview',**body)
            self.assertEqual(p['ids'],['Guard','Horse']);self.assertEqual(len(p['ignored']),2)
            result=self.accept(body)
            exported=self.request('interchange_export',view='base',format='xlsx',layout='imported',formulas='values')
            again=dict(body,text=exported['text'])
            self.assertEqual(self.request('interchange_preview',**again)['ids'],['Guard','Horse'])
            self.assertEqual(result['project']['units']['Guard']['annotations']['Tier'],'T1')

    def test_keyed_cross_sheet_join_and_explicit_list_clear(self):
        cells={'A1':'type','B1':'Attack','A2':'Guard','B2':0,'A3':'Horse'}
        attrs={'A1':'type','B1':'Attributes','A2':'Horse','B2':'[]','A4':'Guard','B4':'[]'}
        body=dict(format='xlsx',text=workbook({'Base stats':cells,'Attributes':attrs}),plans=[
            dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0,'attack':1}),
            dict(sheet='Attributes',view='attributes',header_row=1,mapping={'id':0,'attributes':1})])
        result=self.accept(body)['project']
        self.assertEqual(result['draft']['Guard'],{'attack':0,'attributes':[]})
        self.assertEqual(result['draft']['Horse'],{'attributes':[]})
        fields,removals=sheet_ops.field_changes(self.mod.edu.units[0],result['draft']['Guard'])
        self.assertIn('attributes',removals);self.assertIn('0, 2, no',fields['stat_pri'])
        self.assertIn('; keep',self.mod.edu.units[0].raw)

    def test_duplicate_units_and_conflicting_cross_sheet_fields_refuse(self):
        with self.assertRaises(sheets.SheetError):self.request('interchange_preview',**self.spec('type,Attack\nGuard,0\nGuard,1\n'))
        b=self.spec();b['plans'].append(dict(b['plans'][0]))
        with self.assertRaises(sheets.SheetError):self.request('interchange_preview',**b)

    def test_formulas_are_derived_named_and_never_native_updates(self):
        cells={'A1':'type','B1':'Attack','C1':'Computed','D1':'Unsafe','E1':'Blank input',
               'A2':'Guard','B2':4,'C2':{'formula':'B2*2+1','cache':3},
               'D2':{'formula':'WEBSERVICE("evil")'},'E2':{'formula':'Z2+1'}}
        body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0,'attack':1})])
        p=self.request('interchange_preview',**body)
        issues={(x['cell'],x['code']) for x in p['formula_issues']}
        self.assertIn(('C2','stale_cache'),issues);self.assertIn(('D2','unsupported_formula'),issues)
        self.assertIn(('D2','missing_cache'),issues);self.assertIn(('E2','missing_input'),issues)
        result=self.accept(body)['project']
        self.assertEqual(result['units']['Guard']['extra']['Computed'],9)
        self.assertIsNone(result['units']['Guard']['extra']['Unsafe'])
        body['plans'][0]['mapping']['attack']=2
        with self.assertRaises(sheets.SheetError):self.request('interchange_preview',**body)

    def test_formula_export_choice_and_recalculation_after_native_edit(self):
        from unittransfer import sheet_interchange as interchange
        cells={'A1':'type','B1':'Attack','C1':'Total','A2':'Guard','B2':4,'C2':{'formula':'$B$2*2'}}
        body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0,'attack':1})])
        self.accept(body)
        self.request('operate',view='base',ids=['Guard'],column='attack',operation='set',value=6)
        for mode in ('values','supported'):
            r=self.request('interchange_export',view='base',format='xlsx',layout='imported',formulas=mode)
            table=interchange.read_tables('xlsx',r['text'])[0]
            self.assertEqual(table['cells']['C2']['value'],12)
            self.assertEqual(bool(table['cells']['C2'].get('formula')),mode=='supported')

    def test_all_views_csv_and_xlsx_round_trip(self):
        for view in ('classification','base','attributes','soft','rules:replenish','rules:experience','rules:pool'):
            for fmt in ('csv','xlsx'):
                exported=self.request('interchange_export',view=view,format=fmt,formulas='values')
                info=self.request('interchange_inspect',format=fmt,text=exported['text'])
                self.assertEqual(len(info['sheets']),1)
                self.assertIn('id',info['sheets'][0]['rows'][0]['values'])
                if view.startswith('rules:'):continue
                headers=info['sheets'][0]['rows'][0]['values']
                mapping={h:i for i,h in enumerate(headers) if h=='id' or h in sheet_ops.META or h in sheet_ops.FIELDS}
                body=dict(format=fmt,text=exported['text'],plans=[dict(sheet=info['sheets'][0]['name'],view=view,header_row=1,mapping=mapping)])
                result=self.accept(body)
                self.assertNotIn('None',json.dumps(result['project']['draft']))

    def test_rule_import_merges_by_key_preserving_omitted_values(self):
        for kind in sheets.RULE_KEYS:
            keys=sheets.RULE_KEYS[kind]
            headers=list(keys)+['T0','Notes'] if kind!='replenish' else ['Tier','Human_Earliest','Notes']
            vals=['Human','infantry','T1',0,'retain'] if kind!='replenish' else ['T1',0,'retain']
            mapping={name:i for i,name in enumerate(headers[:-1])}
            body=dict(format='csv',text=','.join(headers)+'\n'+','.join(map(str,vals))+'\n',plans=[dict(sheet='CSV',view='rules:'+kind,header_row=1,mapping=mapping)])
            result=self.accept(body)
            row=result['project']['rules'][kind][0];rowid=row['id']
            exported=self.request('interchange_export',view='rules:'+kind,format='xlsx',layout='imported',formulas='values')
            r=self.accept(dict(body,format='xlsx',text=exported['text']))
            self.assertEqual(r['project']['rules'][kind][0]['id'],rowid)
            self.assertEqual(r['project']['rules'][kind][0][headers[-2]],0)

    def test_fynn_mapping_validates_ids_and_does_not_substitute_native_stats(self):
        body=dict(format='edu_json',text=json.dumps({'Guard':{'Type':'Guard','Race':'Human','StatPri':{'Attack':999}},'Group':{}}),plans=[dict(sheet='Fynn EDU',view='classification',header_row=1,mapping={'id':0,'Unit Race':1})])
        info=self.request('interchange_inspect',format=body['format'],text=body['text'])
        headers=info['sheets'][0]['rows'][0]['values']
        body['plans'][0]['mapping']={'id':headers.index('Name'),'Unit Race':headers.index('Race')}
        r=self.accept(body)['project'];self.assertEqual(r['draft'],{})
        self.assertNotIn('Group',r['units']);self.assertEqual(r['units']['Guard']['extra']['StatPri'],{'Attack':999})

    def test_preview_token_binds_source_mapping_and_project(self):
        body=self.spec();preview=self.request('interchange_preview',**body)
        body['text']=body['text'].replace('Guard,0','Guard,1')
        with self.assertRaises(sheets.SheetError):self.request('interchange_import',**body,preview_token=preview['preview_token'])

    def test_absent_fields_are_blank_and_unknown_headers_survive_canonical_export(self):
        self.accept(self.spec())
        r=self.request('interchange_export',view='base',format='csv',formulas='values')
        self.assertIn('Note',r['text'].splitlines()[0].split(','))
        r=self.request('interchange_export',view='attributes',format='csv',formulas='values')
        import csv
        rows=list(csv.DictReader(io.StringIO(r['text'])))
        self.assertEqual(rows[0]['pri_attributes'],'')
        self.assertEqual(rows[1]['attributes'],'')

    def test_unknown_rule_columns_survive_both_export_layouts(self):
        body=dict(format='csv',text='Tier,Human_Earliest,Notes\nT1,0,retained\n',plans=[dict(sheet='CSV',view='rules:replenish',header_row=1,mapping={'Tier':0,'Human_Earliest':1})])
        self.accept(body)
        for layout in ('canonical','imported'):
            r=self.request('interchange_export',view='rules:replenish',format='csv',layout=layout,formulas='values')
            self.assertIn('Notes',r['text']);self.assertIn('retained',r['text'])

    def test_rule_subset_import_preserves_other_rows_columns_and_zero(self):
        full=dict(format='csv',text='Tier,Human_Earliest,Human_Latest\nT1,0,9\nT2,5,7\n',plans=[dict(sheet='CSV',view='rules:replenish',header_row=1,mapping={'Tier':0,'Human_Earliest':1,'Human_Latest':2})])
        self.accept(full)
        partial=copy.deepcopy(full);partial['text']='Tier,Human_Earliest\nT1,4\n';partial['plans'][0]['mapping'].pop('Human_Latest')
        r=self.accept(partial)['project']['rules']['replenish']
        self.assertEqual([(x['Tier'],x['Human_Earliest'],x['Human_Latest']) for x in r],[('T1',4,9),('T2',5,7)])

    def test_formula_cycles_missing_caches_and_division_by_zero_are_not_zero(self):
        cells={'A1':'type','B1':'Cycle','C1':'Division','D1':'Computed','A2':'Guard',
               'B2':{'formula':'B2+1','cache':100},'C2':{'formula':'1/0','cache':3},'D2':{'formula':'2.5*(1+3)'}}
        body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0})])
        p=self.request('interchange_preview',**body)
        self.assertIn('cyclic_formula',[x['code'] for x in p['formula_issues']])
        self.assertIn('division_by_zero',[x['code'] for x in p['formula_issues']])
        r=self.accept(body)['project']['units']['Guard']['extra']
        self.assertIsNone(r['Cycle']);self.assertIsNone(r['Division']);self.assertEqual(r['Computed'],10)

    def test_clear_list_round_trips_and_no_comments_or_omitted_fields_are_rebuilt(self):
        body=dict(format='csv',text='type,Attributes\nGuard,[]\n',plans=[dict(sheet='CSV',view='attributes',header_row=1,mapping={'id':0,'attributes':1})])
        original=self.mod.edu.units[0].raw
        self.accept(body)
        for fmt in ('csv','xlsx'):
            r=self.request('interchange_export',view='attributes',format=fmt,formulas='values')
            info=self.request('interchange_inspect',format=fmt,text=r['text']);head=info['sheets'][0]['rows'][0]['values']
            again=dict(format=fmt,text=r['text'],plans=[dict(sheet=info['sheets'][0]['name'],view='attributes',header_row=1,mapping={h:i for i,h in enumerate(head) if h in ('id','attributes','pri_attributes','sec_attributes')})])
            p=self.accept(again)['project']
            self.assertEqual(p['draft']['Guard']['attributes'],[])
            self.assertNotIn('pri_attributes',p['draft']['Guard'])
            self.assertNotIn('attack',p['draft']['Guard'])
        self.assertEqual(self.mod.edu.units[0].raw,original)

    def test_formula_export_does_not_retain_unsupported_executable_formulas(self):
        cells={'A1':'type','B1':'Unsafe','A2':'Guard','B2':{'formula':'HYPERLINK("https://invalid")','cache':999}}
        body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0})])
        self.accept(body)
        r=self.request('interchange_export',view='base',format='xlsx',layout='imported',formulas='supported')
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(r['text']))) as z:
            self.assertNotIn(b'<f>',z.read('xl/worksheets/sheet1.xml'))
            self.assertNotIn('xl/vbaProject.bin',z.namelist())
        self.assertTrue(r['formula_issues'])

    def test_full_user_header_shapes_split_lists_and_keyed_round_trip(self):
        from pathlib import Path
        from unittransfer import edu, sheet_interchange as interchange
        heads=json.loads((Path(__file__).parent/'fixtures/sheet_workbook_headers.json').read_text())
        self.mod.edu=edu.parse_text(fixture.TEXT.replace('; keep','stat_cost 1, 500, 100, 10, 20, 600, 4, 8\nformation 1, 2, 3, 4, 5, square, schiltrom\nmount_effect horse +1\n; keep'))
        for variant in ('base20','base17'):
            base={interchange.column_name(c)+'1':v for c,v in enumerate(heads[variant])}
            base.update(B2='Gondor',B3='Guard',D3='Human',E3='T1',O3=0,AE3=0,B4='Horse')
            attrs={interchange.column_name(c)+'1':v for c,v in enumerate(heads['attributes'])}
            attrs.update(A2='Horse',D2='no',A4='Guard',D4='hardy',E4='custom_tag')
            soft={interchange.column_name(c)+'1':v for c,v in enumerate(heads['soft'])}
            soft.update(A3='Guard',D3=0,O3='horse +2',P3='camel -1')
            body=dict(format='xlsx',text=workbook({'Base stats':base,'Attributes':attrs,'Soft stats':soft}),plans=[
                dict(sheet='Base stats',view='base',header_row=1,mapping={'id':1,'Unit Race':3,'Tier':4,'attack':14,'recruit_cost':30}),
                dict(sheet='Attributes',view='attributes',header_row=1,mapping={'id':0,'attributes':list(range(3,14))}),
                dict(sheet='Soft stats',view='soft',header_row=1,mapping={'id':0,'close_side':3,'mount_effect':list(range(14,18))})])
            result=self.accept(body)['project'];draft=result['draft']['Guard']
            self.assertEqual(draft['attack'],0);self.assertEqual(draft['recruit_cost'],0)
            self.assertEqual(draft['attributes'],['hardy','custom_tag']);self.assertEqual(draft['mount_effect'],['horse +2','camel -1'])
            self.assertEqual(result['draft']['Horse']['attributes'],[])
            for plan in body['plans']:
                for fmt in ('csv','xlsx'):
                    exported=self.request('interchange_export',view=plan['view'],format=fmt,layout='imported',formulas='values')
                    replan=copy.deepcopy(plan)
                    replan['sheet']=self.request('interchange_inspect',format=fmt,text=exported['text'])['sheets'][0]['name']
                    again=self.accept(dict(format=fmt,text=exported['text'],plans=[replan]))
                    self.assertEqual(again['project']['draft']['Guard']['attributes'],['hardy','custom_tag'])
            self.assertIn('schiltrom',self.mod.edu.units[0].raw)

    def test_live_derived_values_follow_staged_edits(self):
        cells={'A1':'type','B1':'Attack','C1':'Total','A2':'Guard','B2':4,'C2':{'formula':'B2*2','cache':8}}
        body=dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0,'attack':1})])
        self.accept(body)
        r=self.request('operate',view='base',ids=['Guard'],column='attack',operation='set',value=7)
        self.assertEqual(r['table']['rows'][0]['extra:Total'],14)
        self.assertEqual(r['filter_info']['extra:Total']['kind'],'derived')

    def test_header_only_rule_workbooks_round_trip(self):
        for kind in sheets.RULE_KEYS:
            for fmt in ('csv','xlsx'):
                r=self.request('interchange_export',view='rules:'+kind,format=fmt,formulas='values')
                info=self.request('interchange_inspect',format=fmt,text=r['text']);head=info['sheets'][0]['rows'][0]['values']
                body=dict(format=fmt,text=r['text'],plans=[dict(sheet=info['sheets'][0]['name'],view='rules:'+kind,header_row=1,mapping={k:head.index(k) for k in sheets.RULE_KEYS[kind]})])
                self.assertEqual(self.accept(body)['project']['rules'][kind],[])

    def test_imported_split_list_capacity_does_not_limit_native_editing(self):
        body=self.spec('type,Tags,Other\nGuard,hardy,custom\n')
        body['plans'][0]=dict(sheet='CSV',view='attributes',header_row=1,mapping={'id':0,'attributes':[1,2]})
        self.accept(body)
        self.request('operate',view='attributes',ids=['Guard'],column='attributes',operation='set',value=['a','b','c'])
        with self.assertRaises(sheets.SheetError):self.request('interchange_export',view='attributes',format='xlsx',layout='imported',formulas='values')
        self.request('interchange_export',view='attributes',format='xlsx',formulas='values')
        self.assertEqual(self.request('load')['project']['draft']['Guard']['attributes'],['a','b','c'])

    def test_unknown_duplicate_header_labels_cannot_overwrite_one_another(self):
        body=self.spec('type,X,X,X [B]\nGuard,first,second,third\n')
        body['plans'][0]['mapping']={'id':0}
        extra=self.accept(body)['project']['units']['Guard']['extra']
        self.assertEqual(sorted(extra.values()),['first','second','third'])

    def test_extra_headers_cannot_collide_with_native_export_headers(self):
        body=self.spec('type,attack,extra:attack\nGuard,note one,note two\n')
        body['plans'][0]['mapping']={'id':0}
        self.accept(body)
        r=self.request('interchange_export',view='base',format='csv',formulas='values')
        import csv
        rows=list(csv.reader(io.StringIO(r['text'])))
        self.assertEqual(len(rows[0]),len(set(rows[0])))
        self.assertIn('note one',rows[1]);self.assertIn('note two',rows[1])

    def test_canonical_values_export_reports_unavailable_formula_names(self):
        cells={'A1':'type','B1':'Broken','A2':'Guard','B2':{'formula':'SUM(B2:B3)'}}
        self.accept(dict(format='xlsx',text=workbook({'Base stats':cells}),plans=[dict(sheet='Base stats',view='base',header_row=1,mapping={'id':0})]))
        r=self.request('interchange_export',view='base',format='csv',formulas='values')
        self.assertTrue(any(x['name']=='SUM(B2:B3)' for x in r['formula_issues']))

    def test_invalid_response_filter_cannot_save_an_import(self):
        body=self.spec();preview=self.request('interchange_preview',**body)
        raw=sheets.project_path(self.mod).read_bytes()
        with self.assertRaises(sheets.SheetError):self.request('interchange_import',**body,preview_token=preview['preview_token'],where={'column':'attack','op':'invented','value':5})
        self.assertEqual(sheets.project_path(self.mod).read_bytes(),raw)

    def test_csv_title_rows_before_explicit_header_and_empty_inline_rows(self):
        body=dict(format='csv',text='Synthetic title\n\ntype,Attack\nGuard,0\n',plans=[dict(sheet='CSV',view='base',header_row=3,mapping={'id':0,'attack':1})])
        self.assertEqual(self.accept(body)['project']['draft']['Guard']['attack'],0)
        info=self.request('interchange_inspect',format='xlsx',text=workbook({'Base stats':{'A1':'type','B1':'Attack','A2':'Guard','B2':0,'A999999':'','B999999':''}}))
        self.assertEqual(info['sheets'][0]['populated_rows'],2)
        exported=self.request('interchange_export',view='base',format='csv',layout='imported',formulas='values')
        self.assertEqual(self.accept(dict(body,text=exported['text']))['project']['draft']['Guard']['attack'],0)
        info=self.request('interchange_inspect',format='csv',text='type,Attack\nGuard,0\n,\n,\n')
        self.assertEqual(info['sheets'][0]['populated_rows'],2)

    def test_legacy_http_import_cannot_bypass_preview_and_validated_identity(self):
        samples={'csv':'Name,Tier\nNot_a_live_unit,T3\n','edu_json':'{"Not_a_live_unit":{"Type":"Not_a_live_unit"}}',
                 'replenish':'Tier,Human_Earliest\nT1,2\n',
                 'experience':'Unit Race,Category,BarracksTier,T0\nHuman,infantry,T1,0\n',
                 'pool':'Unit Race,Category,BarracksTier,T0\nHuman,infantry,T1,0\n'}
        self.request('load');before=sheets.project_path(self.mod).read_bytes()
        for kind,text in samples.items():
            with self.subTest(kind=kind),self.assertRaises(sheets.SheetError):self.request('import',kind=kind,text=text)
            self.assertEqual(sheets.project_path(self.mod).read_bytes(),before)

    def test_rule_derived_columns_recalculate_and_export_with_named_issues(self):
        cells={'A1':'Tier','B1':'Human_Earliest','C1':'Computed','D1':'Broken',
               'A2':'T1','B2':4,'C2':{'formula':'B2*2','cache':8},'D2':{'formula':'SUM(B2:B3)'}}
        body=dict(format='xlsx',text=workbook({'Rules':cells}),plans=[dict(sheet='Rules',view='rules:replenish',header_row=1,mapping={'Tier':0,'Human_Earliest':1})])
        r=self.accept(body)
        rowid=r['project']['rules']['replenish'][0]['id']
        r=self.request('operate',view='rules:replenish',ids=[rowid],column='Human_Earliest',operation='set',value=6)
        self.assertEqual(r['table']['rows'][0]['extra:Computed'],12)
        self.assertEqual(r['filter_info']['extra:Computed']['kind'],'derived')
        self.assertTrue(r['filter_info']['extra:Computed']['readonly'])
        self.assertTrue(r['formula_issues'])
        exported=self.request('interchange_export',view='rules:replenish',format='csv',formulas='values')
        import csv
        row=next(csv.DictReader(io.StringIO(exported['text'])))
        self.assertEqual(row['Computed'],'12.0');self.assertEqual(row['Broken'],'')
        self.assertTrue(exported['formula_issues'])


class InterchangeHTTPTests(unittest.TestCase):
    setUp = pipeline_fixture.PipelineTests.setUp
    http_fixture = pipeline_fixture.PipelineTests.http_fixture

    def test_actual_ui_mapping_export_and_backed_up_native_apply_over_http(self):
        import subprocess
        original=self.mod.edu_path.read_bytes()
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert'),base=process.argv[1];
const elements={},calls=[],errors=[],downloads=[];
const c={console,Set,Map,Promise,structuredClone,setTimeout,clearTimeout,Uint8Array,Blob,atob,btoa,
 confirm:()=>true,state:{src:'fixture'},modal:{innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null},overlay:{classList:{add(){}}},
 document:{getElementById:id=>elements[id],createElement:()=>({click(){downloads.push(this.download);}})},
 URL:{createObjectURL:()=>'',revokeObjectURL(){}},tt:k=>k,ttA:k=>k,toast:m=>errors.push(m),errText:e=>e.message,
 esc:v=>String(v).replace(/[<>&"]/g,'_'),api:{post:async(url,body)=>{calls.push(url);const r=await fetch(base+url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.json();}}};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/js/unitsheets.js','utf8'),c);
(async()=>{
 await c.unitSheetsOpen();await c.unitSheetsTab('base');elements.usImportKind={value:'sheet'};
 await c.unitSheetsImport({files:[{name:'fixture.csv',size:35,text:async()=>'A,Size,Note\nGuard,0,retained\nHorse,25,keep\n'}]});
 c.unitSheetsMappingColumn(0,0,'id');c.unitSheetsMappingColumn(0,1,'unit_size');
 await c.unitSheetsInterchangePreview();assert.equal(vm.runInContext('USHEET.interchange.preview.ids.length',c),2,errors.join('\n'));
 assert.equal(vm.runInContext('Object.keys(USHEET.data.project.draft).length',c),0);
 await c.unitSheetsInterchangeStage();assert.equal(vm.runInContext('USHEET.data.project.draft.Guard.unit_size',c),0);
 assert.equal(vm.runInContext('USHEET.past.length',c),1);
 await c.unitSheetsUndo(false);assert.equal(vm.runInContext('Object.keys(USHEET.data.project.draft).length',c),0);
 await c.unitSheetsUndo(true);assert.equal(vm.runInContext('USHEET.data.project.draft.Guard.unit_size',c),0);
 elements.usExportFormat={value:'xlsx'};elements.usExportFormulas={value:'values'};elements.usExportLayout={value:'imported'};
 await c.unitSheetsExport('sheet');assert.equal(downloads[0],'base.xlsx');
 await c.unitSheetsNativePreview();assert.equal(vm.runInContext('USHEET.native.units',c),2,errors.join('\n'));
 await c.unitSheetsNativeApply();
 assert(calls.includes('/api/unit_sheets/interchange_import'));
 assert(calls.includes('/api/unit_sheets/native_apply'));
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        # The fixture applies a token-only size change, preserving every other byte.
        with self.http_fixture() as base:
            result=subprocess.run(['node','-e',script,base],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        changed=self.mod.edu_path.read_bytes()
        expected=original.replace(b'soldier guard, 60',b'soldier guard, 0').replace(b'soldier horse, 30',b'soldier horse, 25')
        self.assertEqual(changed,expected)
        from unittransfer import config
        from unittransfer.transfer import undo
        logs=config.load_log();self.assertEqual(len(logs),1)
        undo(logs[0]['id']);self.assertEqual(self.mod.edu_path.read_bytes(),original)


if __name__=='__main__':unittest.main()
