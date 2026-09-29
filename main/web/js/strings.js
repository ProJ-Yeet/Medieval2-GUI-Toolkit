/* strings.js - Strings mode: the compiled .txt.strings.bin files, read and written

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= STRINGS MODE =======================
   Every piece of text the game shows lives in data/text as a pair: a .txt anyone
   can read, and a .strings.bin the game compiled from it. **The game reads the
   .bin.** Edit the .txt and nothing changes on screen until the .bin agrees -
   which is where "delete the .bin and let the game rebuild it" comes from, and
   why a mod can sit for years showing text its own .txt has not said in months.

   So this module works on the .bin directly. A row here is an entry in the
   compiled file: change it, save it, and the game says the new thing on the next
   launch with nothing deleted and nothing to rebuild. `⟳ Rebuild from .txt`
   recompiles the whole archive from the text file beside it, for when the .txt
   is the one that is right.

   Rows are filtered on the SERVER (see unittransfer/strings.py) - names.txt runs
   to 20 757 entries and shipping all of them so the browser can hide 20 000 is
   how a local tool starts feeling like a website.

   Four archives (battle, shared, strat, tooltips) store bare strings the engine
   addresses by position, with no tags at all. They are editable by row here, but
   they get no Code View: `{tag}text` is not a shape they have.

   48: a tagged archive takes new rows and loses rows too - the backend has taken
   `adds` and `removes` since Phase 6 and this page only ever sent `edits`. An
   archive addressed by position takes neither, and says why in the backend's
   own two sentences (`refused` on the entries payload) rather than a copy of
   them here. */

const STR_PAGE = 400;

async function loadStrings(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('strings.looking_for')} ` + esc(mod) + `${tt('strings.s_text_files')}</div>`;
  let r;
  try{ r = await api.get('/api/strings?mod=' + enc(mod)); }
  catch(e){ if(stale('strings', mod)) return;
    main.innerHTML = `<div class="empty">${tt('strings.couldnt_read_the_text_folder')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadStrings()">${tt('common.retry')}</button></div>`; return; }
  if(stale('strings', mod)) return;
  const keep = state.str && state.str.mod === mod ? state.str.reopen : '';
  state.str = Object.assign({file:'', rows:null, edits:{}, adds:[], removes:{}, busy:false}, r);
  if(keep && r.files.some(f => f.rel === keep)){ renderStrings(); return strOpen(keep); }
  undoReset();
  renderStrings();
}

function renderStrings(){
  const s = state.str;
  if(!s){ loadStrings(); return; }
  const strip = minorTabsHtml('', s.dir || 'data/text');
  if(!s.files.length){
    main.innerHTML = strip + `<div class="empty">${tt('strings.has_no_strings_bin_files_looked',{mod:esc(s.mod),dir:esc(s.dir)})}</div>`;
    return;
  }
  count.textContent = ttN('strings.file_count', s.files.length);
  main.innerHTML = strip + `<div class="strwrap">
    <div class="strlist">${s.files.map(strFileRow).join('')}</div>
    <div class="strmain" id="strMain">${strRowsHtml()}</div>
  </div>`;
}

/* "<name>.txt is newer" is a comparison of two file dates, and on its own it
   reads like an accusation without saying what was done. What it means is one
   specific thing: the plain-text file was saved AFTER the .bin beside it was
   last compiled, and the game reads the .bin. So anything the .txt has been
   made to say since then is not on screen in the game, and will not be until
   something compiles it across.

   That is a fact worth showing and almost never a fault: hand-editing the .txt
   and never rebuilding is how most mods are written, and copying files in the
   wrong order does it too. Nothing is broken by it, so the wording stays a
   quiet warning colour and the whole explanation hangs off a ? rather than
   crowding a list of forty files. */
const STR_STALE_HELP = tt('strings.stale_help');

function strFileRow(f){
  const on = state.str.file === f.rel;
  const state_ = f.error ? `<span class="w-bad">${tt('strings.unreadable')}</span>`
    : f.stale ? tt('strings.is_newer_than_this_bin',{txt:esc(f.txt),txt2:esc(f.txt),x:qm(STR_STALE_HELP, tt('strings.what_is_newer_means'))})
    : f.txt ? `<span class="count">${esc(f.txt)}</span>`
    : `<span class="count">${tt('strings.no_txt_beside_it')}</span>`;
  return `<button class="strfile${on?' on':''}" onclick="strOpen('${q1(esc(f.rel))}')">
    <div class="nm">${esc(f.label)}${f.tagged?'':` <span class="badge">${tt('strings.by_position')}</span>`}</div>
    <div class="sub">${f.error?'':tt('strings.entries',{f:f.entries})}${state_}</div>
  </button>`;
}

async function strOpen(rel){
  activity(tt('strings.opened_strings_file'), `${rel} in ${state.src}`);
  const s = state.str;
  s.file = rel; s.rows = null; s.edits = {}; s.adds = []; s.removes = {}; s.offset = 0;
  renderStrings();
  await strFetchRows();
}

async function strFetchRows(){
  const s = state.str, rel = s.file;
  if(!rel) return;
  const q = search.value.trim();
  let r;
  try{
    r = await api.get(`/api/strings/entries?mod=${enc(s.mod)}&file=${enc(rel)}`
      + `&q=${enc(q)}&limit=${STR_PAGE}&offset=${s.offset||0}`);
  }catch(e){ r = {error: '' + e}; }
  if(state.mode !== 'strings' || state.str !== s || s.file !== rel) return;
  s.rows = r;
  // A file is open now: this is Ctrl+Z's baseline. `undoBaseline` rather than
  // `undoReset` because this also runs for paging and searching within the same
  // file, and pending edits (and their history) outlive both.
  undoBaseline();
  const el = document.getElementById('strMain');
  if(el) el.innerHTML = strRowsHtml();
}

function strRowsHtml(){
  const s = state.str;
  if(!s.file) return `<div class="empty">${tt('strings.pick_a_file_on_the_left')}</div>`;
  const r = s.rows;
  if(!r) return `<div class="empty">${tt('strings.reading_the_entries')}</div>`;
  if(r.error) return `<div class="empty"><span class="w-bad">✗ ${esc(r.error)}</span></div>`;
  const f = s.files.find(x => x.rel === s.file) || {};
  const pending = strPending();
  const shown = r.rows.length, more = r.matched - (r.offset + shown);
  const nAdd = s.adds.length, nRm = Object.keys(s.removes).length;
  const refused = r.refused || {};
  return `<div class="strbar">
      <div>
        <b>${esc(r.name)}</b>
        <span class="count">${r.matched === r.count ? `${r.count} entries`
          : tt('strings.of_entries_match',{matched:r.matched,count:r.count})}${
          r.tagged ? '' : tt('strings.addressed_by_position')}</span>
      </div>
      <span class="sp"></span>
      ${r.tagged ? `<button onclick="strAddRow()" title="${ttA('strings.a_new_entry_in_this_archive')}">${tt('strings.new_entry')}</button>` : ''}
      ${f.txt && r.tagged ? `<button title="${ttA('strings.compile_over_this_archive_so_the',{txt:esc(f.txt)})}"
        onclick="strRebuild()">${tt('strings.rebuild_from',{txt:esc(f.txt)})}</button>` : ''}
      <button class="primary" ${pending?'':'disabled'} onclick="strSave()">
        ${ttN('strings.save_changes',pending)}</button>
    </div>
    ${nAdd || nRm ? `<div class="strnote">${tt(nAdd && nRm ? 'strings.entries_now_after_saving_new_and_removed' : nAdd ? 'strings.entries_now_after_saving_new' : 'strings.entries_now_after_saving_removed',{count:r.count,after:r.count + nAdd - nRm,added:nAdd,removed:nRm,index:r.index && nAdd !== nRm ? tt('strings.the_archives_trailing_tag_index_names',{index:r.index}) : ''})}</div>` : ''}
    ${refused.add ? `<div class="strnote count">${tt('strings.no_new_entries_or_removals_here',{add:esc(refused.add),remove:esc(refused.remove)})}</div>` : ''}
    ${f.stale && r.tagged ? `<div class="strnote w-warn">${tt('strings.was_edited_after_this_archive_was',{txt:esc(f.txt)})}</div>` : ''}
    <table class="strtab">
      <tr><th>${r.tagged ? tt('strings.tag') : tt('strings.row')}</th><th>${tt('strings.text')}</th><th></th></tr>
      ${s.adds.map(strAddHtml).join('')}
      ${r.rows.map(strRowHtml).join('') || `<tr><td colspan="3" class="count">${tt('strings.no_entry_matches')}</td></tr>`}
    </table>
    ${more > 0 ? `<div class="strmore"><button onclick="strMore()">${tt('strings.show_more',{x:Math.min(more, STR_PAGE)})}</button>
      <span class="count">${tt('strings.not_shown_narrow_the_search_above',{more})}</span></div>` : ''}`;
}

function strRowHtml(row){
  const s = state.str;
  const edited = s.edits[row.id] !== undefined, gone = !!s.removes[row.id];
  const value = edited ? s.edits[row.id] : row.value;
  return `<tr class="${edited?'edited':''}${gone?' removed':''}">
    <td class="k"><code>${esc(row.tag || ('#' + row.pos))}</code></td>
    <td><textarea rows="${Math.min(6, 1 + (value.match(/\n/g)||[]).length)}"
      data-row="${esc(row.id)}" ${gone ? 'disabled' : ''}
      oninput="strEdit('${q1(esc(row.id))}',this.value)">${esc(value)}</textarea></td>
    <td class="s">${s.rows.tagged
      ? `<button title="${gone ? tt('strings.keep_this_entry') : tt('strings.remove_this_entry_from_the_archive')}"
           onclick="strToggleRemove('${q1(esc(row.id))}')">${gone ? '↺' : '✕'}</button>` : ''}
      ${edited && !gone
      ? `<button title="${ttA('strings.put_this_entry_back_to_what')}"
           onclick="strRevert('${q1(esc(row.id))}')">↺</button>` : ''}
      ${s.rows.tagged
      ? `<button title="${ttA('strings.show_this_entry_as_the_txt')}"
           onclick="strCode('${q1(esc(row.id))}')">&lt;/&gt;</button>` : ''}</td>
  </tr>`;
}

/* ---- new rows and removed ones (48) ---- */
function strPending(){
  const s = state.str;
  return Object.keys(s.edits).filter(id => !s.removes[id]).length
    + s.adds.length + Object.keys(s.removes).length;
}
function strAddHtml(a, i){
  const bad = strTagProblem(a.tag, i);
  return `<tr class="edited added">
    <td class="k"><input type="text" spellcheck="false" placeholder="NEW_TAG" value="${esc(a.tag)}"
      class="${bad ? 'bad' : ''}" title="${esc(bad || tt('strings.the_tag_the_game_asks_for'))}"
      oninput="strAddSet(${i},'tag',this.value,this)"></td>
    <td><textarea rows="2" placeholder="The text" oninput="strAddSet(${i},'value',this.value,this)">${esc(a.value)}</textarea></td>
    <td class="s"><button title="${ttA('strings.drop_this_new_entry')}" onclick="strAddDrop(${i})">✕</button></td>
  </tr>`;
}
/* the page only paints a box red early; the plan is what refuses */
function strTagProblem(tag, i){
  const t = (tag || '').trim();
  if(!t) return tt('strings.a_new_entry_needs_a_tag');
  if(/[\s{}]/.test(t)) return tt('strings.a_tag_has_no_spaces_or');
  const s = state.str;
  if(s.adds.some((a, j) => j !== i && a.tag.trim() === t)) return tt('strings.this_tag_is_new_twice');
  if((s.rows.rows || []).some(r => r.tag === t && !s.removes[r.id]))
    return tt('strings.this_archive_already_has_an_entry_tagged',{tag:t});
  return '';
}
function strAddRow(){
  state.str.adds.unshift({tag:'', value:''});
  const el = document.getElementById('strMain');
  if(el){ el.innerHTML = strRowsHtml(); const box = el.querySelector('tr.added input'); if(box) box.focus(); }
}
function strAddSet(i, key, value, el){
  const a = state.str.adds[i]; if(!a) return;
  a[key] = value;
  if(key === 'tag'){ const bad = strTagProblem(value, i);
    el.classList.toggle('bad', !!bad); el.title = bad || tt('strings.the_tag_the_game_asks_for'); }
  strPaintBar();
}
function strAddDrop(i){
  state.str.adds.splice(i, 1);
  const el = document.getElementById('strMain'); if(el) el.innerHTML = strRowsHtml();
}
function strToggleRemove(id){
  const s = state.str;
  if(s.removes[id]) delete s.removes[id]; else s.removes[id] = true;
  const el = document.getElementById('strMain'); if(el) el.innerHTML = strRowsHtml();
}

function strEdit(id, value){
  const s = state.str, row = (s.rows.rows || []).find(r => r.id === id);
  if(!row) return;
  if(value === row.value) delete s.edits[id]; else s.edits[id] = value;
  // The bar and this one row are repainted, never the table: redrawing it would
  // take the caret out of the box being typed in.
  const box = document.querySelector(`.strtab textarea[data-row="${cssq(id)}"]`);
  if(box) box.closest('tr').classList.toggle('edited', s.edits[id] !== undefined);
  strPaintBar();
}
function strRevert(id){
  delete state.str.edits[id];
  const el = document.getElementById('strMain');
  if(el) el.innerHTML = strRowsHtml();
}
function strPaintBar(){
  const n = strPending();
  const b = document.querySelector('.strbar button.primary');
  if(b){ b.disabled = !n; b.textContent = ttN('strings.save_changes',n); }
}
// One debounce for the header search, since every keystroke is a round trip
let strSearchT = null;
function strSearch(){
  if(!state.str || !state.str.file) return;
  clearTimeout(strSearchT);
  strSearchT = setTimeout(() => { state.str.offset = 0; strFetchRows(); }, 250);
}
function strMore(){
  const s = state.str;
  s.offset = (s.offset || 0) + STR_PAGE;
  strFetchRows();
}

/* ---- one entry as the .txt writes it ----
   The archive is binary, but an entry is exactly the `{tag}text` line of the
   .txt beside it, so that is what the Code View shows - the format modders
   already write, not a decoded stand-in. */
function strCode(id){
  const s = state.str;
  const row = (s.rows.rows || []).find(r => r.id === id);
  if(!row) return;
  const value = s.edits[id] !== undefined ? s.edits[id] : row.value;
  const cv = cvCreate({
    kind:'strings', mod:s.mod, id:`${s.file}|${row.id}`,
    where:s.rows.name,
    edits:() => ({tag: row.tag, value: strCvValue(cv)}),
    adopt:c => { if(c.detail) strCvSet(row, c.detail.value); },
  });
  cv._value = value;
  strCodeModal(cv, row);
}
const strCvValue = cv => cv._value;
function strCvSet(row, value){
  const s = state.str;
  if(value === row.value) delete s.edits[row.id]; else s.edits[row.id] = value;
  const box = document.getElementById('strCvBox');
  if(box && box.value !== value) box.value = value;
}

async function strCodeModal(cv, row){
  const m = document.getElementById('modal');
  m.className = 'modal wide';
  m.innerHTML = `<div class="ehead"><div>
      <div class="nm">${esc(row.tag)}</div>
      <div class="count">${esc(state.str.rows.name)}</div></div></div>
    <div style="padding:12px">
      <div class="lbl">${tt('strings.text')}</div>
      <textarea id="strCvBox" rows="5" style="width:100%"
        oninput="strCvType(cvOf('${cv.uid}'),this.value)">${esc(cv._value)}</textarea>
      <div id="strCvPane" style="margin-top:10px"></div>
    </div>
    <div style="padding:0 12px 12px;text-align:right">
      <button onclick="strCloseCode(cvOf('${cv.uid}'))">${tt('common.close')}</button></div>`;
  overlay.classList.add('open');
  await cvLoad(cv);
  const pane = document.getElementById('strCvPane');
  if(pane){ pane.innerHTML = cvHtml(cv); cvWire(cv); }
  // cvLoad shows what is ON DISK. If this row already has an unsaved edit, the
  // pane would be showing a different string from the box right above it - so
  // re-render it from the pending value, through the same writer a save uses.
  if(cv.detail && cv._value !== cv.detail.value){ await cvRender(cv); cvRedrawLines(cv); }
}
function strCvType(cv, value){
  if(!cv) return;
  cv._value = value;
  const row = (state.str.rows.rows || []).find(r => `${state.str.file}|${r.id}` === cv.id);
  if(row) strCvSet(row, value);
  cvFromGui(cv);
}
function strCloseCode(cv){
  cvDrop(cv);
  closeModal();
  const el = document.getElementById('strMain');
  if(el) el.innerHTML = strRowsHtml();
}

/* ---- writing ---- */
async function strSave(){
  const s = state.str;
  const edits = Object.keys(s.edits).filter(id => !s.removes[id])
    .map(id => ({id, value: s.edits[id]}));
  const adds = s.adds.map(a => ({tag:a.tag.trim(), value:a.value}));
  const removes = Object.keys(s.removes);
  const bad = s.adds.map((a, i) => strTagProblem(a.tag, i)).find(Boolean);
  if(bad){ toast('✗ ' + bad, 5000); return; }
  const n = edits.length + adds.length + removes.length;
  if(!n) return;
  await strApply({mod:s.mod, file:s.file, edits, adds, removes},
                 tt('strings.change_s_to',{x:n,x2:s.file.split('/').pop()}));
}
async function strRebuild(){
  const s = state.str;
  const f = s.files.find(x => x.rel === s.file) || {};
  if(!confirm(tt('strings.compile_over_the_archive_is_backed_and_log',{txt:f.txt,name:f.name}))) return;
  await strApply({mod:s.mod, file:s.file, action:'rebuild'}, `${f.name} from ${f.txt}`);
}

async function strApply(body, what){
  const s = state.str;
  s.busy = true;
  const plan = await api.post('/api/strings/plan', body);
  if(plan.error){ toast('✗ ' + plan.error, 5000); s.busy = false; return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 12);
  if(!confirm(tt('strings.write_changes_entries_backed_up',{what, changes:lines.join('\n') || tt('common.no_visible_change'),
      more:(p.changes || []).length > 12 ? tt('strings.and_more',{changes:p.changes.length - 12}) : '',
      before:p.before, after:p.after,
      warnings:(p.warnings || []).filter(w => w !== 'nothing to change').length
        ? '\n⚠ ' + p.warnings.filter(w => w !== 'nothing to change').join('\n⚠ ') : ''}))) { s.busy = false; return; }
  const res = await api.post('/api/strings/apply', body);
  s.busy = false;
  if(res.error){ toast('✗ ' + res.error, 5000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  s.reopen = s.file;             // back to the archive that was saved, not the list
  await loadStrings();
}
