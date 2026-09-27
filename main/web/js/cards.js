/* cards.js - Unit cards tab: the two pictures a unit has, deduplicated

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   UNIT AND INFO CARDS - one picture, thirty folders.

   The game finds a unit's card under the PLAYER's faction folder, so a unit
   thirty factions can field needs its card in thirty of them. Mods do exactly
   that, byte for byte, and it is where the disk goes: Divide and Conquer ships
   1.2 GB of info cards for 917 units. The engine also falls back to the merc
   folder for any unit whose own faction folder has nothing - which is where one
   copy can do the job of thirty.

   So this tab is three questions, per kind of card:

     * whose art is for a unit that is GONE - a dictionary no unit claims;
     * which are the SAME picture in several folders - one hash, nothing to
       decide, fold them into the merc folder;
     * which really DIFFER per faction - the tool will not choose between two
       pictures a mod deliberately ships, so those are shown side by side and
       the pick is yours, "leave them alone" included.

   Everything ticked is MOVED to a folder outside the mod, backed up first and
   undoable from 🕑 Log - the same contract the other two cleaners make. It is a
   page rather than a dialog because choosing between card variants is reading
   work, and reading work does not belong in a modal.
   ===================================================================== */
const CARD_KIND_ICON={card:'🃏',info:'🖼'};

async function loadCards(){
  const mod=state.src;
  const job=newJob();
  main.innerHTML=bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit'))+
    `<div class="empty" style="max-width:460px;margin:60px auto">
      <div class="progress-track"><div class="progress-fill" id="jobFill" style="width:0%"></div></div>
      <div class="count" style="margin-top:8px"><b id="jobPct">0%</b>
        <span id="jobStep">${tt('cards.reading_s_cards',{mod:esc(mod)})}</span></div>
      <div class="count" style="margin-top:10px">${tt('cards.every_card_is_hashed_so_the')}</div>
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
    main.innerHTML=bmdbTabsHtml('')+`<div class="empty">${tt('cards.couldnt_read_the_cards')}<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="loadCards()">${tt('common.retry')}</button></div>`; return; }
  finally{ state.cardsJob=null; }
  if(stale('cards',mod))return;
  // What was typed into the folder box and which sections were unfolded survive
  // a re-audit; only the LISTS are replaced.
  const was=(state.cards&&state.cards.a&&state.cards.a.mod===a.mod)?state.cards:null;
  state.cards={a,
    target:(was&&was.target)||state.settings.last_cards_target
                            ||state.settings.last_cleanup_target||'',
    // Gone and duplicated are pre-ticked: both are facts, not judgements. The
    // variant sets are not - every one of them is a question.
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
   The header counts stay whole-list - a tick is a tick whether or not the row it
   is on is on screen - while "Select all" follows what you can see, which is the
   only reading of it that is not a trap while a filter is up. */
const cdQuery=()=>search.value.trim().toLowerCase();
const cdMatch=(row,q)=>!q||row.name.toLowerCase().includes(q)
  ||(row.unit||'').toLowerCase().includes(q)
  ||(row.folders||[]).some(f=>f.toLowerCase().includes(q));
const cdRows=(list)=>{const q=cdQuery(); return list.filter(r=>cdMatch(r,q));};
const cdShownNote=(shown,all)=>shown.length===all.length?''
  :`<div class="count" style="margin-top:6px">${tt('cards.of_shown_the_rest_are_filtered',{shown_n:shown.length,all_n:all.length})}</div>`;

function renderCards(){
  if(!state.cards||state.cards.a.mod!==state.src)return loadCards();
  const c=state.cards,a=c.a;
  count.textContent=`${a.kinds.reduce((n,k)=>n+k.file_count,0)} files`;
  main.innerHTML=bmdbTabsHtml(tt('cards.data_ui_units_data_ui_unit'))+`
    <div class="dbhead">
      <h2>${tt('cards.unit_and_info_cards',{mod:esc(a.mod)})}</h2>
      <span class="count">${tt('cards.unit_in_the_mod_could_stop',{units:a.units,units2:a.units===1?'':'s',kinds:a.kinds.map(k=>`${k.file_count} ${esc(k.label)}${k.file_count===1?'':'s'}`).join(' · '),x:MB(cdFreeable())})}</span>
    </div>
    <div class="cardsbody">
      <fieldset><legend>${tt('cards.where_the_removed_cards_go')}</legend>
        <div class="cltarget">
          <input id="cdTarget" value="${esc(c.target)}"
            placeholder="${ttA('cards.e_g_d_m2tw_backups_cards',{mod:esc(a.mod)})}"
            oninput="state.cards.target=this.value;cdStale()">
          <button onclick="cdPickTarget()">${tt('common.browse')}</button>
        </div>
        <div class="count" style="margin-top:6px">${tt('cards.must_be_outside_the_mod_nothing')}</div>
      </fieldset>
      ${a.kinds.map(cdKindHtml).join('')}
      <div id="cdPreview"></div>
      <div class="cardsfoot">
        <span class="count" id="cdTally">${cdTally()}</span>
        <span style="flex:1"></span>
        <button onclick="cdPreview()">${tt('common.probe')}</button>
        <button class="primary" onclick="cdApply()">${tt('common.move_them_out')}</button>
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
  return tt('cards.frees',{parts:parts.join(' · '),x:MB(cdFreeable())});
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
    <h3>${tt('cards.s_data_faction_falls_back_to',{x:CARD_KIND_ICON[k.kind]||'🖼',label:esc(k.label),base:esc(k.base),merc:esc(k.merc),dictionaries:k.dictionaries,dictionaries2:k.dictionaries===1?'':'s',file_count:k.file_count,file_count2:k.file_count===1?'':'s',x2:MB(k.bytes),already:k.already?` ${tt('cards.already_live_only_in',{already:k.already})} <code>${esc(k.merc)}</code>`:''})}</h3>
    ${sec('unused',tt('cards.for_units_that_are_gone'),()=>cdUnusedBody(k))}
    ${sec('dups',tt('cards.the_same_picture_in_several_folders'),()=>cdDupBody(k))}
    ${sec('vars',tt('cards.different_pictures_per_faction_your_call'),()=>cdVarBody(k))}
    ${cdNotesHtml(k)}
  </section>`;
}
function cdSectionCount(k,g){
  const p=cdPick(k.kind);
  if(g==='unused'){
    const b=k.unused.reduce((n,u)=>n+(p.remove.has(u.name)?u.bytes:0),0);
    return tt('cards.ticked',{remove_n:p.remove.size,unused_n:k.unused.length,MB:MB(b)});
  }
  if(g==='dups'){
    const b=k.duplicates.reduce((n,d)=>n+(p.cons.has(d.name)?d.bytes_saved:0),0);
    return tt('cards.ticked_2',{cons_n:p.cons.size,duplicates_n:k.duplicates.length,MB:MB(b)});
  }
  const n=Object.keys(p.choose).length;
  const b=k.variants.reduce((m,v)=>m+(p.choose[v.name]?v.bytes_saved:0),0);
  return tt('cards.chosen_needs_your_eye',{x:n,variants_n:k.variants.length,MB:MB(b)});
}

function cdUnusedBody(k){
  const p=cdPick(k.kind);
  if(!k.unused.length)return `<div class="count" style="margin-top:8px">${tt('cards.none_every_card_belongs_to_a')}</div>`;
  const rows=cdRows(k.unused);
  return `<div class="count" style="margin-top:7px">${tt('cards.no_unit_in_export_descr_unit')}</div>
    ${cdShownNote(rows,k.unused)}
    <div class="clbar">
      <button onclick="cdAll('${k.kind}','remove',true)">${tt('common.select_all')}</button>
      <button onclick="cdAll('${k.kind}','remove',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(u=>`<div class="clrow">
      <input type="checkbox" ${p.remove.has(u.name)?'checked':''}
        onchange="cdPickOne('${k.kind}','remove','${q1(esc(u.name))}',this.checked)">
      <img class="cdthumb" loading="lazy" onerror="this.style.visibility='hidden'"
        src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(u.showing)}${iconBust()}" alt="">
      <div class="grow"><span class="nm">${esc(u.name)}</span>
        <div class="sub">${tt('cards.folder',{folders_n:u.folders.length,folders:u.folders.length===1?'':'s',folders2:esc(u.folders.slice(0,8).join(', ')),folders3:u.folders.length>8?` +${u.folders.length-8}`:''})}</div></div>
      <span class="count">${MB(u.bytes)}</span></div>`).join('')}</div>`;
}

function cdDupBody(k){
  const p=cdPick(k.kind);
  if(!k.duplicates.length)return `<div class="count" style="margin-top:8px">${tt('cards.none_no_card_is_copied_into')}</div>`;
  const rows=cdRows(k.duplicates);
  return `<div class="count" style="margin-top:7px">${tt('cards.every_copy_of_these_is_byte',{base:esc(k.base),merc:esc(k.merc)})}</div>
    ${cdShownNote(rows,k.duplicates)}
    <div class="clbar">
      <button onclick="cdAll('${k.kind}','cons',true)">${tt('common.select_all')}</button>
      <button onclick="cdAll('${k.kind}','cons',false)">${tt('common.none_2')}</button></div>
    <div class="cllist">${rows.map(d=>`<div class="clrow">
      <input type="checkbox" ${p.cons.has(d.name)?'checked':''}
        onchange="cdPickOne('${k.kind}','cons','${q1(esc(d.name))}',this.checked)">
      <img class="cdthumb" loading="lazy" onerror="this.style.visibility='hidden'"
        src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(d.options[0].rel)}${iconBust()}" alt="">
      <div class="grow"><span class="nm">${esc(d.name)}</span>
        <span class="badge">${esc(d.unit)}</span>
        <div class="sub">${tt('cards.identical_cop',{folders_n:d.folders.length,folders:d.folders.length===1?'y':'ies',folders2:esc(d.folders.slice(0,8).join(', ')),folders3:d.folders.length>8?` +${d.folders.length-8}`:'',x:d.options[0].in_merc?' - one of them is already the merc copy':''})}</div></div>
      <span class="count">−${MB(d.bytes_saved)}</span></div>`).join('')}</div>`;
}

/* The one part of this page that is a question rather than a fact. Each row is a
   unit whose factions really do hold DIFFERENT pictures; the tool shows them
   side by side and takes no view. "Keep all" is the default and stays selected
   until you say otherwise - silently collapsing a mod's per-faction art into one
   picture is exactly the thing this must not do on its own. */
function cdVarBody(k){
  const p=cdPick(k.kind);
  if(!k.variants.length)return `<div class="count" style="margin-top:8px">${tt('cards.none_where_a_card_is_in')}</div>`;
  const rows=cdRows(k.variants);
  return `<div class="count" style="margin-top:7px">${tt('cards.these_units_have_different_cards_in',{merc:esc(k.merc)})}</div>
    ${cdShownNote(rows,k.variants)}
    <div class="clbar">
      <button onclick="cdVarAll('${k.kind}',false)">${tt('cards.keep_all_as_they_are')}</button>
      <button onclick="cdVarAll('${k.kind}',true)" title="${ttA('cards.choose_the_picture_the_most_folders')}">${tt('cards.take_the_commonest_everywhere')}</button></div>
    <div class="cllist vars">${rows.map(v=>`<div class="clrow varrow">
      <div class="grow"><span class="nm">${esc(v.name)}</span>
        <span class="badge">${esc(v.unit)}</span>
        <span class="count">${tt('cards.different_pictures_across_folders',{options_n:v.options.length,folders_n:v.folders.length})}</span>
        <div class="varopts">
          <label class="varopt${p.choose[v.name]?'':' on'}">
            <input type="radio" name="cdv_${esc(k.kind)}_${esc(v.name)}"
              ${p.choose[v.name]?'':'checked'}
              onchange="cdChoose('${k.kind}','${q1(esc(v.name))}','')">
            <span class="varkeep">${tt('cards.keep_all',{options_n:v.options.length})}</span></label>
          ${v.options.map(o=>`<label class="varopt${p.choose[v.name]===o.digest?' on':''}">
            <input type="radio" name="cdv_${esc(k.kind)}_${esc(v.name)}"
              ${p.choose[v.name]===o.digest?'checked':''}
              onchange="cdChoose('${k.kind}','${q1(esc(v.name))}','${esc(o.digest)}')">
            <img loading="lazy" onerror="this.style.visibility='hidden'"
              src="/icon?mod=${enc(state.src)}&kind=modfile&rel=${enc(o.rel)}${iconBust()}" alt="">
            <span class="count">${esc(o.folders.slice(0,3).join(', '))}${
              o.folders.length>3?` +${o.folders.length-3}`:''}${
              o.in_merc?tt('cards.merc'):''}</span></label>`).join('')}
        </div></div>
      <span class="count">−${MB(v.bytes_saved)}</span></div>`).join('')}</div>`;
}

/* Everything this pass deliberately did not touch, said out loud. Each of these
   is a place where "unused" would have been a guess, and the whole value of the
   page is that it never guesses about art it is about to delete. */
function cdNotesHtml(k){
  const bits=[];
  if(k.stray_count)bits.push(tt('cards.file_in_these_folders_not_shaped',{stray_count:k.stray_count,stray_count2:k.stray_count===1?'':'s',stray_count3:k.stray_count===1?'is':'are',label:esc(k.label),x:MB(k.stray_bytes)}));
  if(k.pinned.length)bits.push(tt('cards.unit_pin_their_to_a_folder',{pinned_n:k.pinned.length,pinned:k.pinned.length===1?'':'s',label:esc(k.label),kind:k.kind==='card'?'card_pic_dir':'info_pic_dir'}));
  if(k.lua_kept.length)bits.push(tt('cards.belong_to_a_dictionary_no_unit',{lua_kept_n:k.lua_kept.length,label:esc(k.label),lua_kept:k.lua_kept.length===1?'':'s',lua_kept2:k.lua_kept.length===1?tt('common.it_is'):tt('common.they_are')}));
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
  const r=await api.post('/api/browse_folder',{title:tt('cards.folder_to_move_the_removed_cards')});
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
  box.innerHTML=`<div class="preview">${tt('common.planning')}</div>`;
  const r=await api.post('/api/cards/plan',cdPayload());
  if(r.error){box.innerHTML=`<div class="preview w-bad">${esc(r.error)}</div>`;return null;}
  state.cards.plan=r;
  box.innerHTML=cdPlanHtml(r); return r;
}
function cdPlanHtml(r){
  const li=(cls,items)=>items.map(x=>`<div class="srow ${cls}"><span class="sicon">${
      cls==='bad'?'✗':cls==='warn'?'!':'·'}</span><span class="stext">${esc(x)}</span></div>`).join('');
  return `<div class="sum" style="margin-top:10px">
    <div class="srow shead"><span class="sicon">🧹</span><span class="stext">${tt('cards.what_this_does')}</span></div>
    ${li('',r.changes)}
    ${r.target?`<div class="srow"><span class="sicon">📁</span><span class="stext">${tt('cards.into')}
      <span class="path">${esc(r.target)}</span></span></div>`:''}
    ${r.copies.length?`<div class="srow"><span class="sicon">+</span><span class="stext">
      ${r.copies.slice(0,8).map(x=>`<span class="path">${esc(x)}</span>`).join('<br>')}
      ${r.copy_count>8?`<br><i>${tt('cards.and_more_written_into_the_merc',{copy_count:r.copy_count-8})}</i>`:''}</span></div>`:''}
    ${r.exports.length?`<div class="srow"><span class="sicon">→</span><span class="stext">
      ${r.exports.slice(0,8).map(x=>`<span class="path">${esc(x)}</span>`).join('<br>')}
      ${r.export_count>8?`<br><i>${tt('cards.and_more_moved_out',{export_count:r.export_count-8})}</i>`:''}</span></div>`:''}
    ${li('warn',r.warnings)}${li('bad',r.errors)}</div>`;
}
async function cdApply(){
  const c=state.cards;
  if(!c.target){toast(tt('cards.choose_where_the_removed_cards_should'));return;}
  const r=state.cards.plan||await cdPreview();
  if(!r)return;
  if(r.errors&&r.errors.length){toast(r.errors[0]);return;}
  if(!r.delete_count&&!r.copy_count){toast(tt('common.nothing_is_ticked'));return;}
  if(!confirm(tt('cards.move_card_file_s_out_of',{delete_count:r.delete_count,mod:c.a.mod})+
      tt('cards.mb_they_are_copied_to',{freed:(r.freed/1048576).toFixed(1),target:r.target})+
      `${r.consolidated?tt('cards.card_s_are_folded_into_the',{consolidated:r.consolidated})+
        tt('cards.where_the_game_looks_when_a'):''}`+
      tt('cards.everything_touched_is_backed_up_first')))return;
  const job=newJob();
  const res=await runJob(job,tt('cards.tidying_the_cards'),
    tt('cards.copying_file_s_out_writing_into',{export_count:r.export_count,copy_count:r.copy_count,delete_count:r.delete_count,mod:esc(c.a.mod)}),
    ()=>api.post('/api/cards/apply',{...cdPayload(),job}));
  if(res.error){toast(tt('cards.card_cleanup_failed')+res.error);renderCards();return;}
  closeModal();
  toast(tt('cards.card_file_s_moved_out',{delete_count:res.plan.delete_count,x:(res.plan.freed/1048576).toFixed(1)})
       +tt('cards.mb_freed_undo_in_log'),5200);
  // The lists were built from an audit taken BEFORE this ran, so the mod on disk
  // has changed and the page has to change with it.
  state.cards=null; state.destData=null;
  loadSource();
  loadCards();
}
