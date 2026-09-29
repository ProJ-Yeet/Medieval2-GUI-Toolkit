/* portui.js - “Port from another mod”, shared by the Traits and Ancillaries modes

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= PORT =======================
   The one dialog in the toolkit that reads TWO mods: pick records in another
   mod, and they land in this one - the definition block, the triggers that
   grant it, and its text keys, in one backed-up job.

   One file for both modes because the server has one engine for both
   (unittransfer/portrecords.py): a trait and an ancillary are the same format
   with the level ladder taken out, which is already why they share their
   trigger language. `kind` is the whole of the difference here too.

   THE PAGE NEVER PARSES A GAME FILE. /api/port lists what the other mod has and
   what this one already has; /api/port/plan says exactly what a write would do,
   including everything the ported record names that this mod has not got; and
   nothing is written until /api/port/apply.

   The warnings are the point of the preview, not decoration. A ported trait
   keeps its ExcludeCultures and AntiTraits, a ported ancillary keeps its Image
   and ExcludedAncillaries, and the triggers keep every condition - none of that
   is rewritten to suit the destination, because guessing a substitution is how a
   port silently becomes a different trait. What will not work over there is
   listed instead, while it is still a preview. */

// {kind, source, dest, ov, sel:Set, q, plan, busy, withTriggers, overwrite}
let portState = null;

const PORT_NOUN = {traits:'trait', ancillaries:'ancillary'};

/* Opened from the Traits or the Ancillaries list. The destination is always the
   mod being edited - this is a way IN to the mod on screen, not a general
   two-mod transfer, and offering a destination picker would only invite writing
   into a mod you are not looking at. */
function portOpen(kind){
  const others = (state.mods||[]).map(m=>m.name).filter(n=>n!==state.src);
  if(!others.length){
    toast(tt('portui.there_is_only_one_mod_here_to'), 6000); return;
  }
  portState = {kind, dest:state.src, source:others[0], ov:null, sel:new Set(),
               q:'', plan:null, busy:false, withTriggers:true, overwrite:false,
               onlyNew:true};
  const modal = document.getElementById('modal');
  modal.className = 'modal wide';
  overlay.classList.add('open');
  portRender();
  portLoad();
}

async function portLoad(){
  const p = portState; if(!p) return;
  p.ov = null; p.sel = new Set(); p.plan = null;
  portRender();
  let r;
  try{ r = await api.get(`/api/port?kind=${enc(p.kind)}&source=${enc(p.source)}`
    + `&dest=${enc(p.dest)}`); }
  catch(e){ r = {error:errText(e)}; }
  if(!portState || portState !== p) return;
  p.ov = r;
  portRender();
}

function portPickSource(name){
  const p = portState; if(!p) return;
  p.source = name;
  portLoad();
}

function portRows(){
  const p = portState, ov = p.ov;
  if(!ov || !ov.records) return [];
  const q = (p.q||'').trim().toLowerCase();
  return ov.records.filter(r =>
    (!p.onlyNew || !r.exists || p.sel.has(r.name))
    && (!q || r.name.toLowerCase().includes(q)
        || (r.label||'').toLowerCase().includes(q)));
}

function portRender(){
  const p = portState; if(!p) return;
  const noun = PORT_NOUN[p.kind] || 'record';
  const others = (state.mods||[]).map(m=>m.name).filter(n=>n!==p.dest);
  const ov = p.ov;
  const rows = portRows();
  const body = !ov ? `<div class="empty">${tt('portui.reading_s_s',{source:esc(p.source),noun:esc(noun)})}</div>`
    : ov.error ? `<div class="w-bad">${esc(ov.error)}</div>`
    : `<div class="count" style="margin:8px 0">${ttN('portui.n_nouns_in_source_already_exist_in_dest',ov.count,{noun:esc(noun),source:esc(ov.source),already:ov.already,dest:esc(ov.dest),error:ov.dest_error?`<br><span class="w-bad">${esc(ov.dest_error)}</span>`:''})}</div>
      <div class="barrow">
        <input placeholder="${ttA('portui.filter')}" value="${esc(p.q)}" style="flex:1"
          oninput="portState.q=this.value;portRowsPaint()">
        <label class="chk"><input type="checkbox" ${p.onlyNew?'checked':''}
          onchange="portState.onlyNew=this.checked;portRowsPaint()">
          ${tt('portui.hide_the_this_mod_already_has',{already:ov.already})}</label>
        <span class="count" id="portCount"></span>
      </div>
      <div class="portlist" id="portList">${rows.map(portRowHtml).join('')}</div>`;
  document.getElementById('modal').innerHTML = `
    <h2>${tt('portui.port_s_into',{noun:esc(noun)})} <span class="pill">${esc(p.dest)}</span></h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:8px">${docPoints(
        tt('portui.each_one_brings_three_things_because',{noun:esc(noun)}),[
        tt('portui.its_block_at_the_top_of'),
        tt('portui.every_trigger_in_the_other_mod_that'),
        tt('portui.its_text_keys_without_them_the_character_screen_crashes',{noun:esc(noun)})])}</div>
      <div class="barrow">
        <span class="count">${tt('portui.read_from')}</span>
        <select onchange="portPickSource(this.value)">${others.map(n =>
          `<option value="${esc(n)}"${n===p.source?' selected':''}>${esc(n)}</option>`).join('')}</select>
        <span class="count">${tt('portui.written_into')} <b>${esc(p.dest)}</b></span>
      </div>
      ${body}
      <fieldset style="margin-top:10px"><legend>${tt('portui.how')}</legend>
        <label class="chk"><input type="checkbox" ${p.withTriggers?'checked':''}
          onchange="portState.withTriggers=this.checked;portStale()">
          ${tt('portui.bring_the_triggers_that_grant_it')}</label>
        <div class="count" style="margin:2px 0 6px">${tt('portui.off_the_exists_in_this_mod',{noun:esc(noun)})}</div>
        <label class="chk"><input type="checkbox" ${p.overwrite?'checked':''}
          onchange="portState.overwrite=this.checked;portStale()">
          ${tt('portui.replace_what_is_already_there')}</label>
        <div class="count" style="margin-top:2px">${tt('portui.off_the_safe_default_a_name')}</div>
      </fieldset>
      <div id="portPreview"></div>
    </div>
    <div class="foot">
      <span class="count" id="portSel"></span>
      ${cleanerBoxHtml()}
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="portPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="portApply()">${tt('portui.port_them')}</button>
    </div>`;
  portRowsPaint();
}

function portRowHtml(r){
  const on = portState.sel.has(r.name);
  return `<label class="portrow${r.exists?' here':''}">
    <input type="checkbox" ${on?'checked':''}
      onchange="portTick('${q1(esc(r.name))}',this.checked)">
    <span class="pn">${esc(r.label||r.name)}</span>
    <span class="count">${tt('portui.triggers_and_text_keys',{triggers:r.triggers
      ? ttN('portui.n_triggers',r.triggers)
      : `<b class="w-warn">${tt('portui.nothing_grants_it_there')}</b>`,keys:ttN('portui.n_text_keys',r.keys),exists:r.exists?` ${tt('portui.already_in_this_mod')}`:''})}</span>
  </label>`;
}

// The list only. Ticking a row must not rebuild the dialog around it - 799 rows
// is the biggest list in the toolkit outside Strings.
function portRowsPaint(){
  const p = portState; if(!p || !p.ov || p.ov.error) return;
  const rows = portRows();
  const list = document.getElementById('portList');
  if(list) list.innerHTML = rows.map(portRowHtml).join('')
    || `<div class="count" style="padding:8px">${tt('common.nothing_matches')}</div>`;
  const c = document.getElementById('portCount');
  if(c) c.textContent = `${rows.length}/${p.ov.count}`;
  const s = document.getElementById('portSel');
  if(s) s.textContent = p.sel.size
    ? `${p.sel.size} picked` : tt('portui.nothing_picked_yet');
}
function portTick(name, on){
  const p = portState; if(!p) return;
  on ? p.sel.add(name) : p.sel.delete(name);
  portStale();
  portRowsPaint();
}
// The preview belongs to the choices that were made when it was taken.
function portStale(){
  const p = portState; if(!p) return;
  p.plan = null;
  const box = document.getElementById('portPreview');
  if(box) box.innerHTML = '';
}

const portBody = () => ({kind:portState.kind, source:portState.source,
  dest:portState.dest, names:[...portState.sel],
  with_triggers:portState.withTriggers, overwrite:portState.overwrite});

async function portPreview(){
  const p = portState, box = document.getElementById('portPreview');
  if(!p || !box) return null;
  if(!p.sel.size){ toast(tt('portui.tick_at_least_one',{x:PORT_NOUN[p.kind]||'record'})); return null; }
  box.innerHTML = `<div class="preview">${tt('common.planning')}</div>`;
  let r;
  try{ r = await api.post('/api/port/plan', portBody()); }
  catch(e){ r = {error:errText(e)}; }
  if(!portState || portState !== p) return null;
  if(r.error){ box.innerHTML = `<div class="preview w-bad">${esc(r.error)}</div>`; return null; }
  p.plan = r.plan || {};
  box.innerHTML = portPlanHtml(p.plan);
  return p.plan;
}

function portPlanHtml(pl){
  const li = (cls, items) => (items||[]).map(x =>
    `<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  const changes = (pl.changes||[]).slice(0, 20);
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">⇩</span><span class="stext">${tt('common.what_this_writes')}</span></div>
    ${li('', changes)}
    ${(pl.changes||[]).length>20
      ? `<div class="srow"><span class="sicon">·</span><span class="stext">
         <i>${tt('portui.and_more',{x:pl.changes.length-20})}</i></span></div>` : ''}
    ${li('warn', pl.warnings)}${li('bad', pl.errors)}
    ${(pl.skipped||[]).length
      ? `<div class="srow warn"><span class="sicon">!</span><span class="stext">
         ${tt('portui.already_here_and_left_alone',{skipped_n:pl.skipped.length,x:esc(pl.skipped.slice(0,8).join(', ')),x2:pl.skipped.length>8?'…':''})}</span></div>` : ''}
  </div>`;
}

async function portApply(){
  const p = portState;
  if(!p || p.busy) return;
  const pl = p.plan || await portPreview();
  if(!pl) return;
  if((pl.errors||[]).length){ toast('✗ ' + pl.errors[0], 6000); return; }
  if(!pl.ok){ toast(tt('portui.nothing_to_write_everything_picked_is'), 5000); return; }
  const noun = PORT_NOUN[p.kind] || 'record';
  const lines = (pl.changes||[]).slice(0, 12);
  const warn = (pl.warnings||[]).slice(0, 5).map(w => '⚠ ' + w);
  if(!confirm(tt('portui.port_from_into_confirm',{sel_n:p.sel.size,noun,source:p.source,dest:p.dest,
    changes:(lines.join('\n') || tt('common.no_visible_change'))
      + ((pl.changes||[]).length > 12 ? tt('portui.and_more_2',{x:pl.changes.length-12}) : ''),
    warnings:warn.length ? '\n\n' + warn.join('\n') : ''}))) return;
  p.busy = true;
  let res;
  try{ res = await api.post('/api/port/apply',
        Object.assign(portBody(), {clear_strings_bin:clearBinOn()})); }
  catch(e){ res = {error:errText(e)}; }
  finally{ if(portState === p) p.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  closeModal();
  toast(tt('portui.ported_n_noun_into_dest_undo_in_log',{n:(res.plan&&res.plan.rows||[]).length||p.sel.size,noun,dest:p.dest}), 5200);
  portState = null;
  // the destination is the mod on screen, and its file just changed under it
  if(p.kind === 'traits'){ state.tr = null; loadTraits(); }
  else { state.an = null; loadAncillaries(); }
}
