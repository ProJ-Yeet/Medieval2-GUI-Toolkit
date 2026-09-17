/* mercs.js - Campaign Map: who can hire which mercenary, and where

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE MERCENARY POOLS - Phase 32b.

   Every name here starts `mcp`. Python owns every rule: the page is handed
   each unit line with its gates already resolved (/api/map/mercs) and never
   decides for itself whether a faction can hire something.

   TWO DIRECTIONS. From the province clicked on the map: its pool and every
   unit line in it, with a verdict and the reason for it. From a mercenary:
   every pool that sells it, at what price there, and the provinces - with a
   button that colours them on the map through the query panel's own
   `merc:<unit>` map, so the picture and the legend are the ones every other
   map uses.

   THE VERDICT IS FOR THE FACTION PICKED, OR FOR NOBODY. A line has up to five
   gates and none of them names a province: the unit must be in the EDU, the
   faction's religion in `religions { }`, the faction in `factions { }` (a
   word the file's own header never mentions and Fellowship uses on 41 of 51
   lines), and then `crusading`, `events { }` and the two years only delay it.
   With no faction picked the two faction gates say what they need and decide
   nothing.

   EDITING IS THE POOL ENTRY, NOT THE UNIT. Cost, pool size, replenish and the
   gates are this file's; the unit itself is the EDU's and the Unit Editor
   owns it. A dead reference is fixed by naming a unit that exists. */

/* ---------- state ---------- */

function mcpNew(mod, campaign){
  // `autoLight`: picking a mercenary colours the provinces that sell it, with
  // no second click - on unless the toggle beside the manual button says not
  return {mod, campaign, open: false, loading: false, d: null, faction: '',
          view: 'province', unit: '', q: '', edit: null, adding: '', busy: false,
          autoLight: true};
}

function mcpOpen(){
  const c = state.cmap;
  if(!c) return;
  const was = state.mcp, camp = c.campaign || '';
  if(was && was.mod === c.mod && was.campaign === camp){ mcpPaint(); return; }
  const k = state.mcp = mcpNew(c.mod, camp);
  if(was){ k.open = was.open; k.view = was.view; k.autoLight = was.autoLight; }
  if(k.open) mcpLoad(); else mcpPaint();
}

function mcpToggle(){
  const k = state.mcp;
  if(!k) return;
  k.open = !k.open;
  if(k.open) activity('mercenaries', `${k.mod}: opened the mercenary pools`);
  if(k.open && !k.d) mcpLoad(); else mcpPaint();
}

async function mcpLoad(){
  const k = state.mcp;
  if(!k) return;
  k.loading = true;
  mcpPaint();
  let d;
  try{
    d = await api.get(`/api/map/mercs?mod=${enc(k.mod)}`
      + (k.campaign ? `&campaign=${enc(k.campaign)}` : '')
      + (k.faction ? `&faction=${enc(k.faction)}` : ''),
      {label: 'reading the mercenary pools'});
  }catch(e){ d = {error: errText(e), pools: [], units: []}; }
  if(state.mcp !== k) return;
  k.loading = false;
  k.d = d;
  mcpPaint();
}

function mcpFaction(name){
  const k = state.mcp;
  if(!k) return;
  k.faction = name;
  mcpLoad();
}

function mcpView(v){
  const k = state.mcp;
  if(!k) return;
  k.view = v; k.edit = null; k.adding = '';
  mcpPaint();
}

function mcpPickUnit(name, keep){
  const k = state.mcp;
  if(!k) return;
  k.unit = (k.unit === name && !keep) ? '' : name;
  mcpPaint();
  if(!k.autoLight) return;
  if(k.unit) mcpLight(k.unit, true);
  else mcpUnlight();
}

//: Take the map's colouring off, but only one this panel put there - a theme
//: somebody chose on the Query tab is theirs.
async function mcpUnlight(){
  const q = state.cq;
  if(q && (q.theme || '').startsWith('merc:')) await cqTheme('');
}

function mcpAutoLight(on){
  const k = state.mcp;
  if(!k) return;
  k.autoLight = !!on;
  if(on && k.unit) mcpLight(k.unit, true);
  else if(!on) mcpUnlight();
  mcpPaint();
}

function mcpSearch(q){
  const k = state.mcp;
  if(!k) return;
  k.q = q;
  const el = document.getElementById('mcpList');
  if(el) el.innerHTML = mcpUnitRowsHtml();
}

//: The province the map has picked, or '' - the panel follows the map rather
//: than keeping a pick of its own.
function mcpProvince(){
  const c = state.cmap;
  return (c && c.sel && c.sel.name) || '';
}

function mcpGo(name){
  const c = state.cmap;
  if(!c || !c.man) return;
  const hit = (c.man.regions || []).find(r => r.name.toLowerCase() === name.toLowerCase());
  if(!hit){ toast(`✗ ${name} has no tiles on this map`, 5000); return; }
  cmapGoRegion(hit.key);
}

//: Colour the provinces selling this unit, through the query panel's own map.
async function mcpLight(name, quiet){
  if(!state.cq) cqOpen();
  if(!state.cq) return;
  await cqTheme('merc:' + name);
  if(!quiet) toast(`The map shows where ${name} is sold - the Query tab holds the legend`, 5000);
}

//: The unit's own card, off the same /icon route the unit grid uses. A name the
//: EDU does not have gets no picture rather than a blank frame.
function mcpCardHtml(name, known){
  if(known === false) return '<span class="mcpcard none" title="not a unit in the EDU">?</span>';
  const k = state.mcp;
  return `<img class="mcpcard" loading="lazy" onerror="iconRetry(this)"
    src="${iconUrl(k.mod, name)}" alt="">`;
}

/* ---------- drawing ---------- */

function mcpPaint(){
  const el = document.getElementById('cmMercs');
  if(!el) return;
  el.innerHTML = mcpHtml();
}

const MCP_VERDICT = {
  yes: ['ok', 'can hire'], later: ['later', 'not yet'], no: ['no', 'never'],
  unknown: ['unk', 'depends on a script'],
};

function mcpBadge(v){
  const b = MCP_VERDICT[v] || ['unk', v];
  return `<span class="mcpv ${b[0]}">${esc(b[1])}</span>`;
}

function mcpHtml(){
  const k = state.mcp;
  if(!k || !k.open) return `<div class="cbrpanel">
    <div class="cmbar2">
      <button onclick="mcpToggle()" title="Which mercenaries each province sells,
who may hire them and why not, and every province a mercenary is sold in">Mercenary pools…</button>
      <span class="sp"></span><span class="count">both directions</span>
    </div></div>`;
  if(k.loading && !k.d) return `<div class="cbrpanel count">reading
    <code>descr_mercenaries.txt</code> and the five files its gates name…</div>`;
  const d = k.d || {};
  if(d.error) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.error)}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpToggle()">Close</button></div></div>`;
  const n = d.counts || {};
  return `<div class="cbrpanel mcp">
    <div class="k">Mercenary pools
      <span class="count">${n.pools} pools · ${n.units} units on ${n.lines} lines ·
        ${n.regions} provinces · <code>${esc(d.file)}</code></span></div>
    ${mcpNotesHtml(d)}
    <div class="cmform"><div class="cmfield">
      <label>Hired by</label>
      <select onchange="mcpFaction(this.value)">
        <option value="">(any faction - the faction gates decide nothing)</option>
        ${(d.factions || []).map(f => `<option value="${esc(f.name)}"
          ${f.name === k.faction ? 'selected' : ''}>${esc(f.label || f.name)} ·
          ${esc(f.religion || 'no religion')}${f.status === 'nonplayable' ? ' · not playable' : ''}</option>`).join('')}
      </select>
    </div></div>
    <div class="mftabs mcptabs">
      <button class="mftab${k.view === 'province' ? ' on' : ''}" onclick="mcpView('province')">This province</button>
      <button class="mftab${k.view === 'unit' ? ' on' : ''}" onclick="mcpView('unit')">A mercenary</button>
      <button class="mftab${k.view === 'pools' ? ' on' : ''}" onclick="mcpView('pools')">Pools</button>
    </div>
    ${k.view === 'unit' ? mcpUnitHtml(d) : k.view === 'pools' ? mcpPoolsHtml(d) : mcpProvinceHtml(d)}
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpToggle()">Close</button></div>
  </div>`;
}

//: The whole-file facts worth saying before any row: names the EDU lacks, a
//: province in two pools, and the campaign's own dates that the years gate on.
function mcpNotesHtml(d){
  const out = [];
  const y = d.years || {};
  if(y.start != null) out.push(`<div class="count">The campaign runs ${y.start} to
    ${y.end}${y.timescale ? `, ${y.timescale} of a year a turn` : ''}.</div>`);
  const dead = d.unknown_units || [];
  if(dead.length) out.push(`<div class="w-bad">${dead.length} unit name${
    dead.length === 1 ? '' : 's'} in this file ${dead.length === 1 ? 'is' : 'are'} not a
    unit in the EDU, so no faction can hire ${dead.length === 1 ? 'it' : 'them'}:
    ${dead.slice(0, 6).map(x => `<code>${esc(x)}</code>`).join(', ')}${
    dead.length > 6 ? ` and ${dead.length - 6} more` : ''}.</div>`);
  // 32c's one repair. Which pool a province stays in is a choice, so it is
  // offered both ways and goes through 32a's region_move like any other move
  const two = Object.entries(d.in_two || {});
  if(two.length) out.push(`<div class="w-warn">${two.length} province${
    two.length === 1 ? ' is' : 's are'} in more than one pool, which the file's
    own header forbids. Keep each in one:
    ${two.map(([low, pools]) => {
      const name = mcpRegionName(d, low);
      return `<div class="cmbar2"><code>${esc(name)}</code><span class="sp"></span>${
        pools.map(p => `<button onclick="mcpKeepIn('${q1(esc(name))}', '${q1(esc(p))}')"
          title="Take ${esc(name)} out of every other pool">Keep in ${esc(p)}</button>`).join('')}</div>`;
    }).join('')}</div>`);
  return out.join('');
}

function mcpGatesHtml(u){
  // a unit that is in the EDU says nothing worth a line; every other gate
  // does, including a faction gate that passes, because that is the reason
  return `<div class="mcpgates">${(u.gates || []).filter(g =>
      !(g.gate === 'unit' && g.state === 'ok')).map(g =>
    `<div class="mcpg ${esc(g.state)}"><b>${esc(g.gate)}</b> ${esc(g.say)}</div>`).join('')}</div>`;
}

function mcpLineHtml(pool, u){
  const k = state.mcp;
  const r = u.replenish || [];
  const editing = k.edit && k.edit.pool === pool && k.edit.index === u.index;
  return `<div class="mcpline${u.hire === 'no' ? ' dead' : ''}">
    <div class="mcphead">
      ${mcpCardHtml(u.name, (u.gates || []).some(g => g.gate === 'unit' && g.state === 'no') ? false : null)}
      <span class="mcpnm">${esc(u.name)}</span>${mcpBadge(u.hire)}
      <span class="count">${u.cost} · exp ${u.exp} · pool ${u.initial}/${u.max} ·
        +${r[0]}-${r[1]} a turn</span>
      <span class="sp"></span>
      <button class="rebgo" title="Where else ${esc(u.name)} is sold"
        onclick="mcpView('unit');mcpPickUnit('${q1(esc(u.name))}', true)">⇄</button>
      <button class="rebgo" title="Edit this pool entry"
        onclick="mcpEdit('${q1(esc(pool))}', ${u.index})">✎</button>
    </div>
    ${mcpGatesHtml(u)}
    ${editing ? mcpEditHtml() : ''}
  </div>`;
}

function mcpProvinceHtml(d){
  const k = state.mcp, name = mcpProvince();
  if(!name) return `<div class="count" style="padding:6px 2px">Click a province on
    the map to see the mercenaries it sells.</div>`;
  const low = name.toLowerCase();
  const pools = (d.pools || []).filter(p => p.regions.some(r => r.toLowerCase() === low));
  if(!pools.length) return `<div class="k">${esc(name)}</div>
    <div class="w-warn">In no pool, so no mercenary is ever sold here. The Region
    tab's Mercenaries box puts it in one.</div>`;
  return `<div class="k">${esc(name)}<span class="count">${pools.length > 1
      ? 'in ' + pools.length + ' pools' : 'pool ' + esc(pools[0].name)} ·
    ${pools.reduce((n, p) => n + p.units.length, 0)} unit lines</span></div>
    ${pools.map(p => `${pools.length > 1 ? `<div class="k">${esc(p.name)}</div>` : ''}
      ${p.units.map(u => mcpLineHtml(p.name, u)).join('')
        || '<div class="w-warn">This pool sells nothing.</div>'}
      ${mcpAddHtml(p.name)}`).join('')}`;
}

function mcpPoolsHtml(d){
  return `<div class="reblist">${(d.pools || []).map(p => {
    const hire = p.units.filter(u => u.hire === 'yes').length;
    return `<div class="rebrow" style="flex-wrap:wrap">
      <span class="rebnm">${esc(p.name)}</span>
      <span class="count">${p.regions.length} province${p.regions.length === 1 ? '' : 's'} ·
        ${p.units.length} line${p.units.length === 1 ? '' : 's'}${
        state.mcp.faction ? ` · ${hire} hireable now` : ''}</span>
      <div style="flex:1 0 100%">${p.regions.map(r => `<button class="rebgo"
        onclick="mcpGo('${q1(esc(r))}')">${esc(r)}</button>`).join(' ')}</div>
    </div>`;
  }).join('')}</div>`;
}

function mcpUnitRowsHtml(){
  const k = state.mcp, d = k.d || {}, q = (k.q || '').toLowerCase();
  const rows = (d.units || []).filter(u => !q || u.name.toLowerCase().includes(q));
  return rows.map(u => {
    const yes = u.offers.filter(o => o.hire === 'yes').length;
    const price = u.prices.length ? (u.prices.length > 1
      ? `${u.prices[0]}-${u.prices[u.prices.length - 1]}` : `${u.prices[0]}`) : '?';
    return `<button class="rebrow${k.unit === u.name ? ' on' : ''}${u.known === false ? ' orphan' : ''}"
      onclick="mcpPickUnit('${q1(esc(u.name))}')">
      ${mcpCardHtml(u.name, u.known)}
      <span class="rebnm">${esc(u.name)}${u.known === false
        ? '<span class="reborph">not in the EDU</span>' : ''}</span>
      <span class="count">${u.offers.length} pool${u.offers.length === 1 ? '' : 's'} ·
        ${u.provinces} province${u.provinces === 1 ? '' : 's'} · ${price}${
        k.faction ? ` · ${yes} hireable` : ''}</span></button>`;
  }).join('') || '<div class="count" style="padding:6px">No mercenary matches.</div>';
}

function mcpUnitHtml(d){
  const k = state.mcp;
  const u = (d.units || []).find(x => x.name === k.unit);
  return `<input type="search" placeholder="Find a mercenary…" value="${esc(k.q)}"
      oninput="mcpSearch(this.value)" style="width:100%">
    <div class="reblist" id="mcpList">${mcpUnitRowsHtml()}</div>
    ${u ? `<div class="rebdet">
      <div class="k">${esc(u.name)}<span class="count">sold by ${u.offers.length}
        pool${u.offers.length === 1 ? '' : 's'}${u.prices.length > 1
        ? ` at ${u.prices.length} different prices` : ''}</span></div>
      <div class="cmbar2"><button onclick="mcpLight('${q1(esc(u.name))}')"
        title="Colour every province whose pool sells it">◉ Light on the map</button>
        <label class="mcpauto" title="Colour the provinces as soon as a mercenary is picked">
          <input type="checkbox" ${k.autoLight ? 'checked' : ''}
            onchange="mcpAutoLight(this.checked)"> light it when picked</label></div>
      ${u.offers.map(o => {
        const pool = (d.pools || []).find(p => p.name === o.pool);
        const line = pool && pool.units[o.index];
        return `<div class="mcpoffer"><div class="k">${esc(o.pool)}
          <span class="count">${o.regions.length} province${o.regions.length === 1 ? '' : 's'}</span></div>
          ${line ? mcpLineHtml(o.pool, line) : ''}
          <div>${o.regions.map(r => `<button class="rebgo"
            onclick="mcpGo('${q1(esc(r))}')">${esc(r)}</button>`).join(' ')}</div></div>`;
      }).join('')}
    </div>` : '<div class="count" style="padding:6px 2px">Pick a mercenary to see every pool and province it is sold in.</div>'}`;
}

/* ---------- the pool entry: edit, add, remove ---------- */

const MCP_FIELDS = [
  ['exp', 'Experience', 'a whole number, 0 to 9'],
  ['cost', 'Cost', 'what hiring one costs'],
  ['max', 'Pool size', 'the most the pool holds'],
  ['initial', 'Starts with', 'how many are there on turn one'],
  ['replenish', 'Replenish', 'low and high, units a turn'],
  ['religions', 'Religions', 'blank takes the gate off; empty braces mean everybody'],
  ['factions', 'Factions', 'blank takes the gate off'],
  ['events', 'Events', 'blank takes the gate off'],
  ['start_year', 'From year', '0 or blank for none'],
  ['end_year', 'Until year', '0 or blank for none'],
];

function mcpLineOf(pool, index){
  const d = state.mcp.d || {};
  const p = (d.pools || []).find(x => x.name === pool);
  return p ? p.units[index] : null;
}

//: The form holds text, so what went in is what goes back to Python - which
//: says what is wrong with it rather than this file guessing.
function mcpForm(u){
  const r = u ? u.replenish || [] : [];
  const list = v => v == null ? '' : v.join(' ');
  return {name: u ? u.name : '', exp: u ? String(u.exp) : '0', cost: u ? String(u.cost) : '',
          max: u ? String(u.max) : '1', initial: u ? String(u.initial) : '0',
          replenish: u ? `${r[0]} - ${r[1]}` : '0.05 - 0.1',
          religions: u ? list(u.religions) : '', factions: u ? list(u.factions) : '',
          events: u ? list(u.events) : '',
          start_year: u && u.start_year ? String(u.start_year) : '',
          end_year: u && u.end_year ? String(u.end_year) : '',
          crusading: !!(u && u.crusading),
          had: u ? {religions: u.religions != null, factions: u.factions != null,
                    events: u.events != null} : {}};
}

function mcpEdit(pool, index){
  const k = state.mcp;
  const u = mcpLineOf(pool, index);
  if(!u) return;
  k.adding = '';
  k.edit = (k.edit && k.edit.pool === pool && k.edit.index === index)
    ? null : {pool, index, w: mcpForm(u)};
  mcpPaint();
}

function mcpAddOpen(pool){
  const k = state.mcp;
  k.edit = null;
  k.adding = k.adding === pool ? '' : pool;
  k.addForm = mcpForm(null);
  mcpPaint();
}

function mcpSet(which, key, value){
  const k = state.mcp;
  const w = which === 'add' ? k.addForm : (k.edit && k.edit.w);
  if(w) w[key] = value;
}

function mcpFieldsHtml(which, w){
  return `<div class="mcpform">${[['name', 'Unit', 'a unit type in the EDU']].concat(
      which === 'add' ? [] : []).concat(MCP_FIELDS).map(([key, label, hint]) => {
    if(key === 'name' && which !== 'add') return '';
    return `<label title="${esc(hint)}">${esc(label)}</label>
      <input type="text" value="${esc(w[key])}" placeholder="${esc(hint)}"
        ${key === 'name' ? 'list="mcpEduTypes"' : ''}
        oninput="mcpSet('${which}', '${key}', this.value)">`;
  }).join('')}
    <label>Crusading</label>
    <input type="checkbox" ${w.crusading ? 'checked' : ''}
      onchange="mcpSet('${which}', 'crusading', this.checked)"
      title="only to a crusade or jihad army">
  </div>`;
}

function mcpEditHtml(){
  const k = state.mcp, e = k.edit;
  return `<div class="rebdet">${mcpFieldsHtml('edit', e.w)}
    <div class="cmbar2">
      <button class="bad" onclick="mcpRemove()">Remove this line</button>
      <span class="sp"></span>
      <button onclick="mcpEdit('${q1(esc(e.pool))}', ${e.index})">Cancel</button>
      <button class="primary" onclick="mcpSave()">Save</button>
    </div></div>`;
}

function mcpAddHtml(pool){
  const k = state.mcp;
  if(k.adding !== pool) return `<div class="cmbar2"><span class="sp"></span>
    <button onclick="mcpAddOpen('${q1(esc(pool))}')">＋ Sell another unit here</button></div>`;
  const types = (k.d && k.d.edu_types) || [];
  return `<div class="rebdet"><div class="k">New line in ${esc(pool)}</div>
    ${mcpFieldsHtml('add', k.addForm)}
    <datalist id="mcpEduTypes">${types.map(t => `<option value="${esc(t)}">`).join('')}</datalist>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpAddOpen('${q1(esc(pool))}')">Cancel</button>
      <button class="primary" onclick="mcpAdd()">Add</button></div></div>`;
}

//: Form text to the values Python takes. A list box left blank takes the gate
//: off only if the line had it; `{ }` typed is an empty list, which is a gate.
function mcpValues(w, onlyChanged, base){
  const out = {};
  const num = v => (v === '' || v == null) ? null : v.trim();
  const rep = String(w.replenish || '').split(/\s*-\s*|\s+/).filter(Boolean);
  const vals = {exp: w.exp.trim(), cost: w.cost.trim(), max: w.max.trim(),
                initial: w.initial.trim(), replenish: rep};
  for(const key of ['religions', 'factions', 'events']){
    const t = String(w[key] || '').trim();
    if(t === '') vals[key] = null;
    else vals[key] = t.replace(/[{}]/g, ' ').split(/\s+/).filter(Boolean);
  }
  for(const key of ['start_year', 'end_year']){
    const t = num(w[key]);
    vals[key] = (t === null || t === '0') ? null : t;
  }
  vals.crusading = !!w.crusading;
  if(!onlyChanged) return Object.assign(vals, {name: w.name.trim()});
  const was = mcpForm(base), wv = mcpValues(was, false);
  for(const key of Object.keys(vals)){
    if(JSON.stringify(vals[key]) !== JSON.stringify(wv[key])) out[key] = vals[key];
  }
  return out;
}

async function mcpWrite(body, what){
  const k = state.mcp;
  if(k.busy) return;
  body = Object.assign({mod: k.mod, campaign: k.campaign || ''}, body);
  k.busy = true;
  let res;
  try{ res = await api.post('/api/mercpools/plan', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); return; }
  const p = res.plan || {};
  if(!confirm(`Write: ${what}?\n\n${(p.changes || []).join('\n')}`
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.join('\n⚠ ') : '')
    + `\n\nOnly ${k.d.file} of this campaign is written.`
    + '\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  try{ res = await api.post('/api/mercpools/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); return; }
  toast('Saved. 🕑 Log can undo it.', 5000);
  activity('mercenaries', `${k.mod}: ${what}`);
  k.edit = null; k.adding = '';
  await mcpLoad();
  // the Region tab's pool box reads the same file
  const c = state.cmap;
  if(c && c.det){ const name = c.det.name; c.det = null; cmapOpenRegion(name); }
}

//: `in_two` is keyed lower case; the file's own spelling is what gets written
function mcpRegionName(d, low){
  for(const p of d.pools || []){
    const hit = p.regions.find(r => r.toLowerCase() === low);
    if(hit) return hit;
  }
  return low;
}

async function mcpKeepIn(region, pool){
  await mcpWrite({action: 'region_move', region, pool},
                 `keep ${region} in ${pool} alone`);
}

async function mcpSave(){
  const e = state.mcp.edit;
  if(!e) return;
  const u = mcpLineOf(e.pool, e.index);
  const edits = mcpValues(e.w, true, u);
  if(!Object.keys(edits).length){ toast('Nothing changed', 3000); return; }
  await mcpWrite({action: 'unit_edit', pool: e.pool, unit: e.index, edits},
                 `${u.name} in ${e.pool}`);
}

async function mcpRemove(){
  const e = state.mcp.edit;
  if(!e) return;
  const u = mcpLineOf(e.pool, e.index);
  await mcpWrite({action: 'unit_delete', pool: e.pool, unit: e.index},
                 `remove ${u.name} from ${e.pool}`);
}

async function mcpAdd(){
  const k = state.mcp;
  const values = mcpValues(k.addForm, false);
  if(!values.name){ toast('✗ name the unit first', 4000); return; }
  await mcpWrite({action: 'unit_add', pool: k.adding, values},
                 `sell ${values.name} in ${k.adding}`);
}
