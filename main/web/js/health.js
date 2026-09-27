/* health.js - Health: every check the toolkit has, over one mod (Phase 54, M17)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   A DOOR, NOT A SECOND COPY. The server (unittransfer/health.py) asks each
   validator for its findings and hands back one list in one shape; this page
   decides nothing about any of them. A row says what is wrong, which file,
   and opens the screen that owns it, which is where it is fixed.

   Grouped by WHEN it bites, because that is how somebody arrives: "it crashes
   loading the campaign", not "my EDB has a fatal". Fatal first inside each.

   Notes start hidden: a shipping mod carries a thousand of them (DaC's
   recruitment notes alone fold down to ninety), and a page that opens on those
   is a page nobody reads to the fatal at the top of.

   Every name here starts `hl`; there was none in the tree before.
   ===================================================================== */

const HL_SEV = {
  fatal: ['✕', 'w-bad', tt('health.fatal_the_game_crashes_or_refuses')],
  warn: ['!', 'w-warn', tt('health.warning_it_loads_but_something_will')],
  note: ['·', '', tt('health.note_worth_a_look_not_a')],
};
const HL_PAGE = 150;

function hlNew(mod){
  return {mod, rep: null, err: '', busy: false, notes: false, base: false,
          src: '', shown: {}};
}

const hlBusyHtml = mod => `<div class="empty">${tt('health.running_every_check_over_a_few',{mod:esc(mod)})}</div>`;

function renderHealth(){
  const h = state.hl;
  if(!h || h.mod !== state.src){ loadHealth(); return; }
  hlPaint();
}

async function loadHealth(){
  const mod = state.src;
  const keep = state.hl && state.hl.mod === mod ? state.hl : null;
  const h = state.hl = hlNew(mod);
  if(keep){ h.notes = keep.notes; h.base = keep.base; h.src = keep.src; }
  h.busy = true;
  main.innerHTML = hlBusyHtml(mod);
  let r;
  // the map rules only where the build offers the map screen (2.x ships it off)
  try{ r = await api.get('/api/health?mod=' + enc(mod) + (modeOffered('campmap') ? '&map=1' : '')); }
  catch(e){ r = {error: errText(e)}; }
  if(stale('health', mod) || state.hl !== h) return;
  h.busy = false;
  if(r.error) h.err = r.error; else h.rep = r;
  hlPaint();
}

function hlVisible(f){
  const h = state.hl;
  if(f.severity === 'note' && !h.notes) return false;
  if(f.baseline && h.base) return false;
  if(h.src && f.source !== h.src) return false;
  return true;
}

function hlPaint(){
  const h = state.hl;
  /* The report may not be here yet, and something else may well repaint this
     screen while it is still on its way: the mod list finishing its own load
     repaints whatever mode is showing, and a tab opened straight on
     `?go=health` gets exactly that repaint in the gap between the request
     going out and coming back. Say what is happening rather than read a report
     that is null - which is what this screen did until a link could land on it
     before it had one. */
  if(!h.rep && !h.err){ main.innerHTML = hlBusyHtml(h.mod); return; }
  if(h.err){
    main.innerHTML = `<div class="empty">${tt('health.couldnt_run_the_checks')}<br>
      <span class="count">${esc(h.err)}</span><br><br>
      <button class="primary" onclick="loadHealth()">${tt('common.retry')}</button></div>`;
    return;
  }
  const r = h.rep, rows = r.findings.filter(hlVisible);
  const labelOf = Object.fromEntries(r.sources.map(s => [s.id, s.label]));
  main.innerHTML = `<div class="hlwrap">
    ${hlHeadHtml(r)}
    ${hlSourcesHtml(r)}
    ${r.when.map(w => hlGroupHtml(w, rows.filter(f => f.when === w.id), labelOf)).join('')}
    ${rows.length ? '' : `<div class="bsec"><div class="trnote">${r.findings.length
      ? tt('health.nothing_matches_what_is_shown_tick')
      : tt('health.every_check_came_back_clean')}</div></div>`}
    ${hlSlowHtml(r)}
    ${hlRefusedHtml(r)}
  </div>`;
}

function hlHeadHtml(r){
  const h = state.hl, c = r.counts;
  const base = r.findings.filter(f => f.baseline).length;
  return `<div class="bsec"><h4>${tt('health.health_of_checks_ran_in_s',{mod:esc(r.mod),n:r.sources.filter(s => s.state === 'ok').length,ms:(r.ms / 1000).toFixed(1)})}
      <button style="margin-left:auto" onclick="loadHealth()">${tt('health.run_again')}</button></h4>
    <div class="trnote">${tt('health.every_check_the_toolkit_has_over')}</div>
    <div class="hlcounts">
      ${tt('health.fatal_warning',{fatal:c.fatal,warn:c.warn,warn2:c.warn === 1 ? '' : 's'})}
      <label class="chk"><input type="checkbox" ${h.notes ? 'checked' : ''}
        onchange="state.hl.notes=this.checked;hlPaint()"> ${tt('health.note',{note:c.note,note2:c.note === 1 ? '' : 's'})}</label>
      ${base ? `<label class="chk" title="${ttA('health.the_campaign_map_screen_can_stamp',{base})}"><input type="checkbox"
        ${h.base ? 'checked' : ''} onchange="state.hl.base=this.checked;hlPaint()">
        ${tt('health.hide_that_were_already_there',{base})}</label>` : ''}
    </div></div>`;
}

function hlSourcesHtml(r){
  const h = state.hl;
  return `<div class="hlsrcs">${r.sources.map(s => {
    const n = s.counts.fatal + s.counts.warn + (h.notes ? s.counts.note : 0);
    const cls = s.state === 'failed' ? ' failed' : s.state === 'off' ? ' off' : '';
    const tip = s.state === 'failed' ? tt('health.this_check_could_not_run',{error:s.error})
      : s.state === 'off' ? tt('health.the_campaign_map_screen_is_off')
      : tt('health.ms',{file:s.file,ms:s.ms});
    return `<button class="hlsrc${cls}${h.src === s.id ? ' on' : ''}" title="${esc(tip)}"
      ${s.state === 'ok' ? tt('health.onclick_hlsource',{id:s.id}) : 'disabled'}>
      ${esc(s.label)}
      <span class="n">${s.state === 'failed' ? 'failed' : s.state === 'off' ? 'off'
        : s.counts.fatal ? `<b class="w-bad">${s.counts.fatal}</b>${n > s.counts.fatal ? ' +' + (n - s.counts.fatal) : ''}`
        : n}</span></button>`;
  }).join('')}${r.sources.filter(s => s.state === 'failed').map(s =>
    `<div class="hlfail w-bad">${tt('health.could_not_run',{label:esc(s.label),error:esc(s.error)})}</div>`).join('')}</div>`;
}

function hlSource(id){
  const h = state.hl;
  h.src = h.src === id ? '' : id;
  hlPaint();
}

function hlGroupHtml(w, rows, labelOf){
  if(!rows.length) return '';
  const h = state.hl, lim = h.shown[w.id] || HL_PAGE;
  const fatal = rows.filter(f => f.severity === 'fatal').length;
  return `<div class="bsec hlgroup"><h4>${esc(w.label)} <span class="n">${rows.length}</span>
      ${fatal ? `<span class="w-bad">${tt('health.fatal',{fatal})}</span>` : ''}
      <span class="count">${esc(w.help)}</span></h4>
    <div class="hllist">${rows.slice(0, lim).map(f => hlRowHtml(f, labelOf)).join('')}</div>
    ${rows.length > lim ? `<button class="mini" style="margin-top:6px"
      onclick="state.hl.shown['${w.id}']=${lim + HL_PAGE};hlPaint()">${tt('health.show_more_of',{x:Math.min(HL_PAGE, rows.length - lim),x2:rows.length - lim})}</button>` : ''}</div>`;
}

function hlRowHtml(f, labelOf){
  const [icon, cls, tip] = HL_SEV[f.severity] || HL_SEV.note;
  const at = f.file ? `${f.file}${f.line ? ':' + f.line : ''}` : '';
  const i = state.hl.rep.findings.indexOf(f);
  return `<div class="hlrow${f.baseline ? ' base' : ''}">
    <span class="hlsev ${cls}" title="${esc(tip)}">${icon}</span>
    <div class="hlmsg">${esc(f.message)}${f.count > 1 ? ` <span class="count">(×${f.count})</span>` : ''}
      <div class="count">${esc(labelOf[f.source] || f.source)}${at ? ` · <code>${esc(at)}</code>` : ''}${
        f.baseline ? tt('health.already_there_when_the_map_was') : ''}</div></div>
    <a class="mini" href="${esc(navUrl(f.open || {}))}" onclick="return hlOpen(${i}, event)"
      title="${ttA('health.open_this_where_it_is_fixed')}"
      >${tt('health.open')}</a>
  </div>`;
}

function hlSlowHtml(r){
  return `<div class="bsec"><h4>${tt('health.cleanup_audits_not_run_here')}</h4>
    <div class="trnote">${tt('health.these_look_for_what_a_mod')}</div>
    <div class="hlslow">${r.slow.map(s => `<div class="hlslowrow">
      <div>${esc(s.label)} <span class="count">${esc(s.cost)}</span></div>
      ${navLinkHtml({mode: s.mode}, tt('health.open'), 'mini',
        tt('health.open_this_audit_middle_click_to'))}</div>`).join('')}</div></div>`;
}

// What the crash guides claim that measuring the installed mods refused. Folded,
// because it is an answer to look up rather than something to act on.
function hlRefusedHtml(r){
  if(!(r.refused || []).length) return '';
  return `<div class="bsec ${foldCls('hl.refused')}" data-fold="hl.refused"><h4>${tt('health.what_the_guides_say_that_is')} <span class="n">${r.refused.length}</span></h4>
    <div class="trnote">${tt('health.claims_from_the_two_crash_guides')}</div>
    <div class="hlslow">${r.refused.map(x => `<div class="hlslowrow" style="display:block">
      <div>${esc(x.claim)}</div>
      <div class="count">${tt('health.measured',{source:esc(x.source),measured:esc(x.measured)})}</div></div>`).join('')}</div></div>`;
}

/* ---- going to the screen that owns a finding ----
   A finding's `open` is a ROUTE, and the walk from one to a screen with the
   record picked is `navGo` in core.js. It was written here first, because a
   Health row was the first thing in the tool that had to name a place it was
   not at; it moved out when the crumb bar and `?go=` needed the same walk, and
   what is left here is the one part of it that is Health's: the log line.

   The row's Open is an ANCHOR now rather than a button, and that alone is what
   makes a middle click open the finding in a new tab - the browser does it off
   the href without a line of JavaScript. So only the plain left button is taken
   here; ctrl-click, shift-click and the context menu are left alone on purpose. */
function hlOpen(i, ev){
  if(ev && (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey)) return true;
  if(ev) ev.preventDefault();
  const f = state.hl.rep.findings[i];
  if(!f) return false;
  activity('health', `opened ${f.source} ${f.code}`);
  navGo(f.open || {});
  return false;
}
