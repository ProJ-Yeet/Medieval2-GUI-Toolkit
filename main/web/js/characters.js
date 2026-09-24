/* characters.js - Agents and generals: descr_character.txt

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= AGENTS AND GENERALS (69) =========================
   Twelve character types, each with what it can do, its wage and its action
   points, then a block per faction: the models it stands on the campaign map
   with (a named character's default, heir and leader, and any more), and for
   a named character or a general the battle model it fights with. Each model
   links to its own screen, and a strat model's card links back here, which
   is the join nothing made before.

   THE PAGE NEVER PARSES A GAME FILE: /api/characters and its plan|apply. */

async function loadCharacters(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s agents and generals…</div>';
  let r;
  try{ r = await api.get('/api/characters?mod=' + enc(mod)); }
  catch(e){ if(stale('characters', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read them.<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadCharacters()">Retry</button></div>`; return; }
  if(stale('characters', mod)) return;
  const keep = state.chx && state.chx.mod === mod ? state.chx : null;
  state.chx = Object.assign({mod, sel: keep ? keep.sel : '', focus: keep ? keep.focus : '', w: chxBlank(), busy: false}, r);
  const types = r.types || [];
  if(state.chx.sel !== 'grid' && !types.some(t => t.type === state.chx.sel))
    state.chx.sel = types.length ? types[0].type : '';
  renderCharacters();
}
function chxBlank(){ return {values: {}, add_model: [], remove: [], copy_block: []}; }
function chxChanged(){
  const w = state.chx.w;
  return Object.keys(w.values).length + w.add_model.length + w.remove.length + w.copy_block.length;
}

function renderCharacters(){
  const c = state.chx;
  if(!c){ loadCharacters(); return; }
  const strip = minorTabsHtml('', 'data/descr_character.txt');
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key}));
  const n = chxChanged();
  const left = c.error ? `<div class="count" style="padding:8px">${esc(c.error)}.</div>`
    : `<button class="trrow${c.sel === 'grid' ? ' on' : ''}" onclick="chxPick('grid')">
        <div class="nm">Who has what</div><div class="sub">every type by every faction</div></button>`
      + (c.types || []).map(t => `<button class="trrow${c.sel === t.type ? ' on' : ''}" onclick="chxPick('${q1(esc(t.type))}')">
        <div class="nm">${esc(t.type)}</div><div class="sub">${t.blocks.length} faction block(s)</div></button>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('characters', find, 'chxOpen')}
      <div class="trrows">${left}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>descr_character.txt</b> <span class="count">what each agent does, and the models it stands and fights with</span></div>
        <span style="flex:1"></span>
        <button onclick="chxRevert()" ${n ? '' : 'disabled'}>Revert</button>
        <button class="primary" onclick="chxSave()" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
      </div>
      ${c.error ? '' : c.sel === 'grid' ? chxGridHtml() : chxTypeHtml()}
    </div>
  </div>`;
  if(c.focus){
    const el = document.getElementById('chxb' + c.focus);
    if(el) el.scrollIntoView({block: 'center'});
    c.focus = '';
  }
}
function chxPick(s){ state.chx.sel = s; renderCharacters(); }
/* `block/<line>` from a finding or the Strat models card, or
   `<type>/<faction>` from anywhere a person types one. */
function chxOpen(key){
  const c = state.chx, [kind, rest] = String(key).split(/\/(.*)/);
  let hit = null;
  for(const t of c.types || []){
    for(const b of t.blocks){
      if(kind === 'block' ? String(b.line) === rest
          : t.type.toLowerCase() === kind.toLowerCase() && b.factions.some(f => f.toLowerCase() === String(rest).toLowerCase()))
        hit = [t, b];
    }
    if(!hit && kind === 'type' && t.type === rest) hit = [t, null];
  }
  if(hit){ c.sel = hit[0].type; c.focus = hit[1] ? String(hit[1].line) : ''; }
  renderCharacters();
}
function chxRevert(){ state.chx.w = chxBlank(); renderCharacters(); }
function chxVal(line, v){ const w = state.chx.w.values; return w[line] !== undefined ? w[line] : v; }
function chxSet(line, v, was){
  const w = state.chx.w.values;
  if(v.trim() === was) delete w[line]; else w[line] = v.trim();
  renderCharacters();
}
function chxToggle(list, v){
  const i = list.indexOf(v);
  if(i >= 0) list.splice(i, 1); else list.push(v);
  renderCharacters();
}
function chxBox(r, width, list){
  return `<input style="width:${width}px" value="${esc(chxVal(r.line, r.value))}" ${list ? `list="${list}"` : ''}
    onchange="chxSet(${r.line}, this.value, '${q1(esc(r.value))}')">`;
}

function chxGridHtml(){
  const c = state.chx, roster = c.roster || [];
  const has = t => new Set(t.blocks.flatMap(b => b.factions.map(f => f.toLowerCase())));
  const sets = (c.types || []).map(t => [t, has(t)]);
  return `<div class="cdbsec"><h3>Who has what <span class="count">${roster.length} factions, ${sets.length} types</span></h3>
    <div style="overflow:auto"><table class="smxtab"><tr><th>faction</th>${sets.map(([t]) => `<th>${esc(t.type)}</th>`).join('')}</tr>
    ${roster.map(f => `<tr><td><code>${esc(f)}</code></td>${sets.map(([t, s]) => `<td>${s.has(f)
        ? `<a class="ulink" onclick="chxOpen('${q1(esc(t.type))}/${q1(esc(f))}')">✓</a>` : '<span class="count">·</span>'}</td>`).join('')}</tr>`).join('')}
    </table></div>
    <div class="count">Not every faction has every type, and that is not a fault: the rebels have no diplomat in ROCSS,
      and heretics and witches are the rebels' alone. Adding a faction's missing block is <b>Copy for</b> on a block that works.</div></div>`;
}

function chxTypeHtml(){
  const c = state.chx, t = (c.types || []).find(x => x.type === c.sel);
  if(!t) return '<div class="count" style="padding:8px">Pick a type.</div>';
  const w = c.w;
  const head = `<div class="cdbsec"><h3>${esc(t.type)} <span class="count">line ${t.line}</span></h3>
    <table class="smxtab">${t.head.map(r => `<tr><td><code>${esc(r.key)}</code></td>
      <td>${chxBox(r, r.key === 'actions' ? 620 : 90)}</td></tr>`).join('')}</table>
    <div class="count">The wage is per turn; the action points are how far it moves.</div></div>`;
  const blocks = t.blocks.map(b => {
    const gone = w.remove.includes(b.line);
    const models = b.rows.filter(r => r.key === 'strat_model');
    const rows = b.rows.filter(r => r.key !== 'strat_model').map(r => {
      const link = r.key === 'battle_model' ? ' ' + navLinkHtml({mode: 'bmdb', name: r.value}, '→ model', 'ulink',
        'Open this entry in the Models Editor (middle click: a new tab)') : '';
      return `<tr><td><code>${esc(r.key)}</code></td><td>${chxBox(r, r.key === 'battle_equip' ? 420 : 200,
        r.key === 'battle_model' ? 'chxBattleList' : '')}${link}</td><td></td></tr>`;
    }).join('');
    const mrows = models.map((r, k) => {
      const mg = w.remove.includes(r.line), name = (r.value || '').split(/\s+/)[0];
      return `<tr${mg ? ' style="opacity:.45"' : ''}><td><code>strat_model</code> <span class="count">${k}${r.label ? ' · ' + esc(r.label) : ''}</span></td>
        <td>${chxBox(r, 200, 'chxStratList')} ${navLinkHtml({mode: 'stratmap', name}, '→ model', 'ulink',
          'Open this strat model (middle click: a new tab)')}</td>
        <td>${models.length > 1 ? `<button onclick="chxToggle(state.chx.w.remove, ${r.line})">${mg ? 'keep' : '✕'}</button>` : ''}</td></tr>`;
    }).join('');
    const adds = w.add_model.filter(a => a.block === b.line).map(a =>
      `<tr><td colspan="3" class="count">+ strat_model ${esc(a.model)}, on save</td></tr>`).join('');
    const copies = w.copy_block.filter(a => a.block === b.line).map(a =>
      `<span class="count">+ a block for ${esc(a.faction)} on save</span>`).join(' ');
    return `<div class="cdbsec" id="chxb${b.line}"${gone ? ' style="opacity:.45"' : ''}>
      <h3>${esc(b.factions.join(', '))} <span class="count">line ${b.line}</span>
        ${t.blocks.length > 1 ? `<button onclick="chxToggle(state.chx.w.remove, ${b.line})">${gone ? 'Keep it' : 'Remove block'}</button>` : ''}</h3>
      <table class="smxtab">${rows}${mrows}${adds}</table>
      <div class="trnote">Add a strat model <input id="chxAdd${b.line}" list="chxStratList" style="width:180px" placeholder="model">
        <button onclick="chxAddModel(${b.line})">＋ Add</button>
        · Copy for <input id="chxCopy${b.line}" list="chxRosterList" style="width:120px" placeholder="faction">
        <button onclick="chxCopy(${b.line})">＋ Copy</button> ${copies}</div></div>`;
  }).join('');
  const dl = (id, xs) => `<datalist id="${id}">${(xs || []).map(x => `<option value="${esc(x)}">`).join('')}</datalist>`;
  return head + blocks + dl('chxStratList', c.strat_models) + dl('chxBattleList', c.battle_models)
    + dl('chxRosterList', c.roster);
}
function chxAddModel(line){
  const model = (document.getElementById('chxAdd' + line).value || '').trim();
  if(!model) return toast('Name the strat model first.');
  state.chx.w.add_model.push({block: line, model});
  renderCharacters();
}
function chxCopy(line){
  const faction = (document.getElementById('chxCopy' + line).value || '').trim();
  if(!faction) return toast('Name the faction the copy is for.');
  state.chx.w.copy_block.push({block: line, faction});
  renderCharacters();
}

async function chxSave(){
  const c = state.chx;
  if(c.busy) return;
  const body = Object.assign({mod: state.src, sig: c.sig || ''}, c.w);
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/characters/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write ${(p.changes || []).length} change(s)?\n\n` + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  let res;
  try{ res = await api.post('/api/characters/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadCharacters();
}
