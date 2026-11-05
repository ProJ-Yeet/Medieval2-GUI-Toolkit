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
/* Two tabs, as the Pfadfinder (Oogway) editor has them: Send (a bug or an
   idea, a contact kept if wished, words to hide, screenshots added or pasted,
   Show what is sent, Save, Send) and Answers to my reports (the author's
   answers by report number, and a reply on the same report). report.py
   scrubs every text before it is shown, saved or sent. */

const REPORT = {pics: [], tab: 'send', info: {}, answers: null, pick: '', newCount: 0};
const reportMods = () => [...new Set([state.src, state.dst, state.mod].filter(Boolean))];

async function reportOpen(where, notes){
  try{ REPORT.info = await api.get('/api/report', 1); }catch(e){ REPORT.info = {}; }
  REPORT.where = where || state.mode || '';
  REPORT.pics = [];
  REPORT.tab = 'send';
  document.getElementById('modal').className = 'modal';
  overlay.classList.add('open');
  reportPaint(notes || '');
}
function reportPaint(notes){
  const info = REPORT.info, armOn = !!(state.armProj && (state.armProj.objects || []).length);
  const tabs = info.relay ? `<div class="tabs" style="margin-bottom:8px">
      <button class="${REPORT.tab === 'send' ? 'on' : ''}" onclick="reportTab('send')">${tt('report.tab_send')}</button>
      <button class="${REPORT.tab === 'answers' ? 'on' : ''}" onclick="reportTab('answers')">${tt('report.tab_answers')}${REPORT.newCount ? ` (${tt('report.new_n', {n: REPORT.newCount})})` : ''}</button></div>` : '';
  if(REPORT.tab === 'answers') return reportAnswersPaint(tabs);
  modal.innerHTML = `<div class="armimp" onpaste="reportPaste(event)">
    <h3>${tt('report.title')}</h3>${tabs}
    <div class="count" style="margin-bottom:8px">${tt('report.intro')}</div>
    <div style="margin-bottom:6px"><label class="armcheck"><input type="radio" name="reportKind" value="bug" checked onchange="reportKindChanged()"> ${tt('report.kind_bug')}</label>
      <label class="armcheck"><input type="radio" name="reportKind" value="idea" onchange="reportKindChanged()"> ${tt('report.kind_idea')}</label></div>
    <textarea id="reportNotes" rows="7" style="width:100%" placeholder="${esc(tt('report.notes_placeholder'))}">${esc(notes || '')}</textarea>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0">
      <input id="reportContact" style="flex:1;min-width:180px" placeholder="${esc(tt('report.contact_placeholder'))}" value="${esc(info.contact || '')}">
      <label class="armcheck"><input type="checkbox" id="reportRemember" checked> ${tt('report.remember')}</label></div>
    <input id="reportHide" style="width:100%;margin-bottom:6px" placeholder="${esc(tt('report.hide_placeholder'))}" value="${esc(info.hide || '')}">
    <label class="armcheck"><input type="checkbox" id="reportLogs" checked> ${tt('report.with_logs')}</label>
    <label class="armcheck"><input type="checkbox" id="reportModel"${armOn ? ' checked' : ''}${armOn ? '' : ' disabled'}> ${tt('report.with_model')}</label>
    <div style="margin:6px 0"><button class="mini" onclick="reportAddPics()">${tt('report.add_screenshot')}</button>
      <span class="count">${tt('report.paste_hint')}</span><div id="reportPics" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"></div></div>
    <div class="count">${ttN('report.log_rows', APP_LOG.length)}</div>
    <div id="reportShow" style="display:none;max-height:260px;overflow:auto;margin-top:6px"></div>
    <div class="armimpfoot"><span class="count" style="flex:1">${info.can_send ? '' : esc(tt('report.save_only', {folder: info.folder || 'config/reports'}))}</span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button onclick="reportShowWhat()">${tt('report.show')}</button>
      <button onclick="reportGo(false)">${tt('report.save')}</button>
      ${info.can_send ? `<button class="primary" onclick="reportGo(true)">${tt('report.send')}</button>` : ''}</div>
  </div>`;
  reportPicsPaint();
  document.getElementById('reportNotes').focus();
}
function reportKindChanged(){
  const idea = (document.querySelector('input[name=reportKind]:checked') || {}).value === 'idea';
  const logs = document.getElementById('reportLogs');
  if(logs) logs.checked = !idea;            // an idea needs no logs
}
function reportTab(tab){ REPORT.tab = tab; reportPaint(''); if(tab === 'answers') reportCheck(); }

/* screenshots: picked from disk, or pasted with Ctrl+V anywhere in the dialog */
function reportAddPics(){
  const inp = document.createElement('input');
  inp.type = 'file'; inp.accept = 'image/png,image/jpeg,image/webp'; inp.multiple = true;
  inp.onchange = () => [...inp.files].forEach(reportReadPic);
  inp.click();
}
function reportPaste(e){
  const items = [...((e.clipboardData || {}).items || [])].filter(it => it.type.startsWith('image/'));
  if(!items.length) return;
  e.preventDefault();
  items.forEach(it => reportReadPic(it.getAsFile()));
}
function reportReadPic(file){
  if(!file) return;
  const r = new FileReader();
  r.onload = () => { REPORT.pics.push(r.result); reportPicsPaint(); };
  r.readAsDataURL(file);
}
function reportPicsPaint(){
  const box = document.getElementById('reportPics'); if(!box) return;
  box.innerHTML = REPORT.pics.map((u, i) => `<span style="position:relative"><img src="${u}" style="height:64px;border:1px solid var(--line)">
    <button class="mini" style="position:absolute;top:0;right:0" title="${esc(tt('report.remove_screenshot'))}" onclick="REPORT.pics.splice(${i},1);reportPicsPaint()">✕</button></span>`).join('');
}

function reportBody(extra){
  const v = id => (document.getElementById(id) || {}).value || '';
  const c = id => !!(document.getElementById(id) || {}).checked;
  return Object.assign({notes: v('reportNotes'), log: APP_LOG, where: REPORT.where,
    kind: (document.querySelector('input[name=reportKind]:checked') || {}).value || 'bug',
    contact: v('reportContact'), hide: v('reportHide'), remember: c('reportRemember'),
    logs: c('reportLogs'), pictures: REPORT.pics, mods: reportMods(),
    project: c('reportModel') ? state.armProj : null}, extra || {});
}
async function reportShowWhat(){
  const box = document.getElementById('reportShow');
  let r;
  try{ r = await api.post('/api/report', reportBody({preview: true})); }catch(e){ toast(errText(e), 6000); return; }
  box.style.display = '';
  box.innerHTML = `<div class="count">${tt('report.zip_size', {kb: Math.round(r.bytes / 1024)})}</div>` + r.files.map(f =>
    `<details><summary>${esc(f.name)} <span class="count">${tt('report.file_kb', {kb: Math.round(f.bytes / 1024)})}</span></summary>${f.text != null ? `<pre style="white-space:pre-wrap;max-height:200px;overflow:auto">${esc(f.text.slice(0, 20000))}${f.text.length > 20000 ? '\n…' : ''}</pre>` : ''}</details>`).join('');
}
async function reportGo(send){
  const body = reportBody({send});
  modal.querySelectorAll('button').forEach(b => b.disabled = true);
  let r;
  try{
    r = await api.post('/api/report', body);
  }catch(e){ toast(errText(e), 6000); modal.querySelectorAll('button').forEach(b => b.disabled = false); return; }
  closeModal();
  if(r.sent) toast(r.id ? tt('report.sent_number', {id: r.id}) : tt('report.sent'), 8000);
  else if(r.error) toast(tt('report.not_sent', {why: r.error, path: r.path}), 9000);
  else toast(tt('report.saved', {path: r.path}), 7000);
}

/* --- answers to my reports ----------------------------------------------------- */

async function reportCheck(quiet){
  let r;
  try{ r = await api.get('/api/report/answers', 1); }catch(e){ if(!quiet) toast(errText(e), 6000); return; }
  REPORT.answers = r.reports || [];
  REPORT.newCount = REPORT.answers.reduce((n, a) => n + (a.new || 0), 0);
  reportBadge();
  if(!quiet && r.error) toast(r.error, 6000);
  if(document.getElementById('reportAnswers')) reportPaint('');
}
function reportBadge(){
  const b = document.getElementById('reportBtn'); if(!b) return;
  b.textContent = REPORT.newCount ? tt('app.report_new', {n: REPORT.newCount}) : tt('app.report');
}
function reportAnswersPaint(tabs){
  const list = REPORT.answers;
  const pick = list && (list.find(a => a.id === REPORT.pick) || list[list.length - 1]);
  if(pick) REPORT.pick = pick.id;
  const stateOf = a => !a.state ? tt('report.state_waiting') : a.state === 'open' ? tt('report.state_open')
    : a.reason === 'not_planned' ? tt('report.state_not_planned') : tt('report.state_fixed');
  modal.innerHTML = `<div class="armimp" id="reportAnswers">
    <h3>${tt('report.title')}</h3>${tabs}
    ${list == null ? `<div class="count">${tt('report.checking')}</div>` : !list.length ? `<div class="count">${tt('report.none_sent')}</div>` : `
    <div style="display:flex;gap:10px;min-height:260px">
      <div style="width:38%;overflow:auto;max-height:420px">${list.slice().reverse().map(a => `
        <div class="proglist-row${a.id === REPORT.pick ? ' w-good' : ''}" style="cursor:pointer" onclick="REPORT.pick='${esc(q1(a.id))}';reportPaint('')">
          <b>${esc(a.id)}</b>${a.new ? ` <span class="w-warn">(${tt('report.new_n', {n: a.new})})</span>` : ''}<br>
          <span class="count">${esc(a.kind === 'idea' ? tt('report.kind_idea') : tt('report.kind_bug'))} · ${esc(stateOf(a))} · ${esc(a.when || '')}</span><br>${esc(a.title || '')}</div>`).join('')}</div>
      <div style="flex:1;display:flex;flex-direction:column;gap:6px">
        <div style="flex:1;overflow:auto;max-height:300px">${(pick.messages || []).length ? pick.messages.map(m => `
          <div style="margin-bottom:8px"><b>${m.from === 'author' ? tt('report.from_author') : tt('report.from_you')}</b> <span class="count">${esc((m.at || '').slice(0, 16).replace('T', ' '))}</span>
            <div style="white-space:pre-wrap">${esc(m.text)}</div></div>`).join('') : `<div class="count">${tt('report.no_answer_yet')}</div>`}</div>
        <textarea id="reportReply" rows="4" placeholder="${esc(tt('report.reply_placeholder'))}"></textarea>
        <label class="armcheck"><input type="checkbox" id="reportReplyLogs"> ${tt('report.reply_with_logs')}</label>
        <div><button class="primary" onclick="reportReplyGo()">${tt('report.reply_send')}</button></div>
      </div></div>`}
    <div class="armimpfoot"><span class="count" style="flex:1"></span>
      <button onclick="reportCheck()">${tt('report.check_now')}</button>
      <button onclick="closeModal()">${tt('common.close')}</button></div>
  </div>`;
  if(pick && pick.new){
    api.post('/api/report/seen', {id: pick.id}).catch(() => {});
    REPORT.newCount -= pick.new; pick.new = 0; reportBadge();
  }
}
async function reportReplyGo(){
  const message = (document.getElementById('reportReply') || {}).value || '';
  if(!message.trim()) return;
  const logs = !!(document.getElementById('reportReplyLogs') || {}).checked;
  let r;
  try{
    r = await api.post('/api/report/reply', {id: REPORT.pick, message, logs, log: logs ? APP_LOG : [],
                                             mods: reportMods(), where: REPORT.where});
  }catch(e){ toast(errText(e), 6000); return; }
  if(!r.ok){ toast(r.error || '?', 8000); return; }
  toast(tt('report.reply_sent'), 5000);
  reportCheck();
}

/* On start-up, every few hours: are there answers? The button then says so. */
(function(){
  const EVERY = 4 * 3600 * 1000, KEY = 'reportChecked';
  setTimeout(async () => {
    let info; try{ info = await api.get('/api/report', 1); }catch(e){ return; }
    if(!info.relay || !info.sent) return;
    let last = 0; try{ last = +localStorage.getItem(KEY) || 0; }catch(e){}
    if(Date.now() - last < EVERY) return;
    try{ localStorage.setItem(KEY, String(Date.now())); }catch(e){}
    reportCheck(true);
  }, 4000);
})();
