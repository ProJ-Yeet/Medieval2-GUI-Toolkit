/* Phase 115: actual handlers, explicit mapping and preview before staging. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const calls=[],elements={},downloads=[];
const data={project:{units:{},draft:{},rules:{replenish:[],experience:[],pool:[]},views:{},recipes:{},comparison:{}},
 revision:'r0',source_token:'s',columns:['attack','attributes'],field_info:{attack:{type:'int',view:'base'},attributes:{type:'list',view:'attributes'}},extra_columns:[],
 refresh:{added:[],removed:[],missing_classifications:[],rename_candidates:[]},table:{rows:[],matched_ids:[],total:0}};
const c={console,Set,Map,Promise,structuredClone,setTimeout,clearTimeout,Uint8Array,Blob,atob,btoa,
 state:{src:'fixture'},modal:{innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null},overlay:{classList:{add(){}}},
 document:{getElementById:id=>elements[id],createElement:()=>({click(){downloads.push(this.download);}})},
 URL:{createObjectURL:()=>'',revokeObjectURL(){}},tt:k=>k,ttA:k=>k,toast(){},errText:e=>e.message,
 esc:v=>String(v).replace(/</g,'&lt;').replace(/"/g,'&quot;'),
 api:{post:async(url,body)=>{calls.push({url,body:structuredClone(body)});
  if(url.endsWith('interchange_inspect'))return {sheets:[{name:'Base stats',rows:[{number:1,values:['A','Attack','Attack']},{number:2,values:['Guard','0','8']}]}]};
  if(url.endsWith('interchange_preview'))return {preview_token:'t',ids:['Guard'],fields:['attack'],changes:[{id:'Guard',column:'attack',after:0}],ignored:[],formula_issues:[]};
  if(url.endsWith('interchange_export'))return {name:'base.xlsx',mime:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',encoding:'base64',text:'UEs='};
  return structuredClone(data);}}};
vm.createContext(c);vm.runInContext(fs.readFileSync('web/js/unitsheets.js','utf8'),c);
(async()=>{
 await c.unitSheetsOpen();
 assert(c.modal.innerHTML.includes('.xlsx'));
 elements.usImportKind={value:'sheet'};
 await c.unitSheetsImport({files:[{name:'synthetic.xlsx',size:2,arrayBuffer:async()=>new Uint8Array([80,75]).buffer}]});
 assert(calls.some(x=>x.url.endsWith('interchange_inspect')));
 assert(!calls.some(x=>x.url.endsWith('interchange_import')));
 assert(c.modal.innerHTML.includes('unitSheetsMappingColumn'));
 c.unitSheetsMappingColumn(0,0,'id');c.unitSheetsMappingColumn(0,2,'attack');
 await c.unitSheetsInterchangePreview();
 assert(c.modal.innerHTML.includes('Guard'));assert(c.modal.innerHTML.includes('sheets.interchange_stage'));
 assert(!calls.some(x=>x.url.endsWith('interchange_import')));
 await c.unitSheetsInterchangeStage();
 const staged=calls.find(x=>x.url.endsWith('interchange_import'));
 assert.equal(staged.body.preview_token,'t');assert.equal(staged.body.plans[0].mapping.attack,2);
 assert.equal(vm.runInContext('USHEET.past.length',c),0,'identical response has no undo entry');
 // Mapping changes invalidate the old preview.
 c.unitSheetsMappingColumn(0,1,'attack');
 assert.equal(vm.runInContext('USHEET.interchange.preview',c),null);
 c.unitSheetsMappingColumn(0,1,'attributes');c.unitSheetsMappingColumn(0,2,'attributes');
 assert.deepEqual(Array.from(vm.runInContext('USHEET.interchange.plans[0].mapping.attributes',c)),[1,2]);
 c.unitSheetsMappingColumn(0,1,'');
 assert.deepEqual(Array.from(vm.runInContext('USHEET.interchange.plans[0].mapping.attributes',c)),[2]);
 elements.usExportFormat={value:'xlsx'};elements.usExportFormulas={value:'supported'};elements.usExportLayout={value:'imported'};
 await c.unitSheetsExport('sheet');
 assert.equal(downloads[0],'base.xlsx');
 const exported=calls.find(x=>x.url.endsWith('interchange_export'));
 assert.equal(exported.body.formulas,'supported');assert.equal(exported.body.layout,'imported');
 console.log('PASS: XLSX selection, duplicate column mapping, preview, explicit stage, invalidation and download choice');
})().catch(e=>{console.error(e);process.exitCode=1;});
