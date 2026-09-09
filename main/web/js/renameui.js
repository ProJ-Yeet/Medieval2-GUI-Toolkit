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
  activity('opened rename', `${RENAME_WHAT[subject]} ${old} in ${mod}`);
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
  modal.innerHTML = `<h2>Rename ${esc(what)} <b>${esc(u.old)}</b></h2>
    <div class="mbody">
      <div class="cmfield">
        <label>New name</label>
        <input id="renameBox" value="${esc(u.next)}"
          ${u.busy ? 'disabled' : ''} oninput="renameSet(this.value)">
        <div class="count">${renameRuleHtml()}</div>
      </div>
      ${p ? renamePlanHtml(p) : `<div class="count">${esc(renameLeadIn())}</div>`}
    </div>
    <div class="foot">
      <button onclick="closeModal()">Close</button>
      <button ${u.busy || !u.next || u.next === u.old ? 'disabled' : ''}
        onclick="renamePreview()">${p ? 'Check again' : 'Check what changes'}</button>
      <button class="primary"
        ${p && p.ok && !u.busy ? '' : 'disabled'}
        onclick="renameApply()">Rename in ${p ? p.files.length : 0} file${
          p && p.files.length === 1 ? '' : 's'}</button>
    </div>`;
  const box = document.getElementById('renameBox');
  if(box && !u.busy){ box.focus(); box.setSelectionRange(box.value.length, box.value.length); }
}

const renameRuleHtml = () => renameUi.subject === 'faction'
  ? 'A faction slot is a lower-case word of letters, digits and underscores - '
    + 'that is how every file that names one spells it.'
  : 'One word of letters, digits, underscores and hyphens, starting with a '
    + 'letter. A name with a space in it is two names to the engine.';

const renameLeadIn = () => renameUi.subject === 'settlement'
  ? 'A settlement is named in its province’s record, in the lookup file and '
    + 'in the {key} the campaign map reads it through. Nothing else in the game '
    + 'points at it by name except the campaign script, which is reported and '
    + 'never edited.'
  : renameUi.subject === 'region'
  ? 'A province is named in descr_strat, the win conditions, the mercenary '
    + 'pools, the music types, the custom battle tiles, the lookup file and the '
    + 'names file. It is also named in the campaign script, which is reported '
    + 'and never edited. Check first: the list is the point.'
  : 'A faction slot is named in about twenty files, in the length-prefixed '
    + 'texture records of battle_models.modeldb, and in the art the engine finds '
    + 'from the slot itself. The campaign script is reported and never edited.';

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
      a.dir ? ` (${a.files} file${a.files === 1 ? '' : 's'})` : ''}</div>`).join('');
  const shown = renameUi.showAll ? (p.script || []) : (p.script || []).slice(0, 20);
  const script = !(p.script || []).length ? '' : `
    <div class="rnhead">The campaign script names it ${p.script.length} time${
      p.script.length === 1 ? '' : 's'}, and none of them is rewritten
      <span class="w-bad">change these by hand</span></div>
    <div class="rnscroll">${shown.map(m => `<div class="rnmono">${
      esc(m.rel)}:${m.line} &nbsp; ${esc(m.text)}</div>`).join('')}</div>
    ${p.script.length > shown.length
      ? `<button onclick="renameShowAll()">Show the other ${
          p.script.length - shown.length}</button>` : ''}`;
  const review = !(p.review || []).length ? '' : `
    <div class="rnhead">Also writes the word, and is left alone
      <span class="count">${p.review.length} file${
        p.review.length === 1 ? '' : 's'}</span></div>
    ${p.review.map(r => `<div class="rnmono">${esc(r.rel)}: ${
      r.hits} line${r.hits === 1 ? '' : 's'} (${
      r.lines.join(', ')}${r.hits > r.lines.length ? ', …' : ''})</div>`).join('')}`;
  return `
    ${(p.errors || []).map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${rows ? `<div class="rnhead">Rewritten
        <span class="count">${p.hits} line${p.hits === 1 ? '' : 's'} in ${
          p.files.length} file${p.files.length === 1 ? '' : 's'}</span></div>
      <table class="rntab"><thead><tr><th>File</th><th>Lines</th><th>What it is</th>
        </tr></thead><tbody>${rows}</tbody></table>` : ''}
    ${assets ? `<div class="rnhead">Art the engine finds from the name, moved
      <span class="count">${p.assets.length} item${
        p.assets.length === 1 ? '' : 's'}</span></div>${assets}` : ''}
    ${script}
    ${review}
    ${(p.warnings || []).map(w => `<div class="w-warn">${esc(w)}</div>`).join('')}
    ${(p.notes || []).map(n => `<div class="count">${esc(n)}</div>`).join('')}
    <div class="count">One backup set for all of it, and one 🕑 Log entry:
      a rename half applied is a mod that will not load, so an undo that put back
      some of these files would be worse than one that put back none.</div>`;
}

function renameShowAll(){ renameUi.showAll = true; renamePaint(); }

async function renameApply(){
  const u = renameUi;
  if(u.busy || !u.plan || !u.plan.ok) return;
  const p = u.plan;
  if(!confirm(`Rename ${RENAME_WHAT[u.subject]} ${u.old} to ${u.next}?\n\n`
    + `${p.hits} line(s) in ${p.files.length} file(s)`
    + (p.assets.length ? `, and ${p.assets.length} art item(s) moved` : '')
    + `.\n`
    + (p.script.length
       ? `\n${p.script.length} line(s) of campaign script name it and are NOT `
         + `changed - the list above is what you have to edit by hand.\n` : '')
    + `\nBacked up first, and 🕑 Log can undo all of it.`)) return;
  u.busy = true; renamePaint();
  let res;
  try{
    res = await api.post('/api/renames/apply', {mod: u.mod, subject: u.subject,
                                                old: u.old, new: u.next});
  }
  catch(e){ toast('✗ ' + errText(e), 8000); u.busy = false; renamePaint(); return; }
  finally{ u.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); renamePaint(); return; }
  toast(`Renamed in ${(res.files || []).length} file(s)`
    + (res.script ? `. ${res.script} campaign script line(s) still name the old `
       + `name - 🕑 Log can undo this` : '. 🕑 Log can undo it'), 6000);
  const done = u.done, name = u.next;
  closeModal();
  if(done) await done(name);
}
