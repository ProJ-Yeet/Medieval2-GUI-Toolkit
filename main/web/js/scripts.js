/* scripts.js - Scripts: ready-made add-ons and the no-code Module builder (96e1)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   The Pfadfinder-Adam campaign editor's Add-ons window and Module builder,
   ported with its author's permission (unittransfer/script*.py). A script
   runs on M2EX, which loads every .nut of the game's script/modules folder;
   the two file add-ons change the mod's own files and need no engine. The
   page says which is which, and says plainly when the mod is not marked as
   running on M2EX.

   A recipe is WHEN something happens, IF conditions hold (all, any or none
   of them), DO actions, ELSE other actions, once or for each town, army or
   faction. The server reads it back in plain words, lists what is wrong
   with it, and writes the script; Save keeps it as an add-on of one's own,
   which is then put in like any other. Every name here starts `sx`.
   ===================================================================== */

async function loadScripts(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ${esc(mod)}</div>`;
  let r;
  try{ r = await api.get('/api/scripts?mod=' + enc(mod)); }
  catch(e){ if(stale('scripts', mod)) return; main.innerHTML = `<div class="empty">✗ ${esc(errText(e))}</div>`; return; }
  if(stale('scripts', mod)) return;
  const keep = state.sx && state.sx.mod === mod ? state.sx : null;
  state.sx = Object.assign({mod, tab: keep ? keep.tab : 'addons', recipe: keep ? keep.recipe : null, pv: null}, r);
  if(!state.sx.recipe) state.sx.recipe = {v: 1, title: tt('scripts.my_module'), game: 'medieval2', when: 'player_turn',
    once: false, ifs: [], dos: [], settings: {}, match: 'all', else: [], each: '', each_of: 'this', each_faction: ''};
  renderScripts();
}

function renderScripts(){
  const s = state.sx;
  if(!s || s.mod !== state.src){ loadScripts(); return; }
  const tab = (id, label) => `<button class="${s.tab === id ? 'on' : ''}" onclick="state.sx.tab='${id}';renderScripts()">${label}</button>`;
  main.innerHTML = `<div class="sxwrap">
    <div class="cdbhead"><div>${tt('scripts.head')}</div></div>
    <div class="trnote">${s.m2ex ? tt('scripts.m2ex_yes',{target:esc(s.target)}) : tt('scripts.m2ex_no')}</div>
    <div class="hxtabs">${tab('addons', tt('scripts.tab_addons'))}${tab('builder', tt('scripts.tab_builder'))}${tab('campscript', tt('scripts.tab_campscript'))}</div>
    ${s.tab === 'builder' ? sxBuilderHtml() : s.tab === 'campscript' ? sxCsHtml() : sxAddonsHtml()}
  </div>`;
}

/* ---- add-ons ---- */
function sxSettingHtml(a, st){
  const v = (a.values || {})[st.var];
  const id = `sx_${a.key}_${st.var}`;
  let box;
  if(st.kind === 'bool') box = `<input type="checkbox" id="${id}" ${String(v) === 'true' ? 'checked' : ''}>`;
  else if(st.kind === 'choice') box = `<select id="${id}">${st.choices.map(([cv, cl]) =>
    `<option value="${esc(cv)}" ${String(v) === String(cv) ? 'selected' : ''}>${esc(cl)}</option>`).join('')}</select>`;
  else if(st.kind === 'list' || st.kind === 'set') box = `<input id="${id}" value="${esc(Array.isArray(v) ? v.join(', ') : (v || ''))}" placeholder="${ttA('scripts.comma_list')}">`;
  else box = `<input id="${id}" value="${esc(v === undefined || v === null ? '' : v)}" type="${st.kind === 'int' || st.kind === 'float' ? 'number' : 'text'}" step="any">`;
  return `<label class="lbl" title="${esc(st.help || '')}">${esc(st.label)}</label><div>${box}<div class="count">${esc(st.help || '')}</div></div>`;
}

function sxValues(a){
  const out = {};
  for(const st of a.settings){
    const el = document.getElementById(`sx_${a.key}_${st.var}`);
    if(!el) continue;
    if(st.kind === 'bool') out[st.var] = el.checked ? 'true' : 'false';
    else if(st.kind === 'list' || st.kind === 'set') out[st.var] = el.value.split(',').map(x => x.trim()).filter(Boolean);
    else out[st.var] = el.value;
  }
  return out;
}

function sxAddonsHtml(){
  const s = state.sx;
  return `<div class="sxaddons">${s.addons.map(a => `<div class="bsec sxaddon">
    <h4>${esc(a.title)} ${a.installed ? `<span class="badge">${tt('scripts.in')}</span>` : ''}
      ${a.files ? `<span class="count">${tt('scripts.no_engine')}</span>` : `<span class="count">${tt('scripts.needs_m2ex')}</span>`}</h4>
    <div class="trnote">${esc(a.summary)}</div>
    ${a.error ? `<div class="w-bad">✗ ${esc(a.error)}</div>` : ''}
    ${a.settings.length ? `<div class="trgrid">${a.settings.map(st => sxSettingHtml(a, st)).join('')}</div>` : ''}
    <div class="sxbtns">
      <button class="primary" onclick="sxAddon('${q1(esc(a.key))}','install')">${a.installed ? tt('scripts.update') : tt('scripts.put_in')}</button>
      ${a.installed ? `<button class="danger" onclick="sxAddon('${q1(esc(a.key))}','remove')">${tt('scripts.take_out')}</button>` : ''}
    </div></div>`).join('')}</div>`;
}

async function sxAddon(key, action){
  const s = state.sx, a = s.addons.find(x => x.key === key);
  const body = {mod: s.mod, key, action, values: action === 'install' ? sxValues(a) : {}};
  let p;
  try{ p = await api.post('/api/scripts/addon/plan', body); }catch(e){ p = {error: errText(e)}; }
  if(p.error){ toast('✗ ' + p.error, 8000); return; }
  if(!confirm(tt('scripts.confirm',{words:(p.words || []).join('\n')}))) return;
  let r;
  try{ r = await api.post('/api/scripts/addon/apply', body); }catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  state.sx = null; loadScripts();
}

/* ---- the builder ---- */
function sxPart(list, key){ return list.find(p => p.key === key); }

function sxFieldHtml(group, i, f, it){
  const v = vx => vx === undefined || vx === null ? '' : vx;
  const val = it[f.name], s = state.sx, voc = s.vocab;
  // each box says where its value goes (data-g/-i/-n) and sxSetEl reads it from there
  const at = `data-g="${group}" data-i="${i}" data-n="${esc(f.name)}"`;
  const sel = (pairs) => `<select ${at} onchange="sxSetEl(this)">${pairs.map(([k, l]) => `<option value="${esc(k)}" ${String(val) === String(k) ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select>`;
  const wide = f.kind.startsWith('cond') || f.kind.startsWith('cmd');
  let box;
  if(f.kind === 'op' || f.kind === 'turn_op') box = sel(voc.ops);
  else if(f.kind === 'who') box = sel(voc.who);
  else if(f.kind === 'to') box = sel(voc.to);
  else if(f.kind === 'stance') box = sel(voc.stances);
  else if(f.kind.startsWith('names:')) box = `<input ${at} onchange="sxSetEl(this)" data-list="1" value="${esc(Array.isArray(val) ? val.join(', ') : v(val))}" placeholder="${ttA('scripts.comma_list')}">`;
  else if(f.kind === 'long') box = `<textarea ${at} onchange="sxSetEl(this)" rows="2">${esc(v(val))}</textarea>`;
  else if(['int', 'signed', 'percent'].includes(f.kind)) box = `<input type="number" ${at} onchange="sxSetEl(this)" value="${esc(v(val))}" style="width:90px">`;
  else box = `<input ${at} onchange="sxSetEl(this)" value="${esc(v(val))}" class="${wide ? 'sxwide' : ''}">`;
  return `<span class="sxfield">${f.label ? `<span class="count">${esc(f.label)}</span>` : ''}${box}</span>`;
}

function sxItemsHtml(group, list, items){
  return `${items.map((it, i) => { const p = sxPart(list, it.k);
    return `<div class="sxitem"><select onchange="sxKind('${group}',${i},this.value)">${list.map(x =>
      `<option value="${esc(x.key)}" ${x.key === it.k ? 'selected' : ''}>${esc(x.label)}</option>`).join('')}</select>
      ${p ? p.fields.map(f => sxFieldHtml(group, i, f, it)).join('') : ''}
      <button class="mini" onclick="sxDrop('${group}',${i})">✕</button>
      ${p && p.help ? `<div class="count">${esc(p.help)}</div>` : ''}</div>`; }).join('')}
    <button class="mini" onclick="sxAddItem('${group}')">${tt('scripts.add_line')}</button>`;
}

function sxBuilderHtml(){
  const s = state.sx, r = s.recipe, voc = s.vocab, pv = s.pv;
  const opt = (pairs, cur) => pairs.map(([k, l]) => `<option value="${esc(k)}" ${k === cur ? 'selected' : ''}>${esc(l)}</option>`).join('');
  const ev = voc.events.find(e => e.key === r.when);
  return `<div class="bsec">
    <div class="sxrow"><span class="count">${tt('scripts.start_from')}</span>
      <select onchange="sxExample(this.value)"><option value="">${tt('scripts.blank')}</option>${voc.examples.map(x =>
        `<option value="${esc(x.title)}">${esc(x.label)}</option>`).join('')}</select>
      <input value="${esc(r.title)}" oninput="state.sx.recipe.title=this.value;state.sx.pv=null" style="min-width:240px">
      <span class="hxtabs sxview">${['form', 'blocks'].map(v => `<button class="${(s.view || 'form') === v ? 'on' : ''}"
        onclick="state.sx.view='${v}';renderScripts()">${v === 'form' ? tt('scripts.view_form') : tt('scripts.view_blocks')}</button>`).join('')}</span></div>
    ${s.view === 'blocks' ? sxBlocksHtml() : `
    <h4>${tt('scripts.when')}</h4>
    <div class="sxrow"><select onchange="state.sx.recipe.when=this.value;state.sx.pv=null;renderScripts()">${voc.events.map(e =>
      `<option value="${esc(e.key)}" ${e.key === r.when ? 'selected' : ''}>${esc(e.label)}</option>`).join('')}</select>
      <label class="chk"><input type="checkbox" ${r.once ? 'checked' : ''} onchange="state.sx.recipe.once=this.checked;state.sx.pv=null"> ${tt('scripts.once')}</label></div>
    ${ev ? `<div class="count">${esc(ev.help)}</div>` : ''}
    <h4>${tt('scripts.if')} <select onchange="state.sx.recipe.match=this.value;state.sx.pv=null">${opt(voc.match, r.match)}</select></h4>
    ${sxItemsHtml('ifs', voc.conditions, r.ifs)}
    <h4>${tt('scripts.do')} <select onchange="state.sx.recipe.each=this.value;state.sx.pv=null;renderScripts()">${opt(voc.each, r.each)}</select>
      ${r.each ? `<select onchange="state.sx.recipe.each_of=this.value;state.sx.pv=null;renderScripts()">${opt(voc.each_of, r.each_of)}</select>
        ${r.each_of === 'named' ? `<input value="${esc(r.each_faction || '')}" oninput="state.sx.recipe.each_faction=this.value">` : ''}` : ''}</h4>
    ${sxItemsHtml('dos', voc.actions, r.dos)}
    <h4>${tt('scripts.else')}</h4>
    ${sxItemsHtml('else', voc.actions, r.else || [])}`}
    <div class="sxbtns"><button onclick="sxPreview()">${tt('scripts.read_back')}</button>
      ${pv && !(pv.problems || []).length ? `<button class="primary" onclick="sxSave()">${tt('scripts.save')}</button>` : ''}</div>
    ${pv ? `<div class="sxwords"><b>${esc(pv.words)}</b></div>
      ${(pv.problems || []).map(x => `<div class="w-bad">✗ ${esc(x)}</div>`).join('')}
      ${pv.script ? `<details><summary class="count">${tt('scripts.the_script')}</summary><pre class="hxpre">${esc(pv.script)}</pre></details>` : ''}` : ''}
  </div>
  ${s.mine.length ? `<div class="bsec"><h4>${tt('scripts.mine')}</h4>${s.mine.map(m =>
    `<div class="sxrow"><button class="mini" onclick="sxOpenMine('${q1(esc(m.key))}')">${esc(m.title)}</button></div>`).join('')}</div>` : ''}`;
}

function sxSetEl(el){ sxSet(el.dataset.g, +el.dataset.i, el.dataset.n, el); }
function sxSet(group, i, name, el){
  const it = state.sx.recipe[group][i];
  it[name] = el.dataset.list ? el.value.split(',').map(x => x.trim()).filter(Boolean)
    : el.type === 'number' ? (el.value === '' ? '' : +el.value) : el.value;
  state.sx.pv = null;
}
function sxKind(group, i, key){
  const list = group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions;
  const p = sxPart(list, key), it = {k: key};
  (p.fields || []).forEach(f => { it[f.name] = f['default']; });
  state.sx.recipe[group][i] = it; state.sx.pv = null; renderScripts();
}
function sxAddItem(group){
  const list = group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions;
  state.sx.recipe[group] = state.sx.recipe[group] || [];
  state.sx.recipe[group].push({k: list[0].key});
  sxKind(group, state.sx.recipe[group].length - 1, list[0].key);
}
function sxDrop(group, i){ state.sx.recipe[group].splice(i, 1); state.sx.pv = null; renderScripts(); }

async function sxExample(title){
  const s = state.sx;
  if(!title) return;
  let r;
  try{ r = await api.post('/api/scripts/example', {mod: s.mod, title}); }catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  s.recipe = r.recipe; s.pv = null; renderScripts();
}
function sxOpenMine(key){
  const m = state.sx.mine.find(x => x.key === key);
  if(m){ state.sx.recipe = JSON.parse(JSON.stringify(m.recipe)); state.sx.pv = null; renderScripts(); }
}
async function sxPreview(){
  const s = state.sx;
  let r;
  try{ r = await api.post('/api/scripts/preview', {mod: s.mod, recipe: s.recipe}); }catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 6000); return; }
  s.pv = r; renderScripts();
}
async function sxSave(){
  const s = state.sx;
  let r;
  try{ r = await api.post('/api/scripts/save', {mod: s.mod, recipe: s.recipe}); }catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('scripts.saved',{title:r.title}), 6000);
  const keep = s.recipe; state.sx = null; await loadScripts(); state.sx.recipe = keep; state.sx.tab = 'addons'; renderScripts();
}

/* ---- 96f: the campaign script by pieces ----
   campaign_script.txt listed as its top-level pieces - each monitor, loop,
   if block, counter and command, with the comment above it - and any taken
   out: the ticked ones, or every one the filter shows. The frame (script,
   wait_monitors, end_script) is never offered. The save goes through the raw
   editor's writer, so it is byte-exact elsewhere, refused if the file changed
   since it was read, and undone from the Log. */
const SX_CS_ROWS = 500;
async function sxCsLoad(campaign){
  const s = state.sx;
  s.cs = {campaign: campaign === undefined ? ((s.cs && s.cs.campaign) || '') : campaign,
          d: null, picked: new Set(), filter: '', busy: false};
  renderScripts();
  let d;
  try{ d = await api.get(`/api/campscript?mod=${enc(s.mod)}&campaign=${enc(s.cs.campaign)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.sx !== s) return;
  s.cs.d = d;
  if(!s.cs.campaign && d.campaign) s.cs.campaign = d.campaign;
  renderScripts();
}
function sxCsShown(){
  const c = state.sx.cs, q = c.filter.trim().toLowerCase();
  return c.d.pieces.filter(p => !p.frame && (!q || p.head.toLowerCase().includes(q)
    || p.kind.includes(q) || (p.comment || '').toLowerCase().includes(q)));
}
function sxCsListHtml(){
  const c = state.sx.cs, rows = sxCsShown();
  return `<div class="count">${tt('scripts.cs_shown',{n: rows.length, of: c.d.pieces.filter(p => !p.frame).length, picked: c.picked.size})}</div>
    ${rows.slice(0, SX_CS_ROWS).map(p => `<div class="sxcsrow"><label class="chk" title="${esc(tt('scripts.cs_lines',{a: p.start + 1, b: p.end + 1}))}">
      <input type="checkbox" ${c.picked.has(p.n) ? 'checked' : ''} onchange="sxCsPick(${p.n}, this.checked)">
      <span class="badge">${esc(p.kind)}</span> <code>${esc(p.head)}</code>
      <span class="count">${ttN('scripts.cs_n_lines', p.lines)}${p.comment ? ` · ${esc(p.comment)}` : ''}</span></label></div>`).join('')}
    ${rows.length > SX_CS_ROWS ? `<div class="count">${tt('scripts.cs_more',{n: rows.length - SX_CS_ROWS})}</div>` : ''}`;
}
function sxCsHtml(){
  const s = state.sx, c = s.cs;
  if(!c){ queueMicrotask(() => sxCsLoad()); return `<div class="empty">${tt('common.reading')}</div>`; }
  if(!c.d) return `<div class="empty">${tt('common.reading')}</div>`;
  const d = c.d;
  const camps = (d.campaigns || []).length > 1 ? `<select onchange="sxCsLoad(this.value)">${d.campaigns.map(x =>
    `<option value="${esc(x)}" ${x === c.campaign ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select>` : '';
  if(d.error || d.problem) return `<div class="bsec">${camps}<div class="w-bad">✗ ${esc(d.error || d.problem)}</div></div>`;
  if(d.readonly) return `<div class="bsec">${camps}<div class="w-warn">${esc(d.readonly)}</div></div>`;
  return `<div class="bsec sxcs">
    <div class="trnote">${tt('scripts.cs_head',{rel: esc(d.rel), lines: d.lines})}</div>
    ${(d.warnings || []).map(w => `<div class="trfind w-warn">${esc(w)}</div>`).join('')}
    <div class="brow">${camps}
      <input placeholder="${ttA('scripts.cs_filter')}" value="${esc(c.filter)}" oninput="sxCsFilter(this.value)">
      <button onclick="sxCsTake(false)" ${c.busy ? 'disabled' : ''}>${tt('scripts.cs_take_picked')}</button>
      <button onclick="sxCsTake(true)" ${c.busy ? 'disabled' : ''}>${tt('scripts.cs_take_shown')}</button>
      <button onclick="state.sx.cs.picked.clear();sxCsPaintList()">${tt('scripts.cs_clear')}</button>
    </div>
    <div id="sxCsList" class="sxcslist">${sxCsListHtml()}</div>
  </div>`;
}
//: the filter repaints only the list, so the caret stays in the box
function sxCsFilter(v){ state.sx.cs.filter = v; sxCsPaintList(); }
function sxCsPaintList(){ const el = document.getElementById('sxCsList'); if(el) el.innerHTML = sxCsListHtml(); }
function sxCsPick(n, on){ const p = state.sx.cs.picked; on ? p.add(n) : p.delete(n); sxCsPaintList(); }
async function sxCsTake(shown){
  const s = state.sx, c = s.cs;
  const drop = shown ? sxCsShown().map(p => p.n) : [...c.picked];
  if(!drop.length){ toast(tt('scripts.cs_none')); return; }
  const body = {mod: s.mod, campaign: c.campaign, sig: c.d.sig, drop};
  c.busy = true;
  let r;
  try{ r = await api.post('/api/campscript/plan', body); }catch(e){ r = {error: errText(e)}; }
  c.busy = false;
  if(r.error){ toast('✗ ' + r.error, 7000); return; }
  const p = r.plan || {};
  if(!confirm(tt('scripts.cs_confirm',{n: drop.length, changes: (p.changes || []).join('\n'),
    warnings: (p.warnings || []).slice(0, 4).join('\n')}))) return;
  c.busy = true;
  try{ r = await api.post('/api/campscript/apply', body); }catch(e){ r = {error: errText(e)}; }
  c.busy = false;
  if(r.error){ toast('✗ ' + r.error, 7000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  sxCsLoad(c.campaign);
}
