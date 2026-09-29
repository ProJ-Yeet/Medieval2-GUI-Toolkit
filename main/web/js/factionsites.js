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
  main.innerHTML = `<div class="empty">${tt('factionsites.reading_mod_populace_and_off_map_models',{mod:esc(mod)})}</div>`;
  let r;
  try{ r = await api.get('/api/factionsites?mod=' + enc(mod)); }
  catch(e){ if(stale('factionsites', mod)) return;
    main.innerHTML = `<div class="empty">${tt('common.couldnt_read_them')}<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadFactionSites()">${tt('common.retry')}</button></div>`; return; }
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
          <div class="nm">${esc(p.faction)}${(c.roster || []).includes(p.faction) ? '' : ` <span class="count">${tt('factionsites.not_in_the_roster')}</span>`}</div>
          <div class="sub">${tt('factionsites.model_s',{rows_n:rows.length,tot:tot === 100 ? '' : 'w-warn',tot2:tot,x:c.w.lbc[p.faction] !== undefined ? ` ${tt('common.changed')}` : ''})}</div></button>`;
      }).join('') + fsxAddLbcHtml()
    : off.filter(b => b.depth === 0).map(b => `<button class="trrow${c.sel === b.path ? ' on' : ''}"
          onclick="fsxPick('${q1(esc(b.path))}')"><div class="nm">${esc(b.path)}</div>
          <div class="sub">${tt('factionsites.block_s',{n:off.filter(x => x.path.startsWith(b.path + '/') && x.depth === 1).length})}</div></button>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <div class="fsxtabs">
        <button class="${c.tab === 'lbc' ? 'on' : ''}" onclick="fsxTab('lbc')">${tt('factionsites.populace')}</button>
        <button class="${c.tab === 'offmap' ? 'on' : ''}" onclick="fsxTab('offmap')">${tt('factionsites.off_map_models')}</button>
      </div>
      ${findingsHtml('factionsites', find, 'fsxOpen')}
      <div class="trrows">${left || `<div class="count" style="padding:8px">${esc(c.tab === 'lbc'
        ? (c.lbc_error || tt('factionsites.no_populace_blocks')) : (c.offmap_error || tt('factionsites.no_sections')))}</div>`}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>${c.tab === 'lbc' ? 'descr_lbc_db.txt' : 'descr_offmap_models.txt'}</b>
        <span class="count">${c.tab === 'lbc'
          ? tt('factionsites.the_townsfolk_a_factions_settlements_are')
          : tt('factionsites.a_factions_fleets_and_a_cultures')}</span></div>
        <span style="flex:1"></span>
        <button onclick="fsxRevert()" ${n ? '' : 'disabled'}>${tt('common.revert')}</button>
        <button class="primary" onclick="fsxSave()" ${n ? '' : 'disabled'}>${ttN('factionsites.save_changes',n)}</button>
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
  if(!fac) return `<div class="count" style="padding:8px">${tt('factionsites.pick_a_faction')}</div>`;
  if(c.w.lbc[fac] === null) return `<div class="count" style="padding:8px">${tt('factionsites.s_populace_is_taken_out_on',{fac:esc(fac)})}
    <button onclick="fsxUndrop('${q1(esc(fac))}')">${tt('common.keep_it')}</button></div>`;
  const rows = fsxRows(fac), tot = rows.reduce((s, r) => s + (+r[1] || 0), 0);
  return `<div class="cdbsec"><h3>${tt('factionsites.of_100',{fac:esc(fac),tot:tot === 100 ? 'count' : 'w-warn',tot2:tot})}</h3>
    <table class="smxtab"><tr><th>${tt('factionsites.model')}</th><th>${tt('factionsites.share')}</th><th></th></tr>
    ${rows.map((r, i) => `<tr><td><input style="width:220px" value="${esc(r[0])}" onchange="fsxLbcSet(${i}, 0, this.value)"></td>
      <td><input value="${esc(r[1])}" onchange="fsxLbcSet(${i}, 1, this.value)"></td>
      <td><button onclick="fsxLbcDrop(${i})">✕</button></td></tr>`).join('')}
    </table>
    <button onclick="fsxLbcAdd()">${tt('factionsites.a_model')}</button>
    <button onclick="fsxLbcRemove()" title="${ttA('factionsites.take_this_factions_populace_block_out')}">${tt('factionsites.remove_s_populace',{fac:esc(fac)})}</button>
    <div class="count">${tt('factionsites.both_installed_mods_give_every_faction')}</div></div>`;
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
  return `<div class="trnote">${tt('factionsites.in_the_roster_with_no_populace')}
    <select id="fsxNewFac">${missing.map(f => `<option>${esc(f)}</option>`).join('')}</select>
    ${tt('factionsites.copied_from')} <select id="fsxLike">${(c.lbc || []).map(p => `<option>${esc(p.faction)}</option>`).join('')}</select>
    <button onclick="fsxLbcNew()">${tt('common.add')}</button></div>`;
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
  if(!sec) return `<div class="count" style="padding:8px">${tt('factionsites.pick_a_section')}</div>`;
  const blocks = off.filter(b => b.path.startsWith(sec + '/'));
  const facs = blocks.filter(b => b.depth === 1 && b.kind === 'faction').map(b => b.head[1]);
  const gone = new Set(c.w.remove.filter(r => r.section === sec).map(r => r.faction));
  const body = blocks.map(b => {
    const drop = b.depth === 1 && b.kind === 'faction' && gone.has(b.head[1]);
    return `<div class="fsxblk" style="margin-left:${(b.depth - 1) * 16}px">
      <div class="nm"><code>${esc(b.head.join(' '))}</code> ${tt('factionsites.line',{line:b.line,x:b.depth === 1 && b.kind === 'faction' ? `<button onclick="fsxOffRemove('${q1(esc(sec))}','${q1(esc(b.head[1]))}')">${drop ? 'keep' : '✕'}</button>` : ''})}</div>
      ${drop ? `<div class="count">${tt('factionsites.taken_out_on_save')}</div>` : b.rows.map(r => `<div class="fsxrow">${
        (c.w.rows[r.line] || r.tokens).map((t, k) => `<input value="${esc(t)}" style="width:${k === (r.tokens.length > 3 ? 1 : 0) ? 330 : 70}px"
          onchange="fsxRowSet(${r.line}, ${k}, this.value)">`).join('')}</div>`).join('')}
    </div>`;
  }).join('');
  const add = facs.length ? `<div class="trnote">${tt('factionsites.add_a_faction_to',{sec:esc(sec)})}
    <input id="fsxOffFac" placeholder="${ttA('factionsites.slot')}" style="width:120px"> ${tt('factionsites.copied_from')}
    <select id="fsxOffLike">${facs.map(f => `<option>${esc(f)}</option>`).join('')}</select>
    <button onclick="fsxOffAdd('${q1(esc(sec))}')">${tt('common.add')}</button>
    ${c.w.add.filter(a => a.section === sec).map(a => `<div class="count">${tt('factionsites.from_on_save',{faction:esc(a.faction),like:esc(a.like)})}</div>`).join('')}</div>` : '';
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
  if(!confirm(tt('factionsites.write_confirm',{n:(p.changes || []).length,changes:(p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')}))) return;
  let res;
  try{ res = await api.post('/api/factionsites/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  await loadFactionSites();
}
