/* ---- renaming a province, a settlement or a faction (19b, D2 and D3) ----

   One dialog for all three, because behind them is one engine
   (`unittransfer/renames.py`) and because the thing that has to be shown is the
   same every time: THE LIST. A faction rename in a real mod rewrites
   twenty-four files and four thousand lines, moves five folders of art and
   leaves four hundred lines of campaign script naming a faction that no longer
   exists. `confirm()` with a sentence in it is not consent to that.

   So the plan comes back first and is shown in full - what changes, what is
   reported and refused, what merely writes the same word and is left alone -
   and only then is there a button. Same split as every other write in the
   toolkit; the difference is only that here the preview is the point rather
   than a courtesy. */

//: What is being renamed, in the page's language.
function renameWhat(subject){
  return subject === 'region' ? tt('renameui.what_province')
    : subject === 'settlement' ? tt('renameui.what_settlement')
    : subject === 'faction' ? tt('renameui.what_faction')
    : subject;
}

//: One rename in flight: the plan, the boxes, and who to tell when it lands.
const renameUi = {subject: '', old: '', next: '', mod: '', plan: null,
                  busy: false, done: null, showAll: false};

/* `after` is called with the new name once the write has landed, so the screen
   that opened this can re-read itself under it - the record the panel was
   showing is gone and a repaint of the old name would 404. */
async function renameOpen(mod, subject, old, after){
  renameUi.subject = subject; renameUi.old = old; renameUi.next = old;
  renameUi.mod = mod; renameUi.plan = null; renameUi.done = after || null;
  renameUi.busy = false; renameUi.showAll = false;
  activity(tt('renameui.opened_rename'), `${renameWhat(subject)} ${old} in ${mod}`);
  const modal = document.getElementById('modal');
  modal.className = 'modal wide';
  overlay.classList.add('open');
  renamePaint();
}

function renameSet(value){
  renameUi.next = value;
  renameUi.plan = null;                   // a new name means the old plan is stale
  renamePaint();
}

function renamePaint(){
  const u = renameUi, what = renameWhat(u.subject);
  const modal = document.getElementById('modal');
  const p = u.plan;
  modal.innerHTML = `<h2>${tt('renameui.rename',{what:esc(what)})} <b>${esc(u.old)}</b></h2>
    <div class="mbody">
      <div class="cmfield">
        <label>${tt('renameui.new_name')}</label>
        <input id="renameBox" value="${esc(u.next)}"
          ${u.busy ? 'disabled' : ''} oninput="renameSet(this.value)">
        <div class="count">${renameRuleHtml()}</div>
      </div>
      ${p ? renamePlanHtml(p) : `<div class="count">${esc(renameLeadIn())}</div>`}
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button ${u.busy || !u.next || u.next === u.old ? 'disabled' : ''}
        onclick="renamePreview()">${p ? tt('renameui.check_again') : tt('renameui.check_what_changes')}</button>
      <button class="primary"
        ${p && p.ok && !u.busy ? '' : 'disabled'}
        onclick="renameApply()">${ttN('renameui.rename_in_files', p ? p.files.length : 0)}</button>
    </div>`;
  const box = document.getElementById('renameBox');
  if(box && !u.busy){ box.focus(); box.setSelectionRange(box.value.length, box.value.length); }
}

const renameRuleHtml = () => renameUi.subject === 'faction'
  ? tt('renameui.faction_slot_rule')
  : tt('renameui.name_rule');

const renameLeadIn = () => renameUi.subject === 'settlement'
  ? tt('renameui.lead_in_settlement')
  : renameUi.subject === 'region'
  ? tt('renameui.lead_in_region')
  : tt('renameui.lead_in_faction');

async function renamePreview(){
  const u = renameUi;
  if(u.busy || !u.next || u.next === u.old) return;
  u.busy = true; renamePaint();
  let res;
  try{
    res = await api.post('/api/renames/plan', {mod: u.mod, subject: u.subject,
                                               old: u.old, new: u.next});
  }
  catch(e){ toast('✗ ' + errText(e), 8000); u.busy = false; renamePaint(); return; }
  finally{ u.busy = false; }
  u.plan = res.plan || null;
  if(res.error && !(u.plan && u.plan.files.length)) toast('✗ ' + res.error, 8000);
  renamePaint();
}

/* The whole report, in the order it matters: what changes, what is refused,
   what is only the same word somewhere else. */
function renamePlanHtml(p){
  const rows = (p.files || []).map(f => `<tr>
      <td class="rnmono">${esc(f.rel)}</td>
      <td class="n">${f.count}</td>
      <td>${esc(f.label)}<div class="count">${esc(f.note || '')}</div></td>
    </tr>`).join('');
  const assets = (p.assets || []).map(a =>
    `<div class="rnmono">${a.dir ? ttN('renameui.asset_move_dir', a.files, {src:esc(a.src),dst:esc(a.dst)})
      : tt('renameui.asset_move', {src:esc(a.src),dst:esc(a.dst)})}</div>`).join('');
  const shown = renameUi.showAll ? (p.script || []) : (p.script || []).slice(0, 20);
  const script = !(p.script || []).length ? '' : `
    <div class="rnhead">${ttN('renameui.script_names_it_times', p.script.length)}</div>
    <div class="rnscroll">${shown.map(m => `<div class="rnmono">${
      esc(m.rel)}:${m.line} &nbsp; ${esc(m.text)}</div>`).join('')}</div>
    ${p.script.length > shown.length
      ? `<button onclick="renameShowAll()">${tt('renameui.show_the_other',{n:p.script.length - shown.length})}</button>` : ''}`;
  const review = !(p.review || []).length ? '' : `
    <div class="rnhead">${ttN('renameui.also_writes_the_word_files', p.review.length)}</div>
    ${p.review.map(r => `<div class="rnmono">${ttN('renameui.review_file_lines', r.hits, {rel:esc(r.rel),lines:r.lines.join(', '),more:r.hits > r.lines.length ? ', …' : ''})}</div>`).join('')}`;
  return `
    ${(p.errors || []).map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${rows ? `<div class="rnhead">${tt('renameui.rewritten_lines_in_files', {lines:ttN('renameui.n_lines', p.hits), files:ttN('renameui.n_files', p.files.length)})}</div>
      <table class="rntab"><thead><tr><th>${tt('renameui.file_2')}</th><th>${tt('renameui.lines')}</th><th>${tt('renameui.what_it_is')}</th>
        </tr></thead><tbody>${rows}</tbody></table>` : ''}
    ${assets ? `<div class="rnhead">${ttN('renameui.art_moved_items', p.assets.length)}</div>${assets}` : ''}
    ${script}
    ${review}
    ${(p.warnings || []).map(w => `<div class="w-warn">${esc(w)}</div>`).join('')}
    ${(p.notes || []).map(n => `<div class="count">${esc(n)}</div>`).join('')}
    <div class="count">${tt('renameui.one_backup_set_for_all_of')}</div>`;
}

function renameShowAll(){ renameUi.showAll = true; renamePaint(); }

async function renameApply(){
  const u = renameUi;
  if(u.busy || !u.plan || !u.plan.ok) return;
  const p = u.plan;
  if(!confirm(tt('renameui.confirm_rename',{x:renameWhat(u.subject),old:u.old,next:u.next,
    hits:p.hits,files_n:p.files.length,
    art:p.assets.length ? tt('renameui.confirm_art_moved',{assets_n:p.assets.length}) : '',
    script:p.script.length ? tt('renameui.confirm_script_not_changed',{script_n:p.script.length}) : ''}))) return;
  u.busy = true; renamePaint();
  let res;
  try{
    res = await api.post('/api/renames/apply', {mod: u.mod, subject: u.subject,
                                                old: u.old, new: u.next});
  }
  catch(e){ toast('✗ ' + errText(e), 8000); u.busy = false; renamePaint(); return; }
  finally{ u.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); renamePaint(); return; }
  toast(res.script ? tt('renameui.renamed_script_left',{n:(res.files || []).length,script:res.script})
    : tt('renameui.renamed_done',{n:(res.files || []).length}), 6000);
  const done = u.done, name = u.next;
  closeModal();
  if(done) await done(name);
}
