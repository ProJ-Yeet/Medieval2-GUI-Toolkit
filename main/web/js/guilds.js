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
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s guilds…</div>';
  let r;
  try{ r = await api.get('/api/guilds?mod=' + enc(mod)); }
  catch(e){ if(stale('guilds', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read the guild file.<br>
      <span class="count">${esc(errText(e))}</span><br>
      <span class="count">Guilds live in data/export_descr_guilds.txt</span><br><br>
      <button class="primary" onclick="loadGuilds()">Retry</button></div>`; return; }
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
      <button class="trnew" onclick="guNew()">＋ New guild</button>
      ${guUndeclaredHtml()}
      ${findingsHtml('guilds', guFindingList(), 'guOpen')}
      <div class="trrows">${rows.map(guRowHtml).join('')
        || '<div class="count" style="padding:8px">No guild matches.</div>'}</div>
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
    <b>${list.length} guild${list.length===1?'':'s'} get points and do not exist.</b>
    Triggers in this file award guild points to ${list.map(esc).join(', ')}, and no
    <code>Guild</code> block declares ${list.length===1?'it':'them'}, so those
    points go nowhere.
    ${list.map(n=>`<button class="trnew" style="margin:4px 4px 0 0"
      onclick="guNew('${q1(esc(n))}')">＋ Declare ${esc(n)}</button>`).join('')}
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
    <div class="sub">${r.building?esc(r.building):'<b>no building</b>'}${
      r.levels && r.levels.length?` · ${r.levels.join(' / ')}`:''}${
      r.awards?` · ${r.awards} trigger line${r.awards===1?'':'s'}`
              :' · <b>nothing awards it points</b>'}${
      r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</div>
  </button>`;
}

async function guOpen(name){
  const g = state.gu;
  if(!(g.guilds||[]).some(r => r.name === name)) return;   // an undeclared name
  activity('opened guild', `${name} in ${state.src}`);
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
  g.d = {name:'', label:'(new guild)', w:w, trigs:[], findings:[], awards:[],
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
  if(!g.sel && !g.adding) return `<div class="empty">Pick a guild on the left.<br>
    <span class="count">${(g.guilds||[]).length} guild${
      (g.guilds||[]).length===1?'':'s'}, ${g.triggers} trigger${
      g.triggers===1?'':'s'} and ${g.awards} point line${
      g.awards===1?'':'s'} in ${esc(g.file||'')}</span></div>`;
  if(!d) return '<div class="empty">Reading the guild…</div>';
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(g.adding ? 'New guild' : d.label || d.name)}</b>
        ${d.awards?`<span class="count">${d.awards.length} point line${
          d.awards.length===1?'':'s'}</span>`:''}</div>
      <span class="sp"></span>
      ${g.adding ? '' : `<button class="${d.cv?'on':''}" title="Show this guild exactly as
export_descr_guilds.txt stores it, beside the form. Hover a box to light up its
line; edit either side and the other follows."
        onclick="guCvToggle()">&lt;/&gt; Code view</button>
      <button class="danger" onclick="guDelete()">Delete</button>`}
      <button class="primary" onclick="guSave()">${g.adding?'Create guild':'Save'}</button>
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
    <div class="trsechead">The guild <span class="count">Two lines, and the
      engine reads both of them</span></div>
    <div class="trgrid">
      <label class="lbl" data-label="name">Name</label>
      <input data-label="name" value="${esc(w.name)}" ${state.gu.adding?'':'disabled'}
        placeholder="masons_guild" oninput="guSet('name',this.value)">
      <label class="lbl" data-label="building">Building tree</label>
      <div data-label="building">
        <input value="${esc(w.building)}" list="guBuildings"
          placeholder="guild_masons_guild"
          oninput="guSet('building',this.value.trim())">
        <datalist id="guBuildings">${(voc.buildings||[])
          .filter(b => b.indexOf('guild_') === 0)
          .map(b=>`<option value="${esc(b)}">`).join('')}</datalist>
        <div class="trhint">The <code>export_descr_buildings.txt</code> line this
          guild grants. ${known ? 'Every <code>guild_</code> line in this mod is offered.'
          : 'This mod keeps its EDB in the packed data, so there is no list to offer '
            + 'and nothing here is checked against one.'}</div>
      </div>
      <label class="lbl" data-label="levels">Point thresholds</label>
      <div data-label="levels">
        <input value="${esc(w.levels)}" placeholder="100 250 500" style="width:180px"
          oninput="guSet('levels',this.value)">
        ${levels.length === 3
          ? `<div class="trhint">Tier 1 at ${esc(levels[0])} guild points, tier 2 at
             ${esc(levels[1])}, tier 3 at ${esc(levels[2])}.</div>`
          : `<div class="trhint w-warn">Three numbers, counting upward - one per
             guild tier. 20 of the 21 guilds in the installed mods write three.</div>`}
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
    <div class="trsechead">Points <span class="count">what earns this guild its
      points, and how many</span></div>
    <table class="gutbl"><tbody>${rows.map(a=>`<tr>
      <td>${esc(a.trigger)}</td>
      <td style="text-align:right"><b>${esc(a.points)}</b></td>
      <td>${esc(a.scope_label || a.scope)}</td>
      <td class="count">line ${a.line}</td>
    </tr>`).join('')}</tbody></table>
  </section>`;
}

function guTriggersHtml(d){
  if(state.gu.adding) return `<section class="trsec">
    <div class="trsechead">Triggers</div>
    <div class="count" style="padding:6px">Create the guild first, then add the
      triggers that give it points. A trigger cannot name a guild the file has
      not declared yet.</div></section>`;
  return `<section class="trsec">
    <div class="trsechead">Triggers <span class="count">${d.trigs.length
      ? 'what awards this guild its points'
      : 'nothing awards this guild any points'}</span></div>
    ${d.trigs.length ? '' : `<div class="trfind w-warn">No trigger in this file
      awards a guild point to <b>${esc(d.name)}</b>, so it never reaches its
      first tier and the building it grants can never be built.</div>`}
    ${d.trigs.map((t,i)=>`<div class="trtrig">
      <div class="trtrighead">
        <b>${esc(t.name)}</b>
        <span class="sp"></span>
        <button class="trgdel" title="Remove this trigger"
          onclick="guDelTrigger(${i})">✕</button>
      </div>
      <div id="gutrg-${i}"></div>
    </div>`).join('')}
    <button class="trgadd" onclick="guAddTrigger()">＋ Add trigger</button>
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
         effects:[{keyword:'Guild', args:[d.name, 's', '10']}]}});
  guDirty(true);
}
function guDelTrigger(i){
  const d = state.gu.d;
  const row = d.trigs[i];
  if(!row.added && !confirm(`Remove trigger ${row.name}?\n\n`
    + `It is written out of the file when you save.`)) return;
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
  if(g.adding && !d.w.name.trim()){ toast('A new guild needs a name', 3500); return; }
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
  if(!confirm(`Write: ${what}?\n\n` + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14 ? `\n…and ${p.changes.length - 14} more` : '')
    + ((p.warnings || []).length ? '\n\n' + p.warnings.slice(0, 3).join('\n') : '')
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')
    + `\n\nBacked up first, and 🕑 Log can undo it.`)) return;
  g.busy = true;
  let res;
  try{ res = await api.post('/api/guilds/apply', body); }
  finally{ g.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast('Saved. 🕑 Log can undo it.');
  const keep = body.action === 'delete' ? '' : body.guild;
  await loadGuilds();
  if(keep) guOpen(keep);
}
