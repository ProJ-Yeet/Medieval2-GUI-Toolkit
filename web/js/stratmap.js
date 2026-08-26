/* stratmap.js — Strat map tab: descr_model_strat.txt and data/models_strat

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html — there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE STRAT MAP'S MODELS — the other half of a mod's 3D art.

   BMDB mode's list is every battle model; this is every *campaign map* model:
   the generals, agents, heroes and faction symbols `descr_model_strat.txt`
   declares and the `.CAS` meshes and textures under `data/models_strat` they
   point at. The two screens do the same job on different trees, so this one is
   deliberately the same shape — a list you can search, a row per entry saying
   who uses it, and one 🧹 dialog that moves the dead weight out of the mod
   (backed up, exported, undoable) rather than deleting anything.

   Why it is worth a screen: the strat map is where unused art hides. A battle
   model nobody recruits is at least visible in the unit list; a general model
   that was replaced two versions ago is visible nowhere at all, and its 5 MB
   texture goes on shipping. Divide and Conquer carries 54 MB of files under
   models_strat that nothing in the mod names.

   `models_strat/residences` is left out of all of it — see stratmap.py: the
   game reads a faction's settlement variant out of that tree by folder, with
   nothing naming the file, so "nothing names it" would be wrong about all of it.
   ===================================================================== */
async function loadStratmap(){
  const mod=state.src;
  const job=newJob();
  main.innerHTML=`<div class="empty" style="max-width:420px;margin:60px auto">
      <div class="progress-track"><div class="progress-fill" id="jobFill" style="width:0%"></div></div>
      <div class="count" style="margin-top:8px"><b id="jobPct">0%</b>
        <span id="jobStep">reading ${esc(mod)}’s descr_model_strat.txt…</span></div>
    </div>`;
  state.stmJob=job;
  (async()=>{ while(state.stmJob===job){
    await new Promise(r=>setTimeout(r,300));
    if(state.stmJob!==job)break;
    let p=null; try{p=await api.get('/api/progress?job='+enc(job),1);}catch(e){}
    if(state.stmJob===job&&p&&typeof p.pct==='number')jobPaint(p.pct,p.label||'');
  }})();
  try{ state.stm=await api.get(`/api/stratmap/entries?mod=${enc(mod)}&job=${enc(job)}`); }
  catch(e){ state.stmJob=null; if(stale('stratmap',mod))return;
    main.innerHTML=`<div class="empty">Couldn't read the strat-map models.<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadStratmap()">Retry</button></div>`; return; }
  finally{ state.stmJob=null; }
  if(stale('stratmap',mod))return;
  renderStratmap();
}
function renderStratmap(){
  if(!state.stm||state.stm.mod!==state.src)return loadStratmap();
  const s=state.stm;
  if(!s.has_file){
    count.textContent='';
    main.innerHTML=bmdbTabsHtml('data/descr_model_strat.txt')+`<div class="empty">
      <b>${esc(state.src)}</b> has no <code>data/descr_model_strat.txt</code>.<br>
      <span class="count">That is the file that declares every campaign-map model,
      so there is nothing here to list or clean up. A mod without one uses the
      game's own, and its <code>models_strat</code> folder is not its to tidy.</span></div>`;
    return;
  }
  const qq=search.value.trim().toLowerCase();
  const rows=s.entries.filter(e=>
    (!qq||e.name.toLowerCase().includes(qq)||(e.skeleton||'').toLowerCase().includes(qq)
      ||e.used_by.some(u=>u.toLowerCase().includes(qq))
      ||e.files.some(f=>f.toLowerCase().includes(qq)))
    &&(!unusedOnly.checked||e.unused));
  const nUnused=s.entries.filter(e=>e.unused).length;
  const dupes=s.count-s.names;
  count.textContent=`${rows.length}/${s.names}`;
  main.innerHTML=bmdbTabsHtml('data/descr_model_strat.txt')+`
    <div class="dbhead">
      <h2>${esc(state.src)} · ${s.names} strat-map model${s.names===1?'':'s'}</h2>
      <span class="count">${nUnused} referenced by nothing${
        nUnused?'. <b class="w-warn">🧹 Clean up strat map…</b> moves them out.':''}${
        dupes?` · ${dupes} duplicate block${dupes===1?'':'s'} share a name with another`:''}</span>
    </div>
    ${rows.length?`<div class="dblist">${rows.map(stmRow).join('')}</div>`
                 :'<div class="empty">No strat models match.</div>'}`;
  main.querySelectorAll('.dbrow').forEach(r=>r.onclick=()=>openStratEntry(r.dataset.name));
}
function stmRow(e){
  const use=e.unused?'<span class="w-warn">nothing references it</span>'
    :e.mentioned_in?`<span class="count">No character uses it. ${e.mentioned_in_lua
        ?'named by a <b class="w-good">Lua script</b>':'only named in'} <code>${esc(e.mentioned_in)}</code></span>`
    :`${esc(e.used_by.slice(0,4).join(', '))}${e.use_count>4?` +${e.use_count-4} more`:''}`;
  return `<div class="dbrow ${e.unused?'unused':''}" data-name="${esc(e.name)}">
    <span class="en">${esc(e.name)}</span>
    <span class="use">${use}</span>
    <span class="nums">${e.models} model${e.models===1?'':'s'} · ${e.skins} texture${
      e.skins===1?'':'s'}${e.missing.length?` · <span class="w-warn">${e.missing.length} not shipped</span>`:''}</span>
  </div>`;
}

/* One entry, read-only: the block exactly as the file stores it, and what each
   of its lines points at. Read-only on purpose — this tab exists to find what is
   dead, and a strat model is edited by editing eight tab-aligned lines, which a
   form would make worse rather than better. The block is here so you can check
   what you are about to remove without leaving the tool. */
async function openStratEntry(name){
  const modal=document.getElementById('modal');
  modal.className='modal wide'; modal.innerHTML='<h2>Loading…</h2>';
  overlay.classList.add('open');
  let r;
  try{ r=await api.get(`/api/stratmap/entry?mod=${enc(state.src)}&name=${enc(name)}`); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.innerHTML=`<h2>Strat model</h2><div class="mbody w-bad">${esc(r.error)}</div>
    <div class="foot"><button onclick="closeModal()">Close</button></div>`; return; }
  modal.innerHTML=`<h2>Strat model <span class="pill">${esc(state.src)}</span></h2>
    <div class="ehead">
      <div><div class="nm" style="font-family:ui-monospace,Consolas,monospace">${esc(r.name)}</div>
        <div class="count">${r.skeleton?`skeleton <code>${esc(r.skeleton)}</code> · `:''}line ${r.line}
          of <code>data/descr_model_strat.txt</code> ·
          ${r.used_by.length?`used by ${esc(r.used_by.slice(0,6).join(', '))}${
            r.used_by.length>6?` +${r.used_by.length-6}`:''}`
                            :'<span class="w-warn">referenced by nothing</span>'}</div></div>
    </div>
    <div class="mbody">
      <fieldset class="assetconf"><legend>The files it names</legend>
        <div class="flist">${r.files.map(f=>`<div class="frow">
          <span class="fp">${esc(f.rel)}</span>
          <span class="fs">${esc(f.kind)}${f.exists?'':' · <b class="w-warn">not in this mod</b>'}</span>
        </div>`).join('')||'<div class="count">none</div>'}</div>
        ${r.factions.length?`<div class="count" style="margin-top:6px">Texture factions:
          ${r.factions.map(f=>`<code>${esc(f)}</code>`).join(' ')}</div>`:''}
      </fieldset>
      <fieldset><legend>The block, as the file stores it</legend>
        <pre class="rawblock">${esc(r.raw)}</pre></fieldset>
    </div>
    <div class="foot"><button onclick="closeModal()">Close</button></div>`;
}

/* ======================= 🧹 CLEAN UP THE STRAT MAP =======================
   Same two questions the BMDB cleanup asks, on the other tree: which declared
   models nothing references, and which files under models_strat nothing names.
   Same contract too — everything ticked is MOVED to a folder outside the mod,
   in the mod's own layout, and every rewritten file is backed up first. */
async function openStratCleanup(){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  const job=newJob();
  let a;
  try{ a=await runJob(job,`Clean up ${esc(state.src)}’s strat map`,
        `Reading <code>descr_model_strat.txt</code>, every file that names one of its
         models, and every file under <code>data/models_strat</code>…`,
        ()=>api.get(`/api/stratmap/audit?mod=${enc(state.src)}&job=${enc(job)}`)); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>Clean up</h2><div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">Close</button></div>`; return; }
  const was=(state.strclean&&state.strclean.a&&state.strclean.a.mod===a.mod)?state.strclean:null;
  state.strclean={a,target:(was&&was.target)||state.settings.last_stratmap_target
                                            ||state.settings.last_cleanup_target||'',
    // unused: pre-ticked, they are dead by definition. Files: NOT pre-ticked —
    // a texture with no entry naming it is a likelier false positive than a
    // block with no character naming it, and this is the tick that frees the
    // megabytes, so it is the one worth reading first.
    entries:new Set(a.unused.map(u=>u.entry)),
    orphans:new Set(),
    open:(was&&was.open)||{unused:true,orphans:true},
    plan:null};
  resetPlace();
  renderStratCleanup();
}
function renderStratCleanup(){
  const c=state.strclean,a=c.a;
  const sec=(k,title,body)=>`<div class="clsec">
      <div class="h" onclick="stmToggle('${k}')"><span>${c.open[k]?'▾':'▸'}</span>
        <b>${title}</b><span class="count" id="stc_${k}">${stmCountText(k)}</span></div>
      ${c.open[k]?`<div class="b">${body()}</div>`:''}</div>`;
  document.getElementById('modal').innerHTML=`
    <h2>Clean up ${esc(a.mod)}’s strat map</h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:10px">${a.entry_count} model${
        a.entry_count===1?'':'s'} in <code>${esc(a.file)}</code> scanned, against ${a.scanned.length}
        game file${a.scanned.length===1?'':'s'} and ${a.lua_files} <code>.lua</code> script${
        a.lua_files===1?'':'s'}. Nothing is deleted: everything ticked is <b>moved</b> into the
        folder below, in the mod's own layout, so it can be pasted straight back. Undoable from 🕑 Log.</div>

      <fieldset><legend>Where the removed assets go</legend>
        <div class="cltarget">
          <input id="stmTarget" value="${esc(c.target)}"
            placeholder="e.g. D:\\M2TW backups\\${esc(a.mod)}_stratmap_unused"
            oninput="state.strclean.target=this.value;stmStale()">
          <button onclick="stmPickTarget()">Browse…</button>
        </div>
        <div class="treebox">${esc(a.mod)}_stratmap_unused\\
  removed_model_strat.txt         <span style="color:var(--dim)">only the blocks that were removed</span>
  data\\models_strat\\…             <span style="color:var(--dim)">their meshes and textures, same paths as in the mod</span>
  unused_files\\data\\models_strat\\… <span style="color:var(--dim)">files nothing names at all</span></div>
        <div class="count" style="margin-top:6px">Must be outside the mod, or the files never really leave it.</div>
      </fieldset>

      ${sec('unused','Strat models nothing references',()=>stmUnusedBody())}
      ${sec('orphans',`Files under ${esc(a.skipped_dir.split('/')[0])} no model names`,()=>stmOrphanBody())}

      ${stmLuaBox(a)}
      ${a.mentioned.length?`<div class="count">${a.mentioned.length} more model${
        a.mentioned.length===1?' is':'s are'} used by no character but named in another file
        (<code>${[...new Set(a.mentioned.map(m=>m.file))].slice(0,4).map(esc).join('</code>, <code>')}</code>).
        They are left alone.</div>`:''}
      ${a.held_file_count?`<div class="count">${a.held_file_count} file${
        a.held_file_count===1?' is':'s are'} named by no model, but their bare filename turns up in a
        <code>descr_*.txt</code> or a script — so they are not offered above either.</div>`:''}
      <div class="count"><code>${esc(a.skipped_dir)}</code> is skipped entirely: the game picks a
        faction's settlement variant out of that folder without any file naming it, so
        "nothing names it" would be wrong about every file in there.</div>
      <div id="stmPreview"></div>
    </div>
    <div class="foot">
      <button onclick="closeModal()">Close</button>
      <button onclick="stmPreview()">Probe</button>
      <button class="primary" onclick="stmApply()">Move them out</button>
    </div>`;
}
function stmUnusedBody(){
  const c=state.strclean,rows=c.a.unused;
  if(!rows.length)return '<div class="count" style="margin-top:8px">Nothing. Every model is referenced. 🎉</div>';
  return `<div class="count" style="margin-top:7px">No <code>strat_model</code> line in
      <code>descr_character.txt</code> names these, and nothing else in the mod mentions them.
      Their meshes and textures move out too, unless a model that stays also names them.</div>
    <div class="clbar">
      <button onclick="stmAll('entries',true)">Select all</button>
      <button onclick="stmAll('entries',false)">None</button></div>
    <div class="cllist">${rows.map(u=>`<div class="clrow">
      <input type="checkbox" ${c.entries.has(u.entry)?'checked':''}
        onchange="stmPick('entries','${q1(esc(u.entry))}',this.checked)">
      <div class="grow"><span class="nm">${esc(u.entry)}</span>
        ${u.skeleton?`<span class="badge">${esc(u.skeleton)}</span>`:''}
        <div class="sub">${u.models} model${u.models===1?'':'s'} · ${u.skins} texture${u.skins===1?'':'s'} ·
          ${u.files.length} file${u.files.length===1?'':'s'} named, ${u.on_disk} on disk</div></div>
      <span class="count">${MB(u.bytes)}</span>
    </div>`).join('')}</div>`;
}
function stmOrphanBody(){
  const c=state.strclean,rows=c.a.orphans;
  if(!rows.length)return '<div class="count" style="margin-top:8px">None. Every file under models_strat is named by something.</div>';
  return `<div class="count" style="margin-top:7px">Files sitting in <code>data/models_strat</code> that
      <b>nothing</b> in the mod names — not a model block, not a faction symbol, not a resource,
      not a script. They go to <code>unused_files\\</code> in the destination, paths mirrored.
      A <code>.tga</code> and the <code>.tga.dds</code> beside it count as one texture, so ticking
      one never leaves the other stranded.</div>
    <div class="clbar">
      <button onclick="stmAll('orphans',true)">Select all</button>
      <button onclick="stmAll('orphans',false)">None</button></div>
    <div class="cllist">${rows.map(o=>`<div class="clrow">
      <input type="checkbox" ${c.orphans.has(o.rel)?'checked':''}
        onchange="stmPick('orphans','${q1(esc(o.rel))}',this.checked)">
      <div class="grow"><span class="sub" style="margin:0">${esc(o.rel)}</span></div>
      <span class="count">${MB(o.size)}</span></div>`).join('')}</div>`;
}
/* The Lua safety net, said out loud for the same reason the BMDB dialog says it:
   an M2TWEOP script names a strat model by string and nothing in the mod's .txt
   files records that, so without this pass the cleanup would remove a model the
   campaign spawns and the break would only show up in game. */
function stmLuaBox(a){
  const kept=a.lua_kept||[], scanned=a.lua_files||0;
  if(!scanned) return '';
  if(!kept.length) return `<div class="count">Read <b>${scanned}</b> <code>.lua</code> script${
    scanned===1?'':'s'} in the mod. None of them names a strat model, so nothing was held back for that.</div>`;
  const rows=kept.slice(0,60).map(m=>`<div class="frow"><span class="fp">${esc(m.entry)}</span><span class="fs">${
    esc(m.file)}${m.in_comment?' (in a comment, and still protected)':''}</span></div>`).join('');
  return `<fieldset class="assetconf" style="margin-top:10px;border-color:var(--good)">
    <legend class="w-good">Protected by the mod's Lua scripts</legend>
    <div class="count"><b>${kept.length}</b> model${kept.length===1?' is':'s are'} named by one of this mod's
      <b>${scanned}</b> <code>.lua</code> script${scanned===1?'':'s'} and nothing else, so
      ${kept.length===1?'it is':'they are'} not offered for removal.</div>
    <div class="flist" style="margin-top:6px">${rows}${
      kept.length>60?`<div class="count">…and ${kept.length-60} more</div>`:''}</div>
  </fieldset>`;
}
function stmCountText(k){
  const c=state.strclean,a=c.a;
  if(k==='unused'){
    const bytes=a.unused.reduce((n,u)=>n+(c.entries.has(u.entry)?u.bytes:0),0);
    return `${c.entries.size}/${a.unused.length} ticked · ${MB(bytes)}`;
  }
  const bytes=a.orphans.reduce((n,o)=>n+(c.orphans.has(o.rel)?o.size:0),0);
  return `${c.orphans.size}/${a.orphans.length} ticked · ${MB(bytes)}`;
}
function stmCounts(){['unused','orphans'].forEach(k=>{
  const el=document.getElementById('stc_'+k); if(el)el.textContent=stmCountText(k);});}
// The checkbox already shows its own new state, so only the header count needs
// touching — that keeps ticking one of 600 rows instant.
function stmPick(key,id,on){const s=state.strclean[key]; on?s.add(id):s.delete(id);
  stmStale(); stmCounts();}
function stmAll(key,on){
  const c=state.strclean;
  const all=key==='entries'?c.a.unused.map(u=>u.entry):c.a.orphans.map(o=>o.rel);
  c[key]=new Set(on?all:[]);
  const head=document.getElementById('stc_'+(key==='entries'?'unused':key));
  if(head)head.closest('.clsec').querySelectorAll('.cllist input[type=checkbox]')
    .forEach(cb=>{cb.checked=on;});
  stmStale(); stmCounts();
}
function stmToggle(k){state.strclean.open[k]=!state.strclean.open[k];renderStratCleanup();}
function stmStale(){const b=document.getElementById('stmPreview');
  if(b&&state.strclean.plan){state.strclean.plan=null;b.innerHTML='';}}
async function stmPickTarget(){
  const r=await api.post('/api/browse_folder',{title:'Folder to move the unused strat-map assets into'});
  if(!r.path)return;
  state.strclean.target=r.path; stmStale(); renderStratCleanup();
  state.settings.last_stratmap_target=r.path;
  api.post('/api/settings',{last_stratmap_target:r.path});
}
function stmPayload(){
  const c=state.strclean;
  return {mod:c.a.mod,target:c.target,
    entries:[...c.entries],orphans:[...c.orphans]};
}
async function stmPreview(){
  const box=document.getElementById('stmPreview'); if(!box)return null;
  box.innerHTML='<div class="preview">Planning…</div>';
  const r=await api.post('/api/stratmap/cleanup_plan',stmPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.strclean.plan=r;
  box.innerHTML=clPlanHtml(r); return r;
}
async function stmApply(){
  const c=state.strclean;
  if(!c.target){toast('Choose where the removed assets should go first');return;}
  const r=state.strclean.plan||await stmPreview();
  if(!r)return;
  if(r.errors&&r.errors.length){toast(r.errors[0]);return;}
  if(!r.entry_deletes.length&&!r.export_count){toast('Nothing is ticked');return;}
  if(!confirm(`Move ${r.entry_deletes.length} strat model${r.entry_deletes.length===1?'':'s'} `+
      `and ${r.export_count} file(s) out of “${c.a.mod}”?\n\nThey are copied to:\n${r.target}\n\n`+
      `Everything touched is backed up first. 🕑 Log → Undo puts it all back.`))return;
  const job=newJob();
  const res=await runJob(job,'Cleaning up the strat map…',
    `Copying ${r.export_count} file(s) out, then rewriting ${esc(c.a.mod)}’s
     <code>descr_model_strat.txt</code>. Everything is backed up as it goes.`,
    ()=>api.post('/api/stratmap/cleanup_apply',{...stmPayload(),job}));
  if(res.error){toast('Cleanup failed: '+res.error);renderStratCleanup();return;}
  toast(`Removed ${res.plan.entry_deletes.length} strat model(s) and `+
        `${res.plan.export_count} file(s) ✓  (undo in 🕑 Log)`,5200);
  // The lists in this dialog were built from an audit taken BEFORE the cleanup,
  // so the mod on disk has changed and the answer on screen has to change with
  // it — re-run rather than leave stale rows up inviting a second tick.
  state.stm=null;
  loadStratmap();
  await openStratCleanup();
}
