/* facaudit.js - Is this faction complete? (Phase 21, D6)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   One panel on 17f's faction screen - the question somebody standing on a
   faction asks: which of the dozen files that should name it still do not?

   Every name here starts `fau`, and there was none in the tree before.

   THE SERVER ANSWERS FOR EVERY FACTION AT ONCE. /api/factions/audit reads each
   file once and counts every slot it names (unittransfer/factionaudit.py), so
   the panel holds the whole mod's answer and the faction picker can carry a gap
   count per row without a request per row. Switching faction is a repaint.

   GAP OR NOTE IS THE SERVER'S. A gap is a file every faction in both installed
   mods has; a note is one that real, working factions go without (three of Third
   Age Reforged's have no off-map navy). The panel counts what the server
   counts and shows the rest greyed, so a working mod does not read as broken.

   THE REPAIR IS THE CLONE. "Copy from" runs Add a faction's own cloner for that
   one file with the chosen template as the donor - the same bytes a clone would
   have written there - behind the usual plan, confirmation, backup and undo.
   The two campaign rows are not copies (two factions cannot start in the same
   city), so they are buttons to the two tabs that make them.
   ===================================================================== */

//: The whole mod's audit, and what the panel remembers about itself.
function fauNew(mod, campaign){
  return {mod, campaign, d: null, loading: false, err: '', open: false,
          tpl: {}, busy: false};
}

//: The campaign the audit is about: the map's own, or the default one when
//: the panel is drawn in the Factions mode, which has no campaign.
function fauCampaign(){
  return (state.mode === 'campmap' && state.cj && state.cj.d && state.cj.d.campaign)
    || (state.mode === 'campmap' && state.cmap && state.cmap.campaign) || '';
}

//: The faction the panel is about, from whichever screen it is drawn on.
function fauSlot(){
  if(state.mode === 'campmap') return (state.cj && state.cj.faction) || '';
  return (state.fac && state.fac.sel) ? fcSlotOf(state.fac.sel) : '';
}

async function fauLoad(force){
  const mod = state.mode === 'campmap' && state.cmap ? state.cmap.mod : state.src;
  const camp = fauCampaign();
  const was = state.fau;
  if(!force && was && was.mod === mod && was.campaign === camp && (was.d || was.loading))
    return;
  const k = state.fau = fauNew(mod, camp);
  if(was && was.mod === mod){ k.open = was.open; k.tpl = was.tpl; }
  k.loading = true;
  fauPaint();
  let d;
  try{ d = await api.get(`/api/factions/audit?mod=${enc(mod)}`
                         + (camp ? `&campaign=${enc(camp)}` : '')); }
  catch(e){ d = {error: errText(e)}; }
  if(state.fau !== k) return;
  k.loading = false;
  if(d.error && !(d.factions || []).length){ k.err = d.error; fauPaint(); return; }
  k.d = d;
  fauPaint();
  // the picker's gap counts arrived with it
  if(state.mode === 'campmap' && typeof cjPaint === 'function') cjPaint();
}

//: Something wrote a faction file - the next paint reads the audit again.
function fauStale(){ if(state.fau) state.fau.d = null; }

function fauRow(slot){
  const k = state.fau;
  return k && k.d ? (k.d.factions || []).find(f => f.slot === slot) : null;
}

//: `· 2 gaps` for the faction picker; nothing while it is loading or clean.
function fauBadge(slot){
  const f = fauRow(slot);
  return f && f.gaps ? ` · ${f.gaps} gap${f.gaps === 1 ? '' : 's'}` : '';
}

function fauPaint(){
  const el = document.getElementById('fauMain');
  if(el) el.innerHTML = fauHtml();
}

//: The panel's div. The screens that host it call this and nothing else.
function fauHost(){
  const k = state.fau;
  const want = state.mode === 'campmap' && state.cmap ? state.cmap.mod : state.src;
  if(!k || k.mod !== want || k.campaign !== fauCampaign() || (!k.d && !k.loading && !k.err))
    setTimeout(() => fauLoad(), 0);
  return `<div id="fauMain" class="fau">${fauHtml()}</div>`;
}

function fauToggle(){
  const k = state.fau;
  if(!k) return;
  k.open = !k.open;
  fauPaint();
}

function fauPickTemplate(slot, tpl){
  state.fau.tpl[slot] = tpl;
  fauPaint();
}

const FAU_MARK = {ok: '<span class="w-good">✓</span>',
                  unknown: '<span class="count">?</span>'};

function fauHtml(){
  const k = state.fau, slot = fauSlot();
  if(!k || k.loading) return `<div class="fauhead count">Checking every file that
    should name this faction…</div>`;
  if(k.err) return `<div class="fauhead w-warn">${esc(k.err)}</div>`;
  if(!slot) return '';
  const f = fauRow(slot);
  if(!f) return `<div class="fauhead count">${esc(slot)} is not in the audit - it is
    in neither descr_sm_factions.txt nor this campaign.</div>`;
  const tpl = k.tpl[slot] || f.template;
  const lack = f.rows.filter(r => r.state === 'missing');
  const copyable = lack.filter(r => r.fix === 'clone' && r.level === 'gap' && fauHas(tpl, r.id));
  const head = f.gaps
    ? `<span class="w-bad">✗ ${f.gaps} gap${f.gaps === 1 ? '' : 's'}</span>`
    : `<span class="w-good">✓ Complete</span>`;
  const notes = f.notes ? ` <span class="count">· ${f.notes} note${
    f.notes === 1 ? '' : 's'}</span>` : '';
  const names = lack.filter(r => r.level === 'gap').map(r => r.label);
  return `<div class="fauhead">
      <button class="fautog" onclick="fauToggle()"
        title="Every file that should name this faction, and whether it does">${
        k.open ? '▾' : '▸'} Is it complete?</button>
      ${head}${notes}
      ${!k.open && names.length ? `<span class="count">${esc(names.join(', '))}</span>` : ''}
    </div>
    ${k.open ? `<table class="fautab">${f.rows.map(r => fauRowHtml(f, r, tpl)).join('')}</table>
    ${f.in_roster && lack.some(r => r.fix === 'clone') ? `<div class="faufix">
      <label>Copy from
        <select onchange="fauPickTemplate('${esc(slot)}', this.value)">
          ${fauTemplates(slot).map(t => `<option value="${esc(t.slot)}"${
            t.slot === tpl ? ' selected' : ''}>${esc(t.label)}${
            t.gaps ? ` · ${t.gaps} gap${t.gaps === 1 ? '' : 's'}` : ''}</option>`).join('')}
        </select></label>
      <button class="primary" ${copyable.length && !k.busy ? '' : 'disabled'}
        onclick="fauRepair('${esc(slot)}', null)"
        title="Every gap the template can fill, in one save. A note is copied from its own row"
        >Copy ${copyable.length} gap${copyable.length === 1 ? '' : 's'} from ${esc(tpl)}</button>
      <span class="count">The same records ＋ Add a faction would have written,
        copied only where this faction has none. One backup; 🕑 Log undoes it.</span>
    </div>` : ''}` : ''}`;
}

//: Whether the template has the record a row is about.
function fauHas(tpl, id){
  const t = fauRow(tpl);
  const r = t && t.rows.find(x => x.id === id);
  return !!(r && r.state === 'ok');
}

//: Every other faction in the roster, the suggested one first.
function fauTemplates(slot){
  const k = state.fau, f = fauRow(slot);
  const list = (k.d.factions || []).filter(x => x.in_roster && x.slot !== slot
                                                && x.slot !== 'slave');
  return list.sort((a, b) => (b.slot === f.template) - (a.slot === f.template)
    || a.label.localeCompare(b.label));
}

function fauRowHtml(f, r, tpl){
  const miss = r.state === 'missing';
  const mark = miss ? (r.level === 'gap' ? '<span class="w-bad">✗</span>'
                                         : '<span class="w-warn">·</span>')
                    : FAU_MARK[r.state] || '';
  let fix = '';
  if(miss && r.fix === 'clone' && f.in_roster){
    fix = fauHas(tpl, r.id)
      ? `<button onclick="fauRepair('${esc(f.slot)}', '${r.id}')"
          ${state.fau.busy ? 'disabled' : ''}>Copy from ${esc(tpl)}</button>`
      : `<span class="count">${esc(tpl)} has none either</span>`;
  }else if(miss && r.fix === 'strat' && state.mode === 'campmap' && state.cj && state.cj.d){
    fix = `<button onclick="fauGoCreate('${esc(f.slot)}')"
      title="The campaign screen's New faction tab writes a descr_strat.txt entry">New faction tab</button>`;
  }else if(miss && r.fix === 'wins' && state.mode === 'campmap' && state.cj && state.cj.d){
    fix = `<button onclick="fauGoWins('${esc(f.slot)}')">Add a record</button>`;
  }else if(miss && r.fix === 'addfaction' && typeof facCloneOpen === 'function'){
    fix = `<button onclick="fauGoAdd('${esc(f.slot)}')"
      title="Writes the slot into all twelve files at once, copied from a donor">＋ Add a faction</button>`;
  }
  return `<tr class="${miss ? (r.level === 'gap' ? 'gap' : 'note') : ''}">
    <td class="faumk">${mark}</td>
    <td><b>${esc(r.label)}</b>${r.level === 'note' ? ' <span class="count">(note)</span>' : ''}
      <div class="count">${esc(r.detail)}</div></td>
    <td class="faurel"><a class="ulink" title="${esc(r.why)} - open the file as text"
      onclick="rtOpen('${q1(esc(fauRel(r)))}')">${esc(r.rel)}</a></td>
    <td class="faubtn">${fix}</td>
  </tr>`;
}

//: The file a row is about, as a path under data/ - the two campaign rows name
//: the campaign's own copy, which is the one the game reads.
function fauRel(r){
  if(r.id !== 'campaign' && r.id !== 'wins') return r.rel;
  const camp = (state.fau && state.fau.d && state.fau.d.campaign) || 'imperial_campaign';
  return `world/maps/campaign/${camp}/${r.rel}`;
}

async function fauRepair(slot, id){
  const k = state.fau, f = fauRow(slot);
  if(!k || !f || k.busy) return;
  const tpl = k.tpl[slot] || f.template;
  const body = {mod: k.mod, campaign: k.campaign, faction: slot, template: tpl,
                checks: id ? [id] : []};
  k.busy = true; fauPaint();
  let plan;
  try{ plan = await api.post('/api/factions/repair_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  fauPaint();
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  const warn = (p.warnings || []).map(x => '⚠ ' + x);
  if(!confirm(`Copy into ${slot} from ${tpl}?\n\n`
    + ((p.changes || []).join('\n') || 'no visible change')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true; fauPaint();
  let res;
  try{ res = await api.post('/api/factions/repair_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); fauPaint(); return; }
  toast(`Copied ${(res.files || []).length} file(s) from ${tpl}. 🕑 Log can undo it.`);
  activity('faction repair', `${k.mod}: ${slot} from ${tpl}`);
  // the roster, the text keys and the counts all moved
  if(state.fac && state.fac.mod === k.mod && typeof facFetch === 'function'){
    try{ await facFetch(k.mod); }catch(e){}
  }
  await fauLoad(true);
  if(state.mode === 'factions' && typeof renderFactions === 'function') renderFactions();
}

//: The campaign screen's New faction tab, with the slot already typed in.
function fauGoCreate(slot){
  const c = state.cj;
  if(!c || !c.d) return;
  cjTab('create');
  if(c.w && c.w.made){ c.w.made.name = slot; cjPlanSoon(); cjPaint(); }
}

//: The Winning tab, adding the record - the tab's own `+ faction` button.
async function fauGoWins(slot){
  const c = state.cj;
  if(!c || !c.d) return;
  cjTab('wins');
  await cjWinReset();
  if(state.cj === c && c.wins) cjWinAdd(slot);
}

//: A slot the campaign has and the roster does not: Add a faction, named.
function fauGoAdd(slot){
  facCloneOpen();
  if(state.fac && state.fac.clone) facCloneSet('name', slot);
}
