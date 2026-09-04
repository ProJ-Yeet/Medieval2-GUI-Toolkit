/* mapcheck.js - Campaign Map: the validator, its baseline and its auto-fixes

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE VALIDATOR - Phase 16f.

   Every name here starts `cchk`, and none of them existed anywhere else in the
   tree before this phase - checked, the way 16e checked `cp`.

   THE PANEL DECIDES NOTHING. Python runs the rules, names the severity, works
   out what is in the baseline and builds the sentence; this lists what came
   back and offers two buttons per row. There is no second copy of a rule in
   the browser to drift out of step with the first, which is the same ruling the
   brush makes about pixels and the region form makes about fields.

   JUMP IS THE POINT. A finding nobody can find is a finding nobody fixes, so
   every row that knows a tile centres the map on it, picks it, and lets the
   probe say what all ten layers think - which is usually the whole diagnosis.
   A row that knows a line opens that file in Code View at it instead.

   THE BASELINE IS WHY THE SCREEN IS USABLE AT ALL. A real mod is somebody
   else's work with somebody else's bugs in it: vanilla's own map has 62
   findings and two of them are fatal. Stamping the baseline says "none of this
   is mine" - the rows stay, greyed and counted, and only what appears AFTER the
   stamp is allowed to block a save. Nothing is hidden by it, because a
   validator that hides things is one nobody believes.
   ===================================================================== */

//: The filters across the top of the list, and what each keeps.
const CCHK_VIEWS = [
  ['blocking', 'Blocking', f => f.severity === 'fatal' && !f.baseline],
  ['fatal', 'Fatal', f => f.severity === 'fatal'],
  ['warn', 'Warnings', f => f.severity === 'warn'],
  ['note', 'Notes', f => f.severity === 'note'],
  ['fixable', 'Fixable', f => !!f.fix],
  ['all', 'Everything', () => true],
];

//: How many rows are drawn before the list stops and says how many are left.
//: The server already folds a rule's own overflow into one row; this is the
//: guard on the whole list, which on a map with a broken layer can be long.
const CCHK_ROWS = 120;

const CCHK_DOT = {fatal: '●', warn: '▲', note: '○'};

/* ---------- state ---------- */

/* Kept beside `state.cmap` rather than inside it, exactly like the paint tool:
   `loadCampmap` rebuilds that object whenever the mod changes or a save reloads
   the screen, and which filter somebody is looking through is a habit rather
   than a fact about the map. `rep` is the server's own report and is never
   edited here - a row is greyed because Python said `baseline`, never because
   the browser decided it. */
function cchkNew(mod){
  return {mod, open: false, busy: false, err: '', rep: null, view: 'blocking',
          ran: 0, plan: null, planFor: ''};
}

function cchkOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cchk || state.cchk.mod !== c.mod) state.cchk = cchkNew(c.mod);
  cchkPaint();
}

function cchkToggle(){
  const k = state.cchk;
  if(!k) return;
  k.open = !k.open;
  activity('map check', k.open ? 'opened the validator' : 'closed the validator');
  if(k.open && !k.rep) cchkRun();
  else cchkPaint();
}

/* ---------- the wire ---------- */

/* Run every rule over the map as it is NOW.

   Asked again after every save and after every fix, and asked with no argument
   about what changed, because a rule reads several layers at once and working
   out which rules a stroke could have affected is a second model of the rule
   set. On vanilla the whole run is 154 ms, which is cheaper than being clever
   about it. */
async function cchkRun(){
  const k = state.cchk;
  if(!k || k.busy) return;
  k.busy = true; k.err = ''; k.plan = null;
  cchkPaint();
  try{
    k.rep = await api.get(`/api/map/check?mod=${enc(k.mod)}`, {label: 'checking the map'});
    k.ran = Date.now();
  }catch(e){ k.err = errText(e); }
  finally{ k.busy = false; }
  if(state.cchk === k) cchkPaint();
}

async function cchkPost(path, body){
  const k = state.cchk;
  k.busy = true; k.err = '';
  cchkPaint();
  let r;
  try{ r = await api.post(`/api/map/${path}`, Object.assign({mod: k.mod}, body)); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(state.cchk !== k) return null;
  k.err = r.error || '';
  if(r.report) k.rep = r.report;
  cchkPaint();
  return r;
}

async function cchkBaseline(what){
  const k = state.cchk;
  if(what === 'clear'
     && !confirm('Clear the baseline?\n\nEvery finding already in this mod goes '
                 + 'back to being one the toolkit will block a save on.')) return;
  const r = await cchkPost('baseline', {action: what});
  if(r && !r.error){
    activity('map check', what === 'clear' ? 'cleared the baseline'
             : `stamped ${r.baseline.keys} finding(s) as already in the mod`);
    toast(what === 'clear' ? 'Baseline cleared'
          : `${r.baseline.keys} finding(s) stamped as already in ${k.mod}`);
  }
}

/* ---------- the fixes ---------- */

/* Plan first, always. The plan says which files it would write and how many
   findings it would clear, and it is built by re-running the rule rather than
   from the list on the screen - so a fix cannot act on a finding that has
   stopped being true since the report was drawn. */
async function cchkPlan(code){
  const k = state.cchk;
  const r = await cchkPost('fix_plan', {fixes: [code]});
  if(!r) return;
  k.plan = r.plan && r.plan.ok ? r.plan : null;
  k.planFor = k.plan ? code : '';
  if(!k.plan && !k.err) k.err = (r.plan && r.plan.errors || []).join('; ')
    || 'nothing to fix';
  cchkPaint();
}

async function cchkApply(){
  const k = state.cchk;
  if(!k.planFor) return;
  const r = await cchkPost('fix_apply', {fixes: [k.planFor]});
  if(!r || r.error) return;
  const label = (cchkFix(k.planFor) || {}).label || k.planFor;
  k.plan = null; k.planFor = '';
  activity('map fix', `${label} - ${r.cleared} finding(s), id ${r.id}`);
  toast(`${label}: ${r.cleared} finding(s) fixed. Undo it in the Log.`, 6000);
  // The files on disk changed, so the map the screen is drawn from is stale.
  // Reloading is the whole screen, deliberately: a fixed layer is a different
  // picture, and half a screen showing the old one is worse than a blink.
  if(typeof loadCampmap === 'function') loadCampmap();
}

function cchkFix(code){
  const k = state.cchk;
  return ((k.rep && k.rep.fixes) || []).find(f => f.code === code) || null;
}

/* ---------- going to a finding ---------- */

/* Centre the map on a tile and pick it.

   Not just a pick: a finding at 172,96 on a map fitted to the screen is four
   pixels wide and nobody can see which one it is. So the view zooms in far
   enough to count tiles, puts the tile in the middle and lets cmapPick do the
   rest - the outline, the probe and the region card all follow from that. */
function cchkGo(f){
  const c = state.cmap;
  if(!c || !f.tile) return;
  const [w, h] = cmapCanvasSize();
  const v = c.view;
  v.zoom = Math.max(v.zoom, 8);
  v.ox = w / 2 - (f.tile[0] + 0.5) * v.zoom;
  v.oy = h / 2 - (f.tile[1] + 0.5) * v.zoom;
  v.fitted = true;
  cmapPick(f.tile);
  activity('map check', `went to ${f.code} at ${f.tile.join(',')}`);
}

/* A finding in a file rather than on the map.

   The same mod-relative reveal every other mode uses - it opens the folder in
   the file manager, and it cannot be handed a path from outside the mod. The
   line goes in a toast because nothing here can scroll somebody else's text
   editor to it, and saying the number is better than pretending to. */
async function cchkReveal(f){
  if(!f.file) return;
  activity('map check', `revealed ${f.file}${f.line ? ':' + f.line : ''}`);
  const r = await api.post('/api/reveal', {mod: state.cchk.mod, rel: f.file});
  toast((r && r.ok)
    ? `${f.file}${f.line ? ' - line ' + f.line : ''}`
    : ((r && r.error) || 'that folder could not be opened'), 6000);
}

/* ---------- drawing ---------- */

function cchkPaint(){
  const el = document.getElementById('cmCheck');
  if(!el) return;
  el.innerHTML = cchkHtml();
}

function cchkHtml(){
  const k = state.cchk;
  if(!k) return '';
  const rep = k.rep;
  const counts = (rep && rep.counts) || {};
  const blocking = rep ? rep.blocking : 0;
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cchkToggle()"
      title="Run every rule over the map as it is now, unsaved strokes included."
      >\u{1F50E} Check${k.open ? ' ✓' : ''}</button>
    ${rep ? `<span class="cchksum">${cchkPill('fatal', counts.fatal || 0)}
      ${cchkPill('warn', counts.warn || 0)}${cchkPill('note', counts.note || 0)}
      ${blocking ? `<b class="w-bad">${blocking} blocking</b>`
                 : `<b class="w-good">nothing blocking</b>`}</span>` : ''}
    ${k.busy ? `<span class="count">checking…</span>` : ''}
  </div>`;
  if(!k.open) return head;
  if(k.err) return head + `<div class="cchkpanel w-bad">${esc(k.err)}</div>`;
  if(!rep) return head + `<div class="cchkpanel count">running the rules…</div>`;

  const rows = rep.findings.filter(cchkFilter());
  const listed = rows.slice(0, CCHK_ROWS);
  return head + `<div class="cchkpanel">
    ${cchkViewsHtml(rep)}
    ${cchkBaseHtml(rep)}
    ${listed.length ? listed.map(cchkRowHtml).join('')
      : `<div class="count">Nothing under this filter.
         ${rep.findings.length ? `${rep.findings.length} finding(s) under the others.`
           : `Every rule ran and every one of them passed.`}</div>`}
    ${rows.length > listed.length
      ? `<div class="count">…and ${rows.length - listed.length} more.</div>` : ''}
    ${cchkFixesHtml(rep)}
    ${cchkSkipHtml(rep)}
    <div class="count">${rep.rules.length} rules · ${rep.ms} ms${
      rep.failed.length ? ` · <b class="w-bad">${rep.failed.length} rule(s) could
        not run: ${esc(rep.failed.map(f => f.code + ' (' + f.error + ')').join('; '))}
      </b>` : ''}</div>
  </div>`;
}

function cchkPill(sev, n){
  if(!n) return '';
  const cls = {fatal: 'w-bad', warn: 'w-warn', note: 'count'}[sev];
  return `<b class="${cls}">${CCHK_DOT[sev]} ${n}</b>`;
}

function cchkFilter(){
  const view = CCHK_VIEWS.find(v => v[0] === state.cchk.view);
  return view ? view[2] : (() => true);
}

function cchkViewsHtml(rep){
  const k = state.cchk;
  return `<div class="cchkviews">${CCHK_VIEWS.map(([id, label, fn]) => {
    const n = rep.findings.filter(fn).length;
    return `<button class="cpshape${k.view === id ? ' on' : ''}"
      onclick="cchkView('${id}')">${label}${n ? ` ${n}` : ''}</button>`;
  }).join('')}</div>`;
}

function cchkView(id){
  state.cchk.view = id;
  cchkPaint();
}

/* What was already wrong before this user touched anything.

   The wording matters more than the buttons do. "Stamp" has to say that it
   changes nothing about the map and only about what the toolkit will refuse,
   because the one way to make this feature dangerous is to leave somebody
   thinking it fixed something. */
function cchkBaseHtml(rep){
  const stamped = rep.baseline_keys;
  const inherited = rep.findings.filter(f => f.baseline).length;
  return `<div class="cchkbase">
    <div>${stamped
      ? `<b>${inherited}</b> of these were already in ${esc(rep.mod)} when the
         baseline was stamped on ${esc(rep.baseline_at)}. They are shown, and
         they do not block a save.`
      : `No baseline. Every fatal finding here blocks a save, including the ones
         that came with the mod.`}</div>
    <div class="cprow">
      <button class="cpshape" onclick="cchkBaseline('take')"
        title="Records what is wrong NOW as inherited. It changes nothing in the mod."
        >Stamp what is already wrong</button>
      ${stamped ? `<button class="cpshape" onclick="cchkBaseline('clear')"
        >Clear</button>` : ''}
    </div>
  </div>`;
}

function cchkRowHtml(f){
  const sev = {fatal: 'w-bad', warn: 'w-warn', note: 'count'}[f.severity] || 'count';
  const where = f.tile
    ? `<button class="cpshape" onclick="cchkGoKey('${f.key}')"
        title="Centre the map on ${f.tile.join(',')} and pick it"
        >\u{1F50D} ${f.tile[0]},${f.tile[1]}</button>`
    : f.file ? `<button class="cpshape" onclick="cchkRevealKey('${f.key}')"
        title="Open ${esc(f.file)}${f.line ? ' at line ' + f.line : ''}"
        >\u{1F4C4} ${f.line ? 'line ' + f.line : 'file'}</button>` : '';
  const fix = f.fix ? `<button class="cpshape" onclick="cchkPlan('${f.fix}')"
      title="${esc((cchkFix(f.fix) || {}).what || '')}">\u{1F527} Fix</button>` : '';
  return `<div class="cchkrow${f.baseline ? ' was' : ''}">
    <span class="${sev}">${CCHK_DOT[f.severity] || '·'}</span>
    <div>
      <div class="cchkmsg">${esc(f.message)}</div>
      <div class="count">${esc(f.code)}${f.count > 1 ? ` · ${f.count} tiles` : ''}${
        f.baseline ? ' · already in the mod' : ''}</div>
    </div>
    <div class="cchkbtn">${where}${fix}</div>
  </div>`;
}

//: The buttons take a key rather than an object, because the HTML is a string
//: and a finding is not something to serialise into an onclick attribute.
function cchkFind(key){
  const k = state.cchk;
  return ((k.rep && k.rep.findings) || []).find(f => f.key === key) || null;
}
function cchkGoKey(key){ const f = cchkFind(key); if(f) cchkGo(f); }
function cchkRevealKey(key){ const f = cchkFind(key); if(f) cchkReveal(f); }

/* The plan, and the one button that writes.

   Two steps and not one, for the same reason every other write in this toolkit
   is two: the plan says which files, how many pixels and how many lines BEFORE
   anything is backed up, and it is the only chance anybody gets to read that
   sentence. */
function cchkFixesHtml(rep){
  const k = state.cchk;
  const have = new Set(rep.findings.filter(f => f.fix).map(f => f.fix));
  if(!have.size) return '';
  const plan = k.plan;
  return `<div class="cchkfix">
    <div class="k">Auto-fixes <span class="count">Geomod's debugger actions, with
      one backup set and one Undo in the Log</span></div>
    ${rep.fixes.filter(x => have.has(x.code)).map(x => {
      const n = rep.findings.filter(f => f.fix === x.code).length;
      return `<div class="cchkfixrow">
        <button class="cpshape${k.planFor === x.code ? ' on' : ''}"
          onclick="cchkPlan('${x.code}')">${esc(x.label)} (${n})</button>
        <div class="count">${esc(x.what)}</div>
      </div>`;
    }).join('')}
    ${plan ? `<div class="cchkplan">
      <div><b>${plan.cleared}</b> finding(s) would go. Files written:</div>
      ${plan.changes.map(c => `<div class="count">${esc(c)}</div>`).join('')}
      <div class="cprow">
        <button class="cptog on" onclick="cchkApply()">Write it</button>
        <button class="cpshape" onclick="cchkCancel()">Cancel</button>
      </div>
    </div>` : ''}
  </div>`;
}

function cchkCancel(){
  const k = state.cchk;
  k.plan = null; k.planFor = '';
  cchkPaint();
}

/* What could not be checked, and which file would let it be.

   Never folded away and never phrased as a pass. The stock game keeps
   descr_climates.txt and the region name file inside a .pack, so on vanilla two
   rules cannot run at all - and "no climate is declared" read as "every climate
   colour is wrong" would report the game's own map as broken in 55,755 tiles. */
function cchkSkipHtml(rep){
  if(!rep.skipped.length) return '';
  return `<div class="cchkskip">
    <div class="k">Not checked <span class="count">a rule with nothing to check
      against reports nothing, never everything</span></div>
    ${rep.skipped.map(s => `<div class="count"><b>${esc(s.what)}</b>: ${esc(s.why)}</div>`)
      .join('')}
  </div>`;
}
