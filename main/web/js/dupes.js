/* ============ DUPLICATE MODEL ENTRIES: the blocks the game never reads ============

   `battle_models.modeldb` is a flat stream of entry blocks and nothing in the
   format stops the same name appearing twice. The engine reads the FIRST block
   with a name and walks past every later one, so a second block is a model the
   mod is carrying and cannot reach, with nothing anywhere saying so. Third Age
   Reforged ships eight such names; Divide and Conquer five.

   The BMDB list already puts a ×2 badge on a duplicated name. This is what the
   badge is for: one row per name, the block the game reads shown first and
   locked, and each later block offered the only two things worth doing to it.

     Rename   it stops being dead and becomes an entry a unit can be pointed at
     Remove   it goes, and the file shrinks by that block

   Which of those is right depends entirely on whether the later block is a copy
   of the first or a different model, so that is the loudest thing on each row -
   an identical copy says so and costs nothing to drop, and a different one is
   listed field by field ("skins for 5 factions vs 3") so the choice is made
   against what is actually in the file rather than a guess.

   Nothing here touches an asset. The only file written is the modeldb, backed
   up first and undoable from 🕑 Log like every other write in the tool. */

async function openDupes(){
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  overlay.classList.add('open');
  modal.innerHTML=`<h2>${tt('dupes.duplicate_entries')}</h2><div class="mbody">${tt('dupes.reading_battle_models_modeldb')}</div>`;
  let a;
  try{ a=await api.get(`/api/bmdb/dupes?mod=${enc(state.src)}`); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>${tt('dupes.duplicate_entries')}</h2>
    <div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  // `picks` is keyed by the block's index in the file, which is the only thing
  // that tells two blocks of the same name apart. Nothing is pre-ticked: one
  // choice removes a model and the other invents a name, and neither is a
  // default anybody should get by not reading the row.
  state.dup={a,picks:{},names:{}};
  a.rows.forEach(r=>r.blocks.forEach(b=>{ if(!b.first) state.dup.names[b.index]=b.suggested; }));
  renderDupes();
}

const dupCount=()=>Object.values(state.dup.picks).filter(Boolean).length;

function renderDupes(){
  const s=state.dup,a=s.a;
  const n=a.duplicated,x=a.extra_blocks;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('dupes.duplicate_entries_in_s_battle_models',{mod:esc(a.mod)})}</h2>
    <div class="mbody">
      ${n?`<div class="count" style="margin-bottom:10px">
        ${tt('dupes.names_repeated_blocks_never_read',{names:ttN('dupes.names_appear_more_than_once',n),blocks:ttN('dupes.extra_entry_blocks',x),size:dupBytes(a.extra_bytes)})}</div>

      <div class="count" style="margin-bottom:10px">${tt('dupes.two_ways_out_per_block_rename')}</div>

      <div class="clbar">
        <button onclick="dupAll('remove',true)">${tt('dupes.remove_every_exact_copy')}</button>
        <button onclick="dupAll('rename',false)">${tt('dupes.rename_every_different_one')}</button>
        <button onclick="dupAll('',null)">${tt('common.clear')}</button></div>

      ${a.rows.map(dupRowHtml).join('')}
      <div id="dupPreview"></div>`
      :`<div class="sum" style="margin-top:10px"><div class="srow">
          <span class="sicon">✓</span><span class="stext">${tt('dupes.no_name_appears_twice_all_entry',{entry_count:a.entry_count})}</span></div></div>`}
    </div>
    <div class="foot">
      <button onclick="closeModal()">${tt('common.close')}</button>
      ${n?`<button onclick="dupPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="dupApply()">${tt('common.apply')}</button>`:''}
    </div>`;
}
const dupBytes=n=>n<1024?tt('dupes.size_bytes',{n}):n<1048576?tt('dupes.size_kb',{n:(n/1024).toFixed(1)}):tt('dupes.size_mb',{n:(n/1048576).toFixed(1)});

/* One name. The first block is a row like the others but with no controls on
   it, because seeing WHAT the game reads is half of deciding what to do with
   the rest, and hiding it would leave the later blocks looking like the only
   things in the file. */
function dupRowHtml(r){
  return `<fieldset style="margin-top:10px">
    <legend><code>${esc(r.name)}</code> ${tt('dupes.blocks',{copies:r.copies,identical:r.identical?tt('dupes.identical'):''})}</legend>
    <div class="count">${r.used_by
      ? tt('dupes.used_as_all_of_which_resolve',{used_by:esc(r.used_by)})
      : tt('dupes.no_unit_mount_or_character_names')}</div>
    ${r.blocks.map(b=>dupBlockHtml(r,b)).join('')}
  </fieldset>`;
}

function dupBlockHtml(r,b){
  const s=state.dup;
  const pick=s.picks[b.index]||'';
  const what=b.first
    ? `<b class="w-good">${tt('dupes.the_block_the_game_reads')}</b>`
    : b.identical
      ? tt('dupes.an_exact_copy_of_it_removing')
      : tt('dupes.a_different_model',{differs:esc(b.differs.join('; '))});
  const facts=tt('dupes.line_lods_skins_files_on_disk',{line:b.line,lods:ttN('dupes.lod_count',b.lods),skins:ttN('dupes.skin_count',b.skins),files:ttN('dupes.file_count',b.files.length),on_disk:b.on_disk});
  if(b.first) return `<div class="clrow"><span class="stext">
      <b>#${b.ordinal}</b> ${what}<br><span class="count">${facts}</span></span></div>`;
  return `<div class="clrow"><span class="stext">
      <b>#${b.ordinal}</b> ${what}<br><span class="count">${facts}</span>
      <div class="clbar" style="margin-top:6px">
        <label><input type="radio" name="dup${b.index}" ${pick?'':'checked'}
          onchange="dupPick(${b.index},'')"> ${tt('dupes.leave_it')}</label>
        <label><input type="radio" name="dup${b.index}" ${pick==='rename'?'checked':''}
          onchange="dupPick(${b.index},'rename')"> ${tt('dupes.rename_to')}</label>
        <input style="width:220px" value="${esc(s.names[b.index]||'')}"
          oninput="dupName(${b.index},this.value)"
          onfocus="dupPick(${b.index},'rename')">
        <label><input type="radio" name="dup${b.index}" ${pick==='remove'?'checked':''}
          onchange="dupPick(${b.index},'remove')"> ${tt('dupes.remove_it')}</label>
      </div></span></div>`;
}

function dupPick(index,what){
  state.dup.picks[index]=what;
  dupStale();
  renderDupes();
}
/* The name box does NOT re-render: typing in it would lose the caret on every
   keystroke. It only has to keep the value the payload reads. */
function dupName(index,v){ state.dup.names[index]=v.trim().toLowerCase(); dupStale(); }
function dupStale(){const b=document.getElementById('dupPreview'); if(b)b.innerHTML='';}

/* The two bulk buttons are the two decisions people actually arrive with: "drop
   everything that is only a copy" and "keep everything that is a real model". */
function dupAll(what,identical){
  const s=state.dup;
  s.picks={};
  if(what) s.a.rows.forEach(r=>r.blocks.forEach(b=>{
    if(!b.first && b.identical===identical) s.picks[b.index]=what; }));
  dupStale();
  renderDupes();
}

function dupPayload(){
  const s=state.dup;
  return {mod:s.a.mod, actions:Object.entries(s.picks)
    .filter(([,w])=>w)
    .map(([i,w])=>({index:+i, action:w, new_name:s.names[i]||''}))};
}

async function dupPreview(){
  const box=document.getElementById('dupPreview'); if(!box)return null;
  if(!dupCount()){box.innerHTML=`<div class="preview">${tt('dupes.nothing_is_ticked')}</div>`;return null;}
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/bmdb/dupes_plan',dupPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  box.innerHTML=dupPlanHtml(r.plan); return r;
}
function dupPlanHtml(p){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">🧬</span><span class="stext">${tt('common.what_this_writes')}</span></div>
    ${li('',p.changes)}${li('warn',p.warnings)}${li('bad',p.errors)}</div>`;
}

async function dupApply(){
  const r=await dupPreview();
  if(!r)return;
  if(r.plan.errors&&r.plan.errors.length){toast(r.plan.errors[0]);return;}
  const rm=r.removes.length,rn=r.renames.length;
  const lost=r.removes.filter(x=>!x.identical).length;
  if(!confirm(tt('dupes.rewrite_confirm',{mod:state.dup.a.mod,
      renamed:rn?tt('dupes.block_s_renamed_each_becomes_a',{rn}):'',
      removed:rm?tt('dupes.block_s_removed',{rm}):'',
      lost:lost?tt('dupes.of_the_removed_block_s_is',{lost}):''})))return;
  const res=await api.post('/api/bmdb/dupes_apply',dupPayload());
  if(res.error){toast(tt('dupes.failed_error',{error:res.error}));return;}
  if(res.plan&&res.plan.errors&&res.plan.errors.length){toast(res.plan.errors[0]);return;}
  toast(tt('dupes.renamed_removed_undo_in_log',{renamed:res.renamed,removed:res.removed}),5200);
  state.bmdb=null; state.destData=null;
  // The rows on screen were read BEFORE the write, and their block indices are
  // exactly what a rewrite of the file invalidates. So the scan is re-run here
  // rather than left to whoever reopens the dialog.
  loadSource();
  await openDupes();
}
