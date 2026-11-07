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
  tt:(key,p)=>key,ttA:key=>key,toast(){},errText:e=>e.message,
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
 return {c,calls,elements,get:u=>vm.runInContext(u,c),set:s=>vm.runInContext(s,c)};
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
 p.c.unitSheetsPaste({clipboardData:{getData:()=>"12\n0"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'1'}}});
 assert.deepEqual(pasted.b.cells.map(c=>[c.id,c.value]),[['second','12'],['first','0']]);
 p.c.unitSheetsPaste({clipboardData:{getData:()=>"\t99\n\t88"},preventDefault(){},currentTarget:{dataset:{r:'0',c:'0'}}});
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
 m.c.unitSheetsMissing();await m.get('USHEET.queue');
 assert.equal(m.calls.at(-1).where.column,'needs_classification');
 console.log('PASS: queued edits and project saves, current revisions, stable IDs, frozen identity, safe column handlers, rectangular paste, explicit zero, pending-input flush, balance stage retention and view-safe missing filter');
})().catch(e=>{console.error(e);process.exitCode=1;});
