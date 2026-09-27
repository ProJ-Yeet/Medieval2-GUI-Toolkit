/* edbimport.js - Buildings: building lines brought in from another mod

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   BUILDING LINES FROM ANOTHER MOD - Phase 76.

   Every name here starts `bim`. It opens from the Buildings screen's header,
   beside New building tree. Pick a mod, tick lines, Probe: the server maps
   every faction and culture this mod lacks (each one can be re-pointed here),
   leaves out the recruit pools for units this mod lacks and names them, and
   refuses what the game would refuse, saying which line to add. One Undo.
   ===================================================================== */

function bimOpen(){
  state.bim = {from: '', lines: null, targets: null, picked: [], filter: '',
               replace: false, map: {}, plan: null, stale: false, busy: false, err: ''};
  overlay.classList.add('open');
  document.getElementById('modal').className = 'modal wide';
  bimPaint();
}

function bimClose(){ state.bim = null; closeModal(); }

async function bimFrom(src){
  const k = state.bim;
  if(!k) return;
  Object.assign(k, {from: src, lines: null, targets: null, picked: [], map: {},
                    plan: null, err: ''});
  bimPaint();
  if(!src) return;
  try{
    const r = await api.get(`/api/edbimport/lines?mod=${enc(state.src)}&from=${enc(src)}`,
                            {label: tt('edbimport.reading_s_building_lines',{src})});
    if(state.bim !== k || k.from !== src) return;
    k.lines = r.lines || [];
    k.targets = r.targets || {factions: [], cultures: []};
  }catch(e){
    if(state.bim !== k) return;
    k.err = errText(e);
  }
  bimPaint();
}

function bimToggle(name){
  const k = state.bim;
  const i = k.picked.indexOf(name);
  i < 0 ? k.picked.push(name) : k.picked.splice(i, 1);
  k.stale = !!k.plan;
  bimPaint();
}

//: the filter repaints only the list, so the caret stays in the box
function bimFilter(v){
  state.bim.filter = v;
  const box = document.getElementById('bimList');
  if(box) box.innerHTML = bimListHtml(state.bim);
}

function bimSet(key, value){
  const k = state.bim;
  k[key] = value;
  k.stale = !!k.plan;
  bimPaint();
}

function bimMap(name, to){
  const k = state.bim;
  k.map[name.toLowerCase()] = to;
  k.stale = !!k.plan;
  bimPaint();
}

//: the plan said "add the 'x' line to the import" - one click does
function bimAdd(name){
  const k = state.bim;
  if(!k.picked.includes(name)) k.picked.push(name);
  bimPlan();
}

function bimBody(){
  const k = state.bim;
  return {mod: state.src, from: k.from, lines: k.picked, replace: k.replace,
          map: k.map, clear_strings_bin: clearBinOn()};
}

async function bimPlan(){
  const k = state.bim;
  if(!k || k.busy || !k.picked.length) return;
  k.busy = true; bimPaint();
  let res;
  try{ res = await api.post('/api/edbimport/plan', bimBody(),
                            {label: tt('edbimport.working_out_the_building_lines')}); }
  catch(e){ res = {plan: {errors: [errText(e)]}}; }
  finally{ k.busy = false; }
  if(state.bim !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  k.stale = false;
  bimPaint();
}

async function bimApply(){
  const k = state.bim;
  if(!k || k.busy || !k.plan || !k.plan.ok || k.stale) return;
  k.busy = true; bimPaint();
  let res;
  try{ res = await api.post('/api/edbimport/apply', bimBody(),
                            {label: tt('edbimport.bringing_across',{picked:k.picked.join(', ')})}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('common.the_import_failed')), 9000);
    if(res && res.plan) k.plan = res.plan;
    bimPaint();
    return;
  }
  toast(tt('edbimport.brought_in_from_log_can_undo',{picked:k.picked.join(', '),x:k.from}), 7000);
  activity(tt('edbimport.building_import'), tt('edbimport.from',{src:state.src,picked:k.picked.join(', '),x:k.from}));
  const first = k.picked[0];
  state.bim = null;
  closeModal();
  await loadBuildings(true);
  _bldFiltersFor = '';
  render();
  await openBuilding(first);
}

/* ---------- drawing ---------- */

function bimListHtml(k){
  if(!k.lines) return `<div class="count">${k.from ? tt('common.reading_2') : ''}</div>`;
  const f = (k.filter || '').trim().toLowerCase();
  const rows = k.lines.filter(l => !f || l.name.toLowerCase().includes(f)
    || (l.label || '').toLowerCase().includes(f)
    || l.levels.some(x => x.toLowerCase().includes(f)));
  if(!rows.length) return `<div class="count">${tt('edbimport.no_line_matches')}</div>`;
  return rows.map(l => `<label class="bimrow" title="${esc(l.levels.join(' → '))}">
      <input type="checkbox" ${k.picked.includes(l.name) ? 'checked' : ''}
        onchange="bimToggle('${q1(esc(l.name))}')">
      <code>${esc(l.name)}</code>
      ${tt('edbimport.level',{label:esc(l.label || ''),levels_n:l.levels.length,levels:l.levels.length === 1 ? '' : 's',units:l.units ? tt('edbimport.unit',{units:l.units,units2:l.units === 1 ? '' : 's'}) : '',in_dest:l.in_dest ? `<span class="w-warn">${tt('edbimport.in_too',{src:esc(state.src)})}</span>` : ''})}
    </label>`).join('');
}

function bimTargetOptions(k, to){
  const t = k.targets || {factions: [], cultures: []};
  const opt = v => `<option value="${esc(v)}"${v === to ? ' selected' : ''}>${esc(v)}</option>`;
  return `<option value=""${to ? '' : ' selected'}>${tt('edbimport.left_out')}</option>
    <optgroup label="cultures">${t.cultures.map(opt).join('')}</optgroup>
    <optgroup label="factions">${t.factions.map(f => opt(f.name)).join('')}</optgroup>`;
}

function bimPlanHtml(k, p){
  const adds = [];
  (p.errors || []).forEach(e => {
    const m = /add the '([^']+)' line to the import/.exec(e);
    if(m && !k.picked.includes(m[1]) && !adds.includes(m[1])) adds.push(m[1]);
  });
  const names = p.names || [];
  const units = p.units_left || [];
  // a refusal is the whole answer, so it is shown rather than folded away
  const head = (p.errors || []).length
    ? `<div class="sum" style="margin-top:14px">${p.errors.map(e => `<div class="srow bad">
        <span class="sicon">✕</span><span class="stext">${esc(e)}</span></div>`).join('')}</div>`
    : bldPlanHtml(p, k.stale, 'bim.probe');
  return `${head}
    ${adds.length ? `<div class="cmbar2">${adds.map(n =>
      `<button onclick="bimAdd('${q1(esc(n))}')">${tt('edbimport.add',{x:esc(n)})}</button>`).join('')}</div>` : ''}
    ${names.length ? `<div class="bsec"><h4>${tt('edbimport.names_does_not_have',{src:esc(state.src)})}
        <span class="n">${names.length}</span></h4>
      <div class="bnote">${tt('edbimport.each_is_mapped_onto_one_of')}</div>
      <div class="bimmap">${names.map(n => `<div>
        <code>${esc(n.name)}</code>
        <span class="count">${tt('edbimport.named',{kind:esc(n.kind),culture:n.culture ? ` of ${esc(n.culture)}` : '',uses:n.uses})}</span>
        <select onchange="bimMap('${q1(esc(n.name))}',this.value)">${bimTargetOptions(k, n.to)}</select>
      </div>`).join('')}</div></div>` : ''}
    ${units.length ? `<div class="bsec ${foldCls('bim.units')}" data-fold="bim.units">
      <h4>${tt('edbimport.units_does_not_have',{src:esc(state.src)})} <span class="n">${units.length}</span></h4>
      <div class="bnote">${tt('edbimport.their_recruit_pools_are_left_out')}</div>
      <div class="ntslots">${units.map(u => `<div>${tt('edbimport.pool',{unit:esc(u.unit),pools:u.pools,pools2:u.pools === 1 ? '' : 's'})}</div>`).join('')}</div>
    </div>` : ''}
    ${(p.pictures || []).length ? `<div class="bsec ${foldCls('bim.pics')}" data-fold="bim.pics">
      <h4>${tt('edbimport.building_cards')} <span class="n">${p.pictures.length}</span></h4>
      <div class="ntslots">${p.pictures.map(r => `<div><code>data/${esc(r)}</code></div>`).join('')}</div>
    </div>` : ''}`;
}

function bimPaint(){
  const k = state.bim;
  if(!k) return;
  const others = (state.mods || []).map(m => m.name).filter(n => n !== state.src);
  const clash = (k.lines || []).some(l => l.in_dest && k.picked.includes(l.name));
  const p = k.plan;
  document.getElementById('modal').innerHTML = `<h2>${tt('edbimport.building_lines_from_another_mod_into',{src:esc(state.src)})}</h2>
    <div class="mbody">
      <div class="brow">
        <label style="flex:0 0 260px">${tt('common.from')}
          <select onchange="bimFrom(this.value)">
            <option value="">${tt('edbimport.pick_a_mod')}</option>
            ${others.map(n => `<option value="${esc(n)}"${n === k.from ? ' selected' : ''}>${esc(n)}</option>`).join('')}
          </select></label>
        ${k.lines ? `<label style="flex:1 1 220px">${tt('common.find')}
          <input value="${esc(k.filter)}" placeholder="${ttA('edbimport.a_line_a_level_or_a')}"
            oninput="bimFilter(this.value)"></label>` : ''}
      </div>
      ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
      ${k.from ? `<div class="bsec"><h4>${tt('edbimport.lines_picked',{picked_n:k.picked.length})}</h4>
        <div id="bimList" class="bimlist">${bimListHtml(k)}</div></div>` : ''}
      ${clash ? `<label class="bimrow"><input type="checkbox" ${k.replace ? 'checked' : ''}
          onchange="bimSet('replace',this.checked)">
        ${tt('edbimport.replace_the_line_of_the_same',{picked:k.picked.length === 1 ? '' : 's',src:esc(state.src)})}</label>` : ''}
      ${k.from ? `<div class="bnote">${docPoints(tt('edbimport.what_comes_across'), [
        tt('edbimport.each_line_whole_every_faction_and'),
        tt('edbimport.its_text_keys_in_text_export'),
        tt('edbimport.recruit_pools_for_units_this_mod'),
        tt('edbimport.a_hidden_resource_this_mod_lacks')])}</div>` : ''}
      <div id="bimPlan">${p ? bimPlanHtml(k, p) : ''}</div>
    </div>
    <div class="foot">
      <button onclick="bimClose()">${tt('common.cancel')}</button>
      <button onclick="bimPlan()" ${k.busy || !k.picked.length ? 'disabled' : ''}
        >${k.busy && !p ? tt('common.working_it_out') : tt('common.probe')}</button>
      <button class="primary" onclick="bimApply()"
        ${k.busy || !p || !p.ok || k.stale ? 'disabled' : ''}
        >${k.busy && p ? tt('common.writing') : tt('edbimport.bring_them_in')}</button>
    </div>`;
}
