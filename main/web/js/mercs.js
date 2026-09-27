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
  if(k.open) activity('mercenaries', tt('mercs.opened_the_mercenary_pools',{mod:k.mod}));
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
      {label: tt('mercs.reading_the_mercenary_pools')});
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
  if(!hit){ toast(tt('mercs.has_no_tiles_on_this_map',{name}), 5000); return; }
  cmapGoRegion(hit.key);
}

//: Colour the provinces selling this unit, through the query panel's own map.
async function mcpLight(name, quiet){
  if(!state.cq) cqOpen();
  if(!state.cq) return;
  await cqTheme(tt('mercs.merc') + name);
  if(!quiet) toast(tt('mercs.the_map_shows_where_is_sold',{name}), 5000);
}

//: The unit's own card, off the same /icon route the unit grid uses. A name the
//: EDU does not have gets no picture rather than a blank frame.
function mcpCardHtml(name, known){
  if(known === false) return `<span class="mcpcard none" title="${ttA('mercs.not_a_unit_in_the_edu')}">?</span>`;
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
  yes: ['ok', tt('mercs.can_hire')], later: ['later', tt('mercs.not_yet')], no: ['no', 'never'],
  unknown: ['unk', tt('mercs.depends_on_a_script')],
};

function mcpBadge(v){
  const b = MCP_VERDICT[v] || ['unk', v];
  return `<span class="mcpv ${b[0]}">${esc(b[1])}</span>`;
}

function mcpHtml(){
  const k = state.mcp;
  if(!k || !k.open) return `<div class="cbrpanel">
    <div class="cmbar2">
      <button onclick="mcpToggle()" title="${ttA('mercs.which_mercenaries_each_province_sells_who')}">${tt('mercs.mercenary_pools')}</button>
      <span class="sp"></span><span class="count">${tt('mercs.both_directions')}</span>
    </div></div>`;
  if(k.loading && !k.d) return `<div class="cbrpanel count">${tt('mercs.reading_descr_mercenaries_txt_and_the')}</div>`;
  const d = k.d || {};
  if(d.error) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.error)}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpToggle()">${tt('common.close')}</button></div></div>`;
  const n = d.counts || {};
  return `<div class="cbrpanel mcp">
    <div class="k">${tt('mercs.mercenary_pools_pools_units_on_lines',{pools:n.pools,units:n.units,lines:n.lines,regions:n.regions,file:esc(d.file)})}</div>
    ${mcpNotesHtml(d)}
    <div class="cmform"><div class="cmfield">
      <label>${tt('mercs.hired_by')}</label>
      <select onchange="mcpFaction(this.value)">
        <option value="">${tt('mercs.any_faction_the_faction_gates_decide')}</option>
        ${(d.factions || []).map(f => `<option value="${esc(f.name)}"
          ${f.name === k.faction ? 'selected' : ''}>${esc(f.label || f.name)} ·
          ${esc(f.religion || tt('mercs.no_religion'))}${f.status === 'nonplayable' ? tt('mercs.not_playable') : ''}</option>`).join('')}
      </select>
    </div></div>
    <div class="mftabs mcptabs">
      <button class="mftab${k.view === 'province' ? ' on' : ''}" onclick="mcpView('province')">${tt('mercs.this_province')}</button>
      <button class="mftab${k.view === 'unit' ? ' on' : ''}" onclick="mcpView('unit')">${tt('mercs.a_mercenary')}</button>
      <button class="mftab${k.view === 'pools' ? ' on' : ''}" onclick="mcpView('pools')">${tt('mercs.pools')}</button>
    </div>
    ${k.view === 'unit' ? mcpUnitHtml(d) : k.view === 'pools' ? mcpPoolsHtml(d) : mcpProvinceHtml(d)}
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpToggle()">${tt('common.close')}</button></div>
  </div>`;
}

//: The whole-file facts worth saying before any row: names the EDU lacks, a
//: province in two pools, and the campaign's own dates that the years gate on.
function mcpNotesHtml(d){
  const out = [];
  const y = d.years || {};
  if(y.start != null) out.push(`<div class="count">${tt('mercs.the_campaign_runs_to',{start:y.start,end:y.end,timescale:y.timescale ? tt('mercs.of_a_year_a_turn',{timescale:y.timescale}) : ''})}</div>`);
  const dead = d.unknown_units || [];
  if(dead.length) out.push(`<div class="w-bad">${tt('mercs.unit_name_in_this_file_not',{dead_n:dead.length,dead:dead.length === 1 ? '' : 's',dead2:dead.length === 1 ? 'is' : 'are',dead3:dead.length === 1 ? 'it' : 'them',dead4:dead.slice(0, 6).map(x => `<code>${esc(x)}</code>`).join(', '),dead5:dead.length > 6 ? tt('mercs.and_more',{dead:dead.length - 6}) : ''})}</div>`);
  // 32c's one repair. Which pool a province stays in is a choice, so it is
  // offered both ways and goes through 32a's region_move like any other move
  const two = Object.entries(d.in_two || {});
  if(two.length) out.push(`<div class="w-warn">${tt('mercs.province_in_more_than_one_pool',{two_n:two.length,two:two.length === 1 ? ' is' : tt('common.s_are'),x:two.map(([low, pools]) => {
      const name = mcpRegionName(d, low);
      return `<div class="cmbar2"><code>${esc(name)}</code><span class="sp"></span>${
        pools.map(p => `<button onclick="mcpKeepIn('${q1(esc(name))}', '${q1(esc(p))}')"
          title="${ttA('mercs.take_out_of_every_other_pool',{name:esc(name)})}">${tt('mercs.keep_in',{x:esc(p)})}</button>`).join('')}</div>`;
    }).join('')})}</div>`);
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
      ${tt('mercs.exp_pool_a_turn',{x:mcpCardHtml(u.name, (u.gates || []).some(g => g.gate === 'unit' && g.state === 'no') ? false : null),name:esc(u.name),x2:mcpBadge(u.hire),cost:u.cost,exp:u.exp,initial:u.initial,x3:u.max,x4:r[0],x5:r[1]})}
      <span class="sp"></span>
      <button class="rebgo" title="${ttA('mercs.where_else_is_sold',{name:esc(u.name)})}"
        onclick="mcpView('unit');mcpPickUnit('${q1(esc(u.name))}', true)">⇄</button>
      <button class="rebgo" title="${ttA('mercs.edit_this_pool_entry')}"
        onclick="mcpEdit('${q1(esc(pool))}', ${u.index})">✎</button>
    </div>
    ${mcpGatesHtml(u)}
    ${editing ? mcpEditHtml() : ''}
  </div>`;
}

function mcpProvinceHtml(d){
  const k = state.mcp, name = mcpProvince();
  if(!name) return `<div class="count" style="padding:6px 2px">${tt('mercs.click_a_province_on_the_map')}</div>`;
  const low = name.toLowerCase();
  const pools = (d.pools || []).filter(p => p.regions.some(r => r.toLowerCase() === low));
  if(!pools.length) return `<div class="k">${esc(name)}</div>
    <div class="w-warn">${tt('mercs.in_no_pool_so_no_mercenary')}</div>`;
  return `<div class="k">${tt('mercs.unit_lines',{name:esc(name),x:pools.length > 1
      ? 'in ' + pools.length + ' pools' : 'pool ' + esc(pools[0].name),x2:pools.reduce((n, p) => n + p.units.length, 0)})}</div>
    ${pools.map(p => `${pools.length > 1 ? `<div class="k">${esc(p.name)}</div>` : ''}
      ${p.units.map(u => mcpLineHtml(p.name, u)).join('')
        || `<div class="w-warn">${tt('mercs.this_pool_sells_nothing')}</div>`}
      ${mcpAddHtml(p.name)}`).join('')}`;
}

function mcpPoolsHtml(d){
  return `<div class="reblist">${(d.pools || []).map(p => {
    const hire = p.units.filter(u => u.hire === 'yes').length;
    return `<div class="rebrow" style="flex-wrap:wrap">
      <span class="rebnm">${esc(p.name)}</span>
      <span class="count">${tt('mercs.province_line',{regions_n:p.regions.length,regions:p.regions.length === 1 ? '' : 's',units_n:p.units.length,units:p.units.length === 1 ? '' : 's',x:state.mcp.faction ? tt('mercs.hireable_now',{hire}) : ''})}</span>
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
      ${tt('mercs.pool_province',{x:mcpCardHtml(u.name, u.known),name:esc(u.name),x2:u.known === false
        ? `<span class="reborph">${tt('mercs.not_in_the_edu')}</span>` : '',offers_n:u.offers.length,offers:u.offers.length === 1 ? '' : 's',provinces:u.provinces,provinces2:u.provinces === 1 ? '' : 's',price,faction:k.faction ? tt('mercs.hireable',{yes}) : ''})}</button>`;
  }).join('') || `<div class="count" style="padding:6px">${tt('mercs.no_mercenary_matches')}</div>`;
}

function mcpUnitHtml(d){
  const k = state.mcp;
  const u = (d.units || []).find(x => x.name === k.unit);
  return `<input type="search" placeholder="${ttA('mercs.find_a_mercenary')}" value="${esc(k.q)}"
      oninput="mcpSearch(this.value)" style="width:100%">
    <div class="reblist" id="mcpList">${mcpUnitRowsHtml()}</div>
    ${u ? `<div class="rebdet">
      <div class="k">${tt('mercs.sold_by_pool',{name:esc(u.name),offers_n:u.offers.length,offers:u.offers.length === 1 ? '' : 's',prices:u.prices.length > 1
        ? tt('mercs.at_different_prices',{prices_n:u.prices.length}) : ''})}</div>
      <div class="cmbar2"><button onclick="mcpLight('${q1(esc(u.name))}')"
        title="${ttA('mercs.colour_every_province_whose_pool_sells')}">${tt('mercs.light_on_the_map')}</button>
        <label class="mcpauto" title="${ttA('mercs.colour_the_provinces_as_soon_as')}">
          <input type="checkbox" ${k.autoLight ? 'checked' : ''}
            onchange="mcpAutoLight(this.checked)"> ${tt('mercs.light_it_when_picked')}</label></div>
      ${u.offers.map(o => {
        const pool = (d.pools || []).find(p => p.name === o.pool);
        const line = pool && pool.units[o.index];
        return `<div class="mcpoffer"><div class="k">${tt('mercs.province',{pool:esc(o.pool),regions_n:o.regions.length,regions:o.regions.length === 1 ? '' : 's'})}</div>
          ${line ? mcpLineHtml(o.pool, line) : ''}
          <div>${o.regions.map(r => `<button class="rebgo"
            onclick="mcpGo('${q1(esc(r))}')">${esc(r)}</button>`).join(' ')}</div></div>`;
      }).join('')}
    </div>` : `<div class="count" style="padding:6px 2px">${tt('mercs.pick_a_mercenary_to_see_every')}</div>`}`;
}

/* ---------- the pool entry: edit, add, remove ---------- */

const MCP_FIELDS = [
  ['exp', tt('common.experience'), tt('mercs.a_whole_number_0_to_9')],
  ['cost', tt('common.cost'), tt('mercs.what_hiring_one_costs')],
  ['max', tt('mercs.pool_size'), tt('mercs.the_most_the_pool_holds')],
  ['initial', tt('mercs.starts_with'), tt('mercs.how_many_are_there_on_turn')],
  ['replenish', tt('mercs.replenish'), tt('mercs.low_and_high_units_a_turn')],
  ['religions', tt('common.religions'), tt('mercs.blank_takes_the_gate_off_empty')],
  ['factions', tt('common.factions'), tt('mercs.blank_takes_the_gate_off')],
  ['events', tt('common.events'), tt('mercs.blank_takes_the_gate_off')],
  ['start_year', tt('mercs.from_year'), tt('mercs.0_or_blank_for_none')],
  ['end_year', tt('mercs.until_year'), tt('mercs.0_or_blank_for_none')],
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
  return `<div class="mcpform">${[['name', tt('mercs.unit'), tt('mercs.a_unit_type_in_the_edu')]].concat(
      which === 'add' ? [] : []).concat(MCP_FIELDS).map(([key, label, hint]) => {
    if(key === 'name' && which !== 'add') return '';
    return `<label title="${esc(hint)}">${esc(label)}</label>
      <input type="text" value="${esc(w[key])}" placeholder="${esc(hint)}"
        ${key === 'name' ? 'list="mcpEduTypes"' : ''}
        oninput="mcpSet('${which}', '${key}', this.value)">`;
  }).join('')}
    <label>${tt('mercs.crusading')}</label>
    <input type="checkbox" ${w.crusading ? 'checked' : ''}
      onchange="mcpSet('${which}', 'crusading', this.checked)"
      title="${ttA('mercs.only_to_a_crusade_or_jihad')}">
  </div>`;
}

function mcpEditHtml(){
  const k = state.mcp, e = k.edit;
  return `<div class="rebdet">${mcpFieldsHtml('edit', e.w)}
    <div class="cmbar2">
      <button class="bad" onclick="mcpRemove()">${tt('mercs.remove_this_line')}</button>
      <span class="sp"></span>
      <button onclick="mcpEdit('${q1(esc(e.pool))}', ${e.index})">${tt('common.cancel')}</button>
      <button class="primary" onclick="mcpSave()">${tt('common.save')}</button>
    </div></div>`;
}

function mcpAddHtml(pool){
  const k = state.mcp;
  if(k.adding !== pool) return `<div class="cmbar2"><span class="sp"></span>
    <button onclick="mcpAddOpen('${q1(esc(pool))}')">${tt('mercs.sell_another_unit_here')}</button></div>`;
  const types = (k.d && k.d.edu_types) || [];
  return `<div class="rebdet"><div class="k">${tt('mercs.new_line_in',{pool:esc(pool)})}</div>
    ${mcpFieldsHtml('add', k.addForm)}
    <datalist id="mcpEduTypes">${types.map(t => `<option value="${esc(t)}">`).join('')}</datalist>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="mcpAddOpen('${q1(esc(pool))}')">${tt('common.cancel')}</button>
      <button class="primary" onclick="mcpAdd()">${tt('common.add_2')}</button></div></div>`;
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
  if(!confirm(tt('mercs.write',{what,changes:(p.changes || []).join('\n')})
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.join('\n⚠ ') : '')
    + tt('mercs.only_of_this_campaign_is_written',{file:k.d.file})
    + tt('mercs.backed_up_first_and_log_can'))) return;
  k.busy = true;
  try{ res = await api.post('/api/mercpools/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); return; }
  toast(tt('common.saved_log_can_undo_it'), 5000);
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
                 tt('mercs.keep_in_alone',{region,pool}));
}

async function mcpSave(){
  const e = state.mcp.edit;
  if(!e) return;
  const u = mcpLineOf(e.pool, e.index);
  const edits = mcpValues(e.w, true, u);
  if(!Object.keys(edits).length){ toast(tt('mercs.nothing_changed'), 3000); return; }
  await mcpWrite({action: 'unit_edit', pool: e.pool, unit: e.index, edits},
                 `${u.name} in ${e.pool}`);
}

async function mcpRemove(){
  const e = state.mcp.edit;
  if(!e) return;
  const u = mcpLineOf(e.pool, e.index);
  await mcpWrite({action: 'unit_delete', pool: e.pool, unit: e.index},
                 tt('mercs.remove_from',{name:u.name,pool:e.pool}));
}

async function mcpAdd(){
  const k = state.mcp;
  const values = mcpValues(k.addForm, false);
  if(!values.name){ toast(tt('mercs.name_the_unit_first'), 4000); return; }
  await mcpWrite({action: 'unit_add', pool: k.adding, values},
                 tt('mercs.sell_in',{name:values.name,adding:k.adding}));
}
