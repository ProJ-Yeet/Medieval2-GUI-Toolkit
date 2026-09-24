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
  replaces: ['replaces', 'the mod has it, and this one is different'],
  new: ['new', 'not in the mod yet'],
  refused: ['refused', 'not written, and why'],
  skipped: ['skipped', 'left as it is'],
  same: ['the same', 'already in the mod, byte for byte'],
};

function pzHtml(){
  const z = state.chg && state.chg.pz;
  if(!z) return '';
  const p = z.plan;
  const head = `<h4>Load ${esc(z.name)} into ${esc(state.src)}
    <span class="count">${p && p.manifest && p.manifest.kind ? `a ${esc(p.manifest.kind)}${p.manifest.campaign
      ? ` (${esc(p.manifest.campaign)})` : ''} from ${esc(p.manifest.mod || '?')}, ${esc(p.manifest.made || '')}` : 'a zip of files'}</span></h4>`;
  if(z.busy && !p) return `<div class="bsec">${head}<div class="count">Reading the zip and checking each file…</div></div>`;
  const counts = (p && p.counts) || {};
  const groups = Object.keys(PZ_STATES).filter(s => counts[s]).map(s => {
    const files = p.files.filter(f => f.state === s);
    const open = s === 'replaces' || s === 'refused' || files.length <= 12;
    return `<details ${open ? 'open' : ''}><summary><b>${counts[s]} ${PZ_STATES[s][0]}</b>
        <span class="count">${PZ_STATES[s][1]}</span></summary>
      ${files.slice(0, 400).map(f => `<div class="count" style="margin-left:14px"><code>data/${esc(f.rel)}</code>
        ${f.state === 'replaces' ? ` ${f.before.toLocaleString()} -> ${f.bytes.toLocaleString()} bytes`
          + (f.records.length ? ` · ${esc(f.records.join(', '))}${f.records_more ? ` +${f.records_more} more` : ''}` : '') : ''}
        ${f.why ? ` - ${esc(f.why)}` : ''}
        ${f.warnings.map(w => `<div class="w-warn">⚠ ${esc(w)}</div>`).join('')}</div>`).join('')}
      ${files.length > 400 ? `<div class="count">…and ${files.length - 400} more</div>` : ''}</details>`;
  }).join('');
  const writes = (counts.new || 0) + (counts.replaces || 0);
  return `<div class="bsec">${head}
    ${z.err ? `<div class="w-warn">${esc(z.err)}</div>` : ''}
    ${groups}
    ${p && p.stale.length ? `<div class="count">and ${p.stale.length} compiled <code>map.rwm</code> the loaded map files make stale,
      deleted (backed up) so the game builds it again: ${p.stale.map(r => `<code>${esc(r)}</code>`).join(', ')}</div>` : ''}
    ${p && p.ignored.length ? `<div class="count">${p.ignored.length} file(s) outside <code>data/</code> in the zip are not loaded:
      ${esc(p.ignored.slice(0, 6).join(', '))}${p.ignored.length > 6 ? '…' : ''}</div>` : ''}
    <div class="chgacts">
      <label class="count"><input type="checkbox" ${z.replace ? 'checked' : ''} onchange="pzReplace(this.checked)">
        replace the files the mod already has</label>
      <span style="flex:1"></span>
      <button onclick="pzClose()">Close</button>
      <button class="primary" onclick="pzApply()" ${writes && !z.busy ? '' : 'disabled'}>Load ${writes} file${writes === 1 ? '' : 's'}</button>
    </div></div>`;
}

async function pzApply(){
  const z = state.chg && state.chg.pz;
  if(!z || z.busy || !z.plan) return;
  const c = z.plan.counts || {};
  if(!confirm(`Load ${(c.new || 0) + (c.replaces || 0)} file(s) into ${state.src}: ${c.new || 0} new, `
    + `${c.replaces || 0} replacing the mod's own?\n\nEverything replaced is backed up first, and 🕑 Log undoes the whole load.`)) return;
  z.busy = true;
  chgPaint();
  let r;
  try{ r = await api.post('/api/project/load_apply', {mod: state.src, data: z.data, replace: z.replace}); }
  catch(e){ r = {error: errText(e)}; }
  z.busy = false;
  if(r.error){ z.err = r.error; chgPaint(); return; }
  toast(`Loaded. ${r.record ? r.record.summary : ''}. 🕑 Log undoes it.`, 7000);
  state.chg.pz = null;
  await loadChanges();
}
