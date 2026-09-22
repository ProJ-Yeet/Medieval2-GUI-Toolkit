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
  fatal: ['✕', 'w-bad', 'Fatal: the game crashes or refuses the file'],
  warn: ['!', 'w-warn', 'Warning: it loads, but something will not work as meant'],
  note: ['·', '', 'Note: worth a look, not a fault'],
};
const HL_PAGE = 150;

function hlNew(mod){
  return {mod, rep: null, err: '', busy: false, notes: false, base: false,
          src: '', shown: {}};
}

const hlBusyHtml = mod => `<div class="empty">Running every check over ${esc(mod)}…<br>
  <span class="count">A few seconds: the map rules are the slow part.</span></div>`;

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
    main.innerHTML = `<div class="empty">Couldn't run the checks.<br>
      <span class="count">${esc(h.err)}</span><br><br>
      <button class="primary" onclick="loadHealth()">Retry</button></div>`;
    return;
  }
  const r = h.rep, rows = r.findings.filter(hlVisible);
  const labelOf = Object.fromEntries(r.sources.map(s => [s.id, s.label]));
  main.innerHTML = `<div class="hlwrap">
    ${hlHeadHtml(r)}
    ${hlSourcesHtml(r)}
    ${r.when.map(w => hlGroupHtml(w, rows.filter(f => f.when === w.id), labelOf)).join('')}
    ${rows.length ? '' : `<div class="bsec"><div class="trnote">${r.findings.length
      ? 'Nothing matches what is shown. Tick <b>Notes</b> or clear the source above to see the rest.'
      : 'Every check came back clean.'}</div></div>`}
    ${hlSlowHtml(r)}
    ${hlRefusedHtml(r)}
  </div>`;
}

function hlHeadHtml(r){
  const h = state.hl, c = r.counts;
  const base = r.findings.filter(f => f.baseline).length;
  return `<div class="bsec"><h4>Health of ${esc(r.mod)}
      <span class="count">${r.sources.filter(s => s.state === 'ok').length} checks ran in
        ${(r.ms / 1000).toFixed(1)}s</span>
      <button style="margin-left:auto" onclick="loadHealth()">↻ Run again</button></h4>
    <div class="trnote">Every check the toolkit has, over this mod, in one list. Each row opens the
      screen that owns it, which is where it is fixed. Grouped by when it bites, the way the two
      crash guides in the archive put it.</div>
    <div class="hlcounts">
      <span class="hlc w-bad">✕ ${c.fatal} fatal</span>
      <span class="hlc w-warn">! ${c.warn} warning${c.warn === 1 ? '' : 's'}</span>
      <label class="chk"><input type="checkbox" ${h.notes ? 'checked' : ''}
        onchange="state.hl.notes=this.checked;hlPaint()"> ${c.note} note${c.note === 1 ? '' : 's'}</label>
      ${base ? `<label class="chk" title="The campaign map screen can stamp what a mod already had, so
only what you add afterwards counts. These ${base} were there when it was stamped."><input type="checkbox"
        ${h.base ? 'checked' : ''} onchange="state.hl.base=this.checked;hlPaint()">
        Hide ${base} that were already there</label>` : ''}
    </div></div>`;
}

function hlSourcesHtml(r){
  const h = state.hl;
  return `<div class="hlsrcs">${r.sources.map(s => {
    const n = s.counts.fatal + s.counts.warn + (h.notes ? s.counts.note : 0);
    const cls = s.state === 'failed' ? ' failed' : s.state === 'off' ? ' off' : '';
    const tip = s.state === 'failed' ? `This check could not run: ${s.error}`
      : s.state === 'off' ? 'The campaign map screen is off in this build, so its rules are not run.'
      : `${s.file} · ${s.ms} ms`;
    return `<button class="hlsrc${cls}${h.src === s.id ? ' on' : ''}" title="${esc(tip)}"
      ${s.state === 'ok' ? `onclick="hlSource('${s.id}')"` : 'disabled'}>
      ${esc(s.label)}
      <span class="n">${s.state === 'failed' ? 'failed' : s.state === 'off' ? 'off'
        : s.counts.fatal ? `<b class="w-bad">${s.counts.fatal}</b>${n > s.counts.fatal ? ' +' + (n - s.counts.fatal) : ''}`
        : n}</span></button>`;
  }).join('')}${r.sources.filter(s => s.state === 'failed').map(s =>
    `<div class="hlfail w-bad">✕ ${esc(s.label)} could not run: ${esc(s.error)}</div>`).join('')}</div>`;
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
      ${fatal ? `<span class="w-bad">${fatal} fatal</span>` : ''}
      <span class="count">${esc(w.help)}</span></h4>
    <div class="hllist">${rows.slice(0, lim).map(f => hlRowHtml(f, labelOf)).join('')}</div>
    ${rows.length > lim ? `<button class="mini" style="margin-top:6px"
      onclick="state.hl.shown['${w.id}']=${lim + HL_PAGE};hlPaint()">Show ${Math.min(HL_PAGE, rows.length - lim)}
      more of ${rows.length - lim}</button>` : ''}</div>`;
}

function hlRowHtml(f, labelOf){
  const [icon, cls, tip] = HL_SEV[f.severity] || HL_SEV.note;
  const at = f.file ? `${f.file}${f.line ? ':' + f.line : ''}` : '';
  const i = state.hl.rep.findings.indexOf(f);
  return `<div class="hlrow${f.baseline ? ' base' : ''}">
    <span class="hlsev ${cls}" title="${esc(tip)}">${icon}</span>
    <div class="hlmsg">${esc(f.message)}${f.count > 1 ? ` <span class="count">(×${f.count})</span>` : ''}
      <div class="count">${esc(labelOf[f.source] || f.source)}${at ? ` · <code>${esc(at)}</code>` : ''}${
        f.baseline ? ' · already there when the map was stamped' : ''}</div></div>
    <a class="mini" href="${esc(navUrl(f.open || {}))}" onclick="return hlOpen(${i}, event)"
      title="Open this where it is fixed. Middle-click to open it in a new tab and keep this list."
      >Open →</a>
  </div>`;
}

function hlSlowHtml(r){
  return `<div class="bsec"><h4>Cleanup audits <span class="count">not run here</span></h4>
    <div class="trnote">These look for what a mod carries and never uses: unused models, orphan
      files, duplicate cards. None of it stops a mod starting, and each takes from seconds to over a
      minute on a big mod, so each runs on its own screen when you ask.</div>
    <div class="hlslow">${r.slow.map(s => `<div class="hlslowrow">
      <div>${esc(s.label)} <span class="count">${esc(s.cost)}</span></div>
      ${navLinkHtml({mode: s.mode}, 'Open →', 'mini',
        'Open this audit. Middle-click to open it in a new tab.')}</div>`).join('')}</div></div>`;
}

// What the crash guides claim that measuring the installed mods refused. Folded,
// because it is an answer to look up rather than something to act on.
function hlRefusedHtml(r){
  if(!(r.refused || []).length) return '';
  return `<div class="bsec ${foldCls('hl.refused')}" data-fold="hl.refused"><h4>What the guides say
      that is not checked <span class="n">${r.refused.length}</span></h4>
    <div class="trnote">Claims from the two crash guides that the mods themselves disprove. Each is
      measured, and kept here so it is not rediscovered.</div>
    <div class="hlslow">${r.refused.map(x => `<div class="hlslowrow" style="display:block">
      <div>${esc(x.claim)}</div>
      <div class="count">${esc(x.source)} · measured: ${esc(x.measured)}</div></div>`).join('')}</div></div>`;
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
