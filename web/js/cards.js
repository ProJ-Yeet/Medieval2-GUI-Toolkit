/* cards.js — Unit cards tab: the two pictures a unit has, deduplicated

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html — there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   UNIT AND INFO CARDS — one picture, thirty folders.

   The game finds a unit's card under the PLAYER's faction folder, so a unit
   thirty factions can field needs its card in thirty of them. Mods do exactly
   that, byte for byte, and it is where the disk goes: Divide and Conquer ships
   1.2 GB of info cards for 917 units. The engine also falls back to the merc
   folder for any unit whose own faction folder has nothing — which is where one
   copy can do the job of thirty.

   So this tab is three questions, per kind of card:

     * whose art is for a unit that is GONE — a dictionary no unit claims;
     * which are the SAME picture in several folders — one hash, nothing to
       decide, fold them into the merc folder;
     * which really DIFFER per faction — the tool will not choose between two
       pictures a mod deliberately ships, so those are shown side by side and
       the pick is yours, "leave them alone" included.

   Everything ticked is MOVED to a folder outside the mod, backed up first and
   undoable from 🕑 Log — the same contract the other two cleaners make. It is a
   page rather than a dialog because choosing between card variants is reading
   work, and reading work does not belong in a modal.
   ===================================================================== */
const CARD_KIND_ICON={card:'🃏',info:'🖼'};

async function loadCards(){
  const mod=state.src;
  const job=newJob();
  main.innerHTML=bmdbTabsHtml('data/ui/units · data/ui/unit_info')+
    `<div class="empty" style="max-width:460px;margin:60px auto">
      <div class="progress-track"><div class="progress-fill" id="jobFill" style="width:0%"></div></div>
      <div class="count" style="margin-top:8px"><b id="jobPct">0%</b>
        <span id="jobStep">reading ${esc(mod)}’s cards…</span></div>
      <div class="count" style="margin-top:10px">Every card is hashed, so “the same picture”
        is a fact rather than a guess. A mod with four thousand info cards takes a moment.</div>
    </div>`;
  state.cardsJob=job;
  (async()=>{ while(state.cardsJob===job){
    await new Promise(r=>setTimeout(r,300));
    if(state.cardsJob!==job)break;
    let p=null; try{p=await api.get('/api/progress?job='+enc(job),1);}catch(e){}
    if(state.cardsJob===job&&p&&typeof p.pct==='number')jobPaint(p.pct,p.label||'');
  }})();
  let a;
  try{ a=await api.get(`/api/cards/audit?mod=${enc(mod)}&job=${enc(job)}`); }
  catch(e){ state.cardsJob=null; if(stale('cards',mod))return;
    main.innerHTML=bmdbTabsHtml('')+`<div class="empty">Couldn't read the cards.<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadCards()">Retry</button></div>`; return; }
  finally{ state.cardsJob=null; }
  if(stale('cards',mod))return;
  // What was typed into the folder box and which sections were unfolded survive
  // a re-audit; only the LISTS are replaced.
  const was=(state.cards&&state.cards.a&&state.cards.a.mod===a.mod)?state.cards:null;
  state.cards={a,
    target:(was&&was.target)||state.settings.last_cards_target
                            ||state.settings.last_cleanup_target||'',
    // Gone and duplicated are pre-ticked: both are facts, not judgements. The
    // variant sets are not — every one of them is a question.
    pick:Object.fromEntries(a.kinds.map(k=>[k.kind,{
      remove:new Set(k.unused.map(u=>u.name)),
      cons:new Set(k.duplicates.map(d=>d.name)),
      choose:{}}])),
    open:(was&&was.open)||{},
    plan:null};
  renderCards();
}

const cdKind=key=>state.cards.a.kinds.find(k=>k.kind===key);
const cdPick=key=>state.cards.pick[key];

/* The toolbar's search box, applied to every list on this page.

   Filtering rather than ignoring it, because a mod's info cards run to six
   hundred rows and finding one unit among them by scrolling is not finding it.
   The header counts stay whole-list — a tick is a tick whether or not the row it
   is on is on screen — while "Select all" follows what you can see, which is the
   only reading of it that is not a trap while a filter is up. */
const cdQuery=()=>search.value.trim().toLowerCase();
const cdMatch=(row,q)=>!q||row.name.toLowerCase().includes(q)
  ||(row.unit||'').toLowerCase().includes(q)
  ||(row.folders||[]).some(f=>f.toLowerCase().includes(q));
const cdRows=(list)=>{const q=cdQuery(); return list.filter(r=>cdMatch(r,q));};
const cdShownNote=(shown,all)=>shown.length===all.length?''
  :`<div class="count" style="margin-top:6px">${shown.length} of ${all.length} shown —
     the rest are filtered out by the search box, and stay as they are.</div>`;

function renderCards(){
  if(!state.cards||state.cards.a.mod!==state.src)return loadCards();
  const c=state.cards,a=c.a;
  count.textContent=`${a.kinds.reduce((n,k)=>n+k.file_count,0)} files`;
  main.innerHTML=bmdbTabsHtml('data/ui/units · data/ui/unit_info')+`
    <div class="dbhead">
      <h2>${esc(a.mod)} · unit and info cards</h2>
      <span class="count">${a.units} unit${a.units===1?'':'s'} in the mod ·
        ${a.kinds.map(k=>`${k.file_count} ${esc(k.label)}${k.file_count===1?'':'s'}`).join(' · ')} ·
        <b>${MB(cdFreeable())}</b> could stop shipping</span>
    </div>
    <div class="cardsbody">
      <fieldset><legend>Where the removed cards go</legend>
        <div class="cltarget">
          <input id="cdTarget" value="${esc(c.target)}"
            placeholder="e.g. D:\\M2TW backups\\${esc(a.mod)}_cards"
            oninput="state.cards.target=this.value;cdStale()">
          <button onclick="cdPickTarget()">Browse…</button>
        </div>
        <div class="count" style="margin-top:6px">Must be outside the mod. Nothing is deleted:
          every file moves there in the mod's own layout, and 🕑 Log → Undo puts it all back.</div>
      </fieldset>
      ${a.kinds.map(cdKindHtml).join('')}
      <div id="cdPreview"></div>
      <div class="cardsfoot">
        <span class="count" id="cdTally">${cdTally()}</span>
        <span style="flex:1"></span>
        <button onclick="cdPreview()">Probe</button>
        <button class="primary" onclick="cdApply()">Move them out</button>
      </div>
    </div>`;
}

/* How much this mod would stop shipping if everything currently ticked went.
   Recomputed rather than remembered: it is the number the whole page is for. */
function cdFreeable(){
  return state.cards.a.kinds.reduce((n,k)=>{
    const p=cdPick(k.kind);
    return n
      + k.unused.reduce((m,u)=>m+(p.remove.has(u.name)?u.bytes:0),0)
      + k.duplicates.reduce((m,d)=>m+(p.cons.has(d.name)?d.bytes_saved:0),0)
      + k.variants.reduce((m,v)=>m+(p.choose[v.name]?v.bytes_saved:0),0);
  },0);
}
function cdTally(){
  const parts=state.cards.a.kinds.map(k=>{
    const p=cdPick(k.kind);
    const n=p.remove.size+p.cons.size+Object.keys(p.choose).length;
    return `${n} ${esc(k.label)}${n===1?'':'s'}`;
  });
  return `${parts.join(' · ')} · frees ${MB(cdFreeable())}`;
}
function cdRefreshTally(){
  const el=document.getElementById('cdTally'); if(el)el.textContent=cdTally();
  ['unused','dups','vars'].forEach(g=>state.cards.a.kinds.forEach(k=>{
    const h=document.getElementById(`cdc_${k.kind}_${g}`);
    if(h)h.textContent=cdSectionCount(k,g);
  }));
}

function cdKindHtml(k){
  const sec=(g,title,body)=>{
    const key=k.kind+'_'+g, open=!!state.cards.open[key];
    return `<div class="clsec">
      <div class="h" onclick="cdToggle('${key}')"><span>${open?'▾':'▸'}</span>
        <b>${title}</b><span class="count" id="cdc_${esc(key)}">${cdSectionCount(k,g)}</span></div>
      ${open?`<div class="b">${body()}</div>`:''}</div>`;
  };
  return `<section class="cardkind">
    <h3>${CARD_KIND_ICON[k.kind]||'🖼'} ${esc(k.label)}s <span class="count">
      <code>data/${esc(k.base)}/&lt;faction&gt;/</code> · falls back to
      <code>${esc(k.merc)}</code> · ${k.dictionaries} unit${k.dictionaries===1?'':'s'} have one,
      in ${k.file_count} file${k.file_count===1?'':'s'} (${MB(k.bytes)})${
      k.already?` · ${k.already} already live only in <code>${esc(k.merc)}</code>`:''}</span></h3>
    ${sec('unused','For units that are gone',()=>cdUnusedBody(k))}
    ${sec('dups','The same picture in several folders',()=>cdDupBody(k))}
    ${sec('vars','Different pictures per faction — your call',()=>cdVarBody(k))}
    ${cdNotesHtml(k)}
  </section>`;
}
function cdSectionCount(k,g){
  const p=cdPick(k.kind);
  if(g==='unused'){
    const b=k.unused.reduce((n,u)=>n+(p.remove.has(u.name)?u.bytes:0),0);
    return `${p.remove.size}/${k.unused.length} ticked · ${MB(b)}`;
  }
  if(g==='dups'){
    const b=k.duplicates.reduce((n,d)=>n+(p.cons.has(d.name)?d.bytes_saved:0),0);
    return `${p.cons.size}/${k.duplicates.length} ticked · ${MB(b)}`;
  }
  const n=Object.keys(p.choose).length;
  const b=k.variants.reduce((m,v)=>m+(p.choose[v.name]?v.bytes_saved:0),0);
  return `${n}/${k.variants.length} chosen · ${MB(b)} · needs your eye`;
}

function cdUnusedBody(k){
  const p=cdPick(k.kind);
  if(!k.unused.length)return '<div class="count" style="margin-top:8px">None. Every card belongs to a unit that still exists. 🎉</div>';
  const rows=cdRows(k.unused);
  return `<div class="count" style="margin-top:7px">No unit in
      <code>export_descr_unit.txt</code> (or in an M2TWEOP unit file) has these as its
      <code>dictionary</code>, so nothing in the game can ever reach the art.</div>
    ${cdShownNote(rows,k.unused)}
    <div class="clbar">
      <button onclick="cdAll('${k.kind}','remove',true)">Select all</button>
      <button onclick="cdAll('${k.kind}','remove',false)">None</button></div>
    <div class="cllist">${rows.map(u=>`<div class="clrow">
      <input type="checkbox" ${p.remove.has(u.name)?'checked':''}
        onchange="cdPickOne('${k.kind}','remove','${q1(esc(u.name))}',this.checked)">
      <img class="cdthumb" loading="lazy" onerror="this.style.visibility='hidden'"
        src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(u.showing)}" alt="">
      <div class="grow"><span class="nm">${esc(u.name)}</span>
        <div class="sub">${u.folders.length} folder${u.folders.length===1?'':'s'}:
          ${esc(u.folders.slice(0,8).join(', '))}${u.folders.length>8?` +${u.folders.length-8}`:''}</div></div>
      <span class="count">${MB(u.bytes)}</span></div>`).join('')}</div>`;
}

function cdDupBody(k){
  const p=cdPick(k.kind);
  if(!k.duplicates.length)return '<div class="count" style="margin-top:8px">None — no card is copied into more than one folder.</div>';
  const rows=cdRows(k.duplicates);
  return `<div class="count" style="margin-top:7px">Every copy of these is byte for byte the
      same file. One goes to <code>data/${esc(k.base)}/${esc(k.merc)}/</code>, which is where the
      game looks when a faction's own folder has nothing, and the rest move out.</div>
    ${cdShownNote(rows,k.duplicates)}
    <div class="clbar">
      <button onclick="cdAll('${k.kind}','cons',true)">Select all</button>
      <button onclick="cdAll('${k.kind}','cons',false)">None</button></div>
    <div class="cllist">${rows.map(d=>`<div class="clrow">
      <input type="checkbox" ${p.cons.has(d.name)?'checked':''}
        onchange="cdPickOne('${k.kind}','cons','${q1(esc(d.name))}',this.checked)">
      <img class="cdthumb" loading="lazy" onerror="this.style.visibility='hidden'"
        src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(d.options[0].rel)}" alt="">
      <div class="grow"><span class="nm">${esc(d.name)}</span>
        <span class="badge">${esc(d.unit)}</span>
        <div class="sub">${d.folders.length} identical cop${d.folders.length===1?'y':'ies'}:
          ${esc(d.folders.slice(0,8).join(', '))}${d.folders.length>8?` +${d.folders.length-8}`:''}${
          d.options[0].in_merc?' — one of them is already the merc copy':''}</div></div>
      <span class="count">−${MB(d.bytes_saved)}</span></div>`).join('')}</div>`;
}

/* The one part of this page that is a question rather than a fact. Each row is a
   unit whose factions really do hold DIFFERENT pictures; the tool shows them
   side by side and takes no view. "Keep all" is the default and stays selected
   until you say otherwise — silently collapsing a mod's per-faction art into one
   picture is exactly the thing this must not do on its own. */
function cdVarBody(k){
  const p=cdPick(k.kind);
  if(!k.variants.length)return '<div class="count" style="margin-top:8px">None — where a card is in several folders, every copy is the same picture.</div>';
  const rows=cdRows(k.variants);
  return `<div class="count" style="margin-top:7px">These units have <b>different</b> cards in
      different faction folders. Pick the one that should become the single copy in
      <code>${esc(k.merc)}</code> — the others move out — or leave the set as it is.
      Nothing here is ticked for you.</div>
    ${cdShownNote(rows,k.variants)}
    <div class="clbar">
      <button onclick="cdVarAll('${k.kind}',false)">Keep all as they are</button>
      <button onclick="cdVarAll('${k.kind}',true)" title="Choose the picture the most folders
already share, for every row at once. Read them first.">Take the commonest, everywhere</button></div>
    <div class="cllist vars">${rows.map(v=>`<div class="clrow varrow">
      <div class="grow"><span class="nm">${esc(v.name)}</span>
        <span class="badge">${esc(v.unit)}</span>
        <span class="count">${v.options.length} different pictures across ${v.folders.length} folders</span>
        <div class="varopts">
          <label class="varopt${p.choose[v.name]?'':' on'}">
            <input type="radio" name="cdv_${esc(k.kind)}_${esc(v.name)}"
              ${p.choose[v.name]?'':'checked'}
              onchange="cdChoose('${k.kind}','${q1(esc(v.name))}','')">
            <span class="varkeep">keep<br>all ${v.options.length}</span></label>
          ${v.options.map(o=>`<label class="varopt${p.choose[v.name]===o.digest?' on':''}">
            <input type="radio" name="cdv_${esc(k.kind)}_${esc(v.name)}"
              ${p.choose[v.name]===o.digest?'checked':''}
              onchange="cdChoose('${k.kind}','${q1(esc(v.name))}','${esc(o.digest)}')">
            <img loading="lazy" onerror="this.style.visibility='hidden'"
              src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(o.rel)}" alt="">
            <span class="count">${esc(o.folders.slice(0,3).join(', '))}${
              o.folders.length>3?` +${o.folders.length-3}`:''}${
              o.in_merc?' ·&nbsp;merc':''}</span></label>`).join('')}
        </div></div>
      <span class="count">−${MB(v.bytes_saved)}</span></div>`).join('')}</div>`;
}

/* Everything this pass deliberately did not touch, said out loud. Each of these
   is a place where "unused" would have been a guess, and the whole value of the
   page is that it never guesses about art it is about to delete. */
function cdNotesHtml(k){
  const bits=[];
  if(k.stray_count)bits.push(`${k.stray_count} file${k.stray_count===1?'':'s'} in these folders
    ${k.stray_count===1?'is':'are'} not shaped like a ${esc(k.label)} (the agent pictures —
    <code>spy.tga</code>, <code>diplomat.tga</code> — and whatever else has been dropped in there,
    ${MB(k.stray_bytes)}). Their names say nothing about which unit they belong to, so they are
    counted and left alone.`);
  if(k.pinned.length)bits.push(`${k.pinned.length} unit${k.pinned.length===1?'':'s'} pin their
    ${esc(k.label)} to a folder with <code>${k.kind==='card'?'card_pic_dir':'info_pic_dir'}</code>.
    A pin is the mod saying “look here”, so those are left out of the consolidation.`);
  if(k.lua_kept.length)bits.push(`${k.lua_kept.length} ${esc(k.label)}${
    k.lua_kept.length===1?'':'s'} belong to a dictionary no unit claims, but which one of the mod's
    <code>.lua</code> scripts names — M2TWEOP can build a unit at runtime, so
    ${k.lua_kept.length===1?'it is':'they are'} not offered for removal.`);
  return bits.length?`<div class="count cardnotes">${bits.map(b=>`<div>· ${b}</div>`).join('')}</div>`:'';
}

/* ---- picking ----
   Only the header counts and the footer tally are repainted on a tick: a mod's
   info cards run to 700 rows with a thumbnail each, and rebuilding those per
   click would make the page unusable. */
function cdPickOne(kind,key,name,on){
  const s=cdPick(kind)[key]; on?s.add(name):s.delete(name);
  cdStale(); cdRefreshTally();
}
function cdAll(kind,key,on){
  const k=cdKind(kind);
  const shown=cdRows(key==='remove'?k.unused:k.duplicates).map(x=>x.name);
  const s=cdPick(kind)[key];
  shown.forEach(n=>on?s.add(n):s.delete(n));
  const head=document.getElementById(`cdc_${kind}_${key==='remove'?'unused':'dups'}`);
  if(head)head.closest('.clsec').querySelectorAll('.cllist input[type=checkbox]')
    .forEach(cb=>{cb.checked=on;});
  cdStale(); cdRefreshTally();
}
function cdChoose(kind,name,digest){
  const p=cdPick(kind);
  if(digest)p.choose[name]=digest; else delete p.choose[name];
  // the row's own highlight, without rebuilding 700 thumbnails
  const row=document.querySelector(`.cllist.vars input[name="cdv_${CSS.escape(kind)}_${CSS.escape(name)}"]`);
  const opts=row&&row.closest('.varopts');
  if(opts)opts.querySelectorAll('.varopt').forEach(l=>
    l.classList.toggle('on',l.querySelector('input').checked));
  cdStale(); cdRefreshTally();
}
function cdVarAll(kind,take){
  const p=cdPick(kind);
  // "the commonest" is options[0]: the server sorts each set by how many folders
  // hold that picture, so the first is the one the mod uses most widely.
  cdRows(cdKind(kind).variants).forEach(v=>{
    if(take)p.choose[v.name]=v.options[0].digest; else delete p.choose[v.name];});
  cdStale(); renderCards();
}
function cdToggle(key){state.cards.open[key]=!state.cards.open[key];renderCards();}
function cdStale(){const b=document.getElementById('cdPreview');
  if(b&&state.cards.plan){state.cards.plan=null;b.innerHTML='';}}
async function cdPickTarget(){
  const r=await api.post('/api/browse_folder',{title:'Folder to move the removed cards into'});
  if(!r.path)return;
  state.cards.target=r.path; cdStale(); renderCards();
  state.settings.last_cards_target=r.path;
  api.post('/api/settings',{last_cards_target:r.path});
}

function cdPayload(){
  const c=state.cards;
  const per=f=>Object.fromEntries(c.a.kinds.map(k=>[k.kind,f(cdPick(k.kind))]));
  return {mod:c.a.mod,target:c.target,
    remove:per(p=>[...p.remove]),
    consolidate:per(p=>[...p.cons]),
    choose:per(p=>({...p.choose}))};
}
async function cdPreview(){
  const box=document.getElementById('cdPreview'); if(!box)return null;
  box.innerHTML='<div class="preview">Planning…</div>';
  const r=await api.post('/api/cards/plan',cdPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.cards.plan=r;
  box.innerHTML=cdPlanHtml(r); return r;
}
function cdPlanHtml(r){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">🧹</span><span class="stext">What this does</span></div>
    ${li('',r.changes)}
    ${r.target?`<div class="srow"><span class="sicon">📁</span><span class="stext">into
      <span class="path">${esc(r.target)}</span></span></div>`:''}
    ${r.copies.length?`<div class="srow"><span class="sicon">+</span><span class="stext">
      ${r.copies.slice(0,8).map(x=>`<span class="path">${esc(x)}</span>`).join('<br>')}
      ${r.copy_count>8?`<br><i>…and ${r.copy_count-8} more written into the merc folder</i>`:''}</span></div>`:''}
    ${r.exports.length?`<div class="srow"><span class="sicon">→</span><span class="stext">
      ${r.exports.slice(0,8).map(x=>`<span class="path">${esc(x)}</span>`).join('<br>')}
      ${r.export_count>8?`<br><i>…and ${r.export_count-8} more moved out</i>`:''}</span></div>`:''}
    ${li('warn',r.warnings)}${li('bad',r.errors)}</div>`;
}
async function cdApply(){
  const c=state.cards;
  if(!c.target){toast('Choose where the removed cards should go first');return;}
  const r=state.cards.plan||await cdPreview();
  if(!r)return;
  if(r.errors&&r.errors.length){toast(r.errors[0]);return;}
  if(!r.delete_count&&!r.copy_count){toast('Nothing is ticked');return;}
  if(!confirm(`Move ${r.delete_count} card file(s) out of “${c.a.mod}”, freeing `+
      `${(r.freed/1048576).toFixed(1)} MB?\n\nThey are copied to:\n${r.target}\n\n`+
      `${r.consolidated?`${r.consolidated} card(s) are folded into the merc folder, which is `+
        `where the game looks when a faction's own folder has nothing.\n\n`:''}`+
      `Everything touched is backed up first. 🕑 Log → Undo puts it all back.`))return;
  const job=newJob();
  const res=await runJob(job,'Tidying the cards…',
    `Copying ${r.export_count} file(s) out, writing ${r.copy_count} into the merc folder,
     then taking ${r.delete_count} out of ${esc(c.a.mod)}. Everything is backed up as it goes.`,
    ()=>api.post('/api/cards/apply',{...cdPayload(),job}));
  if(res.error){toast('Card cleanup failed: '+res.error);renderCards();return;}
  closeModal();
  toast(`${res.plan.delete_count} card file(s) moved out, ${(res.plan.freed/1048576).toFixed(1)}`
       +` MB freed ✓  (undo in 🕑 Log)`,5200);
  // The lists were built from an audit taken BEFORE this ran, so the mod on disk
  // has changed and the page has to change with it.
  state.cards=null; state.destData=null;
  loadSource();
  loadCards();
}
