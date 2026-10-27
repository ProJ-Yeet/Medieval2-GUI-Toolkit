/* =========================================================================
   Armory Studio's saved sessions and backups (Phase 99o)

   The project (config/armory/project.json) is the session open now. Saved
   under a name it becomes one of several (config/armory/sessions/), each
   carried on where it was left: its objects, and with them the viewport's
   camera, the card maker's settings and the export dialog's (`extra`). The
   server backs the open one up every few minutes while it changes, the
   last twenty kept (armory.backup), and any of them puts it back; so does
   reopening after a crash, which the page tells from a close by saying
   goodbye when it goes (armory.closed).
   ========================================================================= */

/* What rides with a session besides the model, put in before each save. */
function armExtrasInto(p){
  const keep = o => o ? JSON.parse(JSON.stringify(o)) : null;
  const card = state.cg ? Object.assign({}, state.cg) : null;
  if(card){ for(const k of ['saved', 'err', 'givePlan', 'units', 'poseNote', 'poseNote2']) delete card[k]; }
  p.extra = {cam: keep(ARM.cam), card: keep(card), exp: state.armExp ? keep(state.armExp.settings) : null};
}
/* And taken back out when a session is opened. */
function armExtrasFrom(p){
  const x = (p && p.extra) || {};
  if(x.cam && Array.isArray(x.cam.target)) ARM.cam = Object.assign({}, ARM.cam, x.cam);
  if(x.card) state.cg = Object.assign(cg(), x.card);
  if(x.exp){ state.armExp = null; armExp().settings = Object.assign(armExp().settings, x.exp); }
}

/* On the way out: the project as it is, then goodbye (a beacon survives
   the page closing, a fetch does not). */
let armSessWired = false;
function armSessWire(){
  if(armSessWired) return;
  armSessWired = true;
  window.addEventListener('pagehide', () => {
    if(!ARM.projReady || !state.armProj) return;
    try{
      armExtrasInto(armProj());
      navigator.sendBeacon('/api/armory/project', new Blob([JSON.stringify({project: armProj()})], {type: 'application/json'}));
      navigator.sendBeacon('/api/armory/closed', new Blob(['{}'], {type: 'application/json'}));
    }catch(e){ /* nothing to be done on the way out */ }
  });
}

/* Read once a session: whether the last one ended without goodbye. */
async function armSessCheck(){
  armSessWire();
  try{
    const v = await api.get('/api/armory/sessions?mark=1', 1);
    ARM.unclean = v.unclean && v.backups.length ? v : null;
  }catch(e){ ARM.unclean = null; }
  if(state.mode === 'armory') armPaintBar();
}

/* --- the dialog -------------------------------------------------------------------- */

async function armSessOpen(){
  document.getElementById('modal').className = 'modal wide';
  modal.innerHTML = `<div class="armimp"><div class="count">${tt('armory.reading')}</div></div>`;
  overlay.classList.add('open');
  armSave();
  await new Promise(r => setTimeout(r, 700));        // the save waiting on its timer goes first
  let v;
  try{ v = await api.get('/api/armory/sessions', 1); }
  catch(e){ modal.innerHTML = `<div class="armimp"><div class="w-bad">${esc(errText(e))}</div></div>`; return; }
  ARM.unclean = null;
  const when = t => new Date(t * 1000).toLocaleString();
  const rows = v.sessions.map(s => `<div class="armsessrow${s.id === v.current ? ' on' : ''}">
      <b>${esc(s.name)}</b>${s.id === v.current ? ` <span class="pill">${tt('armory.sess_open_now')}</span>` : ''}
      <span class="count">${ttN('armory.sess_facts', s.objects, {when: when(s.saved)})}</span><span style="flex:1"></span>
      ${s.id === v.current ? '' : `<button class="mini primary" onclick="armSessDo('open','${esc(s.id)}')">${tt('armory.sess_open')}</button>`}
      <button class="mini" onclick="armSessDo('duplicate','${esc(s.id)}')">${tt('armory.sess_duplicate')}</button>
      <button class="mini" onclick="armSessRename('${esc(s.id)}','${esc(s.name).replace(/'/g, '&#39;')}')">${tt('armory.sess_rename')}</button>
      <button class="mini armx" onclick="armSessDelete('${esc(s.id)}','${esc(s.name).replace(/'/g, '&#39;')}')" title="${esc(tt('armory.sess_delete'))}">✕</button></div>`).join('');
  const backs = v.backups.map(b => `<div class="armsessrow"><span>${esc(when(b.time))}</span>
      <span class="count">${ttN('armory.sess_backup_facts', b.objects)}</span><span style="flex:1"></span>
      <button class="mini" onclick="armSessRevert('${esc(q1(b.file))}')">${tt('armory.sess_revert')}</button></div>`).join('');
  modal.innerHTML = `<div class="armimp">
    <h3>${tt('armory.sess_title')}</h3>
    <div class="count">${v.name ? tt('armory.sess_current', {name: esc(v.name)}) : tt('armory.sess_unsaved')}</div>
    <div class="armexprow"><input id="armSessName" placeholder="${esc(tt('armory.sess_name'))}" value="${esc(armProj().name || '')}">
      <button class="primary" onclick="armSessSave()">${tt('armory.sess_save_as')}</button></div>
    <div class="armsect">${tt('armory.sess_saved')}</div>
    <div class="armsesslist">${rows || `<div class="count">${tt('armory.sess_none')}</div>`}</div>
    <div class="armsect">${tt('armory.sess_backups')}</div>
    <div class="count">${tt('armory.sess_backups_note')}</div>
    <div class="armsesslist">${backs || `<div class="count">${tt('armory.sess_no_backups')}</div>`}</div>
    <div class="armimpfoot"><span style="flex:1"></span><button onclick="closeModal()">${tt('common.close')}</button></div>
  </div>`;
}
async function armSessPost(body){
  try{ return await api.post('/api/armory/sessions', body); }
  catch(e){ toast(errText(e), 6000); return null; }
}
async function armSessSave(){
  const name = ((document.getElementById('armSessName') || {}).value || '').trim();
  if(!name){ toast(tt('armory.sess_name_first')); return; }
  armExtrasInto(armProj());
  const r = await armSessPost({action: 'save', name, project: armProj()});
  if(!r) return;
  state.armProj.session = r.project.session;
  toast(tt('armory.sess_saved_as', {name}));
  armSessOpen();
  armPaintBar();
}
async function armSessDo(action, id){
  const r = await armSessPost({action, id});
  if(!r) return;
  if(action === 'open') return armSessLoad(r.project);
  armSessOpen();
}
async function armSessRename(id, name){
  const nm = prompt(tt('armory.sess_rename'), name);
  if(!nm || !nm.trim()) return;
  const r = await armSessPost({action: 'rename', id, name: nm.trim()});
  if(r && armProj().session && armProj().session.id === id) armProj().session = r.project.session;
  armSessOpen(); armPaintBar();
}
async function armSessDelete(id, name){
  if(!confirm(tt('armory.sess_delete_confirm', {name}))) return;
  const r = await armSessPost({action: 'delete', id});
  if(r && armProj().session && armProj().session.id === id) delete armProj().session;
  armSessOpen(); armPaintBar();
}
async function armSessRevert(file){
  if(!confirm(tt('armory.sess_revert_confirm'))) return;
  const r = await armSessPost({action: 'revert', file});
  if(r) armSessLoad(r.project);
}
/* A session or a backup made the project: its assets read, its extras put
   back, its own undo history begun, the page drawn again. */
function armSessLoad(project){
  closeModal();
  state.armProj = project;
  const p = armProj();
  p.objects = p.objects || []; p.assets = p.assets || []; p.collections = p.collections || [];
  ARM.sel.clear(); ARM.detail = null; ARM.unclean = null;
  armExtrasFrom(p);
  ARM.loading = Promise.all(p.assets.map(a => armLoadAsset(a)));
  armUndoReset();
  if(state.mode === 'armory') renderArmory();
  toast(tt('armory.sess_loaded', {name: (p.session || {}).name || tt('armory.untitled')}));
}
