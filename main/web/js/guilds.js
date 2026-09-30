/* guilds.js - Guilds mode: export_descr_guilds.txt, both halves of it

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= GUILDS MODE (18a) =======================
   The file the toolkit has refused against since Phase 12 and could not open:
   Buildings says "this `guild_` requirement has no matching entry" and there was
   nowhere to go and add one. This is that somewhere.

   Like Traits, a guild is two things in two places. The top of the file says
   what it IS - which building tree it grants and the three point thresholds its
   tiers sit at. Past `;== TRIGGER DATA ==`, the triggers say how a settlement
   ever EARNS those points. One without the other tells you nothing, so the
   screen shows the block above and every trigger whose `Guild` line names this
   guild below, in the shared builder from Phase 7.

   THE PAGE NEVER PARSES A GAME FILE. Everything here is /api/guilds, /api/guild
   and /api/guilds/plan|apply.

   Three things the file imposes, all visible here:

     * a `Guild` line with two words is a definition and one with four is an
       effect. It is the same keyword, which is why the server tells them apart
       by word count and why this screen can show the two lists separately.
     * the scope letter is `s`, `o` or `a` - this settlement, every settlement
       the faction owns, or every settlement in the world. Measured off 507 real
       lines; the reference tool documents only the first two.
     * points can be awarded to a guild nothing declares, and both installed
       mods do it. Those points go nowhere, so the undeclared names are listed
       at the top of the list with a button that declares one. */

const GU_BLANK = {name:'', building:'', levels:'100 250 500'};

async function loadGuilds(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('guilds.reading_mod_guilds',{mod:esc(mod)})}</div>`;
  let r;
  try{ r = await api.get('/api/guilds?mod=' + enc(mod)); }
  catch(e){ if(stale('guilds', mod)) return;
    main.innerHTML = `<div class="empty">${tt('guilds.couldnt_read_the_guild_file_guilds',{errText:esc(errText(e))})}<br><br>
      <button class="primary" onclick="loadGuilds()">${tt('common.retry')}</button></div>`; return; }
  if(stale('guilds', mod)) return;
  state.gu = Object.assign({sel:'', d:null, busy:false, adding:false}, r);
  undoReset();
  renderGuilds();
}

function renderGuilds(){
  const g = state.gu;
  if(!g){ loadGuilds(); return; }
  const strip = minorTabsHtml('', 'data/' + (g.file || 'export_descr_guilds.txt'));
  const rows = guRows();
  count.textContent = `${rows.length}/${(g.guilds||[]).length}`;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <div class="trnewrow">
        <button class="trnew" onclick="guNew()">${tt('guilds.new_guild')}</button>
      </div>
      ${guUndeclaredHtml()}
      ${findingsHtml('guilds', guFindingList(), 'guOpen')}
      <div class="trrows">${rows.map(guRowHtml).join('')
        || `<div class="count" style="padding:8px">${tt('guilds.no_guild_matches')}</div>`}</div>
    </div>
    <div class="trmain" id="guMain">${guDetailHtml()}</div>
  </div>`;
}

/* The findings banner wants {name, message}; the server says {guild, message},
   because a finding can be about a name no block declares. */
function guFindingList(){
  return (state.gu.findings || []).map(f =>
    Object.assign({}, f, {name:f.guild || ''}));
}

/* Points awarded to a guild nothing declares. This is the fault the Buildings
   module could see the shadow of and never name, so it is the first thing on
   the screen rather than a row in the findings list - and it comes with the fix
   beside it, because declaring the guild is the only thing anyone would do. */
function guUndeclaredHtml(){
  const list = state.gu.undeclared || [];
  if(!list.length) return '';
  return `<div class="trnote w-warn" style="margin:6px 0">
    ${ttN('guilds.undeclared_guilds_note',list.length,{names:list.map(esc).join(', '),buttons:list.map(n=>`<button class="trnew" style="margin:4px 4px 0 0"
      onclick="guNew('${q1(esc(n))}')">${tt('guilds.declare',{x:esc(n)})}</button>`).join('')})}
  </div>`;
}

// Filtered in the page: 21 rows across both installed mods is a list, not a query.
function guRows(){
  const q = search.value.trim().toLowerCase();
  const rows = state.gu.guilds || [];
  if(!q) return rows;
  return rows.filter(r => r.name.toLowerCase().includes(q)
    || (r.building||'').toLowerCase().includes(q));
}

function guRowHtml(r){
  const on = state.gu.sel === r.name;
  return `<button class="trrow${on?' on':''}" onclick="guOpen('${q1(esc(r.name))}')">
    <div class="nm">${esc(r.name)}</div>
    <div class="sub">${r.building?esc(r.building):`<b>${tt('guilds.no_building')}</b>`}${
      r.levels && r.levels.length?` · ${r.levels.join(' / ')}`:''}${
      r.awards?ttN('guilds.trigger_line_count',r.awards)
              :` ${tt('guilds.nothing_awards_it_points')}`}${
      r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</div>
  </button>`;
}

async function guOpen(name){
  const g = state.gu;
  if(!(g.guilds||[]).some(r => r.name === name)) return;   // an undeclared name
  activity(tt('guilds.opened_guild'), `${name} in ${state.src}`);
  g.sel = name; g.adding = false; g.d = null;
  renderGuilds();
  let d;
  try{ d = await api.get(`/api/guild?mod=${enc(g.mod)}&name=${enc(name)}`); }
  catch(e){ d = {error:errText(e)}; }
  if(state.mode !== 'guilds' || state.gu !== g || g.sel !== name) return;
  g.d = d.error ? d : guWorking(d);
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
  guPaint();
  if(!d.error && state.settings.code_view) guCvToggle();
}

/* The working copy the boxes are bound to, beside the payload the server sent,
   so a save posts the whole form and the server writes only the lines that
   really differ. */
function guWorking(d){
  d.w = {name:d.name, building:d.building || '',
         levels:(d.levels_list || []).join(' ')};
  d.trigs = (d.triggers || []).map(t => ({name:t.name, ui:null, dirty:false, src:t}));
  d.dirty = false;
  return d;
}

function guNew(name){
  const g = state.gu;
  g.sel = ''; g.adding = true;
  const w = Object.assign({}, GU_BLANK, name ? {name:name,
    building:'guild_' + name.replace(/_guild$/, '') + '_guild'} : {});
  g.d = {name:'', label:tt('guilds.new_guild_2'), w:w, trigs:[], findings:[], awards:[],
    triggers:[], dirty:true,
    vocab:{buildings:g.buildings || [], buildings_known:!!g.buildings_known,
           scopes:g.scopes || {}, guilds:(g.guilds||[]).map(r=>r.name)}};
  renderGuilds();
}

function guPaint(){
  const el = document.getElementById('guMain');
  if(el) el.innerHTML = guDetailHtml();
  const d = state.gu.d;
  if(d && d.cv){ cvWire(d.cv); cvBindHover(d.cv, document.getElementById('guGui')); }
  guWireTriggers();
}

// The form only - never the pane, which has the caret in it.
function guPaintForm(){
  const d = state.gu.d, el = document.getElementById('guGui');
  if(!d || !el) return;
  el.innerHTML = guFindingsHtml(d) + guFormHtml(d.w, d);
  if(d.cv) cvBindHover(d.cv, el);
}

/* ---- the detail pane ---- */
function guDetailHtml(){
  const g = state.gu, d = g.d;
  if(!g.sel && !g.adding) return `<div class="empty">${tt('guilds.pick_a_guild_hint',{guilds:ttN('guilds.guild_count',(g.guilds||[]).length),triggers:ttN('guilds.trigger_count',g.triggers),points:ttN('guilds.point_line_count',g.awards),file:esc(g.file||'')})}</div>`;
  if(!d) return `<div class="empty">${tt('guilds.reading_the_guild')}</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(g.adding ? tt('guilds.new_guild_3') : d.label || d.name)}</b>
        ${d.awards?`<span class="count">${ttN('guilds.point_line_count',d.awards.length)}</span>`:''}</div>
      <span class="sp"></span>
      ${g.adding ? '' : `<button class="${d.cv?'on':''}" title="${ttA('guilds.show_this_guild_exactly_as_export')}"
        onclick="guCvToggle()">${tt('common.code_view')}</button>
      <button class="danger" onclick="guDelete()">${tt('common.delete')}</button>`}
      <button class="primary" onclick="guSave()">${g.adding?tt('guilds.create_guild'):tt('common.save')}</button>
    </div>
    <div id="guGui">
      ${guFindingsHtml(d)}
      ${guFormHtml(d.w, d)}
    </div>
    ${guCvHtml()}
    ${guAwardsHtml(d)}
    ${guTriggersHtml(d)}`;
}

function guFindingsHtml(d){
  return (d.findings || []).map(f =>
    `<div class="trfind w-warn">${esc(f.message)}</div>`).join('');
}

function guFormHtml(w, d){
  const voc = d.vocab || {};
  const known = voc.buildings_known !== false;
  const levels = String(w.levels || '').trim().split(/\s+/).filter(Boolean);
  return `<section class="trsec">
    <div class="trsechead">${tt('guilds.the_guild_two_lines_and_the')}</div>
    <div class="trgrid">
      <label class="lbl" data-label="name">${tt('common.name')}</label>
      <input data-label="name" value="${esc(w.name)}" ${state.gu.adding?'':'disabled'}
        placeholder="masons_guild" oninput="guSet('name',this.value)">
      <label class="lbl" data-label="building">${tt('guilds.building_tree')}</label>
      <div data-label="building">
        <input value="${esc(w.building)}" list="guBuildings"
          placeholder="guild_masons_guild"
          oninput="guSet('building',this.value.trim())">
        <datalist id="guBuildings">${(voc.buildings||[])
          .filter(b => b.indexOf('guild_') === 0)
          .map(b=>`<option value="${esc(b)}">`).join('')}</datalist>
        <div class="trhint">${tt('guilds.the_export_descr_buildings_txt_line',{known:known ? tt('guilds.every_guild_line_in_this_mod')
          : tt('guilds.this_mod_keeps_its_edb_packed')})}</div>
      </div>
      <label class="lbl" data-label="levels">${tt('guilds.point_thresholds')}</label>
      <div data-label="levels">
        <input value="${esc(w.levels)}" placeholder="100 250 500" style="width:180px"
          oninput="guSet('levels',this.value)">
        ${levels.length === 3
          ? `<div class="trhint">${tt('guilds.tier_1_at_guild_points_tier',{levels:esc(levels[0]),levels2:esc(levels[1]),levels3:esc(levels[2])})}</div>`
          : `<div class="trhint w-warn">${tt('guilds.three_numbers_counting_upward_one_per')}</div>`}
      </div>
    </div>
  </section>`;
}

/* Every `Guild <name> <scope> <points>` line that feeds this guild, read-only
   and grouped by trigger, because the numbers are the question ("why does this
   never reach tier 3") and the trigger builder below is where they are changed. */
function guAwardsHtml(d){
  const rows = d.awards || [];
  if(!rows.length) return '';
  return `<section class="trsec">
    <div class="trsechead">${tt('guilds.points_what_earns_this_guild_its')}</div>
    <table class="gutbl"><tbody>${rows.map(a=>`<tr>
      <td>${esc(a.trigger)}</td>
      <td style="text-align:right"><b>${esc(a.points)}</b></td>
      <td>${esc(a.scope_label || a.scope)}</td>
      <td class="count">${tt('guilds.line',{line:a.line})}</td>
    </tr>`).join('')}</tbody></table>
  </section>`;
}

function guTriggersHtml(d){
  if(state.gu.adding) return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')}</div>
    <div class="count" style="padding:6px">${tt('guilds.create_the_guild_first_then_add')}</div></section>`;
  return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')} <span class="count">${d.trigs.length
      ? tt('guilds.what_awards_this_guild_its_points')
      : tt('guilds.nothing_awards_this_guild_any_points')}</span></div>
    ${d.trigs.length ? '' : `<div class="trfind w-warn">${tt('guilds.no_trigger_in_this_file_awards',{name:esc(d.name)})}</div>`}
    ${d.trigs.map((t,i)=>`<div class="trtrig">
      <div class="trtrighead">
        <b>${esc(t.name)}</b>
        <span class="sp"></span>
        <button class="trgdel" title="${ttA('common.remove_this_trigger')}"
          onclick="guDelTrigger(${i})">✕</button>
      </div>
      <div id="gutrg-${i}"></div>
    </div>`).join('')}
    <button class="trgadd" onclick="guAddTrigger()">${tt('common.add_trigger')}</button>
  </section>`;
}

// The builder paints itself into a slot by id and loads its vocabulary
// asynchronously, so it is created after the markup exists.
async function guWireTriggers(){
  const d = state.gu.d;
  if(!d || !d.trigs) return;
  for(let i = 0; i < d.trigs.length; i++){
    if(!document.getElementById('gutrg-' + i)) continue;
    const row = d.trigs[i];
    if(!row.ui){
      row.ui = trgCreate({mod:state.gu.mod, trigger:row.src,
        onChange:() => { row.dirty = true; guDirty(); }});
      await trgLoad(row.ui);
    }
    const here = document.getElementById('gutrg-' + i);
    if(here) here.innerHTML = trgHtml(row.ui);
  }
}

/* ---- edits ----
   State first, paint second. A change that alters the SHAPE of the form
   repaints; typing in a box does not, or the caret jumps out from under the
   user on every keystroke. */
function guSet(key, value){
  const d = state.gu.d; if(!d) return;
  d.w[key] = value;
  guDirty(false);
}
function guAddTrigger(){
  const d = state.gu.d; if(!d) return;
  const n = (d.name || 'guild').toLowerCase() + '_' + (d.trigs.length + 1);
  d.trigs.push({name:n, ui:null, dirty:true, added:true,
    src:{name:n, when_to_test:'BuildingCompleted', conditions:[],
         effects:[{keyword:tt('guilds.guild'), args:[d.name, 's', '10']}]}});
  guDirty(true);
}
function guDelTrigger(i){
  const d = state.gu.d;
  const row = d.trigs[i];
  if(!row.added && !confirm(tt('guilds.remove_trigger_confirm',{name:row.name}))) return;
  if(row.ui) trgDrop(row.ui);
  d.trigs.splice(i, 1);
  d.removed = (d.removed || []).concat(row.added ? [] : [row.name]);
  guDirty(true);
}
function guDirty(repaint){
  const d = state.gu.d;
  d.dirty = true;
  if(repaint) guPaint();
  // the GUI→pane half of the Code View contract: change a box and the text pane
  // is re-serialised by the server, through the serialiser the save itself uses
  if(d.cv) cvFromGui(d.cv);
}

/* ---- one guild as the file writes it ---- */
function guCvHtml(){
  const d = state.gu.d;
  return d && d.cv ? `<div id="guCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : '';
}

async function guCvToggle(){
  const d = state.gu.d; if(!d) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); guPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate(guCvHost());
  guPaint();
  await cvLoad(d.cv);
  if(state.gu.d !== d || !d.cv) return;
  guPaint();
}

function guCvHost(){
  return {kind:'guilds', mod:state.gu.mod, id:state.gu.d.name,
    where:'data/' + state.gu.file,
    edits:() => guEdits(),
    // The pane's own text becomes the truth once it has been typed into: it can
    // say things the boxes cannot (a comment, a key nobody put on the form), so
    // the form follows it and the save carries it verbatim.
    adopt:cv => { const d = state.gu.d;
      if(!cv.detail) return;
      d.w = {name:cv.detail.name, building:cv.detail.building || '',
             levels:(cv.detail.levels_list || []).join(' ')};
      // `base`, never `text`: with comment hiding on, `text` is the view with
      // the comment-only lines cut out, and saving that would delete them all.
      d.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => { guPaintForm(); }};
}

/* ---- writing ---- */
function guEdits(){
  const w = state.gu.d.w;
  return {name:w.name, building:w.building, levels:w.levels};
}

function guBody(action){
  const g = state.gu, d = g.d;
  const body = {mod:g.mod, guild:action === 'add' ? d.w.name : d.name, action};
  if(action !== 'delete'){
    body.edits = guEdits();
    if(d.raw) body.raw_block = d.raw;
    const adds = [], edits = [];
    for(const row of (d.trigs || [])){
      if(!row.ui || !row.dirty) continue;
      (row.added ? adds : edits).push({name:row.name, trigger:trgValue(row.ui)});
    }
    body.triggers = {adds, edits, removes:d.removed || []};
  }
  return body;
}

async function guSave(){
  const g = state.gu, d = g.d;
  if(g.adding && !d.w.name.trim()){ toast(tt('guilds.a_new_guild_needs_a_name'), 3500); return; }
  await guApply(guBody(g.adding ? 'add' : 'edit'),
                g.adding ? `create ${d.w.name}` : `save ${d.name}`);
}

async function guDelete(){
  const d = state.gu.d;
  await guApply(guBody('delete'), `delete ${d.name}`);
}

async function guApply(body, what){
  const g = state.gu;
  if(g.busy) return;
  g.busy = true;
  let plan;
  try{ plan = await api.post('/api/guilds/plan', body); }
  finally{ g.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 6000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const found = (p.findings || []).map(f => '⚠ ' + f.message);
  if(!confirm(tt('guilds.write_confirm',{what,changes:(lines.join('\n') || tt('common.no_visible_change'))
    + ((p.changes || []).length > 14 ? tt('guilds.and_more',{changes:p.changes.length - 14}) : '')
    + ((p.warnings || []).length ? '\n\n' + p.warnings.slice(0, 3).join('\n') : '')
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')}))) return;
  g.busy = true;
  let res;
  try{ res = await api.post('/api/guilds/apply', body); }
  finally{ g.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  const keep = body.action === 'delete' ? '' : body.guild;
  await loadGuilds();
  if(keep) guOpen(keep);
}
