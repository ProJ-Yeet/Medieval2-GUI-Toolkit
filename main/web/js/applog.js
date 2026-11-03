/* =========================================================================
   What the page did, for a problem report (the tester's notes on Armory
   Studio: "a detailed log system, a button to send it directly to you, with
   a box to write notes in").

   Every request to the server (its address, how long it took, how it ended),
   every message shown, every error the page met and every screen opened, the
   last APP_LOG_MAX of them, kept in the page only. Report a problem puts it
   in a zip with the notes, the Armory model and the server's log
   (report.py), saved in config/reports/ and sent where an address is set.
   ========================================================================= */

const APP_LOG_MAX = 1500;
const APP_LOG = [];
function appLog(kind, what, extra){
  const row = {t: new Date().toISOString().slice(11, 23), kind, what: String(what).slice(0, 600)};
  if(extra) row.x = extra;
  APP_LOG.push(row);
  if(APP_LOG.length > APP_LOG_MAX) APP_LOG.splice(0, APP_LOG.length - APP_LOG_MAX);
}

/* The requests, by wrapping api's two calls; a body is noted by its size,
   never kept (a model or a mod's text would crowd everything else out). */
(function(){
  const wrap = (name) => {
    const real = api[name];
    api[name] = async function(u, b, o){
      const t0 = performance.now();
      const size = name === 'post' && b ? (() => { try{ return JSON.stringify(b).length; }catch(e){ return -1; } })() : undefined;
      try{
        const out = await real.apply(this, arguments);
        appLog(name, u, {ms: Math.round(performance.now() - t0), size, error: out && out.error ? String(out.error).slice(0, 300) : undefined,
          detail: out && out.detail ? String(out.detail).slice(0, 300) : undefined});
        return out;
      }catch(e){
        appLog(name, u, {ms: Math.round(performance.now() - t0), size, failed: String(e && e.message || e).slice(0, 300)});
        throw e;
      }
    };
  };
  wrap('get'); wrap('post');
  const realToast = toast;
  toast = function(m, ms){ appLog('toast', m); return realToast.apply(this, arguments); };
  window.addEventListener('error', e => { if(e.message){ appLog('error', e.message, {at: `${(e.filename || '').split('/').pop()}:${e.lineno}`}); uiBugBar(e.message); } });
  window.addEventListener('unhandledrejection', e => {
    appLog('error', (e.reason && (e.reason.stack || e.reason.message)) || e.reason);
    // a request that failed has its own message where it was asked; a page
    // being left mid-request is not a fault
    const r = e.reason;
    if(r && (r.apiFailure || r === (typeof ABORTED !== 'undefined' ? ABORTED : null))) return;
    uiBugBar((r && r.message) || String(r));
  });
})();

/* A fault in the page's own code used to show nothing: a button did nothing,
   a panel stayed half drawn, and only the diagnostic log knew. Now one bar
   says so, offers to draw the screen again and to report it (with this log),
   and keeps quiet for a while after, so one fault is one bar. */
let uiBugAt = 0;
function uiBugBar(msg){
  const now = Date.now();
  if(now - uiBugAt < 20000) return;
  uiBugAt = now;
  let bar = document.getElementById('uibug');
  if(!bar){ bar = document.createElement('div'); bar.id = 'uibug'; bar.className = 'uibug'; document.body.appendChild(bar); }
  bar.innerHTML = `<span style="flex:1"><b>${tt('report.bug_head')}</b> ${tt('report.bug_body')}
      <details><summary class="count">${tt('report.bug_details')}</summary><code class="count">${esc(String(msg || '').slice(0, 300))}</code></details></span>
    <button onclick="uiBugRedraw()">${tt('report.bug_redraw')}</button>
    <button onclick="document.getElementById('uibug').classList.remove('on');reportOpen(state.mode)">${tt('report.bug_report')}</button>
    <button class="toastx" title="${ttA('common.close')}" onclick="document.getElementById('uibug').classList.remove('on')">✕</button>`;
  bar.classList.add('on');
}
function uiBugRedraw(){
  const bar = document.getElementById('uibug'); if(bar) bar.classList.remove('on');
  try{ if(typeof render === 'function') render(); }catch(e){ location.reload(); }
}

/* --- the dialog -------------------------------------------------------------- */

async function reportOpen(where){
  let info = {};
  try{ info = await api.get('/api/report', 1); }catch(e){ /* the dialog still saves */ }
  document.getElementById('modal').className = 'modal';
  overlay.classList.add('open');
  const armOn = !!(state.armProj && (state.armProj.objects || []).length);
  modal.innerHTML = `<div class="armimp">
    <h3>${tt('report.title')}</h3>
    <div class="count" style="margin-bottom:8px">${tt('report.intro')}</div>
    <textarea id="reportNotes" rows="7" style="width:100%" placeholder="${esc(tt('report.notes_placeholder'))}"></textarea>
    <label class="armcheck"><input type="checkbox" id="reportModel"${armOn ? ' checked' : ''}${armOn ? '' : ' disabled'}> ${tt('report.with_model')}</label>
    <div class="count">${ttN('report.log_rows', APP_LOG.length)}</div>
    <div class="armimpfoot"><span class="count" style="flex:1">${info.can_send ? '' : esc(tt('report.save_only', {folder: info.folder || 'config/reports'}))}</span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="reportGo('${esc(q1(where || ''))}', false)">${tt('report.save')}</button>
      ${info.can_send ? `<button class="primary" onclick="reportGo('${esc(q1(where || ''))}', true)">${tt('report.send')}</button>` : ''}</div>
  </div>`;
  document.getElementById('reportNotes').focus();
}
async function reportGo(where, send){
  const notes = (document.getElementById('reportNotes') || {}).value || '';
  const withModel = (document.getElementById('reportModel') || {}).checked;
  modal.querySelectorAll('button').forEach(b => b.disabled = true);
  let r;
  try{
    r = await api.post('/api/report', {notes, log: APP_LOG, where: where || state.mode || '', send,
                                       project: withModel ? state.armProj : null});
  }catch(e){ toast(errText(e), 6000); modal.querySelectorAll('button').forEach(b => b.disabled = false); return; }
  closeModal();
  if(r.sent) toast(tt('report.sent'), 5000);
  else if(r.error) toast(tt('report.not_sent', {why: r.error, path: r.path}), 9000);
  else toast(tt('report.saved', {path: r.path}), 7000);
}
