/* walls.js - Walls, gates and towers: descr_walls.txt

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= WALLS, GATES AND TOWERS (68) =========================
   One wall block per wall level the EDB gives (0 to 4): the wall, its
   gateway and the gate types it may carry, its tower with a firing level per
   tower_level, and from level 1 or 2 up its gatehouse. The seven gates sit
   above them. The warning that matters is the EDB giving a wall or tower
   level this file cannot back.

   THE PAGE NEVER PARSES A GAME FILE: /api/walls and its plan|apply. */

async function loadWalls(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s walls…</div>';
  let r;
  try{ r = await api.get('/api/walls?mod=' + enc(mod)); }
  catch(e){ if(stale('walls', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read them.<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadWalls()">Retry</button></div>`; return; }
  if(stale('walls', mod)) return;
  const keep = state.wlx && state.wlx.mod === mod ? state.wlx : null;
  state.wlx = Object.assign({mod, sel: keep ? keep.sel : '', w: wlxBlank(), busy: false}, r);
  const list = r.walls || [];
  if(state.wlx.sel !== 'gates' && !list.some(x => String(x.id) === state.wlx.sel))
    state.wlx.sel = list.length ? String(list[0].id) : 'gates';
  renderWalls();
}
function wlxBlank(){ return {values: {}, add_gate: [], remove: [], copy_firing: []}; }
function wlxChanged(){
  const w = state.wlx.w;
  return Object.keys(w.values).length + w.add_gate.length + w.remove.length + w.copy_firing.length;
}

function renderWalls(){
  const c = state.wlx;
  if(!c){ loadWalls(); return; }
  const strip = minorTabsHtml('', 'data/descr_walls.txt');
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key}));
  const n = wlxChanged();
  const left = c.error ? `<div class="count" style="padding:8px">${esc(c.error)}.</div>`
    : `<button class="trrow${c.sel === 'gates' ? ' on' : ''}" onclick="wlxPick('gates')">
        <div class="nm">Gates</div><div class="sub">${(c.gates || []).length} gate types</div></button>`
      + (c.walls || []).map(x => `<button class="trrow${c.sel === String(x.id) ? ' on' : ''}" onclick="wlxPick('${x.id}')">
        <div class="nm">Wall level ${x.level ?? '?'}</div>
        <div class="sub">${x.parts.map(p => p.kind).join(', ')}${x.edb.length ? ` · ${x.edb.length} building(s) give it` : ''}</div></button>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('walls', find, 'wlxOpen')}
      <div class="trrows">${left}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>descr_walls.txt</b> <span class="count">walls, gates and towers in a siege, by wall level</span></div>
        <span style="flex:1"></span>
        <button onclick="wlxRevert()" ${n ? '' : 'disabled'}>Revert</button>
        <button class="primary" onclick="wlxSave()" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
      </div>
      ${c.error ? '' : c.sel === 'gates' ? wlxGatesHtml() : wlxWallHtml()}
    </div>
  </div>`;
}
function wlxPick(s){ state.wlx.sel = String(s); renderWalls(); }
function wlxOpen(key){
  const [kind, rest] = String(key).split(/\/(.*)/);
  if(kind === 'wall' && rest) state.wlx.sel = rest;
  else if(kind === 'level'){
    const x = (state.wlx.walls || []).find(w => String(w.level) === rest);
    if(x) state.wlx.sel = String(x.id);
  }
  renderWalls();
}
function wlxRevert(){ state.wlx.w = wlxBlank(); renderWalls(); }
function wlxVal(line, v){ const w = state.wlx.w.values; return w[line] !== undefined ? w[line] : v; }
function wlxSet(line, v, was){
  const w = state.wlx.w.values;
  if(v.trim() === was) delete w[line]; else w[line] = v.trim();
  renderWalls();
}
function wlxRows(rows){
  return rows.map(r => {
    const v = wlxVal(r.line, r.value), wide = r.key === 'stat' ? 520 : r.key === 'fire_rate' ? 160 : r.key === 'battle_stats' ? 300 : 110;
    return `<tr><td><code>${esc(r.key)}</code></td>
      <td><input style="width:${wide}px" value="${esc(v)}" onchange="wlxSet(${r.line}, this.value, '${q1(esc(r.value))}')"></td></tr>`;
  }).join('');
}
function wlxGatesHtml(){
  const c = state.wlx;
  return (c.gates || []).map(g => `<div class="cdbsec"><h3>${esc(g.name)} <span class="count">line ${g.line}</span></h3>
    <table class="smxtab">${wlxRows(g.rows)}</table></div>`).join('')
    + `<div class="count">A gateway carries the gate types named inside it. The file's own comment: a short gate is wooden only, medium and huge come in wooden, reinforced and iron.</div>`;
}
function wlxToggle(list, v){
  const i = list.indexOf(v);
  if(i >= 0) list.splice(i, 1); else list.push(v);
  renderWalls();
}
function wlxWallHtml(){
  const c = state.wlx, x = (c.walls || []).find(w => String(w.id) === c.sel);
  if(!x) return '<div class="count" style="padding:8px">Pick a wall level.</div>';
  const w = c.w, gates = (c.gates || []).map(g => g.name);
  const parts = x.parts.map(p => {
    const gateRow = p.kind === 'gateway' ? `<div class="trnote">Gate types:
      ${p.gates.map(g => `<code${w.remove.includes(g.line) ? ' style="opacity:.45"' : ''}>${esc(g.gate)}</code>
        <button onclick="wlxToggle(state.wlx.w.remove, ${g.line})">${w.remove.includes(g.line) ? 'keep' : '✕'}</button>`).join(' ')}
      ${w.add_gate.filter(a => a.gateway === p.line).map(a => `<code>+ ${esc(a.gate)}</code>`).join(' ')}
      ${(() => { const free = gates.filter(g => !p.gates.some(x2 => x2.gate === g) && !w.add_gate.some(a => a.gateway === p.line && a.gate === g));
          return free.length ? `<select id="wlxGate${p.line}">${free.map(g => `<option>${esc(g)}</option>`).join('')}</select>
            <button onclick="wlxAddGate(${p.line})">＋ Add</button>` : ''; })()}</div>` : '';
    const firing = p.firing.map((f, k) => {
      const gone = w.remove.includes(f.line);
      return `<div class="cdbsec"${gone ? ' style="opacity:.45"' : ''}><h3>${esc(p.kind)} · firing level ${k + 1}
          <span class="count"><code>${esc(f.kind)}</code> · line ${f.line}</span>
          <button onclick="wlxToggle(state.wlx.w.copy_firing, ${f.line})">${w.copy_firing.includes(f.line) ? 'no copy' : 'Copy'}</button>
          ${p.firing.length > 1 ? `<button onclick="wlxToggle(state.wlx.w.remove, ${f.line})">${gone ? 'Keep it' : 'Remove'}</button>` : ''}</h3>
        <table class="smxtab">${wlxRows(f.rows)}</table></div>`;
    }).join('');
    return `<div class="cdbsec"><h3>${esc(p.kind)} <span class="count">line ${p.line}</span></h3>
      <table class="smxtab">${wlxRows(p.rows)}</table>${gateRow}</div>${firing}`;
  }).join('');
  return `<div class="cdbsec"><h3>Wall level ${x.level ?? '?'} <span class="count">line ${x.line}</span></h3>
      <table class="smxtab">${wlxRows(x.rows)}</table>
      <div class="count">${x.edb.length ? `Given by ${esc(x.edb.slice(0, 6).join(', '))}${x.edb.length > 6 ? '…' : ''} (<code>wall_level ${x.level}</code>)${
        x.tower_levels.length ? `, with <code>tower_level ${x.tower_levels.join(', ')}</code>: its tower needs that many firing levels` : ''}.`
        : 'No EDB building gives this wall level together with a tower level.'}
        A <code>stat</code> line is the eleven fields of an EDU <code>stat_pri</code>: attack, charge, projectile, range, ammo, and the rest.</div></div>
    ${parts}`;
}
function wlxAddGate(line){
  const gate = document.getElementById('wlxGate' + line).value;
  state.wlx.w.add_gate.push({gateway: line, gate});
  renderWalls();
}

async function wlxSave(){
  const c = state.wlx;
  if(c.busy) return;
  const body = Object.assign({mod: state.src, sig: c.sig || ''}, c.w);
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/walls/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write ${(p.changes || []).length} change(s)?\n\n` + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  let res;
  try{ res = await api.post('/api/walls/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadWalls();
}
