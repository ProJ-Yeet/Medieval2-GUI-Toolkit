/* sidefiles.js - Animals, standards and advice: descr_animals.txt,
   descr_standards.txt and export_descr_advice.txt

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ================= ANIMALS, STANDARDS AND ADVICE (64) =================
   Three small files, one tab each. Animals are records a unit's `animal`
   line names, each with a battle model. The standards file is the strat-map
   flag: two models with a scale, six rectangles on its texture, and the
   symbol sheets. The advice file is threads of items and the triggers that
   fire them - in ROCSS, the one that starts its background script.

   THE PAGE NEVER PARSES A GAME FILE: /api/sidefiles and its plan|apply. */

const SDX_TABS = [
  {id: 'animals', label: tt('sidefiles.animals'), file: 'descr_animals.txt'},
  {id: 'standards', label: tt('sidefiles.standards'), file: 'descr_standards.txt'},
  {id: 'advice', label: tt('sidefiles.advice'), file: 'export_descr_advice.txt'},
];

async function loadSideFiles(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('sidefiles.s_animals_standards_and_advice')}</div>`;
  let r;
  try{ r = await api.get('/api/sidefiles?mod=' + enc(mod)); }
  catch(e){ if(stale('sidefiles', mod)) return;
    main.innerHTML = `<div class="empty">${tt('common.couldnt_read_them')}<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadSideFiles()">${tt('common.retry')}</button></div>`; return; }
  if(stale('sidefiles', mod)) return;
  const keep = state.sdx && state.sdx.mod === mod ? state.sdx : null;
  state.sdx = Object.assign({mod, tab: keep ? keep.tab : 'animals', sel: keep ? keep.sel : '',
                             w: sdxBlank(), busy: false}, r);
  renderSideFiles();
}
function sdxBlank(){
  return {animals: {edit: {}, add: [], remove: []},
          standards: {lines: {}, symbols_add: [], symbols_remove: []},
          advice: {fields: {}, remove: []}};
}
function sdxChanged(){
  const w = state.sdx.w;
  return Object.values(w.animals.edit).reduce((s, o) => s + Object.keys(o).length, 0)
    + w.animals.add.length + w.animals.remove.length
    + Object.keys(w.standards.lines).length + w.standards.symbols_add.length + w.standards.symbols_remove.length
    + Object.keys(w.advice.fields).length + w.advice.remove.length;
}

function renderSideFiles(){
  const c = state.sdx;
  if(!c){ loadSideFiles(); return; }
  const tab = SDX_TABS.find(t => t.id === c.tab);
  const strip = minorTabsHtml('', 'data/' + tab.file);
  const find = (c.findings || []).filter(f => f.key.startsWith(c.tab + '/'))
    .map(f => Object.assign({}, f, {name: f.key}));
  const n = sdxChanged();
  const err = c[c.tab + '_error'];
  const body = err ? `<div class="count" style="padding:8px">${esc(err)}.</div>`
    : c.tab === 'animals' ? sdxAnimalsHtml() : c.tab === 'standards' ? sdxStandardsHtml() : sdxAdviceHtml();
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <div class="fsxtabs">${SDX_TABS.map(t => `<button class="${c.tab === t.id ? 'on' : ''}"
        onclick="sdxTab('${t.id}')">${t.label}</button>`).join('')}</div>
      ${findingsHtml('sidefiles', find, 'sdxOpen')}
      <div class="trrows">${sdxLeftHtml()}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>${esc(tab.file)}</b> <span class="count">${{
          animals: tt('sidefiles.the_war_animals_a_units_animal'),
          standards: tt('sidefiles.how_the_campaign_map_draws_an'),
          advice: tt('sidefiles.the_advisors_threads_and_the_triggers')}[c.tab]}</span></div>
        <span style="flex:1"></span>
        <button onclick="sdxRevert()" ${n ? '' : 'disabled'}>${tt('common.revert')}</button>
        <button class="primary" onclick="sdxSave()" ${n ? '' : 'disabled'}>${tt('sidefiles.save_change',{x:n || '',x2:n === 1 ? '' : 's'})}</button>
      </div>
      ${body}
    </div>
  </div>`;
}

function sdxTab(t){ state.sdx.tab = t; state.sdx.sel = ''; renderSideFiles(); }
function sdxPick(s){ state.sdx.sel = s; renderSideFiles(); }
function sdxOpen(key){
  const [tab, ...rest] = String(key).split('/');
  state.sdx.tab = tab;
  state.sdx.sel = tab === 'advice' && rest[0] === 'trigger' ? '' : rest.join('/');
  renderSideFiles();
}
function sdxRevert(){ state.sdx.w = sdxBlank(); renderSideFiles(); }

function sdxLeftHtml(){
  const c = state.sdx;
  if(c.tab === 'animals'){
    const w = c.w.animals;
    return (c.animals || []).map(a => `<button class="trrow${c.sel === a.name ? ' on' : ''}" onclick="sdxPick('${q1(esc(a.name))}')">
        <div class="nm">${esc(a.name)}${w.remove.includes(a.name) ? ` <span class="count">${tt('common.removed_on_save')}</span>` : ''}</div>
        <div class="sub">${tt('sidefiles.unit_s',{x:esc((a.fields.class || {}).value || '?'),units_n:a.units.length,x2:w.edit[a.name] ? ` ${tt('common.changed')}` : ''})}</div></button>`).join('')
      + w.add.map(a => `<div class="trnote">${tt('sidefiles.from_on_save',{name:esc(a.name),like:esc(a.like)})}</div>`).join('')
      + ((c.animals || []).length ? `<div class="trnote">${tt('sidefiles.new_animal')} <input id="sdxNewAnimal" placeholder="${ttA('sidefiles.name')}" style="width:100px">
        ${tt('sidefiles.copied_from')} <select id="sdxLikeAnimal">${c.animals.map(a => `<option>${esc(a.name)}</option>`).join('')}</select>
        <button onclick="sdxAnimalAdd()">${tt('common.add')}</button></div>` : '');
  }
  if(c.tab === 'standards'){
    const ix = c.standard_indexes || {};
    const sheets = (c.standards || []).filter(r => r.kind === 'symbols');
    return `<div class="count" style="padding:8px">${tt('sidefiles.faction_sheet_s_rebel_sheet_s',{n:sheets.filter(r => r.section === 'factions').length,n2:sheets.filter(r => r.section === 'rebels_factions').length,x:ix.factions ? tt('sidefiles.the_rosters_factions_use_standard_index',{factions:ix.factions,ix:ix.max}) : ''})}</div>`;
  }
  const a = c.advice || {threads: [], triggers: []};
  return a.threads.map(t => `<button class="trrow${c.sel === t.name ? ' on' : ''}" onclick="sdxPick('${q1(esc(t.name))}')">
      <div class="nm">${esc(t.name)}${c.w.advice.remove.includes(t.name) ? ` <span class="count">${tt('common.removed_on_save')}</span>` : ''}</div>
      <div class="sub">${tt('sidefiles.item_s_fired_by',{area:esc(t.area || '?'),items_n:t.items.length,n:a.triggers.filter(g => g.fires.some(f => f.thread === t.name)).length})}</div></button>`).join('')
    || `<div class="count" style="padding:8px">${tt('sidefiles.no_advice_threads_the_file_is')}</div>`;
}

/* ---- animals ---- */
function sdxAnimalsHtml(){
  const c = state.sdx, a = (c.animals || []).find(x => x.name === c.sel);
  if(!a) return `<div class="count" style="padding:8px">${tt('sidefiles.pick_an_animal')}</div>`;
  const w = c.w.animals.edit[a.name] || {};
  const val = k => w[k] !== undefined ? w[k] : ((a.fields[k] || {}).value || '');
  const gone = c.w.animals.remove.includes(a.name);
  return `<div class="cdbsec"><h3>${esc(a.name)}</h3>
    <table class="smxtab"><tr><th>${tt('sidefiles.key')}</th><th>${tt('common.value')}</th><th></th></tr>
    ${['class', 'model', 'radius', 'x_radius', 'height', 'mass'].map(k => `<tr><td><code>${k}</code></td>
      <td><input style="width:${k === 'model' ? 260 : 90}px" value="${esc(val(k))}" onchange="sdxAnimalSet('${q1(esc(a.name))}','${k}',this.value)"></td>
      <td class="count">${k === 'model' && a.model_known === false ? `<span class="w-warn">${tt('sidefiles.not_in_the_battle_modeldb')}</span>`
        : k === 'x_radius' ? tt('sidefiles.optional_the_other_radius_of_an') : ''}</td></tr>`).join('')}
    </table>
    <div class="count">${a.units.length ? tt('sidefiles.units_carrying_it') + a.units.map(esc).join(', ') : tt('sidefiles.no_units_animal_line_names_it')}</div>
    <button onclick="sdxAnimalRemove('${q1(esc(a.name))}')">${gone ? tt('common.keep_it') : tt('sidefiles.remove') + esc(a.name)}</button></div>`;
}
function sdxAnimalSet(name, k, v){
  const c = state.sdx, a = c.animals.find(x => x.name === name);
  const e = c.w.animals.edit[name] = c.w.animals.edit[name] || {};
  if(v.trim() === ((a.fields[k] || {}).value || '')) delete e[k]; else e[k] = v.trim();
  if(!Object.keys(e).length) delete c.w.animals.edit[name];
  renderSideFiles();
}
function sdxAnimalRemove(name){
  const r = state.sdx.w.animals.remove, i = r.indexOf(name);
  if(i >= 0) r.splice(i, 1); else r.push(name);
  renderSideFiles();
}
function sdxAnimalAdd(){
  const name = (document.getElementById('sdxNewAnimal').value || '').trim();
  const like = document.getElementById('sdxLikeAnimal').value;
  if(!name) return;
  state.sdx.w.animals.add.push({name, like});
  renderSideFiles();
}

/* ---- standards ---- */
function sdxStandardsHtml(){
  const c = state.sdx, rows = c.standards || [], w = c.w.standards;
  const cur = r => w.lines[r.line] || r.values;
  const box = (r, k, width) => `<input style="width:${width}px" value="${esc(cur(r)[k])}" onchange="sdxStdSet(${r.line}, ${k}, this.value)">`;
  const files = rows.filter(r => r.kind === 'scale' || r.kind === 'file');
  const rects = rows.filter(r => r.kind === 'rect');
  const sheets = sec => rows.filter(r => r.kind === 'symbols' && r.section === sec);
  return `<div class="cdbsec"><h3>${tt('sidefiles.the_flag_models')}</h3>
    <table class="smxtab">${files.map(r => `<tr><td><code>${esc(r.key)}</code></td>
      <td>${box(r, 0, r.kind === 'file' ? 320 : 80)}</td>
      <td class="count">${r.kind === 'scale' ? tt('sidefiles.the_scale_of_the_model_on') : r.on_disk ? tt('sidefiles.in_the_mod') : tt('sidefiles.not_in_the_mod_the_base')}</td></tr>`).join('')}</table>
    <h3>${tt('sidefiles.rectangles_on_the_standards_texture')}</h3>
    <table class="smxtab"><tr><th></th><th>${tt('sidefiles.left')}</th><th>${tt('sidefiles.top')}</th><th>${tt('sidefiles.right')}</th><th>${tt('sidefiles.bottom')}</th><th>${tt('sidefiles.texture')}</th></tr>
    ${rects.map(r => `<tr><td><code>${esc(r.key)}</code></td>${[0, 1, 2, 3].map(k => `<td>${box(r, k, 70)}</td>`).join('')}
      <td>${r.values.length > 4 ? box(r, 4, 180) : ''}</td></tr>`).join('')}</table>
    ${['factions', 'rebels_factions'].map(sec => `<h3>${tt('sidefiles.symbol_sheets')} <code>${sec}</code></h3>
      <table class="smxtab">${sheets(sec).map((r, i) => {
        const gone = w.symbols_remove.includes(r.line);
        return `<tr><td class="count">${i + 1}</td><td>${box(r, 0, 260)}</td>
          <td class="count">${r.on_disk ? tt('sidefiles.in_the_mod') : tt('sidefiles.not_in_the_mod')}</td>
          <td><button onclick="sdxStdDrop(${r.line})">${gone ? 'keep' : '✕'}</button></td></tr>`;
      }).join('')}
      ${w.symbols_add.filter(s => s.section === sec).map(s => `<tr><td></td><td>${tt('sidefiles.on_save',{path:esc(s.path)})}</td></tr>`).join('')}</table>
      <input id="sdxSheet_${sec}" placeholder="banners/symbols11.tga" style="width:220px">
      <button onclick="sdxStdAdd('${sec}')">${tt('sidefiles.a_sheet')}</button>`).join('')}
    <div class="count">${tt('sidefiles.each_factions_standard_index_in_the')}</div></div>`;
}
function sdxStdSet(line, k, v){
  const c = state.sdx, r = c.standards.find(x => x.line === line);
  const cur = (c.w.standards.lines[line] || r.values).slice();
  cur[k] = v.trim();
  if(cur.join('|') === r.values.join('|')) delete c.w.standards.lines[line]; else c.w.standards.lines[line] = cur;
  renderSideFiles();
}
function sdxStdDrop(line){
  const r = state.sdx.w.standards.symbols_remove, i = r.indexOf(line);
  if(i >= 0) r.splice(i, 1); else r.push(line);
  renderSideFiles();
}
function sdxStdAdd(sec){
  const path = (document.getElementById('sdxSheet_' + sec).value || '').trim();
  if(!path) return;
  state.sdx.w.standards.symbols_add.push({section: sec, path});
  renderSideFiles();
}

/* ---- advice ---- */
function sdxAdviceHtml(){
  const c = state.sdx, a = c.advice || {threads: [], triggers: []};
  const t = a.threads.find(x => x.name === c.sel);
  const trigs = t ? a.triggers.filter(g => g.fires.some(f => f.thread === t.name)) : a.triggers;
  const w = c.w.advice.fields;
  const box = (line, v, width) => `<input style="width:${width}px" value="${esc(w[line] !== undefined ? w[line] : v)}"
    onchange="sdxAdvSet(${line}, this.value, '${q1(esc(v))}')">`;
  const trigHtml = trigs.map(g => `<div class="fsxblk"><div class="nm">${tt('sidefiles.trigger_line_when',{name:esc(g.name),line:g.line,event:esc(g.event || '?')})}</div>
      ${g.conditions.map(x => `<div class="count"><code>${esc(x)}</code></div>`).join('')}
      ${g.fires.map(f => `<div class="fsxrow">${tt('sidefiles.fires_score',{thread:esc(f.thread),x:box(f.line, f.score, 50)})}</div>`).join('')}</div>`).join('');
  if(!t) return `<div class="cdbsec">${a.threads.length ? `<div class="count">${tt('sidefiles.pick_a_thread')}</div>` : ''}${trigHtml}</div>`;
  const gone = c.w.advice.remove.includes(t.name);
  return `<div class="cdbsec"><h3>${tt('sidefiles.gamearea',{name:esc(t.name),area:esc(t.area || '?')})}</h3>
    ${t.items.map(it => `<div class="fsxblk"><div class="nm">${tt('sidefiles.item_line',{name:esc(it.name),line:it.line})}</div>
      <table class="smxtab">${it.fields.map(f => `<tr><td><code>${esc(f.key)}</code></td>
        <td>${f.value ? box(f.line, f.value, f.key === 'On_display' ? 300 : 200) : `<span class="count">${tt('sidefiles.a_flag_no_value')}</span>`}</td></tr>`).join('')}</table></div>`).join('')}
    <h3>${tt('sidefiles.triggers_that_fire_it')}</h3>${trigHtml || `<div class="count">${tt('sidefiles.none_nothing_ever_shows_this_thread')}</div>`}
    <button onclick="sdxAdvRemove('${q1(esc(t.name))}')">${gone ? tt('common.keep_it') : tt('sidefiles.remove_this_thread_and_any_trigger')}</button></div>`;
}
function sdxAdvSet(line, v, was){
  const w = state.sdx.w.advice.fields;
  if(v.trim() === was) delete w[line]; else w[line] = v.trim();
  renderSideFiles();
}
function sdxAdvRemove(name){
  const r = state.sdx.w.advice.remove, i = r.indexOf(name);
  if(i >= 0) r.splice(i, 1); else r.push(name);
  renderSideFiles();
}

async function sdxSave(){
  const c = state.sdx;
  if(c.busy) return;
  const w = c.w, body = {mod: state.src, sigs: c.sigs || {}};
  if(Object.keys(w.animals.edit).length || w.animals.add.length || w.animals.remove.length) body.animals = w.animals;
  if(Object.keys(w.standards.lines).length || w.standards.symbols_add.length || w.standards.symbols_remove.length) body.standards = w.standards;
  if(Object.keys(w.advice.fields).length || w.advice.remove.length) body.advice = w.advice;
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/sidefiles/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(tt('sidefiles.write_change_s',{n:(p.changes || []).length}) + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + tt('common.backed_up_first_and_log_can'))) return;
  let res;
  try{ res = await api.post('/api/sidefiles/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  await loadSideFiles();
}
