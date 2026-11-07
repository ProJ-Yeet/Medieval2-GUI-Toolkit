/* Native editable unit sheets. Project config is saved; game edits stay staged. */
let USHEET=null;
const USHEET_CATEGORY=Object.keys({'Category':0})[0];
const USHEET_META=Object.keys({'Unit Race':0,'Tier':0,'Main Faction':0,'AOR':0,'Category override':0});
async function unitSheetsOpen(){
 const mod=state.src || state.dst;
 if(!mod){toast(tt('sheets.pick_mod'));return;}
 USHEET={mod,view:'classification',offset:0,where:null,sort:[{column:'id',desc:false}],selected:new Set(),past:[],future:[],busy:false,hidden:[],order:[],filterRows:[],group:'all',balanceStages:['replenish','experience','pool']};
 // Draft controls belong to the window, not the project or undo snapshots.
 USHEET.controls={usMassDetails:false,usBalanceDetails:true,usMassColumn:'',usMassOp:'set',
  usMassValue:'',usMassOther:'',usMassMode:'selected',usRecipeName:'',usRecipePicker:'',
  usProfileRecipe:'',usProfileRecipeName:'',usProfileRecipeColumn:'',
  usProfileRecipeOp:'set',usProfileRecipeValue:''};
 modal.className='modal wide';modal.innerHTML=`<div class="count">${tt('sheets.loading')}</div>`;overlay.classList.add('open');
 await unitSheetsRequest('load');
}
function unitSheetsBody(extra={}){
 const u=USHEET;return Object.assign({mod:u.mod,revision:u.data&&u.data.revision,source_token:u.data&&u.data.source_token,
  view:u.view,where:u.where,sort:u.sort,offset:u.offset,limit:75,mode:'selected',comparison_group:u.compareGroup},extra);
}
async function unitSheetsRequest(action,extra={},history=false){
 const u=USHEET;if(!u)return false;
 const pending=(u.queue||Promise.resolve()).then(()=>USHEET===u?unitSheetsRequestNow(action,extra,history):false);
 u.queue=pending.catch(()=>false);return pending;
}
// api.post hands back a refusal as {error}; every caller here treats a resolved
// answer as success, so turn the refusal into the error its catch expects.
async function unitSheetsPost(url,body){
 const r=await api.post(url,body);
 if(r&&r.error)throw new Error(r.error);
 return r;
}
async function unitSheetsRequestNow(action,extra={},history=false){
 const u=USHEET;if(!u || u.busy)return false;u.busy=true;
 const prior=u.data?JSON.stringify(u.data.project):null;
 try{
  if(typeof extra==='function')extra=extra();
  const r=await unitSheetsPost('/api/unit_sheets/'+action,unitSheetsBody(extra));
  if(USHEET!==u)return false;
  if(history&&prior&&JSON.stringify(r.project)!==prior){u.past.push(prior);if(u.past.length>20)u.past.shift();u.future=[];}
  if(history){u.native=null;u.balance=null;}
  const before=u.data&&u.data.table.rows.map(row=>row.id);
  if(before&&JSON.stringify(before)!==JSON.stringify(r.table.rows.map(row=>row.id))){
   unitSheetsClearRect();
  }
  u.data=r;unitSheetsRestoreFilters();unitSheetsPruneSelection();u.err='';unitSheetsPaint();return true;
 }catch(err){if(USHEET===u){u.err=errText(err);unitSheetsPaint();}return false;}
 finally{u.busy=false;}
}
function unitSheetsColumns(includeHidden=false){
 const u=USHEET,d=u.data;let cols;
 if(unitSheetsRuleKind())cols=['id',...d.columns];
 else if(u.view==='recruitment')cols=['id','unit','building','building_type','level','building_depth','building_tier','settlement','section','initial','per_turn','maximum','experience','requires',...USHEET_META,USHEET_CATEGORY];
 else if(u.view==='classification')cols=['id',...USHEET_META,USHEET_CATEGORY,'groups','needs_classification'];
 else cols=['id',...Object.keys(d.field_info).filter(k=>d.field_info[k].view===u.view),
   ...(u.view==='base'?['groups','defense_total','ultra_size','cost_efficiency','upkeep_efficiency',
    ...Object.keys(d.filter_info||{}).filter(key=>/^(pri|sec)_(weapon|tech)_type$/.test(key))]:[])];
 if(u.showExtras&&!unitSheetsRuleKind())cols.push(...d.extra_columns);
 if(u.order.length)cols.sort((a,b)=>(u.order.includes(a)?u.order.indexOf(a):999)-(u.order.includes(b)?u.order.indexOf(b):999));
 const frozen=unitSheetsRuleKind()?(d.frozen_columns||['id']):['id'];
 return [...frozen,...cols.filter(k=>!frozen.includes(k)&&(includeHidden||!u.hidden.includes(k)))];
}
function unitSheetsColumnLabel(column){
 const labels={
  pri_weapon_type:tt('sheets.pri_weapon_type'),pri_tech_type:tt('sheets.pri_tech_type'),
  sec_weapon_type:tt('sheets.sec_weapon_type'),sec_tech_type:tt('sheets.sec_tech_type'),
  building_depth:tt('sheets.building_depth'),building_tier:tt('sheets.building_tier'),
  building_type:tt('sheets.building_type'),groups:tt('sheets.groups')
 };
 return labels[column]||column;
}
function unitSheetsValue(v){return Array.isArray(v)?v.join(', '):v==null?'':String(v);}
function unitSheetsEditable(col){
 if(unitSheetsRuleKind())return col!=='id'&&!!USHEET.data.field_info[col];
 return USHEET.view!=='recruitment'&&(USHEET_META.includes(col)||!!USHEET.data.field_info[col]);}
function unitSheetsRememberControl(control){
 // Record edits before a queued request can rebuild the window.
 USHEET.controls[control.id]=control.tagName==='DETAILS'?control.open:control.value;
}
function unitSheetsPaint(){
 const u=USHEET;if(!u || !u.data){if(u&&u.err)modal.innerHTML=`<div class="w-bad">${esc(u.err)}</div>`;return;}
 const d=u.data,cols=unitSheetsColumns(),table=d.table;
 const controls=u.controls;
 const massColumns=unitSheetsRuleKind()?d.columns:[...USHEET_META,...d.columns];
 const massOperations=unitSheetsRuleKind()?['set','clear','copy']:
  ['set','clear','add','subtract','multiply','divide','percent','min','max','round',
   'copy','expression','replace','append','remove','deduplicate'];
 // A view or schema change can remove a previously valid choice.
 if(!massColumns.includes(controls.usMassColumn))controls.usMassColumn=massColumns[0]??'';
 if(!massOperations.includes(controls.usMassOp))controls.usMassOp=massOperations[0];
 const tabs=[['classification',tt('sheets.classification')],['base',tt('sheets.base')],['attributes',tt('sheets.attributes')],['soft',tt('sheets.soft')],['rules:replenish',tt('sheets.rules')],['recruitment',tt('sheets.recruitment')]];
 const option=col=>`<option value="${esc(col)}">${esc(col)}</option>`;
 const filterCols=Object.keys(d.filter_info||{});
 modal.innerHTML=`<div class="unit-sheets" onkeydown="unitSheetsKey(event)">
 <h3>${tt('sheets.title')} · ${esc(u.mod)}</h3>
 <div class="count">${tt('sheets.staged_note')}</div>
 <div class="count">${tt('sheets.formulas')}</div>
 <div class="barrow">${tabs.map(([id,label])=>`<button class="mini${u.view===id?' primary':''}" onclick="unitSheetsTab('${id}')">${label}</button>`).join('')}
 <button class="mini" onclick="unitSheetsRequest('load')">${tt('sheets.refresh')}</button>
 <button class="mini" onclick="unitSheetsUndo(false)"${u.past.length?'':' disabled'}>↶</button><button class="mini" onclick="unitSheetsUndo(true)"${u.future.length?'':' disabled'}>↷</button></div>
 ${d.stale_drafts&&d.stale_drafts.length?`<div class="w-bad">${tt('sheets.stale_drafts')} ${esc(d.stale_drafts.join(', '))}</div>`:''}
 ${u.err?`<div class="w-bad">${esc(u.err)}</div>`:''}
 <div class="count">${tt('sheets.refresh_summary',{added:d.refresh.added.length,removed:d.refresh.removed.length,missing:d.refresh.missing_classifications.length})}</div>
 ${d.refresh.rename_candidates.length?`<details><summary>${tt('sheets.renames')}</summary>${d.refresh.rename_candidates.map((r,i)=>`<div>${esc(r.from)} → ${esc(r.to)} <button onclick="unitSheetsRename(${i})">${tt('sheets.transfer_notes')}</button></div>`).join('')}</details>`:''}
 <details><summary>${tt('sheets.import_export')}</summary><div class="barrow"><select id="usImportKind"><option value="csv">${tt('sheets.import_csv')}</option><option value="edu_json">${tt('sheets.import_edu_json')}</option><option value="edb_json">${tt('sheets.import_edb_json')}</option><option value="project">${tt('sheets.import_project')}</option><option value="replenish">${tt('sheets.import_replenish')}</option><option value="experience">${tt('sheets.import_experience')}</option><option value="pool">${tt('sheets.import_pool')}</option></select>
 <input type="file" accept=".csv,.json" onchange="unitSheetsImport(this)">
 <button onclick="unitSheetsExport('project')">${tt('sheets.export_project')}</button><button onclick="unitSheetsExport('reference')">${tt('sheets.export_reference')}</button></div>
 <label>${tt('sheets.column_mapping')}<input id="usMapping" placeholder="${ttA('sheets.mapping_example')}"></label></details>
 ${unitSheetsGroupsHtml()}
 <div class="barrow us-legend">${['native','annotation','derived'].map(kind=>`<span class="us-kind-${kind}">${unitSheetsKindLabel(kind)}</span>`).join('')}</div>
 ${unitSheetsRuleKind()?unitSheetsRulesHtml():''}
 <details${u.filterRows.length||u.advancedFilter?' open':''}><summary>${tt('sheets.filters')}</summary>
 <div class="count" id="usActiveFilter">${esc(unitSheetsFilterSummary())} | ${tt('sheets.active_filter_count',{count:table.total})}</div>
 <div id="usFilters">${u.filterRows.map((f,i)=>unitSheetsFilterRow(f,i,filterCols)).join('')}</div>
 <div class="barrow"><button onclick="USHEET.filterRows.push({column:'id',op:'contains',value:''});unitSheetsPaint()">${tt('sheets.add_filter')}</button><select onchange="USHEET.group=this.value"><option value="all"${u.group==='all'?' selected':''}>${tt('sheets.and')}</option><option value="any"${u.group==='any'?' selected':''}>${tt('sheets.or')}</option></select>
 <button onclick="unitSheetsFilter()">${tt('sheets.filter_apply')}</button>${u.view==='recruitment'||unitSheetsRuleKind()?'':`<button onclick="unitSheetsMissing()">${tt('sheets.missing_only')}</button>`}<button onclick="unitSheetsClearFilters()">${tt('sheets.clear_filters')}</button></div>
 <label>${tt('sheets.advanced_filter')}<textarea id="usAdvanced" rows="3" style="width:100%">${esc(JSON.stringify(u.where||{}))}</textarea></label><button onclick="unitSheetsAdvanced()">${tt('sheets.filter_apply')}</button></details>
 <details><summary>${tt('sheets.columns_views')}</summary><div class="barrow"><input id="usViewName" placeholder="${ttA('sheets.view_name')}"><button onclick="unitSheetsSaveView()">${tt('sheets.save_view')}</button><select onchange="unitSheetsLoadView(this.value)"><option value="">${tt('sheets.saved_views')}</option>${Object.keys(d.project.views).map(option).join('')}</select></div>
 <label><input type="checkbox"${u.showExtras?' checked':''} onchange="unitSheetsExtras(this.checked)">${tt('sheets.show_extras')}</label><label>${tt('sheets.visible_columns')}<textarea id="usColumns" rows="2" style="width:100%">${esc(cols.join(', '))}</textarea></label><button onclick="unitSheetsSetColumns()">${tt('sheets.columns_apply')}</button>
 <label>${tt('sheets.comparison')}<input id="usUltra" type="number" step="any" value="${d.project.comparison.ultra_size}"><input id="usDefenseWeight" type="number" step="any" value="${d.project.comparison.defense_weight}"><button onclick="unitSheetsComparison()">${tt('common.save')}</button></label></details>
 <div class="barrow"><span>${tt('sheets.rows_count',{matches:table.total,selected:u.selected.size})}</span><button onclick="unitSheetsSelectMatches()">${tt('sheets.select_matches')}</button><button onclick="USHEET.selected.clear();unitSheetsPaint()">${tt('sheets.select_none')}</button>
 <button onclick="unitSheetsPage(-1)"${u.offset?'':' disabled'}>◀</button><span>${u.offset+1}–${Math.min(u.offset+75,table.total)}</span><button onclick="unitSheetsPage(1)"${u.offset+75<table.total?'':' disabled'}>▶</button></div>
 <div class="us-grid" style="max-height:55vh;overflow:auto">${unitSheetsGridOpen(cols)}<thead><tr><th>✓</th>${cols.map((k,c)=>`<th class="us-kind-${unitSheetsColumnKind(k)}" ${unitSheetsFrozenStyle(k,true)} data-sort="${esc(k)}" onclick="unitSheetsSort(this.dataset.sort,event.shiftKey)" title="${ttA('sheets.sort_hint')}">${esc(unitSheetsColumnLabel(k))}</th>`).join('')}</tr></thead><tbody>
 ${table.rows.map((row,r)=>`<tr class="${row.changed?'us-changed':''}"><td><input type="checkbox"${u.selected.has(row.id)?' checked':''} onchange="unitSheetsSelect(${r},this.checked)"></td>${cols.map((col,c)=>`<td class="us-kind-${unitSheetsColumnKind(col)}" ${unitSheetsFrozenStyle(col)} data-r="${r}" data-c="${c}" onmousedown="unitSheetsRect(event,${r},${c})">${unitSheetsEditable(col)?`<input data-r="${r}" data-c="${c}" data-col="${esc(col)}" value="${esc(unitSheetsValue(row[col]))}" oninput="unitSheetsInput(${r},${c},this.value)" onchange="unitSheetsCell(${r},${c},this.value)" onkeydown="unitSheetsCellKey(event)" onpaste="unitSheetsPaste(event)">`:`<span>${esc(unitSheetsValue(row[col]))}</span>`}</td>`).join('')}</tr>`).join('')}
 </tbody></table></div>
 <details id="usMassDetails"${controls.usMassDetails?' open':''}${u.view==='recruitment'?' hidden':''} ontoggle="unitSheetsRememberControl(this)"><summary>${tt('sheets.mass_edit')}</summary><div class="barrow"><select id="usMassColumn" onchange="unitSheetsRememberControl(this)">${massColumns.map(col=>`<option value="${esc(col)}"${col===controls.usMassColumn?' selected':''}>${esc(col)}</option>`).join('')}</select><select id="usMassOp" onchange="unitSheetsRememberControl(this)">${massOperations.map(k=>`<option${k===controls.usMassOp?' selected':''}>${k}</option>`).join('')}</select>
 <input id="usMassValue" value="${esc(controls.usMassValue)}" oninput="unitSheetsRememberControl(this)" onchange="unitSheetsRememberControl(this)" placeholder="${ttA('sheets.value')}"><input id="usMassOther" value="${esc(controls.usMassOther)}" oninput="unitSheetsRememberControl(this)" onchange="unitSheetsRememberControl(this)" placeholder="${ttA('sheets.replacement')}"><select id="usMassMode" onchange="unitSheetsRememberControl(this)"><option value="selected"${controls.usMassMode==='selected'?' selected':''}>${tt('sheets.mode_selected')}</option><option value="matching"${controls.usMassMode==='matching'?' selected':''}>${tt('sheets.mode_matching')}</option></select><button onclick="unitSheetsMass()">${tt('sheets.stage_selected')}</button><button onclick="unitSheetsFill()">${tt('sheets.fill_down')}</button></div><div class="count">${tt('sheets.fill_page_note')}</div>
 <div class="barrow"><input id="usRecipeName" value="${esc(controls.usRecipeName)}" oninput="unitSheetsRememberControl(this)" onchange="unitSheetsRememberControl(this)" placeholder="${ttA('sheets.recipe_name')}"><button onclick="unitSheetsSaveRecipe()">${tt('common.save')}</button><select id="usRecipePicker" onchange="unitSheetsRememberControl(this);unitSheetsLoadRecipe(this.value)"><option value="">${tt('sheets.recipes')}</option>${unitSheetsRecipeOptions()}</select><button onclick="unitSheetsRunRecipe(document.getElementById('usRecipePicker').value)">${tt('sheets.recipe_run')}</button></div></details>
 ${unitSheetsReviewHtml()}
 ${d.changes?`<details open><summary>${tt('sheets.change_preview')}</summary><pre style="max-height:180px;overflow:auto">${esc(JSON.stringify(d.changes,null,2))}</pre></details>`:''}
 ${u.native?`<details open><summary>${tt('sheets.native_review',{count:u.native.units})}</summary><pre style="max-height:240px;overflow:auto">${esc(u.native.files.map(f=>f.diff).join('\n\n'))}</pre><button onclick="unitSheetsNativeApply()">${tt('sheets.native_apply')}</button></details>`:''}
 <div class="foot"><button onclick="unitSheetsNativePreview()">${tt('sheets.native_preview')}</button><button onclick="unitSheetsDiscard()">${tt('sheets.discard_native')}</button><button onclick="closeModal()">${tt('common.close')}</button></div></div>`;
 unitSheetsRectPaint();
}
function unitSheetsClearRect(){
 USHEET.rect=null;
 USHEET.anchor=null;
}
function unitSheetsPruneSelection(){
 // Only matching stable IDs may remain in the multi-row edit set.
 const u=USHEET,matching=new Set(u.data.table.matched_ids);
 u.selected=new Set([...u.selected].filter(id=>matching.has(id)));
}
function unitSheetsLayout(change,query=true){
 const u=USHEET;
 // Serialize layout changes so each flush still uses the preceding view.
 const pending=(u.layout||Promise.resolve()).then(async()=>{
  if(USHEET!==u)return;
  await unitSheetsFlush();
  if(USHEET!==u)return;
  unitSheetsClearRect();
  change(u);
  unitSheetsRestoreFilters();
  if(query)return unitSheetsRequest('query');
  unitSheetsPaint();
 });
 u.layout=pending.catch(()=>false);
 return pending;
}
function unitSheetsTab(view){
 return unitSheetsLayout(u=>{
  u.view=view==='rules'?'rules:replenish':view;u.offset=0;u.hidden=[];u.order=[];u.where=null;u.filterRows=[];
  u.selected.clear();u.sort=[{column:'id',desc:false}];
 });
}
function unitSheetsSelect(index,on){const id=USHEET.data.table.rows[index].id;on?USHEET.selected.add(id):USHEET.selected.delete(id);unitSheetsPaint();}
function unitSheetsSelectMatches(){
 USHEET.selected=new Set(USHEET.data.table.matched_ids);
 unitSheetsPaint();
}
function unitSheetsPage(dir){
 return unitSheetsLayout(u=>{u.offset=Math.max(0,u.offset+dir*75);});
}
function unitSheetsSort(column,add){
 return unitSheetsLayout(u=>{
  const old=u.sort.find(s=>s.column===column);
  u.sort=add?u.sort.filter(s=>s.column!==column):[];
  u.sort.push({column,desc:old?!old.desc:false});
 });
}
function unitSheetsFilterOpLabel(op){
 const labels={
  eq:tt('sheets.filter_op_eq'),ne:tt('sheets.filter_op_ne'),
  contains:tt('sheets.filter_op_contains'),not_contains:tt('sheets.filter_op_not_contains'),
  gt:tt('sheets.filter_op_gt'),ge:tt('sheets.filter_op_ge'),
  lt:tt('sheets.filter_op_lt'),le:tt('sheets.filter_op_le'),
  blank:tt('sheets.filter_op_blank'),missing:tt('sheets.filter_op_missing'),invalid:tt('sheets.filter_op_invalid')
 };
 return labels[op]||op;
}
function unitSheetsFilterOps(column){
 const kind=USHEET.data.filter_info?.[column]?.type||'text';
 const ops=['eq','ne'];
 if(kind==='text'||kind==='list')ops.push('contains','not_contains');
 if(kind==='number')ops.push('gt','ge','lt','le');
 ops.push('blank','missing');
 if(kind!=='bool')ops.push('invalid');
 return ops;
}
function unitSheetsFilterColumn(index,column){
 // Reset incompatible operators and values when the column type changes.
 const row=USHEET.filterRows[index];
 row.column=column;
 row.op='eq';
 row.value=USHEET.data.filter_info?.[column]?.type==='bool'?true:'';
 unitSheetsPaint();
}
function unitSheetsFilterOperator(index,op){
 const row=USHEET.filterRows[index];
 row.op=op;
 // A saved unary clause has no value to reuse when equality is selected.
 if(row.value===undefined){
  row.value=USHEET.data.filter_info?.[row.column]?.type==='bool'?true:'';
 }
 unitSheetsPaint();
}
function unitSheetsFilterRow(row,index,columns){
 const kind=USHEET.data.filter_info?.[row.column]?.type||'text';
 const unary=['blank','missing','invalid'].includes(row.op);
 const columnMenu=columns.map(column=>`<option value="${esc(column)}"${row.column===column?' selected':''}>${esc(unitSheetsColumnLabel(column))}</option>`).join('');
 const opMenu=unitSheetsFilterOps(row.column).map(op=>`<option value="${op}"${row.op===op?' selected':''}>${unitSheetsFilterOpLabel(op)}</option>`).join('');
 let valueControl='';
 if(!unary){
  if(kind==='bool'){
   valueControl=`<select onchange="USHEET.filterRows[${index}].value=this.value==='true'">${[true,false].map(value=>`<option value="${value}"${String(row.value)===String(value)?' selected':''}>${value?tt('sheets.filter_bool_true'):tt('sheets.filter_bool_false')}</option>`).join('')}</select>`;
  }else{
   valueControl=`<input type="${kind==='number'?'number':'text'}" step="any" value="${esc(row.value??'')}" oninput="USHEET.filterRows[${index}].value=this.value">`;
  }
 }
 return `<div class="barrow"><select onchange="unitSheetsFilterColumn(${index},this.value)">${columnMenu}</select>
 <select onchange="unitSheetsFilterOperator(${index},this.value)">${opMenu}</select>${valueControl}
 <button onclick="USHEET.filterRows.splice(${index},1);unitSheetsPaint()">&#215;</button></div>`;
}
function unitSheetsRestoreFilters(){
 const u=USHEET,where=u.where;
 const leaf=expr=>expr&&typeof expr.column==='string'&&
  Object.keys(expr).every(key=>['column','op','value'].includes(key))&&
  (!u.data?.filter_info||u.data.filter_info[expr.column])&&
  unitSheetsFilterOps(expr.column).includes(expr.op||'eq');
 let rows=[],group='all';
 if(where&&Object.keys(where).length){
  if(leaf(where))rows=[where];
  else if(Object.keys(where).length===1&&
   ['all','any'].some(key=>Array.isArray(where[key])&&where[key].every(leaf))){
   group=Array.isArray(where.all)?'all':'any';
   rows=where[group];
  }else{
   // Nested expressions cannot be represented by the flat visual builder.
   u.filterRows=[];u.advancedFilter=true;
   return;
  }
 }
 u.group=group;
 u.filterRows=structuredClone(rows).map(row=>{
  const restored={...row,op:row.op||'eq'};
  if(u.data?.filter_info?.[row.column]?.type==='bool'&&typeof row.value==='string'){
   restored.value=row.value.trim().toLowerCase()==='true';
  }
  return restored;
 });
 u.advancedFilter=false;
}
function unitSheetsFilterSummary(){
 const u=USHEET;
 function describe(expr,depth=0){
  if(!expr||!Object.keys(expr).length)return tt('sheets.no_active_filter');
  if(depth>8)return tt('sheets.advanced_active');
  for(const group of ['all','any']){
   if(Array.isArray(expr[group])){
    if(!expr[group].length){
     return group==='all'?tt('sheets.filter_empty_all'):tt('sheets.filter_empty_any');
    }
    const parts=expr[group].map(child=>describe(child,depth+1));
    const expression=parts.reduce((left,right)=>group==='all'?
     tt('sheets.filter_all_join',{left,right}):tt('sheets.filter_any_join',{left,right}));
    return tt('sheets.filter_group',{expression});
   }
  }
  if(expr.not)return tt('sheets.filter_not',{expression:describe(expr.not,depth+1)});
  const op=expr.op||'eq';
  const column=unitSheetsColumnLabel(expr.column),operator=unitSheetsFilterOpLabel(op);
  if(['blank','missing','invalid'].includes(op)){
   return tt('sheets.filter_unary',{column,operator});
  }
  const value=typeof expr.value==='boolean'?
   (expr.value?tt('sheets.filter_bool_true'):tt('sheets.filter_bool_false')):
   unitSheetsValue(expr.value);
  return tt('sheets.filter_clause',{column,operator,value});
 }
 const summary=describe(u.where);
 const compact=summary.length>240?summary.slice(0,237)+'...':summary;
 return u.advancedFilter?tt('sheets.advanced_summary',{expression:compact}):compact;
}

function unitSheetsFilter(){
 const rows=structuredClone(USHEET.filterRows);
 for(const row of rows){
  if(USHEET.data.filter_info?.[row.column]?.type==='bool'&&typeof row.value==='string'){
   row.value=row.value.trim().toLowerCase()==='true';
  }
 }
 const where={[USHEET.group]:rows};
 return unitSheetsLayout(u=>{u.where=where;u.offset=0;});
}
function unitSheetsMissing(){
 if(USHEET.view==='recruitment'||unitSheetsRuleKind())return;
 return unitSheetsLayout(u=>{
  u.where={column:'needs_classification',op:'eq',value:true};u.offset=0;
 });
}
function unitSheetsClearFilters(){
 return unitSheetsLayout(u=>{u.where=null;u.filterRows=[];u.offset=0;});
}
function unitSheetsAdvanced(){
 try{
  const where=JSON.parse(document.getElementById('usAdvanced').value);
  return unitSheetsLayout(u=>{u.where=where;u.offset=0;});
 }catch(e){toast(errText(e));}
}
function unitSheetsInput(r,c,value){
 const u=USHEET,col=unitSheetsColumns()[c],id=u.data.table.rows[r].id,key=id+'\u0000'+col;
 u.inputs=u.inputs||new Map();const old=u.inputs.get(key);if(old)clearTimeout(old.timer);
 u.inputs.set(key,{id,column:col,value,timer:setTimeout(()=>unitSheetsCommit(key,u),350)});
}
function unitSheetsCommit(key,u){
 const cell=u.inputs&&u.inputs.get(key);
 if(!cell||USHEET!==u)return;
 clearTimeout(cell.timer);u.inputs.delete(key);
 if(cell.value!==unitSheetsValue(u.data.table.rows.find(row=>row.id===cell.id)?.[cell.column])){
  return unitSheetsRequest('operate',{ids:[cell.id],column:cell.column,operation:'set',value:cell.value},true);
 }
}
function unitSheetsCell(r,c,value){
 const u=USHEET,col=unitSheetsColumns()[c],id=u.data.table.rows[r].id,key=id+'\u0000'+col;
 if(u.inputs&&u.inputs.has(key))return unitSheetsCommit(key,u);
 if(value!==unitSheetsValue(u.data.table.rows[r][col])){
  return unitSheetsRequest('operate',{ids:[id],column:col,operation:'set',value},true);
 }
}

function unitSheetsCellKey(ev){
 const inp=ev.currentTarget,r=+inp.dataset.r,c=+inp.dataset.c;
 if(['ArrowDown','ArrowUp','ArrowLeft','ArrowRight'].includes(ev.key)||ev.key==='Enter'){
  const nr=r+(ev.key==='ArrowDown'||ev.key==='Enter'?1:ev.key==='ArrowUp'?-1:0),nc=c+(ev.key==='ArrowRight'?1:ev.key==='ArrowLeft'?-1:0);
  const next=modal.querySelector(`input[data-r="${nr}"][data-c="${nc}"]`);if(next){ev.preventDefault();next.focus();next.select();}
 }
}
async function unitSheetsPaste(ev){
 const text=ev.clipboardData.getData('text/plain');if(!text.includes('\t')&&!text.includes('\n'))return;
 ev.preventDefault();
 const u=USHEET,r=+ev.currentTarget.dataset.r,c=+ev.currentTarget.dataset.c;
 const cols=unitSheetsColumns(),rows=u.data.table.rows,cells=[];
 // Snapshot displayed IDs and names rather than retaining positional targets.
 const rect=u.rect,range=rect&&(rect.ids.length>1||rect.columns.length>1);
 const startRow=rect?rows.findIndex(row=>row.id===rect.ids[0]):r;
 const startColumn=rect?cols.indexOf(rect.columns[0]):c;
 if(startRow<0||startColumn<0)return;
 // A clicked cell is an insertion point; a larger rectangle bounds the paste.
 const ids=range?rect.ids:rows.slice(startRow).map(row=>row.id);
 const columns=range?rect.columns:cols.slice(startColumn);
 const visible=new Set(rows.map(row=>row.id));
 text.replace(/\r/g,'').replace(/\n$/,'').split('\n').forEach((line,dy)=>line.split('\t').forEach((value,dx)=>{
  const id=ids[dy],column=columns[dx];
  if(value===''&&!unitSheetsRuleKind()||!visible.has(id)||!cols.includes(column)||!unitSheetsEditable(column))return;
  cells.push({id,column,value});
 }));
 await u.layout;await unitSheetsFlush();
 if(USHEET!==u)return;
 // A filter may have completed while the clipboard event was being handled.
 const current=new Set(u.data.table.rows.map(row=>row.id)),shown=unitSheetsColumns();
 const targets=cells.filter(cell=>current.has(cell.id)&&shown.includes(cell.column)&&unitSheetsEditable(cell.column));
 if(targets.length)return unitSheetsRequest('paste',{cells:targets},true);
}
function unitSheetsKey(ev){if((ev.ctrlKey||ev.metaKey)&&['z','y'].includes(ev.key.toLowerCase())&&!ev.target.matches('textarea')){ev.preventDefault();ev.stopPropagation();unitSheetsUndo(ev.key.toLowerCase()==='y'||ev.shiftKey);}}
async function unitSheetsUndo(redo){
 const u=USHEET;
 await u.layout;await unitSheetsFlush();
 if(USHEET!==u||u.busy)return;
 const from=redo?u.future:u.past,to=redo?u.past:u.future;
 if(!from.length)return;
 const next=from[from.length-1],old=JSON.stringify(u.data.project);
 if(unitSheetsRuleKind()){
  // Undo can remove a column referenced by the current filter or sort.
  unitSheetsClearRect();
  u.where=null;u.filterRows=[];u.sort=[{column:'id',desc:false}];u.offset=0;
 }
 if(await unitSheetsRequest('save',{project:JSON.parse(next)})){
  from.pop();to.push(old);unitSheetsPaint();
 }
}

async function unitSheetsMass(){
 const u=USHEET;
 // Flushing a pending cell can repaint controls, so capture the user's mode now.
 const mode=document.getElementById('usMassMode')?.value||'selected';
 const edit={column:document.getElementById('usMassColumn').value,
  operation:document.getElementById('usMassOp').value,
  value:document.getElementById('usMassValue').value,other:document.getElementById('usMassOther').value};
 await u.layout;await unitSheetsFlush();
 if(USHEET!==u)return;
 unitSheetsPruneSelection();
 const ids=[...u.selected];
 if(mode==='selected'&&!ids.length){toast(tt('sheets.select_first'));return;}
 return unitSheetsPreview('operate',{ids,mode,...edit});
}
async function unitSheetsPreview(action,extra){
 const u=USHEET;
 const pending=(u.queue||Promise.resolve()).then(async()=>{
  if(USHEET!==u||u.busy)return false;
  u.busy=true;
  try{
   // Freeze concurrency tokens, filter and targets for the later confirmation.
   const body=structuredClone(unitSheetsBody(extra));
   const result=await unitSheetsPost('/api/unit_sheets/'+action,{...body,dry_run:true});
   if(USHEET!==u)return false;
   u.review={action,body,result};u.err='';unitSheetsPaint();return true;
  }catch(error){
   if(USHEET===u){u.review=null;u.err=errText(error);unitSheetsPaint();}
   return false;
  }finally{u.busy=false;}
 });
 u.queue=pending.catch(()=>false);return pending;
}
function unitSheetsReviewHtml(){
 const review=USHEET.review;
 if(!review)return '';
 const changes=review.result.changes||[],shown=changes.slice(0,100);
 return `<details open><summary>${tt('sheets.review_count',{count:review.result.target_count})}</summary>
 <div style="max-height:260px;overflow:auto"><table><thead><tr><th>${tt('sheets.review_target')}</th><th>${tt('sheets.review_field')}</th><th>${tt('sheets.review_before')}</th><th>${tt('sheets.review_after')}</th></tr></thead><tbody>
 ${shown.map(change=>`<tr><td>${esc(change.id)}</td><td>${esc(change.column)}</td><td>${esc(unitSheetsValue(change.before))}</td><td>${esc(unitSheetsValue(change.after))}</td></tr>`).join('')}
 </tbody></table></div>${changes.length>shown.length?`<div>${tt('sheets.review_more',{count:changes.length-shown.length})}</div>`:''}
 <button onclick="unitSheetsConfirmReview()">${tt('sheets.review_confirm')}</button><button onclick="unitSheetsCancelReview()">${tt('common.cancel')}</button></details>`;
}
function unitSheetsCancelReview(){
 // A preview never enters project history and needs no compensating save.
 USHEET.review=null;unitSheetsPaint();
}
function unitSheetsConfirmReview(){
 const u=USHEET,review=u.review;
 if(!review||u.busy)return false;
 u.review=null;
 return unitSheetsRequest(review.action,review.body,true);
}
async function unitSheetsFill(){
 const u=USHEET,col=document.getElementById('usMassColumn').value;
 await u.layout;
 if(USHEET!==u)return;
 unitSheetsPruneSelection();
 const cols=unitSheetsColumns(),visible=new Map(u.data.table.rows.map(row=>[row.id,row]));
 const rectangle=!!u.rect;
 const ids=rectangle?u.rect.ids.filter(id=>visible.has(id)):
  u.data.table.rows.filter(row=>u.selected.has(row.id)).map(row=>row.id);
 const columns=rectangle?u.rect.columns.filter(column=>cols.includes(column)&&unitSheetsEditable(column)):[col];
 if(!ids.length||!columns.length)return;
 // Capture the top displayed unit before flushing can change the sort order.
 const source=visible.get(ids[0]);
 await unitSheetsFlush();
 if(USHEET!==u)return;
 const fresh=u.data.table.rows.find(row=>row.id===source.id)||{...source,...u.data.project.draft[source.id]};
 const shown=new Set(u.data.table.rows.map(row=>row.id));
 const targets=ids.filter(id=>shown.has(id));
 if(!targets.length)return;
 if(rectangle){
  const cells=targets.flatMap(id=>columns.map(column=>({id,column,value:fresh[column]})));
  return unitSheetsPreview('paste',{cells,mode:'selected'});
 }
 return unitSheetsPreview('operate',{ids:targets,column:col,operation:'set',value:fresh[col]});
}
async function unitSheetsImport(input){const file=input.files[0];if(!file)return;if(file.size>20*1024*1024){toast(tt('sheets.file_large'));return;}try{const mapping=JSON.parse(document.getElementById('usMapping').value||'{}');await unitSheetsRequest('import',{kind:document.getElementById('usImportKind').value,text:await file.text(),mapping},true);}catch(e){toast(errText(e));}}
async function unitSheetsExport(kind){try{const r=await unitSheetsPost('/api/unit_sheets/export',unitSheetsBody({kind}));const content=r.encoding==='base64'?Uint8Array.from(atob(r.text),c=>c.charCodeAt(0)):r.text;const url=URL.createObjectURL(new Blob([content],{type:r.mime}));const a=document.createElement('a');a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(errText(e));}}
function unitSheetsSave(change){return unitSheetsRequest('save',()=>{const project=structuredClone(USHEET.data.project);change(project);return {project};},true);}
function unitSheetsSaveView(){const name=document.getElementById('usViewName').value.trim();if(!name)return;const view=structuredClone({view:USHEET.view,where:USHEET.where,sort:USHEET.sort,hidden:USHEET.hidden,order:USHEET.order,showExtras:USHEET.showExtras});unitSheetsSave(p=>{p.views[name]=view;});}
function unitSheetsLoadView(name){
 const v=USHEET.data.project.views[name];
 if(v)return unitSheetsLayout(u=>{Object.assign(u,structuredClone(v),{offset:0});});
}
function unitSheetsSetColumns(){
 const order=document.getElementById('usColumns').value.split(',').map(x=>x.trim()).filter(Boolean);
 return unitSheetsLayout(u=>{
  // Include previously hidden columns so applying the visible list keeps them hidden.
  const all=new Set([...u.hidden,...unitSheetsColumns(true)]);
  u.order=order;u.hidden=[...all].filter(c=>c!=='id'&&!order.includes(c));
 },false);
}
function unitSheetsExtras(show){
 return unitSheetsLayout(u=>{u.showExtras=show;},false);
}
function unitSheetsComparison(){const comparison={ultra_size:+document.getElementById('usUltra').value,defense_weight:+document.getElementById('usDefenseWeight').value};unitSheetsSave(p=>{p.comparison=comparison;});}
function unitSheetsSaveRecipe(){
 const name=document.getElementById('usRecipeName').value.trim();
 if(!name)return;
 const recipe={target:{view:USHEET.view},column:document.getElementById('usMassColumn').value,
  operation:document.getElementById('usMassOp').value,value:document.getElementById('usMassValue').value,
  other:document.getElementById('usMassOther').value};
 return unitSheetsSave(project=>{project.recipes[name]=recipe;});
}
function unitSheetsRecipeOptions(profile=false){
 const u=USHEET,recipes=u.data.project.recipes,invalid=u.data.invalid_recipes||{};
 const current=recipe=>recipe?.target?.view===u.view;
 const names=Object.keys(recipes).filter(name=>profile?!!recipes[name]?.target?.profile:!recipes[name]?.target?.profile);
 names.sort((a,b)=>Number(current(recipes[b]))-Number(current(recipes[a]))||a.localeCompare(b));
 return names.map(name=>{
  const label=invalid[name]?tt('sheets.recipe_invalid',{name,reason:invalid[name]}):name;
  const selected=u.controls[profile?'usProfileRecipe':'usRecipePicker']===name;
  return `<option value="${esc(name)}"${selected?' selected':''}${invalid[name]?' disabled':''}>${esc(label)}</option>`;
 }).join('');
}
function unitSheetsLoadRecipe(name){
 const u=USHEET,recipe=u.data.project.recipes[name];
 if(!recipe)return;
 if(u.data.invalid_recipes?.[name]){toast(u.data.invalid_recipes[name]);return;}
 u.recipeName=name;
 u.controls.usRecipePicker=name;
 for(const [key,id]of [['column','usMassColumn'],['operation','usMassOp'],['value','usMassValue'],['other','usMassOther']]){
  // Numeric zero is a saved value, not an empty input.
  u.controls[id]=recipe[key]??'';
  document.getElementById(id).value=u.controls[id];
 }
}
async function unitSheetsRunRecipe(name){
 const u=USHEET;
 const mode=document.getElementById('usMassMode')?.value||'selected';
 await u.layout;await unitSheetsFlush();
 if(USHEET!==u)return;
 const recipe=u.data.project.recipes[name];
 if(!recipe)return;
 if(u.data.invalid_recipes?.[name]){toast(u.data.invalid_recipes[name]);return;}
 const target=recipe.target||{};
 if(!target.profile&&target.view&&target.view!==u.view){toast(tt('sheets.invalid_recipe_target'));return;}
 unitSheetsPruneSelection();
 if(!target.profile&&mode==='selected'&&!u.selected.size){toast(tt('sheets.select_first'));return;}
 return unitSheetsPreview('operate',{recipe_name:name,ids:[...u.selected],mode});
}
function unitSheetsDiscard(){unitSheetsSave(p=>{p.draft={};p.draft_sources={};});}
function unitSheetsRename(index){const r=USHEET.data.refresh.rename_candidates[index];unitSheetsRequest('rename',{old:r.from,new:r.to},true);}
function unitSheetsRuleKind(){
 const view=USHEET.view;
 return view.startsWith('rules:')?view.slice(6):view==='rules'?'replenish':null;
}
function unitSheetsGridOpen(columns){
 if(!unitSheetsRuleKind())return '<table class="us-table">';
 return `<table class="us-table" style="table-layout:fixed;width:${36+columns.length*160}px"><colgroup><col style="width:36px">${columns.map(()=>'<col style="width:160px">').join('')}</colgroup>`;
}
function unitSheetsFrozenStyle(column,header=false){
 const frozen=USHEET.data.frozen_columns||[];
 const index=frozen.indexOf(column);
 if(index<0)return '';
 // Fixed widths keep several key columns frozen without overlapping cells.
 return `style="position:sticky;left:${36+index*160}px;min-width:160px;max-width:160px;background:var(--bg,#20232a);z-index:${header?4:2};${header?'top:0;':''}"`;
}
function unitSheetsRulesHtml(){
 const kind=unitSheetsRuleKind(),d=USHEET.data;
 const labels={replenish:tt('sheets.rule_replenish'),experience:tt('sheets.rule_experience'),pool:tt('sheets.rule_pool')};
 const options=d.columns.map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');
 const issues=d.rule_issues||[];
 return `${unitSheetsBalanceHtml()}<div class="count">${tt('sheets.rules_import_hint')}</div><div class="barrow">${['replenish','experience','pool'].map(k=>`<button onclick="unitSheetsTab('rules:${k}')">${labels[k]}</button>`).join('')}
 <button onclick="unitSheetsExport('${kind}')">${tt('sheets.export_table')}</button>
 <button onclick="unitSheetsRuleStructure('add_row')">${tt('sheets.rule_add_row')}</button>
 <button onclick="unitSheetsRuleStructure('remove_rows')">${tt('sheets.rule_remove_rows')}</button></div>
 <div class="barrow"><select id="usRuleColumn">${options}</select>
 <input id="usRuleColumnName" placeholder="${ttA('sheets.rule_column_name')}">
 <label><input id="usRuleKey" type="checkbox">${tt('sheets.rule_key_column')}</label>
 <button onclick="unitSheetsRuleStructure('add_column')">${tt('sheets.rule_add_column')}</button>
 <button onclick="unitSheetsRuleStructure('rename_column')">${tt('sheets.rule_rename_column')}</button>
 <button onclick="unitSheetsRuleStructure('remove_column')">${tt('sheets.rule_remove_column')}</button></div>
 ${issues.length?`<details open><summary>${tt('sheets.rule_issues',{count:issues.length})}</summary>${issues.map(issue=>`<div class="w-bad">${esc(issue.message)}</div>`).join('')}</details>`:''}`;
}
async function unitSheetsRuleStructure(operation){
 const u=USHEET,body={operation};
 if(operation==='remove_rows'||operation==='remove_column'||operation==='rename_column'){
  if(!confirm(tt('sheets.rule_structure_confirm')))return;
 }
 if(operation.includes('column')){
  const name=document.getElementById('usRuleColumnName').value.trim();
  body.column=operation==='add_column'?name:document.getElementById('usRuleColumn').value;
  if(operation==='rename_column')body.name=name;
  if(operation==='add_column')body.key=document.getElementById('usRuleKey').checked;
 }
 await u.layout;await unitSheetsFlush();
 if(USHEET!==u)return;
 unitSheetsPruneSelection();
 if(operation==='remove_rows'){
  body.ids=[...u.selected];
  if(!body.ids.length){toast(tt('sheets.select_first'));return;}
 }
 // Schema changes invalidate filter and sort names; flush in the old layout first.
 unitSheetsClearRect();
 u.where=null;u.filterRows=[];u.sort=[{column:'id',desc:false}];u.offset=0;
 return unitSheetsRequest('rule_structure',body,true);
}

function unitSheetsRect(ev,r,c){
 const u=USHEET,rows=u.data.table.rows,cols=unitSheetsColumns();
 let ar=r,ac=c;
 if(ev.shiftKey&&u.anchor){
  ev.preventDefault();
  ar=rows.findIndex(row=>row.id===u.anchor.id);ac=cols.indexOf(u.anchor.column);
  if(ar<0||ac<0){ar=r;ac=c;}
 }else{u.anchor={id:rows[r].id,column:cols[c]};}
 u.rect={ids:rows.slice(Math.min(r,ar),Math.max(r,ar)+1).map(row=>row.id),
  columns:cols.slice(Math.min(c,ac),Math.max(c,ac)+1)};
 unitSheetsRectPaint();
}
function unitSheetsRectPaint(){
 const u=USHEET,cols=unitSheetsColumns(),rows=u.data.table.rows;
 for(const cell of modal.querySelectorAll('td[data-r]')){
  const row=rows[+cell.dataset.r],column=cols[+cell.dataset.c];
  const selected=!!(u.rect&&row&&u.rect.ids.includes(row.id)&&u.rect.columns.includes(column));
  cell.classList.toggle('us-cell-selected',selected);
 }
}

function unitSheetsProfileRecipeOperations(column,selected=''){
 const profile=USHEET.data.balance_effective||USHEET.data.project.balance_profile||{};
 const labels={set:tt('sheets.recipe_op_set'),add:tt('sheets.recipe_op_add'),
  subtract:tt('sheets.recipe_op_subtract'),multiply:tt('sheets.recipe_op_multiply'),
  divide:tt('sheets.recipe_op_divide'),percent:tt('sheets.recipe_op_percent'),
  min:tt('sheets.recipe_op_min'),max:tt('sheets.recipe_op_max'),round:tt('sheets.recipe_op_round')};
 // Text and boolean profile keys only accept replacement values.
 const operations=typeof profile[column]==='number'?Object.keys(labels):['set'];
 return operations.map(operation=>`<option value="${operation}"${operation===selected?' selected':''}>${labels[operation]}</option>`).join('');
}
function unitSheetsProfileRecipeColumn(){
 const column=document.getElementById('usProfileRecipeColumn').value;
 const operation=document.getElementById('usProfileRecipeOp');
 operation.innerHTML=unitSheetsProfileRecipeOperations(column);
 operation.value='set';
 USHEET.controls.usProfileRecipeColumn=column;
 USHEET.controls.usProfileRecipeOp='set';
}
function unitSheetsSaveProfileRecipe(){
 const name=document.getElementById('usProfileRecipeName').value.trim();
 if(!name)return;
 // The server supplies defaults even before a profile has been saved.
 const profile=USHEET.data.balance_effective||USHEET.data.project.balance_profile||{};
 const recipe={target:{profile:profile.name||'default'},
  column:document.getElementById('usProfileRecipeColumn').value,
  operation:document.getElementById('usProfileRecipeOp').value,
  value:document.getElementById('usProfileRecipeValue').value};
 // Use the shared save queue so server validation and refusal reasons apply.
 return unitSheetsSave(project=>{project.recipes[name]=recipe;});
}
function unitSheetsBalanceHtml(){
 const p=USHEET.data.project,b=USHEET.balance;
 const profile=USHEET.data.balance_effective||p.balance_profile||{};
 const keys=Object.keys(profile).filter(key=>key!=='name'),controls=USHEET.controls;
 if(!keys.includes(controls.usProfileRecipeColumn)){
  controls.usProfileRecipeColumn=keys[0]??'';
  controls.usProfileRecipeOp='set';
 }
 // A numeric key can become text after loading another saved profile.
 if(typeof profile[controls.usProfileRecipeColumn]!=='number'){
  controls.usProfileRecipeOp='set';
 }
 return `<details id="usBalanceDetails"${controls.usBalanceDetails?' open':''} ontoggle="unitSheetsRememberControl(this)"><summary>${tt('sheets.balance')}</summary>
 <div class="barrow">${['replenish','experience','pool'].map(k=>`<label><input type="checkbox" class="us-stage" value="${k}"${USHEET.balanceStages.includes(k)?' checked':''} onchange="unitSheetsStages()"> ${k}</label>`).join('')}
 <button onclick="unitSheetsBalancePreview()">${tt('sheets.preview')}</button><button onclick="unitSheetsBalanceExport()">${tt('sheets.export_balance')}</button><label><input id="usIntermediate" type="checkbox">${tt('sheets.intermediate')}</label></div>
 <div class="barrow"><select id="usProfileRecipe" onchange="unitSheetsRememberControl(this)"><option value="">${tt('sheets.recipes')}</option>${unitSheetsRecipeOptions(true)}</select><button onclick="unitSheetsRunRecipe(document.getElementById('usProfileRecipe').value)">${tt('sheets.recipe_run')}</button></div>
 <div class="barrow"><input id="usProfileRecipeName" value="${esc(controls.usProfileRecipeName)}" oninput="unitSheetsRememberControl(this)" onchange="unitSheetsRememberControl(this)" placeholder="${ttA('sheets.recipe_name')}"><label>${tt('sheets.profile_recipe_key')} <select id="usProfileRecipeColumn" onchange="unitSheetsProfileRecipeColumn()">${keys.map(key=>`<option value="${esc(key)}"${key===controls.usProfileRecipeColumn?' selected':''}>${esc(key)}</option>`).join('')}</select></label>
 <label>${tt('sheets.recipe_operation')} <select id="usProfileRecipeOp" onchange="unitSheetsRememberControl(this)">${unitSheetsProfileRecipeOperations(controls.usProfileRecipeColumn,controls.usProfileRecipeOp)}</select></label><input id="usProfileRecipeValue" value="${esc(controls.usProfileRecipeValue)}" oninput="unitSheetsRememberControl(this)" onchange="unitSheetsRememberControl(this)" placeholder="${ttA('sheets.value')}"><button onclick="unitSheetsSaveProfileRecipe()">${tt('common.save')}</button></div>
 <label>${tt('sheets.profile')}<textarea id="usProfile" rows="4" style="width:100%">${esc(JSON.stringify(b?b.profile:profile,null,2))}</textarea></label>
 <details><summary>${tt('sheets.profile_rules')}</summary><div>${tt('sheets.settlement_exception')}</div><pre style="max-height:240px;overflow:auto">${esc(JSON.stringify(b?b.profile_rules:USHEET.data.balance_profile_rules||{},null,2))}</pre></details>
 <label>${tt('sheets.overrides')}<textarea id="usOverrides" rows="3" style="width:100%">${esc(JSON.stringify(p.balance_overrides||[],null,2))}</textarea></label><button onclick="unitSheetsBalanceProfile()">${tt('common.save')}</button>
 ${b?`<button onclick="unitSheetsBalanceApply()"${b.changed_fields?'':' disabled'}>${tt('sheets.apply_balance')}</button><div>${tt('sheets.balance_count',{rows:b.recruitment_rows,changes:b.changed_fields})}</div><pre style="max-height:160px;overflow:auto">${esc(JSON.stringify(Object.fromEntries(Object.entries(b.logs).map(([k,v])=>[k,v.counts])),null,2))}</pre>
 <details><summary>${tt('sheets.balance_details')}</summary><div>${tt('sheets.preview_log_limit')}</div><pre style="max-height:320px;overflow:auto">${esc(JSON.stringify(b.logs,null,2))}</pre></details>
 <details><summary>${tt('sheets.structure')}</summary><pre style="max-height:240px;overflow:auto">${esc(JSON.stringify(b.structure,null,2))}</pre></details>`:''}</details>`;
}
function unitSheetsStages(){USHEET.balanceStages=[...modal.querySelectorAll('.us-stage:checked')].map(x=>x.value);return USHEET.balanceStages;}
async function unitSheetsBalancePreview(){const u=USHEET;if(u.busy)return;u.busy=true;try{u.balance=await unitSheetsPost('/api/unit_sheets/balance_preview',unitSheetsBody({stages:unitSheetsStages()}));unitSheetsPaint();}catch(e){toast(errText(e));}finally{u.busy=false;}}
async function unitSheetsBalanceExport(){try{const r=await unitSheetsPost('/api/unit_sheets/balance_export',unitSheetsBody({stages:unitSheetsStages(),intermediate:document.getElementById('usIntermediate').checked}));const url=URL.createObjectURL(new Blob([Uint8Array.from(atob(r.text),c=>c.charCodeAt(0))],{type:r.mime}));const a=document.createElement('a');a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(errText(e));}}
function unitSheetsBalanceProfile(){try{const profile=JSON.parse(document.getElementById('usProfile').value||'{}'),overrides=JSON.parse(document.getElementById('usOverrides').value||'[]');USHEET.balance=null;unitSheetsSave(p=>{p.balance_profile=profile;p.balance_overrides=overrides;});}catch(e){toast(errText(e));}}

async function unitSheetsBalanceApply(){const u=USHEET,b=u.balance;if(!b||u.busy||!confirm(tt('sheets.apply_balance_confirm',{count:b.changed_fields})))return;u.busy=true;try{await unitSheetsPost('/api/unit_sheets/balance_apply',unitSheetsBody({stages:b.stages,plan_token:b.plan_token}));u.balance=null;toast(tt('sheets.applied'));}catch(e){toast(errText(e));}finally{u.busy=false;unitSheetsPaint();}}

async function unitSheetsFlush(){const u=USHEET;if(u.inputs)for(const key of [...u.inputs.keys()])unitSheetsCommit(key,u);if(u.queue)await u.queue;}
async function unitSheetsNativePreview(){const u=USHEET;await unitSheetsFlush();if(u.busy)return;u.busy=true;try{u.native=await unitSheetsPost('/api/unit_sheets/native_preview',unitSheetsBody());unitSheetsPaint();}catch(e){toast(errText(e));}finally{u.busy=false;}}
async function unitSheetsNativeApply(){const u=USHEET,n=u.native;if(!n||u.busy||!confirm(tt('sheets.native_confirm',{count:n.units})))return;u.busy=true;try{const applied=await unitSheetsPost('/api/unit_sheets/native_apply',unitSheetsBody({plan_token:n.plan_token}));if(applied.warning)toast(applied.warning);u.native=null;u.past=[];u.future=[];toast(tt('sheets.native_done'));}catch(e){toast(errText(e));}finally{u.busy=false;}await unitSheetsRequest('load');}

function unitSheetsColumnKind(column){
 // The API supplies kinds even for read-only recruitment context columns.
 const declared=USHEET.data.filter_info?.[column]?.kind;
 if(declared)return declared;
 if(USHEET_META.includes(column)||column==='groups'||column==='id'||column.startsWith('extra:'))return 'annotation';
 if(unitSheetsRuleKind())return 'annotation';
 return USHEET.data.field_info[column]?'native':'derived';
}
function unitSheetsGroupPick(name){
 return unitSheetsLayout(u=>{u.compareGroup=name;});
}
async function unitSheetsGroupAction(operation){
 const u=USHEET;
 const input=document.getElementById('usGroupName');
 const typed=input?input.value.trim():'';
 const name=operation==='create'?typed:u.compareGroup;
 if(!name)return;
 await u.layout;
 await unitSheetsFlush();
 if(USHEET!==u)return;
 return unitSheetsRequest('group',()=>{
  // Resolve selected IDs after queued queries have pruned newly hidden rows.
  unitSheetsPruneSelection();
  const body={operation,name};
  if(operation==='add'||operation==='remove'){
   if(u.view==='recruitment'||unitSheetsRuleKind())throw new Error(tt('sheets.group_units_only'));
   body.ids=[...u.selected];
   if(!body.ids.length)throw new Error(tt('sheets.select_first'));
  }
  if(operation==='rename')body.new_name=typed;
  u.compareGroup=operation==='delete'?'':operation==='rename'?typed:name;
  return body;
 },true);
}
function unitSheetsGroupsHtml(){
 const u=USHEET,d=u.data;
 const names=Object.keys(d.project.groups||{});
 const unitView=u.view!=='recruitment'&&!unitSheetsRuleKind();
 const disabled=unitView?'':' disabled';
 let html=`<details${u.compareGroup?' open':''}><summary>${tt('sheets.groups')}</summary>
 <div class="barrow"><select id="usGroupPick" onchange="unitSheetsGroupPick(this.value)"><option value="">${tt('sheets.group_pick')}</option>${names.map(name=>`<option value="${esc(name)}"${name===u.compareGroup?' selected':''}>${esc(name)}</option>`).join('')}</select>
 <input id="usGroupName" placeholder="${ttA('sheets.group_name')}">
 ${['create','rename','delete','add','remove'].map(operation=>`<button onclick="unitSheetsGroupAction('${operation}')"${['add','remove'].includes(operation)?disabled:''}>${unitSheetsGroupLabel(operation)}</button>`).join('')}</div>
 <div class="count">${tt('sheets.group_note')}</div>`;
 const comparison=d.comparison_group;
 if(comparison){
  // Transpose the Base columns so unit values can be read side by side.
  html+=`<div class="us-comparison"><table class="us-table us-compare-table"><thead><tr><th>${esc(comparison.name)}</th>
   ${['min','max','average'].map(key=>`<th>${unitSheetsGroupLabel(key)}</th>`).join('')}
   ${comparison.members.map(member=>`<th>${esc(member.id)}${member.missing?` <span>${tt('sheets.group_missing')}</span>`:''}</th>`).join('')}</tr></thead><tbody>`;
  html+=comparison.columns.map(column=>{
   const stats=comparison.statistics[column];
   const kind=comparison.column_kinds?.[column]||unitSheetsColumnKind(column);
   return `<tr><th class="us-kind-${kind}">${esc(unitSheetsColumnLabel(column))}</th>
    ${['min','max','average'].map(key=>`<td>${esc(unitSheetsValue(stats?.[key]))}</td>`).join('')}
    ${comparison.members.map(member=>`<td class="us-kind-${kind}">${esc(unitSheetsValue(member[column]))}${stats?`<small>${tt('sheets.group_difference',{value:esc(unitSheetsValue(member.difference[column]))})}</small>`:''}</td>`).join('')}</tr>`;
  }).join('');
  html+='</tbody></table></div>';
 }
 return html+'</details>';
}

function unitSheetsKindLabel(kind){
 const labels={native:tt('sheets.kind_native'),annotation:tt('sheets.kind_annotation'),
  derived:tt('sheets.kind_derived')};
 return labels[kind]||kind;
}
function unitSheetsGroupLabel(key){
 const labels={create:tt('sheets.group_create'),rename:tt('sheets.group_rename'),
  delete:tt('sheets.group_delete'),add:tt('sheets.group_add'),remove:tt('sheets.group_remove'),
  min:tt('sheets.group_min'),max:tt('sheets.group_max'),average:tt('sheets.group_average')};
 return labels[key]||key;
}
