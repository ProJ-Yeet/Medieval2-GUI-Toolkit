const SX_TAB_KEYS = {addons:'scripts.tab_addons',builder:'scripts.tab_builder',campscript:'scripts.tab_campscript',lua:'scripts.tab_lua'};
// 125: the Lua tab is offered only with *Opt into beta features*
const sxTabs = () => ['addons','builder','campscript'].concat(betaOn() ? ['lua'] : []);
const SX_VIEW_KEYS = {form:'scripts.view_form',blocks:'scripts.view_blocks'};
/* Script add-ons, recipe builder and campaign-piece removal. */

function sxPart(list, key){ return (list || []).find(x => x.key === key); }
function sxNewRecipe(){
  return {v: 1, title: tt('scripts.my_module'), game: 'medieval2', when: 'player_turn', once: false,
    ifs: [], dos: [], else: [], settings: {}, match: 'all', each: '', each_of: 'this', each_faction: ''};
}
async function loadScripts(){
  const mod = state.src, old = state.sx && state.sx.mod === mod ? state.sx : null;
  const s = state.sx = {mod, tab: old ? old.tab : 'addons', recipe: old ? old.recipe : sxNewRecipe(),
    view: old ? old.view : 'form', busy: true, vocab: old && old.vocab, cs: old && old.cs};
  renderScripts();
  try{
    const r = await api.get('/api/scripts?mod=' + enc(mod));
    if(stale('scripts', mod) || state.sx !== s) return;
    Object.assign(s, r); s.error = r.error || '';
  }catch(e){ if(state.sx === s) s.error = errText(e); }
  finally{ s.busy = false; if(!stale('scripts',mod) && state.sx === s) renderScripts(); }
}
function sxTab(tab){ state.sx.tab = tab; renderScripts(); }
function renderScripts(){
  if(state.mode !== 'scripts') return;
  const s = state.sx;
  if(!s || s.mod !== state.src){ loadScripts(); return; }
  if(s.busy){ main.innerHTML = `<div class="empty">${tt('common.reading')} ${esc(s.mod)}</div>`; return; }
  if(s.error){ main.innerHTML = `<div class="w-bad">${esc(s.error)}</div>`; return; }
  if(!sxTabs().includes(s.tab)) s.tab = 'addons';
  sxLuaKeep();
  main.innerHTML = `<div class="sxwrap"><h3>${tt('scripts.head')}</h3>
    <p class="trnote">${s.m2ex ? tt('scripts.m2ex_yes',{target: esc(s.target)}) : tt('scripts.m2ex_no')}</p>
    <div class="hxtabs">${sxTabs().map(t => `<button class="${s.tab === t ? 'on' : ''}" onclick="sxTab('${t}')">${tt(SX_TAB_KEYS[t])}</button>`).join('')}</div>
    ${s.tab === 'builder' ? sxBuilderHtml() : s.tab === 'campscript' ? sxCampaignHtml() : s.tab === 'lua' ? sxLuaHtml() : sxAddonsHtml()}</div>`;
  if(s.tab === 'lua') sxLuaMount();
}

/* ---- 125: Lua scripts over the toolkit's data (lua_cli.py's run, from the app) ---- */
const SX_LUA_START = 'print(#toolkit.units())\n';  // Lua, not text
function sxLua(){
  const s = state.sx;
  if(!s.lua){ s.lua = {list: null, name: 'my_script.lua', text: [`-- ${tt('scripts.lua_first_line')}`, SX_LUA_START].join('\n'), args: '', busy: false, report: null}; sxLuaLoad(); }
  return s.lua;
}
async function sxLuaLoad(){
  const L = state.sx.lua;
  try{ L.list = await api.post('/api/lua/scripts', {}); }
  catch(e){ L.list = {error: errText(e)}; }
  if(state.sx && state.sx.lua === L) renderScripts();
}
// the editor's text, name and args back into state before the page is redrawn
function sxLuaKeep(){
  const L = state.sx && state.sx.lua; if(!L) return;
  if(L.cm) L.text = L.cm.getValue();
  else { const t = document.getElementById('sxLuaText'); if(t) L.text = t.value; }
  const n = document.getElementById('sxLuaName'); if(n) L.name = n.value;
  const a = document.getElementById('sxLuaArgs'); if(a) L.args = a.value;
  L.cm = null;
}
function sxLuaHtml(){
  const L = sxLua();
  if(!L.list) return `<div class="empty">${tt('common.reading')}</div>`;
  if(L.list.error) return `<div class="w-bad">${esc(L.list.error)}</div>`;
  if(!L.list.available) return `<p class="w-bad">${tt('scripts.lua_no_runtime')}</p>`;
  const opt = (grp, items) => items.length ? `<optgroup label="${esc(grp)}">${items.map(x => `<option value="${esc(grp)}|${esc(x.name)}">${esc(x.name)}</option>`).join('')}</optgroup>` : '';
  const off = L.busy ? 'disabled' : '';
  return `<div class="sxlua">
    <p class="trnote">${tt('scripts.lua_intro')}</p>
    <div class="sxbtns"><select onchange="sxLuaPick(this.value)"><option value="">${tt('scripts.lua_open')}</option>
      ${opt(tt('scripts.lua_saved'), L.list.scripts || [])}${opt(tt('scripts.lua_examples'), L.list.examples || [])}</select>
      <input id="sxLuaName" value="${esc(L.name)}" title="${esc(tt('scripts.lua_name_hint'))}">
      <button ${off} onclick="sxLuaSave()">${tt('scripts.lua_save')}</button></div>
    <textarea id="sxLuaText" class="sxluatext" spellcheck="false">${esc(L.text)}</textarea>
    <label class="sxfield">${tt('scripts.lua_args')}<textarea id="sxLuaArgs" rows="2" spellcheck="false" placeholder="faction=england">${esc(L.args)}</textarea></label>
    <div class="sxbtns"><button ${off} onclick="sxLuaRun(false)">${tt('scripts.lua_dry_run')}</button>
      <button class="primary" ${off} onclick="sxLuaRun(true)">${tt('scripts.lua_apply')}</button>
      ${L.busy ? `<span class="count">${tt('scripts.lua_running')}</span>` : ''}</div>
    ${sxLuaReport(L.report)}
    <details class="sxluaapi"><summary>${tt('scripts.lua_api')}</summary>${(L.list.api || []).map(f =>
      `<div><code>toolkit.${esc(f.name)}(${esc(f.params.join(', '))})</code> <span class="count">${esc(f.doc)}</span></div>`).join('')}</details>
  </div>`;
}
function sxLuaReport(r){
  if(!r) return '';
  const head = !r.ok ? `<p class="w-bad">${esc(r.error)}</p>`
    : r.applied ? `<p class="w-ok">${tt('scripts.lua_applied', {id: esc(r.log_id), s: r.seconds})}</p>`
    : `<p class="trnote">${tt(r.files.length ? 'scripts.lua_dry_done' : 'scripts.lua_no_change', {n: r.files.length, s: r.seconds})}</p>`;
  const line = l => `<div class="${l.startsWith('+') && !l.startsWith('+++') ? 'sxladd' : l.startsWith('-') && !l.startsWith('---') ? 'sxldel' : l.startsWith('@@') ? 'sxlhunk' : ''}">${esc(l) || ' '}</div>`;
  return `<section class="bsec sxluarep">${head}
    ${(r.printed || []).length ? `<h4>${tt('scripts.lua_printed')}</h4><pre>${esc(r.printed.join('\n'))}</pre>` : ''}
    ${(r.edits || []).length ? `<h4>${tt('scripts.lua_edits')}</h4><ul>${r.edits.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : ''}
    ${(r.warnings || []).length ? `<ul class="w-warn">${r.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
    ${(r.files || []).map(f => `<details><summary>${esc(f.rel)} <span class="count">${esc(f.status)} +${f.added} -${f.removed}</span></summary>
      <div class="sxldiff">${f.diff.split('\n').map(line).join('')}</div></details>`).join('')}</section>`;
}
// CodeMirror 5 with its Lua mode, when the page has it; a plain text box otherwise
function sxLuaMount(){
  const L = state.sx.lua, ta = document.getElementById('sxLuaText');
  if(!ta || !window.CodeMirror) return;
  L.cm = CodeMirror.fromTextArea(ta, {mode: 'lua', lineNumbers: true, indentUnit: 2, tabSize: 2,
    extraKeys: {'Ctrl-Space': cm => cm.showHint && cm.showHint({hint: sxLuaHint, completeSingle: false})}});
}
function sxLuaHint(cm){
  const cur = cm.getCursor(), line = cm.getLine(cur.line).slice(0, cur.ch);
  const m = /toolkit\.(\w*)$/.exec(line); if(!m) return null;
  const list = (state.sx.lua.list.api || []).filter(f => f.name.startsWith(m[1]))
    .map(f => ({text: f.name + '(', displayText: `${f.name}(${f.params.join(', ')})`}));
  return {list, from: CodeMirror.Pos(cur.line, cur.ch - m[1].length), to: cur};
}
function sxLuaPick(v){
  if(!v) return;
  sxLuaKeep();
  const L = state.sx.lua, i = v.indexOf('|'), grp = v.slice(0, i), name = v.slice(i + 1);
  const it = (grp === tt('scripts.lua_examples') ? L.list.examples : L.list.scripts).find(x => x.name === name);
  if(it){
    // into the boxes too: the redraw reads them back (sxLuaKeep)
    const ta = document.getElementById('sxLuaText'), nm = document.getElementById('sxLuaName');
    if(ta) ta.value = it.text;
    if(nm) nm.value = it.name;
    L.text = it.text; L.name = it.name; L.report = null;
  }
  renderScripts();
}
function sxLuaArgs(text){
  const out = {};
  for(const ln of String(text || '').split('\n')){
    const i = ln.indexOf('='); if(i > 0) out[ln.slice(0, i).trim()] = ln.slice(i + 1).trim();
  }
  return out;
}
async function sxLuaSave(){
  sxLuaKeep(); const L = state.sx.lua;
  try{ const r = await api.post('/api/lua/save', {name: L.name, text: L.text}); L.name = r.name; toast(tt('scripts.lua_saved_as', {name: r.name})); sxLuaLoad(); }
  catch(e){ toast(errText(e)); renderScripts(); }
}
async function sxLuaRun(apply){
  sxLuaKeep(); const L = state.sx.lua; if(L.busy) return;
  if(apply && !confirm(tt('scripts.lua_apply_confirm', {mod: state.sx.mod}))){ renderScripts(); return; }
  L.busy = true; L.report = null; renderScripts();
  try{ L.report = await api.post('/api/lua/run', {mod: state.sx.mod, name: L.name, text: L.text, args: sxLuaArgs(L.args), apply}); }
  catch(e){ L.report = {ok: false, error: errText(e)}; }
  finally{ L.busy = false; if(L.report && L.report.name) L.name = L.report.name; if(state.sx && state.sx.lua === L) renderScripts(); }
}
function sxPairs(pairs, value){
  return (pairs || []).map(([v,l]) => `<option value="${esc(v)}"${v === value ? ' selected' : ''}>${esc(l)}</option>`).join('');
}
function sxAddonsHtml(){
  return `<div class="sxaddons">${(state.sx.addons || []).map((a,i) => `<section class="bsec sxaddon"><h4>${esc(a.title)} ${a.installed ? `<span class="badge">${tt('scripts.in')}</span>` : ''}</h4>
    <p>${esc(a.summary || '')}</p><div class="count">${a.files ? tt('scripts.no_engine') : tt('scripts.needs_m2ex')}</div>
    ${a.error ? `<p class="w-bad">${esc(a.error)}</p>` : ''}
    ${(a.settings || []).map(f => sxAddonSetting(a,f)).join('')}
    <div class="sxbtns"><button class="primary" ${state.sx.acting ? 'disabled' : ''} onclick="sxAddon(${i},'install')">${a.installed ? tt('scripts.update') : tt('scripts.put_in')}</button>
    ${a.installed ? `<button class="danger" ${state.sx.acting ? 'disabled' : ''} onclick="sxAddon(${i},'remove')">${tt('scripts.take_out')}</button>` : ''}</div></section>`).join('')}</div>`;
}
function sxAddonSetting(a,f){
  const id = 'sx_' + a.key + '_' + f.var, val = (a.values || {})[f.var] ?? f.default ?? '';
  const attrs = `id="${esc(id)}" title="${esc(f.help || '')}"`;
  let input;
  if(f.kind === 'bool') input = `<input type="checkbox" ${attrs}${val === true || val === 'true' ? ' checked' : ''}>`;
  else if(f.kind === 'choice') input = `<select ${attrs}>${sxPairs(f.choices,String(val))}</select>`;
  else input = `<input ${attrs} type="${['int','float'].includes(f.kind) ? 'number' : 'text'}" ${['int','float'].includes(f.kind) ? 'step="any"' : ''} value="${esc(Array.isArray(val) ? val.join(', ') : val)}">`;
  return `<label class="sxfield">${esc(f.label)} ${input}<span class="count">${esc(f.help || '')}</span></label>`;
}
async function sxAddon(index,action){
  const s = state.sx, a = s.addons[index]; if(s.acting) return;
  const values = {};
  if(action === 'install') for(const f of a.settings || []){
    const el = document.getElementById('sx_' + a.key + '_' + f.var);
    values[f.var] = f.kind === 'bool' ? String(el.checked) : ['list','set'].includes(f.kind) ? sxList(el.value) : el.value;
  }
  const body = {mod: s.mod, key: a.key, action, values};
  s.acting = true;
  try{
    const p = await api.post('/api/scripts/addon/plan',body); if(p.error) throw new Error(p.error);
    if(state.sx !== s || stale('scripts',s.mod)) return;
    if(!confirm(tt('scripts.confirm',{words: (p.words || []).join('\n')}))) return;
    const r = await api.post('/api/scripts/addon/apply',body); if(r.error) throw new Error(r.error);
    toast(tt('common.saved_log_can_undo_it')); if(state.sx === s && !stale('scripts',s.mod)) await loadScripts();
  }catch(e){ toast(errText(e)); }
  finally{ s.acting = false; }
}
function sxList(value){ return value.split(',').map(x => x.trim()).filter(Boolean); }
function sxChange(name,value,redraw){ state.sx.recipe[name] = value; state.sx.pv = null; if(redraw) renderScripts(); else sxHidePreview(); }
function sxHidePreview(){ const el = document.getElementById('sxPreview'); if(el) el.innerHTML = ''; }
function sxRecipeEdited(){
  const s = state.sx;
  if(s.previewRecipe && s.previewRecipe !== JSON.stringify(s.recipe)){ s.pv = null; sxHidePreview(); }
}
function sxFieldHtml(group,index,field,item){
  const kind = field.kind || '', v = item[field.name] ?? '', voc = state.sx.vocab;
  const attrs = `data-g="${group}" data-i="${index}" data-n="${esc(field.name)}"`;
  const change = `sxFieldChange(this)`;
  const pairKey = {op:'ops', turn_op:'ops', who:'who', to:'to', stance:'stances'}[kind];
  let input;
  if(pairKey) input = `<select ${attrs} onchange="${change}">${sxPairs(voc[pairKey],v)}</select>`;
  else if(kind === 'long') input = `<textarea ${attrs} oninput="${change}">${esc(v)}</textarea>`;
  else{
    const numeric = ['int','signed','percent'].includes(kind);
    input = `<input ${attrs} data-list="${kind.startsWith('names:') ? '1' : ''}" type="${numeric ? 'number' : 'text'}" step="any" data-number="${numeric ? '1' : ''}" placeholder="${kind.startsWith('names:') ? ttA('scripts.comma_list') : ''}" value="${esc(Array.isArray(v) ? v.join(', ') : v)}" oninput="${change}">`;
  }
  return `<label class="sxfield${kind === 'long' || /condition|command/.test(field.name) || /condition|command/.test(kind) ? ' sxwide' : ''}" title="${esc(field.help || '')}">${esc(field.label || field.name)}${input}<span class="count">${esc(field.help || '')}</span></label>`;
}
function sxFieldChange(el){
  const d = el.dataset, item = state.sx.recipe[d.g][Number(d.i)];
  item[d.n] = d.list ? sxList(el.value) : d.number && el.value !== '' ? Number(el.value) : el.value;
  state.sx.pv = null; sxHidePreview();
}
function sxDrop(group,index){ state.sx.recipe[group].splice(index,1); state.sx.pv = null; renderScripts(); }
function sxItem(group,key){
  const p = sxPart(group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions,key), out = {k:key};
  for(const f of p && p.fields || []) out[f.name] = f.default === undefined ? '' : JSON.parse(JSON.stringify(f.default));
  return out;
}
function sxAdd(group){
  const list = group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions;
  if(list.length) state.sx.recipe[group].push(sxItem(group,list[0].key));
  state.sx.pv = null; renderScripts();
}
function sxKind(group,index,key){ state.sx.recipe[group][index] = sxItem(group,key); state.sx.pv = null; renderScripts(); }
function sxRowsHtml(group){
  const list = group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions;
  return (state.sx.recipe[group] || []).map((item,i) => {
    const p = sxPart(list,item.k);
    return `<div class="sxitem"><select onchange="sxKind('${group}',${i},this.value)">${list.map(x => `<option value="${esc(x.key)}"${x.key === item.k ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}</select>
    <span class="count">${esc(p && p.help || '')}</span>${(p && p.fields || []).map(f => sxFieldHtml(group,i,f,item)).join('')}
    <button class="mini" onclick="sxDrop('${group}',${i})">×</button></div>`;
  }).join('') + `<button class="mini" onclick="sxAdd('${group}')">${tt('scripts.add_line')}</button>`;
}
function sxRecipeSelect(field,pairs,redraw){
  return `<select onchange="sxChange('${field}',this.value,${!!redraw})">${sxPairs(pairs,state.sx.recipe[field])}</select>`;
}
function sxBuilderHtml(){
  const s = state.sx, r = s.recipe, v = s.vocab;
  return `<section class="bsec" oninput="sxRecipeEdited()" onchange="sxRecipeEdited()"><label>${tt('scripts.start_from')} <select onchange="sxExample(this.value)"><option value="">${tt('scripts.blank')}</option>${(v.examples || []).map(x => `<option value="${esc(x.title)}">${esc(x.label)}</option>`).join('')}</select></label>
    <input value="${esc(r.title)}" oninput="sxChange('title',this.value,false)">
    <div class="sxview">${['form','blocks'].map(t => `<button class="${s.view === t ? 'on' : ''}" onclick="state.sx.view='${t}';renderScripts()">${tt(SX_VIEW_KEYS[t])}</button>`).join('')}</div>
    ${s.view === 'blocks' ? sxBlocksHtml() : `<div><label>${tt('scripts.when')} ${sxRecipeSelect('when',v.events.map(x => [x.key,x.label]),false)}</label>
      <label class="chk"><input type="checkbox" ${r.once ? 'checked' : ''} onchange="sxChange('once',this.checked,false)">${tt('scripts.once')}</label>
      <h4>${tt('scripts.if')} ${sxRecipeSelect('match',v.match,false)}</h4>${sxRowsHtml('ifs')}
      <h4>${tt('scripts.do')} ${sxRecipeSelect('each',v.each,true)} ${r.each ? sxRecipeSelect('each_of',v.each_of,true) : ''}
      ${r.each && r.each_of === 'named' ? `<input value="${esc(r.each_faction)}" oninput="sxChange('each_faction',this.value,false)">` : ''}</h4>${sxRowsHtml('dos')}
      <h4>${tt('scripts.else')}</h4>${sxRowsHtml('else')}</div>`}
    <button class="primary" onclick="sxPreview()">${tt('scripts.read_back')}</button><div id="sxPreview">${sxPreviewHtml()}</div>
    ${(s.mine || []).length ? `<h4>${tt('scripts.mine')}</h4>${s.mine.map((x,i) => `<button onclick="sxOpenMine(${i})">${esc(x.title)}</button>`).join('')}` : ''}</section>`;
}
async function sxExample(title){
  if(!title) return;
  const s = state.sx, token = s.exampleRequest = {};
  try{
    const r = await api.post('/api/scripts/example',{mod:s.mod,title}); if(r.error) throw new Error(r.error);
    if(state.sx !== s || s.exampleRequest !== token) return;
    s.recipe = r.recipe; s.pv = null; renderScripts();
  }catch(e){ toast(errText(e)); }
}
function sxOpenMine(index){ const s = state.sx; s.recipe = JSON.parse(JSON.stringify(s.mine[index].recipe)); s.pv = null; renderScripts(); }
async function sxPreview(){
  const s = state.sx, recipe = JSON.parse(JSON.stringify(s.recipe));
  try{
    const p = await api.post('/api/scripts/preview',{mod:s.mod,recipe}); if(p.error) throw new Error(p.error);
    if(state.sx === s && JSON.stringify(s.recipe) === JSON.stringify(recipe)){ s.pv = p; s.previewRecipe = JSON.stringify(recipe); renderScripts(); }
  }catch(e){ toast(errText(e)); }
}
function sxPreviewHtml(){
  const p = state.sx.pv; if(!p) return '';
  return `<div class="sxwords">${esc(Array.isArray(p.words) ? p.words.join('\n') : p.words || '').replace(/\n/g,'<br>')}</div>
    ${(p.problems || []).map(x => `<p class="w-bad">${esc(x)}</p>`).join('')}
    ${p.script ? `<details><summary>${tt('scripts.the_script')}</summary><pre class="hxpre">${esc(p.script)}</pre></details>` : ''}
    ${!(p.problems || []).length ? `<button class="primary" onclick="sxSave()">${tt('scripts.save')}</button>` : ''}`;
}
async function sxSave(){
  const s = state.sx;
  if(!s.pv || (s.pv.problems || []).length) return;
  // Blocks can change fields directly; require the exact recipe that was read back.
  if(s.previewRecipe !== JSON.stringify(s.recipe)){ s.pv = null; renderScripts(); return; }
  try{
    const r = await api.post('/api/scripts/save',{mod:s.mod,recipe:JSON.parse(JSON.stringify(s.recipe))});
    if(r.error) throw new Error(r.error);
    toast(tt('scripts.saved',{title:r.title}));
    if(state.sx === s && !stale('scripts',s.mod)){ s.tab = 'addons'; await loadScripts(); }
  }catch(e){ toast(errText(e)); }
}
function sxCampaignHtml(){
  const s = state.sx;
  if(!s.cs){ sxCampaignLoad(''); return `<div>${tt('common.reading')}</div>`; }
  const c = s.cs;
  if(c.loading) return `<div>${tt('common.reading')}</div>`;
  const campaigns = c.campaigns || [];
  const choose = campaigns.length > 1 ? `<select onchange="sxCampaignLoad(this.value)">${sxPairs(campaigns.map(x => typeof x === 'string' ? [x,x] : [x.name,x.label || x.name]),c.campaign)}</select>` : '';
  if(c.error || c.problem || c.readonly) return choose + `<div class="w-bad">${esc(c.error || c.problem || c.readonly)}</div>`;
  return `<section class="bsec sxcs">${choose}<p>${tt('scripts.cs_head',{rel:esc(c.rel),lines:c.lines})}</p>
    ${(c.warnings || []).map(w => `<p class="w-warn">${esc(w)}</p>`).join('')}
    <input type="search" placeholder="${ttA('scripts.cs_filter')}" value="${esc(c.filter)}" oninput="state.sx.cs.filter=this.value;sxCampaignList()">
    <div class="sxbtns"><button ${c.busy ? 'disabled' : ''} onclick="sxCampaignRemove(false)">${tt('scripts.cs_take_picked')}</button><button ${c.busy ? 'disabled' : ''} onclick="sxCampaignRemove(true)">${tt('scripts.cs_take_shown')}</button>
    <button onclick="state.sx.cs.picked=[];sxCampaignList()">${tt('scripts.cs_clear')}</button></div><div id="sxCsList">${sxCampaignRows()}</div></section>`;
}
async function sxCampaignLoad(campaign){
  const s = state.sx, c = s.cs = {loading:true, filter:'', picked:[]};
  let r;
  try{ r = await api.get(`/api/campscript?mod=${enc(s.mod)}&campaign=${enc(campaign)}`); }catch(e){ r = {error:errText(e)}; }
  if(state.sx !== s || s.cs !== c) return;
  Object.assign(c,r,{loading:false}); if(!stale('scripts',s.mod)) renderScripts();
}
function sxCampaignMatches(){
  const c = state.sx.cs, filter = c.filter.toLowerCase();
  return (c.pieces || []).filter(p => !p.frame && [p.kind,p.head,p.comment].join(' ').toLowerCase().includes(filter));
}
function sxCampaignRows(){
  const c = state.sx.cs, rows = sxCampaignMatches(), total = (c.pieces || []).filter(p => !p.frame).length;
  return `<p class="count">${tt('scripts.cs_shown',{n:rows.length,of:total,picked:c.picked.length})}</p><div class="sxcslist">${rows.slice(0,500).map(p => `<label class="sxcsrow" title="${ttA('scripts.cs_lines',{a:p.start+1,b:p.end+1})}"><input type="checkbox" ${c.picked.includes(p.n) ? 'checked' : ''} onchange="sxCampaignPick(${p.n},this.checked)"> <span class="badge">${esc(p.kind)}</span> ${esc(p.head)} <span class="count">${ttN('scripts.cs_n_lines',p.lines)}</span>${p.comment ? `<div class="count">${esc(p.comment)}</div>` : ''}</label>`).join('')}</div>
    ${rows.length > 500 ? `<p>${tt('scripts.cs_more',{n:rows.length-500})}</p>` : ''}`;
}
function sxCampaignList(){ const el = document.getElementById('sxCsList'); if(el) el.innerHTML = sxCampaignRows(); }
function sxCampaignPick(n,checked){ const c = state.sx.cs; c.picked = c.picked.filter(x => x !== n); if(checked) c.picked.push(n); sxCampaignList(); }
async function sxCampaignRemove(shown){
  const s = state.sx, c = s.cs; if(c.busy) return;
  const drop = shown ? sxCampaignMatches().map(p => p.n) : [...c.picked];
  if(!drop.length){ toast(tt('scripts.cs_none')); return; }
  const body = {mod:s.mod,campaign:c.campaign,sig:c.sig,drop};
  c.busy = true; renderScripts();
  try{
    const r = await api.post('/api/campscript/plan',body); if(r.error) throw new Error(r.error);
    if(state.sx !== s || s.cs !== c) return;
    const p = r.plan || {};
    if(!confirm(tt('scripts.cs_confirm',{n:drop.length,changes:(p.changes || []).join('\n'),warnings:(p.warnings || []).slice(0,4).join('\n')}))) return;
    const done = await api.post('/api/campscript/apply',body); if(done.error) throw new Error(done.error);
    toast(tt('common.saved_log_can_undo_it')); if(state.sx === s && s.cs === c) await sxCampaignLoad(c.campaign);
  }catch(e){ toast(errText(e)); }
  finally{ c.busy = false; if(state.sx === s && s.cs === c && !stale('scripts',s.mod)) renderScripts(); }
}
