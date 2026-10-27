/* Armory Studio - Optimize (100n).

   The user's Quick Cleanup addon (github.com/ProJ-Yeet/Quick-Cleanup-Blender-Addon-),
   the steps a game mesh can take, as a remembered set of checkboxes: merge by
   distance (only where the UVs match too, so a seam stays a seam), degenerate
   triangles and what they leave loose, normals recalculated outside, reset
   vectors (smooth normals from the faces), and the Blender kit's export checks
   last. Light and Game-Ready are the addon's own presets as they apply here.
   The work is armory.optimize; what it leaves rides on each piece (tris, weld,
   flip, nrm), so sheets, UVs and weights stay the asset's. One Undo step. */

const ARM_OPT_DEFAULT = {merge: true, merge_distance: 0.0001, degenerate: true, outside: true,
                         reset_normals: false, checks: true};
const ARM_OPT_PRESETS = {
  light: {merge: true, merge_distance: 0.0001, degenerate: false, outside: true, reset_normals: false, checks: true},
  game: {merge: true, merge_distance: 0.0008, degenerate: true, outside: true, reset_normals: true, checks: true},
};
const ARM_NRM_BUF = new WeakMap();

// the normal buffer of a piece Optimize gave normals: the asset's, with them on
function armNrmBuffer(live, pc){
  const sig = JSON.stringify(pc.nrm);
  const hit = ARM_NRM_BUF.get(pc);
  if(hit && hit.sig === sig && hit.live === live) return hit.buf;
  const gl = armGl();
  const n = new Float32Array(live.geo.normals || new Float32Array(live.geo.positions.length));
  for(const k in pc.nrm){ const v = +k; n[v * 3] = pc.nrm[k][0]; n[v * 3 + 1] = pc.nrm[k][1]; n[v * 3 + 2] = pc.nrm[k][2]; }
  if(hit && hit.buf) gl.deleteBuffer(hit.buf);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, n, gl.STATIC_DRAW);
  ARM_NRM_BUF.set(pc, {sig, live, buf});
  return buf;
}

function armOptOpts(){
  const s = (state.settings || {}).armory_optimize;
  return Object.assign({}, ARM_OPT_DEFAULT, s && typeof s === 'object' ? s : {});
}
function armOptSave(o){
  state.settings.armory_optimize = o;
  api.post('/api/settings', {armory_optimize: o}).catch(() => {});
}
// the selected objects, or every visible one when none is
function armOptTargets(){
  const sel = armSelected();
  return sel.length ? sel : armVisibleObjects();
}

function armOptOpen(){
  document.getElementById('modal').className = 'modal';
  overlay.classList.add('open');
  ARM.optReport = null;
  armOptPaint();
}
function armOptPaint(){
  const o = armOptOpts(), n = armOptTargets().length;
  const box = (k, label, title) => `<label class="armcheck armoptrow" title="${esc(title)}"><input type="checkbox"${o[k] ? ' checked' : ''}
      onchange="armOptSet('${k}', this.checked)"> ${label}</label>`;
  const r = ARM.optReport;
  modal.innerHTML = `<div class="armopt">
    <h3>${tt('armory.optimize')}</h3>
    <div class="count" style="margin-bottom:8px">${tt('armory.opt_intro')}</div>
    <div class="armuvbar"><span class="count">${tt('armory.opt_presets')}</span>
      <button class="mini" onclick="armOptPreset('light')">${tt('armory.opt_light')}</button>
      <button class="mini" onclick="armOptPreset('game')">${tt('armory.opt_game')}</button></div>
    ${box('merge', tt('armory.opt_merge'), tt('armory.opt_merge_title'))}
    <label class="count armoptrow" style="padding-left:24px">${tt('armory.opt_distance')}
      <input type="number" step="0.0001" min="0" value="${o.merge_distance}" style="width:90px" onchange="armOptSet('merge_distance', +this.value)"></label>
    ${box('degenerate', tt('armory.opt_degenerate'), tt('armory.opt_degenerate_title'))}
    ${box('outside', tt('armory.opt_outside'), tt('armory.opt_outside_title'))}
    ${box('reset_normals', tt('armory.opt_reset'), tt('armory.opt_reset_title'))}
    ${box('checks', tt('armory.opt_checks'), tt('armory.opt_checks_title'))}
    <div class="count armnote">${tt('armory.opt_left_out')}</div>
    ${r ? armOptReportHtml(r) : ''}
    <div class="armimpfoot"><span class="count">${ttN('armory.opt_scope', n)}</span><span style="flex:1"></span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button class="primary" id="armOptGo" onclick="armOptRun()"${n ? '' : ' disabled'}>${tt('armory.opt_run')}</button></div>
  </div>`;
}
function armOptSet(k, v){ const o = armOptOpts(); o[k] = v; armOptSave(o); }
function armOptPreset(name){ armOptSave(Object.assign({}, ARM_OPT_PRESETS[name])); armOptPaint(); }

async function armOptRun(){
  const objs = armOptTargets();
  const btn = document.getElementById('armOptGo');
  if(btn){ btn.disabled = true; btn.textContent = tt('armory.working'); }
  let r;
  try{
    r = await api.post('/api/armory/optimize', {project: armProj(), ids: objs.map(o => o.id), opts: armOptOpts()});
    if(r.error) throw new Error(r.error);
  }catch(e){ toast(errText(e), 6000); armOptPaint(); return; }
  for(const [id, got] of Object.entries(r.objects || {})){
    const o = armObj(+id);
    if(!o) continue;
    (got.pieces || []).forEach((ch, i) => {
      const pc = o.src[i];
      if(!pc || !ch) return;
      // the piece as it was before its first run, so Restore puts it back
      // whenever the user likes; nothing here ever touches the file on disk
      if(!pc.opt0) pc.opt0 = JSON.parse(JSON.stringify(Object.fromEntries(ARM_OPT_KEYS.map(k => [k, pc[k] == null ? null : pc[k]]))));
      for(const k of ARM_OPT_KEYS){
        if(ch[k] == null) delete pc[k]; else pc[k] = ch[k];
      }
    });
  }
  ARM.optReport = r;
  armRepaint();
  armOptPaint();
}
const ARM_OPT_KEYS = ['tris', 'weld', 'flip', 'nrm'];
const armOptimized = o => (o.src || []).some(pc => pc.opt0);
// every optimized piece of the object back as it was before Optimize
function armOptRestore(id){
  const o = armObj(id); if(!o) return;
  for(const pc of o.src || []){
    if(!pc.opt0) continue;
    for(const k of ARM_OPT_KEYS){ if(pc.opt0[k] == null) delete pc[k]; else pc[k] = pc.opt0[k]; }
    delete pc.opt0;
  }
  armRepaint();
  toast(tt('armory.opt_restored'));
}
// the run is one Undo step; the dialog stays open on its report, so it offers it
function armOptUndo(){
  armUndo(false);
  ARM.optReport = null;
  armOptPaint();
}
function armOptReportHtml(r){
  const c = r.counts || {};
  const chk = r.checks;
  const issues = chk && chk.issues ? chk.issues : [];
  return `<div class="armoptreport">
    <div><b>${tt('armory.opt_done')}</b> ${tt('armory.opt_counts', {merged: c.merged || 0, degenerate: c.degenerate || 0,
      loose: Math.max(0, c.loose || 0), flipped: c.flipped || 0, normals: c.normals || 0})}
      <button class="mini" onclick="armOptUndo()" title="${esc(tt('armory.undo_title'))}">${tt('armory.opt_undo')}</button></div>
    ${chk ? (chk.error ? `<div class="w-bad">${esc(chk.error)}</div>` : issues.length
      ? issues.map(i => `<div class="armissue ${i.level}"><b>${i.level === 'error' ? tt('armory.exp_error') : tt('armory.exp_warning')}</b>
          ${esc(typeof armChkText === 'function' ? armChkText(i) : i.code)}</div>`).join('')
      : `<div class="armissue ok">${tt('armory.exp_all_clear')}</div>`) : ''}
  </div>`;
}
