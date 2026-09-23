/* factionsites.js - Populace and off-map models: descr_lbc_db.txt and
   descr_offmap_models.txt

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =================== POPULACE AND OFF-MAP MODELS (63) ===================
   Two small files a faction is written into and nothing here edited. The
   populace is a list of townsfolk models and shares per faction, and the
   shares add up to 100 in every block of both installed mods, so the total
   is shown as it is typed. The off-map file is three braced sections - navy
   by faction, settlement and port by culture and level - shown as the tree
   it is, each row's values in boxes.

   THE PAGE NEVER PARSES A GAME FILE: /api/factionsites and its plan|apply. */

async function loadFactionSites(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s populace and off-map models…</div>';
  let r;
  try{ r = await api.get('/api/factionsites?mod=' + enc(mod)); }
  catch(e){ if(stale('factionsites', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read them.<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadFactionSites()">Retry</button></div>`; return; }
  if(stale('factionsites', mod)) return;
  const keep = state.fsx && state.fsx.mod === mod ? state.fsx : null;
  state.fsx = Object.assign({mod, tab: keep ? keep.tab : 'lbc', sel: keep ? keep.sel : '',
                             w: fsxBlank(), busy: false}, r);
  renderFactionSites();
}
function fsxBlank(){ return {lbc: {}, rows: {}, add: [], remove: []}; }

function fsxChanged(){
  const w = state.fsx.w;
  return Object.keys(w.lbc).length + Object.keys(w.rows).length + w.add.length + w.remove.length;
}

function renderFactionSites(){
  const c = state.fsx;
  if(!c){ loadFactionSites(); return; }
  const strip = minorTabsHtml('', 'data/' + (c.tab === 'lbc' ? 'descr_lbc_db.txt' : 'descr_offmap_models.txt'));
  const find = (c.findings || []).filter(f => c.tab === 'lbc' ? f.key.startsWith('lbc/') : f.key.startsWith('offmap/'))
    .map(f => Object.assign({}, f, {name: f.key}));
  const n = fsxChanged();
  const lbc = c.lbc || [], off = c.offmap || [];
  const left = c.tab === 'lbc'
    ? lbc.map(p => {
        const rows = fsxRows(p.faction);
        const tot = rows.reduce((s, r) => s + (+r[1] || 0), 0);
        return `<button class="trrow${c.sel === p.faction ? ' on' : ''}" onclick="fsxPick('${q1(esc(p.faction))}')">
          <div class="nm">${esc(p.faction)}${(c.roster || []).includes(p.faction) ? '' : ' <span class="count">not in the roster</span>'}</div>
          <div class="sub">${rows.length} model(s) · <span class="${tot === 100 ? '' : 'w-warn'}">${tot}%</span>${
            c.w.lbc[p.faction] !== undefined ? ' · <b>changed</b>' : ''}</div></button>`;
      }).join('') + fsxAddLbcHtml()
    : off.filter(b => b.depth === 0).map(b => `<button class="trrow${c.sel === b.path ? ' on' : ''}"
          onclick="fsxPick('${q1(esc(b.path))}')"><div class="nm">${esc(b.path)}</div>
          <div class="sub">${off.filter(x => x.path.startsWith(b.path + '/') && x.depth === 1).length} block(s)</div></button>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <div class="fsxtabs">
        <button class="${c.tab === 'lbc' ? 'on' : ''}" onclick="fsxTab('lbc')">Populace</button>
        <button class="${c.tab === 'offmap' ? 'on' : ''}" onclick="fsxTab('offmap')">Off-map models</button>
      </div>
      ${findingsHtml('factionsites', find, 'fsxOpen')}
      <div class="trrows">${left || `<div class="count" style="padding:8px">${esc(c.tab === 'lbc'
        ? (c.lbc_error || 'No populace blocks.') : (c.offmap_error || 'No sections.'))}</div>`}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>${c.tab === 'lbc' ? 'descr_lbc_db.txt' : 'descr_offmap_models.txt'}</b>
        <span class="count">${c.tab === 'lbc'
          ? 'the townsfolk a faction\'s settlements are drawn with, and how many of each'
          : 'a faction\'s fleets, and a culture\'s settlements and ports, off the map'}</span></div>
        <span style="flex:1"></span>
        <button onclick="fsxRevert()" ${n ? '' : 'disabled'}>Revert</button>
        <button class="primary" onclick="fsxSave()" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
      </div>
      ${c.tab === 'lbc' ? fsxLbcHtml() : fsxOffHtml()}
    </div>
  </div>`;
}

function fsxTab(t){ state.fsx.tab = t; state.fsx.sel = ''; renderFactionSites(); }
function fsxPick(s){ state.fsx.sel = s; renderFactionSites(); }
function fsxOpen(key){
  const k = String(key);
  if(k.startsWith('lbc/')){ state.fsx.tab = 'lbc'; state.fsx.sel = k.slice(4); }
  else { state.fsx.tab = 'offmap'; state.fsx.sel = k.slice(7).split('/')[0]; }
  renderFactionSites();
}
function fsxRevert(){ state.fsx.w = fsxBlank(); renderFactionSites(); }

/* ---- populace ---- */
function fsxRows(fac){
  const w = state.fsx.w.lbc;
  if(w[fac] !== undefined) return w[fac] || [];
  const p = (state.fsx.lbc || []).find(x => x.faction === fac);
  return p ? p.models.map(m => [m.model, m.share]) : [];
}
function fsxLbcHtml(){
  const c = state.fsx, fac = c.sel;
  if(!fac) return '<div class="count" style="padding:8px">Pick a faction.</div>';
  if(c.w.lbc[fac] === null) return `<div class="count" style="padding:8px">${esc(fac)}'s populace is taken out on save.
    <button onclick="fsxUndrop('${q1(esc(fac))}')">Keep it</button></div>`;
  const rows = fsxRows(fac), tot = rows.reduce((s, r) => s + (+r[1] || 0), 0);
  return `<div class="cdbsec"><h3>${esc(fac)} <span class="${tot === 100 ? 'count' : 'w-warn'}">${tot}% of 100</span></h3>
    <table class="smxtab"><tr><th>model</th><th>share</th><th></th></tr>
    ${rows.map((r, i) => `<tr><td><input style="width:220px" value="${esc(r[0])}" onchange="fsxLbcSet(${i}, 0, this.value)"></td>
      <td><input value="${esc(r[1])}" onchange="fsxLbcSet(${i}, 1, this.value)"></td>
      <td><button onclick="fsxLbcDrop(${i})">✕</button></td></tr>`).join('')}
    </table>
    <button onclick="fsxLbcAdd()">＋ a model</button>
    <button onclick="fsxLbcRemove()" title="Take this faction's populace block out">Remove ${esc(fac)}'s populace</button>
    <div class="count">Both installed mods give every faction shares that add up to exactly 100.
      The model names are peasants from the base game's own packed models, so they are not checked here.</div></div>`;
}
function fsxLbcEdit(fn){
  const c = state.fsx, fac = c.sel;
  const rows = fsxRows(fac).map(r => r.slice());
  fn(rows);
  c.w.lbc[fac] = rows;
  renderFactionSites();
}
function fsxLbcSet(i, k, v){ fsxLbcEdit(rows => { rows[i][k] = v.trim(); }); }
function fsxLbcDrop(i){ fsxLbcEdit(rows => rows.splice(i, 1)); }
function fsxLbcAdd(){ fsxLbcEdit(rows => rows.push(['', '0'])); }
function fsxLbcRemove(){ state.fsx.w.lbc[state.fsx.sel] = null; renderFactionSites(); }
function fsxUndrop(fac){ delete state.fsx.w.lbc[fac]; renderFactionSites(); }
function fsxAddLbcHtml(){
  const c = state.fsx, have = new Set((c.lbc || []).map(p => p.faction).concat(Object.keys(c.w.lbc)));
  const missing = (c.roster || []).filter(f => !have.has(f));
  if(!missing.length || !(c.lbc || []).length) return '';
  return `<div class="trnote">In the roster with no populace block:
    <select id="fsxNewFac">${missing.map(f => `<option>${esc(f)}</option>`).join('')}</select>
    copied from <select id="fsxLike">${(c.lbc || []).map(p => `<option>${esc(p.faction)}</option>`).join('')}</select>
    <button onclick="fsxLbcNew()">＋ Add</button></div>`;
}
function fsxLbcNew(){
  const fac = document.getElementById('fsxNewFac').value, like = document.getElementById('fsxLike').value;
  state.fsx.w.lbc[fac] = fsxRows(like).map(r => r.slice());
  state.fsx.lbc.push({faction: fac, line: 0, models: []});
  state.fsx.sel = fac;
  renderFactionSites();
}

/* ---- off-map ---- */
function fsxOffHtml(){
  const c = state.fsx, sec = c.sel, off = c.offmap || [];
  if(!sec) return '<div class="count" style="padding:8px">Pick a section.</div>';
  const blocks = off.filter(b => b.path.startsWith(sec + '/'));
  const facs = blocks.filter(b => b.depth === 1 && b.kind === 'faction').map(b => b.head[1]);
  const gone = new Set(c.w.remove.filter(r => r.section === sec).map(r => r.faction));
  const body = blocks.map(b => {
    const drop = b.depth === 1 && b.kind === 'faction' && gone.has(b.head[1]);
    return `<div class="fsxblk" style="margin-left:${(b.depth - 1) * 16}px">
      <div class="nm"><code>${esc(b.head.join(' '))}</code> <span class="count">line ${b.line}</span>
        ${b.depth === 1 && b.kind === 'faction' ? `<button onclick="fsxOffRemove('${q1(esc(sec))}','${q1(esc(b.head[1]))}')">${drop ? 'keep' : '✕'}</button>` : ''}</div>
      ${drop ? '<div class="count">taken out on save</div>' : b.rows.map(r => `<div class="fsxrow">${
        (c.w.rows[r.line] || r.tokens).map((t, k) => `<input value="${esc(t)}" style="width:${k === (r.tokens.length > 3 ? 1 : 0) ? 330 : 70}px"
          onchange="fsxRowSet(${r.line}, ${k}, this.value)">`).join('')}</div>`).join('')}
    </div>`;
  }).join('');
  const add = facs.length ? `<div class="trnote">Add a faction to ${esc(sec)}:
    <input id="fsxOffFac" placeholder="slot" style="width:120px"> copied from
    <select id="fsxOffLike">${facs.map(f => `<option>${esc(f)}</option>`).join('')}</select>
    <button onclick="fsxOffAdd('${q1(esc(sec))}')">＋ Add</button>
    ${c.w.add.filter(a => a.section === sec).map(a => `<div class="count">+ ${esc(a.faction)} (from ${esc(a.like)}) on save</div>`).join('')}</div>` : '';
  return `<div class="cdbsec">${add}${body}</div>`;
}
function fsxRowSet(line, k, v){
  const c = state.fsx;
  const row = c.offmap.flatMap(b => b.rows).find(r => r.line === line);
  const cur = (c.w.rows[line] || row.tokens).slice();
  cur[k] = v.trim();
  if(cur.join(' ') === row.tokens.join(' ')) delete c.w.rows[line]; else c.w.rows[line] = cur;
  renderFactionSites();
}
function fsxOffAdd(sec){
  const fac = (document.getElementById('fsxOffFac').value || '').trim().toLowerCase();
  const like = document.getElementById('fsxOffLike').value;
  if(!fac) return;
  state.fsx.w.add.push({section: sec, faction: fac, like});
  renderFactionSites();
}
function fsxOffRemove(sec, fac){
  const w = state.fsx.w, i = w.remove.findIndex(r => r.section === sec && r.faction === fac);
  if(i >= 0) w.remove.splice(i, 1); else w.remove.push({section: sec, faction: fac});
  renderFactionSites();
}

async function fsxSave(){
  const c = state.fsx;
  if(c.busy) return;
  const body = {mod: state.src, offmap_sig: c.offmap_sig || ''};
  if(Object.keys(c.w.lbc).length) body.lbc = c.w.lbc;
  if(Object.keys(c.w.rows).length || c.w.add.length || c.w.remove.length)
    body.offmap = {rows: c.w.rows, add: c.w.add, remove: c.w.remove};
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/factionsites/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write ${(p.changes || []).length} change(s)?\n\n` + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  let res;
  try{ res = await api.post('/api/factionsites/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadFactionSites();
}
