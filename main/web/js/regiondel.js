/* regiondel.js - Campaign Map: deleting a province, and who gets its land

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   DELETE A PROVINCE - Phase 24, G1.

   Every name here starts `rdl`. The rules are all Python's - which neighbours
   could inherit the land, what is written where, what is refused - and this
   file asks the two questions that have an answer only somebody looking at the
   map can give: who inherits, and what happens to the port.

   THE PANEL IS TWO STEPS AND THE SECOND ONE IS THE EXPENSIVE ONE. Opening it
   is a read of the map object that is already in memory, so it appears; working
   the delete out walks the whole mod looking for every line that names the
   province, which is seconds on a cold disk. So the heirs, the tiles and what
   stands on the land come back on the click that opens this, and the list of
   files comes back on a button that says it is going to think.

   NOTHING IS DELETED WITHOUT THE LIST IN FRONT OF SOMEBODY. The confirm is the
   plan's own changes and warnings, not a sentence about them, because a delete
   reaches up to a dozen files in two campaigns and no shorter summary of that
   is honest. The campaign script is the one thing this will not edit, and the
   lines it found are shown before the confirm rather than after it.
   ===================================================================== */

//: How many script lines the panel prints before it stops and counts. A long
//: script naming a province forty times is the case this exists for, and forty
//: lines in a side panel is a wall.
const RDL_SCRIPT_SHOWN = 6;

//: What each kind standing on the province's tiles is called in a sentence.
const RDL_STANDING = {character: 'regiondel.standing_character', fort: 'regiondel.standing_fort',
                      watchtower: 'regiondel.standing_watchtower', resource: 'regiondel.standing_resource'};

/* ---------- state ---------- */

function rdlNew(mod, campaign, name){
  return {mod, campaign, name, open: true, loading: true, err: '',
          d: null, heir: '', port: '', plan: null, busy: false};
}

/* Open the panel for the province the region form is showing.

   It is deliberately not opened by clicking the map: a delete is not something
   to arrive at by accident, and the button that gets here sits on the same bar
   as Save. */
function rdlOpen(){
  const c = state.cmap;
  if(!c || !c.det || !c.det.name) return;
  const k = state.rdl;
  if(k && k.open && k.name === c.det.name && k.mod === c.mod){
    rdlClose();
    return;
  }
  state.rdl = rdlNew(c.mod, c.campaign || '', c.det.name);
  activity(tt('regiondel.region_delete'), tt('regiondel.opened_the_delete_panel_for',{mod:c.mod,name:c.det.name}));
  rdlPaint();
  rdlLoad();
}

function rdlClose(){
  state.rdl = null;
  rdlPaint();
}

async function rdlLoad(){
  const k = state.rdl;
  if(!k) return;
  let d;
  try{
    d = await api.get(`/api/map/region_delete?mod=${enc(k.mod)}`
      + `&name=${enc(k.name)}`
      + (k.campaign ? `&campaign=${enc(k.campaign)}` : ''),
      {label: tt('regiondel.reading_what_would_take_with_it',{name:k.name})});
  }catch(e){ d = {ok: false, error: errText(e), heirs: [], standing: []}; }
  if(state.rdl !== k) return;
  k.loading = false;
  k.d = d;
  k.heir = (d.heirs && d.heirs[0]) ? d.heirs[0].name : '';
  // the default the server would pick, shown rather than hidden: a heir with a
  // port of its own cannot take a second one
  k.port = !d.port ? ''
    : ((d.heirs || []).find(h => h.name === k.heir) || {}).port ? 'remove' : 'keep';
  rdlPaint();
}

function rdlSet(field, value){
  const k = state.rdl;
  if(!k) return;
  k[field] = value;
  if(field === 'heir' && k.d && k.d.port){
    const h = (k.d.heirs || []).find(x => x.name === value) || {};
    k.port = h.port ? 'remove' : 'keep';
  }
  k.plan = null;                      // it was worked out for a different answer
  rdlPaint();
}

function rdlBody(){
  const k = state.rdl;
  return {mod: k.mod, campaign: k.campaign, name: k.name,
          heir: k.heir, port: k.port};
}

/* ---------- the plan, and the save ---------- */

async function rdlPlan(){
  const k = state.rdl;
  if(!k || k.busy) return;
  k.busy = true; k.plan = null;
  rdlPaint();
  let res;
  try{ res = await api.post('/api/map/region_delete_plan', rdlBody(),
                            {label: tt('regiondel.working_out_what_deleting_writes',{name:k.name})}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.rdl !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  rdlPaint();
}

async function rdlApply(){
  const k = state.rdl;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  const files = (p.files || []).length + (p.deletes || []).length;
  const detail = `${(p.changes || []).join('\n')}${
    (p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : ''}${
    (p.script || []).length ? tt('regiondel.confirm_script_lines',{script_n:p.script.length,name:k.name}) : ''}`;
  if(!confirm(ttN('regiondel.confirm_delete',p.tiles,{name:k.name,heir:p.heir || 'nobody',detail,files}))) return;
  k.busy = true;
  rdlPaint();
  let res;
  try{ res = await api.post('/api/map/region_delete_apply', rdlBody(),
                            {label: `deleting ${k.name}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('regiondel.the_delete_failed')), 9000);
    rdlPaint();
    return;
  }
  toast(tt('regiondel.deleted_toast',{name:k.name,heir:res.heir || 'nobody',n:(res.files || []).length}), 7000);
  activity(tt('regiondel.region_delete'),
           tt('regiondel.deleted_land_to',{mod:k.mod,name:k.name,x:res.heir || '(nobody)'}));
  state.rdl = null;
  const c = state.cmap;
  if(c){ c.det = null; c.sel = null; c.pick = null; }
  await loadCampmap(true);
}

/* ---------- drawing ---------- */

function rdlPaint(){
  const el = document.getElementById('cmDel');
  if(!el) return;
  el.innerHTML = rdlHtml();
}

function rdlHtml(){
  const k = state.rdl;
  if(!k || !k.open) return '';
  if(k.loading) return `<div class="cbrpanel count">${tt('regiondel.reading_what_would_take_with_it_2',{name:esc(k.name)})}</div>`;
  const d = k.d || {};
  if(!d.ok) return `<div class="cbrpanel w-bad">${esc(d.error
    || tt('regiondel.that_province_could_not_be_read'))}</div>`;
  return `<div class="cbrpanel">
    <div class="k">${ttN('regiondel.delete_tile_counted',d.tiles,{shown:esc(d.shown || k.name),settlement:d.settlement
          ? ` · ${esc(d.settlement)}` : '',region_id:d.region_id >= 0
          ? tt('regiondel.region_id',{region_id:d.region_id}) : ''})}</div>
    ${rdlHeirHtml(d)}
    ${rdlPortHtml(d)}
    ${rdlStandingHtml(d)}
    <div class="count">${ttN('regiondel.taken_out_of_campaigns',d.campaigns.length,{file:esc(d.file),layer:esc(d.layer)})}</div>
    <div class="cmbar2">
      <button onclick="rdlPlan()" ${k.busy ? 'disabled' : ''}
        title="${ttA('regiondel.walk_the_whole_mod_for_every')}"
        >${k.busy && !k.plan ? tt('common.working_it_out') : tt('regiondel.work_out_the_delete')}</button>
      <span class="sp"></span>
      <button onclick="rdlClose()">${tt('common.close')}</button>
    </div>
    ${rdlPlanHtml(k)}
  </div>`;
}

//: Who inherits. A province nothing borders has no answer here and the panel
//: says so rather than offering an empty picker - it is the one case a delete
//: cannot do anything about.
function rdlHeirHtml(d){
  const k = state.rdl;
  if(!d.tiles) return `<div class="w-warn">${tt('regiondel.no_tile_of_is_painted_this',{layer:esc(d.layer)})}</div>`;
  if(!(d.heirs || []).length) return `<div class="w-bad">${tt('regiondel.shares_an_edge_with_no_declared',{name:esc(d.name)})}</div>`;
  return `<div class="cmtrow"><span class="cmtval">
    <span class="cmtnm">${tt('regiondel.its_land_goes_to')}</span>
    <select onchange="rdlSet('heir', this.value)">
      ${d.heirs.map(h => `<option value="${esc(h.name)}"${
        h.name === k.heir ? ' selected' : ''}>${ttN('regiondel.shared_edge_tiles_counted',h.edges,{name:esc(h.name),tiles:h.tiles.toLocaleString()})}</option>`).join('')}
    </select></span></div>
    <div class="count">${tt('regiondel.whole_to_one_province_it_touches')}</div>`;
}

//: The port question, which only exists when this province has one. A heir with
//: a port of its own cannot use a second - the engine picks one - so the
//: default follows the heir and changes when the heir does.
function rdlPortHtml(d){
  const k = state.rdl;
  if(!d.port || !d.tiles || !(d.heirs || []).length) return '';
  const h = (d.heirs || []).find(x => x.name === k.heir) || {};
  return `<div class="cmtrow"><span class="cmtval">
    ${tt('regiondel.its_port')}
      <button class="${k.port === 'keep' ? 'on' : ''}"
        onclick="rdlSet('port', 'keep')">${tt('common.keep_it')}</button>
      <button class="${k.port === 'remove' ? 'on' : ''}"
        onclick="rdlSet('port', 'remove')">${tt('regiondel.remove_it')}</button>
    </span></span></div>
    <div class="count">${h.port
      ? tt('regiondel.already_has_a_port_and_only',{heir:esc(k.heir)})
      : tt('regiondel.has_no_port_of_its_own',{heir:esc(k.heir)})}</div>`;
}

//: Geomod's own caveat, measured. None of this is orphaned - a fort at 212,88
//: is at 212,88 afterwards - so the panel says what is there and whose it
//: becomes, rather than warning about something that is not going to happen.
function rdlStandingHtml(d){
  const k = state.rdl;
  const rows = d.standing || [];
  if(!rows.length) return '';
  return rows.map(r => `<div class="count">${tt(r.counts.character || r.counts.resource ? 'regiondel.puts_on_tiles_stay' : 'regiondel.puts_on_tiles',
      {campaign:esc(r.campaign),kinds:Object.keys(r.counts).map(kind => RDL_STANDING[kind]
        ? ttN(RDL_STANDING[kind], r.counts[kind]) : `${r.counts[kind]}\n      ${kind}`).join(', '),
      heir:k.heir ? esc(k.heir) : tt('regiondel.the_heir')})}</div>`).join('');
}

function rdlPlanHtml(k){
  const p = k.plan;
  if(!p) return '';
  if((p.errors || []).length) return `<div class="w-bad">
    ${p.errors.map(e => esc(e)).join('<br>')}</div>`;
  const script = p.script || [];
  return `<div class="cbrpanel">
    <div class="k">${ttN('regiondel.files_would_change',(p.files || []).length,{deleted:(p.deletes || []).length})}</div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    ${script.length ? `<div class="w-warn">${ttN('regiondel.script_lines_name',script.length,{name:esc(k.name)})}</div>
      ${script.slice(0, RDL_SCRIPT_SHOWN).map(m => `<div class="count">
        <code>${esc(m.rel)}</code>:${m.line} ${esc(m.text)}</div>`).join('')}
      ${script.length > RDL_SCRIPT_SHOWN ? `<div class="count">${tt('regiondel.and_more',{x:script.length - RDL_SCRIPT_SHOWN})}</div>` : ''}` : ''}
    <div class="cmbar2">
      <button class="danger" onclick="rdlApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? tt('regiondel.deleting') : tt('regiondel.delete',{name:esc(k.name)})}</button>
      <span class="sp"></span>
      <span class="count">${tt('regiondel.backed_up_first_log_can_undo')}</span>
    </div>
  </div>`;
}
