/* changes.js - My changes: your edits to a mod, recorded and ported (Phase 52)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   NOTHING HERE HAS TO BE SWITCHED ON. Every save the toolkit makes to a mod
   under <Medieval II>/mods is recorded by the server as it happens (see
   unittransfer/changesets.py): the file's original the first time, your
   version every time. This screen reads that record back, record by record,
   and does the two things it is for:

     * when an update has overwritten the mod, PORT your changes back onto it,
       as a checklist that says what each change meets in the new version;
     * EXPORT the set as one file, and IMPORT one, to carry it to another
       machine or another copy of the mod;
     * SWITCH between versions of the mod in place (Phase 53): a mod can carry
       several sets, one is on at a time, and switching takes one set's
       records out and puts another's in as a single job with one Undo.

   The page decides nothing. The plan is the server's, the apply re-plans on
   the server and names records by file and key, and the write is one backup
   and one log entry, so 🕑 Log's Undo takes a port back.

   Every name here starts `chg`; there was none in the tree before.
   ===================================================================== */

const CHG_OUTCOME = {
  clean: [tt('changes.applies'), 'w-good', tt('changes.the_new_version_left_this_as')],
  merged: [tt('changes.merged'), 'w-good', tt('changes.both_sides_changed_this_in_different')],
  already: [tt('changes.already_there'), '', tt('changes.the_new_version_already_says_what')],
  conflict: [tt('changes.conflict'), 'w-warn', tt('changes.both_sides_changed_the_same_lines')],
  gone: [tt('changes.gone_upstream'), 'w-bad', tt('changes.you_changed_this_and_the_new')],
};
const CHG_KIND = {added: '＋', removed: '−', edited: '✎'};
const CHG_DISK = {
  same: '',
  changed: tt('changes.changed_on_disk_since_your_last'),
  original: tt('changes.back_to_the_original_on_disk'),
  missing: tt('changes.missing_on_disk'),
};

function chgNew(mod){
  return {mod, sum: null, err: '', from: '', target: mod, plan: null,
          picks: new Set(), open: new Set(), busy: false, view: ''};
}

async function loadChanges(){
  const mod = state.src;
  // which set was being looked at survives a reload of the same mod
  const view = (state.chg && state.chg.mod === mod && state.chg.view) || '';
  const k = state.chg = chgNew(mod);
  main.innerHTML = `<div class="empty">${tt('changes.reading_what_you_have_changed_in')} ` + esc(mod) + '…</div>';
  let r;
  try{ r = await api.get('/api/changes?mod=' + enc(mod) + (view ? '&set=' + enc(view) : '')); }
  catch(e){ r = {error: errText(e)}; }
  if(stale('changes', mod) || state.chg !== k) return;
  k.view = view;
  if(r.error) k.err = r.error;
  else{ k.sum = r; k.from = r.set || ((r.sets || [])[0] || {}).name || ''; }
  chgPaint();
}

function renderChanges(){
  const k = state.chg;
  if(!k || k.mod !== state.src){ loadChanges(); return; }
  chgPaint();
}

const chgPickKey = it => it.rel + '\u0000' + it.key;

function chgPaint(){
  const k = state.chg;
  if(k.err){
    main.innerHTML = `<div class="empty">${tt('changes.couldnt_read_the_change_set')}<br>
      <span class="count">${esc(k.err)}</span><br><br>
      <button class="primary" onclick="loadChanges()">${tt('common.retry')}</button></div>`;
    return;
  }
  const s = k.sum;
  main.innerHTML = `<div class="chgwrap">
    ${chgHeadHtml(s)}
    ${typeof pzHtml === 'function' ? pzHtml() : ''}
    ${chgVersionsHtml(s)}
    ${chgFilesHtml(s)}
    ${chgPortHtml(s)}
  </div>`;
}

function chgHeadHtml(s){
  const moved = (s.files || []).filter(f => f.disk && f.disk !== 'same');
  const others = (s.sets || []).filter(x => x.name !== s.set);
  return `<div class="bsec"><h4>${tt('changes.your_changes_to',{mod:esc(s.mod),x:s.set ? `<span class="count">${tt('changes.recorded_since',{set:esc(s.set),on:s.on ? tt('changes.on') : tt('changes.off'),created:esc(s.created || '')})}</span>` : ''})}</h4>
    <div class="trnote">${tt('changes.every_save_this_toolkit_makes_to')}</div>
    ${moved.length ? `<div class="chgwarn">${ttN('changes.files_changed_under_you_since_your',moved.length)}</div>` : ''}
    <div class="chgacts">
      ${s.set ? tt('changes.export_export_changed_files',{x:enc(s.set),x2:enc(s.set)}) : ''}
      <label class="btn" title="${ttA('changes.a_change_set_exported_somewhere_else')}">${tt('changes.import')}
        <input type="file" accept=".m2changes,.zip" style="display:none" onchange="chgImport(this)"></label>
      <label class="btn" title="${ttA('changes.any_zip_laid_out_under_data')}">${tt('changes.load_a_zip_of_files')}
        <input type="file" accept=".zip" style="display:none" onchange="pzChosen(this)"></label>
      ${s.set ? `<button onclick="chgAdopt()" title="${ttA('changes.for_edits_you_made_by_hand')}">${tt('changes.take_the_files_on_disk_as')}</button>
        <button class="danger" onclick="chgForget()" title="${ttA('changes.stop_recording_against_this_original_the')}">${tt('changes.forget_this_record')}</button>` : ''}
    </div>
    ${others.length ? `<div class="count" style="margin-top:6px">${tt('changes.other_change_sets',{x:others.map(x => esc(x.name) + (x.imported ? ' (imported)' : '')).join(', ')})}</div>` : ''}
  </div>`;
}

/* ---- versions of the mod (Phase 53) ----
   Each set is a version: the mod as it shipped, plus that set's records. One is
   on, meaning its records are what the files say; the rest wait, holding both
   their copies. Turning the last one off leaves the mod as it shipped, and the
   next save starts a fresh set - which is how a second version is made. */
function chgVersionsHtml(s){
  const vs = s.versions || [];
  if(!vs.length) return '';
  return `<div class="bsec"><h4>${tt('changes.versions_of_this_mod')} <span class="n">${vs.length}</span></h4>
    <div class="trnote">${tt('changes.one_is_on_at_a_time')}</div>
    ${vs.map(v => `<div class="chgver${v.active ? ' on' : ''}">
      <span class="chgdot">${v.active ? '●' : '○'}</span>
      <b>${esc(v.name)}</b>
      ${ttN('changes.files_changed_since',v.files,{imported:v.imported ? tt('changes.imported') : '',created:esc(v.created || '?'),x:v.name !== s.set ? `<button class="x" onclick="chgView('${q1(esc(v.name))}')">${tt('changes.view')}</button>` : ''})}
      <button class="x" onclick="chgRename('${q1(esc(v.name))}')">${tt('changes.rename')}</button>
      ${v.active
        ? `<button class="x" onclick="chgSwitch(null)" title="${ttA('changes.put_the_original_records_back')}">${tt('changes.turn_off')}</button>`
        : `<button class="x primary" onclick="chgSwitch('${q1(esc(v.name))}')">${tt('changes.switch_to_this')}</button>`}
    </div>`).join('')}
    ${!vs.some(v => v.active) ? `<div class="count" style="margin-top:6px">${tt('changes.every_version_is_off_the_mod')}</div>` : ''}
  </div>`;
}

/* The edits a switch would write over. The page is the only side that knows
   about them, so it asks every editor that keeps a working copy. */
function chgUnsaved(){
  const out = [];
  try{ if(state.bld && state.bld.work && bldDirty()) out.push(tt('common.buildings')); }catch(e){}
  try{ if(state.ed && (edDirty() || edCmpDirty() || edRecDirty())) out.push(tt('changes.the_unit_editor')); }catch(e){}
  try{ if(typeof cevDirty === 'function' && cevDirty()) out.push(tt('changes.campaign_events')); }catch(e){}
  try{ if(typeof cftDirty === 'function' && cftDirty()) out.push('forts'); }catch(e){}
  const names = {tr: tt('common.traits'), an: tt('common.ancillaries'), gu: tt('changes.guilds'), fac: tt('common.factions'),
                 mf: tt('changes.minor_files'), cdb: tt('changes.campaign_constants'), str: tt('changes.strings'), snd: tt('changes.unit_sounds')};
  for(const [k, v] of Object.entries(state)){
    if(v && typeof v === 'object' && (v.dirty === true || (v.d && v.d.dirty === true)))
      out.push(names[k] || k);
  }
  return [...new Set(out)];
}

async function chgSwitch(to){
  const k = state.chg;
  const busy = chgUnsaved();
  if(busy.length){
    toast(tt('changes.save_or_drop_the_unsaved_edits_first',{list:busy.join(', ')}), 6000);
    return;
  }
  let r;
  try{ r = await api.post('/api/changes/switchplan', {mod: k.mod, to}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error && !r.switch){ toast(r.error, 5000); return; }
  const sw = r.switch;
  if(sw.blocked && sw.blocked.length){
    alert(tt('changes.this_switch_is_refused_conflicts',{n:sw.blocked.length,
      list:sw.blocked.slice(0, 12).map(b => '  ' + b.set + ': ' + b.rel + ' / ' + b.key + ' (' + b.outcome + ')').join('\n')}));
    return;
  }
  const what = sw.off && sw.on ? tt('changes.take_out_and_put_in',{off:sw.off,on:sw.on})
    : sw.off ? tt('changes.turn_off_putting_the_original_records',{off:sw.off})
    : tt('changes.turn_on',{on:sw.on});
  if(!confirm(tt('changes.what_files_will_be_rewritten',{what,n:sw.files.length}))) return;
  try{ r = await api.post('/api/changes/switch', {mod: k.mod, to}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast(r.error, 5000); return; }
  toast(tt('changes.switched_file_s_rewritten_undo_is',{n:(r.written || []).length}), 4600);
  k.view = '';
  await loadChanges();
}

async function chgRename(name){
  const nn = prompt(tt('changes.a_name_for_this_version_of'), name);
  if(!nn || nn === name) return;
  const r = await api.post('/api/changes/rename', {set: name, name: nn});
  if(r.error){ toast(r.error, 5000); return; }
  if(state.chg.view === name) state.chg.view = r.set;
  await loadChanges();
}

async function chgView(name){
  state.chg.view = name;
  await loadChanges();
}

function chgFilesHtml(s){
  const files = s.files || [];
  if(!s.set) return `<div class="bsec"><div class="empty" style="padding:18px">${tt('changes.nothing_recorded_for_yet_the_first',{mod:esc(s.mod)})}</div></div>`;
  if(!files.length) return `<div class="bsec"><div class="count">${tt('changes.the_record_holds_no_change_every')}</div></div>`;
  return `<div class="bsec"><h4>${ttN('changes.what_you_changed_files',files.length)}</h4>
    ${files.map(f => `<div class="chgfile">
      <div class="chgfhead"><code>${esc(f.rel)}</code>
        <span class="badge">${esc(f.state)}</span>
        <span class="count">${ttN('changes.count_of_what',f.count,{what:esc(f.what)})}</span>
        ${CHG_DISK[f.disk] ? `<span class="w-warn">· ${esc(CHG_DISK[f.disk])}</span>` : ''}</div>
      <div class="chgrecs">${f.records.map(r => `<span class="chgrec ${esc(r.kind)}"
          title="${esc(r.kind)}">${CHG_KIND[r.kind] || ''} ${esc(r.key)}</span>`).join('')}
        ${f.more ? `<span class="count">${tt('changes.more',{more:f.more})}</span>` : ''}</div>
    </div>`).join('')}
  </div>`;
}

function chgPortHtml(s){
  const k = state.chg;
  const setOpts = (s.sets || []).filter(x => x.files);
  if(!setOpts.length) return '';
  const mods = realMods().map(m => m.name);
  const p = k.plan;
  return `<div class="bsec"><h4>${tt('changes.port_changes_onto_a_version_of')}</h4>
    <div class="brow">
      <span class="k">${tt('changes.changes_from')}</span>
      <select onchange="state.chg.from=this.value;state.chg.plan=null;chgPaint()">
        ${setOpts.map(x => `<option value="${esc(x.name)}" ${x.name === k.from ? 'selected' : ''}>${
          esc(x.name)}${x.imported ? ' (imported)' : ''}</option>`).join('')}
      </select>
      <span class="k" style="flex:0 0 auto">${tt('changes.onto')}</span>
      <select onchange="state.chg.target=this.value;state.chg.plan=null;chgPaint()">
        ${mods.map(m => `<option value="${esc(m)}" ${m === k.target ? 'selected' : ''}>${esc(m)}${
          m === s.mod ? tt('changes.this_mod_as_it_is_on') : ''}</option>`).join('')}
      </select>
      <button class="primary" ${k.busy ? 'disabled' : ''} onclick="chgPlan()">${tt('changes.compare')}</button>
    </div>
    ${p ? chgPlanHtml(p) : ''}
  </div>`;
}

function chgPlanHtml(p){
  const k = state.chg;
  if(!p.items.length) return `<div class="count">${tt('changes.the_set_changes_nothing_that_could')}</div>`;
  const c = p.counts || {};
  const order = ['conflict', 'gone', 'merged', 'clean', 'already'];
  const tally = order.filter(o => c[o]).map(o => `${c[o]} ${CHG_OUTCOME[o][0].replace(/^\S+ /, '')}`).join(' · ');
  const byFile = {};
  p.items.forEach(it => (byFile[it.rel] = byFile[it.rel] || []).push(it));
  const n = p.items.filter(it => k.picks.has(chgPickKey(it))).length;
  return `<div class="count" style="margin:8px 0">${esc(tally)}</div>
    ${Object.entries(byFile).map(([rel, items]) => `<div class="chgfile">
      <div class="chgfhead"><code>${esc(rel)}</code></div>
      ${items.map(chgItemHtml).join('')}
    </div>`).join('')}
    <div class="brow" style="margin-top:10px">
      <button class="primary" ${n && !k.busy ? '' : 'disabled'} onclick="chgApply()">${ttN('changes.port_changes_into',n,{target:esc(p.target)})}</button>
      <span class="count">${tt('changes.backed_up_first_logs_undo_takes')}</span>
    </div>`;
}

function chgItemHtml(it){
  const k = state.chg, [label, cls, help] = CHG_OUTCOME[it.outcome] || [it.outcome, '', ''];
  const key = chgPickKey(it), on = k.picks.has(key), open = k.open.has(it.id);
  const can = it.outcome !== 'already';
  const cmp = (it.mine !== undefined || it.theirs !== undefined) && !it.binary;
  return `<div class="chgitem">
    <label class="chk"><input type="checkbox" ${on ? 'checked' : ''} ${can ? '' : 'disabled'}
      onchange="chgTick(${it.id},this.checked)"></label>
    <span class="chgrec ${esc(it.kind)}">${CHG_KIND[it.kind] || ''} ${esc(it.key)}</span>
    <span class="${cls}" title="${esc(help)}">${esc(label)}</span>
    ${it.dangling && it.dangling.length ? `<span class="w-bad" title="${ttA('changes.the_results_export_descr_unit_txt')}">
      ${tt('changes.recruits_not_in_the_edu',{x:it.dangling.map(esc).join(', ')})}</span>` : ''}
    ${cmp ? `<button class="x" onclick="chgToggle(${it.id})">${open ? tt('changes.hide') : tt('changes.compare')}</button>` : ''}
    ${open ? chgCompareHtml(it) : ''}
  </div>`;
}

function chgCompareHtml(it){
  const col = (title, text) => `<div class="chgcol"><div class="count">${esc(title)}</div>
    <pre>${text == null ? `<span class="count">${tt('changes.not_there')}</span>` : esc(text)}</pre></div>`;
  return `<div class="chgcmp">
    ${col(tt('changes.original'), it.base)}${col(tt('changes.yours'), it.mine)}${col(tt('changes.new_version'), it.theirs)}
    ${it.merged != null ? col(tt('changes.merged_what_a_tick_writes'), it.merged) : ''}
  </div>`;
}

function chgFindItem(id){ return ((state.chg.plan || {}).items || []).find(x => x.id === id); }
function chgTick(id, on){
  const it = chgFindItem(id); if(!it) return;
  const k = state.chg, key = chgPickKey(it);
  if(on) k.picks.add(key); else k.picks.delete(key);
  chgPaint();
}
function chgToggle(id){
  const k = state.chg;
  if(k.open.has(id)) k.open.delete(id); else k.open.add(id);
  chgPaint();
}

async function chgPlan(){
  const k = state.chg;
  k.busy = true; chgPaint();
  let r;
  try{ r = await api.post('/api/changes/plan', {set: k.from, target: k.target}); }
  catch(e){ r = {error: errText(e)}; }
  k.busy = false;
  if(r.error){ toast(r.error, 5000); chgPaint(); return; }
  k.plan = r.plan; k.open = new Set();
  // what applies without a decision is ticked; a conflict or a removed record
  // is a decision, so it starts unticked
  k.picks = new Set(r.plan.items.filter(it => it.default).map(chgPickKey));
  chgPaint();
}

async function chgApply(){
  const k = state.chg, p = k.plan;
  const picks = p.items.filter(it => k.picks.has(chgPickKey(it))).map(it => ({rel: it.rel, key: it.key}));
  if(!picks.length) return;
  k.busy = true; chgPaint();
  let r;
  try{ r = await api.post('/api/changes/apply', {set: k.from, target: k.target, picks}); }
  catch(e){ r = {error: errText(e)}; }
  k.busy = false;
  if(r.error){ toast(r.error, 5000); chgPaint(); return; }
  toast(tt('changes.ported_change_s_into_file_s',{picks_n:picks.length,target:p.target,n:(r.written || []).length + (r.removed || []).length}), 5200);
  await loadChanges();
}

function chgImport(input){
  const f = input.files && input.files[0];
  if(!f) return;
  const rd = new FileReader();
  rd.onload = async () => {
    const data = String(rd.result).split(',')[1] || '';
    let r;
    try{ r = await api.post('/api/changes/import', {data, name: ''}); }
    catch(e){ r = {error: errText(e)}; }
    if(r.error){ toast(r.error, 5000); return; }
    toast(tt('changes.imported_as_pick_it_under_changes',{set:r.set}), 4800);
    await loadChanges();
    state.chg.from = r.set; chgPaint();
  };
  rd.readAsDataURL(f);
}

async function chgAdopt(){
  const k = state.chg;
  if(!confirm(tt('changes.record_every_tracked_file_as_it_wrong_after_update'))) return;
  const r = await api.post('/api/changes/adopt', {set: k.sum.set, mod: k.mod});
  if(r.error){ toast(r.error, 5000); return; }
  await loadChanges();
}

async function chgForget(){
  const k = state.chg;
  if(!confirm(tt('changes.forget_the_record_of_your_changes_to_mod',{mod:k.mod}))) return;
  const r = await api.post('/api/changes/forget', {set: k.sum.set});
  if(r.error){ toast(r.error, 5000); return; }
  await loadChanges();
}
