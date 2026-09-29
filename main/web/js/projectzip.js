/* projectzip.js - a zip of files loaded back into a mod (Phase 71, D12)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= LOAD A ZIP OF FILES (71) =========================
   The other half of every export here that writes a zip laid out under
   data/: My changes' changed files, the faction screen's faction files, the
   campaign map's "this campaign as a zip". A zip is planned first, file by
   file (new, the same, what it replaces and which records differ, what is
   refused and why), and loaded as one job with one Undo. It lives on My
   changes because that is where the changed-files zip is made.

   THE PAGE NEVER PARSES A GAME FILE: /api/project/load_plan|load_apply. */

async function pzChosen(input){
  const f = input.files && input.files[0];
  input.value = '';
  if(!f) return;
  const buf = new Uint8Array(await f.arrayBuffer());
  let bin = '';
  for(let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
  state.chg.pz = {name: f.name, data: btoa(bin), replace: true, plan: null, busy: true, err: ''};
  chgPaint();
  await pzPlan();
}
async function pzPlan(){
  const z = state.chg && state.chg.pz;
  if(!z) return;
  z.busy = true;
  let r;
  try{ r = await api.post('/api/project/load_plan', {mod: state.src, data: z.data, replace: z.replace}); }
  catch(e){ r = {error: errText(e)}; }
  z.busy = false;
  z.plan = r.plan || null;
  z.err = r.error || '';
  chgPaint();
}
function pzClose(){ state.chg.pz = null; chgPaint(); }
function pzReplace(on){ state.chg.pz.replace = on; pzPlan(); }

const PZ_STATES = {
  replaces: ['replaces', tt('projectzip.the_mod_has_it_and_this')],
  new: ['new', tt('projectzip.not_in_the_mod_yet')],
  refused: ['refused', tt('projectzip.not_written_and_why')],
  skipped: ['skipped', tt('projectzip.left_as_it_is')],
  same: [tt('projectzip.the_same'), tt('projectzip.already_in_the_mod_byte_for')],
};

function pzHtml(){
  const z = state.chg && state.chg.pz;
  if(!z) return '';
  const p = z.plan;
  const head = `<h4>${tt('projectzip.load_into',{name:esc(z.name),src:esc(state.src)})}
    <span class="count">${p && p.manifest && p.manifest.kind ? tt('projectzip.a_from',{kind:esc(p.manifest.kind),x:p.manifest.campaign
      ? ` (${esc(p.manifest.campaign)})` : '',x2:esc(p.manifest.mod || '?'),x3:esc(p.manifest.made || '')}) : tt('projectzip.a_zip_of_files')}</span></h4>`;
  if(z.busy && !p) return `<div class="bsec">${head}<div class="count">${tt('projectzip.reading_the_zip_and_checking_each')}</div></div>`;
  const counts = (p && p.counts) || {};
  const groups = Object.keys(PZ_STATES).filter(s => counts[s]).map(s => {
    const files = p.files.filter(f => f.state === s);
    const open = s === 'replaces' || s === 'refused' || files.length <= 12;
    return `<details ${open ? 'open' : ''}><summary><b>${counts[s]} ${PZ_STATES[s][0]}</b>
        <span class="count">${PZ_STATES[s][1]}</span></summary>
      ${files.slice(0, 400).map(f => `<div class="count" style="margin-left:14px"><code>data/${esc(f.rel)}</code>
        ${f.state === 'replaces' ? (f.records.length
          ? tt('projectzip.bytes_records',{before:f.before.toLocaleString(),bytes:f.bytes.toLocaleString(),
            records:esc(f.records.join(', ')) + (f.records_more ? tt('projectzip.more',{records_more:f.records_more}) : '')})
          : tt('projectzip.bytes',{before:f.before.toLocaleString(),bytes:f.bytes.toLocaleString()})) : ''}
        ${f.why ? ` - ${esc(f.why)}` : ''}
        ${f.warnings.map(w => `<div class="w-warn">⚠ ${esc(w)}</div>`).join('')}</div>`).join('')}
      ${files.length > 400 ? `<div class="count">${tt('projectzip.and_more',{files:files.length - 400})}</div>` : ''}</details>`;
  }).join('');
  const writes = (counts.new || 0) + (counts.replaces || 0);
  return `<div class="bsec">${head}
    ${z.err ? `<div class="w-warn">${esc(z.err)}</div>` : ''}
    ${groups}
    ${p && p.stale.length ? `<div class="count">${tt('projectzip.and_compiled_map_rwm_the_loaded',{stale_n:p.stale.length,stale:p.stale.map(r => `<code>${esc(r)}</code>`).join(', ')})}</div>` : ''}
    ${p && p.ignored.length ? `<div class="count">${tt('projectzip.file_s_outside_data_in_the',{ignored_n:p.ignored.length,ignored:esc(p.ignored.slice(0, 6).join(', ')),ignored2:p.ignored.length > 6 ? '…' : ''})}</div>` : ''}
    <div class="chgacts">
      <label class="count"><input type="checkbox" ${z.replace ? 'checked' : ''} onchange="pzReplace(this.checked)">
        ${tt('projectzip.replace_the_files_the_mod_already')}</label>
      <span style="flex:1"></span>
      <button onclick="pzClose()">${tt('common.close')}</button>
      <button class="primary" onclick="pzApply()" ${writes && !z.busy ? '' : 'disabled'}>${ttN('projectzip.load_files', writes)}</button>
    </div></div>`;
}

async function pzApply(){
  const z = state.chg && state.chg.pz;
  if(!z || z.busy || !z.plan) return;
  const c = z.plan.counts || {};
  if(!confirm(tt('projectzip.load_files_confirm',{files:(c.new || 0) + (c.replaces || 0),src:state.src,new:c.new || 0,replaces:c.replaces || 0}))) return;
  z.busy = true;
  chgPaint();
  let r;
  try{ r = await api.post('/api/project/load_apply', {mod: state.src, data: z.data, replace: z.replace}); }
  catch(e){ r = {error: errText(e)}; }
  z.busy = false;
  if(r.error){ z.err = r.error; chgPaint(); return; }
  toast(tt('projectzip.loaded_log_undoes_it',{x:r.record ? r.record.summary : ''}), 7000);
  state.chg.pz = null;
  await loadChanges();
}
