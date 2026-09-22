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
  clean: ['✓ applies', 'w-good', 'The new version left this as it was, so your change goes straight in.'],
  merged: ['⇄ merged', 'w-good', 'Both sides changed this, in different lines. Your lines and theirs are both in. Compare to check.'],
  already: ['= already there', '', 'The new version already says what your change said.'],
  conflict: ['⚠ conflict', 'w-warn', 'Both sides changed the same lines. Tick it to keep yours over theirs; leave it to keep theirs.'],
  gone: ['✗ gone upstream', 'w-bad', 'You changed this and the new version no longer has it. Tick it to put yours back.'],
};
const CHG_KIND = {added: '＋', removed: '−', edited: '✎'};
const CHG_DISK = {
  same: '',
  changed: 'changed on disk since your last save here',
  original: 'back to the original on disk',
  missing: 'missing on disk',
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
  main.innerHTML = '<div class="empty">Reading what you have changed in ' + esc(mod) + '…</div>';
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
    main.innerHTML = `<div class="empty">Couldn't read the change set.<br>
      <span class="count">${esc(k.err)}</span><br><br>
      <button class="primary" onclick="loadChanges()">Retry</button></div>`;
    return;
  }
  const s = k.sum;
  main.innerHTML = `<div class="chgwrap">
    ${chgHeadHtml(s)}
    ${chgVersionsHtml(s)}
    ${chgFilesHtml(s)}
    ${chgPortHtml(s)}
  </div>`;
}

function chgHeadHtml(s){
  const moved = (s.files || []).filter(f => f.disk && f.disk !== 'same');
  const others = (s.sets || []).filter(x => x.name !== s.set);
  return `<div class="bsec"><h4>Your changes to ${esc(s.mod)}
      ${s.set ? `<span class="count">${esc(s.set)}${s.on ? ', on' : ', off'} · recorded since ${
        esc(s.created || '')}</span>` : ''}</h4>
    <div class="trnote">Every save this toolkit makes to a mod is recorded here as it
      happens: the file as it was before your first change, and the file as you left it.
      Both are kept outside the mod folder, so a mod update that overwrites the files cannot
      touch them. When it does, port your changes back onto the new version below.</div>
    ${moved.length ? `<div class="chgwarn">⚠ ${moved.length} file${moved.length === 1 ? '' : 's'}
      changed under you since your last save here - most likely an update to the mod.
      <b>Port your changes onto it</b> below to put them back, change by change.</div>` : ''}
    <div class="chgacts">
      ${s.set ? `<a class="btn" href="/api/changes/export?set=${enc(s.set)}"
          title="The whole record as one file: take it to another machine, or keep it">⤓ Export</a>
        <a class="btn" href="/api/changes/files?set=${enc(s.set)}"
          title="Just the files you changed, as you last saved them, in their data/ folders.
Unzip into a mod's folder to put them in place, or send them to somebody without this tool."
          >⤓ Export changed files</a>` : ''}
      <label class="btn" title="A change set exported somewhere else">⤒ Import
        <input type="file" accept=".m2changes,.zip" style="display:none" onchange="chgImport(this)"></label>
      ${s.set ? `<button onclick="chgAdopt()" title="For edits you made by hand outside the toolkit.
Not after an update: that is what a port is for.">Take the files on disk as mine</button>
        <button class="danger" onclick="chgForget()" title="Stop recording against this original.
The mod is not touched.">Forget this record</button>` : ''}
    </div>
    ${others.length ? `<div class="count" style="margin-top:6px">Other change sets:
      ${others.map(x => esc(x.name) + (x.imported ? ' (imported)' : '')).join(', ')}</div>` : ''}
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
  return `<div class="bsec"><h4>Versions of this mod <span class="n">${vs.length}</span></h4>
    <div class="trnote">One is on at a time. Switching takes that version's changes out
      of the files and puts the other's in, as one save that 🕑 Log can undo. With every
      version off the mod is as it shipped, and your next save starts a new one.</div>
    ${vs.map(v => `<div class="chgver${v.active ? ' on' : ''}">
      <span class="chgdot">${v.active ? '●' : '○'}</span>
      <b>${esc(v.name)}</b>
      <span class="count">${v.files} file${v.files === 1 ? '' : 's'} changed${
        v.imported ? ' · imported' : ''} · since ${esc(v.created || '?')}</span>
      <span class="sp"></span>
      ${v.name !== s.set ? `<button class="x" onclick="chgView('${q1(esc(v.name))}')">View</button>` : ''}
      <button class="x" onclick="chgRename('${q1(esc(v.name))}')">Rename</button>
      ${v.active
        ? `<button class="x" onclick="chgSwitch(null)" title="Put the original records back">Turn off</button>`
        : `<button class="x primary" onclick="chgSwitch('${q1(esc(v.name))}')">Switch to this</button>`}
    </div>`).join('')}
    ${!vs.some(v => v.active) ? '<div class="count" style="margin-top:6px">Every version is off: the mod is as it shipped.</div>' : ''}
  </div>`;
}

/* The edits a switch would write over. The page is the only side that knows
   about them, so it asks every editor that keeps a working copy. */
function chgUnsaved(){
  const out = [];
  try{ if(state.bld && state.bld.work && bldDirty()) out.push('Buildings'); }catch(e){}
  try{ if(state.ed && (edDirty() || edCmpDirty() || edRecDirty())) out.push('the unit editor'); }catch(e){}
  try{ if(typeof cevDirty === 'function' && cevDirty()) out.push('campaign events'); }catch(e){}
  try{ if(typeof cftDirty === 'function' && cftDirty()) out.push('forts'); }catch(e){}
  const names = {tr: 'Traits', an: 'Ancillaries', gu: 'Guilds', fac: 'Factions',
                 mf: 'Minor files', cdb: 'Campaign constants', str: 'Strings', snd: 'Unit sounds'};
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
    toast('Save or drop the unsaved edits first (' + busy.join(', ') + '): a switch rewrites the files under them.', 6000);
    return;
  }
  let r;
  try{ r = await api.post('/api/changes/switchplan', {mod: k.mod, to}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error && !r.switch){ toast(r.error, 5000); return; }
  const sw = r.switch;
  if(sw.blocked && sw.blocked.length){
    alert('This switch is refused: ' + sw.blocked.length + ' record(s) would conflict with the files as they are now.\n\n'
      + sw.blocked.slice(0, 12).map(b => '  ' + b.set + ': ' + b.rel + ' / ' + b.key + ' (' + b.outcome + ')').join('\n')
      + '\n\nThe files moved under the version that is on - most likely an update. Port that version onto the mod first.');
    return;
  }
  const what = sw.off && sw.on ? `Take "${sw.off}" out and put "${sw.on}" in?`
    : sw.off ? `Turn "${sw.off}" off, putting the original records back?`
    : `Turn "${sw.on}" on?`;
  if(!confirm(what + '\n\n' + sw.files.length + ' file(s) will be rewritten. 🕑 Log can undo it.')) return;
  try{ r = await api.post('/api/changes/switch', {mod: k.mod, to}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast(r.error, 5000); return; }
  toast(`Switched: ${(r.written || []).length} file(s) rewritten. Undo is in 🕑 Log.`, 4600);
  k.view = '';
  await loadChanges();
}

async function chgRename(name){
  const nn = prompt('A name for this version of the mod:', name);
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
  if(!s.set) return `<div class="bsec"><div class="empty" style="padding:18px">Nothing recorded for
    ${esc(s.mod)} yet. The first save you make to it from any screen starts the record.</div></div>`;
  if(!files.length) return `<div class="bsec"><div class="count">The record holds no change:
    every file it tracks is back to how it started.</div></div>`;
  return `<div class="bsec"><h4>What you changed <span class="n">${files.length}</span>
      <span class="count">file${files.length === 1 ? '' : 's'}</span></h4>
    ${files.map(f => `<div class="chgfile">
      <div class="chgfhead"><code>${esc(f.rel)}</code>
        <span class="badge">${esc(f.state)}</span>
        <span class="count">${f.count} ${esc(f.what)}${f.count === 1 ? '' : 's'}</span>
        ${CHG_DISK[f.disk] ? `<span class="w-warn">· ${esc(CHG_DISK[f.disk])}</span>` : ''}</div>
      <div class="chgrecs">${f.records.map(r => `<span class="chgrec ${esc(r.kind)}"
          title="${esc(r.kind)}">${CHG_KIND[r.kind] || ''} ${esc(r.key)}</span>`).join('')}
        ${f.more ? `<span class="count">+${f.more} more</span>` : ''}</div>
    </div>`).join('')}
  </div>`;
}

function chgPortHtml(s){
  const k = state.chg;
  const setOpts = (s.sets || []).filter(x => x.files);
  if(!setOpts.length) return '';
  const mods = realMods().map(m => m.name);
  const p = k.plan;
  return `<div class="bsec"><h4>Port changes onto a version of the mod</h4>
    <div class="brow">
      <span class="k">Changes from</span>
      <select onchange="state.chg.from=this.value;state.chg.plan=null;chgPaint()">
        ${setOpts.map(x => `<option value="${esc(x.name)}" ${x.name === k.from ? 'selected' : ''}>${
          esc(x.name)}${x.imported ? ' (imported)' : ''}</option>`).join('')}
      </select>
      <span class="k" style="flex:0 0 auto">onto</span>
      <select onchange="state.chg.target=this.value;state.chg.plan=null;chgPaint()">
        ${mods.map(m => `<option value="${esc(m)}" ${m === k.target ? 'selected' : ''}>${esc(m)}${
          m === s.mod ? ' (this mod, as it is on disk now)' : ''}</option>`).join('')}
      </select>
      <button class="primary" ${k.busy ? 'disabled' : ''} onclick="chgPlan()">Compare</button>
    </div>
    ${p ? chgPlanHtml(p) : ''}
  </div>`;
}

function chgPlanHtml(p){
  const k = state.chg;
  if(!p.items.length) return '<div class="count">The set changes nothing that could be ported.</div>';
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
      <button class="primary" ${n && !k.busy ? '' : 'disabled'} onclick="chgApply()">Port ${n} change${n === 1 ? '' : 's'} into ${esc(p.target)}</button>
      <span class="count">Backed up first. 🕑 Log's Undo takes it back.</span>
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
    ${it.dangling && it.dangling.length ? `<span class="w-bad" title="The result's export_descr_unit.txt has no unit by this name, so the pool would recruit nothing">
      recruits ${it.dangling.map(esc).join(', ')}, not in the EDU</span>` : ''}
    ${cmp ? `<button class="x" onclick="chgToggle(${it.id})">${open ? 'Hide' : 'Compare'}</button>` : ''}
    ${open ? chgCompareHtml(it) : ''}
  </div>`;
}

function chgCompareHtml(it){
  const col = (title, text) => `<div class="chgcol"><div class="count">${esc(title)}</div>
    <pre>${text == null ? '<span class="count">(not there)</span>' : esc(text)}</pre></div>`;
  return `<div class="chgcmp">
    ${col('Original', it.base)}${col('Yours', it.mine)}${col('New version', it.theirs)}
    ${it.merged != null ? col('Merged: what a tick writes', it.merged) : ''}
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
  toast(`Ported ${picks.length} change(s) into ${p.target}: ${(r.written || []).length + (r.removed || []).length} file(s) written. Undo is in 🕑 Log.`, 5200);
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
    toast(`Imported as "${r.set}". Pick it under "Changes from" to port it.`, 4800);
    await loadChanges();
    state.chg.from = r.set; chgPaint();
  };
  rd.readAsDataURL(f);
}

async function chgAdopt(){
  const k = state.chg;
  if(!confirm('Record every tracked file as it is on disk now, as your version?\n\n'
      + 'Right after hand edits made outside the toolkit. WRONG after a mod update: '
      + 'your changes would be replaced by the update. Port instead.')) return;
  const r = await api.post('/api/changes/adopt', {set: k.sum.set, mod: k.mod});
  if(r.error){ toast(r.error, 5000); return; }
  await loadChanges();
}

async function chgForget(){
  const k = state.chg;
  if(!confirm('Forget the record of your changes to ' + k.mod + '?\n\n'
      + 'The mod itself is not touched, but the originals are dropped, so these '
      + 'changes can no longer be ported onto an update. Export it first to keep a copy.')) return;
  const r = await api.post('/api/changes/forget', {set: k.sum.set});
  if(r.error){ toast(r.error, 5000); return; }
  await loadChanges();
}
