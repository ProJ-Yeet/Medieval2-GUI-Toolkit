/* campdb.js - Campaign constants: descr_campaign_db.xml

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= CAMPAIGN CONSTANTS (38) =======================
   Every number the engine reads once for the whole campaign, 18 sections and
   two to three hundred tags. Nothing here knows the tag names: the file writes
   each value as `<name type="value"/>`, so the box a row gets - a tick for a
   bool, a number for the rest - comes off the file, and a tag no mod we have
   seen writes still gets the right one.

   What the page does know is the few tags the archive explains - the fort
   switches, the Britannia piety mode, the ransom chances - and it says so under
   the row, with the document it came from. A documented tag the mod does not
   write is offered as a button, with the value the document prints.

   THE PAGE NEVER PARSES A GAME FILE. Everything here is /api/campdb and
   /api/campdb/plan|apply. */

async function loadCampDb(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s campaign constants…</div>';
  let r;
  try{ r = await api.get('/api/campdb?mod=' + enc(mod)); }
  catch(e){ if(stale('campdb', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read the campaign constants.<br>
      <span class="count">${esc(errText(e))}</span><br>
      <span class="count">They live in data/descr_campaign_db.xml</span><br><br>
      <button class="primary" onclick="loadCampDb()">Retry</button></div>`; return; }
  if(stale('campdb', mod)) return;
  const keep = state.cdb && state.cdb.mod === mod ? state.cdb.sel : '';
  state.cdb = Object.assign({mod, sel:'', w:{}, add:[], busy:false}, r);
  if(!r.sections.some(s => s.name === keep)) state.cdb.sel = (r.sections[0] || {}).name || '';
  else state.cdb.sel = keep;
  renderCampDb();
}

/* the tag rows a section shows, after the search box */
function cdbItems(sec){
  const q = search.value.trim().toLowerCase();
  if(!q) return sec.items;
  return sec.items.filter(it => it.kind === 'tag' && (
    it.name.toLowerCase().includes(q) || (it.note||'').toLowerCase().includes(q)
    || ((it.vocab||{}).doc||'').toLowerCase().includes(q)));
}

function cdbTags(){
  return state.cdb.sections.flatMap(s => s.items.filter(i => i.kind === 'tag'));
}

/* what a row holds now: the working value if one was typed, else the file's */
function cdbVal(it){
  const w = state.cdb.w;
  return Object.prototype.hasOwnProperty.call(w, it.key) ? w[it.key] : it.value;
}

function cdbChanged(){
  const c = state.cdb;
  return cdbTags().filter(t => cdbVal(t) !== t.value).length + c.add.length;
}

/* The server is the one that refuses; this only paints a box red early. */
function cdbBad(type, v){
  if(type === 'bool') return !/^(true|false)$/.test(v);
  if(type === 'uint') return !/^\d+$/.test(v);
  if(type === 'int') return !/^-?\d+$/.test(v);
  if(type === 'float') return !/^-?(\d+(\.\d*)?|\.\d+)$/.test(v);
  if(type === 'string') return /["<>&]/.test(v);
  return false;
}

function renderCampDb(){
  const c = state.cdb;
  if(!c){ loadCampDb(); return; }
  const q = search.value.trim();
  const secs = c.sections.map(s => ({s, rows:cdbItems(s)}))
    .filter(x => !q || x.rows.length);
  count.textContent = q ? `${secs.reduce((n,x)=>n+x.rows.length,0)}/${c.count}` : `${c.count}`;
  const strip = minorTabsHtml('', 'data/' + (c.file || 'descr_campaign_db.xml'));
  const find = (c.findings || []).map(f => Object.assign({}, f, {name:f.key || f.section || ''}));
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('campdb', find, 'cdbOpen')}
      <div class="trrows">${secs.map(({s, rows}) => {
        const n = s.items.filter(i => i.kind === 'tag').length;
        const ch = s.items.filter(i => i.kind === 'tag' && cdbVal(i) !== i.value).length
          + c.add.filter(a => (c.missing.find(m => m.name === a)||{}).section === s.name).length;
        const on = !q && c.sel === s.name;
        return `<button class="trrow${on?' on':''}" onclick="cdbSection('${q1(esc(s.name))}')">
          <div class="nm">${esc(s.name)}</div>
          <div class="sub">${q ? `${rows.length} of ${n} match` : `${n} tag${n===1?'':'s'}`}${
            ch ? ` · <b>${ch} changed</b>` : ''}</div></button>`;
      }).join('') || '<div class="count" style="padding:8px">No tag matches.</div>'}</div>
    </div>
    <div class="trmain" id="cdbMain">${cdbMainHtml(secs)}</div>
  </div>`;
}

function cdbMainHtml(secs){
  const c = state.cdb, q = search.value.trim();
  const shown = q ? secs : secs.filter(x => x.s.name === c.sel);
  const n = cdbChanged();
  const head = `<div class="cdbhead">
    <div><b>descr_campaign_db.xml</b> <span class="count">read once, when a campaign starts -
      a change reaches a NEW campaign, not a save</span></div>
    <span style="flex:1"></span>
    <button onclick="cdbRevert()" id="cdbRevert" ${n?'':'disabled'}>Revert</button>
    <button class="primary" onclick="cdbSave()" id="cdbSave" ${n?'':'disabled'}>Save ${n||''} change${n===1?'':'s'}</button>
  </div>`;
  return head + shown.map(({s, rows}) => {
    const missing = q ? [] : c.missing.filter(m => m.section === s.name);
    return `<div class="cdbsec">
      <h3>&lt;${esc(s.name)}&gt;</h3>
      ${missing.length ? `<div class="trnote cdbmiss">
        <div class="count">The archive documents ${missing.length === 1 ? 'a tag' : 'tags'} this file does not write:</div>
        ${missing.map(m => {
          const on = c.add.includes(m.name);
          return `<div class="cdbadd"><button class="${on?'on':''}" onclick="cdbAdd('${q1(esc(m.name))}')"
            >${on ? '✓ adding' : '＋ add'}</button> <code>${esc(m.name)}</code>
            <span class="cdbtype">${esc(m.type)}</span> = <code>${esc(m.default)}</code>
            <div class="count">${esc(m.doc)} <i>(${esc(m.source)})</i></div></div>`;
        }).join('')}
      </div>` : ''}
      ${rows.map(cdbRowHtml).join('')}
    </div>`;
  }).join('');
}

function cdbRowHtml(it){
  if(it.kind === 'note') return `<div class="cdbnote">${esc(it.text)}</div>`;
  const v = cdbVal(it), ch = v !== it.value, id = 'cdb_' + it.key.replace(/\W/g, '_');
  const box = it.type === 'bool'
    ? `<input type="checkbox" ${v === 'true' ? 'checked' : ''}
         onchange="cdbSet('${q1(esc(it.key))}', this.checked ? 'true' : 'false', this)">`
    : `<input type="text" value="${esc(v)}" spellcheck="false"
         class="${cdbBad(it.type, v) ? 'bad' : ''}"
         oninput="cdbSet('${q1(esc(it.key))}', this.value, this)">`;
  const doc = it.vocab ? `<div class="cdbdoc">${esc(it.vocab.doc)} <i>(${esc(it.vocab.source)})</i></div>` : '';
  return `<div class="cdbrow${ch ? ' on' : ''}" id="${id}">
    <code class="cdbname" title="line ${it.line}">${esc(it.name)}</code>
    <span class="cdbtype">${esc(it.type)}</span>
    <span class="cdbbox">${box}${ch ? `<span class="count" title="the value in the file">was ${esc(it.value)}</span>` : ''}</span>
    <span class="cdbwhy">${it.note ? esc(it.note) : ''}${doc}</span>
  </div>`;
}

/* Typing does not redraw - that would take the caret out of the box - so the
   row and the two buttons are repainted in place. */
function cdbSet(key, value, el){
  const c = state.cdb, it = cdbTags().find(t => t.key === key);
  if(!it) return;
  if(value === it.value) delete c.w[key]; else c.w[key] = value;
  const row = el.closest('.cdbrow');
  if(row) row.classList.toggle('on', value !== it.value);
  if(el.type === 'text') el.classList.toggle('bad', cdbBad(it.type, value));
  cdbPaintButtons();
}

function cdbPaintButtons(){
  const n = cdbChanged(), s = document.getElementById('cdbSave'),
        r = document.getElementById('cdbRevert');
  if(s){ s.disabled = !n; s.textContent = `Save ${n||''} change${n===1?'':'s'}`; }
  if(r) r.disabled = !n;
}

function cdbSection(name){
  state.cdb.sel = name;
  if(search.value){ search.value = ''; }
  renderCampDb();
}

/* a finding names `section/tag`, or a section */
function cdbOpen(key){
  const sec = String(key).split('/')[0];
  if(!state.cdb.sections.some(s => s.name === sec)) return;
  cdbSection(sec);
  const el = document.getElementById('cdb_' + String(key).replace(/\W/g, '_'));
  if(el){ el.scrollIntoView({block:'center'}); el.classList.add('flash');
    setTimeout(() => el.classList.remove('flash'), 1200); }
}

function cdbAdd(name){
  const a = state.cdb.add, i = a.indexOf(name);
  if(i >= 0) a.splice(i, 1); else a.push(name);
  renderCampDb();
}

function cdbRevert(){
  state.cdb.w = {}; state.cdb.add = [];
  renderCampDb();
}

async function cdbSave(){
  const c = state.cdb;
  if(c.busy) return;
  const body = {mod: state.src, values: Object.assign({}, c.w), add: c.add.slice()};
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/campdb/plan', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 16);
  if(!confirm(`Write ${(p.changes||[]).length} change(s) to descr_campaign_db.xml?\n\n`
    + lines.join('\n')
    + ((p.changes || []).length > 16 ? `\n…and ${p.changes.length - 16} more` : '')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 4).join('\n⚠ ') : '')
    + `\n\nIt is read when a campaign starts, so start a new one to see it.`
    + `\nBacked up first, and 🕑 Log can undo it.`)) return;
  c.busy = true;
  let res;
  try{ res = await api.post('/api/campdb/apply', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ c.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadCampDb();
}
