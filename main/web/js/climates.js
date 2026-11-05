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
  activity('climates', tt('climates.opened_the_climates_panel',{mod:c.mod}));
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
      {label: tt('climates.reading_this_mods_climates')});
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
                            {label: tt('climates.working_out_what_declaring_writes',{code:k.code})}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.ccl !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  cclPaint();
}

async function cclApply(){
  const k = state.ccl;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(tt(p.mode === 'add' ? 'climates.declare_climate_in_mod' : 'climates.take_over_climate_in_mod',{code:p.code,mod:k.mod,
      changes:(p.changes || []).join('\n'),
      warnings:(p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n\n') : '',
      files:tt(p.keys && p.keys.length ? 'climates.n_files_and_the_display_name' : 'climates.n_files',{n:(p.files || []).length})}))) return;
  k.busy = true;
  cclPaint();
  let res;
  try{ res = await api.post('/api/map/climate_apply', cclBody(),
                            {label: `declaring ${k.code}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('climates.the_climate_was_not_written')), 9000);
    cclPaint();
    return;
  }
  toast(tt(p.mode === 'add' ? 'climates.declared_files_written' : 'climates.taken_over_files_written',{code:p.code,n:(res.files || []).length}), 7000);
  activity('climates',
           tt(p.mode === 'add' ? 'climates.activity_declared' : 'climates.activity_took_over',{mod:k.mod,code:p.code}));
  k.plan = null;
  await loadCampmap(true);
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
      <button onclick="cclToggle()" title="${ttA('climates.which_climates_this_mod_declares_which')}"
        >${tt('climates.climates')}</button>
      <span class="sp"></span>
      <span class="count">${tt('climates.four_files_and_no_pixels')}</span>
    </div></div>`;
  if(k.loading) return `<div class="cbrpanel count">${tt('climates.reading_descr_climates_txt')}</div>`;
  const d = k.d || {};
  if(!d.have) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.problem || tt('climates.the_climates_could_not_be_read'))}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="cclToggle()">${tt('common.close')}</button></div></div>`;
  return `<div class="cbrpanel">
    <div class="k">${tt('climates.climates_declared_ground_types',{n:(d.slots || []).length,n2:(d.grounds || []).length,file:esc(d.file)})}</div>
    ${cclSlotsHtml(d)}
    ${cclGeogHtml(d)}
    ${cclFormHtml(k, d)}
    <div class="cmbar2">
      <span class="sp"></span>
      <button onclick="cclToggle()">${tt('common.close')}</button>
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
    title="${ttA('climates.index_heat',{code:esc(s.code),index:s.index,heat:s.heat,winter:s.winter ? tt('climates.winter_of_its_own') : tt('climates.drawn_in_its_summer_textures_all'),aerial:s.aerial ? tt('climates.ground_types',{grounds:s.grounds}) : tt('climates.no_texture_block')})}">
    <span class="cclsw" style="background:${cclHex(s.rgb)}"></span>
    <span class="cclnm">${esc(s.label || s.code)}${
      s.spare ? `<span class="cclfree">${tt('climates.spare')}</span>` : ''}</span>
    <span class="count">${ttN(s.aerial ? 'climates.tile_count' : 'climates.tile_count_no_textures',s.tiles)}</span>
  </button>`).join('')}</div>
  ${(d.free || []).length ? `<div class="count">${ttN('climates.spare_by_name_and_on_no_tile',d.free.length,{free:d.free.map(c => `<code>${esc(c)}</code>`).join(' and ')})}</div>`
  : `<div class="count">${tt('climates.both_spare_names_are_already_painted')}</div>`}
  <div class="cmbar2">
    <button class="${k.adding ? 'on' : ''}" onclick="cclAdd()"
      title="${ttA('climates.append_a_name_the_engine_does')}"
      >${tt('climates.add_a_new_name_instead')}</button>
  </div>`;
}

//: The battle map's own file, and the three states it comes in. This is the one
//: thing on the panel that is not about the picture, and it is why the list
//: above is the first answer.
function cclGeogHtml(d){
  const g = d.geography || {};
  if(g.have) return `<div class="count"><code>${esc(g.file)}</code> ${ttN('climates.gives_a_block_to_climates_by_name',g.names.length)}</div>`;
  return `<div class="w-warn">${tt('climates.taking_over_one_of_the_twelve',{problem:esc(g.problem || '')})}</div>`;
}

function cclFormHtml(k, d){
  if(!k.code && !k.adding) return `<div class="count">${tt('climates.pick_a_slot_above_to_take')}</div>`;
  const heat = [0, 1, 2, 3, 4];
  return `<div class="cclform">
    <div class="cmtrow"><span class="cmtval">
      ${tt('climates.name_the_engine_reads',{x:k.adding
        ? `<input value="${esc(k.code)}" placeholder="frozen_arctic"
             oninput="cclSet('code', this.value)">`
        : `<code>${esc(k.code)}</code>`})}</span></div>
    ${k.adding ? `<div class="count">${tt('climates.a_bare_word_a_letter_first')}</div>`
      : `<div class="count">${tt('climates.a_take_over_keeps_the_slots')}</div>`}
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('climates.display_name')}</span>
      <input value="${esc(k.label)}" placeholder="${ttA('climates.its_code_name')}"
        oninput="cclSet('label', this.value)"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('climates.colour_in_map_climates_tga')}</span>
      <input type="color" value="${cclHex(k.rgb)}"
        oninput="cclSetHex(this.value)">
      <span class="count">${k.rgb.join(' ')}</span></span></div>
    <div class="cmtrow"><span class="cmtval">
      ${tt('climates.heat',{x:heat.map(h => `<button class="${
        k.heat === h ? 'on' : ''}" onclick="cclSet('heat', ${h})">${h}</button>`
        ).join('')})}</span></div>
    <div class="count">${tt('climates.the_armour_fatigue_effect_zero_means')}</div>
    <div class="cmtrow"><span class="cmtval">
      ${tt('climates.winter')}
        <button class="${k.winter ? 'on' : ''}"
          onclick="cclSet('winter', true)">${tt('climates.its_own')}</button>
        <button class="${!k.winter ? 'on' : ''}"
          onclick="cclSet('winter', false)">${tt('climates.summer_all_year')}</button>
      </span></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('climates.textures_copied_from')}</span>
      <select onchange="cclSet('donor', this.value)">
        ${(d.donors || []).map(x => `<option value="${esc(x.code)}"${
          x.code === k.donor ? ' selected' : ''}>${ttN('climates.code_ground_types',x.grounds,{code:esc(x.code)})}</option>`
          ).join('')}
      </select></span></div>
    <div class="count">${tt('climates.a_climate_with_no_textures_is')}</div>
    ${cclDonorNote(k, d)}
    <div class="cmbar2">
      <button onclick="cclPlan()" ${k.busy || !k.code.trim() ? 'disabled' : ''}
        title="${ttA('climates.work_out_all_four_files_it')}"
        >${k.busy && !k.plan ? tt('common.working_it_out') : tt('climates.work_out_the_writes')}</button>
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
  return `<div class="w-warn"><code>${esc(k.donor)}</code> ${tt('climates.is_a_block_of_and_not',{x:esc((d.aerial || {}).file || tt('climates.the_aerial_file')),n:(d.slots || []).length})}</div>`;
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
    <div class="k">${ttN('climates.files_would_change_ground_types',n,{mode:p.mode === 'add' ? tt('climates.a_new_name') : tt('climates.a_slot_taken_over'),grounds:(p.grounds || []).length})}</div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    <div class="cmbar2">
      <button onclick="cclApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? tt('common.writing') : tt('climates.declare_2',{code:esc(p.code)})}</button>
      <span class="sp"></span>
      <span class="count">${tt('climates.backed_up_first_log_can_undo')}</span>
    </div>
  </div>`;
}
