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
  modal.innerHTML=`<h2>Duplicate entries</h2><div class="mbody">Reading
    <code>battle_models.modeldb</code>…</div>`;
  let a;
  try{ a=await api.get(`/api/bmdb/dupes?mod=${enc(state.src)}`); }
  catch(e){ a={error:''+e}; }
  if(a.error){ modal.innerHTML=`<h2>Duplicate entries</h2>
    <div class="mbody w-bad">${esc(a.error)}</div>
    <div class="foot"><button onclick="closeModal()">Close</button></div>`; return; }
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
    <h2>Duplicate entries in ${esc(a.mod)}’s battle_models.modeldb</h2>
    <div class="mbody">
      ${n?`<div class="count" style="margin-bottom:10px">
        <b>${n}</b> name${n===1?'':'s'} appear${n===1?'s':''} more than once, which is
        <b>${x}</b> entry block${x===1?'':'s'} (${dupBytes(a.extra_bytes)}) the game never reads.
        M2TW takes the <b>first</b> block with a name and ignores the rest, so every unit
        that names one of these gets the first block's meshes, skins and animations.
        A later block is a model the mod is carrying and cannot reach.</div>

      <div class="count" style="margin-bottom:10px">Two ways out, per block:
        <b>Rename</b> gives it a name of its own so a unit can be pointed at it, and
        <b>Remove</b> drops it. Only the modeldb is written, it is backed up first,
        and 🕑 Log → Undo puts it back.</div>

      <div class="clbar">
        <button onclick="dupAll('remove',true)">Remove every exact copy</button>
        <button onclick="dupAll('rename',false)">Rename every different one</button>
        <button onclick="dupAll('',null)">Clear</button></div>

      ${a.rows.map(dupRowHtml).join('')}
      <div id="dupPreview"></div>`
      :`<div class="sum" style="margin-top:10px"><div class="srow">
          <span class="sicon">✓</span><span class="stext">No name appears twice. All
          <b>${a.entry_count}</b> entry blocks in the file are reachable.</span></div></div>`}
    </div>
    <div class="foot">
      <button onclick="closeModal()">Close</button>
      ${n?`<button onclick="dupPreview()">Probe</button>
      <button class="primary" onclick="dupApply()">Apply</button>`:''}
    </div>`;
}
const dupBytes=n=>n<1024?`${n} bytes`:n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(1)} MB`;

/* One name. The first block is a row like the others but with no controls on
   it, because seeing WHAT the game reads is half of deciding what to do with
   the rest, and hiding it would leave the later blocks looking like the only
   things in the file. */
function dupRowHtml(r){
  return `<fieldset style="margin-top:10px">
    <legend><code>${esc(r.name)}</code> · ${r.copies} blocks${
      r.identical?' · identical':''}</legend>
    <div class="count">${r.used_by
      ? `Used as ${esc(r.used_by)} - all of which resolve to the first block below.`
      : 'No unit, mount or character names this entry, so the game reads none of these blocks today.'}</div>
    ${r.blocks.map(b=>dupBlockHtml(r,b)).join('')}
  </fieldset>`;
}

function dupBlockHtml(r,b){
  const s=state.dup;
  const pick=s.picks[b.index]||'';
  const what=b.first
    ? '<b class="w-good">the block the game reads</b>'
    : b.identical
      ? '<b>an exact copy of it</b> - removing this loses nothing'
      : `<b class="w-warn">a different model</b>: ${esc(b.differs.join('; '))}`;
  const facts=`line ${b.line} · ${b.lods} LOD${b.lods===1?'':'s'} · ${b.skins} skin${
    b.skins===1?'':'s'} · ${b.files.length} file${b.files.length===1?'':'s'}, ${
    b.on_disk} of them in the mod`;
  if(b.first) return `<div class="clrow"><span class="stext">
      <b>#${b.ordinal}</b> ${what}<br><span class="count">${facts}</span></span></div>`;
  return `<div class="clrow"><span class="stext">
      <b>#${b.ordinal}</b> ${what}<br><span class="count">${facts}</span>
      <div class="clbar" style="margin-top:6px">
        <label><input type="radio" name="dup${b.index}" ${pick?'':'checked'}
          onchange="dupPick(${b.index},'')"> Leave it</label>
        <label><input type="radio" name="dup${b.index}" ${pick==='rename'?'checked':''}
          onchange="dupPick(${b.index},'rename')"> Rename to</label>
        <input style="width:220px" value="${esc(s.names[b.index]||'')}"
          oninput="dupName(${b.index},this.value)"
          onfocus="dupPick(${b.index},'rename')">
        <label><input type="radio" name="dup${b.index}" ${pick==='remove'?'checked':''}
          onchange="dupPick(${b.index},'remove')"> Remove it</label>
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
  if(!dupCount()){box.innerHTML='<div class="preview">Nothing is ticked.</div>';return null;}
  box.innerHTML='<div class="preview">Planning…</div>';
  const r=await api.post('/api/bmdb/dupes_plan',dupPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  box.innerHTML=dupPlanHtml(r.plan); return r;
}
function dupPlanHtml(p){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">🧬</span><span class="stext">What this writes</span></div>
    ${li('',p.changes)}${li('warn',p.warnings)}${li('bad',p.errors)}</div>`;
}

async function dupApply(){
  const r=await dupPreview();
  if(!r)return;
  if(r.plan.errors&&r.plan.errors.length){toast(r.plan.errors[0]);return;}
  const rm=r.removes.length,rn=r.renames.length;
  const lost=r.removes.filter(x=>!x.identical).length;
  if(!confirm(`Rewrite “${state.dup.a.mod}”’s battle_models.modeldb?\n\n`+
      `${rn?`${rn} block(s) renamed - each becomes a real entry that nothing names yet.\n`:''}`+
      `${rm?`${rm} block(s) removed.\n`:''}`+
      `${lost?`\n${lost} of the removed block(s) is NOT a copy of the entry the game reads, so a model goes with it.\n`:''}`+
      `\nThe file is backed up first. 🕑 Log → Undo puts it back.`))return;
  const res=await api.post('/api/bmdb/dupes_apply',dupPayload());
  if(res.error){toast('Failed: '+res.error);return;}
  if(res.plan&&res.plan.errors&&res.plan.errors.length){toast(res.plan.errors[0]);return;}
  toast(`${res.renamed} renamed, ${res.removed} removed ✓  (undo in 🕑 Log)`,5200);
  state.bmdb=null; state.destData=null;
  // The rows on screen were read BEFORE the write, and their block indices are
  // exactly what a rewrite of the file invalidates. So the scan is re-run here
  // rather than left to whoever reopens the dialog.
  loadSource();
  await openDupes();
}
