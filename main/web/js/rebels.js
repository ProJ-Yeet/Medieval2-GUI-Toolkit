/* rebels.js - Campaign Map: a rebel faction, and the provinces that name it

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   REBELS RIGHT IN PLACE - Phase 35.

   Every name here starts `reb`. Python owns every rule; this file owns the one
   direction nothing in the toolkit had, which is the reverse of the box on the
   province panel: pick a REBEL FACTION and see the provinces that name it.

   THIS IS NOT A REBEL FACTION EDITOR. The category, the chance and the unit
   list belong to the Minor Files screen and already work there. What this
   edits is the ASSIGNMENT, which is a line in descr_regions.txt and a
   different file entirely. The panel says so and links across rather than
   growing the other screen's fields.

   THE CHANCE IS ON EVERY ROW, and that is the phase's finding rather than a
   decoration. `chance 0` means the assignment does nothing, and it is not rare:
   Third Age Reforged sets it on all 27 of the blocks its provinces name, so
   every one of its 199 provinces points at a rebel faction that will never
   spawn. Divide and Conquer uses it for `No_Rebels` alone. Picking a block for
   a province without seeing that number is the one way to make this edit and
   have it silently do nothing.

   A BLOCK NO PROVINCE NAMES IS NOT ALWAYS AN ORPHAN. Each mod declares one
   block per non-`peasant_revolt` category - `brigands`, `pirates`,
   `gladiator_uprising` - and the engine spawns those by category rather than
   off a region record. They are marked and never counted as unused. What is
   left after that exemption is a real orphan, and DaC has two.

   THE PROVINCE CHIPS GO TO THE MAP. `cmapGoRegion` is the one way of arriving
   at a province and it is what a chip calls, so reading the list and looking at
   the map are the same gesture. */

/* ---------- state ---------- */

function rebNew(mod, campaign){
  return {mod, campaign, open: true, loading: true, d: null,
          pick: '', sel: new Set(), target: '', busy: false, plan: null};
}

/* Open the panel's shell on a fresh map read. Like the climates panel it reads
   nothing until somebody asks: the join is two text files and a person who
   never opens it should not pay for them. A panel already open on the same mod
   and campaign is repainted rather than dropped, so a save that reloads the map
   does not close it under the person who just used it. */
function rebOpen(){
  const c = state.cmap;
  if(!c) return;
  const k = state.reb;
  if(k && k.open && k.mod === c.mod && k.campaign === (c.campaign || '')){
    rebPaint();
    rebLoad();
    return;
  }
  state.reb = null;
  rebPaint();
}

function rebToggle(){
  const c = state.cmap;
  if(!c) return;
  if(state.reb){ state.reb = null; rebPaint(); return; }
  state.reb = rebNew(c.mod, c.campaign || '');
  activity('rebels', tt('rebels.opened_the_rebel_factions_panel',{mod:c.mod}));
  rebPaint();
  rebLoad();
}

async function rebLoad(){
  const k = state.reb;
  if(!k) return;
  let d;
  try{
    d = await api.get(`/api/map/rebels?mod=${enc(k.mod)}`
      + (k.campaign ? `&campaign=${enc(k.campaign)}` : ''),
      {label: tt('rebels.reading_this_mods_rebel_factions')});
  }catch(e){ d = {error: errText(e), rebels: [], dangling: [], blank: []}; }
  if(state.reb !== k) return;
  k.loading = false;
  k.d = d;
  rebPaint();
}

/* Pick a rebel faction. The province tick boxes are cleared, because they were
   ticked against a different list and carrying them over would offer to move
   provinces the person can no longer see. */
function rebPick(name){
  const k = state.reb;
  if(!k || !k.d) return;
  k.pick = (k.pick === name) ? '' : name;
  k.sel = new Set();
  k.target = '';
  k.plan = null;
  rebPaint();
}

function rebRow(){
  const k = state.reb;
  if(!k || !k.d || !k.pick) return null;
  return (k.d.rebels || []).find(r => r.name === k.pick) || null;
}

function rebTick(province, on){
  const k = state.reb;
  if(!k) return;
  if(on) k.sel.add(province); else k.sel.delete(province);
  k.plan = null;
  rebPaint();
}

function rebTickAll(on){
  const k = state.reb, row = rebRow();
  if(!k || !row) return;
  k.sel = on ? new Set(row.provinces) : new Set();
  k.plan = null;
  rebPaint();
}

function rebTarget(value){
  const k = state.reb;
  if(!k) return;
  k.target = value;
  k.plan = null;
  rebPaint();
}

/* Move the ticked provinces onto the target faction.

   The plan is fetched and shown before anything is written, which is the rule
   every writer on this screen follows. Its warnings are the two a person cannot
   see from here - the target's chance being 0, and the target being a
   category block - and both are warnings rather than refusals because both are
   states the installed mods are really in. */
async function rebAssign(){
  const k = state.reb;
  if(!k || k.busy) return;
  const names = [...k.sel];
  if(!names.length){ toast(tt('rebels.tick_the_provinces_to_move_first'), 5000); return; }
  if(!k.target){ toast(tt('rebels.pick_the_rebel_faction_to_move'), 5000); return; }
  const body = {mod: k.mod, campaign: k.campaign || '',
                rebel: k.target, regions: names};
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/rebel_plan', body); }
  finally{ k.busy = false; rebPaint(); }
  if(res.error){ toast('✗ ' + res.error, 9000); return; }
  const p = res.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const warn = (p.warnings || []).map(x => '⚠ ' + x);
  if(!confirm(ttN('rebels.write_move_provinces_confirm',names.length,{target:k.target,rel:p.rel,
    changes:(lines.join('\n') || tt('common.no_visible_change'))
      + ((p.changes || []).length > 14
         ? tt('rebels.and_more',{changes:p.changes.length - 14}) : '')
      + (warn.length ? '\n\n' + warn.join('\n\n') : '')}))) return;
  k.busy = true;
  try{ res = await api.post('/api/map/rebel_apply', body); }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); rebPaint(); return; }
  toast(tt('rebels.summary_log_can_undo',{summary:(res.record && res.record.summary || '').split('\n')[0]}), 6000);
  activity('rebels', tt('rebels.province_s',{mod:k.mod,names_n:names.length,target:k.target}));
  k.sel = new Set();
  k.plan = null;
  await loadCampmap();
  if(state.reb) rebLoad();
}

/* ---------- drawing ---------- */

function rebPaint(){
  const el = document.getElementById('cmRebels');
  if(!el) return;
  el.innerHTML = rebHtml();
}

function rebHtml(){
  const k = state.reb;
  if(!k || !k.open) return `<div class="cbrpanel">
    <div class="cmbar2">
      <button onclick="rebToggle()" title="${ttA('rebels.every_rebel_faction_this_mod_declares')}">${tt('rebels.rebel_factions')}</button>
      <span class="sp"></span>
      <span class="count">${tt('rebels.both_directions')}</span>
    </div></div>`;
  if(k.loading) return `<div class="cbrpanel count">${tt('rebels.reading_descr_rebel_factions_txt')}</div>`;
  const d = k.d || {};
  if(d.error) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.error)}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="rebToggle()">${tt('common.close')}</button></div></div>`;
  return `<div class="cbrpanel">
    <div class="k">${tt('rebels.rebel_factions_declared_named_by_a',{declared:d.declared,named:d.named,orphans:d.orphans ? tt('rebels.named_by_none',{orphans:d.orphans}) : '',file:esc(d.file)})}</div>
    ${rebNoteHtml(d)}
    ${rebListHtml(d)}
    ${rebDetailHtml(d)}
    <div class="cmbar2">
      <span class="sp"></span>
      <button onclick="rebToggle()">${tt('common.close')}</button>
    </div>
  </div>`;
}

//: The two whole-file facts, and neither is a finding. `silent_regions` is the
//: one worth saying out loud before anything else: on Reforged it is every
//: province the mod has.
function rebNoteHtml(d){
  const out = [];
  if(d.silent_regions) out.push(`<div class="w-warn">${tt('rebels.of_provinces_name_a_rebel_faction',{silent_regions:d.silent_regions,regions:d.regions})}</div>`);
  if((d.dangling || []).length) out.push(`<div class="w-bad">${ttN('rebels.rebel_types_named_by_a_province',d.dangling.length,{names:d.dangling.map(x =>
      `<code>${esc(x.name)}</code> (${x.count})`).join(', ')})}</div>`);
  if((d.blank || []).length) out.push(`<div class="count">${ttN('rebels.provinces_name_no_rebel_type',d.blank.length)}</div>`);
  return out.join('');
}

//: One row a faction, commonest first, because the map is mostly the big ones.
//: The three facts on the row are the three that decide whether an assignment
//: to it does anything: how many provinces it has, what its chance is, and how
//: many units it can field.
function rebListHtml(d){
  const k = state.reb;
  const rows = (d.rebels || []).slice().sort((a, b) =>
    b.count - a.count || a.name.localeCompare(b.name));
  return `<div class="reblist">${rows.map(r => `<button
    class="rebrow${k.pick === r.name ? ' on' : ''}${r.orphan ? ' orphan' : ''}"
    onclick="rebPick('${esc(r.name)}')"
    title="${ttA('rebels.chance_units_line',{name:esc(r.name),category:esc(r.category),by_category:r.by_category ? tt('rebels.spawned_by_category_not_off_a') : '',chance:esc(r.chance),units:ttN('rebels.unit_count',r.unit_count),line:r.line})}">
    <span class="rebnm">${esc(r.shown || r.name)}${
      r.by_category ? `<span class="rebcat">${tt('rebels.by_category')}</span>` : ''}${
      r.orphan ? `<span class="reborph">${tt('rebels.no_province')}</span>` : ''}</span>
    <span class="count">${tt('rebels.provinces_chance_units',{provinces:ttN('rebels.province_count',r.count),chance:esc(r.chance) || '?',silent:r.silent ? ` <b>${tt('rebels.none_spawn')}</b>` : '',units:ttN('rebels.unit_count',r.unit_count),dead_units:(r.dead_units || []).length
          ? ` ${tt('rebels.not_in_the_edu',{dead_units_n:r.dead_units.length})}` : ''})}</span>
  </button>`).join('')}</div>`;
}

//: The picked faction, opened out: what it fields, where it is, and the move.
function rebDetailHtml(d){
  const k = state.reb, r = rebRow();
  if(!r) return `<div class="count" style="padding:6px 2px">${tt('rebels.pick_a_rebel_faction_to_see')}</div>`;
  const all = (d.rebels || []).map(x => x.name).sort();
  return `<div class="rebdet">
    <div class="k">${tt('rebels.chance',{x:esc(r.shown || r.name),name:esc(r.name),category:esc(r.category),chance:esc(r.chance),silent:r.silent ? tt('rebels.none_will_spawn') : ''})}</div>
    ${r.silent ? `<div class="w-warn">${tt('rebels.this_faction_has_chance_0_every')}</div>` : ''}
    ${r.by_category ? `<div class="w-warn">${tt('rebels.the_engine_spawns_by_category_rather',{category:esc(r.category)})}</div>` : ''}
    ${r.orphan ? `<div class="w-warn">${ttN('rebels.no_province_names_faction_units',r.unit_count)}</div>` : ''}
    ${rebUnitsHtml(r)}
    ${rebProvincesHtml(r)}
    ${rebMoveHtml(k, r, all)}
  </div>`;
}

//: What it can field. Read-only on purpose: the unit list is the Minor Files
//: screen's and editing it in two places is how the two disagree.
function rebUnitsHtml(r){
  if(!r.unit_count) return `<div class="w-warn">${tt('rebels.this_faction_lists_no_unit_line')}</div>`;
  return `<div class="rebunits">
    <div class="count">${ttN('rebels.fields_units_edit_on_minor_files',r.unit_count)}</div>
    ${r.units.map(u => `<span class="rebunit${
      u.known === false ? ' bad' : ''}" title="${
      u.known === false ? tt('rebels.no_unit_of_this_type_in')
                        : ttA('rebels.line_n',{line:u.line})}">${esc(u.type)}</span>`).join('')}
  </div>`;
}

//: Where it is. Each chip goes to the province on the map, which is the whole
//: point of the reverse direction.
function rebProvincesHtml(r){
  const k = state.reb;
  if(!r.count) return '';
  return `<div class="rebprovs">
    <div class="cmbar2">
      ${ttN('rebels.province_chip',r.count)}
      <button onclick="rebTickAll(true)">${tt('rebels.tick_all')}</button>
      <button onclick="rebTickAll(false)">${tt('common.none_2')}</button>
    </div>
    ${r.provinces.map(p => `<span class="rebprov">
      <input type="checkbox" id="rebp_${esc(p)}"${k.sel.has(p) ? ' checked' : ''}
        onchange="rebTick('${esc(p)}', this.checked)">
      <label for="rebp_${esc(p)}">${esc(p)}</label>
      <button class="rebgo" title="${ttA('rebels.show_on_the_map',{x:esc(p)})}"
        onclick="rebGo('${esc(p)}')">◉</button>
    </span>`).join('')}
  </div>`;
}

//: The move. The target list is every declared faction including this one,
//: because Python refuses a no-op with a sentence rather than the button being
//: mysteriously dead.
function rebMoveHtml(k, r, all){
  const n = k.sel.size;
  return `<div class="rebmove">
    <div class="cmbar2">
      ${tt('rebels.ticked',{x:n})}
      <label class="count" for="rebTo">${tt('rebels.move_to')}</label>
      <select id="rebTo" onchange="rebTarget(this.value)">
        <option value="">…</option>
        ${all.map(x => `<option value="${esc(x)}"${
          k.target === x ? ' selected' : ''}>${esc(x)}</option>`).join('')}
      </select>
      <button class="primary" ${n && k.target && !k.busy ? '' : 'disabled'}
        onclick="rebAssign()">${tt('rebels.assign',{x:n ? ` ${n}` : ''})}</button>
    </div>
  </div>`;
}

//: A chip to the map. The manifest is what knows where a province is - the
//: reverse list is names out of a text file and has no coordinates in it.
function rebGo(name){
  const c = state.cmap;
  if(!c || !c.man) return;
  const hit = (c.man.regions || []).find(r => r.name === name);
  if(!hit){ toast(tt('rebels.has_no_tiles_on_this_map',{name}), 5000); return; }
  cmapGoRegion(hit.key);
}
