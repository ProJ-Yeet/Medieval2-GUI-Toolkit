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
  {id: 'animals', label: 'Animals', file: 'descr_animals.txt'},
  {id: 'standards', label: 'Standards', file: 'descr_standards.txt'},
  {id: 'advice', label: 'Advice', file: 'export_descr_advice.txt'},
];

async function loadSideFiles(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s animals, standards and advice…</div>';
  let r;
  try{ r = await api.get('/api/sidefiles?mod=' + enc(mod)); }
  catch(e){ if(stale('sidefiles', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read them.<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadSideFiles()">Retry</button></div>`; return; }
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
          animals: 'the war animals a unit\'s `animal` line names, and the battle model each is drawn with',
          standards: 'how the campaign map draws an army\'s and a fleet\'s standard, and the faction symbol sheets',
          advice: 'the advisor\'s threads and the triggers that fire them'}[c.tab]}</span></div>
        <span style="flex:1"></span>
        <button onclick="sdxRevert()" ${n ? '' : 'disabled'}>Revert</button>
        <button class="primary" onclick="sdxSave()" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
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
        <div class="nm">${esc(a.name)}${w.remove.includes(a.name) ? ' <span class="count">removed on save</span>' : ''}</div>
        <div class="sub">${esc((a.fields.class || {}).value || '?')} · ${a.units.length} unit(s)${w.edit[a.name] ? ' · <b>changed</b>' : ''}</div></button>`).join('')
      + w.add.map(a => `<div class="trnote">+ ${esc(a.name)} (from ${esc(a.like)}) on save</div>`).join('')
      + ((c.animals || []).length ? `<div class="trnote">New animal <input id="sdxNewAnimal" placeholder="name" style="width:100px">
        copied from <select id="sdxLikeAnimal">${c.animals.map(a => `<option>${esc(a.name)}</option>`).join('')}</select>
        <button onclick="sdxAnimalAdd()">＋ Add</button></div>` : '');
  }
  if(c.tab === 'standards'){
    const ix = c.standard_indexes || {};
    const sheets = (c.standards || []).filter(r => r.kind === 'symbols');
    return `<div class="count" style="padding:8px">${sheets.filter(r => r.section === 'factions').length} faction sheet(s),
      ${sheets.filter(r => r.section === 'rebels_factions').length} rebel sheet(s).
      ${ix.factions ? `The roster's ${ix.factions} factions use standard_index up to ${ix.max}.` : ''}
      How many symbols a sheet holds is not checked: Divide and Conquer's index runs to 30 over seven faction sheets, and it plays.</div>`;
  }
  const a = c.advice || {threads: [], triggers: []};
  return a.threads.map(t => `<button class="trrow${c.sel === t.name ? ' on' : ''}" onclick="sdxPick('${q1(esc(t.name))}')">
      <div class="nm">${esc(t.name)}${c.w.advice.remove.includes(t.name) ? ' <span class="count">removed on save</span>' : ''}</div>
      <div class="sub">${esc(t.area || '?')} · ${t.items.length} item(s) · fired by ${a.triggers.filter(g => g.fires.some(f => f.thread === t.name)).length}</div></button>`).join('')
    || '<div class="count" style="padding:8px">No advice threads - the file is its header and nothing else.</div>';
}

/* ---- animals ---- */
function sdxAnimalsHtml(){
  const c = state.sdx, a = (c.animals || []).find(x => x.name === c.sel);
  if(!a) return '<div class="count" style="padding:8px">Pick an animal.</div>';
  const w = c.w.animals.edit[a.name] || {};
  const val = k => w[k] !== undefined ? w[k] : ((a.fields[k] || {}).value || '');
  const gone = c.w.animals.remove.includes(a.name);
  return `<div class="cdbsec"><h3>${esc(a.name)}</h3>
    <table class="smxtab"><tr><th>key</th><th>value</th><th></th></tr>
    ${['class', 'model', 'radius', 'x_radius', 'height', 'mass'].map(k => `<tr><td><code>${k}</code></td>
      <td><input style="width:${k === 'model' ? 260 : 90}px" value="${esc(val(k))}" onchange="sdxAnimalSet('${q1(esc(a.name))}','${k}',this.value)"></td>
      <td class="count">${k === 'model' && a.model_known === false ? '<span class="w-warn">not in the battle modeldb</span>'
        : k === 'x_radius' ? 'optional: the other radius of an oval animal' : ''}</td></tr>`).join('')}
    </table>
    <div class="count">${a.units.length ? 'Units carrying it: ' + a.units.map(esc).join(', ') : 'No unit\'s <code>animal</code> line names it.'}</div>
    <button onclick="sdxAnimalRemove('${q1(esc(a.name))}')">${gone ? 'Keep it' : 'Remove ' + esc(a.name)}</button></div>`;
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
  return `<div class="cdbsec"><h3>The flag models</h3>
    <table class="smxtab">${files.map(r => `<tr><td><code>${esc(r.key)}</code></td>
      <td>${box(r, 0, r.kind === 'file' ? 320 : 80)}</td>
      <td class="count">${r.kind === 'scale' ? 'the scale of the model on the next line' : r.on_disk ? 'in the mod' : 'not in the mod (the base game packs it)'}</td></tr>`).join('')}</table>
    <h3>Rectangles on the standard's texture</h3>
    <table class="smxtab"><tr><th></th><th>left</th><th>top</th><th>right</th><th>bottom</th><th>texture</th></tr>
    ${rects.map(r => `<tr><td><code>${esc(r.key)}</code></td>${[0, 1, 2, 3].map(k => `<td>${box(r, k, 70)}</td>`).join('')}
      <td>${r.values.length > 4 ? box(r, 4, 180) : ''}</td></tr>`).join('')}</table>
    ${['factions', 'rebels_factions'].map(sec => `<h3>Symbol sheets: <code>${sec}</code></h3>
      <table class="smxtab">${sheets(sec).map((r, i) => {
        const gone = w.symbols_remove.includes(r.line);
        return `<tr><td class="count">${i + 1}</td><td>${box(r, 0, 260)}</td>
          <td class="count">${r.on_disk ? 'in the mod' : 'not in the mod'}</td>
          <td><button onclick="sdxStdDrop(${r.line})">${gone ? 'keep' : '✕'}</button></td></tr>`;
      }).join('')}
      ${w.symbols_add.filter(s => s.section === sec).map(s => `<tr><td></td><td>+ ${esc(s.path)} on save</td></tr>`).join('')}</table>
      <input id="sdxSheet_${sec}" placeholder="banners/symbols11.tga" style="width:220px">
      <button onclick="sdxStdAdd('${sec}')">＋ a sheet</button>`).join('')}
    <div class="count">Each faction's <code>standard_index</code> in the roster picks its symbol from these sheets, in order,
      so a sheet taken out of the middle moves every index after it.</div></div>`;
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
  const trigHtml = trigs.map(g => `<div class="fsxblk"><div class="nm"><code>Trigger ${esc(g.name)}</code>
      <span class="count">line ${g.line} · when ${esc(g.event || '?')}</span></div>
      ${g.conditions.map(x => `<div class="count"><code>${esc(x)}</code></div>`).join('')}
      ${g.fires.map(f => `<div class="fsxrow">fires <code>${esc(f.thread)}</code>, score ${box(f.line, f.score, 50)}</div>`).join('')}</div>`).join('');
  if(!t) return `<div class="cdbsec">${a.threads.length ? '<div class="count">Pick a thread.</div>' : ''}${trigHtml}</div>`;
  const gone = c.w.advice.remove.includes(t.name);
  return `<div class="cdbsec"><h3>${esc(t.name)} <span class="count">GameArea ${esc(t.area || '?')}</span></h3>
    ${t.items.map(it => `<div class="fsxblk"><div class="nm"><code>Item ${esc(it.name)}</code> <span class="count">line ${it.line}</span></div>
      <table class="smxtab">${it.fields.map(f => `<tr><td><code>${esc(f.key)}</code></td>
        <td>${f.value ? box(f.line, f.value, f.key === 'On_display' ? 300 : 200) : '<span class="count">(a flag, no value)</span>'}</td></tr>`).join('')}</table></div>`).join('')}
    <h3>Triggers that fire it</h3>${trigHtml || '<div class="count">None - nothing ever shows this thread.</div>'}
    <button onclick="sdxAdvRemove('${q1(esc(t.name))}')">${gone ? 'Keep it' : 'Remove this thread, and any trigger that fires only it'}</button></div>`;
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
  if(!confirm(`Write ${(p.changes || []).length} change(s)?\n\n` + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  let res;
  try{ res = await api.post('/api/sidefiles/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadSideFiles();
}
