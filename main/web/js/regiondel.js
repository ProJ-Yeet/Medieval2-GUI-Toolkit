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
const RDL_STANDING = {character: 'character', fort: 'fort',
                      watchtower: 'watchtower', resource: 'resource'};

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
  activity('region delete', `${c.mod}: opened the delete panel for ${c.det.name}`);
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
      {label: `reading what ${k.name} would take with it`});
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
                            {label: `working out what deleting ${k.name} writes`}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.rdl !== k) return;
  k.plan = res.plan || {errors: [res.error || 'the plan came back empty']};
  rdlPaint();
}

async function rdlApply(){
  const k = state.rdl;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  const files = (p.files || []).length + (p.deletes || []).length;
  if(!confirm(`Delete ${k.name}, and give its ${p.tiles.toLocaleString()} tile`
    + `${p.tiles === 1 ? '' : 's'} to ${p.heir || 'nobody'}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + ((p.script || []).length
       ? `\n\n⚠ ${p.script.length} line(s) of the campaign script name `
         + `${k.name} and are NOT edited.` : '')
    + `\n\n${files} file(s). Backed up first, and 🕑 Log can undo it.`)) return;
  k.busy = true;
  rdlPaint();
  let res;
  try{ res = await api.post('/api/map/region_delete_apply', rdlBody(),
                            {label: `deleting ${k.name}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || 'the delete failed'), 9000);
    rdlPaint();
    return;
  }
  toast(`${k.name} deleted, its land is ${res.heir || 'nobody'}'s, `
    + `${(res.files || []).length} file(s) written. map.rwm deleted. `
    + '🕑 Log can undo it.', 7000);
  activity('region delete',
           `${k.mod}: deleted ${k.name}, land to ${res.heir || '(nobody)'}`);
  state.rdl = null;
  const c = state.cmap;
  if(c){ c.det = null; c.sel = null; c.pick = null; }
  await loadCampmap();
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
  if(k.loading) return `<div class="cbrpanel count">reading what
    ${esc(k.name)} would take with it…</div>`;
  const d = k.d || {};
  if(!d.ok) return `<div class="cbrpanel w-bad">${esc(d.error
    || 'that province could not be read')}</div>`;
  return `<div class="cbrpanel">
    <div class="k">Delete ${esc(d.shown || k.name)}
      <span class="count">${d.tiles.toLocaleString()} tile${
        d.tiles === 1 ? '' : 's'}${d.settlement
          ? ` · ${esc(d.settlement)}` : ''}${d.region_id >= 0
          ? ` · region ID ${d.region_id}` : ''}</span></div>
    ${rdlHeirHtml(d)}
    ${rdlPortHtml(d)}
    ${rdlStandingHtml(d)}
    <div class="count">It would be taken out of <code>${esc(d.file)}</code> and
      out of every file ${d.campaigns.length === 1 ? 'the campaign' : 'the '
        + d.campaigns.length + ' campaigns'} reading
      <code>${esc(d.layer)}</code> name${d.campaigns.length === 1 ? 's' : ''}
      it in: the start position, the win conditions, the mercenary pools, the
      music types, the lookup pairs and the custom battle tiles. The campaign
      script is listed and never written.</div>
    <div class="cmbar2">
      <button onclick="rdlPlan()" ${k.busy ? 'disabled' : ''}
        title="Walk the whole mod for every line that names this province. Seconds, and it writes nothing."
        >${k.busy && !k.plan ? 'working it out…' : 'Work out the delete'}</button>
      <span class="sp"></span>
      <button onclick="rdlClose()">Close</button>
    </div>
    ${rdlPlanHtml(k)}
  </div>`;
}

//: Who inherits. A province nothing borders has no answer here and the panel
//: says so rather than offering an empty picker - it is the one case a delete
//: cannot do anything about.
function rdlHeirHtml(d){
  const k = state.rdl;
  if(!d.tiles) return `<div class="w-warn">No tile of
    <code>${esc(d.layer)}</code> is painted this province's colour, so there is
    no land to give away. Deleting it removes the record and everything that
    names it, which is the fix for a record with no tiles.</div>`;
  if(!(d.heirs || []).length) return `<div class="w-bad">${esc(d.name)} shares
    an edge with no declared region, so there is nobody to give its land to. A
    province whose only neighbour is the ocean has to be painted over by
    hand.</div>`;
  return `<div class="cmtrow"><span class="cmtval">
    <span class="cmtnm">Its land goes to</span>
    <select onchange="rdlSet('heir', this.value)">
      ${d.heirs.map(h => `<option value="${esc(h.name)}"${
        h.name === k.heir ? ' selected' : ''}>${esc(h.name)} - ${h.edges}
        shared edge${h.edges === 1 ? '' : 's'}, ${h.tiles.toLocaleString()}
        tiles</option>`).join('')}
    </select></span></div>
    <div class="count">Whole, to one province it touches. Sharing it out tile by
      tile is what would leave the pieces unreachable: two areas that each join
      up and share an edge make one that does.</div>`;
}

//: The port question, which only exists when this province has one. A heir with
//: a port of its own cannot use a second - the engine picks one - so the
//: default follows the heir and changes when the heir does.
function rdlPortHtml(d){
  const k = state.rdl;
  if(!d.port || !d.tiles || !(d.heirs || []).length) return '';
  const h = (d.heirs || []).find(x => x.name === k.heir) || {};
  return `<div class="cmtrow"><span class="cmtval">
    <span class="cmtnm">Its port</span>
    <span class="cmseg">
      <button class="${k.port === 'keep' ? 'on' : ''}"
        onclick="rdlSet('port', 'keep')">Keep it</button>
      <button class="${k.port === 'remove' ? 'on' : ''}"
        onclick="rdlSet('port', 'remove')">Remove it</button>
    </span></span></div>
    <div class="count">${h.port
      ? `${esc(k.heir)} already has a port, and only one of two in a province is
         ever used - so removing this one is the answer that leaves a map the
         validator does not report.`
      : `${esc(k.heir)} has no port of its own, so keeping this one gives it a
         harbour on the coast it is about to inherit.`}</div>`;
}

//: Geomod's own caveat, measured. None of this is orphaned - a fort at 212,88
//: is at 212,88 afterwards - so the panel says what is there and whose it
//: becomes, rather than warning about something that is not going to happen.
function rdlStandingHtml(d){
  const k = state.rdl;
  const rows = d.standing || [];
  if(!rows.length) return '';
  return rows.map(r => `<div class="count">${esc(r.campaign)} puts
    ${Object.keys(r.counts).map(kind => `${r.counts[kind]}
      ${RDL_STANDING[kind] || kind}${r.counts[kind] === 1 ? '' : 's'}`).join(', ')}
    on these tiles. Each one is placed by tile rather than by province, so
    ${r.counts.character || r.counts.resource ? 'they stay where they are and '
      : ''}${k.heir ? esc(k.heir) : 'the heir'} is whose province they stand in
    afterwards.</div>`).join('');
}

function rdlPlanHtml(k){
  const p = k.plan;
  if(!p) return '';
  if((p.errors || []).length) return `<div class="w-bad">
    ${p.errors.map(e => esc(e)).join('<br>')}</div>`;
  const script = p.script || [];
  return `<div class="cbrpanel">
    <div class="k">${(p.files || []).length} file${
      (p.files || []).length === 1 ? '' : 's'} would change
      <span class="count">${(p.deletes || []).length} deleted</span></div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    ${script.length ? `<div class="w-warn">${script.length} line${
      script.length === 1 ? '' : 's'} of the campaign script name
      ${esc(k.name)}, and the script is a grammar nothing here parses - so it is
      listed and never written:</div>
      ${script.slice(0, RDL_SCRIPT_SHOWN).map(m => `<div class="count">
        <code>${esc(m.rel)}</code>:${m.line} ${esc(m.text)}</div>`).join('')}
      ${script.length > RDL_SCRIPT_SHOWN ? `<div class="count">…and
        ${script.length - RDL_SCRIPT_SHOWN} more.</div>` : ''}` : ''}
    <div class="cmbar2">
      <button class="danger" onclick="rdlApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? 'deleting…' : `Delete ${esc(k.name)}`}</button>
      <span class="sp"></span>
      <span class="count">Backed up first. 🕑 Log can undo it.</span>
    </div>
  </div>`;
}
