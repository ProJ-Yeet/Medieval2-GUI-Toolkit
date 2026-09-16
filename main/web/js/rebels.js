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
  activity('rebels', `${c.mod}: opened the rebel factions panel`);
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
      {label: 'reading this mod’s rebel factions'});
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
  if(!names.length){ toast('✗ tick the provinces to move first', 5000); return; }
  if(!k.target){ toast('✗ pick the rebel faction to move them to', 5000); return; }
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
  if(!confirm(`Write: move ${names.length} province`
    + `${names.length === 1 ? '' : 's'} to ${k.target}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14
       ? `\n…and ${p.changes.length - 14} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n\n') : '')
    + `\n\nWritten to ${p.rel}.\nmap.rwm is deleted too, or the game loads the `
    + 'old compiled map and shows none of this.'
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  try{ res = await api.post('/api/map/rebel_apply', body); }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); rebPaint(); return; }
  toast(`${(res.record && res.record.summary || '').split('\n')[0]}. `
    + '🕑 Log can undo it.', 6000);
  activity('rebels', `${k.mod}: ${names.length} province(s) -> ${k.target}`);
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
      <button onclick="rebToggle()" title="Every rebel faction this mod declares
and the provinces that name it - the other direction from the rebel type box
on the province record">Rebel factions…</button>
      <span class="sp"></span>
      <span class="count">both directions</span>
    </div></div>`;
  if(k.loading) return `<div class="cbrpanel count">reading
    <code>descr_rebel_factions.txt</code>…</div>`;
  const d = k.d || {};
  if(d.error) return `<div class="cbrpanel">
    <div class="w-bad">${esc(d.error)}</div>
    <div class="cmbar2"><span class="sp"></span>
      <button onclick="rebToggle()">Close</button></div></div>`;
  return `<div class="cbrpanel">
    <div class="k">Rebel factions
      <span class="count">${d.declared} declared · ${d.named} named by a
        province${d.orphans ? ` · ${d.orphans} named by none` : ''} ·
        <code>${esc(d.file)}</code></span></div>
    ${rebNoteHtml(d)}
    ${rebListHtml(d)}
    ${rebDetailHtml(d)}
    <div class="cmbar2">
      <span class="sp"></span>
      <button onclick="rebToggle()">Close</button>
    </div>
  </div>`;
}

//: The two whole-file facts, and neither is a finding. `silent_regions` is the
//: one worth saying out loud before anything else: on Reforged it is every
//: province the mod has.
function rebNoteHtml(d){
  const out = [];
  if(d.silent_regions) out.push(`<div class="w-warn">${d.silent_regions} of
    ${d.regions} provinces name a rebel faction with <code>chance 0</code>, so
    they spawn no rebels. That is a real setting rather than a fault - it is how
    a mod turns province rebels off - but it is what those assignments do.</div>`);
  if((d.dangling || []).length) out.push(`<div class="w-bad">${
    d.dangling.length} rebel type${d.dangling.length === 1 ? '' : 's'} named by a
    province and declared nowhere: ${d.dangling.map(x =>
      `<code>${esc(x.name)}</code> (${x.count})`).join(', ')}. The engine looks
    this value up by name, so those provinces get no rebels at all.</div>`);
  if((d.blank || []).length) out.push(`<div class="count">${d.blank.length}
    province${d.blank.length === 1 ? '' : 's'} name no rebel type at all.</div>`);
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
    title="${esc(r.name)} · ${esc(r.category)}${
      r.by_category ? ' (spawned by category, not off a region record)' : ''
    } · chance ${esc(r.chance)} · ${r.unit_count} unit${
      r.unit_count === 1 ? '' : 's'} · line ${r.line}">
    <span class="rebnm">${esc(r.shown || r.name)}${
      r.by_category ? '<span class="rebcat">by category</span>' : ''}${
      r.orphan ? '<span class="reborph">no province</span>' : ''}</span>
    <span class="count">${r.count} province${r.count === 1 ? '' : 's'} ·
      chance ${esc(r.chance) || '?'}${
        r.silent ? ' <b>(none spawn)</b>' : ''} · ${r.unit_count} unit${
        r.unit_count === 1 ? '' : 's'}${
        (r.dead_units || []).length
          ? ` · <b>${r.dead_units.length} not in the EDU</b>` : ''}</span>
  </button>`).join('')}</div>`;
}

//: The picked faction, opened out: what it fields, where it is, and the move.
function rebDetailHtml(d){
  const k = state.reb, r = rebRow();
  if(!r) return `<div class="count" style="padding:6px 2px">Pick a rebel faction
    to see its provinces, its units, and to move provinces between factions.</div>`;
  const all = (d.rebels || []).map(x => x.name).sort();
  return `<div class="rebdet">
    <div class="k">${esc(r.shown || r.name)}
      <span class="count"><code>${esc(r.name)}</code> · ${esc(r.category)} ·
        chance ${esc(r.chance)}${r.silent ? ' - none will spawn' : ''}</span></div>
    ${r.silent ? `<div class="w-warn">This faction has <code>chance 0</code>.
      Every province below names it and none of them will spawn a rebel
      army.</div>` : ''}
    ${r.by_category ? `<div class="w-warn">The engine spawns
      <code>${esc(r.category)}</code> by category rather than off a region
      record, so naming this one on a province is not how it is meant to be
      reached.</div>` : ''}
    ${r.orphan ? `<div class="w-warn">No province names this faction, so its
      ${r.unit_count} unit${r.unit_count === 1 ? '' : 's'} cannot spawn
      anywhere.</div>` : ''}
    ${rebUnitsHtml(r)}
    ${rebProvincesHtml(r)}
    ${rebMoveHtml(k, r, all)}
  </div>`;
}

//: What it can field. Read-only on purpose: the unit list is the Minor Files
//: screen's and editing it in two places is how the two disagree.
function rebUnitsHtml(r){
  if(!r.unit_count) return `<div class="w-warn">This faction lists no
    <code>unit</code> line, so it has nothing to spawn.</div>`;
  return `<div class="rebunits">
    <div class="count">Fields ${r.unit_count} unit${
      r.unit_count === 1 ? '' : 's'} - edit them on the Minor Files screen,
      which owns this record</div>
    ${r.units.map(u => `<span class="rebunit${
      u.known === false ? ' bad' : ''}" title="${
      u.known === false ? 'no unit of this type in this mod’s EDU'
                        : 'line ' + u.line}">${esc(u.type)}</span>`).join('')}
  </div>`;
}

//: Where it is. Each chip goes to the province on the map, which is the whole
//: point of the reverse direction.
function rebProvincesHtml(r){
  const k = state.reb;
  if(!r.count) return '';
  return `<div class="rebprovs">
    <div class="cmbar2">
      <span class="count">${r.count} province${r.count === 1 ? '' : 's'}</span>
      <span class="sp"></span>
      <button onclick="rebTickAll(true)">Tick all</button>
      <button onclick="rebTickAll(false)">None</button>
    </div>
    ${r.provinces.map(p => `<span class="rebprov">
      <input type="checkbox" id="rebp_${esc(p)}"${k.sel.has(p) ? ' checked' : ''}
        onchange="rebTick('${esc(p)}', this.checked)">
      <label for="rebp_${esc(p)}">${esc(p)}</label>
      <button class="rebgo" title="Show ${esc(p)} on the map"
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
      <span class="count">${n} ticked</span>
      <span class="sp"></span>
      <label class="count" for="rebTo">move to</label>
      <select id="rebTo" onchange="rebTarget(this.value)">
        <option value="">…</option>
        ${all.map(x => `<option value="${esc(x)}"${
          k.target === x ? ' selected' : ''}>${esc(x)}</option>`).join('')}
      </select>
      <button class="primary" ${n && k.target && !k.busy ? '' : 'disabled'}
        onclick="rebAssign()">Assign${n ? ` ${n}` : ''}</button>
    </div>
  </div>`;
}

//: A chip to the map. The manifest is what knows where a province is - the
//: reverse list is names out of a text file and has no coordinates in it.
function rebGo(name){
  const c = state.cmap;
  if(!c || !c.man) return;
  const hit = (c.man.regions || []).find(r => r.name === name);
  if(!hit){ toast(`✗ ${name} has no tiles on this map`, 5000); return; }
  cmapGoRegion(hit.key);
}
