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

const RENAME_WHAT = {region: 'province', settlement: 'settlement',
                     faction: 'faction'};

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
  activity(tt('renameui.opened_rename'), `${RENAME_WHAT[subject]} ${old} in ${mod}`);
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
  const u = renameUi, what = RENAME_WHAT[u.subject] || u.subject;
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
        onclick="renameApply()">${tt('renameui.rename_in_file',{files:p ? p.files.length : 0,files2:p && p.files.length === 1 ? '' : 's'})}</button>
    </div>`;
  const box = document.getElementById('renameBox');
  if(box && !u.busy){ box.focus(); box.setSelectionRange(box.value.length, box.value.length); }
}

const renameRuleHtml = () => renameUi.subject === 'faction'
  ? tt('renameui.a_faction_slot_is_a_lower')
    + tt('renameui.that_is_how_every_file_that')
  : tt('renameui.one_word_of_letters_digits_underscores')
    + tt('renameui.letter_a_name_with_a_space');

const renameLeadIn = () => renameUi.subject === 'settlement'
  ? tt('renameui.a_settlement_is_named_in_its')
    + tt('renameui.in_the_the_campaign_map_reads')
    + tt('renameui.points_at_it_by_name_except')
    + tt('renameui.never_edited')
  : renameUi.subject === 'region'
  ? tt('renameui.a_province_is_named_in_descr')
    + tt('renameui.pools_the_music_types_the_custom')
    + tt('renameui.names_file_it_is_also_named')
    + tt('renameui.and_never_edited_check_first_the')
  : tt('renameui.a_faction_slot_is_named_in')
    + tt('renameui.texture_records_of_battle_models_modeldb')
    + tt('renameui.from_the_slot_itself_the_campaign');

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
    `<div class="rnmono">${esc(a.src)} → ${esc(a.dst)}${
      a.dir ? tt('renameui.file',{files:a.files,files2:a.files === 1 ? '' : 's'}) : ''}</div>`).join('');
  const shown = renameUi.showAll ? (p.script || []) : (p.script || []).slice(0, 20);
  const script = !(p.script || []).length ? '' : `
    <div class="rnhead">${tt('renameui.the_campaign_script_names_it_time',{script_n:p.script.length,script:p.script.length === 1 ? '' : 's'})}</div>
    <div class="rnscroll">${shown.map(m => `<div class="rnmono">${
      esc(m.rel)}:${m.line} &nbsp; ${esc(m.text)}</div>`).join('')}</div>
    ${p.script.length > shown.length
      ? `<button onclick="renameShowAll()">${tt('renameui.show_the_other',{n:p.script.length - shown.length})}</button>` : ''}`;
  const review = !(p.review || []).length ? '' : `
    <div class="rnhead">${tt('renameui.also_writes_the_word_and_is',{review_n:p.review.length,review:p.review.length === 1 ? '' : 's'})}</div>
    ${p.review.map(r => `<div class="rnmono">${tt('renameui.line',{rel:esc(r.rel),hits:r.hits,hits2:r.hits === 1 ? '' : 's',lines:r.lines.join(', '),x:r.hits > r.lines.length ? ', …' : ''})}</div>`).join('')}`;
  return `
    ${(p.errors || []).map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${rows ? `<div class="rnhead">${tt('renameui.rewritten_line_in_file',{hits:p.hits,hits2:p.hits === 1 ? '' : 's',files_n:p.files.length,files:p.files.length === 1 ? '' : 's'})}</div>
      <table class="rntab"><thead><tr><th>${tt('renameui.file_2')}</th><th>${tt('renameui.lines')}</th><th>${tt('renameui.what_it_is')}</th>
        </tr></thead><tbody>${rows}</tbody></table>` : ''}
    ${assets ? `<div class="rnhead">${tt('renameui.art_the_engine_finds_from_the',{assets_n:p.assets.length,assets:p.assets.length === 1 ? '' : 's'})}</div>${assets}` : ''}
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
  if(!confirm(tt('renameui.rename_to',{x:RENAME_WHAT[u.subject],old:u.old,next:u.next})
    + tt('renameui.line_s_in_file_s',{hits:p.hits,files_n:p.files.length})
    + (p.assets.length ? tt('renameui.and_art_item_s_moved',{assets_n:p.assets.length}) : '')
    + `.\n`
    + (p.script.length
       ? tt('renameui.line_s_of_campaign_script_name',{script_n:p.script.length})
         + tt('renameui.changed_the_list_above_is_what') : '')
    + tt('renameui.backed_up_first_and_log_can'))) return;
  u.busy = true; renamePaint();
  let res;
  try{
    res = await api.post('/api/renames/apply', {mod: u.mod, subject: u.subject,
                                                old: u.old, new: u.next});
  }
  catch(e){ toast('✗ ' + errText(e), 8000); u.busy = false; renamePaint(); return; }
  finally{ u.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); renamePaint(); return; }
  toast(tt('renameui.renamed_in_file_s',{n:(res.files || []).length})
    + (res.script ? tt('renameui.campaign_script_line_s_still_name',{script:res.script})
       + tt('renameui.name_log_can_undo_this') : tt('renameui.log_can_undo_it')), 6000);
  const done = u.done, name = u.next;
  closeModal();
  if(done) await done(name);
}
