/* Node VM checks exercise the real frontend module with an asynchronous API. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const fields={attack:{type:'int',view:'base'},attributes:{type:'list',view:'attributes'}};
const initial={project:{units:{},draft:{},rules:{replenish:[],experience:[],pool:[]},views:{},recipes:{},comparison:{ultra_size:2.5,defense_weight:.8}},
 revision:'r0',source_token:'source',field_info:fields,columns:Object.keys(fields),extra_columns:["extra:a');bad();//"],
 refresh:{added:[],removed:[],missing_classifications:[],rename_candidates:[]},
 table:{rows:[{id:'second',attack:5,'Unit Race':'Human'},{id:'first',attack:9,'Unit Race':'Elf'}],total:2,matched_ids:['second','first']}};
function harness(){
 let response=structuredClone(initial),calls=[],elements={};
 const c={structuredClone,console,Set,Map,Promise,setTimeout,clearTimeout,
  state:{src:'Fixture'},modal:{innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null},overlay:{classList:{add(){}}},
  document:{getElementById:id=>elements[id]},
  tt:(key,p)=>key+Object.values(p||{}).join(' '),ttA:key=>key,toast(){},errText:e=>e.message,
  esc:v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  api:{post:async(url,body)=>{await new Promise(r=>setTimeout(r,2));calls.push(structuredClone(body));
   if(url.endsWith('/operate')){
    assert.equal(body.revision,response.revision);
    response.project.draft[body.ids[0]]={[body.column]:body.value};response.revision='r'+calls.length;
   }else if(url.endsWith('/save')){
    assert.equal(body.revision,response.revision);
    response.project=structuredClone(body.project);response.revision='r'+calls.length;
   }return structuredClone(response);}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('web/js/unitsheets.js','utf8'),c);
 return {c,calls,elements,response,get:u=>vm.runInContext(u,c),set:s=>vm.runInContext(s,c)};
}
function massControls(h){
 h.elements.usMassColumn={value:'attack'};
 h.elements.usMassOp={value:'set'};
 h.elements.usMassValue={value:'20'};
 h.elements.usMassOther={value:''};
}
async function safetyRegressions(){
 const failures=[];
 async function check(name,run){
  try{await run();console.log('PASS: '+name);}
  catch(error){failures.push(name+': '+error.message);}
 }
 await check('filter drops hidden selected rows before mass edit',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);
  h.set("USHEET.selected=new Set(['second','first']);USHEET.filterRows=[{column:'id',op:'eq',value:'first'}]");
  h.response.table={rows:[h.response.table.rows[1]],total:1,matched_ids:['first']};
  await h.c.unitSheetsFilter();await h.get('USHEET.queue');
  await h.c.unitSheetsMass();await h.get('USHEET.queue');
  assert.deepEqual(h.calls.at(-1).ids,['first']);
  assert.deepEqual(h.get('[...USHEET.selected]'),['first']);
 });
 await check('select matches replaces stale selection',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  h.set("USHEET.selected=new Set(['stale'])");h.c.unitSheetsSelectMatches();
  assert.deepEqual(h.get('[...USHEET.selected]'),['second','first']);
 });
 await check('mass edit waits for an in-flight filter',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);
  h.set("USHEET.selected=new Set(['second','first'])");
  h.response.table={rows:[h.response.table.rows[1]],total:1,matched_ids:['first']};
  const filtering=h.c.unitSheetsFilter();
  await h.c.unitSheetsMass();await filtering;
  assert.deepEqual(h.calls.at(-1).ids,['first']);
 });
 await check('paste waits for filtering and excludes newly hidden IDs',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='base'");
  h.response.table={rows:[h.response.table.rows[1]],total:1,matched_ids:['first']};
  const filtering=h.c.unitSheetsFilter();
  await h.c.unitSheetsPaste({clipboardData:{getData:()=>"11\n12"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'1'}}});
  await filtering;await h.get('USHEET.queue');
  assert.deepEqual(h.calls.at(-1).cells,[{id:'first',column:'attack',value:'12'}]);
 });
 await check('rectangle stores row IDs and column names',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='base'");
  h.c.unitSheetsRect({},0,1);
  h.c.unitSheetsRect({shiftKey:true,preventDefault(){}},1,1);
  assert.deepEqual(h.get('USHEET.anchor'),{id:'second',column:'attack'});
  assert.deepEqual(h.get('USHEET.rect'),{ids:['second','first'],columns:['attack']});
 });
 await check('rectangle fill uses its top ID and visible targets',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);h.set("USHEET.view='base'");
  h.c.unitSheetsRect({},0,1);h.c.unitSheetsRect({shiftKey:true,preventDefault(){}},1,1);
  h.set("USHEET.selected=new Set(['off-page'])");
  await h.c.unitSheetsFill();await h.get('USHEET.queue');
  assert.deepEqual(h.calls.at(-1).cells,[{id:'second',column:'attack',value:5},{id:'first',column:'attack',value:5}]);
 });
 await check('checkbox fill excludes off-page IDs and follows displayed order',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);
  h.set("USHEET.selected=new Set(['first','off-page','second']);USHEET.data.table.matched_ids.push('off-page')");
  await h.c.unitSheetsFill();await h.get('USHEET.queue');
  assert.deepEqual(h.calls.at(-1).ids,['second','first']);
  assert.equal(h.calls.at(-1).value,5);
 });
 await check('rectangle fill keeps its columns if a flushed edit reorders rows',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);h.set("USHEET.view='base'");
  h.elements.usMassColumn.value='Unit Race';
  h.c.unitSheetsRect({},0,1);h.c.unitSheetsRect({shiftKey:true,preventDefault(){}},1,1);
  const post=h.c.api.post;
  h.c.api.post=async(url,body)=>{
   if(url.endsWith('/operate')){
    h.response.table.rows[0].attack=17;h.response.table.rows.reverse();
   }
   return post(url,body);
  };
  h.c.unitSheetsInput(0,1,'17');await h.c.unitSheetsFill();
  assert.deepEqual(h.calls.at(-1).cells,[{id:'second',column:'attack',value:17},{id:'first',column:'attack',value:17}]);
 });
 await check('paste consumes stable rectangle IDs and column names',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='base'");
  h.c.unitSheetsRect({},0,1);h.c.unitSheetsRect({shiftKey:true,preventDefault(){}},1,1);
  await h.c.unitSheetsPaste({clipboardData:{getData:()=>"11\n12\n13"},preventDefault(){},currentTarget:{dataset:{r:'1',c:'1'}}});
  await h.get('USHEET.queue');
  assert.deepEqual(h.calls.at(-1).cells,[{id:'second',column:'attack',value:'11'},{id:'first',column:'attack',value:'12'}]);
 });
 await check('single-cell rectangle anchors multi-row paste without clipping it',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='base'");
  h.c.unitSheetsRect({},0,1);
  await h.c.unitSheetsPaste({clipboardData:{getData:()=>"11\n12\n13"},preventDefault(){},currentTarget:{dataset:{r:'1',c:'1'}}});
  assert.deepEqual(h.calls.at(-1).cells,[{id:'second',column:'attack',value:'11'},{id:'first',column:'attack',value:'12'}]);
 });
 await check('filter metadata controls recruitment columns and typed operators',async()=>{
  const h=harness();
  h.response.filter_info={id:{type:'text'},changed:{type:'bool'},initial:{type:'number'},ownership:{type:'list'}};
  await h.c.unitSheetsOpen();h.set("USHEET.view='recruitment';USHEET.filterRows=[{column:'changed',op:'eq',value:false}]");
  h.c.unitSheetsPaint();
  const html=h.c.modal.innerHTML.split('id="usFilters"')[1].split('</div>')[0];
  assert(!html.includes('category'));assert(!html.includes('needs_classification'));
  assert(html.includes('value="false" selected'));assert(!html.includes('<input'));
  assert.deepEqual(h.c.unitSheetsFilterOps('changed'),['eq','ne','blank','missing']);
  assert(h.c.unitSheetsFilterOps('initial').includes('gt'));
  assert(!h.c.unitSheetsFilterOps('ownership').includes('gt'));
  h.c.unitSheetsFilterColumn(0,'initial');
  assert.equal(h.get('USHEET.filterRows[0].op'),'eq');
 });
 await check('saved and advanced flat filters restore rows and group',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  const where={any:[{column:'id',op:'eq',value:'first'},{column:'id',op:'eq',value:'second'}]};
  h.response.project.views.flat={view:'base',where,sort:[],hidden:[],order:[]};
  h.set('USHEET.data.project.views='+JSON.stringify(h.response.project.views));
  await h.c.unitSheetsLoadView('flat');
  assert.deepEqual(h.get('USHEET.filterRows'),where.any);assert.equal(h.get('USHEET.group'),'any');
  h.elements.usAdvanced={value:JSON.stringify({all:where.any})};await h.c.unitSheetsAdvanced();
  assert.deepEqual(h.get('USHEET.filterRows'),where.any);assert.equal(h.get('USHEET.group'),'all');
  assert(h.c.unitSheetsFilterSummary().includes('first'));
  assert(h.c.modal.innerHTML.includes('sheets.active_filter_count'));
 });
 await check('nested advanced filters clear misleading builder and show summary',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  h.set("USHEET.filterRows=[{column:'id',op:'eq',value:'stale'}]");
  h.elements.usAdvanced={value:JSON.stringify({not:{column:'id',op:'eq',value:'first'}})};
  await h.c.unitSheetsAdvanced();
  assert.equal(h.get('USHEET.filterRows.length'),0);
  assert(h.c.unitSheetsFilterSummary().includes('sheets.advanced_summary'));
  assert(h.c.unitSheetsFilterSummary().includes('first'));
  await h.c.unitSheetsClearFilters();assert.equal(h.get('USHEET.filterRows.length'),0);
 });
 await check('saved boolean strings and primary weapon columns stay typed and read only',async()=>{
  const h=harness();h.response.filter_info={id:{type:'text'},changed:{type:'bool'},pri_weapon_type:{type:'text',readonly:true}};
  await h.c.unitSheetsOpen();
  h.elements.usAdvanced={value:JSON.stringify({all:[{column:'changed',op:'eq',value:'FALSE'}]})};
  await h.c.unitSheetsAdvanced();await h.c.unitSheetsFilter();
  assert.strictEqual(h.calls.at(-1).where.all[0].value,false);
  h.set("USHEET.view='base'");
  assert(h.c.unitSheetsColumns().includes('pri_weapon_type'));
  assert(!h.c.unitSheetsEditable('pri_weapon_type'));
 });
 await check('restored unary boolean filters get a real value when changed to equality',async()=>{
  const h=harness();h.response.filter_info={id:{type:'text'},changed:{type:'bool'}};
  await h.c.unitSheetsOpen();
  h.elements.usAdvanced={value:JSON.stringify({column:'changed',op:'missing'})};
  await h.c.unitSheetsAdvanced();
  h.c.unitSheetsFilterOperator(0,'eq');await h.c.unitSheetsFilter();
  assert.strictEqual(h.calls.at(-1).where.all[0].value,true);
 });
 const changes=[
  ['sort',h=>h.c.unitSheetsSort('attack',false)],
  ['filter',h=>h.c.unitSheetsFilter()],
  ['missing filter',h=>h.c.unitSheetsMissing()],
  ['advanced filter',h=>{h.elements.usAdvanced={value:'{}'};return h.c.unitSheetsAdvanced();}],
  ['clear filter',h=>h.c.unitSheetsClearFilters()],
  ['page',h=>h.c.unitSheetsPage(1)],
  ['view',h=>h.c.unitSheetsTab('base')],
  ['saved view',h=>{h.set("USHEET.data.project.views.test={view:'base',sort:[{column:'attack',desc:true}],hidden:[],order:[],where:null}");return h.c.unitSheetsLoadView('test');}],
  ['columns',h=>{h.elements.usColumns={value:'id, Tier'};return h.c.unitSheetsSetColumns();}],
  ['extra columns',h=>h.c.unitSheetsExtras(true)]
 ];
 for(const [name,change] of changes){
  await check('pending edit flush and rectangle reset before '+name,async()=>{
   const h=harness();await h.c.unitSheetsOpen();
   h.c.unitSheetsRect({},0,1);h.c.unitSheetsInput(0,1,'Elf');
   await change(h);await h.get('USHEET.queue');
   const edit=h.calls.findIndex(c=>c.column==='Unit Race');
   assert.equal(edit,1,'the edit must be sent before the layout query');
   assert.equal(h.calls[edit].ids[0],'second');assert.equal(h.calls[edit].view,'classification');
   assert(!h.get('USHEET.rect'));assert(!h.get('USHEET.anchor'));
   await h.c.unitSheetsFlush();
   assert.equal(h.calls.filter(c=>c.column==='Unit Race').length,1);
  });
 }
 await check('edit then sort before debounce keeps the typed unit',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  const post=h.c.api.post;
  h.c.api.post=async(url,body)=>{
   if(url.endsWith('/query'))h.response.table.rows.reverse();
   return post(url,body);
  };
  h.c.unitSheetsInput(0,1,'Elf');await h.c.unitSheetsSort('attack',false);
  await h.get('USHEET.queue');await h.c.unitSheetsFlush();
  assert.equal(h.calls[1].column,'Unit Race');assert.equal(h.calls[1].ids[0],'second');
  assert.equal(h.get('USHEET.data.table.rows[0].id'),'first');
  assert.equal(h.get('USHEET.data.project.draft.second["Unit Race"]'),'Elf');
  assert(!h.get('USHEET.data.project.draft.first'));
 });
 await check('repeated column hiding preserves previously hidden columns',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  h.elements.usColumns={value:'id, Tier'};await h.c.unitSheetsSetColumns();
  h.elements.usColumns.value='id';await h.c.unitSheetsSetColumns();
  assert.deepEqual(h.c.unitSheetsColumns(),['id']);
  h.elements.usColumns.value='id, Unit Race';await h.c.unitSheetsSetColumns();
  assert.deepEqual(h.c.unitSheetsColumns(),['id','Unit Race']);
 });
 await check('rules use the shared grid and stable typed columns',async()=>{
  const h=harness();await h.c.unitSheetsOpen();
  h.response.columns=['Unit Race','Category','BarracksTier','T0'];
  h.response.field_info=Object.fromEntries(h.response.columns.map(column=>[column,{type:column==='T0'?'number':'text',view:'rules:pool'}]));
  h.response.frozen_columns=['id','Unit Race','Category','BarracksTier'];
  h.response.table={rows:[{id:'rule-b','Unit Race':'Custom',T0:0},{id:'rule-a','Unit Race':'Other',T0:2}],total:2,matched_ids:['rule-b','rule-a']};
  await h.c.unitSheetsTab('rules:pool');
  assert.deepEqual(h.c.unitSheetsColumns(),['id','Unit Race','Category','BarracksTier','T0']);
  assert(h.c.unitSheetsEditable('T0'));assert(!h.c.unitSheetsEditable('id'));
  assert(h.c.modal.innerHTML.includes('unitSheetsFilter()'));
  assert(h.c.modal.innerHTML.includes('unitSheetsCellKey(event)'));
  assert(h.c.modal.innerHTML.includes('unitSheetsPaste(event)'));
  assert(h.c.modal.innerHTML.includes('position:sticky'));
  h.c.unitSheetsInput(0,4,'');await h.c.unitSheetsFlush();
  assert.deepEqual(h.calls.at(-1).ids,['rule-b']);assert.equal(h.calls.at(-1).value,'');
  await h.c.unitSheetsPaste({clipboardData:{getData:()=>"\n0"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'4'}}});
  assert.deepEqual(h.calls.at(-1).cells,[{id:'rule-b',column:'T0',value:''},{id:'rule-a',column:'T0',value:'0'}]);
 });
 await check('rule structure flushes edits, confirms deletion and uses history queue',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='rules:pool'");
  h.c.confirm=()=>false;
  const before=h.calls.length;
  await h.c.unitSheetsRuleStructure('remove_rows');assert.equal(h.calls.length,before);
  h.c.confirm=()=>true;
  h.set("USHEET.selected=new Set(['second'])");
  await h.c.unitSheetsRuleStructure('remove_rows');
  assert.equal(h.calls.at(-1).operation,'remove_rows');assert.deepEqual(h.calls.at(-1).ids,['second']);
  await h.c.unitSheetsRuleStructure('add_row');
  assert.equal(h.calls.at(-1).operation,'add_row');
 });
 await check('rule structure changes serialize project history and undo redo',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='rules:pool'");
  h.c.confirm=()=>true;
  const post=h.c.api.post;
  h.c.api.post=async(url,body)=>{
   if(url.endsWith('/rule_structure')){
    const rows=h.response.project.rules.pool;
    if(body.operation==='add_row')rows.push({id:'rule-'+rows.length,T0:''});
    if(body.operation==='remove_rows')h.response.project.rules.pool=rows.filter(row=>!body.ids.includes(row.id));
    h.response.revision='structure-'+h.calls.length;
   }
   return post(url,body);
  };
  await Promise.all([h.c.unitSheetsRuleStructure('add_row'),h.c.unitSheetsRuleStructure('add_row')]);
  assert.equal(h.get('USHEET.data.project.rules.pool.length'),2);
  assert.equal(h.get('USHEET.past.length'),2);
  await h.c.unitSheetsUndo(false);assert.equal(h.get('USHEET.data.project.rules.pool.length'),1);
  await h.c.unitSheetsUndo(true);assert.equal(h.get('USHEET.data.project.rules.pool.length'),2);
 });
 await check('rule fill and pending edits retain IDs through sort',async()=>{
  const h=harness();await h.c.unitSheetsOpen();massControls(h);
  h.response.columns=['T0'];h.response.field_info={T0:{type:'number',view:'rules:pool'}};
  h.response.table={rows:[{id:'r-b',T0:0},{id:'r-a',T0:9}],matched_ids:['r-b','r-a'],total:2};
  await h.c.unitSheetsTab('rules:pool');h.elements.usMassColumn.value='T0';
  h.c.unitSheetsRect({},0,1);h.c.unitSheetsRect({shiftKey:true,preventDefault(){}},1,1);
  await h.c.unitSheetsFill();
  assert.deepEqual(h.calls.at(-1).cells,[{id:'r-b',column:'T0',value:0},{id:'r-a',column:'T0',value:0}]);
  h.c.unitSheetsInput(0,1,'3');await h.c.unitSheetsSort('T0',false);
  assert.deepEqual(h.calls.at(-2).ids,['r-b']);
  assert.equal(h.calls.at(-2).view,'rules:pool');assert.equal(h.get('USHEET.rect'),null);
 });
 await check('rule undo flushes a pending cell and clears schema-dependent layout',async()=>{
  const h=harness();await h.c.unitSheetsOpen();h.set("USHEET.view='rules:pool'");
  h.response.columns=['T0'];h.response.field_info={T0:{type:'number',view:'rules:pool'}};
  await h.c.unitSheetsRequest('query');
  h.c.unitSheetsInput(0,1,'7');
  h.set("USHEET.where={column:'T0',op:'eq',value:7};USHEET.sort=[{column:'T0'}]");
  await h.c.unitSheetsUndo(false);await h.get('USHEET.queue');
  assert.equal(h.calls.at(-1).project.draft.second,undefined);
  assert.equal(h.calls.at(-1).where,null);assert.deepEqual(h.calls.at(-1).sort,[{column:'id',desc:false}]);
 });
 assert.equal(failures.length,0,failures.join('\n'));
}
(async()=>{
 const h=harness();await h.c.unitSheetsOpen();
 await Promise.all([h.c.unitSheetsRequest('operate',{ids:['second'],column:'attack',value:6},true),h.c.unitSheetsRequest('operate',{ids:['first'],column:'attack',value:10},true)]);
 assert.deepEqual(h.get('Object.keys(USHEET.data.project.draft)'),['second','first']);
 assert.equal(h.get('USHEET.past.length'),2);assert.notEqual(h.calls[1].revision,h.calls[2].revision);
 h.set("USHEET.view='classification'; USHEET.order=['Tier','id'];USHEET.hidden=['id'];USHEET.showExtras=true");
 assert.equal(h.c.unitSheetsColumns()[0],'id');h.c.unitSheetsPaint();
 assert(!h.c.modal.innerHTML.includes("unitSheetsSort('extra:"));assert(h.c.modal.innerHTML.includes('this.dataset.sort'));
 const p=harness();await p.c.unitSheetsOpen();p.set("USHEET.view='base'");let pasted;
 p.c.unitSheetsRequest=async(a,b)=>{pasted={a,b};};
 await p.c.unitSheetsPaste({clipboardData:{getData:()=>"12\n0"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'1'}}});
 assert.deepEqual(pasted.b.cells.map(c=>[c.id,c.value]),[['second','12'],['first','0']]);
 await p.c.unitSheetsPaste({clipboardData:{getData:()=>"\t99\n\t88"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'0'}}});
 assert.equal(pasted.b.cells.length,2);assert.equal(pasted.b.cells[0].column,'attack');
 const d=harness();await d.c.unitSheetsOpen();d.c.unitSheetsInput(0,1,'Elf');await d.c.unitSheetsFlush();
 assert.equal(d.calls.filter(c=>c.column==='Unit Race').length,1);assert.equal(d.calls.at(-1).ids[0],'second');
 const q=harness();await q.c.unitSheetsOpen();
 q.elements.usUltra={value:'3'};q.elements.usDefenseWeight={value:'.6'};
 const edit=q.c.unitSheetsRequest('operate',{ids:['second'],column:'attack',value:7},true);
 q.c.unitSheetsComparison();await edit;await q.get('USHEET.queue');
 assert.equal(q.get('USHEET.data.project.draft.second.attack'),7,'comparison save must preserve the queued edit');
 assert.equal(q.get('USHEET.data.project.comparison.ultra_size'),3);
 assert.equal(q.get('USHEET.past.length'),2);
 const b=harness();await b.c.unitSheetsOpen();b.set("USHEET.view='rules'");
 // Model the DOM replacing its checkboxes whenever the balance panel repaints.
 let stages=['replenish'];
 b.c.modal.querySelectorAll=()=>stages.map(value=>({value}));
 Object.defineProperty(b.c.modal,'innerHTML',{set(html){stages=[...html.matchAll(/<input[^>]*class="us-stage"[^>]*>/g)].filter(m=>/\bchecked\b/.test(m[0])).map(m=>m[0].match(/value="([^"]+)"/)[1]);}});
 b.c.api.post=async(url,body)=>{
  b.calls.push(structuredClone(body));
  if(url.endsWith('/balance_preview'))return {stages:body.stages,profile:{},logs:{},structure:{},changed_fields:0};
  return {text:'',mime:'application/zip',name:'balance.zip'};
 };
 b.elements.usIntermediate={checked:false};b.c.atob=()=>'';b.c.Blob=class {};b.c.URL={createObjectURL:()=>'',revokeObjectURL(){}};
 b.c.document.createElement=()=>({click(){}});
 await b.c.unitSheetsBalancePreview();
 assert.deepEqual(stages,['replenish'],'preview repaint must keep the chosen stages');
 await b.c.unitSheetsBalanceExport();
 assert.deepEqual(b.calls.at(-1).stages,['replenish'],'export must use the stages selected before preview');
 const m=harness();await m.c.unitSheetsOpen();m.set("USHEET.view='recruitment'");m.c.unitSheetsPaint();
 assert(!/<button[^>]*onclick="unitSheetsMissing\(\)"/.test(m.c.modal.innerHTML),'Recruitment must not offer a filter for a field it lacks');
 const before=m.calls.length;m.c.unitSheetsMissing();await m.get('USHEET.queue');
 assert.equal(m.calls.length,before,'Recruitment must not send the missing-classification filter');
 m.set("USHEET.view='classification'");m.c.unitSheetsPaint();
 assert(/<button[^>]*onclick="unitSheetsMissing\(\)"/.test(m.c.modal.innerHTML));
 await m.c.unitSheetsMissing();await m.get('USHEET.queue');
 assert.equal(m.calls.at(-1).where.column,'needs_classification');

 const g=harness();await g.c.unitSheetsOpen();
 g.set("USHEET.view='base';USHEET.compareGroup='Archers';USHEET.selected=new Set(['second','first'])");
 g.response.table={rows:[g.response.table.rows[1]],total:1,matched_ids:['first']};
 const filtering=g.c.unitSheetsFilter();
 await g.c.unitSheetsGroupAction('add');await filtering;
 assert.deepEqual(g.calls.at(-1).ids,['first'],'group add must wait for filters and prune hidden IDs');
 assert.equal(g.calls.at(-1).operation,'add');
 assert.equal(g.calls.at(-1).name,'Archers');
 g.set("USHEET.data.comparison_group={name:'Archers',columns:['attack'],statistics:{attack:{min:5,max:9,average:7,count:2}},members:[{id:'<missing>',missing:true,difference:{attack:null}},{id:'first',attack:9,difference:{attack:2}}]}");
 const comparison=g.c.unitSheetsGroupsHtml();
 assert(comparison.includes('&lt;missing&gt;'));
 assert(comparison.includes('sheets.group_missing'));
 assert(comparison.includes('sheets.group_average'));
 assert(!comparison.includes('oninput='),'comparison must be read-only');
 g.c.unitSheetsPaint();
 assert(g.c.modal.innerHTML.includes('us-kind-native'));
 assert(g.c.modal.innerHTML.includes('sheets.kind_derived'));
 assert.equal(g.c.unitSheetsColumnKind('Tier'),'annotation');
 assert.equal(g.c.unitSheetsColumnKind('defense_total'),'derived');
 assert.equal(g.c.unitSheetsColumnKind('attack'),'native');
 await safetyRegressions();
 console.log('PASS: queued edits and project saves, current revisions, stable IDs, frozen identity, safe column handlers, rectangular paste, explicit zero, pending-input flush, balance stage retention and view-safe missing filter');
 // The server answers a refused request with {error}, not a thrown HTTP error.
 const refused=harness();await refused.c.unitSheetsOpen();
 refused.c.api.post=async()=>({error:'refused by server'});
 assert.equal(await refused.c.unitSheetsRequest('operate',{ids:['first'],column:'attack',value:'x'},true),false);
 assert.equal(refused.get('USHEET.err'),'refused by server');
 let toasted='';refused.c.toast=m=>{toasted=m;};
 refused.set('USHEET.native={units:1,plan_token:"t",files:[]}');refused.c.confirm=()=>true;
 await refused.c.unitSheetsNativeApply();
 assert.equal(toasted,'refused by server');
 console.log('PASS: refused requests show the server reason instead of passing as success');
})().catch(e=>{console.error(e);process.exitCode=1;});
