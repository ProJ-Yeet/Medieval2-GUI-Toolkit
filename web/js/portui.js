/* portui.js — “Port from another mod”, shared by the Traits and Ancillaries modes

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html — there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= PORT =======================
   The one dialog in the toolkit that reads TWO mods: pick records in another
   mod, and they land in this one — the definition block, the triggers that
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
   and ExcludedAncillaries, and the triggers keep every condition — none of that
   is rewritten to suit the destination, because guessing a substitution is how a
   port silently becomes a different trait. What will not work over there is
   listed instead, while it is still a preview. */

// {kind, source, dest, ov, sel:Set, q, plan, busy, withTriggers, overwrite}
let portState = null;

const PORT_NOUN = {traits:'trait', ancillaries:'ancillary'};

/* Opened from the Traits or the Ancillaries list. The destination is always the
   mod being edited — this is a way IN to the mod on screen, not a general
   two-mod transfer, and offering a destination picker would only invite writing
   into a mod you are not looking at. */
function portOpen(kind){
  const others = (state.mods||[]).map(m=>m.name).filter(n=>n!==state.src);
  if(!others.length){
    toast('There is only one mod here to read from. Point the toolkit at your '
        + 'mods folder in ⚙ Settings if that is wrong.', 6000); return;
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
  const body = !ov ? `<div class="empty">Reading ${esc(p.source)}’s ${esc(noun)}s…</div>`
    : ov.error ? `<div class="w-bad">${esc(ov.error)}</div>`
    : `<div class="count" style="margin:8px 0">${ov.count} ${esc(noun)}${
        ov.count===1?'':'s'} in <b>${esc(ov.source)}</b> · ${ov.already} of them
        already exist in <b>${esc(ov.dest)}</b>
        ${ov.dest_error?`<br><span class="w-bad">${esc(ov.dest_error)}</span>`:''}</div>
      <div class="barrow">
        <input placeholder="Filter…" value="${esc(p.q)}" style="flex:1"
          oninput="portState.q=this.value;portRowsPaint()">
        <label class="chk"><input type="checkbox" ${p.onlyNew?'checked':''}
          onchange="portState.onlyNew=this.checked;portRowsPaint()">
          hide the ${ov.already} this mod already has</label>
        <span class="count" id="portCount"></span>
      </div>
      <div class="portlist" id="portList">${rows.map(portRowHtml).join('')}</div>`;
  document.getElementById('modal').innerHTML = `
    <h2>Port ${esc(noun)}s into <span class="pill">${esc(p.dest)}</span></h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:8px">${docPoints(
        `Each one brings three things, because a ${esc(noun)} is three things:`,[
        'its block, at the top of the file',
        'every trigger in the other mod that grants it, appended to this mod’s '
          + 'trigger section',
        'its text keys — without them the character screen crashes the first time '
          + `anyone has the ${esc(noun)}`])}</div>
      <div class="barrow">
        <span class="count">Read from</span>
        <select onchange="portPickSource(this.value)">${others.map(n =>
          `<option value="${esc(n)}"${n===p.source?' selected':''}>${esc(n)}</option>`).join('')}</select>
        <span class="count">→ written into <b>${esc(p.dest)}</b></span>
      </div>
      ${body}
      <fieldset style="margin-top:10px"><legend>How</legend>
        <label class="chk"><input type="checkbox" ${p.withTriggers?'checked':''}
          onchange="portState.withTriggers=this.checked;portStale()">
          bring the triggers that grant it</label>
        <div class="count" style="margin:2px 0 6px">Off, the ${esc(noun)} exists in
          this mod and nothing ever gives it — useful only when you mean to write
          your own trigger for it.</div>
        <label class="chk"><input type="checkbox" ${p.overwrite?'checked':''}
          onchange="portState.overwrite=this.checked;portStale()">
          replace what is already there</label>
        <div class="count" style="margin-top:2px">Off (the safe default), a name
          this mod already has is skipped and said so. On, its block <b>and its
          wording</b> are overwritten with the other mod’s.</div>
      </fieldset>
      <div id="portPreview"></div>
    </div>
    <div class="foot">
      <span class="count" id="portSel"></span>
      ${cleanerBoxHtml()}
      <button onclick="closeModal()">Close</button>
      <button onclick="portPreview()">Probe</button>
      <button class="primary" onclick="portApply()">Port them</button>
    </div>`;
  portRowsPaint();
}

function portRowHtml(r){
  const on = portState.sel.has(r.name);
  return `<label class="portrow${r.exists?' here':''}">
    <input type="checkbox" ${on?'checked':''}
      onchange="portTick('${q1(esc(r.name))}',this.checked)">
    <span class="pn">${esc(r.label||r.name)}</span>
    <span class="count">${r.triggers
      ? `${r.triggers} trigger${r.triggers===1?'':'s'}`
      : '<b class="w-warn">nothing grants it there</b>'} · ${r.keys} text key${
      r.keys===1?'':'s'}${r.exists?' · <b class="w-warn">already in this mod</b>':''}</span>
  </label>`;
}

// The list only. Ticking a row must not rebuild the dialog around it — 799 rows
// is the biggest list in the toolkit outside Strings.
function portRowsPaint(){
  const p = portState; if(!p || !p.ov || p.ov.error) return;
  const rows = portRows();
  const list = document.getElementById('portList');
  if(list) list.innerHTML = rows.map(portRowHtml).join('')
    || `<div class="count" style="padding:8px">Nothing matches.</div>`;
  const c = document.getElementById('portCount');
  if(c) c.textContent = `${rows.length}/${p.ov.count}`;
  const s = document.getElementById('portSel');
  if(s) s.textContent = p.sel.size
    ? `${p.sel.size} picked` : 'nothing picked yet';
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
  if(!p.sel.size){ toast(`Tick at least one ${PORT_NOUN[p.kind]||'record'}.`); return null; }
  box.innerHTML = '<div class="preview">Planning…</div>';
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
    <div class="srow shead"><span class="sicon">⇩</span><span class="stext">What this writes</span></div>
    ${li('', changes)}
    ${(pl.changes||[]).length>20
      ? `<div class="srow"><span class="sicon">·</span><span class="stext">
         <i>…and ${pl.changes.length-20} more</i></span></div>` : ''}
    ${li('warn', pl.warnings)}${li('bad', pl.errors)}
    ${(pl.skipped||[]).length
      ? `<div class="srow warn"><span class="sicon">!</span><span class="stext">
         ${pl.skipped.length} already here and left alone:
         ${esc(pl.skipped.slice(0,8).join(', '))}${pl.skipped.length>8?'…':''}</span></div>` : ''}
  </div>`;
}

async function portApply(){
  const p = portState;
  if(!p || p.busy) return;
  const pl = p.plan || await portPreview();
  if(!pl) return;
  if((pl.errors||[]).length){ toast('✗ ' + pl.errors[0], 6000); return; }
  if(!pl.ok){ toast('Nothing to write — everything picked is already here.', 5000); return; }
  const noun = PORT_NOUN[p.kind] || 'record';
  const lines = (pl.changes||[]).slice(0, 12);
  const warn = (pl.warnings||[]).slice(0, 5).map(w => '⚠ ' + w);
  if(!confirm(`Port ${p.sel.size} ${noun}(s) from ${p.source} into ${p.dest}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((pl.changes||[]).length > 12 ? `\n…and ${pl.changes.length-12} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nBoth files are backed up first, and 🕑 Log → Undo puts them back.')) return;
  p.busy = true;
  let res;
  try{ res = await api.post('/api/port/apply',
        Object.assign(portBody(), {clear_strings_bin:clearBinOn()})); }
  catch(e){ res = {error:errText(e)}; }
  finally{ if(portState === p) p.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  closeModal();
  toast(`Ported ${(res.plan&&res.plan.rows||[]).length||p.sel.size} ${noun}(s) into `
      + `${p.dest} ✓  (undo in 🕑 Log)`, 5200);
  portState = null;
  // the destination is the mod on screen, and its file just changed under it
  if(p.kind === 'traits'){ state.tr = null; loadTraits(); }
  else { state.an = null; loadAncillaries(); }
}
