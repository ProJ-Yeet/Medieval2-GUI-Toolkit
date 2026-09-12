/* campnew.js - Campaign Map: making a new campaign out of one that works

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   NEW CAMPAIGN - Phase 24, M15.

   Every name here starts `cnw`. It lives inside 20b's campaign browser, under
   the list, because "make another one" is a thing to want while looking at the
   ones there are - and because the browser is already the screen that knows
   what a campaign is made of.

   THE FORM IS THREE BOXES AND THE REST IS SAID RATHER THAN ASKED. A new
   campaign is a copy: which one to copy, what the folder is called, and what
   the new-game menu calls it. Everything else - the compiled map left behind,
   the header set to the new name, every description key rewritten under the new
   token - follows from those three and is in the plan where it can be read.

   WHERE THE FOLDER GOES IS THE ONE THING THIS SCREEN KNOWS BETTER THAN THE
   ENGINE. The game's new-game menu reads the folders directly under
   world/maps/campaign and nothing deeper; this toolkit opens either. So a name
   with a slash in it is allowed, and it is warned about in the plan, in the
   words the server uses.
   ===================================================================== */

/* ---------- state ---------- */

function cnwNew(mod){
  return {mod, open: false, loading: false, err: '', d: null,
          source: '', name: '', title: '', blurb: '',
          plan: null, busy: false};
}

function cnwOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cnw || state.cnw.mod !== c.mod) state.cnw = cnwNew(c.mod);
}

function cnwToggle(){
  cnwOpen();
  const k = state.cnw;
  if(!k) return;
  k.open = !k.open;
  activity('new campaign',
           k.open ? 'opened the new campaign form' : 'closed it');
  if(k.open && !k.d && !k.loading) cnwLoad();
  else cbrPaint();
}

async function cnwLoad(){
  const k = state.cnw;
  if(!k) return;
  k.loading = true; k.err = '';
  cbrPaint();
  let d;
  try{
    d = await api.get(`/api/campnew?mod=${enc(k.mod)}`,
                      {label: 'reading what could be copied'});
  }catch(e){
    if(state.cnw !== k) return;
    k.loading = false; k.err = errText(e); cbrPaint(); return;
  }
  if(state.cnw !== k) return;
  k.loading = false;
  k.d = d;
  // the campaign the screen is reading, when it is one that can be copied
  const here = typeof cbrCurrent === 'function' ? cbrCurrent() : '';
  const rows = d.sources || [];
  k.source = (rows.find(r => r.campaign === here) || rows[0] || {}).campaign || '';
  cbrPaint();
}

function cnwSet(field, value){
  const k = state.cnw;
  if(!k) return;
  k[field] = value;
  k.plan = null;                  // it was worked out for different answers
  cbrPaint();
}

//: The form's boxes, straight through. The server owns every rule about them -
//: what a folder may be called, whether one is already there - so the browser
//: does not repeat any of it and cannot disagree with it.
function cnwBody(){
  const k = state.cnw;
  return {mod: k.mod, source: k.source, name: k.name.trim(),
          title: k.title.trim(), blurb: k.blurb.trim()};
}

/* ---------- the plan, and the save ---------- */

async function cnwPlan(){
  const k = state.cnw;
  if(!k || k.busy) return;
  k.busy = true; k.plan = null;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campnew/plan', cnwBody(),
                            {label: 'working out the copy'}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.cnw !== k) return;
  k.plan = res.plan || {errors: [res.error || 'the plan came back empty']};
  cbrPaint();
}

async function cnwApply(){
  const k = state.cnw;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(`Make ${p.name} out of ${p.source}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + `\n\n${p.files} file(s), ${cnwSize(p.bytes)}. Nothing existing is written `
    + 'over, and 🕑 Log can undo it.')) return;
  k.busy = true;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campnew/apply', cnwBody(),
                            {label: `making ${k.name}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || 'the copy failed'), 9000);
    cbrPaint();
    return;
  }
  toast(`${res.name} made from ${p.source}: ${res.files} file(s). `
    + '🕑 Log can undo it.', 7000);
  activity('new campaign', `${k.mod}: ${res.name} copied from ${p.source}`);
  k.plan = null; k.name = ''; k.title = ''; k.blurb = '';
  k.d = null;
  await cnwLoad();
  if(state.cbr){ state.cbr.d = null; cbrLoad(); }
}

//: Bytes, in thousands rather than in 1024s, because the change line beside it
//: prints the count itself and two numbers for one size that do not agree is
//: the sort of thing somebody stops trusting the whole panel over.
function cnwSize(n){
  if(!n) return '0 bytes';
  if(n < 1000) return `${n} bytes`;
  if(n < 1000000) return `${(n / 1000).toFixed(0)} KB`;
  return `${(n / 1000000).toFixed(1)} MB`;
}

/* ---------- drawing ----------

   Drawn by `cbrPaint`, because this is a block inside the browser's own panel
   and the browser owns that element. Nothing here touches the DOM directly. */

function cnwHtml(){
  const k = state.cnw;
  if(!k) return '';
  const head = `<div class="cmbar2">
    <button class="${k.open ? 'on' : ''}" onclick="cnwToggle()"
      title="Copy a campaign that works into a new folder of its own, with its own name on the new-game menu."
      >+ New campaign</button>
    <span class="sp"></span>
    ${k.loading ? '<span class="count">reading…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.err) return head + `<div class="w-bad">${esc(k.err)}</div>`;
  const d = k.d;
  if(!d) return head + '<div class="count">reading what could be copied…</div>';
  const rows = d.sources || [];
  if(!rows.length) return head + `<div class="count">${esc(k.mod)} has no
    campaign to copy. A new one is a copy of one that works: the engine reads
    more than a dozen files out of that folder and a missing one is a load
    failure with nothing on screen to explain it.</div>`;
  const src = rows.find(r => r.campaign === k.source) || {};
  return head + `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Copy</span>
      <select onchange="cnwSet('source', this.value)">
        ${rows.map(r => `<option value="${esc(r.campaign)}"${
          r.campaign === k.source ? ' selected' : ''}>${esc(r.title || r.leaf)}
          - ${r.files} files, ${cnwSize(r.bytes)}</option>`).join('')}
      </select></span></div>
    ${src.layers && src.layers.length ? `<div class="count">It ships
      ${src.layers.length} map layer${src.layers.length === 1 ? '' : 's'} of its
      own, so the copy gets a copy of those too and the two are then two maps to
      keep in step.</div>` : ''}
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Folder</span>
      <input value="${esc(k.name)}" placeholder="My_Campaign"
        oninput="cnwSet('name', this.value)"></span></div>
    <div class="count">A bare word: a letter first, then letters, digits,
      underscores or hyphens. It goes under <code>${esc(d.dir)}</code>, and the
      engine's new-game menu reads the folders directly under that one -
      ${d.menu.length} there now. A name with a slash in it nests, which this
      screen opens and the menu does not.</div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">On the menu</span>
      <input value="${esc(k.title)}"
        placeholder="${esc(src.title || 'the same as the one it is copied from')}"
        oninput="cnwSet('title', this.value)"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Its blurb</span>
      <input value="${esc(k.blurb)}" placeholder="inherited"
        oninput="cnwSet('blurb', this.value)"></span></div>
    <div class="count">${d.have_descriptions
      ? `Both go into <code>${esc(d.descriptions)}</code>, with every faction's
         title and blurb copied across under the new campaign's own key.`
      : `This mod ships only the compiled archive of
         <code>${esc(d.descriptions)}</code>, which is where the keys would
         go.`}</div>
    <div class="cmbar2">
      <button onclick="cnwPlan()" ${k.busy ? 'disabled' : ''}
        >${k.busy && !k.plan ? 'working it out…' : 'Work out the copy'}</button>
      <span class="sp"></span>
    </div>
    ${cnwPlanHtml(k)}`;
}

function cnwPlanHtml(k){
  const p = k.plan;
  if(!p) return '';
  if((p.errors || []).length) return `<div class="w-bad">
    ${p.errors.map(e => esc(e)).join('<br>')}</div>`;
  return `<div class="cbrrow">
    <div class="k">${p.files} file${p.files === 1 ? '' : 's'},
      ${cnwSize(p.bytes)} <span class="count">into
      <code>${esc(p.folder)}</code></span></div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    <div class="cmbar2">
      <button class="primary" onclick="cnwApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? 'copying…' : `Make ${esc(p.name)}`}</button>
      <span class="sp"></span>
      <span class="count">Nothing existing is written over. 🕑 Log can undo it.</span>
    </div>
  </div>`;
}
