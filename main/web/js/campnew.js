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
  activity(tt('campnew.new_campaign'),
           k.open ? tt('campnew.opened_the_new_campaign_form') : tt('common.closed_it'));
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
                      {label: tt('campnew.reading_what_could_be_copied')});
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
                            {label: tt('campnew.working_out_the_copy')}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.cnw !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  cbrPaint();
}

async function cnwApply(){
  const k = state.cnw;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(tt('campnew.make_out_of',{name:p.name,source:p.source})
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + tt('campnew.file_s_nothing_existing_is_written',{files:p.files,x:cnwSize(p.bytes)})
    + tt('campnew.over_and_log_can_undo_it'))) return;
  k.busy = true;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campnew/apply', cnwBody(),
                            {label: `making ${k.name}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('campnew.the_copy_failed')), 9000);
    cbrPaint();
    return;
  }
  toast(tt('campnew.made_from_file_s',{name:res.name,source:p.source,files:res.files})
    + tt('common.log_can_undo_it'), 7000);
  activity(tt('campnew.new_campaign'), tt('campnew.copied_from',{mod:k.mod,name:res.name,source:p.source}));
  k.plan = null; k.name = ''; k.title = ''; k.blurb = '';
  k.d = null;
  await cnwLoad();
  if(state.cbr){ state.cbr.d = null; cbrLoad(); }
}

//: Bytes, in thousands rather than in 1024s, because the change line beside it
//: prints the count itself and two numbers for one size that do not agree is
//: the sort of thing somebody stops trusting the whole panel over.
function cnwSize(n){
  if(!n) return tt('campnew.0_bytes');
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
      title="${ttA('campnew.copy_a_campaign_that_works_into')}"
      >${tt('campnew.new_campaign_2')}</button>
    <span class="sp"></span>
    ${k.loading ? `<span class="count">${tt('common.reading_2')}</span>` : ''}
  </div>`;
  if(!k.open) return head;
  if(k.err) return head + `<div class="w-bad">${esc(k.err)}</div>`;
  const d = k.d;
  if(!d) return head + `<div class="count">${tt('campnew.reading_what_could_be_copied_2')}</div>`;
  const rows = d.sources || [];
  if(!rows.length) return head + `<div class="count">${tt('campnew.has_no_campaign_to_copy_a',{mod:esc(k.mod)})}</div>`;
  const src = rows.find(r => r.campaign === k.source) || {};
  return head + `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('campnew.copy')}</span>
      <select onchange="cnwSet('source', this.value)">
        ${rows.map(r => `<option value="${esc(r.campaign)}"${
          r.campaign === k.source ? ' selected' : ''}>${tt('campnew.files',{x:esc(r.title || r.leaf),files:r.files,x2:cnwSize(r.bytes)})}</option>`).join('')}
      </select></span></div>
    ${src.layers && src.layers.length ? `<div class="count">${tt('campnew.it_ships_map_layer_of_its',{layers_n:src.layers.length,x:src.layers.length === 1 ? '' : 's'})}</div>` : ''}
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('campnew.folder')}</span>
      <input value="${esc(k.name)}" placeholder="My_Campaign"
        oninput="cnwSet('name', this.value)"></span></div>
    <div class="count">${tt('campnew.a_bare_word_a_letter_first',{dir:esc(d.dir),menu_n:d.menu.length})}</div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('common.on_the_menu')}</span>
      <input value="${esc(k.title)}"
        placeholder="${esc(src.title || tt('campnew.the_same_as_the_one_it'))}"
        oninput="cnwSet('title', this.value)"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('campnew.its_blurb')}</span>
      <input value="${esc(k.blurb)}" placeholder="${ttA('campnew.inherited')}"
        oninput="cnwSet('blurb', this.value)"></span></div>
    <div class="count">${d.have_descriptions
      ? tt('campnew.both_go_into_with_every_factions',{descriptions:esc(d.descriptions)})
      : tt('campnew.this_mod_ships_only_the_compiled',{descriptions:esc(d.descriptions)})}</div>
    <div class="cmbar2">
      <button onclick="cnwPlan()" ${k.busy ? 'disabled' : ''}
        >${k.busy && !k.plan ? tt('common.working_it_out') : tt('campnew.work_out_the_copy')}</button>
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
    <div class="k">${tt('campnew.file_into',{files:p.files,files2:p.files === 1 ? '' : 's',x:cnwSize(p.bytes),folder:esc(p.folder)})}</div>
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    <div class="cmbar2">
      <button class="primary" onclick="cnwApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? tt('campnew.copying') : tt('campnew.make',{name:esc(p.name)})}</button>
      <span class="sp"></span>
      <span class="count">${tt('campnew.nothing_existing_is_written_over_log')}</span>
    </div>
  </div>`;
}
