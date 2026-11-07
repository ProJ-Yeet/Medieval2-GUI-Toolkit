/* Native editable unit sheets. Project config is saved; game edits stay staged. */
let USHEET=null;
const USHEET_CATEGORY=Object.keys({'Category':0})[0];
const USHEET_META=Object.keys({'Unit Race':0,'Tier':0,'Main Faction':0,'AOR':0,'Category override':0});
async function unitSheetsOpen(){
 const mod=state.src || state.dst;
 if(!mod){toast(tt('sheets.pick_mod'));return;}
 USHEET={mod,view:'classification',offset:0,where:null,sort:[{column:'id',desc:false}],selected:new Set(),past:[],future:[],busy:false,hidden:[],order:[],filterRows:[],group:'all',balanceStages:['replenish','experience','pool']};
 modal.className='modal wide';modal.innerHTML=`<div class="count">${tt('sheets.loading')}</div>`;overlay.classList.add('open');
 await unitSheetsRequest('load');
}
function unitSheetsBody(extra={}){
 const u=USHEET;return Object.assign({mod:u.mod,revision:u.data&&u.data.revision,source_token:u.data&&u.data.source_token,
  view:u.view,where:u.where,sort:u.sort,offset:u.offset,limit:75},extra);
}
async function unitSheetsRequest(action,extra={},history=false){
 const u=USHEET;if(!u)return false;
 const pending=(u.queue||Promise.resolve()).then(()=>USHEET===u?unitSheetsRequestNow(action,extra,history):false);
 u.queue=pending.catch(()=>false);return pending;
}
async function unitSheetsRequestNow(action,extra={},history=false){
 const u=USHEET;if(!u || u.busy)return false;u.busy=true;
 const prior=u.data?JSON.stringify(u.data.project):null;
 try{
  if(typeof extra==='function')extra=extra();
  const r=await api.post('/api/unit_sheets/'+action,unitSheetsBody(extra));
  if(USHEET!==u)return false;
  if(history&&prior&&JSON.stringify(r.project)!==prior){u.past.push(prior);if(u.past.length>20)u.past.shift();u.future=[];}
  if(history){u.native=null;u.balance=null;}u.data=r;u.err='';unitSheetsPaint();return true;
 }catch(err){if(USHEET===u){u.err=errText(err);unitSheetsPaint();}return false;}
 finally{u.busy=false;}
}
function unitSheetsColumns(){
 const u=USHEET,d=u.data;let cols;
 if(u.view==='recruitment')cols=['id','unit','building','level','settlement','section','initial','per_turn','maximum','experience','requires',...USHEET_META,USHEET_CATEGORY];
 else if(u.view==='classification')cols=['id',...USHEET_META,USHEET_CATEGORY,'needs_classification'];
 else cols=['id',...Object.keys(d.field_info).filter(k=>d.field_info[k].view===u.view),
   ...(u.view==='base'?['defense_total','ultra_size','cost_efficiency','upkeep_efficiency']:[])];
 if(u.showExtras)cols.push(...d.extra_columns);
 if(u.order.length)cols.sort((a,b)=>(u.order.includes(a)?u.order.indexOf(a):999)-(u.order.includes(b)?u.order.indexOf(b):999));
 return ['id',...cols.filter(k=>k!=='id'&&!u.hidden.includes(k))];
}
function unitSheetsValue(v){return Array.isArray(v)?v.join(', '):v==null?'':String(v);}
function unitSheetsEditable(col){return USHEET.view!=='recruitment'&&(USHEET_META.includes(col)||!!USHEET.data.field_info[col]);}
function unitSheetsPaint(){
 const u=USHEET;if(!u || !u.data){if(u&&u.err)modal.innerHTML=`<div class="w-bad">${esc(u.err)}</div>`;return;}
 const d=u.data,cols=unitSheetsColumns(),table=d.table;
 const tabs=[['classification',tt('sheets.classification')],['base',tt('sheets.base')],['attributes',tt('sheets.attributes')],['soft',tt('sheets.soft')],['rules',tt('sheets.rules')],['recruitment',tt('sheets.recruitment')]];
 const option=col=>`<option value="${esc(col)}">${esc(col)}</option>`;
 const filterCols=['id',...USHEET_META,...d.columns,USHEET_CATEGORY,'ownership','model','mount','projectile','changed','needs_classification',...(u.view==='recruitment'?['unit','building','level','settlement','section','initial','per_turn','maximum','experience','requires']:[]),...d.extra_columns];
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
 ${u.view==='rules'?unitSheetsRulesHtml():`
 <details${u.filterRows.length?' open':''}><summary>${tt('sheets.filters')}</summary>
 <div id="usFilters">${u.filterRows.map((f,i)=>`<div class="barrow"><select onchange="USHEET.filterRows[${i}].column=this.value">${filterCols.map(k=>`<option${f.column===k?' selected':''}>${esc(k)}</option>`).join('')}</select>
 <select onchange="USHEET.filterRows[${i}].op=this.value">${['eq','ne','contains','not_contains','gt','ge','lt','le','blank','missing','invalid'].map(k=>`<option${f.op===k?' selected':''}>${k}</option>`).join('')}</select><input value="${esc(f.value||'')}" oninput="USHEET.filterRows[${i}].value=this.value"><button onclick="USHEET.filterRows.splice(${i},1);unitSheetsPaint()">×</button></div>`).join('')}</div>
 <div class="barrow"><button onclick="USHEET.filterRows.push({column:'id',op:'contains',value:''});unitSheetsPaint()">${tt('sheets.add_filter')}</button><select onchange="USHEET.group=this.value"><option value="all"${u.group==='all'?' selected':''}>${tt('sheets.and')}</option><option value="any"${u.group==='any'?' selected':''}>${tt('sheets.or')}</option></select>
 <button onclick="unitSheetsFilter()">${tt('sheets.filter_apply')}</button>${u.view==='recruitment'?'':`<button onclick="unitSheetsMissing()">${tt('sheets.missing_only')}</button>`}<button onclick="USHEET.where=null;USHEET.filterRows=[];USHEET.offset=0;unitSheetsRequest('query')">${tt('sheets.clear_filters')}</button></div>
 <label>${tt('sheets.advanced_filter')}<textarea id="usAdvanced" rows="3" style="width:100%">${esc(JSON.stringify(u.where||{}))}</textarea></label><button onclick="unitSheetsAdvanced()">${tt('sheets.filter_apply')}</button></details>
 <details><summary>${tt('sheets.columns_views')}</summary><div class="barrow"><input id="usViewName" placeholder="${ttA('sheets.view_name')}"><button onclick="unitSheetsSaveView()">${tt('sheets.save_view')}</button><select onchange="unitSheetsLoadView(this.value)"><option value="">${tt('sheets.saved_views')}</option>${Object.keys(d.project.views).map(option).join('')}</select></div>
 <label><input type="checkbox"${u.showExtras?' checked':''} onchange="USHEET.showExtras=this.checked;unitSheetsPaint()">${tt('sheets.show_extras')}</label><label>${tt('sheets.visible_columns')}<textarea id="usColumns" rows="2" style="width:100%">${esc(cols.join(', '))}</textarea></label><button onclick="unitSheetsSetColumns()">${tt('sheets.columns_apply')}</button>
 <label>${tt('sheets.comparison')}<input id="usUltra" type="number" step="any" value="${d.project.comparison.ultra_size}"><input id="usDefenseWeight" type="number" step="any" value="${d.project.comparison.defense_weight}"><button onclick="unitSheetsComparison()">${tt('common.save')}</button></label></details>
 <div class="barrow"><span>${tt('sheets.rows_count',{matches:table.total,selected:u.selected.size})}</span><button onclick="unitSheetsSelectMatches()">${tt('sheets.select_matches')}</button><button onclick="USHEET.selected.clear();unitSheetsPaint()">${tt('sheets.select_none')}</button>
 <button onclick="unitSheetsPage(-1)"${u.offset?'':' disabled'}>◀</button><span>${u.offset+1}–${Math.min(u.offset+75,table.total)}</span><button onclick="unitSheetsPage(1)"${u.offset+75<table.total?'':' disabled'}>▶</button></div>
 <div class="us-grid" style="max-height:55vh;overflow:auto"><table class="us-table"><thead><tr><th>✓</th>${cols.map((k,c)=>`<th data-sort="${esc(k)}" onclick="unitSheetsSort(this.dataset.sort,event.shiftKey)" title="${ttA('sheets.sort_hint')}">${esc(k)}</th>`).join('')}</tr></thead><tbody>
 ${table.rows.map((row,r)=>`<tr class="${row.changed?'us-changed':''}"><td><input type="checkbox"${u.selected.has(row.id)?' checked':''} onchange="unitSheetsSelect(${r},this.checked)"></td>${cols.map((col,c)=>`<td data-r="${r}" data-c="${c}" onmousedown="unitSheetsRect(event,${r},${c})">${unitSheetsEditable(col)?`<input data-r="${r}" data-c="${c}" data-col="${esc(col)}" value="${esc(unitSheetsValue(row[col]))}" oninput="unitSheetsInput(${r},${c},this.value)" onchange="unitSheetsCell(${r},${c},this.value)" onkeydown="unitSheetsCellKey(event)" onpaste="unitSheetsPaste(event)">`:`<span>${esc(unitSheetsValue(row[col]))}</span>`}</td>`).join('')}</tr>`).join('')}
 </tbody></table></div>
 <details${u.view==='recruitment'?' hidden':''}><summary>${tt('sheets.mass_edit')}</summary><div class="barrow"><select id="usMassColumn">${[...USHEET_META,...d.columns].map(option).join('')}</select><select id="usMassOp">${['set','clear','add','subtract','multiply','divide','percent','min','max','round','copy','expression','replace','append','remove','deduplicate'].map(k=>`<option>${k}</option>`).join('')}</select>
 <input id="usMassValue" placeholder="${ttA('sheets.value')}"><input id="usMassOther" placeholder="${ttA('sheets.replacement')}"><button onclick="unitSheetsMass()">${tt('sheets.stage_selected')}</button><button onclick="unitSheetsFill()">${tt('sheets.fill_down')}</button></div>
 <div class="barrow"><input id="usRecipeName" placeholder="${ttA('sheets.recipe_name')}"><button onclick="unitSheetsSaveRecipe()">${tt('common.save')}</button><select onchange="unitSheetsLoadRecipe(this.value)"><option value="">${tt('sheets.recipes')}</option>${Object.keys(d.project.recipes).map(option).join('')}</select></div></details>`}
 ${d.changes?`<details open><summary>${tt('sheets.change_preview')}</summary><pre style="max-height:180px;overflow:auto">${esc(JSON.stringify(d.changes,null,2))}</pre></details>`:''}
 ${u.native?`<details open><summary>${tt('sheets.native_review',{count:u.native.units})}</summary><pre style="max-height:240px;overflow:auto">${esc(u.native.files.map(f=>f.diff).join('\n\n'))}</pre><button onclick="unitSheetsNativeApply()">${tt('sheets.native_apply')}</button></details>`:''}
 <div class="foot"><button onclick="unitSheetsNativePreview()">${tt('sheets.native_preview')}</button><button onclick="unitSheetsDiscard()">${tt('sheets.discard_native')}</button><button onclick="closeModal()">${tt('common.close')}</button></div></div>`;
}
function unitSheetsTab(view){USHEET.view=view;USHEET.offset=0;USHEET.hidden=[];USHEET.order=[];USHEET.where=null;USHEET.filterRows=[];USHEET.selected.clear();USHEET.sort=[{column:'id',desc:false}];unitSheetsRequest('query');}
function unitSheetsSelect(index,on){const id=USHEET.data.table.rows[index].id;on?USHEET.selected.add(id):USHEET.selected.delete(id);unitSheetsPaint();}
function unitSheetsSelectMatches(){USHEET.data.table.matched_ids.forEach(id=>USHEET.selected.add(id));unitSheetsPaint();}
function unitSheetsPage(dir){USHEET.offset=Math.max(0,USHEET.offset+dir*75);unitSheetsRequest('query');}
function unitSheetsSort(column,add){const u=USHEET,old=u.sort.find(s=>s.column===column);u.sort=add?u.sort.filter(s=>s.column!==column):[];u.sort.push({column,desc:old?!old.desc:false});unitSheetsRequest('query');}
function unitSheetsFilter(){USHEET.where={[USHEET.group]:USHEET.filterRows};USHEET.offset=0;unitSheetsRequest('query');}
function unitSheetsMissing(){if(USHEET.view==='recruitment')return;USHEET.where={column:'needs_classification',op:'eq',value:true};USHEET.offset=0;unitSheetsRequest('query');}
function unitSheetsAdvanced(){try{USHEET.where=JSON.parse(document.getElementById('usAdvanced').value);USHEET.offset=0;unitSheetsRequest('query');}catch(e){toast(errText(e));}}
function unitSheetsInput(r,c,value){
 const u=USHEET,col=unitSheetsColumns()[c],id=u.data.table.rows[r].id,key=id+'\u0000'+col;
 u.inputs=u.inputs||new Map();const old=u.inputs.get(key);if(old)clearTimeout(old.timer);
 u.inputs.set(key,{id,column:col,value,timer:setTimeout(()=>unitSheetsCommit(key,u),350)});
}
function unitSheetsCommit(key,u){const cell=u.inputs&&u.inputs.get(key);if(!cell||USHEET!==u)return;clearTimeout(cell.timer);u.inputs.delete(key);if(cell.value!=='')unitSheetsRequest('operate',{ids:[cell.id],column:cell.column,operation:'set',value:cell.value},true);}
function unitSheetsCell(r,c,value){const u=USHEET,col=unitSheetsColumns()[c],id=u.data.table.rows[r].id,key=id+'\u0000'+col;if(u.inputs&&u.inputs.has(key))unitSheetsCommit(key,u);else if(value!==unitSheetsValue(u.data.table.rows[r][col])&&value!=='')unitSheetsRequest('operate',{ids:[id],column:col,operation:'set',value},true);}

function unitSheetsCellKey(ev){
 const inp=ev.currentTarget,r=+inp.dataset.r,c=+inp.dataset.c;
 if(['ArrowDown','ArrowUp','ArrowLeft','ArrowRight'].includes(ev.key)||ev.key==='Enter'){
  const nr=r+(ev.key==='ArrowDown'||ev.key==='Enter'?1:ev.key==='ArrowUp'?-1:0),nc=c+(ev.key==='ArrowRight'?1:ev.key==='ArrowLeft'?-1:0);
  const next=modal.querySelector(`input[data-r="${nr}"][data-c="${nc}"]`);if(next){ev.preventDefault();next.focus();next.select();}
 }
}
function unitSheetsPaste(ev){
 const text=ev.clipboardData.getData('text/plain');if(!text.includes('\t')&&!text.includes('\n'))return;
 ev.preventDefault();const r=+ev.currentTarget.dataset.r,c=+ev.currentTarget.dataset.c,cols=unitSheetsColumns(),rows=USHEET.data.table.rows,cells=[];
 text.replace(/\r/g,'').replace(/\n$/,'').split('\n').forEach((line,dy)=>line.split('\t').forEach((value,dx)=>{
  if(value===''||!rows[r+dy]||!unitSheetsEditable(cols[c+dx]))return;
  cells.push({id:rows[r+dy].id,column:cols[c+dx],value});
 }));
 if(cells.length)unitSheetsRequest('paste',{cells},true);
}
function unitSheetsKey(ev){if((ev.ctrlKey||ev.metaKey)&&['z','y'].includes(ev.key.toLowerCase())&&!ev.target.matches('textarea')){ev.preventDefault();ev.stopPropagation();unitSheetsUndo(ev.key.toLowerCase()==='y'||ev.shiftKey);}}
async function unitSheetsUndo(redo){const u=USHEET,from=redo?u.future:u.past,to=redo?u.past:u.future;if(!from.length||u.busy)return;const next=from[from.length-1],old=JSON.stringify(u.data.project);if(await unitSheetsRequest('save',{project:JSON.parse(next)})){from.pop();to.push(old);unitSheetsPaint();}}
function unitSheetsMass(){const ids=[...USHEET.selected];if(!ids.length){toast(tt('sheets.select_first'));return;}unitSheetsRequest('operate',{ids,column:document.getElementById('usMassColumn').value,operation:document.getElementById('usMassOp').value,value:document.getElementById('usMassValue').value,other:document.getElementById('usMassOther').value},true);}
function unitSheetsFill(){const u=USHEET,col=document.getElementById('usMassColumn').value,rows=u.data.table.rows.filter(r=>u.selected.has(r.id));if(!rows.length)return;unitSheetsRequest('operate',{ids:[...u.selected],column:col,operation:'set',value:rows[0][col]},true);}
async function unitSheetsImport(input){const file=input.files[0];if(!file)return;if(file.size>20*1024*1024){toast(tt('sheets.file_large'));return;}try{const mapping=JSON.parse(document.getElementById('usMapping').value||'{}');await unitSheetsRequest('import',{kind:document.getElementById('usImportKind').value,text:await file.text(),mapping},true);}catch(e){toast(errText(e));}}
async function unitSheetsExport(kind){try{const r=await api.post('/api/unit_sheets/export',unitSheetsBody({kind}));const content=r.encoding==='base64'?Uint8Array.from(atob(r.text),c=>c.charCodeAt(0)):r.text;const url=URL.createObjectURL(new Blob([content],{type:r.mime}));const a=document.createElement('a');a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(errText(e));}}
function unitSheetsSave(change){return unitSheetsRequest('save',()=>{const project=structuredClone(USHEET.data.project);change(project);return {project};},true);}
function unitSheetsSaveView(){const name=document.getElementById('usViewName').value.trim();if(!name)return;const view=structuredClone({view:USHEET.view,where:USHEET.where,sort:USHEET.sort,hidden:USHEET.hidden,order:USHEET.order,showExtras:USHEET.showExtras});unitSheetsSave(p=>{p.views[name]=view;});}
function unitSheetsLoadView(name){const v=USHEET.data.project.views[name];if(v){Object.assign(USHEET,v,{offset:0});unitSheetsRequest('query');}}
function unitSheetsSetColumns(){const order=document.getElementById('usColumns').value.split(',').map(x=>x.trim()).filter(Boolean);const all=unitSheetsColumns();USHEET.order=order;USHEET.hidden=all.filter(c=>!order.includes(c));unitSheetsPaint();}
function unitSheetsComparison(){const comparison={ultra_size:+document.getElementById('usUltra').value,defense_weight:+document.getElementById('usDefenseWeight').value};unitSheetsSave(p=>{p.comparison=comparison;});}
function unitSheetsSaveRecipe(){const name=document.getElementById('usRecipeName').value.trim();if(!name)return;const recipe={column:document.getElementById('usMassColumn').value,operation:document.getElementById('usMassOp').value,value:document.getElementById('usMassValue').value,other:document.getElementById('usMassOther').value};unitSheetsSave(p=>{p.recipes[name]=recipe;});}
function unitSheetsLoadRecipe(name){const r=USHEET.data.project.recipes[name];if(r)for(const [k,id]of [['column','usMassColumn'],['operation','usMassOp'],['value','usMassValue'],['other','usMassOther']])document.getElementById(id).value=r[k]||'';}
function unitSheetsDiscard(){unitSheetsSave(p=>{p.draft={};p.draft_sources={};});}
function unitSheetsRename(index){const r=USHEET.data.refresh.rename_candidates[index];unitSheetsRequest('rename',{old:r.from,new:r.to},true);}
function unitSheetsRulesHtml(){
 const kind=USHEET.ruleKind||'replenish',rows=USHEET.data.project.rules[kind]||[],keys=[...new Set(rows.flatMap(Object.keys))];
 return `${unitSheetsBalanceHtml()}<div class="barrow">${['replenish','experience','pool'].map(k=>`<button onclick="USHEET.ruleKind='${k}';unitSheetsPaint()">${k}</button>`).join('')}<button onclick="unitSheetsExport('${kind}')">${tt('sheets.export_table')}</button></div>
 <div class="us-grid" style="max-height:55vh;overflow:auto"><table class="us-table"><thead><tr>${keys.map(k=>`<th>${esc(k)}</th>`).join('')}</tr></thead><tbody>${rows.map((row,r)=>`<tr>${keys.map((key,c)=>`<td><input value="${esc(row[key]??'')}" onchange="unitSheetsRuleCell('${kind}',${r},${c},this.value)"></td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="count">${tt('sheets.rules_import_hint')}</div>`;
}
function unitSheetsRuleCell(kind,r,c,value){const keys=[...new Set(USHEET.data.project.rules[kind].flatMap(Object.keys))],key=keys[c];unitSheetsSave(p=>{p.rules[kind][r][key]=value;});}

function unitSheetsRect(ev,r,c){
 const u=USHEET;if(ev.shiftKey&&u.anchor){ev.preventDefault();u.rect={r0:Math.min(r,u.anchor.r),r1:Math.max(r,u.anchor.r),c0:Math.min(c,u.anchor.c),c1:Math.max(c,u.anchor.c)};}
 else {u.anchor={r,c};u.rect={r0:r,r1:r,c0:c,c1:c};}
 for(const cell of modal.querySelectorAll('td[data-r]')){const y=+cell.dataset.r,x=+cell.dataset.c;cell.classList.toggle('us-cell-selected',y>=u.rect.r0&&y<=u.rect.r1&&x>=u.rect.c0&&x<=u.rect.c1);}
}

function unitSheetsBalanceHtml(){
 const p=USHEET.data.project,b=USHEET.balance;
 return `<details open><summary>${tt('sheets.balance')}</summary>
 <div class="barrow">${['replenish','experience','pool'].map(k=>`<label><input type="checkbox" class="us-stage" value="${k}"${USHEET.balanceStages.includes(k)?' checked':''} onchange="unitSheetsStages()"> ${k}</label>`).join('')}
 <button onclick="unitSheetsBalancePreview()">${tt('sheets.preview')}</button><button onclick="unitSheetsBalanceExport()">${tt('sheets.export_balance')}</button><label><input id="usIntermediate" type="checkbox">${tt('sheets.intermediate')}</label></div>
 <label>${tt('sheets.profile')}<textarea id="usProfile" rows="4" style="width:100%">${esc(JSON.stringify(b?b.profile:p.balance_profile||{},null,2))}</textarea></label>
 <label>${tt('sheets.overrides')}<textarea id="usOverrides" rows="3" style="width:100%">${esc(JSON.stringify(p.balance_overrides||[],null,2))}</textarea></label><button onclick="unitSheetsBalanceProfile()">${tt('common.save')}</button>
 ${b?`<button onclick="unitSheetsBalanceApply()"${b.changed_fields?'':' disabled'}>${tt('sheets.apply_balance')}</button><div>${tt('sheets.balance_count',{rows:b.recruitment_rows,changes:b.changed_fields})}</div><pre style="max-height:160px;overflow:auto">${esc(JSON.stringify(Object.fromEntries(Object.entries(b.logs).map(([k,v])=>[k,v.counts])),null,2))}</pre>
 <details><summary>${tt('sheets.balance_details')}</summary><div>${tt('sheets.preview_log_limit')}</div><pre style="max-height:320px;overflow:auto">${esc(JSON.stringify(b.logs,null,2))}</pre></details>
 <details><summary>${tt('sheets.structure')}</summary><pre style="max-height:240px;overflow:auto">${esc(JSON.stringify(b.structure,null,2))}</pre></details>`:''}</details>`;
}
function unitSheetsStages(){USHEET.balanceStages=[...modal.querySelectorAll('.us-stage:checked')].map(x=>x.value);return USHEET.balanceStages;}
async function unitSheetsBalancePreview(){const u=USHEET;if(u.busy)return;u.busy=true;try{u.balance=await api.post('/api/unit_sheets/balance_preview',unitSheetsBody({stages:unitSheetsStages()}));unitSheetsPaint();}catch(e){toast(errText(e));}finally{u.busy=false;}}
async function unitSheetsBalanceExport(){try{const r=await api.post('/api/unit_sheets/balance_export',unitSheetsBody({stages:unitSheetsStages(),intermediate:document.getElementById('usIntermediate').checked}));const url=URL.createObjectURL(new Blob([Uint8Array.from(atob(r.text),c=>c.charCodeAt(0))],{type:r.mime}));const a=document.createElement('a');a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(errText(e));}}
function unitSheetsBalanceProfile(){try{const profile=JSON.parse(document.getElementById('usProfile').value||'{}'),overrides=JSON.parse(document.getElementById('usOverrides').value||'[]');USHEET.balance=null;unitSheetsSave(p=>{p.balance_profile=profile;p.balance_overrides=overrides;});}catch(e){toast(errText(e));}}

async function unitSheetsBalanceApply(){const u=USHEET,b=u.balance;if(!b||u.busy||!confirm(tt('sheets.apply_balance_confirm',{count:b.changed_fields})))return;u.busy=true;try{await api.post('/api/unit_sheets/balance_apply',unitSheetsBody({stages:b.stages,plan_token:b.plan_token}));u.balance=null;toast(tt('sheets.applied'));}catch(e){toast(errText(e));}finally{u.busy=false;unitSheetsPaint();}}

async function unitSheetsFlush(){const u=USHEET;if(u.inputs)for(const key of [...u.inputs.keys()])unitSheetsCommit(key,u);if(u.queue)await u.queue;}
async function unitSheetsNativePreview(){const u=USHEET;await unitSheetsFlush();if(u.busy)return;u.busy=true;try{u.native=await api.post('/api/unit_sheets/native_preview',unitSheetsBody());unitSheetsPaint();}catch(e){toast(errText(e));}finally{u.busy=false;}}
async function unitSheetsNativeApply(){const u=USHEET,n=u.native;if(!n||u.busy||!confirm(tt('sheets.native_confirm',{count:n.units})))return;u.busy=true;try{const applied=await api.post('/api/unit_sheets/native_apply',unitSheetsBody({plan_token:n.plan_token}));if(applied.warning)toast(applied.warning);u.native=null;u.past=[];u.future=[];toast(tt('sheets.native_done'));}catch(e){toast(errText(e));}finally{u.busy=false;}await unitSheetsRequest('load');}
