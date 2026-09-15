/* climates.js - Campaign Map: declaring a climate, and the slot it goes in

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   DECLARE A CLIMATE - Phase 34.

   Every name here starts `ccl`. Python owns every rule - which files are
   written, what clashes, what the battle map knows - and this file asks the one
   question only somebody looking at the map can answer: WHICH SLOT.

   THE PANEL IS A LIST OF TWELVE BEFORE IT IS A FORM. That is the phase's whole
   finding: all four mods measured declare exactly the twelve climates the
   engine ships, `unused1` and `unused2` among them, and not one added a
   thirteenth. So the slots come first, with their colours and their tile
   counts, and the form opens on the one that is clicked. Adding a name is on
   the same panel and below them, because it is the second answer and not the
   first.

   NOTHING IS WRITTEN WITHOUT THE PLAN IN FRONT OF SOMEBODY. The confirm is the
   plan's own changes and warnings, the same rule `rdlApply` follows: this
   reaches four files and the one that matters most - the battle map's
   geography - is a warning rather than a refusal, so it has to be read.

   THE COLOUR PICKER IS THE ONE CONTROL THAT IS NOT A TEXT FIELD, because a
   colour typed as three numbers is a colour nobody can see. It writes the same
   three numbers either way. */

//: How many slots the panel lists before it scrolls. Twelve, which is every
//: climate the engine has - so this is a ceiling that has never been reached
//: and is here so that a mod declaring more does not fill the column.
const CCL_SLOTS_SHOWN = 16;

/* ---------- state ---------- */

function cclNew(mod, campaign){
  return {mod, campaign, open: true, loading: true, d: null, err: '',
          code: '', label: '', rgb: [128, 128, 128], heat: 2, winter: false,
          donor: '', adding: false, plan: null, busy: false};
}

/* Open the panel. Unlike the delete, this reads as soon as it is opened: the
   view is a parse of two text files and a census of one layer, which is the
   same cost the layer legend already pays, and the list of slots IS the
   panel. */
function cclOpen(){
  const c = state.cmap;
  if(!c) return;
  const k = state.ccl;
  if(k && k.open && k.mod === c.mod && k.campaign === (c.campaign || '')){
    cclPaint();
    return;
  }
  state.ccl = null;
  cclPaint();
}

function cclToggle(){
  const c = state.cmap;
  if(!c) return;
  if(state.ccl){ state.ccl = null; cclPaint(); return; }
  state.ccl = cclNew(c.mod, c.campaign || '');
  activity('climates', `${c.mod}: opened the climates panel`);
  cclPaint();
  cclLoad();
}

async function cclLoad(){
  const k = state.ccl;
  if(!k) return;
  let d;
  try{
    d = await api.get(`/api/map/climates?mod=${enc(k.mod)}`
      + (k.campaign ? `&campaign=${enc(k.campaign)}` : ''),
      {label: 'reading this mod’s climates'});
  }catch(e){ d = {have: false, problem: errText(e), slots: [], donors: []}; }
  if(state.ccl !== k) return;
  k.loading = false;
  k.d = d;
  k.donor = (d.donors && d.donors[0]) ? d.donors[0].code : '';
  cclPaint();
}

/* Pick a slot to take over. Everything it already has is loaded into the form -
   its colour, its heat, its winter flag and its display name - so that changing
   one of the five does not silently reset the other four. */
function cclPick(code){
  const k = state.ccl;
  if(!k || !k.d) return;
  const s = (k.d.slots || []).find(x => x.code === code);
  if(!s) return;
  k.adding = false;
  k.code = s.code;
  k.label = s.label || '';
  k.rgb = (s.rgb || [128, 128, 128]).slice();
  k.heat = s.heat;
  k.winter = !!s.winter;
  k.plan = null;
  cclPaint();
}

//: The other road. Kept a separate control rather than a thirteenth row,
//: because the list is the twelve the engine has and a new name is not one.
function cclAdd(){
  const k = state.ccl;
  if(!k) return;
  k.adding = true;
  k.code = '';
  k.label = '';
  k.heat = 2;
  k.winter = false;
  k.plan = null;
  cclPaint();
}

function cclSet(field, value){
  const k = state.ccl;
  if(!k) return;
  if(field === 'heat') value = Math.max(0, Math.min(4, parseInt(value, 10) || 0));
  if(field === 'winter') value = !!value;
  k[field] = value;
  k.plan = null;                    // it was worked out for different answers
  cclPaint();
}

//: The picker and the three numbers are one value. `#rrggbb` is what an
//: `<input type=color>` speaks and `r g b` is what the file does, so the
//: conversion lives here and the plan only ever sees the three numbers.
function cclSetHex(hex){
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if(!m) return;
  const n = parseInt(m[1], 16);
  cclSet('rgb', [(n >> 16) & 255, (n >> 8) & 255, n & 255]);
}

function cclHex(rgb){
  return '#' + (rgb || [0, 0, 0]).map(
    v => Math.max(0, Math.min(255, v | 0)).toString(16).padStart(2, '0')).join('');
}

function cclBody(){
  const k = state.ccl;
  return {mod: k.mod, campaign: k.campaign, code: k.code.trim(),
          label: k.label.trim(), colour: k.rgb, heat: k.heat,
          winter: k.winter, donor: k.donor};
}

/* ---------- the plan, and the save ---------- */

async function cclPlan(){
  const k = state.ccl;
  if(!k || k.busy || !k.code.trim()) return;
  k.busy = true; k.plan = null;
  cclPaint();
  let res;
  try{ res = await api.post('/api/map/climate_plan', cclBody(),
                            {label: `working out what declaring ${k.code} writes`}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.ccl !== k) return;
  k.plan = res.plan || {errors: [res.error || 'the plan came back empty']};
  cclPaint();
}

async function cclApply(){
  const k = state.ccl;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(`${p.mode === 'add' ? 'Declare' : 'Take over'} climate ${p.code}`
    + ` in ${k.mod}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n\n') : '')
    + `\n\n${(p.files || []).length} file(s)${p.keys && p.keys.length
        ? ' and the display name' : ''}. Backed up first, and 🕑 Log `
    + 'can undo it.\n\nmap_climates.tga is NOT written: the brush paints the '
    + 'climate once it is declared.')) return;
  k.busy = true;
  cclPaint();
  let res;
  try{ res = await api.post('/api/map/climate_apply', cclBody(),
                            {label: `declaring ${k.code}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || 'the climate was not written'), 9000);
    cclPaint();
    return;
  }
  toast(`${p.code} ${p.mode === 'add' ? 'declared' : 'taken over'}, `
    + `${(res.files || []).length} file(s) written. Paint it with the climates `
    + 'layer. 🕑 Log can undo it.', 7000);
  activity('climates',
           `${k.mod}: ${p.mode === 'add' ? 'declared' : 'took over'} ${p.code}`);
  k.plan = null;
  await loadCampmap();
}

/* ---------- drawing ---------- */

function cclPaint(){
  const el = document.getElementById('cmClim');
  if(!el) return;
  el.innerHTML = cclHtml();
}

function cclHtml(){
  const k = state.ccl;
  if(!k || !k.open) return `<div class="cbrpanel">
    <div class="cmbar2">
      <button onclick="cclToggle()" title="Which climates this mod declares,
which of the twelve slots are spare, and what declaring one writes"
        >Climates…</button>
      <span class="sp"></span>
      <span class="count">four files, and no pixels</span>
    </div></div>`;
  if(k.loading) return `<div class="cbrpanel count">reading
    <code>descr_climates.txt</code>…</div>`;
  const d = k.d || {};
  if(!d.have) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.problem || 'the climates could not be read')}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="cclToggle()">Close</button></div></div>`;
  return `<div class="cbrpanel">
    <div class="k">Climates
      <span class="count">${(d.slots || []).length} declared ·
        ${(d.grounds || []).length} ground types ·
        <code>${esc(d.file)}</code></span></div>
    ${cclSlotsHtml(d)}
    ${cclGeogHtml(d)}
    ${cclFormHtml(k, d)}
    <div class="cmbar2">
      <span class="sp"></span>
      <button onclick="cclToggle()">Close</button>
    </div>
  </div>`;
}

//: The twelve, with the two facts that decide which one to take: how many tiles
//: already carry its colour, and whether it has a texture block. A spare name
//: is marked, and a spare name on no tiles is the free one.
function cclSlotsHtml(d){
  const k = state.ccl;
  const rows = (d.slots || []).slice(0, CCL_SLOTS_SHOWN);
  return `<div class="cclslots">${rows.map(s => `<button
    class="cclslot${k.code === s.code && !k.adding ? ' on' : ''}${
      s.spare ? ' spare' : ''}"
    onclick="cclPick('${esc(s.code)}')"
    title="${esc(s.code)} · index ${s.index} · heat ${s.heat}${
      s.winter ? ' · winter of its own' : ' · drawn in its summer textures all year'}${
      s.aerial ? ` · ${s.grounds} ground types` : ' · NO texture block'}">
    <span class="cclsw" style="background:${cclHex(s.rgb)}"></span>
    <span class="cclnm">${esc(s.label || s.code)}${
      s.spare ? '<span class="cclfree">spare</span>' : ''}</span>
    <span class="count">${s.tiles.toLocaleString()} tile${
      s.tiles === 1 ? '' : 's'}${s.aerial ? '' : ' · no textures'}</span>
  </button>`).join('')}</div>
  ${(d.free || []).length ? `<div class="count">${
    d.free.map(c => `<code>${esc(c)}</code>`).join(' and ')} ${
    d.free.length === 1 ? 'is' : 'are'} spare by name and on no tile of this
    map, so taking ${d.free.length === 1 ? 'it' : 'one'} over changes
    nothing that is drawn today.</div>`
  : `<div class="count">Both spare names are already painted on this map, so
     taking one over renames tiles somebody put there on purpose. The counts
     above are how many.</div>`}
  <div class="cmbar2">
    <button class="${k.adding ? 'on' : ''}" onclick="cclAdd()"
      title="Append a name the engine does not ship. The strat map draws it; the
battle map reads climates by name, which is what the warning is about."
      >Add a new name instead…</button>
  </div>`;
}

//: The battle map's own file, and the three states it comes in. This is the one
//: thing on the panel that is not about the picture, and it is why the list
//: above is the first answer.
function cclGeogHtml(d){
  const g = d.geography || {};
  if(g.have) return `<div class="count"><code>${esc(g.file)}</code> gives a
    block to ${g.names.length} climate${g.names.length === 1 ? '' : 's'} by
    name, which is what the battle map reads. A name that is not one of them
    is a crash when a battle starts in a province painted with it.</div>`;
  return `<div class="w-warn">${esc(g.problem || '')} Taking over one of the
    twelve the engine ships needs no such check.</div>`;
}

function cclFormHtml(k, d){
  if(!k.code && !k.adding) return `<div class="count">Pick a slot above to take
    it over, or add a name.</div>`;
  const heat = [0, 1, 2, 3, 4];
  return `<div class="cclform">
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Name the engine reads</span>
      ${k.adding
        ? `<input value="${esc(k.code)}" placeholder="frozen_arctic"
             oninput="cclSet('code', this.value)">`
        : `<code>${esc(k.code)}</code>`}</span></div>
    ${k.adding ? `<div class="count">A bare word: a letter first, then letters,
      digits or underscores. It is read out of four files under this name.</div>`
      : `<div class="count">A take-over keeps the slot's name and its place in
        the list, which is the index the engine reads. Only its colour, its
        heat, its winter and its textures change.</div>`}
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Display name</span>
      <input value="${esc(k.label)}" placeholder="(its code name)"
        oninput="cclSet('label', this.value)"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Colour in <code>map_climates.tga</code></span>
      <input type="color" value="${cclHex(k.rgb)}"
        oninput="cclSetHex(this.value)">
      <span class="count">${k.rgb.join(' ')}</span></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Heat</span>
      <span class="cmseg">${heat.map(h => `<button class="${
        k.heat === h ? 'on' : ''}" onclick="cclSet('heat', ${h})">${h}</button>`
        ).join('')}</span></span></div>
    <div class="count">The armour-fatigue effect. Zero means none at all, which
      is the file's own header comment.</div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Winter</span>
      <span class="cmseg">
        <button class="${k.winter ? 'on' : ''}"
          onclick="cclSet('winter', true)">Its own</button>
        <button class="${!k.winter ? 'on' : ''}"
          onclick="cclSet('winter', false)">Summer all year</button>
      </span></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Textures copied from</span>
      <select onchange="cclSet('donor', this.value)">
        ${(d.donors || []).map(x => `<option value="${esc(x.code)}"${
          x.code === k.donor ? ' selected' : ''}>${esc(x.code)} –
          ${x.grounds} ground type${x.grounds === 1 ? '' : 's'}</option>`
          ).join('')}
      </select></span></div>
    <div class="count">A climate with no textures is pink on every tile it is
      painted on, so a new block is copied from one that already draws - both
      seasons, every ground type this mod's own blocks name.</div>
    ${cclDonorNote(k, d)}
    <div class="cmbar2">
      <button onclick="cclPlan()" ${k.busy || !k.code.trim() ? 'disabled' : ''}
        title="Work out all four files. It writes nothing."
        >${k.busy && !k.plan ? 'working it out…' : 'Work out the writes'}</button>
    </div>
    ${cclPlanHtml(k)}
  </div>`;
}

//: The one thing about the donor that is not obvious from its name. `default`
//: is the AERIAL file's fallback block and not a declared climate, so it has no
//: strategy tree models and no battle vegetation to give - and it is the first
//: donor offered, so it is the likeliest thing to be picked. Python raises the
//: same fact on the plan; this is on the control itself, before the plan is
//: asked for, because it is a choice rather than a consequence.
function cclDonorNote(k, d){
  if(k.adding !== true) return '';
  const named = (d.slots || []).some(s => s.code === k.donor);
  if(named) return '';
  return `<div class="w-warn"><code>${esc(k.donor)}</code> is a block of
    <code>${esc((d.aerial || {}).file || 'the aerial file')}</code> and not a
    declared climate, so it has no tree models, no battle vegetation and no env
    map to copy. The new climate would draw its ground and have no trees on it.
    Pick one of the ${(d.slots || []).length} climates to get all three.</div>`;
}

function cclPlanHtml(k){
  const p = k.plan;
  if(!p) return '';
  if((p.errors || []).length) return `<div class="w-bad">
    ${p.errors.map(e => esc(e)).join('<br>')}</div>`;
  // the localisation is a file too, and it is not in `files` - that list is the
  // texts written whole, and the display name goes through a road of its own
  // that may end in a .strings.bin. Counting it here is what makes the number
  // agree with the rows under it.
  const n = (p.files || []).length + ((p.keys || []).length ? 1 : 0);
  return `<div class="cbrpanel">
    <div class="k">${n} file${n === 1 ? '' : 's'} would change
      <span class="count">${p.mode === 'add' ? 'a new name' : 'a slot taken over'}
        · ${(p.grounds || []).length} ground types</span></div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    <div class="cmbar2">
      <button onclick="cclApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? 'writing…' : `Declare ${esc(p.code)}`}</button>
      <span class="sp"></span>
      <span class="count">Backed up first. 🕑 Log can undo it.</span>
    </div>
  </div>`;
}
