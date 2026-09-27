/* soundbanks.js - Sound banks: the six export_descr_sounds_* files beside the voice bank

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= SOUND BANKS (47a) =======================
   Soldier voices, strat map voices, battle events, pre-battle speech, advice
   and narration. Each is a tree of header lines (accent, class or type, vocal,
   notification, element ...) over event blocks, and each event is a folder
   line and the samples under it. The list on the left is that tree; the pane
   on the right is one block: its events to edit, and the block itself to
   duplicate, rename or remove.

   47b: the same screen draws the sound scripts (descr_sounds_*.txt) in the
   `soundscripts` mode. A script's blocks are banks, selectors (unit, hit,
   season, terrain ...) and named events, and it has lines of its own besides
   events: DEFAULT: lines and settings, edited in the pane as `items`. What a
   block may do - copy, rename, remove - is the server's to say, per block.

   THE PAGE NEVER PARSES A GAME FILE. Everything here is /api/soundbanks or
   /api/soundscripts, and every op names its line by number AND by text, so a
   save against a file that changed since it was read is refused rather than
   landed on the wrong block. */

/* which of the two this screen is drawing: the mode says */
function sbkScripts(){ return state.mode === 'soundscripts'; }
function sbkApi(){ return sbkScripts() ? '/api/soundscripts' : '/api/soundbanks'; }

/* the strip over both sound screens: the voice bank keys on units, the six
   banks on accents and events, so they are two screens and one subject */
function soundTabsHtml(note){
  const on = id => state.mode === id ? ' on' : '';
  return `<div class="mftabs">
    <button class="mftab${on('sounds')}" onclick="setAppMode('sounds')">${tt('soundbanks.unit_voices')}</button>
    <button class="mftab${on('soundbanks')}" onclick="setAppMode('soundbanks')">${tt('soundbanks.sound_banks')}</button>
    <button class="mftab${on('soundscripts')}" onclick="setAppMode('soundscripts')">${tt('soundbanks.sound_scripts')}</button>
    ${note ? `<span class="count" style="margin-left:auto">${esc(note)}</span>` : ''}</div>`;
}

async function loadSoundBanks(file){
  const mod = state.src, mode = state.mode, scope = sbkScripts() ? 'scripts' : 'banks';
  const k = state.sbk && state.sbk.mod === mod && state.sbk.scope === scope ? state.sbk : null;
  file = file || (k && k.file) || (scope === 'scripts' ? 'units' : 'soldier_voice');
  main.innerHTML = soundTabsHtml() + `<div class="empty">${tt('common.reading')} ` + esc(mod) + tt('soundbanks.s_sound')
    + (scope === 'scripts' ? 'scripts' : 'banks') + '…</div>';
  let r;
  try{ r = await api.get(sbkApi() + '?mod=' + enc(mod) + '&file=' + enc(file)); }
  catch(e){ if(stale(mode, mod)) return;
    main.innerHTML = soundTabsHtml() + `<div class="empty">${tt('soundbanks.couldnt_read_the_sound_bank')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadSoundBanks()">${tt('common.retry')}</button></div>`; return; }
  if(stale(mode, mod)) return;
  const keepPath = k && k.file === file ? sbkPathOf(k.d, k.sel) : '';
  const open = k && k.file === file ? k.open : new Set();
  state.sbk = {mod, scope, file, d:r, sel:-1, open, w:{}, busy:false};
  if(keepPath){
    const i = r.nodes.findIndex((n, j) => sbkPathOf(r, j) === keepPath);
    state.sbk.sel = i;
  }
  renderSoundBanks();
}

function renderSoundBanks(){
  const k = state.sbk;
  if(!k || k.mod !== state.src || k.scope !== (sbkScripts() ? 'scripts' : 'banks')){
    loadSoundBanks(); return; }
  const d = k.d;
  const files = d.files.map(f => [f.id, f.label + (f.exists === false ? ' (none)' : '')]);
  // 32 scripts do not fit a strip: they are a picker, grouped as the server groups them
  const pick = sbkScripts() ? `<div class="mftabs rectabs"><select onchange="sbkFile(this.value)">${
      [...new Set(d.files.map(f => f.group))].map(g => `<optgroup label="${esc(g)}">${
        d.files.filter(f => f.group === g).map(f => `<option value="${esc(f.id)}"${f.id === k.file ? ' selected' : ''}>${
          esc(f.label)}${f.read_only ? tt('soundbanks.shown_not_edited') : ''}</option>`).join('')}</optgroup>`).join('')}
    </select><span class="count">${tt('soundbanks.scripts',{files_n:d.files.length})}</span></div>`
    : recTabsHtml(files, k.file, 'sbkFile');
  const head = soundTabsHtml('data/' + d.rel) + pick;
  if(!d.exists){
    main.innerHTML = head + `<div class="empty">${tt('soundbanks.has_no_data_the_game_uses',{src:esc(state.src),rel:esc(d.rel),label:esc(d.label.toLowerCase())})}</div>`;
    count.textContent = ''; return;
  }
  count.textContent = tt('soundbanks.blocks_events',{nodes_n:d.nodes.length,events:d.events});
  main.innerHTML = head + `<div class="trwrap">
    <div class="trlist" id="sbkList">${sbkListHtml()}</div>
    <div class="trmain" id="sbkMain">${sbkMainHtml()}</div>
  </div>`;
}

function sbkFile(id){
  if(!sbkLeaveOk()) return;
  if(state.sbk) state.sbk.sel = -1;
  loadSoundBanks(id);
}

/* "accent Arabic / type Admiral / vocal Attacking" - how a block is found
   again after a save moved every line under it */
function sbkPathOf(d, i){
  const out = [];
  for(let n = d.nodes[i]; n; n = n.parent === null ? null : d.nodes[n.parent]) out.unshift(n.label);
  return out.join(' / ');
}

function sbkChildren(i){
  return state.sbk.d.nodes.map((n, j) => [n, j]).filter(([n]) => n.parent === i);
}

function sbkSamples(n){
  return n.events.reduce((a, e) => a + e.lines.filter(l => !/^folder\s/i.test(l)).length, 0);
}

const SBK_CAP = 400;
function sbkListHtml(){
  const k = state.sbk, d = k.d, q = search.value.trim().toLowerCase();
  const row = (n, i, depth, path) => {
    const kids = d.nodes.some(x => x.parent === i);
    const isOpen = k.open.has(i);
    const items = (n.items || []).length;
    const sub = n.kind === 'file' ? tt('soundbanks.line_default_settings_sources',{items,items2:items === 1 ? '' : 's'})
      : kids ? `${sbkChildren(i).length} inside`
      : tt('soundbanks.event_sample',{events_n:n.events.length,events:n.events.length === 1 ? '' : 's',sbkSamples:sbkSamples(n),sbkSamples2:sbkSamples(n) === 1 ? '' : 's'})
        + (items ? tt('soundbanks.setting',{items,items2:items === 1 ? '' : 's'}) : '');
    const dirty = n.events.some(e => k.w[e.at]) || (n.items || []).some(it => k.w['i' + it.at]);
    return `<button class="trrow sbkrow${k.sel === i ? ' on' : ''}" style="margin-left:${depth * 14}px"
        onclick="sbkPick(${i})">
      <div class="nm">${kids ? `<span class="sbktw" onclick="event.stopPropagation();sbkFold(${i})">${isOpen ? '▾' : '▸'}</span>` : ''}${esc(n.label)}${dirty ? ' <b>•</b>' : ''}</div>
      <div class="sub">${path ? esc(path) + ' · ' : ''}${sub}</div></button>`;
  };
  if(q){
    const hits = [];
    d.nodes.forEach((n, i) => { if(hits.length < SBK_CAP && (n.label.toLowerCase().includes(q)
      || n.events.some(e => e.lines.some(l => l.toLowerCase().includes(q))))) hits.push(i); });
    return hits.map(i => {
      const p = sbkPathOf(d, i).split(' / '); p.pop();
      return row(d.nodes[i], i, 0, p.join(' / '));
    }).join('') || `<div class="count" style="padding:8px">${tt('common.nothing_matches')}</div>`;
  }
  const out = [];
  const walk = (parent, depth) => {
    for(const [n, i] of sbkChildren(parent)){
      if(out.length >= SBK_CAP) return;
      out.push(row(n, i, depth, ''));
      if(k.open.has(i)) walk(i, depth + 1);
    }
  };
  walk(null, 0);
  return out.join('') + (out.length >= SBK_CAP ? `<div class="count" style="padding:8px">${tt('soundbanks.the_first_rows_fold_a_block',{SBK_CAP})}</div>` : '');
}

function sbkFold(i){
  const o = state.sbk.open;
  if(o.has(i)) o.delete(i); else o.add(i);
  document.getElementById('sbkList').innerHTML = sbkListHtml();
}

function sbkPick(i){
  const k = state.sbk;
  if(k.d.nodes.some(x => x.parent === i) && k.sel === i) return sbkFold(i);
  k.sel = i;
  if(k.d.nodes.some(x => x.parent === i)) k.open.add(i);
  // opening a block opens the blocks above it, so the list shows where it is
  for(let n = k.d.nodes[i]; n && n.parent !== null; n = k.d.nodes[n.parent]) k.open.add(n.parent);
  document.getElementById('sbkList').innerHTML = sbkListHtml();
  document.getElementById('sbkMain').innerHTML = sbkMainHtml();
}

function sbkMainHtml(){
  const k = state.sbk, d = k.d;
  const n = d.nodes[k.sel];
  const nw = Object.keys(k.w).length, ro = !!d.read_only;
  const bar = `<div class="cdbhead">
    <div><b>${esc(d.label)}</b> <span class="count">${tt('soundbanks.lines_read_when_the_game_starts',{x:d.bank ? tt('soundbanks.bank') + esc(d.bank) + ' · ' : '',line_count:d.line_count})}</span></div>
    <span style="flex:1"></span>
    <button onclick="rtOpen('${q1(esc(d.rel))}'${n && n.line > 0 ? ', ' + n.line : ''})" title="${ttA('soundbanks.the_whole_file_in_the_raw')}">${tt('soundbanks.raw_text')}</button>
    ${ro ? '' : `<button onclick="sbkRevert()" ${nw ? '' : 'disabled'}>${tt('common.revert')}</button>
    <button class="primary" onclick="sbkSave()" ${nw ? '' : 'disabled'}>${tt('soundbanks.save_edit',{nw:nw || '',nw2:nw === 1 ? '' : 's'})}</button>`}
  </div>`;
  const about = `<div class="trnote"><div>${esc(d.about)}</div>
    <div class="count">${esc(d.packed)}</div>
    ${d.vocab ? sbkVocabHtml(d.vocab) : ''}
    ${d.warnings.length ? `<div class="count w-warn">${d.warnings.slice(0, 5).map(esc).join('<br>')}</div>` : ''}</div>`;
  if(!n) return bar + about + `<div class="empty" style="padding:18px">${tt('soundbanks.pick_a_block_on_the_left')}</div>`;
  const kids = sbkChildren(k.sel);
  const path = sbkPathOf(d, k.sel);
  // a bank says nothing and can do everything; a script's block says which
  const can = x => !ro && n.kind !== 'file' && n[x] !== false;
  const sel = n.kind === 'selector';
  const acts = n.kind === 'file' ? '' : `<div class="sbkacts">
    ${tt('soundbanks.line_line',{can:can('can_copy') ? `<button onclick="sbkBlock('duplicate')" title="${ttA('soundbanks.a_copy_of_this_block_straight')}">${tt('soundbanks.duplicate_as')}</button>` : '',can2:can('can_rename') ? `<button onclick="sbkBlock('rename')" title="${sel ? tt('soundbanks.what_this_selector_matches') : d.named || n.kind === 'named' ? tt('soundbanks.the_name_the_engine_or_a') : tt('soundbanks.change_this_block_name')}">${sel ? tt('soundbanks.change_values') : tt('soundbanks.rename')}</button>` : '',can3:can('can_remove') ? `<button class="danger" onclick="sbkBlock('remove')">${tt('common.remove')}</button>` : '',line:n.line,lines:n.lines,lines2:n.lines === 1 ? '' : 's',x:sel && !ro ? tt('soundbanks.a_selector_is_changed_in_place') : ''})}</div>`;
  const inside = kids.length ? `<div class="sbkkids"><div class="count">${tt('soundbanks.inside_it')}</div>
    ${kids.map(([c, j]) => `<button class="sbkkid" onclick="sbkPick(${j})">${esc(c.label)}
      <span class="count">${d.nodes.some(x => x.parent === j) ? sbkChildren(j).length + ' inside'
        : c.events.length + ' event' + (c.events.length === 1 ? '' : 's')}</span></button>`).join('')}</div>` : '';
  const evs = n.events.map((e, x) => sbkEventHtml(e, x, n.events.length)).join('');
  const items = (n.items || []).map(sbkItemHtml).join('');
  return bar + (n.kind === 'file' ? about : '') + `<div class="sbkpath">${esc(path)}</div>` + acts
    + items + evs + inside
    + (kids.length || n.events.length || items ? '' : `<div class="count">${tt('soundbanks.nothing_inside_this_block')}</div>`);
}

function sbkEventHtml(e, x, of){
  const k = state.sbk, w = k.w[e.at] || {};
  const attrs = w.attrs !== undefined ? w.attrs : e.attrs;
  const lines = w.lines !== undefined ? w.lines : e.lines.join('\n');
  const named = k.d.named, ro = !!k.d.read_only;
  const nS = lines.split('\n').filter(l => l.trim() && !/^folder\s/i.test(l.trim())).length;
  return `<div class="sbkev${k.w[e.at] ? ' on' : ''}">
    <div class="sbkevhead">${tt('soundbanks.event_line_sample',{x:e.name ? ' ' + esc(e.name) : '',of:of > 1 ? ` ${x + 1} of ${of}` : '',line:e.line,nS,nS2:nS === 1 ? '' : 's'})}</div>
    ${named ? '' : `<label class="sbkattr"><span class="count">${tt('soundbanks.attributes')}</span>
      <input type="text" spellcheck="false" value="${esc(attrs)}" ${ro ? 'disabled' : ''}
        placeholder="${ttA('soundbanks.none_e_g_priority_120_volume')}"
        oninput="sbkSet(${e.at}, 'attrs', this.value)"></label>`}
    <textarea class="sbklines" spellcheck="false" ${ro ? 'disabled' : ''} rows="${Math.min(18, Math.max(3, lines.split('\n').length + 1))}"
      oninput="sbkSet(${e.at}, 'lines', this.value)">${esc(lines)}</textarea>
    <div class="count">${tt('soundbanks.one_line_each_a_folder_data')}</div>
  </div>`;
}

/* 47b: a script's one-line things - DEFAULT:, a setting, a source - in the
   pane of the block that holds them. A source names the export bank that fills
   the section, which is 47a's screen, so it is shown and not typed over. */
function sbkItemHtml(it){
  const k = state.sbk, w = k.w['i' + it.at];
  const v = w ? w.value : it.value, ro = !!k.d.read_only || it.kind === 'source';
  const what = it.kind === 'default' ? tt('soundbanks.what_every_event_after_it_starts')
    : it.kind === 'setting' ? tt('soundbanks.a_number') : tt('soundbanks.the_export_bank_that_fills_this');
  return `<div class="sbkitem${w ? ' on' : ''}">
    <code class="cdbname" title="${ttA('soundbanks.line',{line:it.line})}">${esc(it.key)}</code>
    <input type="text" spellcheck="false" value="${esc(v)}" ${ro ? 'disabled' : ''}
      oninput="sbkSetItem(${it.at}, this.value, this)">
    <span class="count">${tt('soundbanks.line_2',{line:it.line,what})}</span></div>`;
}

function sbkSetItem(at, value, el){
  const k = state.sbk;
  const it = k.d.nodes.flatMap(n => n.items || []).find(x => x.at === at);
  if(!it) return;
  const same = value.trim().split(/\s+/).join(' ') === it.value;
  if(same) delete k.w['i' + at]; else k.w['i' + at] = {value};
  el.closest('.sbkitem').classList.toggle('on', !same);
  sbkPaintSave();
}

/* what the mod's own scripts write, so a box has something to go on */
function sbkVocabHtml(v){
  const r = v.ranges || {};
  return `<details class="sbkvocab"><summary class="count">${tt('soundbanks.attributes_these_scripts_write')}</summary>
    <div class="count">${tt('soundbanks.numbers',{x:v.num.map(x => `<code>${esc(x)}</code>${r[x] ? ` ${r[x][0]} to ${r[x][1]}` : ''}`).join(' · ')})}</div>
    <div class="count">${tt('soundbanks.on_their_own_pref_and_one',{flags:v.flags.map(x => `<code>${esc(x)}</code>`).join(' '),prefs:(v.prefs || []).map(x => `<code>${esc(x)}</code>`).join(' ')})}</div>
    <div class="count">${tt('soundbanks.the_ranges_are_what_this_mods')}</div></details>`;
}

function sbkPaintSave(){
  const nw = Object.keys(state.sbk.w).length, box = document.getElementById('sbkMain');
  const btns = box.querySelectorAll('.cdbhead button');
  if(btns.length < 3) return;
  const save = btns[btns.length - 1], rev = btns[btns.length - 2];
  save.disabled = rev.disabled = !nw;
  save.textContent = tt('soundbanks.save_edit',{nw:nw || '',nw2:nw === 1 ? '' : 's'});
}

/* typing does not redraw - that would take the caret out of the box */
function sbkSet(at, key, value){
  const k = state.sbk;
  const ev = k.d.nodes[k.sel].events.find(x => x.at === at);
  if(!ev) return;
  const w = k.w[at] || {attrs:ev.attrs, lines:ev.lines.join('\n')};
  w[key] = value;
  const same = w.attrs.trim() === ev.attrs
    && w.lines.split('\n').map(l => l.trim()).filter(Boolean).join('\n') === ev.lines.join('\n');
  if(same) delete k.w[at]; else k.w[at] = w;
  const box = document.getElementById('sbkMain');
  box.querySelectorAll('.sbkev').forEach(el => {
    const t = el.querySelector('textarea');
    if(t && t.getAttribute('oninput').includes('(' + at + ',')) el.classList.toggle('on', !same);
  });
  sbkPaintSave();
}

function sbkRevert(){ state.sbk.w = {}; renderSoundBanks(); }

function sbkLeaveOk(){
  const k = state.sbk;
  return !k || !Object.keys(k.w).length
    || confirm(tt('soundbanks.leave_without_saving_your_edits_are'));
}

function sbkEventOps(){
  const k = state.sbk, ops = [];
  for(const n of k.d.nodes){
    for(const e of n.events){
      const w = k.w[e.at]; if(!w) continue;
      ops.push({op:'event', at:e.at, head:e.head_text, attrs:w.attrs,
                lines:w.lines.split('\n').map(l => l.trim()).filter(Boolean)});
    }
    for(const it of n.items || []){
      const w = k.w['i' + it.at]; if(!w) continue;
      ops.push({op:it.kind, at:it.at, head:it.head_text, value:w.value});
    }
  }
  return ops;
}

async function sbkSave(){ await sbkRun(sbkEventOps()); }

async function sbkBlock(kind){
  const k = state.sbk, n = k.d.nodes[k.sel];
  if(!n) return;
  if(Object.keys(k.w).length){ toast(tt('soundbanks.save_or_revert_the_edits_first'), 5000); return; }
  const op = {op:kind, at:n.head, head:n.head_text};
  if(kind !== 'remove'){
    const v = prompt(kind === 'duplicate'
      ? tt('soundbanks.a_copy_of_straight_after_it',{label:n.label,kw:n.kw})
      : n.kind === 'selector' ? tt('soundbanks.what_matches_as_the_file_writes',{kw:n.kw})
      : tt('soundbanks.rename_to',{label:n.label}), n.value);
    if(v === null) return;
    op.value = v.trim();
  }
  await sbkRun([op]);
}

async function sbkRun(ops){
  const k = state.sbk;
  if(k.busy || !ops.length) return;
  const body = {mod:state.src, file:k.file, ops};
  k.busy = true;
  let r;
  try{ r = await api.post(sbkApi() + '/plan', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ k.busy = false; }
  if(r.error){ toast('✗ ' + r.error, 9000); return; }
  const p = r.plan || {};
  if(!p.ok){ toast(tt('soundbanks.nothing_to_change')); return; }
  if(!confirm(tt('soundbanks.write_change_s_to',{changes_n:p.changes.length,rel:k.d.rel})
    + p.changes.slice(0, 14).join('\n')
    + (p.changes.length > 14 ? tt('soundbanks.and_more',{changes:p.changes.length - 14}) : '')
    + (p.warnings.length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + tt('common.backed_up_first_and_log_can'))) return;
  k.busy = true;
  let res;
  try{ res = await api.post(sbkApi() + '/apply', body); }
  catch(e){ toast('✗ ' + errText(e), 6000); return; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 9000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  const dup = ops.find(o => o.op === 'duplicate' || o.op === 'rename');
  if(dup){
    // land on the block that was made or renamed, not the one it came from
    const n = k.d.nodes[k.sel];
    const parts = sbkPathOf(k.d, k.sel).split(' / ');
    parts[parts.length - 1] = (n.vnv ? 'VnV ' : '') + n.kw + ' ' + dup.value;
    k.d.nodes[k.sel] = Object.assign({}, n, {label:parts[parts.length - 1]});
  }
  k.w = {};
  await loadSoundBanks(k.file);
}
