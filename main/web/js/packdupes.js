/* packdupes.js - duplicate animations in a mod's packs, compared and chosen (101h)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it.

   Opened from Home's Animation packs card. Two lists, one Write:
     one path, different animations - the game plays only the first copy at a
       scale; Compare lays the copies side by side and a pick says which plays
     one animation, several paths   - the same bytes under each path; a merge
       keeps one path and points every slot naming the others at it
   Everything ticked is one job in the Log, with one Undo. */
let PD = null;                 // {mod, r, pick:{key:offset}, cmp:{key:result|'…'}, merge:{i:keep path|''}}

const pdKey = c => `${c.path}@${c.scale}`;

async function pdOpen(mod){
  PD = {mod, r: null, pick: {}, cmp: {}, merge: {}, busy: false};
  const modal = document.getElementById('modal');
  modal.className = 'modal wide';
  modal.innerHTML = `<h2>${tt('packdupes.title', {mod: esc(mod)})}</h2>
    <div class="mbody"><div class="count">${tt('packdupes.reading')}</div></div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`;
  document.getElementById('overlay').classList.add('open');
  let r;
  try{ r = await api.get('/api/packs/duplicates?mod=' + enc(mod)); }
  catch(e){ r = {error: '' + e}; }
  if(!PD || PD.mod !== mod) return;
  PD.r = r;
  // every identical group starts merged into the path most slots already name
  (r.identical || []).forEach((g, i) => { PD.merge[i] = g.paths[0].path; });
  pdRender();
}

function pdChanges(){
  const picks = Object.keys(PD.pick).filter(k => {
    const c = (PD.r.conflicts || []).find(x => pdKey(x) === k);
    return c && PD.pick[k] !== c.copies[0].offset;
  }).length;
  const merges = Object.values(PD.merge).filter(Boolean).length;
  return {picks, merges};
}

function pdRender(){
  if(!PD) return;
  const r = PD.r, modal = document.getElementById('modal');
  const body = r.error ? `<div class="w-bad">${esc(r.error)}</div>` : pdConflictsHtml() + pdIdenticalHtml()
    + (r.same_bytes ? `<div class="count" style="margin-top:10px">${ttN('packdupes.same_bytes', r.same_bytes)}</div>` : '');
  const ch = r.error ? {picks: 0, merges: 0} : pdChanges();
  const n = ch.picks + ch.merges;
  modal.innerHTML = `<h2>${tt('packdupes.title', {mod: esc(PD.mod)})}</h2>
    <div class="mbody">${body}</div>
    <div class="foot"><span class="count" style="flex:1">${n ? tt('packdupes.pending', {picks: ch.picks, merges: ch.merges}) : ''}</span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button class="primary" ${n && !PD.busy ? '' : 'disabled'} onclick="pdApply()">${tt('packdupes.write')}</button></div>`;
}

/* ---- one path, different animations ---- */
function pdConflictsHtml(){
  const r = PD.r, rows = r.conflicts || [];
  const head = `<h3>${tt('packdupes.conflicts_head')}</h3>
    <div class="count">${tt('packdupes.conflicts_note')}</div>`;
  if(!rows.length) return head + `<div class="count w-good" style="margin:6px 0 12px">${tt('packdupes.no_conflicts')}</div>`;
  return head + `<div class="pdlist">${rows.map(c => {
      const k = pdKey(c), open = PD.cmp[k] !== undefined;
      const chosen = PD.pick[k] !== undefined ? PD.pick[k] : c.copies[0].offset;
      return `<div class="pdrow">
        <div class="barrow"><code style="flex:1;min-width:0;overflow-wrap:anywhere">${esc(c.path)}</code>
          <span class="count">${tt('packdupes.scale_copies', {scale: c.scale, n: c.copies.length})}</span>
          <button onclick="pdCompare('${q1(esc(c.path))}',${c.scale})">${open ? tt('packdupes.hide') : tt('packdupes.compare')}</button></div>
        <div class="count">${c.users.length ? tt('packdupes.used_by', {x: c.users.map(esc).join(', ')}) : tt('packdupes.used_by_none')}</div>
        ${open ? pdCompareHtml(c, chosen) : ''}
      </div>`;}).join('')}</div>
    ${r.conflicts_total > rows.length ? `<div class="count">${tt('packdupes.more', {n: r.conflicts_total - rows.length})}</div>` : ''}`;
}

async function pdCompare(path, scale){
  const k = `${path}@${scale}`;
  if(PD.cmp[k] !== undefined){ delete PD.cmp[k]; return pdRender(); }
  PD.cmp[k] = '…'; pdRender();
  let r;
  try{ r = await api.get(`/api/packs/duplicates/compare?mod=${enc(PD.mod)}&path=${enc(path)}&scale=${scale}`); }
  catch(e){ r = {error: '' + e}; }
  if(!PD || PD.cmp[k] === undefined) return;
  PD.cmp[k] = r; pdRender();
}

function pdCompareHtml(c, chosen){
  const k = pdKey(c), r = PD.cmp[k];
  if(r === '…') return `<div class="count">${tt('packdupes.reading')}</div>`;
  if(r.error) return `<div class="w-bad">${esc(r.error)}</div>`;
  const diff = d => d == null ? `<span class="w-warn">${tt('packdupes.other_bones')}</span>`
    : d.max === 0 ? tt('packdupes.same_motion') : tt('packdupes.degrees', {mean: d.mean, max: d.max});
  return `<table class="hctab pdcmp"><tr><th></th><th>${tt('packdupes.col_copy')}</th><th class="r">${tt('packdupes.col_frames')}</th>
      <th class="r">${tt('packdupes.col_seconds')}</th><th class="r">${tt('packdupes.col_bones')}</th><th class="r">${tt('packdupes.col_size')}</th>
      <th>${tt('packdupes.col_difference')}</th></tr>
    ${r.copies.map((x, i) => `<tr>
      <td><input type="radio" name="pd_${esc(k)}" ${x.offset === chosen ? 'checked' : ''}
        onchange="pdPick('${q1(esc(k))}',${x.offset})" title="${ttA('packdupes.play_this')}"></td>
      <td>${i + 1}${x.plays ? ` <span class="pill">${tt('packdupes.plays_now')}</span>` : ''}</td>
      <td class="r">${x.frames}</td><td class="r">${x.seconds != null ? x.seconds : '?'}</td>
      <td class="r">${x.rot_bones}${x.pos_bones ? ` / ${x.pos_bones}` : ''}</td>
      <td class="r count">${homeSize(x.size)}</td>
      <td>${x.error ? `<span class="w-bad">${esc(x.error)}</span>` : i === 0 ? tt('packdupes.the_one_played') : diff(x.difference)}</td></tr>`).join('')}
  </table><div class="count">${tt('packdupes.pick_note')}</div>`;
}
function pdPick(k, offset){ PD.pick[k] = offset; pdRender(); }

/* ---- one animation, several paths ---- */
function pdIdenticalHtml(){
  const r = PD.r, groups = r.identical || [];
  const head = `<h3 style="margin-top:14px">${tt('packdupes.identical_head')}</h3>
    <div class="count">${tt('packdupes.identical_note')}</div>`;
  if(!groups.length) return head + `<div class="count w-good" style="margin:6px 0">${tt('packdupes.no_identical')}</div>`;
  return head + `<div class="count" style="margin-top:4px">${tt('packdupes.identical_total', {groups: r.identical_total.toLocaleString(), freed: homeSize(r.identical_freed)})}</div>
    <div class="barrow" style="margin:6px 0">
      <button onclick="pdMergeAll(true)">${tt('packdupes.merge_all')}</button>
      <button onclick="pdMergeAll(false)">${tt('packdupes.merge_none')}</button></div>
    <div class="pdlist">${groups.map((g, i) => {
      const keep = PD.merge[i] || '';
      return `<div class="pdrow">
        <label class="chk"><input type="checkbox" ${keep ? 'checked' : ''} onchange="pdMergeToggle(${i},this.checked)">
          ${ttN('packdupes.group', g.paths.length, {size: homeSize(g.size), freed: homeSize(g.freed)})}</label>
        ${g.paths.map(p => `<label class="pdpath${keep ? '' : ' off'}">
          <input type="radio" name="pdm_${i}" ${p.path === keep ? 'checked' : ''} ${keep ? '' : 'disabled'}
            onchange="pdMergeKeep(${i},'${q1(esc(p.path))}')" title="${ttA('packdupes.keep_this')}">
          <code>${esc(p.path)}</code>
          <span class="count">${p.users.length ? ttN('packdupes.slots_users', p.users.length) : tt('packdupes.used_by_none')}</span>
          ${keep && p.path === keep ? `<span class="pill">${tt('packdupes.kept')}</span>` : ''}</label>`).join('')}
      </div>`;}).join('')}</div>
    ${r.identical_total > groups.length ? `<div class="count">${tt('packdupes.more', {n: r.identical_total - groups.length})}</div>` : ''}`;
}
function pdMergeToggle(i, on){ PD.merge[i] = on ? PD.r.identical[i].paths[0].path : ''; pdRender(); }
function pdMergeKeep(i, path){ PD.merge[i] = path; pdRender(); }
function pdMergeAll(on){ (PD.r.identical || []).forEach((g, i) => { PD.merge[i] = on ? (PD.merge[i] || g.paths[0].path) : ''; }); pdRender(); }

/* ---- the job ---- */
async function pdApply(){
  const r = PD.r;
  const choices = (r.conflicts || []).filter(c => PD.pick[pdKey(c)] !== undefined && PD.pick[pdKey(c)] !== c.copies[0].offset)
    .map(c => ({path: c.path, scale: c.scale, offset: PD.pick[pdKey(c)]}));
  const merges = (r.identical || []).map((g, i) => PD.merge[i] ? {paths: g.paths.map(p => p.path), keep: PD.merge[i]} : null)
    .filter(Boolean);
  if(!confirm(tt('packdupes.confirm', {picks: choices.length, merges: merges.length, mod: PD.mod}))) return;
  PD.busy = true; pdRender();
  let res;
  try{ res = await api.post('/api/packs/duplicates/apply', {mod: PD.mod, choices, merges}); }
  catch(e){ res = {error: '' + e}; }
  PD.busy = false;
  if(res.error){ toast(res.error, 6000); return pdRender(); }
  activity(tt('packdupes.done_activity'), res.summary);
  toast(res.summary, 5200);
  // Home's packs card counts change too
  delete HOME_REPORTS['_packsr_' + PD.mod];
  pdOpen(PD.mod);
}
