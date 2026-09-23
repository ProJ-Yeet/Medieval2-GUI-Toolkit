/* settlemech.js - Settlement mechanics: descr_settlement_mechanics.xml

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= SETTLEMENT MECHANICS (59) =======================
   How a settlement grows, keeps order and pays: one factor a row, each with
   its pip modifier, its city and castle modifiers and its min and max clamp,
   and the two population ladders underneath. A factor that lacks a modifier
   shows an empty box - typing in it adds the line, and clearing a box that
   has one takes it out (the pip modifier cannot be taken out).

   THE PAGE NEVER PARSES A GAME FILE. Everything here is /api/settlemech and
   /api/settlemech/plan|apply - campdb.js's shape. */

const SMX_KIDS = [['pip_modifier', 'pip'], ['city_modifier', 'city ×'], ['castle_modifier', 'castle ×'],
                  ['pip_min', 'min'], ['pip_max', 'max']];
const SMX_LEVEL = ['base', 'upgrade', 'min', 'max'];

async function loadSettleMech(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s settlement mechanics…</div>';
  let r;
  try{ r = await api.get('/api/settlemech?mod=' + enc(mod)); }
  catch(e){ if(stale('settlemech', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read the settlement mechanics.<br>
      <span class="count">${esc(errText(e))}</span><br>
      <span class="count">They live in data/descr_settlement_mechanics.xml</span><br><br>
      <button class="primary" onclick="loadSettleMech()">Retry</button></div>`; return; }
  if(stale('settlemech', mod)) return;
  const keep = state.smx && state.smx.mod === mod ? state.smx.sel : '';
  state.smx = Object.assign({mod, sel: keep || 'SPF', w: {}, busy: false}, r);
  renderSettleMech();
}

/* every value on the page, as key -> the file's value ('' when absent) */
function smxFileValues(){
  const c = state.smx, out = {};
  c.families.forEach(f => f.factors.forEach(x => SMX_KIDS.forEach(([k]) => {
    out[`factor/${x.name}/${k}`] = x.values[k] !== undefined ? x.values[k] : ''; })));
  c.levels.forEach(l => l.levels.forEach(x => SMX_LEVEL.forEach(k => {
    if(x.values[k] !== undefined) out[`level/${x.name}/${k}`] = x.values[k]; })));
  return out;
}
function smxVal(key){
  const w = state.smx.w;
  return Object.prototype.hasOwnProperty.call(w, key) ? w[key] : (smxFileValues()[key] || '');
}
function smxChanged(){ return Object.keys(state.smx.w).length; }
function smxBad(key, v){
  const s = String(v).trim();
  if(s === '') return false;
  return key.startsWith('level/') ? !/^\d+$/.test(s) : !/^-?(\d+(\.\d*)?|\.\d+)$/.test(s);
}

function renderSettleMech(){
  const c = state.smx;
  if(!c){ loadSettleMech(); return; }
  const q = search.value.trim().toLowerCase();
  const strip = minorTabsHtml('', 'data/' + (c.file || 'descr_settlement_mechanics.xml'));
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key || ''}));
  const tabs = c.families.map(f => ({id: f.id, label: f.label, n: f.factors.length,
      hit: q ? f.factors.filter(x => x.name.toLowerCase().includes(q)).length : 0}))
    .concat([{id: 'levels', label: 'Population levels',
              n: c.levels.reduce((n, l) => n + l.levels.length, 0), hit: 0}]);
  const total = c.families.reduce((n, f) => n + f.factors.length, 0);
  count.textContent = `${total}`;
  const edits = k => Object.keys(c.w).filter(x => k === 'levels' ? x.startsWith('level/')
    : x.startsWith(`factor/${k}_`)).length;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('settlemech', find, 'smxOpen')}
      <div class="trrows">${tabs.map(t => `<button class="trrow${(!q && c.sel === t.id) ? ' on' : ''}"
          onclick="smxSection('${q1(esc(t.id))}')">
        <div class="nm">${esc(t.label)}</div>
        <div class="sub">${q ? `${t.hit} match` : `${t.n} ${t.id === 'levels' ? 'levels' : 'factors'}`}${
          edits(t.id) ? ` · <b>${edits(t.id)} changed</b>` : ''}</div></button>`).join('')}</div>
    </div>
    <div class="trmain" id="smxMain">${smxMainHtml(q)}</div>
  </div>`;
}

function smxMainHtml(q){
  const c = state.smx, n = smxChanged();
  const head = `<div class="cdbhead">
    <div><b>descr_settlement_mechanics.xml</b> <span class="count">growth, public order, income and
      mines for every settlement, and how many people each level holds</span></div>
    <span style="flex:1"></span>
    <button onclick="smxRevert()" id="smxRevert" ${n ? '' : 'disabled'}>Revert</button>
    <button class="primary" onclick="smxSave()" id="smxSave" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
  </div>`;
  const fams = q ? c.families : c.families.filter(f => f.id === c.sel);
  let body = fams.map(f => {
    const rows = f.factors.filter(x => !q || x.name.toLowerCase().includes(q));
    if(!rows.length) return '';
    return `<div class="cdbsec"><h3>${esc(f.label)} <span class="count">${esc(f.id)}_</span></h3>
      <table class="smxtab"><tr><th></th>${SMX_KIDS.map(([, l]) => `<th>${esc(l)}</th>`).join('')}</tr>
      ${rows.map(x => `<tr id="smx_${esc(x.name)}"><td><code title="line ${x.line}">${esc(x.name)}</code></td>${
        SMX_KIDS.map(([k]) => smxBox(`factor/${x.name}/${k}`, x.values[k])).join('')}</tr>`).join('')}
      </table></div>`;
  }).join('');
  if(!q && c.sel === 'levels'){
    body = c.levels.map(l => `<div class="cdbsec"><h3>${l.ladder === 'city' ? 'Cities' : 'Castles'}</h3>
      <table class="smxtab"><tr><th></th>${SMX_LEVEL.map(k => `<th>${k}</th>`).join('')}</tr>
      ${l.levels.map(x => `<tr id="smx_${esc(x.name)}"><td><code title="line ${x.line}">${esc(x.name)}</code></td>${
        SMX_LEVEL.map(k => x.values[k] === undefined ? '<td class="count">-</td>'
          : smxBox(`level/${x.name}/${k}`, x.values[k])).join('')}</tr>`).join('')}
      </table>
      <div class="count">A level's <b>upgrade</b> is the population it grows into the next level at;
        above its <b>max</b> it is never reached. Both installed mods set each upgrade to the next
        level's base.</div></div>`).join('');
  }
  return head + (body || '<div class="count" style="padding:8px">No factor matches.</div>');
}

function smxBox(key, fileVal){
  const v = smxVal(key), had = fileVal !== undefined, ch = Object.prototype.hasOwnProperty.call(state.smx.w, key);
  const pip = key.endsWith('/pip_modifier');
  return `<td class="${ch ? 'on' : ''}"><input type="text" value="${esc(v)}" spellcheck="false"
      class="${smxBad(key, v) ? 'bad' : ''}" placeholder="${had ? '' : '·'}"
      title="${had ? (pip ? 'the factor\'s own weight' : 'clear it to take the line out') : 'type a value to add this line'}"
      oninput="smxSet('${q1(esc(key))}', this.value, this, ${had ? 1 : 0}, '${q1(esc(fileVal || ''))}')"></td>`;
}

/* repaint in place, as campdb does: a redraw would take the caret away */
function smxSet(key, value, el, had, fileVal){
  const c = state.smx;
  const same = had ? value.trim() === fileVal : value.trim() === '';
  if(same) delete c.w[key]; else c.w[key] = value;
  const td = el.closest('td');
  if(td) td.classList.toggle('on', !same);
  el.classList.toggle('bad', smxBad(key, value) || (key.endsWith('/pip_modifier') && had && !value.trim()));
  const n = smxChanged(), s = document.getElementById('smxSave'), r = document.getElementById('smxRevert');
  if(s){ s.disabled = !n; s.textContent = `Save ${n || ''} change${n === 1 ? '' : 's'}`; }
  if(r) r.disabled = !n;
}

function smxSection(id){
  state.smx.sel = id;
  if(search.value) search.value = '';
  renderSettleMech();
}

/* a finding names `factor/NAME/...` or `level/NAME/...` */
function smxOpen(key){
  const [kind, name] = String(key).split('/');
  if(kind === 'level') smxSection('levels');
  else if(name) smxSection(name.split('_')[0]);
  const el = document.getElementById('smx_' + name);
  if(el){ el.scrollIntoView({block: 'center'}); el.classList.add('flash');
    setTimeout(() => el.classList.remove('flash'), 1200); }
}

function smxRevert(){ state.smx.w = {}; renderSettleMech(); }

async function smxSave(){
  const c = state.smx;
  if(c.busy) return;
  const body = {mod: state.src, values: Object.assign({}, c.w)};
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/settlemech/plan', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write ${(p.changes || []).length} change(s) to descr_settlement_mechanics.xml?\n\n`
    + (p.changes || []).slice(0, 16).join('\n')
    + ((p.changes || []).length > 16 ? `\n…and ${p.changes.length - 16} more` : '')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 4).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  c.busy = true;
  let res;
  try{ res = await api.post('/api/settlemech/apply', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ c.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadSettleMech();
}
