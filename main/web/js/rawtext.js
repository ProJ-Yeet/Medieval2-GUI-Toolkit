/* rawtext.js - Raw text: any file the toolkit reads, as plain text (Phase 21, D11)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE ESCAPE HATCH. Every other screen here is a parser with a form on top,
   and every parser meets the mod that does something it does not model. This
   one is a text box over the whole file, for exactly that case.

   Every name here starts `rt`; there was none in the tree before.

   IT IS STILL A SAVE. The page never writes a byte: /api/raw/plan says what a
   save would change - the lines, with their numbers, and anything the
   toolkit's own reader now objects to - and only /api/raw/apply writes, with
   a backup and a log entry, so 🕑 Log's Undo takes it back like any other save.
   See unittransfer/rawtext.py for the three things a text box gets wrong and
   the server puts right: the encoding, the line endings, and somebody else's
   write in between.

   THE TEXT BOX IS NOT REDRAWN. The search box re-renders the mode on every
   keystroke, and rebuilding a textarea holding a megabyte of EDB would lose the
   caret, the scroll and the undo history the browser keeps for it. So the file
   list and the editor are two elements, and a search repaints only the list.
   ===================================================================== */

function rtNew(mod){
  return {mod, files: null, err: '', rel: '', doc: null, dirty: false,
          plan: null, busy: false, loading: false};
}

//: Where another screen asked to land - "open this file as text" from the
//: faction audit, say - held across the mode switch.
let rtWant = null;

async function loadRawtext(){
  const mod = state.src;
  const k = state.rt = rtNew(mod);
  main.innerHTML = `<div class="empty">${tt('rawtext.listing')} ` + esc(mod) + `${tt('rawtext.s_text_files')}</div>`;
  let r;
  try{ r = await api.get('/api/raw/files?mod=' + enc(mod)); }
  catch(e){ r = {error: errText(e)}; }
  if(stale('rawtext', mod) || state.rt !== k) return;
  if(r.error){ k.err = r.error; }
  else k.files = r;
  rtBuild();
  const want = rtWant;
  rtWant = null;
  if(want) rtRead(want.rel, want.line);
}

function renderRawtext(){
  const k = state.rt;
  if(!k || k.mod !== state.src){ loadRawtext(); return; }
  if(!document.getElementById('rtList')){ rtBuild(); return; }
  rtPaintList();
}

//: The page, once. After this only the list and the pieces around the text box
//: are repainted - see the header.
function rtBuild(){
  const k = state.rt;
  if(k.err){
    main.innerHTML = `<div class="empty">${tt('rawtext.couldnt_list_the_files')}<br>
      <span class="count">${esc(k.err)}</span><br><br>
      <button class="primary" onclick="loadRawtext()">${tt('common.retry')}</button></div>`;
    return;
  }
  main.innerHTML = `<div class="trwrap rtwrap">
    <div class="trlist">
      <div class="trnote">${tt('rawtext.every_text_file_the_toolkit_reads')}
        <button class="rtput" onclick="rtPutAny()" title="${ttA('rawtext.put_any_file_from_disk_into')}">${tt('rawtext.put_a_file_into_the_mod')}</button>
        <input type="file" id="rtPutFile" style="display:none" onchange="rtPutChosen(this)"></div>
      <div class="trrows" id="rtList"></div>
    </div>
    <div class="trmain" id="rtMain">${rtMainHtml()}</div>
  </div>`;
  rtPaintList();
  rtWireBox();
}

function rtPaintList(){
  const k = state.rt, el = document.getElementById('rtList');
  if(!el || !k.files) return;
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  el.innerHTML = (k.files.groups || []).map(g => {
    const rows = g.files.filter(f => !q || f.rel.toLowerCase().includes(q)
                                         || (f.screen || '').toLowerCase().includes(q));
    shown += rows.length;
    if(!rows.length) return '';
    return `<div class="rtgroup">${esc(g.label)}</div>` + rows.map(f => `<button
        class="trrow rtrow${f.rel === k.rel ? ' on' : ''}${f.too_big ? ' off' : ''}"
        onclick="rtOpen('${q1(esc(f.rel))}')" title="data/${esc(f.rel)}">
      <span class="antxt"><span class="nm">${esc(f.name)}${
        f.rel === k.rel && k.dirty ? ' <span class="w-warn">●</span>' : ''}</span>
      <span class="sub">${rtSize(f.size)}${f.screen ? ' · ' + esc(f.screen) : ''}${
        f.too_big ? tt('rawtext.too_large_to_open_here') : ''}</span></span>
    </button>`).join('');
  }).join('') || `<div class="count" style="padding:8px">${tt('rawtext.no_file_matches')}</div>`;
  count.textContent = `${shown}/${k.files.count}`;
}

function rtSize(n){
  return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB'
       : n >= 1024 ? Math.round(n / 1024) + ' KB' : n + ' B';
}

/* Open a file as text - from the list, or from any other screen. Asking to
   leave a file with unsaved edits is the one confirmation this screen owes:
   the text box is the only copy of them. */
function rtOpen(rel, line){
  if(state.mode !== 'rawtext'){
    rtWant = {rel, line};
    // a different mod's screen asking is answered in that mod
    if(state.rt && state.rt.mod !== state.src) state.rt = null;
    setAppMode('rawtext');
    return;
  }
  const k = state.rt;
  if(!k || !k.files){ rtWant = {rel, line}; return; }
  if(k.rel === rel && k.doc){ if(line) rtGoLine(line); return; }
  if(k.dirty && !confirm(tt('rawtext.leave_without_saving_the_edits_are',{rel:k.rel})))
    return;
  rtRead(rel, line);
}

async function rtRead(rel, line){
  const k = state.rt;
  k.rel = rel; k.doc = null; k.dirty = false; k.plan = null; k.loading = true;
  rtPaintMain(); rtPaintList();
  let d;
  try{ d = await api.get(`/api/raw/file?mod=${enc(k.mod)}&rel=${enc(rel)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.rt !== k || k.rel !== rel) return;
  k.loading = false;
  k.doc = d;
  activity(tt('rawtext.opened_raw_file'), `${rel} in ${k.mod}`);
  rtPaintMain(); rtPaintList();
  if(line) rtGoLine(line);
}

function rtPaintMain(){
  const el = document.getElementById('rtMain');
  if(!el) return;
  el.innerHTML = rtMainHtml();
  rtWireBox();
}

function rtMainHtml(){
  const k = state.rt;
  if(!k) return '';
  if(!k.rel) return `<div class="empty">${tt('rawtext.pick_a_file_on_the_left')}</div>`;
  if(k.loading) return `<div class="empty">${tt('rawtext.reading_the_file')}</div>`;
  const d = k.doc;
  if(!d || d.error) return `<div class="empty"><span class="w-bad">✗ ${
    esc((d && d.error) || tt('rawtext.no_file'))}</span></div>`;
  const ro = !!d.readonly;
  return `<div class="trbar rtbar">
      <div><b>data/${esc(d.rel)}</b>
        <div class="count">${tt('rawtext.lines',{encoding:esc(d.encoding || ''),x:d.newline ? ' · ' + d.newline : '',mixed:d.mixed ? tt('rawtext.mixed_each_untouched_line_keeps_its') : '',lines:d.lines || 0,rtSize:rtSize(d.size)})}</div></div>
      <span class="sp"></span>
      ${d.screen && d.mode && d.mode !== 'rawtext' ? `<button
        onclick="rtGoScreen('${esc(d.mode)}')"
        title="${ttA('rawtext.the_screen_that_edits_this_file')}">${tt('rawtext.open_in',{screen:esc(d.screen)})}</button>` : ''}
      <label class="count rtgo">${tt('rawtext.line')} <input id="rtLine" type="number" min="1"
        onkeydown="if(event.key==='Enter')rtGoLine(this.value)"></label>
      <span class="count" id="rtCaret"></span>
      <button onclick="rtReload()" title="${ttA('rawtext.read_the_file_from_disk_again')}">${tt('rawtext.reload')}</button>
      <a class="btnlike" href="/api/file?mod=${enc(state.src)}&rel=${enc(d.rel)}" download
        title="${ttA('rawtext.the_file_exactly_as_it_is')}">${tt('rawtext.download')}</a>
      <button onclick="rtPutOver('${q1(esc(d.rel))}')"
        title="${ttA('rawtext.replace_this_file_with_one_from')}">${tt('rawtext.replace')}</button>
      <button class="primary" id="rtSaveBtn" onclick="rtSave()"
        ${ro || !k.dirty || k.busy ? 'disabled' : ''}>${tt('rawtext.save')}</button>
    </div>
    ${ro ? `<div class="trfind w-warn">${tt('rawtext.shown_not_saved',{readonly:esc(d.readonly)})}</div>` : ''}
    <textarea id="rtBox" class="rtbox" spellcheck="false" wrap="off"
      ${ro ? 'readonly' : ''}></textarea>
    <div id="rtPlan">${rtPlanHtml()}</div>`;
}

//: The text goes in by property, not by markup: a megabyte of file inside an
//: attribute-escaped template is twice the work and one stray `</textarea>` in a
//: comment away from a broken page.
function rtWireBox(){
  const k = state.rt, box = document.getElementById('rtBox');
  if(!box || !k || !k.doc) return;
  box.value = k.dirty && k.work !== undefined ? k.work : (k.doc.text || '');
  box.oninput = () => {
    k.work = box.value;
    const was = k.dirty;
    k.dirty = box.value !== k.doc.text;
    if(k.plan){ k.plan = null; rtPaintPlan(); }
    const btn = document.getElementById('rtSaveBtn');
    if(btn) btn.disabled = !!k.doc.readonly || !k.dirty || k.busy;
    if(was !== k.dirty) rtPaintList();
  };
  box.onkeydown = e => {
    // the game files are laid out in tab columns, and Tab leaving the box
    // would make them uneditable by hand - which is the whole point here
    if(e.key === 'Tab' && !e.ctrlKey && !e.altKey && !box.readOnly){
      e.preventDefault();
      box.setRangeText('\t', box.selectionStart, box.selectionEnd, 'end');
      box.oninput();
    }else if((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's'){
      e.preventDefault();
      rtSave();
    }
  };
  box.onkeyup = box.onclick = () => rtCaret(box);
}

function rtCaret(box){
  const el = document.getElementById('rtCaret');
  if(!el) return;
  const line = box.value.slice(0, box.selectionStart).split('\n').length;
  el.textContent = `line ${line}`;
}

//: Put the caret on a line and scroll it into view.
function rtGoLine(n){
  const box = document.getElementById('rtBox');
  n = parseInt(n, 10);
  if(!box || !(n > 0)) return;
  const lines = box.value.split('\n');
  n = Math.min(n, lines.length);
  let at = 0;
  for(let i = 0; i < n - 1; i++) at += lines[i].length + 1;
  box.focus();
  box.setSelectionRange(at, at + lines[n - 1].length);
  // a line's height is the box's own, so the scroll is arithmetic
  const lh = parseFloat(getComputedStyle(box).lineHeight) || 16;
  box.scrollTop = Math.max(0, (n - 4) * lh);
  rtCaret(box);
}

function rtGoScreen(mode){
  const k = state.rt;
  if(k && k.dirty && !confirm(tt('rawtext.leave_without_saving_the_edits_are',{rel:k.rel})))
    return;
  if(k) k.dirty = false;
  if(mode === 'factions' && typeof minorFactions === 'function') return minorFactions();
  setAppMode(mode);
}

function rtReload(){
  const k = state.rt;
  if(!k || !k.rel) return;
  if(k.dirty && !confirm(tt('rawtext.throw_away_the_edits_in_this'))) return;
  rtRead(k.rel);
}

/* ---------- the save ---------- */

async function rtSave(){
  const k = state.rt;
  if(!k || !k.doc || !k.dirty || k.busy || k.doc.readonly) return;
  k.busy = true; rtPaintPlan();
  let r;
  try{ r = await api.post('/api/raw/plan', rtBody()); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(state.rt !== k) return;
  k.plan = r.plan || {errors: [r.error || tt('rawtext.no_plan')]};
  if(r.error && !(k.plan.errors || []).length) k.plan.errors = [r.error];
  rtPaintPlan();
  const el = document.getElementById('rtPlan');
  if(el) el.scrollIntoView({block: 'nearest'});
}

function rtBody(){
  const k = state.rt;
  return {mod: k.mod, rel: k.rel, sig: k.doc.sig, text: k.work};
}

function rtPaintPlan(){
  const el = document.getElementById('rtPlan');
  if(el) el.innerHTML = rtPlanHtml();
  const btn = document.getElementById('rtSaveBtn');
  const k = state.rt;
  if(btn && k && k.doc) btn.disabled = !!k.doc.readonly || !k.dirty || k.busy;
}

/* The confirmation, drawn under the box rather than in a confirm(): the change
   is the thing to read before writing, and a dialog cannot show forty hunks
   with their line numbers. */
function rtPlanHtml(){
  const k = state.rt, p = k && k.plan;
  if(k && k.busy) return `<div class="count rtplan">${tt('common.working_out_what_would_change')}</div>`;
  if(!p) return '';
  const errs = p.errors || [];
  if(errs.length) return `<div class="rtplan">${errs.map(e =>
    `<div class="w-bad">✗ ${esc(e)}</div>`).join('')}
    <div class="csbtns"><button onclick="rtPlanClose()">${tt('rawtext.keep_editing')}</button>${
      errs.some(e => /changed on disk/.test(e))
        ? `<button onclick="rtReload()">${tt('rawtext.reload_from_disk')}</button>` : ''}</div></div>`;
  const c = p.counts || {};
  const hunks = (p.hunks || []).map(h => `<div class="rthunk">
      <div class="count">${tt('rawtext.line_2',{at:h.at})}</div>
      ${(h.was || []).map(l => `<div class="rtdel">- ${esc(l) || '&nbsp;'}</div>`).join('')}
      ${(h.now || []).map(l => `<div class="rtadd">+ ${esc(l) || '&nbsp;'}</div>`).join('')}
      ${h.more ? `<div class="count">${tt('rawtext.and_more_line_s_here',{more:h.more})}</div>` : ''}
    </div>`).join('');
  const shown = (p.hunks || []).length;
  return `<div class="rtplan">
    <div>${tt('rawtext.write_data_changed_added_removed_every',{rel:esc(p.rel),changed:c.changed || 0,added:c.added || 0,removed:c.removed || 0})}</div>
    ${(p.warnings || []).map(w => `<div class="w-warn">⚠ ${esc(w)}</div>`).join('')}
    <div class="rthunks">${hunks}</div>
    ${shown >= 40 ? `<div class="count">${tt('rawtext.only_the_first_forty_changes_are')}</div>` : ''}
    ${(p.notes || []).map(n => `<div class="count">${esc(n)}</div>`).join('')}
    <div class="csbtns">
      <button class="primary" onclick="rtApply()">${tt('rawtext.write_it')}</button>
      <button onclick="rtPlanClose()">${tt('rawtext.keep_editing')}</button>
      <span class="count">${tt('common.backed_up_first_and_log_can_2')}</span>
    </div>
  </div>`;
}

function rtPlanClose(){
  const k = state.rt;
  if(!k) return;
  k.plan = null;
  rtPaintPlan();
}

async function rtApply(){
  const k = state.rt;
  if(!k || !k.plan || k.busy) return;
  k.busy = true; rtPaintPlan();
  let r;
  try{ r = await api.post('/api/raw/apply', rtBody()); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(state.rt !== k) return;
  if(r.error){
    k.plan = r.plan || {errors: [r.error]};
    if(!(k.plan.errors || []).length) k.plan.errors = [r.error];
    rtPaintPlan(); toast('✗ ' + r.error, 8000); return;
  }
  toast(tt('rawtext.saved_data_log_can_undo_it',{rel:k.rel}));
  activity(tt('rawtext.raw_save'), `${k.rel} in ${k.mod}`);
  rtForget(k.rel);
  const box = document.getElementById('rtBox');
  const top = box ? box.scrollTop : 0, at = box ? box.selectionStart : 0;
  k.dirty = false;
  await rtRead(k.rel);
  // back where the person was, in the file as it now is on disk
  const again = document.getElementById('rtBox');
  if(again){ again.scrollTop = top; again.setSelectionRange(at, at); }
}

/* Every other screen holds what it read, and a raw save can change any file
   under any of them. So what they hold for this mod is dropped, and each one
   reads again the next time it is opened - the same thing picking another mod
   does. The unit list is the one read eagerly, because the sidebar shows it. */
function rtForget(rel){
  Object.assign(state, {cfg: {}, bmdb: null, snd: null, str: null, tr: null,
    an: null, mf: null, fac: null, bld: null, gu: null, cmap: null, cj: null,
    fau: null, stm: null, cards: null});
  if(/(^|\/)export_descr_unit\.txt$|^text\/export_units\.txt$/i.test(rel)
     && typeof loadSource === 'function') loadSource();
}


/* ---- one file in or out (Phase 62, B3) ----
   Download is a plain link to /api/file. Putting a file in is a plan and then a
   write, like every save here: the plan names an encoding change, what the
   file's own reader now reports, and the .strings.bin a text/ file recompiles,
   and nothing is written until that has been read. */
let rtPutTarget = null;

function rtPutAny(){
  const rel = (prompt(tt('rawtext.where_in_the_mod_should_it')
                      + 'ui/units/england/#english_archers.tga', '') || '').trim();
  if(!rel) return;
  rtPutTarget = {rel: rel.replace(/^data\//i, ''), replace: false};
  const i = document.getElementById('rtPutFile');
  if(i){ i.value = ''; i.click(); }
}

function rtPutOver(rel){
  rtPutTarget = {rel, replace: true};
  const i = document.getElementById('rtPutFile');
  if(i){ i.value = ''; i.click(); }
}

async function rtPutChosen(input){
  const f = input.files && input.files[0], t = rtPutTarget;
  if(!f || !t) return;
  const buf = new Uint8Array(await f.arrayBuffer());
  let bin = '';
  for(let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
  const body = {mod: state.src, rel: t.rel, data: btoa(bin), replace: t.replace};
  let r;
  try{ r = await api.post('/api/file/put_plan', body); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error && /already in the mod/.test(r.error)){
    if(!confirm(tt('rawtext.data_is_already_in_the_mod',{rel:t.rel,name:f.name}))) return;
    body.replace = true;
    try{ r = await api.post('/api/file/put_plan', body); }
    catch(e){ r = {error: errText(e)}; }
  }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  const p = r.plan || {};
  if(!confirm(tt('rawtext.put_at_data',{name:f.name,rel:p.rel,changes:(p.changes || []).join('\n')})
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.join('\n⚠ ') : '')
    + tt('rawtext.backed_up_first_and_log_undoes'))) return;
  let w;
  try{ w = await api.post('/api/file/put_apply', body); }
  catch(e){ w = {error: errText(e)}; }
  if(w.error){ toast('✗ ' + w.error, 8000); return; }
  toast(tt('rawtext.data_written_log_can_undo_it',{rel:p.rel}), 5000);
  activity(tt('rawtext.put_a_file'), tt('rawtext.data_in',{rel:p.rel,src:state.src}));
  if(state.rt && state.rt.rel === p.rel) rtReload();
  else if(state.rt) loadRawtext();
}
