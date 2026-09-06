/* stratcamp.js - Campaign Map: the campaign's own settings

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE CAMPAIGN PANEL - Phase 16j, first half.

   Every name here starts `cj`, and there was no `cj` name anywhere in the tree
   before this phase - checked, the way 16e checked `cp`, 16f `cchk`, 16g `cq`,
   16h `cs` and 16i `cx`.

   PYTHON OWNS THE RULES, AGAIN AND FOR THE SAME REASON. Whether a season is a
   season, whether a roster names a faction that has a block, whether a standing
   is inside the range every one of the 250 real ones sits in, whether
   `marian_reforms_activated` does anything: every one of those is decided in
   stratcamp.py and arrives here as a sentence with the number that made it a
   rule attached. What is drawn beside a box - which factions this campaign has,
   which AI labels it already uses - is the server's own data being shown, not a
   rule being applied twice.

   SO THE FORM ASKS, on the same 450 ms debounce 16h and 16i use. A plan is a
   file read, a splice and two parses, and it comes back with the findings the
   save would produce rather than a browser's guess at them. On the largest
   campaign installed that is around 220 ms.

   SIX TABS, SEVEN SAVES, ONE REQUEST. When it runs, Who plays, Each faction
   and Diplomacy are one form and one endpoint with a different `what`, because
   in the file they are one file. The diplomacy grid is the one that would have
   been tempting to make clever: it is drawn as it is read - one row per
   faction, both directions shown - because the two directions really are two
   separate lines and nothing in the engine makes one follow from the other.

   THE LAST TWO TABS ARE 16j-2 AND THEY ARE NOT THE SAME SHAPE. New faction
   makes and unmakes a whole campaign entry, and Winning edits a different file
   (`descr_win_conditions.txt`, `/api/map/wins`). They are here rather than in a
   panel of their own because a modder adding a faction does all of it in one
   sitting, and because the New faction form needs the faction list this panel
   is already holding.

   WHAT THE NEW FACTION FORM DOES NOT OFFER is a settlement or a general. The
   server will not clone the donor's - two factions cannot start in the same
   city - so the form does not pretend otherwise: it says what the new faction
   is missing and points at the two panels that fix it.
   ===================================================================== */

//: How long after the last keystroke the panel asks the server what it thinks.
const CJ_DEBOUNCE = 450;

/* ---------- state ---------- */
function cjNew(mod){
  return {mod, open: false, loading: false, err: '', d: null, tab: 'campaign',
          w: null, faction: '', busy: false, preview: null, timer: 0,
          // 16j-2's two tabs. `wins` is a second file and is not read until
          // somebody opens that tab, the way this whole panel is not read until
          // somebody opens it.
          wins: null, ww: null, winPick: '', winErr: '', winLoading: false};
}

async function cjOpen(force){
  const c = state.cmap;
  if(!c) return;
  const was = state.cj;
  if(was && was.mod === c.mod && was.d && !force){ cjPaint(); return; }
  const k = state.cj = cjNew(c.mod);
  k.open = was ? was.open : false;
  if(!k.open){ cjPaint(); return; }
  k.loading = true;
  cjPaint();
  let d;
  try{ d = await api.get(`/api/map/campaign?mod=${enc(c.mod)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cj !== k) return;
  k.loading = false;
  if(d.error){
    // 17f: no campaign file is not no factions. The panel falls back to the
    // faction screen alone, which reads a different file entirely.
    k.err = d.error; cjPaint(); cjSmOpen(); return;
  }
  k.d = d;
  cjReset();
  cjPaint();
  if(k.tab === 'faction') cjSmOpen(k.faction);
}

function cjToggle(){
  const k = state.cj;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.d) cjOpen(true); else cjPaint();
}

function cjTab(name){
  const k = state.cj;
  if(!k) return;
  k.tab = name;
  k.preview = null;
  cjReset();
  cjPaint();
  // 17f: the faction tab is two files now, and the second one is read the
  // moment the tab is opened rather than when the picker is touched
  if(name === 'faction') cjSmOpen(cjEnsureFaction());
}

/* The working copy every box edits and every save is built from - the same
   shape 16h and 16i use, and the shape the values beside it came off disk in,
   so whether anything has changed is a comparison rather than a flag. */
function cjReset(){
  const k = state.cj, d = k.d;
  if(!d) return;
  if(k.tab === 'wins'){ cjWinReset(); return; }
  if(!k.faction || !d.factions.some(f => f.name === k.faction))
    k.faction = (d.factions[0] || {}).name || '';
  const f = d.factions.find(x => x.name === k.faction) || {};
  k.w = {
    values: Object.assign({}, d.values),
    flags: (d.flags || []).slice(),
    rosters: {playable: (d.rosters.playable || []).slice(),
              unlockable: (d.rosters.unlockable || []).slice(),
              nonplayable: (d.rosters.nonplayable || []).slice()},
    scalars: {ai: f.ai || '', ai_label: f.ai_label || '',
              denari: f.denari === undefined ? '' : f.denari,
              denari_kings_purse: f.denari_kings_purse === undefined
                ? '' : f.denari_kings_purse},
    fflags: (f.flags || []).slice(),
    standings: Object.assign({}, f.standings || {}),
    relationships: Object.assign({}, f.relationships || {}),
    made: k.w && k.w.made ? k.w.made
      : {name: '', donor: (d.factions[0] || {}).name || '',
         roster: 'playable', diplomacy: true, denari: ''}
  };
}

/* ---------- 16j-2: the win conditions, which are a different file ---------- */

async function cjWinReset(){
  const k = state.cj;
  if(k.wins || k.winLoading) return;
  k.winLoading = true;
  let d;
  try{ d = await api.get(`/api/map/wins?mod=${enc(k.mod)}`
    + `&campaign=${enc(k.d.campaign)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cj !== k) return;
  k.winLoading = false;
  if(d.error){ k.winErr = d.error; cjPaint(); return; }
  k.wins = d;
  k.winPick = k.winPick || (d.records[0] || {}).faction || '';
  cjWinEdit();
  cjPaint();
}

//: The working copy of one record. Six slots, and a list is edited as the text
//: the file writes - space-separated names - because that is what it is.
function cjWinEdit(){
  const k = state.cj;
  const r = (k.wins.records || []).find(x => x.faction === k.winPick);
  k.ww = r ? {faction: r.faction,
              hold: (r.hold || []).join(' '), take: r.take || '',
              outlive: (r.outlive || []).join(' '),
              short_hold: (r.short_hold || []).join(' '),
              short_take: r.short_take || '',
              short_outlive: (r.short_outlive || []).join(' ')}
           : null;
}

function cjWinPick(who){
  const k = state.cj;
  k.winPick = who;
  k.preview = null;
  cjWinEdit();
  cjPaint();
}

function cjWinSet(slot, value){
  const k = state.cj;
  if(!k.ww) return;
  k.ww[slot] = value;
  cjPlanSoon();
  cjPaint();
}

function cjMade(key, value){
  const k = state.cj;
  k.w.made[key] = value;
  cjPlanSoon();
  cjPaint();
}

function cjPickFaction(name){
  const k = state.cj;
  if(!k) return;
  k.faction = name;
  k.preview = null;
  cjReset();
  cjPaint();
  cjSmOpen(name);
}

/* ---------- 17f: the other half of the same faction ----------

   `descr_sm_factions.txt` says what a faction IS - its culture, its religion,
   the two colours it paints the map with, its horde and its art. This file says
   what it starts the campaign WITH - its AI, its purse, its diplomacy. Nobody
   thinks of those as two modules, so they are one screen; they are still two
   engines and two saves, because they are two files and combining the SCREENS
   must not combine the WRITES.

   factions.js owns that half exactly as it did in its own mode: the same
   `/api/faction` read, the same `/api/factions/plan|apply` save, the same
   confirmation, the same undo. What changed there is only where it paints. */
async function cjSmOpen(slot){
  const c = state.cmap;
  if(!c || typeof facOpen !== 'function') return;
  if(slot && state.fac && state.fac.mod === c.mod
     && state.fac.sel === slot && state.fac.d) return;
  try{
    if(!state.fac || state.fac.mod !== c.mod) await facFetch(c.mod);
  }catch(e){
    state.fac = null;
    const el = document.getElementById('facMain');
    if(el) el.innerHTML = `<div class="empty"><span class="w-bad">✗ ${
      esc(errText(e))}</span></div>`;
    return;
  }
  if(state.mode !== 'campmap' || !state.cmap || state.cmap.mod !== c.mod) return;
  // the roster has arrived, so the picker can be drawn now whether or not the
  // campaign half ever read
  const want = slot || cjEnsureFaction();
  cjPaint();
  if(want) facOpen(want);
}

//: The faction the screen is on, defaulted to the first one either file has.
//: Returns '' when neither file has read yet, which is the only case where
//: there is nothing to draw at all.
function cjEnsureFaction(){
  const k = state.cj;
  if(!k) return '';
  const list = cjFactionList();
  if(!list.length) return '';
  if(!k.faction || !list.some(f => f.name === k.faction)) k.faction = list[0].name;
  return k.faction;
}

//: Every faction either file knows, in one list, with which of the two has it.
//: A slot in one and not the other is a real state - a mod with no campaign has
//: all of them in that state - and the screen says which rather than blanking.
function cjFactionList(){
  const k = state.cj, out = new Map();
  for(const f of ((k && k.d && k.d.factions) || []))
    out.set(f.name, {name: f.name, label: f.label || f.name, camp: true, sm: false});
  for(const r of ((state.fac && state.fac.factions) || [])){
    const e = out.get(r.name);
    if(e) e.sm = true;
    else out.set(r.name, {name: r.name, label: r.label || r.name, camp: false, sm: true});
  }
  return [...out.values()].sort((a, b) => a.label.localeCompare(b.label));
}

/* ---------- the boxes ---------- */

function cjValue(key, value){
  const k = state.cj;
  k.w.values[key] = value;
  cjPlanSoon();
  cjPaint();
}

function cjFlag(name, on, which){
  const k = state.cj;
  const list = which === 'faction' ? k.w.fflags : k.w.flags;
  const at = list.indexOf(name);
  if(on && at < 0) list.push(name);
  if(!on && at >= 0) list.splice(at, 1);
  cjPlanSoon();
  cjPaint();
}

function cjScalar(key, value){
  const k = state.cj;
  k.w.scalars[key] = value;
  cjPlanSoon();
  cjPaint();
}

//: Which of the three lists a faction is in. Nowhere is not an option here,
//: because the server calls a faction with a block and no list fatal - see
//: `camp.block_unlisted` - and offering it would be offering a refusal.
function cjRoster(who, list){
  const k = state.cj;
  for(const name of k.d.vocab.rosters){
    const at = k.w.rosters[name].indexOf(who);
    if(at >= 0) k.w.rosters[name].splice(at, 1);
  }
  k.w.rosters[list].push(who);
  cjPlanSoon();
  cjPaint();
}

function cjStanding(who, value){
  const k = state.cj;
  if(value === '') delete k.w.standings[who];
  else k.w.standings[who] = value;
  cjPlanSoon();
  cjPaint();
}

function cjRelation(who, how){
  const k = state.cj;
  if(!how) delete k.w.relationships[who];
  else k.w.relationships[who] = how;
  cjPlanSoon();
  cjPaint();
}

/* ---------- what the server makes of it ---------- */

function cjBody(){
  const k = state.cj, w = k.w;
  const body = {mod: k.mod, campaign: k.d.campaign, what: k.tab};
  if(k.tab === 'campaign'){ body.what = 'globals';
    body.values = w.values; body.flags = w.flags; }
  else if(k.tab === 'rosters'){ body.what = 'rosters';
    body.rosters = w.rosters; }
  else if(k.tab === 'diplomacy'){ body.what = 'standings';
    body.faction = k.faction; body.standings = w.standings; }
  else if(k.tab === 'create'){ body.what = 'create';
    body.faction = (w.made.name || '').trim().toLowerCase();
    body.donor = w.made.donor; body.roster = w.made.roster;
    body.diplomacy = !!w.made.diplomacy;
    if(String(w.made.denari).trim() !== '')
      body.scalars = {denari: w.made.denari}; }
  else { body.what = 'faction'; body.faction = k.faction;
    body.scalars = w.scalars; body.flags = w.fflags; }
  return body;
}

//: The win conditions are a different file and a different endpoint, so they
//: are a different body. Everything else about the round trip is the same.
function cjWinBody(action){
  const k = state.cj, w = k.ww;
  const body = {mod: k.mod, campaign: k.d.campaign,
                action: action || 'edit', faction: k.winPick};
  if(w) body.values = {hold: w.hold, take: w.take, outlive: w.outlive,
                       short_hold: w.short_hold, short_take: w.short_take,
                       short_outlive: w.short_outlive};
  return body;
}

function cjPlanSoon(){
  const k = state.cj;
  if(!k || !k.d || !k.w) return;
  clearTimeout(k.timer);
  k.timer = setTimeout(() => cjPlanNow(k), CJ_DEBOUNCE);
}

async function cjPlanNow(k){
  if(state.cj !== k || !k.d || !k.w) return;
  if(k.tab === 'wins'){
    if(!k.ww) return;
    let got;
    try{ got = await api.post('/api/map/wins_plan', cjWinBody()); }
    catch(e){ got = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
    if(state.cj !== k) return;
    k.preview = got.plan || null;
    cjPaint();
    return;
  }
  let res;
  try{ res = await api.post('/api/map/campaign_plan', cjBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.cj !== k) return;
  k.preview = res.plan || null;
  cjPaint();
}

async function cjSave(extra){
  const k = state.cj;
  if(!k || !k.d || k.busy) return;
  clearTimeout(k.timer);
  if(k.tab === 'wins') return cjWinSave(extra);
  const body = Object.assign(cjBody(), extra || {});
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/campaign_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); k.preview = plan.plan || null;
    cjPaint(); return; }
  const p = plan.plan || {};
  k.preview = p;
  cjPaint();
  const lines = (p.changes || []).slice(0, 14);
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  // Capped: a new faction declares a run for every other faction's diplomacy
  // row, which on the largest campaign installed is 25 of them and not a
  // sentence anybody reads.
  const runs = (p.spans || []).map(s => s[0] >= s[1] ? `line ${s[0]}`
    : `lines ${s[0]}-${s[1]}`);
  const spans = runs.slice(0, 6).join(', ')
    + (runs.length > 6 ? ` and ${runs.length - 6} more runs` : '');
  if(!confirm(`Write: ${body.what}`
    + (body.faction ? ` for ${body.faction}` : '')
    + ` in ${k.d.campaign}?\n\n`
    + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14
       ? `\n…and ${p.changes.length - 14} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + (spans ? `\n\nOnly ${spans} change.` : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/campaign_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('campaign', `${k.mod}: ${body.what}`
    + (body.faction ? ` ${body.faction}` : ''));
  const at = state.cmap && state.cmap.pick;
  await loadCampmap();
  if(at && state.cmap) cmapPick(at);
}

async function cjWinSave(extra){
  const k = state.cj;
  const body = Object.assign(cjWinBody(), extra || {});
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/wins_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); k.preview = plan.plan || null;
    cjPaint(); return; }
  const p = plan.plan || {};
  k.preview = p;
  cjPaint();
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  if(!confirm(`Write: ${body.action} the win conditions for ${body.faction}?`
    + '\n\n' + ((p.changes || []).join('\n') || 'no visible change')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/wins_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('campaign', `${k.mod}: win conditions ${body.faction}`);
  k.wins = null;
  cjWinReset();
}

//: Diplomacy is two saves because it is two sections of the file, and doing
//: both behind one button would be one confirm dialog over two backups.
function cjSaveRelations(){
  cjSave({what: 'relationships', faction: state.cj.faction,
          relationships: state.cj.w.relationships});
}

/* ---------- drawing ---------- */

/* 17f: the faction screen is two forms wide, and `descr_sm_factions.txt`'s half
   was drawn in a full-width pane in its own mode. The side column already knows
   how to be 620px - the code view asks for it - so the faction tab asks too,
   and gives it back on any other tab. */
function cjWide(){
  const k = state.cj, side = document.getElementById('cmSide');
  if(!side) return;
  const want = !!(k && k.open && k.tab === 'faction');
  if(want) side.classList.add('wide');
  else if(!(state.cmap && state.cmap.det && state.cmap.det.cv)) side.classList.remove('wide');
  if(typeof cmapResize === 'function' && cmapResize()) cmapPaint();
}

function cjPaint(){
  cjWide();
  const el = document.getElementById('cmCamp');
  if(!el) return;
  el.innerHTML = cjHtml();
}

function cjHtml(){
  const k = state.cj;
  if(!k) return '';
  const d = k.d;
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cjToggle()"
      title="The campaign's own settings: when it runs, who can play it, and who starts at war with whom."
      >\u{1F5D3} Campaign${k.open ? ' ✓' : ''}</button>
    ${d ? `<span class="count">${esc(d.name || d.campaign)} ·
      ${esc(d.values.start_date || '?')} to ${esc(d.values.end_date || '?')} ·
      ${d.factions.length} factions</span>` : ''}
    ${k.busy ? '<span class="count">working…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + `<div class="cxpanel count">reading the
    campaign…</div>`;
  /* 17f - the campaign half can be missing and the faction half still be
     there. A mod with no `descr_strat.txt` still has a `descr_sm_factions.txt`
     with every faction it ships in it, and the rule 16f and 16g settled applies
     here too: name the file that is missing, do not blank the form. */
  if(k.err || !d || !k.w){
    const slot = cjEnsureFaction();
    return head + `<div class="cxpanel">
      ${k.err ? `<div class="w-warn">${esc(k.err)}</div>` : ''}
      ${slot ? `<div class="cxform">${cjFactionPickerHtml()}${cjSmHtml()}</div>`
             : ''}</div>`;
  }
  const tabs = [['campaign', 'When it runs'], ['rosters', 'Who plays'],
                ['faction', 'Each faction'], ['diplomacy', 'Diplomacy'],
                ['create', 'New faction'], ['wins', 'Winning']];
  return head + `<div class="cxpanel">
    <div class="cqtabs">
      ${tabs.map(([id, label]) => `<button class="${k.tab === id ? 'on' : ''}"
        onclick="cjTab('${id}')">${label}</button>`).join('')}
    </div>
    ${(d.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`)
      .join('')}
    ${k.tab === 'campaign' ? cjGlobalsHtml()
      : k.tab === 'rosters' ? cjRostersHtml()
      : k.tab === 'faction' ? cjFactionHtml()
      : k.tab === 'create' ? cjCreateHtml()
      : k.tab === 'wins' ? cjWinsHtml() : cjDiplomacyHtml()}
    ${cjFindingsHtml()}
  </div>`;
}

function cjGlobalsHtml(){
  const k = state.cj, w = k.w, v = k.d.vocab;
  const box = (key, label, note) => `<div class="cmfield"><label>${label}</label>
    <input value="${esc(w.values[key] === undefined ? '' : w.values[key])}"
      oninput="cjValue('${key}', this.value)">
    ${note ? `<div class="count">${note}</div>` : ''}</div>`;
  return `<div class="cxform">
    <div class="csrow2">
      ${box('start_date', 'Starts', 'a year and ' + v.seasons.join(' or '))}
      ${box('end_date', 'Ends', '')}
    </div>
    <div class="csrow2">
      ${box('timescale', 'Years per turn', 'a decimal - vanilla writes 2.00')}
      ${box('free_upkeep_forts', 'Free upkeep in forts', 'blank means no line')}
    </div>
    <div class="csrow2">
      ${box('brigand_spawn_value', 'Brigands', 'higher is rarer')}
      ${box('pirate_spawn_value', 'Pirates', '')}
    </div>
    <div class="cmfield"><label>Flags</label>
      <div class="cjflags">${v.flags.map(f => `<label class="cjchk">
        <input type="checkbox"${w.flags.indexOf(f) >= 0 ? ' checked' : ''}
          onchange="cjFlag('${f}', this.checked)">${esc(f)}${
          v.dead_flags.indexOf(f) >= 0 ? ' <span class="count">(does nothing)</span>'
          : ''}</label>`).join('')}</div>
    </div>
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Save the campaign header</button>
    </div>
  </div>`;
}

/* Who plays.

   One radio per faction across the three lists, rather than three editable
   text lists. The engine takes the first list it meets a faction in, so a
   faction in two of them is a warning the server raises and a control that
   cannot express it is the better control. */
function cjRostersHtml(){
  const k = state.cj, w = k.w, v = k.d.vocab;
  const where = {};
  for(const list of v.rosters) for(const who of w.rosters[list]) where[who] = list;
  const rows = k.d.factions.map(f => `<div class="cxrow">
    <b>${esc(f.label || f.name)}</b>
    <span class="cjradio">${v.rosters.map(list => `<label class="cjchk">
      <input type="radio" name="cjr-${esc(f.name)}"${
        where[f.name] === list ? ' checked' : ''}
        onchange="cjRoster('${esc(f.name)}', '${list}')">${list}</label>`)
      .join('')}</span>
  </div>`).join('');
  return `<div class="cxform">
    <div class="cxlist">${rows}</div>
    <div class="count">The engine reads the first list it meets a faction in,
      so each one sits in exactly one.</div>
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Save the three lists</button>
    </div>
  </div>`;
}

function cjFactionPickerHtml(){
  const k = state.cj;
  return `<div class="cmfield"><label>Faction</label>
    <select onchange="cjPickFaction(this.value)">
      ${cjFactionList().map(f => `<option value="${esc(f.name)}"${
        f.name === k.faction ? ' selected' : ''}>${esc(f.label)}${
        f.camp && f.sm ? '' : f.camp ? ' · not in descr_sm_factions.txt'
                                     : ' · not in descr_strat.txt'}</option>`).join('')}
    </select></div>`;
}

function cjFactionHtml(){
  const k = state.cj, w = k.w, v = k.d.vocab;
  const f = k.d.factions.find(x => x.name === k.faction) || {};
  return `<div class="cxform">
    ${cjFactionPickerHtml()}
    ${cjCampFactionHtml(f, w, v)}
    ${cjSmHtml()}
  </div>`;
}

//: The `descr_sm_factions.txt` half, drawn by factions.js into a div of its
//: own. 17f: one screen, two forms, two Save buttons, and each one writes the
//: file it has always written.
function cjSmHtml(){
  const has = !!(state.fac && state.fac.exists);
  return `<div class="cjsm">
    <div class="cjsmhead">The faction itself
      <span class="count">data/descr_sm_factions.txt - its culture, religion,
        colours, horde and art. A separate file and a separate save.</span></div>
    ${has ? '' : `<div class="count">reading descr_sm_factions.txt…</div>`}
    <div id="facMain">${(typeof facDetailHtml === 'function' && state.fac)
      ? facDetailHtml() : ''}</div>
  </div>`;
}

//: What `descr_strat.txt` says this faction starts with. A slot the campaign
//: file has no block for says so rather than showing an empty form somebody
//: could type into and save into nothing.
function cjCampFactionHtml(f, w, v){
  if(!f.name) return `<div class="cjsmhead">The campaign
      <span class="count">data/${esc((state.cj.d && state.cj.d.campaign)
        || 'world/maps/campaign')}/descr_strat.txt</span></div>
    <div class="w-warn">This campaign has no block for
      <b>${esc(state.cj.faction || 'this faction')}</b>, so there is nothing here
      to edit. New faction, on the tab beside this one, writes one.</div>`;
  const list = `<datalist id="cjl-ai">${(v.ai || []).map(x =>
    `<option value="${esc(x)}">`).join('')}</datalist>
    <datalist id="cjl-label">${(v.ai_labels || []).map(x =>
    `<option value="${esc(x)}">`).join('')}</datalist>`;
  return `<div class="cjsmhead">The campaign
      <span class="count">descr_strat.txt - what it starts the campaign with</span></div>
    <div class="count">line ${f.line} · ${f.settlements} settlement${
      f.settlements === 1 ? '' : 's'} · ${f.characters} character${
      f.characters === 1 ? '' : 's'}${f.roster ? ' · ' + f.roster : ''}</div>
    <div class="csrow2">
      <div class="cmfield"><label>AI personality</label>
        <input list="cjl-ai" value="${esc(w.scalars.ai)}"
          oninput="cjScalar('ai', this.value)">
        <div class="count">two words, and no file on disk declares them - the
          list is what this campaign already uses.</div></div>
      <div class="cmfield"><label>AI label</label>
        <input list="cjl-label" value="${esc(w.scalars.ai_label)}"
          oninput="cjScalar('ai_label', this.value)"></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Treasury</label>
        <input type="number" value="${esc(w.scalars.denari)}"
          oninput="cjScalar('denari', this.value)"></div>
      <div class="cmfield"><label>King's purse</label>
        <input type="number" value="${esc(w.scalars.denari_kings_purse)}"
          oninput="cjScalar('denari_kings_purse', this.value)"></div>
    </div>
    <div class="cmfield"><label>Flags</label>
      <div class="cjflags">${v.faction_flags.map(x => `<label class="cjchk">
        <input type="checkbox"${w.fflags.indexOf(x) >= 0 ? ' checked' : ''}
          onchange="cjFlag('${x}', this.checked, 'faction')">${esc(x)}</label>`)
        .join('')}</div>
    </div>
    ${list}
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Save ${esc(state.cj.faction)}
        in descr_strat.txt</button>
    </div>`;
}

/* The diplomacy grid.

   One row per other faction, showing both what this faction thinks of them and
   the relationship written between them. The reverse direction is shown beside
   it, greyed, because it is a different line of the file and changing one does
   not change the other - which is the single most surprising thing about this
   section and worth showing rather than explaining. */
function cjDiplomacyHtml(){
  const k = state.cj, w = k.w, v = k.d.vocab;
  const others = k.d.factions.filter(f => f.name !== k.faction);
  const rows = others.map(f => {
    const back = (f.standings || {})[k.faction];
    const backRel = (f.relationships || {})[k.faction] || '';
    const mine = w.standings[f.name];
    return `<div class="cxrow">
      <b>${esc(f.label || f.name)}</b>
      <input type="number" step="0.1" min="-1" max="1" class="cjnum"
        value="${mine === undefined ? '' : esc(mine)}"
        oninput="cjStanding('${esc(f.name)}', this.value)">
      <select onchange="cjRelation('${esc(f.name)}', this.value)">
        <option value=""${w.relationships[f.name] ? '' : ' selected'}>neutral</option>
        ${v.relations.map(r => `<option value="${r}"${
          w.relationships[f.name] === r ? ' selected' : ''}>${r}</option>`).join('')}
      </select>
      <span class="count">their side: ${back === undefined ? '-' : esc(back)}${
        backRel ? ' · ' + esc(backRel) : ''}</span>
    </div>`;
  }).join('');
  return `<div class="cxform">
    ${cjFactionPickerHtml()}
    <div class="cxlist">${rows || '<div class="count">Nobody else.</div>'}</div>
    <div class="count">The two directions are two separate lines of the file
      and nothing in the engine makes one follow from the other, so "their side"
      is shown rather than kept in step.</div>
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Save the standings</button>
      <button onclick="cjSaveRelations()">Save the relationships</button>
    </div>
  </div>`;
}

/* A whole new faction.

   The donor picker is the only required field beyond the name, and that is the
   point: nothing here is invented, everything is the donor's. What the server
   will not clone is said above the button rather than discovered afterwards. */
function cjCreateHtml(){
  const k = state.cj, m = k.w.made, v = k.d.vocab;
  return `<div class="cxform">
    <div class="csrow2">
      <div class="cmfield"><label>New faction's slot</label>
        <input value="${esc(m.name)}" placeholder="burgundy"
          oninput="cjMade('name', this.value)">
        <div class="count">The name the rest of the mod points at, not the one
          shown in game. Lower case, no spaces.${v.slots_known
          ? ' descr_sm_factions.txt has to declare it first - that is the'
            + ' Factions screen.'
          : ''}</div></div>
      <div class="cmfield"><label>Cloned from</label>
        <select onchange="cjMade('donor', this.value)">
          ${k.d.factions.map(f => `<option value="${esc(f.name)}"${
            f.name === m.donor ? ' selected' : ''}>${esc(f.label || f.name)
            }</option>`).join('')}
        </select>
        <div class="count">Its AI, its label and its purse, written in the shape
          of its own lines.</div></div>
    </div>
    <div class="csrow2">
      <div class="cmfield"><label>Goes in</label>
        <select onchange="cjMade('roster', this.value)">
          ${v.rosters.map(r => `<option value="${r}"${
            r === m.roster ? ' selected' : ''}>${r}</option>`).join('')}
        </select></div>
      <div class="cmfield"><label>Treasury</label>
        <input type="number" value="${esc(m.denari)}"
          placeholder="the donor's"
          oninput="cjMade('denari', this.value)"></div>
    </div>
    <label class="cjchk"><input type="checkbox"${m.diplomacy ? ' checked' : ''}
      onchange="cjMade('diplomacy', this.checked)">Give it the donor's diplomacy,
      both ways</label>
    <div class="count">No settlement and nobody: two factions cannot start in
      the same city, so there is nothing to clone. Give it one with the
      settlement panel and a general with the people panel, and until then it
      is the shape vanilla's Mongols and Timurids are.</div>
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Create the faction</button>
      <button onclick="cjDelete()">Delete ${esc(k.faction)}…</button>
    </div>
  </div>`;
}

//: Deleting is the same endpoint with `what: delete`, and the server refuses
//: while the faction still holds a settlement or a person - so this asks and
//: lets the refusal come back with what it holds.
function cjDelete(){
  const k = state.cj;
  cjSave({what: 'delete', faction: k.faction, donor: '', roster: '',
          diplomacy: false, scalars: null});
}

/* The win conditions.

   A list slot is edited as the text the file writes - space-separated province
   names - rather than as a picker with 200 provinces in it. The provinces this
   map has are offered as a datalist beside it, and whether a name is one of
   them is the server's to say. */
function cjWinsHtml(){
  const k = state.cj;
  if(k.winErr) return `<div class="w-warn">${esc(k.winErr)}</div>`;
  if(!k.wins) return '<div class="count">reading the win conditions…</div>';
  const w = k.ww;
  const rows = (k.wins.records || []).map(r => {
    const bad = (r.findings || []).filter(f => f.fatal).length;
    const warn = (r.findings || []).length - bad;
    return `<div class="cxrow${r.faction === k.winPick ? ' on' : ''}"
      onclick="cjWinPick('${esc(r.faction)}')">
      <b>${esc(r.faction)}</b>
      <span class="count">hold ${(r.hold || []).length} · take ${r.take || 0}${
        r.short_take ? ' · short ' + r.short_take : ''}</span>
      ${bad ? `<span class="w-bad">${bad}</span>` : ''}
      ${warn ? `<span class="w-warn">${warn}</span>` : ''}
    </div>`;
  }).join('');
  const box = (slot, label, note) => `<div class="cmfield"><label>${label}</label>
    ${slot === 'take' || slot === 'short_take'
      ? `<input type="number" min="0" value="${esc(w[slot])}"
           oninput="cjWinSet('${slot}', this.value)">`
      : `<input list="cjl-region" value="${esc(w[slot])}"
           oninput="cjWinSet('${slot}', this.value)">`}
    ${note ? `<div class="count">${note}</div>` : ''}</div>`;
  return `<div class="cxform">
    <div class="cxlist">${rows || '<div class="count">Nobody can win.</div>'}</div>
    ${(k.wins.findings || []).map(f =>
      `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`)
      .join('')}
    ${w ? `
    <div class="cshead"><b>${esc(w.faction)}</b>
      <span class="count">long campaign</span></div>
    ${box('hold', 'Provinces held', 'space-separated, as the file writes them')}
    <div class="csrow2">
      ${box('take', 'Provinces taken', '')}
      ${box('outlive', 'Outlive', 'factions, space-separated')}
    </div>
    <div class="cshead"><span class="count">short campaign</span></div>
    ${box('short_hold', 'Provinces held', '')}
    <div class="csrow2">
      ${box('short_take', 'Provinces taken', '')}
      ${box('short_outlive', 'Outlive', '')}
    </div>
    <datalist id="cjl-region">${(k.wins.vocab.regions || []).map(r =>
      `<option value="${esc(r)}">`).join('')}</datalist>
    <div class="csbtns">
      <button class="primary" onclick="cjSave()">Save ${esc(w.faction)}</button>
      <button onclick="cjSave({action: 'delete'})">Delete</button>
    </div>` : ''}
    ${cjWinAddHtml()}
  </div>`;
}

//: A faction with a block and no win condition is the one thing this panel can
//: add, and the server already knows which they are - it warns about them by
//: name in the file's own findings.
function cjWinAddHtml(){
  const k = state.cj;
  const have = new Set((k.wins.records || []).map(r => r.faction));
  const missing = (k.d.factions || []).map(f => f.name)
    .filter(n => !have.has(n));
  if(!missing.length) return '';
  return `<div class="cjplan"><div class="count">No win condition for
    ${missing.map(esc).join(', ')}.</div>
    <div class="csbtns">${missing.slice(0, 8).map(n =>
      `<button onclick="cjWinAdd('${esc(n)}')">+ ${esc(n)}</button>`).join('')}
    </div></div>`;
}

function cjWinAdd(who){
  const k = state.cj;
  k.winPick = who;
  k.ww = {faction: who, hold: '', take: '20', outlive: '',
          short_hold: '', short_take: '', short_outlive: ''};
  cjSave({action: 'add', faction: who});
}

function cjFindingsHtml(){
  const k = state.cj, p = k.preview;
  if(!p) return '';
  const rows = (p.findings || []).map(f =>
    `<div class="${f.fatal ? 'w-bad' : 'w-warn'}">${esc(f.message)}</div>`)
    .join('');
  const errs = (p.errors || []).filter(e => e !== 'nothing to change');
  return `<div class="cjplan">
    ${errs.map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${rows}
    ${(p.changes || []).length ? `<div class="count">${
      (p.changes || []).map(esc).join(' · ')}</div>` : ''}
    ${p.block ? `<pre class="cjblock">${esc(p.block)}</pre>` : ''}
  </div>`;
}
